#!/usr/bin/env python3
"""
Geist G#8 Hook: SDF Phase 2.1 → SC (M4-M7)

PostToolUse-Hook fuer Skill-Tool. Aufgabe: Erzwingt Min-Skill-Loads
fuer SC-Pipeline-Modi M4/M5/M6/M7, damit der Lead nicht als Mega-Worker
einen Forschungs-Zyklus in einer Skill-Invocation "simuliert" statt
die einzelnen SC-Skills (teamSetup/observe/modelMaintain/qualityGate/
hypothese/ergebnis/implement) sauber zu spawnen.

Kontext: G#8 ist Uebergang SDF Phase 2.1 EXECUTION DISPATCH → SC-Pipeline.
Heute NICHT enforced. Schwester-Hook: guard_geist7_sdf_to_i.py (M2/M3 Code).
Schwere: MEDIUM (M4-M7 weniger Drift-Risiko als M2/M3 Code-Pipeline).

Counter-Logik:
  - Counter beginnt bei Skill(_SC_orchestrate)-Load (PostToolUse).
  - Zaehlt nachfolgende SC-Skill-Loads (`_SC_orchestrate` selbst zaehlt NICHT
    als Step, sondern als Start-Anker).
  - SC-Skills die zaehlen:
       _SC_berater_*          (teamSetup, modusMatrix, kurzlebigPrompt,
                               teamLeadSteuerung)
       _SC_observe
       _SC_hypothese
       _SC_modelMaintain
       _SC_qualityGate
       _SC_ergebnis
       _SC_implement
  - Bei naechstem Skill(_SC_orchestrate)-Load (neue Pipeline) wird Counter
    zurueckgesetzt.

Modus-Min-Loads (M4-M7):
  M4 (SC-Analyse-only):     4 Skills (teamSetup + observe + modelMaintain
                                       + qualityGate)
  M5 (SC-Forschungs-Zyklus): 6 Skills (M4 + hypothese + ergebnis)
  M6 (SC + I):               6 Skills SC (M5) — I-Pipeline-Min wird durch
                              guard_geist7_sdf_to_i.py erfasst
  M7 (SC-Pure-Forschung):    7 Skills (M5 + ergebnis 2x oder
                              modelMaintain 2x)

Bei Verletzung:
  - audit-Event PROCESS_BYPASS_DETECTED_SC_M{N}
  - process_debt=true im State
  - enforceProcess=true: continue=false (BLOCK)
  - enforceProcess=false: continue=true + Warning-Message

State-Persistenz: `.geist8_sc_counter.json` im ROOT_DIR
  {
    "active": true,
    "sc_orchestrate_started_at": "ISO-Timestamp",
    "modus": "M4|M5|M6|M7" | null,
    "skill_loads": [...],
    "count": N
  }
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import fcntl
    _HAS_FCNTL = True
except ImportError:
    _HAS_FCNTL = False


def _lock_shared(f):
    if _HAS_FCNTL:
        fcntl.flock(f.fileno(), fcntl.LOCK_SH)


def _lock_exclusive(f):
    if _HAS_FCNTL:
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)


def _unlock(f):
    if _HAS_FCNTL:
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

STATE_FILE = ROOT_DIR / ".geist8_sc_counter.json"
AUDIT_FILE = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"
GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# Counter-Reset-Anker
SC_ORCHESTRATE = "_SC_orchestrate"

# SC-Skills die als legitime Steps zaehlen
SC_STEP_SKILLS = {
    "_SC_observe",
    "_SC_hypothese",
    "_SC_modelMaintain",
    "_SC_qualityGate",
    "_SC_ergebnis",
    "_SC_implement",
}

# _SC_berater_* zaehlen auch (teamSetup, modusMatrix, kurzlebigPrompt,
# teamLeadSteuerung)
SC_BERATER_PREFIX = "_SC_berater_"

# Min-Loads pro Modus (BL-219 Sister-Spec, M4-M7-Block)
MIN_LOADS_PER_MODUS = {
    "M4": 4,  # teamSetup + observe + modelMaintain + qualityGate
    "M5": 6,  # M4 + hypothese + ergebnis
    "M6": 6,  # M5 SC-Teil (I-Min via geist7)
    "M7": 7,  # M5 + ergebnis 2x / modelMaintain 2x
}


def _resolve_vault_session_params():
    """Aufloest _session_params.md analog guard_modus_writer."""
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


def read_enforce_process():
    """enforceProcess aus _session_params.md.
    Test-Override: OMNI_ENFORCE_GEIST8=1 erzwingt enforce=true.
    """
    if os.environ.get("OMNI_ENFORCE_GEIST8") == "1":
        return True
    if os.environ.get("OMNI_ENFORCE_GEIST8") == "0":
        return False
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


def _state_path():
    """Test-Override fuer pytest: OMNI_GEIST8_STATE_FILE."""
    override = os.environ.get("OMNI_GEIST8_STATE_FILE")
    return Path(override) if override else STATE_FILE


def _empty_state():
    return {
        "active": False,
        "sc_orchestrate_started_at": None,
        "modus": None,
        "skill_loads": [],
        "count": 0,
        "process_debt": False,
    }


def read_state():
    """Lies aktuellen Counter-State."""
    path = _state_path()
    if not path.exists():
        return _empty_state()
    try:
        with open(path, "r", encoding="utf-8") as f:
            _lock_shared(f)
            try:
                return json.load(f)
            finally:
                _unlock(f)
    except Exception:
        return _empty_state()


def write_state(state):
    """Schreibe State atomisch."""
    state_path = _state_path()
    state["updated_at"] = datetime.now().isoformat()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        _lock_exclusive(f)
        try:
            json.dump(state, f, indent=2)
            f.flush()
        finally:
            _unlock(f)


def append_audit_event(event_type, payload):
    """Append audit-Event in audit.jsonl."""
    try:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now().isoformat(),
            "event": event_type,
            "source": "guard_geist8_sdf_to_sc",
            "payload": payload,
        }
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            _lock_exclusive(f)
            try:
                f.write(json.dumps(entry) + "\n")
                f.flush()
            finally:
                _unlock(f)
    except Exception:
        pass


def append_guard_log(violation_type, details, blocked):
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = (
            f"- [{timestamp}] **{violation_type}** [{action}]: "
            f"{details}\n"
        )
        with open(GUARD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def extract_modus(tool_input, args_str):
    """Extrahiere --modus=M{N} aus Skill-Args oder tool_input.
    Akzeptiert Formate:  --modus=M4 / --modus M4 / modus: M4
    """
    if not args_str:
        # Auch in tool_input nachsehen, falls Modus als getrenntes Feld
        if isinstance(tool_input, dict):
            mod = tool_input.get("modus") or tool_input.get("mode")
            if isinstance(mod, str):
                m = re.search(r"M([1-9])", mod)
                if m:
                    return f"M{m.group(1)}"
        return None
    m = re.search(r"(?:--?modus[=\s]+|modus\s*:\s*)M([1-9])", args_str)
    if m:
        return f"M{m.group(1)}"
    return None


def is_sc_step_skill(skill_name):
    """True wenn Skill-Name als SC-Step zaehlt."""
    if not skill_name:
        return False
    if skill_name in SC_STEP_SKILLS:
        return True
    if skill_name.startswith(SC_BERATER_PREFIX):
        return True
    return False


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

        # Nur PostToolUse fuer Skill-Tool
        hook_event = hook_data.get("hook_event_name", "")
        tool_name = hook_data.get("tool_name", "")

        if tool_name != "Skill":
            print(json.dumps({"continue": True}))
            return

        # PreToolUse: Wir wollen Counter-Update + Min-Load-Check beim NEXT
        # Skill-Load. PostToolUse: Counter-Aktualisierung. Beide OK.
        # Hier: PostToolUse-Variante (counter-akkumulierend).
        if hook_event and hook_event not in (
                "PostToolUse", "PreToolUse"):
            print(json.dumps({"continue": True}))
            return

        tool_input = hook_data.get("tool_input", {})
        skill_name = ""
        args_str = ""
        if isinstance(tool_input, dict):
            skill_name = (tool_input.get("skill")
                          or tool_input.get("name") or "")
            args_str = tool_input.get("args", "") or ""
            if not isinstance(args_str, str):
                args_str = str(args_str)

        if not skill_name:
            print(json.dumps({"continue": True}))
            return

        # Skill-Namen normalisieren: plugin:skill → skill-Anteil
        if ":" in skill_name:
            skill_name = skill_name.split(":", 1)[1]

        state = read_state()
        enforce = read_enforce_process()

        # Fall 1: Skill(_SC_orchestrate) gestartet → Counter (re)init
        if skill_name == SC_ORCHESTRATE:
            # Vorheriger SC-Lauf abgeschlossen? Pruefe Min-Loads BEVOR Reset.
            violations = []
            if state.get("active"):
                modus = state.get("modus")
                cnt = int(state.get("count", 0))
                if modus in MIN_LOADS_PER_MODUS:
                    min_loads = MIN_LOADS_PER_MODUS[modus]
                    if cnt < min_loads:
                        violations.append(
                            f"SC-Lauf (modus={modus}) endete mit "
                            f"{cnt} Skill-Loads — Minimum waere "
                            f"{min_loads}. Skill-Loads: "
                            f"{state.get('skill_loads', [])}"
                        )

            # Init neuer Counter
            new_modus = extract_modus(tool_input, args_str)
            state = {
                "active": True,
                "sc_orchestrate_started_at":
                    datetime.now().isoformat(),
                "modus": new_modus,
                "skill_loads": [],
                "count": 0,
                "process_debt": state.get("process_debt", False),
            }
            write_state(state)

            if violations:
                detail = "; ".join(violations)
                state["process_debt"] = True
                write_state(state)
                modus_for_event = state.get("modus") or "MX"
                append_audit_event(
                    f"PROCESS_BYPASS_DETECTED_SC_{modus_for_event}",
                    {
                        "geist": "G#8",
                        "from": "SDF Phase 2.1",
                        "to": "SC-Pipeline",
                        "detail": detail,
                        "enforce": enforce,
                    },
                )
                append_guard_log(
                    "GEIST8_SC_MIN_LOADS_VIOLATION", detail, enforce)
                msg = (
                    f"[GUARD-VIOLATION] GEIST8 (SDF→SC, M4-M7): "
                    f"{detail}. "
                    f"Min-Loads: M4=4, M5=6, M6=6, M7=7. "
                    f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
                )
                print(json.dumps({
                    "continue": not enforce,
                    "message": msg,
                }))
                return

            print(json.dumps({"continue": True}))
            return

        # Fall 2: Skill ist SC-Step → Counter inkrementieren
        if is_sc_step_skill(skill_name) and state.get("active"):
            state["skill_loads"] = list(state.get("skill_loads", [])) + [
                skill_name
            ]
            state["count"] = int(state.get("count", 0)) + 1
            # Falls Modus nachtraeglich bekannt wird via _SC_berater_teamSetup
            # output → wir koennen ihn ggf. spaeter setzen. Heute: passiv.
            write_state(state)
            print(json.dumps({"continue": True}))
            return

        # Fall 3: Anderes Skill → Passthrough
        print(json.dumps({"continue": True}))
        return

    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(
                    f"[{datetime.now()}] guard_geist8 Error: {e}\n")
        except Exception:
            pass
        # NIEMALS Hook crashen lassen
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
