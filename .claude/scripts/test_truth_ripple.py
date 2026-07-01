#!/usr/bin/env python3
"""Tests fuer truth_ripple.py (BL-388 / Kaskaden-Berechnung)."""
from __future__ import annotations

import truth_ripple as rp
import truth_graph as tg


def _t(lid, edges=None, ref_by=None):
    d = {"local_id": lid, "id": f"BL-x.{lid}"}
    if edges:
        d["edges"] = [{"rel": "relates_to", "ziel": z} for z in edges]
    if ref_by:
        d["referenced_by"] = ref_by
    return d


def test_cascade_chain_transitive():
    # W01 -> W02 -> W03 (referenziert). Invalidiere W03 -> W02 + W01 betroffen.
    g = tg.build_graph([_t("W01", edges=["W02"]), _t("W02", edges=["W03"]), _t("W03")])
    assert rp.cascade("BL-x.W03", g) == {"BL-x.W01", "BL-x.W02"}


def test_cascade_leaf_no_dependents():
    g = tg.build_graph([_t("W01", edges=["W02"]), _t("W02")])
    assert rp.cascade("BL-x.W01", g) == set()  # niemand referenziert W01


def test_cascade_cycle_safe():
    g = tg.build_graph([_t("W01", edges=["W02"]), _t("W02", edges=["W01"])])
    assert rp.cascade("BL-x.W01", g) == {"BL-x.W02"}  # kein Hang


def test_cascade_max_depth():
    g = tg.build_graph([_t("W01", edges=["W02"]), _t("W02", edges=["W03"]), _t("W03")])
    assert rp.cascade("BL-x.W03", g, max_depth=1) == {"BL-x.W02"}  # nur direkter Referenzierer


def test_affected_external_notify():
    truths = [_t("W01", edges=["W02"], ref_by=[{"by": "pl-3", "kind": "pl_source_w"}]), _t("W02")]
    g = tg.build_graph(truths)
    affected = rp.cascade("BL-x.W02", g)  # W01 referenziert W02 -> betroffen
    by_id = {t["id"]: t for t in truths}
    assert rp.affected_external(affected, by_id) == [{"truth": "BL-x.W01", "by": "pl-3", "kind": "pl_source_w"}]


def test_ripple_report():
    truths = [_t("W01", edges=["W02"]), _t("W02")]
    g = tg.build_graph(truths)
    by_id = {t["id"]: t for t in truths}
    r = rp.ripple_report("BL-x.W02", g, by_id)
    assert r["invalidated"] == "BL-x.W02"
    assert r["affected_truths"] == ["BL-x.W01"]
    assert r["affected_count"] == 1
