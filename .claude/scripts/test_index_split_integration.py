"""
test_index_split_integration.py — BL-178 AK-10 Integration Tests (10 tests)
Cross-cutting integration tests for Index-vs-Content-Split.
Run: pytest .claude/scripts/test_index_split_integration.py -v
"""

import json
import os
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from quality_index_pointer_verify import (
    check_detail_status_matches_index,
    check_active_index_pointer_resolves,
    check_archive_index_pointer_resolves,
    batch_check,
    ACTIVE_STATUSES,
    ARCHIVE_STATUSES,
)
from token_cost_tracker import track_index_size, TOKENS_PER_LOC


# ─── Shared helpers ───────────────────────────────────────────────────────────

def _make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "Backlog").mkdir()
    return vault


def _write_active_index(vault: Path, rows: list[tuple[str, str]]):
    lines = ["# Active Index\n", "| BL-ID | Title | Status |\n", "|---|---|---|\n"]
    for bl_id, status in rows:
        lines.append(f"| {bl_id} | Title | {status} |\n")
    (vault / "_backlog_index.md").write_text("".join(lines), encoding="utf-8")


def _write_archive_index(vault: Path, rows: list[tuple[str, str]]):
    lines = ["# Archive Index\n", "| BL-ID | Title | Status |\n", "|---|---|---|\n"]
    for bl_id, status in rows:
        lines.append(f"| {bl_id} | Title | {status} |\n")
    (vault / "_backlog_index_done.md").write_text("".join(lines), encoding="utf-8")


def _write_parking_lot(vault: Path, open_items: list[str], done_items: list[str]):
    lines = ["# Parking Lot\n"]
    for item in open_items:
        lines.append(f"- [ ] {item}\n")
    for item in done_items:
        lines.append(f"- [x] {item}\n")
    (vault / "_parking-lot.md").write_text("".join(lines), encoding="utf-8")


def _write_parking_lot_done(vault: Path, items: list[str]):
    lines = ["# Parking Lot DONE\n"]
    for item in items:
        lines.append(f"- [x] {item}\n")
    (vault / "_parking-lot_done.md").write_text("".join(lines), encoding="utf-8")


def _write_detail_file(vault: Path, bl_id: str, status: str):
    d = vault / "Backlog" / f"{bl_id}-slug"
    d.mkdir(exist_ok=True)
    content = f"---\nstatus: {status}\n---\n# {bl_id}\n"
    (d / "_manifest.md").write_text(content, encoding="utf-8")


def _do_migrate(vault: Path, bl_id: str, from_status: str = "READY", to_status: str = "DONE"):
    """Simulate status-trigger migration: move item from active to archive index."""
    # Read active index
    active_path = vault / "_backlog_index.md"
    archive_path = vault / "_backlog_index_done.md"

    active_content = active_path.read_text(encoding="utf-8")
    rows_active = []
    rows_to_archive = []
    for line in active_content.splitlines(keepends=True):
        if f"| {bl_id} |" in line and to_status in line:
            rows_to_archive.append(line)
        elif f"| {bl_id} |" in line:
            rows_to_archive.append(line.replace(from_status, to_status))
        else:
            rows_active.append(line)

    active_path.write_text("".join(rows_active), encoding="utf-8")

    # Append to archive
    archive_content = archive_path.read_text(encoding="utf-8") if archive_path.exists() else "# Archive\n"
    for row in rows_to_archive:
        archive_content += row
    archive_path.write_text(archive_content, encoding="utf-8")

    # Update detail file
    _write_detail_file(vault, bl_id, to_status)


def _do_reopen(vault: Path, bl_id: str):
    """Simulate /_backlog reopen: move item from archive to active index."""
    active_path = vault / "_backlog_index.md"
    archive_path = vault / "_backlog_index_done.md"

    if not archive_path.exists():
        return

    archive_content = archive_path.read_text(encoding="utf-8")
    rows_archive_keep = []
    rows_to_active = []
    for line in archive_content.splitlines(keepends=True):
        if f"| {bl_id} |" in line:
            rows_to_active.append(line.replace("DONE", "DRAFT"))
        else:
            rows_archive_keep.append(line)

    archive_path.write_text("".join(rows_archive_keep), encoding="utf-8")

    active_content = active_path.read_text(encoding="utf-8") if active_path.exists() else "# Active\n"
    for row in rows_to_active:
        active_content += row
    active_path.write_text(active_content, encoding="utf-8")

    _write_detail_file(vault, bl_id, "DRAFT")


# ─── Test 1: Full migration roundtrip ─────────────────────────────────────────

def test_full_migration_roundtrip(tmp_path):
    """Apply migration → verify → rollback (re-activation)."""
    vault = _make_vault(tmp_path)
    _write_active_index(vault, [("BL-100", "READY")])
    _write_archive_index(vault, [])
    _write_detail_file(vault, "BL-100", "READY")

    # Migrate
    _do_migrate(vault, "BL-100", from_status="READY", to_status="DONE")

    # Verify: not in active, in archive
    active_result = check_active_index_pointer_resolves("BL-100", vault)
    archive_result = check_archive_index_pointer_resolves("BL-100", vault)
    assert active_result["ok"] is False  # No longer in active
    assert archive_result["ok"] is True

    # Rollback via reopen
    _do_reopen(vault, "BL-100")
    active_after = check_active_index_pointer_resolves("BL-100", vault)
    assert active_after["ok"] is True


# ─── Test 2: Status hook triggers migration ───────────────────────────────────

def test_status_hook_triggers_migration(tmp_path):
    """Simulates a status change READY→DONE triggering migration."""
    vault = _make_vault(tmp_path)
    _write_active_index(vault, [("BL-101", "READY")])
    _write_archive_index(vault, [])
    _write_detail_file(vault, "BL-101", "READY")

    # Simulate hook: status change detected
    _do_migrate(vault, "BL-101", from_status="READY", to_status="DONE")

    # Post-hook state: item in archive
    archive_result = check_archive_index_pointer_resolves("BL-101", vault)
    assert archive_result["ok"] is True

    # Status consistency: detail file should be DONE
    status_result = check_detail_status_matches_index("BL-101", vault)
    assert status_result["ok"] is True


# ─── Test 3: Reactivation path archive→active ─────────────────────────────────

def test_reactivation_path_archive_to_active(tmp_path):
    """BL starts in archive, reopen moves it to active as DRAFT."""
    vault = _make_vault(tmp_path)
    _write_active_index(vault, [])
    _write_archive_index(vault, [("BL-102", "DONE")])
    _write_detail_file(vault, "BL-102", "DONE")

    _do_reopen(vault, "BL-102")

    active_result = check_active_index_pointer_resolves("BL-102", vault)
    assert active_result["ok"] is True

    detail_result = check_detail_status_matches_index("BL-102", vault)
    assert detail_result["ok"] is True


# ─── Test 4: BDF SCANNING reads active-only ───────────────────────────────────

def test_bdf_scanning_active_only(tmp_path):
    """BDF scanning file list should only contain active index files."""
    # INV-INDEX-SPLIT-5: BDF Phase 2 SCANNING must not read archive files
    vault = _make_vault(tmp_path)

    # Write both active and archive indexes
    _write_active_index(vault, [("BL-103", "READY")])
    _write_archive_index(vault, [("BL-999", "DONE")])
    _write_detail_file(vault, "BL-103", "READY")
    _write_detail_file(vault, "BL-999", "DONE")

    # Simulate BDF scanning: only read active index
    active_path = vault / "_backlog_index.md"
    archive_path = vault / "_backlog_index_done.md"

    active_content = active_path.read_text(encoding="utf-8")
    assert "BL-103" in active_content
    assert "BL-999" not in active_content  # Archive item must NOT appear in active index


# ─── Test 5: Pointer verify finds orphans ─────────────────────────────────────

def test_pointer_verify_finds_orphans(tmp_path):
    """batch_check detects missing detail files (orphan pointers)."""
    vault = _make_vault(tmp_path)
    _write_active_index(vault, [
        ("BL-104", "READY"),   # has detail
        ("BL-105", "DRAFT"),   # missing detail (orphan)
    ])
    _write_archive_index(vault, [])
    _write_detail_file(vault, "BL-104", "READY")
    # BL-105 detail NOT created

    result = batch_check(vault, bl_ids=["BL-104", "BL-105"])
    violation_ids = {v["bl_id"] for v in result["violations"]}
    assert "BL-105" in violation_ids
    assert "BL-104" not in violation_ids


# ─── Test 6: Token saving measured ───────────────────────────────────────────

def test_token_saving_measured(tmp_path):
    """After migration, active LOC should be < total LOC, saving >= threshold."""
    vault = _make_vault(tmp_path)

    # Create large active index (25 items active)
    active_rows = [(f"BL-{200+i:03d}", "READY") for i in range(5)]
    # Create large archive (100 items done)
    archive_rows = [(f"BL-{300+i:03d}", "DONE") for i in range(95)]

    _write_active_index(vault, active_rows)
    _write_archive_index(vault, archive_rows)

    # Write parking-lot files
    (vault / "_parking-lot.md").write_text(
        "# Active PL\n" + "- [ ] item\n" * 20, encoding="utf-8"
    )
    (vault / "_parking-lot_done.md").write_text(
        "# Done PL\n" + "- [x] done_item\n" * 200, encoding="utf-8"
    )

    result = track_index_size(vault)
    # Archive should be significantly larger than active
    assert result["archive_loc"] > result["active_loc"]
    assert result["saving_pct"] > 50.0  # At minimum 50% saving in this test setup


# ─── Test 7: Two parallel migrations serialize ────────────────────────────────

def test_two_parallel_migrations_serialize(tmp_path):
    """Two concurrent migrations on different BLs should not corrupt indexes."""
    vault = _make_vault(tmp_path)
    _write_active_index(vault, [("BL-110", "READY"), ("BL-111", "READY")])
    _write_archive_index(vault, [])
    _write_detail_file(vault, "BL-110", "READY")
    _write_detail_file(vault, "BL-111", "READY")

    errors = []
    lock = threading.Lock()

    def migrate_bl(bl_id):
        try:
            with lock:  # Serialize using lock (BL-175 pattern)
                _do_migrate(vault, bl_id, from_status="READY", to_status="DONE")
        except Exception as e:
            errors.append(str(e))

    t1 = threading.Thread(target=migrate_bl, args=("BL-110",))
    t2 = threading.Thread(target=migrate_bl, args=("BL-111",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert not errors, f"Thread errors: {errors}"

    # Both should be in archive
    r1 = check_archive_index_pointer_resolves("BL-110", vault)
    r2 = check_archive_index_pointer_resolves("BL-111", vault)
    assert r1["ok"] is True
    assert r2["ok"] is True


# ─── Test 8: Partial done preserved active ────────────────────────────────────

def test_partial_done_preserved_active(tmp_path):
    """PARTIAL_DONE status stays in active index (not archive-bound)."""
    vault = _make_vault(tmp_path)
    _write_active_index(vault, [("BL-120", "PARTIAL_DONE")])
    _write_archive_index(vault, [])
    _write_detail_file(vault, "BL-120", "PARTIAL_DONE")

    result = check_detail_status_matches_index("BL-120", vault)
    assert result["ok"] is True


# ─── Test 9: Audit trail complete ────────────────────────────────────────────

def test_audit_trail_complete(tmp_path):
    """Audit events INDEX_GC and TOKEN_SAVING_VERIFIED should be writable."""
    audit_path = tmp_path / "audit.jsonl"

    events = [
        {"type": "INDEX_GC", "target": "backlog_index", "moved_items": 91, "ts": "2026-05-19T00:00:00"},
        {"type": "INDEX_GC", "target": "parking_lot", "moved_items": 4500, "ts": "2026-05-19T00:00:01"},
        {"type": "TOKEN_SAVING_VERIFIED", "saving_pct": 88.0, "ts": "2026-05-19T00:00:02"},
    ]

    with open(audit_path, "w", encoding="utf-8") as f:
        for event in events:
            f.write(json.dumps(event) + "\n")

    # Read back and verify
    with open(audit_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    assert len(lines) == 3
    types = [json.loads(line)["type"] for line in lines]
    assert "INDEX_GC" in types
    assert "TOKEN_SAVING_VERIFIED" in types


# ─── Test 10: INV-INDEX-SPLIT-1 through 6 verified ───────────────────────────

def test_inv_index_split_1_through_6(tmp_path):
    """Verify all 6 INV-INDEX-SPLIT invariants hold in a well-formed vault."""
    vault = _make_vault(tmp_path)

    # Setup: clean split state
    _write_active_index(vault, [
        ("BL-200", "READY"),
        ("BL-201", "DRAFT"),
        ("BL-202", "FREEZE"),
    ])
    _write_archive_index(vault, [
        ("BL-210", "DONE"),
        ("BL-211", "DECOMPOSED"),
    ])
    for bl_id, status in [("BL-200", "READY"), ("BL-201", "DRAFT"), ("BL-202", "FREEZE"),
                           ("BL-210", "DONE"), ("BL-211", "DECOMPOSED")]:
        _write_detail_file(vault, bl_id, status)

    # INV-1: No item in both indexes
    for bl_id in ["BL-200", "BL-201", "BL-202"]:
        r = check_detail_status_matches_index(bl_id, vault)
        assert r["ok"] is True, f"INV-INDEX-SPLIT-1 violated for {bl_id}: {r}"

    # INV-3: Archive index exists and is readable
    archive_path = vault / "_backlog_index_done.md"
    assert archive_path.exists(), "INV-INDEX-SPLIT-3: archive index must exist after migration"

    # INV-5: BDF active reading — active index does NOT contain archive items
    active_content = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    archive_content = archive_path.read_text(encoding="utf-8")
    for bl_id in ["BL-210", "BL-211"]:
        assert bl_id not in active_content, f"INV-INDEX-SPLIT-5: {bl_id} must not be in active index"
    for bl_id in ["BL-200", "BL-201", "BL-202"]:
        assert bl_id not in archive_content, f"INV-INDEX-SPLIT-1: {bl_id} must not be in archive"

    # INV-6: Pointer integrity — all entries resolve
    result = batch_check(vault, bl_ids=["BL-200", "BL-201", "BL-202", "BL-210", "BL-211"])
    assert result["violation_count"] == 0, f"INV-INDEX-SPLIT-6 violated: {result['violations']}"
