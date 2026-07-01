#!/usr/bin/env python3
"""
test_guard_branch_force_develop.py — BL-490 RED tests fuer guard_branch_force_develop.py.

Pflicht-Testfaelle (alle MUESSEN ohne guard_branch_force_develop.py fehlschlagen —
ModuleNotFoundError = RED):

  classify_command (pure, schnell):
   1.  test_block_branch_force_develop            — "git branch -f develop roadmap-c" -> blocked True, ref develop
   2.  test_block_branch_force_long_flag_main     — "git branch --force main roadmap-a" -> blocked True, ref main
   3.  test_block_update_ref_develop              — "git update-ref refs/heads/develop roadmap-a" -> blocked
   4.  test_block_force_push_plus_develop         — "git push origin +develop" -> blocked
   5.  test_block_force_push_flag_develop         — "git push --force origin develop" -> blocked
   6.  test_allow_force_move_lane_branch          — "git branch -f roadmap-a 7a3337e" -> None
   7.  test_allow_force_move_backup_branch        — "git branch -f backup/x HEAD" -> None
   8.  test_allow_plain_branch_develop_no_force   — "git branch develop" -> None
   9.  test_allow_merge_develop                   — "git merge develop" -> None
  10.  test_allow_word_boundary_develop_feature   — "git branch -f develop-feature HEAD" -> None
  11.  test_allow_empty_command                   — "" -> None

  main() (stdin via monkeypatch + capsys):
  12.  test_main_blocks_forbidden_bash            — Bash + "git branch -f develop roadmap-c" -> continue==false
  13.  test_main_allows_safe_bash                 — Bash + "git commit -m x" -> continue==true
  14.  test_main_fail_open_on_bad_json            — leeres stdin -> continue==true
"""
from __future__ import annotations

import io
import json
import sys

import pytest

# RED: guard_branch_force_develop.py existiert NOCH NICHT —
# dieser Import-Fehler IST der erwartete Fehlschlag (ModuleNotFoundError).
import guard_branch_force_develop as g


# ---------------------------------------------------------------------------
# classify_command — BLOCK-Faelle
# ---------------------------------------------------------------------------

def test_block_branch_force_develop():
    result = g.classify_command("git branch -f develop roadmap-c")
    assert result is not None
    assert result["blocked"] is True
    assert result["ref"] == "develop"
    assert "reason" in result


def test_block_branch_force_long_flag_main():
    result = g.classify_command("git branch --force main roadmap-a")
    assert result is not None
    assert result["blocked"] is True
    assert result["ref"] == "main"
    assert "reason" in result


def test_block_update_ref_develop():
    result = g.classify_command("git update-ref refs/heads/develop roadmap-a")
    assert result is not None
    assert result["blocked"] is True
    assert result["ref"] == "develop"


def test_block_force_push_plus_develop():
    result = g.classify_command("git push origin +develop")
    assert result is not None
    assert result["blocked"] is True
    assert result["ref"] == "develop"


def test_block_force_push_flag_develop():
    result = g.classify_command("git push --force origin develop")
    assert result is not None
    assert result["blocked"] is True
    assert result["ref"] == "develop"


# ---------------------------------------------------------------------------
# classify_command — ALLOW-Faelle (→ None)
# ---------------------------------------------------------------------------

def test_allow_force_move_lane_branch():
    assert g.classify_command("git branch -f roadmap-a 7a3337e") is None


def test_allow_force_move_backup_branch():
    assert g.classify_command("git branch -f backup/x HEAD") is None


def test_allow_plain_branch_develop_no_force():
    # kein -f / --force → kein Force-Move
    assert g.classify_command("git branch develop") is None


def test_allow_merge_develop():
    assert g.classify_command("git merge develop") is None


def test_allow_word_boundary_develop_feature():
    # "develop-feature" ≠ "develop" — Wort-Grenze muss korrekt matchen
    assert g.classify_command("git branch -f develop-feature HEAD") is None


def test_allow_empty_command():
    assert g.classify_command("") is None


# ---------------------------------------------------------------------------
# main() — stdin/stdout via monkeypatch + capsys
# ---------------------------------------------------------------------------

def _run_main(monkeypatch, stdin_text: str, capsys):
    """Hilfsfunktion: setzt stdin auf StringIO, ruft main() auf, gibt stdout-Dict zurueck."""
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))
    g.main()
    captured = capsys.readouterr()
    return json.loads(captured.out)


def test_main_blocks_forbidden_bash(monkeypatch, capsys):
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "git branch -f develop roadmap-c"},
    })
    result = _run_main(monkeypatch, payload, capsys)
    assert result["continue"] is False
    assert "message" in result


def test_main_allows_safe_bash(monkeypatch, capsys):
    payload = json.dumps({
        "tool_name": "Bash",
        "tool_input": {"command": "git commit -m x"},
    })
    result = _run_main(monkeypatch, payload, capsys)
    assert result["continue"] is True


def test_main_fail_open_on_bad_json(monkeypatch, capsys):
    # leeres / kaputtes JSON → fail-open (continue: true)
    result = _run_main(monkeypatch, "", capsys)
    assert result["continue"] is True


# ---------------------------------------------------------------------------
# BL-490 Hardening: FN-1 (--force-with-lease) + FN-2 (branch delete) — RED
# ---------------------------------------------------------------------------

def test_block_branch_delete_capital_D_develop():
    # FN-2: "git branch -D develop" muss geblockt werden (shared Branch)
    result = g.classify_command("git branch -D develop")
    assert result is not None
    assert result["blocked"] is True
    assert result["ref"] == "develop"
    assert "reason" in result


def test_block_branch_delete_lower_d_develop():
    # FN-2: "git branch -d develop" muss geblockt werden (shared Branch)
    result = g.classify_command("git branch -d develop")
    assert result is not None
    assert result["blocked"] is True
    assert result["ref"] == "develop"
    assert "reason" in result


def test_block_branch_long_delete_main():
    # FN-2: "git branch --delete main" muss geblockt werden (shared Branch)
    result = g.classify_command("git branch --delete main")
    assert result is not None
    assert result["blocked"] is True
    assert result["ref"] == "main"
    assert "reason" in result


def test_block_push_force_with_lease_develop():
    # FN-1: "--force-with-lease" ist dieselbe Bedrohungsklasse wie --force
    result = g.classify_command("git push --force-with-lease origin develop")
    assert result is not None
    assert result["blocked"] is True
    assert result["ref"] == "develop"
    assert "reason" in result


def test_allow_delete_lane_branch():
    # Loeschung eines NICHT-geteilten Branches bleibt erlaubt
    assert g.classify_command("git branch -D roadmap-a") is None


def test_allow_delete_feature_branch():
    # Loeschung eines Feature-Branches bleibt erlaubt
    assert g.classify_command("git branch -d feature/x") is None
