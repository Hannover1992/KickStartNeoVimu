#!/usr/bin/env python3
"""Tests fuer lane_plan.advance_current (BL-444 AK-3, TDD RED-Phase).

TDD Stage 1 (Atomic). Vorbild: test_guard_autochain_stop.py (BL-394).

Ziel: `advance_current(my_lane, completed_bl_id, plan)` in lane_plan.py
(existiert noch NICHT -> alle Tests failen mit ImportError = korrekter RED-State).

Signatur (SOLL):
    def advance_current(my_lane: str, completed_bl_id: str, plan: Dict[str, Any]) -> Dict[str, Any]:
        \"\"\"Rueckt current fuer my_lane weiter und traegt completed_bl_id in done[] ein.

        Mutiert plan (deepcopy empfohlen vom Caller) und gibt ihn zurueck.
        Wenn der completed_bl_id nicht mehr in queue ist (bereits entfernt): kein Fehler.
        current wird auf das erste noch-nicht-done BL nach completed_bl_id gesetzt,
        oder auf None wenn die Queue leer ist.
        \"\"\"

Tests (T-A1..T-A5):
  T-A1  test_advance_moves_current_to_next_open_item_for_lane
        — Kern: current BL-441 -> advance -> current BL-365
  T-A2  test_advance_skips_done_items
        — BL-365 bereits in done -> springt zu BL-376
  T-A3  test_advance_persists_via_write_lane_plan
        — Round-trip: advance + write -> parse zeigt neuen current
  T-A4  test_advance_at_last_item_sets_current_none_or_empty
        — Queue erschoepft -> current wird None / leer
  T-A5  test_advance_only_touches_own_lane
        — andere Lanes unveraendert nach advance

RED: `from lane_plan import advance_current` -> ImportError (Funktion existiert noch nicht).
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from copy import deepcopy

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# ---------------------------------------------------------------------------
# Import-Versuch (RED: ImportError erwartet bis GREEN-Worker implementiert)
# ---------------------------------------------------------------------------

try:
    from lane_plan import advance_current, parse_lane_plan, write_lane_plan
    _IMPORT_OK = True
    _IMPORT_ERROR = None
except ImportError as e:
    _IMPORT_OK = False
    _IMPORT_ERROR = str(e)
    # Stub damit Tests mit sauberem Fehler failen statt crash-Error
    def advance_current(*a, **kw):  # type: ignore
        raise ImportError(f"advance_current nicht in lane_plan.py implementiert (RED-Phase). {_IMPORT_ERROR}")
    from lane_plan import parse_lane_plan, write_lane_plan


# ---------------------------------------------------------------------------
# Fixtures / Hilfsfunktionen
# ---------------------------------------------------------------------------

def _make_lane_plan_file(plan_dict: dict) -> str:
    """Schreibt ein minimales _lane_plan.md mit LANE_PLAN-YAML-Fence, gibt Pfad zurueck."""
    lines = ["# Lane Plan\n\n"]
    lines.append("```yaml\n")
    lines.append("LANE_PLAN:\n")
    for lane, entry in plan_dict.items():
        lines.append(f"  {lane}:\n")
        current = entry.get("current", "")
        lines.append(f"    current: {current}\n")
        queue = entry.get("queue", [])
        queue_str = "[" + ", ".join(queue) + "]"
        lines.append(f"    queue: {queue_str}\n")
        done = entry.get("done", [])
        done_str = "[" + ", ".join(done) + "]"
        lines.append(f"    done: {done_str}\n")
        branch = entry.get("branch", f"roadmap-{lane.lower()}")
        lines.append(f"    branch: {branch}\n")
    lines.append("```\n")

    tf = tempfile.NamedTemporaryFile(
        mode="w", suffix="_lane_plan.md", delete=False, encoding="utf-8"
    )
    tf.writelines(lines)
    tf.close()
    return tf.name


def _base_plan_a() -> dict:
    """Basisplan: Lane A mit current=BL-441, queue=[BL-441, BL-365, BL-376], done=[]."""
    return {
        "A": {
            "current": "BL-441",
            "queue": ["BL-441", "BL-365", "BL-376"],
            "done": [],
            "branch": "roadmap-a",
        }
    }


# ---------------------------------------------------------------------------
# T-A1: Kern — advance moves current to next open item
# ---------------------------------------------------------------------------

def test_advance_moves_current_to_next_open_item_for_lane():
    """T-A1 (AK-3 Kern-Test): advance_current("A", "BL-441", plan)
    -> plan["A"]["current"] == "BL-365" (naechstes nicht-done Item in queue).
    -> plan["A"]["done"] enthaelt "BL-441".

    RED: advance_current existiert noch nicht -> ImportError.
    """
    plan = _base_plan_a()

    result = advance_current("A", "BL-441", plan)

    assert isinstance(result, dict), (
        f"T-A1: advance_current muss ein dict zurueckgeben, war {type(result)}."
    )
    new_current = result.get("A", {}).get("current")
    assert new_current == "BL-365", (
        f"T-A1 AK-3 Kern: advance_current('A','BL-441',plan) -> current muss 'BL-365' sein "
        f"(naechstes nicht-done Item), war: '{new_current}'."
    )
    done_list = result.get("A", {}).get("done", [])
    assert "BL-441" in done_list, (
        f"T-A1: 'BL-441' muss in done[] eingetragen sein nach advance_current. "
        f"done war: {done_list}."
    )


# ---------------------------------------------------------------------------
# T-A2: advance skips done items
# ---------------------------------------------------------------------------

def test_advance_skips_done_items():
    """T-A2 (AK-3 Skip-done): BL-365 bereits in done -> advance_current springt zu BL-376.

    Setup: current=BL-441, queue=[BL-441, BL-365, BL-376], done=["BL-365"].
    Nach advance("A", "BL-441", plan): current == "BL-376" (BL-365 geskippt weil done).

    RED: advance_current existiert noch nicht.
    """
    plan = {
        "A": {
            "current": "BL-441",
            "queue": ["BL-441", "BL-365", "BL-376"],
            "done": ["BL-365"],
            "branch": "roadmap-a",
        }
    }

    result = advance_current("A", "BL-441", plan)

    new_current = result.get("A", {}).get("current")
    assert new_current == "BL-376", (
        f"T-A2 Skip-done: BL-365 ist in done[] -> advance_current muss BL-376 als naechstes "
        f"setzen (BL-365 geskippt). current war: '{new_current}'."
    )
    done_list = result.get("A", {}).get("done", [])
    assert "BL-441" in done_list, (
        f"T-A2: 'BL-441' muss in done[] eingetragen sein. done war: {done_list}."
    )


# ---------------------------------------------------------------------------
# T-A3: Round-trip persist via write_lane_plan
# ---------------------------------------------------------------------------

def test_advance_persists_via_write_lane_plan():
    """T-A3 (AK-3 Round-trip): advance + write_lane_plan -> parse_lane_plan zeigt neuen current.

    Dieser Test prueft, dass das Ergebnis von advance_current via write_lane_plan persistiert
    und via parse_lane_plan wieder gelesen werden kann (Round-trip stabil).

    RED: advance_current existiert noch nicht.
    """
    plan = _base_plan_a()
    plan_path = _make_lane_plan_file(plan)

    try:
        result = advance_current("A", "BL-441", plan)
        write_lane_plan(plan_path, result)

        reloaded = parse_lane_plan(plan_path)

        new_current = reloaded.get("A", {}).get("current")
        assert new_current == "BL-365", (
            f"T-A3 Round-trip: nach advance + write + parse muss current=='BL-365' sein. "
            f"War: '{new_current}'."
        )
        done_list = reloaded.get("A", {}).get("done", [])
        assert "BL-441" in done_list, (
            f"T-A3: 'BL-441' muss in done[] nach Round-trip stehen. done war: {done_list}."
        )
    finally:
        Path(plan_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# T-A4: advance at last item -> current None or empty
# ---------------------------------------------------------------------------

def test_advance_at_last_item_sets_current_none_or_empty():
    """T-A4 (AK-3 Queue-erschoepft): alle Queue-Items sind nach advance done
    -> current wird None oder '' (leere Lane).

    Setup: current=BL-376, queue=[BL-441, BL-365, BL-376], done=["BL-441", "BL-365"].
    Nach advance("A", "BL-376", plan): kein weiteres nicht-done Item -> current = None.

    RED: advance_current existiert noch nicht.
    """
    plan = {
        "A": {
            "current": "BL-376",
            "queue": ["BL-441", "BL-365", "BL-376"],
            "done": ["BL-441", "BL-365"],
            "branch": "roadmap-a",
        }
    }

    result = advance_current("A", "BL-376", plan)

    new_current = result.get("A", {}).get("current")
    assert new_current in (None, "", "null", "~"), (
        f"T-A4 Queue-erschoepft: kein weiteres not-done Item nach BL-376 -> "
        f"current muss None/''/null sein. War: '{new_current}'."
    )
    done_list = result.get("A", {}).get("done", [])
    assert "BL-376" in done_list, (
        f"T-A4: 'BL-376' muss in done[] eingetragen sein. done war: {done_list}."
    )


# ---------------------------------------------------------------------------
# T-A5: advance only touches own lane
# ---------------------------------------------------------------------------

def test_advance_only_touches_own_lane():
    """T-A5 (AK-3 Lane-Isolation): advance_current("A", ...) darf andere Lanes NICHT veraendern.

    Setup: Lane A + Lane B + Lane C in plan. Advance auf Lane A.
    Nachher: plan["B"] und plan["C"] identisch zu vorher.

    RED: advance_current existiert noch nicht.
    """
    plan = {
        "A": {
            "current": "BL-441",
            "queue": ["BL-441", "BL-365", "BL-376"],
            "done": [],
            "branch": "roadmap-a",
        },
        "B": {
            "current": "BL-410",
            "queue": ["BL-410", "BL-406"],
            "done": ["BL-999"],
            "branch": "roadmap-b",
        },
        "C": {
            "current": "BL-368",
            "queue": ["BL-368", "BL-412"],
            "done": [],
            "branch": "roadmap-c",
        },
    }
    # Snapshot der anderen Lanes VOR dem advance
    lane_b_before = deepcopy(plan["B"])
    lane_c_before = deepcopy(plan["C"])

    result = advance_current("A", "BL-441", plan)

    lane_b_after = result.get("B", {})
    lane_c_after = result.get("C", {})

    assert lane_b_after.get("current") == lane_b_before.get("current"), (
        f"T-A5 Lane-Isolation: Lane B current darf sich nicht aendern. "
        f"Vorher: '{lane_b_before.get('current')}', Nachher: '{lane_b_after.get('current')}'."
    )
    assert lane_b_after.get("done") == lane_b_before.get("done"), (
        f"T-A5: Lane B done darf sich nicht aendern. "
        f"Vorher: {lane_b_before.get('done')}, Nachher: {lane_b_after.get('done')}."
    )
    assert lane_c_after.get("current") == lane_c_before.get("current"), (
        f"T-A5: Lane C current darf sich nicht aendern. "
        f"Vorher: '{lane_c_before.get('current')}', Nachher: '{lane_c_after.get('current')}'."
    )


# ---------------------------------------------------------------------------
# __main__ runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_advance_moves_current_to_next_open_item_for_lane,
        test_advance_skips_done_items,
        test_advance_persists_via_write_lane_plan,
        test_advance_at_last_item_sets_current_none_or_empty,
        test_advance_only_touches_own_lane,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed + failed} ===")
    sys.exit(0 if failed == 0 else 1)
