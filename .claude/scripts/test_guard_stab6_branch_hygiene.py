"""
pytest tests fuer guard_stab6_branch_hygiene.py (Stab S#6).

Tests verwenden Env-Overrides:
  - OMNI_ENFORCE_STAB6_GUARD=1  -> erzwingt enforce=true (unabhaengig von _session_params.md)
  - OMNI_STAB6_GIT_STATUS       -> simulierter git status --porcelain Output
  - OMNI_STAB6_BATCH_MARKER     -> 0/1 simulierter Batch-Marker-Check
  - OMNI_BRANCH_HYGIENE_SKIP=1  -> Override skip
  - OMNI_STAB6_SESSION_PARAMS   -> Pfad zu Test-Session-Params

Pattern: test_guard_modus_writer.py (BL-165).
"""

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_stab6_branch_hygiene.py"


def run_guard(
    tool_name: str = "Skill",
    skill: str = "_BDF_orchestrate",
    args: str = "--batch=batch_v3_13",
    git_status: str = "",
    batch_marker: str | None = None,
    skip_env: bool = False,
    enforce: bool = True,
    extra_env: dict | None = None,
) -> dict:
    """Ruft guard_stab6_branch_hygiene.py mit simuliertem Hook-Input + Env auf."""
    tool_input: dict = {"skill": skill, "args": args}
    hook_data = {"tool_name": tool_name, "tool_input": tool_input}

    env = os.environ.copy()
    env["OMNI_ENFORCE_STAB6_GUARD"] = "1" if enforce else "0"
    env["OMNI_STAB6_GIT_STATUS"] = git_status
    # Tests neutralisieren Session-Params (Datei darf nicht stoeren)
    env.setdefault("OMNI_STAB6_SESSION_PARAMS", str(SCRIPT_DIR / "__nonexistent__.md"))
    if batch_marker is not None:
        env["OMNI_STAB6_BATCH_MARKER"] = batch_marker
    if skip_env:
        env["OMNI_BRANCH_HYGIENE_SKIP"] = "1"
    else:
        env.pop("OMNI_BRANCH_HYGIENE_SKIP", None)
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


def _make_porcelain(n: int, prefix: str = " M ") -> str:
    """Generiert n Zeilen simuliertes git status --porcelain Output."""
    return "\n".join(f"{prefix}path/to/file_{i}.cs" for i in range(n))


# ───── S#6 Branch-Hygiene Core Tests ─────


def test_clean_branch_with_batch_arg_passes():
    """0 modified files + Skill(_BDF_orchestrate) --batch=foo -> continue=true."""
    result = run_guard(
        skill="_BDF_orchestrate",
        args="--batch=batch_v3_13",
        git_status="",
        batch_marker="0",
    )
    assert result["continue"] is True, f"Saubere Branch sollte passen, got: {result}"


def test_three_modified_below_warn_threshold_passes():
    """3 modified files (unter WARN_THRESHOLD=5) -> continue=true."""
    result = run_guard(
        skill="_BDF_orchestrate",
        args="--batch=batch_v3_13",
        git_status=_make_porcelain(3),
        batch_marker="0",
    )
    assert result["continue"] is True, f"3 files unter Threshold, got: {result}"


def test_twentyfive_modified_blocks_bdf_orchestrate():
    """25 modified files + Skill(_BDF_orchestrate) --batch=... -> continue=false (BLOCK)."""
    result = run_guard(
        skill="_BDF_orchestrate",
        args="--batch=batch_v3_13",
        git_status=_make_porcelain(25),
        batch_marker="0",
    )
    assert result["continue"] is False, (
        f"25 modified files MUSS blocken (Cross-Batch-Drift). Got: {result}"
    )
    assert "STAB6_BRANCH_HYGIENE" in result.get("message", "")
    assert "Cross-Batch-Drift" in result.get("message", "")


def test_twentyfive_modified_with_env_override_passes():
    """25 modified files + OMNI_BRANCH_HYGIENE_SKIP=1 -> continue=true."""
    result = run_guard(
        skill="_BDF_orchestrate",
        args="--batch=batch_v3_13",
        git_status=_make_porcelain(25),
        batch_marker="0",
        skip_env=True,
    )
    assert result["continue"] is True, (
        f"Override OMNI_BRANCH_HYGIENE_SKIP=1 MUSS BLOCK aushebeln. Got: {result}"
    )


def test_other_skills_passthrough():
    """Skill(_I_orchestrate) ohne Stab6-Coverage -> continue=true unabhaengig von git status."""
    result = run_guard(
        skill="_I_orchestrate",
        args="--batch=batch_v3_13",
        git_status=_make_porcelain(50),
        batch_marker="0",
    )
    assert result["continue"] is True, (
        f"Andere Skills sollen passthrough, got: {result}"
    )


def test_skill_without_batch_arg_passes():
    """Skill(_BDF_orchestrate) ohne --batch=... -> continue=true (kein Batch-Start)."""
    result = run_guard(
        skill="_BDF_orchestrate",
        args="--resume",
        git_status=_make_porcelain(25),
        batch_marker="0",
    )
    assert result["continue"] is True, (
        f"_BDF_orchestrate ohne --batch ist kein Batch-Start, got: {result}"
    )


def test_eight_modified_with_batch_marker_passes():
    """8 modified files (ueber WARN) ABER mit Batch-Marker -> continue=true."""
    result = run_guard(
        skill="_SDF_orchestrate",
        args="--batch=batch_v3_14",
        git_status=_make_porcelain(8),
        batch_marker="1",
    )
    assert result["continue"] is True, (
        f"Batch-Marker = laufender Batch, kein Drift, got: {result}"
    )


def test_eight_modified_without_batch_marker_warns_passes():
    """8 modified files (>5 WARN, <20 BLOCK), kein Marker -> WARN aber continue=true."""
    result = run_guard(
        skill="_SDF_orchestrate",
        args="--batch=batch_v3_14",
        git_status=_make_porcelain(8),
        batch_marker="0",
    )
    assert result["continue"] is True, (
        f"WARN-Pfad muss continue=true halten, got: {result}"
    )
    assert "STAB6_BRANCH_HYGIENE" in result.get("message", "")
    assert "WARN" in result.get("message", "")


def test_block_downgrades_to_warn_when_enforce_false():
    """25 modified files mit enforce=false -> continue=true (WARN-Downgrade)."""
    result = run_guard(
        skill="_BDF_orchestrate",
        args="--batch=batch_v3_13",
        git_status=_make_porcelain(25),
        batch_marker="0",
        enforce=False,
    )
    assert result["continue"] is True, (
        f"enforce=false MUSS BLOCK zu WARN downgraden, got: {result}"
    )
