"""
TDD RED Tests fuer sdf_last_item_detect.classify_route (BL-429 batch_1)
Alle Tests MUESSEN fehlschlagen (ModuleNotFoundError) solange sdf_last_item_detect.py fehlt.
"""
import pytest

from sdf_last_item_detect import classify_route


# --- TC-1: WEG 3 / TERMINATE / is_last ---
def test_weg3_terminate_when_all_done_no_orphans():
    """is_last=True wenn idf_items==batch_done, open_pl_deferred=[], stage_orphans=[]."""
    result = classify_route(
        idf_items=["a", "b"],
        batch_done=["a", "b"],
        completed_sub_batches=["sb1", "sb2"],
        open_pl_deferred=[],
        stage_orphans=[],
    )
    assert result["weg"] == 3
    assert result["decision_token"] == "TERMINATE"
    assert result["is_last"] is True


# --- TC-2: WEG 2 / RE-BATCH (Items noch offen) ---
def test_weg2_rebatch_when_items_still_open():
    """Noch nicht alle idf_items in batch_done -> WEG 2, RE-BATCH, is_last=False."""
    result = classify_route(
        idf_items=["a", "b", "c"],
        batch_done=["a", "b"],
        completed_sub_batches=["sb1"],
        open_pl_deferred=[],
        stage_orphans=[],
    )
    assert result["weg"] == 2
    assert result["decision_token"] == "RE-BATCH"
    assert result["is_last"] is False


# --- TC-3: WEG 1 via stage_orphans (Prioritaet WEG1 > WEG3) ---
def test_weg1_rollback_when_stage_orphans_present_despite_set_equal():
    """Set-equal, ABER stage_orphans vorhanden -> WEG 1 (kein WEG3 trotz is_last-Kandidat)."""
    result = classify_route(
        idf_items=["a", "b"],
        batch_done=["a", "b"],
        completed_sub_batches=["sb1"],
        open_pl_deferred=[],
        stage_orphans=["sb2"],
    )
    assert result["weg"] == 1
    assert result["decision_token"] == "ROLLBACK"
    assert result["is_last"] is False


# --- TC-4: WEG 1 via genuiner neuer Orphan-PL (nicht in idf_items) ---
def test_weg1_rollback_when_new_orphan_pl_not_in_idf():
    """Set-equal ABER open_pl_deferred enthaelt Item das NICHT in idf_items -> WEG 1."""
    result = classify_route(
        idf_items=["a", "b"],
        batch_done=["a", "b"],
        completed_sub_batches=["sb1"],
        open_pl_deferred=["NEW-orphan-1"],
        stage_orphans=[],
    )
    assert result["weg"] == 1
    assert result["decision_token"] == "ROLLBACK"
    assert result["is_last"] is False


# --- TC-5: deferred KNOWN -> WEG 2, NICHT WEG 3 ---
def test_weg2_rebatch_when_deferred_known_in_idf_items():
    """Set-equal ABER open_pl_deferred=['a'] und 'a' IST in idf_items -> WEG 2, RE-BATCH."""
    result = classify_route(
        idf_items=["a", "b"],
        batch_done=["a", "b"],
        completed_sub_batches=["sb1"],
        open_pl_deferred=["a"],
        stage_orphans=[],
    )
    assert result["weg"] == 2
    assert result["decision_token"] == "RE-BATCH"
    assert result["is_last"] is False


# --- TC-6: Prioritaet WEG1 > WEG3 expliziter Test ---
def test_priority_weg1_beats_weg3_when_stage_orphans_present():
    """all-done UND stage_orphans -> WEG1 gewinnt (nicht WEG3). Prioritaet AK-6."""
    result = classify_route(
        idf_items=["x", "y"],
        batch_done=["x", "y"],
        completed_sub_batches=["sb1"],
        open_pl_deferred=[],
        stage_orphans=["x"],
    )
    assert result["weg"] == 1
    assert result["decision_token"] == "ROLLBACK"


# --- TC-7: INV-MODUS-1 - kein modus/batch_modes Key im result ---
def test_inv_modus1_no_modus_key_in_result():
    """INV-MODUS-1: classify_route setzt KEINEN modus oder batch_modes Key."""
    result = classify_route(
        idf_items=["a"],
        batch_done=["a"],
        completed_sub_batches=[],
        open_pl_deferred=[],
        stage_orphans=[],
    )
    assert "modus" not in result
    assert "batch_modes" not in result
    # Pflicht-Keys muessen vorhanden sein
    assert "weg" in result
    assert "decision_token" in result
    assert "is_last" in result
    assert "reason" in result
