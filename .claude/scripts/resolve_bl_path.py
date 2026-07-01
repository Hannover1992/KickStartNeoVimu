#!/usr/bin/env python3
"""
INV-VAULT-9 Working-Directory Resolver fuer BL-IDs.

Aufgabe: BL_ID -> absoluten Pfad zum BL-Vault-Ordner aufloesen.

Resolver-Reihenfolge (siehe vault-schema.md):
  1. working_dir aus Manifest (wenn BL-Folder _manifest.md mit working_dir-Feld vorhanden)
  2. Glob auf Backlog/BL-{ID}-*/  (PRIMAER, eindeutig)
  3. Slug aus BL-Huelle Frontmatter Backlog/BL-{ID}.md (FALLBACK)

Vault-Root-Resolution: delegiert an resolve_vault_root.py (ARCH-N8, Single Source of Truth).
  Kanonische 4-stufige Kette: ENV CLAUDE_VAULT_ROOT → .vault_root pin → vault-routing.json → Heuristik

Aufruf:
  python3 resolve_bl_path.py BL-154 [VAULT_ROOT]
  -> /home/uczen/Documents/OmniCommand/Backlog/ArchitektonischePatternLibrary/

Default VAULT_ROOT: via resolve_vault_root.resolve_vault_root() (ARCH-N8)
"""

from __future__ import annotations

import json
import re
import sys
from glob import glob
from pathlib import Path

_TICKET_PATTERN = re.compile(r"^([A-Z][A-Z0-9_]*)-(\d+)(?:-.*)?$")

# ARCH-N8: Vault-Root-Resolution delegiert an resolve_vault_root (Lead-Follow-Pattern PT-GEN-LeadFollow)
# resolve_vault_root ist der Lead, _resolve_default_vault_root ist der Follow.
try:
    from resolve_vault_root import resolve_vault_root as _resolve_vault_root_fn
    _VAULT_ROOT_VIA_HELPER = True
except ImportError:
    _VAULT_ROOT_VIA_HELPER = False


def _resolve_default_vault_root() -> Path:
    """Project-aware Vault-Root resolution.

    ARCH-N8: Delegiert an resolve_vault_root.py (Single Source of Truth).
    Fallback (ImportError): eigene 3-stufige Kette fuer Rueckwaerts-Kompatibilitaet.

    Kanonische Reihenfolge (via resolve_vault_root.py):
      1. ENV VAR `CLAUDE_VAULT_ROOT`            (canonical, PRIMAER)
      2. ENV VAR `OBSIDIAN_VAULT_PATH`          (deprecated backwards-compat)
      3. Datei `.claude/.vault_root` im CWD     (per-project pin)
      4. vault-routing.json Path-Pattern-Detection (utf-8-sig BOM aware)
      5. Heuristik: ~/Documents/{cwd_basename}  (letzter Fallback)
    """
    if _VAULT_ROOT_VIA_HELPER:
        return _resolve_vault_root_fn()

    # Fallback wenn resolve_vault_root nicht importierbar (z.B. isolierter Aufruf)
    import os

    # 1. ENV VAR (canonical)
    env_root = os.environ.get("CLAUDE_VAULT_ROOT")
    if env_root:
        return Path(env_root)

    # 2. ENV VAR (deprecated)
    env_root_deprecated = os.environ.get("OBSIDIAN_VAULT_PATH")
    if env_root_deprecated:
        return Path(env_root_deprecated)

    # 3. .vault_root pin file
    pin = Path.cwd() / ".claude" / ".vault_root"
    if pin.is_file():
        try:
            content = pin.read_text(encoding="utf-8").strip()
            if content:
                return Path(content)
        except OSError:
            pass

    # 4. Heuristik: Repo-Name → Vault-Pfad
    cwd_name = Path.cwd().name
    documents = Path.home() / "Documents"
    candidate = documents / cwd_name
    if (candidate / "Backlog").is_dir():
        return candidate

    # 5. Fallback Legacy
    return documents / "OmniCommand"


DEFAULT_VAULT_ROOT = _resolve_default_vault_root()

# F13 (BL-151 Option A): vault-routing.json kann pro Pattern einen `backlog.subfolder`
# definieren (z.B. "DCSRE/Backlog" fuer DCSRE-Vault). Hardcoded "Backlog" funktioniert
# nur fuer Vaults, deren Vault-Root direkt das Project-Root ist (z.B. OmniCommand).
_VAULT_ROUTING_DEFAULT = Path(__file__).parent.parent / "config" / "vault-routing.json"


def _resolve_backlog_subfolder(cwd: Path | None = None) -> str:
    """Resolves backlog.subfolder fuer den aktuellen CWD via vault-routing.json.

    Liest die selben detection.rules wie resolve_vault_root.py — matcht erstes
    Pattern gegen CWD und extrahiert `backlog.subfolder`. Fallback "Backlog".

    Args:
        cwd: Arbeitsverzeichnis (default: Path.cwd())

    Returns:
        Backlog-Subfolder relativ zu vault_root (z.B. "Backlog" oder "DCSRE/Backlog")
    """
    if cwd is None:
        cwd = Path.cwd()
    if not _VAULT_ROUTING_DEFAULT.is_file():
        return "Backlog"
    try:
        raw = _VAULT_ROUTING_DEFAULT.read_text(encoding="utf-8-sig")
        routing = json.loads(raw)
    except (OSError, json.JSONDecodeError):
        return "Backlog"
    cwd_str = str(cwd)
    rules = routing.get("detection", {}).get("rules", [])
    sorted_rules = sorted(rules, key=lambda r: r.get("priority", 999))
    for rule in sorted_rules:
        pattern = rule.get("pattern", "")
        if not pattern or pattern == "*":
            continue
        if pattern.lower() in cwd_str.lower():
            backlog_cfg = rule.get("backlog", {})
            subfolder = backlog_cfg.get("subfolder", "")
            if subfolder:
                return subfolder
            break  # Pattern gematcht aber kein subfolder — Default
    return "Backlog"


def resolve_bl_path(bl_id: str, vault_root: Path = DEFAULT_VAULT_ROOT) -> Path:
    """Resolve a {PREFIX}-{N}-{slug}/ Vault-Folder absolute path from a ticket ID.

    Accepts generic {PREFIX}-{N} patterns (e.g. BL-154, DCSRE-93, JIRA-123).
    BL- bleibt Default-Prefix; andere Prefixes werden nicht abgewiesen.
    """
    match = _TICKET_PATTERN.match(bl_id)
    if not match:
        raise ValueError(
            f"Erwartet {{PREFIX}}-{{N}}-Format (z.B. BL-154, DCSRE-93), bekam: {bl_id}"
        )
    prefix = match.group(1)

    backlog_subfolder = _resolve_backlog_subfolder()
    backlog = vault_root / backlog_subfolder
    if not backlog.is_dir():
        raise FileNotFoundError(f"Backlog-Verzeichnis fehlt: {backlog}")

    # Resolver 2a: Direkt-Glob auf {PREFIX}-{ID}-*/  (vault-schema.md Default)
    matches = [Path(p) for p in glob(str(backlog / f"{bl_id}-*"))
               if Path(p).is_dir()]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise RuntimeError(f"Mehrdeutig: {len(matches)} Treffer fuer {bl_id}: {matches}")

    # Resolver 2b: Huelle title → PascalCase Folder
    # (Real-world Convention 2026-05-01: BL-153 SemantischePatternLibrary,
    #  BL-154 ArchitektonischePatternLibrary — kein Prefix im Vault-Folder)
    huelle = _find_huelle(backlog, bl_id)
    if huelle is not None:
        # Resolver 3a: Frontmatter slug → BL-{ID}-{slug}/
        slug = _read_frontmatter_field(huelle, "slug")
        if slug:
            candidate = backlog / f"{bl_id}-{slug}"
            if candidate.is_dir():
                return candidate
            # Auch slug → PascalCase pruefen (BL-153 SemantischePatternLibrary)
            candidate = backlog / _pascal_case(slug.replace("-", " "))
            if candidate.is_dir():
                return candidate

        # Resolver 3b: title → PascalCase Folder
        title = _read_frontmatter_field(huelle, "title")
        if title:
            pascal = _pascal_case(title)
            candidate = backlog / pascal
            if candidate.is_dir():
                return candidate

            # Auch kebab-Slug als Fallback
            kebab = _kebab_slugify(title)
            candidate = backlog / f"{bl_id}-{kebab}"
            if candidate.is_dir():
                return candidate

    # BL-flat-stub Fallback (2026-05-29): Der OmniCommand-Backlog nutzt flache
    # {PREFIX}-{ID}-{slug}.md-Huellen statt Folder. resolve_bl_path crashte dadurch fuer
    # ALLE flachen BLs (BL-222/224/225/226 ...) -> blockierte A-Pipeline-WORKING_DIR-Resolution.
    # Fix: kanonischen Folder aus der flachen Huelle ableiten (huelle.stem) + idempotent anlegen,
    # damit der Vertrag "Resolver liefert existierenden Working-Dir" erhalten bleibt. Die
    # A-Pipeline expandiert die flache Intake-Huelle ohnehin in eine Folder-Struktur.
    if huelle is not None:
        folder = backlog / huelle.stem  # "BL-226-...md" -> Ordner "BL-226-..."
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    raise FileNotFoundError(
        f"Kein Vault-Folder fuer {bl_id} unter {backlog} gefunden. "
        f"Versuchte Patterns: {prefix}-{{ID}}-*/, PascalCase(title)/, {prefix}-{{ID}}-{{kebab(title)}}/"
    )


def _find_huelle(backlog: Path, bl_id: str) -> Path | None:
    """BL-Huelle finden: zuerst {bl_id}.md (alte Konvention), dann {bl_id}-*.md."""
    direct = backlog / f"{bl_id}.md"
    if direct.is_file():
        return direct
    matches = [Path(p) for p in glob(str(backlog / f"{bl_id}-*.md"))
               if Path(p).is_file()]
    if len(matches) == 1:
        return matches[0]
    return None


def _pascal_case(title: str) -> str:
    """'Architektonische Pattern Library' -> 'ArchitektonischePatternLibrary'."""
    return "".join(word.capitalize() for word in title.split() if word)


def _kebab_slugify(s: str) -> str:
    """'Architektonische Pattern Library' -> 'architektonische-pattern-library'."""
    s = s.strip().lower()
    out = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("-")
    while "--" in "".join(out):
        out = list("".join(out).replace("--", "-"))
    return "".join(out).strip("-")


def _read_frontmatter_field(md_file: Path, field: str) -> str | None:
    """Read a top-level field from YAML frontmatter (--- ... ---)."""
    try:
        text = md_file.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end == -1:
        return None
    fm = text[3:end]
    for line in fm.splitlines():
        line = line.strip()
        if line.startswith(f"{field}:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return None


def main(argv: list[str]) -> int:
    if len(argv) < 2 or len(argv) > 3:
        print(__doc__, file=sys.stderr)
        return 2
    bl_id = argv[1]
    vault_root = Path(argv[2]) if len(argv) == 3 else DEFAULT_VAULT_ROOT
    try:
        path = resolve_bl_path(bl_id, vault_root)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(str(path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
