#!/usr/bin/env python3
"""
test_audit_fanin.py — Tests fuer audit_fanin.py (BL-317 SB-3, AK-4).

Append-only-Concat-Fan-In-Helper fuer worker-lokale audit.jsonl-Streams.

Vertrag (INV-G3-5): worker-lokale audit.jsonl sind volatil + gitignored.
Fan-In = append-only KONKATENATION (kommutativ, reihenfolge-unabhaengig als
Zeilen-MENGE) — kein contended Single-Stream, kein Lock, keine Merge-Konflikte.

Test-Achsen:
  (a) 2 worker-audit.jsonls -> Concat enthaelt alle Zeilen beider.
  (b) Kommutativitaet: concat(A,B) hat dieselbe Zeilen-MENGE wie concat(B,A).
  (c) leere/fehlende Datei -> robust (kein Crash).
  (d) idempotent/append-only: keine Zeile verloren/dupliziert bei korrektem Input.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import pytest

_SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(_SCRIPT_DIR))

from audit_fanin import fan_in_audit_streams, fan_in_to_file


# ── Fixtures ───────────────────────────────────────────────────────────────────

def _write_jsonl(path: Path, lines):
    """Schreibt JSONL-Zeilen (append-only Format: 1 Objekt-Zeile pro Eintrag)."""
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


@pytest.fixture
def worker_a(tmp_path):
    p = tmp_path / "wt_a" / ".claude" / "audit" / "audit.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(p, [
        '{"ts":"2026-06-12T10:00:00","event":"HANDOFF","skill":"_A_orchestrate"}',
        '{"ts":"2026-06-12T10:01:00","event":"WORKER_SPAWN","level":"A"}',
    ])
    return p


@pytest.fixture
def worker_b(tmp_path):
    p = tmp_path / "wt_b" / ".claude" / "audit" / "audit.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(p, [
        '{"ts":"2026-06-12T10:00:30","event":"HANDOFF","skill":"_SDF_orchestrate"}',
        '{"ts":"2026-06-12T10:02:00","event":"STATE_WRITE","file":"_manifest.md"}',
    ])
    return p


# ── (a) Concat enthaelt alle Zeilen beider ───────────────────────────────────────

class TestConcatCompleteness:
    def test_concat_contains_all_lines_of_both(self, worker_a, worker_b):
        merged = fan_in_audit_streams([worker_a, worker_b])
        a_lines = worker_a.read_text(encoding="utf-8").splitlines()
        b_lines = worker_b.read_text(encoding="utf-8").splitlines()
        for line in a_lines + b_lines:
            assert line in merged, f"verlorene Zeile: {line}"

    def test_concat_line_count_equals_sum(self, worker_a, worker_b):
        merged = fan_in_audit_streams([worker_a, worker_b])
        a_n = len([l for l in worker_a.read_text(encoding="utf-8").splitlines() if l.strip()])
        b_n = len([l for l in worker_b.read_text(encoding="utf-8").splitlines() if l.strip()])
        assert len([l for l in merged if l.strip()]) == a_n + b_n


# ── (b) Kommutativitaet (reihenfolge-unabhaengige Zeilen-MENGE) ──────────────────

class TestCommutativity:
    def test_concat_ab_same_multiset_as_ba(self, worker_a, worker_b):
        ab = fan_in_audit_streams([worker_a, worker_b])
        ba = fan_in_audit_streams([worker_b, worker_a])
        # Reihenfolge-unabhaengig: dieselbe MULTI-MENGE (Counter) von Zeilen.
        assert Counter(l for l in ab if l.strip()) == Counter(l for l in ba if l.strip())

    def test_concat_three_streams_any_order_same_multiset(self, tmp_path, worker_a, worker_b):
        c = tmp_path / "wt_c" / ".claude" / "audit" / "audit.jsonl"
        c.parent.mkdir(parents=True, exist_ok=True)
        _write_jsonl(c, ['{"ts":"2026-06-12T10:03:00","event":"SKILL_LOAD","skill_name":"_I_orchestrate"}'])
        order1 = Counter(l for l in fan_in_audit_streams([worker_a, worker_b, c]) if l.strip())
        order2 = Counter(l for l in fan_in_audit_streams([c, worker_a, worker_b]) if l.strip())
        order3 = Counter(l for l in fan_in_audit_streams([worker_b, c, worker_a]) if l.strip())
        assert order1 == order2 == order3


# ── (c) leere/fehlende Datei -> robust ──────────────────────────────────────────

class TestRobustness:
    def test_missing_file_does_not_crash(self, worker_a, tmp_path):
        missing = tmp_path / "nope" / "audit.jsonl"
        merged = fan_in_audit_streams([worker_a, missing])
        a_lines = [l for l in worker_a.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert [l for l in merged if l.strip()] == a_lines  # nur A's Zeilen, kein Crash

    def test_empty_file_yields_no_lines(self, tmp_path):
        empty = tmp_path / "empty" / "audit.jsonl"
        empty.parent.mkdir(parents=True, exist_ok=True)
        empty.write_text("", encoding="utf-8")
        merged = fan_in_audit_streams([empty])
        assert [l for l in merged if l.strip()] == []

    def test_empty_input_list_yields_no_lines(self):
        assert fan_in_audit_streams([]) == []

    def test_blank_lines_are_skipped(self, tmp_path):
        p = tmp_path / "wt" / "audit.jsonl"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text('{"a":1}\n\n   \n{"b":2}\n', encoding="utf-8")
        merged = fan_in_audit_streams([p])
        assert merged == ['{"a":1}', '{"b":2}']


# ── (d) idempotent / append-only: keine Zeile verloren/dupliziert ────────────────

class TestAppendOnlyIdempotent:
    def test_no_line_lost_or_duplicated(self, worker_a, worker_b):
        merged = fan_in_audit_streams([worker_a, worker_b])
        expected = Counter()
        for src in (worker_a, worker_b):
            for l in src.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    expected[l] += 1
        assert Counter(l for l in merged if l.strip()) == expected

    def test_single_source_roundtrip_identical(self, worker_a):
        merged = fan_in_audit_streams([worker_a])
        src = [l for l in worker_a.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert merged == src  # append-only: keine Mutation einer Einzelquelle

    def test_no_conflict_markers_in_output(self, worker_a, worker_b):
        merged = fan_in_audit_streams([worker_a, worker_b])
        for line in merged:
            assert not line.startswith("<<<<<<<")
            assert not line.startswith(">>>>>>>")
            assert not line.startswith("=======")

    def test_fan_in_to_file_writes_valid_jsonl(self, worker_a, worker_b, tmp_path):
        out = tmp_path / "merged" / "audit.jsonl"
        n = fan_in_to_file([worker_a, worker_b], out)
        written = [l for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
        assert n == len(written)
        # Multi-Menge identisch zu Quelle (keine Zeile verloren/dupliziert)
        expected = Counter()
        for src in (worker_a, worker_b):
            for l in src.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    expected[l] += 1
        assert Counter(written) == expected

    def test_fan_in_to_file_append_only_accumulates(self, worker_a, worker_b, tmp_path):
        """Zweiter Fan-In an dieselbe Datei haengt an (append-only), ueberschreibt nicht."""
        out = tmp_path / "merged" / "audit.jsonl"
        fan_in_to_file([worker_a], out, append=True)
        fan_in_to_file([worker_b], out, append=True)
        written = [l for l in out.read_text(encoding="utf-8").splitlines() if l.strip()]
        a_n = len([l for l in worker_a.read_text(encoding="utf-8").splitlines() if l.strip()])
        b_n = len([l for l in worker_b.read_text(encoding="utf-8").splitlines() if l.strip()])
        assert len(written) == a_n + b_n


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
