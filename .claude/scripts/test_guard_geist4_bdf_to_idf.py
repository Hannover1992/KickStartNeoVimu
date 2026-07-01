"""
pytest tests fuer guard_geist4_bdf_to_idf.py (Geist G#4 BDF -> IDF).

6 Test-Cases:
  1. READY-BL                      -> continue:true
  2. SC-REIF-BL                    -> continue:true
  3. UNREIF-BL                     -> continue:false (enforce) "A-Pipeline zuerst"
  4. DONE-BL                       -> continue:false (enforce) "BL terminal"
  5. --pl-only ohne Vault-Folder   -> continue:false (enforce) "Vault-Folder"
  6. Andere Skills passthrough     -> continue:true (kein Trigger)

Pattern: test_guard_modus_writer.py.
"""

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_geist4_bdf_to_idf.py"


# ──────────────────────────── Helpers ────────────────────────────

INDEX_HEADER = textwrap.dedent("""\
    ---
    type: backlog-index
    ---

    | BL-ID | Title | Status | Vault-Pfad | Created | Updated | Spec-Link | Reifegrad |
    |-------|-------|--------|------------|---------|---------|-----------|-----------|
""")


def _index_row(bl_id: str, title: str, status: str, vault_path: str) -> str:
    return (
        f"| BL-{bl_id} | {title} | {status} | {vault_path} "
        f"| 2026-05-27 | 2026-05-27 | null | REIF |\n"
    )


def _write_index(tmp_path: Path, rows: list[str]) -> Path:
    idx = tmp_path / "_backlog_index.md"
    idx.write_text(INDEX_HEADER + "".join(rows), encoding="utf-8")
    return idx


def run_guard(
    skill: str,
    args: str = "",
    *,
    index_file: Path | None = None,
    session_params_file: Path | None = None,
    enforce: bool = True,
    tool_name: str = "Skill",
) -> dict:
    """Ruft guard_geist4_bdf_to_idf.py mit simuliertem Hook-Input auf.

    OMNI_ENFORCE_GEIST4_GUARD=1 erzwingt enforce=true.
    OMNI_GEIST4_BACKLOG_INDEX zeigt auf eine Test-Index-Datei.
    OMNI_GEIST4_SESSION_PARAMS zeigt auf eine Test-Session-Params-Datei.
    """
    tool_input: dict = {}
    if tool_name == "Skill":
        tool_input = {"skill": skill, "args": args}
    elif tool_name in ("Edit", "Write"):
        tool_input = {"file_path": skill, "new_string": args}

    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    env = os.environ.copy()
    if enforce:
        env["OMNI_ENFORCE_GEIST4_GUARD"] = "1"
    else:
        env.pop("OMNI_ENFORCE_GEIST4_GUARD", None)
    if index_file is not None:
        env["OMNI_GEIST4_BACKLOG_INDEX"] = str(index_file)
    if session_params_file is not None:
        env["OMNI_GEIST4_SESSION_PARAMS"] = str(session_params_file)

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


def _write_session_params(tmp_path: Path, enforce: bool) -> Path:
    """Schreibt ein Test-_session_params.md mit gewuenschtem enforceProcess-Wert."""
    sp = tmp_path / "_session_params.md"
    sp.write_text(
        f"# Session Params (Test)\n\n"
        f"**enforceProcess:** {'true' if enforce else 'false'}  _owner: test\n",
        encoding="utf-8",
    )
    return sp


# ──────────────────────────── Tests ────────────────────────────


def test_ready_bl_passes(tmp_path):
    """BL mit Status=READY -> continue=true."""
    vault_md = tmp_path / "BL-300-some-feature.md"
    vault_md.write_text("# BL-300\n", encoding="utf-8")
    idx = _write_index(
        tmp_path, [_index_row("300", "SomeFeature", "READY", str(vault_md))]
    )
    result = run_guard(
        skill="_IDF_orchestrate",
        args="BL-300 --resume",
        index_file=idx,
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_sc_reif_bl_passes(tmp_path):
    """BL mit Status=SC-REIF -> continue=true."""
    vault_md = tmp_path / "BL-301-other.md"
    vault_md.write_text("# BL-301\n", encoding="utf-8")
    idx = _write_index(
        tmp_path, [_index_row("301", "OtherFeature", "SC-REIF", str(vault_md))]
    )
    result = run_guard(
        skill="_IDF_orchestrate",
        args="BL-301",
        index_file=idx,
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_unreif_bl_blocks_with_a_pipeline_hint(tmp_path):
    """BL mit Status=UNREIF -> continue=false (enforce) mit Begruendung A-Pipeline."""
    vault_md = tmp_path / "BL-302-unreif.md"
    vault_md.write_text("# BL-302\n", encoding="utf-8")
    idx = _write_index(
        tmp_path, [_index_row("302", "Unreif", "UNREIF", str(vault_md))]
    )
    result = run_guard(
        skill="_IDF_orchestrate",
        args="BL-302",
        index_file=idx,
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    msg = result.get("message", "")
    assert "A-Pipeline" in msg, f"Expected A-Pipeline hint, got: {msg}"
    assert "BL-302" in msg


def test_done_bl_blocks_as_terminal(tmp_path):
    """BL mit Status=DONE -> continue=false (enforce) mit Begruendung terminal."""
    vault_md = tmp_path / "BL-303-done.md"
    vault_md.write_text("# BL-303\n", encoding="utf-8")
    idx = _write_index(
        tmp_path, [_index_row("303", "Done", "DONE", str(vault_md))]
    )
    result = run_guard(
        skill="_IDF_orchestrate",
        args="BL-303",
        index_file=idx,
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    msg = result.get("message", "")
    assert "terminal" in msg.lower(), f"Expected 'terminal' in message, got: {msg}"
    assert "BL-303" in msg


def test_pl_only_without_vault_folder_blocks(tmp_path):
    """BL=READY aber --pl-only --from=sdf_finish ohne Vault-Folder -> Block."""
    # Vault-Pfad zeigt auf .md, aber Sibling-Folder existiert NICHT
    vault_md = tmp_path / "BL-304-feature.md"
    vault_md.write_text("# BL-304\n", encoding="utf-8")
    # Bewusst KEIN tmp_path/"BL-304-feature/" anlegen
    idx = _write_index(
        tmp_path, [_index_row("304", "Feature", "READY", str(vault_md))]
    )
    result = run_guard(
        skill="_IDF_orchestrate",
        args="BL-304 --pl-only --from=sdf_finish",
        index_file=idx,
    )
    assert result["continue"] is False, f"Expected block, got: {result}"
    msg = result.get("message", "")
    assert "Vault-Folder" in msg or "vault-folder" in msg.lower(), (
        f"Expected Vault-Folder hint, got: {msg}"
    )


def test_pl_only_with_vault_folder_passes(tmp_path):
    """BL=READY mit --pl-only --from=sdf_finish UND existierendem Vault-Folder -> pass."""
    vault_md = tmp_path / "BL-305-feature.md"
    vault_md.write_text("# BL-305\n", encoding="utf-8")
    # Sibling-Folder anlegen
    folder = tmp_path / "BL-305-feature"
    folder.mkdir()
    idx = _write_index(
        tmp_path, [_index_row("305", "Feature", "READY", str(vault_md))]
    )
    result = run_guard(
        skill="_IDF_orchestrate",
        args="BL-305 --pl-only --from=sdf_finish",
        index_file=idx,
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"


def test_other_skill_passthrough(tmp_path):
    """Skill(_BDF_orchestrate) -> kein Trigger fuer Geist G#4 -> continue=true."""
    idx = _write_index(
        tmp_path,
        [_index_row("306", "Doesnt", "UNREIF", str(tmp_path / "BL-306.md"))],
    )
    result = run_guard(
        skill="_BDF_orchestrate",
        args="BL-306",
        index_file=idx,
    )
    assert result["continue"] is True, f"Expected passthrough, got: {result}"


def test_non_skill_tool_passthrough(tmp_path):
    """Edit-Tool (nicht Skill) -> Hook reagiert nicht -> continue=true."""
    idx = _write_index(
        tmp_path,
        [_index_row("307", "Edit", "UNREIF", str(tmp_path / "BL-307.md"))],
    )
    result = run_guard(
        skill="/some/path/_manifest.md",
        args="modus: M2",
        index_file=idx,
        tool_name="Edit",
    )
    assert result["continue"] is True, f"Expected passthrough, got: {result}"


def test_warn_mode_does_not_block(tmp_path):
    """enforce=false (WARN-Mode via _session_params.md) -> selbst bei UNREIF continue=true."""
    vault_md = tmp_path / "BL-308-warn.md"
    vault_md.write_text("# BL-308\n", encoding="utf-8")
    idx = _write_index(
        tmp_path, [_index_row("308", "Warn", "UNREIF", str(vault_md))]
    )
    sp = _write_session_params(tmp_path, enforce=False)
    result = run_guard(
        skill="_IDF_orchestrate",
        args="BL-308",
        index_file=idx,
        session_params_file=sp,
        enforce=False,
    )
    assert result["continue"] is True, f"WARN-Mode should not block: {result}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
