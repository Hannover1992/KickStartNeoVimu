"""
BL-404 batch_1 RED Tests — AK-1, AK-2, AK-3
INV-PROCESS-STRICT-2 Doku-Anker + Vokabular + Report-Format in _I_verify.md.

RED-Phase: Diese Tests MUESSEN FAILEN, weil die Anker noch nicht in _I_verify.md stehen.
GREEN-Worker schreibt die Anker — separater Worker (RED != GREEN).

Datei: .claude/scripts/test_bl404_process_strict.py
Ziel-Doku: .claude/commands/_I_verify.md
"""

from pathlib import Path

# Pfad zur Zieldokument-Datei (relativ zum Repo-Root, absolut aufgeloest)
REPO_ROOT = Path(__file__).parent.parent  # .claude/scripts/ -> .claude/ -> repo root
VERIFY_MD = REPO_ROOT / "commands" / "_I_verify.md"


def _read_verify_md() -> str:
    """Liest _I_verify.md und gibt Inhalt zurueck. Fail-hard wenn nicht gefunden."""
    assert VERIFY_MD.exists(), f"_I_verify.md nicht gefunden unter: {VERIFY_MD}"
    return VERIFY_MD.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AK-1 — INV-PROCESS-STRICT-2 Invariante als benannter kanonischer Block
# ---------------------------------------------------------------------------

def test_ak1_invariante_benannt():
    """
    T-ak1-invariante: Die Invariante INV-PROCESS-STRICT-2 muss als
    benannter Anker in _I_verify.md vorhanden sein.
    GREEN-Worker: fuegt 'INV-PROCESS-STRICT-2' als Abschnitts-Marker ein.
    """
    content = _read_verify_md()
    assert "INV-PROCESS-STRICT-2" in content, (
        "FEHLENDER ANKER: 'INV-PROCESS-STRICT-2' nicht in _I_verify.md gefunden. "
        "GREEN-Worker muss INV-PROCESS-STRICT-2 als benannte Invariante (Refactor-Form-Carve-Out) "
        "im M2-Vertrag verankern."
    )


def test_ak1_token_korrektheits_failure():
    """
    T-ak1-tokens (Teil 1): Token 'Korrektheits-Failure' muss in _I_verify.md vorhanden sein.
    Beschreibt Kat.-A (Verhaltens-Korrektheit) als Kategorie-Bezeichnung.
    Alternativ-Token: 'behavior' als englischer Entsprechungsbegriff.
    """
    content = _read_verify_md()
    has_token = "Korrektheits-Failure" in content or "behavior" in content
    assert has_token, (
        "FEHLENDE TOKEN: Weder 'Korrektheits-Failure' noch 'behavior' in _I_verify.md. "
        "GREEN-Worker muss Kat.-A als 'Korrektheits-Failure/behavior'-Token benennen."
    )


def test_ak1_token_form_gekoppelt():
    """
    T-ak1-tokens (Teil 2): Token 'Form-gekoppelt' oder 'form-coupled' muss vorhanden sein.
    Beschreibt Kat.-B (Form-Kopplung) als Kategorie-Bezeichnung.
    """
    content = _read_verify_md()
    has_token = "Form-gekoppelt" in content or "form-coupled" in content
    assert has_token, (
        "FEHLENDE TOKEN: Weder 'Form-gekoppelt' noch 'form-coupled' in _I_verify.md. "
        "GREEN-Worker muss Kat.-B als 'Form-gekoppelt/form-coupled'-Token benennen."
    )


def test_ak1_token_im_zweifel():
    """
    T-ak1-tokens (Teil 3): Token 'im Zweifel' muss vorhanden sein.
    Beschreibt die Konservativitaets-Regel: im Zweifel -> Korrektheit (Kat. A), Code fixen.
    """
    content = _read_verify_md()
    assert "im Zweifel" in content, (
        "FEHLENDE TOKEN: 'im Zweifel' nicht in _I_verify.md. "
        "GREEN-Worker muss die Konservativitaets-Regel 'im Zweifel: Korrektheit (Kat. A) — "
        "Code fixen, Test unangetastet' als Anker eintragen."
    )


# ---------------------------------------------------------------------------
# AK-2 — Verhaltens-Assert-Vokabular explizit gelistet (Token-Set)
# ---------------------------------------------------------------------------

# Kat.-A-Marker (Verhaltens-Assertions) — mind. 6 erforderlich laut Spec AK-2
KAT_A_TOKENS = [
    "Output",
    "State",
    "Protokoll-Text",
    "Error-Code",
    "Object-Type-Vertrag",
    "Operations-Reihenfolge",
    "Exception-Art",
]

# Kat.-B-Marker (Form-Kopplung) — mind. 4 erforderlich laut Spec AK-2
KAT_B_TOKENS = [
    "alte-Klassen-Instanziierung",
    "Schwellwert",
    "umbenannter Symbol",
    "reorganisierte Struktur",
]


def test_ak2_kat_a_marker_subset():
    """
    T-ak2-vokabular (Kat. A): Alle 7 Kat.-A-Marker (Verhaltens-Assertions)
    muessen als Token-Set in _I_verify.md gelistet sein.
    GREEN-Worker: fuegt explizite Marker-Liste in den INV-PROCESS-STRICT-2-Block ein.
    """
    content = _read_verify_md()
    missing = [token for token in KAT_A_TOKENS if token not in content]
    assert not missing, (
        f"FEHLENDE KAT.-A-TOKEN in _I_verify.md: {missing}. "
        "GREEN-Worker muss alle Kat.-A-Marker (Output, State, Protokoll-Text, Error-Code, "
        "Object-Type-Vertrag, Operations-Reihenfolge, Exception-Art) explizit listen."
    )


def test_ak2_kat_b_marker_subset():
    """
    T-ak2-vokabular (Kat. B): Alle 4 Kat.-B-Marker (Form-Kopplung)
    muessen als Token-Set in _I_verify.md gelistet sein.
    GREEN-Worker: fuegt explizite Marker-Liste in den INV-PROCESS-STRICT-2-Block ein.
    """
    content = _read_verify_md()
    missing = [token for token in KAT_B_TOKENS if token not in content]
    assert not missing, (
        f"FEHLENDE KAT.-B-TOKEN in _I_verify.md: {missing}. "
        "GREEN-Worker muss alle Kat.-B-Marker (alte-Klassen-Instanziierung, Schwellwert, "
        "umbenannter Symbol, reorganisierte Struktur) explizit listen."
    )


# ---------------------------------------------------------------------------
# AK-3 — Per-Failure-Einzelmeldung als Vertrag-Anker (Report-Format)
# ---------------------------------------------------------------------------

def test_ak3_report_format_anker():
    """
    T-ak3-report (Format-Anker): Ein Report-Format-Anker fuer Per-Failure-Einzelmeldung
    muss in _I_verify.md vorhanden sein.
    Erwartete Felder: Test-Name, alte Form-Erwartung, neue Form-Erwartung, Begruendung.
    GREEN-Worker: fuegt das Report-Format als Vertrag-Anker ein.
    """
    content = _read_verify_md()
    # Mind. eines dieser Felder muss als Report-Format-Anker stehen
    report_field_tokens = [
        "Test-Name",
        "alte Form-Erwartung",
        "neue Form-Erwartung",
        "Begruendung",
        "Verhalten unverändert",
        "Verhalten unveraendert",
    ]
    found = [t for t in report_field_tokens if t in content]
    assert len(found) >= 2, (
        f"FEHLENDER REPORT-FORMAT-ANKER: Nur {len(found)} von erwarteten >=2 Feldern gefunden "
        f"({found}) in _I_verify.md. "
        "GREEN-Worker muss ein Per-Failure-Report-Format als Vertrag verankern "
        "(Felder: Test-Name, alte Form-Erwartung, neue, Begruendung 'Verhalten unverändert weil X')."
    )


def test_ak3_nie_still_nie_gebuendelt_anker():
    """
    T-ak3-report (Verbot-Anker): 'gebündelt' oder 'still' als Verbots-Anker muss vorhanden sein.
    Spec AK-3: 'Gebündelte oder stille Anpassung ist verboten.'
    GREEN-Worker: fuegt 'nie still, nie gebuendelt' oder aequivalenten Verbots-Anker ein.
    """
    content = _read_verify_md()
    # Suche nach Verbots-Formulierungen (Varianten toleriert wegen Umlaut-Encoding)
    verbots_tokens = [
        "gebündelt",
        "gebuendelt",
        "nie still",
        "still verboten",
        "gebundelt",
        "nie gebuendelt",
    ]
    found = any(t in content for t in verbots_tokens)
    assert found, (
        "FEHLENDER VERBOTS-ANKER: Kein 'gebündelt'/'nie still' Anker in _I_verify.md. "
        "GREEN-Worker muss 'gebündelte oder stille Anpassung ist verboten' als Vertrag-Anker eintragen."
    )
