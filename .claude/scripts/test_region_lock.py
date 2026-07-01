"""
test_region_lock.py — BL-247 Region-Lock-Erweiterung (BL-353 §15/§17, line-range-claim).

Stage 1 (Unit). Der lange korrekte Weg: RED-Ring ZUERST. Deckt die concurrency-
kritischen Verhalten ab (Behavior-Review > Test-Green — Off-by-One im Overlap =
false-parallel = Korruption):
  TR1 disjoint-grant · TR2 overlap-conflict · TR3 adjacent-halfopen (kein Off-by-One)
  TR4 whole-file collapse (beide Richtungen) · TR5 release-frees · TR6 KANARIE concurrent
  TR7 stale-region-reclaim · TR8 per-resource-isolation

Whole-file-Claim-Konvention: (start=0, end=-1) = ganze Datei, kollidiert mit allem
auf dieser Ressource (self-adaptiv: god-file -> File-Lock).

Run aus Repo-Root (Lead-Verify-Regel):
  py -3 -m pytest .claude/scripts/test_region_lock.py -v
"""
import sys
import time
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import factory_lock as fl
import stage_resource_registry as srr


@pytest.fixture
def tmp_vault(tmp_path):
    return tmp_path


@pytest.fixture(autouse=True)
def patch_vault(tmp_vault, monkeypatch):
    monkeypatch.setattr(fl, "VAULT_ROOT", tmp_vault)
    monkeypatch.setattr(fl, "_emit_audit", lambda *a, **kw: None)
    yield


# ─── TR1: disjunkte Regionen derselben Ressource -> beide True (der Kern-Gewinn) ──
def test_disjoint_regions_both_grant(tmp_vault):
    assert srr.acquire_region("f", 0, 100, "w1", vault_root=tmp_vault) is True
    assert srr.acquire_region("f", 200, 300, "w2", vault_root=tmp_vault) is True


# ─── TR2: ueberlappende Regionen -> zweite False ──────────────────────────────────
def test_overlapping_regions_conflict(tmp_vault):
    assert srr.acquire_region("f", 0, 100, "w1", vault_root=tmp_vault) is True
    assert srr.acquire_region("f", 50, 150, "w2", vault_root=tmp_vault) is False


# ─── TR3: angrenzend halb-offen [0,10)+[10,20) -> beide True (KEIN Off-by-One) ────
def test_adjacent_halfopen_no_offbyone(tmp_vault):
    assert srr.acquire_region("f", 0, 10, "w1", vault_root=tmp_vault) is True
    assert srr.acquire_region("f", 10, 20, "w2", vault_root=tmp_vault) is True
    # echte 1-Zeile-Ueberlappung MUSS dagegen kollidieren
    assert srr.acquire_region("f", 9, 11, "w3", vault_root=tmp_vault) is False


# ─── TR4: whole-file-Claim (0,-1) kollabiert auf File-Lock (beide Richtungen) ─────
def test_whole_file_claim_collapses(tmp_vault):
    # whole-file zuerst -> jede Region scheitert
    assert srr.acquire_region("f", 0, -1, "w1", vault_root=tmp_vault) is True
    assert srr.acquire_region("f", 500, 600, "w2", vault_root=tmp_vault) is False
    # umgekehrt: Region zuerst -> whole-file scheitert
    assert srr.acquire_region("g", 500, 600, "w1", vault_root=tmp_vault) is True
    assert srr.acquire_region("g", 0, -1, "w2", vault_root=tmp_vault) is False


# ─── TR5: release_region gibt Range frei -> ueberlappendes acquire gelingt dann ───
def test_release_region_frees_range(tmp_vault):
    assert srr.acquire_region("f", 0, 100, "w1", vault_root=tmp_vault) is True
    assert srr.acquire_region("f", 50, 150, "w2", vault_root=tmp_vault) is False
    assert srr.release_region("f", 0, 100, "w1", vault_root=tmp_vault) is True
    assert srr.acquire_region("f", 50, 150, "w2", vault_root=tmp_vault) is True


# ─── TR6: KANARIE — nebenlaeufig: N disjunkte alle, N gleiche genau 1 ─────────────
def test_concurrent_regions(tmp_vault):
    n = 8
    # (a) N DISJUNKTE Ranges -> alle N True
    got_disjoint = []
    lk = threading.Lock()
    bar = threading.Barrier(n)

    def disjoint_worker(i):
        try: bar.wait(timeout=10.0)
        except threading.BrokenBarrierError: return
        if srr.acquire_region("fa", i * 100, i * 100 + 50, f"w{i}", vault_root=tmp_vault):
            with lk: got_disjoint.append(i)

    ts = [threading.Thread(target=disjoint_worker, args=(i,)) for i in range(n)]
    for t in ts: t.start()
    for t in ts: t.join(timeout=20.0)
    assert not any(t.is_alive() for t in ts), "Thread haengt (Deadlock?)"
    assert len(got_disjoint) == n, f"alle {n} disjunkten Ranges sollten granten, got {len(got_disjoint)}"

    # (b) N Threads auf GLEICHE Range -> genau 1 True
    got_same = []
    bar2 = threading.Barrier(n)

    def same_worker(i):
        try: bar2.wait(timeout=10.0)
        except threading.BrokenBarrierError: return
        if srr.acquire_region("fb", 0, 100, f"w{i}", vault_root=tmp_vault):
            with lk: got_same.append(i)

    ts2 = [threading.Thread(target=same_worker, args=(i,)) for i in range(n)]
    for t in ts2: t.start()
    for t in ts2: t.join(timeout=20.0)
    assert not any(t.is_alive() for t in ts2), "Thread haengt (Deadlock?)"
    assert len(got_same) == 1, f"genau 1 sollte die gleiche Range granten, got {len(got_same)}: {got_same}"


# ─── TR7: stale Region-Claim wird reclaimt (ttl=1) ────────────────────────────────
def test_stale_region_reclaimed(tmp_vault):
    assert srr.acquire_region("f", 0, 100, "w1", ttl=1, vault_root=tmp_vault) is True
    time.sleep(2)  # Claim wird stale
    assert srr.acquire_region("f", 50, 150, "w2", ttl=300, vault_root=tmp_vault) is True, \
        "stale Region-Claim sollte reclaimt werden"


# ─── TR8: gleiche Range auf VERSCHIEDENEN Ressourcen -> beide True (per-resource) ─
def test_per_resource_isolation(tmp_vault):
    assert srr.acquire_region("f1", 0, 100, "w1", vault_root=tmp_vault) is True
    assert srr.acquire_region("f2", 0, 100, "w2", vault_root=tmp_vault) is True


# ─── TR9: lookup_free_regions liefert FREE/LOCKED je Kandidat-Range (Plan-Zeit-API) ─
def test_lookup_free_regions_states(tmp_vault):
    assert srr.acquire_region("f", 0, 100, "w1", vault_root=tmp_vault) is True
    states = srr.lookup_free_regions("f", [(50, 150), (200, 300)], vault_root=tmp_vault)
    assert states == {(50, 150): "LOCKED", (200, 300): "FREE"}


# ─── TR10: lookup_free_regions ignoriert stale Claims (liest LIVE, nie .md) ────────
def test_lookup_free_regions_ignores_stale(tmp_vault):
    assert srr.acquire_region("f", 0, 100, "w1", ttl=1, vault_root=tmp_vault) is True
    time.sleep(2)
    states = srr.lookup_free_regions("f", [(0, 100)], vault_root=tmp_vault)
    assert states == {(0, 100): "FREE"}, "stale Claim darf NICHT als LOCKED gelten"


# ─── TR11: whole-file-Claim -> jede Kandidat-Range LOCKED ─────────────────────────
def test_lookup_free_regions_whole_file(tmp_vault):
    assert srr.acquire_region("f", 0, -1, "w1", vault_root=tmp_vault) is True
    states = srr.lookup_free_regions("f", [(10, 20), (9999, 10000)], vault_root=tmp_vault)
    assert states == {(10, 20): "LOCKED", (9999, 10000): "LOCKED"}
