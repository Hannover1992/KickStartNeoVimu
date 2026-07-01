#!/usr/bin/env python3
"""
test_vault_quality_validator.py — Tests fuer validate_vault_schema.py (BL-161 AK-6).

Ausfuehren:
    python test_vault_quality_validator.py
    python -m pytest test_vault_quality_validator.py -v
"""
from __future__ import annotations

import sys
import json
import tempfile
import textwrap
from pathlib import Path

# validate_vault_schema aus gleichem Verzeichnis laden
sys.path.insert(0, str(Path(__file__).parent))
from validate_vault_schema import (
    validiere_doc,
    pruefe_pflichtfelder,
    pruefe_tag_konsistenz,
    pruefe_backlink_integritaet,
    lese_frontmatter,
    cmd_check,
)


def schreibe_temp_doc(frontmatter: str, body: str = "# Test\n") -> Path:
    """Erstellt temporaere .md-Datei mit gegebenem Frontmatter."""
    tmp = tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8")
    tmp.write(f"---\n{frontmatter}\n---\n{body}")
    tmp.close()
    return Path(tmp.name)


# ============================================================
# T1: Korrektes Minimal-Doc → keine Issues
# ============================================================
def test_t1_korrektes_doc_keine_issues():
    """T1: Ein vollstaendiges korrektes Doc soll 0 Issues erzeugen."""
    fm_yaml = textwrap.dedent("""\
        type: model
        feature: BL-161-vault-quality-system
        bl-item: BL-161
        created: 2026-05-17
        updated: 2026-05-17
        maturity_level: HIGH
        w_total: 14
        tags:
          - bl/BL-161
          - type/model
    """)
    doc = schreibe_temp_doc(fm_yaml)
    try:
        issues = validiere_doc(doc)
        errors = [i for i in issues if i[0] == "ERROR"]
        assert errors == [], f"T1 FAIL: Unerwartete Errors: {errors}"
        print("T1 PASS: Korrektes Model-Doc — 0 Errors")
    finally:
        doc.unlink(missing_ok=True)


# ============================================================
# T2: Fehlendes Pflicht-Feld → ERROR
# ============================================================
def test_t2_fehlendes_pflichtfeld_ergibt_error():
    """T2: Fehlendes Pflicht-Feld 'feature' muss ERROR erzeugen."""
    fm_yaml = textwrap.dedent("""\
        type: spec
        bl-item: BL-161
        created: 2026-05-17
        updated: 2026-05-17
        ak_count: 6
        inv_count: 5
        tags:
          - bl/BL-161
          - type/spec
    """)
    doc = schreibe_temp_doc(fm_yaml)
    try:
        issues = validiere_doc(doc)
        errors = [i for i in issues if i[0] == "ERROR"]
        assert any("feature" in m for _, m in errors), (
            f"T2 FAIL: Kein ERROR fuer fehlendes 'feature': {issues}"
        )
        print("T2 PASS: Fehlendes 'feature' -> ERROR erkannt")
    finally:
        doc.unlink(missing_ok=True)


# ============================================================
# T3: Falscher Typ-spezifischer Pflichtfeld bei model → ERROR
# ============================================================
def test_t3_model_ohne_w_total_ergibt_error():
    """T3: Model ohne w_total muss ERROR erzeugen (typ-spezifisches Pflichtfeld)."""
    fm_yaml = textwrap.dedent("""\
        type: model
        feature: BL-161-vault-quality-system
        bl-item: BL-161
        created: 2026-05-17
        updated: 2026-05-17
        maturity_level: HIGH
        tags:
          - bl/BL-161
          - type/model
    """)
    doc = schreibe_temp_doc(fm_yaml)
    try:
        issues = validiere_doc(doc)
        errors = [i for i in issues if i[0] == "ERROR"]
        assert any("w_total" in m for _, m in errors), (
            f"T3 FAIL: Kein ERROR fuer fehlendes 'w_total': {issues}"
        )
        print("T3 PASS: Model ohne w_total -> ERROR erkannt")
    finally:
        doc.unlink(missing_ok=True)


# ============================================================
# T4: Tag-Alias wird als WARN gemeldet
# ============================================================
def test_t4_tag_alias_ergibt_warn():
    """T4: Tag in Alias-Map muss WARN erzeugen (nicht kanonische Form)."""
    fm = {
        "type": "model",
        "feature": "BL-161-test",
        "bl-item": "BL-161",
        "created": "2026-05-17",
        "updated": "2026-05-17",
        "maturity_level": "LOW",
        "w_total": 1,
        "tags": ["bl/BL-161", "type/model", "KeyClock"],
    }
    tag_aliases = {"KeyClock": "Keycloak", "Auth": "Authentifizierung"}
    issues = pruefe_tag_konsistenz(fm, tag_aliases)
    warns = [i for i in issues if i[0] == "WARN"]
    assert any("KeyClock" in m for _, m in warns), (
        f"T4 FAIL: Kein WARN fuer alias 'KeyClock': {issues}"
    )
    print("T4 PASS: Tag-Alias 'KeyClock' -> WARN erkannt")


# ============================================================
# T5: Doc ohne Frontmatter → WARN (kein ABORT)
# ============================================================
def test_t5_doc_ohne_frontmatter_ergibt_warn():
    """T5: Doc ohne Frontmatter soll WARN (nicht ERROR) erzeugen."""
    tmp = tempfile.NamedTemporaryFile(suffix=".md", delete=False, mode="w", encoding="utf-8")
    tmp.write("# Kein Frontmatter\n\nNur Text.\n")
    tmp.close()
    doc = Path(tmp.name)
    try:
        issues = validiere_doc(doc)
        errors = [i for i in issues if i[0] == "ERROR"]
        warns = [i for i in issues if i[0] == "WARN"]
        assert errors == [], f"T5 FAIL: Unerwartete ERROR bei fehlender FM: {errors}"
        assert len(warns) > 0, f"T5 FAIL: Erwartete WARN bei fehlendem Frontmatter: {issues}"
        print("T5 PASS: Doc ohne Frontmatter -> WARN (kein ERROR)")
    finally:
        doc.unlink(missing_ok=True)


# ============================================================
# Runner
# ============================================================
def run_all_tests() -> int:
    tests = [
        test_t1_korrektes_doc_keine_issues,
        test_t2_fehlendes_pflichtfeld_ergibt_error,
        test_t3_model_ohne_w_total_ergibt_error,
        test_t4_tag_alias_ergibt_warn,
        test_t5_doc_ohne_frontmatter_ergibt_warn,
    ]
    passed = 0
    failed = 0
    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as exc:
            print(f"FAIL: {test_fn.__name__}: {exc}", file=sys.stderr)
            failed += 1
        except Exception as exc:
            print(f"ERROR: {test_fn.__name__}: {exc}", file=sys.stderr)
            failed += 1

    print(f"\nErgebnis: {passed}/{len(tests)} Tests bestanden, {failed} fehlgeschlagen")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
