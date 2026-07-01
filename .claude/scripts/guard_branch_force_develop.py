#!/usr/bin/env python3
"""
Claude Code Hook — Branch Force-Develop Guard (BL-490).

PreToolUse-Hook: blockiert jeden versuchten Force-Move eines geteilten Branches
(develop / main) via Bash oder PowerShell.

Verbotene Kommandos (classify_command):
  (a) git branch -f/--force develop|main ...
  (b) git update-ref refs/heads/develop|main ...
  (c) git push +develop|+main  ODER  git push --force/-f ... develop|main

Erlaubt: Force-Moves auf Lane-Branches (roadmap-a, backup/x ...), plain branch
develop (ohne -f), merge develop, fetch ... roadmap-a:develop, usw.

Override: OMNI_ENFORCE_ALL_OFF=1 -> continue:true (globaler Kill-Switch).
Recover-Hint: py -3 .claude/scripts/merge_seam.py advance --ref {ref} --to <lane>

Stil: guard_stab6_branch_hygiene.py (Vorlage).
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# Geteilte Branches — Force-Moves verboten
SHARED_BRANCHES = {"develop", "main"}

# Tools die Bash-Kommandos ausfuehren koennen
BASH_TOOLS = {"Bash", "PowerShell"}


# ---------------------------------------------------------------------------
# Logging-Helfer (optional, fail-silent)
# ---------------------------------------------------------------------------

def append_guard_log(severity: str, details: str) -> None:
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        entry = (
            f"- [{timestamp}] **GUARD_BRANCH_FORCE_DEVELOP** [{severity}]: {details}\n"
        )
        with open(GUARD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def append_debug_log(msg: str) -> None:
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] guard_branch_force_develop: {msg}\n")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# classify_command — pure Logik, leicht testbar
# ---------------------------------------------------------------------------

def classify_command(command: str) -> dict | None:
    """Analysiert ein Shell-Kommando auf verbotene Force-Moves geteilter Branches.

    Returns:
        None        — Kommando ist erlaubt (oder kein git-Kommando).
        dict        — {"blocked": True, "reason": str, "ref": "develop"|"main"}
    """
    if not command:
        return None

    tokens = command.split()
    if not tokens:
        return None
    if tokens[0] != "git":
        return None
    if len(tokens) < 2:
        return None

    subcommand = tokens[1]
    rest = tokens[2:]

    # ------------------------------------------------------------------
    # (a) git branch -f/--force <target-branch> ...
    #     git branch -d/-D/--delete <target-branch>  (FN-2, BL-490)
    # ------------------------------------------------------------------
    if subcommand == "branch":
        flags = {t for t in rest if t.startswith("-")}
        has_force = "-f" in flags or "--force" in flags
        has_delete = "-d" in flags or "-D" in flags or "--delete" in flags
        if not has_force and not has_delete:
            return None
        # Erster Nicht-Flag-Operand ist der Ziel-Branch
        for tok in rest:
            if not tok.startswith("-"):
                # Exakter Vergleich (kein Substring) → Wort-Grenze automatisch
                if tok in SHARED_BRANCHES:
                    if has_delete:
                        operation = "Loeschung"
                        verb = f"Loeschung des geteilten Branches '{tok}' via `git branch --delete`"
                    else:
                        operation = "Force-Move"
                        verb = f"Force-Move des geteilten Branches '{tok}' via `git branch -f`"
                    return {
                        "blocked": True,
                        "reason": (
                            f"{verb} ist verboten (BL-490)."
                        ),
                        "ref": tok,
                    }
                # Erster Nicht-Flag bestimmt Ziel — nicht weiter suchen
                break
        return None

    # ------------------------------------------------------------------
    # (b) git update-ref refs/heads/develop|main ...
    # ------------------------------------------------------------------
    if subcommand == "update-ref":
        for tok in rest:
            for ref in SHARED_BRANCHES:
                if tok == f"refs/heads/{ref}":
                    return {
                        "blocked": True,
                        "reason": (
                            f"Force-Move des geteilten Branches '{ref}' via "
                            f"`git update-ref` ist verboten (BL-490)."
                        ),
                        "ref": ref,
                    }
        return None

    # ------------------------------------------------------------------
    # (c) git push — Force-Refspec (+develop / +main) ODER --force/-f + Token
    # ------------------------------------------------------------------
    if subcommand == "push":
        # Pruefen auf +develop / +main als Refspec-Praefix
        for tok in rest:
            if tok.startswith("+"):
                # Token kann "+develop" oder "+develop:develop" o.ae. sein
                # Wir extrahieren den Source-Ref vor dem optionalen ":"
                source = tok[1:].split(":")[0]
                if source in SHARED_BRANCHES:
                    return {
                        "blocked": True,
                        "reason": (
                            f"Force-Push des geteilten Branches '{source}' via "
                            f"`+{source}` Refspec ist verboten (BL-490)."
                        ),
                        "ref": source,
                    }

        # Pruefen auf --force/-f/--force-with-lease UND develop/main als eigenes Token
        flags = {t for t in rest if t.startswith("-")}
        has_force = (
            "--force" in flags
            or "-f" in flags
            or "--force-with-lease" in flags
            or any(f.startswith("--force-with-lease=") for f in flags)
        )
        if has_force:
            # Nicht-Flag-Tokens (ohne Praefix '-' und '+')
            non_flags = {t for t in rest if not t.startswith("-") and not t.startswith("+")}
            for ref in SHARED_BRANCHES:
                if ref in non_flags:
                    return {
                        "blocked": True,
                        "reason": (
                            f"Force-Push des geteilten Branches '{ref}' via "
                            f"`--force` ist verboten (BL-490)."
                        ),
                        "ref": ref,
                    }

        return None

    return None


# ---------------------------------------------------------------------------
# main() — Hook-Vertrag (stdin JSON → stdout JSON)
# ---------------------------------------------------------------------------

def main() -> None:
    # Globaler Kill-Switch (BL-223)
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    # Guard-spezifischer Test-Override (analog OMNI_ENFORCE_STAB6_GUARD=1)
    _guard_override = os.environ.get("OMNI_GUARD_FORCE_DEVELOP")
    if _guard_override == "1":
        pass  # Enforcement erzwingen — Gate ueberspringen
    elif _guard_override == "0":
        print(json.dumps({"continue": True}))
        return
    else:
        # enforce_gate — fail-open bei Import-Fehler
        try:
            _sd = str(SCRIPT_DIR)
            if _sd not in sys.path:
                sys.path.insert(0, _sd)
            from _enforce_gate import enforce_active  # type: ignore[import]
            if not enforce_active():
                print(json.dumps({"continue": True}))
                return
        except Exception:
            pass

    try:
        raw = sys.stdin.read()
        if not raw.strip():
            print(json.dumps({"continue": True}))
            return

        hook_data = json.loads(raw)
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        if tool_name not in BASH_TOOLS:
            print(json.dumps({"continue": True}))
            return

        if not isinstance(tool_input, dict):
            print(json.dumps({"continue": True}))
            return

        command = tool_input.get("command", "") or ""
        result = classify_command(command)

        if result is None:
            print(json.dumps({"continue": True}))
            return

        # --- BLOCK ---
        ref = result["ref"]
        append_guard_log(
            "BLOCKED",
            f"Force-Move '{ref}' blockiert: {command!r}",
        )
        message = (
            f"[GUARD_BRANCH_FORCE_DEVELOP BLOCK] "
            f"Verbotener Force-Move des geteilten Branches '{ref}'. "
            f"Nutze stattdessen: "
            f"`py -3 .claude/scripts/merge_seam.py advance --ref {ref} --to <lane>` "
            f"(FF-safe-gegatet, BL-490) ODER einen echten merge. "
            f"Override (Notfall): OMNI_ENFORCE_ALL_OFF=1"
        )
        print(json.dumps({"continue": False, "message": message}))

    except json.JSONDecodeError as e:
        append_debug_log(f"JSONDecodeError: {e}")
        print(json.dumps({"continue": True}))
    except Exception as e:
        append_debug_log(f"Unexpected error: {e}")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
