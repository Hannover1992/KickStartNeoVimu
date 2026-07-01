"""
bdf_bl_dependency_analyzer.py — BL Dependency Analyzer (BL-176 AK-2)

Reads BL-item frontmatter from a Vault, builds an adjacency matrix of open BLs,
detects cycles (Tarjan's SCC), finds orphans, and exposes a CLI.

Usage:
    py -3 bdf_bl_dependency_analyzer.py analyze --vault-root=<path> [--output=matrix.json]
    py -3 bdf_bl_dependency_analyzer.py orphans --vault-root=<path>
    py -3 bdf_bl_dependency_analyzer.py cycles  --vault-root=<path>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CLOSED_STATUSES: Set[str] = {
    "DONE",
    "ARCHIVED",
    "ARCHIVED_ID_REUSED",
    "FREEZE",
    "DEFER",
}

BL_ID_PATTERN = re.compile(r"BL-\d{3,}")
WIKILINK_PATTERN = re.compile(r"\[\[(BL-\d{3,})[^\]]*\]\]")

# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> Dict:
    """Extract YAML frontmatter from a Markdown file as a raw dict.

    Supports only the subset used in BL files:
    - scalar strings/booleans/numbers
    - flat lists (block style or flow style)
    - nested dicts one level deep (for dependency_types)
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    fm_lines: List[str] = []
    for line in lines[1:]:
        if line.strip() == "---":
            break
        fm_lines.append(line)

    result: Dict = {}
    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        # Skip blank / comment lines
        if not line.strip() or line.strip().startswith("#"):
            i += 1
            continue

        # Key: value  (scalar)
        scalar_match = re.match(r"^(\w[\w_-]*):\s*(.+)$", line)
        list_start = re.match(r"^(\w[\w_-]*):\s*\[(.+)\]", line)
        block_list_start = re.match(r"^(\w[\w_-]*):\s*$", line)
        nested_dict_start = re.match(r"^(\w[\w_-]*):\s*$", line)

        if list_start:
            # Flow-style list:  key: [a, b, c]
            key = list_start.group(1)
            items_str = list_start.group(2)
            items = [s.strip().strip("'\"") for s in items_str.split(",") if s.strip()]
            result[key] = items
            i += 1
        elif block_list_start:
            # Could be block list or nested dict — peek ahead
            key = block_list_start.group(1)
            i += 1
            collected_list: List[str] = []
            collected_dict: Dict[str, str] = {}
            while i < len(fm_lines):
                sub = fm_lines[i]
                list_item = re.match(r"^\s+-\s+(.+)$", sub)
                dict_item = re.match(r"^\s+(\w[\w_-]*):\s+(.+)$", sub)
                if list_item:
                    collected_list.append(list_item.group(1).strip().strip("'\""))
                    i += 1
                elif dict_item:
                    collected_dict[dict_item.group(1)] = dict_item.group(2).strip().strip("'\"")
                    i += 1
                else:
                    break
            if collected_list:
                result[key] = collected_list
            elif collected_dict:
                result[key] = collected_dict
            else:
                result[key] = []
        elif scalar_match:
            key = scalar_match.group(1)
            value = scalar_match.group(2).strip().strip("'\"")
            result[key] = value
            i += 1
        else:
            i += 1

    return result


def _extract_wikilinks(text: str) -> List[str]:
    """Return BL-IDs found in [[BL-XXX]] wikilinks in the body (outside frontmatter)."""
    # Strip frontmatter first
    body = text
    if text.startswith("---"):
        end = text.find("---", 3)
        if end != -1:
            body = text[end + 3:]
    return WIKILINK_PATTERN.findall(body)


def _extract_bl_ids_from_string(value: str) -> List[str]:
    """Extract BL-IDs from a free-text string (legacy related_bl field)."""
    return BL_ID_PATTERN.findall(value)


# ---------------------------------------------------------------------------
# BL reading
# ---------------------------------------------------------------------------

def _find_bl_files(vault_root: Path) -> List[Path]:
    """Recursively find all BL-item markdown files in Backlog directory."""
    backlog_dir = vault_root / "Backlog"
    if not backlog_dir.exists():
        return []

    files: List[Path] = []
    for md_file in backlog_dir.rglob("*.md"):
        files.append(md_file)
    return files


def _read_bl_item(path: Path) -> Optional[Dict]:
    """Read a BL markdown file and return a structured record or None."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    fm = _parse_frontmatter(text)
    bl_id = fm.get("bl_id") or fm.get("id")

    # Fallback: infer BL-ID from directory name
    if not bl_id:
        dir_name = path.parent.name
        match = re.match(r"(BL-\d{3,})", dir_name)
        if match:
            bl_id = match.group(1)

    if not bl_id:
        return None

    # Normalise BL-ID
    bl_id = bl_id.strip().upper()
    if not re.match(r"^BL-\d{3,}$", bl_id):
        return None

    status = fm.get("status", "UNKNOWN").upper()

    # --- Dependency extraction (priority order) ---
    deps: List[str] = []
    dep_types: Dict[str, str] = {}

    # 1. Canonical `dependencies:` field
    if "dependencies" in fm:
        raw = fm["dependencies"]
        if isinstance(raw, list):
            deps.extend([d.strip() for d in raw if d.strip()])

    # 2. Legacy `builds_on:` field
    if "builds_on" in fm:
        raw = fm["builds_on"]
        if isinstance(raw, list):
            for d in raw:
                d = d.strip()
                if d and d not in deps:
                    deps.append(d)
                    dep_types[d] = "builds_on"

    # 3. Legacy `related_bl:` string field
    if "related_bl" in fm and not isinstance(fm["related_bl"], list):
        related_ids = _extract_bl_ids_from_string(str(fm["related_bl"]))
        for d in related_ids:
            if d not in deps:
                deps.append(d)
                dep_types[d] = "related"

    # 4. Wikilinks from body (lowest priority)
    wikilink_ids = _extract_wikilinks(text)
    for d in wikilink_ids:
        if d not in deps:
            deps.append(d)
            dep_types[d] = "related"

    # Optional explicit dependency_types overlay
    if "dependency_types" in fm and isinstance(fm["dependency_types"], dict):
        for k, v in fm["dependency_types"].items():
            dep_types[k] = v

    return {
        "bl_id": bl_id,
        "status": status,
        "title": fm.get("title", ""),
        "prio": fm.get("prio", ""),
        "tags": fm.get("tags", []),
        "dependencies": deps,
        "dependency_types": dep_types,
        "path": str(path),
    }


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def analyze(vault_root: str | Path) -> Dict:
    """Build adjacency matrix of all open BLs.

    Returns:
        {
          "nodes": [bl_id, ...],           # all open BL-IDs
          "closed_nodes": [bl_id, ...],    # filtered-out BL-IDs
          "edges": [[src, dst], ...],       # directed edges (src depends on dst)
          "adjacency": {bl_id: [bl_id]},   # adjacency list (src -> deps)
          "matrix": {bl_id: {bl_id: 0|1}}, # full N×N boolean matrix
          "all_items": [{...}, ...],        # raw records for all found BLs
        }
    """
    vault_root = Path(vault_root)
    files = _find_bl_files(vault_root)

    all_items: List[Dict] = []
    for f in files:
        item = _read_bl_item(f)
        if item:
            all_items.append(item)

    # Deduplicate by bl_id (keep first occurrence)
    seen: Set[str] = set()
    unique_items: List[Dict] = []
    for item in all_items:
        if item["bl_id"] not in seen:
            seen.add(item["bl_id"])
            unique_items.append(item)

    open_items = [i for i in unique_items if i["status"] not in CLOSED_STATUSES]
    closed_items = [i for i in unique_items if i["status"] in CLOSED_STATUSES]

    open_ids: Set[str] = {i["bl_id"] for i in open_items}
    nodes = sorted(open_ids)
    closed_nodes = sorted(i["bl_id"] for i in closed_items)

    # Build adjacency list and edge list (only edges where dest is open)
    adjacency: Dict[str, List[str]] = {n: [] for n in nodes}
    edges: List[Tuple[str, str]] = []

    for item in open_items:
        src = item["bl_id"]
        for dst in item["dependencies"]:
            dst = dst.strip().upper()
            if dst in open_ids and dst != src:
                if dst not in adjacency[src]:
                    adjacency[src].append(dst)
                    edges.append((src, dst))

    # Build N×N matrix
    matrix: Dict[str, Dict[str, int]] = {}
    for n in nodes:
        matrix[n] = {m: 0 for m in nodes}
    for src, dst in edges:
        if src in matrix and dst in matrix[src]:
            matrix[src][dst] = 1

    return {
        "nodes": nodes,
        "closed_nodes": closed_nodes,
        "edges": [[s, d] for s, d in edges],
        "adjacency": adjacency,
        "matrix": matrix,
        "all_items": unique_items,
    }


# ---------------------------------------------------------------------------
# Cycle detection — Tarjan's SCC
# ---------------------------------------------------------------------------

def detect_cycles(matrix_result: Dict) -> List[List[str]]:
    """Detect cycles using Tarjan's strongly-connected-components algorithm.

    Args:
        matrix_result: Result dict from analyze()

    Returns:
        List of SCCs with more than one node (or self-loops), each as a sorted list of BL-IDs.
        Empty list means no cycles.
    """
    adjacency = matrix_result["adjacency"]
    nodes = matrix_result["nodes"]

    index_counter = [0]
    stack: List[str] = []
    lowlink: Dict[str, int] = {}
    index: Dict[str, int] = {}
    on_stack: Dict[str, bool] = {}
    sccs: List[List[str]] = []

    def strongconnect(v: str) -> None:
        index[v] = index_counter[0]
        lowlink[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack[v] = True

        for w in adjacency.get(v, []):
            if w not in index:
                strongconnect(w)
                lowlink[v] = min(lowlink[v], lowlink[w])
            elif on_stack.get(w, False):
                lowlink[v] = min(lowlink[v], index[w])

        if lowlink[v] == index[v]:
            scc: List[str] = []
            while True:
                w = stack.pop()
                on_stack[w] = False
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1:
                sccs.append(sorted(scc))

    for node in nodes:
        if node not in index:
            strongconnect(node)

    return sccs


# ---------------------------------------------------------------------------
# Orphan detection
# ---------------------------------------------------------------------------

def find_orphans(matrix_result: Dict) -> List[str]:
    """Return BL-IDs that have no incoming or outgoing edges in the open graph.

    Args:
        matrix_result: Result dict from analyze()

    Returns:
        Sorted list of orphan BL-IDs.
    """
    adjacency = matrix_result["adjacency"]
    edges = matrix_result["edges"]
    nodes = matrix_result["nodes"]

    connected: Set[str] = set()
    for src, dst in edges:
        connected.add(src)
        connected.add(dst)

    orphans = sorted(n for n in nodes if n not in connected)
    return orphans


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cmd_analyze(args: argparse.Namespace) -> None:
    vault_root = Path(args.vault_root)
    if not vault_root.exists():
        print(f"ERROR: vault-root does not exist: {vault_root}", file=sys.stderr)
        sys.exit(1)

    result = analyze(vault_root)

    # Add cycle and orphan info
    cycles = detect_cycles(result)
    orphans = find_orphans(result)

    summary = {
        "nodes_count": len(result["nodes"]),
        "closed_nodes_count": len(result["closed_nodes"]),
        "edges_count": len(result["edges"]),
        "cycles": cycles,
        "cycles_count": len(cycles),
        "orphans": orphans,
        "orphans_count": len(orphans),
    }

    output = {
        "summary": summary,
        "nodes": result["nodes"],
        "adjacency": result["adjacency"],
        "edges": result["edges"],
    }

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"Matrix written to: {out_path}")
    else:
        print(json.dumps(output, indent=2))

    if cycles:
        print(f"\nWARNING: {len(cycles)} cycle(s) detected — INV-BDF-DEP-1 VIOLATED",
              file=sys.stderr)
        for cycle in cycles:
            print(f"  Cycle: {' -> '.join(cycle)}", file=sys.stderr)


def _cmd_orphans(args: argparse.Namespace) -> None:
    vault_root = Path(args.vault_root)
    result = analyze(vault_root)
    orphans = find_orphans(result)
    print(f"Orphans ({len(orphans)}):")
    for o in orphans:
        print(f"  {o}")


def _cmd_cycles(args: argparse.Namespace) -> None:
    vault_root = Path(args.vault_root)
    result = analyze(vault_root)
    cycles = detect_cycles(result)
    if not cycles:
        print("No cycles detected.")
    else:
        print(f"{len(cycles)} cycle(s) detected:")
        for cycle in cycles:
            print(f"  {' -> '.join(cycle)}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="BL Dependency Analyzer (BL-176 AK-2)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # analyze subcommand
    analyze_parser = subparsers.add_parser("analyze", help="Build full adjacency matrix")
    analyze_parser.add_argument("--vault-root", required=True,
                                help="Path to the OmniCommand Vault root")
    analyze_parser.add_argument("--output", default=None,
                                help="Write JSON result to this file path")

    # orphans subcommand
    orphans_parser = subparsers.add_parser("orphans", help="List orphan BL nodes")
    orphans_parser.add_argument("--vault-root", required=True)

    # cycles subcommand
    cycles_parser = subparsers.add_parser("cycles", help="Detect dependency cycles")
    cycles_parser.add_argument("--vault-root", required=True)

    args = parser.parse_args()

    if args.command == "analyze":
        _cmd_analyze(args)
    elif args.command == "orphans":
        _cmd_orphans(args)
    elif args.command == "cycles":
        _cmd_cycles(args)


if __name__ == "__main__":
    main()
