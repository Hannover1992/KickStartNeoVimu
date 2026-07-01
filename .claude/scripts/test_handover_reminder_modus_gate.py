#!/usr/bin/env python3
"""Tests fuer die Modus-Gate-Funktion des Handschuhwechsel-Reminder-Beraters.

BL-227 Sub-Batch C-3 (AK-9 Modus-Gate-Matrix M3 primaer / M2 optional / M1 aus,
AK-10 Kern-Ziel-Doc-Anker). TDD Stage 1 (Atomic / Laserpointer — Unit, mocks_erlaubt=ja).

SUT: modus_gate(modus, toggle) -> reminder_action  (rein, NUR-LESEND, INV-MODUS-1 Read-Only).

Gate-Matrix (toggle="on"):
  M1 -> "no-fire"   (Modus-Gating aus)
  M3 -> "fire"      (KRITISCHER Hauptfall, DCSRE-486 19->4-Skip-Beleg)
  M2 -> "optional"  (konfigurierbar, Aufrufer entscheidet)

Master-Gate (toggle != "on"):
  toggle="off" / None / beliebig != "on" -> "no-fire" fuer JEDEN Modus.

Fail-Safe (unbekannte Modi):
  M4, M9, "UNKNOWN", "" -> "no-fire" (kein KeyError, kein Crash).

AK-10-Doc-Anker:
  Kern-Ziel im Modul-Header verankert + DCSRE-486-Referenz enthalten.
"""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from handover_reminder_gate import modus_gate, _GATE_MATRIX


# ---------------------------------------------------------------------------
# Ring 0 — Kanarienvogel (deterministisch, bricht Folge-Suite bei Regression)
# ---------------------------------------------------------------------------

def test_gate_m1_no_fire():
    """Kanarienvogel (Ring 0): M1 + toggle=on darf NICHT feuern.

    M1 = Skelett-Modus ohne Phase-3-Gating -> Reminder aus. Bricht dieser Test,
    gilt STOPP gemaess Kanarienvogel-Regel: kein anderer Test zaehlt mehr."""
    assert modus_gate("M1", toggle="on") == "no-fire"


# ---------------------------------------------------------------------------
# Ring 1 — Toggle-Master-Gate (AK-5/AK-9: toggle ist Vor-Bedingung)
# ---------------------------------------------------------------------------

def test_toggle_off_m3_no_fire():
    """toggle=off: M3 darf NICHT feuern, auch wenn Modus kritisch waere."""
    assert modus_gate("M3", toggle="off") == "no-fire"


def test_toggle_off_m2_no_fire():
    """toggle=off: M2 darf NICHT feuern."""
    assert modus_gate("M2", toggle="off") == "no-fire"


def test_toggle_off_m1_no_fire():
    """toggle=off: M1 bleibt korrekt no-fire (Double-check)."""
    assert modus_gate("M1", toggle="off") == "no-fire"


def test_toggle_default_is_off():
    """Default-Toggle (kein Argument) verhält sich wie toggle='off'.

    Regression-Schutz: Kein Modus faellt durch, wenn toggle nicht explizit
    uebergeben wird (Framework-Default ist 'off', AK-5/AK-8)."""
    assert modus_gate("M3") == "no-fire"
    assert modus_gate("M2") == "no-fire"
    assert modus_gate("M1") == "no-fire"


def test_toggle_none_no_fire():
    """toggle=None zählt nicht als 'on' -> no-fire für alle Modi."""
    assert modus_gate("M3", toggle=None) == "no-fire"
    assert modus_gate("M2", toggle=None) == "no-fire"


def test_toggle_truthy_but_not_on_no_fire():
    """toggle=True (bool) ist NICHT dasselbe wie 'on' -> no-fire.

    Der Toggle kennt nur exakt den String 'on' als aktiven Wert (AK-8)."""
    assert modus_gate("M3", toggle=True) == "no-fire"
    assert modus_gate("M3", toggle=1) == "no-fire"
    assert modus_gate("M3", toggle="ON") == "no-fire"   # Gross-/Kleinschreibung
    assert modus_gate("M3", toggle="On") == "no-fire"


# ---------------------------------------------------------------------------
# Ring 2 — Modus-Gate-Matrix bei toggle=on (AK-9 Kern)
# ---------------------------------------------------------------------------

def test_gate_m3_fires():
    """M3 + toggle=on -> 'fire' (KRITISCHER Hauptfall, AK-9)."""
    assert modus_gate("M3", toggle="on") == "fire"


def test_gate_m2_optional():
    """M2 + toggle=on -> 'optional' (konfigurierbar, AK-9 / REQCHECK-WARNING).

    M2-WARNING-Aufloesung: Das Gate liefert 'optional' als explizites Signal
    (nicht 'fire', nicht 'no-fire'). Der Aufrufer (C-4-Hook) entscheidet
    final. Konservative Default-Interpretation: feuert, aber mit niedrigerer
    Prio als M3."""
    assert modus_gate("M2", toggle="on") == "optional"


def test_gate_m1_no_fire_with_toggle_on():
    """M1 + toggle=on -> 'no-fire' (Geschwindigkeit zaehlt, AK-9)."""
    assert modus_gate("M1", toggle="on") == "no-fire"


# ---------------------------------------------------------------------------
# Ring 3 — Fail-Safe fuer unbekannte/zukuenftige Modi (M4..M9, Sonderwerte)
# ---------------------------------------------------------------------------

def test_gate_unknown_modus_no_fire():
    """Unbekannter Modus (z.B. zukuenftiger M4) -> 'no-fire' (Fail-Safe, kein Crash)."""
    assert modus_gate("M4", toggle="on") == "no-fire"
    assert modus_gate("M9", toggle="on") == "no-fire"
    assert modus_gate("UNKNOWN", toggle="on") == "no-fire"
    assert modus_gate("", toggle="on") == "no-fire"


def test_gate_unknown_modus_no_keyerror():
    """Unbekannter Modus darf KEINEN KeyError werfen (Robustheit)."""
    try:
        result = modus_gate("M99", toggle="on")
        assert result == "no-fire"
    except KeyError:
        raise AssertionError("modus_gate wirft KeyError fuer unbekannten Modus — Fail-Safe verletzt")


# ---------------------------------------------------------------------------
# Ring 4 — Read-Only-Invariante (INV-MODUS-1, AK-12)
# ---------------------------------------------------------------------------

def test_gate_does_not_mutate_gate_matrix():
    """modus_gate darf _GATE_MATRIX NICHT veraendern (INV-MODUS-1 Read-Only).

    Snapshot vor und nach mehreren Gate-Aufrufen muss identisch sein."""
    snapshot_before = dict(_GATE_MATRIX)
    for _ in range(10):
        modus_gate("M1", toggle="on")
        modus_gate("M2", toggle="on")
        modus_gate("M3", toggle="on")
        modus_gate("M4", toggle="on")   # unbekannt
        modus_gate("M3", toggle="off")
    assert _GATE_MATRIX == snapshot_before, (
        "_GATE_MATRIX wurde durch modus_gate veraendert — INV-MODUS-1 verletzt"
    )


# ---------------------------------------------------------------------------
# Ring 5 — Vollstaendigkeit _GATE_MATRIX + Werte-Enum (AK-9 / Vollabdeckung)
# ---------------------------------------------------------------------------

def test_gate_matrix_known_entries():
    """_GATE_MATRIX enthaelt genau die bekannten Eintraege M1/M2/M3 mit korrekten Werten."""
    assert _GATE_MATRIX.get("M1") == "no-fire"
    assert _GATE_MATRIX.get("M2") == "optional"
    assert _GATE_MATRIX.get("M3") == "fire"


def test_gate_return_values_are_enum():
    """modus_gate gibt ausschliesslich Werte aus {'fire', 'optional', 'no-fire'} zurueck."""
    allowed = {"fire", "optional", "no-fire"}
    probe_modi = ["M1", "M2", "M3", "M4", "M99", "UNKNOWN", ""]
    probe_toggles = ["on", "off", None]
    for modus in probe_modi:
        for toggle in probe_toggles:
            result = modus_gate(modus, toggle=toggle)
            assert result in allowed, (
                f"modus_gate({modus!r}, toggle={toggle!r}) gab {result!r} zurueck "
                f"— ausserhalb des erlaubten Enums {allowed}"
            )


# ---------------------------------------------------------------------------
# Ring D — Doc-Review-Substitute (AK-10 Kern-Ziel-Anker, Border/Doc-Review)
# ---------------------------------------------------------------------------

def test_ak10_kern_ziel_verankert_in_module_docstring():
    """AK-10: Das Kern-Ziel ist im Modul-Docstring verankert + DCSRE-486-Referenz.

    Test-Strategy fuer AK-10 ist 'Doc-Review (Border)' — hier als Smoke-Check
    auf Schluesselbegriffe im Modul-Header umgesetzt."""
    import handover_reminder_gate as mod
    doc = (mod.__doc__ or "").lower()

    # Kern-Ziel-Formulierung (wortgleich oder sinngleich)
    assert "m3 entschieden" in doc or "m3" in doc, (
        "AK-10: Modul-Docstring enthaelt kein M3-Bezug (Kern-Ziel-Anker fehlt)"
    )
    # DCSRE-486-Beleg
    assert "dcsre-486" in doc, (
        "AK-10: Modul-Docstring enthaelt keinen DCSRE-486-Verweis (Beleg fehlt)"
    )
    # Pflicht-Formulierung "muss" / "verbindlich" o.ae.
    assert "muss" in doc or "verbindlich" in doc or "nicht uebersprungen" in doc, (
        "AK-10: Kern-Ziel-Formulierung ('MUSS durchgezogen', 'verbindlich') fehlt"
    )


if __name__ == "__main__":
    # Quick-Smoke-Run ohne pytest
    tests = [
        test_gate_m1_no_fire,
        test_toggle_off_m3_no_fire,
        test_toggle_off_m2_no_fire,
        test_toggle_off_m1_no_fire,
        test_toggle_default_is_off,
        test_toggle_none_no_fire,
        test_toggle_truthy_but_not_on_no_fire,
        test_gate_m3_fires,
        test_gate_m2_optional,
        test_gate_m1_no_fire_with_toggle_on,
        test_gate_unknown_modus_no_fire,
        test_gate_unknown_modus_no_keyerror,
        test_gate_does_not_mutate_gate_matrix,
        test_gate_matrix_known_entries,
        test_gate_return_values_are_enum,
        test_ak10_kern_ziel_verankert_in_module_docstring,
    ]
    passed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except Exception as exc:
            print(f"  FAIL  {t.__name__}: {exc}")
    print(f"\n=== {passed}/{len(tests)} PASS ===")
