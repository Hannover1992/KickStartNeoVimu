#!/usr/bin/env python3
"""kazman_kscore_axes.py — BL-381 batch_1: zwei neue, getrennte K-Score-Achsen (read-only).

EIN Producer (kein Doppel) fuer die beiden code-dominanten BL-381-Achsen, die der
K-Score-Compute (_K_score.md-Doktrin D03 + per-BL-Compute-Skripte) konsumiert:

  AK-2  co_commit_axis(...)      -> die `co_commit_coupling`-Fragilitaets-Achse (0-100),
        abgeleitet aus cochange_coupling.file_degree. SEMANTISCH ein Co-Change-GRAD
        (Summe der Paar-Counts je Datei), NICHT eine Datei-Change-Frequenz. Tritt als
        EIGENE, benannte Achse NEBEN den schwachen `aenderungs_risiko`-Proxy
        (_K_score.md:677-682) — NICHT in denselben Term addiert (W-AK2-2-Adjudikation).

  AK-4  kscore_risk_finding(...) -> ein K-Score-begleitender eval_finding-Record, der
        `risk_class` (aus den GENAU-4-Kazman-Klassen) + cost/benefit traegt, durch REUSE
        von quality_model_wform.RISK_CLASS_ENUM + check_eval_finding_block. KEIN neues
        Enum, kein dupliziertes Schema. Andockpunkt ist ein NACHGELAGERTER Record
        (eval_kind=design_eval), der den K-Score-Befund per ref_node referenziert — der
        K-Score-Zahlen-Output (k_aufwand/k_kopplung/k_fragilitaet/k_score) bleibt
        unveraendert (W-AK4-3-Adjudikation).

STRIKT READ-ONLY: reine Ableitungs-Funktionen auf uebergebenen Daten. Kein git/subprocess,
kein File-Write, kein State-Mutieren (analog cochange_coupling.py). Die git-Datenquelle
liefert cochange_coupling.py (der EINZIGE Co-Change-Producer); dieses Modul rechnet nur die
0-100-Achse + den Befund-Record darauf.

SEAM zu BL-342/BL-415 (W-AK2-3): das geteilte Substrat ist cochange_coupling.cochange_pairs
(Paarliste) + file_degree (Grad-Map). BL-381 verdrahtet daraus die Fragilitaets-Achse;
BL-342/BL-415 (Parallel-Suitability / Konflikt-Praediktor) konsumiert DENSELBEN Producer-
Output — kein zweites Co-Change-Skript.
"""
from __future__ import annotations

from collections import Counter

# REUSE (KEIN neues Enum): die GENAU-4-Kazman-Risiko-Klassen + der eval_finding-Validator
# stammen aus der BL-382/383-Library. Wir importieren das Enum-Objekt selbst (Identitaet),
# damit kein abweichendes Zweit-Enum entstehen kann.
from quality_model_wform import (
    EVAL_FINDING_NONEMPTY_FIELDS,
    RISK_CLASS_ENUM,
)

# Benannter Achsen-Schluessel — DISTINKT von `aenderungs_risiko` (W-AK2-2: keine
# Summen-Verschmelzung; beide Felder existieren getrennt).
CO_COMMIT_AXIS_NAME = "co_commit_coupling"
AENDERUNGS_RISIKO_AXIS_NAME = "aenderungs_risiko"

# eval_kind des K-Score-begleitenden Befunds (W-AK4-3): design_eval (Plan-/Design-Zeit-Befund).
KSCORE_FINDING_EVAL_KIND = "design_eval"


def co_commit_axis(file_degree: Counter | dict, scale: float = 100.0) -> dict:
    """Leitet die `co_commit_coupling`-Achse (0..scale, default 0-100) aus dem
    Co-Change-Grad je Datei ab (Max-Normalisierung, konsistent mit der K-Skala W-CON-1).

    `file_degree` = cochange_coupling.file_degree(pairs): {datei: grad}, wobei grad die
    Summe der Co-Commit-Paar-Counts ist (Co-Change-GRAD, NICHT Commit-Count). Dateien
    ohne Co-Change-Paar erscheinen NICHT in file_degree -> tragen die Achse nicht (Grad 0);
    genau hier unterscheidet sich die Achse vom aenderungs_risiko-Proxy (Datei-Change-
    Frequenz einer EINZELNEN Datei).

    Leere Eingabe -> {} (kein Crash, keine Division durch 0). Die Datei mit hoechstem Grad
    normalisiert auf `scale`; ein einzelner Knoten IST das Maximum -> scale.
    """
    if not file_degree:
        return {}
    max_deg = max(file_degree.values())
    if max_deg <= 0:
        # Alle Grade 0 (degeneriert) — keine Kopplungs-Information.
        return {f: 0.0 for f in file_degree}
    return {f: round(deg / max_deg * scale, 1) for f, deg in file_degree.items()}


def fragility_axes(file_degree: Counter | dict, aenderungs_risiko: dict | None = None) -> dict:
    """Buendelt die getrennten Fragilitaets-Achsen als EIGENE benannte Felder — Beweis,
    dass `co_commit_coupling` NICHT in `aenderungs_risiko` addiert wird (W-AK2-2). Das ist
    der Konsum-Vertrag fuer den K-Score-Produzenten (D03): er liest beide Achsen GETRENNT
    und summiert sie NICHT zu einem Term.

    -> {"co_commit_coupling": {datei: 0-100}, "aenderungs_risiko": {datei: <proxy>}}
    """
    return {
        CO_COMMIT_AXIS_NAME: co_commit_axis(file_degree),
        AENDERUNGS_RISIKO_AXIS_NAME: dict(aenderungs_risiko or {}),
    }


def kscore_risk_finding(
    bl_slug: str,
    idx: int,
    ref_node: str,
    risk_class: str,
    severity: str,
    befund: str,
    cost: str,
    benefit: str,
    suggested_action: str,
    metric: str = "k_score",
    threshold: str = "<=66",
    status: str = "offen",
) -> dict:
    """Baut EINEN K-Score-begleitenden eval_finding-Record (AK-4), der den K-Score von einer
    blossen Zahl zu etwas Aktionierbarem macht: er traegt `risk_class` (Kazman-Klasse) +
    cost/benefit. REUSE von RISK_CLASS_ENUM (Import) — KEIN neues Enum.

    Andockpunkt (W-AK4-3): ein NACHGELAGERTER Record (eval_kind=design_eval), der den
    K-Score-Befund per `ref_node` (z.B. die AK-ID / Komponente) referenziert. Der K-Score-
    Skalar selbst bleibt unveraendert.

    Validierung VOR Rueckgabe (fail-fast, statt erst im qmw-Validator):
      - risk_class MUSS in RISK_CLASS_ENUM sein (case-sensitiv, Kazman-Title-Case).
      - cost UND benefit MUESSEN nicht-leer sein (EVAL_FINDING_NONEMPTY_FIELDS,
        Aktionierbarkeits-Pflicht).
    -> ValueError bei Verletzung. Der erzeugte Record besteht
    quality_model_wform.check_eval_finding_block (siehe render_eval_finding_block).

    metric/threshold sind gesetzt (default k_score / <=66), weil ein design_eval-Befund die
    Messbarkeits-Klammer (qmw AK-7, EVAL_FINDING_MEASURE_FIELDS) tragen MUSS. Die konkrete
    Schwellen-DEFINITION ist NICHT BL-381-Scope (W-CON-1, an BL-311/312 delegiert) — hier nur
    der strukturelle messbare Bezug, kein neuer Schwellen-Beschluss.
    """
    if risk_class not in RISK_CLASS_ENUM:
        raise ValueError(
            "risk_class %r nicht in RISK_CLASS_ENUM %s (KEIN freier String, KEIN neues Enum)"
            % (risk_class, sorted(RISK_CLASS_ENUM))
        )
    for field, val in (("cost", cost), ("benefit", benefit)):
        if field in EVAL_FINDING_NONEMPTY_FIELDS and not (val and str(val).strip()):
            raise ValueError(
                "%s muss nicht-leer sein (Aktionierbarkeits-Pflicht, "
                "EVAL_FINDING_NONEMPTY_FIELDS)" % field
            )
    return {
        "finding_id": "%s.EF-%d" % (bl_slug, idx),
        "eval_kind": KSCORE_FINDING_EVAL_KIND,
        "ref_node": ref_node,
        "risk_class": risk_class,
        "severity": severity,
        "befund": befund,
        "cost": cost,
        "benefit": benefit,
        "suggested_action": suggested_action,
        "status": status,
        "metric": metric,
        "threshold": threshold,
    }


# Reihenfolge der eval_finding-Felder im gerenderten Block (deckt die qmw-Pflichtfelder
# + Messbarkeits-Klammer ab). Reine Praesentation; die Wahrheit ist der Record-Dict oben.
_RENDER_ORDER = [
    "finding_id", "eval_kind", "ref_node", "risk_class", "severity",
    "befund", "cost", "benefit", "suggested_action", "status", "metric", "threshold",
]


def render_eval_finding_block(rec: dict) -> str:
    """Rendert einen eval_finding-Record als W-Block in der atomaren Gold-Form, die
    quality_model_wform.check_eval_finding_block prueft (YAML-indentierter `eval_finding:`-
    Block unter den Gold-Form-Pflichtfeldern). NUR Praesentation — kein File-Write.

    Der zurueckgegebene String ist als Validator-Eingabe gedacht (Behavior-Verify) bzw. zum
    Einbetten in ein Model/Report durch den Caller. Schluessel ausserhalb _RENDER_ORDER
    werden hinten angehaengt (verlustfrei)."""
    lines = [
        "- **text:** K-Score-Befund %s (risk_class=%s)" % (rec.get("ref_node", "?"), rec.get("risk_class", "?")),
        "- **Status:** OFFEN",
        "- **source:** INTERN .claude/scripts/kazman_kscore_axes.py (BL-381 AK-4)",
        "- **Quelle:** [[Repo:.claude/scripts/quality_model_wform.py]]",
        "- **Edge zu:** %s" % rec.get("ref_node", "?"),
        "- **type:** eval_finding",
        "- eval_finding:",
    ]
    for key in _RENDER_ORDER:
        if key in rec:
            lines.append("    %s: %s" % (key, rec[key]))
    for key, val in rec.items():
        if key not in _RENDER_ORDER:
            lines.append("    %s: %s" % (key, val))
    return "\n".join(lines) + "\n"


__all__ = [
    "CO_COMMIT_AXIS_NAME",
    "AENDERUNGS_RISIKO_AXIS_NAME",
    "KSCORE_FINDING_EVAL_KIND",
    "RISK_CLASS_ENUM",
    "co_commit_axis",
    "fragility_axes",
    "kscore_risk_finding",
    "render_eval_finding_block",
]
