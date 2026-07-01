#!/usr/bin/env python3
"""Tests fuer truth_atomizer.py (BL-309 Phase B / Migrations-Anstoss)."""
from __future__ import annotations

import hashlib

import truth_atomizer as ta
import truth_schema as ts

_MODEL = """# Mein Model

## Wahrheiten

### W01
Erste Aussage.

### W02
Zweite Aussage.
mit zweiter Zeile.

### W-IST-1
Dashed knot.
"""


def test_parse_model_headings_counts_only_w_knots():
    knots = ta.parse_model_headings(_MODEL)
    assert [k["local_id"] for k in knots] == ["W01", "W02", "W-IST-1"]
    # '## Wahrheiten' und '# Mein Model' sind KEINE W-Knoten


def test_parse_captures_body_until_next_heading():
    knots = {k["local_id"]: k for k in ta.parse_model_headings(_MODEL)}
    assert knots["W01"]["text"] == "Erste Aussage."
    assert knots["W02"]["text"] == "Zweite Aussage.\nmit zweiter Zeile."
    assert knots["W-IST-1"]["text"] == "Dashed knot."


def test_original_heading_is_byte_verbatim():
    knots = {k["local_id"]: k for k in ta.parse_model_headings(_MODEL)}
    assert knots["W01"]["original_heading"] == "### W01"


def test_atomize_produces_schema_valid_truths():
    """Integration: jede atomisierte Wahrheit besteht validate_truth ohne ERROR."""
    truths = ta.atomize(_MODEL, "BL-x")
    assert len(truths) == 3
    for t in truths:
        errors = [m for s, m in ts.validate_truth(t) if s == "ERROR"]
        assert errors == [], f"{t['local_id']}: {errors}"


def test_atomize_id_is_dotted_namespace():
    truths = {t["local_id"]: t for t in ta.atomize(_MODEL, "BL-309-truth-migration")}
    assert truths["W01"]["id"] == "BL-309-truth-migration.W01"


def test_content_hash_is_sha256_of_text():
    t = ta.atomize(_MODEL, "BL-x")[0]
    assert t["content_hash"] == hashlib.sha256(t["text"].encode("utf-8")).hexdigest()


def test_roundtrip_proof_holds_for_heading_model():
    truths = ta.atomize(_MODEL, "BL-x")
    assert ta.roundtrip_ok(_MODEL, truths) is True


def test_non_heading_text_yields_no_knots():
    truths = ta.atomize("Nur Prosa ohne W-Headings.\n## Abschnitt\nText.", "BL-x")
    assert truths == []


def test_write_truths_is_idempotent(tmp_path):
    truths = ta.atomize(_MODEL, "BL-x")
    out = tmp_path / "truths"
    first = ta.write_truths(truths, out)
    assert first == {"written": 3, "skipped": 0, "total": 3}
    second = ta.write_truths(truths, out)  # Re-Run = 0 Diff
    assert second == {"written": 0, "skipped": 3, "total": 3}


def test_written_truth_file_is_schema_valid(tmp_path):
    import validate_vault_schema as vvs
    truths = ta.atomize(_MODEL, "BL-x")
    out = tmp_path / "truths"
    ta.write_truths(truths, out)
    issues = vvs.validiere_doc(out / "W01.md")
    # truth-spezifisch sauber (PFLICHT_ALL wie feature/bl-item fehlen hier bewusst -> die ERRORs
    # sind PFLICHT_ALL, nicht truth-spezifisch; wir pruefen: KEIN truth-spezifischer ERROR)
    truth_errors = [m for s, m in issues if s == "ERROR" and "truth" in m]
    assert truth_errors == []


_MODEL_NO_PREAMBLE = (
    "### W01\nErste Aussage.\n\n### W02\nZweite Aussage.\nmit zweiter Zeile.\n\n### W-IST-1\nDashed knot.\n"
)


def test_atomize_model_file_end_to_end(tmp_path):
    """Reines HEADING-Model OHNE Preamble (startet direkt mit ### W01) -> HEADING-Pfad (schlanke View,
    content-verlustfrei)."""
    mp = tmp_path / "Foo_Model.md"
    mp.write_text(_MODEL_NO_PREAMBLE, encoding="utf-8")
    res = ta.atomize_model_file(mp, "BL-x")
    assert res["knots"] == 3
    assert res["roundtrip_ok"] is True
    assert res["schema_errors"] == 0
    assert res["format_hint"] == "HEADING"


def test_titled_preamble_routes_to_segment_byte_identical(tmp_path):
    """BL-396: ein HEADING-Model MIT Titel/Intro-Preamble (`# Titel`/`## Sektion` vor dem 1. W-Heading)
    wuerde auf dem HEADING-Pfad die Preamble still verlieren -> der content-faithful Router schickt es auf
    den SEGMENT-Pfad (View == Source BYTE-identisch, Preamble erhalten). Genau der OmniCommandUltraThink-Fall."""
    mp = tmp_path / "Titled_Model.md"
    mp.write_text(_MODEL, encoding="utf-8")            # _MODEL hat '# Mein Model' + '## Wahrheiten' Preamble
    res = ta.atomize_model_file(mp, "BL-x")
    assert res["format_hint"] == "SEGMENT-B2"          # NICHT HEADING (Preamble haette Content verloren)
    assert res["roundtrip_ok"] is True                 # build_segment_view == Source byte-identisch
    assert res["low_coverage"] is False
    # die Preamble steckt verlustfrei im _verbatim des 1. Segments
    assert "Mein Model" in res["truths"][0]["_verbatim"]
    assert "Wahrheiten" in res["truths"][0]["_verbatim"]


def test_atomize_sets_lifecycle_asserted_default():
    """Schema v2: Legacy-Knoten bekommen lifecycle='asserted' (reift via Scientific-Mode)."""
    truths = ta.atomize(_MODEL, "BL-x")
    assert all(t["lifecycle"] == "asserted" for t in truths)


def test_atomize_extracts_keywords():
    """R3: one-shot keyword-Capture pro Wahrheit (mind. eine traegt keywords)."""
    truths = ta.atomize(_MODEL, "BL-x")
    assert any("keywords" in t and t["keywords"] for t in truths)


def test_atomize_forward_edges_from_text():
    """Forward-Edges aus W-Refs im Text (bidirektional mit referenced_by); Selbst-Ref aus."""
    model = "### W01\nDies haengt von W05 ab.\n\n### W05\nBasis ohne Ref.\n"
    truths = {t["local_id"]: t for t in ta.atomize(model, "BL-x")}
    assert truths["W01"]["edges"] == [{"rel": "relates_to", "ziel": "W05"}]
    assert "edges" not in truths["W05"]


def test_atomize_with_edges_keywords_still_schema_valid():
    import truth_schema as ts
    model = "### W01\nDies haengt von W05 ab und betrifft Migration.\n\n### W05\nBasis.\n"
    for t in ta.atomize(model, "BL-x"):
        assert [m for s, m in ts.validate_truth(t) if s == "ERROR"] == []


def test_atomize_detects_frage_typ():
    """typ-Erkennung: ein Knoten mit '?' wird FRAGE (nicht der FESTSTELLUNG-Default)."""
    t = ta.atomize("### W1\nIst die Migration verlustfrei?\n", "BL-x")[0]
    assert t["typ"] == "FRAGE"


def test_atomize_extracts_ref_suffix_headings():
    """W7_REF-Stil (Referenz-Knoten) + W-DERIV-1 werden extrahiert (BL-174-Fix, nichts verlieren)."""
    model = "### W7_REF: BL-165:W7 — Schema\nRef-Knoten.\n\n### W-DERIV-1: Algo\nNeuer Knoten.\n"
    lids = [t["local_id"] for t in ta.atomize(model, "BL-x")]
    assert "W7_REF" in lids and "W-DERIV-1" in lids


def test_atomize_dedups_repeated_heading_lossless():
    """Multi-Sektion-Model (### W1 mehrfach): verlustfreie Disambiguierung W1/W1~2 (kein Overwrite)."""
    import truth_schema as ts
    model = "### W1\nErste Variante.\n\n### W1\nZweite Variante.\n"
    truths = ta.atomize(model, "BL-x")
    assert [t["local_id"] for t in truths] == ["W1", "W1~2"]
    assert len({t["id"] for t in truths}) == 2  # eindeutige ids (INV-MIG-10)
    assert ta.roundtrip_ok(model, truths) is True  # Roundtrip haelt (parst Heading, nicht local_id)
    for t in truths:
        assert [m for s, m in ts.validate_truth(t) if s == "ERROR"] == []


# ── BL-391 (B): Range-Heading-Kollaps-Detektor (### W16-W19 -> W17/W18/W19 kollabieren) ──

def test_detect_range_collapse_hyphen():
    """### W16-W19 mit nur W16 extrahiert -> W17/W18/W19 als kollabiert gemeldet."""
    text = "### W16-W19: WIDERLEGT durch Z1\n- W16: a\n- W17: b\n- W18: c\n- W19: d\n"
    rc = ta.detect_range_collapses(text, {"W16"})
    assert len(rc) == 1
    assert rc[0]["start_id"] == "W16" and rc[0]["end_id"] == "W19"
    assert rc[0]["implied_count"] == 4
    assert rc[0]["collapsed_ids"] == ["W17", "W18", "W19"]


def test_detect_range_collapse_endash_preserves_padding():
    """En-Dash (–) + Null-Padding: ## W01–W07 -> implizierte Ids W01..W07 (gepaddet)."""
    text = "## W01–W07 — Sektion\n**W01** x\n**W02** y\n"
    rc = ta.detect_range_collapses(text, {"W01"})
    assert rc[0]["collapsed_ids"] == ["W02", "W03", "W04", "W05", "W06", "W07"]


def test_detect_no_collapse_for_single_heading():
    """Normales Einzel-Heading ### W01 ist KEINE Range -> kein Kollaps."""
    assert ta.detect_range_collapses("### W01\nEins.\n", {"W01"}) == []


def test_detect_no_false_positive_when_subids_have_own_headings():
    """Wenn W17/W18/W19 doch eigene ### Headings haben -> KEIN Kollaps (False-Positive-Schutz)."""
    text = "### W16-W19\nx\n### W17\na\n### W18\nb\n### W19\nc\n"
    rc = ta.detect_range_collapses(text, {"W16", "W17", "W18", "W19"})
    assert rc == []


def test_detect_range_collapse_default_assumes_start_only():
    """Ohne extracted_local_ids: konservativ nur Start-Id gewonnen -> Rest kollabiert."""
    rc = ta.detect_range_collapses("### W1-W5: Gates\nW1: ..\nW2: ..\n")
    assert rc[0]["collapsed_ids"] == ["W2", "W3", "W4", "W5"]


# ── BL-391 (B) Korpus-verifizierte Nicht-Flag-Formen (Coverage-Audit 2026-06-17, OmniCommand) ──
# Der Audit ueber den GESAMTEN OmniCommand-Korpus (Vault + .claude/models) fand GENAU zwei
# Dash-Heading-Formen, die KEINE Range sind und korrekt NICHT geflaggt werden duerfen. Beide
# real belegt. Pinnt sie, damit ein spaeteres Verbreitern der Range-Regex (z.B. fuer AK1-AK5)
# sie nicht still in False-Positives kippt — die unabhaengige Signal-Disziplin auch hier.

def test_detect_no_false_positive_for_title_separator_emdash():
    """Real-Korpus (BL-064 '### W16 — T5 Audit-Event ...'): Titel-Trenner-Em-Dash vor einem
    NICHT-W-Token. Die Range-Regex verlangt W\\d+ auf BEIDEN Seiten -> kein Kollaps."""
    text = "### W16 — T5 Audit-Event Schema-Migration\nEin einzelner Knoten.\n"
    assert ta.detect_range_collapses(text, {"W16"}) == []


def test_detect_no_false_positive_for_namespace_suffix_ids():
    """Real-Korpus (BL-113a/b '### W1-BL113a: ...'): Einzel-Knoten mit Namespace-Suffix
    (W-Zahl-Dash-NICHT-W). Rechte Dash-Seite ist kein W\\d+ -> KEINE Range, kein Kollaps."""
    text = "### W1-BL113a: Hierarchie-Struktur\nx\n### W2-BL113a: SHA256 deterministisch\ny\n"
    extracted = {k["local_id"] for k in ta.parse_model_headings(text)}
    assert ta.detect_range_collapses(text, extracted) == []


# ── BL-391 (A): Range-Heading-Member-Atomisierung (Gruppen-Knoten + Kind-Wahrheiten) ──
# 3 reale Body-Formate aus dem Korpus: BL-050 Dash-Bullet, PrePR bare+Continuation, BL-111 Bold-Marker.

_RANGE_DASH = """### W16-W19: WIDERLEGT durch Z1

- W16: ~~SC-Pipeline hat keine Vault-Pfade.~~ [Typ: FESTSTELLUNG, Status: WIDERLEGT]
- W17: ~~modelMaintain ist inkonsistent.~~ [Typ: FESTSTELLUNG, Status: WIDERLEGT]
- W18: ~~K_score widerspricht dem Vertrag.~~ [Typ: FESTSTELLUNG, Status: WIDERLEGT]
- W19: ~~Guard prueft nur .claude Pfade.~~ [Typ: FESTSTELLUNG, Status: WIDERLEGT]
"""


def test_range_member_atomization_dash_bullet():
    """BL-050-Form: Gruppen-Knoten W16 (view-bearing) + Kinder W17/W18/W19 (derived enrichment)."""
    by = {t["local_id"]: t for t in ta.atomize(_RANGE_DASH, "BL-050")}
    assert set(by) == {"W16", "W17", "W18", "W19"}
    assert "derived_from" not in by["W16"]          # Gruppe = view-bearing
    assert by["W17"]["derived_from"] == "W16"        # Kind = enrichment, zeigt auf Gruppe
    assert "inkonsistent" in by["W17"]["text"]       # Slice traegt W17-Inhalt
    assert "K_score" not in by["W17"]["text"]        # sauber von W18 getrennt


def test_range_member_atomization_clears_b_gate():
    """(A) + (B) greifen ineinander: sobald Kinder extrahiert sind, flaggt detect_range_collapses NICHT mehr."""
    truths = ta.atomize(_RANGE_DASH, "BL-050")
    extracted = {t["local_id"] for t in truths}
    assert ta.detect_range_collapses(_RANGE_DASH, extracted) == []


def test_range_member_roundtrip_holds():
    """Kern-Sicherheit: Kinder sind NICHT view-bearing → parse(View)==parse(Original) byte-identisch."""
    truths = ta.atomize(_RANGE_DASH, "BL-050")
    assert ta.roundtrip_ok(_RANGE_DASH, truths) is True


def test_range_member_all_schema_valid():
    for t in ta.atomize(_RANGE_DASH, "BL-050"):
        assert [m for s, m in ts.validate_truth(t) if s == "ERROR"] == [], f"{t['local_id']}"


def test_range_member_ids_unique_inv_mig_10():
    ids = [t["id"] for t in ta.atomize(_RANGE_DASH, "BL-050")]
    assert len(ids) == len(set(ids))


_RANGE_BARE = """### W1-W3: Wie es funktioniert

W1: BESTAETIGT — erster Modus.
  Quelle: foo.md Schritt 3

W2: BESTAETIGT — zweiter Punkt.
  Quelle: bar.md Phase 2

W3: OFFEN — dritter Punkt.
  Quelle: baz.md
"""


def test_range_member_bare_with_continuation():
    """PrePR-Form: bare 'Wn:' + eingerueckte 'Quelle:'-Continuation gehoert zum Member.
    W1 = Start = Gruppe (voller Verbatim-Body); die saubere Slice-Trennung pruefen wir am Kind W2."""
    by = {t["local_id"]: t for t in ta.atomize(_RANGE_BARE, "PrePR")}
    assert set(by) == {"W1", "W2", "W3"}
    assert by["W2"]["derived_from"] == "W1"
    assert "zweiter Punkt" in by["W2"]["text"]         # W2-Slice
    assert "Quelle: bar.md" in by["W2"]["text"]        # eingerueckte Continuation an W2 gebunden
    assert "erster Modus" not in by["W2"]["text"]      # sauber von W1 getrennt


_RANGE_BOLD = """## W01–W03 — Topologie

**W01**
Erste Aussage zur Topologie.
Typ: ENTSCHEIDUNG
Quelle: E01/W1

**W02**
Zweite Aussage hier.
Typ: ARCHITEKTUR

**W03**
Dritte Aussage.
"""


def test_range_member_bold_marker_endash_padding():
    """BL-111-Form: '**W01**'-Marker + En-Dash-Range + Null-Padding (W01..W03) erhalten."""
    truths = ta.atomize(_RANGE_BOLD, "BL-111")
    by = {t["local_id"]: t for t in truths}
    assert set(by) == {"W01", "W02", "W03"}            # Padding erhalten
    assert by["W02"]["derived_from"] == "W01"
    assert "Zweite Aussage" in by["W02"]["text"]
    assert ta.roundtrip_ok(_RANGE_BOLD, truths) is True


def test_non_range_model_unaffected_by_member_atomization():
    """Regression: ein Model ohne Range bekommt KEINE derived children (genau die alten Knoten)."""
    truths = ta.atomize(_MODEL, "BL-x")
    assert all("derived_from" not in t for t in truths)
    assert len(truths) == 3


# ── BL-395 (b): Byte-Coverage — View muss den Quell-Body rekonstruieren (parse-Roundtrip ist dafuer blind) ──

def test_b2_recovers_bullet_model_segment_path(tmp_path):
    """B2: ein reines Bullet-Model (0 ## W-Headings) wird jetzt via SEGMENT-Pfad atomisiert (RECOVERED),
    nicht mehr quarantaeniert. View == Source byte-identisch -> coverage hoch, knots>0, ready."""
    p = tmp_path / "K_Model.md"
    p.write_text("# Konsolidiert\n\n- W1: erste Wahrheit ausfuehrlich beschrieben\n- W2: zweite ebenso\n- W3: dritte\n", encoding="utf-8")
    res = ta.atomize_model_file(p, "K")
    assert res["knots"] == 3                  # 3 Bullet-Definitionen atomisiert
    assert res["roundtrip_ok"] is True        # View == Source byte-identisch (Partition)
    assert res["low_coverage"] is False       # View deckt den Quell-Body -> kein Verlust
    assert res["format_hint"] == "SEGMENT-B2"


def test_b2_safety_holds_for_no_wdef_prose(tmp_path):
    """Safety bleibt: ein Model OHNE W-Definitionen (pure Prosa) -> keine Truths -> low_coverage (quarantaeniert)."""
    p = tmp_path / "P_Model.md"
    p.write_text("# Titel\n\nNur Fliesstext ohne irgendeinen W-Knoten. Zweiter Absatz hier.\n", encoding="utf-8")
    res = ta.atomize_model_file(p, "P")
    assert res["knots"] == 0
    assert res["low_coverage"] is True        # kein W-Inhalt rekonstruierbar -> Gate blockt


def test_atomize_segments_byte_identical_view():
    """B2-KERN-Invariante: build_segment_view == Original byte-identisch (Partition, kein Byte verloren)."""
    text = "# Titel\nPreamble-Prosa.\n\n- W1: erste\n- W2: zweite\n## W3 — Heading-Mix\nKoerper von W3.\n"
    truths = ta.atomize_segments(text, "BL-x")
    assert ta.build_segment_view(truths) == text          # exakte Rekonstruktion
    assert [t["local_id"] for t in truths] == ["W1", "W2", "W3"]


def test_atomize_segments_table_and_bold_formats():
    """Tabellen-Zelle (| W7 |) + Bold-Marker (**W01**) werden als W-Defs segmentiert (Multi-Format)."""
    text = "| W7 | etwas |\n| W8 | anderes |\n**W01** Bold-Aussage\n"
    truths = {t["local_id"]: t for t in ta.atomize_segments(text, "BL-x")}
    assert set(truths) == {"W7", "W8", "W01"}
    assert "etwas" in truths["W7"]["text"]


def test_atomize_segments_schema_valid():
    text = "# K\n\n- W1: erste ausfuehrliche Wahrheit\n- W2: zweite ausfuehrliche\n"
    for t in ta.atomize_segments(text, "BL-x"):
        assert [m for s, m in ts.validate_truth(t) if s == "ERROR"] == [], t["local_id"]


def test_atomize_segments_preamble_incl_frontmatter_in_first_verbatim():
    """Praeambel inkl. Frontmatter steckt im _verbatim des 1. Segments -> concat == Source byte-identisch."""
    text = "---\nid: x\n---\n# Titel\nVorspann.\n\n- W1: a\n- W2: b\n"
    truths = ta.atomize_segments(text, "BL-x")
    assert truths[0]["_verbatim"].startswith("---\nid: x")
    assert ta.build_segment_view(truths) == text


def test_byte_coverage_high_for_clean_heading_model_bl395(tmp_path):
    """Sauberes HEADING-Model -> View rekonstruiert den Body -> low_coverage False (kein Over-Flag)."""
    p = tmp_path / "H_Model.md"
    p.write_text("### W01\nErste Aussage hier ausfuehrlich.\n\n### W02\nZweite Aussage hier ausfuehrlich.\n", encoding="utf-8")
    res = ta.atomize_model_file(p, "H")
    assert res["coverage"] >= 0.5
    assert res["low_coverage"] is False


# ── BL-384 Cutover-Wiring: _verbatim persistieren -> View aus den GESCHRIEBENEN Truths rebuildbar ──

def test_segment_truth_file_persists_verbatim_as_body(tmp_path):
    """SEGMENT-Truth-Datei traegt das exakte _verbatim als Body (truth_to_md) -> read_truth_file holt es zurueck."""
    truths = ta.atomize_segments("- W1: erste\n- W2: zweite\n", "BL-x")
    out = tmp_path / "truths"
    ta.write_truths(truths, out)
    back = ta.read_truth_file(out / "W2.md")
    assert back["view_mode"] == "verbatim"
    assert back["_verbatim"] == truths[1]["_verbatim"]     # byte-exakt zurueckgelesen


def test_segment_model_view_rebuildable_from_disk_byte_identical(tmp_path):
    """KERN (BL-384): SEGMENT-Model -> write_truths -> rebuild_view_from_truths_dir == Quelle BYTE-identisch.
    Glob-Reihenfolge ist alphabetisch; seq stellt die Dokument-Reihenfolge wieder her."""
    text = "---\nid: x\n---\n# K\nPraeambel.\n\n- W2: zweite zuerst im Doc\n- W1: danach\n- W10: und zehn\n"
    truths = ta.atomize_segments(text, "BL-x")
    out = tmp_path / "truths"
    ta.write_truths(truths, out)
    assert ta.rebuild_view_from_truths_dir(out) == text   # byte-identisch trotz alphabetischem Glob (W1/W10/W2)


def test_heading_model_view_rebuildable_from_disk(tmp_path):
    """HEADING-Model: rebuild_view_from_truths_dir == build_model_view (parse-aequivalent zum Original)."""
    truths = ta.atomize(_MODEL, "BL-x")
    out = tmp_path / "truths"
    ta.write_truths(truths, out)
    rebuilt = ta.rebuild_view_from_truths_dir(out)
    assert rebuilt == ta.build_model_view(truths)         # disk-rebuild == in-memory View
    # die disk-rebuilt View parst feldweise identisch zum Original (Roundtrip-Beweis ueber Disk)
    assert ta._knot_key(ta.parse_model_headings(rebuilt)) == ta._knot_key(ta.parse_model_headings(_MODEL))


def test_heading_truth_file_body_unchanged_regression(tmp_path):
    """Regression: HEADING-Truth-Datei behaelt original_heading als Body (kein _verbatim-Pfad)."""
    truths = ta.atomize(_MODEL, "BL-x")
    out = tmp_path / "truths"
    ta.write_truths(truths, out)
    content = (out / "W01.md").read_text(encoding="utf-8")
    assert content.rstrip("\n").endswith("### W01")       # Body = Heading-Zeile (unveraendert)
    assert "view_mode:" not in content                    # HEADING-Truth traegt KEIN view_mode
