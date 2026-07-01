"""
quality_hebb_chain.py — AK-6 Hebb-Chain-Verifikation (BL-177)

Checks Fire-Together-Wire-Together integrity in the vault knowledge graph.
INV-QUALITY-5: New BLs must have at least 1 builds_on Foundation reference.
INV-QUALITY-6: Foundation BLs must reference other foundations.

Exit codes:
  0 = PASS
  1 = WARN
  2 = ERROR (at least one error)
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
# Data model
# ---------------------------------------------------------------------------


@dataclass
class HebbFinding:
    severity: str  # ERROR | WARN | INFO
    check: str
    bl_id: str
    message: str
    fix_suggestion: Optional[str] = None


@dataclass
class HebbChainResult:
    bl_id: str
    bl_folder: Path
    findings: list[HebbFinding] = field(default_factory=list)
    block_status: str = "PASS"
    exit_code: int = 0
    hebb_graph_mermaid: str = ""
    completed_at: str = field(default_factory=lambda: datetime.now().isoformat() + "Z")

    def add(self, finding: HebbFinding) -> None:
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
            "check_type": "hebb_chain",
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
            "hebb_graph_mermaid": self.hebb_graph_mermaid,
        }


# ---------------------------------------------------------------------------
# BL node parsing helpers
# ---------------------------------------------------------------------------


def _parse_yaml_list(text: str, key: str) -> list[str]:
    """Extract a YAML list value by key from raw text (simple parser for inline lists)."""
    pattern = rf"^{re.escape(key)}:\s*\[([^\]]*)\]"
    match = re.search(pattern, text, re.MULTILINE)
    if match:
        raw = match.group(1)
        return [v.strip().strip("'\"") for v in raw.split(",") if v.strip()]

    # Block list format
    block_pattern = rf"^{re.escape(key)}:\s*\n((?:\s+-\s+.+\n?)+)"
    match = re.search(block_pattern, text, re.MULTILINE)
    if match:
        lines = match.group(1).strip().splitlines()
        return [line.strip().lstrip("- ").strip("'\"") for line in lines if line.strip()]
    return []


def _parse_yaml_scalar(text: str, key: str) -> Optional[str]:
    """Extract a scalar YAML value by key."""
    match = re.search(rf"^{re.escape(key)}:\s*(.+)$", text, re.MULTILINE)
    if match:
        return match.group(1).strip().strip("'\"")
    return None


def load_bl_node(bl_folder: Path) -> dict:
    """
    Load BL metadata from _manifest.md or the first .md in backlog root.
    Returns a dict with keys: bl_id, builds_on, status, needs_a_pipeline,
    type, foundation_bl, source_provenance, related_bl.
    """
    node: dict = {
        "bl_id": "",
        "builds_on": [],
        "status": "",
        "needs_a_pipeline": False,
        "type": "",
        "foundation_bl": False,
        "source_provenance": None,
        "related_bl": [],
    }

    # Try _manifest.md first
    manifest = bl_folder / "_manifest.md"
    if not manifest.exists():
        # Try BL-XXX.md at parent level
        parent = bl_folder.parent
        bl_match = re.match(r"(BL-\d+)", bl_folder.name)
        if bl_match:
            candidate = parent / f"{bl_match.group(1)}.md"
            if candidate.exists():
                manifest = candidate
            else:
                return node

    text = manifest.read_text(encoding="utf-8", errors="replace")

    node["bl_id"] = _parse_yaml_scalar(text, "bl-item") or bl_folder.name
    node["builds_on"] = _parse_yaml_list(text, "builds_on")
    node["related_bl"] = _parse_yaml_list(text, "related_bl")
    node["status"] = _parse_yaml_scalar(text, "status") or ""
    node["type"] = _parse_yaml_scalar(text, "type") or ""

    pipeline_val = _parse_yaml_scalar(text, "needs_a_pipeline")
    node["needs_a_pipeline"] = pipeline_val in ("true", "True", "yes", "1")

    foundation_val = _parse_yaml_scalar(text, "foundation_bl")
    node["foundation_bl"] = foundation_val in ("true", "True", "yes", "1")

    # source_provenance: just check if field exists
    node["source_provenance"] = _parse_yaml_scalar(text, "source_provenance")

    return node


# ---------------------------------------------------------------------------
# Core checks (AK-6)
# ---------------------------------------------------------------------------


def check_builds_on_min_one(bl_node: dict) -> list[HebbFinding]:
    """
    INV-QUALITY-5: BLs with needs_a_pipeline=true must have min. 1 builds_on reference.
    """
    findings: list[HebbFinding] = []
    if not bl_node.get("needs_a_pipeline"):
        return findings  # Only applies to pipeline BLs

    builds_on = bl_node.get("builds_on", [])
    if not builds_on:
        findings.append(
            HebbFinding(
                severity="ERROR",
                check="builds_on_min_one",
                bl_id=bl_node.get("bl_id", "?"),
                message=(
                    f"BL '{bl_node.get('bl_id')}' has needs_a_pipeline=true but "
                    f"no builds_on references (INV-QUALITY-5). Wissens-Orphan detected."
                ),
                fix_suggestion="Add at least one Foundation BL to builds_on: list in _manifest.md",
            )
        )
    return findings


def check_foundation_done(
    builds_on_refs: list[str],
    vault_root: Path,
    bl_id: str,
) -> list[HebbFinding]:
    """
    Check that Foundation BLs referenced in builds_on are status=DONE.
    Not-done = WARN (Forward-Reference-OK per OQ decision).
    Non-existent = ERROR.
    """
    findings: list[HebbFinding] = []
    for ref in builds_on_refs:
        ref_folder = _find_bl_folder(vault_root, ref)
        if ref_folder is None:
            findings.append(
                HebbFinding(
                    severity="ERROR",
                    check="foundation_exists",
                    bl_id=bl_id,
                    message=f"builds_on reference '{ref}' does not exist in vault.",
                    fix_suggestion=f"Create {ref} or remove from builds_on.",
                )
            )
            continue
        ref_node = load_bl_node(ref_folder)
        if ref_node["status"] not in ("DONE", "ARCHIVIERT", "ARCHIVED_ID_REUSED"):
            findings.append(
                HebbFinding(
                    severity="WARN",
                    check="foundation_done",
                    bl_id=bl_id,
                    message=(
                        f"builds_on reference '{ref}' has status='{ref_node['status']}' "
                        f"(not DONE). Forward-Reference accepted but tracked."
                    ),
                    fix_suggestion=f"Complete {ref} before {bl_id} goes DONE.",
                )
            )
    return findings


def check_w_fetch_anchors_referenced(bl_folder: Path, bl_node: dict) -> list[HebbFinding]:
    """
    W-Fetch anchors listed in W_fetch/*.md must be in builds_on or related_bl.
    """
    findings: list[HebbFinding] = []
    w_fetch_dir = bl_folder / "W_fetch"
    if not w_fetch_dir.exists():
        return findings

    # Parse anker_nodes from W_fetch files
    anchors: set[str] = set()
    for wf in w_fetch_dir.glob("*.md"):
        text = wf.read_text(encoding="utf-8", errors="replace")
        # anker_nodes: [BL-151, BL-160, ...]
        refs = _parse_yaml_list(text, "anker_nodes")
        anchors.update(refs)
        # Also look for inline [[BL-XXX]] references
        for match in re.finditer(r"\[\[BL-(\d+)[^\]]*\]\]", text):
            anchors.add(f"BL-{match.group(1)}")

    if not anchors:
        return findings

    all_refs = set(bl_node.get("builds_on", [])) | set(bl_node.get("related_bl", []))
    for anchor in anchors:
        if anchor not in all_refs:
            findings.append(
                HebbFinding(
                    severity="WARN",
                    check="w_fetch_anchor_referenced",
                    bl_id=bl_node.get("bl_id", "?"),
                    message=(
                        f"W-Fetch anchor '{anchor}' found in W_fetch/ but not in "
                        f"builds_on or related_bl."
                    ),
                    fix_suggestion=f"Add '{anchor}' to builds_on or related_bl in _manifest.md.",
                )
            )
    return findings


def check_source_provenance_chain(bl_node: dict) -> list[HebbFinding]:
    """
    Vault docs with needs_a_pipeline=true must have source_provenance set.
    """
    findings: list[HebbFinding] = []
    if not bl_node.get("needs_a_pipeline"):
        return findings
    if not bl_node.get("source_provenance"):
        findings.append(
            HebbFinding(
                severity="WARN",
                check="source_provenance_chain",
                bl_id=bl_node.get("bl_id", "?"),
                message=(
                    f"BL '{bl_node.get('bl_id')}' has needs_a_pipeline=true but "
                    f"no source_provenance field set."
                ),
                fix_suggestion="Add source_provenance: {{source: ..., source_kind: ..., fetched_at: ISO}} to manifest.",
            )
        )
    return findings


# ---------------------------------------------------------------------------
# Mermaid graph generation
# ---------------------------------------------------------------------------


def generate_hebb_mermaid(
    bl_id: str,
    builds_on: list[str],
    related_bl: list[str],
    vault_root: Optional[Path] = None,
) -> str:
    """Generate a Mermaid flowchart snippet for the Hebb-Chain."""
    lines = ["graph LR"]
    safe_id = bl_id.replace("-", "_")

    for ref in builds_on:
        safe_ref = ref.replace("-", "_")
        lines.append(f"    {safe_ref}([{ref}]) -->|builds_on| {safe_id}([{bl_id}])")

    for ref in related_bl:
        safe_ref = ref.replace("-", "_")
        lines.append(f"    {safe_id} -.->|related| {safe_ref}([{ref}])")

    if len(lines) == 1:
        lines.append(f"    {safe_id}([{bl_id}])")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_checks(
    bl_folder: Path,
    bl_id: str,
    vault_root: Optional[Path] = None,
) -> HebbChainResult:
    result = HebbChainResult(bl_id=bl_id, bl_folder=bl_folder)

    if not bl_folder.exists():
        result.add(
            HebbFinding(
                severity="ERROR",
                check="folder_exists",
                bl_id=bl_id,
                message=f"BL folder '{bl_folder}' does not exist.",
            )
        )
        return result

    bl_node = load_bl_node(bl_folder)
    if not bl_node["bl_id"]:
        bl_node["bl_id"] = bl_id

    if vault_root is None:
        vault_root = bl_folder.parent

    # Check 1: builds_on min 1
    for f in check_builds_on_min_one(bl_node):
        result.add(f)

    # Check 2: foundation done
    for f in check_foundation_done(bl_node.get("builds_on", []), vault_root, bl_id):
        result.add(f)

    # Check 3: W-fetch anchors
    for f in check_w_fetch_anchors_referenced(bl_folder, bl_node):
        result.add(f)

    # Check 4: source provenance
    for f in check_source_provenance_chain(bl_node):
        result.add(f)

    # Generate Hebb graph
    result.hebb_graph_mermaid = generate_hebb_mermaid(
        bl_id,
        bl_node.get("builds_on", []),
        bl_node.get("related_bl", []),
        vault_root,
    )

    return result


def _find_bl_folder(vault_root: Path, bl_id: str) -> Optional[Path]:
    if not vault_root or not vault_root.exists():
        return None
    for child in vault_root.iterdir():
        if child.is_dir() and child.name.startswith(bl_id):
            return child
    # Also check flat BL-XXX.md
    candidate = vault_root / f"{bl_id}.md"
    if candidate.exists():
        return vault_root  # Use vault root as pseudo-folder
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="AK-6 Hebb-Chain-Verifikation (BL-177 INV-QUALITY-5)"
    )
    parser.add_argument("--bl", required=True, help="BL-XXX or path to BL folder")
    parser.add_argument("--vault-root", default=None, help="Vault backlog root")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--mermaid", action="store_true", help="Print Mermaid graph")

    args = parser.parse_args(argv)

    if args.vault_root:
        vault_root = Path(args.vault_root)
    else:
        vault_root = _default_vault_root()

    bl_arg = args.bl
    if Path(bl_arg).is_dir():
        bl_folder = Path(bl_arg)
    else:
        bl_folder = _find_bl_folder(vault_root, bl_arg) or vault_root / bl_arg

    bl_id = re.match(r"(BL-\d+)", bl_folder.name)
    bl_id_str = bl_id.group(1) if bl_id else bl_folder.name

    result = run_checks(bl_folder, bl_id_str, vault_root)

    if args.json:
        print(json.dumps(result.to_dict(), indent=2))
    else:
        _print_result(result, args.mermaid)

    return result.exit_code


def _default_vault_root() -> Path:
    candidates = [
        Path("C:/Users/Administrator/Documents/OmniCommand/Backlog"),
        Path.cwd() / "Backlog",
    ]
    for c in candidates:
        if c.exists():
            return c
    return Path.cwd()


def _print_result(result: HebbChainResult, show_mermaid: bool = False) -> None:
    print(f"\n=== Hebb-Chain-Check: {result.bl_id} ===")
    print(f"Status: {result.block_status} (exit_code={result.exit_code})")
    print(f"Findings: {len(result.findings)}")

    if not result.findings:
        print("  [PASS] No issues.")
    for f in result.findings:
        icon = {"ERROR": "[ERROR]", "WARN": "[WARN]", "INFO": "[INFO]"}.get(f.severity, "[?]")
        print(f"\n  {icon} [{f.check}]")
        print(f"    {f.message}")
        if f.fix_suggestion:
            print(f"    Fix: {f.fix_suggestion}")

    if show_mermaid and result.hebb_graph_mermaid:
        print(f"\n--- Hebb-Graph (Mermaid) ---")
        print(result.hebb_graph_mermaid)


if __name__ == "__main__":
    sys.exit(main())
