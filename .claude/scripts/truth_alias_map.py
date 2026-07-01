#!/usr/bin/env python3
"""
truth_alias_map.py — Alias-Map-Writer (BL-309 R4 / BL-386 Runbook Schritt 4).

Erzeugt die Alias-Map `{vault}/_meta/truth_alias_map.json`, die truth_resolver als Dual-Read-Stufe 2
liest (Konnektions-Erhalt + never-renumber): jeder Alt-/Duplikat-Ref loest auf die kanonische Wahrheit auf.
Quelle der Aliase = truth_dedup.alias_plan (content_hash-Duplikate → kanonisch = kleinste id + Aliase).

Resolver-Format (truth_resolver.resolve Stufe 2):  { "<alias_id>": {"resolves_to": "<canonical_id>"} }

SICHERHEIT (BL-364): build_alias_map/merge sind read-only-rein; write_alias_map operiert auf UEBERGEBENEM
vault_root (Tests: tmp). Der reale `{vault}/_meta/`-Write ist der bewusste Fresh-Session-Cutover-Akt
(zusammen mit dem --write-Lauf, mit Backup). never-renumber: ein bestehendes Mapping wird NIE still
auf ein abweichendes Ziel ueberschrieben (Konflikt wird gemeldet).
"""
from __future__ import annotations

import json
from pathlib import Path

import truth_dedup as dd

_REL = Path("_meta") / "truth_alias_map.json"


def build_alias_map(truths: list[dict]) -> dict:
    """dedup.alias_plan → Resolver-Alias-Map {alias_id: {resolves_to, reason}}.
    Leere Map wenn keine Duplikate (z.B. OmniCommand-Korpus = 0 byte-Dups)."""
    amap: dict = {}
    for grp in dd.alias_plan(truths):
        canon = grp["canonical"]
        for alias in grp["aliases"]:
            if alias and alias != canon:
                amap[str(alias)] = {"resolves_to": str(canon), "reason": "dedup_content_hash"}
    return amap


def merge_alias_map(existing: dict, new: dict) -> tuple[dict, list]:
    """never-renumber-sicherer Merge: bestehende Mappings bleiben; neue ergaenzen. Ein bestehender
    Eintrag, der auf ein ABWEICHENDES Ziel zeigt, wird NICHT ueberschrieben → als Konflikt gemeldet."""
    merged = dict(existing or {})
    conflicts: list = []
    for k, v in (new or {}).items():
        cur = merged.get(k)
        if cur is not None:
            cur_t = cur.get("resolves_to") if isinstance(cur, dict) else cur
            new_t = v.get("resolves_to") if isinstance(v, dict) else v
            if str(cur_t) != str(new_t):
                conflicts.append({"alias": k, "existing": cur_t, "proposed": new_t})
                continue  # never-renumber: NICHT still ueberschreiben
        merged[k] = v
    return merged, conflicts


def alias_map_path(vault_root) -> Path:
    return Path(vault_root) / _REL


def write_alias_map(amap: dict, vault_root, *, merge: bool = True) -> dict:
    """Schreibt {vault}/_meta/truth_alias_map.json (Resolver-Stufe-2). merge=True erhaelt bestehende
    Eintraege (never-renumber). Returns {path, written, conflicts}. (Fresh-Session-Akt auf echter Vault.)"""
    p = alias_map_path(vault_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    conflicts: list = []
    if merge and p.is_file():
        try:
            existing = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                amap, conflicts = merge_alias_map(existing, amap)
        except (json.JSONDecodeError, OSError):
            pass  # korrupte/leere Map: neu schreiben
    p.write_text(json.dumps(amap, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return {"path": str(p), "written": len(amap), "conflicts": conflicts}
