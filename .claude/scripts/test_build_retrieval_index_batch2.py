"""
test_build_retrieval_index_batch2.py — BL-242 / batch_2 / Stage 1 (Atomic) RED-Suite

M3 test-first GREENFIELD: die 4 batch_2-Erweiterungs-Funktionen
(merge_vault_indexes / render_tag_index_md / query / patch_index) existieren
NOCH NICHT in build_retrieval_index.py. Diese Suite ist die SOLL-Spezifikation
(Kent Beck: "tests are specifications") fuer die 4 atomaren Erweiterungs-Inseln
H8-H11 aus 4_Blueprint/S1/blueprint-batch_2.md (Slice-Plan H8-H11 + Gold-Definition).

Items (batch_2 = DAG-Kinder von AK-1):
  - BL-242-AK-CTX-1-PL-1  (AK-CTX-1, H8):  Cross-Vault-Merge mit vault_origin (SOA-1 Single-Vault graceful)
  - BL-242-AK-2-PL-1      (AK-2, H9):      _Tag-Index.md-Materializer (reiner String, kein File-IO)
  - BL-242-AK-4-PL-1      (AK-4, H10):     Praezisions-Query (Graph-Walk) + Akzeptanztest < grep-Baseline
  - BL-242-AK-6-PL-1      (AK-6, H11):     Inkrementeller Patch (nur path-Eintraege)

Stage-1 Mock-Grenze (stage_1.md / blueprint-batch_2.md §6b): KEIN reales Vault-File-IO,
KEINE vault-routing.json-Root-Resolution, KEIN realer 2-Vault-Walk, KEIN realer grep.
Jede Insel ist eine reine Funktion (voraggregierte Index-Dicts/Strings als Fixture-Argument).
Verdrahtung (Root-Resolution, realer Walk, _Tag-Index.md-Schreiben, realer grep) = Stage 3.

| #   | Insel/AK              | Gold-Bezug (blueprint-batch_2.md §6) |
|-----|-----------------------|--------------------------------------|
| T8  | H8  / AK-CTX-1        | merge_vault_indexes: vault_origin, Listen-Konkat, Single-Vault Pass-through (SOA-1) |
| T9  | H9  / AK-2            | render_tag_index_md: deterministischer MD-String, reine str-Rueckgabe (kein open()) |
| T10 | H10 / AK-4            | query: thematischer Graph-Walk, leere Treffer -> [] |
| T11 | H10 / AK-4 (Acceptance)| test_query_precision_modus: query ⊆ thematisch UND |query| < grep-Baseline |
| T12 | H11 / AK-6            | patch_index: nur path-Eintraege geaendert, Rest bit-identisch |

Reihenfolge = Canary-First / k_score_asc (blueprint-batch_2.md §3 Abh.-Graph):
H11 (k=15) -> H9 (k=34) -> H8 (AK-CTX-1 design-tragend) -> H10 (k=37, schwerst-testbar).
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

# batch_1-Modul existiert bereits (16/16 GREEN). Die 4 batch_2-Funktionen
# (merge_vault_indexes/render_tag_index_md/query/patch_index) sind GREENFIELD-NEU
# und FEHLEN -> die getattr-Asserts/Aufrufe unten schlagen JETZT fehl
# (AttributeError) = RED (Gesetz 2: fehlende Funktion zaehlt als Fehlschlag).
import build_retrieval_index  # noqa: E402


# ===========================================================================
# T12 — H11 (AK-6): patch_index — Canary-First (k_score=15, reine Dict-Mutation)
# ===========================================================================

def test_h11_patch_index_replaces_only_path_entries():
    """
    H11 / AK-6: Inkrementeller Patch ersetzt NUR die Eintraege, die `path`
    referenzieren, fuegt new_entries ein; alle anderen Keys bleiben bit-identisch
    (blueprint-batch_2.md §6 H11-Gold).
    """
    index = {
        "modus": [
            {"path": "old.md", "vault_origin": "OmniCommand"},
            {"path": "keep.md", "vault_origin": "OmniCommand"},
        ],
        "index": [
            {"path": "keep.md", "vault_origin": "OmniCommand"},
        ],
    }
    new_entries = {"modus": [{"path": "old.md", "vault_origin": "OmniCommand"}]}
    patched = build_retrieval_index.patch_index(index, "old.md", new_entries)

    # "keep.md"-Eintraege (anderer path) bleiben unveraendert in beiden Keys
    assert {"path": "keep.md", "vault_origin": "OmniCommand"} in patched["modus"]
    assert patched["index"] == [{"path": "keep.md", "vault_origin": "OmniCommand"}]
    # genau ein "old.md"-Eintrag unter "modus" (alt entfernt, neu eingefuegt)
    old_entries = [e for e in patched["modus"] if e["path"] == "old.md"]
    assert len(old_entries) == 1


def test_h11_patch_index_does_not_mutate_unrelated_keys():
    """
    H11 / AK-6 (Edge/Isolation + Reinheit): ein Key, der `path` gar nicht
    referenziert, ist im Ergebnis bit-identisch zum Original (keine Kollateral-
    Mutation). Zusaetzlich: das EINGABE-Dict bleibt unveraendert (patch_index
    liefert eine frische Kopie, mutiert das Original nicht — Docstring-Vertrag
    "frische Dict-Kopie, keine Eingabe-Mutation").
    """
    original_entry = {"path": "other.md", "vault_origin": "OmniCommand"}
    index = {"untouched": [dict(original_entry)]}
    patched = build_retrieval_index.patch_index(index, "missing.md", {})

    # Ergebnis bit-identisch im Inhalt ...
    assert patched["untouched"] == [original_entry]
    # ... aber eine FRISCHE Liste (kein Aliasing der Eingabe-Liste)
    assert patched["untouched"] is not index["untouched"]
    # Eingabe-Dict wurde NICHT mutiert (Reinheit)
    assert index == {"untouched": [original_entry]}


# ===========================================================================
# T9 — H9 (AK-2): render_tag_index_md — reine String-Funktion (kein File-IO)
# ===========================================================================

def test_h9_render_tag_index_md_returns_str_covering_all_tags():
    """
    H9 / AK-2: rendert das tag_index-Dict (aus build_tag_index, batch_1) als
    _Tag-Index.md-Markdown-STRING — fuer jeden Tag eine Sektion mit allen
    referenzierenden Files (blueprint-batch_2.md §6 H9-Gold).
    """
    tag_index = {
        "topic/index": [
            {"path": "a.md", "vault_origin": "OmniCommand"},
            {"path": "b.md", "vault_origin": "OmniCommand"},
        ],
        "bl/bl-242": [
            {"path": "a.md", "vault_origin": "OmniCommand"},
        ],
    }
    out = build_retrieval_index.render_tag_index_md(tag_index)
    assert isinstance(out, str)
    # jeder Tag erscheint als ECHTE Markdown-Sektion (## {tag}-Heading), nicht nur
    # als beliebiges Substring-Vorkommen (Gold E2: "pro Tag eine Sektion")
    assert "## topic/index" in out
    assert "## bl/bl-242" in out
    # jeder referenzierende File-Pfad erscheint als Markdown-Listenpunkt unter seinem Tag
    assert "- a.md" in out
    assert "- b.md" in out
    # Strukturierung: der Pfad steht NACH seinem Tag-Heading (Sektions-Zuordnung)
    assert out.index("## topic/index") < out.index("- b.md")


def test_h9_render_tag_index_md_is_deterministic_and_pure():
    """
    H9 / AK-2 (Determinismus + Reinheit): gleiche Eingabe -> identischer String
    (stabil sortiert) UND reine str-Rueckgabe (KEIN open()/write() — Datei-Schreiben
    ist Stage 3, blueprint-batch_2.md §6b H9-Nicht-Ziel).
    """
    tag_index = {
        "z/last": [{"path": "z.md", "vault_origin": "OmniCommand"}],
        "a/first": [{"path": "a.md", "vault_origin": "OmniCommand"}],
    }
    first = build_retrieval_index.render_tag_index_md(tag_index)
    second = build_retrieval_index.render_tag_index_md(tag_index)
    assert first == second, "render muss deterministisch sein (stabil sortiert)"
    # deterministische Sortierung: a/first erscheint vor z/last
    assert first.index("a/first") < first.index("z/last")


# ===========================================================================
# T8 — H8 (AK-CTX-1): merge_vault_indexes — design-tragend (vault_origin, SOA-1)
# ===========================================================================

def test_h8_merge_vault_indexes_concatenates_same_key_with_vault_origin():
    """
    H8 / AK-CTX-1: mergt zwei pro-Vault Index-Dicts in einen Cross-Vault-Index;
    gleicher Key in beiden Vaults -> Eintragslisten konkateniert; jeder Eintrag
    traegt sein vault_origin (blueprint-batch_2.md §6 H8-Gold).
    """
    index_a = {"modus": [{"path": "a.md", "vault_origin": "OmniCommand"}]}
    index_b = {
        "modus": [{"path": "d.md", "vault_origin": "DCS"}],
        "edge": [{"path": "e.md", "vault_origin": "DCS"}],  # nur in B vorhanden
    }
    merged = build_retrieval_index.merge_vault_indexes(index_a, index_b)
    # Konkatenation in stabiler Reihenfolge: A-Eintraege zuerst, dann B-Eintraege
    assert merged["modus"] == [
        {"path": "a.md", "vault_origin": "OmniCommand"},
        {"path": "d.md", "vault_origin": "DCS"},
    ]
    # jeder Eintrag traegt sein vault_origin (Herkunft erhalten)
    assert {e["vault_origin"] for e in merged["modus"]} == {"OmniCommand", "DCS"}
    # ein Key, der nur in index_b existiert, wird in den Cross-Vault-Index uebernommen
    assert merged["edge"] == [{"path": "e.md", "vault_origin": "DCS"}]


def test_h8_merge_vault_indexes_single_vault_passthrough():
    """
    H8 / AK-CTX-1 (SOA-1 Single-Vault graceful): index_b is None
    -> graceful Pass-through von index_a (kein Crash, blueprint-batch_2.md §6 H8-Gold).
    """
    index_a = {"modus": [{"path": "a.md", "vault_origin": "OmniCommand"}]}
    merged = build_retrieval_index.merge_vault_indexes(index_a, None)
    assert merged == index_a


# ===========================================================================
# T10 — H10 (AK-4): query — Praezisions-Graph-Walk (k_score=37, schwerst-testbar)
# ===========================================================================

def test_h10_query_returns_thematic_hits_via_graph_walk():
    """
    H10 / AK-4: gerichteter Graph-Walk — Treffer aus keyword_index[term] +
    Edge-Nachbarn aus edge_index; liefert thematische Knoten
    (blueprint-batch_2.md §6 H10-Gold).
    """
    keyword_index = {"modus": [{"path": "sdf_phase_1_1.md", "vault_origin": "OmniCommand"}]}
    edge_index = {
        "sdf_phase_1_1.md": [
            {"target": "bl-165.md", "edge_type": "depends_on", "path": "sdf_phase_1_1.md"},
        ],
    }
    hits = build_retrieval_index.query("modus", keyword_index, edge_index)
    paths = {h["path"] if isinstance(h, dict) else h for h in hits}
    assert "sdf_phase_1_1.md" in paths
    # Edge-Nachbar wird ueber den gerichteten Walk mitgezogen
    assert "bl-165.md" in paths


def test_h10_query_empty_term_returns_empty_list():
    """Edge-Case: Term ohne Index-Treffer -> [] (kein Crash, blueprint §6 H10-Gold)."""
    hits = build_retrieval_index.query("nichtvorhanden", {}, {})
    assert hits == []


# ===========================================================================
# T11 — H10 / AK-4 (Akzeptanztest): query-Praezision < grep-Baseline
# ===========================================================================

def test_query_precision_modus():
    """
    AK-4-Akzeptanztest (blueprint-batch_2.md §3 Akzeptanz-Test-Insel + §6 H10-Gold):
    query('modus') ⊆ thematische_knoten UND |query| < grep-Baseline.

    Fixture: thematische Modus-Knoten (INV-MODUS-Familie / SDF-Phase-1.1 / BL-165) +
    Distraktoren mit zufaelligem 'modus'-Wortvorkommen (Fliesstext-Rauschen).
    grep-Baseline = Fixture-Konstante (bekannte Trefferzahl ueber das Fixture, KEIN
    realer grep-Subprozess in Stage 1, §6b H10-Nicht-Ziel).
    """
    thematische_knoten = {
        "sdf_phase_1_1.md",
        "bl-165.md",
        "inv_modus_familie.md",
    }
    # nur thematische Knoten sind im pre-computed keyword_index unter "modus"
    keyword_index = {
        "modus": [
            {"path": "sdf_phase_1_1.md", "vault_origin": "OmniCommand"},
            {"path": "inv_modus_familie.md", "vault_origin": "OmniCommand"},
        ],
    }
    edge_index = {
        "sdf_phase_1_1.md": [
            {"target": "bl-165.md", "edge_type": "depends_on", "path": "sdf_phase_1_1.md"},
        ],
    }
    # grep wuerde ALLE Files mit dem Substring "modus" treffen — inkl. der
    # 3 Distraktoren mit Fliesstext-Rauschen (z.B. "im laufenden Modus...").
    grep_baseline_count = len(thematische_knoten) + 3  # = 6 (3 thematisch + 3 Rauschen)

    hits = build_retrieval_index.query("modus", keyword_index, edge_index)
    hit_paths = {h["path"] if isinstance(h, dict) else h for h in hits}

    # Praezision: jeder query-Treffer ist thematisch (kein Fliesstext-Rauschen)
    assert hit_paths <= thematische_knoten, (
        f"query lieferte nicht-thematische Treffer: {hit_paths - thematische_knoten}"
    )
    # query schlaegt grep: weniger (aber praezisere) Treffer als die grep-Baseline
    assert len(hit_paths) < grep_baseline_count, (
        f"query ({len(hit_paths)}) muss < grep-Baseline ({grep_baseline_count}) sein"
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
