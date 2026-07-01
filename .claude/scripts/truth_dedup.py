#!/usr/bin/env python3
"""
truth_dedup.py — Duplikat-Detektor via content_hash (BL-309 R4, Migrations-Pass).

User-Direktive 2026-06-16: "Wahrheiten werden heute 2-3x kopiert (eine Wahrheit geklaut an
anderen Stellen). Es soll mit Verweisen gearbeitet werden." -> Migration kollabiert Duplikate
auf EINE kanonische Wahrheit + Aliase (alle Alt-Refs loesen via Alias-Map auf die kanonische auf).

READ-ONLY: erkennt + plant nur. Der eigentliche Kollaps (kanonische behalten, Duplikate als
Alias) ist ein Migrations-WRITE (gefenced, Phase C). Git-CAS-Lektion: gleicher content_hash =
identischer Inhalt = Duplikat.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict


def _hash(t: dict) -> str:
    """content_hash der Wahrheit; faellt auf sha256(text) zurueck wenn Feld fehlt."""
    h = t.get("content_hash")
    if h:
        return str(h)
    return hashlib.sha256((t.get("text") or "").encode("utf-8")).hexdigest()


def _truth_id(t: dict) -> str:
    return str(t.get("id") or t.get("local_id") or "")


def dedup_groups(truths: list[dict]) -> dict[str, list[dict]]:
    """Gruppiert nach content_hash; liefert NUR Gruppen mit >1 Mitglied (= Duplikate)."""
    by_hash: dict[str, list[dict]] = defaultdict(list)
    for t in truths:
        by_hash[_hash(t)].append(t)
    return {h: ts for h, ts in by_hash.items() if len(ts) > 1}


def alias_plan(truths: list[dict]) -> list[dict]:
    """Plan: pro Duplikat-Gruppe eine kanonische Wahrheit + Aliase (deterministisch: kleinste id).

    Returns [{content_hash, canonical, aliases[]}]. Der Plan speist die Alias-Map (Konnektions-
    Erhalt): alle Refs auf die Aliase loesen auf die kanonische auf. KEIN Write hier.
    """
    plan: list[dict] = []
    for h, ts in sorted(dedup_groups(truths).items()):
        ids = sorted(_truth_id(t) for t in ts)
        plan.append({"content_hash": h, "canonical": ids[0], "aliases": ids[1:]})
    return plan


def dedup_stats(truths: list[dict]) -> dict:
    """Verdichtung fuer die Readiness-Inventur."""
    groups = dedup_groups(truths)
    dup_total = sum(len(ts) for ts in groups.values())
    collapsible = dup_total - len(groups)  # so viele Dateien wuerden zu Aliasen
    return {
        "truths": len(truths),
        "duplicate_groups": len(groups),
        "duplicate_members": dup_total,
        "collapsible_to_alias": collapsible,
    }
