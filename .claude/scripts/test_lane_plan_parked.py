"""BL-371 AK-3: test_lane_plan_parked.py — RED-Tests fuer lane_plan.park_bl + next_bl_for_lane-parked-Skip

Erwartet: park_bl in lane_plan.py existiert NICHT -> AttributeError = RED.
next_bl_for_lane skippt parked BLs noch NICHT -> test_next_bl_skips_parked FAIL = RED.
GREEN-Worker implementiert die Erweiterungen in lane_plan.py.

API unter Test (additive Erweiterung, lane_plan.py):
  park_bl(lane, bl_id, plan) -> plan
    Traegt bl_id in plan[lane]["parked"] ein.
    Idempotent: kein Duplikat.

  next_bl_for_lane(my_lane, plan, done=None) -> Optional[str]
    ERWEITERUNG: skippt parked BLs aus plan[lane]["parked"] (analog zu done).
    Rueckwaertskompatibel: bestehende done-Logik unveraendert.

Rueckwaertskompatibilitaet: bestehende Tests (test_lane_plan.py etc.) muessen
GRUEN bleiben — diese Datei erweitert nur, bricht nichts.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

import lane_plan as lp  # noqa: E402


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

SAMPLE_PLAN_CONTENT = """
```yaml
LANE_PLAN:
  A:
    branch: roadmap-a
    worktree: OmniCommand-wtA
    current: BL-100
    queue: [BL-365, BL-371, BL-400]
    done: [BL-441]
    parked: []
```
"""


def _write_plan(tmp_path, content: str) -> Path:
    p = tmp_path / "_lane_plan.md"
    p.write_text(content, encoding="utf-8")
    return p


def _make_plan():
    """Erzeugt ein plan-Dict direkt (ohne Datei) fuer unit-level Tests."""
    return {
        "A": {
            "branch": "roadmap-a",
            "worktree": "OmniCommand-wtA",
            "current": "BL-100",
            "queue": ["BL-365", "BL-371", "BL-400"],
            "done": ["BL-441"],
            "parked": [],
        }
    }


# ---------------------------------------------------------------------------
# AK-3: park_bl — neue Funktion
# ---------------------------------------------------------------------------

def test_park_bl_function_exists():
    """park_bl muss in lane_plan exportiert sein (AttributeError = RED)"""
    # Wenn park_bl fehlt -> AttributeError -> RED-Beweis
    assert hasattr(lp, "park_bl"), "park_bl nicht in lane_plan (RED)"
    assert callable(lp.park_bl), "park_bl ist nicht aufrufbar"


def test_park_bl_adds_to_parked():
    """park_bl('A', 'BL-365', plan) -> plan['A']['parked'] == ['BL-365']"""
    plan = _make_plan()
    result = lp.park_bl("A", "BL-365", plan)
    assert "parked" in result["A"]
    assert "BL-365" in result["A"]["parked"]


def test_park_bl_idempotent():
    """Zweimaliges parken derselben BL-ID -> kein Duplikat in parked"""
    plan = _make_plan()
    plan = lp.park_bl("A", "BL-365", plan)
    plan = lp.park_bl("A", "BL-365", plan)
    parked = plan["A"]["parked"]
    assert parked.count("BL-365") == 1, f"Duplikat gefunden: {parked}"


def test_park_bl_does_not_affect_done():
    """park_bl aendert done[] nicht; done und parked sind unabhaengige Listen"""
    plan = _make_plan()
    plan["A"]["done"] = ["BL-441"]
    plan = lp.park_bl("A", "BL-365", plan)
    # done unveraendert
    assert plan["A"]["done"] == ["BL-441"]
    # parked enthaelt nur BL-365
    assert "BL-365" in plan["A"]["parked"]
    assert "BL-441" not in plan["A"]["parked"]


def test_park_bl_does_not_affect_other_lanes():
    """park_bl in Lane A beeinflusst Lane B nicht"""
    plan = {
        "A": {"queue": ["BL-365", "BL-371"], "done": [], "parked": []},
        "B": {"queue": ["BL-400"], "done": [], "parked": []},
    }
    plan = lp.park_bl("A", "BL-365", plan)
    assert "BL-365" not in plan["B"].get("parked", [])


def test_park_bl_write_read_roundtrip(tmp_path):
    """park_bl + write_lane_plan + parse_lane_plan -> parked-Feld persistiert"""
    plan_path = _write_plan(tmp_path, SAMPLE_PLAN_CONTENT)
    plan = lp.parse_lane_plan(plan_path)
    plan = lp.park_bl("A", "BL-365", plan)
    lp.write_lane_plan(plan_path, plan)

    # Re-read
    plan2 = lp.parse_lane_plan(plan_path)
    parked = plan2.get("A", {}).get("parked", [])
    assert "BL-365" in parked, f"parked nach roundtrip: {parked}"


# ---------------------------------------------------------------------------
# AK-3: next_bl_for_lane — skippt parked BLs
# ---------------------------------------------------------------------------

def test_next_bl_skips_parked():
    """queue=[BL-365, BL-371], parked=[BL-365] -> returns 'BL-371' (nicht BL-365)"""
    plan = {
        "A": {
            "queue": ["BL-365", "BL-371"],
            "done": [],
            "parked": ["BL-365"],
        }
    }
    result = lp.next_bl_for_lane("A", plan)
    assert result == "BL-371", f"Erwartet BL-371, erhalten: {result}"


def test_next_bl_all_parked():
    """Alle BLs in queue sind parked -> returns None"""
    plan = {
        "A": {
            "queue": ["BL-365", "BL-371"],
            "done": [],
            "parked": ["BL-365", "BL-371"],
        }
    }
    result = lp.next_bl_for_lane("A", plan)
    assert result is None, f"Erwartet None, erhalten: {result}"


def test_existing_done_still_skipped():
    """Bestehende done-Logik bleibt unveraendert nach parked-Erweiterung"""
    plan = {
        "A": {
            "queue": ["BL-441", "BL-365", "BL-371"],
            "done": ["BL-441"],
            "parked": ["BL-365"],
        }
    }
    result = lp.next_bl_for_lane("A", plan)
    # BL-441 done, BL-365 parked -> erstes nicht-geskipptes = BL-371
    assert result == "BL-371", f"Erwartet BL-371, erhalten: {result}"


def test_next_bl_done_and_parked_independent():
    """done=[BL-441] + parked=[BL-365] -> beide werden unabhaengig uebersprungen"""
    plan = {
        "A": {
            "queue": ["BL-441", "BL-365", "BL-400"],
            "done": ["BL-441"],
            "parked": ["BL-365"],
        }
    }
    result = lp.next_bl_for_lane("A", plan)
    assert result == "BL-400"


def test_next_bl_no_parked_field_backward_compat():
    """Wenn parked-Feld fehlt (alter Plan) -> kein Crash, bestehende Logik"""
    plan = {
        "A": {
            "queue": ["BL-365", "BL-371"],
            "done": [],
            # kein 'parked'-Feld -> Rueckwaertskompatibilitaet
        }
    }
    result = lp.next_bl_for_lane("A", plan)
    # Sollte BL-365 zurueckgeben (kein Crash)
    assert result == "BL-365"
