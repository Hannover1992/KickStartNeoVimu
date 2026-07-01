#!/usr/bin/env python3
"""BL-312 AK-8 — W-Anknuepfung-light fuer late PL-Items ohne w_refs.

Zweck (gegen srs=100-no_truth_refs-Kollaps):
  Ein late PL-Item, das spaet (Trickle / Entry-3) entsteht, hat oft KEINE w_refs.
  Ohne Truth-Refs faellt es in die `no_truth_refs`-Falle (srs=100) und verzerrt
  ALLE SRS-gesteuerten Routing-Entscheidungen. Dieses Modul knuepft solche Items
  VORGELAGERT an Model-W{n}-Knoten — leichtgewichtig, ohne Graph-Traversal.

  Es ist der **Spiegel der _W_fetch fuzzy_match_score-Logik** (Token-Overlap als
  Primaer + difflib.SequenceMatcher-Fallback, `max()` der beiden), aber reduziert
  auf das Noetige: kein Graph-Walk, kein FS-Zugriff, kein Tag-Co-Occurrence.

Vertrag (Blueprint SB-srseval S1):
  match_item_to_model(item_text, model_w_nodes, threshold=0.5) -> list[dict]
    Pro W{n}-Node (dict mit id + status + title|desc) wird ein fuzzy_match_score
    in [0.0, 1.0] berechnet. Ein w_ref hat die Form:
        {"id": str, "status": str, "score": float, "source": "W_fetch-light"}
    Rueckgabe: nach score DESC sortiert (stabil), gecappt auf top-5.

  Relevanz-Regel (BL-312-Lead-Korrektur 2026-06-12 — NUR threshold-Klarer):
    - Es werden NUR die Knoten als w_refs gefuehrt, die den `threshold` klaren
      (die RELEVANTEN Wahrheiten, an die das Item tatsaechlich gekoppelt ist) —
      NICHT das ganze Model. Jeder mit seinem eigenen score, top-5 gecappt.
    - Klart KEIN Knoten den threshold (echtes Unbekanntes) -> [] (degraded, KEIN
      Crash). Der no_truth_refs-Pfad bleibt dann KORREKT bestehen.
    - WICHTIG (kein Dilutions-Defekt): unverwandte Knoten werden NICHT mit-angeknuepft.
      Ein Item, das nur an eine OFFEN-Wahrheit koppelt, ergibt srs=100 — das ist
      KORREKTE genuine Unsicherheit, NICHT der no_truth_refs-Bug. Der Bug ist das
      FEHLEN von refs (breakdown leer), nicht ein hoher srs-Wert. W_fetch-light hebt
      'blind' (no_truth_refs) -> 'gekoppelt'; der srs spiegelt dann den ECHTEN status-
      Mix der GEKOPPELTEN Wahrheiten (BL-255 AK-S3: 'blind' != 'unsicher').

Eigenschaften:
  - Rein: kein FS-Write, kein I/O.
  - Deterministisch: keine Abhaengigkeit von Python-hash/set-Iterations-Reihenfolge;
    stabile Sortierung (score DESC, dann id ASC als Tie-Breaker).
  - Aendert die SRS-FORMEL NICHT — W_fetch-light ist VORGELAGERT.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher

# Stopwort-tolerant: haeufige (deutsche + englische) Fuellwoerter werden vor dem
# Overlap entfernt, damit sie den Score nicht aufblaehen. Bewusst klein gehalten.
_STOPWORDS = frozenset({
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einen", "einem",
    "und", "oder", "im", "in", "an", "am", "zum", "zur", "zu", "auf", "fuer",
    "von", "mit", "bei", "the", "a", "an", "of", "to", "in", "on", "for", "and",
    "or", "at", "by", "is", "are", "be",
})

# Wort-Split: alphanumerische Tokens; CamelCase wird zusaetzlich an Grossbuchstaben
# zerlegt (Spiegel _W_fetch STUFE 2 A), Underscore/Hyphen sind ohnehin Trenner.
_WORD_RE = re.compile(r"[A-Za-z0-9]+")
_CAMEL_RE = re.compile(r"[A-Z]?[a-z0-9]+|[A-Z]+(?![a-z])")


def _tokenize(text: str) -> frozenset[str]:
    """Lowercase Wort-Split (CamelCase-aware, stopwort-tolerant) -> Token-Menge."""
    if not text:
        return frozenset()
    tokens: set[str] = set()
    for raw in _WORD_RE.findall(text):
        # CamelCase weiter zerlegen (z.B. "DispatcherWorker" -> dispatcher, worker)
        for part in _CAMEL_RE.findall(raw):
            t = part.lower()
            if t and t not in _STOPWORDS:
                tokens.add(t)
    return frozenset(tokens)


def fuzzy_match_score(item_tokens: frozenset[str], node_text: str) -> float:
    """Token-Overlap (Primaer) kombiniert mit difflib-SequenceMatcher (Fallback).

    Spiegel der _W_fetch-Logik:
      A. Token-Overlap = |item ∩ node| / min(|item|, |node|)   (0.0 - 1.0)
      B. SequenceMatcher.ratio() ueber die sortierten Token-Strings (Tippfehler-tolerant)
      C. Final = max(A, B)
    """
    node_tokens = _tokenize(node_text)
    if not item_tokens or not node_tokens:
        return 0.0

    inter = item_tokens & node_tokens
    denom = min(len(item_tokens), len(node_tokens))
    overlap = (len(inter) / denom) if denom else 0.0

    # Deterministischer Fallback: sortierte Token-Strings -> kein set-Iter-Nondeterminismus.
    item_str = " ".join(sorted(item_tokens))
    node_str = " ".join(sorted(node_tokens))
    seq = SequenceMatcher(None, item_str, node_str).ratio()

    return max(overlap, seq)


def match_item_to_model(item_text, model_w_nodes, threshold: float = 0.5):
    """Knuepft ein PL-Item-Text an passende Model-W{n}-Knoten.

    Args:
        item_text: Roh-Text des PL-Items (W/AK/Beschreibung).
        model_w_nodes: Iterable von dicts; pro Node {id, status, title|desc}.
        threshold: Minimaler fuzzy_match_score fuer einen Treffer (Default 0.5).

    Returns:
        list[dict]: w_refs {id, status, score, source:"W_fetch-light"},
        nach score DESC (Tie-Break id ASC) sortiert, top-5 gecappt.
        Leer wenn KEIN Knoten den threshold klart (degraded, kein Crash).
    """
    if not item_text or not model_w_nodes:
        return []

    item_tokens = _tokenize(item_text)
    if not item_tokens:
        return []

    # Schritt 1: jeden Knoten scoren (deterministisch, keine set-Iter-Abhaengigkeit).
    scored = []
    for node in model_w_nodes:
        if not isinstance(node, dict):
            continue
        node_id = node.get("id")
        if not node_id:
            continue
        node_text = node.get("title") or node.get("desc") or ""
        score = fuzzy_match_score(item_tokens, node_text)
        scored.append({
            "id": node_id,
            "status": node.get("status", "OFFEN"),
            "score": round(float(score), 4),
            "source": "W_fetch-light",
        })

    # Schritt 2: NUR die RELEVANTEN Treffer (score >= threshold) anknuepfen.
    # Klart KEIN Knoten den threshold -> [] (echtes Unbekanntes; no_truth_refs bleibt
    # KORREKT). Sonst NUR die threshold-klarenden Knoten als w_refs — NICHT das ganze
    # Model.
    #
    # WARUM NICHT alle Knoten (Dilutions-Defekt, BL-312-Lead-Korrektur 2026-06-12):
    #   Ein Item, das nur an EINE OFFEN-Wahrheit gekoppelt ist, MUSS srs=100 ergeben
    #   (genuine Unsicherheit) — wuerde man unverwandte BESTAETIGT-Knoten mit-anknuepfen,
    #   saenke der srs faelschlich (Dilution -> Unter-Routing). Der no_truth_refs-BUG ist
    #   das FEHLEN von refs (breakdown leer / flag=no_truth_refs), NICHT ein hoher srs-Wert.
    #   W_fetch-light hebt das Item von 'blind' (no_truth_refs) auf 'an-seine-Wahrheiten-
    #   gekoppelt'; der srs reflektiert dann den ECHTEN status-Mix DIESER Wahrheiten.
    #   (BL-255 AK-S3: 'blind' != 'unsicher'.)
    relevant = [r for r in scored if r["score"] >= threshold]
    if not relevant:
        return []

    # Stabil + deterministisch: score DESC, dann id ASC als Tie-Breaker.
    relevant.sort(key=lambda r: (-r["score"], str(r["id"])))
    return relevant[:5]
