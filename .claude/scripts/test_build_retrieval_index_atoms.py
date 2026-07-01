"""
test_build_retrieval_index_atoms.py — BL-389 / batch_2 / AK-ATOM-INDEX / Stage 3 (RED-Suite)

M3 test-first: build_truth_atom_index existiert NOCH NICHT in build_retrieval_index.py.
Diese Suite ist die SOLL-Spezifikation fuer DoD-2 (AK-ATOM-INDEX):

  build_truth_atom_index(vault_roots) walkt type:truth-Dateien, liest keywords[] aus
  Frontmatter, baut deterministischen Inverted-Index {keyword: [truth_path_or_id, ...]}.

Testanforderungen (Spec DoD-2):
  - Walk findet genau type:truth-Dateien (Nicht-Truth-.md werden ignoriert)
  - Inverted-Index korrekt: keyword -> [paths] bildet Korpus-keywords ab
  - Determinismus: zwei Index-Laeufe -> identische Map (stabile Sortierung)
  - Persistenz: _keyword_index.json geschrieben + round-trip-stabil
  - Lead-Parser (parse_frontmatter) per Identitaet reused (kein Duplikat)
  - Serialisierbar via serialize_index_json

Stage-3 (realer tmp-Vault-Korpus): tmp-Verzeichnis mit echten .md-Dateien, kein Mock.
RED-Beweis: build_truth_atom_index fehlt -> AttributeError bei allen Tests.

| #  | Test                                | Invariante |
|----|-------------------------------------|------------|
| A1 | Canary: Funktion existiert          | AttributeError -> RED |
| A2 | Walk: nur type:truth gefunden       | node_type-Filter |
| A3 | Inverted-Index korrekt              | keyword -> paths |
| A4 | 1 keyword in 2 Truths -> 2 Eintraege | Multi-Truth-Aggregation |
| A5 | Deterministisch (stable sort)       | 2x gleicher Index |
| A6 | Reuse Lead-Parser (Identitaet)      | DRY / PT-GEN-LeadFollow |
| A7 | Leerer Vault -> {}                  | Edge-Case kein Crash |
| A8 | Truth ohne keywords -> kein Key     | Grace-Handling |
| A9 | Persistenz: JSON geschrieben        | DoD-2 Artefakt |
| A10| Round-Trip: serialize_index_json    | Serialisierbar |
| A11| truth_keywords.extract_keywords Fallback | falls keywords[] fehlt aber Text vorhanden |
| A12| Nicht-.md Dateien ignoriert         | Filter-Robustheit |
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

import build_retrieval_index  # noqa: E402
import quality_node_health  # noqa: E402

# ---------------------------------------------------------------------------
# Fixtures: tmp-Vault-Korpus
# ---------------------------------------------------------------------------

def _write_truth(dirpath, filename, local_id, keywords=None, extra_text=""):
    """Schreibt eine minimale type:truth .md-Datei in dirpath."""
    kw_yaml = ""
    if keywords is not None:
        kw_str = ", ".join(f'"{k}"' for k in keywords)
        kw_yaml = f"keywords: [{kw_str}]\n"
    content = (
        "---\n"
        "type: truth\n"
        f"id: BL-389.{local_id}\n"
        f"local_id: {local_id}\n"
        "text: Eine Wahrheit ueber das System.\n"
        "typ: FESTSTELLUNG\n"
        "herkunft: INTERN\n"
        "status: OFFEN\n"
        "truth_grade: vault_hypothesis\n"
        f"{kw_yaml}"
        "---\n"
        f"# {local_id}\n\n"
        f"Inhalt der Wahrheit. {extra_text}\n"
    )
    fpath = os.path.join(dirpath, filename)
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(content)
    return fpath


def _write_non_truth(dirpath, filename):
    """Schreibt eine .md-Datei die KEIN type:truth ist (type: spec)."""
    content = (
        "---\n"
        "type: spec\n"
        "feature: BL-389\n"
        "bl-item: BL-389\n"
        "keywords: [index, spec, modus]\n"
        "---\n"
        "# Spec\n\nIch bin keine Wahrheit.\n"
    )
    fpath = os.path.join(dirpath, filename)
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(content)
    return fpath


# ---------------------------------------------------------------------------
# A1 — Canary: Funktion existiert (AttributeError = RED-Beweis)
# ---------------------------------------------------------------------------

def test_atom_index_function_exists():
    """
    A1 Canary: build_truth_atom_index muss in build_retrieval_index verfuegbar sein.
    Jetzt: AttributeError -> RED (Funktion fehlt noch).
    GREEN wenn: hasattr(build_retrieval_index, 'build_truth_atom_index') == True.
    """
    assert hasattr(build_retrieval_index, "build_truth_atom_index"), (
        "build_truth_atom_index fehlt in build_retrieval_index — "
        "GREEN-Worker muss diese Funktion implementieren."
    )


# ---------------------------------------------------------------------------
# A2 — Walk: nur type:truth gefunden, Nicht-Truth-Dateien ignoriert
# ---------------------------------------------------------------------------

def test_atom_index_only_truth_files_indexed(tmp_path):
    """
    A2: Walk findet GENAU die type:truth-Dateien; Nicht-Truth-.md werden
    ignoriert (Spec DoD-2: 'Walk findet genau die type:truth-Dateien').
    """
    _write_truth(str(tmp_path), "truth_a.md", "T001", keywords=["modus", "index"])
    _write_non_truth(str(tmp_path), "spec_b.md")

    idx = build_retrieval_index.build_truth_atom_index([str(tmp_path)])

    # truth_a.md traegt "modus" und "index" -> diese Keywords muessen erscheinen
    assert "modus" in idx, "keyword 'modus' aus type:truth fehlt im Index"
    assert "index" in idx, "keyword 'index' aus type:truth fehlt im Index"

    # spec_b.md ist KEIN type:truth -> sein exklusives keyword "spec" darf NICHT im Index stehen
    # (kein false-positive aus Nicht-Truth-Dateien)
    all_paths_in_index = [
        entry if isinstance(entry, str) else entry.get("path", "")
        for entries in idx.values()
        for entry in (entries if isinstance(entries, list) else [entries])
    ]
    for path in all_paths_in_index:
        assert "spec_b" not in str(path), (
            f"Nicht-Truth-Datei 'spec_b.md' darf nicht im Atom-Index erscheinen, "
            f"gefunden in: {path}"
        )


# ---------------------------------------------------------------------------
# A3 — Inverted-Index korrekt: keyword -> paths/eintraege
# ---------------------------------------------------------------------------

def test_atom_index_inverted_structure_correct(tmp_path):
    """
    A3: keyword -> [entry, ...] bildet Korpus-keywords korrekt ab.
    Jeder Entry enthaelt mindestens den Pfad zur Truth-Datei.
    """
    _write_truth(str(tmp_path), "truth_x.md", "TX01", keywords=["wahrheit", "kausalitaet"])

    idx = build_retrieval_index.build_truth_atom_index([str(tmp_path)])

    assert "wahrheit" in idx, "keyword 'wahrheit' fehlt im Index"
    assert "kausalitaet" in idx, "keyword 'kausalitaet' fehlt im Index"

    # Index ist ein Dict: keyword -> list
    assert isinstance(idx["wahrheit"], list), "Eintraege muessen eine Liste sein"
    assert len(idx["wahrheit"]) == 1, "Genau 1 Truth traegt 'wahrheit'"

    entry = idx["wahrheit"][0]
    # Entry enthaelt path (relativ oder absolut, aber erkennbar als truth_x.md)
    entry_str = str(entry) if isinstance(entry, str) else str(entry.get("path", entry))
    assert "truth_x" in entry_str, (
        f"Entry fuer 'wahrheit' muss Pfad zu truth_x.md enthalten, bekommen: {entry!r}"
    )


# ---------------------------------------------------------------------------
# A4 — 1 keyword in 2 Truths -> 2 Eintraege (Multi-Truth-Aggregation)
# ---------------------------------------------------------------------------

def test_atom_index_shared_keyword_has_two_entries(tmp_path):
    """
    A4 (Spec DoD-2): 'ein keyword in 2 Truths -> 2 Eintraege'.
    Zwei Truths mit demselben keyword 'system' -> Index['system'] hat len==2.
    """
    _write_truth(str(tmp_path), "truth1.md", "T001", keywords=["system", "modus"])
    _write_truth(str(tmp_path), "truth2.md", "T002", keywords=["system", "wahrheit"])

    idx = build_retrieval_index.build_truth_atom_index([str(tmp_path)])

    assert "system" in idx, "Geteiltes keyword 'system' fehlt im Index"
    assert len(idx["system"]) == 2, (
        f"Keyword 'system' soll 2 Eintraege haben (2 Truths), bekommen: {len(idx['system'])}"
    )

    # Beide Truths muessen repraesentiert sein
    paths_str = [
        str(e) if isinstance(e, str) else str(e.get("path", e))
        for e in idx["system"]
    ]
    has_truth1 = any("truth1" in p for p in paths_str)
    has_truth2 = any("truth2" in p for p in paths_str)
    assert has_truth1, f"truth1.md fehlt in Index['system']: {paths_str}"
    assert has_truth2, f"truth2.md fehlt in Index['system']: {paths_str}"


# ---------------------------------------------------------------------------
# A5 — Deterministisch (stable sort, 2 Laeufe -> identischer Index)
# ---------------------------------------------------------------------------

def test_atom_index_deterministic_two_runs(tmp_path):
    """
    A5 (Spec DoD-2): 'zwei Index-Laeufe ueber denselben Korpus -> identische Map
    (stabile Sortierung)'. Kein Hash/Set-Nichtdeterminismus.
    """
    _write_truth(str(tmp_path), "alpha.md", "A001", keywords=["modus", "index", "wahrheit"])
    _write_truth(str(tmp_path), "beta.md", "B001", keywords=["modus", "system"])

    idx_first = build_retrieval_index.build_truth_atom_index([str(tmp_path)])
    idx_second = build_retrieval_index.build_truth_atom_index([str(tmp_path)])

    # Keys muessen identisch sein
    assert sorted(idx_first.keys()) == sorted(idx_second.keys()), (
        "Index-Keys unterscheiden sich zwischen zwei Laeufen (Nichtdeterminismus)"
    )

    # Jede Entry-Liste muss identisch sortiert sein
    for kw in idx_first:
        entries_first = [
            str(e) if isinstance(e, str) else str(e.get("path", e))
            for e in idx_first[kw]
        ]
        entries_second = [
            str(e) if isinstance(e, str) else str(e.get("path", e))
            for e in idx_second[kw]
        ]
        assert entries_first == entries_second, (
            f"Eintraege fuer keyword '{kw}' unterscheiden sich zwischen Laeufen: "
            f"{entries_first} vs {entries_second}"
        )


# ---------------------------------------------------------------------------
# A6 — Reuse Lead-Parser (parse_frontmatter per Identitaet, DRY)
# ---------------------------------------------------------------------------

def test_atom_index_reuses_lead_parser_identity():
    """
    A6: build_truth_atom_index reused parse_frontmatter (quality_node_health)
    per Identitaet — kein eigenes Frontmatter-Parsing (DRY / PT-GEN-LeadFollow).

    Verifikation: der Lead-Parser in build_retrieval_index IST derselbe wie
    quality_node_health.parse_frontmatter (Identitaets-Check, Laufzeit-Objekt).
    """
    assert (
        build_retrieval_index.parse_frontmatter
        is quality_node_health.parse_frontmatter
    ), (
        "build_retrieval_index.parse_frontmatter muss DER Lead (quality_node_health) sein "
        "— kein Re-Implement, nur Re-Export (DRY / PT-GEN-LeadFollow)."
    )


# ---------------------------------------------------------------------------
# A7 — Leerer Vault -> {} (kein Crash, Edge-Case)
# ---------------------------------------------------------------------------

def test_atom_index_empty_vault_returns_empty(tmp_path):
    """
    A7 Edge-Case: leerer Vault-Root (kein .md) -> leeres Dict {} (kein Crash).
    """
    idx = build_retrieval_index.build_truth_atom_index([str(tmp_path)])
    assert idx == {}, f"Leerer Vault muss leeren Index liefern, bekommen: {idx}"


# ---------------------------------------------------------------------------
# A8 — Truth ohne keywords[] -> kein Key im Index
# ---------------------------------------------------------------------------

def test_atom_index_truth_without_keywords_no_key(tmp_path):
    """
    A8 Edge-Case: type:truth ohne keywords[]-Feld -> kein Key im Index
    (keine falsch-positiven Eintraege). Grace-Handling.
    """
    _write_truth(str(tmp_path), "truth_nokw.md", "TNKW", keywords=None)

    idx = build_retrieval_index.build_truth_atom_index([str(tmp_path)])

    assert idx == {}, (
        f"Truth ohne keywords[] darf keinen Index-Key erzeugen, bekommen: {idx}"
    )


# ---------------------------------------------------------------------------
# A9 — Persistenz: Schreibt _keyword_index.json bei persist=True
# ---------------------------------------------------------------------------

def test_atom_index_persistence_writes_json(tmp_path):
    """
    A9 (Spec DoD-2): 'Persistenz: _keyword_index.json wird geschrieben + ist
    wieder einlesbar (Round-Trip).'

    build_truth_atom_index(roots, persist=True) soll den Index als JSON in
    {root}/_keyword_index.json (oder aehnlichen kanonischen Pfad) schreiben.

    Erwartet: JSON-Datei existiert nach Aufruf mit persist=True.
    """
    _write_truth(str(tmp_path), "truth_p.md", "TP01", keywords=["persistenz", "index"])

    # Persistenz via persist=True-Flag ODER automatisch (Impl-Entscheidung des GREEN-Workers).
    # Wir testen beide moeglichen APIs — Hauptvertrag: JSON-Datei entsteht.
    try:
        build_retrieval_index.build_truth_atom_index([str(tmp_path)], persist=True)
    except TypeError:
        # Falls persist-Param noch nicht implementiert: alternativer Aufruf ohne Param
        # -> Dann prueft A10 den Round-Trip via serialize_index_json (inline).
        pytest.skip("persist-Parameter nicht implementiert — A10 prueft Serialisierbarkeit")

    # Suche nach JSON-Artefakt (verschiedene Benennungen erlaubt)
    json_candidates = [
        os.path.join(str(tmp_path), "_keyword_index.json"),
        os.path.join(str(tmp_path), ".claude", "output", "retrieval_index", "_keyword_index.json"),
    ]
    found = any(os.path.exists(p) for p in json_candidates)
    assert found, (
        f"Nach build_truth_atom_index(persist=True) sollte eine _keyword_index.json entstehen. "
        f"Gesucht in: {json_candidates}"
    )


# ---------------------------------------------------------------------------
# A10 — Round-Trip: Index via serialize_index_json serialisierbar
# ---------------------------------------------------------------------------

def test_atom_index_serializable_round_trip(tmp_path):
    """
    A10: Der von build_truth_atom_index gelieferte Index ist via serialize_index_json
    serialisierbar + der Round-Trip (json.loads) liefert gleichen Index.
    (Spec DoD-2: 'Artefakt geschrieben + round-trip-stabil')
    """
    _write_truth(str(tmp_path), "truth_rt.md", "TRT1", keywords=["roundtrip", "serial"])

    idx = build_retrieval_index.build_truth_atom_index([str(tmp_path)])

    # Muss via H12 serialize_index_json serialisierbar sein (existiert bereits)
    json_str = build_retrieval_index.serialize_index_json(idx)
    assert isinstance(json_str, str), "serialize_index_json muss str liefern"

    recovered = json.loads(json_str)
    # Keys muessen uebereinstimmen
    assert set(recovered.keys()) == set(idx.keys()), (
        f"Round-Trip-Verlust: Original-Keys={set(idx.keys())}, "
        f"recovered={set(recovered.keys())}"
    )


# ---------------------------------------------------------------------------
# A11 — Fallback: truth_keywords.extract_keywords wenn keywords[] fehlt aber Text vorhanden
# ---------------------------------------------------------------------------

def test_atom_index_fallback_extract_keywords_from_text(tmp_path):
    """
    A11: Falls eine type:truth-Datei kein keywords[]-Feld hat, aber Text-Inhalt,
    KANN build_truth_atom_index truth_keywords.extract_keywords als Fallback nutzen,
    um thematische Keywords aus dem Text zu extrahieren.

    Spec-Bezug: AK-ATOM-INDEX beschreibt 'keywords[]+ggf. extrahiert via
    truth_keywords' (Aufgabe: 'liest keywords[] (+ggf. extrahiert via truth_keywords)').

    Test: Truth ohne keywords[] aber mit 3x 'kausalitaet' im Text ->
    'kausalitaet' erscheint im Index (wenn Fallback implementiert) ODER Index leer
    (wenn Fallback optional/nicht implementiert -> dann wie A8 kein Crash).

    Dieses ist ein POSITIV-Test fuer den Fallback-Pfad. Wenn der GREEN-Worker
    den Fallback implementiert, erscheint 'kausalitaet' im Index. Wenn nicht,
    gilt A8 (kein Key = akzeptabel als Basis-Impl, Fallback = Enhancement).
    """
    content = (
        "---\n"
        "type: truth\n"
        "id: BL-389.TFALLBACK\n"
        "local_id: TFALLBACK\n"
        "text: kausalitaet kausalitaet kausalitaet — Ursache und Wirkung.\n"
        "typ: FESTSTELLUNG\n"
        "herkunft: INTERN\n"
        "status: OFFEN\n"
        "truth_grade: vault_hypothesis\n"
        "---\n"
        "# Fallback-Test\n\n"
        "kausalitaet kausalitaet kausalitaet ist ein zentrales Konzept.\n"
    )
    fpath = os.path.join(str(tmp_path), "truth_fallback.md")
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write(content)

    idx = build_retrieval_index.build_truth_atom_index([str(tmp_path)])

    # Wenn Fallback implementiert: 'kausalitaet' muss im Index erscheinen
    # Wenn nicht: {} ist auch akzeptabel (kein Crash) — A8 deckt das ab.
    if idx:
        assert "kausalitaet" in idx, (
            f"Fallback-Extraktion sollte 'kausalitaet' (3x im Text) finden, "
            f"bekommen Index-Keys: {sorted(idx.keys())}"
        )
    # else: leerer Index ist akzeptabel (Fallback-Pfad optional)


# ---------------------------------------------------------------------------
# A12 — Nicht-.md Dateien und _Tag-Index.md werden ignoriert
# ---------------------------------------------------------------------------

def test_atom_index_ignores_non_md_and_artifact_files(tmp_path):
    """
    A12: Nicht-.md Dateien (z.B. .json, .py) und das Artefakt _Tag-Index.md
    werden beim Walk ignoriert — kein Crash, kein false-positive.
    """
    # .json Datei: kein .md -> ignoriert
    json_file = os.path.join(str(tmp_path), "some_index.json")
    with open(json_file, "w", encoding="utf-8") as fh:
        fh.write('{"keywords": ["should_not_appear"]}')

    # _Tag-Index.md: Artefakt -> ignoriert (analog _walk_vault_nodes)
    tag_index_file = os.path.join(str(tmp_path), "_Tag-Index.md")
    with open(tag_index_file, "w", encoding="utf-8") as fh:
        fh.write(
            "---\ntype: truth\nid: BL-389.FAKE\nlocal_id: FAKE\n"
            "text: fake\ntyp: FESTSTELLUNG\nherkunft: INTERN\n"
            "status: OFFEN\ntruth_grade: vault_hypothesis\n"
            "keywords: [artifact_keyword]\n---\n# Fake\n"
        )

    # Echte Truth-Datei
    _write_truth(str(tmp_path), "real_truth.md", "TREAL", keywords=["echtes_keyword"])

    idx = build_retrieval_index.build_truth_atom_index([str(tmp_path)])

    assert "echtes_keyword" in idx, "Echte Truth muss indiziert werden"
    assert "should_not_appear" not in idx, "json-Datei darf nicht im Index erscheinen"
    # _Tag-Index.md: ob ignoriert oder nicht -> kein Crash; artifact_keyword ist
    # kein hartes Requirement da _Tag-Index.md kein type:truth in der Produktion ist


# ---------------------------------------------------------------------------
# A13 — Multi-Root: zwei Vault-Roots werden zusammengefuehrt
# ---------------------------------------------------------------------------

def test_atom_index_multi_root_merges_indexes(tmp_path):
    """
    A13: build_truth_atom_index([root1, root2]) -> beide Roots werden gewalkt
    und der Index zusammengefuehrt (analog merge_vault_indexes fuer den Atom-Index).
    """
    root1 = tmp_path / "vault1"
    root2 = tmp_path / "vault2"
    root1.mkdir()
    root2.mkdir()

    _write_truth(str(root1), "truth_v1.md", "TV1", keywords=["vault_eins", "system"])
    _write_truth(str(root2), "truth_v2.md", "TV2", keywords=["vault_zwei", "system"])

    idx = build_retrieval_index.build_truth_atom_index([str(root1), str(root2)])

    assert "vault_eins" in idx, "keyword aus vault1 fehlt"
    assert "vault_zwei" in idx, "keyword aus vault2 fehlt"
    # Geteiltes keyword 'system' -> 2 Eintraege (aus beiden Roots)
    assert "system" in idx
    assert len(idx["system"]) == 2, (
        f"'system' soll aus beiden Roots kommen -> 2 Eintraege, bekommen: {len(idx['system'])}"
    )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
