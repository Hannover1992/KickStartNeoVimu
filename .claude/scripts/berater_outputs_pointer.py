#!/usr/bin/env python3
"""
BL-171: BERATER_OUTPUTS Pointer-Pattern
Trennt Manifest-Index (1-Zeile YAML) von Berater-Inhalt (separate Datei).

INV-POINTER-1: Reader MUSS BEIDE Formate lesen koennen (Pointer + Inline).
INV-POINTER-2: Writer schreibt NUR Pointer-Format (neue Daten).
INV-POINTER-3: Content-File-Pfad ist relativ zu BL-Folder (Vault-portable).
INV-POINTER-4: GC darf nur Pointer + Content-File zusammen loeschen (atomic).
"""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import sys
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    print("FEHLER: PyYAML nicht installiert. pip install pyyaml", file=sys.stderr)
    sys.exit(2)


# ---------------------------------------------------------------------------
# Pointer-Schema (AK-1)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 1


def make_pointer(
    content_path_relative: str,
    status: str = "DONE",
    version: int = 1,
    completed_at: Optional[str] = None,
    checksum: Optional[str] = None,
) -> dict[str, Any]:
    """Erstellt ein Pointer-Dict gemaess AK-1 Schema."""
    ptr: dict[str, Any] = {
        "path": content_path_relative,
        "status": status,
        "version": version,
        "completed_at": completed_at or datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "schema_version": SCHEMA_VERSION,
    }
    if checksum:
        ptr["checksum"] = checksum
    return ptr


def is_pointer(entry: Any) -> bool:
    """True wenn der Eintrag ein Pointer (hat 'path'-Feld) ist."""
    return isinstance(entry, dict) and "path" in entry


# ---------------------------------------------------------------------------
# Manifest-Parsing
# ---------------------------------------------------------------------------

def _load_manifest_raw(manifest_path: Path) -> tuple[dict[str, Any], str]:
    """
    Liest _manifest.md und extrahiert BERATER_OUTPUTS YAML-Block.
    Gibt (berater_outputs_dict, vollstaendiger_dateiinhalt) zurueck.

    BL-229 AK-B (2026-06-10): Erkennt ALLE 108 Block-Varianten (Suffixe via
    [._( ] + Spaces/Paren/Runden-Nummern) in fenced (```yaml) UND ungefencten
    Formen. Additiv: bestehende bare-Block-Erkennung bleibt erhalten.
    """
    text = manifest_path.read_text(encoding="utf-8")

    # BL-229 AK-B: BERATER_OUTPUTS-Block suchen — fenced ODER ungefenct,
    # Block-Header mit beliebigem Suffix (dot/underscore/space/paren + Runden-Nr)
    #
    # Varianten-Muster:
    #   ## BERATER_OUTPUTS                          (bare, original BL-171)
    #   ## BERATER_OUTPUTS.dependencyAnalyzer       (dot-Suffix)
    #   ## BERATER_OUTPUTS_plBewertung_round15      (underscore-Suffix + round)
    #   ## BERATER_OUTPUTS_IDF.validator_round11    (gemischt)
    #   ## BERATER_OUTPUTS (Round 5)                (paren-Form)
    #
    # Fenced-Form:   Header + Leerzeile? + ```yaml\n...\n```
    # Ungefenct-Form: Header + Leerzeile? + YAML-Inhalt bis naechstem ## oder EOF
    #
    # Prioritaet: fenced vor ungefenct (fenced-Regex zuerst probieren)

    # Fenced-Pattern: ## BERATER_OUTPUTS[optional suffix] \n [optional blank] ```yaml\n...\n```
    fenced_pattern = re.compile(
        r"(## BERATER_OUTPUTS[^\n]*\n\s*```yaml\n)(.*?)(```)",
        re.DOTALL,
    )
    match = fenced_pattern.search(text)
    if match:
        yaml_content = match.group(2)
        try:
            data = yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError:
            data = {}
        return data, text

    # Ungefenct-Pattern: ## BERATER_OUTPUTS[optional suffix] \n [optionale Leerzeile] YAML bis ## oder EOF
    unfenced_pattern = re.compile(
        r"(## BERATER_OUTPUTS[^\n]*\n\s*\n?)((?:(?!##).)+)",
        re.DOTALL,
    )
    match = unfenced_pattern.search(text)
    if not match:
        return {}, text

    yaml_content = match.group(2).rstrip()
    try:
        data = yaml.safe_load(yaml_content) or {}
    except yaml.YAMLError:
        data = {}

    return data, text


def _save_manifest_raw(manifest_path: Path, new_berater_outputs: dict[str, Any], original_text: str) -> None:
    """Schreibt BERATER_OUTPUTS-Block zurueck ins Manifest (atomic write).

    BL-229 AK-B (2026-06-10): Unterstuetzt fenced UND ungefencte Block-Formen
    mit beliebigen Suffixen (108 Varianten). Schreibt immer im fenced Format
    zurueck (INV-POINTER-2-kompatibel: kanonisches Format fuer neue Daten).
    """
    yaml_str = yaml.dump(new_berater_outputs, allow_unicode=True, default_flow_style=False)

    # Fenced-Pattern (Prioritaet): ## BERATER_OUTPUTS[suffix]\n[blank?]```yaml\n...\n```
    fenced_pattern = re.compile(
        r"(## BERATER_OUTPUTS[^\n]*\n\s*```yaml\n)(.*?)(```)",
        re.DOTALL,
    )
    if fenced_pattern.search(original_text):
        replacement = rf"\g<1>{yaml_str}\g<3>"
        new_text = fenced_pattern.sub(replacement, original_text)
        _atomic_write(manifest_path, new_text)
        return

    # Ungefenct-Pattern: ## BERATER_OUTPUTS[suffix]\n[blank?] YAML bis ## oder EOF
    unfenced_pattern = re.compile(
        r"(## BERATER_OUTPUTS[^\n]*\n\s*\n?)((?:(?!##).)+)",
        re.DOTALL,
    )
    if unfenced_pattern.search(original_text):
        # Ungefencten Block durch fenced ersetzen (kanonisches Format)
        def _replace_unfenced(m: re.Match) -> str:
            header_line = m.group(1)
            # Header-Zeile extrahieren (erster Zeilenumbruch), Rest bleibt
            first_nl = header_line.index("\n")
            header = header_line[: first_nl + 1]
            return f"{header}\n```yaml\n{yaml_str}```\n"

        new_text = unfenced_pattern.sub(_replace_unfenced, original_text, count=1)
        _atomic_write(manifest_path, new_text)
        return

    # Kein Block gefunden → bare-canonical Block anhaengen
    new_text = original_text.rstrip() + (
        "\n\n## BERATER_OUTPUTS\n\n```yaml\n"
        + yaml_str
        + "```\n"
    )
    _atomic_write(manifest_path, new_text)


def _atomic_write(path: Path, content: str) -> None:
    """Schreibt Datei atomar ueber temporaere Datei (kein partial-write)."""
    parent = path.parent
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=parent,
        delete=False,
        suffix=".tmp",
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


# ---------------------------------------------------------------------------
# Reader (AK-3) — INV-POINTER-1: BEIDE Formate
# ---------------------------------------------------------------------------

def read_berater_output(
    manifest_path: Path,
    phase: str,
    batch_key: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    """
    Liest Berater-Output. Unterstuetzt Pointer-Format (BL-171) UND
    Legacy-Inline-Format (Backward-Compat, INV-POINTER-1).

    phase: z.B. "modusEntscheidung", "patternBrief"
    batch_key: optional Suffix fuer mehrere Batches des gleichen Phasens
    """
    lookup_key = f"{phase}_{batch_key}" if batch_key else phase

    berater_outputs, _ = _load_manifest_raw(manifest_path)

    # Direkt suchen, dann mit batch_key-Varianten
    entry = berater_outputs.get(lookup_key) or berater_outputs.get(phase)
    if entry is None:
        return None

    if is_pointer(entry):
        # Pointer-Format: Inhalt aus Content-File lesen
        bl_folder = manifest_path.parent
        content_path = bl_folder / entry["path"]
        if not content_path.exists():
            return None

        content_text = content_path.read_text(encoding="utf-8")
        # YAML-Frontmatter extrahieren falls vorhanden
        fm_match = re.match(r"^---\n(.*?)\n---\n", content_text, re.DOTALL)
        if fm_match:
            try:
                return yaml.safe_load(fm_match.group(1)) or {}
            except yaml.YAMLError:
                pass
        # Kein Frontmatter → gesamten Text als payload zurueckgeben
        return {"raw_content": content_text}
    else:
        # Legacy-Inline-Format: Eintrag direkt zurueckgeben
        return entry if isinstance(entry, dict) else {"value": entry}


# ---------------------------------------------------------------------------
# Writer (AK-4) — INV-POINTER-2: NUR Pointer-Format
# ---------------------------------------------------------------------------

def write_berater_output(
    manifest_path: Path,
    phase: str,
    batch_key: Optional[str],
    payload: dict[str, Any],
    status: str = "DONE",
) -> Path:
    """
    Schreibt Berater-Output als Pointer-Pattern (INV-POINTER-2).
    Content-File liegt in 6_PL/BERATER_OUTPUTS/{phase}_{batch_key}_{date}.md.
    Gibt Pfad zum Content-File zurueck.
    """
    bl_folder = manifest_path.parent
    today_str = date.today().isoformat()
    filename_parts = [phase]
    if batch_key:
        filename_parts.append(batch_key)
    filename_parts.append(today_str)
    filename = "_".join(filename_parts) + ".md"

    # Content-File schreiben
    output_dir = bl_folder / "6_PL" / "BERATER_OUTPUTS"
    output_dir.mkdir(parents=True, exist_ok=True)
    content_path = output_dir / filename

    # Payload als YAML-Frontmatter in Markdown
    yaml_str = yaml.dump(payload, allow_unicode=True, default_flow_style=False)
    content_text = f"---\n{yaml_str}---\n"
    _atomic_write(content_path, content_text)

    # Checksum fuer Integritaets-Pruefung
    checksum = hashlib.sha256(content_text.encode("utf-8")).hexdigest()[:16]

    # Pointer ins Manifest schreiben (INV-POINTER-3: relativ zu BL-Folder)
    relative_path = content_path.relative_to(bl_folder).as_posix()
    pointer = make_pointer(
        content_path_relative=relative_path,
        status=status,
        completed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        checksum=checksum,
    )

    lookup_key = f"{phase}_{batch_key}" if batch_key else phase
    berater_outputs, original_text = _load_manifest_raw(manifest_path)
    berater_outputs[lookup_key] = pointer
    _save_manifest_raw(manifest_path, berater_outputs, original_text)

    return content_path


# ---------------------------------------------------------------------------
# Migration (AK-6) — Inline → Pointer Bulk-Convert
# ---------------------------------------------------------------------------

def migrate_inline_to_pointer(manifest_path: Path, dry_run: bool = False) -> list[str]:
    """
    Migriert alle Inline-BERATER_OUTPUTS-Eintraege zu Pointer-Format.
    Erstellt Backup vor Migration.
    Gibt Liste der migrierten Keys zurueck.
    """
    berater_outputs, original_text = _load_manifest_raw(manifest_path)
    if not berater_outputs:
        return []

    today_str = date.today().isoformat()
    migrated_keys: list[str] = []

    # Backup erstellen
    if not dry_run:
        backup_path = manifest_path.with_name(
            f"_backup_pre_bl171_{today_str}.md"
        )
        shutil.copy2(manifest_path, backup_path)

    bl_folder = manifest_path.parent
    output_dir = bl_folder / "6_PL" / "BERATER_OUTPUTS"
    if not dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)

    new_berater_outputs: dict[str, Any] = {}

    for key, entry in berater_outputs.items():
        if is_pointer(entry):
            # Bereits Pointer → unveraendert behalten
            new_berater_outputs[key] = entry
            continue

        if not isinstance(entry, dict):
            # Skalarer Wert → als Inline behalten (nicht migrierbar)
            new_berater_outputs[key] = entry
            continue

        # Inline-Dict → als Content-File schreiben + Pointer erstellen
        filename = f"{key}_{today_str}.md"
        content_path = output_dir / filename

        yaml_str = yaml.dump(entry, allow_unicode=True, default_flow_style=False)
        content_text = f"---\n{yaml_str}---\n"

        if not dry_run:
            _atomic_write(content_path, content_text)

        checksum = hashlib.sha256(content_text.encode("utf-8")).hexdigest()[:16]
        relative_path = content_path.relative_to(bl_folder).as_posix()
        pointer = make_pointer(
            content_path_relative=relative_path,
            status=entry.get("status", "DONE"),
            completed_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            checksum=checksum,
        )

        new_berater_outputs[key] = pointer
        migrated_keys.append(key)

    if not dry_run and migrated_keys:
        _save_manifest_raw(manifest_path, new_berater_outputs, original_text)

    return migrated_keys


# ---------------------------------------------------------------------------
# Audit (AK-5 kompatibel)
# ---------------------------------------------------------------------------

def audit_manifest(manifest_path: Path) -> dict[str, Any]:
    """
    Prueft Manifest auf Pointer-Format-Konsistenz.
    Gibt Bericht mit broken/inline/pointer Counts zurueck.
    """
    berater_outputs, _ = _load_manifest_raw(manifest_path)
    bl_folder = manifest_path.parent

    report: dict[str, Any] = {
        "manifest": str(manifest_path),
        "total": len(berater_outputs),
        "pointer": 0,
        "inline": 0,
        "broken_pointer": [],
        "inline_keys": [],
    }

    for key, entry in berater_outputs.items():
        if is_pointer(entry):
            report["pointer"] += 1
            content_path = bl_folder / entry["path"]
            if not content_path.exists():
                report["broken_pointer"].append(key)
        else:
            report["inline"] += 1
            report["inline_keys"].append(key)

    return report


# ---------------------------------------------------------------------------
# GC-Helper (AK-5) — Pointer + Content atomar loeschen
# ---------------------------------------------------------------------------

def gc_delete_pointer(manifest_path: Path, phase_key: str) -> bool:
    """
    Loescht Pointer-Eintrag UND Content-File atomar (INV-POINTER-4).
    Gibt True zurueck wenn erfolgreich geloescht.
    """
    berater_outputs, original_text = _load_manifest_raw(manifest_path)
    entry = berater_outputs.get(phase_key)

    if entry is None:
        return False

    if not is_pointer(entry):
        # Inline-Format: nur Eintrag loeschen, kein File
        del berater_outputs[phase_key]
        _save_manifest_raw(manifest_path, berater_outputs, original_text)
        return True

    bl_folder = manifest_path.parent
    content_path = bl_folder / entry["path"]

    # Atomic: erst File loeschen, dann Pointer (bei Fehler: Konsistenz erhalten)
    if content_path.exists():
        content_path.unlink()

    del berater_outputs[phase_key]
    _save_manifest_raw(manifest_path, berater_outputs, original_text)
    return True


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli_write(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"FEHLER: Manifest nicht gefunden: {manifest_path}", file=sys.stderr)
        return 1

    import json
    try:
        payload = json.loads(args.payload)
    except json.JSONDecodeError as exc:
        print(f"FEHLER: Payload ist kein gueltiges JSON: {exc}", file=sys.stderr)
        return 1

    content_file = write_berater_output(
        manifest_path=manifest_path,
        phase=args.phase,
        batch_key=args.batch_key,
        payload=payload,
        status=args.status,
    )
    print(f"OK: Content-File geschrieben: {content_file}")
    return 0


def _cli_read(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"FEHLER: Manifest nicht gefunden: {manifest_path}", file=sys.stderr)
        return 1

    result = read_berater_output(
        manifest_path=manifest_path,
        phase=args.phase,
        batch_key=args.batch_key,
    )
    if result is None:
        print(f"NICHT GEFUNDEN: {args.phase}", file=sys.stderr)
        return 1

    import json
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _cli_migrate(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"FEHLER: Manifest nicht gefunden: {manifest_path}", file=sys.stderr)
        return 1

    migrated = migrate_inline_to_pointer(manifest_path, dry_run=args.dry_run)
    if args.dry_run:
        print(f"DRY-RUN: {len(migrated)} Keys wuerden migriert: {migrated}")
    else:
        print(f"OK: {len(migrated)} Keys migriert: {migrated}")
    return 0


def _cli_audit(args: argparse.Namespace) -> int:
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"FEHLER: Manifest nicht gefunden: {manifest_path}", file=sys.stderr)
        return 1

    import json
    report = audit_manifest(manifest_path)
    print(json.dumps(report, ensure_ascii=False, indent=2))

    # Exit-Code 1 wenn broken pointers existieren
    if report["broken_pointer"]:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="BL-171 BERATER_OUTPUTS Pointer-Pattern CLI"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # write
    p_write = sub.add_parser("write", help="Berater-Output schreiben (Pointer-Format)")
    p_write.add_argument("manifest", help="Pfad zum _manifest.md")
    p_write.add_argument("phase", help="Berater-Phase, z.B. modusEntscheidung")
    p_write.add_argument("payload", help="JSON-Payload als String")
    p_write.add_argument("--batch-key", default=None, help="Batch-Schluessel (z.B. b1)")
    p_write.add_argument("--status", default="DONE", help="Status: DONE|PARTIAL|FAILED")

    # read
    p_read = sub.add_parser("read", help="Berater-Output lesen (Pointer + Inline compat)")
    p_read.add_argument("manifest", help="Pfad zum _manifest.md")
    p_read.add_argument("phase", help="Berater-Phase")
    p_read.add_argument("--batch-key", default=None, help="Batch-Schluessel")

    # migrate
    p_migrate = sub.add_parser("migrate", help="Inline-BERATER_OUTPUTS zu Pointer migrieren")
    p_migrate.add_argument("manifest", help="Pfad zum _manifest.md")
    p_migrate.add_argument("--dry-run", action="store_true", help="Keine Aenderungen schreiben")

    # audit
    p_audit = sub.add_parser("audit", help="Manifest auf Pointer-Konsistenz pruefen")
    p_audit.add_argument("manifest", help="Pfad zum _manifest.md")

    args = parser.parse_args()

    dispatch = {
        "write": _cli_write,
        "read": _cli_read,
        "migrate": _cli_migrate,
        "audit": _cli_audit,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
