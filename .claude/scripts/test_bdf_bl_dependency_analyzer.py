"""
test_bdf_bl_dependency_analyzer.py — Tests for bdf_bl_dependency_analyzer (BL-176 AK-2)

Run with:
    py -3 -m pytest .claude/scripts/test_bdf_bl_dependency_analyzer.py -v
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Ensure the scripts directory is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from bdf_bl_dependency_analyzer import (
    _extract_wikilinks,
    _parse_frontmatter,
    analyze,
    detect_cycles,
    find_orphans,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bl_file(
    backlog_dir: Path,
    bl_id: str,
    status: str = "IN_PROGRESS",
    deps: list[str] | None = None,
    related_bl: str | None = None,
    builds_on: list[str] | None = None,
    body_wikilinks: list[str] | None = None,
    dep_types: dict[str, str] | None = None,
) -> Path:
    """Write a minimal BL markdown file into backlog_dir/<bl_id>/<bl_id>.md."""
    bl_dir = backlog_dir / f"{bl_id}-test"
    bl_dir.mkdir(parents=True, exist_ok=True)
    path = bl_dir / f"{bl_id}_Task.md"

    lines = ["---", f"bl_id: {bl_id}", f"status: {status}"]

    if deps is not None:
        lines.append("dependencies:")
        for d in deps:
            lines.append(f"  - {d}")

    if builds_on is not None:
        lines.append("builds_on:")
        for d in builds_on:
            lines.append(f"  - {d}")

    if related_bl is not None:
        lines.append(f"related_bl: '{related_bl}'")

    if dep_types is not None:
        lines.append("dependency_types:")
        for k, v in dep_types.items():
            lines.append(f"  {k}: {v}")

    lines.append("---")
    lines.append("")
    lines.append("# Task")
    lines.append("")

    if body_wikilinks:
        for wl in body_wikilinks:
            lines.append(f"See [[{wl}]] for details.")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def _vault(tmp_path: Path) -> tuple[Path, Path]:
    """Create minimal vault structure and return (vault_root, backlog_dir)."""
    vault = tmp_path / "OmniCommand"
    backlog = vault / "Backlog"
    backlog.mkdir(parents=True)
    return vault, backlog


# ---------------------------------------------------------------------------
# Test 1: Simple linear chain
# ---------------------------------------------------------------------------

class TestAnalyzeSimpleChain:
    """test_analyze_simple_chain — 3 BLs: BL-001 -> BL-002 -> BL-003"""

    def test_nodes_present(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-001", deps=["BL-002"])
        _make_bl_file(backlog, "BL-002", deps=["BL-003"])
        _make_bl_file(backlog, "BL-003", deps=[])

        result = analyze(vault)
        assert "BL-001" in result["nodes"]
        assert "BL-002" in result["nodes"]
        assert "BL-003" in result["nodes"]

    def test_edges_correct(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-001", deps=["BL-002"])
        _make_bl_file(backlog, "BL-002", deps=["BL-003"])
        _make_bl_file(backlog, "BL-003", deps=[])

        result = analyze(vault)
        edges = [tuple(e) for e in result["edges"]]
        assert ("BL-001", "BL-002") in edges
        assert ("BL-002", "BL-003") in edges

    def test_adjacency_list(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-001", deps=["BL-002"])
        _make_bl_file(backlog, "BL-002", deps=["BL-003"])
        _make_bl_file(backlog, "BL-003", deps=[])

        result = analyze(vault)
        assert result["adjacency"]["BL-001"] == ["BL-002"]
        assert result["adjacency"]["BL-002"] == ["BL-003"]
        assert result["adjacency"]["BL-003"] == []


# ---------------------------------------------------------------------------
# Test 2: Cycle detection
# ---------------------------------------------------------------------------

class TestDetectCycle:
    """test_detect_cycle — 2-node and 3-node cycles"""

    def test_two_node_cycle(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-010", deps=["BL-011"])
        _make_bl_file(backlog, "BL-011", deps=["BL-010"])

        result = analyze(vault)
        cycles = detect_cycles(result)
        assert len(cycles) >= 1
        cycle_flat = [node for scc in cycles for node in scc]
        assert "BL-010" in cycle_flat
        assert "BL-011" in cycle_flat

    def test_three_node_cycle(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-020", deps=["BL-021"])
        _make_bl_file(backlog, "BL-021", deps=["BL-022"])
        _make_bl_file(backlog, "BL-022", deps=["BL-020"])

        result = analyze(vault)
        cycles = detect_cycles(result)
        assert len(cycles) >= 1
        cycle_flat = [node for scc in cycles for node in scc]
        assert "BL-020" in cycle_flat
        assert "BL-021" in cycle_flat
        assert "BL-022" in cycle_flat

    def test_no_cycle_in_dag(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-030", deps=["BL-031"])
        _make_bl_file(backlog, "BL-031", deps=["BL-032"])
        _make_bl_file(backlog, "BL-032", deps=[])

        result = analyze(vault)
        cycles = detect_cycles(result)
        assert cycles == []


# ---------------------------------------------------------------------------
# Test 3: Orphan detection
# ---------------------------------------------------------------------------

class TestFindOrphans:
    """test_find_orphans — BL with no deps and no dependents is orphan"""

    def test_single_orphan(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-040", deps=["BL-041"])
        _make_bl_file(backlog, "BL-041", deps=[])
        _make_bl_file(backlog, "BL-042", deps=[])  # orphan

        result = analyze(vault)
        orphans = find_orphans(result)
        assert "BL-042" in orphans
        assert "BL-040" not in orphans
        assert "BL-041" not in orphans

    def test_all_orphans(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-050", deps=[])
        _make_bl_file(backlog, "BL-051", deps=[])

        result = analyze(vault)
        orphans = find_orphans(result)
        assert "BL-050" in orphans
        assert "BL-051" in orphans

    def test_no_orphans(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-060", deps=["BL-061"])
        _make_bl_file(backlog, "BL-061", deps=[])

        result = analyze(vault)
        orphans = find_orphans(result)
        # BL-060 has outgoing edge, BL-061 has incoming — neither is orphan
        assert "BL-060" not in orphans
        assert "BL-061" not in orphans


# ---------------------------------------------------------------------------
# Test 4: Filter closed BLs
# ---------------------------------------------------------------------------

class TestFilterClosedBLs:
    """test_filter_closed_bls — DONE/ARCHIVED/FREEZE/DEFER BLs excluded from matrix"""

    @pytest.mark.parametrize("closed_status", ["DONE", "ARCHIVED", "ARCHIVED_ID_REUSED",
                                                 "FREEZE", "DEFER"])
    def test_closed_status_excluded(self, tmp_path, closed_status):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-070", deps=[], status=closed_status)
        _make_bl_file(backlog, "BL-071", deps=[])

        result = analyze(vault)
        assert "BL-070" not in result["nodes"]
        assert "BL-070" in result["closed_nodes"]
        assert "BL-071" in result["nodes"]

    def test_done_dep_edge_dropped(self, tmp_path):
        """Edge to a DONE BL should NOT appear in the matrix."""
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-080", deps=["BL-081"])
        _make_bl_file(backlog, "BL-081", status="DONE")

        result = analyze(vault)
        edges = [tuple(e) for e in result["edges"]]
        assert ("BL-080", "BL-081") not in edges

    def test_open_bl_appears(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-090", status="IN_PROGRESS")
        result = analyze(vault)
        assert "BL-090" in result["nodes"]


# ---------------------------------------------------------------------------
# Test 5: Wikilink extraction
# ---------------------------------------------------------------------------

class TestWikilinkExtraction:
    """test_wikilink_extraction — [[BL-XXX]] in body yields related edges"""

    def test_wikilink_creates_edge(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-100", body_wikilinks=["BL-101"])
        _make_bl_file(backlog, "BL-101", deps=[])

        result = analyze(vault)
        edges = [tuple(e) for e in result["edges"]]
        assert ("BL-100", "BL-101") in edges

    def test_wikilink_pattern_direct(self):
        text = "---\nbl_id: BL-100\nstatus: DRAFT\n---\n\nSee [[BL-101]] for details."
        found = _extract_wikilinks(text)
        assert "BL-101" in found

    def test_wikilink_with_alias(self):
        text = "---\nbl_id: BL-200\nstatus: DRAFT\n---\n\nSee [[BL-202|Alias Name]]."
        found = _extract_wikilinks(text)
        assert "BL-202" in found

    def test_no_wikilink_in_frontmatter(self):
        # Wikilinks in frontmatter should not be extracted (body-only)
        text = "---\nbl_id: BL-300\nrelated: '[[BL-301]]'\n---\n"
        found = _extract_wikilinks(text)
        # Frontmatter content stripped — should be empty
        assert "BL-301" not in found


# ---------------------------------------------------------------------------
# Test 6: Optional dependency_types field
# ---------------------------------------------------------------------------

class TestDependencyTypesOptional:
    """test_dependency_types_optional — dependency_types is optional metadata"""

    def test_without_dep_types(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-110", deps=["BL-111"])
        _make_bl_file(backlog, "BL-111", deps=[])

        result = analyze(vault)
        # Should work fine without dependency_types
        edges = [tuple(e) for e in result["edges"]]
        assert ("BL-110", "BL-111") in edges

    def test_with_dep_types_does_not_break(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(
            backlog, "BL-120",
            deps=["BL-121"],
            dep_types={"BL-121": "blocks"}
        )
        _make_bl_file(backlog, "BL-121", deps=[])

        result = analyze(vault)
        edges = [tuple(e) for e in result["edges"]]
        assert ("BL-120", "BL-121") in edges

    def test_builds_on_legacy_creates_edge(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-130", builds_on=["BL-131"])
        _make_bl_file(backlog, "BL-131", deps=[])

        result = analyze(vault)
        edges = [tuple(e) for e in result["edges"]]
        assert ("BL-130", "BL-131") in edges

    def test_related_bl_legacy_creates_edge(self, tmp_path):
        vault, backlog = _vault(tmp_path)
        _make_bl_file(backlog, "BL-140", related_bl="BL-141 (Prior-Art)")
        _make_bl_file(backlog, "BL-141", deps=[])

        result = analyze(vault)
        edges = [tuple(e) for e in result["edges"]]
        assert ("BL-140", "BL-141") in edges


# ---------------------------------------------------------------------------
# Bonus: frontmatter parser unit tests
# ---------------------------------------------------------------------------

class TestParseFrontmatter:
    def test_scalar(self):
        text = "---\nbl_id: BL-001\nstatus: DONE\n---\n"
        fm = _parse_frontmatter(text)
        assert fm["bl_id"] == "BL-001"
        assert fm["status"] == "DONE"

    def test_block_list(self):
        text = "---\ndependencies:\n  - BL-002\n  - BL-003\n---\n"
        fm = _parse_frontmatter(text)
        assert fm["dependencies"] == ["BL-002", "BL-003"]

    def test_flow_list(self):
        text = "---\nbuilds_on: [BL-010, BL-011]\n---\n"
        fm = _parse_frontmatter(text)
        assert fm["builds_on"] == ["BL-010", "BL-011"]

    def test_no_frontmatter(self):
        text = "# Just markdown\nNo frontmatter here."
        fm = _parse_frontmatter(text)
        assert fm == {}
