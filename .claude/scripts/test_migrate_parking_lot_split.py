"""
test_migrate_parking_lot_split.py — BL-178 AK-3 Tests (5 Tests)
"""
import json
from pathlib import Path

import pytest

from migrate_parking_lot_split import (
    _build_archive_content,
    _classify_lines,
    migrate,
    rollback,
    verify,
    ARCHIVE_MARKERS,
    ACTIVE_MARKERS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_PL = """\
---
type: parking-lot
updated: '2026-05-19'
---

# Parking Lot

[x] DONE item 1 — shipped BL-100
[x] DONE item 2 — resolved
[ ] Open item A — needs investigation
[ ] Open item B — discuss with team
[~] Partial item C — in progress
[?] Unknown item D — unclear
[!] Alert item E — critical
[x] DONE item 3 — archived
"""


def _make_pl_vault(tmp_path: Path, content: str = SAMPLE_PL) -> Path:
    pl = tmp_path / "_parking-lot.md"
    pl.write_text(content, encoding="utf-8")
    audit_dir = tmp_path / ".claude" / "audit"
    audit_dir.mkdir(parents=True)
    (audit_dir / "audit.jsonl").write_text("", encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_migrate_creates_archive_file(tmp_path):
    vault = _make_pl_vault(tmp_path)
    result = migrate(vault, rollback_tag="test-pl-001", dry_run=False)
    archive = vault / "_parking-lot_done.md"
    assert archive.exists(), "_parking-lot_done.md should be created"
    assert result["archive_item_count"] == 3  # 3 [x] items


def test_migrate_removes_done_from_active(tmp_path):
    vault = _make_pl_vault(tmp_path)
    migrate(vault, rollback_tag="test-pl-002", dry_run=False)
    active_content = (vault / "_parking-lot.md").read_text(encoding="utf-8")
    # No [x] items should remain in active
    for line in active_content.splitlines():
        assert "[x]" not in line, f"[x] item still in active PL: {line!r}"


def test_dry_run_no_writes(tmp_path):
    vault = _make_pl_vault(tmp_path)
    original = (vault / "_parking-lot.md").read_text(encoding="utf-8")
    result = migrate(vault, rollback_tag="test-pl-003", dry_run=True)
    assert result["dry_run"] is True
    assert not (vault / "_parking-lot_done.md").exists()
    after = (vault / "_parking-lot.md").read_text(encoding="utf-8")
    assert after == original


def test_rollback_restores_pl(tmp_path):
    vault = _make_pl_vault(tmp_path)
    original = (vault / "_parking-lot.md").read_text(encoding="utf-8")
    tag = "test-pl-rollback-004"
    migrate(vault, rollback_tag=tag, dry_run=False)
    rollback(vault, tag)
    restored = (vault / "_parking-lot.md").read_text(encoding="utf-8")
    assert restored == original


def test_verify_no_done_in_active(tmp_path):
    vault = _make_pl_vault(tmp_path)
    migrate(vault, rollback_tag="test-pl-005", dry_run=False)
    result = verify(vault)
    assert result["ok"] is True
    assert len(result["violations"]) == 0


def test_active_markers_preserved(tmp_path):
    """[ ], [~], [?], [!] items must stay in active."""
    vault = _make_pl_vault(tmp_path)
    migrate(vault, rollback_tag="test-pl-006", dry_run=False)
    active_content = (vault / "_parking-lot.md").read_text(encoding="utf-8")
    assert "[ ] Open item A" in active_content
    assert "[~] Partial item C" in active_content
    assert "[?] Unknown item D" in active_content
    assert "[!] Alert item E" in active_content


def test_archive_has_correct_frontmatter(tmp_path):
    vault = _make_pl_vault(tmp_path)
    migrate(vault, rollback_tag="test-pl-007", dry_run=False)
    archive_content = (vault / "_parking-lot_done.md").read_text(encoding="utf-8")
    assert "type: parking-lot-archive" in archive_content
    assert "migrated_from: _parking-lot.md" in archive_content


# ---------------------------------------------------------------------------
# BL-333 / G2c (ADDITIV — Stamping-Schicht). Die 7 Bestands-Tests oben bleiben
# UNVERAENDERT (Kanarienvogel). Greenfield: _build_archive_content emittiert
# format_version noch NICHT -> AssertionError = RED.
# ---------------------------------------------------------------------------

def test_archive_header_traegt_format_version():
    """G2c: Archiv-Header traegt format_version (== resolve_format_version('parking_lot')).

    Stamp ist additiv: type/created/migrated_from/lines_migrated bleiben erhalten,
    format_version kommt als zusaetzliche Frontmatter-Zeile hinzu.
    """
    content = _build_archive_content(
        archive_lines=["[x] DONE item — shipped\n"],
        migration_date="2026-06-13",
        source_file="_parking-lot.md",
    )
    fm = content.split("---", 2)[1]
    fv_lines = [ln for ln in fm.splitlines() if ln.startswith("format_version:")]
    assert len(fv_lines) == 1, (
        f"genau 1 format_version-Zeile im Archiv-Header erwartet, fand {fv_lines}"
    )
    # Bestands-Felder bleiben (additiv, kein Re-Format).
    assert "type: parking-lot-archive" in fm
    assert "migrated_from: _parking-lot.md" in fm
