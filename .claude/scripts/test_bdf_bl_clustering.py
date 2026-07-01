"""
test_bdf_bl_clustering.py — Unit tests for BL-176 AK-3: bdf_bl_clustering

5 tests covering core clustering behavior.
"""

import pytest
from bdf_bl_clustering import (
    cluster_bls,
    _cohesion_score,
    _topic_overlap,
    _type_match,
    _builds_on_connected,
    Cluster,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

METADATA_SIMPLE = {
    "BL-001": {"tags": ["topic/routing", "type/feature"], "builds_on": []},
    "BL-002": {"tags": ["topic/routing", "type/feature"], "builds_on": []},
    "BL-003": {"tags": ["topic/memory", "type/bugfix"], "builds_on": []},
    "BL-004": {"tags": ["topic/memory", "type/bugfix"], "builds_on": ["BL-003"]},
    "BL-005": {"tags": ["topic/ui", "type/docs"], "builds_on": []},
}

MATRIX_SIMPLE = {
    "items": ["BL-001", "BL-002", "BL-003", "BL-004", "BL-005"],
    "bl_metadata": METADATA_SIMPLE,
}


# ---------------------------------------------------------------------------
# Test 1: Items with identical topic + type tags end up in the same cluster
# ---------------------------------------------------------------------------

def test_same_topic_and_type_grouped_together():
    clusters = cluster_bls(MATRIX_SIMPLE, METADATA_SIMPLE, cohesion_threshold=0.2)
    # BL-001 and BL-002 share topic/routing + type/feature
    cluster_items = [sorted(c.items) for c in clusters]
    assert ["BL-001", "BL-002"] in cluster_items, (
        f"Expected BL-001+BL-002 in same cluster, got: {cluster_items}"
    )


# ---------------------------------------------------------------------------
# Test 2: Items with no shared tags go into separate clusters
# ---------------------------------------------------------------------------

def test_disjoint_topics_separate_clusters():
    metadata = {
        "BL-A": {"tags": ["topic/alpha", "type/feature"], "builds_on": []},
        "BL-B": {"tags": ["topic/beta", "type/refactor"], "builds_on": []},
    }
    matrix = {"items": ["BL-A", "BL-B"], "bl_metadata": metadata}
    clusters = cluster_bls(matrix, metadata, cohesion_threshold=0.2)
    assert len(clusters) == 2, f"Expected 2 separate clusters, got {len(clusters)}"


# ---------------------------------------------------------------------------
# Test 3: builds_on chain increases cohesion and triggers merge
# ---------------------------------------------------------------------------

def test_builds_on_chain_merges_cluster():
    metadata = {
        "BL-X": {"tags": ["topic/infra"], "builds_on": []},
        "BL-Y": {"tags": ["topic/other"], "builds_on": ["BL-X"]},
    }
    matrix = {"items": ["BL-X", "BL-Y"]}
    # builds_on alone gives 0.2 cohesion, exactly at threshold
    clusters = cluster_bls(matrix, metadata, cohesion_threshold=0.2)
    all_items = [item for c in clusters for item in c.items]
    assert "BL-X" in all_items and "BL-Y" in all_items
    # They should be merged into one cluster (score 0.2 >= threshold 0.2)
    cluster_sizes = [len(c.items) for c in clusters]
    assert 2 in cluster_sizes, f"Expected a cluster of size 2, got sizes: {cluster_sizes}"


# ---------------------------------------------------------------------------
# Test 4: dominant_topic and dominant_type are correctly computed
# ---------------------------------------------------------------------------

def test_cluster_dominant_fields():
    metadata = {
        "BL-P": {"tags": ["topic/routing", "type/feature"], "builds_on": []},
        "BL-Q": {"tags": ["topic/routing", "type/feature"], "builds_on": []},
        "BL-R": {"tags": ["topic/routing", "type/bugfix"], "builds_on": []},
    }
    matrix = {"items": ["BL-P", "BL-Q", "BL-R"]}
    clusters = cluster_bls(matrix, metadata, cohesion_threshold=0.2)
    # All share topic/routing → should end up together
    assert len(clusters) == 1
    c = clusters[0]
    assert c.dominant_topic == "topic/routing"
    assert c.dominant_type == "type/feature"  # feature appears 2/3


# ---------------------------------------------------------------------------
# Test 5: Empty matrix returns empty cluster list
# ---------------------------------------------------------------------------

def test_empty_matrix_returns_empty():
    clusters = cluster_bls({"items": []}, {})
    assert clusters == []


# ---------------------------------------------------------------------------
# Test cohesion score helpers (bonus unit tests)
# ---------------------------------------------------------------------------

def test_topic_overlap_perfect():
    tags_a = ["topic/foo", "topic/bar"]
    tags_b = ["topic/foo", "topic/bar"]
    assert _topic_overlap(tags_a, tags_b) == 1.0


def test_cohesion_score_full():
    metadata = {
        "A": {"tags": ["topic/x", "type/feature"], "builds_on": ["B"]},
        "B": {"tags": ["topic/x", "type/feature"], "builds_on": []},
    }
    score = _cohesion_score("A", "B", metadata)
    # topic overlap = 1.0 * 0.5 + type match 0.3 + builds_on 0.2 = 1.0
    assert score == pytest.approx(1.0)
