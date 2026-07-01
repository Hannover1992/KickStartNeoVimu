#!/usr/bin/env python3
"""Tests fuer truth_lifecycle.py (BL-309 R2 / Reife-Ableitung)."""
from __future__ import annotations

import truth_lifecycle as tl


def test_code_verified_is_experiment_proven():
    assert tl.map_lifecycle(status="OFFEN", truth_grade="code_verified") == ("experiment_proven", False)


def test_code_contradicted_is_contradicted():
    assert tl.map_lifecycle(truth_grade="code_contradicted")[0] == "contradicted"


def test_grade_overrides_status():
    # starkes Code-Signal schlaegt epistemischen Status
    assert tl.map_lifecycle(status="OFFEN", truth_grade="code_verified")[0] == "experiment_proven"


def test_status_bestaetigt_is_reviewed_no_hil():
    lc, hil = tl.map_lifecycle(status="BESTAETIGT", truth_grade="vault_hypothesis")
    assert lc == "reviewed" and hil is False


def test_status_offen_is_asserted():
    assert tl.map_lifecycle(status="OFFEN")[0] == "asserted"


def test_status_widerlegt_is_contradicted():
    assert tl.map_lifecycle(status="WIDERLEGT")[0] == "contradicted"


def test_status_retracted_and_veraltet_are_retracted():
    assert tl.map_lifecycle(status="RETRACTED")[0] == "retracted"
    assert tl.map_lifecycle(status="VERALTET_DATEI_GELOESCHT")[0] == "retracted"


def test_unknown_status_is_asserted_with_hil_flag():
    lc, hil = tl.map_lifecycle(status="FOOBAR_LEGACY")
    assert lc == "asserted" and hil is True


def test_none_defaults_asserted_with_hil():
    lc, hil = tl.map_lifecycle()
    assert lc == "asserted" and hil is True


def test_ungraded_vault_hypothesis_is_asserted():
    # der Legacy-HEADING-Default-Pfad (Atomizer)
    assert tl.map_lifecycle(status="UNGRADED", truth_grade="vault_hypothesis") == ("asserted", False)
