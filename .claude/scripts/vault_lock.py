"""
vault_lock.py — BL-334 sub_batch_1: Vault-Lock/Quiescenz-Primitiv (thin wrapper)

A vault-GLOBAL lock that lives in its OWN {vault_root}/_vault.lock file
(NOT in _factory_lock.md — INV-VAULT-LOCK-6, No-5th-Lock-Machine constraint).

Reuse over rebuild: the entire mechanism (tempfile+os.replace atomicity, stale-TTL,
heartbeat, safe-break reclaim + audit, HeartbeatDaemon) is REUSED from factory_lock
via its optional ``lock_file_name`` parameter (default unchanged -> backward-compatible).
The ONLY genuinely new pieces here are:
  - the file name + scope/purpose CONVENTION (scope="vault", file="_vault.lock")
  - the closed ``zweck`` vocabulary {health_heal, wave_fanin} (AK-4), written into
    factory_lock's ``purpose`` field (Dual-Use: same mechanism, zweck distinguishes
    health-heal vs. 230-wave-fan-in).

Dual-Use (INV-VAULT-LOCK-1/3, AK-4):
  - zweck="health_heal" : BL-335 healer holds the lock during destructive healing
                          (long hold + HeartbeatDaemon, INV-VAULT-LOCK-4).
  - zweck="wave_fanin"  : BL-230 wave-barrier holds it briefly at the fan-in to write
                          the truth as Single-Writer-Observable.

Scope notes (forward-dependencies, NOT built here — sub_batch_1):
  - the /_health heal-caller (AK-3) = BL-335, NOT here.
  - the Write-Seam hook guard_vault_write_lock.py (AK-2) = sub_batch_2, NOT here.

Usage:
    py -3 vault_lock.py acquire --zweck=health_heal --ttl=1800 --worker-id=heal-123
    py -3 vault_lock.py release --worker-id=heal-123
    py -3 vault_lock.py heartbeat --worker-id=heal-123
    py -3 vault_lock.py status
"""

import os
import sys
import argparse
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

import factory_lock as _fl
from factory_lock import VAULT_ROOT, DEFAULT_TTL, DEFAULT_TIMEOUT  # noqa: F401  (re-export)


# ── Vault-Lock-Konvention (the only genuinely new constants — INV-VAULT-LOCK-6) ──
VAULT_LOCK_FILE_NAME = "_vault.lock"
VAULT_SCOPE = "vault"

# Generous default for a long destructive heal (Slim/Migration/Kollaps), OQ-8.
# HeartbeatDaemon keeps it alive; TTL is the safe-break ceiling if the heal dies.
DEFAULT_HEAL_TTL = 1800  # 30 min

# AK-4: closed zweck vocabulary (validated; unknown -> ValueError / fail-loud).
ZWECK_VOCABULARY = ("health_heal", "wave_fanin")


def _validate_zweck(zweck: str) -> None:
    """Fail-loud on unknown zweck (AK-4 closed set)."""
    if zweck not in ZWECK_VOCABULARY:
        raise ValueError(
            f"vault_lock: unknown zweck={zweck!r}; "
            f"allowed: {', '.join(ZWECK_VOCABULARY)}"
        )


def _vault_lock_file_path(vault_root: Optional[Path] = None) -> Path:
    """Path to the SEPARATE {vault_root}/_vault.lock file."""
    return _fl._lock_file_path(vault_root, VAULT_LOCK_FILE_NAME)


def acquire(
    zweck: str,
    ttl: int = DEFAULT_HEAL_TTL,
    worker_id: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    vault_root: Optional[Path] = None,
) -> bool:
    """
    Acquire the vault-global lock for the given zweck.
    zweck is validated against the closed vocabulary and written into the
    lock's ``purpose`` field. scope is always "vault".
    Mechanism (atomicity/stale/reclaim) is reused from factory_lock.

    Returns True on success, False on timeout / lock held by other.
    Raises ValueError on unknown zweck.
    """
    _validate_zweck(zweck)
    return _fl.acquire(
        scope=VAULT_SCOPE,
        ttl=ttl,
        worker_id=worker_id,
        timeout=timeout,
        purpose=zweck,
        vault_root=vault_root,
        lock_file_name=VAULT_LOCK_FILE_NAME,
    )


def release(worker_id: str, vault_root: Optional[Path] = None) -> bool:
    """Release the vault lock (only the holder can). Reused from factory_lock."""
    return _fl.release(
        worker_id=worker_id,
        vault_root=vault_root,
        lock_file_name=VAULT_LOCK_FILE_NAME,
    )


def heartbeat(worker_id: str, vault_root: Optional[Path] = None) -> bool:
    """Update heartbeat_at for the vault-lock holder. Reused from factory_lock."""
    return _fl.heartbeat(
        worker_id=worker_id,
        vault_root=vault_root,
        lock_file_name=VAULT_LOCK_FILE_NAME,
    )


def is_locked(vault_root: Optional[Path] = None) -> Optional[dict]:
    """
    Return holder info dict if a non-stale vault lock is active, else None.
    Filters on scope="vault". Stale locks treated as unlocked (INV-LOCK-2).
    """
    return _fl.is_locked(
        scope=VAULT_SCOPE,
        vault_root=vault_root,
        lock_file_name=VAULT_LOCK_FILE_NAME,
    )


def force_release(vault_root: Optional[Path] = None) -> bool:
    """Admin: unconditionally release the vault lock. Reused from factory_lock."""
    return _fl.force_release(
        scope=VAULT_SCOPE,
        vault_root=vault_root,
        lock_file_name=VAULT_LOCK_FILE_NAME,
    )


class HeartbeatDaemon(_fl.HeartbeatDaemon):
    """
    Background heartbeat thread bound to the _vault.lock file (INV-VAULT-LOCK-4).
    Reuses factory_lock.HeartbeatDaemon; only pins lock_file_name to _vault.lock.
    """

    def __init__(self, worker_id: str, interval: int = _fl.HEARTBEAT_INTERVAL,
                 vault_root: Optional[Path] = None):
        super().__init__(
            worker_id=worker_id,
            interval=interval,
            vault_root=vault_root,
            lock_file_name=VAULT_LOCK_FILE_NAME,
        )


# ── CLI ────────────────────────────────────────────────────────────────────────

def _cli_main():
    parser = argparse.ArgumentParser(description="Vault Lock CLI (BL-334)")
    sub = parser.add_subparsers(dest="command")

    p_acquire = sub.add_parser("acquire")
    # AK-4: --zweck primary CLI alias; --purpose accepted as synonym.
    p_acquire.add_argument("--zweck", "--purpose", dest="zweck", default=None,
                           help=f"one of: {', '.join(ZWECK_VOCABULARY)}")
    p_acquire.add_argument("--ttl", type=int, default=DEFAULT_HEAL_TTL)
    p_acquire.add_argument("--worker-id", default=None)
    p_acquire.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)

    p_release = sub.add_parser("release")
    p_release.add_argument("--worker-id", required=True)

    p_hb = sub.add_parser("heartbeat")
    p_hb.add_argument("--worker-id", required=True)

    p_fr = sub.add_parser("force-release")

    sub.add_parser("status")

    args = parser.parse_args()

    if args.command == "acquire":
        if not args.zweck:
            print("[VAULT-LOCK] ERROR: --zweck required "
                  f"({', '.join(ZWECK_VOCABULARY)})", file=sys.stderr)
            sys.exit(2)
        try:
            ok = acquire(zweck=args.zweck, ttl=args.ttl,
                         worker_id=args.worker_id, timeout=args.timeout)
        except ValueError as e:
            print(f"[VAULT-LOCK] ERROR: {e}", file=sys.stderr)
            sys.exit(2)
        sys.exit(0 if ok else 1)

    elif args.command == "release":
        ok = release(worker_id=args.worker_id)
        if not ok:
            print(f"[VAULT-LOCK] ERROR: Not the holder or lock not held by "
                  f"{args.worker_id}", file=sys.stderr)
        sys.exit(0 if ok else 1)

    elif args.command == "heartbeat":
        ok = heartbeat(worker_id=args.worker_id)
        sys.exit(0 if ok else 1)

    elif args.command == "force-release":
        force_release()
        sys.exit(0)

    elif args.command == "status":
        info = is_locked()
        if info:
            print(f"VAULT LOCKED by {info['holder']} since {info['acquired_at']} "
                  f"(zweck={info['purpose']}, ttl={info['ttl_seconds']}s, "
                  f"heartbeat={info['heartbeat_at']})")
        else:
            print("VAULT UNLOCKED")
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
