#!/usr/bin/env python3
"""Tests fuer truth_schema.py (BL-309 Phase A1 / Truth-Atomisierung)."""
from __future__ import annotations

import truth_schema as ts


def _valid_truth() -> dict:
    """Ein vollstaendig gueltiges type:truth-Frontmatter (0 issues erwartet)."""
    return {
        "type": "truth",
        "id": "BL-309-truth-migration.W01",
        "local_id": "W01",
        "text": "Das alte System ist model-basiert.",
        "typ": "FESTSTELLUNG",
        "herkunft": "INTERN",
        "status": "BESTAETIGT",
        "truth_grade": "code_verified",
    }


def _errors(issues):
    return [m for s, m in issues if s == "ERROR"]


def _warns(issues):
    return [m for s, m in issues if s == "WARN"]


# ─── Happy Path ───
def test_valid_truth_has_no_issues():
    assert ts.validate_truth(_valid_truth()) == []


def test_canonical_id_builds_dotted_form():
    assert ts.canonical_id("BL-309-truth-migration", "W-AK-A") == "BL-309-truth-migration.W-AK-A"


def test_dashed_local_id_is_valid():
    fm = _valid_truth()
    fm["id"] = "BL-309-truth-migration.W-IST-1"
    fm["local_id"] = "W-IST-1"
    assert ts.validate_truth(fm) == []


# ─── Pflichtfelder → ERROR ───
def test_missing_text_is_error():
    fm = _valid_truth()
    del fm["text"]
    assert any("text" in m for m in _errors(ts.validate_truth(fm)))


def test_empty_required_field_is_error():
    fm = _valid_truth()
    fm["typ"] = ""
    assert any("typ" in m for m in _errors(ts.validate_truth(fm)))


def test_non_dict_is_error():
    assert _errors(ts.validate_truth("not a dict"))  # type: ignore[arg-type]


# ─── Settled Enums → ERROR ───
def test_invalid_typ_is_error():
    fm = _valid_truth()
    fm["typ"] = "BEHAUPTUNG"
    assert any("typ" in m for m in _errors(ts.validate_truth(fm)))


def test_invalid_herkunft_is_error():
    fm = _valid_truth()
    fm["herkunft"] = "WOANDERS"
    assert any("herkunft" in m for m in _errors(ts.validate_truth(fm)))


def test_invalid_truth_grade_is_error():
    fm = _valid_truth()
    fm["truth_grade"] = "gefuehlt_wahr"
    assert any("truth_grade" in m for m in _errors(ts.validate_truth(fm)))


def test_all_three_settled_enums_accept_each_member():
    for typ in ts.TYP_VALUES:
        for herk in ts.HERKUNFT_VALUES:
            for grade in ts.TRUTH_GRADE_VALUES:
                fm = _valid_truth()
                fm.update(typ=typ, herkunft=herk, truth_grade=grade)
                assert _errors(ts.validate_truth(fm)) == []


# ─── status → WARN (nicht ERROR, weil Mapping = Phase-2-HiL-Gate) ───
def test_unknown_status_is_warn_not_error():
    fm = _valid_truth()
    fm["status"] = "irgendwas_legacy"
    issues = ts.validate_truth(fm)
    assert _errors(issues) == []
    assert any("status" in m for m in _warns(issues))


def test_widerlegt_is_canonical_status():
    fm = _valid_truth()
    fm["status"] = "WIDERLEGT"
    assert ts.validate_truth(fm) == []


# ─── ID-Form → WARN ───
def test_id_without_dot_is_warn():
    fm = _valid_truth()
    fm["id"] = "W01"
    assert any("id" in m for m in _warns(ts.validate_truth(fm)))


def test_id_suffix_mismatch_local_id_is_warn():
    fm = _valid_truth()
    fm["id"] = "BL-309-truth-migration.W99"  # endet nicht auf .W01
    assert any("local_id" in m or "id" in m for m in _warns(ts.validate_truth(fm)))


# ─── content_hash (Git-CAS) → WARN bei Malformed ───
def test_bad_content_hash_is_warn():
    fm = _valid_truth()
    fm["content_hash"] = "xyz"
    assert any("content_hash" in m for m in _warns(ts.validate_truth(fm)))


def test_good_content_hash_ok():
    fm = _valid_truth()
    fm["content_hash"] = "a" * 64
    assert ts.validate_truth(fm) == []


# ─── typisierte Kanten (RDF-Lektion) → WARN bei untypisiert/unbekannt ───
def test_untyped_edge_string_is_warn():
    fm = _valid_truth()
    fm["edges"] = ["BL-309-truth-migration.W02"]
    assert any("edges" in m or "untypisiert" in m for m in _warns(ts.validate_truth(fm)))


def test_unknown_edge_rel_is_warn():
    fm = _valid_truth()
    fm["edges"] = [{"rel": "magic", "ziel": "BL-309-truth-migration.W02"}]
    assert any("rel" in m for m in _warns(ts.validate_truth(fm)))


def test_typed_edge_ok():
    fm = _valid_truth()
    fm["edges"] = [{"rel": "depends_on", "ziel": "BL-309-truth-migration.W02"}]
    assert ts.validate_truth(fm) == []


# ─── Schema v2 (R1 referenced_by · R2 lifecycle · R3 keywords) ───
def test_lifecycle_valid_members():
    for lc in ts.LIFECYCLE_VALUES:
        fm = _valid_truth()
        fm["lifecycle"] = lc
        assert _errors(ts.validate_truth(fm)) == []


def test_invalid_lifecycle_is_error():
    fm = _valid_truth()
    fm["lifecycle"] = "gefuehlt_reif"
    assert any("lifecycle" in m for m in _errors(ts.validate_truth(fm)))


def test_lifecycle_absent_is_ok():
    fm = _valid_truth()  # kein lifecycle -> optional, kein issue
    assert ts.validate_truth(fm) == []


def test_referenced_by_typed_ok():
    fm = _valid_truth()
    fm["referenced_by"] = [{"by": "BL-x.PL-3", "kind": "pl_source_w"}]
    assert ts.validate_truth(fm) == []


def test_referenced_by_untyped_is_warn():
    fm = _valid_truth()
    fm["referenced_by"] = ["BL-x.PL-3"]
    assert any("referenced_by" in m for m in _warns(ts.validate_truth(fm)))


def test_referenced_by_unknown_kind_is_warn():
    fm = _valid_truth()
    fm["referenced_by"] = [{"by": "x", "kind": "magic"}]
    assert any("kind" in m for m in _warns(ts.validate_truth(fm)))


def test_keywords_list_ok():
    fm = _valid_truth()
    fm["keywords"] = ["migration", "schema"]
    assert ts.validate_truth(fm) == []


def test_keywords_nonlist_is_warn():
    fm = _valid_truth()
    fm["keywords"] = "migration"
    assert any("keywords" in m for m in _warns(ts.validate_truth(fm)))
