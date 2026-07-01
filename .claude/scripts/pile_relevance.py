#!/usr/bin/env python3
"""
pile_relevance.py - BL-346 AK-1: pileOfMud-Relevanz-Gate fuer A-Pipeline Phase 0.5

Problem (BL-346): findingsExtraction iteriert `.claude/pileOfMud/*` als BL-Quelle, OHNE
zu pruefen ob die Live-Files zum aktiven BL gehoeren. Live-Fall 2026-06-14: BL-282-Launch -
pileOfMud enthielt 5 BL-282-UNVERWANDTE Files (anderer Sessions) -> haette sie als
BL-282-Findings mis-extrahiert (Garbage).

Relevanz-Wahrheit: `/_backlog` snapshotted die fuer DIESEN BL gedroppten Pile-Files nach
`{bl_folder}/Sources/_pileOfMud_snapshot/` MIT source_provenance.original_hash (SHA-256 des
Originals). Die fuer den BL relevanten Live-Pile-Files sind genau die, deren Basename (und,
wenn vorhanden, Inhalts-Hash) im Snapshot wiedergefunden wird. Alles andere ist Fremd-Material
einer anderen Session und wird LAUT gemeldet + geskippt ("No silent caps").

ABWAERTSKOMPATIBEL: ein frisches Intake-BL (Snapshot = die eben gedroppten Files) laeuft
unveraendert - seine Live-Files sind name+hash-identisch zum Snapshot, also alle relevant.

AK-2-Carve-Out (mature consolidated EPIC): ein BL mit 0 relevanten Pile-Files ABER reichem
in-Node-AK-Inhalt + superseded-Sources (z.B. BL-282) ist KEIN frisches Intake. Seine Quelle
sind Node + superseded Nodes, NICHT fremder pileOfMud. `is_mature_consolidated_epic(...)`
liefert das Routing-Signal fuer _A_orchestrate (Node-Quelle statt Garbage-Extract).

Aufruf (optional als CLI; primaer als importierbarer Helper):
    py -3 pile_relevance.py partition <bl_id_or_folder> <live_pile_dir> [--json]

Exit-Codes (CLI):
    0  OK (mind. 1 relevante Datei ODER leerer Live-Pile)
    1  WARN (0 relevant, aber Fremd-Material vorhanden -> nichts extrahieren)
    2  USAGE / Fehler
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

SNAPSHOT_SUBFOLDER = "Sources/_pileOfMud_snapshot"
# Extrahierbar (Spiegel von _A_orchestrate Phase 0.5 EXTRACTABLE_EXT)
_EXTRACTABLE_EXT = (".md", ".txt", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".pdf")


def _snapshot_dir(bl_folder: Path) -> Path:
    return bl_folder / SNAPSHOT_SUBFOLDER


def _is_extractable(name: str) -> bool:
    return name.lower().endswith(_EXTRACTABLE_EXT)


def _file_sha256(path: Path) -> str | None:
    """SHA-256 des Datei-INHALTS (Bytes). None bei Lesefehler."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


_HASH_RE = re.compile(r"^\s*original_hash:\s*([0-9a-fA-F]{64})\s*$", re.MULTILINE)


def _snapshot_original_hash(snap_file: Path) -> str | None:
    """Liest source_provenance.original_hash aus dem Snapshot-Frontmatter.

    Robust gegen YAML-frei: ein einfaches Regex auf das 64-Hex-Feld (das /_backlog
    AK-2 schreibt). None wenn nicht vorhanden (legacy / pre-BL-160 Snapshot).
    """
    try:
        text = snap_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    fm = text[3:end] if end != -1 else text
    m = _HASH_RE.search(fm)
    return m.group(1).lower() if m else None


def _build_snapshot_index(bl_folder: Path) -> dict[str, str | None]:
    """basename(lower) -> original_hash (oder None bei legacy ohne Hash).

    Leer wenn kein Snapshot-Ordner / keine extrahierbaren Snapshot-Files existieren.
    """
    snap_dir = _snapshot_dir(bl_folder)
    index: dict[str, str | None] = {}
    if not snap_dir.is_dir():
        return index
    for f in sorted(snap_dir.iterdir()):
        if not f.is_file():
            continue
        if not _is_extractable(f.name):
            continue
        index[f.name.lower()] = _snapshot_original_hash(f)
    return index


def partition_pile_by_relevance(bl_folder: str | Path, pile_files) -> dict:
    """Partitioniert Live-pileOfMud-Files in relevant / foreign fuer den BL.

    Relevanz-Regeln:
      - Kein Snapshot-Ordner (oder leer) -> KEINE Live-Datei ist beweisbar relevant.
        Alle -> foreign (skip_reason="no_snapshot"). Fall BL-282 (consolidated EPIC).
      - Snapshot vorhanden:
          * Basename matcht KEINEN Snapshot-Eintrag -> foreign ("not_in_snapshot").
          * Basename matcht UND Snapshot hat original_hash:
                - Live-Inhalts-Hash == Snapshot-Hash -> relevant.
                - Hash weicht ab -> foreign ("content_drift": andere Version als der
                  fuer diesen BL gefrorene Snapshot).
          * Basename matcht UND Snapshot hat KEINEN Hash (legacy) -> relevant
            (Name-Match genuegt, kein Hash zum Vergleichen).

    Args:
        bl_folder: BL-Vault-Ordner (Pfad) - Heimat des Sources/_pileOfMud_snapshot/.
        pile_files: Iterable von Live-pileOfMud-Pfaden (z.B. Glob-Ergebnis).

    Returns:
        {
          relevant: [str, ...],                       # Pfade, die extrahiert werden duerfen
          foreign:  [{path: str, skip_reason: str}],  # geskippt + LAUT gemeldet
          snapshot_present: bool,
          snapshot_count: int,
        }
    """
    bl_folder = Path(bl_folder)
    snap_index = _build_snapshot_index(bl_folder)
    snapshot_present = len(snap_index) > 0

    relevant: list[str] = []
    foreign: list[dict] = []

    for raw in pile_files:
        f = Path(raw)
        name = f.name.lower()
        if not snapshot_present:
            foreign.append({
                "path": str(f),
                "skip_reason": "no_snapshot: kein Sources/_pileOfMud_snapshot/ fuer "
                               "diesen BL - Live-Pile NICHT diesem BL zuordenbar "
                               "(fremde Session / consolidated EPIC).",
            })
            continue
        if name not in snap_index:
            foreign.append({
                "path": str(f),
                "skip_reason": "not_in_snapshot: Basename nicht im per-BL Snapshot - "
                               "Fremd-Material einer anderen Session.",
            })
            continue
        expected_hash = snap_index[name]
        if expected_hash is None:
            # Legacy-Snapshot ohne Hash: Name-Match genuegt.
            relevant.append(str(f))
            continue
        live_hash = _file_sha256(f)
        if live_hash is not None and live_hash.lower() == expected_hash:
            relevant.append(str(f))
        else:
            foreign.append({
                "path": str(f),
                "skip_reason": "content_drift: Name im Snapshot, aber Inhalts-Hash weicht "
                               "vom gefrorenen Snapshot ab (andere Version / fremde Session).",
            })

    return {
        "relevant": relevant,
        "foreign": foreign,
        "snapshot_present": snapshot_present,
        "snapshot_count": len(snap_index),
    }


def is_mature_consolidated_epic(
    relevant_count: int,
    node_text: str | None,
    node_ak_count: int,
    has_superseded: bool,
    ak_threshold: int = 4,
) -> bool:
    """AK-2: erkennt einen reifen, konsolidierten Vault-EPIC (Carve-Out).

    Signatur eines consolidated EPIC (z.B. BL-282 merged BL-240/249/250/263):
      - 0 relevante Pile-Files (kein frisches Intake-Material), UND
      - reicher in-Node-AK-Cluster (>= ak_threshold AKs im Node), UND
      - superseded-Sources (der EPIC fasst aeltere Nodes zusammen).

    Solch ein BL routet zu Node+superseded-als-Quelle (IDF-grade Refinement) statt zu
    pileOfMud-Findings-Extraktion. KEIN Garbage-Extract aus fremdem Pile.

    Ein frischer Pile-BL (relevant_count > 0) ist NIE ein consolidated EPIC.
    """
    if relevant_count > 0:
        return False
    if not has_superseded:
        return False
    if node_ak_count < ak_threshold:
        return False
    # node_text optional als zusaetzliches Plausibilitaets-Signal (nicht-leer).
    if node_text is not None and not node_text.strip():
        return False
    return True


def _resolve_bl_folder(bl_arg: str) -> Path:
    """CLI-Helper: akzeptiert entweder einen Ordner-Pfad ODER eine BL-ID."""
    p = Path(bl_arg)
    if p.is_dir():
        return p
    # BL-ID -> resolve_bl_path (cwd-stabil: Script-Dir auf sys.path)
    script_dir = Path(__file__).parent.resolve()
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    try:
        from resolve_bl_path import resolve_bl_path  # type: ignore
    except ImportError as exc:  # pragma: no cover - defensiv
        raise FileNotFoundError(f"resolve_bl_path nicht importierbar: {exc}") from exc
    return resolve_bl_path(bl_arg)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="pile_relevance",
        description="BL-346 AK-1: pileOfMud-Relevanz-Gate (Snapshot-Provenance-Match)",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_part = sub.add_parser("partition", help="Live-Pile in relevant/foreign partitionieren")
    p_part.add_argument("bl", help="BL-ID (z.B. BL-282) ODER BL-Vault-Ordner-Pfad")
    p_part.add_argument("live_pile_dir", help="Live-pileOfMud-Verzeichnis")
    p_part.add_argument("--json", action="store_true", help="JSON-Output")
    args = parser.parse_args(argv[1:])

    if args.cmd == "partition":
        try:
            bl_folder = _resolve_bl_folder(args.bl)
        except (FileNotFoundError, RuntimeError, ValueError) as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
        live_dir = Path(args.live_pile_dir)
        if not live_dir.is_dir():
            print(f"ERROR: Live-Pile-Verzeichnis fehlt: {live_dir}", file=sys.stderr)
            return 2
        live_files = [f for f in sorted(live_dir.iterdir())
                      if f.is_file() and _is_extractable(f.name)]
        res = partition_pile_by_relevance(bl_folder, live_files)
        if args.json:
            print(json.dumps(res, indent=2, ensure_ascii=False))
        else:
            print(f"snapshot_present={res['snapshot_present']} "
                  f"snapshot_count={res['snapshot_count']}")
            print(f"relevant ({len(res['relevant'])}):")
            for p in res["relevant"]:
                print(f"  + {p}")
            if res["foreign"]:
                print(f"WARN: {len(res['foreign'])} Fremd-Pile-File(s) GESKIPPT "
                      f"(No silent caps):")
                for entry in res["foreign"]:
                    print(f"  - {entry['path']}  [{entry['skip_reason']}]")
        if not res["relevant"] and res["foreign"]:
            return 1
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
