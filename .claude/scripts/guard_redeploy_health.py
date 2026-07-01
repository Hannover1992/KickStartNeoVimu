#!/usr/bin/env python3
"""
guard_redeploy_health.py — Redeploy->Health-Seam-Guard (BL-337 PL-337-1, INV-HEALTH-1).

4. HookGuard-Mirror (nach guard_a_idf_handoff / guard_idf_sdf_handoff / guard_stage_seam).
Spiegel von guard_idf_sdf_handoff.py auf der Engine-Austausch-Achse: ein Redeploy tauscht
den Motor, nicht den State. Darum MUSS nach JEDEM Redeploy ein /_health_orchestrate
(report-only Self-Check) laufen, BEVOR der neue Motor State beruehrt (INV-HEALTH-1,
feedback_machine_not_context — Motor-Austausch am fahrenden Auto).

Detektion (PreToolUse Edit/Write):
  WENN Edit/Write (irgendein produktiver State-Write)
  UND der audit ein `SKILL_LOAD _redeploy` zeigt
  UND seit diesem Redeploy KEIN `SKILL_LOAD _health_orchestrate`
  -> Redeploy-Ende ohne Health-Self-Check (Bypass) -> sys.exit(2) + Recovery-Hint.

Ausnahmen (PASS): Kill-Switch (OMNI_REDEPLOY_HEALTH_OFF=1 / OMNI_ENFORCE_ALL_OFF=1);
Gate bereits erfuellt (Health lief NACH Redeploy); gar kein Redeploy im audit
(kein Motor-Austausch -> nichts zu pruefen, no-op fail-safe gegen Over-Triggering).

Detekt-Substrat (KEIN neuer Marker): audit.jsonl SKILL_LOAD-Scan. health_ran_since_redeploy()
= exaktes Analogon zu sdf_ran_since_idf() in guard_idf_sdf_handoff.py.

Template/Blaupause: guard_idf_sdf_handoff.py.
DIP-Analogon: Guard kennt NUR audit-State, NICHT Redeploy-/Health-interne Ablauflogik.

Test-Override: OMNI_REDEPLOY_HEALTH_AUDIT (audit-path, Spiegel von OMNI_IDF_SDF_HANDOFF_AUDIT).
enforce: OMNI_SESSION_PARAMS (enthaelt "enforceProcess: false" -> WARN). Globaler
Owner-Kill-Switch: OMNI_ENFORCE_ALL_OFF=1. Lokaler Off: OMNI_REDEPLOY_HEALTH_OFF=1.

heal-mode CLI-Scope (AK-8, BL-364 F8 — Scope-Entscheidung):
  Dieses Script ist AUSSCHLIESSLICH ein PreToolUse-Hook (stdin-JSON-Protokoll).
  `--mode=heal` ist KEIN implementiertes CLI-Flag (kein argparse fuer --mode).
  Begruendung: heal-mode = Heiler-Dispatch-Naht — der tatsaechliche Heiler-Aufruf
  (Skill(_health_orchestrate)) ist Skill-Sache, NICHT Script-Aufgabe. Das Script
  PLANT die Stamp-Action (bewertet den Guard-Zustand und gibt continue/block), aber
  der Heiler-Dispatch passiert durch den Lead via Skill(_health_orchestrate).
  Falls ein CLI-heal-mode spaeter benoetigt wird: argparse-Stub mit NotImplementedError
  hinzufuegen + AK-8b als proper-fix tracken. Bis dahin: kein --mode-Parsing noetig.
  Verweis: [[BL-364]] AK-8, OA-1.
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

RECOVERY_HINT = (
    "Rufe Skill(_health_orchestrate, args={vault}) — INV-HEALTH-1: nach Redeploy MUSS "
    "/_health (report-only) laufen, bevor der neue Motor State beruehrt."
)


def get_audit_path():
    return Path(os.environ.get("OMNI_REDEPLOY_HEALTH_AUDIT", str(AUDIT_FILE)))


def read_enforce():
    """enforceProcess aus OMNI_SESSION_PARAMS (Test) oder Default true. BLOCK ist Default
    am Trigger-Punkt (Redeploy-Health-Seam darf nicht nur gewarnt werden)."""
    sp = os.environ.get("OMNI_SESSION_PARAMS")
    if sp and Path(sp).exists():
        try:
            txt = Path(sp).read_text(encoding="utf-8", errors="replace")
            if re.search(r"enforceProcess\s*:?\*?\*?\s*false", txt, re.IGNORECASE):
                return False
        except Exception:
            pass
    return True


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **REDEPLOY_HEALTH** [{action}]: {msg}\n")
    except Exception:
        pass


def _redeploy_matches_bl(ev, current_bl_id):
    """AK-1 (BL-364): Pruefe ob ein _redeploy SKILL_LOAD-Event zum aktuellen BL gehoert.

    Wenn CLAUDE_BL_ID gesetzt ist, muss der ctx.feature des Redeploy-Events das gleiche
    BL enthalten. Redeployments fuer fremde BLs werden ignoriert (kein falscher Block).
    Wenn CLAUDE_BL_ID NICHT gesetzt ist, passt jeder Redeploy (Rueckwaertskompatibilitaet).
    """
    if not current_bl_id:
        return True  # kein Scope-Filter ohne BL_ID
    ctx = ev.get("ctx") or {}
    feature = ctx.get("feature") or ""
    # Normalisierter Vergleich: BL-ID muss im feature-String vorkommen
    return current_bl_id.upper() in feature.upper()


def health_ran_since_redeploy(audit_path, current_bl_id=None):
    """Scanne audit rueckwaerts. Returns (redeploy_active, health_since).
      redeploy_active: gab es ein _redeploy SKILL_LOAD (fuer das aktuelle BL)?
      health_since:    _health_orchestrate NACH letztem relevanten _redeploy?

    AK-1 (BL-364): current_bl_id eingrenzt den Scope — fremde BL-Redeployments
    aktivieren den Guard NICHT fuer das aktuelle BL (F3-global-scope-Bug behoben).
    """
    if not audit_path.exists():
        return False, True
    try:
        lines = audit_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False, True

    pos_redeploy = -1
    pos_health = -1
    for i in range(len(lines) - 1, -1, -1):
        try:
            ev = json.loads(lines[i])
        except Exception:
            continue
        skill = ev.get("skill_name") or ev.get("skill") or ""
        cmd = ev.get("command") or ""
        if (pos_redeploy == -1 and ev.get("event") == "SKILL_LOAD" and skill == "_redeploy"
                and ev.get("load_method") != "read"  # BL-367 F12: load_method=read (Doc-Read von _redeploy.md) ist KEIN echter Redeploy
                and _redeploy_matches_bl(ev, current_bl_id)):  # AK-1: nur eigenes BL
            pos_redeploy = i
        if pos_health == -1 and ("_health_orchestrate" in skill or "_health_orchestrate" in cmd):
            pos_health = i
        if pos_redeploy != -1 and pos_health != -1:
            break

    redeploy_active = pos_redeploy != -1
    health_since = pos_health != -1 and pos_health >= pos_redeploy
    return redeploy_active, health_since


def main():
    # === Globaler Owner-Kill-Switch (BL-210): enforceProcess=false -> Guard aus ===
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return
    if os.environ.get("OMNI_REDEPLOY_HEALTH_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    if event.get("tool_name") not in ("Edit", "Write"):
        print(json.dumps({"continue": True}))
        return

    # AK-2 (BL-364): Gen-0-PROCEED — format_version: 0 bedeutet initialer State-Write,
    # kein Motor-Austausch-Risiko (Doktrin: Gen-0 ist OK, Guard darf nicht abbrechen).
    tool_input = event.get("tool_input") or {}
    file_content = tool_input.get("content") or ""
    if file_content and re.search(r"format_version\s*:\s*0\b", file_content):
        print(json.dumps({"continue": True}))
        return

    # AK-1 (BL-364): bl_id-Scope-Filter — nur eigenes BL triggert den Guard
    current_bl_id = os.environ.get("CLAUDE_BL_ID")
    redeploy_active, health_since = health_ran_since_redeploy(get_audit_path(), current_bl_id)

    if not redeploy_active:
        # Kein Motor-Austausch -> nichts zu pruefen (no-op, fail-safe gegen Over-Triggering)
        print(json.dumps({"continue": True}))
        return

    if health_since:
        # _health_orchestrate lief nach Redeploy -> Gate erfuellt
        print(json.dumps({"continue": True}))
        return

    # Redeploy ohne nachfolgenden Health-Self-Check -> Bypass
    fp = (event.get("tool_input", {}) or {}).get("file_path", "")
    enforce = read_enforce()
    msg = (
        f"[GUARD-VIOLATION] REDEPLOY_HEALTH: produktiver State-Write ({Path(fp).name}) nach "
        f"Redeploy, ABER kein Skill(_health_orchestrate) seit _redeploy.\n"
        f"  -> HEALTH-GATE FEHLT (Redeploy->Health, BL-337, INV-HEALTH-1: Motor getauscht, State nicht).\n"
        f"  -> FIX: {RECOVERY_HINT} "
        + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARNED (enforceProcess=false Opt-out).")
    )
    append_guard_log(f"Redeploy-State-Write ohne _health_orchestrate ({Path(fp).name})", enforce)
    print(json.dumps({"continue": not enforce, "message": msg}))
    if enforce:
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_redeploy_health ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
