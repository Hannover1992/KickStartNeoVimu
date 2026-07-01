"""
design_eval.py — BL-383 batch_PL2 (AK-1): Design-Eval (Plan-Zeit, vor Bau).

Der erste maschinelle Bewertungs-KONSUMENT der BL-380 `quality_scenario`-Nodes (SOLL).
Pro Top-Szenario:  SOLL (`response_measure{metric, threshold}`) -> IST (Entwurf) -> vergleichen.
Ausgabe = `eval_finding`-Records (PL1-Schema, `eval_kind: design_eval`), die der
`quality_model_wform.py`-Validator (check_eval_finding_block, AK-4/AK-7) als gold prueft.

**Eval-MODUS folgt STRUKTURELL aus `response_measure.endpoint_type`** (BL-380 W-RM-1) —
KEINE design_eval-Wahl, KEIN Pipeline-`DF_BATCH_STATE.modus` (INV-MODUS-1):
  - `metric_component` -> PATH_DETERMINISTIC: deterministischer SOLL/IST-Vergleich gegen
    threshold (das testbare Build-Artefakt; der Befund traegt metric+threshold = AK-7).
  - `ak_test`          -> PATH_AK_TEST: der Befund nennt den AK (endpoint_ref) als
    Falsifikations-Bezug (RED/GREEN-Loop; kein numerischer Vergleich zur Plan-Zeit).
  - rein-qualitativ / fehlend / unbekannt / reine Laufzeit-Metrik -> PATH_QUALITATIVE:
    LAUFZEIT/Urteils-Pfad (Graceful Degradation, SOA-4 — NICHT build-test, kein Hard-Fail;
    der qualitative LLM-Urteils-Schritt selbst ist markdown_uncoverable / ROTE Zone, AK-8).

read-only Konsum (kein Producer-Write in den Vault, KEIN neuer Truth-Node-Typ, W-DOM-1).
Das Gate ist Bewerter/Daten-Lieferant — es setzt NIE einen Modus und traegt NIE eines der
INV-MODUS-5-Verbotsfelder (AK-9, hook-doppelt-gesichert).

Scope batch_PL2: die DETERMINISTISCHE Logik (Szenario-Lesen, endpoint_type-Routing,
metric_component-Vergleich, Existenz-/Abdeckungs-Befund, Graceful Degradation). Die
WO-Verdrahtung an IDF-Plan-Zeit (AK-5) ist markdown_uncoverable (Skill-Doc, Forward-Verify).

CLI: `py design_eval.py <Model.md> [...]`  (read-only; gibt die Befund-Liste je Datei aus).
exit 0 = Lauf ok (auch: keine Szenarien = Graceful), 2 = Usage-Fehler.
"""

import re
import sys

import quality_model_wform as qmw

# ── Eval-Pfade (folgen aus endpoint_type, W-RM-1) ─────────────────────────────
PATH_DETERMINISTIC = "deterministic"   # metric_component: numerischer SOLL/IST-Vergleich
PATH_AK_TEST = "ak_test"               # ak_test: AK-Test-Bezug (RED/GREEN-Loop)
PATH_QUALITATIVE = "qualitative"       # rein-qualitativ / Laufzeit (Urteil/Graceful, ROTE Zone)

# endpoint_type -> Eval-Pfad. Unbekannt/None/leer faellt fail-safe auf den qualitativen
# (Laufzeit-/Urteils-) Pfad (Graceful Degradation, kein Crash, kein false-Hard-Fail).
_ENDPOINT_TO_PATH = {
    "metric_component": PATH_DETERMINISTIC,
    "ak_test": PATH_AK_TEST,
}


def route_eval_path(endpoint_type):
    """AK-1: bildet endpoint_type (W-RM-1) auf den Eval-Pfad ab. Das ist KEINE freie Wahl —
    es FOLGT strukturell aus dem SOLL-Knoten (BL-380). Unbekannt/None/leer -> qualitativer
    Laufzeit-Pfad (fail-safe Graceful Degradation)."""
    if not endpoint_type:
        return PATH_QUALITATIVE
    return _ENDPOINT_TO_PATH.get(str(endpoint_type).strip().lower(), PATH_QUALITATIVE)


def _scenario_field(body, key):
    """Liest einen einzeiligen Skalar-Wert (Bullet- ODER YAML-indentiert) aus dem
    Szenario-Body. Delegiert an den generischen Reader des Validators (Single-Source)."""
    return qmw._eval_field_value(body, key)


def _scenario_node_id(body):
    """Eigene Szenario-ID `{BL-SLUG}.QS-{n}` aus `- **id:**`/`id:` (Quotes gestrippt)."""
    return qmw._adr_node_id(body)


def load_quality_scenarios(content):
    """AK-1 (read-only Konsum): parst ein Model und liefert die quality_scenario-Nodes als
    dicts {w_id, id, endpoint_type, endpoint_ref, metric, threshold, method}. Nicht-Szenario-
    Knoten (plain-W, adr, eval_finding) werden ignoriert. KEIN Schema-Edit, KEIN Write."""
    out = []
    for block in qmw.parse_w_blocks(content):
        body = block["body"]
        if not qmw._is_quality_scenario(body):
            continue
        out.append({
            "w_id": block["w_id"],
            "id": _scenario_node_id(body) or block["w_id"],
            "endpoint_type": _scenario_field(body, "endpoint_type"),
            "endpoint_ref": _scenario_field(body, "endpoint_ref"),
            "metric": _scenario_field(body, "metric"),
            "threshold": _scenario_field(body, "threshold"),
            "method": _scenario_field(body, "method"),
        })
    return out


# ── Deterministischer SOLL/IST-Vergleich (metric_component-Pfad) ──────────────
# Aus dem threshold-String wird der Operator + die Zahl gezogen (z.B. "I < 0.4" -> (<, 0.4)).
# Reicht das nicht (keine Zahl extrahierbar), faellt der Vergleich graceful aus (covered-Flag
# entscheidet dann). Wir erfinden KEINE Semantik ueber das hinaus, was im threshold steht.
_THRESHOLD_RE = re.compile(r"(<=|>=|<|>|==|=)\s*([0-9]+(?:\.[0-9]+)?)")
_OPS = {
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "=": lambda a, b: a == b,
}


def _threshold_satisfied(threshold_str, ist_value):
    """Deterministischer SOLL/IST-Vergleich. -> True (erfuellt) / False (verletzt) / None
    (nicht entscheidbar: kein parsebarer Operator+Zahl ODER kein IST-Wert)."""
    if ist_value is None or not threshold_str:
        return None
    m = _THRESHOLD_RE.search(str(threshold_str))
    if not m:
        return None
    op, num = m.group(1), float(m.group(2))
    try:
        return _OPS[op](float(ist_value), num)
    except (TypeError, ValueError):
        return None


def _finding(bl_slug, idx, ref_node, risk_class, severity, befund, cost, benefit,
             suggested_action, eval_path, metric=None, threshold=None):
    """Baut EINEN eval_finding-Record (PL1-Schema, eval_kind=design_eval). Traegt KEIN
    Modus-/Verbots-Feld (INV-MODUS-5). `eval_path` ist die deterministisch abgeleitete
    Eval-Route (KEIN DF_BATCH_STATE.modus). metric/threshold werden NUR fuer den
    deterministischen Pfad gesetzt (AK-7-Messbarkeits-Klammer)."""
    rec = {
        "finding_id": "%s.EF-%d" % (bl_slug, idx),
        "eval_kind": "design_eval",
        "ref_node": ref_node,
        "risk_class": risk_class,
        "severity": severity,
        "befund": befund,
        "cost": cost,
        "benefit": benefit,
        "suggested_action": suggested_action,
        "status": "offen",
        "eval_path": eval_path,
    }
    # AK-7 Messbarkeits-Klammer: design_eval-Befund auf dem deterministischen Pfad traegt
    # metric+threshold (sonst ist der PL1-Validator-Check 6 unerfuellbar). Der qualitative/
    # ak_test-Pfad tragen sie nicht (dort kein numerischer SOLL/IST-Bezug).
    if metric is not None and threshold is not None:
        rec["metric"] = metric
        rec["threshold"] = threshold
    return rec


def design_eval(content, coverage_map=None, bl_slug="BL-383"):
    """AK-1: Design-Eval ueber alle Top-quality_scenario-Nodes eines Models.

    Pro Szenario:
      1) Eval-Pfad aus endpoint_type ableiten (route_eval_path; W-RM-1).
      2) PATH_QUALITATIVE (rein-qualitativ / reine Laufzeit-Metrik): Graceful Degradation
         (SOA-4) — vor-Bau NICHT deterministisch pruefbar; KEIN harter Omission-Befund mit
         det-Pfad. Es entsteht kein false-Hard-Fail (leer = "auf Laufzeit/Drift-Eval vertagt").
      3) PATH_DETERMINISTIC (metric_component): SOLL/IST gegen threshold vergleichen.
         - keine Abdeckung (coverage fehlt/covered=False)      -> Omission-Befund (T-5)
         - IST verletzt Schwelle                               -> Commission-Befund
         - IST erfuellt Schwelle                               -> KEIN Befund
         Der Befund traegt metric+threshold (AK-7).
      4) PATH_AK_TEST (ak_test): keine Abdeckung -> Omission-Befund auf dem AK-Test-Pfad,
         der den AK (endpoint_ref) als Falsifikations-Bezug nennt (kein num. Vergleich).

    `coverage_map`: {QS-ID: {"covered": bool, "ist_value": <Zahl|None>}}; das ist der IST-
    Input (was der Entwurf abdeckt / welcher Wert erreicht wird). Fehlt er -> {} (alles offen).
    -> Liste von eval_finding-Records (PL1-schema-valide). Leere Liste = keine Risiken / keine
    Szenarien (Graceful, KEIN Hard-Fail)."""
    coverage_map = coverage_map or {}
    findings = []
    idx = 0
    for sc in load_quality_scenarios(content):
        qs_id = sc["id"]
        path = route_eval_path(sc["endpoint_type"])
        cov = coverage_map.get(qs_id, {})
        covered = bool(cov.get("covered"))
        ist_value = cov.get("ist_value")

        if path == PATH_QUALITATIVE:
            # Graceful Degradation (SOA-4): vor-Bau nicht deterministisch pruefbar.
            # Kein Befund (auf Drift-Eval/Laufzeit vertagt) — explizit KEIN det-Hard-Fail.
            continue

        if path == PATH_AK_TEST:
            if not covered:
                idx += 1
                findings.append(_finding(
                    bl_slug, idx, qs_id, "Omission", "mittel",
                    befund="Top-Szenario %s (ak_test) ohne Entwurfs-Abdeckung; "
                           "AK-Test-Bezug %s nicht nachweisbar adressiert"
                           % (qs_id, sc["endpoint_ref"] or "?"),
                    cost="AK-Test/Slice fuer %s vorsehen (mittel)" % (sc["endpoint_ref"] or "?"),
                    benefit="schliesst Omission-Luecke ueber bestehbaren Test (RED/GREEN)",
                    suggested_action="AK-Test-Abdeckung fuer %s einplanen" % qs_id,
                    eval_path=PATH_AK_TEST,
                ))
            continue

        # PATH_DETERMINISTIC (metric_component).
        if not covered:
            idx += 1
            findings.append(_finding(
                bl_slug, idx, qs_id, "Omission", "hoch",
                befund="Top-Szenario %s vom Entwurf nicht abgedeckt "
                       "(Schwelle %s nicht nachweisbar erfuellt)" % (qs_id, sc["threshold"] or "?"),
                cost="Entwurf um Komponente fuer %s erweitern (mittel)" % qs_id,
                benefit="schliesst Omission-Luecke messbar gegen Schwelle vor Bau",
                suggested_action="Komponente fuer %s im Model nachziehen" % qs_id,
                eval_path=PATH_DETERMINISTIC,
                metric=sc["metric"], threshold=sc["threshold"],
            ))
            continue

        satisfied = _threshold_satisfied(sc["threshold"], ist_value)
        if satisfied is False:
            idx += 1
            findings.append(_finding(
                bl_slug, idx, qs_id, "Commission", "hoch",
                befund="Entwurf-IST (%s) verletzt SOLL-Schwelle %s fuer %s"
                       % (ist_value, sc["threshold"], qs_id),
                cost="Entwurf nachbessern bis Schwelle erfuellt (mittel-hoch)",
                benefit="stellt messbare SOLL-Erfuellung gegen Schwelle her",
                suggested_action="Metrik %s gegen Schwelle %s im Entwurf senken/heben"
                                 % (sc["metric"] or "?", sc["threshold"] or "?"),
                eval_path=PATH_DETERMINISTIC,
                metric=sc["metric"], threshold=sc["threshold"],
            ))
        # satisfied True ODER None-aber-covered -> kein Befund (erfuellt bzw. abgedeckt).
    return findings


def render_findings_as_w_blocks(findings):
    """Rendert eval_finding-Records als `### W{n}`-Gold-Form-Bloecke (eval_finding-Subtyp),
    sodass der `quality_model_wform.py`-Validator sie als gold pruefen kann (Interop-Beweis
    AK-1 x AK-4/AK-7). Nur die schema-relevanten Felder werden in den eval_finding:-Block
    geschrieben (eval_path ist eine Eval-interne Annotation, KEIN Schema-Feld)."""
    schema_keys = qmw.EVAL_FINDING_FIELDS + qmw.EVAL_FINDING_MEASURE_FIELDS
    parts = []
    for f in findings:
        fid = f["finding_id"]
        lines = [
            "### W-%s · Design-Eval-Befund %s" % (fid.replace(".", "-"), f["ref_node"]),
            "- **text:** Design-Eval-Befund fuer %s (%s)." % (f["ref_node"], f["risk_class"]),
            "- **Status:** TENTATIV",
            "- **source:** `Repo: design_eval.py gate-script run`",
            "- **Quelle:** `[[3_Spec/BL-383_Spec.md#AK-1]]`",
            "- **Edge zu:** W-DES-1",
            "- **type:** eval_finding",
            "- **id:** `%s`" % fid,
            "- **eval_finding:**",
        ]
        for k in schema_keys:
            if k in f:
                lines.append("    - %s: %s" % (k, f[k]))
        parts.append("\n".join(lines) + "\n")
    return "".join(parts)


def main(argv):
    if not argv:
        print("usage: design_eval.py <Model.md> [<Model.md> ...]")
        return 2
    for path in argv:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            print("[FEHLER] {}: {}".format(path, exc))
            return 2
        scenarios = load_quality_scenarios(content)
        findings = design_eval(content, coverage_map={}, bl_slug="BL-383")
        if not scenarios:
            print("[GRACEFUL] {}: 0 quality_scenario-Nodes -> kein Design-Eval "
                  "(kein Hard-Fail)".format(path))
            continue
        print("[DESIGN-EVAL] {}: {} Szenario(en), {} Befund(e) (alle offen, vor-Bau)".format(
            path, len(scenarios), len(findings)))
        for f in findings:
            print("    {risk}/{path}: {ref} — {befund}".format(
                risk=f["risk_class"], path=f["eval_path"], ref=f["ref_node"], befund=f["befund"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
