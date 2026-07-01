#!/usr/bin/env python3
"""_dual_read_manifest.py — BL-229 AK-F: Consumer-Dual-Read-Helper.

Compliance-Greps (process_audit, geist9/9b/7c, manifest_reader) lasen bisher
AUSSCHLIESSLICH den Manifest-Body. Nach dem State-vs-Report-Split (BL-229) lebt
ausgelagerter Inhalt aber NICHT mehr inline:
  - AK-B Pointer: BERATER_OUTPUTS-Payload wandert in 6_PL/BERATER_OUTPUTS/*.md
    (im Manifest bleibt nur ein 1-Zeilen-Pointer).
  - AK-C Offload: fruehere-Round State-Familien-Snapshots wandern in
    _manifest_history_{date}.md (im Manifest bleibt nur die letzte Round).

INV-POINTER-1: Der gelesene Inhalt ist inhaltlich identisch — egal ob inline,
ueber Pointer ausgelagert ODER in die History offloaded. Dieser Helper liefert
den UNION-Heuhaufen (Manifest + History + Pointer-Bodies), sodass eine
bestehende Grep auf dem Union weiterhin Treffer findet und KEIN False-Negative
liefert (process_audit RED-bei-False-Negative, geist Block/Stall).

ADDITIV (BL-229 AK-F, 2026-06-10): Die alte Inline-Lesung bleibt 1:1 erhalten
(der Manifest-Text ist immer Teil des Union). Die Pointer-/History-Lesung kommt
NUR additiv hinzu. Enforcement-Semantik der Konsumenten bleibt unveraendert —
es weitet sich allein die LESE-Quelle.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

# Wo AK-B die Pointer-Payloads ablegt (relativ zum BL-Folder).
_POINTER_DIR = ("6_PL", "BERATER_OUTPUTS")
# AK-C-Offload-Archiv (per-BL neben dem Manifest).
_HISTORY_GLOB = "_manifest_history_*.md"


def collect_offloaded_text(bl_folder: Optional[Path]) -> str:
    """Konkateniert alle ausgelagerten Report-/History-Bodies eines BL-Folders.

    Quellen (additiv, BL-229 AK-F):
      1. _manifest_history_{date}.md           (AK-C Round-Offload)
      2. 6_PL/BERATER_OUTPUTS/*.md             (AK-B Pointer-Payloads)

    Fehlende Dateien/Ordner -> leerer Beitrag (kein Fehler). Gibt "" zurueck wenn
    bl_folder None ist oder nichts ausgelagert wurde.
    """
    if bl_folder is None:
        return ""
    bl_folder = Path(bl_folder)
    parts: list[str] = []

    # 1. AK-C History-Archive (es koennen mehrere Daten existieren)
    try:
        for hist in sorted(bl_folder.glob(_HISTORY_GLOB)):
            try:
                parts.append(hist.read_text(encoding="utf-8", errors="replace"))
            except Exception:
                continue
    except Exception:
        pass

    # 2. AK-B Pointer-Payloads
    pointer_dir = bl_folder.joinpath(*_POINTER_DIR)
    try:
        if pointer_dir.is_dir():
            for content_file in sorted(pointer_dir.glob("*.md")):
                try:
                    parts.append(content_file.read_text(encoding="utf-8", errors="replace"))
                except Exception:
                    continue
    except Exception:
        pass

    return "\n".join(parts)


def _resolve_bl_folder(manifest_path: Optional[Path], bl_folder: Optional[Path]) -> Optional[Path]:
    """BL-Folder bestimmen: expliziter Param hat Vorrang, sonst Manifest-Parent."""
    if bl_folder is not None:
        return Path(bl_folder)
    if manifest_path is not None:
        return Path(manifest_path).parent
    return None


def dual_read_text(
    manifest_text: str,
    manifest_path: Optional[Path] = None,
    bl_folder: Optional[Path] = None,
) -> str:
    """Union-Heuhaufen: Manifest-Body + ausgelagerte History-/Pointer-Bodies.

    INV-POINTER-1: inhaltlich identisch egal ob inline/pointer/offloaded. Eine
    bestehende Grep auf dem Rueckgabe-String findet weiterhin Treffer, auch wenn
    der gesuchte Inhalt durch den Split ausgelagert wurde.

    (BL-229 AK-F, 2026-06-10)
    """
    folder = _resolve_bl_folder(manifest_path, bl_folder)
    offloaded = collect_offloaded_text(folder)
    if not offloaded:
        return manifest_text  # nichts ausgelagert -> reine Inline-Lesung (Backward-Compat)
    return manifest_text + "\n" + offloaded


def read_manifest_dual(
    manifest_path: Path,
    bl_folder: Optional[Path] = None,
) -> Tuple[str, str]:
    """Liest Manifest + Union-Heuhaufen vom Pfad.

    -> (manifest_text, dual_text). manifest_text ist der reine Manifest-Body
    (fuer Greps die strikt nur das Manifest betrachten muessen), dual_text der
    Union (fuer die Dual-Read-aware Greps). (BL-229 AK-F, 2026-06-10)
    """
    manifest_path = Path(manifest_path)
    if not manifest_path.exists():
        manifest_text = ""
    else:
        manifest_text = manifest_path.read_text(encoding="utf-8", errors="replace")
    folder = bl_folder if bl_folder is not None else manifest_path.parent
    return manifest_text, dual_read_text(manifest_text, manifest_path, folder)
