#!/usr/bin/env python3
"""Tests fuer truth_consume.py (BL-387 Konsumenten-API)."""
from __future__ import annotations

import truth_consume as tc


def _mk_truth(truths_dir, lid, text, typ="FESTSTELLUNG", lifecycle="asserted"):
    truths_dir.mkdir(parents=True, exist_ok=True)
    (truths_dir / f"{lid}.md").write_text(
        f"---\ntype: truth\nid: BL-x.{lid}\nlocal_id: {lid}\ntext: {text}\n"
        f"typ: {typ}\nherkunft: INTERN\nstatus: BESTAETIGT\ntruth_grade: code_verified\n"
        f"lifecycle: {lifecycle}\n---\n",
        encoding="utf-8",
    )


def test_value_resolves_atomic(tmp_path):
    bl = tmp_path / "BL-x"
    _mk_truth(bl / "2_Model" / "truths", "W01", "Eine Wahrheit", lifecycle="experiment_proven")
    v = tc.value("W01", bl_folder=bl)
    assert v["found"] and v["text"] == "Eine Wahrheit" and v["lifecycle"] == "experiment_proven"
    assert v["source"] == "atomic"


def test_value_unresolved_is_loud():
    v = tc.value("W99", bl_folder=None)
    assert v["found"] is False


def test_is_open_via_lifecycle(tmp_path):
    bl = tmp_path / "BL-x"
    _mk_truth(bl / "2_Model" / "truths", "W01", "x", lifecycle="asserted")
    _mk_truth(bl / "2_Model" / "truths", "W02", "y", lifecycle="experiment_proven")
    assert tc.is_open("W01", bl_folder=bl) is True
    assert tc.is_open("W02", bl_folder=bl) is False


def test_is_open_frage_always(tmp_path):
    bl = tmp_path / "BL-x"
    _mk_truth(bl / "2_Model" / "truths", "W01", "x", typ="FRAGE", lifecycle="experiment_proven")
    assert tc.is_open("W01", bl_folder=bl) is True  # FRAGE inhaerent offen


def test_is_open_unresolved_is_none():
    assert tc.is_open("W99", bl_folder=None) is None


def test_srs_for_refs(tmp_path):
    bl = tmp_path / "BL-x"
    _mk_truth(bl / "2_Model" / "truths", "W01", "x", lifecycle="asserted")
    _mk_truth(bl / "2_Model" / "truths", "W02", "y", lifecycle="experiment_proven")
    r = tc.srs_for(["W01", "W02", "W99"], bl_folder=bl)  # W99 unaufloesbar
    assert r["w_total"] == 2 and r["w_open"] == 1 and r["srs"] == 50
    assert r["unresolved_refs"] == 1
