#!/usr/bin/env python3
"""
truth_wikilink_rematerialize.py — BL-451 AC-2a

Re-materializes ## Verwandte Wahrheiten sections in truth-type atom files.
Replaces stale wikilink sections with fresh, path-form links derived from
edges in the atom's frontmatter.  Dangling edges (ziel not resolvable in
the vault) are skipped for the body section.

API:
    build_id_path_map(root) -> dict[str, Path]
    rematerialize(root, apply=False, backup_dir=None) -> dict
    main(argv) -> int
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False

from wikilink_materializer import (
    build_wikilink,
    _split_raw_frontmatter,
    WIKILINK_SECTION_HEADER,
)

# ─── Constants ────────────────────────────────────────────────────────────────

_VERWANDTE_HEADER = WIKILINK_SECTION_HEADER  # "## Verwandte Wahrheiten"


# ─── Core helpers ─────────────────────────────────────────────────────────────


def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from content. Returns {} on failure."""
    if not _HAS_YAML:
        return {}
    if not content.startswith("---"):
        return {}
    end_fm = content.find("\n---", 3)
    if end_fm == -1:
        return {}
    yaml_text = content[3:end_fm].strip()
    try:
        parsed = yaml.safe_load(yaml_text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    return {}


def build_id_path_map(root: Path) -> dict[str, Path]:
    """Return {id: absolute_path} for all truth-type atoms under root."""
    result: dict[str, Path] = {}
    for md_file in root.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            continue
        fm = _parse_frontmatter(content)
        if fm.get("type") != "truth":
            continue
        atom_id = fm.get("id")
        if not atom_id:
            continue
        result[str(atom_id)] = md_file.resolve()
    return result


def _is_verwandte_header(line: str) -> bool:
    """Return True if line is a ## Verwandte Wahrheiten header (exact or variant).

    Matches any line whose stripped form starts with '## Verwandte Wahrheiten'
    (prefix-match), catching variants like '## Verwandte Wahrheiten / Links'.
    """
    return line.rstrip("\r\n").startswith(_VERWANDTE_HEADER)


def _remove_verwandte_section(body: str) -> str:
    """Remove ALL ## Verwandte Wahrheiten sections (exact and variant headers)
    and everything up to the next top-level ## header that is NOT itself a
    Verwandte header (or end of body).  Loops until no such section remains
    (handles duplicate accumulation and variant headers).

    Only operates on body — frontmatter is never passed here.
    """
    # Fast-path: no Verwandte header anywhere in body
    if _VERWANDTE_HEADER not in body:
        return body

    # Loop until stable (each pass removes at most one section; duplicates need
    # multiple passes, variants may appear anywhere)
    while True:
        lines = body.splitlines(keepends=True)
        header_idx: int | None = None
        for i, line in enumerate(lines):
            if _is_verwandte_header(line):
                header_idx = i
                break

        if header_idx is None:
            # No more matching headers — done
            break

        # Find next top-level ## header that is NOT a Verwandte header
        end_idx = len(lines)
        for i in range(header_idx + 1, len(lines)):
            stripped = lines[i].rstrip("\r\n")
            if stripped.startswith("## ") and not _is_verwandte_header(lines[i]):
                end_idx = i
                break

        # Remove the Verwandte section (header + its content lines)
        body = "".join(lines[:header_idx] + lines[end_idx:])

    return body


def _rebuild_raw_frontmatter(raw_fm: str, fm_dict: dict, resolvable_edges: list[dict]) -> str:
    """Rebuild raw frontmatter, replacing the edges block with only resolvable edges.

    Preserves all other fields byte-for-byte.  If resolvable_edges is empty,
    the edges field is set to an empty list (edges: []).

    Args:
        raw_fm:            Original raw frontmatter block (including --- delimiters).
        fm_dict:           Parsed frontmatter dict (for context, not for serialization).
        resolvable_edges:  Only the edges whose ziel resolved in the id_path map.

    Returns:
        Updated raw frontmatter string.
    """
    lines = raw_fm.splitlines(keepends=True)

    # Find the "edges:" key line
    edges_start: int = -1
    for i, line in enumerate(lines):
        stripped = line.rstrip("\r\n")
        if stripped == "edges:" or stripped.startswith("edges:"):
            edges_start = i
            break

    if edges_start == -1:
        # No edges field — nothing to change
        return raw_fm

    # Find the extent of the edges block (all list-item lines after the key)
    edges_end = edges_start + 1
    while edges_end < len(lines):
        stripped = lines[edges_end].rstrip("\r\n")
        # Continuation: indented list item or blank line within the block
        if stripped.startswith("  ") or stripped.startswith("\t"):
            edges_end += 1
        else:
            break

    # Build replacement block
    if resolvable_edges:
        new_edge_lines: list[str] = ["edges:\n"]
        for edge in resolvable_edges:
            first = True
            for k, v in edge.items():
                prefix = "  - " if first else "    "
                new_edge_lines.append(f"{prefix}{k}: {v}\n")
                first = False
        replacement = new_edge_lines
    else:
        replacement = ["edges: []\n"]

    lines = lines[:edges_start] + replacement + lines[edges_end:]
    return "".join(lines)


def rematerialize(
    root: Path,
    apply: bool = False,
    backup_dir: Path | None = None,
) -> dict:
    """Re-materialize ## Verwandte Wahrheiten sections for all truth atoms.

    Dangling edges (ziel not found in vault) are removed from the frontmatter
    edges list and produce no wikilink in the body section.

    Args:
        root:       Vault root to scan recursively.
        apply:      If True, write changes to disk. If False, dry-run only.
        backup_dir: If given and apply=True, copy each changed file here before
                    overwriting.

    Returns:
        dict with keys: scanned, with_edges, would_update, updated, backed_up
    """
    counts = {
        "scanned": 0,
        "with_edges": 0,
        "would_update": 0,
        "updated": 0,
        "backed_up": 0,
    }

    # Phase 1: build the id→path map
    id_path = build_id_path_map(root)
    root_abs = root.resolve()

    # Phase 2: iterate all truth atoms
    for md_file in root.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8")
        except OSError:
            continue

        fm = _parse_frontmatter(content)
        if fm.get("type") != "truth":
            continue
        atom_id = fm.get("id")
        if not atom_id:
            continue

        counts["scanned"] += 1

        # Parse edges from frontmatter
        raw_edges = fm.get("edges") or []
        if not isinstance(raw_edges, list):
            raw_edges = []

        if raw_edges:
            counts["with_edges"] += 1

        # Separate resolvable from dangling edges
        resolvable_edges: list[dict] = []
        for edge in raw_edges:
            if not isinstance(edge, dict):
                continue
            ziel = edge.get("ziel")
            if not ziel:
                continue
            if str(ziel) in id_path:
                resolvable_edges.append(edge)
            # else: dangling — skip (don't add to resolvable)

        # Split content into raw_fm + body — raw_fm is NEVER modified
        raw_fm, body = _split_raw_frontmatter(content)

        # Build desired body section lines (path-form, deduped, stable order)
        # Only resolvable edges produce links; dangling edges stay in raw_fm untouched.
        seen_links: set[str] = set()
        desired_lines: list[str] = []
        for edge in resolvable_edges:
            ziel = str(edge.get("ziel", ""))
            target_path = id_path[ziel]
            label = ziel.split(".")[-1]
            link_str = "- Verwandt: " + build_wikilink(target_path, root_abs, label)
            if link_str in seen_links:
                continue
            seen_links.add(link_str)
            desired_lines.append(link_str)

        # Remove existing Verwandte section from body (if any)
        new_body = _remove_verwandte_section(body)

        # Append new section if there are resolvable edges
        if desired_lines:
            new_body = new_body.rstrip("\n") + "\n\n" + _VERWANDTE_HEADER + "\n"
            new_body += "\n".join(desired_lines) + "\n"
        # else: no resolvable edges → section stays removed (orphan-cleanup)

        # raw_fm is prepended byte-identically — never rebuilt/modified
        new_content = raw_fm + new_body

        if new_content == content:
            # Already up-to-date — idempotent skip
            continue

        counts["would_update"] += 1

        if apply:
            if backup_dir is not None:
                backup_dir = Path(backup_dir)
                backup_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(md_file, backup_dir / md_file.name)
                counts["backed_up"] += 1

            md_file.write_text(new_content, encoding="utf-8")
            counts["updated"] += 1

    return counts


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Re-materialize ## Verwandte Wahrheiten sections in truth atoms."
    )
    parser.add_argument("root", help="Vault root to scan recursively")
    parser.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Write changes to disk (default: dry-run)",
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        help="Directory to copy changed files before overwriting",
    )
    args = parser.parse_args(argv)

    root = Path(args.root)
    backup_dir = Path(args.backup_dir) if args.backup_dir else None

    counts = rematerialize(root, apply=args.apply, backup_dir=backup_dir)
    print(
        f"[truth_wikilink_rematerialize] "
        f"scanned={counts['scanned']} "
        f"with_edges={counts['with_edges']} "
        f"would_update={counts['would_update']} "
        f"updated={counts['updated']} "
        f"backed_up={counts['backed_up']} "
        f"apply={args.apply}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
