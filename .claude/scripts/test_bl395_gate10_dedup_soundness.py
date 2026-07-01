#!/usr/bin/env python3
"""
test_bl395_gate10_dedup_soundness.py — RED-Tests fuer den Gate-10-Korrektheits-Fix (BL-395, entblockt BL-309).

BUG (Wurzel, verifiziert): truth_gate_check.py Gate 10 `dedup_soundness_r4` prueft
    sound = (duplicate_groups == collapsible_to_alias)
Das ist algebraisch "jede Dup-Gruppe hat GENAU 2 Mitglieder" und schlaegt faelschlich
bei n>=3 byte-identischen Dup-Gruppen fehl, OBWOHL diese verlustfrei alias-kollabierbar
sind (truth_dedup gruppiert nach content_hash -> jede Gruppe ist byte-identisch ->
alias_plan: canonical=kleinste id + Rest=aliases, fuer JEDE Gruppengroesse).

SOLL (was GREEN baut): Gate 10 zertifiziert die alias-plan-Verlustfreiheit, nicht "nur Paare":
    sound = (collapsible_to_alias == duplicate_members - duplicate_groups)
-> PASS fuer byte-identische Dup-Gruppen JEDER Groesse (n>=2). Gates 1-9 bleiben die
echten Loss=0-Garantien; Gate 10 zertifiziert nur den R4-Kollaps.

Konvention: tmp-Vault wie test_truth_gate_check.py (Backlog/BL-N/2_Model/*.md), HEADING-Format
(### W01 + Body-Zeile). Identischer Body-Text in mehreren Models -> identischer content_hash
-> eine Dup-Gruppe der entsprechenden Groesse. Der jeweils 2. (Pair) bzw. 2.+ (Triple) Knoten
ist pro Model verschieden -> nur Gate 10 ist betroffen, alle anderen Gates bleiben gruen.
"""
from __future__ import annotations

import truth_gate_check as gc


def _mk(p, content):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def _gate10(rep):
    return next(s for s in rep["steps"] if s["name"] == "dedup_soundness_r4")


def _other_fails(rep):
    return [s["step"] for s in rep["steps"] if not s["pass"] and s["step"] != 10]


# ── geteilter Truth-Body, byte-identisch ueber Models -> selber content_hash -> Dup-Gruppe ──
_SHARED = "### W01\nDie eine geklaute Wahrheit, woertlich gleich an mehreren Stellen.\n"


def test_gate10_passes_for_triple_byte_identical_group(tmp_path):
    """RED (Kern): eine n=3 byte-identische Dup-Gruppe (BL-380/382/383 W-INV-1-Klasse).
    Gate 10 MUSS passen (verlustfrei alias-kollabierbar). Heute FAIL (groups=1 != collapsible=2)."""
    b = tmp_path / "Backlog"
    _mk(b / "BL-380" / "2_Model" / "H_Model.md", _SHARED + "\n### W02\nNur in 380.\n")
    _mk(b / "BL-382" / "2_Model" / "H_Model.md", _SHARED + "\n### W03\nNur in 382.\n")
    _mk(b / "BL-383" / "2_Model" / "H_Model.md", _SHARED + "\n### W04\nNur in 383.\n")
    rep = gc.run_gates(b, None, jobs=1)

    # Vorbedingung: es entsteht WIRKLICH eine n=3-Gruppe (sonst triggert der Bug nicht).
    g10 = _gate10(rep)
    assert g10["detail"]["duplicate_groups"] == 1, g10["detail"]
    assert g10["detail"]["collapsible_to_alias"] == 2, g10["detail"]   # 3 members - 1 group

    # nur Gate 10 ist betroffen — die echten Loss=0-Gates (1-9) bleiben gruen.
    assert _other_fails(rep) == [], [s for s in rep["steps"] if not s["pass"]]

    # SOLL: die n=3-Gruppe ist verlustfrei alias-kollabierbar -> Gate 10 PASS.
    assert g10["pass"] is True, g10["detail"]
    assert rep["extraction_go"] is True


def test_gate10_passes_for_mixed_pair_and_triple(tmp_path):
    """RED/Guard: gemischt 1 Paar (n=2) + 1 Triple (n=3) -> Gate 10 PASS.
    Heute FAIL (groups=2 != collapsible=3). SOLL: collapsible(3) == members(5) - groups(2)."""
    b = tmp_path / "Backlog"
    pair = "### W01\nGeteilte Paar-Wahrheit, woertlich gleich.\n"
    trip = "### W01\nGeteilte Triple-Wahrheit, woertlich gleich.\n"
    _mk(b / "BL-1" / "2_Model" / "H_Model.md", pair + "\n### W02\nPaar A.\n")
    _mk(b / "BL-2" / "2_Model" / "H_Model.md", pair + "\n### W03\nPaar B.\n")
    _mk(b / "BL-3" / "2_Model" / "H_Model.md", trip + "\n### W04\nTriple A.\n")
    _mk(b / "BL-4" / "2_Model" / "H_Model.md", trip + "\n### W05\nTriple B.\n")
    _mk(b / "BL-5" / "2_Model" / "H_Model.md", trip + "\n### W06\nTriple C.\n")
    rep = gc.run_gates(b, None, jobs=1)

    g10 = _gate10(rep)
    assert g10["detail"]["duplicate_groups"] == 2, g10["detail"]
    assert g10["detail"]["collapsible_to_alias"] == 3, g10["detail"]
    assert _other_fails(rep) == [], [s for s in rep["steps"] if not s["pass"]]

    assert g10["pass"] is True, g10["detail"]
    assert rep["extraction_go"] is True


def test_gate10_stays_green_for_pure_pair(tmp_path):
    """GRUEN-Regression: reiner Paar-Fall (n=2) -> Gate 10 PASS (kein Rueckschritt).
    groups=1, collapsible=1; SOLL: collapsible(1) == members(2) - groups(1)."""
    b = tmp_path / "Backlog"
    pair = "### W01\nGeteilte Paar-Wahrheit, woertlich gleich.\n"
    _mk(b / "BL-1" / "2_Model" / "H_Model.md", pair + "\n### W02\nNur hier.\n")
    _mk(b / "BL-2" / "2_Model" / "H_Model.md", pair + "\n### W03\nNur dort.\n")
    rep = gc.run_gates(b, None, jobs=1)

    g10 = _gate10(rep)
    assert g10["detail"]["duplicate_groups"] == 1, g10["detail"]
    assert g10["detail"]["collapsible_to_alias"] == 1, g10["detail"]
    assert g10["pass"] is True, g10["detail"]
    assert rep["extraction_go"] is True


def test_gate10_stays_green_with_no_dups(tmp_path):
    """GRUEN-Regression: keine Dups -> Gate 10 PASS (collapsible=0 == members(0) - groups(0))."""
    b = tmp_path / "Backlog"
    _mk(b / "BL-1" / "2_Model" / "H_Model.md", "### W01\nEinzig eins.\n")
    _mk(b / "BL-2" / "2_Model" / "H_Model.md", "### W01\nEinzig zwei.\n")
    rep = gc.run_gates(b, None, jobs=1)

    g10 = _gate10(rep)
    assert g10["detail"]["duplicate_groups"] == 0, g10["detail"]
    assert g10["detail"]["collapsible_to_alias"] == 0, g10["detail"]
    assert g10["pass"] is True, g10["detail"]
    assert rep["extraction_go"] is True


def test_gate10_soundness_condition_rejects_inconsistent_dd():
    """Meaningful-Guard: Gate 10 bleibt aussagekraeftig — ein INKONSISTENTES dd-Dict
    (collapsible passt NICHT zu members - groups) muss als UNSOUND (False) gelten.

    Die SOLL-Bedingung ist `collapsible_to_alias == duplicate_members - duplicate_groups`.
    GREEN soll diese Bedingung idealerweise in eine kleine testbare Helper-Funktion ziehen
    (vorgeschlagener Name: truth_gate_check.dedup_sound(dd)). Solange es keinen Helper gibt,
    SKIPpt dieser Test (kein Block fuer RED) und meldet die Erwartung an GREEN.
    """
    import pytest

    helper = getattr(gc, "dedup_sound", None)
    if helper is None:
        pytest.skip("GREEN-TODO: Soundness-Bedingung in testbare Helper-Fn gc.dedup_sound(dd) ziehen "
                    "(SOLL: collapsible_to_alias == duplicate_members - duplicate_groups). "
                    "Korpus-Tests decken das End-zu-End-Verhalten ab.")

    # konstruiert inkonsistent: collapsible (99) passt nicht zu members(5) - groups(2) == 3
    assert helper({"duplicate_groups": 2, "duplicate_members": 5, "collapsible_to_alias": 99}) is False
    # konstruiert konsistent (auch n>=3): members(5) - groups(2) == 3 == collapsible
    assert helper({"duplicate_groups": 2, "duplicate_members": 5, "collapsible_to_alias": 3}) is True
    # leer/keine Dups: 0 == 0 - 0
    assert helper({"duplicate_groups": 0, "duplicate_members": 0, "collapsible_to_alias": 0}) is True
