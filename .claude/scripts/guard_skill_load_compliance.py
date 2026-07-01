#!/usr/bin/env python3
"""
Claude Code Hook — Skill-Loading-Compliance Guard (BL-159 AK-2 + AK-3).

PreToolUse-Hook auf Read. Blockiert Read von `.claude/commands/_*.md` und
verlangt stattdessen `Skill(_skill_name)`. Verhindert das Mega-Agent-Anti-
Pattern (Slash-Commands inline interpretieren statt via Skill-Tool laden).

Spec (BL-159):
  AK-2: Read von .claude/commands/_*.md  ->  BLOCK + Hint "Use Skill tool"
  AK-3: Pipeline-Stop statt Silent-Degradieren

Toggle:
  enforceProcess=true   (default) -> BLOCKIERT (continue=false)
  enforceProcess=false             -> WARNING (continue=true)

Override (per Shell):
  OMNI_ALLOW_SKILL_READ=1 -> Skip-Hook (z.B. `_audit --skill-load-replay`).
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
AUDIT_DIR = ROOT_DIR / ".claude" / "audit"
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"


def _resolve_vault_session_params():
    try:
        import subprocess
        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True, text=True, timeout=5,
                cwd=str(ROOT_DIR),
            )
            if proc.returncode == 0:
                vault_root_str = proc.stdout.strip()
                if vault_root_str:
                    return Path(vault_root_str) / "_session_params.md"
    except Exception:
        pass
    return ROOT_DIR / ".claude" / "analysis" / "_session_params.md"


SESSION_PARAMS_FILE = _resolve_vault_session_params()
GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

SKILL_PATH_PATTERN = re.compile(
    r"(?:^|[\\/])\.claude[\\/]commands[\\/](_[A-Za-z0-9_]+)\.md$"
)


def read_enforce_process():
    try:
        if not SESSION_PARAMS_FILE.exists():
            return True
        content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
        m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
        if m:
            return m.group(1) == "true"
    except Exception:
        pass
    return True


def extract_skill_name(file_path):
    if not file_path:
        return None
    normalized = file_path.replace("\\", "/")
    m = SKILL_PATH_PATTERN.search(file_path) or SKILL_PATH_PATTERN.search(normalized)
    if m:
        return m.group(1)
    return None


def append_guard_log(skill_name, file_path, blocked):
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = (
            f"- [{timestamp}] **SKILL_LOAD_VIA_READ** [{action}]: "
            f"skill={skill_name} file={file_path}\n"
        )
        with open(GUARD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def write_rollback_audit_event(file_path: str, skill_name: str) -> None:
    """BL-159 AK-6 PL-6-08: Schreibt ROLLBACK-Event in audit.jsonl (INV-ROLL-1..5)."""
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        inputs_redacted: dict = {}
        if file_path:
            inputs_redacted["file_path"] = file_path
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "event": "ROLLBACK",
            "tool": "Read",
            "target": file_path or skill_name,
            "reason": (
                f"SKILL_LOAD_VIOLATION: Read ohne vorherigen Skill()-Call — "
                f"skill={skill_name} (Mega-Agent-Anti-Pattern BL-159 AK-2/AK-3)"
            ),
            "guard": "guard_skill_load_compliance.py",
            "inputs": inputs_redacted,
        }
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main():
    # === Globaler Owner-Kill-Switch (BL-223): enforceProcess=false -> Guard aus ===
    import os as _os, json as _json
    if _os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(_json.dumps({"continue": True}))
        return
    try:
        import sys as _sys
        from pathlib import Path as _P
        _sd = str(_P(__file__).parent.absolute())
        if _sd not in _sys.path:
            _sys.path.insert(0, _sd)
        from _enforce_gate import enforce_active
        if not enforce_active():
            print(_json.dumps({"continue": True}))
            return
    except Exception:
        pass
    try:
        hook_data = json.loads(sys.stdin.read())
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        if tool_name != "Read":
            print(json.dumps({"continue": True}))
            return

        if os.environ.get("OMNI_ALLOW_SKILL_READ") == "1":
            print(json.dumps({"continue": True}))
            return

        file_path = ""
        if isinstance(tool_input, dict):
            file_path = tool_input.get("file_path", "")

        skill_name = extract_skill_name(file_path)
        if not skill_name:
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()
        hint = (
            f"[GUARD-VIOLATION] SKILL_LOAD_VIA_READ. "
            f"Read({file_path}) interpretiert {skill_name} INLINE (Mega-Agent-Anti-Pattern, BL-159). "
            f"Stattdessen: Skill(skill=\"{skill_name}\") nutzen, damit der Skill-Vertrag bindend ist. "
            f"Override fuer legitime Inspektion: OMNI_ALLOW_SKILL_READ=1. "
            f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
        )
        print(json.dumps({
            "continue": not enforce,
            "message": hint,
        }))
        append_guard_log(skill_name, file_path, enforce)
        if enforce:
            write_rollback_audit_event(file_path, skill_name)

    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_skill_load_compliance Error: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
