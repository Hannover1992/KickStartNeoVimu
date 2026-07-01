"""
BL-308 RED-Tests: Twin-Diff Wiring in _I_verify.md

Diese Tests pruefen den INHALT von .claude/commands/_I_verify.md auf das Vorhandensein
von BL-308-spezifischen Marker-Strings, die AKTUELL FEHLEN -> RED-Phase.

GREEN muss folgende Marker in _I_verify.md einbauen:

AK-1 (Verifier-Branch): "twin_diff_gate"
    -> Referenz auf die Funktion twin_diff_gate aus twin_diff.py muss in _I_verify.md vorkommen.
    -> Alternativ akzeptierter Marker: "twin_diff_gate" (exakter Funktionsname).

AK-2 (Verdikt-Matrix): "Verdikt-Matrix" UND mindestens eines von {"conformant", "twin_available"}
    -> Eine Tabelle/Matrix mit den Spalten conformant/non-conformant x twin_available.
    -> Mindest-Pruefung: beide Schlagwoerter "Verdikt-Matrix" (oder "verdikt_matrix") + "twin_available" muessen vorkommen.

AK-12 (STATE-Block): "twin_conformance" oder "twin_diff_verdict"
    -> Entweder der STATE-Block-Name "twin_conformance" oder ein Verdikt-Feld "twin_diff_verdict"
       muss als dokumentiertes Feld in _I_verify.md vorkommen.

AK-6 (Proportionalitaet): ("twin_available" + "graceful") oder ("twin_available=false" + "PASS")
    -> Expliziter Hinweis dass twin_available=false -> graceful PASS (kein Block fuer Twin-lose Items).
    -> Mindest-Pruefung: "graceful" UND "twin_available" muessen beide vorkommen.

AK-14 (Abgrenzung): ("Konformanz" oder "Referenz-Konformanz") + ("Korrektheit" oder "TDD")
    -> Ein Abgrenzungs-Absatz der Twin-Diff (Referenz-Konformanz) vs TDD-Tests (Korrektheit)
       vs nachgelagertes Audit unterscheidet.
    -> Mindest-Pruefung: "Konformanz" (oder "Referenz-Konformanz") + "Korrektheit" muessen vorkommen.

WICHTIG FUER GREEN-Worker:
- Alle 5 Marker-Sets muessen in .claude/commands/_I_verify.md vorhanden sein.
- Die exakten Minimal-Strings sind:
    1. "twin_diff_gate"
    2. "Verdikt-Matrix" (oder "verdikt_matrix") + "twin_available"
    3. "twin_conformance"
    4. "graceful" + "twin_available"
    5. "Konformanz" + "Korrektheit"
"""

import pathlib
import pytest

# Absoluter Pfad zur Ziel-Datei
_IVERIFY_PATH = pathlib.Path(__file__).parent.parent / "commands" / "_I_verify.md"


@pytest.fixture(scope="module")
def iverify_content() -> str:
    """Liest _I_verify.md einmalig fuer alle Tests."""
    if not _IVERIFY_PATH.exists():
        pytest.fail(f"_I_verify.md nicht gefunden unter: {_IVERIFY_PATH}")
    return _IVERIFY_PATH.read_text(encoding="utf-8")


class TestBL308IVerifyWiring:
    """
    RED-Tests fuer BL-308 Sub-Batches PL2+PL5.
    Alle Tests MUESSEN jetzt fehlschlagen (Marker noch nicht in _I_verify.md).
    GREEN-Worker baut die Marker ein.
    """

    def test_iverify_references_twin_diff_gate(self, iverify_content: str) -> None:
        """
        AK-1 Verifier-Branch: _I_verify.md muss 'twin_diff_gate' enthalten.

        GREEN-Marker: "twin_diff_gate"
        Beleg: _I_verify muss einen Branch dokumentieren der vor BATCH_DONE
        twin_diff_gate(...) aus twin_diff.py konsultiert (Referenz auf Modul-Funktion).
        Exakter Marker-String: 'twin_diff_gate'
        """
        assert "twin_diff_gate" in iverify_content, (
            "AK-1 FEHLT: 'twin_diff_gate' nicht in _I_verify.md gefunden. "
            "GREEN muss einen Twin-Diff-Verifier-Branch dokumentieren der "
            "explizit auf die twin_diff_gate-Funktion (twin_diff.py) verweist."
        )

    def test_iverify_verdict_matrix_present(self, iverify_content: str) -> None:
        """
        AK-2 Verdikt-Matrix: _I_verify.md muss eine Verdikt-Matrix dokumentieren.

        GREEN-Marker: "Verdikt-Matrix" (oder "verdikt_matrix", case-insensitive check) + "twin_available"
        Beleg: Eine Matrix/Tabelle mit conformant/non-conformant x twin_available -> PASS/FAIL/graceful.
        Minimal: beide Schlagwoerter muessen im Dokument vorkommen.
        """
        content_lower = iverify_content.lower()
        has_matrix = "verdikt-matrix" in content_lower or "verdikt_matrix" in content_lower
        has_twin_available = "twin_available" in iverify_content

        assert has_matrix, (
            "AK-2 FEHLT: 'Verdikt-Matrix' (oder 'verdikt_matrix') nicht in _I_verify.md. "
            "GREEN muss eine 3-Wege-Verdikt-Matrix (IS-IDENTICAL/IS-ADAPTED/IS-NEW x "
            "twin_available -> PASS/FAIL/SKIPPED) dokumentieren."
        )
        assert has_twin_available, (
            "AK-2 FEHLT: 'twin_available' nicht in _I_verify.md. "
            "GREEN muss 'twin_available' als Verdikt-Matrix-Dimension benennen."
        )

    def test_iverify_twin_diff_state(self, iverify_content: str) -> None:
        """
        AK-12 STATE-Block: _I_verify.md muss twin_conformance STATE-Block dokumentieren.

        GREEN-Marker: "twin_conformance" (bevorzugt) oder "twin_diff_verdict"
        Beleg: AK-12 fordert einen parallelen twin_conformance-STATE-Block neben i_core_result
        mit Feldern anchor, classification, verdict (GREEN|BLOCK|SKIPPED).
        """
        has_twin_conformance = "twin_conformance" in iverify_content
        has_twin_diff_verdict = "twin_diff_verdict" in iverify_content

        assert has_twin_conformance or has_twin_diff_verdict, (
            "AK-12 FEHLT: Weder 'twin_conformance' noch 'twin_diff_verdict' in _I_verify.md. "
            "GREEN muss einen TWIN_DIFF-STATE-Block dokumentieren ('twin_conformance' als "
            "paralleler STATE-Block neben i_core_result, Felder: anchors, verdict)."
        )

    def test_iverify_proportionality_graceful(self, iverify_content: str) -> None:
        """
        AK-6 Proportionalitaet: _I_verify.md muss graceful-PASS fuer twin-lose Items dokumentieren.

        GREEN-Marker: "graceful" + "twin_available" beide vorhanden
        Beleg: AK-6 fordert dass twin_available=false -> graceful PASS (kein Block,
        kein extra Step, keine veraenderte Laufzeit gegenueber Pre-BL-308-Pfad).
        """
        has_graceful = "graceful" in iverify_content
        has_twin_available = "twin_available" in iverify_content

        assert has_graceful, (
            "AK-6 FEHLT: 'graceful' nicht in _I_verify.md. "
            "GREEN muss explizit dokumentieren dass twin_available=false einen "
            "graceful PASS ergibt (kein Block fuer Twin-lose Items, Proportionalitaet)."
        )
        assert has_twin_available, (
            "AK-6 FEHLT: 'twin_available' nicht in _I_verify.md. "
            "GREEN muss 'twin_available' als Proportionalitaets-Guard-Variable benennen."
        )

    def test_iverify_abgrenzung(self, iverify_content: str) -> None:
        """
        AK-14 Abgrenzung: _I_verify.md muss Abgrenzung Twin-Diff vs TDD vs Audit dokumentieren.

        GREEN-Marker: ("Konformanz" oder "Referenz-Konformanz") + "Korrektheit"
        Beleg: AK-14 fordert einen Abgrenzungs-Absatz der klarstellt:
        - Twin-Diff = Referenz-Konformanz (Datei-Vergleich, nicht Pattern-Conformance)
        - TDD-Tests = Korrektheit (Verhalten)
        - Nachgelagertes Audit = separater Prozess
        """
        has_konformanz = "Konformanz" in iverify_content or "Referenz-Konformanz" in iverify_content
        has_korrektheit = "Korrektheit" in iverify_content

        assert has_konformanz, (
            "AK-14 FEHLT: 'Konformanz' (oder 'Referenz-Konformanz') nicht in _I_verify.md. "
            "GREEN muss einen Abgrenzungs-Absatz einbauen der Twin-Diff als "
            "Referenz-Konformanz-Pruefung (vs TDD-Korrektheit, vs Audit) benennt."
        )
        assert has_korrektheit, (
            "AK-14 FEHLT: 'Korrektheit' nicht in _I_verify.md. "
            "GREEN muss 'Korrektheit' als Abgrenzungs-Begriff gegenueber Konformanz benennen "
            "(TDD-Tests pruefen Korrektheit, Twin-Diff prueft Konformanz)."
        )
