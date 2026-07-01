"""
test_eval_finding.py — BL-383 batch_PL1 (AK-4 / AK-9): Eval-Gate Output-Form.

Das Eval-Gate (BL-383) ist ein Bewertungs-KONSUMENT der BL-380/382-Truth-Nodes,
KEIN neuer Truth-Node-Typ. Sein Output ist ein `eval_finding`-Record (Kazman-
Playbook-Issue-Form), additiv auf quality_model_wform.py (Schwester des
quality_scenario- + adr-Validators):

  - AK-4: eval_finding-Record-Validator. `risk_class` IN den GENAU 4 Kazman-Klassen
    {Omission, Commission, Realization, Managerial} (geschlossenes Enum, freie Strings
    verboten — analog BL-382 ADR_STATUS_ENUM). `cost` UND `benefit` Pflicht (nicht-leer,
    Aktionierbarkeit). `eval_kind` IN {design_eval, drift_eval, pattern_realization}.
    `ref_node` per ID-Format. **KEIN binaeres PASS/FAIL als Primaer-Output** (Risiko-
    Befund-Form erzwungen). exit 0 = gold, 1 = Violation, 2 = Usage.
  - AK-9: Pre-Write-Hook (guard_modus_writer.py) faengt INV-MODUS-5-Verbotskeys
    AUCH unter verschachteltem `eval_finding:`-Block (nicht nur Top-Level) — content-
    gated, list-form-dicht wie der ADR-Fall. Das Gate ist Bewerter, kein Modus-Setzer.

ADDITIV-Invariante: bestehende `### W{n}`-Gold-Form-, quality_scenario- und adr-
Knoten bleiben unveraendert valide — die typ-konditionale eval_finding-Pruefung
greift NUR bei `type: eval_finding`.

Hinweis Scope (batch_PL1): NUR AK-4 (Schema/Enum/cost-benefit/no-PASS-FAIL) +
AK-9 (Hook nested eval_finding). Design-Eval-Routing (AK-1), Pattern-Realization-
Flag (AK-3), Drift-betrifft_baustein (AK-2), ID-Regex (AK-6), workflow_zones (AK-8)
gehoeren NICHT zu batch_PL1.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import quality_model_wform as qmw  # noqa: E402

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_modus_writer.py"


# ───────────────────────── AK-4: Validator-Fixtures ─────────────────────────

# Vollstaendiger, valider eval_finding-Knoten (Gold-Form-Basis + eval_finding-Block).
# Kazman-Playbook-Issue-Form: risk_class IN Kazman-4 + cost/benefit nicht-leer.
# eval_kind=design_eval -> traegt die AK-7-Messbarkeits-Klammer (metric+threshold).
EVAL_FINDING_VALID = (
    "### W-EF-1 · Top-Szenario QS-2 ohne Entwurfs-Abdeckung\n"
    "- **text:** Das Top-Qualitaetsszenario QS-2 traegt keinen Abdeckungs-Befund im Entwurf.\n"
    "- **Status:** TENTATIV\n"
    "- **source:** `Repo: design_eval gate-script run`\n"
    "- **Quelle:** `[[3_Spec/BL-383_Spec.md#AK-4]]`\n"
    "- **Edge zu:** W-OUT-1\n"
    "- **type:** eval_finding\n"
    "- **id:** `BL-383.EF-1`\n"
    "- **eval_finding:**\n"
    "    - finding_id: BL-383.EF-1\n"
    "    - eval_kind: design_eval\n"
    "    - ref_node: BL-380.QS-2\n"
    "    - risk_class: Omission\n"
    "    - severity: hoch\n"
    "    - befund: Top-Szenario QS-2 vom Entwurf nicht abgedeckt\n"
    "    - cost: Entwurf um Lastpfad-Komponente erweitern (mittel)\n"
    "    - benefit: schliesst Omission-Luecke vor Bau, vermeidet Re-Architektur\n"
    "    - suggested_action: Lastpfad-Komponente in Model nachziehen\n"
    "    - status: offen\n"
    "    - metric: p90-Latenz in ms\n"          # << AK-7: design_eval-Messbarkeits-Klammer
    "    - threshold: p90 < 200ms\n"
)

# Invalider Knoten: risk_class NICHT im Kazman-4-Enum (freier String, AK-4).
EVAL_FINDING_INVALID_RISK_CLASS = (
    "### W-EF-2 · Befund mit freiem risk_class\n"
    "- **text:** Eval-Befund mit ungueltiger Risiko-Klasse.\n"
    "- **Status:** TENTATIV\n"
    "- **source:** `Repo: gate-script`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-OUT-1\n"
    "- **type:** eval_finding\n"
    "- **id:** `BL-383.EF-2`\n"
    "- **eval_finding:**\n"
    "    - finding_id: BL-383.EF-2\n"
    "    - eval_kind: drift_eval\n"
    "    - ref_node: BL-382.ADR-1\n"
    "    - risk_class: Schwerwiegend\n"   # << NICHT im 4-Enum
    "    - severity: blocker\n"
    "    - befund: Impl widerspricht ADR\n"
    "    - cost: Refactor (hoch)\n"
    "    - benefit: ADR-Konformitaet\n"
    "    - suggested_action: Impl anpassen\n"
    "    - status: offen\n"
)

# Invalider Knoten: eval_finding ohne `cost` (Pflicht-Aktionierbarkeit fehlt, AK-4).
EVAL_FINDING_MISSING_COST = (
    "### W-EF-3 · Befund ohne cost\n"
    "- **text:** Eval-Befund ohne Cost-Feld.\n"
    "- **Status:** TENTATIV\n"
    "- **source:** `Repo: gate-script`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-OUT-2\n"
    "- **type:** eval_finding\n"
    "- **id:** `BL-383.EF-3`\n"
    "- **eval_finding:**\n"
    "    - finding_id: BL-383.EF-3\n"
    "    - eval_kind: pattern_realization\n"
    "    - ref_node: factory-lock-pattern\n"
    "    - risk_class: Realization\n"
    "    - severity: mittel\n"
    "    - befund: Pattern an falscher Schicht instanziiert\n"
    "    - benefit: korrekte Schicht-Grenze\n"   # << cost fehlt
    "    - suggested_action: Pattern in Domain-Schicht verschieben\n"
    "    - status: offen\n"
)

# Invalider Knoten: cost PRAESENT aber LEER (nicht-leer-Pflicht, AK-4).
EVAL_FINDING_EMPTY_BENEFIT = (
    "### W-EF-4 · Befund mit leerem benefit\n"
    "- **text:** Eval-Befund mit blankem Benefit.\n"
    "- **Status:** TENTATIV\n"
    "- **source:** `Repo: gate-script`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-OUT-2\n"
    "- **type:** eval_finding\n"
    "- **id:** `BL-383.EF-4`\n"
    "- **eval_finding:**\n"
    "    - finding_id: BL-383.EF-4\n"
    "    - eval_kind: design_eval\n"
    "    - ref_node: BL-380.QS-1\n"
    "    - risk_class: Managerial\n"
    "    - severity: niedrig\n"
    "    - befund: ADR konflikt-offen\n"
    "    - cost: Klaerungs-Termin (niedrig)\n"
    "    - benefit:    \n"   # << blank (nur Whitespace)
    "    - suggested_action: ADR adjudizieren\n"
    "    - status: offen\n"
)

# Invalider Knoten: eval_finding mit binaerem PASS/FAIL als Primaer-Output (AK-4 Kern-Anti-These).
EVAL_FINDING_WITH_PASS_FAIL = (
    "### W-EF-5 · Befund mit PASS/FAIL-Primaer\n"
    "- **text:** Eval-Befund der ein binaeres Verdikt als Primaer-Output traegt.\n"
    "- **Status:** TENTATIV\n"
    "- **source:** `Repo: gate-script`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-OUT-3\n"
    "- **type:** eval_finding\n"
    "- **id:** `BL-383.EF-5`\n"
    "- **eval_finding:**\n"
    "    - finding_id: BL-383.EF-5\n"
    "    - eval_kind: drift_eval\n"
    "    - ref_node: BL-382.ADR-2\n"
    "    - risk_class: Commission\n"
    "    - severity: blocker\n"
    "    - befund: Impl widerspricht akzeptierter ADR\n"
    "    - cost: Refactor (hoch)\n"
    "    - benefit: ADR-Konformitaet wiederhergestellt\n"
    "    - suggested_action: Impl an ADR anpassen\n"
    "    - status: offen\n"
    "    - pass_fail: FAIL\n"   # << binaeres PASS/FAIL-Primaer verboten (AK-4)
)

# Valider Knoten je Kazman-Klasse (Enum-Vollstaendigkeits-Beweis).
EVAL_FINDING_COMMISSION = EVAL_FINDING_VALID.replace(
    "- **id:** `BL-383.EF-1`", "- **id:** `BL-383.EF-9`"
).replace("BL-383.EF-1", "BL-383.EF-9").replace(
    "risk_class: Omission", "risk_class: Commission"
).replace("W-EF-1", "W-EF-9")

# Bestehende quality_scenario- / adr- / plain-Knoten (Nicht-Regression).
SCENARIO_GOLD = (
    "### W-EXAMPLE-1\n"
    "- **text:** Niedriger Instabilitaets-Index bei neuer Modul-Einbindung.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Spec: BL-380_Spec.md Sec 3`\n"
    "- **Quelle:** `[[3_Spec/BL-380_Spec.md#3]]`\n"
    "- **Edge zu:** W-RM-4\n"
    "- **type:** quality_scenario\n"
    "- **id:** `BL-380.QS-1`\n"
    "- **scenario:**\n"
    "    - source: Entwickler\n"
    "    - stimulus: Einbindung eines neuen Utility-Moduls\n"
    "    - artifact: \"[ungegroundet: artifact?]\"\n"
    "    - environment: Entwicklung (CI-Build)\n"
    "    - response: Kopplung bleibt unter Schwelle\n"
    "    - response_measure:\n"
    "        - metric: Instabilitaets-Index I = Ce / (Ca + Ce) per AK\n"
    "        - threshold: I < 0.4\n"
    "        - method: K-Score-Lauf (Ca/Ce-Analyse) nach Code-Aenderung\n"
    "- **endpoint_type:** metric_component\n"
    "- **endpoint_ref:** `ak_details[AK_n].k_score_pro_ak`\n"
    "- **qualitaetsziel_ref:** `[[arc42/01_einfuehrung.md#Wartbarkeit]]`\n"
)

PLAIN_W_GOLD = (
    "### W-DOM-2 · Zweite Wahrheit\n"
    "- **text:** Drei der fuenf Indizes sind reine Frontmatter-Aggregate.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Repo:x.py:71`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-DOM-1\n"
)


# ───────────────────────── AK-4: Konstanten + Enum ─────────────────────────

def test_eval_finding_constants_present():
    """AK-4: RISK_CLASS_ENUM (genau die 4 Kazman-Klassen) + EVAL_KIND_ENUM (3 Werte) +
    EVAL_FINDING_FIELDS (Pflichtfelder) als Konstanten (analog ADR_STATUS_ENUM)."""
    assert qmw.RISK_CLASS_ENUM == {
        "Omission", "Commission", "Realization", "Managerial",
    }
    assert qmw.EVAL_KIND_ENUM == {
        "design_eval", "drift_eval", "pattern_realization",
    }
    # Pflichtfelder des Records (W-DOM-3) — mind. die kanonischen Schema-Felder.
    for f in ("finding_id", "eval_kind", "ref_node", "risk_class",
              "severity", "befund", "cost", "benefit", "suggested_action", "status"):
        assert f in qmw.EVAL_FINDING_FIELDS, f


def test_is_eval_finding_detection():
    """AK-4: `_is_eval_finding(body)` erkennt den type:eval_finding-Diskriminator;
    quality_scenario / adr / plain-W sind KEIN eval_finding."""
    blocks = qmw.parse_w_blocks(EVAL_FINDING_VALID)
    assert qmw._is_eval_finding(blocks[0]["body"]) is True
    assert qmw._is_eval_finding(qmw.parse_w_blocks(SCENARIO_GOLD)[0]["body"]) is False
    assert qmw._is_eval_finding(qmw.parse_w_blocks(PLAIN_W_GOLD)[0]["body"]) is False


# ───────────────────────── AK-4: Schema + Pflichtfelder ─────────────────────────

def test_valid_eval_finding_passes():
    """AK-4 (T-1): vollstaendiger eval_finding (alle Pflichtfelder + gueltige Enums +
    cost/benefit nicht-leer) -> gold (exit 0)."""
    res = qmw.validate_model(EVAL_FINDING_VALID)
    assert res["total"] == 1
    assert res["gold_count"] == 1, res["violations"]
    assert res["violations"] == []
    assert qmw.check_eval_finding_block(qmw.parse_w_blocks(EVAL_FINDING_VALID)[0]["body"]) == []


def test_eval_finding_metadata_exposed():
    """AK-4: der Check exponiert is_eval_finding=True + eval_finding_missing-Detail."""
    chk = qmw.check_w_block(qmw.parse_w_blocks(EVAL_FINDING_VALID)[0])
    assert chk.get("is_eval_finding") is True
    assert chk.get("eval_finding_missing") == []


def test_missing_schema_field_flagged():
    """AK-4: eval_finding ohne ein Pflicht-Schema-Feld (`befund` entfernt) -> Violation."""
    content = EVAL_FINDING_VALID.replace(
        "    - befund: Top-Szenario QS-2 vom Entwurf nicht abgedeckt\n", ""
    )
    missing = qmw.check_eval_finding_block(qmw.parse_w_blocks(content)[0]["body"])
    assert any("befund" in m for m in missing), missing
    assert qmw.validate_model(content)["gold_count"] == 0


# ───────────────────────── AK-4 (T-2): risk_class Kazman-4-Enum ─────────────────────────

def test_invalid_risk_class_flagged():
    """AK-4 (T-2): risk_class NICHT im Kazman-4-Enum (freier String) -> Violation."""
    res = qmw.validate_model(EVAL_FINDING_INVALID_RISK_CLASS)
    assert res["gold_count"] == 0
    missing_all = [m for v in res["violations"] for m in v["missing"]]
    assert any("risk_class" in m.lower() for m in missing_all), missing_all


def test_all_four_kazman_classes_valid():
    """AK-4: jede der 4 Kazman-Klassen ist ein valider risk_class-Wert (Enum vollstaendig)."""
    for cls in ("Omission", "Commission", "Realization", "Managerial"):
        content = EVAL_FINDING_VALID.replace("risk_class: Omission", "risk_class: %s" % cls)
        res = qmw.validate_model(content)
        assert res["gold_count"] == 1, (cls, res["violations"])


# ───────────────────────── AK-4 (T-3): cost/benefit-Pflicht ─────────────────────────

def test_missing_cost_flagged():
    """AK-4 (T-3): eval_finding ohne `cost` -> Violation (Aktionierbarkeit-Pflicht)."""
    res = qmw.validate_model(EVAL_FINDING_MISSING_COST)
    assert res["gold_count"] == 0
    missing_all = [m for v in res["violations"] for m in v["missing"]]
    assert any("cost" in m.lower() for m in missing_all), missing_all


def test_empty_benefit_flagged():
    """AK-4 (T-3): `benefit` PRAESENT aber LEER (blank) -> Violation (nicht-leer-Pflicht)."""
    res = qmw.validate_model(EVAL_FINDING_EMPTY_BENEFIT)
    assert res["gold_count"] == 0
    missing = qmw.check_eval_finding_block(qmw.parse_w_blocks(EVAL_FINDING_EMPTY_BENEFIT)[0]["body"])
    assert any("benefit" in m for m in missing), missing


def test_invalid_eval_kind_flagged():
    """AK-4: eval_kind NICHT im 3-Enum -> Violation (geschlossenes Enum)."""
    content = EVAL_FINDING_VALID.replace("eval_kind: design_eval", "eval_kind: laufzeit_eval")
    missing = qmw.check_eval_finding_block(qmw.parse_w_blocks(content)[0]["body"])
    assert any("eval_kind" in m for m in missing), missing


# ───────────────────────── AK-4 (T-4): KEIN binaeres PASS/FAIL als Primaer ─────────────────────────

def test_pass_fail_primary_flagged():
    """AK-4 (T-4): eval_finding mit `pass_fail`-Feld als Primaer-Output -> Violation.
    Das Gate liefert eine Risiko-Befund-Liste, NIE ein binaeres PASS/FAIL (Kern-Anti-These)."""
    res = qmw.validate_model(EVAL_FINDING_WITH_PASS_FAIL)
    assert res["gold_count"] == 0
    missing = qmw.check_eval_finding_block(qmw.parse_w_blocks(EVAL_FINDING_WITH_PASS_FAIL)[0]["body"])
    assert any("pass_fail" in m.lower() or "pass/fail" in m.lower() for m in missing), missing


def test_findings_list_is_primary_output():
    """AK-4 (T-4): eine eval_finding-LISTE (mehrere Befunde, Risiko-Form) -> gold; das ist
    das Primaer-Output (Befund-Liste), kein binaeres Verdikt."""
    content = EVAL_FINDING_VALID + EVAL_FINDING_COMMISSION
    res = qmw.validate_model(content)
    assert res["total"] == 2
    assert res["gold_count"] == 2, res["violations"]


# ───────────────────────── AK-4: Additiv (Nicht-Regression) ─────────────────────────

def test_scenario_node_unaffected_by_eval_finding_rule():
    """AK-4: ein quality_scenario-Knoten bleibt gold (eval_finding-Regel greift nicht)."""
    res = qmw.validate_model(SCENARIO_GOLD)
    assert res["total"] == 1
    assert res["gold_count"] == 1, res["violations"]


def test_plain_w_node_unaffected_by_eval_finding_rule():
    """AK-4: ein normaler Gold-Form-W{n}-Knoten bleibt gold (eval_finding-Regel greift nicht)."""
    res = qmw.validate_model(PLAIN_W_GOLD)
    assert res["total"] == 1
    assert res["gold_count"] == 1


def test_cli_exit_codes_eval_finding(tmp_path):
    """AK-4: CLI — valider eval_finding -> exit 0; risk_class-invalider -> exit 1; usage -> 2."""
    good = tmp_path / "good_ef_Model.md"
    good.write_text(EVAL_FINDING_VALID, encoding="utf-8")
    bad = tmp_path / "bad_ef_Model.md"
    bad.write_text(EVAL_FINDING_INVALID_RISK_CLASS, encoding="utf-8")
    assert qmw.main([str(good)]) == 0
    assert qmw.main([str(bad)]) == 1
    assert qmw.main([]) == 2


# ───────────────────────── AK-9: Pre-Write-Hook nested eval_finding-keys ─────────────────────────

def _run_guard(tool_name: str, file_path: str, content: str = "", new_string: str = "") -> dict:
    """Ruft guard_modus_writer.py mit simuliertem Hook-Input auf.
    OMNI_ENFORCE_MODUS_GUARD=1 erzwingt enforce=true unabhaengig von _session_params.md."""
    tool_input = {"file_path": file_path}
    if tool_name == "Write":
        tool_input["content"] = content
    else:
        tool_input["new_string"] = new_string
    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    env = os.environ.copy()
    env["OMNI_ENFORCE_MODUS_GUARD"] = "1"
    # Sicherstellen, dass der globale Kill-Switch NICHT aktiv ist.
    env.pop("OMNI_ENFORCE_ALL_OFF", None)
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(proc.stdout.strip())


def test_blocks_eval_finding_with_nested_sdf_mode():
    """AK-9 (T-12): type:eval_finding-Node mit verschachteltem `sdf_mode:` unter eval_finding: -> Block.

    Das Gate ist Bewerter, KEIN Modus-Setzer (INV-MODUS-5). Verschachtelte Verbotskeys
    unter eval_finding: muessen gefangen werden (content-gated, nicht nur Top-Level)."""
    result = _run_guard(
        tool_name="Edit",
        file_path="/vault/Backlog/BL-383-x/2_Model/BL-383_Model.md",
        new_string=(
            "### W-EF-1\n"
            "- **type:** eval_finding\n"
            "- **id:** `BL-383.EF-1`\n"
            "- **eval_finding:**\n"
            "    - finding_id: BL-383.EF-1\n"
            "    - risk_class: Omission\n"
            "    - sdf_mode: heavy\n"   # << verschachteltes Verbotsfeld unter eval_finding:
        ),
    )
    assert result["continue"] is False, (
        f"AK-9: eval_finding-Block mit verschachteltem sdf_mode muss blockiert sein (INV-MODUS-5). Got: {result}"
    )
    assert "MODUS_WRITER" in result.get("message", ""), f"Expected guard message, got: {result}"


def test_blocks_eval_finding_with_nested_recommended_modus():
    """AK-9: type:eval_finding-Node mit verschachteltem `recommended_modus:` -> Block."""
    result = _run_guard(
        tool_name="Write",
        file_path="/vault/Backlog/BL-383-x/2_Model/BL-383_Model.md",
        content=(
            "### W-EF-2\n"
            "type: eval_finding\n"
            "eval_finding:\n"
            "  finding_id: BL-383.EF-2\n"
            "  risk_class: Commission\n"
            "  recommended_modus: M3\n"   # << Verbotskey
        ),
    )
    assert result["continue"] is False, (
        f"AK-9: eval_finding-Block mit recommended_modus muss blockiert sein (INV-MODUS-5). Got: {result}"
    )
    assert "MODUS_WRITER" in result.get("message", "")


def test_allows_clean_eval_finding_node():
    """AK-9 (T-13): ein sauberer type:eval_finding-Node (kein Modus-Feld) -> passt durch
    (kein false-positive)."""
    result = _run_guard(
        tool_name="Edit",
        file_path="/vault/Backlog/BL-383-x/2_Model/BL-383_Model.md",
        new_string=(
            "### W-EF-3\n"
            "- **type:** eval_finding\n"
            "- **id:** `BL-383.EF-3`\n"
            "- **eval_finding:**\n"
            "    - finding_id: BL-383.EF-3\n"
            "    - eval_kind: design_eval\n"
            "    - ref_node: BL-380.QS-1\n"
            "    - risk_class: Omission\n"
            "    - severity: hoch\n"
            "    - befund: Top-Szenario nicht abgedeckt\n"
            "    - cost: Entwurf erweitern (mittel)\n"
            "    - benefit: schliesst Omission-Luecke\n"
            "    - suggested_action: Komponente nachziehen\n"
            "    - status: offen\n"
        ),
    )
    assert result["continue"] is True, (
        f"AK-9: sauberer eval_finding-Node (ohne Modus-Feld) muss passieren. Got: {result}"
    )


def test_eval_finding_hook_does_not_globally_scan_non_eval():
    """AK-9-Additiv-Schutz: Nicht-eval_finding-Nicht-ADR-Nicht-QDSA-Nicht-Manifest-Datei mit
    forbidden_key passiert weiterhin (BL-383-Erweiterung ist type:eval_finding-getriggert,
    nicht global)."""
    result = _run_guard(
        tool_name="Edit",
        file_path="/some/path/_berater_outputs.md",
        new_string="recommended_modus: M3\nsdf_mode_hint: heavy\n",
    )
    assert result["continue"] is True, (
        f"AK-9: Nicht-eval_finding-Nicht-QDSA-Nicht-Manifest-Datei muss weiterhin passieren. Got: {result}"
    )


# ───────────────────────── AK-7 (T-7): Messbarkeits-Klammer (metric/threshold-Bezug) ─────────────────────────
#
# batch_PL2 / AK-7: ein design_eval-Befund (der eine Szenario-Abdeckung bewertet) MUSS
# einen messbaren Bezug tragen — `metric`+`threshold` (goldDefine-Prinzip "messbar, nicht
# gut-genug", Spiegel BL-380 W-GH-1 response_measure.method-Pflichtfeld). Ohne diesen Bezug
# ist die Bewertung Bauchgefuehl -> Violation. ADDITIV-Scope: greift NUR fuer
# eval_kind: design_eval (drift_eval/pattern_realization tragen keinen response_measure-Bezug).

# Valider design_eval-Befund MIT metric/threshold-Bezug (Messbarkeits-Klammer erfuellt, AK-7).
EVAL_FINDING_DESIGN_WITH_MEASURE = (
    "### W-EF-7 · Top-Szenario QS-1 gegen Schwelle bewertet\n"
    "- **text:** Design-Eval bewertet QS-1 gegen seinen response_measure.\n"
    "- **Status:** TENTATIV\n"
    "- **source:** `Repo: design_eval gate-script run`\n"
    "- **Quelle:** `[[3_Spec/BL-383_Spec.md#AK-7]]`\n"
    "- **Edge zu:** W-DES-4\n"
    "- **type:** eval_finding\n"
    "- **id:** `BL-383.EF-7`\n"
    "- **eval_finding:**\n"
    "    - finding_id: BL-383.EF-7\n"
    "    - eval_kind: design_eval\n"
    "    - ref_node: BL-380.QS-1\n"
    "    - risk_class: Omission\n"
    "    - severity: hoch\n"
    "    - befund: QS-1 Schwelle I < 0.4 vom Entwurf nicht nachweisbar erfuellt\n"
    "    - cost: Entwurf um Kopplungs-Pfad erweitern (mittel)\n"
    "    - benefit: schliesst Omission-Luecke messbar gegen Schwelle\n"
    "    - suggested_action: Kopplung im Model reduzieren\n"
    "    - status: offen\n"
    "    - metric: Instabilitaets-Index I = Ce / (Ca + Ce)\n"   # << AK-7: messbarer Bezug
    "    - threshold: I < 0.4\n"                                  # << AK-7: Schwelle
)

# Invalider design_eval-Befund OHNE metric/threshold-Bezug (Bauchgefuehl statt messbar, AK-7).
EVAL_FINDING_DESIGN_NO_MEASURE = (
    "### W-EF-8 · Design-Befund ohne messbaren Bezug\n"
    "- **text:** Design-Eval-Befund der nur ein Bauchgefuehl traegt.\n"
    "- **Status:** TENTATIV\n"
    "- **source:** `Repo: design_eval gate-script run`\n"
    "- **Quelle:** `[[3_Spec/BL-383_Spec.md#AK-7]]`\n"
    "- **Edge zu:** W-DES-4\n"
    "- **type:** eval_finding\n"
    "- **id:** `BL-383.EF-8`\n"
    "- **eval_finding:**\n"
    "    - finding_id: BL-383.EF-8\n"
    "    - eval_kind: design_eval\n"
    "    - ref_node: BL-380.QS-1\n"
    "    - risk_class: Omission\n"
    "    - severity: hoch\n"
    "    - befund: QS-1 wirkt nicht gut genug abgedeckt\n"   # << kein metric/threshold-Bezug
    "    - cost: Entwurf ueberarbeiten (mittel)\n"
    "    - benefit: bessere Abdeckung\n"
    "    - suggested_action: Entwurf nachschaerfen\n"
    "    - status: offen\n"
)


def test_design_eval_finding_with_measure_passes():
    """AK-7 (T-7): ein design_eval-Befund MIT metric+threshold-Bezug -> gold (goldDefine-Muster)."""
    res = qmw.validate_model(EVAL_FINDING_DESIGN_WITH_MEASURE)
    assert res["total"] == 1
    assert res["gold_count"] == 1, res["violations"]
    assert qmw.check_eval_finding_block(
        qmw.parse_w_blocks(EVAL_FINDING_DESIGN_WITH_MEASURE)[0]["body"]
    ) == []


def test_design_eval_finding_without_measure_flagged():
    """AK-7 (T-7): ein design_eval-Befund OHNE metric/threshold-Bezug -> Violation.
    Die Messbarkeits-Klammer (goldDefine) ist strukturell, kein Bauchgefuehl."""
    res = qmw.validate_model(EVAL_FINDING_DESIGN_NO_MEASURE)
    assert res["gold_count"] == 0
    missing = qmw.check_eval_finding_block(
        qmw.parse_w_blocks(EVAL_FINDING_DESIGN_NO_MEASURE)[0]["body"]
    )
    assert any("metric" in m.lower() or "threshold" in m.lower() or "measure" in m.lower()
               for m in missing), missing


def test_design_eval_finding_partial_measure_flagged():
    """AK-7: metric vorhanden, threshold fehlt -> Violation (BEIDE Teile der Klammer Pflicht)."""
    content = EVAL_FINDING_DESIGN_WITH_MEASURE.replace(
        "    - threshold: I < 0.4\n", ""
    )
    missing = qmw.check_eval_finding_block(qmw.parse_w_blocks(content)[0]["body"])
    assert any("threshold" in m.lower() or "measure" in m.lower() for m in missing), missing


def test_non_design_eval_finding_exempt_from_measure():
    """AK-7-Scope: ein drift_eval-Befund (kein response_measure-Bezug) bleibt OHNE
    metric/threshold gold — die Messbarkeits-Klammer greift NUR fuer design_eval."""
    # EVAL_FINDING_VALID ist drift_eval-frei (Omission/design); explizit drift_eval bauen:
    drift = EVAL_FINDING_VALID.replace(
        "eval_kind: design_eval", "eval_kind: drift_eval"
    ).replace("ref_node: BL-380.QS-2", "ref_node: BL-382.ADR-1")
    res = qmw.validate_model(drift)
    assert res["gold_count"] == 1, res["violations"]


def test_pattern_realization_finding_exempt_from_measure():
    """AK-7-Scope: ein pattern_realization-Befund bleibt OHNE metric/threshold gold."""
    res = qmw.validate_model(EVAL_FINDING_MISSING_COST.replace(
        # cost ergaenzen, damit NUR die Measure-Frage (nicht cost) getestet wird:
        "    - benefit: korrekte Schicht-Grenze\n",
        "    - cost: Pattern verschieben (mittel)\n    - benefit: korrekte Schicht-Grenze\n",
    ))
    assert res["gold_count"] == 1, res["violations"]
