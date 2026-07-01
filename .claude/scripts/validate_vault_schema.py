#!/usr/bin/env python3
"""
validate_vault_schema.py — Vault-Doc Frontmatter-Validator (BL-161 AK-6).

Prueft Vault-Docs auf Schema-Konsistenz gemaess .claude/meta/schemas/vault_quality_schema.md.

Pflicht-Felder ALL:  type, feature, bl-item, created, updated, tags
Extra fuer Model:    maturity_level, w_total
Extra fuer Spec:     ak_count, inv_count
Extra fuer Task:     phase
Extra fuer Blueprint: version (nein, optional)

Aufruf:
    python validate_vault_schema.py check <doc_path>
        Pruefe einen einzelnen Doc.

    python validate_vault_schema.py scan <vault_root>
        Scannt alle .md-Dateien im vault_root.

    python validate_vault_schema.py report <vault_root>
        Gibt strukturierten Quality-Report aus (Markdown-Format).

    python validate_vault_schema.py check <doc_path> --json
        JSON-Output fuer Pre-Write-Hook-Integration.

Exit-Codes:
    0  OK
    1  WARN (optionale Felder fehlen, nicht-blocking)
    2  ERROR (Pflicht-Felder fehlen — BLOCKS Write)
    3  USAGE / Internal-Error
"""
from __future__ import annotations

import sys
import json
import re
import argparse
from pathlib import Path
from typing import Optional

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. pip install pyyaml", file=sys.stderr)
    sys.exit(3)

# BL-309 Phase A: type:truth-Vertrag (EINE Quelle). Dual-Read-Resilienz wenn Modul fehlt.
try:
    import truth_schema
except ImportError:
    truth_schema = None  # type: ignore

# Pflicht-Felder fuer ALLE Vault-Docs
PFLICHT_ALL: list[str] = ["type", "feature", "bl-item", "created", "updated", "tags"]

# Pflicht-Felder pro Doc-Typ
PFLICHT_PRO_TYP: dict[str, list[str]] = {
    "model": ["maturity_level", "w_total"],
    "spec": ["ak_count", "inv_count"],
    "task-definition": ["phase"],
    "blueprint": [],
    "crumbs": [],
    "truth": [],  # truth-spezifische Pflichtfelder prueft truth_schema.validate_truth (BL-309 Phase A)
}

# Erlaubte doc-type Werte
ALLOWED_TYPES: set[str] = {
    "model", "spec", "task-definition", "blueprint", "crumbs",
    "implementation-log", "research", "domain-glossary",
    "truth",  # BL-309 Phase A: atomare Wahrheit (1 Wahrheit = 1 Datei)
}

# ISO-Datum-Format (YYYY-MM-DD)
ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Tags muessen bl/-Prefix enthalten (mindestens ein Tag mit bl/ oder type/)
REQUIRED_TAG_PREFIXES: list[str] = ["bl/", "type/"]


def lese_frontmatter(path: Path) -> tuple[Optional[dict], str]:
    """Liest YAML-Frontmatter + Body. Returns (frontmatter_dict, body_str)."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return None, f"Lesefehler: {exc}"
    m = re.match(r"^---\n(.+?)\n---\n(.*)$", text, re.DOTALL)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError as exc:
        return None, f"YAML-Parse-Fehler: {exc}"
    return (fm if isinstance(fm, dict) else None), m.group(2)


def pruefe_pflichtfelder(fm: dict) -> list[tuple[str, str]]:
    """Pruefe ALL + typ-spezifische Pflichtfelder. Returns [(severity, message)]."""
    issues: list[tuple[str, str]] = []

    # ALL-Felder
    for field in PFLICHT_ALL:
        val = fm.get(field)
        if val is None or val == "" or val == []:
            issues.append(("ERROR", f"Pflicht-Feld '{field}' fehlt oder leer"))

    # Datum-Format
    for date_field in ("created", "updated"):
        val = fm.get(date_field)
        if val and not ISO_DATE_RE.match(str(val)):
            issues.append(("WARN", f"'{date_field}'={val!r} kein ISO-Datum (YYYY-MM-DD)"))

    # Tags: mindestens ein bl/ und ein type/ Tag
    tags = fm.get("tags")
    if isinstance(tags, list):
        for prefix in REQUIRED_TAG_PREFIXES:
            if not any(str(t).startswith(prefix) for t in tags):
                issues.append(("WARN", f"tags: kein Tag mit Prefix '{prefix}' gefunden"))
    elif tags is not None:
        issues.append(("ERROR", "tags muss eine Liste sein"))

    # type-Feld Wert pruefen
    doc_type = fm.get("type")
    if doc_type and doc_type not in ALLOWED_TYPES:
        issues.append(("WARN", f"type='{doc_type}' nicht in erlaubten Typen {ALLOWED_TYPES}"))

    # Typ-spezifische Pflichtfelder
    if doc_type and doc_type in PFLICHT_PRO_TYP:
        for field in PFLICHT_PRO_TYP[doc_type]:
            val = fm.get(field)
            if val is None or val == "":
                issues.append(("ERROR", f"Typ '{doc_type}': Pflicht-Feld '{field}' fehlt"))

    return issues


def pruefe_tag_konsistenz(fm: dict, tag_aliases: dict[str, str]) -> list[tuple[str, str]]:
    """Pruefe ob Tags kanonische Form haben. tag_aliases: alias -> canonical."""
    issues: list[tuple[str, str]] = []
    tags = fm.get("tags")
    if not isinstance(tags, list):
        return issues
    for tag in tags:
        tag_str = str(tag)
        if tag_str in tag_aliases:
            canonical = tag_aliases[tag_str]
            issues.append(("WARN", f"Tag '{tag_str}' ist Alias fuer '{canonical}' — kanonische Form verwenden"))
    return issues


def pruefe_backlink_integritaet(fm: dict, vault_root: Optional[Path]) -> list[tuple[str, str]]:
    """Pruefe ob related_bl-Eintraege tatsaechlich existieren."""
    issues: list[tuple[str, str]] = []
    if vault_root is None:
        return issues
    related = fm.get("related_bl") or fm.get("related_bls") or []
    if isinstance(related, str):
        related = [related]
    if not isinstance(related, list):
        return issues
    for bl_ref in related:
        # Erwartet Format "BL-XXX"
        bl_str = str(bl_ref)
        if re.match(r"^BL-\d+$", bl_str):
            slug_pattern = f"BL-{bl_str.split('-')[1]}-*"
            matches = list(vault_root.glob(f"Backlog/{slug_pattern}"))
            if not matches:
                issues.append(("WARN", f"related_bl '{bl_str}' hat kein Backlog-Verzeichnis in {vault_root}/Backlog/"))
    return issues


def validiere_doc(
    doc_path: Path,
    vault_root: Optional[Path] = None,
    tag_aliases: Optional[dict[str, str]] = None,
) -> list[tuple[str, str]]:
    """Vollstaendige Validierung eines Docs. Returns [(severity, message)]."""
    fm, _ = lese_frontmatter(doc_path)
    if fm is None:
        return [("WARN", "Kein YAML-Frontmatter gefunden — legacy doc")]

    issues = pruefe_pflichtfelder(fm)
    if tag_aliases:
        issues.extend(pruefe_tag_konsistenz(fm, tag_aliases))
    issues.extend(pruefe_backlink_integritaet(fm, vault_root))
    # BL-309 Phase A: truth-spezifische Validierung (Enums/ID-Form/typisierte Kanten)
    if fm.get("type") == "truth" and truth_schema is not None:
        issues.extend(truth_schema.validate_truth(fm))
    return issues


def lade_tag_aliases(vault_root: Path) -> dict[str, str]:
    """Laedt tag-aliases.md falls vorhanden. Returns alias->canonical map."""
    aliases_path = vault_root / "Libraries/SemanticLibrary/_global/tag-aliases.md"
    if not aliases_path.exists():
        return {}
    aliases: dict[str, str] = {}
    text = aliases_path.read_text(encoding="utf-8", errors="replace")
    # Format: | alias1\|alias2 | canonical |
    for line in text.splitlines():
        m = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|", line)
        if m and not line.startswith("|---"):
            raw_aliases = m.group(1)
            canonical = m.group(2).strip()
            if canonical and not canonical.startswith("-"):
                for alias in raw_aliases.split("|"):
                    alias = alias.strip()
                    if alias and alias != canonical:
                        aliases[alias] = canonical
    return aliases


def cmd_check(doc_path: Path, vault_root: Optional[Path], json_mode: bool) -> int:
    """Pruefe einzelnen Doc."""
    if not doc_path.exists():
        msg = f"ERROR: {doc_path} nicht gefunden"
        if json_mode:
            print(json.dumps({"path": str(doc_path), "status": "NOT_FOUND", "issues": []}))
        else:
            print(msg, file=sys.stderr)
        return 2

    tag_aliases = lade_tag_aliases(vault_root) if vault_root else {}
    issues = validiere_doc(doc_path, vault_root, tag_aliases)
    errors = [i for i in issues if i[0] == "ERROR"]
    warns = [i for i in issues if i[0] == "WARN"]
    status = "ERROR" if errors else ("WARN" if warns else "OK")

    if json_mode:
        print(json.dumps({
            "path": str(doc_path),
            "status": status,
            "issues": [{"severity": s, "message": m} for s, m in issues],
        }, indent=2))
    else:
        if not issues:
            print(f"OK: {doc_path}")
        else:
            print(f"[{status}] {doc_path}")
            for severity, msg in issues:
                print(f"  [{severity}] {msg}")

    return 2 if errors else (1 if warns else 0)


def cmd_scan(vault_root: Path) -> int:
    """Scannt alle Vault-Docs."""
    if not vault_root.exists():
        print(f"ERROR: vault_root {vault_root} nicht gefunden", file=sys.stderr)
        return 2

    tag_aliases = lade_tag_aliases(vault_root)
    total = 0
    error_count = 0
    warn_count = 0
    max_exit = 0

    for md_path in sorted(vault_root.rglob("*.md")):
        rel = str(md_path.relative_to(vault_root)).replace("\\", "/")
        if any(skip in rel for skip in ["Sources/_pileOfMud_snapshot/", ".claude/"]):
            continue
        total += 1
        issues = validiere_doc(md_path, vault_root, tag_aliases)
        errors = [i for i in issues if i[0] == "ERROR"]
        warns = [i for i in issues if i[0] == "WARN"]
        if errors:
            error_count += 1
            print(f"[ERROR] {rel}")
            for _, msg in errors:
                print(f"  {msg}")
            max_exit = max(max_exit, 2)
        elif warns:
            warn_count += 1
            max_exit = max(max_exit, 1)

    print(f"\nScan: {total} Docs, {error_count} ERROR, {warn_count} WARN, {total - error_count - warn_count} OK")
    return max_exit


def cmd_report(vault_root: Path) -> int:
    """Gibt Quality-Report als Markdown aus."""
    if not vault_root.exists():
        print(f"ERROR: vault_root {vault_root} nicht gefunden", file=sys.stderr)
        return 2

    tag_aliases = lade_tag_aliases(vault_root)
    results: list[tuple[str, str, list[tuple[str, str]]]] = []

    for md_path in sorted(vault_root.rglob("*.md")):
        rel = str(md_path.relative_to(vault_root)).replace("\\", "/")
        if any(skip in rel for skip in ["Sources/_pileOfMud_snapshot/", ".claude/"]):
            continue
        issues = validiere_doc(md_path, vault_root, tag_aliases)
        if issues:
            results.append((rel, "ERROR" if any(s == "ERROR" for s, _ in issues) else "WARN", issues))

    total_scanned = sum(1 for _ in vault_root.rglob("*.md"))
    error_docs = [r for r in results if r[1] == "ERROR"]
    warn_docs = [r for r in results if r[1] == "WARN"]

    print("# Vault Quality Report — BL-161 AK-6")
    print(f"\n**Gescannt:** {total_scanned} Docs")
    print(f"**Fehler:** {len(error_docs)} Docs mit ERROR")
    print(f"**Warnungen:** {len(warn_docs)} Docs mit WARN")
    print(f"**OK:** {total_scanned - len(results)} Docs\n")

    if error_docs:
        print("## ERROR Docs\n")
        for rel, _, issues in error_docs:
            print(f"### `{rel}`")
            for severity, msg in issues:
                print(f"- [{severity}] {msg}")
            print()

    if warn_docs:
        print("## WARN Docs\n")
        for rel, _, issues in warn_docs[:20]:  # Max 20 zur Uebersicht
            print(f"- `{rel}`: {'; '.join(m for _, m in issues[:3])}")

    return 2 if error_docs else (1 if warn_docs else 0)


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="validate_vault_schema",
        description="BL-161 AK-6: Frontmatter-Validator fuer Vault-Docs",
    )
    parser.add_argument("--json", action="store_true", help="JSON-Output fuer Hook-Integration")
    parser.add_argument("--vault-root", type=Path, default=None, help="Vault-Root fuer Backlink-Checks")

    sub = parser.add_subparsers(dest="cmd", required=True)

    p_check = sub.add_parser("check", help="Einzelnen Doc validieren")
    p_check.add_argument("doc_path", type=Path)

    p_scan = sub.add_parser("scan", help="Vault-weit scannen")
    p_scan.add_argument("vault_root", type=Path)

    p_report = sub.add_parser("report", help="Markdown Quality-Report ausgeben")
    p_report.add_argument("vault_root", type=Path)

    args = parser.parse_args()

    if args.cmd == "check":
        return cmd_check(args.doc_path, args.vault_root, args.json)
    if args.cmd == "scan":
        return cmd_scan(args.vault_root)
    if args.cmd == "report":
        return cmd_report(args.vault_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
