"""
quality_auto_fix.py — AK-8 Auto-Fix-Mechanismus (BL-177)

Provides suggest/apply/batch fix operations for Quality-Berater findings.

Modes:
  suggest (default) — Print fix suggestions, no changes applied
  apply (--confirm)  — Apply a single fix after explicit user confirmation
  batch  (--auto-fix) — Apply all trivial fixes with audit trail

INV-QUALITY-3: NO silent auto-fix. Default = suggest only.
                apply requires --confirm, batch requires --auto-fix.

Forbidden auto-fix operations (hardcoded guard):
  - status / reifegrad changes
  - builds_on modifications
  - Wikilink additions

Exit codes:
  0 = PASS / fixes applied
  1 = WARN (some fixes skipped / not applicable)
  2 = ERROR (forbidden operation attempted or I/O error)
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
# Fix-Scope Registry
# ---------------------------------------------------------------------------

# Fields that ARE allowed for auto-fix
ALLOWED_AUTO_FIX_FIELDS = {"tags", "updated", "subfolder_rename"}

# Fields FORBIDDEN for auto-fix (INV-QUALITY-3, AK-8)
FORBIDDEN_AUTO_FIX_FIELDS = {"status", "reifegrad", "builds_on", "wikilinks", "related_bl"}

# Mapping from check_type to fix operation
CHECK_TO_FIX_MAP: dict[str, str] = {
    "subfolder_naming_convention": "subfolder_rename",
    "no_adhoc_folders": "subfolder_rename",
    "missing_updated_date": "updated",
    "missing_tags": "tags",
    "tags_count": "tags",
}


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class FixProposal:
    finding_check: str
    bl_id: str
    description: str
    fix_operation: str  # subfolder_rename | tags | updated | forbidden
    is_allowed: bool
    target_path: Optional[Path] = None
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    fix_suggestion: Optional[str] = None


@dataclass
class AutoFixResult:
    bl_id: str
    proposals: list[FixProposal] = field(default_factory=list)
    applied: list[FixProposal] = field(default_factory=list)
    skipped: list[FixProposal] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    exit_code: int = 0
    completed_at: str = field(default_factory=lambda: datetime.now().isoformat() + "Z")

    def to_dict(self) -> dict:
        return {
            "completed_at": self.completed_at,
            "bl_id": self.bl_id,
            "proposals_count": len(self.proposals),
            "applied_count": len(self.applied),
            "skipped_count": len(self.skipped),
            "errors": self.errors,
            "exit_code": self.exit_code,
            "applied": [
                {
                    "check": p.finding_check,
                    "operation": p.fix_operation,
                    "description": p.description,
                }
                for p in self.applied
            ],
        }


# ---------------------------------------------------------------------------
# Core functions
# ---------------------------------------------------------------------------


def suggest_fix(finding: dict) -> FixProposal:
    """
    Generate a FixProposal for a single finding dict.
    Default mode — no file changes, only proposal generation.
    """
    check = finding.get("check", finding.get("field", ""))
    bl_id = finding.get("bl_id", "?")
    severity = finding.get("severity", "INFO")
    message = finding.get("message", "")
    fix_suggestion = finding.get("fix_suggestion", "")

    # Determine fix operation
    operation = CHECK_TO_FIX_MAP.get(check, "unknown")
    is_allowed = operation in ALLOWED_AUTO_FIX_FIELDS

    # Check forbidden operations
    for forbidden in FORBIDDEN_AUTO_FIX_FIELDS:
        if forbidden in check.lower() or forbidden in message.lower():
            operation = "forbidden"
            is_allowed = False
            break

    description = f"[{severity}] {check}: {message}"
    if fix_suggestion:
        description += f" | Suggestion: {fix_suggestion}"

    return FixProposal(
        finding_check=check,
        bl_id=bl_id,
        description=description,
        fix_operation=operation,
        is_allowed=is_allowed,
        fix_suggestion=fix_suggestion,
    )


def apply_fix(
    proposal: FixProposal,
    bl_folder: Optional[Path] = None,
    confirm: bool = False,
) -> tuple[bool, str]:
    """
    Apply a single fix with explicit --confirm flag (INV-QUALITY-3).
    Returns (success, message).
    """
    if not confirm:
        return False, "Fix not applied: --confirm flag required (INV-QUALITY-3 No-Silent-Fix)."

    if not proposal.is_allowed:
        return False, (
            f"Fix FORBIDDEN: operation='{proposal.fix_operation}' is in FORBIDDEN_AUTO_FIX_FIELDS. "
            f"Manual intervention required (INV-QUALITY-3, AK-8)."
        )

    if proposal.fix_operation == "subfolder_rename":
        return _apply_subfolder_rename(proposal, bl_folder)
    elif proposal.fix_operation == "updated":
        return _apply_update_date(proposal, bl_folder)
    elif proposal.fix_operation == "tags":
        return _apply_tags_fix(proposal, bl_folder)
    else:
        return False, f"No auto-fix implementation for operation='{proposal.fix_operation}'."


def _apply_subfolder_rename(proposal: FixProposal, bl_folder: Optional[Path]) -> tuple[bool, str]:
    """Rename ad-hoc subfolder to canonical name."""
    if not bl_folder or not bl_folder.exists():
        return False, "bl_folder required for subfolder_rename."

    suggestion = proposal.fix_suggestion or ""
    # Parse "Rename 'old' → 'new'"
    match = re.search(r"[Rr]ename\s+'?([^'→]+)'?\s*→\s*'?([^'(\s]+)", suggestion)
    if not match:
        return False, f"Cannot parse rename from suggestion: '{suggestion}'"

    old_name = match.group(1).strip()
    new_name = match.group(2).strip()
    old_path = bl_folder / old_name
    new_path = bl_folder / new_name

    if not old_path.exists():
        return False, f"Source folder '{old_path}' does not exist."
    if new_path.exists():
        return False, f"Target folder '{new_path}' already exists — manual merge required."

    old_path.rename(new_path)
    return True, f"Renamed '{old_name}' → '{new_name}'"


def _apply_update_date(proposal: FixProposal, bl_folder: Optional[Path]) -> tuple[bool, str]:
    """Set/update the 'updated:' field in _manifest.md frontmatter."""
    if not bl_folder:
        return False, "bl_folder required for updated date fix."

    manifest = bl_folder / "_manifest.md"
    if not manifest.exists():
        return False, f"_manifest.md not found in {bl_folder}."

    text = manifest.read_text(encoding="utf-8")
    today = datetime.now().strftime("%Y-%m-%d")
    new_text = re.sub(
        r"^updated:\s*.+$",
        f"updated: '{today}'",
        text,
        flags=re.MULTILINE,
    )
    if new_text == text:
        # Add after created:
        new_text = re.sub(
            r"^(created:\s*.+)$",
            rf"\1\nupdated: '{today}'",
            text,
            flags=re.MULTILINE,
        )

    manifest.write_text(new_text, encoding="utf-8")
    return True, f"Set updated: '{today}' in _manifest.md"


def _apply_tags_fix(proposal: FixProposal, bl_folder: Optional[Path]) -> tuple[bool, str]:
    """Add missing tags to _manifest.md (only if unambiguously derivable)."""
    # Tags are domain knowledge — we only add bl/ID and type/X if BL-ID is known
    if not bl_folder:
        return False, "bl_folder required for tags fix."

    manifest = bl_folder / "_manifest.md"
    if not manifest.exists():
        return False, f"_manifest.md not found."

    bl_match = re.match(r"(BL-\d+)", bl_folder.name)
    if not bl_match:
        return False, "Cannot derive BL-ID from folder name."

    bl_id = bl_match.group(1)
    text = manifest.read_text(encoding="utf-8")

    # Check if tags section exists
    if "tags:" not in text:
        return False, "No tags: section found — cannot safely add tags."

    # Add bl/ID tag if missing
    bl_tag = f"bl/{bl_id}"
    if bl_tag not in text:
        text = text.replace("tags:", f"tags:\n  - {bl_tag}", 1)
        manifest.write_text(text, encoding="utf-8")
        return True, f"Added tag '{bl_tag}' to tags section."

    return False, f"Tag '{bl_tag}' already present — no change needed."


def batch_fix_all(
    findings: list[dict],
    bl_folder: Optional[Path] = None,
    auto_fix: bool = False,
    audit_jsonl: Optional[Path] = None,
    bl_id: str = "?",
) -> AutoFixResult:
    """
    Mass-fix for all findings with auto_fix flag.
    Each applied fix is written to audit trail (INV-QUALITY-2).
    INV-QUALITY-3: Requires --auto-fix flag; forbidden ops always skipped.
    """
    result = AutoFixResult(bl_id=bl_id)

    for finding in findings:
        proposal = suggest_fix(finding)
        result.proposals.append(proposal)

        if not auto_fix:
            result.skipped.append(proposal)
            continue

        if not proposal.is_allowed:
            # FORBIDDEN auto-fix — always skip with note
            result.skipped.append(proposal)
            continue

        success, message = apply_fix(proposal, bl_folder=bl_folder, confirm=True)
        if success:
            result.applied.append(proposal)
            # Emit audit event
            if audit_jsonl:
                _emit_fix_event(audit_jsonl, bl_id, proposal, message)
        else:
            result.errors.append(message)
            result.skipped.append(proposal)

    if result.errors:
        result.exit_code = 1
    return result


def _emit_fix_event(
    audit_jsonl: Path,
    bl_id: str,
    proposal: FixProposal,
    message: str,
) -> None:
    """Write AUTO_FIX_APPLIED event to audit trail (INV-QUALITY-2)."""
    event = {
        "event": "AUTO_FIX_APPLIED",
        "bl_id": bl_id,
        "check": proposal.finding_check,
        "operation": proposal.fix_operation,
        "description": message,
        "timestamp": datetime.now().isoformat() + "Z",
    }
    with audit_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AK-8 Auto-Fix-Mechanismus (BL-177 INV-QUALITY-3)"
    )
    parser.add_argument("--findings-json", default=None, help="JSON file with findings list")
    parser.add_argument("--bl-folder", default=None, help="BL folder path for file operations")
    parser.add_argument("--bl", default=None, help="BL-XXX identifier")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required for apply mode (single fix)",
    )
    parser.add_argument(
        "--auto-fix",
        action="store_true",
        help="Required for batch mode. All allowed fixes applied. Forbidden ops always skipped.",
    )
    parser.add_argument("--audit-jsonl", default=None, help="audit.jsonl path for audit trail")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Dry-run (default): suggest only, no changes. Use --auto-fix or --confirm to apply.",
    )

    args = parser.parse_args(argv)

    # Load findings
    findings: list[dict] = []
    if args.findings_json:
        findings_path = Path(args.findings_json)
        if findings_path.exists():
            data = json.loads(findings_path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                findings = data
            elif isinstance(data, dict) and "findings" in data:
                findings = data["findings"]

    bl_folder = Path(args.bl_folder) if args.bl_folder else None
    bl_id = args.bl or (bl_folder.name if bl_folder else "?")
    audit_jsonl = Path(args.audit_jsonl) if args.audit_jsonl else None

    if not findings:
        print("[INFO] No findings provided — nothing to fix.")
        return 0

    is_batch = args.auto_fix
    is_apply = args.confirm and not is_batch

    if is_batch:
        result = batch_fix_all(findings, bl_folder, auto_fix=True, audit_jsonl=audit_jsonl, bl_id=bl_id)
    elif is_apply and len(findings) == 1:
        proposal = suggest_fix(findings[0])
        success, msg = apply_fix(proposal, bl_folder, confirm=True)
        result = AutoFixResult(bl_id=bl_id)
        result.proposals.append(proposal)
        if success:
            result.applied.append(proposal)
        else:
            result.skipped.append(proposal)
            result.errors.append(msg)
    else:
        # Suggest mode (default / dry-run)
        result = AutoFixResult(bl_id=bl_id)
        print(f"[SUGGEST MODE] {len(findings)} findings — showing proposals only (INV-QUALITY-3).")
        print("Use --auto-fix for batch apply or --confirm for single apply.\n")
        for finding in findings:
            proposal = suggest_fix(finding)
            result.proposals.append(proposal)
            result.skipped.append(proposal)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_result(result)

    return result.exit_code


def _print_result(result: AutoFixResult) -> None:
    print(f"\n=== Auto-Fix: {result.bl_id} ===")
    print(f"Proposals: {len(result.proposals)}")
    print(f"Applied:   {len(result.applied)}")
    print(f"Skipped:   {len(result.skipped)}")
    if result.errors:
        print(f"Errors:    {len(result.errors)}")
        for e in result.errors:
            print(f"  [ERROR] {e}")

    for p in result.proposals:
        allowed_str = "ALLOWED" if p.is_allowed else "FORBIDDEN"
        applied_str = "APPLIED" if p in result.applied else "SKIPPED"
        print(f"\n  [{applied_str}][{allowed_str}] {p.finding_check}")
        print(f"    {p.description}")
        if p.fix_suggestion:
            print(f"    Suggestion: {p.fix_suggestion}")


if __name__ == "__main__":
    sys.exit(main())
