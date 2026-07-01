#!/usr/bin/env python3
"""
sidecar_ttl.py — BL-338 / batch_PL3 / PL-338-6 (Blueprint/Sidecar-TTL, M3).

Nach Story-DONE die transienten Sidecar-Artefakte eines BL-Folders archivieren bzw.
prunen — aber NUR wenn die Story wirklich done ist (story_done=True) UND aelter als die
TTL (ttl_days). Verlustfrei: vor jedem Delete wird archiviert (lossless-Kopie); kein
Delete eines noch lebenden Working-Sets (Security-Pruefung-6-konform).

Sidecar-Patterns (PL-338-6 §Detection):
  - Blueprint_*.md          (Blueprint-Dateien)
  - *Blueprint*  (Dirs)     (Blueprint-Output-Verzeichnisse)
  - BERATER_OUTPUTS*        (Berater-Sidecar-Dateien)
NIE Working-Set: _manifest.md, 3_Spec/ (und dessen Inhalt) bleiben unangetastet.

cwd-STABILITAETS-MANDAT (PL-336-4-Lehre): find_sidecars/prune_sidecars verwenden den
uebergebenen bl_folder 1:1 (Path(bl_folder)), NIE cwd-relativ re-interpretiert.

Aufruf:
  python3 .claude/scripts/sidecar_ttl.py BL_FOLDER [--ttl-days N] [--dry-run]
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

# Sidecar-Glob-Patterns (Detection). Reihenfolge egal — Dedup ueber set().
_SIDECAR_FILE_GLOBS = ("Blueprint_*.md", "BERATER_OUTPUTS*")
_SIDECAR_DIR_SUBSTR = "blueprint"  # Dirs mit *Blueprint* (case-insensitive)

# Working-Set: NIE Sidecar (auch wenn ein Glob zufaellig matchte).
_WORKING_SET_NAMES = {"_manifest.md", "3_spec"}


def find_sidecars(bl_folder: str, patterns: list[str] | None = None) -> list:
    """Findet die Sidecar-Artefakte eines BL-Folders (Top-Level).

    Matcht Blueprint_*.md / BERATER_OUTPUTS*-Dateien + *Blueprint*-Dirs. Working-Set
    (_manifest.md, 3_Spec/) ist NIE ein Sidecar. Gibt absolute Pfade (str) zurueck.

    `patterns` (optional) ersetzt die Default-Datei-Globs (Dir-Substr bleibt). (PL-338-6)
    """
    bl = Path(bl_folder)  # 1:1 (cwd-STABIL)
    if not bl.is_dir():
        return []

    file_globs = patterns if patterns is not None else _SIDECAR_FILE_GLOBS
    found: dict[str, Path] = {}  # str(path) -> Path (Dedup)

    for entry in bl.iterdir():
        if entry.name.lower() in _WORKING_SET_NAMES:
            continue  # Working-Set ausschliessen
        if entry.is_dir():
            if _SIDECAR_DIR_SUBSTR in entry.name.lower():
                found[str(entry)] = entry
            continue
        # Datei: gegen die File-Globs matchen.
        if any(entry.match(g) for g in file_globs):
            found[str(entry)] = entry

    return [str(p) for p in found.values()]


def _age_days(path: Path) -> float:
    """Alter der Datei/des Dirs in Tagen (jetzt - mtime)."""
    return (time.time() - path.stat().st_mtime) / 86400.0


def _archive_lossless(path: Path, archive_root: Path) -> Path:
    """Verlustfreie Kopie eines Sidecars (Datei ODER Dir) ins Archiv. -> Archiv-Pfad."""
    archive_root.mkdir(parents=True, exist_ok=True)
    dest = archive_root / path.name
    if path.is_dir():
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(path, dest)
    else:
        shutil.copy2(path, dest)
    return dest


def _prune(path: Path) -> None:
    """Sidecar (Datei ODER Dir) entfernen — NUR nach erfolgtem Archiv-Aufruf."""
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def prune_sidecars(bl_folder: str, story_done: bool = True, ttl_days: int = 30,
                   dry_run: bool = False) -> dict:
    """Archiviert + prunet alte Sidecars eines BL-Folders — nur bei story_done + TTL.

    Gate-Kette (PL-338-6):
      1. story_done=False -> No-Op {archived:[], pruned:[], skipped:[...]} (G6b).
      2. Sidecar juenger als ttl_days -> skipped (Working-Set-Schutz, G6c).
      3. Sidecar aelter als ttl_days -> ERST archivieren (lossless) DANN prunen (G6d).
      4. dry_run=True -> Report, was geprunt WUERDE, ohne Delete (G6e).

    archived/pruned/skipped sind Listen von Pfaden (str). (PL-338-6, 2026-06-13)
    """
    bl = Path(bl_folder)  # 1:1 (cwd-STABIL)
    archived: list[str] = []
    pruned: list[str] = []
    skipped: list[str] = []

    sidecars = [Path(p) for p in find_sidecars(str(bl))]

    # Gate 1: nur bei abgeschlossener Story ueberhaupt prunen.
    if not story_done:
        skipped = [str(p) for p in sidecars]
        return {"archived": archived, "pruned": pruned, "skipped": skipped}

    archive_root = bl / "_sidecar_archive"

    for sc in sidecars:
        if not sc.exists():
            continue
        # Gate 2: TTL-Respekt — frisches Sidecar bleibt (Working-Set-Schutz).
        if _age_days(sc) < ttl_days:
            skipped.append(str(sc))
            continue
        # Gate 4: dry_run meldet nur, was geprunt WUERDE.
        if dry_run:
            archived.append(str(sc))
            pruned.append(str(sc))
            continue
        # Gate 3: ERST archivieren (lossless), DANN prunen.
        _archive_lossless(sc, archive_root)
        archived.append(str(sc))
        _prune(sc)
        pruned.append(str(sc))

    return {"archived": archived, "pruned": pruned, "skipped": skipped}


def _cli(argv=None) -> int:
    ap = argparse.ArgumentParser(description="BL-338 sidecar_ttl — Blueprint/Sidecar-TTL-Prune")
    ap.add_argument("bl_folder")
    ap.add_argument("--ttl-days", type=int, default=30)
    ap.add_argument("--not-done", action="store_true", help="story_done=False erzwingen (No-Op)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    result = prune_sidecars(
        args.bl_folder, story_done=not args.not_done,
        ttl_days=args.ttl_days, dry_run=args.dry_run,
    )
    tag = "DRY-RUN" if args.dry_run else "DONE"
    print(f"[SIDECAR-TTL {tag}] {args.bl_folder}: archived={len(result['archived'])} "
          f"pruned={len(result['pruned'])} skipped={len(result['skipped'])}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())
