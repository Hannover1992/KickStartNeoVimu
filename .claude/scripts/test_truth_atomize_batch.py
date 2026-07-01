#!/usr/bin/env python3
"""Tests fuer truth_atomize_batch.py (BL-309 Phase B / paralleler Fan-Out + Readiness)."""
from __future__ import annotations

from pathlib import Path

import truth_atomize_batch as tb

_HEADING = "# M\n\n### W01\nEins.\n\n### W02\nZwei.\n"


def _mk_model(tmp_path, name, content):
    p = tmp_path / name
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def test_batch_jobs1_ready_count(tmp_path):
    m1 = _mk_model(tmp_path, "A_Model.md", _HEADING)
    m2 = _mk_model(tmp_path, "B_Model.md", _HEADING)
    jobs = [(m1, "BL-a", None), (m2, "BL-b", None)]
    summary = tb.aggregate(tb.batch_atomize(jobs, jobs=1))
    assert summary["models"] == 2
    assert summary["ready"] == 2
    assert summary["knot_coverage"] == 1.0


def test_batch_threaded_jobs2_same_result(tmp_path):
    m1 = _mk_model(tmp_path, "A_Model.md", _HEADING)
    m2 = _mk_model(tmp_path, "B_Model.md", _HEADING)
    jobs = [(m1, "BL-a", None), (m2, "BL-b", None)]
    seq = tb.aggregate(tb.batch_atomize(jobs, jobs=1))
    par = tb.aggregate(tb.batch_atomize(jobs, jobs=2, backend="thread"))
    assert seq["ready"] == par["ready"] == 2
    assert seq["knots_extracted"] == par["knots_extracted"]


def test_aggregate_flags_incomplete_silent_loss():
    """Census sagt 5 Knoten, Atomizer fand 0 -> complete=False -> NICHT ready."""
    results = [
        {"model": "x", "knots": 0, "census_knots": 5, "roundtrip_ok": True,
         "schema_errors": 0, "complete": False, "format_hint": "NICHT-HEADING (Phase B2 TODO)"},
    ]
    summary = tb.aggregate(results)
    assert summary["incomplete_count"] == 1
    assert summary["ready"] == 0  # roundtrip-ok aber unvollstaendig => NICHT ready


def test_aggregate_ready_excludes_schema_errors():
    results = [
        {"model": "y", "knots": 3, "census_knots": 3, "roundtrip_ok": True,
         "schema_errors": 2, "complete": True, "format_hint": "HEADING"},
    ]
    assert tb.aggregate(results)["ready"] == 0


def test_aggregate_counts_clean_ready():
    results = [
        {"model": "z", "knots": 3, "census_knots": 3, "roundtrip_ok": True,
         "schema_errors": 0, "complete": True, "format_hint": "HEADING"},
    ]
    s = tb.aggregate(results)
    assert s["ready"] == 1 and s["knot_coverage"] == 1.0


def test_namespace_for_vault_bl(tmp_path):
    p = tmp_path / "Backlog" / "BL-309-truth-migration" / "2_Model" / "Foo_Model.md"
    assert tb.namespace_for(p, tmp_path) == "BL-309-truth-migration"


def test_discover_models_finds_candidates(tmp_path):
    _mk_model(tmp_path, "Foo_Model.md", _HEADING)
    (tmp_path / "notes.md").write_text("kein model", encoding="utf-8")
    found = tb.discover_models(tmp_path, None)
    names = [p.name for p in found]
    assert "Foo_Model.md" in names


def test_is_canonical_model_excludes_noise(tmp_path):
    # Crumbs/model_* sind Arbeitsnotizen, KEINE kanonischen Models (INV-MIG-10-Fix)
    assert tb.is_canonical_model(tmp_path / "BL-x" / "Crumbs" / "model_D01_schema.md") is False
    assert tb.is_canonical_model(tmp_path / "BL-x" / "2_Model" / "Foo_Model.md") is True
    assert tb.is_canonical_model(tmp_path / ".claude" / "models" / "Bar_Model.md") is True
    assert tb.is_canonical_model(tmp_path / "BL-x" / "2_Model" / "truths" / "W01.md") is False


def test_discover_excludes_crumbs(tmp_path):
    _mk_model(tmp_path / "BL-x" / "2_Model", "Real_Model.md", _HEADING)
    _mk_model(tmp_path / "BL-x" / "Crumbs", "model_D01_schema.md", "### W1\nNotiz.\n")
    names = [p.name for p in tb.discover_models(tmp_path, None)]
    assert "Real_Model.md" in names and "model_D01_schema.md" not in names


def test_discover_cross_root_dedup_prefers_vault(tmp_path):
    # BL-390: dasselbe Nicht-BL-Model in Vault UND Repo -> gleiche ns -> nur Vault behalten.
    vault = tmp_path / "vault"
    repo = tmp_path / "repo"
    _mk_model(vault / "Models", "Foo_Model.md", _HEADING)   # kanonisch (ns=Foo)
    _mk_model(repo, "Foo_Model.md", _HEADING)               # stale Repo-Legacy (ns=Foo)
    found = tb.discover_models(vault, repo)
    assert len(found) == 1
    assert str(found[0]).startswith(str(vault))  # Vault (kanonisch) schlaegt Repo-Legacy


def test_discover_excludes_archive_snapshots(tmp_path):
    # BL-390 (DCSRE-Befund): datierte Archiv-Snapshots (.claude_archive_*) sind stale ->
    # NICHT discovern (sonst kollidieren sie mit der Live-Kopie, INV-MIG-10).
    # Praedikat auf synthetischen rel-Pfaden (frei von tmp-Namens-Rauschen):
    assert tb.is_canonical_model(Path(".claude_archive_2026-05-02/models/X_Model.md")) is False
    assert tb.is_canonical_model(Path("DCSRE-98/2_Model/DCSRE-98_Model.md")) is True
    # Integration: discover behaelt die Live-Kopie, droppt die Archiv-Kopie.
    _mk_model(tmp_path / "DCSRE-98" / "2_Model", "DCSRE-98_Model.md", _HEADING)
    _mk_model(tmp_path / ".claude_archive_2026-05-02" / "models", "DCSRE-98_Model.md", _HEADING)
    found = tb.discover_models(tmp_path, None)
    assert len(found) == 1
    assert ".claude_archive" not in str(found[0])  # die Archiv-Kopie wurde NICHT genommen
    assert "2_Model" in str(found[0])


def test_discover_excludes_deprecated_folders(tmp_path):
    # BL-393 (DCSRE live-Befund): explizit deprecate'te Ordner (....deprecated_DATE/) sind NIE Quellen.
    assert tb.is_canonical_model(Path("BL-x.deprecated_2026-05-04/2_Model/Old_Model.md")) is False
    assert tb.is_canonical_model(Path("BL-x/2_Model/Live_Model.md")) is True
    _mk_model(tmp_path / "BL-x" / "2_Model", "Live_Model.md", _HEADING)
    _mk_model(tmp_path / "BL-x.deprecated_2026-05-04" / "2_Model", "Old_Model.md", _HEADING)
    names = [Path(p).name for p in tb.discover_models(tmp_path, None)]
    assert "Live_Model.md" in names and "Old_Model.md" not in names


def test_discover_keeps_archive_named_modelfile(tmp_path):
    # Sicherheits-Guard: eine Datei "Archive_Model.md" (kein "_archive"-Dir) bleibt erhalten.
    _mk_model(tmp_path / "2_Model", "Archive_Model.md", _HEADING)
    assert "Archive_Model.md" in [p.name for p in tb.discover_models(tmp_path, None)]


def test_discover_cross_root_keeps_distinct_ns_same_basename(tmp_path):
    # BL-390-Sicherheits-Guard: gleicher Basename, ABER verschiedene ns (BL-Ordner vs flach)
    # -> KEIN faelschlicher Drop (waere neuer Silent-Loss).
    vault = tmp_path / "vault"
    repo = tmp_path / "repo"
    _mk_model(vault / "Backlog" / "BL-100-x" / "2_Model", "Auth_Model.md", _HEADING)  # ns=BL-100-x
    _mk_model(repo, "Auth_Model.md", _HEADING)                                         # ns=Auth
    found = tb.discover_models(vault, repo)
    assert len(found) == 2  # verschiedene ns -> beide behalten


# ── BL-391 (A)+(B): Range-Heading wird von (A) atomisiert -> (B)-Span-Signal cleart (Interlock) ──

# Kein Titel-Preamble (startet direkt mit dem Range-Heading) -> bleibt auf dem HEADING-Pfad, der die
# BL-391(A) Range-Member-Atomisierung ausfuehrt (ein Titel-Preamble wuerde via BL-396 content-faithful
# Router auf den SEGMENT-Pfad gehen — byte-identisch, aber andere Granularitaet; das ist NICHT was diese
# Tests pruefen). Titel-Preamble->SEGMENT ist separat abgedeckt (test_titled_preamble_routes_to_segment).
_RANGE = "### W16-W19: WIDERLEGT\n- W16: a\n- W17: b\n- W18: c\n- W19: d\n"
# Range OHNE parsebare Member-Zeilen -> (A) emittiert leere Kind-Slices -> Schema-ERROR (Schutz via Schema)
_RANGE_UNSLICEABLE = "### W16-W19: nur Prosa\nFliesstext ohne irgendeine W-Member-Zeile.\n"


def test_batch_range_resolved_by_member_atomization(tmp_path):
    # (A) atomisiert W17/W18/W19 als Kinder -> (B)-Span-Signal cleart (extracted >= implied), kein merged Blob.
    m = _mk_model(tmp_path, "R_Model.md", _RANGE)
    summary = tb.aggregate(tb.batch_atomize([(m, "BL-r", None)], jobs=1))
    assert summary["range_collapse_count"] == 0      # vor (A) war das 1
    assert summary["range_collapse_ids"] == 0
    assert summary["knots_extracted"] == 4           # Gruppe W16 + Kinder W17/W18/W19
    assert summary["ready"] == 1                     # atomisiert + sauber -> ready


def test_batch_atomized_range_allows_write(tmp_path):
    # (A): well-formed Range -> kein Kollaps -> Write erlaubt; W17 wird eigene atomare Truth-Datei.
    m = _mk_model(tmp_path, "R_Model.md", _RANGE)
    out = tmp_path / "truths"
    res = tb.batch_atomize([(m, "BL-r", out)], jobs=1, write=True)[0]
    assert res["range_collapsed"] is False
    assert res["write"] is not None and out.exists()
    assert (out / "W17.md").exists()                 # nicht in W16 vergraben


def test_batch_unsliceable_range_blocks_write_via_schema(tmp_path):
    # Schutz erhalten: Range ohne parsebare Member -> leere Kind-Slices -> Schema-ERROR -> KEIN Write.
    m = _mk_model(tmp_path, "E_Model.md", _RANGE_UNSLICEABLE)
    out = tmp_path / "truths"
    res = tb.batch_atomize([(m, "BL-e", out)], jobs=1, write=True)[0]
    assert res["schema_errors"] > 0                  # Pflichtfeld 'text' leer in den Kindern
    assert res["write"] is None and not out.exists()


def test_batch_no_collapse_for_plain_headings(tmp_path):
    m = _mk_model(tmp_path, "C_Model.md", _HEADING)
    summary = tb.aggregate(tb.batch_atomize([(m, "BL-c", None)], jobs=1))
    assert summary["range_collapse_count"] == 0


def test_aggregate_tolerates_missing_range_keys():
    # Hand-gebaute Result-Dicts (aeltere Aufrufer) ohne range-Felder -> kein Crash, count 0.
    results = [{"model": "z", "knots": 3, "census_knots": 3, "roundtrip_ok": True,
                "schema_errors": 0, "complete": True, "format_hint": "HEADING"}]
    s = tb.aggregate(results)
    assert s["range_collapse_count"] == 0 and s["range_collapse_ids"] == 0
