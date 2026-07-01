"""
view_ref_sweep.py — P2 Forward-Garantie queue-drain sweep (BL-460 follow-on).

Drains `{vault_root}/_forward_ref_pending.md` (enqueued by hook_view_forward_reference.py)
by materializing each pending view via the production engine.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from view_forward_reference import forward_reference_view
from view_node_predicate import is_view_node
import referenz_ableiter


def drain_pending(
    vault_root,
    *,
    atom_index=None,
    report_path=None,
    gate_mode="target",
    write=True,
    scorer=None,
) -> dict:
    """Drain the forward-reference pending queue.

    Reads `{vault_root}/_forward_ref_pending.md`, processes each path, and
    rewrites the queue with only the paths that must be retried (deferred).

    Returns:
        dict with keys: processed, written, idempotent, deferred, skipped, remaining
    """
    empty = {
        "processed": 0,
        "written": 0,
        "idempotent": 0,
        "deferred": 0,
        "skipped": 0,
        "remaining": 0,
    }

    queue_file = Path(vault_root) / "_forward_ref_pending.md"

    if not queue_file.exists():
        return empty

    # Read and dedup the queue (preserve first-seen order)
    raw_lines = queue_file.read_text(encoding="utf-8").splitlines()
    seen: set[str] = set()
    deduped: list[str] = []
    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped not in seen:
            seen.add(stripped)
            deduped.append(stripped)

    if not deduped:
        if write:
            queue_file.write_bytes(b"")
        return empty

    # Build atom_index lazily (once) if not provided and write=True
    effective_index = atom_index
    if effective_index is None:
        try:
            effective_index = referenz_ableiter.build_atom_index_from_vault(vault_root)
        except Exception:
            effective_index = {}

    processed = 0
    written = 0
    idempotent = 0
    deferred = 0
    skipped = 0
    kept: list[str] = []

    for path in deduped:
        processed += 1

        if not is_view_node(path, str(vault_root)):
            skipped += 1
            # Do NOT keep — remove from queue
            continue

        try:
            r = forward_reference_view(
                path,
                str(vault_root),
                atom_index=effective_index,
                write=write,
                gate_mode=gate_mode,
                report_path=report_path,
            )
            action = r.get("action", "")

            if action == "written":
                reason = r.get("reason", "")
                if "idempotent" in reason:
                    idempotent += 1
                else:
                    written += 1
                # Remove from queue (successful write or idempotent)

            elif action == "deferred-gated":
                deferred += 1
                kept.append(path)

            elif action == "dry-run":
                # Dry-run: do not mutate the queue; keep entry
                kept.append(path)

            else:
                # Unknown/unexpected action — keep defensively
                kept.append(path)

        except Exception:
            # On any exception: count as deferred + keep so nothing is lost
            deferred += 1
            kept.append(path)

    # Rewrite queue file only when write=True
    if write:
        if kept:
            content = "".join(p + "\n" for p in kept)
            queue_file.write_text(content, encoding="utf-8")
        else:
            queue_file.write_bytes(b"")
        remaining = len(kept)
    else:
        # Dry-run: leave file unchanged; remaining = original queue length
        remaining = len(deduped)

    return {
        "processed": processed,
        "written": written,
        "idempotent": idempotent,
        "deferred": deferred,
        "skipped": skipped,
        "remaining": remaining,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="P2 Forward-Garantie queue-drain sweep (BL-460)"
    )
    parser.add_argument("--vault-root", required=True, help="Vault root directory")
    parser.add_argument("--report-path", default=None, help="Optional report path")
    parser.add_argument("--gate-mode", default="target", help="Gate mode (default: target)")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Dry-run mode: do not write or mutate the queue",
    )

    args = parser.parse_args(argv)

    result = drain_pending(
        args.vault_root,
        report_path=args.report_path,
        gate_mode=args.gate_mode,
        write=not args.dry_run,
    )

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
