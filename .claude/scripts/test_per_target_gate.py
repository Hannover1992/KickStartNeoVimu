"""
test_per_target_gate.py — RED-phase TDD tests for per-target gate_mode param.

BL-460: gate_mode="target" checks only TARGET file for null bytes instead of
doing a vault-wide scan. gate_mode="vault" (default) keeps current behavior.

These tests MUST FAIL against current code because gate_mode param does not
exist yet — TypeError is genuine RED for an additive feature.

The 3 default-mode regression-pin tests (no gate_mode arg) may PASS against
current code — that is expected and correct.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import pytest

# Ensure scripts dir is importable
sys.path.insert(0, os.path.dirname(__file__))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VIEW_FRONTMATTER = """\
---
title: BL-001-x Model
type: view
id: BL-001-x
source_atoms: []
---
"""

_VIEW_BODY = """\
# BL-001-x Model

This view describes the atom corpus keyword overlap for testing.
Relevant: atom score threshold matching corpus scoring.
"""

_VIEW_CONTENT = _VIEW_FRONTMATTER + _VIEW_BODY


def _make_clean_view(tmp_path: Path) -> Path:
    """Create a clean view file at a valid view-node path."""
    view_dir = tmp_path / "Backlog" / "BL-001-x" / "2_Model"
    view_dir.mkdir(parents=True)
    view_file = view_dir / "BL-001-x_Model.md"
    view_file.write_text(_VIEW_CONTENT, encoding="utf-8")
    return view_file


def _make_unrelated_corrupt(tmp_path: Path) -> Path:
    """Create an UNRELATED corrupt file elsewhere in the vault."""
    corrupt_dir = tmp_path / "Backlog" / "BL-002-y" / "6_PL"
    corrupt_dir.mkdir(parents=True)
    corrupt_file = corrupt_dir / "corrupt.md"
    corrupt_file.write_bytes(b"\x00" * 50)
    return corrupt_file


def _make_corrupt_target(tmp_path: Path) -> Path:
    """Create a corrupt TARGET view file (null bytes)."""
    view_dir = tmp_path / "Backlog" / "BL-003-z" / "2_Model"
    view_dir.mkdir(parents=True)
    corrupt_target = view_dir / "BL-003-z_Model.md"
    corrupt_target.write_bytes(b"\x00" * 50)
    return corrupt_target


def _make_dry_run_report(tmp_path: Path, view_path: Path) -> Path:
    """Create a minimal dry-run JSON report so write_source_atoms doesn't block on it."""
    report = {
        "view": str(view_path),
        "proposed_atoms": ["A-1"],
        "n_proposed": 1,
        "action": "dry-run",
        "reason": "1 atoms proposed; no write (dry-run mode)",
    }
    report_path = tmp_path / "dry_run_report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Tests for forward_reference_view
# ---------------------------------------------------------------------------

class TestForwardReferenceViewTargetMode:
    """Tests for gate_mode="target" on forward_reference_view."""

    def test_target_mode_writes_clean_target_despite_unrelated_corruption(
        self, tmp_path, monkeypatch
    ):
        """gate_mode='target' + clean target + unrelated corrupt -> action='written'."""
        from view_forward_reference import forward_reference_view
        import view_forward_reference as vfr_mod

        clean_view = _make_clean_view(tmp_path)
        _make_unrelated_corrupt(tmp_path)

        # Monkeypatch score_view to deterministically propose A-1
        monkeypatch.setattr(
            vfr_mod,
            "score_view",
            lambda *a, **kw: [{"atom_id": "A-1", "confidence": 0.9, "sub_threshold": False}],
        )

        result = forward_reference_view(
            str(clean_view),
            str(tmp_path),
            atom_index={"keyword": []},
            write=True,
            gate_mode="target",  # NEW PARAM — causes TypeError in current code
        )

        assert result["action"] == "written", (
            f"Expected action='written' but got action='{result['action']}'. "
            f"Reason: {result.get('reason')}"
        )

    def test_target_mode_blocks_corrupt_target(self, tmp_path, monkeypatch):
        """gate_mode='target' + corrupt TARGET -> action='deferred-gated'."""
        from view_forward_reference import forward_reference_view
        import view_forward_reference as vfr_mod

        corrupt_target = _make_corrupt_target(tmp_path)

        monkeypatch.setattr(
            vfr_mod,
            "score_view",
            lambda *a, **kw: [{"atom_id": "A-1", "confidence": 0.9, "sub_threshold": False}],
        )

        result = forward_reference_view(
            str(corrupt_target),
            str(tmp_path),
            atom_index={"keyword": []},
            write=True,
            gate_mode="target",  # NEW PARAM — causes TypeError in current code
        )

        assert result["action"] == "deferred-gated", (
            f"Expected action='deferred-gated' but got '{result['action']}'"
        )
        reason = result.get("reason", "")
        assert any(word in reason.lower() for word in ("target", "corrupt", "null", "block", "gated")), (
            f"Reason should mention target/corrupt/null but got: {reason!r}"
        )

    def test_default_vault_mode_blocks_on_unrelated_corruption(
        self, tmp_path, monkeypatch
    ):
        """REGRESSION PIN: default gate_mode ('vault') still blocks on unrelated corruption."""
        from view_forward_reference import forward_reference_view
        import view_forward_reference as vfr_mod

        clean_view = _make_clean_view(tmp_path)
        _make_unrelated_corrupt(tmp_path)

        monkeypatch.setattr(
            vfr_mod,
            "score_view",
            lambda *a, **kw: [{"atom_id": "A-1", "confidence": 0.9, "sub_threshold": False}],
        )

        # Ensure the write-gate enforces (not warn-only)
        monkeypatch.setenv("OMNI_WRITE_GATE_ENFORCE", "1")

        # NO gate_mode arg -> defaults to "vault" -> vault-wide check -> blocked
        result = forward_reference_view(
            str(clean_view),
            str(tmp_path),
            atom_index={"keyword": []},
            write=True,
        )

        assert result["action"] == "deferred-gated", (
            f"Regression: vault-mode should still block on unrelated corruption. "
            f"Got action='{result['action']}', reason={result.get('reason')!r}"
        )


# ---------------------------------------------------------------------------
# Tests for write_source_atoms
# ---------------------------------------------------------------------------

class TestWriteSourceAtomsTargetMode:
    """Tests for gate_mode="target" on write_source_atoms."""

    def test_wsa_target_mode_writes_clean_target_despite_unrelated_corruption(
        self, tmp_path
    ):
        """gate_mode='target' + clean target + unrelated corrupt -> (True, ...)."""
        from wikilink_materializer import write_source_atoms

        clean_view = _make_clean_view(tmp_path)
        _make_unrelated_corrupt(tmp_path)

        # Ensure enforce mode so vault-wide would block if gate_mode not respected
        os.environ["OMNI_WRITE_GATE_ENFORCE"] = "1"
        try:
            result = write_source_atoms(
                clean_view,
                ["A-1"],
                tmp_path,
                gate_mode="target",  # NEW PARAM — causes TypeError in current code
            )
        finally:
            os.environ.pop("OMNI_WRITE_GATE_ENFORCE", None)

        ok, reason = result
        assert ok is True, (
            f"Expected (True, ...) but got (False, {reason!r}). "
            "target-mode should proceed when target itself is clean."
        )
        assert "BLOCKED" not in reason, (
            f"Reason should not contain 'BLOCKED' but got: {reason!r}"
        )

    def test_wsa_target_mode_blocks_corrupt_target(self, tmp_path):
        """gate_mode='target' + corrupt TARGET -> (False, 'BLOCKED: ...')."""
        from wikilink_materializer import write_source_atoms

        corrupt_target = _make_corrupt_target(tmp_path)

        result = write_source_atoms(
            corrupt_target,
            ["A-1"],
            tmp_path,
            gate_mode="target",  # NEW PARAM — causes TypeError in current code
        )

        ok, reason = result
        assert ok is False, (
            f"Expected (False, ...) but got (True, {reason!r}). "
            "target-mode must block when the target file itself is corrupt."
        )
        assert "BLOCKED" in reason, (
            f"Reason should contain 'BLOCKED' but got: {reason!r}"
        )

    def test_wsa_default_vault_mode_blocks_on_unrelated_corruption(self, tmp_path):
        """REGRESSION PIN: default gate_mode ('vault') still blocks on unrelated corruption."""
        from wikilink_materializer import write_source_atoms

        clean_view = _make_clean_view(tmp_path)
        _make_unrelated_corrupt(tmp_path)

        # Ensure enforce mode
        os.environ["OMNI_WRITE_GATE_ENFORCE"] = "1"
        try:
            # NO gate_mode arg -> defaults to "vault" -> vault-wide check -> blocked
            result = write_source_atoms(
                clean_view,
                ["A-1"],
                tmp_path,
                # no gate_mode
            )
        finally:
            os.environ.pop("OMNI_WRITE_GATE_ENFORCE", None)

        ok, reason = result
        assert ok is False, (
            f"Regression: vault-mode should still block. Got (True, {reason!r})"
        )
        assert "BLOCKED" in reason, (
            f"Reason should contain 'BLOCKED' but got: {reason!r}"
        )
