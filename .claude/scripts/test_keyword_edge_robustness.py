"""
test_keyword_edge_robustness.py — RED-Tests fuer BL-450 heterogene existing_edges

Reproduzieren den Live-Crash: edges: Frontmatter-Felder mit Strings (nicht Dicts)
fuehren in is_edge_planted + write_edges_to_atom zu AttributeError.

AKTUELL RED: diese Tests muessen ALLE scheitern (AttributeError) bis der Fix
in keyword_edge_writer.py implementiert ist.

Konvention: INV-BUILD-GRAIN RED != GREEN — kein Fix hier, nur Crash-Nachweis.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

# Import des Moduls unter Test (relativ zum scripts-Verzeichnis)
import sys

sys.path.insert(0, str(Path(__file__).parent))

from keyword_edge_writer import is_edge_planted, write_edges_to_atom


# ---------------------------------------------------------------------------
# Test 1: is_edge_planted mit reiner String-Kanten-Liste
# ---------------------------------------------------------------------------


def test_is_edge_planted_string_edges_no_crash():
    """existing_edges als String-Liste darf NICHT crashen.

    Echte Vault-Atome liefern manchmal edges: ["AtomX", "AtomY"] (YAML-String-Liste).
    is_edge_planted ruft aktuell edge.get("ziel") -> AttributeError auf Strings.

    Erwartetes Verhalten nach Fix:
      - Strings werden ignoriert (kein dict -> kein Match) -> return False
      - kein AttributeError
    """
    existing_string_edges = ["AtomX", "AtomY"]

    # AKTUELL RED: AttributeError: 'str' object has no attribute 'get'
    result = is_edge_planted(existing_string_edges, "AtomZ", "relates_to")
    assert result is False, "Nicht-existente Kante muss False liefern"


def test_is_edge_planted_string_equals_dst():
    """String in existing_edges der der dst_id entspricht.

    Bei reiner String-Liste koennte man argumentieren, ob ein String-Match
    (ohne rel-Check) als 'planted' gilt. Nach Fix: String-Eintrag, der dem
    dst_id entspricht, gilt als planted (True) — rel unbekannt, safety-first.
    Falls das Design anders entschieden wird, kann dieser Test angepasst werden.

    Aktuell RED wegen AttributeError bevor ein Match-Urteil moeglich ist.
    """
    existing_edges = ["AtomX"]

    # AKTUELL RED: AttributeError noch vor dem assert
    result = is_edge_planted(existing_edges, "AtomX", "relates_to")
    # Nach Fix: True (String-Match auf dst_id) ODER False (nur Dict-Matches) —
    # beides waere ein Fortschritt; der Test prueft nur keinen Crash + bool-Rueckgabe.
    assert isinstance(result, bool), f"Rueckgabe muss bool sein, nicht Crash. Bekam: {result!r}"


# ---------------------------------------------------------------------------
# Test 2: is_edge_planted mit gemischter Liste (Strings + Dicts)
# ---------------------------------------------------------------------------


def test_is_edge_planted_mixed_edges_no_crash():
    """Gemischte existing_edges (Strings + Dicts) — kein Crash, korrekte Treffer.

    AKTUELL RED: AttributeError beim ersten String-Element.
    Nach Fix:
      - "AtomX" (String) kein Match auf {"ziel":"AtomY","rel":"relates_to"}
      - {"ziel":"AtomY","rel":"relates_to"} (Dict) matched korrekt
    """
    existing_edges = ["AtomX", {"ziel": "AtomY", "rel": "relates_to"}]

    # AKTUELL RED: AttributeError auf "AtomX".get("ziel")
    result_miss = is_edge_planted(existing_edges, "AtomZ", "relates_to")
    assert result_miss is False, "AtomZ ist nicht in edges -> False erwartet"

    result_hit = is_edge_planted(existing_edges, "AtomY", "relates_to")
    assert result_hit is True, "AtomY/relates_to ist als Dict vorhanden -> True erwartet"


def test_is_edge_planted_mixed_string_before_matching_dict():
    """String-Element kommt VOR dem matchenden Dict — kein Abbruch nach String.

    Sicherstellt dass der Iterator nach einem String-Element korrekt weiterlaueft.
    AKTUELL RED: AttributeError beim String-Element, Dict-Element wird nie erreicht.
    """
    existing_edges = ["noise_string", {"ziel": "TargetAtom", "rel": "relates_to"}]

    # AKTUELL RED: bricht bei "noise_string" ab
    result = is_edge_planted(existing_edges, "TargetAtom", "relates_to")
    assert result is True, "TargetAtom/relates_to als Dict nach String-Rauschen -> True erwartet"


# ---------------------------------------------------------------------------
# Test 3: write_edges_to_atom mit String-existing-edges im Frontmatter
# ---------------------------------------------------------------------------


def test_write_edges_to_atom_string_existing(tmp_path: Path):
    """Atom-Datei mit edges: ["[[AtomA]]"] als String-Liste.

    write_edges_to_atom laedt existing_edges via fm.get("edges") -> ruft
    is_edge_planted auf -> AttributeError auf String-Elementen.

    Erwartetes Verhalten nach Fix:
      - kein Crash
      - neue Dict-Kante wird gemerged
      - String-Elemente aus dem Original-Frontmatter bleiben erhalten (non-destruktiv)
    """
    atom_content = textwrap.dedent("""\
        ---
        id: BL-TEST.edge-robustness
        local_id: edge-robustness
        edges:
          - "[[AtomA]]"
          - "[[AtomB]]"
        ---
        Body-Text des Atoms.
    """)

    atom_file = tmp_path / "edge_robustness.md"
    atom_file.write_text(atom_content, encoding="utf-8")

    new_edges = [{"rel": "relates_to", "ziel": "BL-NEW.some-atom"}]

    # AKTUELL RED: AttributeError in is_edge_planted("[[AtomA]]".get(...))
    written = write_edges_to_atom(atom_file, new_edges)

    assert written == 1, f"Genau 1 neue Kante soll geschrieben werden, bekam: {written}"

    # Pruefe dass Datei veraendert wurde und neue Kante enthaelt
    result_text = atom_file.read_text(encoding="utf-8")
    assert "BL-NEW.some-atom" in result_text, "Neue Kante muss in Datei stehen"

    # Non-destruktiv: Original-Strings sollen erhalten bleiben
    assert "AtomA" in result_text or "[[AtomA]]" in result_text, (
        "Original String-Kante AtomA soll erhalten bleiben (non-destruktiv)"
    )


def test_write_edges_to_atom_mixed_existing(tmp_path: Path):
    """Atom mit gemischten edges (String + Dict) — kein Crash, idempotenter Merge.

    Nach Fix: die Dict-Kante schon vorhanden -> wird nicht dupliziert.
    String-Kanten werden nicht als Duplikate fehlklassifiziert.
    AKTUELL RED: AttributeError beim ersten String-Element.
    """
    atom_content = textwrap.dedent("""\
        ---
        id: BL-TEST.mixed-edges
        local_id: mixed-edges
        edges:
          - "[[AtomLegacy]]"
          - rel: relates_to
            ziel: BL-EXISTING.atom
        ---
        Body.
    """)

    atom_file = tmp_path / "mixed_edges.md"
    atom_file.write_text(atom_content, encoding="utf-8")

    # BL-EXISTING.atom ist schon als Dict-Kante drin -> soll NICHT nochmal geschrieben werden
    new_edges = [
        {"rel": "relates_to", "ziel": "BL-EXISTING.atom"},
        {"rel": "relates_to", "ziel": "BL-BRAND-NEW.atom"},
    ]

    # AKTUELL RED: AttributeError
    written = write_edges_to_atom(atom_file, new_edges)

    assert written == 1, (
        f"Nur BL-BRAND-NEW.atom ist neu -> 1 Kante erwartet, bekam: {written}"
    )

    result_text = atom_file.read_text(encoding="utf-8")
    assert "BL-BRAND-NEW.atom" in result_text, "Neue Kante muss in Datei stehen"
