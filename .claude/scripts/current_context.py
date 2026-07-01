#!/usr/bin/env python3
"""
current_context.py — Worker-Awareness Helper (BL-151 NEW-K2-essenziell).

Liefert dem Worker auf einen Blick:
  - branch:     git branch --show-current
  - bl_id:      aktives BL-Item (aus working_dir-Feld in vault-routing oder Heuristik)
  - vault_root: via resolve_vault_root.py
  - bl_folder:  via resolve_bl_path.py wenn bl_id bekannt
  - cwd:        aktuelles Arbeitsverzeichnis

BL-173 AK-4: Manifest-Pfad-Resolver (neue Felder):
  - factory_manifest_path:   {vault_root}/_factory_manifest.md (immer berechnet)
  - factory_manifest_exists: bool, ob Datei existiert
  - bl_manifest_path:        {bl_folder}/_manifest.md (nur wenn bl_id bekannt)
  - bl_manifest_exists:      bool, ob BL-Manifest existiert
  - legacy_manifest_path:    {vault_root}/_manifest.md (Backward-Compat bis BL-172 done)
  - manifest_mode:           "split" wenn _factory_manifest.md existiert, sonst "legacy"

Deprecation: legacy_manifest_path wird nach BL-172 Migration via eigenem BL entfernt.

Auflage-Reihenfolge fuer bl_id:
  1. ENV var CLAUDE_BL_ID            (explizit gesetzt von Orchestrator)
  2. Branch-Name parsen: feature/BL-{N}-* → BL-{N}
  3. Branch-Name parsen: feature/{PREFIX}-{N}-* → {PREFIX}-{N} (Jira/DCSRE)
  4. None (Worker nicht an BL-Item gebunden, z.B. Standalone-Skript)

Aufruf:
  python3 .claude/scripts/current_context.py [--format=json|kv]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_BRANCH_BL_PATTERN = re.compile(r"(?:^|/)([A-Z][A-Z0-9_]*-\d+)(?:[-_]|$)")

# BL-317 AK-2b: Motor-Branch-Worktree-Suffix-Schema. Der Workflow-Motor haengt an
# einen Branch-Namen einen Batch/Worktree-Suffix der Form "_B-<N>" an (z.B.
# feature/BL-317-haertung_B-3). Dieser Suffix ist KEINE bl_id und darf NIE als
# solche missdeutet werden. ADDITIV: wird vor dem bl_id-Match abgeschnitten,
# sodass bestehende BL-{N}/{PREFIX}-{N}-Treffer NICHT regredieren.
_MOTOR_SUFFIX_PATTERN = re.compile(r"_B-\d+$")
# Ein "B-<N>"-Token (allein oder als isoliertes Pfad-Segment) ist immer der
# Motor-Suffix, nie eine bl_id — schuetzt vor Misdeutung wenn der Suffix als
# fuehrendes Segment/ganzer Branch auftaucht (z.B. "B-3", "feature/B-3-worktree").
_BARE_MOTOR_PATTERN = re.compile(r"^B-\d+$")

# BL-317 AK-2a: __file__-Anker statt rel. cwd-String. current_context.py liegt
# unter <repo-root>/.claude/scripts/ — parents[2] ist die Repo-Root, parents[0]
# das scripts-Verzeichnis. Die Helfer-Skripte (resolve_vault_root.py /
# resolve_bl_path.py) werden ueber ihren ABSOLUTEN Pfad aufgerufen UND mit
# cwd=Repo-Root, sodass die Aufloesung bei CWD!=Repo-Root NICHT mehr still bricht
# (vorher: rel. ".claude/scripts/..." fand das Skript nicht -> null-Felder ->
# BL-310-Klasse). Der cwd-FELD-Wert bleibt unveraendert das echte os.getcwd().
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent.parent
_RESOLVE_VAULT_ROOT = _SCRIPT_DIR / "resolve_vault_root.py"
_RESOLVE_BL_PATH = _SCRIPT_DIR / "resolve_bl_path.py"


def _git_branch() -> str | None:
    try:
        out = subprocess.run(
            ["git", "branch", "--show-current"],
            capture_output=True, text=True, timeout=3,
        )
        if out.returncode == 0:
            return out.stdout.strip() or None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _resolve_vault_root() -> str | None:
    try:
        out = subprocess.run(
            [sys.executable, str(_RESOLVE_VAULT_ROOT)],
            capture_output=True, text=True, timeout=5,
            cwd=str(_REPO_ROOT),
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def _resolve_bl_folder(bl_id: str) -> str | None:
    try:
        out = subprocess.run(
            [sys.executable, str(_RESOLVE_BL_PATH), bl_id],
            capture_output=True, text=True, timeout=5,
            cwd=str(_REPO_ROOT),
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return None


def detect_bl_id(branch: str | None) -> str | None:
    env = os.environ.get("CLAUDE_BL_ID")
    if env:
        return env
    if branch:
        # BL-317 AK-2b (ADDITIV): den Motor-Worktree-Suffix "_B-<N>" abschneiden,
        # bevor die bl_id extrahiert wird — sodass {slug}_B-N die ECHTE bl_id aus
        # dem Slug liefert und der Suffix nie als bl_id durchschlaegt.
        candidate = _MOTOR_SUFFIX_PATTERN.sub("", branch)
        m = _BRANCH_BL_PATTERN.search(candidate)
        if m:
            token = m.group(1)
            # Ein isolierter "B-<N>"-Token ist der Motor-Suffix, keine bl_id.
            if not _BARE_MOTOR_PATTERN.match(token):
                return token
    return None


def _resolve_manifest_paths(vault_root: str | None, bl_folder: str | None) -> dict:
    """
    BL-173 AK-4: Berechnet alle Manifest-Pfade und Existenz-Flags.

    Returns:
        dict mit factory_manifest_path, factory_manifest_exists,
        bl_manifest_path, bl_manifest_exists,
        legacy_manifest_path, manifest_mode
    """
    result: dict = {}

    # factory_manifest_path: immer berechnet (kein BL-Kontext noetig)
    if vault_root:
        factory_path = Path(vault_root) / "_factory_manifest.md"
        result["factory_manifest_path"] = str(factory_path)
        result["factory_manifest_exists"] = factory_path.exists()
        # legacy_manifest_path: Backward-Compat bis BL-172 Migration abgeschlossen
        # DEPRECATION-WARNING: wird via eigenem BL (BL-177 o.ae.) entfernt
        legacy_path = Path(vault_root) / "_manifest.md"
        result["legacy_manifest_path"] = str(legacy_path)
        # manifest_mode: "split" wenn _factory_manifest.md existiert, sonst "legacy"
        result["manifest_mode"] = "split" if factory_path.exists() else "legacy"
        if result["manifest_mode"] == "legacy" and legacy_path.exists():
            import sys as _sys
            print(
                "[DEPRECATION] legacy_manifest_path aktiv: _manifest.md noch nicht gesplittet. "
                "Bitte BL-173 AK-2 migrate_manifest_split.py ausfuehren.",
                file=_sys.stderr,
            )
    else:
        result["factory_manifest_path"] = None
        result["factory_manifest_exists"] = False
        result["legacy_manifest_path"] = None
        result["manifest_mode"] = "unknown"

    # bl_manifest_path: nur wenn bl_folder bekannt
    if bl_folder:
        bl_manifest = Path(bl_folder) / "_manifest.md"
        result["bl_manifest_path"] = str(bl_manifest)
        result["bl_manifest_exists"] = bl_manifest.exists()
    else:
        result["bl_manifest_path"] = None
        result["bl_manifest_exists"] = False

    return result


def gather() -> dict:
    branch = _git_branch()
    vault_root = _resolve_vault_root()
    bl_id = detect_bl_id(branch)
    bl_folder = _resolve_bl_folder(bl_id) if bl_id else None

    manifest_info = _resolve_manifest_paths(vault_root, bl_folder)

    # BL-210 M2 + Iter 2 R1 Fix 2026-05-24: project_name ergaenzen (basierend auf vault_root oder cwd).
    # Vorher: Feld fehlte — _backlog.md M2-Fix verwendete Fallback "OmniCommand" als Default.
    # Jetzt: project_name aus vault_root extrahiert (letzter Pfad-Teil) oder cwd-Heuristik.
    project_name = None
    if vault_root:
        # vault_root ist typischerweise .../OmniCommand oder .../DCS/DCSRE
        project_name = os.path.basename(os.path.normpath(vault_root))
    if not project_name:
        # Fallback: cwd-Heuristik (suche bekannte Marker im Pfad)
        cwd = os.getcwd()
        for marker in ["OmniCommand", "DCSRE", "DCS"]:
            if marker in cwd:
                project_name = marker
                break
    if not project_name:
        project_name = "Unknown"

    ctx = {
        "branch": branch,
        "bl_id": bl_id,
        "vault_root": vault_root,
        "bl_folder": bl_folder,
        "cwd": os.getcwd(),
        "project_name": project_name,
    }
    ctx.update(manifest_info)
    return ctx


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(description="Worker-Awareness Context Helper")
    p.add_argument("--format", choices=["json", "kv"], default="kv")
    args = p.parse_args(argv[1:])

    # ROBUSTHEIT (BL-RESILIENZ 2026-05-29): gather() darf NIE leeren/non-JSON-stdout
    # verursachen. Ein still gecrashter Subprozess fuehrte sonst zu leerem stdout ->
    # _manifest_resolver._read_context() bekam JSONDecodeError (line 1 col 0) -> Guards
    # (geist5/6/9, STAB10-B) konnten das Manifest NICHT aufloesen -> Prozess-Stall am
    # IDF->SDF-Handover. stdout ist jetzt IMMER valides JSON (Fallback = alle Felder null).
    try:
        ctx = gather()
    except Exception as e:
        ctx = {
            "branch": None, "bl_id": None, "vault_root": None, "bl_folder": None,
            "cwd": None, "project_name": "Unknown",
            "factory_manifest_path": None, "factory_manifest_exists": False,
            "bl_manifest_path": None, "bl_manifest_exists": False,
            "legacy_manifest_path": None, "manifest_mode": "unknown",
            "_error": f"gather() failed: {type(e).__name__}: {e}",
        }
        try:
            ctx["cwd"] = os.getcwd()
        except Exception:
            pass

    if args.format == "json":
        json.dump(ctx, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
    else:
        for k, v in ctx.items():
            sys.stdout.write(f"{k}={v if v is not None else ''}\n")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except SystemExit:
        raise
    except Exception:
        # Letzte Verteidigung: NIE leerer stdout. Valides leeres JSON statt Traceback-only.
        try:
            sys.stdout.write("{}\n")
        except Exception:
            pass
        sys.exit(0)
