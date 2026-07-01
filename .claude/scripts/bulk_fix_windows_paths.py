#!/usr/bin/env python3
"""
bulk_fix_windows_paths.py — Ersetzt hardcoded Windows-Pfade in Vault-Backlog-Dateien.

BL-151 NEW-L1: Bulk-Fix fuer C:/Users/Administrator/Documents/OmniCommand/
Ersetzt durch dynamisch aufgeloesten Vault-Root (Linux-Pfad).

Aufruf:
  python3 bulk_fix_windows_paths.py          # dry-run (Standard)
  python3 bulk_fix_windows_paths.py --apply  # echtes Schreiben
"""

import sys
import os
import re
import argparse
from pathlib import Path

# resolve_vault_root via sys.path
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))
from resolve_vault_root import resolve_vault_root
from vault_write_atomic import write_vault_node_atomic

WINDOWS_PATTERNS = [
    "C:/Users/Administrator/Documents/OmniCommand/",
    "C:\\\\Users\\\\Administrator\\\\Documents\\\\OmniCommand\\\\",
    "C:\\Users\\Administrator\\Documents\\OmniCommand\\",
]


def fix_file(path: Path, vault_root: str, apply: bool) -> tuple[int, bool]:
    """Returns (treffer_count, changed)."""
    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  SKIP (read error): {path}: {e}")
        return 0, False

    new_content = content
    total_hits = 0

    for pattern in WINDOWS_PATTERNS:
        count = new_content.count(pattern)
        if count > 0:
            # Normalize replacement: vault_root + trailing slash
            replacement = vault_root.rstrip("/") + "/"
            new_content = new_content.replace(pattern, replacement)
            total_hits += count

    if total_hits == 0:
        return 0, False

    if apply:
        write_vault_node_atomic(path, new_content, encoding="utf-8")

    return total_hits, True


def main():
    parser = argparse.ArgumentParser(description="Bulk-Fix Windows-Pfade in Vault-Backlog-Dateien")
    parser.add_argument("--apply", action="store_true", help="Echtes Schreiben (Standard: dry-run)")
    args = parser.parse_args()

    vault_root = str(resolve_vault_root())
    backlog_dir = Path(vault_root) / "Backlog"

    if not backlog_dir.exists():
        print(f"ERROR: Backlog-Verzeichnis nicht gefunden: {backlog_dir}")
        sys.exit(1)

    md_files = list(backlog_dir.rglob("*.md"))

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[bulk_fix_windows_paths] Modus: {mode}")
    print(f"[bulk_fix_windows_paths] Vault-Root: {vault_root}")
    print(f"[bulk_fix_windows_paths] Backlog-Dir: {backlog_dir}")
    print(f"[bulk_fix_windows_paths] Gefundene .md-Files: {len(md_files)}")
    print()

    inspected = 0
    changed_files = 0
    total_treffer = 0

    for md_file in sorted(md_files):
        inspected += 1
        treffer, changed = fix_file(md_file, vault_root, apply=args.apply)
        if changed:
            changed_files += 1
            total_treffer += treffer
            action = "FIXED" if args.apply else "WOULD FIX"
            print(f"  [{action}] {md_file.relative_to(backlog_dir)} ({treffer} Treffer)")

    print()
    print(f"[bulk_fix_windows_paths] ERGEBNIS:")
    print(f"  {inspected} Files inspiziert")
    print(f"  {changed_files} geaendert{'  (dry-run: noch nicht geschrieben)' if not args.apply else ''}")
    print(f"  {total_treffer} Treffer gesamt")

    if not args.apply and changed_files > 0:
        print()
        print("  => Fuehre mit --apply aus um Aenderungen zu schreiben.")


if __name__ == "__main__":
    main()
