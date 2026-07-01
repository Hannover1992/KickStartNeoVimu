#!/usr/bin/env python3
"""
regenerate_backlog_index.py — Backlog-Index neu generieren.

AUDIT-002 (BL-151 VDD): Regeneriert _backlog_index.md mit allen BL-Items,
korrekten relativen Vault-Pfaden (keine Windows-Pfade), und aktuellem Datum.

Aufgabe:
  1. Vault-Root via resolve_vault_root.py aufloesen
  2. Glob {vault_root}/Backlog/BL-*.md (Huellen) UND {vault_root}/Backlog/BL-*/ (Folder)
  3. Pro BL: Frontmatter aus .md lesen (title, status, created, reifegrad/maturity)
  4. Vault-Pfad RELATIV zu vault_root schreiben
  5. Markdown-Tabelle: BL-ID | Title | Status | Vault-Pfad | Created | Reifegrad
  6. backlog_last_update auf heute
  7. Sortiert nach BL-Nummer aufsteigend

Aufruf:
  python3 regenerate_backlog_index.py [--dry-run]
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from datetime import date

# Vault-Root via resolve_vault_root (ARCH-N8)
_SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(_SCRIPTS_DIR))
try:
    from resolve_vault_root import resolve_vault_root as _resolve_vault_root_fn
    VAULT_ROOT = _resolve_vault_root_fn()
except ImportError:
    VAULT_ROOT = Path.home() / "Documents" / "OmniCommand"

# BL-333: format_version-Stamp (Writer=Follow, Wert via Loader-Call, kein eigenes Literal).
try:
    from resolve_format_version import resolve_format_version
except ImportError:  # Dual-Read-Resilienz: Loader fehlt -> kein Crash, Stamp wird weggelassen.
    def resolve_format_version(typ):  # type: ignore
        return None

TODAY = date.today().isoformat()  # 2026-05-02

# F4 (Sanity-Dynamic 2026-05-08): Generic ticket pattern (BL-, DCSRE-, JIRA-, etc.)
# Vorher hardcoded BL-NNN — jetzt generisch wie resolve_bl_path.py:_TICKET_PATTERN
_TICKET_NUM_RE = re.compile(r"^([A-Z][A-Z0-9_]*)-(\d+)")
# Backwards-compat fuer Code der noch _BL_NUM_RE erwartet (matcht BL-{NNN} explizit)
_BL_NUM_RE = re.compile(r"^BL-(\d+)")

# F4: vault-routing.json fuer subfolder + index_file lookup
_VAULT_ROUTING_DEFAULT = Path(__file__).parent.parent / "config" / "vault-routing.json"


def _load_vault_routing() -> dict | None:
    """Liest vault-routing.json (BOM-aware)."""
    if not _VAULT_ROUTING_DEFAULT.is_file():
        return None
    try:
        return json.loads(_VAULT_ROUTING_DEFAULT.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _match_rule_for_cwd(routing: dict, cwd: Path) -> dict | None:
    """Findet das passende detection.rules Pattern fuer cwd."""
    if not routing:
        return None
    cwd_str = str(cwd)
    rules = routing.get("detection", {}).get("rules", [])
    for rule in sorted(rules, key=lambda r: r.get("priority", 999)):
        pattern = rule.get("pattern", "")
        if not pattern or pattern == "*":
            continue
        if pattern.lower() in cwd_str.lower():
            return rule
    return None


def _resolve_backlog_subfolder() -> str:
    """F4: Resolves backlog.subfolder aus vault-routing.json (Fallback 'Backlog')."""
    routing = _load_vault_routing()
    if routing is None:
        return "Backlog"
    rule = _match_rule_for_cwd(routing, Path.cwd())
    if rule is None:
        return "Backlog"
    subfolder = rule.get("backlog", {}).get("subfolder", "")
    return subfolder if subfolder else "Backlog"


def _resolve_index_file(backlog: Path) -> Path:
    """F4: Resolves index_file aus vault-routing.json (Fallback {backlog}/_backlog_index.md)."""
    routing = _load_vault_routing()
    if routing is not None:
        rule = _match_rule_for_cwd(routing, Path.cwd())
        if rule is not None:
            index_file = rule.get("backlog", {}).get("index_file", "")
            if index_file:
                return Path(index_file)
    return backlog / "_backlog_index.md"


def _ticket_num(ticket_id: str) -> tuple[str, int]:
    """Generic Sortier-Tuple: (Prefix, Num). 'BL-001' → ('BL', 1), 'DCSRE-486' → ('DCSRE', 486)."""
    m = _TICKET_NUM_RE.match(ticket_id)
    if m:
        return (m.group(1), int(m.group(2)))
    return ("", 0)


def _parse_frontmatter(md_path: Path) -> dict[str, str]:
    """Liest YAML-Frontmatter inline (kein PyYAML noetig)."""
    try:
        text = md_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    fm_block = text[3:end]
    result: dict[str, str] = {}
    for line in fm_block.splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and val:
            result[key] = val
    return result


def _bl_num(bl_id: str) -> int:
    """Backwards-compat: gibt Num fuer BL-NNN, ignoriert andere Prefixes (Fallback 0)."""
    m = _BL_NUM_RE.match(bl_id)
    return int(m.group(1)) if m else 0


def collect_bl_items(backlog: Path) -> dict[str, dict]:
    """Sammelt alle BL-/DCSRE-/JIRA-Items aus Huellen (.md) und Folder-Verzeichnissen."""
    items: dict[str, dict] = {}

    # F4: Pass 1 — generischer Glob ueber alle .md, Filter via _TICKET_NUM_RE
    for md in backlog.glob("*.md"):
        if md.name == "_backlog_index.md":
            continue  # Index selbst nicht als Item zaehlen
        name = md.stem  # z.B. BL-153-semantische-pattern-library oder DCSRE-486-...
        m = _TICKET_NUM_RE.match(name)
        if not m:
            continue
        prefix, num = m.group(1), m.group(2)
        ticket_id_from_file = f"{prefix}-{num}"
        fm = _parse_frontmatter(md)
        # ID aus Frontmatter bevorzugen (normalisiert)
        bl_id = fm.get("id", ticket_id_from_file).strip().strip('"').strip("'")
        # Normalisiere ID — entferne eventuelle Suffixe (greife generisches Pattern)
        id_match = _TICKET_NUM_RE.match(bl_id)
        if id_match:
            bl_id = f"{id_match.group(1)}-{id_match.group(2)}"
        else:
            bl_id = ticket_id_from_file

        title = fm.get("title", name)
        status = fm.get("status", "UNKNOWN")
        created = fm.get("created", "")
        reifegrad = fm.get("reifegrad", fm.get("maturity", fm.get("reifegrad_hint", "")))

        rel_path = md.relative_to(VAULT_ROOT)

        if bl_id not in items:
            items[bl_id] = {
                "bl_id": bl_id,
                "title": title,
                "status": status,
                "created": created,
                "reifegrad": reifegrad,
                "vault_path": str(rel_path),
            }
        else:
            # Update wenn Huelle mehr Infos hat
            existing = items[bl_id]
            if not existing.get("title") or existing["title"] == name:
                existing["title"] = title
            if not existing.get("status") or existing["status"] == "UNKNOWN":
                existing["status"] = status
            if not existing.get("created"):
                existing["created"] = created
            if not existing.get("reifegrad"):
                existing["reifegrad"] = reifegrad

    # F4: Pass 2 — generischer Folder-Scan (BL-/DCSRE-/JIRA-/...)
    for folder in backlog.iterdir():
        if not folder.is_dir():
            continue
        name = folder.name
        m = _TICKET_NUM_RE.match(name)
        if not m:
            continue
        bl_id = f"{m.group(1)}-{m.group(2)}"
        rel_path = folder.relative_to(VAULT_ROOT)

        # Suche _manifest.md oder erstes .md im Folder fuer Frontmatter
        fm: dict[str, str] = {}
        manifest = folder / "_manifest.md"
        if manifest.is_file():
            fm = _parse_frontmatter(manifest)
        else:
            mds = list(folder.glob("*.md"))
            if mds:
                fm = _parse_frontmatter(mds[0])

        title = fm.get("title", "")
        status = fm.get("status", "")
        created = fm.get("created", "")
        reifegrad = fm.get("reifegrad", fm.get("maturity", fm.get("reifegrad_hint", "")))

        if bl_id not in items:
            items[bl_id] = {
                "bl_id": bl_id,
                "title": title or name,
                "status": status or "UNKNOWN",
                "created": created,
                "reifegrad": reifegrad,
                "vault_path": str(rel_path),
            }
        else:
            # Folder-Pfad als vault_path setzen (Folder > Huelle als primaerer Pfad)
            items[bl_id]["vault_path"] = str(rel_path)
            if title and not items[bl_id].get("title"):
                items[bl_id]["title"] = title
            if status and items[bl_id].get("status") in ("", "UNKNOWN"):
                items[bl_id]["status"] = status
            if created and not items[bl_id].get("created"):
                items[bl_id]["created"] = created
            if reifegrad and not items[bl_id].get("reifegrad"):
                items[bl_id]["reifegrad"] = reifegrad

    return items


def _escape_pipe(s: str) -> str:
    return s.replace("|", "\\|")


def render_index(items: dict[str, dict], total_count: int) -> str:
    """Rendert Markdown-Tabelle sortiert nach (Prefix, Nummer)."""
    sorted_items = sorted(items.values(), key=lambda x: _ticket_num(x["bl_id"]))

    # BL-333: format_version-Stamp (Writer=Follow). Loader-fehlt/None -> Stamp weglassen (G2e).
    _fv = resolve_format_version("backlog_index")
    _fv_lines = [f"format_version: {_fv}"] if _fv is not None else []

    lines = [
        f"---",
        *_fv_lines,
        f"backlog_counter: {total_count}",
        f'backlog_last_update: "{TODAY}"',
        f"---",
        "",
        "# Backlog Index",
        "",
        "| BL-ID | Title | Status | Vault-Pfad | Created | Reifegrad |",
        "|-------|-------|--------|------------|---------|-----------|",
    ]

    for item in sorted_items:
        bl_id = _escape_pipe(item["bl_id"])
        title = _escape_pipe(item.get("title", ""))
        status = _escape_pipe(item.get("status", ""))
        vault_path = _escape_pipe(item.get("vault_path", ""))
        created = _escape_pipe(item.get("created", ""))
        reifegrad = _escape_pipe(item.get("reifegrad", ""))
        lines.append(
            f"| {bl_id} | {title} | {status} | {vault_path} | {created} | {reifegrad} |"
        )

    lines.append("")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    dry_run = "--dry-run" in argv

    # F4: subfolder-aware (Option A Vault-Layout: vault_root/{subfolder}/Backlog)
    backlog_subfolder = _resolve_backlog_subfolder()
    backlog = VAULT_ROOT / backlog_subfolder
    if not backlog.is_dir():
        print(f"ERROR: Backlog-Verzeichnis fehlt: {backlog}", file=sys.stderr)
        return 1

    print(f"Vault-Root: {VAULT_ROOT}", file=sys.stderr)
    print(f"Backlog: {backlog}", file=sys.stderr)

    items = collect_bl_items(backlog)
    # F4: max ueber BL-Prefixes nur (BL-Counter ist BL-spezifisch)
    bl_only_nums = [_bl_num(k) for k in items if k.startswith("BL-")]
    total_count = max(bl_only_nums, default=0)

    content = render_index(items, total_count)

    # F4: index_file aus vault-routing.json (Fallback backlog/_backlog_index.md)
    index_path = _resolve_index_file(backlog)

    if dry_run:
        print(content)
        print(f"\n[DRY-RUN] Wuerde {index_path} schreiben ({len(items)} Items, BL-Counter={total_count})", file=sys.stderr)
        return 0

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(content, encoding="utf-8")
    print(f"Geschrieben: {index_path}", file=sys.stderr)
    print(f"Items: {len(items)} (BL-Counter bis BL-{total_count})", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
