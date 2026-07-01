#!/usr/bin/env python3
"""
Claude Code Hook — Geist G#7 Guard (BL-219: SDF Phase 2.1 -> I-Pipeline).

PostToolUse-Hook fuer Skill-Tool: erkennt Mega-Worker-Drift im I-Pipeline-Lauf.

Trigger:
  Skill(_I_orchestrate) wurde geladen UND ein Skill-Wechsel ist passiert
  (d.h. ein NEUER Skill != _I_* wurde aufgerufen -> I-Pipeline geschlossen).

Counter-Logik:
  Vom letzten "SKILL_LOAD _I_orchestrate"-Event vorwaerts:
    - Zaehle Distinct _I_*-Skill-Loads (incl. _TDD_* fuer M3) bis zum naechsten
      Non-_I_/Non-_TDD_-Skill-Load.
  Wenn < MIN(modus, slicing) -> Violation.

Min-Map (BL-219 AK-1):
  M2 (slicing=false): 5  (_I_requirementCheck, _I_goldDefine, _I_blueprintQG, _I_verify + 1 Stage-QG)
  M2 (slicing=true):  8
  M3 (slicing=false): 10 (5 Blueprint + 5 TDD-Cycle: _TDD_red/_TDD_execute/_TDD_green/_TDD_refactorCode/_TDD_check)
  M3 (slicing=true):  14
  M5/M7 (lead_direct): 3 (nicht-I-Pipeline, hier nicht enforced)

Pragmatik-Override:
  Wenn `pragmatik_reason` im aktiven DF_BATCH_STATE des BL-Manifests vorhanden -> WARN-only.

enforceProcess (Default true):
  =true:  BLOCK (continue=false) bei Violation ohne Pragmatik
  =false: WARN-only (continue=true)

Manifest-Side-Effect bei Violation:
  - `BL_LIFECYCLE_STATE.process_debt=true` setzen (idempotent)
  - Audit-Event `PROCESS_BYPASS_DETECTED_M{N}_min={X}_actual={Y}`

Test-Hooks (Env-Vars):
  OMNI_ENFORCE_GEIST7=1        -> erzwinge enforceProcess=true (fuer pytest)
  OMNI_GEIST7_AUDIT_PATH=...   -> Override audit.jsonl-Pfad (fuer pytest)
  OMNI_GEIST7_MANIFEST_PATH=...-> Override Manifest-Pfad (fuer pytest)
  OMNI_GEIST7_SESSION_PARAMS=..-> Override Session-Params-Pfad (fuer pytest)
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

AUDIT_FILE = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"
GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"


# Min-Map (BL-219 AK-1) — keyed by (modus, slicing_bool)
MIN_SKILL_LOADS = {
    ("M2", False): 5,
    ("M2", True):  8,
    ("M3", False): 10,
    ("M3", True):  14,
    # M5/M7 sind lead-direct, nicht via I-Pipeline -> kein Min hier
}

# Set der "echten" I-Pipeline-Step-Skills
I_PIPELINE_STEP_PATTERNS = (
    re.compile(r"^_I_(?!orchestrate$).+"),  # _I_* aber NICHT _I_orchestrate selbst
    re.compile(r"^_TDD_(?!orchestrate$).+"),  # _TDD_* aber NICHT _TDD_orchestrate (deprecated)
)


def _resolve_vault_session_params():
    """Resolve session-params from vault-routing (analog guard_modus_writer.py)."""
    override = os.environ.get("OMNI_GEIST7_SESSION_PARAMS")
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


def get_audit_path():
    override = os.environ.get("OMNI_GEIST7_AUDIT_PATH")
    if override:
        return Path(override)
    return AUDIT_FILE


def read_enforce_process():
    """Liest enforceProcess aus _session_params.md. Default: true."""
    if os.environ.get("OMNI_ENFORCE_GEIST7") == "1":
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


def read_audit_events():
    """Lese audit.jsonl, Zeile-fuer-Zeile, robust gegen Parse-Fehler."""
    audit_path = get_audit_path()
    if not audit_path.exists():
        return []
    events = []
    try:
        for line in audit_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except Exception:
                pass
    except Exception:
        pass
    return events


def is_i_pipeline_step_skill(skill_name):
    """True wenn skill_name ein _I_* oder _TDD_* Step-Skill ist (NICHT der Orchestrator)."""
    if not skill_name:
        return False
    return any(p.match(skill_name) for p in I_PIPELINE_STEP_PATTERNS)


def find_last_i_orchestrate_run(events):
    """Finde Index des letzten SKILL_LOAD _I_orchestrate-Events.

    Returns: idx or None
    """
    for i in range(len(events) - 1, -1, -1):
        e = events[i]
        if e.get("event") == "SKILL_LOAD" and e.get("skill_name") == "_I_orchestrate":
            return i
    return None


def count_i_steps_after(events, start_idx):
    """Zaehle distinct _I_*/_TDD_* SKILL_LOAD-Events zwischen start_idx+1
    und Skill-Wechsel zu Non-_I_/Non-_TDD_-Skill.

    Returns: (count, current_active) where current_active is True solange noch im
    I-Pipeline-Run.
    """
    seen = set()
    current_active = True
    for e in events[start_idx + 1:]:
        if e.get("event") != "SKILL_LOAD":
            continue
        name = e.get("skill_name", "")
        # Re-Start des Orchestrators selbst -> abbrechen (neuer Run)
        if name == "_I_orchestrate":
            current_active = False
            break
        if is_i_pipeline_step_skill(name):
            seen.add(name)
        else:
            # Skill-Wechsel zu nicht-I-Pipeline -> Run geschlossen
            current_active = False
            break
    return len(seen), current_active


def find_bl_manifest_for_event(events, start_idx):
    """Heuristik: ermittele BL-Folder/Manifest-Pfad fuer aktiven I-Run.

    Strategie:
      1. Override via OMNI_GEIST7_MANIFEST_PATH (Test-Modus)
      2. Scan rueckwaerts ab start_idx nach STATE_WRITE auf _manifest.md
         und nimm pfad aus 'file'-Feld -> nicht direkt verfuegbar (audit speichert
         nur Basename). Faellt zurueck auf git status fuer modifizierte Manifeste.
      3. Fallback: None

    Returns: Path or None.
    """
    override = os.environ.get("OMNI_GEIST7_MANIFEST_PATH")
    if override:
        return Path(override)

    # Heuristik via git status (analog process_audit_stop_hook.py)
    try:
        import subprocess
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(ROOT_DIR), timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                m = re.match(r"^\s*[\?MA]+\s+(.+_manifest\.md)\s*$", line)
                if m:
                    candidate = ROOT_DIR / m.group(1)
                    if candidate.exists():
                        return candidate
    except Exception:
        pass
    return None


def read_manifest_context(manifest_path):
    """Lese Modus + Slicing + Pragmatik aus Manifest.

    Returns: dict {modus, slicing, has_pragmatik_reason, raw_content}
    """
    ctx = {
        "modus": None,
        "slicing": False,
        "has_pragmatik_reason": False,
        "raw_content": "",
        "exists": False,
    }
    if not manifest_path or not Path(manifest_path).exists():
        return ctx
    try:
        content = Path(manifest_path).read_text(encoding="utf-8", errors="replace")
        ctx["raw_content"] = content
        ctx["exists"] = True

        # Modus: letzte (juengste) DF_BATCH_STATE-Modus-Mention nehmen
        modus_matches = re.findall(r"(?:^|\n)\s*modus\s*:\s*(M[1-7])", content)
        if modus_matches:
            ctx["modus"] = modus_matches[-1]
        else:
            # Fallback: batch_modes-Map -> nimm erste M{N}
            m = re.search(r"batch_modes\s*:.*?(M[1-7])", content, re.DOTALL)
            if m:
                ctx["modus"] = m.group(1)

        # Slicing
        slicing_match = re.search(r"slicing\s*[:=]\s*(true|false)", content, re.IGNORECASE)
        if slicing_match:
            ctx["slicing"] = slicing_match.group(1).lower() == "true"

        # Pragmatik-Reason (Override)
        if re.search(r"pragmatik_reason\s*:\s*\S+", content):
            ctx["has_pragmatik_reason"] = True
    except Exception:
        pass
    return ctx


def write_audit_event(event_dict):
    """Append ein Event zu audit.jsonl."""
    try:
        audit_path = get_audit_path()
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_dict, ensure_ascii=False) + "\n")
    except Exception:
        pass


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


def mark_process_debt_in_manifest(manifest_path):
    """Setze BL_LIFECYCLE_STATE.process_debt=true idempotent."""
    if not manifest_path:
        return
    try:
        p = Path(manifest_path)
        if not p.exists():
            return
        content = p.read_text(encoding="utf-8", errors="replace")
        # Idempotenz-Check
        if re.search(r"^\s*process_debt\s*:\s*true", content, re.MULTILINE):
            return
        # Append am Ende der Datei (eigene Section)
        addendum = (
            "\n\n## BL_LIFECYCLE_STATE (Geist G#7 Process-Debt)\n"
            f"process_debt: true\n"
            f"process_debt_set_by: guard_geist7_sdf_to_i\n"
            f"process_debt_ts: {datetime.now().isoformat(timespec='seconds')}\n"
        )
        with open(p, "a", encoding="utf-8") as f:
            f.write(addendum)
    except Exception:
        pass


def evaluate_geist7(hook_data):
    """Kern-Logik: pruefe ob aktueller Tool-Call ein I-Pipeline-Abschluss bedeutet
    und ob Min-Skill-Loads erfuellt sind.

    Returns: dict mit {decision: 'pass'|'warn'|'block', message, details}
    """
    tool_name = hook_data.get("tool_name", "")
    tool_input = hook_data.get("tool_input", {})

    # PostToolUse-Hook: wir wollen wissen ob gerade ein Skill(...) ausgeloest wurde,
    # der NICHT _I_/_TDD_ ist -> dann ist das der "Skill-Wechsel der I-Pipeline schliesst".
    # Sonderfall: tool_name != Skill -> passthrough.
    if tool_name != "Skill":
        return {"decision": "pass", "message": "non-skill tool", "details": {}}

    next_skill = ""
    if isinstance(tool_input, dict):
        next_skill = tool_input.get("skill", "")

    # Lese Audit-Events (jetzt-stand, vor unserem post-hook write)
    events = read_audit_events()

    last_idx = find_last_i_orchestrate_run(events)
    if last_idx is None:
        # Noch nie I-Pipeline gestartet -> passthrough
        return {"decision": "pass", "message": "no _I_orchestrate run found", "details": {}}

    # Counter zaehlen mit aktuellem next_skill als implicit "Skill-Wechsel"-Check
    count, run_still_active = count_i_steps_after(events, last_idx)

    # Wenn der next_skill (jetzt gerade aufgerufen) selbst ein I-Step ist
    # UND run_still_active=True -> I-Pipeline laeuft noch, kein Abschluss-Check.
    if run_still_active and is_i_pipeline_step_skill(next_skill):
        return {"decision": "pass", "message": "I-pipeline still active", "details": {"count": count}}

    # Wenn next_skill == _I_orchestrate -> Re-Start oder Resume, kein Abschluss-Check
    if next_skill == "_I_orchestrate":
        return {"decision": "pass", "message": "_I_orchestrate restart", "details": {"count": count}}

    # Wenn run_still_active=True UND next_skill ist ein Non-I-Skill -> Abschluss-Punkt!
    # Wenn run_still_active=False (Wechsel war schon in vergangenen Events) -> auch Abschluss-Punkt.
    # In beiden Faellen: zaehlen und vergleichen.

    # Manifest-Lookup fuer Modus/Slicing/Pragmatik
    manifest_path = find_bl_manifest_for_event(events, last_idx)
    mctx = read_manifest_context(manifest_path)

    modus = mctx["modus"]
    slicing = mctx["slicing"]
    has_pragmatik = mctx["has_pragmatik_reason"]

    if not modus:
        # Modus unbekannt -> kann nicht enforcen, durchlassen mit Warn-Log
        return {
            "decision": "pass",
            "message": "modus undetermined (no manifest or no modus field)",
            "details": {"count": count, "manifest": str(manifest_path) if manifest_path else None},
        }

    if modus not in ("M2", "M3"):
        # M5/M7 sind lead-direct, nicht von G#7 gedeckt
        return {
            "decision": "pass",
            "message": f"modus={modus} not covered by G#7",
            "details": {"count": count, "modus": modus},
        }

    min_required = MIN_SKILL_LOADS.get((modus, slicing))
    if min_required is None:
        return {
            "decision": "pass",
            "message": f"no min defined for modus={modus} slicing={slicing}",
            "details": {"count": count},
        }

    if count >= min_required:
        return {
            "decision": "pass",
            "message": f"min met: {count} >= {min_required}",
            "details": {"count": count, "modus": modus, "slicing": slicing, "min": min_required},
        }

    # VIOLATION
    detail = {
        "count": count,
        "modus": modus,
        "slicing": slicing,
        "min": min_required,
        "manifest": str(manifest_path) if manifest_path else None,
        "has_pragmatik_reason": has_pragmatik,
    }
    if has_pragmatik:
        return {
            "decision": "warn",
            "message": (
                f"G#7 Min-Skill-Loads NICHT erfuellt ({count} < {min_required} fuer "
                f"{modus} slicing={slicing}) — aber pragmatik_reason vorhanden, "
                f"daher WARN-only."
            ),
            "details": detail,
        }
    return {
        "decision": "block",
        "message": (
            f"G#7 PROCESS_BYPASS_DETECTED_{modus}_min={min_required}_actual={count}: "
            f"I-Pipeline-Run zaehlte nur {count} distinct _I_*/_TDD_*-Skill-Loads. "
            f"Erwartet >= {min_required} fuer Modus {modus} (slicing={slicing}). "
            f"Mega-Worker-Drift verdaechtig.\n"
            f"  -> FIX (setzt Prozess fort): restliche {max(0, min_required - count)} "
            f"_I_*/_TDD_*-Schritte der Modus-{modus}-Sequenz als EIGENE Skill-Loads "
            f"nachfahren (nicht inline im Worker), dann erneut. "
            f"Bewusster Kurzpfad: pragmatik_reason im Manifest (DF_BATCH_STATE) setzen."
        ),
        "details": detail,
    }


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

        # PostToolUse-Hook: wir reagieren nur auf Skill-Tool-Calls
        tool_name = hook_data.get("tool_name", "")
        if tool_name != "Skill":
            print(json.dumps({"continue": True}))
            return

        verdict = evaluate_geist7(hook_data)

        if verdict["decision"] == "pass":
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()
        details = verdict["details"]
        modus = details.get("modus", "?")
        min_req = details.get("min", "?")
        actual = details.get("count", "?")
        manifest = details.get("manifest")

        # Audit-Event schreiben
        audit_evt = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "event": f"PROCESS_BYPASS_DETECTED_{modus}_min={min_req}_actual={actual}",
            "geist": "G#7",
            "skill": "_I_orchestrate",
            "decision": verdict["decision"],
            "enforced": enforce and verdict["decision"] == "block",
            "details": details,
        }
        write_audit_event(audit_evt)

        # Manifest-Side-Effect (nur bei block, oder bei warn mit pragmatik dokumentieren)
        if verdict["decision"] == "block" and manifest:
            mark_process_debt_in_manifest(manifest)

        append_guard_log(
            "GEIST7_PROCESS_BYPASS",
            f"modus={modus} min={min_req} actual={actual} pragmatik={details.get('has_pragmatik_reason')}",
            blocked=(verdict["decision"] == "block" and enforce),
        )

        # JSON-Response
        if verdict["decision"] == "warn":
            print(json.dumps({"continue": True, "message": verdict["message"]}))
            return

        # decision == 'block'
        if enforce:
            print(json.dumps({"continue": False, "message": verdict["message"]}))
        else:
            warn_msg = "[WARN enforceProcess=false] " + verdict["message"]
            print(json.dumps({"continue": True, "message": warn_msg}))

    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_geist7_sdf_to_i Error: {e}\n")
        except Exception:
            pass
        # Bei interner Exception immer durchlassen (kein false-Block-Risiko)
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
