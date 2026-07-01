"""
test_adr_node.py — BL-382 batch_PL1 (AK-1 / AK-5 / AK-11): ADR Truth-Node-Typ.

Der `type: adr`-Knoten ist eine ADDITIVE Erweiterung des BL-243-atomaren
Gold-Form-`### W{n}`-Knotens (strukturelle Schwester von BL-380 quality_scenario).
Er traegt zusaetzlich einen typisierten `adr:`-Block mit den 6 Nygard-Feldern
(entscheidung / problem_kontext / alternativen / begruendung / konsequenzen / status):

  - AK-1: 6 Nygard-Pflichtfelder unter `adr:` (analog SCENARIO_ISAQB_FIELDS).
  - AK-5: `adr.status` IN {vorgeschlagen, akzeptiert, superseded, konflikt-offen}
    — geprueft gegen das ADR-Enum, NIE gegen CANONICAL_STATUS (Namens-Kollisions-
    Schutz; `adr.status` ist orthogonal zum Gold-Form-`Status:`, W-VAL-3).
  - AK-11: Pre-Write-Hook (guard_modus_writer.py) faengt INV-MODUS-5-Verbotskeys
    AUCH unter verschachteltem `adr:`-Block (nicht nur Top-Level).

ADDITIV-Invariante: bestehende `### W{n}`-Gold-Form-Knoten und `quality_scenario`-
Knoten bleiben unveraendert valide — die typ-konditionale ADR-Pruefung greift NUR
bei `type: adr`.

Hinweis: Goodhart-Guard (begruendung nicht-leer, AK-4), alternativen-Inhalts-Pruefung
(B-3, AK-6), Zyklus-Guard (AK-7) und Konflikt-Stufe-1 (AK-8) gehoeren NICHT zu
batch_PL1 — diese Datei deckt AK-1 (Schema/6 Felder) + AK-5 (Status-Enum) + AK-11
(Hook nested adr) ab.
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


# ───────────────────────── AK-1 / AK-5: Validator-Fixtures ─────────────────────────

# Vollstaendiger, valider ADR-Knoten (Gold-Form-Basis + adr-Block mit 6 Nygard-Feldern).
ADR_VALID = (
    "### W-ADR-1 · Workflow-Motor als deterministischer Dispatch\n"
    "- **text:** Der SDF-Implement-Inner-Loop laeuft als deterministischer Workflow.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Spec: BL-382_Spec.md Sec 5`\n"
    "- **Quelle:** `[[3_Spec/BL-382_Spec.md#5]]`\n"
    "- **Edge zu:** W-DOM-1\n"
    "- **type:** adr\n"
    "- **id:** `BL-382.ADR-1`\n"
    "- **adr:**\n"
    "    - entscheidung: Workflow-Motor als deterministischer Dispatch\n"
    "    - problem_kontext: Mega-Worker-Fragilitaet bei interpretiertem Skill-Pseudocode\n"
    "    - alternativen:\n"
    "        - option: Mega-Worker beibehalten\n"
    "          abgelehnt_weil: Step-Buendelung strukturell moeglich\n"
    "    - begruendung: Step-Skeleton aus feststehendem Modus schliesst Self-Assign aus\n"
    "    - konsequenzen: Determinismus gewonnen, Engine-Komplexitaet steigt\n"
    "    - status: akzeptiert\n"
    "    - betrifft_baustein: [\"dispatch_implement.js\"]\n"
)

# Invalider Knoten: adr-Block ohne `begruendung` (Nygard-Pflichtfeld fehlt, AK-1).
ADR_MISSING_BEGRUENDUNG = (
    "### W-ADR-2 · ID-adressierbarer ADR-Knoten\n"
    "- **text:** Jeder ADR-Knoten hat eine stabile ID.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Spec: BL-382_Spec.md Sec 5`\n"
    "- **Quelle:** `[[3_Spec/BL-382_Spec.md#5]]`\n"
    "- **Edge zu:** W-DOM-4\n"
    "- **type:** adr\n"
    "- **id:** `BL-382.ADR-2`\n"
    "- **adr:**\n"
    "    - entscheidung: ID-Schema {BL-SLUG}.ADR-{n}\n"
    "    - problem_kontext: Downstream-Konsumenten muessen per Maschinencode referenzieren\n"
    "    - alternativen:\n"
    "        - option: Nur Vault-Dokument-Pfad\n"
    "          abgelehnt_weil: nicht stabil adressierbar\n"
    "    - konsequenzen: BL-383 kann per ID referenzieren\n"
    "    - status: vorgeschlagen\n"
)

# Invalider Knoten: adr.status NICHT im ADR-Enum (AK-5).
ADR_INVALID_STATUS = (
    "### W-ADR-3 · Status nicht im Enum\n"
    "- **text:** ADR mit ungueltigem Status.\n"
    "- **Status:** TENTATIV\n"
    "- **source:** `Crumbs:B-4`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-STAT-1\n"
    "- **type:** adr\n"
    "- **id:** `BL-382.ADR-3`\n"
    "- **adr:**\n"
    "    - entscheidung: Irgendwas\n"
    "    - problem_kontext: Kontext\n"
    "    - alternativen:\n"
    "        - option: Andere Wahl\n"
    "          abgelehnt_weil: Grund\n"
    "    - begruendung: Eine Begruendung\n"
    "    - konsequenzen: Folgen\n"
    "    - status: entschieden\n"   # << NICHT im 4-Enum (vorgeschlagen/akzeptiert/superseded/konflikt-offen)
)

# Valider Knoten mit Orthogonalitaet: Gold-Form Status BESTAETIGT + adr.status superseded (W-VAL-3).
ADR_ORTHOGONAL_STATUS = (
    "### W-ADR-4 · Orthogonale Status-Dimensionen\n"
    "- **text:** Eine abgeloeste, aber sicher getroffene Entscheidung.\n"
    "- **Status:** BESTAETIGT\n"   # << Gold-Form epistemisch (CANONICAL_STATUS)
    "- **source:** `Spec: BL-382_Spec.md Sec 5`\n"
    "- **Quelle:** `[[3_Spec/BL-382_Spec.md#5]]`\n"
    "- **Edge zu:** W-VAL-3\n"
    "- **type:** adr\n"
    "- **id:** `BL-382.ADR-4`\n"
    "- **adr:**\n"
    "    - entscheidung: Alte Architektur-Wahl\n"
    "    - problem_kontext: Frueherer Kontext\n"
    "    - alternativen:\n"
    "        - option: Beibehalten\n"
    "          abgelehnt_weil: ueberholt\n"
    "    - begruendung: War damals korrekt, inzwischen abgeloest\n"
    "    - konsequenzen: Historie bleibt verlustfrei erhalten\n"
    "    - status: superseded\n"   # << ADR-Enum fachlich (NICHT CANONICAL_STATUS)
)

# Bestehender quality_scenario-Knoten (Nicht-Regression — darf NICHT von adr-Regel beruehrt werden).
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

# Bestehender plain-W-Knoten OHNE type (Nicht-Regression).
PLAIN_W_GOLD = (
    "### W-DOM-2 · Zweite Wahrheit\n"
    "- **text:** Drei der fuenf Indizes sind reine Frontmatter-Aggregate.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Repo:x.py:71`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-DOM-1\n"
)


# ───────────────────────── AK-1: Schema + 6 Nygard-Felder ─────────────────────────

def test_valid_adr_passes():
    """AK-1: Ein vollstaendiger ADR-Knoten (alle 6 Nygard-Felder + gueltiger status) ist gold."""
    res = qmw.validate_model(ADR_VALID)
    assert res["total"] == 1
    assert res["gold_count"] == 1, res["violations"]
    assert res["violations"] == []


def test_adr_constants_present():
    """AK-1/AK-5: Konstanten ADR_NYGARD_FIELDS (6 Felder) + ADR_STATUS_ENUM (4 Werte)."""
    assert qmw.ADR_NYGARD_FIELDS == [
        "entscheidung", "problem_kontext", "alternativen",
        "begruendung", "konsequenzen", "status",
    ]
    assert qmw.ADR_STATUS_ENUM == {
        "vorgeschlagen", "akzeptiert", "superseded", "konflikt-offen",
    }


def test_is_adr_detection():
    """AK-1: `_is_adr(body)` erkennt den type:adr-Diskriminator (Bullet- ODER YAML-Form)."""
    blocks = qmw.parse_w_blocks(ADR_VALID)
    assert qmw._is_adr(blocks[0]["body"]) is True
    # quality_scenario-Body ist KEIN adr
    sc_blocks = qmw.parse_w_blocks(SCENARIO_GOLD)
    assert qmw._is_adr(sc_blocks[0]["body"]) is False
    # plain-W ist KEIN adr
    pw_blocks = qmw.parse_w_blocks(PLAIN_W_GOLD)
    assert qmw._is_adr(pw_blocks[0]["body"]) is False


def test_missing_nygard_field_flagged():
    """AK-1: ADR ohne `begruendung` (Nygard-Pflichtfeld) -> Violation."""
    res = qmw.validate_model(ADR_MISSING_BEGRUENDUNG)
    assert res["gold_count"] == 0
    assert any(
        any("begruendung" in m for m in v["missing"]) for v in res["violations"]
    ), res["violations"]


def test_check_adr_block_returns_missing():
    """AK-1: check_adr_block listet fehlende Nygard-Felder (leer = ok)."""
    valid_block = qmw.parse_w_blocks(ADR_VALID)[0]
    assert qmw.check_adr_block(valid_block["body"]) == []
    bad_block = qmw.parse_w_blocks(ADR_MISSING_BEGRUENDUNG)[0]
    missing = qmw.check_adr_block(bad_block["body"])
    assert any("begruendung" in m for m in missing), missing


def test_adr_metadata_exposed():
    """AK-1: Der Check exponiert is_adr=True + adr_missing-Detail fuer Tooling."""
    blocks = qmw.parse_w_blocks(ADR_VALID)
    chk = qmw.check_w_block(blocks[0])
    assert chk.get("is_adr") is True
    assert chk.get("adr_missing") == []


# ───────────────────────── AK-5: Status-Enum ─────────────────────────

def test_invalid_adr_status_flagged():
    """AK-5: adr.status NICHT im 4-Enum -> Violation."""
    res = qmw.validate_model(ADR_INVALID_STATUS)
    assert res["gold_count"] == 0
    missing_all = [m for v in res["violations"] for m in v["missing"]]
    assert any("status" in m.lower() for m in missing_all), missing_all


def test_adr_status_orthogonal_to_goldform_status():
    """AK-5/W-VAL-3: Gold-Form `Status: BESTAETIGT` + `adr.status: superseded` koexistieren -> gold.

    Der Validator prueft adr.status gegen das ADR-Enum, NIE gegen CANONICAL_STATUS
    (sonst wuerde `superseded` faelschlich rot, da nicht in CANONICAL_STATUS)."""
    res = qmw.validate_model(ADR_ORTHOGONAL_STATUS)
    assert res["total"] == 1
    assert res["gold_count"] == 1, res["violations"]
    # Gold-Form-Status bleibt separat kanonisch geprueft
    chk = qmw.check_w_block(qmw.parse_w_blocks(ADR_ORTHOGONAL_STATUS)[0])
    assert chk["status_canonical"] is True
    assert chk["is_adr"] is True


def test_superseded_not_in_canonical_status():
    """AK-5-Garantie: `superseded` ist KEIN Gold-Form-Status (Beweis der Enum-Trennung)."""
    assert "superseded" not in qmw.CANONICAL_STATUS
    assert "superseded" in qmw.ADR_STATUS_ENUM


# ───────────────────────── AK-1: Additiv (Nicht-Regression) ─────────────────────────

def test_scenario_node_unaffected_by_adr_rule():
    """AK-1: ein quality_scenario-Knoten bleibt gold (adr-Regel greift nicht)."""
    res = qmw.validate_model(SCENARIO_GOLD)
    assert res["total"] == 1
    assert res["gold_count"] == 1, res["violations"]
    assert res["violations"] == []


def test_plain_w_node_unaffected_by_adr_rule():
    """AK-1: ein normaler Gold-Form-W{n}-Knoten bleibt gold (adr-Regel greift nicht)."""
    res = qmw.validate_model(PLAIN_W_GOLD)
    assert res["total"] == 1
    assert res["gold_count"] == 1
    assert res["violations"] == []


def test_cli_exit_codes_adr(tmp_path):
    """AK-1/AK-5: CLI — valider ADR-Node -> exit 0; status-invalider -> exit 1."""
    good = tmp_path / "good_adr_Model.md"
    good.write_text(ADR_VALID, encoding="utf-8")
    bad = tmp_path / "bad_adr_Model.md"
    bad.write_text(ADR_INVALID_STATUS, encoding="utf-8")
    assert qmw.main([str(good)]) == 0
    assert qmw.main([str(bad)]) == 1


# ───────────────────────── AK-11: Pre-Write-Hook nested adr-keys ─────────────────────────

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
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(proc.stdout.strip())


def test_blocks_adr_node_with_nested_sdf_mode_in_model():
    """AK-11: type:adr-Node in Model-Datei mit verschachteltem `sdf_mode:` unter adr: -> Block.

    Vor BL-382: der Guard triggerte nur auf quality_goals/quality_scenario (QDSA) -> eine
    adr-Datei (kein _manifest.md) ging ungestoert durch (Naming-Bypass moeglich).
    Nach BL-382: type:adr triggert die forbidden-field-Pruefung (content-gated)."""
    result = _run_guard(
        tool_name="Edit",
        file_path="/vault/Backlog/BL-382-x/2_Model/BL-382_Model.md",
        new_string=(
            "### W-ADR-1\n"
            "- **type:** adr\n"
            "- **id:** `BL-382.ADR-1`\n"
            "- **adr:**\n"
            "    - entscheidung: Workflow-Motor\n"
            "    - sdf_mode: heavy\n"   # << verschachteltes Verbotsfeld unter adr:
        ),
    )
    assert result["continue"] is False, (
        f"AK-11: adr-Block mit verschachteltem sdf_mode muss blockiert sein (INV-MODUS-5). Got: {result}"
    )
    assert "MODUS_WRITER" in result.get("message", ""), f"Expected guard message, got: {result}"


def test_blocks_adr_node_with_nested_recommended_modus():
    """AK-11: type:adr-Node mit verschachteltem `recommended_modus:` -> Block."""
    result = _run_guard(
        tool_name="Write",
        file_path="/vault/Backlog/BL-382-x/2_Model/BL-382_Model.md",
        content=(
            "### W-ADR-2\n"
            "type: adr\n"
            "adr:\n"
            "  entscheidung: Schwellen-Mechanik\n"
            "  recommended_modus: M3\n"   # << Verbotskey
        ),
    )
    assert result["continue"] is False, (
        f"AK-11: adr-Block mit recommended_modus muss blockiert sein (INV-MODUS-5). Got: {result}"
    )
    assert "MODUS_WRITER" in result.get("message", "")


def test_allows_clean_adr_node():
    """AK-11: ein sauberer type:adr-Node (kein Modus-Feld) -> passt durch (kein false-positive)."""
    result = _run_guard(
        tool_name="Edit",
        file_path="/vault/Backlog/BL-382-x/2_Model/BL-382_Model.md",
        new_string=(
            "### W-ADR-3\n"
            "- **type:** adr\n"
            "- **id:** `BL-382.ADR-3`\n"
            "- **adr:**\n"
            "    - entscheidung: Status-Lebenszyklus 4-Enum\n"
            "    - problem_kontext: Widersprueche maschinen-sichtbar machen\n"
            "    - alternativen:\n"
            "        - option: Freitext-Status\n"
            "          abgelehnt_weil: nicht maschinell pruefbar\n"
            "    - begruendung: geschlossenes Enum macht Konflikte abfragbar\n"
            "    - konsequenzen: Validator kann status pruefen\n"
            "    - status: akzeptiert\n"
        ),
    )
    assert result["continue"] is True, (
        f"AK-11: sauberer adr-Node (ohne Modus-Feld) muss passieren (kein Naming-Bypass-Verdacht). Got: {result}"
    )


def test_adr_hook_does_not_globally_scan_non_adr():
    """AK-11-Additiv-Schutz: Nicht-ADR-Nicht-QDSA-Nicht-Manifest-Datei mit forbidden_key
    passiert weiterhin (BL-382-Erweiterung ist type:adr-getriggert, nicht global)."""
    result = _run_guard(
        tool_name="Edit",
        file_path="/some/path/_berater_outputs.md",
        new_string="recommended_modus: M3\nsdf_mode_hint: heavy\n",
    )
    assert result["continue"] is True, (
        f"AK-11: Nicht-ADR-Nicht-QDSA-Nicht-Manifest-Datei muss weiterhin passieren. Got: {result}"
    )


# ═══════════════════════ batch_PL3 (AK-7 / AK-8) Fixtures ═══════════════════════
# Cross-ADR-Checks operieren auf der NODE-LISTE eines ganzen Models (mehrere
# `### W-ADR-{n}`-Bloecke). Helfer: qmw.parse_w_blocks(content) -> [{w_id,title,body}].

def _adr(node_id, status, *, supersedes_into=None, baustein=None,
         entscheidung="Eine Entscheidung", wid=None):
    """Minimaler valider ADR-Block-Generator fuer die Ketten-/Konflikt-Fixtures.

    node_id          -> `- **id:** {node_id}`  (eigene ADR-ID, z.B. BL-382.ADR-1)
    status           -> adr.status
    supersedes_into  -> adr.superseded_by-Ziel (diese ADR wurde von jenem abgeloest)
    baustein         -> adr.betrifft_baustein (einzelner Baustein-Ref oder None)
    entscheidung     -> adr.entscheidung (fuer Konflikt-Detektion)
    """
    head = wid or ("W-ADR-" + node_id.rsplit(".ADR-", 1)[-1])
    lines = [
        "### %s · %s" % (head, entscheidung),
        "- **text:** Diese Entscheidung wurde getroffen.",
        "- **Status:** BESTAETIGT",
        "- **source:** `Spec: BL-382_Spec.md`",
        "- **Quelle:** `[[3_Spec/BL-382_Spec.md#5]]`",
        "- **Edge zu:** W-DOM-1",
        "- **type:** adr",
        "- **id:** `%s`" % node_id,
        "- **adr:**",
        "    - entscheidung: %s" % entscheidung,
        "    - problem_kontext: Kontext",
        "    - alternativen:",
        "        - option: Andere Wahl",
        "          abgelehnt_weil: Grund",
        "    - begruendung: Begruendung",
        "    - konsequenzen: Folgen",
        "    - status: %s" % status,
    ]
    if baustein is not None:
        lines.append('    - betrifft_baustein: ["%s"]' % baustein)
    if supersedes_into is not None:
        lines.append("    - superseded_by: %s" % supersedes_into)
    return "\n".join(lines) + "\n"


# ───────────────────────── AK-7: superseded-Ketten-Konsistenz ─────────────────────────

def test_valid_linear_chain_one_head_passes():
    """AK-7: lineare zyklenfreie Kette ADR-1->ADR-2->ADR-3 mit GENAU EINEM aktiven Kopf
    (ADR-3 akzeptiert, Vorgaenger superseded) -> keine Violation."""
    content = (
        _adr("BL-382.ADR-1", "superseded", supersedes_into="BL-382.ADR-2")
        + _adr("BL-382.ADR-2", "superseded", supersedes_into="BL-382.ADR-3")
        + _adr("BL-382.ADR-3", "akzeptiert")
    )
    nodes = qmw.parse_w_blocks(content)
    assert qmw.check_adr_superseded_chains(nodes) == []


def test_cyclic_chain_flagged():
    """AK-7: zyklische superseded_by-Kette ADR-1->ADR-2->ADR-1 -> Zyklus-Violation."""
    content = (
        _adr("BL-382.ADR-1", "superseded", supersedes_into="BL-382.ADR-2")
        + _adr("BL-382.ADR-2", "superseded", supersedes_into="BL-382.ADR-1")
    )
    nodes = qmw.parse_w_blocks(content)
    viol = qmw.check_adr_superseded_chains(nodes)
    assert any("cycle" in v.lower() for v in viol), viol


def test_two_active_heads_flagged():
    """AK-7: zwei aktive Koepfe in EINER Kette (ADR-1->ADR-2, ADR-1 aber NICHT superseded)
    -> Violation 'mehr als ein aktiver Kopf' / fehlender superseded-Status des Vorgaengers."""
    content = (
        # ADR-1 zeigt auf ADR-2 (abgeloest), traegt aber faelschlich `akzeptiert`.
        _adr("BL-382.ADR-1", "akzeptiert", supersedes_into="BL-382.ADR-2")
        + _adr("BL-382.ADR-2", "akzeptiert")
    )
    nodes = qmw.parse_w_blocks(content)
    viol = qmw.check_adr_superseded_chains(nodes)
    assert any(("head" in v.lower()) or ("superseded" in v.lower()) for v in viol), viol


def test_chain_with_no_active_head_flagged():
    """AK-7: Kette in der ALLE Knoten superseded sind (kein aktiver Kopf) -> Violation."""
    content = (
        _adr("BL-382.ADR-1", "superseded", supersedes_into="BL-382.ADR-2")
        + _adr("BL-382.ADR-2", "superseded")   # << Kopf ohne Nachfolger, aber superseded
    )
    nodes = qmw.parse_w_blocks(content)
    viol = qmw.check_adr_superseded_chains(nodes)
    assert any("head" in v.lower() for v in viol), viol


def test_independent_chains_each_one_head_passes():
    """AK-7: zwei UNABHAENGIGE valide Ketten -> keine Violation (Komponenten getrennt)."""
    content = (
        _adr("BL-382.ADR-1", "superseded", supersedes_into="BL-382.ADR-2")
        + _adr("BL-382.ADR-2", "akzeptiert")
        + _adr("BL-382.ADR-5", "superseded", supersedes_into="BL-382.ADR-6")
        + _adr("BL-382.ADR-6", "akzeptiert")
    )
    nodes = qmw.parse_w_blocks(content)
    assert qmw.check_adr_superseded_chains(nodes) == []


def test_single_active_adr_no_chain_passes():
    """AK-7: eine einzelne aktive ADR ohne superseded_by ist eine triviale 1-Knoten-Kette -> ok."""
    content = _adr("BL-382.ADR-1", "akzeptiert")
    nodes = qmw.parse_w_blocks(content)
    assert qmw.check_adr_superseded_chains(nodes) == []


def test_chain_check_ignores_non_adr_nodes():
    """AK-7: plain-W + quality_scenario-Knoten werden ignoriert (kein false-positive)."""
    content = PLAIN_W_GOLD + SCENARIO_GOLD + _adr("BL-382.ADR-1", "akzeptiert")
    nodes = qmw.parse_w_blocks(content)
    assert qmw.check_adr_superseded_chains(nodes) == []


def test_chain_dangling_superseded_target_flagged():
    """AK-7-Robustheit: superseded_by zeigt auf eine NICHT-existente ADR-ID -> Violation
    (dangling edge — die Kette ist nicht aufloesbar, kein stiller Durchlass)."""
    content = _adr("BL-382.ADR-1", "superseded", supersedes_into="BL-999.ADR-7")
    nodes = qmw.parse_w_blocks(content)
    viol = qmw.check_adr_superseded_chains(nodes)
    assert any("dangling" in v.lower() or "BL-999.ADR-7" in v for v in viol), viol


# ───────────────────────── AK-8 Stufe-1: deterministischer Konflikt-Detektor ─────────────────────────

def test_conflict_two_active_same_baustein_detected():
    """AK-8 Stufe-1: zwei nicht-superseded `akzeptiert`-ADRs am SELBEN Baustein mit
    UNTERSCHIEDLICHER entscheidung -> Kandidat erkannt (deterministischer Vorfilter)."""
    content = (
        _adr("BL-382.ADR-1", "akzeptiert", baustein="dispatch_implement.js",
             entscheidung="Workflow-Motor als Dispatch")
        + _adr("BL-382.ADR-2", "akzeptiert", baustein="dispatch_implement.js",
               entscheidung="Mega-Worker beibehalten")
    )
    nodes = qmw.parse_w_blocks(content)
    cand = qmw.detect_adr_conflicts(nodes)
    assert len(cand) == 1, cand
    ids = set(cand[0]["adr_ids"])
    assert ids == {"BL-382.ADR-1", "BL-382.ADR-2"}, cand
    assert cand[0]["baustein"] == "dispatch_implement.js", cand


def test_conflict_none_when_different_baustein():
    """AK-8 Stufe-1: zwei akzeptierte ADRs an VERSCHIEDENEN Bausteinen -> kein Kandidat."""
    content = (
        _adr("BL-382.ADR-1", "akzeptiert", baustein="dispatch_implement.js")
        + _adr("BL-382.ADR-2", "akzeptiert", baustein="quality_model_wform.py")
    )
    nodes = qmw.parse_w_blocks(content)
    assert qmw.detect_adr_conflicts(nodes) == []


def test_conflict_none_when_one_superseded():
    """AK-8 Stufe-1: ist eine der beiden ADRs superseded -> kein aktiver Konflikt-Kandidat."""
    content = (
        _adr("BL-382.ADR-1", "superseded", supersedes_into="BL-382.ADR-2",
             baustein="dispatch_implement.js", entscheidung="Alte Wahl")
        + _adr("BL-382.ADR-2", "akzeptiert", baustein="dispatch_implement.js",
               entscheidung="Neue Wahl")
    )
    nodes = qmw.parse_w_blocks(content)
    assert qmw.detect_adr_conflicts(nodes) == []


def test_conflict_none_when_same_entscheidung():
    """AK-8 Stufe-1: zwei akzeptierte ADRs am selben Baustein mit IDENTISCHER entscheidung
    -> kein Widerspruch-Kandidat (Stufe-1 filtert gleiche Entscheidung deterministisch raus)."""
    content = (
        _adr("BL-382.ADR-1", "akzeptiert", baustein="dispatch_implement.js",
             entscheidung="Workflow-Motor als Dispatch")
        + _adr("BL-382.ADR-2", "akzeptiert", baustein="dispatch_implement.js",
               entscheidung="Workflow-Motor als Dispatch")
    )
    nodes = qmw.parse_w_blocks(content)
    assert qmw.detect_adr_conflicts(nodes) == []


def test_conflict_none_when_no_baustein():
    """AK-8 Stufe-1: ADRs ohne betrifft_baustein (Luecken-Marker-Fall) -> kein Kandidat
    (kein gemeinsamer Baustein = keine deterministische Ueberlappung)."""
    content = (
        _adr("BL-382.ADR-1", "akzeptiert", entscheidung="A")
        + _adr("BL-382.ADR-2", "akzeptiert", entscheidung="B")
    )
    nodes = qmw.parse_w_blocks(content)
    assert qmw.detect_adr_conflicts(nodes) == []


def test_conflict_ignores_vorgeschlagen():
    """AK-8 Stufe-1: nur `akzeptiert` zaehlt als aktiv-im-Konflikt; `vorgeschlagen` (noch nicht
    entschieden) loest keinen Kandidaten aus (W-STAT-3: zwei AKZEPTIERTE widersprechen sich)."""
    content = (
        _adr("BL-382.ADR-1", "akzeptiert", baustein="x.py", entscheidung="A")
        + _adr("BL-382.ADR-2", "vorgeschlagen", baustein="x.py", entscheidung="B")
    )
    nodes = qmw.parse_w_blocks(content)
    assert qmw.detect_adr_conflicts(nodes) == []


# ═══════════════════════ batch_PL6 (AK-6 / B-3): Nicht-Leer-Inhaltspruefung ═══════════════════════
# Die VALIDATOR-HAERTUNG: die 6 Nygard-Pflichtfelder muessen nicht nur PRAESENT
# (`_key_present`) sondern NICHT-LEER sein. `alternativen` = nicht-leere Liste (nicht
# `[]`/leer); `begruendung`/`entscheidung`/`problem_kontext`/`konsequenzen` = nicht-leerer
# String (nicht blank/`""`). Goodhart-Bezug (AK-4): begruendung nicht-leer = strukturelle
# Haelfte des Goodhart-Guards. Additiv, exit-Semantik konsistent. Diese Pruefung geht ueber
# `_key_present` (nur Anwesenheit) hinaus (B-3-Falsifikationskriterium W-VAL-2 adressiert).
#
# Bauplan-Helfer: ein vollstaendiger ADR-Block mit ueberschreibbaren Einzelfeldern, damit
# je-Feld ein Leer-Wert injiziert werden kann ohne die anderen Felder zu beruehren.

def _adr_fields(
    *, node_id="BL-382.ADR-7", status="akzeptiert",
    entscheidung="Workflow-Motor als deterministischer Dispatch",
    problem_kontext="Mega-Worker-Fragilitaet bei interpretiertem Skill-Pseudocode",
    alternativen_block=(
        "    - alternativen:\n"
        "        - option: Mega-Worker beibehalten\n"
        "          abgelehnt_weil: Step-Buendelung strukturell moeglich\n"
    ),
    begruendung="Step-Skeleton aus feststehendem Modus schliesst Self-Assign aus",
    konsequenzen="Determinismus gewonnen, Engine-Komplexitaet steigt",
):
    """Voll-nicht-leerer ADR-Block-Generator; jedes Skalar-Feld einzeln ueberschreibbar
    (Leer-Wert = '' injizieren), alternativen als ganzer Block ersetzbar."""
    head = "W-ADR-" + node_id.rsplit(".ADR-", 1)[-1]
    return (
        "### %s · %s\n" % (head, entscheidung or "ADR")
        + "- **text:** Diese Entscheidung wurde getroffen.\n"
        + "- **Status:** BESTAETIGT\n"
        + "- **source:** `Spec: BL-382_Spec.md Sec 5`\n"
        + "- **Quelle:** `[[3_Spec/BL-382_Spec.md#5]]`\n"
        + "- **Edge zu:** W-DOM-1\n"
        + "- **type:** adr\n"
        + "- **id:** `%s`\n" % node_id
        + "- **adr:**\n"
        + "    - entscheidung: %s\n" % entscheidung
        + "    - problem_kontext: %s\n" % problem_kontext
        + alternativen_block
        + "    - begruendung: %s\n" % begruendung
        + "    - konsequenzen: %s\n" % konsequenzen
        + "    - status: %s\n" % status
    )


def test_full_nonempty_adr_is_gold():
    """B-3-Basis: ein ADR mit ALLEN 6 Feldern valide UND nicht-leer -> gold (exit 0).
    Stellt sicher, dass die Haertung den Voll-Gold-Fall NICHT faelschlich rot macht."""
    res = qmw.validate_model(_adr_fields())
    assert res["total"] == 1
    assert res["gold_count"] == 1, res["violations"]
    assert res["violations"] == []
    assert qmw.check_adr_block(qmw.parse_w_blocks(_adr_fields())[0]["body"]) == []


def test_empty_begruendung_flagged():
    """B-3 (Goodhart-Haelfte, AK-4/AK-6): begruendung PRAESENT aber LEER -> Violation.
    Vor der Haertung passte das (`_key_present` sieht nur Anwesenheit)."""
    content = _adr_fields(begruendung="")
    missing = qmw.check_adr_block(qmw.parse_w_blocks(content)[0]["body"])
    assert any("begruendung" in m for m in missing), missing
    assert qmw.validate_model(content)["gold_count"] == 0


def test_blank_begruendung_flagged():
    """B-3: begruendung nur aus Whitespace -> Violation (blank zaehlt als leer)."""
    content = _adr_fields(begruendung="   ")
    missing = qmw.check_adr_block(qmw.parse_w_blocks(content)[0]["body"])
    assert any("begruendung" in m for m in missing), missing


def test_empty_alternativen_list_flagged():
    """B-3 (AK-3/AK-6): `alternativen: []` (leere Liste) -> Violation.
    Nygards 'Warum nicht anders?' braucht mind. einen erwogenen Eintrag."""
    content = _adr_fields(alternativen_block="    - alternativen: []\n")
    missing = qmw.check_adr_block(qmw.parse_w_blocks(content)[0]["body"])
    assert any("alternativen" in m for m in missing), missing
    assert qmw.validate_model(content)["gold_count"] == 0


def test_blank_alternativen_scalar_flagged():
    """B-3: `alternativen:` ohne Wert (blank Skalar, keine Listen-Eintraege) -> Violation."""
    content = _adr_fields(alternativen_block="    - alternativen:\n")
    missing = qmw.check_adr_block(qmw.parse_w_blocks(content)[0]["body"])
    assert any("alternativen" in m for m in missing), missing


def test_empty_entscheidung_flagged():
    """B-3: entscheidung PRAESENT aber LEER -> Violation (nicht-leer-Pflicht fuer String-Felder)."""
    content = _adr_fields(entscheidung="")
    missing = qmw.check_adr_block(qmw.parse_w_blocks(content)[0]["body"])
    assert any("entscheidung" in m for m in missing), missing


def test_empty_problem_kontext_flagged():
    """B-3: problem_kontext PRAESENT aber LEER -> Violation."""
    content = _adr_fields(problem_kontext="")
    missing = qmw.check_adr_block(qmw.parse_w_blocks(content)[0]["body"])
    assert any("problem_kontext" in m for m in missing), missing


def test_empty_konsequenzen_flagged():
    """B-3: konsequenzen PRAESENT aber LEER -> Violation."""
    content = _adr_fields(konsequenzen="")
    missing = qmw.check_adr_block(qmw.parse_w_blocks(content)[0]["body"])
    assert any("konsequenzen" in m for m in missing), missing


def test_existing_valid_fixtures_stay_gold_under_hardening():
    """B-3-Regression: die bestehenden batch_PL1-Voll-Fixtures (ADR_VALID / ADR_ORTHOGONAL_STATUS)
    haben nicht-leere Felder und MUESSEN unter der Haertung gold bleiben (kein false-positive)."""
    assert qmw.validate_model(ADR_VALID)["gold_count"] == 1
    assert qmw.validate_model(ADR_ORTHOGONAL_STATUS)["gold_count"] == 1


def test_full_adr_validator_coherent_whole():
    """AK-6 Integration: der VOLLE ADR-Validator (Schema + Status-Enum + Kanten-ID +
    Nicht-Leer) greift als kohaerentes Ganzes — ein gold-ADR (alle Felder valide+nicht-leer)
    -> exit 0; jede einzelne Leer-Verletzung -> exit 1 (CLI-Vertrag)."""
    import tempfile
    gold = _adr_fields()
    with tempfile.TemporaryDirectory() as d:
        gp = Path(d) / "gold_adr_Model.md"
        gp.write_text(gold, encoding="utf-8")
        assert qmw.main([str(gp)]) == 0
        for kw in ("begruendung", "entscheidung", "konsequenzen", "problem_kontext"):
            bad = _adr_fields(**{kw: ""})
            bp = Path(d) / ("bad_%s_Model.md" % kw)
            bp.write_text(bad, encoding="utf-8")
            assert qmw.main([str(bp)]) == 1, kw
        # leere alternativen-Liste ebenfalls exit 1
        ba = _adr_fields(alternativen_block="    - alternativen: []\n")
        bap = Path(d) / "bad_alternativen_Model.md"
        bap.write_text(ba, encoding="utf-8")
        assert qmw.main([str(bap)]) == 1
