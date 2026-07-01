"""
bdf_bl_clustering.py — BL-176 AK-3: BL-Kohäsions-Clustering

Gruppiert Backlog-Items nach Kohäsions-Signalen:
- tags topic/* Überschneidung
- type/ Identität
- builds_on: Chains

Usage:
    py -3 bdf_bl_clustering.py cluster --matrix=matrix.json
    py -3 bdf_bl_clustering.py cluster --matrix=matrix.json --output=clusters.json
"""

import json
import argparse
import sys
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field, asdict


@dataclass
class Cluster:
    """Represents a cohesion-based cluster of BL items."""
    id: str
    items: list[str]
    dominant_topic: str | None
    dominant_type: str | None
    cohesion_score: float = 0.0
    tags_union: list[str] = field(default_factory=list)


def _extract_topic_tags(tags: list[str]) -> list[str]:
    """Return only topic/* tags from a tag list."""
    return [t for t in tags if t.startswith("topic/")]


def _extract_type_tag(tags: list[str]) -> str | None:
    """Return the first type/* tag, or None."""
    for t in tags:
        if t.startswith("type/"):
            return t
    return None


def _topic_overlap(tags_a: list[str], tags_b: list[str]) -> float:
    """Jaccard similarity between topic tag sets."""
    topics_a = set(_extract_topic_tags(tags_a))
    topics_b = set(_extract_topic_tags(tags_b))
    if not topics_a and not topics_b:
        return 0.0
    union = topics_a | topics_b
    intersection = topics_a & topics_b
    return len(intersection) / len(union)


def _type_match(tags_a: list[str], tags_b: list[str]) -> bool:
    """True if both items share the same type/* tag."""
    return _extract_type_tag(tags_a) == _extract_type_tag(tags_b) and _extract_type_tag(tags_a) is not None


def _builds_on_connected(bl_id_a: str, bl_id_b: str, metadata: dict[str, Any]) -> bool:
    """True if either item builds_on the other."""
    builds_a = metadata.get(bl_id_a, {}).get("builds_on", [])
    builds_b = metadata.get(bl_id_b, {}).get("builds_on", [])
    return bl_id_b in builds_a or bl_id_a in builds_b


def _cohesion_score(bl_id_a: str, bl_id_b: str, metadata: dict[str, Any]) -> float:
    """
    Composite cohesion score in [0.0, 1.0]:
    - topic overlap contributes up to 0.5
    - type match contributes 0.3
    - builds_on chain contributes 0.2
    """
    meta_a = metadata.get(bl_id_a, {})
    meta_b = metadata.get(bl_id_b, {})
    tags_a = meta_a.get("tags", [])
    tags_b = meta_b.get("tags", [])

    score = 0.0
    score += _topic_overlap(tags_a, tags_b) * 0.5
    if _type_match(tags_a, tags_b):
        score += 0.3
    if _builds_on_connected(bl_id_a, bl_id_b, metadata):
        score += 0.2
    return round(score, 4)


def _dominant_topic(items: list[str], metadata: dict[str, Any]) -> str | None:
    """Return the most common topic/* tag across all items in the cluster."""
    topic_count: dict[str, int] = {}
    for bl_id in items:
        for tag in _extract_topic_tags(metadata.get(bl_id, {}).get("tags", [])):
            topic_count[tag] = topic_count.get(tag, 0) + 1
    if not topic_count:
        return None
    return max(topic_count, key=lambda t: topic_count[t])


def _dominant_type(items: list[str], metadata: dict[str, Any]) -> str | None:
    """Return the most common type/* tag across all items."""
    type_count: dict[str, int] = {}
    for bl_id in items:
        t = _extract_type_tag(metadata.get(bl_id, {}).get("tags", []))
        if t:
            type_count[t] = type_count.get(t, 0) + 1
    if not type_count:
        return None
    return max(type_count, key=lambda t: type_count[t])


def _union_tags(items: list[str], metadata: dict[str, Any]) -> list[str]:
    """Union of all tags across items."""
    tags: set[str] = set()
    for bl_id in items:
        tags.update(metadata.get(bl_id, {}).get("tags", []))
    return sorted(tags)


def _avg_cluster_cohesion(items: list[str], metadata: dict[str, Any]) -> float:
    """Average pairwise cohesion score within a cluster."""
    if len(items) < 2:
        return 1.0
    pairs = 0
    total = 0.0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            total += _cohesion_score(items[i], items[j], metadata)
            pairs += 1
    return round(total / pairs, 4) if pairs > 0 else 0.0


def cluster_bls(
    matrix: dict[str, Any],
    bl_metadata: dict[str, Any],
    cohesion_threshold: float = 0.2,
) -> list[Cluster]:
    """
    Group BL items into cohesion-based clusters.

    Args:
        matrix: Dependency/priority matrix. Expected keys: 'items' (list of bl_ids),
                optionally 'dependencies' dict.
        bl_metadata: Per-BL metadata dict: {bl_id: {tags: [...], builds_on: [...], ...}}
        cohesion_threshold: Minimum pairwise cohesion score to merge into same cluster.

    Returns:
        List of Cluster objects, sorted by dominant_topic then id.
    """
    items: list[str] = matrix.get("items", [])
    if not items:
        return []

    # Union-Find for cluster grouping
    parent: dict[str, str] = {bl: bl for bl in items}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x: str, y: str) -> None:
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[ry] = rx

    # Merge items with sufficient cohesion
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            score = _cohesion_score(items[i], items[j], bl_metadata)
            if score >= cohesion_threshold:
                union(items[i], items[j])

    # Build cluster groups
    groups: dict[str, list[str]] = {}
    for bl in items:
        root = find(bl)
        groups.setdefault(root, []).append(bl)

    clusters: list[Cluster] = []
    for idx, (root, members) in enumerate(sorted(groups.items())):
        c = Cluster(
            id=f"cluster-{idx + 1:02d}",
            items=sorted(members),
            dominant_topic=_dominant_topic(members, bl_metadata),
            dominant_type=_dominant_type(members, bl_metadata),
            cohesion_score=_avg_cluster_cohesion(members, bl_metadata),
            tags_union=_union_tags(members, bl_metadata),
        )
        clusters.append(c)

    # Sort: dominant_topic (None last), then cluster id
    clusters.sort(key=lambda c: (c.dominant_topic or "zzz", c.id))
    # Re-number after sort
    for idx, c in enumerate(clusters):
        c.id = f"cluster-{idx + 1:02d}"

    return clusters


def clusters_to_dict(clusters: list[Cluster]) -> list[dict]:
    return [asdict(c) for c in clusters]


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="BDF BL Clustering — group BL items by cohesion"
    )
    sub = p.add_subparsers(dest="command")

    cluster_cmd = sub.add_parser("cluster", help="Cluster BL items from matrix")
    cluster_cmd.add_argument("--matrix", required=True, help="Path to matrix JSON file")
    cluster_cmd.add_argument("--metadata", help="Path to bl_metadata JSON file (optional, falls back to matrix.bl_metadata)")
    cluster_cmd.add_argument("--threshold", type=float, default=0.2, help="Cohesion threshold (default: 0.2)")
    cluster_cmd.add_argument("--output", help="Output JSON file (default: stdout)")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "cluster":
        matrix_path = Path(args.matrix)
        if not matrix_path.exists():
            print(f"ERROR: matrix file not found: {matrix_path}", file=sys.stderr)
            return 1

        with open(matrix_path, encoding="utf-8") as f:
            matrix = json.load(f)

        # metadata: explicit file or embedded in matrix
        if args.metadata:
            with open(args.metadata, encoding="utf-8") as f:
                bl_metadata = json.load(f)
        else:
            bl_metadata = matrix.get("bl_metadata", {})

        clusters = cluster_bls(matrix, bl_metadata, cohesion_threshold=args.threshold)
        result = clusters_to_dict(clusters)

        output_text = json.dumps(result, indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(output_text, encoding="utf-8")
            print(f"Wrote {len(clusters)} clusters to {args.output}")
        else:
            print(output_text)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
