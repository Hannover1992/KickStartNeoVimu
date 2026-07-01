#!/usr/bin/env python3
"""
view_backref_index.py — atom->views backward mapping (BL-491 AC-2, ARTIFACT 2).

Builds the index Lane C will consume to WRITE atom-side `referenced_by`. Enumerates
VIEW nodes (view_node_predicate.is_view_node), reads each view's frontmatter +
`source_atoms`, and maps every referenced atom to the views that name it. Each backref
carries the resolved view-id (view_id_convention.resolve_view_id) — a frontmatter `id`
when present, else the path-derived `view::` id — so id-less views become nameable.

FENCE — VIEWS-ONLY: this tool NEVER creates, opens-for-write, or modifies any atom
file. It reads VIEW files and may `stat` an atom path (to flag unresolved) only.
Reuses the YAML-first, block-sequence-tolerant frontmatter parsing style of
view_source_atoms_materialize.py.

Public API:
    build_view_backref_index(vault) -> dict
    main(argv=None) -> int
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    import yaml  # PyYAML (available); robustly parses block-sequence frontmatter
except ImportError:  # pragma: no cover - line-scan fallback covers absence
    yaml = None  # type: ignore[assignment]

SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from view_id_convention import resolve_view_id  # noqa: E402
from view_node_predicate import is_view_node  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────────
# Frontmatter parsing (VIEW files only — YAML-first, tolerant of the real-vault
# UNINDENTED block-sequence `source_atoms` form; mirrors view_source_atoms_materialize)
# ──────────────────────────────────────────────────────────────────────────────
def _read_frontmatter_text(view_path) -> str:
    """Raw YAML frontmatter block (between the first two `---`), else "" when no
    well-formed frontmatter is present / file unreadable."""
    try:
        content = Path(view_path).read_text(encoding="utf-8")
    except OSError:
        return ""
    if not content.startswith("---"):
        return ""
    end = content.find("\n---", 3)
    if end == -1:
        return ""
    return content[3:end]


def _line_scan_parse(fm_text: str):
    """Fallback parser (YAML unavailable): extract `id` scalar + `source_atoms`
    items, accepting block sequences at ANY indentation (incl. column 0) and a
    single inline flow list."""
    fm: dict = {}
    source_atoms: list[str] = []
    lines = fm_text.splitlines()
    i, n = 0, len(lines)
    while i < n:
        stripped = lines[i].strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if stripped.startswith("id:"):
            val = stripped[len("id:"):].strip().strip("'\"")
            if val and val not in ("null", "~"):
                fm["id"] = val
            i += 1
            continue
        if stripped == "source_atoms:" or stripped.startswith("source_atoms:"):
            inline = stripped[len("source_atoms:"):].strip()
            if inline:
                if inline.startswith("[") and inline.endswith("]"):
                    inner = inline[1:-1].strip()
                    if inner:
                        source_atoms.extend(
                            x.strip().strip("'\"") for x in inner.split(",") if x.strip()
                        )
                i += 1
                continue
            i += 1
            while i < n:
                ns = lines[i].strip()
                if not ns:
                    i += 1
                    continue
                if ns.startswith("- "):
                    source_atoms.append(ns[2:].strip().strip("'\""))
                    i += 1
                    continue
                break
            continue
        i += 1
    return fm, source_atoms


def _parse_view(view_path):
    """Return (fm_dict, source_atoms_list) for a VIEW file. Tolerant: malformed /
    missing frontmatter -> ({}, []). source_atoms entries are kept as strings."""
    fm_text = _read_frontmatter_text(view_path)
    if not fm_text:
        return {}, []

    if yaml is not None:
        try:
            data = yaml.safe_load(fm_text)
        except Exception:
            data = None
        if isinstance(data, dict):
            sa = data.get("source_atoms")
            source_atoms = (
                [str(x) for x in sa if isinstance(x, str)]
                if isinstance(sa, list)
                else []
            )
            return data, source_atoms

    return _line_scan_parse(fm_text)


# ──────────────────────────────────────────────────────────────────────────────
# Index build
# ──────────────────────────────────────────────────────────────────────────────
def build_view_backref_index(vault: Path) -> dict:
    """Build the atom->views backward index over all VIEW nodes under `vault`.

    For each view node and each `atom_rel` in its `source_atoms`:
        vid = resolve_view_id(fm, view_rel)
        backrefs[atom_rel] += {"by": vid, "kind": "view_source", "view_rel": view_rel}
    Identical (by, atom_rel) pairs are deduped (first kept). `atom_rel` is passed
    through verbatim with backslashes normalized to "/"; an atom path that does not
    exist under `vault` is recorded in `unresolved` (a `stat` only — atom files are
    NEVER opened/written). Lists + keys are sorted for determinism.

    Returns dict with keys: vault, backrefs, view_count, edge_count, atom_count,
    unresolved.
    """
    vault = Path(vault)

    backrefs: dict[str, list[dict]] = {}
    seen_pairs: set[tuple[str, str]] = set()
    unresolved_seen: set[tuple[str, str]] = set()
    unresolved: list[dict] = []
    view_count = 0

    views = sorted(
        p for p in vault.rglob("*.md") if is_view_node(str(p), str(vault))
    )

    for view in views:
        fm, source_atoms = _parse_view(view)
        if not source_atoms:
            continue
        view_count += 1
        view_rel = view.relative_to(vault).as_posix()
        vid = resolve_view_id(fm, view_rel)

        for raw_atom in source_atoms:
            atom_rel = str(raw_atom).replace("\\", "/")

            pair = (vid, atom_rel)
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                backrefs.setdefault(atom_rel, []).append(
                    {"by": vid, "kind": "view_source", "view_rel": view_rel}
                )

            # stat-only existence check (never opens the atom)
            if not (vault / atom_rel).exists():
                ukey = (view_rel, atom_rel)
                if ukey not in unresolved_seen:
                    unresolved_seen.add(ukey)
                    unresolved.append({"view_rel": view_rel, "atom_rel": atom_rel})

    # Determinism: sort each backref list, then sort the keys.
    for entries in backrefs.values():
        entries.sort(key=lambda e: (e["by"], e["view_rel"]))
    backrefs = {k: backrefs[k] for k in sorted(backrefs)}
    unresolved.sort(key=lambda u: (u["view_rel"], u["atom_rel"]))

    edge_count = sum(len(v) for v in backrefs.values())

    return {
        "vault": str(vault),
        "backrefs": backrefs,
        "view_count": view_count,
        "edge_count": edge_count,
        "atom_count": len(backrefs),
        "unresolved": unresolved,
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the atom->views backward index over VIEW nodes "
        "(BL-491 AC-2). VIEWS-ONLY: never touches atom files."
    )
    parser.add_argument("--vault", required=True, help="Path to vault root")
    parser.add_argument("--out", default=None, help="Write index as JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress summary print")
    args = parser.parse_args(argv)

    vault = Path(args.vault)
    result = build_view_backref_index(vault)

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    if not args.quiet:
        print(
            f"[view_backref_index] vault={result['vault']} "
            f"views={result['view_count']} edges={result['edge_count']} "
            f"atoms={result['atom_count']} unresolved={len(result['unresolved'])}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
