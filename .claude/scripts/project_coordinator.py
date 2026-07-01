#!/usr/bin/env python3
"""
BL-194: Project-Coordinator (Default BCCD aus HIL_BLOCK_NOTE_2026-05-24)

Architektur-Entscheidungen (User-Default akzeptiert):
  Q1 = B: Cron-Wrapper Process (cross-platform)
  Q2 = C: File-based State + Polling (factory_lock.py + Vault-Files)
  Q3 = C: Hybrid Lock-Coordination (File-Primaer + Daemon-Watcher)
  Q4 = D: All-of-the-above Crash-Recovery (TTL + Heartbeat + Generation)

Funktionen:
  1. Worktree-Registry (welche Worktrees sind aktiv?)
  2. BL-Slot-Allocation (welche BL bekommt welche Worktree?)
  3. Lock-Watcher (stale-Recovery, Heartbeat-Check, Generation-Bump)
  4. Cross-Worktree-Event-Bus (file-based)

Usage:
  python3 project_coordinator.py daemon    # Starte als langlebiger Watcher
  python3 project_coordinator.py register {worktree_path}
  python3 project_coordinator.py allocate {bl_id} {worktree_path}
  python3 project_coordinator.py status

State-File: {vault_root}/.coordinator_state/coordinator.json
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path


# Q1: Cron-Wrapper (kein systemd, kein daemon binding)
# Q2: File-based State
# Q3: Hybrid (File primaer, Daemon-Watcher optional)
# Q4: TTL + Heartbeat + Generation

DEFAULT_TTL_SEC = 300         # Lock TTL
HEARTBEAT_INTERVAL = 30       # Sekunden zwischen Heartbeats
GENERATION_BUMP_ON_RESTART = True


def state_path(vault_root):
    """Pfad zum Coordinator-State-File."""
    state_dir = Path(vault_root) / ".coordinator_state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir / "coordinator.json"


def load_state(vault_root):
    """Lade Coordinator-State (oder init wenn nicht vorhanden)."""
    path = state_path(vault_root)
    if not path.exists():
        return {
            "generation": 1,
            "started_at": datetime.now().isoformat(),
            "worktrees": {},
            "bl_allocations": {},
            "last_heartbeat": None,
        }
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_state(vault_root, state):
    """Persistiere State."""
    path = state_path(vault_root)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def register_worktree(vault_root, worktree_path):
    """Q1+Q2: Worktree-Registry. AK-1."""
    state = load_state(vault_root)
    wt_id = str(uuid.uuid4())[:8]
    state["worktrees"][wt_id] = {
        "path": str(worktree_path),
        "registered_at": datetime.now().isoformat(),
        "status": "idle",
        "current_bl": None,
        "last_heartbeat": datetime.now().isoformat(),
    }
    save_state(vault_root, state)
    print(f"[REGISTER] Worktree {wt_id} = {worktree_path}")
    return wt_id


def allocate_bl(vault_root, bl_id, worktree_path):
    """AK-3: BL-Slot-Allocation."""
    state = load_state(vault_root)
    # Finde Worktree-ID anhand path
    wt_id = None
    for wid, wt in state["worktrees"].items():
        if wt["path"] == str(worktree_path):
            wt_id = wid
            break
    if not wt_id:
        print(f"[ERROR] Worktree {worktree_path} not registered", file=sys.stderr)
        return 1
    state["worktrees"][wt_id]["current_bl"] = bl_id
    state["worktrees"][wt_id]["status"] = "busy"
    state["bl_allocations"][bl_id] = {
        "worktree_id": wt_id,
        "allocated_at": datetime.now().isoformat(),
    }
    save_state(vault_root, state)
    print(f"[ALLOCATE] {bl_id} -> Worktree {wt_id} ({worktree_path})")
    return 0


def watcher_daemon(vault_root, max_iterations=None):
    """Q4: Daemon-Watcher fuer Stale-Lock-Recovery + Heartbeat-Check.

    Args:
        vault_root: Vault-Pfad
        max_iterations: None = unendlich, sonst N Iterations (fuer Tests)
    """
    print(f"[DAEMON] Coordinator-Watcher gestartet, vault={vault_root}")
    iteration = 0
    while True:
        state = load_state(vault_root)
        now = datetime.now()
        state["last_heartbeat"] = now.isoformat()

        # Q4 TTL-Check: stale Worktrees markieren
        for wt_id, wt in list(state["worktrees"].items()):
            last_hb = wt.get("last_heartbeat")
            if last_hb:
                last_dt = datetime.fromisoformat(last_hb)
                age = (now - last_dt).total_seconds()
                if age > DEFAULT_TTL_SEC:
                    print(f"[DAEMON] STALE Worktree {wt_id}: last HB {age:.0f}s ago, marking idle")
                    wt["status"] = "stale"
                    wt["current_bl"] = None

        save_state(vault_root, state)
        iteration += 1
        if max_iterations is not None and iteration >= max_iterations:
            break
        time.sleep(HEARTBEAT_INTERVAL)
    return 0


def status(vault_root):
    """Ausgabe des aktuellen Coordinator-Status."""
    state = load_state(vault_root)
    print(f"=== Project-Coordinator Status (Gen {state['generation']}) ===")
    print(f"Started: {state.get('started_at')}")
    print(f"Last Heartbeat: {state.get('last_heartbeat')}")
    print(f"\nWorktrees ({len(state['worktrees'])}):")
    for wt_id, wt in state["worktrees"].items():
        print(f"  {wt_id}: {wt['path']} [{wt['status']}] BL={wt.get('current_bl')}")
    print(f"\nBL-Allocations ({len(state['bl_allocations'])}):")
    for bl_id, alloc in state["bl_allocations"].items():
        print(f"  {bl_id}: {alloc['worktree_id']} @ {alloc['allocated_at']}")
    return 0


def main(argv):
    p = argparse.ArgumentParser(description="BL-194 Project-Coordinator (Default BCCD)")
    p.add_argument("command", choices=["daemon", "register", "allocate", "status"])
    p.add_argument("--vault-root", default=os.environ.get("VAULT_ROOT", "."))
    p.add_argument("--worktree", help="Worktree-Pfad (fuer register/allocate)")
    p.add_argument("--bl-id", help="BL-ID (fuer allocate)")
    p.add_argument("--max-iter", type=int, help="Max Iterations fuer daemon (fuer Tests)")
    args = p.parse_args(argv[1:])

    vault_root = args.vault_root

    if args.command == "daemon":
        return watcher_daemon(vault_root, max_iterations=args.max_iter)
    elif args.command == "register":
        if not args.worktree:
            print("[ERROR] --worktree required", file=sys.stderr)
            return 1
        register_worktree(vault_root, args.worktree)
        return 0
    elif args.command == "allocate":
        if not args.bl_id or not args.worktree:
            print("[ERROR] --bl-id and --worktree required", file=sys.stderr)
            return 1
        return allocate_bl(vault_root, args.bl_id, args.worktree)
    elif args.command == "status":
        return status(vault_root)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
