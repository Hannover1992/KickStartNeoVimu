"""
test_quality_berater_base.py — Tests for quality_berater_base.py (BL-177 AK-9)

4 Tests:
1. test_finding_severity_values — Finding accepts valid severities, rejects invalid
2. test_result_block_status_derivation — QualityResult.block_status derived correctly
3. test_exit_code_mapping — exit_code matches block_status
4. test_base_berater_audit_trail — audit.jsonl event emitted on run()
"""

import json
import os
import sys
import tempfile
import pytest

# Ensure scripts dir on path
sys.path.insert(0, os.path.dirname(__file__))

from quality_berater_base import (
    BaseQualityBerater,
    Finding,
    QualityResult,
    SEVERITY_ERROR,
    SEVERITY_WARN,
    SEVERITY_INFO,
    BLOCK_STATUS_BLOCK,
    BLOCK_STATUS_WARN,
    BLOCK_STATUS_PASS,
    EXIT_PASS,
    EXIT_WARN,
    EXIT_BLOCK,
)


# ---------------------------------------------------------------------------
# Minimal concrete subclass for testing
# ---------------------------------------------------------------------------

class _StubBerater(BaseQualityBerater):
    """Stub that returns findings injected via constructor."""

    check_type = "stub"

    def __init__(self, repo_root: str, findings: list):
        super().__init__(repo_root)
        self._findings = findings

    def run_checks(self, bl_id: str, data: dict, auto_fix: bool = False) -> QualityResult:
        result = QualityResult(bl_id=bl_id, check_type=self.check_type)
        for f in self._findings:
            result.add_finding(f)
        return result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_finding_severity_values():
    """Finding accepts ERROR/WARN/INFO, raises on unknown severity."""
    f_err = Finding(SEVERITY_ERROR, "error msg", field="status")
    assert f_err.severity == SEVERITY_ERROR
    assert f_err.field == "status"

    f_warn = Finding(SEVERITY_WARN, "warn msg")
    assert f_warn.severity == SEVERITY_WARN
    assert f_warn.field is None

    f_info = Finding(SEVERITY_INFO, "info msg", fix_suggestion="fix it")
    assert f_info.severity == SEVERITY_INFO
    assert f_info.fix_suggestion == "fix it"

    with pytest.raises(AssertionError):
        Finding("CRITICAL", "bad severity")


def test_result_block_status_derivation():
    """block_status is BLOCK when ERROR present, WARN when only WARN, PASS when all INFO."""
    # PASS case
    result_pass = QualityResult("BL-177", "stub")
    result_pass.add_finding(Finding(SEVERITY_INFO, "just info"))
    assert result_pass.block_status == BLOCK_STATUS_PASS

    # WARN case
    result_warn = QualityResult("BL-177", "stub")
    result_warn.add_finding(Finding(SEVERITY_WARN, "a warning"))
    assert result_warn.block_status == BLOCK_STATUS_WARN

    # BLOCK case (ERROR present)
    result_block = QualityResult("BL-177", "stub")
    result_block.add_finding(Finding(SEVERITY_WARN, "a warning"))
    result_block.add_finding(Finding(SEVERITY_ERROR, "an error"))
    assert result_block.block_status == BLOCK_STATUS_BLOCK

    # Empty findings = PASS
    result_empty = QualityResult("BL-177", "stub")
    assert result_empty.block_status == BLOCK_STATUS_PASS


def test_exit_code_mapping():
    """exit_code is 0/1/2 matching PASS/WARN/BLOCK."""
    r_pass = QualityResult("BL-177", "stub")
    assert r_pass.exit_code == EXIT_PASS  # 0

    r_warn = QualityResult("BL-177", "stub")
    r_warn.add_finding(Finding(SEVERITY_WARN, "w"))
    assert r_warn.exit_code == EXIT_WARN  # 1

    r_block = QualityResult("BL-177", "stub")
    r_block.add_finding(Finding(SEVERITY_ERROR, "e"))
    assert r_block.exit_code == EXIT_BLOCK  # 2


def test_base_berater_audit_trail():
    """BaseQualityBerater.run() emits QUALITY_CHECK event to audit.jsonl."""
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_dir = os.path.join(tmpdir, ".claude", "audit")
        os.makedirs(audit_dir)
        audit_path = os.path.join(audit_dir, "audit.jsonl")

        berater = _StubBerater(
            repo_root=tmpdir,
            findings=[Finding(SEVERITY_WARN, "test warning", field="tags")],
        )
        result = berater.run(bl_id="BL-177", data={})

        # exit_code = 1 (WARN)
        assert result.exit_code == EXIT_WARN
        assert result.block_status == BLOCK_STATUS_WARN

        # audit.jsonl must exist and contain valid JSON
        assert os.path.isfile(audit_path), "audit.jsonl was not created"
        with open(audit_path, encoding="utf-8") as fh:
            events = [json.loads(line) for line in fh if line.strip()]

        assert len(events) == 1
        ev = events[0]
        assert ev["event"] == "QUALITY_CHECK"
        assert ev["bl_id"] == "BL-177"
        assert ev["check_type"] == "stub"
        assert ev["exit_code"] == EXIT_WARN
        assert ev["findings_count"] == 1
