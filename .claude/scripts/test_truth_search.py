"""test_truth_search.py — RED tests fuer truth_search.py (BL-389 batch_3, AK-WFETCH-ATOMS DoD-3).

NUR test-first. truth_search.py existiert NICHT (RED-Phase, RED!=GREEN).
Target API:
  search_truths(query: str, atom_index: dict) -> list[dict]
  oder:
  search_truths(query: str, roots: list) -> list[dict]

Semantik:
  - thematische Query (Freitext) -> extract_keywords -> Lookup im atom_index
  - Ergebnis: rankte Truth-Atome [{path, bl_id, vault_origin, node_type, score}, ...]
  - Mehr keyword-Treffer = hoeher gerankt (score = Anzahl matching keywords)
  - leere/no-match Query -> []
  - deterministisch (gleicher Input -> gleicher Output)

Import: truth_search.search_truths
Reuse: build_retrieval_index.build_truth_atom_index + truth_keywords.extract_keywords
"""

import os
import sys
import tempfile

import pytest

# Sicherstellen, dass .claude/scripts im Pfad ist (fuer imports)
_SCRIPTS = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS not in sys.path:
    sys.path.insert(0, _SCRIPTS)

# ---- Fixtures ---------------------------------------------------------------

# Atom-Index Shape (aus build_truth_atom_index):
# {keyword: [{path, bl_id, vault_origin, node_type}, ...]}

_ATOM_A = {"path": "truths/tdd-regel.md", "bl_id": "BL-100", "vault_origin": "/vault", "node_type": "truth"}
_ATOM_B = {"path": "truths/tdd-fehler.md", "bl_id": "BL-101", "vault_origin": "/vault", "node_type": "truth"}
_ATOM_C = {"path": "truths/agile-sprint.md", "bl_id": "BL-102", "vault_origin": "/vault", "node_type": "truth"}

_SMALL_INDEX = {
    "tdd":      [_ATOM_A, _ATOM_B],
    "test":     [_ATOM_A],
    "fehler":   [_ATOM_B],
    "agile":    [_ATOM_C],
    "sprint":   [_ATOM_C],
    "regel":    [_ATOM_A],
}


def _make_truth_md(keywords, bl_id="BL-TEST", text=""):
    """Erzeugt Inhalt einer type:truth .md Datei fuer tmp-Korpus."""
    kw_yaml = "\n".join(f"  - {k}" for k in keywords)
    return (
        "---\n"
        "type: truth\n"
        f"bl: {bl_id}\n"
        "node_type: truth\n"
        "keywords:\n"
        f"{kw_yaml}\n"
        "---\n"
        f"{text}\n"
    )


# ---- Import target (muss fehlschlagen -> RED) --------------------------------

def _import_search_truths():
    """Versucht search_truths zu importieren; gibt Funktion oder None zurueck."""
    try:
        from truth_search import search_truths  # noqa: F401
        return search_truths
    except ImportError:
        return None


# ---- Tests -------------------------------------------------------------------

class TestTruthSearchImport:
    """Stellt sicher, dass das Modul existiert und search_truths exportiert."""

    def test_search_truths_importierbar(self):
        """truth_search.search_truths muss importierbar sein."""
        fn = _import_search_truths()
        assert fn is not None, (
            "truth_search.search_truths nicht importierbar — Modul truth_search.py fehlt (RED erwartet)"
        )

    def test_search_truths_ist_callable(self):
        """search_truths muss callable sein."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"
        assert callable(fn), "search_truths ist kein Callable"


class TestSearchTruthsKeywordMatch:
    """Thematische Query findet thematisch passende Truth-Atome via keyword-Match."""

    def test_search_query_tdd_findet_tdd_atome(self):
        """Query 'tdd' findet Atome mit keyword 'tdd' im Index."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("tdd", atom_index=_SMALL_INDEX)
        paths = [r["path"] for r in results]

        assert _ATOM_A["path"] in paths, f"tdd-regel.md muss in Ergebnis sein, got: {paths}"
        assert _ATOM_B["path"] in paths, f"tdd-fehler.md muss in Ergebnis sein, got: {paths}"

    def test_search_query_einzelwort_findet_exakten_atom(self):
        """Query 'fehler' findet genau den Atom mit keyword 'fehler'."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("fehler", atom_index=_SMALL_INDEX)
        paths = [r["path"] for r in results]

        assert _ATOM_B["path"] in paths, f"tdd-fehler.md muss gefunden werden, got: {paths}"
        assert _ATOM_C["path"] not in paths, f"agile-sprint.md darf NICHT gefunden werden, got: {paths}"

    def test_search_query_mehrwoertig_findet_alle_passenden_atome(self):
        """Query 'tdd test' findet alle Atome die mindestens eines der keywords matchen."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("tdd test", atom_index=_SMALL_INDEX)
        paths = [r["path"] for r in results]

        # tdd-regel.md hat beide keywords 'tdd' und 'test' -> muss drin sein
        assert _ATOM_A["path"] in paths, f"tdd-regel.md (match tdd+test) muss in Ergebnis sein, got: {paths}"
        # tdd-fehler.md hat 'tdd' -> auch drin
        assert _ATOM_B["path"] in paths, f"tdd-fehler.md (match tdd) muss in Ergebnis sein, got: {paths}"


class TestSearchTruthsRanking:
    """Mehr keyword-Treffer = hoeher gerankt (score-basiert)."""

    def test_mehr_treffer_hoeher_gerankt(self):
        """Atom mit 2 keyword-Treffern steht vor Atom mit 1 Treffer."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        # Query 'tdd test': _ATOM_A hat beide keywords (tdd + test), _ATOM_B nur tdd
        results = fn("tdd test", atom_index=_SMALL_INDEX)
        assert len(results) >= 2, f"Erwarte mind. 2 Ergebnisse, got: {results}"

        paths = [r["path"] for r in results]
        idx_a = paths.index(_ATOM_A["path"])
        idx_b = paths.index(_ATOM_B["path"])
        assert idx_a < idx_b, (
            f"tdd-regel.md (2 Treffer) muss vor tdd-fehler.md (1 Treffer) stehen; "
            f"got Reihenfolge: {paths}"
        )

    def test_score_feld_vorhanden_und_positiv(self):
        """Jeder Treffer traegt ein 'score'-Feld >= 1."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("tdd", atom_index=_SMALL_INDEX)
        assert results, "Erwarte mindestens einen Treffer fuer 'tdd'"
        for r in results:
            assert "score" in r, f"'score'-Feld fehlt in Ergebnis-Eintrag: {r}"
            assert r["score"] >= 1, f"score muss >= 1 sein, got: {r['score']}"

    def test_score_steigt_mit_trefferzahl(self):
        """Atom mit 2 keyword-Matches hat score >= score des Atoms mit 1 Match."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("tdd test", atom_index=_SMALL_INDEX)
        by_path = {r["path"]: r for r in results}

        assert _ATOM_A["path"] in by_path, "tdd-regel.md (2 Treffer) muss in Ergebnis sein"
        assert _ATOM_B["path"] in by_path, "tdd-fehler.md (1 Treffer) muss in Ergebnis sein"

        score_a = by_path[_ATOM_A["path"]]["score"]
        score_b = by_path[_ATOM_B["path"]]["score"]
        assert score_a >= score_b, (
            f"Atom mit 2 Treffern muss score >= Atom mit 1 Treffer haben: {score_a} vs {score_b}"
        )


class TestSearchTruthsEmptyAndNoMatch:
    """Leere/no-match Queries geben [] zurueck (kein Crash)."""

    def test_leere_query_gibt_leeres_ergebnis(self):
        """Leere Query -> []."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("", atom_index=_SMALL_INDEX)
        assert results == [], f"Leere Query muss [] liefern, got: {results}"

    def test_nur_stopwoerter_query_gibt_leeres_ergebnis(self):
        """Query aus reinen Stopwoertern -> []."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("und der die das", atom_index=_SMALL_INDEX)
        assert results == [], f"Stopwort-Query muss [] liefern, got: {results}"

    def test_kein_match_query_gibt_leeres_ergebnis(self):
        """Query mit unbekanntem Begriff -> []."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("xyzAbcNichtImIndex123", atom_index=_SMALL_INDEX)
        assert results == [], f"No-Match Query muss [] liefern, got: {results}"

    def test_leerer_index_gibt_leeres_ergebnis(self):
        """Leerer atom_index -> []."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("tdd", atom_index={})
        assert results == [], f"Leerer Index muss [] liefern, got: {results}"

    def test_kein_crash_bei_none_index(self):
        """None als atom_index fuehrt nicht zu einem Crash (graceful [])."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        # Kein Exception erwartet
        try:
            results = fn("tdd", atom_index=None)
            assert results == [], f"None-Index muss [] liefern, got: {results}"
        except TypeError as exc:
            pytest.fail(f"search_truths crashed mit TypeError bei atom_index=None: {exc}")


class TestSearchTruthsDeterminism:
    """Gleicher Input -> identischer Output (deterministisch)."""

    def test_zweimaliger_aufruf_identisch(self):
        """Zweimaliger Aufruf mit identischem Query + Index -> identische Ergebnisliste."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        r1 = fn("tdd test regel", atom_index=_SMALL_INDEX)
        r2 = fn("tdd test regel", atom_index=_SMALL_INDEX)
        assert r1 == r2, f"Deterministisch erwartet: r1={r1} != r2={r2}"

    def test_reihenfolge_deterministisch_bei_gleichem_score(self):
        """Bei Gleichstand (gleicher score) ist die Reihenfolge deterministisch (alphabetisch nach path)."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        # Beide Atome haben score=1 (je 1 Treffer auf 'agile'/'sprint')
        index = {
            "agile": [_ATOM_C],
            "thema": [_ATOM_C],
        }
        r1 = fn("agile", atom_index=index)
        r2 = fn("agile", atom_index=index)
        assert r1 == r2, f"Deterministisch erwartet auch bei Gleichstand: r1={r1} != r2={r2}"


class TestSearchTruthsResultShape:
    """Ergebnis-Eintraege haben die erwarteten Felder (path, bl_id, vault_origin, node_type, score)."""

    def test_result_eintrag_hat_pflichtfelder(self):
        """Jeder Treffer-Eintrag hat path, bl_id, vault_origin, node_type, score."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("tdd", atom_index=_SMALL_INDEX)
        assert results, "Erwarte Treffer fuer 'tdd'"

        for r in results:
            for field in ("path", "bl_id", "vault_origin", "node_type", "score"):
                assert field in r, f"Pflichtfeld '{field}' fehlt in Ergebnis: {r}"

    def test_path_feld_ist_string(self):
        """path-Feld ist immer ein String."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("tdd", atom_index=_SMALL_INDEX)
        for r in results:
            assert isinstance(r["path"], str), f"path muss str sein, got: {type(r['path'])}"

    def test_score_feld_ist_numerisch(self):
        """score-Feld ist int oder float."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        results = fn("tdd", atom_index=_SMALL_INDEX)
        for r in results:
            assert isinstance(r["score"], (int, float)), (
                f"score muss int/float sein, got: {type(r['score'])}"
            )


class TestSearchTruthsWithTmpCorpus:
    """Integration: search_truths auf realem tmp-Korpus via build_truth_atom_index (roots-Variante)."""

    def test_search_via_roots_findet_truth_atom(self):
        """search_truths(query, roots=[...]) walkt Vault live und findet passenden Truth-Atom."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Truth-Datei anlegen
            truth_path = os.path.join(tmpdir, "wahrheit_tdd.md")
            with open(truth_path, "w", encoding="utf-8") as fh:
                fh.write(_make_truth_md(["tdd", "test", "qualitaet"], bl_id="BL-T1"))

            # Nicht-Truth-Datei anlegen (darf nicht gefunden werden)
            other_path = os.path.join(tmpdir, "notizen.md")
            with open(other_path, "w", encoding="utf-8") as fh:
                fh.write("---\ntype: note\n---\nblah tdd test\n")

            results = fn("tdd test", roots=[tmpdir])
            paths = [r["path"] for r in results]

            # wahrheit_tdd.md (type:truth) muss gefunden werden
            found = any("wahrheit_tdd" in p for p in paths)
            assert found, f"wahrheit_tdd.md muss gefunden werden, got paths: {paths}"

    def test_search_via_roots_ignoriert_nicht_truth_dateien(self):
        """search_truths via roots-Variante gibt NUR type:truth-Atome zurueck."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Truth-Datei
            truth_path = os.path.join(tmpdir, "wahrheit.md")
            with open(truth_path, "w", encoding="utf-8") as fh:
                fh.write(_make_truth_md(["architektur", "design"], bl_id="BL-T2"))

            # Note-Datei mit gleichen keywords (soll NICHT gefunden werden)
            note_path = os.path.join(tmpdir, "notiz.md")
            with open(note_path, "w", encoding="utf-8") as fh:
                fh.write(
                    "---\ntype: note\nkeywords:\n  - architektur\n  - design\n---\ntext\n"
                )

            results = fn("architektur", roots=[tmpdir])
            # Alle Ergebnisse muessen node_type == 'truth' haben (oder path ~ 'wahrheit')
            for r in results:
                assert r.get("node_type") == "truth" or "wahrheit" in r.get("path", ""), (
                    f"Nicht-Truth-Atom im Ergebnis: {r}"
                )

    def test_search_via_roots_leer_wenn_keine_truths(self):
        """Leerer Korpus (keine type:truth-Dateien) -> []."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        with tempfile.TemporaryDirectory() as tmpdir:
            results = fn("tdd", roots=[tmpdir])
            assert results == [], f"Leerer Korpus muss [] liefern, got: {results}"

    def test_search_via_roots_mehrere_truths_ranking(self):
        """Zwei Truths: die mit mehr keyword-Treffern steht vorne."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Truth A: 2 passende keywords
            truth_a = os.path.join(tmpdir, "truth_a.md")
            with open(truth_a, "w", encoding="utf-8") as fh:
                fh.write(_make_truth_md(["tdd", "test"], bl_id="BL-A"))

            # Truth B: nur 1 passendes keyword
            truth_b = os.path.join(tmpdir, "truth_b.md")
            with open(truth_b, "w", encoding="utf-8") as fh:
                fh.write(_make_truth_md(["tdd", "architektur"], bl_id="BL-B"))

            results = fn("tdd test", roots=[tmpdir])
            assert len(results) >= 2, f"Erwarte mind. 2 Treffer, got: {results}"

            # Truth A (tdd + test = 2 Treffer) muss vorne sein
            paths = [r["path"] for r in results]
            idx_a = next((i for i, p in enumerate(paths) if "truth_a" in p), None)
            idx_b = next((i for i, p in enumerate(paths) if "truth_b" in p), None)
            assert idx_a is not None, f"truth_a nicht in Ergebnissen: {paths}"
            assert idx_b is not None, f"truth_b nicht in Ergebnissen: {paths}"
            assert idx_a < idx_b, (
                f"truth_a (2 Treffer) muss vor truth_b (1 Treffer) stehen; got: {paths}"
            )


class TestSearchTruthsApiSignature:
    """Beide API-Varianten werden akzeptiert: atom_index-kwarg UND roots-kwarg."""

    def test_atom_index_kwarg_akzeptiert(self):
        """search_truths(query, atom_index={...}) laeuft ohne TypeError."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        try:
            fn("tdd", atom_index=_SMALL_INDEX)
        except TypeError as exc:
            pytest.fail(f"atom_index-kwarg fuehrt zu TypeError: {exc}")

    def test_roots_kwarg_akzeptiert(self):
        """search_truths(query, roots=[...]) laeuft ohne TypeError."""
        fn = _import_search_truths()
        assert fn is not None, "truth_search.search_truths nicht importierbar (RED)"

        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                fn("tdd", roots=[tmpdir])
            except TypeError as exc:
                pytest.fail(f"roots-kwarg fuehrt zu TypeError: {exc}")
