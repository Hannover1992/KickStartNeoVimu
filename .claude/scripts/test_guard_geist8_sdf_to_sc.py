"""
pytest tests fuer guard_geist8_sdf_to_sc.py (Geist G#8 SDF→SC M4-M7).

Tests fuer:
  - M4 mit zu wenig Loads (3 statt 4) → BLOCK
  - M4 mit genau 4 Loads → PASS
  - M5 mit 5 Loads → BLOCK (Minimum 6)
  - M6 mit 5 Loads → BLOCK (SC-Teil Minimum 6)
  - M7 mit 6 Loads → BLOCK (Minimum 7)
  - Pragmatik-Reason / Passthrough fuer Nicht-SC-Skills → PASS
  - Reset bei neuem _SC_orchestrate-Load
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_geist8_sdf_to_sc.py"


def _run_guard(hook_event: str, skill: str, args: str = "",
               state_file: Path = None,
               enforce: bool = True) -> dict:
    """Ruft guard_geist8_sdf_to_sc.py mit simuliertem Hook-Input auf."""
    tool_input = {"skill": skill, "args": args}
    hook_data = {
        "hook_event_name": hook_event,
        "tool_name": "Skill",
        "tool_input": tool_input,
    }
    env = os.environ.copy()
    env["OMNI_ENFORCE_GEIST8"] = "1" if enforce else "0"
    if state_file is not None:
        env["OMNI_GEIST8_STATE_FILE"] = str(state_file)
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    out = proc.stdout.strip()
    return json.loads(out) if out else {"continue": True}


def _simulate_sc_run(state_file: Path, modus: str, sc_steps: list,
                     enforce: bool = True):
    """Hilfs-Fixture: startet SC-Orchestrate + spielt sc_steps ab.
    Letzte Aktion (naechstes _SC_orchestrate oder Final-Check) wird vom
    Aufrufer ausgeloest.
    """
    # Start
    _run_guard("PostToolUse", "_SC_orchestrate",
               args=f"--modus={modus} --batch=batch_v1",
               state_file=state_file, enforce=enforce)
    # Skill-Steps abspielen
    for step in sc_steps:
        _run_guard("PostToolUse", step, state_file=state_file,
                   enforce=enforce)


def _make_state_file():
    fd, path = tempfile.mkstemp(suffix=".json", prefix="geist8_state_")
    os.close(fd)
    p = Path(path)
    p.unlink(missing_ok=True)  # leeren Start
    return p


# ───── TESTS ─────


def test_m4_too_few_loads_blocks_on_next_orchestrate():
    """M4 mit nur 3 Loads (teamSetup + observe + modelMaintain) — beim
    naechsten _SC_orchestrate-Load muss G#8 blockieren weil qualityGate fehlt."""
    state_file = _make_state_file()
    try:
        _simulate_sc_run(state_file, "M4", [
            "_SC_berater_teamSetup",
            "_SC_observe",
            "_SC_modelMaintain",
            # qualityGate fehlt!
        ])
        # Naechster _SC_orchestrate triggert Min-Load-Check
        result = _run_guard(
            "PostToolUse", "_SC_orchestrate",
            args="--modus=M4 --batch=batch_v2",
            state_file=state_file, enforce=True,
        )
        assert result["continue"] is False, (
            f"Expected BLOCK for M4 with only 3 loads, got: {result}"
        )
        assert "GEIST8" in result.get("message", "")
        assert "M4" in result.get("message", "")
    finally:
        state_file.unlink(missing_ok=True)


def test_m4_exact_minimum_passes():
    """M4 mit genau 4 Loads (teamSetup + observe + modelMaintain +
    qualityGate) — naechster _SC_orchestrate-Load darf NICHT blockieren."""
    state_file = _make_state_file()
    try:
        _simulate_sc_run(state_file, "M4", [
            "_SC_berater_teamSetup",
            "_SC_observe",
            "_SC_modelMaintain",
            "_SC_qualityGate",
        ])
        result = _run_guard(
            "PostToolUse", "_SC_orchestrate",
            args="--modus=M4 --batch=batch_v2",
            state_file=state_file, enforce=True,
        )
        assert result["continue"] is True, (
            f"Expected PASS for M4 with exact min 4 loads, got: {result}"
        )
    finally:
        state_file.unlink(missing_ok=True)


def test_m5_too_few_loads_blocks():
    """M5 erfordert min 6 — bei 5 Loads muss G#8 blocken."""
    state_file = _make_state_file()
    try:
        _simulate_sc_run(state_file, "M5", [
            "_SC_berater_teamSetup",
            "_SC_observe",
            "_SC_modelMaintain",
            "_SC_qualityGate",
            "_SC_hypothese",
            # ergebnis fehlt → nur 5
        ])
        result = _run_guard(
            "PostToolUse", "_SC_orchestrate",
            args="--modus=M5 --batch=batch_v2",
            state_file=state_file, enforce=True,
        )
        assert result["continue"] is False, (
            f"Expected BLOCK for M5 with only 5 loads, got: {result}"
        )
        assert "M5" in result.get("message", "")
        assert "GEIST8" in result.get("message", "")
    finally:
        state_file.unlink(missing_ok=True)


def test_m6_sc_part_too_few_loads_blocks():
    """M6 SC-Teil erfordert min 6 SC-Skill-Loads (I-Teil via geist7)."""
    state_file = _make_state_file()
    try:
        _simulate_sc_run(state_file, "M6", [
            "_SC_berater_teamSetup",
            "_SC_observe",
            "_SC_modelMaintain",
            "_SC_qualityGate",
            "_SC_hypothese",
            # ergebnis fehlt → nur 5 SC-Loads
        ])
        result = _run_guard(
            "PostToolUse", "_SC_orchestrate",
            args="--modus=M6 --batch=batch_v2",
            state_file=state_file, enforce=True,
        )
        assert result["continue"] is False, (
            f"Expected BLOCK for M6 SC-part with only 5 loads, got: {result}"
        )
        assert "M6" in result.get("message", "")
    finally:
        state_file.unlink(missing_ok=True)


def test_m7_too_few_loads_blocks():
    """M7 erfordert min 7 — bei 6 Loads muss G#8 blocken."""
    state_file = _make_state_file()
    try:
        _simulate_sc_run(state_file, "M7", [
            "_SC_berater_teamSetup",
            "_SC_observe",
            "_SC_modelMaintain",
            "_SC_qualityGate",
            "_SC_hypothese",
            "_SC_ergebnis",
            # Pure-Forschung fordert 7. 6 reicht nicht.
        ])
        result = _run_guard(
            "PostToolUse", "_SC_orchestrate",
            args="--modus=M7 --batch=batch_v2",
            state_file=state_file, enforce=True,
        )
        assert result["continue"] is False, (
            f"Expected BLOCK for M7 with only 6 loads, got: {result}"
        )
        assert "M7" in result.get("message", "")
    finally:
        state_file.unlink(missing_ok=True)


def test_m7_seven_loads_passes():
    """M7 mit 7 Loads (zB ergebnis 2x oder modelMaintain 2x) → PASS."""
    state_file = _make_state_file()
    try:
        _simulate_sc_run(state_file, "M7", [
            "_SC_berater_teamSetup",
            "_SC_observe",
            "_SC_modelMaintain",
            "_SC_qualityGate",
            "_SC_hypothese",
            "_SC_ergebnis",
            "_SC_modelMaintain",   # zweiter Loop, gemaess M7 Pure-Forschung
        ])
        result = _run_guard(
            "PostToolUse", "_SC_orchestrate",
            args="--modus=M7 --batch=batch_v2",
            state_file=state_file, enforce=True,
        )
        assert result["continue"] is True, (
            f"Expected PASS for M7 with 7 loads, got: {result}"
        )
    finally:
        state_file.unlink(missing_ok=True)


def test_non_sc_skill_passthrough():
    """Skills die nicht zu SC gehoeren (zB _IDF_orchestrate) sollen
    Counter NICHT veraendern und immer durchgehen."""
    state_file = _make_state_file()
    try:
        # SC-Lauf starten
        _run_guard("PostToolUse", "_SC_orchestrate",
                   args="--modus=M4", state_file=state_file)
        # Fremdes Skill dazwischen — darf nicht blockieren, nicht zaehlen
        result = _run_guard(
            "PostToolUse", "_IDF_orchestrate", args="",
            state_file=state_file, enforce=True,
        )
        assert result["continue"] is True, (
            f"Expected PASS for unrelated skill, got: {result}"
        )
        # State darf nicht inkrementiert worden sein
        with open(state_file, "r", encoding="utf-8") as f:
            state = json.load(f)
        assert state["count"] == 0, (
            f"Counter should not increment for non-SC skill, got: {state}"
        )
    finally:
        state_file.unlink(missing_ok=True)


def test_warn_only_when_enforce_false():
    """Bei enforceProcess=false: WARNING aber continue=true."""
    state_file = _make_state_file()
    try:
        _simulate_sc_run(state_file, "M4", [
            "_SC_berater_teamSetup",
            "_SC_observe",
            # nur 2 statt 4
        ], enforce=False)
        result = _run_guard(
            "PostToolUse", "_SC_orchestrate",
            args="--modus=M4",
            state_file=state_file, enforce=False,
        )
        assert result["continue"] is True, (
            f"Expected PASS (WARN-only) with enforce=false, got: {result}"
        )
        assert "WARNING" in result.get("message", "") or \
               "GEIST8" in result.get("message", ""), (
            f"Expected warning hint, got: {result}"
        )
    finally:
        state_file.unlink(missing_ok=True)
