#!/usr/bin/env python3
"""
audit_fanin.py — Append-only-Concat-Fan-In-Helper fuer audit.jsonl-Streams.

BL-317 SB-3 / AK-4 (INV-G3-5).

KONTEXT
-------
`audit_hook.py` schreibt JEDEN Handschuh-Wechsel als 1 JSONL-Zeile in
`ROOT_DIR/.claude/audit/audit.jsonl` — repo-/cwd-relativ, also DE-FACTO
worker-lokal: in einem `parallel()`-Worktree landet der Stream im Worktree-Dir,
nicht im Main-Tree. audit.jsonl ist volatil/regenerierbar und (per BL-317 AK-5)
gitignored, damit N Worker-Kopien nicht git-getrackt und damit Fan-In-konflikten.

FAN-IN-MODELL (de-YAGNI, kein globaler Single-Stream)
-----------------------------------------------------
Weil das Format **append-only** ist (1 vollstaendiges JSON-Objekt pro Zeile,
keine zeilenuebergreifende Struktur), ist das Zusammenfuehren von N worker-lokalen
Streams eine reine **KONKATENATION der Zeilen-Mengen**. Diese Operation ist
KOMMUTATIV: das Ergebnis ist als Zeilen-Multi-Menge reihenfolge-unabhaengig
(concat(A,B) == concat(B,A) als Multiset). Darum braucht der Fan-In:
  - KEINEN Lock (kein contended Write auf einen Single-Stream),
  - KEINE Merge-Heuristik (Append-only => keine Merge-Konflikte/Konflikt-Marker),
  - KEINE globale Sammeldatei zur Schreibzeit (jeder Worker schreibt nur lokal).

Der Fan-In ist eine NACHGELAGERTE Lese-/Sammel-Operation (z.B. zum Batch-Ende
in der spaeteren BL-230-Wellen-Phase). Die Zeit-Reihenfolge laesst sich, falls
fuer Analyse gewuenscht, ueber das `ts`-Feld pro Zeile rekonstruieren — der
Fan-In selbst erzwingt KEINE Sortierung (das waere eine Praesentations-Wahl,
nicht Teil der kommutativen Concat-Semantik).

ABGRENZUNG: Die echte Merge-Strategie fuer PERSISTENTE `.claude/analysis`-Artefakte
bei N>1 Worktrees ist DEFERRED -> BL-230-Wellen-Phase (siehe BL-317_Spec.md §4).
Dieser Helper deckt NUR die volatile append-only audit-Stream-Klasse.

API
---
  fan_in_audit_streams(paths) -> list[str]
      Liest N audit.jsonl-Pfade, gibt die konkatenierte Zeilen-Liste zurueck
      (nicht-leere Zeilen, in Eingabe-Reihenfolge der Pfade; Ergebnis-Multiset
      reihenfolge-unabhaengig). Fehlende/leere Dateien -> robust uebersprungen.

  fan_in_to_file(paths, out_path, append=False) -> int
      Wie oben, schreibt das Ergebnis als gueltiges append-only JSONL nach
      out_path. append=True haengt an einen bestehenden Stream an (akkumulierend).
      Gibt die Anzahl geschriebener Zeilen zurueck.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Union

PathLike = Union[str, Path]


def _read_lines(path: PathLike) -> List[str]:
    """Liest nicht-leere Zeilen einer audit.jsonl. Fehlend/leer -> []. Robust."""
    p = Path(path)
    try:
        if not p.exists() or not p.is_file():
            return []
        text = p.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        # Volatiler Stream — Fan-In darf NIE crashen (kein Block-Risiko, AK-4).
        return []
    return [line for line in text.splitlines() if line.strip()]


def fan_in_audit_streams(paths: Iterable[PathLike]) -> List[str]:
    """Konkateniert N worker-lokale audit.jsonl-Streams (append-only, kommutativ).

    Args:
        paths: Iterable von audit.jsonl-Pfaden (worker-lokal).

    Returns:
        Liste der nicht-leeren JSONL-Zeilen aller Quellen. In Pfad-Eingabe-
        Reihenfolge konkateniert; als Zeilen-Multi-Menge reihenfolge-unabhaengig
        (Kommutativitaet). Fehlende/leere Quellen werden robust uebersprungen.
    """
    merged: List[str] = []
    for path in paths:
        merged.extend(_read_lines(path))
    return merged


def fan_in_to_file(
    paths: Iterable[PathLike],
    out_path: PathLike,
    append: bool = False,
) -> int:
    """Fan-In nach out_path als gueltiges append-only JSONL.

    Args:
        paths: worker-lokale audit.jsonl-Quellen.
        out_path: Ziel-Stream (wird angelegt; Parent-Dir wird erstellt).
        append: True -> an bestehenden out_path anhaengen (akkumulierend,
                append-only). False -> out_path neu schreiben.

    Returns:
        Anzahl der in DIESEM Aufruf geschriebenen Zeilen.
    """
    lines = fan_in_audit_streams(paths)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if append else "w"
    with open(out, mode, encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    return len(lines)


def _cli(argv: List[str]) -> int:
    """CLI: audit_fanin.py [--out OUT] [--append] STREAM1 STREAM2 ...

    Ohne --out: konkatenierte Zeilen nach stdout (append-only JSONL).
    Mit --out: Fan-In in die Zieldatei; gibt geschriebene Zeilen-Anzahl aus.
    """
    out_path = None
    append = False
    streams: List[str] = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--out":
            i += 1
            if i >= len(argv):
                print("Fehler: --out erwartet einen Pfad", flush=True)
                return 2
            out_path = argv[i]
        elif a == "--append":
            append = True
        else:
            streams.append(a)
        i += 1

    if out_path is None:
        for line in fan_in_audit_streams(streams):
            print(line)
        return 0
    n = fan_in_to_file(streams, out_path, append=append)
    print(f"{n} Zeilen -> {out_path}")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(_cli(sys.argv[1:]))
