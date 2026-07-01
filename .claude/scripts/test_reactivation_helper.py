"""
test_reactivation_helper.py — BL-178 AK-5 Tests (5 Tests)
"""
import json
from pathlib import Path

import pytest

from reactivation_helper import reactivate_bl, reactivate_pl_item
from migrate_backlog_index_split import migrate as migrate_backlog


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ACTIVE_CONTENT = """\
---
type: backlog-index
backlog_counter: 5
updated: '2026-05-19'
---

# Backlog Index

| BL-ID | Titel | Status | Reifegrad |
|-------|-------|--------|-----------|
| BL-002 | Beta | READY | SC-REIF |
| BL-004 | Delta | DRAFT | DRAFT |
"""

ARCHIVE_CONTENT = """\
---
type: backlog-archive-index
created: '2026-05-19'
migrated_from: _backlog_index.md
items_count: 2
inv: INV-INDEX-SPLIT-1
---

# Backlog Archive Index

| BL-ID | Titel | Status | Reifegrad |
|-------|-------|--------|-----------|
| BL-001 | Alpha | DONE | DONE |
| BL-003 | Gamma | DECOMPOSED | DONE |
"""

ACTIVE_PL = """\
---
type: parking-lot
---

# Parking Lot

[ ] Open item keep
[ ] Another open item
"""

ARCHIVE_PL = """\
---
type: parking-lot-archive
---

# Parking Lot Archive

[x] BL-100 DONE item 1
[x] BL-200 DONE item 2
"""


def _make_reactivation_vault(tmp_path: Path) -> Path:
    (tmp_path / "_backlog_index.md").write_text(ACTIVE_CONTENT, encoding="utf-8")
    (tmp_path / "_backlog_index_done.md").write_text(ARCHIVE_CONTENT, encoding="utf-8")
    (tmp_path / "_parking-lot.md").write_text(ACTIVE_PL, encoding="utf-8")
    (tmp_path / "_parking-lot_done.md").write_text(ARCHIVE_PL, encoding="utf-8")
    audit_dir = tmp_path / ".claude" / "audit"
    audit_dir.mkdir(parents=True)
    (audit_dir / "audit.jsonl").write_text("", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_reactivation_pathway(tmp_path):
    vault = _make_reactivation_vault(tmp_path)
    result = reactivate_bl("BL-001", vault)
    assert result["bl_id"] == "BL-001"
    assert result["new_status"] == "DRAFT"

    # BL-001 should now be in active index
    active_content = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    assert "BL-001" in active_content

    # BL-001 should NOT be in archive anymore
    archive_content = (vault / "_backlog_index_done.md").read_text(encoding="utf-8")
    assert "BL-001" not in archive_content


def test_reactivation_audit_trail(tmp_path):
    vault = _make_reactivation_vault(tmp_path)
    reactivate_bl("BL-003", vault)

    audit_lines = (vault / ".claude" / "audit" / "audit.jsonl").read_text(encoding="utf-8").strip().splitlines()
    events = [json.loads(l) for l in audit_lines if l.strip()]
    reactivation_events = [e for e in events if e.get("type") == "REACTIVATION"]
    assert len(reactivation_events) == 1
    evt = reactivation_events[0]
    assert evt["bl_id"] == "BL-003"
    assert evt["from_archive"] is True
    assert evt["new_status"] == "DRAFT"


def test_reactivation_unknown_id_raises(tmp_path):
    vault = _make_reactivation_vault(tmp_path)
    with pytest.raises(ValueError, match="not found in archive"):
        reactivate_bl("BL-999", vault)


def test_active_archive_split_roundtrip(tmp_path):
    """Full roundtrip: active → archive → active without data loss."""
    from migrate_backlog_index_split import ARCHIVE_STATUS_SET

    initial_content = """\
---
type: backlog-index
backlog_counter: 5
updated: '2026-05-19'
---

# Backlog Index

| BL-ID | Titel | Status | Reifegrad |
|-------|-------|--------|-----------|
| BL-010 | One | READY | DRAFT |
| BL-020 | Two | DONE | DONE |
| BL-030 | Three | DRAFT | DRAFT |
| BL-040 | Four | DECOMPOSED | DONE |
| BL-050 | Five | IN_PROGRESS | SC-REIF |
"""
    vault = tmp_path
    (vault / "_backlog_index.md").write_text(initial_content, encoding="utf-8")
    audit_dir = vault / ".claude" / "audit"
    audit_dir.mkdir(parents=True)
    (audit_dir / "audit.jsonl").write_text("", encoding="utf-8")

    # Step 1: Migrate
    migrate_backlog(vault, rollback_tag="roundtrip-tag", dry_run=False)

    active_content = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    archive_content = (vault / "_backlog_index_done.md").read_text(encoding="utf-8")

    from migrate_backlog_index_split import _parse_table_rows
    active_ids = {r["bl_id"] for r in _parse_table_rows(active_content)}
    archive_ids = {r["bl_id"] for r in _parse_table_rows(archive_content)}

    assert "BL-020" in archive_ids
    assert "BL-040" in archive_ids
    assert "BL-010" in active_ids
    assert "BL-030" in active_ids
    assert "BL-050" in active_ids

    # Step 2: Re-activate BL-020
    result = reactivate_bl("BL-020", vault)
    assert result["new_status"] == "DRAFT"

    active_after = (vault / "_backlog_index.md").read_text(encoding="utf-8")
    active_ids_after = {r["bl_id"] for r in _parse_table_rows(active_after)}

    # BL-020 back in active, no items lost
    assert "BL-020" in active_ids_after
    original_active_ids = {"BL-010", "BL-030", "BL-050"}
    assert original_active_ids.issubset(active_ids_after), "No active items lost in roundtrip"


def test_pl_reactivation(tmp_path):
    vault = _make_reactivation_vault(tmp_path)
    result = reactivate_pl_item("BL-100", vault)
    assert result["status"] == "reactivated"

    # Active PL should contain the reactivated item
    active_content = (vault / "_parking-lot.md").read_text(encoding="utf-8")
    assert "BL-100" in active_content

    # Archive PL should not contain it
    archive_content = (vault / "_parking-lot_done.md").read_text(encoding="utf-8")
    assert "BL-100" not in archive_content
