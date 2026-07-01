"""
BL-450 batch_2 Stage 1 -- RED-Worker Tests
_extraction_orchestrate.py -- 5-Stufen-Orchestrator CLI-Wrapper

17 Tests (9 K-Tests + 4 B-Tests + 4 A-Tests).
Alle subprocess.run-Aufrufe gemockt -- prueft ROUTING + GATING, keine echte Vault-Mutation.
Zieldatei _extraction_orchestrate.py existiert noch NICHT -> ALLE Tests fehlschlagen (RED).

INV-EO-2 (KRITISCH): mode=extract/full OHNE --confirm-cutover -> kein Cutover-Aufruf, exit 1.
INV-EO-4: --vault required (argparse), kein Optional mit Default.
AK-6: kein hardcoded Vault-Pfad.
"""

import importlib
import subprocess
import sys
import os
import pathlib
import pytest
from unittest.mock import patch, MagicMock, call


# ---------------------------------------------------------------------------
# Hilfsfunktionen
# ---------------------------------------------------------------------------

def _import_eo():
    """Importiert _extraction_orchestrate -- schlaegt fehl wenn Modul nicht existiert (RED)."""
    import importlib.util
    scripts_dir = pathlib.Path(__file__).parent
    spec = importlib.util.spec_from_file_location(
        "_extraction_orchestrate",
        scripts_dir / "_extraction_orchestrate.py",
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run_main(argv, mock_subprocess=True, extra_patches=None):
    """
    Ruft eo.main(argv) auf.
    Wenn mock_subprocess=True, wird subprocess.run gemockt (returncode=0).
    Gibt (return_code, mock_subprocess_run) zurueck.
    """
    eo = _import_eo()
    patches = []
    mock_sp = None
    if mock_subprocess:
        patcher = patch.object(eo.subprocess, "run", return_value=MagicMock(returncode=0))
        mock_sp = patcher.start()
        patches.append(patcher)
    if extra_patches:
        for p in extra_patches:
            p.start()
            patches.append(p)
    try:
        rc = eo.main(argv)
    except SystemExit as e:
        rc = e.code
    finally:
        for p in patches:
            p.stop()
    return rc, mock_sp


def _valid_vault(tmp_path):
    """Erstellt ein temporaeres Vault-Verzeichnis und gibt den Pfad als str zurueck."""
    v = tmp_path / "vault"
    v.mkdir()
    return str(v)


# ---------------------------------------------------------------------------
# K-Kategorie (Kern-Verhalten)
# ---------------------------------------------------------------------------

class TestKernVerhalten:

    def test_k_eo_1_mode_analyse_calls_stage1_only(self, tmp_path):
        """K-EO-1: --mode analyse --vault {valid} ruft nur Stufe-1-Script auf (truth_migrate_orchestrator)."""
        vault = _valid_vault(tmp_path)
        eo = _import_eo()
        with patch.object(eo.subprocess, "run", return_value=MagicMock(returncode=0)) as mock_sp:
            rc = eo.main(["--mode", "analyse", "--vault", vault])
        assert rc == 0
        called_scripts = [c.args[0][1] for c in mock_sp.call_args_list]
        assert any("truth_migrate_orchestrator" in s for s in called_scripts), (
            "Stufe 1 (truth_migrate_orchestrator) wurde nicht aufgerufen"
        )
        # Stufen 2-5 sollen NICHT aufgerufen werden
        for forbidden in ("truth_normalize", "truth_gate_check", "truth_pilot_cutover"):
            assert not any(forbidden in s for s in called_scripts), (
                f"mode=analyse darf {forbidden} nicht aufrufen"
            )

    def test_k_eo_2_mode_edges_calls_stage5_only(self, tmp_path):
        """K-EO-2: --mode edges --vault {valid} ruft nur Stufe-5 (keyword_edge_writer) auf."""
        vault = _valid_vault(tmp_path)
        eo = _import_eo()
        # keyword_edge_writer.main kann direkt importiert werden; mocken
        with patch.object(eo, "run_stage5_edges", return_value=0) as mock_s5, \
             patch.object(eo.subprocess, "run", return_value=MagicMock(returncode=0)) as mock_sp:
            rc = eo.main(["--mode", "edges", "--vault", vault])
        assert rc == 0
        mock_s5.assert_called_once()
        # Stufen 1-4 sollen NICHT aufgerufen worden sein
        assert mock_sp.call_count == 0, "mode=edges darf subprocess nicht fuer Stufen 1-4 aufrufen"

    def test_k_eo_3_mode_extract_without_confirm_exits_1(self, tmp_path):
        """K-EO-3: --mode extract OHNE --confirm-cutover -> exit 1 (INV-EO-2 KRITISCH)."""
        vault = _valid_vault(tmp_path)
        rc, mock_sp = _run_main(["--mode", "extract", "--vault", vault])
        assert rc == 1, (
            "INV-EO-2 verletzt: mode=extract ohne --confirm-cutover muss exit 1 liefern"
        )
        # truth_pilot_cutover darf NICHT aufgerufen worden sein
        if mock_sp is not None:
            called_scripts = [c.args[0][1] for c in mock_sp.call_args_list]
            assert not any("truth_pilot_cutover" in s for s in called_scripts), (
                "truth_pilot_cutover darf ohne --confirm-cutover NICHT aufgerufen werden"
            )

    def test_k_eo_4_mode_full_without_confirm_exits_1(self, tmp_path):
        """K-EO-4: --mode full OHNE --confirm-cutover -> exit 1 (INV-EO-2 KRITISCH)."""
        vault = _valid_vault(tmp_path)
        rc, mock_sp = _run_main(["--mode", "full", "--vault", vault])
        assert rc == 1, (
            "INV-EO-2 verletzt: mode=full ohne --confirm-cutover muss exit 1 liefern"
        )
        if mock_sp is not None:
            called_scripts = [c.args[0][1] for c in mock_sp.call_args_list]
            assert not any("truth_pilot_cutover" in s for s in called_scripts), (
                "truth_pilot_cutover darf ohne --confirm-cutover NICHT aufgerufen werden"
            )

    def test_k_eo_5_mode_probe_calls_stages_1_2_3(self, tmp_path):
        """K-EO-5: --mode probe ruft Stufen 1+2+3 auf (truth_migrate_orchestrator, truth_normalize, truth_gate_check)."""
        vault = _valid_vault(tmp_path)
        eo = _import_eo()
        with patch.object(eo.subprocess, "run", return_value=MagicMock(returncode=0)) as mock_sp:
            rc = eo.main(["--mode", "probe", "--vault", vault])
        assert rc == 0
        called_scripts = [c.args[0][1] for c in mock_sp.call_args_list]
        for expected in ("truth_migrate_orchestrator", "truth_normalize", "truth_gate_check"):
            assert any(expected in s for s in called_scripts), (
                f"mode=probe muss {expected} aufrufen"
            )
        # Stufe 4 soll NICHT aufgerufen werden
        assert not any("truth_pilot_cutover" in s for s in called_scripts), (
            "mode=probe darf truth_pilot_cutover nicht aufrufen"
        )

    def test_k_eo_6_no_hardcoded_vault_path_in_source(self):
        """K-EO-6: Kein hardcoded Vault-Pfad im Quellcode (grep-Check AK-6 + INV-EO-1)."""
        source_path = pathlib.Path(__file__).parent / "_extraction_orchestrate.py"
        assert source_path.exists(), "_extraction_orchestrate.py existiert nicht"
        content = source_path.read_text(encoding="utf-8")
        forbidden_patterns = [
            "OmniCommand",
            "C:\\\\Users\\\\hanno",
            "C:/Users/hanno",
            "/home/",
            "DEFAULT_VAULT",
        ]
        for pattern in forbidden_patterns:
            assert pattern not in content, (
                f"INV-EO-1 verletzt: hardcoded Vault-Pfad '{pattern}' in _extraction_orchestrate.py gefunden"
            )

    def test_k_eo_7_missing_vault_exits_2(self):
        """K-EO-7: --vault fehlt -> argparse exit 2 (INV-EO-4 / AK-6)."""
        rc, _ = _run_main(["--mode", "analyse"])
        assert rc == 2, (
            "INV-EO-4: fehlendes --vault muss argparse exit 2 produzieren"
        )

    def test_k_eo_8_nonexistent_vault_exits_with_error(self, tmp_path):
        """K-EO-8: --vault {non_existent_dir} -> exit != 0 mit Fehlermeldung."""
        non_existent = str(tmp_path / "does_not_exist")
        rc, _ = _run_main(["--mode", "analyse", "--vault", non_existent])
        assert rc != 0, (
            "AK-6: nicht-existierendes --vault muss einen Fehler-Exit produzieren"
        )

    def test_k_eo_9_mode_full_with_confirm_calls_all_5_stages(self, tmp_path):
        """K-EO-9: --mode full --vault {valid} --confirm-cutover ruft alle 5 Stufen auf."""
        vault = _valid_vault(tmp_path)
        eo = _import_eo()
        with patch.object(eo.subprocess, "run", return_value=MagicMock(returncode=0)) as mock_sp, \
             patch.object(eo, "run_stage5_edges", return_value=0) as mock_s5:
            rc = eo.main(["--mode", "full", "--vault", vault, "--confirm-cutover"])
        assert rc == 0
        called_scripts = [c.args[0][1] for c in mock_sp.call_args_list]
        for expected in (
            "truth_migrate_orchestrator",
            "truth_normalize",
            "truth_gate_check",
            "truth_pilot_cutover",
        ):
            assert any(expected in s for s in called_scripts), (
                f"mode=full mit --confirm-cutover muss {expected} aufrufen"
            )
        mock_s5.assert_called_once()


# ---------------------------------------------------------------------------
# B-Kategorie (Boundary-Verhalten)
# ---------------------------------------------------------------------------

class TestBoundaryVerhalten:

    def test_b_eo_1_dry_run_flag_forwarded_to_subprocesses(self, tmp_path):
        """B-EO-1: --dry-run Flag wird an Subprocess-Aufrufe weitergeleitet."""
        vault = _valid_vault(tmp_path)
        eo = _import_eo()
        with patch.object(eo.subprocess, "run", return_value=MagicMock(returncode=0)) as mock_sp:
            rc = eo.main(["--mode", "analyse", "--vault", vault, "--dry-run"])
        assert rc == 0
        # Zumindest ein Subprocess-Aufruf muss "--dry-run" in den Args enthalten
        found_dry_run = False
        for c in mock_sp.call_args_list:
            if "--dry-run" in c.args[0]:
                found_dry_run = True
                break
        assert found_dry_run, "--dry-run muss an Subprocess-Aufrufe weitergeleitet werden"

    def test_b_eo_2_invalid_mode_causes_argparse_error(self, tmp_path):
        """B-EO-2: --mode mit ungueltigem Wert -> argparse error (choices-Pruefung)."""
        vault = _valid_vault(tmp_path)
        rc, _ = _run_main(["--mode", "invalid_mode_xyz", "--vault", vault])
        assert rc == 2, (
            "Ungueltiger --mode Wert muss argparse exit 2 produzieren"
        )

    def test_b_eo_3_resolve_vault_root_returns_path_for_existing_dir(self, tmp_path):
        """B-EO-3: resolve_vault_root() gibt Path zurueck bei existierendem Dir."""
        vault = _valid_vault(tmp_path)
        eo = _import_eo()
        result = eo.resolve_vault_root(vault)
        assert isinstance(result, pathlib.Path), (
            "resolve_vault_root muss ein pathlib.Path-Objekt zurueckgeben"
        )
        assert result.exists(), "resolve_vault_root muss einen existierenden Pfad zurueckgeben"

    def test_b_eo_4_resolve_vault_root_raises_for_nonexistent_path(self, tmp_path):
        """B-EO-4: resolve_vault_root() wirft SystemExit oder ValueError bei nicht-existierendem Pfad."""
        eo = _import_eo()
        non_existent = str(tmp_path / "does_not_exist")
        with pytest.raises((SystemExit, ValueError, FileNotFoundError)):
            eo.resolve_vault_root(non_existent)


# ---------------------------------------------------------------------------
# A-Kategorie (Assertions / Struktur-Checks)
# ---------------------------------------------------------------------------

class TestStrukturChecks:

    def test_a_eo_1_extraction_orchestrate_file_exists(self):
        """A-EO-1: _extraction_orchestrate.py existiert unter .claude/scripts/."""
        target = pathlib.Path(__file__).parent / "_extraction_orchestrate.py"
        assert target.exists(), (
            "_extraction_orchestrate.py existiert nicht unter .claude/scripts/"
        )

    def test_a_eo_2_help_output_contains_all_5_modes(self, capsys):
        """A-EO-2: --help Output enthaelt alle 5 Modi-Strings (analyse/probe/extract/edges/full)."""
        try:
            rc, _ = _run_main(["--help"], mock_subprocess=False)
        except SystemExit:
            pass
        captured = capsys.readouterr()
        help_text = captured.out + captured.err
        for mode in ("analyse", "probe", "extract", "edges", "full"):
            assert mode in help_text, (
                f"--help Output muss Modus '{mode}' enthalten"
            )

    def test_a_eo_3_help_output_contains_vault_param(self, capsys):
        """A-EO-3: --help Output enthaelt --vault."""
        try:
            rc, _ = _run_main(["--help"], mock_subprocess=False)
        except SystemExit:
            pass
        captured = capsys.readouterr()
        help_text = captured.out + captured.err
        assert "--vault" in help_text, "--help Output muss --vault enthalten"

    def test_a_eo_4_main_entry_point_convention(self):
        """A-EO-4: sys.exit(main()) Konvention vorhanden (if __name__ == '__main__')."""
        source_path = pathlib.Path(__file__).parent / "_extraction_orchestrate.py"
        assert source_path.exists(), "_extraction_orchestrate.py existiert nicht"
        content = source_path.read_text(encoding="utf-8")
        assert '__name__' in content and '__main__' in content, (
            "if __name__ == '__main__' Konvention fehlt"
        )
        assert "main()" in content, "main() Einstiegspunkt fehlt"
