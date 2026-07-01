"""
test_quality_edge_health.py — BL-177 AK-3 + AK-9 Edge-Health Tests

6 Tests:
1. test_wikilink_resolution_valid      — resolvable wikilinks produce no errors
2. test_wikilink_unresolvable_error    — phantom wikilink = ERROR
3. test_dependencies_exist_warn        — missing builds_on dep = WARN
4. test_builds_on_chain_inv_quality_5  — needs_a_pipeline=true without builds_on = ERROR
5. test_bidirectional_asymmetry_warn   — A.blocks=B but B.blocked_by missing A = WARN
6. test_edge_health_berater_pass       — clean BL with resolved links = PASS
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(__file__))

from quality_edge_health import (
    EdgeHealthBerater,
    check_wikilink_resolution,
    check_dependencies_exist,
    check_builds_on_chain,
    check_bidirectional,
    extract_wikilinks,
    build_vault_index,
)
from quality_berater_base import (
    SEVERITY_ERROR,
    SEVERITY_WARN,
    SEVERITY_INFO,
    BLOCK_STATUS_BLOCK,
    BLOCK_STATUS_PASS,
    BLOCK_STATUS_WARN,
    EXIT_BLOCK,
    EXIT_PASS,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VAULT_INDEX_STUB = {
    "BL-177": "/vault/Backlog/BL-177-quality",
    "BL-163": "/vault/Backlog/BL-163-hil",
    "BL-165": "/vault/Backlog/BL-165-modus",
}

CONTENT_WITH_VALID_LINKS = """---
type: backlog
feature: Test
bl-item: BL-177
tags: [quality, process, vault]
status: READY
builds_on: [BL-163, BL-165]
---

See [[BL-163]] and [[BL-165]] for context.
"""

CONTENT_WITH_BROKEN_LINK = """---
type: backlog
feature: Test
bl-item: BL-177
tags: [quality, process, vault]
status: READY
---

See [[BL-999]] for context. This BL does not exist.
"""

CONTENT_MISSING_BUILDS_ON = """---
type: backlog
feature: Test
bl-item: BL-177
tags: [quality, process, vault]
status: READY
needs_a_pipeline: 'true'
builds_on: []
---

# BL-177 Missing builds_on despite needs_a_pipeline=true
"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_wikilink_resolution_valid():
    """Wikilinks that exist in vault index produce no ERROR findings."""
    findings = check_wikilink_resolution(CONTENT_WITH_VALID_LINKS, "BL-177", VAULT_INDEX_STUB)
    errors = [f for f in findings if f.severity == SEVERITY_ERROR]
    assert errors == [], f"Unexpected errors: {errors}"


def test_wikilink_unresolvable_error():
    """[[BL-999]] not in vault index produces ERROR finding."""
    findings = check_wikilink_resolution(CONTENT_WITH_BROKEN_LINK, "BL-177", VAULT_INDEX_STUB)
    errors = [f for f in findings if f.severity == SEVERITY_ERROR]
    assert len(errors) >= 1, "Expected ERROR for unresolvable wikilink"
    assert "BL-999" in errors[0].message


def test_dependencies_exist_warn():
    """builds_on reference to unknown BL produces WARN."""
    fm = {
        "builds_on": ["BL-999"],
        "related_bl": [],
    }
    findings = check_dependencies_exist(fm, VAULT_INDEX_STUB, "BL-177")
    warns = [f for f in findings if f.severity == SEVERITY_WARN]
    assert len(warns) >= 1, f"Expected WARN for missing dep BL-999, got: {findings}"
    assert "BL-999" in warns[0].message


def test_builds_on_chain_inv_quality_5():
    """needs_a_pipeline=true + empty builds_on = ERROR (INV-QUALITY-5)."""
    fm = {
        "needs_a_pipeline": "true",
        "builds_on": [],
    }
    findings = check_builds_on_chain(fm, "BL-177")
    errors = [f for f in findings if f.severity == SEVERITY_ERROR]
    assert len(errors) >= 1, f"Expected ERROR for missing builds_on chain, got: {findings}"
    assert "INV-QUALITY-5" in errors[0].message


def test_bidirectional_asymmetry_warn():
    """A.blocks=B but B.blocked_by missing A produces WARN."""
    fm_a = {"blocks": ["BL-200"]}
    fm_b = {"blocked_by": []}  # Missing BL-177

    findings = check_bidirectional("BL-177", fm_a, "BL-200", fm_b)
    warns = [f for f in findings if f.severity == SEVERITY_WARN]
    assert len(warns) >= 1, f"Expected WARN for bidirectional asymmetry, got: {findings}"
    assert "BL-200" in warns[0].message


def test_edge_health_berater_pass():
    """EdgeHealthBerater returns PASS for clean BL with resolved links."""
    with tempfile.TemporaryDirectory() as tmpdir:
        berater = EdgeHealthBerater(repo_root=tmpdir)
        data = {
            "content": CONTENT_WITH_VALID_LINKS,
            "frontmatter": {
                "builds_on": ["BL-163", "BL-165"],
                "needs_a_pipeline": "false",
            },
            "vault_index": VAULT_INDEX_STUB,
        }
        result = berater.run(bl_id="BL-177", data=data)
        assert result.block_status == BLOCK_STATUS_PASS, \
            f"Expected PASS, got {result.block_status}: {result.findings}"
        assert result.exit_code == EXIT_PASS
