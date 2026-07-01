"""
test_drift_eval.py — BL-383 batch_PL5 (AK-2): Drift-Eval (Impl<->Entwurf, NACH Bau).

Nach dem Bau prueft Drift-Eval Konformitaet entlang ZWEIER Bezuege (OQ-2, W-DRIFT-1):
  (a) gegen `adr`-Nodes (BL-382) — widerspricht die Implementierung einer akzeptierten
      Entscheidung? (semantische Verletzung; der WIDERSPRUCHS-URTEIL selbst ist ROTE Zone)
  (b) gegen die Bausteinsicht (arc42 §5 / dependencyAnalyzer file_index) — verletzt sie die
      geplante Komponenten-Struktur? (topologische Verletzung, deterministisch pruefbar)
Disjunkte Verletzungs-Klassen (semantisch vs. topologisch), keine Redundanz.

Der Drift-Befund traegt eine `betrifft_baustein`-Referenz (BL-382 AK-3-Kante / W-EDGE-1),
sodass Drift baustein-verankert maschinenlesbar ist. eval_kind=drift_eval (AK-4).

Anknuepfung (W-LOC-2, PL3 WO-Doktrin, markdown_uncoverable): Drift-Eval ist eine ACHSEN-
Erweiterung von `_AC_orchestrate` (post-I, AC-SUMMARY) + `_PostBatch_ArchConformance`
(Batch, ESCALATION_QUEUE) — KEIN neues Kommando. Hier testbar: das Befund-SCHEMA + der
`betrifft_baustein`-Anker + der topologische file_index-Abgleich. Die semantische ADR-
Widerspruchs-Erkennung (Achse a) ist agentisch (ROTE Zone, forward_verify).

Scope batch_PL5 (AK-2): die DETERMINISTISCHE Drift-Detektor-Logik (Bausteinsicht-Struktur-
Abgleich gegen file_index + betrifft_baustein-Anker am Befund + drift_eval eval_finding-
Output). KEIN modus-Write (INV-MODUS-1), kein neuer Truth-Node-Typ (W-DOM-1).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

import quality_model_wform as qmw  # noqa: E402
import drift_eval as dr  # noqa: E402

SCRIPT_DIR = Path(__file__).parent.absolute()


# ───────────────────────── Fixtures: BL-382 adr-Nodes mit betrifft_baustein ─────────────────────────

# Ein akzeptierter ADR, der die Komponente-A betrifft (Drift-Bezug, semantische Achse a).
_ADR_NODE = (
    "### W-ADR-1 · Nutze Repository-Pattern fuer Persistenz\n"
    "- **text:** Persistenz laeuft ausschliesslich ueber Repositories.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Repo:y.py:2`\n"
    "- **Quelle:** `[[c.md#d]]`\n"
    "- **Edge zu:** W-DOM-1\n"
    "- **type:** adr\n"
    "- **id:** `BL-382.ADR-1`\n"
    "- **adr:**\n"
    "    - entscheidung: Persistenz nur ueber Repository-Schicht\n"
    "    - problem_kontext: direkte DB-Zugriffe streuten\n"
    "    - alternativen: [Active-Record]\n"
    "    - begruendung: Testbarkeit + Entkopplung\n"
    "    - konsequenzen: Repository-Boilerplate\n"
    "    - status: akzeptiert\n"
    "    - betrifft_baustein: [PersistenzSchicht]\n"
)

_PLAIN_AND_QS = (
    "### W-DOM-2 · Plain\n"
    "- **text:** Eine normale Wahrheit.\n"
    "- **Status:** BESTAETIGT\n"
    "- **source:** `Repo:x.py:1`\n"
    "- **Quelle:** `[[a.md#b]]`\n"
    "- **Edge zu:** W-DOM-1\n"
)


# ═══════════════════════════════════════════════════════════════════════════
# AK-2 — Bausteinsicht-Struktur-Check (topologisch, gegen file_index, Achse b)
# ═══════════════════════════════════════════════════════════════════════════

def test_geplante_komponente_ohne_drift_kein_befund():
    """AK-2 (Achse b): eine Datei, die zu ihrem GEPLANTEN Baustein gehoert (file_index-
    konform), erzeugt KEINEN Struktur-Drift-Befund."""
    file_index = {
        "PersistenzSchicht": ["src/persistence/repo.py"],
        "DomainSchicht": ["src/domain/model.py"],
    }
    drift = dr.detect_structural_drift(
        changed_files=["src/persistence/repo.py"],
        file_index=file_index,
    )
    assert drift == [], drift


def test_datei_ausserhalb_geplanter_bausteine_ist_struktur_drift():
    """AK-2 (Achse b, topologisch): eine geaenderte Datei, die in KEINEM geplanten Baustein
    des file_index liegt -> Struktur-Drift-Kandidat (Bausteinsicht-Verletzung)."""
    file_index = {
        "PersistenzSchicht": ["src/persistence/repo.py"],
    }
    drift = dr.detect_structural_drift(
        changed_files=["src/persistence/repo.py", "src/rogue/sneaky.py"],
        file_index=file_index,
    )
    assert len(drift) == 1, drift
    assert drift[0]["datei"] == "src/rogue/sneaky.py"


def test_leerer_file_index_degradiert_graceful():
    """AK-2 (Graceful, W-LOC-1-Spiegel): ohne file_index (keine Bausteinsicht zur Bauzeit)
    -> kein Struktur-Drift-Hard-Fail (leere Liste, auf Laufzeit/Urteil vertagt)."""
    assert dr.detect_structural_drift(changed_files=["x.py"], file_index={}) == []
    assert dr.detect_structural_drift(changed_files=["x.py"], file_index=None) == []


# ═══════════════════════════════════════════════════════════════════════════
# AK-2 — Drift-Befund traegt betrifft_baustein-Anker (BL-382 AK-3-Kante, T-11)
# ═══════════════════════════════════════════════════════════════════════════

def test_drift_finding_carries_betrifft_baustein_anchor():
    """AK-2 (T-11): ein Drift-Befund gegen einen ADR traegt dessen `betrifft_baustein`-ID
    als Anker (baustein-verankert maschinenlesbar, BL-382 W-EDGE-1)."""
    findings = dr.drift_findings_against_adrs(
        _ADR_NODE,
        # Impl widerspricht ADR-1 an der PersistenzSchicht (semantischer Drift-Bezug, von
        # einem upstream-Urteil/forward_verify gemeldet; hier als Input gegeben).
        adr_violations={"BL-382.ADR-1": "direkter DB-Zugriff in repo.py umgeht Repository"},
        bl_slug="BL-383",
    )
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["eval_kind"] == "drift_eval"
    assert f["ref_node"] == "BL-382.ADR-1"
    # Der Befund traegt die betrifft_baustein-Referenz des ADR (T-11-Anker).
    assert "PersistenzSchicht" in str(f.get("betrifft_baustein")), f


def test_no_adr_violation_yields_no_drift_finding():
    """AK-2: ohne gemeldete ADR-Verletzung -> KEIN Drift-Befund (kein false-positive)."""
    findings = dr.drift_findings_against_adrs(
        _ADR_NODE, adr_violations={}, bl_slug="BL-383",
    )
    assert findings == []


def test_structural_drift_finding_carries_baustein_anchor():
    """AK-2 (Achse b -> Befund): ein Struktur-Drift-Befund traegt den verletzten/erwarteten
    Baustein-Bezug (betrifft_baustein), sodass auch topologischer Drift verankert ist."""
    file_index = {"PersistenzSchicht": ["src/persistence/repo.py"]}
    findings = dr.structural_drift_findings(
        changed_files=["src/rogue/sneaky.py"],
        file_index=file_index,
        bl_slug="BL-383",
    )
    assert len(findings) == 1, findings
    f = findings[0]
    assert f["eval_kind"] == "drift_eval"
    assert f["risk_class"] in qmw.RISK_CLASS_ENUM
    assert f.get("betrifft_baustein") is not None


# ═══════════════════════════════════════════════════════════════════════════
# AK-2 — Risk-Klassen-Zuordnung (Commission semantisch, Omission/Commission topologisch)
# ═══════════════════════════════════════════════════════════════════════════

def test_adr_contradiction_is_commission():
    """AK-2 (W-OUT-1): ein ADR-Widerspruch (Impl tut etwas Falsches gegen akzeptierte
    Entscheidung) ist risk_class=Commission (etwas Schaedliches ist da)."""
    findings = dr.drift_findings_against_adrs(
        _ADR_NODE,
        adr_violations={"BL-382.ADR-1": "umgeht Repository"},
        bl_slug="BL-383",
    )
    assert findings[0]["risk_class"] == "Commission"


# ═══════════════════════════════════════════════════════════════════════════
# AK-2 — Output = valide drift_eval eval_finding-Records (PL1-Interop)
# ═══════════════════════════════════════════════════════════════════════════

def test_drift_findings_are_valid_eval_finding_records():
    """AK-2 x AK-4-Interop: jeder Drift-Befund ist ein PL1-schema-valider eval_finding-
    Record (als W-Block gerendert -> gold gegen den PL1-Validator). drift_eval ist von der
    AK-7-Messbarkeits-Klammer exempt (kein response_measure-Bezug)."""
    adr_findings = dr.drift_findings_against_adrs(
        _ADR_NODE, adr_violations={"BL-382.ADR-1": "umgeht Repository"}, bl_slug="BL-383",
    )
    struct_findings = dr.structural_drift_findings(
        changed_files=["src/rogue/sneaky.py"],
        file_index={"PersistenzSchicht": ["src/persistence/repo.py"]},
        bl_slug="BL-383",
    )
    findings = adr_findings + struct_findings
    assert findings
    md = dr.render_findings_as_w_blocks(findings)
    res = qmw.validate_model(md)
    assert res["total"] == len(findings)
    assert res["gold_count"] == len(findings), res["violations"]


def test_drift_finding_has_no_metric_threshold():
    """AK-2 x AK-7-Scope: ein drift_eval-Befund traegt KEINEN metric/threshold-Bezug
    (Messbarkeits-Klammer greift NUR fuer design_eval) — er bleibt trotzdem gold."""
    findings = dr.drift_findings_against_adrs(
        _ADR_NODE, adr_violations={"BL-382.ADR-1": "umgeht Repository"}, bl_slug="BL-383",
    )
    assert "metric" not in findings[0]
    assert "threshold" not in findings[0]


# ═══════════════════════════════════════════════════════════════════════════
# AK-2 — ADR-Node-Konsum per ID (read-only, baut auf eval_id_consume/qmw)
# ═══════════════════════════════════════════════════════════════════════════

def test_load_adr_nodes_with_betrifft_baustein():
    """AK-2: Drift-Eval liest die adr-Nodes per ID inkl. betrifft_baustein (read-only Konsum,
    Single-Source ueber quality_model_wform). Nicht-ADR-Knoten werden ignoriert."""
    index = dr.load_adr_nodes(_ADR_NODE + _PLAIN_AND_QS)
    assert "BL-382.ADR-1" in index
    assert "PersistenzSchicht" in index["BL-382.ADR-1"]["betrifft_baustein"]
    assert index["BL-382.ADR-1"]["status"] == "akzeptiert"


# ═══════════════════════════════════════════════════════════════════════════
# AK-2 x INV-MODUS-1/5 — kein Modus-/Verbots-Feld im Drift-Befund
# ═══════════════════════════════════════════════════════════════════════════

def test_no_modus_field_in_drift_findings():
    """AK-2 x INV-MODUS-1/5: Drift-Befunde tragen NIE ein Modus-/Verbots-Feld (AK-9)."""
    forbidden = {"recommended_modus", "sdf_mode", "sdf_mode_hint",
                 "expected_sdf_mode", "mode_recommendation", "modus"}
    findings = dr.drift_findings_against_adrs(
        _ADR_NODE, adr_violations={"BL-382.ADR-1": "umgeht Repository"}, bl_slug="BL-383",
    ) + dr.structural_drift_findings(
        changed_files=["src/rogue/x.py"],
        file_index={"A": ["src/a/y.py"]}, bl_slug="BL-383",
    )
    for f in findings:
        assert not (set(f.keys()) & forbidden), f


# ═══════════════════════════════════════════════════════════════════════════
# AK-2 — CLI-Smoke (read-only)
# ═══════════════════════════════════════════════════════════════════════════

def test_cli_runs_on_model_file(tmp_path):
    """AK-2: CLI-Smoke — drift_eval.py <Model.md> liest adr-Nodes read-only, exit 0
    (Graceful bei keinem ADR / keiner Verletzung); usage -> exit 2."""
    model = tmp_path / "ADR_Model.md"
    model.write_text(_ADR_NODE, encoding="utf-8")
    assert dr.main([str(model)]) == 0
    empty = tmp_path / "Plain_Model.md"
    empty.write_text(_PLAIN_AND_QS, encoding="utf-8")
    assert dr.main([str(empty)]) == 0
    assert dr.main([]) == 2  # Usage
