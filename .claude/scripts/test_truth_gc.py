#!/usr/bin/env python3
"""Tests fuer truth_gc.py (BL-399 batch_1 — AK-GC-SCAN + AK-ANTI-REBLOAT-METRIK).

RED-Worker (TDD test-first, RED!=GREEN). Definiert die truth_gc-API DURCH Tests.
Scope batch_1: NUR scan() (5 Dimensionen, read-only) + metric() (Anti-Re-Bloat-Snapshot).
NICHT-Scope (andere Batches): health-integration, safety-gate, plan_heal-Verdrahtung.

Korpus-Modell (tmp): ein "root" = BL-Ordner mit `truths/*.md` (type:truth-Atome,
yaml-Frontmatter) + optional Model-Dateien (2_Model/) fuer accumulation/Metrik.
scan(roots) liest read-only und liefert einen 5-Dimensions-Report-dict. Die 4 fertigen
Sonden werden reused (truth_dedup / truth_lifecycle+referenced_by / truth_backref_index /
truth_normalize); accumulation nutzt eine neue konservative Schwelle + truth_census.count_wknots.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

import truth_gc as gc  # noqa: F401  — existiert (noch) NICHT -> RED


# ──────────────────────────────────────────────────────────────────────────────
# Korpus-Helfer: schreibt type:truth-Atome (yaml-Frontmatter) in einen tmp-Root.
# ──────────────────────────────────────────────────────────────────────────────

def _fm(**kv) -> str:
    """Baut yaml-Frontmatter-Block aus simplen scalars/lists."""
    lines = ["---"]
    for k, v in kv.items():
        if isinstance(v, list):
            if not v:
                lines.append(f"{k}: []")
            else:
                lines.append(f"{k}:")
                for item in v:
                    if isinstance(item, dict):
                        first = True
                        for ik, iv in item.items():
                            prefix = "  - " if first else "    "
                            lines.append(f"{prefix}{ik}: {iv}")
                            first = False
                    else:
                        lines.append(f"  - {item}")
        else:
            lines.append(f"{k}: {v}")
    lines.append("---")
    return "\n".join(lines)


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_truth(root: Path, local_id: str, *, text: str = "## W: eine Wahrheit\n\nKoerper.",
                 status: str = "BESTAETIGT", truth_grade: str = "vault_hypothesis",
                 content_hash: str | None = None, referenced_by=None, edges=None,
                 body: str | None = None) -> Path:
    """Schreibt truths/{local_id}.md als type:truth-Atom. Defaults = sauberes Atom."""
    truths_dir = root / "truths"
    truths_dir.mkdir(parents=True, exist_ok=True)
    fm_kwargs = {
        "id": f"BL-TMP.{local_id}",
        "local_id": local_id,
        "type": "truth",
        "text": text,
        "typ": "FESTSTELLUNG",
        "herkunft": "INTERN",
        "status": status,
        "truth_grade": truth_grade,
    }
    if content_hash is not None:
        fm_kwargs["content_hash"] = content_hash
    if referenced_by is not None:
        fm_kwargs["referenced_by"] = referenced_by
    if edges is not None:
        fm_kwargs["edges"] = edges
    p = truths_dir / f"{local_id}.md"
    doc = _fm(**fm_kwargs) + "\n\n" + (body if body is not None else f"# {local_id}\n\n{text}\n")
    p.write_text(doc, encoding="utf-8")
    return p


def _clean_root(tmp_path: Path) -> Path:
    """Ein sauberer Korpus: 2 distinkte, kanonische, referenzierte, frische Atome."""
    root = tmp_path / "clean_bl"
    _write_truth(root, "w001", text="Erste Wahrheit",
                 referenced_by=[{"by": "spec", "kind": "spec_link"}],
                 body="## W-w001: Erste Wahrheit\n\nKlare kanonische View.\n")
    _write_truth(root, "w002", text="Zweite Wahrheit",
                 referenced_by=[{"by": "kscore", "kind": "kscore_ref"}],
                 body="## W-w002: Zweite Wahrheit\n\nKlare kanonische View.\n")
    return root


def _corpus_bytes(root: Path) -> dict[str, bytes]:
    """Snapshot aller Datei-Bytes unter root (fuer read-only-Roundtrip)."""
    return {str(p): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


# ──────────────────────────────────────────────────────────────────────────────
# AK-GC-SCAN — T-SCAN-1 .. T-SCAN-7
# ──────────────────────────────────────────────────────────────────────────────

EXPECTED_KEYS = {"duplicates", "stale", "orphaned", "format_regression", "accumulation"}


def test_scan_report_has_exactly_five_dimension_keys(tmp_path):
    """DoD-1: scan(roots) gibt dict mit genau den 5 Dimensions-Keys."""
    root = _clean_root(tmp_path)
    report = gc.scan([root])
    assert isinstance(report, dict)
    assert EXPECTED_KEYS.issubset(report.keys())
    for key in EXPECTED_KEYS:
        assert isinstance(report[key], list)


def test_scan_clean_corpus_all_dimensions_empty(tmp_path):
    """Sauberer Korpus -> alle 5 Dimensionen leer."""
    root = _clean_root(tmp_path)
    report = gc.scan([root])
    for key in EXPECTED_KEYS:
        assert report[key] == [], f"{key} sollte leer sein bei sauberem Korpus, war {report[key]!r}"


def test_scan_t1_duplicates_same_content_hash(tmp_path):
    """T-SCAN-1: 2 Atome identischem content_hash -> beide in duplicates (Reuse dedup_groups)."""
    root = tmp_path / "dup_bl"
    h = _content_hash("identischer-koerper")
    _write_truth(root, "w001", text="A", content_hash=h,
                 referenced_by=[{"by": "spec", "kind": "spec_link"}])
    _write_truth(root, "w002", text="A-kopie", content_hash=h,
                 referenced_by=[{"by": "spec", "kind": "spec_link"}])
    report = gc.scan([root])
    dup_ids = {d.get("local_id") or d.get("id") for d in report["duplicates"]}
    assert "w001" in dup_ids and "w002" in dup_ids


def test_scan_t1_no_duplicates_distinct_hash(tmp_path):
    """T-SCAN-1 (negativ): distinkte content_hashes -> duplicates leer."""
    root = tmp_path / "nodup_bl"
    _write_truth(root, "w001", text="A", content_hash=_content_hash("a"),
                 referenced_by=[{"by": "spec", "kind": "spec_link"}])
    _write_truth(root, "w002", text="B", content_hash=_content_hash("b"),
                 referenced_by=[{"by": "spec", "kind": "spec_link"}])
    report = gc.scan([root])
    assert report["duplicates"] == []


def test_scan_t2_stale_contradicted_but_referenced(tmp_path):
    """T-SCAN-2: lifecycle contradicted/retracted UND referenced_by nicht leer -> stale."""
    root = tmp_path / "stale_bl"
    # status WIDERLEGT -> lifecycle contradicted; referenced_by nicht leer
    _write_truth(root, "w001", text="alt", status="WIDERLEGT",
                 referenced_by=[{"by": "spec", "kind": "spec_link"}])
    report = gc.scan([root])
    stale_ids = {d.get("local_id") or d.get("id") for d in report["stale"]}
    assert "w001" in stale_ids


def test_scan_t2_stale_contradicted_but_unreferenced_not_stale(tmp_path):
    """T-SCAN-2 (negativ): contradicted ABER referenced_by leer -> NICHT stale."""
    root = tmp_path / "stale_neg_bl"
    _write_truth(root, "w001", text="alt", status="WIDERLEGT", referenced_by=[],
                 edges=[{"rel": "depends_on", "ziel": "BL-TMP.w999"}])
    report = gc.scan([root])
    stale_ids = {d.get("local_id") or d.get("id") for d in report["stale"]}
    assert "w001" not in stale_ids


def test_scan_t2_active_referenced_not_stale(tmp_path):
    """T-SCAN-2 (negativ): aktiver (reviewed) referenzierter Truth -> NICHT stale."""
    root = _clean_root(tmp_path)
    report = gc.scan([root])
    assert report["stale"] == []


def test_scan_t3_orphaned_no_refs_no_edges(tmp_path):
    """T-SCAN-3: Atom ohne referenced_by UND ohne edges -> orphaned."""
    root = tmp_path / "orphan_bl"
    _write_truth(root, "w001", text="verwaist", referenced_by=[], edges=[],
                 body="## W-w001: verwaist\n\nNiemand zeigt drauf.\n")
    report = gc.scan([root])
    orphan_ids = {d.get("local_id") or d.get("id") for d in report["orphaned"]}
    assert "w001" in orphan_ids


def test_scan_t3_not_orphaned_with_referenced_by(tmp_path):
    """T-SCAN-3 (negativ): referenced_by ODER edges vorhanden -> NICHT orphaned."""
    root = tmp_path / "orphan_neg_bl"
    _write_truth(root, "w001", text="hat-ref", referenced_by=[{"by": "spec", "kind": "spec_link"}],
                 edges=[])
    _write_truth(root, "w002", text="hat-edge", referenced_by=[],
                 edges=[{"rel": "depends_on", "ziel": "BL-TMP.w001"}])
    report = gc.scan([root])
    orphan_ids = {d.get("local_id") or d.get("id") for d in report["orphaned"]}
    assert "w001" not in orphan_ids
    assert "w002" not in orphan_ids


def test_scan_t4_format_regression_non_canonical(tmp_path):
    """T-SCAN-4: nicht-kanonischer Text (is_canonical_format False) -> format_regression."""
    root = tmp_path / "fmt_bl"
    # KEINE Headings im Body -> no_headings -> is_canonical_format == False (BL-397).
    _write_truth(root, "w001", text="flacher text ohne struktur",
                 referenced_by=[{"by": "spec", "kind": "spec_link"}],
                 body="flacher text ohne ueberschriften und ohne atom-struktur\n")
    report = gc.scan([root])
    fmt_ids = {d.get("local_id") or d.get("id") for d in report["format_regression"]}
    assert "w001" in fmt_ids


def test_scan_t4_canonical_text_not_regression(tmp_path):
    """T-SCAN-4 (negativ): kanonischer Korpus -> format_regression leer."""
    root = _clean_root(tmp_path)
    report = gc.scan([root])
    assert report["format_regression"] == []


def test_scan_t5_accumulation_over_threshold(tmp_path):
    """T-SCAN-5: Model mit ref_count/atom_count ueber konservativer Schwelle -> accumulation."""
    root = tmp_path / "accum_bl"
    # Viele referenzierte Atome -> aggregierter ref_count des Models ueber Schwelle.
    for i in range(60):
        _write_truth(root, f"w{i:03d}", text=f"w{i}",
                     referenced_by=[{"by": f"spec{i}", "kind": "spec_link"},
                                    {"by": f"ks{i}", "kind": "kscore_ref"}])
    report = gc.scan([root], threshold=10)
    assert len(report["accumulation"]) >= 1


def test_scan_t5_accumulation_under_threshold_empty(tmp_path):
    """T-SCAN-5 (negativ): unter Schwelle -> accumulation leer."""
    root = _clean_root(tmp_path)
    report = gc.scan([root], threshold=1000)
    assert report["accumulation"] == []


def test_scan_t6_read_only_corpus_bytes_unchanged(tmp_path):
    """T-SCAN-6 (read-only-INV): vor/nach scan ist der Korpus byte-identisch."""
    root = tmp_path / "ro_bl"
    h = _content_hash("dup")
    _write_truth(root, "w001", text="dup", content_hash=h, referenced_by=[])
    _write_truth(root, "w002", text="dup2", content_hash=h, referenced_by=[], edges=[])
    _write_truth(root, "w003", text="schlecht", status="WIDERLEGT",
                 referenced_by=[{"by": "spec", "kind": "spec_link"}],
                 body="kein heading hier\n")
    before = _corpus_bytes(root)
    gc.scan([root])
    after = _corpus_bytes(root)
    assert before == after, "scan darf KEINE Datei aendern/loeschen/anlegen (read-only-INV)"


def test_scan_t7_report_json_serializable(tmp_path):
    """T-SCAN-7: Report ist JSON-dumpbar (dict, alle 5 Keys, serialisierbar)."""
    root = tmp_path / "ser_bl"
    _write_truth(root, "w001", text="x", referenced_by=[], edges=[])
    report = gc.scan([root])
    blob = json.dumps(report)
    reloaded = json.loads(blob)
    assert EXPECTED_KEYS.issubset(reloaded.keys())


def test_scan_multi_root_aggregates(tmp_path):
    """scan akzeptiert mehrere roots und aggregiert die Befunde."""
    r1 = tmp_path / "bl_a"
    r2 = tmp_path / "bl_b"
    _write_truth(r1, "w001", text="orphan-a", referenced_by=[], edges=[])
    _write_truth(r2, "w001", text="orphan-b", referenced_by=[], edges=[])
    report = gc.scan([r1, r2])
    assert len(report["orphaned"]) >= 2


# ──────────────────────────────────────────────────────────────────────────────
# AK-ANTI-REBLOAT-METRIK — T-MET-1 .. T-MET-4
# ──────────────────────────────────────────────────────────────────────────────

def test_metric_t1_report_has_ref_count_and_atom_count(tmp_path):
    """T-MET-1: metric(roots) liefert pro Model ref_count (aggregiert) + atom_count (count_wknots)."""
    root = tmp_path / "met_bl"
    _write_truth(root, "w001", text="a", referenced_by=[{"by": "spec", "kind": "spec_link"}])
    _write_truth(root, "w002", text="b", referenced_by=[{"by": "ks", "kind": "kscore_ref"},
                                                        {"by": "spec", "kind": "spec_link"}])
    snap = gc.metric([root])
    assert isinstance(snap, dict)
    assert "ref_count" in snap
    assert "atom_count" in snap
    assert isinstance(snap["ref_count"], int)
    assert isinstance(snap["atom_count"], int)
    # 3 referenzen gesamt, 2 atome
    assert snap["ref_count"] == 3
    assert snap["atom_count"] == 2


def test_metric_t2_over_threshold_in_accumulation_with_reason(tmp_path):
    """T-MET-2: ref_count > Schwelle -> Eintrag in scan-accumulation mit Begruendung 'ref_count=N'."""
    root = tmp_path / "met2_bl"
    for i in range(40):
        _write_truth(root, f"w{i:03d}", text=f"w{i}",
                     referenced_by=[{"by": f"s{i}", "kind": "spec_link"}])
    report = gc.scan([root], threshold=5)
    assert report["accumulation"], "ueber Schwelle muss accumulation-Eintrag erzeugen"
    entry = report["accumulation"][0]
    reason = str(entry.get("reason", ""))
    assert "ref_count" in reason
    assert "Schwelle" in reason or "threshold" in reason.lower()


def test_metric_t3_threshold_configurable_default_conservative(tmp_path):
    """T-MET-3: Schwelle configbar; default konservativ -> kleines Model unter Default -> leer."""
    root = _clean_root(tmp_path)
    # default-Schwelle (kein threshold-Arg) darf kleines sauberes Model NICHT als bloat melden.
    report_default = gc.scan([root])
    assert report_default["accumulation"] == []
    # explizit kleine Schwelle -> selber Korpus loest aus (Beweis: configbar wirkt).
    report_low = gc.scan([root], threshold=1)
    assert len(report_low["accumulation"]) >= 1


def test_metric_t4_markdown_render_shows_metric_columns(tmp_path):
    """T-MET-4: Markdown-Render zeigt View-Referenz-Zahl + Atom-Zahl (Beobachtbarkeit)."""
    root = tmp_path / "render_bl"
    _write_truth(root, "w001", text="a", referenced_by=[{"by": "spec", "kind": "spec_link"}])
    report = gc.scan([root])
    md = gc.render_markdown(report)
    assert isinstance(md, str)
    low = md.lower()
    assert "ref_count" in low or "referenz" in low
    assert "atom_count" in low or "atom" in low


def test_metric_read_only(tmp_path):
    """read-only-INV: metric aendert keine Dateien."""
    root = tmp_path / "met_ro_bl"
    _write_truth(root, "w001", text="a", referenced_by=[{"by": "spec", "kind": "spec_link"}])
    before = _corpus_bytes(root)
    gc.metric([root])
    after = _corpus_bytes(root)
    assert before == after


# ──────────────────────────────────────────────────────────────────────────────
# DoD-2 Reuse-Nachweis: scan ruft die fertigen Sonden (kein Sonden-Neubau).
# ──────────────────────────────────────────────────────────────────────────────

def test_scan_reuses_dedup_groups(tmp_path, monkeypatch):
    """DoD-2: duplicates-Dimension ruft truth_dedup.dedup_groups (Import-Nachweis)."""
    import truth_dedup
    calls = {"n": 0}
    orig = truth_dedup.dedup_groups

    def spy(truths):
        calls["n"] += 1
        return orig(truths)

    monkeypatch.setattr(truth_dedup, "dedup_groups", spy, raising=True)
    root = tmp_path / "reuse_dedup_bl"
    _write_truth(root, "w001", text="a", content_hash=_content_hash("x"))
    _write_truth(root, "w002", text="b", content_hash=_content_hash("x"))
    gc.scan([root])
    assert calls["n"] >= 1, "scan muss truth_dedup.dedup_groups reusen, nicht neu bauen"


def test_scan_reuses_map_lifecycle(tmp_path, monkeypatch):
    """DoD-2: stale-Dimension ruft truth_lifecycle.map_lifecycle (Import-Nachweis)."""
    import truth_lifecycle
    calls = {"n": 0}
    orig = truth_lifecycle.map_lifecycle

    def spy(*a, **k):
        calls["n"] += 1
        return orig(*a, **k)

    monkeypatch.setattr(truth_lifecycle, "map_lifecycle", spy, raising=True)
    root = tmp_path / "reuse_life_bl"
    _write_truth(root, "w001", text="a", status="WIDERLEGT",
                 referenced_by=[{"by": "spec", "kind": "spec_link"}])
    gc.scan([root])
    assert calls["n"] >= 1, "scan muss truth_lifecycle.map_lifecycle reusen"


def test_scan_reuses_is_canonical_format(tmp_path, monkeypatch):
    """DoD-2: format_regression-Dimension ruft truth_normalize.is_canonical_format."""
    import truth_normalize
    calls = {"n": 0}
    orig = truth_normalize.is_canonical_format

    def spy(text):
        calls["n"] += 1
        return orig(text)

    monkeypatch.setattr(truth_normalize, "is_canonical_format", spy, raising=True)
    root = tmp_path / "reuse_fmt_bl"
    _write_truth(root, "w001", text="a", referenced_by=[{"by": "spec", "kind": "spec_link"}],
                 body="kein heading\n")
    gc.scan([root])
    assert calls["n"] >= 1, "scan muss truth_normalize.is_canonical_format reusen"


def test_scan_reuses_count_wknots(tmp_path, monkeypatch):
    """DoD-3: accumulation/Metrik nutzt truth_census.count_wknots."""
    import truth_census
    calls = {"n": 0}
    orig = truth_census.count_wknots

    def spy(text):
        calls["n"] += 1
        return orig(text)

    monkeypatch.setattr(truth_census, "count_wknots", spy, raising=True)
    root = tmp_path / "reuse_census_bl"
    _write_truth(root, "w001", text="a", referenced_by=[{"by": "spec", "kind": "spec_link"}])
    gc.scan([root])
    assert calls["n"] >= 1, "accumulation/Metrik muss truth_census.count_wknots nutzen"
