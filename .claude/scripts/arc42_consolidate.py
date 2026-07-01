"""BL-417: arc42 konsolidiertes all.md — Concat-Fan-In.

build_all_md(arc42_dir) -> Path
  Sammelt NN_*.md (01..12, numerisch sortiert), schreibt {arc42_dir}/all.md.
  AK-1: read-only Projektion — Quell-Dateien unveraendert.
  AK-2: Idempotent (sorted(), kein Timestamp, kein BOM).
  AK-3: TOC oben mit Sektionstiteln.
  AK-4: BOM-frei UTF-8, reines LF.
  AK-5: Kein Self-Include (all.md + 00_index.md ausgeschlossen).
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path


def _extract_first_heading(text: str) -> str:
    """Extrahiert die erste # -Heading-Zeile (ohne fuehrendes #)."""
    for line in text.splitlines():
        m = re.match(r"^#\s+(.+)", line)
        if m:
            return m.group(1).strip()
    return ""


def build_all_md(arc42_dir: "str | Path") -> Path:
    """Konkateniert NN_*.md (01..12) zu {arc42_dir}/all.md und gibt den Path zurueck."""
    arc42_dir = Path(arc42_dir)
    all_md = arc42_dir / "all.md"

    # Sammle NN_*.md, numerisch sortiert; exkludiere 00_index.md und all.md selbst
    section_files = sorted(
        [
            f
            for f in arc42_dir.glob("[0-9][0-9]_*.md")
            if f.name != "00_index.md" and f.name != "all.md"
        ],
        key=lambda f: f.name,  # lexikografisch == numerisch fuer zweistellige Praefix
    )

    # Texte lesen (Quellen werden NICHT veraendert)
    sections: list[tuple[str, str]] = []
    for f in section_files:
        text = f.read_text(encoding="utf-8")
        heading = _extract_first_heading(text)
        sections.append((heading, text))

    # TOC (AK-3)
    toc_lines = ["## Inhalt", ""]
    for heading, _ in sections:
        toc_lines.append(f"- {heading}")
    toc_lines.append("")
    toc = "\n".join(toc_lines)

    # Sektionen konkatenieren
    body_parts = [sec_text.rstrip("\n") for _, sec_text in sections]
    body = "\n\n---\n\n".join(body_parts)

    # Gesamt-Inhalt (TOC + Trennlinie + Body)
    content = toc + "\n---\n\n" + body + "\n"

    # AK-4: BOM-frei UTF-8, reines LF
    all_md.write_bytes(content.encode("utf-8"))

    return all_md


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="arc42 all.md Konsolidierung")
    parser.add_argument("--arc42-dir", required=True, help="Pfad zum arc42/-Verzeichnis")
    args = parser.parse_args()
    out = build_all_md(args.arc42_dir)
    print(f"Geschrieben: {out}")
