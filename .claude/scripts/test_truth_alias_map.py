#!/usr/bin/env python3
"""Tests fuer truth_alias_map.py (BL-309 R4 / BL-386 Runbook Schritt 4; tmp, kein Real-Vault)."""
from __future__ import annotations

import truth_alias_map as am
import truth_resolver as tr


def _t(lid, h, text="x"):
    return {"id": f"BL-x.{lid}", "local_id": lid, "content_hash": h, "text": text}


def test_build_alias_map_dedup():
    # W01/W02 byte-gleich -> W02 (nicht-kanonisch) loest auf W01 (kleinste id = kanonisch).
    amap = am.build_alias_map([_t("W01", "h1"), _t("W02", "h1"), _t("W03", "h2")])
    assert amap == {"BL-x.W02": {"resolves_to": "BL-x.W01", "reason": "dedup_content_hash"}}


def test_build_alias_map_no_dups_is_empty():
    assert am.build_alias_map([_t("W01", "h1"), _t("W02", "h2")]) == {}


def test_write_then_load_via_resolver(tmp_path):
    # Beweis: das geschriebene Format ist truth_resolver-kompatibel (Stufe 2).
    amap = am.build_alias_map([_t("W01", "h1"), _t("W02", "h1")])
    res = am.write_alias_map(amap, tmp_path)
    assert res["written"] == 1
    loaded = tr.load_alias_map(tmp_path)
    assert loaded["BL-x.W02"]["resolves_to"] == "BL-x.W01"


def test_merge_preserves_existing_and_flags_conflict():
    existing = {"BL-x.W02": {"resolves_to": "BL-x.W01"}}
    new = {"BL-x.W02": {"resolves_to": "BL-x.W99"}, "BL-x.W05": {"resolves_to": "BL-x.W04"}}
    merged, conflicts = am.merge_alias_map(existing, new)
    assert merged["BL-x.W02"]["resolves_to"] == "BL-x.W01"  # never-renumber: bestehendes bleibt
    assert merged["BL-x.W05"]["resolves_to"] == "BL-x.W04"  # neues ergaenzt
    assert len(conflicts) == 1 and conflicts[0]["alias"] == "BL-x.W02"


def test_write_merge_never_renumbers_on_rewrite(tmp_path):
    am.write_alias_map({"BL-x.W02": {"resolves_to": "BL-x.W01"}}, tmp_path)
    res = am.write_alias_map({"BL-x.W02": {"resolves_to": "BL-x.W99"}}, tmp_path)  # Konflikt
    assert len(res["conflicts"]) == 1
    loaded = tr.load_alias_map(tmp_path)
    assert loaded["BL-x.W02"]["resolves_to"] == "BL-x.W01"  # NIE still ueberschrieben
