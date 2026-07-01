#!/usr/bin/env python3
"""Tests fuer truth_backref_index.py (BL-309 R1 / Inverse-Index, one-shot)."""
from __future__ import annotations

import truth_backref_index as bi


def _mk(p, content):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_find_wrefs_excludes_wknoten():
    assert bi.find_wrefs("siehe W01 und W-IST-2, aber nicht W-Knoten") == {"W01", "W-IST-2"}


def test_build_index_across_surfaces(tmp_path):
    bl = tmp_path / "BL-x"
    _mk(bl / "6_PL" / "BL-x-parking-lot.md", "PL deckt W01 ab.")
    _mk(bl / "3_Spec" / "BL-x_Spec.md", "Spec referenziert W01 und W02.")
    _mk(bl / "4_K-Score" / "BL-x-K-SCORE.md", "model_refs: W01.")
    idx = bi.build_backref_index(bl)
    assert sorted(e["kind"] for e in idx["W01"]) == ["kscore_ref", "pl_source_w", "spec_link"]
    assert [e["kind"] for e in idx["W02"]] == ["spec_link"]


def test_index_dedups_same_file_same_kind(tmp_path):
    bl = tmp_path / "BL-x"
    _mk(bl / "6_PL" / "BL-x-parking-lot.md", "W01 ... und nochmal W01 weiter unten.")
    idx = bi.build_backref_index(bl)
    assert len(idx["W01"]) == 1


def test_truth_edges_become_backrefs(tmp_path):
    bl = tmp_path / "BL-x"
    _mk(bl / "2_Model" / "truths" / "W05.md",
        "---\ntype: truth\nlocal_id: W05\nedges:\n  - rel: depends_on\n    ziel: W01\n---\n")
    idx = bi.build_backref_index(bl)
    assert any(e["by"] == "W05" and e["kind"] == "truth_edge" for e in idx["W01"])


def test_no_refs_returns_empty(tmp_path):
    bl = tmp_path / "BL-x"
    bl.mkdir()
    assert bi.build_backref_index(bl) == {}


def test_referenced_by_for_helper(tmp_path):
    bl = tmp_path / "BL-x"
    _mk(bl / "6_PL" / "pl.md", "W01")
    idx = bi.build_backref_index(bl)
    assert bi.referenced_by_for("W01", idx)[0]["kind"] == "pl_source_w"
    assert bi.referenced_by_for("W99", idx) == []


def test_apply_backrefs_populates_and_stays_schema_valid(tmp_path):
    """End-to-end R1: atomize -> build index -> apply -> referenced_by gesetzt + schema-valid."""
    import truth_atomizer as ta
    import truth_schema as ts
    bl = tmp_path / "BL-x"
    _mk(bl / "2_Model" / "Foo_Model.md", "### W01\nEine Wahrheit.\n")
    _mk(bl / "6_PL" / "pl.md", "PL deckt W01 ab.")
    truths = ta.atomize((bl / "2_Model" / "Foo_Model.md").read_text(encoding="utf-8"), "BL-x")
    bi.apply_backrefs(truths, bi.build_backref_index(bl))
    assert truths[0]["referenced_by"][0]["kind"] == "pl_source_w"
    assert [m for s, m in ts.validate_truth(truths[0]) if s == "ERROR"] == []
