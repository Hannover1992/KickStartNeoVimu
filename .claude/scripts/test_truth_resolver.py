#!/usr/bin/env python3
"""Tests fuer truth_resolver.py (BL-309 Phase A2 / Dual-Read)."""
from __future__ import annotations

import json

import truth_resolver as tr


def _mk_truth(truths_dir, local_id, text, tid=None):
    truths_dir.mkdir(parents=True, exist_ok=True)
    tid = tid or f"BL-x.{local_id}"
    (truths_dir / f"{local_id}.md").write_text(
        f"---\ntype: truth\nid: {tid}\nlocal_id: {local_id}\ntext: {text}\n"
        f"typ: FESTSTELLUNG\nherkunft: INTERN\nstatus: BESTAETIGT\ntruth_grade: code_verified\n---\n\n# {local_id}\n",
        encoding="utf-8",
    )


def test_split_ref():
    assert tr.split_ref("BL-309-slug.W01") == ("BL-309-slug", "W01")
    assert tr.split_ref("W01") == (None, "W01")


def test_atomic_resolution(tmp_path):
    bl = tmp_path / "BL-x"
    _mk_truth(bl / "2_Model" / "truths", "W01", "Erste Wahrheit", tid="BL-x.W01")
    r = tr.resolve("BL-x.W01", bl_folder=bl)
    assert r.found and r.source == tr.SOURCE_ATOMIC
    assert r.resolved_id == "BL-x.W01"
    assert r.truth["text"] == "Erste Wahrheit"


def test_atomic_by_bare_local_id(tmp_path):
    bl = tmp_path / "BL-x"
    _mk_truth(bl / "2_Model" / "truths", "W01", "X")
    assert tr.resolve("W01", bl_folder=bl).source == tr.SOURCE_ATOMIC


def test_alias_resolution(tmp_path):
    bl = tmp_path / "BL-x"
    _mk_truth(bl / "2_Model" / "truths", "W01", "Ziel")
    meta = tmp_path / "_meta"
    meta.mkdir()
    (meta / "truth_alias_map.json").write_text(
        json.dumps([{"old_ref": "W99", "resolves_to": "W01", "reason": "modelsplit_renumber"}]),
        encoding="utf-8",
    )
    r = tr.resolve("W99", bl_folder=bl, vault_root=tmp_path)
    assert r.found and r.source == tr.SOURCE_ALIAS
    assert r.truth["text"] == "Ziel"


def test_legacy_parse_stops_at_next_heading(tmp_path):
    bl = tmp_path / "BL-x"
    (bl / "2_Model").mkdir(parents=True)
    (bl / "2_Model" / "Foo_Model.md").write_text(
        "# Model\n\n### W05\nLegacy Body Text.\n\n### W06\nAndere.\n", encoding="utf-8"
    )
    r = tr.resolve("W05", bl_folder=bl)
    assert r.found and r.source == tr.SOURCE_LEGACY
    assert "Legacy Body Text." in r.truth["text"]
    assert "Andere" not in r.truth["text"]


def test_atomic_beats_legacy(tmp_path):
    bl = tmp_path / "BL-x"
    _mk_truth(bl / "2_Model" / "truths", "W01", "Atomar")
    (bl / "2_Model" / "Foo_Model.md").write_text("### W01\nLegacy.\n", encoding="utf-8")
    r = tr.resolve("W01", bl_folder=bl)
    assert r.source == tr.SOURCE_ATOMIC and r.truth["text"] == "Atomar"


def test_repo_fallback(tmp_path):
    repo = tmp_path / "models"
    repo.mkdir()
    (repo / "Meta_Model.md").write_text("### W09\nRepo Wahrheit.\n", encoding="utf-8")
    r = tr.resolve("W09", repo_models=repo)
    assert r.found and r.source == tr.SOURCE_REPO


def test_not_found_is_loud_not_silent(tmp_path):
    r = tr.resolve("W42", bl_folder=tmp_path / "nope")
    assert not r.found and r.source == tr.SOURCE_NOT_FOUND


def test_extract_wknot_legacy():
    txt = "### W01\nEins.\n### W02\nZwei.\n"
    assert tr.extract_wknot_legacy(txt, "W01")["text"] == "Eins."
    assert tr.extract_wknot_legacy(txt, "W02")["text"] == "Zwei."
    assert tr.extract_wknot_legacy(txt, "W99") is None


def test_dashed_local_id_legacy():
    txt = "## W-IST-1\nDashed body.\n## W-IST-2\nNext.\n"
    assert tr.extract_wknot_legacy(txt, "W-IST-1")["text"] == "Dashed body."


def test_resolve_truth_refs_over_text(tmp_path):
    bl = tmp_path / "BL-x"
    _mk_truth(bl / "2_Model" / "truths", "W01", "A")
    _mk_truth(bl / "2_Model" / "truths", "W02", "B")
    res = tr.resolve_truth_refs("Siehe W01 und W02 dazu.", bl_folder=bl)
    assert set(res) == {"W01", "W02"}
    assert all(v.found for v in res.values())


def test_self_alias_does_not_loop(tmp_path):
    meta = tmp_path / "_meta"
    meta.mkdir()
    (meta / "truth_alias_map.json").write_text(
        json.dumps({"W99": {"resolves_to": "W99"}}), encoding="utf-8"
    )
    r = tr.resolve("W99", vault_root=tmp_path)
    assert not r.found  # self-alias wird uebersprungen, kein Hang
