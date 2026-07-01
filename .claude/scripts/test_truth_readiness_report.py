#!/usr/bin/env python3
"""Tests fuer truth_readiness_report.py (BL-309 Pre-Flight GO/NO-GO)."""
from __future__ import annotations

import truth_readiness_report as rr


def _mk(p, content):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_go_for_pilot_all_ready():
    assert rr.go_for_pilot([{"ready": True}, {"ready": True}]) is True


def test_go_for_pilot_false_if_one_not_ready():
    assert rr.go_for_pilot([{"ready": True}, {"ready": False}]) is False


def test_go_for_pilot_empty_is_false():
    assert rr.go_for_pilot([]) is False


def test_compose_happy_fixture(tmp_path):
    bl = tmp_path / "Backlog" / "BL-1"
    _mk(bl / "2_Model" / "Foo_Model.md", "### W01\nEine Wahrheit ueber Migration.\n")
    _mk(bl / "6_PL" / "pl.md", "W01 referenziert.")
    rep = rr.compose(tmp_path / "Backlog", None, jobs=1)
    assert rep["models"] == 1
    assert rep["go_for_pilot"] is True
    assert rep["referenced_by_coverage"] == 1
    assert "graph" in rep and "srs" in rep and "dedup" in rep


def test_compose_sections_complete(tmp_path):
    bl = tmp_path / "Backlog" / "BL-2"
    _mk(bl / "2_Model" / "B_Model.md", "### W01\nEins.\n\n### W02\nZwei haengt von W01 ab.\n")
    rep = rr.compose(tmp_path / "Backlog", None, jobs=1)
    # W02 referenziert W01 im Text -> forward-edge -> Graph hat eine Kante
    assert rep["graph"]["edges"] >= 1
    assert rep["knots"] == 2


def test_compose_includes_verify_clean_in_go(tmp_path):
    # GO bezieht jetzt INV-MIG-10 (verify clean) ein
    bl = tmp_path / "Backlog" / "BL-1"
    _mk(bl / "2_Model" / "Foo_Model.md", "### W01\nEins.\n")
    rep = rr.compose(tmp_path / "Backlog", None, jobs=1)
    assert rep["verify"]["clean"] is True and rep["verify"]["id_collisions"] == 0
    assert rep["go_for_pilot"] is True  # ready UND clean
    assert rep["range_collapse"] == []  # BL-391: kein Kollaps bei Einzel-Headings


def test_compose_atomized_range_does_not_block_go(tmp_path):
    # BL-391 (A)+(B): (A) atomisiert die Member -> range_collapse cleart -> GO nicht mehr durch Range blockiert.
    bl = tmp_path / "Backlog" / "BL-50"
    _mk(bl / "2_Model" / "DW_Model.md", "### W16-W19: WIDERLEGT\n- W16: a\n- W17: b\n- W18: c\n- W19: d\n")
    rep = rr.compose(tmp_path / "Backlog", None, jobs=1)
    assert rep["range_collapse_count"] == 0
    assert rep["range_collapse"] == []
    assert rep["go_for_pilot"] is True   # Range aufgeloest -> GO flippt True (Interlock)


def test_compose_unsliceable_range_still_blocks_go_via_schema(tmp_path):
    # Schutz erhalten: Range ohne parsebare Member -> leere Kind-Slices -> Schema-ERROR -> GO ehrlich False.
    bl = tmp_path / "Backlog" / "BL-51"
    _mk(bl / "2_Model" / "E_Model.md", "### W16-W19: nur Prosa\nFliesstext ohne W-Member-Zeile.\n")
    rep = rr.compose(tmp_path / "Backlog", None, jobs=1)
    assert rep["go_for_pilot"] is False  # leere Member-Truths -> nicht ready


def test_compose_quarantine_manifest_bl395(tmp_path):
    # BL-395: compose emittiert die Quarantaene-Liste (per-Model + Grund). Post-B2: ein No-W-Def-Prosa-Model
    # bleibt quarantaeniert (nicht recoverbar).
    _mk(tmp_path / "Backlog" / "BL-90" / "2_Model" / "Prosa_Model.md", "# Titel\n\nNur Fliesstext ohne W-Knoten.\n")
    rep = rr.compose(tmp_path / "Backlog", None, jobs=1)
    assert rep["quarantine_count"] >= 1
    assert all(e["reasons"] for e in rep["quarantine"])   # jedes Quarantaene-Item hat >=1 Grund


def test_compose_bullet_recovered_b2_go_true(tmp_path):
    # B2: ein Bullet-Model allein wird via Segment-Pfad recovert -> ready -> GO True (B2 hebt die
    # Quarantaene auf, View==Source byte-identisch). Vor B2 blockierte dieses Model GO.
    bl = tmp_path / "Backlog" / "BL-90"
    _mk(bl / "2_Model" / "K_Model.md", "# K\n\n- W1: a\n- W2: b\n")
    rep = rr.compose(tmp_path / "Backlog", None, jobs=1)
    assert rep["go_for_pilot"] is True
    assert rep["quarantine_count"] == 0


def test_compose_no_wdef_prose_blocks_go_bl395(tmp_path):
    # Safety bleibt: ein No-W-Def-Prosa-Model ist nicht recoverbar -> quarantaeniert -> GO ehrlich False.
    bl = tmp_path / "Backlog" / "BL-92"
    _mk(bl / "2_Model" / "Prosa_Model.md", "# Titel\n\nNur Fliesstext ohne W-Knoten hier.\n")
    rep = rr.compose(tmp_path / "Backlog", None, jobs=1)
    assert rep["go_for_pilot"] is False
