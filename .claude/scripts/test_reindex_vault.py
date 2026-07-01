"""test_reindex_vault.py — BL-274 / batch_1 / M3 RED-Suite (test-first)

reindex_vault.py existiert NOCH NICHT. Diese Suite ist die SOLL-Spezifikation
(Kent Beck: "tests are specifications") fuer den Map-Reduce-Reindex-Orchestrator
ueber den fertigen BL-242-Primitiven (DRY, AK-1 / N6).

Scope batch_1 = die 9 Orchestrierungs-AKs (AK-1, AK-4..AK-11). AK-2 (cut_sections)
und AK-3 (_derive_map_slots) sind SB-2 bereits in build_retrieval_index.py gebaut
und werden hier nur als REUSE-Substrat importiert (nicht neu definiert).

Erwartete Orchestrator-API (durch diese Tests definiert):
  reindex_vault(vault_root, budget=1, resume=False) -> dict
    Orchestriert MAP -> REDUCE(tree, unter factory_lock) -> PERSIST.
    Ruft ausschliesslich existierende Primitive (build_index / merge_vault_indexes /
    serialize_index_json / factory_lock.acquire/release). Rueckgabe = das finale
    built-Index-Dict.
  tree_merge_indexes(part_indexes) -> dict
    Baumartige (paarweise) Faltung ueber merge_vault_indexes (AK-4).
  verify_clean_state(index, vault_files) -> dict
    Coverage (AK-9) UND stale-Eviction (AK-10) -> UND-Verknuepfung (AK-11).

Mock-Grenze: KEIN echter Vault-Write ausserhalb tmp_path. factory_lock-Aufrufe
werden via monkeypatch beobachtet (Lock-Vertrag, nicht reale Datei-Kontention).
"""

import ast
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

# M3 test-first: dieser Import schlaegt JETZT fehl (Modul GREENFIELD-NEU, FEHLT)
# -> Collection-Error = RED (Gesetz 2: Import-Fehler zaehlt als Fehlschlag).
import reindex_vault  # noqa: E402

# REUSE-Substrat (BL-242 / SB-2) — existiert bereits, NICHT neu zu bauen.
import build_retrieval_index  # noqa: E402
import factory_lock  # noqa: E402


# ===========================================================================
# Fixtures — tmp-Vault (kein echter Vault-Write)
# ===========================================================================

def _write_md(root, relpath, frontmatter_keywords=None, tags=None, body=""):
    """Schreibt ein .md-File mit YAML-Frontmatter in den tmp-Vault."""
    fpath = os.path.join(root, relpath)
    os.makedirs(os.path.dirname(fpath), exist_ok=True)
    lines = ["---"]
    if frontmatter_keywords:
        lines.append("keywords: [{}]".format(", ".join(frontmatter_keywords)))
    if tags:
        lines.append("tags: [{}]".format(", ".join(tags)))
    lines.append("---")
    lines.append("")
    lines.append(body)
    with open(fpath, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return fpath


@pytest.fixture
def tmp_vault(tmp_path):
    """Minimaler tmp-Vault mit >=2 Top-Level-Dirs (>=2 Sektionen, AK-1/AK-2)."""
    root = str(tmp_path)
    _write_md(root, "dirA/node1.md", frontmatter_keywords=["alpha"], tags=["topic/x"])
    _write_md(root, "dirB/node2.md", frontmatter_keywords=["beta"], tags=["topic/y"])
    return root


# ===========================================================================
# AK-1 — reindex_vault() Orchestrator existiert + DRY ueber BL-242-Primitive
# ===========================================================================

def test_ak1_reindex_vault_callable_exists():
    """AK-1: reindex_vault ist eine aufrufbare Orchestrator-Funktion."""
    assert hasattr(reindex_vault, "reindex_vault"), \
        "reindex_vault() Orchestrator muss existieren"
    assert callable(reindex_vault.reindex_vault)


def test_ak1_reuses_bl242_primitives_no_redefinition():
    """AK-1 / N6 (DRY): reindex_vault definiert KEINE der BL-242/BL-194-Primitive
    neu — kein eigenes build_index / merge_vault_indexes / serialize_index_json /
    Lock-Code. Statische AST-Pruefung: diese Namen sind im Modul NICHT als
    Funktion top-level definiert (nur importiert/aufgerufen)."""
    src_path = reindex_vault.__file__
    with open(src_path, "r", encoding="utf-8") as fh:
        tree = ast.parse(fh.read(), filename=src_path)
    defined = {
        n.name for n in ast.walk(tree)
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    forbidden = {
        "build_index", "merge_vault_indexes", "serialize_index_json",
        "acquire", "release", "compute_coverage",
    }
    leaked = forbidden & defined
    assert not leaked, \
        "DRY-Verstoss: Primitive duerfen nicht neu definiert werden, gefunden: {}".format(leaked)


def test_ak1_orchestrator_calls_build_index_per_section(tmp_vault, monkeypatch):
    """AK-1: der Orchestrator ruft build_index (MAP) ueber die Primitive auf —
    nachweisbar durch einen Spy auf build_index (kein eigener Walk)."""
    calls = []
    real_build = build_retrieval_index.build_index

    def spy_build_index(roots):
        calls.append(list(roots))
        return real_build(roots)

    monkeypatch.setattr(build_retrieval_index, "build_index", spy_build_index)
    # Falls reindex_vault build_index per from-import gebunden hat, auch dort patchen:
    if hasattr(reindex_vault, "build_index"):
        monkeypatch.setattr(reindex_vault, "build_index", spy_build_index)

    reindex_vault.reindex_vault(tmp_vault, budget=1)
    assert calls, "reindex_vault muss build_index (MAP) ueber die Primitive aufrufen"


def test_ak1_returns_index_dict_with_expected_shape(tmp_vault):
    """AK-1: Rueckgabe ist das finale built-Index-Dict (D2-Form: keyword_index
    etc.), das aus dem Merge der Sektionen entsteht."""
    result = reindex_vault.reindex_vault(tmp_vault, budget=1)
    assert isinstance(result, dict)
    assert "keyword_index" in result, "Index muss keyword_index (D2-Form) enthalten"


# ===========================================================================
# AK-4 — REDUCE: baumartiger paarweiser Merge (tree-merge)
# ===========================================================================

def test_ak4_tree_merge_helper_exists():
    """AK-4: ein baumartiger Merge-Reducer existiert (tree_merge_indexes)."""
    assert hasattr(reindex_vault, "tree_merge_indexes"), \
        "tree_merge_indexes (baumartiger Reducer) muss existieren"
    assert callable(reindex_vault.tree_merge_indexes)


def test_ak4_tree_merge_equals_linear_accumulation():
    """AK-4: baumartiges Merge-Ergebnis == lineare Akkumulation
    (Merge-Assoziativitaet). Mehrere Teil-Indizes -> identisches Ergebnis."""
    parts = [
        {"kw": [{"path": "a", "id": 1}]},
        {"kw": [{"path": "b", "id": 2}]},
        {"kw": [{"path": "c", "id": 3}]},
        {"kw": [{"path": "d", "id": 4}]},
        {"kw": [{"path": "e", "id": 5}]},
    ]
    # Lineare Referenz ueber das Primitiv:
    linear = {}
    for p in parts:
        linear = build_retrieval_index.merge_vault_indexes(linear, p)

    tree = reindex_vault.tree_merge_indexes(parts)
    # Eintrags-Menge muss identisch sein (Reihenfolge-tolerant):
    assert sorted(e["id"] for e in tree["kw"]) == sorted(e["id"] for e in linear["kw"]), \
        "Tree-Merge muss dasselbe Eintrags-Set liefern wie lineare Akkumulation"


def test_ak4_tree_merge_is_pairwise_not_serial_accumulative():
    """AK-4: Faltung ist baumartig/paarweise (Tiefe ~ceil(log2 N)), NICHT
    seriell-akkumulativ (N-1 Merges auf einem wachsenden Akkumulator).

    Wir beobachten die Operanden-Groessen jedes merge_vault_indexes-Aufrufs:
    seriell-akkumulativ -> der linke Operand waechst monoton (1,2,3,4...).
    baumartig -> es gibt mindestens einen Merge zweier bereits gemergter Paare
    (beide Operanden > 1 Eintrag), was die serielle Akkumulation NIE erzeugt.
    """
    parts = [{"kw": [{"path": chr(97 + i), "id": i}]} for i in range(4)]
    operand_sizes = []
    real_merge = build_retrieval_index.merge_vault_indexes

    def spy_merge(a, b):
        a_n = len((a or {}).get("kw", []))
        b_n = len((b or {}).get("kw", []))
        operand_sizes.append((a_n, b_n))
        return real_merge(a, b)

    # tree_merge_indexes muss merge_vault_indexes ueber das Primitiv-Modul nutzen:
    import unittest.mock as mock
    with mock.patch.object(build_retrieval_index, "merge_vault_indexes", spy_merge):
        if hasattr(reindex_vault, "merge_vault_indexes"):
            with mock.patch.object(reindex_vault, "merge_vault_indexes", spy_merge):
                reindex_vault.tree_merge_indexes(parts)
        else:
            reindex_vault.tree_merge_indexes(parts)

    # Baumartig: mindestens ein Merge hat BEIDE Operanden mit >=2 (Paar-von-Paaren).
    # Seriell-akkumulativ kann das nie: der rechte Operand ist immer eine frische
    # Einzel-Sektion (1 Eintrag).
    pair_of_pairs = any(a >= 2 and b >= 2 for (a, b) in operand_sizes)
    assert pair_of_pairs, (
        "REDUCE muss baumartig (Paar-von-Paaren) sein, nicht seriell-akkumulativ; "
        "beobachtete Operanden-Groessen: {}".format(operand_sizes)
    )


# ===========================================================================
# AK-5 — REDUCE: Index-Lock (nur EIN Merge schreibt zur Zeit)
# ===========================================================================

def test_ak5_acquires_and_releases_lock_around_merge_write(tmp_vault, monkeypatch):
    """AK-5: jeder Merge-Schritt auf den Ziel-Index laeuft unter factory_lock —
    acquire VOR dem Merge-Write, release DANACH. Wir beobachten die Reihenfolge
    der Lock-Events."""
    events = []
    real_acquire = factory_lock.acquire
    real_release = factory_lock.release

    def spy_acquire(*args, **kwargs):
        events.append("acquire")
        return True  # Lock simuliert erworben

    def spy_release(*args, **kwargs):
        events.append("release")
        return True

    monkeypatch.setattr(factory_lock, "acquire", spy_acquire)
    monkeypatch.setattr(factory_lock, "release", spy_release)
    if hasattr(reindex_vault, "acquire"):
        monkeypatch.setattr(reindex_vault, "acquire", spy_acquire)
    if hasattr(reindex_vault, "release"):
        monkeypatch.setattr(reindex_vault, "release", spy_release)

    reindex_vault.reindex_vault(tmp_vault, budget=1)

    assert "acquire" in events, "factory_lock.acquire muss vor dem Merge-Write gerufen werden"
    assert "release" in events, "factory_lock.release muss nach dem Merge-Write gerufen werden"
    assert events.index("acquire") < events.index("release"), \
        "Lock-Reihenfolge muss acquire -> release sein (single-writer)"


def test_ak5_lock_uses_reindex_purpose_scope(tmp_vault, monkeypatch):
    """AK-5: der Lock wird mit einem REINDEX-Zweck/scope erworben (factory_lock-Stil,
    SA-4 ein globaler scope). Wir pruefen, dass acquire mit purpose/scope aufgerufen
    wird (kein neuer Lock-Code, Reuse)."""
    captured = {}

    def spy_acquire(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return True

    monkeypatch.setattr(factory_lock, "acquire", spy_acquire)
    monkeypatch.setattr(factory_lock, "release", lambda *a, **k: True)
    if hasattr(reindex_vault, "acquire"):
        monkeypatch.setattr(reindex_vault, "acquire", spy_acquire)

    reindex_vault.reindex_vault(tmp_vault, budget=1)

    assert "args" in captured, "factory_lock.acquire muss aufgerufen worden sein"
    # SA-4: ein benannter Zweck/scope fuer den Reindex (purpose oder scope getragen)
    blob = " ".join(str(captured["args"])) + " " + str(captured["kwargs"])
    assert "REINDEX" in blob.upper() or "scope" in captured["kwargs"] or "purpose" in captured["kwargs"], \
        "Lock muss mit erkennbarem REINDEX-purpose/scope erworben werden (SA-4)"


# ===========================================================================
# AK-6 — REDUCE: Dedup von Ueberlappung beim Merge
# ===========================================================================

def test_ak6_overlapping_sections_dedup_to_single_entry():
    """AK-6: ueberlappende Sektionen erzeugen Doppel-Eintraege; nach dem Merge
    enthaelt der finale Index den Eintrag genau EINMAL pro Eintrags-Identitaet
    (SA-2: Dedup-Key = Eintrags-Identitaet)."""
    # Zwei Teil-Indizes mit einem ueberlappenden (identischen) Eintrag:
    overlap_entry = {"path": "shared.md", "bl_id": "BL-1", "vault_origin": "v",
                     "node_type": "spec"}
    part_a = {"kw": [overlap_entry, {"path": "a.md", "bl_id": "BL-2",
                                     "vault_origin": "v", "node_type": "spec"}]}
    part_b = {"kw": [dict(overlap_entry), {"path": "b.md", "bl_id": "BL-3",
                                           "vault_origin": "v", "node_type": "spec"}]}

    merged = reindex_vault.tree_merge_indexes([part_a, part_b])
    shared = [e for e in merged["kw"] if e.get("path") == "shared.md"]
    assert len(shared) == 1, \
        "Ueberlappender Eintrag muss genau einmal vorkommen (Dedup, AK-6), nicht {}".format(len(shared))


# ===========================================================================
# AK-7 — PERSIST: deterministischer, _W_fetch-lesbarer JSON-Index
# ===========================================================================

def test_ak7_persist_is_deterministic_byte_identical(tmp_vault):
    """AK-7 / N3: zwei Reindex-Laeufe auf identischem Vault-Stand erzeugen
    bit-identisches JSON (serialize_index_json sort_keys=True)."""
    reindex_vault.reindex_vault(tmp_vault, budget=1)
    out_dir = os.path.join(tmp_vault, ".claude", "output", "retrieval_index")
    fpath = os.path.join(out_dir, "_keyword_index.json")
    assert os.path.exists(fpath), "PERSIST muss den JSON-Index ablegen ({})".format(fpath)
    with open(fpath, "r", encoding="utf-8") as fh:
        first = fh.read()

    reindex_vault.reindex_vault(tmp_vault, budget=1)
    with open(fpath, "r", encoding="utf-8") as fh:
        second = fh.read()

    assert first == second, "PERSIST muss deterministisch (bit-identisch) sein (AK-7/N3)"


def test_ak7_persisted_json_is_wfetch_loadable(tmp_vault):
    """AK-7: der persistierte Index ist valides, ladbares JSON (serialize_index_json
    -> _W_fetch-lesbar, Index-First-Read)."""
    import json
    reindex_vault.reindex_vault(tmp_vault, budget=1)
    out_dir = os.path.join(tmp_vault, ".claude", "output", "retrieval_index")
    fpath = os.path.join(out_dir, "_keyword_index.json")
    with open(fpath, "r", encoding="utf-8") as fh:
        loaded = json.load(fh)  # wirft bei kaputtem JSON
    assert isinstance(loaded, dict), "Persistierter Index muss als JSON-dict ladbar sein"


# ===========================================================================
# AK-8 — RESUME: persistierte Sektion wird bei Abbruch NICHT neu gebaut
# ===========================================================================

def test_ak8_resume_skips_already_persisted_section(tmp_vault, monkeypatch):
    """AK-8: GIVEN ein Reindex mit bereits persistierter Sektion WHEN mit
    resume=True wieder aufgenommen THEN wird die persistierte Sektion NICHT neu
    gebaut (build_index wird fuer sie nicht erneut gerufen)."""
    # Erst-Lauf: baut + persistiert alle Sektionen + committed Resume-Cursor.
    reindex_vault.reindex_vault(tmp_vault, budget=1)

    sections = build_retrieval_index.cut_sections([tmp_vault])
    # Mindestens eine Sektion muss als persistiert markiert sein nach dem 1. Lauf:
    built_sections = []
    real_build = build_retrieval_index.build_index

    def spy_build_index(roots):
        built_sections.append(list(roots))
        return real_build(roots)

    monkeypatch.setattr(build_retrieval_index, "build_index", spy_build_index)
    if hasattr(reindex_vault, "build_index"):
        monkeypatch.setattr(reindex_vault, "build_index", spy_build_index)

    # Resume-Lauf: keine Sektion darf neu gebaut werden (alle bereits persistiert).
    reindex_vault.reindex_vault(tmp_vault, budget=1, resume=True)
    assert built_sections == [], (
        "RESUME darf bereits persistierte Sektionen NICHT neu bauen; "
        "neu gebaut wurde aber: {}".format(built_sections)
    )


def test_ak8_resume_cursor_persisted_in_index_dir(tmp_vault):
    """AK-8 / SA-6: der Resume-Cursor liegt committed im persistierten
    Index-Verzeichnis (nicht nur transient). Nach einem Lauf existiert ein
    committed Cursor-Artefakt."""
    reindex_vault.reindex_vault(tmp_vault, budget=1)
    out_dir = os.path.join(tmp_vault, ".claude", "output", "retrieval_index")
    # Der Orchestrator persistiert einen Sektions-Cursor (Liste fertiger Sektionen).
    assert hasattr(reindex_vault, "read_resume_cursor"), \
        "read_resume_cursor (committed Cursor-Read, SA-6) muss existieren"
    cursor = reindex_vault.read_resume_cursor(out_dir)
    assert cursor, "Resume-Cursor muss nach einem Lauf fertige Sektionen enthalten (SA-6)"


# ===========================================================================
# AK-9 — CLEAN-STATE: Coverage-Verifikation (Haelfte 1)
# ===========================================================================

def test_ak9_verify_clean_state_coverage_ok_when_full():
    """AK-9: verify_clean_state meldet coverage_ok=True wenn jeder Vault-Knoten
    im Index repraesentiert ist (missing=leer)."""
    index_files = [{"path": "a.md", "keywords": ["x"]},
                   {"path": "b.md", "keywords": ["y"]}]
    vault_files = ["a.md", "b.md"]
    result = reindex_vault.verify_clean_state(index_files, vault_files)
    assert isinstance(result, dict)
    assert result.get("coverage_ok") is True, \
        "Bei voller Abdeckung muss coverage_ok True sein (AK-9)"


def test_ak9_verify_clean_state_coverage_fails_when_missing():
    """AK-9: fehlt ein Vault-Knoten im Index -> coverage_ok=False."""
    index_files = [{"path": "a.md", "keywords": ["x"]}]
    vault_files = ["a.md", "b.md"]  # b.md fehlt im Index
    result = reindex_vault.verify_clean_state(index_files, vault_files)
    assert result.get("coverage_ok") is False, \
        "Fehlender Vault-Knoten muss coverage_ok False setzen (AK-9)"


# ===========================================================================
# AK-10 — CLEAN-STATE: stale-Eviction-Verifikation (Haelfte 2)
# ===========================================================================

def test_ak10_stale_eviction_ok_when_no_dead_entry():
    """AK-10: jeder Index-Eintrags-Quellpfad existiert im aktuellen Vault-Walk
    -> stale_evicted_ok=True (stale-Set leer)."""
    index_files = [{"path": "a.md"}, {"path": "b.md"}]
    vault_files = ["a.md", "b.md"]
    result = reindex_vault.verify_clean_state(index_files, vault_files)
    assert result.get("stale_evicted_ok") is True, \
        "Ohne tote Eintraege muss stale_evicted_ok True sein (AK-10)"


def test_ak10_stale_eviction_fails_when_dead_entry_present():
    """AK-10: ein Index-Eintrag referenziert eine geloeschte (nicht mehr im Walk
    vorhandene) Quelle -> stale_evicted_ok=False."""
    index_files = [{"path": "a.md"}, {"path": "gone.md"}]  # gone.md geloescht
    vault_files = ["a.md"]
    result = reindex_vault.verify_clean_state(index_files, vault_files)
    assert result.get("stale_evicted_ok") is False, \
        "Toter Index-Eintrag muss stale_evicted_ok False setzen (AK-10)"


# ===========================================================================
# AK-11 — CLEAN-STATE: clean = Coverage UND stale-Eviction (Wahrheitstabelle)
# ===========================================================================

def test_ak11_clean_state_true_only_when_both_green():
    """AK-11: clean_state=True nur wenn coverage_ok UND stale_evicted_ok beide
    True sind (UND-Verknuepfung)."""
    index_files = [{"path": "a.md", "keywords": ["x"]},
                   {"path": "b.md", "keywords": ["y"]}]
    vault_files = ["a.md", "b.md"]
    result = reindex_vault.verify_clean_state(index_files, vault_files)
    assert result.get("clean_state") is True, \
        "Coverage gruen UND stale gruen -> clean_state True (AK-11)"


@pytest.mark.parametrize("index_files,vault_files,expected", [
    # Coverage rot (b.md fehlt im Index) -> clean False
    ([{"path": "a.md", "keywords": ["x"]}], ["a.md", "b.md"], False),
    # stale rot (gone.md tot) -> clean False
    ([{"path": "a.md", "keywords": ["x"]}, {"path": "gone.md", "keywords": ["z"]}],
     ["a.md"], False),
    # beide gruen -> clean True
    ([{"path": "a.md", "keywords": ["x"]}], ["a.md"], True),
])
def test_ak11_clean_state_truth_table(index_files, vault_files, expected):
    """AK-11: vollstaendige UND-Wahrheitstabelle (eine rot -> clean False)."""
    result = reindex_vault.verify_clean_state(index_files, vault_files)
    assert result.get("clean_state") is expected, \
        "clean_state-Wahrheitstabelle verletzt: erwartet {}".format(expected)
