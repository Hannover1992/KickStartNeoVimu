"""
quality_process_injection.py — AK-7 Process-Injection-Points (BL-177)

Checks that Quality-Berater calls are properly integrated into Command workflows.
Validates audit.jsonl for QUALITY_CHECK events and block-status enforcement.

Exit codes:
  0 = PASS
  1 = WARN
  2 = ERROR
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Injection-Point Registry (AK-7 Injection-Map)
# ---------------------------------------------------------------------------

INJECTION_MAP: list[dict] = [
    {
        "command": "_backlog",
        "phase": "Phase 4 (Vault-Write)",
        "berater": "_backlog_quality_post_write",
        "block_type": "ERROR=BLOCK",
        "trigger": "Nach schreiben BL-XXX.md",
    },
    {
        "command": "_A_orchestrate",
        "phase": "Phase 3 (model)",
        "berater": "_A_quality_model_node",
        "block_type": "WARN=Log",
        "trigger": "Nach schreiben Model.md",
    },
    {
        "command": "_A_orchestrate",
        "phase": "Phase 4 (spec)",
        "berater": "_A_quality_spec_node",
        "block_type": "WARN=Log",
        "trigger": "Nach schreiben Spec.md",
    },
    {
        "command": "_A_orchestrate",
        "phase": "Phase 4k (K-Score)",
        "berater": "_A_quality_kscore_node",
        "block_type": "INFO=Audit",
        "trigger": "Nach schreiben K-SCORE.md",
    },
    {
        "command": "_IDF_orchestrate",
        "phase": "Phase 6 sequencePlanner",
        "berater": "_IDF_quality_edge_check",
        "block_type": "ERROR=BLOCK",
        "trigger": "Nach items_routed_ready",
    },
    {
        "command": "_SDF_orchestrate_post",
        "phase": "Phase 3.5 modelSync",
        "berater": "_SDF_quality_model_promotion",
        "block_type": "WARN=Log",
        "trigger": "Nach Model-Promotion",
    },
]

CROSS_CUTTING_BERATER = [
    "_quality_backlink_resolver",
    "_quality_tag_consistency",
    "_quality_subfolder_schema",
]

# Patterns indicating Quality-Berater calls in command markdown
QUALITY_CALL_PATTERNS = [
    re.compile(r"quality_\w+", re.IGNORECASE),
    re.compile(r"_quality_\w+", re.IGNORECASE),
    re.compile(r"_\w+_quality_\w+", re.IGNORECASE),
    re.compile(r"QUALITY_CHECK", re.IGNORECASE),
    re.compile(r"quality-berater", re.IGNORECASE),
]


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class InjectionFinding:
    severity: str
    check: str
    context: str
    message: str
    fix_suggestion: Optional[str] = None


@dataclass
class ProcessInjectionResult:
    context: str
    findings: list[InjectionFinding] = field(default_factory=list)
    block_status: str = "PASS"
    exit_code: int = 0
    compliance_score: float = 1.0
    completed_at: str = field(default_factory=lambda: datetime.now().isoformat() + "Z")

    def add(self, finding: InjectionFinding) -> None:
        self.findings.append(finding)
        if finding.severity == "ERROR":
            self.block_status = "BLOCK"
            self.exit_code = 2
        elif finding.severity == "WARN" and self.exit_code < 2:
            if self.block_status == "PASS":
                self.block_status = "WARN"
            self.exit_code = max(self.exit_code, 1)

    def compute_compliance_score(self, total_checks: int) -> None:
        if total_checks == 0:
            self.compliance_score = 1.0
            return
        error_count = sum(1 for f in self.findings if f.severity == "ERROR")
        warn_count = sum(1 for f in self.findings if f.severity == "WARN")
        # ERRORs count double
        penalty = (error_count * 2 + warn_count) / (total_checks * 2)
        self.compliance_score = max(0.0, round(1.0 - penalty, 2))

    def to_dict(self) -> dict:
        return {
            "completed_at": self.completed_at,
            "context": self.context,
            "check_type": "process_injection",
            "findings": [
                {
                    "severity": f.severity,
                    "field": f.check,
                    "message": f.message,
                    "fix_suggestion": f.fix_suggestion,
                }
                for f in self.findings
            ],
            "block_status": self.block_status,
            "exit_code": self.exit_code,
            "compliance_score": self.compliance_score,
        }


# ---------------------------------------------------------------------------
# Core checks (AK-7)
# ---------------------------------------------------------------------------


def check_quality_hooks_in_command(command_md: Path) -> list[InjectionFinding]:
    """
    Check whether a command markdown file contains Quality-Berater calls.
    Searches for known quality call patterns (INV-QUALITY-1 enforcement).
    """
    findings: list[InjectionFinding] = []
    if not command_md.exists():
        findings.append(
            InjectionFinding(
                severity="WARN",
                check="command_file_exists",
                context=str(command_md),
                message=f"Command file '{command_md.name}' not found — cannot verify quality hooks.",
                fix_suggestion=f"Create {command_md} with quality hook pseudocode.",
            )
        )
        return findings

    text = command_md.read_text(encoding="utf-8", errors="replace")
    found_any = any(pat.search(text) for pat in QUALITY_CALL_PATTERNS)

    if not found_any:
        cmd_name = command_md.stem
        relevant = [inj for inj in INJECTION_MAP if inj["command"] == cmd_name]
        if relevant:
            findings.append(
                InjectionFinding(
                    severity="WARN",
                    check="quality_hooks_in_command",
                    context=command_md.name,
                    message=(
                        f"Command '{cmd_name}' has {len(relevant)} registered injection point(s) "
                        f"but no Quality-Berater calls found in markdown."
                    ),
                    fix_suggestion=(
                        f"Add quality calls: "
                        + ", ".join(inj["berater"] for inj in relevant)
                    ),
                )
            )
    return findings


def check_audit_jsonl_event(
    audit_jsonl_path: Path,
    event_type: str = "QUALITY_CHECK",
    bl_id: Optional[str] = None,
) -> list[InjectionFinding]:
    """
    Verify QUALITY_CHECK events exist in audit.jsonl.
    Returns WARN if no events found (not ERROR — first run may have none).
    """
    findings: list[InjectionFinding] = []
    if not audit_jsonl_path.exists():
        findings.append(
            InjectionFinding(
                severity="INFO",
                check="audit_jsonl_exists",
                context=str(audit_jsonl_path),
                message=f"audit.jsonl not found at '{audit_jsonl_path}'. No audit trail.",
                fix_suggestion="Ensure audit.jsonl is created by Quality-Berater runs.",
            )
        )
        return findings

    events: list[dict] = []
    with audit_jsonl_path.open(encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                if obj.get("event") == event_type:
                    if bl_id is None or obj.get("bl_id") == bl_id:
                        events.append(obj)
            except json.JSONDecodeError:
                pass

    if not events:
        scope = f" for bl_id={bl_id}" if bl_id else ""
        findings.append(
            InjectionFinding(
                severity="INFO",
                check="audit_jsonl_event",
                context=str(audit_jsonl_path.name),
                message=(
                    f"No '{event_type}' events found in audit.jsonl{scope}. "
                    f"Quality-Berater may not have run yet."
                ),
                fix_suggestion=f"Run Quality-Berater checks to generate QUALITY_CHECK events.",
            )
        )
    return findings


def check_block_status_enforcement(berater_output: dict) -> list[InjectionFinding]:
    """
    Validate that a berater_output dict respects INV-QUALITY-1:
    exit_code=2 when block_status=BLOCK.
    exit_code=1 when block_status=WARN.
    exit_code=0 when block_status=PASS.
    """
    findings: list[InjectionFinding] = []
    block_status = berater_output.get("block_status", "PASS")
    exit_code = berater_output.get("exit_code", 0)
    bl_id = berater_output.get("bl_id", "?")

    expected = {"BLOCK": 2, "WARN": 1, "PASS": 0}
    expected_code = expected.get(block_status, 0)

    if exit_code != expected_code:
        findings.append(
            InjectionFinding(
                severity="ERROR",
                check="block_status_enforcement",
                context=bl_id,
                message=(
                    f"BL '{bl_id}': block_status='{block_status}' requires exit_code={expected_code} "
                    f"but got exit_code={exit_code} (INV-QUALITY-1 violation)."
                ),
                fix_suggestion=f"Set exit_code={expected_code} when block_status={block_status}.",
            )
        )
    return findings


def emit_quality_check_event(
    audit_jsonl_path: Path,
    bl_id: str,
    check_type: str,
    exit_code: int,
) -> None:
    """Emit a QUALITY_CHECK event to audit.jsonl (INV-QUALITY-2)."""
    event = {
        "event": "QUALITY_CHECK",
        "bl_id": bl_id,
        "check_type": check_type,
        "exit_code": exit_code,
        "timestamp": datetime.now().isoformat() + "Z",
    }
    with audit_jsonl_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_checks(
    command_files: list[Path],
    audit_jsonl: Optional[Path] = None,
    bl_id: Optional[str] = None,
    berater_outputs: Optional[list[dict]] = None,
) -> ProcessInjectionResult:
    context = bl_id or "global"
    result = ProcessInjectionResult(context=context)
    total_checks = 0

    # Check 1: quality hooks in each command file
    for cmd_file in command_files:
        for f in check_quality_hooks_in_command(cmd_file):
            result.add(f)
        total_checks += 1

    # Check 2: audit.jsonl events
    if audit_jsonl:
        for f in check_audit_jsonl_event(audit_jsonl, bl_id=bl_id):
            result.add(f)
        total_checks += 1

    # Check 3: block status enforcement for each berater output
    for output in (berater_outputs or []):
        for f in check_block_status_enforcement(output):
            result.add(f)
        total_checks += 1

    result.compute_compliance_score(total_checks)
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AK-7 Process-Injection-Points checker (BL-177)"
    )
    parser.add_argument("--commands-dir", default=None, help="Dir with command .md files")
    parser.add_argument("--audit-jsonl", default=None, help="Path to audit.jsonl")
    parser.add_argument("--bl", default=None, help="BL-XXX to filter audit events")
    parser.add_argument("--json", action="store_true", help="JSON output")

    args = parser.parse_args(argv)

    # Collect command files
    command_files: list[Path] = []
    if args.commands_dir:
        cmd_dir = Path(args.commands_dir)
        for inj in INJECTION_MAP:
            candidates = [
                cmd_dir / f"_{inj['command']}.md",
                cmd_dir / f"{inj['command']}.md",
            ]
            for c in candidates:
                if c.exists():
                    command_files.append(c)

    audit_jsonl = Path(args.audit_jsonl) if args.audit_jsonl else None

    result = run_checks(command_files, audit_jsonl, bl_id=args.bl)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_result(result)

    return result.exit_code


def _print_result(result: ProcessInjectionResult) -> None:
    print(f"\n=== Process-Injection-Check: {result.context} ===")
    print(f"Status: {result.block_status} (exit_code={result.exit_code})")
    print(f"Compliance-Score: {result.compliance_score:.0%}")
    print(f"Findings: {len(result.findings)}")

    if not result.findings:
        print("  [PASS] No issues.")
        return

    for f in result.findings:
        icon = {"ERROR": "[ERROR]", "WARN": "[WARN]", "INFO": "[INFO]"}.get(f.severity, "[?]")
        print(f"\n  {icon} [{f.check}] {f.context}")
        print(f"    {f.message}")
        if f.fix_suggestion:
            print(f"    Fix: {f.fix_suggestion}")

    print(f"\nInjection-Map ({len(INJECTION_MAP)} entries):")
    for inj in INJECTION_MAP:
        print(f"  {inj['command']} @ {inj['phase']} → {inj['berater']} [{inj['block_type']}]")


if __name__ == "__main__":
    sys.exit(main())
