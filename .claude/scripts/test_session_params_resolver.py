#!/usr/bin/env python3
"""
test_session_params_resolver.py — BL-174 AK-7: Pytest tests fuer session_params_resolver.py.

10 Tests:
  1.  test_framework_default
  2.  test_vault_override
  3.  test_bl_override
  4.  test_bl_takes_precedence_over_vault
  5.  test_vault_takes_precedence_over_framework
  6.  test_unknown_param_returns_none
  7.  test_bl_id_none_falls_through_vault
  8.  test_schema_validation
  9.  test_concurrent_reads
  10. test_resolve_all_params
"""
from __future__ import annotations

import concurrent.futures
import threading
import textwrap
from pathlib import Path
from typing import Optional

import pytest

from session_params_resolver import (
    FRAMEWORK_DEFAULTS,
    resolve_param,
    resolve_all_params,
    validate_param,
    _parse_session_params_file,
    _coerce_value,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_params_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


# ---------------------------------------------------------------------------
# Test 1: Framework Default — no overrides present
# ---------------------------------------------------------------------------

def test_framework_default(tmp_path: Path) -> None:
    """resolve_param returns Framework value when no Vault or BL file exists."""
    # Empty vault root — no _session_defaults.md, no BL folder
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    assert resolve_param("hil", bl_id=None, vault_root=str(vault_root)) == "off"
    assert resolve_param("difficulty", bl_id=None, vault_root=str(vault_root)) == "normal"
    assert resolve_param("ceiling", bl_id=None, vault_root=str(vault_root)) == "opus"
    assert resolve_param("floor", bl_id=None, vault_root=str(vault_root)) == "sonnet"
    assert resolve_param("tdd", bl_id=None, vault_root=str(vault_root)) is False
    # BL-373: motor_production_ready default False (Gate-D-Lock; vor Gate-D IMMER off)
    assert resolve_param("motor_production_ready", bl_id=None, vault_root=str(vault_root)) is False


# ---------------------------------------------------------------------------
# Test BL-373: motor_production_ready Flag (Gate-D Motor-Produktions-Lock)
# ---------------------------------------------------------------------------

def test_motor_production_ready_flag() -> None:
    """BL-373: motor_production_ready ist registriert, default False, bool-coerced + validiert."""
    assert FRAMEWORK_DEFAULTS["motor_production_ready"]["value"] is False
    assert validate_param("motor_production_ready", "true") is True
    assert validate_param("motor_production_ready", "false") is False
    assert _coerce_value("motor_production_ready", "true") is True
    assert _coerce_value("motor_production_ready", "false") is False


# ---------------------------------------------------------------------------
# Test 2: Vault Override — Vault-Default overrides Framework
# ---------------------------------------------------------------------------

def test_vault_override(tmp_path: Path) -> None:
    """Vault _session_defaults.md value overrides Framework default."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    _write_params_file(
        vault_root / "_session_defaults.md",
        """\
        **hil:** cycle _owner: user
        **difficulty:** hard _owner: user
        """,
    )

    assert resolve_param("hil", bl_id=None, vault_root=str(vault_root)) == "cycle"
    assert resolve_param("difficulty", bl_id=None, vault_root=str(vault_root)) == "hard"
    # Params not in Vault file fall back to Framework
    assert resolve_param("ceiling", bl_id=None, vault_root=str(vault_root)) == "opus"


# ---------------------------------------------------------------------------
# Test 3: BL Override — BL _session_params.md overrides everything
# ---------------------------------------------------------------------------

def test_bl_override(tmp_path: Path) -> None:
    """BL _session_params.md overrides both Vault and Framework."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-999-test-story"
    bl_folder.mkdir(parents=True)

    _write_params_file(
        vault_root / "_session_defaults.md",
        "**hil:** cycle _owner: user\n",
    )
    _write_params_file(
        bl_folder / "_session_params.md",
        "**hil:** phase _owner: user\n",
    )

    assert resolve_param("hil", bl_id="BL-999", vault_root=str(vault_root)) == "phase"


# ---------------------------------------------------------------------------
# Test 3b: BL-234 AK-3 — Resolver findet BL-Folder im konfigurierten Subfolder
#          (z.B. DCSRE/Backlog), nicht nur im hardcoded vault_root/Backlog
# ---------------------------------------------------------------------------

def test_find_bl_folder_respects_subfolder(tmp_path: Path) -> None:
    """BL-234 AK-3: _find_bl_folder respektiert backlog.subfolder (DCSRE/Backlog).

    Hardcoded 'Backlog' wuerde den DCSRE-BL-Folder NICHT finden; mit korrektem
    Subfolder wird er gefunden. OmniCommand-Layout (Subfolder='Backlog') bleibt
    via Fallback unveraendert (486-safe)."""
    from session_params_resolver import _find_bl_folder

    vault_root = tmp_path / "DCS"
    # DCSRE-Layout: vault_root/DCSRE/Backlog/BL-1944-...
    bl_folder = vault_root / "DCSRE" / "Backlog" / "BL-1944-qdvs-test"
    bl_folder.mkdir(parents=True)

    # Hardcoded "Backlog" (vault_root/Backlog existiert nicht) -> nicht gefunden
    assert _find_bl_folder("BL-1944", vault_root, backlog_subfolder="Backlog") is None
    # Konfigurierter Subfolder -> gefunden
    found = _find_bl_folder("BL-1944", vault_root, backlog_subfolder="DCSRE/Backlog")
    assert found == bl_folder, f"Expected {bl_folder}, got {found}"

    # BL-234 AK-2: voller Feature-Name statt bl_id wird via Ticket-Extraktion aufgeloest
    by_name = _find_bl_folder(
        "BL-1944_QDVS_TP_SA_Anlegen_Analyse", vault_root, backlog_subfolder="DCSRE/Backlog"
    )
    assert by_name == bl_folder, f"Name-Variante: expected {bl_folder}, got {by_name}"

    # Backward-Compat: OmniCommand-Layout mit Subfolder="Backlog" findet weiterhin
    om_vault = tmp_path / "OmniCommand"
    om_bl = om_vault / "Backlog" / "BL-234-test"
    om_bl.mkdir(parents=True)
    assert _find_bl_folder("BL-234", om_vault, backlog_subfolder="Backlog") == om_bl


# ---------------------------------------------------------------------------
# Test 3c: BL-234 AK-5 — zwei BLs resolven Params UNABHAENGIG (Parallel-Sicherheit)
# ---------------------------------------------------------------------------

def test_bl234_parallel_two_bls_independent(tmp_path: Path) -> None:
    """BL-234 AK-5: zwei BLs mit unterschiedlichen per-BL-Params resolven unabhaengig
    (Parallel-Worktree-Sicherheit: BL-1944 hil=cycle vs BL-2486 hil=phase, beide
    gegen denselben Umbrella). BL ohne per-BL-File erbt den Umbrella."""
    vault_root = tmp_path / "vault"
    bl_a = vault_root / "Backlog" / "BL-1944-a"
    bl_b = vault_root / "Backlog" / "BL-2486-b"
    bl_a.mkdir(parents=True)
    bl_b.mkdir(parents=True)
    _write_params_file(vault_root / "_session_defaults.md", "**hil:** off\n")
    _write_params_file(bl_a / "_session_params.md", "**hil:** cycle\n")
    _write_params_file(bl_b / "_session_params.md", "**hil:** phase\n")

    assert resolve_param("hil", bl_id="BL-1944", vault_root=str(vault_root)) == "cycle"
    assert resolve_param("hil", bl_id="BL-2486", vault_root=str(vault_root)) == "phase"
    # BL ohne per-BL-File -> Umbrella
    assert resolve_param("hil", bl_id="BL-9999", vault_root=str(vault_root)) == "off"


# ---------------------------------------------------------------------------
# Test 3d: BL-224 Strang B — allowed_stages-Param (IDF-Plan-Whitelist)
# ---------------------------------------------------------------------------

def test_bl224_allowed_stages_param(tmp_path: Path) -> None:
    """BL-224 Strang B: allowed_stages — Default [] (kein Filter, 486-safe), per-BL Override,
    Int-1-7-Listen-Validierung (analog tdd_stages, eigener Param-Seam)."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-224-x"
    bl_folder.mkdir(parents=True)

    # Default: leere Liste = kein Filter
    assert resolve_param("allowed_stages", bl_id=None, vault_root=str(vault_root)) == []

    # Per-BL Override (coerced via _parse_session_params_file)
    _write_params_file(bl_folder / "_session_params.md", "**allowed_stages:** [1,3]\n")
    assert resolve_param("allowed_stages", bl_id="BL-224", vault_root=str(vault_root)) == [1, 3]

    # Validierung: Int 1-7
    assert validate_param("allowed_stages", "[1,3,6]") == [1, 3, 6]
    with pytest.raises(ValueError):
        validate_param("allowed_stages", "[1,9]")  # 9 ausserhalb 1-7


# ---------------------------------------------------------------------------
# Test 4: BL takes precedence over Vault (INV-PARAM-RESOLVE-2)
# ---------------------------------------------------------------------------

def test_bl_takes_precedence_over_vault(tmp_path: Path) -> None:
    """BL-Override > Vault-Default (INV-PARAM-RESOLVE-2)."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-100-precedence"
    bl_folder.mkdir(parents=True)

    _write_params_file(
        vault_root / "_session_defaults.md",
        "**difficulty:** easy _owner: user\n",
    )
    _write_params_file(
        bl_folder / "_session_params.md",
        "**difficulty:** hard _owner: user\n",
    )

    result = resolve_param("difficulty", bl_id="BL-100", vault_root=str(vault_root))
    assert result == "hard", f"Expected 'hard' (BL wins), got {result!r}"


# ---------------------------------------------------------------------------
# Test 5: Vault takes precedence over Framework (INV-PARAM-RESOLVE-2)
# ---------------------------------------------------------------------------

def test_vault_takes_precedence_over_framework(tmp_path: Path) -> None:
    """Vault-Default > Framework-Default (INV-PARAM-RESOLVE-2)."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    _write_params_file(
        vault_root / "_session_defaults.md",
        "**floor:** haiku _owner: user\n",
    )

    result = resolve_param("floor", bl_id=None, vault_root=str(vault_root))
    assert result == "haiku", f"Expected 'haiku' (Vault wins over 'sonnet' Framework), got {result!r}"


# ---------------------------------------------------------------------------
# Test 6: Unknown param returns None
# ---------------------------------------------------------------------------

def test_unknown_param_returns_none(tmp_path: Path) -> None:
    """resolve_param returns None for params not in FRAMEWORK_DEFAULTS."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    result = resolve_param("totally_unknown_param_xyz", bl_id=None, vault_root=str(vault_root))
    assert result is None


# ---------------------------------------------------------------------------
# Test 7: bl_id=None falls through to Vault then Framework
# ---------------------------------------------------------------------------

def test_bl_id_none_falls_through_vault(tmp_path: Path) -> None:
    """When bl_id is None, BL layer is skipped and Vault/Framework used."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    _write_params_file(
        vault_root / "_session_defaults.md",
        "**tdd:** true _owner: user\n",
    )

    # bl_id=None — no BL layer
    result = resolve_param("tdd", bl_id=None, vault_root=str(vault_root))
    assert result is True

    # Also verify Framework default when Vault has nothing for 'ceiling'
    ceiling = resolve_param("ceiling", bl_id=None, vault_root=str(vault_root))
    assert ceiling == "opus"  # Framework default


# ---------------------------------------------------------------------------
# Test 8: Schema Validation — invalid value raises ValueError
# ---------------------------------------------------------------------------

def test_schema_validation() -> None:
    """validate_param raises ValueError for invalid values."""
    with pytest.raises(ValueError, match="hil"):
        validate_param("hil", "invalid_hil_value")

    with pytest.raises(ValueError, match="difficulty"):
        validate_param("difficulty", "ultra")

    with pytest.raises(ValueError, match="ceiling"):
        validate_param("ceiling", "gpt4")

    # Valid values should not raise
    assert validate_param("hil", "phase") == "phase"
    assert validate_param("difficulty", "hard") == "hard"
    assert validate_param("tdd", "true") is True
    assert validate_param("tdd_stages", "[1,3]") == [1, 3]


# ---------------------------------------------------------------------------
# Test 9: Concurrent reads are Lock-safe
# ---------------------------------------------------------------------------

def test_concurrent_reads(tmp_path: Path) -> None:
    """Multiple threads calling resolve_param simultaneously should not crash."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    _write_params_file(
        vault_root / "_session_defaults.md",
        "**hil:** cycle _owner: user\n**difficulty:** hard _owner: user\n",
    )

    results: list[str] = []
    errors: list[Exception] = []
    lock = threading.Lock()

    def worker(i: int) -> None:
        try:
            val = resolve_param("hil", bl_id=None, vault_root=str(vault_root))
            with lock:
                results.append(str(val))
        except Exception as e:
            with lock:
                errors.append(e)

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futs = [pool.submit(worker, i) for i in range(20)]
        concurrent.futures.wait(futs)

    assert not errors, f"Concurrent read errors: {errors}"
    assert len(results) == 20
    assert all(r == "cycle" for r in results), f"Inconsistent results: {set(results)}"


# ---------------------------------------------------------------------------
# Test 10: resolve_all_params returns complete dict
# ---------------------------------------------------------------------------

def test_resolve_all_params(tmp_path: Path) -> None:
    """resolve_all_params returns all FRAMEWORK_DEFAULTS keys with correct merged values."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-200-batch"
    bl_folder.mkdir(parents=True)

    _write_params_file(
        vault_root / "_session_defaults.md",
        "**ceiling:** sonnet _owner: user\n",
    )
    _write_params_file(
        bl_folder / "_session_params.md",
        "**hil:** manual _owner: user\n",
    )

    all_p = resolve_all_params(bl_id="BL-200", vault_root=str(vault_root))

    # All Framework keys must be present
    for key in FRAMEWORK_DEFAULTS:
        assert key in all_p, f"Missing param in resolve_all result: {key}"

    # BL override
    assert all_p["hil"] == "manual"
    # Vault override
    assert all_p["ceiling"] == "sonnet"
    # Framework fallback
    assert all_p["floor"] == "sonnet"
    assert all_p["difficulty"] == "normal"
    assert all_p["tdd"] is False


# ---------------------------------------------------------------------------
# BL-227 / C-2 / Stage 1 — Ring 0 (Kern), T1 Canary (AK-5):
#   step_adherence_reminder Framework-Default == "off"
# RED-Beweis: 'step_adherence_reminder' ist (noch) NICHT in FRAMEWORK_DEFAULTS,
#   daher liefert resolve_param() aktuell None statt "off" -> Test ist ROT, bis
#   der Toggle-Eintrag {"value":"off","_owner":"user"} ergaenzt ist (GREEN-Schritt).
# ---------------------------------------------------------------------------

def test_step_adherence_reminder_framework_default_off(tmp_path: Path) -> None:
    """AK-5 Canary: ohne Override liefert resolve_param("step_adherence_reminder") den
    Framework-Default "off" (additive Schicht standardmaessig still).

    Living-Doc-Vertrag (AK-5): Der Reminder-Berater-Toggle ist standardmaessig AUS,
    d.h. eine Session ohne expliziten /_param-Eintrag laeuft das Framework byte-identisch
    zum Vor-BL-227-Zustand (additive Schicht still). Pin: exakt der String "off" (kein
    truthy/None-Surrogat), aufgeloest aus der Framework-Stufe der 3-stufigen Kaskade.
    """
    # Arrange: leerer Vault-Root — kein _session_defaults.md, kein BL-Override
    #          -> Resolver muss bis zur Framework-Stufe durchfallen (PT-CMD-006).
    EXPECTED_FRAMEWORK_DEFAULT = "off"
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    # Act: Resolution OHNE jeden Override (bl_id=None, leerer Vault).
    result = resolve_param("step_adherence_reminder", bl_id=None, vault_root=str(vault_root))

    # Assert: exakt "off" — nicht None (Key fehlt in FRAMEWORK_DEFAULTS) und nicht
    #         irgendein anderer Toggle-Wert. Praeziser String-Match als Living-Doc.
    assert result == EXPECTED_FRAMEWORK_DEFAULT, (
        "AK-5 verletzt: step_adherence_reminder muss ohne Override den Framework-Default "
        f"{EXPECTED_FRAMEWORK_DEFAULT!r} liefern (additive Schicht still), erhalten: {result!r}. "
        "result is None => Key fehlt in FRAMEWORK_DEFAULTS; result='on' => falscher Default."
    )


# ---------------------------------------------------------------------------
# Bonus: _parse_session_params_file handles table format
# ---------------------------------------------------------------------------

def test_parse_table_format(tmp_path: Path) -> None:
    """_parse_session_params_file handles Markdown table format."""
    f = tmp_path / "_session_params.md"
    _write_params_file(
        f,
        """\
        | Parameter | Wert | Owner |
        |-----------|------|-------|
        | hil | phase | user |
        | difficulty | hard | user |
        """,
    )
    result = _parse_session_params_file(f)
    assert result.get("hil") == "phase"
    assert result.get("difficulty") == "hard"


# ===========================================================================
# BL-327 — Parallel-Parameter-Dial (OFF -> SINGLE -> WAVE)
#   AK-1 (Params + Coercion + Kaskade) + AK-3 (Validierungs-Guard im Resolver)
# RED-Beweis: parallel_mode/nr_parallel_batches sind (noch) NICHT in
#   FRAMEWORK_DEFAULTS, die Coercion kennt sie nicht, der N<1-Check, die
#   false=>N=1-Kombi-Regel und der Bypass-Guard existieren noch nicht ->
#   diese Tests sind ROT bis der GREEN-Schritt session_params_resolver.py
#   erweitert. 15 Baseline-Tests + die AK-1-Tests bleiben dabei gruen.
# ===========================================================================

# --- AK-1 (a): parallel_mode Framework-Default == False ---

def test_parallel_mode_framework_default_false(tmp_path: Path) -> None:
    """AK-1: ohne Override liefert resolve_param("parallel_mode") den
    Framework-Default False (Master-Schalter standardmaessig OFF =
    byte-identischer serieller Pfad, Null-Risiko-Fallback)."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    result = resolve_param("parallel_mode", bl_id=None, vault_root=str(vault_root))
    assert result is False, (
        "AK-1 verletzt: parallel_mode muss ohne Override den Framework-Default "
        f"False liefern (OFF = serieller Pfad), erhalten: {result!r}. "
        "result is None => Key fehlt in FRAMEWORK_DEFAULTS."
    )


# --- AK-1 (b): nr_parallel_batches Framework-Default == 1 ---

def test_nr_parallel_batches_framework_default_one(tmp_path: Path) -> None:
    """AK-1: ohne Override liefert resolve_param("nr_parallel_batches") den
    Framework-Default 1 (SINGLE-Breite = keine Concurrency)."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    result = resolve_param("nr_parallel_batches", bl_id=None, vault_root=str(vault_root))
    assert result == 1, (
        "AK-1 verletzt: nr_parallel_batches muss ohne Override den Framework-"
        f"Default 1 liefern, erhalten: {result!r}."
    )


# --- AK-1 (c): Coercion bool / int ---

def test_parallel_dial_coercion(tmp_path: Path) -> None:
    """AK-1: parallel_mode -> bool (analog tdd), nr_parallel_batches -> int
    (analog tdd_stages/pattern_scan_threshold). String-Quellwerte aus der
    _session_params.md-Datei werden in native Typen ueberfuehrt."""
    assert _coerce_value("parallel_mode", "true") is True
    assert _coerce_value("parallel_mode", "false") is False
    assert _coerce_value("parallel_mode", True) is True
    assert _coerce_value("nr_parallel_batches", "3") == 3
    assert _coerce_value("nr_parallel_batches", "1") == 1
    assert _coerce_value("nr_parallel_batches", 2) == 2
    # native int bleibt int (kein Crash)
    assert isinstance(_coerce_value("nr_parallel_batches", "4"), int)


# --- AK-1 (d): Kaskade BL > Vault > Framework fuer beide Params ---

def test_parallel_dial_cascade_bl_over_vault_over_framework(tmp_path: Path) -> None:
    """AK-1: 3-Stufen-Inheritance gilt fuer beide Dial-Params.
    BL-Override > Vault-Default > Framework-Default."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-327-dial"
    bl_folder.mkdir(parents=True)

    # Vault setzt parallel_mode=true + nr_parallel_batches=2 ...
    _write_params_file(
        vault_root / "_session_defaults.md",
        "**parallel_mode:** true\n**nr_parallel_batches:** 2\n",
    )
    # ... BL ueberschreibt nr_parallel_batches=5 (parallel_mode erbt Vault=true)
    _write_params_file(
        bl_folder / "_session_params.md",
        "**nr_parallel_batches:** 5\n",
    )

    # parallel_mode=true (Vault gewinnt ueber Framework False)
    assert resolve_param("parallel_mode", bl_id="BL-327", vault_root=str(vault_root)) is True
    # nr_parallel_batches=5 (BL gewinnt ueber Vault=2 und Framework=1)
    # parallel_mode=true => N bleibt wie gesetzt (keine OFF-Erzwingung)
    assert resolve_param("nr_parallel_batches", bl_id="BL-327", vault_root=str(vault_root)) == 5

    # Vault-Stufe ohne BL-Override fuer nr_parallel_batches (anderer BL, kein File)
    assert resolve_param("nr_parallel_batches", bl_id="BL-999", vault_root=str(vault_root)) == 2


# --- AK-3 (1): nr_parallel_batches < 1 ist invalid (ValueError) ---

def test_nr_parallel_batches_below_one_invalid() -> None:
    """AK-3.1: validate_param("nr_parallel_batches", N) raised ValueError fuer
    N<1 (analog tdd_stages-Integer-Wertebereichs-Check); N>=1 passt."""
    with pytest.raises(ValueError):
        validate_param("nr_parallel_batches", 0)
    with pytest.raises(ValueError):
        validate_param("nr_parallel_batches", -1)
    with pytest.raises(ValueError):
        validate_param("nr_parallel_batches", "0")
    # N>=1 akzeptiert, als int zurueck
    assert validate_param("nr_parallel_batches", 1) == 1
    assert validate_param("nr_parallel_batches", "2") == 2


# --- AK-3 (2): parallel_mode=false => N erzwungen 1 (false dominiert) ---

def test_off_forces_n_one(tmp_path: Path) -> None:
    """AK-3.2: Kombinations-Regel — bei parallel_mode=false liefert die
    Resolution nr_parallel_batches=1 ERZWUNGEN, auch wenn eine Quelle N=4 setzt.
    OFF hat per Definition fanout 1 (kein Wellen-Effekt). Clamp, KEIN Error."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-327-off"
    bl_folder.mkdir(parents=True)

    # Quelle sagt N=4, aber parallel_mode=false
    _write_params_file(
        bl_folder / "_session_params.md",
        "**parallel_mode:** false\n**nr_parallel_batches:** 4\n",
    )

    result = resolve_param("nr_parallel_batches", bl_id="BL-327", vault_root=str(vault_root))
    assert result == 1, (
        "AK-3.2 verletzt: parallel_mode=false MUSS nr_parallel_batches auf 1 "
        f"erzwingen (false dominiert), erhalten: {result!r} (Quelle sagte 4)."
    )

    # Gegenprobe via resolve_all_params: gleicher Clamp im Bulk-Pfad
    all_p = resolve_all_params(bl_id="BL-327", vault_root=str(vault_root))
    assert all_p["parallel_mode"] is False
    assert all_p["nr_parallel_batches"] == 1, (
        "AK-3.2 (resolve_all): false=>N=1-Clamp muss auch im Bulk-Pfad greifen, "
        f"erhalten: {all_p['nr_parallel_batches']!r}."
    )


# --- AK-3 (2-Gegenstueck): parallel_mode=true => N bleibt wie gesetzt ---

def test_on_keeps_n(tmp_path: Path) -> None:
    """AK-3: bei parallel_mode=true bleibt nr_parallel_batches wie gesetzt
    (keine OFF-Erzwingung). Gegenstueck zu test_off_forces_n_one."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-327-on"
    bl_folder.mkdir(parents=True)

    _write_params_file(
        bl_folder / "_session_params.md",
        "**parallel_mode:** true\n**nr_parallel_batches:** 4\n",
    )

    result = resolve_param("nr_parallel_batches", bl_id="BL-327", vault_root=str(vault_root))
    assert result == 4, (
        "AK-3 verletzt: parallel_mode=true MUSS nr_parallel_batches unveraendert "
        f"lassen, erhalten: {result!r} (erwartet 4)."
    )


# --- AK-3 (4): parallel_mode nicht-bool-like Wert => ValueError ---

def test_parallel_mode_invalid_value() -> None:
    """AK-3.4: parallel_mode-Wertebereich ist bool-like (true/false). Andere
    Werte raisen ValueError (analog _VALID_VALUES fuer tdd/slicing)."""
    with pytest.raises(ValueError, match="parallel_mode"):
        validate_param("parallel_mode", "maybe")
    # Valid bool-likes passen
    assert validate_param("parallel_mode", "true") is True
    assert validate_param("parallel_mode", "false") is False


# --- AK-3 (3): Bypass-Feld => ValueError (kein zweiter Schreibweg am Dial vorbei) ---

def test_dial_bypass_field_blocked() -> None:
    """AK-3.3: verbotene Bypass-Felder (analog INV-MODUS-5) sind kein zweiter
    Schreibweg am Dial vorbei. validate_no_parallel_bypass raised ValueError,
    wenn eines der Felder in einer Params-Quelle auftaucht."""
    from session_params_resolver import validate_no_parallel_bypass, _PARALLEL_BYPASS_FIELDS

    # Sanity: das kanonische Set ist definiert
    assert "force_parallel" in _PARALLEL_BYPASS_FIELDS
    assert "wave_override" in _PARALLEL_BYPASS_FIELDS

    # Ein Bypass-Feld in der Key-Menge -> ValueError
    with pytest.raises(ValueError, match="force_parallel"):
        validate_no_parallel_bypass({"parallel_mode", "force_parallel"})
    with pytest.raises(ValueError):
        validate_no_parallel_bypass(["wave_override"])

    # Saubere Key-Menge (nur legitime Dial-Felder) -> kein Error
    assert validate_no_parallel_bypass({"parallel_mode", "nr_parallel_batches"}) is None


# --- AK-3 (3-Integration): Bypass-Feld in einer Datei-Quelle => ValueError beim Resolve ---

def test_dial_bypass_field_in_file_blocks_resolve(tmp_path: Path) -> None:
    """AK-3.3 Integration: taucht ein Bypass-Feld in einer Params-Quelle (Datei)
    auf, blockt der Resolver (ValueError) — der Dial bleibt die EINZIGE
    Stellschraube (analog INV-MODUS-5-Pre-Write-Block-Doktrin)."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-327-bypass"
    bl_folder.mkdir(parents=True)

    # Eine Quelle versucht, am Dial vorbei force_parallel zu setzen
    _write_params_file(
        bl_folder / "_session_params.md",
        "**parallel_mode:** false\n**force_parallel:** true\n",
    )

    with pytest.raises(ValueError, match="force_parallel"):
        resolve_param("nr_parallel_batches", bl_id="BL-327", vault_root=str(vault_root))


# ===========================================================================
# BL-330 — 3-Modi Workflow-Dial (User-Design 2026-06-12, ersetzt tier+burnin)
#   workflow ∈ {false, normal, fast}  (default "false")
#     false  = alles altmodisch (Teams)            — heutiges Verhalten byte-identisch
#     normal = gruene (hart-det) Zone als Workflow ; gelb+rot altmodisch
#     fast   = gruen + gelb als Workflow           ; rot IMMER altmodisch
#   KEIN cognitive/all-Modus (rot strukturell nie schaltbar — Resolver-Invariante).
#   Aliase: true/on -> normal ; off -> false (benutzerfreundlich).
#   Bypass-Guard (analog INV-MODUS-5/BL-327): force_workflow/ultracode_force/
#     workflow_override/motor_zone_force => ValueError (Ultracode-Auto-Reflex geblockt).
# RED-Beweis: 'workflow' ist (noch) NICHT in FRAMEWORK_DEFAULTS, die Alias-Coercion +
#   Enum-Validierung + der workflow-Bypass-Guard existieren noch nicht -> ROT bis GREEN.
# ===========================================================================

# --- (a) Framework-Default == "false" (alles altmodisch) ---

def test_workflow_framework_default_false(tmp_path: Path) -> None:
    """Ohne Override liefert resolve_param("workflow") den Framework-Default "false"
    (alles altmodisch = heutiges Verhalten byte-identisch)."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()

    result = resolve_param("workflow", bl_id=None, vault_root=str(vault_root))
    assert result == "false", (
        "workflow muss ohne Override den Framework-Default 'false' liefern (alles "
        f"altmodisch), erhalten: {result!r}. result is None => Key fehlt in FRAMEWORK_DEFAULTS."
    )


# --- (b) Coercion + benutzerfreundliche Aliase ---

def test_workflow_coercion_and_aliases() -> None:
    """workflow ist ein 3-Wert-String-Enum. Kanonische Werte bleiben; freundliche
    Aliase werden gemappt: true/on -> normal, off -> false. Bool True (z.B. aus
    /_param workflow=true) -> normal."""
    # Kanonisch
    assert _coerce_value("workflow", "false") == "false"
    assert _coerce_value("workflow", "normal") == "normal"
    assert _coerce_value("workflow", "fast") == "fast"
    # Aliase
    assert _coerce_value("workflow", "true") == "normal"
    assert _coerce_value("workflow", "on") == "normal"
    assert _coerce_value("workflow", "off") == "false"
    assert _coerce_value("workflow", True) == "normal"
    assert _coerce_value("workflow", False) == "false"
    # Case-insensitiv
    assert _coerce_value("workflow", "NORMAL") == "normal"


# --- (c) Wertebereich — invalide Werte (inkl. cognitive/all) raisen ---

def test_workflow_rejects_invalid() -> None:
    """KEIN cognitive/all-Modus: das Enum kennt nur {false,normal,fast}. 'cognitive'/
    'all'/'maybe' raisen ValueError (rot ist nie ueber den Dial schaltbar)."""
    for bad in ("cognitive", "all", "maybe", "ultra", "2"):
        with pytest.raises(ValueError, match="workflow"):
            validate_param("workflow", bad)
    # Gueltige Werte (inkl. Aliase via Coercion in validate_param)
    assert validate_param("workflow", "false") == "false"
    assert validate_param("workflow", "normal") == "normal"
    assert validate_param("workflow", "fast") == "fast"
    assert validate_param("workflow", "true") == "normal"   # Alias
    assert validate_param("workflow", "off") == "false"     # Alias


# --- (d) Kaskade BL > Vault > Framework ---

def test_workflow_cascade(tmp_path: Path) -> None:
    """3-Stufen-Inheritance gilt fuer den workflow-Param."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-330-w"
    bl_folder.mkdir(parents=True)

    _write_params_file(vault_root / "_session_defaults.md", "**workflow:** normal\n")
    _write_params_file(bl_folder / "_session_params.md", "**workflow:** fast\n")

    # BL gewinnt (fast)
    assert resolve_param("workflow", bl_id="BL-330", vault_root=str(vault_root)) == "fast"
    # anderer BL ohne Override -> Vault-Stufe (normal)
    assert resolve_param("workflow", bl_id="BL-999", vault_root=str(vault_root)) == "normal"
    # Alias aus Datei: true -> normal
    _write_params_file(bl_folder / "_session_params.md", "**workflow:** true\n")
    assert resolve_param("workflow", bl_id="BL-330", vault_root=str(vault_root)) == "normal"


# --- (e) Bypass-Felder => ValueError (Ultracode-Auto-Reflex geblockt) ---

def test_workflow_bypass_field_blocked() -> None:
    """Verbotene Bypass-Felder sind kein zweiter Schreibweg am Dial vorbei
    (analog INV-MODUS-5/BL-327)."""
    from session_params_resolver import (
        validate_no_workflow_zone_bypass,
        _WORKFLOW_ZONE_BYPASS_FIELDS,
    )
    assert "force_workflow" in _WORKFLOW_ZONE_BYPASS_FIELDS
    assert "ultracode_force" in _WORKFLOW_ZONE_BYPASS_FIELDS

    with pytest.raises(ValueError, match="force_workflow"):
        validate_no_workflow_zone_bypass({"workflow", "force_workflow"})
    with pytest.raises(ValueError):
        validate_no_workflow_zone_bypass(["ultracode_force"])
    assert validate_no_workflow_zone_bypass({"workflow"}) is None


# --- (e-Integration): Bypass-Feld in Datei => ValueError beim Resolve ---

def test_workflow_bypass_in_file_blocks_resolve(tmp_path: Path) -> None:
    """Taucht ein Bypass-Feld in einer Params-Quelle auf, blockt der Resolver."""
    vault_root = tmp_path / "vault"
    bl_folder = vault_root / "Backlog" / "BL-330-bp"
    bl_folder.mkdir(parents=True)
    _write_params_file(
        bl_folder / "_session_params.md",
        "**workflow:** false\n**ultracode_force:** true\n",
    )
    with pytest.raises(ValueError, match="ultracode_force"):
        resolve_param("workflow", bl_id="BL-330", vault_root=str(vault_root))


# --- (f) resolve_all enthaelt den workflow-Param ---

def test_resolve_all_includes_workflow(tmp_path: Path) -> None:
    """resolve_all_params enthaelt 'workflow' mit Default 'false'."""
    vault_root = tmp_path / "vault"
    vault_root.mkdir()
    all_p = resolve_all_params(bl_id=None, vault_root=str(vault_root))
    assert "workflow" in all_p
    assert all_p["workflow"] == "false"


# ===========================================================================
# BL-442 batch_5 AK-3 — merge Default-Flip (true) + lane-Param (W14)
#
# RED-Beweis:
#   T-m1: merge Framework-Default ist aktuell False (FRAMEWORK_DEFAULTS Zeile 98)
#          -> resolve_param("merge") ohne Override liefert False, nicht True -> FAIL (ROT).
#   T-m2: Praezedenz BL>Vault>Framework muss auch nach Flip intakt bleiben
#          -> bei merge=false Override muss False gewinnen (NICHT True).
#   T-l1: "lane" fehlt aktuell komplett in FRAMEWORK_DEFAULTS
#          -> resolve_param("lane") liefert None (unbekannt) statt Framework-Default -> FAIL (ROT).
#   T-l2: lane-Override via BL muss resolvierbar sein (kein ValueError)
#          -> wenn "lane" noch nicht in FRAMEWORK_DEFAULTS: None statt "A" -> FAIL (ROT).
#
# GREEN flippt:
#   - FRAMEWORK_DEFAULTS["merge"]["value"] = True  (statt False)
#   - FRAMEWORK_DEFAULTS["lane"] = {"value": None, "_owner": "user"}  (neu)
#   - _VALID_VALUES["lane"] = {None, "A", "B", "C", ""}  (oder ohne Validation -> as-is)
#   - _coerce_value fuer "lane" = as-is (kein bool-Cast noetig)
# ===========================================================================


class TestBL442MergeAndLane:
    """BL-442 AK-3: merge=true Default-Flip (SOA-2=B) + lane-Param W14."""

    # -----------------------------------------------------------------------
    # T-m1: merge Framework-Default == True (nach Default-Flip)
    # -----------------------------------------------------------------------

    def test_m1_merge_framework_default_true(self, tmp_path: "Path") -> None:
        """T-m1 (RED): resolve_param("merge") ohne Override -> True.

        AK-3/SOA-2=B: Default-Flip von False auf True. Aktuell ist
        FRAMEWORK_DEFAULTS["merge"]["value"] == False -> Test failt (ROT).
        GREEN: setzt FRAMEWORK_DEFAULTS["merge"]["value"] = True.
        """
        vault_root = tmp_path / "vault"
        vault_root.mkdir()

        result = resolve_param("merge", bl_id=None, vault_root=str(vault_root))
        assert result is True, (
            "BL-442 AK-3 T-m1 verletzt: merge muss nach Default-Flip den "
            f"Framework-Default True liefern (SOA-2=B), erhalten: {result!r}. "
            "result is False => FRAMEWORK_DEFAULTS['merge']['value'] noch False (GREEN flippt)."
        )

    # -----------------------------------------------------------------------
    # T-m2: Praezedenz BL > Vault > Framework bleibt nach Flip intakt
    # -----------------------------------------------------------------------

    def test_m2_merge_bl_override_false_wins_over_default_true(
        self, tmp_path: "Path"
    ) -> None:
        """T-m2 (RED-vorbeugt): BL-Override merge=false gewinnt ueber Framework-Default True.

        Prueft dass der Default-Flip die Praezedenz-Kaskade (INV-PARAM-RESOLVE-2)
        nicht bricht. Ein explizites merge=false im BL muss False liefern —
        NICHT True vom Framework-Default.

        Dieser Test ist GRUEN solange merge in FRAMEWORK_DEFAULTS existiert UND
        die Kaskade korrekt ist; er failt nur wenn T-m1 wegen fehlendem Key keinen
        Eintrag hat. Als Vorsorge-Test: sichert Kaskaden-Integrität nach Flip.
        """
        vault_root = tmp_path / "vault"
        bl_folder = vault_root / "Backlog" / "BL-442-merge-override"
        bl_folder.mkdir(parents=True)

        # BL-Override setzt merge explizit auf false
        _write_params_file(
            bl_folder / "_session_params.md",
            "**merge:** false\n",
        )

        result = resolve_param(
            "merge", bl_id="BL-442", vault_root=str(vault_root)
        )
        assert result is False, (
            "BL-442 AK-3 T-m2 verletzt: BL-Override merge=false muss False liefern "
            f"(BL > Framework, INV-PARAM-RESOLVE-2), erhalten: {result!r}. "
            "Kaskaden-Integrität verletzt nach Default-Flip."
        )

    # -----------------------------------------------------------------------
    # T-l1: lane-Param bekannt — resolve liefert Framework-Default (nicht None)
    # -----------------------------------------------------------------------

    def test_l1_lane_param_known_returns_default(self, tmp_path: "Path") -> None:
        """T-l1 (RED): resolve_param("lane") ohne Override -> Framework-Default (nicht None).

        W14: _session_params.md erhaelt lane=A|B|C als neuen Parameter.
        Aktuell fehlt "lane" in FRAMEWORK_DEFAULTS -> resolve_param liefert None
        (unbekannter Param, Zeile 536-537) -> Test failt (ROT).
        GREEN: ergaenzt FRAMEWORK_DEFAULTS["lane"] = {"value": None/_UNSET, "_owner": "user"}
        (oder "" oder einen anderen Sentinel fuer 'kein Lane-Override') damit der
        Param bekannt ist und kein ValueError/None-fuer-unbekannt kommt.
        """
        vault_root = tmp_path / "vault"
        vault_root.mkdir()

        result = resolve_param("lane", bl_id=None, vault_root=str(vault_root))

        # Der Resolver darf nicht None fuer "unbekannt" liefern — "lane" muss
        # ein registrierter Param sein. Der exakte Default-Wert (None / "" / "unset")
        # ist dem GREEN-Worker ueberlassen; wir pruefen nur: NICHT None-fuer-unbekannt.
        # Da FRAMEWORK_DEFAULTS["lane"] fehlt gibt _resolve_one() None zurueck
        # (Zeile 537: return None). Nach GREEN muss er den registrierten Default liefern.
        assert result is not None or "lane" in FRAMEWORK_DEFAULTS, (
            "BL-442 AK-3 T-l1 verletzt: 'lane' muss als registrierter Param in "
            "FRAMEWORK_DEFAULTS stehen (W14 Pre-Condition). Aktuell fehlt der Key "
            f"-> resolve_param liefert None (unbekannt), erhalten: {result!r}. "
            "GREEN: ergaenzt FRAMEWORK_DEFAULTS['lane']."
        )
        # Haertere Assertion: wenn GREEN lane in FRAMEWORK_DEFAULTS ergaenzt,
        # muss resolve_param einen Wert zurueckgeben der != None-fuer-unbekannt ist.
        # Wir nutzen FRAMEWORK_DEFAULTS-Prazenz als RED-Trigger:
        assert "lane" in FRAMEWORK_DEFAULTS, (
            "BL-442 AK-3 T-l1 (haerter): 'lane' muss in FRAMEWORK_DEFAULTS registriert sein. "
            "Aktuell nicht vorhanden -> RED. GREEN ergaenzt den Eintrag."
        )

    # -----------------------------------------------------------------------
    # T-l2: lane-Override (BL: lane=A) resolvierbar -> liefert "A"
    # -----------------------------------------------------------------------

    def test_l2_lane_override_resolves(self, tmp_path: "Path") -> None:
        """T-l2 (RED): BL-Override lane=A -> resolve_param("lane") liefert "A".

        Prueft dass ein per-BL lane=A|B|C korrekt durch die 3-Stufen-Kaskade
        aufgeloest wird. Setzt voraus dass "lane" in FRAMEWORK_DEFAULTS bekannt ist
        (T-l1). Wenn "lane" fehlt, scheitert auch T-l2 (kaskadierende Abhaengigkeit).
        """
        vault_root = tmp_path / "vault"
        bl_folder = vault_root / "Backlog" / "BL-442-lane-test"
        bl_folder.mkdir(parents=True)

        _write_params_file(
            bl_folder / "_session_params.md",
            "**lane:** A\n",
        )

        result = resolve_param(
            "lane", bl_id="BL-442", vault_root=str(vault_root)
        )
        assert result == "A", (
            "BL-442 AK-3 T-l2 verletzt: BL-Override lane=A muss 'A' liefern "
            f"(BL > Framework, INV-PARAM-RESOLVE-2), erhalten: {result!r}. "
            "'lane' fehlt in FRAMEWORK_DEFAULTS -> _coerce_value kennt ihn nicht "
            "-> raw-String bleibt unkeoerced aber trotzdem 'A'. "
            "Oder lane fehlt komplett -> None."
        )
