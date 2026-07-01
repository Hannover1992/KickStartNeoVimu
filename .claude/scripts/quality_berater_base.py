"""
quality_berater_base.py — BL-177 Quality-Berater Base Class

Provides BaseQualityBerater with run(), write_output(), audit_trail() methods.
All specific Quality-Berater classes inherit from this base.

INV-QUALITY-1: exit_code=2 bei ERROR (BLOCK), 1 bei WARN, 0 bei PASS
INV-QUALITY-2: Jeder Lauf schreibt audit.jsonl Event
INV-QUALITY-3: Kein Silent-Fix ohne --auto-fix Flag
INV-QUALITY-4: Idempotente Checks
"""

import json
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

SEVERITY_ERROR = "ERROR"
SEVERITY_WARN = "WARN"
SEVERITY_INFO = "INFO"

BLOCK_STATUS_BLOCK = "BLOCK"
BLOCK_STATUS_WARN = "WARN"
BLOCK_STATUS_PASS = "PASS"

EXIT_PASS = 0
EXIT_WARN = 1
EXIT_BLOCK = 2


class Finding:
    """Single quality finding."""

    def __init__(
        self,
        severity: str,
        message: str,
        field: Optional[str] = None,
        fix_suggestion: Optional[str] = None,
    ):
        assert severity in (SEVERITY_ERROR, SEVERITY_WARN, SEVERITY_INFO), \
            f"Invalid severity: {severity}"
        self.severity = severity
        self.message = message
        self.field = field
        self.fix_suggestion = fix_suggestion

    def to_dict(self) -> dict:
        d = {
            "severity": self.severity,
            "message": self.message,
        }
        if self.field is not None:
            d["field"] = self.field
        if self.fix_suggestion is not None:
            d["fix_suggestion"] = self.fix_suggestion
        return d

    def __repr__(self) -> str:
        return f"Finding({self.severity}, field={self.field!r}, msg={self.message!r})"


class QualityResult:
    """Aggregated result from a Quality-Berater run."""

    def __init__(self, bl_id: str, check_type: str):
        self.bl_id = bl_id
        self.check_type = check_type
        self.findings: list[Finding] = []
        self.completed_at: str = datetime.utcnow().isoformat(timespec="seconds")
        self.auto_fixed: bool = False

    def add_finding(self, finding: Finding) -> None:
        self.findings.append(finding)

    @property
    def block_status(self) -> str:
        severities = {f.severity for f in self.findings}
        if SEVERITY_ERROR in severities:
            return BLOCK_STATUS_BLOCK
        if SEVERITY_WARN in severities:
            return BLOCK_STATUS_WARN
        return BLOCK_STATUS_PASS

    @property
    def exit_code(self) -> int:
        if self.block_status == BLOCK_STATUS_BLOCK:
            return EXIT_BLOCK
        if self.block_status == BLOCK_STATUS_WARN:
            return EXIT_WARN
        return EXIT_PASS

    def to_dict(self) -> dict:
        return {
            "completed_at": self.completed_at,
            "bl_id": self.bl_id,
            "check_type": self.check_type,
            "findings": [f.to_dict() for f in self.findings],
            "block_status": self.block_status,
            "exit_code": self.exit_code,
            "auto_fixed": self.auto_fixed,
        }

    def summary_line(self) -> str:
        counts = {SEVERITY_ERROR: 0, SEVERITY_WARN: 0, SEVERITY_INFO: 0}
        for f in self.findings:
            counts[f.severity] += 1
        return (
            f"[{self.block_status}] {self.bl_id} {self.check_type} — "
            f"E:{counts[SEVERITY_ERROR]} W:{counts[SEVERITY_WARN]} "
            f"I:{counts[SEVERITY_INFO]} (exit={self.exit_code})"
        )


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------


class BaseQualityBerater(ABC):
    """
    Abstract base for all Quality-Berater.

    Subclasses must implement:
        - check_type (str class attr)
        - run_checks(bl_id, data, auto_fix) -> QualityResult
    """

    check_type: str = "base"

    def __init__(self, repo_root: str):
        self.repo_root = repo_root
        self.audit_log_path = os.path.join(repo_root, ".claude", "audit", "audit.jsonl")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        bl_id: str,
        data: dict,
        auto_fix: bool = False,
    ) -> QualityResult:
        """
        Main entry point. Runs checks and returns QualityResult.

        INV-QUALITY-1: exit_code reflects severity
        INV-QUALITY-2: Always writes audit trail
        INV-QUALITY-3: auto_fix only when explicitly True
        """
        result = self.run_checks(bl_id=bl_id, data=data, auto_fix=auto_fix)
        result.auto_fixed = auto_fix and (result.exit_code < EXIT_BLOCK)
        self.audit_trail(result)
        return result

    @abstractmethod
    def run_checks(
        self,
        bl_id: str,
        data: dict,
        auto_fix: bool = False,
    ) -> QualityResult:
        """Perform actual checks. Must return QualityResult."""

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    def write_output(self, result: QualityResult, manifest_path: Optional[str] = None) -> None:
        """
        Write quality slot to per-BL _manifest.md if path given.
        Prints result summary to stdout always.

        INV-QUALITY-2: Ensures audit trail exists.
        """
        print(result.summary_line())
        for finding in result.findings:
            prefix = {"ERROR": "[ERR]", "WARN": "[WRN]", "INFO": "[INF]"}[finding.severity]
            field_part = f" ({finding.field})" if finding.field else ""
            fix_part = f" => {finding.fix_suggestion}" if finding.fix_suggestion else ""
            print(f"  {prefix}{field_part} {finding.message}{fix_part}")

        if manifest_path and os.path.isfile(manifest_path):
            self._inject_manifest_slot(result, manifest_path)

    def _inject_manifest_slot(self, result: QualityResult, manifest_path: str) -> None:
        """Append or replace quality slot in manifest YAML block."""
        slot_key = f"quality_{result.check_type}"
        slot_yaml = self._result_to_yaml(result, indent=4)

        with open(manifest_path, "r", encoding="utf-8") as fh:
            content = fh.read()

        # Simple append to BERATER_OUTPUTS block or end of file
        # Full YAML-parse is overkill here; use marker-based injection
        marker = f"  {slot_key}:"
        if marker in content:
            # Replace existing slot (find next top-level key or end of yaml block)
            # For safety, just skip re-injection in base (subclass can override)
            return

        # Append before closing ``` if present
        if "```" in content:
            insertion_point = content.rfind("```")
            new_content = content[:insertion_point] + f"\n  {slot_key}:\n{slot_yaml}\n" + content[insertion_point:]
        else:
            new_content = content + f"\n## Quality Check — {slot_key}\n```yaml\n{slot_key}:\n{slot_yaml}\n```\n"

        with open(manifest_path, "w", encoding="utf-8") as fh:
            fh.write(new_content)

    def _result_to_yaml(self, result: QualityResult, indent: int = 4) -> str:
        pad = " " * indent
        lines = [
            f"{pad}completed_at: '{result.completed_at}'",
            f"{pad}bl_id: {result.bl_id}",
            f"{pad}check_type: {result.check_type}",
            f"{pad}block_status: {result.block_status}",
            f"{pad}exit_code: {result.exit_code}",
            f"{pad}auto_fixed: {'true' if result.auto_fixed else 'false'}",
            f"{pad}findings:",
        ]
        if not result.findings:
            lines.append(f"{pad}  []")
        else:
            for f in result.findings:
                lines.append(f"{pad}  - severity: {f.severity}")
                if f.field:
                    lines.append(f"{pad}    field: {f.field}")
                lines.append(f"{pad}    message: \"{f.message}\"")
                if f.fix_suggestion:
                    lines.append(f"{pad}    fix_suggestion: \"{f.fix_suggestion}\"")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    def audit_trail(self, result: QualityResult) -> None:
        """
        Emit QUALITY_CHECK event to audit.jsonl.
        INV-QUALITY-2: Mandatory for every run.
        """
        event = {
            "event": "QUALITY_CHECK",
            "bl_id": result.bl_id,
            "check_type": result.check_type,
            "block_status": result.block_status,
            "exit_code": result.exit_code,
            "findings_count": len(result.findings),
            "timestamp": result.completed_at,
        }
        try:
            os.makedirs(os.path.dirname(self.audit_log_path), exist_ok=True)
            with open(self.audit_log_path, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(event) + "\n")
        except OSError:
            # Never crash pipeline due to audit failure
            print(f"[WARN] audit.jsonl write failed: {self.audit_log_path}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Helper utilities for subclasses
    # ------------------------------------------------------------------

    @staticmethod
    def make_finding(
        severity: str,
        message: str,
        field: Optional[str] = None,
        fix_suggestion: Optional[str] = None,
    ) -> Finding:
        return Finding(severity=severity, message=message, field=field, fix_suggestion=fix_suggestion)

    @staticmethod
    def error(message: str, field: Optional[str] = None, fix: Optional[str] = None) -> Finding:
        return Finding(SEVERITY_ERROR, message, field=field, fix_suggestion=fix)

    @staticmethod
    def warn(message: str, field: Optional[str] = None, fix: Optional[str] = None) -> Finding:
        return Finding(SEVERITY_WARN, message, field=field, fix_suggestion=fix)

    @staticmethod
    def info(message: str, field: Optional[str] = None) -> Finding:
        return Finding(SEVERITY_INFO, message, field=field)
