"""
test_resource_allocator.py — BL-368 batch_2: Tests fuer resource_allocator.py (Lease-Verb)

TDD-RED: Alle Tests erwarten ModuleNotFoundError fuer resource_allocator.py (existiert noch nicht).
KEIN Produktiv-Code in dieser Datei (GREEN-Worker separiert, INV-BUILD-GRAIN).

Fassaden-API (THIN, delegierend):
  lease(resource_id, *, ttl=600, worker_id, vault_root) -> bool
    Delegiert an stage_resource_registry.acquire(resource_id, worker_id=..., ttl=..., vault_root=...)
    Claim mit expliziter TTL; schreibt res_ttl.txt-Sidecar (geerbt via srr.acquire).

  renew(resource_id, *, worker_id, vault_root) -> bool
    Delegiert an factory_lock.heartbeat_bl(bl_id=srr._res_bl_id(resource_id), worker_id=..., vault_root=...)
    Heartbeat-Verlaengerung des bestehenden Lease-Locks.

Signaturen-Ableitung:
  stage_resource_registry.acquire(resource_id, worker_id, bl_id="", ttl=600, vault_root=None) -> bool
  factory_lock.heartbeat_bl(bl_id, worker_id, vault_root=None) -> bool
  srr._res_bl_id(resource_id) -> str  (interne Konvention: "res__" + _fs_safe(resource_id))

Delegation = THIN: resource_allocator erfindet KEINE eigene Lock-Semantik.

Run (aus Repo-Root):
  py -3 -m pytest .claude/scripts/test_resource_allocator.py -q
"""

import sys
import time
from pathlib import Path

import pytest

# Add scripts dir to path (selbe Konvention wie test_stage_resource_registry.py)
sys.path.insert(0, str(Path(__file__).parent))

import factory_lock as fl
import stage_resource_registry as srr

# NEU — existiert noch nicht => RED (ModuleNotFoundError) bis GREEN-Worker baut
import resource_allocator as ra


@pytest.fixture
def tmp_vault(tmp_path):
    """Isolierter vault_root unter tmp_path — .locks/ entsteht dort."""
    return tmp_path


@pytest.fixture(autouse=True)
def patch_vault(tmp_vault, monkeypatch):
    """Patch VAULT_ROOT + no-op _emit_audit -> echtes .locks/ und audit.jsonl unberuehrt."""
    monkeypatch.setattr(fl, "VAULT_ROOT", tmp_vault)
    monkeypatch.setattr(fl, "_emit_audit", lambda *a, **kw: None)
    yield


# ─── T-a1: Lease-Auto-Expiry + Reclaim durch zweiten Worker ─────────────────

def test_lease_auto_expiry_allows_reclaim(tmp_vault):
    """AK-LEASE-PL-1 (T-a1): ein Lease mit kleiner ttl (ttl=1) ist nach Ablauf stale
    -> ein zweiter lease() desselben resource_id durch anderen worker gelingt (Reclaim).

    Prueft das Sidecar-Stale-Reclaim (res_ttl.txt) via die Fassaden-Methode lease().
    Der Reclaim delegiert an srr.acquire -> factory_lock (kein Eigen-rmtree in ra).
    """
    # Erster Lease: kurze TTL
    result = ra.lease("res_expiry", ttl=1, worker_id="worker-a", vault_root=tmp_vault)
    assert result is True, "Erster lease() auf freier Ressource soll True liefern"

    # Lock-Dir und res_ttl.txt pruefen (Sidecar-Nicht-Regression)
    res_bl_id = srr._res_bl_id("res_expiry")
    lock_dir = fl._bl_lock_dir(res_bl_id, vault_root=tmp_vault)
    assert lock_dir.exists(), "Lock-Dir soll nach lease() existieren"
    res_ttl_file = lock_dir / "res_ttl.txt"
    assert res_ttl_file.exists(), "res_ttl.txt Sidecar soll von lease() geschrieben worden sein"
    assert res_ttl_file.read_text(encoding="utf-8").strip() == "1", (
        "res_ttl.txt soll die erzeugende ttl (1) enthalten"
    )

    # Warten bis Lease stale ist
    time.sleep(2)

    # Zweiter lease durch anderen Worker -> Reclaim -> True
    result2 = ra.lease("res_expiry", ttl=300, worker_id="worker-b", vault_root=tmp_vault)
    assert result2 is True, (
        "Nach Ablauf der ttl soll lease() durch anderen Worker True (Reclaim) liefern"
    )
    # Eigentuemer hat gewechselt
    owner = (lock_dir / "owner.txt").read_text(encoding="utf-8").strip()
    assert owner == "worker-b", (
        f"Owner nach Reclaim soll worker-b sein, ist {owner!r}"
    )


# ─── T-a2: Heartbeat-Renew haelt Lock frisch ─────────────────────────────────

def test_heartbeat_renew_keeps_lock_fresh(tmp_vault):
    """AK-LEASE-PL-1 (T-a2): renew() aktualisiert heartbeat -> Lock bleibt nicht-stale.

    Strategie: lease mit grosser ttl, renew aufrufen, is_bl_stale pruefen -> False.
    Prueft dass renew() korrekt an factory_lock.heartbeat_bl delegiert.
    """
    res_id = "res_heartbeat"
    res_bl_id = srr._res_bl_id(res_id)

    assert ra.lease(res_id, ttl=600, worker_id="worker-c", vault_root=tmp_vault) is True

    # renew aufrufen
    result = ra.renew(res_id, worker_id="worker-c", vault_root=tmp_vault)
    assert result is True, "renew() soll True liefern wenn worker der Owner ist"

    # Nach renew: Lock nicht stale (heartbeat aktuell)
    assert fl.is_bl_stale(res_bl_id, timeout=600, vault_root=tmp_vault) is False, (
        "Lock soll nach renew() nicht stale sein"
    )


# ─── T-a3: res_ttl-Sidecar Nicht-Regression ─────────────────────────────────

def test_res_ttl_sidecar_persisted_by_lease(tmp_vault):
    """AK-LEASE-PL-1 (T-a3): res_ttl.txt wird von lease() im Lock-Dir persistiert.

    Nicht-Regression: die erzeugende ttl MUSS via Sidecar gespeichert werden, damit
    ein späterer Acquirer die Lock-eigene Stale-Schwelle kennt (BL-352-(b)).
    lease() ist THIN — der Sidecar-Write ist Verhalten von srr.acquire, das lease()
    delegiert; dieser Test stellt sicher dass die Delegation korrekt verdrahtet ist.
    """
    custom_ttl = 42
    resource_id = "res_sidecar"
    res_bl_id = srr._res_bl_id(resource_id)
    lock_dir = fl._bl_lock_dir(res_bl_id, vault_root=tmp_vault)

    result = ra.lease(resource_id, ttl=custom_ttl, worker_id="worker-d", vault_root=tmp_vault)
    assert result is True

    # res_ttl.txt muss existieren und die korrekte ttl enthalten
    res_ttl_path = lock_dir / "res_ttl.txt"
    assert res_ttl_path.exists(), (
        "res_ttl.txt Sidecar muss von lease() (via srr.acquire) im Lock-Dir angelegt werden"
    )
    persisted_ttl = int(res_ttl_path.read_text(encoding="utf-8").strip())
    assert persisted_ttl == custom_ttl, (
        f"res_ttl.txt soll die erzeugende ttl ({custom_ttl}) enthalten, "
        f"enthält aber {persisted_ttl}"
    )


# ─── T-b1: acquire_with_wait blockt-bis-frei ─────────────────────────────────

def test_acquire_with_wait_blocks_until_free(tmp_vault, monkeypatch):
    """AK-WAIT-PL-1 (T-b1): Ressource zunaechst von worker_A gehalten;
    srr.acquire liefert beim N-ten Versuch True -> acquire_with_wait von
    worker_B liefert True (warte-loop-Mechanik, deterministisch+schnell).

    Strategie: monkeypatch time.sleep -> no-op; monkeypatch srr.acquire mit
    einem Zaehler-Side-Effect [False, False, True] -> acquire_with_wait
    erkennt beim dritten Versuch 'frei' und gibt True zurueck.
    """
    call_count = {"n": 0}
    acquire_results = [False, False, True]

    def fake_acquire(resource_id, worker_id, bl_id="", ttl=600, vault_root=None):
        result = acquire_results[min(call_count["n"], len(acquire_results) - 1)]
        call_count["n"] += 1
        return result

    monkeypatch.setattr(srr, "acquire", fake_acquire)
    monkeypatch.setattr("time.sleep", lambda s: None)

    result = ra.acquire_with_wait(
        "res_wait_free",
        worker_id="worker-b",
        ttl=600,
        timeout=60,
        vault_root=tmp_vault,
    )
    assert result is True, (
        "acquire_with_wait soll True liefern wenn srr.acquire beim dritten Versuch True gibt"
    )
    assert call_count["n"] >= 3, (
        f"srr.acquire soll mindestens 3x aufgerufen werden (Retry-Loop), war {call_count['n']}x"
    )


# ─── T-b2: acquire_with_wait blockt-bis-timeout ───────────────────────────────

def test_acquire_with_wait_returns_false_on_timeout(tmp_vault, monkeypatch):
    """AK-WAIT-PL-1 (T-b2): Ressource bleibt belegt (srr.acquire immer False)
    -> acquire_with_wait liefert nach Erschoepfen des Backoff/timeout False.
    Kein Haengen; time.sleep gemockt.

    Strategie: srr.acquire gibt immer False; time.sleep ist no-op;
    timeout=5 (kleiner als Summe der Backoff-Schritte, damit der Loop
    deterministisch abbricht). Ergebnis muss False sein.
    """
    monkeypatch.setattr(srr, "acquire", lambda *a, **kw: False)
    monkeypatch.setattr("time.sleep", lambda s: None)

    result = ra.acquire_with_wait(
        "res_timeout",
        worker_id="worker-c",
        ttl=600,
        timeout=5,
        vault_root=tmp_vault,
    )
    assert result is False, (
        "acquire_with_wait soll False liefern wenn srr.acquire immer False gibt (timeout)"
    )


# ─── T-b3: Backoff-Schritte respektiert ──────────────────────────────────────

def test_acquire_with_wait_respects_backoff_sequence(tmp_vault, monkeypatch):
    """AK-WAIT-PL-1 (T-b3): die Schlaf-Intervalle folgen der Backoff-Sequenz
    [1,2,4,8,30] (factory_lock.py:233). Capture die an time.sleep uebergebenen
    Werte via monkeypatch-Recorder und pruefe Reihenfolge/Werte.

    Strategie: srr.acquire immer False; time.sleep wird ersetzt durch einen
    Recorder der alle Sleep-Werte sammelt; timeout gross genug, damit alle
    5 Backoff-Stufen durchlaufen werden. Danach pruefe dass die ersten 5
    sleep-Aufrufe genau [1,2,4,8,30] (oder prefix davon bis timeout) sind.
    """
    sleep_calls = []

    def record_sleep(seconds):
        sleep_calls.append(seconds)

    monkeypatch.setattr(srr, "acquire", lambda *a, **kw: False)
    monkeypatch.setattr("time.sleep", record_sleep)

    # timeout=0 damit der Loop sofort nach einem Durchgang abbricht,
    # aber wir brauchen genug timeout fuer mindestens 5 Schritte:
    # Summe [1+2+4+8+30]=45 -> timeout=50, aber sleep ist no-op-artig
    # (Recorder+Aufruf), so bleibt der Loop durch die monotonic-Zeit = 0-nahe,
    # und bricht nur wenn elapsed>=timeout. Mit monkeypatched sleep=0-Zeit
    # und timeout=0 bricht er sofort. Darum: timeout=100 damit alle 5 Stufen laufen.
    ra.acquire_with_wait(
        "res_backoff",
        worker_id="worker-d",
        ttl=600,
        timeout=100,
        backoff=[1, 2, 4, 8, 30],
        vault_root=tmp_vault,
    )

    # Mindestens 5 Schlaf-Aufrufe (alle Backoff-Stufen) sollten gelogt sein
    assert len(sleep_calls) >= 5, (
        f"Erwarte mindestens 5 sleep-Aufrufe (Backoff [1,2,4,8,30]), "
        f"erhalten: {sleep_calls}"
    )
    # Die ersten 5 Werte muessen der Backoff-Sequenz entsprechen
    assert sleep_calls[:5] == [1, 2, 4, 8, 30], (
        f"Die ersten 5 sleep-Werte sollen [1,2,4,8,30] sein, sind: {sleep_calls[:5]}"
    )


# ─── T-b4: per-resource-timeout-override bricht frueher ab ───────────────────

def test_acquire_with_wait_per_call_timeout_override(tmp_vault, monkeypatch):
    """AK-WAIT-PL-1 (T-b4): ein explizit kleineres timeout-Arg bricht frueher
    ab (weniger Backoff-Schritte als Default timeout=60).

    Strategie: srr.acquire immer False; time.sleep Recorder; erst mit
    timeout=100 (alle Backoff-Stufen) dann mit timeout=3 (nur backoff[0]=1
    passt noch rein, backoff[1]=2 nicht mehr -> weniger Schritte). Pruefe
    dass die Anzahl der sleep-Calls bei timeout=3 kleiner ist als bei timeout=100.
    """
    sleep_calls_long = []
    sleep_calls_short = []

    def record_sleep_long(s):
        sleep_calls_long.append(s)

    def record_sleep_short(s):
        sleep_calls_short.append(s)

    monkeypatch.setattr(srr, "acquire", lambda *a, **kw: False)

    # Lauf 1: grosses timeout -> viele Backoff-Schritte
    monkeypatch.setattr("time.sleep", record_sleep_long)
    ra.acquire_with_wait(
        "res_override_long",
        worker_id="worker-e",
        ttl=600,
        timeout=100,
        backoff=[1, 2, 4, 8, 30],
        vault_root=tmp_vault,
    )

    # Lauf 2: kleines timeout -> weniger Schritte
    monkeypatch.setattr("time.sleep", record_sleep_short)
    ra.acquire_with_wait(
        "res_override_short",
        worker_id="worker-f",
        ttl=600,
        timeout=3,
        backoff=[1, 2, 4, 8, 30],
        vault_root=tmp_vault,
    )

    assert len(sleep_calls_short) < len(sleep_calls_long), (
        f"Kleineres timeout soll weniger sleep-Aufrufe erzeugen: "
        f"short={len(sleep_calls_short)}, long={len(sleep_calls_long)}"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BL-368 batch_4: AK-ALLOCATOR-PL-1 — claim/release/acquire_all (RED-Worker)
# Signaturen gespiegelt von stage_resource_registry:
#   srr.acquire(resource_id, worker_id, bl_id="", ttl=600, vault_root=None) -> bool
#   srr.release(resource_id, worker_id, vault_root=None) -> bool
#   srr.acquire_all(resource_ids, worker_id, bl_id="", ttl=600, vault_root=None) -> bool
# ═══════════════════════════════════════════════════════════════════════════════

# ─── T-c1: claim auf freier Ressource -> True ────────────────────────────────

def test_claim_free_returns_true(tmp_vault):
    """AK-ALLOCATOR-PL-1 (T-c1): claim() auf FREIer Ressource liefert True.

    claim() ist non-blocking single-attempt: delegates to srr.acquire;
    freie Ressource -> sofortiger True ohne Retry-Loop.
    """
    result = ra.claim("res_claim_free", worker_id="worker-x", ttl=600, vault_root=tmp_vault)
    assert result is True, "claim() auf freier Ressource soll True liefern"


# ─── T-c2: claim auf belegter Ressource (anderer Owner) -> False ──────────────

def test_claim_held_by_other_returns_false(tmp_vault):
    """AK-ALLOCATOR-PL-1 (T-c2): claim() non-blocking — worker_B erhaelt False
    wenn worker_A die Ressource haelt (kein Wait, kein Retry).

    Unterschied zu acquire_with_wait: claim() versucht exakt EINMAL.
    """
    # worker_A haelt die Ressource
    assert ra.claim("res_claim_held", worker_id="worker-a", ttl=600, vault_root=tmp_vault) is True
    # worker_B claim -> False, kein Haengen
    result = ra.claim("res_claim_held", worker_id="worker-b", ttl=600, vault_root=tmp_vault)
    assert result is False, (
        "claim() soll False liefern wenn Ressource von anderem Worker gehalten wird"
    )


# ─── T-c3: release durch Owner -> Ressource wieder claimbar ─────────────────

def test_release_owner_frees_resource(tmp_vault):
    """AK-ALLOCATOR-PL-1 (T-c3): release() durch den Owner gibt Ressource frei;
    danach ist claim() durch einen anderen Worker wieder True.

    Prueft: owner-gated FREE via srr.release-Delegation.
    """
    resource_id = "res_release_owner"
    # worker_A claimed
    assert ra.claim(resource_id, worker_id="worker-a", ttl=600, vault_root=tmp_vault) is True
    # release durch owner
    released = ra.release(resource_id, worker_id="worker-a", vault_root=tmp_vault)
    assert released is True, "release() durch Owner soll True liefern"
    # danach: worker_B kann claimen
    result = ra.claim(resource_id, worker_id="worker-b", ttl=600, vault_root=tmp_vault)
    assert result is True, "Nach release() durch Owner soll claim() eines anderen Workers True liefern"


# ─── T-c4: acquire_all partial-fail -> Rollback (andere Ressourcen frei) ──────

def test_acquire_all_partial_fail_rollback(tmp_vault):
    """AK-ALLOCATOR-PL-1 (T-c4): acquire_all() bei partial-fail -> False UND
    die bereits geholten Ressourcen werden zurueckgegeben (Rollback).

    Setup: res_c4_a ist frei, res_c4_b ist von worker-blocker belegt.
    acquire_all(["res_c4_a", "res_c4_b"], worker_id="worker-z") soll False liefern
    und res_c4_a danach wieder frei claimbar sein (Rollback-Beweis).
    """
    # Vorbelegen: res_c4_b von anderem Worker halten
    assert srr.acquire("res_c4_b", "worker-blocker", vault_root=tmp_vault) is True

    result = ra.acquire_all(
        ["res_c4_a", "res_c4_b"],
        worker_id="worker-z",
        ttl=600,
        vault_root=tmp_vault,
    )
    assert result is False, "acquire_all() soll False liefern wenn eine Ressource belegt ist"

    # Rollback-Beweis: res_c4_a soll wieder frei claimbar sein (nicht dauerhaft gehalten)
    free_again = ra.claim("res_c4_a", worker_id="worker-check", ttl=600, vault_root=tmp_vault)
    assert free_again is True, (
        "Nach partial-fail Rollback soll die nicht-belegte Ressource (res_c4_a) "
        "wieder frei claimbar sein"
    )


# ─── T-c5: Delegations-grep — THIN-DoD (keine eigene Lock-Semantik) ──────────

def test_claim_release_acquire_all_thin_no_own_lock_semantics():
    """AK-ALLOCATOR-PL-1 (T-c5): Beweist THIN-DoD — resource_allocator.py enthaelt
    KEINE eigene Lock-Semantik (kein mkdir, os.replace, _robust_rmtree, shutil.rmtree)
    in Nicht-Kommentar-Zeilen.

    Liest den Quelltext von resource_allocator.py und prueft alle
    Code-Zeilen (Kommentar-Zeilen und Docstring-Zeilen ausgenommen).
    """
    src_path = Path(__file__).parent / "resource_allocator.py"
    src_text = src_path.read_text(encoding="utf-8")

    forbidden_patterns = ["mkdir", "os.replace", "_robust_rmtree", "shutil.rmtree"]
    code_lines = []
    in_docstring = False
    docstring_char = None

    for line in src_text.splitlines():
        stripped = line.strip()
        # Skip blank lines
        if not stripped:
            continue
        # Docstring-Toggle: einfacher Heuristik (triple-quote open/close)
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                # Single-line docstring (open+close auf gleicher Zeile)?
                rest = stripped[3:]
                if docstring_char in rest:
                    continue  # vollstaendige Single-Line Docstring -> Skip
                in_docstring = True
                continue
            # Inline-Kommentar-Zeile
            if stripped.startswith("#"):
                continue
            code_lines.append(line)
        else:
            # In docstring: warte auf schliessende triple-quote
            if docstring_char and docstring_char in stripped:
                in_docstring = False
            continue

    violations = []
    for code_line in code_lines:
        # Entferne Inline-Kommentar-Teil (nach erstem #, ausser in Strings — vereinfacht)
        code_part = code_line.split("#")[0]
        for pat in forbidden_patterns:
            if pat in code_part:
                violations.append(f"  '{pat}' in: {code_line.rstrip()}")

    assert not violations, (
        "resource_allocator.py enthaelt verbotene Lock-Semantik-Konstrukte "
        f"(THIN-DoD verletzt):\n" + "\n".join(violations)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BL-368 batch_5: AK-HANDSHAKE-PL-1 — last-release Teardown-Hook (RED-Worker)
#
# Neue API: register_teardown_hook(resource_id, callback) -> None
#   Registriert callback, das beim LAST-RELEASE der Ressource GENAU-mind-EINMAL
#   feuert. at-least-once-Garantie ist BL-368s Job; Idempotenz des callbacks
#   ist Sache des Consumers (BL-408), nicht hier.
#
# Drei Trigger-Pfade:
#   Pfad 1: normaler release() -> Hook feuert genau einmal
#   Pfad 2: Lease-Expiry/Stale-Reclaim -> Reclaimer feuert Teardown BEVOR
#            naechster Claimer den Lock erhaelt (Ordnungs-Invariante)
#   Pfad 3: force-clear (kommt T7, hier nur Hook-Punkt vorbereiten)
# ═══════════════════════════════════════════════════════════════════════════════

# ─── T-d1: release -> Hook genau einmal ──────────────────────────────────────

def test_teardown_hook_fires_once_on_release(tmp_vault):
    """AK-HANDSHAKE-PL-1 (T-d1): register_teardown_hook + normaler release()
    -> callback wird GENAU einmal aufgerufen, mit resource_id als Argument.

    Spy-Strategie: callback haengt (resource_id,) an eine Liste; nach release()
    pruefe len==1 und korrekter resource_id.
    """
    fired = []

    def spy_callback(resource_id):
        fired.append(resource_id)

    resource_id = "res_hook_release"

    assert ra.claim(resource_id, worker_id="worker-hook-a", ttl=600, vault_root=tmp_vault) is True
    ra.register_teardown_hook(resource_id, spy_callback)

    ra.release(resource_id, worker_id="worker-hook-a", vault_root=tmp_vault)

    assert len(fired) == 1, (
        f"Teardown-Hook soll genau einmal nach release() feuern, feuerte {len(fired)}x"
    )
    assert fired[0] == resource_id, (
        f"Teardown-Hook soll mit resource_id='{resource_id}' aufgerufen werden, "
        f"erhielt '{fired[0]}'"
    )


# ─── T-d2: Lease-Expiry-Reclaim -> Hook VOR naechstem Claim ──────────────────

def test_teardown_hook_fires_before_reclaimer_acquires(tmp_vault):
    """AK-HANDSHAKE-PL-1 (T-d2): Lease-Expiry-Reclaim -> Teardown-Hook feuert
    BEVOR der naechste Worker den Lock erhaelt (Ordnungs-Invariante).

    Strategie: worker_A claim mit ttl=1; register_teardown_hook; kurz warten
    bis stale; worker_B lease() loest Stale-Reclaim aus -> Hook muss vor
    dem erfolgreichen B-acquire gefeuert haben.

    Zeitstempel-Spy: callback haengt monotonic-Timestamp an 'hook_times';
    B-acquire-Erfolg wird mit 'acquire_times' verglichen.
    Pruefe: hook_times[0] <= acquire_times[0] (Hook feuert nicht nach B-acquire).

    Timing gespiegelt von test_lease_auto_expiry_allows_reclaim (T-a1):
    ttl=1 + time.sleep(2) fuer deterministischen Stale-Zustand.
    """
    hook_times = []
    acquire_times = []

    def spy_callback(resource_id):
        hook_times.append(time.monotonic())

    resource_id = "res_hook_reclaim"

    # worker_A: kurze ttl
    assert ra.lease(resource_id, ttl=1, worker_id="worker-a-hook", vault_root=tmp_vault) is True
    ra.register_teardown_hook(resource_id, spy_callback)

    # Warten bis stale (wie T-a1)
    time.sleep(2)

    # worker_B lease() loest Stale-Reclaim aus; Hook soll VOR B-acquire feuern
    result = ra.lease(resource_id, ttl=300, worker_id="worker-b-hook", vault_root=tmp_vault)
    acquire_times.append(time.monotonic())

    assert result is True, "worker_B lease() nach Stale soll True (Reclaim) liefern"
    assert len(hook_times) >= 1, (
        "Teardown-Hook soll beim Stale-Reclaim gefeuert haben (bevor worker_B den Lock haelt)"
    )
    assert hook_times[0] <= acquire_times[0], (
        f"Hook-Timestamp ({hook_times[0]:.6f}) muss <= B-acquire-Timestamp "
        f"({acquire_times[0]:.6f}) sein (Hook vor Reclaim-Abschluss)"
    )


# ─── T-d3: at-least-once — doppeltes release feuert Hook nicht 0x ─────────────

def test_teardown_hook_at_least_once_on_double_release(tmp_vault):
    """AK-HANDSHAKE-PL-1 (T-d3): doppeltes release() (oder release nach bereits
    frei) fuehrt dazu dass der Hook >= 1x gefeuert wurde — NICHT 0x.

    at-least-once-Semantik: das erste release gibt den Lock frei + feuert den Hook;
    das zweite release ist ein no-op (kein Owner mehr), darf den Hook NICHT auf 0
    ruecksetzen. Gesamtzahl >= 1 nach beiden release()-Aufrufen.

    Prueft: len(fired) >= 1 nach claim + hook + release + release.
    """
    fired = []

    def spy_callback(resource_id):
        fired.append(resource_id)

    resource_id = "res_hook_double_release"

    assert ra.claim(resource_id, worker_id="worker-d3-a", ttl=600, vault_root=tmp_vault) is True
    ra.register_teardown_hook(resource_id, spy_callback)

    # Erstes release: gibt frei + feuert Hook
    ra.release(resource_id, worker_id="worker-d3-a", vault_root=tmp_vault)
    # Zweites release: kein Owner mehr -> no-op; Hook NICHT auf 0 ruecksetzen
    ra.release(resource_id, worker_id="worker-d3-a", vault_root=tmp_vault)

    assert len(fired) >= 1, (
        f"at-least-once: Hook soll nach claim+release+release mindestens 1x gefeuert "
        f"haben, feuerte {len(fired)}x"
    )


# ─── T-d4: last-holder — Hook nur beim LETZTEN release ───────────────────────

def test_teardown_hook_fires_only_for_actual_holder(tmp_vault):
    """AK-HANDSHAKE-PL-1 (T-d4): Ein fehlgeschlagener claim (Nicht-Owner) loest
    den Teardown-Hook NICHT aus.

    Prueft last-holder-Semantik: nur der tatsaechliche Owner kann release() +
    Hook ausloesen. Ein Nicht-Owner-release() (der Lock wird nicht freigegeben)
    darf den Hook NICHT feuern.

    Setup: worker_A haelt die Ressource; register_teardown_hook; worker_B
    versucht release() (kein Owner) -> Hook darf NICHT gefeuert haben.
    Dann worker_A release() -> Hook feuert.
    """
    fired = []

    def spy_callback(resource_id):
        fired.append(resource_id)

    resource_id = "res_hook_last_holder"

    assert ra.claim(resource_id, worker_id="worker-holder", ttl=600, vault_root=tmp_vault) is True
    ra.register_teardown_hook(resource_id, spy_callback)

    # Nicht-Owner release() -> soll False liefern UND Hook nicht feuern
    non_owner_result = ra.release(resource_id, worker_id="worker-non-owner", vault_root=tmp_vault)
    assert non_owner_result is False, "release() durch Nicht-Owner soll False liefern"
    assert len(fired) == 0, (
        f"Teardown-Hook darf nach Nicht-Owner-release() NICHT gefeuert haben, "
        f"feuerte {len(fired)}x"
    )

    # Jetzt echter Owner release() -> Hook feuert
    ra.release(resource_id, worker_id="worker-holder", vault_root=tmp_vault)
    assert len(fired) == 1, (
        f"Teardown-Hook soll nach Owner-release() genau 1x gefeuert haben, "
        f"feuerte {len(fired)}x"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BL-368 batch_6: AK-DIVISIBILITY-PL-1 — Divisibility-Routing (RED-Worker)
#
# Neue API:
#   claim_divisible(resource_id, *, worker_id, region=None, vault_root=None,
#                   divisibility=None) -> bool
#
# Routing-Vertrag:
#   unteilbar (oder None/unbekannt) -> whole-claim via srr.acquire
#   teilbar + region gegeben       -> Region-Lock via srr.acquire_region
#
# Substrat-Befunde (verifiziert):
#   srr.acquire_region(resource_id, start, end, worker_id, ...) -> bool  [EXISTIERT]
#   srr.acquire(resource_id, worker_id, ...) -> bool                     [EXISTIERT]
#   stage_resource_seam.stage_resources() -> {"divisibility": {id: "teilbar"|"unteilbar"}}
#   DEFAULT_DIVISIBILITY = "unteilbar"  (konservativ, kein False-Share)
#
# Region-Format: region = (start, end) als half-open [start, end), end=-1 = Whole-File.
# ═══════════════════════════════════════════════════════════════════════════════

# ─── T-e1: unteilbar -> whole-single-holder (zweiter Claimer blockt) ─────────

def test_claim_divisible_unteilbar_whole_claim_blocks_second(tmp_vault):
    """AK-DIVISIBILITY-PL-1 (T-e1): divisibility='unteilbar' -> whole-claim via srr.acquire;
    zweiter Claimer derselben Ressource erhaelt False (nicht teilbar, kein paralleler Zugriff).

    Prueft: 1. Claim -> True (frei); 2. Claim desselben resource_id -> False (belegt).
    Routing-Verifikation via monkeypatch-Spy: srr.acquire wird aufgerufen (NICHT srr.acquire_region).
    """
    acquire_calls = []
    acquire_region_calls = []

    real_acquire = srr.acquire
    real_acquire_region = srr.acquire_region

    def spy_acquire(resource_id, worker_id, **kwargs):
        acquire_calls.append((resource_id, worker_id))
        return real_acquire(resource_id, worker_id, **kwargs)

    def spy_acquire_region(resource_id, start, end, worker_id, **kwargs):
        acquire_region_calls.append((resource_id, start, end, worker_id))
        return real_acquire_region(resource_id, start, end, worker_id, **kwargs)

    import unittest.mock as mock
    with mock.patch.object(srr, "acquire", side_effect=spy_acquire), \
         mock.patch.object(srr, "acquire_region", side_effect=spy_acquire_region):

        # Erster Claim: soll True liefern (Ressource frei)
        result1 = ra.claim_divisible(
            "res_unteilbar_e1",
            worker_id="worker-e1-a",
            divisibility="unteilbar",
            vault_root=tmp_vault,
        )
        assert result1 is True, "Erster claim_divisible (unteilbar) auf freier Ressource soll True liefern"

        # Zweiter Claim: soll False liefern (Ressource belegt, unteilbar)
        result2 = ra.claim_divisible(
            "res_unteilbar_e1",
            worker_id="worker-e1-b",
            divisibility="unteilbar",
            vault_root=tmp_vault,
        )
        assert result2 is False, (
            "Zweiter claim_divisible (unteilbar) auf belegter Ressource soll False liefern"
        )

    # Routing-Verifikation: srr.acquire aufgerufen, NICHT srr.acquire_region
    assert len(acquire_calls) >= 1, "srr.acquire soll bei unteilbar-Routing aufgerufen werden"
    assert len(acquire_region_calls) == 0, (
        "srr.acquire_region darf bei unteilbar-Routing NICHT aufgerufen werden"
    )


# ─── T-e2: teilbar -> disjunkte Regionen parallel (beide True) ───────────────

def test_claim_divisible_teilbar_disjoint_regions_both_succeed(tmp_vault):
    """AK-DIVISIBILITY-PL-1 (T-e2): divisibility='teilbar' + DISJUNKTE Regionen
    -> beide Claims gelingen (True/True).

    Region-A: [0, 50), Region-B: [50, 100) -- keine Ueberlappung.
    Prueft: 1. Claim worker_A auf [0,50) -> True; 2. Claim worker_B auf [50,100) -> True.
    Routing-Verifikation: srr.acquire_region wird aufgerufen (NICHT srr.acquire fuer den Claim selbst).
    """
    acquire_calls = []
    acquire_region_calls = []

    real_acquire_region = srr.acquire_region

    def spy_acquire_region(resource_id, start, end, worker_id, **kwargs):
        acquire_region_calls.append((resource_id, start, end, worker_id))
        return real_acquire_region(resource_id, start, end, worker_id, **kwargs)

    import unittest.mock as mock
    with mock.patch.object(srr, "acquire_region", side_effect=spy_acquire_region):

        result1 = ra.claim_divisible(
            "res_teilbar_e2",
            worker_id="worker-e2-a",
            region=(0, 50),
            divisibility="teilbar",
            vault_root=tmp_vault,
        )
        assert result1 is True, "Erster claim_divisible (teilbar, Region [0,50)) soll True liefern"

        result2 = ra.claim_divisible(
            "res_teilbar_e2",
            worker_id="worker-e2-b",
            region=(50, 100),
            divisibility="teilbar",
            vault_root=tmp_vault,
        )
        assert result2 is True, (
            "Zweiter claim_divisible (teilbar, disjunkte Region [50,100)) soll True liefern"
        )

    # Routing-Verifikation: srr.acquire_region aufgerufen
    assert len(acquire_region_calls) == 2, (
        f"srr.acquire_region soll 2x aufgerufen worden sein (ein Aufruf je Worker), "
        f"war {len(acquire_region_calls)}x"
    )


# ─── T-e3: teilbar -> ueberlappende Regionen kollidieren (zweiter False) ──────

def test_claim_divisible_teilbar_overlapping_regions_second_fails(tmp_vault):
    """AK-DIVISIBILITY-PL-1 (T-e3): divisibility='teilbar' + UEBERLAPPENDE Regionen
    -> zweiter Claim False (Kollision).

    Region-A: [0, 60), Region-B: [40, 100) -- Ueberlappung [40, 60).
    Prueft: 1. Claim worker_A auf [0,60) -> True; 2. Claim worker_B auf [40,100) -> False.
    """
    result1 = ra.claim_divisible(
        "res_teilbar_e3",
        worker_id="worker-e3-a",
        region=(0, 60),
        divisibility="teilbar",
        vault_root=tmp_vault,
    )
    assert result1 is True, "Erster claim_divisible (teilbar, Region [0,60)) soll True liefern"

    result2 = ra.claim_divisible(
        "res_teilbar_e3",
        worker_id="worker-e3-b",
        region=(40, 100),
        divisibility="teilbar",
        vault_root=tmp_vault,
    )
    assert result2 is False, (
        "Zweiter claim_divisible (teilbar, ueberlappende Region [40,100)) soll False liefern (Kollision)"
    )


# ─── T-e4: Default (keine divisibility-Deklaration) -> unteilbar (whole-claim) ──

def test_claim_divisible_no_declaration_defaults_to_unteilbar(tmp_vault):
    """AK-DIVISIBILITY-PL-1 (T-e4): keine divisibility-Deklaration (divisibility=None)
    -> Default = unteilbar -> whole-claim via srr.acquire (konservativ, kein False-Share).

    Prueft: claim_divisible ohne divisibility-Param -> verhaelt sich wie unteilbar:
    1. erster Claim True; 2. zweiter Claimer False.
    Routing-Spy: srr.acquire wird aufgerufen (NICHT srr.acquire_region).
    """
    acquire_calls = []
    acquire_region_calls = []

    real_acquire = srr.acquire

    def spy_acquire(resource_id, worker_id, **kwargs):
        acquire_calls.append((resource_id, worker_id))
        return real_acquire(resource_id, worker_id, **kwargs)

    import unittest.mock as mock
    with mock.patch.object(srr, "acquire", side_effect=spy_acquire), \
         mock.patch.object(srr, "acquire_region", side_effect=lambda *a, **kw: acquire_region_calls.append(a) or False):

        result1 = ra.claim_divisible(
            "res_default_e4",
            worker_id="worker-e4-a",
            # divisibility=None (kein Param) -> Default unteilbar
            vault_root=tmp_vault,
        )
        assert result1 is True, "claim_divisible ohne divisibility-Deklaration soll True liefern (Ressource frei)"

        result2 = ra.claim_divisible(
            "res_default_e4",
            worker_id="worker-e4-b",
            vault_root=tmp_vault,
        )
        assert result2 is False, (
            "claim_divisible ohne divisibility-Deklaration (Default=unteilbar): "
            "zweiter Claimer soll False liefern"
        )

    # Routing-Verifikation: nur srr.acquire, kein srr.acquire_region
    assert len(acquire_calls) >= 1, "srr.acquire soll bei Default-unteilbar-Routing aufgerufen werden"
    assert len(acquire_region_calls) == 0, (
        "srr.acquire_region darf bei Default-unteilbar (kein divisibility-Param) NICHT aufgerufen werden"
    )


# ═══════════════════════════════════════════════════════════════════════════════
# BL-368 batch_7: AK-FORCE-CLEAR-PL-1 — force_clear (Crash-Recovery, Pfad 3)
#
# Neue API:
#   force_clear(resource_id, *, vault_root=None) -> bool
#
# Semantik (PRIVILEGIERT, Admin/PC):
#   - Unconditional free: bricht den gehaltenen res__-Lock OHNE Owner-Check
#   - Delegiert an factory_lock (via _res_bl_id) zur Lockdir-Entfernung
#   - Feuert _fire_teardown_hooks(resource_id) nach dem Freigeben (Pfad 3)
#   - Gibt True zurueck wenn die Ressource nun frei ist
#   - Lease-Invalidierung: danach kann jeder Worker die Ressource neu claimen
#
# Substrat-Konventionen (verifiziert):
#   srr._res_bl_id(resource_id) -> "res__" + _fs_safe(resource_id)
#   fl._bl_lock_dir(bl_id, vault_root) -> Path des Lock-Verzeichnisses
#   ra._fire_teardown_hooks(resource_id) -> feuert alle registrierten Hooks (Pfad 3)
#   ra.register_teardown_hook(resource_id, callback) -> registriert Callback
#   ra.claim(resource_id, *, worker_id, ...) -> bool
# ═══════════════════════════════════════════════════════════════════════════════

# ─── T-f1: force_clear bricht gehaltenen Lock -> Ressource ist FREE ──────────

def test_force_clear_held_lock_returns_true_and_frees_resource(tmp_vault):
    """AK-FORCE-CLEAR-PL-1 (T-f1): force_clear() auf gehaltener Ressource
    -> True; Ressource ist danach FREE (Lock-Dir weg oder Owner-los).

    Prueft: worker_A claim(); force_clear() durch "jemand anderen" (kein worker_id-
    Arg — unconditional, kein Owner-Check); Ressource danach FREE beweisbar.

    Beweis fuer FREE: Lock-Dir nicht mehr existent ODER ein neuer claim() durch
    worker_B gelingt (True). Beides beweist den freigegebenen Zustand.
    """
    resource_id = "res_force_f1"

    # worker_A haelt die Ressource
    assert ra.claim(resource_id, worker_id="worker-f1-a", ttl=600, vault_root=tmp_vault) is True

    # Verifiziere dass der Lock existiert (Vorbedingung)
    res_bl_id = srr._res_bl_id(resource_id)
    lock_dir = fl._bl_lock_dir(res_bl_id, vault_root=tmp_vault)
    assert lock_dir.exists(), "Lock-Dir muss nach claim() existieren (Vorbedingung)"

    # force_clear durch "jemand anderen" (kein worker_id = unconditional, KEIN Owner-Check)
    result = ra.force_clear(resource_id, vault_root=tmp_vault)
    assert result is True, "force_clear() auf gehaltener Ressource soll True liefern"

    # Ressource ist jetzt FREE: Lock-Dir darf nicht mehr existent sein
    assert not lock_dir.exists(), (
        "Lock-Dir muss nach force_clear() entfernt worden sein (Ressource ist FREE)"
    )


# ─── T-f2: nach force_clear kann worker_B die Ressource claimen (claimbar) ───

def test_force_clear_resource_is_claimable_afterwards(tmp_vault):
    """AK-FORCE-CLEAR-PL-1 (T-f2): nach force_clear() kann ein anderer Worker
    die Ressource sofort neu claimen (Lease-Invalidierung, claimbar).

    Setup: worker_A claim; force_clear; worker_B claim -> True.
    Prueft die Lease-Invalidierungs-Eigenschaft: force_clear macht den Lock
    frei, so dass kein anderer Worker blockiert bleibt.
    """
    resource_id = "res_force_f2"

    # worker_A haelt die Ressource
    assert ra.claim(resource_id, worker_id="worker-f2-a", ttl=600, vault_root=tmp_vault) is True

    # Vor force_clear: worker_B claim soll False liefern (belegt)
    assert ra.claim(resource_id, worker_id="worker-f2-b", ttl=600, vault_root=tmp_vault) is False, (
        "Vor force_clear soll claim() des anderen Workers False liefern (belegt)"
    )

    # force_clear (unconditional)
    fc_result = ra.force_clear(resource_id, vault_root=tmp_vault)
    assert fc_result is True, "force_clear() soll True liefern"

    # Nach force_clear: worker_B kann die Ressource claimen
    result = ra.claim(resource_id, worker_id="worker-f2-b", ttl=600, vault_root=tmp_vault)
    assert result is True, (
        "Nach force_clear() soll claim() durch einen anderen Worker True liefern (Ressource claimbar)"
    )


# ─── T-f3: force_clear feuert Teardown-Hook (Pfad 3) ────────────────────────

def test_force_clear_fires_teardown_hook_path3(tmp_vault):
    """AK-FORCE-CLEAR-PL-1 (T-f3): force_clear() feuert registrierten Teardown-Hook
    (Pfad 3 — at-least-once-Garantie, wie Pfad 1/release und Pfad 2/stale-reclaim).

    Spy-Strategie: register_teardown_hook mit spy_callback; claim; force_clear;
    pruefe dass spy_callback mindestens 1x aufgerufen wurde.

    Prueft: at-least-once (len(fired) >= 1) nach force_clear().
    """
    fired = []

    def spy_callback(resource_id):
        fired.append(resource_id)

    resource_id = "res_force_f3"

    # Hook registrieren, dann claim
    ra.register_teardown_hook(resource_id, spy_callback)
    assert ra.claim(resource_id, worker_id="worker-f3-a", ttl=600, vault_root=tmp_vault) is True

    # force_clear -> Pfad 3: Hook muss feuern
    ra.force_clear(resource_id, vault_root=tmp_vault)

    assert len(fired) >= 1, (
        f"Teardown-Hook (Pfad 3) muss nach force_clear() mindestens 1x gefeuert haben, "
        f"feuerte {len(fired)}x"
    )
    assert fired[0] == resource_id, (
        f"Teardown-Hook soll mit resource_id='{resource_id}' aufgerufen werden, "
        f"erhielt '{fired[0]}'"
    )
