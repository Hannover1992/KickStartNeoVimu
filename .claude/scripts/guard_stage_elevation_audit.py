#!/usr/bin/env python3
"""
guard_stage_elevation_audit.py — off-the-books-Stufen-Elevation-Detektor (BL-486 AK-E E2-FIX).

Schliesst W15 (off-the-books-Elevation): ein Stufen-Inkrement-Event (current_stage bump /
STAGE_INCREMENT / STAGE_ELEVATION / completed_stages-Append / ELEVATE) im audit.jsonl OHNE
vorausgehendes Skill(_SDF_orchestrate_post) SKILL_LOAD ist eine off-the-books-Elevation —
die Stufe wurde erhoeht, ohne dass die Phase-3/4-Post-Bookkeeping-Pflicht (INV-MODUS-7,
INV-HANDOVER-1) lief. Fail-Loud (PT-CMD-011): WARN/FAIL statt stiller Akzeptanz.

Schablone: `post_phase_ran_since_i_pipeline()` (guard_geist9b_sdf_post_inline.py:75-107) —
audit.jsonl-Rueckwaerts-Scan. Hier gespiegelt: pro Inkrement-Event wird rueckwaerts geprueft,
ob ein _SDF_orchestrate_post SKILL_LOAD davor liegt.

INV-STAGE-CHANNEL-1 (Option B, HART): dieses Modul liest AUSSCHLIESSLICH audit.jsonl (Pfad via
OMNI_STAGE_ELEVATION_AUDIT-Override fuer Tests). Es referenziert/liest/schreibt KEINE
Stage-Cursor-Markdown-Datei (das waere Option A = Invarianten-Bruch). Reiner read-only Scan.

Kill-Switch: OMNI_ENFORCE_ALL_OFF=1 (agent-UNERREICHBARE Owner-env, BL-210) → fail-open.
Off (Debug/Opt-out): OMNI_STAGE_ELEVATION_OFF=1.
Test-Override (audit-path): OMNI_STAGE_ELEVATION_AUDIT.
Fail-open-Konvention: jeder unerwartete Fehler → {"continue": true} (Engine-Guard-Konvention).
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

# Post-SDF-Handschuh-Marker (das, was VOR einem Stufen-Inkrement liegen MUSS).
POST_SKILL = "_SDF_orchestrate_post"

# Stufen-Inkrement-Event-Marker (alle Auspraegungen aus dem Blueprint, robust erkannt).
#   - explizites event-Feld: STAGE_INCREMENT / STAGE_ELEVATION / ELEVATE
#   - completed_stages-Append (Stufe als erledigt vermerkt = de-facto Inkrement)
_INCREMENT_EVENTS = {"STAGE_INCREMENT", "STAGE_ELEVATION", "ELEVATE", "ELEVATE_STAGE"}
_COMPLETED_STAGES_RE = re.compile(r"completed_stages", re.IGNORECASE)


def get_audit_path():
    return Path(os.environ.get("OMNI_STAGE_ELEVATION_AUDIT", str(AUDIT_FILE)))


def _parse(line):
    try:
        return json.loads(line)
    except Exception:
        return None


def _is_post_skill_load(ev):
    """True wenn das Event ein _SDF_orchestrate_post SKILL_LOAD ist."""
    if ev is None:
        return False
    skill = ev.get("skill_name") or ev.get("skill") or ""
    cmd = ev.get("command") or ""
    if ev.get("event") == "SKILL_LOAD":
        return POST_SKILL in skill or POST_SKILL in cmd
    # Auch ohne explizites SKILL_LOAD-Event: ein Post-Skill-Marker im skill/command-Feld zaehlt.
    return POST_SKILL in skill or POST_SKILL in cmd


def _is_stage_increment(ev, raw_line):
    """True wenn das Event ein Stufen-Inkrement ist (event-Marker ODER completed_stages-Append)."""
    if ev is None:
        # raw-Zeile parst nicht -> nur grob auf completed_stages pruefen
        return bool(_COMPLETED_STAGES_RE.search(raw_line or ""))
    if ev.get("event") in _INCREMENT_EVENTS:
        return True
    # completed_stages-Append als Inkrement-Surrogat
    if "completed_stages" in ev:
        return True
    return bool(_COMPLETED_STAGES_RE.search(raw_line or ""))


def stage_increment_has_preceding_post(audit_lines):
    """Rueckwaerts-Scan ueber audit.jsonl-Zeilen.

    Returns (ok, offenders):
      ok        : True gdw. JEDES Stufen-Inkrement-Event ein vorausgehendes
                  _SDF_orchestrate_post SKILL_LOAD hat (kein off-the-books).
      offenders : Liste der verletzenden Inkrement-Events (Fail-Loud — die Verstoesse
                  werden benannt, nicht stillgeschwiegen). Leer wenn ok=True.

    Spiegel von post_phase_ran_since_i_pipeline (guard_geist9b_sdf_post_inline.py:75-107):
    pro Inkrement bei Index i wird im Praefix [0..i) geprueft, ob ein Post-SDF-Load liegt.
    """
    lines = list(audit_lines or [])
    parsed = [_parse(ln) for ln in lines]

    offenders = []
    for i in range(len(lines)):
        if not _is_stage_increment(parsed[i], lines[i]):
            continue
        # Rueckwaerts vom Inkrement: liegt ein _SDF_orchestrate_post davor?
        has_preceding = False
        for j in range(i - 1, -1, -1):
            if _is_post_skill_load(parsed[j]):
                has_preceding = True
                break
        if not has_preceding:
            offenders.append(parsed[i] if parsed[i] is not None else {"raw": lines[i]})

    return (len(offenders) == 0), offenders


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **STAGE_ELEVATION_AUDIT** [{action}]: {msg}\n")
    except Exception:
        pass


def _read_audit_lines():
    audit = get_audit_path()
    if not audit.exists():
        return []
    try:
        return audit.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return []


def main():
    # === Owner-Kill-Switch (BL-210): agent-UNERREICHBARE env-Notbremse ===
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    # stdin lesen (PreToolUse-faehig); fail-open bei Parse-Fehler.
    try:
        sys.stdin.read()
    except Exception:
        print(json.dumps({"continue": True}))
        return

    if os.environ.get("OMNI_STAGE_ELEVATION_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    lines = _read_audit_lines()
    ok, offenders = stage_increment_has_preceding_post(lines)

    if ok:
        # Kein off-the-books-Inkrement (oder kein Inkrement vorhanden) -> sauber.
        print(json.dumps({"continue": True}))
        return

    # off-the-books-Elevation erkannt -> Fail-Loud (PT-CMD-011).
    n = len(offenders)
    msg = (
        f"[GUARD-VIOLATION] STAGE_ELEVATION_AUDIT: {n} Stufen-Inkrement(e) im audit.jsonl OHNE "
        f"vorausgehendes Skill({POST_SKILL}) SKILL_LOAD (off-the-books-Elevation, W15).\n"
        f"  -> Die Stufe wurde erhoeht, ohne dass die Post-SDF-Phase 3/4 (recalibrate/postItem/"
        f"statusTransition/modelSync + loopDecision) lief (INV-MODUS-7, INV-HANDOVER-1).\n"
        f"  -> FIX: jedes Stufen-Inkrement MUSS ein vorausgehendes Skill({POST_SKILL}) haben. "
        f"Verletzende Events: {offenders}"
    )
    append_guard_log(f"{n} off-the-books-Inkrement(e) (kein preceding {POST_SKILL})", True)
    print(json.dumps({"continue": False, "message": msg}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_stage_elevation_audit ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
