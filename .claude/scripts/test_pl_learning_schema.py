#!/usr/bin/env python3
"""Tests fuer pl_learning_schema.py (BL-271 batch_1 — Korrektur=Lern-Signal).

TDD Stage 1 (Atomic), Modus M3. Spiegel-Stil von test_pl_defer_filter.py
(import-tolerant + standalone __main__-Runner + pytest-kompatibel).

PROBLEM (BL-271, 486-Empirie): stille Korrekturen = verlorenes Lernen. Ein
PL-Item braucht am CAPTURE-Punkt zwei kanonische Lern-Felder, damit das Signal
spaeter ERNTBAR ist (_PT_berater_classify liest sie statt sie teuer zu
rekonstruieren):
  - commit_ref:     Pointer auf den Commit der Korrektur (Hash-String).
  - classification: eine der 4 PT-classify-Achsen (semantic|architectural|
                    fachlich|factoring) am Entstehungsort.

KONTRAKT (rein, deterministisch — KEIN State, KEIN IO):
- validate_learning_fields(item) -> {ok, errors}
- has_learning_signal(item)      -> bool

ABWAERTSKOMPATIBEL (KERN-CONSTRAINT): BEIDE Felder sind OPTIONAL. Ein Item
ohne die neuen Felder MUSS valide bleiben (errors == []). Kein Bruch des
bestehenden /_parking-lot-Vertrags.

RED-Beweis: pl_learning_schema.py existiert NOCH NICHT -> ImportError -> die
Referenzen bleiben None -> jeder Test failt loud. Das IST RED.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

# Import-tolerant: solange pl_learning_schema.py fehlt (RED-Phase) bleiben die
# Referenzen None und jeder Test failt mit klarer Meldung statt CollectError.
try:
    from pl_learning_schema import validate_learning_fields as _VALIDATE
    from pl_learning_schema import has_learning_signal as _HAS_SIGNAL
    from pl_learning_schema import CLASSIFICATION_AXES as _AXES
    _IMPORT_ERR = None
except ImportError as e:  # RED: Modul existiert noch nicht
    _VALIDATE = None
    _HAS_SIGNAL = None
    _AXES = None
    _IMPORT_ERR = e


def _require_import():
    assert _VALIDATE is not None and _HAS_SIGNAL is not None and _AXES is not None, (
        f"pl_learning_schema.py nicht importierbar (RED erwartet vor GREEN): {_IMPORT_ERR}"
    )


# --- T1: Item mit BEIDEN Feldern (gueltig) -----------------------------------
def test_valid_item_with_both_fields():
    _require_import()
    item = {
        "pl_item_id": "PL-271-001",
        "type": "correction",
        "commit_ref": "a96eb1c",
        "classification": "factoring",
    }
    res = _VALIDATE(item)
    assert res["ok"] is True, f"Item mit beiden gueltigen Feldern muss ok sein: {res['errors']}"
    assert res["errors"] == [], f"keine Fehler erwartet, waren {res['errors']}"


# --- T2: ABWAERTSKOMPATIBILITAET — Item OHNE neue Felder = valide ------------
def test_backward_compat_no_new_fields_valid():
    _require_import()
    # Bestands-PL-Item (Pre-BL-271): kein commit_ref, kein classification.
    item = {
        "pl_item_id": "PL-201-007",
        "type": "addition",
        "title": "Altbestand ohne Lern-Felder",
    }
    res = _VALIDATE(item)
    assert res["ok"] is True, (
        f"ABWAERTSKOMPAT-BRUCH: Item ohne neue Felder muss valide bleiben, war {res}"
    )
    assert res["errors"] == [], f"keine Fehler erwartet (Felder optional), waren {res['errors']}"


# --- T3: ungueltige classification -> reject ---------------------------------
def test_invalid_classification_rejected():
    _require_import()
    item = {"pl_item_id": "PL-271-002", "classification": "performance"}
    res = _VALIDATE(item)
    assert res["ok"] is False, "classification ausserhalb der 4 Achsen muss rejected werden"
    assert any("classification" in e for e in res["errors"]), (
        f"Fehler muss classification benennen, waren {res['errors']}"
    )


# --- T4: classification-Enum = EXAKT die 4 PT-classify-Achsen ----------------
def test_classification_enum_matches_pt_classify_axes():
    _require_import()
    # _PT_berater_classify.md: semantic | architectural | fachlich | factoring
    assert set(_AXES) == {"semantic", "architectural", "fachlich", "factoring"}, (
        f"classification-Enum muss EXAKT die 4 PT-classify-Achsen sein, war {set(_AXES)}"
    )
    # jede einzelne Achse muss als classification akzeptiert werden
    for axis in ("semantic", "architectural", "fachlich", "factoring"):
        res = _VALIDATE({"classification": axis})
        assert res["ok"] is True, f"Achse {axis!r} muss valide classification sein: {res['errors']}"


# --- T5: commit_ref-Plausibilitaet (Hash-String) -----------------------------
def test_commit_ref_plausibility():
    _require_import()
    # plausible Hashes (kurz + lang, hex)
    for good in ("a96eb1c", "150e8d7", "badfa2b", "0d4f9b1f2e3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c"):
        res = _VALIDATE({"commit_ref": good})
        assert res["ok"] is True, f"plausibler Hash {good!r} muss akzeptiert werden: {res['errors']}"
    # implausibel: zu kurz, Nicht-Hex, Leerzeichen, klar kein Hash.
    # NB: "" gehoert NICHT hierher — Leer-String == 'nicht gesetzt' == valide
    # (optional/abwaertskompatibel, siehe test_empty_field_values_treated_as_unset).
    for bad in ("xyz", "g12h34", "not a commit", "12"):
        res = _VALIDATE({"commit_ref": bad})
        assert res["ok"] is False, f"implausibler commit_ref {bad!r} muss rejected werden"
        assert any("commit_ref" in e for e in res["errors"]), (
            f"Fehler muss commit_ref benennen fuer {bad!r}, waren {res['errors']}"
        )


# --- T6: has_learning_signal — commit_ref ODER classification ODER correction-Typ
def test_has_learning_signal_cases():
    _require_import()
    # traegt commit_ref
    assert _HAS_SIGNAL({"commit_ref": "a96eb1c"}) is True
    # traegt classification
    assert _HAS_SIGNAL({"classification": "semantic"}) is True
    # correction-Typ (zweite Signal-Klasse AK-S1)
    assert _HAS_SIGNAL({"type": "correction"}) is True
    # gar kein Signal
    assert _HAS_SIGNAL({"type": "addition", "title": "x"}) is False
    # leeres / None tolerant
    assert _HAS_SIGNAL({}) is False
    assert _HAS_SIGNAL(None) is False


# --- T7: AK-S1 zweite Signal-Klasse — inkorrekte_umsetzung/kurs_korrektur ----
def test_correction_type_subclasses_are_signal():
    _require_import()
    # Die zweite Signal-Klasse (inkorrekte Umsetzung / Kurs-Korrektur) ist als
    # correction-Typ capture-bar — neben der "widerlegten Wahrheit".
    for t in ("correction", "inkorrekte_umsetzung", "kurs_korrektur"):
        assert _HAS_SIGNAL({"type": t}) is True, (
            f"correction-Subtyp {t!r} muss als Lern-Signal zaehlen (AK-S1)"
        )


# --- T8: kombinierte Validierung — beide Felder ungueltig -> beide Fehler ----
def test_both_fields_invalid_collects_both_errors():
    _require_import()
    item = {"commit_ref": "nope", "classification": "refactoring"}
    res = _VALIDATE(item)
    assert res["ok"] is False
    assert any("commit_ref" in e for e in res["errors"]), "commit_ref-Fehler erwartet"
    assert any("classification" in e for e in res["errors"]), (
        "classification-Fehler erwartet ('refactoring' ist NICHT die Achse — die heisst 'factoring')"
    )


# --- T9: None/Nicht-dict-Eingabe robust --------------------------------------
def test_validate_none_and_non_dict_robust():
    _require_import()
    res = _VALIDATE(None)
    assert res["ok"] is False, "None-Item ist kein valides PL-Item"
    assert res["errors"], "None muss einen Fehler liefern"
    res2 = _VALIDATE("not a dict")
    assert res2["ok"] is False


# --- T10: leere/None-Feldwerte gelten als 'nicht gesetzt' (abwaertskompat) ---
def test_empty_field_values_treated_as_unset():
    _require_import()
    # explizit None oder leer = Feld nicht gesetzt -> valide (optional)
    res = _VALIDATE({"commit_ref": None, "classification": None})
    assert res["ok"] is True, f"None-Werte = unset -> valide, war {res}"
    res2 = _VALIDATE({"commit_ref": "", "classification": ""})
    assert res2["ok"] is True, f"Leer-Strings = unset -> valide, war {res2}"
    # und kein Lern-Signal, wenn beide leer und kein correction-Typ
    assert _HAS_SIGNAL({"commit_ref": "", "classification": None}) is False


if __name__ == "__main__":
    # Windows-stdout ist standardmaessig cp1252 -> Umlaute crashen mit
    # UnicodeEncodeError. utf-8 erzwingen (Py3.7+), fail-safe (a96eb1c-Lehre).
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    tests = [
        test_valid_item_with_both_fields,
        test_backward_compat_no_new_fields_valid,
        test_invalid_classification_rejected,
        test_classification_enum_matches_pt_classify_axes,
        test_commit_ref_plausibility,
        test_has_learning_signal_cases,
        test_correction_type_subclasses_are_signal,
        test_both_fields_invalid_collects_both_errors,
        test_validate_none_and_non_dict_robust,
        test_empty_field_values_treated_as_unset,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed + failed} ===")
    sys.exit(0 if failed == 0 else 1)
