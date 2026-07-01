"""BL-371 Walker-Integration-Decider.

Komponiert factory_lock + lane_plan zu einem deterministischen Entscheidungsbaum:
  next_walker_action(worker_id, lane, lane_plan_path, vault_root, autocracy, stuck=False)
    -> WalkerAction(kind, bl_id, branch, detail)

Invarianten:
  INV-WALKER-LOCK:      Kein TAKE_NEXT ohne acquire_bl=True (INV-LOCK)
  INV-WALKER-NONBLOCK:  stuck=True + offenes BL -> PARK_AND_NEXT (nie blockieren)
  INV-WALKER-AUTOCRACY: autocracy-Param ist EINZIGE HIL-Gating-Stellschraube

kind-Werte:
  TAKE_NEXT      — autonomes Nehmen, Lock erworben
  HIL_ASK        — Human-in-Loop benoetigt (checkpoint-Modus)
  PARK_AND_NEXT  — aktuelles BL geparkt, naechstes BL returned
  IDLE_DONE      — keine weiteren BLs oder Lock nicht verfuegbar

Deferred: _BDF-Verdrahtung / Multi-Worktree (BL-230/431).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import factory_lock
import lane_plan as _lp


@dataclass
class WalkerAction:
    """Ergebnis von next_walker_action."""
    kind: str        # TAKE_NEXT | HIL_ASK | PARK_AND_NEXT | IDLE_DONE
    bl_id: Optional[str]
    branch: Optional[str]
    detail: str


def compute_branch(bl_id: str, base: str = "develop") -> str:
    """Deterministischer Branch-Name der bl_id enthaelt.

    Beispiel: compute_branch("BL-371") -> "develop-bl-371"
              compute_branch("BL-100", "roadmap-a") -> "roadmap-a-bl-100"
    """
    return f"{base}-{bl_id.lower()}"


def next_walker_action(
    worker_id: str,
    lane: str,
    lane_plan_path: str,
    vault_root: str,
    autocracy: str,
    stuck: bool = False,
) -> WalkerAction:
    """Entscheidungsbaum fuer den naechsten Walker-Schritt.

    Args:
        worker_id:      Eindeutiger Worker-Identifier (fuer factory_lock).
        lane:           Lane-Key (z.B. "A").
        lane_plan_path: Pfad zur _lane_plan.md-Datei.
        vault_root:     Vault-Root-Verzeichnis (fuer factory_lock BL-Locks).
        autocracy:      "full_auto" | "checkpoint" | "manual"
        stuck:          True wenn aktuelles BL blockiert ist [INV-WALKER-NONBLOCK].

    Returns:
        WalkerAction mit kind ∈ {TAKE_NEXT, HIL_ASK, PARK_AND_NEXT, IDLE_DONE}.
    """
    vault_path = Path(vault_root)
    plan = _lp.parse_lane_plan(lane_plan_path)

    # --- stuck-Pfad: INV-WALKER-NONBLOCK ---
    if stuck:
        # Park current BL und suche naechstes
        lane_entry = plan.get(lane, {})
        current_bl = lane_entry.get("current")

        if current_bl:
            plan = _lp.park_bl(lane, current_bl, plan)
            # Plan persistieren damit next_bl_for_lane den parked-Skip sieht
            _lp.write_lane_plan(lane_plan_path, plan)
            # Plan neu lesen (parked-Set ist jetzt im plan-Dict)
            plan = _lp.parse_lane_plan(lane_plan_path)

        next_bl = _lp.next_bl_for_lane(lane, plan)

        if next_bl is None:
            return WalkerAction(
                kind="IDLE_DONE",
                bl_id=None,
                branch=None,
                detail="stuck + Lane erschoepft (kein weiteres BL nach park)",
            )

        return WalkerAction(
            kind="PARK_AND_NEXT",
            bl_id=next_bl,
            branch=compute_branch(next_bl),
            detail=f"geparkt: {current_bl}, naechstes: {next_bl}",
        )

    # --- normaler Pfad ---
    next_bl = _lp.next_bl_for_lane(lane, plan)

    if next_bl is None:
        return WalkerAction(
            kind="IDLE_DONE",
            bl_id=None,
            branch=None,
            detail="Lane erschoepft (keine weiteren BLs)",
        )

    # autocracy-Gating [INV-WALKER-AUTOCRACY]
    if autocracy == "full_auto":
        acquired = factory_lock.acquire_bl(
            bl_id=next_bl,
            worker_id=worker_id,
            vault_root=vault_path,
        )
        if not acquired:
            return WalkerAction(
                kind="IDLE_DONE",
                bl_id=None,
                branch=None,
                detail=f"Lock fuer {next_bl} nicht verfuegbar [INV-WALKER-LOCK]",
            )
        return WalkerAction(
            kind="TAKE_NEXT",
            bl_id=next_bl,
            branch=compute_branch(next_bl),
            detail=f"Lock erworben fuer {next_bl}",
        )

    elif autocracy == "checkpoint":
        # HIL-Ask: kein autonomer Take, kein Lock-Erwerb [INV-WALKER-AUTOCRACY]
        return WalkerAction(
            kind="HIL_ASK",
            bl_id=next_bl,
            branch=compute_branch(next_bl),
            detail=f"HIL-Bestaetigung erforderlich fuer {next_bl} (checkpoint-Modus)",
        )

    else:
        # manual oder unbekannt -> IDLE_DONE (kein autonomer Take)
        return WalkerAction(
            kind="IDLE_DONE",
            bl_id=None,
            branch=None,
            detail=f"Manueller Modus ({autocracy!r}) — kein autonomer Take",
        )
