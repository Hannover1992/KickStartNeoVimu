#!/usr/bin/env python3
"""
truth_id_allocator.py — EIN kollisionsfreier local_id-Allokator (BL-387 / BL-309).

Loest den dokumentierten 2-Allokator-Konflikt (Truth-Migration-Architektur):
  modelSync     vergibt max+1      (KORREKT: nie Renummerierung, nie Kollision)
  modelMaintain vergibt w_total+1  (DEFEKT: kollidiert sobald es Luecken gibt -
                                    z.B. retracted/geloeschte ids -> w_total < max)

Going-forward muessen ALLE Produzenten denselben Allokator nutzen, sonst entsteht neuer
ID-Drift schneller als die Migration ihn heilt. Regel: max(numerische W-ids) + 1, Breite
der Konvention erhalten, never-renumber (bestehende ids unangetastet), never-collide.
"""
from __future__ import annotations

import re

_WNUM = re.compile(r"^W(\d+)[A-Za-z]?$")  # W01, W12, W12a  (NICHT W-AK-A / dashed)


def w_number(local_id: str) -> int | None:
    """Numerischer Teil einer W-id (W01->1, W12a->12); None bei dashed (W-AK-A) o.ae."""
    m = _WNUM.match(str(local_id))
    return int(m.group(1)) if m else None


def next_local_id(existing, prefix: str = "W") -> str:
    """Naechste kollisionsfreie W-id = max(numerisch)+1 (NICHT count+1). Breite konvention-erhaltend.

    never-renumber: bestehende ids bleiben unberuehrt. never-collide: Ergebnis nicht in `existing`.
    """
    existing = set(str(e) for e in existing)
    nums: list[int] = []
    width = 2  # Default-Konvention W01
    for lid in existing:
        m = _WNUM.match(lid)
        if m:
            nums.append(int(m.group(1)))
            width = max(width, len(m.group(1)))
    nxt = (max(nums) + 1) if nums else 1
    cand = f"{prefix}{nxt:0{width}d}"
    while cand in existing:  # Paranoia gegen Rest-Kollision (z.B. gemischte Breiten)
        nxt += 1
        cand = f"{prefix}{nxt:0{width}d}"
    return cand


def allocate_batch(existing, n: int, prefix: str = "W") -> list[str]:
    """n neue kollisionsfreie ids sequentiell (jede wird beim Vergeben zu existing addiert)."""
    pool = set(str(e) for e in existing)
    out: list[str] = []
    for _ in range(n):
        nid = next_local_id(pool, prefix)
        out.append(nid)
        pool.add(nid)
    return out
