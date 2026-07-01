"""
pytest Tests fuer guard_stab1_berater_provenance.py (Stab S#1, RCA-486-Round11).

Test-Cases:
  1. Vollstaendiger Block (set_by + exit_code + ts) -> continue=true
  2. Block ohne set_by -> continue=false
  3. Block ohne exit_code -> continue=false
  4. Block ohne ts -> continue=false
  5. Edit auf andere Datei (nicht _manifest.md) -> passthrough
  6. Bestehender BERATER_OUTPUTS-Block ohne Provenance + neuer Block ohne Provenance
     -> nur neuer wird geblockt (alter ignoriert weil im old_string)
  7. enforce=false -> WARN-only (continue=true, message gesetzt)
  8. _factory_manifest.md wird ebenso geprueft
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_stab1_berater_provenance.py"


def run_guard(
    tool_name: str,
    file_path: str,
    content: str = "",
    new_string: str = "",
    old_string: str = "",
    enforce: bool = True,
) -> dict:
    """Ruft Guard-Script mit simuliertem Hook-Input auf."""
    tool_input = {"file_path": file_path}
    if tool_name == "Write":
        tool_input["content"] = content
    else:  # Edit
        tool_input["new_string"] = new_string
        tool_input["old_string"] = old_string

    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    env = os.environ.copy()
    env["OMNI_ENFORCE_STAB1_GUARD"] = "1" if enforce else "0"
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(proc.stdout.strip())


# ---- Test 1: Vollstaendiger Block ----------------------------------------------------

def test_complete_block_passes():
    """Block mit set_by + exit_code + ts -> continue=true."""
    block = (
        "## BERATER_OUTPUTS.modusEntscheidung_round11\n"
        "set_by: _SDF_berater_modusEntscheidung\n"
        "exit_code: 0\n"
        "ts: 2026-05-27T13:45:00\n"
        "modus: M3\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=block,
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"


# ---- Test 2: Block ohne set_by --------------------------------------------------------

def test_block_without_set_by_blocked():
    """Block ohne set_by -> continue=false."""
    block = (
        "## BERATER_OUTPUTS.modusEntscheidung_round11\n"
        "exit_code: 0\n"
        "ts: 2026-05-27\n"
        "modus: M3\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=block,
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "set_by" in result.get("message", ""), f"Expected set_by in msg, got: {result}"
    assert "STAB1_BERATER_PROVENANCE" in result.get("message", "")


# ---- Test 3: Block ohne exit_code -----------------------------------------------------

def test_block_without_exit_code_blocked():
    """Block ohne exit_code -> continue=false."""
    block = (
        "## BERATER_OUTPUTS.patternBrief_round11\n"
        "set_by: _SDF_berater_patternBrief\n"
        "ts: 2026-05-27\n"
        "patterns: []\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=block,
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "exit_code" in result.get("message", "")


# ---- Test 4: Block ohne ts ------------------------------------------------------------

def test_block_without_ts_blocked():
    """Block ohne ts -> continue=false."""
    block = (
        "## BERATER_OUTPUTS.validator_round11\n"
        "set_by: _IDF_berater_validator\n"
        "exit_code: 0\n"
        "validated: true\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=block,
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "ts" in result.get("message", "")


# ---- Test 5: Edit auf andere Datei (nicht manifest) -> passthrough ------------------

def test_unrelated_file_passes():
    """Edit auf andere Datei (z.B. _berater_outputs.md) -> continue=true."""
    block = (
        "## BERATER_OUTPUTS.modusEntscheidung\n"
        "modus: M3\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_berater_outputs.md",
        new_string=block,
    )
    assert result["continue"] is True, (
        f"Expected pass for non-manifest, got: {result}"
    )


# ---- Test 6: Bestehender Block + neuer Block -----------------------------------------

def test_existing_block_without_provenance_ignored_new_block_checked():
    """Im old_string: Block ohne Provenance (legacy).
    Im new_string: derselbe Block PLUS neuer Block ohne Provenance.
    -> Nur der NEUE Block wird geblockt."""
    old = (
        "## BERATER_OUTPUTS.legacy_block\n"
        "result: ok_old\n"
    )
    new = (
        "## BERATER_OUTPUTS.legacy_block\n"
        "result: ok_old\n"
        "\n"
        "## BERATER_OUTPUTS.brand_new_block\n"
        "result: ok_new_but_no_provenance\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=new,
        old_string=old,
    )
    assert result["continue"] is False, (
        f"Expected block on new_block, got: {result}"
    )
    msg = result.get("message", "")
    assert "brand_new_block" in msg, f"Expected brand_new_block in msg, got: {msg}"
    # Legacy darf NICHT als Violation erscheinen
    assert "legacy_block" not in msg, (
        f"Legacy block sollte ignoriert sein, aber gefunden in: {msg}"
    )


# ---- Test 7: enforce=false -> WARN-only ----------------------------------------------

def test_warn_only_when_enforce_false():
    """enforce=false: continue=true ABER message gesetzt."""
    block = (
        "## BERATER_OUTPUTS.modusEntscheidung_round11\n"
        "exit_code: 0\n"
        "ts: 2026-05-27\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=block,
        enforce=False,
    )
    assert result["continue"] is True, f"Expected pass in WARN mode, got: {result}"
    assert "WARNING" in result.get("message", ""), (
        f"Expected WARNING marker in msg, got: {result}"
    )


# ---- Test 8: _factory_manifest.md auch geprueft --------------------------------------

def test_factory_manifest_triggers_guard():
    """_factory_manifest.md soll genauso geprueft werden wie _manifest.md."""
    block = (
        "## BERATER_OUTPUTS.bdfPlan\n"
        "modus: dispatch\n"
    )
    result = run_guard(
        tool_name="Write",
        file_path="/some/path/_factory_manifest.md",
        content=block,
    )
    assert result["continue"] is False, (
        f"Expected block on factory_manifest, got: {result}"
    )


# ---- Bonus: Suffix-Varianten (BERATER_OUTPUTS_IDF.x, _FE.x) erkannt ------------------

def test_suffix_variant_detected():
    """## BERATER_OUTPUTS_IDF.plAggregation_round11 ohne Provenance -> Block."""
    block = (
        "## BERATER_OUTPUTS_IDF.plAggregation_round11\n"
        "items: [PL-1, PL-2]\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=block,
    )
    assert result["continue"] is False, (
        f"Expected block on suffix variant, got: {result}"
    )
    assert "plAggregation_round11" in result.get("message", "")
