"""
BL-455 RED-Tests: Spezifitaets-Filter fuer keyword_edge_writer.compute_keyword_edges

ZIEL-Signatur (fuer GREEN-Worker):
    compute_keyword_edges(
        src_atom: dict,
        keyword_index: dict[str, list[dict]],
        src_namespace: str,
        *,
        df_threshold: float = 0.05,   # keywords in > df_threshold * total_atoms Atomen = Stopword
        min_shared: int = 1,          # Mindest-Anzahl geteilter Nicht-Stopword-Keywords fuer Kante
        max_edges: int = 15,          # Per-Atom-Cap: max Kanten pro Quell-Atom
        total_atoms: int | None = None,  # Gesamt-Atom-Anzahl (fuer DF-Berechnung); falls None aus keyword_index ableiten
    ) -> list[dict]

Alle 5 Tests MUESSEN aktuell FEHLSCHLAGEN (aktuelle Impl kennt df_threshold/min_shared/max_edges nicht).
"""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

# Sicherstellen, dass das scripts-Verzeichnis im Pfad ist
_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from keyword_edge_writer import compute_keyword_edges


# ---------------------------------------------------------------------------
# Helper: erzeuge minimale Atom-Dicts und keyword_index
# ---------------------------------------------------------------------------

def _make_atom(local_id: str, keywords: list[str], bl_id: str = "BL-TEST") -> dict:
    return {"local_id": local_id, "keywords": keywords, "id": f"{bl_id}.{local_id}"}


def _make_index_entry(local_id: str, bl_id: str = "BL-TEST") -> dict:
    return {"local_id": local_id, "bl_id": bl_id, "path": f"/fake/{bl_id}/{local_id}.md"}


def _build_keyword_index(atoms: list[dict], bl_id: str = "BL-TEST") -> dict[str, list[dict]]:
    """Baut einen keyword_index aus einer Liste von Atom-Dicts."""
    index: dict[str, list[dict]] = {}
    for atom in atoms:
        for kw in atom.get("keywords") or []:
            index.setdefault(kw, []).append(_make_index_entry(atom["local_id"], bl_id))
    return index


# ---------------------------------------------------------------------------
# Test 1: Haeufiges Keyword (> df_threshold) -> KEINE Kante
# ---------------------------------------------------------------------------

def test_common_keyword_no_edge():
    """Stopword-Filter: ein keyword das in > 5% aller Atome vorkommt erzeugt keine Kante.

    Erwartete neue Signatur:
        compute_keyword_edges(src, index, ns, df_threshold=0.05, total_atoms=100)

    Setup: 100 Atome, 60 davon haben keyword "common" -> DF = 60/100 = 0.60 > 0.05.
    Atom src und atom_b teilen NUR "common". Erwartung: KEINE Kante.
    """
    n_total = 100
    n_common = 60  # 60% der Atome -> Stopword

    # Baue keyword_index: "common" in 60 Atomen
    common_atoms = [_make_atom(f"atom_{i}", ["common"]) for i in range(n_common)]
    index = _build_keyword_index(common_atoms)

    src = _make_atom("src_atom", ["common"])

    edges = compute_keyword_edges(
        src,
        index,
        "BL-TEST",
        df_threshold=0.05,
        total_atoms=n_total,
    )

    assert edges == [], (
        f"Stopword 'common' (DF=60%) sollte keine Kanten erzeugen, aber es wurden {len(edges)} Kanten gefunden"
    )


# ---------------------------------------------------------------------------
# Test 2: Seltenes Keyword (DF klein) -> Kante entsteht
# ---------------------------------------------------------------------------

def test_rare_shared_keyword_edge():
    """Seltenes keyword (DF=2/100=2%) teilen zwei Atome -> Kante muss entstehen.

    Erwartete neue Signatur:
        compute_keyword_edges(src, index, ns, df_threshold=0.05, total_atoms=100)
    """
    n_total = 100

    atom_b = _make_atom("atom_b", ["rare_xyz"])
    index = _build_keyword_index([atom_b])  # nur 1 Eintrag => DF = 1/100 (+ src selbst = 2/100)

    src = _make_atom("src_atom", ["rare_xyz"])

    edges = compute_keyword_edges(
        src,
        index,
        "BL-TEST",
        df_threshold=0.05,
        total_atoms=n_total,
    )

    dst_ids = [e["ziel"] for e in edges]
    assert any("atom_b" in ziel for ziel in dst_ids), (
        f"Seltenes keyword 'rare_xyz' (DF<=2%) sollte Kante zu atom_b erzeugen. Edges: {edges}"
    )


# ---------------------------------------------------------------------------
# Test 3: min_shared >= 2 — zwei nicht-ultra-haeufige Keywords -> Kante
# ---------------------------------------------------------------------------

def test_min_shared_two_generic():
    """Zwei Atome teilen 2 seltene Keywords mit min_shared=2 -> Kante entsteht.

    Erwartete neue Signatur:
        compute_keyword_edges(src, index, ns, df_threshold=0.05, min_shared=2, total_atoms=50)

    Kontroll-Fall: teilen nur 1 Keyword bei min_shared=2 -> KEINE Kante.
    """
    n_total = 50

    # atom_b teilt 2 keywords mit src
    atom_b = _make_atom("atom_b", ["kw_alpha", "kw_beta"])
    # atom_c teilt nur 1 keyword mit src
    atom_c = _make_atom("atom_c", ["kw_alpha"])

    atoms = [atom_b, atom_c]
    index = _build_keyword_index(atoms)

    src = _make_atom("src_atom", ["kw_alpha", "kw_beta"])

    # min_shared=2: beide keywords muessen geteilt werden
    edges = compute_keyword_edges(
        src,
        index,
        "BL-TEST",
        df_threshold=0.05,
        min_shared=2,
        total_atoms=n_total,
    )

    dst_ids = [e["ziel"] for e in edges]
    assert any("atom_b" in ziel for ziel in dst_ids), (
        f"atom_b teilt 2 keywords -> sollte Kante erhalten. Edges: {edges}"
    )
    assert not any("atom_c" in ziel for ziel in dst_ids), (
        f"atom_c teilt nur 1 keyword bei min_shared=2 -> sollte KEINE Kante erhalten. Edges: {edges}"
    )


# ---------------------------------------------------------------------------
# Test 4: Per-Atom-Cap (max_edges=15)
# ---------------------------------------------------------------------------

def test_per_atom_cap():
    """Ein Atom das 100 Kanten haette wird auf max_edges=15 gekappt (Top-K).

    Erwartete neue Signatur:
        compute_keyword_edges(src, index, ns, df_threshold=1.0, max_edges=15, total_atoms=200)

    df_threshold=1.0 deaktiviert den Stopword-Filter damit 100 Kanten entstehen koennen.
    Erwartet: len(edges) <= 15.
    """
    n_total = 200
    n_targets = 100

    # 100 Atome teilen ein seltenes keyword "rare_topic" mit src
    target_atoms = [_make_atom(f"tgt_{i}", ["rare_topic"]) for i in range(n_targets)]
    index = _build_keyword_index(target_atoms)

    src = _make_atom("src_atom", ["rare_topic"])

    edges = compute_keyword_edges(
        src,
        index,
        "BL-TEST",
        df_threshold=1.0,   # Stopword-Filter aus
        max_edges=15,
        total_atoms=n_total,
    )

    assert len(edges) <= 15, (
        f"Per-Atom-Cap max_edges=15 verletzt: {len(edges)} Kanten erzeugt (erwartet <= 15)"
    )
    assert len(edges) > 0, "Es sollten mindestens einige Kanten (bis zum Cap) entstehen"


# ---------------------------------------------------------------------------
# Test 5: Gesamt-Kantenzahl bei realistischer Keyword-Verteilung begrenzt
# ---------------------------------------------------------------------------

def test_total_edge_count_bounded():
    """Synthetischer Index mit realistischer Verteilung: Schnitt-Kanten pro Atom <= ~30.

    Setup:
    - 200 Atome
    - 5 haeufige keywords (je 80 Atome -> 40% DF -> Stopword bei df_threshold=0.05)
    - 50 seltene keywords (je 3 Atome -> 1.5% DF -> erlaubt)
    - jedes Atom hat 2 haeufige + 2 seltene keywords

    Erwartete neue Signatur:
        compute_keyword_edges(src, index, ns, df_threshold=0.05, max_edges=30, total_atoms=200)

    Erwartung: kein einzelnes Atom hat mehr als 30 Kanten.
    """
    n_total = 200
    common_kws = [f"common_{i}" for i in range(5)]   # 5 haeufige
    rare_kws = [f"rare_{i}" for i in range(50)]       # 50 seltene

    atoms: list[dict] = []

    # 200 Atome erzeugen
    for i in range(n_total):
        # 2 haeufige + 2 seltene keywords pro Atom
        kws = [
            common_kws[i % len(common_kws)],
            common_kws[(i + 1) % len(common_kws)],
            rare_kws[i % len(rare_kws)],
            rare_kws[(i + 3) % len(rare_kws)],
        ]
        atoms.append(_make_atom(f"atom_{i}", kws))

    index = _build_keyword_index(atoms)

    # Pruefe alle Atome
    max_seen = 0
    for atom in atoms:
        edges = compute_keyword_edges(
            atom,
            index,
            "BL-TEST",
            df_threshold=0.05,
            max_edges=30,
            total_atoms=n_total,
        )
        if len(edges) > max_seen:
            max_seen = len(edges)

    assert max_seen <= 30, (
        f"Kein Atom sollte mehr als 30 Kanten haben (max_edges=30). "
        f"Tatsaechliches Maximum: {max_seen}"
    )
    # Zusaetzlich: kein kompletter Hairball (alle Atome < 30 ist das Ziel)
    # Sanity: es sollten IRGENDWELCHE Kanten existieren (seltene keywords matchen)
    sample_edges = compute_keyword_edges(
        atoms[0], index, "BL-TEST",
        df_threshold=0.05, max_edges=30, total_atoms=n_total,
    )
    # atoms[0] teilt rare_kws mit anderen -> mind. 1 Kante erwartet
    # (rare_0 teilt atoms[0] mit atom_50, atom_100, atom_150 -> DF=4/200=2%)
    assert len(sample_edges) > 0, "Seltene keywords sollten mindestens einige Kanten erzeugen"
