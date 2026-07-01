"""
quality_subfolder_schema.py — AK-5 Subfolder-Schema-Validator (BL-177)

Checks vault BL-folder subfolder compliance against vault-routing.json schema.
INV-QUALITY-7: Only vault-routing.json defined subfolders allowed.

Exit codes:
  0 = PASS (all checks pass)
  1 = WARN (warnings only)
  2 = ERROR (at least one error finding)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REQUIRED_SUBFOLDERS = ["1_Task", "2_Model", "3_Spec", "4_K-Score", "5_Gap", "6_PL"]
OPTIONAL_SUBFOLDERS = {"Sources", "Crumbs", "W_fetch", "Implementation"}
ALLOWED_SUBFOLDERS = set(REQUIRED_SUBFOLDERS) | OPTIONAL_SUBFOLDERS

# Ad-hoc → canonical rename suggestions (INV-QUALITY-7)
RENAME_MAP: dict[str, str] = {
    "2_Research": "2_Model",
    "4_Implementation": "Implementation",
    "5_Tests": "6_PL",
    "4_Tests": "6_PL",
    "3_Implementation": "Implementation",
    "3_Research": "2_Model",
    "Research": "2_Model",
    "Tests": "6_PL",
    "Spec": "3_Spec",
    "Model": "2_Model",
    "Task": "1_Task",
    "KScore": "4_K-Score",
    "K_Score": "4_K-Score",
    "Gap": "5_Gap",
    "PL": "6_PL",
}

# Naming convention: BL-XXX_{type}.md
BL_FILE_PATTERN = re.compile(r"^BL-\d+[a-zA-Z0-9_-]*\.[a-zA-Z]+$")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Finding:
    severity: str  # ERROR | WARN | INFO
    check: str
    folder: str
    message: str
    fix_suggestion: Optional[str] = None


@dataclass
class SubfolderCheckResult:
    bl_id: str
    bl_folder: Path
    findings: list[Finding] = field(default_factory=list)
    block_status: str = "PASS"
    exit_code: int = 0
    completed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)
        if finding.severity == "ERROR":
            self.block_status = "BLOCK"
            self.exit_code = 2
        elif finding.severity == "WARN" and self.exit_code < 2:
            if self.block_status == "PASS":
                self.block_status = "WARN"
            self.exit_code = max(self.exit_code, 1)

    def to_dict(self) -> dict:
        return {
            "completed_at": self.completed_at,
            "bl_id": self.bl_id,
            "check_type": "subfolder_schema",
            "findings": [
                {
                    "severity": f.severity,
                    "field": f.folder,
                    "message": f.message,
                    "fix_suggestion": f.fix_suggestion,
                }
                for f in self.findings
            ],
            "block_status": self.block_status,
            "exit_code": self.exit_code,
        }


# ---------------------------------------------------------------------------
# Core checks
# ---------------------------------------------------------------------------


def check_required_subfolders(
    bl_folder: Path,
    vault_routing: Optional[dict] = None,
) -> list[Finding]:
    """
    Check that all required subfolders are present.
    Uses vault_routing override if provided, else falls back to REQUIRED_SUBFOLDERS.
    """
    required = REQUIRED_SUBFOLDERS
    if vault_routing:
        required = vault_routing.get("required_subfolders", REQUIRED_SUBFOLDERS)

    findings: list[Finding] = []
    existing = {p.name for p in bl_folder.iterdir() if p.is_dir()}

    for subfolder in required:
        if subfolder not in existing:
            findings.append(
                Finding(
                    severity="WARN",
                    check="required_subfolders",
                    folder=subfolder,
                    message=f"Required subfolder '{subfolder}' missing in {bl_folder.name}.",
                    fix_suggestion=f"mkdir {bl_folder / subfolder}",
                )
            )
    return findings


def check_no_adhoc_folders(bl_folder: Path) -> list[Finding]:
    """
    Detect any subfolders that are NOT in ALLOWED_SUBFOLDERS.
    Ad-hoc folders = ERROR with rename suggestion (INV-QUALITY-7).
    """
    findings: list[Finding] = []
    for child in bl_folder.iterdir():
        if not child.is_dir():
            continue
        if child.name not in ALLOWED_SUBFOLDERS:
            suggestion = auto_fix_rename_suggestion(child.name)
            findings.append(
                Finding(
                    severity="ERROR",
                    check="no_adhoc_folders",
                    folder=child.name,
                    message=(
                        f"Ad-hoc subfolder '{child.name}' found in {bl_folder.name}. "
                        f"Only {sorted(ALLOWED_SUBFOLDERS)} are allowed (INV-QUALITY-7)."
                    ),
                    fix_suggestion=suggestion,
                )
            )
    return findings


def check_subfolder_not_empty(bl_folder: Path, subfolder: str) -> list[Finding]:
    """
    Check that subfolder contains at least one file following BL-XXX naming convention.
    Returns INFO if subfolder exists but is empty.
    Returns WARN if files present but naming convention violated.
    """
    findings: list[Finding] = []
    target = bl_folder / subfolder
    if not target.exists() or not target.is_dir():
        return findings

    files = [f for f in target.iterdir() if f.is_file()]
    if not files:
        findings.append(
            Finding(
                severity="INFO",
                check="subfolder_not_empty",
                folder=subfolder,
                message=f"Subfolder '{subfolder}' in {bl_folder.name} is empty.",
                fix_suggestion=f"Add at least one file following BL-XXX_<type>.md naming.",
            )
        )
        return findings

    # Check naming convention for each file
    for f in files:
        if not BL_FILE_PATTERN.match(f.name):
            findings.append(
                Finding(
                    severity="WARN",
                    check="subfolder_naming_convention",
                    folder=subfolder,
                    message=(
                        f"File '{f.name}' in '{subfolder}' does not follow "
                        f"BL-XXX_{{type}}.md naming convention."
                    ),
                    fix_suggestion=f"Rename to BL-XXX_{subfolder.replace('-', '_').lower()}.md",
                )
            )
    return findings


def auto_fix_rename_suggestion(adhoc_folder: str) -> str:
    """
    Return a rename suggestion for a known ad-hoc folder name.
    Returns a descriptive string if no mapping found.
    """
    if adhoc_folder in RENAME_MAP:
        canonical = RENAME_MAP[adhoc_folder]
        return f"Rename '{adhoc_folder}' → '{canonical}' (INV-QUALITY-7 canonical name)"
    return (
        f"Remove or rename '{adhoc_folder}' to one of: {sorted(ALLOWED_SUBFOLDERS)}. "
        f"No automatic mapping found — manual decision required."
    )


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_checks(
    bl_folder: Path,
    bl_id: str,
    vault_routing: Optional[dict] = None,
    auto_fix: bool = False,
) -> SubfolderCheckResult:
    result = SubfolderCheckResult(bl_id=bl_id, bl_folder=bl_folder)

    if not bl_folder.exists() or not bl_folder.is_dir():
        result.add(
            Finding(
                severity="ERROR",
                check="folder_exists",
                folder=str(bl_folder),
                message=f"BL folder '{bl_folder}' does not exist.",
            )
        )
        return result

    # Check 1: required subfolders
    for f in check_required_subfolders(bl_folder, vault_routing):
        result.add(f)

    # Check 2: no ad-hoc folders
    for f in check_no_adhoc_folders(bl_folder):
        result.add(f)

    # Check 3: subfolder naming + empty check for all required
    required = REQUIRED_SUBFOLDERS
    if vault_routing:
        required = vault_routing.get("required_subfolders", REQUIRED_SUBFOLDERS)
    for subfolder in required:
        for f in check_subfolder_not_empty(bl_folder, subfolder):
            result.add(f)

    # Auto-fix: apply renames if --auto-fix (only for ad-hoc folder renaming)
    if auto_fix:
        _apply_auto_fix(bl_folder, result)

    return result


def _apply_auto_fix(bl_folder: Path, result: SubfolderCheckResult) -> None:
    """Apply auto-fix for ad-hoc subfolder renames. Requires --auto-fix flag (INV-QUALITY-3)."""
    for finding in result.findings:
        if finding.check == "no_adhoc_folders" and finding.fix_suggestion:
            # Parse rename suggestion
            if "→" in finding.fix_suggestion:
                old_name = finding.folder
                new_name = finding.fix_suggestion.split("→")[1].strip().split(" ")[0].strip("'")
                old_path = bl_folder / old_name
                new_path = bl_folder / new_name
                if old_path.exists() and not new_path.exists():
                    old_path.rename(new_path)
                    finding.message += f" [AUTO-FIXED: renamed to '{new_name}']"
                    print(f"[AUTO-FIX] Renamed '{old_name}' → '{new_name}'")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _extract_bl_id(bl_folder: Path) -> str:
    """Extract BL-XXX from folder name like BL-177-knowledge-graph-qualitaet."""
    match = re.match(r"(BL-\d+)", bl_folder.name)
    return match.group(1) if match else bl_folder.name


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AK-5 Subfolder-Schema-Validator (BL-177 INV-QUALITY-7)"
    )
    subparsers = parser.add_subparsers(dest="command")

    check_cmd = subparsers.add_parser("check", help="Check subfolder schema")
    check_cmd.add_argument("--bl", required=True, help="BL-XXX identifier or folder path")
    check_cmd.add_argument(
        "--vault-root",
        default=None,
        help="Vault backlog root (default: inferred from cwd)",
    )
    check_cmd.add_argument(
        "--auto-fix",
        action="store_true",
        help="Apply auto-fix for trivial renames (INV-QUALITY-3: confirmation implied by flag)",
    )
    check_cmd.add_argument("--json", action="store_true", help="Output JSON")

    args = parser.parse_args(argv)

    if args.command == "check":
        # Resolve BL folder
        bl_arg: str = args.bl
        if os.path.isdir(bl_arg):
            bl_folder = Path(bl_arg)
        else:
            # Search vault root
            vault_root = Path(args.vault_root) if args.vault_root else _find_vault_root()
            bl_folder = _find_bl_folder(vault_root, bl_arg)
            if bl_folder is None:
                print(f"ERROR: Cannot find folder for '{bl_arg}' in {vault_root}", file=sys.stderr)
                return 2

        bl_id = _extract_bl_id(bl_folder)
        result = run_checks(bl_folder, bl_id, auto_fix=args.auto_fix)

        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            _print_result(result)

        return result.exit_code
    else:
        parser.print_help()
        return 0


def _find_vault_root() -> Path:
    """Try to find vault backlog root from common locations."""
    candidates = [
        Path("C:/Users/Administrator/Documents/OmniCommand/Backlog"),
        Path.cwd() / "Backlog",
        Path.cwd().parent / "Backlog",
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path.cwd()


def _find_bl_folder(vault_root: Path, bl_id: str) -> Path | None:
    """Find BL folder by BL-XXX prefix in vault root."""
    if not vault_root.exists():
        return None
    for child in vault_root.iterdir():
        if child.is_dir() and child.name.startswith(bl_id):
            return child
    return None


def _print_result(result: SubfolderCheckResult) -> None:
    print(f"\n=== Subfolder-Schema-Check: {result.bl_id} ===")
    print(f"Folder: {result.bl_folder}")
    print(f"Status: {result.block_status} (exit_code={result.exit_code})")
    print(f"Findings: {len(result.findings)}")

    if not result.findings:
        print("  [PASS] No issues found.")
        return

    for f in result.findings:
        icon = {"ERROR": "[ERROR]", "WARN": "[WARN]", "INFO": "[INFO]"}.get(f.severity, "[?]")
        print(f"\n  {icon} [{f.check}] {f.folder}")
        print(f"    {f.message}")
        if f.fix_suggestion:
            print(f"    Fix: {f.fix_suggestion}")


if __name__ == "__main__":
    sys.exit(main())
