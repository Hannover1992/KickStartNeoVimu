"""
test_view_ref_sweep.py — RED-phase TDD for view_ref_sweep.drain_pending (BL-460 P2 follow-on)

These tests MUST FAIL until view_ref_sweep.py is created (ImportError = genuine RED).

Contract under test:
    drain_pending(vault_root, *, atom_index=None, report_path=None, gate_mode="target",
                  write=True, scorer=None) -> dict

keys: processed, written, idempotent, deferred, skipped, remaining
"""

from __future__ import annotations

import os
import sys
import json
from pathlib import Path
from unittest.mock import patch

import pytest

# Ensure the scripts dir is on sys.path so imports resolve
sys.path.insert(0, os.path.dirname(__file__))

# This import MUST fail until view_ref_sweep.py is created — that is the RED state.
from view_ref_sweep import drain_pending  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_view_node(vault: Path) -> Path:
    """Create a minimal valid Model view file inside vault_root."""
    bl_dir = vault / "Backlog" / "BL-001-x" / "2_Model"
    bl_dir.mkdir(parents=True, exist_ok=True)
    view = bl_dir / "BL-001-x_Model.md"
    view.write_text("# BL-001-x Model\n\nSome content referencing domain concepts.\n", encoding="utf-8")
    return view


def _make_non_view(vault: Path) -> Path:
    """Create a _manifest.md (excluded by is_view_node)."""
    bl_dir = vault / "Backlog" / "BL-001-x"
    bl_dir.mkdir(parents=True, exist_ok=True)
    manifest = bl_dir / "_manifest.md"
    manifest.write_text("# manifest\n", encoding="utf-8")
    return manifest


def _write_pending(vault: Path, paths: list[str]) -> Path:
    """Write _forward_ref_pending.md with given absolute paths."""
    pending = vault / "_forward_ref_pending.md"
    pending.write_text("\n".join(paths) + "\n", encoding="utf-8")
    return pending


def _read_pending_lines(vault: Path) -> list[str]:
    """Return non-blank lines from _forward_ref_pending.md."""
    pending = vault / "_forward_ref_pending.md"
    if not pending.exists():
        return []
    return [ln for ln in pending.read_text(encoding="utf-8").splitlines() if ln.strip()]


def _score_stub(view_path, vault_root, *, atom_index, conf_threshold=0.70):
    """Deterministic score stub: returns 1 above-threshold atom for any view."""
    return [{"atom_id": "A-1", "confidence": 0.9, "sub_threshold": False}]


def _make_report(tmp_path: Path) -> Path:
    """Create a minimal dry-run JSON report file."""
    report = tmp_path / "report.json"
    report.write_text(json.dumps({"proposed": [], "written": []}), encoding="utf-8")
    return report


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDrainPendingWritesViewNode:
    """test_drains_view_node_writes_and_removes"""

    def test_drains_view_node_writes_and_removes(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        view = _make_view_node(vault)
        report = _make_report(tmp_path)
        _write_pending(vault, [str(view)])

        with patch("view_forward_reference.score_view", side_effect=_score_stub):
            result = drain_pending(
                str(vault),
                gate_mode="target",
                report_path=str(report),
                write=True,
            )

        # Either a real write or idempotent — at least one of them is counted
        assert result["written"] + result["idempotent"] >= 1, (
            f"Expected written+idempotent >= 1, got {result}"
        )
        # The view path must have been removed from the queue
        remaining_lines = _read_pending_lines(vault)
        assert str(view) not in remaining_lines, (
            f"View path still in queue after drain: {remaining_lines}"
        )
        # remaining count must match actual queue length
        assert result["remaining"] == len(remaining_lines), (
            f"result['remaining']={result['remaining']} != actual {len(remaining_lines)}"
        )


class TestSkipsNonViewNode:
    """test_skips_non_view_node_and_removes"""

    def test_skips_non_view_node_and_removes(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        manifest = _make_non_view(vault)
        _write_pending(vault, [str(manifest)])

        with patch("view_forward_reference.score_view", side_effect=_score_stub):
            result = drain_pending(str(vault), write=True)

        assert result["skipped"] >= 1, f"Expected skipped >= 1, got {result}"
        remaining_lines = _read_pending_lines(vault)
        assert str(manifest) not in remaining_lines, (
            f"Non-view path still in queue after drain: {remaining_lines}"
        )


class TestDeferredCorruptTargetKeptInQueue:
    """test_deferred_corrupt_target_kept_in_queue"""

    def test_deferred_corrupt_target_kept_in_queue(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        # Create the view node directory structure but with null-byte content
        bl_dir = vault / "Backlog" / "BL-002-y" / "2_Model"
        bl_dir.mkdir(parents=True, exist_ok=True)
        corrupt_view = bl_dir / "BL-002-y_Model.md"
        corrupt_view.write_bytes(b"\x00" * 40)  # null-byte corrupt

        _write_pending(vault, [str(corrupt_view)])

        with patch("view_forward_reference.score_view", side_effect=_score_stub):
            result = drain_pending(
                str(vault),
                gate_mode="target",
                write=True,
            )

        assert result["deferred"] >= 1, f"Expected deferred >= 1, got {result}"
        # Path MUST remain in the queue (retry on next sweep)
        remaining_lines = _read_pending_lines(vault)
        assert str(corrupt_view) in remaining_lines, (
            f"Corrupt view path was removed but should be kept: {remaining_lines}"
        )


class TestMissingQueueFileGraceful:
    """test_missing_queue_file_graceful"""

    def test_missing_queue_file_graceful(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        # Deliberately do NOT create _forward_ref_pending.md

        result = drain_pending(str(vault), write=True)

        assert result["processed"] == 0, (
            f"Expected processed==0 for missing queue, got {result}"
        )
        # Must return valid summary dict without raising
        for key in ("processed", "written", "idempotent", "deferred", "skipped", "remaining"):
            assert key in result, f"Missing key '{key}' in result: {result}"


class TestDryRunDoesNotMutateQueue:
    """test_dry_run_does_not_mutate_queue"""

    def test_dry_run_does_not_mutate_queue(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        view = _make_view_node(vault)
        _write_pending(vault, [str(view)])

        original_lines = _read_pending_lines(vault)

        with patch("view_forward_reference.score_view", side_effect=_score_stub):
            drain_pending(str(vault), write=False)  # dry-run

        after_lines = _read_pending_lines(vault)
        assert original_lines == after_lines, (
            f"Dry-run mutated the queue.\nBefore: {original_lines}\nAfter: {after_lines}"
        )


class TestIdempotentSecondDrain:
    """test_idempotent_second_drain"""

    def test_idempotent_second_drain(self, tmp_path):
        vault = tmp_path / "vault"
        vault.mkdir()
        view = _make_view_node(vault)
        report = _make_report(tmp_path)
        _write_pending(vault, [str(view)])

        with patch("view_forward_reference.score_view", side_effect=_score_stub):
            first = drain_pending(
                str(vault),
                gate_mode="target",
                report_path=str(report),
                write=True,
            )

        # After first drain, run again — must not raise and processed must reflect
        # only remaining entries (queue may be empty or have deferred items)
        with patch("view_forward_reference.score_view", side_effect=_score_stub):
            second = drain_pending(
                str(vault),
                gate_mode="target",
                report_path=str(report),
                write=True,
            )

        # Second drain must succeed without error
        for key in ("processed", "written", "idempotent", "deferred", "skipped", "remaining"):
            assert key in second, f"Missing key '{key}' in second result: {second}"

        # If first drain emptied the queue, second should process 0
        if first["remaining"] == 0:
            assert second["processed"] == 0, (
                f"Second drain should process 0 when queue is empty, got {second}"
            )
