"""BL-247: Stage-Availability-Registry — thin wrapper over factory_lock (BL-229).

Ressourcen-zentrische, run-uebergreifende FREE/LOCKED-Schicht fuer nicht-teilbare
Ressourcen. KEINE eigene Lock-Semantik: delegiert auf factory_lock.acquire_bl/
release_bl mit bl_id="res__{fs_safe(resource_id)}". .locks/res__{id}.lock/-Dirs =
Source-of-Truth (C3), _resource_availability.md = abgeleiteter Render.

BL-352-(a) (Windows-FS-safe + REVERSIBEL): factory_lock baut den Lock-Dir-Namen
als f"{bl_id}.lock" — der bl_id wird also zum Verzeichnisnamen. Der frueher
gewaehlte Prefix "res::" enthaelt ':' (auf Windows in Datei-/Ordnernamen ILLEGAL,
WinError 123 bei mkdir). resource_ids selbst koennen ebenfalls FS-illegale Zeichen
tragen. Loesung: _fs_safe() encodet jedes FS-illegale Zeichen (`: / \\ * ? " < > |`
plus den Escape-Introducer `~`) REVERSIBEL zu einem `~XX~`-Token; _fs_unsafe()
dekodiert. AK-2-Geist gewahrt: der Key IST der resource_id, nur FS-enkodiert — kein
Surplus-Identifier-Raum. render()/lookup_free() liefern den ORIGINAL-resource_id
(Caller-Eingabe wird durchgereicht; _fs_unsafe rekonstruiert ihn aus dem Lock-Key).

Vorbild (PT-GEN-HookGuard-Mirror, 1:1): factory_lock.acquire_promotion_lock /
release_promotion_lock (factory_lock.py:767-828, BL-320) — selbes thin-Wrapper-Trio.
acquire/release erfinden KEINE Lock-Semantik (PT-GEN-LeadFollow): atomares
test-and-set (AK-4), Stale-Reclaim (AK-8) und gone-Wahrheit (W-LOCK-4) sind von
factory_lock GEERBT. render() = NEUES versioniertes Vault-Artefakt mit
format_version-Stempel (PT-GEN-FormatVersion-DualRead).
"""

import time
import factory_lock as fl  # Import-Konvention wie test_factory_lock (import factory_lock as fl)
from pathlib import Path
from typing import Optional, Dict, List, Tuple, Any

# Top-Level format_version-Stempel fuer das _resource_availability.md-Artefakt
# (PT-GEN-FormatVersion-DualRead, NIE Crash bei Alt-Vault/Redeploy).
FORMAT_VERSION = "1.0"
RESOURCE_LOCK_PREFIX = "res__"  # res__{fs_safe(resource_id)} -> .locks/res__{id}.lock/
RENDER_FILE_NAME = "_resource_availability.md"

# BL-352-(a): reversibles, SELBST-DELIMITIERENDES FS-safe-Encoding (percent-style,
# Tilde statt %). Jedes auf Windows in Datei-/Ordnernamen illegale Zeichen — plus der
# Escape-Introducer `~` SELBST — wird zu `~XX` mit GENAU 2 Hex-Ziffern (Char-Code,
# ord<256). Fixe Token-Breite (3 Zeichen) => kein Token kann in ein anderes
# hineinragen (das frueher gewaehlte `~X~`-Schema war NICHT prefix-frei:
# `~s~b~s~` enthielt `~b~` als Teilstring -> Decode-Kollision, Behavior-Review-Fund).
# `~` wird mit-escapt (`~7e`), damit die Abbildung bijektiv bleibt.
_FS_ILLEGAL = set(':/\\*?"<>|~')  # `~` = Escape-Introducer, MUSS mit-escapt werden


def _fs_safe(resource_id: str) -> str:
    """Encode a resource_id to a Windows-FS-safe, REVERSIBLE token (BL-352-(a)).

    Each FS-illegal char (`: / \\ * ? " < > |`) and the escape-introducer `~` becomes
    a fixed-width `~XX` (XX = 2-digit lowercase hex of the char code). Fixed width =
    self-delimiting -> bijective decode (no token straddles another). A simple id
    without illegal chars passes through unchanged (e.g. 'r1' -> 'r1')."""
    out = []
    for ch in resource_id:
        if ch in _FS_ILLEGAL:
            out.append(f"~{ord(ch):02x}")
        else:
            out.append(ch)
    return "".join(out)


def _fs_unsafe(fs_safe_id: str) -> str:
    """Inverse of _fs_safe — reconstruct the original resource_id from a key.

    Scans for `~XX` (tilde + exactly 2 hex digits) and restores chr(int(XX,16));
    a lone `~` not followed by 2 hex digits is passed through (robust). Fixed-width
    tokens make this a clean single left-to-right pass (bijective roundtrip)."""
    out = []
    i = 0
    n = len(fs_safe_id)
    while i < n:
        ch = fs_safe_id[i]
        if ch == "~" and i + 2 < n:
            hexpart = fs_safe_id[i + 1:i + 3]
            try:
                out.append(chr(int(hexpart, 16)))
                i += 3
                continue
            except ValueError:
                pass  # not a valid token -> pass the '~' through verbatim
        out.append(ch)
        i += 1
    return "".join(out)


# ── Helper: resource_id -> factory_lock bl_id ────────────────────────────────
def _res_bl_id(resource_id: str) -> str:
    """Map a resource_id to the factory_lock bl_id namespace ('res__{fs_safe(id)}').

    BL-352-(a): FS-safe + reversibel. factory_lock haengt '.lock' an und macht den
    bl_id zum Dir-Namen; daher MUSS er Windows-legal sein. Der Key bleibt der
    resource_id (AK-2, kein Surplus-Raum) — nur FS-enkodiert via _fs_safe."""
    return f"{RESOURCE_LOCK_PREFIX}{_fs_safe(resource_id)}"


def _vault_root(vault_root: Optional[Path]) -> Path:
    """Vault-First: expliziter vault_root gewinnt, sonst fl.VAULT_ROOT (DT-13)."""
    return vault_root if vault_root is not None else fl.VAULT_ROOT


# ── AK-3 / AK-4 / AK-8: acquire (single resource) ────────────────────────────
def acquire(
    resource_id: str,
    worker_id: str,
    bl_id: str = "",
    ttl: int = 600,
    vault_root: Optional[Path] = None,
) -> bool:
    """Acquire one non-shareable resource. Delegates to factory_lock.acquire_bl.

    Returns True (FREE->LOCKED or stale-reclaim), False (held non-stale).
    'bl_id' (das acquirende BL) wird via phase getragen (factory_lock hat kein
    Fremd-BL-Feld; phase.txt ist frei, C7/SOA-2). run_id = worktree (cwd, AK-11).
    'ttl' steuert die Stale-Schwelle dieser Ressource (AK-8): ein per-Ressource
    aelterer Lock wird vor dem acquire reclaimt, damit T6 (ttl=1) deterministisch
    bleibt — der Reclaim selbst delegiert an factory_lock (kein Eigen-rmtree).
    """
    res_id = _res_bl_id(resource_id)

    # AK-8: per-Ressource Stale-Schwelle. factory_lock.acquire_bl/is_bl_stale messen
    # die heartbeat-Frische gegen einen vom CALLER uebergebenen timeout — sie kennen
    # KEINE pro-Lock-gespeicherte ttl. Der ttl ist aber eine Eigenschaft des Locks,
    # MIT DEM er erzeugt wurde (BL-352-(b)): ein mit ttl=1 erzeugter Lock soll nach
    # 1s stale sein, egal welchen ttl ein SPAETERER Acquirer mitbringt. Loesung: der
    # erzeugende ttl wird beim Acquire in einer Sidecar-Datei (res_ttl.txt) IM bereits
    # von factory_lock erzeugten Lock-Dir abgelegt (reiner Metadaten-Write, KEIN
    # eigenes mkdir/rmtree — selbe Klasse wie factory_locks worktree.txt/phase.txt).
    # Der Stale-Pre-Check liest diese Sidecar => die effektive Schwelle ist die des
    # GEHALTENEN Locks, nicht die des aktuellen Aufrufers (Fallback: aktueller ttl,
    # falls Sidecar fehlt — Alt-Lock/Redeploy-robust, FormatVersion-Geist).
    lock_dir = fl._bl_lock_dir(res_id, vault_root=vault_root)
    if lock_dir.exists():
        effective_ttl = _lock_ttl(lock_dir, fallback=ttl)
        if fl.is_bl_stale(res_id, timeout=effective_ttl, vault_root=vault_root):
            # Stale nach der Lock-eigenen ttl: Reclaim ueber factory_lock (kein
            # Eigen-rmtree). release_bl ist owner-gated + nutzt _robust_rmtree
            # (gone-Wahrheit) — wir reichen den protokollierten Owner durch.
            _reclaim_if_stale(res_id, effective_ttl, vault_root)

    acquired = fl.acquire_bl(
        bl_id=res_id,
        worker_id=worker_id,
        ttl=ttl,
        phase=f"res:{bl_id}" if bl_id else "res",
        vault_root=vault_root,
    )
    if acquired:
        # Persist die erzeugende ttl IN das (jetzt existierende) Lock-Dir, damit ein
        # spaeterer Acquirer die Lock-eigene Stale-Schwelle kennt. Metadaten-Write in
        # ein vorhandenes Dir (kein mkdir/rmtree => anti-dup gewahrt, factory_lock
        # unberuehrt). Best-effort: ein fehlgeschlagener Sidecar-Write degradiert nur
        # auf den ttl-Fallback, bricht das acquire nicht.
        try:
            (lock_dir / "res_ttl.txt").write_text(str(int(ttl)), encoding="utf-8")
        except OSError:
            pass
    return acquired


def _lock_ttl(lock_dir: Path, fallback: int) -> int:
    """Read the per-lock stale-threshold (res_ttl.txt) written at acquire-time.

    BL-352-(b): the stale window of a held lock is the ttl IT was created with, not
    the ttl a later acquirer passes. Returns the persisted ttl, or 'fallback' (the
    current call's ttl) if the sidecar is missing/unreadable (older lock / robust)."""
    try:
        return int((lock_dir / "res_ttl.txt").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return fallback


def _reclaim_if_stale(res_id: str, ttl: int, vault_root: Optional[Path]) -> None:
    """Delegate the stale-reclaim of a per-resource lock to factory_lock.

    factory_lock.reclaim_stale_bl_locks uses the default 300s threshold and skips
    '_'-prefixed locks; it does not honor a per-resource ttl. To keep the wrapper
    a pure delegate (no own rmtree/mkdir/mtime-compare) while honoring the lock's
    own ttl, we check is_bl_stale(timeout=ttl) — but the physical removal stays
    inside factory_lock. We re-use release_bl with the recorded owner."""
    if not fl.is_bl_stale(res_id, timeout=ttl, vault_root=vault_root):
        return
    lock_dir = fl._bl_lock_dir(res_id, vault_root=vault_root)
    try:
        owner = (lock_dir / "owner.txt").read_text(encoding="utf-8").strip()
    except OSError:
        owner = ""
    if owner:
        # release_bl is owner-gated + uses factory_lock's own _robust_rmtree
        # (gone-Wahrheit). Passing the recorded owner makes the stale holder's
        # lock removable without this module performing any rmtree/mkdir itself.
        fl.release_bl(bl_id=res_id, worker_id=owner, vault_root=vault_root)


# ── AK-3: release (single resource) ──────────────────────────────────────────
def release(
    resource_id: str,
    worker_id: str,
    vault_root: Optional[Path] = None,
) -> bool:
    """Release one resource (owner-only). Delegates to factory_lock.release_bl
    -> uses _robust_rmtree (gone-Wahrheit, W-LOCK-4). True if owner released."""
    return fl.release_bl(
        bl_id=_res_bl_id(resource_id),
        worker_id=worker_id,
        vault_root=vault_root,
    )


# ── SOA-4: all-or-nothing acquire (n:m, mit Rollback) ────────────────────────
def acquire_all(
    resource_ids: List[str],
    worker_id: str,
    bl_id: str = "",
    ttl: int = 600,
    vault_root: Optional[Path] = None,
) -> bool:
    """Acquire ALL resources atomar-gestaffelt. Deterministische Reihenfolge
    (sorted) gegen acquire-order-deadlock. Bei Partial-Fail: Rollback (release
    der bereits gehaltenen). True nur wenn ALLE acquiriert; sonst False + nichts
    gehalten. Baut NUR auf acquire/release (kein neuer Lock-Mechanismus)."""
    held: List[str] = []
    for rid in sorted(resource_ids):  # sorted = deterministische Lock-Order
        if acquire(rid, worker_id, bl_id=bl_id, ttl=ttl, vault_root=vault_root):
            held.append(rid)
        else:
            for h in held:  # Rollback bereits gehaltener
                release(h, worker_id, vault_root=vault_root)
            return False
    return True


# ── BL-486 F1-FIX: release_all (machine-globale Crash-Recovery-Governance) ───
def release_all(vault_root: Optional[Path] = None) -> List[str]:
    """Release ALL held resource-locks (machine-global Crash-Recovery governance).

    Zweck (DoD-14 F1): nach einem Crash/Neustart koennen verwaiste res__-Locks
    deadlocken (kein Owner mehr da, non-stale -> un-acquirable). release_all() ist
    der machine-globale Recovery-Befehl: er iteriert ALLE res__*.lock-Dirs im
    .locks-Root und gibt jeden via fl.force_release_bl UNCONDITIONAL frei (kein
    Owner-Check — Crash-Recovery). Gibt die Liste der freigegebenen resource_ids
    (dekodiert via _fs_unsafe, ORIGINAL-ids) zurueck. Idempotent: leerer Glob -> [].

    GLOB-SCOPE: das Pattern 'res__*.lock' matcht NUR Ressourcen-Locks. Es matcht
    NICHT 'rescoord__*.lock' (Region-Koordinations-Mutex, anderes Prefix — 'res__'
    verlangt '__' an Position 4, 'rescoord' hat dort 'co'). regclaims__-Dateien
    sind .txt (kein .lock) -> ebenfalls ausserhalb des Globs.

    CIRCULAR-IMPORT-VERBOT (Blueprint 2.3, LOAD-BEARING): nutzt AUSSCHLIESSLICH
    factory_lock-Primitive (fl.force_release_bl, fl._bl_locks_root) + _fs_unsafe.
    KEIN resource_allocator-Import (ra importiert srr -> Rueck-Import = Circular).
    teardown-hooks sind resource_allocator-Territorium, F1-DoD verlangt sie nicht.
    """
    locks_root = fl._bl_locks_root(_vault_root(vault_root))  # DT-13 helper (DRY, identisch zu render/_claims_path)
    released: List[str] = []
    if not locks_root.exists():
        return released
    for lock_dir in locks_root.glob(f"{RESOURCE_LOCK_PREFIX}*.lock"):
        bl_id = lock_dir.name[:-len(".lock")]              # strip '.lock'-Suffix
        resource_id = _fs_unsafe(bl_id[len(RESOURCE_LOCK_PREFIX):])  # strip 'res__'-Prefix + dekodiere
        fl.force_release_bl(bl_id, vault_root=vault_root)  # UNCONDITIONAL, idempotent
        released.append(resource_id)
    return released


# ── AK-9: lookup_free (Plan-Zeit-API fuer stagePlanner) ──────────────────────
def lookup_free(
    resource_ids: List[str],
    vault_root: Optional[Path] = None,
) -> Dict[str, str]:
    """Read the LIVE .locks/-state (NIE die .md, SOA-1-Mitigation). Returns
    {resource_id: 'FREE'|'LOCKED'}. Ein non-stale belegter Lock = LOCKED;
    fehlend ODER stale = FREE (acquirebar). Plan-Zeit-Input fuer BL-318-soft-defer."""
    states: Dict[str, str] = {}
    for rid in resource_ids:
        res_id = _res_bl_id(rid)
        lock_dir = fl._bl_lock_dir(res_id, vault_root=vault_root)
        # LOCKED gdw lock_dir existiert UND nicht stale (sonst FREE/reclaimbar).
        # Stale-Schwelle = die Lock-eigene ttl (res_ttl.txt, BL-352-(b)), Fallback
        # factory_locks Default — sonst lese ein kurzlebiger Lock faelschlich LOCKED.
        if lock_dir.exists() and not fl.is_bl_stale(
            res_id, timeout=_lock_ttl(lock_dir, fl.BL_LOCK_STALE_SECONDS),
            vault_root=vault_root,
        ):
            states[rid] = "LOCKED"
        else:
            states[rid] = "FREE"
    return states


# ── AK-1 / AK-11: render (.md-Spiegel aus .locks/-Zustand) ───────────────────
def render(
    resource_ids: List[str],
    vault_root: Optional[Path] = None,
) -> Path:
    """(Re-)build {VAULT}/_resource_availability.md aus dem .locks/-Zustand.

    Pro resource_id ein Eintrag {status, locked_by:{bl_id,run_id}, since}:
      status   <- lock_dir-Existenz + is_bl_stale
      since    <- started.txt
      run_id   <- worktree.txt  (default cwd, C7/AK-11)
      bl_id    <- aus phase.txt 'res:{bl}' geparst  (acquirendes BL)
    format_version Top-Level-Stempel (FormatVersion-DualRead). Datei-Format =
    _factory_lock.md-Vorbild (YAML-Frontmatter + Markdown-Log). Returns Pfad."""
    root = _vault_root(vault_root)
    out_path = root / RENDER_FILE_NAME

    lines = [
        "---",
        f"format_version: \"{FORMAT_VERSION}\"",
        "type: resource_availability",
        "feature: BL-247",
        "---",
        "",
        "# Resource Availability",
        "",
    ]

    for rid in resource_ids:
        res_id = _res_bl_id(rid)
        lock_dir = fl._bl_lock_dir(res_id, vault_root=vault_root)
        # Stale-Schwelle = Lock-eigene ttl (res_ttl.txt, BL-352-(b)), Default-Fallback.
        is_locked = lock_dir.exists() and not fl.is_bl_stale(
            res_id, timeout=_lock_ttl(lock_dir, fl.BL_LOCK_STALE_SECONDS),
            vault_root=vault_root,
        )

        status = "LOCKED" if is_locked else "FREE"
        since = ""
        run_id = ""
        bl_id = ""
        if is_locked:
            since = _read_lock_file(lock_dir, "started.txt")
            run_id = _read_lock_file(lock_dir, "worktree.txt")  # AK-11
            phase = _read_lock_file(lock_dir, "phase.txt")
            if phase.startswith("res:"):
                bl_id = phase[len("res:"):]

        lines.append(f"## {rid}")
        lines.append(f"- status: {status}")
        if is_locked:
            lines.append(f"- locked_by:")
            lines.append(f"    - bl_id: {bl_id or 'null'}")
            lines.append(f"    - run_id: {run_id}")
            lines.append(f"- since: {since}")
        else:
            lines.append(f"- locked_by: null")
            lines.append(f"- since: null")
        lines.append("")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out_path


def _read_lock_file(lock_dir: Path, fname: str) -> str:
    """Read one metadata file from a lock dir, '' if missing/unreadable."""
    try:
        return (lock_dir / fname).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


# ═══════════════════════════════════════════════════════════════════════════════
# REGION-LOCK (BL-247-Erweiterung, BL-353 §15/§17 — line-range-claim)
# ───────────────────────────────────────────────────────────────────────────────
# Cheap-Unit des Schneide-Modells: zwei Worker duerfen DISJUNKTE Zeilen-Bereiche
# DERSELBEN Ressource gleichzeitig halten; UEBERLAPPENDE kollidieren. Self-adaptiv:
# whole-file-Claim (start=0, end=WHOLE_FILE_END=-1 = unendlich) kollidiert mit allem
# -> kollabiert auf File-Lock (god-file). Halb-offene Intervalle [start, end).
#
# Mechanik (thin, AK-R3): EIN transienter Koordinations-Mutex (factory_lock, brief
# gehalten, stale-reclaimbar) serialisiert das Read-Check-Write der Claims; die Claims
# selbst leben in EINER Datei pro Ressource (regclaims__{fs_safe(id)}.txt, je Zeile
# 'start end worker ts ttl'). KEINE eigene Lock-Semantik — der Mutex ist factory_lock,
# Stale-Claims werden ts/ttl-basiert beim Read verworfen (AK-R3 res_ttl-Schwester).
# Plan-Optimismus: die ECHTE Kollision faengt das merge-Hunk-Verify am Fan-In (AK-R4).
WHOLE_FILE_END = -1                  # end-Sentinel: ganze Datei (unendlich)
REGION_COORD_PREFIX = "rescoord__"   # transienter Koordinations-Mutex je Ressource
REGION_CLAIMS_PREFIX = "regclaims__" # Claims-Datei je Ressource (im locks_root)
REGION_COORD_TTL = 30                # Mutex nur transient gehalten; 30s = Crash-Safety

_Claim = Tuple[int, int, str, float, int]  # (start, end, worker, ts, ttl)


def _claims_path(resource_id: str, vault_root: Optional[Path]) -> Path:
    root = fl._bl_locks_root(_vault_root(vault_root))
    return root / f"{REGION_CLAIMS_PREFIX}{_fs_safe(resource_id)}.txt"


def _read_claims(resource_id: str, vault_root: Optional[Path]) -> List[_Claim]:
    """Read all region-claims for a resource ('' if file missing). Robust per line."""
    claims: List[_Claim] = []
    try:
        text = _claims_path(resource_id, vault_root).read_text(encoding="utf-8")
    except OSError:
        return claims
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 5:
            continue  # robust gegen Teilzeilen
        try:
            claims.append((int(parts[0]), int(parts[1]), parts[2],
                           float(parts[3]), int(parts[4])))
        except ValueError:
            continue
    return claims


def _write_claims(resource_id: str, claims: List[_Claim], vault_root: Optional[Path]) -> None:
    p = _claims_path(resource_id, vault_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{s} {e} {w} {ts:.3f} {ttl}" for (s, e, w, ts, ttl) in claims]
    p.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _region_overlap(a: Tuple[int, int], b: Tuple[int, int]) -> bool:
    """Half-open [start,end) overlap. end==WHOLE_FILE_END(-1) => infinity (whole file)."""
    s1, e1 = a
    s2, e2 = b
    hi1 = float("inf") if e1 == WHOLE_FILE_END else e1
    hi2 = float("inf") if e2 == WHOLE_FILE_END else e2
    return s1 < hi2 and s2 < hi1


def _claim_is_stale(claim: _Claim, now: float) -> bool:
    _, _, _, ts, ttl = claim
    return (now - ts) > ttl


def _acquire_coord(resource_id: str, worker_id: str, vault_root: Optional[Path]) -> Optional[str]:
    """Acquire the transient per-resource coordination mutex (factory_lock). Retries
    briefly; reclaims a stale coord-holder (crash mid-critical-section). Returns the
    coord key on success, None on persistent contention."""
    coord = f"{REGION_COORD_PREFIX}{_fs_safe(resource_id)}"
    for _ in range(100):
        if fl.acquire_bl(coord, worker_id, ttl=REGION_COORD_TTL,
                         phase="rescoord", vault_root=vault_root):
            return coord
        if fl.is_bl_stale(coord, timeout=REGION_COORD_TTL, vault_root=vault_root):
            _reclaim_if_stale(coord, REGION_COORD_TTL, vault_root)
        time.sleep(0.01)
    return None


def acquire_region(
    resource_id: str,
    start: int,
    end: int,
    worker_id: str,
    bl_id: str = "",
    ttl: int = 600,
    vault_root: Optional[Path] = None,
) -> bool:
    """Acquire a half-open line-range [start,end) on a resource (end=-1 = whole file).

    True if no LIVE (non-stale) claim of ANOTHER worker overlaps the range; the claim
    is then recorded/refreshed. False on overlap or coord-contention. Same worker may
    re-claim its own range (refresh). Self-adaptiv: a (0,-1) claim collides with all.
    """
    coord = _acquire_coord(resource_id, worker_id, vault_root)
    if coord is None:
        return False
    try:
        now = time.time()
        claims = _read_claims(resource_id, vault_root)
        live = [c for c in claims if not _claim_is_stale(c, now)]
        for (cs, ce, cw, _, _) in live:
            if cw == worker_id:
                continue  # own claim never blocks self
            if _region_overlap((start, end), (cs, ce)):
                if len(live) != len(claims):
                    _write_claims(resource_id, live, vault_root)  # persist de-staling
                return False
        # grant: drop prior identical-own claim, append refreshed
        live = [c for c in live if not (c[2] == worker_id and c[0] == start and c[1] == end)]
        live.append((start, end, worker_id, now, ttl))
        _write_claims(resource_id, live, vault_root)
        return True
    finally:
        fl.release_bl(coord, worker_id, vault_root=vault_root)


def release_region(
    resource_id: str,
    start: int,
    end: int,
    worker_id: str,
    vault_root: Optional[Path] = None,
) -> bool:
    """Release one's own region-claim [start,end). True if a matching claim was removed."""
    coord = _acquire_coord(resource_id, worker_id, vault_root)
    if coord is None:
        return False
    try:
        claims = _read_claims(resource_id, vault_root)
        kept = [c for c in claims if not (c[2] == worker_id and c[0] == start and c[1] == end)]
        _write_claims(resource_id, kept, vault_root)
        return len(kept) != len(claims)
    finally:
        fl.release_bl(coord, worker_id, vault_root=vault_root)


def lookup_free_regions(
    resource_id: str,
    candidate_ranges: List[Tuple[int, int]],
    vault_root: Optional[Path] = None,
) -> Dict[Tuple[int, int], str]:
    """Plan-Zeit-API (Symmetrie zu lookup_free): welche Kandidat-[start,end)-Ranges sind
    FREE vs LOCKED auf einer Ressource. Liest die LIVE (non-stale) Claims (SOA-1, NIE die
    .md). Ein Kandidat ist LOCKED gdw er eine live Claim ueberlappt (egal welcher Worker);
    stale Claims zaehlen NICHT. Read-only -> kein coord-Mutex (wie lookup_free; advisory,
    der verbindliche Check passiert in acquire_region unter dem Mutex)."""
    now = time.time()
    live = [c for c in _read_claims(resource_id, vault_root) if not _claim_is_stale(c, now)]
    states: Dict[Tuple[int, int], str] = {}
    for (s, e) in candidate_ranges:
        locked = any(_region_overlap((s, e), (cs, ce)) for (cs, ce, _, _, _) in live)
        states[(s, e)] = "LOCKED" if locked else "FREE"
    return states


def fan_in_hunk_verify(
    worker_hunks: Optional[Dict[str, Dict[str, List[Tuple[int, int]]]]],
) -> List[Dict[str, Any]]:
    """AK-R4 Retirement-Netz: pessimistischer merge-Hunk-Verify am Fan-In.

    Der Region-Claim (acquire_region) ist PLAN-OPTIMISMUS. Diese Funktion prueft am
    Fan-In die TATSAECHLICH beruehrten Hunks (Zeilen-Ranges) ALLER Worker erneut und
    faengt Cross-Worker-Kollisionen, die der Plan-Claim verfehlte (Optimistic->
    Pessimistic-Kette). Reine, deterministische Funktion — nutzt dasselbe half-open
    Overlap wie der Region-Lock (end=-1 = ganze Datei).

    worker_hunks: {worker_id: {file_path: [(start, end), ...]}}.
    Returns: Liste von Konflikten [{file, worker_a, worker_b, range_a, range_b}]
    (deterministisch sortiert). Leere Liste = sauberer Merge. Eigene Hunks eines Workers
    kollidieren NIE mit sich selbst (nur Cross-Worker zaehlt). None/leer-tolerant.
    """
    # pro Datei sammeln: [(worker, (start,end)), ...]
    by_file: Dict[str, List[Tuple[str, Tuple[int, int]]]] = {}
    for worker, files in (worker_hunks or {}).items():
        for f, ranges in (files or {}).items():
            for r in (ranges or []):
                by_file.setdefault(f, []).append((worker, (int(r[0]), int(r[1]))))

    conflicts: List[Dict[str, Any]] = []
    for f in sorted(by_file):
        entries = by_file[f]
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                wa, ra = entries[i]
                wb, rb = entries[j]
                if wa == wb:
                    continue  # eigene Hunks blocken self nicht
                if _region_overlap(ra, rb):
                    conflicts.append({
                        "file": f, "worker_a": wa, "worker_b": wb,
                        "range_a": list(ra), "range_b": list(rb),
                    })
    return conflicts
