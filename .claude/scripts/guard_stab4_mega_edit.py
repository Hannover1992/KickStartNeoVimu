#!/usr/bin/env python3
"""
Claude Code Hook — Stabilisierungs-Hook S#4: Mega-Edit Detector
(BL-RCA-486-Round11 Layer-L5, 2026-05-27).

PreToolUse-Hook fuer Edit/Write: erkennt Mega-Worker-Pattern auf Tool-Call-Ebene.

Hintergrund:
  G#7 (guard_geist7_sdf_to_i) zaehlt Skill-Loads — kann aber theoretisch
  alle Skills absolvieren und dann trotzdem 1 Mega-Edit mit 1000+ LOC schreiben.
  S#4 schliesst diese Luecke auf Tool-Call-Ebene:
    Edit/Write > Threshold-LOC OHNE Berater-Spawn in den letzten 5 Tool-Calls → BLOCK.

Threshold-Map (per Dateityp):
  Code-Dateien (*.ts/*.tsx/*.cs/*.py/*.html/*.scss): > 200 LOC = MEGA
  Markdown      (*.md):                              > 500 LOC = MEGA
  Test-Dateien (*.spec.*/*.test.*):                  > 300 LOC = MEGA

Berater-Spawn-Detection:
  Skill(_*_berater_*) ODER Skill(_TDD_*) in den letzten 5 Tool-Calls
  (state-tracked, NICHT live aus audit.jsonl gelesen — schnellere Antwort,
   reicht fuer Anti-Mega-Worker-Zweck).

Pragmatik-Override:
  - Env: OMNI_MEGA_EDIT_OVERRIDE=1 → continue:true mit Warn-Message
  - Inline-Marker: `pragmatik_reason:` im new_string/content → continue:true

State:
  .claude/temp/stab4_mega_state.json — ringbuffer von 10 letzten Tool-Calls
  Format: {"calls": [{"ts": "...", "tool": "Skill", "subject": "_X_berater_Y"}, ...]}

enforceProcess=true (Default): BLOCKIERT (continue=false)
enforceProcess=false: NUR Warning (continue=true)

Test-Hooks (Env-Vars):
  OMNI_ENFORCE_STAB4=1            → erzwingt enforce=true (fuer pytest)
  OMNI_STAB4_STATE_PATH=...       → Override state-Pfad (fuer pytest)
  OMNI_STAB4_SESSION_PARAMS=...   → Override Session-Params-Pfad
  OMNI_MEGA_EDIT_OVERRIDE=1       → Pragmatik-Override (User-Bypass)
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

DEFAULT_STATE_FILE = ROOT_DIR / ".claude" / "temp" / "stab4_mega_state.json"
GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# Ringbuffer-Tiefe
STATE_WINDOW = 10
# Berater-Lookback-Tiefe (Subset von STATE_WINDOW)
BERATER_LOOKBACK = 5

# Threshold-Map (LOC pro Datei-Klasse)
THRESHOLDS = {
    "code": 200,
    "markdown": 500,
    "test": 300,
}

CODE_EXT = (".ts", ".tsx", ".cs", ".py", ".html", ".scss", ".js", ".jsx")
MARKDOWN_EXT = (".md",)
# Test-Dateien per Suffix (*.spec.* oder *.test.*) — vor Code-Check pruefen
TEST_RE = re.compile(r"\.(spec|test)\.[A-Za-z0-9]+$")

# Berater-Spawn-Patterns (Skill-Name)
BERATER_SKILL_RE = re.compile(r"^_[A-Z]+_berater_[A-Za-z]+$")
TDD_SKILL_RE = re.compile(r"^_TDD_[A-Za-z]+$")

# Pragmatik-Reason Inline-Marker
PRAGMATIK_RE = re.compile(r"^\s*pragmatik_reason\s*:\s*\S+", re.MULTILINE)


# ──────────────────────────── Helpers ────────────────────────────


def get_state_path():
    override = os.environ.get("OMNI_STAB4_STATE_PATH")
    if override:
        return Path(override)
    return DEFAULT_STATE_FILE


def _resolve_vault_session_params():
    override = os.environ.get("OMNI_STAB4_SESSION_PARAMS")
    if override:
        return Path(override)
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


def read_enforce_process():
    """enforceProcess aus _session_params.md. Default: true."""
    if os.environ.get("OMNI_ENFORCE_STAB4") == "1":
        return True
    params_file = _resolve_vault_session_params()
    try:
        if not params_file.exists():
            return True
        content = params_file.read_text(encoding="utf-8")
        m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
        if m:
            return m.group(1) == "true"
    except Exception:
        pass
    return True


def load_state():
    """Lade state aus JSON. Fallback: leer."""
    path = get_state_path()
    if not path.exists():
        return {"calls": []}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict) and isinstance(data.get("calls"), list):
            return data
    except Exception:
        pass
    return {"calls": []}


def save_state(state):
    """Persistiere state. Bei Fehler: ignorieren (Hook darf nicht blocken)."""
    path = get_state_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # Nur letzte STATE_WINDOW behalten
        calls = state.get("calls", [])[-STATE_WINDOW:]
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"calls": calls}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def append_call(state, tool_name, subject):
    """Append ein Tool-Call-Event in den Ringbuffer."""
    calls = state.get("calls", [])
    calls.append({
        "ts": datetime.now().isoformat(timespec="seconds"),
        "tool": tool_name,
        "subject": subject,
    })
    state["calls"] = calls[-STATE_WINDOW:]
    return state


def has_recent_berater_spawn(state, lookback=BERATER_LOOKBACK):
    """Pruefe ob in den letzten `lookback` Tool-Calls ein Berater-Spawn war.

    Berater-Spawn = Skill-Call mit Name matched BERATER_SKILL_RE oder TDD_SKILL_RE.

    Returns: (has_berater, matched_subject_or_None)
    """
    calls = state.get("calls", [])
    # Letzte lookback (exklusive des aktuellen Calls, der noch NICHT appended ist)
    window = calls[-lookback:]
    for c in window:
        if c.get("tool") != "Skill":
            continue
        subj = c.get("subject", "")
        if BERATER_SKILL_RE.match(subj) or TDD_SKILL_RE.match(subj):
            return True, subj
    return False, None


def classify_file(file_path):
    """Klassifiziere Datei → 'code'/'markdown'/'test'/'other'.

    Reihenfolge: Test vor Code (*.spec.ts ist Test, nicht Code).
    """
    if not file_path:
        return "other"
    lower = file_path.lower()
    if TEST_RE.search(lower):
        return "test"
    if lower.endswith(MARKDOWN_EXT):
        return "markdown"
    if lower.endswith(CODE_EXT):
        return "code"
    return "other"


def count_loc(text):
    """LOC = Anzahl Newline-getrennter Zeilen (mind. 1 falls non-empty)."""
    if not text:
        return 0
    # splitlines() ignoriert trailing-newline-only -> akkurat fuer LOC
    return len(text.splitlines())


def is_mega_edit(file_path, content_or_new_string):
    """Pruefe ob (file_class, loc) > Threshold.

    Returns: (is_mega, loc, threshold, file_class)
    """
    cls = classify_file(file_path)
    if cls == "other":
        return False, 0, None, cls
    loc = count_loc(content_or_new_string)
    threshold = THRESHOLDS.get(cls)
    if threshold is None:
        return False, loc, None, cls
    return loc > threshold, loc, threshold, cls


def has_inline_pragmatik(content_or_new_string):
    """Pruefe ob `pragmatik_reason:` im neuen Content steht."""
    if not content_or_new_string:
        return False
    return bool(PRAGMATIK_RE.search(content_or_new_string))


def append_guard_log(violation_type, details, blocked):
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = f"- [{timestamp}] **{violation_type}** [{action}]: {details}\n"
        with open(GUARD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


# ──────────────────────────── Main ────────────────────────────


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
        raw = sys.stdin.read()
        try:
            hook_data = json.loads(raw)
        except Exception:
            print(json.dumps({"continue": True}))
            return

        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {}) or {}

        # State immer laden (auch fuer non-Edit/Write Tool-Calls — wir tracken Skill-Calls!)
        state = load_state()

        # Skill-Tool: nur tracken (kein Mega-Check)
        if tool_name == "Skill":
            subj = tool_input.get("skill", "") if isinstance(tool_input, dict) else ""
            state = append_call(state, "Skill", subj)
            save_state(state)
            print(json.dumps({"continue": True}))
            return

        # Andere Nicht-Edit/Write Tool-Calls auch tracken (Kontext-Erhaltung)
        if tool_name not in ("Edit", "Write"):
            state = append_call(state, tool_name, "")
            save_state(state)
            print(json.dumps({"continue": True}))
            return

        # ──── Ab hier: Edit oder Write ────
        file_path = ""
        new_content = ""
        if isinstance(tool_input, dict):
            file_path = tool_input.get("file_path", "") or ""
            # Edit: new_string; Write: content
            new_content = tool_input.get("new_string", "") or tool_input.get("content", "") or ""

        is_mega, loc, threshold, file_cls = is_mega_edit(file_path, new_content)

        # Subject fuer State = "{tool}:{file_basename}:{loc}LOC"
        try:
            base = Path(file_path).name if file_path else "?"
        except Exception:
            base = "?"
        subject = f"{base}:{loc}LOC"

        if not is_mega:
            # Tracken und durchlassen
            state = append_call(state, tool_name, subject)
            save_state(state)
            print(json.dumps({"continue": True}))
            return

        # ──── MEGA-Edit erkannt ────
        # Check 1: Inline-Pragmatik?
        if has_inline_pragmatik(new_content):
            state = append_call(state, tool_name, subject + ":pragmatik")
            save_state(state)
            print(json.dumps({
                "continue": True,
                "message": (
                    f"[STAB4-WARN] Mega-Edit ({loc} LOC > {threshold} fuer {file_cls}) "
                    f"durchgelassen wegen inline pragmatik_reason. {base}"
                ),
            }))
            append_guard_log(
                "STAB4_MEGA_EDIT_PRAGMATIK",
                f"{base}: {loc} LOC > {threshold} ({file_cls}) — pragmatik_reason inline",
                blocked=False,
            )
            return

        # Check 2: Env-Override?
        if os.environ.get("OMNI_MEGA_EDIT_OVERRIDE") == "1":
            state = append_call(state, tool_name, subject + ":env_override")
            save_state(state)
            print(json.dumps({
                "continue": True,
                "message": (
                    f"[STAB4-WARN] Mega-Edit ({loc} LOC > {threshold} fuer {file_cls}) "
                    f"durchgelassen wegen OMNI_MEGA_EDIT_OVERRIDE=1. {base}"
                ),
            }))
            append_guard_log(
                "STAB4_MEGA_EDIT_ENV_OVERRIDE",
                f"{base}: {loc} LOC > {threshold} ({file_cls}) — OMNI_MEGA_EDIT_OVERRIDE",
                blocked=False,
            )
            return

        # Check 3: Berater-Spawn in letzten 5 Tool-Calls?
        has_berater, matched = has_recent_berater_spawn(state, lookback=BERATER_LOOKBACK)

        if has_berater:
            state = append_call(state, tool_name, subject + ":post_berater")
            save_state(state)
            print(json.dumps({
                "continue": True,
                "message": (
                    f"[STAB4-OK] Mega-Edit ({loc} LOC > {threshold} fuer {file_cls}) "
                    f"durchgelassen weil Berater-Spawn '{matched}' in letzten "
                    f"{BERATER_LOOKBACK} Tool-Calls."
                ),
            }))
            return

        # ──── BLOCK: Mega ohne Berater + ohne Pragmatik ────
        enforce = read_enforce_process()
        details = (
            f"file={base} loc={loc} threshold={threshold} class={file_cls} "
            f"berater_lookback={BERATER_LOOKBACK}"
        )
        message = (
            f"[STAB4-VIOLATION] MEGA_EDIT_WITHOUT_BERATER_SPAWN: "
            f"{tool_name} auf {base} mit {loc} LOC ueberschreitet Threshold "
            f"{threshold} fuer Klasse '{file_cls}'. "
            f"In den letzten {BERATER_LOOKBACK} Tool-Calls war KEIN Berater-Spawn "
            f"(Skill(_*_berater_*) oder Skill(_TDD_*)). "
            f"Mega-Worker-Pattern verdaechtig. "
            f"Loese mit Berater-Spawn-Sequenz, splitte in mehrere Edits, "
            f"oder setze OMNI_MEGA_EDIT_OVERRIDE=1 / inline pragmatik_reason."
        )

        # State persistieren — Block-Versuch loggen
        state = append_call(state, tool_name, subject + ":BLOCKED")
        save_state(state)
        append_guard_log("STAB4_MEGA_EDIT_BLOCKED", details, blocked=enforce)

        if enforce:
            print(json.dumps({"continue": False, "message": message}))
        else:
            print(json.dumps({
                "continue": True,
                "message": f"[STAB4-WARN enforceProcess=false] {message}",
            }))

    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_stab4_mega_edit Error: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
