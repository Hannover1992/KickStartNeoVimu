"""
test_scope_guard.py — BL-460 B-1 RED-Phase (Stage 1 unit, M3).

Tests fuer scope_guard.check_vault_scope(target_path, vault_root):
  - OmniCommand-vault path → (True, "")
  - DCS-Vault path (fremder Vault) → (False, reason)
  - fail-open: malformed input / exception → (True, ...) kein Crash
  - CLI exit codes via main([...])

Konventionen: sys.path.insert fuer Import, pytest, tmp_path, main([...]).
RED-STATE: scope_guard.py existiert NICHT → alle Tests schlagen mit ModuleNotFoundError fehl.
"""

import os
import sys
import subprocess
import json

sys.path.insert(0, os.path.dirname(__file__))

import scope_guard  # noqa: E402  (RED: Modul existiert noch nicht)


# ---------------------------------------------------------------------------
# Fixture-Hilfsfunktionen
# ---------------------------------------------------------------------------

def _make_omni_vault(tmp_path):
    """Erstellt eine minimale OmniCommand-Vault-Struktur unter tmp_path."""
    vault = tmp_path / "OmniCommand"
    vault.mkdir()
    (vault / "Backlog").mkdir()
    return vault


def _make_dcs_vault(tmp_path):
    """Erstellt einen separaten DCS-Vault-Pfad unter tmp_path (fremder Vault)."""
    dcs = tmp_path / "DCSRE" / "Vault"
    dcs.mkdir(parents=True)
    return dcs


# ---------------------------------------------------------------------------
# K (Kern): Pfad im OmniCommand-Vault → ALLOW
# ---------------------------------------------------------------------------

def test_omnicommand_path_is_allowed(tmp_path):
    """
    Ein Pfad der sich innerhalb des OmniCommand-Vaults befindet
    muss (True, '') liefern.
    """
    vault = _make_omni_vault(tmp_path)
    target = vault / "Backlog" / "some_file.md"
    target.touch()

    allowed, reason = scope_guard.check_vault_scope(str(target), vault_root=str(vault))

    assert allowed is True
    assert reason == ""


def test_vault_root_itself_is_allowed(tmp_path):
    """
    Grenzfall: target_path == vault_root selbst → ALLOW.
    """
    vault = _make_omni_vault(tmp_path)

    allowed, reason = scope_guard.check_vault_scope(str(vault), vault_root=str(vault))

    assert allowed is True
    assert reason == ""


def test_deeply_nested_omnicommand_path_is_allowed(tmp_path):
    """
    Ein tief verschachtelter Pfad innerhalb OmniCommand-Vault → ALLOW.
    """
    vault = _make_omni_vault(tmp_path)
    deep = vault / "Backlog" / "BL-460" / "4_Blueprint" / "S1" / "blueprint.md"
    deep.parent.mkdir(parents=True)
    deep.touch()

    allowed, reason = scope_guard.check_vault_scope(str(deep), vault_root=str(vault))

    assert allowed is True
    assert reason == ""


# ---------------------------------------------------------------------------
# K (Kern): DCS-Vault / fremder Vault → BLOCK
# ---------------------------------------------------------------------------

def test_dcs_vault_path_is_blocked(tmp_path):
    """
    Ein Pfad ausserhalb des OmniCommand-Vaults (DCS-Vault)
    muss (False, reason) liefern — reason darf nicht leer sein.
    """
    vault = _make_omni_vault(tmp_path)
    dcs = _make_dcs_vault(tmp_path)
    target = dcs / "some_node.md"
    target.touch()

    allowed, reason = scope_guard.check_vault_scope(str(target), vault_root=str(vault))

    assert allowed is False
    assert reason != ""


def test_sibling_vault_with_same_prefix_is_blocked(tmp_path):
    """
    B (Boundary): Pfad mit gleichem Praefix-String aber anderem Vault-Knoten → BLOCK.
    Schutzt vor einfachem startswith-Bug ohne Path-Normalisierung.
    Beispiel: vault_root=/OmniCommand, target=/OmniCommandExtra/file.md
    """
    vault = tmp_path / "OmniCommand"
    vault.mkdir()
    sibling = tmp_path / "OmniCommandExtra"
    sibling.mkdir()
    target = sibling / "file.md"
    target.touch()

    allowed, reason = scope_guard.check_vault_scope(str(target), vault_root=str(vault))

    assert allowed is False
    assert reason != ""


def test_parent_of_vault_root_is_blocked(tmp_path):
    """
    Das Elternverzeichnis des vault_root ist KEIN gueltiger OmniCommand-Pfad → BLOCK.
    """
    vault = _make_omni_vault(tmp_path)
    parent = tmp_path  # Elterverzeichnis

    allowed, reason = scope_guard.check_vault_scope(str(parent), vault_root=str(vault))

    assert allowed is False
    assert reason != ""


# ---------------------------------------------------------------------------
# A (Ausnahme): fail-open — kein Crash bei Sonderfaellen
# ---------------------------------------------------------------------------

def test_none_target_path_failopen():
    """
    A: target_path=None → fail-open: (True, ...) statt Exception.
    Kein Crash — Guards duerfen den Betrieb nicht lahmlegen.
    """
    try:
        result = scope_guard.check_vault_scope(None, vault_root="/some/path")
        allowed, _ = result
        assert allowed is True  # fail-open
    except Exception as exc:
        raise AssertionError(f"fail-open verletzt — Exception statt graceful return: {exc}") from exc


def test_nonexistent_vault_root_failopen(tmp_path):
    """
    A: vault_root existiert nicht → fail-open: (True, ...) statt Exception.
    """
    target = tmp_path / "some_file.md"
    fake_vault = tmp_path / "does_not_exist"

    try:
        result = scope_guard.check_vault_scope(str(target), vault_root=str(fake_vault))
        allowed, _ = result
        assert allowed is True  # fail-open
    except Exception as exc:
        raise AssertionError(f"fail-open verletzt — Exception statt graceful return: {exc}") from exc


def test_empty_string_target_failopen():
    """
    A: leerer String als target_path → fail-open: kein Crash.
    """
    try:
        result = scope_guard.check_vault_scope("", vault_root="/some/vault")
        allowed, _ = result
        assert allowed is True  # fail-open
    except Exception as exc:
        raise AssertionError(f"fail-open verletzt — Exception statt graceful return: {exc}") from exc


# ---------------------------------------------------------------------------
# CLI exit codes via main([...]) — DT-5-Konvention
# ---------------------------------------------------------------------------

def test_cli_exit_0_for_allowed_path(tmp_path):
    """
    CLI main([...]) gibt 0 zurueck wenn Pfad im OmniCommand-Vault liegt.
    """
    vault = _make_omni_vault(tmp_path)
    target = vault / "Backlog" / "file.md"
    target.touch()

    exit_code = scope_guard.main(["--path", str(target), "--vault-root", str(vault)])

    assert exit_code == 0


def test_cli_exit_1_for_blocked_path(tmp_path):
    """
    CLI main([...]) gibt 1 zurueck wenn Pfad ausserhalb des Vaults liegt
    und enforceProcess=true (default).
    """
    vault = _make_omni_vault(tmp_path)
    dcs = _make_dcs_vault(tmp_path)
    target = dcs / "blocked.md"
    target.touch()

    exit_code = scope_guard.main(["--path", str(target), "--vault-root", str(vault)])

    assert exit_code == 1


def test_cli_exit_2_for_missing_args():
    """
    CLI main([...]) gibt 2 zurueck bei Usage-Fehler (kein --path und kein Stdin).
    """
    # Rufe main mit leeren Args (kein --path, kein stdin) und erwarte 2
    # Implementierung darf auch SystemExit(2) werfen — beide akzeptiert.
    try:
        exit_code = scope_guard.main(["--vault-root", "/some/vault"])
        # Falls kein Exception: muss 2 sein
        assert exit_code == 2
    except SystemExit as e:
        assert e.code == 2


def test_cli_stdout_json_for_blocked_path(tmp_path, capsys):
    """
    CLI gibt JSON {"continue": false, "message": "..."} auf stdout bei BLOCK.
    """
    vault = _make_omni_vault(tmp_path)
    dcs = _make_dcs_vault(tmp_path)
    target = dcs / "blocked.md"
    target.touch()

    scope_guard.main(["--path", str(target), "--vault-root", str(vault)])

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["continue"] is False
    assert "message" in output


def test_cli_stdout_json_for_allowed_path(tmp_path, capsys):
    """
    CLI gibt JSON {"continue": true, ...} auf stdout bei ALLOW.
    """
    vault = _make_omni_vault(tmp_path)
    target = vault / "file.md"
    target.touch()

    scope_guard.main(["--path", str(target), "--vault-root", str(vault)])

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["continue"] is True
