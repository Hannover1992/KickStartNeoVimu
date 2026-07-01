"""
test_bdf_bl_sequence_planner.py — Unit tests for BL-176 AK-4: bdf_bl_sequence_planner

6 tests covering topological sort, tiebreak, and cycle detection.
"""

import pytest
from bdf_bl_sequence_planner import (
    plan_sequence,
    CycleDetectedError,
    _priority_key,
)


# ---------------------------------------------------------------------------
# Test 1: Linear dependency chain → correct order
# ---------------------------------------------------------------------------

def test_linear_chain_ordered():
    matrix = {
        "items": ["BL-C", "BL-A", "BL-B"],
        "dependencies": {
            "BL-B": ["BL-A"],  # BL-B depends on BL-A
            "BL-C": ["BL-B"],  # BL-C depends on BL-B
        },
    }
    priorities = {}
    result = plan_sequence(matrix, priorities)
    assert result.index("BL-A") < result.index("BL-B")
    assert result.index("BL-B") < result.index("BL-C")


# ---------------------------------------------------------------------------
# Test 2: No dependencies → sorted by priority
# ---------------------------------------------------------------------------

def test_no_deps_priority_tiebreak():
    matrix = {
        "items": ["BL-LOW", "BL-HIGH", "BL-CRIT", "BL-MED"],
        "dependencies": {},
    }
    priorities = {
        "BL-LOW": {"priority": "NIEDRIG", "k_score": 10.0},
        "BL-HIGH": {"priority": "HOCH", "k_score": 50.0},
        "BL-CRIT": {"priority": "KRITISCH", "k_score": 80.0},
        "BL-MED": {"priority": "MITTEL", "k_score": 30.0},
    }
    result = plan_sequence(matrix, priorities)
    assert result[0] == "BL-CRIT"
    assert result[1] == "BL-HIGH"
    assert result[2] == "BL-MED"
    assert result[3] == "BL-LOW"


# ---------------------------------------------------------------------------
# Test 3: k_score tiebreak within same priority level
# ---------------------------------------------------------------------------

def test_k_score_tiebreak_same_priority():
    matrix = {
        "items": ["BL-X", "BL-Y", "BL-Z"],
        "dependencies": {},
    }
    priorities = {
        "BL-X": {"priority": "HOCH", "k_score": 30.0},
        "BL-Y": {"priority": "HOCH", "k_score": 70.0},
        "BL-Z": {"priority": "HOCH", "k_score": 50.0},
    }
    result = plan_sequence(matrix, priorities)
    # Higher k_score should come first within same priority
    assert result[0] == "BL-Y"
    assert result[1] == "BL-Z"
    assert result[2] == "BL-X"


# ---------------------------------------------------------------------------
# Test 4: Cycle detection raises CycleDetectedError (HiL-Alert)
# ---------------------------------------------------------------------------

def test_cycle_detection_raises():
    matrix = {
        "items": ["BL-1", "BL-2", "BL-3"],
        "dependencies": {
            "BL-2": ["BL-1"],
            "BL-3": ["BL-2"],
            "BL-1": ["BL-3"],  # closes the cycle
        },
    }
    with pytest.raises(CycleDetectedError) as exc_info:
        plan_sequence(matrix, {})
    assert len(exc_info.value.cycle_nodes) > 0


# ---------------------------------------------------------------------------
# Test 5: Empty matrix returns empty sequence
# ---------------------------------------------------------------------------

def test_empty_matrix_returns_empty():
    result = plan_sequence({"items": [], "dependencies": {}}, {})
    assert result == []


# ---------------------------------------------------------------------------
# Test 6: Dependencies to unknown items are ignored gracefully
# ---------------------------------------------------------------------------

def test_unknown_dependency_ignored():
    matrix = {
        "items": ["BL-A", "BL-B"],
        "dependencies": {
            "BL-B": ["BL-A", "BL-UNKNOWN"],  # BL-UNKNOWN not in items
        },
    }
    result = plan_sequence(matrix, {})
    assert result.index("BL-A") < result.index("BL-B")
    assert len(result) == 2


# ---------------------------------------------------------------------------
# Bonus: priority_key helper
# ---------------------------------------------------------------------------

def test_priority_key_ordering():
    priorities = {
        "a": {"priority": "KRITISCH", "k_score": 100},
        "b": {"priority": "NIEDRIG", "k_score": 100},
    }
    assert _priority_key("a", priorities) < _priority_key("b", priorities)
