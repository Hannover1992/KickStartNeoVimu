#!/usr/bin/env python3
"""migration_readiness.py — BL-253 batch_1 (M3): Pre-Migration-Readiness-Gate.

Aggregiert 5 Checks zu einem READY/NOT_READY-Verdict, bevor ein Lane-Worktree
nach develop gemerged / migriert wird:

  C1 check_uncommitted        — Working-Tree sauber? (git status --porcelain)
  C2 check_unpushed           — keine unpushed Commits? (git rev-list @{u}..HEAD)
  C3 check_lane_divergenz     — Lane in-sync mit develop? (ahead_behind + action)
  C4 check_untracked_product  — keine untracked .py-Produkte? (?? Zeilen)
  C5 vault_sync_status        — Vault-Versionierung sauber? (teil-gated/WARN)

DRY-Reuse (KEIN Re-Implement — Identity-erhaltend re-exportiert):
  - ahead_behind, develop_sync_action  aus lane_develop_sync
  - resolve_vault_root                 aus resolve_vault_root

Reine subprocess-git-Aufrufe; kein Push/Commit. main() liefert exit 0=READY/1=NOT_READY.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# ── DRY-Reuse: Primitive importieren + als Modul-Namen re-exportieren ──────────
# Identity-Tests pruefen `mr.X is sourcemodule.X` -> direkte Re-Bindung, kein Wrap.
from lane_develop_sync import ahead_behind, develop_sync_action  # noqa: F401
from resolve_vault_root import resolve_vault_root  # noqa: F401


# ===========================================================================
# C1 — Uncommitted Working-Tree-Aenderungen
# ===========================================================================

def check_uncommitted(repo: str) -> dict:
    """green wenn das Working-Tree sauber ist (keine porcelain-Zeilen)."""
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    count = len(lines)
    return {"green": count == 0, "count": count}


# ===========================================================================
# C2 — Unpushed Commits (ahead of remote upstream)
# ===========================================================================

def check_unpushed(repo: str) -> dict:
    """green wenn keine Commits vor dem Upstream liegen.

    Kein Upstream -> git rev-list wirft CalledProcessError -> RED + status=no_upstream
    (kein Crash).
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-list", "--count", "@{u}..HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        return {"green": False, "ahead_of_remote": 0, "status": "no_upstream"}
    ahead = int(result.stdout.strip() or "0")
    return {"green": ahead == 0, "ahead_of_remote": ahead}


# ===========================================================================
# C3 — Lane-Divergenz ggue. develop (DRY-Reuse lane_develop_sync)
# ===========================================================================

def check_lane_divergenz(repo: str) -> dict:
    """green nur bei action == 'in-sync'.

    Nutzt das modul-lokale (patch-bare) ahead_behind + develop_sync_action.
    None von ahead_behind (git-Fehler) -> RED + status=git_error.
    """
    ab = ahead_behind("HEAD")
    if ab is None:
        return {"green": False, "action": None, "status": "git_error"}
    ahead, behind = ab
    action = develop_sync_action(ahead, behind)
    return {"green": action == "in-sync", "action": action}


# ===========================================================================
# C4 — Untracked Produkt-Dateien (nur .py zaehlt als Produkt)
# ===========================================================================

def check_untracked_product(repo: str) -> dict:
    """green wenn keine untracked .py-Produkte existieren.

    git status --porcelain ??-Zeilen; .md (und alles Nicht-.py) wird ignoriert.
    """
    result = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    untracked_products: list[str] = []
    for line in result.stdout.splitlines():
        if not line.startswith("??"):
            continue
        path = line[2:].strip()
        if path.endswith(".py"):
            untracked_products.append(path)
    return {"green": not untracked_products, "untracked_products": untracked_products}


# ===========================================================================
# C5 — Vault-Sync-Status (teil-gated: nicht-versionierter Vault = WARN)
# ===========================================================================

def vault_sync_status(vault_root: str) -> dict:
    """Vault-Versionierungs-Status.

    Kein .git -> status=vault_not_versioned, warn=True, blocking=False (kein hartes Fail).
    Mit .git: clean -> green=True, dirty -> green=False.
    """
    git_dir = Path(vault_root) / ".git"
    if not git_dir.exists():
        return {
            "status": "vault_not_versioned",
            "green": False,
            "warn": True,
            "blocking": False,
        }
    result = subprocess.run(
        ["git", "-C", str(vault_root), "status", "--porcelain"],
        capture_output=True,
        text=True,
    )
    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
    clean = len(lines) == 0
    return {
        "status": "clean" if clean else "dirty",
        "green": clean,
        "warn": False,
        "blocking": not clean,
    }


# ===========================================================================
# Verdict — alle 5 Checks aggregieren
# ===========================================================================

def migration_ready(repo: str, vault_root: str) -> dict:
    """Aggregiert C1..C5 zu READY/NOT_READY.

    C5 (Vault) ist teil-gated: nicht-versionierter Vault (blocking=False) blockt
    die Migration NICHT, ein dirty versionierter Vault (green=False, blocking=True)
    schon. Ein Check ist 'rot' fuers Verdict wenn er nicht green ist UND nicht
    explizit blocking=False traegt.
    """
    checks = {
        "c1": check_uncommitted(repo),
        "c2": check_unpushed(repo),
        "c3": check_lane_divergenz(repo),
        "c4": check_untracked_product(repo),
        "c5": vault_sync_status(vault_root),
    }
    red_checks: list[str] = []
    for name, res in checks.items():
        if res.get("green") is True:
            continue
        if res.get("blocking", True) is False:
            continue  # WARN-only (z.B. vault_not_versioned) blockt nicht
        red_checks.append(name)

    ready = not red_checks
    return {
        "migration_ready": ready,
        "verdict": "READY" if ready else "NOT_READY",
        "checks": checks,
        "red_checks": red_checks,
    }


# ===========================================================================
# CLI
# ===========================================================================

def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Pre-Migration-Readiness-Gate (BL-253)"
    )
    parser.add_argument("--repo", default=".", help="Repo-Pfad (default: .)")
    parser.add_argument(
        "--vault-root",
        default=None,
        help="Vault-Root (default: resolve_vault_root)",
    )
    parser.add_argument(
        "--json", action="store_true", help="JSON-only auf stdout"
    )
    args = parser.parse_args(argv)

    if args.vault_root is not None:
        vault_root = args.vault_root
    else:
        vault_root = str(resolve_vault_root())

    result = migration_ready(args.repo, vault_root)

    if args.json:
        print(json.dumps(result))
    else:
        print(f"verdict={result['verdict']}")
        for name, res in result["checks"].items():
            print(f"  {name}: {'GREEN' if res.get('green') else 'RED'} {res}")
        if result["red_checks"]:
            print(f"  red_checks: {', '.join(result['red_checks'])}")

    return 0 if result["migration_ready"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
