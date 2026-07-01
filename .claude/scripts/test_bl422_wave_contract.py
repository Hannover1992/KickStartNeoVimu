"""
BL-422 AK-2(a) RED Tests — Wave Contract in _A_orchestrate.md
RED-Worker: NUR Tests, KEINE Implementierung. _A_orchestrate.md wird NICHT veraendert.

Getestet wird: ob _A_orchestrate.md einen expliziten benannten Wellen-Spawn-Kontrakt
fuer die A-Pipeline-Wellen enthaelt (Explorer -> Drafter -> Synthese mit TaskCreate/blockedBy-DAG).

Erwartetes Ergebnis: test_a_orchestrate_has_wave_spawn_contract FAILT (Kontrakt fehlt).
                     test_a_orchestrate_wave_forbids_anonymous_collapse FAILT (Verbot fehlt).
                     test_a_orchestrate_wave_syncdrive_fallback kann PASSEN (SYNC-DRIVE existiert).
"""

import re
import pathlib
import pytest

A_ORCHESTRATE_PATH = pathlib.Path(
    "C:/Users/hanno/RiderProjects/OmniCommand-wtA/.claude/commands/_A_orchestrate.md"
)


def _read_orchestrate() -> str:
    assert A_ORCHESTRATE_PATH.exists(), (
        f"_A_orchestrate.md nicht gefunden: {A_ORCHESTRATE_PATH}"
    )
    return A_ORCHESTRATE_PATH.read_text(encoding="utf-8")


class TestBl422WaveContract:
    """
    BL-422 AK-2(a): Expliziter benannter Wellen-Spawn-Kontrakt in _A_orchestrate.md.

    AK-2 Anforderung: Der POSITIVE Wellen-Spawn-Kontrakt MUSS im Skill stehen —
    nicht nur in Doku. Konkret: 5 Explorer -> 3 Drafter -> 1 Synthese mit
    TaskCreate(blockedBy)-DAG und explizit benannten Teammates.
    """

    def test_a_orchestrate_has_wave_spawn_contract(self):
        """
        _A_orchestrate.md enthaelt einen expliziten benannten Wellen-Spawn-Kontrakt.

        Prueft ob ALLE folgenden Elemente vorhanden sind:
        - "BL-422" (Referenz auf dieses Feature)
        - "Explorer" (erste Welle: 5 Explorer-Agents)
        - "Drafter" (zweite Welle: 3 Drafter-Agents)
        - "Synthese" (dritte Welle: 1 Synthese-Agent)
        - "TaskCreate" (DAG-Bau via TaskCreate)
        - "blockedBy" ODER "blocked_by" ODER "depends_on" (DAG-Abhaengigkeiten)
        - "benannt" ODER "named" ODER "team_name" (explizit benannte Teammates)

        Fehlt jetzt -> RED (Kontrakt noch nicht im Skill).
        """
        content = _read_orchestrate()

        missing = []

        if "BL-422" not in content:
            missing.append("BL-422 (Referenz auf Wellen-Kontrakt-Feature)")

        if not re.search(r"Explorer", content):
            missing.append("Explorer (erste Welle: 5 Explorer-Agents)")

        if not re.search(r"Drafter", content):
            missing.append("Drafter (zweite Welle: 3 Drafter-Agents)")

        if not re.search(r"Synthese", content):
            missing.append("Synthese (dritte Welle: 1 Synthese-Agent)")

        if "TaskCreate" not in content:
            missing.append("TaskCreate (DAG-Bau)")

        if not re.search(r"blockedBy|blocked_by|depends_on", content):
            missing.append("blockedBy/blocked_by/depends_on (DAG-Abhaengigkeiten)")

        # "benannt"/"named"/"team_name" — team_name existiert bereits im Spawn-Pattern,
        # aber NICHT im Kontext eines expliziten Wellen-Kontrakts mit BL-422-Referenz.
        # Dieser Check prueft ob es im Wellen-Kontrakt-Kontext steht (BL-422-Abschnitt).
        bl422_section = _extract_bl422_section(content)
        if bl422_section is None:
            missing.append(
                "BL-422-Abschnitt (eigener Wellen-Kontrakt-Block, nicht nur globale Referenz)"
            )
        else:
            if not re.search(r"benannt|named|team_name", bl422_section):
                missing.append(
                    "benannt/named/team_name im BL-422-Kontrakt-Kontext"
                )

        assert not missing, (
            "Wellen-Spawn-Kontrakt FEHLT in _A_orchestrate.md.\n"
            "Fehlende Elemente:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )

    def test_a_orchestrate_wave_forbids_anonymous_collapse(self):
        """
        Der Wellen-Kontrakt in _A_orchestrate.md benennt explizit das Verbot
        des Einzel-anonymen-Sub-Agent-Kollaps.

        Prueft ob im Wellen-Kontrakt-Kontext (BL-422-Abschnitt) mindestens eines
        dieser Signalwoerter vorkommt:
        - "anonym" / "anonymous"
        - "Einzel" (Einzel-Agent-Kollaps)
        - "Mega-Worker" (INV-AO-CALLER-Verweis)
        - "Kollaps"

        UND ein Verweis auf INV-PM-5 ODER INV-AO-CALLER.

        Fehlt jetzt -> RED (Verbot noch nicht explizit im Skill dokumentiert).
        """
        content = _read_orchestrate()

        bl422_section = _extract_bl422_section(content)

        assert bl422_section is not None, (
            "BL-422-Abschnitt nicht gefunden in _A_orchestrate.md. "
            "Wellen-Kontrakt-Block muss mit '# BL-422' oder '## BL-422' o.ae. beginnen, "
            "ODER BL-422 muss im Wellen-Kontrakt-Kontext eine eigene Section haben."
        )

        has_collapse_keyword = bool(
            re.search(r"anonym|anonymous|Einzel|Mega-Worker|Kollaps", bl422_section)
        )
        has_inv_reference = bool(
            re.search(r"INV-PM-5|INV-AO-CALLER", bl422_section)
        )

        missing = []
        if not has_collapse_keyword:
            missing.append(
                "Verbot-Signalwort (anonym/anonymous/Einzel/Mega-Worker/Kollaps) "
                "im BL-422-Abschnitt"
            )
        if not has_inv_reference:
            missing.append(
                "INV-Verweis (INV-PM-5 oder INV-AO-CALLER) im BL-422-Abschnitt"
            )

        assert not missing, (
            "Wellen-Kontrakt in _A_orchestrate.md benennt das Verbot des "
            "anonymen Einzel-Kollaps NICHT explizit.\n"
            "Fehlende Elemente:\n"
            + "\n".join(f"  - {m}" for m in missing)
        )

    def test_a_orchestrate_wave_syncdrive_fallback(self):
        """
        Charakterisierungs-Test (soll nach GREEN gruen bleiben):
        Der Wellen-Kontrakt (oder die SYNC-DRIVE-DOKTRIN) erwaehnt den SYNC-DRIVE-PLAIN-
        Fallback fuer geladene Sessions.

        SYNC-DRIVE-DOKTRIN existiert bereits in _A_orchestrate.md (Zeilen 327-346).
        Dieser Test prueft ob "SYNC-DRIVE" oder "PLAIN" im Dokument vorkommt.

        Kann jetzt schon PASSEN (SYNC-DRIVE existiert). Soll nach GREEN weiter gruen sein,
        wenn der Kontrakt explizit darauf verweist.
        """
        content = _read_orchestrate()

        has_sync_drive = bool(re.search(r"SYNC-DRIVE|PLAIN", content))

        assert has_sync_drive, (
            "SYNC-DRIVE oder PLAIN nicht in _A_orchestrate.md gefunden. "
            "Die SYNC-DRIVE-DOKTRIN (Fallback fuer geladene Sessions) fehlt."
        )


def _extract_bl422_section(content: str) -> str | None:
    """
    Extrahiert den BL-422-spezifischen Wellen-Kontrakt-Abschnitt aus dem Dokument.

    Sucht nach einem Abschnitt der explizit BL-422 erwaehnt und den Wellen-Kontrakt
    beschreibt. Gibt None zurueck wenn kein solcher Abschnitt existiert.

    Strategie:
    1. Suche nach Markdown-Section-Header mit BL-422 (## BL-422 ..., # BL-422 ...)
    2. Alternativ: suche nach einem Absatz/Block der sowohl BL-422 als auch
       "Wellen" oder "Explorer" oder "Drafter" enthaelt.
    """
    # Strategie 1: Markdown-Section-Header mit BL-422
    header_match = re.search(
        r"^#{1,4}\s+.*BL-422.*$",
        content,
        re.MULTILINE | re.IGNORECASE
    )
    if header_match:
        start = header_match.start()
        # Naechster gleichwertiger oder hoeherer Header beendet den Abschnitt
        header_level = len(re.match(r"(#+)", header_match.group()).group(1))
        end_pattern = rf"^#{{1,{header_level}}}\s"
        end_match = re.search(end_pattern, content[header_match.end():], re.MULTILINE)
        end = header_match.end() + end_match.start() if end_match else len(content)
        return content[start:end]

    # Strategie 2: Suche nach Absatz/Block mit BL-422 + Wellen-Kontext
    # Teile den Content in Paragraphen (doppelte Newlines)
    paragraphs = re.split(r"\n{2,}", content)
    wave_context_keywords = ["Wellen", "Explorer", "Drafter", "Synthese", "wave"]
    for para in paragraphs:
        if "BL-422" in para and any(kw in para for kw in wave_context_keywords):
            return para

    return None
