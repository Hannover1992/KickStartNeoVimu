"""
pytest tests fuer guard_geist2_bdf_to_a.py.

Geist G#2 (BDF -> A): Pruefe dass A-Pipeline NUR fuer UNREIF-BLs laufen darf.
Tests setzen einen Temp-Vault per OMNI_GEIST2_VAULT_ROOT und simulieren
Skill-Tool-Events ueber stdin.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_geist2_bdf_to_a.py"


def make_vault(tmp_path, bl_id, reifegrad):
    """Baut Temp-Vault mit Backlog/BL-{NNN}-test.md + Frontmatter reifegrad.
    Returns Path zum Vault-Root.
    """
    vault = tmp_path / "vault"
    backlog = vault / "Backlog"
    backlog.mkdir(parents=True)
    node = backlog / f"{bl_id}-test.md"
    frontmatter = (
        "---\n"
        f"id: \"{bl_id}\"\n"
        f"title: \"Test BL\"\n"
        f"reifegrad: {reifegrad}\n"
        "---\n\n"
        "# Test\n"
    )
    node.write_text(frontmatter, encoding="utf-8")
    return vault


def run_guard(tool_name, tool_input, vault_root=None, enforce=True):
    """Ruft guard_geist2_bdf_to_a.py mit Hook-Event ueber stdin auf.
    enforce=True setzt OMNI_ENFORCE_GEIST2_GUARD=1.
    """
    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    env = os.environ.copy()
    if enforce:
        env["OMNI_ENFORCE_GEIST2_GUARD"] = "1"
    else:
        env.pop("OMNI_ENFORCE_GEIST2_GUARD", None)
    if vault_root is not None:
        env["OMNI_GEIST2_VAULT_ROOT"] = str(vault_root)
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    if not proc.stdout.strip():
        pytest.fail(
            f"guard returned empty stdout. stderr={proc.stderr!r}, rc={proc.returncode}"
        )
    return json.loads(proc.stdout.strip())


# ---------- Tests ----------


def test_unreif_bl_passes(tmp_path):
    """UNREIF-BL -> A-Pipeline erlaubt, continue:true."""
    vault = make_vault(tmp_path, "BL-501", "UNREIF")
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_A_orchestrate", "args": "BL-501 some flags"},
        vault_root=vault,
    )
    assert result["continue"] is True, f"Expected pass for UNREIF, got: {result}"


def test_ready_bl_blocks_with_enforce(tmp_path):
    """READY-BL -> A-Pipeline verboten, BLOCK (enforceProcess=true)."""
    vault = make_vault(tmp_path, "BL-502", "READY")
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_A_orchestrate", "args": "BL-502"},
        vault_root=vault,
        enforce=True,
    )
    assert result["continue"] is False, f"Expected block for READY, got: {result}"
    assert "GEIST2" in result.get("message", ""), f"Expected guard message, got: {result}"


def test_ready_bl_warns_without_enforce(tmp_path):
    """READY-BL ohne enforce -> WARN, continue=true mit message."""
    # _session_params.md im Vault -> enforceProcess: false
    vault = make_vault(tmp_path, "BL-503", "READY")
    (vault / "_session_params.md").write_text(
        "**enforceProcess:** false\n", encoding="utf-8"
    )
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_A_orchestrate", "args": "BL-503"},
        vault_root=vault,
        enforce=False,  # nicht via ENV erzwingen -> Datei wird gelesen
    )
    assert result["continue"] is True, f"Expected warn-pass for READY no-enforce, got: {result}"
    # Message-Feld optional vorhanden
    assert "GEIST2" in result.get("message", ""), (
        f"Expected GEIST2 message even in warn-mode, got: {result}"
    )


def test_sc_reif_blocks(tmp_path):
    """SC-REIF -> BLOCK (enforce)."""
    vault = make_vault(tmp_path, "BL-504", "SC-REIF")
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_A_orchestrate", "args": "BL-504 --foo"},
        vault_root=vault,
        enforce=True,
    )
    assert result["continue"] is False, f"Expected block for SC-REIF, got: {result}"


def test_done_blocks(tmp_path):
    """DONE -> BLOCK (enforce)."""
    vault = make_vault(tmp_path, "BL-505", "DONE")
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_A_orchestrate", "args": "BL-505"},
        vault_root=vault,
        enforce=True,
    )
    assert result["continue"] is False, f"Expected block for DONE, got: {result}"


def test_other_skill_passes(tmp_path):
    """Andere Skills (nicht _A_orchestrate) -> Passthrough, continue=true."""
    vault = make_vault(tmp_path, "BL-506", "DONE")  # auch wenn DONE: andere Skill
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_BDF_orchestrate", "args": "BL-506"},
        vault_root=vault,
        enforce=True,
    )
    assert result["continue"] is True, f"Expected passthrough for non-A skill, got: {result}"


def test_no_bl_id_passes(tmp_path):
    """Keine BL-ID in args -> konservativ continue=true."""
    vault = make_vault(tmp_path, "BL-507", "DONE")
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_A_orchestrate", "args": "--help"},
        vault_root=vault,
        enforce=True,
    )
    assert result["continue"] is True, f"Expected pass without BL-ID, got: {result}"


def test_missing_vault_node_passes(tmp_path):
    """BL-ID ohne Vault-Knoten + ohne Manifest -> UNKNOWN -> continue=true."""
    # Vault mit Backlog-Folder aber ohne BL-Knoten
    vault = tmp_path / "vault_empty"
    (vault / "Backlog").mkdir(parents=True)
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill": "_A_orchestrate", "args": "BL-999"},
        vault_root=vault,
        enforce=True,
    )
    assert result["continue"] is True, (
        f"Expected conservative passthrough when reifegrad unknown, got: {result}"
    )


def test_non_skill_tool_passes(tmp_path):
    """Edit/Write Tool-Calls -> Passthrough (nur Skill ist relevant)."""
    vault = make_vault(tmp_path, "BL-508", "DONE")
    result = run_guard(
        tool_name="Edit",
        tool_input={"file_path": "/foo/bar.md", "new_string": "BL-508"},
        vault_root=vault,
        enforce=True,
    )
    assert result["continue"] is True, f"Expected passthrough for Edit, got: {result}"
