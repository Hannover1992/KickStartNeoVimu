"""
test_stage_resource_registry.py — BL-247: Tests for stage_resource_registry.py

Stage 1 (Unit/pytest, Laserpointer). Batch-as-Slice: 1 Slice = ganzer batch_PL1.
12 Tests T1-T12 fuer den thin-Wrapper auf factory_lock (BL-229, kein Lock-Dup).

Test-Override-Muster (Produktions-Isolation): JEDER Test reicht vault_root=tmp_path
durch -> .locks/res::{id}.lock/ entsteht unter tmp_path/.locks/, das echte
Produktions-.locks/ (Vault-Root) bleibt UNBERUEHRT ("echte audit.jsonl unberuehrt").

Vorbild: test_factory_lock.py (gleiche Schicht, tmp_vault-Fixture, threading-Race-Sim).

Run aus Repo-Root (Produktions-cwd, Lead-Verify-Regel):
  py -3 -m pytest .claude/scripts/test_stage_resource_registry.py -v

STATUS: TEST-RING (RED). Das Produktiv-Modul stage_resource_registry.py existiert
noch NICHT — alle 12 Tests sind erwartet-RED (ImportError beim Modul-Import) bis die
TDD-green-Steps (Bau-Reihenfolge _res_bl_id -> acquire -> release -> lookup_free ->
acquire_all -> render) sie gruen ziehen. KEIN Produktiv-Code in dieser Datei (W7,
INV-PROCESS-STRICT).
"""

import sys
import time
import threading
from pathlib import Path

import pytest

# Add scripts dir to path (selbe Konvention wie test_factory_lock.py)
sys.path.insert(0, str(Path(__file__).parent))

import factory_lock as fl
import stage_resource_registry as srr  # NEU — existiert noch nicht => RED bis green-Steps


@pytest.fixture
def tmp_vault(tmp_path):
    """Provide a temporary vault root for isolation (.locks/ unter tmp_path/.locks/)."""
    return tmp_path


@pytest.fixture(autouse=True)
def patch_vault(tmp_vault, monkeypatch):
    """Patch VAULT_ROOT + no-op _emit_audit -> echtes .locks/ und audit.jsonl unberuehrt."""
    monkeypatch.setattr(fl, "VAULT_ROOT", tmp_vault)
    monkeypatch.setattr(fl, "_emit_audit", lambda *a, **kw: None)
    yield


# ─── T1: acquire auf FREIer Ressource -> True (AK-3) ──────────────────────────

def test_acquire_free_returns_true(tmp_vault):
    """AK-3: acquire(r,w1) auf FREIer Ressource -> True, .locks/res::r.lock/ entsteht."""
    result = srr.acquire("r", "w1", vault_root=tmp_vault)
    assert result is True
    lock_dir = fl._bl_lock_dir(srr._res_bl_id("r"), vault_root=tmp_vault)
    assert lock_dir.exists(), "res::r.lock/ sollte nach acquire existieren"


# ─── T2: acquire auf non-stale gehaltener Ressource -> False (AK-3/4) ─────────

def test_acquire_held_returns_false(tmp_vault):
    """AK-3/4: nach acquire(r,w1) liefert acquire(r,w2) -> False (held, non-stale)."""
    assert srr.acquire("r", "w1", vault_root=tmp_vault) is True
    result = srr.acquire("r", "w2", vault_root=tmp_vault)
    assert result is False


# ─── T3: release dann acquire -> True (AK-3) ──────────────────────────────────

def test_release_then_acquire(tmp_vault):
    """AK-3: release(r,w1) -> True; danach acquire(r,w2) -> True."""
    assert srr.acquire("r", "w1", vault_root=tmp_vault) is True
    assert srr.release("r", "w1", vault_root=tmp_vault) is True
    result = srr.acquire("r", "w2", vault_root=tmp_vault)
    assert result is True


# ─── T4: release durch Nicht-Owner -> False (AK-3) ────────────────────────────

def test_release_non_owner_fails(tmp_vault):
    """AK-3: release(r,'wrong') durch Nicht-Owner -> False, Lock bleibt gehalten."""
    assert srr.acquire("r", "w1", vault_root=tmp_vault) is True
    result = srr.release("r", "wrong", vault_root=tmp_vault)
    assert result is False
    # Lock weiterhin gehalten -> erneutes acquire durch Dritten scheitert
    assert srr.acquire("r", "w2", vault_root=tmp_vault) is False


# ─── T5: KANARIENVOGEL — nebenlaeufiges acquire, genau 1 Gewinner (AK-4) ──────

def test_concurrent_acquire_only_one_wins(tmp_vault):
    """AK-4 (Kanarienvogel, PFLICHT-DoD): N barrier-synchronisierte Threads acquiren
    EINE FREIe Ressource -> genau 1x True (atomares test-and-set geerbt aus factory_lock).
    Faengt jede Race-/Atomaritaets-Regression. Vorbild test_factory_lock:258."""
    n = 8
    acquired = []
    errors = []
    acq_lock = threading.Lock()
    barrier = threading.Barrier(n)

    def worker(i):
        wid = f"race-w{i}"
        try:
            barrier.wait(timeout=10.0)
        except threading.BrokenBarrierError:
            with acq_lock:
                errors.append((wid, "barrier-timeout"))
            return
        try:
            got = srr.acquire("r", wid, vault_root=tmp_vault)
            if got:
                with acq_lock:
                    acquired.append(wid)
        except Exception as e:
            with acq_lock:
                errors.append((wid, repr(e)))

    threads = [threading.Thread(target=worker, args=(i,), name=f"res-race-w{i}")
               for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20.0)

    assert not any(t.is_alive() for t in threads), "Ein Worker-Thread haengt (Deadlock?)"
    assert errors == [], f"Uncaught exception(s) (Race B): {errors}"
    assert len(acquired) == 1, (
        f"Mutual-Exclusion verletzt — {len(acquired)} Threads acquirten gleichzeitig "
        f"(erwartet genau 1): {acquired}"
    )


# ─── T6: Stale-Lock wird reclaimt (AK-8) ──────────────────────────────────────

def test_stale_lock_reclaimed(tmp_vault):
    """AK-8: verwaister res::r-Lock (ttl=1, heartbeat gealtert) -> naechstes acquire
    reclaimt + True (Stale-Reclaim geerbt aus factory_lock.is_bl_stale)."""
    assert srr.acquire("r", "w1", ttl=1, vault_root=tmp_vault) is True
    time.sleep(2)  # heartbeat ueberschreitet ttl -> Lock wird stale
    result = srr.acquire("r", "w2", ttl=300, vault_root=tmp_vault)
    assert result is True, "Stale-Lock sollte reclaimt werden"
    lock_dir = fl._bl_lock_dir(srr._res_bl_id("r"), vault_root=tmp_vault)
    owner = (lock_dir / "owner.txt").read_text(encoding="utf-8").strip()
    assert owner == "w2", f"Owner nach Reclaim sollte w2 sein, ist {owner!r}"


# ─── T7: Lock-Key = resource_id, kein Surplus-Key (AK-2) ──────────────────────

def test_lock_key_is_resource_id_no_surplus(tmp_vault):
    """AK-2: acquire(r1)+acquire(r2) erzeugt NUR res__r1/res__r2.lock — kein
    erfundener Identifier-Raum (Key = resource_id aus concurrency_depends_on).

    BL-352 (Test-Korrektur, vom Lead autorisiert): der frueher asserted Literal
    'res::r1.lock' zementierte ein auf Windows UNBAUBARES Design (':' in Dir-Namen
    -> WinError 123). Korrigiert auf den Windows-safe Key 'res__r1.lock'. Fuer
    simple ids ist _fs_safe('r1')=='r1', also bleibt der Key der resource_id (nur
    FS-enkodiert) — AK-2-Geist (kein Surplus-Identifier-Raum) UNVERAENDERT gewahrt.
    KEINE Test-Schwaechung: ein Test der ein unbaubares Design festschrieb, wird
    auf das baubare, semantisch identische Design korrigiert."""
    assert srr.acquire("r1", "w1", vault_root=tmp_vault) is True
    assert srr.acquire("r2", "w1", vault_root=tmp_vault) is True
    locks_root = fl._bl_locks_root(tmp_vault)
    lock_dirs = sorted(p.name for p in locks_root.iterdir() if p.is_dir())
    assert lock_dirs == ["res__r1.lock", "res__r2.lock"], (
        f"Nur res__r1/res__r2 erwartet, gefunden: {lock_dirs}"
    )


# ─── T8: run_id == worktree (AK-11) ───────────────────────────────────────────

def test_run_id_is_worktree(tmp_vault):
    """AK-11: nach acquire ist render-Eintrag.locked_by.run_id == worktree.txt-Inhalt
    (default Path.cwd(), kein neues Feld in factory_lock)."""
    assert srr.acquire("r", "w1", bl_id="BL-247", vault_root=tmp_vault) is True
    lock_dir = fl._bl_lock_dir(srr._res_bl_id("r"), vault_root=tmp_vault)
    worktree = (lock_dir / "worktree.txt").read_text(encoding="utf-8").strip()

    out_path = srr.render(["r"], vault_root=tmp_vault)
    content = Path(out_path).read_text(encoding="utf-8")
    assert worktree in content, (
        f"render-Output sollte run_id (worktree {worktree!r}) enthalten"
    )


# ─── T9: lookup_free liefert FREE/LOCKED-Zustaende (AK-9) ─────────────────────

def test_lookup_free_states(tmp_vault):
    """AK-9: gemischt held/frei -> lookup_free([r1,r2]) == {r1:'LOCKED', r2:'FREE'}
    (Plan-Zeit-API, liest LIVE .locks/, nie die .md)."""
    assert srr.acquire("r1", "w1", vault_root=tmp_vault) is True
    states = srr.lookup_free(["r1", "r2"], vault_root=tmp_vault)
    assert states == {"r1": "LOCKED", "r2": "FREE"}


# ─── T10: render Schema-Roundtrip + format_version (AK-1) ─────────────────────

def test_render_schema_roundtrip(tmp_vault):
    """AK-1: render([r1,r2]) erzeugt _resource_availability.md mit format_version-Stempel
    und Schema {resource_id,status,locked_by:{bl_id,run_id},since}; FREE -> locked_by null."""
    assert srr.acquire("r1", "w1", bl_id="BL-247", vault_root=tmp_vault) is True
    out_path = srr.render(["r1", "r2"], vault_root=tmp_vault)
    out_path = Path(out_path)
    assert out_path.name == "_resource_availability.md"
    assert out_path.exists()
    content = out_path.read_text(encoding="utf-8")
    assert "format_version" in content, "format_version-Stempel fehlt (FormatVersion-DualRead)"
    assert "r1" in content and "r2" in content, "beide resource_ids sollten gerendert sein"
    assert "LOCKED" in content, "r1 ist gehalten -> Status LOCKED erwartet"
    assert "FREE" in content, "r2 ist frei -> Status FREE erwartet"


# ─── T11: render gegen mehrere Ressourcen, je 1 Eintrag (AK-1 Integration) ────

def test_render_multiple_resources(tmp_vault):
    """AK-1 (Integration): render gegen mehrere resource_ids -> je genau 1 Eintrag."""
    for rid in ["r1", "r2", "r3"]:
        assert srr.acquire(rid, "w1", vault_root=tmp_vault) is True
    out_path = Path(srr.render(["r1", "r2", "r3"], vault_root=tmp_vault))
    content = out_path.read_text(encoding="utf-8")
    for rid in ["r1", "r2", "r3"]:
        assert content.count(rid) >= 1, f"{rid} sollte mindestens 1x im Render auftauchen"


# ─── T12: KANARIENVOGEL — acquire_all Rollback bei Partial-Fail (SOA-4) ───────

def test_acquire_all_rollback_on_partial_fail(tmp_vault):
    """SOA-4 (Kanarienvogel, PFLICHT-DoD): r2 vorab gelockt -> acquire_all([r1,r2])
    -> False UND r1 NICHT gehalten (Rollback). Wahrheits-Anker der all-or-nothing-Garantie:
    kein Partial-Lock-Deadlock."""
    assert srr.acquire("r2", "blocker", vault_root=tmp_vault) is True
    result = srr.acquire_all(["r1", "r2"], "w1", vault_root=tmp_vault)
    assert result is False, "acquire_all sollte bei Partial-Fail False liefern"
    # r1 darf NICHT gehalten sein (Rollback) -> erneutes acquire durch Dritten gelingt
    assert srr.acquire("r1", "w2", vault_root=tmp_vault) is True, (
        "r1 sollte nach Rollback FREI sein (kein Partial-Lock)"
    )


# ─── BL-486 batch_3 F1-FIX: release_all() Tests (T13-T17) ───────────────────
# RED: srr.release_all existiert noch NICHT -> AttributeError beim Aufruf.
# GREEN-Worker implementiert release_all(); diese Tests bleiben bis dahin rot.

# ─── T13: G-F1-1 — Symbol callable + korrekte Signatur ───────────────────────

def test_release_all_callable_and_signature(tmp_vault):
    """G-F1-1: release_all existiert, ist callable, hat vault_root=None-Default.

    RED: AttributeError('module ... has no attribute release_all') bis GREEN-Worker baut.
    """
    import inspect
    assert callable(srr.release_all), "release_all muss callable sein"
    sig = inspect.signature(srr.release_all)
    assert "vault_root" in sig.parameters, "release_all muss vault_root-Parameter haben"
    param = sig.parameters["vault_root"]
    assert param.default is None, "vault_root Default muss None sein"


# ─── T14: G-F1-2 — Multi-Lock release: alle Locks werden freigegeben ─────────

def test_release_all_frees_all_locks(tmp_vault):
    """G-F1-2: 3 Locks acquiren -> release_all() -> alle FREE, Rueckgabe = {res_a,res_b,res_c}.

    RED: AttributeError('module ... has no attribute release_all') bis GREEN-Worker baut.
    """
    assert srr.acquire("res_a", "w1", vault_root=tmp_vault) is True
    assert srr.acquire("res_b", "w1", vault_root=tmp_vault) is True
    assert srr.acquire("res_c", "w1", vault_root=tmp_vault) is True

    released = srr.release_all(vault_root=tmp_vault)

    assert set(released) == {"res_a", "res_b", "res_c"}, (
        f"release_all muss alle 3 resource_ids zurueckgeben, bekam: {released}"
    )
    states = srr.lookup_free(["res_a", "res_b", "res_c"], tmp_vault)
    for rid in ["res_a", "res_b", "res_c"]:
        assert states[rid] == "FREE", f"{rid} sollte nach release_all FREE sein, ist {states[rid]}"


# ─── T15: G-F1-3 — Idempotenz: kein Fehler, leere Liste ─────────────────────

def test_release_all_idempotent(tmp_vault):
    """G-F1-3: release_all() ohne Locks -> []; zweimaliger Aufruf -> zweiter gibt [].

    RED: AttributeError('module ... has no attribute release_all') bis GREEN-Worker baut.
    """
    # Fall 1: keine Locks vorhanden
    result = srr.release_all(vault_root=tmp_vault)
    assert result == [], f"release_all() ohne Locks muss [] zurueckgeben, bekam: {result}"

    # Fall 2: zweimaliger Aufruf nach acquire
    assert srr.acquire("res_x", "w1", vault_root=tmp_vault) is True
    srr.release_all(vault_root=tmp_vault)
    result2 = srr.release_all(vault_root=tmp_vault)
    assert result2 == [], f"Zweiter release_all()-Aufruf muss [] zurueckgeben, bekam: {result2}"


# ─── T16: G-F1-4 — Rueckgabe enthaelt dekodierte Original-resource_ids ───────

def test_release_all_returns_decoded_original_ids(tmp_vault):
    """G-F1-4: release_all() Rueckgabe enthaelt Original-ids (NICHT Lock-Dir-Namen).

    Prueft: 'res_a' in released (nicht 'res__res_a.lock') aus G-F1-2-Szenario.
    Prueft zusaetzlich FS-Sonderzeichen-ID wird korrekt dekodiert zurueckgegeben.

    RED: AttributeError('module ... has no attribute release_all') bis GREEN-Worker baut.
    """
    # Standard-ids (keine FS-Sonderzeichen) -> direkter Roundtrip
    assert srr.acquire("res_a", "w1", vault_root=tmp_vault) is True
    assert srr.acquire("res_b", "w1", vault_root=tmp_vault) is True
    released = srr.release_all(vault_root=tmp_vault)

    # NICHT die Lock-Dir-Namen (res__res_a.lock) sondern Original-ids
    for lock_dir_name in ["res__res_a.lock", "res__res_b.lock"]:
        assert lock_dir_name not in released, (
            f"release_all darf keine Lock-Dir-Namen zurueckgeben, aber '{lock_dir_name}' gefunden"
        )
    assert "res_a" in released, "Original-id 'res_a' muss in released sein"
    assert "res_b" in released, "Original-id 'res_b' muss in released sein"


# ─── T17: G-F1-5 — kein resource_allocator-Import (AST-Scan) ─────────────────

def test_no_resource_allocator_import_in_srr(tmp_vault):
    """G-F1-5: stage_resource_registry.py enthaelt KEINEN import resource_allocator.

    Circular-Import-Verbot (Blueprint 2.3 LOAD-BEARING CONSTRAINT).
    AST-Scan: kein 'import resource_allocator' / 'from resource_allocator' moeglich.

    Dieser Test ist von Anfang an gruen (kein ri-Import vorhanden) -- er sichert
    die Constraint gegen spaeteren Bruch durch GREEN-Worker.
    """
    import ast
    import pathlib
    src_path = pathlib.Path(".claude/scripts/stage_resource_registry.py")
    if not src_path.exists():
        # Fallback: absoluter Pfad (cwd-robust)
        src_path = pathlib.Path(__file__).parent / "stage_resource_registry.py"
    src = src_path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name != "resource_allocator", (
                    f"CIRCULAR-IMPORT-VERBOT: 'import resource_allocator' in "
                    f"stage_resource_registry.py Zeile {node.lineno} gefunden"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert module != "resource_allocator", (
                f"CIRCULAR-IMPORT-VERBOT: 'from resource_allocator' in "
                f"stage_resource_registry.py Zeile {node.lineno} gefunden"
            )
