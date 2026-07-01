"""
BL-445 Regression-Tests: volatile Append-Logs duerfen NICHT git-getrackt sein.

AK-1: git rm --cached der 3 volatilen Files.
AK-4: nach Untrack sind die Files strukturell nicht im Merge-Set.

RED-Zustand (vor Fix): test_audit_jsonl_not_tracked, test_guard_log_not_tracked,
  test_berater_outputs_not_tracked, test_merge_stable_no_tracked_volatile_logs FALLEN.
GREEN-Zustand (nach git rm --cached x3): alle Tests gruen.
"""

import subprocess
import pathlib
import pytest

# Robuste Ermittlung des Repo-Roots via git rev-parse
def _get_repo_root() -> pathlib.Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=pathlib.Path(__file__).parent,
        capture_output=True,
        text=True,
        check=True,
    )
    return pathlib.Path(result.stdout.strip())


REPO_ROOT = _get_repo_root()
GITIGNORE = REPO_ROOT / ".gitignore"

VOLATILE_FILES = [
    ".claude/audit/audit.jsonl",
    ".claude/analysis/_guard_log.md",
    ".claude/analysis/_berater_outputs.md",
]


def git_ls_files(rel_path: str) -> str:
    """Ruft git ls-files fuer einen relativen Pfad auf; gibt Stdout-Strip zurueck."""
    result = subprocess.run(
        ["git", "ls-files", rel_path],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# ---------------------------------------------------------------------------
# AK-1: Einzelne not-tracked-Tests (werden per Promptvorgabe explizit benannt)
# ---------------------------------------------------------------------------

def test_audit_jsonl_not_tracked():
    """AK-1: .claude/audit/audit.jsonl darf NICHT git-getrackt sein.

    RED vor Fix: git ls-files gibt den Pfad zurueck (nicht leer).
    GREEN nach 'git rm --cached .claude/audit/audit.jsonl'.
    """
    tracked = git_ls_files(".claude/audit/audit.jsonl")
    assert tracked == "", (
        f".claude/audit/audit.jsonl ist noch git-getrackt: git ls-files gibt '{tracked}' zurueck. "
        "Fix: git rm --cached .claude/audit/audit.jsonl"
    )


def test_guard_log_not_tracked():
    """AK-1: .claude/analysis/_guard_log.md darf NICHT git-getrackt sein.

    RED vor Fix: git ls-files gibt den Pfad zurueck (nicht leer).
    GREEN nach 'git rm --cached .claude/analysis/_guard_log.md'.
    """
    tracked = git_ls_files(".claude/analysis/_guard_log.md")
    assert tracked == "", (
        f".claude/analysis/_guard_log.md ist noch git-getrackt: git ls-files gibt '{tracked}' zurueck. "
        "Fix: git rm --cached .claude/analysis/_guard_log.md"
    )


def test_berater_outputs_not_tracked():
    """AK-1: .claude/analysis/_berater_outputs.md darf NICHT git-getrackt sein.

    RED vor Fix: git ls-files gibt den Pfad zurueck (nicht leer).
    GREEN nach 'git rm --cached .claude/analysis/_berater_outputs.md'.
    """
    tracked = git_ls_files(".claude/analysis/_berater_outputs.md")
    assert tracked == "", (
        f".claude/analysis/_berater_outputs.md ist noch git-getrackt: git ls-files gibt '{tracked}' zurueck. "
        "Fix: git rm --cached .claude/analysis/_berater_outputs.md"
    )


# ---------------------------------------------------------------------------
# AK-1: gitignore-Coverage-Tests (sollten bereits GRUEN sein — Eintraege vorhanden)
# ---------------------------------------------------------------------------

def test_audit_jsonl_in_gitignore():
    """AK-1: .gitignore muss .claude/audit/audit.jsonl abdecken.

    Prueft auf direkten Substring-Match im .gitignore.
    (Eintrag existiert bereits seit BL-317 — sollte GRUEN sein.)
    """
    gitignore_text = GITIGNORE.read_text(encoding="utf-8")
    assert ".claude/audit/audit.jsonl" in gitignore_text, (
        ".claude/audit/audit.jsonl fehlt in .gitignore — Eintrag ergaenzen."
    )


def test_volatile_logs_gitignore_covered():
    """AK-1: alle 3 volatilen Pfade muessen in .gitignore abgedeckt sein.

    Prueft Substring-Match fuer jeden Pfad.
    (Eintraege existieren bereits — sollten GRUEN sein.)
    """
    gitignore_text = GITIGNORE.read_text(encoding="utf-8")
    missing = []
    for rel_path in VOLATILE_FILES:
        base = pathlib.PurePosixPath(rel_path).name
        if rel_path not in gitignore_text and base not in gitignore_text:
            missing.append(rel_path)
    assert not missing, (
        "Folgende volatile Files fehlen in .gitignore:\n"
        + "\n".join(missing)
    )


# ---------------------------------------------------------------------------
# AK-4: kombinierter Merge-Stabilitaets-Beweis
# ---------------------------------------------------------------------------

def test_merge_stable_no_tracked_volatile_logs():
    """AK-4: KEINE der 3 volatilen Files darf in git ls-files erscheinen.

    Beweis: ungetrackte Files sind nicht im git-Merge-Set — kein 'git merge develop'
    kann sie mischen. Cross-Worktree-Trail-Kontamination ist strukturell ausgeschlossen.

    RED vor Fix: alle 3 Files sind getrackt (im Merge-Set).
    GREEN nach 'git rm --cached' x3: git ls-files leer fuer alle 3.
    """
    tracked_any = []
    for rel_path in VOLATILE_FILES:
        tracked = git_ls_files(rel_path)
        if tracked:
            tracked_any.append(f"{rel_path}: '{tracked}'")
    assert not tracked_any, (
        "Noch getrackte volatile Files — Merge-Kontamination weiterhin moeglich:\n"
        + "\n".join(tracked_any)
        + "\nFix: git rm --cached fuer alle obigen Files (AK-1), dann commit."
    )
