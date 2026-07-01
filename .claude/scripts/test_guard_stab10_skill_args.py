"""
pytest tests fuer guard_stab10_skill_args.py (Stab S#10).

8 Test-Cases (User-Spec):
  1. Skill(_A_orchestrate, "BL-218")           -> continue:true
  2. Skill(_A_orchestrate, "--resume")          -> continue:true
  3. Skill(_A_orchestrate, "")                  -> continue:false
  4. Skill(_IDF_orchestrate, "BL-218 --refresh-aks") -> continue:true
  5. Skill(_SDF_orchestrate, "--batch=v3_13")   -> continue:true
  6. Skill(_SDF_orchestrate, "")                -> continue:false
  7. Skill(_Pre_PR_orchestrate, "")             -> continue:true (keine Pflicht)
  8. Skill(_BDF_orchestrate, "--resume")        -> continue:true (kein Map-Eintrag = passthrough)

Pragmatik-Override-Test ergaenzt: --allow-noargs umgeht Block.

Pattern: test_guard_modus_writer.py / test_guard_geist4_bdf_to_idf.py.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_stab10_skill_args.py"


def run_guard(skill: str, args: str = "", *, tool_name: str = "Skill") -> dict:
    """Ruft guard_stab10_skill_args.py mit simuliertem Hook-Input auf.

    OMNI_ENFORCE_STAB10_GUARD=1 erzwingt enforce=true unabhaengig von
    _session_params.md.
    """
    if tool_name == "Skill":
        tool_input = {"skill": skill, "args": args}
    else:
        tool_input = {}

    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    env = os.environ.copy()
    env["OMNI_ENFORCE_STAB10_GUARD"] = "1"
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    stdout = (proc.stdout or "").strip()
    assert stdout, (
        f"Guard schrieb kein JSON auf stdout. stderr={proc.stderr!r}"
    )
    return json.loads(stdout)


# ──────────────────────────── Tests ────────────────────────────


def test_a_orchestrate_with_bl_id_passes():
    """Skill(_A_orchestrate, 'BL-218') -> continue=true."""
    result = run_guard("_A_orchestrate", "BL-218")
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_a_orchestrate_with_resume_flag_passes():
    """Skill(_A_orchestrate, '--resume') -> continue=true."""
    result = run_guard("_A_orchestrate", "--resume")
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_a_orchestrate_empty_args_blocks():
    """Skill(_A_orchestrate, '') -> continue=false (Phantom-Skip-Schutz)."""
    result = run_guard("_A_orchestrate", "")
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "STAB10_SKILL_ARGS" in result.get("message", ""), (
        f"Expected guard message, got: {result}"
    )
    assert "Phantom-Skip" in result.get("message", ""), (
        f"Expected Phantom-Skip hint, got: {result}"
    )


def test_idf_orchestrate_with_bl_and_extra_flag_passes():
    """Skill(_IDF_orchestrate, 'BL-218 --refresh-aks') -> continue=true."""
    result = run_guard("_IDF_orchestrate", "BL-218 --refresh-aks")
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_sdf_orchestrate_with_batch_flag_passes():
    """Skill(_SDF_orchestrate, '--batch=v3_13') -> continue=true."""
    result = run_guard("_SDF_orchestrate", "--batch=v3_13")
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_sdf_orchestrate_empty_args_blocks():
    """Skill(_SDF_orchestrate, '') -> continue=false."""
    result = run_guard("_SDF_orchestrate", "")
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "STAB10_SKILL_ARGS" in result.get("message", ""), (
        f"Expected guard message, got: {result}"
    )


def test_pre_pr_orchestrate_empty_args_passes():
    """Skill(_Pre_PR_orchestrate, '') -> continue=true (keine Pflicht-Regel)."""
    result = run_guard("_Pre_PR_orchestrate", "")
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_bdf_orchestrate_not_in_map_passes():
    """Skill(_BDF_orchestrate, '--resume') -> continue=true.

    _BDF_orchestrate hat keinen Eintrag in der Pflicht-Map -> Passthrough.
    """
    result = run_guard("_BDF_orchestrate", "--resume")
    assert result["continue"] is True, f"Expected passthrough, got: {result}"


# ──────────────────────────── Bonus-Tests (Robustness) ────────────────────────────


def test_allow_noargs_override_unblocks_a_orchestrate():
    """Pragmatik-Override: --allow-noargs umgeht Block."""
    result = run_guard("_A_orchestrate", "--allow-noargs")
    assert result["continue"] is True, f"Expected override pass, got: {result}"


def test_non_skill_tool_passes():
    """Anderer Tool-Aufruf (z.B. Read) -> continue=true (kein Skill-Trigger)."""
    result = run_guard("ignored", "ignored", tool_name="Read")
    assert result["continue"] is True, f"Expected passthrough, got: {result}"


def test_postbatch_with_bl_positional_passes():
    """Skill(_PostBatch_orchestrate, 'BL-v3_13') -> continue=true."""
    result = run_guard("_PostBatch_orchestrate", "BL-v3_13")
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_postbatch_with_stages_flag_passes():
    """Skill(_PostBatch_orchestrate, '--stages=stage7,stage8') -> continue=true."""
    result = run_guard("_PostBatch_orchestrate", "--stages=stage7,stage8")
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_postbatch_empty_blocks():
    """Skill(_PostBatch_orchestrate, '') -> continue=false."""
    result = run_guard("_PostBatch_orchestrate", "")
    assert result["continue"] is False, f"Expected block, got: {result}"


# ──────────────────────────── A: Aktionable Recovery (2026-05-28) ────────────────────────────


def test_block_message_contains_exact_retry_command():
    """A: Block-Message liefert das exakte Retry-Kommando (--resume Self-Heal)."""
    result = run_guard("_SDF_orchestrate", "DCSRE-486")
    assert result["continue"] is False
    msg = result.get("message", "")
    assert "RETRY" in msg, f"Erwarte RETRY-Hinweis, got: {msg!r}"
    assert "/_SDF_orchestrate DCSRE-486 --resume" in msg, (
        f"Erwarte exaktes Recovery-Kommando, got: {msg!r}"
    )


# ──────────────────────────── B: state-aware Auto-Resume (2026-05-28) ────────────────────────────

import tempfile as _tempfile


def _run_guard_with_manifest(skill: str, args: str, manifest_body: str | None, *, no_autoresume: bool = False) -> dict:
    """Wie run_guard, aber mit B-Manifest-Override (OMNI_STAB10_AUTORESUME_MANIFEST)."""
    hook_data = {"tool_name": "Skill", "tool_input": {"skill": skill, "args": args}}
    env = os.environ.copy()
    env["OMNI_ENFORCE_STAB10_GUARD"] = "1"
    tmp_path = None
    if manifest_body is not None:
        fd, tmp_path = _tempfile.mkstemp(suffix=".md")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(manifest_body)
        env["OMNI_STAB10_AUTORESUME_MANIFEST"] = tmp_path
    if no_autoresume:
        env["OMNI_STAB10_NO_AUTORESUME"] = "1"
    try:
        proc = subprocess.run(
            [sys.executable, str(GUARD_SCRIPT)],
            input=json.dumps(hook_data), capture_output=True, text=True, env=env,
        )
        return json.loads((proc.stdout or "").strip())
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)


_RESUMABLE_MANIFEST = """## DF_BATCH_STATE_round17_sdf
status: READY_FOR_MODE_DECISION
batch_order: [B_r17_03, B_r17_04]
batch_mode_hints: {...}
"""

# PRAEZISIERT 2026-05-31 (DCSRE-486 Round-19 Live-Stall): Terminal-Marker ist batch_status/df_status,
# NICHT nacktes `status:`. Frueher leakte ein finalSummary-`status:DONE` (Berater fertig) als Batch-
# terminal -> nach IDF_DONE blockte ein nackter _SDF_orchestrate. Der Test prueft jetzt den ECHTEN
# Batch-Lifecycle-Marker (Intent unveraendert: ein genuin-terminaler Batch blockt den nackten Resume).
_TERMINAL_MANIFEST = """## DF_BATCH_STATE_round17_sdf
batch_status: DONE
batch_order: [B_r17_03]
"""

_NO_SIGNAL_MANIFEST = """## SOME_OTHER_SECTION
foo: bar
"""


def test_b_resumable_state_auto_resumes():
    """B: nackter SDF-Call + nicht-terminaler DF_BATCH_STATE -> AUTO-RESUME (pass)."""
    result = _run_guard_with_manifest("_SDF_orchestrate", "DCSRE-486", _RESUMABLE_MANIFEST)
    assert result["continue"] is True, f"Erwarte Auto-Resume, got: {result}"
    assert "AUTO-RESUME" in result.get("message", "")


def test_b_terminal_state_still_blocks():
    """B: terminaler DF_BATCH_STATE (status DONE) -> Block bleibt (Phantom-Skip-Schutz)."""
    result = _run_guard_with_manifest("_SDF_orchestrate", "DCSRE-486", _TERMINAL_MANIFEST)
    assert result["continue"] is False, f"Erwarte Block, got: {result}"


def test_b_no_resumable_signal_blocks():
    """B: kein DF_BATCH_STATE-Resume-Signal -> Block bleibt."""
    result = _run_guard_with_manifest("_SDF_orchestrate", "DCSRE-486", _NO_SIGNAL_MANIFEST)
    assert result["continue"] is False, f"Erwarte Block, got: {result}"


def test_b_kill_switch_forces_block():
    """B: OMNI_STAB10_NO_AUTORESUME=1 -> Block trotz resumebarem State."""
    result = _run_guard_with_manifest("_SDF_orchestrate", "DCSRE-486", _RESUMABLE_MANIFEST, no_autoresume=True)
    assert result["continue"] is False, f"Erwarte Block (Kill-Switch), got: {result}"


def test_b_only_applies_to_sdf_not_idf():
    """B konservativ: IDF ist NICHT im resumable-Set -> Block trotz resumebarem State."""
    result = _run_guard_with_manifest("_IDF_orchestrate", "", _RESUMABLE_MANIFEST)
    assert result["continue"] is False, f"Erwarte Block (IDF nicht in B-Scope), got: {result}"


# ──────────────── P1: Args-Chain-Fallback (BL-RESILIENZ 2026-05-29) ────────────────
# Manifest unlesbar (current_context.py-Fragilitaet) -> B faellt auf Chain-Marker im args zurueck.
# In Tests ist das Manifest via OMNI_ENFORCE_STAB10_GUARD-Gate ohnehin "" (unlesbar simuliert).

def test_p1_idf_chain_args_autoresume():
    """Live-Fall: _SDF_orchestrate mit --from=idf_chain-Blob, Manifest unlesbar -> AUTO-RESUME."""
    result = run_guard("_SDF_orchestrate",
                       "DCSRE-486 --from=idf_chain --vault=C:/x | Goal=parking_lot_loop. IDF_DONE, current_sub_batch=batch_C2.")
    assert result["continue"] is True, f"Erwarte AUTO-RESUME via args-chain-signal, got: {result}"
    assert "AUTO-RESUME" in result.get("message", "")


def test_p1_goal_marker_args_autoresume():
    """Chain-Marker 'Goal=' allein reicht als Resume-Beweis."""
    result = run_guard("_SDF_orchestrate", "DCSRE-486 | Goal=parking_lot_loop")
    assert result["continue"] is True, f"Erwarte AUTO-RESUME (Goal=), got: {result}"


def test_p1_bare_blid_no_chain_marker_still_blocks():
    """Phantom-Skip-Schutz: bloße BL-ID OHNE Chain-Marker -> BLOCK (A-Recovery greift)."""
    result = run_guard("_SDF_orchestrate", "DCSRE-486")
    assert result["continue"] is False, f"Erwarte BLOCK (kein Chain-Marker), got: {result}"


def test_p1_empty_args_still_blocks():
    """Phantom-Skip-Schutz: wirklich leere args -> BLOCK."""
    result = run_guard("_SDF_orchestrate", "")
    assert result["continue"] is False, f"Erwarte BLOCK (leer), got: {result}"
