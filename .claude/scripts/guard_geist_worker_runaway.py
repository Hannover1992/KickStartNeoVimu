#!/usr/bin/env python3
"""
guard_geist_worker_runaway.py — INV-SPAWN Role-Scope-Lock (CRITICAL).

5. Auftreten des "Single Authorized Writer"-Prinzips:
  1. INV-MODUS-1     → DF_BATCH_STATE.modus nur _SDF_berater_modusEntscheidung
  2. _owner=user     → User-Params nur User
  3. Param-Identity  → GLOBAL_* nur /_param
  4. geist7b         → SDF→I-Dispatch nur via Skill(_I_orchestrate)
  5. DIESER Guard    → BERATER_OUTPUTS.{phase} nur der Worker DIESER Phase

Problem (DCSRE-486 Round 17, 2x):
  Worker 'idf-resumeGuard-r17' wurde fuer NUR Phase 0 (resumeGuard) gespawnt.
  INV-SPAWN: "Worker macht 1 Phase, meldet via SendMessage, STIRBT."
  Stattdessen fuehrte er autonom Phasen 4-8.0 aus und schrieb FREMDE BERATER_OUTPUTS
  (batchPlan, stagePlanner, metricPlanner, finalSummary) = Mega-Agent auf Worker-Ebene.

  Kein bestehender Hook fing das: geist7b faengt SDF→general-sonnet-Spawn (Dispatch-Bypass),
  aber NICHT einen bereits laufenden Worker der INLINE fremde Phasen-Outputs schreibt.

Detektor (PreToolUse Edit/Write auf _manifest.md):
  - Extrahiere worker-role aus OMNI_AGENT_NAME (idf-resumeGuard-r17 → resumeGuard).
  - Extrahiere alle BERATER_OUTPUTS-Berater-Namen aus dem Write.
  - Wenn IRGENDEIN Berater-Name NICHT zur worker-role passt → RUNAWAY → BLOCK.
  - EXEMPT: kein OMNI_AGENT_NAME (Team Lead, Konsolidierungs-Autoritaet) → allow.
  - EXEMPT: Berater-Name == worker-role (Worker schreibt EIGENE Phase) → allow.

Cross-Platform: subprocess IMMER [sys.executable, ...] (NIE 'python' — Windows hat nur py-3).
enforceProcess-Toggle. Override: OMNI_WORKER_RUNAWAY_OFF=1. Test: OMNI_ENFORCE_WORKER_RUNAWAY=1.
fail-open bei Hook-Crash.
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
AUDIT_FILE = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# Pipeline-Prefixe die aus dem Agent-Namen gestrippt werden zur Rollen-Extraktion
PIPELINE_PREFIXES = ("idf-", "sdf-", "sc-", "i-", "bdf-", "a-", "post-", "pre-")

# BERATER_OUTPUTS-Block-Header: BERATER_OUTPUTS_{berater}_roundN  ODER  BERATER_OUTPUTS.{berater}
BERATER_KEY_PATTERN = re.compile(
    r"BERATER_OUTPUTS[._]([A-Za-z][A-Za-z0-9_]*?)(?:_round\d+|_r\d+|\.|\s|:|$)",
    re.MULTILINE,
)


def normalize(s):
    """Lowercase + nur Alphanumerisch (entfernt _, -, camelCase-Grenzen egal)."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def extract_worker_role():
    """OMNI_AGENT_NAME → role-token. None wenn kein Agent (= Team Lead)."""
    name = os.environ.get("OMNI_AGENT_NAME", "").strip()
    if not name:
        return None
    role = name
    # Pipeline-Prefix strippen
    for p in PIPELINE_PREFIXES:
        if role.lower().startswith(p):
            role = role[len(p):]
            break
    # Round-Suffix strippen: -r17, -round17, -17
    role = re.sub(r"-(?:r|round)?\d+$", "", role)
    return role or None


def extract_berater_names(content):
    """Alle BERATER_OUTPUTS-Berater-Namen aus dem Write-Content."""
    return BERATER_KEY_PATTERN.findall(content or "")


def read_enforce():
    if os.environ.get("OMNI_ENFORCE_WORKER_RUNAWAY") == "1":
        return True
    if os.environ.get("OMNI_ENFORCE_WORKER_RUNAWAY") == "0":
        return False
    sp = _resolve_vault_root() / "_session_params.md"
    try:
        if sp.exists():
            content = sp.read_text(encoding="utf-8")
            m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
            if m:
                return m.group(1) == "true"
    except Exception:
        pass
    return True


def _resolve_vault_root():
    try:
        import subprocess
        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True, text=True, timeout=5, cwd=str(ROOT_DIR),
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return Path(proc.stdout.strip())
    except Exception:
        pass
    return ROOT_DIR


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **WORKER_RUNAWAY** [{action}]: {msg}\n")
    except Exception:
        pass


def append_audit(detail):
    try:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now().isoformat(),
                "event": "WORKER_RUNAWAY_BLOCKED",
                "detail": detail,
            }) + "\n")
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
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    if os.environ.get("OMNI_WORKER_RUNAWAY_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    if event.get("tool_name") not in ("Edit", "Write"):
        print(json.dumps({"continue": True}))
        return

    ti = event.get("tool_input", {}) or {}
    file_path = ti.get("file_path", "")
    if "_manifest.md" not in file_path and "_factory_manifest.md" not in file_path:
        print(json.dumps({"continue": True}))
        return

    new_content = ti.get("new_string", "") or ti.get("content", "")
    berater_names = extract_berater_names(new_content)
    if not berater_names:
        # Kein BERATER_OUTPUTS-Write → dieser Guard ist nicht zustaendig
        print(json.dumps({"continue": True}))
        return

    role = extract_worker_role()
    if role is None:
        # Team Lead (kein OMNI_AGENT_NAME) → Konsolidierungs-Autoritaet, exempt
        print(json.dumps({"continue": True}))
        return

    role_norm = normalize(role)
    foreign = []
    for bn in berater_names:
        bn_norm = normalize(bn)
        # Match wenn role_norm in bn_norm ODER bn_norm in role_norm (beide Richtungen)
        if role_norm and bn_norm and (role_norm in bn_norm or bn_norm in role_norm):
            continue
        foreign.append(bn)

    if not foreign:
        # Alle geschriebenen Berater-Outputs gehoeren zur eigenen Rolle → allow
        print(json.dumps({"continue": True}))
        return

    # RUNAWAY: Worker schreibt fremde BERATER_OUTPUTS
    enforce = read_enforce()
    agent_name = os.environ.get("OMNI_AGENT_NAME", "?")
    msg = (
        f"[GUARD-VIOLATION] WORKER_RUNAWAY (INV-SPAWN): Worker '{agent_name}' (role='{role}') "
        f"schreibt FREMDE BERATER_OUTPUTS {foreign}. Ein Worker darf NUR seine eigene Phase "
        f"schreiben, dann STERBEN (Single-Unit-of-Work). Folge-Phasen sind Lead-Aufgabe "
        f"(neuer Worker-Spawn). DCSRE-486 Round 17 Runaway-Pattern. "
        + ("BLOCKIERT." if enforce else "WARNED.")
    )
    append_guard_log(f"'{agent_name}' role='{role}' → foreign={foreign}", enforce)
    append_audit({"agent": agent_name, "role": role, "foreign_berater": foreign})
    print(json.dumps({"continue": not enforce, "message": msg}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_geist_worker_runaway ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
