#!/usr/bin/env python3
"""
gc_slim_general.py — BL-338 / batch_PL3 / PL-338-2 (Slim-Generalisierung, M3).

Verallgemeinert den BL-229-manifest_slim-Kern (Map -> Split -> Verify, MD5-lossless)
von "Manifest-Rounds" auf eine TYP-PARAMETRISIERTE Familien-/Done-Definition je
Langzeit-Artefakt:
  - backlog_index : DONE-Eintraege ([x]) auslagern, offene ([ ]) behalten
  - parking_lot   : abgehakte [x]-Items auslagern, offene [ ] behalten
  - model         : superseded-Bloecke auslagern, Working-Set (active/invariant) behalten

Wiederverwendung statt Re-Invent (PL-338-2 §Reuse): das lossless-Gate uebernimmt das
manifest_slim.verify_split-Prinzip (jede nicht-leere Original-Zeile ist in kept ODER
archived) + manifest_slim._md5; Budget via gc_budgets.resolve_budget.

cwd-STABILITAETS-MANDAT (PL-336-4-Lehre): slim_artifact loest den uebergebenen `path`
NIE cwd-relativ auf — der Pfad wird 1:1 verwendet (Path(path)). resolve_budget ist
seinerseits __file__-relativ (gc_budgets), liefert also aus jedem cwd identisch.

Aufruf:
  python3 .claude/scripts/gc_slim_general.py slim PATH ARTIFACT_TYPE [--dry-run]
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

# Budget-Registry. Modul-globaler Name `resolve_budget` ist der Monkeypatch-Anker
# in test_gc_slim_general.py (monkeypatch.setattr(gs, "resolve_budget", ...)).
from gc_budgets import resolve_budget  # noqa: F401

# Reuse statt Re-Invent (PL-338-2 §Reuse): das MD5- + Split-Verify-Prinzip aus BL-229.
from manifest_slim import _md5, verify_split  # noqa: F401


# Done-Marker je Zeilen-basiertem Typ: eine Zeile gilt als "done/auslagerbar", wenn
# das Pattern matcht. Offene Working-Set-Zeilen bleiben.
_DONE_LINE = re.compile(r"-\s*\[x\]", re.IGNORECASE)


def _split_lines_by_done(content: str) -> tuple[str, str]:
    """Zeilen-Familie (backlog_index / parking_lot): [x]-Zeilen auslagern, Rest behalten.

    Lossless: jede Original-Zeile landet entweder in kept ODER in archived. Reine
    Struktur-/Leerzeilen (Header, Blank) bleiben im Working-Set (kept).
    """
    kept_lines: list[str] = []
    archived_lines: list[str] = []
    for line in content.splitlines(keepends=True):
        if _DONE_LINE.search(line):
            archived_lines.append(line)
        else:
            kept_lines.append(line)
    return "".join(kept_lines), "".join(archived_lines)


def _split_model_blocks(content: str) -> tuple[str, str]:
    """Model-Familie: `## `-Bloecke mit superseded-Status auslagern, Working-Set behalten.

    Analog manifest_slim._split_blocks (Block-Grenze = `## `-Header). Ein Block ist
    auslagerbar, wenn sein Text `superseded` (status/Marker) enthaelt; der aktuelle
    active-Block + invariante AK bleiben im kept (lossless: Preamble immer behalten).
    """
    lines = content.splitlines(keepends=True)
    preamble: list[str] = []
    blocks: list[str] = []  # je Eintrag: kompletter `## ...`-Blocktext
    cur: list[str] | None = None

    def flush():
        if cur is not None:
            blocks.append("".join(cur))

    for line in lines:
        if line.startswith("## "):
            flush()
            cur = [line]
        elif cur is None:
            preamble.append(line)
        else:
            cur.append(line)
    flush()

    kept_parts: list[str] = ["".join(preamble)]
    archived_parts: list[str] = []
    for block in blocks:
        if re.search(r"superseded", block, re.IGNORECASE):
            archived_parts.append(block)
        else:
            kept_parts.append(block)
    return "".join(kept_parts), "".join(archived_parts)


# Typ -> Splitter. Unbekannter Typ steht NICHT hier -> safe No-Op (G2e).
_SPLITTERS = {
    "backlog_index": _split_lines_by_done,
    "parking_lot": _split_lines_by_done,
    "model": _split_model_blocks,
}


def _no_op(path: Path) -> dict:
    """Resilienz-Sentinel: nichts auslagern, Original unangetastet (G2d/G2e)."""
    return {
        "kept": path.read_text(encoding="utf-8") if path.is_file() else "",
        "archived": "",
        "archive_path": None,
        "over_budget": False,
        "lossless": True,
    }


def slim_artifact(path: str, artifact_type: str, dry_run: bool = False) -> dict:
    """Typ-parametrisiertes Slim eines Langzeit-Artefakts (Map -> Split -> Verify).

    1. Budget via resolve_budget(artifact_type). budget None (unbekannter Typ /
       fehlende Registry) -> safe No-Op {over_budget: False}, KEIN Crash (G2e).
    2. Datei-Groesse (bytes) <= Budget -> No-Op {over_budget: False} (G2d).
    3. Sonst: typ-spezifisch in kept/archived splitten; lossless-Gate (verify_split-
       Prinzip: jede nicht-leere Original-Zeile in kept ODER archived). dry_run -> kein
       Write. Sonst kept zurueck ins Original + archived in eine Senke (verlustfrei).

    -> {kept, archived, archive_path, over_budget, lossless}.

    cwd-stabil: der uebergebene `path` wird 1:1 als Path verwendet, NIE cwd-relativ.
    (PL-338-2, 2026-06-13)
    """
    p = Path(path)  # 1:1 uebernehmen (cwd-STABIL — kein cwd-Re-Interpret)
    budget = resolve_budget(artifact_type)
    splitter = _SPLITTERS.get(artifact_type)

    # G2e: unbekannter Typ / fehlendes Budget -> safe No-Op (kein Crash).
    if budget is None or splitter is None or not p.is_file():
        return _no_op(p)

    original = p.read_text(encoding="utf-8")
    actual = len(original.encode("utf-8"))

    # G2d: unter (oder gleich) Budget -> No-Op, Original unangetastet.
    if actual <= budget:
        result = _no_op(p)
        result["kept"] = original
        return result

    # ── MAP + SPLIT (typ-spezifisch) ──
    kept, archived = splitter(original)
    archive_md5 = _md5(archived)

    # ── VERIFY: lossless-Gate (manifest_slim.verify_split Gate-3-Prinzip) ──
    # live_markers leer: Zeilen-/Block-Familien haben keine separaten currentState-Marker;
    # das missing-Gate (jede nicht-leere Zeile in kept|archived) ist der lossless-Beweis.
    _all_pass, report = verify_split(
        original=original, kept=kept, archived=archived,
        archive_md5=archive_md5, live_markers=[],
    )
    lossless = report["lossless"] and not report["missing"]

    archive_path = p.parent / f"{p.stem}_archive_{datetime.now().strftime('%Y-%m-%d')}{p.suffix}"

    if dry_run:
        # dry_run veraendert NICHTS — kein Write am Original, keine persistente Senke (G2c).
        return {
            "kept": kept,
            "archived": archived,
            "archive_path": None,
            "over_budget": True,
            "lossless": lossless,
        }

    # ── WRITE: archived in die Senke (verlustfrei), kept zurueck ins Original. ──
    head = (
        f"# {p.stem} — ausgelagertes Archiv ({datetime.now().strftime('%Y-%m-%d')})\n\n"
        f"<!-- gc_slim_general PL-338-2: verlustfrei, typ={artifact_type}, MD5={archive_md5} -->\n\n"
    )
    archive_path.write_text(head + archived, encoding="utf-8")
    p.write_text(kept, encoding="utf-8")

    return {
        "kept": kept,
        "archived": archived,
        "archive_path": archive_path,
        "over_budget": True,
        "lossless": lossless,
    }


def _cli(argv=None) -> int:
    ap = argparse.ArgumentParser(description="BL-338 gc_slim_general — typ-parametrisiertes Artefakt-Slim")
    sub = ap.add_subparsers(dest="cmd")
    ps = sub.add_parser("slim")
    ps.add_argument("path")
    ps.add_argument("artifact_type")
    ps.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    if args.cmd != "slim":
        ap.print_help()
        return 2

    result = slim_artifact(args.path, args.artifact_type, dry_run=args.dry_run)
    tag = "DRY-RUN" if args.dry_run else "DONE"
    print(f"[GC-SLIM {tag}] {args.path} ({args.artifact_type}): over_budget={result['over_budget']} "
          f"lossless={result['lossless']} archive={result['archive_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
