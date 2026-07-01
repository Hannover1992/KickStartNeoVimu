#!/usr/bin/env python3
"""
truth_gap.py — Gap-View ueber Wahrheiten (BL-384, komplettiert das Derived-View-Trio).

SRS = Score (wie offen), Graph = Struktur (wie verbunden), Gap = die LISTE der offenen Items
(was konkret noch zu schliessen ist). Eine generierte View ueber den Wahrheiten (Rebuildability-LAW).

Die ACTIONABLE Gap (nicht das triviale 'alles-asserted'): explizite FRAGE-Knoten + niedrig-gradige
(vault_hypothesis) — das ist die Arbeits-Queue fuer SC/Scientific-Mode (BL-325). READ-ONLY.
"""
from __future__ import annotations

from collections import Counter

import truth_srs as tsrs


def _ns(truth: dict) -> str:
    tid = str(truth.get("id", ""))
    return tid.rsplit(".", 1)[0] if "." in tid else (truth.get("local_id") or "?")


def open_truths(truths: list[dict]) -> list[dict]:
    """Epistemisch offene Wahrheiten (lifecycle asserted ODER typ FRAGE)."""
    return [t for t in truths if tsrs.is_open(t)]


def actionable_gap(truths: list[dict]) -> list[dict]:
    """Die KONKRET zu schliessende Gap: explizite FRAGE-Knoten (nicht das triviale alles-asserted)."""
    return [t for t in truths if str(t.get("typ")) == "FRAGE"]


def gap_report(truths: list[dict]) -> dict:
    total = len(truths)
    op = open_truths(truths)
    questions = actionable_gap(truths)
    return {
        "total": total,
        "open": len(op),
        "open_questions": len(questions),  # die actionable Gap (FRAGE)
        "vault_hypotheses": sum(1 for t in truths if str(t.get("truth_grade")) == "vault_hypothesis"),
        "questions_by_bl": dict(Counter(_ns(t) for t in questions).most_common(15)),
    }
