#!/usr/bin/env python3
"""BL-065 AK-14 / RF-10: Numerisches Compliance-Audit-Script.

Misst fuer 6 Artefakt-Typen das Verhaeltnis vault_count / (vault_count + claude_count).
Schwellwerte (gestaffelt, OQ-G02 Option B):
- Model, Spec, Gap, K-Score, Implementation: >= 95%
- Crumbs: >= 80% (BL-045 Case-Study Baseline war 3%)

Exit 0: alle Schwellwerte erreicht (PASS)
Exit 1: mindestens ein Typ unter Schwelle (FAIL)

Idempotent: Mehrfach-Laeufe produzieren identische Ausgabe.
Seiteneffekt-frei: Keine Datei-Writes, keine Env-Modifikationen.
"""
import os
import sys
from pathlib import Path

# Konfiguration
# FALLBACK: Linux-Default fuer DCS_VAULT_ROOT, falls Env-Var nicht gesetzt.
# Auf Windows wird die Env-Var via resolve_vault_root.py / current_context.py gesetzt.
VAULT_ROOT = os.environ.get("DCS_VAULT_ROOT", "/home/uczen/Documents/DCS")
CLAUDE_ROOT = "."  # Current working directory

THRESHOLDS = {
    "Model": 0.95,
    "Spec": 0.95,
    "Gap": 0.95,
    "K-Score": 0.95,
    "Implementation": 0.95,
    "Crumbs": 0.80,  # Staffelung: Crumbs sind oft ephemer
}

# Subfolder-Map fuer Vault
VAULT_SUBFOLDERS = {
    "Model": "2_Model",
    "Spec": "3_Spec",
    "Gap": "5_Gap",
    "K-Score": "4_K-Score",
    "Implementation": "Implementation",
    "Crumbs": "Crumbs",
}

# Legacy-Pfade in .claude/
CLAUDE_LEGACY_PATHS = {
    "Model": ".claude/models",
    "Spec": ".claude/specs",
    "Gap": ".claude/analysis/synthese",  # *-GAP.md
    "K-Score": ".claude/analysis/synthese",  # *-K-SCORE*.md
    "Implementation": ".claude/analysis/synthese",  # Implementation-Logs
    "Crumbs": ".claude/crumbs",
}

# Exclude-Patterns (nicht mitzaehlen)
EXCLUDE_PATTERNS = [
    "_archive_BL-065",
    ".claude/analysis/drafts",
    ".claude/analysis/exploration",
    "__pycache__",
]

# Pattern pro Typ fuer .claude/-Legacy
CLAUDE_PATTERNS = {
    "Model": "*_Model.md",
    "Spec": "*_Spec.md",
    "Gap": "*-GAP.md",
    "K-Score": "*-K-SCORE*.md",
    "Implementation": "*-IMPL*.md",
    "Crumbs": "*.md",
}


def count_vault_files(typ: str) -> int:
    """Zaehlt Dateien im Vault fuer einen Typ (deterministisch sortiert)."""
    subfolder = VAULT_SUBFOLDERS[typ]
    backlog_root = Path(VAULT_ROOT) / "OmniCommand" / "Backlog"
    if not backlog_root.exists():
        return 0
    count = 0
    # sortierte Iteration fuer Idempotenz
    for bl_dir in sorted(backlog_root.iterdir()):
        if not bl_dir.is_dir():
            continue
        if any(excl in str(bl_dir) for excl in EXCLUDE_PATTERNS):
            continue
        typ_dir = bl_dir / subfolder
        if typ_dir.exists() and typ_dir.is_dir():
            count += sum(1 for _ in sorted(typ_dir.rglob("*.md")))
    return count


def count_claude_files(typ: str) -> int:
    """Zaehlt Dateien unter .claude/ fuer einen Typ (deterministisch sortiert)."""
    base = Path(CLAUDE_LEGACY_PATHS[typ])
    if not base.exists():
        return 0
    pattern = CLAUDE_PATTERNS[typ]
    count = 0
    for f in sorted(base.rglob(pattern)):
        if any(excl in str(f) for excl in EXCLUDE_PATTERNS):
            continue
        count += 1
    return count


def main() -> int:
    print("BL-065 Compliance Audit Script")
    print("=" * 70)
    print(f"Vault Root: {VAULT_ROOT}")
    print(f"Claude Root: {Path(CLAUDE_ROOT).resolve()}")
    print("=" * 70)
    print(f"{'Typ':<16} {'Vault':>8} {'Claude':>8} {'Compl %':>10} {'Thresh':>8} {'Status':>8}")
    print("-" * 70)

    all_pass = True
    for typ in THRESHOLDS.keys():
        vault_count = count_vault_files(typ)
        claude_count = count_claude_files(typ)
        total = vault_count + claude_count
        compliance = (vault_count / total * 100) if total > 0 else 100.0
        threshold = THRESHOLDS[typ] * 100
        status = "PASS" if compliance >= threshold else "FAIL"
        if status == "FAIL":
            all_pass = False
        print(f"{typ:<16} {vault_count:>8} {claude_count:>8} {compliance:>9.1f}% {threshold:>7.0f}% {status:>8}")

    print("-" * 70)
    overall = "PASS" if all_pass else "FAIL"
    print(f"{'OVERALL':<44} {overall:>8}")
    print()

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
