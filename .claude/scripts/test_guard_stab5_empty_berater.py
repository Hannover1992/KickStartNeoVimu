"""
pytest tests fuer guard_stab5_empty_berater.py (Stab S#5 Phantom-DONE-Detector).

7 Test-Cases gem. S#5 Vertrag:
  1. Vollstaendiger Berater-Output (10+ Zeilen)         -> continue:true
  2. Leerer Output mit exit_code:0 ohne reason          -> continue:false
  3. Leerer Output mit empty_reason                     -> continue:true
  4. Leerer Output mit skip_reason                      -> continue:true
  5. exit_code:2 (FAIL) ohne Content                    -> continue:true
  6. Phantom-Block in BERATER_OUTPUTS_IDF.* Subspace    -> continue:false
  7. Edit auf andere Datei (kein _manifest.md)          -> continue:true

Style-Quelle: test_guard_modus_writer.py.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_stab5_empty_berater.py"


def run_guard(tool_name: str, file_path: str, content: str = "", new_string: str = "") -> dict:
    """Ruft guard_stab5_empty_berater.py mit simuliertem Hook-Input auf.

    OMNI_ENFORCE_STAB5=1 erzwingt enforce=true unabhaengig von _session_params.md.
    """
    tool_input = {"file_path": file_path}
    if tool_name == "Write":
        tool_input["content"] = content
    else:
        tool_input["new_string"] = new_string

    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    env = os.environ.copy()
    env["OMNI_ENFORCE_STAB5"] = "1"
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    # Stdout kann mehrere Lines enthalten — letzte JSON-Zeile nehmen
    out = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else "{}"
    return json.loads(out)


# ───── 1. Vollstaendiger Berater-Output mit substantiellem Content ─────


def test_allows_complete_berater_output():
    """Edit mit vollem Berater-Output (10+ Content-Zeilen) -> continue=true."""
    full_block = (
        "## BERATER_OUTPUTS.modusEntscheidung_round11\n"
        "set_by: _SDF_berater_modusEntscheidung\n"
        "exit_code: 0\n"
        "ts: 2026-05-27T10:00:00\n"
        "schema_version: 1\n"
        "decision: M3\n"
        "begruendung: k_score=0.82, srs=0.55, batch_type=TDD\n"
        "k_score: 0.82\n"
        "srs: 0.55\n"
        "batch_type: TDD\n"
        "ceiling: 5\n"
        "floor: 2\n"
        "next_phase: 2.1\n"
        "patterns_consulted: [PT-CMD-001, PT-CMD-005]\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=full_block,
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"


# ───── 2. Phantom: exit_code:0 + leerer Content + kein empty_reason ─────


def test_blocks_phantom_empty_exit_code_zero():
    """Round 11 F9 Phantom-Pattern: exit_code:0 aber nur Provenance -> BLOCK."""
    phantom_block = (
        "## BERATER_OUTPUTS.modusEntscheidung_round11\n"
        "set_by: _SDF_berater_modusEntscheidung\n"
        "exit_code: 0\n"
        "ts: 2026-05-27T10:00:00\n"
        "schema_version: 1\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=phantom_block,
    )
    assert result["continue"] is False, (
        f"REGRESSION! Phantom-Block (exit_code:0 + leer + kein empty_reason) "
        f"sollte blockiert sein. Got: {result}"
    )
    assert "STAB_S5_EMPTY_BERATER" in result.get("message", ""), (
        f"Expected guard message, got: {result}"
    )


# ───── 3. Legitimer Leer-Output mit empty_reason ─────


def test_allows_empty_with_empty_reason():
    """exit_code:0 + empty_reason gesetzt -> legitimer Skip, pass."""
    legit_skip_block = (
        "## BERATER_OUTPUTS.modelSync_round11\n"
        "set_by: _SDF_berater_modelSync\n"
        "exit_code: 0\n"
        "ts: 2026-05-27T10:05:00\n"
        "empty_reason: twin-mirror patterns, kein neues Model fuer Round 11\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=legit_skip_block,
    )
    assert result["continue"] is True, (
        f"Expected pass (empty_reason ist legitim), got: {result}"
    )


# ───── 4. Legitimer Skip mit skip_reason ─────


def test_allows_empty_with_skip_reason():
    """exit_code:0 + skip_reason -> legitimer Skip, pass."""
    skip_block = (
        "## BERATER_OUTPUTS.patternBrief_round11\n"
        "set_by: _SDF_berater_patternBrief\n"
        "exit_code: 0\n"
        "ts: 2026-05-27T10:10:00\n"
        "skip_reason: SKIP — keine neuen Pattern-Kandidaten im Sub-Batch\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=skip_block,
    )
    assert result["continue"] is True, (
        f"Expected pass (skip_reason ist legitim), got: {result}"
    )


# ───── 5. FAIL ohne Content ist OK (Worker hat gefailt — kein Output zu erwarten) ─────


def test_allows_fail_exit_code_without_content():
    """exit_code:2 (FAIL) ohne Content -> kein Phantom, pass."""
    fail_block = (
        "## BERATER_OUTPUTS.validator_round11\n"
        "set_by: _SDF_berater_validator\n"
        "exit_code: 2\n"
        "ts: 2026-05-27T10:15:00\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=fail_block,
    )
    assert result["continue"] is True, (
        f"Expected pass (Fail-Output braucht keinen Content), got: {result}"
    )


# ───── 6. Phantom in BERATER_OUTPUTS_IDF.* Subspace ─────


def test_blocks_phantom_in_subspace_idf():
    """BERATER_OUTPUTS_IDF.* Subspace darf nicht durchrutschen."""
    phantom_idf_block = (
        "## BERATER_OUTPUTS_IDF.plAggregation_round11\n"
        "set_by: _IDF_berater_plAggregation\n"
        "exit_code: 0\n"
        "ts: 2026-05-27T11:00:00\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=phantom_idf_block,
    )
    assert result["continue"] is False, (
        f"REGRESSION! Phantom in BERATER_OUTPUTS_IDF.* Subspace sollte "
        f"blockiert sein. Got: {result}"
    )
    assert "STAB_S5_EMPTY_BERATER" in result.get("message", "")


# ───── 7. Passthrough fuer andere Dateien ─────


def test_passes_unrelated_file_edits():
    """Edit auf andere Datei (kein _manifest.md) -> passthrough."""
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_berater_outputs.md",
        new_string=(
            "## BERATER_OUTPUTS.foo_round11\n"
            "set_by: _whoever\n"
            "exit_code: 0\n"
        ),
    )
    assert result["continue"] is True, (
        f"Expected pass fuer non-manifest file, got: {result}"
    )
