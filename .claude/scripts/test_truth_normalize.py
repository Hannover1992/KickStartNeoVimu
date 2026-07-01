#!/usr/bin/env python3
"""test_truth_normalize.py — RED-Worker-Tests fuer BL-397 (Model-Vorab-Normalisierung).

RED!=GREEN-Konvention: dieser Worker schreibt NUR Tests gegen das (noch nicht existierende)
truth_normalize.py. Er definiert die API durch die Tests. Bis truth_normalize.py + die geforderten
Funktionen existieren, faellt die ganze Suite (ModuleNotFoundError / AttributeError) = RED.

Reuse (importiert, NICHT neu gebaut): truth_atomizer (atomize_model_file/heading_adequate-Logik/
_content_preserved), truth_cutover (backup/rollback-Muster), truth_census (count_wknots),
truth_wid (WDEF_LINE/_HEADING_LINE-Lexikon), truth_gate_check (run_gates).

Erwartete truth_normalize-API (durch Tests definiert):
  - is_canonical_format(model_text)  -> (bool, [reasons])                            # AK-1
  - classify_drift(model_text)       -> {drift_type, distance, segment_reason}       # AK-2
  - classify_corpus(list[text])      -> {drift_type: count}  (read-only Histogramm)  # AK-2 DoD-2.4
  - normalize_model(model_path, *, legacy_dir=None) -> dict                          # AK-3
        {normalized: bool, format_hint, content_faithful, legacy, reason?}
  - normalize_text(model_text) -> str | None  (None = nicht content-faithful)        # AK-3 (in-mem)
  - rollback(model_path, legacy_dir) -> {restored: bool, reason?}                    # AK-3 DoD-3.5
  - normalize_until_canonical(model_text, *, max_rounds=...) -> dict                 # AK-4
        {status: "konvergiert"|"nicht_normalisierbar", rounds, reasons:[...], text?}
  - slimming_gain(list[text]) -> dict                                               # AK-5
        {heading_before, heading_after, gain, content_loss}
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

import truth_atomizer as ta  # Reuse: bewiesener Atomizer (Orakel fuer kanonisch/content-faithful)

# truth_normalize existiert (noch) NICHT -> harter Import (NICHT importorskip): RED muss FAILEN,
# nicht SKIPpen — ein geskippter Test beweist kein RED. GREEN baut das Modul -> Import gelingt.
import truth_normalize as tn  # noqa: E402  (RED: ModuleNotFoundError bis GREEN baut)


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures: synthetische Model-Strings je Drift-Typ (tmp).
# Der kanonische Referenz-Body ist content-faithful aequivalent zu allen drifted Varianten
# (gleiche W-Definitionen W1/W2/W3, gleicher Sinn) -> Census-Gleichheit beweisbar.
# ──────────────────────────────────────────────────────────────────────────────

NS = "BL-397-test"


@pytest.fixture
def canonical_model() -> str:
    """Kanonische Format-A-Form: ### W{n} + atomarer Body, keine Nicht-W-Sektion, kein Range."""
    return (
        "### W1: Erste Wahrheit\n"
        "Der Body der ersten Wahrheit.\n\n"
        "### W2: Zweite Wahrheit\n"
        "Der Body der zweiten Wahrheit.\n\n"
        "### W3: Dritte Wahrheit\n"
        "Der Body der dritten Wahrheit.\n"
    )


@pytest.fixture
def drifted_bullet_model() -> str:
    """Bullet-Drift: W-Definitionen als Dash-Bullets statt Headings (BL-050-Generation)."""
    return (
        "- W1: Erste Wahrheit — Der Body der ersten Wahrheit.\n"
        "- W2: Zweite Wahrheit — Der Body der zweiten Wahrheit.\n"
        "- W3: Dritte Wahrheit — Der Body der dritten Wahrheit.\n"
    )


@pytest.fixture
def drifted_table_model() -> str:
    """Table-Drift: W-Definitionen in Tabellen-Zellen."""
    return (
        "| ID | Aussage |\n"
        "|----|---------|\n"
        "| W1 | Erste Wahrheit |\n"
        "| W2 | Zweite Wahrheit |\n"
        "| W3 | Dritte Wahrheit |\n"
    )


@pytest.fixture
def drifted_bold_model() -> str:
    """Bold-Marker-Drift: **W01** (BL-111-Generation)."""
    return (
        "**W1** Erste Wahrheit. Body eins.\n\n"
        "**W2** Zweite Wahrheit. Body zwei.\n\n"
        "**W3** Dritte Wahrheit. Body drei.\n"
    )


@pytest.fixture
def drifted_bare_model() -> str:
    """Bare-Drift: W1: ... am Zeilenanfang ohne Marker (PrePR-Generation)."""
    return (
        "W1: Erste Wahrheit. Body eins.\n\n"
        "W2: Zweite Wahrheit. Body zwei.\n\n"
        "W3: Dritte Wahrheit. Body drei.\n"
    )


@pytest.fixture
def drifted_range_model() -> str:
    """Range-Heading-Drift: ### W1-W3 packt N Wahrheiten unter EINE Ueberschrift (Atomaritaets-Verlust)."""
    return (
        "### W1-W3 Die drei Wahrheiten\n"
        "- W1: Erste Wahrheit.\n"
        "- W2: Zweite Wahrheit.\n"
        "- W3: Dritte Wahrheit.\n"
    )


@pytest.fixture
def drifted_preamble_model() -> str:
    """Preamble-Drift: substantieller Nicht-W-Content VOR dem ersten W-Heading
    (HEADING-View droppt ihn -> content_not_preserved)."""
    return (
        "Dies ist eine lange einleitende Sektion mit echtem Inhalt, der kein W-Knoten ist "
        "und beim reinen HEADING-Atomize verloren gehen wuerde. Mehrere Saetze.\n\n"
        "### W1: Erste Wahrheit\n"
        "Body eins.\n\n"
        "### W2: Zweite Wahrheit\n"
        "Body zwei.\n"
    )


@pytest.fixture
def nicht_normalisierbar_model() -> str:
    """Kein aufloesbares W-Definitions-Signal (nur Prosa, W-Token nur als Cross-Ref im Satz)
    -> kein kanonischer Pfad erzeugbar -> 'nicht_normalisierbar'."""
    return (
        "Dieses Dokument enthaelt keine echten W-Definitionen am Zeilenanfang. "
        "Es erwaehnt W1 nur mitten im Satz als Referenz und hat sonst nur Fliesstext.\n\n"
        "Noch ein Absatz reiner Prosa ohne strukturierte Wahrheits-Knoten.\n"
    )


def _write_model(tmp_path: Path, name: str, text: str) -> Path:
    """Schreibt ein tmp-Model in eine 2_Model/-Struktur (atomize_model_file liest Pfade)."""
    d = tmp_path / "2_Model"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(text, encoding="utf-8")
    return p


# ──────────────────────────────────────────────────────────────────────────────
# AK-1: is_canonical_format(model_text) -> (bool, [reasons])
# ──────────────────────────────────────────────────────────────────────────────

class TestAK1IsCanonicalFormat:
    def test_canonical_returns_true_empty_reasons(self, canonical_model):
        ok, reasons = tn.is_canonical_format(canonical_model)
        assert ok is True
        assert reasons == []

    def test_canonical_consistent_with_atomizer_heading_path(self, tmp_path, canonical_model):
        # DoD-1.2/1.4: kanonisch <-> atomize_model_file().format_hint == "HEADING"
        p = _write_model(tmp_path, "canon.md", canonical_model)
        res = ta.atomize_model_file(p, NS)
        ok, _ = tn.is_canonical_format(canonical_model)
        assert ok is True
        assert res["format_hint"] == "HEADING"

    def test_bullet_drift_false_with_reason(self, drifted_bullet_model):
        ok, reasons = tn.is_canonical_format(drifted_bullet_model)
        assert ok is False
        assert reasons  # nicht-leer
        # erwarteter benannter Grund: keine Headings / Census-Unterdeckung
        assert any("no_headings" in r or "census_undercover" in r for r in reasons)

    def test_range_drift_false_with_range_reason(self, drifted_range_model):
        ok, reasons = tn.is_canonical_format(drifted_range_model)
        assert ok is False
        assert any("range_collapsed" in r for r in reasons)

    def test_preamble_drift_false_with_content_reason(self, drifted_preamble_model):
        ok, reasons = tn.is_canonical_format(drifted_preamble_model)
        assert ok is False
        assert any("content_not_preserved" in r for r in reasons)

    def test_drifted_inconsistent_with_heading_path(self, tmp_path, drifted_bullet_model):
        # DoD-1.4 Kontrapositiv: drifted -> format_hint != "HEADING"
        p = _write_model(tmp_path, "drift.md", drifted_bullet_model)
        res = ta.atomize_model_file(p, NS)
        ok, _ = tn.is_canonical_format(drifted_bullet_model)
        assert ok is False
        assert res["format_hint"] != "HEADING"


# ──────────────────────────────────────────────────────────────────────────────
# AK-2: classify_drift(model) -> {drift_type, distance, segment_reason} + Korpus-Histogramm
# ──────────────────────────────────────────────────────────────────────────────

class TestAK2ClassifyDrift:
    def test_returns_three_part_shape(self, drifted_bullet_model):
        d = tn.classify_drift(drifted_bullet_model)
        assert set(d) >= {"drift_type", "distance", "segment_reason"}

    def test_canonical_drift_type_heading_clean(self, canonical_model):
        d = tn.classify_drift(canonical_model)
        assert d["drift_type"] == "heading_clean"

    def test_canonical_distance_zero(self, canonical_model):
        # DoD-2.2: distance == WDEF_LINE - _HEADING_LINE; kanonisch -> 0
        d = tn.classify_drift(canonical_model)
        assert d["distance"] == 0

    def test_bullet_drift_type(self, drifted_bullet_model):
        assert tn.classify_drift(drifted_bullet_model)["drift_type"] == "bullet"

    def test_table_drift_type(self, drifted_table_model):
        assert tn.classify_drift(drifted_table_model)["drift_type"] == "table"

    def test_bold_drift_type(self, drifted_bold_model):
        assert tn.classify_drift(drifted_bold_model)["drift_type"] == "bold"

    def test_bare_drift_type(self, drifted_bare_model):
        assert tn.classify_drift(drifted_bare_model)["drift_type"] == "bare"

    def test_range_heading_drift_type(self, drifted_range_model):
        assert tn.classify_drift(drifted_range_model)["drift_type"] == "range_heading"

    def test_distance_is_wdef_minus_heading(self, drifted_bullet_model):
        # DoD-2.2: positive Distanz bei reinem Bullet (WDEF zaehlt 3, HEADING 0)
        d = tn.classify_drift(drifted_bullet_model)
        assert d["distance"] == 3

    def test_segment_reason_is_three_part(self, drifted_preamble_model):
        # DoD-2.3: segment_reason schluesselt die 3 heading_adequate-Bedingungen auf
        sr = tn.classify_drift(drifted_preamble_model)["segment_reason"]
        # 3-teilig maschinen-lesbar (W3/W4/W5): no_headings / census_undercover / content_not_preserved
        keys = set(sr) if isinstance(sr, dict) else set(sr)
        assert {"no_headings", "census_undercover", "content_not_preserved"} <= keys

    def test_segment_reason_flags_content_not_preserved_for_preamble(self, drifted_preamble_model):
        sr = tn.classify_drift(drifted_preamble_model)["segment_reason"]
        val = sr["content_not_preserved"] if isinstance(sr, dict) else ("content_not_preserved" in sr)
        assert val

    def test_corpus_histogram(self, drifted_bullet_model, drifted_table_model, canonical_model):
        # DoD-2.4: Korpus -> Histogramm drift_type -> count
        hist = tn.classify_corpus([drifted_bullet_model, drifted_table_model, canonical_model])
        assert hist.get("bullet") == 1
        assert hist.get("table") == 1
        assert hist.get("heading_clean") == 1

    def test_classify_drift_is_read_only(self, tmp_path, drifted_bullet_model):
        # DoD-2.4 read-only-INV: tmp-Model byte-unveraendert nach Analyzer-Lauf
        p = _write_model(tmp_path, "ro.md", drifted_bullet_model)
        before = p.read_bytes()
        tn.classify_drift(p.read_text(encoding="utf-8"))
        assert p.read_bytes() == before


# ──────────────────────────────────────────────────────────────────────────────
# AK-3: normalize_model(model) -> kanonische Form, content-faithful + reversibel
# ──────────────────────────────────────────────────────────────────────────────

def _census_local_ids(text: str) -> set:
    """Reuse truth_census-Lexikon: distinkte W-Def-local_ids (Census-Gleichheits-Beweis)."""
    import truth_census as tc
    return set(tc._WDEF_LINE.findall(text))


class TestAK3NormalizeModel:
    def test_normalize_bullet_to_heading_path(self, tmp_path, drifted_bullet_model):
        # DoD-3.1: normalisiertes Model -> atomize_model_file().format_hint == "HEADING"
        p = _write_model(tmp_path, "b.md", drifted_bullet_model)
        res = tn.normalize_model(p, legacy_dir=tmp_path / "_legacy")
        assert res["normalized"] is True
        after = ta.atomize_model_file(p, NS)
        assert after["format_hint"] == "HEADING"

    def test_normalize_table_to_heading_path(self, tmp_path, drifted_table_model):
        p = _write_model(tmp_path, "t.md", drifted_table_model)
        res = tn.normalize_model(p, legacy_dir=tmp_path / "_legacy")
        assert res["normalized"] is True
        assert ta.atomize_model_file(p, NS)["format_hint"] == "HEADING"

    def test_census_equal_after_normalize(self, tmp_path, drifted_bullet_model):
        # DoD-3.2 content-faithful: gleiche W-Def-local_id-Menge vor/nach (nichts verloren/erfunden)
        before_ids = _census_local_ids(drifted_bullet_model)
        p = _write_model(tmp_path, "c.md", drifted_bullet_model)
        tn.normalize_model(p, legacy_dir=tmp_path / "_legacy")
        after_ids = _census_local_ids(p.read_text(encoding="utf-8"))
        assert after_ids == before_ids

    def test_content_preserved_after_normalize(self, tmp_path, drifted_bullet_model):
        # DoD-3.3: 0 Content-Verlust gegen Original-Body (_content_preserved-Muster)
        p = _write_model(tmp_path, "cp.md", drifted_bullet_model)
        res = tn.normalize_model(p, legacy_dir=tmp_path / "_legacy")
        assert res["content_faithful"] is True

    def test_backup_pre_normalize_created(self, tmp_path, drifted_bullet_model):
        # DoD-3.4: {legacy}/{stem}.pre_normalize.md entsteht byte-genau
        legacy = tmp_path / "_legacy"
        p = _write_model(tmp_path, "bk.md", drifted_bullet_model)
        original = p.read_bytes()
        tn.normalize_model(p, legacy_dir=legacy)
        backup = legacy / "bk.pre_normalize.md"
        assert backup.exists()
        assert backup.read_bytes() == original

    def test_backup_suffix_distinct_from_cutover(self, tmp_path, drifted_bullet_model):
        # DoD-3.4 F-12: .pre_normalize.md kollidiert NICHT mit Cutover-.pre_truth.md
        legacy = tmp_path / "_legacy"
        p = _write_model(tmp_path, "sx.md", drifted_bullet_model)
        tn.normalize_model(p, legacy_dir=legacy)
        assert (legacy / "sx.pre_normalize.md").exists()
        assert not (legacy / "sx.pre_truth.md").exists()

    def test_backup_idempotent_never_overwritten(self, tmp_path, drifted_bullet_model):
        # DoD-3.4 idempotent: 2. Lauf ueberschreibt das Backup nie (Original heilig)
        legacy = tmp_path / "_legacy"
        p = _write_model(tmp_path, "id.md", drifted_bullet_model)
        original = p.read_bytes()
        tn.normalize_model(p, legacy_dir=legacy)
        backup = legacy / "id.pre_normalize.md"
        first_backup = backup.read_bytes()
        # zweiter Lauf (Model ist jetzt schon kanonisch) darf das Original-Backup nicht zerstoeren
        tn.normalize_model(p, legacy_dir=legacy)
        assert backup.read_bytes() == first_backup == original

    def test_rollback_byte_identical(self, tmp_path, drifted_bullet_model):
        # DoD-3.5 rollback: BYTE-IDENTISCH aus .pre_normalize.md (INV-MIG-11-Muster)
        legacy = tmp_path / "_legacy"
        p = _write_model(tmp_path, "rb.md", drifted_bullet_model)
        original = p.read_bytes()
        tn.normalize_model(p, legacy_dir=legacy)
        assert p.read_bytes() != original  # tatsaechlich normalisiert
        res = tn.rollback(p, legacy)
        assert res["restored"] is True
        assert p.read_bytes() == original

    def test_guarded_no_persist_without_content_faithful(self, tmp_path, nicht_normalisierbar_model):
        # DoD-3.6 guarded: nicht-faithful Transform wird NICHT geschrieben (CUTOVER-SAFE-1-Analogon)
        legacy = tmp_path / "_legacy"
        p = _write_model(tmp_path, "guard.md", nicht_normalisierbar_model)
        original = p.read_bytes()
        res = tn.normalize_model(p, legacy_dir=legacy)
        assert res["normalized"] is False
        assert res.get("reason")            # Grund gemeldet
        assert p.read_bytes() == original   # Model unveraendert


# ──────────────────────────────────────────────────────────────────────────────
# AK-4: multi-round bis Konvergenz ODER "nicht_normalisierbar" + harter Cap
# ──────────────────────────────────────────────────────────────────────────────

class TestAK4MultiRound:
    def test_converges_to_heading_adequate(self, drifted_bullet_model):
        # DoD-4.1: konvergiert zu heading_adequate == True
        res = tn.normalize_until_canonical(drifted_bullet_model)
        assert res["status"] == "konvergiert"
        ok, _ = tn.is_canonical_format(res["text"])
        assert ok is True

    def test_range_converges_over_multiple_rounds(self, drifted_range_model):
        # DoD-4.1: Range braucht ggf. >1 Runde (Range-Split -> Bullet-Members -> Headings)
        res = tn.normalize_until_canonical(drifted_range_model)
        assert res["status"] == "konvergiert"
        assert res["rounds"] >= 1

    def test_non_normalizable_explicit_marker(self, nicht_normalisierbar_model):
        # DoD-4.2: explizites status=="nicht_normalisierbar" + nicht-leere Gruende, KEIN stilles True
        res = tn.normalize_until_canonical(nicht_normalisierbar_model)
        assert res["status"] == "nicht_normalisierbar"
        assert res["reasons"]

    def test_hard_iteration_cap(self, nicht_normalisierbar_model):
        # DoD-4.3: harter Cap greift -> Marker statt Hang/Exception; rounds <= cap
        res = tn.normalize_until_canonical(nicht_normalisierbar_model, max_rounds=3)
        assert res["status"] == "nicht_normalisierbar"
        assert res["rounds"] <= 3

    def test_cap_does_not_raise(self, nicht_normalisierbar_model):
        # DoD-4.3: kein Endlos-Loop, keine Exception
        res = tn.normalize_until_canonical(nicht_normalisierbar_model, max_rounds=2)
        assert res["status"] in {"konvergiert", "nicht_normalisierbar"}


# ──────────────────────────────────────────────────────────────────────────────
# AK-5: Slimming-Gewinn messbar bei content-loss=0; truth_gate_check bleibt voll gruen
# ──────────────────────────────────────────────────────────────────────────────

class TestAK5SlimmingGain:
    def test_heading_share_rises(self, drifted_bullet_model, drifted_table_model, drifted_bold_model):
        # DoD-5.1: HEADING-Anteil nach normalize > davor
        corpus = [drifted_bullet_model, drifted_table_model, drifted_bold_model]
        m = tn.slimming_gain(corpus)
        assert m["heading_after"] > m["heading_before"]
        assert m["gain"] > 0

    def test_slimming_at_zero_content_loss(self, drifted_bullet_model, drifted_table_model):
        # DoD-5.2: Steigerung bei content-loss == 0
        m = tn.slimming_gain([drifted_bullet_model, drifted_table_model])
        assert m["content_loss"] == 0

    def test_gate_check_full_green_on_normalized(self, tmp_path, drifted_bullet_model):
        # DoD-5.3: run_gates voll gruen auf einem normalisierten tmp-Model (kein Gate gebrochen)
        import truth_gate_check as tg
        p = _write_model(tmp_path, "gate.md", drifted_bullet_model)
        tn.normalize_model(p, legacy_dir=tmp_path / "_legacy")
        rep = tg.run_gates(tmp_path, None)
        steps = rep["steps"] if isinstance(rep, dict) and "steps" in rep else rep
        assert steps  # nicht-leer
        assert all(s["pass"] for s in steps)


# ──────────────────────────────────────────────────────────────────────────────
# AK-6 (DoD-6.1 coverable): truth_normalize.py als eigenstaendiges CLI
# ──────────────────────────────────────────────────────────────────────────────

class TestAK6CLI:
    def test_has_argparse_main(self):
        # DoD-6.1: CLI aufrufbar (main mit exit-code), eigenstaendig
        assert hasattr(tn, "main")
        assert callable(tn.main)

    def test_cli_classify_exit_zero(self, tmp_path, drifted_bullet_model, capsys):
        # DoD-6.1: read-only classify-Lauf gibt exit-code 0 ohne BL-398
        p = _write_model(tmp_path, "cli.md", drifted_bullet_model)
        rc = tn.main(["classify", str(p)])
        assert rc == 0
