#!/usr/bin/env python3
"""
truth_keywords.py — thematische Schluesselwoerter pro Wahrheit (BL-309 R3 / BL-389).

User-Direktive 2026-06-16: "die Substanz waechst exponentiell (DCSRE 1000s Knoten); es muss
ermoeglicht werden, dass man die Sachen thematisch wiederfindet. Direkt suchbar muessen sie sein."
-> keywords[] ist Schema-v2-Feld; die Erfassung ist ONE-SHOT (waehrend der Migration), die SUCHE
(Embeddings/Index, BL-389) folgt spaeter. Capture-now / search-later.

First-cut (User: "first-cut Tool nicht ueber-praezisieren"): Frequenz-basiert, Stopwords raus,
>=3 Zeichen. Kein Stemming/NLP — reicht als thematischer Anker; Embeddings kommen in BL-389.
"""
from __future__ import annotations

import re
from collections import Counter

_WORD = re.compile(r"[A-Za-zÄÖÜäöüß][A-Za-zÄÖÜäöüß0-9_-]{2,}")

# Knappe DE+EN-Stopword-Liste (first-cut; bewusst klein gehalten).
_STOP: frozenset[str] = frozenset({
    # DE
    "der", "die", "das", "und", "oder", "ist", "sind", "ein", "eine", "einen", "einem", "einer",
    "den", "dem", "des", "fuer", "von", "mit", "auf", "aus", "bei", "nach", "wird", "werden",
    "wenn", "dann", "auch", "nicht", "noch", "schon", "aber", "als", "wie", "was", "wer", "wo",
    "diese", "dieser", "dieses", "man", "sich", "nur", "alle", "alles", "mehr", "sehr", "kann",
    "muss", "soll", "hat", "haben", "im", "in", "zu", "zum", "zur", "am", "an", "es", "er", "sie",
    # EN
    "the", "and", "for", "are", "was", "with", "that", "this", "from", "not", "but", "all", "can",
    "has", "have", "will", "should", "must", "via", "per",
})


def extract_keywords(text: str, top: int = 8, bigrams: bool = False) -> list[str]:
    """Top-N thematische Schluesselwoerter (frequenz-basiert, Stopwords/Kurzwoerter raus).

    Args:
        text:    Eingabe-Text (None wird als leerer String behandelt).
        top:     Maximale Anzahl Keywords im Output.
        bigrams: Wenn True, werden aufeinanderfolgende Wort-Paare (beide >=3 Zeichen,
                 beide nicht Stopword) als "word1_word2"-Tokens in den Counter gemischt.
    """
    raw_words = _WORD.findall(text or "")
    words = [w.lower() for w in raw_words]
    words = [w for w in words if w not in _STOP and len(w) >= 3]
    if not words:
        return []

    counter: Counter[str] = Counter(words)

    if bigrams:
        for a, b in zip(words, words[1:]):
            if a not in _STOP and b not in _STOP and len(a) >= 3 and len(b) >= 3:
                counter[f"{a}_{b}"] += 1

    # Deterministischer Tie-Breaker: absteigend nach Frequenz, dann alphabetisch.
    sorted_items = sorted(counter.items(), key=lambda x: (-x[1], x[0]))
    return [w for w, _ in sorted_items[:top]]
