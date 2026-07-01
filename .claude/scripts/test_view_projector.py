#!/usr/bin/env python3
"""RED-phase tests for view_projector.py (BL-478 STERN-P4).

AK FIXTURE FORMAT NOTE (for GREEN implementer):
  Spec files use HEADING format: lines beginning with `### AK-N: <title>`
  e.g.:  ### AK-1: First criterion title
  GREEN must parse `### AK-N:` heading lines (### + space + AK- prefix).
  Item ids rendered as `BL-{nn}-AK-{N}` in the parking-lot content.

Module view_projector.py does NOT exist yet — all tests fail with ImportError (RED).
"""
from __future__ import annotations

import sys
import os

# Ensure .claude/scripts/ is on sys.path so import resolution works once GREEN exists.
sys.path.insert(0, os.path.dirname(__file__))

import pytest

from view_projector import parse_view_identity, gather_substrate, project_view  # noqa: E402 — RED: ImportError expected


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _make_rich_bl(tmp_path):
    """Build BL-100-x with 2 AKs in 3_Spec and 2 truth-atoms in 2_Model/truths."""
    bl_dir = tmp_path / "Backlog" / "BL-100-x"
    spec_dir = bl_dir / "3_Spec"
    spec_dir.mkdir(parents=True)

    # Spec with 2 AKs — HEADING format: ### AK-N: <title>
    spec_content = """\
---
type: spec
bl-item: BL-100
---

# BL-100 Spec

### AK-1: First criterion title

Description of the first acceptance criterion.

### AK-2: Second criterion title

Description of the second acceptance criterion.
"""
    (spec_dir / "BL-100-x_Spec.md").write_text(spec_content, encoding="utf-8")

    # Truth atoms in 2_Model/truths/
    atoms_dir = bl_dir / "2_Model" / "truths"
    atoms_dir.mkdir(parents=True)

    atom1 = """\
---
id: BL-100-x.W1
type: truth
---

First truth statement.
"""
    atom2 = """\
---
id: BL-100-x.W2
type: truth
---

Second truth statement.
"""
    (atoms_dir / "W1.md").write_text(atom1, encoding="utf-8")
    (atoms_dir / "W2.md").write_text(atom2, encoding="utf-8")

    # Corrupt parking view (null bytes)
    pl_dir = bl_dir / "6_PL"
    pl_dir.mkdir(parents=True)
    pl_path = pl_dir / "BL-100-x-parking-lot.md"
    pl_path.write_bytes(b"\x00" * 30)

    return pl_path


def _make_barren_bl(tmp_path):
    """Build BL-200-y with NO spec and NO atoms — just a node file with no parseable AKs."""
    bl_dir = tmp_path / "Backlog" / "BL-200-y"
    bl_dir.mkdir(parents=True)

    # Node file — no AK headings
    node = tmp_path / "Backlog" / "BL-200-y.md"
    node.write_text("---\ntype: node\nbl-item: BL-200\n---\n\nNo AKs here.\n", encoding="utf-8")

    # Corrupt parking view
    pl_dir = bl_dir / "6_PL"
    pl_dir.mkdir(parents=True)
    pl_path = pl_dir / "BL-200-y-parking-lot.md"
    pl_path.write_bytes(b"\x00" * 30)

    return pl_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_parse_identity_parking(tmp_path):
    """parse_view_identity on BL-100 parking path → bl=='BL-100', view_type=='parking'."""
    pl_path = _make_rich_bl(tmp_path)
    result = parse_view_identity(str(pl_path), str(tmp_path))
    assert result["bl"] == "BL-100", f"Expected bl='BL-100', got {result['bl']!r}"
    assert result["view_type"] == "parking", f"Expected view_type='parking', got {result['view_type']!r}"


def test_gather_substrate_finds_aks_and_atoms(tmp_path):
    """gather_substrate('BL-100', vault) → >=2 aks, ==2 atoms, has_substrate True."""
    _make_rich_bl(tmp_path)
    result = gather_substrate("BL-100", str(tmp_path))
    assert result["has_substrate"] is True, "has_substrate must be True for rich BL"
    assert len(result["aks"]) >= 2, f"Expected >=2 AKs, got {len(result['aks'])}: {result['aks']}"
    assert len(result["atoms"]) == 2, f"Expected 2 atoms, got {len(result['atoms'])}: {result['atoms']}"


def test_gather_substrate_barren_is_empty(tmp_path):
    """gather_substrate('BL-200', vault) → has_substrate False, no aks, no atoms."""
    _make_barren_bl(tmp_path)
    result = gather_substrate("BL-200", str(tmp_path))
    assert result["has_substrate"] is False, "has_substrate must be False for barren BL"
    assert len(result.get("aks", [])) == 0, f"Expected 0 AKs, got {result.get('aks')}"
    assert len(result.get("atoms", [])) == 0, f"Expected 0 atoms, got {result.get('atoms')}"


def test_project_derivable_renders_canonical(tmp_path):
    """project_view(BL-100 parking path, vault) → derivable True + canonical content."""
    pl_path = _make_rich_bl(tmp_path)
    result = project_view(str(pl_path), str(tmp_path))

    assert result["derivable"] is True, f"Expected derivable=True, got {result['derivable']}"
    content = result["content"]
    assert content is not None, "content must not be None when derivable=True"

    # Frontmatter markers
    assert "type: parking_lot" in content, "Missing 'type: parking_lot' in frontmatter"
    assert "reconstructed_from_substrate: true" in content, "Missing 'reconstructed_from_substrate: true'"

    # Structural sections
    assert "## Items" in content, "Missing '## Items' section"
    assert "## Verwandte Wahrheiten" in content, "Missing '## Verwandte Wahrheiten' section"

    # AK item ids — must reference real AK ids (BL-100-AK-N or BL-100-AC-N)
    assert "BL-100-AK" in content or "BL-100-AC" in content, (
        f"No AK/AC item ids referencing BL-100 found in content:\n{content}"
    )

    # Wikilinks to atoms
    assert "[[Backlog/BL-100" in content, (
        f"No wikilinks to BL-100 Backlog entries found in content:\n{content}"
    )


def test_project_never_fabricates_item_count(tmp_path):
    """project_view checkbox count == gather_substrate aks count — no invented items."""
    pl_path = _make_rich_bl(tmp_path)
    substrate = gather_substrate("BL-100", str(tmp_path))
    result = project_view(str(pl_path), str(tmp_path))

    assert result["derivable"] is True
    content = result["content"]
    assert content is not None

    checkbox_lines = [line for line in content.splitlines() if line.strip().startswith("- [ ]")]
    n_aks = len(substrate["aks"])
    assert len(checkbox_lines) == n_aks, (
        f"Fabrication detected: {len(checkbox_lines)} checkbox items vs {n_aks} real AKs. "
        f"Items: {checkbox_lines}"
    )


def test_project_barren_is_loss(tmp_path):
    """project_view(BL-200 parking path, vault) → derivable False, content None, loss_note set."""
    pl_path = _make_barren_bl(tmp_path)
    result = project_view(str(pl_path), str(tmp_path))

    assert result["derivable"] is False, f"Expected derivable=False, got {result['derivable']}"
    assert result["content"] is None, f"Expected content=None, got {result['content']!r}"
    assert result.get("loss_note"), (
        f"Expected non-empty loss_note for accepted loss, got {result.get('loss_note')!r}"
    )
