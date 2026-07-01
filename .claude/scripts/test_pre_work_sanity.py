"""
test_pre_work_sanity.py — BL-194-N10, INV-PC-12: Tests for pre_work_sanity() in factory_lock.py

4 Tests covering skip detection, non-skip path, empty list, and trimmed bl_id matching.
Run: py -3 -m pytest .claude/scripts/test_pre_work_sanity.py -v
"""

import sys
from pathlib import Path

import pytest

# Add scripts dir to path
sys.path.insert(0, str(Path(__file__).parent))

# Import the function under test — does NOT exist yet (RED phase)
from factory_lock import pre_work_sanity


# ─── Test 1: bl_id in completed_bls -> (True, non-empty reason) ───────────────

def test_in_completed_bls_returns_skip_true():
    """bl_id present in completed_bls -> (True, reason) where reason mentions bl_id."""
    skip, reason = pre_work_sanity("BL-194", ["BL-193", "BL-194", "BL-195"])
    assert skip is True
    assert "BL-194" in reason
    assert reason != ""


# ─── Test 2: bl_id NOT in completed_bls -> (False, "") ───────────────────────

def test_not_in_completed_bls_returns_no_skip():
    """bl_id not present in completed_bls -> (False, '')."""
    skip, reason = pre_work_sanity("BL-200", ["BL-193", "BL-194", "BL-195"])
    assert skip is False
    assert reason == ""


# ─── Test 3: empty list -> (False, "") ───────────────────────────────────────

def test_empty_completed_bls_returns_no_skip():
    """completed_bls is empty list -> (False, '')."""
    skip, reason = pre_work_sanity("BL-194", [])
    assert skip is False
    assert reason == ""


# ─── Test 4: None completed_bls -> (False, "") ───────────────────────────────

def test_none_completed_bls_returns_no_skip():
    """completed_bls is None -> (False, '')."""
    skip, reason = pre_work_sanity("BL-194", None)
    assert skip is False
    assert reason == ""


# ─── Test 5: trimmed bl_id matches entry in list ─────────────────────────────

def test_trimmed_bl_id_matches():
    """bl_id with surrounding whitespace still matches entry in completed_bls."""
    skip, reason = pre_work_sanity(" BL-194 ", ["BL-194"])
    assert skip is True
    assert "BL-194" in reason
