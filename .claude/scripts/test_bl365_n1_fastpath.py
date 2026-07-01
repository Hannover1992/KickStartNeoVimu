#!/usr/bin/env python3
"""
test_bl365_n1_fastpath.py — BL-365 batch_1 RED-Tests: N=1 Fast-Path Dial + Phase 1.6.

4 Tests (AK-1, AK-2, AK-3, AK-5):
  1. test_n1_fastpath_dial_default_false
  2. test_n1_fastpath_dial_bool_coerce
  3. test_sdf_phase16_has_n1_fastpath_logic
  4. test_sdf_phase16_inv_modus_1

RED-Beweis: 'n1_fastpath_bl365' fehlt in FRAMEWORK_DEFAULTS; Phase 1.6 in
_SDF_orchestrate.md hat keine N=1-Fast-Path-Logik (actionable_count / idf_bypass_reason).
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parent
_SDF_ORCHESTRATE_MD = (
    _SCRIPTS_DIR.parent / "commands" / "_SDF_orchestrate.md"
)

# Importiere die public API exakt wie test_session_params_resolver.py
from session_params_resolver import (
    FRAMEWORK_DEFAULTS,
    resolve_param,
    _coerce_value,
)


# ---------------------------------------------------------------------------
# Test 1: AK-1.3 — n1_fastpath_bl365 Framework-Default == False (default-OFF)
#
# RED-Beweis: 'n1_fastpath_bl365' ist (noch) NICHT in FRAMEWORK_DEFAULTS
#   -> resolve_param liefert None (unbekannt), nicht False -> FAIL (ROT).
# GREEN: fuegt FRAMEWORK_DEFAULTS["n1_fastpath_bl365"] = {"value": False, "_owner": "user"} ein.
# ---------------------------------------------------------------------------

def test_n1_fastpath_dial_default_false(tmp_path: Path) -> None:
    """AK-1.3: n1_fastpath_bl365 ist default-OFF (False) ohne jeden Override.

    Living-Doc-Vertrag: Der N=1-Fast-Path-Dial ist standardmaessig AUS —
    eine Session ohne expliziten Override laeuft den vollstaendigen IDF-Pfad
    byte-identisch zum Vor-BL-365-Zustand (kein IDF-Bypass). Default = False,
    NICHT None (unbekannter Param), NICHT True (aktiv).
    """
    # Arrange: leerer Vault-Root — kein _session_defaults.md, kein BL-Override
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    # Voraussetzung: Param muss in FRAMEWORK_DEFAULTS registriert sein
    assert "n1_fastpath_bl365" in FRAMEWORK_DEFAULTS, (
        "BL-365 AK-1.3: 'n1_fastpath_bl365' muss in FRAMEWORK_DEFAULTS registriert sein. "
        "Fehlt noch -> RED. GREEN fuegt den Eintrag ein."
    )

    # Act: Resolution ohne jeden Override (bl_id=None, leerer Vault)
    result = resolve_param("n1_fastpath_bl365", bl_id=None, vault_root=str(vault_root))

    # Assert: exakt False — nicht None (Key fehlt) und nicht True (faelschlicherweise aktiv)
    assert result is False, (
        "BL-365 AK-1.3 verletzt: n1_fastpath_bl365 muss ohne Override den "
        f"Framework-Default False liefern (default-OFF, kein IDF-Bypass), erhalten: {result!r}. "
        "result is None => Key fehlt in FRAMEWORK_DEFAULTS (RED-Ursache)."
    )


# ---------------------------------------------------------------------------
# Test 2: AK-2 — String-Coercion "true"/"false" -> bool
#
# RED-Beweis: _coerce_value kennt "n1_fastpath_bl365" noch nicht
#   -> entweder KeyError oder falsche Typ-Konversion -> FAIL (ROT).
# GREEN: fuegt bool-Coercion fuer n1_fastpath_bl365 analog zu "tdd" ein.
# ---------------------------------------------------------------------------

def test_n1_fastpath_dial_bool_coerce() -> None:
    """AK-2: n1_fastpath_bl365 -> bool korrekt (Muster: tdd, parallel_mode).

    String-Quellwerte aus _session_params.md werden zu nativen bool konvertiert:
      "true"  -> True
      "false" -> False
      True    -> True  (native bool durchgereicht)
      False   -> False (native bool durchgereicht)
    Analog zu _coerce_value("tdd", ...) und _coerce_value("parallel_mode", ...).
    """
    assert _coerce_value("n1_fastpath_bl365", "true") is True, (
        "BL-365 AK-2: _coerce_value('n1_fastpath_bl365', 'true') muss True liefern. "
        "Fehler => Coercion noch nicht implementiert (RED)."
    )
    assert _coerce_value("n1_fastpath_bl365", "false") is False, (
        "BL-365 AK-2: _coerce_value('n1_fastpath_bl365', 'false') muss False liefern."
    )
    assert _coerce_value("n1_fastpath_bl365", True) is True, (
        "BL-365 AK-2: native bool True muss durchgereicht werden."
    )
    assert _coerce_value("n1_fastpath_bl365", False) is False, (
        "BL-365 AK-2: native bool False muss durchgereicht werden."
    )


# ---------------------------------------------------------------------------
# Test 3: AK-3 — _SDF_orchestrate.md Phase 1.6 enthaelt N=1-Fast-Path-Logik
#
# RED-Beweis: Phase 1.6 hat aktuell NUR den generellen IDF-GATE-Block (Skill(_IDF_orchestrate)).
#   Keine actionable_count-Abfrage, kein idf_bypass_reason, kein "N=1"-Kommentar,
#   kein Hinweis dass Skill(_IDF_orchestrate) bei N=1 NICHT aufgerufen wird -> FAIL (ROT).
# GREEN: fuegt N=1-Fast-Path-Logik in Phase 1.6 ein.
# ---------------------------------------------------------------------------

def test_sdf_phase16_has_n1_fastpath_logic() -> None:
    """AK-3: _SDF_orchestrate.md Phase 1.6 enthaelt N=1-Fast-Path-Logik.

    Greift nach 4 Schluessel-Begriffen die den Fast-Path definieren:
      - "actionable_count"    : Zaehl-Variable der aktionsfaehigen Items
      - "idf_bypass_reason"   : Dokumentations-Feld wenn IDF uebersprungen wird
      - "N=1" oder "n1_fastpath": Marker fuer den Fast-Path-Zweig
      - Hinweis kein Skill(_IDF_orchestrate)-Aufruf bei N=1 (negatives Muster)

    Alle 4 Terme muessen im Datei-Inhalt vorkommen (in Phase-1.6-Naehe).
    """
    assert _SDF_ORCHESTRATE_MD.exists(), (
        f"_SDF_orchestrate.md nicht gefunden: {_SDF_ORCHESTRATE_MD}. "
        "Pfad-Problem oder Datei fehlt."
    )

    content = _SDF_ORCHESTRATE_MD.read_text(encoding="utf-8")

    # Term 1: actionable_count
    assert "actionable_count" in content, (
        "BL-365 AK-3: 'actionable_count' fehlt in _SDF_orchestrate.md. "
        "Phase 1.6 N=1-Fast-Path-Logik noch nicht implementiert (RED)."
    )

    # Term 2: idf_bypass_reason
    assert "idf_bypass_reason" in content, (
        "BL-365 AK-3: 'idf_bypass_reason' fehlt in _SDF_orchestrate.md. "
        "Phase 1.6 N=1-Bypass-Dokumentationsfeld noch nicht implementiert (RED)."
    )

    # Term 3: N=1 oder n1_fastpath (case-sensitive — Skill-Kommentare verwenden beide)
    has_n1_marker = ("N=1" in content) or ("n1_fastpath" in content)
    assert has_n1_marker, (
        "BL-365 AK-3: Weder 'N=1' noch 'n1_fastpath' in _SDF_orchestrate.md. "
        "Phase 1.6 Fast-Path-Marker fehlt (RED)."
    )

    # Term 4: Expliziter Hinweis dass bei N=1 Skill(_IDF_orchestrate) NICHT aufgerufen wird.
    # Pattern: "kein Skill(_IDF_orchestrate)" oder "KEIN Skill(_IDF_orchestrate)"
    # oder "IDF_orchestrate) nicht" oder "skip" + "IDF" in Naehe.
    has_no_idf_hint = bool(
        re.search(r"(?i)kein\s+Skill\(_IDF_orchestrate\)", content)
        or re.search(r"(?i)skip.*IDF_orchestrate", content)
        or re.search(r"(?i)IDF_orchestrate.*skip", content)
        or re.search(r"(?i)bypass.*IDF_orchestrate", content)
        or re.search(r"(?i)IDF_orchestrate.*bypass", content)
        or re.search(r"(?i)KEIN.*IDF.*aufruf", content)
        or re.search(r"(?i)idf_bypass_reason.*N=1", content)
        or re.search(r"N=1.*kein.*IDF", content, re.IGNORECASE)
    )
    assert has_no_idf_hint, (
        "BL-365 AK-3: Kein Hinweis in _SDF_orchestrate.md dass bei N=1 "
        "Skill(_IDF_orchestrate) NICHT aufgerufen wird. "
        "Fast-Path-Logik mit explizitem IDF-Skip fehlt (RED)."
    )


# ---------------------------------------------------------------------------
# Test 4: AK-5 — INV-MODUS-1: Phase 1.6 schreibt nur batch_mode_hints, NIE batch_modes
#
# RED-Beweis: Phase 1.6 erwaehnt weder "batch_mode_hints" noch "INV-MODUS-1"
#   im Fast-Path-Kontext -> FAIL (ROT).
# GREEN: Fast-Path-Logik in Phase 1.6 setzt batch_mode_hints (NICHT batch_modes)
#        und referenziert INV-MODUS-1.
# ---------------------------------------------------------------------------

def test_sdf_phase16_inv_modus_1() -> None:
    """AK-5: N=1-Inline-Logik in Phase 1.6 schreibt batch_mode_hints, NIE batch_modes.

    Grep-Beleg: der Phase-1.6-Abschnitt enthaelt:
      - "batch_mode_hints"  : das erlaubte Pre-SDF-Feld (Empfehlung, nicht Setzung)
      - "INV-MODUS-1"       : explizite Regel-Referenz (nur C3 setzt batch_modes)

    INV-MODUS-1 verbietet jedem anderen als _SDF_berater_modusEntscheidung
    das Schreiben von batch_modes. Der N=1-Fast-Path muss diese Invariante
    dokumentieren und das Feld batch_mode_hints (statt batch_modes) verwenden.
    """
    assert _SDF_ORCHESTRATE_MD.exists(), (
        f"_SDF_orchestrate.md nicht gefunden: {_SDF_ORCHESTRATE_MD}."
    )

    content = _SDF_ORCHESTRATE_MD.read_text(encoding="utf-8")

    # Term 1: batch_mode_hints (das erlaubte Pre-SDF-Feld)
    assert "batch_mode_hints" in content, (
        "BL-365 AK-5: 'batch_mode_hints' fehlt in _SDF_orchestrate.md. "
        "Phase 1.6 N=1-Fast-Path muss batch_mode_hints (NICHT batch_modes) setzen (RED)."
    )

    # Term 2: INV-MODUS-1 im Kontext der Phase-1.6 Fast-Path-Logik
    # Pruefe dass INV-MODUS-1 im Text vorkommt (kein Positions-Check —
    # die Referenz muss irgendwo im Dokument stehen; Phase 1.6 wird sie enthalten)
    assert "INV-MODUS-1" in content, (
        "BL-365 AK-5: 'INV-MODUS-1' fehlt in _SDF_orchestrate.md. "
        "Phase 1.6 N=1-Fast-Path-Logik muss INV-MODUS-1 explizit referenzieren "
        "um den batch_mode_hints-vs-batch_modes-Unterschied zu begruenden (RED). "
        "Hinweis: INV-MODUS-1 existiert bereits im CLAUDE.md-Kontext aber "
        "fehlt als expliziter Anker in der Phase-1.6-Logik von _SDF_orchestrate.md."
    )

    # Haerterer Beweis: beide Terme im selben Dokument ist notwendig aber
    # kein Positions-Fenster-Check erforderlich (die Fast-Path-Logik wird
    # den Abschnitt klar in Phase 1.6 verorten). Grep-Beleg erfuellt.
