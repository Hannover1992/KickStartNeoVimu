"""
quality_index_pointer_verify.py — BL-178 AK-7
Verifies pointer integrity between index files and detail files.
Per INV-INDEX-SPLIT-5 (BL-178, 2026-05-19).
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional


ACTIVE_INDEX_FILENAME = "_backlog_index.md"
ARCHIVE_INDEX_FILENAME = "_backlog_index_done.md"

ARCHIVE_STATUSES = {
    "DONE", "DECOMPOSED", "ARCHIVIERT", "ABSORBED",
    "ABSORBED_INTO_X", "ARCHIVED_ID_REUSED", "DUPLIKAT"
}
ACTIVE_STATUSES = {
    "DRAFT", "READY", "PLANNED", "IN_PROGRESS", "RUNNING",
    "SC-REIF", "FREEZE", "HOLD", "DEFERRED", "PARTIAL_DONE", "PHANTOM"
}


def _find_backlog_dir(vault_root: Path) -> Path:
    """Returns the Backlog directory path."""
    return vault_root / "Backlog"


def _extract_bl_entries_from_index(index_path: Path) -> list[dict]:
    """
    Parse index file lines. Expected format:
      | BL-NNN | ... | STATUS | ... | path/to/detail.md |
    or simpler table rows. Returns list of dicts with bl_id, status, vault_path.
    """
    entries = []
    if not index_path.exists():
        return entries

    content = index_path.read_text(encoding="utf-8", errors="replace")
    # Match table rows: | BL-NNN | ... | STATUS |
    # Supports 3-column: | BL-ID | Title | STATUS |
    # or 4-column: | BL-ID | Title | extra | STATUS |
    row_pattern = re.compile(
        r"\|\s*(BL-\d+[^\|]*?)\s*\|\s*[^\|]*\|\s*([A-Z_\-]+)\s*\|",
        re.IGNORECASE
    )
    for line in content.splitlines():
        m = row_pattern.search(line)
        if m:
            bl_id_raw = m.group(1).strip()
            status = m.group(2).strip().upper()
            # Extract clean BL id
            bl_id_match = re.match(r"(BL-\d+)", bl_id_raw)
            if not bl_id_match:
                continue
            bl_id = bl_id_match.group(1)
            entries.append({
                "bl_id": bl_id,
                "status": status,
                "source_file": str(index_path),
            })
    return entries


def _find_detail_file(bl_id: str, vault_root: Path) -> Optional[Path]:
    """
    Locates the detail file for a BL-ID in the Backlog directory.
    Searches for files starting with BL-NNN or containing BL-NNN.
    """
    backlog_dir = _find_backlog_dir(vault_root)
    if not backlog_dir.exists():
        return None

    # Direct slug folder (new style: Backlog/BL-NNN-slug/_manifest.md)
    for entry in backlog_dir.iterdir():
        if entry.is_dir() and entry.name.startswith(bl_id):
            manifest = entry / "_manifest.md"
            if manifest.exists():
                return manifest

    # Flat file style: Backlog/BL-NNN-slug.md
    for entry in backlog_dir.iterdir():
        if entry.is_file() and entry.name.startswith(bl_id):
            return entry

    return None


def _read_detail_status(detail_path: Path) -> Optional[str]:
    """Extract status from YAML frontmatter of detail file."""
    try:
        content = detail_path.read_text(encoding="utf-8", errors="replace")
        # Match frontmatter status field
        m = re.search(r"^status:\s*['\"]?([A-Z_\-]+)['\"]?\s*$", content, re.MULTILINE | re.IGNORECASE)
        if m:
            return m.group(1).strip().upper()
    except Exception:
        pass
    return None


def check_active_index_pointer_resolves(bl_id: str, vault_root: Path) -> dict:
    """
    Checks that an active-index entry for bl_id resolves to an existing detail file.
    Returns: {ok: bool, bl_id: str, violation: str|None}
    """
    active_index = vault_root / ACTIVE_INDEX_FILENAME
    entries = _extract_bl_entries_from_index(active_index)
    entry = next((e for e in entries if e["bl_id"] == bl_id), None)

    if entry is None:
        return {"ok": False, "bl_id": bl_id, "violation": f"{bl_id} not found in active index {active_index}"}

    detail = _find_detail_file(bl_id, vault_root)
    if detail is None:
        return {"ok": False, "bl_id": bl_id, "violation": f"Detail file missing for {bl_id} (active index entry exists)"}

    return {"ok": True, "bl_id": bl_id, "violation": None}


def check_archive_index_pointer_resolves(bl_id: str, vault_root: Path) -> dict:
    """
    Checks that an archive-index entry for bl_id resolves to an existing detail file.
    Returns: {ok: bool, bl_id: str, violation: str|None}
    """
    archive_index = vault_root / ARCHIVE_INDEX_FILENAME
    entries = _extract_bl_entries_from_index(archive_index)
    entry = next((e for e in entries if e["bl_id"] == bl_id), None)

    if entry is None:
        return {"ok": False, "bl_id": bl_id, "violation": f"{bl_id} not found in archive index {archive_index}"}

    detail = _find_detail_file(bl_id, vault_root)
    if detail is None:
        return {"ok": False, "bl_id": bl_id, "violation": f"Detail file missing for {bl_id} (archive index entry exists)"}

    return {"ok": True, "bl_id": bl_id, "violation": None}


def check_detail_status_matches_index(bl_id: str, vault_root: Path) -> dict:
    """
    Checks status consistency: if in active index, status must be in ACTIVE_STATUSES.
    If in archive index, status must be in ARCHIVE_STATUSES.
    Returns: {ok: bool, bl_id: str, violation: str|None}
    """
    active_index = vault_root / ACTIVE_INDEX_FILENAME
    archive_index = vault_root / ARCHIVE_INDEX_FILENAME

    active_entries = _extract_bl_entries_from_index(active_index)
    archive_entries = _extract_bl_entries_from_index(archive_index)

    in_active = next((e for e in active_entries if e["bl_id"] == bl_id), None)
    in_archive = next((e for e in archive_entries if e["bl_id"] == bl_id), None)

    # INV-INDEX-SPLIT-1: must not be in both
    if in_active and in_archive:
        return {"ok": False, "bl_id": bl_id, "violation": f"{bl_id} appears in BOTH active and archive index (INV-INDEX-SPLIT-1 violated)"}

    detail = _find_detail_file(bl_id, vault_root)
    if detail is None:
        return {"ok": False, "bl_id": bl_id, "violation": f"Detail file missing for {bl_id}"}

    detail_status = _read_detail_status(detail)
    if detail_status is None:
        return {"ok": False, "bl_id": bl_id, "violation": f"Cannot read status from detail file {detail}"}

    if in_active:
        index_status = in_active["status"]
        if detail_status in ARCHIVE_STATUSES:
            return {
                "ok": False, "bl_id": bl_id,
                "violation": f"{bl_id} in active index but detail status={detail_status} is archive-bound"
            }
        return {"ok": True, "bl_id": bl_id, "violation": None}

    if in_archive:
        if detail_status in ACTIVE_STATUSES:
            return {
                "ok": False, "bl_id": bl_id,
                "violation": f"{bl_id} in archive index but detail status={detail_status} is active"
            }
        return {"ok": True, "bl_id": bl_id, "violation": None}

    return {"ok": False, "bl_id": bl_id, "violation": f"{bl_id} not found in either index"}


def batch_check(vault_root: Path, bl_ids: Optional[list[str]] = None) -> dict:
    """
    Runs appropriate checks for all BLs (or given list).
    - Active-only items: check_active_index_pointer_resolves + check_detail_status_matches_index
    - Archive-only items: check_archive_index_pointer_resolves + check_detail_status_matches_index
    - Both indexes: check_detail_status_matches_index (INV-INDEX-SPLIT-1 violation)
    Returns: {ok_count: int, violation_count: int, violations: list[dict]}
    """
    active_index = vault_root / ACTIVE_INDEX_FILENAME
    archive_index = vault_root / ARCHIVE_INDEX_FILENAME

    active_entries = _extract_bl_entries_from_index(active_index)
    archive_entries = _extract_bl_entries_from_index(archive_index)

    active_ids = {e["bl_id"] for e in active_entries}
    archive_ids = {e["bl_id"] for e in archive_entries}

    all_bl_ids = bl_ids or list(active_ids | archive_ids)

    violations = []
    checks_run = 0

    for bl_id in sorted(all_bl_ids):
        in_active = bl_id in active_ids
        in_archive = bl_id in archive_ids

        if in_active:
            r = check_active_index_pointer_resolves(bl_id, vault_root)
            checks_run += 1
            if not r["ok"]:
                violations.append(r)

        if in_archive:
            r = check_archive_index_pointer_resolves(bl_id, vault_root)
            checks_run += 1
            if not r["ok"]:
                violations.append(r)

        # Status consistency check for all known BLs
        r = check_detail_status_matches_index(bl_id, vault_root)
        checks_run += 1
        if not r["ok"]:
            violations.append(r)

    ok_count = checks_run - len(violations)
    return {
        "ok_count": ok_count,
        "violation_count": len(violations),
        "violations": violations,
    }


def main():
    parser = argparse.ArgumentParser(
        description="BL-178 AK-7 — Index Pointer Integrity Verifier"
    )
    parser.add_argument("--vault-root", required=True, help="Path to vault root directory")
    parser.add_argument("--bl-id", help="Single BL-ID to check (e.g. BL-178)")
    parser.add_argument("--all", action="store_true", help="Check all BLs found in index files")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")
    args = parser.parse_args()

    vault_root = Path(args.vault_root)
    if not vault_root.exists():
        print(f"ERROR: vault-root does not exist: {vault_root}", file=sys.stderr)
        sys.exit(1)

    if args.bl_id:
        result = check_detail_status_matches_index(args.bl_id, vault_root)
        r2 = check_active_index_pointer_resolves(args.bl_id, vault_root)
        r3 = check_archive_index_pointer_resolves(args.bl_id, vault_root)
        violations = [r for r in [result, r2, r3] if not r["ok"]]
        output = {
            "bl_id": args.bl_id,
            "ok_count": 3 - len(violations),
            "violation_count": len(violations),
            "violations": violations,
        }
    elif args.all:
        output = batch_check(vault_root)
    else:
        parser.print_help()
        sys.exit(0)

    if args.json_output:
        print(json.dumps(output, indent=2))
    else:
        print(f"OK: {output.get('ok_count', 0)}  Violations: {output.get('violation_count', 0)}")
        for v in output.get("violations", []):
            print(f"  VIOLATION [{v['bl_id']}]: {v['violation']}")

    if output.get("violation_count", 0) > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
