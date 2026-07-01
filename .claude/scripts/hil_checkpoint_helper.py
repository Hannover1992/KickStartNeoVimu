"""
hil_checkpoint_helper.py — BL-163 HiL-Symmetrie

Berechnet ob ein HiL-Checkpoint ausgeloest werden soll basierend auf
Checkpoint-Klasse (A/B/C), HiL-Modus (off/manual/cycle/phase/full) und Kontext.

CLI: check / list-checkpoints / report-mode
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CheckpointClass(str, Enum):
    """A=Decision, B=Validate, C=Continue — BL-163 Klassifikation."""
    A = "A"  # Pipeline-Routing-Entscheid, hoecstes Risiko
    B = "B"  # Berechnetes/klassifiziertes Ergebnis, mittleres Risiko
    C = "C"  # Qualitaetspruefung, minimales Risiko


class HilMode(str, Enum):
    """HIL-Modi aus _session_params.md."""
    OFF = "off"
    MANUAL = "manual"
    CYCLE = "cycle"
    PHASE = "phase"
    FULL = "full"


# Alle bekannten Checkpoints aus BL-163 hil_symmetrie_pattern.md
KNOWN_CHECKPOINTS: dict[str, dict] = {
    "findings_review": {
        "phase": "A Phase 0.5.2",
        "berater": "_A_berater_findingsReview",
        "class": CheckpointClass.B,
        "cluster_focus": "Findings: Wichtigkeit, Scope, Konflikte",
    },
    "spec_ak_review": {
        "phase": "A Phase 4 Spec",
        "berater": "_spec",
        "class": CheckpointClass.B,
        "cluster_focus": "AKs: Vollstaendigkeit, Machbarkeit, Widersprueche",
    },
    "kscore_review": {
        "phase": "A Phase 5 K-Score",
        "berater": "_K_score",
        "class": CheckpointClass.B,
        "cluster_focus": "Score-Outlier, Pattern-Match-Confidence, First-Principle-Beleg",
    },
    "gap_review": {
        "phase": "A Phase 6 Gap",
        "berater": "_gap",
        "class": CheckpointClass.B,
        "cluster_focus": "PARTIAL-Items, COVERED-Verifikation, MISSING-Priorisierung",
    },
    "reifegrad_review": {
        "phase": "A Phase 7 Reifegrad",
        "berater": "_A_berater_metadatenAggregation",
        "class": CheckpointClass.A,
        "cluster_focus": "Aggregat-Plausibilitaet, Schwellenwert-Begruendung, Routing-Hint",
    },
    "model_review": {
        "phase": "A Phase 2 Model",
        "berater": "_model",
        "class": CheckpointClass.C,
        "cluster_focus": "Modell-Vollstaendigkeit (optional)",
    },
}


@dataclass
class HilContext:
    """Kontext fuer HiL-Checkpoint-Entscheidung."""
    checkpoint_id: str
    checkpoint_class: CheckpointClass
    hil_mode: HilMode
    is_cycle_boundary: bool = False
    no_hil_review_flag: bool = False


def should_trigger_hil(
    checkpoint_class: CheckpointClass,
    mode: HilMode,
    context: Optional[HilContext] = None,
) -> bool:
    """
    Bestimmt ob ein HiL-Review ausgeloest werden soll.

    INV-HIL-1: Bei phase MUSS Klasse A+B reviewed werden.
    INV-HIL-5: Bei off DARF kein Review ausgefuehrt werden.

    Args:
        checkpoint_class: A (Decision), B (Validate) oder C (Continue)
        mode: HiL-Modus aus _session_params.md
        context: Optionaler Kontext (no_hil_review_flag, is_cycle_boundary)

    Returns:
        True wenn HiL-Review ausgeloest werden soll, False sonst.
    """
    # INV-HIL-5: off und manual → niemals Review
    if mode in (HilMode.OFF, HilMode.MANUAL):
        return False

    # Explizites --no-hil-review Flag respektieren (Ausnahme von INV-HIL-1)
    if context is not None and context.no_hil_review_flag:
        return False

    if mode == HilMode.CYCLE:
        # cycle: nur bei Cycle-Grenzen, und nur Klasse A+B
        if context is None or not context.is_cycle_boundary:
            return False
        return checkpoint_class in (CheckpointClass.A, CheckpointClass.B)

    if mode == HilMode.PHASE:
        # INV-HIL-1: phase → Klasse A+B immer, C niemals
        return checkpoint_class in (CheckpointClass.A, CheckpointClass.B)

    if mode == HilMode.FULL:
        # full → alle Klassen
        return True

    return False


def get_interaction_form(
    checkpoint_class: CheckpointClass,
    mode: HilMode,
    context: Optional[HilContext] = None,
) -> str:
    """
    Gibt die korrekte Interaktionsform zurueck.

    Returns:
        'cluster_assay_question' | 'simple_confirm' | 'auto_continue'
    """
    if not should_trigger_hil(checkpoint_class, mode, context):
        return "auto_continue"

    if mode == HilMode.CYCLE:
        return "simple_confirm"

    # phase oder full mit Klasse A/B/C
    return "cluster_assay_question"


def get_checkpoint_info(checkpoint_id: str) -> Optional[dict]:
    """Gibt Infos zu einem bekannten Checkpoint zurueck."""
    return KNOWN_CHECKPOINTS.get(checkpoint_id)


def report_mode(mode: HilMode) -> dict:
    """
    Erstellt einen vollstaendigen Report welche Checkpoints bei gegebenem Modus aktiv sind.

    Returns:
        Dict mit aktiven/inaktiven Checkpoints und Interaktionsform.
    """
    active = []
    inactive = []

    for cp_id, cp_info in KNOWN_CHECKPOINTS.items():
        cp_class = cp_info["class"]
        triggers = should_trigger_hil(cp_class, mode)
        interaction = get_interaction_form(cp_class, mode)
        entry = {
            "id": cp_id,
            "phase": cp_info["phase"],
            "berater": cp_info["berater"],
            "class": cp_class.value,
            "interaction": interaction,
            "cluster_focus": cp_info["cluster_focus"],
        }
        if triggers:
            active.append(entry)
        else:
            inactive.append(entry)

    return {
        "hil_mode": mode.value,
        "active_checkpoints": active,
        "inactive_checkpoints": inactive,
        "summary": f"{len(active)} aktiv, {len(inactive)} inaktiv",
    }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def cmd_check(args: argparse.Namespace) -> int:
    checkpoint_class = CheckpointClass(args.checkpoint_class.upper())
    mode = HilMode(args.mode.lower())
    context = HilContext(
        checkpoint_id=args.checkpoint_id or "unknown",
        checkpoint_class=checkpoint_class,
        hil_mode=mode,
        is_cycle_boundary=args.cycle_boundary,
        no_hil_review_flag=args.no_hil_review,
    )
    triggers = should_trigger_hil(checkpoint_class, mode, context)
    interaction = get_interaction_form(checkpoint_class, mode, context)
    result = {
        "triggers": triggers,
        "interaction": interaction,
        "checkpoint_class": checkpoint_class.value,
        "hil_mode": mode.value,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


def cmd_list_checkpoints(_args: argparse.Namespace) -> int:
    print(json.dumps(KNOWN_CHECKPOINTS, indent=2, default=lambda o: o.value, ensure_ascii=False))
    return 0


def cmd_report_mode(args: argparse.Namespace) -> int:
    mode = HilMode(args.mode.lower())
    result = report_mode(mode)
    print(json.dumps(result, indent=2, default=lambda o: o.value, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="HiL-Checkpoint-Helper — BL-163",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check
    p_check = subparsers.add_parser("check", help="Pruefe ob HiL ausgeloest wird")
    p_check.add_argument("checkpoint_class", choices=["A", "B", "C", "a", "b", "c"],
                         help="Checkpoint-Klasse (A=Decision, B=Validate, C=Continue)")
    p_check.add_argument("mode", help="HiL-Modus (off/manual/cycle/phase/full)")
    p_check.add_argument("--checkpoint-id", dest="checkpoint_id", default=None)
    p_check.add_argument("--cycle-boundary", action="store_true", default=False,
                         help="Handelt es sich um eine Cycle-Grenze?")
    p_check.add_argument("--no-hil-review", action="store_true", default=False,
                         help="--no-hil-review Flag gesetzt?")
    p_check.set_defaults(func=cmd_check)

    # list-checkpoints
    p_list = subparsers.add_parser("list-checkpoints", help="Alle bekannten Checkpoints")
    p_list.set_defaults(func=cmd_list_checkpoints)

    # report-mode
    p_report = subparsers.add_parser("report-mode", help="Report fuer einen HiL-Modus")
    p_report.add_argument("mode", help="HiL-Modus (off/manual/cycle/phase/full)")
    p_report.set_defaults(func=cmd_report_mode)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
