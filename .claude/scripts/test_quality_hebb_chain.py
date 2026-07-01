"""
test_quality_hebb_chain.py — Tests for AK-6 Hebb-Chain-Verifikation (BL-177)

6 Tests GREEN required.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from quality_hebb_chain import (
    HebbChainResult,
    check_builds_on_min_one,
    check_foundation_done,
    check_source_provenance_chain,
    check_w_fetch_anchors_referenced,
    generate_hebb_mermaid,
    run_checks,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def bl_node_orphan() -> dict:
    """BL with needs_a_pipeline=true but no builds_on."""
    return {
        "bl_id": "BL-999",
        "builds_on": [],
        "status": "READY",
        "needs_a_pipeline": True,
        "type": "feature",
        "foundation_bl": False,
        "source_provenance": "audio-talk-2026",
        "related_bl": [],
    }


@pytest.fixture()
def bl_node_valid() -> dict:
    """BL with all required fields and valid builds_on."""
    return {
        "bl_id": "BL-177",
        "builds_on": ["BL-151", "BL-163"],
        "status": "READY",
        "needs_a_pipeline": True,
        "type": "process-quality",
        "foundation_bl": False,
        "source_provenance": "audio-talk-2026-05-19",
        "related_bl": ["BL-160"],
    }


@pytest.fixture()
def bl_node_no_provenance() -> dict:
    """BL with needs_a_pipeline=true but no source_provenance."""
    return {
        "bl_id": "BL-998",
        "builds_on": ["BL-151"],
        "status": "READY",
        "needs_a_pipeline": True,
        "type": "feature",
        "foundation_bl": False,
        "source_provenance": None,
        "related_bl": [],
    }


@pytest.fixture()
def vault_with_done_bl(tmp_path: Path) -> tuple[Path, Path]:
    """Vault root with BL-151 as DONE folder + BL-177 folder."""
    vault = tmp_path / "Backlog"
    vault.mkdir()

    # BL-151 DONE
    bl151 = vault / "BL-151-vault-routing"
    bl151.mkdir()
    manifest = bl151 / "_manifest.md"
    manifest.write_text(
        "---\nbl-item: BL-151\nstatus: DONE\ntype: foundation\n---\n"
    )

    # BL-177 test folder
    bl177 = vault / "BL-177-test"
    bl177.mkdir()
    (bl177 / "_manifest.md").write_text(
        "---\nbl-item: BL-177\nstatus: READY\nneeds_a_pipeline: true\n"
        "builds_on: [BL-151]\nsource_provenance: audio\n---\n"
    )

    return vault, bl177


@pytest.fixture()
def bl_folder_with_wfetch(tmp_path: Path) -> Path:
    """BL folder with W_fetch dir containing anchor not in builds_on."""
    folder = tmp_path / "BL-177-test"
    folder.mkdir()
    (folder / "_manifest.md").write_text(
        "---\nbl-item: BL-177\nbuilds_on: [BL-151]\nrelated_bl: []\n---\n"
    )
    wfetch = folder / "W_fetch"
    wfetch.mkdir()
    (wfetch / "BL-177_W_fetch.md").write_text(
        "---\nanker_nodes: [BL-151, BL-999]\n---\n# W-Fetch"
    )
    return folder


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_orphan_no_builds_on(bl_node_orphan: dict) -> None:
    """BL with needs_a_pipeline=true and no builds_on → ERROR finding."""
    findings = check_builds_on_min_one(bl_node_orphan)
    assert len(findings) == 1
    assert findings[0].severity == "ERROR"
    assert "builds_on" in findings[0].message.lower() or "orphan" in findings[0].message.lower()


def test_valid_bl_no_orphan_error(bl_node_valid: dict) -> None:
    """BL with builds_on references → 0 ERROR findings."""
    findings = check_builds_on_min_one(bl_node_valid)
    assert all(f.severity != "ERROR" for f in findings)


def test_foundation_done_check(vault_with_done_bl: tuple[Path, Path]) -> None:
    """builds_on BL-151 which is DONE → 0 findings."""
    vault, bl177 = vault_with_done_bl
    findings = check_foundation_done(["BL-151"], vault, "BL-177")
    errors = [f for f in findings if f.severity == "ERROR"]
    assert errors == []


def test_missing_source_provenance(bl_node_no_provenance: dict) -> None:
    """BL with needs_a_pipeline=true but no source_provenance → WARN."""
    findings = check_source_provenance_chain(bl_node_no_provenance)
    assert len(findings) == 1
    assert findings[0].severity == "WARN"
    assert "source_provenance" in findings[0].message


def test_w_fetch_anchor_not_referenced(bl_folder_with_wfetch: Path) -> None:
    """W-Fetch anchor BL-999 not in builds_on/related_bl → WARN."""
    node = {
        "bl_id": "BL-177",
        "builds_on": ["BL-151"],
        "related_bl": [],
    }
    findings = check_w_fetch_anchors_referenced(bl_folder_with_wfetch, node)
    warn_bl999 = [f for f in findings if "BL-999" in f.message]
    assert len(warn_bl999) >= 1
    assert warn_bl999[0].severity == "WARN"


def test_mermaid_graph_generated(bl_node_valid: dict) -> None:
    """Mermaid graph is generated with builds_on and related_bl edges."""
    mermaid = generate_hebb_mermaid(
        "BL-177",
        bl_node_valid["builds_on"],
        bl_node_valid["related_bl"],
    )
    assert "graph LR" in mermaid
    assert "BL_177" in mermaid or "BL-177" in mermaid
    assert "BL_151" in mermaid or "BL-151" in mermaid
    assert "builds_on" in mermaid
