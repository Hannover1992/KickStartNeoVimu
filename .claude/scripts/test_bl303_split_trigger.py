"""
BL-303 AK-1: Split-Trigger-Doku (content-grep, RED-Phase).

Prueft dass _SDF_berater_modusEntscheidung.md einen expliziten Trigger dokumentiert:
  "Item aendert bestehende Test-Assertions" -> split_required=true -> aus M2 raus (nach M3).

Aktueller Zustand (RED): Die Datei dokumentiert split_required-Trigger fuer k_score_max
und verify_mode-Heterogenitaet (Schritt 7), aber KEINEN Trigger fuer den Fall dass eine
geplante Code-Aenderung bestehende Test-Assertions beruehrt (Test-Correction-Fall, BL-303).

Erwartetes Verhalten nach GREEN:
  Die Datei enthaelt im split_required-Kontext (SCHRITT 7 oder Aequivalent) eine Bedingung
  die sinngemaesch "Item aendert Test-Assertion" -> split_required=true -> M3-Pflicht mappt.

Lauf: pytest .claude/scripts/test_bl303_split_trigger.py   (exit 0 = alle gruen)
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MD_PATH = REPO_ROOT / ".claude" / "commands" / "_SDF_berater_modusEntscheidung.md"


def _load_md() -> str:
    assert MD_PATH.exists(), f"Datei nicht gefunden: {MD_PATH}"
    return MD_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AK-1a: Die Datei enthaelt ueberhaupt split_required-Kontext (Sanity-Check).
# ---------------------------------------------------------------------------
def test_AK1a_split_required_context_exists():
    """Sanity: split_required ist bekannt dokumentiert (Baseline-Check, MUSS gruen sein)."""
    content = _load_md()
    assert "split_required" in content, (
        "split_required fehlt komplett in der Datei — Baseline-Check schlaegt fehl"
    )


# ---------------------------------------------------------------------------
# AK-1b (RED): Im split_required-Block fehlt ein Trigger fuer
# "Item aendert Test-Assertion" / Test-Correction-Fall.
#
# Der Test sucht nach Woertern die diesen Trigger beschreiben. Alle Patterns
# muessen derzeit NICHT matchen -> Test ist RED. Nach GREEN (Impl) matcht
# mindestens ein Pattern.
# ---------------------------------------------------------------------------
_TEST_CORRECTION_PATTERNS = [
    # Direkte Beschreibung des Test-Correction-Triggers
    r"test[_\s-]?correction",
    r"aendert\s+(?:bestehende\s+)?[Tt]est[\s-][Aa]ssertion",
    r"modif(?:ies|iziert)\s+(?:existing\s+)?test[\s-]assertion",
    # "beruehrt / betrifft bestehende Assertion"
    r"beruehr\w*\s+(?:bestehende\s+)?(?:gruene\s+)?[Tt]est",
    r"affect\w*\s+existing\s+(?:green\s+)?test[\s-]assertion",
    # "Test-Assertion-Aenderung" als split_required-Grund
    r"split.*test[\s_-]assertion",
    r"test[\s_-]assertion.*split",
    # BL-303-Referenz im split_required-Kontext (wuerde automatisch Doku anzeigen)
    r"BL-303.*split",
    r"split.*BL-303",
]


def test_AK1b_modusentscheidung_has_test_assertion_split_trigger():
    """
    RED (jetzt): _SDF_berater_modusEntscheidung.md enthaelt NOCH KEINEN split_required-Trigger
    fuer den Fall 'Item aendert bestehende Test-Assertion' (BL-303 AK-1).

    POSITIV-ASSERTION: mindestens 1 Pattern aus _TEST_CORRECTION_PATTERNS MUSS im Inhalt
    gefunden werden (nach GREEN-Impl).

    FAILt jetzt (Feature fehlt) = korrektes RED.
    GREENt nach Impl (Pattern hinzugefuegt in SCHRITT 7 / split_required-Block).
    """
    content = _load_md()

    matched = []
    for pattern in _TEST_CORRECTION_PATTERNS:
        m = re.search(pattern, content, re.IGNORECASE)
        if m:
            matched.append((pattern, m.group(0)))

    # POSITIV: nach GREEN MUSS mindestens 1 Pattern matchen.
    assert len(matched) >= 1, (
        f"AK-1b FAIL (RED — erwartet): _SDF_berater_modusEntscheidung.md enthaelt KEINEN "
        f"split_required-Trigger fuer 'Item aendert Test-Assertion'.\n"
        f"Gesuchte Patterns: {_TEST_CORRECTION_PATTERNS}\n"
        f"Kein einziger Treffer gefunden.\n"
        f"=> GREEN-Impl muss einen dieser Begriffe im split_required-Kontext ergaenzen."
    )


# ---------------------------------------------------------------------------
# AK-1c (RED): Der Split-Trigger-Kontext (SCHRITT 7 Mitose-Logik) verweist
# NICHT auf M3-Pflicht bei Test-Assertion-Beruehrung.
#
# Nach GREEN: "test_correction" -> split_required=true -> "M3" oder "m3" im Kontext.
# ---------------------------------------------------------------------------
def test_AK1c_modusentscheidung_test_correction_reroutes_m3():
    """
    RED (jetzt): _SDF_berater_modusEntscheidung.md dokumentiert NOCH KEINEN Pfad
    'Test-Correction-Item -> M3-Pflicht' (BL-303 AK-1).

    POSITIV-ASSERTION: Mindestens 1 Absatz MUSS enthalten:
      - split_required (im Kontext) UND
      - M3 UND
      - Test-Assertion-Bezug (Assertion | test_correction | aendert)

    FAILt jetzt (Kombination fehlt) = korrektes RED.
    GREENt nach Impl (SCHRITT 7 erwaehnt M3 + Test-Assertion-Trigger im split_required-Block).
    """
    content = _load_md()

    # Suche nach Absaetzen die split_required + M3 + test in Naehe von "Assertion" erwaehnen
    paragraphs = re.split(r"\n{2,}", content)

    m3_split_test_paragraphs = [
        p for p in paragraphs
        if re.search(r"split_required", p, re.IGNORECASE)
        and re.search(r"\bM3\b", p)
        and re.search(r"[Tt]est", p)
        and re.search(r"[Aa]ssertion|test[_\s-]correction|aendert", p, re.IGNORECASE)
    ]

    # POSITIV: nach GREEN MUSS mindestens 1 solcher Absatz existieren.
    assert len(m3_split_test_paragraphs) >= 1, (
        f"AK-1c FAIL (RED — erwartet): Kein Absatz in _SDF_berater_modusEntscheidung.md "
        f"verbindet split_required + M3 + Test-Assertion-Kontext.\n"
        f"Gesuchte Kombination: split_required AND M3 AND (Assertion|test_correction|aendert) "
        f"im selben Absatz.\n"
        f"=> GREEN-Impl muss einen Hinweis auf M3-Pflicht bei Test-Correction im "
        f"split_required-Block ergaenzen."
    )
