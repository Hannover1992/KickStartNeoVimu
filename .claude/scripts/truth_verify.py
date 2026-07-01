#!/usr/bin/env python3
"""
truth_verify.py — INV-MIG-Verifikations-Suite (BL-309 Schritt 9, read-only).

Die formale Korrektheits-Pruefung VOR dem Cutover (zusaetzlich zu roundtrip/census/schema/dedup):
  INV-MIG-10  ID-Eindeutigkeit: kein globales {BL-SLUG}.{local_id} doppelt (Allokator + never-renumber
              muessen das garantieren; der Verifier BEWEIST es ueber den ganzen Korpus).
  ID/local_id-Konsistenz: id endet auf '.{local_id}' (never-renumber-Anker).
  Referenz-Integritaet: edge-ziele loesen auf existierende Knoten auf (unaufgeloest = Cross-BL/missing
              = SIGNAL fuer die Alias-Map, kein Hard-Fail).

READ-ONLY. clean = keine ID-Kollision + keine id/local-Inkonsistenz (die harten Invarianten).
"""
from __future__ import annotations

from collections import defaultdict


def check_id_uniqueness(truths: list[dict]) -> dict[str, list]:
    """INV-MIG-10: globale id darf nicht doppelt sein. Returns {id: [local_ids]} fuer Kollisionen."""
    seen: dict[str, list] = defaultdict(list)
    for t in truths:
        tid = t.get("id")
        if tid:
            seen[str(tid)].append(t.get("local_id"))
    return {tid: lids for tid, lids in seen.items() if len(lids) > 1}


def check_id_local_consistency(truths: list[dict]) -> list[dict]:
    """id muss auf '.{local_id}' enden (never-renumber-Konsistenz)."""
    bad: list[dict] = []
    for t in truths:
        tid, lid = t.get("id"), t.get("local_id")
        if tid and lid and not str(tid).endswith("." + str(lid)):
            bad.append({"id": tid, "local_id": lid})
    return bad


def check_reference_resolution(truths: list[dict]) -> list[dict]:
    """Edge-Ziele (im Quell-namespace global aufgeloest) sollen auf existierende ids zeigen.
    Unaufgeloest = Cross-BL/missing = Signal (kein Hard-Fail)."""
    ids = {str(t.get("id")) for t in truths if t.get("id")}
    unresolved: list[dict] = []
    for t in truths:
        tid = str(t.get("id", ""))
        ns = tid.rsplit(".", 1)[0] if "." in tid else None
        for e in t.get("edges", []):
            if not isinstance(e, dict) or not e.get("ziel"):
                continue
            ziel = str(e["ziel"])
            g = ziel if "." in ziel else (f"{ns}.{ziel}" if ns else ziel)
            if g not in ids:
                unresolved.append({"from": tid, "to": g})
    return unresolved


def verify_all(truths: list[dict]) -> dict:
    collisions = check_id_uniqueness(truths)
    inconsistencies = check_id_local_consistency(truths)
    unresolved = check_reference_resolution(truths)
    return {
        "truths": len(truths),
        "id_collisions": collisions,
        "id_collision_count": len(collisions),
        "id_local_inconsistencies": inconsistencies,
        "unresolved_edges": len(unresolved),
        "clean": not collisions and not inconsistencies,  # harte Invarianten; unresolved = Signal
    }
