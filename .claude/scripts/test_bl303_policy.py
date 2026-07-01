"""
BL-303 batch_2 Policy Content-Verify Tests (RED Phase)
M2/content-verify: prueft ob _TDD_green.md und _TDD_red.md
die BL-303 Policy-Dokumentation (Schritt 1.6, autorisierte
Test-Korrektur-Escape) enthalten.

GREEN-Worker muss:
  - _TDD_green.md: Schritt 1.6 + test_correction_authorized + BL-303 + autorisiert/Escape einfuegen
  - _TDD_red.md:   Schritt 1.6 + test_correction + BL-303 einfuegen
  - AK5_ForwardVerify.md im BL-Folder anlegen

RED-Erwartung: alle 3 Tests FAIL (Strings fehlen, Datei fehlt).
"""
import pathlib
import subprocess
import sys

REPO_ROOT = pathlib.Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA")
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"
TDD_GREEN_MD = COMMANDS_DIR / "_TDD_green.md"
TDD_RED_MD = COMMANDS_DIR / "_TDD_red.md"

BL_FOLDER = pathlib.Path(
    "C:/Users/hanno/Documents/Work/Wissen/Berechtigung/OmniCommand/OmniCommand"
    "/Backlog"
    "/BL-303-tdd-green-protection-keine-autorisierte-testkorrektur-escape-hatch-finding-vs-test-adjudikation"
)
AK5_DOC = BL_FOLDER / "AK5_ForwardVerify.md"


def read_file(path: pathlib.Path) -> str:
    """Liest Datei-Inhalt als String. Gibt leeren String zurueck wenn Datei fehlt."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: _TDD_green.md dokumentiert den autorisierten-Test-Korrektur-Escape
# ---------------------------------------------------------------------------
def test_tdd_green_policy_authorized_correction():
    """
    _TDD_green.md muss Schritt 1.6 (oder Green-Schutz-Abschnitt) enthalten,
    der die autorisierte Test-Korrektur dokumentiert:
    - "test_correction_authorized" (technisches Schluesselwort)
    - "BL-303" (Rueckverweis auf Herkunft)
    - "autorisiert" ODER "Escape" (Policy-Kontext)

    GREEN-Worker legt diese Strings an. Fehlen sie → AssertionError (RED).
    """
    content = read_file(TDD_GREEN_MD)
    assert content, f"_TDD_green.md nicht lesbar oder leer: {TDD_GREEN_MD}"

    assert "test_correction_authorized" in content, (
        "POLICY FEHLT: _TDD_green.md enthaelt nicht 'test_correction_authorized'. "
        "GREEN-Worker muss Schritt 1.6 mit Escape-Hatch-Dokumentation einfuegen (BL-303)."
    )
    assert "BL-303" in content, (
        "POLICY FEHLT: _TDD_green.md enthaelt nicht 'BL-303'. "
        "Schritt 1.6 muss den Herkunfts-BL referenzieren."
    )
    # Mindestens eines der beiden kontextuellen Schlagworte muss vorkommen
    assert ("autorisiert" in content) or ("Escape" in content), (
        "POLICY FEHLT: _TDD_green.md enthaelt weder 'autorisiert' noch 'Escape'. "
        "Schritt 1.6 muss den Policy-Kontext (autorisierte Verhaltens-Aenderung / Escape-Hatch) beschreiben."
    )


# ---------------------------------------------------------------------------
# Test 2: _TDD_red.md dokumentiert den korrigierten Test als neues RED
# ---------------------------------------------------------------------------
def test_tdd_red_policy():
    """
    _TDD_red.md muss dokumentieren, dass bei autorisierter test-correction
    der korrigierte Test das neue RED ist (Schritt 1.6):
    - "test_correction" (Policy-Begriff)
    - "BL-303" (Rueckverweis)

    GREEN-Worker legt diese Strings an. Fehlen sie → AssertionError (RED).
    """
    content = read_file(TDD_RED_MD)
    assert content, f"_TDD_red.md nicht lesbar oder leer: {TDD_RED_MD}"

    assert "test_correction" in content, (
        "POLICY FEHLT: _TDD_red.md enthaelt nicht 'test_correction'. "
        "GREEN-Worker muss Schritt 1.6 einfuegen: bei autorisierter Korrektur "
        "ist der korrigierte Test das neue RED (BL-303)."
    )
    assert "BL-303" in content, (
        "POLICY FEHLT: _TDD_red.md enthaelt nicht 'BL-303'. "
        "Schritt 1.6 muss den Herkunfts-BL referenzieren."
    )


# ---------------------------------------------------------------------------
# Test 3: AK-5 Forward-Verify Contract-Doc existiert im BL-Folder
# ---------------------------------------------------------------------------
def test_ak5_forward_verify_contract():
    """
    AK-5-Contract: AK5_ForwardVerify.md im BL-Folder muss existieren UND
    die T2094/T2095-Klasse beschreiben:
    - "T2094" ODER "T2095" (Forward-Verify-Testklassen)
    - "autorisiert" (positiver Fall: mit Autorisierung gebaut)
    - "blockt" ODER "geblockt" ODER "GREEN_BLOCKED" (negativer Fall: ohne Autorisierung geblockt)

    GREEN-Worker erstellt dieses Dokument. Fehlt es → AssertionError (RED).
    """
    assert AK5_DOC.exists(), (
        f"AK-5-CONTRACT FEHLT: {AK5_DOC} existiert nicht. "
        "GREEN-Worker muss AK5_ForwardVerify.md anlegen mit T2094/T2095-Beschreibung."
    )

    content = AK5_DOC.read_text(encoding="utf-8")

    assert ("T2094" in content) or ("T2095" in content), (
        "AK-5-CONTRACT UNVOLLSTAENDIG: AK5_ForwardVerify.md enthaelt weder 'T2094' noch 'T2095'. "
        "Die Forward-Verify-Testklassen muessen beschrieben sein."
    )
    assert "autorisiert" in content, (
        "AK-5-CONTRACT UNVOLLSTAENDIG: AK5_ForwardVerify.md enthaelt nicht 'autorisiert'. "
        "Der positive Fall (mit Autorisierung gebaut) muss beschrieben sein."
    )
    assert ("blockt" in content) or ("geblockt" in content) or ("GREEN_BLOCKED" in content), (
        "AK-5-CONTRACT UNVOLLSTAENDIG: AK5_ForwardVerify.md enthaelt keinen Block-Indikator "
        "('blockt'/'geblockt'/'GREEN_BLOCKED'). "
        "Der negative Fall (ohne Autorisierung geblockt) muss beschrieben sein."
    )
