"""
test_design_eval.py — BL-383 batch_PL2 (AK-1): Design-Eval Plan-Zeit-Logik.

Design-Eval ist der erste maschinelle Bewertungs-Konsument der BL-380
`quality_scenario`-Nodes (SOLL). Pro Top-Szenario:
  SOLL (`response_measure{metric, threshold, method}`) -> IST (Entwurf) -> vergleichen.

Der Eval-MODUS folgt STRUKTURELL aus `response_measure.endpoint_type` (BL-380 W-RM-1,
KEINE BL-383-Wahl, KEIN DF_BATCH_STATE.modus):
  - `metric_component` -> DETERMINISTISCHER Vergleich (testbar, das Build-Artefakt)
  - `ak_test`          -> AK-Test-Bezug (RED/GREEN-Loop, der Befund nennt den AK)
  - rein-qualitativ / reine Laufzeit-Metrik -> LAUFZEIT/Urteils-Pfad (NICHT build-test,
    dokumentiert; Graceful Degradation, kein Hard-Fail)

Output = eval_finding-Records (PL1-Schema, design_eval-eval_kind). read-only Konsum
(W-DOM = reiner Konsument, KEIN neuer Truth-Node-Typ, KEIN Producer-Write, kein Modus).

Scope batch_PL2: die DETERMINISTISCHE Design-Eval-Logik (Szenario-Lesen, endpoint_type-
Routing, metric_component-SOLL/IST-Vergleich, Existenz-/Abdeckungs-Befund, Graceful
Degradation). Der rein-qualitative LLM-Urteils-Pfad selbst ist markdown_uncoverable
(agentisch, ROTE Zone) — hier nur ROUTING dorthin (Befund-Markierung) testbar.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import quality_model_wform as qmw  # noqa: E402
import design_eval as de  # noqa: E402

SCRIPT_DIR = Path(__file__).parent.absolute()


# ───────────────────────── Szenario-Fixtures (BL-380-Schema) ─────────────────────────

# metric_component-Szenario: deterministisch pruefbar (zeigt auf K-Score/SRS-Komponente).
SCENARIO_METRIC_COMPONENT = (
    "### W-QS-1 · Niedriger Instabilitaets-Index\n"
    "- **text:** Kopplung bleibt unter Schwelle.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Spec: BL-380_Spec.md Sec 3`\n"
    "- **Quelle:** `[[3_Spec/BL-380_Spec.md#3]]`\n"
    "- **Edge zu:** W-RM-4\n"
    "- **type:** quality_scenario\n"
    "- **id:** `BL-380.QS-1`\n"
    "- **scenario:**\n"
    "    - source: Entwickler\n"
    "    - stimulus: Einbindung eines neuen Moduls\n"
    "    - artifact: Utility-Modul\n"
    "    - environment: Entwicklung (CI-Build)\n"
    "    - response: Kopplung bleibt unter Schwelle\n"
    "    - response_measure:\n"
    "        - metric: Instabilitaets-Index I = Ce / (Ca + Ce)\n"
    "        - threshold: I < 0.4\n"
    "        - method: K-Score-Lauf (Ca/Ce-Analyse) nach Code-Aenderung\n"
    "- **endpoint_type:** metric_component\n"
    "- **endpoint_ref:** `ak_details[AK_1].k_score_pro_ak`\n"
    "- **qualitaetsziel_ref:** `[[arc42/01_einfuehrung.md#Wartbarkeit]]`\n"
)

# ak_test-Szenario: per bestehbarem Test pruefbar (zeigt auf konkreten AK).
SCENARIO_AK_TEST = (
    "### W-QS-2 · Antwortzeit unter Last\n"
    "- **text:** p90-Latenz unter 200ms unter Last.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Spec: BL-380_Spec.md Sec 3`\n"
    "- **Quelle:** `[[3_Spec/BL-380_Spec.md#3]]`\n"
    "- **Edge zu:** W-RM-3\n"
    "- **type:** quality_scenario\n"
    "- **id:** `BL-380.QS-2`\n"
    "- **scenario:**\n"
    "    - source: Nutzer (HTTP-Client)\n"
    "    - stimulus: 1000 parallele Anfragen\n"
    "    - artifact: API-Gateway\n"
    "    - environment: Last (1000 konk. Nutzer)\n"
    "    - response: System liefert valide Antwort\n"
    "    - response_measure:\n"
    "        - metric: p90-Latenz in ms\n"
    "        - threshold: p90 < 200ms\n"
    "        - method: Lasttest via k6 ueber 10min-Fenster\n"
    "- **endpoint_type:** ak_test\n"
    "- **endpoint_ref:** `AK-12`\n"
    "- **qualitaetsziel_ref:** `[[arc42/01_einfuehrung.md#Leistungseffizienz]]`\n"
)

# Plain-W + ADR (kein Szenario) — Design-Eval ignoriert sie.
PLAIN_AND_ADR = (
    "### W-DOM-2 · Plain\n"
    "- **text:** Eine normale Wahrheit.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Repo:x.py:1`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-DOM-1\n"
    "### W-ADR-1 · Eine Entscheidung\n"
    "- **text:** Wir nutzen X.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Repo:y.py:2`\n"
    "- **Quelle:** `[[c.md#d]]`\n"
    "- **Edge zu:** W-DOM-1\n"
    "- **type:** adr\n"
    "- **id:** `BL-382.ADR-1`\n"
    "- **adr:**\n"
    "    - entscheidung: Nutze X\n"
    "    - problem_kontext: Y\n"
    "    - alternativen: [Z]\n"
    "    - begruendung: weil X besser\n"
    "    - konsequenzen: mehr X\n"
    "    - status: akzeptiert\n"
)


# ───────────────────────── Szenario-Konsum (read-only) ─────────────────────────

def test_load_quality_scenarios_reads_per_id():
    """AK-1: Design-Eval liest quality_scenario-Nodes per ID (read-only Konsum)."""
    scenarios = de.load_quality_scenarios(SCENARIO_METRIC_COMPONENT + SCENARIO_AK_TEST)
    ids = {s["id"] for s in scenarios}
    assert ids == {"BL-380.QS-1", "BL-380.QS-2"}
    qs1 = next(s for s in scenarios if s["id"] == "BL-380.QS-1")
    assert qs1["endpoint_type"] == "metric_component"
    assert qs1["metric"] and qs1["threshold"]


def test_load_quality_scenarios_ignores_non_scenarios():
    """AK-1: plain-W- und adr-Knoten sind KEINE quality_scenario -> nicht geladen."""
    scenarios = de.load_quality_scenarios(PLAIN_AND_ADR)
    assert scenarios == []


# ───────────────────────── endpoint_type-Routing (W-RM-1) ─────────────────────────

def test_route_metric_component_is_deterministic():
    """AK-1: endpoint_type=metric_component -> deterministischer Eval-Pfad."""
    assert de.route_eval_path("metric_component") == de.PATH_DETERMINISTIC


def test_route_ak_test_is_ak_test_loop():
    """AK-1: endpoint_type=ak_test -> AK-Test-Bezug-Pfad (RED/GREEN-Loop)."""
    assert de.route_eval_path("ak_test") == de.PATH_AK_TEST


def test_route_unknown_or_missing_is_qualitative_runtime():
    """AK-1: rein-qualitativ / unbekannt / fehlend -> Laufzeit/Urteils-Pfad (Graceful, kein Crash)."""
    assert de.route_eval_path(None) == de.PATH_QUALITATIVE
    assert de.route_eval_path("") == de.PATH_QUALITATIVE
    assert de.route_eval_path("stakeholder_urteil") == de.PATH_QUALITATIVE


# ───────────────────────── Existenz-/Abdeckungs-Befund (AK-1, T-5) ─────────────────────────

def test_top_scenario_without_coverage_yields_omission():
    """AK-1 (T-5): ein Top-Szenario OHNE Abdeckungs-Befund im Entwurf -> Omission-Kandidat-Befund.
    coverage_map ohne Eintrag fuer QS-1 -> design_eval-Befund risk_class=Omission, ref_node=QS-1."""
    findings = de.design_eval(
        SCENARIO_METRIC_COMPONENT,
        coverage_map={},  # nichts abgedeckt
        bl_slug="BL-383",
    )
    om = [f for f in findings if f["ref_node"] == "BL-380.QS-1"]
    assert om, findings
    assert om[0]["risk_class"] == "Omission"
    assert om[0]["eval_kind"] == "design_eval"


def test_covered_metric_component_scenario_no_omission():
    """AK-1: ein metric_component-Szenario, dessen IST die Schwelle erfuellt -> KEIN Omission-Befund."""
    findings = de.design_eval(
        SCENARIO_METRIC_COMPONENT,
        coverage_map={"BL-380.QS-1": {"ist_value": 0.30, "covered": True}},
        bl_slug="BL-383",
    )
    om = [f for f in findings if f["ref_node"] == "BL-380.QS-1" and f["risk_class"] == "Omission"]
    assert om == [], findings


# ───────────────────────── metric_component det-Vergleich (AK-1, T-6) ─────────────────────────

def test_metric_component_soll_ist_compare_pass():
    """AK-1 (T-6): metric_component -> deterministischer SOLL/IST-Vergleich; IST erfuellt
    Schwelle (I=0.30 < 0.4) -> kein Schwellen-Befund."""
    findings = de.design_eval(
        SCENARIO_METRIC_COMPONENT,
        coverage_map={"BL-380.QS-1": {"ist_value": 0.30, "covered": True}},
        bl_slug="BL-383",
    )
    # IST erfuellt -> kein Commission/Omission-Befund fuer QS-1.
    bad = [f for f in findings if f["ref_node"] == "BL-380.QS-1"
           and f["risk_class"] in ("Omission", "Commission")]
    assert bad == [], findings


def test_metric_component_soll_ist_compare_fail_yields_finding():
    """AK-1 (T-6): metric_component -> IST verletzt Schwelle (I=0.55 !< 0.4) -> Befund mit
    metric+threshold-Bezug (AK-7-Spiegel) und deterministischem Pfad."""
    findings = de.design_eval(
        SCENARIO_METRIC_COMPONENT,
        coverage_map={"BL-380.QS-1": {"ist_value": 0.55, "covered": True}},
        bl_slug="BL-383",
    )
    qs1 = [f for f in findings if f["ref_node"] == "BL-380.QS-1"]
    assert qs1, findings
    f = qs1[0]
    # Der Befund traegt den messbaren Bezug (AK-7 Messbarkeits-Klammer).
    assert f.get("metric") and f.get("threshold"), f
    assert f["eval_path"] == de.PATH_DETERMINISTIC


# ───────────────────────── ak_test-Routing (AK-1) ─────────────────────────

def test_ak_test_scenario_routes_to_ak_reference():
    """AK-1: ein ak_test-Szenario ohne Abdeckung -> Befund auf dem AK-Test-Pfad, der den
    AK (endpoint_ref) als Falsifikations-Bezug nennt (kein det-Metric-Vergleich)."""
    findings = de.design_eval(SCENARIO_AK_TEST, coverage_map={}, bl_slug="BL-383")
    qs2 = [f for f in findings if f["ref_node"] == "BL-380.QS-2"]
    assert qs2, findings
    assert qs2[0]["eval_path"] == de.PATH_AK_TEST


# ───────────────────────── Graceful Degradation (AK-1, SOA-4) ─────────────────────────

def test_no_scenarios_yields_empty_no_hard_fail():
    """AK-1 (T-19-Spiegel): keine quality_scenario-Nodes -> kein Design-Eval, leere Liste,
    KEIN Hard-Fail (Graceful Degradation)."""
    findings = de.design_eval(PLAIN_AND_ADR, coverage_map={}, bl_slug="BL-383")
    assert findings == []


def test_runtime_only_metric_degrades_gracefully():
    """AK-1 (SOA-4): ein Szenario dessen response_measure erst am laufenden System messbar
    ist (qualitativer/Laufzeit-Pfad) -> markiert als vor-Bau-nicht-anwendbar, KEIN false-Omission."""
    # Szenario ohne endpoint_type (faellt auf qualitativen/Laufzeit-Pfad).
    runtime_scenario = SCENARIO_METRIC_COMPONENT.replace(
        "- **endpoint_type:** metric_component\n", ""
    ).replace("- **id:** `BL-380.QS-1`", "- **id:** `BL-380.QS-9`").replace(
        "W-QS-1", "W-QS-9"
    )
    findings = de.design_eval(runtime_scenario, coverage_map={}, bl_slug="BL-383")
    qs9 = [f for f in findings if f["ref_node"] == "BL-380.QS-9"]
    # Entweder leer (skip) ODER ein Befund auf dem qualitativen Pfad — NIE ein hartes Omission
    # mit deterministischem Pfad (das waere ein false-Hard-Fail).
    for f in qs9:
        assert f["eval_path"] != de.PATH_DETERMINISTIC


# ───────────────────────── Output = valide eval_finding-Records (PL1-Interop) ─────────────────────────

def test_findings_are_valid_eval_finding_records():
    """AK-1 x AK-4/AK-7-Interop: jeder design_eval-Output ist ein PL1-schema-valider
    eval_finding-Record (rendert man ihn als W-Block, ist er gold gegen den PL1-Validator)."""
    findings = de.design_eval(
        SCENARIO_METRIC_COMPONENT,
        coverage_map={"BL-380.QS-1": {"ist_value": 0.55, "covered": True}},
        bl_slug="BL-383",
    )
    assert findings
    md = de.render_findings_as_w_blocks(findings)
    res = qmw.validate_model(md)
    assert res["total"] == len(findings)
    assert res["gold_count"] == len(findings), res["violations"]


def test_no_modus_field_in_output():
    """AK-1 x INV-MODUS-1/5: Design-Eval-Output traegt NIE ein Modus-/Verbots-Feld."""
    findings = de.design_eval(
        SCENARIO_METRIC_COMPONENT + SCENARIO_AK_TEST,
        coverage_map={},
        bl_slug="BL-383",
    )
    forbidden = {"recommended_modus", "sdf_mode", "sdf_mode_hint",
                 "expected_sdf_mode", "mode_recommendation", "modus"}
    for f in findings:
        assert not (set(f.keys()) & forbidden), f


def test_cli_runs_on_model_file(tmp_path):
    """AK-1: CLI-Smoke — design_eval.py <Model.md> liest Szenarien, gibt Befund-Liste,
    exit 0 (read-only, kein Crash bei fehlender coverage_map)."""
    model = tmp_path / "QS_Model.md"
    model.write_text(SCENARIO_METRIC_COMPONENT + SCENARIO_AK_TEST, encoding="utf-8")
    assert de.main([str(model)]) == 0
    # leeres/Nicht-Szenario-Model -> ebenfalls exit 0 (Graceful, keine Szenarien).
    empty = tmp_path / "Plain_Model.md"
    empty.write_text(PLAIN_AND_ADR, encoding="utf-8")
    assert de.main([str(empty)]) == 0
    assert de.main([]) == 2  # Usage
