#!/usr/bin/env python3
"""
truth_lifecycle.py — Reife-Ableitung: status/truth_grade -> lifecycle (BL-309 R2).

User-Direktive 2026-06-16: "Wahrheiten haben ihren Lebenszyklus: am Anfang behauptet, dann
gereift/gecheckt/durch Experimente bewiesen. Sie haben Kategorien - Information ueber die Reife,
die Badges. Super wichtig!" -> der lifecycle (Schema v2 R2) wird aus den vorhandenen Signalen
abgeleitet:
  truth_grade (gegen-Code-Signal, am staerksten) > status (epistemischer Zustand) > Default asserted.

Unbekannt/fehlend -> 'asserted' + needs_hil_review (die finale Status-Mapping-Tabelle ist ein
Phase-2-HiL-HARD-Gate; diese Ableitung ist die best-effort-Vorlage, die HiL bestaetigt/korrigiert).
"""
from __future__ import annotations

from typing import Optional

# Epistemischer Status -> Lebenszyklus-Stufe.
STATUS_TO_LIFECYCLE: dict[str, str] = {
    "OFFEN": "asserted",
    "UNGRADED": "asserted",
    "EXPERIMENT_PROVABLE": "reviewed",
    "BESTAETIGT": "reviewed",
    "AKTIV_BESTAETIGT": "reviewed",
    "INTEGRATED": "reviewed",
    "WIDERLEGT": "contradicted",
    "RETRACTED": "retracted",
    "VERALTET_DATEI_GELOESCHT": "retracted",
}

# truth_grade ist das staerkste Reife-Signal (gegen Code geprueft) -> ueberschreibt status.
GRADE_TO_LIFECYCLE: dict[str, Optional[str]] = {
    "code_verified": "experiment_proven",   # gegen Code verifiziert = bewiesen
    "code_contradicted": "contradicted",
    "vault_hypothesis": None,                # kein eigenes Reife-Signal -> status entscheidet
}


def map_lifecycle(status: Optional[str] = None, truth_grade: Optional[str] = None) -> tuple[str, bool]:
    """Leitet (lifecycle, needs_hil_review) aus truth_grade + status ab.

    Praezedenz: truth_grade (code_verified/contradicted) > status-Map > Default asserted+HiL-Flag.
    """
    g = GRADE_TO_LIFECYCLE.get(str(truth_grade)) if truth_grade is not None else None
    if g:
        return g, False
    if status is not None and str(status) in STATUS_TO_LIFECYCLE:
        return STATUS_TO_LIFECYCLE[str(status)], False
    # unbekannt/fehlend: konservativ asserted, aber zur HiL-Review markiert
    return "asserted", True
