#!/usr/bin/env python3
"""
BL-196: Multi-Machine Cross-Vault Parallel Mode (Phase B von BL-194).

Skeleton-Implementation. Erweitert project_coordinator.py um Cross-Vault
Synchronisation: zwei Vaults (z.B. auf 2 Maschinen) sync'en Lock-State + BL-Allocations
via gemeinsamem Sync-Endpunkt (file-based, z.B. NFS / SMB / Git-Repo).

Default-Decisions (von BL-194 BCCD geerbt):
  - File-based State (kein Redis)
  - Hybrid Lock-Coordination (File-Primaer + Daemon-Watcher)
  - TTL + Heartbeat + Generation Crash-Recovery

Cross-Vault Sync-Pfad:
  {sync_root}/cross_vault_index.json   (zentraler Index aller Vaults)
  {sync_root}/locks/{bl_id}.lock       (cross-vault BL-Locks)
  {sync_root}/events/{ts}_{vault}.evt   (Append-only Event-Log)

Usage:
  python3 cross_vault_sync.py register --vault-id={id} --vault-path={path} --sync-root={path}
  python3 cross_vault_sync.py acquire-bl --bl-id=BL-NNN --vault-id={id} --sync-root={path}
  python3 cross_vault_sync.py release-bl --bl-id=BL-NNN --vault-id={id} --sync-root={path}
  python3 cross_vault_sync.py list-vaults --sync-root={path}
"""

import argparse
import json
import os
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path


DEFAULT_BL_LOCK_TTL = 600  # 10 Min (Cross-Vault sollte laenger sein als Single-Vault)


def sync_paths(sync_root):
    """Init der Sync-Root-Verzeichnisstruktur."""
    sync = Path(sync_root)
    (sync / "locks").mkdir(parents=True, exist_ok=True)
    (sync / "events").mkdir(parents=True, exist_ok=True)
    return {
        "index": sync / "cross_vault_index.json",
        "locks": sync / "locks",
        "events": sync / "events",
    }


def load_index(sync_root):
    paths = sync_paths(sync_root)
    if not paths["index"].exists():
        return {"vaults": {}, "created": datetime.now().isoformat()}
    with open(paths["index"], "r", encoding="utf-8") as f:
        return json.load(f)


def save_index(sync_root, idx):
    paths = sync_paths(sync_root)
    with open(paths["index"], "w", encoding="utf-8") as f:
        json.dump(idx, f, indent=2)


def append_event(sync_root, vault_id, event_type, payload):
    """Append-only Event-Log fuer Audit-Trail."""
    paths = sync_paths(sync_root)
    ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    event_file = paths["events"] / f"{ts}_{vault_id}.evt"
    with open(event_file, "w", encoding="utf-8") as f:
        json.dump({"ts": ts, "vault_id": vault_id, "type": event_type, "payload": payload}, f)


def register_vault(sync_root, vault_id, vault_path):
    """Registriere Vault im Cross-Vault-Index."""
    idx = load_index(sync_root)
    idx["vaults"][vault_id] = {
        "path": str(vault_path),
        "registered_at": datetime.now().isoformat(),
        "last_heartbeat": datetime.now().isoformat(),
    }
    save_index(sync_root, idx)
    append_event(sync_root, vault_id, "register", {"path": str(vault_path)})
    print(f"[X-VAULT] Registered vault {vault_id} @ {vault_path}")
    return 0


def acquire_bl(sync_root, bl_id, vault_id, ttl=DEFAULT_BL_LOCK_TTL):
    """Cross-Vault BL-Lock acquire. Failed wenn anderer Vault BL haelt + TTL nicht abgelaufen."""
    paths = sync_paths(sync_root)
    lock_file = paths["locks"] / f"{bl_id}.lock"
    now = datetime.now()

    if lock_file.exists():
        with open(lock_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
        held_by = existing["vault_id"]
        held_since = datetime.fromisoformat(existing["acquired_at"])
        age = (now - held_since).total_seconds()
        if age < existing.get("ttl", DEFAULT_BL_LOCK_TTL):
            if held_by != vault_id:
                print(f"[X-VAULT] BL-Lock {bl_id} CONFLICT — held by {held_by} ({age:.0f}s)", file=sys.stderr)
                return 2
            else:
                print(f"[X-VAULT] BL-Lock {bl_id} ALREADY held by self (re-entry)")
                return 0
        else:
            print(f"[X-VAULT] BL-Lock {bl_id} STALE ({age:.0f}s > {existing.get('ttl')}s) — taking over")
            append_event(sync_root, vault_id, "lock_stale_takeover",
                         {"bl_id": bl_id, "old_holder": held_by})

    # Acquire
    with open(lock_file, "w", encoding="utf-8") as f:
        json.dump({
            "bl_id": bl_id,
            "vault_id": vault_id,
            "acquired_at": now.isoformat(),
            "ttl": ttl,
            "generation": uuid.uuid4().hex[:8],
        }, f, indent=2)
    append_event(sync_root, vault_id, "acquire_bl", {"bl_id": bl_id, "ttl": ttl})
    print(f"[X-VAULT] Acquired BL-Lock {bl_id} for vault={vault_id} (TTL={ttl}s)")
    return 0


def release_bl(sync_root, bl_id, vault_id):
    """Cross-Vault BL-Lock release. Only own locks released."""
    paths = sync_paths(sync_root)
    lock_file = paths["locks"] / f"{bl_id}.lock"
    if not lock_file.exists():
        print(f"[X-VAULT] BL-Lock {bl_id} not held — nothing to release")
        return 0
    with open(lock_file, "r", encoding="utf-8") as f:
        existing = json.load(f)
    if existing["vault_id"] != vault_id:
        print(f"[X-VAULT] BL-Lock {bl_id} held by {existing['vault_id']}, not us ({vault_id}) — refusing release",
              file=sys.stderr)
        return 3
    lock_file.unlink()
    append_event(sync_root, vault_id, "release_bl", {"bl_id": bl_id})
    print(f"[X-VAULT] Released BL-Lock {bl_id}")
    return 0


def list_vaults(sync_root):
    """List alle registrierten Vaults + ihre active locks."""
    idx = load_index(sync_root)
    paths = sync_paths(sync_root)
    print(f"=== Cross-Vault Index ({sync_root}) ===")
    print(f"\nVaults ({len(idx['vaults'])}):")
    for vid, v in idx["vaults"].items():
        print(f"  {vid}: {v['path']} (HB={v.get('last_heartbeat')})")
    locks = list(paths["locks"].glob("*.lock"))
    print(f"\nActive BL-Locks ({len(locks)}):")
    for lf in locks:
        with open(lf, "r", encoding="utf-8") as f:
            lock = json.load(f)
        age = (datetime.now() - datetime.fromisoformat(lock["acquired_at"])).total_seconds()
        print(f"  {lock['bl_id']}: vault={lock['vault_id']} age={age:.0f}s ttl={lock.get('ttl')}s")
    return 0


def main(argv):
    p = argparse.ArgumentParser(description="BL-196 Cross-Vault Sync (Phase B von BL-194)")
    p.add_argument("command", choices=["register", "acquire-bl", "release-bl", "list-vaults"])
    p.add_argument("--sync-root", required=True, help="Sync-Root (shared between Vaults)")
    p.add_argument("--vault-id", help="Eindeutige Vault-ID")
    p.add_argument("--vault-path", help="Pfad zum lokalen Vault")
    p.add_argument("--bl-id", help="BL-ID fuer acquire/release")
    p.add_argument("--ttl", type=int, default=DEFAULT_BL_LOCK_TTL, help="Lock-TTL in Sek")
    args = p.parse_args(argv[1:])

    if args.command == "register":
        if not args.vault_id or not args.vault_path:
            print("[ERROR] --vault-id and --vault-path required", file=sys.stderr)
            return 1
        return register_vault(args.sync_root, args.vault_id, args.vault_path)
    elif args.command == "acquire-bl":
        if not args.bl_id or not args.vault_id:
            print("[ERROR] --bl-id and --vault-id required", file=sys.stderr)
            return 1
        return acquire_bl(args.sync_root, args.bl_id, args.vault_id, ttl=args.ttl)
    elif args.command == "release-bl":
        if not args.bl_id or not args.vault_id:
            print("[ERROR] --bl-id and --vault-id required", file=sys.stderr)
            return 1
        return release_bl(args.sync_root, args.bl_id, args.vault_id)
    elif args.command == "list-vaults":
        return list_vaults(args.sync_root)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
