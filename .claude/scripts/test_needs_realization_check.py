"""
test_needs_realization_check.py — BL-383 batch_PL5 (AK-3): Pattern-Realization-Check.

HEUTE inkrementiert Pattern-Konsum nur `usage++` (Treffer-Zaehlung, F4). NACH BL-383
traegt jeder PatternLibrary-Treffer ein `needs_realization_check=true`-Flag, bis ein
AKTIVER Realization-Verify ihn auf `realized=true|false` aufloest. Ein Treffer mit
offenem Flag zaehlt NICHT als architektonischer Pluspunkt (Kern-Anti-These, F6/F7).

Der aktive Verify prueft ZWEI Achsen (W-PRC-2):
  (a) Suitability        — passt das Pattern fuer den Kontext? (Kazman-Urteil, ROTE Zone)
  (b) Instanziierungs-Ort — ist es an der korrekten `_project/{LAYER}`-Schicht-Grenze
                            instanziiert? (code-naeher, deterministisch pruefbar)
Beide gruen -> `realized=true`; sonst -> Realization-Risiko-Befund (risk_class=Realization,
eval_kind=pattern_realization, AK-4).

Selbst-Konsistenz (W-PRC-3 / W-INV-3, AK-8): der Suitability-URTEIL selbst ist eine ROTE/
agentische Zone (INV-VEHIKEL-2) — hier nur die FLAG-MECHANIK + der deterministische
Instanziierungs-Ort-Schicht-Check (code-coverable). Anti-false-GREEN auf Arch-Ebene.

Scope batch_PL5 (AK-3): die FLAG-Mechanik (`needs_realization_check`-Setzen, "offener
Treffer != Pluspunkt", `realized`-Aufloesung aus 2 Achsen) + der Instanziierungs-Ort-
Schicht-Grenz-Check. Der Suitability-Verify (passt das Pattern?) ist markdown_uncoverable
(ROTE Zone, agentisch) — hier nur testbar, DASS er als Achse eingeht (suitability=fail ->
kein realized). KEIN modus-Write (INV-MODUS-1), kein neuer Truth-Node-Typ (W-DOM-1).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import quality_model_wform as qmw  # noqa: E402
import needs_realization_check as nrc  # noqa: E402

SCRIPT_DIR = Path(__file__).parent.absolute()

# Die kanonischen PatternLibrary-Layer (aus Libraries/PatternLibrary/_index.md).
KNOWN_LAYERS = ("BERATER", "COMMANDS", "ORCHESTRATOR", "SCRIPTS", "META", "HOOKS")


# ═══════════════════════════════════════════════════════════════════════════
# AK-3 — Flag-Mechanik: Treffer -> needs_realization_check=true (KEINE Auto-Gutschrift)
# ═══════════════════════════════════════════════════════════════════════════

def test_new_hit_sets_needs_realization_check_true():
    """AK-3 (T-9): ein frischer PatternLibrary-Treffer (usage++) traegt
    `needs_realization_check=true` und `realized=null` (offen) — KEINE Auto-Gutschrift."""
    hit = nrc.new_pattern_hit("PT-META-001", usage=5)
    assert hit["needs_realization_check"] is True
    assert hit["realized"] is None
    assert hit["pattern_id"] == "PT-META-001"
    # usage-Telemetrie bleibt unveraendert (Flag lebt NEBEN dem Counter, W-PRC-1).
    assert hit["usage"] == 5


def test_open_hit_is_not_an_architectural_pluspunkt():
    """AK-3 (T-9, Kern-Anti-These F6/F7): ein Treffer mit offenem needs_realization_check
    zaehlt NICHT als architektonischer Pluspunkt — counts_as_credit() ist False solange
    das Flag offen ist."""
    open_hit = nrc.new_pattern_hit("PT-BRT-001", usage=1)
    assert nrc.counts_as_credit(open_hit) is False


def test_resolved_realized_hit_counts_as_pluspunkt():
    """AK-3: ein per aktivem Verify auf realized=true aufgeloester Treffer zaehlt als
    Pluspunkt (Flag geschlossen, beide Achsen gruen)."""
    hit = nrc.new_pattern_hit("PT-META-002", usage=2)
    resolved = nrc.resolve_realization(hit, suitability="pass", instantiation_site="pass")
    assert resolved["needs_realization_check"] is False
    assert resolved["realized"] is True
    assert nrc.counts_as_credit(resolved) is True


def test_realized_false_hit_does_not_count_as_pluspunkt():
    """AK-3: ein auf realized=false aufgeloester Treffer (eine Achse fail) zaehlt NICHT
    als Pluspunkt, obwohl das Flag geschlossen ist (counts_as_credit braucht realized=True)."""
    hit = nrc.new_pattern_hit("PT-ORC-001", usage=1)
    resolved = nrc.resolve_realization(hit, suitability="fail", instantiation_site="pass")
    assert resolved["realized"] is False
    assert resolved["needs_realization_check"] is False
    assert nrc.counts_as_credit(resolved) is False


# ═══════════════════════════════════════════════════════════════════════════
# AK-3 — 2-Achsen-Aufloesung (W-PRC-2): Suitability + Instanziierungs-Ort
# ═══════════════════════════════════════════════════════════════════════════

def test_both_axes_pass_yields_realized_true():
    """AK-3 (W-PRC-2): beide Achsen gruen -> realized=true."""
    hit = nrc.new_pattern_hit("PT-META-003", usage=1)
    resolved = nrc.resolve_realization(hit, suitability="pass", instantiation_site="pass")
    assert resolved["realized"] is True
    assert resolved["realization_axes"]["suitability"] == "pass"
    assert resolved["realization_axes"]["instantiation_site"] == "pass"


def test_suitability_fail_yields_realized_false():
    """AK-3 (W-PRC-2 Achse a): Suitability fail (Pattern passt nicht) -> realized=false,
    egal ob am richtigen Ort instanziiert."""
    hit = nrc.new_pattern_hit("PT-META-004", usage=1)
    resolved = nrc.resolve_realization(hit, suitability="fail", instantiation_site="pass")
    assert resolved["realized"] is False


def test_instantiation_site_fail_yields_realized_false():
    """AK-3 (W-PRC-2 Achse b): Instanziierungs-Ort fail (falsche Schicht) -> realized=false,
    egal ob das Pattern grundsaetzlich passt."""
    hit = nrc.new_pattern_hit("PT-META-005", usage=1)
    resolved = nrc.resolve_realization(hit, suitability="pass", instantiation_site="fail")
    assert resolved["realized"] is False


def test_unresolved_axis_keeps_flag_open():
    """AK-3: solange eine Achse null/offen ist, bleibt needs_realization_check=true offen
    (KEINE vorzeitige Auto-Gutschrift)."""
    hit = nrc.new_pattern_hit("PT-HK-001", usage=1)
    partial = nrc.resolve_realization(hit, suitability="pass", instantiation_site=None)
    assert partial["needs_realization_check"] is True
    assert partial["realized"] is None
    assert nrc.counts_as_credit(partial) is False


# ═══════════════════════════════════════════════════════════════════════════
# AK-3 — Instanziierungs-Ort-Schicht-Check (`_project/{LAYER}`-Grenze, code-naeher)
# ═══════════════════════════════════════════════════════════════════════════

def test_instantiation_site_matches_expected_layer():
    """AK-3 (T-10, Achse b deterministisch): ein Pattern, das an seiner erwarteten
    `_project/{LAYER}`-Schicht instanziiert ist, -> instantiation_site=pass."""
    # PT-META-001 ist ein META-Layer-Pattern; instanziiert in einer META-Schicht-Datei.
    assert nrc.check_instantiation_site(
        pattern_layer="META",
        instantiation_path="Libraries/PatternLibrary/_project/META/PT-META-001.md",
    ) == "pass"


def test_instantiation_site_wrong_layer_is_fail():
    """AK-3 (T-10): ein Pattern an der FALSCHEN `_project/{LAYER}`-Grenze instanziiert
    -> instantiation_site=fail (Realization-Risiko, der code-nahe Teil von W-PRC-2)."""
    # META-Pattern, aber in der HOOKS-Schicht instanziiert -> Grenz-Verletzung.
    assert nrc.check_instantiation_site(
        pattern_layer="META",
        instantiation_path="Libraries/PatternLibrary/_project/HOOKS/x.md",
    ) == "fail"


def test_instantiation_site_unknown_path_is_null():
    """AK-3: kann der Instanziierungs-Ort nicht bestimmt werden (kein _project/{LAYER}-Pfad)
    -> null (nicht entscheidbar; faellt auf den Urteils-Pfad, KEIN false-fail)."""
    assert nrc.check_instantiation_site(
        pattern_layer="META", instantiation_path="some/random/file.py",
    ) is None
    assert nrc.check_instantiation_site(pattern_layer="META", instantiation_path=None) is None


# ═══════════════════════════════════════════════════════════════════════════
# AK-3 — Realization-Risiko-Befund = valider pattern_realization eval_finding (PL1-Interop)
# ═══════════════════════════════════════════════════════════════════════════

def test_unrealized_hit_yields_realization_finding():
    """AK-3 (W-OUT-1): ein Treffer der NICHT realisiert ist (eine Achse fail) -> ein
    eval_finding mit risk_class=Realization, eval_kind=pattern_realization, ref_node=pattern-id."""
    hit = nrc.new_pattern_hit("PT-META-001", usage=3)
    resolved = nrc.resolve_realization(hit, suitability="pass", instantiation_site="fail")
    findings = nrc.realization_findings([resolved], bl_slug="BL-383")
    assert len(findings) == 1
    f = findings[0]
    assert f["risk_class"] == "Realization"
    assert f["eval_kind"] == "pattern_realization"
    assert f["ref_node"] == "PT-META-001"
    assert f["cost"] and f["benefit"]


def test_realized_hit_yields_no_finding():
    """AK-3: ein voll realisierter Treffer (beide Achsen gruen) -> KEIN Risiko-Befund."""
    hit = nrc.new_pattern_hit("PT-META-002", usage=1)
    resolved = nrc.resolve_realization(hit, suitability="pass", instantiation_site="pass")
    assert nrc.realization_findings([resolved], bl_slug="BL-383") == []


def test_open_hit_yields_managerial_or_realization_finding():
    """AK-3 (Anti-false-GREEN): ein Treffer mit OFFENEM Flag (kein Verify gelaufen) ist
    NICHT durchgewunken — er erzeugt einen Befund (offener Realization-Check = ungeklaertes
    Risiko), zaehlt also nie still als Pluspunkt."""
    open_hit = nrc.new_pattern_hit("PT-BRT-002", usage=1)
    findings = nrc.realization_findings([open_hit], bl_slug="BL-383")
    assert len(findings) == 1
    assert findings[0]["eval_kind"] == "pattern_realization"


def test_findings_are_valid_eval_finding_records():
    """AK-3 x AK-4-Interop: jeder Realization-Befund ist ein PL1-schema-valider
    eval_finding-Record (als W-Block gerendert -> gold gegen den PL1-Validator)."""
    hits = [
        nrc.resolve_realization(nrc.new_pattern_hit("PT-META-001", 1),
                                suitability="fail", instantiation_site="pass"),
        nrc.new_pattern_hit("PT-HK-001", 2),  # offen
    ]
    findings = nrc.realization_findings(hits, bl_slug="BL-383")
    assert findings
    md = nrc.render_findings_as_w_blocks(findings)
    res = qmw.validate_model(md)
    assert res["total"] == len(findings)
    assert res["gold_count"] == len(findings), res["violations"]


# ═══════════════════════════════════════════════════════════════════════════
# AK-3 x INV-MODUS-1/5 — kein Modus-/Verbots-Feld in Hit ODER Befund
# ═══════════════════════════════════════════════════════════════════════════

def test_no_modus_field_in_hit_or_finding():
    """AK-3 x INV-MODUS-1/5: weder das pattern_hit-Flag-Objekt noch der Realization-Befund
    tragen je eines der Verbotsfelder (das Gate ist Bewerter, KEIN Modus-Setzer, AK-9)."""
    forbidden = {"recommended_modus", "sdf_mode", "sdf_mode_hint",
                 "expected_sdf_mode", "mode_recommendation", "modus"}
    hit = nrc.new_pattern_hit("PT-META-001", usage=1)
    resolved = nrc.resolve_realization(hit, suitability="fail", instantiation_site="pass")
    assert not (set(resolved.keys()) & forbidden), resolved
    for f in nrc.realization_findings([resolved], bl_slug="BL-383"):
        assert not (set(f.keys()) & forbidden), f


# ═══════════════════════════════════════════════════════════════════════════
# AK-3 — CLI-Smoke
# ═══════════════════════════════════════════════════════════════════════════

def test_cli_runs_on_index_file(tmp_path):
    """AK-3: CLI-Smoke — needs_realization_check.py <PatternLibrary/_index.md> laeuft
    read-only, listet die Pattern-Treffer mit Flag-Status, exit 0."""
    idx = tmp_path / "_index.md"
    idx.write_text(
        "# PatternLibrary\n\n| PT | Beschreibung |\n|----|----|\n"
        "| PT-META-001 | x |\n| PT-BRT-001 | y |\n",
        encoding="utf-8",
    )
    assert nrc.main([str(idx)]) == 0
    assert nrc.main([]) == 2  # Usage
