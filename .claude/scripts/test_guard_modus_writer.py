"""
pytest tests fuer guard_modus_writer.py (BL-165 AK-5 PL-TDD Stage 3).
4 Test-Cases: forbidden_key, non-whitelisted modus-write, whitelisted, unrelated.
"""

import json
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_modus_writer.py"


def run_guard(tool_name: str, file_path: str, content: str = "", new_string: str = "") -> dict:
    """Ruft guard_modus_writer.py mit simuliertem Hook-Input auf.
    OMNI_ENFORCE_MODUS_GUARD=1 erzwingt enforce=true unabhaengig von _session_params.md.
    """
    import os
    tool_input = {"file_path": file_path}
    if tool_name == "Write":
        tool_input["content"] = content
    else:
        tool_input["new_string"] = new_string

    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    env = os.environ.copy()
    env["OMNI_ENFORCE_MODUS_GUARD"] = "1"
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(proc.stdout.strip())


def test_blocks_forbidden_key_recommended_modus():
    """Edit mit 'recommended_modus: M3' in _manifest.md -> continue=false."""
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string="recommended_modus: M3\nmodus: M3\n",
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "MODUS_WRITER" in result.get("message", ""), f"Expected guard message, got: {result}"


def test_blocks_modus_write_without_whitelist():
    """Edit Manifest mit modus: M3 und modus_set_by: _other_skill -> continue=false."""
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string="DF_BATCH_STATE.modus: M3\nmodus_set_by: _other_skill\n",
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    assert "MODUS_WRITER" in result.get("message", ""), f"Expected guard message, got: {result}"


def test_allows_modus_write_with_whitelist():
    """Edit mit modus_set_by: _SDF_berater_modusEntscheidung -> continue=true."""
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string="DF_BATCH_STATE.modus: M3\nmodus_set_by: _SDF_berater_modusEntscheidung\n",
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_passes_unrelated_edits():
    """Edit auf andere Datei (_berater_outputs.md) -> continue=true, kein Block."""
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_berater_outputs.md",
        new_string="recommended_modus: M3\nsdf_mode_hint: heavy\n",
    )
    assert result["continue"] is True, f"Expected pass for non-manifest file, got: {result}"


# ───── BL-RCA-486-Round11 (2026-05-27): batch_modes plural + lead_fallback Tests ─────


def test_blocks_batch_modes_plural_without_whitelist():
    """LIVE-Beweis Round 11: IDF schreibt batch_modes ohne batch_modes_set_by -> MUSS blocken.

    Vor BL-RCA-486-Round11 Fix: ging durch weil Guard nur Singular `modus` kannte.
    Nach Fix: Plural batch_modes-Pattern matched + Block.
    """
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=(
            "## DF_BATCH_STATE (Round 11)\n"
            "batch_modes:\n"
            "  batch_v3_13: M2\n"
            "  batch_v3_14: M3\n"
        ),
    )
    assert result["continue"] is False, (
        f"REGRESSION! batch_modes plural sollte blockiert sein (DCSRE-486 Round 11 Bug). "
        f"Got: {result}"
    )
    assert "MODUS_WRITER" in result.get("message", "")


def test_blocks_batch_modes_with_wrong_writer():
    """batch_modes mit batch_modes_set_by: _IDF_berater_metricPlanner -> Block."""
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=(
            "batch_modes:\n"
            "  batch_v3_13: M2\n"
            "batch_modes_set_by: _IDF_berater_metricPlanner\n"
        ),
    )
    assert result["continue"] is False
    assert "MODUS_WRITER" in result.get("message", "")


def test_allows_batch_modes_with_whitelisted_writer():
    """batch_modes mit batch_modes_set_by: _SDF_berater_modusEntscheidung -> pass."""
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=(
            "batch_modes:\n"
            "  batch_v3_13: M2\n"
            "batch_modes_set_by: _SDF_berater_modusEntscheidung\n"
        ),
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_blocks_modus_begruendung_per_batch_forbidden_key():
    """modus_begruendung_per_batch ist BL-RCA-486-Round11 forbidden_key — Block."""
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=(
            "modus_begruendung_per_batch:\n"
            "  batch_v3_13: M2 weil quickwins\n"
        ),
    )
    assert result["continue"] is False
    assert "MODUS_WRITER" in result.get("message", "")


def test_blocks_lead_fallback_without_pragmatik_reason():
    """`mode: lead_fallback` ohne pragmatik_reason -> Block."""
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=(
            "## DF_BATCH_STATE_round11\n"
            "mode: lead_fallback\n"
            "batch_keys: [batch_v3_13]\n"
        ),
    )
    assert result["continue"] is False, (
        f"REGRESSION! lead_fallback ohne pragmatik_reason sollte blockiert sein. Got: {result}"
    )


def test_allows_lead_fallback_with_pragmatik_reason():
    """mode: lead_fallback MIT pragmatik_reason innerhalb 200 Zeichen -> pass."""
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string=(
            "mode: lead_fallback\n"
            "pragmatik_reason: SDF Phase 1.1 timeout, single-batch retry mit Lead-Decision\n"
        ),
    )
    assert result["continue"] is True, f"Expected pass with pragmatik_reason, got: {result}"


# ───── BL-380 B2/AK-4 (QDSA-Antrieb): quality_goals[] + quality_scenario INV-MODUS-5 ─────
# Die taskDefinition-quality_goals[] (1_Task/BL-SLUG_Task.md) und quality_scenario-Nodes
# (2_Model/*.md) leben NICHT in _manifest.md. Der Guard pruefte vor BL-380 NUR _manifest.md
# (continue=true fuer alles andere) → ein quality_goal/quality_scenario das ein Modus-Feld
# encoden will, ging ungestoert durch. BL-380 erweitert die forbidden-field-Pruefung auf
# diese QDSA-Strukturen (content-getriggert, dateiname-unabhaengig, additiv).


def test_blocks_quality_goals_with_recommended_modus_in_task():
    """AK-4: quality_goals[]-Block in Task-Datei mit recommended_modus -> Block (INV-MODUS-5).

    Vor BL-380: Task-Datei != _manifest.md -> continue=true (Naming-Bypass moeglich).
    Nach BL-380: quality_goals-Struktur triggert forbidden-field-Pruefung -> Block.
    """
    result = run_guard(
        tool_name="Write",
        file_path="/vault/Backlog/BL-380-x/1_Task/BL-380_Task.md",
        content=(
            "## quality_goals\n"
            "quality_goals:\n"
            "  - goal_id: QG-1\n"
            "    qualitaetsziel: Wartbarkeit\n"
            "    priority_source: paragraph_1_2\n"
            "    recommended_modus: M3\n"
        ),
    )
    assert result["continue"] is False, (
        f"AK-4: quality_goals mit recommended_modus muss blockiert sein (INV-MODUS-5). Got: {result}"
    )
    assert "MODUS_WRITER" in result.get("message", ""), f"Expected guard message, got: {result}"


def test_blocks_quality_scenario_node_with_sdf_mode_in_model():
    """AK-4: quality_scenario-Node in Model-Datei mit sdf_mode -> Block (INV-MODUS-5)."""
    result = run_guard(
        tool_name="Edit",
        file_path="/vault/Backlog/BL-380-x/2_Model/BL-380_Model.md",
        new_string=(
            "### W-EXAMPLE-1\n"
            "type: quality_scenario\n"
            "id: BL-380.QS-1\n"
            "sdf_mode: heavy\n"
        ),
    )
    assert result["continue"] is False, (
        f"AK-4: quality_scenario mit sdf_mode muss blockiert sein (INV-MODUS-5). Got: {result}"
    )
    assert "MODUS_WRITER" in result.get("message", ""), f"Expected guard message, got: {result}"


def test_blocks_quality_goals_forbidden_value_pattern():
    """AK-4: quality_goals-Block mit forbidden_value_pattern ('Empfehlung M3') -> Block."""
    result = run_guard(
        tool_name="Write",
        file_path="/vault/Backlog/BL-380-x/1_Task/BL-380_Task.md",
        content=(
            "quality_goals:\n"
            "  - goal_id: QG-1\n"
            "    qualitaetsziel: Leistungseffizienz (Empfehlung M3 fuer schnelle Iteration)\n"
        ),
    )
    assert result["continue"] is False, (
        f"AK-4: quality_goals mit 'Empfehlung M3' (forbidden_value_pattern) muss blockiert sein. Got: {result}"
    )


def test_allows_legit_quality_goals_without_modus_field():
    """AK-4: Legitimer quality_goals[]-Block OHNE Modus-Feld -> pass (kein Naming-Bypass)."""
    result = run_guard(
        tool_name="Write",
        file_path="/vault/Backlog/BL-380-x/1_Task/BL-380_Task.md",
        content=(
            "## quality_goals\n"
            "quality_goals:\n"
            "  - goal_id: QG-1\n"
            "    qualitaetsziel: Wartbarkeit\n"
            "    iso25010_achse: Wartbarkeit\n"
            "    priority_source: paragraph_1_2\n"
            "    priority_rank: 1\n"
            "  - goal_id: QG-2\n"
            "    qualitaetsziel: Zuverlaessigkeit\n"
            "    priority_source: srs_ranking\n"
            "    priority_rank: 2\n"
        ),
    )
    assert result["continue"] is True, (
        f"AK-4: legitimer quality_goals-Block (ohne Modus-Feld) muss passieren. Got: {result}"
    )


def test_allows_legit_quality_scenario_node_without_modus_field():
    """AK-4: Legitimer quality_scenario-Node (6-Feld-iSAQB) OHNE Modus-Feld -> pass."""
    result = run_guard(
        tool_name="Edit",
        file_path="/vault/Backlog/BL-380-x/2_Model/BL-380_Model.md",
        new_string=(
            "### W-EXAMPLE-2\n"
            "type: quality_scenario\n"
            "id: BL-380.QS-2\n"
            "scenario:\n"
            "  source: Nutzer\n"
            "  stimulus: 1000 parallele Anfragen\n"
            "  artifact: API-Gateway\n"
            "  environment: Last\n"
            "  response: valide Antwort ohne Timeout\n"
            "  response_measure:\n"
            "    metric: p90-Latenz\n"
            "    threshold: p90 < 200ms\n"
            "    method: Lasttest via k6\n"
            "endpoint_type: ak_test\n"
            "endpoint_ref: AK-12\n"
        ),
    )
    assert result["continue"] is True, (
        f"AK-4: legitimer quality_scenario-Node (ohne Modus-Feld) muss passieren. Got: {result}"
    )


def test_qdsa_scope_non_qdsa_non_manifest_still_passes():
    """AK-4-Additiv-Schutz: Nicht-QDSA-Datei OHNE quality_goals/quality_scenario mit
    forbidden_key passiert weiterhin (BL-380-Erweiterung ist QDSA-getriggert, nicht global).

    Spiegelt test_passes_unrelated_edits — stellt sicher, dass die BL-380-Erweiterung NICHT
    jede Nicht-Manifest-Datei auf forbidden_keys prueft (sonst Regression an _berater_outputs.md).
    """
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_berater_outputs.md",
        new_string="recommended_modus: M3\nsdf_mode_hint: heavy\n",
    )
    assert result["continue"] is True, (
        f"AK-4: Nicht-QDSA-Nicht-Manifest-Datei muss weiterhin passieren (kein globaler Scan). Got: {result}"
    )


# ───── BL-410 AK-3a: Anti-Rueckkehr-Fixture — list-form INV-MODUS-5-Verbotskeys ─────


def test_blocks_forbidden_key_listform_sdf_mode():
    """AK-3/BL-410: list-form '- sdf_mode: heavy' in Manifest MUSS blockiert sein.

    Anti-Rueckkehr-Fixture: lockt BL-382-AK-11-Fix ((?:-\\s*)?{key}-Pattern in
    check_forbidden_keys) fest. Wenn dieses Pattern entfernt wird -> RED hier.
    """
    result = run_guard(
        tool_name="Edit",
        file_path="/some/path/_manifest.md",
        new_string="features:\n  - sdf_mode: heavy\n",
    )
    assert result["continue"] is False, (
        f"BL-410 AK-3: list-form '- sdf_mode: heavy' muss blockiert sein (BL-382-Fix). Got: {result}"
    )
    assert "MODUS_WRITER" in result.get("message", ""), (
        f"Expected MODUS_WRITER guard message, got: {result}"
    )
