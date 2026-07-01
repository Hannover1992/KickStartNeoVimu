#!/usr/bin/env python3
"""
guard_param_writer_identity.py — Session-Param Writer-Identity-Lock (2026-05-28).

KERN-PRINZIP (3. Auftreten von "Single Authorized Writer"):
  1. INV-MODUS-1: DF_BATCH_STATE.modus → NUR _SDF_berater_modusEntscheidung
  2. _owner=user: User-Params → NUR User
  3. DIESER Guard: Session-Params (GLOBAL_* + _session_params.md) → NUR /_param

Problem (Live-Beweis DCSRE-486 Round 16, 2026-05-28):
  SDF Phase 0 hat GLOBAL_DIFFICULTY/CEILING/FLOOR im Manifest-Header still
  ueberschrieben (easy/opus/opus → normal/sonnet/haiku). Der User-Wille wurde
  von der Maschine uebersteuert = Kontrollverlust.

  Der alte guard_session_params_protection.py blockte nur _session_params.md
  (nicht Manifest-GLOBAL_*) UND nur RICHTUNG (Upgrade) — er konnte User von
  Maschine nicht unterscheiden, blockte deshalb auch legitime User-Upgrades.

Loesung — IDENTITY statt RICHTUNG:
  Session-Param-Felder duerfen NUR geschrieben werden wenn der aktive Skill /_param
  (oder /_backlog) ist. Erkennung via audit.jsonl letztes SKILL_LOAD-Event.
  - Aktiver Skill == _param/_backlog        → ALLOW (autorisierter Writer = User-Befehl)
  - Kein SKILL_LOAD (Human-Direct-Session)  → ALLOW (menschliche Autoritaet)
  - Aktiver Skill == Orchestrator (SDF/IDF/BDF/...) → BLOCK (Maschine darf NICHT)

Geschuetzte Felder:
  _session_params.md:  **difficulty/ceiling/floor/HiL/slicing/enforceProcess/step_adherence_reminder:**
  _manifest.md Header:  **GLOBAL_DIFFICULTY/GLOBAL_CEILING/GLOBAL_FLOOR/GLOBAL_HIL/GLOBAL_SLICING:**

PreToolUse-Hook fuer Edit/Write.
Override: OMNI_PARAM_WRITER_OFF=1 → Guard deaktiviert (Recovery).
Test-Override: OMNI_PARAM_ACTIVE_SKILL=NAME setzt aktiven Skill direkt (pytest).
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
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# Autorisierte Param-Writer (User-Befehls-Skills)
AUTHORIZED_WRITERS = {"_param", "_backlog"}

# Param-Feld-Patterns
SESSION_PARAM_PATTERN = re.compile(
    r"\*\*(difficulty|ceiling|floor|HiL|slicing|enforceProcess|step_adherence_reminder)\s*:\*\*",
    re.IGNORECASE,
)
GLOBAL_PARAM_PATTERN = re.compile(
    r"\*\*(GLOBAL_DIFFICULTY|GLOBAL_CEILING|GLOBAL_FLOOR|GLOBAL_HIL|GLOBAL_SLICING)\s*:\*\*",
    re.IGNORECASE,
)


def detect_active_skill():
    """Liest letztes SKILL_LOAD aus audit.jsonl. Returns skill_name oder None.

    Test-Override: OMNI_PARAM_ACTIVE_SKILL.
    """
    override = os.environ.get("OMNI_PARAM_ACTIVE_SKILL")
    if override is not None:
        return override or None

    audit_path = Path(os.environ.get("OMNI_AUDIT_JSONL_PATH", str(AUDIT_FILE)))
    if not audit_path.exists():
        return None
    try:
        # Lese rueckwaerts — letztes SKILL_LOAD
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


def touches_param_fields(file_path, new_text):
    """Prueft ob der Write Param-Felder beruehrt (je nach Datei-Typ)."""
    if "_session_params.md" in file_path:
        return bool(SESSION_PARAM_PATTERN.search(new_text))
    if "_manifest.md" in file_path or "_factory_manifest.md" in file_path:
        return bool(GLOBAL_PARAM_PATTERN.search(new_text))
    return False


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "ALLOWED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **PARAM_WRITER_IDENTITY** [{action}]: {msg}\n")
    except Exception:
        pass


def main():
    # === Owner-Env-Notbremse (NUR Env, NICHT file-enforceProcess): B4/BL-223 ===
    # SOUVERAENITAETS-Guard: haengt BEWUSST NICHT am file-basierten enforceProcess.
    # Sonst koennte ein Sub-Agent via _session_params.md-Write (enforceProcess:false)
    # seinen EIGENEN Waechter abschalten = agent-erreichbarer Self-Unlock (Generalschluessel,
    # Audit 2026-05-29 B4). Nur die agent-UNERREICHBARE Env-Notbremse + OMNI_PARAM_WRITER_OFF
    # zaehlen. (enforceProcess ist jetzt selbst ein geschuetztes SESSION_PARAM-Feld → B4a.)
    import os as _os, json as _json
    if _os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(_json.dumps({"continue": True}))
        return
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    if os.environ.get("OMNI_PARAM_WRITER_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    if event.get("tool_name") not in ("Edit", "Write"):
        print(json.dumps({"continue": True}))
        return

    ti = event.get("tool_input", {}) or {}
    file_path = ti.get("file_path", "")
    new_text = ti.get("new_string", "") or ti.get("content", "")

    if not touches_param_fields(file_path, new_text):
        print(json.dumps({"continue": True}))
        return

    active = detect_active_skill()

    # Autorisiert: /_param, /_backlog, oder Human-Direct (kein Skill aktiv)
    if active is None or active in AUTHORIZED_WRITERS:
        append_guard_log(f"Param-Write erlaubt (active_skill={active or 'human-direct'})", False)
        print(json.dumps({"continue": True}))
        return

    # Maschine (Orchestrator-Skill aktiv) versucht Param-Write → BLOCK
    msg = (
        f"[GUARD-VIOLATION] PARAM_WRITER_IDENTITY: Skill '{active}' versucht Session-Params "
        f"zu schreiben ({Path(file_path).name}). Session-Params sind USER-souveraen — "
        f"NUR /_param (User-Befehl) darf schreiben. Skills duerfen LESEN, nicht SCHREIBEN. "
        f"BLOCKIERT. (Recovery: OMNI_PARAM_WRITER_OFF=1)"
    )
    append_guard_log(f"Skill '{active}' Param-Write BLOCKIERT ({Path(file_path).name})", True)
    print(json.dumps({"continue": False, "message": msg}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_param_writer_identity ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
