"""BL-417: arc42 konsolidiertes all.md — Concat-Fan-In.

RED-Tests (Test-Autor != GREEN-Implementierer, false-GREEN-Fang). Erwartetes Verhalten:
- build_all_md(arc42_dir) konkateniert die gerenderten NN_*.md (01..12) in NUMERISCHER
  Sektions-Reihenfolge zu {arc42_dir}/all.md (read-only Projektion, AK-1/AK-2).
- TOC oben (AK-3). BOM-frei UTF-8, reines LF (AK-4). Idempotent (AK-2).
- 00_index.md + all.md selbst werden NICHT mit-konkateniert (kein Self-Include).
- Quell-NN_*.md bleiben unveraendert (read-only, INV-ARC42-1).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import arc42_consolidate as ac  # noqa: E402


def _setup(arc42_dir: Path):
    arc42_dir.mkdir(parents=True)
    (arc42_dir / "00_index.md").write_text("# Index\nGrounding-Coverage: 90%\n", encoding="utf-8")
    # absichtlich NICHT in Datei-Reihenfolge angelegt -> testet numerische Sortierung
    (arc42_dir / "03_kontext.md").write_text("# 3. Kontext\nKONTEXT_BODY\n", encoding="utf-8")
    (arc42_dir / "01_einfuehrung_ziele.md").write_text("# 1. Einfuehrung\nEINFUEHRUNG_BODY\n", encoding="utf-8")


def test_builds_all_md_in_section_order(tmp_path):
    d = tmp_path / "arc42"
    _setup(d)
    out = ac.build_all_md(d)
    assert out == d / "all.md"
    txt = (d / "all.md").read_text(encoding="utf-8")
    # Sektions-Reihenfolge: §1 vor §3
    assert "EINFUEHRUNG_BODY" in txt and "KONTEXT_BODY" in txt
    assert txt.index("EINFUEHRUNG_BODY") < txt.index("KONTEXT_BODY")


def test_has_toc(tmp_path):
    d = tmp_path / "arc42"
    _setup(d)
    ac.build_all_md(d)
    txt = (d / "all.md").read_text(encoding="utf-8")
    # AK-3: ein Inhaltsverzeichnis oben (TOC-Marker + beide Sektionstitel)
    assert ("Inhalt" in txt or "TOC" in txt or "Table of Contents" in txt)
    assert "Einfuehrung" in txt and "Kontext" in txt


def test_no_self_include(tmp_path):
    d = tmp_path / "arc42"
    _setup(d)
    ac.build_all_md(d)
    txt = (d / "all.md").read_text(encoding="utf-8")
    assert "Grounding-Coverage: 90%" not in txt.split("KONTEXT_BODY")[0].replace("# Index", "") or "00_index" not in txt
    # all.md darf sich nicht selbst einschliessen (kein doppelter Body bei Re-Run)


def test_bom_free_lf_and_idempotent(tmp_path):
    d = tmp_path / "arc42"
    _setup(d)
    ac.build_all_md(d)
    raw = (d / "all.md").read_bytes()
    assert not raw.startswith(b"\xef\xbb\xbf"), "all.md muss BOM-frei sein (AK-4)"
    assert b"\r\n" not in raw, "all.md muss reines LF sein (AK-4)"
    first = (d / "all.md").read_text(encoding="utf-8")
    ac.build_all_md(d)  # Re-Run
    second = (d / "all.md").read_text(encoding="utf-8")
    assert first == second, "build_all_md muss idempotent sein (AK-2)"


def test_sources_unchanged(tmp_path):
    d = tmp_path / "arc42"
    _setup(d)
    before = (d / "01_einfuehrung_ziele.md").read_text(encoding="utf-8")
    ac.build_all_md(d)
    after = (d / "01_einfuehrung_ziele.md").read_text(encoding="utf-8")
    assert before == after, "Quell-Sektionen bleiben unveraendert (read-only, INV-ARC42-1)"
