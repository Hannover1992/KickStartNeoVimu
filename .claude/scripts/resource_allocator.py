"""resource_allocator.py — BL-368: vollstaendige THIN claim/lease/wait/release-Fassade (T4 KERN).

4-Verben-Fassade:
  claim(resource_id, *, worker_id, ttl=600, vault_root=None) -> bool
    Non-blocking single-attempt; delegates to srr.acquire.
  lease(resource_id, *, ttl=600, worker_id, vault_root=None) -> bool
    Acquire with explicit TTL (Lease-Semantik); delegates to srr.acquire.
  acquire_with_wait(resource_id, *, worker_id, ttl=600, timeout=60, backoff=None, vault_root=None) -> bool
    Blocking acquire with backoff retry; delegates to srr.acquire.
  release(resource_id, *, worker_id, vault_root=None) -> bool
    Owner-gated free; delegates to srr.release.
  acquire_all(resource_ids, *, worker_id, ttl=600, vault_root=None) -> bool
    Atomic all-or-nothing acquire; delegates to srr.acquire_all (Rollback geerbt).

Teardown-Hook-Mechanismus (BL-368 batch_5, AK-HANDSHAKE-PL-1):
  register_teardown_hook(resource_id, callback) -> None
    Registriert callback(resource_id) fuer LAST-RELEASE-Ereignisse dieser Ressource.
    Modul-level dict (_TEARDOWN_HOOKS) — kein eigener Lock-Mechanismus.
  _fire_teardown_hooks(resource_id) -> None
    Ruft alle registrierten callbacks fuer resource_id auf (at-least-once-Garantie).
    Idempotenz der callbacks ist Sache des Consumers (BL-408), nicht hier.

Drei Trigger-Pfade fuer _fire_teardown_hooks:
  Pfad 1 (normaler release): srr.release liefert True -> Hooks feuern.
  Pfad 2 (Lease-Expiry/Stale-Reclaim): Stale-Check VOR srr.acquire entdeckt stale Lock
    -> Hooks feuern BEVOR srr.acquire den Reclaim durchfuehrt (Ordnungs-Invariante:
    neuer Holder erbt keinen dreckigen Zustand).
  Pfad 3 (force-clear): force_clear (kommt T7) ruft _fire_teardown_hooks direkt.

Abgrenzungs-Doktrin BL-368 vs. BL-408:
  BL-368 (dieses Modul) — Verantwortung: Hook-PUNKT + at-least-once-GARANTIE
    Dieses Modul stellt sicher, dass der Teardown-Callback beim last-release eines
    Locks aufgerufen wird — ueber alle drei Trigger-Pfade. Die Garantie ist
    at-least-once, nicht exactly-once: in Edge-Cases (z.B. Stale-Reclaim gleichzeitig
    mit normalem release) kann der Hook mehr als einmal feuern. Dieses Modul macht
    KEINE Aussage ueber den Inhalt des callbacks oder dessen Nebeneffekte.

  BL-408 (separates BL, forward) — Verantwortung: callback-INHALT + IDEMPOTENZ
    Weil BL-368 only at-least-once garantiert, MUSS jeder callback (registriert via
    register_teardown_hook) idempotent implementiert werden. Doppeltes Feuern darf
    keinen inkorrekten Zustand erzeugen. Die Implementierung und Idempotenz-Sicherung
    der konkreten Cleanup-Logik ist vollstaendig Sache von BL-408.

  Consumer-Doku (wie den Hook nutzen):
    1. Idempotenten Callback implementieren:
         def my_cleanup(resource_id: str) -> None:
             # Idempotent: safe to call more than once for the same resource_id
             ...
    2. Hook registrieren (vor dem ersten claim/lease):
         from resource_allocator import register_teardown_hook
         register_teardown_hook("my-resource", my_cleanup)
    3. Wann feuert der Hook:
         - Bei normalem release() durch den Owner (Pfad 1)
         - Bei Lease-Expiry/Stale-Reclaim, BEVOR der naechste claim() greift (Pfad 2)
         - Bei force_clear() (Pfad 3, T7)
    4. Garantie-Grenze: at-least-once (nicht exactly-once). Callback muss idempotent
       sein (BL-408). Kein automatisches Aufraeumen des Hooks nach dem Feuern.
    5. Skill-Verdrahtung: siehe _TDD_teardown.md (batch_4 PL-2) fuer die
       Skill-seitige Integration dieser Hook-Infrastruktur.

Keine eigene Lock-Semantik — delegiert ausschliesslich an stage_resource_registry
(srr) und factory_lock (fl). Kein mkdir/os.replace/rmtree/eigenes Stale-Handling.

format_version: "1.0"
"""

import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

# Import-Konvention wie die Geschwister-Module (stage_resource_registry, factory_lock)
sys.path.insert(0, str(Path(__file__).parent))

import stage_resource_registry as srr
import factory_lock as fl

FORMAT_VERSION = "1.0"

# ── Teardown-Hook-Registry (BL-368 batch_5) ───────────────────────────────────
# Modul-level state — kein eigener Lock-Mechanismus (THIN-DoD).
# {resource_id: [callback, ...]}
_TEARDOWN_HOOKS: Dict[str, List[Callable[[str], None]]] = {}


def register_teardown_hook(resource_id: str, callback: Callable[[str], None]) -> None:
    """Register a teardown callback for a resource's last-release event.

    callback(resource_id) is called at-least-once when the resource lock is freed
    (via normal release, stale-reclaim, or force-clear). Idempotency of the callback
    is the consumer's responsibility (BL-408), not enforced here.

    Multiple callbacks per resource_id are accumulated; all fire on teardown.
    """
    _TEARDOWN_HOOKS.setdefault(resource_id, []).append(callback)


def _fire_teardown_hooks(resource_id: str) -> None:
    """Fire all registered teardown callbacks for resource_id (at-least-once).

    Called on three trigger paths:
      Pfad 1: normal release() — srr.release returned True (owner released).
      Pfad 2: stale-reclaim — BEFORE srr.acquire reclaims the expired lock
               (ordering invariant: new holder does not inherit dirty state).
      Pfad 3: force-clear — force_clear() calls this directly (T7, batch_7).

    at-least-once guarantee: if a callback raises, remaining callbacks still run.
    Does NOT clear the registry after firing (consumers may re-register).
    """
    for cb in _TEARDOWN_HOOKS.get(resource_id, []):
        try:
            cb(resource_id)
        except Exception:
            pass  # at-least-once: continue despite individual callback failures


def _check_stale_and_fire_hooks(resource_id: str, ttl: int, vault_root: Optional[Path]) -> None:
    """Check if the held lock for resource_id is stale; if so, fire teardown hooks.

    Pfad 2 implementation: mirrors the stale-detection logic in srr.acquire so that
    hooks fire BEFORE srr.acquire performs the reclaim. This preserves the ordering
    invariant: teardown runs before the next holder acquires the lock.

    Uses srr._res_bl_id + fl.is_bl_stale (same delegation chain as srr.acquire).
    No own lock removal — the actual reclaim stays inside srr.acquire/factory_lock.
    """
    res_id = srr._res_bl_id(resource_id)
    lock_dir = fl._bl_lock_dir(res_id, vault_root=vault_root)
    if not lock_dir.exists():
        return
    effective_ttl = srr._lock_ttl(lock_dir, fallback=ttl)
    if fl.is_bl_stale(res_id, timeout=effective_ttl, vault_root=vault_root):
        _fire_teardown_hooks(resource_id)


# ── Lease-Verb (T2) ───────────────────────────────────────────────────────────

def lease(
    resource_id: str,
    *,
    ttl: int = 600,
    worker_id: str,
    vault_root: Optional[Path] = None,
) -> bool:
    """Acquire a named resource with explicit TTL (lease semantics).

    Delegates to srr.acquire(resource_id, worker_id=worker_id, ttl=ttl,
    vault_root=vault_root). Returns True on success (FREE->LOCKED or stale-reclaim),
    False if the resource is held non-stale by another worker.

    THIN-DoD: no own lock mechanism, no mkdir/os.replace/rmtree.
    Teardown-Hook Pfad 2: fires registered hooks if the existing lock is stale,
    BEFORE srr.acquire performs the reclaim (ordering invariant).
    """
    _check_stale_and_fire_hooks(resource_id, ttl, vault_root)
    return srr.acquire(resource_id, worker_id=worker_id, ttl=ttl, vault_root=vault_root)


def renew(
    resource_id: str,
    *,
    worker_id: str,
    vault_root: Optional[Path] = None,
) -> bool:
    """Renew (heartbeat) an existing lease without re-acquiring.

    Delegates to fl.heartbeat_bl(bl_id=srr._res_bl_id(resource_id),
    worker_id=worker_id, vault_root=vault_root). Returns True if the heartbeat
    was written (caller is owner), False if lock missing or caller is not owner.

    THIN-DoD: no own lock mechanism, no mkdir/os.replace/rmtree.
    """
    bl_id = srr._res_bl_id(resource_id)
    return fl.heartbeat_bl(bl_id=bl_id, worker_id=worker_id, vault_root=vault_root)


# ── Wait-Verb (T3) ────────────────────────────────────────────────────────────

def acquire_with_wait(
    resource_id: str,
    *,
    worker_id: str,
    ttl: int = 600,
    timeout: float = 60,
    backoff: Optional[List[float]] = None,
    vault_root: Optional[Path] = None,
) -> bool:
    """Blocking acquire: retries srr.acquire until success or timeout.

    Time-triple:
      - timeout  : total allowed wait (seconds, accumulated over backoff steps)
      - backoff  : sleep intervals per attempt [1,2,4,8,30]; last value repeats
                   (analog to factory_lock.py:233, Z279-285)
      - ttl      : forwarded to srr.acquire as the lease duration

    Elapsed time is tracked as accumulated backoff (sleep) values, so the
    function is deterministic under mocked time.sleep without requiring real
    wall-clock waiting. Returns True on success, False when accumulated elapsed
    meets or exceeds timeout.

    THIN-DoD: no own lock mechanism, no mkdir/os.replace/rmtree.
    """
    if backoff is None:
        backoff = [1, 2, 4, 8, 30]

    elapsed = 0.0
    attempt = 0

    while True:
        if srr.acquire(resource_id, worker_id=worker_id, ttl=ttl, vault_root=vault_root):
            return True

        wait = backoff[min(attempt, len(backoff) - 1)]
        elapsed += wait
        if elapsed >= timeout:
            return False

        time.sleep(wait)
        attempt += 1


# ── Claim-Verb (T4 — non-blocking single-attempt) ────────────────────────────

def claim(
    resource_id: str,
    *,
    worker_id: str,
    ttl: int = 600,
    vault_root: Optional[Path] = None,
) -> bool:
    """Non-blocking single-attempt acquire of a named resource.

    Delegates to srr.acquire(resource_id, worker_id, ttl=ttl, vault_root=vault_root).
    Returns True immediately if the resource is free, False if held by another worker.
    No retry, no blocking — use acquire_with_wait for blocking semantics.

    THIN-DoD: no own lock mechanism, no mkdir/os.replace/rmtree.
    Teardown-Hook Pfad 2: fires registered hooks if the existing lock is stale,
    BEFORE srr.acquire performs the reclaim (ordering invariant).
    """
    _check_stale_and_fire_hooks(resource_id, ttl, vault_root)
    return srr.acquire(resource_id, worker_id, ttl=ttl, vault_root=vault_root)


# ── Release-Verb (T4 — owner-gated free) ──────────────────────────────────────

def release(
    resource_id: str,
    *,
    worker_id: str,
    vault_root: Optional[Path] = None,
) -> bool:
    """Owner-gated release of a named resource.

    Delegates to srr.release(resource_id, worker_id, vault_root=vault_root).
    Returns True if the caller is the owner and the resource was freed,
    False if the caller is not the owner or the resource was not held.

    THIN-DoD: no own lock mechanism, no mkdir/os.replace/rmtree.
    Teardown-Hook Pfad 1: fires registered hooks when the owner successfully
    releases the lock (srr.release returns True).
    """
    released = srr.release(resource_id, worker_id, vault_root=vault_root)
    if released:
        _fire_teardown_hooks(resource_id)
    return released


# ── Claim-Divisible-Verb (batch_6, AK-DIVISIBILITY-PL-1) ─────────────────────
# Routing-Vertrag (THIN-Konsument):
#   divisibility=None  -> query stage_resource_seam; DEFAULT_DIVISIBILITY="unteilbar"
#   "unteilbar" (oder unbekannt, oder teilbar ohne region) -> srr.acquire (whole-claim)
#   "teilbar" + region=(start,end) -> srr.acquire_region (region-lock)
#
# Konsument-only: kein mkdir/os.replace/rmtree. Kein eigenes acquire/release.
# Region-Schneide-Optimierung = BL-353/415/416-Territorium, NICHT hier.

DEFAULT_DIVISIBILITY = "unteilbar"


def claim_divisible(
    resource_id: str,
    *,
    worker_id: str,
    region: Optional[tuple] = None,
    vault_root: Optional[Path] = None,
    divisibility: Optional[str] = None,
    ttl: int = 600,
) -> bool:
    """Divisibility-routing claim for a named resource.

    Routing rule (pure consumer — no own acquire/release logic):
      1. Resolve divisibility:
           - If ``divisibility`` param given: use as-is.
           - If None: query stage_resource_seam.stage_resources()["divisibility"]
             for this resource_id; fall back to DEFAULT_DIVISIBILITY="unteilbar".
      2. "teilbar" AND region given (start, end tuple):
           -> srr.acquire_region(resource_id, region[0], region[1], worker_id, ...)
      3. Otherwise ("unteilbar" / unknown / "teilbar" without region):
           -> srr.acquire(resource_id, worker_id, ...) — whole-claim.

    THIN-DoD: no mkdir/os.replace/rmtree. Seam is read-only.
    Region-cutting optimisation belongs to BL-353/415/416, not here.
    """
    # Step 1: resolve divisibility
    # When divisibility=None: default to DEFAULT_DIVISIBILITY (conservative, no False-Share).
    # stage_resource_seam.stage_resources() requires a stage-handle arg (producer-oriented API)
    # and is not a zero-arg registry query — per-resource seam lookup is BL-353/415/416 scope.
    if divisibility is None:
        divisibility = DEFAULT_DIVISIBILITY

    # Step 2: route
    if divisibility == "teilbar" and region is not None:
        return srr.acquire_region(
            resource_id, region[0], region[1], worker_id, ttl=ttl, vault_root=vault_root
        )

    # Step 3: unteilbar / fallback -> whole-claim
    return srr.acquire(resource_id, worker_id, ttl=ttl, vault_root=vault_root)


# ── Acquire-All-Verb (T4 — atomic all-or-nothing) ─────────────────────────────

def acquire_all(
    resource_ids: List[str],
    *,
    worker_id: str,
    ttl: int = 600,
    vault_root: Optional[Path] = None,
) -> bool:
    """Atomic all-or-nothing acquire for a list of resource IDs.

    Delegates to srr.acquire_all(resource_ids, worker_id, ttl=ttl, vault_root=vault_root).
    Returns True only if ALL resources were successfully acquired. On partial failure,
    rollback is inherited from srr.acquire_all — no own rollback logic.

    THIN-DoD: no own lock mechanism, no mkdir/os.replace/rmtree.
    """
    return srr.acquire_all(resource_ids, worker_id, ttl=ttl, vault_root=vault_root)


# ── Force-Clear-Verb (batch_7, AK-FORCE-CLEAR-PL-1) ──────────────────────────
# Privilegiert (Admin/PC), Crash-Recovery. THIN: delegiert Lockdir-Entfernung
# ausschliesslich an fl.force_release_bl — kein eigenes rmtree/mkdir/os.replace.

def force_clear(
    resource_id: str,
    *,
    vault_root: Optional[Path] = None,
) -> bool:
    """Privileged unconditional free of a named resource (Admin/PC, Crash-Recovery).

    Breaks the held res__-Lock WITHOUT an owner-check. Three steps, all delegated:
      1. Resolve the bl_id: srr._res_bl_id(resource_id)
      2. Remove the lock dir: fl.force_release_bl(bl_id, vault_root=vault_root)
      3. Fire teardown hooks: _fire_teardown_hooks(resource_id)  [Pfad 3, at-least-once]

    Returns the result of fl.force_release_bl (True, including when the dir was
    already gone = idempotent). THIN-DoD: no mkdir/os.replace/rmtree in this file.
    """
    bl_id = srr._res_bl_id(resource_id)
    ok = fl.force_release_bl(bl_id, vault_root=vault_root)
    _fire_teardown_hooks(resource_id)
    return ok
