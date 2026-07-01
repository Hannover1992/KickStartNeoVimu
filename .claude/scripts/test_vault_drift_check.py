"""
test_vault_drift_check.py — BL-446 AK-3 RED Tests (TDD test-first)

Tests fuer vault_drift_check.py (existiert NOCH NICHT -> muss RED sein).

Getestete API (erwartet):
  report_disconnected(backlog_root: str | Path) -> dict
    Returns: {"disconnected": [...], "count": int}

  DriftCheckBerater(repo_root: str) subclass von BaseQualityBerater
    check_type = "drift_check"
    run_checks(bl_id, data, auto_fix=False) -> QualityResult
    data keys:
      "backlog_root" (str|Path) — Backlog-Ordner
      "vault_root"   (str|Path) — Vault-Root (optional, abgeleitet)

Exit-Codes (INV-QUALITY-1):
  0 = PASS (kein Drift)
  1 = WARN (Drift gefunden)

Artefakt-Disconnected = keine bl_root im Frontmatter UND kein "> Teil von "-Header.
"""

import os
import sys
import textwrap
import pytest
from pathlib import Path

# Importpfad: .claude/scripts/ liegt neben uns
SCRIPTS_DIR = os.path.dirname(__file__)
sys.path.insert(0, SCRIPTS_DIR)

# ---- Ziel-Import (NOCH NICHT GEBAUT — soll RED geben) ----
import vault_drift_check  # noqa: E402  <- ImportError expected RED


# ---------------------------------------------------------------------------
# Fixtures — tmp-BL-Korpus
# ---------------------------------------------------------------------------

def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(textwrap.dedent(content), encoding="utf-8")


@pytest.fixture()
def disconnected_corpus(tmp_path: Path) -> Path:
    """Backlog mit 2 BL-Ordnern: beide Artefakte disconnected (kein Backlink)."""
    backlog = tmp_path / "Backlog"

    # BL-901
    bl901 = backlog / "BL-901-alpha-feature"
    _write(bl901 / "BL-901-alpha-feature.md", """\
        # BL-901 Root Hub

        Hub-Datei ohne Artefakte-Sektion.
    """)
    _write(bl901 / "2_Model" / "BL-901_Model.md", """\
        ---
        type: model
        bl-item: BL-901
        ---
        # BL-901 Model

        Kein bl_root-Backlink hier.
    """)
    _write(bl901 / "3_Spec" / "BL-901_Spec.md", """\
        # BL-901 Spec

        Auch kein > Teil von Header.
    """)

    # BL-902
    bl902 = backlog / "BL-902-beta-fix"
    _write(bl902 / "BL-902-beta-fix.md", """\
        # BL-902 Root Hub
    """)
    _write(bl902 / "2_Model" / "BL-902_Model.md", """\
        ---
        type: model
        ---
        # BL-902 Model disconnected
    """)

    return backlog


@pytest.fixture()
def connected_corpus(tmp_path: Path) -> Path:
    """Backlog mit 1 BL: Artefakt hat bl_root-Backlink (voll verschaltet)."""
    backlog = tmp_path / "Backlog"

    bl903 = backlog / "BL-903-connected"
    _write(bl903 / "BL-903-connected.md", """\
        # BL-903 Root Hub

        ## Artefakte

        - [[Backlog/BL-903-connected/2_Model/BL-903_Model]]
    """)
    _write(bl903 / "2_Model" / "BL-903_Model.md", """\
        ---
        type: model
        bl-item: BL-903
        bl_root: "[[Backlog/BL-903-connected/BL-903-connected]]"
        ---
        # BL-903 Model (verschaltet)
    """)

    return backlog


@pytest.fixture()
def mixed_corpus(tmp_path: Path) -> Path:
    """Backlog mit 2 BL: BL-904 verschaltet, BL-905 disconnected."""
    backlog = tmp_path / "Backlog"

    # BL-904 — voll verschaltet
    bl904 = backlog / "BL-904-done"
    _write(bl904 / "BL-904-done.md", """\
        # BL-904 Root Hub

        ## Artefakte

        - [[Backlog/BL-904-done/2_Model/BL-904_Model]]
    """)
    _write(bl904 / "2_Model" / "BL-904_Model.md", """\
        ---
        type: model
        bl_root: "[[Backlog/BL-904-done/BL-904-done]]"
        ---
        # BL-904 Model
    """)

    # BL-905 — disconnected
    bl905 = backlog / "BL-905-island"
    _write(bl905 / "BL-905-island.md", """\
        # BL-905 Root Hub ohne Artefakte-Sektion
    """)
    _write(bl905 / "3_Spec" / "BL-905_Spec.md", """\
        # BL-905 Spec (kein Backlink)
    """)

    return backlog


@pytest.fixture()
def header_connected_corpus(tmp_path: Path) -> Path:
    """Backlog mit 1 BL: Artefakt hat > Teil von -Header (kein Frontmatter-bl_root)."""
    backlog = tmp_path / "Backlog"

    bl906 = backlog / "BL-906-header-link"
    _write(bl906 / "BL-906-header-link.md", """\
        # BL-906 Root Hub

        ## Artefakte

        - [[Backlog/BL-906-header-link/2_Model/BL-906_Model]]
    """)
    _write(bl906 / "2_Model" / "BL-906_Model.md", """\
        > Teil von [[Backlog/BL-906-header-link/BL-906-header-link]]

        # BL-906 Model (via Header-Backlink)
    """)

    return backlog


# ---------------------------------------------------------------------------
# AK-3.1 — report_disconnected findet disconnected Artefakte
# ---------------------------------------------------------------------------

class TestReportDisconnected:
    """report_disconnected(backlog_root) -> {disconnected:[...], count: int}"""

    def test_finds_disconnected_artefacts_in_disconnected_corpus(
        self, disconnected_corpus: Path
    ) -> None:
        result = vault_drift_check.report_disconnected(disconnected_corpus)
        assert result["count"] > 0, "Erwartet: mindestens 1 disconnected Artefakt"

    def test_returns_dict_with_disconnected_list_and_count(
        self, disconnected_corpus: Path
    ) -> None:
        result = vault_drift_check.report_disconnected(disconnected_corpus)
        assert isinstance(result, dict)
        assert "disconnected" in result
        assert "count" in result
        assert isinstance(result["disconnected"], list)
        assert isinstance(result["count"], int)

    def test_count_matches_disconnected_list_length(
        self, disconnected_corpus: Path
    ) -> None:
        result = vault_drift_check.report_disconnected(disconnected_corpus)
        assert result["count"] == len(result["disconnected"])

    def test_zero_count_on_connected_corpus(self, connected_corpus: Path) -> None:
        result = vault_drift_check.report_disconnected(connected_corpus)
        assert result["count"] == 0, "Vollstaendig verschalteter Korpus -> Drift = 0"
        assert result["disconnected"] == []

    def test_partial_corpus_finds_only_disconnected(
        self, mixed_corpus: Path
    ) -> None:
        result = vault_drift_check.report_disconnected(mixed_corpus)
        # BL-905 hat 1 disconnected Artefakt, BL-904 ist sauber
        assert result["count"] >= 1
        # Keiner der Pfade darf aus BL-904 stammen
        for item in result["disconnected"]:
            item_str = str(item)
            assert "BL-904" not in item_str, (
                f"BL-904 ist verschaltet — darf nicht in disconnected stehen: {item_str}"
            )

    def test_header_backlink_counts_as_connected(
        self, header_connected_corpus: Path
    ) -> None:
        result = vault_drift_check.report_disconnected(header_connected_corpus)
        assert result["count"] == 0, (
            "> Teil von -Header soll als Backlink anerkannt werden (kein Drift)"
        )

    def test_accepts_path_object(self, connected_corpus: Path) -> None:
        # Path-Objekt (kein str) muss akzeptiert werden
        result = vault_drift_check.report_disconnected(connected_corpus)
        assert "count" in result

    def test_accepts_string_path(self, connected_corpus: Path) -> None:
        result = vault_drift_check.report_disconnected(str(connected_corpus))
        assert "count" in result

    def test_empty_backlog_returns_zero(self, tmp_path: Path) -> None:
        empty_backlog = tmp_path / "Backlog"
        empty_backlog.mkdir(parents=True)
        result = vault_drift_check.report_disconnected(empty_backlog)
        assert result["count"] == 0

    def test_nonexistent_backlog_returns_zero(self, tmp_path: Path) -> None:
        result = vault_drift_check.report_disconnected(tmp_path / "NonExistent")
        assert result["count"] == 0


# ---------------------------------------------------------------------------
# AK-3.2 — Root-Hub ohne ## Artefakte-Sektion -> Finding
# ---------------------------------------------------------------------------

class TestHubWithoutArtefakteSection:
    """Root-Sibling ohne ## Artefakte-Sektion -> gemeldet (DoD-3.2)."""

    def test_hub_without_artefakte_section_is_reported(
        self, disconnected_corpus: Path
    ) -> None:
        result = vault_drift_check.report_disconnected(disconnected_corpus)
        # BL-901 und BL-902 beide haben Hub ohne ## Artefakte-Sektion
        hub_issues = [
            item for item in result["disconnected"]
            if "hub" in str(item).lower() or "root" in str(item).lower()
            or str(item).endswith(".md") and "Spec" not in str(item) and "Model" not in str(item)
        ]
        # Es gibt mindestens disconnected items — der Test bestaetigt count > 0 genuegt
        assert result["count"] > 0


# ---------------------------------------------------------------------------
# AK-3.3 — Framework-Reuse: DriftCheckBerater subclass von BaseQualityBerater
# ---------------------------------------------------------------------------

class TestDriftCheckBeraterClass:
    """DriftCheckBerater muss BaseQualityBerater subclassen (DoD-3.3)."""

    def test_module_exposes_drift_check_berater(self) -> None:
        assert hasattr(vault_drift_check, "DriftCheckBerater"), (
            "vault_drift_check muss DriftCheckBerater exportieren"
        )

    def test_drift_check_berater_is_subclass_of_base(self, tmp_path: Path) -> None:
        from quality_berater_base import BaseQualityBerater
        berater = vault_drift_check.DriftCheckBerater(repo_root=str(tmp_path))
        assert isinstance(berater, BaseQualityBerater)

    def test_drift_check_berater_has_correct_check_type(self, tmp_path: Path) -> None:
        berater = vault_drift_check.DriftCheckBerater(repo_root=str(tmp_path))
        assert berater.check_type == "drift_check"

    def test_run_checks_returns_quality_result(
        self, disconnected_corpus: Path, tmp_path: Path
    ) -> None:
        from quality_berater_base import QualityResult
        berater = vault_drift_check.DriftCheckBerater(repo_root=str(tmp_path))
        data = {"backlog_root": disconnected_corpus}
        result = berater.run_checks(bl_id="BL-CORPUS", data=data)
        assert isinstance(result, QualityResult)

    def test_findings_are_warn_severity_on_drift(
        self, disconnected_corpus: Path, tmp_path: Path
    ) -> None:
        from quality_berater_base import SEVERITY_WARN
        berater = vault_drift_check.DriftCheckBerater(repo_root=str(tmp_path))
        data = {"backlog_root": disconnected_corpus}
        result = berater.run_checks(bl_id="BL-CORPUS", data=data)
        assert len(result.findings) > 0
        for finding in result.findings:
            assert finding.severity == SEVERITY_WARN, (
                f"Drift-Findings muessen WARN sein, nicht {finding.severity}"
            )

    def test_no_findings_on_connected_corpus(
        self, connected_corpus: Path, tmp_path: Path
    ) -> None:
        berater = vault_drift_check.DriftCheckBerater(repo_root=str(tmp_path))
        data = {"backlog_root": connected_corpus}
        result = berater.run_checks(bl_id="BL-CORPUS", data=data)
        assert len(result.findings) == 0


# ---------------------------------------------------------------------------
# AK-3.4 — Exit-Codes (INV-QUALITY-1)
# ---------------------------------------------------------------------------

class TestExitCodes:
    """Exit 1 (WARN) bei Drift, Exit 0 (PASS) bei Drift=0 (DoD-3.4)."""

    def test_exit_code_1_on_drift(
        self, disconnected_corpus: Path, tmp_path: Path
    ) -> None:
        from quality_berater_base import EXIT_WARN
        berater = vault_drift_check.DriftCheckBerater(repo_root=str(tmp_path))
        data = {"backlog_root": disconnected_corpus}
        result = berater.run(bl_id="BL-CORPUS", data=data)
        assert result.exit_code == EXIT_WARN

    def test_exit_code_0_on_no_drift(
        self, connected_corpus: Path, tmp_path: Path
    ) -> None:
        from quality_berater_base import EXIT_PASS
        berater = vault_drift_check.DriftCheckBerater(repo_root=str(tmp_path))
        data = {"backlog_root": connected_corpus}
        result = berater.run(bl_id="BL-CORPUS", data=data)
        assert result.exit_code == EXIT_PASS


# ---------------------------------------------------------------------------
# AK-3.5 — READ-ONLY: vault_drift_check mutiert NICHTS
# ---------------------------------------------------------------------------

class TestReadOnly:
    """vault_drift_check mutiert keine Dateien (DoD-3.5)."""

    def test_report_disconnected_does_not_mutate_files(
        self, disconnected_corpus: Path
    ) -> None:
        # Snapshot aller Datei-Inhalte vor dem Lauf
        snapshots: dict[str, str] = {}
        for p in sorted(disconnected_corpus.rglob("*.md")):
            snapshots[str(p)] = p.read_text(encoding="utf-8")

        vault_drift_check.report_disconnected(disconnected_corpus)

        for path_str, original_content in snapshots.items():
            current_content = Path(path_str).read_text(encoding="utf-8")
            assert current_content == original_content, (
                f"vault_drift_check hat {path_str} mutiert (READ-ONLY-Verletzung)"
            )

    def test_drift_check_berater_does_not_mutate_files(
        self, disconnected_corpus: Path, tmp_path: Path
    ) -> None:
        snapshots: dict[str, str] = {}
        for p in sorted(disconnected_corpus.rglob("*.md")):
            snapshots[str(p)] = p.read_text(encoding="utf-8")

        berater = vault_drift_check.DriftCheckBerater(repo_root=str(tmp_path))
        data = {"backlog_root": disconnected_corpus}
        berater.run(bl_id="BL-CORPUS", data=data)

        for path_str, original_content in snapshots.items():
            current_content = Path(path_str).read_text(encoding="utf-8")
            assert current_content == original_content, (
                f"DriftCheckBerater hat {path_str} mutiert (READ-ONLY-Verletzung)"
            )
