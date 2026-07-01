#!/usr/bin/env python3
"""Tests fuer truth_migrate_orchestrator.py (BL-386 read-only Spine)."""
from __future__ import annotations

import truth_migrate_orchestrator as orch


def _mk(p, content):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_bl_folder_of_finds_ticket_ancestor(tmp_path):
    mp = tmp_path / "Backlog" / "BL-309-slug" / "2_Model" / "Foo_Model.md"
    _mk(mp, "### W01\nx\n")
    assert orch._bl_folder_of(mp).name == "BL-309-slug"


def test_bl_folder_of_repo_model_is_none(tmp_path):
    mp = tmp_path / "models" / "Foo_Model.md"
    _mk(mp, "### W01\nx\n")
    assert orch._bl_folder_of(mp) is None


def test_process_bl_unit_ready_with_backrefs(tmp_path):
    bl = tmp_path / "Backlog" / "BL-1"
    _mk(bl / "2_Model" / "Foo_Model.md", "### W01\nEine Wahrheit.\n\n### W02\nZwei.\n")
    _mk(bl / "6_PL" / "pl.md", "PL deckt W01 ab.")
    r = orch.process_bl_unit(str(bl / "2_Model" / "Foo_Model.md"))
    assert r["ready"] is True
    assert r["knots"] == 2
    assert r["backref_count"] == 1  # nur W01 wird von PL referenziert


def test_run_global_report(tmp_path):
    bl = tmp_path / "Backlog" / "BL-1"
    _mk(bl / "2_Model" / "Foo_Model.md", "### W01\nEins.\n")
    _mk(bl / "6_PL" / "pl.md", "W01 referenziert.")
    rep = orch.run(tmp_path / "Backlog", None, jobs=1)
    assert rep["models"] == 1
    assert rep["ready"] == 1
    assert rep["referenced_by_coverage"] == 1


def test_write_is_hard_fenced_no_mutation(tmp_path):
    bl = tmp_path / "Backlog" / "BL-1"
    _mk(bl / "2_Model" / "Foo_Model.md", "### W01\nEins.\n")
    rep = orch.run(tmp_path / "Backlog", None, jobs=1, write=True)
    assert rep["write_fenced"] is not None
    assert not (bl / "2_Model" / "truths").exists()  # NICHTS geschrieben


def test_mode_bl_filters(tmp_path):
    _mk(tmp_path / "Backlog" / "BL-1" / "2_Model" / "A_Model.md", "### W01\nx\n")
    _mk(tmp_path / "Backlog" / "BL-2" / "2_Model" / "B_Model.md", "### W02\ny\n")
    rep = orch.run(tmp_path / "Backlog", None, mode="bl:BL-1", jobs=1)
    assert rep["models"] == 1


def test_threaded_jobs2_same_ready(tmp_path):
    for n in ("A", "B"):
        _mk(tmp_path / "Backlog" / f"BL-{n}" / "2_Model" / f"{n}_Model.md", "### W01\nx\n")
    seq = orch.run(tmp_path / "Backlog", None, jobs=1)
    par = orch.run(tmp_path / "Backlog", None, jobs=2)
    assert seq["ready"] == par["ready"] == 2


def test_process_bl_unit_range_resolved_by_atomization(tmp_path):
    # BL-391 (A)+(B): (A) atomisiert die Member -> process_bl_unit meldet KEINEN Kollaps mehr.
    bl = tmp_path / "Backlog" / "BL-50"
    _mk(bl / "2_Model" / "DW_Model.md", "### W16-W19: WIDERLEGT\n- W16: a\n- W17: b\n- W18: c\n- W19: d\n")
    r = orch.process_bl_unit(str(bl / "2_Model" / "DW_Model.md"))
    assert r["range_collapsed"] is False
    assert r["collapsed_ids"] == []
    assert r["knots"] == 4   # Gruppe W16 + Kinder W17/W18/W19 (atomar)


def test_run_range_resolved_no_surface(tmp_path):
    # Regression-Guard: feuert wieder, falls (A) bricht (atomize keine Kinder mehr emittiert).
    bl = tmp_path / "Backlog" / "BL-50"
    _mk(bl / "2_Model" / "DW_Model.md", "### W1-W3\n- W1: a\n- W2: b\n- W3: c\n")
    rep = orch.run(tmp_path / "Backlog", None, jobs=1)
    assert rep["range_collapse"] == []


def test_run_quarantine_manifest_bl395(tmp_path):
    # BL-395: die Quarantaene ist ein erstklassiger, deterministischer MASCHINEN-Output (per-Model + Grund).
    # Post-B2: ein No-W-Def-Prosa-Model bleibt quarantaeniert (nicht recoverbar); ein Bullet-Model wird von
    # B2 recovert -> NICHT mehr quarantaeniert.
    _mk(tmp_path / "Backlog" / "BL-90" / "2_Model" / "Prosa_Model.md", "# Titel\n\nNur Fliesstext ohne W-Knoten.\n")
    _mk(tmp_path / "Backlog" / "BL-91" / "2_Model" / "Bullet_Model.md", "# B\n\n- W1: a\n- W2: b\n")
    rep = orch.run(tmp_path / "Backlog", None, jobs=1)
    qmodels = {e["model"]: e["reasons"] for e in rep["quarantine"]}
    p_reasons = [r for m, r in qmodels.items() if m.endswith("Prosa_Model.md")]
    assert p_reasons and "low_byte_coverage" in p_reasons[0]          # No-W -> quarantaeniert, mit Grund
    assert not any(m.endswith("Bullet_Model.md") for m in qmodels)   # B2 recovert -> NICHT quarantaeniert   # ready -> NICHT in Quarantaene


def test_quarantine_reasons_helper_bl395():
    # deterministische Gruende, eine pro Gate-Dimension; ready -> leer.
    assert orch.quarantine_reasons({"roundtrip_ok": True, "complete": True}) == []
    r = orch.quarantine_reasons({"roundtrip_ok": True, "complete": False, "low_coverage": True, "range_collapsed": True, "schema_errors": 2})
    assert set(r) == {"truth_count_loss", "low_byte_coverage", "range_collapse", "schema_error"}


def test_process_bl_unit_bullet_recovered_by_b2(tmp_path):
    # B2: das Bullet-Model wird jetzt via SEGMENT-Pfad atomisiert (RECOVERED) — knots==census, ready.
    # (Vor B2 fing es der Loss-Gate als Silent-Loss; B2 holt es verlustfrei zurueck, View==Source.)
    bl = tmp_path / "Backlog" / "BL-90"
    _mk(bl / "2_Model" / "Konsolidiert_Model.md", "# Konsolidiert\n\n- W1: a\n- W2: b\n- W3: c\n")
    r = orch.process_bl_unit(str(bl / "2_Model" / "Konsolidiert_Model.md"))
    assert r["knots"] == 3            # 3 Bullet-Definitionen atomisiert (Segment-Pfad)
    assert r["complete"] is True     # 3 >= census 3
    assert r["ready"] is True        # recovered, nicht mehr quarantaeniert
