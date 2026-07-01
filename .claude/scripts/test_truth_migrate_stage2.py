#!/usr/bin/env python3
"""RED-Tests fuer BL-398 batch_1 (CAPSTONE) — Stage 2 (truth_normalize) Wiring im Orchestrator.

Diese Tests sind ABSICHTLICH RED gegen den aktuellen truth_migrate_orchestrator: dort haengt Stage 2
(truth_normalize.normalize_model) NICHT in der process_bl_unit-Kette (grep normalize @orchestrator=0).
GREEN haengt normalize als Stage 2 VOR atomize (Stage 3) ein — read-only-first / DRY-RUN-default.

Erwartete Stage-2-Integrations-API (GREEN baut):
  process_bl_unit(model_path, *, normalize=False, legacy_dir=None) -> dict
    - normalize=False  -> bestehendes Verhalten UNVERAENDERT (Regression-Schutz).
    - normalize=True   -> ruft truth_normalize.normalize_model(...) VOR atomize_model_file(...);
                          Result enthaelt Stage-2-Observables: "normalized", "format_hint",
                          "stage2_legacy" (Pfad des .pre_normalize.md-Backups oder None).
  run(..., normalize=False) -> Report; mit normalize=True faedelt Stage 2 in die Kette,
    bleibt aber DRY-RUN/gefenced (write_fenced gesetzt, kein truths/-Write).

ALLES tmp/DRY-RUN — KEINE LIVE-Vault-Mutation. NUR Tests (RED!=GREEN, kein Impl).
"""
from __future__ import annotations

import pathlib

import truth_atomizer as ta
import truth_migrate_orchestrator as orch
import truth_normalize as tn


def _mk(p: pathlib.Path, content: str) -> pathlib.Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


# Drift-Korpus-Bausteine, die content-faithful zu HEADING normalisieren (verifiziert):
_BULLET = "- W1: Eine Wahrheit.\n- W2: Zwei.\n- W3: Drei.\n"
_BOLD = "**W1** Eine Wahrheit.\n**W2** Zwei.\n"
_BARE = "W1: Eine.\nW2: Zwei.\n"
_TABLE = "| ID | Aussage |\n|----|----|\n| W1 | Eine. |\n| W2 | Zwei. |\n"
_RANGE = "### W1-W3\n- W1: a\n- W2: b\n- W3: c\n"
_CANON = "### W01\nEine Wahrheit.\n\n### W02\nZwei.\n"
_PROSA = "# Titel\n\nNur Fliesstext ohne W-Knoten.\n"   # nicht content-faithful normalisierbar


# ─────────────────────────────────────────────────────────────────────────────
# AK-STAGE2-WIRING (DoD-W.1/W.2): normalize laeuft als Stage 2 VOR atomize
# ─────────────────────────────────────────────────────────────────────────────

def test_stage2_drifted_model_reaches_heading_path_dryrun(tmp_path):
    """DoD-W.2: ein driftetes Bullet-Model -> Stage 2 normalisiert -> Stage 3 atomize liefert
    format_hint=='HEADING' (statt SEGMENT-B2 Verbatim-Fallback). RED: ohne Stage-2-Wiring bleibt
    es auf SEGMENT-B2."""
    bl = tmp_path / "Backlog" / "BL-1"
    mp = _mk(bl / "2_Model" / "Bullet_Model.md", _BULLET)
    r = orch.process_bl_unit(str(mp), normalize=True, legacy_dir=str(tmp_path / "_legacy"))
    assert r["format_hint"] == "HEADING"
    assert r["normalized"] is True


def test_stage2_all_drift_forms_reach_heading(tmp_path):
    """DoD-W.2: Bullet/Bold/bare/Table/Range alle -> HEADING nach Stage 2. RED ohne Wiring."""
    forms = {"Bullet": _BULLET, "Bold": _BOLD, "Bare": _BARE, "Table": _TABLE, "Range": _RANGE}
    for name, content in forms.items():
        mp = _mk(tmp_path / "Backlog" / f"BL-{name}" / "2_Model" / f"{name}_Model.md", content)
        r = orch.process_bl_unit(str(mp), normalize=True, legacy_dir=str(tmp_path / "_legacy"))
        assert r["format_hint"] == "HEADING", f"{name} blieb auf {r['format_hint']}"


def test_stage2_runs_before_atomize_order_spy(tmp_path, monkeypatch):
    """DoD-1.2: Spy-Order-Beweis — normalize_model wird AUFGERUFEN BEVOR atomize_model_file das Model
    anfasst. RED: ohne Stage-2-Wiring wird normalize_model NIE gerufen (calls bleibt leer)."""
    bl = tmp_path / "Backlog" / "BL-1"
    mp = _mk(bl / "2_Model" / "Bullet_Model.md", _BULLET)

    calls: list[str] = []
    real_norm = tn.normalize_model
    real_atom = ta.atomize_model_file

    def spy_norm(model_path, **kw):
        calls.append("normalize")
        return real_norm(model_path, **kw)

    def spy_atom(model_path, namespace):
        calls.append("atomize")
        return real_atom(model_path, namespace)

    monkeypatch.setattr(orch.tn, "normalize_model", spy_norm, raising=False)
    monkeypatch.setattr(orch.ta, "atomize_model_file", spy_atom)

    orch.process_bl_unit(str(mp), normalize=True, legacy_dir=str(tmp_path / "_legacy"))
    assert "normalize" in calls, "Stage 2 (normalize_model) wurde NICHT aufgerufen"
    assert "atomize" in calls
    assert calls.index("normalize") < calls.index("atomize"), "normalize muss VOR atomize laufen"


def test_orch_module_exposes_truth_normalize(tmp_path):
    """DoD-W.1: der Orchestrator referenziert truth_normalize (grep-normalize-Match != 0).
    RED: das Modul importiert truth_normalize aktuell nicht."""
    assert hasattr(orch, "tn"), "truth_migrate_orchestrator referenziert truth_normalize (Stage 2) nicht"


# ─────────────────────────────────────────────────────────────────────────────
# AK-STAGE2-WIRING (DoD-W.3): messbarer Slimming-Gewinn
# ─────────────────────────────────────────────────────────────────────────────

def test_slimming_gain_measurable_over_corpus(tmp_path):
    """DoD-W.3: ueber den tmp-Korpus ist heading_after > heading_before bei content_loss==0
    (via truth_normalize.slimming_gain — die Stage-2-Wirkung ist messbar)."""
    texts = [_BULLET, _BOLD, _CANON, _PROSA]
    g = tn.slimming_gain(texts)
    assert g["heading_after"] > g["heading_before"]
    assert g["content_loss"] == 0


def test_run_dryrun_normalize_reports_slimming(tmp_path):
    """DoD-W.3 (integriert): run(normalize=True) DRY-RUN meldet einen Stage-2-Slimming-Effekt
    (mehr HEADING-Models als ohne Stage 2). RED: run kennt normalize nicht / der Report-Key fehlt."""
    for name, content in {"Bullet": _BULLET, "Bold": _BOLD}.items():
        _mk(tmp_path / "Backlog" / f"BL-{name}" / "2_Model" / f"{name}_Model.md", content)
    rep = orch.run(tmp_path / "Backlog", None, jobs=1, normalize=True)
    # Stage-2-Observable: der Report fuehrt einen Slimming-/Heading-Gewinn (>0).
    assert rep.get("stage2_heading_gain", 0) > 0


# ─────────────────────────────────────────────────────────────────────────────
# AK-1 (1-Befehl, volle 5-Stage-Kette, Stage 2 drin) — DRY-RUN
# ─────────────────────────────────────────────────────────────────────────────

def test_single_call_full_pipeline_stage2_in_chain(tmp_path):
    """AK-1 DoD-1.1/1.2: EIN run(normalize=True)-Aufruf faehrt analyze->normalize->atomize (DRY-RUN);
    Stage 2 ist in der Kette (normalisierte Models tauchen als HEADING in der Readiness auf)."""
    bl = tmp_path / "Backlog" / "BL-1"
    _mk(bl / "2_Model" / "Bullet_Model.md", _BULLET)
    rep = orch.run(tmp_path / "Backlog", None, jobs=1, normalize=True)
    assert rep["models"] == 1
    assert rep["ready"] == 1
    # Stage-2-Wirkung: das Bullet-Model ist ready UND wurde normalisiert (nicht SEGMENT-quarantaeniert).
    assert rep.get("stage2_normalized", 0) >= 1


# ─────────────────────────────────────────────────────────────────────────────
# AK-2 (read-only-first hart): kein Write, DRY-RUN-default, nichts mutiert ohne Gate
# ─────────────────────────────────────────────────────────────────────────────

def test_stage2_dryrun_does_not_mutate_source_model(tmp_path):
    """AK-2 DoD-2.1/2.3: process_bl_unit(normalize=True) ohne confirm mutiert das QUELL-Model NICHT
    (byte-identisch vorher/nachher). Stage 2 normalisiert auf einer KOPIE im legacy_dir-Scope, nie
    in-place am Quell-Model. RED-Schutz gegen eine in-place-normalize-Implementierung."""
    bl = tmp_path / "Backlog" / "BL-1"
    mp = _mk(bl / "2_Model" / "Bullet_Model.md", _BULLET)
    before = mp.read_bytes()
    orch.process_bl_unit(str(mp), normalize=True, legacy_dir=str(tmp_path / "_legacy"))
    assert mp.read_bytes() == before, "Stage 2 darf das Quell-Model im DRY-RUN NICHT in-place aendern"


def test_run_stage2_still_write_fenced(tmp_path):
    """AK-2: auch mit Stage 2 + write=True bleibt der Orchestrator hart gefenced (kein truths/-Write)."""
    bl = tmp_path / "Backlog" / "BL-1"
    _mk(bl / "2_Model" / "Bullet_Model.md", _BULLET)
    rep = orch.run(tmp_path / "Backlog", None, jobs=1, write=True, normalize=True)
    assert rep["write_fenced"] is not None
    assert not (bl / "2_Model" / "truths").exists()


# ─────────────────────────────────────────────────────────────────────────────
# AK-3 (reversibel): Stage-2-Backup .pre_normalize.md + disjunkte Suffixe
# ─────────────────────────────────────────────────────────────────────────────

def test_stage2_backup_suffix_disjoint_from_cutover(tmp_path):
    """AK-3 DoD-3.3: Stage-2-Suffix (.pre_normalize.md) ist DISJUNKT zum Stage-5-Suffix (.pre_truth.md).
    Beide Rollbacks kollidieren nicht."""
    import truth_cutover as tcut
    assert tn._LEGACY_SUFFIX == ".pre_normalize.md"
    assert tcut._LEGACY_SUFFIX == ".pre_truth.md"
    assert tn._LEGACY_SUFFIX != tcut._LEGACY_SUFFIX


def test_stage2_byte_identical_rollback(tmp_path):
    """AK-3 DoD-3.1: ein Stage-2-normalisiertes Model laesst sich byte-identisch aus .pre_normalize.md
    zuruecksetzen. (Direkt gegen truth_normalize-API — Reversibilitaets-Mechanik, die Stage 2 nutzt.)"""
    bl = tmp_path / "Backlog" / "BL-1"
    mp = _mk(bl / "2_Model" / "Bullet_Model.md", _BULLET)
    original = mp.read_bytes()
    legacy_dir = tmp_path / "_legacy"
    res = tn.normalize_model(mp, legacy_dir=legacy_dir)
    assert res["normalized"] is True
    assert mp.read_bytes() != original                 # Model wurde normalisiert
    tn.rollback(mp, legacy_dir)
    assert mp.read_bytes() == original                 # byte-identisch zurueck


# ─────────────────────────────────────────────────────────────────────────────
# AK-STAGE2-WIRING (DoD-W.4): nicht-content-faithful Model bleibt UNANGETASTET
# ─────────────────────────────────────────────────────────────────────────────

def test_stage2_non_faithful_model_falls_back_to_segment(tmp_path):
    """DoD-W.4: ein No-W-Def-Prosa-Model ist NICHT content-faithful normalisierbar -> Stage 2 fasst
    es nicht an -> Stage 3 faellt auf den SEGMENT-Pfad (kein stiller Verlust, Quarantaene intakt)."""
    bl = tmp_path / "Backlog" / "BL-90"
    mp = _mk(bl / "2_Model" / "Prosa_Model.md", _PROSA)
    before = mp.read_bytes()
    r = orch.process_bl_unit(str(mp), normalize=True, legacy_dir=str(tmp_path / "_legacy"))
    assert r["normalized"] is False
    assert r["format_hint"] != "HEADING"     # SEGMENT/LEER-Fallback
    assert mp.read_bytes() == before          # nicht angetastet


# ─────────────────────────────────────────────────────────────────────────────
# AK-5 Mechanik (DoD-5.1/5.2): Models = Views / Truths = Substanz (DRY-RUN)
# ─────────────────────────────────────────────────────────────────────────────

def test_ak5_view_equals_generated_from_truths_after_stage2(tmp_path):
    """DoD-5.2: nach Stage 2+3 ist die Model-View == aus-Wahrheiten-generiert (Models sind Views).
    RED: process_bl_unit liefert ohne Stage-2-Wiring kein normalisiertes HEADING-Substrat fuer das
    Bullet-Model, daher kein verlustfreier HEADING-View-Nachweis."""
    bl = tmp_path / "Backlog" / "BL-1"
    mp = _mk(bl / "2_Model" / "Bullet_Model.md", _BULLET)
    r = orch.process_bl_unit(str(mp), normalize=True, legacy_dir=str(tmp_path / "_legacy"))
    assert r["format_hint"] == "HEADING"
    # Substanz-Nachweis: die atomisierten Truths rekonstruieren die View deterministisch.
    truths = r["_truths"]
    view = ta.build_model_view(truths)
    assert view == ta.build_model_view(ta.atomize(view, r["ns"]))   # idempotent View<->Truths


def test_ak5_disk_rebuild_lossless_mechanic(tmp_path):
    """DoD-5.1: disk-rebuild Mechanik — die aus den normalisierten Wahrheiten generierte View
    rekonstruiert den (normalisierten) Quell-Body verlustfrei (is_canonical_format True)."""
    norm = tn.normalize_text(_BULLET)
    assert norm is not None
    ok, reasons = tn.is_canonical_format(norm)
    assert ok, f"View nicht verlustfrei: {reasons}"
