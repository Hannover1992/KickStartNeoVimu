#!/usr/bin/env python3
"""migrate_commands_to_meta_resolver.py — BL-193 AK-2 Command-Migration.

Rewrites hardcoded `.claude/meta/{path}` READ-references in command files to the
`{META}/{path}` resolver-token. `{META}` resolves via resolve_vault_meta.py
(vault-first → meta-cache → legacy `.claude/meta/` fallback, Tier 6 — NON-DOWNGRADING:
worst case `{META}/X` resolves to exactly the literal `.claude/meta/X` it replaced).

HOLISTISCH (BL-193 Compat-Pass): die Refs sind NICHT uniform. Bewusst LITERAL gelassen:
  1. DENYLIST_FILES — Commands die Meta SCHREIBEN/DEPLOYEN/BOOTSTRAPPEN (literal-Pfad ist
     dort Absicht): updateMeta, PrePR_Update_Meta, redeploy, init, *_help, stagePlanner,
     PT_seedImport/extract, meta_snapshot.
  2. stage_*.md — stagePlanner/redeploy GLOBBEN diese dynamisch aus {repo_path}/.claude/meta/
     implementation/ (INV repo-lokal, BL-168/224). Single-file-Resolver kann keinen Glob —
     diese tote Annahme NICHT zurueckdrehen.
  3. pr/active-pr.json, pr/routing.json — Runtime-State, kein Meta-Wissen.
  4. *.bak* — Backups, nicht live.

Usage:
  python migrate_commands_to_meta_resolver.py --dry-run   # nur Report (kein Schreiben)
  python migrate_commands_to_meta_resolver.py --apply     # in-place rewrite
"""
import argparse
import re
import sys
from pathlib import Path

COMMANDS_DIR = Path(__file__).parent.parent / "commands"

# .claude/meta/{path} — Pfad-Capture (Char-Klasse stoppt an ) " ` space etc.)
META_RE = re.compile(r"\.claude/meta/([A-Za-z0-9_./*-]+)")

# Commands die Meta SCHREIBEN/DEPLOYEN/BOOTSTRAPPEN — literal-Pfade sind Absicht.
DENYLIST_FILES = {
    "_I_updateMeta.md",          # schreibt/aktualisiert Meta-Dateien
    "_PrePR_Update_Meta.md",     # schreibt Meta aus PrePR-Erkenntnissen
    "_PrePR_Update_Meta",        # (Variation)
    "_redeploy.md",              # deployt .claude/meta/ in Worktrees (mkdir/cp literal)
    "_init.md",                  # Bootstrap
    "_help.md", "_I_help.md", "_SC_help.md", "_PrePR_help.md", "_help",  # Doku beschreibt Pfade
    "_IDF_berater_stagePlanner.md",  # stage_*.md repo-lokal Glob (INV-STAGE-1)
    "_PT_seedImport.md",         # Seed-Import schreibt
    "_PT_extract.md",            # Extract schreibt
    "_Pre_PR_orchestrate.md",    # Write-Target .claude/meta/codeKonvention/*.md (Z281) — literal
    "_project_mitose.md",        # cp -r .../.claude/meta/ -> Projekt-Klon-Deploy (literal)
}

# Pfad-Exclusions (egal in welchem File) — bleiben literal.
def is_excluded_path(rel_path: str) -> bool:
    if rel_path.startswith("implementation/stage_"):   # stage_*.md repo-lokal
        return True
    if rel_path.rstrip("/") == "implementation":       # bare stage-meta Dir: repo-lokaler CLI-Arg
        return True                                     # (--meta-dir/--target-dir; stage_*.md werden HIER gegloebt, INV-STAGE-1 #2)
    if "stage_*" in rel_path or "stage_N" in rel_path:
        return True
    if rel_path.startswith("pr/active-pr") or rel_path.startswith("pr/routing"):  # runtime state
        return True
    return False


def migrate_text(text: str):
    changes = 0
    skipped_paths = []

    def repl(m):
        nonlocal changes
        rel = m.group(1)
        if is_excluded_path(rel):
            skipped_paths.append(rel)
            return m.group(0)
        changes += 1
        return "{META}/" + rel

    new = META_RE.sub(repl, text)
    return new, changes, skipped_paths


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="in-place rewrite")
    ap.add_argument("--dry-run", action="store_true", help="nur Report")
    args = ap.parse_args()
    apply = args.apply and not args.dry_run
    if not args.apply and not args.dry_run:
        print("Bitte --dry-run ODER --apply angeben."); sys.exit(1)

    files = sorted(COMMANDS_DIR.glob("*.md"))
    tot_changes = tot_files = tot_skip = 0
    denylist_hits = []

    for f in files:
        if ".bak" in f.name:
            continue
        if f.name in DENYLIST_FILES:
            # zaehlen, aber NICHT migrieren (Transparenz)
            cnt = len(META_RE.findall(f.read_text(encoding="utf-8", errors="replace")))
            if cnt:
                denylist_hits.append((f.name, cnt))
            continue
        text = f.read_text(encoding="utf-8", errors="replace")
        new, changes, skipped = migrate_text(text)
        tot_skip += len(skipped)
        if changes > 0:
            tot_files += 1
            tot_changes += changes
            note = f"  ({len(skipped)} stage/runtime literal)" if skipped else ""
            print(f"{'APPLY' if apply else 'DRY '} {f.name}: {changes} -> {{META}}{note}")
            if apply:
                f.write_text(new, encoding="utf-8")

    print(f"\n{'='*60}")
    print(f"MIGRIERT: {tot_changes} READ-Refs in {tot_files} Command-Files {'(APPLIED)' if apply else '(DRY-RUN)'}")
    print(f"LITERAL (stage_*/runtime-Pfade): {tot_skip}")
    print(f"DENYLIST (Meta-Writer/Deploy/Help, bewusst literal): "
          f"{sum(c for _, c in denylist_hits)} Refs in {len(denylist_hits)} Files")
    for name, cnt in sorted(denylist_hits, key=lambda x: -x[1]):
        print(f"    - {name}: {cnt}")


if __name__ == "__main__":
    main()
