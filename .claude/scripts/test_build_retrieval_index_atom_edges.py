"""
test_build_retrieval_index_atom_edges.py — BL-242 / atom-edge-gap / RED-Suite

Pinnt zwei strukturelle Luecken die zusammen dazu fuehren, dass truth-Atom-Edges
NIEMALS in build_index["edge_index"] landen:

  Luecke 1 (walk-Luecke): _walk_vault_nodes (~Z.234) baut den Knoten-Dict OHNE
  "edges"-Key. build_edge_index liest node.get("edges") -> None -> kein Eintrag.

  Luecke 2 (schema-Luecke): build_edge_index (~Z.55) liest e.get("target") +
  e.get("edge_type"). Truth-Atom-Edges tragen aber "ziel"/"rel"
  (z.B. {"rel": "relates_to", "ziel": "NS.B1"}) -> target==None, edge_type==None.

Netto-Effekt: ein Truth-Atom mit edges:[{rel:..., ziel:...}] -> edge_index leer.

Tests:
  E1 — E2E: build_index([tmp_path]) mit echtem type:truth-.md -> edge_index NON-empty
             + target=="NS.B1" + edge_type=="relates_to".  [RED: empty]
  E2 — Unit: build_edge_index mit atom-Schema {rel, ziel} -> target=="NS.B1".  [RED: None]
  E3 — Back-compat: build_edge_index mit BL-Schema {target, edge_type} bleibt korrekt.  [GREEN]

Stage-3 (realer tmp-Vault-Korpus fuer E1): tmp-Verzeichnis mit echten .md-Dateien.
Stage-1 (reine Funktions-Fixtures fuer E2/E3): kein File-IO.

RED-Beweis: E1/E2 schlagen fehl weil edge_index leer / target==None.
E3 soll SOFORT gruen sein (Back-compat-Guard).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import build_retrieval_index  # noqa: E402


# ---------------------------------------------------------------------------
# Hilfsfunktion: schreibt ein minimales type:truth-.md mit edges-Block
# Stil: keywords als inline/flow (wie _write_truth in test_build_retrieval_index_atoms.py)
# Edges als YAML-Block-Sequenz (einziges sinnvolle Format fuer Listen von Dicts).
# ---------------------------------------------------------------------------

def _write_truth_with_edges(dirpath, filename, atom_id, keywords=None, edges=None):
    """Schreibt eine type:truth .md-Datei mit optionalem edges-Block in dirpath.

    keywords: Liste von Strings -> inline YAML: keywords: ["k1", "k2"]
    edges: Liste von Dicts mit "rel"/"ziel" -> YAML-Block-Sequenz.
    """
    kw_yaml = ""
    if keywords is not None:
        kw_str = ", ".join(f'"{k}"' for k in keywords)
        kw_yaml = f"keywords: [{kw_str}]\n"

    edges_yaml = ""
    if edges:
        edges_yaml = "edges:\n"
        for edge in edges:
            # Atom-Schema: rel + ziel
            rel = edge.get("rel", "")
            ziel = edge.get("ziel", "")
            edges_yaml += f"- rel: {rel}\n"
            edges_yaml += f"  ziel: {ziel}\n"

    content = (
        "---\n"
        "type: truth\n"
        f"id: {atom_id}\n"
        "text: Eine Wahrheit ueber das System.\n"
        "typ: FESTSTELLUNG\n"
        "herkunft: INTERN\n"
        "status: OFFEN\n"
        "truth_grade: vault_hypothesis\n"
        f"{kw_yaml}"
        f"{edges_yaml}"
        "---\n"
        f"# {atom_id}\n\n"
        "Inhalt der Wahrheit.\n"
    )
    fpath = os.path.join(dirpath, filename)
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(content)
    return fpath


# ---------------------------------------------------------------------------
# E1 — End-to-End: build_index captures atom ziel/rel edges
# ---------------------------------------------------------------------------

def test_e1_build_index_captures_atom_edges_end_to_end(tmp_path):
    """
    E1 (E2E Stage-3): build_index([tmp_path]) mit einem type:truth-.md das
    edges:[{rel: relates_to, ziel: NS.B1}] traegt -> built["edge_index"] ist
    NON-empty und enthaelt target=="NS.B1" (+ edge_type=="relates_to").

    RED jetzt weil zwei Luecken zusammenwirken:
      Luecke 1 (walk): _walk_vault_nodes baut Knoten-Dict OHNE "edges"-Key ->
        build_edge_index sieht keine Edges, Index bleibt leer.
      Luecke 2 (schema): build_edge_index liest e.get("target") -> None
        (Atom-Edges tragen "ziel", nicht "target").

    GREEN wenn: build_index leitet fm["edges"] in den Knoten-Dict durch UND
    build_edge_index akzeptiert "ziel"/"rel" als Alternative zu "target"/"edge_type".
    """
    _write_truth_with_edges(
        str(tmp_path),
        "atom_ns_a1.md",
        atom_id="NS.A1",
        keywords=["system", "edge"],
        edges=[{"rel": "relates_to", "ziel": "NS.B1"}],
    )

    built = build_retrieval_index.build_index([str(tmp_path)])

    edge_index = built["edge_index"]

    # Luecke 1 Assert: edge_index darf NICHT leer sein
    assert edge_index, (
        "build_index['edge_index'] ist leer fuer ein Atom mit edges:[{rel, ziel}]. "
        "Ursache: _walk_vault_nodes uebergibt 'edges' nicht an den Knoten-Dict "
        "(fm.get('edges') vorhanden, aber Knoten-Dict hat keinen 'edges'-Key)."
    )

    # Luecke 2 Assert: target muss "NS.B1" sein (nicht None)
    all_targets = [
        entry.get("target")
        for entries in edge_index.values()
        for entry in (entries if isinstance(entries, list) else [entries])
    ]
    assert "NS.B1" in all_targets, (
        f"build_index['edge_index'] enthaelt kein entry mit target=='NS.B1'. "
        f"Alle gefundenen targets: {all_targets}. "
        "Ursache: build_edge_index liest e.get('target') statt e.get('ziel') "
        "fuer Atom-Edges mit 'ziel'-Key."
    )

    # Bonus-Assert: edge_type soll auch korrekt sein
    all_edge_types = [
        entry.get("edge_type")
        for entries in edge_index.values()
        for entry in (entries if isinstance(entries, list) else [entries])
        if entry.get("target") == "NS.B1"
    ]
    assert "relates_to" in all_edge_types, (
        f"edge_type fuer NS.B1 soll 'relates_to' sein, bekommen: {all_edge_types}. "
        "Ursache: build_edge_index liest e.get('edge_type') statt e.get('rel')."
    )


# ---------------------------------------------------------------------------
# E2 — Unit: build_edge_index akzeptiert Atom-Schema {rel, ziel} direkt
# ---------------------------------------------------------------------------

def test_e2_build_edge_index_accepts_atom_schema_rel_ziel():
    """
    E2 (Unit Stage-1): build_edge_index([{"path": "a.md", "edges": [{"rel": "relates_to",
    "ziel": "NS.B1"}]}]) mappt "a.md" auf einen Eintrag mit target=="NS.B1".

    RED jetzt: build_edge_index liest e.get("target") -> None (kein 'target'-Key
    im Atom-Schema). Ergebnis: target==None statt "NS.B1".

    GREEN wenn: build_edge_index target als e.get("target") or e.get("ziel") aufloeست
    (rueckwaerts-kompatibel mit BL-Schema).
    """
    nodes = [
        {
            "path": "a.md",
            "edges": [{"rel": "relates_to", "ziel": "NS.B1"}],
        }
    ]

    idx = build_retrieval_index.build_edge_index(nodes)

    # "a.md" muss als Key erscheinen (edges sind vorhanden)
    assert "a.md" in idx, (
        f"build_edge_index liefert keinen Key 'a.md' fuer Atom-Schema {{rel, ziel}}. "
        f"Index: {idx}"
    )

    entries = idx["a.md"]
    assert len(entries) == 1, f"Genau 1 Edge erwartet, bekommen: {entries}"

    entry = entries[0]
    assert entry.get("target") == "NS.B1", (
        f"target soll 'NS.B1' sein (aus 'ziel'), bekommen: {entry.get('target')!r}. "
        "build_edge_index liest e.get('target') -> None (Atom-Edges tragen 'ziel')."
    )
    assert entry.get("edge_type") == "relates_to", (
        f"edge_type soll 'relates_to' sein (aus 'rel'), bekommen: {entry.get('edge_type')!r}. "
        "build_edge_index liest e.get('edge_type') -> None (Atom-Edges tragen 'rel')."
    )
    assert entry.get("path") == "a.md", (
        f"path soll 'a.md' sein, bekommen: {entry.get('path')!r}."
    )


# ---------------------------------------------------------------------------
# E3 — Back-compat: build_edge_index BL-Schema {target, edge_type} bleibt korrekt
# ---------------------------------------------------------------------------

def test_e3_build_edge_index_backcompat_bl_schema_target_edge_type():
    """
    E3 (Back-compat Guard, Stage-1): build_edge_index mit dem bestehenden BL-Node-
    Schema {target, edge_type} liefert nach dem Fix weiterhin korrekte Ergebnisse.

    Pinnt test_h3_build_edge_index_aggregates_by_source (aus test_build_retrieval_index.py)
    als Invariante fuer diesen Kontext: der Fix DARF das BL-Schema nicht brechen.

    GREEN bereits jetzt (kein Impl-Aenderung): build_edge_index liest e.get("target")
    und e.get("edge_type") korrekt fuer BL-Nodes.
    GREEN auch nach dem Fix (Backward-Compat-Pflicht).
    """
    nodes = [
        {
            "path": "b.md",
            "edges": [{"target": "BL-161", "edge_type": "depends_on"}],
        }
    ]

    idx = build_retrieval_index.build_edge_index(nodes)

    assert "b.md" in idx, (
        f"build_edge_index soll 'b.md' als Key liefern fuer BL-Schema. Index: {idx}"
    )

    entries = idx["b.md"]
    assert len(entries) == 1, f"Genau 1 Edge erwartet, bekommen: {entries}"

    entry = entries[0]
    assert entry.get("target") == "BL-161", (
        f"target soll 'BL-161' sein (BL-Schema), bekommen: {entry.get('target')!r}."
    )
    assert entry.get("edge_type") == "depends_on", (
        f"edge_type soll 'depends_on' sein (BL-Schema), bekommen: {entry.get('edge_type')!r}."
    )
    assert entry.get("path") == "b.md", (
        f"path soll 'b.md' sein, bekommen: {entry.get('path')!r}."
    )


if __name__ == "__main__":
    import sys as _sys
    _sys.exit(pytest.main([__file__, "-v"]))
