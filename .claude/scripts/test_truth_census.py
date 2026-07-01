"""Tests fuer truth_census.py (BL-309 PHASE-1.1, read-only). Lead-verify aus Repo-Root."""
import truth_census as tc


def test_heading_only_oldest():
    t = "### W1: irgendeine Aussage\nfreitext\n### W2: noch eine\n"
    c = tc.count_wknots(t)
    assert c["headings"] == 2
    assert c["total_estimate"] == 2
    assert tc.classify_format(t) == "HEADING-only (aelteste)"


def test_text_field_format():
    t = "### W-IST-1\n**text:** Foo ist Bar\n**status:** bestaetigt\n"
    c = tc.count_wknots(t)
    assert c["field_text"] == 1
    assert tc.classify_format(t) == "TEXT-Feld (aeltere)"


def test_aussage_field_newest():
    t = "### W01\n**Aussage:** Neue Generation\n**status:** offen\n"
    c = tc.count_wknots(t)
    assert c["field_aussage"] == 1
    assert tc.classify_format(t) == "AUSSAGE-Feld (juengste)"


def test_target_atomic_truth():
    t = "---\ntype: truth\nid: BL-379-slug.W01\n---\n**text:** atomar\n"
    assert tc.classify_format(t) == "ZIEL_ATOMIC (type:truth)"
    assert tc.count_wknots(t)["truth_frontmatter"] == 1


def test_no_signal():
    t = "# Model\n## Uebersicht\nKein Wahrheits-Knoten hier.\n"
    assert tc.count_wknots(t)["total_estimate"] == 0
    assert tc.classify_format(t) == "KEIN-W-Signal"


def test_estimate_is_max_not_sum():
    # Heading + Feld zaehlen denselben Knoten -> max, nicht Summe (Anti-Doppelzaehlung).
    t = "### W01\n**text:** eins\n### W02\n**text:** zwei\n"
    c = tc.count_wknots(t)
    assert c["headings"] == 2 and c["field_text"] == 2
    assert c["total_estimate"] == 2


def test_id_lexicon_variants():
    t = "### W01\n### W-IST-1\n### W-AK-A2\n"
    rec_ids = sorted(set(tc._WID_TOKEN.findall(t)))
    assert any(x.startswith("W") for x in rec_ids)
    # GEHAERTET 2026-06-16: W-Knoten (deutsches Section-Wort) ist KEINE ID-Form — Lexikon stimmt mit Count ueberein
    assert "W-Knoten" not in tc._WID_TOKEN.findall("siehe ## W-Knoten Abschnitt unten")
    assert "W-IST-1" in tc._WID_TOKEN.findall("W-IST-1 und W01 bleiben echte IDs")


def test_candidate_filter_excludes_logs():
    from pathlib import Path
    assert tc.is_candidate(Path("Backlog/BL-1/2_Model/X_Model.md"))
    assert not tc.is_candidate(Path("Backlog/BL-1/2_Model/_modelSync_log_2026.md"))
    assert not tc.is_candidate(Path("Backlog/BL-1/2_Model/X.pre_truth.md"))


# ── BL-395: census zaehlt W-DEFINITIONEN (Zeilenanfang, format-agnostisch) -> bricht den HEADING-Lockstep ──

def test_bullet_list_wnodes_counted_bl395():
    """Bullet-Definitionen (- W1:) werden gezaehlt — der reine HEADING-Census sah hier 0 (Silent-Loss-Blindfleck)."""
    t = "# Konsolidiert\n\n- W1: erste Wahrheit\n- W2: zweite\n- W3: dritte\n"
    c = tc.count_wknots(t)
    assert c["headings"] == 0          # keine ## W-Headings
    assert c["member_defs"] == 3       # aber 3 Bullet-Definitionen
    assert c["total_estimate"] == 3    # vor BL-395 war das 0 -> complete=knots>=0=True (lockstep-blind)


def test_table_cell_wnodes_counted_bl395():
    t = "# T\n\n| ID | Aussage |\n|----|----|\n| W7 | etwas |\n| W8 | anderes |\n"
    c = tc.count_wknots(t)
    assert c["member_defs"] == 2 and c["total_estimate"] == 2


def test_yaml_wahrheits_knoten_counted_bl395():
    """yaml-Aggregat (wahrheits_knoten: im Frontmatter) — BL-203-Silent-Loss-Klasse."""
    t = "---\nwahrheits_knoten:\n  - id: W1\n    status: BESTAETIGT\n  - id: W2\n  - id: W3\n---\n## _IDF_berater\nProsa.\n"
    c = tc.count_wknots(t)
    assert c["wahr_yaml"] == 3
    assert c["total_estimate"] >= 3    # vor BL-395: 0 (wahrheits_knoten-Key nie in total_estimate summiert)


def test_prose_mentions_not_overcounted_bl395():
    """Cross-Refs/Erwaehnungen MITTEN in der Zeile sind keine Definitionen -> member_defs == headings (kein Over-Flag)."""
    t = "### W01\nDies haengt von W05 ab, siehe auch W99 in BL-165.\n### W02\nNutzt W01 und W50.\n"
    c = tc.count_wknots(t)
    assert c["headings"] == 2
    assert c["member_defs"] == 2       # W05/W99/W50 mid-line zaehlen NICHT (sind Referenzen, keine Defs)
    assert c["total_estimate"] == 2    # sauberes HEADING-Model bleibt unberuehrt


def test_w_knoten_section_heading_excluded():
    # GEHAERTET 2026-06-16: "## W-Knoten" ist die Section-UEBERSCHRIFT (leitet eine Knoten-Liste ein),
    # KEIN Knoten selbst — darf NICHT mitgezaehlt werden (war der letzte Erster-Cut-Ueberzaehler).
    t = "## W-Knoten\n### W01: echte Aussage\n### W-IST-1\n"
    c = tc.count_wknots(t)
    assert c["headings"] == 2          # nur W01 + W-IST-1, NICHT die W-Knoten-Section-Heading
    # Standalone Section-Heading = 0 Knoten
    assert tc.count_wknots("## W-Knoten\n")["headings"] == 0
    # Suffix-Varianten (Wortgrenze nach Knoten) ebenfalls ausgeschlossen
    assert tc.count_wknots("## W-Knoten-Uebersicht\n")["headings"] == 0
    # Gegenprobe: echte dashed-IDs bleiben erhalten (kein Over-Block)
    assert tc.count_wknots("### W-AK-A\n### W-GAP-2\n")["headings"] == 2
