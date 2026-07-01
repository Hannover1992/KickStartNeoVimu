"""
quality_edge_health.py — BL-177 AK-3 Edge-Health-Checker

Checks wikilink resolution, dependency chains, bidirectional consistency.

CLI: py -3 quality_edge_health.py check --bl=BL-XXX [--vault=PATH]
     py -3 quality_edge_health.py broken-edges --vault=PATH

Exit codes (INV-QUALITY-1):
  0 = PASS
  1 = WARN
  2 = BLOCK (unresolvable wikilink = ERROR per OQ-2)
"""

import argparse
import os
import re
import sys
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
from quality_node_health import parse_frontmatter


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WIKILINK_PATTERN = re.compile(r'\[\[([^\]]+)\]\]')
BL_ID_PATTERN = re.compile(r'^BL-\d+', re.IGNORECASE)


# ---------------------------------------------------------------------------
# Vault index builder
# ---------------------------------------------------------------------------

def build_vault_index(vault_root: str) -> dict[str, str]:
    """
    Build {bl_id: folder_path} index from vault Backlog directory.
    Also scans for BL-XXX.md files at vault root level.
    """
    index: dict[str, str] = {}
    backlog_dir = os.path.join(vault_root, "Backlog")

    def _scan_dir(base: str) -> None:
        if not os.path.isdir(base):
            return
        for entry in os.listdir(base):
            full = os.path.join(base, entry)
            # Folder named BL-XXX-*
            if os.path.isdir(full):
                m = BL_ID_PATTERN.match(entry)
                if m:
                    bl_id = entry.split("-")[0] + "-" + entry.split("-")[1]
                    index[bl_id.upper()] = full
            # File named BL-XXX.md
            elif entry.endswith(".md"):
                stem = entry[:-3]
                m = BL_ID_PATTERN.match(stem)
                if m and "-" in stem:
                    parts = stem.split("-")
                    if len(parts) >= 2:
                        bl_id = f"{parts[0]}-{parts[1]}".upper()
                        index[bl_id] = full

    _scan_dir(backlog_dir)
    _scan_dir(vault_root)
    return index


# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------

def extract_wikilinks(content: str) -> list[str]:
    """Extract all [[target]] references from content, return target strings."""
    return WIKILINK_PATTERN.findall(content)


def check_wikilink_resolution(
    content: str,
    bl_id: str,
    vault_index: dict[str, str],
) -> list[Finding]:
    """
    Check that all [[BL-XXX]] wikilinks in content resolve to known BL IDs.
    Non-BL wikilinks (e.g. [[SomePage]]) are skipped.
    Unresolvable [[BL-XXX]] = ERROR (OQ-2 decision).
    """
    findings = []
    links = extract_wikilinks(content)
    bl_links = [lnk for lnk in links if BL_ID_PATTERN.match(lnk.strip())]

    for lnk in bl_links:
        # Extract BL ID from link (e.g. "BL-177 Some Title" → "BL-177")
        raw = lnk.strip()
        m = re.match(r'(BL-\d+)', raw, re.IGNORECASE)
        if not m:
            continue
        ref_id = m.group(1).upper()
        if ref_id == bl_id.upper():
            continue  # self-reference allowed

        if ref_id not in vault_index:
            findings.append(Finding(
                SEVERITY_ERROR,
                f"Wikilink [[{raw}]] cannot be resolved — {ref_id} not found in vault",
                field="wikilink",
                fix_suggestion=f"Create {ref_id} node or remove the link",
            ))
        else:
            findings.append(Finding(
                SEVERITY_INFO,
                f"Wikilink [[{raw}]] resolved OK",
                field="wikilink",
            ))
    return findings


def check_dependencies_exist(
    frontmatter: dict,
    vault_index: dict[str, str],
    bl_id: str,
) -> list[Finding]:
    """
    Check builds_on and related_bl references resolve in vault.
    Missing dep = WARN (not ERROR — dep might be planned but not yet created).
    """
    findings = []
    deps: list[str] = []

    builds_on = frontmatter.get("builds_on") or []
    if isinstance(builds_on, str):
        builds_on = [builds_on]
    deps.extend(builds_on)

    related = frontmatter.get("related_bl") or []
    if isinstance(related, str):
        related = [related]
    deps.extend(related)

    for dep in deps:
        dep_id = str(dep).strip().upper()
        if not dep_id:
            continue
        if dep_id == bl_id.upper():
            continue
        if dep_id not in vault_index:
            findings.append(Finding(
                SEVERITY_WARN,
                f"Dependency '{dep_id}' referenced in builds_on/related_bl but not found in vault",
                field="builds_on",
                fix_suggestion=f"Create {dep_id} node or remove the reference",
            ))
        else:
            findings.append(Finding(
                SEVERITY_INFO,
                f"Dependency {dep_id} resolved OK",
                field="builds_on",
            ))
    return findings


def check_builds_on_chain(frontmatter: dict, bl_id: str) -> list[Finding]:
    """
    INV-QUALITY-5: BLs with needs_a_pipeline=true must have builds_on.
    """
    findings = []
    needs_pipeline = frontmatter.get("needs_a_pipeline")
    if str(needs_pipeline).lower() == "true":
        builds_on = frontmatter.get("builds_on") or []
        if isinstance(builds_on, str):
            builds_on = [builds_on]
        if not builds_on or builds_on == [None] or builds_on == [""]:
            findings.append(Finding(
                SEVERITY_ERROR,
                f"{bl_id} has needs_a_pipeline=true but no builds_on chain (INV-QUALITY-5)",
                field="builds_on",
                fix_suggestion="Add at least one foundation BL to builds_on: []",
            ))
    return findings


def check_bidirectional(
    bl_a_id: str,
    fm_a: dict,
    bl_b_id: str,
    fm_b: dict,
) -> list[Finding]:
    """
    Check bidirectional consistency: if A.blocks contains B, then B.blocked_by should contain A.
    Returns findings with WARN severity (not ERROR — partial metadata is common).
    """
    findings = []

    blocks_a = fm_a.get("blocks") or []
    if isinstance(blocks_a, str):
        blocks_a = [blocks_a]

    blocked_by_b = fm_b.get("blocked_by") or []
    if isinstance(blocked_by_b, str):
        blocked_by_b = [blocked_by_b]

    blocks_a_upper = [str(x).upper() for x in blocks_a]
    blocked_by_b_upper = [str(x).upper() for x in blocked_by_b]

    if bl_b_id.upper() in blocks_a_upper and bl_a_id.upper() not in blocked_by_b_upper:
        findings.append(Finding(
            SEVERITY_WARN,
            f"{bl_a_id}.blocks contains {bl_b_id}, but {bl_b_id}.blocked_by does not contain {bl_a_id}",
            field="blocked_by",
            fix_suggestion=f"Add '{bl_a_id}' to {bl_b_id}.blocked_by: []",
        ))

    return findings


# ---------------------------------------------------------------------------
# Edge Health Berater
# ---------------------------------------------------------------------------

class EdgeHealthBerater(BaseQualityBerater):
    """
    Quality-Berater for BL edge health.

    data dict expected keys:
        content (str)            — raw markdown content
        frontmatter (dict|None)  — parsed frontmatter (or derived from content)
        vault_index (dict)       — {BL-ID: path} from build_vault_index()
    """

    check_type = "edge_health"

    def run_checks(self, bl_id: str, data: dict, auto_fix: bool = False) -> QualityResult:
        result = QualityResult(bl_id=bl_id, check_type=self.check_type)
        content = data.get("content", "")
        vault_index = data.get("vault_index", {})

        fm = data.get("frontmatter")
        if fm is None:
            fm = parse_frontmatter(content) or {}

        # Wikilink resolution
        for f in check_wikilink_resolution(content, bl_id, vault_index):
            # Skip INFO to keep output clean (only errors and warns)
            if f.severity != SEVERITY_INFO:
                result.add_finding(f)

        # Dependency existence
        for f in check_dependencies_exist(fm, vault_index, bl_id):
            if f.severity != SEVERITY_INFO:
                result.add_finding(f)

        # Hebb-chain (INV-QUALITY-5)
        for f in check_builds_on_chain(fm, bl_id):
            result.add_finding(f)

        return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_bl(bl_folder: str, bl_id: str) -> tuple[str, dict]:
    """Load content + frontmatter for a BL from its folder."""
    manifest = os.path.join(bl_folder, "_manifest.md")
    if os.path.isfile(manifest):
        with open(manifest, encoding="utf-8") as fh:
            content = fh.read()
        fm = parse_frontmatter(content) or {}
        return content, fm

    # Fallback: BL-XXX.md in parent
    parent = os.path.dirname(bl_folder)
    node = os.path.join(parent, f"{bl_id}.md")
    if os.path.isfile(node):
        with open(node, encoding="utf-8") as fh:
            content = fh.read()
        fm = parse_frontmatter(content) or {}
        return content, fm

    return "", {}


def cmd_check(args: argparse.Namespace) -> int:
    vault_root = os.path.abspath(args.vault)
    vault_index = build_vault_index(vault_root)

    bl_id = args.bl.upper()
    if bl_id not in vault_index:
        print(f"[ERROR] {bl_id} not found in vault index")
        return 2

    bl_folder = vault_index[bl_id]
    content, fm = _load_bl(bl_folder, bl_id)

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    berater = EdgeHealthBerater(repo_root=repo_root)
    data = {"content": content, "frontmatter": fm, "vault_index": vault_index}
    result = berater.run(bl_id=bl_id, data=data)
    berater.write_output(result)
    return result.exit_code


def cmd_broken_edges(args: argparse.Namespace) -> int:
    """Scan all BLs for broken wikilinks."""
    vault_root = os.path.abspath(args.vault)
    vault_index = build_vault_index(vault_root)
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    broken: list[tuple[str, Finding]] = []
    for bl_id, bl_folder in sorted(vault_index.items()):
        content, fm = _load_bl(bl_folder, bl_id)
        if not content:
            continue
        for f in check_wikilink_resolution(content, bl_id, vault_index):
            if f.severity == SEVERITY_ERROR:
                broken.append((bl_id, f))

    if broken:
        print(f"[REPORT] {len(broken)} broken edge(s) found:")
        for bl_id, f in broken:
            print(f"  {bl_id}: {f.message}")
    else:
        print("[REPORT] No broken edges found.")

    return 2 if broken else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="BL-177 Edge Health Checker")
    sub = parser.add_subparsers(dest="cmd")

    chk = sub.add_parser("check", help="Check single BL edge health")
    chk.add_argument("--bl", required=True)
    chk.add_argument("--vault", default=os.path.join(os.path.dirname(__file__), "..", "..", "..", "OmniCommand"))

    be = sub.add_parser("broken-edges", help="Report all broken edges across vault")
    be.add_argument("--vault", default=os.path.join(os.path.dirname(__file__), "..", "..", "..", "OmniCommand"))

    args = parser.parse_args()
    if args.cmd == "check":
        return cmd_check(args)
    elif args.cmd == "broken-edges":
        return cmd_broken_edges(args)
    else:
        parser.print_help()
        return 1


if __name__ == "__main__":
    sys.exit(main())
