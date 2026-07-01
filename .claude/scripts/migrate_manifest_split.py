#!/usr/bin/env python3
"""
migrate_manifest_split.py — BL-173 AK-2: Big-Bang Manifest-Scope-Split.

Splittet {VAULT}/_manifest.md in:
  - {VAULT}/_factory_manifest.md  (BDF + GLOBAL_* Bloecke)
  - {VAULT}/Backlog/{BL_FOLDER}/_manifest.md  (pro BL: A/IDF/SDF/SC/I/DF_BATCH/BERATER)
  - {VAULT}/_manifest_orphans.md  (Bloecke ohne erkennbare BL-ID)

INV-MANIFEST-SPLIT-4: Migration MUSS atomar oder Rollback sein.

CLI Beispiele:
  py -3 migrate_manifest_split.py dry-run --vault-root="C:/Users/.../OmniCommand"
  py -3 migrate_manifest_split.py migrate --vault-root="..." --rollback-tag=2026-05-18
  py -3 migrate_manifest_split.py rollback --vault-root="..." --rollback-tag=2026-05-18
  py -3 migrate_manifest_split.py verify --vault-root="..."
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

def _configure_utf8_stdout() -> None:
    """Windows-Konsole: UTF-8 erzwingen (nur im __main__-Kontext, nicht bei pytest-Import)."""
    if sys.platform == "win32":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except AttributeError:
            pass  # pytest capsys hat kein .buffer — ignorieren

# ---------------------------------------------------------------------------
# Konstanten: Factory vs. BL Block-Klassifikation
# ---------------------------------------------------------------------------

FACTORY_BLOCK_NAMES: set[str] = {
    "BDF_PIPELINE_STATE",
    "BACKLOG_STATE",
    "GLOBAL_PARAMS",
    "FACTORY_STATES",
    "FACTORY_LOCK",
    "LOCK_STATE",
}

# Bloecke die per-BL gehoeren
BL_BLOCK_NAMES: set[str] = {
    "A_PIPELINE_STATE",
    "IDF_PIPELINE_STATE",
    "SDF_PIPELINE_STATE",
    "SC_PIPELINE_STATE",
    "I_PIPELINE_STATE",
    "DF_PIPELINE_STATE",  # legacy name
    "DF_BATCH_STATE",
}

# Bloecke die BERATER_OUTPUTS-Prefix haben (BL-gebunden, BL-ID im Name)
BERATER_OUTPUTS_PREFIX = "BERATER_OUTPUTS"

# BL_LIFECYCLE_STATE: split nach Feld (factory: status/reifegrad; bl: pipeline_phases_done etc.)
# Fuer Migration: gesamter Block geht factory wenn kein BL-Kontext erkennbar
BL_LIFECYCLE_BLOCK = "BL_LIFECYCLE_STATE"

# TOMBSTONE-Kommentare und sonstige globale Zeilen werden factory zugeordnet
GLOBAL_KEYS: set[str] = {
    "GLOBAL_MODUS",
    "GLOBAL_DIFFICULTY",
    "GLOBAL_CEILING",
    "GLOBAL_FLOOR",
    "GLOBAL_HIL",
    "dark_factory_max_cycles_override",
    "active_feature",
    "param_change",
}


# ---------------------------------------------------------------------------
# Datenstrukturen
# ---------------------------------------------------------------------------

@dataclass
class ManifestBlock:
    """Ein zusammenhaengender State-Block aus dem Manifest."""
    header: str           # z.B. "## BDF_PIPELINE_STATE" oder leer fuer pre-header Zeilen
    block_name: str       # z.B. "BDF_PIPELINE_STATE" oder "" fuer global header
    lines: list[str] = field(default_factory=list)
    scope: str = ""       # "factory", "bl", "orphan"
    bl_id: Optional[str] = None
    bl_folder: Optional[str] = None  # aufgeloester Pfad falls gefunden

    @property
    def content(self) -> str:
        text = ""
        if self.header:
            text = self.header + "\n"
        text += "\n".join(self.lines)
        return text


@dataclass
class MigrationPlan:
    factory_blocks: list[ManifestBlock] = field(default_factory=list)
    bl_blocks: dict[str, list[ManifestBlock]] = field(default_factory=dict)  # bl_id -> blocks
    orphan_blocks: list[ManifestBlock] = field(default_factory=list)
    total_lines: int = 0
    source_path: str = ""


# ---------------------------------------------------------------------------
# BL-ID Extraktion aus Block-Inhalt
# ---------------------------------------------------------------------------

_BL_ID_PATTERN = re.compile(r"\b(BL-\d+)\b")
_BL_ID_FIELD_PATTERNS = [
    re.compile(r"(?:^|\s)bl_id:\s*(BL-\d+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"(?:^|\s)sc_target_bl:\s*(BL-\d+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"(?:^|\s)sc_name:\s*(BL-\d+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"(?:^|\s)active_feature:\s*(BL-\d+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"(?:^|\s)current_item:\s*(BL-\d+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"(?:^|\s)idf_batch_id:\s*(BL-\d+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"(?:^|\s)batch_target_bl:\s*(BL-\d+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"(?:^|\s)df_task:\s*(BL-\d+)", re.MULTILINE | re.IGNORECASE),
    re.compile(r"(?:^|\s)namespace:\s*(BL-\d+)", re.MULTILINE | re.IGNORECASE),
]


def extract_bl_id_from_block_name(block_name: str) -> Optional[str]:
    """Extrahiert BL-ID aus Blocknamen wie BERATER_OUTPUTS_IDF_BL163."""
    # BERATER_OUTPUTS_IDF_BL163 -> BL-163
    m = re.search(r"BL[_-]?(\d+)", block_name, re.IGNORECASE)
    if m:
        return f"BL-{m.group(1)}"
    return None


def extract_bl_id_from_content(lines: list[str]) -> Optional[str]:
    """Extrahiert BL-ID aus Block-Inhalt per Feld-Patterns."""
    content = "\n".join(lines)
    # Priorisiert explizite Felder
    for pat in _BL_ID_FIELD_PATTERNS:
        m = pat.search(content)
        if m:
            return m.group(1)
    return None


def find_bl_folder(vault_root: Path, bl_id: str) -> Optional[Path]:
    """Sucht den Backlog-Ordner fuer eine BL-ID."""
    backlog_dir = vault_root / "Backlog"
    if not backlog_dir.exists():
        return None
    prefix = bl_id + "-"
    for d in backlog_dir.iterdir():
        if d.is_dir() and d.name.startswith(prefix):
            return d
    # Exakter Ordner-Name Match (z.B. BL-162 ohne Slug)
    exact = backlog_dir / bl_id
    if exact.exists():
        return exact
    return None


# ---------------------------------------------------------------------------
# Manifest-Parser
# ---------------------------------------------------------------------------

def parse_manifest(manifest_path: Path) -> list[ManifestBlock]:
    """
    Zerlegt das Manifest in Bloecke.
    Jeder ## Header beginnt einen neuen Block.
    Zeilen vor dem ersten Header gehoeren zum "global header" Block (factory).
    """
    lines = manifest_path.read_text(encoding="utf-8").splitlines()
    blocks: list[ManifestBlock] = []
    current_block: Optional[ManifestBlock] = None

    def _finalize(block: ManifestBlock) -> ManifestBlock:
        # Trailing leere Zeilen entfernen
        while block.lines and block.lines[-1].strip() == "":
            block.lines.pop()
        return block

    for line in lines:
        if line.startswith("## "):
            if current_block is not None:
                blocks.append(_finalize(current_block))
            block_name = line[3:].strip()
            current_block = ManifestBlock(header=line, block_name=block_name)
        else:
            if current_block is None:
                # Pre-header Zeilen -> globaler Header-Block
                current_block = ManifestBlock(header="", block_name="_GLOBAL_HEADER")
            current_block.lines.append(line)

    if current_block is not None:
        blocks.append(_finalize(current_block))

    return blocks


# ---------------------------------------------------------------------------
# Block-Klassifikation
# ---------------------------------------------------------------------------

def classify_block(block: ManifestBlock, vault_root: Path) -> ManifestBlock:
    """
    Setzt block.scope ("factory"|"bl"|"orphan") und block.bl_id.
    """
    name = block.block_name

    # Globaler Header (GLOBAL_* Felder, param_change, active_feature) -> factory
    if name == "_GLOBAL_HEADER":
        block.scope = "factory"
        return block

    # Explizit factory
    if name in FACTORY_BLOCK_NAMES:
        block.scope = "factory"
        return block

    # TOMBSTONE-Kommentare oder sonstige factory-Metazeilen
    if name.startswith("TOMBSTONE") or name.startswith("LOCK"):
        block.scope = "factory"
        return block

    # Explizit BL-gebunden (ohne BL-ID im Namen)
    if name in BL_BLOCK_NAMES:
        bl_id = extract_bl_id_from_content(block.lines)
        if bl_id:
            block.scope = "bl"
            block.bl_id = bl_id
            folder = find_bl_folder(vault_root, bl_id)
            block.bl_folder = str(folder) if folder else None
        else:
            block.scope = "orphan"
        return block

    # BERATER_OUTPUTS mit BL-Suffix (z.B. BERATER_OUTPUTS_IDF_BL163)
    if name.startswith(BERATER_OUTPUTS_PREFIX):
        # Versuche BL-ID aus Block-Namen
        bl_id = extract_bl_id_from_block_name(name)
        if not bl_id:
            # Versuche aus Inhalt
            bl_id = extract_bl_id_from_content(block.lines)
        if bl_id:
            block.scope = "bl"
            block.bl_id = bl_id
            folder = find_bl_folder(vault_root, bl_id)
            block.bl_folder = str(folder) if folder else None
        else:
            # BERATER_OUTPUTS ohne BL-ID -> try sc_target_bl in content
            block.scope = "orphan"
        return block

    # BL_LIFECYCLE_STATE: factory (status/reifegrad fuer BDF-Routing)
    if name == BL_LIFECYCLE_BLOCK:
        bl_id = extract_bl_id_from_content(block.lines)
        if bl_id:
            # Pipeline-spezifische Felder -> bl
            block.scope = "bl"
            block.bl_id = bl_id
            folder = find_bl_folder(vault_root, bl_id)
            block.bl_folder = str(folder) if folder else None
        else:
            block.scope = "factory"
        return block

    # Unbekannte Bloecke -> orphan
    block.scope = "orphan"
    return block


# ---------------------------------------------------------------------------
# Plan-Builder
# ---------------------------------------------------------------------------

def build_plan(manifest_path: Path, vault_root: Path) -> MigrationPlan:
    """Liest Manifest und erstellt MigrationPlan."""
    blocks = parse_manifest(manifest_path)
    plan = MigrationPlan(source_path=str(manifest_path))

    raw_lines = manifest_path.read_text(encoding="utf-8").splitlines()
    plan.total_lines = len(raw_lines)

    for block in blocks:
        classify_block(block, vault_root)

        if block.scope == "factory":
            plan.factory_blocks.append(block)
        elif block.scope == "bl" and block.bl_id:
            plan.bl_blocks.setdefault(block.bl_id, []).append(block)
        else:
            plan.orphan_blocks.append(block)

    return plan


# ---------------------------------------------------------------------------
# Render-Helfer
# ---------------------------------------------------------------------------

def render_factory_content(plan: MigrationPlan) -> str:
    """Rendert _factory_manifest.md Inhalt."""
    parts = [
        "# Factory Manifest",
        "# Generiert von migrate_manifest_split.py (BL-173 AK-2)",
        "# Authorisierte Writer: _BDF_orchestrate, _BDF_berater_*, _backlog",
        "# INV-MANIFEST-SPLIT-2: BDF schreibt NUR diese Datei",
        "",
    ]
    for block in plan.factory_blocks:
        parts.append(block.content)
        parts.append("")
    return "\n".join(parts)


def render_bl_content(bl_id: str, blocks: list[ManifestBlock]) -> str:
    """Rendert {BL}/_manifest.md Inhalt."""
    parts = [
        f"# BL-Manifest: {bl_id}",
        "# Generiert von migrate_manifest_split.py (BL-173 AK-2)",
        "# Authorisierte Writer: _A_orchestrate, _IDF_orchestrate, _SDF_orchestrate, _SC_orchestrate, _I_orchestrate",
        "# INV-MANIFEST-SPLIT-3: Pipeline-Skills schreiben NUR diese Datei",
        "",
    ]
    for block in blocks:
        parts.append(block.content)
        parts.append("")
    return "\n".join(parts)


def render_orphan_content(plan: MigrationPlan) -> str:
    """Rendert _manifest_orphans.md Inhalt."""
    parts = [
        "# Migration Orphans",
        "# Generiert von migrate_manifest_split.py (BL-173 AK-2)",
        "# WARNUNG: Diese Bloecke hatten keine erkennbare BL-ID.",
        "# Bitte manuell pruefen und archivieren oder loeschen.",
        "",
    ]
    for block in plan.orphan_blocks:
        parts.append(f"## ORPHAN: {block.block_name}")
        parts.append(block.content)
        parts.append("")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_dry_run(vault_root: Path) -> dict:
    """Zeigt geplante Splits ohne zu schreiben."""
    manifest_path = vault_root / "_manifest.md"
    if not manifest_path.exists():
        print(f"ERROR: _manifest.md nicht gefunden: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    plan = build_plan(manifest_path, vault_root)

    print("=== DRY-RUN: Manifest-Split-Plan ===")
    print(f"Quelle:      {manifest_path}")
    print(f"Total Zeilen: {plan.total_lines}")
    print()
    print(f"FACTORY-Bloecke ({len(plan.factory_blocks)}):")
    for b in plan.factory_blocks:
        print(f"  [{b.block_name}] -> _factory_manifest.md")

    print()
    print(f"BL-Bloecke ({sum(len(v) for v in plan.bl_blocks.values())}) in {len(plan.bl_blocks)} BLs:")
    for bl_id, blocks in sorted(plan.bl_blocks.items()):
        folder = blocks[0].bl_folder or "(Ordner nicht gefunden - ORPHAN-Kandidat)"
        print(f"  {bl_id} ({len(blocks)} Bloecke) -> {folder}/_manifest.md")
        for b in blocks:
            print(f"    [{b.block_name}]")

    print()
    print(f"ORPHAN-Bloecke ({len(plan.orphan_blocks)}) -> _manifest_orphans.md:")
    for b in plan.orphan_blocks:
        print(f"  [{b.block_name}] (kein BL-ID erkannt)")

    summary = {
        "mode": "dry-run",
        "source": str(manifest_path),
        "total_lines_processed": plan.total_lines,
        "factory_blocks_count": len(plan.factory_blocks),
        "bl_ids_found": sorted(plan.bl_blocks.keys()),
        "bl_manifests_would_write": len(plan.bl_blocks),
        "orphan_blocks": len(plan.orphan_blocks),
        "files_would_create": ["_factory_manifest.md"]
            + [f"Backlog/{bl_id}-*/_manifest.md" for bl_id in sorted(plan.bl_blocks.keys())]
            + (["_manifest_orphans.md"] if plan.orphan_blocks else []),
    }
    print()
    print("=== JSON-Summary ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def cmd_migrate(vault_root: Path, rollback_tag: Optional[str], force: bool) -> dict:
    """
    Atomische Migration: alle Writes in tmp-Files, dann rename.
    Falls eines fehlschlaegt: kompletter Rollback.
    INV-MANIFEST-SPLIT-4.
    """
    manifest_path = vault_root / "_manifest.md"
    if not manifest_path.exists():
        print(f"ERROR: _manifest.md nicht gefunden: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    # Sicherheits-Guard: ohne rollback_tag und ohne force -> Abbruch
    if not rollback_tag and not force:
        print("WARN: --rollback-tag nicht angegeben. Empfehlung: immer Backup erstellen.", file=sys.stderr)
        print("      Nutze --rollback-tag=DATUM oder --force um fortzufahren.", file=sys.stderr)
        print("      Abbruch. (Nutze --force um ohne Backup-Tag fortzufahren)", file=sys.stderr)
        sys.exit(1)

    # Pre-Check: Ziel-Datei darf nicht existieren (es sei denn --force)
    if not force:
        factory_target = vault_root / "_factory_manifest.md"
        if factory_target.exists():
            print(f"ERROR: _factory_manifest.md existiert bereits. Nutze --force um zu ueberschreiben.", file=sys.stderr)
            sys.exit(1)

    # Backup erstellen
    if rollback_tag:
        backup_path = vault_root / f"_manifest.backup-{rollback_tag}.md"
        shutil.copy2(manifest_path, backup_path)
        print(f"Backup erstellt: {backup_path}")

    plan = build_plan(manifest_path, vault_root)

    # Tmp-Verzeichnis fuer atomische Writes
    tmp_dir = Path(tempfile.mkdtemp(prefix="manifest_split_"))
    tmp_files: list[tuple[Path, Path]] = []  # (tmp_path, final_path)

    try:
        # 1. Factory Manifest
        factory_content = render_factory_content(plan)
        tmp_factory = tmp_dir / "_factory_manifest.md"
        tmp_factory.write_text(factory_content, encoding="utf-8")
        tmp_files.append((tmp_factory, vault_root / "_factory_manifest.md"))

        # 2. Per-BL Manifeste
        for bl_id, blocks in plan.bl_blocks.items():
            # BL-Folder bestimmen
            folder = None
            for b in blocks:
                if b.bl_folder:
                    folder = Path(b.bl_folder)
                    break
            if folder is None:
                folder = find_bl_folder(vault_root, bl_id)
            if folder is None:
                # Kein Ordner gefunden -> Orphan
                print(f"WARN: BL {bl_id} hat keinen Backlog-Ordner -> als Orphan behandelt")
                plan.orphan_blocks.extend(blocks)
                continue

            bl_content = render_bl_content(bl_id, blocks)
            tmp_bl = tmp_dir / f"{bl_id}_manifest.md"
            tmp_bl.write_text(bl_content, encoding="utf-8")
            final_bl = folder / "_manifest.md"
            tmp_files.append((tmp_bl, final_bl))

        # 3. Orphan-Datei (falls Orphans vorhanden)
        if plan.orphan_blocks:
            orphan_content = render_orphan_content(plan)
            tmp_orphan = tmp_dir / "_manifest_orphans.md"
            tmp_orphan.write_text(orphan_content, encoding="utf-8")
            tmp_files.append((tmp_orphan, vault_root / "_manifest_orphans.md"))

        # Atomische Umbenennung: alle tmp -> final
        print(f"Schreibe {len(tmp_files)} Dateien (atomar)...")
        written: list[Path] = []
        for tmp_path, final_path in tmp_files:
            final_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(tmp_path, final_path)
            written.append(final_path)
            print(f"  OK: {final_path}")

    except Exception as exc:
        # Rollback: alle bereits geschriebenen Dateien loeschen
        print(f"\nFEHLER waehrend Write-Phase: {exc}", file=sys.stderr)
        print("ROLLBACK: loesche bereits geschriebene Dateien...", file=sys.stderr)
        for p in written:
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        shutil.rmtree(tmp_dir, ignore_errors=True)
        print("ROLLBACK abgeschlossen. Quell-Manifest unveraendert.", file=sys.stderr)
        sys.exit(2)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    summary = {
        "mode": "migrate",
        "source": str(manifest_path),
        "total_lines_processed": plan.total_lines,
        "factory_blocks_count": len(plan.factory_blocks),
        "bl_manifests_written": len(plan.bl_blocks),
        "orphan_blocks": len(plan.orphan_blocks),
        "files_written": [str(p) for _, p in tmp_files],
        "backup": str(vault_root / f"_manifest.backup-{rollback_tag}.md") if rollback_tag else None,
    }
    print("\n=== ERFOLG ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def cmd_rollback(vault_root: Path, rollback_tag: str) -> dict:
    """Stellt _manifest.md aus Backup wieder her."""
    backup_path = vault_root / f"_manifest.backup-{rollback_tag}.md"
    manifest_path = vault_root / "_manifest.md"

    if not backup_path.exists():
        print(f"ERROR: Backup nicht gefunden: {backup_path}", file=sys.stderr)
        sys.exit(1)

    shutil.copy2(backup_path, manifest_path)
    print(f"ROLLBACK: {manifest_path} wiederhergestellt aus {backup_path}")

    summary = {
        "mode": "rollback",
        "restored": str(manifest_path),
        "backup_used": str(backup_path),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def cmd_verify(vault_root: Path) -> dict:
    """Verifiziert dass factory_manifest + BL-Manifeste konsistent sind."""
    issues: list[str] = []
    factory_path = vault_root / "_factory_manifest.md"
    orphan_path = vault_root / "_manifest_orphans.md"

    if not factory_path.exists():
        issues.append("_factory_manifest.md fehlt")
    else:
        content = factory_path.read_text(encoding="utf-8")
        # Pruefen dass keine BL-Pipeline-Bloecke im Factory-Manifest sind
        for bl_block in BL_BLOCK_NAMES:
            if f"## {bl_block}" in content:
                issues.append(f"Factory-Manifest enthaelt BL-Block: {bl_block} (INV-MANIFEST-SPLIT-2)")

    # BL-Manifeste pruefen
    backlog_dir = vault_root / "Backlog"
    bl_manifests_found = []
    if backlog_dir.exists():
        for d in backlog_dir.iterdir():
            bl_manifest = d / "_manifest.md"
            if bl_manifest.exists():
                bl_manifests_found.append(str(bl_manifest))
                content = bl_manifest.read_text(encoding="utf-8")
                # Pruefen dass keine Factory-Bloecke in BL-Manifesten sind
                for fblock in FACTORY_BLOCK_NAMES:
                    if f"## {fblock}" in content:
                        issues.append(f"{bl_manifest}: enthaelt Factory-Block {fblock} (INV-MANIFEST-SPLIT-3)")

    status = "OK" if not issues else "FEHLER"
    summary = {
        "mode": "verify",
        "status": status,
        "factory_manifest_exists": factory_path.exists(),
        "orphan_manifest_exists": orphan_path.exists(),
        "bl_manifests_found": len(bl_manifests_found),
        "issues": issues,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if issues:
        sys.exit(3)
    return summary


# ---------------------------------------------------------------------------
# Vault-Root Aufloesung
# ---------------------------------------------------------------------------

def resolve_vault_root_default() -> Optional[Path]:
    """Versucht vault_root aus current_context.py oder resolve_vault_root.py zu ermitteln."""
    script_dir = Path(__file__).parent
    resolver = script_dir / "resolve_vault_root.py"
    if resolver.exists():
        try:
            out = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True, text=True, timeout=5,
            )
            if out.returncode == 0 and out.stdout.strip():
                return Path(out.stdout.strip())
        except Exception:
            pass
    return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="BL-173 AK-2: Manifest-Scope-Split Migration Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "subcommand",
        choices=["migrate", "dry-run", "rollback", "verify"],
        help="Auszufuehrender Subcommand",
    )
    parser.add_argument(
        "--vault-root",
        default=None,
        help="Pfad zum Vault-Root-Verzeichnis (default: via resolve_vault_root.py)",
    )
    parser.add_argument(
        "--rollback-tag",
        default=None,
        help="Tag fuer Backup-Datei z.B. 2026-05-18 -> _manifest.backup-2026-05-18.md",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Alias fuer subcommand dry-run",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skipt Pre-Checks (z.B. wenn _factory_manifest.md bereits existiert)",
    )

    args = parser.parse_args()

    # Vault-Root bestimmen
    if args.vault_root:
        vault_root = Path(args.vault_root)
    else:
        vault_root = resolve_vault_root_default()

    if vault_root is None:
        print("ERROR: --vault-root nicht angegeben und automatische Aufloesung fehlgeschlagen.", file=sys.stderr)
        sys.exit(1)

    vault_root = vault_root.resolve()
    if not vault_root.exists():
        print(f"ERROR: vault_root existiert nicht: {vault_root}", file=sys.stderr)
        sys.exit(1)

    # Subcommand ausführen
    subcommand = args.subcommand
    if args.dry_run:
        subcommand = "dry-run"

    if subcommand == "dry-run":
        cmd_dry_run(vault_root)

    elif subcommand == "migrate":
        cmd_migrate(vault_root, args.rollback_tag, args.force)

    elif subcommand == "rollback":
        if not args.rollback_tag:
            print("ERROR: --rollback-tag erforderlich fuer rollback.", file=sys.stderr)
            sys.exit(1)
        cmd_rollback(vault_root, args.rollback_tag)

    elif subcommand == "verify":
        cmd_verify(vault_root)


if __name__ == "__main__":
    _configure_utf8_stdout()
    main()
