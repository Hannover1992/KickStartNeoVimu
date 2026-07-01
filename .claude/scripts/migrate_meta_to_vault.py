#!/usr/bin/env python3
"""migrate_meta_to_vault.py — Stub fuer BL-193 Phase B Command-Migration (BL-193 PL-8).

Dieses Skript ist STUB fuer die Folge-BL (BL-FOLGE-BL-193_command_migration).
Es soll automatisiert alle 61 Commands identifizieren die .claude/meta/ direkt
lesen und diese auf resolve_vault_meta.py Lookup umstellen.

Geplante Faehigkeiten (Phase B):
  1. Scan aller .claude/commands/**/*.md nach Meta-Pfad-Referenzen
  2. Klassifizierung: Local-Direktreferenz vs. bereits Vault-kompatibel
  3. Findings-Report als Migration-Plan
  4. Optionaler Auto-Apply (--apply Flag)

AKTUELLER STAND: Nur Findings-Scan implementiert (keine Auto-Apply-Logik).
"""
import os
import sys
import re
from pathlib import Path

META_PATTERN = re.compile(r'\.claude/meta/([^\s"\']+)')
COMMANDS_DIR = Path(__file__).parent.parent / "commands"


def scan_commands(commands_dir: Path) -> list[dict]:
    """Scan all command files for .claude/meta/ references."""
    findings = []
    for cmd_file in sorted(commands_dir.rglob("*.md")):
        try:
            content = cmd_file.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  SKIP (read error): {cmd_file} — {e}", file=sys.stderr)
            continue
        matches = META_PATTERN.findall(content)
        if matches:
            findings.append({
                "file": str(cmd_file.relative_to(COMMANDS_DIR.parent)),
                "references": list(set(matches)),
                "count": len(matches),
            })
    return findings


def main():
    print(f"=== BL-193 Meta-Migration Scan ===")
    print(f"Commands-Dir: {COMMANDS_DIR}")
    if not COMMANDS_DIR.exists():
        print(f"ERROR: commands dir not found: {COMMANDS_DIR}", file=sys.stderr)
        sys.exit(1)

    findings = scan_commands(COMMANDS_DIR)
    total_refs = sum(f["count"] for f in findings)

    print(f"\nFiles with .claude/meta/ references: {len(findings)}")
    print(f"Total references: {total_refs}")
    print()

    for f in findings:
        print(f"  {f['file']} ({f['count']} refs)")
        for ref in sorted(f["references"]):
            print(f"    - .claude/meta/{ref}")

    print(f"\nTODO: {len(findings)} commands need migration to resolve_vault_meta.py")
    print("Run with --apply to auto-migrate (NOT YET IMPLEMENTED — Phase B)")


if __name__ == "__main__":
    main()
