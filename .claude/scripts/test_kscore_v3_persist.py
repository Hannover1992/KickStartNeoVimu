"""test_kscore_v3_persist.py — BL-311 batch_2 RED-Tests: kscore_v3_persist.

5 Exit-Kriterien (AK-14/15):
  T-17: build_schema_3_document — alle Schema-2.0-Felder im Output (Dual-Write-Contract, BL-266)
  T-18: build_schema_3_document — neue 3.0-Felder overlap_edges/contention_per_item/k_min vorhanden
  T-19: build_schema_3_document testbar ohne File-IO (gibt String zurueck)
  T-20: should_use_v3_full — 3 Cases (item_count<n_schwelle, >=n_schwelle, k_verdacht=True Override)
  T-21: write_schema_3 — mockt File-Write, prueft build_schema_3_document-Delegation

Kanarivogel:
  K-6: Dual-Write-Contract (T-17) — Schema-2.0-Felder MUESSEN erhalten bleiben (BL-266-Lehre)

RED-Worker: NUR Tests. KEIN Impl.
"""
import pytest
from unittest.mock import patch, mock_open, MagicMock

from kscore_v3_persist import (
    write_schema_3,
    build_schema_3_document,
    should_use_v3_full,
)


# ---------------------------------------------------------------------------
# Test-Fixtures
# ---------------------------------------------------------------------------

def _minimal_scored_item(item_id="I1", k_final=5.0):
    return {
        "item_id": item_id,
        "k_aufwand": 1.0, "k_kopplung": 2.0, "k_fragilitaet": 1.0,
        "k_roh": 5.0, "k_praez": 4.5, "k_final": k_final,
        "pattern_status": "none", "discount_factor": 1.0,
        "discount_evidence": None, "truth_grade": "code_verified",
        "penalty_factor": 1.0, "weights_used": {"w1": 0.4, "w2": 0.35, "w3": 0.25},
    }


def _minimal_aggregate(k_min=2.0, k_avg=5.0, k_max=8.0):
    return {
        "k_max": k_max, "k_avg": k_avg, "k_min": k_min,
        "item_count": 2,
        "per_item": [_minimal_scored_item("I1", k_min), _minimal_scored_item("I2", k_max)],
    }


def _minimal_topology_summary():
    return {
        "overlap_graph": {
            "nodes": ["I1", "I2"],
            "edges": [{"from": "I1", "to": "I2", "shared_files": ["f.py"], "shared_symbols": [], "weight": 1}],
            "adj": {"I1": ["I2"], "I2": ["I1"]},
        },
        "hotspots": {"datei_hotspots": [], "symbol_hotspots": []},
        "contention": {"I1": 0.5, "I2": 0.5},
    }


SCHEMA2_COMPAT_FIELDS = {
    "bl": "BL-311",
    "batch": "batch_2",
    "schema_version": "2.0",
    "k_max": 8.0,
    "k_avg": 5.0,
    "created": "2026-06-21",
}


# ---------------------------------------------------------------------------
# T-17 KANARIVOGEL K-6: Schema-2.0-Contract (Dual-Write-Invariante)
# ---------------------------------------------------------------------------

class TestSchema2Contract:
    def test_all_schema2_compat_fields_present_in_output(self):
        """K-6 + T-17: alle schema2_compat_fields im Output-String vorhanden (BL-266 Dual-Write-Invariante, AK-14 Gold-Zeile 1)."""
        doc_str = build_schema_3_document(
            scored_items=[_minimal_scored_item()],
            aggregate_scores=_minimal_aggregate(),
            topology_summary=_minimal_topology_summary(),
            schema2_compat_fields=SCHEMA2_COMPAT_FIELDS,
            bl_id="BL-311",
            batch_id="batch_2",
        )
        for key in SCHEMA2_COMPAT_FIELDS:
            assert key in doc_str, (
                f"Schema-2.0-Feld '{key}' fehlt im build_schema_3_document Output. "
                f"BL-266 Dual-Write-Invariante verletzt. doc_str[:200]={doc_str[:200]}"
            )

    def test_schema2_field_values_preserved(self):
        """Schema-2.0-Feldwerte unveraendert im Output (nicht nur Schluessel vorhanden)."""
        doc_str = build_schema_3_document(
            scored_items=[_minimal_scored_item()],
            aggregate_scores=_minimal_aggregate(),
            topology_summary=_minimal_topology_summary(),
            schema2_compat_fields=SCHEMA2_COMPAT_FIELDS,
            bl_id="BL-311",
            batch_id="batch_2",
        )
        # BL-311 als Wert muss im String vorkommen
        assert "BL-311" in doc_str, "Schema-2.0-Wert 'BL-311' fehlt im Output"
        assert "batch_2" in doc_str, "Schema-2.0-Wert 'batch_2' fehlt im Output"


# ---------------------------------------------------------------------------
# T-18: Schema-3.0-Felder vorhanden
# ---------------------------------------------------------------------------

class TestSchema30Fields:
    def test_schema30_overlap_edges_in_output(self):
        """T-18a: overlap_edges im Output-String vorhanden (AK-14 Gold-Zeile 2)."""
        doc_str = build_schema_3_document(
            scored_items=[_minimal_scored_item()],
            aggregate_scores=_minimal_aggregate(),
            topology_summary=_minimal_topology_summary(),
            schema2_compat_fields=SCHEMA2_COMPAT_FIELDS,
            bl_id="BL-311",
            batch_id="batch_2",
        )
        assert "overlap_edges" in doc_str, (
            f"Schema-3.0-Feld 'overlap_edges' fehlt im Output. doc_str[:300]={doc_str[:300]}"
        )

    def test_schema30_contention_per_item_in_output(self):
        """T-18b: contention_per_item im Output-String vorhanden (AK-14 Gold-Zeile 2)."""
        doc_str = build_schema_3_document(
            scored_items=[_minimal_scored_item()],
            aggregate_scores=_minimal_aggregate(),
            topology_summary=_minimal_topology_summary(),
            schema2_compat_fields=SCHEMA2_COMPAT_FIELDS,
            bl_id="BL-311",
            batch_id="batch_2",
        )
        assert "contention_per_item" in doc_str, (
            f"Schema-3.0-Feld 'contention_per_item' fehlt im Output. doc_str[:300]={doc_str[:300]}"
        )

    def test_schema30_k_min_in_output(self):
        """T-18c: k_min im Output-String vorhanden (AK-14 Gold-Zeile 2)."""
        doc_str = build_schema_3_document(
            scored_items=[_minimal_scored_item()],
            aggregate_scores=_minimal_aggregate(k_min=2.0),
            topology_summary=_minimal_topology_summary(),
            schema2_compat_fields=SCHEMA2_COMPAT_FIELDS,
            bl_id="BL-311",
            batch_id="batch_2",
        )
        assert "k_min" in doc_str, (
            f"Schema-3.0-Feld 'k_min' fehlt im Output. doc_str[:300]={doc_str[:300]}"
        )


# ---------------------------------------------------------------------------
# T-19: build_schema_3_document gibt String zurueck (File-IO-entkoppelt)
# ---------------------------------------------------------------------------

class TestBuildSchema3DocumentFileIODecoupled:
    def test_returns_string_without_file_io(self):
        """T-19: build_schema_3_document gibt str zurueck (kein File-IO intern, AK-14 Gold-Zeile 3)."""
        doc_str = build_schema_3_document(
            scored_items=[_minimal_scored_item()],
            aggregate_scores=_minimal_aggregate(),
            topology_summary=_minimal_topology_summary(),
            schema2_compat_fields=SCHEMA2_COMPAT_FIELDS,
            bl_id="BL-311",
            batch_id="batch_2",
        )
        assert isinstance(doc_str, str), (
            f"build_schema_3_document muss str zurueckgeben, got {type(doc_str)}"
        )
        assert len(doc_str) > 0, "build_schema_3_document Output darf nicht leer sein"

    def test_returns_nonempty_string_for_minimal_input(self):
        """Minimale Inputs -> non-empty String (kein Crash)."""
        doc_str = build_schema_3_document(
            scored_items=[],
            aggregate_scores={"k_max": 0.0, "k_avg": 0.0, "k_min": 0.0, "item_count": 0, "per_item": []},
            topology_summary={"overlap_graph": {"nodes": [], "edges": [], "adj": {}},
                               "hotspots": {"datei_hotspots": [], "symbol_hotspots": []},
                               "contention": {}},
            schema2_compat_fields={},
            bl_id="BL-TEST",
            batch_id="batch_0",
        )
        assert isinstance(doc_str, str)


# ---------------------------------------------------------------------------
# T-20: should_use_v3_full — 3 Cases
# ---------------------------------------------------------------------------

class TestShouldUseV3Full:
    def test_item_count_below_n_schwelle_returns_false(self):
        """T-20a: item_count < n_schwelle AND k_verdacht=False -> False (Solo-Pfad, AK-15 Gold-Zeile 1)."""
        result = should_use_v3_full(item_count=1, k_verdacht=False, n_schwelle=3)
        assert result is False, (
            f"should_use_v3_full(1, False, 3) muss False (Solo-Pfad). got {result}"
        )

    def test_item_count_at_n_schwelle_returns_true(self):
        """T-20b: item_count >= n_schwelle -> True (v3-Full, AK-15 Gold-Zeile 2)."""
        result = should_use_v3_full(item_count=3, k_verdacht=False, n_schwelle=3)
        assert result is True, (
            f"should_use_v3_full(3, False, 3) muss True (v3-Full). got {result}"
        )

    def test_k_verdacht_true_overrides_count(self):
        """T-20c: k_verdacht=True bei item_count=1 -> True (Override, AK-15 Gold-Zeile 3)."""
        result = should_use_v3_full(item_count=1, k_verdacht=True, n_schwelle=3)
        assert result is True, (
            f"should_use_v3_full(1, True, 3) muss True (k_verdacht Override). got {result}"
        )

    def test_item_count_above_n_schwelle_returns_true(self):
        """item_count > n_schwelle -> True."""
        result = should_use_v3_full(item_count=10, k_verdacht=False, n_schwelle=3)
        assert result is True


# ---------------------------------------------------------------------------
# T-21: write_schema_3 — File-IO gemockt
# ---------------------------------------------------------------------------

class TestWriteSchema3:
    def test_write_schema_3_delegates_to_build_and_writes_file(self):
        """T-21: write_schema_3 schreibt Datei; Inhalt = build_schema_3_document Output (AK-14 Gold-Zeile 5)."""
        output_path = "/fake/path/K-SCORE.md"

        with patch("builtins.open", mock_open()) as mock_file:
            write_schema_3(
                output_path=output_path,
                scored_items=[_minimal_scored_item()],
                aggregate_scores=_minimal_aggregate(),
                topology_summary=_minimal_topology_summary(),
                schema2_compat_fields=SCHEMA2_COMPAT_FIELDS,
                bl_id="BL-311",
                batch_id="batch_2",
            )
        # File muss geoeffnet worden sein
        mock_file.assert_called_once_with(output_path, "w", encoding="utf-8")
        # write muss aufgerufen worden sein (Inhalt wird geschrieben)
        handle = mock_file()
        handle.write.assert_called_once()
        written_content = handle.write.call_args[0][0]
        # Geschriebener Inhalt muss Schema-3.0-Felder enthalten
        assert "overlap_edges" in written_content, (
            f"write_schema_3 muss 'overlap_edges' in den Output schreiben. "
            f"written[:200]={written_content[:200]}"
        )
        assert "contention_per_item" in written_content, (
            "write_schema_3 muss 'contention_per_item' in den Output schreiben."
        )
