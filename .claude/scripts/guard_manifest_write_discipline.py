#!/usr/bin/env python3
"""
guard_manifest_write_discipline.py — Enforcement fuer INV-MANIFEST-WRITE-1 (BL-367 F8/F9, parent BL-322).

PreToolUse (Bash / PowerShell): erkennt **ad-hoc Manifest-Block-Writes** in Shell-Kommandos
(Out-File / Add-Content / Set-Content / WriteAllText / `>>`-Redirect / `python3` auf ein Manifest)
und verweist auf den gemeinsamen Helper `.claude/scripts/manifest_append.py`. So wird
"kein ad-hoc PowerShell/Python mehr" (BL-367) STRUKTURELL durchgesetzt statt nur dokumentiert.

Detektion (Heuristik, bewusst konservativ — kein Hard-Block auf Verdacht):
  Kommando referenziert ein Manifest (`_manifest.md` / `_factory_manifest.md`)
  UND nutzt eine ad-hoc Write-Methode (Out-File/Add-Content/Set-Content/WriteAllText/`>>`/`python3`)
  UND enthaelt NICHT `manifest_append` (der sanktionierte Helper)
  -> Treffer.

Default-Mode = WARN (continue:true + Hinweis) — niedrige Blast-Radius beim Rollout. BLOCK
(continue:false, exit 2) nur wenn enforce UND OMNI_MANIFEST_WRITE_GUARD_BLOCK=1 (bewusste
Owner-Eskalation, nachdem die Heuristik validiert ist). Fail-open: jede Exception -> continue:true.

Kill-Switches: OMNI_ENFORCE_ALL_OFF=1 / OMNI_MANIFEST_WRITE_GUARD_OFF=1.
Template: guard_redeploy_health.py.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

HELPER_HINT = (
    "Nutze den gemeinsamen Helper (INV-MANIFEST-WRITE-1, BL-367): "
    "py -3 .claude/scripts/manifest_append.py {manifest} --block-file {f} --marker \"{m}\" "
    "(utf-8 no-BOM + col-0-fence-balanced + line-safe + post-write-Re-Read-Assert). "
    "VERBOTEN: Out-File/Add-Content/Set-Content/WriteAllText/>>/python3 direkt aufs Manifest."
)

MANIFEST_RE = re.compile(r"_manifest\.md|_factory_manifest\.md", re.IGNORECASE)
CMDLET_RE = re.compile(r"\b(Out-File|Add-Content|Set-Content|WriteAllText)\b", re.IGNORECASE)
APPEND_REDIRECT_RE = re.compile(r">>")
PYTHON3_RE = re.compile(r"\bpython3\b")


def classify_command(cmd: str) -> tuple[str, str]:
    """Reine Klassifikations-Logik (testbar). Returns (verdict, reason).

    verdict: "PASS" (kein ad-hoc Manifest-Write) | "WARN" (ad-hoc Manifest-Write erkannt).
    """
    if not cmd or not cmd.strip():
        return ("PASS", "leeres Kommando")
    # Sanktionierter Helper -> immer PASS (auch wenn er ein Manifest + py-3 referenziert).
    if "manifest_append" in cmd:
        return ("PASS", "manifest_append-Helper")
    if not MANIFEST_RE.search(cmd):
        return ("PASS", "keine Manifest-Referenz")
    # Manifest referenziert — ist es ein ad-hoc WRITE?
    m = CMDLET_RE.search(cmd)
    if m:
        return ("WARN", f"ad-hoc Write-Cmdlet auf Manifest: {m.group(1)}")
    if APPEND_REDIRECT_RE.search(cmd):
        return ("WARN", "Shell-Append-Redirect (>>) auf Manifest")
    if PYTHON3_RE.search(cmd):
        return ("WARN", "python3 (F9 MS-Store-Stub-Risiko, silent no-op) auf Manifest -> py -3 / Helper")
    return ("PASS", "Manifest referenziert, aber kein ad-hoc Write erkannt")


def read_enforce() -> bool:
    sp = os.environ.get("OMNI_SESSION_PARAMS")
    if sp and Path(sp).exists():
        try:
            txt = Path(sp).read_text(encoding="utf-8", errors="replace")
            if re.search(r"enforceProcess\s*:?\*?\*?\s*false", txt, re.IGNORECASE):
                return False
        except Exception:
            pass
    return True


def append_guard_log(reason: str, blocked: bool) -> None:
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **MANIFEST_WRITE_DISCIPLINE** [{action}]: {reason}\n")
    except Exception:
        pass


def main() -> None:
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return
    if os.environ.get("OMNI_MANIFEST_WRITE_GUARD_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    if event.get("tool_name") not in ("Bash", "PowerShell"):
        print(json.dumps({"continue": True}))
        return

    cmd = (event.get("tool_input", {}) or {}).get("command", "") or ""
    verdict, reason = classify_command(cmd)
    if verdict == "PASS":
        print(json.dumps({"continue": True}))
        return

    # WARN-Treffer.
    enforce = read_enforce()
    hard_block = enforce and os.environ.get("OMNI_MANIFEST_WRITE_GUARD_BLOCK") == "1"
    msg = (
        f"[GUARD-{'BLOCK' if hard_block else 'WARN'}] MANIFEST_WRITE_DISCIPLINE: {reason}.\n"
        f"  -> {HELPER_HINT}"
    )
    append_guard_log(reason, hard_block)
    print(json.dumps({"continue": not hard_block, "message": msg}))
    if hard_block:
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_manifest_write_discipline ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
