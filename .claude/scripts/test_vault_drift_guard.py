"""
test_vault_drift_guard.py — RED tests for vault_drift_guard.py (BL-P3).

Contract under test (module does NOT yet exist → all tests fail with ImportError):
  run_all_drift_checks(
      vault_root,
      *,
      node_health_fn=None,
      index_drift_fn=None,
      manifest_drift_fn=None,
  ) -> dict {
      "corruption":     list,          # from node_health_fn
      "index_drift":    list,          # from index_drift_fn
      "manifest_drift": dict,          # from manifest_drift_fn
      "total_issues":   int,           # len(corruption) + len(index_drift)
                                       # + len(manifest_drift["duplicate_blocks"])
                                       # + len(manifest_drift["split_brain_blocks"])
      "clean":          bool,          # True iff total_issues == 0
  }

  main() — argparse vault_root -> run_all_drift_checks -> report to stdout ->
            exit 0 (clean) or exit 1 (drift found). READ-ONLY, no auto-heal.

Aggregation formula (GREEN contract):
  total_issues = (
      len(corruption)
      + len(index_drift)
      + len(manifest_drift.get("duplicate_blocks", []))
      + len(manifest_drift.get("split_brain_blocks", []))
  )
  clean = (total_issues == 0)
"""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# RED: this import will fail (module does not exist) — proves RED state.
from vault_drift_guard import run_all_drift_checks  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers / stubs
# ---------------------------------------------------------------------------

def _stub_node_health_empty(backlog_dir):
    """Stub: no corruption detected."""
    return []


def _stub_index_drift_empty(vault_root):
    """Stub: no index drift detected."""
    return []


def _stub_manifest_drift_empty(vault_root):
    """Stub: no manifest drift detected."""
    return {"duplicate_blocks": [], "split_brain_blocks": []}


def _stub_node_health_one(backlog_dir):
    """Stub: one corrupted node."""
    return [{"path": "BL-999/BL-999.md", "kind": "NULL_BYTES"}]


def _stub_index_drift_two(vault_root):
    """Stub: two index drifts."""
    return [
        {"bl_id": "BL-001", "index_status": "DONE", "node_status": "OPEN", "kind": "forward"},
        {"bl_id": "BL-002", "index_status": "OPEN", "node_status": "DONE", "kind": "backward"},
    ]


def _stub_manifest_drift_with_issues(vault_root):
    """Stub: one duplicate block, zero split-brain blocks."""
    return {"duplicate_blocks": ["BL-001"], "split_brain_blocks": []}


# ---------------------------------------------------------------------------
# T1: run_all_drift_checks — clean (all stubs return empty)
# ---------------------------------------------------------------------------

class TestRunAllDriftChecksClean:
    """T1: when all 3 DI functions return empty results → clean==True, total_issues==0."""

    def test_clean_true_when_all_detectors_empty(self, tmp_path):
        result = run_all_drift_checks(
            tmp_path,
            node_health_fn=_stub_node_health_empty,
            index_drift_fn=_stub_index_drift_empty,
            manifest_drift_fn=_stub_manifest_drift_empty,
        )
        assert result["clean"] is True

    def test_total_issues_zero_when_all_detectors_empty(self, tmp_path):
        result = run_all_drift_checks(
            tmp_path,
            node_health_fn=_stub_node_health_empty,
            index_drift_fn=_stub_index_drift_empty,
            manifest_drift_fn=_stub_manifest_drift_empty,
        )
        assert result["total_issues"] == 0

    def test_dict_has_all_required_keys_clean(self, tmp_path):
        result = run_all_drift_checks(
            tmp_path,
            node_health_fn=_stub_node_health_empty,
            index_drift_fn=_stub_index_drift_empty,
            manifest_drift_fn=_stub_manifest_drift_empty,
        )
        assert set(result.keys()) >= {
            "corruption", "index_drift", "manifest_drift", "total_issues", "clean"
        }

    def test_corruption_list_empty(self, tmp_path):
        result = run_all_drift_checks(
            tmp_path,
            node_health_fn=_stub_node_health_empty,
            index_drift_fn=_stub_index_drift_empty,
            manifest_drift_fn=_stub_manifest_drift_empty,
        )
        assert result["corruption"] == []

    def test_index_drift_list_empty(self, tmp_path):
        result = run_all_drift_checks(
            tmp_path,
            node_health_fn=_stub_node_health_empty,
            index_drift_fn=_stub_index_drift_empty,
            manifest_drift_fn=_stub_manifest_drift_empty,
        )
        assert result["index_drift"] == []


# ---------------------------------------------------------------------------
# T2: run_all_drift_checks — with drift (3 stubs return data)
# ---------------------------------------------------------------------------

class TestRunAllDriftChecksWithDrift:
    """T2: node_health→1, index_drift→2, manifest_drift→{dup:["X"],split:[]}
    → clean==False, total_issues==4 (1+2+1+0), all categories present."""

    def _call(self, tmp_path):
        return run_all_drift_checks(
            tmp_path,
            node_health_fn=_stub_node_health_one,
            index_drift_fn=_stub_index_drift_two,
            manifest_drift_fn=_stub_manifest_drift_with_issues,
        )

    def test_clean_false_when_drift(self, tmp_path):
        result = self._call(tmp_path)
        assert result["clean"] is False

    def test_total_issues_equals_four(self, tmp_path):
        """1 corruption + 2 index drifts + 1 duplicate_block + 0 split_brain = 4."""
        result = self._call(tmp_path)
        assert result["total_issues"] == 4

    def test_corruption_category_populated(self, tmp_path):
        result = self._call(tmp_path)
        assert len(result["corruption"]) == 1

    def test_index_drift_category_populated(self, tmp_path):
        result = self._call(tmp_path)
        assert len(result["index_drift"]) == 2

    def test_manifest_drift_category_populated(self, tmp_path):
        result = self._call(tmp_path)
        md = result["manifest_drift"]
        assert "duplicate_blocks" in md
        assert len(md["duplicate_blocks"]) == 1

    def test_aggregation_formula_correctness(self, tmp_path):
        """Verify formula: total = corruption + index + dup_blocks + split_blocks."""
        result = self._call(tmp_path)
        md = result["manifest_drift"]
        expected = (
            len(result["corruption"])
            + len(result["index_drift"])
            + len(md.get("duplicate_blocks", []))
            + len(md.get("split_brain_blocks", []))
        )
        assert result["total_issues"] == expected


# ---------------------------------------------------------------------------
# T3: main() smoke — exit code 0 (clean) and 1 (drift)
# ---------------------------------------------------------------------------

class TestMainSmoke:
    """T3: main() returns exit 0 when clean, exit 1 when drift; report contains categories."""

    _scripts_dir = Path(__file__).parent

    def test_main_exit_zero_when_clean(self, tmp_path):
        """main() on an empty vault_root should exit 0 (no real files → detectors get empty)."""
        # We use monkeypatching via env or subprocess with a fixture vault.
        # Strategy: subprocess call with a tmp_path that has no backlog → clean.
        (tmp_path / "Vault" / "Backlog").mkdir(parents=True)
        result = subprocess.run(
            [sys.executable, str(self._scripts_dir / "vault_drift_guard.py"),
             str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Expected exit 0 (clean), got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_main_exit_one_when_drift(self, tmp_path):
        """main() on a vault with a corrupted node should exit 1."""
        # Create a minimal vault structure with a NULL-BYTES node.
        backlog_dir = tmp_path / "Vault" / "Backlog" / "BL-999"
        backlog_dir.mkdir(parents=True)
        corrupt_file = backlog_dir / "BL-999.md"
        corrupt_file.write_bytes(b"\x00\x00\x00")  # NULL bytes → corruption
        result = subprocess.run(
            [sys.executable, str(self._scripts_dir / "vault_drift_guard.py"),
             str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, (
            f"Expected exit 1 (drift), got {result.returncode}.\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_main_report_contains_categories(self, tmp_path):
        """stdout report must mention all 3 categories regardless of drift state."""
        (tmp_path / "Vault" / "Backlog").mkdir(parents=True)
        result = subprocess.run(
            [sys.executable, str(self._scripts_dir / "vault_drift_guard.py"),
             str(tmp_path)],
            capture_output=True,
            text=True,
        )
        # At minimum, report must reference corruption, index_drift, manifest_drift categories
        output = result.stdout.lower()
        assert "corruption" in output, f"'corruption' not in report: {result.stdout}"
        assert "index" in output, f"'index' not in report: {result.stdout}"
        assert "manifest" in output, f"'manifest' not in report: {result.stdout}"
