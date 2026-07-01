#!/usr/bin/env python3
"""
truth_graph.py — der bidirektionale Wahrheits-Graph als read-only VIEW (BL-384 / BL-309).

User-Direktive 2026-06-16: "es gibt diese bidirektionale Verbindung zwischen der Wahrheit und den
Knoten ... wir wollen spaeter diesen Ripple-Effekt." -> der Graph ist eine generierte VIEW ueber
den Wahrheiten (forward edges[] + ext_refs aus referenced_by), KEINE eigene Quelle (Rebuildability-LAW).

Das ist die STATISCHE Graph-Sicht (Struktur + Metriken), NICHT die lernende Maschine (BL-287, deferred).
Sie ist das Substrat, das der Ripple/Observer (BL-388) traversiert + das Navigieren ermoeglicht.
READ-ONLY.
"""
from __future__ import annotations

from collections import Counter


def build_graph(truths: list[dict]) -> dict:
    """{nodes: {global_id: {...}}, edges: [{src, dst, rel}]}. Edges = forward edges[] pro Wahrheit.

    Knoten per GLOBALER id (BL-SLUG.local_id), sonst kollidieren gleiche local_ids (W01...) ueber
    BLs hinweg in einen Knoten (Real-Korpus-Befund: 2289 Truths -> 492 Knoten + W1-W11-Super-Hubs).
    Edge-ziel (local_id) wird im namespace der Quelle global aufgeloest.
    """
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    for t in truths:
        gid = t.get("id") or t.get("local_id")
        if gid is None:
            continue
        ns = gid.rsplit(".", 1)[0] if "." in str(gid) else None
        nodes[gid] = {
            "local_id": t.get("local_id"),
            "typ": t.get("typ"),
            "lifecycle": t.get("lifecycle"),
            "ext_refs": len(t.get("referenced_by", [])),  # PL/Spec/K-Score etc. zeigen rein
        }
        for e in t.get("edges", []):
            if isinstance(e, dict) and e.get("ziel"):
                ziel = str(e["ziel"])
                dst = ziel if "." in ziel else (f"{ns}.{ziel}" if ns else ziel)
                edges.append({"src": gid, "dst": dst, "rel": e.get("rel", "relates_to")})
    return {"nodes": nodes, "edges": edges}


def out_degree(graph: dict) -> Counter:
    return Counter(e["src"] for e in graph["edges"])


def in_degree(graph: dict) -> Counter:
    return Counter(e["dst"] for e in graph["edges"])


def hubs(graph: dict, top: int = 10) -> list[tuple[str, int]]:
    """Knoten nach Gesamt-Grad (in+out), absteigend."""
    deg: Counter = Counter()
    for e in graph["edges"]:
        deg[e["src"]] += 1
        deg[e["dst"]] += 1
    return deg.most_common(top)


def dangling_edges(graph: dict) -> list[dict]:
    """Edges, deren Ziel kein bekannter Knoten ist (Ref auf externe/fehlende Wahrheit) -> Migrations-Signal."""
    known = set(graph["nodes"])
    return [e for e in graph["edges"] if e["dst"] not in known]


def isolated(graph: dict) -> list[str]:
    """Knoten ohne jede Verbindung (kein edge rein/raus, keine ext_refs) -> Wald-Einsamkeit."""
    connected: set[str] = set()
    for e in graph["edges"]:
        connected.add(e["src"])
        if e["dst"] in graph["nodes"]:
            connected.add(e["dst"])
    return sorted(
        lid for lid, n in graph["nodes"].items()
        if lid not in connected and not n.get("ext_refs")
    )


def graph_stats(graph: dict) -> dict:
    return {
        "nodes": len(graph["nodes"]),
        "edges": len(graph["edges"]),
        "dangling": len(dangling_edges(graph)),
        "isolated": len(isolated(graph)),
        "top_hubs": hubs(graph, 5),
    }
