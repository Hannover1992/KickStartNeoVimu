#!/usr/bin/env python3
"""
truth_backref_index.py — Inverse-Index-Bau (BL-309 R1, one-shot-kritisch).

User-Direktive 2026-06-16 (ultrathink): "wenn eine Wahrheit sich aendert, muss sie bidirektional
ALLE Anker kennen, die auf sie referenzieren" -> Ripple/Observer (BL-388). Das WISSEN (der Index)
laesst sich NUR EINMAL sauber bauen: waehrend der Migration, durch Scannen aller Oberflaechen, die
auf Wahrheiten zeigen. Danach befuellt der Atomizer/Orchestrator `referenced_by[]` pro Wahrheit.

READ-ONLY: scannt nur, mutiert nichts. Liefert {local_id -> [{by, kind}]}.

Oberflaechen (kind = REFERENCED_BY_KINDS aus truth_schema):
  Parking-Lot (pl_source_w) · Spec (spec_link) · K-Score (kscore_ref) · andere Truths' edges (truth_edge).
Das Model selbst ist die QUELLE der Knoten (Definition), kein Referenzierer -> ausgeschlossen.
"""
from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

# BL-395(c): EINE kanonische W-ID-Lexikon-Quelle (truth_wid = identisch mit _HEADING_LINE local_id) statt
# 4x Duplikat. Fallback unifiziert mit _HEADING_LINE (inkl. '_'-Suffix -> W7_REF-Referenzen aufloesbar).
try:
    from truth_wid import WID_TOKEN as _WREF
except ImportError:
    _WREF = re.compile(r"\bW(?:\d+[A-Za-z0-9_]*|-(?!Knoten\b)[A-Z][A-Za-z0-9_-]*)\b")

# (glob, kind). Reihenfolge egal; Dedup am Ende. Model/truths bewusst NICHT dabei.
SURFACES: list[tuple[str, str]] = [
    ("**/*parking-lot*.md", "pl_source_w"),
    ("**/6_PL/*.md", "pl_source_w"),
    ("**/*Spec*.md", "spec_link"),
    ("**/3_Spec/*.md", "spec_link"),
    ("**/*K-SCORE*.md", "kscore_ref"),
    ("**/*K-Score*.md", "kscore_ref"),
    ("**/4_K-Score/*.md", "kscore_ref"),
]


def find_wrefs(text: str) -> set[str]:
    """Alle W-Referenzen in einem Text."""
    return set(_WREF.findall(text))


def _dedup(entries: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    out: list[dict] = []
    for e in entries:
        key = (e.get("by"), e.get("kind"))
        if key not in seen:
            seen.add(key)
            out.append(e)
    return out


def build_backref_index(bl_folder: Path) -> dict[str, list[dict]]:
    """Scannt alle Referenzier-Oberflaechen eines BL-Ordners -> {local_id: [{by, kind}]}.

    Bidirektional: pro W-Knoten alle Anker, die auf ihn zeigen. Das ist der one-shot-Index
    fuer den Ripple/Observer (BL-388) und das `referenced_by[]`-Feld (Schema v2 R1).
    """
    bl_folder = Path(bl_folder)
    index: dict[str, list[dict]] = defaultdict(list)
    seen_files: set[tuple[Path, str]] = set()

    for glob_pat, kind in SURFACES:
        for f in bl_folder.glob(glob_pat):
            if not f.is_file():
                continue
            if (f, kind) in seen_files:
                continue
            seen_files.add((f, kind))
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for wref in find_wrefs(text):
                index[wref].append({"by": f.stem, "kind": kind})

    # andere Truths' edges (falls schon atomisiert): truths/{id}.md mit edges[].ziel -> truth_edge
    truths_dir = bl_folder / "2_Model" / "truths"
    if truths_dir.is_dir():
        for tf in truths_dir.glob("*.md"):
            try:
                text = tf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            # billige Heuristik: W-Refs im edges-Block (ohne yaml-Parse) -> Quelle = tf.stem
            for wref in find_wrefs(text):
                if wref != tf.stem:  # Selbst-Referenz ausschliessen
                    index[wref].append({"by": tf.stem, "kind": "truth_edge"})

    return {lid: _dedup(entries) for lid, entries in index.items()}


def referenced_by_for(local_id: str, index: dict[str, list[dict]]) -> list[dict]:
    """Bequemer Zugriff: die referenced_by-Liste fuer einen Knoten (leer wenn keiner zeigt)."""
    return index.get(local_id, [])


def apply_backrefs(truths: list[dict], index: dict[str, list[dict]]) -> list[dict]:
    """Befuellt `referenced_by[]` pro Wahrheit aus dem Inverse-Index (Schema v2 R1).
    Mutiert die truth-Dicts in-place + gibt sie zurueck. Der Orchestrator (BL-386) ruft
    nach atomize() diesen Pass; ohne Treffer bleibt das Feld weg (optional)."""
    for t in truths:
        rb = index.get(t.get("local_id"))
        if rb:
            t["referenced_by"] = rb
    return truths


def main(argv: list[str]) -> int:
    import argparse
    import json
    p = argparse.ArgumentParser(prog="truth_backref_index", description="BL-309 R1: Inverse-Index (read-only)")
    p.add_argument("bl_folder", type=Path)
    p.add_argument("--out", type=Path, default=None)
    args = p.parse_args(argv)
    if not args.bl_folder.is_dir():
        print(f"ERROR: {args.bl_folder} kein Verzeichnis", flush=True)
        return 2
    idx = build_backref_index(args.bl_folder)
    total_refs = sum(len(v) for v in idx.values())
    print(f"Knoten mit Rueck-Refs: {len(idx)}  Rueck-Refs gesamt: {total_refs}")
    if args.out:
        Path(args.out).write_text(json.dumps(idx, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Index: {args.out}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main(sys.argv[1:]))
