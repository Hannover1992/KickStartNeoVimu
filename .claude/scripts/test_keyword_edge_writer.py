"""
test_keyword_edge_writer.py — RED-Worker BL-450 batch_1 Stage 1

Tests: K-KEW-1..9 (Kanten-Bau, Idempotenz-Guard, EDGE_RELS-Konformitaet, Dry-Run)
       A-AK4-1..3 (truth_gate_check.py UNMODIFIZIERT wiederverwendet — keine Kopplung)

Ziel-Modul: keyword_edge_writer.py (EXISTIERT NOCH NICHT -> alle Tests MUESSEN fehlschlagen)
Konvention: pytest, test_-Prefix (NC-6), Fixtures via tmp_path (Stufe 1 Laserpointer)

BL-450 Blueprint Kap. 6, Kap. 4.1, Kap. 4.3
"""
import hashlib
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Hilfsfunktionen fuer Fixtures
# ---------------------------------------------------------------------------

SCRIPTS_DIR = Path(__file__).parent


def _write_atom(path: Path, frontmatter_extra: str = "", body: str = "") -> Path:
    """Schreibt eine minimale Atom-.md Datei mit YAML-Frontmatter."""
    content = f"---\n{frontmatter_extra}\n---\n{body}\n"
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# K-KEW-1: compute_keyword_edges — 2 Atome mit 1 shared keyword -> 1 Kante
# ---------------------------------------------------------------------------

def test_kew1_compute_keyword_edges_shared_keyword_builds_one_edge():
    """K-KEW-1: compute_keyword_edges() bei 2 Atomen mit 1 shared-keyword liefert 1 Kante."""
    from keyword_edge_writer import compute_keyword_edges  # type: ignore[import]

    src_atom = {
        "id": "NS-A.atom-001",
        "local_id": "atom-001",
        "keywords": ["machine-learning"],
    }
    # keyword_index: keyword -> [{path, bl_id, local_id}]
    keyword_index = {
        "machine-learning": [
            {"path": "/vault/BL-123/truths/atom-002.md", "bl_id": "BL-123", "local_id": "atom-002"},
        ]
    }
    edges = compute_keyword_edges(src_atom, keyword_index, src_namespace="NS-A")

    assert len(edges) == 1
    assert edges[0]["rel"] == "relates_to"
    assert "atom-002" in edges[0]["ziel"]


# ---------------------------------------------------------------------------
# K-KEW-2: compute_keyword_edges — 0 shared keywords -> leere Liste
# ---------------------------------------------------------------------------

def test_kew2_compute_keyword_edges_no_shared_keywords_returns_empty():
    """K-KEW-2: compute_keyword_edges() bei 0 shared-keywords liefert []. """
    from keyword_edge_writer import compute_keyword_edges  # type: ignore[import]

    src_atom = {"id": "NS-A.atom-001", "local_id": "atom-001", "keywords": ["unrelated-topic"]}
    keyword_index = {"machine-learning": [{"path": "/x", "bl_id": "BL-1", "local_id": "other"}]}

    edges = compute_keyword_edges(src_atom, keyword_index, src_namespace="NS-A")

    assert edges == []


# ---------------------------------------------------------------------------
# K-KEW-3: is_edge_planted — True wenn Tripel bereits in edges[]
# ---------------------------------------------------------------------------

def test_kew3_is_edge_planted_returns_true_for_existing_tripel():
    """K-KEW-3: is_edge_planted() gibt True zurueck wenn {dst_id, rel} bereits vorhanden."""
    from keyword_edge_writer import is_edge_planted  # type: ignore[import]

    existing_edges = [
        {"rel": "relates_to", "ziel": "NS-B.atom-002"},
        {"rel": "depends_on", "ziel": "NS-C.atom-003"},
    ]

    assert is_edge_planted(existing_edges, dst_id="NS-B.atom-002", rel="relates_to") is True


# ---------------------------------------------------------------------------
# K-KEW-4: is_edge_planted — False fuer neues Tripel
# ---------------------------------------------------------------------------

def test_kew4_is_edge_planted_returns_false_for_new_tripel():
    """K-KEW-4: is_edge_planted() gibt False zurueck fuer neues {dst_id, rel}-Tripel."""
    from keyword_edge_writer import is_edge_planted  # type: ignore[import]

    existing_edges = [{"rel": "relates_to", "ziel": "NS-B.atom-002"}]

    # Gleiche dst aber anderes rel -> neues Tripel
    assert is_edge_planted(existing_edges, dst_id="NS-B.atom-002", rel="depends_on") is False
    # Komplett neues
    assert is_edge_planted(existing_edges, dst_id="NS-X.atom-999", rel="relates_to") is False


# ---------------------------------------------------------------------------
# K-KEW-5: write_edges_to_atom — 0 Kanten bei vollstaendig verkantetem Atom (Re-Run-Invariante)
# ---------------------------------------------------------------------------

def test_kew5_write_edges_to_atom_returns_zero_on_fully_planted_rerun(tmp_path):
    """K-KEW-5: write_edges_to_atom() schreibt 0 Kanten wenn alle Kanten bereits im Frontmatter."""
    from keyword_edge_writer import write_edges_to_atom  # type: ignore[import]

    # Atom-Datei mit bereits vorhandenen Kanten im edges[]-Frontmatter
    atom_file = tmp_path / "atom-already-planted.md"
    frontmatter = (
        "id: NS-A.atom-001\n"
        "local_id: atom-001\n"
        "edges:\n"
        "  - rel: relates_to\n"
        "    ziel: NS-B.atom-002\n"
    )
    _write_atom(atom_file, frontmatter_extra=frontmatter)

    # Gleiche Kanten nochmals schreiben wollen
    new_edges = [{"rel": "relates_to", "ziel": "NS-B.atom-002"}]
    written = write_edges_to_atom(atom_file, new_edges)

    assert written == 0, f"Re-Run-Invariante verletzt: {written} Kanten geschrieben statt 0"


# ---------------------------------------------------------------------------
# K-KEW-6: write_edges_to_atom — schreibt N Kanten bei leerem edges[]
# ---------------------------------------------------------------------------

def test_kew6_write_edges_to_atom_writes_n_edges_when_edges_empty(tmp_path):
    """K-KEW-6: write_edges_to_atom() schreibt neue Kanten in leeres Atom-edges[]."""
    from keyword_edge_writer import write_edges_to_atom  # type: ignore[import]

    atom_file = tmp_path / "atom-empty-edges.md"
    frontmatter = "id: NS-A.atom-001\nlocal_id: atom-001\nedges: []\n"
    _write_atom(atom_file, frontmatter_extra=frontmatter)

    new_edges = [
        {"rel": "relates_to", "ziel": "NS-B.atom-002"},
        {"rel": "relates_to", "ziel": "NS-C.atom-003"},
    ]
    written = write_edges_to_atom(atom_file, new_edges)

    assert written == 2


# ---------------------------------------------------------------------------
# K-KEW-7: Alle rel-Werte sind in truth_schema.EDGE_RELS (AK-2 Schema-Konformitaet)
# ---------------------------------------------------------------------------

def test_kew7_all_written_rels_conform_to_edge_rels(tmp_path):
    """K-KEW-7: keyword_edge_writer.py importiert EDGE_RELS aus truth_schema und
    compute_keyword_edges() gibt ausschliesslich EDGE_RELS-konforme rel-Werte zurueck."""
    from keyword_edge_writer import compute_keyword_edges  # type: ignore[import]
    from truth_schema import EDGE_RELS  # type: ignore[import]

    src_atom = {
        "id": "NS-A.atom-001",
        "local_id": "atom-001",
        "keywords": ["distributed-systems", "consensus"],
    }
    keyword_index = {
        "distributed-systems": [{"path": "/v/BL-1/truths/a.md", "bl_id": "BL-1", "local_id": "a"}],
        "consensus": [{"path": "/v/BL-2/truths/b.md", "bl_id": "BL-2", "local_id": "b"}],
    }

    edges = compute_keyword_edges(src_atom, keyword_index, src_namespace="NS-A")

    for edge in edges:
        assert edge["rel"] in EDGE_RELS, (
            f"rel={edge['rel']!r} nicht in EDGE_RELS={sorted(EDGE_RELS)}"
        )


# ---------------------------------------------------------------------------
# K-KEW-8: main() mit --vault missing_path -> exit code 2
# ---------------------------------------------------------------------------

def test_kew8_main_with_missing_vault_exits_2(tmp_path):
    """K-KEW-8: main() gibt exit-Code 2 zurueck wenn --vault auf nicht-existierenden Pfad zeigt."""
    from keyword_edge_writer import main  # type: ignore[import]

    missing = str(tmp_path / "no-such-vault")
    result = main(["--vault", missing])

    assert result == 2, f"Erwartet exit 2 fuer fehlendem Vault-Pfad, bekam {result}"


# ---------------------------------------------------------------------------
# K-KEW-9: main() mit --dry-run -> keine Datei geaendert (Mtime unveraendert)
# ---------------------------------------------------------------------------

def test_kew9_dry_run_writes_no_files(tmp_path):
    """K-KEW-9: main() mit --dry-run schreibt keine Datei (Mtime aller Atom-Dateien unveraendert)."""
    from keyword_edge_writer import main  # type: ignore[import]

    # Minimale Vault-Struktur: 1 Atom mit keywords
    atom_dir = tmp_path / "BL-TEST" / "2_Model" / "truths"
    atom_dir.mkdir(parents=True)
    atom_file = atom_dir / "atom-001.md"
    frontmatter = (
        "id: NS-TEST.atom-001\n"
        "local_id: atom-001\n"
        "keywords:\n"
        "  - shared-concept\n"
        "edges: []\n"
    )
    _write_atom(atom_file, frontmatter_extra=frontmatter)

    # Mtime vorher merken
    mtime_before = atom_file.stat().st_mtime

    main(["--vault", str(tmp_path), "--dry-run"])

    mtime_after = atom_file.stat().st_mtime
    assert mtime_before == mtime_after, (
        "Dry-Run hat Datei-Mtime veraendert — Datei wurde trotz --dry-run geschrieben"
    )


# ---------------------------------------------------------------------------
# A-AK4-1: truth_gate_check.py existiert unter .claude/scripts/
# ---------------------------------------------------------------------------

def test_ak4_1_truth_gate_check_exists():
    """A-AK4-1: truth_gate_check.py muss unter .claude/scripts/ existieren (AK-4 Reuse-Verifikation)."""
    gate_check = SCRIPTS_DIR / "truth_gate_check.py"
    assert gate_check.exists(), (
        f"truth_gate_check.py fehlt unter {SCRIPTS_DIR} — AK-4 Reuse-Kontrakt verletzt"
    )


# ---------------------------------------------------------------------------
# A-AK4-2: keyword_edge_writer.py importiert NICHT aus truth_gate_check
# ---------------------------------------------------------------------------

def test_ak4_2_keyword_edge_writer_does_not_import_truth_gate_check():
    """A-AK4-2: keyword_edge_writer.py darf truth_gate_check NICHT importieren (AK-4, kein Overlap)."""
    kew_path = SCRIPTS_DIR / "keyword_edge_writer.py"
    if not kew_path.exists():
        pytest.skip("keyword_edge_writer.py existiert noch nicht (GREEN-Worker-Aufgabe)")
    content = kew_path.read_text(encoding="utf-8")
    assert "truth_gate_check" not in content, (
        "keyword_edge_writer.py importiert truth_gate_check — AK-4 Kopplung-Verbot verletzt"
    )


# ---------------------------------------------------------------------------
# A-AK4-3: wikilink_materializer.py importiert NICHT aus truth_gate_check
# ---------------------------------------------------------------------------

def test_ak4_3_wikilink_materializer_does_not_import_truth_gate_check():
    """A-AK4-3: wikilink_materializer.py darf truth_gate_check NICHT importieren (AK-4, kein Overlap)."""
    wm_path = SCRIPTS_DIR / "wikilink_materializer.py"
    if not wm_path.exists():
        pytest.skip("wikilink_materializer.py existiert noch nicht (GREEN-Worker-Aufgabe)")
    content = wm_path.read_text(encoding="utf-8")
    assert "truth_gate_check" not in content, (
        "wikilink_materializer.py importiert truth_gate_check — AK-4 Kopplung-Verbot verletzt"
    )
