"""
pytest Tests fuer guard_geist5_idf_to_sdf.py (Geist G#5 IDF -> SDF Contract-Hook).

8 Test-Cases:
  1. IDF_DONE + batch_mode_hints + batch_stages + batch_items_per_batch -> continue:true
  2. Kein IDF_DONE -> continue:false ("IDF not completed")
  3. batch_mode_hints fehlt -> continue:false ("IDF contract missing")
  4. batch_stages fehlt -> continue:false
  5. batch_modes ohne writer -> continue:false (= Round 11 Drift)
  6. Legitimer Re-Entry (batch_modes_set_by=SDF) -> continue:true
  7. Andere Skills (passthrough) -> continue:true
  8. mode: lead_fallback ohne pragmatik_reason -> continue:false (Lead-Bypass)

Strategie: temp Vault-Dir mit fake _factory_manifest.md schreiben, dann
guard via subprocess + simulierter sys.stdin Hook-Input testen.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_geist5_idf_to_sdf.py"


def run_guard(
    skill_name: str,
    manifest_content: str | None,
    tmp_path: Path,
    enforce: bool = True,
    use_legacy_manifest: bool = False,
) -> dict:
    """Ruft guard_geist5_idf_to_sdf.py mit simuliertem Skill-Hook-Input auf.

    Schreibt manifest_content (wenn nicht None) in tmp_path/_factory_manifest.md
    (oder _manifest.md bei use_legacy_manifest=True).
    """
    if manifest_content is not None:
        manifest_name = "_manifest.md" if use_legacy_manifest else "_factory_manifest.md"
        (tmp_path / manifest_name).write_text(manifest_content, encoding="utf-8")

    tool_input = {"skill": skill_name}
    hook_data = {"tool_name": "Skill", "tool_input": tool_input}

    env = os.environ.copy()
    env["OMNI_GEIST5_VAULT_ROOT"] = str(tmp_path)
    env["OMNI_ENFORCE_GEIST5_GUARD"] = "1" if enforce else "0"

    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    if not proc.stdout.strip():
        raise AssertionError(
            f"guard_geist5_idf_to_sdf.py gab keinen Output. stderr={proc.stderr!r}"
        )
    return json.loads(proc.stdout.strip())


# ────────────────────────────────────────────────────────────────────────
# Fixtures: typische Manifest-Inhalte
# ────────────────────────────────────────────────────────────────────────


HAPPY_PATH_MANIFEST = """\
## IDF_PIPELINE_STATE
status: IDF_DONE
phase: phase_8_done

## DF_BATCH_STATE
batch_items_per_batch:
  batch_v3_13:
    - PL-3-01
    - PL-3-02
  batch_v3_14:
    - PL-3-05

batch_mode_hints:
  batch_v3_13: M2
  batch_v3_14: M3

batch_stages:
  batch_v3_13: [stage_1, stage_2]
  batch_v3_14: [stage_1, stage_2, stage_3]
"""


LEGITIMATE_REENTRY_MANIFEST = """\
## IDF_PIPELINE_STATE
status: IDF_DONE

## DF_BATCH_STATE
batch_items_per_batch:
  batch_v3_13:
    - PL-3-01

batch_modes:
  batch_v3_13: M2
batch_modes_set_by: _SDF_berater_modusEntscheidung

batch_stages:
  batch_v3_13: [stage_1]
"""


ROUND_11_DRIFT_MANIFEST = """\
## IDF_PIPELINE_STATE
status: IDF_DONE

## DF_BATCH_STATE
batch_items_per_batch:
  batch_v3_13:
    - PL-3-01

batch_modes:
  batch_v3_13: M2
  batch_v3_14: M3

batch_stages:
  batch_v3_13: [stage_1]
"""


NO_IDF_DONE_MANIFEST = """\
## IDF_PIPELINE_STATE
status: PHASE_5_RUNNING

## DF_BATCH_STATE
batch_items_per_batch:
  batch_v3_13:
    - PL-3-01

batch_mode_hints:
  batch_v3_13: M2

batch_stages:
  batch_v3_13: [stage_1]
"""


NO_HINTS_MANIFEST = """\
## IDF_PIPELINE_STATE
status: IDF_DONE

## DF_BATCH_STATE
batch_items_per_batch:
  batch_v3_13:
    - PL-3-01

batch_stages:
  batch_v3_13: [stage_1]
"""


NO_STAGES_MANIFEST = """\
## IDF_PIPELINE_STATE
status: IDF_DONE

## DF_BATCH_STATE
batch_items_per_batch:
  batch_v3_13:
    - PL-3-01

batch_mode_hints:
  batch_v3_13: M2
"""


LEAD_FALLBACK_DRIFT_MANIFEST = """\
## IDF_PIPELINE_STATE
status: IDF_DONE

## DF_BATCH_STATE
batch_items_per_batch:
  batch_v3_13:
    - PL-3-01

batch_mode_hints:
  batch_v3_13: M2

batch_stages:
  batch_v3_13: [stage_1]

mode: lead_fallback
batch_keys: [batch_v3_13]
"""


# ────────────────────────────────────────────────────────────────────────
# Tests
# ────────────────────────────────────────────────────────────────────────


def test_happy_path_idf_done_with_hints_and_stages(tmp_path):
    """1. IDF_DONE + batch_mode_hints + batch_stages + items -> continue:true."""
    result = run_guard("_SDF_orchestrate", HAPPY_PATH_MANIFEST, tmp_path)
    assert result["continue"] is True, (
        f"Expected pass (Happy Path), got: {result}"
    )


def test_blocks_when_idf_not_done(tmp_path):
    """2. Kein IDF_DONE -> continue:false ('IDF not completed')."""
    result = run_guard("_SDF_orchestrate", NO_IDF_DONE_MANIFEST, tmp_path)
    assert result["continue"] is False, f"Expected block, got: {result}"
    msg = result.get("message", "")
    assert "IDF_DONE" in msg or "IDF not completed" in msg, (
        f"Expected IDF-not-completed message, got: {msg}"
    )


def test_blocks_when_batch_mode_hints_missing(tmp_path):
    """3. batch_mode_hints fehlt -> continue:false ('IDF contract missing')."""
    result = run_guard("_SDF_orchestrate", NO_HINTS_MANIFEST, tmp_path)
    assert result["continue"] is False, f"Expected block, got: {result}"
    msg = result.get("message", "")
    assert "batch_mode_hints" in msg, (
        f"Expected batch_mode_hints message, got: {msg}"
    )
    assert "IDF contract missing" in msg or "contract missing" in msg.lower()


def test_blocks_when_batch_stages_missing(tmp_path):
    """4. batch_stages fehlt -> continue:false."""
    result = run_guard("_SDF_orchestrate", NO_STAGES_MANIFEST, tmp_path)
    assert result["continue"] is False, f"Expected block, got: {result}"
    msg = result.get("message", "")
    assert "batch_stages" in msg, (
        f"Expected batch_stages message, got: {msg}"
    )


def test_blocks_round_11_drift_batch_modes_without_writer(tmp_path):
    """5. batch_modes ohne batch_modes_set_by -> continue:false (Round 11 Drift)."""
    result = run_guard("_SDF_orchestrate", ROUND_11_DRIFT_MANIFEST, tmp_path)
    assert result["continue"] is False, (
        f"REGRESSION! batch_modes ohne batch_modes_set_by ist Round-11-Drift. "
        f"Expected block, got: {result}"
    )
    msg = result.get("message", "")
    assert "Round-11" in msg or "batch_modes" in msg or "IDF schrieb" in msg, (
        f"Expected Round-11-Drift message, got: {msg}"
    )


def test_allows_legitimate_reentry_batch_modes_with_sdf_writer(tmp_path):
    """6. batch_modes mit batch_modes_set_by=_SDF_berater_modusEntscheidung -> continue:true."""
    result = run_guard("_SDF_orchestrate", LEGITIMATE_REENTRY_MANIFEST, tmp_path)
    assert result["continue"] is True, (
        f"Expected pass (legitimer Re-Entry), got: {result}"
    )


def test_passthrough_for_other_skills(tmp_path):
    """7. Skill != _SDF_orchestrate -> continue:true ohne Check."""
    # KEIN Manifest schreiben — guard darf nicht prufen.
    result = run_guard("_I_orchestrate", None, tmp_path)
    assert result["continue"] is True, (
        f"Expected passthrough for other skill, got: {result}"
    )

    # Auch bei kaputtem Manifest: andere Skills nie checken.
    result2 = run_guard("_A_orchestrate", "garbage content", tmp_path)
    assert result2["continue"] is True, (
        f"Expected passthrough for _A_orchestrate, got: {result2}"
    )


def test_blocks_lead_fallback_without_pragmatik_reason(tmp_path):
    """8. mode: lead_fallback ohne pragmatik_reason -> continue:false (Lead-Bypass-Drift)."""
    result = run_guard("_SDF_orchestrate", LEAD_FALLBACK_DRIFT_MANIFEST, tmp_path)
    assert result["continue"] is False, (
        f"REGRESSION! lead_fallback ohne pragmatik_reason ist Round-11-Pattern. "
        f"Expected block, got: {result}"
    )
    msg = result.get("message", "")
    assert "lead_fallback" in msg or "pragmatik_reason" in msg, (
        f"Expected lead_fallback message, got: {msg}"
    )


# ────────────────────────────────────────────────────────────────────────
# Zusatz-Tests: Edge-Cases (Bonus)
# ────────────────────────────────────────────────────────────────────────


def test_warn_mode_does_not_block(tmp_path):
    """enforceProcess=false -> continue:true mit message (WARN-Mode)."""
    result = run_guard(
        "_SDF_orchestrate",
        ROUND_11_DRIFT_MANIFEST,
        tmp_path,
        enforce=False,
    )
    assert result["continue"] is True, (
        f"WARN-mode darf nicht blocken, got: {result}"
    )
    # Message muss trotzdem da sein
    assert "GEIST5" in result.get("message", "") or "GUARD" in result.get("message", "")


def test_legacy_manifest_fallback(tmp_path):
    """guard nutzt _manifest.md als Fallback wenn _factory_manifest.md fehlt."""
    result = run_guard(
        "_SDF_orchestrate",
        HAPPY_PATH_MANIFEST,
        tmp_path,
        use_legacy_manifest=True,
    )
    assert result["continue"] is True, (
        f"Legacy _manifest.md fallback sollte funktionieren, got: {result}"
    )


def test_missing_manifest_blocks(tmp_path):
    """Kein Manifest vorhanden -> guard MUSS blocken (SDF darf nicht ohne IDF starten)."""
    # tmp_path bewusst leer lassen
    result = run_guard("_SDF_orchestrate", None, tmp_path)
    assert result["continue"] is False, (
        f"Fehlendes Manifest darf nicht durchlaufen, got: {result}"
    )
