"""
BL-348 Index-Honesty Detection-Core — index_node_drift.py

Functions:
  parse_index_rows(index_text) -> dict[str, dict]
  classify_drift(bl_id, index_status, node_status) -> str | None
  scan_drift(vault_root, read_index_fn, read_done_fn, read_node_fn) -> list[dict]
  main() -> CLI entry point (Guard/Health-Check, exit 0 = clean, exit 1 = drifts found)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Callable, Optional


# ---------------------------------------------------------------------------
# parse_index_rows
# ---------------------------------------------------------------------------

def parse_index_rows(index_text: str) -> dict[str, dict]:
    """Header-aware Markdown table parser.

    Finds the header row that contains columns "BL" and "Status" (case-insensitive),
    builds a column-name -> position map, then extracts status for each BL data row
    using that map (not positional/hardcoded).
    """
    lines = index_text.splitlines()

    header_idx: Optional[int] = None
    col_map: dict[str, int] = {}

    for i, line in enumerate(lines):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        # Remove empty cells from leading/trailing |
        cells = [c for c in cells if c != ""]
        cells_upper = [c.upper() for c in cells]
        # Accept "BL" or any cell starting with "BL" (e.g. "BL-ID") as the BL column
        has_bl_col = any(c == "BL" or c.startswith("BL") for c in cells_upper)
        if has_bl_col and "STATUS" in cells_upper:
            header_idx = i
            # Normalise BL-variant column names (BL, BL-ID, ...) -> "BL" in col_map
            col_map = {}
            for idx, name in enumerate(cells):
                key = name.upper()
                if key != "BL" and key.startswith("BL"):
                    key = "BL"
                col_map[key] = idx
            break

    if header_idx is None or "BL" not in col_map or "STATUS" not in col_map:
        return {}

    bl_col = col_map["BL"]
    status_col = col_map["STATUS"]

    result: dict[str, dict] = {}

    for line in lines[header_idx + 1:]:
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        cells = [c for c in cells if c != ""]
        # Skip separator rows like |---|---|
        if all(re.match(r"^-+$", c) for c in cells):
            continue
        # Must look like a BL row
        if len(cells) <= max(bl_col, status_col):
            continue
        bl_id = cells[bl_col]
        if not re.match(r"^BL-\d+$", bl_id):
            continue
        status = cells[status_col]
        result[bl_id] = {"status": status}

    return result


# ---------------------------------------------------------------------------
# classify_drift
# ---------------------------------------------------------------------------

def _norm_status(s: Optional[str]) -> Optional[str]:
    """Normalise a status string for comparison.

    Strips trailing parenthetical annotations (e.g. "DONE (done)" -> "DONE"),
    strips surrounding whitespace, and upper-cases the result.
    Returns None if the input is None or normalises to empty string.
    """
    if s is None:
        return None
    s2 = re.sub(r"\s*\(.*\)\s*$", "", str(s).strip()).strip().upper()
    return s2 or None


def classify_drift(
    bl_id: str,
    index_status: str,
    node_status: Optional[str],
) -> Optional[str]:
    """Classify drift between index status and node status.

    Priority order:
      1. node_defect  (node is missing/corrupt)
      2. cosmetic     (DEPRECATED <-> DECOMPOSED/ABSORBED)
      3. stale_index  (node=DONE but index!=DONE)
      4. over_optimistic_index (index=DONE but node!=DONE)
      5. None         (in-sync or unclassifiable)
    """
    # Raw normalise (case + whitespace only) — used for node_defect check
    # so that None/NO_STATUS/NULL_BYTES are caught before annotation-stripping.
    node_raw = node_status.strip().upper() if node_status else None

    # 1. node_defect — checked on raw value (None stays None)
    if node_raw is None or node_raw in {"NO_STATUS", "NULL_BYTES", "READ_ERR"}:
        return "node_defect"

    # Normalise both operands (strip parenthetical annotations) for remaining checks
    idx = _norm_status(index_status) or ""
    node = _norm_status(node_status) or ""

    # 2. cosmetic: DEPRECATED <-> DECOMPOSED/ABSORBED
    if idx == "DEPRECATED" and node in {"DECOMPOSED", "ABSORBED"}:
        return "cosmetic"

    # 3. stale_index: node done but index not done
    if node == "DONE" and idx != "DONE":
        return "stale_index"

    # 4. over_optimistic_index: index done but node not done
    if idx == "DONE" and node != "DONE":
        return "over_optimistic_index"

    # 5. in-sync or unclassifiable
    return None


# ---------------------------------------------------------------------------
# scan_drift
# ---------------------------------------------------------------------------

def _default_read_index(vault_root: str) -> str:
    path = os.path.join(vault_root, "_backlog_index.md")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _default_read_done(vault_root: str) -> str:
    path = os.path.join(vault_root, "_backlog_index_done.md")
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _default_read_node(vault_root: str, bl_id: str) -> Optional[str]:
    """Read node frontmatter status from vault BL folder.

    Supports two layouts:
    1. Flat file: {vault_root}/Backlog/{bl_id}-*.md  (primary, BL-348 fix)
    2. Directory: {vault_root}/Backlog/{bl_id}-*/*.md (legacy fallback)
    """
    bl_folder_pattern = re.compile(rf"^{re.escape(bl_id)}[_-]", re.IGNORECASE)
    backlog_dir = os.path.join(vault_root, "Backlog")
    if not os.path.isdir(backlog_dir):
        return None

    def _read_status_from_file(fpath: str) -> Optional[str]:
        try:
            with open(fpath, encoding="utf-8", errors="replace") as f:
                content = f.read(2048)
            if "\x00" in content:
                return "NULL_BYTES"
            m = re.search(r"^status:\s*(\S+)", content, re.MULTILINE)
            if m:
                return m.group(1).strip()
            return "NO_STATUS"
        except OSError:
            return "READ_ERR"

    flat_candidates: list[str] = []
    dir_candidates: list[str] = []

    for entry in os.scandir(backlog_dir):
        if not bl_folder_pattern.match(entry.name):
            continue
        if entry.is_file() and entry.name.endswith(".md"):
            flat_candidates.append(entry.path)
        elif entry.is_dir():
            for fname in os.listdir(entry.path):
                if fname.endswith(".md"):
                    dir_candidates.append(os.path.join(entry.path, fname))

    # Flat files take priority: try each, return first real status found
    for fpath in flat_candidates:
        result = _read_status_from_file(fpath)
        if result not in (None, "NO_STATUS"):
            return result

    # Flat files had no real status — try directory candidates
    for fpath in dir_candidates:
        result = _read_status_from_file(fpath)
        if result is not None:
            return result

    # Return whatever flat files gave us (NO_STATUS or None) before giving up
    for fpath in flat_candidates:
        result = _read_status_from_file(fpath)
        if result is not None:
            return result

    return None


def scan_drift(
    vault_root: str,
    read_index_fn: Optional[Callable] = None,
    read_done_fn: Optional[Callable] = None,
    read_node_fn: Optional[Callable] = None,
) -> list[dict]:
    """Scan for drift between backlog index and node files.

    DI-bar: inject read_index_fn/read_done_fn/read_node_fn for testing.
    Returns list of {bl_id, index_status, node_status, kind} for drifted items only.
    """
    # Resolve readers
    if read_index_fn is None:
        _read_index = lambda: _default_read_index(vault_root)
    else:
        _read_index = read_index_fn

    if read_done_fn is None:
        _read_done = lambda: _default_read_done(vault_root)
    else:
        _read_done = read_done_fn

    if read_node_fn is None:
        _read_node = lambda bl_id: _default_read_node(vault_root, bl_id)
    else:
        _read_node = read_node_fn

    # Parse active and done index rows
    active_rows = parse_index_rows(_read_index())
    done_rows = parse_index_rows(_read_done())

    # Merge: active takes priority over done
    all_rows: dict[str, dict] = {}
    all_rows.update(done_rows)
    all_rows.update(active_rows)

    # Classify each BL
    drifts: list[dict] = []
    for bl_id, meta in all_rows.items():
        index_status = meta.get("status", "")
        node_status = _read_node(bl_id)
        kind = classify_drift(bl_id, index_status, node_status)
        if kind is not None:
            drifts.append({
                "bl_id": bl_id,
                "index_status": index_status,
                "node_status": node_status,
                "kind": kind,
            })

    return drifts


# ---------------------------------------------------------------------------
# main — CLI entry point (Guard / Health-Check)
# ---------------------------------------------------------------------------

_KIND_CHOICES = ("stale_index", "over_optimistic_index", "node_defect", "cosmetic")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for index_node_drift.

    Usage:
      py -3 .claude/scripts/index_node_drift.py <vault_root> [--kind KIND] [--json]

    Exit codes:
      0 — no drifts (or no drifts matching the requested kind filter)
      1 — one or more drifts found
    """
    parser = argparse.ArgumentParser(
        prog="index_node_drift",
        description=(
            "BL-348 Health-Check: scan index vs. node drift in an OmniCommand vault.\n"
            "Exit 0 = clean, exit 1 = drifts found (suitable as pre-commit guard)."
        ),
    )
    parser.add_argument(
        "vault_root",
        help="Absolute path to the vault root (directory containing _backlog_index.md).",
    )
    parser.add_argument(
        "--kind",
        choices=_KIND_CHOICES,
        default=None,
        help=(
            "Filter output to a single drift kind: "
            "stale_index | over_optimistic_index | node_defect | cosmetic. "
            "Default: show all kinds."
        ),
    )
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        default=False,
        help="Emit results as JSON array instead of human-readable report.",
    )

    args = parser.parse_args(argv)
    vault_root: str = args.vault_root
    kind_filter: str | None = args.kind
    as_json: bool = args.as_json

    drifts = scan_drift(vault_root)

    # Apply kind filter
    if kind_filter is not None:
        drifts = [d for d in drifts if d["kind"] == kind_filter]

    if as_json:
        print(json.dumps(drifts, indent=2, ensure_ascii=False))
    else:
        _print_report(drifts, kind_filter)

    return 0 if len(drifts) == 0 else 1


def _print_report(drifts: list[dict], kind_filter: str | None) -> None:
    """Print a human-readable grouped report to stdout."""
    total = len(drifts)

    filter_note = f" (filter: {kind_filter})" if kind_filter else ""
    print(f"=== index_node_drift report{filter_note} ===")
    print(f"Total drifts: {total}")

    if total == 0:
        print("OK — no drift detected.")
        return

    # Group by kind
    groups: dict[str, list[dict]] = {}
    for d in drifts:
        groups.setdefault(d["kind"], []).append(d)

    for kind in _KIND_CHOICES:
        items = groups.get(kind)
        if not items:
            continue
        print(f"\n[{kind}] ({len(items)} items)")
        for item in items:
            bl_id = item["bl_id"]
            idx_s = item["index_status"]
            node_s = item["node_status"] if item["node_status"] is not None else "None"
            print(f"  {bl_id}: index={idx_s} -> node={node_s}")


if __name__ == "__main__":
    sys.exit(main())
