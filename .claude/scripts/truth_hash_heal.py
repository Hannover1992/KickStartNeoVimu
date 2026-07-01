#!/usr/bin/env python3
"""truth_hash_heal.py -- Surgical content_hash healer for truth atoms.

Walk a directory tree, find all type:truth frontmatter atoms whose
content_hash field does not match sha256(text), and surgically replace
only the content_hash: line -- leaving every other byte identical.

Modi:
  apply=False (dry-run): count only, never write (updated=0).
  apply=True : write.  updated = number of actually changed files. Idempotent.
  backup_dir + apply: copy PRE-write file to backup_dir before writing;
    backed_up == updated.

Return dict keys (all int):
  scanned, mismatched, would_update, updated, backed_up
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Public primitive
# ---------------------------------------------------------------------------

def expected_hash(text: str) -> str:
    """Return sha256(text.encode('utf-8')).hexdigest()."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
_CONTENT_HASH_LINE_RE = re.compile(r"^(\s*)content_hash:")


def _surgical_replace(content: str, new_hash: str) -> str:
    """Replace the content_hash: line in the frontmatter.

    Only the first matching line is replaced.  All other content is
    preserved byte-identical.
    """
    m = _FM_RE.match(content)
    if m is None:
        return content

    fm_text = m.group(1)
    prefix = content[: m.start(1)]   # "---\n"
    body_tail = content[m.end(1):]   # "\n---\n<body>"

    fm_lines = fm_text.split("\n")
    new_fm_lines = []
    replaced = False
    for line in fm_lines:
        if not replaced and _CONTENT_HASH_LINE_RE.match(line):
            lm = _CONTENT_HASH_LINE_RE.match(line)
            indentation = lm.group(1)
            new_fm_lines.append(f"{indentation}content_hash: {new_hash}")
            replaced = True
        else:
            new_fm_lines.append(line)

    new_fm_text = "\n".join(new_fm_lines)
    return prefix + new_fm_text + body_tail


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def heal(root, apply: bool = False, backup_dir=None) -> dict:
    """Scan Path(root).rglob('*.md') for type:truth atoms; fix wrong hashes.

    apply=False -> dry-run (count only, no writes).
    apply=True  -> write changed files.
    backup_dir + apply -> copy pre-write file to backup_dir / atom.relative_to(root).

    Returns:
      {
        "scanned":     int,  # truth atoms seen
        "mismatched":  int,  # truth atoms with wrong content_hash
        "would_update": int,
        "updated":     int,
        "backed_up":   int,
      }
    """
    root = Path(root)
    if backup_dir is not None:
        backup_dir = Path(backup_dir)

    scanned = 0
    mismatched = 0
    would_update = 0
    updated = 0
    backed_up = 0

    for f in sorted(root.rglob("*.md")):
        if not f.is_file():
            continue

        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        # Parse frontmatter block
        m = _FM_RE.match(content)
        if m is None:
            continue

        fm_text = m.group(1)
        try:
            fm_data = yaml.safe_load(fm_text)
        except yaml.YAMLError:
            continue

        if not isinstance(fm_data, dict):
            continue

        if fm_data.get("type") != "truth":
            continue

        scanned += 1

        text_val = fm_data.get("text")
        stored_hash = fm_data.get("content_hash")

        if not isinstance(text_val, str):
            # No text field or not a string -- skip
            continue

        new_hash = expected_hash(text_val)
        if stored_hash == new_hash:
            # Already correct -- no-op
            continue

        mismatched += 1
        would_update += 1

        if not apply:
            continue

        # Surgical fix
        new_content = _surgical_replace(content, new_hash)

        if backup_dir is not None:
            dest = backup_dir / f.relative_to(root)
            dest.parent.mkdir(parents=True, exist_ok=True)
            # Write backup from in-memory text (LF-normalised by read_text) so
            # backup bytes match content.encode("utf-8") on all platforms --
            # mirrors truth_keyword_demerge convention.
            dest.write_bytes(content.encode("utf-8"))
            backed_up += 1

        f.write_text(new_content, encoding="utf-8")
        updated += 1

    return {
        "scanned": scanned,
        "mismatched": mismatched,
        "would_update": would_update,
        "updated": updated,
        "backed_up": backed_up,
    }


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    """argparse entry point.

    Positional: root directory.
    --apply          write changes (default: dry-run).
    --backup-dir DIR copy pre-apply files here before writing.

    Returns 0 on success, 2 if root is not a directory.
    """
    p = argparse.ArgumentParser(
        prog="truth_hash_heal",
        description="Surgical content_hash healer for truth atoms",
    )
    p.add_argument("root", help="Root directory to scan")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Write changes (default: dry-run only)",
    )
    p.add_argument(
        "--backup-dir",
        dest="backup_dir",
        default=None,
        metavar="DIR",
        help="Directory for pre-apply backups (requires --apply)",
    )
    args = p.parse_args(argv)

    root = Path(args.root)
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 2

    backup_dir = Path(args.backup_dir) if args.backup_dir else None
    result = heal(root, apply=args.apply, backup_dir=backup_dir)

    print(
        f"scanned={result['scanned']} "
        f"mismatched={result['mismatched']} "
        f"would_update={result['would_update']} "
        f"updated={result['updated']} "
        f"backed_up={result['backed_up']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
