#!/usr/bin/env python3
"""BL-065 AK-11 / INV-01: vault-routing.json ist SSoT fuer Pfade.

Test: Keine hartcodierten absoluten Linux-Pfade zu /home/uczen/Documents/DCS in den
Commands (ausser in explizit markierten # FALLBACK:-Bloecken).
"""
import sys
import re
from pathlib import Path

SCAN_DIRS = [
    ".claude/commands",
    ".claude/scripts",
]

# V12 (2026-05-08): Archive + Test-Self-Reference ausschliessen
EXCLUDE_DIRS = {"_archive_BL-065"}
EXCLUDE_FILES = {"test_no_hardcoded_vault_paths.py",
                 "migrate_backlog_index_linux_paths.py"}  # BL-225 AK-A: Migrations-Tool braucht den Linux-Pattern als Swap-Quelle

HARDCODED_PATTERNS = [
    r'/home/uczen/Documents/DCS',
    r'/home/[^/]+/Documents/DCS',
]

def is_excluded(path):
    if path.name in EXCLUDE_FILES:
        return True
    parts = set(path.parts)
    if parts & EXCLUDE_DIRS:
        return True
    return False

def scan_file(path):
    """Return list of unmarked hardcoded path lines."""
    content = Path(path).read_text(encoding='utf-8')
    lines = content.split("\n")
    violations = []
    for i, line in enumerate(lines):
        # V12 (2026-05-08): Pro Zeile maximal EIN Treffer (vorher: Doppel-
        # zaehlung weil 2 Patterns die gleiche Zeile matchen — Linux-Default-Pfad
        # matcht beide Regex-Muster).
        matched = False
        for pattern in HARDCODED_PATTERNS:
            if matched:
                break
            if re.search(pattern, line):
                # Pruefe ob innerhalb +/- 2 Zeilen ein FALLBACK-Marker steht.
                # V12 (2026-05-08): "Default Linux:" / "Default Windows:" gelten
                # als Auto-Marker — sie signalisieren explizit eine Fallback-Kette
                # in Vertrags-Dokumentation (vgl. _W_fetch, _W_help).
                window = lines[max(0, i-2):i+3]
                fallback_markers = (
                    "# FALLBACK:", "# primaerquelle", "primaerquellen:",
                    "primaerquelle_gelesen", "Default Linux:", "Default Windows:",
                    "Linux-Default", "Windows-Default",
                )
                if any(m in w for m in fallback_markers for w in window):
                    matched = True  # legit fallback — skip rest of patterns
                    continue
                violations.append((i+1, line.strip()[:100]))
                matched = True
    return violations

def _vault_index_files():
    """BL-225 AK-F: kanonische Vault-Index-Files (liegen AUSSERHALB .claude/), via resolve_vault_root."""
    import subprocess
    try:
        r = Path(__file__).parent / "resolve_vault_root.py"
        if r.is_file():
            p = subprocess.run([sys.executable, str(r)], capture_output=True, text=True, timeout=5)
            if p.returncode == 0 and p.stdout.strip():
                v = Path(p.stdout.strip())
                return [v / "_backlog_index.md", v / "_backlog_index_done.md"]
    except Exception:
        pass
    return []


def main():
    total_violations = 0
    # BL-225 AK-F: kanonischen Vault-Index mitscannen (genau die Klasse — Linux-Pfad im Index —
    # die dem Guard bisher entging, weil er nur .claude/ scannte).
    for idx in _vault_index_files():
        if idx.is_file():
            violations = scan_file(idx)
            if violations:
                total_violations += len(violations)
                print(f"FAIL: {idx}: {len(violations)} hardcoded path(s)")
                for lineno, line in violations[:3]:
                    print(f"  Z.{lineno}: {line}")
                if len(violations) > 3:
                    print(f"  ... und {len(violations) - 3} weitere")
    for scan_dir in SCAN_DIRS:
        base = Path(scan_dir)
        if not base.exists():
            continue
        for md_file in list(base.rglob("*.md")) + list(base.rglob("*.py")):
            if is_excluded(md_file):
                continue
            violations = scan_file(md_file)
            if violations:
                total_violations += len(violations)
                print(f"FAIL: {md_file}: {len(violations)} hardcoded path(s)")
                for lineno, line in violations[:3]:
                    print(f"  Z.{lineno}: {line}")
                if len(violations) > 3:
                    print(f"  ... und {len(violations) - 3} weitere")
    if total_violations > 0:
        print(f"\nFAIL: {total_violations} hardcoded absolute paths (outside FALLBACK markers)")
        sys.exit(1)
    print(f"\nPASS: No hardcoded absolute paths outside FALLBACK markers")
    sys.exit(0)

if __name__ == "__main__":
    main()
