#!/usr/bin/env python3
"""
truth_consume.py — Konsumenten-API ueber dem Wahrheits-Substrat (BL-387 Keystone).

User-Direktive 2026-06-16 (Prio 1): "das System muss mit den neuen Wahrheiten arbeiten —
nicht mehr Inline-Parse, sondern Referenzen/Pointer". Die ~10 Konsumenten-Oberflaechen
(K-Score model_refs, PL source_w, Spec-Wikilinks, Gap, SRS, arc42) sollen NICHT mehr Model.md
ad-hoc parsen (drift-anfaellig), sondern diese DETERMINISTISCHE API aufrufen.

Das ist der thin consumer-facing Adapter ueber truth_resolver (Dual-Read) + truth_srs. Die
spaetere Skill-Verdrahtung (BL-387 Doc-Fläche) ruft nur noch `truth_consume.value(ref)` etc.
READ-ONLY.
"""
from __future__ import annotations

from typing import Optional

import truth_resolver as tr
import truth_srs as tsrs


def value(ref: str, *, bl_folder=None, vault_root=None, repo_models=None) -> dict:
    """Loest eine Wahrheits-Referenz auf -> Konsumenten-Sicht (text/status/lifecycle/typ/grade).
    found=False wenn unaufloesbar (lautes Signal, kein stiller Default)."""
    r = tr.resolve(ref, bl_folder=bl_folder, vault_root=vault_root, repo_models=repo_models)
    if not r.found:
        return {"found": False, "ref": str(ref), "source": r.source}
    t = r.truth or {}
    return {
        "found": True,
        "ref": str(ref),
        "resolved_id": r.resolved_id,
        "source": r.source,
        "text": t.get("text"),
        "status": t.get("status"),
        "lifecycle": t.get("lifecycle"),
        "typ": t.get("typ"),
        "truth_grade": t.get("truth_grade"),
    }


def is_open(ref: str, **kw) -> Optional[bool]:
    """Ist die referenzierte Wahrheit epistemisch offen? None wenn unaufloesbar."""
    v = value(ref, **kw)
    if not v["found"]:
        return None
    return tsrs.is_open({"typ": v.get("typ"), "lifecycle": v.get("lifecycle")})


def srs_for(refs, **kw) -> dict:
    """SRS-View ueber einer Menge referenzierter Wahrheiten (Konsument: PL/Story-SRS).
    Unaufloesbare Refs werden uebersprungen + in 'unresolved' gezaehlt."""
    truths: list[dict] = []
    unresolved = 0
    for ref in refs:
        v = value(ref, **kw)
        if v["found"]:
            truths.append({"typ": v.get("typ"), "lifecycle": v.get("lifecycle")})
        else:
            unresolved += 1
    out = tsrs.srs_from_truths(truths)
    out["unresolved_refs"] = unresolved
    return out
