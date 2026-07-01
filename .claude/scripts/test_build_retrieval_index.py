"""
test_build_retrieval_index.py — BL-242 / batch_1 / Stage 1 (Atomic) RED-Suite

M3 test-first GREENFIELD: build_retrieval_index.py existiert NOCH NICHT.
Diese Suite ist die SOLL-Spezifikation (Kent Beck: "tests are specifications")
fuer die 7 atomaren Aggregator-/Verifikations-Inseln H1-H7 aus
4_Blueprint/S1/sub-1.md + blueprint.md (Gold-Definition).

Items (batch_1):
  - BL-242-AK-CTX-3-PL-1  (AK-CTX-3, H1): Reuse-Substrat / Import-Disziplin (DRY)
  - BL-242-AK-1-PL-1      (AK-1, H2-H6): 5 Index-Aggregatoren
  - BL-242-AK-3-PL-1      (AK-3, H7): Coverage-Report-Counter (Report-only)

Stage-1 Mock-Grenze (stage_1.md): KEIN reales Vault-File-IO. Jede Insel ist
eine reine Funktion (parsed_nodes / wikilinks / files als Fixture-Argument).
Realer Vault-Walk + Artefakt-Schreiben = Stage 3 (NICHT hier).

| #  | Insel/AK              | Gold-Bezug |
|----|-----------------------|------------|
| T1 | H1 / AK-CTX-3         | Import-Identitaet der 3 Lead-Parser (DRY, keine eigene Regex) |
| T2 | H7 / AK-3             | compute_coverage Report (total/with_keywords/missing/pct) |
| T3 | H2 / AK-1             | build_keyword_index Aggregation je Keyword |
| T4 | H3 / AK-1             | build_edge_index Aggregation je Quell-Knoten |
| T5 | H4 / AK-1             | build_tag_index via extract_tags (Lead) |
| T6 | H5 / AK-1             | build_anchor_index Score bc*0.6 + fw*0.4 (BL-161 AK-2.3) |
| T7 | H6 / AK-1             | build_backlinks {referenced_by, references} + bidirektional (BL-161 AK-3.1) |

Reihenfolge = Outside-In / Canary-First (sub-1.md): niedrigstes Risiko zuerst
(statische Import-Verifikation T1), dann reiner Counter T2, dann Kern-Aggregatoren.
"""

import ast
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

# M3 test-first: dieser Import schlaegt JETZT fehl (Modul GREENFIELD-NEU, FEHLT)
# -> Collection-Error = RED (Gesetz 2: Compile-/Import-Fehler zaehlt als Fehlschlag).
import build_retrieval_index  # noqa: E402
import quality_node_health  # noqa: E402
import quality_tag_cluster  # noqa: E402
import quality_edge_health  # noqa: E402


# ---------------------------------------------------------------------------
# T1 — H1 (AK-CTX-3): Import-Identitaet / DRY (Canary, niedrigstes Risiko)
# ---------------------------------------------------------------------------

def test_h1_lead_parsers_are_imported_identity():
    """
    H1 / AK-CTX-3: Der Builder bindet die 3 Lead-Parser per Identitaet
    (Re-Use, kein Re-Implement). PT-GEN-LeadFollow / DRY.
    """
    assert (
        build_retrieval_index.parse_frontmatter
        is quality_node_health.parse_frontmatter
    ), "parse_frontmatter muss der Lead (quality_node_health) selbst sein, nicht eine Kopie"
    assert (
        build_retrieval_index.extract_tags
        is quality_tag_cluster.extract_tags
    ), "extract_tags muss der Lead (quality_tag_cluster) selbst sein"
    assert (
        build_retrieval_index.extract_wikilinks
        is quality_edge_health.extract_wikilinks
    ), "extract_wikilinks muss der Lead (quality_edge_health) selbst sein"


def _module_ast():
    """Parst das Ziel-Modul zu einem AST (statische Struktur-Analyse, kein Run)."""
    src_path = build_retrieval_index.__file__
    with open(src_path, "r", encoding="utf-8") as fh:
        return ast.parse(fh.read(), filename=src_path)


def test_h1_no_local_parser_regex_defined():
    """
    H1 / AK-CTX-3 (DRY-Negativ): Das Modul definiert KEINE eigene Parse-Logik —
    es nutzt KEINE re-Compilation/-Matching ueberhaupt (DRY: die 3 Lead-Parser
    werden re-exportiert, nicht re-implementiert).

    AST-basiert (vorher: naiver Substring-OR-Guard `"re.compile" not in src or
    "frontmatter" not in src`, der bei umformulierten Kommentaren faelschlich gruen
    wurde UND eine echte lokale `re.match(...)`-Parse-Regex durchgelassen haette,
    solange das Wort "frontmatter" im Source fehlte). Der AST-Scan nagelt das echte
    Verhalten fest: KEIN Aufruf von re.compile/re.match/re.search/re.findall/
    re.fullmatch/re.finditer/re.sub im Modul — unabhaengig von Kommentar-Text.
    """
    tree = _module_ast()
    forbidden_re_calls = {
        "compile", "match", "search", "findall", "fullmatch", "finditer", "sub",
    }
    re_parse_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "re"
        and node.func.attr in forbidden_re_calls
    ]
    assert re_parse_calls == [], (
        "Builder darf KEINE eigene Parse-Regex kompilieren/matchen "
        f"(DRY-Verletzung): gefundene re.*-Aufrufe in Z. "
        f"{[n.lineno for n in re_parse_calls]}"
    )


def test_h1_lead_parsers_not_locally_redefined():
    """
    H1 / AK-CTX-3 (DRY-Positiv-Pin, AST): Die 3 Lead-Parser-Namen werden per
    Import (ast.ImportFrom) gebunden und NICHT als lokale `def`/`class` im Modul
    re-implementiert. Pinnt PT-GEN-LeadFollow strukturell fest — der `is`-Identitaets-
    Check (test_h1_lead_parsers_are_imported_identity) prueft das Laufzeit-Objekt,
    dieser Test prueft die statische Quell-Struktur (kein Schatten-`def`).
    """
    tree = _module_ast()
    lead_names = {"parse_frontmatter", "extract_tags", "extract_wikilinks"}

    imported = {
        alias.asname or alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
        for alias in node.names
    }
    locally_defined = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }

    assert lead_names <= imported, (
        "Alle 3 Lead-Parser muessen per `from ... import` gebunden sein (DRY-Reuse): "
        f"fehlend = {sorted(lead_names - imported)}"
    )
    assert lead_names.isdisjoint(locally_defined), (
        "Kein Lead-Parser darf lokal re-implementiert werden (Schatten-def "
        "verletzt PT-GEN-LeadFollow/DRY): "
        f"lokal definiert = {sorted(lead_names & locally_defined)}"
    )


# ---------------------------------------------------------------------------
# T2 — H7 (AK-3): compute_coverage Report-only Counter (Canary)
# ---------------------------------------------------------------------------

def _coverage_fixture():
    """3 Files: 2 mit keywords, 1 ohne -> with_keywords=2, missing=1."""
    return [
        {"path": "a.md", "keywords": ["modus", "index"]},
        {"path": "b.md", "keywords": ["coverage"]},
        {"path": "c.md", "keywords": []},
    ]


def test_h7_compute_coverage_report_shape():
    """H7 / AK-3: korrektes Report-Dict total/with_keywords/missing/pct."""
    files = _coverage_fixture()
    report = build_retrieval_index.compute_coverage(files)
    assert report["total"] == 3
    assert report["with_keywords"] == 2
    assert report["missing"] == ["c.md"]
    assert report["pct"] == round(2 / 3 * 100, 1)
    # len(missing) == total - with_keywords
    assert len(report["missing"]) == report["total"] - report["with_keywords"]


def test_h7_compute_coverage_no_side_effect():
    """H7 / AK-3: Report-only — KEINE Mutation der Eingabe-Files (A6/SOA-2)."""
    files = _coverage_fixture()
    before = [dict(f) for f in files]
    build_retrieval_index.compute_coverage(files)
    assert files == before, "compute_coverage darf die Quell-Files nicht mutieren"


def test_h7_compute_coverage_empty_division_guard():
    """Edge-Case: total==0 -> pct definiert (Division-Guard), missing leer."""
    report = build_retrieval_index.compute_coverage([])
    assert report["total"] == 0
    assert report["with_keywords"] == 0
    assert report["missing"] == []
    assert report["pct"] == 0.0


# ---------------------------------------------------------------------------
# T3 — H2 (AK-1): build_keyword_index
# ---------------------------------------------------------------------------

def test_h2_build_keyword_index_aggregates_referencing_nodes():
    """
    H2 / AK-1: je Keyword die referenzierenden Knoten
    ({path, bl_id, vault_origin, node_type}).
    """
    nodes = [
        {
            "path": "BL-242/x.md",
            "bl_id": "BL-242",
            "vault_origin": "OmniCommand",
            "node_type": "spec",
            "keywords": ["modus"],
        },
    ]
    idx = build_retrieval_index.build_keyword_index(nodes)
    assert idx["modus"] == [
        {
            "path": "BL-242/x.md",
            "bl_id": "BL-242",
            "vault_origin": "OmniCommand",
            "node_type": "spec",
        }
    ]


def test_h2_build_keyword_index_empty_field_no_entry():
    """Edge-Case: Knoten mit leerem keywords-Feld erzeugt KEINEN Index-Key."""
    nodes = [{"path": "y.md", "bl_id": "BL-242", "vault_origin": "OmniCommand",
              "node_type": "model", "keywords": []}]
    idx = build_retrieval_index.build_keyword_index(nodes)
    assert idx == {}


# ---------------------------------------------------------------------------
# T4 — H3 (AK-1): build_edge_index
# ---------------------------------------------------------------------------

def test_h3_build_edge_index_aggregates_by_source():
    """H3 / AK-1: Frontmatter-edges nach Quell-Knoten ({target, edge_type, path})."""
    nodes = [
        {
            "path": "BL-242/a.md",
            "edges": [{"target": "BL-161", "edge_type": "depends_on"}],
        },
    ]
    idx = build_retrieval_index.build_edge_index(nodes)
    assert idx["BL-242/a.md"] == [
        {"target": "BL-161", "edge_type": "depends_on", "path": "BL-242/a.md"}
    ]


def test_h3_build_edge_index_no_edges_no_key():
    """Edge-Case: Knoten ohne edges-Feld -> kein Key im Index."""
    nodes = [{"path": "BL-242/b.md"}]
    idx = build_retrieval_index.build_edge_index(nodes)
    assert "BL-242/b.md" not in idx


# ---------------------------------------------------------------------------
# T5 — H4 (AK-1): build_tag_index (via extract_tags Lead)
# ---------------------------------------------------------------------------

def test_h4_build_tag_index_lists_files_per_tag_via_lead():
    """
    H4 / AK-1: ruft extract_tags (Lead) auf, listet je Tag alle Files
    ({path, vault_origin}). KEINE MD-Materialisierung (batch_2-Scope).
    """
    nodes = [
        {"path": "a.md", "vault_origin": "OmniCommand",
         "frontmatter": {"tags": ["topic/Index", "bl/BL-242"]}},
        {"path": "b.md", "vault_origin": "OmniCommand",
         "frontmatter": {"tags": ["topic/Index"]}},
    ]
    idx = build_retrieval_index.build_tag_index(nodes)
    # extract_tags normalisiert auf lowercase (Lead-Verhalten)
    assert {"path": "a.md", "vault_origin": "OmniCommand"} in idx["topic/index"]
    assert {"path": "b.md", "vault_origin": "OmniCommand"} in idx["topic/index"]
    assert len(idx["topic/index"]) == 2
    assert idx["bl/bl-242"] == [{"path": "a.md", "vault_origin": "OmniCommand"}]


def test_h4_build_tag_index_empty_tags_no_key():
    """Edge-Case: Knoten ohne tags -> kein Tag-Key."""
    nodes = [{"path": "c.md", "vault_origin": "OmniCommand", "frontmatter": {}}]
    idx = build_retrieval_index.build_tag_index(nodes)
    assert idx == {}


# ---------------------------------------------------------------------------
# T6 — H5 (AK-1): build_anchor_index (Score bc*0.6 + fw*0.4, BL-161 AK-2.3)
# ---------------------------------------------------------------------------

def test_h6_build_anchor_index_score_formula():
    """
    H5 / AK-1: Score == round(backlink_count*0.6 + frontmatter_weight*0.4)
    (BL-161 AK-2.3).
    """
    nodes = [{"path": "a.md", "frontmatter_weight": 5}]
    # wikilinks: 2 Knoten verweisen auf a.md -> backlink_count(a)=2
    wikilinks = [
        {"source": "x.md", "target": "a.md"},
        {"source": "y.md", "target": "a.md"},
    ]
    idx = build_retrieval_index.build_anchor_index(nodes, wikilinks)
    expected = round(2 * 0.6 + 5 * 0.4)
    assert idx["a.md"]["score"] == expected


def test_h6_build_anchor_index_no_backlinks_uses_frontmatter_only():
    """Edge-Case: Knoten ohne Backlinks -> Score nur aus frontmatter_weight."""
    nodes = [{"path": "lonely.md", "frontmatter_weight": 3}]
    idx = build_retrieval_index.build_anchor_index(nodes, [])
    assert idx["lonely.md"]["score"] == round(0 * 0.6 + 3 * 0.4)


# ---------------------------------------------------------------------------
# T7 — H6 (AK-1): build_backlinks ({referenced_by, references}, BL-161 AK-3.1)
# ---------------------------------------------------------------------------

def test_h5_build_backlinks_schema_and_bidirectional_consistency():
    """
    H6 / AK-1: Schema {path: {referenced_by, references}} + bidirektionale
    Konsistenz: B in references[A] <=> A in referenced_by[B] (BL-161 AK-3.1).
    """
    nodes = [{"path": "A.md"}, {"path": "B.md"}]
    wikilinks = [{"source": "A.md", "target": "B.md"}]
    idx = build_retrieval_index.build_backlinks(nodes, wikilinks)
    assert idx["A.md"] == {"referenced_by": [], "references": ["B.md"]}
    assert idx["B.md"] == {"referenced_by": ["A.md"], "references": []}
    # bidirektionale Konsistenz
    assert "B.md" in idx["A.md"]["references"]
    assert "A.md" in idx["B.md"]["referenced_by"]


def test_h5_build_backlinks_no_links_empty_maps():
    """Edge-Case: Knoten ohne Wikilinks -> beide Listen leer."""
    nodes = [{"path": "iso.md"}]
    idx = build_retrieval_index.build_backlinks(nodes, [])
    assert idx["iso.md"] == {"referenced_by": [], "references": []}


# ===========================================================================
# BL-242 / batch_3 / Stage 1 (Atomic) — RED-Suite (M3 test-first GREENFIELD)
#
# Items (batch_3):
#   - BL-242-AK-CTX-2-PL-1  (AK-CTX-2, H12-H14): Index-Serialisierung + Form-Fn
#   - BL-242-AK-5-PL-1       (AK-5): _W_fetch Schritt 0d — KEIN Stage-1-Artefakt
#                            (Markdown-Skill-Edit, Szenario-Verify = Stage 3).
#
# Stage-1 Mock-Grenze (stage_1.md / sub-1-batch_3.md): reine Funktionen gegen
# Fixtures. KEIN reales json.dump/open(), KEINE Pfad-Resolution
# (.claude/output/retrieval_index/), KEIN _Tag-Index.md-Schreiben (= Stage 3).
#
# | #   | Insel/AK             | Gold-Bezug |
# |-----|----------------------|------------|
# | T12 | H13 / AK-CTX-2        | anchor_score bc*0.6 + fw*0.4 (BL-161 AK-2.3) — Canary |
# | T13 | H14 / AK-CTX-2        | backlinks_schema {path, referenced_by, references} (BL-161 AK-3.1) |
# | T14 | H12 / AK-CTX-2        | serialize_index_json deterministisch + JSON-Round-Trip |
#
# Reihenfolge = Canary-First (sub-1-batch_3.md): reine Arithmetik (H13) zuerst,
# dann reine Form (H14), dann Determinismus-Kern (H12).
# RED-Beweis: serialize_index_json/anchor_score/backlinks_schema existieren
# NICHT in build_retrieval_index.py -> AttributeError (GREENFIELD-missing).
# ===========================================================================


# ---------------------------------------------------------------------------
# T12 — H13 (AK-CTX-2): anchor_score (BL-161 AK-2.3, Canary — reine Arithmetik)
# ---------------------------------------------------------------------------

def test_h13_anchor_score_formula():
    """
    H13 / AK-CTX-2: Anchor-Score-Formel BL-161 AK-2.3:
    backlink_count*0.6 + frontmatter_weight*0.4 ueber mehrere Fixture-Tupel.
    Reine Arithmetik, KEIN IO.
    """
    # Konkrete erwartete Score-Werte (Living-Doc: der Vertrag 0.6/0.4 ist als
    # Literal gepinnt, nicht nur als Formel-Spiegel — ein Gewichts-Drift
    # (z.B. 0.5/0.5) faellt auf, auch wenn die Spiegel-Arithmetik mitwanderte).
    assert build_retrieval_index.anchor_score(2, 5) == 3.2   # 2*0.6 + 5*0.4
    assert build_retrieval_index.anchor_score(10, 0) == 6.0  # 10*0.6 + 0*0.4
    assert build_retrieval_index.anchor_score(3, 7) == 4.6   # 3*0.6 + 7*0.4


def test_h13_anchor_score_zero_boundary():
    """Edge-Case: Null-Grenzwert (0,0) -> 0.0."""
    assert build_retrieval_index.anchor_score(0, 0) == 0.0


def test_h13_anchor_score_deterministic():
    """H13: deterministisch — gleicher Input -> bit-identischer Output, und der
    Output ist der exakt erwartete float-Wert (4*0.6 + 6*0.4 == 4.8)."""
    first = build_retrieval_index.anchor_score(4, 6)
    second = build_retrieval_index.anchor_score(4, 6)
    assert first == second
    assert first == 4.8
    assert isinstance(first, float)


# ---------------------------------------------------------------------------
# T13 — H14 (AK-CTX-2): backlinks_schema (BL-161 AK-3.1, reine Form-Fn)
# ---------------------------------------------------------------------------

def test_h14_backlinks_schema_exact_keys():
    """
    H14 / AK-CTX-2: Backlinks-Eintrag exakt Keys {path, referenced_by, references}
    (BL-161 AK-3.1). Reine (args) -> dict-Fn, KEIN IO.
    """
    entry = build_retrieval_index.backlinks_schema("A.md", ["B.md"], ["C.md"])
    assert set(entry.keys()) == {"path", "referenced_by", "references"}
    assert entry["path"] == "A.md"


def test_h14_backlinks_schema_lists_stable_sorted():
    """H14: referenced_by / references Listen stabil sortiert."""
    entry = build_retrieval_index.backlinks_schema("A.md", ["z.md", "a.md"], ["y.md", "b.md"])
    assert entry["referenced_by"] == ["a.md", "z.md"]
    assert entry["references"] == ["b.md", "y.md"]


def test_h14_backlinks_schema_empty_lists():
    """Edge-Case: leere referenced_by/references -> Keys vorhanden, Listen leer."""
    entry = build_retrieval_index.backlinks_schema("iso.md", [], [])
    assert entry == {"path": "iso.md", "referenced_by": [], "references": []}


# ---------------------------------------------------------------------------
# T14 — H12 (AK-CTX-2): serialize_index_json (Determinismus-Kern + Round-Trip)
# ---------------------------------------------------------------------------

def test_h12_serialize_index_json_is_str_no_file_io():
    """
    H12 / AK-CTX-2: RUECKGABE ist str (reine dict -> str-Fn). KEIN open()/Datei-
    Schreiben (Mock-Grenze Stage 1).
    """
    idx = {"keyword_index": {"modus": [{"path": "A.md"}]}}
    out = build_retrieval_index.serialize_index_json(idx)
    assert isinstance(out, str)
    # Kanonische (kompakte) Separatoren: KEINE Whitespace-Trenner (sep=(",",":")).
    assert ", " not in out
    assert ": " not in out


def test_h12_serialize_index_json_round_trip():
    """H12: json.loads(serialize_index_json(idx)) == idx (Round-Trip-Treue)."""
    idx = {
        "keyword_index": {"modus": [{"path": "A.md"}], "vault": [{"path": "B.md"}]},
        "edge_index": {"A.md": ["B.md"]},
        "anchor_index": {"A.md": {"score": 3.2}},
        "backlinks": {"A.md": {"referenced_by": [], "references": ["B.md"]}},
    }
    assert json.loads(build_retrieval_index.serialize_index_json(idx)) == idx


def test_h12_serialize_index_json_deterministic_bit_identical():
    """
    H12: bit-identisch bei wiederholtem Aufruf (Determinismus); Keys stabil
    sortiert (sort_keys=True). Zwei verschieden-geordnete aber gleiche Dicts
    serialisieren identisch.
    """
    idx_a = {"b": {"y": 1, "x": 2}, "a": {"m": 3}}
    idx_b = {"a": {"m": 3}, "b": {"x": 2, "y": 1}}
    assert build_retrieval_index.serialize_index_json(idx_a) == build_retrieval_index.serialize_index_json(idx_a)
    assert build_retrieval_index.serialize_index_json(idx_a) == build_retrieval_index.serialize_index_json(idx_b)
    # sort_keys=True strukturell gepinnt: Schluessel 'a' steht VOR 'b' (lexikalisch),
    # unabhaengig von der Insertion-Reihenfolge des Eingabe-Dicts.
    out_a = build_retrieval_index.serialize_index_json(idx_a)
    assert out_a.startswith('{"a":')
    assert out_a.index('"a"') < out_a.index('"b"')


def test_h12_serialize_index_json_empty_dict():
    """Edge-Case: leeres Index-Dict {} -> valider JSON-String, Round-Trip == {}."""
    out = build_retrieval_index.serialize_index_json({})
    assert json.loads(out) == {}


# ===========================================================================
# BL-274 / SB-2 / Stage 1 (Atomic, Laserpointer) — MAP-cut RED-Suite
#
# Items: BL-274-AK-2-PL-1 (cut_sections) + BL-274-AK-3-PL-1 (_derive_map_slots).
# M3 test-first GREENFIELD: cut_sections + _derive_map_slots existieren NOCH
# NICHT in build_retrieval_index.py -> AttributeError = RED (Gesetz 2:
# fehlendes Symbol zaehlt als Fehlschlag). Reine, seiteneffektfreie Funktionen:
# synthetische Root-Listen als Fixture-Argument, KEIN reales Vault-File-IO,
# KEIN Lock/Dispatch unter Test (Stage-1-Grenze INV-STAGE-8).
#
# Reihenfolge Outside-In / Canary-First (sub-1.md SB-2):
#   T1 Canary (B=1=seriell) -> T2 Slot-Formel -> T3 Voll-Abdeckung (groebste
#   Invariante) -> T4 Format-Treue -> T5 kontrollierte Ueberlappung ->
#   T6 Determinismus (feinste Invariante).
# ===========================================================================


# ---------------------------------------------------------------------------
# T1 — AK-3 (Canary): B=1 -> 0 parallele Slots -> seriell (Regress-Guard)
# ---------------------------------------------------------------------------

def test_derive_map_slots_budget_one_is_serial_canary():
    """
    AK-3 Kanarienvogel (niedrigstes Risiko zuerst): parallelism_budget=1 ->
    0 parallele Map-Slots -> serieller Lauf (heutiges Verhalten, kein Regress).
    """
    assert build_retrieval_index._derive_map_slots(1) == 0


# ---------------------------------------------------------------------------
# T2 — AK-3: Slot-Formel max(B-1, 0) ueber mehrere Budgets
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("budget,expected_map_slots", [
    (1, 0),   # seriell (Regress-Guard)
    (2, 1),
    (3, 2),
    (5, 4),
])
def test_derive_map_slots_equals_max_budget_minus_one(budget, expected_map_slots):
    """
    AK-3: bei parallelism_budget=B stehen max(B-1, 0) parallele Map-Slots zur
    Verfuegung (1 Slot bleibt fuer den Lead/Orchestrator, PT-CMD-005 Wellen).
    """
    assert build_retrieval_index._derive_map_slots(budget) == max(budget - 1, 0)


# ---------------------------------------------------------------------------
# T3 — AK-2: cut_sections deckt den vollen Root-Set lueckenlos ab (missing=∅)
# ---------------------------------------------------------------------------

def test_cut_sections_covers_full_root_set_no_gap():
    """
    AK-2: Vereinigung aller Sektionen == voller Root-Set. Kein Root faellt durch
    den Schnitt (Knoten-Luecke verboten). Synthetische Root-Liste als Fixture.
    """
    roots = ["vault/A", "vault/B", "vault/C", "vault/D"]
    sections = build_retrieval_index.cut_sections(roots)
    flattened = [r for section in sections for r in section]
    assert set(flattened) == set(roots)


def test_cut_sections_empty_root_set_yields_empty():
    """AK-2 Edge-Case (Raender zuerst): leerer Root-Set -> [] (kein Crash)."""
    assert build_retrieval_index.cut_sections([]) == []


# ---------------------------------------------------------------------------
# T4 — AK-2: Format-Treue — jede Sektion ist list[root], build_index-uebergebbar
# ---------------------------------------------------------------------------

def test_cut_sections_each_section_is_root_list_build_index_compatible():
    """
    AK-2 / AE-1: jede Sektion ist eine list (Root-Liste), exakt das
    build_index(roots)-Eingabeformat (kein neues Section-DTO). Typ-Treue.
    """
    roots = ["vault/A", "vault/B", "vault/C"]
    sections = build_retrieval_index.cut_sections(roots)
    assert all(isinstance(section, list) for section in sections)
    # Jede Sektion ist direkt an build_index uebergebbar (list[root]).
    assert all(all(isinstance(r, str) for r in section) for section in sections)


# ---------------------------------------------------------------------------
# T5 — AK-2: kontrollierte Ueberlappung — Default-Strategy disjunkt
# ---------------------------------------------------------------------------

def test_cut_sections_default_strategy_is_disjoint_no_uncontrolled_overlap():
    """
    AK-2: bei Default-Strategy (toplevel_dir_range, SA-1) sind die Sektionen
    disjunkt — kein Root erscheint in mehr als einer Sektion (keine
    unkontrollierte Ueberlappung).
    """
    roots = ["vault/A", "vault/B", "vault/C", "vault/D"]
    sections = build_retrieval_index.cut_sections(roots)
    flattened = [r for section in sections for r in section]
    # Disjunkt: keine Root-Duplikate ueber Sektionen hinweg.
    assert len(flattened) == len(set(flattened))


# ---------------------------------------------------------------------------
# T6 — AK-2: Determinismus / Resume-Stabilitaet (PT-CMD-007)
# ---------------------------------------------------------------------------

def test_cut_sections_is_deterministic_rerun_identical():
    """
    AK-2: gleicher Input -> identische Partition (Re-Run-Identitaet). Vorbedingung
    fuer AK-8 RESUME (SB-5). Kein Mengen-/Hash-Nichtdeterminismus.
    """
    roots = ["vault/D", "vault/A", "vault/C", "vault/B"]
    assert build_retrieval_index.cut_sections(roots) == build_retrieval_index.cut_sections(roots)


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
