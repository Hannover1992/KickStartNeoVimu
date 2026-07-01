"""
test_view_node_model_locations.py — RED-phase TDD (BL-460 extension).

Tests for is_view_node covering alternate Model-view locations that are
currently MISSING from the predicate:
  - Backlog/<bl>/Model/<name>_Model.md  (legacy Model/ folder, depth 4)
  - Models/<name>_Model.md             (vault-top Models/ dir, depth 2)
  - <name>_Model.md at vault root      (depth 1)

The 3 INCLUDE tests MUST FAIL against current code (genuine RED).
EXCLUDE + REGRESSION groups pin existing behaviour and should PASS already.
"""

from __future__ import annotations

import os
import sys

# Ensure the scripts directory is on sys.path so the import works regardless
# of how pytest is invoked.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pytest
from view_node_predicate import is_view_node


def _make(tmp_path, rel_path: str, content: str = "# placeholder\n") -> tuple[str, str]:
    """Create a file at vault_root/rel_path and return (abs_file_path, vault_root)."""
    vault = tmp_path
    target = vault / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return str(target), str(vault)


# ---------------------------------------------------------------------------
# INCLUDE group — currently return False, MUST FAIL in RED phase
# ---------------------------------------------------------------------------

def test_include_vault_top_models_dir(tmp_path):
    """Models/<name>_Model.md — vault-top Models/ directory (depth 2)."""
    file_path, vault = _make(
        tmp_path,
        "Models/OmniCommand_SprintMonitor_Model.md",
    )
    assert is_view_node(file_path, vault), (
        "Expected is_view_node==True for vault-top Models/<name>_Model.md"
    )


def test_include_vault_root_model(tmp_path):
    """<name>_Model.md at vault root — depth 1."""
    file_path, vault = _make(
        tmp_path,
        "I_MetaPattern_Model.md",
    )
    assert is_view_node(file_path, vault), (
        "Expected is_view_node==True for vault-root <name>_Model.md"
    )


def test_include_legacy_model_folder(tmp_path):
    """Backlog/<bl>/Model/<name>_Model.md — legacy 'Model/' folder (depth 4)."""
    file_path, vault = _make(
        tmp_path,
        "Backlog/BL-041-x/Model/SDF_PostPhase_Migration_Model.md",
    )
    assert is_view_node(file_path, vault), (
        "Expected is_view_node==True for Backlog/<bl>/Model/<name>_Model.md (legacy folder)"
    )


# ---------------------------------------------------------------------------
# EXCLUDE group — must remain False (pin existing + new behaviour)
# ---------------------------------------------------------------------------

def test_exclude_archived_snapshot_deep(tmp_path):
    """Backlog/<bl>/ParkingLot/Snapshot_xxx/2_Model/<name>_Model.md — archived, depth 6."""
    file_path, vault = _make(
        tmp_path,
        "Backlog/BL-151-x/ParkingLot/Snapshot_2026/2_Model/VaultDrivenDevelopment_Model.md",
    )
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for archived snapshot (depth 6)"
    )


def test_exclude_atom_under_legacy_model_folder(tmp_path):
    """Backlog/<bl>/Model/truths/W1.md — atom under legacy Model/, must stay excluded."""
    file_path, vault = _make(
        tmp_path,
        "Backlog/BL-041-x/Model/truths/W1.md",
    )
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for atom under legacy Model/truths/"
    )


def test_exclude_legacy_dir(tmp_path):
    """_legacy/I_MetaPattern_Model.pre_truth.md — legacy dir."""
    file_path, vault = _make(
        tmp_path,
        "_legacy/I_MetaPattern_Model.pre_truth.md",
    )
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for _legacy/ subtree"
    )


def test_exclude_models_readme(tmp_path):
    """Models/README.md — not a *_Model.md, must be False."""
    file_path, vault = _make(
        tmp_path,
        "Models/README.md",
    )
    assert not is_view_node(file_path, vault), (
        "Expected is_view_node==False for Models/README.md (not a model-view)"
    )


# ---------------------------------------------------------------------------
# REGRESSION True — existing patterns must still pass after GREEN
# ---------------------------------------------------------------------------

def test_regression_true_2_model(tmp_path):
    """Backlog/<bl>/2_Model/<name>_Model.md — existing canonical path."""
    file_path, vault = _make(
        tmp_path,
        "Backlog/BL-060-x/2_Model/Foo_Model.md",
    )
    assert is_view_node(file_path, vault), (
        "REGRESSION: Backlog/<bl>/2_Model/<name>_Model.md must remain True"
    )


def test_regression_true_arc42(tmp_path):
    """Backlog/<bl>/arc42/<name>.md — existing canonical path."""
    file_path, vault = _make(
        tmp_path,
        "Backlog/BL-060-x/arc42/01_intro.md",
    )
    assert is_view_node(file_path, vault), (
        "REGRESSION: Backlog/<bl>/arc42/<name>.md must remain True"
    )


def test_regression_true_6_pl(tmp_path):
    """Backlog/<bl>/6_PL/<name>.md — existing canonical path."""
    file_path, vault = _make(
        tmp_path,
        "Backlog/BL-060-x/6_PL/BL-060-x-parking-lot.md",
    )
    assert is_view_node(file_path, vault), (
        "REGRESSION: Backlog/<bl>/6_PL/<name>.md must remain True"
    )


# ---------------------------------------------------------------------------
# REGRESSION False — existing exclusions must still hold after GREEN
# ---------------------------------------------------------------------------

def test_regression_false_truths(tmp_path):
    """Backlog/<bl>/2_Model/truths/W1.md — atom, must remain False."""
    file_path, vault = _make(
        tmp_path,
        "Backlog/BL-060-x/2_Model/truths/W1.md",
    )
    assert not is_view_node(file_path, vault), (
        "REGRESSION: Backlog/<bl>/2_Model/truths/*.md must remain False"
    )


def test_regression_false_manifest(tmp_path):
    """Backlog/<bl>/_manifest.md — must remain False."""
    file_path, vault = _make(
        tmp_path,
        "Backlog/BL-060-x/_manifest.md",
    )
    assert not is_view_node(file_path, vault), (
        "REGRESSION: _manifest.md must remain False"
    )
