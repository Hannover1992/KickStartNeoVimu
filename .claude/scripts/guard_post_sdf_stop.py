#!/usr/bin/env python3
"""
guard_post_sdf_stop.py — SDF-Post-Stop-Guard (BL-427, FEUER-Mechanismus — Stop-Hook).

Schliesst den TERMINAL-GAP: wenn ein I/SC-Build-Caller-Load sattfand und der Turn
danach einfach endet ohne _SDF_orchestrate_post (INV-HANDOVER-1 Skill-Handschuh-Pfad),
blockiert dieser Stop-Hook den Turn-Ende.

Komplement zu guard_sdf_post_handoff.py (PreToolUse-Guard): der PreToolUse-Guard
faengt den naechsten _SDF_orchestrate-Resume ohne Post; dieser Stop-Hook faengt
den terminalen Flow-Abbruch nach I/SC-Build ohne Post.

hook_event=Stop: laeuft bei Turn-Ende / Goal-Termination.

Soll-Semantik:
  1. Scanne audit.jsonl rueckwaerts.
  2. Wenn juengste Orchestrator-Level-Aktion ein Build-Caller ist
     (_I_orchestrate / _SC_orchestrate, SKILL_LOAD)
  3. UND seitdem KEIN _SDF_orchestrate_post-Load UND kein _SDF_orchestrate-Resume
     (kein Weiter-Ringen mit SDF, das den Post haette nachholen koennen)
  4. -> VIOLATION.
  5. VIOLATION + enforceProcess=true -> {"continue": false} + Block-Reason.
  6. VIOLATION + enforceProcess=false -> WARN + {"continue": true}.
  7. Kein Build-Caller als juengste Aktion / Post bereits gefeuert -> {"continue": true}.
  8. Off-Switches: OMNI_ENFORCE_ALL_OFF=1 + OMNI_POST_SDF_STOP_OFF=1 -> {"continue": true}.
  9. Kein audit.jsonl -> fail-open -> {"continue": true}.

Test-Override: OMNI_POST_SDF_STOP_AUDIT (audit-path). enforce: OMNI_SESSION_PARAMS.
Globaler Off-Switch: OMNI_ENFORCE_ALL_OFF=1.
Lokaler Off-Switch: OMNI_POST_SDF_STOP_OFF=1.

Vorbild: guard_sdf_post_handoff.py (BL-427 Schwester).
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

# Build-Caller-Skill-Namen (I/SC)
_BUILD_CALLERS = ("_I_orchestrate", "_SC_orchestrate")

BLOCK_REASON = (
    "Skill(_SDF_orchestrate_post) muss am I/SC-Ende gefeuert werden (BL-427 FEUER-Mechanismus)"
)


def get_audit_path():
    return Path(os.environ.get("OMNI_POST_SDF_STOP_AUDIT", str(AUDIT_FILE)))


def _resolve_session_params():
    """Vault-resolved _session_params.md (kanonisch, analog guard_sdf_post_handoff);
    Fallback ROOT_DIR/_session_params.md."""
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


def _enforce_in_text(txt):
    """True/False aus enforceProcess-Zeile (bold **..** oder plain); None wenn nicht gefunden."""
    m = re.search(r"enforceProcess[\s:*]*\b(true|false)\b", txt, re.IGNORECASE)
    if m:
        return m.group(1).strip().lower() == "true"
    return None


def read_enforce():
    """enforceProcess-Quelle: OMNI_SESSION_PARAMS (Test-Override) >
    vault-resolved _session_params.md (kanonisch) > Default true."""
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


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **POST_SDF_STOP** [{action}]: {msg}\n")
    except Exception:
        pass


def post_sdf_ran_since_i_sc():
    """Scanne audit rueckwaerts. Returns (build_active, post_sdf_since).

      build_active:    gab es einen I/SC-Build-Caller-Load (_I_orchestrate oder _SC_orchestrate)?
      post_sdf_since:  _SDF_orchestrate_post NACH letztem Build-Caller-Load sichtbar?

    Analogon zu post_sdf_ran_since_i_sc() in guard_sdf_post_handoff.py.
    """
    audit = get_audit_path()
    if not audit.exists():
        return False, True  # fail-open: kein Audit -> kein Build-Kontext bekannt

    try:
        lines = audit.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False, True

    pos_build = -1   # Index des letzten Build-Caller-Loads
    pos_post = -1    # Index des letzten _SDF_orchestrate_post-Loads

    for i in range(len(lines) - 1, -1, -1):
        try:
            ev = json.loads(lines[i])
        except Exception:
            continue
        skill = ev.get("skill_name") or ev.get("skill") or ev.get("command") or ""
        skill_str = str(skill)

        # Suche nach letztem Build-Caller (I/SC)
        if pos_build == -1 and ev.get("event") == "SKILL_LOAD":
            for caller in _BUILD_CALLERS:
                if caller in skill_str:
                    pos_build = i
                    break

        # Suche nach letztem _SDF_orchestrate_post-Load ODER _SDF_orchestrate-Resume
        if pos_post == -1 and (
            "_SDF_orchestrate_post" in skill_str
            or ("_SDF_orchestrate" in skill_str and "_SDF_orchestrate_post" not in skill_str
                and ev.get("event") == "SKILL_LOAD")
        ):
            pos_post = i

        # Fruehzeitiger Abbruch wenn beide gefunden
        if pos_build != -1 and pos_post != -1:
            break

    build_active = pos_build != -1
    # Post-SDF gilt als "since" wenn es NACH (groesserer Index) dem Build-Caller kam
    post_sdf_since = pos_post != -1 and pos_post > pos_build
    return build_active, post_sdf_since


def main():
    # === Globaler Off-Switch ===
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return
    # === Lokaler Off-Switch ===
    if os.environ.get("OMNI_POST_SDF_STOP_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    try:
        _event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    build_active, post_sdf_since = post_sdf_ran_since_i_sc()

    if not build_active or post_sdf_since:
        # Kein Build-Kontext bekannt ODER Post-SDF lief -> legitim
        print(json.dumps({"continue": True}))
        return

    # Build-Caller lief, ABER kein _SDF_orchestrate_post danach -> TERMINAL-GAP / INV-HANDOVER-1
    enforce = read_enforce()
    msg = (
        f"[GUARD-VIOLATION] POST_SDF_STOP: Turn-Ende nach I/SC-Build-Caller OHNE "
        f"Skill(_SDF_orchestrate_post).\n"
        f"  -> INV-HANDOVER-1 verletzt: TERMINAL-GAP — _SDF_orchestrate_post muss am "
        f"I/SC-Ende gefeuert werden (BL-427 FEUER-Mechanismus).\n"
        f"  -> FIX: Skill(_SDF_orchestrate_post) laden. "
        + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARN (enforceProcess=false Opt-out).")
    )
    append_guard_log(
        "Turn-Ende (_SDF_orchestrate_post fehlt) nach I/SC-Build-Caller", enforce
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
                log.write(f"[{datetime.now()}] guard_post_sdf_stop ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
