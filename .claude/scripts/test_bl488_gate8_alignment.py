#!/usr/bin/env python3
"""
BL-488 F-2 Regression Guard: Gate-8 <-> Orchestrator Alignment Invariant.

THE INVARIANT (AC-2 blocker, now fixed by Lane-C):
  Every reason that puts a model into the orchestrator's `quarantined` set MUST be a reason
  cutover_model refuses on. If any quarantine reason is not covered by cutover_model's
  refuse-guards, a quarantined model slips Gate 8 (refuse_fail != []).

BL-203 was the specific F-2 holdout: knots=9 < census=25 (truth_count_loss quarantine reason),
but truth_cutover.py had no truth_count_loss guard -> cutover_model would NOT refuse BL-203 ->
Gate 8 would show refuse_fail=[BL-203_Model.md] (RED).
Fix: Lane-C added truth_cutover.py L118-119 (mirror of quarantine_reasons' truth_count_loss branch).

These tests lock the invariant permanently. test_alignment_guard_has_teeth (#4) is the
teeth-proof: it demonstrates that removing the truth_count_loss guard makes the guard test red.

READ-ONLY: tests use temp copies for any cutover_model calls, never touching the real vault.
"""
from __future__ import annotations

import shutil
import tempfile
import unittest.mock as mock
from pathlib import Path

import pytest

import truth_cutover as tcut
import truth_migrate_orchestrator as orch

_VAULT = Path("C:/Users/hanno/Documents/Work/Wissen/Berechtigung/OmniCommand/OmniCommand")
_BL203_MODEL = _VAULT / "Backlog/BL-203-k-score-refresh-in-idf/2_Model/BL-203_Model.md"
_BL199_MODEL = _VAULT / "Backlog/BL-199-idf-loop-check-reentry/2_Model/BL-199_Model.md"


def _copy_to_tmp(src: Path, tmp_root: Path, subdir: str) -> Path:
    """Copy model to tmp dir preserving 2_Model/ structure. Returns tmp model path."""
    dst = tmp_root / subdir / "2_Model" / src.name
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    return dst


def _gate8_refused(tmp: Path, before: bytes) -> bool:
    """Returns True iff cutover_model refuses and satisfies Gate-8's refuse condition:
    cutover=False AND bytes unchanged AND no _legacy dir. Mirrors truth_gate_check.py L133."""
    res = tcut.cutover_model(tmp, "BL-q")
    return (
        res.get("cutover") is False
        and tmp.read_bytes() == before
        and not (tmp.parent / "_legacy").exists()
    )


# ── Test 1: STRUCTURAL invariant — cutover_model refuse-reason set covers quarantine-reason set ──

def test_cutover_model_refuses_each_quarantine_reason(tmp_path):
    """STRUCTURAL invariant (load-bearing): for every reason in quarantine_reasons() there
    must be a matching cutover_model refuse-guard, so no quarantined model slips Gate 8.

    Exercises:
      roundtrip_fail     -> real BL-199 model (0 truths -> no_truths refuse, which IS a refuse)
      low_byte_coverage  -> real BL-199 model (same model: roundtrip_ok=False + low_coverage=True)
      truth_count_loss   -> real BL-203 model (knots=9 < census=25; C's L118-119 guard fires)
      schema_error       -> synthetic via mock (no vault model has this reason currently)

    The gate-8 refuse condition: cutover=False AND bytes unchanged AND no _legacy dir.
    """
    assert _VAULT.exists(), f"Vault not found: {_VAULT}"
    assert _BL199_MODEL.exists(), f"BL-199 model not found: {_BL199_MODEL}"
    assert _BL203_MODEL.exists(), f"BL-203 model not found: {_BL203_MODEL}"

    # ── roundtrip_fail + low_byte_coverage: real BL-199 ──
    r199 = orch.process_bl_unit(str(_BL199_MODEL))
    reasons199 = orch.quarantine_reasons(r199)
    assert "roundtrip_fail" in reasons199, f"BL-199 should have roundtrip_fail; got {reasons199}"
    assert "low_byte_coverage" in reasons199, f"BL-199 should have low_byte_coverage; got {reasons199}"

    tmp199 = _copy_to_tmp(_BL199_MODEL, tmp_path, "bl199")
    before199 = tmp199.read_bytes()
    assert _gate8_refused(tmp199, before199), \
        f"cutover_model did not gate-8-refuse BL-199 (roundtrip_fail+low_byte_coverage): " \
        f"{tcut.cutover_model(_copy_to_tmp(_BL199_MODEL, tmp_path, 'bl199b'), 'BL-199')}"

    # ── truth_count_loss: real BL-203 (the F-2 holdout) ──
    r203 = orch.process_bl_unit(str(_BL203_MODEL))
    reasons203 = orch.quarantine_reasons(r203)
    assert "truth_count_loss" in reasons203, f"BL-203 should have truth_count_loss; got {reasons203}"

    tmp203 = _copy_to_tmp(_BL203_MODEL, tmp_path, "bl203")
    before203 = tmp203.read_bytes()
    res203 = tcut.cutover_model(tmp203, "BL-203")
    assert res203.get("cutover") is False, \
        f"cutover_model did not refuse BL-203 (truth_count_loss): {res203}"
    assert res203.get("reason") == "truth_count_loss", \
        f"Expected reason=truth_count_loss, got: {res203}"
    assert _gate8_refused(_copy_to_tmp(_BL203_MODEL, tmp_path, "bl203b"), before203), \
        "Gate-8 refuse condition (bytes unchanged + no _legacy) not met for BL-203"

    # ── schema_error: synthetic via mock (no real vault model has this reason) ──
    schema_model = tmp_path / "schema_test" / "2_Model" / "Schema_Model.md"
    schema_model.parent.mkdir(parents=True)
    schema_model.write_text("### W01\nSynthetic truth for schema_error test.\n", encoding="utf-8")

    import truth_atomizer as ta_real
    real_res = ta_real.atomize_model_file(schema_model, "SCHEMA_TEST")
    # Inject schema_errors into the atomize result (truths present, roundtrip_ok, but schema bad)
    broken_res = dict(real_res, schema_errors=1)

    with mock.patch.object(tcut.ta, "atomize_model_file", return_value=broken_res):
        res_schema = tcut.cutover_model(schema_model, "SCHEMA_TEST")
    assert res_schema.get("cutover") is False, \
        f"cutover_model should refuse schema_error, got: {res_schema}"
    assert res_schema.get("reason") == "schema_error", \
        f"Expected reason=schema_error, got: {res_schema}"


# ── Test 2: F-2 holdout — BL-203 truth_count_loss refused (load-bearing, pins Lane-C's guard) ──

def test_bl203_truth_count_loss_refused(tmp_path):
    """The F-2 holdout: BL-203 is quarantined for truth_count_loss (knots=9 < census=25)
    AND cutover_model refuses it with reason=truth_count_loss (C's L118-119 guard).

    If Lane-C's truth_count_loss guard (truth_cutover.py L118-119) were reverted, this test REDS:
    cutover_model would proceed past the guard and return cutover=True for BL-203.
    """
    assert _BL203_MODEL.exists(), f"BL-203 model not found: {_BL203_MODEL}"

    # ── Orchestrator: BL-203 is quarantined for truth_count_loss ──
    r = orch.process_bl_unit(str(_BL203_MODEL))
    assert r["ready"] is False, "BL-203 must not be ready"
    assert orch.quarantine_reasons(r) == ["truth_count_loss"], \
        f"BL-203 quarantine_reasons should be exactly ['truth_count_loss'], got: {orch.quarantine_reasons(r)}"
    assert r["knots"] < r["census"], \
        f"BL-203 knots ({r['knots']}) must be < census ({r['census']})"

    # ── cutover_model on temp copy: refuses with truth_count_loss ──
    tmp = _copy_to_tmp(_BL203_MODEL, tmp_path, "bl203_f2")
    before = tmp.read_bytes()
    res = tcut.cutover_model(tmp, "BL-203")

    assert res.get("cutover") is False, \
        f"cutover_model must refuse BL-203 (truth_count_loss), got: {res}"
    assert res.get("reason") == "truth_count_loss", \
        f"Expected reason=truth_count_loss, got reason={res.get('reason')!r}"

    # ── Gate-8 refuse condition (mirrors truth_gate_check.py L133) ──
    assert tmp.read_bytes() == before, \
        "Gate-8: bytes must be unchanged after refused cutover_model"
    assert not (tmp.parent / "_legacy").exists(), \
        "Gate-8: no _legacy dir must exist after refused cutover_model"


# ── Test 3: integration smoke — real vault Gate-8 quarantined set is fully refused ──

@pytest.mark.testtyp_integration
def test_real_vault_gate8_no_refuse_fail(tmp_path):
    """Integration smoke: for every quarantined model in the real vault, cutover_model refuses.
    Locks current green state: refuse_fail == [] (Gate 8 PASS).

    Iterates only the quarantined subset (not the full 200+ model vault) for reasonable runtime.
    """
    assert _VAULT.exists(), f"Vault not found: {_VAULT}"

    rep = orch.run(_VAULT, None, mode="global", jobs=4)
    quarantine_list = rep.get("quarantine", [])

    refuse_fail = []
    with tempfile.TemporaryDirectory() as td:
        for i, q in enumerate(quarantine_list):
            src = Path(q["model"])
            tmp = Path(td) / f"q{i}" / "2_Model" / src.name
            tmp.parent.mkdir(parents=True)
            before = src.read_bytes()
            tmp.write_bytes(before)
            res = tcut.cutover_model(tmp, "BL-q")
            gate8_ok = (
                res.get("cutover") is False
                and tmp.read_bytes() == before
                and not (tmp.parent / "_legacy").exists()
            )
            if not gate8_ok:
                refuse_fail.append({
                    "model": src.name,
                    "reasons": q["reasons"],
                    "cutover_result": res,
                })

    assert refuse_fail == [], (
        f"Gate-8 FAIL: {len(refuse_fail)} quarantined model(s) not refused by cutover_model.\n"
        f"refuse_fail: {refuse_fail}\n"
        f"(This is the F-2 class — a quarantined model slips Gate 8.)"
    )
    # Confirm the count: all quarantined must be refused
    assert len(quarantine_list) > 0, "Expected at least some quarantined models in vault"


# ── Test 4: TEETH-PROOF — alignment guard reds when truth_count_loss guard is removed ──

def test_alignment_guard_has_teeth(tmp_path):
    """TEETH-PROOF (no file edits): demonstrates that if the truth_count_loss guard
    (truth_cutover.py L118-119) is disabled, BL-203 is NOT refused by cutover_model —
    proving test_bl203_truth_count_loss_refused genuinely catches a regression.

    Method: patch truth_cutover.tc.count_wknots to return total_estimate <= knots (9)
    so that `res['knots'] < census` evaluates to False and the guard is skipped.
    Under broken guard: BL-203 (roundtrip_ok=True, low_coverage=False, schema_errors=0)
    passes all other checks -> cutover succeeds (cutover=True) -> Guard test #2 would RED.

    All operations on a temp copy. No file edits. Restored by mock context manager.
    """
    assert _BL203_MODEL.exists(), f"BL-203 model not found: {_BL203_MODEL}"

    # Get the real knots count for BL-203 so our patch is exact
    r = orch.process_bl_unit(str(_BL203_MODEL))
    bl203_knots = r["knots"]  # 9
    assert bl203_knots < r["census"], "precondition: BL-203 should have knots < census"

    # Make a temp copy to absorb the cutover write
    tmp = _copy_to_tmp(_BL203_MODEL, tmp_path, "bl203_teeth")

    # Patch tc.count_wknots to return total_estimate = bl203_knots (= knots, not > knots)
    # -> census = bl203_knots -> res["knots"] < census becomes False -> guard skipped
    assert tcut.tc is not None, "truth_census must be importable in truth_cutover"
    with mock.patch.object(tcut.tc, "count_wknots", return_value={"total_estimate": bl203_knots}):
        res_broken = tcut.cutover_model(tmp, "BL-203")

    # With the guard disabled, BL-203 is no longer refused for truth_count_loss.
    # BL-203 has roundtrip_ok=True, low_coverage=False, schema_errors=0 (confirmed above),
    # so cutover_model proceeds to write -> returns cutover=True.
    # This is the broken state that test_bl203_truth_count_loss_refused catches.
    assert res_broken.get("cutover") is not False or res_broken.get("reason") != "truth_count_loss", (
        f"Guard has no teeth: BL-203 still refused for truth_count_loss even with guard disabled. "
        f"Result: {res_broken}"
    )
    # More precisely: without the guard, the only possible outcomes for BL-203 are
    # cutover=True (swap succeeded) or a structural failure unrelated to truth_count_loss.
    # Either way, the alignment is broken and Gate 8 would have a refuse_fail.
    assert res_broken.get("cutover") is True, (
        f"Expected cutover=True when truth_count_loss guard is patched out for BL-203. "
        f"Got: {res_broken}. "
        f"(If cutover=False for a different reason, that reason must also be in quarantine_reasons "
        f"— check test_cutover_model_refuses_each_quarantine_reason for coverage.)"
    )
