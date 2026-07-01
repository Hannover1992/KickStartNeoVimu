"""
test_resolve_lock_root.py — BL-368 AK-LEDGER-PL-1: Tests fuer resolve_lock_root.py

Testet die NOCH NICHT EXISTIERENDE Funktion resolve_lock_root() (RED-Phase).
Funktion-Spezifikation:
  resolve_lock_root(cwd=None, *, debug=False) -> pathlib.Path

Resolver-Semantik:
  1. Default = VAULT_ROOT (kein Env-Override → selber Root wie resolve_vault_root())
  2. Env-Override OMNI_LOCK_ROOT: hat Vorrang vor allem anderen
  3. cross-worktree-Stabilitaet: zwei cwd-Werte + OMNI_LOCK_ROOT → identischer Lock-Root
  4. Typ-Garantie: immer pathlib.Path; ~ wird expandiert

Run: py -3 -m pytest .claude/scripts/test_resolve_lock_root.py -q
"""

import os
import sys
from pathlib import Path

import pytest

# Projekt-ueblicher Import-Stil (siehe test_factory_lock.py)
sys.path.insert(0, str(Path(__file__).parent))

from resolve_lock_root import resolve_lock_root  # noqa: E402  (Modul existiert noch nicht)


# ─── Test 1: Default ohne Env-Override = VAULT_ROOT ───────────────────────────

def test_default_equals_vault_root(monkeypatch):
    """Ohne OMNI_LOCK_ROOT liefert resolve_lock_root() denselben Root wie resolve_vault_root()."""
    # Sicherstellen dass OMNI_LOCK_ROOT nicht gesetzt ist
    monkeypatch.delenv("OMNI_LOCK_ROOT", raising=False)

    from resolve_vault_root import resolve_vault_root
    expected = resolve_vault_root()

    result = resolve_lock_root()

    assert result == expected, (
        f"Default Lock-Root {result!r} weicht vom Vault-Root {expected!r} ab"
    )


# ─── Test 2: Env-Override OMNI_LOCK_ROOT hat Vorrang ─────────────────────────

def test_env_override_takes_precedence(monkeypatch, tmp_path):
    """Wenn OMNI_LOCK_ROOT gesetzt ist, liefert resolve_lock_root() genau diesen Pfad."""
    lock_dir = tmp_path / "custom_locks"
    monkeypatch.setenv("OMNI_LOCK_ROOT", str(lock_dir))

    result = resolve_lock_root()

    assert result == lock_dir, (
        f"OMNI_LOCK_ROOT={lock_dir!r} wurde ignoriert, stattdessen {result!r}"
    )


# ─── Test 3: cross-worktree-Stabilitaet ──────────────────────────────────────

def test_cross_worktree_stability(monkeypatch, tmp_path):
    """Zwei verschiedene cwd-Werte liefern bei gesetztem OMNI_LOCK_ROOT denselben Lock-Root."""
    lock_dir = tmp_path / "shared_locks"
    monkeypatch.setenv("OMNI_LOCK_ROOT", str(lock_dir))

    worktree_a = tmp_path / "worktree_a"
    worktree_b = tmp_path / "worktree_b"

    result_a = resolve_lock_root(cwd=worktree_a)
    result_b = resolve_lock_root(cwd=worktree_b)

    assert result_a == result_b, (
        f"Lock-Root divergiert zwischen Worktrees: {result_a!r} != {result_b!r}"
    )


# ─── Test 4: Typ-Garantie + Tilde-Expansion ───────────────────────────────────

def test_return_type_is_path_and_tilde_expanded(monkeypatch):
    """Rueckgabe ist immer pathlib.Path; ~ in OMNI_LOCK_ROOT wird expandiert."""
    monkeypatch.setenv("OMNI_LOCK_ROOT", "~/my_locks")

    result = resolve_lock_root()

    assert isinstance(result, Path), (
        f"Rueckgabe ist kein pathlib.Path, sondern {type(result)}"
    )
    assert "~" not in str(result), (
        f"Tilde wurde nicht expandiert: {result!r}"
    )
    assert str(Path.home()) in str(result), (
        f"Home-Pfad fehlt nach Tilde-Expansion: {result!r}"
    )
