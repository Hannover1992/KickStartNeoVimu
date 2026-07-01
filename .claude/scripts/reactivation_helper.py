"""
reactivation_helper.py — BL-178 AK-5

Re-activates a BL item from Archive back to Active.

Usage:
    py -3 reactivation_helper.py reopen --bl=BL-XXX --vault-root=PATH
    py -3 reactivation_helper.py reopen-pl --item-id=ITEM_ID --vault-root=PATH
"""
import argparse
import json
import logging
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

try:
    from migrate_backlog_index_split import _atomic_write, _parse_table_rows
except ImportError:
    from pathlib import Path as _Path
    import os, tempfile

    def _atomic_write(path, content):
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

    def _parse_table_rows(content):
        rows = []
        lines = content.splitlines(keepends=True)
        ROW_RE = re.compile(r"^\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]*)\|?.*$")
        in_fm, fm_count, header_passed = False, 0, False
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
            if c1.startswith("-") or c1.lower() in ("bl-id", "id"):
                header_passed = True
                continue
            if c3.startswith("-") or c3.lower() == "status":
                continue
            if not header_passed:
                continue
            rows.append({"raw": line, "bl_id": c1, "status": c3, "line_idx": idx})
        return rows


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_audit(vault_root: Path, event: dict) -> None:
    audit_path = vault_root / ".claude" / "audit" / "audit.jsonl"
    if audit_path.exists():
        with open(audit_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event) + "\n")


def _insert_row_sorted(active_content: str, row_line: str, bl_id: str) -> str:
    """
    Insert row into active index, sorted by BL-ID numerically.
    """
    lines = active_content.splitlines(keepends=True)
    # Clean archived_at comment from row
    clean_row = re.sub(r"\s*<!--.*?-->", "", row_line).rstrip() + "\n"
    # Change status to DRAFT
    clean_row = re.sub(
        r"(\|\s*" + re.escape(bl_id) + r"\s*\|[^|]*\|)\s*[A-Z_]+\s*(\|)",
        lambda m: m.group(1) + " DRAFT " + m.group(2),
        clean_row,
    )

    # Find insertion point (after last header row, before next BL with higher ID)
    bl_num = int(re.search(r"\d+", bl_id).group()) if re.search(r"\d+", bl_id) else 0
    ROW_RE = re.compile(r"^\|\s*(BL-\d+)\s*\|")
    insert_at = len(lines)

    for i, line in enumerate(lines):
        m = ROW_RE.match(line)
        if m:
            existing_id = m.group(1)
            existing_num_m = re.search(r"\d+", existing_id)
            if existing_num_m:
                existing_num = int(existing_num_m.group())
                if existing_num > bl_num:
                    insert_at = i
                    break

    lines.insert(insert_at, clean_row)
    return "".join(lines)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def reactivate_bl(bl_id: str, vault_root: Path) -> dict:
    """
    Re-activates a BL item from Archive Index to Active Index.

    Steps:
    1. Find BL-ID in _backlog_index_done.md
    2. Remove from archive
    3. Insert into _backlog_index.md (ID-sorted) with status=DRAFT
    4. Update Detail-File status → DRAFT, add reactivated_at
    5. Audit event REACTIVATION
    """
    archive_index = vault_root / "_backlog_index_done.md"
    active_index = vault_root / "_backlog_index.md"

    if not archive_index.exists():
        raise FileNotFoundError(f"Archive index not found: {archive_index}")
    if not active_index.exists():
        raise FileNotFoundError(f"Active index not found: {active_index}")

    archive_content = archive_index.read_text(encoding="utf-8")
    active_content = active_index.read_text(encoding="utf-8")

    # 1. Find item in archive
    archive_rows = _parse_table_rows(archive_content)
    target_row = next((r for r in archive_rows if r["bl_id"] == bl_id), None)
    if target_row is None:
        raise ValueError(f"{bl_id} not found in archive index")

    ts = _ts()
    old_status = target_row["status"]
    raw_line = target_row["raw"]

    # 2. Remove from archive
    archive_lines = archive_content.splitlines(keepends=True)
    row_re = re.compile(r"^\|\s*" + re.escape(bl_id) + r"\s*\|")
    new_archive_lines = [l for l in archive_lines if not row_re.match(l)]
    new_archive_content = "".join(new_archive_lines)

    # 3. Insert into active (sorted, status=DRAFT)
    new_active_content = _insert_row_sorted(active_content, raw_line, bl_id)

    # 4. Atomic writes
    _atomic_write(archive_index, new_archive_content)
    _atomic_write(active_index, new_active_content)

    # 5. Update Detail-File if found
    detail_updated = _update_detail_file(bl_id, vault_root, ts)

    # 6. Audit
    _write_audit(vault_root, {
        "type": "REACTIVATION",
        "bl_id": bl_id,
        "from_archive": True,
        "old_status": old_status,
        "new_status": "DRAFT",
        "detail_file_updated": detail_updated,
        "ts": ts,
    })

    log.info("Reactivated %s (was %s → now DRAFT)", bl_id, old_status)
    return {
        "bl_id": bl_id,
        "old_status": old_status,
        "new_status": "DRAFT",
        "detail_file_updated": detail_updated,
    }


def _update_detail_file(bl_id: str, vault_root: Path, ts: str) -> bool:
    """Find and update BL detail file. Returns True if updated."""
    # Common locations
    search_patterns = [
        vault_root / f"**/{bl_id}*.md",
    ]
    # Try direct search in Backlog folder
    backlog_root = vault_root.parent / "Backlog" if vault_root.name != "Backlog" else vault_root
    candidates = []

    # Search adjacent Backlog folder
    for search_root in [vault_root, backlog_root]:
        if search_root.exists():
            for p in search_root.rglob(f"{bl_id}*.md"):
                # Skip index files
                if "index" not in p.name.lower():
                    candidates.append(p)

    if not candidates:
        log.debug("No detail file found for %s", bl_id)
        return False

    detail_file = candidates[0]
    content = detail_file.read_text(encoding="utf-8")

    # Update status in frontmatter
    updated = re.sub(
        r"(^status:\s*)['\"]?[A-Z_]+['\"]?",
        r"\g<1>DRAFT",
        content,
        flags=re.MULTILINE,
    )
    # Add reactivated_at
    if "reactivated_at:" not in updated:
        updated = re.sub(
            r"(^status:\s*DRAFT)",
            f"\\1\nreactivated_at: '{ts}'",
            updated,
            flags=re.MULTILINE,
        )

    _atomic_write(detail_file, updated)
    log.info("Updated detail file: %s", detail_file)
    return True


def reactivate_pl_item(item_id: str, vault_root: Path) -> dict:
    """
    Re-activates a Parking-Lot item from _parking-lot_done.md to _parking-lot.md.
    """
    archive_pl = vault_root / "_parking-lot_done.md"
    active_pl = vault_root / "_parking-lot.md"

    if not archive_pl.exists():
        raise FileNotFoundError(f"Archive PL not found: {archive_pl}")
    if not active_pl.exists():
        raise FileNotFoundError(f"Active PL not found: {active_pl}")

    archive_content = archive_pl.read_text(encoding="utf-8")
    active_content = active_pl.read_text(encoding="utf-8")

    # Find line containing item_id
    archive_lines = archive_content.splitlines(keepends=True)
    target_line = None
    remaining_lines = []

    for line in archive_lines:
        if item_id in line and not target_line:
            target_line = line
        else:
            remaining_lines.append(line)

    if target_line is None:
        raise ValueError(f"Item '{item_id}' not found in archive PL")

    ts = _ts()

    # Change [x] back to [ ] for re-activation
    clean_line = re.sub(r"\[x\]", "[ ]", target_line)
    # Remove archived comments
    clean_line = re.sub(r"\s*<!--.*?-->", "", clean_line).rstrip() + "\n"

    # Append to active PL
    new_active_content = active_content + clean_line
    new_archive_content = "".join(remaining_lines)

    _atomic_write(active_pl, new_active_content)
    _atomic_write(archive_pl, new_archive_content)

    _write_audit(vault_root, {
        "type": "REACTIVATION",
        "item_id": item_id,
        "target": "parking_lot",
        "from_archive": True,
        "ts": ts,
    })

    log.info("Reactivated PL item: %s", item_id)
    return {"item_id": item_id, "status": "reactivated"}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BL-178 AK-5: Re-Activation Helper")
    sub = parser.add_subparsers(dest="command", required=True)

    reopen = sub.add_parser("reopen", help="Reopen a BL item from archive")
    reopen.add_argument("--bl", required=True, help="BL-ID, e.g. BL-178")
    reopen.add_argument("--vault-root", required=True)

    reopen_pl = sub.add_parser("reopen-pl", help="Reopen a parking-lot item from archive")
    reopen_pl.add_argument("--item-id", required=True)
    reopen_pl.add_argument("--vault-root", required=True)

    return parser


def main(argv=None):
    parser = _build_parser()
    args = parser.parse_args(argv)
    vault_root = Path(args.vault_root)

    if args.command == "reopen":
        result = reactivate_bl(args.bl, vault_root)
        print(json.dumps(result, indent=2))
        return 0

    if args.command == "reopen-pl":
        result = reactivate_pl_item(args.item_id, vault_root)
        print(json.dumps(result, indent=2))
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
