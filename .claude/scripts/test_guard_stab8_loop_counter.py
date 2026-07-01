"""
pytest tests fuer guard_stab8_loop_counter.py (BL-075 T2/T4, S#8).

Test-Setup: Schreibt einen Disk-Manifest mit bekannten Counter-Werten,
ruft den Hook mit simuliertem Edit auf und prueft continue-Output.

Style-Reference: test_guard_modus_writer.py.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_stab8_loop_counter.py"


def run_guard(
    tool_name: str,
    file_path: str,
    content: str = "",
    new_string: str = "",
    extra_env: dict | None = None,
) -> dict:
    """Ruft guard_stab8_loop_counter.py mit simuliertem Hook-Input auf.

    OMNI_ENFORCE_LOOP_COUNTER_GUARD=1 erzwingt enforce=true unabhaengig von
    _session_params.md (siehe test_guard_modus_writer.py-Pattern).
    """
    tool_input = {"file_path": file_path}
    if tool_name == "Write":
        tool_input["content"] = content
    else:
        tool_input["new_string"] = new_string

    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    env = os.environ.copy()
    env["OMNI_ENFORCE_LOOP_COUNTER_GUARD"] = "1"
    # OMNI_COUNTER_RESET_OK darf NICHT durchsickern aus parent-env
    env.pop("OMNI_COUNTER_RESET_OK", None)
    if extra_env:
        env.update(extra_env)
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(proc.stdout.strip())


def _write_manifest(tmp_path: Path, body: str) -> Path:
    """Erzeugt eine tempo _manifest.md im tmp_path mit body als Inhalt."""
    p = tmp_path / "_manifest.md"
    p.write_text(body, encoding="utf-8")
    return p


# ───── Tests ─────


def test_increment_passes(tmp_path):
    """bdf_scan_iterations: 5 → 6 (legitimer Inkrement) → continue=true."""
    manifest = _write_manifest(
        tmp_path,
        "BDF_PIPELINE_STATE:\n  bdf_scan_iterations: 5\n  reifung_cycles: 1\n  bdf_bl_handoff_depth: 0\n",
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(manifest),
        new_string="bdf_scan_iterations: 6\n",
    )
    assert result["continue"] is True, f"Expected pass for increment, got: {result}"


def test_reset_without_item_done_blocks(tmp_path):
    """bdf_scan_iterations: 5 → 0 ohne Item-Done-Marker → continue=false."""
    manifest = _write_manifest(
        tmp_path,
        "BDF_PIPELINE_STATE:\n  bdf_scan_iterations: 5\n",
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(manifest),
        new_string="bdf_scan_iterations: 0\n",
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "STAB8_LOOP_COUNTER" in result.get("message", ""), \
        f"Expected guard message, got: {result}"


def test_reset_with_item_done_passes(tmp_path):
    """bdf_scan_iterations: 5 → 0 MIT items_done append → continue=true."""
    manifest = _write_manifest(
        tmp_path,
        "BDF_PIPELINE_STATE:\n  bdf_scan_iterations: 5\n  reifung_cycles: 2\n",
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(manifest),
        new_string=(
            "# Anti-Zirkel Zaehler Reset nach erfolgreichem Item\n"
            "BDF_PIPELINE_STATE:\n"
            "  bdf_scan_iterations: 0\n"
            "  reifung_cycles: 0\n"
            "  items_done: [BL-209]\n"
        ),
    )
    assert result["continue"] is True, f"Expected pass with item-done, got: {result}"


def test_over_max_blocks(tmp_path):
    """bdf_scan_iterations: 999 (over-max=20) → continue=false."""
    manifest = _write_manifest(
        tmp_path,
        "BDF_PIPELINE_STATE:\n  bdf_scan_iterations: 19\n",
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(manifest),
        new_string="bdf_scan_iterations: 999\n",
    )
    assert result["continue"] is False, f"Expected block on over-max, got: {result}"
    assert "STAB8_LOOP_COUNTER" in result.get("message", "")
    assert "999" in result.get("message", "") or "max" in result.get("message", "").lower()


def test_override_env_passes(tmp_path):
    """OMNI_COUNTER_RESET_OK=1 → continue=true auch bei illegitimem Reset."""
    manifest = _write_manifest(
        tmp_path,
        "BDF_PIPELINE_STATE:\n  bdf_scan_iterations: 5\n",
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(manifest),
        new_string="bdf_scan_iterations: 0\n",
        extra_env={"OMNI_COUNTER_RESET_OK": "1"},
    )
    assert result["continue"] is True, f"Expected pass with override, got: {result}"


def test_unrelated_file_passes(tmp_path):
    """Edit auf andere Datei (_berater_outputs.md) → continue=true."""
    other = tmp_path / "_berater_outputs.md"
    other.write_text("anything here", encoding="utf-8")
    result = run_guard(
        tool_name="Edit",
        file_path=str(other),
        new_string="bdf_scan_iterations: 0\nbdf_bl_handoff_depth: 999\n",
    )
    assert result["continue"] is True, \
        f"Expected pass for non-manifest file, got: {result}"


def test_handoff_depth_decrement_passes(tmp_path):
    """bdf_bl_handoff_depth: 2 → 1 (Dekrement-Pfad) → continue=true."""
    manifest = _write_manifest(
        tmp_path,
        "BDF_PIPELINE_STATE:\n  bdf_bl_handoff_depth: 2\n",
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(manifest),
        new_string="bdf_bl_handoff_depth: 1\n",
    )
    assert result["continue"] is True, f"Expected pass for decrement, got: {result}"


def test_handoff_depth_jump_to_zero_blocks(tmp_path):
    """bdf_bl_handoff_depth: 2 → 0 (kein Dekrement) → continue=false."""
    manifest = _write_manifest(
        tmp_path,
        "BDF_PIPELINE_STATE:\n  bdf_bl_handoff_depth: 2\n",
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(manifest),
        new_string="bdf_bl_handoff_depth: 0\n",
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "STAB8_LOOP_COUNTER" in result.get("message", "")
