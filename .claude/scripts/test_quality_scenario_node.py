"""
test_quality_scenario_node.py — BL-380 B1/AK-1: quality_scenario Truth-Node-Typ.

Der `type: quality_scenario`-Knoten ist eine ADDITIVE Erweiterung des BL-243-atomaren
Gold-Form-`### W{n}`-Knotens. Er traegt zusaetzlich:
  - einen typisierten `scenario:`-Block mit den 6 iSAQB-Feldern
    (source/stimulus/artifact/environment/response/response_measure)
  - response_measure als Pflicht-Triple {metric, threshold, method}
    (`method` = Goodhart-Guard, W-GH-1 / AK-6-Vorgriff)
  - zwei Pflicht-Kanten: UP `qualitaetsziel_ref` (arc42 §1.2), DOWN `endpoint_ref`/`endpoint_type`
  - ID-Schema `{BL-SLUG}.QS-{n}`

ADDITIV-Invariante: bestehende `### W{n}`-Gold-Form-Knoten (ohne `type: quality_scenario`)
bleiben unveraendert valide — die typ-konditionale Pruefung greift NUR bei quality_scenario.

On-disk-Form (Spec Sec 2.1 / Sec 3): `### W{n}`-Heading + Gold-Form-Bullets (text/Status/
source/Quelle/Edge zu) + ein YAML-indentierter `scenario:`-Block + endpoint_type/endpoint_ref
+ qualitaetsziel_ref.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import quality_model_wform as qmw  # noqa: E402


# Vollstaendiger, valider quality_scenario-Knoten (Gold-Form-Basis + scenario-Block + Kanten).
SCENARIO_VALID = (
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

# Invalider Knoten: response_measure ohne `method` (Goodhart-Guard, W-GH-1).
SCENARIO_MISSING_METHOD = (
    "### W-EXAMPLE-2\n"
    "- **text:** Antwortzeit unter 200ms im 90. Perzentil unter Last.\n"
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
    "- **endpoint_type:** ak_test\n"
    "- **endpoint_ref:** `AK-12`\n"
    "- **qualitaetsziel_ref:** `[[arc42/01_einfuehrung.md#Leistungseffizienz]]`\n"
)

# Invalider Knoten: fehlendes Pflicht-iSAQB-Feld (environment) + fehlende UP-Kante.
SCENARIO_MISSING_FIELD = (
    "### W-EXAMPLE-3\n"
    "- **text:** Unvollstaendiges Szenario.\n"
    "- **Status:** TENTATIV\n"
    "- **source:** `Crumbs:F`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-X-9\n"
    "- **type:** quality_scenario\n"
    "- **id:** `BL-380.QS-3`\n"
    "- **scenario:**\n"
    "    - source: Entwickler\n"
    "    - stimulus: Aenderung\n"
    "    - artifact: Modul\n"
    "    - response: Verhalten\n"
    "    - response_measure:\n"
    "        - metric: X\n"
    "        - threshold: Y\n"
    "        - method: Z\n"
    "- **endpoint_type:** ak_test\n"
    "- **endpoint_ref:** `AK-3`\n"
)

# Bestehender Gold-Form-W{n}-Knoten OHNE type: quality_scenario (Nicht-Regression).
PLAIN_W_GOLD = (
    "### W-DOM-2 · Zweite Wahrheit\n"
    "- **text:** Drei der fuenf Indizes sind reine Frontmatter-Aggregate.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Repo:x.py:71`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-DOM-1\n"
)


def test_valid_scenario_passes():
    """Ein vollstaendiger quality_scenario-Knoten ist gold (alle 6 Felder + Triple + 2 Kanten)."""
    res = qmw.validate_model(SCENARIO_VALID)
    assert res["total"] == 1
    assert res["gold_count"] == 1, res["violations"]
    assert res["violations"] == []


def test_missing_method_flagged():
    """Goodhart-Guard: response_measure ohne `method` -> Violation (W-GH-1 / AK-6-Vorgriff)."""
    res = qmw.validate_model(SCENARIO_MISSING_METHOD)
    assert res["gold_count"] == 0
    assert any(
        any("method" in m for m in v["missing"]) for v in res["violations"]
    ), res["violations"]


def test_missing_isaqb_field_and_edge_flagged():
    """Fehlendes Pflicht-iSAQB-Feld (environment) + fehlende UP-Kante -> Violation."""
    res = qmw.validate_model(SCENARIO_MISSING_FIELD)
    assert res["gold_count"] == 0
    missing_all = [m for v in res["violations"] for m in v["missing"]]
    assert any("environment" in m for m in missing_all), missing_all
    assert any("qualitaetsziel_ref" in m for m in missing_all), missing_all


def test_plain_w_node_unaffected_by_scenario_rule():
    """ADDITIV: ein normaler Gold-Form-W{n}-Knoten bleibt gold (scenario-Regel greift nicht)."""
    res = qmw.validate_model(PLAIN_W_GOLD)
    assert res["total"] == 1
    assert res["gold_count"] == 1
    assert res["violations"] == []


def test_scenario_metadata_exposed():
    """Der Check exponiert is_scenario=True + scenario_missing-Detail fuer Tooling."""
    blocks = qmw.parse_w_blocks(SCENARIO_VALID)
    chk = qmw.check_w_block(blocks[0])
    assert chk.get("is_scenario") is True
    assert chk.get("scenario_missing") == []


def test_cli_exit_codes_scenario(tmp_path):
    """CLI: valider Szenario-Node -> exit 0; method-loser -> exit 1 (Smoke)."""
    good = tmp_path / "good_scenario_Model.md"
    good.write_text(SCENARIO_VALID, encoding="utf-8")
    bad = tmp_path / "bad_scenario_Model.md"
    bad.write_text(SCENARIO_MISSING_METHOD, encoding="utf-8")
    assert qmw.main([str(good)]) == 0
    assert qmw.main([str(bad)]) == 1
