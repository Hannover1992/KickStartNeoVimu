"""
test_parallel_suitability.py — BL-342 Stufe-1 Producer (Plan-Zeit, file-level).

Der lange korrekte Weg: RED-Ring zuerst. Plan-Zeit (ziel_dateien) -> Konflikt-Matrix
(pairwise file-overlap, AK-1/AK-2 deterministisch+erklaerbar) + aggregat suitability
(Konflikt-Insel-Zahl, NICHT shatter — shatter ist commit-level). build_share (AK-6)
daempft review-dominierte Mengen.

Run aus Repo-Root:  py -3 -m pytest .claude/scripts/test_parallel_suitability.py -v
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import parallel_suitability as ps


# ─── conflict_matrix (AK-1/AK-2): pairwise ziel_dateien-Overlap, erklaerbar ──────
def test_conflict_matrix_disjoint():
    sb = [{"id": "B1", "ziel_dateien": ["a.cs"]},
          {"id": "B2", "ziel_dateien": ["b.cs"]}]
    m = ps.conflict_matrix(sb)
    assert m[("B1", "B2")]["status"] == "disjoint"
    assert m[("B1", "B2")]["files"] == []


def test_conflict_matrix_overlap_lists_shared_files():
    sb = [{"id": "B1", "ziel_dateien": ["a.cs", "shared.cs"]},
          {"id": "B2", "ziel_dateien": ["shared.cs", "c.cs"]}]
    m = ps.conflict_matrix(sb)
    assert m[("B1", "B2")]["status"] == "overlap"
    assert m[("B1", "B2")]["files"] == ["shared.cs"]  # erklaerbar: WELCHE Datei


# ─── suitability_for_batches: Insel-basiert + build_share ─────────────────────────
def test_disjoint_batches_parallel():
    sb = [{"id": f"B{i}", "ziel_dateien": [f"f{i}.cs"], "change_type": "add"} for i in range(4)]
    v = ps.suitability_for_batches(sb)
    assert v["conflict_islands"] == 4
    assert v["recommended_N"] >= 2
    assert v["suitable"] is True


def test_all_share_one_file_serial():
    """4 Sub-Batches fassen ALLE dieselbe Datei an -> 1 Konflikt-Insel -> seriell (N=1),
    egal change_type (file-level kann disjunkte Regionen nicht sehen -> konservativ)."""
    sb = [{"id": f"B{i}", "ziel_dateien": ["god.cs"], "change_type": "add"} for i in range(4)]
    v = ps.suitability_for_batches(sb)
    assert v["conflict_islands"] == 1
    assert v["recommended_N"] == 1
    assert v["suitable"] is False


def test_build_share_dampens_review():
    """Disjunkte Dateien ABER alle modify -> build_share 0 -> N gedaempft (review-dominiert)."""
    sb = [{"id": f"B{i}", "ziel_dateien": [f"f{i}.cs"], "change_type": "modify"} for i in range(4)]
    v = ps.suitability_for_batches(sb)
    assert v["build_share"] == 0.0
    assert v["recommended_N"] < 4  # gedaempft ggü. 4 disjunkten Inseln


def test_single_batch_not_suitable():
    v = ps.suitability_for_batches([{"id": "B1", "ziel_dateien": ["a.cs"]}])
    assert v["recommended_N"] == 1
    assert v["suitable"] is False
