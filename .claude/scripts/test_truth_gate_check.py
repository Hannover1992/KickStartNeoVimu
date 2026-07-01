#!/usr/bin/env python3
"""Tests fuer truth_gate_check.py (BL-309 Pre-Flight Gate-Strasse; tmp-Vault, read-only)."""
from __future__ import annotations

import truth_gate_check as gc


def _mk(p, content):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def test_all_gates_pass_clean_vault(tmp_path):
    # HEADING-ready (kein Preamble) + SEGMENT-ready (Bullet) -> alle 10 Gates gruen, EXTRACTION-GO.
    _mk(tmp_path / "Backlog" / "BL-1" / "2_Model" / "H_Model.md", "### W01\nEine Wahrheit.\n\n### W02\nZwei.\n")
    _mk(tmp_path / "Backlog" / "BL-2" / "2_Model" / "S_Model.md", "- W1: erste Wahrheit\n- W2: zweite Wahrheit\n")
    rep = gc.run_gates(tmp_path / "Backlog", None, jobs=1)
    assert rep["gates_total"] == 10
    assert rep["gates_passed"] == 10, [s for s in rep["steps"] if not s["pass"]]
    assert rep["extraction_go"] is True
    assert rep["ready"] == 2 and rep["quarantine"] == 0


def test_titled_preamble_is_content_lossless_gate4(tmp_path):
    # BL-396: ein Model MIT Titel-Preamble wuerde auf dem HEADING-Pfad Content verlieren -> der Router
    # schickt es auf SEGMENT (byte-identisch) -> Gate 4 (Content-Erhalt) bleibt GRUEN (kein Silent-Loss).
    _mk(tmp_path / "Backlog" / "BL-1" / "2_Model" / "T_Model.md",
        "# Mein Titel\n\nWichtiger Intro-Absatz vor den Wahrheiten.\n\n### W01\nErste.\n\n### W02\nZweite.\n")
    rep = gc.run_gates(tmp_path / "Backlog", None, jobs=1)
    g4 = next(s for s in rep["steps"] if s["step"] == 4)
    assert g4["pass"] is True and g4["detail"]["content_loss_models"] == 0
    assert rep["extraction_go"] is True


def test_quarantine_model_handled_gate7_gate8(tmp_path):
    # Prosa ohne W-Definition = Quarantaene. Gate 7 (Determinismus: Partition + Gruende) + Gate 8 (REFUSED)
    # bleiben gruen; die Extraktion ist GO (Quarantaene korrekt ausgeschlossen, nicht still verloren).
    _mk(tmp_path / "Backlog" / "BL-1" / "2_Model" / "H_Model.md", "### W01\nEine Wahrheit.\n\n### W02\nZwei.\n")
    _mk(tmp_path / "Backlog" / "BL-9" / "2_Model" / "P_Model.md", "# Titel\n\nNur Fliesstext ohne jeden W-Knoten.\n")
    rep = gc.run_gates(tmp_path / "Backlog", None, jobs=1)
    assert rep["ready"] == 1 and rep["quarantine"] == 1
    g7 = next(s for s in rep["steps"] if s["step"] == 7)
    g8 = next(s for s in rep["steps"] if s["step"] == 8)
    assert g7["pass"] is True and g7["detail"]["every_quarantine_has_reasons"] is True
    assert g8["pass"] is True and g8["detail"]["quarantine_refused"] == "1/1"
    assert rep["extraction_go"] is True   # Quarantaene blockt die Extraktion NICHT (sie wird korrekt exkludiert)


def test_gate_report_shape(tmp_path):
    _mk(tmp_path / "Backlog" / "BL-1" / "2_Model" / "H_Model.md", "### W01\nEins.\n")
    rep = gc.run_gates(tmp_path / "Backlog", None, jobs=1)
    assert [s["step"] for s in rep["steps"]] == list(range(1, 11))      # 10 Schritte, geordnet
    for s in rep["steps"]:
        assert set(s) == {"step", "name", "pass", "detail"}
    assert "write_fenced" in rep                                        # der Cutover bleibt explizit gefenced


def test_disk_rebuild_and_cutover_on_temp_only(tmp_path):
    # Sicherheit: die Write-Pfad-Gates fassen den Quell-Vault NICHT an (nur temp). Quell-Model unveraendert.
    model = tmp_path / "Backlog" / "BL-1" / "2_Model" / "S_Model.md"
    _mk(model, "- W1: erste\n- W2: zweite\n")
    before = model.read_bytes()
    rep = gc.run_gates(tmp_path / "Backlog", None, jobs=1)
    g9 = next(s for s in rep["steps"] if s["step"] == 9)
    assert g9["pass"] is True
    assert model.read_bytes() == before                                # Quelle UNBERUEHRT (read-only)
    assert not (model.parent / "truths").exists()                      # kein Write in den Quell-Vault
    assert not (model.parent / "_legacy").exists()
