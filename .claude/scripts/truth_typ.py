#!/usr/bin/env python3
"""
truth_typ.py — typ-Erkennung FRAGE/SOLL/FESTSTELLUNG (BL-309, one-shot Capture).

User-Direktive 2026-06-16: Wahrheiten "haben auch ihre Kategorien". typ ist ein Schema-Feld
(FESTSTELLUNG|SOLL|FRAGE) das u.a. SRS treibt (FRAGE = inhaerent offen). Der Atomizer defaultete
alle Legacy-Knoten auf FESTSTELLUNG; diese Heuristik hebt klare FRAGE/SOLL heraus.

KONSERVATIV (first-cut, low-false-positive, User: "first-cut nicht ueber-praezisieren"):
  FRAGE  = explizites '?' ODER offene-Frage-Marker (offene Frage/ungeklaert/TBD/open question).
  SOLL   = starke Normativ-Marker (MUSS/SOLL/PFLICHT gross-als-Wort ODER shall/erforderlich/verpflichtend).
  sonst  = FESTSTELLUNG (faktischer Default).
"""
from __future__ import annotations

import re

_FRAGE = re.compile(r"\?|offene?\s+frage|ungekl[aä]rt|\bTBD\b|open question|fraglich", re.IGNORECASE)
# SOLL: GROSS-geschriebene Normativ-Woerter (MUSS/SOLL/PFLICHT) ohne IGNORECASE (vermeidet das
# allgegenwaertige kleine "muss/soll" in deskriptiver Prosa) + eindeutige Marker mit IGNORECASE.
_SOLL_STRONG = re.compile(r"\b(MUSS|SOLL|PFLICHT|MUSS_|SOLL_)\b")
_SOLL_WORD = re.compile(r"\b(shall|erforderlich|verpflichtend|mandatory)\b", re.IGNORECASE)


def detect_typ(heading: str, text: str) -> str:
    blob = f"{heading}\n{text}"
    if _FRAGE.search(blob):
        return "FRAGE"
    if _SOLL_STRONG.search(blob) or _SOLL_WORD.search(blob):
        return "SOLL"
    return "FESTSTELLUNG"
