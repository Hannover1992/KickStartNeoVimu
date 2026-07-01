#!/usr/bin/env python3
"""Integrations-Test: validate_vault_schema dispatcht type:truth → truth_schema (BL-309 Phase A1)."""
from __future__ import annotations

import validate_vault_schema as vvs

_VALID = """---
type: truth
feature: BL-309
bl-item: BL-309
created: 2026-06-16
updated: 2026-06-16
tags: [bl/309, type/truth]
id: BL-309-truth-migration.W01
local_id: W01
text: Das alte System ist model-basiert.
typ: FESTSTELLUNG
herkunft: INTERN
status: BESTAETIGT
truth_grade: code_verified
---

# W01
"""


def _write(tmp_path, content):
    p = tmp_path / "t.md"
    p.write_text(content, encoding="utf-8")
    return p


def _errors(issues):
    return [m for s, m in issues if s == "ERROR"]


def test_truth_type_is_allowed_no_unknown_type_warn(tmp_path):
    issues = vvs.validiere_doc(_write(tmp_path, _VALID))
    assert not any("nicht in erlaubten Typen" in m for _, m in issues)


def test_valid_truth_has_no_errors(tmp_path):
    """PFLICHT_ALL + truth-spezifisch beide sauber → 0 ERROR."""
    assert _errors(vvs.validiere_doc(_write(tmp_path, _VALID))) == []


def test_bad_typ_is_dispatched_to_truth_schema(tmp_path):
    bad = _VALID.replace("typ: FESTSTELLUNG", "typ: BEHAUPTUNG")
    assert any("typ" in m for m in _errors(vvs.validiere_doc(_write(tmp_path, bad))))


def test_missing_pflicht_all_still_caught_for_truth(tmp_path):
    """truths tragen weiter PFLICHT_ALL (Schema-Kompatibilitaet) — fehlendes feature = ERROR."""
    bad = _VALID.replace("feature: BL-309\n", "")
    assert any("feature" in m for m in _errors(vvs.validiere_doc(_write(tmp_path, bad))))
