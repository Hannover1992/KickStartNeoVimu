"""
test_keyword_edge_truth_scope.py — RED-Worker BL-479 sub_batch_1 Stage 1

Tests: AC-1..4 (Truth-Scope-Schaerfung fuer _build_keyword_index + main-Loop)

Ziel-Modul: keyword_edge_writer.py (FILTER NOCH NICHT IMPLEMENTIERT -> alle Tests MUESSEN fehlschlagen)
Konvention: pytest, test_-Prefix, Fixtures via tmp_path

BL-479 AC-1: _build_keyword_index indiziert nur type:truth Atome
BL-479 AC-2: compute_keyword_edges erzeugt keine Kanten zu Nicht-Truth-Zielen
BL-479 AC-3: Scope-Invariante im Docstring von _build_keyword_index
BL-479 AC-4: Modul-Konstante EXPECTED_PRECISE_EDGE_COUNT = 48095 existiert
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Ensure the scripts directory is on sys.path so keyword_edge_writer is importable
sys.path.insert(0, str(Path(__file__).parent))


# ---------------------------------------------------------------------------
# Hilfsfunktion: minimale .md-Datei schreiben
# ---------------------------------------------------------------------------

def _write_md(path: Path, frontmatter_lines: str, body: str = "") -> Path:
    """Schreibt eine .md-Datei mit YAML-Frontmatter in den angegebenen Pfad."""
    path.parent.mkdir(parents=True, exist_ok=True)
    content = f"---\n{frontmatter_lines}\n---\n{body}\n"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# AC-1 — _build_keyword_index schließt Nicht-Truth-Files aus dem Index aus
# ---------------------------------------------------------------------------

def test_index_excludes_non_truth_files(tmp_path):
    """
    AC-1 RED: _build_keyword_index(vault) indiziert NUR Atome mit type:truth.

    Fixture-Vault:
      truths/W1.md       — type:truth, keywords:[alpha, beta]
      BL-X-node.md       — type:bug (kein truth), keywords:[alpha, beta]

    Erwartung (SOLL): Index fuer "alpha" enthaelt NUR W1-Eintrag.
    Aktuelles Verhalten (IST): beide Eintraege sind drin -> Test MUSS roт sein.
    """
    from keyword_edge_writer import _build_keyword_index  # type: ignore[import]

    # Truth-Atom
    _write_md(
        tmp_path / "truths" / "W1.md",
        "id: truth-scope.W1\nlocal_id: W1\ntype: truth\nkeywords:\n  - alpha\n  - beta",
    )
    # Nicht-Truth-File (type: bug)
    _write_md(
        tmp_path / "BL-X-node.md",
        "id: BL-X.node\nlocal_id: BL-X-node\ntype: bug\nkeywords:\n  - alpha\n  - beta",
    )

    index = _build_keyword_index(tmp_path)

    # "alpha" muss im Index vorhanden sein (Truth-Atom hat es)
    assert "alpha" in index, "Index fuer 'alpha' fehlt komplett — Truth-Atom nicht indiziert"

    alpha_entries = index["alpha"]
    atom_ids = [e.get("atom_id", "") for e in alpha_entries]
    local_ids = [e.get("local_id", "") for e in alpha_entries]

    # Truth-Atom MUSS drin sein
    assert any("W1" in aid or "W1" in lid for aid, lid in zip(atom_ids, local_ids)), (
        "Truth-Atom W1 fehlt im Index fuer 'alpha'"
    )

    # Nicht-Truth-File darf NICHT drin sein
    assert not any("BL-X" in aid or "BL-X-node" in lid for aid, lid in zip(atom_ids, local_ids)), (
        "Nicht-Truth-File BL-X-node ist im Index fuer 'alpha' — AC-1-Filter fehlt"
    )


# ---------------------------------------------------------------------------
# AC-2 — compute_keyword_edges erzeugt keine Kante zum Nicht-Truth-Ziel
# ---------------------------------------------------------------------------

def test_no_nontruth_edge_targets(tmp_path):
    """
    AC-2 RED: compute_keyword_edges liefert KEINE Kante mit Ziel=Nicht-Truth-Atom.

    Fixture-Vault: gleiche Struktur wie AC-1.
    Ablauf: _build_keyword_index -> compute_keyword_edges fuer W1 pruefen.

    Aktuelles Verhalten (IST): Kante truth-scope.W1 -> BL-X.node entsteht -> Test MUSS rot sein.
    """
    from keyword_edge_writer import _build_keyword_index, compute_keyword_edges  # type: ignore[import]

    # Truth-Atom (Quelle + potenzielles Ziel)
    _write_md(
        tmp_path / "truths" / "W1.md",
        "id: truth-scope.W1\nlocal_id: W1\ntype: truth\nkeywords:\n  - alpha\n  - beta",
    )
    # Nicht-Truth-File (Nicht-Truth-Ziel)
    _write_md(
        tmp_path / "BL-X-node.md",
        "id: BL-X.node\nlocal_id: BL-X-node\ntype: bug\nkeywords:\n  - alpha\n  - beta",
    )

    keyword_index = _build_keyword_index(tmp_path)

    src_atom = {
        "id": "truth-scope.W1",
        "local_id": "W1",
        "keywords": ["alpha", "beta"],
    }
    # Namespace aus Pfad: truths/
    edges = compute_keyword_edges(
        src_atom,
        keyword_index,
        src_namespace="truths",
        # Kein min_shared / df_threshold Override -> defaults
    )

    ziel_ids = [e.get("ziel", "") for e in edges]

    # Kein Ziel darf auf das Nicht-Truth-File zeigen
    assert not any("BL-X" in z or "BL-X-node" in z for z in ziel_ids), (
        f"Kante(n) zu Nicht-Truth-Ziel gefunden: {[z for z in ziel_ids if 'BL-X' in z or 'BL-X-node' in z]}"
        " — AC-2-Filter fehlt"
    )


# ---------------------------------------------------------------------------
# AC-4 — Modul-Konstante EXPECTED_PRECISE_EDGE_COUNT = 48095 existiert
# ---------------------------------------------------------------------------

def test_baseline_constant_exists():
    """
    AC-4 RED: keyword_edge_writer.EXPECTED_PRECISE_EDGE_COUNT muss importierbar
    sein und den Wert 48095 haben.

    Aktuelles Verhalten (IST): AttributeError / ImportError -> Test MUSS rot sein.
    """
    import keyword_edge_writer  # type: ignore[import]

    assert hasattr(keyword_edge_writer, "EXPECTED_PRECISE_EDGE_COUNT"), (
        "EXPECTED_PRECISE_EDGE_COUNT fehlt in keyword_edge_writer — AC-4 nicht erfuellt"
    )
    assert keyword_edge_writer.EXPECTED_PRECISE_EDGE_COUNT == 48095, (
        f"EXPECTED_PRECISE_EDGE_COUNT={keyword_edge_writer.EXPECTED_PRECISE_EDGE_COUNT!r}, "
        "erwartet 48095"
    )


# ---------------------------------------------------------------------------
# AC-3 — _build_keyword_index Docstring dokumentiert Truth-Scope-Invariante
# ---------------------------------------------------------------------------

def test_build_index_docstring_documents_truth_scope():
    """
    AC-3 RED: _build_keyword_index.__doc__ muss (case-insensitive) 'truth'
    UND ('only' ODER 'scope' ODER 'type') enthalten.

    Aktuelles Verhalten (IST): Docstring lautet
      'Scan vault_root for all atom .md files and build keyword -> [atom_info] index.'
    -> kein 'truth', kein 'scope'/'only'/'type' -> Test MUSS rot sein.
    """
    from keyword_edge_writer import _build_keyword_index  # type: ignore[import]

    doc = (_build_keyword_index.__doc__ or "").lower()

    assert "truth" in doc, (
        f"_build_keyword_index.__doc__ enthaelt 'truth' nicht. "
        f"Aktueller Docstring: {_build_keyword_index.__doc__!r}"
    )
    assert any(word in doc for word in ("only", "scope", "type")), (
        f"_build_keyword_index.__doc__ enthaelt weder 'only' noch 'scope' noch 'type'. "
        f"Aktueller Docstring: {_build_keyword_index.__doc__!r}"
    )
