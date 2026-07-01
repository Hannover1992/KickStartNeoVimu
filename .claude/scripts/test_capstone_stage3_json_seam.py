"""BL-493-FIX RED tests — Capstone Stage-3 JSON seam.

Tests the full seam: keyword_edge_writer --dry-run stdout -> _parse_stage_output
-> StageResult -> _gate_edge_quality.

RED-Worker: test_real_writer_json_feeds_gate_green is currently RED (writer emits
plaintext -> _parse_stage_output returns {} -> max_edges_per_atom=None -> gate False).
The two documentary tests may already be GREEN (they test the capstone side which
already handles JSON correctly).

keyword_edge_writer.py and truth_migration_capstone.py are NOT modified here.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import truth_migration_capstone as cap

SCRIPTS = Path(__file__).parent


# ---------------------------------------------------------------------------
# Fixture: tiny vault with truth atoms (duplicated from test_keyword_edge_dryrun_json)
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
# Documentary test (a): JSON input -> gate GREEN  [likely already GREEN]
# ---------------------------------------------------------------------------

def test_stage3_gate_green_on_writer_json() -> None:
    """Capstone can already parse JSON and gate passes (documents Part-b is working).

    This test should be GREEN before the GREEN-Worker runs — it verifies the
    capstone side of the seam is correct.
    """
    json_str = (
        '{"max_edges_per_atom":15,"edge_count":100,"cap_ok":true,'
        '"dangling_count":0,"dry_run":true}'
    )
    data = cap._parse_stage_output(3, json_str)
    assert isinstance(data, dict), f"_parse_stage_output returned {type(data)}"
    assert data.get("max_edges_per_atom") == 15

    sr = cap.StageResult(
        stage_id=3,
        name="edge_quality_gate",
        status="ok",
        gate_ok=True,
        max_edges_per_atom=data.get("max_edges_per_atom"),
        dangling_count=data.get("dangling_count"),
    )
    assert cap._gate_edge_quality(sr) is True, (
        f"_gate_edge_quality should be True for valid JSON input, got False. sr={sr!r}"
    )


# ---------------------------------------------------------------------------
# Documentary test (b): plaintext input -> gate RED  [likely already GREEN]
# ---------------------------------------------------------------------------

def test_stage3_gate_red_on_plaintext() -> None:
    """Documents the FALSE RED: old plaintext from writer causes gate to fail.

    This test should be GREEN — it documents the existing broken behaviour that
    BL-493-FIX resolves (plaintext -> {} -> max_edges_per_atom=None -> gate False).
    """
    plaintext = "[keyword_edge_writer] vault=x would write=100 edges dry_run=True"
    data = cap._parse_stage_output(3, plaintext)
    assert data == {}, (
        f"_parse_stage_output should return {{}} for plaintext, got {data!r}"
    )

    sr = cap.StageResult(
        stage_id=3,
        name="edge_quality_gate",
        status="ok",
        gate_ok=True,
        max_edges_per_atom=data.get("max_edges_per_atom"),  # None
        dangling_count=data.get("dangling_count"),           # None -> treated as 0
    )
    assert cap._gate_edge_quality(sr) is False, (
        "Expected gate=False for plaintext (max_edges_per_atom=None), but got True. "
        "This would mean the FALSE-RED is no longer reproducible."
    )


# ---------------------------------------------------------------------------
# Real seam test (RED until GREEN-Worker fixes keyword_edge_writer)
# ---------------------------------------------------------------------------

def test_real_writer_json_feeds_gate_green(tiny_vault: Path) -> None:
    """End-to-end seam: real writer subprocess -> capstone parse -> gate True.

    Currently RED: writer emits plaintext -> _parse_stage_output returns {} ->
    max_edges_per_atom=None -> _gate_edge_quality returns False.

    After GREEN-Worker fix: writer emits JSON -> parse succeeds -> gate True.
    """
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPTS / "keyword_edge_writer.py"),
            "--vault", str(tiny_vault),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, (
        f"keyword_edge_writer --dry-run failed (exit {proc.returncode}).\n"
        f"stdout: {proc.stdout!r}\nstderr: {proc.stderr!r}"
    )

    data = cap._parse_stage_output(3, proc.stdout)

    # This assertion will fail (RED) because data={} when writer emits plaintext
    assert data != {}, (
        f"_parse_stage_output returned {{}} — writer stdout is not JSON (RED).\n"
        f"writer stdout={proc.stdout!r}"
    )

    sr = cap.StageResult(
        stage_id=3,
        name="edge_quality_gate",
        status="ok",
        gate_ok=True,
        max_edges_per_atom=data.get("max_edges_per_atom"),
        dangling_count=data.get("dangling_count"),
    )
    gate_result = cap._gate_edge_quality(sr)
    assert gate_result is True, (
        f"_gate_edge_quality returned False (RED). "
        f"max_edges_per_atom={sr.max_edges_per_atom!r}, dangling_count={sr.dangling_count!r}. "
        f"writer stdout={proc.stdout!r}"
    )
