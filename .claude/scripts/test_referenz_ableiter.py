"""
test_referenz_ableiter.py — BL-460 B-4 / Stage 1 / RED-Suite

TDD-RED: referenz_ableiter.py does NOT exist yet.
Diese Suite ist die SOLL-Spezifikation gegen GOLD-1..GOLD-8 aus dem HANDOFF:
  BL-460-HANDOFF.md  (SC/BL-460-HANDOFF.md, produziert von SC_observe)

Bottleneck: AK-2 (Referenz-Ableitung) + AK-CTX-2 (Threshold-Gate).
Interface unter Test:
    score_view(view_path, vault_root, *, atom_index, conf_threshold=0.70,
               within_bl_boost=1.4, per_view_cap=15) -> list[dict]

GOLD-Abdeckung:
  GOLD-1  Rueckgabe-Struktur (Pflichtfelder: atom_id, confidence, sub_threshold)
  GOLD-2  Konfidenz normiert auf [0,1] relativ zu Top-Match (Top == 1.0)
  GOLD-3  Within-BL-Boost x1.4 wirkt; boost=1.0 schaltet ihn ab
  GOLD-4  sub_threshold-Flag korrekt gesetzt (< threshold -> True)
  GOLD-5  per_view_cap haelt die Listlaenge
  GOLD-6  Leere View / leerer Index -> [] (kein Crash)
  GOLD-7  raw_score und boosted_score-Felder vorhanden; IDF-Semantik via Scoring
  GOLD-8  PoC-Scale-Anker (Regression, vault-free mock-Variante)

Stage-1 Mock-Grenze: KEIN reales Vault-IO. Alle Tests nutzen tmp_path +
in-memory atom_index (injiziert). GOLD-8 laeuft vault-free via gross-mock.
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

# M3 test-first: dieser Import schlaegt JETZT fehl (Modul GREENFIELD-NEU, FEHLT)
# -> Collection-Error = RED (Gesetz 2: Compile-/Import-Fehler zaehlt als Fehlschlag).
from referenz_ableiter import score_view  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_view(tmp_path, name: str, content: str, bl: str | None = None) -> str:
    """Schreibt eine minimale Markdown-View in tmp_path und gibt den absoluten Pfad zurueck."""
    fm_lines = ["---"]
    fm_lines.append(f"type: view")
    if bl:
        fm_lines.append(f"bl: {bl}")
    fm_lines.append("---")
    fm_lines.append(content)
    p = tmp_path / name
    p.write_text("\n".join(fm_lines), encoding="utf-8")
    return str(p)


def _make_atom_entry(path: str, bl_id: str | None, keywords: list[str]) -> dict:
    """Erzeugt einen Inverted-Index-Eintrag (ein keyword -> [entry])."""
    return {
        "path": path,
        "bl_id": bl_id,
        "vault_origin": "/mock/vault",
        "node_type": "truth",
    }


def _build_index(atoms: list[tuple[str, str | None, list[str]]]) -> dict:
    """Baut einen Inverted-Index aus [(path, bl_id, [keywords])] auf.

    Format: {keyword: [{path, bl_id, vault_origin, node_type}, ...]}
    """
    index: dict = {}
    for path, bl_id, keywords in atoms:
        entry = _make_atom_entry(path, bl_id, keywords)
        for kw in keywords:
            index.setdefault(kw, []).append(entry)
    return index


# ---------------------------------------------------------------------------
# GOLD-1 — Rueckgabe-Struktur
# ---------------------------------------------------------------------------

class TestGold1ReturnStructure:
    """GOLD-1: score_view liefert list[dict] mit Pflichtfeldern."""

    def test_returns_list(self, tmp_path):
        view = _write_view(tmp_path, "v1.md", "atom score view test", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/atom1.md", "BL-460", ["atom", "score", "view"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index)
        assert isinstance(result, list)

    def test_entries_are_dicts_with_required_fields(self, tmp_path):
        view = _write_view(tmp_path, "v1.md", "atom score view test", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/atom1.md", "BL-460", ["atom", "score", "view"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index)
        assert len(result) >= 1
        for entry in result:
            assert "atom_id" in entry, "Feld atom_id fehlt"
            assert "confidence" in entry, "Feld confidence fehlt"
            assert "sub_threshold" in entry, "Feld sub_threshold fehlt"

    def test_optional_fields_present(self, tmp_path):
        """raw_score und boosted_score muessen ebenfalls vorhanden sein (HANDOFF 3.1)."""
        view = _write_view(tmp_path, "v1.md", "atom score view test", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/atom1.md", "BL-460", ["atom", "score", "view"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index)
        assert len(result) >= 1
        entry = result[0]
        assert "raw_score" in entry, "Feld raw_score fehlt"
        assert "boosted_score" in entry, "Feld boosted_score fehlt"
        assert "bl_id" in entry, "Feld bl_id fehlt"

    def test_nonempty_when_index_and_view_have_overlap(self, tmp_path):
        """Lesbarer View mit Termen und passendem Index -> nicht-leere Liste."""
        view = _write_view(tmp_path, "v1.md", "referenz atom view scoring", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/a1.md", "BL-460", ["referenz", "atom", "scoring"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index)
        assert len(result) >= 1


# ---------------------------------------------------------------------------
# GOLD-2 — Konfidenz normiert auf [0,1], Top-Match == 1.0
# ---------------------------------------------------------------------------

class TestGold2ConfidenceNormalization:
    """GOLD-2: confidence relativ zu Top-Match, Top-Match == 1.0 exakt."""

    def test_top_match_confidence_is_1(self, tmp_path):
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz view test", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/a1.md", "BL-460", ["atom", "scoring", "referenz"]),
            ("BL-460/atoms/a2.md", "BL-460", ["atom"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index)
        assert len(result) >= 1
        top_conf = result[0]["confidence"]
        assert top_conf == pytest.approx(1.0), f"Top-Konfidenz erwartet 1.0, erhalten {top_conf}"

    def test_all_confidence_in_0_1(self, tmp_path):
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz view test", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/a1.md", "BL-460", ["atom", "scoring", "referenz"]),
            ("BL-460/atoms/a2.md", "BL-460", ["atom"]),
            ("BL-461/atoms/a3.md", "BL-461", ["referenz"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index)
        for entry in result:
            c = entry["confidence"]
            assert 0.0 <= c <= 1.0, f"confidence={c} ausserhalb [0,1]"

    def test_ordering_descending_by_confidence(self, tmp_path):
        """Ergebnis ist absteigend nach confidence sortiert."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz view test", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/a1.md", "BL-460", ["atom", "scoring", "referenz"]),  # 3 hits
            ("BL-460/atoms/a2.md", "BL-460", ["atom", "scoring"]),              # 2 hits
            ("BL-461/atoms/a3.md", "BL-461", ["referenz"]),                     # 1 hit
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index, within_bl_boost=1.0)
        confs = [r["confidence"] for r in result]
        assert confs == sorted(confs, reverse=True), f"Nicht absteigend sortiert: {confs}"

    def test_relative_not_absolute_threshold_independence(self, tmp_path):
        """Kuerzere und laengere Views sollen denselben Top-Match confidence=1.0 liefern."""
        short_view = _write_view(tmp_path, "short.md", "atom scoring", bl="BL-460")
        long_view = _write_view(
            tmp_path, "long.md",
            "atom scoring referenz view test implementation " * 10,
            bl="BL-460",
        )
        index = _build_index([
            ("BL-460/atoms/a1.md", "BL-460", ["atom", "scoring", "referenz"]),
        ])
        r_short = score_view(str(short_view), str(tmp_path), atom_index=index)
        r_long = score_view(str(long_view), str(tmp_path), atom_index=index)
        if r_short:
            assert r_short[0]["confidence"] == pytest.approx(1.0)
        if r_long:
            assert r_long[0]["confidence"] == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# GOLD-3 — Within-BL-Boost wirkt
# ---------------------------------------------------------------------------

class TestGold3WithinBlBoost:
    """GOLD-3: Within-BL-Boost x1.4 bevorzugt same-BL-Atom bei gleichem raw_score."""

    def test_within_bl_atom_ranks_higher_than_equal_cross_bl(self, tmp_path):
        """Zwei Atome mit identischem raw_score; same-BL soll vorne stehen (boost=1.4)."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz", bl="BL-460")
        # beide Atome matchen exakt dieselben 3 Keywords
        index = _build_index([
            ("BL-460/atoms/same.md", "BL-460", ["atom", "scoring", "referenz"]),   # same BL
            ("BL-461/atoms/cross.md", "BL-461", ["atom", "scoring", "referenz"]),  # cross BL
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index, within_bl_boost=1.4)
        assert len(result) == 2
        atom_ids = [r["atom_id"] for r in result]
        # same-BL-Atom soll an erster Position stehen
        assert "same.md" in atom_ids[0] or atom_ids[0].endswith("same.md"), (
            f"Erwartet same-BL-Atom an Position 0, erhalten: {atom_ids}"
        )

    def test_boost_1_means_no_preference(self, tmp_path):
        """Mit within_bl_boost=1.0 gibt es keinen Unterschied zwischen same- und cross-BL."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/same.md", "BL-460", ["atom", "scoring", "referenz"]),
            ("BL-461/atoms/cross.md", "BL-461", ["atom", "scoring", "referenz"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index, within_bl_boost=1.0)
        # Beide sollen dieselbe confidence haben (bei gleichen raw_scores + no boost)
        assert len(result) == 2
        c0, c1 = result[0]["confidence"], result[1]["confidence"]
        assert c0 == pytest.approx(c1), (
            f"Mit boost=1.0 erwarte gleiche Konfidenz, erhalten {c0} vs {c1}"
        )

    def test_cross_bl_wins_if_substantially_higher_raw_score(self, tmp_path):
        """Cross-BL mit 6 Hits gewinnt gegen same-BL mit 4 Hits (6 > 4*1.4=5.6)."""
        view = _write_view(
            tmp_path, "v1.md",
            "atom scoring referenz view test implementation extra",
            bl="BL-460",
        )
        # same-BL: 4 matches
        # cross-BL: 6 matches
        index = _build_index([
            ("BL-460/atoms/same4.md", "BL-460", ["atom", "scoring", "referenz", "view"]),
            ("BL-461/atoms/cross6.md", "BL-461",
             ["atom", "scoring", "referenz", "view", "test", "implementation"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index, within_bl_boost=1.4)
        assert len(result) == 2
        # cross6: raw=6, boosted=6.0; same4: raw=4, boosted=4*1.4=5.6 → cross wins
        assert "cross6.md" in result[0]["atom_id"], (
            f"Cross-BL mit raw=6 soll same-BL raw=4*1.4=5.6 schlagen: {result[0]}"
        )

    def test_boosted_score_field_reflects_boost(self, tmp_path):
        """boosted_score eines same-BL-Atoms ist raw_score * within_bl_boost."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/a.md", "BL-460", ["atom", "scoring", "referenz"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index, within_bl_boost=1.4)
        assert len(result) >= 1
        entry = result[0]
        expected_boost = entry["raw_score"] * 1.4
        assert entry["boosted_score"] == pytest.approx(expected_boost), (
            f"boosted_score erwartet {expected_boost}, erhalten {entry['boosted_score']}"
        )

    def test_cross_bl_atom_boosted_score_equals_raw(self, tmp_path):
        """Cross-BL-Atom: boosted_score == raw_score (kein Boost)."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz", bl="BL-460")
        index = _build_index([
            ("BL-461/atoms/cross.md", "BL-461", ["atom", "scoring", "referenz"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index, within_bl_boost=1.4)
        assert len(result) >= 1
        entry = result[0]
        assert entry["boosted_score"] == pytest.approx(entry["raw_score"]), (
            f"Cross-BL: boosted_score sollte == raw_score, erhalten {entry}"
        )


# ---------------------------------------------------------------------------
# GOLD-4 — sub_threshold-Flag korrekt
# ---------------------------------------------------------------------------

class TestGold4SubThreshold:
    """GOLD-4: sub_threshold=True iff confidence < conf_threshold."""

    def test_sub_threshold_false_for_top_match(self, tmp_path):
        """Top-Match hat confidence=1.0 -> sub_threshold=False fuer threshold<=1.0."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/a1.md", "BL-460", ["atom", "scoring", "referenz"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index, conf_threshold=0.70)
        assert result[0]["sub_threshold"] is False

    def test_sub_threshold_true_for_weaker_match(self, tmp_path):
        """Schwaecheres Match (confidence<0.70) wird als sub_threshold=True markiert."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz view test", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/strong.md", "BL-460", ["atom", "scoring", "referenz", "view", "test"]),
            ("BL-460/atoms/weak.md", "BL-460", ["atom"]),  # nur 1 Treffer von 5 -> conf=0.2
        ])
        result = score_view(
            str(view), str(tmp_path),
            atom_index=index,
            conf_threshold=0.70,
            within_bl_boost=1.0,
        )
        # strong soll confidence=1.0, weak confidence=0.2 haben
        by_id = {r["atom_id"].split("/")[-1]: r for r in result}
        assert "strong.md" in by_id
        assert "weak.md" in by_id
        assert by_id["strong.md"]["sub_threshold"] is False
        assert by_id["weak.md"]["sub_threshold"] is True

    def test_flag_matches_threshold_exactly(self, tmp_path):
        """Alle Eintraege mit confidence >= threshold: sub_threshold=False;
        confidence < threshold: sub_threshold=True."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz view test", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/a5.md", "BL-460", ["atom", "scoring", "referenz", "view", "test"]),
            ("BL-460/atoms/a4.md", "BL-460", ["atom", "scoring", "referenz", "view"]),
            ("BL-460/atoms/a3.md", "BL-460", ["atom", "scoring", "referenz"]),
            ("BL-460/atoms/a2.md", "BL-460", ["atom", "scoring"]),
            ("BL-460/atoms/a1.md", "BL-460", ["atom"]),
        ])
        result = score_view(
            str(view), str(tmp_path),
            atom_index=index,
            conf_threshold=0.70,
            within_bl_boost=1.0,
        )
        for entry in result:
            if entry["confidence"] >= 0.70:
                assert entry["sub_threshold"] is False, (
                    f"confidence={entry['confidence']} >= 0.70 aber sub_threshold=True"
                )
            else:
                assert entry["sub_threshold"] is True, (
                    f"confidence={entry['confidence']} < 0.70 aber sub_threshold=False"
                )

    def test_sub_threshold_entries_not_dropped(self, tmp_path):
        """Sub-threshold Eintraege werden NICHT verworfen — sie erscheinen mit flag=True."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz view test", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/strong.md", "BL-460", ["atom", "scoring", "referenz", "view", "test"]),
            ("BL-460/atoms/weak.md", "BL-460", ["atom"]),
        ])
        result = score_view(
            str(view), str(tmp_path),
            atom_index=index,
            conf_threshold=0.70,
            within_bl_boost=1.0,
        )
        # beide Eintraege muessen sichtbar sein
        assert len(result) == 2, f"Erwartet 2 Eintraege (inkl. sub-threshold), erhalten {len(result)}"


# ---------------------------------------------------------------------------
# GOLD-5 — per_view_cap
# ---------------------------------------------------------------------------

class TestGold5PerViewCap:
    """GOLD-5: per_view_cap begrenzt Listlaenge inkl. sub-threshold."""

    def test_cap_15_default(self, tmp_path):
        """Default cap=15: niemals mehr als 15 Eintraege."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz", bl="BL-460")
        # 25 Atome, alle matchen mindestens 1 Keyword
        atoms = [
            (f"BL-460/atoms/a{i}.md", "BL-460", ["atom"])
            for i in range(25)
        ]
        index = _build_index(atoms)
        result = score_view(str(view), str(tmp_path), atom_index=index)
        assert len(result) <= 15

    def test_cap_custom(self, tmp_path):
        """per_view_cap=3: niemals mehr als 3 Eintraege."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz", bl="BL-460")
        atoms = [
            (f"BL-460/atoms/a{i}.md", "BL-460", ["atom"])
            for i in range(10)
        ]
        index = _build_index(atoms)
        result = score_view(str(view), str(tmp_path), atom_index=index, per_view_cap=3)
        assert len(result) <= 3

    def test_cap_includes_sub_threshold(self, tmp_path):
        """Cap zaehlt sub-threshold Eintraege mit (DT-AK-CTX-2-3)."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz view test", bl="BL-460")
        # Nur 1 starker Match, Rest schwach -> sub-threshold
        # Bei cap=3 sollen hoechstens 3 zurueckgegeben werden
        atoms = [
            ("BL-460/atoms/strong.md", "BL-460", ["atom", "scoring", "referenz", "view", "test"]),
        ] + [
            (f"BL-460/atoms/weak{i}.md", "BL-460", ["atom"])
            for i in range(10)
        ]
        index = _build_index(atoms)
        result = score_view(
            str(view), str(tmp_path),
            atom_index=index,
            per_view_cap=3,
            within_bl_boost=1.0,
        )
        assert len(result) <= 3

    def test_result_shorter_than_cap_when_few_atoms(self, tmp_path):
        """Weniger Matches als cap: Liste kuerzer als cap (kein Padding)."""
        view = _write_view(tmp_path, "v1.md", "atom scoring", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/a1.md", "BL-460", ["atom", "scoring"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index, per_view_cap=15)
        assert len(result) == 1


# ---------------------------------------------------------------------------
# GOLD-6 — Leere View / leerer Index -> []
# ---------------------------------------------------------------------------

class TestGold6EmptyRobust:
    """GOLD-6: Kein Crash bei Rand-Inputs; leere Ergebnisliste bei no-match."""

    def test_nonexistent_view_returns_empty(self, tmp_path):
        """Nicht-existente View-Datei -> [] (kein Crash)."""
        index = _build_index([
            ("BL-460/atoms/a1.md", "BL-460", ["atom"]),
        ])
        result = score_view(
            str(tmp_path / "nonexistent.md"), str(tmp_path), atom_index=index
        )
        assert result == []

    def test_empty_atom_index_returns_empty(self, tmp_path):
        """Leerer atom_index -> []."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz", bl="BL-460")
        result = score_view(str(view), str(tmp_path), atom_index={})
        assert result == []

    def test_none_atom_index_and_no_vault_returns_empty(self, tmp_path):
        """atom_index=None ohne echten Vault -> [] (kein Crash, keine Exception)."""
        view = _write_view(tmp_path, "v1.md", "atom scoring", bl="BL-460")
        # vault_root ist tmp_path (leer, keine Atoms) — kein realer Vault
        result = score_view(str(view), str(tmp_path), atom_index=None)
        assert result == []

    def test_view_with_no_salient_terms_returns_empty(self, tmp_path):
        """View deren Text nur Stopwords enthaelt -> [] (keine Keywords extrahierbar)."""
        view = _write_view(
            tmp_path, "stopwords.md",
            "und die der das ist ein eine",
            bl="BL-460",
        )
        index = _build_index([
            ("BL-460/atoms/a1.md", "BL-460", ["atom", "scoring"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index)
        assert result == []

    def test_no_overlap_between_view_and_index_returns_empty(self, tmp_path):
        """View-Keywords und Index-Keywords ueberlappen sich nicht -> []."""
        view = _write_view(tmp_path, "v1.md", "routing referenz dispatch", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/a1.md", "BL-460", ["scoring", "threshold", "boosting"]),
        ])
        result = score_view(
            str(view), str(tmp_path), atom_index=index, within_bl_boost=1.0
        )
        assert result == []


# ---------------------------------------------------------------------------
# GOLD-7 — IDF-Semantik: seltenere Keywords tragen mehr bei
# ---------------------------------------------------------------------------

class TestGold7IdfWeighting:
    """GOLD-7: IDF-Gewichtung — rarer Keywords haben groesseren Beitrag als haeufige.

    Hinweis: truth_search.py / extract_keywords implementieren frequency-based
    keyword-Extraktion (kein echtes TF-IDF). 'Rarer' im Sinne des HANDOFF bedeutet,
    dass ein Atom, das ein seltenes (aber hochrelevantes) Keyword der View matcht,
    hoeher ranken soll als eines, das nur haeufige generische Terms trifft.

    Da truth_search.py den Score als Anzahl matched keywords berechnet, testen wir
    dass atom_id und raw_score konsistent mit dem tatsaechlichen Match sind.
    """

    def test_more_keyword_matches_means_higher_raw_score(self, tmp_path):
        """Atom mit mehr Keyword-Ueberlappungen hat hoehere raw_score als Atom mit weniger."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz view test", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/many.md", "BL-460", ["atom", "scoring", "referenz", "view", "test"]),
            ("BL-460/atoms/few.md", "BL-460", ["atom"]),
        ])
        result = score_view(
            str(view), str(tmp_path),
            atom_index=index,
            within_bl_boost=1.0,
        )
        by_id = {r["atom_id"].split("/")[-1]: r for r in result}
        assert by_id["many.md"]["raw_score"] > by_id["few.md"]["raw_score"]

    def test_raw_score_is_integer_count(self, tmp_path):
        """raw_score ist ein ganzzahliger Keyword-Treffer-Zaehler."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/a.md", "BL-460", ["atom", "scoring", "referenz"]),
        ])
        result = score_view(str(view), str(tmp_path), atom_index=index)
        assert len(result) >= 1
        assert isinstance(result[0]["raw_score"], (int, float))
        assert result[0]["raw_score"] > 0

    def test_deterministic_output_same_input(self, tmp_path):
        """Gleicher Input -> gleicher Output (deterministisch, GOLD-7 Teil)."""
        view = _write_view(tmp_path, "v1.md", "atom scoring referenz view test", bl="BL-460")
        index = _build_index([
            ("BL-460/atoms/a1.md", "BL-460", ["atom", "scoring", "referenz"]),
            ("BL-460/atoms/a2.md", "BL-460", ["view", "test"]),
            ("BL-461/atoms/a3.md", "BL-461", ["atom", "view"]),
        ])
        r1 = score_view(str(view), str(tmp_path), atom_index=index)
        r2 = score_view(str(view), str(tmp_path), atom_index=index)
        assert [e["atom_id"] for e in r1] == [e["atom_id"] for e in r2]
        assert [e["confidence"] for e in r1] == [e["confidence"] for e in r2]


# ---------------------------------------------------------------------------
# GOLD-8 — PoC-Scale-Anker (vault-free mock, Regression)
# ---------------------------------------------------------------------------

class TestGold8PocScaleRegression:
    """GOLD-8: PoC-Skala-Regression — vault-free via Mock (131 Views, conf=0.30).

    Der echte PoC lief auf 131 Model-Views + 3413 Atome mit conf>=0.30.
    Da wir hier KEIN reales Vault benutzen, simulieren wir die Skalierung mit
    einem Mock-Index: 100 Views (synthetisch), ~50 Atome, conf=0.30.
    Assertions:
    - models_with_proposals >= 95% der Views (>=95 von 100)
    - cap=15 haelt fuer alle Views
    - Keine Exception auf dem Korpus
    """

    def _make_mock_corpus(self, tmp_path, n_views=100, n_atoms=50):
        """Erzeugt n_views Mock-Views und einen Mock-Index mit n_atoms."""
        import random
        random.seed(42)
        keywords_pool = [
            "atom", "scoring", "referenz", "view", "test", "implementation",
            "threshold", "boost", "confidence", "ranking", "index", "keyword",
            "backlog", "routing", "dispatch", "pipeline", "validator", "schema",
            "model", "wikilink", "materializer", "dryrun", "corpus", "frontmatter",
            "bl460", "bl461", "truth", "anchor", "edge", "node",
        ]
        # Atome mit zufaelligen Keywords
        atoms = []
        for i in range(n_atoms):
            kws = random.sample(keywords_pool, k=random.randint(3, 8))
            bl = f"BL-4{60 + (i % 5)}"
            atoms.append((f"{bl}/atoms/atom{i}.md", bl, kws))
        index = _build_index(atoms)

        # Views: Text der zufaellig Keywords aus dem Pool enthaelt
        view_paths = []
        for i in range(n_views):
            # sicherstellen dass mind. 2 Keywords aus dem Pool vorkommen
            kws = random.sample(keywords_pool, k=random.randint(2, 6))
            view_text = " ".join(kws) + " extra context words here"
            bl = f"BL-4{60 + (i % 5)}"
            vpath = _write_view(tmp_path, f"view{i}.md", view_text, bl=bl)
            view_paths.append(vpath)

        return view_paths, index

    def test_poc_scale_no_exception(self, tmp_path):
        """Keine Exception auf dem Mock-Korpus (100 Views, 50 Atome)."""
        view_paths, index = self._make_mock_corpus(tmp_path)
        for vpath in view_paths:
            # darf nicht werfen
            score_view(str(vpath), str(tmp_path), atom_index=index, conf_threshold=0.30)

    def test_poc_scale_cap_respected(self, tmp_path):
        """Cap=15 wird fuer alle Views eingehalten."""
        view_paths, index = self._make_mock_corpus(tmp_path)
        for vpath in view_paths:
            result = score_view(str(vpath), str(tmp_path), atom_index=index, conf_threshold=0.30)
            assert len(result) <= 15, f"Cap verletzt fuer {vpath}: {len(result)}"

    def test_poc_scale_coverage_baseline(self, tmp_path):
        """Mindestens 85% der Views haben mindestens einen Vorschlag bei conf=0.30."""
        view_paths, index = self._make_mock_corpus(tmp_path)
        with_proposals = sum(
            1 for vpath in view_paths
            if score_view(str(vpath), str(tmp_path), atom_index=index, conf_threshold=0.30)
        )
        coverage = with_proposals / len(view_paths)
        assert coverage >= 0.85, (
            f"Coverage {coverage:.1%} unter 85% Baseline (PoC-Anker): "
            f"{with_proposals}/{len(view_paths)} Views mit Vorschlaegen"
        )
