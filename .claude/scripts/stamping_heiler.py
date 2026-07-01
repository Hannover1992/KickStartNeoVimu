#!/usr/bin/env python3
"""
stamping_heiler.py — BL-343 / batch_PL2 / PL-343-3 (M3, Stage 1, Atomic).

Manifest-Write-Back-Wrapper um das Bestands-Primitiv aus resolve_format_version.py.
Liest ein Manifest von Platte, stempelt die `format_version:`-Zeile additiv ins
Top-Level-Frontmatter (Writer=Follow, Wert via resolve_format_version) und schreibt
es LOSSLESS zurueck — idempotent, version=None-safe, dry_run-faehig.

Kein eigenes Versions-Literal, keine Re-Implementierung des Stempel-Algorithmus:
stamp_format_version_lines / read_format_version / resolve_format_version werden
1:1 wiederverwendet. Import-by-Name macht resolve_format_version auf diesem Modul
monkeypatch-bar (Test pinnt sh.resolve_format_version, Writer=Follow).
"""
from __future__ import annotations

import os
import sys

# __file__-RELATIVER sys.path-Eintrag (cwd-INVARIANT, BL-343-Linie) — das Primitiv
# liegt neben diesem Skript; Import funktioniert aus Repo-Root wie aus scripts-cwd.
_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

# Import-by-Name in den Modul-Namespace: resolve_format_version ist so als
# sh.resolve_format_version monkeypatch-bar (Test-Vertrag). Kein Re-Invent.
from resolve_format_version import (  # noqa: E402
    read_format_version,
    resolve_format_version,
    stamp_format_version_lines,
)


def stamp_manifest_writeback(manifest_path: str, dry_run: bool = False) -> dict:
    """Stempelt die format_version-Zeile additiv ins Manifest-Frontmatter (Write-Back).

    Returns: {stamped, was_already, version, [skipped_reason]}.

    - ist==0 (ungestempelt) UND soll!=None -> Stamp + Lossless-Write-Back,
      return {stamped:True, was_already:False, version:soll}.
    - ist==soll (bereits gestempelt)        -> No-Op,
      return {stamped:False, was_already:True, version:soll}. Idempotent.
    - soll==None (Registry nicht aufloesbar) -> No-Op, kein Crash,
      return {stamped:False, was_already:False, version:None, skipped_reason:"no_soll"}.
    - dry_run=True -> KEIN Write; return-Felder = was-wuerde.

    Lossless: NUR die eingefuegte format_version-Zeile ist neu; Body + andere
    Frontmatter-Felder bleiben byte-identisch.
    """
    text = _read_text(manifest_path)

    # Soll via Loader-Call (Writer=Follow, kein eigenes Literal; monkeypatch-bar).
    soll = resolve_format_version("manifest")
    if soll is None:
        # Symmetrie zu stamp_format_version_lines(version=None): Stamp WEG, kein Crash.
        return {
            "stamped": False,
            "was_already": False,
            "version": None,
            "skipped_reason": "no_soll",
        }

    # Ist aus dem Top-Level-Frontmatter (Dual-Read-Resilienz: fehlt -> 0 = Gen-0).
    fm_text = _extract_top_frontmatter(text)
    ist = read_format_version(fm_text)

    if ist == soll:
        # Bereits gestempelt -> No-Op (idempotent, kein Doppel-Stempel).
        return {"stamped": False, "was_already": True, "version": soll}

    # ist != soll (typischerweise ist==0 ungestempelt) -> additiv stempeln.
    # Ganze Datei-Lines durch das Primitiv: es fuegt nach der ERSTEN `---`
    # (= oeffnende FM-Fence) genau 1 Zeile ein. Body + Rest byte-identisch.
    lines = text.split("\n")
    stamped_lines = stamp_format_version_lines(lines, typ="manifest", version=soll)
    new_text = "\n".join(stamped_lines)

    if not dry_run:
        _write_text(manifest_path, new_text)

    return {"stamped": True, "was_already": False, "version": soll}


def _read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def _write_text(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def _extract_top_frontmatter(text: str) -> str:
    """Extrahiert den Frontmatter-Block zwischen erstem `---` und naechstem `---`.

    Kein Top-Level-Frontmatter -> "" (read_format_version -> 0 = Gen-0).
    """
    lines = text.split("\n")
    start = None
    for i, raw in enumerate(lines):
        if raw.strip() == "---":
            start = i
            break
    if start is None:
        return ""
    for j in range(start + 1, len(lines)):
        if lines[j].strip() == "---":
            return "\n".join(lines[start + 1:j])
    # Oeffnende Fence ohne Schliesser -> Rest als FM behandeln (Dual-Read-Resilienz).
    return "\n".join(lines[start + 1:])
