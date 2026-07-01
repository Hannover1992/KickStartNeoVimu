# -*- coding: utf-8 -*-
"""Tests fuer disciplinary_report.py — BL-324 batch_1 (Feldjaeger Lead-Abweichungs-Capture).

TDD M3. Template-Konventionen: deviation_signals/crown2_dedupe (cwd-stabil,
robust, Default-Pfad via Path(__file__).resolve()), test_guard_a_idf_handoff
(subprocess-CLI). KEINE echte Live-Prod-jsonl wird mutiert — alle Tests nutzen
tmp-Dateien (report_path-Param).

RED-Ringe:
  Ring 1 (Happy):     append_report schreibt + Readback liefert den Eintrag.
  Ring 2 (Schema):    fehlende Pflichtfelder -> reject (False, kein Append).
  Ring 3 (Klasse):    unbekannte deviation_class -> reject.
  Ring 4 (Aggregate): aggregate_by_class gruppiert nach Klasse (count/was_correct).
  Ring 5 (Robust):    leere/fehlende Datei -> {} / [] kein Crash; kaputte Zeile geskippt.
  Ring 6 (CLI):       __main__ --aggregate laeuft crash-frei (a96eb1c utf-8-Lehre).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
SCRIPT = SCRIPT_DIR / "disciplinary_report.py"

sys.path.insert(0, str(SCRIPT_DIR))
import disciplinary_report as dr  # noqa: E402


def _valid_entry(**overrides):
    """Ein schema-vollstaendiger Report-Eintrag (alle Pflichtfelder)."""
    base = {
        "deviation_class": "machine_missed_catch",
        "kontext": "acquire_bl 2-Owner-Race in BL-320-Session",
        "lead_reasoning": "TOCTOU zwischen rmtree und remkdir manuell erkannt",
        "machine_should_have": "Concurrency-Forward-Verify-Guard fehlte",
        "learning_signal": "Race-Klasse braucht Forward-Verify -> BL-344",
        "was_correct": True,
        "proposed_hardening": "_process_lock um acquire/reclaim (BL-344)",
    }
    base.update(overrides)
    return base


def _tmp_report():
    fd, path = tempfile.mkstemp(suffix="_disciplinary_report.jsonl")
    os.close(fd)
    # mkstemp legt eine leere Datei an; fuer den fehlende-Datei-Test loeschen wir sie ggf.
    return Path(path)


# ── Ring 1: Happy-Path append + readback ────────────────────────────────────

def test_append_and_readback():
    p = _tmp_report()
    try:
        ok = dr.append_report(_valid_entry(), report_path=str(p))
        assert ok is True
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) == 1
        obj = json.loads(lines[0])
        assert obj["deviation_class"] == "machine_missed_catch"
        assert obj["was_correct"] is True
        # ts wird automatisch gestempelt, wenn nicht mitgegeben
        assert "ts" in obj and obj["ts"]
    finally:
        p.unlink(missing_ok=True)


def test_append_preserves_explicit_ts():
    p = _tmp_report()
    try:
        e = _valid_entry(ts="2026-06-13T10:00:00Z")
        assert dr.append_report(e, report_path=str(p)) is True
        obj = json.loads(p.read_text(encoding="utf-8").splitlines()[0])
        assert obj["ts"] == "2026-06-13T10:00:00Z"
    finally:
        p.unlink(missing_ok=True)


def test_append_multiple_appends_not_overwrites():
    p = _tmp_report()
    try:
        dr.append_report(_valid_entry(), report_path=str(p))
        dr.append_report(_valid_entry(deviation_class="tier_leak"), report_path=str(p))
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) == 2
    finally:
        p.unlink(missing_ok=True)


# ── Ring 2: Schema-Validierung (fehlende Pflichtfelder) ──────────────────────

def test_missing_required_field_rejected():
    p = _tmp_report()
    try:
        e = _valid_entry()
        del e["learning_signal"]  # Pflichtfeld entfernen
        ok = dr.append_report(e, report_path=str(p))
        assert ok is False
        # Nichts geschrieben
        assert p.read_text(encoding="utf-8").strip() == ""
    finally:
        p.unlink(missing_ok=True)


def test_each_required_field_individually_enforced():
    for field in dr.REQUIRED_FIELDS:
        p = _tmp_report()
        try:
            e = _valid_entry()
            del e[field]
            assert dr.append_report(e, report_path=str(p)) is False, f"{field} nicht erzwungen"
        finally:
            p.unlink(missing_ok=True)


def test_non_dict_entry_rejected():
    p = _tmp_report()
    try:
        assert dr.append_report("not a dict", report_path=str(p)) is False
        assert dr.append_report(None, report_path=str(p)) is False
    finally:
        p.unlink(missing_ok=True)


def test_was_correct_must_be_bool():
    p = _tmp_report()
    try:
        e = _valid_entry(was_correct="yes")  # kein bool
        assert dr.append_report(e, report_path=str(p)) is False
    finally:
        p.unlink(missing_ok=True)


# ── Ring 3: unbekannte deviation_class ───────────────────────────────────────

def test_unknown_deviation_class_rejected():
    p = _tmp_report()
    try:
        e = _valid_entry(deviation_class="erfundene_klasse")
        assert dr.append_report(e, report_path=str(p)) is False
        assert p.read_text(encoding="utf-8").strip() == ""
    finally:
        p.unlink(missing_ok=True)


def test_all_five_classes_accepted():
    expected = {
        "bewusster_override",
        "improvisation_ohne_prozesspfad",
        "machine_missed_catch",
        "tier_leak",
        "foresight_luecke",
    }
    assert set(dr.DEVIATION_CLASSES) == expected
    for cls in dr.DEVIATION_CLASSES:
        p = _tmp_report()
        try:
            assert dr.append_report(_valid_entry(deviation_class=cls), report_path=str(p)) is True
        finally:
            p.unlink(missing_ok=True)


# ── Ring 4: aggregate_by_class ───────────────────────────────────────────────

def test_aggregate_groups_by_class():
    p = _tmp_report()
    try:
        dr.append_report(_valid_entry(was_correct=True), report_path=str(p))
        dr.append_report(_valid_entry(was_correct=False), report_path=str(p))
        dr.append_report(_valid_entry(deviation_class="tier_leak", was_correct=True),
                         report_path=str(p))
        agg = dr.aggregate_by_class(report_path=str(p))
        assert agg["machine_missed_catch"]["count"] == 2
        assert agg["machine_missed_catch"]["was_correct_count"] == 1
        assert agg["tier_leak"]["count"] == 1
        assert agg["tier_leak"]["was_correct_count"] == 1
        assert len(agg["machine_missed_catch"]["entries"]) == 2
    finally:
        p.unlink(missing_ok=True)


def test_aggregate_empty_file_returns_empty_dict():
    p = _tmp_report()  # mkstemp -> existiert, aber leer
    try:
        assert dr.aggregate_by_class(report_path=str(p)) == {}
    finally:
        p.unlink(missing_ok=True)


def test_aggregate_missing_file_returns_empty_dict_no_crash():
    p = _tmp_report()
    p.unlink(missing_ok=True)  # bewusst loeschen -> Datei fehlt
    assert dr.aggregate_by_class(report_path=str(p)) == {}


def test_aggregate_skips_corrupt_lines():
    p = _tmp_report()
    try:
        # eine gueltige Zeile + Muell + eine gueltige
        with p.open("w", encoding="utf-8") as f:
            f.write(json.dumps(_valid_entry()) + "\n")
            f.write("DAS IST KEIN JSON {{{\n")
            f.write("\n")  # Leerzeile
            f.write(json.dumps(_valid_entry(deviation_class="foresight_luecke")) + "\n")
        agg = dr.aggregate_by_class(report_path=str(p))
        assert agg["machine_missed_catch"]["count"] == 1
        assert agg["foresight_luecke"]["count"] == 1
    finally:
        p.unlink(missing_ok=True)


def test_aggregate_skips_lines_with_unknown_class():
    p = _tmp_report()
    try:
        with p.open("w", encoding="utf-8") as f:
            f.write(json.dumps(_valid_entry()) + "\n")
            # manuell eingeschmuggelte unbekannte Klasse (umgeht append-Validierung)
            f.write(json.dumps({"deviation_class": "rogue", "ts": "x"}) + "\n")
        agg = dr.aggregate_by_class(report_path=str(p))
        assert "rogue" not in agg
        assert agg["machine_missed_catch"]["count"] == 1
    finally:
        p.unlink(missing_ok=True)


# ── Ring 5: cwd-Stabilitaet (default report_path haengt nicht an cwd) ─────────

def test_default_report_path_is_cwd_stable():
    """Ohne report_path-Param muss der Default cwd-unabhaengig sein (BL-336):
    aus zwei verschiedenen cwds aufgerufen -> identischer Default-Pfad."""
    code = (
        "import sys; sys.path.insert(0, r'%s');"
        "import disciplinary_report as dr;"
        "print(dr._default_report_path())"
    ) % str(SCRIPT_DIR)
    r1 = subprocess.run([sys.executable, "-c", code], cwd=str(SCRIPT_DIR),
                        capture_output=True, text=True)
    r2 = subprocess.run([sys.executable, "-c", code], cwd=str(Path.home()),
                        capture_output=True, text=True)
    assert r1.returncode == 0 and r2.returncode == 0, (r1.stderr, r2.stderr)
    assert r1.stdout.strip() == r2.stdout.strip()
    assert r1.stdout.strip()  # nicht leer


# ── Ring 6: CLI / __main__ crash-frei (a96eb1c Windows-cp1252-Lehre) ─────────

def test_cli_aggregate_runs_crashfree():
    p = _tmp_report()
    try:
        # Eintrag mit Umlauten in den Freitextfeldern -> cp1252-Falle scharf stellen
        dr.append_report(
            _valid_entry(kontext="Abweichung mit Umlauten: äöü ß — Anführungszeichen"),
            report_path=str(p),
        )
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--aggregate", "--report-path", str(p)],
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, (proc.stdout, proc.stderr)
        # read-only: das CLI darf die Datei nicht veraendern
        lines = [ln for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert len(lines) == 1
    finally:
        p.unlink(missing_ok=True)


def test_cli_no_args_runs_crashfree():
    """Bloesser Lauf ohne Args (zeigt Aggregat des Default-Pfads) darf nicht crashen."""
    proc = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True)
    assert proc.returncode == 0, (proc.stdout, proc.stderr)


if __name__ == "__main__":
    sys.exit(__import__("pytest").main([__file__, "-v"]))
