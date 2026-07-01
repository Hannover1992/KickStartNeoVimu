#!/usr/bin/env python3
"""
test_merge_seam.py — BL-425 batch_1 RED tests fuer merge_seam.py.

Pflicht-Testfaelle (alle MUESSEN ohne merge_seam.py fehlschlagen — ModuleNotFoundError = RED):
  1.  test_mergeable_check_clean        — merge-tree clean + status leer -> CLEAN
  2.  test_mergeable_check_conflict     — merge-tree Konflikt-Marker -> CONFLICT
  3.  test_mergeable_check_dirty        — status nicht-leer -> DIRTY
  4.  test_merge_exec_no_force          — merge_exec baut NIE '--force'/'-f' in den Befehl
  5.  test_aufruf_guard_clean_only      — do_merge_if_clean ruft merge_exec NUR bei CLEAN
  6.  test_aufruf_guard_conflict_noop   — do_merge_if_clean ruft merge_exec NICHT bei CONFLICT
  7.  test_aufruf_guard_dirty_noop      — do_merge_if_clean ruft merge_exec NICHT bei DIRTY
  8.  test_conflict_to_pl_conflict      — conflict_to_pl(CONFLICT,...) liefert dict mit Pflichtfeldern
  9.  test_conflict_to_pl_fail_loud     — conflict_to_pl(CONFLICT, files=[], ...) wirft ValueError/AssertionError
  10. test_conflict_to_pl_hold_true     — hold==True in PL-Item-Draft
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch, call
from typing import Any

import pytest

# RED: merge_seam.py existiert NICHT — dieser Import-Fail IST der erwartete Fehlschlag.
from merge_seam import (
    mergeable_check,
    merge_exec,
    conflict_to_pl,
    do_merge_if_clean,
    is_ff_safe,
    advance_ref_ff_safe,
)


# ---------------------------------------------------------------------------
# Helfer: gemockte subprocess-runner Fabrik
# ---------------------------------------------------------------------------

def _make_runner(merge_tree_stdout: str = "", merge_tree_returncode: int = 0,
                 status_stdout: str = "", status_returncode: int = 0):
    """Gibt einen Mock-Runner zurueck der alle git-Calls abhaengig vom Sub-Befehl beantwortet."""
    def _run(cmd, **kwargs):
        result = MagicMock()
        if "merge-tree" in cmd:
            result.stdout = merge_tree_stdout
            result.returncode = merge_tree_returncode
        elif "status" in cmd:
            result.stdout = status_stdout
            result.returncode = status_returncode
        else:
            result.stdout = ""
            result.returncode = 0
        return result
    return _run


# ---------------------------------------------------------------------------
# Test 1: mergeable_check -> CLEAN (merge-tree sauber, status leer)
# ---------------------------------------------------------------------------

def test_mergeable_check_clean() -> None:
    """CLEAN wenn merge-tree kein Konflikt-Marker + status --porcelain leer."""
    runner = _make_runner(
        merge_tree_stdout="Fast-forward",
        status_stdout="",
    )
    result = mergeable_check("feature/my-branch", "develop", run=runner)
    assert result == "CLEAN"


# ---------------------------------------------------------------------------
# Test 2: mergeable_check -> CONFLICT (merge-tree Konflikt-Marker)
# ---------------------------------------------------------------------------

def test_mergeable_check_conflict() -> None:
    """CONFLICT wenn merge-tree Ausgabe Konflikt-Marker enthaelt."""
    runner = _make_runner(
        merge_tree_stdout="<<<<<<< HEAD\nsome code\n=======\nother code\n>>>>>>> develop",
        status_stdout="",
    )
    result = mergeable_check("feature/my-branch", "develop", run=runner)
    assert result == "CONFLICT"


# ---------------------------------------------------------------------------
# Test 3: mergeable_check -> DIRTY (status nicht-leer)
# ---------------------------------------------------------------------------

def test_mergeable_check_dirty() -> None:
    """DIRTY wenn git status --porcelain nicht-leer (uncommitted changes im Working Tree)."""
    runner = _make_runner(
        merge_tree_stdout="Fast-forward",
        status_stdout=" M some_file.py\n",
    )
    result = mergeable_check("feature/my-branch", "develop", run=runner)
    assert result == "DIRTY"


# ---------------------------------------------------------------------------
# Test 4: merge_exec enthaelt NIE '--force'/'-f'
# ---------------------------------------------------------------------------

def test_merge_exec_no_force() -> None:
    """merge_exec baut NIE '--force' oder '-f' in den git-Befehl ein."""
    captured_cmds: list[Any] = []

    def _capturing_runner(cmd, **kwargs):
        captured_cmds.append(list(cmd))
        result = MagicMock()
        result.stdout = ""
        result.returncode = 0
        return result

    merge_exec("feature/my-branch", "develop", run=_capturing_runner)

    assert len(captured_cmds) >= 1, "merge_exec muss mindestens einen git-Befehl ausfuehren"
    for cmd in captured_cmds:
        assert "--force" not in cmd, f"--force gefunden in: {cmd}"
        assert "-f" not in cmd, f"-f gefunden in: {cmd}"


# ---------------------------------------------------------------------------
# Test 5: do_merge_if_clean ruft merge_exec NUR bei CLEAN
# ---------------------------------------------------------------------------

def test_aufruf_guard_clean_only() -> None:
    """Aufruf-Guard: do_merge_if_clean ruft merge_exec GENAU EINMAL bei CLEAN-Verdikt."""
    merge_exec_mock = MagicMock(return_value={"status": "merged"})

    # CLEAN-Pfad: merge_exec MUSS aufgerufen werden
    result = do_merge_if_clean(
        verdict="CLEAN",
        current_branch="feature/my-branch",
        merge_target="develop",
        merge_exec_fn=merge_exec_mock,
    )
    merge_exec_mock.assert_called_once()


# ---------------------------------------------------------------------------
# Test 6: do_merge_if_clean ruft merge_exec NICHT bei CONFLICT
# ---------------------------------------------------------------------------

def test_aufruf_guard_conflict_noop() -> None:
    """Aufruf-Guard: do_merge_if_clean ruft merge_exec NICHT bei CONFLICT."""
    merge_exec_mock = MagicMock()

    do_merge_if_clean(
        verdict="CONFLICT",
        current_branch="feature/my-branch",
        merge_target="develop",
        merge_exec_fn=merge_exec_mock,
    )
    merge_exec_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Test 7: do_merge_if_clean ruft merge_exec NICHT bei DIRTY
# ---------------------------------------------------------------------------

def test_aufruf_guard_dirty_noop() -> None:
    """Aufruf-Guard: do_merge_if_clean ruft merge_exec NICHT bei DIRTY."""
    merge_exec_mock = MagicMock()

    do_merge_if_clean(
        verdict="DIRTY",
        current_branch="feature/my-branch",
        merge_target="develop",
        merge_exec_fn=merge_exec_mock,
    )
    merge_exec_mock.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8: conflict_to_pl liefert dict mit Pflichtfeldern bei CONFLICT
# ---------------------------------------------------------------------------

def test_conflict_to_pl_conflict() -> None:
    """conflict_to_pl(CONFLICT,...) -> dict mit conflict_files + merge_target + hold + verdict."""
    files = ["src/foo.py", "src/bar.py"]
    result = conflict_to_pl(verdict="CONFLICT", files=files, target="develop")

    assert isinstance(result, dict)
    assert result.get("conflict_files") == files
    assert result.get("merge_target") == "develop"
    assert result.get("hold") is True
    assert result.get("verdict") == "CONFLICT"


# ---------------------------------------------------------------------------
# Test 9: conflict_to_pl fail-loud bei leerer files-Liste
# ---------------------------------------------------------------------------

def test_conflict_to_pl_fail_loud() -> None:
    """conflict_to_pl mit leerer files-Liste muss eine Exception werfen (fail-loud, kein None)."""
    with pytest.raises((ValueError, AssertionError)):
        conflict_to_pl(verdict="CONFLICT", files=[], target="develop")


# ---------------------------------------------------------------------------
# Test 10: hold==True im PL-Item-Draft (expliziter Check)
# ---------------------------------------------------------------------------

def test_conflict_to_pl_hold_true() -> None:
    """conflict_to_pl setzt hold=True im PL-Item-Draft — kein False, kein None."""
    result = conflict_to_pl(verdict="CONFLICT", files=["conflict.py"], target="develop")
    assert result["hold"] is True, f"hold muss True sein, war: {result.get('hold')!r}"


# ===========================================================================
# BL-490: FF-Safety-Gate — Tests fuer is_ff_safe + advance_ref_ff_safe
# ===========================================================================

def _make_ff_runner(ancestor_returncode: int = 0):
    """Capturing Mock-Runner fuer merge-base --is-ancestor und branch -f Calls.

    Gibt ein Tupel (runner, captured_cmds) zurueck.
    ancestor_returncode: steuert den returncode des merge-base --is-ancestor Calls.
    Alle anderen Calls (branch -f) landen ebenfalls in captured_cmds mit returncode 0.
    """
    captured_cmds: list[list[str]] = []

    def _runner(cmd, **kwargs):
        captured_cmds.append(list(cmd))
        result = MagicMock()
        result.stdout = ""
        if "merge-base" in cmd and "--is-ancestor" in cmd:
            result.returncode = ancestor_returncode
        else:
            result.returncode = 0
        return result

    return _runner, captured_cmds


# ---------------------------------------------------------------------------
# Test 11: is_ff_safe -> True wenn merge-base --is-ancestor returncode 0
# ---------------------------------------------------------------------------

def test_is_ff_safe_true_when_ancestor() -> None:
    """is_ff_safe gibt True zurueck wenn git merge-base --is-ancestor returncode 0 liefert."""
    runner, _ = _make_ff_runner(ancestor_returncode=0)
    result = is_ff_safe("develop", "roadmap-a", run=runner)
    assert result is True, f"is_ff_safe muss True sein bei ancestor returncode=0, war: {result!r}"


# ---------------------------------------------------------------------------
# Test 12: is_ff_safe -> False wenn merge-base --is-ancestor returncode != 0
# ---------------------------------------------------------------------------

def test_is_ff_safe_false_when_not_ancestor() -> None:
    """is_ff_safe gibt False zurueck wenn git merge-base --is-ancestor returncode 1 liefert."""
    runner, _ = _make_ff_runner(ancestor_returncode=1)
    result = is_ff_safe("develop", "roadmap-a", run=runner)
    assert result is False, f"is_ff_safe muss False sein bei ancestor returncode=1, war: {result!r}"


# ---------------------------------------------------------------------------
# Test 13: advance_ref_ff_safe -> status=="advanced" + branch -f Befehl bei FF
# ---------------------------------------------------------------------------

def test_advance_ref_ff_safe_advances_on_ff() -> None:
    """FF-safe: advance_ref_ff_safe gibt status=='advanced' zurueck und fuehrt git branch -f aus."""
    runner, captured_cmds = _make_ff_runner(ancestor_returncode=0)
    result = advance_ref_ff_safe("develop", "roadmap-a", run=runner)

    assert result.get("status") == "advanced", (
        f"status muss 'advanced' sein bei FF, war: {result.get('status')!r}"
    )
    assert result.get("ref") == "develop"
    assert result.get("new_tip") == "roadmap-a"

    expected_cmd = ["git", "branch", "-f", "develop", "roadmap-a"]
    assert expected_cmd in captured_cmds, (
        f"git branch -f develop roadmap-a muss ausgefuehrt worden sein. "
        f"Erfasste Befehle: {captured_cmds}"
    )


# ---------------------------------------------------------------------------
# Test 14: advance_ref_ff_safe -> status=="refused", reason=="non_ff", hint vorhanden
# ---------------------------------------------------------------------------

def test_advance_ref_ff_safe_refuses_on_non_ff() -> None:
    """non-FF: advance_ref_ff_safe gibt status=='refused' + reason=='non_ff' + nicht-leeren hint zurueck."""
    runner, _ = _make_ff_runner(ancestor_returncode=1)
    result = advance_ref_ff_safe("develop", "roadmap-a", run=runner)

    assert result.get("status") == "refused", (
        f"status muss 'refused' sein bei non-FF, war: {result.get('status')!r}"
    )
    assert result.get("reason") == "non_ff", (
        f"reason muss 'non_ff' sein, war: {result.get('reason')!r}"
    )
    hint = result.get("hint", "")
    assert hint, f"hint muss vorhanden und nicht-leer sein, war: {hint!r}"


# ---------------------------------------------------------------------------
# Test 15: advance_ref_ff_safe fuehrt KEIN git branch -f aus bei non-FF
# ---------------------------------------------------------------------------

def test_advance_ref_ff_safe_no_force_move_on_non_ff() -> None:
    """non-FF: KEIN erfasster Befehl darf gleichzeitig 'branch' und '-f' enthalten."""
    runner, captured_cmds = _make_ff_runner(ancestor_returncode=1)
    advance_ref_ff_safe("develop", "roadmap-a", run=runner)

    force_branch_cmds = [
        cmd for cmd in captured_cmds
        if "branch" in cmd and "-f" in cmd
    ]
    assert force_branch_cmds == [], (
        f"git branch -f darf bei non-FF NICHT ausgefuehrt werden. "
        f"Unerlaubte Befehle: {force_branch_cmds}"
    )


# ---------------------------------------------------------------------------
# Test 16: hint erwaehnt "merge" UND den ref-Namen bei non-FF
# ---------------------------------------------------------------------------

def test_advance_ref_ff_safe_hint_mentions_merge() -> None:
    """non-FF: hint.lower() enthaelt 'merge' UND den ref-Namen ('develop')."""
    runner, _ = _make_ff_runner(ancestor_returncode=1)
    result = advance_ref_ff_safe("develop", "roadmap-a", run=runner)

    hint = result.get("hint", "")
    hint_lower = hint.lower()
    assert "merge" in hint_lower, (
        f"hint muss das Wort 'merge' enthalten, war: {hint!r}"
    )
    assert "develop" in hint_lower, (
        f"hint muss den ref-Namen 'develop' enthalten, war: {hint!r}"
    )
