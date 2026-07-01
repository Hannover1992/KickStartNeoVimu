"""
backlog_counter_lock.py — Counter-Lock for Multi-Lane Filing Race (P2)

Serialises BL-ID allocation across concurrent workers via factory_lock.
Ensures read-increment-write is atomic: N concurrent callers get N distinct
consecutive IDs with no lost-update and no duplicates.

Module-level acquire/release imports are REQUIRED for T3 spy-patching via bcl.acquire/bcl.release.
"""

import re
import uuid
from pathlib import Path
from factory_lock import acquire, release  # noqa: F401 — T3 spy patches bcl.acquire / bcl.release

_BL_RE = re.compile(r"BL-(\d+)")


class LockTimeoutError(Exception):
    """Raised when the factory lock cannot be acquired within timeout."""
    pass


def scan_max_existing_bl(vault_root) -> int:
    """Scan vault_root for the highest existing BL number across three sources.

    Sources:
      a) Directory entries under {vault_root}/Backlog/ matching BL-(\\d+)
      b) Lines in {vault_root}/_backlog_index.md matching BL-(\\d+)
      c) Lines in {vault_root}/_backlog_index_done.md matching BL-(\\d+)

    Returns the highest integer found, or 0 if no BL numbers are found.
    Missing directories/files are silently skipped (no crash).
    """
    vault_root = Path(vault_root)
    max_bl = 0

    # Source a: Backlog/ subdirectory names
    try:
        backlog_dir = vault_root / "Backlog"
        for entry in backlog_dir.iterdir():
            m = _BL_RE.match(entry.name)
            if m:
                max_bl = max(max_bl, int(m.group(1)))
    except OSError:
        pass

    # Sources b + c: index files
    for index_file in ("_backlog_index.md", "_backlog_index_done.md"):
        try:
            text = (vault_root / index_file).read_text(encoding="utf-8")
            for m in _BL_RE.finditer(text):
                max_bl = max(max_bl, int(m.group(1)))
        except OSError:
            pass

    return max_bl


def allocate_next_bl_id(
    vault_root,
    *,
    read_counter,
    write_counter,
    lock_scope: str = "backlog_counter",
    timeout: int = 30,
    floor_provider=None,
) -> int:
    """Allocate the next BL ID atomically under a factory lock.

    1. Generate a unique worker_id per call so concurrent threads genuinely
       compete for the file lock (no shared worker_id shortcut).
    2. Acquire the lock; raise LockTimeoutError on timeout.
    3. Under the lock: read -> floor -> increment -> write (atomic triple).
       INV-COUNTER-LOCK-2 (BL-475): new = max(cur, floor_provider()) + 1 so the
       allocated ID never falls behind the real highest existing BL number.
    4. Release in finally so the lock is always freed.

    Returns the newly allocated BL ID.
    """
    worker_id = uuid.uuid4().hex  # unique per call — concurrent threads compete

    ok = acquire(
        scope=lock_scope,
        vault_root=vault_root,
        worker_id=worker_id,
        timeout=timeout,
    )
    if not ok:
        raise LockTimeoutError(
            f"Could not acquire lock scope='{lock_scope}' within {timeout}s"
        )

    try:
        cur = read_counter()
        floor = floor_provider() if floor_provider else 0
        new = max(cur, floor) + 1
        write_counter(new)
        return new
    finally:
        release(worker_id=worker_id, vault_root=vault_root)
