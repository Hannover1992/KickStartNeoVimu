#!/usr/bin/env python3
"""
truth_view_backref_materialize.py — view_source referenced_by materializer (BL-491 G3).

Consumes view_backref_index.build_view_backref_index and writes atom-side
referenced_by entries for each view that lists the atom in source_atoms.
Reuses truth_backref_materialize._build_new_content for surgical frontmatter
patching. Idempotent: second run on an already-current vault makes no changes.

Modi:
  apply=False (dry-run): count only, never write (updated=0).
  apply=True:  write. updated = number of actually changed files.
  backup_dir + apply: copy PRE-write file to backup_dir/<atom_rel> before writing.

Return dict keys (all int): views, atoms, would_update, updated, backed_up,
added_backrefs.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import view_backref_index  # noqa: E402
import truth_backref_materialize  # noqa: E402


# ──────────────────────────────────────────────────────────────────────────────
# Frontmatter helper — parse existing referenced_by from an atom file
# ──────────────────────────────────────────────────────────────────────────────

def _parse_current_rb(content: str) -> list[dict]:
    """Return the existing referenced_by list from frontmatter.

    Parses via yaml.safe_load (when available) to handle any indentation style.
    Returns [] on any failure or when no referenced_by field is present.
    """
    if not content.startswith("---"):
        return []
    end = content.find("\n---", 3)
    if end == -1:
        return []
    fm_text = content[3:end]
    if yaml is not None:
        try:
            data = yaml.safe_load(fm_text)
            if isinstance(data, dict):
                rb = data.get("referenced_by")
                if isinstance(rb, list):
                    return [e for e in rb if isinstance(e, dict)]
        except Exception:
            pass
    return []


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def materialize(vault, apply: bool = False, backup_dir=None) -> dict:
    """Materialize view_source referenced_by entries in truth atoms.

    For each atom referenced by a VIEW node:
    - Read current referenced_by (preserve existing truth_edge entries).
    - Add only the new view_source entries that are NOT already present (dedup).
    - If there is nothing new, skip (idempotent).
    - Patch the file surgically via truth_backref_materialize._build_new_content.

    apply=False -> dry-run (only count). apply=True -> write (surgical patch).
    backup_dir + apply -> copy pre-write file to Path(backup_dir)/atom_rel.

    Returns dict with int keys: views, atoms, would_update, updated, backed_up,
    added_backrefs.
    """
    vault = Path(vault)

    idx = view_backref_index.build_view_backref_index(vault)
    views: int = idx["view_count"]
    backrefs: dict = idx["backrefs"]
    atoms: int = len(backrefs)

    would_update = 0
    updated = 0
    backed_up = 0
    added_backrefs = 0

    if backup_dir is not None:
        backup_dir = Path(backup_dir)

    for atom_rel, view_backrefs in sorted(backrefs.items()):
        atom_path = vault / atom_rel
        if not atom_path.is_file():
            continue

        try:
            content = atom_path.read_text(encoding="utf-8")
        except OSError:
            continue

        # Parse what is already in referenced_by
        current_rb = _parse_current_rb(content)
        existing = {
            (e.get("by"), e.get("kind"))
            for e in current_rb
            if isinstance(e, dict)
        }

        # Collect only the new view_source entries (DROP view_rel — not stored)
        new_entries: list[dict] = []
        for vb in view_backrefs:
            entry_by = vb["by"]
            if (entry_by, "view_source") not in existing:
                new_entries.append({"by": entry_by, "kind": "view_source"})

        if not new_entries:
            # Nothing new — already current (or atom not in any view)
            continue

        # Merge: existing entries (preserve order + their by/kind) + new entries.
        # Normalise to plain {by, kind} dicts so _build_new_content only sees those.
        combined: list[dict] = [
            {"by": e.get("by", ""), "kind": e.get("kind", "")}
            for e in current_rb
        ] + new_entries

        new_content = truth_backref_materialize._build_new_content(content, combined)
        if new_content is None or new_content == content:
            continue

        would_update += 1
        added_backrefs += len(new_entries)

        if apply:
            if backup_dir is not None:
                backup_path = backup_dir / atom_rel
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                # Read raw bytes so backup is byte-identical to the pre-write file
                # (preserves platform line endings, e.g. CRLF on Windows).
                backup_path.write_bytes(atom_path.read_bytes())
                backed_up += 1
            atom_path.write_text(new_content, encoding="utf-8")
            updated += 1

    return {
        "views": views,
        "atoms": atoms,
        "would_update": would_update,
        "updated": updated,
        "backed_up": backed_up,
        "added_backrefs": added_backrefs,
    }


def main(argv=None) -> int:
    """CLI entry point.

    --vault REQUIRED  Path to vault root.
    --apply           Write changes (default: dry-run).
    --backup-dir DIR  Copy pre-write files here at backup_dir/<atom_rel>.

    Returns 0 on success, 2 when vault is not a directory.
    """
    parser = argparse.ArgumentParser(
        prog="truth_view_backref_materialize",
        description="BL-491 G3: view_source referenced_by materializer",
    )
    parser.add_argument("--vault", required=True, help="Path to vault root")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes (default: dry-run, no writes)",
    )
    parser.add_argument(
        "--backup-dir",
        default=None,
        metavar="DIR",
        help="Copy pre-write files to DIR/<atom_rel> before writing",
    )
    args = parser.parse_args(argv)

    vault = Path(args.vault)
    if not vault.is_dir():
        print(f"ERROR: {vault} is not a directory", file=sys.stderr)
        return 2

    backup_dir = Path(args.backup_dir) if args.backup_dir else None
    result = materialize(vault, apply=args.apply, backup_dir=backup_dir)

    print(
        f"views={result['views']} atoms={result['atoms']} "
        f"would_update={result['would_update']} updated={result['updated']} "
        f"backed_up={result['backed_up']} added_backrefs={result['added_backrefs']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
