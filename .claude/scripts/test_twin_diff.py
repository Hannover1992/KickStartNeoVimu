"""
TDD-RED Tests fuer twin_diff.py (BL-308: Twin-Diff-Pflicht-Gate vor BATCH_DONE).

API-Kontrakt (abgeleitet aus BL-308_Spec.md AK-3/9/10/5/11/13/4/8):

conformance_diff(actual, reference, subst_map=None) -> dict
    5-Schritt-Anker-Mechanik (AK-9):
    1. Substitutions-Map laden/normalisieren
    2. Anker aus actual + reference extrahieren
    3. Substitution auf reference-Anker anwenden
    4. Anker-Mengen vergleichen (Identitaet, nicht Zeilen-Text)
    5. Rest-Delta via Verdikt-Matrix klassifizieren
    Gibt zurueck: {
        'conformant': bool,
        'deviations': list[{
            'path': str | None,
            'anchor': str,
            'expected': str | None,
            'actual': str | None,
            'kind': str  # 'missing_in_actual' | 'missing_in_reference' | 'mismatch'
        }]
    }
    actual: dict (Anker-Menge als set/list) oder str (raw Anker-Text, zeilenweise)
    reference: dict oder str

format_deviations(deviations: list) -> str
    5-Felder-Schema pro Deviation (AK-5/11):
    Felder: anchor, expected, actual, kind, severity
    Gibt Markdown-String zurueck.

parse_deviations(md: str) -> list
    Parst format_deviations-Output zurueck zu list[dict] (round-trip, AK-11).

twin_path(bl_folder: str) -> str | Path
    Twin-Ordner-Konvention (AK-13): gibt {bl_folder}/Twin/ zurueck.

twin_diff_gate(actual, reference, twin_available: bool, deviations_md=None) -> dict
    Gate-Decider VOR BATCH_DONE (AK-4/8):
    Gibt zurueck: {
        'pass': bool,
        'deviations': list,
        'verdict': str  # 'PASS' | 'FAIL' | 'SKIPPED'
    }
    twin_available=False -> graceful PASS (Proportionalitaet, AK-6/8)
    twin_available=True + non-conformant -> FAIL (blockt BATCH_DONE)
    twin_available=True + conformant -> PASS

twin_ref_schema() -> dict
    Schema-Beschreibung des twin_ref-Feldes (AK-8):
    Gibt zurueck: {'allowed_values': list, 'default': None | str}

validate_twin_ref(value) -> bool
    Validiert einen twin_ref-Wert gegen das Schema (AK-8):
    Erlaubt: 'IS-IDENTICAL' | 'IS-ADAPTED' | 'IS-NEW' | None
    Jeden anderen Wert -> False
"""

import pytest
from pathlib import Path

# Import wird nach Implementierung gruen — jetzt RED (ImportError)
from twin_diff import (
    conformance_diff,
    format_deviations,
    parse_deviations,
    twin_path,
    twin_diff_gate,
    twin_ref_schema,
    validate_twin_ref,
)


# ---------------------------------------------------------------------------
# Gruppe 1: conformance_diff — AK-3/9 Konformanz-Diff-Mechanik
# ---------------------------------------------------------------------------

class TestConformanceDiffConformant:
    """AK-3/9: identische Inputs -> conformant=True, leere deviations."""

    def test_identical_dict_anchors_conformant(self):
        """Identische Anker-Mengen (dict-Format) -> conformant."""
        actual = {"anchors": [".btn-primary", ".btn-secondary"]}
        reference = {"anchors": [".btn-primary", ".btn-secondary"]}
        result = conformance_diff(actual, reference)
        assert result["conformant"] is True
        assert result["deviations"] == []

    def test_identical_string_anchors_conformant(self):
        """Identische Anker als str (zeilenweise) -> conformant."""
        actual = ".btn-primary\n.btn-secondary"
        reference = ".btn-primary\n.btn-secondary"
        result = conformance_diff(actual, reference)
        assert result["conformant"] is True
        assert result["deviations"] == []

    def test_order_independent_conformant(self):
        """Mengen-Vergleich ist reihenfolge-unabhaengig (AK-9 Schritt 4)."""
        actual = {"anchors": [".alpha", ".beta", ".gamma"]}
        reference = {"anchors": [".gamma", ".alpha", ".beta"]}
        result = conformance_diff(actual, reference)
        assert result["conformant"] is True
        assert result["deviations"] == []


class TestConformanceDiffNonConformant:
    """AK-3/9: nicht-identische Inputs -> conformant=False + deviations gelistet."""

    def test_missing_anchor_in_actual(self):
        """Fehlender Anker in actual -> non-conformant, deviation mit kind=missing_in_actual."""
        actual = {"anchors": [".btn-primary"]}
        reference = {"anchors": [".btn-primary", ".btn-danger"]}
        result = conformance_diff(actual, reference)
        assert result["conformant"] is False
        assert len(result["deviations"]) == 1
        dev = result["deviations"][0]
        assert dev["anchor"] == ".btn-danger"
        assert dev["kind"] == "missing_in_actual"

    def test_extra_anchor_in_actual(self):
        """Extra Anker in actual (nicht in reference) -> non-conformant, kind=missing_in_reference."""
        actual = {"anchors": [".btn-primary", ".btn-extra"]}
        reference = {"anchors": [".btn-primary"]}
        result = conformance_diff(actual, reference)
        assert result["conformant"] is False
        devs = result["deviations"]
        assert any(d["anchor"] == ".btn-extra" and d["kind"] == "missing_in_reference" for d in devs)

    def test_multiple_deviations_all_listed(self):
        """Mehrere Abweichungen alle in deviations gelistet."""
        actual = {"anchors": ["methodA", "methodC"]}
        reference = {"anchors": ["methodA", "methodB", "methodD"]}
        result = conformance_diff(actual, reference)
        assert result["conformant"] is False
        anchors_in_devs = {d["anchor"] for d in result["deviations"]}
        assert "methodB" in anchors_in_devs
        assert "methodD" in anchors_in_devs

    def test_deviation_structure_has_required_fields(self):
        """Jede Deviation hat Pflicht-Felder: anchor, kind (AK-9 Schritt 5)."""
        actual = {"anchors": [".a"]}
        reference = {"anchors": [".a", ".b"]}
        result = conformance_diff(actual, reference)
        assert result["conformant"] is False
        for dev in result["deviations"]:
            assert "anchor" in dev
            assert "kind" in dev


class TestConformanceDiffSubstitutionMap:
    """AK-10: Substitutions-Map normalisiert erwartbare Varianz vor Vergleich."""

    def test_subst_map_makes_diff_conformant(self):
        """Mit Subst-Map (QDVS->QDVTP) wird Diff leer -> conformant (AK-10)."""
        actual = {"anchors": [".QDVTP-card"]}
        reference = {"anchors": [".QDVS-card"]}
        subst_map = [{"from": "QDVS", "to": "QDVTP"}]
        result = conformance_diff(actual, reference, subst_map=subst_map)
        assert result["conformant"] is True
        assert result["deviations"] == []

    def test_subst_map_missing_file_empty_map(self):
        """Ohne Subst-Map -> leere Map (Identitaets-Diff, kein Fehler, AK-10)."""
        actual = {"anchors": [".QDVTP-card"]}
        reference = {"anchors": [".QDVS-card"]}
        result = conformance_diff(actual, reference, subst_map=None)
        # Ohne Map bleiben QDVS != QDVTP -> non-conformant
        assert result["conformant"] is False

    def test_subst_map_partial_substitution(self):
        """Subst-Map substituiert nur passende Anker; nicht-passende bleiben."""
        actual = {"anchors": [".QDVTP-card", ".QDVTP-header"]}
        reference = {"anchors": [".QDVS-card", ".QDVS-header"]}
        subst_map = [{"from": "QDVS", "to": "QDVTP"}]
        result = conformance_diff(actual, reference, subst_map=subst_map)
        assert result["conformant"] is True


# ---------------------------------------------------------------------------
# Gruppe 2: format_deviations + parse_deviations — AK-5/11 deviations.md Schema
# ---------------------------------------------------------------------------

class TestDeviationsSchema:
    """AK-5/11: 5-Felder-Schema round-trip."""

    def test_format_deviations_produces_string(self):
        """format_deviations gibt Markdown-String aus."""
        devs = [
            {
                "anchor": ".btn-danger",
                "expected": ".btn-danger (im Twin)",
                "actual": "(fehlt in Impl)",
                "kind": "missing_in_actual",
                "severity": "high",
            }
        ]
        result = format_deviations(devs)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_format_deviations_contains_all_five_fields(self):
        """Jeder Eintrag enthaelt alle 5 Pflicht-Felder (AK-11)."""
        devs = [
            {
                "anchor": "methodPay",
                "expected": "methodPay(amount: number)",
                "actual": "(fehlt)",
                "kind": "missing_in_actual",
                "severity": "critical",
            }
        ]
        result = format_deviations(devs)
        assert "anchor" in result or "methodPay" in result
        assert "expected" in result or "methodPay(amount: number)" in result
        assert "actual" in result
        assert "kind" in result or "missing_in_actual" in result
        assert "severity" in result or "critical" in result

    def test_parse_deviations_round_trip(self):
        """format + parse = round-trip (AK-11)."""
        devs_in = [
            {
                "anchor": ".card-header",
                "expected": ".card-header (Twin)",
                "actual": "(nicht vorhanden)",
                "kind": "missing_in_actual",
                "severity": "medium",
            }
        ]
        md = format_deviations(devs_in)
        devs_out = parse_deviations(md)
        assert isinstance(devs_out, list)
        assert len(devs_out) == 1
        parsed = devs_out[0]
        assert parsed["anchor"] == ".card-header"
        assert parsed["severity"] == "medium"

    def test_parse_deviations_empty_md(self):
        """Leere/leeres Markdown -> leere Liste (kein Fehler)."""
        result = parse_deviations("")
        assert result == []

    def test_parse_deviations_multiple_entries(self):
        """Mehrere Eintraege round-trip."""
        devs_in = [
            {"anchor": "a1", "expected": "e1", "actual": "ac1", "kind": "mismatch", "severity": "low"},
            {"anchor": "a2", "expected": "e2", "actual": "ac2", "kind": "missing_in_actual", "severity": "high"},
        ]
        md = format_deviations(devs_in)
        devs_out = parse_deviations(md)
        assert len(devs_out) == 2
        anchors = {d["anchor"] for d in devs_out}
        assert {"a1", "a2"} == anchors


# ---------------------------------------------------------------------------
# Gruppe 3: twin_path — AK-13 Twin-Ordner-Konvention
# ---------------------------------------------------------------------------

class TestTwinPath:
    """AK-13: twin_path gibt {bl_folder}/Twin/ als vault-resolved Pfad zurueck."""

    def test_twin_path_appends_twin_subfolder(self):
        """twin_path haengt 'Twin' an den bl_folder an."""
        bl = "/vault/Backlog/BL-308-example"
        result = twin_path(bl)
        p = Path(result)
        assert p.name == "Twin"
        assert str(p.parent) == bl or p.parent == Path(bl)

    def test_twin_path_returns_path_or_string(self):
        """Rueckgabe ist str oder pathlib.Path."""
        bl = "/vault/Backlog/BL-308-example"
        result = twin_path(bl)
        assert isinstance(result, (str, Path))

    def test_twin_path_with_windows_style(self):
        """Funktioniert auch mit Windows-Pfaden."""
        bl = r"C:\Users\hanno\Vault\Backlog\BL-308"
        result = twin_path(bl)
        assert "Twin" in str(result)


# ---------------------------------------------------------------------------
# Gruppe 4: twin_diff_gate — AK-4/8 Gate-Decider vor BATCH_DONE
# ---------------------------------------------------------------------------

class TestTwinDiffGate:
    """AK-4/8: twin_diff_gate entscheidet VOR BATCH_DONE."""

    def test_gate_pass_when_no_twin_available(self):
        """twin_available=False -> graceful PASS (Proportionalitaet, AK-6)."""
        result = twin_diff_gate(
            actual={"anchors": [".foo"]},
            reference={"anchors": [".bar"]},
            twin_available=False,
        )
        assert result["pass"] is True
        assert result["verdict"] == "PASS"

    def test_gate_pass_when_conformant(self):
        """twin_available=True + konformer Input -> PASS."""
        actual = {"anchors": [".btn-primary"]}
        reference = {"anchors": [".btn-primary"]}
        result = twin_diff_gate(actual, reference, twin_available=True)
        assert result["pass"] is True
        assert result["verdict"] == "PASS"

    def test_gate_fail_when_drift_detected(self):
        """twin_available=True + Drift -> FAIL (blockt BATCH_DONE, AK-4)."""
        actual = {"anchors": [".btn-old"]}
        reference = {"anchors": [".btn-new"]}
        result = twin_diff_gate(actual, reference, twin_available=True)
        assert result["pass"] is False
        assert result["verdict"] == "FAIL"

    def test_gate_fail_includes_deviations(self):
        """FAIL-Result enthaelt deviations-Liste mit mindestens 1 Eintrag."""
        actual = {"anchors": []}
        reference = {"anchors": [".btn-primary"]}
        result = twin_diff_gate(actual, reference, twin_available=True)
        assert result["pass"] is False
        assert len(result["deviations"]) >= 1

    def test_gate_result_always_has_required_keys(self):
        """Ergebnis-Dict hat immer pass, deviations, verdict."""
        result = twin_diff_gate({"anchors": []}, {"anchors": []}, twin_available=False)
        assert "pass" in result
        assert "deviations" in result
        assert "verdict" in result


# ---------------------------------------------------------------------------
# Gruppe 5: twin_ref_schema + validate_twin_ref — AK-8 Schema-Validierung
# ---------------------------------------------------------------------------

class TestTwinRefSchema:
    """AK-8: twin_ref-Schema-Validierung."""

    def test_schema_has_allowed_values(self):
        """twin_ref_schema() gibt allowed_values zurück."""
        schema = twin_ref_schema()
        assert "allowed_values" in schema
        allowed = schema["allowed_values"]
        assert "IS-IDENTICAL" in allowed
        assert "IS-ADAPTED" in allowed
        assert "IS-NEW" in allowed

    def test_schema_default_is_null(self):
        """Default von twin_ref ist null/None (abwaerts-kompatibel, AK-8)."""
        schema = twin_ref_schema()
        assert schema.get("default") is None

    def test_valid_values_accepted(self):
        """Alle Enum-Werte sind gueltig."""
        for val in ("IS-IDENTICAL", "IS-ADAPTED", "IS-NEW"):
            assert validate_twin_ref(val) is True, f"Expected {val!r} to be valid"

    def test_null_default_valid(self):
        """None (Default) ist gueltig (kein twin_ref -> Gate skipt)."""
        assert validate_twin_ref(None) is True

    def test_invalid_value_rejected(self):
        """Beliebiger anderer Wert -> Schema-Fehler (False)."""
        assert validate_twin_ref("IS-DIFFERENT") is False
        assert validate_twin_ref("identical") is False
        assert validate_twin_ref("") is False
        assert validate_twin_ref(42) is False
