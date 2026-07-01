"""
pytest tests fuer guard_stab9_manifest_dup.py (Stab S#9, Live-Finding F105).

Tests decken:
  1) 1x DF_BATCH_STATE                                  -> pass
  2) 2x DF_BATCH_STATE OHNE Suffix                      -> BLOCK
  3) 2x DF_BATCH_STATE mit unterschiedlichen Suffixen   -> pass
  4) BERATER_OUTPUTS.foo duplication (kein Singleton)   -> pass
  5) Edit andere Datei (kein Manifest)                  -> passthrough
  6) 2x A_PIPELINE_STATE mit gleichem Suffix            -> BLOCK
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_stab9_manifest_dup.py"


def run_guard(tool_name: str, file_path: str, content: str = "", new_string: str = "", old_string: str = "") -> dict:
    """Ruft guard_stab9_manifest_dup.py mit simuliertem Hook-Input auf.

    OMNI_ENFORCE_STAB9_GUARD=1 erzwingt enforce=true unabhaengig von _session_params.md.
    """
    import os
    tool_input = {"file_path": file_path}
    if tool_name == "Write":
        tool_input["content"] = content
    else:
        tool_input["new_string"] = new_string
        if old_string:
            tool_input["old_string"] = old_string

    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    env = os.environ.copy()
    env["OMNI_ENFORCE_STAB9_GUARD"] = "1"
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(proc.stdout.strip())


def test_single_df_batch_state_passes():
    """Genau 1x ## DF_BATCH_STATE im Manifest -> continue=true."""
    result = run_guard(
        tool_name="Write",
        file_path="/tmp/some/_manifest.md",
        content=(
            "# Manifest\n"
            "\n"
            "## DF_BATCH_STATE\n"
            "modus: M3\n"
            "modus_set_by: _SDF_berater_modusEntscheidung\n"
        ),
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_blocks_two_df_batch_state_without_suffix():
    """LIVE-Finding F105: 2x ## DF_BATCH_STATE ohne Suffix -> BLOCK."""
    result = run_guard(
        tool_name="Write",
        file_path="/tmp/some/_manifest.md",
        content=(
            "# Manifest\n"
            "\n"
            "## DF_BATCH_STATE\n"
            "modus: M3\n"
            "\n"
            "## OTHER_SECTION\n"
            "foo: bar\n"
            "\n"
            "## DF_BATCH_STATE\n"
            "modus: M2\n"
        ),
    )
    assert result["continue"] is False, (
        f"REGRESSION! 2x DF_BATCH_STATE ohne Suffix sollte blockiert sein "
        f"(F105 Live-Finding 2026-05-09). Got: {result}"
    )
    msg = result.get("message", "")
    assert "Duplicate manifest section" in msg, f"Expected duplicate message, got: {msg}"
    assert "DF_BATCH_STATE" in msg, f"Expected DF_BATCH_STATE in message, got: {msg}"


def test_allows_two_df_batch_state_with_different_round_suffix():
    """2x ## DF_BATCH_STATE mit unterschiedlichen Round-Suffixen -> pass."""
    result = run_guard(
        tool_name="Write",
        file_path="/tmp/some/_manifest.md",
        content=(
            "# Manifest\n"
            "\n"
            "## DF_BATCH_STATE (Round 11)\n"
            "modus: M3\n"
            "\n"
            "## DF_BATCH_STATE (Round 12)\n"
            "modus: M2\n"
        ),
    )
    assert result["continue"] is True, (
        f"Expected pass (unterschiedliche Round-Suffixe = legitime Koexistenz). "
        f"Got: {result}"
    )


def test_allows_berater_outputs_duplication():
    """## BERATER_OUTPUTS.foo ist KEIN Singleton — mehrfach erlaubt."""
    result = run_guard(
        tool_name="Write",
        file_path="/tmp/some/_manifest.md",
        content=(
            "# Manifest\n"
            "\n"
            "## BERATER_OUTPUTS\n"
            "set_by: _SDF_berater_x\n"
            "\n"
            "## BERATER_OUTPUTS\n"
            "set_by: _SDF_berater_y\n"
            "\n"
            "## DF_BATCH_STATE\n"
            "modus: M3\n"
        ),
    )
    assert result["continue"] is True, (
        f"Expected pass — BERATER_OUTPUTS ist kein Singleton. Got: {result}"
    )


def test_passes_non_manifest_file():
    """Edit auf andere Datei (kein _manifest.md / _factory_manifest.md) -> passthrough."""
    result = run_guard(
        tool_name="Edit",
        file_path="/tmp/some/_berater_outputs.md",
        new_string=(
            "## DF_BATCH_STATE\n"
            "modus: M3\n"
            "## DF_BATCH_STATE\n"
            "modus: M2\n"
        ),
    )
    assert result["continue"] is True, (
        f"Expected passthrough for non-manifest file, got: {result}"
    )


def test_blocks_two_a_pipeline_state_same_suffix():
    """2x ## A_PIPELINE_STATE mit gleichem Suffix -> BLOCK."""
    result = run_guard(
        tool_name="Write",
        file_path="/tmp/some/_manifest.md",
        content=(
            "# Manifest\n"
            "\n"
            "## A_PIPELINE_STATE (Round 11)\n"
            "phase: COMPLETED\n"
            "\n"
            "## A_PIPELINE_STATE (Round 11)\n"
            "phase: PENDING\n"
        ),
    )
    assert result["continue"] is False, (
        f"REGRESSION! 2x A_PIPELINE_STATE (Round 11) sollte blockiert sein. Got: {result}"
    )
    msg = result.get("message", "")
    assert "A_PIPELINE_STATE" in msg, f"Expected A_PIPELINE_STATE in message, got: {msg}"
