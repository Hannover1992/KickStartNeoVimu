#!/usr/bin/env python3
"""
guard_lane_closure_stop.py — Lane-Closure-Stop-Guard (BL-444, INV-CLOSURE-1 — Stop-Hook).

Schliesst die STALL-Luecke nach SDF-TERMINATE in Lane/Goal-Modus:
Wenn die Lane nach TERMINATE noch pending BLs hat (next_bl != None) und KEIN
LANE_CLOSURE_CHAIN-Event sichtbar ist, wird der Turn-Ende geblockt (enforce=true)
oder gewarnt (enforce=false).

Soll-Semantik (Stop-Hook):
  1. Off-Switches: OMNI_ENFORCE_ALL_OFF=1 + OMNI_LANE_CLOSURE_STOP_OFF=1 -> {"continue": true}
  2. hil = read_hil_with_fallback(); hil != "off" -> {"continue": true}  [AK-5: hil=on kein Block]
  3. TERMINATE_event = audit-Scan: POST_SDF_EXIT mode=terminate vorhanden?
  4. lane_oder_goal = lane-Param in session_params ODER goal_mode=true
  5. next_bl = lane_plan.next_bl_for_lane(my_lane, plan, done) — direkt aufgerufen
  6. next_bl == None -> {"continue": true}  [leere Lane, kein Fehler]
  7. chain_event = audit-Scan: LANE_CLOSURE_CHAIN vorhanden NACH letztem TERMINATE?
  8. VIOLATION = TERMINATE_event AND lane_oder_goal AND next_bl != None AND NOT chain_event
  9. VIOLATION + enforce=true  -> {"continue": false} + sys.exit(2) + Recovery-Hint
  10. VIOLATION + enforce=false -> WARN + {"continue": true}
  11. kein TERMINATE / chain_event vorhanden / next_bl=None -> fail-open {"continue": true}

Recovery-Hint: "Skill(_A_orchestrate, {next_bl})"

Test-Override-Env-Vars:
  OMNI_LANE_CLOSURE_STOP_AUDIT       — audit-Pfad
  OMNI_SESSION_PARAMS                — session_params-Pfad
  OMNI_LANE_CLOSURE_STOP_LANE_PLAN   — lane_plan-Pfad
  OMNI_ENFORCE_ALL_OFF               — globaler Off-Switch
  OMNI_LANE_CLOSURE_STOP_OFF         — lokaler Off-Switch

Vorbild: guard_autochain_stop.py (BL-394).
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
AUDIT_FILE = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# hil-Regex (Fallback wenn session_params_resolver-Import scheitert)
_HIL_RE = re.compile(r"(GLOBAL_HIL|HiL|hil)\s*:?\s*\**\s*(\w+)", re.IGNORECASE)

# Lane-Regex fuer session_params (diverse Formate: **lane:** A / **lane**: A / lane: A)
_LANE_RE = re.compile(r"\*\*lane\*?\*?:?\*?\*?\s*:?\s*(\w+)", re.IGNORECASE)
_LANE_RE2 = re.compile(r"^lane\s*:\s*(\w+)", re.IGNORECASE | re.MULTILINE)


def get_audit_path() -> Path:
    return Path(os.environ.get("OMNI_LANE_CLOSURE_STOP_AUDIT", str(AUDIT_FILE)))


def get_lane_plan_path():
    """Lane-Plan-Pfad: OMNI_LANE_CLOSURE_STOP_LANE_PLAN (Test-Override) >
    vault-resolved _lane_plan.md. None wenn nicht aufloesbar."""
    override = os.environ.get("OMNI_LANE_CLOSURE_STOP_LANE_PLAN")
    if override:
        return Path(override)
    try:
        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True, text=True, timeout=5, cwd=str(ROOT_DIR),
            )
            if proc.returncode == 0:
                vr = proc.stdout.strip()
                if vr:
                    return Path(vr) / "_lane_plan.md"
    except Exception:
        pass
    return None


def _resolve_session_params() -> Path:
    """Vault-resolved _session_params.md; Fallback ROOT_DIR/_session_params.md."""
    try:
        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True, text=True, timeout=5, cwd=str(ROOT_DIR),
            )
            if proc.returncode == 0:
                vr = proc.stdout.strip()
                if vr:
                    cand = Path(vr) / "_session_params.md"
                    if cand.exists():
                        return cand
    except Exception:
        pass
    return ROOT_DIR / "_session_params.md"


def read_hil_with_fallback() -> str:
    """HiL-Wert: OMNI_SESSION_PARAMS (Test-Override) > vault-resolved _session_params.md.
    Default 'off' (fail-safe pass, aber hil=off bedeutet Guard greift)."""
    sp = os.environ.get("OMNI_SESSION_PARAMS")
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from session_params_resolver import read_hil_with_fallback as _rhwf
        return _rhwf(sp)
    except Exception:
        pass
    # Lokaler Fallback
    try:
        if sp and Path(sp).exists():
            txt = Path(sp).read_text(encoding="utf-8", errors="replace")
        else:
            vsp = _resolve_session_params()
            txt = vsp.read_text(encoding="utf-8", errors="replace") if vsp.exists() else ""
        m = _HIL_RE.search(txt)
        if m:
            return m.group(2).lower()
    except Exception:
        pass
    return "off"


def _enforce_in_text(txt: str):
    """True/False aus enforceProcess-Zeile; None wenn nicht gefunden."""
    m = re.search(r"enforceProcess[\s:*]*\b(true|false)\b", txt, re.IGNORECASE)
    if m:
        return m.group(1).strip().lower() == "true"
    return None


def read_enforce() -> bool:
    """enforceProcess: OMNI_SESSION_PARAMS > vault _session_params.md > Default true."""
    sp = os.environ.get("OMNI_SESSION_PARAMS")
    if sp and Path(sp).exists():
        try:
            v = _enforce_in_text(Path(sp).read_text(encoding="utf-8", errors="replace"))
            if v is not None:
                return v
        except Exception:
            pass
        return True
    try:
        vsp = _resolve_session_params()
        if vsp.exists():
            v = _enforce_in_text(vsp.read_text(encoding="utf-8", errors="replace"))
            if v is not None:
                return v
    except Exception:
        pass
    return True


def read_lane_from_session_params() -> str:
    """Liest lane-Param aus session_params. Gibt '' wenn nicht gefunden."""
    sp = os.environ.get("OMNI_SESSION_PARAMS")
    txt = ""
    if sp and Path(sp).exists():
        try:
            txt = Path(sp).read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass
    else:
        try:
            vsp = _resolve_session_params()
            if vsp.exists():
                txt = vsp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            pass

    # Bold format: **lane:** A
    m = _LANE_RE.search(txt)
    if m:
        return m.group(1).strip()
    # Plain format: lane: A
    m2 = _LANE_RE2.search(txt)
    if m2:
        return m2.group(1).strip()
    return ""


def read_lane_plan_plan():
    """Liest den Lane-Plan. Gibt None bei Fehler (fail-open)."""
    lp_path = get_lane_plan_path()
    if lp_path is None or not Path(lp_path).exists():
        return None
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from lane_plan import parse_lane_plan
        return parse_lane_plan(lp_path)
    except Exception:
        return None


def scan_audit_for_terminate_and_chain(audit_path: Path = None):
    """Scanne audit.

    Returns (terminate_found, chain_after_terminate):
      terminate_found: True wenn POST_SDF_EXIT mode=terminate vorhanden.
      chain_after_terminate: True wenn LANE_CLOSURE_CHAIN NACH dem letzten TERMINATE.
    """
    audit = audit_path if audit_path is not None else get_audit_path()
    audit = Path(audit)
    if not audit.exists():
        return False, False

    try:
        lines = audit.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False, False

    # Alle Events in Reihenfolge einlesen
    events = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            ev = json.loads(line)
            events.append(ev)
        except Exception:
            continue

    # Letzten TERMINATE-Index finden
    last_terminate_idx = -1
    for i, ev in enumerate(events):
        ev_type = ev.get("type", "")
        mode = ev.get("mode", "")
        if ev_type == "POST_SDF_EXIT" and mode == "terminate":
            last_terminate_idx = i

    if last_terminate_idx == -1:
        return False, False

    # LANE_CLOSURE_CHAIN nach letztem TERMINATE suchen
    chain_found = False
    for i in range(last_terminate_idx + 1, len(events)):
        if events[i].get("type") == "LANE_CLOSURE_CHAIN":
            chain_found = True
            break

    return True, chain_found


def append_guard_log(msg: str, blocked: bool) -> None:
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **LANE_CLOSURE_STOP** [{action}]: {msg}\n")
    except Exception:
        pass


def main():
    # === Off-Switches ===
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return
    if os.environ.get("OMNI_LANE_CLOSURE_STOP_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    try:
        _event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    # === hil-Gate: nur unter hil=off greift der Lane-Closure-Schutz (AK-5) ===
    hil = read_hil_with_fallback()
    if hil != "off":
        # hil=on: kein Auto-Block, User entscheidet
        print(json.dumps({"continue": True}))
        return

    # === TERMINATE-Event-Scan ===
    audit_path = get_audit_path()
    terminate_found, chain_after_terminate = scan_audit_for_terminate_and_chain(audit_path)

    if not terminate_found:
        # Kein TERMINATE -> kein Block
        print(json.dumps({"continue": True}))
        return

    # === Lane/Goal-Modus pruefen ===
    my_lane = read_lane_from_session_params()
    # lane_oder_goal: wenn lane-Param gesetzt (nicht leer)
    lane_oder_goal = bool(my_lane)
    if not lane_oder_goal:
        # Kein Lane-Modus -> kein Block
        print(json.dumps({"continue": True}))
        return

    # === next_bl bestimmen ===
    plan = read_lane_plan_plan()
    if plan is None:
        # Kein Plan lesbar -> fail-open
        print(json.dumps({"continue": True}))
        return

    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from lane_plan import next_bl_for_lane
        lane_entry = plan.get(my_lane, {})
        done_list = lane_entry.get("done", []) or []
        done_set = set(done_list)
        next_bl = next_bl_for_lane(my_lane, plan, done_set)
    except Exception:
        # Fehler beim Lane-Plan-Lesen -> fail-open
        print(json.dumps({"continue": True}))
        return

    if next_bl is None:
        # Leere Lane -> legitimes Ende, kein Block
        print(json.dumps({"continue": True}))
        return

    # === Chain-Event-Check ===
    if chain_after_terminate:
        # Chain wurde bereits ausgefuehrt -> kein Block
        print(json.dumps({"continue": True}))
        return

    # === VIOLATION: TERMINATE + lane_oder_goal + next_bl != None + kein chain_event ===
    enforce = read_enforce()
    recovery_hint = f"Skill(_A_orchestrate, {next_bl})"
    msg = (
        f"[GUARD-VIOLATION] LANE_CLOSURE_STOP (BL-444, INV-CLOSURE-1): "
        f"Turn-Ende nach SDF-TERMINATE in Lane '{my_lane}' mit pending next_bl='{next_bl}' "
        f"OHNE LANE_CLOSURE_CHAIN-Event.\n"
        f"  -> STALL-Schutz: Lane hat noch offene Items nach TERMINATE. "
        f"Chain muss explizit ausgefuehrt werden.\n"
        f"  -> FIX: {recovery_hint}. "
        + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARN (enforceProcess=false Opt-out).")
    )
    append_guard_log(
        f"Turn-Ende nach TERMINATE in Lane '{my_lane}' mit pending next_bl='{next_bl}' ohne Chain",
        enforce,
    )

    if enforce:
        print(json.dumps({"continue": False, "message": msg}))
        sys.exit(2)
    else:
        print(json.dumps({"continue": True, "message": msg}), file=sys.stderr)
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_lane_closure_stop ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
