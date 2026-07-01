"""
test_sub_batch_targets.py — BL-342 Phase-1a Naht: ziel_dateien-Surfacing (RED zuerst).

Der lange korrekte Weg. Step 1 der IDF-Phase-7.8-Verdrahtung: aus dem REALEN
dependencyAnalyzer-Output `file_index` (invertierter Index Datei -> [Items]) und
`batch_items_per_batch` (Sub-Batch -> [Items]) die `ziel_dateien` pro Sub-Batch
ableiten — der Plan-Zeit-Input fuer parallel_suitability.suitability_for_batches.

WICHTIG (Szenario-Verify, messen statt glauben): die Quelle ist `file_index`
(BERATER_OUTPUTS.dependencyAnalyzer), NICHT `dateien_geplant` (0 Treffer im echten
486-Manifest) und NICHT gatherSignals.file_refs (PT-Harvest, andere Item-IDs).
Fixture = die ECHTE 486 v6-orphan file_index (Z2738-2745) — DUC-2 ist der
Kopplungs-Hub (5 Dateien), DUC-13 (time-mask) isoliert.

Run aus Repo-Root:  py -3 -m pytest .claude/scripts/test_sub_batch_targets.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import sub_batch_targets as sbt
import parallel_suitability as ps


# ─── ECHTE 486 v6-orphan file_index (Ground-Truth, _manifest.md Z2738-2745) ──────
F486_V6 = {
    "autocomplete-chips-field.ts": ["PR2-DUC-1", "PR2-DUC-2", "PR2-DUC-3",
                                    "PR2-DUC-4", "PR2-DUC-5", "PR2-DUC-6"],
    "selbstauskunft-details-qdvtp.component.ts": ["PR2-DUC-2", "PR2-DUC-7",
                                                  "PR2-DUC-8", "PR2-DUC-12"],
    "selbstauskunft-qdvtp-form-mappers.ts": ["PR2-DUC-2", "PR2-DUC-11"],
    "selbstauskunft-details-qdvs.component.ts": ["PR2-DUC-2", "PR2-DUC-11"],
    "selbstauskunft-form-converters.ts": ["PR2-DUC-2"],
    "validation-constants.ts": ["PR2-DUC-7"],
    "time-mask.directive.ts": ["PR2-DUC-13"],
}


# ─── ziel_dateien_per_batch: invert file_index scoped per Sub-Batch ──────────────
def test_ziel_dateien_disjoint_batches():
    bipb = {"B1": ["i1"], "B2": ["i2"]}
    fidx = {"a.ts": ["i1"], "b.ts": ["i2"]}
    out = sbt.ziel_dateien_per_batch(bipb, fidx)
    assert out["B1"] == ["a.ts"]
    assert out["B2"] == ["b.ts"]


def test_ziel_dateien_shared_file_appears_in_both():
    bipb = {"B1": ["i1"], "B2": ["i2"]}
    fidx = {"shared.ts": ["i1", "i2"], "a.ts": ["i1"]}
    out = sbt.ziel_dateien_per_batch(bipb, fidx)
    assert out["B1"] == ["a.ts", "shared.ts"]   # sorted
    assert out["B2"] == ["shared.ts"]


def test_ziel_dateien_dedup_and_sorted():
    # item touches a file via multiple file_index entries -> dedup; output sorted
    bipb = {"B1": ["i1", "i2"]}
    fidx = {"z.ts": ["i1"], "a.ts": ["i2"], "m.ts": ["i1", "i2"]}
    out = sbt.ziel_dateien_per_batch(bipb, fidx)
    assert out["B1"] == ["a.ts", "m.ts", "z.ts"]   # dedup + sorted, m.ts once


def test_ziel_dateien_item_not_in_file_index_contributes_nothing():
    # best-effort: batch item with no file_index entry -> no files, no crash
    bipb = {"B1": ["ghost-item"]}
    fidx = {"a.ts": ["i1"]}
    out = sbt.ziel_dateien_per_batch(bipb, fidx)
    assert out["B1"] == []


def test_ziel_dateien_none_and_empty_tolerant():
    assert sbt.ziel_dateien_per_batch(None, None) == {}
    assert sbt.ziel_dateien_per_batch({}, {}) == {}
    assert sbt.ziel_dateien_per_batch({"B1": None}, {"a.ts": None}) == {"B1": []}


# ─── build_sub_batches: producer-ready Liste {id, ziel_dateien, change_type} ──────
def test_build_sub_batches_shape_default_change_type_none():
    bipb = {"B1": ["i1"], "B2": ["i2"]}
    fidx = {"a.ts": ["i1"], "b.ts": ["i2"]}
    sb = sbt.build_sub_batches(bipb, fidx)
    assert sb == [
        {"id": "B1", "ziel_dateien": ["a.ts"], "change_type": None},
        {"id": "B2", "ziel_dateien": ["b.ts"], "change_type": None},
    ]


def test_build_sub_batches_with_change_type_map():
    bipb = {"B1": ["i1"]}
    fidx = {"a.ts": ["i1"]}
    sb = sbt.build_sub_batches(bipb, fidx, change_type_map={"B1": "add"})
    assert sb[0]["change_type"] == "add"


# ─── Forward-Verify (Unit-Ebene) gegen ECHTE 486 v6 file_index + Producer ─────────
def test_forward_verify_486_isolated_vs_hub():
    # Split: chips-cluster (ohne DUC-2-Hub) vs isoliertes time-mask DUC-13
    bipb = {
        "chips": ["PR2-DUC-1", "PR2-DUC-3", "PR2-DUC-4", "PR2-DUC-5", "PR2-DUC-6"],
        "timemask": ["PR2-DUC-13"],
    }
    sb = sbt.build_sub_batches(bipb, F486_V6)
    m = ps.conflict_matrix(sb)
    # chips beruehrt NUR autocomplete-chips-field.ts; timemask NUR time-mask.directive.ts
    assert m[("chips", "timemask")]["status"] == "disjoint"
    res = ps.suitability_for_batches(sb)
    assert res["conflict_islands"] == 2          # 2 disjunkte Inseln
    assert res["suitable"] is True               # parallel-able (build_share=None -> island-count)


def test_forward_verify_486_duc2_hub_couples():
    # DUC-2 (Hub, 5 Dateien) in batch A, DUC-7 in batch B -> teilen qdvtp.component.ts
    bipb = {"hub": ["PR2-DUC-2"], "oz": ["PR2-DUC-7"]}
    sb = sbt.build_sub_batches(bipb, F486_V6)
    m = ps.conflict_matrix(sb)
    assert m[("hub", "oz")]["status"] == "overlap"
    assert "selbstauskunft-details-qdvtp.component.ts" in m[("hub", "oz")]["files"]
    res = ps.suitability_for_batches(sb)
    assert res["conflict_islands"] == 1          # 1 Insel -> gekoppelt
    assert res["recommended_N"] == 1             # seriell (Hub koppelt)
