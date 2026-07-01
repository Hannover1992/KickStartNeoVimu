#!/usr/bin/env python3
"""Tests fuer truth_cutover.py (BL-385/386 Cutover-Write-Schicht; tmp-Fixtures, kein Real-Vault)."""
from __future__ import annotations

import truth_atomizer as ta
import truth_cutover as tc

_MODEL = "# M\n\n### W01\nEins.\n\n### W02\nZwei.\n"


def test_swap_then_rollback_byte_identical(tmp_path):
    # INV-MIG-11: Swap -> Rollback stellt das Original BYTE-IDENTISCH wieder her.
    model = tmp_path / "X_Model.md"
    model.write_text(_MODEL, encoding="utf-8")
    original_bytes = model.read_bytes()
    truths = ta.atomize(_MODEL, "BL-x")
    legacy = tmp_path / "_legacy"

    res = tc.swap_model_to_view(model, truths, legacy)
    assert res["swapped"] is True
    assert tc.legacy_path(model, legacy).read_bytes() == original_bytes  # Original heilig gesichert

    assert tc.rollback_model(model, legacy)["restored"] is True
    assert model.read_bytes() == original_bytes  # INV-MIG-11


def test_swap_refused_on_roundtrip_fail(tmp_path):
    # CUTOVER-SAFE-1: Truths die nicht zum Original passen -> KEIN Swap, Original unberuehrt.
    model = tmp_path / "X_Model.md"
    model.write_text("# M\n\n### W01\nEins.\n", encoding="utf-8")
    before = model.read_bytes()
    bad = ta.atomize("### W99\nAnders.\n", "BL-x")
    res = tc.swap_model_to_view(model, bad, tmp_path / "_legacy")
    assert res["swapped"] is False and res["reason"] == "roundtrip_failed"
    assert model.read_bytes() == before  # Original UNBERUEHRT


def test_backup_legacy_idempotent_original_sacred(tmp_path):
    # CUTOVER-SAFE-2: ein bereits gesichertes Original wird NIE ueberschrieben.
    model = tmp_path / "X_Model.md"
    model.write_text("ORIGINAL\n", encoding="utf-8")
    legacy = tmp_path / "_legacy"
    tc.backup_to_legacy(model, legacy)
    model.write_text("CHANGED\n", encoding="utf-8")  # spaeterer Stand (z.B. schon die View)
    tc.backup_to_legacy(model, legacy)               # darf das heilige Original NICHT ueberschreiben
    assert tc.legacy_path(model, legacy).read_text(encoding="utf-8") == "ORIGINAL\n"


def test_cutover_model_full_cycle(tmp_path):
    bl = tmp_path / "BL-x" / "2_Model"
    bl.mkdir(parents=True)
    model = bl / "Foo_Model.md"
    model.write_text(_MODEL, encoding="utf-8")
    original_bytes = model.read_bytes()

    res = tc.cutover_model(model, "BL-x")
    assert res["cutover"] is True and res["knots"] == 2
    assert len(list((bl / "truths").glob("*.md"))) == 2  # truths geschrieben

    # Rollback byte-identisch (Original in _legacy gesichert)
    assert tc.rollback_model(model, bl / "_legacy")["restored"] is True
    assert model.read_bytes() == original_bytes


def test_rollback_without_legacy_is_safe(tmp_path):
    model = tmp_path / "X_Model.md"
    model.write_text("x\n", encoding="utf-8")
    assert tc.rollback_model(model, tmp_path / "_legacy")["restored"] is False  # kein Legacy -> No-Op


# ── B2-aware Cutover (BL-395): SEGMENT-Model byte-verlustfrei swappen; Quarantaene refusen ──

_SEGMENT_MODEL = "# Konsolidiert\n\n- W1: erste Wahrheit ausfuehrlich\n- W2: zweite ebenso\n- W3: dritte\n"


def test_cutover_segment_model_byte_lossless_and_rollback(tmp_path):
    """SEGMENT-Model (Bullet, 0 ## W-Heading): Cutover via build_segment_view -> Model.md BYTE-identisch
    zur Quelle (verbatim-View), truths geschrieben, Rollback byte-identisch. KEIN Verlust (vs alter
    HEADING-only-Pfad, der hier eine leere View geschrieben + den blinden Roundtrip bestanden haette)."""
    bl = tmp_path / "BL-seg" / "2_Model"
    bl.mkdir(parents=True)
    model = bl / "K_Model.md"
    model.write_text(_SEGMENT_MODEL, encoding="utf-8")
    original_bytes = model.read_bytes()

    res = tc.cutover_model(model, "BL-seg")
    assert res["cutover"] is True
    assert res["format_hint"] == "SEGMENT-B2" and res["view_mode"] == "verbatim"
    assert res["knots"] == 3
    assert len(list((bl / "truths").glob("*.md"))) == 3
    assert model.read_bytes() == original_bytes          # SEGMENT-View == Quelle byte-identisch (verlustfrei)

    assert tc.rollback_model(model, bl / "_legacy")["restored"] is True
    assert model.read_bytes() == original_bytes          # INV-MIG-11


def test_cutover_refuses_quarantined_no_wdef_prose(tmp_path):
    """Pure Prosa ohne W-Definition (= eine der 8 genuine Quarantaene-Klassen): Cutover REFUSED,
    Original UNBERUEHRT, KEIN Legacy. Strukturell unmoeglich, eine verlustige View zu schreiben."""
    bl = tmp_path / "BL-prose" / "2_Model"
    bl.mkdir(parents=True)
    model = bl / "P_Model.md"
    model.write_text("# Titel\n\nNur Fliesstext ohne jeden W-Knoten. Zweiter Absatz.\n", encoding="utf-8")
    before = model.read_bytes()

    res = tc.cutover_model(model, "BL-prose")
    assert res["cutover"] is False
    assert res["reason"] in ("no_truths", "low_coverage")
    assert model.read_bytes() == before                  # Original UNBERUEHRT
    assert not (bl / "_legacy").exists()                  # kein Backup -> kein begonnener Swap


def test_swap_segment_truths_byte_identical(tmp_path):
    """swap_model_to_view erkennt SEGMENT-Truths (view_mode==verbatim) -> build_segment_view + Byte-Gate."""
    model = tmp_path / "K_Model.md"
    model.write_text(_SEGMENT_MODEL, encoding="utf-8")
    truths = ta.atomize_segments(_SEGMENT_MODEL, "BL-seg")
    res = tc.swap_model_to_view(model, truths, tmp_path / "_legacy")
    assert res["swapped"] is True and res["view_mode"] == "verbatim"
    assert model.read_text(encoding="utf-8") == _SEGMENT_MODEL   # byte-identisch


def test_cutover_refuses_truth_count_loss(tmp_path, monkeypatch):
    """RED: cutover_model MUSS bei atomized knots < census estimate (truth_count_loss) REFUSE
    (cutover=False, reason='truth_count_loss') und DARF weder truths/ noch _legacy/ anlegen.

    Safety-Bug: aktuell fehlt der Census-Guard in cutover_model. Ohne Guard:
      -> write_truths + swap_model_to_view werden aufgerufen
      -> swap_model_to_view legt _legacy/ an und swapt das Model
      -> cutover=True (SAFETY-VERLUST: atomize hat Knoten verloren, aber cutover schreibt trotzdem)

    Approach (a): echter truth_census.count_wknots auf 3-Heading-Body -> total_estimate=3 verifiziert.
    Monkeypatch ta.atomize_model_file gibt nur 2 Truths zurueck (< census=3, kein anderer Fehler).
    ta.write_truths / ta.roundtrip_ok / ta.build_model_view monkeypatcht, damit der aktuelle Code
    ohne Census-Guard den vollstaendigen Swap versucht (-> cutover=True, _legacy/ erstellt) und die
    Assertion-1 (cutover is False) + Assertion-3 (_legacy/ nicht vorhanden) als klares RED scheitern.
    Nach Fix: Census-Guard vor write_truths -> sofortiges REFUSE -> alle 4 Assertions GRUEN.
    """
    import truth_cutover  # fuer Zugriff auf truth_cutover.ta (das importierte truth_atomizer-Modul)

    # 3 W-Headings -> count_wknots(text)["total_estimate"] == 3 (Approach a, empirisch verifiziert:
    # headings=3, member_defs=3, total_estimate=max(3,0,0,0,3,0)=3)
    _BODY = "# M\n\n### W01\nEins.\n\n### W02\nZwei.\n\n### W03\nDrei.\n"

    bl = tmp_path / "BL-tcl" / "2_Model"
    bl.mkdir(parents=True)
    model = bl / "Foo_Model.md"
    model.write_text(_BODY, encoding="utf-8")

    # 2 Fake-Truths (keine view_mode=verbatim -> geht ueber HEADING-Pfad in swap_model_to_view,
    # kein _verbatim-Key -> _is_segment_truths=False)
    _fake_truths = [
        {"local_id": "W01", "title": "Eins"},
        {"local_id": "W02", "title": "Zwei"},
    ]

    # Monkeypatch: atomize_model_file -> 2 Truths (< census=3), kein anderer Quarantaene-Grund
    monkeypatch.setattr(
        truth_cutover.ta, "atomize_model_file",
        lambda path, ns: {
            "knots": 2,
            "truths": _fake_truths,
            "roundtrip_ok": True,
            "low_coverage": False,
            "schema_errors": 0,
            "format_hint": None,
        },
    )
    # Monkeypatch: write_truths -> no-op (kein truths/-Write; sauberer side-effect-Check)
    monkeypatch.setattr(truth_cutover.ta, "write_truths", lambda truths, d: 0)
    # Monkeypatch: roundtrip_ok -> True + build_model_view -> _BODY, damit swap_model_to_view
    # im aktuellen Code (ohne Census-Guard) swapped=True zurueckgibt (-> cutover=True, _legacy/ erstellt)
    monkeypatch.setattr(truth_cutover.ta, "roundtrip_ok", lambda original, truths: True)
    monkeypatch.setattr(truth_cutover.ta, "build_model_view", lambda truths: _BODY)

    res = truth_cutover.cutover_model(model, "BL-tcl")

    # PRIMAERASSERT: Guard fehlt -> aktuell cutover=True -> FAIL = RED
    assert res["cutover"] is False, f"Expected cutover=False (truth_count_loss guard missing!), got: {res}"
    assert res.get("reason") == "truth_count_loss", (
        f"Expected reason='truth_count_loss', got reason={res.get('reason')!r} (full: {res})"
    )
    # SEITENEFFEKT-Guards: kein Write-Artefakt vor dem Refuse angelegt
    assert not (bl / "truths").exists(), "truths/ dir created despite truth_count_loss REFUSE"
    assert not (bl / "_legacy").exists(), "_legacy/ dir created despite truth_count_loss REFUSE"
