#!/usr/bin/env python3
"""
test_migrate_manifest_split.py — BL-173 AK-6 (partial): Tests fuer migrate_manifest_split.py

Tests:
1. test_block_classification: Mock-Manifest → korrekte factory/bl-Klassifikation
2. test_bl_id_resolution: Per-Block bl_id-Extraktion
3. test_dry_run_no_write: Dry-Run veraendert keine Files
4. test_atomic_write: Migration bei Fehler → komplettes Rollback
5. test_rollback: Rollback stellt _manifest.md wieder her

Aufruf: pytest .claude/scripts/test_migrate_manifest_split.py -v
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import textwrap
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest

# Skript-Verzeichnis zum sys.path hinzufuegen
_HERE = Path(__file__).parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from migrate_manifest_split import (
    BL_BLOCK_NAMES,
    FACTORY_BLOCK_NAMES,
    ManifestBlock,
    MigrationPlan,
    build_plan,
    classify_block,
    cmd_dry_run,
    cmd_migrate,
    cmd_rollback,
    cmd_verify,
    extract_bl_id_from_block_name,
    extract_bl_id_from_content,
    find_bl_folder,
    parse_manifest,
    render_bl_content,
    render_factory_content,
    render_orphan_content,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_vault(tmp_path: Path) -> Path:
    """Erstellt eine minimale Vault-Struktur mit Mock-Manifest."""
    vault = tmp_path / "OmniCommand"
    vault.mkdir()
    backlog = vault / "Backlog"
    backlog.mkdir()
    # BL-159 Ordner
    (backlog / "BL-159-skill-loading-compliance").mkdir()
    # BL-162 Ordner
    (backlog / "BL-162-kscore-coupling-analysis").mkdir()
    return vault


@pytest.fixture
def sample_manifest_content() -> str:
    return textwrap.dedent("""\
        # Forschungs-Manifest
        **GLOBAL_MODUS:** small_dark_factory
        **GLOBAL_DIFFICULTY:** easy
        **GLOBAL_CEILING:** opus
        **GLOBAL_FLOOR:** sonnet
        **GLOBAL_HIL:** off
        active_feature: BL-162

        ## BDF_PIPELINE_STATE
        bdf_status: SCANNING
        current_item: null
        items_done: []
        bdf_start: 2026-05-14
        feature_branch: feature/bdf-2026-05-14

        ## FACTORY_STATES
        SDF_DEFAULT:
          instance_id: SDF_DEFAULT
          status: DONE

        ## SC_PIPELINE_STATE
        sc_status: SETUP
        sc_mode: FULL
        sc_name: BL-162-SubA
        sc_target_bl: BL-162
        sc_start: 2026-05-16

        ## DF_BATCH_STATE
        batch_items: [BL-NEW-61, BL-NEW-47]
        batch_status: DONE
        modus: M7
        bl_id: BL-159

        ## BERATER_OUTPUTS_IDF_BL162
        BERATER_OUTPUTS_IDF_BL162.init:
          completed_at: 2026-05-18
          bl_id: BL-162

        ## BERATER_OUTPUTS
        teamSetup:
          completed_at: 2026-05-17
          bl_id: BL-159

        ## UNKNOWN_BLOCK_NO_BL
        some_field: some_value
        no_bl_id_here: true
    """)


@pytest.fixture
def mock_vault_with_manifest(mock_vault: Path, sample_manifest_content: str) -> Path:
    """Vault mit befueltem _manifest.md."""
    (mock_vault / "_manifest.md").write_text(sample_manifest_content, encoding="utf-8")
    return mock_vault


# ---------------------------------------------------------------------------
# Test 1: Block-Klassifikation
# ---------------------------------------------------------------------------

class TestBlockClassification:
    """test_block_classification: Mock-Manifest → korrekte factory/bl-Klassifikation."""

    def test_global_header_is_factory(self, mock_vault: Path) -> None:
        block = ManifestBlock(header="", block_name="_GLOBAL_HEADER",
                              lines=["**GLOBAL_MODUS:** small_dark_factory"])
        classify_block(block, mock_vault)
        assert block.scope == "factory"

    def test_bdf_pipeline_state_is_factory(self, mock_vault: Path) -> None:
        block = ManifestBlock(header="## BDF_PIPELINE_STATE", block_name="BDF_PIPELINE_STATE",
                              lines=["bdf_status: SCANNING"])
        classify_block(block, mock_vault)
        assert block.scope == "factory"
        assert block.bl_id is None

    def test_factory_states_is_factory(self, mock_vault: Path) -> None:
        block = ManifestBlock(header="## FACTORY_STATES", block_name="FACTORY_STATES",
                              lines=["SDF_DEFAULT:", "  status: DONE"])
        classify_block(block, mock_vault)
        assert block.scope == "factory"

    def test_backlog_state_is_factory(self, mock_vault: Path) -> None:
        block = ManifestBlock(header="## BACKLOG_STATE", block_name="BACKLOG_STATE",
                              lines=["counter: 173"])
        classify_block(block, mock_vault)
        assert block.scope == "factory"

    def test_sc_pipeline_state_with_bl_id_is_bl(self, mock_vault: Path) -> None:
        block = ManifestBlock(header="## SC_PIPELINE_STATE", block_name="SC_PIPELINE_STATE",
                              lines=["sc_target_bl: BL-162", "sc_status: SETUP"])
        classify_block(block, mock_vault)
        assert block.scope == "bl"
        assert block.bl_id == "BL-162"

    def test_df_batch_state_with_bl_id_is_bl(self, mock_vault: Path) -> None:
        block = ManifestBlock(header="## DF_BATCH_STATE", block_name="DF_BATCH_STATE",
                              lines=["bl_id: BL-159", "modus: M7"])
        classify_block(block, mock_vault)
        assert block.scope == "bl"
        assert block.bl_id == "BL-159"

    def test_berater_outputs_with_bl_suffix_is_bl(self, mock_vault: Path) -> None:
        block = ManifestBlock(header="## BERATER_OUTPUTS_IDF_BL162",
                              block_name="BERATER_OUTPUTS_IDF_BL162",
                              lines=["completed_at: 2026-05-18"])
        classify_block(block, mock_vault)
        assert block.scope == "bl"
        assert block.bl_id == "BL-162"

    def test_berater_outputs_with_bl_id_in_content_is_bl(self, mock_vault: Path) -> None:
        block = ManifestBlock(header="## BERATER_OUTPUTS", block_name="BERATER_OUTPUTS",
                              lines=["teamSetup:", "  bl_id: BL-159"])
        classify_block(block, mock_vault)
        assert block.scope == "bl"
        assert block.bl_id == "BL-159"

    def test_unknown_block_without_bl_id_is_orphan(self, mock_vault: Path) -> None:
        block = ManifestBlock(header="## MYSTERY_STATE", block_name="MYSTERY_STATE",
                              lines=["some_field: value"])
        classify_block(block, mock_vault)
        assert block.scope == "orphan"
        assert block.bl_id is None

    def test_sc_pipeline_state_without_bl_id_is_orphan(self, mock_vault: Path) -> None:
        block = ManifestBlock(header="## SC_PIPELINE_STATE", block_name="SC_PIPELINE_STATE",
                              lines=["sc_status: SETUP"])
        classify_block(block, mock_vault)
        assert block.scope == "orphan"

    def test_full_manifest_classification(self, mock_vault_with_manifest: Path) -> None:
        """Voller Manifest-Parse + Klassifikation."""
        manifest_path = mock_vault_with_manifest / "_manifest.md"
        plan = build_plan(manifest_path, mock_vault_with_manifest)

        # Factory-Bloecke: _GLOBAL_HEADER, BDF_PIPELINE_STATE, FACTORY_STATES
        factory_names = [b.block_name for b in plan.factory_blocks]
        assert "_GLOBAL_HEADER" in factory_names
        assert "BDF_PIPELINE_STATE" in factory_names
        assert "FACTORY_STATES" in factory_names

        # BL-Bloecke
        assert "BL-162" in plan.bl_blocks or "BL-159" in plan.bl_blocks

        # Orphan: UNKNOWN_BLOCK_NO_BL
        orphan_names = [b.block_name for b in plan.orphan_blocks]
        assert "UNKNOWN_BLOCK_NO_BL" in orphan_names


# ---------------------------------------------------------------------------
# Test 2: BL-ID Extraktion
# ---------------------------------------------------------------------------

class TestBlIdResolution:
    """test_bl_id_resolution: Per-Block bl_id-Extraktion."""

    def test_extract_from_bl_id_field(self) -> None:
        lines = ["bl_id: BL-159", "status: DONE"]
        result = extract_bl_id_from_content(lines)
        assert result == "BL-159"

    def test_extract_from_sc_target_bl(self) -> None:
        lines = ["sc_target_bl: BL-162", "sc_status: SETUP"]
        result = extract_bl_id_from_content(lines)
        assert result == "BL-162"

    def test_extract_from_sc_name(self) -> None:
        lines = ["sc_name: BL-162-SubA", "sc_mode: FULL"]
        result = extract_bl_id_from_content(lines)
        assert result == "BL-162"

    def test_extract_from_block_name_with_bl_suffix(self) -> None:
        result = extract_bl_id_from_block_name("BERATER_OUTPUTS_IDF_BL163")
        assert result == "BL-163"

    def test_extract_from_block_name_with_hyphen(self) -> None:
        result = extract_bl_id_from_block_name("IDF_PIPELINE_STATE_BL-159")
        assert result == "BL-159"

    def test_extract_no_bl_id_returns_none(self) -> None:
        lines = ["some_field: value", "no_bl: here"]
        result = extract_bl_id_from_content(lines)
        assert result is None

    def test_extract_no_bl_id_from_block_name_returns_none(self) -> None:
        result = extract_bl_id_from_block_name("FACTORY_STATES")
        assert result is None

    def test_find_bl_folder_existing(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        backlog = vault / "Backlog"
        backlog.mkdir()
        (backlog / "BL-159-skill-loading").mkdir()
        result = find_bl_folder(vault, "BL-159")
        assert result is not None
        assert result.name == "BL-159-skill-loading"

    def test_find_bl_folder_missing_returns_none(self, tmp_path: Path) -> None:
        vault = tmp_path / "vault"
        vault.mkdir()
        (vault / "Backlog").mkdir()
        result = find_bl_folder(vault, "BL-999")
        assert result is None

    def test_find_bl_folder_no_backlog_dir(self, tmp_path: Path) -> None:
        result = find_bl_folder(tmp_path, "BL-159")
        assert result is None


# ---------------------------------------------------------------------------
# Test 3: Dry-Run schreibt keine Files
# ---------------------------------------------------------------------------

class TestDryRunNoWrite:
    """test_dry_run_no_write: Dry-Run veraendert keine Files."""

    def test_dry_run_does_not_create_factory_manifest(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        cmd_dry_run(mock_vault_with_manifest)
        factory_path = mock_vault_with_manifest / "_factory_manifest.md"
        assert not factory_path.exists(), "_factory_manifest.md darf nach dry-run nicht existieren"

    def test_dry_run_does_not_create_bl_manifests(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        cmd_dry_run(mock_vault_with_manifest)
        backlog = mock_vault_with_manifest / "Backlog"
        for d in backlog.iterdir():
            bl_manifest = d / "_manifest.md"
            assert not bl_manifest.exists(), f"{bl_manifest} darf nach dry-run nicht existieren"

    def test_dry_run_does_not_create_orphans_file(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        cmd_dry_run(mock_vault_with_manifest)
        orphan_path = mock_vault_with_manifest / "_manifest_orphans.md"
        assert not orphan_path.exists(), "_manifest_orphans.md darf nach dry-run nicht existieren"

    def test_dry_run_original_manifest_unchanged(
        self, mock_vault_with_manifest: Path, capsys, sample_manifest_content: str
    ) -> None:
        original = (mock_vault_with_manifest / "_manifest.md").read_text(encoding="utf-8")
        cmd_dry_run(mock_vault_with_manifest)
        after = (mock_vault_with_manifest / "_manifest.md").read_text(encoding="utf-8")
        assert original == after, "_manifest.md muss nach dry-run unveraendert sein"

    def test_dry_run_returns_summary_dict(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        result = cmd_dry_run(mock_vault_with_manifest)
        assert isinstance(result, dict)
        assert result["mode"] == "dry-run"
        assert "factory_blocks_count" in result
        assert "total_lines_processed" in result
        assert result["total_lines_processed"] > 0

    def test_dry_run_shows_plan_in_stdout(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        cmd_dry_run(mock_vault_with_manifest)
        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "_factory_manifest.md" in captured.out


# ---------------------------------------------------------------------------
# Test 4: Atomisches Write — bei Fehler kompletter Rollback
# ---------------------------------------------------------------------------

class TestAtomicWrite:
    """test_atomic_write: Migration bei Fehler in einem File → komplettes Rollback."""

    def test_migration_creates_factory_manifest(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        cmd_migrate(mock_vault_with_manifest, rollback_tag="test", force=True)
        assert (mock_vault_with_manifest / "_factory_manifest.md").exists()

    def test_migration_creates_backup(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        cmd_migrate(mock_vault_with_manifest, rollback_tag="test-backup", force=True)
        backup = mock_vault_with_manifest / "_manifest.backup-test-backup.md"
        assert backup.exists(), "Backup-Datei muss erstellt werden"

    def test_migration_backup_equals_original(
        self, mock_vault_with_manifest: Path, capsys, sample_manifest_content: str
    ) -> None:
        cmd_migrate(mock_vault_with_manifest, rollback_tag="verify-backup", force=True)
        backup = mock_vault_with_manifest / "_manifest.backup-verify-backup.md"
        backup_content = backup.read_text(encoding="utf-8")
        assert backup_content == sample_manifest_content

    def test_migration_factory_manifest_contains_bdf_state(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        cmd_migrate(mock_vault_with_manifest, rollback_tag="test", force=True)
        factory = (mock_vault_with_manifest / "_factory_manifest.md").read_text(encoding="utf-8")
        assert "BDF_PIPELINE_STATE" in factory

    def test_migration_factory_manifest_no_sc_pipeline(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        cmd_migrate(mock_vault_with_manifest, rollback_tag="test", force=True)
        factory = (mock_vault_with_manifest / "_factory_manifest.md").read_text(encoding="utf-8")
        # SC_PIPELINE_STATE hat BL-ID → soll im BL-Manifest sein, nicht factory
        # (Solange sc_target_bl gesetzt ist)
        assert "SC_PIPELINE_STATE" not in factory, \
            "SC_PIPELINE_STATE mit BL-ID darf nicht im factory manifest sein"

    def test_migration_rollback_on_write_error(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        """Simuliert einen Fehler waehrend der Write-Phase und prueft Rollback."""
        original_content = (mock_vault_with_manifest / "_manifest.md").read_text(encoding="utf-8")

        call_count = [0]
        real_copy = shutil.copy2

        def failing_copy(src, dst):
            call_count[0] += 1
            if call_count[0] >= 2:
                raise OSError("Simulierter Disk-Fehler")
            real_copy(src, dst)

        with patch("migrate_manifest_split.shutil.copy2", side_effect=failing_copy):
            with pytest.raises(SystemExit) as exc_info:
                cmd_migrate(mock_vault_with_manifest, rollback_tag="fail-test", force=True)
            assert exc_info.value.code == 2

        # Nach Rollback: Original-Manifest unveraendert (Backup wurde erstellt)
        backup = mock_vault_with_manifest / "_manifest.backup-fail-test.md"
        if backup.exists():
            assert backup.read_text(encoding="utf-8") == original_content

    def test_migration_requires_rollback_tag_without_force(
        self, mock_vault_with_manifest: Path
    ) -> None:
        """Ohne --rollback-tag und ohne --force: Abbruch."""
        with pytest.raises(SystemExit) as exc_info:
            cmd_migrate(mock_vault_with_manifest, rollback_tag=None, force=False)
        assert exc_info.value.code == 1

    def test_migration_summary_json_structure(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        result = cmd_migrate(mock_vault_with_manifest, rollback_tag="json-test", force=True)
        assert "factory_blocks_count" in result
        assert "bl_manifests_written" in result
        assert "orphan_blocks" in result
        assert "total_lines_processed" in result
        assert result["mode"] == "migrate"


# ---------------------------------------------------------------------------
# Test 5: Rollback
# ---------------------------------------------------------------------------

class TestRollback:
    """test_rollback: Rollback stellt _manifest.md wieder her."""

    def test_rollback_restores_manifest(
        self, mock_vault_with_manifest: Path, capsys, sample_manifest_content: str
    ) -> None:
        # Erst migrieren (erstellt Backup)
        cmd_migrate(mock_vault_with_manifest, rollback_tag="restore-test", force=True)

        # Manifest veraendern (simuliert post-migration state)
        (mock_vault_with_manifest / "_manifest.md").write_text("MODIFIED CONTENT", encoding="utf-8")

        # Rollback
        cmd_rollback(mock_vault_with_manifest, rollback_tag="restore-test")

        # Manifest muss Original-Inhalt haben
        restored = (mock_vault_with_manifest / "_manifest.md").read_text(encoding="utf-8")
        assert restored == sample_manifest_content

    def test_rollback_missing_backup_exits_with_error(
        self, mock_vault_with_manifest: Path
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            cmd_rollback(mock_vault_with_manifest, rollback_tag="nonexistent-tag")
        assert exc_info.value.code == 1

    def test_rollback_summary_structure(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        cmd_migrate(mock_vault_with_manifest, rollback_tag="summary-test", force=True)
        result = cmd_rollback(mock_vault_with_manifest, rollback_tag="summary-test")
        assert result["mode"] == "rollback"
        assert "restored" in result
        assert "backup_used" in result

    def test_rollback_does_not_modify_backup(
        self, mock_vault_with_manifest: Path, capsys, sample_manifest_content: str
    ) -> None:
        cmd_migrate(mock_vault_with_manifest, rollback_tag="preserve-backup", force=True)
        backup_before = (mock_vault_with_manifest / "_manifest.backup-preserve-backup.md").read_text(encoding="utf-8")
        cmd_rollback(mock_vault_with_manifest, rollback_tag="preserve-backup")
        backup_after = (mock_vault_with_manifest / "_manifest.backup-preserve-backup.md").read_text(encoding="utf-8")
        assert backup_before == backup_after, "Backup-Datei darf durch Rollback nicht veraendert werden"


# ---------------------------------------------------------------------------
# Bonus: Verify-Subcommand
# ---------------------------------------------------------------------------

class TestVerify:
    """Zusaetzliche Tests fuer den verify-Subcommand."""

    def test_verify_detects_missing_factory_manifest(
        self, mock_vault: Path, capsys
    ) -> None:
        with pytest.raises(SystemExit) as exc_info:
            cmd_verify(mock_vault)
        assert exc_info.value.code == 3

    def test_verify_ok_after_migration(
        self, mock_vault_with_manifest: Path, capsys
    ) -> None:
        cmd_migrate(mock_vault_with_manifest, rollback_tag="verify-ok", force=True)
        result = cmd_verify(mock_vault_with_manifest)
        assert result["status"] == "OK"
        assert result["factory_manifest_exists"] is True

    def test_verify_detects_bl_block_in_factory(
        self, mock_vault: Path, capsys
    ) -> None:
        # Erstelle factory manifest mit BL-Block (Invariant-Verletzung)
        bad_content = "# Factory\n\n## SC_PIPELINE_STATE\nsc_status: SETUP\n"
        (mock_vault / "_factory_manifest.md").write_text(bad_content, encoding="utf-8")
        with pytest.raises(SystemExit) as exc_info:
            cmd_verify(mock_vault)
        assert exc_info.value.code == 3


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", __file__, "-v", "--tb=short"],
        cwd=str(Path(__file__).parent.parent.parent),  # repo root
    )
    sys.exit(result.returncode)
