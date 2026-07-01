"""
test_audit_worker_id.py — BL-194-N9, INV-PC-7: Tests for worker_id_fields() in audit_hook.py

5 Tests covering parallelism-budget gating, bl_parallel flag, and regression for serial runs.
Run: py -3 -m pytest .claude/scripts/test_audit_worker_id.py -v
"""

import sys
from pathlib import Path

import pytest

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the function under test — does NOT exist yet (RED phase)
from audit_hook import worker_id_fields


# ─── Test 1: budget=2 + worker_id -> has worker_id ───────────────────────────

def test_parallel_budget_and_worker_id_returns_worker_id():
    """budget>1 + worker_id set -> dict contains worker_id."""
    result = worker_id_fields(parallelism_budget=2, worker_id="terminal-A")
    assert "worker_id" in result
    assert result["worker_id"] == "terminal-A"


# ─── Test 2: budget=2 + worker_id + lane + worktree_id -> all 3 fields ───────

def test_parallel_budget_with_lane_and_worktree_id():
    """budget>1 + worker_id + lane + worktree_id -> all three fields present."""
    result = worker_id_fields(
        parallelism_budget=2,
        worker_id="terminal-B",
        lane="A",
        worktree_id="WT-1",
    )
    assert result["worker_id"] == "terminal-B"
    assert result["lane"] == "A"
    assert result["worktree_id"] == "WT-1"


# ─── Test 3: budget=1 -> {} (serial regression) ───────────────────────────────

def test_serial_budget_returns_empty_dict():
    """budget<=1 + no bl_parallel -> {} (serial run regression: no worker_id emitted)."""
    result = worker_id_fields(parallelism_budget=1, worker_id="terminal-C")
    assert result == {}


# ─── Test 4: bl_parallel=True + budget=1 + worker_id -> has worker_id ────────

def test_bl_parallel_flag_activates_parallel_mode():
    """bl_parallel=True overrides budget=1 -> dict contains worker_id."""
    result = worker_id_fields(
        parallelism_budget=1,
        worker_id="terminal-D",
        bl_parallel=True,
    )
    assert "worker_id" in result
    assert result["worker_id"] == "terminal-D"


# ─── Test 5: budget=2 + worker_id=None -> {} (no empty field emitted) ────────

def test_parallel_budget_with_none_worker_id_returns_empty_dict():
    """budget>1 but worker_id=None -> {} (do not emit empty worker_id field)."""
    result = worker_id_fields(parallelism_budget=2, worker_id=None)
    assert result == {}
