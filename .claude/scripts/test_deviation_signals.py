# -*- coding: utf-8 -*-
"""Tests fuer deviation_signals.py (BL-252 AK-1 — reiner Signal-Sammler).

M3, RED->GREEN. Nutzt ausschliesslich tmp-Fixtures (Mini-audit.jsonl + Mini-Manifest/Index).
Mutiert NIEMALS die echten Live-Dateien.
"""
import json
import os
import sys

import pytest

# Sammler-Import (RED bei Erst-Lauf: ImportError, weil Modul noch nicht existiert)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deviation_signals import (  # noqa: E402
    collect_deviation_signals,
    _scan_audit,
    _scan_counter_drift,
    _scan_status_drift,
    _scan_disciplinary_reports,
    SIGNAL_FIELDS,
)
import disciplinary_report as _dr  # noqa: E402 — BL-324 AK-4 Quelle


# ---------------------------------------------------------------------------
# Fixtures: Mini-Manifest, Mini-Index, Mini-Audit (alle in tmp)
# ---------------------------------------------------------------------------

def _write_manifest(path, counter):
    path.write_text(
        "**BACKLOG_STATE:**\n"
        f"  backlog_counter: {counter}\n"
        f"  backlog_last_id: BL-{counter}\n"
        "  backlog_last_update: 2026-06-13\n",
        encoding="utf-8",
    )


def _write_index(path, counter, rows):
    """rows: Liste von (bl_id, title, status)."""
    lines = [
        "---",
        "format_version: 1",
        f"backlog_counter: {counter}",
        'backlog_last_update: "2026-06-13"',
        "---",
        "",
        "# Backlog Index",
        "",
        "| BL-ID | Title | Status | Vault-Pfad | Created | Reifegrad |",
        "|-------|-------|--------|------------|---------|-----------|",
    ]
    for bl_id, title, status in rows:
        lines.append(f"| {bl_id} | {title} | {status} | Backlog\\{bl_id}.md | 2026-06-01 |  |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_bl(backlog_dir, bl_id, status):
    fp = backlog_dir / f"{bl_id}.md"
    fp.write_text(
        "---\n"
        f"id: {bl_id}\n"
        f"title: {bl_id}_titel\n"
        f"status: {status}\n"
        "---\n\n# Body\n",
        encoding="utf-8",
    )
    return fp


def _write_audit(path, events):
    with path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


@pytest.fixture
def vault(tmp_path):
    """Ein vollstaendiger tmp-Vault: Manifest, Index, Backlog/-Dir."""
    backlog = tmp_path / "Backlog"
    backlog.mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Counter-Drift
# ---------------------------------------------------------------------------

def test_counter_drift_detected(vault):
    _write_manifest(vault / "_manifest.md", 345)
    _write_index(vault / "_backlog_index.md", 340, [("BL-001", "T", "DONE")])
    sigs = _scan_counter_drift(vault)
    drift = [s for s in sigs if s["kind"] == "counter_drift"]
    assert len(drift) == 1
    ev = drift[0]["evidence"]
    assert ev["manifest_counter"] == 345
    assert ev["index_counter"] == 340


def test_counter_no_drift_when_equal(vault):
    _write_manifest(vault / "_manifest.md", 345)
    _write_index(vault / "_backlog_index.md", 345, [("BL-001", "T", "DONE")])
    sigs = _scan_counter_drift(vault)
    assert [s for s in sigs if s["kind"] == "counter_drift"] == []


# ---------------------------------------------------------------------------
# Status-Drift
# ---------------------------------------------------------------------------

def test_status_drift_detected(vault):
    _write_manifest(vault / "_manifest.md", 2)
    _write_index(
        vault / "_backlog_index.md", 2,
        [("BL-001", "T1", "DONE"), ("BL-002", "T2", "DRAFT")],
    )
    # BL-002 Frontmatter sagt DONE, Index sagt DRAFT -> Drift
    _write_bl(vault / "Backlog", "BL-001", "DONE")
    _write_bl(vault / "Backlog", "BL-002", "DONE")
    sigs = _scan_status_drift(vault)
    drift = [s for s in sigs if s["kind"] == "status_drift"]
    assert len(drift) == 1
    ev = drift[0]["evidence"]
    assert ev["bl_id"] == "BL-002"
    assert ev["frontmatter_status"] == "DONE"
    assert ev["index_status"] == "DRAFT"


def test_status_no_drift_when_aligned(vault):
    _write_manifest(vault / "_manifest.md", 1)
    _write_index(vault / "_backlog_index.md", 1, [("BL-001", "T1", "DONE")])
    _write_bl(vault / "Backlog", "BL-001", "DONE")
    sigs = _scan_status_drift(vault)
    assert [s for s in sigs if s["kind"] == "status_drift"] == []


def test_status_drift_ignores_missing_frontmatter(vault):
    # Index hat BL-009 aber keine BL-Datei -> kein Crash, kein Drift-Signal
    _write_manifest(vault / "_manifest.md", 9)
    _write_index(vault / "_backlog_index.md", 9, [("BL-009", "Ghost", "DRAFT")])
    sigs = _scan_status_drift(vault)
    assert [s for s in sigs if s["kind"] == "status_drift"] == []


# ---------------------------------------------------------------------------
# Audit-Anomalien
# ---------------------------------------------------------------------------

ANOMALY_EVENTS = [
    {"ts": "2026-06-01T10:00:00", "event": "GUARD_BLOCK", "violation": "DIRECT_IMPL_BYPASS"},
    {"ts": "2026-06-01T10:01:00", "event": "HARD_GATE_BLOCK", "reason": "active_team missing"},
    {"ts": "2026-06-01T10:02:00", "event": "LOCK_STALE_RECLAIM", "old_holder": "x"},
    {"ts": "2026-06-01T10:03:00", "event": "WORKER_RUNAWAY_BLOCKED", "detail": {}},
    {"ts": "2026-06-01T10:04:00", "event": "ROLLBACK", "reason": "SKILL_LOAD_VIOLATION"},
]
NORMAL_EVENTS = [
    {"ts": "2026-06-01T09:00:00", "event": "WORKER_SPAWN"},
    {"ts": "2026-06-01T09:01:00", "event": "SKILL_LOAD", "skill_name": "_A_orchestrate"},
    {"ts": "2026-06-01T09:02:00", "event": "STATE_WRITE", "file": "_manifest.md"},
    {"ts": "2026-06-01T09:03:00", "event": "LOCK_CLAIMED"},
    {"ts": "2026-06-01T09:04:00", "event": "HANDOFF"},
]


def test_audit_anomaly_detected(tmp_path):
    ap = tmp_path / "audit.jsonl"
    _write_audit(ap, [ANOMALY_EVENTS[0]])
    sigs = _scan_audit(audit_path=ap)
    assert len(sigs) == 1
    assert sigs[0]["kind"] == "guard_block"
    assert sigs[0]["source"] == "audit"


def test_audit_normal_events_not_over_reported(tmp_path):
    ap = tmp_path / "audit.jsonl"
    _write_audit(ap, NORMAL_EVENTS)
    sigs = _scan_audit(audit_path=ap)
    assert sigs == [], f"Normal-Events wurden als Signal gemeldet: {sigs}"


def test_audit_mixed_only_anomalies(tmp_path):
    ap = tmp_path / "audit.jsonl"
    # interleaved: 5 anomalies + 5 normals
    mixed = []
    for a, n in zip(ANOMALY_EVENTS, NORMAL_EVENTS):
        mixed.append(n)
        mixed.append(a)
    _write_audit(ap, mixed)
    sigs = _scan_audit(audit_path=ap)
    assert len(sigs) == len(ANOMALY_EVENTS)
    kinds = {s["kind"] for s in sigs}
    assert kinds == {
        "guard_block",
        "hard_gate_block",
        "stale_lock_reclaim",
        "worker_runaway",
        "rollback",
    }


def test_audit_since_filter(tmp_path):
    ap = tmp_path / "audit.jsonl"
    old = {"ts": "2026-05-01T00:00:00", "event": "GUARD_BLOCK"}
    new = {"ts": "2026-06-10T00:00:00", "event": "GUARD_BLOCK"}
    _write_audit(ap, [old, new])
    sigs = _scan_audit(audit_path=ap, since="2026-06-01T00:00:00")
    assert len(sigs) == 1
    assert sigs[0]["first_seen"] == "2026-06-10T00:00:00"


# ---------------------------------------------------------------------------
# Robustheit: leere/fehlende Quellen
# ---------------------------------------------------------------------------

def test_empty_audit_no_crash(tmp_path):
    ap = tmp_path / "audit.jsonl"
    ap.write_text("", encoding="utf-8")
    assert _scan_audit(audit_path=ap) == []


def test_missing_audit_no_crash(tmp_path):
    ap = tmp_path / "does_not_exist.jsonl"
    assert _scan_audit(audit_path=ap) == []


def test_malformed_audit_line_skipped(tmp_path):
    ap = tmp_path / "audit.jsonl"
    ap.write_text(
        '{"ts": "2026-06-01T10:00:00", "event": "GUARD_BLOCK"}\n'
        "NOT JSON AT ALL\n"
        "\n"
        '{"ts": "2026-06-01T10:01:00", "event": "WORKER_SPAWN"}\n',
        encoding="utf-8",
    )
    sigs = _scan_audit(audit_path=ap)
    assert len(sigs) == 1
    assert sigs[0]["kind"] == "guard_block"


def test_missing_manifest_no_crash(vault):
    # nur Index, kein Manifest
    _write_index(vault / "_backlog_index.md", 5, [("BL-001", "T", "DONE")])
    sigs = _scan_counter_drift(vault)
    assert sigs == []


def test_missing_index_no_crash(vault):
    _write_manifest(vault / "_manifest.md", 5)
    assert _scan_counter_drift(vault) == []
    assert _scan_status_drift(vault) == []


def test_empty_vault_collect_returns_empty(tmp_path):
    # Voellig leer: kein Manifest, kein Index, keine Audit -> leere Liste, kein Crash.
    # BL-346/BL-324-Isolation: report_path MUSS auf eine tmp-Datei zeigen, sonst liest
    # _scan_disciplinary_reports die ECHTE .claude/audit/disciplinary_report.jsonl
    # (die seit dem Feldjaeger-Dogfood echte Eintraege traegt) -> Test-Leck. Jede Quelle
    # (audit_path / vault_root / report_path) muss fuer Isolation gesetzt sein.
    sigs = collect_deviation_signals(
        vault_root=tmp_path, audit_path=tmp_path / "nope.jsonl",
        report_path=tmp_path / "no_disciplinary.jsonl",
    )
    assert sigs == []


# ---------------------------------------------------------------------------
# Schema-Konsistenz + Integration
# ---------------------------------------------------------------------------

def test_all_signals_have_required_fields(vault, tmp_path):
    _write_manifest(vault / "_manifest.md", 345)
    _write_index(
        vault / "_backlog_index.md", 340,
        [("BL-001", "T1", "DONE"), ("BL-002", "T2", "DRAFT")],
    )
    _write_bl(vault / "Backlog", "BL-001", "DONE")
    _write_bl(vault / "Backlog", "BL-002", "DONE")  # Drift
    ap = tmp_path / "audit.jsonl"
    _write_audit(ap, ANOMALY_EVENTS + NORMAL_EVENTS)

    # report_path isoliert die ECHTE disciplinary_report.jsonl (BL-324 AK-4 4. Quelle);
    # "disciplinary" ist seit AK-4 eine valide source (Whitelist nachgezogen).
    sigs = collect_deviation_signals(
        vault_root=vault, audit_path=ap, report_path=tmp_path / "no_disciplinary.jsonl"
    )
    assert len(sigs) >= 1
    for s in sigs:
        for field in SIGNAL_FIELDS:
            assert field in s, f"Pflichtfeld {field} fehlt in {s}"
        assert s["source"] in {"audit", "manifest", "index", "disciplinary"}
        assert s["severity_hint"] in {"low", "medium", "high"}


def test_collect_aggregates_all_sources(vault, tmp_path):
    _write_manifest(vault / "_manifest.md", 345)
    _write_index(
        vault / "_backlog_index.md", 340,
        [("BL-001", "T1", "DONE"), ("BL-002", "T2", "DRAFT")],
    )
    _write_bl(vault / "Backlog", "BL-001", "DONE")
    _write_bl(vault / "Backlog", "BL-002", "DONE")  # Drift
    ap = tmp_path / "audit.jsonl"
    _write_audit(ap, ANOMALY_EVENTS)

    sigs = collect_deviation_signals(vault_root=vault, audit_path=ap)
    kinds = {s["kind"] for s in sigs}
    assert "counter_drift" in kinds
    assert "status_drift" in kinds
    assert "guard_block" in kinds


# ---------------------------------------------------------------------------
# BL-324 AK-4: Lead-Selbst-Reports (disciplinary_report.jsonl) als 4. Quelle
# ---------------------------------------------------------------------------

def _write_disciplinary(path, entries):
    """Schreibt valide disciplinary-Report-Eintraege via append_report (tmp-Datei).

    Nutzt den echten Writer (Schema-konform) — mutiert NIE die Live-jsonl.
    """
    for e in entries:
        assert _dr.append_report(e, report_path=str(path)) is True


def _disc_entry(deviation_class="machine_missed_catch", was_correct=True, ts=None):
    e = {
        "deviation_class": deviation_class,
        "kontext": "tmp-test-kontext",
        "lead_reasoning": "tmp-grund",
        "machine_should_have": "tmp-maschine",
        "learning_signal": "tmp-lehre",
        "was_correct": was_correct,
        "proposed_hardening": "tmp-fix",
    }
    if ts is not None:
        e["ts"] = ts
    return e


def test_disciplinary_entry_yields_signal(tmp_path):
    dp = tmp_path / "disciplinary_report.jsonl"
    _write_disciplinary(dp, [_disc_entry(deviation_class="tier_leak", ts="2026-06-13T10:00:00Z")])
    sigs = _scan_disciplinary_reports(report_path=dp)
    assert len(sigs) == 1
    s = sigs[0]
    assert s["source"] == "disciplinary"
    assert s["kind"] == "lead_deviation_tier_leak"
    assert s["first_seen"] == "2026-06-13T10:00:00Z"
    # evidence ist der rohe Report-Eintrag
    assert s["evidence"]["deviation_class"] == "tier_leak"


def test_disciplinary_was_correct_severity_mapping(tmp_path):
    dp = tmp_path / "disciplinary_report.jsonl"
    _write_disciplinary(
        dp,
        [
            _disc_entry(was_correct=True),   # richtige Abweichung -> low
            _disc_entry(was_correct=False),  # falsch gewesene -> medium (gewichtiger)
        ],
    )
    sigs = _scan_disciplinary_reports(report_path=dp)
    assert len(sigs) == 2
    sev = [s["severity_hint"] for s in sigs]
    assert sev == ["low", "medium"]


def test_disciplinary_kind_per_class(tmp_path):
    dp = tmp_path / "disciplinary_report.jsonl"
    _write_disciplinary(dp, [_disc_entry(deviation_class=c) for c in _dr.DEVIATION_CLASSES])
    sigs = _scan_disciplinary_reports(report_path=dp)
    kinds = {s["kind"] for s in sigs}
    assert kinds == {"lead_deviation_" + c for c in _dr.DEVIATION_CLASSES}


def test_disciplinary_empty_file_no_signal(tmp_path):
    dp = tmp_path / "disciplinary_report.jsonl"
    dp.write_text("", encoding="utf-8")
    assert _scan_disciplinary_reports(report_path=dp) == []


def test_disciplinary_missing_file_no_crash(tmp_path):
    dp = tmp_path / "does_not_exist.jsonl"
    assert _scan_disciplinary_reports(report_path=dp) == []


def test_disciplinary_malformed_line_skipped(tmp_path):
    dp = tmp_path / "disciplinary_report.jsonl"
    # eine valide Zeile + Muell + Leerzeile
    with dp.open("w", encoding="utf-8") as f:
        f.write(json.dumps(_disc_entry()) + "\n")
        f.write("NICHT JSON {{{\n")
        f.write("\n")
    sigs = _scan_disciplinary_reports(report_path=dp)
    assert len(sigs) == 1
    assert sigs[0]["kind"] == "lead_deviation_machine_missed_catch"


def test_disciplinary_unknown_class_skipped(tmp_path):
    dp = tmp_path / "disciplinary_report.jsonl"
    # manuell eingeschmuggelte unbekannte Klasse (umgeht append-Validierung)
    with dp.open("w", encoding="utf-8") as f:
        f.write(json.dumps(_disc_entry()) + "\n")
        f.write(json.dumps({"deviation_class": "rogue_klasse", "ts": "x"}) + "\n")
    sigs = _scan_disciplinary_reports(report_path=dp)
    assert len(sigs) == 1
    assert all("rogue" not in s["kind"] for s in sigs)


def test_disciplinary_signals_have_required_fields(tmp_path):
    dp = tmp_path / "disciplinary_report.jsonl"
    _write_disciplinary(dp, [_disc_entry(was_correct=False)])
    sigs = _scan_disciplinary_reports(report_path=dp)
    assert sigs
    for s in sigs:
        for field in SIGNAL_FIELDS:
            assert field in s, f"Pflichtfeld {field} fehlt in {s}"
        assert s["source"] == "disciplinary"
        assert s["severity_hint"] in {"low", "medium", "high"}


def test_collect_includes_disciplinary_when_present(vault, tmp_path):
    # vollstaendiger Vault (sonst keine anderen Signale) + disciplinary-Quelle
    _write_manifest(vault / "_manifest.md", 1)
    _write_index(vault / "_backlog_index.md", 1, [("BL-001", "T", "DONE")])
    _write_bl(vault / "Backlog", "BL-001", "DONE")
    dp = tmp_path / "disciplinary_report.jsonl"
    _write_disciplinary(dp, [_disc_entry(deviation_class="foresight_luecke")])
    sigs = collect_deviation_signals(
        vault_root=vault, audit_path=tmp_path / "nope.jsonl", report_path=dp
    )
    kinds = {s["kind"] for s in sigs}
    assert "lead_deviation_foresight_luecke" in kinds


def test_collect_without_disciplinary_file_no_disciplinary_signal(vault, tmp_path):
    _write_manifest(vault / "_manifest.md", 1)
    _write_index(vault / "_backlog_index.md", 1, [("BL-001", "T", "DONE")])
    _write_bl(vault / "Backlog", "BL-001", "DONE")
    sigs = collect_deviation_signals(
        vault_root=vault,
        audit_path=tmp_path / "nope.jsonl",
        report_path=tmp_path / "missing_disciplinary.jsonl",
    )
    assert [s for s in sigs if s["source"] == "disciplinary"] == []


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
