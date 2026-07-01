#!/usr/bin/env python3
"""
truth_id_dedup.py -- Deduplicator for truth atoms sharing the same global id.

Collision shape: two or more truth atoms share the same global id {namespace}.{local_id}.
Canonical copy: path contains the namespace string.
Stray copy: path does NOT contain the namespace string.
Fix: keep canonical, delete stray(s).

Ambiguous: no path (or more than one path) contains the namespace -> skip, record.

Modi:
  - apply=False (dry-run): count only, never delete (deleted=0).
  - apply=True:  delete strays.  deleted = number of actually removed files.
  - backup_dir + apply: copy pre-delete file to backup_dir before removing;
    backed_up == deleted.

Return dict keys:
  collisions   int  -- number of ids with >1 truth file
  resolved     int  -- colliding ids with a non-None canonical
  deleted      int  -- files actually deleted (0 in dry-run)
  backed_up    int  -- files backed up (0 without backup_dir)
  ambiguous    int  -- colliding ids where canonical_path returned None
  ambiguous_ids list[str] -- the ids themselves
"""
from __future__ import annotations

import argparse
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import yaml

# ---------------------------------------------------------------------------
# Frontmatter helpers (mirror truth_keyword_demerge conventions)
# ---------------------------------------------------------------------------

def _parse_frontmatter(content: str) -> Optional[dict]:
    """Parse YAML frontmatter block.  Return dict or None on failure."""
    if not content.startswith("---\n"):
        return None
    end = content.find("\n---\n", 4)
    if end == -1:
        return None
    fm_text = content[4:end]
    try:
        data = yaml.safe_load(fm_text)
        if isinstance(data, dict):
            return data
        return None
    except yaml.YAMLError:
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_collisions(root) -> Dict[str, List[str]]:
    """Walk root, find truth atoms, return ids with >1 file.

    Returns {id: sorted([relative_posix_path, ...])} for colliding ids only.
    """
    root = Path(root)
    by_id: Dict[str, List[str]] = defaultdict(list)

    for f in sorted(root.rglob("*.md")):
        if not f.is_file():
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        data = _parse_frontmatter(content)
        if data is None:
            continue
        if data.get("type") != "truth":
            continue
        atom_id = data.get("id")
        if not atom_id:
            continue
        atom_id = str(atom_id).strip()
        if not atom_id:
            continue

        rel = f.relative_to(root).as_posix()
        by_id[atom_id].append(rel)

    return {
        aid: sorted(paths)
        for aid, paths in by_id.items()
        if len(paths) > 1
    }


def canonical_path(atom_id: str, paths: List[str]) -> Optional[str]:
    """Return the one path whose string contains the namespace, or None.

    Namespace = atom_id.rsplit('.', 1)[0] (part before last dot).
    Returns None when zero or more-than-one path matches (ambiguous).
    """
    ns = atom_id.rsplit(".", 1)[0]
    matches = [p for p in paths if ns in p]
    if len(matches) == 1:
        return matches[0]
    return None


def dedup(root, apply: bool = False, backup_dir=None) -> dict:
    """Scan root for id collisions and optionally delete strays.

    Returns:
      {
        "collisions":    int,
        "resolved":      int,
        "deleted":       int,
        "backed_up":     int,
        "ambiguous":     int,
        "ambiguous_ids": list[str],
      }
    """
    root = Path(root)
    if backup_dir is not None:
        backup_dir = Path(backup_dir)

    collisions_map = find_collisions(root)

    n_collisions = len(collisions_map)
    n_resolved = 0
    n_deleted = 0
    n_backed_up = 0
    n_ambiguous = 0
    ambiguous_ids: List[str] = []

    for atom_id, paths in collisions_map.items():
        canon = canonical_path(atom_id, paths)
        if canon is None:
            n_ambiguous += 1
            ambiguous_ids.append(atom_id)
            continue

        n_resolved += 1
        deletion_set = [p for p in paths if p != canon]

        if apply:
            for rel_path in deletion_set:
                abs_path = root / rel_path
                if backup_dir is not None:
                    dest = backup_dir / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    # Read as text (normalises CRLF -> LF on Windows) and write
                    # as UTF-8 bytes so backup bytes match content.encode("utf-8")
                    # on all platforms -- same approach as truth_keyword_demerge.py.
                    try:
                        raw = abs_path.read_text(encoding="utf-8", errors="replace")
                        dest.write_bytes(raw.encode("utf-8"))
                    except OSError:
                        shutil.copy2(str(abs_path), str(dest))
                    n_backed_up += 1
                abs_path.unlink()
                n_deleted += 1

    return {
        "collisions": n_collisions,
        "resolved": n_resolved,
        "deleted": n_deleted,
        "backed_up": n_backed_up,
        "ambiguous": n_ambiguous,
        "ambiguous_ids": ambiguous_ids,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    """argparse entry point.

    Positional: root directory.
    --apply          delete strays (default: dry-run).
    --backup-dir DIR copy pre-delete files here before removing.

    Returns 0 on success, 2 if root is not a directory.
    Prints WARNING to stderr if ambiguous_ids is non-empty.
    """
    p = argparse.ArgumentParser(
        prog="truth_id_dedup",
        description="Deduplicate truth atoms sharing the same global id",
    )
    p.add_argument("root", help="Root directory to scan")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Delete stray files (default: dry-run only)",
    )
    p.add_argument(
        "--backup-dir",
        dest="backup_dir",
        default=None,
        metavar="DIR",
        help="Directory for pre-delete backups (requires --apply)",
    )
    args = p.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 2

    backup_dir = Path(args.backup_dir) if args.backup_dir else None

    result = dedup(root, apply=args.apply, backup_dir=backup_dir)

    print(
        f"collisions={result['collisions']} "
        f"resolved={result['resolved']} "
        f"deleted={result['deleted']} "
        f"backed_up={result['backed_up']} "
        f"ambiguous={result['ambiguous']}"
    )

    if result["ambiguous_ids"]:
        count = len(result["ambiguous_ids"])
        print(
            f"WARNING: {count} ambiguous id{'s' if count != 1 else ''} "
            f"could not be resolved (no unique namespace path): "
            f"{result['ambiguous_ids']!r}",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
