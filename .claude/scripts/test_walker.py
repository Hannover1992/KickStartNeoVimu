"""BL-371 AK-1 + AK-2: test_walker.py — RED-Tests fuer walker.py

Erwartet: walker.py existiert NICHT oder enthaelt nur Stubs -> ImportError oder
alle Tests FAIL (RED). GREEN-Worker implementiert walker.py.

API unter Test:
  next_walker_action(worker_id, lane, lane_plan_path, vault_root, autocracy, stuck=False)
    -> WalkerAction(kind, bl_id, branch, detail)
  compute_branch(bl_id, base="develop") -> str

Invarianten (laut Spec BL-371):
  INV-WALKER-LOCK:     Kein TAKE_NEXT ohne acquire_bl=True
  INV-WALKER-NONBLOCK: stuck=True + offenes BL -> PARK_AND_NEXT (nie IDLE_DONE)
  INV-WALKER-AUTOCRACY: autocracy-Param ist EINZIGE HIL-Gating-Stellschraube
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))

# RED: Dieser Import schlaegt fehl solange walker.py nicht existiert / nicht vollstaendig ist
from walker import next_walker_action, compute_branch, WalkerAction  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

LANE_PLAN_CONTENT_SINGLE = """
```yaml
LANE_PLAN:
  A:
    branch: roadmap-a
    worktree: OmniCommand-wtA
    current: BL-100
    queue: [BL-100, BL-371]
    done: []
    parked: []
```
"""

LANE_PLAN_CONTENT_EMPTY = """
```yaml
LANE_PLAN:
  A:
    branch: roadmap-a
    worktree: OmniCommand-wtA
    current: null
    queue: []
    done: []
    parked: []
```
"""

LANE_PLAN_CONTENT_ALL_DONE = """
```yaml
LANE_PLAN:
  A:
    branch: roadmap-a
    worktree: OmniCommand-wtA
    current: BL-100
    queue: [BL-100]
    done: [BL-100]
    parked: []
```
"""


def _write_plan(tmp_path, content: str) -> Path:
    p = tmp_path / "_lane_plan.md"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# AK-2: compute_branch
# ---------------------------------------------------------------------------

def test_compute_branch_default():
    """compute_branch mit default-base 'develop' -> 'develop-bl-371'"""
    result = compute_branch("BL-371")
    assert result == "develop-bl-371"


def test_compute_branch_custom_base():
    """compute_branch mit custom base 'roadmap-a' -> 'roadmap-a-bl-371'"""
    result = compute_branch("BL-371", "roadmap-a")
    assert result == "roadmap-a-bl-371"


def test_compute_branch_uppercase_normalized():
    """BL-ID wird lowercase -> 'develop-bl-100'"""
    result = compute_branch("BL-100")
    assert result == "develop-bl-100"


def test_compute_branch_different_ids_different_names():
    """Verschiedene BL-IDs ergeben verschiedene Branch-Namen"""
    b1 = compute_branch("BL-100")
    b2 = compute_branch("BL-200")
    assert b1 != b2
    # Beide enthalten die jeweilige bl_id
    assert "bl-100" in b1
    assert "bl-200" in b2


# ---------------------------------------------------------------------------
# AK-1: WalkerAction-Dataclass
# ---------------------------------------------------------------------------

def test_walker_action_fields():
    """WalkerAction hat die Pflichtfelder kind, bl_id, branch, detail"""
    action = WalkerAction(kind="IDLE_DONE", bl_id=None, branch=None, detail="test")
    assert action.kind == "IDLE_DONE"
    assert action.bl_id is None
    assert action.branch is None
    assert action.detail == "test"


def test_walker_action_take_next_fields():
    """TAKE_NEXT WalkerAction traegt bl_id + branch"""
    action = WalkerAction(kind="TAKE_NEXT", bl_id="BL-371", branch="develop-bl-371", detail="ok")
    assert action.kind == "TAKE_NEXT"
    assert action.bl_id == "BL-371"
    assert action.branch == "develop-bl-371"


# ---------------------------------------------------------------------------
# AK-1: next_walker_action — Entscheidungsbaum
# ---------------------------------------------------------------------------

def test_idle_done_lane_exhausted(tmp_path):
    """Leere queue -> IDLE_DONE (kein next_bl)"""
    plan_path = _write_plan(tmp_path, LANE_PLAN_CONTENT_EMPTY)
    vault_root = str(tmp_path / "vault")
    Path(vault_root).mkdir()

    with patch("factory_lock.acquire_bl", return_value=True):
        action = next_walker_action(
            worker_id="w-test",
            lane="A",
            lane_plan_path=str(plan_path),
            vault_root=vault_root,
            autocracy="full_auto",
        )

    assert action.kind == "IDLE_DONE"
    assert action.bl_id is None


def test_idle_done_all_done(tmp_path):
    """Alle BLs in done -> IDLE_DONE"""
    plan_path = _write_plan(tmp_path, LANE_PLAN_CONTENT_ALL_DONE)
    vault_root = str(tmp_path / "vault")
    Path(vault_root).mkdir()

    with patch("factory_lock.acquire_bl", return_value=True):
        action = next_walker_action(
            worker_id="w-test",
            lane="A",
            lane_plan_path=str(plan_path),
            vault_root=vault_root,
            autocracy="full_auto",
        )

    assert action.kind == "IDLE_DONE"


def test_hil_ask_checkpoint(tmp_path):
    """autocracy=checkpoint + naechstes BL vorhanden -> HIL_ASK [INV-WALKER-AUTOCRACY]"""
    plan_path = _write_plan(tmp_path, LANE_PLAN_CONTENT_SINGLE)
    vault_root = str(tmp_path / "vault")
    Path(vault_root).mkdir()

    # acquire_bl sollte bei checkpoint NICHT aufgerufen werden
    with patch("factory_lock.acquire_bl", return_value=True) as mock_acquire:
        action = next_walker_action(
            worker_id="w-test",
            lane="A",
            lane_plan_path=str(plan_path),
            vault_root=vault_root,
            autocracy="checkpoint",
        )

    assert action.kind == "HIL_ASK"
    assert action.bl_id is not None
    # acquire_bl darf bei checkpoint NICHT aufgerufen worden sein (INV-WALKER-AUTOCRACY)
    mock_acquire.assert_not_called()


def test_idle_done_manual(tmp_path):
    """autocracy=manual -> IDLE_DONE (kein autonomer Take)"""
    plan_path = _write_plan(tmp_path, LANE_PLAN_CONTENT_SINGLE)
    vault_root = str(tmp_path / "vault")
    Path(vault_root).mkdir()

    with patch("factory_lock.acquire_bl", return_value=True) as mock_acquire:
        action = next_walker_action(
            worker_id="w-test",
            lane="A",
            lane_plan_path=str(plan_path),
            vault_root=vault_root,
            autocracy="manual",
        )

    assert action.kind == "IDLE_DONE"
    mock_acquire.assert_not_called()


def test_take_next_full_auto_lock_ok(tmp_path):
    """autocracy=full_auto + acquire_bl=True -> TAKE_NEXT mit bl_id"""
    plan_path = _write_plan(tmp_path, LANE_PLAN_CONTENT_SINGLE)
    vault_root = str(tmp_path / "vault")
    Path(vault_root).mkdir()

    with patch("factory_lock.acquire_bl", return_value=True):
        action = next_walker_action(
            worker_id="w-test",
            lane="A",
            lane_plan_path=str(plan_path),
            vault_root=vault_root,
            autocracy="full_auto",
        )

    assert action.kind == "TAKE_NEXT"
    assert action.bl_id is not None


def test_no_take_without_lock(tmp_path):
    """INV-WALKER-LOCK: acquire_bl=False -> KEIN TAKE_NEXT (IDLE_DONE oder wait)"""
    plan_path = _write_plan(tmp_path, LANE_PLAN_CONTENT_SINGLE)
    vault_root = str(tmp_path / "vault")
    Path(vault_root).mkdir()

    with patch("factory_lock.acquire_bl", return_value=False):
        action = next_walker_action(
            worker_id="w-test",
            lane="A",
            lane_plan_path=str(plan_path),
            vault_root=vault_root,
            autocracy="full_auto",
        )

    # KEIN TAKE_NEXT wenn Lock nicht erworben (INV-WALKER-LOCK)
    assert action.kind != "TAKE_NEXT"


def test_idle_done_lock_held(tmp_path):
    """autocracy=full_auto + acquire_bl=False -> IDLE_DONE (Lock gehalten)"""
    plan_path = _write_plan(tmp_path, LANE_PLAN_CONTENT_SINGLE)
    vault_root = str(tmp_path / "vault")
    Path(vault_root).mkdir()

    with patch("factory_lock.acquire_bl", return_value=False):
        action = next_walker_action(
            worker_id="w-test",
            lane="A",
            lane_plan_path=str(plan_path),
            vault_root=vault_root,
            autocracy="full_auto",
        )

    assert action.kind == "IDLE_DONE"


def test_take_next_has_branch(tmp_path):
    """TAKE_NEXT-Result hat branch != None (compute_branch wurde aufgerufen)"""
    plan_path = _write_plan(tmp_path, LANE_PLAN_CONTENT_SINGLE)
    vault_root = str(tmp_path / "vault")
    Path(vault_root).mkdir()

    with patch("factory_lock.acquire_bl", return_value=True):
        action = next_walker_action(
            worker_id="w-test",
            lane="A",
            lane_plan_path=str(plan_path),
            vault_root=vault_root,
            autocracy="full_auto",
        )

    assert action.kind == "TAKE_NEXT"
    assert action.branch is not None
    assert len(action.branch) > 0


def test_park_and_next_stuck(tmp_path):
    """stuck=True + naechstes BL vorhanden -> PARK_AND_NEXT [INV-WALKER-NONBLOCK]

    Lane hat BL-100 als current + BL-371 als next. Bei stuck=True wird BL-100
    geparkt und BL-371 als naechstes returned.
    """
    plan_content = """
```yaml
LANE_PLAN:
  A:
    branch: roadmap-a
    worktree: OmniCommand-wtA
    current: BL-100
    queue: [BL-100, BL-371]
    done: []
    parked: []
```
"""
    plan_path = _write_plan(tmp_path, plan_content)
    vault_root = str(tmp_path / "vault")
    Path(vault_root).mkdir()

    action = next_walker_action(
        worker_id="w-test",
        lane="A",
        lane_plan_path=str(plan_path),
        vault_root=vault_root,
        autocracy="full_auto",
        stuck=True,
    )

    # INV-WALKER-NONBLOCK: stuck + next_bl vorhanden -> immer PARK_AND_NEXT
    assert action.kind == "PARK_AND_NEXT"
    # bl_id zeigt das naechste zu verarbeitende BL (nach park)
    assert action.bl_id is not None


def test_idle_done_stuck_exhausted(tmp_path):
    """stuck=True + keine weiteren BLs (leere/done Queue) -> IDLE_DONE"""
    plan_content = """
```yaml
LANE_PLAN:
  A:
    branch: roadmap-a
    worktree: OmniCommand-wtA
    current: BL-100
    queue: [BL-100]
    done: []
    parked: []
```
"""
    plan_path = _write_plan(tmp_path, plan_content)
    vault_root = str(tmp_path / "vault")
    Path(vault_root).mkdir()

    action = next_walker_action(
        worker_id="w-test",
        lane="A",
        lane_plan_path=str(plan_path),
        vault_root=vault_root,
        autocracy="full_auto",
        stuck=True,
    )

    # stuck + kein next_bl -> IDLE_DONE (Lane erschoepft)
    assert action.kind == "IDLE_DONE"
