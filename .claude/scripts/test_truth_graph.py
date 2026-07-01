#!/usr/bin/env python3
"""Tests fuer truth_graph.py (BL-384 / bidirektionaler Wahrheits-Graph als View).

Knoten per GLOBALER id (BL-x.W01) — Cross-BL-Kollision von local_ids verhindert.
"""
from __future__ import annotations

import truth_graph as g


def _t(lid, edges=None, ref_by=0):
    d = {"local_id": lid, "id": f"BL-x.{lid}", "typ": "FESTSTELLUNG", "lifecycle": "asserted"}
    if edges:
        d["edges"] = [{"rel": "relates_to", "ziel": z} for z in edges]
    if ref_by:
        d["referenced_by"] = [{"by": f"pl-{i}", "kind": "pl_source_w"} for i in range(ref_by)]
    return d


def test_build_graph_keys_by_global_id():
    graph = g.build_graph([_t("W01", edges=["W02"]), _t("W02")])
    assert set(graph["nodes"]) == {"BL-x.W01", "BL-x.W02"}
    # edge-ziel (local_id) im Quell-namespace global aufgeloest
    assert graph["edges"] == [{"src": "BL-x.W01", "dst": "BL-x.W02", "rel": "relates_to"}]


def test_cross_bl_local_ids_do_not_collide():
    # zwei BLs mit je W01 -> ZWEI Knoten (nicht ein kollidierter)
    a = {"local_id": "W01", "id": "BL-a.W01"}
    b = {"local_id": "W01", "id": "BL-b.W01"}
    graph = g.build_graph([a, b])
    assert set(graph["nodes"]) == {"BL-a.W01", "BL-b.W01"}


def test_out_and_in_degree():
    graph = g.build_graph([_t("W01", edges=["W02", "W03"]), _t("W02", edges=["W03"]), _t("W03")])
    assert g.out_degree(graph)["BL-x.W01"] == 2
    assert g.in_degree(graph)["BL-x.W03"] == 2


def test_hubs_by_total_degree():
    graph = g.build_graph([_t("W01", edges=["W02"]), _t("W02", edges=["W03"]), _t("W03", edges=["W02"])])
    assert g.hubs(graph, 1)[0][0] == "BL-x.W02"


def test_dangling_edge_detected():
    graph = g.build_graph([_t("W01", edges=["W99"])])  # W99 existiert nicht
    assert g.dangling_edges(graph) == [{"src": "BL-x.W01", "dst": "BL-x.W99", "rel": "relates_to"}]


def test_isolated_node():
    graph = g.build_graph([_t("W01", edges=["W02"]), _t("W02"), _t("W09")])
    assert g.isolated(graph) == ["BL-x.W09"]


def test_ext_refs_make_node_not_isolated():
    graph = g.build_graph([_t("W09", ref_by=1)])
    assert g.isolated(graph) == []
    assert graph["nodes"]["BL-x.W09"]["ext_refs"] == 1


def test_graph_stats():
    graph = g.build_graph([_t("W01", edges=["W02"]), _t("W02"), _t("W09")])
    s = g.graph_stats(graph)
    assert s["nodes"] == 3 and s["edges"] == 1 and s["isolated"] == 1
