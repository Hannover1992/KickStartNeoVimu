"""
test_write_gate_guard.py — BL-460 B-1 RED-Phase (Stage 1 unit, M3).

Tests fuer:
  - write_gate_guard.is_write_gated(vault_root) -> (bool, str)
  - write_gate_guard._count_corrupt_nodes(vault_root) -> int
  - CLI exit codes via main([...])

Gold-Kriterien (Blueprint S1):
  - clean vault (keine null-bytes) → (False, "clean — 0 corrupt nodes")
  - vault mit >=1 null-byte-Datei → (True, "N corrupt nodes found ...")
  - _count_corrupt_nodes zaehlt exakt die null-byte-Dateien
  - fail-open: IOError/PermissionError → (True,...) kein Crash
  - CLI: 0=clean/ALLOW, 1=gated+enforceProcess=true, 2=usage

RED-STATE: write_gate_guard.py existiert NICHT → alle Tests schlagen mit ModuleNotFoundError fehl.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import write_gate_guard  # noqa: E402  (RED: Modul existiert noch nicht)


# ---------------------------------------------------------------------------
# K (Kern): clean vault → ALLOW
# ---------------------------------------------------------------------------

def test_clean_vault_not_gated(tmp_path):
    """
    K: Vault mit nur sauberen .md-Dateien (keine null-bytes) → is_write_gated False.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "a.md").write_bytes(b"# Hello\nno null bytes here\n")
    (vault / "b.md").write_bytes(b"## Section\nclean content\n")

    gated, reason = write_gate_guard.is_write_gated(vault_root=str(vault))

    assert gated is False
    assert "0" in reason or "clean" in reason.lower()


def test_clean_vault_count_is_zero(tmp_path):
    """
    K: _count_corrupt_nodes gibt 0 zurueck bei sauberen Dateien.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "clean.md").write_bytes(b"clean content, no nulls\n")

    count = write_gate_guard._count_corrupt_nodes(vault)

    assert count == 0


def test_empty_vault_not_gated(tmp_path):
    """
    K: Leerer Vault (keine .md-Dateien) → nicht gegated, 0 corrupt nodes.
    """
    vault = tmp_path / "empty_vault"
    vault.mkdir()

    gated, reason = write_gate_guard.is_write_gated(vault_root=str(vault))

    assert gated is False
    assert write_gate_guard._count_corrupt_nodes(vault) == 0


# ---------------------------------------------------------------------------
# K (Kern): vault mit null-byte-Dateien → BLOCK
# ---------------------------------------------------------------------------

def test_single_corrupt_file_gates_write(tmp_path):
    """
    K: Eine Datei mit null-byte → is_write_gated True.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "corrupt.md").write_bytes(b"before\x00after\n")
    (vault / "clean.md").write_bytes(b"no null byte\n")

    gated, reason = write_gate_guard.is_write_gated(vault_root=str(vault))

    assert gated is True
    # Reason muss Anzahl corrupt nodes enthalten
    assert "1" in reason


def test_multiple_corrupt_files_count_in_reason(tmp_path):
    """
    K: Mehrere null-byte-Dateien → reason nennt die korrekte Anzahl.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "c1.md").write_bytes(b"data\x00here")
    (vault / "c2.md").write_bytes(b"\x00start")
    (vault / "c3.md").write_bytes(b"end\x00")
    (vault / "clean.md").write_bytes(b"fine content")

    gated, reason = write_gate_guard.is_write_gated(vault_root=str(vault))

    assert gated is True
    assert "3" in reason


def test_count_corrupt_nodes_exact_count(tmp_path):
    """
    K: _count_corrupt_nodes zaehlt exakt N null-byte-Dateien (nicht mehr, nicht weniger).
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "c1.md").write_bytes(b"null\x00byte")
    (vault / "c2.md").write_bytes(b"also\x00null")
    (vault / "ok.md").write_bytes(b"clean")

    count = write_gate_guard._count_corrupt_nodes(vault)

    assert count == 2


def test_count_corrupt_nodes_nested_directory(tmp_path):
    """
    K: _count_corrupt_nodes traversiert Unterverzeichnisse (rglob).
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    sub = vault / "Backlog" / "BL-999"
    sub.mkdir(parents=True)
    (sub / "deep_corrupt.md").write_bytes(b"deep\x00null")
    (vault / "root.md").write_bytes(b"clean root")

    count = write_gate_guard._count_corrupt_nodes(vault)

    assert count == 1


# ---------------------------------------------------------------------------
# B (Boundary): Grenzfall — genau 1 null-byte-Node (Schwelle)
# ---------------------------------------------------------------------------

def test_exactly_one_corrupt_node_triggers_gate(tmp_path):
    """
    B: Genau 1 null-byte-Node ist die Schwelle — muss BLOCK ausloesen.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "boundary.md").write_bytes(b"before\x00after")

    gated, _ = write_gate_guard.is_write_gated(vault_root=str(vault))
    count = write_gate_guard._count_corrupt_nodes(vault)

    assert gated is True
    assert count == 1


def test_non_md_files_not_counted(tmp_path):
    """
    B: Nur .md-Dateien werden gescannt — .py/.json mit null-bytes zaehlen NICHT.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "script.py").write_bytes(b"py\x00file")  # keine .md → ignorieren
    (vault / "data.json").write_bytes(b'{"x":"\x00"}')  # keine .md → ignorieren
    (vault / "clean.md").write_bytes(b"clean markdown")

    count = write_gate_guard._count_corrupt_nodes(vault)
    gated, _ = write_gate_guard.is_write_gated(vault_root=str(vault))

    assert count == 0
    assert gated is False


def test_file_with_multiple_nulls_counts_as_one(tmp_path):
    """
    B: Eine Datei mit mehreren null-bytes zaehlt als 1 corrupt node (nicht mehr).
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "multi_null.md").write_bytes(b"\x00\x00\x00multiple nulls\x00")

    count = write_gate_guard._count_corrupt_nodes(vault)

    assert count == 1


# ---------------------------------------------------------------------------
# A (Ausnahme): fail-open — kein Crash bei IOError/PermissionError
# ---------------------------------------------------------------------------

def test_failopen_on_nonexistent_vault():
    """
    A: Nicht existenter vault_root → fail-open: (False, ...) oder (True, ...) — KEIN Crash.
    """
    fake_vault = "/this/path/does/not/exist/at/all"

    try:
        result = write_gate_guard.is_write_gated(vault_root=fake_vault)
        gated, reason = result
        # fail-open: der Guard darf nicht crashen, return-Typ muss stimmen
        assert isinstance(gated, bool)
        assert isinstance(reason, str)
    except Exception as exc:
        raise AssertionError(f"fail-open verletzt — Exception statt graceful return: {exc}") from exc


def test_count_corrupt_nodes_failopen_on_nonexistent(tmp_path):
    """
    A: _count_corrupt_nodes mit nicht-existentem Pfad → kein Crash, gibt int zurueck.
    """
    fake = tmp_path / "does_not_exist"

    try:
        count = write_gate_guard._count_corrupt_nodes(fake)
        assert isinstance(count, int)
        assert count >= 0
    except Exception as exc:
        raise AssertionError(f"fail-open verletzt in _count_corrupt_nodes: {exc}") from exc


# ---------------------------------------------------------------------------
# CLI exit codes via main([...]) — DT-5-Konvention
# ---------------------------------------------------------------------------

def test_cli_exit_0_for_clean_vault(tmp_path):
    """
    CLI main([...]) gibt 0 zurueck wenn Vault sauber ist.
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "clean.md").write_bytes(b"no null bytes")

    exit_code = write_gate_guard.main(["--vault-root", str(vault)])

    assert exit_code == 0


def test_cli_exit_1_for_gated_vault(tmp_path):
    """
    CLI main([...]) gibt 1 zurueck wenn Vault korrupt ist (enforceProcess=true default).
    """
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "corrupt.md").write_bytes(b"null\x00here")

    exit_code = write_gate_guard.main(["--vault-root", str(vault)])

    assert exit_code == 1


def test_cli_exit_2_for_invalid_args():
    """
    CLI main([...]) gibt 2 zurueck bei Usage-Fehler.
    """
    try:
        exit_code = write_gate_guard.main(["--invalid-flag-xyz"])
        assert exit_code == 2
    except SystemExit as e:
        assert e.code == 2


def test_cli_stdout_json_continue_false_for_gated(tmp_path, capsys):
    """
    CLI gibt JSON {"continue": false, "message": "..."} wenn Vault gegated ist.
    """
    import json
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "corrupt.md").write_bytes(b"data\x00corrupt")

    write_gate_guard.main(["--vault-root", str(vault)])

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["continue"] is False
    assert "message" in output


def test_cli_stdout_json_continue_true_for_clean(tmp_path, capsys):
    """
    CLI gibt JSON {"continue": true} wenn Vault sauber ist.
    """
    import json
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "clean.md").write_bytes(b"all good")

    write_gate_guard.main(["--vault-root", str(vault)])

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert output["continue"] is True
