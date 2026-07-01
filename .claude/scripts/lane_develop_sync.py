"""BL-442 AK-3: develop-Resync-Disziplin (GAP-3, SOA-2=Goal-Hook-merge-step).

Entscheidungslogik fuer den per-BL Resync-Schritt:
- nach BL-Done: if should_merge_after_bl_done: merge_seam.merge_exec(branch, develop) (CLEAN-gated, BL-425)
- vor BL-Start: if action=="pull-first": develop pullen
Verhindert Lane-Divergenz (Lane B war 4 ahead).
"""

import subprocess
from typing import Optional


def develop_sync_action(ahead: int, behind: int) -> str:
    """Entscheide was zu tun ist basierend auf (ahead, behind) der Lane ggue. develop.

    ahead==0 and behind==0 -> "in-sync"
    ahead>0  and behind==0 -> "merge"        (clean ff nach develop, per-BL-Done)
    ahead==0 and behind>0  -> "pull-first"   (develop integrieren vor BL-Start)
    ahead>0  and behind>0  -> "diverged"     (Merge/Rebase-Aufloesung noetig, HiL/coord)
    """
    if ahead == 0 and behind == 0:
        return "in-sync"
    if ahead > 0 and behind == 0:
        return "merge"
    if ahead == 0 and behind > 0:
        return "pull-first"
    # ahead > 0 and behind > 0
    return "diverged"


def should_merge_after_bl_done(ahead: int, behind: int) -> bool:
    """True nur wenn develop_sync_action(ahead, behind) == 'merge'.

    Docstring: per-BL nach Done -> if should_merge_after_bl_done:
        merge_seam.merge_exec(branch, develop) (CLEAN-gated, BL-425);
    vor BL-Start -> if action=="pull-first": develop pullen.
    Verhindert Lane-Divergenz (Lane B war 4 ahead).
    """
    return develop_sync_action(ahead, behind) == "merge"


def ahead_behind(branch: str, target: str = "develop") -> Optional[tuple[int, int]]:
    """Liefert (ahead, behind) via git rev-list --left-right --count target...branch.

    Gibt None zurueck wenn git-Aufruf fehlschlaegt.
    """
    try:
        result = subprocess.run(
            ["git", "rev-list", "--left-right", "--count", f"{target}...{branch}"],
            capture_output=True,
            text=True,
            check=True,
        )
        parts = result.stdout.strip().split()
        if len(parts) == 2:
            behind = int(parts[0])
            ahead = int(parts[1])
            return ahead, behind
        return None
    except (subprocess.CalledProcessError, ValueError, OSError):
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="develop-Resync-Disziplin: Lane-Divergenz-Check (BL-442 AK-3)"
    )
    parser.add_argument("--branch", default="HEAD", help="Lane-Branch (default: HEAD)")
    parser.add_argument("--target", default="develop", help="Ziel-Branch (default: develop)")
    parser.add_argument("--ahead", type=int, help="Manuell: Anzahl ahead-Commits")
    parser.add_argument("--behind", type=int, help="Manuell: Anzahl behind-Commits")
    args = parser.parse_args()

    if args.ahead is not None and args.behind is not None:
        a, b = args.ahead, args.behind
    else:
        result = ahead_behind(args.branch, args.target)
        if result is None:
            print("ERROR: git ahead_behind fehlgeschlagen")
            raise SystemExit(1)
        a, b = result

    action = develop_sync_action(a, b)
    merge = should_merge_after_bl_done(a, b)
    print(f"ahead={a} behind={b} -> action={action} should_merge={merge}")
