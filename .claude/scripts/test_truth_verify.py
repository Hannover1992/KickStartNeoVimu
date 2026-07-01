#!/usr/bin/env python3
"""Tests fuer truth_verify.py (BL-309 Schritt 9 / INV-MIG-Verifikation)."""
from __future__ import annotations

import truth_verify as v


def _t(tid, lid, edges=None):
    d = {"id": tid, "local_id": lid}
    if edges:
        d["edges"] = [{"rel": "relates_to", "ziel": z} for z in edges]
    return d


def test_id_collision_detected():
    truths = [_t("BL-a.W01", "W01"), _t("BL-a.W01", "W01")]
    assert "BL-a.W01" in v.check_id_uniqueness(truths)


def test_no_collision_for_distinct_global_ids():
    truths = [_t("BL-a.W01", "W01"), _t("BL-b.W01", "W01")]  # gleiche local_id, andere BLs
    assert v.check_id_uniqueness(truths) == {}


def test_id_local_inconsistency_flagged():
    truths = [_t("BL-a.W99", "W01")]  # id endet .W99, local_id W01
    assert v.check_id_local_consistency(truths) == [{"id": "BL-a.W99", "local_id": "W01"}]


def test_reference_resolution_unresolved():
    truths = [_t("BL-a.W01", "W01", edges=["W99"])]
    assert v.check_reference_resolution(truths) == [{"from": "BL-a.W01", "to": "BL-a.W99"}]


def test_reference_resolution_resolved():
    truths = [_t("BL-a.W01", "W01", edges=["W02"]), _t("BL-a.W02", "W02")]
    assert v.check_reference_resolution(truths) == []


def test_verify_all_clean():
    r = v.verify_all([_t("BL-a.W01", "W01"), _t("BL-a.W02", "W02")])
    assert r["clean"] is True and r["id_collision_count"] == 0


def test_verify_all_dirty_on_collision():
    assert v.verify_all([_t("BL-a.W01", "W01"), _t("BL-a.W01", "W01")])["clean"] is False
