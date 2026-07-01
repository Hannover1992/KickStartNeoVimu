"""
test_guard_pc_invariants.py — BL-194-N11, INV-PC-7 + INV-PC-12:
Tests for check_inv_pc_7() and check_inv_pc_12() in guard_pc_invariants.py

5 Tests covering PC-7 violation detection (parallel + missing worker_id),
FP-free serial mode, and PC-12 double-build detection.
Run: py -3 -m pytest .claude/scripts/test_guard_pc_invariants.py -v
"""

import sys
from pathlib import Path

import pytest

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

# Import functions under test — module does NOT exist yet (RED phase)
from guard_pc_invariants import check_inv_pc_7, check_inv_pc_12


# ─── INV-PC-7 Tests ───────────────────────────────────────────────────────────

def test_pc7_parallel_budget_no_worker_id_yields_violation():
    """budget>1 + entry missing worker_id -> 1 violation mentioning INV-PC-7."""
    entry = {"bl_id": "BL-194", "phase": "build"}
    violations = check_inv_pc_7(entry, parallelism_budget=2)
    assert len(violations) == 1
    assert "INV-PC-7" in violations[0]


def test_pc7_parallel_budget_with_worker_id_yields_no_violation():
    """budget>1 + entry has non-empty worker_id -> [] (no violation)."""
    entry = {"bl_id": "BL-194", "phase": "build", "worker_id": "terminal-A"}
    violations = check_inv_pc_7(entry, parallelism_budget=2)
    assert violations == []


def test_pc7_serial_budget_no_worker_id_yields_no_violation():
    """budget<=1 + entry missing worker_id -> [] (FP-free for serial runs)."""
    entry = {"bl_id": "BL-194", "phase": "build"}
    violations = check_inv_pc_7(entry, parallelism_budget=1)
    assert violations == []


# ─── INV-PC-12 Tests ──────────────────────────────────────────────────────────

def test_pc12_bl_in_completed_yields_violation():
    """bl_id found in completed_bls -> 1 violation mentioning INV-PC-12."""
    violations = check_inv_pc_12("BL-194", completed_bls=["BL-193", "BL-194"])
    assert len(violations) == 1
    assert "INV-PC-12" in violations[0]


def test_pc12_fresh_bl_yields_no_violation():
    """bl_id NOT in completed_bls -> [] (no double-build violation)."""
    violations = check_inv_pc_12("BL-200", completed_bls=["BL-193", "BL-194"])
    assert violations == []
