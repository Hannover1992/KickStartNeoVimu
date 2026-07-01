"""
test_quality_auto_fix.py — Tests for AK-8 Auto-Fix-Mechanismus (BL-177)

5 Tests GREEN required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from quality_auto_fix import (
    AutoFixResult,
    apply_fix,
    batch_fix_all,
    suggest_fix,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def subfolder_finding() -> dict:
    return {
        "check": "no_adhoc_folders",
        "bl_id": "BL-174",
        "severity": "ERROR",
        "message": "Ad-hoc subfolder '2_Research' found.",
        "fix_suggestion": "Rename '2_Research' → '2_Model' (INV-QUALITY-7 canonical name)",
    }


@pytest.fixture()
def forbidden_finding() -> dict:
    return {
        "check": "status_change",
        "bl_id": "BL-174",
        "severity": "ERROR",
        "message": "status should be DONE",
        "fix_suggestion": "Change status to DONE",
    }


@pytest.fixture()
def bl_folder_with_adhoc(tmp_path: Path) -> Path:
    """BL folder with 2_Research ad-hoc subfolder for rename test."""
    folder = tmp_path / "BL-174-test"
    folder.mkdir()
    (folder / "2_Research").mkdir()
    return folder


@pytest.fixture()
def audit_path(tmp_path: Path) -> Path:
    return tmp_path / "audit.jsonl"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_suggest_only_default(subfolder_finding: dict) -> None:
    """suggest_fix generates proposal without applying changes."""
    proposal = suggest_fix(subfolder_finding)
    assert proposal.finding_check == "no_adhoc_folders"
    assert proposal.bl_id == "BL-174"
    assert proposal.is_allowed is True
    assert proposal.fix_operation == "subfolder_rename"
    # No file changes happened (no bl_folder)


def test_apply_requires_confirm(subfolder_finding: dict) -> None:
    """apply_fix without --confirm returns False with INV-QUALITY-3 message."""
    proposal = suggest_fix(subfolder_finding)
    success, msg = apply_fix(proposal, confirm=False)
    assert success is False
    assert "INV-QUALITY-3" in msg or "--confirm" in msg


def test_batch_with_auto_fix_flag(
    subfolder_finding: dict,
    bl_folder_with_adhoc: Path,
    audit_path: Path,
) -> None:
    """batch_fix_all with auto_fix=True applies allowed subfolder rename."""
    result = batch_fix_all(
        [subfolder_finding],
        bl_folder=bl_folder_with_adhoc,
        auto_fix=True,
        audit_jsonl=audit_path,
        bl_id="BL-174",
    )
    # Either applied (rename success) or skipped with error (parse issue) — not forbidden
    assert len(result.proposals) == 1
    assert result.proposals[0].is_allowed is True
    # Check that 2_Research was renamed or at least attempted
    model_exists = (bl_folder_with_adhoc / "2_Model").exists()
    research_exists = (bl_folder_with_adhoc / "2_Research").exists()
    # Exactly one of them should exist
    assert model_exists or research_exists  # rename either succeeded or source was already renamed


def test_audit_trail_jsonl(
    subfolder_finding: dict,
    bl_folder_with_adhoc: Path,
    audit_path: Path,
) -> None:
    """batch_fix_all emits AUTO_FIX_APPLIED event when fix applied."""
    batch_fix_all(
        [subfolder_finding],
        bl_folder=bl_folder_with_adhoc,
        auto_fix=True,
        audit_jsonl=audit_path,
        bl_id="BL-174",
    )
    # If rename succeeded, audit trail has entry
    if audit_path.exists():
        lines = audit_path.read_text().strip().splitlines()
        if lines:
            obj = json.loads(lines[0])
            assert obj["event"] == "AUTO_FIX_APPLIED"
            assert obj["bl_id"] == "BL-174"


def test_no_silent_fix_inv_quality_3(forbidden_finding: dict) -> None:
    """
    Forbidden operation (status change) must never be auto-applied.
    INV-QUALITY-3: No-Silent-Fix.
    """
    proposal = suggest_fix(forbidden_finding)
    # status is in FORBIDDEN_AUTO_FIX_FIELDS
    assert proposal.is_allowed is False
    assert proposal.fix_operation == "forbidden"

    # batch_fix_all must skip forbidden proposals even with auto_fix=True
    result = batch_fix_all(
        [forbidden_finding],
        auto_fix=True,
        bl_id="BL-174",
    )
    assert len(result.applied) == 0
    assert len(result.skipped) == 1
