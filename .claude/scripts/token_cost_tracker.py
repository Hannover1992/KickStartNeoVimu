"""
token_cost_tracker.py — BL-178 AK-8
Track and visualize token cost savings from Index vs Content split.
Per INV-INDEX-SPLIT-5 (BL-178, 2026-05-19).

Usage:
  py -3 .claude/scripts/token_cost_tracker.py track --vault-root PATH [--json]
  py -3 .claude/scripts/token_cost_tracker.py compare --vault-root PATH --rollback-tag TAG [--json]
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


TOKENS_PER_LOC = 25  # 1 LOC ≈ 25 tokens (conservative estimate)

ACTIVE_INDEX_FILES = [
    "_backlog_index.md",
    "_parking-lot.md",
]
ARCHIVE_INDEX_FILES = [
    "_backlog_index_done.md",
    "_parking-lot_done.md",
]


def count_loc(path: Path) -> int:
    """Count non-empty lines in a file. Returns 0 if file doesn't exist."""
    if not path.exists():
        return 0
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return sum(1 for line in lines if line.strip())
    except Exception:
        return 0


def track_index_size(vault_root: Path) -> dict:
    """
    Measure current LOC and token estimates for active and archive indexes.
    Returns: {total_loc, active_loc, archive_loc, token_estimate, saving_pct, files}
    """
    vault = Path(vault_root)
    active_loc = 0
    archive_loc = 0
    files_detail = {}

    for fname in ACTIVE_INDEX_FILES:
        fpath = vault / fname
        loc = count_loc(fpath)
        active_loc += loc
        files_detail[fname] = {"loc": loc, "exists": fpath.exists(), "type": "active"}

    for fname in ARCHIVE_INDEX_FILES:
        fpath = vault / fname
        loc = count_loc(fpath)
        archive_loc += loc
        files_detail[fname] = {"loc": loc, "exists": fpath.exists(), "type": "archive"}

    total_loc = active_loc + archive_loc
    token_estimate_active = active_loc * TOKENS_PER_LOC
    token_estimate_total = total_loc * TOKENS_PER_LOC

    if total_loc > 0:
        saving_pct = round((archive_loc / total_loc) * 100, 1)
    else:
        saving_pct = 0.0

    return {
        "total_loc": total_loc,
        "active_loc": active_loc,
        "archive_loc": archive_loc,
        "token_estimate_active": token_estimate_active,
        "token_estimate_total": token_estimate_total,
        "saving_pct": saving_pct,
        "files": files_detail,
    }


def compare_pre_post_migration(vault_root: Path, rollback_tag: str) -> dict:
    """
    Compare index sizes before migration (via git tag) and now.
    Returns: {pre, post, delta_loc, delta_tokens, saving_pct}
    """
    vault = Path(vault_root)
    pre_loc = {}
    post_snapshot = track_index_size(vault)

    # Read LOC at rollback_tag from git
    for fname in ACTIVE_INDEX_FILES + ARCHIVE_INDEX_FILES:
        fpath = vault / fname
        # Get file relative to repo root
        try:
            rel = os.path.relpath(str(fpath))
            result = subprocess.run(
                ["git", "show", f"{rollback_tag}:{rel}"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                lines = result.stdout.splitlines()
                pre_loc[fname] = sum(1 for line in lines if line.strip())
            else:
                pre_loc[fname] = 0
        except Exception:
            pre_loc[fname] = 0

    pre_total = sum(pre_loc.values())
    post_active = post_snapshot["active_loc"]
    delta_loc = pre_total - post_active

    if pre_total > 0:
        saving_pct = round((delta_loc / pre_total) * 100, 1)
    else:
        saving_pct = 0.0

    return {
        "rollback_tag": rollback_tag,
        "pre": {
            "total_loc": pre_total,
            "token_estimate": pre_total * TOKENS_PER_LOC,
            "files": pre_loc,
        },
        "post": {
            "active_loc": post_active,
            "token_estimate_active": post_snapshot["token_estimate_active"],
        },
        "delta_loc": delta_loc,
        "delta_tokens": delta_loc * TOKENS_PER_LOC,
        "saving_pct": saving_pct,
    }


def ascii_bar_chart(data: dict) -> str:
    """
    Renders an ASCII bar chart comparing active vs archive LOC.
    """
    active = data["active_loc"]
    archive = data["archive_loc"]
    total = data["total_loc"]
    saving = data["saving_pct"]

    bar_width = 40
    if total > 0:
        active_bars = max(1, int((active / total) * bar_width))
        archive_bars = max(1, int((archive / total) * bar_width))
    else:
        active_bars = bar_width
        archive_bars = 0

    lines = [
        "╔══════════════════════════════════════════════════╗",
        "║  BL-178 Token-Saving Report (AK-8)               ║",
        "╠══════════════════════════════════════════════════╣",
        f"║  Total LOC:   {total:>6}  ({total * TOKENS_PER_LOC:>7} tokens est.)    ║",
        f"║  Active LOC:  {active:>6}  ({active * TOKENS_PER_LOC:>7} tokens)        ║",
        f"║  Archive LOC: {archive:>6}  ({archive * TOKENS_PER_LOC:>7} tokens)        ║",
        f"║  Saving:      {saving:>5}%                              ║",
        "╠══════════════════════════════════════════════════╣",
        f"║  Active  [{'#' * active_bars}{' ' * (bar_width - active_bars)}]  ║",
        f"║  Archive [{'#' * archive_bars}{' ' * (bar_width - archive_bars)}]  ║",
        "╚══════════════════════════════════════════════════╝",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="BL-178 AK-8 — Token Cost Tracker for Index Split"
    )
    subparsers = parser.add_subparsers(dest="command")

    # track subcommand
    track_parser = subparsers.add_parser("track", help="Measure current index sizes")
    track_parser.add_argument("--vault-root", required=True)
    track_parser.add_argument("--json", action="store_true", dest="json_output")

    # compare subcommand
    compare_parser = subparsers.add_parser("compare", help="Compare pre/post migration")
    compare_parser.add_argument("--vault-root", required=True)
    compare_parser.add_argument("--rollback-tag", required=True)
    compare_parser.add_argument("--json", action="store_true", dest="json_output")

    args = parser.parse_args()

    if args.command == "track":
        result = track_index_size(Path(args.vault_root))
        if args.json_output:
            print(json.dumps(result, indent=2))
        else:
            print(ascii_bar_chart(result))
            for fname, info in result["files"].items():
                status = "OK" if info["exists"] else "MISSING"
                print(f"  [{info['type'].upper()}] {fname}: {info['loc']} LOC ({status})")

    elif args.command == "compare":
        result = compare_pre_post_migration(Path(args.vault_root), args.rollback_tag)
        if args.json_output:
            print(json.dumps(result, indent=2))
        else:
            print(f"Pre-migration total: {result['pre']['total_loc']} LOC")
            print(f"Post-migration active: {result['post']['active_loc']} LOC")
            print(f"Delta: -{result['delta_loc']} LOC ({result['saving_pct']}% saving)")
            print(f"Token saving: ~{result['delta_tokens']:,} tokens")

    else:
        parser.print_help()
        sys.exit(0)


if __name__ == "__main__":
    main()
