#!/usr/bin/env python3
"""Tests fuer truth_pilot_cutover.py (BL-385/386 Pilot-Cutover; tmp-Vault, DRY-RUN default)."""
from __future__ import annotations

import truth_pilot_cutover as pc


def _mk(p, content):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _vault(tmp_path):
    """Mini-Vault: 1 ready HEADING + 1 ready SEGMENT + 1 ready-aber-Owner-Scope-out (BL-199_Model) + 1 Prosa-Quarantaene."""
    _mk(tmp_path / "Backlog" / "BL-1" / "2_Model" / "H_Model.md", "### W01\nEine Wahrheit.\n\n### W02\nZwei.\n")
    _mk(tmp_path / "Backlog" / "BL-2" / "2_Model" / "S_Model.md", "- W1: erste Wahrheit\n- W2: zweite\n")
    _mk(tmp_path / "Backlog" / "BL-199" / "2_Model" / "BL-199_Model.md", "### W01\nReady aber per Owner ausgeschlossen.\n")
    _mk(tmp_path / "Backlog" / "BL-9" / "2_Model" / "P_Model.md", "# Titel\n\nNur Fliesstext ohne W-Knoten.\n")
    return tmp_path / "Backlog"


def test_plan_excludes_owner_scopeout_and_quarantine(tmp_path):
    pl = pc.plan(_vault(tmp_path), None, jobs=1)
    scope = {pc.Path(s["model"]).name for s in pl["write_scope"]}
    skipped = {pc.Path(s["model"]).name: s["reason"] for s in pl["skipped"]}
    assert scope == {"H_Model.md", "S_Model.md"}                         # nur ready + nicht-exkludiert
    assert skipped["BL-199_Model.md"] == "owner_scope_out"               # ready, aber explizit Owner-Scope-out
    assert "quarantine" in skipped["P_Model.md"]                         # Prosa -> Quarantaene (mit Grund)


def test_dry_run_default_writes_nothing(tmp_path):
    vault = _vault(tmp_path)
    rep = pc.execute(vault, None, jobs=1)                                 # confirm default False
    assert rep["dry_run"] is True
    assert set(pc.Path(m).name for m in rep["would_cutover"]) == {"H_Model.md", "S_Model.md"}
    # KEINE Mutation: keine truths/ oder _legacy irgendwo, Models byte-unveraendert
    for sub in ("BL-1", "BL-2", "BL-199", "BL-9"):
        assert not (vault / sub / "2_Model" / "truths").exists()
        assert not (vault / sub / "2_Model" / "_legacy").exists()


def test_confirm_cutover_then_rollback_byte_identical(tmp_path):
    vault = _vault(tmp_path)
    h = vault / "BL-1" / "2_Model" / "H_Model.md"
    s = vault / "BL-2" / "2_Model" / "S_Model.md"
    excl = vault / "BL-199" / "2_Model" / "BL-199_Model.md"
    h0, s0, e0 = h.read_bytes(), s.read_bytes(), excl.read_bytes()

    rep = pc.execute(vault, None, confirm=True, jobs=1, require_gate_go=False)
    assert rep["dry_run"] is False and rep["cutover_ok"] == 2
    assert (vault / "BL-1" / "2_Model" / "truths").exists()              # Scope geschrieben
    assert excl.read_bytes() == e0                                       # Owner-Scope-out UNBERUEHRT

    rb = pc.rollback(vault, None, jobs=1)
    assert rb["restored"] == 2
    assert h.read_bytes() == h0 and s.read_bytes() == s0                 # INV-MIG-11 byte-identisch


def test_limit_pilot_trio(tmp_path):
    rep = pc.execute(_vault(tmp_path), None, jobs=1, limit=1)             # Dry-Run, nur 1 Model
    assert rep["scope_count"] == 1


def test_gate_go_required_aborts_when_not_go(tmp_path, monkeypatch):
    # INV-MIG-GATE: execute bricht ab, wenn die Gate-Strasse kein EXTRACTION-GO liefert.
    monkeypatch.setattr(pc.gc, "run_gates",
                        lambda *a, **k: {"extraction_go": False, "steps": [{"name": "content_preservation", "pass": False}]})
    rep = pc.execute(_vault(tmp_path), None, confirm=True, jobs=1)
    assert rep.get("aborted") == "gate_not_go"
    assert "content_preservation" in rep["failed_gates"]
