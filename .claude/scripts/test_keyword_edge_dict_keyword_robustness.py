"""
test_keyword_edge_dict_keyword_robustness.py — RED-Tests fuer BL-487 F-1

Reproduzieren den Live-Crash: keywords-Liste mit Dict-Eintraegen (corrupted
referenced_by-Eintraege in keywords gemergt) fuehrt zu
  TypeError: unhashable type: 'dict'
in compute_keyword_edges; _build_keyword_index indiziert Dicts als stringified
Keys statt zu skippen und zu warnen.

AKTUELL RED:
  - T1/T3/T4: TypeError in compute_keyword_edges (keyword_index.get(kw) / df_count[kw])
  - T2: kein Crash, aber stringified-Dict-Key landet im Index (AssertionError)

GREEN-Worker-Aufgabe (NICHT HIER): keyword_edge_writer.py haerten:
  1. Skip non-string keywords (die kein normalisierbares text-Feld haben)
  2. Normalize {"text": ...} / {"term": ...} / {"keyword": ...} / {"value": ...} / {"name": ...}
  3. WARNING via logging.getLogger(__name__) fuer geskippte Keywords (nie still)

BL-487 AC-1..4
"""
from __future__ import annotations

import logging
import sys
import textwrap
from pathlib import Path

import pytest

# Sicherstellen dass .claude/scripts/ im sys.path ist (analog test_keyword_edge_robustness.py)
sys.path.insert(0, str(Path(__file__).parent))

from keyword_edge_writer import compute_keyword_edges, _build_keyword_index  # type: ignore[import]


# ---------------------------------------------------------------------------
# BL-487 F-1-T1: compute_keyword_edges — Dict-Eintrag in keywords crasht nicht
# ---------------------------------------------------------------------------

def test_compute_keyword_edges_skips_dict_keywords():
    """BL-487 F-1-T1: compute_keyword_edges() darf nicht raisen wenn keywords Dict-Eintraege enthaelt.

    Live-Crash-Reproduktion:
      src_atom.keywords = ["alpha", "beta", {"by": "X.W1", "kind": "truth_edge"}]
      -> keyword_index.get({"by":...}) -> TypeError: unhashable type: 'dict'

    Nach Fix: Dict-Eintrag uebersprungen; Kanten aus "alpha" und "beta" korrekt gebaut.

    AKTUELL RED: TypeError: unhashable type: 'dict' bei keyword_index.get(kw).
    """
    src_atom = {
        "id": "NS-TEST.atom-src",
        "local_id": "atom-src",
        "keywords": ["alpha", "beta", {"by": "X.W1", "kind": "truth_edge"}],
    }
    keyword_index: dict[str, list[dict]] = {
        "alpha": [
            {
                "path": "/vault/BL-1/truths/atom-alpha.md",
                "bl_id": "BL-1",
                "local_id": "atom-alpha",
                "atom_id": "BL-1.atom-alpha",
            }
        ],
        "beta": [
            {
                "path": "/vault/BL-2/truths/atom-beta.md",
                "bl_id": "BL-2",
                "local_id": "atom-beta",
                "atom_id": "BL-2.atom-beta",
            }
        ],
    }

    # AKTUELL RED: TypeError: unhashable type: 'dict' — Dict-Keyword crasht keyword_index.get(kw)
    edges = compute_keyword_edges(src_atom, keyword_index, src_namespace="NS-TEST")

    # Nach Fix: Kanten aus string-Keywords entstehen; Dict-Eintrag ignoriert
    assert isinstance(edges, list), f"Erwarte list, bekam {type(edges)}"
    ziels = {e["ziel"] for e in edges}
    assert any("atom-alpha" in z or "BL-1" in z for z in ziels), (
        f"Edge zu alpha-Atom (BL-1.atom-alpha) erwartet. Tatsaechliche ziels: {ziels}"
    )
    assert any("atom-beta" in z or "BL-2" in z for z in ziels), (
        f"Edge zu beta-Atom (BL-2.atom-beta) erwartet. Tatsaechliche ziels: {ziels}"
    )


# ---------------------------------------------------------------------------
# BL-487 F-1-T2: _build_keyword_index — Dict-Eintrag wird nicht als String-Key indiziert
# ---------------------------------------------------------------------------

def test_build_keyword_index_skips_dict_keywords(tmp_path: Path):
    """BL-487 F-1-T2: _build_keyword_index() soll Dict-Keywords ueberspringen statt stringifizieren.

    Aktuell: _build_keyword_index verwendet str(kw) fuer alle Keywords; ein Dict-Keyword
    landet als "{'by': 'X.W1', 'kind': 'truth_edge'}" im Index statt geskippt zu werden.

    YAML-Atom:
      keywords:
        - valid_kw
        - by: X.W1
          kind: truth_edge   <- YAML-Dict-Eintrag

    Nach Fix: nur "valid_kw" im Index; stringified-Dict-Key abwesend; WARNING emittiert.

    AKTUELL RED: kein Crash, aber stringified Dict-Key ist im Index -> AssertionError.
    """
    atom_dir = tmp_path / "BL-TEST" / "truths"
    atom_dir.mkdir(parents=True)
    atom_file = atom_dir / "atom-dict-kw.md"
    atom_content = textwrap.dedent("""\
        ---
        id: BL-TEST.atom-dict-kw
        local_id: atom-dict-kw
        type: truth
        keywords:
          - valid_kw
          - by: X.W1
            kind: truth_edge
        ---
        Body.
    """)
    atom_file.write_text(atom_content, encoding="utf-8")

    # AKTUELL RED: kein Crash, aber stringified Dict ist im Index
    index = _build_keyword_index(tmp_path)

    assert "valid_kw" in index, (
        f"'valid_kw' muss im Index stehen. Schluessel im Index: {list(index.keys())}"
    )

    # Stringified Dict-Key darf NICHT im Index stehen
    # (PyYAML laedt 'by: X.W1 / kind: truth_edge' als {'by': 'X.W1', 'kind': 'truth_edge'})
    stringified = str({"by": "X.W1", "kind": "truth_edge"})
    assert stringified not in index, (
        f"Stringified Dict-Key {stringified!r} ist im Index — "
        "Dict-Keywords muessen geskippt werden, nicht als str() indiziert"
    )


# ---------------------------------------------------------------------------
# BL-487 F-1-T3: Geskippte Dict-Keywords werden via logging.WARNING gemeldet
# ---------------------------------------------------------------------------

def test_dict_keyword_skip_is_logged(caplog):
    """BL-487 F-1-T3: Geskippte Dict-Keywords muessen via logging.WARNING gemeldet werden.

    LOUD-REPORTING: nie still droppen. Nach Fix emittiert keyword_edge_writer
    via logging.getLogger(__name__) ein WARNING das den nicht-string/unnormierbaren
    Keyword benennt.

    AKTUELL RED: Funktion crasht mit TypeError: unhashable type: 'dict' bevor
    ein Log moeglich ist -> Test schlaegt mit TypeError fehl (RED fuer richtigen Grund).
    """
    src_atom = {
        "id": "NS-LOG.atom-src",
        "local_id": "atom-src",
        "keywords": ["good_kw", {"by": "X.W1", "kind": "truth_edge"}],
    }
    keyword_index: dict[str, list[dict]] = {
        "good_kw": [
            {
                "path": "/vault/BL-1/truths/a.md",
                "bl_id": "BL-1",
                "local_id": "a",
                "atom_id": "BL-1.a",
            }
        ]
    }

    with caplog.at_level(logging.WARNING, logger="keyword_edge_writer"):
        # AKTUELL RED: TypeError crasht hier, kein Log entsteht
        edges = compute_keyword_edges(src_atom, keyword_index, src_namespace="NS-LOG")

    assert isinstance(edges, list)

    # Nach Fix: mindestens 1 WARNING-Record im caplog
    assert any(
        record.levelno >= logging.WARNING
        for record in caplog.records
    ), (
        "Kein WARNING-Log gefunden — geskippte non-string Keywords muessen via "
        "logging.WARNING gemeldet werden (BL-487 AC-4 LOUD-REPORTING)"
    )

    # Der WARNING-Text muss auf das Skipping hinweisen
    warning_texts = " ".join(
        record.message
        for record in caplog.records
        if record.levelno >= logging.WARNING
    )
    assert any(
        term in warning_texts.lower()
        for term in ("skip", "non-string", "dict", "keyword", "unhashable")
    ), f"WARNING-Text vermittelt kein Skipping-Signal: {warning_texts!r}"


# ---------------------------------------------------------------------------
# BL-487 F-1-T4 (optional): Dict-Keyword mit 'text'-Feld wird normalisiert
# ---------------------------------------------------------------------------

def test_dict_keyword_with_text_field_normalized():
    """BL-487 F-1-T4: {"text": "gamma"} soll zu "gamma" normalisiert und als Keyword verwendet werden.

    Dicts mit Feldern text/term/keyword/value/name haben verwendbaren Text -> normalisieren.
    Dicts ohne solches Feld ({by, kind}) -> skippen + warnen.

    Dieser Test pinnt den Normalize-Pfad.

    AKTUELL RED: TypeError: unhashable type: 'dict' bei keyword_index.get({"text": "gamma"})
    bevor jede Normalisierungs-Logik greifen koennte.
    """
    src_atom = {
        "id": "NS-NORM.atom-src",
        "local_id": "atom-src",
        "keywords": ["alpha", {"text": "gamma"}],
    }
    keyword_index: dict[str, list[dict]] = {
        "alpha": [
            {
                "path": "/vault/BL-1/truths/a.md",
                "bl_id": "BL-1",
                "local_id": "a",
                "atom_id": "BL-1.a",
            }
        ],
        "gamma": [
            {
                "path": "/vault/BL-2/truths/g.md",
                "bl_id": "BL-2",
                "local_id": "g",
                "atom_id": "BL-2.g",
            }
        ],
    }

    # AKTUELL RED: TypeError: unhashable type: 'dict' bei {"text": "gamma"}
    edges = compute_keyword_edges(src_atom, keyword_index, src_namespace="NS-NORM")

    assert isinstance(edges, list)

    # Nach Fix: {"text": "gamma"} -> "gamma" normalisiert -> Kante zu BL-2.g
    ziels = {e["ziel"] for e in edges}
    assert any("g" in z or "gamma" in z or "BL-2" in z for z in ziels), (
        f"Normalisierter gamma-Keyword soll Kante zu BL-2.g erzeugen. "
        f"Tatsaechliche ziels: {ziels}"
    )
