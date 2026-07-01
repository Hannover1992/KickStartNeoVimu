#!/usr/bin/env python3
"""vault_drift_check.py — BL-446 AK-3/AK-4: READ-ONLY Drift-Check fuer Vault-Edges.

Erkennt disconnected Artefakte: *.md-Dateien in einem BL-Ordner, die KEINEN
Backlink auf den Sibling-Root (Hub) tragen. Ein Artefakt gilt als verschaltet,
wenn es eine der beiden Backlink-Formen besitzt (wie vault_bl_edges sie schreibt):

  - Frontmatter-Feld `bl_root: "[[Backlog/BL-XXX-slug/BL-XXX-slug]]"`
  - Header-Zeile  `> Teil von [[Backlog/BL-XXX-slug/BL-XXX-slug]]`

READ-ONLY: dieses Modul mutiert NIE eine Datei (INV-QUALITY-3, DoD-3.5).

API:
  report_disconnected(backlog_root) -> {"disconnected": [Path, ...], "count": int}
  class DriftCheckBerater(BaseQualityBerater)  (check_type="drift_check")
      run_checks(bl_id, data, auto_fix=False) -> QualityResult
      data["backlog_root"] = Backlog-Ordner

Exit-Codes (INV-QUALITY-1):
  0 = PASS (kein Drift)
  1 = WARN (Drift gefunden)
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from quality_berater_base import (
    BaseQualityBerater,
    QualityResult,
    SEVERITY_WARN,
)

# Backlink-Marker — exakt das, was vault_bl_edges schreibt (Speiche->Hub).
_BL_ROOT_FIELD = re.compile(r"^\s*bl_root\s*:", re.MULTILINE)
_TEIL_VON_HEADER = re.compile(r"^\s*>\s*Teil von\s*\[\[", re.MULTILINE)

# Dateien, die KEINE Artefakte sind (Sibling-Root liegt ohnehin neben dem Ordner).
_NON_ARTEFACT_NAMES = {"_manifest.md"}


# ---------------------------------------------------------------------------
# Backlink-Erkennung
# ---------------------------------------------------------------------------

def _has_backlink(content: str) -> bool:
    """True wenn das Artefakt einen Hub-Backlink traegt (Frontmatter ODER Header)."""
    return bool(_BL_ROOT_FIELD.search(content) or _TEIL_VON_HEADER.search(content))


def _iter_bl_folders(backlog_root: Path):
    """Direkte Kind-Ordner von backlog_root, die wie ein BL-Ordner aussehen (BL-XXX-...)."""
    if not backlog_root.is_dir():
        return
    for entry in sorted(backlog_root.iterdir()):
        if not entry.is_dir():
            continue
        name = entry.name
        parts = name.split("-")
        if len(parts) >= 2 and parts[0].isalpha() and parts[1].isdigit():
            yield entry


def _iter_artefacts(bl_folder: Path):
    """Alle *.md-Artefakte rekursiv im BL-Ordner (ohne _manifest.md, ohne Hub-Root).

    Der Root-Hub heisst {folder_name}.md (z.B. BL-903-connected/BL-903-connected.md).
    Er ist der Hub (traegt ## Artefakte, nie einen bl_root-Backlink) und KEIN Artefakt
    — daher ausgeschlossen, egal ob er im Ordner oder daneben liegt.
    """
    root_hub_name = f"{bl_folder.name}.md"
    for p in sorted(bl_folder.rglob("*.md")):
        if not p.is_file():
            continue
        if p.name in _NON_ARTEFACT_NAMES:
            continue
        # Hub-Root direkt im BL-Ordner -> kein Artefakt.
        if p.name == root_hub_name and p.parent == bl_folder:
            continue
        yield p


# ---------------------------------------------------------------------------
# Public: report_disconnected (READ-ONLY)
# ---------------------------------------------------------------------------

def report_disconnected(backlog_root: str | Path) -> dict:
    """Findet alle disconnected Artefakte unter backlog_root.

    Ein Artefakt ist disconnected, wenn es KEINEN Hub-Backlink traegt
    (weder `bl_root:`-Frontmatter noch `> Teil von [[..]]`-Header).

    READ-ONLY — keine Mutation. Returns {"disconnected": [Path, ...], "count": int}.
    Nicht existierender / leerer Backlog -> count = 0.
    """
    backlog_root = Path(backlog_root)
    disconnected: list[Path] = []

    for bl_folder in _iter_bl_folders(backlog_root):
        for artefact in _iter_artefacts(bl_folder):
            try:
                content = artefact.read_text(encoding="utf-8")
            except OSError:
                continue
            if not _has_backlink(content):
                disconnected.append(artefact)

    return {"disconnected": disconnected, "count": len(disconnected)}


# ---------------------------------------------------------------------------
# DriftCheckBerater (Framework-Reuse)
# ---------------------------------------------------------------------------

class DriftCheckBerater(BaseQualityBerater):
    """Quality-Berater fuer Vault-Edge-Drift.

    data dict expected keys:
        backlog_root (str|Path) — Backlog-Ordner (Pflicht)
        vault_root   (str|Path) — optional, fuer Ableitung (ungenutzt: backlog_root reicht)

    Pro disconnected Artefakt ein WARN-Finding. exit_code = 1 (WARN) bei Drift,
    0 (PASS) bei Drift = 0.
    """

    check_type = "drift_check"

    def run_checks(self, bl_id: str, data: dict, auto_fix: bool = False) -> QualityResult:
        result = QualityResult(bl_id=bl_id, check_type=self.check_type)

        backlog_root = data.get("backlog_root")
        if backlog_root is None:
            vault_root = data.get("vault_root")
            if vault_root is not None:
                backlog_root = Path(vault_root) / "Backlog"

        if backlog_root is None:
            return result

        report = report_disconnected(backlog_root)
        for artefact in report["disconnected"]:
            result.add_finding(self.warn(
                f"Disconnected Artefakt ohne Hub-Backlink: {artefact}",
                field="bl_root",
                fix=f"Edge setzen via vault_edge_link / migrate_bl_edges fuer {artefact}",
            ))
        return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="BL-446 Vault Drift Check (READ-ONLY)")
    parser.add_argument("--backlog", required=True, help="Backlog-Ordner")
    parser.add_argument("--bl", default="BL-DRIFT", help="BL-ID fuer Audit-Trail")
    args = parser.parse_args()

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    berater = DriftCheckBerater(repo_root=repo_root)
    result = berater.run(bl_id=args.bl, data={"backlog_root": args.backlog})
    berater.write_output(result)
    return result.exit_code


if __name__ == "__main__":
    sys.exit(main())
