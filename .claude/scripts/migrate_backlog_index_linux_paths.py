#!/usr/bin/env python3
"""BL-225 AK-A: Backlog-Index Linux-Pfad-Residue bereinigen (reversibel).

Migrations-Residue (BL-151 Vault-Split Linux->Windows): der kanonische
_backlog_index.md traegt ~93 Zeilen mit Linux-Pfaden
`/home/uczen/Documents/DCS/OmniCommand/...` die auf Windows NICHT resolven.
Sie zeigen auf .../OmniCommand/ (NICHT .../DCS/OmniCommand) -> reiner Prefix-Tausch.

Diese Migration (reversibel, Backup-Tag zuerst):
  1. Backup index -> {index}.bak_{DATE}
  2. Pro Tabellen-Zeile mit Linux-Prefix: Prefix -> Windows tauschen.
  3. DONE-Eintraege (status=DONE) der getauschten Zeilen -> _backlog_index_done.md
     auslagern (BL-178 done-Split); aktive/FREEZE/DECOMPOSED bleiben im Haupt-Index
     (mit Windows-Pfad).
  4. Cleaned index schreiben.

Idempotent: ein zweiter Lauf findet 0 Linux-Pfade.
Reversibel: Backup wiederherstellen.

Usage: py -3 .claude/scripts/migrate_backlog_index_linux_paths.py [--apply] [--date=YYYY-MM-DD]
       Ohne --apply: Dry-Run (zeigt Counts, schreibt NICHTS).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# BL-225-Befund 2026-06-01: die Linux-Pfade zeigen auf .../OmniCommand/ (OHNE 'DCS/'),
# nicht .../DCS/OmniCommand. Reiner Prefix-Tausch.
LINUX_PREFIX = "/home/uczen/Documents/OmniCommand"
WIN_PREFIX = "C:/Users/Administrator/Documents/OmniCommand"


def _resolve_vault_root() -> Path:
    import subprocess
    try:
        r = Path(__file__).parent / "resolve_vault_root.py"
        if r.is_file():
            p = subprocess.run([sys.executable, str(r)], capture_output=True, text=True, timeout=5)
            if p.returncode == 0 and p.stdout.strip():
                return Path(p.stdout.strip())
    except Exception:
        pass
    for cand in (WIN_PREFIX, LINUX_PREFIX):
        if Path(cand, "_backlog_index.md").is_file():
            return Path(cand)
    return Path(WIN_PREFIX)


def _status_of(row: str) -> str:
    # Markdown-Tabellenzeile: | BL-ID | Title | STATUS | Pfad | ... |
    cols = [c.strip() for c in row.split("|")]
    return cols[3].upper() if len(cols) > 3 else ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Schreibt Aenderungen (sonst Dry-Run)")
    ap.add_argument("--date", default="2026-06-01", help="Backup-Datum-Tag")
    args = ap.parse_args()

    vault = _resolve_vault_root()
    index_path = vault / "_backlog_index.md"
    done_path = vault / "_backlog_index_done.md"
    if not index_path.is_file():
        print(f"FAIL: {index_path} nicht gefunden")
        return 2

    lines = index_path.read_text(encoding="utf-8").split("\n")
    keep: list[str] = []
    moved_done: list[str] = []
    swapped = 0
    for line in lines:
        if LINUX_PREFIX in line:
            swapped += 1
            win_line = line.replace(LINUX_PREFIX, WIN_PREFIX)
            if _status_of(win_line) == "DONE":
                moved_done.append(win_line)
            else:
                keep.append(win_line)  # aktiv/FREEZE/DECOMPOSED bleiben (mit Windows-Pfad)
        else:
            keep.append(line)

    print(f"[BL-225 AK-A] Linux-Pfad-Zeilen gefunden: {swapped}")
    print(f"[BL-225 AK-A]   -> DONE ausgelagert nach _backlog_index_done.md: {len(moved_done)}")
    print(f"[BL-225 AK-A]   -> nicht-DONE im Haupt-Index (Windows-Pfad): {swapped - len(moved_done)}")

    if not args.apply:
        print("[BL-225 AK-A] DRY-RUN (kein --apply) — nichts geschrieben.")
        return 0

    # 1. Backup
    backup = index_path.with_name(f"_backlog_index.md.bak_{args.date}")
    backup.write_text("\n".join(lines), encoding="utf-8")
    print(f"[BL-225 AK-A] Backup: {backup}")

    # 2. done-File anhaengen (Header sichern falls leer)
    done_existing = done_path.read_text(encoding="utf-8") if done_path.is_file() else "# Backlog Index — DONE (ausgelagert, BL-178 done-Split)\n"
    if moved_done:
        done_new = done_existing.rstrip("\n") + "\n" + "\n".join(moved_done) + "\n"
        done_path.write_text(done_new, encoding="utf-8")
        print(f"[BL-225 AK-A] {len(moved_done)} DONE-Zeilen an {done_path.name} angehaengt.")

    # 3. Cleaned index schreiben
    index_path.write_text("\n".join(keep), encoding="utf-8")
    print(f"[BL-225 AK-A] Index bereinigt: {len(lines)} -> {len(keep)} Zeilen. 0 Linux-Pfade.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
