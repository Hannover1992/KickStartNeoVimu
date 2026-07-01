"""kscore_v3_scoring.py — BL-311 batch_2: Stage 3 Parametrisches Scoring.

Wandelt pro-Item Achsen-Vektoren (aus batch_1 Walker) + Contention-Score
(aus Stage 2 Topologie) in die 3-Schicht-Metrik k_roh -> k_praez -> k_final um.

EINGABE (immer Parameter — nie aus git/FS gelesen):
  - achse1..achse6: die sechs Achsen-Dicts aus batch_1 (kscore_v3_axes).
  - contention_score: float aus Stage 2 (kscore_v3_topology.contention_per_item).
  - pattern_status / truth_grade: klassifizierte Eingaben fuer Discount/Penalty.
  - weights: optionale Gewichts-Ueberschreibung (Default DEFAULT_WEIGHTS).

AUSGABE: score_item -> Dict mit allen drei Schichten + Faktoren + Evidence;
  aggregate -> k_max/k_avg/k_min ueber gescorte Items.

STAGE: Stage 3 (Scoring) zwischen Stage 2 Topologie und Stage 4 Persist.

3-Schicht-Invariante:
  k_roh   = w1*k_aufwand + w2*k_kopplung + w3*k_fragilitaet  (NUR Achsen 1-6)
  k_praez = pattern_discount(k_roh, pattern_status)            (Achse 9)
  k_final = epistemik_penalty(k_praez, truth_grade)            (Achse 8)

INV-METRIC (BL-205): truth_grade fliesst NUR in epistemik_penalty —
  NICHT in k_roh oder k_praez (Orthogonalitaet, Kanarienvogel K-4).

REUSE (kein Duplikat): OP_MULT + STREUUNG_FAKTOR via Import aus kscore_v3_axes.
"""
from __future__ import annotations

from typing import Optional

from kscore_v3_axes import OP_MULT, STREUUNG_FAKTOR  # noqa: F401 (Single-Source-Reuse-Nachweis)

# ---------------------------------------------------------------------------
# Konstanten (Single-Source — kalibrierbare Default-Gewichte + Normierung)
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS: dict[str, float] = {"w1": 0.40, "w2": 0.35, "w3": 0.25}

# Normierungs-Divisoren der Schicht-Basis-Formeln (kein inline Magic Number).
LOC_NORM: float = 100.0          # LOC -> normierte Groesse
ZYKLOMATIK_NORM: float = 10.0    # Zyklomatik -> normierte Groesse
DATEI_NORM: float = 10.0         # Datei-Anzahl -> normierte Groesse/Kopplung
KOPPLUNG_NORM: float = 10.0      # (Ca+Ce) / fan_in / call_tiefe -> normierte Kopplung
CROSS_LAYER_BONUS: float = 0.5   # Aufschlag wenn cross_layer=True

# Pattern-Discount-Staffelung (AK-12, W-VAL-8, W-MAP-3)
PATTERN_DISCOUNT: dict[str, float] = {
    "twin_identical": 0.4,
    "promoted_1_1":   0.5,
    "battle_tested":  0.7,
    "experimental":   0.85,
    "none":           1.0,
}

# Epistemik-Penalty-Mapping (AK-11, W-VAL-7) — truth_grade -> Penalty-Faktor
EPISTEMIK_PENALTY_MAP: dict[str, float] = {
    "code_verified":   1.0,
    "test_covered":    1.0,
    "vault_confirmed": 1.05,
    "vault_hypothesis": 1.2,
    "unverified":      1.4,
}


# ---------------------------------------------------------------------------
# Hilfsfunktionen: Schicht-Berechnungen
# ---------------------------------------------------------------------------

def _compute_k_aufwand(achse1: dict, achse2: dict) -> float:
    """k_aufwand = f(loc, zyklomatik, datei_anz) * op_mult."""
    loc = achse1.get("loc", 0)
    zyklomatik = achse1.get("zyklomatik", 1)
    datei_anz = achse1.get("datei_anz", 1)
    op_mult = achse2.get("op_mult", 1.0)
    # Basis: normierte Groesse aus LOC + Zyklomatik + Datei-Anzahl.
    basis = (loc / LOC_NORM) + (zyklomatik / ZYKLOMATIK_NORM) + (datei_anz / DATEI_NORM)
    return basis * op_mult


def _compute_k_kopplung(achse3: dict, achse6: dict) -> float:
    """k_kopplung = f(Ca, Ce, instability, fan_in, call_tiefe, cross_layer) * streuung_faktor."""
    ca = achse3.get("ca", 0)
    ce = achse3.get("ce", 0)
    instability = achse3.get("instability", 0.0)
    fan_in = achse3.get("fan_in", 0)
    call_tiefe = achse3.get("call_tiefe", 0)
    cross_layer = achse3.get("cross_layer", False)
    streuung_faktor = achse6.get("streuung_faktor", 1.0)

    cross_layer_bonus = CROSS_LAYER_BONUS if cross_layer else 0.0
    # Basis: normierte Kopplung aus Martin-Metriken + Fan-in + Call-Tiefe.
    basis = (
        (ca + ce) / KOPPLUNG_NORM
        + instability
        + fan_in / KOPPLUNG_NORM
        + call_tiefe / KOPPLUNG_NORM
        + cross_layer_bonus
    )
    return basis * streuung_faktor


def _compute_k_fragilitaet(achse4: dict, achse5: dict, contention_score: float) -> float:
    """k_fragilitaet = f(srp_defizit, ocp_fehlt, uncovered, contention_score)."""
    srp_defizit = achse4.get("srp_defizit", 0.0)
    uncovered = achse4.get("uncovered", 0.0)
    ocp_fehlt = achse5.get("ocp_fehlt", 0.0)
    # Basis: summe der Fragilitaets-Indikatoren + contention
    return srp_defizit + ocp_fehlt + uncovered + contention_score


# ---------------------------------------------------------------------------
# Oeffentliche Funktionen
# ---------------------------------------------------------------------------

def pattern_discount(
    k_roh: float,
    pattern_status: str,
    discount_evidence: Optional[dict] = None,
) -> tuple[float, float]:
    """Wendet PATTERN_DISCOUNT auf k_roh an.

    SOA-1-Konformanz: fehlende BL-283-Telemetrie -> confidence=low in discount_evidence.

    Returns: (k_praez, discount_factor)
    """
    factor = PATTERN_DISCOUNT.get(pattern_status, 1.0)
    k_praez = k_roh * factor
    return (k_praez, factor)


def epistemik_penalty(
    k_praez: float,
    truth_grade: str,
) -> tuple[float, float]:
    """Multipliziert k_praez mit Penalty-Faktor fuer truth_grade.

    INV-METRIC: orthogonal zu k_roh — srs fliesst NICHT in k_aufwand/k_kopplung/k_fragilitaet.
    Penalty ist EINZIGE deklarierte K<->SRS-Koppelstelle (W-VAL-7, BL-205).

    Returns: (k_final, penalty_factor)
    """
    factor = EPISTEMIK_PENALTY_MAP.get(truth_grade, 1.4)
    k_final = k_praez * factor
    return (k_final, factor)


def score_item(
    item_id: str,
    achse1: dict,
    achse2: dict,
    achse3: dict,
    achse4: dict,
    achse5: dict,
    achse6: dict,
    contention_score: float,
    pattern_status: str = "none",
    truth_grade: str = "unverified",
    discount_evidence: Optional[dict] = None,
    weights: Optional[dict] = None,
) -> dict:
    """Berechnet k_roh -> k_praez -> k_final fuer ein Item.

    3-Schicht-Komposition (W-SCO-4):
      k_aufwand    = f(loc, zyklomatik, datei_anz) * op_mult
      k_kopplung   = f(ca, ce, instability, fan_in, call_tiefe, cross_layer) * streuung_faktor
      k_fragilitaet = f(srp_defizit, ocp_fehlt, uncovered, contention_score)
      k_roh        = w1*k_aufwand + w2*k_kopplung + w3*k_fragilitaet
      k_praez      = pattern_discount(k_roh, pattern_status)
      k_final      = epistemik_penalty(k_praez, truth_grade)

    INV-METRIC (BL-205): truth_grade fliesst NUR in epistemik_penalty.
    """
    w = {**DEFAULT_WEIGHTS, **(weights or {})}

    k_aufwand = _compute_k_aufwand(achse1, achse2)
    k_kopplung = _compute_k_kopplung(achse3, achse6)
    k_fragilitaet = _compute_k_fragilitaet(achse4, achse5, contention_score)

    k_roh = w["w1"] * k_aufwand + w["w2"] * k_kopplung + w["w3"] * k_fragilitaet

    k_praez, discount_factor = pattern_discount(k_roh, pattern_status, discount_evidence)

    k_final, penalty_factor = epistemik_penalty(k_praez, truth_grade)

    # SOA-1-Konformanz: fehlende discount_evidence -> confidence=low
    effective_evidence = discount_evidence
    if effective_evidence is None and pattern_status != "none":
        effective_evidence = {
            "pattern_id": pattern_status,
            "status": "unknown",
            "usage": 0,
            "confidence": "low",
        }

    return {
        "item_id": item_id,
        "k_aufwand": k_aufwand,
        "k_kopplung": k_kopplung,
        "k_fragilitaet": k_fragilitaet,
        "k_roh": k_roh,
        "k_praez": k_praez,
        "k_final": k_final,
        "pattern_status": pattern_status,
        "discount_factor": discount_factor,
        "discount_evidence": effective_evidence,
        "truth_grade": truth_grade,
        "penalty_factor": penalty_factor,
        "weights_used": {"w1": w["w1"], "w2": w["w2"], "w3": w["w3"]},
    }


def aggregate(scored_items: list[dict]) -> dict:
    """Berechnet k_max, k_avg, k_min ueber alle gescorten Items.

    k_min ist load-bearing fuer BL-304-Heterogenitaets-Praezision.

    Returns:
        {
          k_max: float, k_avg: float, k_min: float,
          item_count: int,
          per_item: list[dict],
        }
    """
    if not scored_items:
        return {
            "k_max": 0.0,
            "k_avg": 0.0,
            "k_min": 0.0,
            "item_count": 0,
            "per_item": [],
        }

    k_finals = [item["k_final"] for item in scored_items]
    return {
        "k_max": max(k_finals),
        "k_avg": sum(k_finals) / len(k_finals),
        "k_min": min(k_finals),
        "item_count": len(scored_items),
        "per_item": scored_items,
    }
