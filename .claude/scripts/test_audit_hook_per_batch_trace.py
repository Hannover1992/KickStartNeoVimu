#!/usr/bin/env python3
"""
test_audit_hook_per_batch_trace.py — BL-230 SB-2 RED: AK-PER-BATCH-TRACE.

Failing tests (RED phase) for the per-batch audit-trace extension of audit_hook.py.
Written by the RED-Worker (BL-230 SB-2 RED). The GREEN-Worker hardens audit_hook.py
SEPARATELY (RED != GREEN, INV-BUILD-GRAIN). RED-Worker writes ONLY tests.

Gold: .claude/analysis/blueprints/BL-230/S1/blueprint.md (SB-2-Abschnitt, Slice
"Per-Batch-Trace", 4 Exit-Kriterien) + Edge-Cases EC-BT-1..4.

AK-PER-BATCH-TRACE (k=50, Spec SUPPORT_AK / BORDER-9 / FK-4/FK-6):
  - batch-id-keyed Stream: jeder parallele Worker schreibt batch-id-keyed (worker-lokal,
    kein Interleaving im geteilten audit.jsonl). worker_id_fields wird um ein batch_id-Feld
    erweitert (analog worktree_id, graceful: leer im seriellen Lauf).
  - deterministischer Merge nach batch_id (permutations-invariant, stabile Sortierung).
  - Inventur-Liste der batch_ids (vollstaendig, dedupliziert).
  - serieller Lauf byte-identisch: budget<=1 + bl_parallel=false -> {} (BL-194-N9 Verhalten).

RED-Erwartung:
  - TestWorkerIdFieldsBatchId (batch_id-Feld) FAILEN — worker_id_fields hat heute kein
    batch_id-Argument/-Feld (Z253-281).
  - TestMergePerBatchStreams (Merge-Funktion + Inventur) FAILEN — merge_per_batch_streams
    existiert nicht (greenfield, ImportError im Setup -> Tests FAIL).
  - TestWorkerIdFieldsSerialRegression (BL-194-N9 Kanarienvogel) GRUEN — die serielle
    {}-Konvention bleibt unangetastet.

Run: py -3 -m pytest .claude/scripts/test_audit_hook_per_batch_trace.py -q
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add scripts dir to path (analog test_audit_worker_id.py Z14).
sys.path.insert(0, str(Path(__file__).parent))

from audit_hook import worker_id_fields  # noqa: E402


def _maybe(name):
    """Import an attribute from audit_hook if present, else None.

    Returns None when the symbol does not exist yet (greenfield RED) — the test
    using it then fails its assertion explicitly (not via collection error).
    """
    import audit_hook  # noqa: E402
    return getattr(audit_hook, name, None)


# ===========================================================================
# AK-PER-BATCH-TRACE — Exit 1: batch-id-keyed Stream (worker_id_fields + batch_id-Feld).
# EC-BT-2: parallel aktiv + batch_id gesetzt -> Eintrag traegt batch_id-Feld.
# ===========================================================================

class TestWorkerIdFieldsBatchId:
    def test_parallel_with_batch_id_emits_batch_id_field(self):
        """EC-BT-2: budget>1 + worker_id + batch_id -> dict enthaelt batch_id-Feld."""
        result = worker_id_fields(
            parallelism_budget=2,
            worker_id="terminal-A",
            batch_id="BL-230-SB-2",
        )
        assert "batch_id" in result
        assert result["batch_id"] == "BL-230-SB-2"

    def test_batch_id_alongside_worktree_id_and_lane(self):
        """batch_id steht neben worker_id/lane/worktree_id (analoge graceful-Konvention)."""
        result = worker_id_fields(
            parallelism_budget=2,
            worker_id="terminal-B",
            lane="A",
            worktree_id="WT-1",
            batch_id="BL-230-SB-2",
        )
        assert result["worker_id"] == "terminal-B"
        assert result["lane"] == "A"
        assert result["worktree_id"] == "WT-1"
        assert result["batch_id"] == "BL-230-SB-2"

    def test_parallel_without_batch_id_omits_field(self):
        """graceful: parallel aktiv, aber batch_id=None -> KEIN batch_id-Feld (analog worktree_id)."""
        result = worker_id_fields(
            parallelism_budget=2,
            worker_id="terminal-C",
            batch_id=None,
        )
        assert "worker_id" in result
        assert "batch_id" not in result

    def test_bl_parallel_activates_batch_id_at_budget_1(self):
        """bl_parallel=True ueberstimmt budget=1 -> batch_id-Feld trotzdem gesetzt."""
        result = worker_id_fields(
            parallelism_budget=1,
            worker_id="terminal-D",
            batch_id="BL-230-SB-2",
            bl_parallel=True,
        )
        assert result.get("batch_id") == "BL-230-SB-2"


# ===========================================================================
# AK-PER-BATCH-TRACE — Exit 4 (Null-Regression): serieller Lauf byte-identisch.
# EC-BT-1: budget<=1 + bl_parallel=false -> {} (BL-194-N9 byte-identisch).
# Das ist der KANARIENVOGEL — MUSS schon GRUEN sein (RED-Worker bricht ihn NICHT).
# ===========================================================================

class TestWorkerIdFieldsSerialRegression:
    def test_serial_with_batch_id_still_empty(self):
        """EC-BT-1 (RED): budget=1 + bl_parallel=false -> {} auch wenn batch_id gesetzt.

        Faellt heute mit TypeError (Signatur kennt batch_id nicht) -> RED fuer das neue
        Feature. NACH GREEN muss der serielle Pfad trotz gesetztem batch_id {} liefern
        (BL-194-N9 byte-identisch). Der PURE Kanarienvogel (alte Signatur, kein batch_id)
        ist test_serial_no_worker_id_empty + die 5 Tests in test_audit_worker_id.py — die
        bleiben unangetastet GRUEN.
        """
        result = worker_id_fields(
            parallelism_budget=1,
            worker_id="terminal-E",
            batch_id="BL-230-SB-2",
        )
        assert result == {}

    def test_serial_no_worker_id_empty(self):
        """[GUARD]: serieller Lauf ohne worker_id -> {} (unveraendert)."""
        result = worker_id_fields(parallelism_budget=1, worker_id=None)
        assert result == {}


# ===========================================================================
# AK-PER-BATCH-TRACE — Exit 2 + 3: deterministischer Merge nach batch_id + Inventur-Liste.
# merge_per_batch_streams(streams) -> (merged_stream, inventory). Greenfield: existiert noch nicht.
# EC-BT-3: Merge in beliebiger Reihenfolge -> identisches Ergebnis (Permutations-invariant).
# EC-BT-4: leere Stream-Liste -> leerer Stream + leere Inventur, kein Crash.
# ===========================================================================

class TestMergePerBatchStreams:
    def _merge(self):
        fn = _maybe("merge_per_batch_streams")
        assert fn is not None, (
            "merge_per_batch_streams fehlt in audit_hook.py (greenfield RED — "
            "AK-PER-BATCH-TRACE Exit 2/3 nicht implementiert)"
        )
        return fn

    def test_merge_function_exists(self):
        """Exit 2/3: die Merge-Funktion merge_per_batch_streams existiert."""
        assert _maybe("merge_per_batch_streams") is not None

    def test_merge_deterministic_permutation_invariant(self):
        """EC-BT-3: zwei per-Batch-Streams in beliebiger Reihenfolge -> identisches Merge-Ergebnis."""
        merge = self._merge()
        stream_a = [{"batch_id": "sb1", "event": "x1"}, {"batch_id": "sb1", "event": "x2"}]
        stream_b = [{"batch_id": "sb2", "event": "y1"}]
        merged_ab, _inv_ab = merge([stream_a, stream_b])
        merged_ba, _inv_ba = merge([stream_b, stream_a])
        # Stabile Sortierung nach batch_id -> reihenfolge-unabhaengig identisch.
        assert merged_ab == merged_ba

    def test_merge_sorted_by_batch_id(self):
        """Exit 2: das gemergte Ergebnis ist stabil nach batch_id sortiert."""
        merge = self._merge()
        stream_z = [{"batch_id": "sb9", "event": "z"}]
        stream_a = [{"batch_id": "sb1", "event": "a"}]
        merged, _inv = merge([stream_z, stream_a])
        batch_ids_in_order = [e["batch_id"] for e in merged]
        assert batch_ids_in_order == sorted(batch_ids_in_order)

    def test_merge_inventory_complete_and_deduped(self):
        """Exit 3: Inventur == Menge der eingegebenen batch_ids (vollstaendig, dedupliziert)."""
        merge = self._merge()
        stream_a = [{"batch_id": "sb1", "event": "x1"}, {"batch_id": "sb1", "event": "x2"}]
        stream_b = [{"batch_id": "sb2", "event": "y1"}]
        _merged, inventory = merge([stream_a, stream_b])
        assert set(inventory) == {"sb1", "sb2"}
        # Dedupliziert: sb1 erscheint zweimal im Stream, aber nur einmal in der Inventur.
        assert len(inventory) == len(set(inventory))

    def test_merge_empty_list_no_crash(self):
        """EC-BT-4: leere Stream-Liste -> leerer Stream + leere Inventur, kein Crash."""
        merge = self._merge()
        merged, inventory = merge([])
        assert merged == []
        assert list(inventory) == []
