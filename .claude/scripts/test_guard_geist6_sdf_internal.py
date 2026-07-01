"""pytest tests fuer guard_geist6_sdf_internal.py.

Geist G#6 PreToolUse Hook: SDF Phase 1.1 modusEntscheidung muss VOR Phase 2.1 Dispatch laufen.

Test-Setup:
  - Manifest-Stub via OMNI_GEIST6_MANIFEST (Pfad zu tmp_path).
  - Enforce-Modus via OMNI_ENFORCE_GEIST6 (1=true, 0=false).
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_geist6_sdf_internal.py"


def run_guard(
    tool_name: str,
    tool_input: dict,
    manifest_content: str | None = None,
    enforce: bool = True,
    tmp_path: Path | None = None,
) -> dict:
    """Ruft guard_geist6_sdf_internal.py mit simuliertem Hook-Input auf."""
    import os

    env = os.environ.copy()
    env["OMNI_ENFORCE_GEIST6"] = "1" if enforce else "0"

    if manifest_content is not None:
        assert tmp_path is not None, "tmp_path benoetigt fuer Manifest-Stub"
        manifest_file = tmp_path / "_manifest.md"
        manifest_file.write_text(manifest_content, encoding="utf-8")
        env["OMNI_GEIST6_MANIFEST"] = str(manifest_file)
    else:
        # explizit nicht setzen — Hook nutzt Vault/Default
        env.pop("OMNI_GEIST6_MANIFEST", None)

    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, f"Guard non-zero exit: {proc.returncode}, stderr={proc.stderr}"
    return json.loads(proc.stdout.strip())


# ───────────────────────── Manifest-Fixtures ─────────────────────────

MANIFEST_COMPLETE = """\
df_status: ITEM_LOOP

## DF_BATCH_STATE
batch_items: [BL-218]
modus: M3
modus_set_by: _SDF_berater_modusEntscheidung
modus_begruendung: "Aus k_score=70 + srs=48 + batch_type=standard -> M3"

## BERATER_OUTPUTS
modusEntscheidung:
  gewaehlter_modus: M3
  pipeline_route: A_I
  batch_aware: true
  completed_at: "2026-05-27T12:00:00Z"
  last_berater: _SDF_berater_modusEntscheidung
"""


MANIFEST_COMPLETE_MULTIROUND = """\
df_status: BATCH_LOOP

## DF_BATCH_STATE_BATCH2
batch_items: [BL-218]
batch_modes:
  batch_v3_13: M2
  batch_v3_14: M3
batch_modes_set_by: _SDF_berater_modusEntscheidung

## BERATER_OUTPUTS
modusEntscheidung_round2:
  gewaehlter_modus: M2
  completed_at: "2026-05-27T13:00:00Z"
modusEntscheidung_round_3:
  gewaehlter_modus: M3
  completed_at: "2026-05-27T14:00:00Z"
"""


MANIFEST_NO_BERATER_OUTPUTS = """\
df_status: ITEM_LOOP

## DF_BATCH_STATE
batch_items: [BL-218]
modus: M3
modus_set_by: _SDF_berater_modusEntscheidung
"""


MANIFEST_NO_MODUS_SET_BY = """\
df_status: ITEM_LOOP

## DF_BATCH_STATE
batch_items: [BL-218]
modus: M3
modus_begruendung: "klar M3"

## BERATER_OUTPUTS
modusEntscheidung:
  gewaehlter_modus: M3
"""


MANIFEST_WRONG_WRITER = """\
df_status: ITEM_LOOP

## DF_BATCH_STATE
batch_items: [BL-218]
modus: M3
modus_set_by: _IDF_berater_metricPlanner

## BERATER_OUTPUTS
modusEntscheidung:
  gewaehlter_modus: M3
"""


# ───────────────────────── Tests ─────────────────────────


def test_continue_when_all_contracts_satisfied(tmp_path):
    """Vollstaendiger BERATER_OUTPUTS + modus + modus_set_by -> continue=true."""
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_SDF_berater_executionDispatch"},
        manifest_content=MANIFEST_COMPLETE,
        enforce=True,
        tmp_path=tmp_path,
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"
    assert "message" not in result or "VIOLATION" not in result.get("message", "")


def test_continue_when_multiround_contracts_satisfied(tmp_path):
    """Multi-Round Manifest mit modusEntscheidung_round{N} + batch_modes_set_by -> continue=true."""
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_I_orchestrate"},
        manifest_content=MANIFEST_COMPLETE_MULTIROUND,
        enforce=True,
        tmp_path=tmp_path,
    )
    assert result["continue"] is True, f"Expected pass (multi-round valid), got: {result}"


def test_blocks_when_berater_outputs_missing(tmp_path):
    """Skill(_I_orchestrate) ohne BERATER_OUTPUTS.modusEntscheidung -> continue=false."""
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_I_orchestrate"},
        manifest_content=MANIFEST_NO_BERATER_OUTPUTS,
        enforce=True,
        tmp_path=tmp_path,
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "GEIST_G6" in result.get("message", "")
    assert "modusEntscheidung" in result.get("message", "")


def test_blocks_when_modus_set_by_missing(tmp_path):
    """modus ohne modus_set_by -> continue=false."""
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_SC_orchestrate"},
        manifest_content=MANIFEST_NO_MODUS_SET_BY,
        enforce=True,
        tmp_path=tmp_path,
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "GEIST_G6" in result.get("message", "")
    assert "modus_set_by" in result.get("message", "") or "set_by" in result.get("message", "")


def test_blocks_when_writer_not_whitelisted(tmp_path):
    """modus_set_by mit anderem Writer (z.B. _IDF_berater_metricPlanner) -> continue=false."""
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_SDF_berater_executionDispatch"},
        manifest_content=MANIFEST_WRONG_WRITER,
        enforce=True,
        tmp_path=tmp_path,
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "GEIST_G6" in result.get("message", "")
    # Writer-Name oder 'not whitelisted'/'whitelisted' im Message
    assert (
        "_IDF_berater_metricPlanner" in result.get("message", "")
        or "whitelisted" in result.get("message", "")
    )


def test_passes_unrelated_skill(tmp_path):
    """Skill der nicht G#6 triggert (z.B. _BDF_orchestrate) -> continue=true ohne Check."""
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_BDF_orchestrate"},
        manifest_content=MANIFEST_NO_BERATER_OUTPUTS,  # bewusst unvollstaendig
        enforce=True,
        tmp_path=tmp_path,
    )
    assert result["continue"] is True, f"Expected pass (unrelated skill), got: {result}"


def test_warn_mode_continues_with_additional_context(tmp_path):
    """enforceProcess=false + Verletzung -> continue=true + additionalContext + message."""
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_I_orchestrate"},
        manifest_content=MANIFEST_NO_BERATER_OUTPUTS,
        enforce=False,
        tmp_path=tmp_path,
    )
    assert result["continue"] is True, f"Warn-Modus muss continue=true sein, got: {result}"
    assert "GEIST_G6" in result.get("message", ""), f"Warn-Message fehlt: {result}"
    assert "additionalContext" in result, f"additionalContext fehlt in Warn-Modus: {result}"
