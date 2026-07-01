#!/usr/bin/env python3
"""test_meta_resolver_migration.py — BL-193 AK-2 Regression-Guard.

Codifiziert die Command-Meta-Migration als Invariante (forward-enforce):
  1. KEINE hardcoded `.claude/meta/{path}` READ-Refs mehr in Nicht-Denylist-Command-Files
     (ausser den bewussten stage_*/runtime-Exceptions). Neue Drift wird sofort rot.
  2. Denylist-Files (Meta-Writer/Deploy/Help) BEHALTEN ihre literalen Pfade
     (Write-Targets, Glob, cp — duerfen NICHT zu {META}-Token werden).
  3. stage_*.md bleibt repo-lokal literal (INV-STAGE-1, BL-168/224).
  4. {META}-Token sind tatsaechlich praesent (Migration applied).
"""
import re
from pathlib import Path

from migrate_commands_to_meta_resolver import (
    COMMANDS_DIR,
    DENYLIST_FILES,
    META_RE,
    is_excluded_path,
)


def _cmd_files():
    return [f for f in sorted(COMMANDS_DIR.glob("*.md")) if ".bak" not in f.name]


def test_no_hardcoded_meta_reads_outside_exceptions():
    leaks = []
    for f in _cmd_files():
        if f.name in DENYLIST_FILES:
            continue
        for rel in META_RE.findall(f.read_text(encoding="utf-8", errors="replace")):
            if not is_excluded_path(rel):
                leaks.append(f"{f.name}: .claude/meta/{rel}")
    assert leaks == [], f"Hardcoded Meta-READ-Refs (sollten {{META}}-Token sein): {leaks}"


def test_denylist_files_keep_literal_paths():
    # Meta-Writer/Deploy behalten literale .claude/meta/-Pfade (Write-Targets/Glob/cp).
    for name in ("_I_updateMeta.md", "_Pre_PR_orchestrate.md", "_IDF_berater_stagePlanner.md"):
        p = COMMANDS_DIR / name
        if p.exists():
            assert ".claude/meta/" in p.read_text(encoding="utf-8", errors="replace"), \
                f"{name} sollte literale .claude/meta/-Pfade behalten (Write/Glob)"


def test_stage_refs_stay_repo_local():
    # stagePlanner globt stage_*.md aus {repo_path}/.claude/meta/implementation/ (INV-STAGE-1).
    p = COMMANDS_DIR / "_IDF_berater_stagePlanner.md"
    if p.exists():
        txt = p.read_text(encoding="utf-8", errors="replace")
        assert ".claude/meta/implementation/stage_" in txt
        assert "{META}/implementation/stage_" not in txt, "stage_*.md darf NICHT tokenisiert sein"


def test_meta_token_present():
    total = sum(f.read_text(encoding="utf-8", errors="replace").count("{META}/") for f in _cmd_files())
    assert total >= 90, f"Erwartet >=90 {{META}}-Token nach Migration, gefunden {total}"
