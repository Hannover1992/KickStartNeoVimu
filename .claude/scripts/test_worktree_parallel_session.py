#!/usr/bin/env python3
"""
test_worktree_parallel_session.py — Parallel-Session-Tests (BL-172 AK-5).

Simuliert 2 Worktrees die parallel in eigene _session_params_{ns}.md schreiben.
Assertion: keine Cross-Contamination, beide Sessions unabhaengig und konsistent.

Tests nutzen tmp_path Fixtures (kein Vault-Root-Zugriff noetig).
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

_SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(_SCRIPT_DIR))

from worktree_aware_params import (
    get_worktree_namespace,
    resolve_session_params,
    write_session_param,
    _extract_params_from_file,
)


# ── Helper ────────────────────────────────────────────────────────────────────

def _write_param_for_worktree(
    wt_id: str,
    key: str,
    value: str,
    vault_root: Path,
) -> Path:
    """Schreibt einen Param fuer einen spezifischen Worktree."""
    params_path, mode = write_session_param(
        key=key,
        value=value,
        owner="worker",
        worktree_id=wt_id,
        vault_root=vault_root,
    )
    return params_path


# ── Tests: Isolation ─────────────────────────────────────────────────────────

class TestParallelSessionIsolation:
    def test_two_worktrees_write_separate_files(self, tmp_path):
        """Zwei Worktrees schreiben in eigene Dateien — keine Datei-Kollision."""
        wt_a = "worktree_a"
        wt_b = "worktree_b"

        path_a = _write_param_for_worktree(wt_a, "hil", "phase", tmp_path)
        path_b = _write_param_for_worktree(wt_b, "hil", "off", tmp_path)

        assert path_a != path_b
        assert path_a.name == f"_session_params_{wt_a}.md"
        assert path_b.name == f"_session_params_{wt_b}.md"
        assert path_a.exists()
        assert path_b.exists()

    def test_no_cross_contamination(self, tmp_path):
        """Wert aus Worktree-A darf nicht in Worktree-B-Datei erscheinen."""
        wt_a = "session_wt_a"
        wt_b = "session_wt_b"

        _write_param_for_worktree(wt_a, "difficulty", "hard", tmp_path)
        _write_param_for_worktree(wt_b, "difficulty", "easy", tmp_path)

        params_a = _extract_params_from_file(tmp_path / f"_session_params_{wt_a}.md")
        params_b = _extract_params_from_file(tmp_path / f"_session_params_{wt_b}.md")

        assert params_a.get("difficulty") == "hard"
        assert params_b.get("difficulty") == "easy"

    def test_worktree_a_update_does_not_affect_worktree_b(self, tmp_path):
        """Update in Worktree-A veraendert Worktree-B-Datei NICHT."""
        wt_a = "alpha"
        wt_b = "beta"

        _write_param_for_worktree(wt_a, "hil", "phase", tmp_path)
        _write_param_for_worktree(wt_b, "hil", "off", tmp_path)

        # Update in wt_a
        _write_param_for_worktree(wt_a, "hil", "full", tmp_path)

        params_b = _extract_params_from_file(tmp_path / f"_session_params_{wt_b}.md")
        assert params_b.get("hil") == "off", "wt_b darf nicht durch wt_a-Update veraendert werden"

    def test_parallel_writes_thread_safe(self, tmp_path):
        """Zwei Threads schreiben gleichzeitig in ihre Namespaces — kein Data-Race."""
        errors: list[str] = []
        written: list[tuple[str, str]] = []

        def write_wt(wt_id: str, value: str) -> None:
            try:
                for i in range(5):
                    _write_param_for_worktree(wt_id, "counter", str(i), tmp_path)
                params = _extract_params_from_file(
                    tmp_path / f"_session_params_{wt_id}.md"
                )
                written.append((wt_id, params.get("counter", "MISSING")))
            except Exception as e:
                errors.append(f"{wt_id}: {e}")

        t1 = threading.Thread(target=write_wt, args=("thread_wt_a", "valueA"))
        t2 = threading.Thread(target=write_wt, args=("thread_wt_b", "valueB"))
        t1.start()
        t2.start()
        t1.join(timeout=10)
        t2.join(timeout=10)

        assert not errors, f"Thread-Fehler: {errors}"
        # Beide Worktrees muessen final counter=4 haben (letzter Write)
        written_map = dict(written)
        assert written_map.get("thread_wt_a") == "4"
        assert written_map.get("thread_wt_b") == "4"

    def test_resolve_session_params_returns_correct_path(self, tmp_path):
        """resolve_session_params liefert worktree-spezifischen Pfad wenn ns gegeben."""
        path, mode = resolve_session_params(worktree_id="my_worktree", vault_root=tmp_path)
        assert mode == "multi"
        assert path.name == "_session_params_my_worktree.md"
        assert path.parent == tmp_path
