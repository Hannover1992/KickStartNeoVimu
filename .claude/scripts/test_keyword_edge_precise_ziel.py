#!/usr/bin/env python3
"""
test_keyword_edge_precise_ziel.py — BL-451 AC-2a RED tests

Tests for precise edge ziel using atom_id (full id) rather than coarse
bl_id+local_id construction, plus replace_rel semantics in write_edges_to_atom.

These tests are RED against the current implementation:
- compute_keyword_edges uses coarse "bl_id.local_id" (not atom_id)
- write_edges_to_atom has no replace_rel parameter

Run: py -3 -m pytest .claude/scripts/test_keyword_edge_precise_ziel.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent))

from keyword_edge_writer import compute_keyword_edges, write_edges_to_atom

# Try to import _KEYWORD_REL — it is a module-private symbol but tests need it.
try:
    from keyword_edge_writer import _KEYWORD_REL
except ImportError:
    _KEYWORD_REL = "relates_to"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_atom_file(tmp_path: Path, name: str, edges: list[dict]) -> Path:
    """Write a minimal atom .md file with given edges in frontmatter."""
    fm = {"id": name, "local_id": name, "edges": edges}
    fm_text = yaml.dump(fm, allow_unicode=True, default_flow_style=False, sort_keys=False)
    content = f"---\n{fm_text}---\nbody text\n"
    p = tmp_path / f"{name}.md"
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Test 1: precise ziel uses atom_id when available
# ---------------------------------------------------------------------------

def test_precise_ziel_uses_atom_id():
    """When keyword_index target has atom_id, compute_keyword_edges must emit
    that atom_id as ziel — NOT the coarse "bl_id.local_id" fallback."""
    # src atom shares keyword "alpha" with target
    src_atom = {
        "id": "NS-SRC.W1",
        "local_id": "W1",
        "keywords": ["alpha"],
    }
    # Target has atom_id="BL-041-sdf.W3" but bl_id="Backlog" and local_id="W3"
    # Coarse would yield "Backlog.W3" — precise should yield "BL-041-sdf.W3"
    keyword_index = {
        "alpha": [
            {
                "path": "/vault/Backlog/W3.md",
                "bl_id": "Backlog",
                "local_id": "W3",
                "atom_id": "BL-041-sdf.W3",
            }
        ]
    }
    edges = compute_keyword_edges(src_atom, keyword_index, src_namespace="NS-SRC")
    assert edges, "Expected at least one edge"
    ziels = [e["ziel"] for e in edges]
    # Precise: must use atom_id
    assert "BL-041-sdf.W3" in ziels, (
        f"Expected precise ziel 'BL-041-sdf.W3', got: {ziels}"
    )
    # Must NOT use coarse form
    assert "Backlog.W3" not in ziels, (
        f"Got coarse ziel 'Backlog.W3' — atom_id precision NOT applied: {ziels}"
    )


# ---------------------------------------------------------------------------
# Test 2: precise ziel distinguishes collision between two targets
# ---------------------------------------------------------------------------

def test_precise_ziel_distinguishes_collision():
    """Two targets share local_id='W3' but different atom_ids.
    Coarse construction yields "Backlog.W3" for both (collision → dedup to 1).
    Precise construction yields distinct "NSA.W3" and "NSB.W3" (2 edges)."""
    src_atom = {
        "id": "NS-SRC.W99",
        "local_id": "W99",
        "keywords": ["beta"],
    }
    keyword_index = {
        "beta": [
            {
                "path": "/vault/Backlog/a/W3.md",
                "bl_id": "Backlog",
                "local_id": "W3",
                "atom_id": "NSA.W3",
            },
            {
                "path": "/vault/Backlog/b/W3.md",
                "bl_id": "Backlog",
                "local_id": "W3",
                "atom_id": "NSB.W3",
            },
        ]
    }
    edges = compute_keyword_edges(src_atom, keyword_index, src_namespace="NS-SRC")
    ziels = {e["ziel"] for e in edges}
    assert ziels == {"NSA.W3", "NSB.W3"}, (
        f"Expected {{'NSA.W3', 'NSB.W3'}} (collision-distinct), got: {ziels}"
    )


# ---------------------------------------------------------------------------
# Test 3: fallback to coarse when atom_id absent
# ---------------------------------------------------------------------------

def test_precise_ziel_fallback_no_atom_id():
    """When target has no atom_id, fall back to 'bl_id.local_id' (coarse).
    This keeps existing tests green (K-KEW-1 etc)."""
    src_atom = {
        "id": "NS-SRC.W2",
        "local_id": "W2",
        "keywords": ["gamma"],
    }
    keyword_index = {
        "gamma": [
            {
                "path": "/vault/BL-123/atom-002.md",
                "bl_id": "BL-123",
                "local_id": "atom-002",
                # No atom_id key
            }
        ]
    }
    edges = compute_keyword_edges(src_atom, keyword_index, src_namespace="NS-SRC")
    assert edges, "Expected at least one edge for fallback test"
    ziels = [e["ziel"] for e in edges]
    assert "BL-123.atom-002" in ziels, (
        f"Expected coarse fallback ziel 'BL-123.atom-002', got: {ziels}"
    )


# ---------------------------------------------------------------------------
# Test 4: no self-edge when src atom appears in keyword_index via atom_id
# ---------------------------------------------------------------------------

def test_no_self_edge_precise():
    """src_atom id='NS.W1'; keyword_index contains the src atom itself with
    atom_id='NS.W1'. Must NOT emit a self-edge ziel='NS.W1'."""
    src_atom = {
        "id": "NS.W1",
        "local_id": "W1",
        "keywords": ["delta"],
    }
    keyword_index = {
        "delta": [
            # Self-entry — atom_id matches src
            {
                "path": "/vault/NS/W1.md",
                "bl_id": "NS",
                "local_id": "W1",
                "atom_id": "NS.W1",
            },
            # Other target
            {
                "path": "/vault/NS/W2.md",
                "bl_id": "NS",
                "local_id": "W2",
                "atom_id": "NS.W2",
            },
        ]
    }
    edges = compute_keyword_edges(src_atom, keyword_index, src_namespace="NS")
    ziels = [e["ziel"] for e in edges]
    assert "NS.W1" not in ziels, (
        f"Self-edge found: ziel='NS.W1' in {ziels}"
    )


# ---------------------------------------------------------------------------
# Test 5: write_edges_to_atom with replace_rel drops old edges of that rel
# ---------------------------------------------------------------------------

def test_write_replace_rel_drops_old_keyword_edges(tmp_path):
    """write_edges_to_atom(..., replace_rel='relates_to') must:
    - REMOVE existing relates_to edges (coarse Backlog.W3)
    - KEEP unrelated rels (depends_on X.W1)
    - ADD new precise relates_to edge (BL-041.W3)
    """
    atom_path = _make_atom_file(tmp_path, "W5", edges=[
        {"rel": "relates_to", "ziel": "Backlog.W3"},
        {"rel": "depends_on", "ziel": "X.W1"},
    ])

    new_edges = [{"rel": "relates_to", "ziel": "BL-041.W3"}]
    # This call signature is the new API — will raise TypeError in current impl
    written = write_edges_to_atom(atom_path, new_edges, replace_rel="relates_to")

    # Re-read and assert
    content = atom_path.read_text(encoding="utf-8")
    # parse frontmatter
    assert content.startswith("---"), "Expected frontmatter"
    end = content.find("\n---", 3)
    fm = yaml.safe_load(content[4:end]) or {}
    edges = fm.get("edges", [])

    edge_tuples = {(e.get("rel"), e.get("ziel")) for e in edges}

    # Old coarse relates_to must be gone
    assert ("relates_to", "Backlog.W3") not in edge_tuples, (
        f"Old coarse relates_to 'Backlog.W3' was NOT dropped: {edges}"
    )
    # depends_on must survive
    assert ("depends_on", "X.W1") in edge_tuples, (
        f"depends_on edge was lost: {edges}"
    )
    # New precise relates_to must be present
    assert ("relates_to", "BL-041.W3") in edge_tuples, (
        f"New precise relates_to 'BL-041.W3' not found: {edges}"
    )


# ---------------------------------------------------------------------------
# Test 6: write_edges_to_atom with replace_rel is idempotent
# ---------------------------------------------------------------------------

def test_write_replace_rel_idempotent(tmp_path):
    """Calling write_edges_to_atom twice with same new_edges and replace_rel
    must yield identical final state — no duplicate relates_to edges."""
    atom_path = _make_atom_file(tmp_path, "W6", edges=[
        {"rel": "relates_to", "ziel": "Backlog.W3"},
    ])

    new_edges = [{"rel": "relates_to", "ziel": "BL-041.W3"}]

    # First call
    write_edges_to_atom(atom_path, new_edges, replace_rel="relates_to")
    # Second call — idempotent
    write_edges_to_atom(atom_path, new_edges, replace_rel="relates_to")

    content = atom_path.read_text(encoding="utf-8")
    end = content.find("\n---", 3)
    fm = yaml.safe_load(content[4:end]) or {}
    edges = fm.get("edges", [])

    relates_to_edges = [e for e in edges if e.get("rel") == "relates_to"]
    assert len(relates_to_edges) == 1, (
        f"Expected exactly 1 relates_to edge after idempotent double-write, got {len(relates_to_edges)}: {relates_to_edges}"
    )
    assert relates_to_edges[0].get("ziel") == "BL-041.W3", (
        f"relates_to ziel mismatch: {relates_to_edges}"
    )
