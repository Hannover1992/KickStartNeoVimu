#!/usr/bin/env python3
"""
truth_edge_backref.py — Edge-basierter referenced_by-Materializer (BL-451 AC-2a).

Invertiert edges[].ziel → referenced_by[{by, kind:"truth_edge"}] in truth-Atomen.

Unterschied zu truth_backref_materialize: nutzt das edges[]-Feld im Frontmatter statt
den global gebauten Backref-Index (build_backref_index). Praezise Inversion basierend
auf expliziten Kanten.

Modi:
  - apply=False (dry-run): nur zaehlen, NIE schreiben (updated=0).
  - apply=True: schreiben. updated = Anzahl tatsaechlich geaenderter Dateien. Idempotent.
  - backup_dir + apply: VOR dem Schreiben jede zu aendernde Datei nach backup_dir kopieren;
    backed_up = updated.

Rueckgabe-dict: {"scanned", "with_refs", "would_update", "updated", "backed_up"} (alle int).
"""
from __future__ import annotations

import argparse
import shutil
import sys
from collections import defaultdict
from pathlib import Path

import yaml

from truth_backref_materialize import (
    _build_new_content,
    _parse_frontmatter,
    _scalar_field,
)


def build_edge_backref_index(root: Path) -> dict[str, list[dict]]:
    """Scannt root rekursiv nach truth-Atomen und invertiert edges[].ziel.

    Liefert {B_id: [{by: A_id, kind: "truth_edge"}, ...]} fuer alle Kanten A->B.

    - Dangling (ziel-id nicht in id_set) werden ausgelassen.
    - Self-Edges (ziel == A_id) werden ausgelassen.
    - Dedup pro Ziel auf (by, kind).
    """
    root = Path(root)

    # Pass 1: id_set aufbauen + rohe Kanten sammeln
    id_set: set[str] = set()
    raw_edges: list[tuple[str, str]] = []  # (A_id, B_id)

    for f in sorted(root.rglob("*.md")):
        if not f.is_file():
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parsed = _parse_frontmatter(content)
        if parsed is None:
            continue
        fm_text = parsed[0]

        if _scalar_field(fm_text, "type") != "truth":
            continue
        atom_id = _scalar_field(fm_text, "id")
        if not atom_id:
            continue

        id_set.add(atom_id)

        # Edges aus YAML parsen
        try:
            fm_data = yaml.safe_load(fm_text) or {}
        except yaml.YAMLError:
            fm_data = {}

        edges = fm_data.get("edges") or []
        for edge in edges:
            if not isinstance(edge, dict):
                continue
            ziel = edge.get("ziel")
            if ziel and isinstance(ziel, str):
                raw_edges.append((atom_id, ziel))

    # Pass 2: invertieren (mit id_set-Filter + Self-Edge-Filter + Dedup)
    index: dict[str, list[dict]] = defaultdict(list)
    seen: set[tuple[str, str]] = set()  # (B_id, A_id) fuer Dedup

    for a_id, b_id in raw_edges:
        if b_id not in id_set:
            continue  # Dangling
        if b_id == a_id:
            continue  # Self-Edge
        key = (b_id, a_id)
        if key in seen:
            continue  # Dedup
        seen.add(key)
        index[b_id].append({"by": a_id, "kind": "truth_edge"})

    return dict(index)


def materialize_edges(
    root: Path,
    apply: bool = False,
    backup_dir: Path | None = None,
) -> dict:
    """Materialisiert referenced_by[] via Edge-Inversion in truth-Atomen unter root.

    apply=False -> dry-run (nur zaehlen). apply=True -> schreiben (surgical patch).
    backup_dir + apply -> vor jedem Write die Datei sichern.
    """
    root = Path(root)
    index = build_edge_backref_index(root)

    scanned = 0
    with_refs = 0
    would_update = 0
    updated = 0
    backed_up = 0

    if backup_dir is not None:
        backup_dir = Path(backup_dir)

    for f in sorted(root.rglob("*.md")):
        if not f.is_file():
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parsed = _parse_frontmatter(content)
        if parsed is None:
            continue
        fm_text = parsed[0]

        if _scalar_field(fm_text, "type") != "truth":
            continue
        atom_id = _scalar_field(fm_text, "id")
        if not atom_id:
            continue

        scanned += 1

        rb = index.get(atom_id)
        if not rb:
            continue
        with_refs += 1

        new_content = _build_new_content(content, rb)
        if new_content is None:
            continue
        if new_content == content:
            # Bereits aktuell -> kein Update noetig (Idempotenz).
            continue

        would_update += 1

        if apply:
            if backup_dir is not None:
                backup_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, backup_dir / f.name)
                backed_up += 1
            f.write_text(new_content, encoding="utf-8")
            updated += 1

    return {
        "scanned": scanned,
        "with_refs": with_refs,
        "would_update": would_update,
        "updated": updated,
        "backed_up": backed_up,
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="truth_edge_backref",
        description="BL-451 AC-2a: referenced_by[] edge-inversion materializer",
    )
    p.add_argument("root", type=Path)
    p.add_argument("--apply", action="store_true", help="schreiben (sonst dry-run)")
    p.add_argument("--backup-dir", type=Path, default=None, help="Backup-Verzeichnis vor Apply")
    args = p.parse_args(argv)

    if not args.root.is_dir():
        print(f"ERROR: {args.root} kein Verzeichnis", file=sys.stderr)
        return 2

    res = materialize_edges(args.root, apply=args.apply, backup_dir=args.backup_dir)
    print(
        f"scanned={res['scanned']} with_refs={res['with_refs']} "
        f"would_update={res['would_update']} updated={res['updated']} "
        f"backed_up={res['backed_up']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
