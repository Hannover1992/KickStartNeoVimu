"""Tests fuer truth_wid.py (BL-395 c: EINE kanonische W-ID-Lexikon-Quelle). Lead-verify aus Repo-Root."""
import truth_wid as tw


def test_wid_token_matches_underscore_suffix_ids():
    """Der Kern-Fix (Audit-Vektor 3): W*_REF (mit '_') wird jetzt als Referenz erkannt — war vorher unsichtbar
    (das `\\b` nach 'W7' griff bei 'W7_REF' nicht), darum gingen alle Cross-BL-Ref-Kanten verloren."""
    assert tw.WID_TOKEN.findall("siehe W7_REF und W10_REF in der Tabelle") == ["W7_REF", "W10_REF"]


def test_wid_token_matches_legacy_forms():
    assert set(tw.WID_TOKEN.findall("W01 W7 W12a W-IST-1 W-AK-A")) == {"W01", "W7", "W12a", "W-IST-1", "W-AK-A"}


def test_wid_token_excludes_german_w_words_and_w_knoten():
    """Digit-First-Regel bleibt: deutsche W-Woerter + Section-Ueberschrift W-Knoten matchen NICHT (kein Over-Match)."""
    assert tw.WID_TOKEN.findall("Warum Workflow Wellen Worker und die ## W-Knoten Sektion") == []


def test_backref_find_wrefs_now_sees_underscore_ref():
    """Integration: der Inverse-Index (referenced_by) sieht jetzt eine W7_REF-Referenz (vorher set())."""
    import truth_backref_index as bi
    assert "W7_REF" in bi.find_wrefs("AK-16 wird von W7_REF getragen")


# ── B2-Audit Gap-Fixes: kombinierte Praefixe (Gap-A) + dashed-digit (Gap-B) + Mermaid-Over-Seg-Guard ──

def test_wdef_line_combined_prefix_bullet_bold():
    """Gap-A: '- **W1:**' (Bullet+Bold) + '| **W7** |' (Tabelle+Bold) sind W-Definitionen (kombinierte Marker)."""
    assert tw.WDEF_LINE.match("- **W1:** erste Wahrheit").group(1) == "W1"
    assert tw.WDEF_LINE.match("| **W7** | Aussage |").group(1) == "W7"


def test_wdef_line_dashed_digit_heading():
    """Gap-B: '### W-01:' (Ziffer nach Bindestrich, BL-215) ist eine W-Definition."""
    assert tw.WDEF_LINE.match("### W-01: Aussage").group(1) == "W-01"
    assert tw.WID_TOKEN.findall("siehe W-01 und W-07") == ["W-01", "W-07"]


def test_wdef_line_excludes_mermaid_edges():
    """Over-Seg-Guard: ein Zeilenanfang-W-Id direkt vor einem Pfeil (Mermaid/Sequenz-Kante) ist KEINE Definition."""
    assert tw.WDEF_LINE.match("W1 --> W2") is None
    assert tw.WDEF_LINE.match("W220 --> SDF") is None
    assert tw.WDEF_LINE.match("    W1-->>TL: msg") is None
    assert tw.WDEF_LINE.match("- W1: echte Definition").group(1) == "W1"   # ':' statt Pfeil -> echte Def


def test_wid_token_still_matches_mermaid_targets():
    """Referenzen: in 'W1 --> W2' sind BEIDE echte Ref-Ziele -> WID_TOKEN matcht weiter (kein Guard auf Refs)."""
    assert tw.WID_TOKEN.findall("W1 --> W2") == ["W1", "W2"]


def test_wdef_line_clean_forms_regression():
    """Regression: bekannte Formen matchen weiter; W-Knoten bleibt ausgeschlossen."""
    assert tw.WDEF_LINE.match("### W01 — Titel").group(1) == "W01"   # em-dash != ascii-Pfeil
    assert tw.WDEF_LINE.match("- W16: bullet").group(1) == "W16"
    assert tw.WDEF_LINE.match("**W01** bold").group(1) == "W01"
    assert tw.WDEF_LINE.match("W1: bare").group(1) == "W1"
    assert tw.WDEF_LINE.match("## W-Knoten") is None


def test_lexicon_unified_across_layers():
    """Alle Referenz-Schichten teilen jetzt DIESELBE Quelle -> kein Drift mehr (BL-395 c)."""
    import truth_atomizer as ta
    import truth_backref_index as bi
    import truth_resolver as tr
    import truth_census as tc
    probe = "W7_REF W01 W-IST-1"
    expected = set(tw.WID_TOKEN.findall(probe))
    assert set(ta._WREF_IN_TEXT.findall(probe)) == expected
    assert set(bi._WREF.findall(probe)) == expected
    assert set(tr._WID_TOKEN.findall(probe)) == expected
    assert set(tc._WID_TOKEN.findall(probe)) == expected
