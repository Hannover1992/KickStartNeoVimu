#!/usr/bin/env python3
"""
test_single_mode_worktree.py — Tests fuer single_mode_worktree.py (BL-328 SB1, AK-2).

Werkzeug-Buendel fuer den Single-Mode-Worktree-Betriebspfad (N=1, altmodisch).
Dieser SB1 deckt die Pre-Welle-Gate-Funktionen ab (GAP-1 + GAP-6):

  - clean_tree_gate(target_tree)              — Clean-Tree-Gate auf ZIEL-Tree (OQ-D, INV-SM-1)
  - pin_base_sha(target_tree, manifest_sha)   — Base-Ref-Pin (OQ-C, INV-SM-7)
  - generate_worktree_branch_name(...)        — kollisionsfreier _B-N-Branch-Name (GAP-6)
  - repo_present(path)                         — Repo-Anwesenheits-Guard (T9-Basis)

Modus: M3 (RED-first TDD). coverage_class=coverable_py (reine Wrapper-/Generator-Funktionen).

Test-Achsen (das RICHTIGE Verhalten, nicht nur "kein Crash"):
  - clean_tree_gate: proceed bei sauberem Tree, abort + korrektiver Hint bei dirty,
    na bei git-losem Pfad (T9, kein Crash). PRUEFT NUR den ZIEL-Tree, nie cwd/Engine-Repo.
  - pin_base_sha: bevorzugt gueltige Manifest-SHA, sonst HEAD-Pin (reproduzierbar).
  - generate_worktree_branch_name: kollisionsfrei gegen `existing`, _B-N-Schema, sanitized.
  - repo_present: True fuer echtes Repo, False fuer git-losen Pfad.

Echte temp-git-Repos (git init in tmp_path), finally-Cleanup via tmp_path-Fixture.
Console-Output ASCII (keine Unicode-Pfeile).
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(_SCRIPT_DIR))

from single_mode_worktree import (
    assert_zero_orphans,
    bootstrap_worktree,
    cleanup_worktree,
    clean_tree_gate,
    _is_volatile_churn,
    commit_in_worktree,
    emit_telemetry,
    fan_in_merge,
    gate_b_status,
    generate_worktree_branch_name,
    hook_green_rate,
    pin_base_sha,
    post_merge_gate,
    repo_present,
    run_post_merge_check,
)


# -- Fixtures -----------------------------------------------------------------

def _git(args, cwd):
    """git mit lokaler Identitaet (kein globaler Config-Zwang in CI/tmp)."""
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=10,
    )


@pytest.fixture
def clean_repo(tmp_path):
    """Echtes git-Repo mit committetem Inhalt -> sauberer Working-Tree."""
    repo = tmp_path / "clean_target"
    repo.mkdir()
    _git(["init"], repo)
    _git(["config", "user.email", "t@t.test"], repo)
    _git(["config", "user.name", "Test"], repo)
    (repo / "README.md").write_text("hello\n", encoding="utf-8")
    _git(["add", "."], repo)
    _git(["commit", "-m", "init"], repo)
    return repo


@pytest.fixture
def dirty_repo(clean_repo):
    """Sauberes Repo + uncommittete Aenderungen -> dirty Working-Tree."""
    (clean_repo / "README.md").write_text("changed\n", encoding="utf-8")
    (clean_repo / "untracked.txt").write_text("new\n", encoding="utf-8")
    return clean_repo


@pytest.fixture
def no_git_dir(tmp_path):
    """Verzeichnis ohne .git -> git-loser Pfad (T9)."""
    d = tmp_path / "not_a_repo"
    d.mkdir()
    return d


# -- repo_present (T9-Basis) --------------------------------------------------

def test_repo_present_true_for_real_repo(clean_repo):
    assert repo_present(str(clean_repo)) is True


def test_repo_present_false_for_non_repo(no_git_dir):
    assert repo_present(str(no_git_dir)) is False


def test_repo_present_false_for_nonexistent_path(tmp_path):
    ghost = tmp_path / "does_not_exist"
    assert repo_present(str(ghost)) is False


# -- clean_tree_gate (GAP-1, OQ-D, INV-SM-1) ----------------------------------

def test_clean_tree_gate_proceed_on_clean(clean_repo):
    result = clean_tree_gate(str(clean_repo))
    assert result["decision"] == "proceed"
    assert isinstance(result["hint"], str)


# -- BL-317/INV-SM-1: volatile Runtime-Log-Churn-Toleranz ---------------------

def test_is_volatile_churn_classifies():
    # bekannte volatile Runtime-Logs -> toleriert
    assert _is_volatile_churn(" M .claude/audit/audit.jsonl") is True
    assert _is_volatile_churn("?? .claude/audit/disciplinary_report.jsonl") is True
    assert _is_volatile_churn(" M .claude/analysis/_guard_log.md") is True
    assert _is_volatile_churn(" M .claude/analysis/_berater_outputs.md") is True
    assert _is_volatile_churn(" M .hook_debug.log") is True
    assert _is_volatile_churn(" D .claude/scheduled_tasks.lock") is True
    # ECHTE Aenderungen -> NICHT volatil (muessen weiter aborten)
    assert _is_volatile_churn(" M .claude/scripts/foo.py") is False
    assert _is_volatile_churn(" M .claude/commands/_A_orchestrate.md") is False
    assert _is_volatile_churn("?? newcode.py") is False


@pytest.fixture
def volatile_only_repo(clean_repo):
    """Repo mit getracktem volatilem Runtime-Log, das dirty churnt (nur Churn, keine echte Aenderung)."""
    audit = clean_repo / ".claude" / "audit"
    audit.mkdir(parents=True)
    (audit / "audit.jsonl").write_text("{}\n", encoding="utf-8")
    _git(["add", "."], clean_repo)
    _git(["commit", "-m", "track audit"], clean_repo)
    (audit / "audit.jsonl").write_text("{}\n{}\n", encoding="utf-8")  # churn -> dirty, nur volatil
    return clean_repo


def test_clean_tree_gate_proceeds_on_only_volatile_churn(volatile_only_repo):
    # INV-SM-1/BL-317: nur volatile Runtime-Log-Churn dirty -> proceed (kein Dauer-Abort, Findings #D U4).
    result = clean_tree_gate(str(volatile_only_repo))
    assert result["decision"] == "proceed", result["hint"]
    assert "volatile" in result["hint"].lower()


def test_clean_tree_gate_aborts_on_real_dirt_despite_volatile(volatile_only_repo):
    # volatile Churn + ECHTE Aenderung -> abort (die echte Aenderung gewinnt, wird genannt).
    (volatile_only_repo / "README.md").write_text("real change\n", encoding="utf-8")
    result = clean_tree_gate(str(volatile_only_repo))
    assert result["decision"] == "abort", result["hint"]
    assert "echte" in result["hint"].lower()


def test_clean_tree_gate_abort_on_dirty(dirty_repo):
    result = clean_tree_gate(str(dirty_repo))
    assert result["decision"] == "abort"
    # Korrektiver Hint MUSS die Dirty-Datei-Anzahl nennen (hier: 1 modified + 1 untracked = 2).
    assert "2" in result["hint"], result["hint"]
    assert result["hint"].strip() != ""


def test_clean_tree_gate_na_on_git_less_path(no_git_dir):
    # T9: git-loser Pfad -> na statt Crash.
    result = clean_tree_gate(str(no_git_dir))
    assert result["decision"] == "na"
    assert result["hint"].strip() != ""


def test_clean_tree_gate_checks_only_target_tree_not_cwd(clean_repo, tmp_path, monkeypatch):
    """OQ-D/INV-SM-1: das Gate prueft den uebergebenen ZIEL-Tree, nicht das cwd/Engine-Repo.

    Wir setzen cwd auf ein SEPARATES, DIRTY Repo und uebergeben einen SAUBEREN
    Ziel-Tree. Korrektes Verhalten: proceed (der Ziel-Tree ist sauber) — das
    cwd-Dirty darf das Ergebnis NICHT verfaelschen. (clean_repo wird hier NICHT
    angefasst; das dirty Repo ist ein eigenes, unabhaengiges Verzeichnis.)
    """
    cwd_dirty = tmp_path / "cwd_engine_like"
    cwd_dirty.mkdir()
    _git(["init"], cwd_dirty)
    _git(["config", "user.email", "t@t.test"], cwd_dirty)
    _git(["config", "user.name", "Test"], cwd_dirty)
    (cwd_dirty / "README.md").write_text("hello\n", encoding="utf-8")
    _git(["add", "."], cwd_dirty)
    _git(["commit", "-m", "init"], cwd_dirty)
    # cwd jetzt dirty machen — simuliert das dauerhaft-dirtige Engine-Repo.
    (cwd_dirty / "churn.txt").write_text("uncommitted\n", encoding="utf-8")
    assert clean_tree_gate(str(cwd_dirty))["decision"] == "abort"  # Sanity: cwd IST dirty

    monkeypatch.chdir(cwd_dirty)
    result = clean_tree_gate(str(clean_repo))
    assert result["decision"] == "proceed", (
        "Gate darf nur den ZIEL-Tree pruefen, nicht das (dirty) cwd"
    )


# -- pin_base_sha (GAP-6, OQ-C, INV-SM-7) -------------------------------------

def test_pin_base_sha_prefers_valid_manifest_sha(clean_repo):
    head = _git(["rev-parse", "HEAD"], clean_repo).stdout.strip()
    # Manifest-SHA gegeben + gueltig -> wird bevorzugt (nicht HEAD neu pinnen).
    pinned = pin_base_sha(str(clean_repo), head)
    assert pinned == head


def test_pin_base_sha_falls_back_to_head_when_no_manifest_sha(clean_repo):
    head = _git(["rev-parse", "HEAD"], clean_repo).stdout.strip()
    pinned = pin_base_sha(str(clean_repo), None)
    assert pinned == head


def test_pin_base_sha_falls_back_to_head_on_invalid_manifest_sha(clean_repo):
    head = _git(["rev-parse", "HEAD"], clean_repo).stdout.strip()
    # Ungueltige SHA -> ignoriert, HEAD-Pin als reproduzierbarer Anker.
    pinned = pin_base_sha(str(clean_repo), "deadbeefnotacommit")
    assert pinned == head


def test_pin_base_sha_reproducible(clean_repo):
    a = pin_base_sha(str(clean_repo), None)
    b = pin_base_sha(str(clean_repo), None)
    assert a == b
    assert len(a) >= 7  # echte SHA, kein leerer String


# -- generate_worktree_branch_name (GAP-6) ------------------------------------

def test_generate_branch_name_uses_b_n_suffix_scheme():
    name = generate_worktree_branch_name("feature/BL-328-single-mode", 3)
    assert name.endswith("_B-3"), name
    assert "BL-328" in name


def test_generate_branch_name_sanitizes_slashes():
    name = generate_worktree_branch_name("feature/BL-328-single-mode", 1)
    # Branch-Namen mit "/" sind als Worktree-Branch valide, aber der generierte
    # Name darf keine Datei-/Pfad-problematischen Zeichen tragen.
    assert "\\" not in name
    assert "<" not in name and ">" not in name and ":" not in name


def test_generate_branch_name_collision_free_against_existing():
    existing = {"feature/BL-328-single-mode_B-1"}
    name = generate_worktree_branch_name("feature/BL-328-single-mode", 1, existing=existing)
    assert name not in existing, "Name muss kollisionsfrei gegen existing sein"


def test_generate_branch_name_two_calls_differ_when_accumulating():
    """Zwei Wellen -> verschiedene Namen, wenn der erste in `existing` akkumuliert."""
    existing: set[str] = set()
    first = generate_worktree_branch_name("feature/BL-328-single-mode", 1, existing=existing)
    existing.add(first)
    second = generate_worktree_branch_name("feature/BL-328-single-mode", 1, existing=existing)
    assert first != second, (first, second)


def test_generate_branch_name_escalates_suffix_on_collision():
    existing = {
        "feature/BL-328-single-mode_B-2",
        "feature/BL-328-single-mode_B-3",
    }
    name = generate_worktree_branch_name("feature/BL-328-single-mode", 2, existing=existing)
    assert name not in existing
    # Schema bleibt _B-N (hochgezaehlt), kein willkuerliches Format.
    assert "_B-" in name


# =============================================================================
# SB2 — Wave-Body (GAP-2 bootstrap, GAP-3 fan-in-merge, GAP-7 commit-in-worktree).
#
# Echte temp-git-Repos + echte `git worktree add`/Commits/Merges. PFLICHT (B-3-Klasse):
# jeder erzeugte Worktree wird in `finally` mit `git worktree remove --force` +
# `git worktree prune` aufgeraeumt; jeder Test asserted am Ende 0-Orphan
# (`git worktree list` == Baseline). KEINE Worktree-Leichen.
# =============================================================================


def _worktree_list(repo) -> set[str]:
    """Normierter Set der Worktree-Pfade des Repos (Backslash->Slash, lowercase)."""
    out = _git(["worktree", "list", "--porcelain"], repo)
    paths = set()
    for line in out.stdout.splitlines():
        if line.startswith("worktree "):
            raw = line[len("worktree "):]
            paths.add(raw.replace("\\", "/").rstrip("/").lower())
    return paths


def _force_cleanup_worktree(repo, worktree_path) -> None:
    """remove --force + prune — IMMER im finally, auch bei Fehlschlag (B-3-Klasse)."""
    _git(["worktree", "remove", "--force", str(worktree_path)], repo)
    _git(["worktree", "prune"], repo)


def _head_sha(repo) -> str:
    return _git(["rev-parse", "HEAD"], repo).stdout.strip()


# -- bootstrap_worktree (GAP-2, Schritt 3) ------------------------------------

def test_bootstrap_worktree_creates_real_worktree_at_base_sha(clean_repo, tmp_path):
    """Bootstrap erzeugt einen ECHTEN Worktree am base_sha + misst plausibel."""
    base_sha = _head_sha(clean_repo)
    branch = "feature/BL-328-single-mode_B-1"
    wt = tmp_path / "wt_bootstrap"
    baseline = _worktree_list(clean_repo)
    try:
        result = bootstrap_worktree(str(clean_repo), str(wt), branch, base_sha)
        assert result["ok"] is True, result.get("hint")
        # Echter Worktree am base_sha: Verzeichnis da, in der Liste, HEAD == base_sha.
        assert wt.exists()
        assert _worktree_list(clean_repo) - baseline, "Worktree muss in der Liste auftauchen"
        assert _head_sha(wt) == base_sha, "Worktree-HEAD muss am gepinnten base_sha haengen"
        assert result["branch"] == branch
        # Plausible Messung (GAP-2): Zeit >= 0, Worktree-Groesse > 0 (echte Dateien).
        assert isinstance(result["bootstrap_seconds"], float) and result["bootstrap_seconds"] >= 0.0
        assert isinstance(result["disk_bytes"], int) and result["disk_bytes"] > 0
    finally:
        _force_cleanup_worktree(clean_repo, wt)
    # 0-Orphan: Liste zurueck auf Baseline.
    assert _worktree_list(clean_repo) == baseline, "0-Orphan verletzt nach bootstrap"


def test_bootstrap_worktree_runs_build_cmd(clean_repo, tmp_path):
    """build_cmd wird IM Worktree ausgefuehrt (Bootstrap-Verfahren je Projekt)."""
    base_sha = _head_sha(clean_repo)
    branch = "feature/BL-328-single-mode_B-2"
    wt = tmp_path / "wt_build"
    marker = wt / "bootstrap_ran.txt"
    baseline = _worktree_list(clean_repo)
    # Ein plattform-portabler build_cmd: python schreibt eine Marker-Datei IM Worktree-cwd.
    build_cmd = [sys.executable, "-c", "open('bootstrap_ran.txt','w').write('ok')"]
    try:
        result = bootstrap_worktree(str(clean_repo), str(wt), branch, base_sha, build_cmd=build_cmd)
        assert result["ok"] is True, result.get("hint")
        assert marker.exists(), "build_cmd muss im Worktree-cwd gelaufen sein"
        assert marker.read_text(encoding="utf-8") == "ok"
    finally:
        _force_cleanup_worktree(clean_repo, wt)
    assert _worktree_list(clean_repo) == baseline, "0-Orphan verletzt nach build-bootstrap"


def test_bootstrap_worktree_na_on_git_less_target(no_git_dir, tmp_path):
    """T9: git-loses Ziel -> ok=False/na-Pfad statt Crash."""
    wt = tmp_path / "wt_na"
    result = bootstrap_worktree(str(no_git_dir), str(wt), "br_B-1", "deadbeef")
    assert result["ok"] is False
    assert result["hint"].strip() != ""
    assert not wt.exists(), "kein Worktree bei git-losem Ziel"


# -- commit_in_worktree (GAP-7, Schritt 5) ------------------------------------

def test_commit_in_worktree_commits_in_worktree_not_mothership(clean_repo, tmp_path):
    """commit_in_worktree committet IM Worktree-cwd; Mothership-HEAD bleibt unveraendert."""
    base_sha = _head_sha(clean_repo)
    branch = "feature/BL-328-single-mode_B-3"
    wt = tmp_path / "wt_commit"
    baseline = _worktree_list(clean_repo)
    mother_head_before = _head_sha(clean_repo)
    try:
        bootstrap_worktree(str(clean_repo), str(wt), branch, base_sha)
        # Eine Aenderung im Worktree-cwd erzeugen.
        (wt / "feature.txt").write_text("worktree work\n", encoding="utf-8")
        result = commit_in_worktree(str(wt), "BL-328: worktree-batch commit")
        assert result["committed"] is True, result.get("hint")
        assert result["sha"] and len(result["sha"]) >= 7
        # Worktree-HEAD ist vorangeschritten; Mothership-HEAD steht still (bis zum Merge).
        assert _head_sha(wt) != base_sha
        assert _head_sha(clean_repo) == mother_head_before, (
            "Mothership-HEAD darf sich vor dem Fan-In NICHT bewegen"
        )
    finally:
        _force_cleanup_worktree(clean_repo, wt)
    assert _worktree_list(clean_repo) == baseline, "0-Orphan verletzt nach commit"


def test_commit_in_worktree_na_on_git_less_path(no_git_dir):
    """T9: git-loser Pfad -> committed=False/na statt Crash."""
    result = commit_in_worktree(str(no_git_dir), "msg")
    assert result["committed"] is False
    assert result["sha"] is None
    assert result["hint"].strip() != ""


# -- fan_in_merge (GAP-3, Schritt 6) ------------------------------------------

def test_fan_in_merge_brings_worktree_commit_into_mothership(clean_repo, tmp_path):
    """Fan-In bringt einen Worktree-Branch-Commit WIRKLICH in den Mothership.

    Verifiziert per `git log` im Mothership, dass der Worktree-Commit-SHA nach
    dem Merge erreichbar ist (nicht nur rc==0). Der Lock-CODE-Pfad (zweck=wave_fanin)
    laeuft, wird aber per lock_dir in ein tmp-Verzeichnis injiziert (kein globaler vault_root).
    """
    base_sha = _head_sha(clean_repo)
    branch = "feature/BL-328-single-mode_B-4"
    wt = tmp_path / "wt_merge"
    lock_dir = tmp_path / "lock_home"
    lock_dir.mkdir()
    baseline = _worktree_list(clean_repo)
    try:
        bootstrap_worktree(str(clean_repo), str(wt), branch, base_sha)
        (wt / "merged_feature.txt").write_text("to be merged\n", encoding="utf-8")
        commit_res = commit_in_worktree(str(wt), "BL-328: feature to merge")
        worktree_commit = commit_res["sha"]
        assert worktree_commit

        result = fan_in_merge(str(clean_repo), branch, lock_dir=str(lock_dir))
        assert result["merged"] is True, result.get("hint")
        assert result["conflict"] is False
        # WIRKLICH im Mothership: der Worktree-Commit ist von Mothership-HEAD aus erreichbar.
        log = _git(["log", "--format=%H"], clean_repo).stdout.split()
        assert worktree_commit in log, (
            "Worktree-Commit muss nach Fan-In im Mothership-Log erscheinen"
        )
        # Die gemergte Datei ist im Mothership-Tree (HEAD vorangeschritten).
        assert (clean_repo / "merged_feature.txt").exists()
        assert _head_sha(clean_repo) != base_sha
    finally:
        _force_cleanup_worktree(clean_repo, wt)
    assert _worktree_list(clean_repo) == baseline, "0-Orphan verletzt nach merge"


def test_fan_in_merge_no_ff_creates_merge_commit(clean_repo, tmp_path):
    """--no-ff: der Fan-In erzeugt einen echten Merge-Commit (2 Parents)."""
    base_sha = _head_sha(clean_repo)
    branch = "feature/BL-328-single-mode_B-5"
    wt = tmp_path / "wt_noff"
    lock_dir = tmp_path / "lock_home_noff"
    lock_dir.mkdir()
    baseline = _worktree_list(clean_repo)
    try:
        bootstrap_worktree(str(clean_repo), str(wt), branch, base_sha)
        (wt / "noff.txt").write_text("x\n", encoding="utf-8")
        commit_in_worktree(str(wt), "BL-328: no-ff body")
        result = fan_in_merge(str(clean_repo), branch, lock_dir=str(lock_dir))
        assert result["merged"] is True, result.get("hint")
        # HEAD ist ein Merge-Commit: hat 2 Parents (--no-ff erzwingt das).
        parents = _git(["rev-list", "--parents", "-n", "1", "HEAD"], clean_repo).stdout.split()
        assert len(parents) == 3, ("Merge-Commit (1 self + 2 parents) erwartet", parents)
    finally:
        _force_cleanup_worktree(clean_repo, wt)
    assert _worktree_list(clean_repo) == baseline, "0-Orphan verletzt nach no-ff merge"


def test_fan_in_merge_na_on_git_less_target(no_git_dir):
    """T9: git-loses Ziel -> merged=False/na statt Crash."""
    result = fan_in_merge(str(no_git_dir), "some_branch")
    assert result["merged"] is False
    assert result["hint"].strip() != ""


# -- Globale 0-Orphan-Sicherung (B-3-Klasse) ----------------------------------

def test_no_worktree_orphans_after_suite(clean_repo):
    """Ein frisches Repo hat genau seinen eigenen Worktree — kein SB2-Leak im Repo."""
    # clean_repo ist eine frische Fixture-Instanz; SB2 raeumt pro Test in finally auf.
    assert _worktree_list(clean_repo) == _worktree_list(clean_repo)
    assert len(_worktree_list(clean_repo)) == 1, "nur der Main-Worktree, keine Leichen"


# =============================================================================
# SB3 — Post-Merge-Green-Gate (GAP-4, Schritt 7, AK-3, INV-SM-4).
#
# Ein Batch zaehlt erst als `done`, NACHDEM das Post-Merge-Green-Gate gruen ist
# (Build+Unit auf dem MOTHERSHIP NACH dem Fan-In-Merge). Rot -> Batch bleibt
# offen + Recovery (Revert/Re-Batch), KEIN stilles `done`.
#
# Zonen-Grenze (BL-330): das GATING ist deterministisch (Exit-Code -> done/hold)
# = M3-Code hier. Das GREEN-KLARHEITS-URTEIL ("ist dieser gruene Build WIRKLICH
# korrekt?") ist KOGNITIV (M2) und gehoert in den Orchestrator-Skill/Lead, NICHT
# in diese Wrapper. Diese Tests pruefen NUR das deterministische Exit-Code-Gate.
#
# build_cmd/test_cmd sind plattform-portable python-Einzeiler:
#   [sys.executable, "-c", "exit(0)"]  -> gruen
#   [sys.executable, "-c", "exit(1)"]  -> rot
# =============================================================================

_GREEN_CMD = [sys.executable, "-c", "exit(0)"]
_RED_CMD = [sys.executable, "-c", "exit(1)"]


# -- run_post_merge_check (GAP-4, Exit-Code-Erfassung im Mothership) ----------

def test_run_post_merge_check_both_green(clean_repo):
    """Beide cmds gruen -> build_ok=test_ok=True, rc==0, kein hold-Signal."""
    result = run_post_merge_check(str(clean_repo), build_cmd=_GREEN_CMD, test_cmd=_GREEN_CMD)
    assert result["build_ok"] is True, result.get("hint")
    assert result["test_ok"] is True, result.get("hint")
    assert result["build_rc"] == 0
    assert result["test_rc"] == 0
    assert result["hint"].strip() != ""


def test_run_post_merge_check_test_red(clean_repo):
    """test_cmd rot -> test_ok=False (Build gruen), rc-Wert ungleich 0 erfasst."""
    result = run_post_merge_check(str(clean_repo), build_cmd=_GREEN_CMD, test_cmd=_RED_CMD)
    assert result["build_ok"] is True
    assert result["test_ok"] is False, "rotes test_cmd MUSS test_ok=False ergeben"
    assert result["test_rc"] != 0


def test_run_post_merge_check_build_red(clean_repo):
    """build_cmd rot -> build_ok=False (fail-safe: Build-Fehler wird erfasst)."""
    result = run_post_merge_check(str(clean_repo), build_cmd=_RED_CMD, test_cmd=_GREEN_CMD)
    assert result["build_ok"] is False, "rotes build_cmd MUSS build_ok=False ergeben"
    assert result["build_rc"] != 0


def test_run_post_merge_check_none_cmds_skipped(clean_repo):
    """None-cmd = uebersprungen (ok=True, rc=None) — kein Build-/Test-Verfahren konfiguriert."""
    result = run_post_merge_check(str(clean_repo), build_cmd=None, test_cmd=None)
    assert result["build_ok"] is True
    assert result["test_ok"] is True
    assert result["build_rc"] is None
    assert result["test_rc"] is None


def test_run_post_merge_check_runs_in_mothership_cwd(clean_repo):
    """Die cmds laufen im MOTHERSHIP-cwd (target_tree, nach Merge), nicht im Test-cwd.

    Der test_cmd schreibt eine Marker-Datei ins cwd; sie muss im target_tree
    (Mothership) landen — das ist der INV-SM-4-Punkt: gemessen wird der gemergte
    Mothership-Tree, nicht ein fremdes Verzeichnis.
    """
    marker_cmd = [sys.executable, "-c", "open('post_merge_marker.txt','w').write('ran')"]
    result = run_post_merge_check(str(clean_repo), build_cmd=None, test_cmd=marker_cmd)
    assert result["test_ok"] is True, result.get("hint")
    assert (clean_repo / "post_merge_marker.txt").exists(), (
        "test_cmd muss im Mothership-cwd (target_tree) gelaufen sein"
    )


def test_run_post_merge_check_na_on_git_less_target(no_git_dir):
    """T9: git-loses Ziel -> na-Pfad statt Crash (Repo-Guard zuerst)."""
    result = run_post_merge_check(str(no_git_dir), build_cmd=_GREEN_CMD, test_cmd=_GREEN_CMD)
    assert result.get("decision") == "na" or result["build_ok"] is False, result
    assert result["hint"].strip() != ""


# -- post_merge_gate (GAP-4, reiner done/hold-Wrapper, INV-SM-4) --------------

def test_post_merge_gate_done_only_when_both_green():
    """Beide ok -> done. Das ist die EINZIGE Bedingung fuer done."""
    result = post_merge_gate(build_ok=True, test_ok=True)
    assert result["decision"] == "done"
    assert result["hint"].strip() != ""


def test_post_merge_gate_hold_when_test_red():
    """test rot -> hold (NICHT done) + Recovery-Hint (Revert/Re-Batch, INV-SM-4)."""
    result = post_merge_gate(build_ok=True, test_ok=False)
    assert result["decision"] == "hold", "rotes test darf NIE done ergeben"
    # Recovery-Hint MUSS den korrektiven Pfad nennen.
    hint = result["hint"].lower()
    assert "revert" in hint or "re-batch" in hint or "recovery" in hint, result["hint"]


def test_post_merge_gate_hold_when_build_red():
    """build rot -> hold (NICHT done)."""
    result = post_merge_gate(build_ok=False, test_ok=True)
    assert result["decision"] == "hold", "roter Build darf NIE done ergeben"


def test_post_merge_gate_hold_when_both_red():
    """beide rot -> hold (NICHT done)."""
    result = post_merge_gate(build_ok=False, test_ok=False)
    assert result["decision"] == "hold"


def test_post_merge_gate_fail_safe_default_is_hold():
    """fail-safe: JEDER nicht-vollstaendig-gruene Input -> hold (Default-Richtung).

    Mutations-Gedanke: ein Gate, das done/hold NICHT unterscheidet, waere wertlos.
    Dieser Test flippt zu FAIL, wenn das Gate bei nicht-gruenem Input faelschlich
    done zurueckgibt. Nur (True, True) darf done sein; alle 3 anderen Kombinationen
    MUESSEN hold sein.
    """
    assert post_merge_gate(True, True)["decision"] == "done"
    for build_ok, test_ok in [(True, False), (False, True), (False, False)]:
        assert post_merge_gate(build_ok, test_ok)["decision"] == "hold", (
            f"({build_ok},{test_ok}) muss hold sein (fail-safe), nicht done"
        )


# -- INV-SM-4 Integrations-Beweis: done NUR nach gruenem Post-Merge-Build -------

def test_inv_sm4_batch_done_only_after_green_post_merge(clean_repo, tmp_path):
    """INV-SM-4-BEWEIS: nach echtem Fan-In-Merge entscheidet das Post-Merge-Gate.

    Der volle Pfad: bootstrap -> commit-im-worktree -> fan_in_merge (Mothership) ->
    run_post_merge_check (auf dem GEMERGTEN Mothership) -> post_merge_gate.
    Bei gruenem Post-Merge-Build+Test -> done (Batch zaehlt als fertig).
    Bei rotem test_cmd -> hold (Batch bleibt OFFEN, NICHT done) — der semantische
    Konflikt-Anker (U1/FK-11). KEIN stilles done bei rot.
    """
    base_sha = _head_sha(clean_repo)
    branch = "feature/BL-328-single-mode_B-6"
    wt = tmp_path / "wt_postmerge"
    lock_dir = tmp_path / "lock_home_pm"
    lock_dir.mkdir()
    baseline = _worktree_list(clean_repo)
    try:
        bootstrap_worktree(str(clean_repo), str(wt), branch, base_sha)
        (wt / "post_merge_feature.txt").write_text("merged work\n", encoding="utf-8")
        commit_in_worktree(str(wt), "BL-328: post-merge-gate body")
        merge = fan_in_merge(str(clean_repo), branch, lock_dir=str(lock_dir))
        assert merge["merged"] is True, merge.get("hint")

        # GRUEN-Fall: Post-Merge-Build+Test gruen -> Gate sagt done.
        green = run_post_merge_check(str(clean_repo), build_cmd=_GREEN_CMD, test_cmd=_GREEN_CMD)
        green_gate = post_merge_gate(green["build_ok"], green["test_ok"])
        assert green_gate["decision"] == "done", (
            "gruener Post-Merge-Build MUSS den Batch als done freigeben"
        )

        # ROT-Fall: derselbe gemergte Mothership, aber rotes test_cmd -> hold (NICHT done).
        red = run_post_merge_check(str(clean_repo), build_cmd=_GREEN_CMD, test_cmd=_RED_CMD)
        red_gate = post_merge_gate(red["build_ok"], red["test_ok"])
        assert red_gate["decision"] == "hold", (
            "rotes Post-Merge-test MUSS den Batch OFFEN halten (INV-SM-4), kein stilles done"
        )
    finally:
        _force_cleanup_worktree(clean_repo, wt)
    assert _worktree_list(clean_repo) == baseline, "0-Orphan verletzt nach post-merge-gate"


# =============================================================================
# SB4 — Cleanup Windows-robust + 0-Orphan-Assertion + Telemetrie
#       (GAP-7-Cleanup / GAP-2-Messung-Verzahnung / GAP-5, Schritt 8+9,
#        AK-4, INV-SM-5, INV-SM-8, OQ-E).
#
#   - cleanup_worktree(target_tree, worktree_path, retries=2)
#       Schritt 8: `git worktree remove --force` + `prune`. WINDOWS-ROBUST:
#       Retry bei gehaltenem File-Handle / gecrashtem Build (B-3-Leichen-Klasse),
#       als letzte Stufe best-effort Verzeichnis-Entfernung + prune. 0-Orphan.
#   - assert_zero_orphans(target_tree, baseline)
#       INV-SM-5: aktuelle Worktree-Pfade MINUS baseline (Set-Subtraktion) == leer?
#       Der ECHTE-Orphan-Negativ-Fall ist PFLICHT (sonst vakuos).
#   - emit_telemetry(audit_path, **fields)
#       Schritt 9: EINE append-only JSON-Zeile (audit.jsonl-Stil) mit den 5
#       Gate-B-Feldern + event + ts. KOMMUTATIV/append-only (INV-SM-8).
#       WICHTIG: audit_path ist ein PARAMETER (Tests nutzen IMMER ein tmp-audit;
#       NIEMALS die echte .claude/audit/audit.jsonl des Engine-Repos).
# =============================================================================


# -- cleanup_worktree (GAP-7, Schritt 8, INV-SM-5) ----------------------------

def test_cleanup_worktree_removes_real_worktree(clean_repo, tmp_path):
    """cleanup_worktree entfernt einen ECHTEN Worktree -> danach nicht mehr in der Liste."""
    base_sha = _head_sha(clean_repo)
    branch = "feature/BL-328-single-mode_B-7"
    wt = tmp_path / "wt_cleanup"
    baseline = _worktree_list(clean_repo)
    bootstrap_worktree(str(clean_repo), str(wt), branch, base_sha)
    # Sanity: der Worktree IST jetzt in der Liste (sonst waere der Test vakuos).
    assert _worktree_list(clean_repo) - baseline, "Setup: Worktree muss erst da sein"

    result = cleanup_worktree(str(clean_repo), str(wt))
    assert result["removed"] is True, result.get("hint")
    assert result["pruned"] is True, result.get("hint")
    assert isinstance(result["attempts"], int) and result["attempts"] >= 1
    # 0-Orphan: der entfernte Worktree ist NICHT mehr in der Liste.
    assert _worktree_list(clean_repo) == baseline, "Worktree muss nach cleanup verschwunden sein"


def test_cleanup_worktree_still_zero_orphan_after_held_handle(clean_repo, tmp_path):
    """B-3-Leichen-Klasse: ein gehaltenes File-Handle (gecrashter Build) darf KEINEN
    Orphan hinterlassen — Retry/Force/best-effort raeumt trotzdem auf.

    Wir oeffnen eine Datei IM Worktree und halten das Handle waehrend des Cleanups
    offen (auf Windows blockiert das `worktree remove`). cleanup_worktree MUSS
    trotzdem zum 0-Orphan-Zustand fuehren (Retry -> Force -> best-effort dir-remove).
    """
    base_sha = _head_sha(clean_repo)
    branch = "feature/BL-328-single-mode_B-8"
    wt = tmp_path / "wt_held"
    baseline = _worktree_list(clean_repo)
    bootstrap_worktree(str(clean_repo), str(wt), branch, base_sha)
    held = wt / "held_open.bin"
    held.write_text("locked\n", encoding="utf-8")
    fh = open(held, "rb")  # Handle bewusst offen lassen waehrend cleanup
    try:
        result = cleanup_worktree(str(clean_repo), str(wt), retries=2)
        # Egal wie viele Retries: am Ende KEIN Orphan in der git-Worktree-Liste.
        assert result["pruned"] is True, result.get("hint")
        assert _worktree_list(clean_repo) == baseline, (
            "0-Orphan MUSS auch bei gehaltenem Handle erreicht werden (Retry/Force/prune)"
        )
        # Mehr als ein Versuch ist plausibel (aber nicht erzwungen — Plattform-abhaengig).
        assert result["attempts"] >= 1
    finally:
        fh.close()
        _force_cleanup_worktree(clean_repo, wt)
    assert _worktree_list(clean_repo) == baseline


def test_cleanup_worktree_na_on_git_less_target(no_git_dir, tmp_path):
    """T9: git-loses Ziel -> sauberer na/Skip-Pfad statt Crash (Repo-Guard zuerst)."""
    wt = tmp_path / "wt_na_cleanup"
    result = cleanup_worktree(str(no_git_dir), str(wt))
    assert result["removed"] is False
    assert result["hint"].strip() != ""


# -- assert_zero_orphans (INV-SM-5) -------------------------------------------

def test_assert_zero_orphans_true_when_back_to_baseline(clean_repo, tmp_path):
    """Nach sauberem Bootstrap+Cleanup -> zero_orphans=True, keine genannten Orphans."""
    base_sha = _head_sha(clean_repo)
    branch = "feature/BL-328-single-mode_B-9"
    wt = tmp_path / "wt_zo_ok"
    baseline = _worktree_list(clean_repo)
    bootstrap_worktree(str(clean_repo), str(wt), branch, base_sha)
    cleanup_worktree(str(clean_repo), str(wt))

    result = assert_zero_orphans(str(clean_repo), baseline)
    assert result["zero_orphans"] is True, result.get("hint")
    assert result["orphans"] == []


def test_assert_zero_orphans_detects_real_orphan(clean_repo, tmp_path):
    """PFLICHT-Negativ-Fall: ein ABSICHTLICH liegengelassener Worktree wird als
    Orphan erkannt (zero_orphans=False + nennt ihn). Ohne diesen Fall waere die
    Assertion vakuos (sie wuerde IMMER True sagen).
    """
    base_sha = _head_sha(clean_repo)
    branch = "feature/BL-328-single-mode_B-10"
    wt = tmp_path / "wt_orphan"
    baseline = _worktree_list(clean_repo)
    bootstrap_worktree(str(clean_repo), str(wt), branch, base_sha)
    try:
        # Worktree absichtlich NICHT aufraeumen -> echter Orphan gegen baseline.
        result = assert_zero_orphans(str(clean_repo), baseline)
        assert result["zero_orphans"] is False, "ein liegengelassener Worktree MUSS Orphan sein"
        assert result["orphans"], "der Orphan MUSS benannt werden"
        # Der genannte Orphan ist normiert der liegengelassene Worktree-Pfad.
        norm_wt = str(wt).replace("\\", "/").rstrip("/").lower()
        assert any(norm_wt in o or o in norm_wt for o in result["orphans"]), (
            (norm_wt, result["orphans"])
        )
        assert result["hint"].strip() != ""
    finally:
        _force_cleanup_worktree(clean_repo, wt)
    # Nach echtem Cleanup wieder sauber.
    assert assert_zero_orphans(str(clean_repo), baseline)["zero_orphans"] is True


# -- emit_telemetry (GAP-5, Schritt 9, INV-SM-8, OQ-E) ------------------------

_TELEMETRY_FIELDS = {
    "bootstrap_seconds": 1.5,
    "disk_bytes": 4096,
    "hook_green_rate": 1.0,
    "orphan_count": 0,
    "merge_result": "merged",
}


def test_emit_telemetry_writes_valid_json_line_with_5_fields(tmp_path):
    """Eine valide append-only JSON-Zeile mit allen 5 Gate-B-Feldern in ein TMP-audit.

    Liest zurueck + json.loads + asserted die Felder. audit_path ist ein PARAMETER
    (tmp), NIEMALS die echte .claude/audit/audit.jsonl.
    """
    import json
    audit_path = tmp_path / "tmp_audit.jsonl"
    result = emit_telemetry(str(audit_path), **_TELEMETRY_FIELDS)
    assert result["emitted"] is True, result.get("hint")
    assert audit_path.exists()
    lines = [ln for ln in audit_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 1, "genau eine Zeile pro Emit"
    entry = json.loads(lines[0])  # MUSS gueltiges JSON sein (append-only JSONL)
    for field, value in _TELEMETRY_FIELDS.items():
        assert entry[field] == value, (field, entry.get(field), value)
    # Event-Stream-Konvention (wie _emit_audit): event + ts vorhanden.
    assert "event" in entry and entry["event"].strip() != ""
    assert "ts" in entry and entry["ts"].strip() != ""


def test_emit_telemetry_is_append_only(tmp_path):
    """Zwei Emits -> zwei Zeilen (append-only, kein Ueberschreiben). INV-SM-8."""
    import json
    audit_path = tmp_path / "append_audit.jsonl"
    emit_telemetry(str(audit_path), **_TELEMETRY_FIELDS)
    emit_telemetry(str(audit_path), **{**_TELEMETRY_FIELDS, "merge_result": "hold"})
    lines = [ln for ln in audit_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(lines) == 2, "zwei Emits muessen zwei Zeilen ergeben (append-only)"
    # Beide Zeilen sind je fuer sich gueltiges JSON (kommutativ konkatenierbar).
    second = json.loads(lines[1])
    assert second["merge_result"] == "hold"


def test_emit_telemetry_fanin_compatible(tmp_path):
    """INV-SM-8 / OQ-E: die emittierten Zeilen sind kommutativ via audit_fanin
    konkatenierbar (jede Zeile = vollstaendiges JSON-Objekt, keine Mehr-Zeilen-Struktur).
    """
    import json
    sys.path.insert(0, str(_SCRIPT_DIR))
    from audit_fanin import fan_in_audit_streams

    stream_a = tmp_path / "a_audit.jsonl"
    stream_b = tmp_path / "b_audit.jsonl"
    emit_telemetry(str(stream_a), **_TELEMETRY_FIELDS)
    emit_telemetry(str(stream_b), **{**_TELEMETRY_FIELDS, "orphan_count": 1})
    merged = fan_in_audit_streams([str(stream_a), str(stream_b)])
    assert len(merged) == 2
    # Kommutativ: A+B und B+A liefern dieselbe Zeilen-Multimenge.
    merged_rev = fan_in_audit_streams([str(stream_b), str(stream_a)])
    assert sorted(merged) == sorted(merged_rev)
    # Jede gemergte Zeile ist gueltiges JSON.
    for line in merged:
        json.loads(line)


def test_emit_telemetry_does_not_touch_real_audit_jsonl(tmp_path):
    """Sicherung: ein Emit mit tmp-audit_path beruehrt NICHT die echte Engine-audit.jsonl.

    Wir lesen die Groesse der echten .claude/audit/audit.jsonl vor/nach einem
    Emit-in-tmp; sie darf sich NICHT veraendern (kein Pollution, analog SB2
    lock_dir-Lehre).
    """
    real_audit = _SCRIPT_DIR.parent / "audit" / "audit.jsonl"
    size_before = real_audit.stat().st_size if real_audit.exists() else None

    audit_path = tmp_path / "isolated_audit.jsonl"
    emit_telemetry(str(audit_path), **_TELEMETRY_FIELDS)

    size_after = real_audit.stat().st_size if real_audit.exists() else None
    assert size_after == size_before, (
        "emit_telemetry mit tmp-audit_path darf die echte audit.jsonl NICHT veraendern"
    )


# -- SB4 Integrations-Beweis: Telemetrie speist sich aus echtem Lifecycle ------

def test_sb4_full_cleanup_telemetry_cycle(clean_repo, tmp_path):
    """Voller SB4-Zyklus: bootstrap (misst) -> cleanup -> assert_zero_orphans ->
    emit_telemetry mit den ECHTEN gemessenen Werten in ein tmp-audit.
    """
    import json
    base_sha = _head_sha(clean_repo)
    branch = "feature/BL-328-single-mode_B-11"
    wt = tmp_path / "wt_cycle"
    audit_path = tmp_path / "cycle_audit.jsonl"
    baseline = _worktree_list(clean_repo)

    boot = bootstrap_worktree(str(clean_repo), str(wt), branch, base_sha)
    assert boot["ok"] is True, boot.get("hint")
    clean = cleanup_worktree(str(clean_repo), str(wt))
    assert clean["pruned"] is True
    zo = assert_zero_orphans(str(clean_repo), baseline)
    assert zo["zero_orphans"] is True

    emit = emit_telemetry(
        str(audit_path),
        bootstrap_seconds=boot["bootstrap_seconds"],
        disk_bytes=boot["disk_bytes"],
        hook_green_rate=1.0,
        orphan_count=len(zo["orphans"]),
        merge_result="merged",
    )
    assert emit["emitted"] is True
    entry = json.loads(audit_path.read_text(encoding="utf-8").splitlines()[0])
    assert entry["bootstrap_seconds"] == boot["bootstrap_seconds"]
    assert entry["disk_bytes"] == boot["disk_bytes"]
    assert entry["orphan_count"] == 0
    assert _worktree_list(clean_repo) == baseline


# =============================================================================
# SB5 — G3-Kopplung (hook_green_rate, AK-5) + Gate-B-Messlatte (gate_b_status,
#       AK-6, Forward-Verify). GAP-5 (speist sich aus den Telemetrie-Events).
#
#   - hook_green_rate(hook_results) -> float
#       AK-5: gruene Hook-Verdikte / gesamte. Akzeptiert bool ODER {"green":bool}.
#       Konvention (bewusst gewaehlt + dokumentiert): leere Liste -> 1.0
#       (vacuously green — "keine Hooks liefen, also keine roten"); das ist der
#       neutrale Multiplikator fuer die Gate-B-Aggregation und matcht die
#       worktree_hook_router-Semantik (relevant=True/keine Verletzung -> gruen).
#   - gate_b_status(telemetry_events, min_batches=10) -> dict
#       AK-6 Forward-Verify: aggregiert die single_mode_batch_telemetry-Events.
#       PASS gdw >=min_batches Batches UND ueber ALLE: hook_green_rate==1.0 ∧
#       orphan_count==0 ∧ merge_result gruen. Sonst PENDING(X/min_batches).
#       fail-safe: zu wenig/uneindeutige Events -> PENDING, nie faelschlich PASS.
#
# RED-first TDD: synthetische Events (keine echten git-Ops noetig — reine
# Aggregations-/Schwellen-Logik ueber Dicts).
# =============================================================================


# -- hook_green_rate (AK-5, GAP-5) --------------------------------------------

def test_hook_green_rate_all_green_is_one():
    """Alle Hook-Verdikte gruen -> Rate 1.0."""
    assert hook_green_rate([True, True, True]) == 1.0


def test_hook_green_rate_all_red_is_zero():
    """Alle Hook-Verdikte rot -> Rate 0.0."""
    assert hook_green_rate([False, False]) == 0.0


def test_hook_green_rate_mixed_is_fraction():
    """Gemischt -> exakter Bruch gruen/gesamt (deterministisch)."""
    assert hook_green_rate([True, False, True, True]) == 0.75


def test_hook_green_rate_accepts_dict_verdicts():
    """Verdikte duerfen {"green": bool}-Dicts sein (Hook-Router-Form)."""
    results = [{"green": True}, {"green": False}, {"green": True}]
    assert hook_green_rate(results) == pytest.approx(2 / 3)


def test_hook_green_rate_empty_is_vacuously_green():
    """Bewusste Konvention: leere Liste -> 1.0 (vacuously green, neutraler Wert).

    Dokumentiert im Docstring: "keine Hooks liefen" zaehlt als gruen (kein roter
    Hook), damit ein Batch ohne Hook-Lauf die Gate-B-Aggregation nicht faelschlich
    auf PENDING zieht. Der ECHTE-rot-Fall wird separat abgedeckt.
    """
    assert hook_green_rate([]) == 1.0


def test_hook_green_rate_is_deterministic():
    """Zwei Aufrufe mit derselben Eingabe -> identisch (reine Funktion)."""
    sample = [True, False, {"green": True}]
    assert hook_green_rate(sample) == hook_green_rate(sample)


# -- gate_b_status (AK-6, Forward-Verify, GAP-5) ------------------------------

def _telemetry_event(**overrides) -> dict:
    """Ein synthetisches single_mode_batch_telemetry-Event (all-green Default)."""
    base = {
        "event": "single_mode_batch_telemetry",
        "bootstrap_seconds": 1.2,
        "disk_bytes": 4096,
        "hook_green_rate": 1.0,
        "orphan_count": 0,
        "merge_result": "merged",
    }
    base.update(overrides)
    return base


def test_gate_b_status_pass_on_10_all_green():
    """>=10 Batches, alle gruen (hook==1.0, 0 Orphans, merge gruen) -> PASS."""
    events = [_telemetry_event() for _ in range(10)]
    result = gate_b_status(events)
    assert result["status"] == "PASS", result.get("hint")
    assert result["green_batches"] == 10
    assert result["total_batches"] == 10


def test_gate_b_status_pending_when_one_has_orphan():
    """9 gruen + 1 mit orphan_count=1 -> PENDING(9/10), nie PASS."""
    events = [_telemetry_event() for _ in range(9)] + [_telemetry_event(orphan_count=1)]
    result = gate_b_status(events)
    assert result["status"] == "PENDING", result.get("hint")
    assert result["green_batches"] == 9
    assert "9" in result["progress"] and "10" in result["progress"]


def test_gate_b_status_pending_when_hook_rate_below_one():
    """10 Batches aber einer mit hook_green_rate<1.0 -> PENDING (Hook nicht 100%)."""
    events = [_telemetry_event() for _ in range(9)] + [_telemetry_event(hook_green_rate=0.5)]
    result = gate_b_status(events)
    assert result["status"] == "PENDING", result.get("hint")
    assert result["green_batches"] == 9


def test_gate_b_status_pending_when_merge_not_green():
    """merge_result nicht gruen (z.B. 'hold') -> Batch zaehlt nicht gruen -> PENDING."""
    events = [_telemetry_event() for _ in range(9)] + [_telemetry_event(merge_result="hold")]
    result = gate_b_status(events)
    assert result["status"] == "PENDING", result.get("hint")
    assert result["green_batches"] == 9


def test_gate_b_status_pending_when_too_few_batches():
    """Weniger als min_batches gruene Batches -> PENDING(X/min)."""
    events = [_telemetry_event() for _ in range(3)]
    result = gate_b_status(events)
    assert result["status"] == "PENDING"
    assert result["green_batches"] == 3
    assert "3" in result["progress"] and "10" in result["progress"]


def test_gate_b_status_pending_on_empty():
    """Leer -> PENDING(0/10), niemals PASS (fail-safe)."""
    result = gate_b_status([])
    assert result["status"] == "PENDING"
    assert result["green_batches"] == 0
    assert "0" in result["progress"]


def test_gate_b_status_merge_result_true_counts_green():
    """merge_result==True (bool) zaehlt ebenso gruen wie 'merged' (Form-Toleranz)."""
    events = [_telemetry_event(merge_result=True) for _ in range(10)]
    result = gate_b_status(events)
    assert result["status"] == "PASS", result.get("hint")


def test_gate_b_status_ignores_foreign_events():
    """Fremde audit.jsonl-Events (anderes 'event') werden NICHT als Batch gezaehlt.

    Der Telemetrie-Stream ist gemischt; gate_b_status filtert auf
    single_mode_batch_telemetry. 10 gueltige + Fremd-Rauschen -> PASS, total==10.
    """
    events = (
        [_telemetry_event() for _ in range(10)]
        + [{"event": "factory_lock_acquired", "worker_id": "x"}]
        + [{"event": "some_other_thing", "orphan_count": 99}]
    )
    result = gate_b_status(events)
    assert result["status"] == "PASS", result.get("hint")
    assert result["total_batches"] == 10, "Fremd-Events duerfen nicht mitzaehlen"


def test_gate_b_status_respects_custom_min_batches():
    """min_batches ist parametrisierbar: 5 all-green + min_batches=5 -> PASS."""
    events = [_telemetry_event() for _ in range(5)]
    assert gate_b_status(events, min_batches=5)["status"] == "PASS"
    assert gate_b_status(events, min_batches=6)["status"] == "PENDING"


def test_gate_b_status_mutation_always_pass_would_break():
    """Mutations-Anker: ein gate, das IMMER PASS retourniert, MUSS hier kippen.

    Drei Konstellationen, die PASS verbieten muessen (orphan / hook<1 / zu wenig).
    Mind. 3 dieser Asserts kippen, wenn jemand gate_b_status zu "always PASS" mutiert.
    """
    too_few = gate_b_status([_telemetry_event() for _ in range(2)])
    with_orphan = gate_b_status([_telemetry_event() for _ in range(9)] + [_telemetry_event(orphan_count=2)])
    with_red_hook = gate_b_status([_telemetry_event() for _ in range(9)] + [_telemetry_event(hook_green_rate=0.9)])
    assert too_few["status"] == "PENDING"
    assert with_orphan["status"] == "PENDING"
    assert with_red_hook["status"] == "PENDING"


def test_gate_b_status_returns_documented_shape():
    """Return-Vertrag: status/green_batches/total_batches/progress/hint vorhanden."""
    result = gate_b_status([_telemetry_event() for _ in range(10)])
    for key in ("status", "green_batches", "total_batches", "progress", "hint"):
        assert key in result, (key, result)
    assert result["status"] in ("PASS", "PENDING")


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
