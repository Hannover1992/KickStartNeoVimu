"""
test_bl178_pointer_verify.py — BL-178 AK-7 Tests (8 tests, batch_4)
Tests for quality_index_pointer_verify.py
Run: pytest .claude/scripts/test_bl178_pointer_verify.py -v
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure scripts dir is importable
sys.path.insert(0, str(Path(__file__).parent))
from quality_index_pointer_verify import (
    check_active_index_pointer_resolves,
    check_archive_index_pointer_resolves,
    check_detail_status_matches_index,
    batch_check,
    ACTIVE_STATUSES,
    ARCHIVE_STATUSES,
)


def _make_vault(tmp_path: Path) -> Path:
    """Creates a minimal vault structure for testing."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Backlog").mkdir()
    return vault


def _write_active_index(vault: Path, rows: list[tuple[str, str]]):
    """Write _backlog_index.md with (bl_id, status) rows."""
    lines = ["# Active Index\n", "| BL-ID | Title | Status |\n", "|---|---|---|\n"]
    for bl_id, status in rows:
        lines.append(f"| {bl_id} | Test Title | {status} |\n")
    (vault / "_backlog_index.md").write_text("".join(lines), encoding="utf-8")


def _write_archive_index(vault: Path, rows: list[tuple[str, str]]):
    """Write _backlog_index_done.md with (bl_id, status) rows."""
    lines = ["# Archive Index\n", "| BL-ID | Title | Status |\n", "|---|---|---|\n"]
    for bl_id, status in rows:
        lines.append(f"| {bl_id} | Test Title | {status} |\n")
    (vault / "_backlog_index_done.md").write_text("".join(lines), encoding="utf-8")


def _write_detail_file(vault: Path, bl_id: str, status: str):
    """Create a minimal detail file for bl_id."""
    detail_dir = vault / "Backlog" / f"{bl_id}-test-slug"
    detail_dir.mkdir(exist_ok=True)
    content = f"---\nstatus: {status}\n---\n# {bl_id}\n"
    (detail_dir / "_manifest.md").write_text(content, encoding="utf-8")


# ─── Test 1: active index pointer resolves when file exists ───────────────────

def test_active_pointer_resolves_ok(tmp_path):
    vault = _make_vault(tmp_path)
    _write_active_index(vault, [("BL-001", "READY")])
    _write_detail_file(vault, "BL-001", "READY")

    result = check_active_index_pointer_resolves("BL-001", vault)
    assert result["ok"] is True
    assert result["violation"] is None


# ─── Test 2: active index pointer fails when detail file missing ──────────────

def test_active_pointer_missing_detail(tmp_path):
    vault = _make_vault(tmp_path)
    _write_active_index(vault, [("BL-002", "DRAFT")])
    # No detail file created

    result = check_active_index_pointer_resolves("BL-002", vault)
    assert result["ok"] is False
    assert "BL-002" in result["violation"]


# ─── Test 3: archive index pointer resolves when file exists ──────────────────

def test_archive_pointer_resolves_ok(tmp_path):
    vault = _make_vault(tmp_path)
    _write_archive_index(vault, [("BL-003", "DONE")])
    _write_detail_file(vault, "BL-003", "DONE")

    result = check_archive_index_pointer_resolves("BL-003", vault)
    assert result["ok"] is True


# ─── Test 4: archive index pointer fails when not in archive index ────────────

def test_archive_pointer_missing_entry(tmp_path):
    vault = _make_vault(tmp_path)
    # Empty archive index
    _write_archive_index(vault, [])

    result = check_archive_index_pointer_resolves("BL-004", vault)
    assert result["ok"] is False
    assert "BL-004" in result["violation"]


# ─── Test 5: status consistency — active index with active status → OK ────────

def test_status_match_active_consistent(tmp_path):
    vault = _make_vault(tmp_path)
    _write_active_index(vault, [("BL-005", "READY")])
    _write_detail_file(vault, "BL-005", "READY")

    result = check_detail_status_matches_index("BL-005", vault)
    assert result["ok"] is True


# ─── Test 6: status mismatch — active index but detail status is DONE ─────────

def test_status_mismatch_active_has_done_detail(tmp_path):
    vault = _make_vault(tmp_path)
    _write_active_index(vault, [("BL-006", "READY")])
    _write_detail_file(vault, "BL-006", "DONE")  # mismatch: active index, archive status

    result = check_detail_status_matches_index("BL-006", vault)
    assert result["ok"] is False
    assert "archive-bound" in result["violation"]


# ─── Test 7: INV-INDEX-SPLIT-1 — item in both indexes ────────────────────────

def test_inv_index_split_1_item_in_both(tmp_path):
    vault = _make_vault(tmp_path)
    _write_active_index(vault, [("BL-007", "READY")])
    _write_archive_index(vault, [("BL-007", "DONE")])
    _write_detail_file(vault, "BL-007", "READY")

    result = check_detail_status_matches_index("BL-007", vault)
    assert result["ok"] is False
    assert "BOTH" in result["violation"]


# ─── Test 8: batch_check finds multiple violations ────────────────────────────

def test_batch_check_multiple(tmp_path):
    vault = _make_vault(tmp_path)
    # BL-010: valid active
    _write_active_index(vault, [("BL-010", "READY"), ("BL-011", "DRAFT")])
    _write_detail_file(vault, "BL-010", "READY")
    # BL-011: missing detail file → violation
    # No detail for BL-011

    result = batch_check(vault, bl_ids=["BL-010", "BL-011"])
    # BL-011 should have violations
    violation_ids = {v["bl_id"] for v in result["violations"]}
    assert "BL-011" in violation_ids
    assert result["violation_count"] > 0
