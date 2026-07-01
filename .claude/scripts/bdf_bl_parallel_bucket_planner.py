"""
bdf_bl_parallel_bucket_planner.py — BL-176 AK-5: Parallel Bucket Planner

Distributes a topologically-ordered BL sequence into parallel execution buckets:
- Foundation-BLs (foundation_bl: true) execute single-stream (INV-BDF-PARALLEL-2)
- Independent BLs at the same topological level split across buckets
- Bucket balancing by K-Score aggregate
- BL-175 factory_lock integration for multi-worker coordination

Usage:
    py -3 bdf_bl_parallel_bucket_planner.py plan --sequence=seq.json --max-buckets=2
    py -3 bdf_bl_parallel_bucket_planner.py plan --sequence=seq.json --max-buckets=2 --output=buckets.json
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field, asdict

# Optional factory_lock import — gracefully degrade if not in sys.path
try:
    import importlib.util as _ilu
    _script_dir = Path(__file__).parent
    _spec = _ilu.spec_from_file_location("factory_lock", _script_dir / "factory_lock.py")
    if _spec and _spec.loader:
        _fl_module = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_fl_module)  # type: ignore[union-attr]
        _FactoryLock = getattr(_fl_module, "FactoryLock", None)
    else:
        _FactoryLock = None
except Exception:
    _FactoryLock = None


@dataclass
class Bucket:
    """A parallel execution bucket containing one or more BL items."""
    id: str
    items: list[str]
    worktree_suggestion: str
    k_score_aggregate: float = 0.0
    is_foundation_stream: bool = False


@dataclass
class BucketPlan:
    """Full parallel bucket plan for a BL sequence."""
    buckets: list[Bucket]
    foundation_stream: list[str]
    parallel_levels: list[list[str]]  # raw topological levels
    max_buckets: int
    total_items: int


def _get_k_score(bl_id: str, metadata: dict[str, Any]) -> float:
    """Return k_score for a BL item (default 0.0)."""
    return float(metadata.get(bl_id, {}).get("k_score", 0.0))


def _is_foundation(bl_id: str, metadata: dict[str, Any]) -> bool:
    """Return True if BL is a foundation BL (must run single-stream)."""
    return bool(metadata.get(bl_id, {}).get("foundation_bl", False))


def _build_topo_levels(
    sequence: list[str],
    dependencies: dict[str, list[str]],
) -> list[list[str]]:
    """
    Given a topologically ordered sequence and dependency map,
    group items into levels where items in the same level have no
    cross-dependencies and can potentially run in parallel.

    A BL is in level N if all its dependencies are in levels < N.
    """
    level_of: dict[str, int] = {}
    item_set = set(sequence)

    for bl in sequence:
        deps = [d for d in dependencies.get(bl, []) if d in item_set]
        if not deps:
            level_of[bl] = 0
        else:
            level_of[bl] = max(level_of.get(d, 0) for d in deps) + 1

    max_level = max(level_of.values(), default=0)
    levels: list[list[str]] = [[] for _ in range(max_level + 1)]
    for bl in sequence:
        levels[level_of[bl]].append(bl)

    return [lvl for lvl in levels if lvl]


def _assign_to_buckets(
    items: list[str],
    max_buckets: int,
    metadata: dict[str, Any],
    bucket_id_offset: int = 0,
) -> list[Bucket]:
    """
    Assign items to up to max_buckets buckets, balancing by k_score aggregate.
    Uses a greedy approach: assign each item to the bucket with lowest current aggregate.
    """
    n = min(max_buckets, len(items))
    buckets: list[list[str]] = [[] for _ in range(n)]
    scores: list[float] = [0.0] * n

    # Sort items by k_score descending for better balance (LPT heuristic)
    sorted_items = sorted(items, key=lambda b: _get_k_score(b, metadata), reverse=True)

    for bl in sorted_items:
        # Assign to bucket with minimum current aggregate
        min_idx = scores.index(min(scores))
        buckets[min_idx].append(bl)
        scores[min_idx] += _get_k_score(bl, metadata)

    result: list[Bucket] = []
    for i, (bucket_items, agg) in enumerate(zip(buckets, scores)):
        if bucket_items:
            bid = f"bucket-{bucket_id_offset + i + 1:02d}"
            result.append(Bucket(
                id=bid,
                items=bucket_items,
                worktree_suggestion=f"worktree-{bucket_id_offset + i + 1}",
                k_score_aggregate=round(agg, 2),
                is_foundation_stream=False,
            ))
    return result


def plan_parallel_buckets(
    sequence: list[str],
    max_buckets: int = 2,
    metadata: dict[str, Any] | None = None,
    dependencies: dict[str, list[str]] | None = None,
) -> BucketPlan:
    """
    Plan parallel execution buckets from a topologically-ordered BL sequence.

    INV-BDF-PARALLEL-2: Foundation BLs run in a single sequential stream.
    Non-foundation BLs at the same topological level are distributed across buckets.

    Args:
        sequence: Ordered list of bl_ids (output of sequence planner).
        max_buckets: Maximum number of parallel buckets (default: 2).
        metadata: Per-BL metadata {bl_id: {k_score, foundation_bl, ...}}.
        dependencies: {bl_id: [dep_bl_id, ...]} for level computation.

    Returns:
        BucketPlan with bucket assignments and worktree suggestions.
    """
    if metadata is None:
        metadata = {}
    if dependencies is None:
        dependencies = {}

    if not sequence:
        return BucketPlan(
            buckets=[],
            foundation_stream=[],
            parallel_levels=[],
            max_buckets=max_buckets,
            total_items=0,
        )

    # Separate foundation BLs
    foundation_stream = [bl for bl in sequence if _is_foundation(bl, metadata)]
    parallel_candidates = [bl for bl in sequence if not _is_foundation(bl, metadata)]

    # Build topological levels for parallel candidates
    if parallel_candidates:
        topo_levels = _build_topo_levels(parallel_candidates, dependencies)
    else:
        topo_levels = []

    all_buckets: list[Bucket] = []
    bucket_offset = 0

    # Foundation stream → single bucket (sequential)
    if foundation_stream:
        foundation_agg = sum(_get_k_score(bl, metadata) for bl in foundation_stream)
        all_buckets.append(Bucket(
            id="bucket-foundation",
            items=foundation_stream,
            worktree_suggestion="worktree-foundation",
            k_score_aggregate=round(foundation_agg, 2),
            is_foundation_stream=True,
        ))

    # Parallel levels → distribute across buckets
    for level_items in topo_levels:
        level_buckets = _assign_to_buckets(
            level_items,
            max_buckets=max_buckets,
            metadata=metadata,
            bucket_id_offset=bucket_offset,
        )
        all_buckets.extend(level_buckets)
        bucket_offset += len(level_buckets)

    return BucketPlan(
        buckets=all_buckets,
        foundation_stream=foundation_stream,
        parallel_levels=topo_levels,
        max_buckets=max_buckets,
        total_items=len(sequence),
    )


def coordinate_with_lock(
    bucket_id: str,
    vault_root: str | Path,
    worker_id: str | None = None,
    ttl: int = 300,
) -> bool:
    """
    Acquire a BL-175 factory_lock scoped to the given bucket.

    Args:
        bucket_id: Bucket identifier (e.g. 'bucket-01').
        vault_root: Path to the vault root containing _factory_lock.md.
        worker_id: Optional worker identifier. Auto-generated if None.
        ttl: Lock TTL in seconds (default: 300).

    Returns:
        True if lock acquired, False if factory_lock unavailable.

    Raises:
        RuntimeError: If lock cannot be acquired within timeout.
    """
    if _FactoryLock is None:
        # factory_lock module not available — degrade gracefully
        return False

    scope = f"bucket-{bucket_id}"
    lock = _FactoryLock(
        scope=scope,
        vault_root=Path(vault_root),
        ttl_seconds=ttl,
        worker_id=worker_id,
    )
    acquired = lock.acquire(timeout=60)
    if not acquired:
        raise RuntimeError(
            f"Could not acquire lock for {scope} within 60s. "
            "Another worker may be holding it."
        )
    return True


def bucket_plan_to_dict(plan: BucketPlan) -> dict:
    return {
        "max_buckets": plan.max_buckets,
        "total_items": plan.total_items,
        "foundation_stream": plan.foundation_stream,
        "parallel_levels": plan.parallel_levels,
        "buckets": [asdict(b) for b in plan.buckets],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="BDF BL Parallel Bucket Planner — distribute BL sequence into parallel buckets"
    )
    sub = p.add_subparsers(dest="command")

    plan_cmd = sub.add_parser("plan", help="Plan parallel buckets from sequence")
    plan_cmd.add_argument("--sequence", required=True, help="Path to sequence JSON file")
    plan_cmd.add_argument("--metadata", help="Path to bl_metadata JSON (optional, falls back to sequence.bl_metadata)")
    plan_cmd.add_argument("--max-buckets", type=int, default=2, help="Max parallel buckets (default: 2)")
    plan_cmd.add_argument("--output", help="Output JSON file (default: stdout)")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "plan":
        seq_path = Path(args.sequence)
        if not seq_path.exists():
            print(f"ERROR: sequence file not found: {seq_path}", file=sys.stderr)
            return 1

        with open(seq_path, encoding="utf-8") as f:
            seq_data = json.load(f)

        # sequence may be a list or {"sequence": [...]}
        if isinstance(seq_data, list):
            sequence = seq_data
            dependencies = {}
        else:
            sequence = seq_data.get("sequence", [])
            dependencies = seq_data.get("dependencies", {})

        if args.metadata:
            with open(args.metadata, encoding="utf-8") as f:
                bl_metadata = json.load(f)
        else:
            bl_metadata = seq_data.get("bl_metadata", {}) if isinstance(seq_data, dict) else {}

        plan = plan_parallel_buckets(
            sequence=sequence,
            max_buckets=args.max_buckets,
            metadata=bl_metadata,
            dependencies=dependencies,
        )

        result = bucket_plan_to_dict(plan)
        output_text = json.dumps(result, indent=2, ensure_ascii=False)

        if args.output:
            Path(args.output).write_text(output_text, encoding="utf-8")
            print(f"Wrote {len(plan.buckets)} buckets to {args.output}")
        else:
            print(output_text)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
