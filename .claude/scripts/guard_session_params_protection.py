#!/usr/bin/env python3
"""
Claude Code Hook — Session-Params Protection (Intelligenz-Budget-Cap-Guard, 2026-04-18)
Extended: Ownership-Guard (BL-159 AK-5-ERW, 2026-05-17)

Pre-Hook auf Edit/Write Tool-Calls: Erkennt wenn ein LLM/Agent versucht,
die Session-Param-Obergrenzen in _session_params.md zu ERHOEHEN.
Pre-Hook auf Skill(_param): Erkennt wenn ein Worker-Agent _owner=user Parameter mutiert.

Hintergrund:
  Session-Params sind die vom User gesetzte Obergrenze fuer Intelligenz-Budget.
  difficulty, ceiling, floor — CLI darf NIEMALS darueber gehen.
  Hierarchien:
    difficulty: easy < normal < hard
    ceiling:    haiku < sonnet < opus
    floor:      haiku < sonnet

Problem (beobachtet 2026-04-18):
  LLM wollte _session_params.md von difficulty=easy auf difficulty=normal
  aendern, um CLI-Argument durchzusetzen. Session-Cap wurde damit umgangen.

Ownership-Problem (F90, BL-159):
  BDF-Worker setzt /_param dark_factory=true und mutiert implizit hil=phase -> hil=off.
  Worker darf _owner=user Parameter NIEMALS aendern.

Regel:
  Schreib-Zugriff auf _session_params.md ist NUR erlaubt wenn:
  - difficulty wird NICHT erhoeht (easy→normal BLOCKIERT)
  - ceiling wird NICHT erhoeht (sonnet→opus BLOCKIERT)
  - floor wird NICHT erhoeht (haiku→sonnet BLOCKIERT)
  - Erniedrigen oder Gleichbleiben ist IMMER erlaubt

Ownership-Regel (Skill-Guard):
  Worker (OMNI_AGENT_NAME enthaelt Worker-Suffix) darf NICHT _owner=user Parameter setzen.
  OMNI_ENFORCE_PARAM_GUARD=1 aktiviert Block (analog enforceProcess=true).

enforceProcess=true (Default): BLOCKIERT Upgrades (continue=false)
enforceProcess=false: NUR Warning (continue=true)
"""

import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

# Worker detection: agent names containing these suffixes are considered Workers
WORKER_SUFFIXES = ["-worker", "-sonnet-worker", "-haiku-worker", "-opus-worker"]
WORKER_WHITELIST = ["_param", "_backlog", "user-direct", ""]

# Default audit path (overrideable via OMNI_AUDIT_JSONL_PATH)
DEFAULT_AUDIT_PATH = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"


def is_worker_context() -> bool:
    """Returns True if OMNI_AGENT_NAME indicates a Worker (non-whitelisted) agent."""
    agent_name = os.environ.get("OMNI_AGENT_NAME", "").strip()
    if agent_name in WORKER_WHITELIST:
        return False
    for suffix in WORKER_SUFFIXES:
        if agent_name.endswith(suffix):
            return True
    # Also treat any non-empty non-whitelist name with worker keyword
    if "worker" in agent_name.lower():
        return True
    return False


def write_audit_event(event: str, extra: dict):
    """Appends a JSON audit event to audit.jsonl."""
    try:
        audit_path_str = os.environ.get("OMNI_AUDIT_JSONL_PATH", "")
        audit_path = Path(audit_path_str) if audit_path_str else DEFAULT_AUDIT_PATH
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"event": event, "ts": datetime.now(timezone.utc).isoformat()}
        entry.update(extra)
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass


def handle_skill_param_guard(tool_input: dict) -> dict | None:
    """Ownership-Guard for Skill(_param) calls.

    Returns a response dict to short-circuit, or None to fall through.
    """
    skill_name = tool_input.get("skill_name", "")
    if skill_name != "_param":
        # Non-_param skill: always allow
        return {"continue": True}

    enforce = os.environ.get("OMNI_ENFORCE_PARAM_GUARD", "0") == "1"
    owner = tool_input.get("_owner", "")

    if owner != "user":
        # No _owner=user marker → allow (system/worker params are fine)
        return {"continue": True}

    if not is_worker_context():
        # Non-worker context (e.g. Team Lead) → allow even _owner=user
        return {"continue": True}

    if not enforce:
        # Not in enforcement mode → allow but don't block
        return {"continue": True}

    # Worker + _owner=user + enforce=1 → BLOCK
    args_str = tool_input.get("args", "")
    # Extract param_name from args (e.g. "hil=off" → "hil")
    param_name = args_str.split("=")[0].strip() if "=" in args_str else args_str.strip()
    attempted_value = args_str.split("=", 1)[1].strip() if "=" in args_str else ""
    agent_name = os.environ.get("OMNI_AGENT_NAME", "unknown")

    write_audit_event("PARAM_MUTATION_BLOCKED", {
        "param_name": param_name,
        "attempted_value": attempted_value,
        "blocker": agent_name,
        "owner": "user",
        "skill": "_param",
        "args": args_str,
    })

    msg = (
        f"PARAM_MUTATION_BLOCKED: Worker '{agent_name}' darf _owner=user Parameter "
        f"nicht mutieren. Parameter '{param_name}={attempted_value}' ist User-owned "
        f"(INV-OWNER-1, BL-159 AK-5-ERW). ABBRUCH."
    )
    return {"continue": False, "message": msg}


def _resolve_vault_session_params():
    """BL-159 W17-Fix: Resolve Vault-root via resolve_vault_root.py, fallback to legacy path.

    Pre-fix bug: SESSION_PARAMS_FILE pointed to deprecated `.claude/analysis/_session_params.md`
    (project-local) — the guard was wirkungslos because real _session_params.md lives in the
    Vault. Now use resolve_vault_root() to find Vault, then VAULT_ROOT / "_session_params.md".
    """
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
                    vault_root = Path(vault_root_str)
                    return vault_root / "_session_params.md"
    except Exception:
        pass
    return ROOT_DIR / ".claude" / "analysis" / "_session_params.md"


SESSION_PARAMS_FILE = _resolve_vault_session_params()
GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
LOG_FILE = ROOT_DIR / ".hook_debug.log"

# Hierarchien (hoeherer Wert = mehr Intelligenz/Budget)
DIFFICULTY_HIERARCHY = {"easy": 1, "normal": 2, "hard": 3}
CEILING_HIERARCHY = {"haiku": 1, "sonnet": 2, "opus": 3}
FLOOR_HIERARCHY = {"haiku": 1, "sonnet": 2, "opus": 3}


def _detect_active_skill_for_param():
    """Liest letztes SKILL_LOAD aus audit.jsonl (Identity-Modell, BL-RCA-Round16).

    Returns skill_name oder None (Human-Direct). Test-Override: OMNI_PARAM_ACTIVE_SKILL.
    """
    override = os.environ.get("OMNI_PARAM_ACTIVE_SKILL")
    if override is not None:
        return override or None
    audit_path = Path(os.environ.get("OMNI_AUDIT_JSONL_PATH", str(DEFAULT_AUDIT_PATH)))
    if not audit_path.exists():
        return None
    try:
        lines = audit_path.read_text(encoding="utf-8", errors="replace").splitlines()
        for line in reversed(lines):
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("event") == "SKILL_LOAD":
                return ev.get("skill_name") or ev.get("skill")
    except Exception:
        pass
    return None


def read_enforce_process():
    """Liest enforceProcess aus _session_params.md. Default: true."""
    try:
        if not SESSION_PARAMS_FILE.exists():
            return True
        content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
        match = re.search(r'\*\*enforceProcess:\*\*\s*(true|false)', content)
        if match:
            return match.group(1) == "true"
    except Exception:
        pass
    return True


def extract_params(content):
    """Extrahiere difficulty, ceiling, floor aus session_params-Content."""
    result = {}
    for key in ["difficulty", "ceiling", "floor"]:
        pattern = rf'\*\*{key}:\*\*\s*([a-zA-Z]+)'
        match = re.search(pattern, content)
        if match:
            result[key] = match.group(1).lower().strip()
    return result


def apply_edit(old_content, old_string, new_string):
    """Simuliere Edit-Tool: ersetze old_string durch new_string im Content."""
    if old_string in old_content:
        return old_content.replace(old_string, new_string, 1)
    return old_content  # Edit wuerde scheitern, aber wir lassen das nicht uns betreffen


def append_guard_log(violation_type, details, blocked):
    """Appende Violation an GUARD_LOG Datei."""
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = f"- [{timestamp}] **{violation_type}** [{action}]: {details}\n"
        with open(GUARD_LOG_FILE, "a", encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        pass


def check_upgrades(old_params, new_params):
    """Vergleiche alt vs. neu. Returne Liste von Upgrades (hoch-Richtung)."""
    upgrades = []
    hierarchies = {
        "difficulty": DIFFICULTY_HIERARCHY,
        "ceiling": CEILING_HIERARCHY,
        "floor": FLOOR_HIERARCHY,
    }
    for key, hierarchy in hierarchies.items():
        old_val = old_params.get(key)
        new_val = new_params.get(key)
        if old_val is None or new_val is None:
            continue
        if old_val == new_val:
            continue
        old_level = hierarchy.get(old_val, 0)
        new_level = hierarchy.get(new_val, 0)
        if new_level > old_level:
            upgrades.append(f"{key}: {old_val}→{new_val}")
    return upgrades


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

        # Ownership-Guard: Skill(_param) + _owner=user + worker context
        if tool_name == "Skill":
            result = handle_skill_param_guard(tool_input)
            if result is not None:
                print(json.dumps(result))
                return

        if tool_name not in ["Edit", "Write"]:
            print(json.dumps({"continue": True}))
            return

        file_path = ""
        old_string = ""
        new_string = ""
        new_content = ""
        if isinstance(tool_input, dict):
            file_path = tool_input.get("file_path", "")
            old_string = tool_input.get("old_string", "")
            new_string = tool_input.get("new_string", "")
            new_content = tool_input.get("content", "")

        if not file_path or "_session_params.md" not in file_path:
            print(json.dumps({"continue": True}))
            return

        if not SESSION_PARAMS_FILE.exists():
            print(json.dumps({"continue": True}))
            return

        old_content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
        old_params = extract_params(old_content)

        if tool_name == "Edit":
            simulated_new = apply_edit(old_content, old_string, new_string)
        else:  # Write
            simulated_new = new_content

        new_params = extract_params(simulated_new)

        upgrades = check_upgrades(old_params, new_params)

        if not upgrades:
            print(json.dumps({"continue": True}))
            return

        # IDENTITY-EARLY-OUT (BL-RCA-Round16 2026-05-28):
        # Wenn der aktive Skill /_param ist (= User-Befehl), darf der User Params
        # in JEDE Richtung setzen (auch Upgrade). Der Upgrade-Block war RICHTUNGS-
        # basiert und konnte User nicht von Maschine unterscheiden — er blockte
        # legitime User-Upgrades. Identity-Modell loest das: /_param = autorisiert.
        try:
            active_skill = _detect_active_skill_for_param()
            if active_skill is None or active_skill in ("_param", "_backlog"):
                # User-Befehl ODER Human-Direct → Upgrade erlaubt
                print(json.dumps({"continue": True}))
                return
        except Exception:
            pass  # Bei Fehler: alte Upgrade-Block-Logik greift (sicher)

        enforce = read_enforce_process()
        upgrade_str = ", ".join(upgrades)

        warning = (
            f"[GUARD-VIOLATION] INTELLIGENZ-BUDGET-CAP umgangen! "
            f"_session_params.md Upgrade-Versuch: {upgrade_str}. "
            f"Session-Params sind die USER-gesetzte Obergrenze — LLM darf sie NIEMALS erhoehen. "
            f"CLI darf nur unter Session-Cap bleiben. Nutze min_level(CLI, params). "
            f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
        )
        print(json.dumps({
            "continue": not enforce,
            "message": warning
        }))
        append_guard_log(
            "SESSION_PARAMS_UPGRADE",
            f"_session_params.md Upgrade-Versuch: {upgrade_str}",
            enforce
        )

    except Exception as e:
        try:
            with open(LOG_FILE, "a", encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] guard_session_params_protection Error: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
