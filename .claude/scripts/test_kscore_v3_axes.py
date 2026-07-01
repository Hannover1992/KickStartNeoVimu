"""test_kscore_v3_axes.py — TDD RED fuer BL-311 batch_1 (PY-AXES).

21 Exit-Kriterien (Gold-Definition, blueprint.md ##6) + 3 Kanarienvoegel.
Import-Error bei fehlendem kscore_v3_axes.py = erwartet ROT.

AK-4: axis1_scope (Scope/Groesse, deterministisch)
AK-5: axis3_coupling (Martin-Kopplung + INV-K2)
AK-6: axis6_locality (Streuungs-Klassifikation, deterministisch)
AK-7: axis2_operation (OP_MULT-Matrix, Hybrid)
AK-8: axis4_cohesion + axis5_ocp (SRP/OCP, Hybrid mit Substrat-Reuse)
"""
import pytest

from kscore_v3_axes import (
    axis1_scope,
    axis2_operation,
    axis3_coupling,
    axis4_cohesion,
    axis5_ocp,
    axis6_locality,
    OP_MULT,
    STREUUNG_FAKTOR,
)


# ---------------------------------------------------------------------------
# KANARIENVOEGEL — laufen bei JEDEM tddExecute als Smoke-Tripwire
# ---------------------------------------------------------------------------

class TestKanarienvoegel:
    """K-1, K-2, K-3 — bricht einer, kein weiterer RED/GREEN-Zyklus."""

    def test_k1_axis1_scope_determinism_kanarienvogel(self):
        """K-1 (T-AK4-1): identischer source -> identischer Output (Determinismus-Kern-Invariante).
        Schlaegt sofort an wenn interner State eingefuehrt wird."""
        src = "x = 1\n"
        assert axis1_scope(src) == axis1_scope(src)

    def test_k2_axis3_coupling_inv_k2_kanarienvogel(self):
        """K-2 (T-AK5-2): lsp_available=False + evidence=None -> ValueError (INV-K2-Firewall)."""
        with pytest.raises(ValueError):
            axis3_coupling(
                ca=0, ce=5, fan_in=1, call_tiefe=2,
                cross_layer=False, lsp_available=False, evidence=None,
            )

    def test_k3_axis2_operation_op_mult_kanarienvogel(self):
        """K-3 (T-AK7-1): MODIFY->1.6 aus OP_MULT (Konstanten-Integritaet)."""
        result = axis2_operation("MODIFY", 0.9, "git diff L5")
        assert result["op_mult"] == pytest.approx(1.6)


# ---------------------------------------------------------------------------
# TestAxis1Scope — AK-4 (4 Exit-Kriterien)
# ---------------------------------------------------------------------------

class TestAxis1Scope:
    """axis1_scope: Scope/Groesse-Achse, Script-deterministisch via AST."""

    def test_determinism_same_source_same_output(self):
        """Exit-Kriterium AK-4/1: gleicher source -> identischer Output (Determinismus)."""
        src = "def foo():\n    if True:\n        return 1\n"
        r1 = axis1_scope(src)
        r2 = axis1_scope(src)
        assert r1 == r2

    def test_loc_excludes_empty_lines(self):
        """Exit-Kriterium AK-4/2: LOC zaehlt nur nicht-leere Zeilen."""
        src = "x = 1\n\n\ny = 2\n"
        result = axis1_scope(src)
        assert result["loc"] == 2

    def test_zyklomatik_heuristik_counts_branches(self):
        """Exit-Kriterium AK-4/3: Zyklomatik-Heuristik zaehlt If/For/While/BoolOp-Knoten."""
        src = "if x:\n    pass\n"
        result = axis1_scope(src)
        assert result["zyklomatik"] == 1

    def test_soa2_zyklomatik_source_heuristik_when_no_tool(self):
        """Exit-Kriterium AK-4/4: bei fehlendem Tool ist zyklomatik_source='heuristik' (SOA-2)."""
        src = "x = 1\n"
        result = axis1_scope(src)
        assert result["zyklomatik_source"] == "heuristik"


# ---------------------------------------------------------------------------
# TestAxis3Coupling — AK-5 (4 Exit-Kriterien)
# ---------------------------------------------------------------------------

class TestAxis3Coupling:
    """axis3_coupling: Martin-Kopplung + INV-K2-Guard."""

    def test_instability_calculation(self):
        """Exit-Kriterium AK-5/1: I = Ce/(Ca+Ce), z.B. Ca=3/Ce=1 -> I=0.25."""
        result = axis3_coupling(
            ca=3, ce=1, fan_in=2, call_tiefe=3,
            cross_layer=False, lsp_available=True, evidence="lsp:module.py",
        )
        assert result["instability"] == pytest.approx(0.25)

    def test_instability_zero_when_ca_ce_both_zero(self):
        """Exit-Kriterium AK-5/1 (Edge): Ca+Ce=0 -> I=0 (kein ZeroDivisionError)."""
        result = axis3_coupling(
            ca=0, ce=0, fan_in=0, call_tiefe=0,
            cross_layer=False, lsp_available=True, evidence="lsp:module.py",
        )
        assert result["instability"] == pytest.approx(0.0)

    def test_inv_k2_lsp_miss_no_marker_raises_value_error(self):
        """Exit-Kriterium AK-5/2: lsp_available=False ohne [LSP-MISS] im evidence -> ValueError."""
        with pytest.raises(ValueError):
            axis3_coupling(
                ca=1, ce=2, fan_in=1, call_tiefe=1,
                cross_layer=False, lsp_available=False,
                evidence="kein marker hier",
            )

    def test_inv_k2_lsp_miss_with_marker_passes(self):
        """Exit-Kriterium AK-5/2b: lsp_available=False MIT [LSP-MISS] -> kein Fehler, lsp_miss=True."""
        result = axis3_coupling(
            ca=1, ce=2, fan_in=1, call_tiefe=1,
            cross_layer=False, lsp_available=False,
            evidence="fallback [LSP-MISS] heuristik",
        )
        assert result["lsp_miss"] is True

    def test_cochange_degree_none_no_crash(self):
        """Exit-Kriterium AK-5/3: cochange_degree=None -> kein Crash, result["cochange_degree"] is None."""
        result = axis3_coupling(
            ca=2, ce=1, fan_in=1, call_tiefe=2,
            cross_layer=False, cochange_degree=None,
            lsp_available=True, evidence="lsp:x.py",
        )
        assert result["cochange_degree"] is None


# ---------------------------------------------------------------------------
# TestAxis6Locality — AK-6 (3 Exit-Kriterien)
# ---------------------------------------------------------------------------

class TestAxis6Locality:
    """axis6_locality: Streuungs-Klassifikation, Script-deterministisch."""

    def test_single_file_classification(self):
        """Exit-Kriterium AK-6/1: 1 Datei -> streuung_klasse='single_file', streuung_faktor=1.2."""
        result = axis6_locality(["src/foo.py"])
        assert result["streuung_klasse"] == "single_file"
        assert result["streuung_faktor"] == pytest.approx(1.2)

    def test_cross_layer_with_divergent_layers(self):
        """Exit-Kriterium AK-6/2: >1 Datei + 2 verschiedene Layer -> streuung_klasse='cross_layer', faktor=2.0."""
        result = axis6_locality(
            ["src/domain/foo.py", "src/infra/bar.py"],
            layer_mapping={
                "src/domain/foo.py": "domain",
                "src/infra/bar.py": "infra",
            },
        )
        assert result["streuung_klasse"] == "cross_layer"
        assert result["streuung_faktor"] == pytest.approx(2.0)

    def test_streuung_faktor_from_constant(self):
        """Exit-Kriterium AK-6/3: streuung_faktor stammt immer aus STREUUNG_FAKTOR-Konstante."""
        result = axis6_locality(["a.py", "b.py"])
        assert result["streuung_faktor"] in STREUUNG_FAKTOR.values()


# ---------------------------------------------------------------------------
# TestAxis2Operation — AK-7 (4 Exit-Kriterien)
# ---------------------------------------------------------------------------

class TestAxis2Operation:
    """axis2_operation: OP_MULT-Matrix, Hybrid."""

    def test_op_mult_mapping_all_five_types(self):
        """Exit-Kriterium AK-7/1: OP_MULT korrekt fuer alle 5 Typen."""
        expected = {"ADD": 1.0, "EXTEND": 1.3, "MODIFY": 1.6, "DELETE": 1.4, "MOVE": 1.2}
        for op, mult in expected.items():
            result = axis2_operation(op, 0.9, f"evidence for {op}")
            assert result["op_mult"] == pytest.approx(mult), f"Falsch fuer op_typ={op}"

    def test_case_normalization_add_equals_ADD(self):
        """Exit-Kriterium AK-7/2: case-Normalisierung — 'add' -> selber Output wie 'ADD'."""
        r_lower = axis2_operation("add", 0.8, "heuristik: lowercase")
        r_upper = axis2_operation("ADD", 0.8, "heuristik: lowercase")
        assert r_lower["op_mult"] == r_upper["op_mult"]
        assert r_lower["op_typ"].upper() == r_upper["op_typ"].upper()

    def test_unknown_op_typ_raises_value_error(self):
        """Exit-Kriterium AK-7/3: unbekannter op_typ -> ValueError."""
        with pytest.raises(ValueError):
            axis2_operation("RENAME", 0.5, "some evidence")

    def test_empty_evidence_raises_value_error(self):
        """Exit-Kriterium AK-7/4: leeres evidence -> ValueError (Evidence-Pflicht)."""
        with pytest.raises(ValueError):
            axis2_operation("ADD", 0.9, "")

    def test_whitespace_only_evidence_raises_value_error(self):
        """Edge-Case AK-7/4b: nur Whitespace im evidence -> ValueError."""
        with pytest.raises(ValueError):
            axis2_operation("ADD", 0.9, "   ")


# ---------------------------------------------------------------------------
# TestAxis4Cohesion — AK-8 SRP-Teil (3 Exit-Kriterien)
# ---------------------------------------------------------------------------

# Minimalklasse: 2 Methoden, beide nutzen self.x -> lcom=0
_COHESIVE_CLASS_SOURCE = """\
class Foo:
    def __init__(self):
        self.x = 0
    def method_a(self):
        return self.x + 1
    def method_b(self):
        return self.x - 1
"""

# Klasse mit 16 Methoden (> GOTT_KLASSE_METHOD_THRESHOLD=15)
_GOTT_KLASSE_SOURCE = (
    "class Big:\n"
    "    def __init__(self):\n"
    "        self.v = 0\n"
    + "".join(
        f"    def method_{i}(self):\n        return {i}\n"
        for i in range(16)
    )
)


class TestAxis4Cohesion:
    """axis4_cohesion: SRP-Defizit / LCOM-Heuristik + substrat_reuse."""

    def test_lcom_zero_when_all_methods_share_attribute(self):
        """Exit-Kriterium AK-8/1: alle Methoden teilen self.x -> lcom_heuristik=0.0."""
        result = axis4_cohesion(_COHESIVE_CLASS_SOURCE, class_name="Foo")
        assert result["lcom_heuristik"] == pytest.approx(0.0)

    def test_gott_klasse_indikator_true_above_threshold(self):
        """Exit-Kriterium AK-8/2: method_count > 15 -> gott_klasse_indikator=True."""
        result = axis4_cohesion(_GOTT_KLASSE_SOURCE, class_name="Big")
        assert result["gott_klasse_indikator"] is True

    def test_substrat_reuse_field_present(self):
        """Exit-Kriterium AK-8/3: substrat_reuse='kazman_kscore_axes.fragility_axes' im Output."""
        result = axis4_cohesion(_COHESIVE_CLASS_SOURCE)
        assert result["substrat_reuse"] == "kazman_kscore_axes.fragility_axes"

    def test_llm_verdict_without_evidence_raises(self):
        """Exit-Kriterium AK-8/6 (axis4-Seite): llm_verdict gesetzt + llm_evidence=None -> ValueError."""
        with pytest.raises(ValueError):
            axis4_cohesion(
                _COHESIVE_CLASS_SOURCE,
                llm_verdict="gott_klasse",
                llm_evidence=None,
            )


# ---------------------------------------------------------------------------
# TestAxis5Ocp — AK-8 OCP-Teil (3 Exit-Kriterien)
# ---------------------------------------------------------------------------

_ABSTRACT_SOURCE = """\
import abc

class MyABC(abc.ABC):
    @abc.abstractmethod
    def do_thing(self):
        pass
"""

_NO_OCP_SOURCE = """\
class Plain:
    def do_thing(self):
        return 42
"""


class TestAxis5Ocp:
    """axis5_ocp: OCP-Verfuegbarkeit, LSP-bevorzugt + INV-K2-analog."""

    def test_abstractmethod_detected_ocp_vorhanden(self):
        """Exit-Kriterium AK-8/4: @abstractmethod -> ocp_vorhanden=True."""
        result = axis5_ocp(_ABSTRACT_SOURCE, filename="my_abc.py")
        assert result["ocp_vorhanden"] is True

    def test_inv_k2_analog_lsp_miss_no_marker_raises(self):
        """Exit-Kriterium AK-8/5: lsp_available=False ohne [LSP-MISS] -> ValueError."""
        with pytest.raises(ValueError):
            axis5_ocp(
                _NO_OCP_SOURCE,
                lsp_available=False,
                # kein [LSP-MISS] im evidence
            )

    def test_inv_k2_analog_lsp_miss_with_marker_passes(self):
        """Edge-Case AK-8/5b: lsp_available=False MIT [LSP-MISS] -> kein Fehler."""
        result = axis5_ocp(
            _NO_OCP_SOURCE,
            lsp_available=False,
            evidence="[LSP-MISS] kein LSP verfuegbar",
        )
        assert result["lsp_miss"] is True

    def test_llm_verdict_without_evidence_raises(self):
        """Exit-Kriterium AK-8/6 (axis5-Seite): llm_verdict + llm_evidence=None -> ValueError."""
        with pytest.raises(ValueError):
            axis5_ocp(
                _ABSTRACT_SOURCE,
                llm_verdict="ocp_ok",
                llm_evidence=None,
            )
