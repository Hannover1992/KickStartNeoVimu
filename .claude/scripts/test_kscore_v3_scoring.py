"""test_kscore_v3_scoring.py — BL-311 batch_2 RED-Tests: kscore_v3_scoring.

11 Exit-Kriterien (AK-10/11/12/13):
  T-6:  score_item k_aufwand-Schicht isoliert (loc=10, zyklomatik=2, op_mult=1.6)
  T-7:  score_item k_kopplung-Schicht isoliert (Ca/Ce * streuung_faktor)
  T-8:  score_item k_fragilitaet-Schicht isoliert (srp_defizit + contention merklich)
  T-9:  score_item k_roh-Komposition Default-Gewichte (0.40/0.35/0.25)
  T-10: INV-METRIC Orthogonalitaet — verschiedener truth_grade -> identisches k_roh
  T-11: epistemik_penalty — code_verified -> 1.0; vault_hypothesis -> 1.2; unverified -> 1.4
  T-12: pattern_discount — alle 5 Stufen (twin_identical..none)
  T-13: pattern_discount — confidence=low bei fehlendem discount_evidence (SOA-1)
  T-14: score_item — k_praez vor k_final (Reihenfolge + SEPARAT im Result)
  T-15: aggregate — 3-Item-Set k_min=2.0/k_avg=5.0/k_max=8.0 (BL-304 load-bearing)
  T-16: aggregate — 1-Item: k_min==k_max==k_avg

Kanarienvogel:
  K-4: INV-METRIC-Orthogonalitaet (T-10) — truth_grade darf k_roh NICHT beeinflussen
  K-5: k_min-Load-Bearing (T-15) — k_min=2.0 bei {2,8,5}

RED-Worker: NUR Tests. KEIN Impl.
"""
import pytest

from kscore_v3_scoring import (
    score_item,
    pattern_discount,
    epistemik_penalty,
    aggregate,
)


# ---------------------------------------------------------------------------
# Fixtures: minimale Achsen-Dicts (nur Felder die scoring braucht)
# ---------------------------------------------------------------------------

def _achse1(loc=10, zyklomatik=2, datei_anz=1):
    """Minimales achse1-Dict fuer score_item-Tests."""
    return {"loc": loc, "zyklomatik": zyklomatik, "datei_anz": datei_anz}


def _achse2(op_mult=1.6):
    """Minimales achse2-Dict (MODIFY -> 1.6 aus OP_MULT)."""
    return {"op_mult": op_mult}


def _achse3(ca=2, ce=3, instability=0.6, fan_in=1, call_tiefe=2, cross_layer=False):
    """Minimales achse3-Dict fuer Kopplungs-Tests."""
    return {
        "ca": ca, "ce": ce, "instability": instability,
        "fan_in": fan_in, "call_tiefe": call_tiefe, "cross_layer": cross_layer,
    }


def _achse4(srp_defizit=0.2, uncovered=0.1):
    return {"srp_defizit": srp_defizit, "uncovered": uncovered}


def _achse5(ocp_fehlt=0.1):
    return {"ocp_fehlt": ocp_fehlt}


def _achse6(streuung_faktor=1.2):
    """single_file -> 1.2."""
    return {"streuung_faktor": streuung_faktor}


def _base_score_item(**overrides):
    """score_item mit minimalen Default-Inputs; Overrides moeglich."""
    params = dict(
        item_id="test_item",
        achse1=_achse1(),
        achse2=_achse2(),
        achse3=_achse3(),
        achse4=_achse4(),
        achse5=_achse5(),
        achse6=_achse6(),
        contention_score=0.0,
        pattern_status="none",
        truth_grade="code_verified",
        discount_evidence=None,
        weights=None,
    )
    params.update(overrides)
    return score_item(**params)


# ---------------------------------------------------------------------------
# T-6: k_aufwand-Schicht
# ---------------------------------------------------------------------------

class TestKAufwand:
    def test_k_aufwand_computed_correctly_with_modify_op_mult(self):
        """T-6: loc=10, zyklomatik=2, datei_anz=1, op_mult=1.6 -> k_aufwand korrekt (AK-10)."""
        result = _base_score_item(
            achse1=_achse1(loc=10, zyklomatik=2, datei_anz=1),
            achse2=_achse2(op_mult=1.6),
        )
        # k_aufwand = f(loc, zyklomatik, datei_anz) * op_mult
        # Genaue Formel ist Impl-Sache; wir pruefen: k_aufwand im Result vorhanden + > 0
        assert "k_aufwand" in result, "k_aufwand fehlt im score_item Result"
        assert result["k_aufwand"] > 0.0, (
            f"k_aufwand bei loc=10/zyklomatik=2/op_mult=1.6 muss > 0. result={result['k_aufwand']}"
        )

    def test_k_aufwand_higher_with_more_loc(self):
        """k_aufwand skaliert mit LOC (mehr LOC -> hoeher)."""
        r_low  = _base_score_item(achse1=_achse1(loc=5,  zyklomatik=1))
        r_high = _base_score_item(achse1=_achse1(loc=50, zyklomatik=5))
        assert r_high["k_aufwand"] > r_low["k_aufwand"], (
            "k_aufwand muss mit LOC skalieren. "
            f"low={r_low['k_aufwand']} high={r_high['k_aufwand']}"
        )


# ---------------------------------------------------------------------------
# T-7: k_kopplung-Schicht
# ---------------------------------------------------------------------------

class TestKKopplung:
    def test_k_kopplung_present_and_positive(self):
        """T-7: k_kopplung-Schicht f(Ca, Ce, instability, fan_in, call_tiefe, cross_layer) * streuung_faktor (AK-10)."""
        result = _base_score_item(
            achse3=_achse3(ca=2, ce=3, instability=0.6, fan_in=1, call_tiefe=2, cross_layer=False),
            achse6=_achse6(streuung_faktor=1.2),
        )
        assert "k_kopplung" in result, "k_kopplung fehlt im score_item Result"
        assert result["k_kopplung"] > 0.0, (
            f"k_kopplung bei Ca=2/Ce=3/instability=0.6/streuung=1.2 muss > 0. result={result['k_kopplung']}"
        )

    def test_k_kopplung_scales_with_streuung_faktor(self):
        """k_kopplung steigt mit streuung_faktor (cross_layer > single_file)."""
        r_single = _base_score_item(achse6=_achse6(streuung_faktor=1.2))
        r_cross  = _base_score_item(achse6=_achse6(streuung_faktor=2.0))
        assert r_cross["k_kopplung"] > r_single["k_kopplung"], (
            "k_kopplung muss mit streuung_faktor skalieren. "
            f"single={r_single['k_kopplung']} cross={r_cross['k_kopplung']}"
        )


# ---------------------------------------------------------------------------
# T-8: k_fragilitaet-Schicht
# ---------------------------------------------------------------------------

class TestKFragilitaet:
    def test_k_fragilitaet_present(self):
        """T-8: k_fragilitaet im Result (AK-10)."""
        result = _base_score_item()
        assert "k_fragilitaet" in result, "k_fragilitaet fehlt im score_item Result"

    def test_contention_1_drives_k_fragilitaet_high(self):
        """T-8 Gold: contention=1.0 treibt k_fragilitaet merklich hoch vs. contention=0 (AK-10)."""
        r_no_contention   = _base_score_item(contention_score=0.0)
        r_full_contention = _base_score_item(contention_score=1.0)
        assert r_full_contention["k_fragilitaet"] > r_no_contention["k_fragilitaet"], (
            "contention=1.0 muss k_fragilitaet erhoehen. "
            f"no_contention={r_no_contention['k_fragilitaet']} "
            f"full_contention={r_full_contention['k_fragilitaet']}"
        )


# ---------------------------------------------------------------------------
# T-9: k_roh-Komposition Default-Gewichte
# ---------------------------------------------------------------------------

class TestKRoh:
    def test_k_roh_composition_with_default_weights(self):
        """T-9: k_roh = w1*k_aufwand + w2*k_kopplung + w3*k_fragilitaet; Default 0.40/0.35/0.25 (AK-10 Gold-Zeile 4)."""
        result = _base_score_item()
        assert "k_roh" in result, "k_roh fehlt im score_item Result"
        assert "weights_used" in result, "weights_used fehlt im score_item Result"
        wu = result["weights_used"]
        assert abs(wu.get("w1", 0) - 0.40) < 0.001, f"w1 Default muss 0.40 sein, got {wu.get('w1')}"
        assert abs(wu.get("w2", 0) - 0.35) < 0.001, f"w2 Default muss 0.35 sein, got {wu.get('w2')}"
        assert abs(wu.get("w3", 0) - 0.25) < 0.001, f"w3 Default muss 0.25 sein, got {wu.get('w3')}"
        # k_roh muss linear Komposition sein
        expected_k_roh = (
            wu["w1"] * result["k_aufwand"]
            + wu["w2"] * result["k_kopplung"]
            + wu["w3"] * result["k_fragilitaet"]
        )
        assert abs(result["k_roh"] - expected_k_roh) < 0.001, (
            f"k_roh={result['k_roh']} != w1*k_a + w2*k_k + w3*k_f={expected_k_roh}"
        )


# ---------------------------------------------------------------------------
# T-10 KANARIVOGEL K-4: INV-METRIC Orthogonalitaet
# ---------------------------------------------------------------------------

class TestInvMetricOrthogonalitaet:
    def test_truth_grade_does_not_affect_k_roh(self):
        """K-4 + T-10: identische Achsen 1-6, verschiedener truth_grade -> identisches k_roh.
        INV-METRIC (BL-205): truth_grade fliesst NUR in epistemik_penalty, NICHT in k_roh.
        """
        r_verified   = _base_score_item(truth_grade="code_verified")
        r_unverified = _base_score_item(truth_grade="unverified")
        assert r_verified["k_roh"] == r_unverified["k_roh"], (
            "INV-METRIC verletzt: truth_grade darf k_roh NICHT beeinflussen. "
            f"k_roh(code_verified)={r_verified['k_roh']} "
            f"k_roh(unverified)={r_unverified['k_roh']}"
        )

    def test_truth_grade_does_not_affect_k_praez(self):
        """INV-METRIC: truth_grade darf auch k_praez NICHT beeinflussen (nur k_final)."""
        r_verified   = _base_score_item(truth_grade="code_verified",  pattern_status="none")
        r_unverified = _base_score_item(truth_grade="unverified",     pattern_status="none")
        assert r_verified["k_praez"] == r_unverified["k_praez"], (
            "INV-METRIC verletzt: truth_grade darf k_praez NICHT beeinflussen. "
            f"k_praez(code_verified)={r_verified['k_praez']} "
            f"k_praez(unverified)={r_unverified['k_praez']}"
        )


# ---------------------------------------------------------------------------
# T-11: epistemik_penalty Stufen
# ---------------------------------------------------------------------------

class TestEpistemikPenalty:
    def test_code_verified_penalty_factor_is_1_0(self):
        """T-11a: code_verified -> penalty_factor=1.0 (keine Strafe) (AK-11 Gold-Zeile 7)."""
        k_praez = 5.0
        k_final, factor = epistemik_penalty(k_praez, "code_verified")
        assert abs(factor - 1.0) < 0.001, f"code_verified: penalty_factor muss 1.0 sein, got {factor}"
        assert abs(k_final - k_praez * 1.0) < 0.001

    def test_vault_hypothesis_penalty_factor_is_1_2(self):
        """T-11b: vault_hypothesis -> penalty_factor=1.2 (AK-11 Gold-Zeile 7)."""
        k_praez = 5.0
        k_final, factor = epistemik_penalty(k_praez, "vault_hypothesis")
        assert abs(factor - 1.2) < 0.001, f"vault_hypothesis: penalty_factor muss 1.2 sein, got {factor}"
        assert abs(k_final - k_praez * 1.2) < 0.001

    def test_unverified_penalty_factor_is_1_4(self):
        """T-11c: unverified -> penalty_factor=1.4 (AK-11)."""
        k_praez = 5.0
        k_final, factor = epistemik_penalty(k_praez, "unverified")
        assert abs(factor - 1.4) < 0.001, f"unverified: penalty_factor muss 1.4 sein, got {factor}"

    def test_vault_confirmed_penalty_factor_is_1_05(self):
        """vault_confirmed -> penalty_factor=1.05 (leichte Strafe)."""
        k_praez = 4.0
        k_final, factor = epistemik_penalty(k_praez, "vault_confirmed")
        assert abs(factor - 1.05) < 0.001, f"vault_confirmed: penalty_factor muss 1.05, got {factor}"

    def test_penalty_returns_tuple_k_final_and_factor(self):
        """epistemik_penalty gibt (k_final, penalty_factor) Tuple zurueck (SEPARAT ausgewiesen)."""
        result = epistemik_penalty(3.0, "code_verified")
        assert isinstance(result, tuple) and len(result) == 2, (
            f"epistemik_penalty muss (k_final, factor) Tuple zurueckgeben, got {type(result)}"
        )


# ---------------------------------------------------------------------------
# T-12 + T-13: pattern_discount Stufen + confidence=low
# ---------------------------------------------------------------------------

class TestPatternDiscount:
    @pytest.mark.parametrize("status,expected_factor", [
        ("twin_identical",  0.4),
        ("promoted_1_1",    0.5),
        ("battle_tested",   0.7),
        ("experimental",    0.85),
        ("none",            1.0),
    ])
    def test_all_five_discount_stufen(self, status, expected_factor):
        """T-12: alle 5 PATTERN_DISCOUNT-Stufen (AK-12 Gold-Zeile 5)."""
        k_roh = 8.0
        k_praez, factor = pattern_discount(k_roh, status)
        assert abs(factor - expected_factor) < 0.001, (
            f"pattern_discount('{status}'): factor muss {expected_factor}, got {factor}"
        )
        assert abs(k_praez - k_roh * expected_factor) < 0.001, (
            f"k_praez muss k_roh*factor={k_roh * expected_factor}, got {k_praez}"
        )

    def test_missing_discount_evidence_sets_confidence_low(self):
        """T-13: fehlende discount_evidence -> confidence=low in Result (SOA-1-Konformanz, AK-12 Gold-Zeile 6)."""
        k_roh = 6.0
        k_praez, factor = pattern_discount(k_roh, "battle_tested", discount_evidence=None)
        # SOA-1: ohne BL-283-Telemetrie darf NICHT blind "battle_tested" angenommen werden
        # Implementierung muss confidence=low signalisieren; wir pruefen via score_item Result
        # da pattern_discount als Tuple zurueckgibt, testen wir den vollstaendigen Pfad via score_item
        result = _base_score_item(
            pattern_status="battle_tested",
            discount_evidence=None,
        )
        # discount_evidence im Result muss confidence=low haben
        evidence_in_result = result.get("discount_evidence") or {}
        assert evidence_in_result.get("confidence") == "low", (
            f"SOA-1: confidence muss 'low' sein wenn discount_evidence=None. "
            f"discount_evidence im Result={evidence_in_result}"
        )

    def test_pattern_discount_returns_tuple(self):
        """pattern_discount gibt (k_praez, discount_factor) Tuple zurueck."""
        result = pattern_discount(5.0, "none")
        assert isinstance(result, tuple) and len(result) == 2


# ---------------------------------------------------------------------------
# T-14: Reihenfolge k_praez vor k_final (SEPARAT im Result)
# ---------------------------------------------------------------------------

class TestScoringReihenfolge:
    def test_k_praez_and_k_final_separate_in_result(self):
        """T-14: k_praez SEPARAT von k_final; Reihenfolge Penalty NACH Discount (AK-11/12 Gold-Zeile 8)."""
        result = _base_score_item(
            pattern_status="battle_tested",
            truth_grade="vault_hypothesis",
            discount_evidence={"pattern_id": "X", "status": "ok", "usage": 5, "confidence": "high"},
        )
        assert "k_praez" in result, "k_praez fehlt im score_item Result"
        assert "k_final" in result, "k_final fehlt im score_item Result"
        assert "discount_factor" in result, "discount_factor fehlt im score_item Result"
        assert "penalty_factor" in result, "penalty_factor fehlt im score_item Result"
        # k_praez != k_final (bei vault_hypothesis + battle_tested)
        assert result["k_praez"] != result["k_final"], (
            f"k_praez und k_final muessen verschieden sein bei battle_tested+vault_hypothesis. "
            f"k_praez={result['k_praez']} k_final={result['k_final']}"
        )
        # Reihenfolge: k_final = k_praez * penalty_factor
        expected_k_final = result["k_praez"] * result["penalty_factor"]
        assert abs(result["k_final"] - expected_k_final) < 0.001, (
            f"k_final muss k_praez*penalty_factor={expected_k_final}, got {result['k_final']}"
        )


# ---------------------------------------------------------------------------
# T-15 KANARIVOGEL K-5: aggregate k_min Load-Bearing (BL-304)
# ---------------------------------------------------------------------------

class TestAggregate:
    def _make_scored_item(self, item_id: str, k_final: float) -> dict:
        """Minimales scored_item-Dict fuer aggregate-Tests."""
        return {
            "item_id": item_id,
            "k_aufwand": 1.0,
            "k_kopplung": 1.0,
            "k_fragilitaet": 1.0,
            "k_roh": k_final,
            "k_praez": k_final,
            "k_final": k_final,
            "pattern_status": "none",
            "discount_factor": 1.0,
            "discount_evidence": None,
            "truth_grade": "code_verified",
            "penalty_factor": 1.0,
            "weights_used": {"w1": 0.40, "w2": 0.35, "w3": 0.25},
        }

    def test_aggregate_3_items_k_min_load_bearing(self):
        """K-5 + T-15: heterogener 3-Item-Set {2,8,5} -> k_min=2.0/k_avg=5.0/k_max=8.0 (BL-304)."""
        scored_items = [
            self._make_scored_item("I1", 2.0),
            self._make_scored_item("I2", 8.0),
            self._make_scored_item("I3", 5.0),
        ]
        agg = aggregate(scored_items)
        assert abs(agg["k_min"] - 2.0) < 0.001, f"k_min muss 2.0, got {agg['k_min']}"
        assert abs(agg["k_avg"] - 5.0) < 0.001, f"k_avg muss 5.0, got {agg['k_avg']}"
        assert abs(agg["k_max"] - 8.0) < 0.001, f"k_max muss 8.0, got {agg['k_max']}"
        assert agg["item_count"] == 3

    def test_aggregate_1_item_k_min_equals_k_max_equals_k_avg(self):
        """T-16: 1 Item -> k_min==k_max==k_avg (AK-13 Gold-Zeile 10)."""
        scored_items = [self._make_scored_item("solo", 7.5)]
        agg = aggregate(scored_items)
        assert abs(agg["k_min"] - agg["k_max"]) < 0.001, (
            f"k_min muss k_max bei 1 Item. k_min={agg['k_min']} k_max={agg['k_max']}"
        )
        assert abs(agg["k_min"] - agg["k_avg"]) < 0.001, (
            f"k_min muss k_avg bei 1 Item. k_min={agg['k_min']} k_avg={agg['k_avg']}"
        )
        assert abs(agg["k_min"] - 7.5) < 0.001

    def test_aggregate_contains_per_item_reference(self):
        """aggregate Result enthaelt per_item Referenz."""
        scored_items = [
            self._make_scored_item("A", 3.0),
            self._make_scored_item("B", 6.0),
        ]
        agg = aggregate(scored_items)
        assert "per_item" in agg, "per_item fehlt im aggregate Result"
        assert len(agg["per_item"]) == 2
