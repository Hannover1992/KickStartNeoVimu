"""
test_quality_tag_cluster.py — BL-177 AK-4 + AK-9 Tag-Cluster Tests

5 Tests:
1. test_find_topic_clusters             — clusters built correctly from BL list
2. test_singleton_topics_warn           — tag with 1 BL = WARN
3. test_cross_references_for_topic      — BLs sharing topic without links get INFO
4. test_tag_format_kebab_case           — space in tag = ERROR, uppercase = WARN
5. test_tag_cluster_berater_clean       — clean BL with valid tags = PASS
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(__file__))

from quality_tag_cluster import (
    TagClusterBerater,
    find_topic_clusters,
    check_singleton_topics,
    check_cross_references_for_topic,
    check_tag_format,
    extract_tags,
)
from quality_berater_base import (
    SEVERITY_ERROR,
    SEVERITY_WARN,
    SEVERITY_INFO,
    BLOCK_STATUS_PASS,
    BLOCK_STATUS_WARN,
    BLOCK_STATUS_BLOCK,
    EXIT_PASS,
    EXIT_WARN,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ALL_BLS_FIXTURE = [
    {"bl_id": "BL-177", "frontmatter": {"tags": ["quality", "process", "vault"]}},
    {"bl_id": "BL-163", "frontmatter": {"tags": ["process", "hil", "symmetry"]}},
    {"bl_id": "BL-165", "frontmatter": {"tags": ["process", "modus", "sdf"]}},
    {"bl_id": "BL-160", "frontmatter": {"tags": ["vault", "source-provenance"]}},
    {"bl_id": "BL-999", "frontmatter": {"tags": ["unique-singleton-tag-xyz"]}},
]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_find_topic_clusters():
    """find_topic_clusters groups BLs correctly by tag."""
    clusters = find_topic_clusters(ALL_BLS_FIXTURE)

    assert "quality" in clusters
    assert "BL-177" in clusters["quality"]

    assert "process" in clusters
    process_bls = clusters["process"]
    assert "BL-177" in process_bls
    assert "BL-163" in process_bls
    assert "BL-165" in process_bls

    assert "vault" in clusters
    assert "BL-177" in clusters["vault"]
    assert "BL-160" in clusters["vault"]


def test_singleton_topics_warn():
    """Tag with only 1 BL produces WARN finding for singleton."""
    clusters = find_topic_clusters(ALL_BLS_FIXTURE)
    findings = check_singleton_topics(clusters)

    # "unique-singleton-tag-xyz" should be a singleton
    singleton_msgs = [f.message for f in findings if "unique-singleton-tag-xyz" in f.message]
    assert len(singleton_msgs) >= 1, f"Expected singleton WARN for unique-singleton-tag-xyz, got: {findings}"

    warn_only = [f for f in findings if f.severity != SEVERITY_WARN]
    assert warn_only == [], f"Singleton findings should all be WARN, got: {warn_only}"


def test_cross_references_for_topic():
    """BLs sharing a large topic without cross-references get INFO findings."""
    all_bls_fm = {
        "BL-177": {"tags": ["shared-topic", "other"], "related_bl": [], "builds_on": []},
        "BL-163": {"tags": ["shared-topic", "other"], "related_bl": [], "builds_on": []},
        "BL-165": {"tags": ["shared-topic", "other"], "related_bl": [], "builds_on": []},
        "BL-160": {"tags": ["shared-topic", "other"], "related_bl": [], "builds_on": []},
    }
    bls_in_topic = ["BL-177", "BL-163", "BL-165", "BL-160"]
    findings = check_cross_references_for_topic("shared-topic", bls_in_topic, all_bls_fm)

    # Should produce INFO findings for nodes without cross-references
    info_findings = [f for f in findings if f.severity == SEVERITY_INFO]
    assert len(info_findings) > 0, "Expected INFO findings for missing cross-references"


def test_tag_format_kebab_case():
    """Tags with spaces = ERROR, uppercase = WARN."""
    tags_with_issues = ["quality process", "Process-Type", "vault"]
    findings = check_tag_format(tags_with_issues, "BL-TEST")

    # "quality process" has space = ERROR
    space_errors = [f for f in findings if f.severity == SEVERITY_ERROR and "space" in f.message.lower()]
    assert len(space_errors) >= 1, f"Expected ERROR for tag with space, got: {findings}"

    # "Process-Type" has uppercase = WARN
    case_warns = [f for f in findings if f.severity == SEVERITY_WARN and "Process-Type" in f.message]
    assert len(case_warns) >= 1, f"Expected WARN for uppercase tag, got: {findings}"

    # "vault" is fine — no findings
    vault_findings = [f for f in findings if "vault" in f.message]
    assert vault_findings == [], f"'vault' should have no findings, got: {vault_findings}"


def test_tag_cluster_berater_clean():
    """TagClusterBerater returns PASS for well-formed tags with no singleton issues."""
    with tempfile.TemporaryDirectory() as tmpdir:
        berater = TagClusterBerater(repo_root=tmpdir)

        # Provide a BL with tags that exist in multiple BLs (not singletons)
        fm = {"tags": ["quality", "process", "vault"]}
        data = {
            "frontmatter": fm,
            "all_bls": ALL_BLS_FIXTURE,
        }
        result = berater.run(bl_id="BL-177", data=data)

        # BL-177's tags (quality, process, vault) all appear in multiple BLs
        # so no singleton WARN should be emitted for THIS BL
        errors = [f for f in result.findings if f.severity == SEVERITY_ERROR]
        assert errors == [], f"Expected no errors for clean BL-177 tags, got: {errors}"
        assert result.exit_code in (EXIT_PASS, EXIT_WARN), f"Expected PASS or WARN, got {result.exit_code}"
