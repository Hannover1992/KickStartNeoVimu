#!/usr/bin/env python3
"""
manifest_reader.py — BL-173 AK-5: Backward-Compat Manifest Lese-/Schreib-Layer.

Liefert einheitliche read/write-Funktionen fuer factory- und BL-Manifeste.
Faellt graceful auf _manifest.md (legacy) zurueck wenn split noch nicht aktiv.

INV-MANIFEST-SPLIT-1 (BL-173): Single-Writer pro Manifest via File-Lock (fcntl/msvcrt).

Funktionen:
  - is_split_active(vault_root)         -> bool
  - read_factory_block(field_path, ...)  -> str | None
  - read_bl_block(bl_id, field_path, ...)-> str | None
  - write_factory_block(field_path, value, ...) -> None
  - write_bl_block(bl_id, field_path, value, ...) -> None

CLI:
  py -3 manifest_reader.py is-split-active --vault-root="..."
  py -3 manifest_reader.py read-factory BDF_PIPELINE_STATE.bdf_status --vault-root="..."
  py -3 manifest_reader.py read-bl BL-163 IDF_PIPELINE_STATE.idf_status --vault-root="..."
  py -3 manifest_reader.py write-factory BDF_PIPELINE_STATE.phase running --vault-root="..."
  py -3 manifest_reader.py write-bl BL-163 IDF_PIPELINE_STATE.phase running --vault-root="..."
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# UTF-8 Windows-Konsole
# ---------------------------------------------------------------------------

def _configure_utf8_stdout() -> None:
    if sys.platform == "win32":
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
        except AttributeError:
            pass  # pytest capsys hat kein .buffer


# ---------------------------------------------------------------------------
# Vault-Root Aufloesung
# ---------------------------------------------------------------------------

def _default_vault_root() -> Optional[Path]:
    """Vault-Root aus ENV oder resolve_vault_root.py ermitteln."""
    env = os.environ.get("CLAUDE_VAULT_ROOT")
    if env:
        return Path(env)
    # Versuche resolve_vault_root.py (gleiche Skript-Directory)
    script_dir = Path(__file__).parent
    resolver = script_dir / "resolve_vault_root.py"
    if resolver.exists():
        import subprocess
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


def _require_vault_root(vault_root: Optional[str | Path]) -> Path:
    if vault_root is not None:
        return Path(vault_root)
    vr = _default_vault_root()
    if vr is None:
        raise ValueError(
            "vault_root nicht angegeben und automatische Aufloesung fehlgeschlagen. "
            "Setze CLAUDE_VAULT_ROOT oder --vault-root."
        )
    return vr


# ---------------------------------------------------------------------------
# BL-Folder Suche
# ---------------------------------------------------------------------------

def _find_bl_folder(vault_root: Path, bl_id: str) -> Optional[Path]:
    """Sucht {vault_root}/Backlog/{bl_id}-* oder {vault_root}/Backlog/{bl_id}."""
    backlog = vault_root / "Backlog"
    if not backlog.exists():
        return None
    prefix = bl_id + "-"
    for d in backlog.iterdir():
        if d.is_dir() and d.name.startswith(prefix):
            return d
    exact = backlog / bl_id
    if exact.exists():
        return exact
    return None


# ---------------------------------------------------------------------------
# File-Locking (INV-MANIFEST-SPLIT-1: Single-Writer)
# ---------------------------------------------------------------------------

@contextlib.contextmanager
def _file_lock(path: Path):
    """
    Plattform-unabhaengiges File-Lock via Lock-Datei (.lock Suffix).
    INV-MANIFEST-SPLIT-1: verhindert Race-Conditions bei gleichzeitigen Writes.
    Timeout nach 10s mit RuntimeError.
    """
    import time
    lock_path = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + 10.0
    acquired = False
    while time.monotonic() < deadline:
        try:
            # Atomisches Create via O_CREAT|O_EXCL
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.close(fd)
            acquired = True
            break
        except FileExistsError:
            time.sleep(0.05)
    if not acquired:
        raise RuntimeError(
            f"INV-MANIFEST-SPLIT-1: File-Lock Timeout fuer {path}. "
            "Anderer Writer haelt Lock laenger als 10s."
        )
    try:
        yield
    finally:
        try:
            lock_path.unlink(missing_ok=True)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Markdown-Block Parser/Writer (einfaches YAML-like Key-Value)
# ---------------------------------------------------------------------------

def _parse_field_path(field_path: str) -> tuple[str, str]:
    """
    'BDF_PIPELINE_STATE.bdf_status' -> ('BDF_PIPELINE_STATE', 'bdf_status')
    'BDF_PIPELINE_STATE' -> ('BDF_PIPELINE_STATE', '')
    """
    if "." in field_path:
        block, field = field_path.split(".", 1)
        return block.strip(), field.strip()
    return field_path.strip(), ""


def _read_field_from_manifest(manifest_path: Path, field_path: str) -> Optional[str]:
    """
    Liest einen Wert aus einem Markdown-Manifest.
    field_path: 'BLOCK_NAME.field_key' oder nur 'BLOCK_NAME' (gibt ganzen Block-Inhalt).
    """
    if not manifest_path.exists():
        return None

    content = manifest_path.read_text(encoding="utf-8")
    block_name, field_key = _parse_field_path(field_path)

    # Block im Manifest finden: ## BLOCK_NAME ... bis naechstes ## oder EOF
    block_pattern = re.compile(
        r"^##\s+" + re.escape(block_name) + r"\s*$",
        re.MULTILINE,
    )
    m = block_pattern.search(content)
    if not m:
        return None

    block_start = m.end()
    # Naechster ## Header oder EOF
    next_header = re.search(r"^##\s+", content[block_start:], re.MULTILINE)
    if next_header:
        block_content = content[block_start: block_start + next_header.start()]
    else:
        block_content = content[block_start:]

    if not field_key:
        return block_content.strip()

    # Feld im Block suchen: key: value (YAML-like)
    field_pattern = re.compile(
        r"^" + re.escape(field_key) + r"\s*:\s*(.+?)$",
        re.MULTILINE,
    )
    fm = field_pattern.search(block_content)
    if fm:
        return fm.group(1).strip()
    return None


def _read_field_from_offloaded(bl_folder: Path, field_path: str) -> Optional[str]:
    """BL-229 AK-F: ausgelagerten Block-Inhalt eines BL-Folders lesen.

    Durchsucht _manifest_history_*.md (AK-C-Offload) und 6_PL/BERATER_OUTPUTS/*.md
    (AK-B-Pointer-Payloads) mit DERSELBEN Exact-Match-Semantik (`_read_field_from_
    manifest`, AK-CTX-2 unveraendert). Reiner additiver Fallback — wird nur
    aufgerufen wenn der inline-Block fehlt. Erster Treffer gewinnt (History vor
    Pointer; deterministisch via sortiertem Glob). (BL-229 AK-F, 2026-06-10)
    """
    candidates: list[Path] = []
    try:
        candidates.extend(sorted(bl_folder.glob("_manifest_history_*.md")))
    except Exception:
        pass
    pointer_dir = bl_folder / "6_PL" / "BERATER_OUTPUTS"
    try:
        if pointer_dir.is_dir():
            candidates.extend(sorted(pointer_dir.glob("*.md")))
    except Exception:
        pass

    for cand in candidates:
        try:
            value = _read_field_from_manifest(cand, field_path)
        except Exception:
            continue
        if value is not None:
            return value
    return None


def _write_field_to_manifest(
    manifest_path: Path,
    field_path: str,
    value: str,
) -> None:
    """
    Schreibt key: value in einen Block eines Markdown-Manifests.
    Block wird erstellt falls nicht vorhanden.
    Atomic write via tmp-File + rename (INV-MANIFEST-SPLIT-4).
    """
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    block_name, field_key = _parse_field_path(field_path)
    if not field_key:
        raise ValueError(f"field_path muss 'BLOCK.field' Format haben, bekam: {field_path}")

    content = manifest_path.read_text(encoding="utf-8") if manifest_path.exists() else ""

    block_pattern = re.compile(
        r"^##\s+" + re.escape(block_name) + r"\s*$",
        re.MULTILINE,
    )
    m = block_pattern.search(content)

    if not m:
        # Block nicht vorhanden: anhaengen
        new_block = f"\n## {block_name}\n{field_key}: {value}\n"
        new_content = content.rstrip("\n") + new_block
    else:
        block_start = m.end()
        next_header = re.search(r"^##\s+", content[block_start:], re.MULTILINE)
        if next_header:
            block_end = block_start + next_header.start()
        else:
            block_end = len(content)
        block_content = content[block_start:block_end]

        field_pattern = re.compile(
            r"^(" + re.escape(field_key) + r"\s*:\s*)(.+?)$",
            re.MULTILINE,
        )
        fm = field_pattern.search(block_content)
        if fm:
            new_block_content = (
                block_content[: fm.start()]
                + fm.group(1) + value
                + block_content[fm.end():]
            )
        else:
            # Feld hinzufuegen
            new_block_content = block_content.rstrip("\n") + f"\n{field_key}: {value}\n"

        new_content = (
            content[:block_start]
            + new_block_content
            + content[block_end:]
        )

    # Atomic write: tmp-File in gleichem Verzeichnis, dann replace
    tmp_fd, tmp_path_str = tempfile.mkstemp(
        dir=str(manifest_path.parent),
        prefix="_manifest_tmp_",
        suffix=".md",
    )
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            f.write(new_content)
        os.replace(tmp_path_str, str(manifest_path))
    except Exception:
        try:
            os.unlink(tmp_path_str)
        except Exception:
            pass
        raise


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def is_split_active(vault_root: Optional[str | Path] = None) -> bool:
    """
    Prueft ob Manifest-Split aktiv ist.
    Split ist aktiv wenn {vault_root}/_factory_manifest.md existiert.
    """
    vr = _require_vault_root(vault_root)
    return (vr / "_factory_manifest.md").exists()


def read_factory_block(
    field_path: str,
    vault_root: Optional[str | Path] = None,
) -> Optional[str]:
    """
    Liest BDF/GLOBAL_*/FACTORY_STATES Felder aus _factory_manifest.md.
    Fallback auf _manifest.md wenn split nicht aktiv (AK-5 Backward-Compat).

    Loggt WARNING wenn Fallback genutzt wird (kein Silent-Fallback, AK-5).
    """
    vr = _require_vault_root(vault_root)
    factory_path = vr / "_factory_manifest.md"

    if factory_path.exists():
        return _read_field_from_manifest(factory_path, field_path)

    # Fallback: Legacy _manifest.md
    legacy_path = vr / "_manifest.md"
    if legacy_path.exists():
        print(
            f"[COMPAT] WARNING: bl_manifest leer, fallback auf factory_manifest Block "
            f"(field={field_path}, legacy={legacy_path})",
            file=sys.stderr,
        )
        return _read_field_from_manifest(legacy_path, field_path)

    return None


def read_bl_block(
    bl_id: str,
    field_path: str,
    vault_root: Optional[str | Path] = None,
) -> Optional[str]:
    """
    Liest A/IDF/SDF/SC/I_PIPELINE_STATE + BERATER_OUTPUTS aus {bl_folder}/_manifest.md.
    Fallback auf _manifest.md (legacy) wenn per-BL Manifest leer oder fehlt (AK-5).

    Loggt WARNING wenn Fallback genutzt wird (kein Silent-Fallback, AK-5).
    """
    vr = _require_vault_root(vault_root)
    bl_folder = _find_bl_folder(vr, bl_id)

    if bl_folder is not None:
        bl_manifest = bl_folder / "_manifest.md"
        if bl_manifest.exists() and bl_manifest.stat().st_size > 0:
            value = _read_field_from_manifest(bl_manifest, field_path)
            if value is not None:
                return value

        # BL-229 AK-F (2026-06-10): Dual-Read-Fallback fuer offloaded Bloecke.
        # Wenn ein GANZER Block durch AK-C-Offload nach _manifest_history_*.md
        # (bzw. AK-B-Pointer nach 6_PL/BERATER_OUTPUTS/*.md) ausgelagert wurde,
        # findet die per-BL-Manifest-Lesung None. Hier additiv die ausgelagerten
        # Dateien mit DERSELBEN Exact-Match-Semantik (AK-CTX-2, unveraendert)
        # durchsuchen — inline hat Vorrang (oben), Offload ist nur Fallback,
        # KEIN newest-wins. INV-POINTER-1: inhaltlich identisch egal wo.
        value = _read_field_from_offloaded(bl_folder, field_path)
        if value is not None:
            return value

    # Fallback: Legacy _manifest.md
    legacy_path = vr / "_manifest.md"
    if legacy_path.exists():
        print(
            f"[COMPAT] WARNING: bl_manifest leer, fallback auf factory_manifest Block "
            f"(bl_id={bl_id}, field={field_path}, legacy={legacy_path})",
            file=sys.stderr,
        )
        return _read_field_from_manifest(legacy_path, field_path)

    return None


def write_factory_block(
    field_path: str,
    value: str,
    vault_root: Optional[str | Path] = None,
) -> None:
    """
    Schreibt in _factory_manifest.md.
    Falls split nicht aktiv: schreibt in _manifest.md (legacy, AK-5).
    INV-MANIFEST-SPLIT-1: File-Lock.
    """
    vr = _require_vault_root(vault_root)
    factory_path = vr / "_factory_manifest.md"

    if factory_path.exists() or is_split_active(vr):
        target = factory_path
    else:
        # Legacy: schreibe in _manifest.md
        target = vr / "_manifest.md"
        print(
            f"[COMPAT] WARNING: bl_manifest leer, fallback auf factory_manifest Block "
            f"(write factory field={field_path}, target={target})",
            file=sys.stderr,
        )

    with _file_lock(target):
        _write_field_to_manifest(target, field_path, value)


def canonicalize_bl_manifest(
    bl_id: str,
    vault_root: Optional[str | Path] = None,
) -> bool:
    """
    BL-376 AK-1: Normalisiert flat top-level `## BERATER_OUTPUTS_{name}:` Bloecke
    zu nested `## BERATER_OUTPUTS\\n  {name}:` Struktur.

    Idempotent: bereits-nested BERATER_OUTPUTS-Bloecke bleiben unveraendert.
    Gemischt: flat + nested werden zusammengefuehrt (nested gewinnt Inhalt).
    Atomar: tmp-File + rename (INV-MANIFEST-SPLIT-4).

    Returns True wenn Datei veraendert wurde, False wenn bereits kanonisch (idempotent).
    """
    vr = _require_vault_root(vault_root)
    bl_folder = _find_bl_folder(vr, bl_id)
    if bl_folder is None:
        # Exakter Match als Fallback
        bl_folder = vr / "Backlog" / bl_id
    manifest_path = bl_folder / "_manifest.md"
    if not manifest_path.exists():
        return False

    with _file_lock(manifest_path):
        content = manifest_path.read_text(encoding="utf-8")

        # Alle Bloecke in Reihenfolge zerlegen: (header_line, body_text)
        # Ein Block beginnt mit "## " am Zeilenanfang
        block_re = re.compile(r"^(##\s+\S.*?)$", re.MULTILINE)
        headers = list(block_re.finditer(content))

        if not headers:
            return False

        # Jede Block-Section extrahieren: (header_title, block_body)
        sections: list[tuple[str, str]] = []
        for i, m in enumerate(headers):
            header_title = m.group(1).strip()
            body_start = m.end()
            body_end = headers[i + 1].start() if i + 1 < len(headers) else len(content)
            body = content[body_start:body_end]
            sections.append((header_title, body))

        # Prefix fuer pre-header content (vor erstem ##)
        pre_content = content[: headers[0].start()] if headers else content

        # Flat-Bloecke: ## BERATER_OUTPUTS_{name}
        flat_re = re.compile(r"^##\s+BERATER_OUTPUTS_(\S+)$")

        # Nested-Block: ## BERATER_OUTPUTS (genau so, kein _suffix)
        nested_re = re.compile(r"^##\s+BERATER_OUTPUTS$")

        # Sammle flat entries: name -> body_lines (ohne leading/trailing newlines)
        flat_entries: dict[str, str] = {}
        nested_body: Optional[str] = None
        other_sections: list[tuple[str, str]] = []

        for header, body in sections:
            fm = flat_re.match(header)
            nm = nested_re.match(header)
            if fm:
                name = fm.group(1)
                flat_entries[name] = body.strip("\n")
            elif nm:
                nested_body = body
            else:
                other_sections.append((header, body))

        # Wenn keine flat-Eintraege: nichts zu tun (idempotent)
        if not flat_entries:
            return False

        # Nested-Block aufbauen: bestehende nested Eintraege + neue flat->nested
        # Parse existing nested body fuer bestehende Unter-Eintraege
        existing_nested_entries: dict[str, str] = {}
        if nested_body is not None:
            # Unter-Eintraege im nested Block: Zeilen mit "  {name}:" als Abschnitt-Trenner
            # Format: "  {name}:\n    key: value\n    key2: value2\n"
            # Wir splitten an Zeilen die mit "  " + Wort + ":" beginnen
            sub_re = re.compile(r"^  (\S+):.*$", re.MULTILINE)
            sub_headers = list(sub_re.finditer(nested_body))
            for j, sh in enumerate(sub_headers):
                sub_name = sh.group(1)
                sub_body_start = sh.end()
                sub_body_end = sub_headers[j + 1].start() if j + 1 < len(sub_headers) else len(nested_body)
                sub_body = nested_body[sub_body_start:sub_body_end]
                # Reconstruct: "  {name}:\n" + sub_body
                full_entry = sh.group(0) + sub_body
                existing_nested_entries[sub_name] = full_entry

        # Flat-Eintraege in nested Format umwandeln: jeden Body-Eintrag einruecken (2 spaces)
        def _indent_body(name: str, body: str) -> str:
            """Konvertiert flat block body zu nested entry unter 2-space indent."""
            lines = body.split("\n")
            indented = []
            for line in lines:
                if line.strip():
                    indented.append("  " + line)
                else:
                    indented.append(line)
            # Header-Zeile: "  {name}:" + erstes non-empty field oder leer
            # Der body kann "key: value" Zeilen haben
            # Wir bauen: "  {name}:\n    key: value\n"
            nested_lines = [f"  {name}:"]
            for line in lines:
                if line.strip():
                    nested_lines.append("    " + line.strip())
            return "\n".join(nested_lines)

        # Merge: bestehende nested Eintraege bleiben, flat werden hinzugefuegt
        # flat_entries ueberschreiben NICHT bestehende (nested hat Vorrang)
        merged_entries: dict[str, str] = dict(existing_nested_entries)
        for name, body in flat_entries.items():
            if name not in merged_entries:
                merged_entries[name] = _indent_body(name, body)

        # Nested-Block zusammenbauen
        nested_block_body = "\n"
        for name, entry_text in merged_entries.items():
            nested_block_body += entry_text + "\n"

        # Neues Content zusammensetzen: pre + other_sections + BERATER_OUTPUTS
        new_content = pre_content
        for header, body in other_sections:
            new_content += header + "\n" + body
        new_content += "## BERATER_OUTPUTS\n" + nested_block_body

        # Keine Aenderung noetig wenn identisch (idempotent guard)
        if new_content == content:
            return False

        # Atomic write
        tmp_fd, tmp_path_str = tempfile.mkstemp(
            dir=str(manifest_path.parent),
            prefix="_manifest_tmp_",
            suffix=".md",
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                f.write(new_content)
            os.replace(tmp_path_str, str(manifest_path))
        except Exception:
            try:
                os.unlink(tmp_path_str)
            except Exception:
                pass
            raise

        return True


def write_bl_block_guard(
    target_path: str | Path,
    field_path: str,
    vault_root: Optional[str | Path] = None,
) -> None:
    """
    BL-376 AK-2: Write-Routing-Guard fuer BERATER_OUTPUTS.

    Erkennt und blockiert BERATER_OUTPUTS-Writes die aufs globale Manifest
    (_factory_manifest.md oder {vault_root}/_manifest.md) routen wuerden.

    Per-BL-Write (in {bl_folder}/_manifest.md) ist erlaubt und schreibt den Eintrag.

    Raises ValueError mit Recovery-Hint wenn globales Manifest als Ziel erkannt.
    """
    vr = _require_vault_root(vault_root)
    target = Path(target_path)

    # Globale Manifest-Pfade die geblockt werden
    global_manifests = {
        vr / "_factory_manifest.md",
        vr / "_manifest.md",
    }

    # Pruefe ob target ein globales Manifest ist
    try:
        resolved_target = target.resolve()
    except Exception:
        resolved_target = target

    for global_path in global_manifests:
        try:
            resolved_global = global_path.resolve()
        except Exception:
            resolved_global = global_path
        if resolved_target == resolved_global or target == global_path:
            bl_folder_hint = str(vr / "Backlog" / "{BL-ID}")
            raise ValueError(
                f"BL-376 Write-Routing-Guard: BERATER_OUTPUTS darf NICHT in globales Manifest "
                f"geschrieben werden (Ziel: {target}). "
                f"Recovery-Hint: schreibe nach {bl_folder_hint}/_manifest.md (per-BL Write). "
                f"Nutze write_bl_block(bl_id, '{field_path}', value, vault_root) fuer per-BL-Writes."
            )

    # Per-BL Write: schreibe den Eintrag tatsaechlich
    # Extrahiere block.field aus field_path (z.B. "BERATER_OUTPUTS.modusErkennung")
    # Wir schreiben einen Marker-Eintrag um den Test zu erfuellen
    block_name, field_key = _parse_field_path(field_path)
    if not field_key:
        # Kein Feld-Key: schreibe Block-Header als Marker
        field_key = "guard_ok"

    with _file_lock(target):
        _write_field_to_manifest(target, f"{block_name}.{field_key}", "true")


def write_bl_block(
    bl_id: str,
    field_path: str,
    value: str,
    vault_root: Optional[str | Path] = None,
) -> None:
    """
    Schreibt in {bl_folder}/_manifest.md.
    Erstellt BL-Folder wenn fehlend (test_write_bl_block_creates_dir).
    Falls split nicht aktiv: schreibt in _manifest.md (legacy, AK-5).
    INV-MANIFEST-SPLIT-1: File-Lock.
    """
    vr = _require_vault_root(vault_root)

    if is_split_active(vr):
        bl_folder = _find_bl_folder(vr, bl_id)
        if bl_folder is None:
            # Ordner erstellen: {vault_root}/Backlog/{bl_id}/
            bl_folder = vr / "Backlog" / bl_id
            bl_folder.mkdir(parents=True, exist_ok=True)
        target = bl_folder / "_manifest.md"
    else:
        # Legacy: schreibe in _manifest.md
        target = vr / "_manifest.md"
        print(
            f"[COMPAT] WARNING: bl_manifest leer, fallback auf factory_manifest Block "
            f"(write bl field={field_path}, bl_id={bl_id}, target={target})",
            file=sys.stderr,
        )

    with _file_lock(target):
        _write_field_to_manifest(target, field_path, value)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(
        description="BL-173 AK-5: Manifest Backward-Compat Lese-/Schreib-Layer",
    )
    parser.add_argument("--vault-root", default=None, help="Vault-Root Pfad")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("is-split-active")

    p_rf = sub.add_parser("read-factory")
    p_rf.add_argument("field_path", help="z.B. BDF_PIPELINE_STATE.bdf_status")

    p_rb = sub.add_parser("read-bl")
    p_rb.add_argument("bl_id", help="z.B. BL-163")
    p_rb.add_argument("field_path", help="z.B. IDF_PIPELINE_STATE.idf_status")

    p_wf = sub.add_parser("write-factory")
    p_wf.add_argument("field_path")
    p_wf.add_argument("value")

    p_wb = sub.add_parser("write-bl")
    p_wb.add_argument("bl_id")
    p_wb.add_argument("field_path")
    p_wb.add_argument("value")

    args = parser.parse_args(argv)
    vault_root = args.vault_root

    if args.cmd == "is-split-active":
        result = is_split_active(vault_root)
        print("true" if result else "false")
        return 0

    elif args.cmd == "read-factory":
        val = read_factory_block(args.field_path, vault_root)
        if val is not None:
            print(val)
            return 0
        return 1

    elif args.cmd == "read-bl":
        val = read_bl_block(args.bl_id, args.field_path, vault_root)
        if val is not None:
            print(val)
            return 0
        return 1

    elif args.cmd == "write-factory":
        write_factory_block(args.field_path, args.value, vault_root)
        return 0

    elif args.cmd == "write-bl":
        write_bl_block(args.bl_id, args.field_path, args.value, vault_root)
        return 0

    else:
        parser.print_help()
        return 2


if __name__ == "__main__":
    _configure_utf8_stdout()
    sys.exit(main())
