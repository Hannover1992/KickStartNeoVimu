#!/usr/bin/env python3
"""
test_migrate_to_worktree_aware.py — Tests fuer migrate_to_worktree_aware.py (BL-172 AK-6).
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(_SCRIPT_DIR))

from migrate_to_worktree_aware import migrate, rollback, status


def _mock_ns(ns):
    return patch("migrate_to_worktree_aware._get_namespace", return_value=ns)


class TestMigrate:
    def test_migrate_creates_worktree_file(self, tmp_path):
        source = tmp_path / "_session_params.md"
        source.write_text("**hil:** phase  _owner: user\n**difficulty:** medium\n", encoding="utf-8")

        with _mock_ns("feature_bdf"):
            result = migrate(vault_root=tmp_path, rollback_tag="2026-05-19")

        assert result["status"] == "DONE"
        target = tmp_path / "_session_params_feature_bdf.md"
        assert target.exists()
        content = target.read_text(encoding="utf-8")
        assert "hil" in content
        assert "feature_bdf" in content

    def test_migrate_creates_backup(self, tmp_path):
        source = tmp_path / "_session_params.md"
        source.write_text("**hil:** phase\n", encoding="utf-8")

        with _mock_ns("wt_test"):
            result = migrate(vault_root=tmp_path, rollback_tag="2026-05-19")

        backup = tmp_path / "_session_params.md.backup_2026-05-19"
        assert backup.exists()
        assert result["backed_up"] == str(backup)

    def test_migrate_dry_run_no_files_written(self, tmp_path):
        source = tmp_path / "_session_params.md"
        source.write_text("**hil:** off\n", encoding="utf-8")

        with _mock_ns("wt_dry"):
            result = migrate(vault_root=tmp_path, dry_run=True, rollback_tag="2026-05-19")

        assert result["status"] == "DRY_RUN"
        target = tmp_path / "_session_params_wt_dry.md"
        assert not target.exists()
        backup = tmp_path / "_session_params.md.backup_2026-05-19"
        assert not backup.exists()

    def test_migrate_skip_if_no_source(self, tmp_path):
        with _mock_ns("wt_x"):
            result = migrate(vault_root=tmp_path, rollback_tag="2026-05-19")
        assert result["status"] == "SKIP"

    def test_migrate_skip_if_no_namespace(self, tmp_path):
        source = tmp_path / "_session_params.md"
        source.write_text("**hil:** phase\n", encoding="utf-8")

        with _mock_ns(None):
            result = migrate(vault_root=tmp_path, rollback_tag="2026-05-19")

        assert result["status"] == "SKIP"


class TestRollback:
    def test_rollback_deletes_worktree_file_and_restores_backup(self, tmp_path):
        worktree_file = tmp_path / "_session_params_wt_r.md"
        worktree_file.write_text("migrated content\n", encoding="utf-8")
        backup = tmp_path / "_session_params.md.backup_2026-05-18"
        backup.write_text("original content\n", encoding="utf-8")

        with _mock_ns("wt_r"):
            result = rollback(vault_root=tmp_path, rollback_tag="2026-05-18")

        assert result["status"] == "DONE"
        assert not worktree_file.exists()
        original = tmp_path / "_session_params.md"
        assert original.exists()
        assert "original content" in original.read_text(encoding="utf-8")

    def test_rollback_dry_run(self, tmp_path):
        worktree_file = tmp_path / "_session_params_wt_d.md"
        worktree_file.write_text("content\n", encoding="utf-8")
        backup = tmp_path / "_session_params.md.backup_2026-05-18"
        backup.write_text("backup\n", encoding="utf-8")

        with _mock_ns("wt_d"):
            result = rollback(vault_root=tmp_path, rollback_tag="2026-05-18", dry_run=True)

        assert result["status"] == "DRY_RUN"
        assert worktree_file.exists()  # nicht geloescht


class TestStatus:
    def test_status_detects_worktree_files(self, tmp_path):
        (tmp_path / "_session_params.md").write_text("base\n", encoding="utf-8")
        (tmp_path / "_session_params_wt_a.md").write_text("a\n", encoding="utf-8")
        (tmp_path / "_session_params_wt_b.md").write_text("b\n", encoding="utf-8")

        with _mock_ns("wt_a"):
            result = status(tmp_path)

        assert result["base_file_exists"] is True
        assert result["worktree_file_count"] == 2
        namespaces = [f["namespace"] for f in result["worktree_files"]]
        assert "wt_a" in namespaces
        assert "wt_b" in namespaces
