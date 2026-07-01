"""
bdf_bl_sequence_planner.py — BL-176 AK-4: Topological Sequence Planner

Topological sort of BL items with:
- Kahn's algorithm for cycle-free ordering
- Tiebreak: KRITISCH > HOCH > MITTEL > NIEDRIG, then k_score descending
- Cycle detection with HiL-Alert

Usage:
    py -3 bdf_bl_sequence_planner.py plan --matrix=matrix.json
    py -3 bdf_bl_sequence_planner.py plan --matrix=matrix.json --output=sequence.json
"""

import json
import argparse
import sys
from collections import defaultdict, deque
from pathlib import Path
from typing import Any


PRIORITY_ORDER = {"KRITISCH": 0, "HOCH": 1, "MITTEL": 2, "NIEDRIG": 3}
DEFAULT_PRIORITY = "NIEDRIG"


class CycleDetectedError(Exception):
    """Raised when a dependency cycle is detected in the BL graph."""
    def __init__(self, cycle_nodes: list[str]):
        self.cycle_nodes = cycle_nodes
        super().__init__(f"HiL-ALERT: Dependency cycle detected involving: {cycle_nodes}")


def _priority_key(bl_id: str, priorities: dict[str, Any]) -> tuple[int, float]:
    """
    Returns sort key (priority_rank, -k_score) for stable tiebreak.
    Lower priority_rank = higher urgency.
    """
    entry = priorities.get(bl_id, {})
    if isinstance(entry, str):
        # priorities may map bl_id -> priority string directly
        prio_str = entry.upper()
        k_score = 0.0
    else:
        prio_str = str(entry.get("priority", DEFAULT_PRIORITY)).upper()
        k_score = float(entry.get("k_score", 0.0))
    rank = PRIORITY_ORDER.get(prio_str, PRIORITY_ORDER[DEFAULT_PRIORITY])
    return (rank, -k_score)


def _find_cycle(graph: dict[str, list[str]], all_nodes: list[str]) -> list[str]:
    """
    DFS-based cycle detection. Returns nodes involved in a cycle, or empty list.
    """
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n: WHITE for n in all_nodes}
    cycle_nodes: list[str] = []

    def dfs(node: str, path: list[str]) -> bool:
        color[node] = GRAY
        path.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                # Found cycle — extract the cycle portion
                cycle_start = path.index(neighbor)
                cycle_nodes.extend(path[cycle_start:])
                return True
            if color[neighbor] == WHITE:
                if dfs(neighbor, path):
                    return True
        path.pop()
        color[node] = BLACK
        return False

    for node in all_nodes:
        if color[node] == WHITE:
            if dfs(node, []):
                return cycle_nodes
    return []


def plan_sequence(
    matrix: dict[str, Any],
    priorities: dict[str, Any],
) -> list[str]:
    """
    Topological sort of BL items using Kahn's algorithm.

    Args:
        matrix: Must contain 'items' (list of bl_ids) and optionally
                'dependencies' ({bl_id: [dep_bl_id, ...]}).
        priorities: {bl_id: {priority: str, k_score: float}} or {bl_id: priority_str}

    Returns:
        Ordered list of bl_ids (dependencies before dependents).

    Raises:
        CycleDetectedError: If a dependency cycle is detected (HiL-Alert).
    """
    items: list[str] = matrix.get("items", [])
    if not items:
        return []

    raw_deps: dict[str, list[str]] = matrix.get("dependencies", {})

    # Build adjacency: node -> [successors that depend on node]
    # deps[b] = [a] means b must come before a (a depends on b)
    in_degree: dict[str, int] = {bl: 0 for bl in items}
    successors: dict[str, list[str]] = defaultdict(list)  # dep -> [dependents]

    item_set = set(items)

    for bl, deps in raw_deps.items():
        if bl not in item_set:
            continue
        for dep in deps:
            if dep not in item_set:
                continue
            # bl depends on dep => dep must come first
            successors[dep].append(bl)
            in_degree[bl] = in_degree.get(bl, 0) + 1

    # Ensure all items have an in_degree entry
    for bl in items:
        if bl not in in_degree:
            in_degree[bl] = 0

    # Cycle check first
    forward_graph: dict[str, list[str]] = {bl: list(successors.get(bl, [])) for bl in items}
    cycle = _find_cycle(forward_graph, items)
    if cycle:
        raise CycleDetectedError(cycle)

    # Kahn's algorithm with priority tiebreak
    result: list[str] = []
    # Queue: all nodes with in_degree 0, sorted by priority
    ready: list[str] = [bl for bl in items if in_degree[bl] == 0]
    ready.sort(key=lambda bl: _priority_key(bl, priorities))

    # Use a sorted list as priority queue (small N, so sort on each pop is fine)
    ready_deque = deque(ready)

    while ready_deque:
        node = ready_deque.popleft()
        result.append(node)

        newly_ready: list[str] = []
        for succ in successors.get(node, []):
            in_degree[succ] -= 1
            if in_degree[succ] == 0:
                newly_ready.append(succ)

        if newly_ready:
            newly_ready.sort(key=lambda bl: _priority_key(bl, priorities))
            # Insert into ready_deque maintaining priority order
            # Re-sort full deque + newly_ready
            combined = list(ready_deque) + newly_ready
            combined.sort(key=lambda bl: _priority_key(bl, priorities))
            ready_deque = deque(combined)

    if len(result) != len(items):
        # Residual items not reachable — indicates cycle not caught by DFS
        remaining = [bl for bl in items if bl not in set(result)]
        raise CycleDetectedError(remaining)

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="BDF BL Sequence Planner — topological sort with priority tiebreak"
    )
    sub = p.add_subparsers(dest="command")

    plan_cmd = sub.add_parser("plan", help="Plan BL execution sequence from matrix")
    plan_cmd.add_argument("--matrix", required=True, help="Path to matrix JSON file")
    plan_cmd.add_argument("--priorities", help="Path to priorities JSON file (optional, falls back to matrix.priorities)")
    plan_cmd.add_argument("--output", help="Output JSON file (default: stdout)")

    return p


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "plan":
        matrix_path = Path(args.matrix)
        if not matrix_path.exists():
            print(f"ERROR: matrix file not found: {matrix_path}", file=sys.stderr)
            return 1

        with open(matrix_path, encoding="utf-8") as f:
            matrix = json.load(f)

        if args.priorities:
            with open(args.priorities, encoding="utf-8") as f:
                priorities = json.load(f)
        else:
            priorities = matrix.get("priorities", {})

        try:
            sequence = plan_sequence(matrix, priorities)
        except CycleDetectedError as e:
            print(f"HiL-ALERT: {e}", file=sys.stderr)
            return 2

        result = {"sequence": sequence, "count": len(sequence)}
        output_text = json.dumps(result, indent=2, ensure_ascii=False)

        if args.output:
            Path(args.output).write_text(output_text, encoding="utf-8")
            print(f"Wrote sequence of {len(sequence)} items to {args.output}")
        else:
            print(output_text)
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
