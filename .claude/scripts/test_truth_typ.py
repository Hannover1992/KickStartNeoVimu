#!/usr/bin/env python3
"""Tests fuer truth_typ.py (BL-309 / typ-Erkennung, konservativ)."""
from __future__ import annotations

import truth_typ as tt


def test_frage_from_question_mark():
    assert tt.detect_typ("### W1", "Ist das wahr?") == "FRAGE"


def test_frage_from_marker():
    assert tt.detect_typ("### W1: offene Frage", "noch ungeklaert") == "FRAGE"


def test_soll_from_strong_uppercase_marker():
    assert tt.detect_typ("### W1", "Das System MUSS X tun.") == "SOLL"


def test_soll_from_word():
    assert tt.detect_typ("### W1", "Dies ist erforderlich.") == "SOLL"


def test_feststellung_default():
    assert tt.detect_typ("### W1", "Das System ist model-basiert.") == "FESTSTELLUNG"


def test_lowercase_muss_is_not_soll():
    # kleines deskriptives "muss" -> KEIN SOLL (konservativ, low-false-positive)
    assert tt.detect_typ("### W1", "Der Wert muss berechnet werden.") == "FESTSTELLUNG"


def test_frage_beats_soll():
    assert tt.detect_typ("### W1", "MUSS das so sein?") == "FRAGE"
