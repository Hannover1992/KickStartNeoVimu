#!/usr/bin/env python3
"""Tests fuer truth_gap.py (BL-384 / Gap-View, actionable open-questions)."""
from __future__ import annotations

import truth_gap as gp


def _t(lid, typ="FESTSTELLUNG", lifecycle="asserted", grade="vault_hypothesis"):
    return {"id": f"BL-x.{lid}", "local_id": lid, "typ": typ, "lifecycle": lifecycle, "truth_grade": grade}


def test_open_truths_includes_asserted_and_frage():
    truths = [_t("W1", lifecycle="asserted"), _t("W2", lifecycle="experiment_proven"),
              _t("W3", typ="FRAGE", lifecycle="experiment_proven")]
    ids = {t["local_id"] for t in gp.open_truths(truths)}
    assert ids == {"W1", "W3"}  # W2 settled (proven, kein FRAGE)


def test_actionable_gap_is_frage_only():
    truths = [_t("W1"), _t("W2", typ="FRAGE"), _t("W3", typ="SOLL")]
    assert [t["local_id"] for t in gp.actionable_gap(truths)] == ["W2"]


def test_gap_report_counts():
    truths = [_t("W1", typ="FRAGE"), _t("W2", lifecycle="experiment_proven", grade="code_verified"),
              _t("W3")]
    r = gp.gap_report(truths)
    assert r["total"] == 3
    assert r["open_questions"] == 1            # W1 FRAGE
    assert r["vault_hypotheses"] == 2          # W1, W3 (W2 ist code_verified)
    assert r["questions_by_bl"] == {"BL-x": 1}


def test_empty():
    r = gp.gap_report([])
    assert r["total"] == 0 and r["open_questions"] == 0
