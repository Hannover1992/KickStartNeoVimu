"""
Tests fuer hil_checkpoint_helper.py — BL-163 HiL-Symmetrie

Deckt should_trigger_hil() Kernlogik und get_interaction_form() ab.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from hil_checkpoint_helper import (
    CheckpointClass,
    HilContext,
    HilMode,
    get_interaction_form,
    report_mode,
    should_trigger_hil,
)


# ─── should_trigger_hil ───────────────────────────────────────────────────────


def test_off_mode_never_triggers_any_class():
    """INV-HIL-5: hil=off darf niemals triggern — fuer alle Klassen."""
    for cls in CheckpointClass:
        assert not should_trigger_hil(cls, HilMode.OFF), (
            f"hil=off sollte fuer Klasse {cls} niemals triggern"
        )


def test_phase_mode_triggers_class_a_and_b_but_not_c():
    """INV-HIL-1: hil=phase muss Klasse A+B triggern, C nicht."""
    assert should_trigger_hil(CheckpointClass.A, HilMode.PHASE)
    assert should_trigger_hil(CheckpointClass.B, HilMode.PHASE)
    assert not should_trigger_hil(CheckpointClass.C, HilMode.PHASE)


def test_full_mode_triggers_all_classes():
    """hil=full triggert A+B+C."""
    for cls in CheckpointClass:
        assert should_trigger_hil(cls, HilMode.FULL), (
            f"hil=full sollte Klasse {cls} triggern"
        )


def test_no_hil_review_flag_suppresses_phase_trigger():
    """--no-hil-review Flag unterdrueckt auch Pflicht-Review bei hil=phase."""
    context = HilContext(
        checkpoint_id="spec_ak_review",
        checkpoint_class=CheckpointClass.B,
        hil_mode=HilMode.PHASE,
        no_hil_review_flag=True,
    )
    assert not should_trigger_hil(CheckpointClass.B, HilMode.PHASE, context)


def test_cycle_mode_triggers_only_at_cycle_boundary_for_a_b():
    """hil=cycle triggert nur an Cycle-Grenzen, und nur Klasse A+B."""
    # Kein Cycle-Boundary → kein Trigger
    ctx_no_boundary = HilContext(
        checkpoint_id="reifegrad_review",
        checkpoint_class=CheckpointClass.A,
        hil_mode=HilMode.CYCLE,
        is_cycle_boundary=False,
    )
    assert not should_trigger_hil(CheckpointClass.A, HilMode.CYCLE, ctx_no_boundary)

    # Cycle-Boundary + Klasse A → Trigger
    ctx_boundary = HilContext(
        checkpoint_id="reifegrad_review",
        checkpoint_class=CheckpointClass.A,
        hil_mode=HilMode.CYCLE,
        is_cycle_boundary=True,
    )
    assert should_trigger_hil(CheckpointClass.A, HilMode.CYCLE, ctx_boundary)

    # Cycle-Boundary + Klasse C → kein Trigger
    ctx_c_boundary = HilContext(
        checkpoint_id="model_review",
        checkpoint_class=CheckpointClass.C,
        hil_mode=HilMode.CYCLE,
        is_cycle_boundary=True,
    )
    assert not should_trigger_hil(CheckpointClass.C, HilMode.CYCLE, ctx_c_boundary)


# ─── get_interaction_form ─────────────────────────────────────────────────────


def test_interaction_form_auto_continue_for_off():
    """hil=off → immer auto_continue fuer alle Klassen."""
    for cls in CheckpointClass:
        form = get_interaction_form(cls, HilMode.OFF)
        assert form == "auto_continue", f"Erwartet auto_continue, bekam {form}"


def test_interaction_form_cluster_assay_for_phase_class_a():
    """hil=phase + Klasse A → cluster_assay_question."""
    form = get_interaction_form(CheckpointClass.A, HilMode.PHASE)
    assert form == "cluster_assay_question"


def test_interaction_form_simple_confirm_for_cycle_boundary():
    """hil=cycle + Cycle-Boundary + Klasse B → simple_confirm."""
    ctx = HilContext(
        checkpoint_id="spec_ak_review",
        checkpoint_class=CheckpointClass.B,
        hil_mode=HilMode.CYCLE,
        is_cycle_boundary=True,
    )
    form = get_interaction_form(CheckpointClass.B, HilMode.CYCLE, ctx)
    assert form == "simple_confirm"


# ─── report_mode ─────────────────────────────────────────────────────────────


def test_report_mode_off_has_all_inactive():
    """report_mode(off) → alle Checkpoints inaktiv."""
    result = report_mode(HilMode.OFF)
    assert len(result["active_checkpoints"]) == 0
    assert len(result["inactive_checkpoints"]) > 0


def test_report_mode_phase_activates_a_and_b_checkpoints():
    """report_mode(phase) → Klasse A+B aktiv, C inaktiv."""
    result = report_mode(HilMode.PHASE)
    active_classes = {cp["class"] for cp in result["active_checkpoints"]}
    inactive_classes = {cp["class"] for cp in result["inactive_checkpoints"]}
    assert "A" in active_classes
    assert "B" in active_classes
    assert "C" in inactive_classes
    assert "C" not in active_classes


if __name__ == "__main__":
    # Einfacher Test-Runner ohne pytest-Abhaengigkeit
    tests = [
        test_off_mode_never_triggers_any_class,
        test_phase_mode_triggers_class_a_and_b_but_not_c,
        test_full_mode_triggers_all_classes,
        test_no_hil_review_flag_suppresses_phase_trigger,
        test_cycle_mode_triggers_only_at_cycle_boundary_for_a_b,
        test_interaction_form_auto_continue_for_off,
        test_interaction_form_cluster_assay_for_phase_class_a,
        test_interaction_form_simple_confirm_for_cycle_boundary,
        test_report_mode_off_has_all_inactive,
        test_report_mode_phase_activates_a_and_b_checkpoints,
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {e}")
            failed += 1
    print(f"\n{len(tests) - failed}/{len(tests)} Tests bestanden.")
    sys.exit(0 if failed == 0 else 1)
