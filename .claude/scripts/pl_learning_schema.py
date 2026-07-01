#!/usr/bin/env python3
"""pl_learning_schema.py — BL-271 batch_1 (Korrektur = Lern-Signal).

Reiner, deterministischer Schema-Validator fuer die zwei NEUEN, OPTIONALEN
PL-Item-Lern-Felder (BL-271). Stille Korrekturen = verlorenes Lernen: ein
PL-Item, dessen Lern-Signal spaeter ERNTBAR sein soll (_PT_berater_classify /
PT-Extraction), traegt am CAPTURE-Punkt zwei kanonische Felder:

  - commit_ref:     Pointer auf den Commit der Korrektur (Hash-String).
  - classification: eine der 4 PT-classify-Achsen am Entstehungsort —
                    semantic | architectural | fachlich | factoring.
                    (EXAKT die Achsen aus _PT_berater_classify.md; KEINE
                    Divergenz. Der Auftrags-Sprachgebrauch 'domain' == 'fachlich',
                    'refactoring' == 'factoring' — der Vertrag nutzt die
                    PT-classify-Labels als Single-Source.)

KERN-CONSTRAINT (ABWAERTSKOMPATIBEL): BEIDE Felder sind OPTIONAL. Ein
Bestands-PL-Item OHNE diese Felder bleibt valide (errors == []). Der bestehende
/_parking-lot-Vertrag wird NICHT gebrochen.

KONTRAKT (rein, deterministisch — KEIN State, KEIN IO, cwd-stabil per
Konstruktion: dieses Modul loest keine Pfade auf):
  - validate_learning_fields(item) -> {ok: bool, errors: [str]}
        commit_ref (wenn gesetzt) muss ein plausibler Hash-String sein;
        classification (wenn gesetzt) muss in CLASSIFICATION_AXES liegen.
        BEIDE optional -> fehlend/leer/None == valide.
  - has_learning_signal(item) -> bool
        Traegt das Item ueberhaupt ein Lern-Signal? True gdw. commit_ref ODER
        classification gesetzt ODER type ist ein correction-Subtyp (AK-S1:
        zweite Signal-Klasse inkorrekte_umsetzung/kurs_korrektur neben der
        widerlegten Wahrheit).

Andockung: zitiert vom /_parking-lot-Vertrag (Schema-Erweiterung, M2-Doc) als
gemeinsame, einheitliche Lern-Feld-Validierungs-Naht. Das Capture-Routing
(SDF->HiL/BDF->PL), commit_ref-Auto-Population (C7 statusTransition), Git-Trailer
und Library-Feed sind batch_2 — NICHT hier.
"""
import re
import sys

# Die 4 PT-classify-Achsen — EXAKT aus _PT_berater_classify.md (reuse, keine
# Divergenz). Reihenfolge spiegelt den dortigen Tie-Break (architektonisch >
# factoring > fachlich > semantisch), ist hier aber nur dokumentarisch — die
# Validierung ist mengen-basiert.
CLASSIFICATION_AXES = ("semantic", "architectural", "fachlich", "factoring")

# correction-Subtypen (AK-S1, zweite Signal-Klasse): inkorrekte Umsetzung /
# Kurs-Korrektur sind als Lern-Signal capture-bar, neben der widerlegten Wahrheit.
_CORRECTION_TYPES = frozenset({"correction", "inkorrekte_umsetzung", "kurs_korrektur"})

# Plausibler Git-Commit-Hash: hex, abgekuerzt (>=7) bis voll (40). Konservativ —
# nur ein PLAUSIBILITAETS-Check (kein Repo-Lookup): 7..40 reine Hex-Zeichen.
_COMMIT_REF_RE = re.compile(r"^[0-9a-fA-F]{7,40}$")


def _is_unset(value):
    """True, wenn ein Feld als 'nicht gesetzt' gilt (None oder Leer-String).

    Optionale Felder, die fehlen/None/leer sind, gelten als nicht vorhanden ->
    abwaertskompatibel valide.
    """
    if value is None:
        return True
    if isinstance(value, str) and value.strip() == "":
        return True
    return False


def is_plausible_commit_ref(value):
    """Reines Praedikat: ist `value` ein plausibler Commit-Hash-String?

    Konservativ — kein Repo-Lookup, nur Form (7..40 Hex-Zeichen).
    """
    if not isinstance(value, str):
        return False
    return bool(_COMMIT_REF_RE.match(value.strip()))


def validate_learning_fields(item):
    """Validiert die zwei OPTIONALEN Lern-Felder eines PL-Items.

    Returns {"ok": bool, "errors": [str]}.

    Regeln:
      - item muss ein dict sein (sonst ok=False).
      - commit_ref (wenn gesetzt) muss ein plausibler Hash-String sein.
      - classification (wenn gesetzt) muss in CLASSIFICATION_AXES liegen.
      - BEIDE Felder optional: fehlend/None/leer == valide (abwaertskompatibel).
    """
    errors = []

    if not isinstance(item, dict):
        return {"ok": False, "errors": ["item: kein dict (erwartet PL-Item-Mapping)"]}

    commit_ref = item.get("commit_ref")
    if not _is_unset(commit_ref):
        if not is_plausible_commit_ref(commit_ref):
            errors.append(
                f"commit_ref: '{commit_ref}' ist kein plausibler Commit-Hash "
                f"(erwartet 7-40 Hex-Zeichen)"
            )

    classification = item.get("classification")
    if not _is_unset(classification):
        norm = classification.strip() if isinstance(classification, str) else classification
        if norm not in CLASSIFICATION_AXES:
            errors.append(
                f"classification: '{classification}' nicht in den 4 PT-classify-Achsen "
                f"{list(CLASSIFICATION_AXES)}"
            )

    return {"ok": len(errors) == 0, "errors": errors}


def has_learning_signal(item):
    """Reines Praedikat: traegt das Item ein erntbares Lern-Signal?

    True gdw. commit_ref ODER classification gesetzt ODER type ein
    correction-Subtyp (AK-S1). None-/Nicht-dict-tolerant (-> False).
    """
    if not isinstance(item, dict):
        return False
    if not _is_unset(item.get("commit_ref")):
        return True
    if not _is_unset(item.get("classification")):
        return True
    item_type = item.get("type")
    if isinstance(item_type, str) and item_type.strip().lower() in _CORRECTION_TYPES:
        return True
    return False


if __name__ == "__main__":
    # Windows-stdout ist standardmaessig cp1252 -> Umlaute crashen mit
    # UnicodeEncodeError. utf-8 erzwingen (Py3.7+), fail-safe (a96eb1c-Lehre).
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass

    # Selbst-Demo (Vertrag-Selbsttest) — exit 0 bei erwartetem Verhalten.
    demos = [
        ("beide Felder gueltig", {"commit_ref": "a96eb1c", "classification": "factoring"}, True),
        ("ohne neue Felder (abwaertskompat)", {"type": "addition"}, True),
        ("ungueltige classification", {"classification": "refactoring"}, False),
        ("implausibler commit_ref", {"commit_ref": "nope"}, False),
    ]
    ok_all = True
    for name, item, expect_ok in demos:
        res = validate_learning_fields(item)
        status = "OK" if res["ok"] == expect_ok else "MISMATCH"
        if res["ok"] != expect_ok:
            ok_all = False
        print(f"[{status}] {name}: ok={res['ok']} errors={res['errors']}")
    print(f"has_learning_signal(correction) = {has_learning_signal({'type': 'correction'})}")
    print(f"has_learning_signal(leer)       = {has_learning_signal({'type': 'addition'})}")
    print(f"CLASSIFICATION_AXES = {CLASSIFICATION_AXES}")
    sys.exit(0 if ok_all else 1)
