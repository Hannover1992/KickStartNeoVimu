"""
test_quality_process_injection.py — Tests for AK-7 Process-Injection-Points (BL-177)

6 Tests GREEN required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from quality_process_injection import (
    ProcessInjectionResult,
    check_audit_jsonl_event,
    check_block_status_enforcement,
    check_quality_hooks_in_command,
    emit_quality_check_event,
    run_checks,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def command_with_hook(tmp_path: Path) -> Path:
    """Command markdown with quality hook call."""
    f = tmp_path / "_backlog.md"
    f.write_text("## Phase 4\nRun _backlog_quality_post_write after vault write.\n")
    return f


@pytest.fixture()
def command_without_hook(tmp_path: Path) -> Path:
    """Command markdown without any quality hook."""
    f = tmp_path / "_backlog.md"
    f.write_text("## Phase 4\nWrite BL.md to vault.\n# No quality checks here.\n")
    return f


@pytest.fixture()
def audit_jsonl_with_event(tmp_path: Path) -> Path:
    """audit.jsonl with one QUALITY_CHECK event."""
    path = tmp_path / "audit.jsonl"
    event = {
        "event": "QUALITY_CHECK",
        "bl_id": "BL-177",
        "check_type": "node_health",
        "exit_code": 0,
        "timestamp": "2026-05-19T10:00:00Z",
    }
    path.write_text(json.dumps(event) + "\n")
    return path


@pytest.fixture()
def audit_jsonl_empty(tmp_path: Path) -> Path:
    """audit.jsonl with no QUALITY_CHECK events."""
    path = tmp_path / "audit.jsonl"
    path.write_text('{"event": "OTHER_EVENT", "bl_id": "BL-177"}\n')
    return path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_command_with_hook_passes(command_with_hook: Path) -> None:
    """Command markdown with quality hook → no WARN/ERROR findings."""
    findings = check_quality_hooks_in_command(command_with_hook)
    critical = [f for f in findings if f.severity in ("ERROR", "WARN")]
    assert critical == []


def test_command_without_hook_warns(command_without_hook: Path) -> None:
    """Command markdown without quality hook (has injection in map) → WARN."""
    findings = check_quality_hooks_in_command(command_without_hook)
    # _backlog has 1 registered injection point
    warns = [f for f in findings if f.severity == "WARN"]
    assert len(warns) >= 1
    assert any("_backlog_quality_post_write" in (f.fix_suggestion or "") for f in warns)


def test_audit_jsonl_event_found(audit_jsonl_with_event: Path) -> None:
    """QUALITY_CHECK event exists in audit.jsonl → 0 findings."""
    findings = check_audit_jsonl_event(audit_jsonl_with_event, bl_id="BL-177")
    assert findings == []


def test_audit_jsonl_event_missing(audit_jsonl_empty: Path) -> None:
    """No QUALITY_CHECK events → INFO finding."""
    findings = check_audit_jsonl_event(audit_jsonl_empty, bl_id="BL-177")
    assert len(findings) == 1
    assert findings[0].severity == "INFO"


def test_block_status_enforcement_valid() -> None:
    """BLOCK + exit_code=2 → no findings (compliant)."""
    output = {"bl_id": "BL-177", "block_status": "BLOCK", "exit_code": 2}
    findings = check_block_status_enforcement(output)
    assert findings == []


def test_block_status_enforcement_violation() -> None:
    """BLOCK + exit_code=0 → ERROR finding (INV-QUALITY-1 violation)."""
    output = {"bl_id": "BL-177", "block_status": "BLOCK", "exit_code": 0}
    findings = check_block_status_enforcement(output)
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"
    assert "INV-QUALITY-1" in findings[0].message


def test_emit_quality_check_event(tmp_path: Path) -> None:
    """emit_quality_check_event writes valid JSONL entry."""
    audit_path = tmp_path / "audit.jsonl"
    emit_quality_check_event(audit_path, "BL-177", "subfolder_schema", 0)
    lines = audit_path.read_text().strip().splitlines()
    assert len(lines) == 1
    obj = json.loads(lines[0])
    assert obj["event"] == "QUALITY_CHECK"
    assert obj["bl_id"] == "BL-177"
    assert obj["check_type"] == "subfolder_schema"
    assert obj["exit_code"] == 0
