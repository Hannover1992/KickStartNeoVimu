"""test_kscore_v3_topology.py — BL-311 batch_2 RED-Tests: kscore_v3_topology.

5 Exit-Kriterien (AK-9):
  T-1: build_overlap_graph — shared Datei -> Kante vorhanden
  T-2: build_overlap_graph — kein Overlap -> keine Kante
  T-3: build_overlap_graph — shared Symbol (nicht Datei) -> Kante vorhanden
  T-4: detect_hotspots — Datei in >= threshold Items -> Hotspot erkannt
  T-5: contention_per_item — Item mit Kanten -> Score > 0.0; isoliertes Item -> 0.0; topology_summary Output-Keys vollstaendig

RED-Worker: NUR Tests. KEIN Impl.
Importe fehlschlagen mit ImportError (Module existieren nicht) -> ROT bestaetig.
"""
import pytest

from kscore_v3_topology import (
    build_overlap_graph,
    detect_hotspots,
    contention_per_item,
    topology_summary,
)


class TestBuildOverlapGraph:
    """T-1, T-2, T-3 — AK-9 Gold: build_overlap_graph."""

    def test_shared_datei_creates_edge(self):
        """T-1: 2 Items mit shared Datei -> Kante vorhanden (AK-9 Gold-Zeile 1)."""
        walker_outputs = [
            {"item_id": "A", "dateien": ["src/foo.py"], "symbole": []},
            {"item_id": "B", "dateien": ["src/foo.py"], "symbole": []},
        ]
        graph = build_overlap_graph(walker_outputs)
        # Kante A-B muss vorhanden sein (egal ob {from:A,to:B} oder {from:B,to:A})
        edges = graph["edges"]
        item_ids_in_edges = [
            (e["from"], e["to"]) for e in edges
        ]
        assert any(
            (f == "A" and t == "B") or (f == "B" and t == "A")
            for f, t in item_ids_in_edges
        ), f"Kante A-B fehlt bei shared Datei. edges={edges}"

    def test_no_overlap_no_edge(self):
        """T-2: 2 Items OHNE Overlap -> keine Kante (AK-9 Gold-Zeile 2)."""
        walker_outputs = [
            {"item_id": "X", "dateien": ["src/x.py"], "symbole": ["sym_x"]},
            {"item_id": "Y", "dateien": ["src/y.py"], "symbole": ["sym_y"]},
        ]
        graph = build_overlap_graph(walker_outputs)
        assert len(graph["edges"]) == 0, (
            f"Keine Kante erwartet bei disjunkten Items. edges={graph['edges']}"
        )

    def test_shared_symbol_only_creates_edge(self):
        """T-3: shared Symbol (nicht Datei) -> Kante vorhanden (AK-9 Gold-Zeile 3)."""
        walker_outputs = [
            {"item_id": "C", "dateien": ["src/c.py"], "symbole": ["MyClass"]},
            {"item_id": "D", "dateien": ["src/d.py"], "symbole": ["MyClass"]},
        ]
        graph = build_overlap_graph(walker_outputs)
        edges = graph["edges"]
        item_ids_in_edges = [
            (e["from"], e["to"]) for e in edges
        ]
        assert any(
            (f == "C" and t == "D") or (f == "D" and t == "C")
            for f, t in item_ids_in_edges
        ), f"Kante C-D fehlt bei shared Symbol. edges={edges}"

    def test_pure_function_determinism(self):
        """AK-9 Gold: gleiche Inputs -> identischer Graph (pure function)."""
        walker_outputs = [
            {"item_id": "A", "dateien": ["shared.py"], "symbole": []},
            {"item_id": "B", "dateien": ["shared.py"], "symbole": []},
        ]
        g1 = build_overlap_graph(walker_outputs)
        g2 = build_overlap_graph(walker_outputs)
        assert g1["nodes"] == g2["nodes"]
        assert g1["edges"] == g2["edges"]


class TestDetectHotspots:
    """T-4 — AK-9 Gold: detect_hotspots."""

    def test_file_above_threshold_is_hotspot(self):
        """T-4a: Datei in >= threshold Items -> in datei_hotspots (AK-9 Gold-Zeile 3)."""
        walker_outputs = [
            {"item_id": "A", "dateien": ["hot.py"], "symbole": []},
            {"item_id": "B", "dateien": ["hot.py"], "symbole": []},
            {"item_id": "C", "dateien": ["hot.py"], "symbole": []},
        ]
        result = detect_hotspots(walker_outputs, hotspot_threshold=3)
        hotspot_datei_names = [h["datei"] for h in result["datei_hotspots"]]
        assert "hot.py" in hotspot_datei_names, (
            f"hot.py muss Hotspot sein (3 >= threshold=3). datei_hotspots={result['datei_hotspots']}"
        )

    def test_file_below_threshold_not_hotspot(self):
        """T-4b: Datei in < threshold Items -> NICHT in datei_hotspots."""
        walker_outputs = [
            {"item_id": "A", "dateien": ["cold.py"], "symbole": []},
            {"item_id": "B", "dateien": ["cold.py"], "symbole": []},
        ]
        result = detect_hotspots(walker_outputs, hotspot_threshold=3)
        hotspot_datei_names = [h["datei"] for h in result["datei_hotspots"]]
        assert "cold.py" not in hotspot_datei_names, (
            f"cold.py darf kein Hotspot sein (2 < threshold=3). datei_hotspots={result['datei_hotspots']}"
        )


class TestContentionPerItem:
    """T-5 — AK-9 Gold: contention_per_item + topology_summary."""

    def test_item_with_edges_has_positive_contention(self):
        """T-5a: Item mit N Kanten -> contention > 0.0 (AK-9 Gold-Zeile 4)."""
        walker_outputs = [
            {"item_id": "A", "dateien": ["shared.py"], "symbole": []},
            {"item_id": "B", "dateien": ["shared.py"], "symbole": []},
            {"item_id": "C", "dateien": ["shared.py"], "symbole": []},
        ]
        graph = build_overlap_graph(walker_outputs)
        contention = contention_per_item(walker_outputs, graph)
        assert contention["A"] > 0.0, (
            f"Item A (in 2 Kanten) muss contention > 0.0 haben. contention={contention}"
        )

    def test_isolated_item_has_zero_contention(self):
        """T-5b: isoliertes Item (keine Kanten) -> contention == 0.0 (AK-9 Gold-Zeile 4)."""
        walker_outputs = [
            {"item_id": "ISO", "dateien": ["unique.py"], "symbole": ["unique_sym"]},
            {"item_id": "B",   "dateien": ["shared.py"], "symbole": []},
            {"item_id": "C",   "dateien": ["shared.py"], "symbole": []},
        ]
        graph = build_overlap_graph(walker_outputs)
        contention = contention_per_item(walker_outputs, graph)
        assert contention["ISO"] == 0.0, (
            f"Isoliertes Item ISO muss contention=0.0 haben. contention={contention}"
        )

    def test_all_contention_values_in_unit_interval(self):
        """AK-9 Gold: alle Werte in [0,1] (normiert)."""
        walker_outputs = [
            {"item_id": "A", "dateien": ["f.py"], "symbole": []},
            {"item_id": "B", "dateien": ["f.py"], "symbole": []},
            {"item_id": "C", "dateien": ["g.py"], "symbole": []},
        ]
        graph = build_overlap_graph(walker_outputs)
        contention = contention_per_item(walker_outputs, graph)
        for item_id, val in contention.items():
            assert 0.0 <= val <= 1.0, (
                f"contention[{item_id}]={val} liegt ausserhalb [0,1]"
            )

    def test_topology_summary_output_keys_complete(self):
        """T-5c: topology_summary Output-Keys vollstaendig (AK-9 Gold-Zeile 5)."""
        walker_outputs = [
            {"item_id": "A", "dateien": ["x.py"], "symbole": []},
            {"item_id": "B", "dateien": ["x.py"], "symbole": []},
        ]
        result = topology_summary(walker_outputs)
        assert "overlap_graph" in result, "Key 'overlap_graph' fehlt in topology_summary Output"
        assert "hotspots" in result, "Key 'hotspots' fehlt in topology_summary Output"
        assert "contention" in result, "Key 'contention' fehlt in topology_summary Output"

    def test_topology_summary_empty_walker_outputs(self):
        """Edge-Case: leere walker_outputs -> kein Crash, Struktur vollstaendig."""
        result = topology_summary([])
        assert "overlap_graph" in result
        assert "hotspots" in result
        assert "contention" in result
        # Leerer Graph: keine Knoten, keine Kanten
        assert result["overlap_graph"]["nodes"] == []
        assert result["overlap_graph"]["edges"] == []
