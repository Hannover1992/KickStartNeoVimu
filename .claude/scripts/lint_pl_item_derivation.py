#!/usr/bin/env python3
"""
lint_pl_item_derivation.py — BL-174 AK-18 Linter

Prueft PL-Item-Files auf derivation_source + metric_provenance compliance.
Glob: Vault/Backlog/*/6_PL/*_PL_Items.md

Exit Codes:
  0  OK   (hand-waved ratio <= threshold)
  1  FAIL (hand-waved ratio  > threshold)
  2  Error (vault not found / file-read error)
"""

import argparse
import os
import re
import sys
from datetime import date, datetime
from pathlib import Path

LABEL = "[lint_pl_item_derivation]"

# Regex: valid derivation_source values
# AK-18 = self-reference fuer Linter/Hook-Items (PL-RUN-10 2026-05-17)
DERIV_SRC_RE = re.compile(
    r"^AK-(15|16|17|18)(\s*\+\s*AK-(15|16|17|18))*(\s*\(.*?\))*$"
)

# Frontmatter extraction
FM_BLOCK_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)

# Key-value within frontmatter (simple: key: value, handles lists inline)
SCALAR_RE = re.compile(r"^(\s*)(\w[\w_-]*):\s*(.+)$")

# Markdown table row item fields (used in BL-165 style)
TABLE_ID_RE = re.compile(r"\|\s*id\s*\|\s*(\S+)\s*\|")
TABLE_FIELD_RE = re.compile(r"\|\s*([\w_-]+)\s*\|\s*(.+?)\s*\|")

# Section header for per-item blocks in markdown body
ITEM_SECTION_RE = re.compile(r"^#{2,4}\s+(PL-[\w-]+)")

# created_at / date field patterns
DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _parse_date(s: str):
    """Return date object from YYYY-MM-DD string or None."""
    if not s:
        return None
    m = DATE_RE.search(str(s))
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            return None
    return None


def _extract_frontmatter(text: str) -> str:
    """Return raw frontmatter block (between --- delimiters) or empty string."""
    m = FM_BLOCK_RE.match(text)
    if m:
        return m.group(1)
    return ""


def _parse_simple_yaml_scalar(fm: str, key: str):
    """
    Extract a scalar value for `key` from raw YAML frontmatter string.
    Handles: key: value  and  key: "value" and  key: 'value'
    Does NOT handle multi-line. Returns stripped string or None.
    """
    pattern = re.compile(
        r"^" + re.escape(key) + r":\s*(['\"]?)(.+?)\1\s*$",
        re.MULTILINE,
    )
    m = pattern.search(fm)
    if m:
        return m.group(2).strip()
    return None


def _parse_yaml_items_list(fm: str):
    """
    Parse the `items:` block from YAML frontmatter.
    Returns list of dicts, each representing one item.
    Handles indented block items starting with `  - id: ...`
    """
    items = []
    # Find `items:` line then scan indented block
    in_items = False
    current = {}
    item_indent = None

    for line in fm.splitlines():
        stripped = line.strip()

        if re.match(r"^items\s*:", line):
            in_items = True
            continue

        if not in_items:
            continue

        # Detect start of a new list item (leading `- `)
        list_item_m = re.match(r"^(\s+)-\s+(.*)", line)
        if list_item_m:
            indent = len(list_item_m.group(1))
            rest = list_item_m.group(2)
            if item_indent is None or indent <= item_indent:
                # New top-level item
                if current:
                    items.append(current)
                current = {}
                item_indent = indent
            # Parse inline key: value on same line as `-`
            kv = re.match(r"([\w_-]+):\s*(.+)", rest)
            if kv:
                current[kv.group(1)] = kv.group(2).strip().strip("'\"")
            continue

        # Continuation key-value under current item
        kv_m = re.match(r"(\s+)([\w_-]+):\s*(.+)", line)
        if kv_m and in_items and current is not None:
            indent = len(kv_m.group(1))
            if item_indent is not None and indent > item_indent:
                key = kv_m.group(2)
                val = kv_m.group(3).strip().strip("'\"")
                current[key] = val
            continue

        # Top-level key (not indented beyond items list) -> end of items block
        if in_items and line and not line[0].isspace() and not stripped.startswith("-"):
            break

    if current:
        items.append(current)

    return items


def _parse_table_items(text: str, file_path: Path, file_date):
    """
    Parse BL-165-style markdown table items.
    Each item is a `### PL-X-YY: ...` section containing a markdown table.
    Returns list of dicts with id, derivation_source, metric_provenance, created_date.
    """
    items = []
    current_id = None
    current_fields = {}

    for line in text.splitlines():
        # New item section?
        sec_m = ITEM_SECTION_RE.match(line)
        if sec_m:
            if current_id:
                current_fields.setdefault("id", current_id)
                current_fields.setdefault("created_date", file_date)
                items.append(current_fields)
            current_id = sec_m.group(1)
            current_fields = {"id": current_id, "created_date": file_date}
            continue

        if current_id is None:
            continue

        # Table row: | key | value |
        row_m = re.match(r"\|\s*([\w_-]+)\s*\|\s*(.+?)\s*\|", line)
        if row_m:
            key = row_m.group(1).strip()
            val = row_m.group(2).strip().strip("'\"")
            if key not in ("Feld", "---", "feld"):
                current_fields[key] = val

    if current_id:
        current_fields.setdefault("id", current_id)
        current_fields.setdefault("created_date", file_date)
        items.append(current_fields)

    return items


def parse_pl_items(file_path: Path):
    """
    Parse a PL-Items.md file and return list of item dicts.
    Tries YAML frontmatter items list first, then markdown table format.
    Each dict has at minimum: {id, derivation_source (or None), metric_provenance (or None), created_date (or None)}.
    """
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        print(f"{LABEL} ERROR reading {file_path}: {e}", file=sys.stderr)
        return None  # signal read error

    fm = _extract_frontmatter(text)

    # Try to get file-level date from frontmatter
    fm_date_str = _parse_simple_yaml_scalar(fm, "date") if fm else None
    file_date = _parse_date(fm_date_str) if fm_date_str else None
    if file_date is None:
        # Fallback to file mtime
        try:
            mtime = file_path.stat().st_mtime
            file_date = datetime.fromtimestamp(mtime).date()
        except OSError:
            file_date = None

    items = []

    # Strategy 1: YAML frontmatter `items:` list
    if fm and "items:" in fm:
        parsed = _parse_yaml_items_list(fm)
        for item in parsed:
            item.setdefault("id", item.get("id", "?"))
            # created_at from item or file date
            created_str = item.get("created_at") or item.get("created_date")
            item["created_date"] = _parse_date(created_str) or file_date
            items.append(item)

    # Strategy 2: Markdown table per-section format (BL-165 style)
    # Use when no frontmatter items found
    if not items:
        items = _parse_table_items(text, file_path, file_date)

    return items


def find_pl_files(vault_root: Path):
    """Glob for all PL-Items.md files under vault_root/Backlog/*/6_PL/."""
    pattern = vault_root / "Backlog" / "*" / "6_PL" / "*_PL_Items.md"
    return sorted(pattern.parent.parent.parent.glob("*/6_PL/*_PL_Items.md"))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def is_derivation_valid(item: dict):
    """
    Returns True if item has valid derivation_source AND metric_provenance != hand_waved.
    """
    deriv = item.get("derivation_source", "") or ""
    deriv = str(deriv).strip()
    prov = item.get("metric_provenance", "") or ""
    prov = str(prov).strip().lower()

    if not deriv:
        return False, "missing_field: derivation_source absent"
    if not DERIV_SRC_RE.match(deriv):
        return False, f"fail_hand_waved: derivation_source='{deriv}' does not match AK-(15|16|17|18)"
    if prov == "hand_waved":
        return False, "fail_hand_waved: metric_provenance=hand_waved"
    if not prov:
        return False, "missing_field: metric_provenance absent"
    return True, "pass"


def check_item(item: dict, file_path: Path, ignore_pre_date):
    """
    Returns (status, reason) where status in:
      pass | fail_hand_waved | grandfathered | missing_field
    """
    created = item.get("created_date")

    if ignore_pre_date is not None and created is not None:
        if created < ignore_pre_date:
            return "grandfathered", f"created_date={created} < ignore_pre={ignore_pre_date}"

    valid, reason = is_derivation_valid(item)
    if valid:
        return "pass", reason

    # Classify: missing_field vs fail_hand_waved
    if reason.startswith("missing_field"):
        return "missing_field", reason
    return "fail_hand_waved", reason


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "BL-174 AK-18 Linter — prueft PL-Item-Files auf "
            "derivation_source + metric_provenance compliance."
        )
    )
    parser.add_argument(
        "--vault-root",
        "--vault",
        dest="vault_root",
        default=None,
        help=(
            "Root des Vault (default: env CLAUDE_VAULT_ROOT oder "
            "C:/Users/Administrator/Documents/OmniCommand)"
        ),
    )
    parser.add_argument(
        "--ignore-pre",
        dest="ignore_pre",
        default="2026-05-17",
        metavar="YYYY-MM-DD",
        help=(
            "Grandfather: Items mit created_date < diesem Datum ueberspringen. "
            "Default 2026-05-17 (BL-174 Cut-Off — existing BL-165 PL-Items "
            "vor BL-174 Linter werden grandfathered, BL-174-Items+ gescannt). "
            "Override mit '' (leer) deaktiviert Grandfather."
        ),
    )
    parser.add_argument(
        "--threshold",
        dest="threshold",
        type=float,
        default=5.0,
        help="Fail-Threshold in Prozent (default: 5.0). Exit 1 wenn > X%% hand-waved.",
    )
    return parser.parse_args()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    args = parse_args()

    # Resolve vault root
    vault_root_str = (
        args.vault_root
        or os.environ.get("CLAUDE_VAULT_ROOT")
        or r"C:\Users\Administrator\Documents\OmniCommand"
    )
    vault_root = Path(vault_root_str)

    if not vault_root.exists():
        print(
            f"{LABEL} ERROR: vault root not found: {vault_root}",
            file=sys.stderr,
        )
        sys.exit(2)

    # Parse ignore-pre date
    ignore_pre_date = None
    if args.ignore_pre:
        ignore_pre_date = _parse_date(args.ignore_pre)
        if ignore_pre_date is None:
            print(
                f"{LABEL} ERROR: --ignore-pre must be YYYY-MM-DD, got: {args.ignore_pre}",
                file=sys.stderr,
            )
            sys.exit(2)

    threshold_pct = args.threshold
    threshold_ratio = threshold_pct / 100.0

    # Find files
    backlog_dir = vault_root / "Backlog"
    if not backlog_dir.exists():
        print(f"{LABEL} ERROR: Backlog dir not found: {backlog_dir}", file=sys.stderr)
        sys.exit(2)

    pl_files = sorted(backlog_dir.glob("*/6_PL/*_PL_Items.md"))

    print(f"{LABEL} Scanning {backlog_dir}/*/6_PL/*_PL_Items.md")

    read_error_count = 0
    all_items = []  # list of (file_path, item_dict)

    for f in pl_files:
        items = parse_pl_items(f)
        if items is None:
            read_error_count += 1
            continue
        for item in items:
            all_items.append((f, item))

    if read_error_count > 0:
        print(
            f"{LABEL} ERROR: {read_error_count} file(s) could not be read",
            file=sys.stderr,
        )
        sys.exit(2)

    total_items = len(all_items)
    print(f"{LABEL} Found {total_items} PL-Items in {len(pl_files)} files")

    # Classify items
    failed_hand_waved = []
    failed_missing = []
    grandfathered_count = 0
    passed_count = 0
    checked_count = 0

    for f, item in all_items:
        status, reason = check_item(item, f, ignore_pre_date)
        item_id = item.get("id", "?")

        if status == "grandfathered":
            grandfathered_count += 1
        elif status == "pass":
            checked_count += 1
            passed_count += 1
        elif status == "fail_hand_waved":
            checked_count += 1
            failed_hand_waved.append((f, item_id, reason))
        elif status == "missing_field":
            checked_count += 1
            failed_missing.append((f, item_id, reason))

    non_grandfathered = checked_count
    fail_hw_count = len(failed_hand_waved)
    fail_mf_count = len(failed_missing)
    total_fail = fail_hw_count + fail_mf_count

    ratio = total_fail / max(non_grandfathered, 1)
    actual_pct = ratio * 100.0

    if ignore_pre_date:
        print(f"{LABEL} Skipped (grandfathered <{ignore_pre_date}): {grandfathered_count}")
    else:
        print(f"{LABEL} Skipped (grandfathered): 0 (no --ignore-pre set)")

    print(f"{LABEL} Checked: {non_grandfathered}")
    print(f"{LABEL} FAIL hand-waved: {fail_hw_count} ({actual_pct:.1f}%)")
    print(f"{LABEL} FAIL missing_field: {fail_mf_count}")

    if total_fail > 0:
        print()
        print("Failed items:")
        for f, item_id, reason in failed_hand_waved + failed_missing:
            rel = f.relative_to(vault_root) if f.is_relative_to(vault_root) else f
            print(f"  - {rel}: {item_id} — {reason}")

    print()

    # Threshold evaluation
    # Note: hand-waved ratio includes both fail_hand_waved and missing_field
    if non_grandfathered == 0:
        exit_code = 0
        print(f"THRESHOLD={threshold_pct:.1f}%, ACTUAL=0.0% (no items checked) => EXIT=0")
    elif ratio > threshold_ratio:
        exit_code = 1
        print(
            f"THRESHOLD={threshold_pct:.1f}%, ACTUAL={actual_pct:.1f}% => EXIT=1 (FAIL)"
        )
    else:
        exit_code = 0
        print(
            f"THRESHOLD={threshold_pct:.1f}%, ACTUAL={actual_pct:.1f}% => EXIT=0 (PASS)"
        )

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
