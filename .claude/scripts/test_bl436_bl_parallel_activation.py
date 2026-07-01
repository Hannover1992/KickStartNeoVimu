#!/usr/bin/env python3
"""
test_bl436_bl_parallel_activation.py — TDD RED BL-436 D1.

Testet: bl_parallel FRAMEWORK_DEFAULT=False + per-Worktree-Aktivierung (NICHT via shared deployable).

RED-Tests (D1, alle 3 sollen FAIL sein solange Impl fehlt):
  1. test_bl_parallel_in_framework_defaults_false
  2. test_bl_parallel_per_worktree_override
  3. test_bl_parallel_not_in_shared_deployable

KEIN Production-Code in dieser Datei.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest import mock

import pytest

# ---------------------------------------------------------------------------
# Pfad-Setup: Scripts-Dir in sys.path eintragen
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_SCRIPTS_DIR = Path(__file__).resolve().parent

if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ---------------------------------------------------------------------------
# Test 1: bl_parallel in FRAMEWORK_DEFAULTS mit value=False + _owner="user"
#
# Erwartet: session_params_resolver stellt eine dedizierte Funktion
# get_bl_parallel_framework_default() bereit, die (False, "user") zurueckgibt.
# Aktuell existiert diese Funktion NICHT in session_params_resolver -> RED.
#
# Warum eigene Funktion statt FRAMEWORK_DEFAULTS-Direktzugriff?
# BL-436 fordert eine stabile, versionierte API fuer bl_parallel-Default-Abfragen
# (kein direkter Dict-Zugriff von aussen — das waere ein Encapsulation-Bruch).
# ---------------------------------------------------------------------------

def test_bl_parallel_in_framework_defaults_false():
    """
    FRAMEWORK_DEFAULTS muss bl_parallel mit value=False und _owner='user' enthalten.
    UND session_params_resolver muss eine dedizierte get_bl_parallel_framework_default()
    Funktion bereitstellen, die (value=False, owner='user') liefert.

    RED: get_bl_parallel_framework_default() existiert noch NICHT -> AttributeError.
    """
    import session_params_resolver as spr

    # Schritt 1: FRAMEWORK_DEFAULTS-Eintrag vorhanden (prueft Basis-Invariante)
    assert "bl_parallel" in spr.FRAMEWORK_DEFAULTS, (
        "bl_parallel fehlt in FRAMEWORK_DEFAULTS — muss als value=False, _owner='user' vorhanden sein"
    )
    entry = spr.FRAMEWORK_DEFAULTS["bl_parallel"]
    assert entry["value"] is False, f"FRAMEWORK_DEFAULTS['bl_parallel']['value'] muss False sein, ist {entry['value']!r}"
    assert entry.get("_owner") == "user", f"_owner muss 'user' sein, ist {entry.get('_owner')!r}"

    # Schritt 2: Dedizierte API-Funktion (BL-436 Anforderung — noch NICHT implementiert -> RED)
    # Diese Funktion soll als stabile API fuer andere Komponenten dienen
    # statt direktem FRAMEWORK_DEFAULTS["bl_parallel"]-Zugriff.
    assert hasattr(spr, "get_bl_parallel_framework_default"), (
        "session_params_resolver muss get_bl_parallel_framework_default() bereitstellen "
        "(BL-436 stabile API fuer bl_parallel-Default-Abfrage)"
    )
    value, owner = spr.get_bl_parallel_framework_default()
    assert value is False, f"get_bl_parallel_framework_default() value muss False sein, ist {value!r}"
    assert owner == "user", f"get_bl_parallel_framework_default() owner muss 'user' sein, ist {owner!r}"


# ---------------------------------------------------------------------------
# Test 2: per-Worktree-Aktivierung via resolve_bl_parallel(worktree_id)
#
# Erwartet: worktree_aware_params stellt resolve_bl_parallel(worktree_id) bereit.
# - Ohne Worktree-Override: liefert Framework-Default False
# - Mit CLAUDE_WORKTREE_ID gesetzt UND Worktree opted-in: liefert True
# Aktuell existiert resolve_bl_parallel() NICHT -> RED.
# ---------------------------------------------------------------------------

def test_bl_parallel_per_worktree_override():
    """
    worktree_aware_params.resolve_bl_parallel(worktree_id) muss:
      - Framework-Default False liefern wenn kein Override vorhanden
      - True liefern wenn der Worktree opted-in ist

    RED: resolve_bl_parallel() existiert noch NICHT in worktree_aware_params -> AttributeError.

    Testet per monkeypatch/env CLAUDE_WORKTREE_ID (INV-WORKTREE-3).
    """
    import worktree_aware_params as wap

    # Pruefe dass die Funktion existiert (wird RED sein bis Impl)
    assert hasattr(wap, "resolve_bl_parallel"), (
        "worktree_aware_params muss resolve_bl_parallel(worktree_id=None) bereitstellen "
        "(BL-436 per-Worktree bl_parallel-Aktivierung)"
    )

    # Ohne jeglichen Override: Framework-Default False erwartet
    with mock.patch.dict(os.environ, {}, clear=False):
        # CLAUDE_WORKTREE_ID entfernen falls gesetzt
        env_clean = {k: v for k, v in os.environ.items() if k != "CLAUDE_WORKTREE_ID"}
        with mock.patch.dict(os.environ, env_clean, clear=True):
            result_no_override = wap.resolve_bl_parallel(worktree_id=None)
    assert result_no_override is False, (
        f"resolve_bl_parallel(worktree_id=None) ohne Override muss False (Framework-Default) liefern, "
        f"ist {result_no_override!r}"
    )

    # Mit CLAUDE_WORKTREE_ID gesetzt + Worktree ist opted-in:
    # Der Mechanismus: worktree-spezifischer Params-Namespace enthaelt bl_parallel=true.
    # Wir mocken den Lookup so dass der Worktree-Namespace "wt-test" opted-in ist.
    with mock.patch.dict(os.environ, {"CLAUDE_WORKTREE_ID": "wt-test"}):
        # Mocke resolve_session_params so dass eine Worktree-Datei mit bl_parallel=true
        # "existiert" (kein echter Vault-IO notwendig).
        fake_params_content = "**bl_parallel:** true  _owner: user\n"
        fake_params_path = Path("/nonexistent/fake/_session_params_wt-test.md")

        with mock.patch.object(wap, "resolve_session_params",
                               return_value=(fake_params_path, "multi")):
            with mock.patch("pathlib.Path.exists", return_value=True):
                with mock.patch("pathlib.Path.read_text", return_value=fake_params_content):
                    result_opted_in = wap.resolve_bl_parallel(worktree_id="wt-test")

    assert result_opted_in is True, (
        f"resolve_bl_parallel('wt-test') mit opted-in Worktree muss True liefern, "
        f"ist {result_opted_in!r}"
    )


# ---------------------------------------------------------------------------
# Test 3: bl_parallel NICHT im shared deployable (_session_params.md)
#
# Erwartet: die shared Vault-Datei _session_params.md enthaelt bl_parallel
# NICHT (oder als =false). Aktuell ist bl_parallel: true drin -> RED.
#
# Dieser Test ist tolerant wenn Vault nicht erreichbar (skip).
# ---------------------------------------------------------------------------

def test_bl_parallel_not_in_shared_deployable():
    """
    Die shared Vault-Datei _session_params.md darf bl_parallel NICHT mit 'true'
    enthalten (Leak-Check). Der Wert gehoert NUR in worktree-spezifische
    _session_params_{worktree_id}.md Dateien.

    RED: Aktuell 'bl_parallel: true' in _session_params.md -> Test schlaegt fehl.

    Tolerant: Skip wenn Vault nicht erreichbar.
    """
    import session_params_resolver as spr

    # Vault-Root ermitteln (tolerant: skip wenn nicht erreichbar)
    vault_root = spr._find_vault_root()
    if vault_root is None:
        pytest.skip("Vault nicht erreichbar — Test 3 skip (tolerant)")

    # Shared deployable: _session_defaults.md bevorzugt, sonst _session_params.md
    shared_path = vault_root / "_session_defaults.md"
    if not shared_path.exists():
        shared_path = vault_root / "_session_params.md"

    if not shared_path.exists():
        pytest.skip(f"Shared deployable nicht gefunden unter {vault_root} — skip (tolerant)")

    content = shared_path.read_text(encoding="utf-8")

    import re

    # Suche nach bl_parallel=true (in verschiedenen Formaten)
    # Format 1: **bl_parallel:** true
    # Format 2: bl_parallel: true
    # Format 3: | bl_parallel | true |
    leak_pattern = re.compile(
        r"bl_parallel\s*[:\*]+\s*true",
        re.IGNORECASE | re.MULTILINE,
    )
    matches = leak_pattern.findall(content)

    assert not matches, (
        f"LEAK: '{shared_path}' enthaelt bl_parallel=true (Matches: {matches}). "
        f"bl_parallel darf NUR in worktree-spezifischen _session_params_{{worktree_id}}.md "
        f"auf 'true' gesetzt werden, NICHT im shared deployable (BL-436 D1)."
    )
