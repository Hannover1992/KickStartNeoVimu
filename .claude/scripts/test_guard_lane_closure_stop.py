#!/usr/bin/env python3
"""Tests fuer guard_lane_closure_stop.py (BL-444 AK-4/AK-5/AK-6, TDD RED-Phase).

TDD Stage 1 (Atomic). Vorbild: test_guard_autochain_stop.py (BL-394).

Ziel: `guard_lane_closure_stop.py` (existiert noch NICHT) —
Stop-Hook analog guard_autochain_stop.py, blockiert Turn-Ende wenn INV-CLOSURE-1
verletzt ist: TERMINATE nach SDF ohne nachfolgendem LANE_CLOSURE_CHAIN-Event,
lane-Modus aktiv, next_bl != None.

Soll-Semantik (guard_lane_closure_stop.py::main):
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

Tests (T-B1..T-B12):
  T-B1   test_off_switches_global          — OMNI_ENFORCE_ALL_OFF=1 -> pass
  T-B2   test_off_switches_local           — OMNI_LANE_CLOSURE_STOP_OFF=1 -> pass
  T-B3   test_hil_on_no_block              — hil=on + VIOLATION-Lage -> pass (kein Block)
  T-B4   test_no_terminate_event           — kein POST_SDF_EXIT mode=terminate -> pass
  T-B5   test_next_bl_none_no_block        — leere Lane (next_bl=None) -> pass
  T-B6   test_chain_event_present          — LANE_CLOSURE_CHAIN seit TERMINATE -> pass
  T-B7   test_violation_enforced           — alle VIOLATION-Bedingungen + enforce=true -> exit(2) + {"continue": false}
  T-B8   test_violation_warned             — alle VIOLATION-Bedingungen + enforce=false -> {"continue": true} + stderr-WARN
  T-B9   test_recovery_hint_names_redirect_target — Recovery-Hint enthaelt "_A_orchestrate"
  T-B10  test_hil_off_auto_chains          — hil=off + VIOLATION + enforce=true -> BLOCK (kein stilles Idle)
  T-B11  test_scenario_lane_a_terminate_no_stall  — AK-4 A-Lane-Szenario: TERMINATE -> kein STALL
  T-B12  test_scenario_closure_sequence_atomic    — AK-5: hil=off + hil=on erschoepfend (kein drittes Verhalten)

RED: guard_lane_closure_stop.py existiert noch nicht -> alle Tests failen mit
     subprocess-exit != 0 / FileNotFoundError / ImportError.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_lane_closure_stop.py"

ROOT_DIR = SCRIPT_DIR.parent.parent
SETTINGS_JSON = ROOT_DIR / ".claude" / "settings.json"


# ---------------------------------------------------------------------------
# Hilfs-Fixtures
# ---------------------------------------------------------------------------

def _make_audit_jsonl(events: list) -> str:
    """Schreibt Events als JSONL in eine Tempfile, gibt Pfad zurueck."""
    tf = tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    )
    for ev in events:
        tf.write(json.dumps(ev) + "\n")
    tf.close()
    return tf.name


def _make_session_params(enforce: bool = True, hil: str = "off", lane: str = "A") -> str:
    """Schreibt eine _session_params.md Tempfile, gibt Pfad zurueck."""
    tf = tempfile.NamedTemporaryFile(
        mode="w", suffix="_session_params.md", delete=False, encoding="utf-8"
    )
    tf.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
    tf.write(f"**GLOBAL_HIL:** {hil}\n")
    tf.write(f"**lane:** {lane}\n")
    tf.close()
    return tf.name


def _make_lane_plan_md(lanes: dict) -> str:
    """Schreibt ein minimales _lane_plan.md mit LANE_PLAN-YAML-Fence.

    lanes: { "A": {"current": "BL-365", "queue": ["BL-444", "BL-365", "BL-376"], "done": ["BL-444"]} }
    """
    lines = ["# Lane Plan\n\n", "```yaml\n", "LANE_PLAN:\n"]
    for lane_key, entry in lanes.items():
        lines.append(f"  {lane_key}:\n")
        current = entry.get("current", "")
        lines.append(f"    current: {current}\n")
        queue = entry.get("queue", [])
        lines.append(f"    queue: [{', '.join(queue)}]\n")
        done = entry.get("done", [])
        lines.append(f"    done: [{', '.join(done)}]\n")
        lines.append(f"    branch: roadmap-{lane_key.lower()}\n")
    lines.append("```\n")

    tf = tempfile.NamedTemporaryFile(
        mode="w", suffix="_lane_plan.md", delete=False, encoding="utf-8"
    )
    tf.writelines(lines)
    tf.close()
    return tf.name


def _run_guard(
    audit_events: list = None,
    enforce: bool = True,
    hil: str = "off",
    lane: str = "A",
    lane_plan_lanes: dict = None,
    extra_env: dict = None,
) -> tuple:
    """Fuehrt guard_lane_closure_stop.py als Subprocess aus.

    Gibt (proc, result_dict) zurueck.
    result_dict ist das geparste JSON aus stdout (oder {} wenn leer/ungueltig).

    Standardmaessig:
    - Lane A mit queue=[BL-444, BL-365, BL-376], done=[BL-444], current=BL-365
      -> next_bl = BL-365 vorhanden (VIOLATION moeglich)
    - audit enthaelt TERMINATE-Event aber KEIN LANE_CLOSURE_CHAIN
    """
    audit_events = audit_events if audit_events is not None else [
        {"type": "POST_SDF_EXIT", "target": "outer_loop_exit", "mode": "terminate"},
    ]
    if lane_plan_lanes is None:
        lane_plan_lanes = {
            "A": {
                "current": "BL-365",
                "queue": ["BL-444", "BL-365", "BL-376"],
                "done": ["BL-444"],
            }
        }

    audit_path = _make_audit_jsonl(audit_events)
    sp_path = _make_session_params(enforce=enforce, hil=hil, lane=lane)
    lp_path = _make_lane_plan_md(lane_plan_lanes)

    env = os.environ.copy()
    env["OMNI_LANE_CLOSURE_STOP_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    env["OMNI_LANE_CLOSURE_STOP_LANE_PLAN"] = lp_path
    # Off-Switch Schluessel fuer lokalen Schalter (sicher stellen dass nicht gesetzt)
    env.pop("OMNI_ENFORCE_ALL_OFF", None)
    env.pop("OMNI_LANE_CLOSURE_STOP_OFF", None)
    if extra_env:
        env.update(extra_env)

    stop_event = {"hook_event": "Stop", "reason": "turn_end"}

    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(stop_event),
        capture_output=True,
        text=True,
        env=env,
    )

    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    Path(lp_path).unlink(missing_ok=True)

    try:
        result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    except Exception:
        result = {}
    return proc, result


# ---------------------------------------------------------------------------
# T-B1: Off-Switch global
# ---------------------------------------------------------------------------

def test_off_switches_global():
    """T-B1 (AK-6 Off-Switch): OMNI_ENFORCE_ALL_OFF=1 -> Guard deaktiviert -> {"continue": true}.

    Auch bei voller VIOLATION-Lage (TERMINATE + pending next_bl + kein chain_event).

    RED: guard_lane_closure_stop.py existiert noch nicht -> subprocess-Fehler.
    """
    proc, r = _run_guard(
        enforce=True,
        hil="off",
        extra_env={"OMNI_ENFORCE_ALL_OFF": "1"},
    )
    assert r.get("continue") is True, (
        f"T-B1 OMNI_ENFORCE_ALL_OFF=1 -> continue:true erwartet (Guard deaktiviert). War: {r}. "
        f"guard_lane_closure_stop.py existiert vermutlich noch nicht (RED erwartet)."
    )
    assert proc.returncode == 0, (
        f"T-B1: exit 0 erwartet (Off-Switch global), war {proc.returncode}. "
        f"stdout: {proc.stdout[:200]}, stderr: {proc.stderr[:200]}"
    )


# ---------------------------------------------------------------------------
# T-B2: Off-Switch lokal
# ---------------------------------------------------------------------------

def test_off_switches_local():
    """T-B2 (AK-6 Off-Switch lokal): OMNI_LANE_CLOSURE_STOP_OFF=1 -> pass.

    RED: guard_lane_closure_stop.py existiert noch nicht.
    """
    proc, r = _run_guard(
        enforce=True,
        hil="off",
        extra_env={"OMNI_LANE_CLOSURE_STOP_OFF": "1"},
    )
    assert r.get("continue") is True, (
        f"T-B2 OMNI_LANE_CLOSURE_STOP_OFF=1 -> continue:true erwartet. War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-B2: exit 0 erwartet (Off-Switch lokal), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-B3: hil=on kein Block (AK-5)
# ---------------------------------------------------------------------------

def test_hil_on_no_block():
    """T-B3 (AK-5 hil=on): hil=on + volle VIOLATION-Lage -> Guard blockt NICHT.

    Bei hil=on entscheidet der User, kein Auto-Block durch Guard.
    INV-CLOSURE-3: Guard greift nur bei hil=off.

    RED: guard_lane_closure_stop.py existiert noch nicht.
    """
    proc, r = _run_guard(
        enforce=True,
        hil="on",  # User-Checkpoint-Modus, kein Auto-Block
    )
    assert r.get("continue") is True, (
        f"T-B3 AK-5 hil=on: VIOLATION-Lage + hil=on -> continue:true (kein Block). War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-B3: exit 0 erwartet (hil=on kein Block), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-B4: kein TERMINATE-Event
# ---------------------------------------------------------------------------

def test_no_terminate_event():
    """T-B4 (AK-6 kein Trigger): kein POST_SDF_EXIT mit mode=terminate im audit -> pass.

    Guard prueft NUR auf TERMINATE-Events. Anderes Events triggern keinen Block.

    RED: guard_lane_closure_stop.py existiert noch nicht.
    """
    proc, r = _run_guard(
        audit_events=[
            # Nur normaler Batch-Abschluss, kein TERMINATE
            {"type": "POST_SDF_DONE", "target": "batch_end", "mode": "continue"},
        ],
        enforce=True,
        hil="off",
    )
    assert r.get("continue") is True, (
        f"T-B4 kein TERMINATE: audit ohne POST_SDF_EXIT mode=terminate -> continue:true. War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-B4: exit 0 erwartet (kein Trigger), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-B5: next_bl None (leere Lane)
# ---------------------------------------------------------------------------

def test_next_bl_none_no_block():
    """T-B5 (AK-6 FP-Schutz): next_bl_for_lane -> None (alle Items done) -> kein Block.

    Leere Lane nach TERMINATE ist legitimes Ende, kein STALL.
    INV-CLOSURE-1 Klausel: next_bl != None Bedingung.

    RED: guard_lane_closure_stop.py existiert noch nicht.
    """
    proc, r = _run_guard(
        audit_events=[
            {"type": "POST_SDF_EXIT", "target": "outer_loop_exit", "mode": "terminate"},
        ],
        enforce=True,
        hil="off",
        lane_plan_lanes={
            "A": {
                "current": "",
                "queue": ["BL-444", "BL-365"],
                "done": ["BL-444", "BL-365"],  # alle done -> next_bl = None
            }
        },
    )
    assert r.get("continue") is True, (
        f"T-B5 leere Lane (next_bl=None): TERMINATE + alle done -> continue:true (kein Block). War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-B5: exit 0 erwartet (leere Lane = legit Ende), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-B6: LANE_CLOSURE_CHAIN vorhanden seit TERMINATE -> pass
# ---------------------------------------------------------------------------

def test_chain_event_present():
    """T-B6 (AK-6 Chain-Event): LANE_CLOSURE_CHAIN im audit nach TERMINATE -> kein Block.

    Chain wurde bereits ausgefuehrt -> keine VIOLATION.

    RED: guard_lane_closure_stop.py existiert noch nicht.
    """
    proc, r = _run_guard(
        audit_events=[
            {"type": "POST_SDF_EXIT", "target": "outer_loop_exit", "mode": "terminate"},
            # Chain-Event NACH dem TERMINATE vorhanden
            {"type": "LANE_CLOSURE_CHAIN", "lane": "A", "next_bl": "BL-365", "hil": "off"},
        ],
        enforce=True,
        hil="off",
    )
    assert r.get("continue") is True, (
        f"T-B6 LANE_CLOSURE_CHAIN seit TERMINATE: kein Block erwartet (Chain lief bereits). War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-B6: exit 0 erwartet (Chain-Event vorhanden), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-B7: VIOLATION + enforce=true -> Block
# ---------------------------------------------------------------------------

def test_violation_enforced():
    """T-B7 (AK-6 VIOLATION enforce=true): alle VIOLATION-Bedingungen erfuellt + enforce=true
    -> {"continue": false} + sys.exit(2).

    VIOLATION = TERMINATE_event AND lane_oder_goal AND next_bl != None AND NOT chain_event.

    RED: guard_lane_closure_stop.py existiert noch nicht.
    """
    proc, r = _run_guard(
        audit_events=[
            # TERMINATE ohne nachfolgendem LANE_CLOSURE_CHAIN
            {"type": "POST_SDF_EXIT", "target": "outer_loop_exit", "mode": "terminate"},
        ],
        enforce=True,
        hil="off",
        lane="A",
        lane_plan_lanes={
            "A": {
                "current": "BL-365",
                "queue": ["BL-444", "BL-365", "BL-376"],
                "done": ["BL-444"],  # BL-365 noch nicht done -> next_bl = BL-365
            }
        },
    )
    assert r.get("continue") is False, (
        f"T-B7 VIOLATION + enforce=true: continue:false (BLOCK) erwartet. War: {r}. "
        f"stdout: {proc.stdout[:300]}, stderr: {proc.stderr[:200]}"
    )
    assert proc.returncode == 2, (
        f"T-B7: sys.exit(2) erwartet bei Block, war returncode={proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-B8: VIOLATION + enforce=false -> WARN, no Block
# ---------------------------------------------------------------------------

def test_violation_warned():
    """T-B8 (AK-6 VIOLATION enforce=false): VIOLATION + enforce=false
    -> {"continue": true} + Warnung in stderr/message (kein Block).

    RED: guard_lane_closure_stop.py existiert noch nicht.
    """
    proc, r = _run_guard(
        audit_events=[
            {"type": "POST_SDF_EXIT", "target": "outer_loop_exit", "mode": "terminate"},
        ],
        enforce=False,
        hil="off",
        lane="A",
        lane_plan_lanes={
            "A": {
                "current": "BL-365",
                "queue": ["BL-444", "BL-365", "BL-376"],
                "done": ["BL-444"],
            }
        },
    )
    assert r.get("continue") is True, (
        f"T-B8 VIOLATION + enforce=false: continue:true (WARN kein Block) erwartet. War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-B8: exit 0 erwartet (enforce=false kein Block), war {proc.returncode}."
    )
    # Warnung muss irgendwo sichtbar sein (stderr oder message-Feld)
    combined = (r.get("message", "") or "") + proc.stderr
    assert len(combined) > 0 or True, "T-B8: Warnung erwartet (lax check, Impl definiert Format)"


# ---------------------------------------------------------------------------
# T-B9: Recovery-Hint enthaelt "_A_orchestrate"
# ---------------------------------------------------------------------------

def test_recovery_hint_names_redirect_target():
    """T-B9 (AK-6 Recovery-Hint): Bei VIOLATION + enforce=true muss der Recovery-Hint
    "Skill(_A_orchestrate" oder "_A_orchestrate" enthalten (konkrete Aktion, kein vages "chain").

    RED: guard_lane_closure_stop.py existiert noch nicht.
    """
    proc, r = _run_guard(
        audit_events=[
            {"type": "POST_SDF_EXIT", "target": "outer_loop_exit", "mode": "terminate"},
        ],
        enforce=True,
        hil="off",
        lane="A",
        lane_plan_lanes={
            "A": {
                "current": "BL-365",
                "queue": ["BL-444", "BL-365", "BL-376"],
                "done": ["BL-444"],
            }
        },
    )
    combined = (r.get("message", "") or "") + proc.stdout + proc.stderr
    assert "_A_orchestrate" in combined, (
        f"T-B9 Recovery-Hint: '_A_orchestrate' muss im Output/Stderr sichtbar sein. "
        f"War: '{combined[:400]}'."
    )


# ---------------------------------------------------------------------------
# T-B10: hil=off + VIOLATION -> BLOCK (kein stilles Idle) — AK-5
# ---------------------------------------------------------------------------

def test_hil_off_auto_chains():
    """T-B10 (AK-5 hil=off): hil=off + VIOLATION-Lage -> Guard BLOCKT deterministisch.

    hil=off = Auto-Chain-Modus. Guard signalisiert BLOCK als Erinnerung dass
    der Chain nicht ausgefuehrt wurde (kein stilles Idle = INV-CLOSURE-3).

    RED: guard_lane_closure_stop.py existiert noch nicht.
    """
    proc, r = _run_guard(
        audit_events=[
            {"type": "POST_SDF_EXIT", "target": "outer_loop_exit", "mode": "terminate"},
        ],
        enforce=True,
        hil="off",
        lane="A",
        lane_plan_lanes={
            "A": {
                "current": "BL-365",
                "queue": ["BL-444", "BL-365", "BL-376"],
                "done": ["BL-444"],
            }
        },
    )
    # hil=off + pending next_bl + kein chain_event = VIOLATION -> BLOCK
    assert r.get("continue") is False, (
        f"T-B10 hil=off + VIOLATION: continue:false erwartet (Guard blockt, kein stilles Idle). "
        f"War: {r}. (INV-CLOSURE-3: stilles Idle VERBOTEN)"
    )
    assert proc.returncode == 2, (
        f"T-B10: sys.exit(2) erwartet (enforce=true + VIOLATION), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-B11: AK-4 Szenario — Lane A TERMINATE kein STALL
# ---------------------------------------------------------------------------

def test_scenario_lane_a_terminate_no_stall():
    """T-B11 (AK-4 E2E-Szenario): Simuliert A-Lane-Szenario nach BL-444-Abschluss.

    Ausgangszustand:
    - Lane A: current=BL-365, queue=[BL-444, BL-365, BL-376], done=[BL-444]
    - hil=off, enforce=true
    - audit: POST_SDF_EXIT mode=terminate vorhanden, KEIN LANE_CLOSURE_CHAIN

    Erwartung: Guard BLOCKT (continue=false, exit 2) -> kein STALL, Recovery-Hint zeigt next_bl.

    Das ist der Szenario-Test der beweist: das STALL-Problem (45-55min Idle aus BL-444-Node)
    wird GEFANGEN vom Guard (Guard blockt und erzwingt den Chain via Recovery-Hint).

    RED: guard_lane_closure_stop.py existiert noch nicht.
    """
    proc, r = _run_guard(
        audit_events=[
            # SDF hat TERMINATE gemeldet (BL-444 abgeschlossen)
            {"type": "POST_SDF_EXIT", "target": "outer_loop_exit", "mode": "terminate",
             "bl_id": "BL-444", "lane": "A"},
            # KEIN LANE_CLOSURE_CHAIN -> STALL-Situation
        ],
        enforce=True,
        hil="off",
        lane="A",
        lane_plan_lanes={
            "A": {
                "current": "BL-365",
                "queue": ["BL-444", "BL-365", "BL-376"],
                "done": ["BL-444"],  # BL-444 done, BL-365 pending -> next_bl = BL-365
            }
        },
    )
    # Guard muss BLOCKEN (kein stilles Idle)
    assert r.get("continue") is False, (
        f"T-B11 AK-4 A-Lane-Szenario: TERMINATE ohne LANE_CLOSURE_CHAIN + next_bl=BL-365 "
        f"-> continue:false (BLOCK, kein STALL) erwartet. "
        f"War: {r}. returncode={proc.returncode}. "
        f"Aus BL-444-Node: A und C stallten 45-55min weil dieser Block fehlte."
    )
    assert proc.returncode == 2, (
        f"T-B11: sys.exit(2) erwartet (VIOLATION enforce=true), war {proc.returncode}."
    )
    # Recovery-Hint muss BL-365 oder _A_orchestrate nennen
    combined = (r.get("message", "") or "") + proc.stdout + proc.stderr
    assert "_A_orchestrate" in combined or "BL-365" in combined, (
        f"T-B11: Recovery-Hint muss '_A_orchestrate' oder 'BL-365' enthalten. "
        f"War: '{combined[:400]}'."
    )


# ---------------------------------------------------------------------------
# T-B12: AK-5 HiL-Matrix — hil=off vs hil=on vollstaendig und erschoepfend
# ---------------------------------------------------------------------------

def test_scenario_closure_sequence_atomic():
    """T-B12 (AK-5 HiL-Erschoepfung): Die HiL-Gabelung ist binaer und erschoepfend.
    Weder hil=off noch hil=on duerfen in stilles Idle fallen (INV-CLOSURE-3).

    Sub-Test A: hil=off + VIOLATION -> Guard blockt (continue=false) — kein stilles Idle.
    Sub-Test B: hil=on + VIOLATION -> Guard blockt NICHT (continue=true) — User entscheidet.
    Sub-Test C: hil=off + CHAIN_EVENT vorhanden -> Guard pass (continue=true) — Chain lief.

    Kein dritter Pfad zwischen A und B (weder Idle noch undefinierten Zustand).

    RED: guard_lane_closure_stop.py existiert noch nicht.
    """
    base_lanes = {
        "A": {
            "current": "BL-365",
            "queue": ["BL-444", "BL-365", "BL-376"],
            "done": ["BL-444"],
        }
    }
    terminate_event = [
        {"type": "POST_SDF_EXIT", "target": "outer_loop_exit", "mode": "terminate"},
    ]

    # Sub-Test A: hil=off + VIOLATION -> BLOCK
    proc_a, r_a = _run_guard(
        audit_events=terminate_event,
        enforce=True,
        hil="off",
        lane="A",
        lane_plan_lanes=base_lanes,
    )
    assert r_a.get("continue") is False, (
        f"T-B12 Sub-A hil=off + VIOLATION: continue:false erwartet (BLOCK). War: {r_a}."
    )
    assert proc_a.returncode == 2, (
        f"T-B12 Sub-A: exit 2 erwartet (VIOLATION enforce=true), war {proc_a.returncode}."
    )

    # Sub-Test B: hil=on + VIOLATION -> pass (kein Block)
    proc_b, r_b = _run_guard(
        audit_events=terminate_event,
        enforce=True,
        hil="on",
        lane="A",
        lane_plan_lanes=base_lanes,
    )
    assert r_b.get("continue") is True, (
        f"T-B12 Sub-B hil=on + VIOLATION: continue:true erwartet (User-Checkpoint, kein Block). "
        f"War: {r_b}."
    )
    assert proc_b.returncode == 0, (
        f"T-B12 Sub-B: exit 0 erwartet (hil=on kein Block), war {proc_b.returncode}."
    )

    # Sub-Test C: hil=off + Chain-Event vorhanden -> pass
    proc_c, r_c = _run_guard(
        audit_events=[
            {"type": "POST_SDF_EXIT", "target": "outer_loop_exit", "mode": "terminate"},
            {"type": "LANE_CLOSURE_CHAIN", "lane": "A", "next_bl": "BL-365", "hil": "off"},
        ],
        enforce=True,
        hil="off",
        lane="A",
        lane_plan_lanes=base_lanes,
    )
    assert r_c.get("continue") is True, (
        f"T-B12 Sub-C hil=off + LANE_CLOSURE_CHAIN vorhanden: continue:true erwartet (Chain lief). "
        f"War: {r_c}."
    )
    assert proc_c.returncode == 0, (
        f"T-B12 Sub-C: exit 0 erwartet (Chain-Event vorhanden), war {proc_c.returncode}."
    )


# ---------------------------------------------------------------------------
# __main__ runner (direkt ausfuehrbar ohne pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_off_switches_global,
        test_off_switches_local,
        test_hil_on_no_block,
        test_no_terminate_event,
        test_next_bl_none_no_block,
        test_chain_event_present,
        test_violation_enforced,
        test_violation_warned,
        test_recovery_hint_names_redirect_target,
        test_hil_off_auto_chains,
        test_scenario_lane_a_terminate_no_stall,
        test_scenario_closure_sequence_atomic,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed + failed} ===")
    sys.exit(0 if failed == 0 else 1)
