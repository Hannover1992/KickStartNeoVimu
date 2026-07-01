"""
factory_lock.py — BL-175 + BL-194: BDF Factory-Lock-Mechanismus

Atomic lock-file based coordination for multi-BDF parallelism.
Lock-File: {vault_root}/_factory_lock.md (YAML-Frontmatter + Markdown-Log)

BL-175: Factory-level locking (global scope, file-based).
BL-194: BL-level locking (mkdir-pattern in .locks/BL-{NNN}.lock/).

INV-LOCK-1: Acquire and release are atomic (tempfile + os.replace).
INV-LOCK-2: Stale-detection via TTL: now > acquired_at + ttl_seconds -> auto-release.
INV-LOCK-3: Single-writer per scope at any time.
INV-PC-2 (BL-194): PC schreibt .locks/; Worker schreibt nur heartbeat.txt + phase.txt.
INV-PC-4 (BL-194): Heartbeat-Intervall 60s; stale > 300s same-machine.
INV-PC-9 (BL-194): Stale-Reclaim NUR durch PC, nie durch Worker direkt.

Usage (BL-175 Factory-Lock):
    py -3 factory_lock.py acquire --scope=global --ttl=300 --worker-id=terminal-123
    py -3 factory_lock.py release --worker-id=terminal-123
    py -3 factory_lock.py heartbeat --worker-id=terminal-123
    py -3 factory_lock.py status
    py -3 factory_lock.py force-release --scope=global

Usage (BL-194 BL-Locks):
    py -3 factory_lock.py acquire-bl BL-179 --worker-id=claude-sess-abc123 --ttl=600
    py -3 factory_lock.py release-bl BL-179 --worker-id=claude-sess-abc123
    py -3 factory_lock.py heartbeat-bl BL-179 --worker-id=claude-sess-abc123
    py -3 factory_lock.py status-bl BL-179
    py -3 factory_lock.py list-bl-locks
    py -3 factory_lock.py reclaim-stale-bl-locks  (PC-only, INV-PC-9)
"""

import os
import sys
import time
import threading
import argparse
import random
import string
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    # Minimal YAML parser/writer for simple frontmatter
    yaml = None


VAULT_ROOT = Path(os.environ.get("VAULT_ROOT", "C:/Users/Administrator/Documents/OmniCommand"))
LOCK_FILE_NAME = "_factory_lock.md"
DEFAULT_TTL = 300       # 5 minutes
DEFAULT_TIMEOUT = 60    # 60 seconds to wait for lock
HEARTBEAT_INTERVAL = 30 # seconds

# In-process threading lock to serialize acquire/release within the same process.
# The file-based lock handles multi-process coordination.
_process_lock = threading.Lock()


class LockFileError(Exception):
    """Raised when lock-file operations fail."""
    pass


def _lock_file_path(vault_root: Optional[Path] = None,
                    lock_file_name: Optional[str] = None) -> Path:
    root = vault_root or VAULT_ROOT
    return root / (lock_file_name or LOCK_FILE_NAME)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(s: str) -> datetime:
    s = s.strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    return datetime.fromisoformat(s)


def _generate_worker_id() -> str:
    rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"terminal-{os.getpid()}-{rand}"


def _parse_frontmatter(content: str) -> dict:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    fm_text = content[3:end].strip()
    if yaml is not None:
        try:
            return yaml.safe_load(fm_text) or {}
        except Exception:
            return {}
    # Minimal YAML parser for simple key: value pairs
    result = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip().strip('"').strip("'")
            try:
                result[key.strip()] = int(val)
            except ValueError:
                result[key.strip()] = val
    return result


def _build_content(data: dict, log_entries: list) -> str:
    """Build lock-file markdown content from data dict and log entries."""
    lines = ["---"]
    for key, val in data.items():
        if isinstance(val, str):
            lines.append(f'{key}: "{val}"')
        else:
            lines.append(f"{key}: {val}")
    lines.append("---")
    lines.append("")
    lines.append("# Factory Lock Log")
    lines.append("")
    for entry in log_entries:
        lines.append(f"- {entry}")
    return "\n".join(lines) + "\n"


def _read_lock(lock_path: Path) -> tuple[dict, list]:
    """Read lock file, return (frontmatter_dict, log_lines)."""
    if not lock_path.exists():
        return {}, []
    try:
        content = lock_path.read_text(encoding="utf-8")
    except OSError:
        return {}, []
    fm = _parse_frontmatter(content)
    # Parse log lines
    log_lines = []
    in_log = False
    for line in content.splitlines():
        if line.strip() == "# Factory Lock Log":
            in_log = True
            continue
        if in_log and line.startswith("- "):
            log_lines.append(line[2:])
    return fm, log_lines


def _atomic_write(lock_path: Path, content: str) -> None:
    """Atomically write content to lock_path using tempfile + os.replace."""
    tmp_path = str(lock_path) + f".tmp.{os.getpid()}.{threading.get_ident()}"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(lock_path))
    except OSError as e:
        # Clean up tmp if it exists
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise LockFileError(f"Atomic write failed: {e}") from e


def _is_stale(fm: dict) -> bool:
    """Return True if lock is stale (now > acquired_at + ttl_seconds)."""
    if not fm.get("holder"):
        return True
    if fm.get("stage") == "RELEASED":
        return True
    try:
        acquired_at = _parse_iso(str(fm.get("acquired_at", "")))
        ttl = int(fm.get("ttl_seconds", DEFAULT_TTL))
        return datetime.now(timezone.utc) > acquired_at + timedelta(seconds=ttl)
    except (ValueError, TypeError):
        return True


def is_locked(scope: str = "global", vault_root: Optional[Path] = None,
              lock_file_name: Optional[str] = None) -> Optional[dict]:
    """
    Return holder info dict if lock is active, None otherwise.
    INV-LOCK-2: stale locks are treated as unlocked.
    """
    lock_path = _lock_file_path(vault_root, lock_file_name)
    fm, _ = _read_lock(lock_path)
    if not fm.get("holder"):
        return None
    if fm.get("scope", "global") != scope:
        return None
    if fm.get("stage") == "RELEASED":
        return None
    if _is_stale(fm):
        return None
    return {
        "holder": fm["holder"],
        "acquired_at": fm.get("acquired_at"),
        "ttl_seconds": fm.get("ttl_seconds", DEFAULT_TTL),
        "heartbeat_at": fm.get("heartbeat_at"),
        "scope": fm.get("scope", "global"),
        "purpose": fm.get("purpose", ""),
        "stage": fm.get("stage", ""),
    }


def acquire(
    scope: str = "global",
    ttl: int = DEFAULT_TTL,
    worker_id: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT,
    purpose: str = "BDF",
    stage: str = "SCANNING",
    vault_root: Optional[Path] = None,
    lock_file_name: Optional[str] = None,
) -> bool:
    """
    Acquire the factory lock.
    INV-LOCK-1: atomic write via tempfile+os.replace.
    INV-LOCK-3: single-writer per scope.
    Returns True on success, False on timeout.
    """
    if worker_id is None:
        worker_id = _generate_worker_id()

    lock_path = _lock_file_path(vault_root, lock_file_name)
    start = time.monotonic()
    attempt = 0
    backoff_steps = [1, 2, 4, 8, 30]

    while True:
        need_wait = False
        with _process_lock:
            fm, log_lines = _read_lock(lock_path)
            current_holder = fm.get("holder", "")
            current_scope = fm.get("scope", "global")
            is_released = not current_holder or fm.get("stage") == "RELEASED"

            if is_released or current_scope != scope or _is_stale(fm):
                if not is_released and current_holder and current_scope == scope:
                    old_holder = current_holder
                    old_age = int((datetime.now(timezone.utc) - _parse_iso(str(fm.get("acquired_at", _now_iso())))).total_seconds())
                    print(f"[BDF-LOCK] Stale lock detected (holder={old_holder}, age={old_age}s > ttl={fm.get('ttl_seconds', DEFAULT_TTL)}s) — reclaiming")
                    _emit_audit("LOCK_STALE_RECLAIM", {"old_holder": old_holder, "scope": scope, "worker_id": worker_id})

                # Acquire
                now = _now_iso()
                data = {
                    "holder": worker_id,
                    "acquired_at": now,
                    "ttl_seconds": ttl,
                    "heartbeat_at": now,
                    "scope": scope,
                    "purpose": purpose,
                    "stage": stage,
                }
                new_log = log_lines[-50:]  # Keep last 50 entries
                new_log.append(f"{now} ACQUIRED by {worker_id} (scope={scope}, ttl={ttl}s, purpose={purpose})")
                content = _build_content(data, new_log)
                _atomic_write(lock_path, content)
                print(f"[BDF-LOCK] Lock acquired (scope={scope}, worker={worker_id})")
                _emit_audit("LOCK_CLAIMED", {"scope": scope, "worker_id": worker_id, "ttl": ttl})
                return True

            else:
                # Lock is held by someone else
                elapsed = time.monotonic() - start
                if elapsed >= timeout:
                    print(f"[BDF-LOCK] Timeout acquiring lock after {timeout}s")
                    return False
                hold_age = int((datetime.now(timezone.utc) - _parse_iso(str(fm.get("acquired_at", _now_iso())))).total_seconds())
                print(f"[BDF-LOCK] Warte auf {current_holder} (lock_held_for={hold_age}s, ttl={fm.get('ttl_seconds', DEFAULT_TTL)}s)")
                need_wait = True

        if need_wait:
            wait = backoff_steps[min(attempt, len(backoff_steps) - 1)]
            remaining = timeout - (time.monotonic() - start)
            if remaining <= 0:
                return False
            time.sleep(min(wait, remaining))
            attempt += 1


def release(worker_id: str, vault_root: Optional[Path] = None,
            lock_file_name: Optional[str] = None) -> bool:
    """
    Release the factory lock.
    Only the current holder can release.
    Returns True if released, False if not the holder.
    """
    lock_path = _lock_file_path(vault_root, lock_file_name)
    fm, log_lines = _read_lock(lock_path)

    if fm.get("holder") != worker_id:
        return False

    now = _now_iso()
    data = {
        "holder": "",
        "acquired_at": fm.get("acquired_at", now),
        "ttl_seconds": fm.get("ttl_seconds", DEFAULT_TTL),
        "heartbeat_at": now,
        "scope": fm.get("scope", "global"),
        "purpose": "",
        "stage": "RELEASED",
    }
    new_log = log_lines[-50:]
    new_log.append(f"{now} RELEASED by {worker_id}")
    content = _build_content(data, new_log)
    _atomic_write(lock_path, content)
    print(f"[BDF-LOCK] Lock released (scope={fm.get('scope', 'global')}, worker={worker_id})")
    _emit_audit("LOCK_RELEASED", {"scope": fm.get("scope", "global"), "worker_id": worker_id})
    return True


def heartbeat(worker_id: str, vault_root: Optional[Path] = None,
              lock_file_name: Optional[str] = None) -> bool:
    """
    Update heartbeat_at for the current lock holder.
    Returns True if heartbeat updated, False if not the holder.
    """
    lock_path = _lock_file_path(vault_root, lock_file_name)
    fm, log_lines = _read_lock(lock_path)

    if fm.get("holder") != worker_id:
        return False
    if fm.get("stage") == "RELEASED":
        return False

    now = _now_iso()
    data = {k: v for k, v in fm.items()}
    data["heartbeat_at"] = now
    new_log = log_lines[-50:]
    new_log.append(f"{now} HEARTBEAT {worker_id}")
    content = _build_content(data, new_log)
    _atomic_write(lock_path, content)
    _emit_audit("LOCK_HEARTBEAT", {"worker_id": worker_id})
    return True


def force_release(scope: str = "global", vault_root: Optional[Path] = None,
                  lock_file_name: Optional[str] = None) -> bool:
    """
    Admin: unconditionally release the lock.
    """
    lock_path = _lock_file_path(vault_root, lock_file_name)
    fm, log_lines = _read_lock(lock_path)
    now = _now_iso()
    old_holder = fm.get("holder", "none")
    data = {
        "holder": "",
        "acquired_at": now,
        "ttl_seconds": fm.get("ttl_seconds", DEFAULT_TTL),
        "heartbeat_at": now,
        "scope": scope,
        "purpose": "",
        "stage": "RELEASED",
    }
    new_log = log_lines[-50:]
    new_log.append(f"{now} FORCE_RELEASED (was: {old_holder})")
    content = _build_content(data, new_log)
    _atomic_write(lock_path, content)
    print(f"[BDF-LOCK] Force-released (was: {old_holder})")
    _emit_audit("LOCK_FORCE_RELEASED", {"old_holder": old_holder, "scope": scope})
    return True


def _emit_audit(event_type: str, data: dict) -> None:
    """Emit audit event to audit.jsonl."""
    try:
        import json
        audit_path = Path(os.environ.get("REPO_ROOT", "C:/Users/Administrator/Documents/Projekt/OmniCommand/OmniCommand")) / ".claude" / "audit" / "audit.jsonl"
        if audit_path.parent.exists():
            entry = {
                "ts": _now_iso(),
                "event": event_type,
                "source": "factory_lock",
                **data,
            }
            with open(str(audit_path), "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
    except Exception:
        pass  # Audit failure must not block lock operation


class HeartbeatDaemon(threading.Thread):
    """
    Background thread that sends periodic heartbeats while lock is held.
    AK-5: Stops automatically on release() or stop().
    """

    def __init__(
        self,
        worker_id: str,
        interval: int = HEARTBEAT_INTERVAL,
        vault_root: Optional[Path] = None,
        lock_file_name: Optional[str] = None,
    ):
        super().__init__(daemon=True, name=f"hb-{worker_id}")
        self.worker_id = worker_id
        self.interval = interval
        self.vault_root = vault_root
        self.lock_file_name = lock_file_name
        self._stop_event = threading.Event()

    def run(self):
        while not self._stop_event.wait(timeout=self.interval):
            ok = heartbeat(self.worker_id, vault_root=self.vault_root,
                           lock_file_name=self.lock_file_name)
            if not ok:
                # Not the holder anymore — stop
                break

    def stop(self):
        self._stop_event.set()


# ── BL-194: BL-Level Locks (mkdir-Pattern) ──────────────────────────────────
# INV-PC-2: PC creates lock dir; Worker only writes heartbeat.txt + phase.txt
# INV-PC-4: stale > 300s same-machine
# INV-PC-9: Stale-Reclaim only by PC, never Worker

BL_LOCKS_DIR = ".locks"
BL_LOCK_STALE_SECONDS = 300       # 5 min same-machine (INV-PC-4)
BL_HEARTBEAT_INTERVAL = 60        # 60s (OQ-1 resolution)
BL_PT_PROMOTION_LOCK_DIR = ".locks/_pt_promotion.lock"

_BL_LOCK_REQUIRED_FILES = ["owner.txt", "host.txt", "worktree.txt",
                            "started.txt", "heartbeat.txt", "phase.txt"]


def _bl_locks_root(vault_root: Optional[Path] = None) -> Path:
    root = vault_root or VAULT_ROOT
    return root / BL_LOCKS_DIR


def _bl_lock_dir(bl_id: str, vault_root: Optional[Path] = None) -> Path:
    return _bl_locks_root(vault_root) / f"{bl_id}.lock"


def _robust_rmtree(lock_dir: Path, attempts: int = 5) -> bool:
    """BL-344: remove a BL-lock dir Windows-robustly (BL-328 SB4 'gone-Wahrheit').

    shutil.rmtree(ignore_errors=True) on Windows can transiently fail on an
    individual file (handle/AV/timing) and silently leave the dir half-populated
    (e.g. heartbeat.txt only). Such a leftover is fresh -> non-stale -> un-acquirable
    AND owner-less -> un-releasable = a permanent dead-lock until the 300s stale
    timeout. Retry the rmtree and verify the dir is actually GONE before returning.

    Returns True if the dir no longer exists, False if it stubbornly survived.
    """
    import shutil
    for i in range(attempts):
        if not lock_dir.exists():
            return True
        shutil.rmtree(str(lock_dir), ignore_errors=True)
        if not lock_dir.exists():
            return True
        time.sleep(0.01 * (i + 1))
    return not lock_dir.exists()


def acquire_bl(
    bl_id: str,
    worker_id: str,
    ttl: int = 600,
    worktree: str = "",
    phase: str = "A.init",
    vault_root: Optional[Path] = None,
) -> bool:
    """
    Acquire a BL-level lock via mkdir-Pattern (BL-194 AK-2, INV-PC-2).
    Creates {vault_root}/.locks/{bl_id}.lock/ directory with metadata files.

    Returns True on success, False if lock already held (non-stale).
    Only PC should call this (INV-PC-2 — PC writes .locks/).
    """
    lock_dir = _bl_lock_dir(bl_id, vault_root)
    locks_root = _bl_locks_root(vault_root)

    # Ensure .locks/ parent exists
    locks_root.mkdir(parents=True, exist_ok=True)

    # BL-344 AK-3: serialize the acquire/reclaim decision within this process so
    # intra-process threads can't both win the mkdir/reclaim race. is_bl_stale()
    # does NOT take _process_lock -> no re-entrant deadlock (verified).
    with _process_lock:
        try:
            lock_dir.mkdir(exist_ok=False)  # Atomic: fails if exists
        except FileExistsError:
            # Lock exists — check if stale
            if is_bl_stale(bl_id, vault_root=vault_root):
                # Stale: reclaim (INV-PC-9 — caller must be PC)
                _robust_rmtree(lock_dir)
                # BL-344 AK-1 (Race B): another process/thread may have reclaimed
                # this lock between our rmtree and remkdir. A lost remkdir race means
                # someone else now holds the freshly-reclaimed lock -> don't crash on
                # the uncaught FileExistsError, return a clean False instead.
                try:
                    lock_dir.mkdir(exist_ok=False)
                except FileExistsError:
                    print(f"[BL-LOCK] {bl_id} reclaim lost to concurrent acquire")
                    return False
                print(f"[BL-LOCK] Stale lock for {bl_id} reclaimed")
                _emit_audit("BL_LOCK_STALE_RECLAIM", {"bl_id": bl_id, "worker_id": worker_id})
            else:
                print(f"[BL-LOCK] {bl_id} already locked (non-stale)")
                return False

        now = _now_iso()
        import socket
        try:
            hostname = socket.gethostname()
        except Exception:
            hostname = "unknown"

        # Write AK-2 required files. BL-344 AK-2(a): write heartbeat.txt (+ started.txt)
        # FIRST, before the other metadata, so the no-heartbeat window — during which
        # is_bl_stale would otherwise see lock_dir-without-heartbeat — is minimal.
        (lock_dir / "started.txt").write_text(now, encoding="utf-8")
        (lock_dir / "heartbeat.txt").write_text(now, encoding="utf-8")
        (lock_dir / "owner.txt").write_text(worker_id, encoding="utf-8")
        (lock_dir / "host.txt").write_text(hostname, encoding="utf-8")
        (lock_dir / "worktree.txt").write_text(worktree or str(Path.cwd()), encoding="utf-8")
        (lock_dir / "phase.txt").write_text(phase, encoding="utf-8")

        print(f"[BL-LOCK] Acquired lock for {bl_id} (worker={worker_id})")
        _emit_audit("BL_LOCK_ACQUIRED", {"bl_id": bl_id, "worker_id": worker_id, "phase": phase})
        return True


def force_release_bl(
    bl_id: str,
    *,
    vault_root: Optional[Path] = None,
) -> bool:
    """Unconditionally remove the BL-lock dir — no Owner-Check (privileged/Crash-Recovery).

    Generalisiert force_release auf BL/Ressourcen-Ebene (BL-368). Entfernt
    {bl_id}.lock UNCONDITIONAL via _robust_rmtree. Idempotent: liefert True auch
    wenn das Dir nicht existierte. Das ist der proper home fuer die rmtree-Mechanik
    (NICHT in der Fassade resource_allocator.py).

    Returns True always (including when the dir did not exist = already free).
    """
    lock_dir = _bl_lock_dir(bl_id, vault_root)
    if not lock_dir.exists():
        return True
    _robust_rmtree(lock_dir)
    _emit_audit("BL_LOCK_FORCE_RELEASED", {"bl_id": bl_id})
    return True


def release_bl(
    bl_id: str,
    worker_id: str,
    vault_root: Optional[Path] = None,
) -> bool:
    """
    Release a BL-level lock.
    Only the owning worker can release (INV-PC-2).
    Returns True if released, False if not the owner.
    """
    lock_dir = _bl_lock_dir(bl_id, vault_root)

    if not lock_dir.exists():
        return False

    try:
        owner = (lock_dir / "owner.txt").read_text(encoding="utf-8").strip()
    except OSError:
        owner = ""

    if owner != worker_id:
        print(f"[BL-LOCK] ERROR: {worker_id} is not the owner of {bl_id}.lock (owner={owner})",
              file=sys.stderr)
        return False

    # BL-344: Windows-robust removal — a half-removed dir (e.g. heartbeat.txt only)
    # is fresh-non-stale yet owner-less = a permanent dead-lock for waiters.
    _robust_rmtree(lock_dir)
    print(f"[BL-LOCK] Released lock for {bl_id}")
    _emit_audit("BL_LOCK_RELEASED", {"bl_id": bl_id, "worker_id": worker_id})
    return True


def heartbeat_bl(
    bl_id: str,
    worker_id: str,
    vault_root: Optional[Path] = None,
) -> bool:
    """
    Update heartbeat.txt for an active BL-lock.
    Worker is allowed to write ONLY heartbeat.txt + phase.txt (INV-PC-2).
    Returns True if updated, False if not the owner or lock missing.
    """
    lock_dir = _bl_lock_dir(bl_id, vault_root)

    if not lock_dir.exists():
        return False

    try:
        owner = (lock_dir / "owner.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return False

    if owner != worker_id:
        return False

    (lock_dir / "heartbeat.txt").write_text(_now_iso(), encoding="utf-8")
    _emit_audit("BL_LOCK_HEARTBEAT", {"bl_id": bl_id, "worker_id": worker_id})
    return True


def update_bl_phase(
    bl_id: str,
    worker_id: str,
    phase: str,
    vault_root: Optional[Path] = None,
) -> bool:
    """
    Update phase.txt for an active BL-lock.
    Worker is allowed to write ONLY heartbeat.txt + phase.txt (INV-PC-2).
    Format: {Pipeline}.phase{N} or A.init, e.g. 'SDF.phase3', 'A.init', 'DONE'
    """
    lock_dir = _bl_lock_dir(bl_id, vault_root)

    if not lock_dir.exists():
        return False

    try:
        owner = (lock_dir / "owner.txt").read_text(encoding="utf-8").strip()
    except OSError:
        return False

    if owner != worker_id:
        return False

    (lock_dir / "phase.txt").write_text(phase, encoding="utf-8")
    return True


def is_bl_stale(
    bl_id: str,
    timeout: int = BL_LOCK_STALE_SECONDS,
    vault_root: Optional[Path] = None,
) -> bool:
    """
    Return True if BL-lock heartbeat is older than timeout seconds.
    INV-PC-4: stale > 300s same-machine.
    """
    lock_dir = _bl_lock_dir(bl_id, vault_root)
    heartbeat_file = lock_dir / "heartbeat.txt"

    if not lock_dir.exists():
        return True  # No lock = treat as stale (caller should check exists first)

    if not heartbeat_file.exists():
        # BL-344 AK-2(b): lock_dir exists but heartbeat.txt is not written yet.
        # Do NOT blindly call it stale — a concurrent acquire_bl that just won the
        # mkdir is in this exact window (forming lock). Use the dir's own mtime as an
        # age fallback: a young dir = forming/live lock (NOT stale); only an old dir
        # without a heartbeat (crash-before-write) is genuinely stale.
        try:
            age = (datetime.now(timezone.utc).timestamp() - lock_dir.stat().st_mtime)
        except OSError:
            return True
        return age > timeout

    try:
        ts_str = heartbeat_file.read_text(encoding="utf-8").strip()
        ts = _parse_iso(ts_str)
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        return age > timeout
    except Exception:
        return True


def get_bl_lock_info(
    bl_id: str,
    vault_root: Optional[Path] = None,
) -> Optional[dict]:
    """
    Return info dict for a BL-lock if it exists and is non-stale, else None.
    """
    lock_dir = _bl_lock_dir(bl_id, vault_root)

    if not lock_dir.exists():
        return None

    if is_bl_stale(bl_id, vault_root=vault_root):
        return None

    def _read(fname: str) -> str:
        try:
            return (lock_dir / fname).read_text(encoding="utf-8").strip()
        except OSError:
            return ""

    return {
        "bl_id": bl_id,
        "owner": _read("owner.txt"),
        "host": _read("host.txt"),
        "worktree": _read("worktree.txt"),
        "started": _read("started.txt"),
        "heartbeat": _read("heartbeat.txt"),
        "phase": _read("phase.txt"),
    }


def list_active_bl_locks(vault_root: Optional[Path] = None) -> list:
    """
    Return list of non-stale BL-lock info dicts currently in .locks/.
    Used by PC for Dispatch-Set-Berechnung and Heartbeat-Loop.
    """
    locks_root = _bl_locks_root(vault_root)
    if not locks_root.exists():
        return []

    result = []
    for item in locks_root.iterdir():
        if not item.is_dir() or not item.name.endswith(".lock"):
            continue
        if item.name.startswith("_"):
            continue  # Skip _master.lock, _pt_promotion.lock
        bl_id = item.name[:-5]  # Strip .lock suffix
        info = get_bl_lock_info(bl_id, vault_root=vault_root)
        if info:
            result.append(info)
    return result


def reclaim_stale_bl_locks(vault_root: Optional[Path] = None) -> list:
    """
    PC-only: scan .locks/ for stale BL-locks and reclaim them.
    INV-PC-9: Stale-Reclaim ONLY by PC, never by Worker.
    Returns list of reclaimed bl_ids.
    """
    import shutil
    locks_root = _bl_locks_root(vault_root)
    if not locks_root.exists():
        return []

    reclaimed = []
    for item in locks_root.iterdir():
        if not item.is_dir() or not item.name.endswith(".lock"):
            continue
        if item.name.startswith("_"):
            continue

        bl_id = item.name[:-5]
        if is_bl_stale(bl_id, vault_root=vault_root):
            try:
                heartbeat_file = item / "heartbeat.txt"
                stale_age = 9999
                if heartbeat_file.exists():
                    ts_str = heartbeat_file.read_text(encoding="utf-8").strip()
                    ts = _parse_iso(ts_str)
                    stale_age = int((datetime.now(timezone.utc) - ts).total_seconds())
                shutil.rmtree(str(item), ignore_errors=True)
                reclaimed.append(bl_id)
                print(f"[BL-LOCK] Reclaimed stale lock: {bl_id} (age={stale_age}s)")
                _emit_audit("BL_LOCK_STALE_RECLAIM", {
                    "bl_id": bl_id,
                    "stale_age_seconds": stale_age,
                    "stale_age_minutes": round(stale_age / 60, 1),
                })
            except Exception as e:
                print(f"[BL-LOCK] WARN: Could not reclaim {bl_id}: {e}", file=sys.stderr)

    return reclaimed


# ── BL-320: PT/SL Promotion-Mutex (thin wrapper over BL-Locks) ───────────────
# One shared promotion lock (bl_id="_pt_promotion") so two parallel batches never
# promote into the same Library (PatternLibrary / SemanticLibrary) simultaneously.
# REUSES acquire_bl/release_bl/is_bl_stale -> stale-reclaim (AK-3) comes for free.
# PT and SL share THIS ONE lock -> they serialize against each other.

def pre_work_sanity(bl_id: str, completed_bls) -> tuple:
    """BL-194-N10, INV-PC-12: Prueft ob bl_id bereits in completed_bls.

    completed_bls None/leer -> (False, "").
    bl_id.strip() in {c.strip() for c in completed_bls} -> (True, reason).
    sonst -> (False, "").
    """
    if not completed_bls:
        return (False, "")
    stripped_id = bl_id.strip()
    completed_set = {c.strip() for c in completed_bls}
    if stripped_id in completed_set:
        reason = f"{stripped_id} ist bereits in completed_bls — Doppel-Build verhindert (INV-PC-12)"
        return (True, reason)
    return (False, "")


import contextlib

PROMOTION_LOCK_BL_ID = "_pt_promotion"


def acquire_promotion_lock(
    worker_id: str,
    ttl: int = 600,
    vault_root: Optional[Path] = None,
    phase: str = "promote",
) -> bool:
    """
    Acquire the shared PT/SL promotion lock (BL-320).
    Delegates to acquire_bl(bl_id="_pt_promotion", ...) -> lands on
    BL_PT_PROMOTION_LOCK_DIR (.locks/_pt_promotion.lock) and inherits
    is_bl_stale-based reclaim (AK-3, no dead-lock on worker death).

    Returns True on success, False if held (non-stale).
    """
    return acquire_bl(
        bl_id=PROMOTION_LOCK_BL_ID,
        worker_id=worker_id,
        ttl=ttl,
        phase=phase,
        vault_root=vault_root,
    )


def release_promotion_lock(
    worker_id: str,
    vault_root: Optional[Path] = None,
) -> bool:
    """
    Release the shared PT/SL promotion lock (BL-320).
    Delegates to release_bl(bl_id="_pt_promotion", ...).
    Only the owning worker can release.

    Returns True if released, False if not the owner.
    """
    return release_bl(
        bl_id=PROMOTION_LOCK_BL_ID,
        worker_id=worker_id,
        vault_root=vault_root,
    )


@contextlib.contextmanager
def promotion_lock(
    worker_id: str,
    ttl: int = 600,
    vault_root: Optional[Path] = None,
    phase: str = "promote",
):
    """
    Context manager convenience for the _PT_/_SL_promoteFromPL skill-seam (BL-320).
    Acquires on __enter__, releases on __exit__ (same worker_id), even on exception.

    Note: yields the acquire-result so callers may inspect it; the seam holds the
    lock for the duration of the block regardless.
    """
    acquired = acquire_promotion_lock(
        worker_id=worker_id, ttl=ttl, vault_root=vault_root, phase=phase
    )
    try:
        yield acquired
    finally:
        release_promotion_lock(worker_id=worker_id, vault_root=vault_root)


# ── BL-230 SB-5: per-BL truth_lease (AK-TRUTH-LEASE + AK-EXCL-SEMAPHOR) ───────
# A per-BL 1-slot lease (EC-ES-1: 1 Lease-Slot = 1 EXCLUSIVE-Slot/BL). REUSES the
# mkdir-Pattern (atomic, Windows-robust rmtree) but in its OWN namespace
# ({bl}.truthlease vs {bl}.lock) so it never collides with the ordinary BL-lock
# or the _pt_promotion lock. EC-ES-2: the M5-EXCLUSIVE-Semaphor IS the truth_lease.
# Stale-Reclaim is inherited (TTL-based) so a dead M5-Worker never dead-locks the
# lease. The lease records its OWN ttl (per-lease TTL, NOT the fixed 300s BL-stale)
# so a short ttl + sleep makes it re-acquirable (mirrors test ttl=1 + sleep(1.5)).

TRUTH_LEASE_SUFFIX = ".truthlease"
DEFAULT_TRUTH_LEASE_TTL = 600


def _truth_lease_dir(bl_id: str, vault_root: Optional[Path] = None) -> Path:
    return _bl_locks_root(vault_root) / f"{bl_id}{TRUTH_LEASE_SUFFIX}"


def _is_truth_lease_stale(lease_dir: Path) -> bool:
    """Return True if the truth-lease heartbeat is older than its own recorded ttl.

    Unlike is_bl_stale (fixed 300s), the truth_lease honours the per-lease ttl
    persisted in ttl.txt at acquire time -> a ttl=1 lease becomes stale after 1s
    (EC: Worker-Tod != Dead-Lock). A forming dir without heartbeat falls back to
    the dir mtime (BL-344 AK-2(b) analogue).
    """
    if not lease_dir.exists():
        return True

    try:
        ttl = int((lease_dir / "ttl.txt").read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        ttl = DEFAULT_TRUTH_LEASE_TTL

    heartbeat_file = lease_dir / "heartbeat.txt"
    if not heartbeat_file.exists():
        try:
            age = (datetime.now(timezone.utc).timestamp() - lease_dir.stat().st_mtime)
        except OSError:
            return True
        return age > ttl

    try:
        ts = _parse_iso(heartbeat_file.read_text(encoding="utf-8").strip())
        age = (datetime.now(timezone.utc) - ts).total_seconds()
        return age > ttl
    except Exception:
        return True


def acquire_truth_lease(
    bl_id: str,
    worker_id: str,
    ttl: int = DEFAULT_TRUTH_LEASE_TTL,
    vault_root: Optional[Path] = None,
) -> bool:
    """Acquire the per-BL truth_lease (BL-230 SB-5, AK-TRUTH-LEASE / EC-ES-2).

    1-slot semaphore per BL in its OWN namespace ({bl}.truthlease). Mirrors
    acquire_bl's atomic mkdir + stale-reclaim, but honours the per-lease ttl.

    Returns True on success, False if held (non-stale). Non-blocking: a busy slot
    returns False IMMEDIATELY (no wait) -> the Motor maps that to 'deferred'.
    """
    lease_dir = _truth_lease_dir(bl_id, vault_root)
    locks_root = _bl_locks_root(vault_root)
    locks_root.mkdir(parents=True, exist_ok=True)

    with _process_lock:
        try:
            lease_dir.mkdir(exist_ok=False)  # Atomic: fails if exists
        except FileExistsError:
            if _is_truth_lease_stale(lease_dir):
                _robust_rmtree(lease_dir)
                try:
                    lease_dir.mkdir(exist_ok=False)
                except FileExistsError:
                    return False  # reclaim lost to concurrent acquire
                _emit_audit("TRUTH_LEASE_STALE_RECLAIM", {"bl_id": bl_id, "worker_id": worker_id})
            else:
                return False  # held, non-stale -> non-blocking False (deferred)

        now = _now_iso()
        # heartbeat first (minimise the no-heartbeat window, BL-344 AK-2(a))
        (lease_dir / "heartbeat.txt").write_text(now, encoding="utf-8")
        (lease_dir / "started.txt").write_text(now, encoding="utf-8")
        (lease_dir / "ttl.txt").write_text(str(ttl), encoding="utf-8")
        (lease_dir / "owner.txt").write_text(worker_id, encoding="utf-8")
        _emit_audit("TRUTH_LEASE_ACQUIRED", {"bl_id": bl_id, "worker_id": worker_id, "ttl": ttl})
        return True


def release_truth_lease(
    bl_id: str,
    worker_id: str,
    vault_root: Optional[Path] = None,
) -> bool:
    """Release the per-BL truth_lease. Only the owner may release.

    Idempotent: a double release (or release of a free slot) returns False without
    throwing. A foreign-worker release returns False and leaves the lease intact.
    """
    lease_dir = _truth_lease_dir(bl_id, vault_root)

    if not lease_dir.exists():
        return False

    try:
        owner = (lease_dir / "owner.txt").read_text(encoding="utf-8").strip()
    except OSError:
        owner = ""

    if owner != worker_id:
        return False

    _robust_rmtree(lease_dir)
    _emit_audit("TRUTH_LEASE_RELEASED", {"bl_id": bl_id, "worker_id": worker_id})
    return True


def is_truth_leased(
    bl_id: str,
    vault_root: Optional[Path] = None,
) -> bool:
    """Return True if the per-BL truth_lease is currently held (non-stale).

    A stale lease (TTL exceeded) reports False (re-acquirable, no dead-lock signal).
    """
    lease_dir = _truth_lease_dir(bl_id, vault_root)
    if not lease_dir.exists():
        return False
    return not _is_truth_lease_stale(lease_dir)


# ── CLI ──────────────────────────────────────────────────────────────────────

def _cli_main():
    parser = argparse.ArgumentParser(description="BDF Factory Lock CLI (BL-175)")
    sub = parser.add_subparsers(dest="command")

    p_acquire = sub.add_parser("acquire")
    p_acquire.add_argument("--scope", default="global")
    p_acquire.add_argument("--ttl", type=int, default=DEFAULT_TTL)
    p_acquire.add_argument("--worker-id", default=None)
    p_acquire.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    p_acquire.add_argument("--purpose", default="BDF")

    p_release = sub.add_parser("release")
    p_release.add_argument("--worker-id", required=True)

    p_hb = sub.add_parser("heartbeat")
    p_hb.add_argument("--worker-id", required=True)

    p_fr = sub.add_parser("force-release")
    p_fr.add_argument("--scope", default="global")

    sub.add_parser("status")

    # BL-194: BL-level lock commands
    p_abl = sub.add_parser("acquire-bl")
    p_abl.add_argument("bl_id")
    p_abl.add_argument("--worker-id", required=True)
    p_abl.add_argument("--ttl", type=int, default=600)
    p_abl.add_argument("--worktree", default="")
    p_abl.add_argument("--phase", default="A.init")

    p_rbl = sub.add_parser("release-bl")
    p_rbl.add_argument("bl_id")
    p_rbl.add_argument("--worker-id", required=True)

    p_hbl = sub.add_parser("heartbeat-bl")
    p_hbl.add_argument("bl_id")
    p_hbl.add_argument("--worker-id", required=True)

    p_sbl = sub.add_parser("status-bl")
    p_sbl.add_argument("bl_id")

    sub.add_parser("list-bl-locks")

    sub.add_parser("reclaim-stale-bl-locks")

    args = parser.parse_args()

    if args.command == "acquire":
        ok = acquire(
            scope=args.scope,
            ttl=args.ttl,
            worker_id=args.worker_id,
            timeout=args.timeout,
            purpose=args.purpose,
        )
        sys.exit(0 if ok else 1)

    elif args.command == "release":
        ok = release(worker_id=args.worker_id)
        if not ok:
            print(f"[BDF-LOCK] ERROR: Not the lock holder or lock not held by {args.worker_id}", file=sys.stderr)
        sys.exit(0 if ok else 1)

    elif args.command == "heartbeat":
        ok = heartbeat(worker_id=args.worker_id)
        sys.exit(0 if ok else 1)

    elif args.command == "force-release":
        force_release(scope=args.scope)
        sys.exit(0)

    elif args.command == "status":
        info = is_locked()
        if info:
            print(f"LOCKED by {info['holder']} since {info['acquired_at']} (ttl={info['ttl_seconds']}s, heartbeat={info['heartbeat_at']})")
        else:
            print("UNLOCKED")
        sys.exit(0)

    # BL-194 BL-level commands
    elif args.command == "acquire-bl":
        ok = acquire_bl(
            bl_id=args.bl_id,
            worker_id=args.worker_id,
            ttl=args.ttl,
            worktree=args.worktree,
            phase=args.phase,
        )
        sys.exit(0 if ok else 1)

    elif args.command == "release-bl":
        ok = release_bl(bl_id=args.bl_id, worker_id=args.worker_id)
        if not ok:
            print(f"[BL-LOCK] ERROR: Could not release {args.bl_id}", file=sys.stderr)
        sys.exit(0 if ok else 1)

    elif args.command == "heartbeat-bl":
        ok = heartbeat_bl(bl_id=args.bl_id, worker_id=args.worker_id)
        sys.exit(0 if ok else 1)

    elif args.command == "status-bl":
        info = get_bl_lock_info(args.bl_id)
        if info:
            print(f"LOCKED: {info['bl_id']} by {info['owner']} "
                  f"(phase={info['phase']}, heartbeat={info['heartbeat']}, host={info['host']})")
        else:
            stale = is_bl_stale(args.bl_id)
            if stale:
                print(f"STALE or UNLOCKED: {args.bl_id}")
            else:
                print(f"UNLOCKED: {args.bl_id}")
        sys.exit(0)

    elif args.command == "list-bl-locks":
        locks = list_active_bl_locks()
        if not locks:
            print("No active BL-locks.")
        else:
            for lock in locks:
                print(f"  {lock['bl_id']}: owner={lock['owner']}, phase={lock['phase']}, heartbeat={lock['heartbeat']}")
        sys.exit(0)

    elif args.command == "reclaim-stale-bl-locks":
        reclaimed = reclaim_stale_bl_locks()
        if reclaimed:
            print(f"Reclaimed {len(reclaimed)} stale locks: {reclaimed}")
        else:
            print("No stale BL-locks found.")
        sys.exit(0)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    _cli_main()
