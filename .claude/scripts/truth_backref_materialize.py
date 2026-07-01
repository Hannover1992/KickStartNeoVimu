#!/usr/bin/env python3
"""
truth_backref_materialize.py — Materializer fuer referenced_by[] (BL-309 P1).

Komponiert die GETESTETEN Primitive aus truth_backref_index.py:
  - build_backref_index(root)  -> {local_id: [{by, kind}]}
  - apply_backrefs-Struktur    -> t["referenced_by"] = index[local_id]

Scant root rekursiv nach truth-Atomen (type: truth + local_id im Frontmatter),
plant pro Atom den referenced_by-Eintrag aus dem Inverse-Index, und schreibt ihn
SURGICAL ins Frontmatter (NUR das referenced_by-Feld einfuegen/ersetzen; alle anderen
Zeilen — insbesondere der mehrzeilige text:-Block — byte-identisch lassen).

Modi:
  - apply=False (dry-run): nur zaehlen, NIE schreiben (updated=0).
  - apply=True: schreiben. updated = Anzahl tatsaechlich geaenderter Dateien. Idempotent.
  - backup_dir + apply: VOR dem Schreiben jede zu aendernde Datei nach backup_dir kopieren;
    backed_up = updated.

Rueckgabe-dict: {"scanned", "with_refs", "would_update", "updated", "backed_up"} (alle int).
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

import truth_backref_index

# Frontmatter-Block: --- ... --- am Datei-Anfang.
_FM_BLOCK = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)
# Feldzeile: "key: ..." auf Top-Level (keine Einrueckung).
_FIELD_RE = re.compile(r"^(\w[\w-]*):")


def _parse_frontmatter(content: str):
    """Liefert (fm_text, fm_start, fm_end) oder None — fm_text ist der Block ZWISCHEN den Delimitern.

    fm_start/fm_end sind char-Offsets im content (fm_start = nach dem oeffnenden '---\\n',
    fm_end = vor dem schliessenden '\\n---\\n')."""
    m = _FM_BLOCK.match(content)
    if not m:
        return None
    return m.group(1), m.start(1), m.end(1)


def _scalar_field(fm_text: str, field: str) -> str | None:
    """Holt einen einfachen einzeiligen Skalar-Wert (z.B. local_id, type) aus dem Frontmatter."""
    for line in fm_text.split("\n"):
        m = re.match(rf"^{re.escape(field)}:\s*(.*)$", line)
        if m:
            return m.group(1).strip()
    return None


def _is_truth_atom(fm_text: str) -> bool:
    return _scalar_field(fm_text, "type") == "truth" and _scalar_field(fm_text, "local_id") is not None


def _render_referenced_by(rb: list[dict]) -> list[str]:
    """Block-Sequence-Form passend zum Schema (Liste von {by, kind}-Dicts)."""
    lines = ["referenced_by:"]
    for entry in rb:
        by = entry.get("by", "")
        kind = entry.get("kind", "")
        lines.append(f"  - by: {by}")
        lines.append(f"    kind: {kind}")
    return lines


def _split_fm_lines(fm_text: str) -> list[str]:
    return fm_text.split("\n")


def _strip_existing_referenced_by(lines: list[str]) -> list[str]:
    """Entfernt einen vorhandenen referenced_by:-Block (Feldzeile + eingerueckte Folgezeilen
    sowie column-0 Block-Sequence-Items wie '- by: ...')."""
    out: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if re.match(r"^referenced_by:", line):
            # Feldzeile selbst ueberspringen
            i += 1
            # Gesamten Block-Body konsumieren: eingerueckte Zeilen UND column-0 Listen-Items
            while i < n:
                nxt = lines[i]
                if nxt.strip() == "":
                    break  # Leerzeile beendet den Block
                is_indented = nxt.startswith(" ") or nxt.startswith("\t")
                is_list_item = nxt.lstrip().startswith("- ") or nxt.strip() == "-"
                if is_indented or is_list_item:
                    i += 1
                    continue
                break  # echtes Top-Level-Feld (z.B. 'seq:', 'edges:') -> stoppen
            continue
        out.append(line)
        i += 1
    return out


def _insert_referenced_by(lines: list[str], rb_lines: list[str]) -> list[str]:
    """Fuegt referenced_by-Zeilen an stabiler Stelle ein: direkt nach der keywords:-Sektion,
    sonst am Ende des Frontmatter-Blocks."""
    # Suche das Ende der keywords:-Sektion.
    insert_at = None
    n = len(lines)
    for idx, line in enumerate(lines):
        if re.match(r"^keywords:", line):
            # Ende der keywords-Sektion finden (eingerueckte Listenzeilen)
            j = idx + 1
            while j < n and lines[j].strip() != "" and (
                lines[j].startswith(" ") or lines[j].startswith("\t")
                or lines[j].lstrip().startswith("- ") or lines[j].strip() == "-"
            ):
                j += 1
            insert_at = j
            break
    if insert_at is None:
        # Keine keywords-Sektion -> ans Ende des Frontmatter-Blocks anhaengen.
        insert_at = len(lines)
        # Trailing leere Zeile am Block-Ende vermeiden: einfuegen vor evtl. letzter Leerzeile.
        while insert_at > 0 and lines[insert_at - 1].strip() == "":
            insert_at -= 1
    return lines[:insert_at] + rb_lines + lines[insert_at:]


def _build_new_content(content: str, rb: list[dict]) -> str | None:
    """Baut den neuen Datei-Inhalt mit surgisch eingefuegtem/ersetztem referenced_by.
    Liefert None, wenn kein Frontmatter vorhanden."""
    parsed = _parse_frontmatter(content)
    if parsed is None:
        return None
    fm_text, fm_start, fm_end = parsed

    lines = _split_fm_lines(fm_text)
    lines = _strip_existing_referenced_by(lines)
    rb_lines = _render_referenced_by(rb)
    lines = _insert_referenced_by(lines, rb_lines)

    new_fm = "\n".join(lines)
    return content[:fm_start] + new_fm + content[fm_end:]


def _iter_truth_atoms(root: Path):
    """Yields (path, fm_text, local_id) fuer alle truth-Atome unter root."""
    for f in sorted(root.rglob("*.md")):
        if not f.is_file():
            continue
        # BL-494-family: tooling/backup/scratch under any .claude/ segment is NEVER
        # vault content (e.g. Stage-4 backref_backup copies). Skip so the census never
        # double-counts. relative_to(root) so a vault that itself lives under a .claude
        # ancestor is not wholly excluded — only .claude segments BELOW root are skipped.
        try:
            rel_parts = f.relative_to(root).parts
        except ValueError:
            rel_parts = f.parts
        if ".claude" in rel_parts:
            continue
        try:
            content = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        parsed = _parse_frontmatter(content)
        if parsed is None:
            continue
        fm_text = parsed[0]
        if not _is_truth_atom(fm_text):
            continue
        local_id = _scalar_field(fm_text, "local_id")
        yield f, content, local_id


def materialize(root: Path, apply: bool = False, backup_dir: Path | None = None) -> dict:
    """Materialisiert referenced_by[] in truth-Atomen unter root.

    apply=False -> dry-run (nur zaehlen). apply=True -> schreiben (surgical patch).
    backup_dir + apply -> vor jedem Write die Datei sichern.
    """
    root = Path(root)
    index = truth_backref_index.build_backref_index(root)

    scanned = 0
    with_refs = 0
    would_update = 0
    updated = 0
    backed_up = 0

    if backup_dir is not None:
        backup_dir = Path(backup_dir)

    for path, content, local_id in _iter_truth_atoms(root):
        scanned += 1
        rb = index.get(local_id)
        if not rb:
            continue
        with_refs += 1

        new_content = _build_new_content(content, rb)
        if new_content is None:
            continue
        if new_content == content:
            # Bereits aktuell -> kein Update noetig (Idempotenz).
            continue

        would_update += 1

        if apply:
            if backup_dir is not None:
                backup_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup_dir / path.name)
                backed_up += 1
            path.write_text(new_content, encoding="utf-8")
            updated += 1

    return {
        "scanned": scanned,
        "with_refs": with_refs,
        "would_update": would_update,
        "updated": updated,
        "backed_up": backed_up,
    }


def main(argv: list[str]) -> int:
    p = argparse.ArgumentParser(
        prog="truth_backref_materialize",
        description="BL-309 P1: referenced_by[] surgical materializer",
    )
    p.add_argument("root", type=Path)
    p.add_argument("--apply", action="store_true", help="schreiben (sonst dry-run)")
    p.add_argument("--backup-dir", type=Path, default=None, help="Backup-Verzeichnis vor Apply")
    args = p.parse_args(argv)

    if not args.root.is_dir():
        print(f"ERROR: {args.root} kein Verzeichnis", file=sys.stderr)
        return 2

    res = materialize(args.root, apply=args.apply, backup_dir=args.backup_dir)
    print(
        f"scanned={res['scanned']} with_refs={res['with_refs']} "
        f"would_update={res['would_update']} updated={res['updated']} "
        f"backed_up={res['backed_up']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
