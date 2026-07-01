"""
migrate_backlog_index_split.py — BL-178 AK-2

Splits _backlog_index.md into:
  - _backlog_index.md (Active-Items only)
  - _backlog_index_done.md (Archive-Items)

Usage:
    py -3 migrate_backlog_index_split.py migrate --vault-root=PATH [--dry-run] [--rollback-tag TAG]
    py -3 migrate_backlog_index_split.py rollback --vault-root=PATH --rollback-tag TAG
    py -3 migrate_backlog_index_split.py verify --vault-root=PATH
"""
import argparse
import json
import logging
import os
import re
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger(__name__)

# INV-INDEX-SPLIT-1: Status-Sets from schema_active_archive_index.md
ACTIVE_STATUS_SET = {
    "DRAFT", "READY", "PLANNED", "IN_PROGRESS", "RUNNING",
    "SC-REIF", "FREEZE", "HOLD", "DEFERRED", "PARTIAL_DONE", "PHANTOM",
    "QUESTION_HOLD",
}

ARCHIVE_STATUS_SET = {
    "DONE", "DECOMPOSED", "ARCHIVIERT", "ABSORBED",
    "ABSORBED_INTO_X", "ARCHIVED_ID_REUSED", "DUPLIKAT",
}

# Regex to match table rows: | BL-NNN | ... | STATUS | ... |
_ROW_RE = re.compile(r"^\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]*)\|?.*$")
# Frontmatter block
_FM_RE = re.compile(r"^---\s*$")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _parse_table_rows(content: str) -> list[dict]:
    """Parse markdown table rows into dicts with keys: raw, bl_id, status, line_idx."""
    rows = []
    lines = content.splitlines(keepends=True)
    in_frontmatter = False
    fm_count = 0
    header_passed = False

    for idx, line in enumerate(lines):
        stripped = line.rstrip("\n").rstrip()
        if _FM_RE.match(stripped):
            fm_count += 1
            in_frontmatter = fm_count == 1
            if fm_count == 2:
                in_frontmatter = False
            continue
        if in_frontmatter:
            continue

        m = _ROW_RE.match(stripped)
        if not m:
            continue

        col1 = m.group(1).strip()
        col3 = m.group(3).strip()

        # Skip header/separator rows
        if col1.startswith("-") or col1.lower() in ("bl-id", "id", "bl_id"):
            header_passed = True
            continue
        if col3.startswith("-") or col3.lower() in ("status", "---"):
            continue

        if not header_passed:
            continue

        rows.append({
            "raw": line,
            "bl_id": col1,
            "status": col3,
            "line_idx": idx,
        })

    return rows


def classify_rows(rows: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    """
    Returns (active_rows, archive_rows, unknown_rows).
    INV-INDEX-SPLIT-1: each item in exactly one set.
    """
    active, archive, unknown = [], [], []
    for row in rows:
        status = row["status"]
        if status in ARCHIVE_STATUS_SET:
            archive.append(row)
        elif status in ACTIVE_STATUS_SET:
            active.append(row)
        else:
            log.warning("UNKNOWN_STATUS '%s' for '%s' — keeping in active", status, row["bl_id"])
            unknown.append(row)
    return active, archive, unknown


def _build_active_content(original: str, archive_rows: list[dict]) -> str:
    """Remove archive rows from original content."""
    if not archive_rows:
        return original
    archive_line_indices = {r["line_idx"] for r in archive_rows}
    lines = original.splitlines(keepends=True)
    kept = [line for idx, line in enumerate(lines) if idx not in archive_line_indices]
    return "".join(kept)


def _build_archive_content(archive_rows: list[dict], migration_date: str, source_file: str) -> str:
    """Build _backlog_index_done.md content."""
    header = (
        f"---\n"
        f"type: backlog-archive-index\n"
        f"created: '{migration_date}'\n"
        f"migrated_from: {source_file}\n"
        f"items_count: {len(archive_rows)}\n"
        f"inv: INV-INDEX-SPLIT-1\n"
        f"---\n\n"
        f"# Backlog Archive Index\n\n"
        f"<!-- Items migrated from {source_file} on {migration_date} -->\n"
        f"<!-- Re-activate via: /_backlog reopen BL-XXX -->\n\n"
        f"| BL-ID | Titel | Status | Reifegrad |\n"
        f"|-------|-------|--------|-----------|\n"
    )
    return header + "".join(r["raw"] for r in archive_rows)


def _atomic_write(path: Path, content: str) -> None:
    """Write via tempfile + os.replace for atomicity (INV-INDEX-SPLIT-3)."""
    parent = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=parent, prefix=".tmp_", suffix=".md")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _write_audit_event(vault_root: Path, event: dict) -> None:
    """Append event to audit.jsonl."""
    audit_path = vault_root / ".claude" / "audit" / "audit.jsonl"
    if audit_path.exists():
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    else:
        log.warning("audit.jsonl not found at %s — skipping audit write", audit_path)


def _set_rollback_tag(rollback_tag: str) -> bool:
    """Create git tag for rollback."""
    try:
        result = subprocess.run(
            ["git", "tag", rollback_tag],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            log.info("Rollback tag created: %s", rollback_tag)
            return True
        else:
            log.warning("Git tag failed: %s", result.stderr.strip())
            return False
    except FileNotFoundError:
        log.warning("git not found — skipping rollback tag")
        return False


def _backup_path(vault_root: Path, rollback_tag: str) -> Path:
    return vault_root / f"_backlog_index.backup.{rollback_tag}.md"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def migrate(
    vault_root: Path,
    rollback_tag: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """
    Main migration function.

    Returns summary dict with keys:
      active_count, archive_count, unknown_count, dry_run
    """
    active_index = vault_root / "_backlog_index.md"
    archive_index = vault_root / "_backlog_index_done.md"

    if not active_index.exists():
        raise FileNotFoundError(f"_backlog_index.md not found at {active_index}")

    content = _read_file(active_index)
    rows = _parse_table_rows(content)
    active_rows, archive_rows, unknown_rows = classify_rows(rows)

    log.info(
        "Classified: %d active, %d archive, %d unknown (total rows: %d)",
        len(active_rows), len(archive_rows), len(unknown_rows), len(rows),
    )

    if dry_run:
        log.info("[DRY-RUN] Would migrate %d items to archive", len(archive_rows))
        for r in archive_rows:
            log.info("  → ARCHIVE: %s (status=%s)", r["bl_id"], r["status"])
        return {
            "active_count": len(active_rows),
            "archive_count": len(archive_rows),
            "unknown_count": len(unknown_rows),
            "dry_run": True,
        }

    today = _today()
    ts = _ts()

    if rollback_tag is None:
        rollback_tag = f"pre-bl178-backlog-migration-{today}"

    # 1. Git tag
    _set_rollback_tag(rollback_tag)

    # 2. Backup for rollback
    backup = _backup_path(vault_root, rollback_tag)
    _atomic_write(backup, content)
    log.info("Backup written: %s", backup)

    # 3. Build new contents
    new_active_content = _build_active_content(content, archive_rows)
    new_archive_content = _build_archive_content(archive_rows, today, "_backlog_index.md")

    # 4. Atomic writes (INV-INDEX-SPLIT-3)
    _atomic_write(active_index, new_active_content)
    _atomic_write(archive_index, new_archive_content)

    log.info("Migration complete: %d items archived", len(archive_rows))

    # 5. Audit
    event = {
        "type": "INDEX_GC",
        "target": "backlog_index",
        "moved_items": len(archive_rows),
        "active_remaining": len(active_rows),
        "unknown_count": len(unknown_rows),
        "rollback_tag": rollback_tag,
        "ts": ts,
    }
    _write_audit_event(vault_root, event)

    return {
        "active_count": len(active_rows),
        "archive_count": len(archive_rows),
        "unknown_count": len(unknown_rows),
        "dry_run": False,
    }


def rollback(vault_root: Path, rollback_tag: str) -> dict:
    """
    Restore _backlog_index.md from backup created during migrate().
    """
    backup = _backup_path(vault_root, rollback_tag)
    if not backup.exists():
        raise FileNotFoundError(f"Backup not found: {backup}")

    content = _read_file(backup)
    active_index = vault_root / "_backlog_index.md"
    _atomic_write(active_index, content)
    log.info("Rollback complete — restored from %s", backup)

    ts = _ts()
    _write_audit_event(vault_root, {
        "type": "INDEX_GC_ROLLBACK",
        "target": "backlog_index",
        "rollback_tag": rollback_tag,
        "ts": ts,
    })

    return {"status": "rolled_back", "rollback_tag": rollback_tag}


def verify(vault_root: Path) -> dict:
    """
    Verify consistency: no item in both active and archive (INV-INDEX-SPLIT-1).
    """
    active_index = vault_root / "_backlog_index.md"
    archive_index = vault_root / "_backlog_index_done.md"

    violations = []

    if not active_index.exists():
        return {"ok": False, "error": "_backlog_index.md missing"}

    active_rows = _parse_table_rows(_read_file(active_index))
    active_ids = {r["bl_id"] for r in active_rows}

    if archive_index.exists():
        archive_rows = _parse_table_rows(_read_file(archive_index))
        archive_ids = {r["bl_id"] for r in archive_rows}
        overlap = active_ids & archive_ids
        for bl_id in overlap:
            violations.append({"bl_id": bl_id, "violation": "INV-INDEX-SPLIT-1: item in both indexes"})

        # Check status consistency (INV-INDEX-SPLIT-2)
        for r in archive_rows:
            if r["status"] in ACTIVE_STATUS_SET:
                violations.append({
                    "bl_id": r["bl_id"],
                    "violation": f"INV-INDEX-SPLIT-2: archive item has active status '{r['status']}'",
                })
        for r in active_rows:
            if r["status"] in ARCHIVE_STATUS_SET:
                violations.append({
                    "bl_id": r["bl_id"],
                    "violation": f"INV-INDEX-SPLIT-2: active item has archive status '{r['status']}'",
                })

    ok = len(violations) == 0
    log.info("Verify: %s (%d violations)", "OK" if ok else "FAIL", len(violations))
    return {"ok": ok, "violations": violations, "active_count": len(active_ids)}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="BL-178: Backlog Index Split Migration"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # migrate
    m = sub.add_parser("migrate", help="Split _backlog_index.md into active + archive")
    m.add_argument("--vault-root", required=True, help="Path to vault root")
    m.add_argument("--dry-run", action="store_true", help="Preview without writing")
    m.add_argument("--rollback-tag", default=None, help="Git tag name for rollback")

    # rollback
    r = sub.add_parser("rollback", help="Restore from backup")
    r.add_argument("--vault-root", required=True)
    r.add_argument("--rollback-tag", required=True)

    # verify
    v = sub.add_parser("verify", help="Verify index consistency")
    v.add_argument("--vault-root", required=True)

    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    vault_root = Path(args.vault_root)

    if args.command == "migrate":
        result = migrate(vault_root, rollback_tag=args.rollback_tag, dry_run=args.dry_run)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "rollback":
        result = rollback(vault_root, args.rollback_tag)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "verify":
        result = verify(vault_root)
        print(json.dumps(result, indent=2))
        return 0 if result["ok"] else 1

    return 1


if __name__ == "__main__":
    sys.exit(main())
