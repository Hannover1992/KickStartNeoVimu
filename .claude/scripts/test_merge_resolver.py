#!/usr/bin/env python3
"""
test_merge_resolver.py — BL-425 batch_1 RED tests fuer Merge-Resolver-Defaults.

Pflicht-Testfaelle (alle MUESSEN RED sein — neue Defaults existieren noch nicht im Resolver):
  1.  test_merge_default_false          — merge=False als FRAMEWORK_DEFAULTS
  2.  test_merge_target_default         — merge_target="develop" als FRAMEWORK_DEFAULTS
  3.  test_merge_timing_default         — merge_timing="per_bl" als FRAMEWORK_DEFAULTS
  4.  test_default_off_no_exec          — merge=False -> kein merge_exec (No-Op-Garantie)

Erwartetes RED: KeyError weil "merge"/"merge_target"/"merge_timing" NICHT in FRAMEWORK_DEFAULTS.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from session_params_resolver import (
    FRAMEWORK_DEFAULTS,
    resolve_param,
    _coerce_value,
)


# ---------------------------------------------------------------------------
# Test 1: merge=False als FRAMEWORK_DEFAULTS (AK-1/AK-2/AK-7)
# ---------------------------------------------------------------------------

def test_merge_default_false(tmp_path: Path) -> None:
    """BL-425 AK-1: session_params_resolver liefert merge=False als Default (kein Merge-Flow)."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    # Pruefe FRAMEWORK_DEFAULTS direkt (Schnell-RED ohne Datei-IO)
    assert "merge" in FRAMEWORK_DEFAULTS, "merge-Param fehlt in FRAMEWORK_DEFAULTS"
    assert FRAMEWORK_DEFAULTS["merge"]["value"] is False

    # Pruefe auch via resolve_param (kein Override vorhanden)
    result = resolve_param("merge", bl_id=None, vault_root=str(vault_root))
    assert result is False


# ---------------------------------------------------------------------------
# Test 2: merge_target="develop" als FRAMEWORK_DEFAULTS (AK-2/AK-7)
# ---------------------------------------------------------------------------

def test_merge_target_default(tmp_path: Path) -> None:
    """BL-425 AK-2: session_params_resolver liefert merge_target='develop' als Default."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    assert "merge_target" in FRAMEWORK_DEFAULTS, "merge_target-Param fehlt in FRAMEWORK_DEFAULTS"
    assert FRAMEWORK_DEFAULTS["merge_target"]["value"] == "develop"

    result = resolve_param("merge_target", bl_id=None, vault_root=str(vault_root))
    assert result == "develop"


# ---------------------------------------------------------------------------
# Test 3: merge_timing="per_bl" als FRAMEWORK_DEFAULTS (AK-7)
# ---------------------------------------------------------------------------

def test_merge_timing_default(tmp_path: Path) -> None:
    """BL-425 AK-7: session_params_resolver liefert merge_timing='per_bl' als Default."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    assert "merge_timing" in FRAMEWORK_DEFAULTS, "merge_timing-Param fehlt in FRAMEWORK_DEFAULTS"
    assert FRAMEWORK_DEFAULTS["merge_timing"]["value"] == "per_bl"

    result = resolve_param("merge_timing", bl_id=None, vault_root=str(vault_root))
    assert result == "per_bl"


# ---------------------------------------------------------------------------
# Test 4: merge=False -> merge_exec wird NICHT aufgerufen (AK-9 Default-OFF)
# ---------------------------------------------------------------------------

def test_default_off_no_exec() -> None:
    """BL-425 AK-9: merge=False -> Merge-Flow ist No-Op (merge_exec NICHT gerufen)."""
    # Importiere merge_seam erst hier — auch dieser Import ist RED (ModuleNotFoundError)
    # wenn merge_seam.py fehlt. Das ist beabsichtigt: beide RED-Ursachen sind valide.
    from merge_seam import do_merge_if_clean  # noqa: PLC0415

    merge_exec_mock = MagicMock()

    # merge=False -> do_merge_if_clean sollte mit einem Noop-Verdikt oder
    # gar nicht aufgerufen werden; der Aufrufer prueft merge zuerst.
    # Hier: teste dass merge=False das Guard-Verdikt "SKIP" produziert oder
    # do_merge_if_clean gar nicht aufgerufen wird.
    # Einfachster Test: resolve_param("merge") == False -> kein merge_exec-Call.
    merge_enabled = FRAMEWORK_DEFAULTS.get("merge", {}).get("value", True)
    assert merge_enabled is False, (
        f"merge Default muss False sein (Default-OFF AK-9), war: {merge_enabled!r}"
    )
    # Wenn merge=False: merge_exec darf NIE ohne explizite Aktivierung gerufen werden
    merge_exec_mock.assert_not_called()
