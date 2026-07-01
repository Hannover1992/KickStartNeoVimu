"""
BL-272 Per-Backlog Finish-Gate Decider.

Reine Decider-Logik (kein Seiteneffekt, keine Datei-IO, kein Manifest-Write).

Vier Funktionen:
    finish_gate_decision     -- Gate-Status (NOT_READY / AUTO_FINISH / HIL_WAIT)
    harvest_source_from_completed -- Items aus completed_sub_batches (flach)
    build_finish_sequence    -- geordnete Step-Liste fuer die Finish-Phase
    hil_bad_path_route       -- Routing-Entscheidung nach HIL-Eingabe

Verdrahtung mit _SDF_orchestrate_post und _BDF sowie der model_split-Orchestrator
(BL-270) sind DEFERRED -- diese Datei enthaelt ausschliesslich die Entscheidungslogik.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# AK-1: finish_gate_decision
# ---------------------------------------------------------------------------

def finish_gate_decision(pl_empty: bool, bdf: bool, hil: str) -> str:
    """Entscheidet den Gate-Status am Ende eines Backlogs.

    Args:
        pl_empty: True wenn die Live-PL keine offenen Items mehr hat.
        bdf:      True wenn der BDF-Automatikmodus aktiv ist (kein Mensch
                  muss manuell freigeben).
        hil:      HIL-Status-String (z.B. "on"/"off"). Orthogonal zum
                  Gate-Ergebnis in V1 (BL-159: bdf vs hil getrennt).

    Returns:
        "NOT_READY"   -- Gate gesperrt, PL hat noch offene Items.
        "AUTO_FINISH" -- PL leer + BDF aktiv -> Engine kann autonom abschliessen.
        "HIL_WAIT"    -- PL leer + BDF inaktiv -> Mensch muss freigeben.
    """
    if not pl_empty:
        return "NOT_READY"

    # pl_empty=True ab hier
    if bdf:
        return "AUTO_FINISH"
    return "HIL_WAIT"


# ---------------------------------------------------------------------------
# AK-2a: harvest_source_from_completed
# ---------------------------------------------------------------------------

def harvest_source_from_completed(manifest_state: dict) -> list:
    """Sammelt alle abgeschlossenen Items aus completed_sub_batches.

    Liest aus manifest_state["completed_sub_batches"] (Liste von Batch-Dicts
    mit einem "items"-Key je Batch).  Gibt eine flache Liste aller Items
    zurueck.  live_pl wird IGNORIERT (AK-S4: COMPLETED-Quelle, nicht live-PL).

    Args:
        manifest_state: Das SDF-Manifest als dict.

    Returns:
        Flache Liste aller Items aus completed_sub_batches.
        Leere Liste wenn der Key fehlt, None ist oder keine Items vorhanden.
    """
    completed_batches: list[dict[str, Any]] = manifest_state.get(
        "completed_sub_batches", []
    ) or []

    items: list[Any] = []
    for batch in completed_batches:
        batch_items = batch.get("items") or []
        items.extend(batch_items)
    return items


# ---------------------------------------------------------------------------
# AK-2b: build_finish_sequence
# ---------------------------------------------------------------------------

def build_finish_sequence(
    manifest_state: dict,
    model_split_available: bool = False,
) -> list:
    """Baut die geordnete Step-Liste fuer die Finish-Phase.

    Reihenfolge:
        1. model_split  -- SKIPPED (BL-270 deferred) oder READY (wenn verfuegbar)
        2. pt_harvest   -- READY; source="completed_history"; items aus Manifest
        3. state_transition -- READY; target="DONE"; immer letzter Step

    model_split und pt_harvest haben disjunkte Inputs und koennen parallel
    ausgefuehrt werden (Markierung: parallel=True auf beiden Steps).

    Args:
        manifest_state:        Das SDF-Manifest als dict.
        model_split_available: Ob der model_split-Orchestrator (BL-270)
                               verfuegbar ist.

    Returns:
        Geordnete Liste von Step-Dicts.
    """
    steps: list[dict[str, Any]] = []

    # Step 1: model_split
    if model_split_available:
        model_split_step: dict[str, Any] = {
            "step": "model_split",
            "status": "READY",
            "parallel": True,
        }
    else:
        model_split_step = {
            "step": "model_split",
            "status": "SKIPPED",
            "reason": "BL-270 (model_split-Orchestrator) ist deferred/nicht verfuegbar",
            "parallel": True,
        }
    steps.append(model_split_step)

    # Step 2: pt_harvest (parallel zu model_split, disjunkte Inputs)
    harvested_items = harvest_source_from_completed(manifest_state)
    pt_harvest_step: dict[str, Any] = {
        "step": "pt_harvest",
        "status": "READY",
        "source": "completed_history",
        "items": harvested_items,
        "parallel": True,
    }
    steps.append(pt_harvest_step)

    # Step 3: state_transition -- immer letzter Step
    state_transition_step: dict[str, Any] = {
        "step": "state_transition",
        "status": "READY",
        "target": "DONE",
    }
    steps.append(state_transition_step)

    return steps


# ---------------------------------------------------------------------------
# AK-3: hil_bad_path_route
# ---------------------------------------------------------------------------

def hil_bad_path_route(user_pl_items: list | None) -> dict:
    """Routing-Entscheidung nach HIL-Eingabe mit verbleibenden PL-Items.

    Args:
        user_pl_items: Liste von Items die der Mensch als noch offen markiert.
                       Leer oder None bedeutet: keine offenen Items gefunden.

    Returns:
        {"action": "PROCEED_FINISH"}
            wenn user_pl_items leer oder None ist.

        {"action": "IDF_RECHECK",
         "skill_arg": "--mode=recheck --from=backlog_hil",
         "new_pl_items": user_pl_items}
            wenn Items vorhanden sind (IDF soll die Items neu bewerten).
    """
    if not user_pl_items:
        return {"action": "PROCEED_FINISH"}

    return {
        "action": "IDF_RECHECK",
        "skill_arg": "--mode=recheck --from=backlog_hil",
        "new_pl_items": user_pl_items,
    }
