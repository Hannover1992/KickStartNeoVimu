"""
test_fan_in_hunk_verify.py — BL-247 AK-R4: merge-Hunk-Verify Retirement-Netz (RED zuerst).

Der lange korrekte Weg. R4 = die PESSIMISTISCHE Naht hinter dem OPTIMISTISCHEN Plan-Zeit-
Region-Claim (acquire_region): am Fan-In werden die TATSÄCHLICH berührten Hunks (Zeilen-
Ranges) aller Worker re-geprüft — fängt Kollisionen, die der Plan-Claim verfehlte
(Optimistic→Pessimistic-Kette, merge_cost_model-Empirie). Reine Funktion (kein Vault),
nutzt dasselbe half-open Overlap (−1 = ganze Datei) wie der Region-Lock.

NICHT blind: synthetische Hunk-Fixtures (disjoint/overlap/adjacent/whole-file/multi-worker).
Die LIVE-Validierung unter echter Parallel-Execution = Gate-C (wie der Suitability-Forward-Verify).

Run aus Repo-Root:  py -3 -m pytest .claude/scripts/test_fan_in_hunk_verify.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import stage_resource_registry as srr


def test_disjoint_same_file_no_conflict():
    wh = {"w1": {"a.cs": [(0, 10)]}, "w2": {"a.cs": [(20, 30)]}}
    assert srr.fan_in_hunk_verify(wh) == []


def test_overlap_same_file_reports_conflict():
    wh = {"w1": {"a.cs": [(0, 15)]}, "w2": {"a.cs": [(10, 20)]}}
    conflicts = srr.fan_in_hunk_verify(wh)
    assert len(conflicts) == 1
    c = conflicts[0]
    assert c["file"] == "a.cs"
    assert {c["worker_a"], c["worker_b"]} == {"w1", "w2"}


def test_adjacent_halfopen_no_off_by_one():
    # [0,10) and [10,20) berühren sich NICHT (half-open) -> kein Konflikt
    wh = {"w1": {"a.cs": [(0, 10)]}, "w2": {"a.cs": [(10, 20)]}}
    assert srr.fan_in_hunk_verify(wh) == []


def test_whole_file_collides_with_any():
    # (0,-1) = ganze Datei -> kollidiert mit jedem anderen Hunk derselben Datei
    wh = {"w1": {"a.cs": [(0, -1)]}, "w2": {"a.cs": [(5, 8)]}}
    assert len(srr.fan_in_hunk_verify(wh)) == 1


def test_different_files_no_conflict():
    wh = {"w1": {"a.cs": [(0, 100)]}, "w2": {"b.cs": [(0, 100)]}}
    assert srr.fan_in_hunk_verify(wh) == []


def test_same_worker_own_overlapping_hunks_no_conflict():
    # eigene Hunks kollidieren NIE mit sich selbst (nur Cross-Worker zählt)
    wh = {"w1": {"a.cs": [(0, 10), (5, 15)]}}
    assert srr.fan_in_hunk_verify(wh) == []


def test_none_and_empty_tolerant():
    assert srr.fan_in_hunk_verify(None) == []
    assert srr.fan_in_hunk_verify({}) == []
    assert srr.fan_in_hunk_verify({"w1": {"a.cs": []}}) == []
    assert srr.fan_in_hunk_verify({"w1": {}}) == []


def test_three_workers_only_overlapping_pair_reported():
    # w1/w3 überlappen in a.cs; w2 disjunkt -> genau 1 Konflikt (w1,w3)
    wh = {
        "w1": {"a.cs": [(0, 10)]},
        "w2": {"a.cs": [(50, 60)]},
        "w3": {"a.cs": [(5, 8)]},
    }
    conflicts = srr.fan_in_hunk_verify(wh)
    assert len(conflicts) == 1
    assert {conflicts[0]["worker_a"], conflicts[0]["worker_b"]} == {"w1", "w3"}
