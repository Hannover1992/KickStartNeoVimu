#!/usr/bin/env python3
"""
BL-202: Manifest Garbage Collector

Reduziert {bl_folder}/_manifest.md auf Live-State-Only durch Verschieben von
Verlauf-Feldern (history[], rollover_blocks, completed_*) in
_manifest_protokoll.md (existing Pattern B Rollover-Mechanismus).

Live-State Whitelist:
- *_PIPELINE_STATE.phase, current_*, last_completed
- BERATER_OUTPUTS.<latest_only>
- DF_BATCH_STATE.modus, batch_items, batch_modes (aktuelle)
- BL_LIFECYCLE_STATE (aktiv)

Verlauf (wird verschoben):
- *_PIPELINE_STATE.history[]
- BERATER_OUTPUTS.<superseded>
- completed_sub_batches (alt)
- *_log[] Felder
- *_ARCHIVED, *_PREV Felder

Usage:
  python3 manifest_gc.py {bl_folder}/_manifest.md
  python3 manifest_gc.py {bl_folder}/_manifest.md --dry-run
  python3 manifest_gc.py {bl_folder}/_manifest.md --threshold=5000
  python3 manifest_gc.py {bl_folder}/_manifest.md --migrate (Backward-Compat)

Exit-Codes:
  0  - GC erfolgreich (auch wenn nichts zu tun)
  1  - File-Fehler (Pfad existiert nicht, etc.)
  2  - Schema-Fehler (Manifest ungueltiges YAML)
  3  - Threshold nicht erreicht (kein GC noetig)
"""

import argparse
import os
import re
import sys
import shutil
from datetime import datetime
from pathlib import Path


# AK-1: Live-State-Whitelist (was BLEIBT im Manifest)
LIVE_STATE_FIELDS = {
    "BL_LIFECYCLE_STATE",
    "A_PIPELINE_STATE",
    "IDF_PIPELINE_STATE",
    "DF_PIPELINE_STATE",
    "DF_BATCH_STATE",
    "SC_PIPELINE_STATE",
    "I_PIPELINE_STATE",
    "POSTBATCH_PIPELINE_STATE",
    "PREPRE_PIPELINE_STATE",
    "CROWN_STATE",
    "GLOBAL_HIL",
    "GLOBAL_MODUS",
    "GLOBAL_DIFFICULTY",
    "GLOBAL_CEILING",
    "GLOBAL_FLOOR",
}

# AK-1: Verlauf-Patterns (wird zu Protokoll verschoben)
HISTORY_PATTERNS = [
    re.compile(r"^.*\.history\[\]", re.MULTILINE),
    re.compile(r"^.*_log:\s*$", re.MULTILINE),
    re.compile(r"^.*_ARCHIVED:", re.MULTILINE),
    re.compile(r"^.*_PREV:", re.MULTILINE),
    re.compile(r"^.*completed_sub_batches:\s*\[.*\]$", re.MULTILINE),
]


def parse_args(argv):
    p = argparse.ArgumentParser(description="BL-202 Manifest Garbage Collector")
    p.add_argument("manifest_path", help="Pfad zu {bl_folder}/_manifest.md")
    p.add_argument("--dry-run", action="store_true", help="Nur analysieren, keine Aenderung")
    p.add_argument("--threshold", type=int, default=5000,
                   help="Schwellwert in LOC fuer Auto-GC (default 5000)")
    p.add_argument("--migrate", action="store_true",
                   help="Einmal-Migration alter Manifests + Marker gc_migrated=true")
    p.add_argument("--force", action="store_true",
                   help="GC ausfuehren auch unter Threshold")
    return p.parse_args(argv[1:])


def count_lines(path):
    if not os.path.exists(path):
        return 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


def detect_history_blocks(content):
    """
    AK-2: Findet Verlauf-Bloecke im Manifest.
    Heuristik: alle Felder mit Suffix _ARCHIVED, _PREV, _log, .history[],
    plus completed_sub_batches arrays mit > 0 Eintraegen.

    Returns: List von (start_line, end_line, field_name) Tupeln.
    """
    blocks = []
    lines = content.splitlines()
    for i, line in enumerate(lines):
        for pattern in HISTORY_PATTERNS:
            if pattern.match(line):
                # Suche Block-Ende (naechste Top-Level-Zeile mit anderer Einrueckung)
                indent = len(line) - len(line.lstrip())
                end = i + 1
                while end < len(lines):
                    next_indent = len(lines[end]) - len(lines[end].lstrip())
                    if lines[end].strip() and next_indent <= indent and not lines[end].startswith(' '):
                        break
                    end += 1
                blocks.append((i, end, line.strip()))
                break
    return blocks


def move_to_protokoll(manifest_path, history_blocks, dry_run=False):
    """
    AK-2: Verschiebt Verlauf-Bloecke nach _manifest_protokoll.md (Pattern B).
    """
    protokoll_path = Path(manifest_path).parent / "_manifest_protokoll.md"
    timestamp = datetime.now().isoformat()

    with open(manifest_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Sortiere Bloecke rueckwaerts (von hinten nach vorn loeschen)
    blocks_sorted = sorted(history_blocks, key=lambda b: b[0], reverse=True)

    moved_content = [f"\n\n## GC-Eintrag {timestamp}\n",
                     f"Source: {manifest_path}\n",
                     f"Blocks moved: {len(blocks_sorted)}\n\n"]

    for start, end, name in blocks_sorted:
        moved_content.append(f"### {name}\n```\n")
        moved_content.extend(lines[start:end])
        moved_content.append("\n```\n\n")
        if not dry_run:
            del lines[start:end]

    if dry_run:
        print(f"[DRY-RUN] Would move {len(blocks_sorted)} blocks:")
        for s, e, n in blocks_sorted:
            print(f"  {s}-{e}: {n}")
        return False

    # Write modified manifest
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.writelines(lines)

    # Append to protokoll (Pattern B prepend would be better but for simplicity append)
    with open(protokoll_path, "a", encoding="utf-8") as f:
        f.writelines(moved_content)

    return True


def add_gc_marker(manifest_path):
    """AK-5: Backward-Compat Migration Marker."""
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "gc_migrated:" in content:
        return False
    # Insert before first non-frontmatter line
    lines = content.splitlines(keepends=True)
    insert_idx = 1
    fm_count = 0
    for i, line in enumerate(lines):
        if line.startswith("---"):
            fm_count += 1
            if fm_count == 2:
                insert_idx = i
                break
    marker = f"gc_migrated: true\ngc_migrated_at: {datetime.now().isoformat()}\n"
    lines.insert(insert_idx, marker)
    with open(manifest_path, "w", encoding="utf-8") as f:
        f.writelines(lines)
    return True


def main(argv):
    args = parse_args(argv)
    manifest_path = args.manifest_path

    if not os.path.exists(manifest_path):
        print(f"[ERROR] Manifest not found: {manifest_path}", file=sys.stderr)
        return 1

    line_count = count_lines(manifest_path)
    print(f"[GC] Manifest: {manifest_path} ({line_count} LOC)")

    # AK-4: Threshold-Check
    if line_count < args.threshold and not args.force:
        print(f"[GC] Below threshold ({args.threshold} LOC) — no GC needed")
        return 3

    # Backup
    if not args.dry_run:
        backup_path = f"{manifest_path}.bak_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        shutil.copy2(manifest_path, backup_path)
        print(f"[GC] Backup: {backup_path}")

    # Read content
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()

    # AK-2: Detect history blocks
    history_blocks = detect_history_blocks(content)
    print(f"[GC] Detected {len(history_blocks)} history-block candidates")

    if not history_blocks:
        print("[GC] No history blocks found — nothing to do")
        return 0

    # AK-2: Move to protokoll
    moved = move_to_protokoll(manifest_path, history_blocks, dry_run=args.dry_run)

    # AK-5: Add migration marker
    if args.migrate and not args.dry_run:
        if add_gc_marker(manifest_path):
            print("[GC] Added gc_migrated marker")

    if args.dry_run:
        print("[GC] DRY-RUN complete - no changes")
    else:
        new_count = count_lines(manifest_path)
        print(f"[GC] Reduced: {line_count} -> {new_count} LOC (saved {line_count - new_count})")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
