#!/usr/bin/env python3
"""
manifest_append.py — Gemeinsamer Manifest-Append-Helper (BL-367 F8/F9, parent BL-322).

EIN robuster Append-Pfad fuer ALLE Berater-Manifest-Writes — ersetzt das ~14x ad-hoc
PowerShell/Python-Append pro Berater. Eliminiert auf einen Schlag (BL-367 F8/F9/Verstaerkung):
  - F8 : unbalancierte col-0-```-Fences (latentes Korruptions-Risiko fuer YAML-Block-Parser).
  - F9 : python3-MS-Store-Stub silent-no-op (Phantom-Write / silent data loss auf Windows).
  - Glue-Klasse: PowerShell-here-string-geglue'te Zeilen (z.B. "...befund: true    batch_PL3:").

5 Eigenschaften (BL-367 Fix-Skizze, woertlich):
  1. utf-8 no-BOM         — read strip-BOM (utf-8-sig), write IMMER ohne BOM.
  2. col-0-fence-balanced — zaehlt NUR Spalte-0-```; indentierte/Prosa-``` ausgeschlossen
                            (F8-KORREKTUR: naive ```-Zaehlung produziert Fehlalarme +
                            Falsch-"Reparaturen"). Ungerade col-0-Fences nach Append -> RAISE, KEIN Write.
  3. line-separator-safe  — Block startet IMMER auf neuer Zeile; bestehender NL-Stil (CRLF/LF) bleibt.
                            Kein Zeilen-Merge/Glue zwischen Bestand und Block.
  4. post-write Re-Read   — nach dem Write: re-read + verify Marker praesent; sonst RuntimeError
                            (NIE silent — faengt F9-Phantom-Write strukturell).
  5. py-3                 — reines Python-Modul. Der F9-Stub (`python3` -> MS-Store) kann das Modul
                            nicht laden -> kein Phantom-Write. CLI + Doku nutzen `py -3` (Windows-robust).

CLI:
  py -3 .claude/scripts/manifest_append.py <manifest_path> --block-file <f> [--marker "<unique>"]
  echo "<block>" | py -3 .claude/scripts/manifest_append.py <manifest_path> --block -
API:
  from manifest_append import append_block, count_col0_fences
  append_block(manifest_path, block_text, marker=None) -> dict
"""

import json
import sys
from pathlib import Path


def count_col0_fences(text: str) -> int:
    """Anzahl der Spalte-0-Code-Fences (Zeile beginnt OHNE Einrueckung mit ```).

    Indentierte / Prosa-```-Marker (mit fuehrendem Whitespace) werden NICHT gezaehlt.
    Das ist die F8-KORREKTUR: eine naive ```-Zaehlung zaehlt ein eingeruecktes Prosa-Zitat
    als strukturellen Fence -> Fehlalarm + Risiko einer Falsch-"Reparatur", die erst eine
    echte Imbalance einfuehrt. Nur col-0-Fences sind strukturelle YAML-Block-Grenzen.
    """
    n = 0
    for ln in text.split("\n"):
        if ln.startswith("```"):
            n += 1
    return n


def _detect_nl(raw: bytes) -> str:
    """CRLF wenn irgendwo \\r\\n vorkommt, sonst LF. Default LF fuer leere/neue Files."""
    return "\r\n" if b"\r\n" in raw else "\n"


def _read_text_no_bom(path: Path):
    """Returns (text_LF_normalized, nl_style, existed). utf-8-sig strippt ein evtl. BOM beim Read."""
    if not path.exists():
        return "", "\n", False
    raw = path.read_bytes()
    nl = _detect_nl(raw)
    text = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    return text, nl, True


def append_block(manifest_path, block_text: str, marker: str | None = None) -> dict:
    """Haengt block_text robust an manifest_path an (5 Eigenschaften, siehe Modul-Docstring).

    Args:
      manifest_path: Ziel-Manifest (wird erzeugt falls nicht vorhanden).
      block_text:    der anzuhaengende Block (eigene Fences muessen in sich balanciert sein).
      marker:        eindeutiger String, der NACH dem Write im File praesent sein MUSS.
                     Default = erste nicht-leere Zeile des Blocks (stabiler Single-Line-Anker).

    Raises:
      ValueError:   block_text leer / kein Marker ableitbar.
      RuntimeError: col-0-Fence-Imbalance nach Append (F8) | BOM nach Write |
                    Marker fehlt nach Re-Read (F9 silent-no-op).

    Returns:
      dict {ok, path, existed, bytes, col0_fences, marker, nl}.
    """
    p = Path(manifest_path)
    text, nl, existed = _read_text_no_bom(p)

    block = block_text.replace("\r\n", "\n").replace("\r", "\n").strip("\n")
    if not block.strip():
        raise ValueError("manifest_append: block_text ist leer — nichts anzuhaengen.")

    # (4-Vorbereitung) Marker: stabiler Single-Line-Anker = erste nicht-leere Block-Zeile.
    if marker is None:
        nonempty = [ln for ln in block.split("\n") if ln.strip()]
        marker = nonempty[0].strip()
    marker_norm = marker.replace("\r\n", "\n").replace("\r", "\n")
    if not marker_norm.strip():
        raise ValueError("manifest_append: kein Marker ableitbar.")

    # (3) line-separator-safe: Bestand auf genau eine Trennleerzeile normieren, dann Block.
    if existed and text.strip():
        base = text.rstrip("\n") + "\n\n"
    else:
        base = ""
    new_text = base + block + "\n"

    # (2) col-0-Fence-Balance VOR dem Write pruefen — kein korrupter Write (F8).
    fences = count_col0_fences(new_text)
    if fences % 2 != 0:
        existing_fences = count_col0_fences(text)
        block_fences = count_col0_fences(block)
        raise RuntimeError(
            f"manifest_append: col-0-```-Fence-Imbalance ({fences} ungerade) nach Append an "
            f"{p.name} — KEIN Write (F8). Bestand={existing_fences}, Block={block_fences}. "
            f"{'Bestand bereits unbalanciert.' if existing_fences % 2 else 'Block fuehrt Imbalance ein.'}"
        )

    # (1) write utf-8 OHNE BOM, (3) im bestehenden NL-Stil.
    out = new_text.replace("\n", nl)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(out.encode("utf-8"))

    # (4) post-write Re-Read-Assert — nie silent (F9).
    verify_raw = p.read_bytes()
    if verify_raw[:3] == b"\xef\xbb\xbf":
        raise RuntimeError(f"manifest_append: BOM nach Write in {p.name} — Schreibpfad fehlerhaft.")
    verify = verify_raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    if marker_norm not in verify:
        raise RuntimeError(
            f"manifest_append: Marker {marker_norm!r} nach Re-Read NICHT in {p.name} gefunden — "
            f"moeglicher silent no-op / Phantom-Write (F9). KEIN Erfolg gemeldet."
        )

    return {
        "ok": True,
        "path": str(p),
        "existed": existed,
        "bytes": len(verify_raw),
        "col0_fences": count_col0_fences(verify),
        "marker": marker_norm.split("\n")[0],
        "nl": "CRLF" if nl == "\r\n" else "LF",
    }


def main(argv: list[str]) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Robuster Manifest-Block-Append (BL-367 F8/F9).")
    ap.add_argument("manifest_path")
    ap.add_argument("--block", help="Block-Text direkt, oder '-' fuer stdin.")
    ap.add_argument("--block-file", help="Datei mit Block-Text (utf-8).")
    ap.add_argument("--marker", default=None, help="Pflicht-Marker (Default: erste Block-Zeile).")
    a = ap.parse_args(argv[1:])

    if a.block_file:
        block = Path(a.block_file).read_text(encoding="utf-8-sig")
    elif a.block is None or a.block == "-":
        block = sys.stdin.read()
    else:
        block = a.block

    try:
        res = append_block(a.manifest_path, block, marker=a.marker)
    except (ValueError, RuntimeError) as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(res, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
