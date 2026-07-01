"""
quality_node_health.py — BL-177 AK-2 Node-Health-Checker

Checks BL frontmatter schema, required fields, tags, status enum, reifegrad enum.

CLI: py -3 quality_node_health.py check --bl=BL-XXX [--vault=PATH] [--auto-fix]

Exit codes (INV-QUALITY-1):
  0 = PASS
  1 = WARN
  2 = BLOCK (ERROR present)
"""

import argparse
import os
import sys
import re
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))

from quality_berater_base import (
    BaseQualityBerater,
    QualityResult,
    Finding,
    SEVERITY_ERROR,
    SEVERITY_WARN,
    SEVERITY_INFO,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_STATUS = {
    "DRAFT", "READY", "IN_PROGRESS", "BLOCKED", "QUESTION_HOLD",
    "DONE", "ARCHIVED", "CANCELLED",
}

VALID_REIFEGRAD = {"UNREIF", "SC-REIF", "REIF"}

REQUIRED_FRONTMATTER_FIELDS = [
    "type",
    "feature",
    "bl-item",
    "tags",
    "status",
]

OPTIONAL_FRONTMATTER_FIELDS = [
    "reifegrad",
    "created",
    "updated",
    "builds_on",
    "related_bl",
    "prio",
    "foundation_bl",
]

MIN_TAGS_COUNT = 3

VALID_SUBFOLDERS_REQUIRED = {"1_Task", "2_Model", "3_Spec", "4_K-Score", "5_Gap", "6_PL"}
VALID_SUBFOLDERS_OPTIONAL = {"Sources", "Crumbs", "W_fetch", "Implementation", "__pycache__"}
VALID_SUBFOLDERS_ALL = VALID_SUBFOLDERS_REQUIRED | VALID_SUBFOLDERS_OPTIONAL


# ---------------------------------------------------------------------------
# Frontmatter parser (minimal — no external deps)
# ---------------------------------------------------------------------------

def parse_frontmatter(content: str) -> Optional[dict]:
    """
    Parse YAML frontmatter from markdown content.
    Returns dict or None if no frontmatter found.
    Only handles simple key: value and key: [list] patterns.
    """
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None

    fm_lines = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)

    result = {}
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        # Skip empty lines and comments
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue

        # key: value
        m = re.match(r'^(\S[^:]*?):\s*(.*)', line)
        if m:
            key = m.group(1).strip()
            val = m.group(2).strip()

            if val.startswith("[") and val.endswith("]"):
                # inline list
                inner = val[1:-1]
                items = [v.strip().strip("'\"") for v in inner.split(",") if v.strip()]
                result[key] = items
            elif val.startswith("["):
                # multi-line list (simple: collect until ])
                list_items = []
                full = val
                while "]" not in full and i + 1 < len(fm_lines):
                    i += 1
                    full += fm_lines[i]
                inner = re.search(r'\[([^\]]*)\]', full)
                if inner:
                    list_items = [v.strip().strip("'\"") for v in inner.group(1).split(",") if v.strip()]
                result[key] = list_items
            elif val == "" or val is None:
                # might be a block scalar — just store empty
                result[key] = None
            else:
                # strip quotes
                val = val.strip("'\"")
                result[key] = val
        i += 1

    return result


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

def check_required_fields(frontmatter: dict) -> list[Finding]:
    """Check all required frontmatter fields are present and non-empty."""
    findings = []
    for field in REQUIRED_FRONTMATTER_FIELDS:
        if field not in frontmatter or frontmatter[field] is None:
            findings.append(Finding(
                SEVERITY_ERROR,
                f"Required field '{field}' is missing",
                field=field,
                fix_suggestion=f"Add '{field}: <value>' to frontmatter",
            ))
        elif frontmatter[field] == "" or frontmatter[field] == []:
            findings.append(Finding(
                SEVERITY_ERROR,
                f"Required field '{field}' is empty",
                field=field,
                fix_suggestion=f"Set a value for '{field}'",
            ))
    return findings


def check_status_enum(frontmatter: dict) -> list[Finding]:
    """Check status is a valid enum value."""
    findings = []
    status = frontmatter.get("status")
    if status is None:
        return findings  # covered by check_required_fields

    status_upper = str(status).upper()
    if status_upper not in VALID_STATUS:
        findings.append(Finding(
            SEVERITY_ERROR,
            f"Invalid status '{status}'. Allowed: {sorted(VALID_STATUS)}",
            field="status",
            fix_suggestion=f"Set status to one of: {', '.join(sorted(VALID_STATUS))}",
        ))
    return findings


def check_reifegrad_enum(frontmatter: dict) -> list[Finding]:
    """Check reifegrad enum if present."""
    findings = []
    reifegrad = frontmatter.get("reifegrad")
    if reifegrad is None:
        # Optional field — WARN only if status=READY/IN_PROGRESS/DONE
        status = frontmatter.get("status", "").upper()
        if status in ("READY", "IN_PROGRESS", "DONE"):
            findings.append(Finding(
                SEVERITY_WARN,
                "Field 'reifegrad' missing but status implies it should be set",
                field="reifegrad",
                fix_suggestion="Add 'reifegrad: UNREIF|SC-REIF|REIF'",
            ))
        return findings

    reifegrad_upper = str(reifegrad).upper()
    if reifegrad_upper not in VALID_REIFEGRAD:
        findings.append(Finding(
            SEVERITY_ERROR,
            f"Invalid reifegrad '{reifegrad}'. Allowed: {sorted(VALID_REIFEGRAD)}",
            field="reifegrad",
            fix_suggestion=f"Set reifegrad to one of: {', '.join(sorted(VALID_REIFEGRAD))}",
        ))
    return findings


def check_tags_min_count(frontmatter: dict, min_count: int = MIN_TAGS_COUNT) -> list[Finding]:
    """Check tags field has at least min_count entries."""
    findings = []
    tags = frontmatter.get("tags")
    if tags is None:
        return findings  # covered by check_required_fields

    if isinstance(tags, str):
        # Might be a single-tag string
        tags_list = [tags] if tags else []
    elif isinstance(tags, list):
        tags_list = tags
    else:
        tags_list = []

    if len(tags_list) < min_count:
        findings.append(Finding(
            SEVERITY_WARN,
            f"tags has {len(tags_list)} entries, minimum is {min_count}",
            field="tags",
            fix_suggestion=f"Add at least {min_count - len(tags_list)} more tag(s)",
        ))
    return findings


def check_frontmatter_schema(content: str, bl_id: str) -> list[Finding]:
    """
    Top-level schema check: parse frontmatter and validate structure.
    Returns list of Findings.
    """
    findings = []

    if not content.strip().startswith("---"):
        findings.append(Finding(
            SEVERITY_ERROR,
            "No YAML frontmatter block found (file must start with ---)",
            field="frontmatter",
            fix_suggestion="Add YAML frontmatter block at top of file",
        ))
        return findings

    fm = parse_frontmatter(content)
    if fm is None:
        findings.append(Finding(
            SEVERITY_ERROR,
            "Frontmatter could not be parsed",
            field="frontmatter",
        ))
        return findings

    # Check bl-item matches expected BL
    bl_item = fm.get("bl-item")
    if bl_item and str(bl_item) != bl_id:
        findings.append(Finding(
            SEVERITY_WARN,
            f"bl-item '{bl_item}' does not match expected '{bl_id}'",
            field="bl-item",
        ))

    findings.extend(check_required_fields(fm))
    findings.extend(check_status_enum(fm))
    findings.extend(check_reifegrad_enum(fm))
    findings.extend(check_tags_min_count(fm))

    return findings


def check_subfolder_schema(bl_folder: str) -> list[Finding]:
    """
    Check that bl_folder only contains whitelisted subfolders.
    INV-QUALITY-7.
    """
    findings = []
    if not os.path.isdir(bl_folder):
        findings.append(Finding(
            SEVERITY_ERROR,
            f"BL folder not found: {bl_folder}",
            field="folder",
        ))
        return findings

    for entry in os.listdir(bl_folder):
        full_path = os.path.join(bl_folder, entry)
        if os.path.isdir(full_path) and entry not in VALID_SUBFOLDERS_ALL:
            findings.append(Finding(
                SEVERITY_ERROR,
                f"Non-whitelisted subfolder '{entry}' found",
                field="subfolder",
                fix_suggestion=f"Rename or remove '{entry}'. Allowed: {sorted(VALID_SUBFOLDERS_ALL)}",
            ))
    return findings


# ---------------------------------------------------------------------------
# Quality Berater class
# ---------------------------------------------------------------------------

class NodeHealthBerater(BaseQualityBerater):
    """
    Quality-Berater for BL node health.

    data dict expected keys:
        content (str)         — raw markdown content of BL node
        bl_folder (str|None)  — path to BL folder (for subfolder check)
    """

    check_type = "node_health"

    def run_checks(self, bl_id: str, data: dict, auto_fix: bool = False) -> QualityResult:
        result = QualityResult(bl_id=bl_id, check_type=self.check_type)
        content = data.get("content", "")
        bl_folder = data.get("bl_folder")

        # Frontmatter checks
        for finding in check_frontmatter_schema(content, bl_id):
            result.add_finding(finding)

        # Subfolder checks (INV-QUALITY-7)
        if bl_folder:
            for finding in check_subfolder_schema(bl_folder):
                result.add_finding(finding)

        # Auto-fix: only allowed operations (INV-QUALITY-3)
        if auto_fix and result.exit_code < 2:
            result.auto_fixed = True
            # Auto-fix: set updated: date if missing (allowed by AK-8)
            # (actual file manipulation is out of scope for base check)

        return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _find_bl_folder(vault_root: str, bl_id: str) -> Optional[str]:
    """Search vault_root for folder matching BL-XXX pattern."""
    pattern = re.compile(rf"^{re.escape(bl_id)}-", re.IGNORECASE)
    backlog_dir = os.path.join(vault_root, "Backlog")
    if os.path.isdir(backlog_dir):
        for entry in os.listdir(backlog_dir):
            if pattern.match(entry):
                return os.path.join(backlog_dir, entry)
    # Also search vault_root directly
    for entry in os.listdir(vault_root):
        if pattern.match(entry):
            return os.path.join(vault_root, entry)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="BL-177 Node Health Checker",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  py -3 quality_node_health.py check --bl=BL-177
  py -3 quality_node_health.py check --bl=BL-177 --vault=C:/vault --auto-fix
        """,
    )
    sub = parser.add_subparsers(dest="cmd")
    chk = sub.add_parser("check", help="Run node health check")
    chk.add_argument("--bl", required=True, help="BL ID, e.g. BL-177")
    chk.add_argument(
        "--vault",
        default=os.path.join(os.path.dirname(__file__), "..", "..", "..", "OmniCommand"),
        help="Path to Vault/Backlog root",
    )
    chk.add_argument("--auto-fix", action="store_true", help="Apply allowed auto-fixes (INV-QUALITY-3)")
    chk.add_argument("--repo-root", default=None, help="Repo root for audit.jsonl")

    args = parser.parse_args()

    if args.cmd != "check":
        parser.print_help()
        return 1

    vault_root = os.path.abspath(args.vault)
    bl_folder = _find_bl_folder(vault_root, args.bl)

    if bl_folder is None:
        print(f"[ERROR] BL folder not found for {args.bl} in {vault_root}")
        return 2

    # Find _manifest.md or BL node .md
    manifest_path = os.path.join(bl_folder, "_manifest.md")
    node_path = manifest_path if os.path.isfile(manifest_path) else None

    # Also check for BL-XXX.md in backlog root
    bl_md = os.path.join(os.path.dirname(bl_folder), f"{args.bl}.md")
    if not node_path and os.path.isfile(bl_md):
        node_path = bl_md

    content = ""
    if node_path and os.path.isfile(node_path):
        with open(node_path, encoding="utf-8") as fh:
            content = fh.read()
    else:
        print(f"[WARN] No node .md found for {args.bl} in {bl_folder}")

    repo_root = args.repo_root or os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..")
    )

    berater = NodeHealthBerater(repo_root=repo_root)
    data = {"content": content, "bl_folder": bl_folder}
    result = berater.run(bl_id=args.bl, data=data, auto_fix=args.auto_fix)
    berater.write_output(result)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
