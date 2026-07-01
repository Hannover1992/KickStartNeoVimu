"""
test_eval_zone_consume.py — BL-383 batch_PL4 (AK-8 + AK-6): Selbst-Konsistenz-Zonierung
des Eval-Gate-Urteils-Kerns (ROTE Zone) + Konsument-per-ID Schema-Konsum (read-only).

AK-8 (Urteils-Kern = ROTE Zone, Selbst-Konsistenz W-INV-3 / W-PRC-3):
  Das Eval-Gate ist Anti-false-GREEN. Sein eigener qualitativer Urteils-Kern (Suitability,
  Konflikt-Erkennung, qualitatives Szenario-Urteil, inhaltliche risk_class-Zuordnung) MUSS
  eine ROTE/agentische Zone sein (INV-VEHIKEL-2) — NIEMALS ein durchwinkender Workflow. Ein
  per Workflow durchgewinktes Eval-Gate waere die ironische Selbst-Verletzung der Doktrin.
  Nur der deterministische Schema-/Existenz-/Zaehl-/metric_component-Anteil bleibt gruen-faehig.
  Das TESTBARE Artefakt = der `workflow_zones.py`-Registry-Eintrag: resolve_vehicle der
  Eval-Urteils-Aktivitaet gibt in JEDEM Modus 'worker' (rot-never-Invariante).

AK-6 (Konsument-per-ID + read-only Schema-Konsum, W-DOM-1 / W-INTEROP-1):
  Das Eval-Gate fuehrt KEINEN neuen Truth-Node-Typ ein. Es liest BL-380 quality_scenario-
  (SOLL) und BL-382 adr-Nodes (Drift-Bezug) per STABILER ID (`{BL-SLUG}.QS-{n}` /
  `{BL-SLUG}.ADR-{n}`, BL-380/382 W-DOM-4) read-only. ID-Regex testbar (akzeptiert wohlge-
  formte IDs, lehnt malformed + Vault-Pfad-Referenzen ab). Schema-Konsum validiert eine
  referenzierte ID gegen die im Model produzierten Nodes (unbekannte ID -> Fehler), OHNE
  je in den Vault zu schreiben (kein Producer-Apparat, kein Schema-Edit).

Scope batch_PL4: die DETERMINISTISCHE Zonen-Registrierung (AK-8) + ID-Regex + read-only
Schema-Konsum-Validator (AK-6). Der qualitative Realization-/Suitability-Verify selbst
(das WAS er urteilt) ist markdown_uncoverable (ROTE Zone, agentisch) — hier nur testbar,
DASS er rot registriert ist + DASS der Konsum per ID read-only laeuft. Das Interop-Erbe
(FINALE-BL-380/382-Impl-Abgleich, SOA-2) ist forward_verify (dokumentiert, nicht jetzt-testbar).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import workflow_zones as wz  # noqa: E402
import eval_id_consume as eic  # noqa: E402

SCRIPT_DIR = Path(__file__).parent.absolute()


# ═══════════════════════════════════════════════════════════════════════════
# AK-8 — Urteils-Kern des Eval-Gates = ROTE Zone (workflow_zones-Registrierung)
# ═══════════════════════════════════════════════════════════════════════════

# Die Eval-Urteils-Aktivitaeten (qualitativer Kern). Diese MUESSEN rot sein (INV-VEHIKEL-2):
#   - der Realization-Suitability-Verify (IV-14, AK-3: passt das Pattern? Kazman-Urteil)
#   - das qualitative Design-Eval-Urteil (AK-1 rein-qualitativer Pfad, kein metric_component)
#   - die semantische Drift-/ADR-Widerspruchs-Erkennung (AK-2: widerspricht Impl der ADR?)
EVAL_JUDGMENT_RED_ACTIVITIES = [
    "_eval_berater_realizationverify",   # Realization-Suitability-Verify (ROTE Zone, AK-3/AK-8)
    "_eval_berater_designeval_urteil",   # qualitatives Design-Eval-Urteil (AK-1 qualitativer Pfad)
    "_eval_berater_drifturteil",         # semantische ADR-Drift-Widerspruchs-Erkennung (AK-2)
]


def test_eval_judgment_core_is_red_zone():
    """AK-8 (T-14): der qualitative Urteils-Kern des Eval-Gates ist als ROTE Zone
    registriert — NIE gruen, NIE gelb. Selbst-Konsistenz (W-INV-3): das Anti-false-GREEN-
    Gate darf seinen eigenen Urteils-Schritt nicht durchwinken."""
    for act in EVAL_JUDGMENT_RED_ACTIVITIES:
        assert wz.zone_of(act) == "red", (
            f"Eval-Urteils-Aktivitaet {act} MUSS rot sein (AK-8 Selbst-Konsistenz)"
        )


def test_eval_judgment_core_never_workflow_any_mode():
    """AK-8 (T-14, rot-never-Invariante): die Eval-Urteils-Aktivitaet wird in KEINEM Modus
    (false/normal/fast) zu 'workflow' aufgeloest — strukturell altmodisch (Team-Member)."""
    for act in EVAL_JUDGMENT_RED_ACTIVITIES:
        for mode in ("false", "normal", "fast"):
            v = wz.vehicle_for(act, mode)
            assert v == "worker", (
                f"INVARIANT-VERLETZUNG: {act} (Eval-Urteil) -> {v} bei mode={mode} "
                f"(Anti-false-GREEN-Gate darf sich nicht selbst per Workflow durchwinken)"
            )


def test_eval_judgment_core_registered_explicitly_not_failsafe():
    """AK-8 / INV-VEHIKEL-6b: die Eval-Urteils-Aktivitaeten sind EXPLIZIT in der Registry
    (nicht nur per Fail-Safe-rot) — damit die Selbst-Konsistenz dokumentiert + bewusst ist,
    nicht zufaellig (W-LOC-4: bewusste Zonierung statt unklassifiziert)."""
    for act in EVAL_JUDGMENT_RED_ACTIVITIES:
        assert wz._norm(act) in wz.ZONE_REGISTRY, (
            f"{act} sollte EXPLIZIT (nicht fail-safe) als rot registriert sein"
        )
        assert wz.ZONE_REGISTRY[wz._norm(act)] == "red"


def test_eval_gate_script_anteil_bleibt_green_faehig():
    """AK-8 (Selbst-Konsistenz-Gegenstueck): der DETERMINISTISCHE Gate-Script-Anteil
    (Schema/Existenz/Zaehl/metric_component-Vergleich) bleibt gruen-faehig — nur der
    URTEILS-Kern ist rot. Die Zonierung schneidet entlang INV-VEHIKEL-Zonen (W-LOC-4),
    nicht das ganze Gate rot."""
    # Der deterministische Eval-Gate-Script-Lauf (Schema-/ID-/Existenz-Checks) ist green.
    assert wz.zone_of("eval_gate_script") == "green"
    # green @normal -> Workflow-faehig (der det-Anteil DARF Workflow sein).
    assert wz.vehicle_for("eval_gate_script", "normal") == "workflow"


def test_red_never_workflow_invariant_still_holds():
    """AK-8-Regression: die globale rot-never-Invariante (BL-330 Kern) bleibt unberuehrt —
    KEINE rote Registry-Aktivitaet (inkl. der neuen Eval-Urteils-Eintraege) loest je zu
    Workflow auf."""
    red_acts = [a for a, z in wz.ZONE_REGISTRY.items() if z == "red"]
    assert red_acts
    for act in red_acts:
        for mode in ("false", "normal", "fast"):
            assert wz.vehicle_for(act, mode) != "workflow", (
                f"rot-never-Invariante verletzt: {act} -> workflow @ {mode}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# AK-6 — ID-Referenz-Regex (`{BL-SLUG}.QS-{n}` / `{BL-SLUG}.ADR-{n}`)
# ═══════════════════════════════════════════════════════════════════════════

def test_qs_id_regex_accepts_wellformed():
    """AK-6 (T-8): die QS-ID-Regex akzeptiert wohlgeformte `{BL-SLUG}.QS-{n}`-Referenzen."""
    for good in ("BL-380.QS-1", "BL-380.QS-42", "BL-383.QS-7"):
        assert eic.is_qs_id(good), good


def test_qs_id_regex_rejects_malformed_and_paths():
    """AK-6 (T-8): malformed QS-IDs + Vault-Pfad-Referenzen werden abgelehnt (robust gegen
    Vault-Reorg = per ID, NICHT per Pfad)."""
    for bad in (
        "BL-380.QS-",            # keine Nummer
        "BL-380.QS",             # kein Trenner/Nummer
        "QS-1",                  # kein BL-SLUG-Praefix
        "BL-380.ADR-1",          # ADR, keine QS
        "2_Model/BL-380_Model.md#W-QS-1",  # Vault-Pfad+Anchor (verboten, W-DOM-2)
        "BL-380.QS-1.2",         # Nummer nicht rein-numerisch terminiert
        "",
        None,
    ):
        assert not eic.is_qs_id(bad), bad


def test_adr_id_regex_accepts_wellformed():
    """AK-6 (T-8): die ADR-ID-Regex akzeptiert wohlgeformte `{BL-SLUG}.ADR-{n}`-Referenzen
    (identisch zum ADR_EDGE_ID-Schema in quality_model_wform — Single-Source)."""
    for good in ("BL-382.ADR-1", "BL-382.ADR-99", "BL-383.ADR-3"):
        assert eic.is_adr_id(good), good


def test_adr_id_regex_rejects_malformed_and_paths():
    """AK-6 (T-8): malformed ADR-IDs + Pfad-Referenzen werden abgelehnt."""
    for bad in (
        "BL-382.ADR-",
        "ADR-1",
        "BL-382.QS-1",          # QS, keine ADR
        "Backlog/BL-382/.../2_Model#W-ADR-1",
        "",
        None,
    ):
        assert not eic.is_adr_id(bad), bad


def test_classify_ref_id_kind():
    """AK-6: classify_ref_id ordnet eine ref_node-ID ihrem SOLL-Knoten-Typ zu
    (qs / adr / pattern / None bei malformed)."""
    assert eic.classify_ref_id("BL-380.QS-1") == "qs"
    assert eic.classify_ref_id("BL-382.ADR-2") == "adr"
    # Pattern-IDs (PatternLibrary-Treffer, AK-3 ref_node) sind weder QS noch ADR.
    assert eic.classify_ref_id("pattern-strategy-factory") == "pattern"
    assert eic.classify_ref_id("2_Model/x.md#W-QS-1") is None  # Pfad = malformed


# ═══════════════════════════════════════════════════════════════════════════
# AK-6 — read-only Schema-Konsum (per ID gegen produzierte BL-380/382-Nodes)
# ═══════════════════════════════════════════════════════════════════════════

# BL-380 quality_scenario-Node (6 iSAQB-Felder + response_measure + QS-ID) — Producer-Output.
_QS_NODE = (
    "### W-QS-1 · Niedrige Kopplung\n"
    "- **text:** Kopplung bleibt unter Schwelle.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Spec: BL-380_Spec.md`\n"
    "- **Quelle:** `[[3_Spec/BL-380_Spec.md#3]]`\n"
    "- **Edge zu:** W-RM-1\n"
    "- **type:** quality_scenario\n"
    "- **id:** `BL-380.QS-1`\n"
    "- **scenario:**\n"
    "    - source: Entwickler\n"
    "    - stimulus: neues Modul\n"
    "    - artifact: Utility\n"
    "    - environment: CI\n"
    "    - response: unter Schwelle\n"
    "    - response_measure:\n"
    "        - metric: Instabilitaet I\n"
    "        - threshold: I < 0.4\n"
    "        - method: K-Score-Lauf\n"
    "- **endpoint_type:** metric_component\n"
    "- **endpoint_ref:** `ak_details[AK_1]`\n"
)

# BL-382 adr-Node (6 Nygard-Felder + betrifft_baustein + ADR-ID) — Producer-Output.
_ADR_NODE = (
    "### W-ADR-1 · Nutze X\n"
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
    "    - begruendung: weil besser\n"
    "    - konsequenzen: mehr X\n"
    "    - status: akzeptiert\n"
    "    - betrifft_baustein: [Komponente-A]\n"
)

_PRODUCER_MODEL = _QS_NODE + _ADR_NODE


def test_load_consumable_nodes_indexes_qs_and_adr_by_id():
    """AK-6 (W-INTEROP-1): der Konsum liest die produzierten quality_scenario- + adr-Nodes
    und indiziert sie PER ID (read-only). Schluessel = die stabilen IDs."""
    index = eic.load_consumable_nodes(_PRODUCER_MODEL)
    assert set(index.keys()) == {"BL-380.QS-1", "BL-382.ADR-1"}
    assert index["BL-380.QS-1"]["kind"] == "quality_scenario"
    assert index["BL-382.ADR-1"]["kind"] == "adr"


def test_resolve_ref_node_known_qs_returns_schema_fields():
    """AK-6: eine bekannte QS-ID wird aufgeloest -> der konsumierte Knoten traegt die
    BL-380-Schema-Felder (response_measure-Tripel + endpoint_type), read-only."""
    res = eic.resolve_ref_node("BL-380.QS-1", _PRODUCER_MODEL)
    assert res is not None
    assert res["kind"] == "quality_scenario"
    assert res["fields"].get("metric") and res["fields"].get("threshold")
    assert res["fields"].get("endpoint_type") == "metric_component"


def test_resolve_ref_node_known_adr_returns_betrifft_baustein():
    """AK-6 (Drift-Bezug, AK-2-Anker): eine bekannte ADR-ID wird aufgeloest -> der Knoten
    traegt die betrifft_baustein-Kante (BL-382-Schema), read-only."""
    res = eic.resolve_ref_node("BL-382.ADR-1", _PRODUCER_MODEL)
    assert res is not None
    assert res["kind"] == "adr"
    assert res["fields"].get("betrifft_baustein")
    assert res["fields"].get("status") == "akzeptiert"


def test_resolve_unknown_ref_node_is_error():
    """AK-6 (Negativ): eine unbekannte/nicht-produzierte ID loest NICHT auf (None) — der
    Befund haengt nachweislich an einem EXISTENTEN SOLL-Knoten (rueckverfolgbar)."""
    assert eic.resolve_ref_node("BL-380.QS-999", _PRODUCER_MODEL) is None
    assert eic.resolve_ref_node("BL-382.ADR-7", _PRODUCER_MODEL) is None


def test_resolve_malformed_ref_node_is_error():
    """AK-6 (Negativ): eine malformed ID-Referenz (z.B. Vault-Pfad) loest NIE auf."""
    assert eic.resolve_ref_node("2_Model/BL-380_Model.md#W-QS-1", _PRODUCER_MODEL) is None
    assert eic.resolve_ref_node("", _PRODUCER_MODEL) is None
    assert eic.resolve_ref_node(None, _PRODUCER_MODEL) is None


def test_validate_ref_consumable_known_ok_unknown_violation():
    """AK-6: validate_ref_consumable prueft EINE ref_node-ID gegen das Producer-Model.
    bekannt + ID-format-valide -> [] (ok); unbekannt / malformed -> Violation-Liste."""
    assert eic.validate_ref_consumable("BL-380.QS-1", _PRODUCER_MODEL) == []
    assert eic.validate_ref_consumable("BL-382.ADR-1", _PRODUCER_MODEL) == []
    # malformed ID-Format.
    assert eic.validate_ref_consumable("QS-1", _PRODUCER_MODEL)
    # ID-format-valide ABER nicht im Model produziert (dangling Referenz).
    assert eic.validate_ref_consumable("BL-380.QS-42", _PRODUCER_MODEL)


def test_consume_is_read_only_no_write(tmp_path):
    """AK-6 (W-DOM-1 Kern): der Schema-Konsum schreibt NIE in den Vault — Producer-Datei
    bleibt byte-identisch nach dem Konsum (kein Producer-Apparat, kein Schema-Edit)."""
    model = tmp_path / "Producer_Model.md"
    model.write_text(_PRODUCER_MODEL, encoding="utf-8")
    before = model.read_bytes()
    # voller Konsum-Lauf: laden, aufloesen, validieren.
    eic.load_consumable_nodes(model.read_text(encoding="utf-8"))
    eic.resolve_ref_node("BL-380.QS-1", model.read_text(encoding="utf-8"))
    eic.validate_ref_consumable("BL-382.ADR-1", model.read_text(encoding="utf-8"))
    after = model.read_bytes()
    assert before == after, "Schema-Konsum MUSS read-only sein (kein Vault-Write)"


def test_consume_introduces_no_new_truth_node_type():
    """AK-6 (W-DOM-1-Falsifikation): der Konsum fuehrt KEINEN eigenen persistenten Truth-
    Node-Typ ein — load_consumable_nodes liefert NUR die bestehenden BL-380/382-Typen
    (quality_scenario/adr), nie einen BL-383-eigenen Node-Typ."""
    index = eic.load_consumable_nodes(_PRODUCER_MODEL)
    kinds = {n["kind"] for n in index.values()}
    assert kinds <= {"quality_scenario", "adr"}, (
        "Konsument darf nur BL-380/382-Node-Typen lesen, keinen eigenen einfuehren"
    )


# ═══════════════════════════════════════════════════════════════════════════
# AK-6 — CLI-Smoke (read-only, exit-Codes)
# ═══════════════════════════════════════════════════════════════════════════

def test_cli_resolve_known_id_exit0(tmp_path):
    """AK-6: CLI `eval_id_consume.py <Model.md> --ref <ID>` -> exit 0 bei bekannter ID."""
    model = tmp_path / "M.md"
    model.write_text(_PRODUCER_MODEL, encoding="utf-8")
    assert eic.main([str(model), "--ref", "BL-380.QS-1"]) == 0


def test_cli_resolve_unknown_id_exit1(tmp_path):
    """AK-6: CLI -> exit 1 (Violation) bei unbekannter/dangling ID."""
    model = tmp_path / "M.md"
    model.write_text(_PRODUCER_MODEL, encoding="utf-8")
    assert eic.main([str(model), "--ref", "BL-380.QS-999"]) == 1


def test_cli_usage_error_exit2():
    """AK-6: CLI ohne Argumente -> exit 2 (Usage)."""
    assert eic.main([]) == 2
