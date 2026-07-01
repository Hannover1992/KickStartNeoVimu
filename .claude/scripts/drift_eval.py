"""
drift_eval.py — BL-383 batch_PL5 (AK-2): Drift-Eval (Impl<->Entwurf, NACH Bau).

Nach dem Bau prueft Drift-Eval Konformitaet entlang ZWEIER Bezuege (OQ-2, W-DRIFT-1) —
disjunkte Verletzungs-Klassen, keine Redundanz:
  (a) gegen `adr`-Nodes (BL-382) — widerspricht die Implementierung einer `akzeptiert`-
      Entscheidung? (SEMANTISCHE Verletzung). Das WIDERSPRUCHS-URTEIL selbst ist eine
      ROTE Zone (AK-8, `_eval_berater_drifturteil`, agentisch/forward_verify) — hier kommt
      es als adr_violations-Map (ADR-ID -> Verletzungs-Text) INPUT an (kein Urteil im Script).
  (b) gegen die Bausteinsicht (arc42 §5 / `dependencyAnalyzer` file_index) — verletzt die
      Impl die geplante Komponenten-Struktur? (TOPOLOGISCHE Verletzung) — DETERMINISTISCH
      (detect_structural_drift: geaenderte Datei in keinem geplanten Baustein).

Jeder Drift-Befund traegt eine `betrifft_baustein`-Referenz (BL-382 W-EDGE-1 / AK-3-Kante),
sodass Drift baustein-verankert maschinenlesbar ist (T-11). Output = drift_eval eval_finding-
Records (PL1-Schema, AK-4); drift_eval ist von der AK-7-Messbarkeits-Klammer exempt.

Anknuepfung (W-LOC-2, WO-Doktrin PL3, markdown_uncoverable): Drift-Eval ist eine ACHSEN-
Erweiterung von `_AC_orchestrate` (post-I, AC-SUMMARY + ac_*-Felder) + `_PostBatch_Arch
Conformance` (Batch, ARCHITECT_ESCALATION_QUEUE) — KEIN neues Kommando (F17). Die AC-/
PostBatch-Worker liefern die adr_violations (semantisches Urteil) + den file_index; dieses
Script traegt die DETERMINISTISCHE Detektor-/Befund-Logik.

read-only Konsum der adr-Nodes (Single-Source ueber quality_model_wform). KEIN Modus-Write
(INV-MODUS-1), KEIN neuer Truth-Node-Typ (W-DOM-1).

CLI: `py drift_eval.py <Model.md> [...]`  (read-only; listet die adr-Nodes je Datei).
exit 0 = Lauf ok (auch: keine ADRs/keine Verletzung = Graceful), 2 = Usage-Fehler.
"""

import sys

import quality_model_wform as qmw


# ── read-only ADR-Node-Konsum (per ID, inkl. betrifft_baustein) ──────────────

def load_adr_nodes(content):
    """AK-2 (read-only Konsum): parst ein Model und liefert die BL-382 adr-Nodes als
    {id: {"w_id", "status", "betrifft_baustein": [...], "entscheidung"}}. Single-Source
    ueber die quality_model_wform-Reader (Konsum + Produktion divergieren nie). Nicht-ADR-
    Knoten werden ignoriert. KEIN Schema-Edit, KEIN Write (W-DOM-1)."""
    index = {}
    for block in qmw.parse_w_blocks(content):
        body = block["body"]
        if not qmw._is_adr(body):
            continue
        node_id = qmw._adr_node_id(body) or block["w_id"]
        index[node_id] = {
            "w_id": block["w_id"],
            "status": qmw._adr_status_value(body),
            "betrifft_baustein": qmw._adr_edge_ids(body, "betrifft_baustein"),
            "entscheidung": qmw._adr_field_value(body, "entscheidung"),
        }
    return index


# ── Achse b: Bausteinsicht-Struktur-Drift (topologisch, gegen file_index) ─────

def detect_structural_drift(changed_files, file_index):
    """AK-2 (Achse b, deterministisch): findet geaenderte Dateien, die in KEINEM geplanten
    Baustein des `file_index` (arc42 §5 Bausteinsicht / dependencyAnalyzer) liegen —
    Struktur-Drift-Kandidaten (Bausteinsicht-Verletzung, topologisch).

    `file_index`: {baustein_name: [datei, ...]} (die geplante Komponenten->Datei-Zuordnung).
    -> Liste von {datei} fuer jede geaenderte Datei ausserhalb der geplanten Bausteine.
    Graceful (W-LOC-1-Spiegel): ohne file_index (keine Bausteinsicht zur Bauzeit) -> []
    (kein Hard-Fail; auf Laufzeit/Urteil vertagt)."""
    if not file_index:
        return []
    planned = set()
    for files in file_index.values():
        planned.update(files or [])
    drift = []
    for datei in (changed_files or []):
        if datei not in planned:
            drift.append({"datei": datei})
    return drift


# ── Befund-Bau (drift_eval eval_finding, AK-4-Interop) ────────────────────────

def _finding(bl_slug, idx, ref_node, risk_class, severity, befund, cost, benefit,
             suggested_action, betrifft_baustein):
    """Baut EINEN drift_eval eval_finding-Record (PL1-Schema). Traegt den `betrifft_baustein`-
    Anker (T-11, baustein-verankert) und KEIN Modus-/Verbots-Feld (INV-MODUS-5) und KEINEN
    metric/threshold-Bezug (drift_eval ist von der AK-7-Klammer exempt)."""
    return {
        "finding_id": "%s.EF-%d" % (bl_slug, idx),
        "eval_kind": "drift_eval",
        "ref_node": ref_node,
        "risk_class": risk_class,
        "severity": severity,
        "befund": befund,
        "cost": cost,
        "benefit": benefit,
        "suggested_action": suggested_action,
        "status": "offen",
        "betrifft_baustein": betrifft_baustein,
    }


def drift_findings_against_adrs(content, adr_violations, bl_slug="BL-383"):
    """AK-2 (Achse a -> Befund): erzeugt Drift-Befunde gegen die im Model produzierten
    adr-Nodes. `adr_violations`: {ADR-ID: violation_text} — die vom AC-/PostBatch-Worker
    (semantisches Urteil, ROTE Zone) gemeldeten Widersprueche.

    Pro gemeldeter Verletzung gegen einen existenten ADR -> ein drift_eval-Befund
    risk_class=Commission (Impl tut etwas Schaedliches gegen eine akzeptierte Entscheidung),
    der den betrifft_baustein-Anker des ADR traegt (T-11). Verletzungen gegen nicht-existente
    ADR-IDs werden uebersprungen (kein dangling Befund). Leere Map -> [] (kein false-positive).
    -> Liste PL1-schema-valider drift_eval eval_finding-Records."""
    adrs = load_adr_nodes(content)
    findings = []
    idx = 0
    for adr_id, violation in (adr_violations or {}).items():
        node = adrs.get(adr_id)
        if node is None:
            continue  # Verletzung gegen nicht-produzierten ADR -> kein dangling Befund.
        idx += 1
        bausteine = node.get("betrifft_baustein") or []
        findings.append(_finding(
            bl_slug, idx, adr_id, "Commission", "hoch",
            befund="Impl widerspricht akzeptierter ADR %s: %s" % (adr_id, violation),
            cost="Impl an ADR %s anpassen bzw. ADR adjudizieren (mittel-hoch)" % adr_id,
            benefit="stellt ADR-Konformitaet wieder her (Entscheidungs-Drift geschlossen)",
            suggested_action="Impl gegen ADR %s konform machen" % adr_id,
            betrifft_baustein=bausteine,
        ))
    return findings


def structural_drift_findings(changed_files, file_index, bl_slug="BL-383"):
    """AK-2 (Achse b -> Befund): erzeugt Struktur-Drift-Befunde fuer geaenderte Dateien
    ausserhalb der geplanten Bausteine (detect_structural_drift). risk_class=Commission
    (eine Datei lebt an einer ungeplanten Stelle = Struktur-Verletzung). Der Befund traegt
    den verletzten Baustein-Bezug (hier: der gesamte geplante Baustein-Satz als Kontext-Anker,
    sodass auch topologischer Drift baustein-verankert ist).
    -> Liste PL1-schema-valider drift_eval eval_finding-Records."""
    drift = detect_structural_drift(changed_files, file_index)
    if not drift:
        return []
    planned_bausteine = sorted((file_index or {}).keys())
    findings = []
    idx = 0
    for d in drift:
        idx += 1
        datei = d["datei"]
        findings.append(_finding(
            bl_slug, idx, datei, "Commission", "mittel",
            befund="Geaenderte Datei %s liegt in keinem geplanten Baustein der Bausteinsicht "
                   "(file_index) — Struktur-Drift" % datei,
            cost="Datei einem geplanten Baustein zuordnen ODER Bausteinsicht nachziehen (mittel)",
            benefit="haelt die Impl an der geplanten Komponenten-Struktur (Topologie-Drift zu)",
            suggested_action="%s in einen geplanten Baustein einordnen" % datei,
            betrifft_baustein=planned_bausteine,
        ))
    return findings


def render_findings_as_w_blocks(findings):
    """Rendert drift_eval-Befunde als `### W{n}`-Gold-Form-Bloecke (eval_finding-Subtyp),
    sodass der `quality_model_wform.py`-Validator sie als gold prueft (Interop-Beweis AK-2 x
    AK-4). Nur die Schema-Felder kommen in den eval_finding:-Block (betrifft_baustein ist
    ein Drift-Eval-interner Anker, KEIN eval_finding-Schema-Feld -> nicht in den Block)."""
    schema_keys = qmw.EVAL_FINDING_FIELDS
    parts = []
    for f in findings:
        fid = f["finding_id"]
        lines = [
            "### W-%s · Drift-Eval-Befund %s" % (fid.replace(".", "-"), f["ref_node"]),
            "- **text:** Drift-Eval-Befund fuer %s (%s)." % (f["ref_node"], f["risk_class"]),
            "- **Status:** TENTATIV",
            "- **source:** `Repo: drift_eval.py gate-script run`",
            "- **Quelle:** `[[3_Spec/BL-383_Spec.md#AK-2]]`",
            "- **Edge zu:** W-DRIFT-1",
            "- **type:** eval_finding",
            "- **id:** `%s`" % fid,
            "- **eval_finding:**",
        ]
        for k in schema_keys:
            if k in f:
                lines.append("    - %s: %s" % (k, f[k]))
        parts.append("\n".join(lines) + "\n")
    return "".join(parts)


# ── CLI (read-only: liest die adr-Nodes eines Models, listet sie) ─────────────

def _print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def main(argv):
    if not argv:
        print("usage: drift_eval.py <Model.md> [<Model.md> ...]")
        return 2
    for path in argv:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            _print("[FEHLER] {}: {}".format(path, exc))
            return 2
        adrs = load_adr_nodes(content)
        if not adrs:
            _print("[GRACEFUL] {}: 0 adr-Nodes -> kein ADR-Drift-Eval (kein Hard-Fail)".format(path))
            continue
        _print("[DRIFT-EVAL] {}: {} adr-Node(s) konsumiert (read-only, betrifft_baustein-Anker "
               "vorhanden); Drift-Befunde brauchen gemeldete Verletzungen (AC/PostBatch-Input)".format(
                   path, len(adrs)))
        for adr_id, node in sorted(adrs.items()):
            _print("    {} [{}] betrifft_baustein={}".format(
                adr_id, node["status"], node["betrifft_baustein"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
