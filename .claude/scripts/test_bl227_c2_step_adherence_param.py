#!/usr/bin/env python3
"""
test_bl227_c2_step_adherence_param.py — BL-227 C-2: Param-Mechanik fuer step_adherence_reminder.

AK-5: Toggle in session_params, off/on/default (Framework=off) funktional.
AK-6: 3-stufige Resolution (BL > Vault > Framework), kein Skip.
AK-7: Writer-Identity-Lock — nur /_param darf den Toggle schreiben.
AK-8: Param-Name step_adherence_reminder, Default=off, global (kein per-Orchestrator-Key).

REQCHECK-S1 WARNING (M2-Semantik): M2-Verhalten ist "optional/konfigurierbar" — der Param
kennt nur off/on (keine M2-spezifische Auspraegung). Modus-Gating ist C-3-Scope.
Der Toggle steuert ob der Reminder-Mechanismus prinzipiell aktiv ist (on) oder nicht (off).
M2-Feinkonfiguration bleibt C-3 (Modus-Gate liest diesen Toggle als Voraussetzung).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()

from session_params_resolver import (
    FRAMEWORK_DEFAULTS,
    _VALID_VALUES,
    resolve_param,
    resolve_all_params,
    validate_param,
    _parse_session_params_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_params_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


# ---------------------------------------------------------------------------
# AK-8 — Param-Name + Default + Global-Granularitaet (Schema-Inspektion)
# ---------------------------------------------------------------------------

def test_ak8_param_name_exists_in_framework_defaults() -> None:
    """AK-8: FRAMEWORK_DEFAULTS enthaelt genau den Key 'step_adherence_reminder'."""
    assert "step_adherence_reminder" in FRAMEWORK_DEFAULTS, (
        "FRAMEWORK_DEFAULTS muss 'step_adherence_reminder' enthalten (AK-8)."
    )


def test_ak8_default_is_off() -> None:
    """AK-8: Default-Wert = 'off' (additive Schicht standardmaessig still)."""
    entry = FRAMEWORK_DEFAULTS["step_adherence_reminder"]
    assert entry["value"] == "off", (
        f"Default muss 'off' sein, ist {entry['value']!r} (AK-8)."
    )


def test_ak8_owner_is_user() -> None:
    """AK-8: _owner = 'user' (nur /_param darf schreiben, AK-7/INV-OWNER-1)."""
    entry = FRAMEWORK_DEFAULTS["step_adherence_reminder"]
    assert entry["_owner"] == "user", (
        f"_owner muss 'user' sein, ist {entry['_owner']!r} (AK-8/AK-7)."
    )


def test_ak8_no_per_orchestrator_key() -> None:
    """AK-8: Kein per-Orchestrator-Key in FRAMEWORK_DEFAULTS (YAGNI, v1.0 global)."""
    orchestrator_variants = [
        "step_adherence_reminder_a",
        "step_adherence_reminder_idf",
        "step_adherence_reminder_sdf",
        "step_adherence_reminder_sc",
        "step_adherence_reminder_post",
        "step_adherence_reminder_i",
    ]
    for key in orchestrator_variants:
        assert key not in FRAMEWORK_DEFAULTS, (
            f"Per-Orchestrator-Key '{key}' darf in v1.0 NICHT in FRAMEWORK_DEFAULTS sein (AK-8 YAGNI)."
        )


def test_ak8_valid_values_defined() -> None:
    """AK-8: _VALID_VALUES enthaelt genau {off, on} fuer step_adherence_reminder."""
    assert "step_adherence_reminder" in _VALID_VALUES, (
        "_VALID_VALUES muss 'step_adherence_reminder' kennen."
    )
    assert _VALID_VALUES["step_adherence_reminder"] == {"off", "on"}, (
        f"Gueltige Werte muessen {{off, on}} sein, sind {_VALID_VALUES['step_adherence_reminder']!r}."
    )


# ---------------------------------------------------------------------------
# AK-5 — Toggle AUS/AN/Default funktional
# ---------------------------------------------------------------------------

def test_ak5_framework_default_off(tmp_path: Path) -> None:
    """AK-5: Kein expliziter Wert -> Framework-Default 'off' (AK-8 Default=off)."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    result = resolve_param("step_adherence_reminder", bl_id=None, vault_root=str(vault_root))
    assert result == "off", (
        f"Framework-Default muss 'off' sein, got {result!r} (AK-5)."
    )


def test_ak5_param_on_via_vault(tmp_path: Path) -> None:
    """AK-5: Vault setzt Param auf 'on' -> resolve_param liefert 'on'."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    _write_params_file(
        vault_root / "_session_defaults.md",
        "**step_adherence_reminder:** on _owner: user\n",
    )

    result = resolve_param("step_adherence_reminder", bl_id=None, vault_root=str(vault_root))
    assert result == "on", f"Vault-Override 'on' erwartet, got {result!r} (AK-5)."


def test_ak5_param_off_via_vault(tmp_path: Path) -> None:
    """AK-5: Vault setzt Param explizit auf 'off' -> resolve_param liefert 'off'."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    _write_params_file(
        vault_root / "_session_defaults.md",
        "**step_adherence_reminder:** off _owner: user\n",
    )

    result = resolve_param("step_adherence_reminder", bl_id=None, vault_root=str(vault_root))
    assert result == "off", f"Vault-Override 'off' erwartet, got {result!r} (AK-5)."


def test_ak5_in_resolve_all(tmp_path: Path) -> None:
    """AK-5: resolve_all_params enthaelt step_adherence_reminder mit Default 'off'."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    all_p = resolve_all_params(bl_id=None, vault_root=str(vault_root))
    assert "step_adherence_reminder" in all_p, (
        "resolve_all_params muss 'step_adherence_reminder' enthalten (AK-5)."
    )
    assert all_p["step_adherence_reminder"] == "off", (
        f"Default in resolve_all muss 'off' sein, got {all_p['step_adherence_reminder']!r}."
    )


# ---------------------------------------------------------------------------
# AK-6 — 3-stufige Resolution (BL > Vault > Framework), kein Skip
# ---------------------------------------------------------------------------

def test_ak6_bl_overrides_vault(tmp_path: Path) -> None:
    """AK-6: BL-Override (on) > Vault (off) > Framework (off). BL gewinnt."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-227-test"
    bl_folder.mkdir(parents=True)

    _write_params_file(
        vault_root / "_session_defaults.md",
        "**step_adherence_reminder:** off _owner: user\n",
    )
    _write_params_file(
        bl_folder / "_session_params.md",
        "**step_adherence_reminder:** on _owner: user\n",
    )

    result = resolve_param("step_adherence_reminder", bl_id="BL-227", vault_root=str(vault_root))
    assert result == "on", f"BL-Override 'on' muss Vault 'off' schlagen, got {result!r} (AK-6)."


def test_ak6_vault_overrides_framework(tmp_path: Path) -> None:
    """AK-6: Vault (on) > Framework (off). Vault gewinnt; kein Skip."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    _write_params_file(
        vault_root / "_session_defaults.md",
        "**step_adherence_reminder:** on _owner: user\n",
    )

    result = resolve_param("step_adherence_reminder", bl_id=None, vault_root=str(vault_root))
    assert result == "on", f"Vault 'on' muss Framework 'off' schlagen, got {result!r} (AK-6)."


def test_ak6_bl_off_overrides_vault_on(tmp_path: Path) -> None:
    """AK-6: BL setzt 'off', Vault setzt 'on' -> BL gewinnt (off)."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-227-off"
    bl_folder.mkdir(parents=True)

    _write_params_file(
        vault_root / "_session_defaults.md",
        "**step_adherence_reminder:** on _owner: user\n",
    )
    _write_params_file(
        bl_folder / "_session_params.md",
        "**step_adherence_reminder:** off _owner: user\n",
    )

    result = resolve_param("step_adherence_reminder", bl_id="BL-227", vault_root=str(vault_root))
    assert result == "off", f"BL 'off' muss Vault 'on' schlagen, got {result!r} (AK-6)."


def test_ak6_no_bl_falls_through_vault_to_framework(tmp_path: Path) -> None:
    """AK-6: bl_id=None -> BL-Schicht uebersprungen, Vault/Framework greifen (kein Skip)."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    # No vault file either -> Framework-Default
    result = resolve_param("step_adherence_reminder", bl_id=None, vault_root=str(vault_root))
    assert result == "off", f"Ohne BL/Vault -> Framework 'off', got {result!r} (AK-6)."


# ---------------------------------------------------------------------------
# AK-5 (Validation) — validate_param akzeptiert on/off, lehnt Sonstige ab
# ---------------------------------------------------------------------------

def test_validation_on_accepted() -> None:
    """validate_param akzeptiert 'on' fuer step_adherence_reminder."""
    assert validate_param("step_adherence_reminder", "on") == "on"


def test_validation_off_accepted() -> None:
    """validate_param akzeptiert 'off' fuer step_adherence_reminder."""
    assert validate_param("step_adherence_reminder", "off") == "off"


def test_validation_invalid_rejected() -> None:
    """validate_param lehnt ungueltige Werte ab (z.B. 'true', 'm3', 'auto')."""
    for invalid_val in ("true", "false", "m3", "auto", "1", "yes"):
        with pytest.raises(ValueError, match="step_adherence_reminder"):
            validate_param("step_adherence_reminder", invalid_val)


# ---------------------------------------------------------------------------
# AK-7 — Writer-Identity-Lock: Guard blockt Skill-Write des Toggles
# ---------------------------------------------------------------------------

GUARD_PROTECTION = SCRIPT_DIR / "guard_session_params_protection.py"
GUARD_WRITER_IDENTITY = SCRIPT_DIR / "guard_param_writer_identity.py"


def _run_protection_guard(tool_name: str, tool_input: dict, env_extra: dict | None = None) -> dict:
    """Ruft guard_session_params_protection.py mit simuliertem Hook-Input auf."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    proc = subprocess.run(
        [sys.executable, str(GUARD_PROTECTION)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    try:
        return json.loads(proc.stdout.strip())
    except Exception:
        return {"continue": True, "_parse_error": proc.stdout}


def _run_writer_identity_guard(file_path: str, new_text: str, active_skill: str | None, tool: str = "Write") -> dict:
    """Ruft guard_param_writer_identity.py auf."""
    env = os.environ.copy()
    env["OMNI_PARAM_ACTIVE_SKILL"] = active_skill if active_skill is not None else ""
    ti: dict = {"file_path": file_path}
    if tool == "Write":
        ti["content"] = new_text
    else:
        ti["new_string"] = new_text
    event = {"tool_name": tool, "tool_input": ti}
    proc = subprocess.run(
        [sys.executable, str(GUARD_WRITER_IDENTITY)],
        input=json.dumps(event),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def test_ak7_worker_blocked_from_writing_toggle() -> None:
    """AK-7: Worker + _owner=user + step_adherence_reminder -> BLOCK (INV-OWNER-1)."""
    result = _run_protection_guard(
        tool_name="Skill",
        tool_input={
            "skill_name": "_param",
            "args": "step_adherence_reminder=on",
            "_owner": "user",
        },
        env_extra={"OMNI_AGENT_NAME": "general-sonnet-worker", "OMNI_ENFORCE_PARAM_GUARD": "1"},
    )
    assert result["continue"] is False, (
        f"Worker darf step_adherence_reminder (_owner=user) nicht schreiben, got: {result}"
    )
    assert "PARAM_MUTATION_BLOCKED" in result.get("message", ""), (
        f"Erwarte PARAM_MUTATION_BLOCKED in message, got: {result.get('message', '')}"
    )


def test_ak7_param_skill_allowed_to_write_toggle() -> None:
    """AK-7: /_param (nicht Worker) darf step_adherence_reminder schreiben (ALLOW)."""
    result = _run_protection_guard(
        tool_name="Skill",
        tool_input={
            "skill_name": "_param",
            "args": "step_adherence_reminder=on",
            "_owner": "user",
        },
        # Kein Worker-Agent-Name -> Non-Worker-Kontext -> ALLOW
        env_extra={"OMNI_AGENT_NAME": ""},
    )
    assert result["continue"] is True, (
        f"/_param (non-worker) muss step_adherence_reminder schreiben duerfen, got: {result}"
    )


def test_ak7_sdf_skill_blocked_from_writing_toggle_to_session_params() -> None:
    """AK-7: SDF-Skill + Write auf _session_params.md mit step_adherence_reminder -> BLOCK."""
    result = _run_writer_identity_guard(
        file_path="/vault/_session_params.md",
        new_text="**step_adherence_reminder:** on\n",
        active_skill="_SDF_orchestrate",
    )
    assert result.get("continue") is False, (
        f"SDF darf step_adherence_reminder in _session_params.md nicht schreiben, got: {result}"
    )


def test_ak7_param_skill_allowed_via_session_params_write() -> None:
    """AK-7: /_param (active_skill) + Write auf _session_params.md -> ALLOW."""
    result = _run_writer_identity_guard(
        file_path="/vault/_session_params.md",
        new_text="**step_adherence_reminder:** on\n",
        active_skill="_param",
    )
    assert result.get("continue") is True, (
        f"/_param muss step_adherence_reminder in _session_params.md schreiben duerfen, got: {result}"
    )


def test_ak7_human_direct_allowed() -> None:
    """AK-7: Human-Direct (kein active_skill) -> ALLOW (kein False-Positive)."""
    result = _run_writer_identity_guard(
        file_path="/vault/_session_params.md",
        new_text="**step_adherence_reminder:** on\n",
        active_skill=None,
    )
    assert result.get("continue") is True, (
        f"Human-Direct muss step_adherence_reminder schreiben duerfen, got: {result}"
    )
