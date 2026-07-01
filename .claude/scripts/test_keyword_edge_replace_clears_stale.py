"""
test_keyword_edge_replace_clears_stale.py — RED-Worker BL-451 AC-2a Folge-Fix

Tests: replace-mode MUSS write_edges_to_atom auch bei leeren edges aufrufen,
       damit stale relates_to-Kanten gedroppt werden.

BUG: main()-Loop Zeile 330 `if not edges: continue` skippt das Atom komplett
     im --replace-Modus -> stale relates_to bleibt stehen.

RED-Erwartung:
  - test_replace_clears_stale_relates_to_when_no_new_matches  -> FAIL
  - test_replace_preserves_other_rel_when_no_new_matches      -> FAIL
  - test_no_replace_leaves_stale_untouched                    -> PASS (Regression)
"""
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS_DIR = Path(__file__).parent
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def _write_atom(path: Path, frontmatter: dict, body: str = "") -> Path:
    """Write a minimal truth atom .md with YAML frontmatter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fm_text = yaml.dump(frontmatter, allow_unicode=True, default_flow_style=False, sort_keys=False)
    content = f"---\n{fm_text}---\n{body}\n"
    path.write_text(content, encoding="utf-8")
    return path


def _read_edges(path: Path) -> list:
    """Read edges from atom frontmatter, return [] if none."""
    content = path.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return []
    end = content.find("\n---", 3)
    if end == -1:
        return []
    fm_text = content[4:end]
    fm = yaml.safe_load(fm_text) or {}
    return fm.get("edges") or []


# ---------------------------------------------------------------------------
# Test 1: --replace MUSS stale relates_to droppen, auch wenn keine neuen Kanten
# ---------------------------------------------------------------------------

def test_replace_clears_stale_relates_to_when_no_new_matches(tmp_path):
    """
    BUG-Nachweis: Ein Atom mit keywords die KEINE anderen Atome matchen
    (0 Treffer nach Stopword/min_shared-Filter) und einer vorbestehenden
    stale relates_to-Kante -> main(--replace) muss die stale Kante droppen.

    RED: aktuell wird das Atom geskippt (if not edges: continue),
         write_edges_to_atom wird NIE aufgerufen, stale Kante bleibt.
    """
    from keyword_edge_writer import main  # type: ignore[import]

    # Vault-Struktur: BL-X/Model/truths/W1.md
    atom_path = tmp_path / "BL-X" / "Model" / "truths" / "W1.md"

    # keywords: einzigartiges Wort das kein anderes Atom teilt -> 0 Treffer
    # (nur 1 Atom im Vault -> DF = 1.0/1 = 1.0 > threshold 0.05 -> stopword,
    #  ODER kein zweites Atom mit dem selben keyword -> 0 shared partners)
    frontmatter = {
        "id": "NS.W1",
        "local_id": "W1",
        "keywords": ["zzz-unique-nomatch-keyword-xq9z"],
        "edges": [
            {"rel": "relates_to", "ziel": "Backlog.W9"},
        ],
    }
    _write_atom(atom_path, frontmatter)

    # Run main with --replace
    result = main(["--vault", str(tmp_path), "--replace"])
    assert result == 0

    # SOLL: stale relates_to-Kante ist WEG
    edges = _read_edges(atom_path)
    relates_to_edges = [e for e in edges if isinstance(e, dict) and e.get("rel") == "relates_to"]
    assert relates_to_edges == [], (
        f"BUG: stale relates_to-Kante wurde NICHT gedroppt. "
        f"Alle edges: {edges}"
    )


# ---------------------------------------------------------------------------
# Test 2: --replace droppt nur relates_to, andere rels bleiben erhalten
# ---------------------------------------------------------------------------

def test_replace_preserves_other_rel_when_no_new_matches(tmp_path):
    """
    Gleiches Setup wie Test 1, aber das Atom hat ZUSAETZLICH eine depends_on-Kante.
    Nach main(--replace): depends_on bleibt, stale relates_to ist WEG.

    RED: aktuell wird das Atom geskippt -> BEIDE Kanten bleiben stehen
         (stale relates_to bleibt, obwohl sie haette gedroppt werden sollen).
    """
    from keyword_edge_writer import main  # type: ignore[import]

    atom_path = tmp_path / "BL-X" / "Model" / "truths" / "W1.md"

    frontmatter = {
        "id": "NS.W1",
        "local_id": "W1",
        "keywords": ["zzz-unique-nomatch-keyword-xq9z"],
        "edges": [
            {"rel": "relates_to", "ziel": "Backlog.W9"},   # stale -> MUSS WEG
            {"rel": "depends_on", "ziel": "X.W2"},          # andere rel -> MUSS BLEIBEN
        ],
    }
    _write_atom(atom_path, frontmatter)

    result = main(["--vault", str(tmp_path), "--replace"])
    assert result == 0

    edges = _read_edges(atom_path)

    # stale relates_to muss weg sein
    relates_to_edges = [e for e in edges if isinstance(e, dict) and e.get("rel") == "relates_to"]
    assert relates_to_edges == [], (
        f"BUG: stale relates_to wurde NICHT gedroppt. Alle edges: {edges}"
    )

    # depends_on muss erhalten sein
    depends_on_edges = [e for e in edges if isinstance(e, dict) and e.get("rel") == "depends_on"]
    assert len(depends_on_edges) == 1, (
        f"depends_on-Kante sollte erhalten bleiben, aber edges={edges}"
    )
    assert depends_on_edges[0]["ziel"] == "X.W2"


# ---------------------------------------------------------------------------
# Test 3 (Regression): OHNE --replace bleibt stale Kante unveraendert
# ---------------------------------------------------------------------------

def test_no_replace_leaves_stale_untouched(tmp_path):
    """
    Regression: OHNE --replace darf die stale relates_to-Kante NICHT gedroppt werden.
    Das Alt-Verhalten (if not edges: continue) ist in diesem Modus KORREKT.

    PASS schon jetzt (kein --replace -> kein Bug-Pfad), dient als Sicherheitsnetz
    damit GREEN den Nicht-replace-Pfad nicht kaputtmacht.
    """
    from keyword_edge_writer import main  # type: ignore[import]

    atom_path = tmp_path / "BL-X" / "Model" / "truths" / "W1.md"

    frontmatter = {
        "id": "NS.W1",
        "local_id": "W1",
        "keywords": ["zzz-unique-nomatch-keyword-xq9z"],
        "edges": [
            {"rel": "relates_to", "ziel": "Backlog.W9"},
        ],
    }
    _write_atom(atom_path, frontmatter)

    # Run WITHOUT --replace
    result = main(["--vault", str(tmp_path)])
    assert result == 0

    edges = _read_edges(atom_path)
    relates_to_edges = [e for e in edges if isinstance(e, dict) and e.get("rel") == "relates_to"]
    assert len(relates_to_edges) == 1, (
        f"REGRESSION: stale relates_to sollte ohne --replace unveraendert bleiben, "
        f"aber edges={edges}"
    )
    assert relates_to_edges[0]["ziel"] == "Backlog.W9"
