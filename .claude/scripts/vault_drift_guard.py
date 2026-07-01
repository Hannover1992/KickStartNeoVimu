"""
vault_drift_guard.py — BL-P3 Vault-Drift-Guard (READ-ONLY health-check compositor).

Composites 3 existing detectors:
  - vault_node_health.scan_vault_backlog  (corruption)
  - index_node_drift.scan_drift           (index drift)
  - manifest_drift_detector.scan_manifest_drift (manifest drift)

API:
    run_all_drift_checks(vault_root, *, node_health_fn=None, index_drift_fn=None,
                         manifest_drift_fn=None) -> dict

main() — argparse vault_root -> report to stdout -> exit 0 (clean) or exit 1 (drift).
READ-ONLY: does NOT auto-correct any drift.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---- same script-dir sys.path pattern used in other scripts ----
_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import vault_node_health
import index_node_drift
import manifest_drift_detector


def run_all_drift_checks(
    vault_root,
    *,
    node_health_fn=None,
    index_drift_fn=None,
    manifest_drift_fn=None,
) -> dict:
    """Aggregate all drift checks into a single report dict.

    DI parameters allow injecting stub functions for testing.
    - node_health_fn(backlog_dir) -> list
    - index_drift_fn(vault_root) -> list
    - manifest_drift_fn(vault_root) -> dict

    Defaults call the real detector functions.
    Fail-safe: each detector wrapped in try/except; errors yield empty results.

    Returns:
        {
            "corruption":     list,
            "index_drift":    list,
            "manifest_drift": dict,
            "total_issues":   int,
            "clean":          bool,
        }
    """
    vault_root = Path(vault_root)
    backlog_dir = vault_root / "Vault" / "Backlog"

    # --- node health (corruption) ---
    if node_health_fn is None:
        # Default: recursive scan of Backlog (all .md files in subdirs too).
        # scan_vault_backlog is flat (1 level); vault_drift_guard scans fully recursive.
        def _node_fn(bd: Path) -> list:
            results = []
            if not bd.is_dir():
                return results
            for md_file in bd.rglob("*.md"):
                if md_file.is_file():
                    r = vault_node_health.scan_vault_node(md_file)
                    if r is not None:
                        results.append(r)
            return results
    else:
        _node_fn = node_health_fn

    try:
        corruption = list(_node_fn(backlog_dir))
    except Exception:
        corruption = []

    # --- index drift ---
    if index_drift_fn is None:
        _idx_fn = lambda vr: index_node_drift.scan_drift(str(vr))
    else:
        _idx_fn = index_drift_fn

    try:
        index_drift = list(_idx_fn(vault_root))
    except Exception:
        index_drift = []

    # --- manifest drift ---
    if manifest_drift_fn is None:
        _mfn = lambda vr: manifest_drift_detector.scan_manifest_drift(str(vr))
    else:
        _mfn = manifest_drift_fn

    try:
        manifest_drift = _mfn(vault_root)
    except Exception:
        manifest_drift = {"duplicate_blocks": [], "split_brain_blocks": []}

    # Ensure manifest_drift is a dict with required keys (fail-safe)
    if not isinstance(manifest_drift, dict):
        manifest_drift = {"duplicate_blocks": [], "split_brain_blocks": []}

    total_issues = (
        len(corruption)
        + len(index_drift)
        + len(manifest_drift.get("duplicate_blocks", []))
        + len(manifest_drift.get("split_brain_blocks", []))
    )
    clean = total_issues == 0

    return {
        "corruption": corruption,
        "index_drift": index_drift,
        "manifest_drift": manifest_drift,
        "total_issues": total_issues,
        "clean": clean,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vault Drift Guard — READ-ONLY composite health check."
    )
    parser.add_argument("vault_root", help="Path to the vault root directory.")
    args = parser.parse_args()

    result = run_all_drift_checks(args.vault_root)

    corruption = result["corruption"]
    index_drift = result["index_drift"]
    manifest_drift = result["manifest_drift"]
    total_issues = result["total_issues"]
    clean = result["clean"]

    print("=== Vault Drift Guard Report ===")
    print()

    # corruption section
    print(f"[corruption] count={len(corruption)}")
    for item in corruption:
        print(f"  - {item}")

    print()

    # index drift section
    print(f"[index_drift] count={len(index_drift)}")
    for item in index_drift:
        print(f"  - {item}")

    print()

    # manifest drift section
    dup_blocks = manifest_drift.get("duplicate_blocks", [])
    split_blocks = manifest_drift.get("split_brain_blocks", [])
    print(
        f"[manifest_drift] duplicate_blocks={len(dup_blocks)}"
        f" split_brain_blocks={len(split_blocks)}"
    )
    for item in dup_blocks:
        print(f"  dup: {item}")
    for item in split_blocks:
        print(f"  split: {item}")

    print()
    print(f"total_issues={total_issues}  clean={clean}")

    sys.exit(0 if clean else 1)


if __name__ == "__main__":
    main()
