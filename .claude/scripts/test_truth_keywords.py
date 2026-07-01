#!/usr/bin/env python3
"""Tests fuer truth_keywords.py (BL-309 R3 / thematische Schluesselwoerter)."""
from __future__ import annotations

import truth_keywords as kw


def test_extracts_frequent_terms():
    r = kw.extract_keywords("Migration Migration Wahrheit Wahrheit Wahrheit Schema", top=3)
    assert "wahrheit" in r and "migration" in r


def test_stopwords_excluded():
    r = kw.extract_keywords("der die das und Migration Migration")
    assert "der" not in r and "und" not in r
    assert "migration" in r


def test_short_words_excluded():
    assert "ab" not in kw.extract_keywords("ab cd Migration Migration")


def test_empty_and_stopword_only_return_empty():
    assert kw.extract_keywords("") == []
    assert kw.extract_keywords("der die das und") == []


def test_top_limit():
    text = " ".join(f"begriff{i} begriff{i}" for i in range(20))
    assert len(kw.extract_keywords(text, top=5)) == 5


def test_german_umlaut_words_kept():
    r = kw.extract_keywords("Wahrheiten Knoten Knoten Aenderung")
    assert "knoten" in r


# ---------------------------------------------------------------------------
# AK-KEYWORDS Haertungs-Tests (BL-389 batch_1) — RED-Worker 2026-06-21
# ---------------------------------------------------------------------------

def test_ak_keywords_determinism_same_order():
    """Zweimaliger Aufruf mit gleichem Input MUSS identische Reihenfolge liefern (Determinismus).
    Regression-Guard: Gleicher Text = gleiche Insertion-Order = stabile Ergebnis-Reihenfolge.
    Dieser Test sichert dass kein nicht-deterministischer interner Zustand eingebaut wird.
    """
    text = "schema migration schema migration atom knoten atom knoten wahrheit wahrheit"
    r1 = kw.extract_keywords(text, top=5)
    r2 = kw.extract_keywords(text, top=5)
    assert r1 == r2, f"Nicht-deterministisch: {r1} != {r2}"


def test_ak_keywords_determinism_tie_order_independent():
    """Determinismus bei Ties darf NICHT von Insertion-Order abhaengen — nur von Alphabet.
    RED: Ohne expliziten Tie-Breaker liefert gleicher-Frequenz-Korpus in unterschiedlicher
    Wort-Reihenfolge UNTERSCHIEDLICHE Ergebnisse. DoD-1 verlangt reproduzierbare Reihenfolge
    unabhaengig von der Wort-Erscheinungsreihenfolge im Text.
    """
    # Gleicher Wort-Satz, unterschiedliche Reihenfolge im Text
    text_fwd = "atom atom extraktion extraktion knoten knoten"
    text_rev = "knoten knoten extraktion extraktion atom atom"
    r_fwd = kw.extract_keywords(text_fwd, top=3)
    r_rev = kw.extract_keywords(text_rev, top=3)
    assert r_fwd == r_rev, (
        f"Reihenfolge insertion-order-abhaengig: fwd={r_fwd} != rev={r_rev}. "
        "Erwartet: alphabetischer Tie-Breaker liefert gleiche Liste unabhaengig von Wordreihenfolge."
    )


def test_ak_keywords_tie_breaking_alphabetic():
    """Bei gleicher Frequenz muessen Keywords alphabetisch geordnet sein (stabile Tie-Breaker-Regel).
    RED: aktuell kein expliziter Tie-Breaker — Counter.most_common() liefert Tie-Reihenfolge
    nach Insertion-Order, nicht alphabetisch.
    Beweis: text mit umgekehrter Einfu??gereihenfolge (gamma zuerst) liefert ohne expliziten
    Tie-Breaker ['gamma','beta','alpha'] statt ['alpha','beta','gamma'].
    """
    # Umgekehrte Reihenfolge: gamma zuerst — ohne alphabetischen Tie-Breaker kommt gamma vorne raus
    text = "gamma gamma beta beta alpha alpha"
    r = kw.extract_keywords(text, top=3)
    assert r == ["alpha", "beta", "gamma"], (
        f"Tie-Breaker nicht alphabetisch (insertion-order-abhaengig): {r}"
    )


def test_ak_keywords_no_duplicates():
    """Output darf keine doppelten Keywords enthalten (YAML-Frontmatter keywords[] safe).
    Regression-Guard: Counter verhindert Duplikate, aber explizit absichern.
    """
    text = "migration migration migration migration"
    r = kw.extract_keywords(text, top=8)
    assert len(r) == len(set(r)), f"Duplikate im Output: {r}"


def test_ak_keywords_all_lowercase():
    """Alle Keywords im Output muessen lowercase sein (Frontmatter-Suchbarkeit einheitlich).
    Regression-Guard: extract_keywords macht bereits .lower() — explizit testen.
    """
    text = "MIGRATION Migration MiGrAtIoN Schema SCHEMA schema"
    r = kw.extract_keywords(text, top=3)
    for word in r:
        assert word == word.lower(), f"Nicht-lowercase im Output: {word!r}"


def test_ak_keywords_none_input_returns_empty():
    """None als Input darf keinen TypeError werfen — muss leere Liste liefern.
    RED: aktuelle Impl hat `text or ''` aber der Typ-Hint sagt str; None-Verhalten undokumentiert.
    AK-KEYWORDS erfordert robuste Edge-Case-Behandlung.
    """
    r = kw.extract_keywords(None, top=8)  # type: ignore[arg-type]
    assert r == [], f"None-Input muss [] liefern, bekam: {r}"


def test_ak_keywords_only_numbers_returns_empty():
    """Rein-numerischer Text (keine Buchstaben) muss leere Liste liefern.
    RED: _WORD-Regex verlangt Buchstaben-Start, aber z.B. '123abc' koennte durchrutschen.
    Prueft dass rein-numerische Tokens nicht als Keywords aufgenommen werden.
    """
    r = kw.extract_keywords("123 456 789 000", top=8)
    assert r == [], f"Nur-Zahlen-Input muss [] liefern, bekam: {r}"


def test_ak_keywords_special_chars_stripped():
    """Sonderzeichen/Interpunktion duerfen nicht als Teil von Keywords aufgenommen werden.
    Frontmatter-Suchbarkeit: keywords mssen YAML-sicher sein.
    Regression-Guard + Absicherung.
    """
    text = "migration! migration? schema... schema--- atom@atom atom"
    r = kw.extract_keywords(text, top=5)
    for word in r:
        assert word.isalnum() or all(c.isalpha() or c in "-_" for c in word), (
            f"Sonderzeichen im Keyword: {word!r}"
        )
    assert "migration" in r


def test_ak_keywords_bigram_domain_boost():
    """Mehrwort/Bigram-Kandidaten (wiederkehrender Domain-Begriff) werden als thematischer Anker erfasst.
    RED (Kern-AK): AK-KEYWORDS Spec fordert Bigram-/Domain-Boost UEBER reinen top-Frequenz-Cut.
    Aktuell hat truth_keywords.py KEINE Bigram-Unterstuetzung -> MUSS RED sein.

    Korpus: 'vault migration' taucht 3x auf, einzeln kommen vault(3x) und migration(3x) vor.
    Erwartet: 'vault_migration' oder 'vault migration' als Bigram-Eintrag im Output ODER
    extract_keywords unterstuetzt kwarg bigrams=True und liefert Bigram-Kandidaten.
    """
    text = (
        "vault migration vault migration vault migration "
        "schema schema node"
    )
    # Test ob API bigrams=True akzeptiert und Bigram liefert
    try:
        r = kw.extract_keywords(text, top=5, bigrams=True)
        bigram_found = any("vault" in w and "migration" in w for w in r)
        assert bigram_found, (
            f"Bigram 'vault migration' nicht im Output bei bigrams=True: {r}"
        )
    except TypeError:
        # Kein bigrams-Parameter -> RED (Feature fehlt)
        raise AssertionError(
            "extract_keywords akzeptiert keinen bigrams=True Parameter — Bigram-Support fehlt (AK-KEYWORDS Spec DoD-1)"
        )


def test_ak_keywords_stable_across_repeated_calls_large_text():
    """Reproduzierbarkeit bei groesseren Texten: 10 Aufrufe, immer identisches Ergebnis.
    RED: prueft ob Determinismus auch bei groesseren Inputs stabil bleibt (dict-Ordnung, Counter).
    """
    text = " ".join(
        ["migration"] * 5 + ["schema"] * 4 + ["knoten"] * 3 +
        ["wahrheit"] * 3 + ["atom"] * 2 + ["vault"] * 2 +
        ["index"] * 2 + ["extraktion"] * 1
    )
    results = [kw.extract_keywords(text, top=5) for _ in range(10)]
    for i, r in enumerate(results[1:], 1):
        assert r == results[0], (
            f"Aufruf {i} weicht ab: {r} != {results[0]}"
        )
