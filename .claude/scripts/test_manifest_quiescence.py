#!/usr/bin/env python3
"""Tests fuer manifest_quiescence.py (BL-229 AK-E)."""
import pytest

from manifest_quiescence import evaluate_quiescence, is_manifest_quiescent, require_quiescent


# ── evaluate_quiescence (reine Logik, alle Branches) ──
def test_evaluate_manifest_not_found():
    ok, reason = evaluate_quiescence(None, None, None)
    assert ok is False and "not found" in reason


def test_evaluate_foreign_lock_blocks():
    lock = {"owner": "worker-A", "phase": "SDF.phase3"}
    ok, reason = evaluate_quiescence(lock, 100.0, 100.0, self_worker_id="worker-B")
    assert ok is False and "foreign active lock" in reason and "worker-A" in reason


def test_evaluate_self_lock_ok():
    lock = {"owner": "me", "phase": "slim"}
    ok, reason = evaluate_quiescence(lock, 100.0, 100.0, self_worker_id="me")
    assert ok is True and reason == "quiescent"


def test_evaluate_mtime_changed_blocks():
    ok, reason = evaluate_quiescence(None, 100.0, 105.0)
    assert ok is False and "mtime changed" in reason


def test_evaluate_all_clear():
    ok, reason = evaluate_quiescence(None, 100.0, 100.0)
    assert ok is True and reason == "quiescent"


# ── is_manifest_quiescent (echte stat+settle) ──
def test_quiescent_stable_file(tmp_path):
    m = tmp_path / "_manifest.md"
    m.write_text("state", encoding="utf-8")
    ok, reason = is_manifest_quiescent(m, settle_seconds=0.05)
    assert ok is True and reason == "quiescent"


def test_busy_missing_file(tmp_path):
    ok, reason = is_manifest_quiescent(tmp_path / "nope.md", settle_seconds=0.0)
    assert ok is False and "not found" in reason


def test_require_quiescent_raises_on_busy(tmp_path):
    with pytest.raises(RuntimeError, match="QUIESCENCE-GATE"):
        require_quiescent(tmp_path / "nope.md", settle_seconds=0.0)
