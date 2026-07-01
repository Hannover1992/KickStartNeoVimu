#!/usr/bin/env python3
"""
truth_keyword_demerge.py -- Surgical de-merger for keyword/referenced_by corruption.

Corruption shape: truth atoms have {by, kind: truth_edge} dicts wrongly mixed
into their keywords: list.  Those dicts are referenced_by-format entries that
leaked into keywords.  This module removes them SURGICALLY from the keywords
block, keeping everything else (referenced_by block, text, edges, body, all
other fields, and the string keywords) BYTE-IDENTICAL.

Modi:
  - apply=False (dry-run): count only, never write (updated=0).
  - apply=True:  write.  updated = number of actually changed files.  Idempotent.
  - backup_dir + apply: copy PRE-write file to backup_dir before writing;
    backed_up == updated.

Return dict keys (all int unless noted):
  scanned, with_dict_keywords, would_update, updated, backed_up,
  dropped_total, became_empty  (int)
  dropped_non_subset  (list of {path, by, kind} dicts)
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Optional

import yaml

_FM_BLOCK = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)


# ---------------------------------------------------------------------------
# Public primitive
# ---------------------------------------------------------------------------

def assert_keywords_type_pure(keywords: list) -> None:
    """Raise AssertionError naming offending entries if any element is not a str.

    Returns None if all elements are strings (including empty list).
    """
    offenders = [entry for entry in keywords if not isinstance(entry, str)]
    if offenders:
        raise AssertionError(
            f"keywords contains non-str (dict leakage) entries: {offenders!r}"
        )


# ---------------------------------------------------------------------------
# Surgical block rewriter
# ---------------------------------------------------------------------------

def demerge_keywords_block(content: str) -> Optional[str]:
    """Remove dict entries from the keywords block, keep everything else verbatim.

    Returns the modified content string when at least one dict was dropped.
    Returns None when:
      - no YAML frontmatter found, OR
      - no keywords field found, OR
      - keywords uses inline/flow style (non-empty inline value), OR
      - nothing changed (no dict entries in keywords / already clean).
    """
    # Step 1: locate frontmatter
    m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    if m is None:
        return None

    fm_text = m.group(1)
    prefix = content[: m.start(1)]  # "---\n"
    suffix = content[m.end(1):]     # "\n---\n<body>"

    # Step 2: find the keywords: line
    lines = fm_text.split("\n")
    k: Optional[int] = None
    inline_val = ""
    for i, line in enumerate(lines):
        m2 = re.match(r"^keywords:\s*(.*)$", line)
        if m2:
            k = i
            inline_val = m2.group(1).strip()
            break
    if k is None:
        return None
    if inline_val:
        # Flow-style (e.g. "keywords: []") -- never corrupted in our data.
        return None

    # Step 3: find the block end j (first top-level field after k, or end of lines)
    j = len(lines)
    for idx in range(k + 1, len(lines)):
        # Top-level field: starts with [A-Za-z_], no leading space, not a list item.
        if re.match(r"^[A-Za-z_][\w-]*:", lines[idx]):
            j = idx
            break

    # Step 4: split block lines [k+1, j) into items.
    # An item starts at a line matching ^\s*-(\s|$); continuation lines follow.
    block_lines = lines[k + 1 : j]
    items: list[list[str]] = []
    current_item: Optional[list[str]] = None

    for line in block_lines:
        if re.match(r"^(\s*)-(\s|$)", line):
            if current_item is not None:
                items.append(current_item)
            current_item = [line]
        else:
            if current_item is not None:
                current_item.append(line)
            # else: orphan line before any item -- ignore (should not happen)
    if current_item is not None:
        items.append(current_item)

    # Step 5: classify each item as dict (drop) or str/other (keep).
    kept_item_lines: list[list[str]] = []
    any_dict_found = False

    for item_lines in items:
        m3 = re.match(r"^(\s*)-", item_lines[0])
        if not m3:
            # Cannot parse -- keep conservatively.
            kept_item_lines.append(item_lines)
            continue

        indent = len(m3.group(1))
        # Dedent by the dash's leading indent before feeding to yaml.
        dedented = [
            line[indent:] if len(line) >= indent else line
            for line in item_lines
        ]
        text = "\n".join(dedented)

        try:
            val = yaml.safe_load(text)
            if isinstance(val, list) and len(val) >= 1:
                element = val[0]
                if isinstance(element, dict):
                    any_dict_found = True
                    # DROP: do not add to kept_item_lines
                    continue
                # str or other scalar -- KEEP verbatim
                kept_item_lines.append(item_lines)
            else:
                # Unexpected structure -- keep conservatively
                kept_item_lines.append(item_lines)
        except yaml.YAMLError:
            # Parsing failure -- keep conservatively
            kept_item_lines.append(item_lines)

    if not any_dict_found:
        # Nothing to change.
        return None

    # Step 6: rebuild the keywords section.
    kw_line = lines[k]
    kw_indent_str = " " * (len(kw_line) - len(kw_line.lstrip()))

    new_lines: list[str] = list(lines[:k])

    if kept_item_lines:
        # At least one string item survives -- emit keywords: + kept items verbatim.
        new_lines.append(kw_line)
        for item_lines in kept_item_lines:
            new_lines.extend(item_lines)
    else:
        # All items were dicts -- collapse to empty list.
        new_lines.append(f"{kw_indent_str}keywords: []")

    # Append everything from the block end onward (referenced_by, seq, edges, ...).
    new_lines.extend(lines[j:])

    # Step 7: reassemble content.
    new_fm = "\n".join(new_lines)
    new_content = prefix + new_fm + suffix

    if new_content == content:
        return None
    return new_content


# ---------------------------------------------------------------------------
# Internal helpers (driver)
# ---------------------------------------------------------------------------

def _parse_frontmatter(content: str):
    """Return (fm_text, fm_start, fm_end) or None."""
    m = _FM_BLOCK.match(content)
    if not m:
        return None
    return m.group(1), m.start(1), m.end(1)


def _scalar_field(fm_text: str, field: str) -> Optional[str]:
    """Extract a simple top-level scalar from raw frontmatter text."""
    for line in fm_text.split("\n"):
        m = re.match(rf"^{re.escape(field)}:\s*(.*)$", line)
        if m:
            return m.group(1).strip()
    return None


def _is_truth_atom(fm_text: str) -> bool:
    return _scalar_field(fm_text, "type") == "truth"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def demerge(root, apply: bool = False, backup_dir=None) -> dict:
    """Scan Path(root).rglob('*.md') for truth atoms; remove dict keywords.

    apply=False -> dry-run (count only, no writes).
    apply=True  -> write changed files.
    backup_dir + apply -> copy pre-write file to backup_dir / atom.relative_to(root).

    Returns:
      {
        "scanned":           int,   # all .md files iterated
        "with_dict_keywords": int,  # truth atoms with >=1 dict keyword
        "would_update":      int,
        "updated":           int,
        "backed_up":         int,
        "dropped_total":     int,   # total dict-keyword entries removed
        "became_empty":      int,   # atoms whose keywords list became []
        "dropped_non_subset": list, # {path, by, kind} for non-referenced_by dicts
      }
    """
    root = Path(root)
    if backup_dir is not None:
        backup_dir = Path(backup_dir)

    scanned = 0
    with_dict_keywords = 0
    would_update = 0
    updated = 0
    backed_up = 0
    dropped_total = 0
    became_empty = 0
    dropped_non_subset: list[dict] = []

    for f in sorted(root.rglob("*.md")):
        if not f.is_file():
            continue
        scanned += 1

        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        parsed_fm = _parse_frontmatter(content)
        if parsed_fm is None:
            continue
        fm_text = parsed_fm[0]

        if not _is_truth_atom(fm_text):
            continue

        # Parse frontmatter with yaml to inspect keywords / referenced_by.
        try:
            fm_data = yaml.safe_load(fm_text)
        except yaml.YAMLError:
            continue

        if not isinstance(fm_data, dict):
            continue

        keywords = fm_data.get("keywords", [])
        if not isinstance(keywords, list):
            continue

        dict_keywords = [kw for kw in keywords if isinstance(kw, dict)]
        if not dict_keywords:
            continue

        with_dict_keywords += 1

        # Determine dropped_non_subset: dict kws whose (by,kind) is not in referenced_by.
        referenced_by = fm_data.get("referenced_by", [])
        if not isinstance(referenced_by, list):
            referenced_by = []
        rb_set = {
            (e.get("by"), e.get("kind"))
            for e in referenced_by
            if isinstance(e, dict)
        }
        for dk in dict_keywords:
            by_val = dk.get("by")
            kind_val = dk.get("kind")
            if (by_val, kind_val) not in rb_set:
                dropped_non_subset.append({
                    "path": str(f),
                    "by": by_val,
                    "kind": kind_val,
                })

        # Count statistics.
        n_dict = len(dict_keywords)
        n_string = sum(1 for kw in keywords if isinstance(kw, str))
        dropped_total += n_dict
        if n_string == 0:
            became_empty += 1

        # Surgical removal.
        new_content = demerge_keywords_block(content)
        if new_content is None:
            # demerge_keywords_block returned None -- content already clean
            # or no change needed (idempotent).
            continue

        would_update += 1

        if apply:
            if backup_dir is not None:
                dest = backup_dir / f.relative_to(root)
                dest.parent.mkdir(parents=True, exist_ok=True)
                # Write backup from the in-memory text (LF-normalised by read_text)
                # so backup bytes match content.encode("utf-8") on all platforms,
                # avoiding Windows CRLF vs LF divergence from shutil.copy2.
                dest.write_bytes(content.encode("utf-8"))
                backed_up += 1
            f.write_text(new_content, encoding="utf-8")
            updated += 1

    return {
        "scanned": scanned,
        "with_dict_keywords": with_dict_keywords,
        "would_update": would_update,
        "updated": updated,
        "backed_up": backed_up,
        "dropped_total": dropped_total,
        "became_empty": became_empty,
        "dropped_non_subset": dropped_non_subset,
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
    Prints WARNING to stderr if dropped_non_subset is non-empty.
    """
    p = argparse.ArgumentParser(
        prog="truth_keyword_demerge",
        description="Surgical removal of dict-keyword corruption from truth atoms",
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

    result = demerge(root, apply=args.apply, backup_dir=backup_dir)

    print(
        f"scanned={result['scanned']} "
        f"with_dict_keywords={result['with_dict_keywords']} "
        f"would_update={result['would_update']} "
        f"updated={result['updated']} "
        f"backed_up={result['backed_up']} "
        f"dropped_total={result['dropped_total']} "
        f"became_empty={result['became_empty']}"
    )

    if result["dropped_non_subset"]:
        count = len(result["dropped_non_subset"])
        print(
            f"WARNING: {count} dict-keyword entr{'y' if count == 1 else 'ies'} "
            f"had no matching referenced_by entry and were still removed: "
            f"{result['dropped_non_subset']!r}",
            file=sys.stderr,
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
