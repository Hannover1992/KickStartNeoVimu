"""BL-493-FIX RED tests — keyword_edge_writer --dry-run must emit pure JSON.

RED-Worker: these tests FAIL until the GREEN-Worker fixes keyword_edge_writer.py.
keyword_edge_writer.py and truth_migration_capstone.py are NOT modified here.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).parent


# ---------------------------------------------------------------------------
# Fixture: tiny vault with truth atoms
# ---------------------------------------------------------------------------

def _make_truth_vault(tmp_path: Path) -> Path:
    """Create a minimal vault with 3 truth-atom .md files in the Truth folder."""
    vault = tmp_path / "vault"
    truth_dir = vault / "Truth"
    truth_dir.mkdir(parents=True)

    atoms = [
        ("atom-001.md", ["python", "testing"]),
        ("atom-002.md", ["python", "capstone"]),
        ("atom-003.md", ["capstone", "json"]),
    ]
    for filename, keywords in atoms:
        kw_yaml = "\n".join(f"  - {kw}" for kw in keywords)
        content = (
            "---\n"
            f"id: {filename[:-3]}\n"
            "type: truth\n"
            "keywords:\n"
            f"{kw_yaml}\n"
            "---\n"
            "Minimal truth atom for BL-493-FIX RED tests.\n"
        )
        (truth_dir / filename).write_text(content, encoding="utf-8")

    return vault


@pytest.fixture()
def tiny_vault(tmp_path: Path) -> Path:
    return _make_truth_vault(tmp_path)


# ---------------------------------------------------------------------------
# Helper: run the writer exactly as Capstone Stage-3 does
# ---------------------------------------------------------------------------

def _run_dryrun(vault: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPTS / "keyword_edge_writer.py"), "--vault", str(vault), "--dry-run"],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Tests (currently RED — writer emits plaintext, not JSON)
# ---------------------------------------------------------------------------

def test_dryrun_exit_zero(tiny_vault: Path) -> None:
    """The writer must exit 0 in --dry-run mode."""
    proc = _run_dryrun(tiny_vault)
    assert proc.returncode == 0, (
        f"keyword_edge_writer --dry-run exited {proc.returncode}.\n"
        f"stdout: {proc.stdout!r}\nstderr: {proc.stderr!r}"
    )


def test_dryrun_stdout_is_pure_json(tiny_vault: Path) -> None:
    """stdout must be parseable as JSON (currently plaintext -> JSONDecodeError = RED)."""
    proc = _run_dryrun(tiny_vault)
    assert proc.returncode == 0, f"process failed: {proc.stderr!r}"
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"keyword_edge_writer --dry-run stdout is NOT pure JSON (RED).\n"
            f"stdout={proc.stdout!r}\nError: {exc}"
        ) from exc
    assert isinstance(result, dict), f"Expected dict, got {type(result)}: {result!r}"


def test_dryrun_json_has_required_keys(tiny_vault: Path) -> None:
    """JSON output must contain the keys the Capstone gate depends on."""
    proc = _run_dryrun(tiny_vault)
    assert proc.returncode == 0, f"process failed: {proc.stderr!r}"
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Cannot check keys — stdout is not JSON: {proc.stdout!r}"
        ) from exc
    required = {"max_edges_per_atom", "edge_count", "cap_ok", "dry_run"}
    missing = required - result.keys()
    assert not missing, (
        f"Missing required JSON keys: {missing}\nGot: {sorted(result.keys())}"
    )


def test_dryrun_cap_ok_and_max_le_15(tiny_vault: Path) -> None:
    """max_edges_per_atom must be <= 15 and cap_ok must be True."""
    proc = _run_dryrun(tiny_vault)
    assert proc.returncode == 0, f"process failed: {proc.stderr!r}"
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise AssertionError(
            f"Cannot check cap — stdout is not JSON: {proc.stdout!r}"
        ) from exc
    max_edges = result.get("max_edges_per_atom")
    assert max_edges is not None, "max_edges_per_atom missing from JSON output"
    assert max_edges <= 15, f"max_edges_per_atom={max_edges} exceeds BL-455 cap of 15"
    assert result.get("cap_ok") is True, (
        f"cap_ok should be True but got {result.get('cap_ok')!r}"
    )
