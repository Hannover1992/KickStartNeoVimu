"""
test_quality_subfolder_schema.py — Tests for AK-5 Subfolder-Schema-Validator (BL-177)

7 Tests GREEN required.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# Allow running from repo root or scripts dir
sys.path.insert(0, str(Path(__file__).parent))

from quality_subfolder_schema import (
    REQUIRED_SUBFOLDERS,
    auto_fix_rename_suggestion,
    check_no_adhoc_folders,
    check_required_subfolders,
    check_subfolder_not_empty,
    run_checks,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def bl_folder_full(tmp_path: Path) -> Path:
    """BL folder with all required + some optional subfolders, each with a valid file."""
    folder = tmp_path / "BL-177-test"
    folder.mkdir()
    for sub in REQUIRED_SUBFOLDERS:
        sub_path = folder / sub
        sub_path.mkdir()
        (sub_path / f"BL-177_{sub.replace('-', '_')}.md").write_text("# content")
    # Optional: add Sources + Crumbs
    (folder / "Sources").mkdir()
    (folder / "Crumbs").mkdir()
    return folder


@pytest.fixture()
def bl_folder_missing_model(tmp_path: Path) -> Path:
    """BL folder missing 2_Model subfolder."""
    folder = tmp_path / "BL-177-test"
    folder.mkdir()
    for sub in REQUIRED_SUBFOLDERS:
        if sub == "2_Model":
            continue
        sub_path = folder / sub
        sub_path.mkdir()
        (sub_path / f"BL-177_{sub}.md").write_text("# content")
    return folder


@pytest.fixture()
def bl_folder_adhoc_research(tmp_path: Path) -> Path:
    """BL folder with ad-hoc 2_Research subfolder."""
    folder = tmp_path / "BL-174-test"
    folder.mkdir()
    for sub in REQUIRED_SUBFOLDERS:
        sub_path = folder / sub
        sub_path.mkdir()
        (sub_path / f"BL-174_{sub}.md").write_text("# content")
    (folder / "2_Research").mkdir()  # ad-hoc
    return folder


@pytest.fixture()
def bl_folder_adhoc_implementation(tmp_path: Path) -> Path:
    """BL folder with ad-hoc 4_Implementation subfolder (not in whitelist)."""
    folder = tmp_path / "BL-175-test"
    folder.mkdir()
    for sub in REQUIRED_SUBFOLDERS:
        sub_path = folder / sub
        sub_path.mkdir()
        (sub_path / f"BL-175_{sub}.md").write_text("# content")
    (folder / "4_Implementation").mkdir()  # ad-hoc
    return folder


@pytest.fixture()
def bl_folder_naming_violation(tmp_path: Path) -> Path:
    """BL folder with 1_Task containing a file with bad naming."""
    folder = tmp_path / "BL-177-test"
    folder.mkdir()
    for sub in REQUIRED_SUBFOLDERS:
        sub_path = folder / sub
        sub_path.mkdir()
        if sub == "1_Task":
            (sub_path / "task.md").write_text("bad naming")
        else:
            (sub_path / f"BL-177_{sub}.md").write_text("# content")
    return folder


@pytest.fixture()
def bl_folder_empty_subfolder(tmp_path: Path) -> Path:
    """BL folder with an empty 6_PL subfolder."""
    folder = tmp_path / "BL-177-test"
    folder.mkdir()
    for sub in REQUIRED_SUBFOLDERS:
        sub_path = folder / sub
        sub_path.mkdir()
        if sub != "6_PL":
            (sub_path / f"BL-177_{sub}.md").write_text("# content")
    return folder


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_all_required_present(bl_folder_full: Path) -> None:
    """All required subfolders present → 0 ERROR/WARN findings."""
    findings = check_required_subfolders(bl_folder_full)
    errors_warns = [f for f in findings if f.severity in ("ERROR", "WARN")]
    assert errors_warns == [], f"Unexpected findings: {errors_warns}"


def test_adhoc_2_research_detected(bl_folder_adhoc_research: Path) -> None:
    """Ad-hoc '2_Research' folder detected as ERROR with rename suggestion."""
    findings = check_no_adhoc_folders(bl_folder_adhoc_research)
    adhoc_findings = [f for f in findings if f.folder == "2_Research"]
    assert len(adhoc_findings) == 1
    f = adhoc_findings[0]
    assert f.severity == "ERROR"
    assert "2_Research" in f.message
    assert f.fix_suggestion is not None
    assert "2_Model" in f.fix_suggestion


def test_adhoc_4_implementation(bl_folder_adhoc_implementation: Path) -> None:
    """Ad-hoc '4_Implementation' folder detected as ERROR."""
    findings = check_no_adhoc_folders(bl_folder_adhoc_implementation)
    adhoc_findings = [f for f in findings if f.folder == "4_Implementation"]
    assert len(adhoc_findings) == 1
    assert adhoc_findings[0].severity == "ERROR"
    assert adhoc_findings[0].fix_suggestion is not None


def test_naming_convention_violation(bl_folder_naming_violation: Path) -> None:
    """File 'task.md' violates BL-XXX naming convention → WARN."""
    findings = check_subfolder_not_empty(bl_folder_naming_violation, "1_Task")
    warn_findings = [f for f in findings if f.severity == "WARN"]
    assert len(warn_findings) >= 1
    assert any("task.md" in f.message for f in warn_findings)


def test_auto_fix_2_research_to_model() -> None:
    """auto_fix_rename_suggestion maps '2_Research' → '2_Model'."""
    suggestion = auto_fix_rename_suggestion("2_Research")
    assert "2_Model" in suggestion


def test_subfolder_empty_warn(bl_folder_empty_subfolder: Path) -> None:
    """Empty '6_PL' subfolder → INFO finding."""
    findings = check_subfolder_not_empty(bl_folder_empty_subfolder, "6_PL")
    assert len(findings) == 1
    assert findings[0].severity == "INFO"
    assert "empty" in findings[0].message.lower()


def test_pass_full_compliance(bl_folder_full: Path) -> None:
    """Full compliance BL folder → exit_code=0, block_status=PASS."""
    result = run_checks(bl_folder_full, "BL-177")
    # Only INFO findings allowed for PASS
    errors_warns = [f for f in result.findings if f.severity in ("ERROR", "WARN")]
    assert errors_warns == []
    assert result.exit_code == 0
    assert result.block_status == "PASS"


