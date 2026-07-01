#!/usr/bin/env python3
"""
view_decorrupt.py — BL-491 AC-1 (Lane B) provably-non-destructive de-corruption tool.

The keyword-forward-reference writer corrupted 25 view files by prepending one or
more BARE `source_atoms:` blocks (NO `---` delimiters) at byte 0. Each re-run
re-prepended, stacking stray blocks. Corruption has two shapes, both = a leading
contiguous run of stray lines at byte 0:
  - Shape A: stray run, then a BOM (EF BB BF), then the real `---` frontmatter.
  - Shape B: stray run, then the ORIGINAL body (no leading frontmatter, starts `#`).

This tool removes ONLY the validated stray prefix. It operates on BYTES and NEVER
decodes / re-encodes / normalizes the body — the de-corrupted output is ALWAYS an
exact SUFFIX of the input (`raw.endswith(out)` and `out == raw[cut:]`). This is the
load-bearing safety invariant.

FENCE: VIEW-FILES ONLY. Files under `_meta_truths/` (the atom domain, Lane C) are
NEVER discovered or touched. Default DRY-RUN writes nothing. Idempotent.

Public API:
    find_stray_run_end(raw: bytes) -> int | None
    decorrupt_bytes(raw: bytes) -> tuple[bytes | None, str]
    discover_corrupt(vault: Path) -> list[Path]
    decorrupt_file(path: Path, *, write: bool) -> dict
    run(vault: Path, *, write: bool) -> dict
    main(argv=None) -> int
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BOM = b"\xef\xbb\xbf"

_HEADER_RE = re.compile(r"source_atoms:\s*")
_LIST_ITEM_RE = re.compile(r"\s+-\s+(\S.*?)\s*")


# ──────────────────────────────────────────────────────────────────────────────
# Core algorithm
# ──────────────────────────────────────────────────────────────────────────────
def find_stray_run_end(raw: bytes) -> int | None:
    """Return the byte index where the real content begins (the cut point), or
    None if `raw` is NOT corrupt.

    Walks lines (split on b"\\n", keeping the newline). A line is STRAY iff it is a
    `source_atoms:` header OR an indented yaml list item whose value contains "/"
    or ends ".md". Blank lines inside the run are tolerated. The run ends at the
    first non-stray line; `saw_header` (at least one `source_atoms:` header) is
    REQUIRED, else not our corruption -> None.

    A leading BOM on a line is stripped for CLASSIFICATION only (so a BOM-glued
    `\\xef\\xbb\\xbf---` line is recognized as the real `---` and ends the run). The
    cut is the byte START of that line; then, if a BOM sits glued before the real
    `---`, the cut advances past it — the BOM is part of the corruption prefix (its
    presence is what defeated the writer's frontmatter detection), so it is
    SWALLOWED. The de-corrupted output is the EXACT suffix `raw[cut:]` beginning at
    the well-formed `---`.
    """
    # Already clean — real frontmatter at byte 0, not corrupt.
    if raw.startswith(b"---"):
        return None

    saw_header = False
    pos = 0
    offset = 0
    consumed_all = True

    for line in raw.splitlines(keepends=True):
        core = line.rstrip(b"\r\n")
        if core.startswith(BOM):
            core = core[len(BOM):]
        s = core.decode("utf-8", "replace")

        if s == "":
            # blank line inside the run is tolerated
            offset += len(line)
            continue
        if _HEADER_RE.fullmatch(s):
            saw_header = True
            offset += len(line)
            continue
        m = _LIST_ITEM_RE.fullmatch(s)
        if m and ("/" in m.group(1) or m.group(1).endswith(".md")):
            offset += len(line)
            continue

        # first NON-stray line -> the run ends here
        pos = offset
        consumed_all = False
        break

    if consumed_all:
        # the loop consumed the whole file as stray
        pos = len(raw)

    if not saw_header:
        # no source_atoms: header consumed -> not our corruption
        return None

    # swallow a BOM glued before the real --- (Shape A: stray + BOM + frontmatter)
    if raw[pos:pos + len(BOM)] == BOM:
        pos += len(BOM)

    return pos


def decorrupt_bytes(raw: bytes) -> tuple[bytes | None, str]:
    """Return (new_bytes, reason). The returned bytes are ALWAYS an exact SUFFIX of
    the input — only a validated stray prefix is removed; the body is never modified.

    - not corrupt           -> (None, "clean")
    - only stray, no body    -> (None, "empty_after_decorrupt")
    - corrupt + real body    -> (raw[cut:], "decorrupted")
    """
    cut = find_stray_run_end(raw)
    if cut is None:
        return (None, "clean")
    body = raw[cut:]
    if body.strip() == b"":
        return (None, "empty_after_decorrupt")
    return (body, "decorrupted")


# ──────────────────────────────────────────────────────────────────────────────
# Discovery
# ──────────────────────────────────────────────────────────────────────────────
def discover_corrupt(vault: Path) -> list[Path]:
    """rglob `*.md` under `vault`, EXCLUDE any file whose vault-relative posix path
    starts with `_meta_truths/` (atom domain — NEVER touch). Include a file iff
    `decorrupt_bytes` yields non-None new bytes (corrupt + non-empty real body).
    """
    vault = Path(vault)
    found: list[Path] = []
    if not vault.is_dir():
        return found

    for path in sorted(vault.rglob("*.md")):
        if not path.is_file():
            continue
        rel = path.relative_to(vault).as_posix()
        if rel.startswith("_meta_truths/"):
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        new, _reason = decorrupt_bytes(raw)
        if new is not None:
            found.append(path)
    return found


# ──────────────────────────────────────────────────────────────────────────────
# De-corruption (single file)
# ──────────────────────────────────────────────────────────────────────────────
def decorrupt_file(path: Path, *, write: bool) -> dict:
    """De-corrupt one file.

    Reads bytes; new, reason = decorrupt_bytes(raw).
      - new is None -> action "skip", reason ("clean" / "empty_after_decorrupt").
      - else        -> action "decorrupt"; if write: path.write_bytes(new).

    Idempotent: a second call on a now-clean file returns action="skip",
    reason="clean".
    """
    path = Path(path)
    raw = path.read_bytes()
    new, reason = decorrupt_bytes(raw)

    result: dict = {
        "path": str(path),
        "action": None,
        "reason": reason,
        "removed_bytes": 0,
        "shape": None,
    }

    if new is None:
        result["action"] = "skip"
        return result

    result["action"] = "decorrupt"
    # Shape A = real `---` frontmatter (the BOM, if any, was swallowed by the cut);
    # Shape B = no frontmatter (the original body starts with a heading).
    result["shape"] = "A" if new.startswith(b"---") else "B"
    result["removed_bytes"] = len(raw) - len(new)
    if write:
        path.write_bytes(new)
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Batch run
# ──────────────────────────────────────────────────────────────────────────────
def run(vault: Path, *, write: bool) -> dict:
    """Discover corrupt views, de-corrupt each.

    Returns {vault, write, decorrupted:[...], skipped_count, total_candidates}.
    """
    vault = Path(vault)
    candidates = discover_corrupt(vault)
    decorrupted: list[dict] = []
    skipped = 0
    for path in candidates:
        res = decorrupt_file(path, write=write)
        if res["action"] == "decorrupt":
            decorrupted.append(res)
        else:
            skipped += 1
    return {
        "vault": str(vault),
        "write": write,
        "decorrupted": decorrupted,
        "skipped_count": skipped,
        "total_candidates": len(candidates),
    }


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Provably-non-destructive de-corruption of stray source_atoms "
        "prefixes in view files (BL-491 AC-1, Lane B). Default DRY-RUN."
    )
    parser.add_argument("--vault", required=True, help="Path to vault root")
    parser.add_argument(
        "--write", action="store_true", help="Destructive write (default: dry-run)"
    )
    parser.add_argument("--out", default=None, help="Write run report as JSON")
    parser.add_argument("--quiet", action="store_true", help="Suppress summary print")
    args = parser.parse_args(argv)

    vault = Path(args.vault)
    result = run(vault, write=args.write)

    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    if not args.quiet:
        mode = "WRITE" if args.write else "DRY-RUN"
        print(
            f"[view_decorrupt] {mode} vault={result['vault']} "
            f"candidates={result['total_candidates']} "
            f"decorrupted={len(result['decorrupted'])} "
            f"skipped={result['skipped_count']}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
