#!/usr/bin/env python3
"""Tests fuer den Handschuhwechsel-Reminder-Kern (BL-227 Sub-Batch C-1, AK-1/2/3).

SUT: build_reminder(target_orchestrator, next_step, handoff_block) -> str
  (rein, NUR-LESEND, INV-MODUS-1 Read-Only, KEIN Block-Pfad — AK-12).

Der Kern baut die Progressive-Disclosure-Injektion fuer einen nicht-motorisierten
Handschuhwechsel (A->IDF / IDF->SDF / SC->Post / I->SDF_post). Er erinnert den Team
Lead an GENAU den naechsten Pflicht-Schritt (k+1) + dessen Delegations-Vertrag — als
XML-schema-getaggte, durchnummerierte, ACK-pflichtige, sandwiched Injektion.

Test-First (greenfield / uncovered, M3-artig). RED-Ring 0 (Kanarienvogel):
test_reminder_is_xml_wellformed garantiert RED, weil handover_reminder_core.py /
build_reminder() noch NICHT existiert (ImportError).

AK-Abdeckung:
  AK-1: Reminder existiert + ist als Berater-Kern aufrufbar (Import + Marker-Tag).
  AK-2: Progressive Disclosure — GENAU 1 Step (k+1), KEINE Folge-Steps (k+2..n).
  AK-3: XML-wohlgeformt, durchnummerierte Step-ID, ACK-Pflichtfeld, keine Prosa,
        Sandwiching (Step vor UND nach dem Handoff-Datenblock).
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _next_step():
    return {
        "id": 8,
        "name": "validator",
        "objective": "Spec-vs-IST Delta pruefen",
        "output_format": "validator.md",
        "boundaries": "kein Code, nur Read",
    }


def _build():
    from handover_reminder_core import build_reminder
    return build_reminder(
        target_orchestrator="_IDF_orchestrate",
        next_step=_next_step(),
        handoff_block="<<<HANDOFF-DATEN A->IDF>>>",
    )


# --- Ring 0: Kanarienvogel (deterministisch RED bis SUT existiert) ---
def test_reminder_is_xml_wellformed():
    """AK-3: Die Injektion ist in EIN wohlgeformtes XML-Envelope gekapselt."""
    out = _build()
    # Jeder <step-reminder>-Block muss fuer sich wohlgeformt parsebar sein.
    blocks = [b for b in out.split("<step-reminder") if b.strip()]
    assert blocks, "kein <step-reminder>-Block gefunden"
    for b in blocks:
        frag = "<step-reminder" + b.split("</step-reminder>")[0] + "</step-reminder>"
        ET.fromstring(frag)  # ParseError wenn nicht wohlgeformt


# --- AK-3: durchnummerierte Step-ID ---
def test_reminder_has_numbered_step_id():
    out = _build()
    frag = "<step-reminder" + out.split("<step-reminder", 1)[1].split("</step-reminder>")[0] + "</step-reminder>"
    el = ET.fromstring(frag)
    assert el.get("step-id") == "8", "step-id muss die durchnummerierte k+1-ID (8) sein"


# --- AK-3: ACK-Pflichtfeld vorhanden ---
def test_reminder_has_ack_field():
    out = _build()
    frag = "<step-reminder" + out.split("<step-reminder", 1)[1].split("</step-reminder>")[0] + "</step-reminder>"
    el = ET.fromstring(frag)
    assert el.find("ack") is not None, "ACK-Pflichtfeld <ack> fehlt"
    assert el.find("ack").get("required") == "true"


# --- AK-2: Progressive Disclosure — GENAU 1 Step, keine Folge-Steps ---
def test_reminder_discloses_exactly_one_step():
    out = _build()
    # Genau ein eindeutiger step-id-Wert (k+1), keine k+2..n.
    import re
    ids = sorted(set(re.findall(r'step-id="(\d+)"', out)))
    assert ids == ["8"], f"erwartet GENAU step-id 8 (k+1), gefunden: {ids}"


# --- AK-3: Sandwiching — Step vor UND nach dem Handoff-Datenblock ---
def test_reminder_sandwiches_handoff_block():
    out = _build()
    first = out.find("<step-reminder")
    handoff = out.find("<<<HANDOFF-DATEN A->IDF>>>")
    last = out.rfind("<step-reminder")
    assert -1 < first < handoff < last, (
        "Sandwiching verletzt: Step muss VOR und NACH dem Handoff-Datenblock erscheinen"
    )


# --- AK-3: keine Prosa (Vertrag steckt in getaggten Feldern, nicht in Freitext) ---
def test_reminder_contract_fields_are_tagged_not_prose():
    out = _build()
    frag = "<step-reminder" + out.split("<step-reminder", 1)[1].split("</step-reminder>")[0] + "</step-reminder>"
    el = ET.fromstring(frag)
    for tag in ("objective", "output-format", "boundaries"):
        assert el.find(tag) is not None, f"Vertrag-Feld <{tag}> fehlt (keine Prosa-Kapselung)"


# --- AK-1: Reminder traegt einen identifizierenden Marker (erster-Step-Semantik) ---
def test_reminder_carries_target_orchestrator():
    out = _build()
    frag = "<step-reminder" + out.split("<step-reminder", 1)[1].split("</step-reminder>")[0] + "</step-reminder>"
    el = ET.fromstring(frag)
    assert el.get("target") == "_IDF_orchestrate"


# --- AK-3 (Robustheit, T5/Ring 2): escape gegen </& im Vertrags-Text -> kein XML-Bruch ---
# Named constants (Magic-String-Auslagerung): die EINE Sonderzeichen-Nutzlast wird genau
# einmal definiert, sodass der Roundtrip-Assert gegen DENSELBEN Quellwert prueft (kein
# zweites, unabhaengig getipptes Literal, das stumm driften koennte) — Living-Doc.
_RAW_OBJECTIVE_WITH_SPECIALS = "pruefe a < b && parse <tag> roh"  # rohe `<` UND `&` im Vertragstext
_EXPECTED_ESCAPED_TOKENS = ("&amp;&amp;", "&lt;tag&gt;")  # SOLL-Markup nach escape() von ` && ` / `<tag>`
_RAW_FORBIDDEN_TOKENS = ("<tag>", " && ")  # diese ROHEN Tokens duerfen NIE unescaped im Markup stehen


def test_reminder_escapes_special_chars_in_contract():
    """AK-3 Robustheit: Vertragsfelder mit XML-Sonderzeichen (`<`/`&`) duerfen das
    Envelope NICHT brechen. Der Kern muss alle interpolierten Vertragswerte escapen
    (xml.sax.saxutils.escape), sonst erzeugt ein `<` im objective-Text einen
    ParseError. Vor diesem Test wurde KEIN Sonderzeichen durch den Render-Pfad
    geschickt -> RED, falls escape je entfernt/umgangen wird.
    """
    from handover_reminder_core import build_reminder

    # Arrange: GENAU ein Vertragsfeld traegt rohe XML-Sonderzeichen (`<` und `&`).
    out = build_reminder(
        target_orchestrator="_IDF_orchestrate",
        next_step={
            "id": 8,
            "name": "validator",
            "objective": _RAW_OBJECTIVE_WITH_SPECIALS,
            "output_format": "validator.md",
            "boundaries": "kein Code, nur Read",
        },
        handoff_block="<<<HANDOFF-DATEN A->IDF>>>",
    )

    # Act: das (escaped) Envelope wieder einparsen.
    frag = "<step-reminder" + out.split("<step-reminder", 1)[1].split("</step-reminder>")[0] + "</step-reminder>"
    el = ET.fromstring(frag)  # ParseError => escape fehlt => AK-3-Robustheit verletzt (Assert 1)

    # Assert 2: Roundtrip ist verlustfrei — der Parser liefert GENAU den Eingabewert
    # zurueck (gegen dieselbe Konstante, nicht gegen eine Re-Typ-Kopie).
    assert el.find("objective").text == _RAW_OBJECTIVE_WITH_SPECIALS, (
        f"objective-Text muss nach dem XML-Roundtrip unveraendert sein (korrektes escape); "
        f"erwartet {_RAW_OBJECTIVE_WITH_SPECIALS!r}, geparst {el.find('objective').text!r}"
    )

    # Assert 3: jedes Sonderzeichen erscheint ESCAPED im Markup (sonst kein echtes escape).
    for token in _EXPECTED_ESCAPED_TOKENS:
        assert token in out, (
            f"escaptes Sonderzeichen {token!r} fehlt im Markup — escape() unvollstaendig (AK-3)"
        )

    # Assert 4: Negativ-Pin — KEIN rohes (unescaped) Sonderzeichen-Token im Markup. Faengt
    # sowohl fehlendes escape als auch einen Doppel-Render (escaped + roh) ab.
    for token in _RAW_FORBIDDEN_TOKENS:
        assert token not in out, (
            f"rohes (unescaped) Vertrags-Token {token!r} darf NICHT im Markup stehen "
            f"(escape unvollstaendig oder Doppel-Render-Leck)"
        )


# --- AK-12: kein Block-/Abort-Pfad im Kern (Reminder != Enforcement) ---
def test_core_has_no_block_path():
    src = (SCRIPT_DIR / "handover_reminder_core.py").read_text(encoding="utf-8")
    for forbidden in ("sys.exit", "continue\": False", "'continue': False", "raise SystemExit"):
        assert forbidden not in src, f"Block-/Abort-Pfad '{forbidden}' verletzt AK-12 (Reminder != Enforcement)"


if __name__ == "__main__":
    test_reminder_is_xml_wellformed()
    test_reminder_has_numbered_step_id()
    test_reminder_has_ack_field()
    test_reminder_discloses_exactly_one_step()
    test_reminder_sandwiches_handoff_block()
    test_reminder_contract_fields_are_tagged_not_prose()
    test_reminder_carries_target_orchestrator()
    test_reminder_escapes_special_chars_in_contract()
    test_core_has_no_block_path()
    print("=== 9/9 PASS ===")
