"""
BL-377 batch1 - RED-Worker: Content-Verify-Tests fuer _W_fetch.md
Prueft asymptotische Traversal-Logik (AK-1), CORE/BORDER-Klassifikation (AK-2),
Regression-Invarianten (AK-3).
ERWARTETER ZUSTAND: alle Tests RED (Features fehlen in _W_fetch.md v5.0)
"""

import re
from pathlib import Path

WFETCH_PATH = Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA/.claude/commands/_W_fetch.md")


def _read_wfetch() -> str:
    """Lese _W_fetch.md und gib Inhalt zurueck."""
    assert WFETCH_PATH.exists(), f"_W_fetch.md nicht gefunden: {WFETCH_PATH}"
    return WFETCH_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AK-1: Loop-until-dry + SAFETY_CAP (asymptotische Termination)
# ---------------------------------------------------------------------------

def test_loop_until_dry_present():
    """
    AK-1: Stufe 3 GRAPH-TRAVERSAL muss loop-until-dry-Logik enthalten.
    Erwartete Signale: 'delta_core' (Haupt-Terminations-Signal)
    UND 'SAFETY_CAP' (absoluter Cap z.B. 6).
    Aktuell: nur fixer 'max 3 hops' ohne delta-Terminierung → RED.
    """
    content = _read_wfetch()

    # delta_core ist das Haupt-Terminations-Signal (loop-until-dry)
    has_delta_core = bool(re.search(r"delta_core", content, re.IGNORECASE))
    # Alternativform: "loop-until-dry" oder "delta==0"
    has_loop_until_dry_alt = bool(
        re.search(r"loop[- ]until[- ]dry", content, re.IGNORECASE)
        or re.search(r"delta\s*==\s*0", content)
    )

    # SAFETY_CAP als absoluter Sicherheits-Cap (z.B. SAFETY_CAP=6)
    has_safety_cap = bool(re.search(r"SAFETY_CAP", content))

    assert has_delta_core or has_loop_until_dry_alt, (
        "AK-1 FEHLT: Keine loop-until-dry-Terminations-Logik in Stufe 3 gefunden. "
        "Erwartet: 'delta_core' (oder 'loop-until-dry'/'delta==0') als Terminations-Signal. "
        "Aktuell: nur fixer 'Max 3 Hops' ohne asymptotische Konvergenz."
    )

    assert has_safety_cap, (
        "AK-1 FEHLT: Kein 'SAFETY_CAP' in _W_fetch.md. "
        "Erwartet: absoluter Safety-Cap (z.B. SAFETY_CAP=6) als Backup-Termination. "
        "Aktuell: kein SAFETY_CAP definiert."
    )


# ---------------------------------------------------------------------------
# AK-1b: Fixer 3-Hop-Cap als alleinige Terminierung muss ersetzt sein
# ---------------------------------------------------------------------------

def test_fixed_3hop_cap_removed():
    """
    AK-1b: Der harte 'Max 3 Hops' als ALLEINIGE Termination ist ersetzt durch
    asymptotische delta_core-Termination. Der '3 Hops'-Text darf als historischer
    Kontext / Safety-Cap-Erwaehnung existieren, aber delta_core MUSS als
    Haupt-Signal praesentiert werden.
    Aktuell: delta_core fehlt komplett → RED.
    """
    content = _read_wfetch()

    # delta_core muss als Hauptsignal vorhanden sein
    has_delta_core = bool(re.search(r"delta_core", content, re.IGNORECASE))

    assert has_delta_core, (
        "AK-1b FEHLT: 'delta_core' nicht in _W_fetch.md. "
        "Die asymptotische Termination (delta_core als Hauptsignal) fehlt vollstaendig. "
        "Aktuell: Einzige Terminierung ist 'Max 3 Hops' (fix, nicht asymptotisch). "
        "Erwartet: delta_core-Logik dominiert; '3 Hops' darf als Safety-Cap bleiben."
    )


# ---------------------------------------------------------------------------
# AK-2: CORE/BORDER-Klassifikation
# ---------------------------------------------------------------------------

def test_core_border_classification():
    """
    AK-2: _W_fetch.md muss CORE/BORDER-Klassifikation enthalten.
    CORE = Grounding-Treiber / Expansion (tiefere Traversal-Prioritaet).
    BORDER = demoted / Anhang (flachere Behandlung, nicht geloescht).
    Aktuell: keine CORE/BORDER-Unterscheidung → RED.
    """
    content = _read_wfetch()

    has_core = bool(re.search(r"\bCORE\b", content))
    has_border = bool(re.search(r"\bBORDER\b", content))

    # CORE muss mit Grounding-/Expansion-Semantik verknuepft sein
    has_core_grounding = bool(
        re.search(r"CORE.{0,200}(grounding|expansion|Grounding|Expansion)", content, re.DOTALL)
        or re.search(r"(grounding|expansion|Grounding|Expansion).{0,200}CORE", content, re.DOTALL)
    )

    # BORDER muss mit demoted-/Anhang-Semantik verknuepft sein
    has_border_demoted = bool(
        re.search(r"BORDER.{0,200}(demoted|Anhang|appendix)", content, re.DOTALL | re.IGNORECASE)
        or re.search(r"(demoted|Anhang|appendix).{0,200}BORDER", content, re.DOTALL | re.IGNORECASE)
    )

    assert has_core, (
        "AK-2 FEHLT: Kein 'CORE'-Marker in _W_fetch.md. "
        "Erwartet: CORE-Klassifikation fuer Grounding-Treiber-Knoten."
    )

    assert has_border, (
        "AK-2 FEHLT: Kein 'BORDER'-Marker in _W_fetch.md. "
        "Erwartet: BORDER-Klassifikation fuer demoted/Anhang-Knoten."
    )

    assert has_core_grounding, (
        "AK-2 FEHLT: CORE ohne Grounding/Expansion-Semantik. "
        "Erwartet: CORE-Knoten steuern Grounding/Expansion der Traversal."
    )

    assert has_border_demoted, (
        "AK-2 FEHLT: BORDER ohne demoted/Anhang-Semantik. "
        "Erwartet: BORDER-Knoten sind demoted oder als Anhang behandelt."
    )


# ---------------------------------------------------------------------------
# AK-3: Regression-Invarianten dokumentiert
# ---------------------------------------------------------------------------

def test_regression_invariants_documented():
    """
    AK-3: Regression-Invarianten muessen textlich dokumentiert sein:
    1. 'visited' (Cache bleibt, kein Re-Visit) — vorhanden als 'Visited-Cache', aber
       INV-Formulierung fuer Regression fehlt.
    2. BORDER-Knoten werden NIE geloescht (nur demoted).
    3. Grounding-only-deepen-Hinweis (CORE-Knoten werden vertieft, BORDER nicht).
    Aktuell: INV-Dokumentation fehlt → RED.
    """
    content = _read_wfetch()

    # INV-1: visited-Cache Invariante (explizite INV-Formulierung erwartet)
    has_visited_inv = bool(
        re.search(r"visited.{0,100}(bleibt|cache|invariant|INV)", content, re.IGNORECASE | re.DOTALL)
        or re.search(r"(INV|invariant).{0,200}visited", content, re.IGNORECASE | re.DOTALL)
    )

    # INV-2: BORDER nie geloescht
    has_border_never_deleted = bool(
        re.search(r"BORDER.{0,200}(nie|never|nicht geloescht|not deleted)", content, re.IGNORECASE | re.DOTALL)
        or re.search(r"(nie|never|nicht geloescht|not deleted).{0,200}BORDER", content, re.IGNORECASE | re.DOTALL)
    )

    # INV-3: Grounding-only-deepen (CORE vertieft, BORDER nicht)
    has_grounding_only_deepen = bool(
        re.search(r"grounding.{0,200}(only|deepen|vertieft)", content, re.IGNORECASE | re.DOTALL)
        or re.search(r"(only|deepen|vertieft).{0,200}grounding", content, re.IGNORECASE | re.DOTALL)
    )

    assert has_visited_inv, (
        "AK-3 FEHLT: Visited-Cache-Invariante nicht als INV dokumentiert. "
        "Erwartet: explizite Formulierung dass visited-Cache erhalten bleibt (kein Re-Visit). "
        "Aktuell: 'Visited-Cache' erwaehnt (Z427), aber keine INV-Formulierung."
    )

    assert has_border_never_deleted, (
        "AK-3 FEHLT: Keine 'BORDER nie geloescht'-Invariante in _W_fetch.md. "
        "Erwartet: BORDER-Knoten werden demoted aber NIE aus dem Graph entfernt."
    )

    assert has_grounding_only_deepen, (
        "AK-3 FEHLT: Kein 'Grounding-only-deepen'-Hinweis in _W_fetch.md. "
        "Erwartet: CORE-Knoten werden vertieft (deepen), BORDER nicht."
    )
