"""
BL-331 RED Tests: post_item_learning.py (AK-1/2/3/5)

Diese Tests muessen FEHLSCHLAGEN bis GREEN-Worker post_item_learning.py implementiert.
Importiert from post_item_learning -> ImportError = RED.

AK-1: should_run_learning(global_modus, hil, all_pl_done, all_batches_done) -> bool
AK-2: classify_harvest_scope(coverage_classes: list[str]) -> str
AK-3: model_channel_decision(has_2_model_dir: bool, model_param_on: bool) -> str
AK-5: post_item_learning_gate(...) -> dict (komposit aus AK-1/2/3)
"""
from __future__ import annotations

import pytest

# RED: Dieses Modul existiert noch nicht -> ImportError bei Lauf ohne Implementierung.
# GREEN-Worker implementiert .claude/scripts/post_item_learning.py gemaess Spec.
from post_item_learning import (
    should_run_learning,
    classify_harvest_scope,
    model_channel_decision,
    post_item_learning_gate,
)


# ===========================================================================
# AK-1: should_run_learning — Gate-Bedingung (INV-LEARN-GATE)
# Alle 4 UND-Bedingungen muessen erfuellt sein -> True, sonst False.
# ===========================================================================

class TestShouldRunLearningGateOpen:
    """AK-1: Gate offen NUR wenn ALLE 4 Bedingungen erfuellt."""

    def test_gate_open_when_all_conditions_met(self):
        """Goldpfad: big_dark_factory + hil=off + all_pl_done=True + all_batches_done=True."""
        assert should_run_learning("big_dark_factory", "off", True, True) is True


class TestShouldRunLearningGateClosed:
    """AK-1: Gate bleibt zu wenn irgendeine Bedingung nicht erfuellt ist."""

    def test_gate_closed_wrong_modus_dark_factory(self):
        """'dark_factory' (ohne 'big_') ist NICHT 'big_dark_factory'."""
        assert should_run_learning("dark_factory", "off", True, True) is False

    def test_gate_closed_wrong_modus_manual(self):
        """'manual' Modus schliesst Gate."""
        assert should_run_learning("manual", "off", True, True) is False

    def test_gate_closed_empty_modus(self):
        """Leerer Modus-String schliesst Gate."""
        assert should_run_learning("", "off", True, True) is False

    def test_gate_closed_hil_on(self):
        """hil='on' schliesst Gate (HIL-Betrieb, kein autonomes Lernen)."""
        assert should_run_learning("big_dark_factory", "on", True, True) is False

    def test_gate_closed_hil_cycle(self):
        """hil='cycle' ist NICHT 'off' -> Gate bleibt zu."""
        assert should_run_learning("big_dark_factory", "cycle", True, True) is False

    def test_gate_closed_hil_phase(self):
        """hil='phase' ist NICHT 'off' -> Gate bleibt zu."""
        assert should_run_learning("big_dark_factory", "phase", True, True) is False

    def test_gate_closed_pl_not_done(self):
        """all_pl_done=False: noch offene PL-Items -> Gate bleibt zu."""
        assert should_run_learning("big_dark_factory", "off", False, True) is False

    def test_gate_closed_batches_not_done(self):
        """all_batches_done=False: noch laufende Batches -> Gate bleibt zu."""
        assert should_run_learning("big_dark_factory", "off", True, False) is False

    def test_gate_closed_multiple_conditions_fail_wrong_modus_and_hil(self):
        """Mehrere Bedingungen gleichzeitig nicht erfuellt -> False."""
        assert should_run_learning("dark_factory", "on", False, False) is False

    def test_gate_closed_multiple_conditions_fail_pl_and_batches(self):
        """pl_done=False + batches_done=False -> False, auch bei richtigen anderen Params."""
        assert should_run_learning("big_dark_factory", "off", False, False) is False


# ===========================================================================
# AK-2: classify_harvest_scope — Proportionalitaet (INV-LEARN-PROPORTIONAL)
# coverage_classes: list[str] -> "FULL_HARVEST" | "SLIM_NOOP"
# ===========================================================================

class TestClassifyHarvestScopeSlimNoop:
    """AK-2: SLIM_NOOP wenn ALLE Batches markdown_target_uncoverable oder Liste leer."""

    def test_slim_noop_all_markdown_uncoverable(self):
        """Alle Batches uncoverable -> SLIM_NOOP (BL-321-Muster, doc-Fold)."""
        result = classify_harvest_scope(
            ["markdown_target_uncoverable", "markdown_target_uncoverable"]
        )
        assert result == "SLIM_NOOP"

    def test_slim_noop_single_markdown(self):
        """Einzelner uncoverable Batch -> SLIM_NOOP."""
        assert classify_harvest_scope(["markdown_target_uncoverable"]) == "SLIM_NOOP"

    def test_slim_noop_empty_list(self):
        """Leere Liste -> SLIM_NOOP (kein Coverage-Info = kein Harvest)."""
        assert classify_harvest_scope([]) == "SLIM_NOOP"

    def test_slim_noop_none_values(self):
        """None-Werte werden als 'markdown_target_uncoverable' behandelt -> SLIM_NOOP."""
        assert classify_harvest_scope([None, None]) == "SLIM_NOOP"

    def test_slim_noop_bl321_pattern(self):
        """BL-321 war doc-Fold: alle Batches uncoverable -> SLIM_NOOP."""
        assert classify_harvest_scope(["markdown_target_uncoverable"]) == "SLIM_NOOP"


class TestClassifyHarvestScopeFullHarvest:
    """AK-2: FULL_HARVEST wenn mind. 1 Batch NICHT markdown_target_uncoverable."""

    def test_full_harvest_single_testable_batch(self):
        """'testable' coverage_class -> FULL_HARVEST."""
        assert classify_harvest_scope(["testable"]) == "FULL_HARVEST"

    def test_full_harvest_single_covered_batch(self):
        """'covered' coverage_class -> FULL_HARVEST."""
        assert classify_harvest_scope(["covered"]) == "FULL_HARVEST"

    def test_full_harvest_single_code_batch(self):
        """'code' coverage_class -> FULL_HARVEST."""
        assert classify_harvest_scope(["code"]) == "FULL_HARVEST"

    def test_full_harvest_mixed_batches_testable_and_uncoverable(self):
        """Gemischt: mind. 1 code -> FULL_HARVEST dominiert."""
        result = classify_harvest_scope(["testable", "markdown_target_uncoverable"])
        assert result == "FULL_HARVEST"

    def test_full_harvest_mixed_batches_uncoverable_then_covered(self):
        """Reihenfolge spielt keine Rolle: code-Batch genug fuer FULL_HARVEST."""
        result = classify_harvest_scope(["markdown_target_uncoverable", "covered"])
        assert result == "FULL_HARVEST"

    def test_full_harvest_bl313_pattern(self):
        """BL-313 war CODE-BL mit testable-Batches -> FULL_HARVEST."""
        result = classify_harvest_scope(["testable", "testable"])
        assert result == "FULL_HARVEST"


# ===========================================================================
# AK-3: model_channel_decision — Model-Kanal-Routing
# (has_2_model_dir: bool, model_param_on: bool) -> str
# ===========================================================================

class TestModelChannelDecision:
    """AK-3: Routing-String-Entscheidung fuer Model-Kanal."""

    def test_noop_when_param_off_with_2_model_dir(self):
        """model_param_on=False -> NOOP, egal ob 2_Model/ existiert."""
        assert model_channel_decision(has_2_model_dir=True, model_param_on=False) == "NOOP"

    def test_noop_when_param_off_without_2_model_dir(self):
        """model_param_on=False -> NOOP, egal ob 2_Model/ existiert."""
        assert model_channel_decision(has_2_model_dir=False, model_param_on=False) == "NOOP"

    def test_full_model_sync_when_2_model_dir_exists(self):
        """has_2_model_dir=True + param=on -> FULL_MODEL_SYNC (story-level)."""
        assert model_channel_decision(has_2_model_dir=True, model_param_on=True) == "FULL_MODEL_SYNC"

    def test_domain_direct_when_no_2_model_dir(self):
        """has_2_model_dir=False + param=on -> DOMAIN_DIRECT (BL-313-Fallback-Muster)."""
        assert model_channel_decision(has_2_model_dir=False, model_param_on=True) == "DOMAIN_DIRECT"

    def test_domain_direct_is_fallback_not_error(self):
        """Fehlende 2_Model/ ist KEIN Fehler — valider DOMAIN_DIRECT-Pfad."""
        result = model_channel_decision(False, True)
        assert isinstance(result, str)
        assert result == "DOMAIN_DIRECT"

    def test_model_sync_bl331_itself(self):
        """BL-331 hat 2_Model/ (dieses BL selbst) -> FULL_MODEL_SYNC bei param=on."""
        assert model_channel_decision(has_2_model_dir=True, model_param_on=True) == "FULL_MODEL_SYNC"


# ===========================================================================
# AK-5: post_item_learning_gate — Haupt-Gate-Router (komposiert AK-1/2/3)
# INV-LEARN-NO-SIDEEFFECT: reiner Decider, kein File-IO, kein Manifest-Write.
# ===========================================================================

class TestPostItemLearningGateClosed:
    """AK-5: Gate geschlossen -> run=False, pt_routing.scope=SKIP."""

    def test_gate_closed_returns_run_false(self):
        """Falscher Modus -> run=False, pt_routing.scope=SKIP."""
        result = post_item_learning_gate("manual", "off", True, True, [], True)
        assert result["run"] is False
        assert result["pt_routing"]["scope"] == "SKIP"

    def test_gate_closed_model_routing_noop(self):
        """Gate geschlossen -> model_routing.mode=NOOP."""
        result = post_item_learning_gate("manual", "off", True, True, [], True)
        assert result["model_routing"]["mode"] == "NOOP"

    def test_gate_closed_hil_on(self):
        """hil=on -> Gate geschlossen, run=False."""
        result = post_item_learning_gate("big_dark_factory", "on", True, True, ["testable"], True)
        assert result["run"] is False


class TestPostItemLearningGateOpen:
    """AK-5: Gate offen -> run=True, Routing aus AK-2/3."""

    def test_gate_open_full_harvest_full_model_sync(self):
        """CODE-BL mit 2_Model/ -> run=True, FULL_HARVEST, FULL_MODEL_SYNC."""
        result = post_item_learning_gate(
            "big_dark_factory", "off", True, True,
            ["testable", "testable"], True, pt_on=True, model_on=True
        )
        assert result["run"] is True
        assert result["harvest_scope"] == "FULL_HARVEST"
        assert result["pt_routing"]["scope"] == "FULL_HARVEST"
        assert result["model_routing"]["mode"] == "FULL_MODEL_SYNC"

    def test_gate_open_slim_noop_domain_direct(self):
        """doc-Fold ohne 2_Model/ -> run=True, SLIM_NOOP, DOMAIN_DIRECT."""
        result = post_item_learning_gate(
            "big_dark_factory", "off", True, True,
            ["markdown_target_uncoverable"], False, pt_on=True, model_on=True
        )
        assert result["run"] is True
        assert result["harvest_scope"] == "SLIM_NOOP"
        assert result["pt_routing"]["scope"] == "SLIM_NOOP"
        assert result["model_routing"]["mode"] == "DOMAIN_DIRECT"

    def test_gate_open_pt_off_skips_harvest(self):
        """pt_on=False -> pt_routing.scope=SKIP, model laeuft trotzdem."""
        result = post_item_learning_gate(
            "big_dark_factory", "off", True, True,
            ["testable"], True, pt_on=False, model_on=True
        )
        assert result["run"] is True
        assert result["pt_routing"]["scope"] == "SKIP"
        assert result["model_routing"]["mode"] == "FULL_MODEL_SYNC"

    def test_gate_open_model_off_noop_model(self):
        """model_on=False -> model_routing.mode=NOOP, PT laeuft trotzdem."""
        result = post_item_learning_gate(
            "big_dark_factory", "off", True, True,
            ["testable"], True, pt_on=True, model_on=False
        )
        assert result["run"] is True
        assert result["pt_routing"]["scope"] == "FULL_HARVEST"
        assert result["model_routing"]["mode"] == "NOOP"

    def test_gate_open_both_off_everything_noop(self):
        """pt_on=False + model_on=False -> beide SKIP/NOOP, aber run=True (Gate offen)."""
        result = post_item_learning_gate(
            "big_dark_factory", "off", True, True,
            ["testable"], True, pt_on=False, model_on=False
        )
        assert result["run"] is True
        assert result["pt_routing"]["scope"] == "SKIP"
        assert result["model_routing"]["mode"] == "NOOP"


class TestPostItemLearningGateProperties:
    """AK-5: Strukturelle Eigenschaften des Gate-Returns."""

    def test_no_sideeffect_pure_function_idempotent(self):
        """Gleiche Inputs -> gleiche Outputs (Idempotenz-Basis, INV-LEARN-NO-SIDEEFFECT)."""
        args = ("big_dark_factory", "off", True, True, ["testable"], True)
        r1 = post_item_learning_gate(*args)
        r2 = post_item_learning_gate(*args)
        assert r1 == r2

    def test_reason_contains_modus_when_gate_open(self):
        """reason-Feld enthaelt den globalen Modus (Begruendung nachvollziehbar)."""
        result = post_item_learning_gate("big_dark_factory", "off", True, True, [], True)
        assert "big_dark_factory" in result["reason"]

    def test_reason_contains_hil_when_gate_open(self):
        """reason-Feld enthaelt den hil-Wert."""
        result = post_item_learning_gate("big_dark_factory", "off", True, True, [], True)
        assert "off" in result["reason"]

    def test_return_keys_present(self):
        """Return-Dict enthaelt alle erwarteten Keys."""
        result = post_item_learning_gate("big_dark_factory", "off", True, True, ["testable"], True)
        assert set(result.keys()) == {"run", "reason", "harvest_scope", "pt_routing", "model_routing"}
        assert "scope" in result["pt_routing"]
        assert "mode" in result["model_routing"]
