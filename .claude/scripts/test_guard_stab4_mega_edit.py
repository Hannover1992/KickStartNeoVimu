"""
pytest tests fuer guard_stab4_mega_edit.py (S#4 Mega-Edit Detector,
BL-RCA-486-Round11 Layer L5).

Test-Pattern (analog test_guard_geist7_sdf_to_i.py):
  - Subprocess-Aufruf des Guards mit synthetischem stdin
  - Env-Override OMNI_ENFORCE_STAB4=1 erzwingt enforce=true
  - Env-Override OMNI_STAB4_STATE_PATH fuer Isolation (tmpdir)
  - Jeder Test seedet ggf. state, ruft Guard, prueft JSON.

8 Test-Cases:
  T1: 250 LOC .ts ohne Berater-Spawn  → continue:false (Block)
  T2: 250 LOC .ts MIT Berater-Spawn   → continue:true  (pass, post_berater)
  T3: 100 LOC .ts                     → continue:true  (unter Threshold)
  T4: 600 LOC .md ohne Berater        → continue:false (Block, markdown>500)
  T5: OMNI_MEGA_EDIT_OVERRIDE=1       → continue:true  (env_override, warn)
  T6: Inline pragmatik_reason         → continue:true  (pragmatik, warn)
  T7: 350 LOC .spec.ts ohne Berater   → continue:false (test>300)
  T8: 200 LOC .ts (genau Threshold)   → continue:true  (Threshold = strict-greater)
"""

import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_stab4_mega_edit.py"


# ──────────────────────────── Helpers ────────────────────────────


def _seed_state(state_path, calls):
    """Schreibe state-JSON mit gegebenen calls als Vorgeschichte."""
    state = {"calls": calls}
    Path(state_path).parent.mkdir(parents=True, exist_ok=True)
    with open(state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False)


def _make_call(tool, subject):
    return {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "tool": tool,
        "subject": subject,
    }


def run_guard(tool_name, tool_input, prior_calls=None,
              env_override=False, session_enforce="true"):
    """Ruft guard_stab4_mega_edit.py mit isoliertem Env auf.

    Args:
        tool_name: "Edit" oder "Write"
        tool_input: dict mit file_path + new_string/content
        prior_calls: optionale Liste von Vorgaenger-Tool-Calls fuer state
        env_override: setze OMNI_MEGA_EDIT_OVERRIDE=1
        session_enforce: "true" oder "false" (im _session_params.md)

    Returns: dict (parsed JSON von Guard-Output).
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        state_file = tmp_path / "stab4_state.json"
        session_file = tmp_path / "_session_params.md"

        if prior_calls:
            _seed_state(state_file, prior_calls)

        session_file.write_text(
            f"# Session Params\n**enforceProcess:** {session_enforce}\n",
            encoding="utf-8"
        )

        env = os.environ.copy()
        env["OMNI_ENFORCE_STAB4"] = "1" if session_enforce == "true" else "0"
        env["OMNI_STAB4_STATE_PATH"] = str(state_file)
        env["OMNI_STAB4_SESSION_PARAMS"] = str(session_file)
        if env_override:
            env["OMNI_MEGA_EDIT_OVERRIDE"] = "1"
        else:
            env.pop("OMNI_MEGA_EDIT_OVERRIDE", None)

        hook_data = {"tool_name": tool_name, "tool_input": tool_input}
        proc = subprocess.run(
            [sys.executable, str(GUARD_SCRIPT)],
            input=json.dumps(hook_data),
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        out = proc.stdout.strip()
        if not out:
            raise RuntimeError(f"empty stdout, stderr={proc.stderr!r}")
        last_line = out.splitlines()[-1]
        return json.loads(last_line)


# ──────────────────────────── Tests ────────────────────────────


def test_t1_250_loc_code_no_berater_blocks():
    """T1: 250 LOC .ts ohne Berater-Spawn in History → Block."""
    big_code = "\n".join(f"const v{i} = {i};" for i in range(250))
    result = run_guard(
        tool_name="Write",
        tool_input={"file_path": "/proj/src/component.ts", "content": big_code},
        prior_calls=[
            _make_call("Read", ""),
            _make_call("Read", ""),
            _make_call("Skill", "_I_orchestrate"),  # NICHT Berater!
        ],
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    msg = result.get("message", "")
    assert "STAB4-VIOLATION" in msg or "MEGA_EDIT_WITHOUT_BERATER_SPAWN" in msg, (
        f"Expected violation message, got: {msg}"
    )
    assert "200" in msg or "code" in msg, f"Expected threshold mention, got: {msg}"


def test_t2_250_loc_code_with_berater_passes():
    """T2: 250 LOC .ts MIT Berater-Spawn in letzten 5 Calls → pass."""
    big_code = "\n".join(f"const v{i} = {i};" for i in range(250))
    result = run_guard(
        tool_name="Write",
        tool_input={"file_path": "/proj/src/component.ts", "content": big_code},
        prior_calls=[
            _make_call("Read", ""),
            _make_call("Skill", "_I_blueprintArchitect"),
            _make_call("Skill", "_IDF_berater_specParse"),  # ← Berater-Spawn!
            _make_call("Read", ""),
        ],
    )
    assert result["continue"] is True, f"Expected pass with Berater, got: {result}"


def test_t3_100_loc_code_under_threshold_passes():
    """T3: 100 LOC .ts (unter Threshold 200) → pass ohne Berater-Check."""
    small_code = "\n".join(f"const v{i} = {i};" for i in range(100))
    result = run_guard(
        tool_name="Write",
        tool_input={"file_path": "/proj/src/component.ts", "content": small_code},
        prior_calls=[_make_call("Read", "")],  # kein Berater noetig
    )
    assert result["continue"] is True, f"Expected pass under threshold, got: {result}"


def test_t4_600_loc_markdown_no_berater_blocks():
    """T4: 600 LOC .md ueberschreitet Markdown-Threshold 500 ohne Berater → Block."""
    big_md = "\n".join(f"# Heading {i}" for i in range(600))
    result = run_guard(
        tool_name="Write",
        tool_input={"file_path": "/proj/docs/big.md", "content": big_md},
        prior_calls=[
            _make_call("Read", ""),
            _make_call("Skill", "_BDF_orchestrate"),
        ],
    )
    assert result["continue"] is False, f"Expected block for big .md, got: {result}"
    msg = result.get("message", "")
    assert "500" in msg or "markdown" in msg, f"Expected markdown-threshold, got: {msg}"


def test_t5_env_override_passes_with_warn():
    """T5: OMNI_MEGA_EDIT_OVERRIDE=1 → durchgelassen mit Warn-Message."""
    big_code = "\n".join(f"const v{i} = {i};" for i in range(300))
    result = run_guard(
        tool_name="Edit",
        tool_input={"file_path": "/proj/src/component.ts", "new_string": big_code},
        prior_calls=[],  # absichtlich keine Berater
        env_override=True,
    )
    assert result["continue"] is True, f"Expected pass with env override, got: {result}"
    msg = result.get("message", "")
    assert "STAB4-WARN" in msg or "OMNI_MEGA_EDIT_OVERRIDE" in msg, (
        f"Expected warn message, got: {msg}"
    )


def test_t6_inline_pragmatik_reason_passes_with_warn():
    """T6: Inline pragmatik_reason im content → durchgelassen mit Warn."""
    big_code = (
        "pragmatik_reason: Generierte Datei aus Code-Generator, kein Berater-Spawn moeglich\n"
        + "\n".join(f"const v{i} = {i};" for i in range(250))
    )
    result = run_guard(
        tool_name="Write",
        tool_input={"file_path": "/proj/src/generated.ts", "content": big_code},
        prior_calls=[],  # absichtlich keine Berater
    )
    assert result["continue"] is True, f"Expected pass with pragmatik_reason, got: {result}"
    msg = result.get("message", "")
    assert "pragmatik" in msg.lower(), f"Expected pragmatik-warn, got: {msg}"


def test_t7_350_loc_test_file_blocks():
    """T7: 350 LOC *.spec.ts ueberschreitet Test-Threshold 300 ohne Berater → Block."""
    big_test = "\n".join(f"it('test {i}', () => {{}});" for i in range(350))
    result = run_guard(
        tool_name="Write",
        tool_input={"file_path": "/proj/src/component.spec.ts", "content": big_test},
        prior_calls=[
            _make_call("Read", ""),
            _make_call("Skill", "_I_orchestrate"),  # NICHT Berater
        ],
    )
    assert result["continue"] is False, f"Expected block for big test file, got: {result}"
    msg = result.get("message", "")
    assert "300" in msg or "test" in msg, f"Expected test-threshold, got: {msg}"


def test_t8_threshold_boundary_passes():
    """T8: Genau 200 LOC .ts (Threshold) → pass (strict-greater).

    Threshold = strict-greater (> 200): genau 200 LOC darf durch.
    """
    boundary_code = "\n".join(f"const v{i} = {i};" for i in range(200))
    # Genau 200 Zeilen (kein trailing newline)
    result = run_guard(
        tool_name="Write",
        tool_input={"file_path": "/proj/src/component.ts", "content": boundary_code},
        prior_calls=[],
    )
    assert result["continue"] is True, f"Expected pass at threshold-boundary, got: {result}"
