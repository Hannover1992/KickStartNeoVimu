"""
test_bdf_bl_visualize.py — Tests fuer bdf_bl_visualize.py
BL-176 AK-8, PL-176-024

Tests:
  - test_mermaid_output_format
  - test_ascii_output_format
  - test_bucket_coloring
  - test_empty_snapshot
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Sicherstellen dass scripts/ im Path ist
sys.path.insert(0, str(Path(__file__).parent))

from bdf_bl_visualize import (
    build_output,
    generate_ascii,
    generate_mermaid,
    get_bucket_for_bl,
    load_snapshot,
)


def make_snapshot(
    bls: list,
    deps: dict = None,
    buckets: dict = None,
    sequence: list = None,
) -> dict:
    """Hilfsfunktion: baut minimales Snapshot-Dict fuer Tests."""
    matrix = {bl: deps.get(bl, []) if deps else [] for bl in bls}
    buckets_data = {}
    if buckets:
        bucket_list = {}
        for idx, bucket_bls in enumerate(buckets):
            bucket_list[f"bucket-{idx}"] = {
                "bls": bucket_bls,
                "parallel": idx > 0,
            }
        buckets_data = {
            "bucket_count": len(buckets),
            "buckets": bucket_list,
        }
    seq_data = {"sequence": sequence or bls}
    matrix_data = {"matrix": matrix, "bl_count": len(bls)}
    return {
        "buckets": buckets_data,
        "matrix": matrix_data,
        "sequence": seq_data,
    }


class TestMermaidOutputFormat:
    """test_mermaid_output_format: Prueft Grundstruktur des Mermaid-Outputs."""

    def test_mermaid_starts_with_code_block(self):
        snapshot = make_snapshot(["BL-100", "BL-101"])
        output = generate_mermaid(snapshot)
        assert output.startswith("```mermaid"), "Mermaid-Block muss mit ```mermaid beginnen"

    def test_mermaid_contains_graph_td(self):
        snapshot = make_snapshot(["BL-100", "BL-101"])
        output = generate_mermaid(snapshot)
        assert "graph TD" in output, "Mermaid muss 'graph TD' enthalten"

    def test_mermaid_contains_node_for_each_bl(self):
        bls = ["BL-100", "BL-101", "BL-102"]
        snapshot = make_snapshot(bls)
        output = generate_mermaid(snapshot)
        for bl in bls:
            safe = bl.replace("-", "_")
            assert safe in output, f"Node fuer {bl} fehlt im Mermaid-Output"

    def test_mermaid_contains_edge_for_dependency(self):
        snapshot = make_snapshot(
            ["BL-100", "BL-101"],
            deps={"BL-101": ["BL-100"]},
        )
        output = generate_mermaid(snapshot)
        assert "BL_100 --> BL_101" in output, "Edge BL-100 --> BL-101 fehlt"

    def test_mermaid_ends_with_closing_backticks(self):
        snapshot = make_snapshot(["BL-100"])
        output = generate_mermaid(snapshot)
        assert "```" in output[output.index("```mermaid") + 9:], "Schliessender Code-Block fehlt"


class TestAsciiOutputFormat:
    """test_ascii_output_format: Prueft ASCII-Tabellen-Struktur."""

    def test_ascii_contains_header(self):
        snapshot = make_snapshot(["BL-100", "BL-101"])
        output = generate_ascii(snapshot)
        assert "BL Interest-Radius Snapshot" in output

    def test_ascii_contains_separator_line(self):
        snapshot = make_snapshot(["BL-100"])
        output = generate_ascii(snapshot)
        assert "---" in output or "---" in output, "Separator-Linie fehlt in ASCII-Output"

    def test_ascii_contains_all_bls(self):
        bls = ["BL-100", "BL-101", "BL-102"]
        snapshot = make_snapshot(bls)
        output = generate_ascii(snapshot)
        for bl in bls:
            assert bl in output, f"{bl} fehlt in ASCII-Tabelle"

    def test_ascii_shows_dependencies(self):
        snapshot = make_snapshot(
            ["BL-100", "BL-101"],
            deps={"BL-101": ["BL-100"]},
            sequence=["BL-100", "BL-101"],
        )
        output = generate_ascii(snapshot)
        # BL-101 sollte BL-100 als Dependency zeigen
        lines = output.split("\n")
        bl_101_line = next((l for l in lines if "BL-101" in l and "BL_" not in l), None)
        assert bl_101_line is not None
        assert "BL-100" in bl_101_line, "Dependency BL-100 fehlt in BL-101 Zeile"

    def test_ascii_bucket_summary_present(self):
        snapshot = make_snapshot(
            ["BL-100", "BL-101"],
            buckets=[["BL-100"], ["BL-101"]],
        )
        output = generate_ascii(snapshot)
        assert "Bucket Summary" in output, "Bucket-Summary fehlt in ASCII-Output"


class TestBucketColoring:
    """test_bucket_coloring: Prueft dass Buckets korrekte Farb-Klassen erhalten."""

    def test_bucket_0_has_green_color_class(self):
        snapshot = make_snapshot(
            ["BL-100", "BL-101"],
            buckets=[["BL-100"], ["BL-101"]],
        )
        output = generate_mermaid(snapshot)
        # Bucket 0 sollte classDef bucket0 mit gruen-artiger Fill haben
        assert "classDef bucket0" in output, "classDef bucket0 fehlt"
        assert "fill:#e8f5e9" in output, "Gruen-Fill fuer Bucket-0 fehlt"

    def test_bucket_1_has_blue_color_class(self):
        snapshot = make_snapshot(
            ["BL-100", "BL-101"],
            buckets=[["BL-100"], ["BL-101"]],
        )
        output = generate_mermaid(snapshot)
        assert "classDef bucket1" in output, "classDef bucket1 fehlt"
        assert "fill:#e3f2fd" in output, "Blau-Fill fuer Bucket-1 fehlt"

    def test_bl_assigned_to_correct_bucket_class(self):
        snapshot = make_snapshot(
            ["BL-100", "BL-101"],
            buckets=[["BL-100"], ["BL-101"]],
        )
        output = generate_mermaid(snapshot)
        # BL_100 sollte class bucket0 haben
        lines = output.split("\n")
        class_lines = [l for l in lines if l.strip().startswith("class ") and "bucket" in l]
        bucket0_line = next((l for l in class_lines if "bucket0" in l), None)
        assert bucket0_line is not None, "Bucket-0 class-Zuweisung fehlt"
        assert "BL_100" in bucket0_line, "BL_100 nicht in Bucket-0 Klasse"

    def test_get_bucket_for_bl_returns_correct_index(self):
        buckets_data = {
            "bucket_count": 2,
            "buckets": {
                "bucket-0": {"bls": ["BL-100"], "parallel": False},
                "bucket-1": {"bls": ["BL-101"], "parallel": True},
            },
        }
        assert get_bucket_for_bl("BL-100", buckets_data) == 0
        assert get_bucket_for_bl("BL-101", buckets_data) == 1
        assert get_bucket_for_bl("BL-999", buckets_data) == -1


class TestEmptySnapshot:
    """test_empty_snapshot: Prueft Verhalten bei leerem oder fehlendem Snapshot."""

    def test_empty_snapshot_mermaid_doesnt_crash(self):
        output = generate_mermaid({})
        assert "```mermaid" in output, "Mermaid-Block muss auch bei leerem Snapshot produziert werden"
        assert "No BLs" in output or "EMPTY" in output, "Leerer Snapshot soll EMPTY-Node zeigen"

    def test_empty_snapshot_ascii_doesnt_crash(self):
        output = generate_ascii({})
        assert "No data" in output or "BL Interest-Radius" in output

    def test_empty_snapshot_build_output_both(self):
        output = build_output({}, "both")
        assert output is not None
        assert len(output) > 0

    def test_load_snapshot_from_nonexistent_dir_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Kein interest_radius Unterordner → leeres Dict
            snapshot = load_snapshot(tmpdir)
            assert isinstance(snapshot, dict)
            assert len(snapshot) == 0

    def test_load_snapshot_from_existing_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            interest_dir = Path(tmpdir) / "Vault" / "Meta" / "interest_radius"
            interest_dir.mkdir(parents=True)

            matrix_data = {"generated_at": "2026-05-19", "matrix": {"BL-100": []}, "bl_count": 1}
            with open(interest_dir / "bl_dependency_matrix.json", "w") as f:
                json.dump(matrix_data, f)

            snapshot = load_snapshot(tmpdir)
            assert "matrix" in snapshot
            assert snapshot["matrix"]["bl_count"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
