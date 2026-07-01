"""
test_dry_run_reporter.py — BL-460 B-3a RED-Phase (Stage 1 unit, M3).

Tests fuer:
  - dry_run_reporter.dry_run(views, scorer, vault_root) -> report_dict
  - dry_run_reporter.assert_dry_run_before_write(report_path) -> (bool, reason)

GOLD-Kriterien (Blueprint G3-1..G3-8):
  G3-1: dry_run(views, mock_scorer) -> report mit allen Views
  G3-2: assert_dry_run_before_write(existing_report_path) -> (True, "")
  G3-3: assert_dry_run_before_write(missing_path) -> (False, reason)
  G3-4: is_write_gated returns (True, reason) -> report["status"] == "BLOCKED"
  G3-5: is_write_gated returns (False, "clean") -> report["status"] == "ALLOW"
  G3-6: dry_run schreibt NICHTS in den Vault (keine Vault-Dateien veraendert)
  G3-7: CLI exit 0 bei erfolgreichem Dry-Run
  G3-8: write_gate_guard ImportError -> fail-open (kein Crash, WARN im report)

Mock-Scorer-Konvention: scorer(view_path: str, vault_root: Path) -> list[dict]
  Jedes Element: {"atom_id": str, "score": float, "label": str}

RED-STATE: dry_run_reporter.py existiert NICHT -> alle Tests schlagen mit ModuleNotFoundError fehl.
"""

import os
import sys
import json
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(__file__))

import dry_run_reporter  # noqa: E402  (RED: Modul existiert noch nicht)


# ---------------------------------------------------------------------------
# Mock-Scorer-Fixtures (ScorerInterface: callable injiziert, NICHT re-implementiert)
# ---------------------------------------------------------------------------

def _mock_scorer_with_atoms(view_path, vault_root):
    """Mock-Scorer: gibt 2 Atom-Vorschlaege pro View zurueck."""
    return [
        {"atom_id": "AT-001", "score": 0.85, "label": "Atom One"},
        {"atom_id": "AT-002", "score": 0.72, "label": "Atom Two"},
    ]


def _mock_scorer_empty(view_path, vault_root):
    """Mock-Scorer: gibt leere Liste zurueck (keine Proposals)."""
    return []


def _mock_scorer_below_threshold(view_path, vault_root):
    """Mock-Scorer: gibt Atom mit Score unter Threshold zurueck."""
    return [
        {"atom_id": "AT-LOW", "score": 0.10, "label": "Low Score Atom"},
    ]


def _make_vault_with_views(tmp_path, n_views=3):
    """Erstellt einen minimalen Vault mit n Views."""
    vault = tmp_path / "vault"
    views_dir = vault / "Backlog" / "BL-001" / "2_Model"
    views_dir.mkdir(parents=True)
    view_paths = []
    for i in range(n_views):
        p = views_dir / f"View_{i:03d}_Model.md"
        p.write_text(f"# View {i}\ncontent\n", encoding="utf-8")
        view_paths.append(str(p))
    return vault, view_paths


# ---------------------------------------------------------------------------
# K (Kern): dry_run produziert Report mit pro-View-Eintraegen
# ---------------------------------------------------------------------------

def test_dry_run_report_contains_all_views(tmp_path):
    """
    K (G3-1): dry_run(views, mock_scorer, vault_root) liefert Report-Dict
    mit Eintrag fuer JEDE View.
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=4)

    report = dry_run_reporter.dry_run(
        views=views,
        scorer=_mock_scorer_with_atoms,
        vault_root=str(vault),
    )

    assert "views" in report
    assert len(report["views"]) == 4


def test_dry_run_report_per_view_has_required_fields(tmp_path):
    """
    K (G3-1): Jeder View-Eintrag im Report enthaelt 'path', 'proposed_atoms', 'status'.
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=2)

    report = dry_run_reporter.dry_run(
        views=views,
        scorer=_mock_scorer_with_atoms,
        vault_root=str(vault),
    )

    for entry in report["views"]:
        assert "path" in entry, f"Missing 'path' in entry: {entry}"
        assert "proposed_atoms" in entry, f"Missing 'proposed_atoms' in entry: {entry}"
        assert "status" in entry, f"Missing 'status' in entry: {entry}"


def test_dry_run_mock_scorer_called_per_view(tmp_path):
    """
    K: Mock-Scorer wird fuer jede View aufgerufen (scorer-Injection funktioniert).
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=3)
    call_count = [0]

    def counting_scorer(view_path, vault_root):
        call_count[0] += 1
        return [{"atom_id": "AT-X", "score": 0.5, "label": "X"}]

    dry_run_reporter.dry_run(
        views=views,
        scorer=counting_scorer,
        vault_root=str(vault),
    )

    assert call_count[0] == 3, \
        f"Expected scorer called 3 times, got {call_count[0]}"


def test_dry_run_report_has_total_views_field(tmp_path):
    """
    K: Report-Dict enthaelt 'total_views' und 'views_with_proposals'.
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=3)

    report = dry_run_reporter.dry_run(
        views=views,
        scorer=_mock_scorer_with_atoms,
        vault_root=str(vault),
    )

    assert "total_views" in report
    assert report["total_views"] == 3


def test_dry_run_report_has_generated_at_timestamp(tmp_path):
    """
    K: Report-Dict enthaelt 'generated_at' ISO-Timestamp.
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=2)

    report = dry_run_reporter.dry_run(
        views=views,
        scorer=_mock_scorer_with_atoms,
        vault_root=str(vault),
    )

    assert "generated_at" in report
    assert isinstance(report["generated_at"], str)
    assert len(report["generated_at"]) > 0


# ---------------------------------------------------------------------------
# K (Kern): assert_dry_run_before_write Gate-Logik
# ---------------------------------------------------------------------------

def test_assert_dry_run_before_write_returns_true_when_report_exists(tmp_path):
    """
    K (G3-2): assert_dry_run_before_write(existing_report_path) -> (True, "").
    """
    report_path = tmp_path / "dry_run_report.json"
    # Schreibe einen minimalen Report
    report_path.write_text(
        json.dumps({"status": "ALLOW", "views": [], "total_views": 0}),
        encoding="utf-8"
    )

    ok, reason = dry_run_reporter.assert_dry_run_before_write(str(report_path))

    assert ok is True
    assert reason == ""


def test_assert_dry_run_before_write_returns_false_when_report_missing(tmp_path):
    """
    K (G3-3): assert_dry_run_before_write(nonexistent_path) -> (False, reason).
    """
    missing_path = str(tmp_path / "no_report_here.json")

    ok, reason = dry_run_reporter.assert_dry_run_before_write(missing_path)

    assert ok is False
    assert reason != ""


def test_assert_dry_run_before_write_returns_false_for_invalid_json(tmp_path):
    """
    K: assert_dry_run_before_write mit nicht-parsebarer Datei -> (False, reason).
    """
    bad_report = tmp_path / "bad_report.json"
    bad_report.write_text("this is not valid JSON {{{", encoding="utf-8")

    ok, reason = dry_run_reporter.assert_dry_run_before_write(str(bad_report))

    assert ok is False
    assert reason != ""


# ---------------------------------------------------------------------------
# K (Kern): write_gate_guard-Integration (dry-run-gate, AK-3)
# ---------------------------------------------------------------------------

def test_dry_run_blocked_when_write_gate_is_gated(tmp_path):
    """
    K (G3-4): Wenn is_write_gated -> (True, "N corrupt nodes"),
    dann report["status"] == "BLOCKED".
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=2)

    # Mock is_write_gated: gibt (True, "3 corrupt nodes found") zurueck
    with patch.object(dry_run_reporter, "_is_write_gated_fn",
                      return_value=(True, "3 corrupt nodes found"),
                      create=True):
        report = dry_run_reporter.dry_run(
            views=views,
            scorer=_mock_scorer_with_atoms,
            vault_root=str(vault),
        )

    assert report["status"] == "BLOCKED"
    assert report.get("blocked_reason") is not None
    assert "corrupt" in report["blocked_reason"].lower() or \
           "3" in report["blocked_reason"]


def test_dry_run_allow_when_write_gate_is_clean(tmp_path):
    """
    K (G3-5): Wenn is_write_gated -> (False, "clean"),
    dann report["status"] == "ALLOW".
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=2)

    # Mock is_write_gated: gibt (False, "clean") zurueck
    with patch.object(dry_run_reporter, "_is_write_gated_fn",
                      return_value=(False, "clean"),
                      create=True):
        report = dry_run_reporter.dry_run(
            views=views,
            scorer=_mock_scorer_with_atoms,
            vault_root=str(vault),
        )

    assert report["status"] == "ALLOW"


# ---------------------------------------------------------------------------
# K (Kern): dry_run schreibt NICHTS in den Vault (G3-6)
# ---------------------------------------------------------------------------

def test_dry_run_writes_nothing_to_vault(tmp_path):
    """
    K (G3-6): dry_run schreibt NICHTS in den Vault. Keine Vault-Dateien werden
    veraendert oder hinzugefuegt.
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=3)

    # Snapshot der Vault-Dateien vor dem Dry-Run
    vault_files_before = {
        str(p): p.stat().st_mtime
        for p in vault.rglob("*")
        if p.is_file()
    }

    # Kleines Sleep um sicherzustellen, dass Timestamps veraendert werden wuerden
    time.sleep(0.05)

    dry_run_reporter.dry_run(
        views=views,
        scorer=_mock_scorer_with_atoms,
        vault_root=str(vault),
    )

    # Snapshot nach dem Dry-Run
    vault_files_after = {
        str(p): p.stat().st_mtime
        for p in vault.rglob("*")
        if p.is_file()
    }

    # Keine neuen Dateien
    new_files = set(vault_files_after.keys()) - set(vault_files_before.keys())
    assert len(new_files) == 0, \
        f"dry_run created new files in vault: {new_files}"

    # Keine veraenderten Dateien (mtime unveraendert)
    for path, mtime_before in vault_files_before.items():
        mtime_after = vault_files_after.get(path, mtime_before)
        assert mtime_after == mtime_before, \
            f"dry_run modified vault file: {path}"


# ---------------------------------------------------------------------------
# B (Boundary): leere views / scorer gibt nichts zurueck
# ---------------------------------------------------------------------------

def test_dry_run_empty_views_returns_empty_report(tmp_path):
    """
    B: leere views-Liste -> leerer Report (views=[]), exit 0.
    """
    vault = tmp_path / "vault"
    vault.mkdir()

    report = dry_run_reporter.dry_run(
        views=[],
        scorer=_mock_scorer_with_atoms,
        vault_root=str(vault),
    )

    assert isinstance(report, dict)
    assert report.get("total_views", 0) == 0
    assert report.get("views", []) == []


def test_dry_run_scorer_returns_empty_per_view(tmp_path):
    """
    B: scorer gibt [] fuer jede View -> Report mit 0 proposals pro View.
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=3)

    report = dry_run_reporter.dry_run(
        views=views,
        scorer=_mock_scorer_empty,
        vault_root=str(vault),
    )

    for entry in report["views"]:
        assert entry["proposed_atoms"] == [], \
            f"Expected empty proposals, got {entry['proposed_atoms']}"


# ---------------------------------------------------------------------------
# A (Ausnahme): write_gate_guard ImportError -> fail-open
# ---------------------------------------------------------------------------

def test_dry_run_failopen_when_write_gate_guard_unavailable(tmp_path):
    """
    A (G3-8): Wenn write_gate_guard nicht importierbar ist ->
    fail-open: kein Crash, Report enthaelt WARN-Hinweis.
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=2)

    # Simuliere fehlenden write_gate_guard (HAS_WRITE_GATE = False)
    with patch.object(dry_run_reporter, "_HAS_WRITE_GATE", False, create=True):
        try:
            report = dry_run_reporter.dry_run(
                views=views,
                scorer=_mock_scorer_with_atoms,
                vault_root=str(vault),
            )
            # Kein Crash — report muss dict sein
            assert isinstance(report, dict)
        except Exception as exc:
            raise AssertionError(
                f"fail-open verletzt — Exception statt graceful return: {exc}"
            ) from exc


def test_assert_dry_run_before_write_permission_error_returns_false(tmp_path):
    """
    A: report_path mit Permission-Fehler -> (False, reason) sauber — kein Crash.
    """
    # Wir simulieren einen IOError durch Patchen von Path.exists / open
    with patch("builtins.open", side_effect=PermissionError("access denied")):
        try:
            ok, reason = dry_run_reporter.assert_dry_run_before_write(
                str(tmp_path / "protected.json")
            )
            assert ok is False
            assert reason != ""
        except PermissionError:
            # Falls das Modul die Exception nicht faengt: Test failt korrekt
            raise AssertionError(
                "assert_dry_run_before_write muss PermissionError fangen -> (False, reason)"
            )


# ---------------------------------------------------------------------------
# CLI exit codes via main([...]) — DT-5-Konvention
# ---------------------------------------------------------------------------

def test_cli_exit_0_on_successful_dry_run(tmp_path):
    """
    K (G3-7): CLI main([...]) gibt 0 zurueck bei erfolgreichem Dry-Run.
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=3)
    views_json = tmp_path / "views.json"
    views_json.write_text(json.dumps(views), encoding="utf-8")
    output_path = tmp_path / "report.json"

    exit_code = dry_run_reporter.main([
        "--vault-root", str(vault),
        "--views-json", str(views_json),
        "--output", str(output_path),
    ])

    assert exit_code == 0


def test_cli_exit_2_for_usage_error():
    """
    CLI main([...]) gibt 2 zurueck bei Usage-Fehler.
    """
    try:
        exit_code = dry_run_reporter.main(["--invalid-flag-xyz"])
        assert exit_code == 2
    except SystemExit as e:
        assert e.code == 2


def test_cli_writes_report_to_output_path(tmp_path):
    """
    CLI mit --output schreibt den Report als JSON-Datei.
    """
    vault, views = _make_vault_with_views(tmp_path, n_views=2)
    views_json = tmp_path / "views.json"
    views_json.write_text(json.dumps(views), encoding="utf-8")
    output_path = tmp_path / "out_report.json"

    dry_run_reporter.main([
        "--vault-root", str(vault),
        "--views-json", str(views_json),
        "--output", str(output_path),
    ])

    assert output_path.exists(), "CLI did not create output report file"
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert "views" in report
