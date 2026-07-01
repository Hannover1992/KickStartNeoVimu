"""
pytest tests fuer guard_stab7_status_drift.py (S#7 Status-Drift Stabilization Hook).

Test-Cases:
  1. Index DONE + Frontmatter DONE -> continue=True (kein Drift)
  2. Index DONE + Frontmatter READY (WARN-Default) -> continue=True mit Message
  3. Index DONE + Frontmatter DONE im strict-mode -> continue=True
  4. Index DONE + Frontmatter READY im strict-mode -> continue=False (BLOCK)
  5. Edit auf andere Datei -> passthrough
  6. Vault-Knoten fehlt -> passthrough konservativ
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_stab7_status_drift.py"


def make_vault(tmp_path: Path, index_rows: list, bl_files: dict) -> Path:
    """Baut Mini-Vault: tmp/Vault/_backlog_index.md + tmp/Vault/Backlog/BL-*.md.

    Args:
        index_rows: Liste von (bl_id_short, title, status) Tupeln
        bl_files: dict {bl_id_short: status} fuer Vault-Knoten-Frontmatter

    Returns:
        Path zum Vault-Root
    """
    vault = tmp_path / "Vault"
    vault.mkdir(parents=True, exist_ok=True)
    backlog = vault / "Backlog"
    backlog.mkdir(parents=True, exist_ok=True)

    # Index
    lines = [
        "---",
        "type: backlog-index",
        "---",
        "",
        "# Backlog Index",
        "",
        "| BL-ID | Title | Status | Vault-Pfad | Created | Updated | Spec-Link | Reifegrad |",
        "|-------|-------|--------|------------|---------|---------|-----------|-----------|",
    ]
    for bl_id, title, status in index_rows:
        lines.append(
            f"| {bl_id} | {title} | {status} | {vault}/Backlog/{bl_id.lower()}-foo.md "
            f"| 2026-05-27 | 2026-05-27 | null | REIF |"
        )
    (vault / "_backlog_index.md").write_text("\n".join(lines), encoding="utf-8")

    # BL-Knoten
    for bl_id, status in bl_files.items():
        fm = (
            "---\n"
            f"id: {bl_id}\n"
            f"title: Foo {bl_id}\n"
            f"status: {status}\n"
            "created: '2026-05-27'\n"
            "---\n\n"
            f"# {bl_id}: Foo\n"
        )
        (backlog / f"{bl_id.lower()}-foo.md").write_text(fm, encoding="utf-8")

    # _session_params.md im Vault-Root mit enforceProcess
    (vault / "_session_params.md").write_text(
        "**enforceProcess:** true  _owner: user\n", encoding="utf-8"
    )
    return vault


def run_guard(
    tool_name: str,
    file_path: str,
    new_content: str,
    vault_root: Path = None,
    strict: bool = False,
    enforce_override: bool = True,
) -> dict:
    """Ruft guard_stab7_status_drift.py mit simuliertem Hook-Input auf.

    Args:
        tool_name: "Edit" oder "Write"
        file_path: Pfad-String fuer tool_input.file_path
        new_content: Edit.new_string oder Write.content
        vault_root: CLAUDE_VAULT_ROOT-Override
        strict: setzt OMNI_STATUS_DRIFT_STRICT=1
        enforce_override: setzt OMNI_ENFORCE_STAB7=1 (default True fuer Tests)
    """
    tool_input = {"file_path": file_path}
    if tool_name == "Write":
        tool_input["content"] = new_content
    else:
        tool_input["new_string"] = new_content

    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    env = os.environ.copy()
    if enforce_override:
        env["OMNI_ENFORCE_STAB7"] = "1"
    else:
        env.pop("OMNI_ENFORCE_STAB7", None)
    if strict:
        env["OMNI_STATUS_DRIFT_STRICT"] = "1"
    else:
        env.pop("OMNI_STATUS_DRIFT_STRICT", None)
    if vault_root is not None:
        env["CLAUDE_VAULT_ROOT"] = str(vault_root)

    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(proc.stdout.strip())


# ───── Test 1: Index DONE + Frontmatter DONE → continue=True ────────────────


def test_index_done_frontmatter_done_passes(tmp_path):
    """Beide Quellen sagen DONE -> kein Drift, continue=True."""
    vault = make_vault(
        tmp_path,
        index_rows=[("BL-001", "Foo", "DONE")],
        bl_files={"BL-001": "DONE"},
    )
    # Edit auf Vault-Knoten mit identischem Status
    result = run_guard(
        tool_name="Edit",
        file_path=str(vault / "Backlog" / "bl-001-foo.md"),
        new_content=(
            "---\n"
            "id: BL-001\n"
            "status: DONE\n"
            "---\n"
        ),
        vault_root=vault,
    )
    assert result["continue"] is True, f"Expected pass, got: {result}"


# ───── Test 2: Index DONE + Frontmatter READY → WARN (continue=True+msg) ────


def test_index_done_frontmatter_ready_warns(tmp_path):
    """Drift im non-strict-Mode: continue=True mit Warn-Message."""
    vault = make_vault(
        tmp_path,
        index_rows=[("BL-001", "Foo", "DONE")],
        bl_files={"BL-001": "DONE"},  # Vault hat DONE, Edit setzt READY
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(vault / "Backlog" / "bl-001-foo.md"),
        new_content=(
            "---\n"
            "id: BL-001\n"
            "status: READY\n"
            "---\n"
        ),
        vault_root=vault,
        strict=False,
    )
    assert result["continue"] is True, f"Expected warn (passthrough), got: {result}"
    assert "STAB7" in result.get("message", ""), f"Expected warn message, got: {result}"


# ───── Test 3: Index DONE + Frontmatter DONE im strict-mode → continue=True ─


def test_consistent_in_strict_mode_passes(tmp_path):
    """Strict-Mode + konsistente Quellen -> continue=True."""
    vault = make_vault(
        tmp_path,
        index_rows=[("BL-002", "Bar", "DONE")],
        bl_files={"BL-002": "DONE"},
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(vault / "Backlog" / "bl-002-foo.md"),
        new_content=(
            "---\n"
            "id: BL-002\n"
            "status: DONE\n"
            "---\n"
        ),
        vault_root=vault,
        strict=True,
    )
    assert result["continue"] is True, f"Expected pass even in strict, got: {result}"


# ───── Test 4: Index DONE + Frontmatter READY im strict-mode → continue=False


def test_drift_in_strict_mode_blocks(tmp_path):
    """Drift im strict-Mode + enforce=true -> continue=False (BLOCK)."""
    vault = make_vault(
        tmp_path,
        index_rows=[("BL-003", "Baz", "DONE")],
        bl_files={"BL-003": "DONE"},  # Vault sagt DONE
    )
    # Edit setzt READY -> Drift vs Index DONE
    result = run_guard(
        tool_name="Edit",
        file_path=str(vault / "Backlog" / "bl-003-foo.md"),
        new_content=(
            "---\n"
            "id: BL-003\n"
            "status: READY\n"
            "---\n"
        ),
        vault_root=vault,
        strict=True,
    )
    assert result["continue"] is False, f"Expected BLOCK in strict mode, got: {result}"
    assert "STAB7" in result.get("message", "")
    assert "BLOCKED" in result.get("message", "")


# ───── Test 5: Edit auf andere Datei → passthrough ──────────────────────────


def test_passes_unrelated_file(tmp_path):
    """Edit auf nicht-Index/nicht-Backlog-Datei -> continue=True (passthrough)."""
    vault = make_vault(
        tmp_path,
        index_rows=[("BL-004", "Qux", "DONE")],
        bl_files={"BL-004": "READY"},  # Drift im Vault, aber Edit ist woanders
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(vault / "some_other_file.md"),
        new_content="status: READY\n",
        vault_root=vault,
        strict=True,
    )
    assert result["continue"] is True, f"Expected passthrough, got: {result}"


# ───── Test 6: BL-Vault-Knoten fehlt → passthrough konservativ ──────────────


def test_passes_when_vault_node_missing(tmp_path):
    """Index-Edit fuer BL ohne Vault-Knoten -> passthrough konservativ."""
    vault = make_vault(
        tmp_path,
        index_rows=[("BL-005", "Missing", "DONE")],
        bl_files={},  # KEIN Vault-Knoten fuer BL-005
    )
    # Edit auf Index-Datei mit Drift-verdaechtigem Status
    new_index_content = (
        "| BL-ID | Title | Status | Vault-Pfad | Created | Updated | Spec-Link | Reifegrad |\n"
        "|-------|-------|--------|------------|---------|---------|-----------|-----------|\n"
        "| BL-005 | Missing | DONE | foo | 2026-05-27 | 2026-05-27 | null | REIF |\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(vault / "_backlog_index.md"),
        new_content=new_index_content,
        vault_root=vault,
        strict=True,
    )
    assert result["continue"] is True, (
        f"Expected passthrough when Vault-Knoten fehlt, got: {result}"
    )


# ───── Bonus Test 7: Index-Edit mit Drift im strict-mode → BLOCK ────────────


def test_index_edit_drift_in_strict_mode_blocks(tmp_path):
    """Index-Edit setzt DONE, aber Vault-Knoten hat READY -> BLOCK in strict."""
    vault = make_vault(
        tmp_path,
        index_rows=[("BL-006", "Drift", "READY")],
        bl_files={"BL-006": "READY"},  # Vault sagt READY
    )
    # Edit auf Index setzt DONE (Drift vs Vault READY)
    new_index_content = (
        "| BL-ID | Title | Status | Vault-Pfad | Created | Updated | Spec-Link | Reifegrad |\n"
        "|-------|-------|--------|------------|---------|---------|-----------|-----------|\n"
        "| BL-006 | Drift | DONE | foo | 2026-05-27 | 2026-05-27 | null | REIF |\n"
    )
    result = run_guard(
        tool_name="Edit",
        file_path=str(vault / "_backlog_index.md"),
        new_content=new_index_content,
        vault_root=vault,
        strict=True,
    )
    assert result["continue"] is False, (
        f"Expected BLOCK on Index-Edit drift in strict, got: {result}"
    )
    assert "STAB7" in result.get("message", "")
