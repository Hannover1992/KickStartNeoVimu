#!/usr/bin/env python3
"""Tests fuer roadmap_status.py (der /_roadmap Kompass-Kern)."""
from __future__ import annotations

import roadmap_status as rs


# ── parse_roadmap_order: BL-IDs in Dokument-Reihenfolge, dedupliziert ──

def test_parse_order_document_order_deduped():
    text = "Phase 1 [[BL-397]] dann Phase 2 [[BL-398]]; BL-397 nochmal; dann BL-387 und BL-388."
    assert rs.parse_roadmap_order(text) == ["BL-397", "BL-398", "BL-387", "BL-388"]


def test_parse_order_empty():
    assert rs.parse_roadmap_order("") == []


def test_parse_order_prefers_marked_block():
    # Prosa erwaehnt BL-390/391; der kuratierte ORDER-Block hat die echte Build-Reihenfolge.
    text = (
        "Bla bla BL-390 und BL-391 in der Prosa.\n"
        "<!-- ROADMAP-ORDER:START -->\n1. BL-397\n2. BL-398\n3. BL-387\n<!-- ROADMAP-ORDER:END -->\n"
        "Noch mehr Prosa BL-999.\n"
    )
    assert rs.parse_roadmap_order(text) == ["BL-397", "BL-398", "BL-387"]   # NUR der Block


# ── parse_index: Status + Reifegrad aus der Tabelle ──

def test_parse_index_status_and_reifegrad():
    idx = (
        "| BL-397 | Model-Normalisierung | DRAFT | path.md | 2026-06-18 | 2026-06-18 | hoch | UNREIF |\n"
        "| BL-001 | alt | DONE | p.md | x | y | hoch | REIF |\n"
        "kein Tabellen-Zeile\n"
    )
    parsed = rs.parse_index(idx)
    assert parsed["BL-397"] == {"status": "DRAFT", "reifegrad": "UNREIF"}
    assert parsed["BL-001"]["status"] == "DONE"


# ── next_command_for_bl: das Prozess-Routing (der Kern-Wert) ──

def test_next_unreif_goes_to_a_fresh_lead():
    r = rs.next_command_for_bl("BL-397", "UNREIF", "DRAFT")
    assert r["command"] == "/_A_orchestrate BL-397"
    assert r["fresh_session"] is True
    assert "Mega-Worker" in r["lead"]            # Anti-Mega-Worker-Hinweis IMMER dabei


def test_next_matured_goes_to_idf():
    assert rs.next_command_for_bl("BL-9", "SC-REIF", "READY")["command"] == "/_IDF_orchestrate BL-9"
    assert rs.next_command_for_bl("BL-9", "READY")["command"] == "/_IDF_orchestrate BL-9"


def test_next_a_done_flag_goes_to_idf_even_if_unreif():
    # Manifest sagt A gelaufen -> IDF, auch wenn Index-Reifegrad noch nicht nachgezogen ist.
    assert rs.next_command_for_bl("BL-9", "UNREIF", a_done=True)["command"] == "/_IDF_orchestrate BL-9"


def test_next_in_flight_resumes():
    r = rs.next_command_for_bl("BL-9", "SC-REIF", in_flight=True)
    assert r["command"] == "/_SDF_orchestrate BL-9 --resume"
    assert r["fresh_session"] is False


def test_next_done_has_no_command():
    assert rs.next_command_for_bl("BL-1", "REIF", "DONE")["command"] is None


def test_next_unknown_reifegrad_conservative_a():
    assert rs.next_command_for_bl("BL-X", "WEIRD")["command"] == "/_A_orchestrate BL-X"


# ── roadmap_status: WO / WOHIN / Ziel + naechster Befehl ──

_ROADMAP = "Phase 1 [[BL-397]] → Phase 2 [[BL-398]] → [[BL-387]] → [[BL-399]] → [[BL-388]] → [[BL-389]]"


def _idx(**kw):
    # kw: BL_ohne_Bindestrich? nein — baue dict direkt
    return kw


def test_status_target_is_first_non_done():
    index = {
        "BL-397": {"status": "DRAFT", "reifegrad": "UNREIF"},
        "BL-398": {"status": "DRAFT", "reifegrad": "UNREIF"},
        "BL-387": {"status": "DRAFT", "reifegrad": "UNREIF"},
        "BL-399": {"status": "DRAFT", "reifegrad": "UNREIF"},
        "BL-388": {"status": "DRAFT", "reifegrad": "UNREIF"},
        "BL-389": {"status": "DRAFT", "reifegrad": "UNREIF"},
    }
    st = rs.roadmap_status(_ROADMAP, index)
    assert st["target"] == "BL-397"
    assert st["next"]["command"] == "/_A_orchestrate BL-397"
    assert st["remaining"][0] == "BL-397" and st["remaining"][-1] == "BL-389"


def test_status_done_advances_target():
    # BL-397 done (via done-Index), BL-398 done (status), Ziel = BL-387.
    index = {
        "BL-398": {"status": "DONE", "reifegrad": "REIF"},
        "BL-387": {"status": "DRAFT", "reifegrad": "UNREIF"},
        "BL-399": {"status": "DRAFT", "reifegrad": "UNREIF"},
        "BL-388": {"status": "DRAFT", "reifegrad": "UNREIF"},
        "BL-389": {"status": "DRAFT", "reifegrad": "UNREIF"},
    }
    st = rs.roadmap_status(_ROADMAP, index, done_ids={"BL-397"})
    assert "BL-397" in st["done"] and "BL-398" in st["done"]
    assert st["target"] == "BL-387"


def test_status_epic_complete_no_target():
    index = {b: {"status": "DONE", "reifegrad": "REIF"} for b in
             ["BL-397", "BL-398", "BL-387", "BL-399", "BL-388", "BL-389"]}
    st = rs.roadmap_status(_ROADMAP, index)
    assert st["target"] is None and st["remaining"] == []


def test_status_absent_bl_flagged_unknown():
    # BL-388 weder im aktiven Index noch im done-Set -> unknown (Lead prueft), NICHT still als done.
    index = {"BL-397": {"status": "DRAFT", "reifegrad": "UNREIF"}}
    st = rs.roadmap_status("[[BL-397]] [[BL-388]]", index)
    assert "BL-388" in st["unknown"]


def test_format_report_shows_next_command():
    index = {"BL-397": {"status": "DRAFT", "reifegrad": "UNREIF"}}
    rep = rs.format_report(rs.roadmap_status("[[BL-397]]", index), epic="Wahrheiten")
    assert "/_A_orchestrate BL-397" in rep
    assert "NAECHSTER BEFEHL" in rep


# ── render_build_chain: BAU-KETTE (reifegrad-bewusster Start-Punkt) ──

def test_build_chain_unreif_starts_at_a():
    """UNREIF-BL: Kette startet bei A, alle 4 Stufen vorhanden."""
    chain = rs.render_build_chain("BL-397", "/_A_orchestrate BL-397")
    assert "BAU-KETTE" in chain
    assert "/_A_orchestrate BL-397" in chain
    assert "/_IDF_orchestrate" in chain
    assert "/_SDF_orchestrate" in chain
    assert "C3-modusEntscheidung" in chain
    assert "/_SDF_orchestrate_post" in chain
    # A muss als erster Eintrag stehen
    assert chain.index("/_A_orchestrate") < chain.index("/_IDF_orchestrate")


def test_build_chain_reif_starts_at_idf_no_a():
    """READY/SC-REIF: Kette startet bei IDF — kein A als Start-Schritt."""
    chain = rs.render_build_chain("BL-9", "/_IDF_orchestrate BL-9")
    assert "BAU-KETTE" in chain
    assert "/_IDF_orchestrate" in chain
    assert "/_SDF_orchestrate" in chain
    assert "C3-modusEntscheidung" in chain
    assert "/_SDF_orchestrate_post" in chain
    # A-Orchestrate darf NICHT als Start-Schritt erscheinen
    # (es koennte im Erklaer-Text erscheinen, aber nicht als Befehl)
    lines = chain.splitlines()
    first_command_line = next(
        (l for l in lines if "/_A_orchestrate" in l or "/_IDF_orchestrate" in l), ""
    )
    assert "/_IDF_orchestrate" in first_command_line, (
        "Erste Pipeline-Zeile muss IDF sein, nicht A"
    )


def test_build_chain_resume_shows_sdf_resume():
    """Mid-flight BL: Kette startet bei SDF --resume."""
    chain = rs.render_build_chain("BL-9", "/_SDF_orchestrate BL-9 --resume")
    assert "BAU-KETTE" in chain
    assert "--resume" in chain
    assert "/_SDF_orchestrate_post" in chain


def test_build_chain_done_returns_empty():
    """DONE-BL: keine Kette (naechste BL nehmen)."""
    chain = rs.render_build_chain("BL-1", None)
    assert chain == ""


def test_format_report_contains_build_chain_for_unreif():
    """format_report fuer UNREIF-BL muss den BAU-KETTE-Block enthalten."""
    index = {"BL-397": {"status": "DRAFT", "reifegrad": "UNREIF"}}
    rep = rs.format_report(rs.roadmap_status("[[BL-397]]", index), epic="Wahrheiten")
    assert "BAU-KETTE" in rep
    assert "/_IDF_orchestrate" in rep
    assert "/_SDF_orchestrate" in rep
    assert "C3-modusEntscheidung" in rep
    assert "/_SDF_orchestrate_post" in rep


def test_format_report_contains_build_chain_for_reif():
    """format_report fuer READY-BL: BAU-KETTE vorhanden, Start bei IDF."""
    index = {"BL-9": {"status": "READY", "reifegrad": "READY"}}
    rep = rs.format_report(rs.roadmap_status("[[BL-9]]", index), epic="Test")
    assert "BAU-KETTE" in rep
    assert "/_IDF_orchestrate" in rep
    # A darf nicht als Start-Zeile auftauchen
    lines = rep.splitlines()
    chain_start = next((i for i, l in enumerate(lines) if "BAU-KETTE" in l), -1)
    assert chain_start >= 0, "BAU-KETTE-Block fehlt"
    chain_lines = lines[chain_start:]
    first_pipeline = next(
        (l for l in chain_lines if "/_A_orchestrate" in l or "/_IDF_orchestrate" in l), ""
    )
    assert "/_IDF_orchestrate" in first_pipeline, "Reif-Kette muss bei IDF starten"
