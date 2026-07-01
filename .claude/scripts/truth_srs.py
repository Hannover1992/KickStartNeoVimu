#!/usr/bin/env python3
"""
truth_srs.py — SRS als generierte VIEW ueber atomare Wahrheiten (BL-384 Rebuildability-LAW).

User-Direktive 2026-06-16: SRS wird heute aus dem Model berechnet (w_offen/w_total); Parking-Lots
verweisen auf Wahrheiten dort. Rebuildability-LAW (Event-Sourcing-Lektion): SRS ist KEINE eigene
Quelle, sondern eine FUNKTION ueber den Wahrheiten - rebuildbar, nie autoritativ gespeichert.

Dieser Generator ist der Beweis-of-Concept fuer BL-384: ein abgeleitetes Artefakt (SRS) als
deterministische View ueber dem Truth-Substrat. K-Score/Gap/arc42 folgen demselben Muster.

SRS-Epistemik (0-100, hoeher = unreifer/offener): w_open / w_total * 100.
  open  = lifecycle 'asserted' (noch nicht gereift/geprueft) ODER typ 'FRAGE' (inhaerent offen)
  settled = lifecycle reviewed|experiment_proven|contradicted|retracted
READ-ONLY: reine Berechnung, keine Mutation.
"""
from __future__ import annotations

from collections import Counter

_OPEN_LIFECYCLE = {"asserted"}
# settled = alles andere Gueltige: reviewed | experiment_proven | contradicted | retracted


def is_open(truth: dict) -> bool:
    """Eine Wahrheit ist 'offen' (unreif) wenn sie noch nicht gereift ist oder eine FRAGE ist."""
    if str(truth.get("typ")) == "FRAGE":
        return True
    return str(truth.get("lifecycle", "asserted")) in _OPEN_LIFECYCLE


def srs_from_truths(truths: list[dict]) -> dict:
    """SRS-View ueber einer Menge Wahrheiten. Rebuildbar aus dem Substrat (kein eigener Speicher)."""
    total = len(truths)
    if total == 0:
        return {"w_total": 0, "w_open": 0, "srs": 0, "by_lifecycle": {}, "by_typ": {}}
    w_open = sum(1 for t in truths if is_open(t))
    return {
        "w_total": total,
        "w_open": w_open,
        "srs": round(100 * w_open / total),
        "by_lifecycle": dict(Counter(str(t.get("lifecycle", "asserted")) for t in truths)),
        "by_typ": dict(Counter(str(t.get("typ", "?")) for t in truths)),
    }
