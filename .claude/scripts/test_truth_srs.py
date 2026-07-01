#!/usr/bin/env python3
"""Tests fuer truth_srs.py (BL-384 / SRS als View ueber Wahrheiten)."""
from __future__ import annotations

import truth_srs as srs


def _t(lifecycle="asserted", typ="FESTSTELLUNG"):
    return {"lifecycle": lifecycle, "typ": typ}


def test_all_asserted_is_srs_100():
    assert srs.srs_from_truths([_t(), _t(), _t()])["srs"] == 100


def test_all_proven_is_srs_0():
    truths = [_t(lifecycle="experiment_proven"), _t(lifecycle="experiment_proven")]
    assert srs.srs_from_truths(truths)["srs"] == 0


def test_half_open_is_srs_50():
    truths = [_t(), _t(), _t(lifecycle="reviewed"), _t(lifecycle="experiment_proven")]
    r = srs.srs_from_truths(truths)
    assert r["w_total"] == 4 and r["w_open"] == 2 and r["srs"] == 50


def test_frage_is_always_open_even_if_proven():
    t = _t(lifecycle="experiment_proven", typ="FRAGE")
    assert srs.is_open(t) is True


def test_empty_is_srs_0():
    assert srs.srs_from_truths([])["srs"] == 0


def test_lifecycle_distribution():
    truths = [_t(), _t(lifecycle="reviewed"), _t(lifecycle="reviewed")]
    assert srs.srs_from_truths(truths)["by_lifecycle"] == {"asserted": 1, "reviewed": 2}


def test_missing_lifecycle_defaults_open():
    # ohne lifecycle-Feld -> Default 'asserted' -> offen
    assert srs.is_open({"typ": "FESTSTELLUNG"}) is True


def test_contradicted_and_retracted_are_settled():
    assert srs.is_open(_t(lifecycle="contradicted")) is False
    assert srs.is_open(_t(lifecycle="retracted")) is False
