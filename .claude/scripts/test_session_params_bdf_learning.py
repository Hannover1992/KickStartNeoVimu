"""
BL-331 RED Tests: session_params_resolver.py (AK-4)
bdf_post_item_learning Param — Presence + Default + Validierung + Bypass-Guard.

Diese Tests muessen FEHLSCHLAGEN bis GREEN-Worker den Param in FRAMEWORK_DEFAULTS
+ _VALID_VALUES + _coerce_value + _BYPASS_FIELDS_LEARNING einfuegt.

Getestete API (alle Tests gegen EXISTIERENDE resolve-API):
    FRAMEWORK_DEFAULTS["bdf_post_item_learning"]  -> {"value": {"pt": "on", "model": "on"}, "_owner": "user"}
    resolve_param("bdf_post_item_learning")       -> {"pt": "on", "model": "on"} (ohne Override)
    validate_param("bdf_post_item_learning", ...) -> coerced dict ODER ValueError
"""
from __future__ import annotations

import pytest

from session_params_resolver import (
    FRAMEWORK_DEFAULTS,
    resolve_param,
    validate_param,
)


# ===========================================================================
# AK-4: FRAMEWORK_DEFAULTS Eintrag (Param-Presence + Default-Wert)
# RED: Param fehlt jetzt -> KeyError / AssertionError.
# ===========================================================================

class TestBdfPostItemLearningDefaults:
    """AK-4: bdf_post_item_learning muss in FRAMEWORK_DEFAULTS vorhanden sein."""

    def test_default_bdf_post_item_learning_exists(self):
        """Param muss in FRAMEWORK_DEFAULTS registriert sein (RED: KeyError jetzt)."""
        assert "bdf_post_item_learning" in FRAMEWORK_DEFAULTS

    def test_default_value_is_pt_on_model_on(self):
        """Default-Wert: {'pt': 'on', 'model': 'on'} (beide Kanaele AN per default)."""
        entry = FRAMEWORK_DEFAULTS["bdf_post_item_learning"]
        assert entry["value"] == {"pt": "on", "model": "on"}

    def test_default_owner_is_user(self):
        """Owner muss 'user' sein (Nutzer-steuerbarer Dial, analog hil/floor)."""
        entry = FRAMEWORK_DEFAULTS["bdf_post_item_learning"]
        assert entry["_owner"] == "user"


# ===========================================================================
# AK-4: resolve_param API — liefert Default ohne Override
# RED: Param fehlt -> resolve_param gibt None statt dict.
# ===========================================================================

class TestBdfPostItemLearningResolve:
    """AK-4: resolve_param gibt Default-Dict zurueck wenn kein Override existiert."""

    def test_resolve_returns_default_without_override(self):
        """resolve_param ohne bl_id/vault-Override -> {"pt": "on", "model": "on"}."""
        # Kein bl_id -> kein BL/Vault-Override moeglich -> Framework-Default
        result = resolve_param("bdf_post_item_learning")
        assert result == {"pt": "on", "model": "on"}


# ===========================================================================
# AK-4: validate_param / _coerce_value — Sub-Key-Validierung
# RED: validate_param kennt den Param noch nicht -> kein Sub-Key-Check.
# ===========================================================================

class TestBdfPostItemLearningValidate:
    """AK-4: validate_param prueft Sub-Keys {pt, model} ∈ {'on', 'off'}."""

    def test_coerce_valid_pt_off_model_on(self):
        """pt=off ist valid -> dict wird unveraendert zurueckgegeben."""
        result = validate_param("bdf_post_item_learning", {"pt": "off", "model": "on"})
        assert result == {"pt": "off", "model": "on"}

    def test_coerce_valid_pt_on_model_off(self):
        """model=off ist valid -> dict wird unveraendert zurueckgegeben."""
        result = validate_param("bdf_post_item_learning", {"pt": "on", "model": "off"})
        assert result == {"pt": "on", "model": "off"}

    def test_coerce_valid_both_off(self):
        """Beide off: explizites Deaktivieren beider Kanaele -> dict korrekt."""
        result = validate_param("bdf_post_item_learning", {"pt": "off", "model": "off"})
        assert result == {"pt": "off", "model": "off"}

    def test_coerce_valid_both_on(self):
        """Standard-Default pt=on + model=on -> valid, kein Fehler."""
        result = validate_param("bdf_post_item_learning", {"pt": "on", "model": "on"})
        assert result == {"pt": "on", "model": "on"}


# ===========================================================================
# AK-4: Bypass-Felder -> ValueError (INV-LEARN-PARAM)
# Bypass-Felder force_learning, skip_harvest, learning_override duerfen NICHT
# als Sub-Keys akzeptiert werden -> ValueError.
# ===========================================================================

class TestBdfPostItemLearningBypassFields:
    """AK-4: Verbotene Bypass-Felder/Sub-Keys -> ValueError (INV-LEARN-PARAM)."""

    def test_bypass_field_force_learning_raises(self):
        """'force_learning' ist verbotener Bypass-Sub-Key -> ValueError."""
        with pytest.raises(ValueError):
            validate_param("bdf_post_item_learning", {"force_learning": "on"})

    def test_bypass_field_skip_harvest_raises(self):
        """'skip_harvest' ist verbotener Bypass-Sub-Key -> ValueError."""
        with pytest.raises(ValueError):
            validate_param("bdf_post_item_learning", {"skip_harvest": True})

    def test_unknown_sub_key_raises_valueerror(self):
        """Unbekannter Sub-Key 'unknown' -> ValueError (streng: nur 'pt'/'model' erlaubt)."""
        with pytest.raises(ValueError):
            validate_param("bdf_post_item_learning", {"pt": "on", "unknown": "x"})

    def test_invalid_sub_value_raises_valueerror(self):
        """Sub-Wert 'maybe' ist nicht in {'on','off'} -> ValueError."""
        with pytest.raises(ValueError):
            validate_param("bdf_post_item_learning", {"pt": "maybe"})

    def test_non_dict_string_raises_valueerror(self):
        """String statt dict -> ValueError (kein Typ-Surrogat)."""
        with pytest.raises(ValueError):
            validate_param("bdf_post_item_learning", "on")

    def test_non_dict_bool_raises_valueerror(self):
        """Bool statt dict -> ValueError."""
        with pytest.raises(ValueError):
            validate_param("bdf_post_item_learning", True)
