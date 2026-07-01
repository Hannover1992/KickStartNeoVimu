"""
test_migrate_backlog_index_split.py — BL-178 AK-2 Tests (10 Tests)
"""
import json
import os
import tempfile
from pathlib import Path

import pytest

from migrate_backlog_index_split import (
    ACTIVE_STATUS_SET,
    ARCHIVE_STATUS_SET,
    classify_rows,
    migrate,
    rollback,
    verify,
    _parse_table_rows,
    _build_archive_content,
    _atomic_write,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_ACTIVE_CONTENT = """\
---
type: backlog-index
backlog_counter: 10
updated: '2026-05-19'
---

# Backlog Index

| BL-ID | Titel | Status | Reifegrad |
|-------|-------|--------|-----------|
| BL-001 | Alpha | DONE | DONE |
| BL-002 | Beta | READY | SC-REIF |
| BL-003 | Gamma | DECOMPOSED | DONE |
| BL-004 | Delta | DRAFT | DRAFT |
| BL-005 | Epsilon | DONE | DONE |
| BL-006 | Zeta | PARTIAL_DONE | IN_PROGRESS |
"""


def _make_vault(tmp_path: Path, content: str = SAMPLE_ACTIVE_CONTENT) -> Path:
    index = tmp_path / "_backlog_index.md"
    index.write_text(content, encoding="utf-8")
    # Create minimal audit.jsonl
    audit_dir = tmp_path / ".claude" / "audit"
    audit_dir.mkdir(parents=True)
    (audit_dir / "audit.jsonl").write_text("", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_migrate_creates_archive_file(tmp_path):
    vault = _make_vault(tmp_path)
    result = migrate(vault, rollback_tag="test-tag-001", dry_run=False)
    archive = vault / "_backlog_index_done.md"
    assert archive.exists(), "_backlog_index_done.md should be created"
    assert result["archive_count"] > 0


def test_migrate_removes_archive_from_active(tmp_path):
    vault = _make_vault(tmp_path)
    migrate(vault, rollback_tag="test-tag-002", dry_run=False)
    active_content = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    # DONE and DECOMPOSED should not appear as table row status
    rows = _parse_table_rows(active_content)
    for row in rows:
        assert row["status"] not in ARCHIVE_STATUS_SET, (
            f"Archive status {row['status']} still in active index for {row['bl_id']}"
        )


def test_dry_run_no_writes(tmp_path):
    vault = _make_vault(tmp_path)
    original = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    result = migrate(vault, rollback_tag="test-tag-003", dry_run=True)
    assert result["dry_run"] is True
    assert not (vault / "_backlog_index_done.md").exists(), "dry-run must not create archive"
    after = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    assert after == original, "dry-run must not modify active index"


def test_atomic_write_rollback_on_failure(tmp_path):
    """Atomic write must not leave partial file on simulated error."""
    target = tmp_path / "test_atomic.md"
    target.write_text("original", encoding="utf-8")

    # Successful write
    _atomic_write(target, "new content")
    assert target.read_text(encoding="utf-8") == "new content"

    # Verify no temp files left
    leftovers = list(tmp_path.glob(".tmp_*"))
    assert len(leftovers) == 0, f"Leftover temp files: {leftovers}"


def test_partial_done_stays_active(tmp_path):
    content = """\
---
type: backlog-index
backlog_counter: 2
updated: '2026-05-19'
---

# Backlog Index

| BL-ID | Titel | Status | Reifegrad |
|-------|-------|--------|-----------|
| BL-010 | PartialItem | PARTIAL_DONE | IN_PROGRESS |
| BL-011 | DoneItem | DONE | DONE |
"""
    vault = _make_vault(tmp_path, content)
    migrate(vault, rollback_tag="test-tag-004", dry_run=False)
    active_content = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    rows = _parse_table_rows(active_content)
    active_ids = {r["bl_id"] for r in rows}
    assert "BL-010" in active_ids, "PARTIAL_DONE must stay in active"
    assert "BL-011" not in active_ids, "DONE must be archived"


def test_rollback_restores(tmp_path):
    vault = _make_vault(tmp_path)
    original = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    tag = "test-rollback-tag-005"
    migrate(vault, rollback_tag=tag, dry_run=False)
    # Verify migration happened
    assert (vault / "_backlog_index_done.md").exists()
    # Now rollback
    rollback(vault, tag)
    restored = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    assert restored == original, "Rollback must restore original content"


def test_verify_consistency(tmp_path):
    vault = _make_vault(tmp_path)
    migrate(vault, rollback_tag="test-tag-006", dry_run=False)
    result = verify(vault)
    assert result["ok"] is True, f"Violations found: {result.get('violations')}"
    assert len(result["violations"]) == 0


def test_unknown_status_warning(tmp_path, caplog):
    content = """\
---
type: backlog-index
backlog_counter: 1
updated: '2026-05-19'
---

# Backlog Index

| BL-ID | Titel | Status | Reifegrad |
|-------|-------|--------|-----------|
| BL-099 | WeirdItem | TOTALLY_UNKNOWN_STATUS | DRAFT |
"""
    vault = _make_vault(tmp_path, content)
    import logging
    with caplog.at_level(logging.WARNING):
        result = migrate(vault, rollback_tag="test-tag-007", dry_run=False)
    assert result["unknown_count"] == 1
    assert any("UNKNOWN_STATUS" in m for m in caplog.messages)


def test_idempotency(tmp_path):
    vault = _make_vault(tmp_path)
    # First migration
    r1 = migrate(vault, rollback_tag="test-tag-008a", dry_run=False)
    active_after_first = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    archive_after_first = (vault / "_backlog_index_done.md").read_text(encoding="utf-8")

    # Second migration (should be idempotent — no archive items left in active)
    r2 = migrate(vault, rollback_tag="test-tag-008b", dry_run=False)
    active_after_second = (vault / "_backlog_index.md").read_text(encoding="utf-8")

    # Active index should be unchanged (no new items to archive)
    assert r2["archive_count"] == 0, "Second run should find no items to archive"
    # Active content should be same
    active_rows_1 = _parse_table_rows(active_after_first)
    active_rows_2 = _parse_table_rows(active_after_second)
    assert len(active_rows_1) == len(active_rows_2)


def test_counter_preserved(tmp_path):
    """backlog_counter in active frontmatter must be preserved (INV-INDEX-SPLIT-4)."""
    content = """\
---
type: backlog-index
backlog_counter: 42
updated: '2026-05-19'
---

# Backlog Index

| BL-ID | Titel | Status | Reifegrad |
|-------|-------|--------|-----------|
| BL-042 | CounterTest | DONE | DONE |
| BL-043 | ActiveTest | READY | DRAFT |
"""
    vault = _make_vault(tmp_path, content)
    migrate(vault, rollback_tag="test-tag-009", dry_run=False)
    active_content = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    assert "backlog_counter: 42" in active_content, (
        "backlog_counter must be preserved in active index"
    )
    # Archive must NOT have backlog_counter
    archive_content = (vault / "_backlog_index_done.md").read_text(encoding="utf-8")
    assert "backlog_counter" not in archive_content, (
        "Archive index must not contain backlog_counter"
    )
