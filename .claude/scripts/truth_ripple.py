#!/usr/bin/env python3
"""
truth_ripple.py — Ripple/Observer Kaskaden-BERECHNUNG (BL-388, read-only Teil).

User-Direktive 2026-06-16: "wenn eine Wahrheit sich aendert/als nicht-wahr herausstellt, muss
alles was darauf aufbaut zum Update gezwungen werden — Observer-Pattern." Die referenced_by[]
(Inverse-Index, R1) + der Graph machen das berechenbar:

  Wird Wahrheit X invalidiert -> betroffen ist ALLES, was X (transitiv) referenziert.
  = Rueckwaerts-BFS ueber die Kanten (src referenziert dst) ab X + die externen Referenzierer
    (PL/Spec/K-Score via referenced_by) der betroffenen Knoten.

Diese DATEI berechnet nur die Kaskaden-Menge (read-only, zyklen-sicher). Die AKTUIERUNG
(PL re-open / Spec-flag / K-Score-recompute / abhaengige Truth re-check) ist der Live-Teil
und bleibt deferred (BL-388 Mechanismus-Vollzug).
"""
from __future__ import annotations

from collections import defaultdict


def reverse_adjacency(graph: dict) -> dict:
    """dst -> {srcs}: wer referenziert diesen Knoten (die Abhaengigen)."""
    adj: dict[str, set] = defaultdict(set)
    for e in graph.get("edges", []):
        adj[e["dst"]].add(e["src"])
    return adj


def cascade(start_id: str, graph: dict, max_depth: int | None = None) -> set[str]:
    """Alle Knoten, die start_id (transitiv) referenzieren = betroffen, wenn start_id invalidiert wird.

    Rueckwaerts-BFS, zyklen-sicher. start_id selbst NICHT im Ergebnis.
    """
    adj = reverse_adjacency(graph)
    seen: set[str] = {start_id}
    frontier: set[str] = {start_id}
    depth = 0
    while frontier:
        if max_depth is not None and depth >= max_depth:
            break
        nxt: set[str] = set()
        for node in frontier:
            for src in adj.get(node, ()):
                if src not in seen:
                    seen.add(src)
                    nxt.add(src)
        frontier = nxt
        depth += 1
    seen.discard(start_id)
    return seen


def affected_external(affected: set[str], truths_by_id: dict[str, dict]) -> list[dict]:
    """Externe Referenzierer (PL/Spec/K-Score) der betroffenen Knoten = was benachrichtigt werden muss."""
    out: list[dict] = []
    for tid in sorted(affected):
        t = truths_by_id.get(tid)
        if not t:
            continue
        for rb in t.get("referenced_by", []):
            if isinstance(rb, dict) and rb.get("by"):
                out.append({"truth": tid, "by": rb["by"], "kind": rb.get("kind")})
    return out


def ripple_report(start_id: str, graph: dict, truths_by_id: dict[str, dict]) -> dict:
    """Vollstaendiger Kaskaden-Bericht fuer eine Invalidierung (read-only)."""
    affected = cascade(start_id, graph)
    return {
        "invalidated": start_id,
        "affected_truths": sorted(affected),
        "affected_count": len(affected),
        "notify_external": affected_external(affected, truths_by_id),
    }
