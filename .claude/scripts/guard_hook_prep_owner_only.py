#!/usr/bin/env python3
"""
guard_hook_prep_owner_only.py — Owner-Only-Enforcement fuer /_hook_workaround.

KERN-INVARIANTE: /_hook_workaround darf NUR vom Menschen (Main-Session Team Lead)
aufgerufen werden, NIEMALS von einem Sub-Agent / Worker.

Begruendung:
  /_hook_workaround bereitet Daten so vor dass Hooks durchlassen (bewusster Override).
  Das ist MENSCHLICHE AUTORITAET — der Mensch sieht einen False-Positive, uebernimmt
  Verantwortung, normalisiert. Ein Agent kann real-drift NICHT von false-positive
  unterscheiden (genau deshalb existieren die Hooks). Wuerde ein Agent /_hook_prep
  nutzen, koennte er Drift kaschieren (Drift-Laundering). VERBOTEN.

Detektion Mensch vs Agent:
  - Worker/Sub-Agent haben OMNI_AGENT_NAME env gesetzt (z.B. "idf-resumeguard").
  - Main-Session Team Lead hat OMNI_AGENT_NAME NICHT gesetzt.
  - Wenn OMNI_AGENT_NAME gesetzt UND Skill == _hook_prep -> BLOCK (immer, kein Toggle).

PreToolUse-Hook fuer Skill-Tool. Triggert nur bei Skill(_hook_prep).
HARTER Block (kein enforceProcess-Toggle — Owner-Only ist absolut, Bootstrap-Schutz:
schuetzt den Override-Mechanismus selbst). Owner-Notbremse: OMNI_HOOK_PREP_OFF=1
setzt den Agent-Block bewusst aus (Symmetrie zu OMNI_PARAM_WRITER_OFF=1).
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
AUDIT_FILE = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

PROTECTED_SKILL = "_hook_workaround"

# Env-Vars die einen Agent/Worker-Kontext markieren
AGENT_CONTEXT_MARKERS = ("OMNI_AGENT_NAME", "OMNI_WORKER_ID", "OMNI_SUBAGENT")


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "ALLOWED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **HOOK_PREP_OWNER_ONLY** [{action}]: {msg}\n")
    except Exception:
        pass


def append_audit(event, detail):
    try:
        AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "ts": datetime.now().isoformat(),
                "event": event,
                "detail": detail,
            }) + "\n")
    except Exception:
        pass


def detect_agent_context():
    """Gibt Agent-Name zurueck wenn Agent-Kontext, sonst None (= Main-Session)."""
    for marker in AGENT_CONTEXT_MARKERS:
        val = os.environ.get(marker)
        if val:
            return f"{marker}={val}"
    return None


def main():
    # === Owner-Env-Notbremse (NUR Env, NICHT file-enforceProcess): B4/BL-223 ===
    # SOUVERAENITAETS-Guard (Owner-Only, absolut): haengt BEWUSST NICHT am
    # file-basierten enforceProcess — sonst koennte ein Sub-Agent via
    # _session_params.md-Write seinen eigenen Waechter abschalten (Self-Unlock,
    # Audit 2026-05-29 B4). Nur die agent-UNERREICHBARE Env-Notbremse +
    # OMNI_HOOK_PREP_OFF zaehlen.
    import os as _os, json as _json
    if _os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(_json.dumps({"continue": True}))
        return
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    if event.get("tool_name") != "Skill":
        print(json.dumps({"continue": True}))
        return

    tool_input = event.get("tool_input", {}) or {}
    skill = tool_input.get("skill", "")
    if skill != PROTECTED_SKILL:
        print(json.dumps({"continue": True}))
        return

    # Owner-Notbremse (Symmetrie zu OMNI_PARAM_WRITER_OFF): der Owner kann den
    # Agent-Block bewusst aussetzen. Env-Vars setzt nur der Launcher/Owner — ein
    # Sub-Agent kann die Parent-Env des Hook-Subprozesses NICHT aendern, daher
    # bleibt das Owner-souveraen (kein Drift-Laundering-Loch). Dieser Guard hoert
    # NICHT auf enforceProcess (Bootstrap-Schutz: er schuetzt den Override-Mechanismus
    # selbst), aber der Owner hat hier seine explizite, eigene Notbremse.
    if os.environ.get("OMNI_HOOK_PREP_OFF") == "1":
        append_guard_log("Owner-Hatch OMNI_HOOK_PREP_OFF=1 — Agent-Block ausgesetzt", False)
        append_audit("HOOK_PREP_OWNER_HATCH", {"reason": "OMNI_HOOK_PREP_OFF=1"})
        print(json.dumps({"continue": True}))
        return

    # /_hook_prep wird geladen — pruefe Kontext
    agent_ctx = detect_agent_context()
    if agent_ctx:
        # AGENT versucht /_hook_prep zu nutzen -> HARTER BLOCK
        msg = (
            f"[GUARD-VIOLATION] HOOK_PREP_OWNER_ONLY: /_hook_workaround ist OWNER-ONLY. "
            f"Agent-Kontext erkannt ({agent_ctx}). "
            f"Begruendung: /_hook_workaround bereitet Hook-Preconditions vor (bewusster Override) — "
            f"das ist MENSCHLICHE Autoritaet. Agents koennen Drift nicht von False-Positive "
            f"unterscheiden. VERBOTEN fuer Agents (Anti-Drift-Laundering). BLOCKIERT."
        )
        append_guard_log(f"Agent-Versuch ({agent_ctx}) BLOCKIERT", True)
        append_audit("HOOK_PREP_AGENT_BLOCKED", {"agent_ctx": agent_ctx})
        print(json.dumps({"continue": False, "message": msg}))
        return

    # Main-Session (Mensch) -> erlauben + loggen
    append_guard_log("Main-Session (Owner) — /_hook_prep erlaubt", False)
    append_audit("HOOK_PREP_OWNER_INVOKED", {"context": "main_session"})
    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_hook_prep_owner_only ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
