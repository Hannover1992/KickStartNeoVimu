#!/usr/bin/env python3
"""BL-229 AK-F: manifest_reader.read_bl_block Dual-Read fuer offloaded Bloecke.

read_bl_block nutzt Exact-Match (`^## BLOCK$`, AK-CTX-2 — bleibt unveraendert).
Wenn aber ein GANZER Block durch AK-C-Offload nach _manifest_history_{date}.md
ausgelagert wurde, findet die per-BL-Manifest-Lesung None -> Reader meldet
"nicht vorhanden" (False-Negative). AK-F: additive Dual-Read-Fallback liest den
ausgelagerten Block, OHNE die Exact-Match-Semantik fuer inline-Bloecke zu aendern.

RED (vor Migration): read_bl_block fuer einen offloaded Block -> None.
GREEN (nach Migration): read_bl_block findet ihn in der History (additiver Fallback).
INV (AK-CTX-2): inline-Exact-Match unveraendert (bare-canonical=live).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import manifest_reader as mr


def _make_split_active(vault_root: Path) -> None:
    (vault_root / "_factory_manifest.md").write_text(
        "# Factory\n\n## BDF_PIPELINE_STATE\nphase: running\n", encoding="utf-8"
    )


def _make_bl(vault_root: Path, bl_id: str, manifest_body: str) -> Path:
    bl_folder = vault_root / "Backlog" / f"{bl_id}-test"
    bl_folder.mkdir(parents=True, exist_ok=True)
    (bl_folder / "_manifest.md").write_text(manifest_body, encoding="utf-8")
    return bl_folder


def test_read_bl_block_finds_offloaded_block(tmp_path):
    # Arrange: split aktiv; per-BL-Manifest enthaelt NUR die letzte Round.
    _make_split_active(tmp_path)
    bl_folder = _make_bl(
        tmp_path, "BL-RD",
        "---\nbl_id: BL-RD\n---\n\n## IDF_PIPELINE_STATE\nidf_status: active\n",
    )
    # AK-C-Offload: der gesuchte (frueher-Round) Block liegt in der History.
    (bl_folder / "_manifest_history_2026-06-10.md").write_text(
        "# Historie\n\n## A_PIPELINE_STATE\na_status: DONE_A\n",
        encoding="utf-8",
    )

    # Act: A_PIPELINE_STATE.a_status ist NICHT im per-BL-Manifest, nur offloaded.
    val = mr.read_bl_block("BL-RD", "A_PIPELINE_STATE.a_status", vault_root=tmp_path)

    # Assert: via Dual-Read-Fallback gefunden (kein False-Negative).
    assert val == "DONE_A", f"offloaded Block muss via Dual-Read lesbar sein, war: {val!r}"


def test_inline_exact_match_unchanged(tmp_path):
    # Arrange: Block ist inline im per-BL-Manifest (Standardfall, AK-CTX-2).
    _make_split_active(tmp_path)
    _make_bl(
        tmp_path, "BL-RD2",
        "---\nbl_id: BL-RD2\n---\n\n## IDF_PIPELINE_STATE\nidf_status: active\n",
    )

    # Act
    val = mr.read_bl_block("BL-RD2", "IDF_PIPELINE_STATE.idf_status", vault_root=tmp_path)

    # Assert: inline-Exact-Match weiterhin korrekt (unveraendert).
    assert val == "active"


def test_inline_takes_precedence_over_offloaded(tmp_path):
    # Arrange: Block existiert inline (live, bare-canonical) UND in History (alt).
    # Exact-Match-Live-Semantik (AK-CTX-2): inline gewinnt, History ist nur Fallback.
    _make_split_active(tmp_path)
    bl_folder = _make_bl(
        tmp_path, "BL-RD3",
        "---\nbl_id: BL-RD3\n---\n\n## IDF_PIPELINE_STATE\nidf_status: live\n",
    )
    (bl_folder / "_manifest_history_2026-06-10.md").write_text(
        "# Historie\n\n## IDF_PIPELINE_STATE\nidf_status: stale\n",
        encoding="utf-8",
    )

    # Act
    val = mr.read_bl_block("BL-RD3", "IDF_PIPELINE_STATE.idf_status", vault_root=tmp_path)

    # Assert: live (inline) gewinnt, NICHT stale (History). Kein newest-wins.
    assert val == "live", f"inline-live muss Vorrang vor offloaded-stale haben, war: {val!r}"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
