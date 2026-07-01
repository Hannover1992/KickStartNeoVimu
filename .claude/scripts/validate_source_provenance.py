#!/usr/bin/env python3
"""
validate_source_provenance.py — Schema-Validator fuer source_provenance Frontmatter

BL-160 AK-9: Validiert Vault-Doc gegen AK-1-Schema (siehe meta/schemas/source_provenance.schema.json).

Aufruf:
    python validate_source_provenance.py check <doc_path>
        Pruefe einen einzelnen Vault-Doc (Frontmatter-Validation).

    python validate_source_provenance.py scan <vault_root>
        Scannt alle .md-Dateien im vault_root, sammelt Validation-Errors.
        Tolerant gegenueber legacy-Markern (source_kind=legacy ist OK).

    python validate_source_provenance.py --json <doc_path>
        JSON-Output fuer Pre-Commit-Hook-Integration.

Exit-Codes:
    0  OK / valid
    1  WARN (Optional-Feld fehlt, nicht-blocking)
    2  ERROR (Pflicht-Feld fehlt, Bidir-Mismatch, Schema-Violation)
    3  USAGE / Internal-Error (PyYAML missing etc.)
"""

import sys
import argparse
import json
import re
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. Install via: pip install pyyaml", file=sys.stderr)
    sys.exit(3)

# Schema-Konstanten (aus source_provenance.schema.json reduziert)
REQUIRED_FIELDS_PROVENANCE = ["source", "source_kind", "fetched_at"]
ALLOWED_SOURCE_KINDS = {"confluence", "jira", "github", "userspeech", "pileOfMud", "legacy", "derived"}
ALLOWED_ROLES = {"original", "snapshot", "finding", "spec", "model", "blueprint", "code"}
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?Z?)?$")
URL_RE = re.compile(r"^https?://")


def read_frontmatter(path: Path) -> tuple[Optional[dict], str]:
    """Liest YAML-Frontmatter + Body. Returns (frontmatter_dict, body_str) oder (None, content) bei kein Frontmatter."""
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\n(.+?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None, text
    return (fm if isinstance(fm, dict) else None), m.group(2)


def validate_source_provenance(fm: dict) -> list[tuple[str, str]]:
    """Validiere source_provenance-Block. Returns Liste (severity, message): severity in {ERROR, WARN}."""
    issues: list[tuple[str, str]] = []
    sp = fm.get("source_provenance")
    if not sp:
        issues.append(("WARN", "source_provenance Feld fehlt — pre-BL-160 legacy doc"))
        return issues
    if not isinstance(sp, dict):
        issues.append(("ERROR", "source_provenance MUSS dict sein"))
        return issues
    for field in REQUIRED_FIELDS_PROVENANCE:
        if field not in sp or sp[field] in (None, "", []):
            issues.append(("ERROR", f"source_provenance.{field} ist Pflicht"))
    kind = sp.get("source_kind")
    if kind and kind not in ALLOWED_SOURCE_KINDS:
        issues.append(("ERROR", f"source_provenance.source_kind={kind!r} nicht in {ALLOWED_SOURCE_KINDS}"))
    fetched_at = sp.get("fetched_at")
    if fetched_at and not ISO_DATE_RE.match(str(fetched_at)):
        issues.append(("ERROR", f"source_provenance.fetched_at={fetched_at!r} kein ISO-Datum"))
    return issues


def validate_provenance_chain(fm: dict) -> list[tuple[str, str]]:
    """Validiere provenance_chain-Liste. Returns Liste (severity, message)."""
    issues: list[tuple[str, str]] = []
    chain = fm.get("provenance_chain")
    if chain is None:
        issues.append(("WARN", "provenance_chain fehlt — empfohlen ab Layer >= 1"))
        return issues
    if not isinstance(chain, list):
        issues.append(("ERROR", "provenance_chain MUSS Liste sein"))
        return issues
    prev_layer = -1
    prev_ts = ""
    for i, entry in enumerate(chain):
        if not isinstance(entry, dict):
            issues.append(("ERROR", f"provenance_chain[{i}] MUSS dict sein"))
            continue
        layer = entry.get("layer")
        if not isinstance(layer, int):
            issues.append(("ERROR", f"provenance_chain[{i}].layer MUSS int sein"))
        elif layer != prev_layer + 1 and prev_layer >= 0:
            issues.append(("ERROR", f"INV-SCHEMA-2: Layer-Sprung von {prev_layer} zu {layer} in chain[{i}]"))
        role = entry.get("role")
        if role and role not in ALLOWED_ROLES:
            issues.append(("ERROR", f"provenance_chain[{i}].role={role!r} nicht in {ALLOWED_ROLES}"))
        ts = entry.get("timestamp", "")
        if ts and prev_ts and str(ts) < str(prev_ts):
            issues.append(("ERROR", f"INV-SCHEMA-5: timestamp[{i}]={ts} < prev={prev_ts} (chronologie)"))
        prev_layer = layer if isinstance(layer, int) else prev_layer
        prev_ts = str(ts) if ts else prev_ts
    return issues


def cmd_check(doc_path: Path, json_mode: bool = False) -> int:
    """Pruefe Single-Doc. Returns Exit-Code."""
    if not doc_path.exists():
        print(f"ERROR: {doc_path} nicht gefunden", file=sys.stderr)
        return 2
    fm, _ = read_frontmatter(doc_path)
    if not fm:
        if json_mode:
            print(json.dumps({"path": str(doc_path), "status": "NO_FRONTMATTER", "issues": []}))
        else:
            print(f"WARN: {doc_path} hat kein YAML-Frontmatter")
        return 1
    issues = validate_source_provenance(fm) + validate_provenance_chain(fm)
    errors = [i for i in issues if i[0] == "ERROR"]
    warns = [i for i in issues if i[0] == "WARN"]
    if json_mode:
        print(json.dumps({
            "path": str(doc_path),
            "status": "ERROR" if errors else ("WARN" if warns else "OK"),
            "issues": [{"severity": s, "message": m} for s, m in issues]
        }, indent=2))
    else:
        if not issues:
            print(f"OK: {doc_path}")
        for severity, msg in issues:
            print(f"  [{severity}] {msg}")
    if errors:
        return 2
    if warns:
        return 1
    return 0


def cmd_scan(vault_root: Path) -> int:
    """Scannt Vault. Returns Exit-Code (max von allen Docs)."""
    if not vault_root.exists():
        print(f"ERROR: vault_root {vault_root} nicht gefunden", file=sys.stderr)
        return 2
    max_exit = 0
    total = 0
    errors_count = 0
    warns_count = 0
    for md_path in vault_root.rglob("*.md"):
        # Skip Libraries-Index + Sources-Snapshots (out-of-scope)
        rel = str(md_path.relative_to(vault_root)).replace("\\", "/")
        if "Sources/_pileOfMud_snapshot/" in rel:
            continue
        total += 1
        fm, _ = read_frontmatter(md_path)
        if not fm:
            continue
        issues = validate_source_provenance(fm) + validate_provenance_chain(fm)
        has_err = any(s == "ERROR" for s, _ in issues)
        has_warn = any(s == "WARN" for s, _ in issues)
        if has_err:
            errors_count += 1
            print(f"[ERROR] {rel}")
            for severity, msg in issues:
                if severity == "ERROR":
                    print(f"  {msg}")
            max_exit = max(max_exit, 2)
        elif has_warn:
            warns_count += 1
            max_exit = max(max_exit, 1)
    print(f"\nScan: {total} Docs, {errors_count} ERROR, {warns_count} WARN")
    return max_exit


def main() -> int:
    parser = argparse.ArgumentParser(prog="validate_source_provenance",
                                     description="BL-160 AK-9: Validator fuer source_provenance Schema")
    parser.add_argument("--json", action="store_true", help="JSON-Output fuer Pre-Commit-Hook")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="Single-Doc-Validierung")
    p_check.add_argument("doc_path", type=Path)

    p_scan = sub.add_parser("scan", help="Vault-Scan")
    p_scan.add_argument("vault_root", type=Path)

    args = parser.parse_args()
    if args.cmd == "check":
        return cmd_check(args.doc_path, args.json)
    if args.cmd == "scan":
        return cmd_scan(args.vault_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
