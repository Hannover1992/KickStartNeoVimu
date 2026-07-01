"""
TDD-RED Tests fuer BL-272: Per-Backlog Finish-Gate + Finish-Sequenz.

Import gegen NICHT-existierendes Modul finish_gate.py -> ImportError = RED.

API (definiert in BL-272_Spec.md):

    finish_gate_decision(pl_empty: bool, bdf: bool, hil: str) -> str
        "NOT_READY"   wenn pl_empty=False (Gate gesperrt, PL hat noch Items)
        "AUTO_FINISH" wenn pl_empty=True und bdf=True
        "HIL_WAIT"    wenn pl_empty=True und bdf=False
        hil-Param ist orthogonal (BL-159) — beeinflusst Entscheidung in V1 NICHT direkt

    harvest_source_from_completed(manifest_state: dict) -> list
        Liest aus manifest_state["completed_sub_batches"] (Liste von Batch-Dicts mit "items").
        Gibt flache Liste aller completed Items zurueck.
        Graceful-empty bei fehlendem Key (kein KeyError).

    build_finish_sequence(manifest_state: dict, model_split_available: bool = False) -> list
        Gibt geordnete Step-Liste zurueck:
          - {"step": "model_split", "status": "SKIPPED", "reason": ...}  wenn unavailable
          - {"step": "model_split", "status": "READY"}                   wenn available
          - {"step": "pt_harvest", "status": "READY",
             "source": "completed_history", "items": [...]}
          - {"step": "state_transition", "status": "READY", "target": "DONE"}

    hil_bad_path_route(user_pl_items: list) -> dict
        user_pl_items leer/None -> {"action": "PROCEED_FINISH"}
        user_pl_items nicht leer -> {"action": "IDF_RECHECK",
                                     "skill_arg": "--mode=recheck --from=backlog_hil",
                                     "new_pl_items": user_pl_items}
"""

import pytest
from finish_gate import (
    finish_gate_decision,
    harvest_source_from_completed,
    build_finish_sequence,
    hil_bad_path_route,
)


# ---------------------------------------------------------------------------
# AK-1: finish_gate_decision — 6 Tests
# ---------------------------------------------------------------------------

class TestFinishGateDecision:

    def test_not_ready_when_pl_not_empty_bdf_true(self):
        """pl_empty=False + bdf=True -> NOT_READY (Gate gesperrt)."""
        result = finish_gate_decision(pl_empty=False, bdf=True, hil="off")
        assert result == "NOT_READY"

    def test_not_ready_when_pl_not_empty_bdf_false(self):
        """pl_empty=False + bdf=False -> NOT_READY (Gate gesperrt)."""
        result = finish_gate_decision(pl_empty=False, bdf=False, hil="off")
        assert result == "NOT_READY"

    def test_auto_finish_when_pl_empty_and_bdf_true(self):
        """pl_empty=True + bdf=True -> AUTO_FINISH (Engine autonom)."""
        result = finish_gate_decision(pl_empty=True, bdf=True, hil="off")
        assert result == "AUTO_FINISH"

    def test_hil_wait_when_pl_empty_and_bdf_false(self):
        """pl_empty=True + bdf=False -> HIL_WAIT (Mensch muss freigeben)."""
        result = finish_gate_decision(pl_empty=True, bdf=False, hil="off")
        assert result == "HIL_WAIT"

    def test_hil_on_does_not_override_not_ready(self):
        """hil='on' bei pl_empty=False -> NOT_READY (hil aendert Gate-Sperre nicht)."""
        result = finish_gate_decision(pl_empty=False, bdf=False, hil="on")
        assert result == "NOT_READY"

    def test_auto_finish_hil_off_bdf_true(self):
        """hil='off' + bdf=True + pl_empty=True -> AUTO_FINISH (hil orthogonal, aendert nichts)."""
        result = finish_gate_decision(pl_empty=True, bdf=True, hil="off")
        assert result == "AUTO_FINISH"


# ---------------------------------------------------------------------------
# AK-2a: harvest_source_from_completed — 3 Tests
# ---------------------------------------------------------------------------

class TestHarvestSourceFromCompleted:

    def test_completed_source_empty_when_no_completed_batches(self):
        """manifest ohne completed_sub_batches -> leere Liste, kein Fehler."""
        manifest = {"live_pl": ["some_item"]}  # keine completed_sub_batches
        result = harvest_source_from_completed(manifest)
        assert result == []

    def test_completed_source_extracts_items_from_completed_batches(self):
        """manifest mit 2 completed_sub_batches a 3 Items -> 6 Items in output."""
        manifest = {
            "completed_sub_batches": [
                {
                    "batch_id": "batch_1",
                    "items": [
                        {"id": "BL-001", "title": "Item 1"},
                        {"id": "BL-002", "title": "Item 2"},
                        {"id": "BL-003", "title": "Item 3"},
                    ],
                },
                {
                    "batch_id": "batch_2",
                    "items": [
                        {"id": "BL-004", "title": "Item 4"},
                        {"id": "BL-005", "title": "Item 5"},
                        {"id": "BL-006", "title": "Item 6"},
                    ],
                },
            ]
        }
        result = harvest_source_from_completed(manifest)
        assert len(result) == 6
        ids = [item["id"] for item in result]
        assert "BL-001" in ids
        assert "BL-006" in ids

    def test_completed_source_graceful_empty_key_missing(self):
        """manifest = {} -> [] (kein KeyError, graceful-empty)."""
        result = harvest_source_from_completed({})
        assert result == []

    def test_completed_source_reads_completed_not_live_pl(self):
        """Fixture mit leerer live-PL aber gefuellter completed-Historie -> gibt completed zurueck.

        Prueft: harvest_source_from_completed liest COMPLETED-Items, NICHT live-PL.
        """
        manifest = {
            "live_pl": [],  # leere live-PL (Backlog-Ende-Situation)
            "completed_sub_batches": [
                {
                    "batch_id": "batch_final",
                    "items": [
                        {"id": "BL-010", "title": "Completed Item A"},
                        {"id": "BL-011", "title": "Completed Item B"},
                    ],
                }
            ],
        }
        result = harvest_source_from_completed(manifest)
        # Muss aus completed_sub_batches lesen, nicht aus leerer live_pl
        assert len(result) == 2
        assert result[0]["id"] in ("BL-010", "BL-011")


# ---------------------------------------------------------------------------
# AK-2b: build_finish_sequence — 7 Tests  (3 + 4 Restgruppe = 7 insgesamt)
# ---------------------------------------------------------------------------

class TestBuildFinishSequence:

    def _empty_manifest(self):
        return {"completed_sub_batches": []}

    def _manifest_with_items(self):
        return {
            "completed_sub_batches": [
                {
                    "batch_id": "b1",
                    "items": [
                        {"id": "BL-100", "title": "Item X"},
                        {"id": "BL-101", "title": "Item Y"},
                    ],
                }
            ]
        }

    def test_model_split_skipped_when_unavailable(self):
        """model_split_available=False -> erster Step hat status SKIPPED."""
        steps = build_finish_sequence(
            manifest_state=self._empty_manifest(),
            model_split_available=False,
        )
        assert len(steps) >= 1
        first = steps[0]
        assert first["step"] == "model_split"
        assert first["status"].upper() in ("SKIPPED", "SKIP")

    def test_model_split_skipped_reason_mentions_bl270(self):
        """model_split_available=False -> reason des SKIPPED-Steps enthaelt 'BL-270'."""
        steps = build_finish_sequence(
            manifest_state=self._empty_manifest(),
            model_split_available=False,
        )
        first = steps[0]
        assert "BL-270" in first.get("reason", ""), (
            f"Erwartet 'BL-270' in reason, got: {first}"
        )

    def test_model_split_ready_when_available(self):
        """model_split_available=True -> erster Step hat status READY."""
        steps = build_finish_sequence(
            manifest_state=self._empty_manifest(),
            model_split_available=True,
        )
        first = steps[0]
        assert first["step"] == "model_split"
        assert first["status"].upper() == "READY"

    def test_pt_harvest_step_present_with_source_completed_history(self):
        """pt_harvest-Step hat source='completed_history'."""
        steps = build_finish_sequence(
            manifest_state=self._manifest_with_items(),
            model_split_available=False,
        )
        pt_steps = [s for s in steps if s["step"] == "pt_harvest"]
        assert len(pt_steps) == 1
        assert pt_steps[0]["source"] == "completed_history"

    def test_pt_harvest_step_has_items_from_manifest(self):
        """pt_harvest-Step hat items aus manifest (nicht leer wenn completed vorhanden)."""
        steps = build_finish_sequence(
            manifest_state=self._manifest_with_items(),
            model_split_available=False,
        )
        pt_steps = [s for s in steps if s["step"] == "pt_harvest"]
        assert len(pt_steps[0]["items"]) == 2

    def test_state_transition_last_step(self):
        """state_transition-Step ist immer letzter Step."""
        steps = build_finish_sequence(
            manifest_state=self._empty_manifest(),
            model_split_available=False,
        )
        last = steps[-1]
        assert last["step"] == "state_transition"
        assert last.get("target") == "DONE"

    def test_state_transition_is_ready(self):
        """state_transition-Step hat status READY."""
        steps = build_finish_sequence(
            manifest_state=self._empty_manifest(),
            model_split_available=False,
        )
        last = steps[-1]
        assert last["status"].upper() == "READY"


# ---------------------------------------------------------------------------
# AK-3: hil_bad_path_route — 5 Tests
# ---------------------------------------------------------------------------

class TestHilBadPathRoute:

    def test_proceed_finish_when_no_items(self):
        """user_pl_items=[] -> {"action": "PROCEED_FINISH"}."""
        result = hil_bad_path_route([])
        assert result == {"action": "PROCEED_FINISH"}

    def test_proceed_finish_when_none(self):
        """user_pl_items=None -> {"action": "PROCEED_FINISH"}."""
        result = hil_bad_path_route(None)
        assert result == {"action": "PROCEED_FINISH"}

    def test_idf_recheck_when_items_given(self):
        """user_pl_items=[...] -> action='IDF_RECHECK'."""
        result = hil_bad_path_route(["Fix auth", "Add logging"])
        assert result["action"] == "IDF_RECHECK"

    def test_idf_recheck_skill_arg_contains_backlog_hil(self):
        """IDF_RECHECK result hat skill_arg mit '--from=backlog_hil'."""
        result = hil_bad_path_route(["Fix auth"])
        assert "--from=backlog_hil" in result.get("skill_arg", ""), (
            f"Erwartet '--from=backlog_hil' in skill_arg, got: {result}"
        )

    def test_hil_bad_path_preserves_new_pl_items(self):
        """neue Items in output['new_pl_items'] identisch zu input."""
        items = ["Fix auth", "Add logging", "Update docs"]
        result = hil_bad_path_route(items)
        assert result.get("new_pl_items") == items
