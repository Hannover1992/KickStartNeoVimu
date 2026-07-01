"""
test_view_forward_reference.py — TDD RED for P2 Forward-Garantie (BL-460 Lane-B)

Target module: view_forward_reference.py (does NOT exist yet — all tests MUST FAIL RED).

Interface under test:
    forward_reference_view(
        view_path, vault_root, *,
        atom_index, conf_threshold=0.70,
        write=False, report_path=None
    ) -> dict

Return schema:
    {
        "view":           str  (absolute view_path),
        "proposed_atoms": list[str],  # atom_ids ABOVE threshold (sub_threshold==False)
        "n_proposed":     int,
        "action":         str,  # "dry-run" | "deferred-gated" | "written"
        "reason":         str,
    }

AK coverage:
  AK-DRY    write=False -> action=="dry-run", no writes
  AK-GATE   write=True + is_write_gated==(True,...) -> action=="deferred-gated", no write
  AK-WRITE  write=True + is_write_gated==(False,...) -> delegates to write_source_atoms
  AK-IDEM   second write call -> write_source_atoms returns changed=False -> action=="written", reason notes idempotent
  AK-ABOVE  only sub_threshold==False atoms are in proposed_atoms
  AK-EMPTY  no above-threshold matches -> n_proposed==0, no crash
  AK-NULL   empty/None atom_index -> n_proposed==0, no crash

Mirror conventions from test_referenz_ableiter.py / test_wikilink_materializer_source_atoms.py:
  sys.path.insert, pytest, tmp_path, patch.object / unittest.mock.patch
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Mirror existing convention: insert scripts dir so local imports resolve
sys.path.insert(0, os.path.dirname(__file__))

# M3 test-first: this import FAILS now (module DOES NOT EXIST yet)
# -> ModuleNotFoundError = RED (collection-error counts as FAIL)
from view_forward_reference import forward_reference_view  # noqa: E402  type: ignore[import]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_view(tmp_path: Path, name: str = "test_view.md", content: str = "body text") -> Path:
    """Create a minimal view .md file."""
    p = tmp_path / name
    p.write_text(f"---\ntype: view\nbl: BL-460\n---\n{content}\n", encoding="utf-8")
    return p


def _above(atom_id: str, confidence: float = 0.85) -> dict:
    """Mock score_view result entry ABOVE threshold (sub_threshold=False)."""
    return {"atom_id": atom_id, "confidence": confidence, "sub_threshold": False}


def _below(atom_id: str, confidence: float = 0.50) -> dict:
    """Mock score_view result entry BELOW threshold (sub_threshold=True)."""
    return {"atom_id": atom_id, "confidence": confidence, "sub_threshold": True}


# ---------------------------------------------------------------------------
# AK-DRY: write=False (default) -> dry-run, no vault writes
# ---------------------------------------------------------------------------

class TestDryRun:
    """write=False path: action=='dry-run', proposed_atoms populated, no write."""

    def test_dry_run_action_label(self, tmp_path):
        """T-DRY-1: default write=False -> action=='dry-run'."""
        view = _write_view(tmp_path)
        mock_scores = [_above("ATOM-001"), _above("ATOM-002"), _below("ATOM-003")]

        with patch("view_forward_reference.score_view", return_value=mock_scores) as _sv, \
             patch("view_forward_reference.write_source_atoms") as mock_wsa, \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=False
            )

        assert result["action"] == "dry-run"
        mock_wsa.assert_not_called()

    def test_dry_run_proposed_atoms_above_threshold_only(self, tmp_path):
        """T-DRY-2: proposed_atoms contains only sub_threshold==False atom_ids."""
        view = _write_view(tmp_path)
        mock_scores = [_above("ATOM-A"), _below("ATOM-B"), _above("ATOM-C")]

        with patch("view_forward_reference.score_view", return_value=mock_scores), \
             patch("view_forward_reference.write_source_atoms"), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=False
            )

        assert set(result["proposed_atoms"]) == {"ATOM-A", "ATOM-C"}
        assert "ATOM-B" not in result["proposed_atoms"]

    def test_dry_run_n_proposed_matches_proposed_atoms(self, tmp_path):
        """T-DRY-3: n_proposed == len(proposed_atoms)."""
        view = _write_view(tmp_path)
        mock_scores = [_above("A-1"), _above("A-2"), _below("B-1")]

        with patch("view_forward_reference.score_view", return_value=mock_scores), \
             patch("view_forward_reference.write_source_atoms"), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=False
            )

        assert result["n_proposed"] == 2
        assert result["n_proposed"] == len(result["proposed_atoms"])

    def test_dry_run_view_field_is_absolute_path(self, tmp_path):
        """T-DRY-4: result['view'] is the absolute view_path string."""
        view = _write_view(tmp_path)
        mock_scores = [_above("ATOM-X")]

        with patch("view_forward_reference.score_view", return_value=mock_scores), \
             patch("view_forward_reference.write_source_atoms"), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=False
            )

        assert result["view"] == str(view)

    def test_dry_run_no_mtime_change(self, tmp_path):
        """T-DRY-5: write=False must NOT alter view file mtime."""
        view = _write_view(tmp_path)
        mtime_before = view.stat().st_mtime
        mock_scores = [_above("ATOM-Y")]

        with patch("view_forward_reference.score_view", return_value=mock_scores), \
             patch("view_forward_reference.write_source_atoms"), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=False
            )

        assert view.stat().st_mtime == mtime_before


# ---------------------------------------------------------------------------
# AK-GATE: write=True + is_write_gated==(True,...) -> deferred-gated, NO write
# ---------------------------------------------------------------------------

class TestWriteGated:
    """write=True but vault gated -> action=='deferred-gated', no actual write."""

    def test_gated_action_label(self, tmp_path):
        """T-GATE-1: gated vault -> action=='deferred-gated'."""
        view = _write_view(tmp_path)
        gate_reason = "3 corrupt nodes found — write gated (BL-443 open)"

        with patch("view_forward_reference.score_view", return_value=[_above("ATOM-G1")]), \
             patch("view_forward_reference.is_write_gated", return_value=(True, gate_reason)) as mock_gate, \
             patch("view_forward_reference.write_source_atoms") as mock_wsa:

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        assert result["action"] == "deferred-gated"
        mock_wsa.assert_not_called()

    def test_gated_reason_names_gate(self, tmp_path):
        """T-GATE-2: reason field names the BL-443 gate reason."""
        view = _write_view(tmp_path)
        gate_reason = "5 corrupt nodes found — write gated (BL-443 open)"

        with patch("view_forward_reference.score_view", return_value=[_above("ATOM-G2")]), \
             patch("view_forward_reference.is_write_gated", return_value=(True, gate_reason)), \
             patch("view_forward_reference.write_source_atoms"):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        # reason must reference the gate message in some form
        assert gate_reason in result["reason"] or "BL-443" in result["reason"] or "gated" in result["reason"]

    def test_gated_proposed_atoms_still_populated(self, tmp_path):
        """T-GATE-3: even when gated, proposed_atoms shows what WOULD have been written."""
        view = _write_view(tmp_path)
        mock_scores = [_above("ATOM-G3"), _below("ATOM-G4")]

        with patch("view_forward_reference.score_view", return_value=mock_scores), \
             patch("view_forward_reference.is_write_gated", return_value=(True, "gated")), \
             patch("view_forward_reference.write_source_atoms"):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        assert result["proposed_atoms"] == ["ATOM-G3"]
        assert result["n_proposed"] == 1

    def test_gated_no_mtime_change(self, tmp_path):
        """T-GATE-4: gated write must NOT alter view file mtime."""
        view = _write_view(tmp_path)
        mtime_before = view.stat().st_mtime

        with patch("view_forward_reference.score_view", return_value=[_above("ATOM-G5")]), \
             patch("view_forward_reference.is_write_gated", return_value=(True, "gated")), \
             patch("view_forward_reference.write_source_atoms"):

            forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        assert view.stat().st_mtime == mtime_before


# ---------------------------------------------------------------------------
# AK-WRITE: write=True + vault clean -> delegates to write_source_atoms
# ---------------------------------------------------------------------------

class TestWriteClean:
    """write=True + vault clean -> action=='written', write_source_atoms called."""

    def test_write_action_label(self, tmp_path):
        """T-WRITE-1: clean vault + write=True -> action=='written'."""
        view = _write_view(tmp_path)

        with patch("view_forward_reference.score_view", return_value=[_above("ATOM-W1")]), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")), \
             patch("view_forward_reference.write_source_atoms", return_value=(True, "written")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        assert result["action"] == "written"

    def test_write_delegates_above_threshold_only(self, tmp_path):
        """T-WRITE-2: write_source_atoms receives only above-threshold atom_ids."""
        view = _write_view(tmp_path)
        mock_scores = [_above("ATOM-W2"), _below("ATOM-W3"), _above("ATOM-W4")]

        with patch("view_forward_reference.score_view", return_value=mock_scores), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")), \
             patch("view_forward_reference.write_source_atoms", return_value=(True, "written")) as mock_wsa:

            forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        call_atom_ids = mock_wsa.call_args[0][1]  # positional arg 2
        assert set(call_atom_ids) == {"ATOM-W2", "ATOM-W4"}
        assert "ATOM-W3" not in call_atom_ids

    def test_write_passes_vault_root(self, tmp_path):
        """T-WRITE-3: write_source_atoms receives the correct vault_root."""
        view = _write_view(tmp_path)

        with patch("view_forward_reference.score_view", return_value=[_above("ATOM-W5")]), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")), \
             patch("view_forward_reference.write_source_atoms", return_value=(True, "written")) as mock_wsa:

            forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        # vault_root should be passed (positional arg index 2 or keyword)
        args = mock_wsa.call_args
        # either positional arg[2] or kwarg vault_root
        passed_vault = args[0][2] if len(args[0]) > 2 else args[1].get("vault_root")
        assert str(passed_vault) == str(tmp_path)


# ---------------------------------------------------------------------------
# AK-IDEM: idempotent — second write -> changed=False -> reason notes no-change
# ---------------------------------------------------------------------------

class TestIdempotency:
    """Second write call with same atoms -> write_source_atoms returns changed=False."""

    def test_idempotent_action_still_written(self, tmp_path):
        """T-IDEM-1: second call -> action=='written' even when changed=False."""
        view = _write_view(tmp_path)

        with patch("view_forward_reference.score_view", return_value=[_above("ATOM-I1")]), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")), \
             patch("view_forward_reference.write_source_atoms", return_value=(False, "already_present")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        assert result["action"] == "written"

    def test_idempotent_reason_notes_no_change(self, tmp_path):
        """T-IDEM-2: when changed=False, reason mentions idempotent/no-change/already_present."""
        view = _write_view(tmp_path)

        with patch("view_forward_reference.score_view", return_value=[_above("ATOM-I2")]), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")), \
             patch("view_forward_reference.write_source_atoms", return_value=(False, "already_present")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        reason_lower = result["reason"].lower()
        assert any(kw in reason_lower for kw in ("idempotent", "no-change", "no_change", "already", "unchanged"))


# ---------------------------------------------------------------------------
# AK-EMPTY: no above-threshold matches -> n_proposed==0, no crash
# ---------------------------------------------------------------------------

class TestNoAboveThreshold:
    """All score_view results are sub_threshold -> proposed_atoms empty, no crash."""

    def test_all_below_threshold_dry_run(self, tmp_path):
        """T-EMPTY-1: all sub_threshold=True -> n_proposed==0, action=='dry-run'."""
        view = _write_view(tmp_path)
        mock_scores = [_below("ATOM-E1"), _below("ATOM-E2")]

        with patch("view_forward_reference.score_view", return_value=mock_scores), \
             patch("view_forward_reference.write_source_atoms"), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=False
            )

        assert result["n_proposed"] == 0
        assert result["proposed_atoms"] == []
        assert result["action"] == "dry-run"

    def test_all_below_threshold_write(self, tmp_path):
        """T-EMPTY-2: write=True + no above-threshold -> n_proposed==0, action=='written', no crash."""
        view = _write_view(tmp_path)
        mock_scores = [_below("ATOM-E3")]

        with patch("view_forward_reference.score_view", return_value=mock_scores), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")), \
             patch("view_forward_reference.write_source_atoms", return_value=(False, "nothing_to_write")) as mock_wsa:

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        assert result["n_proposed"] == 0
        # write_source_atoms called with empty list (or not called at all — both valid; no crash is load-bearing)
        assert result["action"] in ("written", "dry-run")  # no crash is the contract

    def test_empty_score_view_result(self, tmp_path):
        """T-EMPTY-3: score_view returns [] -> n_proposed==0, no crash."""
        view = _write_view(tmp_path)

        with patch("view_forward_reference.score_view", return_value=[]), \
             patch("view_forward_reference.write_source_atoms"), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=False
            )

        assert result["n_proposed"] == 0
        assert result["proposed_atoms"] == []


# ---------------------------------------------------------------------------
# AK-NULL: empty/None atom_index -> n_proposed==0, no crash
# ---------------------------------------------------------------------------

class TestNullAtomIndex:
    """Robust with empty or None atom_index."""

    def test_empty_dict_atom_index(self, tmp_path):
        """T-NULL-1: atom_index={} -> no crash, n_proposed==0."""
        view = _write_view(tmp_path)

        with patch("view_forward_reference.score_view", return_value=[]), \
             patch("view_forward_reference.write_source_atoms"), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=False
            )

        assert result["n_proposed"] == 0

    def test_none_atom_index(self, tmp_path):
        """T-NULL-2: atom_index=None -> no crash, n_proposed==0."""
        view = _write_view(tmp_path)

        with patch("view_forward_reference.score_view", return_value=[]), \
             patch("view_forward_reference.write_source_atoms"), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index=None, write=False
            )

        assert result["n_proposed"] == 0


# ---------------------------------------------------------------------------
# AK-ABOVE: filtering assertion — sub_threshold==False IS included, ==True is NOT
# ---------------------------------------------------------------------------

class TestAboveThresholdFiltering:
    """Core AK-CTX-2 hairball-prevention: only sub_threshold==False in proposed_atoms."""

    def test_mixed_scores_only_above_in_proposed(self, tmp_path):
        """T-ABOVE-1: mixed above/below -> only above in proposed_atoms."""
        view = _write_view(tmp_path)
        mock_scores = [
            _above("ABOVE-1", 0.95),
            _below("BELOW-1", 0.40),
            _above("ABOVE-2", 0.80),
            _below("BELOW-2", 0.65),  # close but still sub_threshold
        ]

        with patch("view_forward_reference.score_view", return_value=mock_scores), \
             patch("view_forward_reference.write_source_atoms"), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=False
            )

        assert "ABOVE-1" in result["proposed_atoms"]
        assert "ABOVE-2" in result["proposed_atoms"]
        assert "BELOW-1" not in result["proposed_atoms"]
        assert "BELOW-2" not in result["proposed_atoms"]
        assert result["n_proposed"] == 2

    def test_sub_threshold_flag_is_authoritative(self, tmp_path):
        """T-ABOVE-2: sub_threshold field on score entry is the ONLY filter criterion (not confidence re-check)."""
        view = _write_view(tmp_path)
        # atom has high confidence but sub_threshold=True (edge case: caller decided)
        mock_scores = [
            {"atom_id": "EDGE-1", "confidence": 0.99, "sub_threshold": True},
            {"atom_id": "EDGE-2", "confidence": 0.71, "sub_threshold": False},
        ]

        with patch("view_forward_reference.score_view", return_value=mock_scores), \
             patch("view_forward_reference.write_source_atoms"), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=False
            )

        assert "EDGE-1" not in result["proposed_atoms"]
        assert "EDGE-2" in result["proposed_atoms"]


# ---------------------------------------------------------------------------
# AK-SCHEMA: result dict always has required keys
# ---------------------------------------------------------------------------

class TestReturnSchema:
    """Result dict always contains all required keys regardless of path."""

    REQUIRED_KEYS = {"view", "proposed_atoms", "n_proposed", "action", "reason"}

    def test_schema_dry_run(self, tmp_path):
        """T-SCHEMA-1: dry-run path returns all required keys."""
        view = _write_view(tmp_path)

        with patch("view_forward_reference.score_view", return_value=[_above("S1")]), \
             patch("view_forward_reference.write_source_atoms"), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=False
            )

        assert self.REQUIRED_KEYS.issubset(result.keys())

    def test_schema_gated(self, tmp_path):
        """T-SCHEMA-2: gated path returns all required keys."""
        view = _write_view(tmp_path)

        with patch("view_forward_reference.score_view", return_value=[_above("S2")]), \
             patch("view_forward_reference.is_write_gated", return_value=(True, "gated")), \
             patch("view_forward_reference.write_source_atoms"):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        assert self.REQUIRED_KEYS.issubset(result.keys())

    def test_schema_written(self, tmp_path):
        """T-SCHEMA-3: written path returns all required keys."""
        view = _write_view(tmp_path)

        with patch("view_forward_reference.score_view", return_value=[_above("S3")]), \
             patch("view_forward_reference.is_write_gated", return_value=(False, "clean")), \
             patch("view_forward_reference.write_source_atoms", return_value=(True, "written")):

            result = forward_reference_view(
                str(view), str(tmp_path), atom_index={}, write=True
            )

        assert self.REQUIRED_KEYS.issubset(result.keys())
