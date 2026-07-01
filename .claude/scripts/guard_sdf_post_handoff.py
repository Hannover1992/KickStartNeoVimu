#!/usr/bin/env python3
"""
guard_sdf_post_handoff.py — SDF-Post-Handoff-Guard (BL-427, INV-HANDOVER-1).

Schliesst die SDF-Post-Luecke (BL-427): nach jedem I/SC-Build-Caller-Load
(_I_orchestrate / _SC_orchestrate) MUSS vor dem naechsten _SDF_orchestrate-Resume-Load
ein _SDF_orchestrate_post geladen worden sein (INV-HANDOVER-1: Skill-Handschuh-Pfad).

BL-350 enforce-AFTER-write-Pattern (analog guard_a_idf_handoff.py):
  - TRIGGER A (Enforcement): Skill-Load _SDF_orchestrate (NICHT _SDF_orchestrate_post)
    -> prueft ob _SDF_orchestrate_post seit letztem I/SC-Build-Load lief.
  - TRIGGER B (Signal-Write): Edit/Write auf _manifest.md -> IMMER passthrough.

Detektion:
  TRIGGER A — Skill-Load `_SDF_orchestrate`:
    WENN PreToolUse Skill-Load von `_SDF_orchestrate`
    UND seit letztem I/SC-Build (_I_orchestrate / _SC_orchestrate) KEIN _SDF_orchestrate_post
    -> INV-HANDOVER-1-Verletzung -> sys.exit(2) + Recovery-Hint (enforceProcess=true)
    -> WARN + continue=True (enforceProcess=false)

  TRIGGER B (Edit/Write auf `_manifest.md`):
    IMMER durchlassen (continue=True). Kein Pre-Block.

Test-Override: OMNI_SDF_POST_HANDOFF_AUDIT (audit-path). enforce: OMNI_SESSION_PARAMS.
Globaler Off-Switch: OMNI_ENFORCE_ALL_OFF=1.
Lokaler Off-Switch: OMNI_SDF_POST_HANDOFF_OFF=1.

Vorbild: guard_a_idf_handoff.py (BL-226/BL-350).
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

RECOVERY_HINT = "Rufe Skill(_SDF_orchestrate_post) vor naechstem Sub-Batch/Resume"


def get_audit_path():
    return Path(os.environ.get("OMNI_SDF_POST_HANDOFF_AUDIT", str(AUDIT_FILE)))


def _resolve_session_params():
    """Vault-resolved _session_params.md (kanonisch, analog guard_a_idf_handoff);
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
            f.write(f"- [{ts}] **SDF_POST_HANDOFF** [{action}]: {msg}\n")
    except Exception:
        pass


def _is_sdf_orchestrate_skill_load(tool_name, tool_input):
    """True wenn der PreToolUse-Event ein Skill-Load von _SDF_orchestrate ist (TRIGGER A).

    Matcht _SDF_orchestrate aber NICHT _SDF_orchestrate_post (der Post-Guard selbst
    soll nicht als TRIGGER A ausloesen). Substring-Match auf '_SDF_orchestrate' deckt
    args-Varianten ab; expliziter Ausschluss von '_SDF_orchestrate_post'.
    """
    if not tool_name or "execute_skill" not in str(tool_name).lower():
        return False
    if not isinstance(tool_input, dict):
        return False
    skill = (
        tool_input.get("skill_name")
        or tool_input.get("skill")
        or tool_input.get("name")
        or ""
    )
    skill_str = str(skill)
    return "_SDF_orchestrate" in skill_str and "_SDF_orchestrate_post" not in skill_str


def post_sdf_ran_since_i_sc():
    """Scanne audit rueckwaerts. Returns (build_active, post_sdf_since).

      build_active:    gab es einen I/SC-Build-Caller-Load (_I_orchestrate oder _SC_orchestrate)?
      post_sdf_since:  _SDF_orchestrate_post NACH letztem Build-Caller-Load sichtbar?

    Analogon zu postroute_ran_since_a_pipeline() in guard_a_idf_handoff.py.
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

        # Suche nach letztem _SDF_orchestrate_post-Load
        if pos_post == -1 and "_SDF_orchestrate_post" in skill_str:
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
    if os.environ.get("OMNI_SDF_POST_HANDOFF_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    tool_name = event.get("tool_name")
    ti = event.get("tool_input", {}) or {}

    # === TRIGGER A (enforce-AFTER-write): Skill-Load _SDF_orchestrate ===
    if _is_sdf_orchestrate_skill_load(tool_name, ti):
        build_active, post_sdf_since = post_sdf_ran_since_i_sc()
        if (not build_active) or post_sdf_since:
            # Kein Build-Kontext bekannt ODER Post-SDF lief -> legitim
            print(json.dumps({"continue": True}))
            return
        # Build-Caller lief, ABER kein _SDF_orchestrate_post danach -> INV-HANDOVER-1 verletzt
        enforce = read_enforce()
        msg = (
            f"[GUARD-VIOLATION] SDF_POST_HANDOFF: Skill-Load _SDF_orchestrate OHNE vorausgehenden "
            f"Skill(_SDF_orchestrate_post) seit I/SC-Build-Caller.\n"
            f"  -> INV-HANDOVER-1 verletzt: Skill-Handschuh-Pfad erfordert _SDF_orchestrate_post "
            f"nach jedem I/SC-Build vor dem naechsten SDF-Resume.\n"
            f"  -> FIX: {RECOVERY_HINT}. "
            + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARN (enforceProcess=false Opt-out).")
        )
        append_guard_log("SDF-Resume (_SDF_orchestrate) ohne _SDF_orchestrate_post seit I/SC-Build", enforce)
        print(json.dumps({"continue": not enforce, "message": msg}))
        if enforce:
            sys.exit(2)
        return

    # === TRIGGER B (Signal-Write): Edit/Write auf _manifest.md -> IMMER passthrough ===
    if tool_name not in ("Edit", "Write"):
        print(json.dumps({"continue": True}))
        return

    fp = ti.get("file_path", "")
    if "_manifest.md" not in fp:
        print(json.dumps({"continue": True}))
        return

    # Manifest-Write IMMER durchlassen (enforce-AFTER-write-Pattern, BL-350).
    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_sdf_post_handoff ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
