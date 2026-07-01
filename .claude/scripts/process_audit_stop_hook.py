#!/usr/bin/env python3
"""
Stop-Hook: Process-Audit-Gate (BL-RCA-486-Round11, 2026-05-27).

Bei JEDEM Stop-Event (Goal-Termination, normaler Turn-Ende):
  1. Scanne `git status` nach modifizierten BL-Folder-Manifesten
  2. Pro Manifest: rufe process_audit.py mit --bl-folder + --round=auto auf
  3. Wenn EINER der Scans RED zurueckgibt → blockiere Stop mit Begruendung
  4. Wenn YELLOW → Warning aber durchlassen

OMNI_PROCESS_AUDIT_ENFORCE Env-Var:
  =0 (default): Warning-Only Mode (kompatibel mit existierenden Workflows)
  =1: Hard-Block bei RED
  =off: Hook deaktiviert

JSON-Hook-Response:
  {"continue": true}  -> Stop erlaubt
  {"continue": false, "message": "..."} -> Stop blockiert (Goal-Hook bleibt offen)
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
PROCESS_AUDIT = SCRIPT_DIR / "process_audit.py"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"


def log_debug(msg):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] process_audit_stop_hook: {msg}\n")
    except Exception:
        pass


def find_modified_bl_folders():
    """Scannt git status nach modifizierten BL-Folder-Manifesten.

    Returns: list of (bl_folder_path, round_n) tuples
    """
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(ROOT_DIR), timeout=10
        )
        if result.returncode != 0:
            return []
    except Exception as e:
        log_debug(f"git status failed: {e}")
        return []

    bl_folders = set()
    for line in result.stdout.splitlines():
        # Format: ' M path/to/_manifest.md' oder '?? ...'
        m = re.match(r"^\s*[\?MA]+\s+(.+_manifest\.md)\s*$", line)
        if m:
            manifest_path = Path(m.group(1))
            bl_folder = (ROOT_DIR / manifest_path).parent
            if bl_folder.exists():
                bl_folders.add(bl_folder)

    # Pro Folder: ermittele Round aus Manifest-Inhalt (max round Z?)
    results = []
    for bl_folder in bl_folders:
        round_n = _detect_round_from_manifest(bl_folder / "_manifest.md")
        results.append((str(bl_folder), round_n))
    return results


def _detect_round_from_manifest(manifest_path):
    """Heuristik: max `round_N` Mention im Manifest = aktuelle Round."""
    try:
        content = manifest_path.read_text(encoding="utf-8", errors="replace")
        rounds = re.findall(r"round_?(\d+)|Round\s+(\d+)|round=(\d+)", content)
        nums = [int(g[0] or g[1] or g[2]) for g in rounds if any(g)]
        if nums:
            return max(nums)
    except Exception:
        pass
    return 1  # default


def run_process_audit(bl_folder, round_n):
    """Rufe process_audit.py + parse JSON-Output."""
    try:
        result = subprocess.run(
            [sys.executable, str(PROCESS_AUDIT),
             "--bl-folder", bl_folder,
             "--round", str(round_n),
             "--json"],
            capture_output=True, text=True, timeout=30
        )
        if result.stdout:
            return json.loads(result.stdout)
    except Exception as e:
        log_debug(f"process_audit run failed for {bl_folder}: {e}")
    return None


def main():
    enforce_mode = os.environ.get("OMNI_PROCESS_AUDIT_ENFORCE", "0")

    if enforce_mode == "off":
        print(json.dumps({"continue": True}))
        return

    try:
        # Hook-Input ignorieren (Stop-Hook braucht keinen Input-Parse)
        _ = sys.stdin.read()
    except Exception:
        pass

    bl_folders = find_modified_bl_folders()
    if not bl_folders:
        # Keine BL-Manifeste modifiziert → kein Audit noetig
        print(json.dumps({"continue": True}))
        return

    red_findings = []
    yellow_findings = []
    for bl_folder, round_n in bl_folders:
        audit = run_process_audit(bl_folder, round_n)
        if not audit:
            continue
        if audit.get("verdict") == "RED":
            red_findings.append((bl_folder, round_n, audit.get("findings", [])))
        elif audit.get("verdict") == "YELLOW":
            yellow_findings.append((bl_folder, round_n, audit.get("findings", [])))

    if red_findings and enforce_mode == "1":
        # Hard-Block
        msgs = []
        for bl_folder, round_n, findings in red_findings:
            crit = [f for f in findings if f.get("severity") == "CRITICAL"]
            msgs.append(f"{Path(bl_folder).name} Round {round_n}: {len(crit)} CRITICAL "
                        + ", ".join(f["rule"] for f in crit))
        message = (
            f"[PROCESS-AUDIT-BLOCK] Stop blockiert — {len(red_findings)} BL(s) mit Process-RED. "
            f"Details: {' | '.join(msgs)}. "
            f"Beheben via process_audit.py oder OMNI_PROCESS_AUDIT_ENFORCE=0 setzen."
        )
        log_debug(f"BLOCKED: {message}")
        print(json.dumps({"continue": False, "message": message}))
        return

    if red_findings or yellow_findings:
        # Warning-Mode: durchlassen mit Notiz
        summary = (
            f"[PROCESS-AUDIT-WARN] {len(red_findings)} RED + {len(yellow_findings)} YELLOW "
            f"BL(s) — siehe process_audit.py-Output. (set OMNI_PROCESS_AUDIT_ENFORCE=1 fuer Block)"
        )
        log_debug(f"WARN: {summary}")
        # continue:true mit warning Message
        print(json.dumps({"continue": True, "message": summary}))
        return

    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
