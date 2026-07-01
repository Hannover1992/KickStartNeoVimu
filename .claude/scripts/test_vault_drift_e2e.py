"""
test_vault_drift_e2e.py — BL-446 AK-4 E2E RED Tests (TDD test-first)

End-to-End Beweis: disconnected Korpus -> migrate_all -> drift_check meldet 0.

Teststrategie (DoD-4.1..4.3):
  1. Erstelle tmp-Korpus mit disconnected Artefakten.
  2. Laufe vault_drift_check.report_disconnected -> count > 0 (Pre-Migration, Exit 1).
  3. Laufe vault_bl_edges.migrate_all auf demselben Korpus.
  4. Laufe vault_drift_check.report_disconnected nochmal -> count = 0 (Post-Migration, Exit 0).

HINWEIS zum RED-Profil:
  - vault_bl_edges (migrate_all, vault_edge_link) ist GRUEN (bereits gebaut).
  - vault_drift_check ist NOCH NICHT gebaut -> AK-4-Tests sind RED (ImportError).
"""

import os
import sys
import textwrap
import pytest
from pathlib import Path

SCRIPTS_DIR = os.path.dirname(__file__)
sys.path.insert(0, SCRIPTS_DIR)

# vault_bl_edges ist bereits gebaut -> gruen
from vault_bl_edges import migrate_all, vault_edge_link  # noqa: E402

# vault_drift_check ist NOCH NICHT gebaut -> RED (ImportError expected)
import vault_drift_check  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


# ---------------------------------------------------------------------------
# E2E Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def e2e_disconnected_corpus(tmp_path: Path) -> tuple[Path, Path]:
    """
    Liefert (vault_root, backlog_root) mit 2 vollstaendig disconnected BL-Ordnern.
    Kein _manifest.md -> skip_active=True in migrate_all ueberspringt sie NICHT.
    """
    vault_root = tmp_path / "Vault"
    backlog = vault_root / "Backlog"

    # BL-910 — 2 Artefakte, keine Edges
    bl910 = backlog / "BL-910-e2e-alpha"
    _write(bl910 / "BL-910-e2e-alpha.md", "# BL-910 Root Hub\n")
    _write(bl910 / "2_Model" / "BL-910_Model.md", textwrap.dedent("""\
        ---
        type: model
        bl-item: BL-910
        ---
        # BL-910 Model (disconnected)
    """))
    _write(bl910 / "3_Spec" / "BL-910_Spec.md", textwrap.dedent("""\
        # BL-910 Spec (disconnected, kein Header)
    """))

    # BL-911 — 1 Artefakt, keine Edges
    bl911 = backlog / "BL-911-e2e-beta"
    _write(bl911 / "BL-911-e2e-beta.md", "# BL-911 Root Hub\n")
    _write(bl911 / "2_Model" / "BL-911_Model.md", textwrap.dedent("""\
        ---
        type: model
        bl-item: BL-911
        ---
        # BL-911 Model (disconnected)
    """))

    return vault_root, backlog


@pytest.fixture()
def e2e_single_bl_corpus(tmp_path: Path) -> tuple[Path, Path]:
    """Einzelner BL-Ordner, 1 Artefakt disconnected."""
    vault_root = tmp_path / "Vault"
    backlog = vault_root / "Backlog"

    bl920 = backlog / "BL-920-single"
    _write(bl920 / "BL-920-single.md", "# BL-920 Root Hub\n")
    _write(bl920 / "2_Model" / "BL-920_Model.md", textwrap.dedent("""\
        ---
        type: model
        ---
        # BL-920 Model (disconnected)
    """))

    return vault_root, backlog


# ---------------------------------------------------------------------------
# AK-4 Core E2E Tests
# ---------------------------------------------------------------------------

class TestDriftZeroAfterMigration:
    """DoD-4.1..4.2: Pre-Migration drift>0, Post-Migration drift=0."""

    def test_pre_migration_drift_is_positive(
        self, e2e_disconnected_corpus: tuple[Path, Path]
    ) -> None:
        """DoD-4.1: Vor migrate_all meldet report_disconnected Drift > 0."""
        _vault_root, backlog = e2e_disconnected_corpus
        result = vault_drift_check.report_disconnected(backlog)
        assert result["count"] > 0, (
            f"Erwartet Drift > 0 vor Migration, bekam: {result}"
        )

    def test_post_migration_drift_is_zero(
        self, e2e_disconnected_corpus: tuple[Path, Path]
    ) -> None:
        """DoD-4.2: Nach migrate_all meldet report_disconnected Drift = 0."""
        vault_root, backlog = e2e_disconnected_corpus
        # Migration ausfuehren
        edges_set = migrate_all(backlog, skip_active=False)
        assert edges_set > 0, f"migrate_all muss Edges setzen, setzte: {edges_set}"
        # Drift-Check nach Migration
        result = vault_drift_check.report_disconnected(backlog)
        assert result["count"] == 0, (
            f"Erwartet Drift = 0 nach Migration, bekam: {result}"
        )
        assert result["disconnected"] == []

    def test_full_cycle_single_bl(
        self, e2e_single_bl_corpus: tuple[Path, Path]
    ) -> None:
        """Vollzyklus auf einem einzelnen BL: disconnected -> migrate -> Drift=0."""
        vault_root, backlog = e2e_single_bl_corpus
        # Pre
        pre = vault_drift_check.report_disconnected(backlog)
        assert pre["count"] > 0, "Einzelner disconnected BL muss Drift > 0 melden"
        # Migrate
        migrate_all(backlog, skip_active=False)
        # Post
        post = vault_drift_check.report_disconnected(backlog)
        assert post["count"] == 0, "Nach Migration muss Drift = 0 sein"

    def test_migrate_then_drift_check_exit_code_is_pass(
        self, e2e_disconnected_corpus: tuple[Path, Path], tmp_path: Path
    ) -> None:
        """DoD-4.2 via DriftCheckBerater: exit_code = 0 (PASS) nach Migration."""
        from quality_berater_base import EXIT_PASS
        vault_root, backlog = e2e_disconnected_corpus
        migrate_all(backlog, skip_active=False)
        berater = vault_drift_check.DriftCheckBerater(repo_root=str(tmp_path))
        data = {"backlog_root": backlog}
        result = berater.run(bl_id="BL-E2E", data=data)
        assert result.exit_code == EXIT_PASS, (
            f"Erwartet EXIT_PASS nach Migration, bekam exit_code={result.exit_code}, "
            f"findings={result.findings}"
        )

    def test_idempotent_second_migration_still_drift_zero(
        self, e2e_disconnected_corpus: tuple[Path, Path]
    ) -> None:
        """Zweiter migrate_all-Lauf + Drift-Check bleibt 0 (Idempotenz)."""
        vault_root, backlog = e2e_disconnected_corpus
        migrate_all(backlog, skip_active=False)
        migrate_all(backlog, skip_active=False)  # zweiter Lauf
        result = vault_drift_check.report_disconnected(backlog)
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# AK-4 via vault_edge_link direkt (Single-Edge E2E)
# ---------------------------------------------------------------------------

class TestSingleEdgeCycleE2E:
    """vault_edge_link (Einzel-Edge) -> Drift-Check erkennt korrekt."""

    def test_single_edge_heals_single_artefact(
        self, tmp_path: Path
    ) -> None:
        """Nach vault_edge_link auf 1 Artefakt -> report_disconnected count=0."""
        vault_root = tmp_path / "Vault"
        backlog = vault_root / "Backlog"

        bl930 = backlog / "BL-930-edge-test"
        artefact = bl930 / "2_Model" / "BL-930_Model.md"
        _write(bl930 / "BL-930-edge-test.md", "# BL-930 Hub\n")
        _write(artefact, textwrap.dedent("""\
            ---
            type: model
            ---
            # BL-930 Model disconnected
        """))

        # Pre: 1 disconnected
        pre = vault_drift_check.report_disconnected(backlog)
        assert pre["count"] > 0

        # Einzel-Edge setzen
        vault_edge_link("BL-930", artefact, vault_root=vault_root)

        # Post: 0 disconnected
        post = vault_drift_check.report_disconnected(backlog)
        assert post["count"] == 0, (
            f"Nach Einzel-Edge muss Drift = 0, bekam: {post}"
        )

    def test_partial_migration_leaves_remaining_drift(
        self, e2e_disconnected_corpus: tuple[Path, Path]
    ) -> None:
        """Wenn nur 1 von 3 Artefakten migriert wird, bleibt Drift > 0."""
        vault_root, backlog = e2e_disconnected_corpus

        # Nur ein einziges Artefakt manuell verschalten
        bl910_model = backlog / "BL-910-e2e-alpha" / "2_Model" / "BL-910_Model.md"
        vault_edge_link("BL-910", bl910_model, vault_root=vault_root)

        # Noch 2 Artefakte disconnected (BL-910 Spec + BL-911 Model)
        result = vault_drift_check.report_disconnected(backlog)
        assert result["count"] > 0, (
            "Partielle Migration: restliche disconnected Artefakte muessen gemeldet werden"
        )


# ---------------------------------------------------------------------------
# DoD-4.3 Reproduzierbarkeit — Corpus-Reset zwischen Laeufen
# ---------------------------------------------------------------------------

class TestReproducibility:
    """DoD-4.3: Beweis ist reproduzierbar (tmp-Fixture, kein echter Vault)."""

    def test_two_independent_corpus_instances_both_heal(
        self, tmp_path: Path
    ) -> None:
        """Zwei unabhaengige tmp-Korpora heilen unabhaengig voneinander."""
        def _make_corpus(base: Path) -> Path:
            backlog = base / "Backlog"
            bl = backlog / "BL-940-repro"
            _write(bl / "BL-940-repro.md", "# BL-940\n")
            _write(bl / "2_Model" / "BL-940_Model.md", textwrap.dedent("""\
                ---
                type: model
                ---
                # Disconnected
            """))
            return backlog

        corpus_a = _make_corpus(tmp_path / "corpusA")
        corpus_b = _make_corpus(tmp_path / "corpusB")

        # Beide vor Migration disconnected
        assert vault_drift_check.report_disconnected(corpus_a)["count"] > 0
        assert vault_drift_check.report_disconnected(corpus_b)["count"] > 0

        # Nur A migrieren
        migrate_all(corpus_a, skip_active=False)

        # A = 0, B immer noch > 0 (keine Kreuz-Kontamination)
        assert vault_drift_check.report_disconnected(corpus_a)["count"] == 0
        assert vault_drift_check.report_disconnected(corpus_b)["count"] > 0
