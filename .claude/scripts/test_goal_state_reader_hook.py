#!/usr/bin/env python3
"""Tests fuer goal_state_reader_hook.py (BL-221) — echte Goal-State-Validierung."""
import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

from goal_state_reader_hook import parse_goal, resolve_bl_status, evaluate

HOOK = Path(__file__).parent / "goal_state_reader_hook.py"


def _mk_bl(backlog: Path, bl_id: str, status: str) -> None:
    backlog.mkdir(parents=True, exist_ok=True)
    (backlog / f"{bl_id}-test-slug.md").write_text(
        f"---\nid: {bl_id}\nstatus: {status}\n---\n# {bl_id}\n", encoding="utf-8")


# ── parse_goal (AK-2 reale Shape) ──
def test_parse_goal_inline_list():
    mode, bls = parse_goal("---\nmode: backlog_drain\ntarget_bls: [BL-229, BL-230, BL-221]\n---\n")
    assert mode == "backlog_drain"
    assert bls == ["BL-229", "BL-230", "BL-221"]


def test_parse_goal_yaml_block():
    _, bls = parse_goal("mode: backlog\ntarget_bls:\n  - BL-229\n  - BL-193\n")
    assert bls == ["BL-229", "BL-193"]


def test_parse_goal_ignores_sentinel():
    # ALL_OPEN (self-discovering) ist kein BL-\d+ -> ignoriert (kein Fehl-Alarm)
    _, bls = parse_goal("target_bls: [ALL_OPEN]\n")
    assert bls == []


# ── resolve_bl_status (BL-File autoritativ, NICHT Index) ──
def test_resolve_bl_status_from_file(tmp_path):
    _mk_bl(tmp_path / "Backlog", "BL-221", "READY")
    assert resolve_bl_status(tmp_path, "BL-221") == "READY"
    assert resolve_bl_status(tmp_path, "BL-999") is None


# ── evaluate (Kern) ──
def test_evaluate_all_done(tmp_path):
    _mk_bl(tmp_path / "Backlog", "BL-1", "DONE")
    _mk_bl(tmp_path / "Backlog", "BL-2", "DONE")
    all_done, done, openn, _, _ = evaluate("target_bls: [BL-1, BL-2]\n", tmp_path)
    assert all_done is True and openn == [] and sorted(done) == ["BL-1", "BL-2"]


def test_evaluate_partial(tmp_path):
    _mk_bl(tmp_path / "Backlog", "BL-1", "DONE")
    _mk_bl(tmp_path / "Backlog", "BL-2", "DRAFT")
    all_done, done, openn, _, _ = evaluate("target_bls: [BL-1, BL-2]\n", tmp_path)
    assert all_done is False and done == ["BL-1"] and len(openn) == 1 and "BL-2" in openn[0]


# ── main (env-Verhalten via subprocess) ──
def test_main_off_env():
    env = os.environ.copy()
    env["OMNI_GOAL_STATE_READER_OFF"] = "1"
    r = subprocess.run([sys.executable, str(HOOK)], input="", capture_output=True, text=True, env=env)
    assert json.loads(r.stdout)["continue"] is True


def test_main_enforce_blocks_partial(tmp_path):
    _mk_bl(tmp_path / "Backlog", "BL-1", "DRAFT")
    goal = tmp_path / "GOAL.md"
    goal.write_text("mode: backlog\ntarget_bls: [BL-1]\n", encoding="utf-8")
    env = os.environ.copy()
    env.update({"OMNI_GOAL_MD": str(goal), "OMNI_GOAL_VAULT_ROOT": str(tmp_path),
                "OMNI_GOAL_STATE_READER_ENFORCE": "1"})
    r = subprocess.run([sys.executable, str(HOOK)], input="", capture_output=True, text=True, env=env)
    out = json.loads(r.stdout)
    assert out["continue"] is False and "0/1" in out["message"]


def test_main_warn_all_done(tmp_path):
    _mk_bl(tmp_path / "Backlog", "BL-1", "DONE")
    goal = tmp_path / "GOAL.md"
    goal.write_text("mode: backlog\ntarget_bls: [BL-1]\n", encoding="utf-8")
    env = os.environ.copy()
    env.update({"OMNI_GOAL_MD": str(goal), "OMNI_GOAL_VAULT_ROOT": str(tmp_path)})
    r = subprocess.run([sys.executable, str(HOOK)], input="", capture_output=True, text=True, env=env)
    out = json.loads(r.stdout)
    assert out["continue"] is True and "erfuellt" in out["message"]
