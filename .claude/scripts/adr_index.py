#!/usr/bin/env python3
"""adr_index.py — idempotenter ADR-Index-Generator.

Scannt Libraries/ADR/*.md, parst kanonisches Frontmatter (type:adr),
generiert _index.md (Tabelle adr_nr|title|status|keywords), idempotent (SHA256).

Analogon zu pattern_library.py (_PT_extract-Logik), aber schlank:
kein Counter, kein Lifecycle — reiner Scanner + Emitter.

BL-244 sub_batch_2.
"""
import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

# ---------------------------------------------------------------------------
# Konstanten (exportiert fuer TC-SCHEMA-1 + TC-SCHEMA-2)
# ---------------------------------------------------------------------------

ADR_NR_REGEX = r"^BL-\d+-ADR-\d{3}$"

STATUS_WHITELIST = {"DRAFT", "ACCEPTED", "SUPERSEDED", "RETIRED"}


def validate_adr_nr(adr_nr: str) -> bool:
    """Prueft ob adr_nr dem Schema BL-{N}-ADR-{NNN} entspricht."""
    import re
    return bool(re.match(ADR_NR_REGEX, adr_nr))


def validate_adr_status(status: str) -> bool:
    """Prueft ob status in der STATUS_WHITELIST liegt."""
    return status in STATUS_WHITELIST


# ---------------------------------------------------------------------------
# Interne Hilfsfunktion
# ---------------------------------------------------------------------------


def _extract_frontmatter_text(text: str) -> Optional[str]:
    """Extrahiert den rohen YAML-Text zwischen den --- Trennern.

    Interne Hilfsfunktion fuer parse_adr_frontmatter.
    Gibt None zurueck wenn kein gueltiger Frontmatter-Block.
    """
    if not text.startswith("---"):
        return None
    # Suche nach dem zweiten --- Trenner
    first_end = text.find("\n---", 3)
    if first_end == -1:
        return None
    # YAML-Inhalt zwischen den Trennern
    yaml_text = text[3:first_end].strip()
    return yaml_text


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_adr_frontmatter(path: Path) -> Optional[dict]:
    """Parst YAML-Frontmatter einer einzelnen Markdown-Datei.

    Logik:
      - Liest Datei als UTF-8 (errors=replace)
      - Extrahiert Block zwischen erstem "---" und zweitem "---"
      - Parsed via yaml.safe_load()
      - Gibt None zurueck wenn kein Frontmatter vorhanden oder parse-Fehler
      - Gibt leeres dict zurueck wenn Frontmatter vorhanden aber leer

    Warum separiert: testbar unabhaengig von Directory-Scan.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except (OSError, IOError):
        return None

    yaml_text = _extract_frontmatter_text(text)
    if yaml_text is None:
        return None

    # Leerer Frontmatter-Block (---\n---\n)
    if not yaml_text:
        return {}

    try:
        result = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return None

    if result is None:
        return {}

    if not isinstance(result, dict):
        return None

    return result


def scan_adr_directory(adr_dir: Path) -> list:
    """Scannt adr_dir nach Markdown-Dateien mit `type: adr` im YAML-Frontmatter.

    Logik:
      - Iteriert alle *.md in adr_dir (nicht rekursiv — ADRs liegen flach)
      - Parst YAML-Frontmatter jeder Datei
      - Behaelt nur Dateien mit frontmatter.get("type") == "adr"
      - CONVENTION.md / TEMPLATE.md / _index.md werden korrekt uebersprungen
        (kein type:adr -> fallen durch den Filter)
      - Migrierte ADR-domain-single-source.md (type:adr, adr_nr:BL-254-ADR-001) wird erfasst

    Returns:
      Sortierte Liste von Dicts (sortiert nach adr_nr, lexikografisch).
      Jedes Dict enthaelt mindestens:
        {adr_nr, title, status, bl-item, created, tags, _path}
      Fehlende Felder werden mit "" / [] als Default gefuellt (robust gegen Teilmigration).
    """
    results = []

    for md_file in sorted(adr_dir.glob("*.md")):
        fm = parse_adr_frontmatter(md_file)
        if fm is None:
            continue
        if not isinstance(fm, dict):
            continue
        if fm.get("type") != "adr":
            continue

        # Fehlende Felder mit Defaults auffuellen
        entry = {
            "adr_nr": fm.get("adr_nr", ""),
            "title": fm.get("title", ""),
            "status": fm.get("status", ""),
            "bl-item": fm.get("bl-item", ""),
            "created": str(fm.get("created", "")),
            "tags": fm.get("tags") or [],
            "_path": str(md_file),
        }
        # Restliche Frontmatter-Felder ebenfalls uebernehmen (fuer type-Zugriff etc.)
        for k, v in fm.items():
            if k not in entry:
                entry[k] = v

        results.append(entry)

    # Sortiert nach adr_nr (lexikografisch)
    results.sort(key=lambda d: d.get("adr_nr", ""))
    return results


def render_index(adrs: list, generated_at: str) -> str:
    """Generiert den vollstaendigen _index.md-Inhalt.

    Output-Format (gemaess AK-S3 Spec):
      YAML-Frontmatter:
        doc_type: library-index
        generated_at: {generated_at}
        adr_count: {len(adrs)}
      Markdown-Tabelle:
        | adr_nr | title | status | bl-item | created | tags |
        |--------|-------|--------|---------|---------|------|
        | {row per adr} |

    Eigenschaften:
      - Deterministisch: gleiche adrs-Liste + gleicher generated_at -> identischer String
      - tags: Liste wird als kommaseparierter String serialisiert
      - Leere Felder -> "" (kein "None" in Ausgabe)

    Returns: vollstaendiger _index.md-Inhalt als String.
    """
    lines = []

    # YAML-Frontmatter
    lines.append("---")
    lines.append("doc_type: library-index")
    lines.append(f"generated_at: {generated_at}")
    lines.append(f"adr_count: {len(adrs)}")
    lines.append("---")
    lines.append("")

    # Tabellen-Header
    lines.append("| adr_nr | title | status | bl-item | created | tags |")
    lines.append("|--------|-------|--------|---------|---------|------|")

    # Daten-Zeilen
    for adr in adrs:
        adr_nr = adr.get("adr_nr") or ""
        title = adr.get("title") or ""
        status = adr.get("status") or ""
        bl_item = adr.get("bl-item") or ""
        created = str(adr.get("created") or "")
        tags_raw = adr.get("tags") or []
        if isinstance(tags_raw, list):
            tags_str = ", ".join(str(t) for t in tags_raw)
        else:
            tags_str = str(tags_raw)

        lines.append(f"| {adr_nr} | {title} | {status} | {bl_item} | {created} | {tags_str} |")

    lines.append("")
    return "\n".join(lines)


def write_index_idempotent(content: str, output_path: Path) -> bool:
    """Schreibt output_path nur wenn Hash(content) != Hash(bestehender Inhalt).

    Logik:
      - SHA256-Hash des neuen content
      - SHA256-Hash des bestehenden output_path (falls vorhanden)
      - Gleiche Hashes -> kein Write, return False
      - Unterschiedliche Hashes oder Datei nicht vorhanden -> Write, return True

    Idempotenz-Garantie (AK-S3): mehrfacher Aufruf ohne ADR-Aenderungen
    -> identischer content -> gleiche Hashes -> False (kein Write).

    Returns: True wenn geschrieben, False wenn identisch.
    """
    new_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    if output_path.exists():
        existing = output_path.read_text(encoding="utf-8")
        existing_hash = hashlib.sha256(existing.encode("utf-8")).hexdigest()
        if new_hash == existing_hash:
            return False

    output_path.write_text(content, encoding="utf-8")
    return True


def _adr_content_hash(adrs: list) -> str:
    """Berechnet SHA256-Hash ueber den ADR-Inhalt (ohne generated_at).

    Wird fuer Idempotenz-Entscheidung in main() genutzt:
    Wenn adr_content_hash unveraendert -> unveraenderter generated_at -> kein Write.
    """
    key = "|".join(
        f"{d.get('adr_nr', '')}:{d.get('title', '')}:{d.get('status', '')}"
        for d in adrs
    )
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def _read_existing_generated_at(output_path: Path) -> Optional[str]:
    """Liest den generated_at-Wert aus einer bestehenden _index.md.

    Gibt None zurueck wenn Datei nicht existiert oder kein generated_at vorhanden.
    """
    if not output_path.exists():
        return None
    text = output_path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("generated_at:"):
            return line[len("generated_at:"):].strip()
    return None


def main() -> None:
    """CLI-Einstiegspunkt.

    Usage:
      python adr_index.py [--adr-dir PFAD] [--output PFAD] [--vault-root PFAD]

    Defaults (via resolve_vault_root.py, analog pattern_library.py):
      --adr-dir:    {vault_root}/Libraries/ADR/
      --output:     {vault_root}/Libraries/ADR/_index.md
      --vault-root: aus resolve_vault_root.py (CLAUDE_VAULT_ROOT oder .vault_root oder Heuristik)

    Ablauf:
      1. adrs = scan_adr_directory(adr_dir)
      2. content = render_index(adrs, generated_at=datetime.utcnow().isoformat())
      3. written = write_index_idempotent(content, output_path)
      4. Print: "adr_index: {len(adrs)} ADRs -> {output_path} ({'written' if written else 'unchanged'})"
    """
    # Vault-Root-Aufloesung
    _scripts_dir = Path(__file__).parent
    vault_root = None
    resolve_script = _scripts_dir / "resolve_vault_root.py"
    if resolve_script.exists():
        import subprocess
        try:
            result = subprocess.run(
                [sys.executable, str(resolve_script)],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                vault_root = Path(result.stdout.strip())
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="ADR-Index-Generator")
    parser.add_argument("--adr-dir", type=Path, default=None,
                        help="Pfad zum ADR-Verzeichnis (default: {vault_root}/Libraries/ADR/)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Ausgabepfad fuer _index.md")
    parser.add_argument("--vault-root", type=Path, default=None,
                        help="Vault-Root-Override")

    args = parser.parse_args()

    # vault-root Override
    if args.vault_root:
        vault_root = args.vault_root

    # Defaults setzen
    if args.adr_dir:
        adr_dir = args.adr_dir
    elif vault_root:
        adr_dir = vault_root / "Libraries" / "ADR"
    else:
        raise ValueError("--adr-dir oder --vault-root erforderlich")

    if args.output:
        output_path = args.output
    elif vault_root:
        output_path = vault_root / "Libraries" / "ADR" / "_index.md"
    else:
        output_path = adr_dir / "_index.md"

    # Ablauf mit Idempotenz via ADR-Content-Hash (A3: generated_at nicht neu setzen wenn ADRs unveraendert)
    adrs = scan_adr_directory(adr_dir)

    # Bestehenden generated_at lesen
    existing_generated_at = _read_existing_generated_at(output_path)

    if existing_generated_at is not None:
        # Pruefe ob ADR-Inhalt unveraendert ist (ohne re-render mit neuem Timestamp)
        # Erzeuge probe-Content mit altem Timestamp und vergleiche Hashes
        probe_content = render_index(adrs, existing_generated_at)
        if output_path.exists():
            existing_text = output_path.read_text(encoding="utf-8")
            existing_hash = hashlib.sha256(existing_text.encode("utf-8")).hexdigest()
            probe_hash = hashlib.sha256(probe_content.encode("utf-8")).hexdigest()
            if existing_hash == probe_hash:
                # ADRs unveraendert — kein Write, gleicher Content
                content = probe_content
                written = False
            else:
                # ADRs geaendert — neuen Timestamp verwenden
                generated_at = datetime.utcnow().isoformat()
                content = render_index(adrs, generated_at)
                written = write_index_idempotent(content, output_path)
        else:
            generated_at = datetime.utcnow().isoformat()
            content = render_index(adrs, generated_at)
            written = write_index_idempotent(content, output_path)
    else:
        generated_at = datetime.utcnow().isoformat()
        content = render_index(adrs, generated_at)
        written = write_index_idempotent(content, output_path)

    status_str = "written" if written else "unchanged"
    print(f"adr_index: {len(adrs)} ADRs -> {output_path} ({status_str})")


if __name__ == "__main__":
    main()
