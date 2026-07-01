#!/usr/bin/env python3
"""view_projector.py — BL-478 View-Projection mechanic (STERN-P4).

Re-derives a lost view's content from the BL's surviving clean substrate.
Load-bearing: atom/substrate-grounded or NOT AT ALL — NEVER fabricate.
"""
from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path


# ---------------------------------------------------------------------------
# parse_view_identity
# ---------------------------------------------------------------------------

def parse_view_identity(view_path: str, vault_root: str) -> dict:
    """Return {"bl": <"BL-123" or None>, "view_type": <"parking"|"library"|"unknown">}."""
    # Normalize to forward slashes for cross-platform matching
    normalized = view_path.replace("\\", "/")
    basename = os.path.basename(view_path)

    # Extract BL number from path (first match)
    bl_match = re.search(r"BL-\d+", normalized)
    bl = bl_match.group(0) if bl_match else None

    # Determine view type
    if "/6_PL/" in normalized and basename.endswith("-parking-lot.md"):
        view_type = "parking"
    elif "/Libraries/" in normalized or "PatternLibrary" in normalized:
        view_type = "library"
    else:
        view_type = "unknown"

    return {"bl": bl, "view_type": view_type}


# ---------------------------------------------------------------------------
# gather_substrate
# ---------------------------------------------------------------------------

# Unified pattern for AK/AC criteria lines (all forms, case-insensitive).
# Handles:
#   ### AK-<n>: <title>                          (heading, colon)
#   ### AK-<n> [<tags>] — <title>               (heading, optional tags, em-dash U+2014)
#   ### AK-<n> — <title>                        (heading, em-dash, no tags)
#   - **AK-<n>:** <title>                       (bold bullet, colon inside **)
#   - **AK-<n>** ... — <title>                 (bold bullet, em-dash)
#   - AK-<n>: <title>                           (plain bullet, colon)
# Groups: (1) AK/AC type, (2) id-number/word, (3) title text
_AK_UNIFIED_RE = re.compile(
    r"^\s*(?:#{1,6}\s*|[-*]\s*)?\*?\*?(A[KC])-(\w+)\*?\*?"  # prefix + id (optional bold stars)
    r"(?:[^:—\n]*?)"                                          # optional non-separator content (e.g. trailing **, intermediate text)
    r"\s*(?:\[[^\]]*\])?\s*"                                  # optional [tags] block
    r"[:—]\s*"                                                # separator: colon or em-dash (U+2014)
    r"\*?\*?\s*"                                              # optional leading ** after separator (bold-colon form)
    r"(.+)$",                                                 # title
    re.IGNORECASE,
)
# Keep old names as aliases so any external imports don't break
_AK_HEADING_RE = _AK_UNIFIED_RE
_AK_BULLET_BOLD_COLON_RE = _AK_UNIFIED_RE
_AK_BULLET_BOLD_DASH_RE = _AK_UNIFIED_RE


def _parse_aks_from_text(text: str) -> list[dict]:
    """Extract AK/AC items from text, returning list of {"id": "AK-N", "title": "..."}."""
    aks = []
    seen_ids: set[str] = set()
    for line in text.splitlines():
        m = _AK_UNIFIED_RE.match(line)
        if m:
            n = m.group(2)
            if not any(ch.isdigit() for ch in n) and n.lower() != "dod":
                continue  # header like "AK-Liste"/"AK-Master", not a real AK id
            title = m.group(3).strip()[:100]
            ak_id = f"AK-{n}"
            if ak_id not in seen_ids:
                seen_ids.add(ak_id)
                aks.append({"id": ak_id, "title": title})
    return aks


def _is_corrupt(path: Path) -> bool:
    """Return True if the file contains null bytes."""
    try:
        return path.read_bytes().count(0) > 0
    except OSError:
        return True


def gather_substrate(bl: str, vault_root: str) -> dict:
    """Return {"aks": [...], "atoms": [...], "has_substrate": bool}."""
    vault = Path(vault_root)
    backlog_dir = vault / "Backlog"

    aks: list[dict] = []
    atoms: list[str] = []

    # --- Find the BL directory (e.g. BL-100-x) ---
    bl_dirs: list[Path] = []
    if backlog_dir.exists():
        for d in backlog_dir.iterdir():
            if d.is_dir() and d.name.startswith(f"{bl}-"):
                bl_dirs.append(d)

    # --- AKs: scan 3_Spec/*.md first, then node file ---
    ak_seen_ids: set[str] = set()

    def _add_aks_from_file(p: Path) -> None:
        if _is_corrupt(p):
            return
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return
        for item in _parse_aks_from_text(text):
            if item["id"] not in ak_seen_ids:
                ak_seen_ids.add(item["id"])
                aks.append(item)

    # Spec files
    spec_found = False
    for bl_dir in bl_dirs:
        spec_dir = bl_dir / "3_Spec"
        if spec_dir.exists():
            for spec_file in sorted(spec_dir.glob("*.md")):
                _add_aks_from_file(spec_file)
                spec_found = True

    # If no spec files found, fall back to the BL node file
    if not spec_found and backlog_dir.exists():
        for node_file in backlog_dir.glob(f"{bl}-*.md"):
            _add_aks_from_file(node_file)
        # Also try exact node file like BL-200-y.md
        for node_file in backlog_dir.glob(f"{bl}*.md"):
            if node_file.is_file():
                _add_aks_from_file(node_file)

    # --- Atoms: scan 2_Model/truths/*.md and Model/truths/*.md ---
    atom_paths: list[str] = []
    for bl_dir in bl_dirs:
        for truths_dir in (
            bl_dir / "2_Model" / "truths",
            bl_dir / "Model" / "truths",
        ):
            if truths_dir.exists():
                for atom_file in sorted(truths_dir.glob("*.md")):
                    if _is_corrupt(atom_file):
                        continue
                    # Relative path from vault_root, posix forward-slash
                    try:
                        rel = atom_file.relative_to(vault).as_posix()
                        atom_paths.append(rel)
                    except ValueError:
                        atom_paths.append(atom_file.as_posix())

    atoms = sorted(atom_paths)

    has_substrate = bool(aks) or bool(atoms)
    return {"aks": aks, "atoms": atoms, "has_substrate": has_substrate}


# ---------------------------------------------------------------------------
# project_view
# ---------------------------------------------------------------------------

def project_view(view_path: str, vault_root: str) -> dict:
    """Return {"derivable", "content", "source_components", "loss_note"}."""
    identity = parse_view_identity(view_path, vault_root)
    bl = identity["bl"]
    view_type = identity["view_type"]

    # Cannot handle unknown identity
    if bl is None or view_type == "unknown":
        return {
            "derivable": False,
            "content": None,
            "source_components": [],
            "loss_note": "unrecognized view identity",
        }

    # Library: no projection source
    if view_type == "library":
        return {
            "derivable": False,
            "content": None,
            "source_components": [],
            "loss_note": "library pattern content has no atom/substrate projection source — accepted loss",
        }

    sub = gather_substrate(bl, vault_root)

    if not sub["has_substrate"]:
        return {
            "derivable": False,
            "content": None,
            "source_components": [],
            "loss_note": f"no atom/substrate source for {bl} — accepted loss (original null-byte-lost to BL-443)",
        }

    # parking — derivable
    aks = sub["aks"]
    atoms = sub["atoms"]

    source_components = []
    if aks:
        source_components.append("spec_aks")
    if atoms:
        source_components.append("truth_atoms")

    components_str = ", ".join(source_components)

    # Build frontmatter
    frontmatter_lines = [
        "---",
        "type: parking_lot",
        f"bl-item: {bl}",
        "reconstructed_from_substrate: true",
        "projected_by: view_projector",
        "original_lost_to: BL-443",
        f"source_components: [{components_str}]",
        f"items_total: {len(aks)}",
        "---",
    ]
    frontmatter = "\n".join(frontmatter_lines)

    # Build body
    body_lines = [
        f"# PL Master — {bl}",
        "",
        "Re-projiziert aus Substrat (view_projector, BL-478). Original null-byte-verloren (BL-443). Atom-fundiert, nicht halluziniert.",
        "",
        "## Items",
    ]

    if aks:
        for ak in aks:
            body_lines.append(f"- [ ] **{bl}-{ak['id']}-PL-1** (status: open) — {ak['title']}")
    else:
        body_lines.append("- (keine AK-Quelle erhalten — Items nicht re-derivierbar, akzeptierter Teil-Verlust)")

    if atoms:
        body_lines.append("")
        body_lines.append("## Verwandte Wahrheiten")
        for atom_path in atoms:
            body_lines.append(f"- Verwandt: [[{atom_path}|md]]")
    # else: omit the section entirely

    body = "\n".join(body_lines)
    content = frontmatter + "\n\n" + body

    return {
        "derivable": True,
        "content": content,
        "source_components": source_components,
        "loss_note": None,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="BL-478 view_projector — re-derive a lost parking-lot view from substrate."
    )
    parser.add_argument("view_path", help="Path to the (lost/corrupt) view file")
    parser.add_argument("vault_root", help="Root of the Vault directory")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write projected content back to view_path if derivable",
    )
    args = parser.parse_args()

    result = project_view(args.view_path, args.vault_root)

    if args.write and result["derivable"] and result["content"] is not None:
        Path(args.view_path).write_text(result["content"], encoding="utf-8")
        print(f"Written to {args.view_path}")
    else:
        # Serialize for JSON — replace None with null
        print(json.dumps(result, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
