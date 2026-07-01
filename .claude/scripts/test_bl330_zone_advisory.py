#!/usr/bin/env python3
"""
test_bl330_zone_advisory.py — BL-330 AK-3 RED-Phase
Testet die noch-nicht-existierende Funktion zone_advisory() in workflow_zones.py.

Alle Tests MUESSEN FEHLSCHLAGEN (RED), da zone_advisory() noch nicht implementiert ist.
Keine Impl in workflow_zones.py — nur Tests.
"""
import pytest
import sys
import os

# Absoluter Pfad zum scripts-Verzeichnis
SCRIPTS_DIR = os.path.join(
    "C:", os.sep, "Users", "hanno", "RiderProjects", "OmniCommand-wtA",
    ".claude", "scripts"
)
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from workflow_zones import zone_advisory  # noqa: E402  — wird RED wegen ImportError


class TestZoneAdvisoryRedActivity:
    """Test 1: Rote Zone -> motor_faehig False, recommended_vehicle worker."""

    def test_zone_advisory_red_activity_not_motor_faehig(self):
        """_tdd_red ist explizit rot in ZONE_REGISTRY.
        zone_advisory muss motor_faehig=False und recommended_vehicle='worker' liefern.
        advisory_only muss immer True sein.
        """
        result = zone_advisory("_tdd_red", mode="false")
        assert isinstance(result, dict), "zone_advisory muss ein dict zurueckgeben"
        assert result["activity"] == "_tdd_red"
        assert result["zone"] == "red"
        assert result["motor_faehig"] is False, (
            "Rote Zone darf NIE motor-faehig sein (INV-VEHIKEL-2: rot=worker)"
        )
        assert result["recommended_vehicle"] == "worker", (
            "Rote Zone -> recommended_vehicle='worker'"
        )
        assert result["advisory_only"] is True
        assert "rationale" in result

    def test_zone_advisory_red_modusentscheidung_not_motor_faehig(self):
        """_sdf_berater_modusentscheidung ist explizit rot — zweite rote Activity fuer Robustheit."""
        result = zone_advisory("_sdf_berater_modusentscheidung", mode="normal")
        assert result["motor_faehig"] is False
        assert result["recommended_vehicle"] == "worker"
        assert result["advisory_only"] is True


class TestZoneAdvisoryGreenActivity:
    """Test 2: Gruene Zone -> motor_faehig True, recommended_vehicle workflow."""

    def test_zone_advisory_green_activity_motor_faehig(self):
        """dispatch_implement ist explizit gruen (green) in ZONE_REGISTRY.
        Bei mode='normal' oder 'fast' liefert resolve_vehicle 'workflow'.
        zone_advisory muss motor_faehig=True und recommended_vehicle='workflow' liefern.
        """
        result = zone_advisory("dispatch_implement", mode="normal")
        assert isinstance(result, dict), "zone_advisory muss ein dict zurueckgeben"
        assert result["activity"] == "dispatch_implement"
        assert result["zone"] == "green"
        assert result["motor_faehig"] is True, (
            "Gruene Zone @ mode=normal ist workflow-faehig -> motor_faehig=True"
        )
        assert result["recommended_vehicle"] == "workflow", (
            "Gruene Zone @ mode=normal -> recommended_vehicle='workflow'"
        )
        assert result["advisory_only"] is True

    def test_zone_advisory_green_statemaintain_motor_faehig(self):
        """_sdf_berater_statemaintain ist explizit gruen — zweite gruene Activity fuer Robustheit."""
        result = zone_advisory("_sdf_berater_statemaintain", mode="fast")
        assert result["motor_faehig"] is True
        assert result["recommended_vehicle"] == "workflow"
        assert result["advisory_only"] is True


class TestZoneAdvisoryAdvisoryOnly:
    """Test 3: advisory_only ist IMMER True, egal welche Activity oder Modus."""

    def test_zone_advisory_always_advisory_only_red(self):
        """Rote Activity: advisory_only muss True sein."""
        result = zone_advisory("_tdd_green", mode="false")
        assert result["advisory_only"] is True, (
            "advisory_only muss True sein — Berater schlaegt vor, entscheidet NIE"
        )

    def test_zone_advisory_always_advisory_only_green(self):
        """Gruene Activity: advisory_only muss True sein."""
        result = zone_advisory("_sdf_berater_batchende", mode="normal")
        assert result["advisory_only"] is True

    def test_zone_advisory_always_advisory_only_yellow(self):
        """Gelbe Activity: advisory_only muss True sein."""
        result = zone_advisory("_k_score", mode="fast")
        assert result["advisory_only"] is True

    def test_zone_advisory_always_advisory_only_unknown(self):
        """Unbekannte Activity (fail-safe rot): advisory_only muss True sein."""
        result = zone_advisory("_unknown_activity_xyz_not_in_registry", mode="normal")
        assert result["advisory_only"] is True

    def test_zone_advisory_always_advisory_only_none_activity(self):
        """None-Activity (fail-safe rot): advisory_only muss True sein."""
        result = zone_advisory(None, mode="normal")
        assert result["advisory_only"] is True


class TestZoneAdvisoryRationale:
    """Test 4: rationale ist immer ein nicht-leerer String."""

    def test_zone_advisory_has_rationale_red(self):
        """Rote Activity: rationale muss non-empty str sein."""
        result = zone_advisory("_i_golddefine", mode="false")
        assert "rationale" in result, "Ergebnis muss 'rationale'-Key enthalten"
        assert isinstance(result["rationale"], str), "rationale muss str sein"
        assert len(result["rationale"].strip()) > 0, "rationale darf nicht leer sein"

    def test_zone_advisory_has_rationale_green(self):
        """Gruene Activity: rationale muss non-empty str sein."""
        result = zone_advisory("dispatch_arc42", mode="fast")
        assert "rationale" in result
        assert isinstance(result["rationale"], str)
        assert len(result["rationale"].strip()) > 0

    def test_zone_advisory_has_rationale_yellow(self):
        """Gelbe Activity: rationale muss non-empty str sein."""
        result = zone_advisory("_sdf_berater_stageelevation", mode="fast")
        assert "rationale" in result
        assert isinstance(result["rationale"], str)
        assert len(result["rationale"].strip()) > 0

    def test_zone_advisory_has_rationale_unknown(self):
        """Unbekannte Activity (fail-safe): rationale muss non-empty str sein."""
        result = zone_advisory("_totally_unknown_berater_XYZ", mode="normal")
        assert "rationale" in result
        assert isinstance(result["rationale"], str)
        assert len(result["rationale"].strip()) > 0


class TestZoneAdvisoryReturnShape:
    """Zusatz: Vollstaendige Keys im Ergebnis-Dict."""

    def test_zone_advisory_return_has_all_keys(self):
        """Dict muss alle 6 Pflicht-Keys enthalten."""
        result = zone_advisory("dispatch_implement", mode="normal")
        required_keys = {"activity", "zone", "recommended_vehicle", "motor_faehig",
                         "advisory_only", "rationale"}
        missing = required_keys - set(result.keys())
        assert not missing, f"Fehlende Keys: {missing}"

    def test_zone_advisory_motor_faehig_is_bool(self):
        """motor_faehig muss bool sein (nicht truthy int o.ae.)."""
        result = zone_advisory("dispatch_implement", mode="normal")
        assert isinstance(result["motor_faehig"], bool), (
            f"motor_faehig muss bool sein, war: {type(result['motor_faehig'])}"
        )

    def test_zone_advisory_recommended_vehicle_valid(self):
        """recommended_vehicle muss in {workflow, advisory, worker} liegen."""
        for activity, mode in [
            ("dispatch_implement", "normal"),
            ("_tdd_red", "false"),
            ("_k_score", "fast"),
        ]:
            result = zone_advisory(activity, mode=mode)
            assert result["recommended_vehicle"] in {"workflow", "advisory", "worker"}, (
                f"Ungueltig recommended_vehicle='{result['recommended_vehicle']}' "
                f"fuer {activity}@{mode}"
            )
