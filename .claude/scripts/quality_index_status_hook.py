"""
quality_index_status_hook.py — BL-178 AK-4

Pre-Write-Hook for _backlog_index.md.
Detects status transitions to Archive-status → triggers auto-migration.

Hook signature:
    pre_write_hook(old_content, new_content) -> str
    Returns potentially modified new_content.
"""
import json
import logging
import os
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

# Import status sets from migrate script (or redefine for standalone use)
try:
    from migrate_backlog_index_split import (
        ACTIVE_STATUS_SET,
        ARCHIVE_STATUS_SET,
        _parse_table_rows,
        _atomic_write,
    )
except ImportError:
    # Fallback for standalone use
    ACTIVE_STATUS_SET = {
        "DRAFT", "READY", "PLANNED", "IN_PROGRESS", "RUNNING",
        "SC-REIF", "FREEZE", "HOLD", "DEFERRED", "PARTIAL_DONE", "PHANTOM",
        "QUESTION_HOLD",
    }
    ARCHIVE_STATUS_SET = {
        "DONE", "DECOMPOSED", "ARCHIVIERT", "ABSORBED",
        "ABSORBED_INTO_X", "ARCHIVED_ID_REUSED", "DUPLIKAT",
    }

    def _parse_table_rows(content):
        rows = []
        lines = content.splitlines(keepends=True)
        in_fm = False
        fm_count = 0
        header_passed = False
        ROW_RE = re.compile(r"^\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]*)\|?.*$")
        for idx, line in enumerate(lines):
            s = line.rstrip()
            if s == "---":
                fm_count += 1
                in_fm = fm_count == 1
                if fm_count == 2:
                    in_fm = False
                continue
            if in_fm:
                continue
            m = ROW_RE.match(s)
            if not m:
                continue
            c1, c3 = m.group(1).strip(), m.group(3).strip()
            if c1.startswith("-") or c1.lower() in ("bl-id", "id", "bl_id"):
                header_passed = True
                continue
            if c3.startswith("-") or c3.lower() == "status":
                continue
            if not header_passed:
                continue
            rows.append({"raw": line, "bl_id": c1, "status": c3, "line_idx": idx})
        return rows

    def _atomic_write(path, content):
        import tempfile, os
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp_", suffix=".md")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


# ---------------------------------------------------------------------------
# Lock (BL-175 integration)
# ---------------------------------------------------------------------------

_LOCK_FILE_NAME = ".backlog_index_migration.lock"


class _FileLock:
    """Simple file-based lock for BL-175 compliance."""

    def __init__(self, lock_path: Path):
        self._lock_path = lock_path
        self._fd = None

    def acquire(self, timeout: float = 5.0) -> bool:
        import time
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                self._fd = os.open(
                    str(self._lock_path),
                    os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                )
                return True
            except FileExistsError:
                time.sleep(0.05)
        return False

    def release(self) -> None:
        if self._fd is not None:
            try:
                os.close(self._fd)
            except OSError:
                pass
            self._fd = None
        try:
            os.unlink(str(self._lock_path))
        except OSError:
            pass


def acquire_lock(lock_dir: Path) -> _FileLock:
    lock = _FileLock(lock_dir / _LOCK_FILE_NAME)
    acquired = lock.acquire()
    if not acquired:
        raise TimeoutError("Could not acquire backlog_index_migration lock (BL-175)")
    return lock


# ---------------------------------------------------------------------------
# Diff helper
# ---------------------------------------------------------------------------

def _detect_status_changes(old_content: str, new_content: str) -> list[dict]:
    """
    Detect rows where status changed from Active to Archive.
    Returns list of dicts: {bl_id, old_status, new_status}
    """
    old_rows = {r["bl_id"]: r["status"] for r in _parse_table_rows(old_content)}
    new_rows = {r["bl_id"]: r for r in _parse_table_rows(new_content)}

    changes = []
    for bl_id, new_row in new_rows.items():
        new_status = new_row["status"]
        old_status = old_rows.get(bl_id)
        if (
            old_status is not None
            and old_status != new_status
            and new_status in ARCHIVE_STATUS_SET
        ):
            changes.append({
                "bl_id": bl_id,
                "old_status": old_status,
                "new_status": new_status,
                "raw": new_row["raw"],
            })

    return changes


def _write_audit(vault_root: Path, event: dict) -> None:
    audit_path = vault_root / ".claude" / "audit" / "audit.jsonl"
    if audit_path.exists():
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    else:
        log.debug("audit.jsonl not found, skipping")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Main hook function
# ---------------------------------------------------------------------------

def pre_write_hook(
    old_content: str,
    new_content: str,
    vault_root: Optional[Path] = None,
) -> str:
    """
    Pre-write hook for _backlog_index.md.

    Detects status transitions to Archive-status.
    If found: triggers migration of those items to _backlog_index_done.md.
    Returns (possibly modified) new_content.

    INV-INDEX-SPLIT-1: items must not exist in both indexes.
    INV-INDEX-SPLIT-3: atomic writes only.
    BL-175: lock acquisition before write.
    """
    if vault_root is None:
        # Try to auto-detect from environment
        vault_env = os.environ.get("VAULT_ROOT")
        vault_root = Path(vault_env) if vault_env else None

    changes = _detect_status_changes(old_content, new_content)
    if not changes:
        return new_content

    log.info("Hook: detected %d status transition(s) to archive", len(changes))

    if vault_root is None:
        log.warning("VAULT_ROOT not set — skipping auto-migration for %d items", len(changes))
        return new_content

    archive_index = vault_root / "_backlog_index_done.md"

    # Acquire lock (BL-175)
    lock = acquire_lock(vault_root)
    try:
        ts = _ts()

        # 1. Load or init archive content
        if archive_index.exists():
            archive_content = archive_index.read_text(encoding="utf-8")
        else:
            from datetime import datetime
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            archive_content = (
                f"---\ntype: backlog-archive-index\ncreated: '{today}'\n"
                f"migrated_from: _backlog_index.md\nitems_count: 0\n"
                f"inv: INV-INDEX-SPLIT-1\n---\n\n"
                f"# Backlog Archive Index\n\n"
                f"| BL-ID | Titel | Status | Reifegrad |\n"
                f"|-------|-------|--------|-----------|\n"
            )

        # 2. For each change: remove from new_content, add to archive
        modified_new = new_content
        for change in changes:
            bl_id = change["bl_id"]
            # Find and remove the row from new_content
            lines = modified_new.splitlines(keepends=True)
            row_re = re.compile(r"^\|\s*" + re.escape(bl_id) + r"\s*\|")
            kept = []
            removed_raw = None
            for line in lines:
                if row_re.match(line):
                    removed_raw = line
                else:
                    kept.append(line)
            modified_new = "".join(kept)

            # Append to archive (with archived_at timestamp)
            raw = removed_raw or change["raw"]
            # Update status in raw line if needed
            raw_updated = re.sub(
                r"(\|\s*" + re.escape(bl_id) + r"\s*\|[^|]*\|)\s*[A-Z_]+\s*(\|)",
                lambda m_: m_.group(1) + f" {change['new_status']} " + m_.group(2),
                raw,
            )
            # Append archived_at as comment at end of line
            archived_line = raw_updated.rstrip("\n") + f" <!-- archived_at={ts} -->\n"
            archive_content += archived_line

            log.info(
                "Hook: migrated %s (%s → %s) to archive",
                bl_id, change["old_status"], change["new_status"],
            )

        # 3. Atomic writes
        _atomic_write(vault_root / "_backlog_index.md", modified_new)
        _atomic_write(archive_index, archive_content)

        # 4. Audit
        for change in changes:
            _write_audit(vault_root, {
                "type": "INDEX_GC",
                "bl_id": change["bl_id"],
                "old_status": change["old_status"],
                "new_status": change["new_status"],
                "trigger": "pre_write_hook",
                "ts": ts,
            })

        return modified_new

    finally:
        lock.release()


# ---------------------------------------------------------------------------
# CLI (for testing)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BL-178 AK-4: Quality Index Status Hook")
    parser.add_argument("--old-file", required=True)
    parser.add_argument("--new-file", required=True)
    parser.add_argument("--vault-root", required=True)
    args = parser.parse_args()

    old = Path(args.old_file).read_text(encoding="utf-8")
    new = Path(args.new_file).read_text(encoding="utf-8")
    result = pre_write_hook(old, new, vault_root=Path(args.vault_root))
    print("Hook result (first 200 chars):", result[:200])
