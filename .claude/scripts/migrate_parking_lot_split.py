"""
migrate_parking_lot_split.py — BL-178 AK-3

Splits _parking-lot.md into:
  - _parking-lot.md (Active items: [ ], [~], [?], [!])
  - _parking-lot_done.md (Archive items: [x])

Usage:
    py -3 migrate_parking_lot_split.py migrate --vault-root=PATH [--dry-run] [--rollback-tag TAG]
    py -3 migrate_parking_lot_split.py rollback --vault-root=PATH --rollback-tag TAG
    py -3 migrate_parking_lot_split.py verify --vault-root=PATH
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

# BL-333: format_version-Stamp (Writer=Follow, Wert via Loader-Call). Loader-fehlt -> kein Crash.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from resolve_format_version import resolve_format_version
except ImportError:
    def resolve_format_version(typ):  # type: ignore
        return None

# OQ-5 Entscheidung: only [x] is archived
ARCHIVE_MARKERS = {"[x]"}
ACTIVE_MARKERS = {"[ ]", "[~]", "[?]", "[!]"}

# Regex to detect marker at start of a line (after optional leading whitespace)
_MARKER_RE = re.compile(r"^(\s*)((\[[ x~?!]\]))(.*)")


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _read_file(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _atomic_write(path: Path, content: str) -> None:
    """Write via tempfile + os.replace for atomicity (INV-INDEX-SPLIT-3)."""
    parent = path.parent
    fd, tmp_path = tempfile.mkstemp(dir=parent, prefix=".tmp_pl_", suffix=".md")
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
    audit_path = vault_root / ".claude" / "audit" / "audit.jsonl"
    if audit_path.exists():
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")
    else:
        log.warning("audit.jsonl not found at %s — skipping audit write", audit_path)


def _set_rollback_tag(tag: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "tag", tag],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            log.info("Rollback tag created: %s", tag)
            return True
        log.warning("Git tag failed: %s", result.stderr.strip())
        return False
    except FileNotFoundError:
        log.warning("git not found — skipping rollback tag")
        return False


def _backup_path(vault_root: Path, rollback_tag: str) -> Path:
    return vault_root / f"_parking-lot.backup.{rollback_tag}.md"


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def _classify_lines(content: str) -> tuple[list[str], list[str], int, int]:
    """
    Returns (active_lines, archive_lines, active_count, archive_count).
    Lines without a marker are kept in active (headers, blank lines, etc.).
    """
    active_lines = []
    archive_lines = []
    active_count = 0
    archive_count = 0

    for line in content.splitlines(keepends=True):
        m = _MARKER_RE.match(line)
        if m:
            marker = m.group(3)
            if marker in ARCHIVE_MARKERS:
                archive_lines.append(line)
                archive_count += 1
                continue
        # default: keep in active (includes all non-marker lines + active markers)
        active_lines.append(line)
        if m and m.group(3) in ACTIVE_MARKERS:
            active_count += 1

    return active_lines, archive_lines, active_count, archive_count


def _build_archive_content(archive_lines: list[str], migration_date: str, source_file: str) -> str:
    """Build _parking-lot_done.md content (chronological, newest items at top from source order)."""
    # BL-333: format_version additiv stempeln (Writer=Follow). Loader-fehlt (None) -> weglassen (G2e).
    _fv = resolve_format_version("parking_lot")
    _fv_line = f"format_version: {_fv}\n" if _fv is not None else ""
    header = (
        f"---\n"
        f"{_fv_line}"
        f"type: parking-lot-archive\n"
        f"created: '{migration_date}'\n"
        f"migrated_from: {source_file}\n"
        f"lines_migrated: {len(archive_lines)}\n"
        f"---\n\n"
        f"# Parking Lot — Archive (Done Items)\n\n"
        f"<!-- Items migrated from {source_file} on {migration_date} -->\n"
        f"<!-- Re-activate via: /_backlog reopen-pl ITEM_ID -->\n\n"
    )
    # Reverse so newest (last in source) appear first in archive
    return header + "".join(reversed(archive_lines))


def migrate(
    vault_root: Path,
    rollback_tag: Optional[str] = None,
    dry_run: bool = False,
) -> dict:
    """
    Main migration function.
    Returns summary dict.
    """
    active_pl = vault_root / "_parking-lot.md"
    archive_pl = vault_root / "_parking-lot_done.md"

    if not active_pl.exists():
        raise FileNotFoundError(f"_parking-lot.md not found at {active_pl}")

    content = _read_file(active_pl)
    total_loc = content.count("\n") + (1 if content and not content.endswith("\n") else 0)

    active_lines, archive_lines, active_item_count, archive_item_count = _classify_lines(content)

    log.info(
        "Classified: %d active items, %d archive items (total LOC: %d)",
        active_item_count, archive_item_count, total_loc,
    )

    if dry_run:
        log.info("[DRY-RUN] Would migrate %d lines (~%d LOC) to archive", len(archive_lines), len(archive_lines))
        saving_pct = (len(archive_lines) / total_loc * 100) if total_loc > 0 else 0
        log.info("[DRY-RUN] Estimated saving: %.1f%%", saving_pct)
        return {
            "active_item_count": active_item_count,
            "archive_item_count": archive_item_count,
            "archive_lines": len(archive_lines),
            "total_loc": total_loc,
            "estimated_saving_pct": round(saving_pct, 1),
            "dry_run": True,
        }

    today = _today()
    ts = _ts()

    if rollback_tag is None:
        rollback_tag = f"pre-bl178-parking-lot-migration-{today}"

    # 1. Git tag
    _set_rollback_tag(rollback_tag)

    # 2. Backup
    backup = _backup_path(vault_root, rollback_tag)
    _atomic_write(backup, content)
    log.info("Backup written: %s", backup)

    # 3. Build new contents
    new_active_content = "".join(active_lines)
    new_archive_content = _build_archive_content(archive_lines, today, "_parking-lot.md")

    # 4. Atomic writes (INV-INDEX-SPLIT-3)
    _atomic_write(active_pl, new_active_content)
    _atomic_write(archive_pl, new_archive_content)

    new_loc = new_active_content.count("\n")
    saving_pct = ((total_loc - new_loc) / total_loc * 100) if total_loc > 0 else 0
    log.info("Migration complete: %d lines archived (%.1f%% reduction)", len(archive_lines), saving_pct)

    # 5. Audit
    event = {
        "type": "PL_GC",
        "target": "parking_lot",
        "archive_lines": len(archive_lines),
        "active_lines_remaining": len(active_lines),
        "original_loc": total_loc,
        "saving_pct": round(saving_pct, 1),
        "rollback_tag": rollback_tag,
        "ts": ts,
    }
    _write_audit_event(vault_root, event)

    return {
        "active_item_count": active_item_count,
        "archive_item_count": archive_item_count,
        "archive_lines": len(archive_lines),
        "total_loc": total_loc,
        "saving_pct": round(saving_pct, 1),
        "dry_run": False,
    }


def rollback(vault_root: Path, rollback_tag: str) -> dict:
    backup = _backup_path(vault_root, rollback_tag)
    if not backup.exists():
        raise FileNotFoundError(f"Backup not found: {backup}")

    content = _read_file(backup)
    _atomic_write(vault_root / "_parking-lot.md", content)
    log.info("Rollback complete — restored from %s", backup)

    _write_audit_event(vault_root, {
        "type": "PL_GC_ROLLBACK",
        "target": "parking_lot",
        "rollback_tag": rollback_tag,
        "ts": _ts(),
    })

    return {"status": "rolled_back", "rollback_tag": rollback_tag}


def verify(vault_root: Path) -> dict:
    """Verify no [x] items remain in active parking lot."""
    active_pl = vault_root / "_parking-lot.md"
    if not active_pl.exists():
        return {"ok": False, "error": "_parking-lot.md missing"}

    content = _read_file(active_pl)
    violations = []
    for i, line in enumerate(content.splitlines(), start=1):
        m = _MARKER_RE.match(line)
        if m and m.group(3) in ARCHIVE_MARKERS:
            violations.append({"line": i, "content": line.strip(), "violation": "[x] item in active PL"})

    ok = len(violations) == 0
    log.info("Verify: %s (%d violations)", "OK" if ok else "FAIL", len(violations))
    return {"ok": ok, "violations": violations}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BL-178: Parking-Lot Split Migration")
    sub = parser.add_subparsers(dest="command", required=True)

    m = sub.add_parser("migrate", help="Split _parking-lot.md into active + archive")
    m.add_argument("--vault-root", required=True)
    m.add_argument("--dry-run", action="store_true")
    m.add_argument("--rollback-tag", default=None)

    r = sub.add_parser("rollback", help="Restore from backup")
    r.add_argument("--vault-root", required=True)
    r.add_argument("--rollback-tag", required=True)

    v = sub.add_parser("verify", help="Verify active PL has no [x] items")
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
