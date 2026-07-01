#!/usr/bin/env python3
"""
Tests fuer truth_edge_backref.py — YAML-Gueltigkeit nach materialize_edges (BL-451 AC-2a).

Bug-Reproduktion: _insert_referenced_by skippt NUR eingerueckte Folgezeilen (startswith(" ")).
Echte Atome verwenden Spalte-0 Block-Sequence fuer keywords:
  keywords:
  - alpha
  - beta
Die "- alpha"-Zeilen starten mit "-" (kein Space) -> werden NICHT geskippt -> referenced_by
wird DIREKT nach "keywords:" eingefuegt, VOR den "- item"-Zeilen -> kaputtes YAML.

RED-Tests: zeigen, dass der materialisierte Output KEIN gueltiges YAML mehr ist.
"""
from __future__ import annotations

import re
import yaml
import pytest

from truth_edge_backref import materialize_edges


# ---------------------------------------------------------------------------
# Hilfsfunktion: Frontmatter aus Datei-Inhalt extrahieren
# ---------------------------------------------------------------------------

def _extract_frontmatter(content: str) -> str:
    """Liefert den Text zwischen den '---'-Delimitern (ohne Delimiter selbst)."""
    m = re.match(r"^---\n(.*?)\n---\n", content, re.DOTALL)
    assert m is not None, f"Kein Frontmatter gefunden in:\n{content!r}"
    return m.group(1)


# ---------------------------------------------------------------------------
# Atom-Schreiber: EXAKTES Spalte-0-Block-Sequence-Format (Bug-Ausloeser)
# ---------------------------------------------------------------------------

def _write_atom_a(path, atom_id: str = "NS.A1") -> None:
    """Atom A mit edges -> NS.B1. keywords im Spalte-0-Format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        "type: truth\n"
        f"id: {atom_id}\n"
        "local_id: A1\n"
        "text: 'A1: irgendein einzeiliger text'\n"
        "keywords:\n"
        "- alpha\n"
        "- beta\n"
        "seq: 0\n"
        "edges:\n"
        "- rel: relates_to\n"
        "  ziel: NS.B1\n"
        "---\n"
        "body\n"
    )
    path.write_text(content, encoding="utf-8")


def _write_atom_b(path, atom_id: str = "NS.B1") -> None:
    """Atom B als Ziel-Atom. keywords im Spalte-0-Format (Bug-Ausloeser)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        "type: truth\n"
        f"id: {atom_id}\n"
        "local_id: B1\n"
        "text: 'B1: irgendein einzeiliger text'\n"
        "keywords:\n"
        "- alpha\n"
        "- beta\n"
        "- gamma\n"
        "seq: 0\n"
        "edges: []\n"
        "---\n"
        "body\n"
    )
    path.write_text(content, encoding="utf-8")


def _write_atom_b_multiline(path, atom_id: str = "NS.B1") -> None:
    """Atom B mit mehrzeiligem text (literal block) UND Spalte-0 keywords."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "---\n"
        "type: truth\n"
        f"id: {atom_id}\n"
        "local_id: B1\n"
        "text: |\n"
        "  Zeile eins: Kern-Phrase ist erhalten.\n"
        "  Zeile zwei: weitere Information.\n"
        "  Zeile drei: Abschluss.\n"
        "keywords:\n"
        "- alpha\n"
        "- beta\n"
        "- gamma\n"
        "seq: 0\n"
        "edges: []\n"
        "---\n"
        "body\n"
    )
    path.write_text(content, encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: Haupttest — YAML-Gueltigkeit + keywords intakt + referenced_by present
# ---------------------------------------------------------------------------

class TestMaterializeOutputValidYamlColumn0Keywords:
    def test_materialize_output_valid_yaml_column0_keywords(self, tmp_path):
        """Nach materialize_edges(apply=True) muss der Output von Atom B gueltiges YAML sein.

        Bug: referenced_by wird VOR die "- item"-Zeilen eingefuegt -> kaputtes YAML.
        RED erwartet: yaml.safe_load schlaegt fehl ODER keywords ist null/zerstoert
                      ODER referenced_by fehlt.
        """
        atom_a_path = tmp_path / "NS.A1.md"
        atom_b_path = tmp_path / "NS.B1.md"

        _write_atom_a(atom_a_path)
        _write_atom_b(atom_b_path)

        result = materialize_edges(tmp_path, apply=True)

        assert result["updated"] >= 1, (
            f"Kein Atom wurde aktualisiert (updated={result['updated']}). "
            "Index-Aufbau oder Edge-Inversion fehlgeschlagen."
        )

        content_b = atom_b_path.read_text(encoding="utf-8")
        fm_block = _extract_frontmatter(content_b)

        # Muss gueltiges YAML sein
        parsed = yaml.safe_load(fm_block)
        assert parsed is not None, "yaml.safe_load lieferte None fuer Frontmatter von Atom B"

        # keywords muss die vollstaendige Liste sein (nicht null/zerstoert)
        assert parsed.get("keywords") == ["alpha", "beta", "gamma"], (
            f"keywords zerstoert oder fehlend. Wert: {parsed.get('keywords')!r}\n"
            f"Frontmatter:\n{fm_block}"
        )

        # referenced_by muss vorhanden und eine nicht-leere Liste sein
        rb = parsed.get("referenced_by")
        assert rb is not None and len(rb) >= 1, (
            f"referenced_by fehlt oder leer. Wert: {rb!r}\n"
            f"Frontmatter:\n{fm_block}"
        )
        assert rb[0].get("by") == "NS.A1", (
            f"referenced_by[0].by erwartet 'NS.A1', bekam: {rb[0].get('by')!r}"
        )
        assert rb[0].get("kind") == "truth_edge", (
            f"referenced_by[0].kind erwartet 'truth_edge', bekam: {rb[0].get('kind')!r}"
        )

        # Felder nach keywords muessen intakt sein
        assert parsed.get("seq") == 0, (
            f"seq-Feld nach keywords zerstoert. Wert: {parsed.get('seq')!r}"
        )
        assert parsed.get("id") == "NS.B1", (
            f"id-Feld nach keywords zerstoert. Wert: {parsed.get('id')!r}"
        )


# ---------------------------------------------------------------------------
# Test 2: Keine orphaned block-items im Frontmatter
# ---------------------------------------------------------------------------

class TestMaterializeNoOrphanListItems:
    def test_materialize_no_orphan_list_items(self, tmp_path):
        """Nach apply darf kein orphaned list-item im Frontmatter existieren.

        Bug-Ausloeser: referenced_by wird zwischen "keywords:" und "- alpha" eingefuegt.
        Das ergibt:
          keywords:
          referenced_by:
            - by: NS.A1
              kind: truth_edge
          - alpha   <- orphaned block-item
          - beta
          - gamma
        yaml.safe_load wuerde "- alpha" etc. als Fehler oder fehlinterpretieren.
        """
        atom_a_path = tmp_path / "NS.A1.md"
        atom_b_path = tmp_path / "NS.B1.md"

        _write_atom_a(atom_a_path)
        _write_atom_b(atom_b_path)

        materialize_edges(tmp_path, apply=True)

        content_b = atom_b_path.read_text(encoding="utf-8")
        fm_block = _extract_frontmatter(content_b)

        # Re-parsen muss funktionieren
        parsed = yaml.safe_load(fm_block)
        assert parsed is not None, (
            f"yaml.safe_load fehlgeschlagen (None). Frontmatter:\n{fm_block}"
        )

        # keywords muss exakt die 3-Element-Liste sein (kein Datenverlust)
        kw = parsed.get("keywords")
        assert isinstance(kw, list), (
            f"keywords ist keine Liste sondern {type(kw).__name__}. Wert: {kw!r}\n"
            f"Frontmatter:\n{fm_block}"
        )
        assert set(kw) == {"alpha", "beta", "gamma"}, (
            f"keywords hat falsche Elemente: {kw!r}\n"
            f"Frontmatter:\n{fm_block}"
        )
        assert len(kw) == 3, (
            f"keywords hat {len(kw)} Elemente statt 3 (Datenverlust): {kw!r}"
        )


# ---------------------------------------------------------------------------
# Test 3: Mehrzeiliger text + Spalte-0 keywords + eingehende Kante -> gueltig
# ---------------------------------------------------------------------------

class TestMaterializeMultilineTextColumn0KeywordsValid:
    def test_materialize_multiline_text_column0_keywords_valid(self, tmp_path):
        """Atom B mit mehrzeiligem text (literal block) UND Spalte-0 keywords.

        Nach apply: yaml.safe_load OK, text semantisch erhalten,
        keywords intakt, referenced_by present.
        """
        atom_a_path = tmp_path / "NS.A1.md"
        atom_b_path = tmp_path / "NS.B1.md"

        _write_atom_a(atom_a_path)
        _write_atom_b_multiline(atom_b_path)

        result = materialize_edges(tmp_path, apply=True)
        assert result["updated"] >= 1, (
            f"Kein Update (updated={result['updated']}). "
            "Edge-Inversion oder Indexaufbau fehlgeschlagen."
        )

        content_b = atom_b_path.read_text(encoding="utf-8")
        fm_block = _extract_frontmatter(content_b)

        # YAML muss gueltig bleiben
        parsed = yaml.safe_load(fm_block)
        assert parsed is not None, (
            f"yaml.safe_load lieferte None. Frontmatter:\n{fm_block}"
        )

        # text-Wert semantisch erhalten (Kern-Phrase)
        text_val = parsed.get("text", "")
        assert "Kern-Phrase ist erhalten" in str(text_val), (
            f"text-Wert enthaelt die Kern-Phrase nicht. Wert: {text_val!r}"
        )

        # keywords intakt
        kw = parsed.get("keywords")
        assert kw == ["alpha", "beta", "gamma"], (
            f"keywords zerstoert. Wert: {kw!r}\nFrontmatter:\n{fm_block}"
        )

        # referenced_by vorhanden
        rb = parsed.get("referenced_by")
        assert rb is not None and len(rb) >= 1, (
            f"referenced_by fehlt oder leer. Wert: {rb!r}\nFrontmatter:\n{fm_block}"
        )
        assert rb[0].get("by") == "NS.A1", (
            f"referenced_by[0].by: erwartet 'NS.A1', bekam {rb[0].get('by')!r}"
        )


# ---------------------------------------------------------------------------
# Test 4 (RED): materialize_edges darf keywords NIE mit Dicts befuellen
# (BL-xxx AC: truth_keyword_demerge guard)
# ---------------------------------------------------------------------------

class TestMaterializeKeywordsTypePurity:
    """Structural guard: materialize_edges must never pollute the keywords field
    with dict entries.

    RED now because truth_keyword_demerge is absent (ModuleNotFoundError).
    GREEN only after both:
      1. truth_keyword_demerge.py is implemented (assert_keywords_type_pure), AND
      2. materialize_edges keeps keywords string-only.
    """

    def test_materialize_does_not_pollute_keywords_with_dicts(self, tmp_path):
        """After materialize_edges(apply=True), Atom B's keywords must be all strings.

        Uses assert_keywords_type_pure from truth_keyword_demerge to enforce the
        type contract. If the materializer ever leaks dict entries into keywords,
        assert_keywords_type_pure raises and this test fails.
        """
        from truth_keyword_demerge import assert_keywords_type_pure

        atom_a_path = tmp_path / "NS.A1.md"
        atom_b_path = tmp_path / "NS.B1.md"

        _write_atom_a(atom_a_path)
        _write_atom_b(atom_b_path)

        result = materialize_edges(tmp_path, apply=True)
        assert result["updated"] >= 1, (
            f"Kein Update (updated={result['updated']}). "
            "Edge-Inversion oder Indexaufbau fehlgeschlagen."
        )

        content_b = atom_b_path.read_text(encoding="utf-8")
        fm_block = _extract_frontmatter(content_b)
        parsed = yaml.safe_load(fm_block)
        assert parsed is not None, (
            f"yaml.safe_load lieferte None. Frontmatter:\n{fm_block}"
        )

        kw = parsed.get("keywords")
        assert isinstance(kw, list), (
            f"keywords ist keine Liste nach materialize: {type(kw).__name__}. "
            f"Wert: {kw!r}"
        )

        # This is the structural guard: raises AssertionError if any entry is a dict
        assert_keywords_type_pure(kw)

        # Additionally verify every entry is a str
        for entry in kw:
            assert isinstance(entry, str), (
                f"keywords-Eintrag ist kein str: {entry!r} (type={type(entry).__name__})"
            )
