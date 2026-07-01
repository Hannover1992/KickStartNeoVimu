"""
test_factory_lock_truth_lease.py — BL-230 SB-5 (LETZTER) RED-Tests.

AK-TRUTH-LEASE (k=70) + AK-EXCL-SEMAPHOR (k=61, PY-Anteil):
  factory_lock.py bekommt ein per-BL `truth_lease` (analog acquire_bl/promotion_lock-Muster):
    acquire_truth_lease(bl_id, worker_id, ...) / release_truth_lease(...) / is_truth_leased(bl_id)
  Scope = per-BL (NICHT cross-BL, NICHT Vault-Model.md). Erbt Stale-Reclaim (heartbeat/TTL) vom
  BL-Lock-Substrat. Eigener Lease-Namespace (kollidiert NICHT mit {bl}.lock / _pt_promotion.lock).
  EC-ES-2: Der EXCLUSIVE-Semaphor fuer M5 IST die truth_lease (1 Lease-Slot = 1 EXCLUSIVE-Slot/BL).

Blueprint: 4_Blueprint/BL-230_blueprint_AK-MOTOR-WELLE_S1.md → SB-5
  Akzeptanz-Punkte AON-TL-LEASE-MUTEX (10) / AON-TL-STALE-RECLAIM (11) + S-ES-1 (PY-Defer-Substrat).

RED-Worker (RED != GREEN, INV-BUILD-GRAIN): NUR Tests, KEIN Produktiv-Edit an factory_lock.py.
Folgt dem test_factory_lock.py-Stil (tmp_vault-Fixture, vault_root-Param-Durchreichung, EC-TL-3).

Run: py -3 -m pytest .claude/scripts/test_factory_lock_truth_lease.py -q
"""

import sys
import time
import threading
from pathlib import Path

import pytest

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

import factory_lock as fl


@pytest.fixture
def tmp_vault(tmp_path):
    """Provide a temporary vault root for isolation (EC-TL-3: vault_root-Param durchreichen)."""
    return tmp_path


@pytest.fixture(autouse=True)
def patch_vault(tmp_vault, monkeypatch):
    """Patch VAULT_ROOT so tests use tmp dir + no-op audit (analog test_factory_lock.py)."""
    monkeypatch.setattr(fl, "VAULT_ROOT", tmp_vault)
    monkeypatch.setattr(fl, "_emit_audit", lambda *a, **kw: None)
    yield


def _has_truth_lease_api() -> bool:
    """RED-Guard: die 3 truth_lease-Funktionen existieren noch nicht (greenfield)."""
    return (
        hasattr(fl, "acquire_truth_lease")
        and hasattr(fl, "release_truth_lease")
        and hasattr(fl, "is_truth_leased")
    )


# ─── AON-TL-LEASE-MUTEX (10) ──────────────────────────────────────────────────

def test_truth_lease_api_exists(tmp_vault):
    """RED: acquire_truth_lease / release_truth_lease / is_truth_leased existieren als per-BL-Lease.
    (greenfield — grep truth_lease in factory_lock.py == 0, IST-Befund Blueprint Z138/Z160.)"""
    assert _has_truth_lease_api(), (
        "truth_lease-API fehlt (acquire_truth_lease/release_truth_lease/is_truth_leased) — greenfield"
    )


def test_truth_lease_first_acquire_succeeds(tmp_vault):
    """RED: erster acquire_truth_lease(bl, w1) -> True (Lease frei)."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    got = fl.acquire_truth_lease("BL-230", worker_id="w1", ttl=600, vault_root=tmp_vault)
    assert got is True


def test_truth_lease_second_acquire_blocked(tmp_vault):
    """RED (AON-TL-LEASE-MUTEX): zweiter acquire bei besetztem (non-stale) Lease -> False."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    fl.acquire_truth_lease("BL-230", worker_id="w1", ttl=600, vault_root=tmp_vault)
    got = fl.acquire_truth_lease("BL-230", worker_id="w2", ttl=600, vault_root=tmp_vault)
    assert got is False, "zweiter Lease-Nehmer bei besetztem Slot muss False bekommen (1-Slot-Semaphor/BL)"


def test_truth_lease_release_then_reacquire(tmp_vault):
    """RED (AON-TL-LEASE-MUTEX): release(bl, w1) -> True; danach acquire(bl, w2) -> True."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    fl.acquire_truth_lease("BL-230", worker_id="w1", ttl=600, vault_root=tmp_vault)
    rel = fl.release_truth_lease("BL-230", worker_id="w1", vault_root=tmp_vault)
    assert rel is True
    got = fl.acquire_truth_lease("BL-230", worker_id="w2", ttl=600, vault_root=tmp_vault)
    assert got is True, "nach release muss der Slot wieder frei und neu-leasbar sein"


def test_is_truth_leased_reflects_state(tmp_vault):
    """RED (AON-TL-LEASE-MUTEX): is_truth_leased(bl) spiegelt den Stand (frei -> belegt -> frei)."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    assert fl.is_truth_leased("BL-230", vault_root=tmp_vault) is False
    fl.acquire_truth_lease("BL-230", worker_id="w1", ttl=600, vault_root=tmp_vault)
    assert fl.is_truth_leased("BL-230", vault_root=tmp_vault) is True
    fl.release_truth_lease("BL-230", worker_id="w1", vault_root=tmp_vault)
    assert fl.is_truth_leased("BL-230", vault_root=tmp_vault) is False


def test_truth_lease_per_bl_scope_disjoint(tmp_vault):
    """RED (EC-ES-1 per-BL-Scope): zwei verschiedene BLs teilen den Lease NICHT (kein cross-BL-Block)."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    a = fl.acquire_truth_lease("BL-230", worker_id="w1", ttl=600, vault_root=tmp_vault)
    b = fl.acquire_truth_lease("BL-999", worker_id="w2", ttl=600, vault_root=tmp_vault)
    assert a is True and b is True, "per-BL-Lease: BL-230 und BL-999 sind unabhaengige Slots"


def test_truth_lease_own_namespace_no_collision_with_bl_lock(tmp_vault):
    """RED (AON-TL-LEASE-MUTEX, eigener Namespace): truth_lease kollidiert NICHT mit {bl}.lock.
    Ein aktiver acquire_bl belegt NICHT den truth_lease-Slot desselben BL und umgekehrt."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    # Der gewoehnliche BL-Lock belegt {bl}.lock; die truth_lease muss einen EIGENEN Eintrag haben.
    fl.acquire_bl("BL-230", worker_id="bl-owner", ttl=600, vault_root=tmp_vault)
    got = fl.acquire_truth_lease("BL-230", worker_id="lease-owner", ttl=600, vault_root=tmp_vault)
    assert got is True, "truth_lease muss trotz aktivem {bl}.lock erwerbbar sein (eigener Namespace)"
    # ...und der BL-Lock bleibt unberuehrt vom truth_lease.
    info = fl.get_bl_lock_info("BL-230", vault_root=tmp_vault)
    assert info is not None and info.get("owner") == "bl-owner", "truth_lease darf {bl}.lock nicht stoeren"


# ─── AON-TL-STALE-RECLAIM (11) ────────────────────────────────────────────────

def test_truth_lease_stale_is_reacquirable(tmp_vault):
    """RED (AON-TL-STALE-RECLAIM): Stale-Lease (TTL ueberschritten) -> re-acquirable (kein Dead-Lock).
    Erbt is_bl_stale-Mechanik: ttl=1 + sleep(1.5) -> heartbeat veraltet -> reclaim."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    fl.acquire_truth_lease("BL-230", worker_id="w1", ttl=1, vault_root=tmp_vault)
    time.sleep(1.5)
    got = fl.acquire_truth_lease("BL-230", worker_id="w2", ttl=600, vault_root=tmp_vault)
    assert got is True, "stale Lease (TTL ueberschritten) muss reclaimbar sein (Worker-Tod != Dead-Lock)"


def test_truth_lease_stale_is_not_leased(tmp_vault):
    """RED (AON-TL-STALE-RECLAIM): is_truth_leased -> False sobald Lease stale ist (kein Dead-Lock-Signal)."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    fl.acquire_truth_lease("BL-230", worker_id="w1", ttl=1, vault_root=tmp_vault)
    time.sleep(1.5)
    assert fl.is_truth_leased("BL-230", vault_root=tmp_vault) is False, (
        "ein staler Lease darf NICHT als aktiv-geleast gelten (sonst permanenter Dead-Lock)"
    )


def test_truth_lease_foreign_release_returns_false(tmp_vault):
    """RED (AON-TL-STALE-RECLAIM): release durch Nicht-Owner -> False (kein Fremd-Release)."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    fl.acquire_truth_lease("BL-230", worker_id="w1", ttl=600, vault_root=tmp_vault)
    rel = fl.release_truth_lease("BL-230", worker_id="fremder-worker", vault_root=tmp_vault)
    assert rel is False, "Nicht-Owner darf den Lease nicht freigeben"
    assert fl.is_truth_leased("BL-230", vault_root=tmp_vault) is True, "Lease bleibt nach Fremd-Release-Versuch belegt"


def test_truth_lease_double_release_no_throw(tmp_vault):
    """RED (AON-TL-STALE-RECLAIM / S-TL-3 Idempotenz): doppeltes release -> kein Throw (idempotent)."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    fl.acquire_truth_lease("BL-230", worker_id="w1", ttl=600, vault_root=tmp_vault)
    fl.release_truth_lease("BL-230", worker_id="w1", vault_root=tmp_vault)
    # zweites release darf NICHT werfen (idempotent); Rueckgabe False (nichts mehr zu loesen) ist ok.
    try:
        again = fl.release_truth_lease("BL-230", worker_id="w1", vault_root=tmp_vault)
    except Exception as e:  # noqa: BLE001
        pytest.fail(f"doppeltes release_truth_lease warf eine Exception (nicht idempotent): {e!r}")
    assert again is False


# ─── S-ES-1 PY-Substrat: EXCLUSIVE/M5-Semaphor == truth_lease (EC-ES-2) ───────

def test_exclusive_semaphor_is_truth_lease_single_slot(tmp_vault):
    """RED (S-ES-1 / EC-ES-2): der M5-EXCLUSIVE-Semaphor IST die truth_lease — 1 physischer Lock/BL.
    Zweiter M5/EXCLUSIVE acquire bei besetztem Slot -> False (Motor mappt das auf 'deferred',
    NICHT blockierend gewartet, KEIN Throw). Hier der Lock-seitige Beweis: genau 1 Slot."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    first = fl.acquire_truth_lease("BL-230", worker_id="m5-batch-A", ttl=600, vault_root=tmp_vault)
    second = fl.acquire_truth_lease("BL-230", worker_id="m5-batch-B", ttl=600, vault_root=tmp_vault)
    assert first is True, "erster M5 erhaelt den EXCLUSIVE-Semaphor (= truth_lease)"
    assert second is False, "zweiter M5 bei besetztem Slot -> False (-> Motor: deferred, non-blocking)"


def test_exclusive_semaphor_acquire_does_not_block(tmp_vault):
    """RED (S-ES-1, Nicht-Anhalten-Doktrin): der zweite acquire kehrt SOFORT zurueck (kein blockierendes
    Warten, kein Throw) — die Defer-Entscheidung ist non-blocking."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    fl.acquire_truth_lease("BL-230", worker_id="m5-A", ttl=600, vault_root=tmp_vault)
    start = time.monotonic()
    second = fl.acquire_truth_lease("BL-230", worker_id="m5-B", ttl=600, vault_root=tmp_vault)
    elapsed = time.monotonic() - start
    assert second is False
    assert elapsed < 1.0, f"acquire_truth_lease bei besetztem Slot blockierte ({elapsed:.2f}s) — muss non-blocking sein"


# ─── Mutual-Exclusion unter Nebenlaeufigkeit (BL-344-Stil-Schaerfe) ───────────

def test_truth_lease_concurrent_only_one_wins(tmp_vault):
    """RED: N=8 barrier-synchronisierte Threads auf EINEN frischen truth_lease -> genau 1 Gewinner,
    0 uncaught Exceptions (mirror test_acquire_bl_concurrent_fresh_lock_exclusive)."""
    assert _has_truth_lease_api(), "truth_lease-API fehlt — greenfield"
    n = 8
    bl_id = "BL-LEASE-RACE"
    acquired = []
    errors = []
    acq_lock = threading.Lock()
    barrier = threading.Barrier(n)

    def worker(i):
        wid = f"lease-w{i}"
        try:
            barrier.wait(timeout=10.0)
        except threading.BrokenBarrierError:
            with acq_lock:
                errors.append((wid, "barrier-timeout"))
            return
        try:
            got = fl.acquire_truth_lease(bl_id, worker_id=wid, ttl=600, vault_root=tmp_vault)
            if got:
                with acq_lock:
                    acquired.append(wid)
        except Exception as e:  # noqa: BLE001
            with acq_lock:
                errors.append((wid, repr(e)))

    threads = [threading.Thread(target=worker, args=(i,), name=f"lease-race-w{i}") for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20.0)

    assert not any(t.is_alive() for t in threads), "ein Lease-Worker-Thread haengt (moeglicher Dead-Lock)"
    assert errors == [], f"uncaught Exception(s) in acquire_truth_lease: {errors}"
    assert len(acquired) == 1, f"Mutual-Exclusion verletzt — {len(acquired)} Gewinner (erwartet 1): {acquired}"
