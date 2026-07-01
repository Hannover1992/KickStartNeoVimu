"""BL-331 BDF Post-Item-Learning-Gate Decider.

FENCE: nur Routing-Entscheidung; _PT_orchestrate-Aufruf + PatternLibrary/DomainLibrary-Writes
= Lane B (deferred). _BDF-Phase-Verdrahtung = Folge-Slice.

INV-LEARN-GATE: Learning nur wenn big_dark_factory + hil=off + all_pl_done + all_batches_done.
INV-LEARN-PROPORTIONAL: FULL_HARVEST wenn mind. 1 coverage_class != markdown_target_uncoverable.
INV-LEARN-NO-SIDEEFFECT: reiner Decider, kein File-IO, kein Manifest-Write.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def should_run_learning(
    global_modus: str,
    hil: str,
    all_pl_done: bool,
    all_batches_done: bool,
) -> bool:
    """INV-LEARN-GATE: True NUR wenn alle 4 UND-Bedingungen erfuellt.

    Args:
        global_modus: Session-Modus (muss "big_dark_factory" sein).
        hil: HIL-Wert (muss "off" sein fuer autonomes Lernen).
        all_pl_done: True wenn alle PL-Items abgearbeitet.
        all_batches_done: True wenn alle Batches completed.

    Returns:
        True wenn Learning ausgefuehrt werden soll, False sonst.
    """
    return (
        global_modus == "big_dark_factory"
        and hil == "off"
        and bool(all_pl_done)
        and bool(all_batches_done)
    )


def classify_harvest_scope(coverage_classes: Optional[List[Any]]) -> str:
    """INV-LEARN-PROPORTIONAL: Harvest-Scope aus coverage_classes ableiten.

    Args:
        coverage_classes: Liste von Coverage-Klassen der Batches. None/leer -> SLIM_NOOP.
            None-Werte werden als "markdown_target_uncoverable" behandelt.

    Returns:
        "FULL_HARVEST" wenn mind. 1 Element NICHT "markdown_target_uncoverable".
        "SLIM_NOOP" wenn leer/None/alle-uncoverable.
    """
    if not coverage_classes:
        return "SLIM_NOOP"

    for cls in coverage_classes:
        if cls is not None and cls != "markdown_target_uncoverable":
            return "FULL_HARVEST"

    return "SLIM_NOOP"


def model_channel_decision(has_2_model_dir: bool, model_param_on: bool) -> str:
    """Model-Kanal-Routing.

    Args:
        has_2_model_dir: True wenn 2_Model/-Verzeichnis im BL-Folder existiert.
        model_param_on: True wenn model-Param auf "on" gesetzt.

    Returns:
        "NOOP" wenn model_param_on=False.
        "FULL_MODEL_SYNC" wenn model_param_on=True und has_2_model_dir=True.
        "DOMAIN_DIRECT" wenn model_param_on=True und has_2_model_dir=False.
    """
    if not model_param_on:
        return "NOOP"
    if has_2_model_dir:
        return "FULL_MODEL_SYNC"
    return "DOMAIN_DIRECT"


def post_item_learning_gate(
    global_modus: str,
    hil: str,
    all_pl_done: bool,
    all_batches_done: bool,
    coverage_classes: Optional[List[Any]],
    has_2_model_dir: bool,
    pt_on: bool = True,
    model_on: bool = True,
) -> Dict[str, Any]:
    """Haupt-Gate-Router: komposiert AK-1/2/3 (INV-LEARN-NO-SIDEEFFECT).

    Reiner Decider — kein File-IO, kein Manifest-Write, keine Seiteneffekte.

    Args:
        global_modus: Session-Modus.
        hil: HIL-Wert.
        all_pl_done: True wenn alle PL-Items done.
        all_batches_done: True wenn alle Batches done.
        coverage_classes: Liste von Coverage-Klassen.
        has_2_model_dir: True wenn 2_Model/-Verzeichnis vorhanden.
        pt_on: True wenn PT-Kanal aktiv (default True).
        model_on: True wenn Model-Kanal aktiv (default True).

    Returns:
        Dict mit Keys:
            run (bool): should_run_learning Ergebnis.
            reason (str): Begruendung (enthaelt global_modus + hil).
            harvest_scope (str): FULL_HARVEST | SLIM_NOOP (nur wenn run=True).
            pt_routing (dict): {"scope": ...}
            model_routing (dict): {"mode": ...}
    """
    run = should_run_learning(global_modus, hil, all_pl_done, all_batches_done)
    reason = (
        f"global_modus={global_modus} hil={hil} "
        f"all_pl_done={all_pl_done} all_batches_done={all_batches_done}"
    )

    if not run:
        return {
            "run": False,
            "reason": reason,
            "harvest_scope": "SLIM_NOOP",
            "pt_routing": {"scope": "SKIP"},
            "model_routing": {"mode": "NOOP"},
        }

    harvest_scope = classify_harvest_scope(coverage_classes)
    pt_scope = classify_harvest_scope(coverage_classes) if pt_on else "SKIP"
    model_mode = model_channel_decision(has_2_model_dir, model_on)

    return {
        "run": True,
        "reason": reason,
        "harvest_scope": harvest_scope,
        "pt_routing": {"scope": pt_scope},
        "model_routing": {"mode": model_mode},
    }
