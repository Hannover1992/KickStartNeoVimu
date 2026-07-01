#!/usr/bin/env python3
"""BL-477 behavioral RED-Tests fuer pattern_library.py add-Tooling 4 Bugs.

RED-Worker: schreibt Tests gegen IST-Code (4 CORE-Faelle FAIL + 1 Robustheit).
GREEN-Worker (NICHT dieser): fixt die 4 Loci in pattern_library.py.

AK-3: next_id("COMMANDS") == "PT-CMD-001" (heute: PT-COMMANDS-001)
AK-4: arch-add erzeugt clean {pid}.md (heute: {pid}_{slug}.md)
AK-1: _append_index_row fuegt in ## Patterns-Tabelle ein (heute: am Datei-Ende)
AK-2: total_patterns-Frontmatter +1 if-present (heute: kein Bump)
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import pattern_library as pl


# ── Shared Fixture Helper (Vorbild test_pattern_library.py::_seed_layer) ──

def _seed_layer(vault: Path, layer="BE-DOMAIN", existing=None):
    d = vault / "Libraries" / "PatternLibrary" / "_project" / layer
    d.mkdir(parents=True, exist_ok=True)
    for pid_name in (existing or []):
        (d / f"{pid_name}.md").write_text("---\nid: x\n---\n", encoding="utf-8")
    return d


# ── AK-3: next_id("COMMANDS") == "PT-CMD-001" ──

def test_next_id_commands_pt_cmd(tmp_path):
    """AK-3 RED: LAYER_SHORT fehlt COMMANDS-Eintrag -> faellt auf layer-string 'COMMANDS' zurueck
    -> next_id liefert 'PT-COMMANDS-001'. GREEN fixt via LAYER_SHORT["COMMANDS"]="CMD"."""
    _seed_layer(tmp_path, layer="COMMANDS")
    result = pl.next_id("COMMANDS", vault_root=tmp_path)
    assert result == "PT-CMD-001", (
        f"Erwartet 'PT-CMD-001', bekommen '{result}'. "
        "LAYER_SHORT fehlt COMMANDS-Eintrag (AC-3, BL-477)."
    )


# ── AK-4: arch-add erzeugt clean {pid}.md (SCOPED arch) ──

def test_arch_add_clean_filename(tmp_path):
    """AK-4 RED: _name_to_filename haengt _{slug} an -> Dateiname 'PT-DOM-001_Some_Name.md'.
    GREEN fixt arch-Pfad auf clean '{pid}.md'; semantic-Seite (add_semantic_file) UNVERAENDERT."""
    _seed_layer(tmp_path)
    pid, fpath, _ = pl.add_arch(
        "BE-DOMAIN", "Some Name",
        description="d",
        vault_root=tmp_path,
    )
    assert pid == "PT-DOM-001", f"pid erwartet PT-DOM-001, bekommen {pid!r}"
    assert fpath.name == "PT-DOM-001.md", (
        f"Dateiname erwartet 'PT-DOM-001.md', bekommen '{fpath.name}'. "
        "_name_to_filename haengt Slug an (AC-4 SCOPED arch, BL-477)."
    )
    # Negativ-Assert: die slug-Variante darf NICHT existieren
    slug_path = fpath.parent / "PT-DOM-001_Some_Name.md"
    assert not slug_path.exists(), (
        f"Slug-Datei sollte NICHT existieren: {slug_path.name}"
    )


# ── AK-1: Insert in ## Patterns-Tabelle (Multi-Tab-Fixture) ──

# Kanonischer Multi-Tab-Index: ## Patterns + ## Bootstrap-Historie
# Der ## Patterns-Header ist _is_table_header-konform (enthaelt ID + Kurzbeschreibung).
# Der ## Bootstrap-Historie-Block traegt eine NICHT-_is_table_header-Tabelle (kein ID-Feld).
_MULTI_TAB_INDEX = """\
# COMMANDS Pattern Library

## Patterns

| ID | Datei | Kurzbeschreibung | usage_count | broken_count | status |
|----|-------|-----------------|-------------|--------------|--------|
| PT-CMD-001 | [PT-CMD-001.md](PT-CMD-001.md) | Erstes | 0 | 0 | experimental |

## Bootstrap-Historie

| Datum | Aktion |
|-------|--------|
| 2026-05-02 | seed |
"""


def test_index_row_in_patterns_table(tmp_path):
    """AK-1 RED: _append_index_row Z372 nutzt 'last_tbl = max(letzte |-Zeile GANZER Datei)'.
    Bei Multi-Tab-Fixture landet neue Zeile UNTER Bootstrap-Historie (Datei-Ende).
    GREEN fixiert Insert-Punkt auf Ende der ## Patterns-Tabelle (ab header_idx)."""
    # COMMANDS-Layer-Verzeichnis + kanonische Multi-Tab-_index.md anlegen
    ld = tmp_path / "Libraries" / "PatternLibrary" / "_project" / "COMMANDS"
    ld.mkdir(parents=True, exist_ok=True)
    # Existierende PT-CMD-001.md damit next_id PT-CMD-002 vergibt
    (ld / "PT-CMD-001.md").write_text("---\nid: PT-CMD-001\n---\n", encoding="utf-8")
    (ld / "_index.md").write_text(_MULTI_TAB_INDEX, encoding="utf-8")

    # Direkt _append_index_row aufrufen (ohne add_arch) um Filename-Bug AK-4 zu isolieren
    pl._append_index_row(
        "arch", "COMMANDS", "PT-CMD-002", "PT-CMD-002.md",
        "Zweites", story=None, vault_root=tmp_path,
    )

    lines = (ld / "_index.md").read_text(encoding="utf-8").splitlines()

    # Neue Zeile muss IRGENDWO in der Datei sein
    new_indices = [i for i, l in enumerate(lines) if "PT-CMD-002" in l]
    assert new_indices, "PT-CMD-002 wurde nicht in die _index.md geschrieben"
    new_idx = new_indices[0]

    # Bootstrap-Historie-Heading
    boot_indices = [i for i, l in enumerate(lines) if "Bootstrap-Historie" in l]
    assert boot_indices, "Bootstrap-Historie-Heading nicht gefunden (Fixture-Problem)"
    boot_idx = boot_indices[0]

    # KERN-ASSERT: neue Zeile muss VOR Bootstrap-Historie stehen
    assert new_idx < boot_idx, (
        f"PT-CMD-002 steht in Zeile {new_idx}, Bootstrap-Historie-Heading in Zeile {boot_idx}. "
        "Die neue Zeile ist unter die Bootstrap-Tabelle geraten (AC-1, BL-477). "
        "Erwartet: new_idx < boot_idx (neue Zeile in der ## Patterns-Tabelle)."
    )

    # Praeziser: PT-CMD-001 < PT-CMD-002 < Bootstrap-Heading
    pt1_indices = [i for i, l in enumerate(lines) if "PT-CMD-001" in l and l.strip().startswith("|")]
    assert pt1_indices, "PT-CMD-001-Zeile nicht gefunden"
    pt1_idx = pt1_indices[0]
    assert pt1_idx < new_idx < boot_idx, (
        f"Erwartete Reihenfolge PT-CMD-001({pt1_idx}) < PT-CMD-002({new_idx}) < Bootstrap({boot_idx})"
    )


# ── AK-2: total_patterns-Frontmatter +1 if-present ──

_FM_INDEX_WITH_TOTAL = """\
---
id_prefix: PT-CMD
total_patterns: 5
---
# COMMANDS Pattern Library

## Patterns

| ID | Datei | Kurzbeschreibung | usage_count | broken_count | status |
|----|-------|-----------------|-------------|--------------|--------|
| PT-CMD-001 | [PT-CMD-001.md](PT-CMD-001.md) | Erstes | 0 | 0 | experimental |
"""

_FM_INDEX_NO_TOTAL = """\
---
id_prefix: PT-CMD
---
# COMMANDS Pattern Library

## Patterns

| ID | Datei | Kurzbeschreibung | usage_count | broken_count | status |
|----|-------|-----------------|-------------|--------------|--------|
| PT-CMD-001 | [PT-CMD-001.md](PT-CMD-001.md) | Erstes | 0 | 0 | experimental |
"""


def test_total_patterns_increments(tmp_path):
    """AK-2 RED: grep 'total_patterns' ueber .claude/scripts = 0 Treffer -> kein Code bumpt es.
    Nach add bleibt total_patterns auf 5. GREEN fixt via +1 if-present in _append_index_row."""
    ld = tmp_path / "Libraries" / "PatternLibrary" / "_project" / "COMMANDS"
    ld.mkdir(parents=True, exist_ok=True)
    (ld / "PT-CMD-001.md").write_text("---\nid: PT-CMD-001\n---\n", encoding="utf-8")
    (ld / "_index.md").write_text(_FM_INDEX_WITH_TOTAL, encoding="utf-8")

    pl._append_index_row(
        "arch", "COMMANDS", "PT-CMD-002", "PT-CMD-002.md",
        "Zweites", story=None, vault_root=tmp_path,
    )

    txt = (ld / "_index.md").read_text(encoding="utf-8")
    match = re.search(r"^total_patterns:\s*(\d+)\b", txt, re.MULTILINE)
    assert match, f"total_patterns-Feld nicht in _index.md gefunden:\n{txt}"
    actual = int(match.group(1))
    assert actual == 6, (
        f"total_patterns erwartet 6 (5+1), bekommen {actual}. "
        "Kein Code bumpt das Frontmatter-Feld (AC-2, BL-477)."
    )


def test_total_patterns_absent_no_crash(tmp_path):
    """AK-2 Robustheit: _index.md OHNE total_patterns-Feld -> add_arch crasht nicht + fuegt
    KEINEN Key hinzu (if-present-Guard). Dieser Test sollte schon heute GREEN sein (kein Bump-Code
    -> kein Crash) und nach dem GREEN-Fix gruen bleiben (if-present-Guard)."""
    _seed_layer(tmp_path)  # BE-DOMAIN ohne _index.md (greenfield)
    # add_arch legt greenfield-_index.md ohne total_patterns an -> kein Crash erwartet
    pid, fpath, _ = pl.add_arch(
        "BE-DOMAIN", "Kein FM Total",
        description="d",
        vault_root=tmp_path,
    )
    assert pid is not None, "add_arch gab keine pid zurueck"
    assert fpath.exists(), f"Pattern-Datei nicht angelegt: {fpath}"

    ld = tmp_path / "Libraries" / "PatternLibrary" / "_project" / "BE-DOMAIN"
    idx_txt = (ld / "_index.md").read_text(encoding="utf-8")
    assert pid in idx_txt, f"pid {pid} nicht im Index"
    assert "total_patterns" not in idx_txt, (
        "total_patterns sollte NICHT erzwungen werden (if-present-Guard, AC-2, BL-477). "
        f"_index.md enthaelt: ...{idx_txt[:300]}..."
    )
