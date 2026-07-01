"""kscore_v3_topology.py — BL-311 batch_2: Stage 2 Topologie-Barrier.

Aggregiert pro-Item Walker-Outputs (Rohdaten-Vektoren der Achsen 1-6) zu einer
Batch-weiten Topologie-Sicht: Overlap-Graph (Knoten=Items, Kanten=geteilte
Dateien/Symbole), Contention-Score pro Item und Datei-/Symbol-Hotspots.

EINGABE (immer Parameter — nie aus git/FS gelesen):
  - walker_outputs: list[dict], je Item mit `item_id` (str) + optional
    `dateien` (list[str]) + `symbole` (list[str]). Fehlende Listen -> leer.
  - hotspot_threshold/n: Schwellwerte als Parameter (kein interner State).

AUSGABE: reine Dicts (Graph / Hotspots / Contention) — direkt serialisierbar.

STAGE: Stage 2 (Topologie-Barrier) zwischen batch_1 Walker (Achsen) und
  Stage 3 Scoring (kscore_v3_scoring).

REUSE (kein Duplikat): Algorithmus-Muster analog cochange_coupling.file_degree
  (Counter/Adjazenz ueber Item-Paare).

INV: Alle Funktionen sind pure (keine Seiteneffekte, kein File-IO) — gleiche
  EINGABE liefert garantiert identische AUSGABE (Determinismus).
"""
from __future__ import annotations

from collections import defaultdict
from itertools import combinations


def _item_id(walker_output: dict) -> str:
    """Liest die item_id eines Walker-Outputs (Pflichtfeld)."""
    return walker_output["item_id"]


def _dateien(walker_output: dict) -> set[str]:
    """Liest die beruehrten Dateien eines Walker-Outputs als Menge (leer wenn fehlend)."""
    return set(walker_output.get("dateien", []))


def _symbole(walker_output: dict) -> set[str]:
    """Liest die beruehrten Symbole eines Walker-Outputs als Menge (leer wenn fehlend)."""
    return set(walker_output.get("symbole", []))


def build_overlap_graph(walker_outputs: list[dict]) -> dict:
    """Baut Overlap-Graph aus allen Walker-Outputs.

    Knoten = item_ids. Kante (A, B) entsteht wenn items A und B mindestens
    1 gemeinsame Datei ODER 1 gemeinsames Symbol teilen.

    Returns:
        {
          "nodes": list[str],          # item_ids
          "edges": list[dict],         # [{from, to, shared_files, shared_symbols, weight}]
          "adj": dict[str, list[str]], # Adjazenzliste fuer schnellen Lookup
        }
    INV: Pure function — gleiche Inputs -> identischer Graph.
    """
    nodes = [_item_id(wo) for wo in walker_outputs]
    edges = []
    adj: dict[str, list[str]] = {n: [] for n in nodes}

    for wo_a, wo_b in combinations(walker_outputs, 2):
        id_a = _item_id(wo_a)
        id_b = _item_id(wo_b)

        shared_files = sorted(_dateien(wo_a) & _dateien(wo_b))
        shared_symbols = sorted(_symbole(wo_a) & _symbole(wo_b))

        if shared_files or shared_symbols:
            weight = len(shared_files) + len(shared_symbols)
            edges.append({
                "from": id_a,
                "to": id_b,
                "shared_files": shared_files,
                "shared_symbols": shared_symbols,
                "weight": weight,
            })
            adj[id_a].append(id_b)
            adj[id_b].append(id_a)

    return {"nodes": nodes, "edges": edges, "adj": adj}


def detect_hotspots(
    walker_outputs: list[dict],
    hotspot_threshold: int = 3,
) -> dict:
    """Identifiziert Dateien/Symbole die viele Items beruehren (Hotspot-Kandidaten).

    Returns:
        {
          "datei_hotspots": list[dict],   # [{datei, item_count, item_ids}]
          "symbol_hotspots": list[dict],  # [{symbol, item_count, item_ids}]
        }
    """
    datei_to_items: dict[str, list[str]] = defaultdict(list)
    symbol_to_items: dict[str, list[str]] = defaultdict(list)

    for wo in walker_outputs:
        item_id = _item_id(wo)
        for datei in _dateien(wo):
            datei_to_items[datei].append(item_id)
        for sym in _symbole(wo):
            symbol_to_items[sym].append(item_id)

    return {
        "datei_hotspots": _hotspots_above(datei_to_items, "datei", hotspot_threshold),
        "symbol_hotspots": _hotspots_above(symbol_to_items, "symbol", hotspot_threshold),
    }


def _hotspots_above(
    schluessel_to_items: dict[str, list[str]],
    key_name: str,
    threshold: int,
) -> list[dict]:
    """Filtert Schluessel (Datei/Symbol) die >= threshold Items beruehren.

    DRY-Helfer fuer datei_hotspots + symbol_hotspots — identische Filter-Logik,
    nur der Ergebnis-Key (`datei` vs. `symbol`) unterscheidet sich.
    """
    return [
        {key_name: schluessel, "item_count": len(items), "item_ids": items}
        for schluessel, items in schluessel_to_items.items()
        if len(items) >= threshold
    ]


def contention_per_item(
    walker_outputs: list[dict],
    overlap_graph: dict,
) -> dict[str, float]:
    """Berechnet Contention-Score pro Item = Anzahl Items mit denen es Dateien/Symbole teilt.

    Normiert auf [0,1] relativ zur Batch-Groesse.

    Returns: {item_id: float}
    """
    adj = overlap_graph.get("adj", {})
    n = len(walker_outputs)

    # max moeglich: n-1 Kanten
    max_possible = n - 1 if n > 1 else 1

    result: dict[str, float] = {}
    for wo in walker_outputs:
        item_id = _item_id(wo)
        neighbor_count = len(adj.get(item_id, []))
        result[item_id] = neighbor_count / max_possible if max_possible > 0 else 0.0

    return result


def topology_summary(
    walker_outputs: list[dict],
    hotspot_threshold: int = 3,
) -> dict:
    """Top-Level-Convenience: ruft build_overlap_graph + detect_hotspots + contention_per_item.

    Returns:
        {
          "overlap_graph": dict,
          "hotspots": dict,
          "contention": dict[str,float],
        }
    """
    overlap_graph = build_overlap_graph(walker_outputs)
    hotspots = detect_hotspots(walker_outputs, hotspot_threshold=hotspot_threshold)
    contention = contention_per_item(walker_outputs, overlap_graph)

    return {
        "overlap_graph": overlap_graph,
        "hotspots": hotspots,
        "contention": contention,
    }
