"""
test_bdf_bl_parallel_bucket_planner.py — Tests for BL-176 AK-5: bdf_bl_parallel_bucket_planner

8 tests covering bucket planning, foundation-stream isolation, balancing,
lock coordination, and edge cases.
"""

import pytest
from unittest.mock import patch, MagicMock
from bdf_bl_parallel_bucket_planner import (
    plan_parallel_buckets,
    coordinate_with_lock,
    BucketPlan,
    Bucket,
)


# ---------------------------------------------------------------------------
# Test 1: Independent BLs go into separate buckets
# ---------------------------------------------------------------------------

def test_independent_bls_in_separate_buckets():
    sequence = ["BL-A", "BL-B", "BL-C", "BL-D"]
    metadata = {
        "BL-A": {"k_score": 50.0},
        "BL-B": {"k_score": 50.0},
        "BL-C": {"k_score": 50.0},
        "BL-D": {"k_score": 50.0},
    }
    dependencies = {}  # all independent
    plan = plan_parallel_buckets(sequence, max_buckets=2, metadata=metadata, dependencies=dependencies)

    # Should have 2 parallel buckets (no foundation stream)
    non_foundation = [b for b in plan.buckets if not b.is_foundation_stream]
    assert len(non_foundation) == 2, f"Expected 2 parallel buckets, got {len(non_foundation)}"
    # Each bucket should have 2 items
    for b in non_foundation:
        assert len(b.items) == 2, f"Expected 2 items per bucket, got {b.items}"


# ---------------------------------------------------------------------------
# Test 2: Foundation BL goes into single-stream (INV-BDF-PARALLEL-2)
# ---------------------------------------------------------------------------

def test_foundation_bl_single_stream():
    sequence = ["BL-FOUND", "BL-A", "BL-B"]
    metadata = {
        "BL-FOUND": {"k_score": 80.0, "foundation_bl": True},
        "BL-A": {"k_score": 30.0},
        "BL-B": {"k_score": 20.0},
    }
    plan = plan_parallel_buckets(sequence, max_buckets=2, metadata=metadata)

    # Foundation stream must exist and contain BL-FOUND
    assert "BL-FOUND" in plan.foundation_stream
    # Foundation bucket must be marked
    foundation_buckets = [b for b in plan.buckets if b.is_foundation_stream]
    assert len(foundation_buckets) == 1
    assert foundation_buckets[0].id == "bucket-foundation"
    # BL-A and BL-B NOT in foundation
    assert "BL-A" not in plan.foundation_stream
    assert "BL-B" not in plan.foundation_stream


# ---------------------------------------------------------------------------
# Test 3: Bucket balancing by k_score aggregate
# ---------------------------------------------------------------------------

def test_bucket_balancing():
    sequence = ["BL-1", "BL-2", "BL-3", "BL-4"]
    metadata = {
        "BL-1": {"k_score": 80.0},
        "BL-2": {"k_score": 70.0},
        "BL-3": {"k_score": 60.0},
        "BL-4": {"k_score": 50.0},
    }
    plan = plan_parallel_buckets(sequence, max_buckets=2, metadata=metadata)
    non_foundation = [b for b in plan.buckets if not b.is_foundation_stream]

    assert len(non_foundation) == 2
    aggs = sorted([b.k_score_aggregate for b in non_foundation])
    # LPT heuristic: (80+50) vs (70+60) = 130 vs 130 — perfectly balanced
    assert aggs[1] - aggs[0] <= 30.0, f"Buckets not balanced enough: {aggs}"


# ---------------------------------------------------------------------------
# Test 4: max_buckets constraint respected
# ---------------------------------------------------------------------------

def test_max_buckets_constraint():
    sequence = [f"BL-{i}" for i in range(10)]
    metadata = {bl: {"k_score": 10.0} for bl in sequence}
    plan = plan_parallel_buckets(sequence, max_buckets=3, metadata=metadata)
    non_foundation = [b for b in plan.buckets if not b.is_foundation_stream]
    assert len(non_foundation) <= 3, f"Expected at most 3 buckets, got {len(non_foundation)}"


# ---------------------------------------------------------------------------
# Test 5: Lock coordination with BL-175 factory_lock (mock)
# ---------------------------------------------------------------------------

def test_lock_coordination_with_BL_175():
    mock_lock_instance = MagicMock()
    mock_lock_instance.acquire.return_value = True

    mock_factory_lock_cls = MagicMock(return_value=mock_lock_instance)

    import bdf_bl_parallel_bucket_planner as module
    original = module._FactoryLock
    try:
        module._FactoryLock = mock_factory_lock_cls
        result = coordinate_with_lock("01", vault_root="/tmp/vault", worker_id="test-worker")
        assert result is True
        mock_factory_lock_cls.assert_called_once()
        call_kwargs = mock_factory_lock_cls.call_args
        assert call_kwargs is not None
    finally:
        module._FactoryLock = original


# ---------------------------------------------------------------------------
# Test 6: Two parallel buckets have no item overlap
# ---------------------------------------------------------------------------

def test_two_parallel_buckets_no_overlap():
    sequence = ["BL-X", "BL-Y", "BL-Z", "BL-W"]
    metadata = {bl: {"k_score": 25.0} for bl in sequence}
    plan = plan_parallel_buckets(sequence, max_buckets=2, metadata=metadata)
    non_foundation = [b for b in plan.buckets if not b.is_foundation_stream]

    all_items = [item for b in non_foundation for item in b.items]
    assert len(all_items) == len(set(all_items)), "Duplicate items found across buckets"
    assert set(all_items) == set(sequence), "Not all items accounted for"


# ---------------------------------------------------------------------------
# Test 7: Dependency cross-bucket prevention (dependent BL not parallelized with its dep)
# ---------------------------------------------------------------------------

def test_dependency_cross_bucket_prevented():
    # BL-B depends on BL-A → they must be in different topological levels
    # so they won't be placed in the same parallel level
    sequence = ["BL-A", "BL-B"]
    metadata = {"BL-A": {"k_score": 40.0}, "BL-B": {"k_score": 40.0}}
    dependencies = {"BL-B": ["BL-A"]}
    plan = plan_parallel_buckets(sequence, max_buckets=2, metadata=metadata, dependencies=dependencies)

    # With 2 topo-levels of 1 item each, max 1 item per level → each level gets 1 bucket
    non_foundation = [b for b in plan.buckets if not b.is_foundation_stream]
    # Check that BL-A and BL-B are never in the same bucket
    for b in non_foundation:
        assert not ("BL-A" in b.items and "BL-B" in b.items), (
            f"BL-A and BL-B found in same bucket {b.id} — dependency violated"
        )


# ---------------------------------------------------------------------------
# Test 8: Empty sequence returns empty plan
# ---------------------------------------------------------------------------

def test_empty_sequence():
    plan = plan_parallel_buckets([], max_buckets=2)
    assert plan.buckets == []
    assert plan.foundation_stream == []
    assert plan.total_items == 0
    assert plan.parallel_levels == []
