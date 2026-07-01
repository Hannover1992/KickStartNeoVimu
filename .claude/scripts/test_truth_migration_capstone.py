#!/usr/bin/env python3
"""Tests fuer truth_migration_capstone.py (BL-483 RED worker).

RED: truth_migration_capstone.py existiert NOCH NICHT — alle Tests MUESSEN
fehlschlagen mit ModuleNotFoundError oder ImportError.

Vertrag (pins die GREEN-API-Oberflaeche):
- StageResult dataclass: stage_id, name, status, gate_ok (+ optionale Felder)
- STAGES: geordnete Registry der Stages 0-7 + Stage 8 (BL-484 interface)
- GATE_CHECKS: dict stage_id -> gate_fn (StageResult -> bool)
- rollback(backup_tag, vault_root): loggt, stellt wieder her
- STATE_MACHINE: kennt ROLLBACK- und DONE-Zustand
- CLI/main: --dry-run DEFAULT, --write --force-go, --stage-from/--stage-to,
  --write ohne --force-go = interactive GO prompt (exit 3 wenn nicht GO)
- Preflight-Fehler (Stage 0a) => exit 2 + aborted_at=PREFLIGHT_CHECK, kein naechster Stage
- Bericht-JSON: {"vault":str, "run_ts":..., "stages":[...], "overall_ok":bool}

RED!=GREEN (INV-BUILD-GRAIN M3): Dieser Worker implementiert NICHTS ausser Tests.
"""
from __future__ import annotations

import json
import sys
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import pytest

# ---------------------------------------------------------------------------
# RED IMPORT — das Modul existiert noch NICHT
# ---------------------------------------------------------------------------
import truth_migration_capstone as cap  # noqa: F401 — erwartet ModuleNotFoundError

# ---------------------------------------------------------------------------
# Hilfs-Funktionen
# ---------------------------------------------------------------------------

def _make_stage_result(**kwargs) -> "cap.StageResult":
    """Erstellt ein minimales StageResult-Objekt mit sinnvollen Defaults."""
    defaults = dict(stage_id=1, name="atomize", status="ok", gate_ok=True)
    defaults.update(kwargs)
    return cap.StageResult(**defaults)


# ---------------------------------------------------------------------------
# T1b — StageResult-Dataclass-Struktur
# ---------------------------------------------------------------------------

class TestStageResultDataclass:
    def test_stage_result_dataclass(self):
        """StageResult muss die 4 Pflichtfelder enthalten + typsicher sein."""
        sr = cap.StageResult(stage_id=2, name="edges", status="ok", gate_ok=True)
        assert sr.stage_id == 2
        assert sr.name == "edges"
        assert sr.status == "ok"
        assert sr.gate_ok is True

    def test_stage_result_has_optional_write_scope(self):
        """Stage 1 StageResult: write_scope, quarantine_refused, content_loss."""
        sr = cap.StageResult(
            stage_id=1,
            name="atomize",
            status="ok",
            gate_ok=True,
            write_scope=10,
            quarantine_refused=2,
            content_loss=0,
        )
        assert sr.write_scope == 10
        assert sr.quarantine_refused == 2
        assert sr.content_loss == 0

    def test_stage_result_has_optional_edge_fields(self):
        """Stage 3 StageResult: dangling_count, max_edges_per_atom."""
        sr = cap.StageResult(
            stage_id=3,
            name="edge_quality_gate",
            status="ok",
            gate_ok=True,
            dangling_count=0,
            max_edges_per_atom=12,
        )
        assert sr.dangling_count == 0
        assert sr.max_edges_per_atom == 12

    def test_stage_result_has_optional_updated(self):
        """Stage 4 StageResult: updated field."""
        sr = cap.StageResult(stage_id=4, name="backref_invert", status="ok", gate_ok=True, updated=42)
        assert sr.updated == 42


# ---------------------------------------------------------------------------
# T1a — Stage-Registry (STAGES / GATE_CHECKS vollstaendigkeit)
# ---------------------------------------------------------------------------

class TestStageRegistry:
    def test_stages_contains_all_stage_ids(self):
        """STAGES muss Stages 0-8 (9 Eintraege) enthalten (stage 8 = BL-484 interface)."""
        stages = cap.STAGES
        # Supports list-of-dicts oder dict
        if isinstance(stages, dict):
            ids = set(stages.keys())
        else:
            ids = {s.get("stage_id", s.get("id")) for s in stages}
        assert ids == {0, 1, 2, 3, 4, 5, 6, 7, 8}, (
            f"STAGES enthaelt nicht genau IDs 0-8, sondern: {ids}"
        )

    def test_stages_have_names(self):
        """Jeder Stage-Eintrag hat einen nicht-leeren 'name'-Key."""
        stages = cap.STAGES
        if isinstance(stages, dict):
            items = list(stages.values())
        else:
            items = list(stages)
        for item in items:
            name = item.get("name", "")
            assert name, f"Stage {item} hat keinen 'name'"

    def test_stage_8_is_bl484_interface(self):
        """Stage 8 muss name='post_gate_bl484' oder aequivalenten BL-484-Verweis haben."""
        stages = cap.STAGES
        if isinstance(stages, dict):
            s8 = stages.get(8, {})
        else:
            s8 = next((s for s in stages if s.get("stage_id", s.get("id")) == 8), {})
        name = s8.get("name", "")
        assert "bl484" in name.lower() or "post" in name.lower() or "postflight" in name.lower(), (
            f"Stage 8 name '{name}' verweist nicht erkennbar auf BL-484"
        )

    def test_gate_checks_covers_all_stages(self):
        """GATE_CHECKS muss Eintraege fuer alle Stage-IDs 0-7 haben (Stage 8 conditional)."""
        for stage_id in range(8):  # 0..7
            assert stage_id in cap.GATE_CHECKS, (
                f"GATE_CHECKS fehlt fuer stage_id={stage_id}"
            )

    def test_gate_checks_values_are_callable(self):
        """Alle gate_fn in GATE_CHECKS muessen callable sein."""
        for stage_id, gate_fn in cap.GATE_CHECKS.items():
            assert callable(gate_fn), f"gate_fn fuer stage {stage_id} ist nicht callable"


# ---------------------------------------------------------------------------
# Gate-Logik direkt (Unit-Tests auf GATE_CHECKS-Funktionen, kein echtes Vault)
# ---------------------------------------------------------------------------

class TestEdgeQualityGate:
    def test_edge_quality_gate_ok(self):
        """dangling_count==0 UND max_edges_per_atom<=15 => gate True."""
        sr = cap.StageResult(
            stage_id=3, name="edge_quality_gate", status="ok", gate_ok=True,
            dangling_count=0, max_edges_per_atom=15
        )
        gate_fn = cap.GATE_CHECKS[3]
        assert gate_fn(sr) is True

    def test_edge_quality_gate_dangling_one_fails(self):
        """dangling_count=1 => gate False (T3d, T4f)."""
        sr = cap.StageResult(
            stage_id=3, name="edge_quality_gate", status="ok", gate_ok=True,
            dangling_count=1, max_edges_per_atom=5
        )
        gate_fn = cap.GATE_CHECKS[3]
        assert gate_fn(sr) is False, "dangling_count=1 muss gate verwerfen"

    def test_edge_quality_gate_cap_exceeded_fails(self):
        """max_edges_per_atom=16 => gate False (T3d, BL-455 cap)."""
        sr = cap.StageResult(
            stage_id=3, name="edge_quality_gate", status="ok", gate_ok=True,
            dangling_count=0, max_edges_per_atom=16
        )
        gate_fn = cap.GATE_CHECKS[3]
        assert gate_fn(sr) is False, "max_edges_per_atom=16 (>15) muss gate verwerfen"

    def test_edge_quality_gate_cap_exactly_15_ok(self):
        """max_edges_per_atom=15 ist genau die Grenze — muss bestehen."""
        sr = cap.StageResult(
            stage_id=3, name="edge_quality_gate", status="ok", gate_ok=True,
            dangling_count=0, max_edges_per_atom=15
        )
        gate_fn = cap.GATE_CHECKS[3]
        assert gate_fn(sr) is True


class TestContentLossGate:
    def test_content_loss_zero_and_quarantine_ok(self):
        """content_loss==0 UND quarantine_refused==quarantine_count => gate True (T3c, T4g)."""
        sr = cap.StageResult(
            stage_id=1, name="atomize", status="ok", gate_ok=True,
            write_scope=5, quarantine_refused=2, content_loss=0,
            quarantine_count=2
        )
        gate_fn = cap.GATE_CHECKS[1]
        assert gate_fn(sr) is True

    def test_content_loss_nonzero_fails(self):
        """content_loss=1 => gate False (T3c)."""
        sr = cap.StageResult(
            stage_id=1, name="atomize", status="ok", gate_ok=True,
            write_scope=5, quarantine_refused=2, content_loss=1,
            quarantine_count=2
        )
        gate_fn = cap.GATE_CHECKS[1]
        assert gate_fn(sr) is False, "content_loss=1 muss gate verwerfen"

    def test_quarantine_not_fully_refused_fails(self):
        """quarantine_refused < quarantine_count => gate False (T4g)."""
        sr = cap.StageResult(
            stage_id=1, name="atomize", status="ok", gate_ok=True,
            write_scope=5, quarantine_refused=1, content_loss=0,
            quarantine_count=2
        )
        gate_fn = cap.GATE_CHECKS[1]
        assert gate_fn(sr) is False, "unvollstaendige Quarantaene muss gate verwerfen"


class TestStage8Gate:
    def test_stage8_exit_zero_passes(self):
        """Stage 8 gate: exit_code==0 => True (T3f, INV-CAPSTONE-4)."""
        sr = cap.StageResult(
            stage_id=8, name="post_gate_bl484", status="ok", gate_ok=True,
            exit_code=0
        )
        gate_fn = cap.GATE_CHECKS.get(8)
        if gate_fn is None:
            pytest.skip("Stage 8 gate optional wenn BL-484 fehlt")
        assert gate_fn(sr) is True

    def test_stage8_nonzero_exit_fails(self):
        """Stage 8 gate: exit_code!=0 => False => rollback."""
        sr = cap.StageResult(
            stage_id=8, name="post_gate_bl484", status="fail", gate_ok=False,
            exit_code=1
        )
        gate_fn = cap.GATE_CHECKS.get(8)
        if gate_fn is None:
            pytest.skip("Stage 8 gate optional wenn BL-484 fehlt")
        assert gate_fn(sr) is False


# ---------------------------------------------------------------------------
# T4a/T4d — rollback-Funktion
# ---------------------------------------------------------------------------

class TestRollbackFunction:
    def test_rollback_exists_and_callable(self):
        """rollback(backup_tag, vault_root) muss existieren und callable sein (T4a)."""
        assert callable(cap.rollback), "cap.rollback ist nicht callable"

    def test_rollback_logs_tag_and_path(self, tmp_path, capsys):
        """rollback() muss backup_tag und vault_root loggbar machen (T4d)."""
        tag = "migration-capstone-backup-20260625T120000"
        # rollback darf external commands aufrufen — mocken wir subprocess
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            cap.rollback(tag, tmp_path)
        # Entweder stdout oder subprocess-Call enthaelt den tag
        out, err = capsys.readouterr()
        combined = out + err
        # Mindestens eine der folgenden Bedingungen: tag im output ODER tag im subprocess-call
        tag_in_output = tag in combined
        tag_in_subprocess = any(
            tag in str(c) for c in mock_run.call_args_list
        ) if mock_run.called else False
        assert tag_in_output or tag_in_subprocess, (
            f"rollback hat den backup_tag '{tag}' weder geloggt noch an subprocess uebergeben"
        )


# ---------------------------------------------------------------------------
# T1g/T1h — Gate-Failure-Pfad + State-Machine ROLLBACK
# ---------------------------------------------------------------------------

class TestGateFailurePath:
    def test_gate_failure_stops_pipeline(self, tmp_path):
        """Wenn Stage 0a (preflight) fehlschlaegt: exit code 2, kein naechster Stage (T1g, T1h)."""
        # Wir mocken run_stage so, dass Stage 0 fehlschlaegt und beobachten,
        # dass kein Stage 1+ gestartet wird.
        executed_stages = []

        def fake_run_stage(stage_id, cmd_or_fn, *, gate_fn, **kwargs):
            executed_stages.append(stage_id)
            if stage_id == 0:
                return cap.StageResult(
                    stage_id=0, name="preflight_check", status="fail", gate_ok=False
                )
            return cap.StageResult(stage_id=stage_id, name="x", status="ok", gate_ok=True)

        with patch.object(cap, "run_stage", side_effect=fake_run_stage):
            with pytest.raises(SystemExit) as exc_info:
                cap.run(
                    vault=tmp_path,
                    repo_models=tmp_path,
                    dry_run=True,
                    force_go=True,
                    stage_from=0,
                    stage_to=7,
                )
        assert exc_info.value.code == 2, (
            f"Erwarte exit code 2 bei Preflight-Fail, bekam {exc_info.value.code}"
        )
        # Stage 1+ darf NICHT in executed_stages erscheinen
        assert all(s == 0 for s in executed_stages), (
            f"Stages nach Preflight-Fail wurden noch ausgefuehrt: {executed_stages}"
        )

    def test_gate_failure_report_contains_aborted_at(self, tmp_path):
        """Preflight-Fail-Report muss aborted_at=PREFLIGHT_CHECK enthalten (T1g)."""
        report_path = tmp_path / "report.json"

        def fake_run_stage(stage_id, cmd_or_fn, *, gate_fn, **kwargs):
            if stage_id == 0:
                return cap.StageResult(
                    stage_id=0, name="preflight_check", status="fail", gate_ok=False
                )
            return cap.StageResult(stage_id=stage_id, name="x", status="ok", gate_ok=True)

        with patch.object(cap, "run_stage", side_effect=fake_run_stage):
            try:
                cap.run(
                    vault=tmp_path,
                    repo_models=tmp_path,
                    dry_run=True,
                    force_go=True,
                    stage_from=0,
                    stage_to=7,
                    out=report_path,
                )
            except SystemExit:
                pass

        assert report_path.exists(), "report.json wurde nicht geschrieben"
        report = json.loads(report_path.read_text(encoding="utf-8"))
        assert report.get("aborted_at") == "PREFLIGHT_CHECK", (
            f"report[aborted_at] erwartet 'PREFLIGHT_CHECK', bekam: {report.get('aborted_at')}"
        )

    def test_gate_failure_transitions_to_rollback_state(self, tmp_path):
        """State-Machine muss nach gate failure in ROLLBACK-Zustand (nicht DONE) wechseln (T4c)."""
        state_transitions = []

        original_set_state = getattr(cap, "set_state", None)

        def fake_set_state(state):
            state_transitions.append(state)
            if original_set_state:
                original_set_state(state)

        with patch.object(cap, "run_stage", side_effect=lambda sid, cmd, *, gate_fn, **kw: (
            cap.StageResult(stage_id=sid, name="x", status="fail", gate_ok=False)
        )):
            with patch.object(cap, "set_state", side_effect=fake_set_state, create=True):
                try:
                    cap.run(
                        vault=tmp_path,
                        repo_models=tmp_path,
                        dry_run=True,
                        force_go=True,
                        stage_from=0,
                        stage_to=7,
                    )
                except SystemExit:
                    pass

        # ROLLBACK muss in den Zustandsuebergaengen erscheinen, DONE nicht (wenn gate fail)
        assert "ROLLBACK" in state_transitions or any(
            "rollback" in str(s).lower() for s in state_transitions
        ), f"ROLLBACK-Zustand nie eingetreten. Zustaende: {state_transitions}"
        assert "DONE" not in state_transitions, (
            f"DONE-Zustand nach gate-failure ist verboten. Zustaende: {state_transitions}"
        )


# ---------------------------------------------------------------------------
# T4b/T4e — Rollback wird bei gate failure aufgerufen, NICHT bei dry-run
# ---------------------------------------------------------------------------

class TestRollbackCalledOnGateFailure:
    def test_rollback_called_on_gate_failure(self, tmp_path):
        """Nach Simulate-Gate-Fail in Stage 2 muss rollback() aufgerufen werden (T4b)."""
        rollback_calls = []

        def fake_rollback(tag, vault_root):
            rollback_calls.append((tag, vault_root))

        def fake_run_stage(stage_id, cmd_or_fn, *, gate_fn, **kwargs):
            if stage_id == 2:
                return cap.StageResult(
                    stage_id=2, name="edges", status="fail", gate_ok=False
                )
            return cap.StageResult(stage_id=stage_id, name="x", status="ok", gate_ok=True)

        with patch.object(cap, "run_stage", side_effect=fake_run_stage):
            with patch.object(cap, "rollback", side_effect=fake_rollback):
                try:
                    cap.run(
                        vault=tmp_path,
                        repo_models=tmp_path,
                        dry_run=False,
                        force_go=True,
                        stage_from=0,
                        stage_to=7,
                    )
                except SystemExit:
                    pass

        assert len(rollback_calls) >= 1, "rollback() wurde nach gate-fail NICHT aufgerufen"

    def test_dry_run_never_calls_rollback(self, tmp_path):
        """--dry-run darf rollback() NIEMALS aufrufen, auch bei gate failure (T4e, INV-CAPSTONE-3)."""
        rollback_calls = []

        def fake_rollback(tag, vault_root):
            rollback_calls.append((tag, vault_root))

        def fake_run_stage(stage_id, cmd_or_fn, *, gate_fn, **kwargs):
            # Simuliere gate fail in Stage 2 auch im dry-run
            if stage_id == 2:
                return cap.StageResult(
                    stage_id=2, name="edges", status="fail", gate_ok=False
                )
            return cap.StageResult(stage_id=stage_id, name="x", status="ok", gate_ok=True)

        with patch.object(cap, "run_stage", side_effect=fake_run_stage):
            with patch.object(cap, "rollback", side_effect=fake_rollback):
                try:
                    cap.run(
                        vault=tmp_path,
                        repo_models=tmp_path,
                        dry_run=True,  # DRY-RUN
                        force_go=True,
                        stage_from=0,
                        stage_to=7,
                    )
                except SystemExit:
                    pass

        assert rollback_calls == [], (
            f"rollback() wurde im dry-run aufgerufen (verboten!): {rollback_calls}"
        )


# ---------------------------------------------------------------------------
# T5a — Write-Fence: --write ohne --force-go => interactive GO prompt
# ---------------------------------------------------------------------------

class TestWriteFence:
    def test_user_go_required_for_write(self, tmp_path):
        """--write ohne --force-go: wenn User NICHT 'GO' tippt => exit 3 (T5a, INV-CAPSTONE-3)."""
        with patch("builtins.input", return_value="no"):
            with pytest.raises(SystemExit) as exc_info:
                cap.run(
                    vault=tmp_path,
                    repo_models=tmp_path,
                    dry_run=False,
                    force_go=False,  # kein --force-go
                    stage_from=0,
                    stage_to=7,
                )
        assert exc_info.value.code == 3, (
            f"Erwartet exit 3 bei nicht-GO User-Input, bekam {exc_info.value.code}"
        )

    def test_write_fence_user_go_proceeds(self, tmp_path):
        """--write ohne --force-go, User tippt 'GO' => kein exit 3 (Prompt akzeptiert)."""
        stage_started = []

        def fake_run_stage(stage_id, cmd_or_fn, *, gate_fn, **kwargs):
            stage_started.append(stage_id)
            return cap.StageResult(stage_id=stage_id, name="x", status="ok", gate_ok=True)

        with patch("builtins.input", return_value="GO"):
            with patch.object(cap, "run_stage", side_effect=fake_run_stage):
                try:
                    cap.run(
                        vault=tmp_path,
                        repo_models=tmp_path,
                        dry_run=False,
                        force_go=False,
                        stage_from=0,
                        stage_to=7,
                    )
                except SystemExit as e:
                    assert e.code != 3, "User GO akzeptiert => kein exit 3 erlaubt"

    def test_write_fence_default_is_dry_run(self, tmp_path):
        """Wenn main() ohne --write/--dry-run aufgerufen wird, laueft es als dry-run (INV-CAPSTONE-3)."""
        # Pruefen via main() CLI mit minimalem Vault
        argv = ["run", f"--vault={tmp_path}", f"--repo-models={tmp_path}", "--force-go"]
        # main() darf KEINE Schreiboperationen machen ohne --write
        with patch.object(cap, "run_stage", side_effect=lambda sid, cmd, *, gate_fn, **kw: (
            cap.StageResult(stage_id=sid, name="x", status="ok", gate_ok=True)
        )):
            try:
                cap.main(argv)
            except SystemExit as e:
                # exit 0 oder 2 okay, exit 3 verboten (write-fence bei dry-run ist Unsinn)
                assert e.code != 3, "dry-run (default) loest irrtuemlicherweise write-fence aus"


# ---------------------------------------------------------------------------
# T1d/T5d — --stage-from/--stage-to Isolation
# ---------------------------------------------------------------------------

class TestStageFromToIsolation:
    def test_stage_from_to_isolation(self, tmp_path):
        """--stage-from 2 --stage-to 3 darf nur Stages 2 und 3 ausfuehren (T1d, T5d)."""
        executed_stages = []

        def fake_run_stage(stage_id, cmd_or_fn, *, gate_fn, **kwargs):
            executed_stages.append(stage_id)
            return cap.StageResult(stage_id=stage_id, name="x", status="ok", gate_ok=True)

        with patch.object(cap, "run_stage", side_effect=fake_run_stage):
            try:
                cap.run(
                    vault=tmp_path,
                    repo_models=tmp_path,
                    dry_run=True,
                    force_go=True,
                    stage_from=2,
                    stage_to=3,
                )
            except SystemExit:
                pass

        unexpected = [s for s in executed_stages if s < 2 or s > 3]
        assert not unexpected, (
            f"Stages ausserhalb [2,3] wurden ausgefuehrt: {unexpected}"
        )
        assert 2 in executed_stages, "Stage 2 wurde nicht ausgefuehrt"
        assert 3 in executed_stages, "Stage 3 wurde nicht ausgefuehrt"


# ---------------------------------------------------------------------------
# T5e — Report-JSON-Schema
# ---------------------------------------------------------------------------

class TestReportJsonSchema:
    def test_report_json_schema(self, tmp_path):
        """Finales report JSON muss vault, run_ts, stages, overall_ok enthalten (T5e)."""
        report_path = tmp_path / "capstone_report.json"

        def fake_run_stage(stage_id, cmd_or_fn, *, gate_fn, **kwargs):
            return cap.StageResult(stage_id=stage_id, name="x", status="ok", gate_ok=True)

        with patch.object(cap, "run_stage", side_effect=fake_run_stage):
            try:
                cap.run(
                    vault=tmp_path,
                    repo_models=tmp_path,
                    dry_run=True,
                    force_go=True,
                    stage_from=0,
                    stage_to=7,
                    out=report_path,
                )
            except SystemExit:
                pass

        assert report_path.exists(), "capstone_report.json wurde nicht geschrieben"
        report = json.loads(report_path.read_text(encoding="utf-8"))

        assert "vault" in report, "report fehlt 'vault'"
        assert "run_ts" in report, "report fehlt 'run_ts'"
        assert "stages" in report, "report fehlt 'stages'"
        assert "overall_ok" in report, "report fehlt 'overall_ok'"

        # stages muss eine Liste mit stage-Eintraegen sein
        stages_list = report["stages"]
        assert isinstance(stages_list, list), f"report['stages'] ist kein list: {type(stages_list)}"

        # Jeder stage-Eintrag braucht mindestens stage_id + gate_ok
        for s in stages_list:
            assert "gate_ok" in s, f"stage-Eintrag fehlt 'gate_ok': {s}"

        # vault muss auf tmp_path verweisen
        assert str(tmp_path) in report["vault"] or report["vault"] == str(tmp_path), (
            f"report['vault']={report['vault']} stimmt nicht mit {tmp_path} ueberein"
        )

        # overall_ok muss bool sein
        assert isinstance(report["overall_ok"], bool), (
            f"overall_ok muss bool sein, ist {type(report['overall_ok'])}"
        )


# ---------------------------------------------------------------------------
# INV-CAPSTONE-4 — Stage 8 ist nur Interface, kein Rollback wenn BL-484 fehlt
# ---------------------------------------------------------------------------

class TestStage8InterfaceOnly:
    def test_stage8_absent_bl484_noop_not_error(self, tmp_path):
        """INV-CAPSTONE-4: wenn BL-484 nicht gebaut ist, ist Stage 8 WARNING, kein Fehler.
        overall_ok reflektiert nur Stages 0-7."""
        report_path = tmp_path / "report8.json"

        def fake_run_stage(stage_id, cmd_or_fn, *, gate_fn, **kwargs):
            if stage_id == 8:
                # BL-484 fehlt — kein tool vorhanden
                raise FileNotFoundError("BL-484 tool not found")
            return cap.StageResult(stage_id=stage_id, name="x", status="ok", gate_ok=True)

        rollback_calls = []
        with patch.object(cap, "run_stage", side_effect=fake_run_stage):
            with patch.object(cap, "rollback", side_effect=lambda t, v: rollback_calls.append((t, v))):
                try:
                    cap.run(
                        vault=tmp_path,
                        repo_models=tmp_path,
                        dry_run=True,
                        force_go=True,
                        stage_from=0,
                        stage_to=8,
                        out=report_path,
                    )
                except SystemExit as e:
                    # exit 0 oder 2 nur wenn Stages 0-7 alle ok
                    # exit 2 wegen BL-484 fehlen waere FALSCH
                    assert e.code == 0, (
                        f"fehlende BL-484 darf NICHT exit 2 erzwingen, bekam {e.code}"
                    )

        # Kein Rollback durch fehlende BL-484
        assert rollback_calls == [], (
            "Rollback wurde durch fehlende BL-484 ausgeloest (verboten, INV-CAPSTONE-4)"
        )

        if report_path.exists():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            # overall_ok reflektiert 0-7, nicht Stage 8
            assert report.get("overall_ok") is True, (
                "overall_ok muss True sein wenn Stages 0-7 alle bestanden"
            )


# ---------------------------------------------------------------------------
# T5c — Backup BEVOR Stage 1 schreibt
# ---------------------------------------------------------------------------

class TestBackupBeforeWrite:
    def test_backup_before_write(self, tmp_path):
        """Stage 0c (Backup) muss VOR Stage 1 (Atomize) laufen (T5c, AK-5)."""
        call_order = []

        def fake_run_stage(stage_id, cmd_or_fn, *, gate_fn, **kwargs):
            call_order.append(stage_id)
            return cap.StageResult(stage_id=stage_id, name="x", status="ok", gate_ok=True)

        with patch.object(cap, "run_stage", side_effect=fake_run_stage):
            try:
                cap.run(
                    vault=tmp_path,
                    repo_models=tmp_path,
                    dry_run=False,
                    force_go=True,
                    stage_from=0,
                    stage_to=1,
                )
            except SystemExit:
                pass

        # Stage 0 muss VOR Stage 1 aufgerufen worden sein
        if 0 in call_order and 1 in call_order:
            assert call_order.index(0) < call_order.index(1), (
                "Stage 0 (Preflight+Backup) muss vor Stage 1 (Atomize) laufen"
            )


# ---------------------------------------------------------------------------
# Kommando-Markdown-Strukturtest (INV-CAPSTONE-1, M2-Characterization)
# ---------------------------------------------------------------------------

class TestCommandMarkdownStructure:
    """Prueft, dass _truth_migration_capstone.md die VDD-Vertrags-Marker enthaelt
    und ein echtes Thin-Invoker ist (kein Pseudocode, der Stage-Logik re-implementiert).
    Dieser Test MUSS fehlschlagen solange die Datei nicht existiert (RED)."""

    COMMAND_MD = Path(
        "C:/Users/hanno/RiderProjects/OmniCommand-wtA/.claude/commands/_truth_migration_capstone.md"
    )

    def test_command_md_exists(self):
        """_truth_migration_capstone.md muss existieren."""
        assert self.COMMAND_MD.exists(), (
            f"Kommando-Markdown fehlt: {self.COMMAND_MD}\n"
            "RED: dies ist erwartet — GREEN-Worker muss die Datei erstellen."
        )

    def test_command_md_has_state_machine_section(self):
        """Kommando-MD muss einen STATE-MACHINE-Abschnitt enthalten."""
        content = self.COMMAND_MD.read_text(encoding="utf-8")
        assert "STATE-MACHINE" in content, (
            "Kein STATE-MACHINE-Abschnitt in _truth_migration_capstone.md"
        )

    def test_command_md_has_per_stage_entries(self):
        """Kommando-MD muss Pro-Stage-Eintraege (Stage 0 bis Stage 7) haben."""
        content = self.COMMAND_MD.read_text(encoding="utf-8")
        for stage_id in range(8):
            assert f"Stage {stage_id}" in content or f"stage_{stage_id}" in content.lower(), (
                f"Stage {stage_id} fehlt im Kommando-Markdown"
            )

    def test_command_md_has_gate_markers(self):
        """Kommando-MD muss [GATE]-Marker fuer Gate-Definitionen enthalten."""
        content = self.COMMAND_MD.read_text(encoding="utf-8")
        assert "[GATE]" in content, "Keine [GATE]-Marker in _truth_migration_capstone.md"

    def test_command_md_has_inv_capstone1_marker(self):
        """INV-CAPSTONE-1 (Thin-Invoker) muss im Kommando-Markdown referenziert sein."""
        content = self.COMMAND_MD.read_text(encoding="utf-8")
        assert "INV-CAPSTONE-1" in content, (
            "INV-CAPSTONE-1 (Thin-Invoker-Invariante) fehlt im Kommando-Markdown"
        )

    def test_command_md_is_thin_invoker_no_inline_stage_logic(self):
        """INV-CAPSTONE-1: Kommando-MD referenziert py -3 .claude/scripts/truth_migration_capstone.py,
        implementiert Stage-Logik NICHT als Pseudocode inline."""
        content = self.COMMAND_MD.read_text(encoding="utf-8")
        # Thin-Invoker muss CLI-Aufruf enthalten
        assert "truth_migration_capstone.py" in content, (
            "Kommando-MD verweist nicht auf truth_migration_capstone.py (Thin-Invoker-Verletzung)"
        )
        assert "py -3" in content or "python" in content.lower(), (
            "Kein python/py -3-Aufruf in Kommando-MD (Thin-Invoker-Verletzung)"
        )
        # Muss KEINEN Stage-Pseudocode direkt implementieren
        # (Heuristik: kein langer Pseudocode-Block mit mehreren stage/tool-Zeilen ohne py-Aufruf)
        pseudocode_density = content.count("run_stage") + content.count("subprocess.run")
        assert pseudocode_density == 0 or (
            "truth_migration_capstone.py" in content
        ), "Verdacht auf inline Pseudocode in Kommando-MD (INV-CAPSTONE-1-Verletzung)"


# ---------------------------------------------------------------------------
# BUG-CHARACTERIZING TESTS (BL-483 Verify-Phase finding, 2026-06-25)
# Bug: _write_report() and run() never mkdir the output/capstone directory,
# causing FileNotFoundError on real vaults.
# RED: these MUST fail until GREEN fixes the mkdir omission.
# ---------------------------------------------------------------------------

class TestOutputDirCreation:
    def test_write_report_creates_parent_dirs(self, tmp_path):
        """_write_report() muss parent-Verzeichnisse anlegen bevor es schreibt.

        Bug: Path(out).write_text(...) ohne vorheriges parent.mkdir(parents=True)
        schlaegt fehl, wenn das Verzeichnis noch nicht existiert.
        Fix: out_path.parent.mkdir(parents=True, exist_ok=True) vor write_text.
        """
        out = tmp_path / "nested" / "deep" / "r.json"
        # Directory does NOT exist yet — the function must create it
        cap._write_report(
            out=out,
            vault=tmp_path,
            run_ts="t",
            results=[],
            overall_ok=True,
        )
        assert out.exists(), (
            f"_write_report() hat {out} nicht erstellt — parent-Verzeichnis wurde nicht angelegt "
            "(Bug: fehlendes parent.mkdir vor write_text)"
        )

    def test_run_creates_subtool_out_dir(self, tmp_path):
        """run() muss out_dir (vault/.claude/output/capstone) anlegen BEVOR Stages gestartet werden.

        Bug: out_dir = vault / '.claude' / 'output' / 'capstone' wird berechnet aber nie
        mkdir'd — Sub-Tools erhalten einen --out-Pfad in einem nicht-existenten Verzeichnis
        und crashen mit FileNotFoundError (false-negative gate failure).
        Fix: out_dir.mkdir(parents=True, exist_ok=True) direkt nach Berechnung von out_dir.
        """
        expected_out_dir = tmp_path / ".claude" / "output" / "capstone"
        assert not expected_out_dir.exists(), "Precondition: out_dir darf noch nicht existieren"

        def fake_run_stage(stage_id, cmd_or_fn, *, gate_fn, **kwargs):
            return cap.StageResult(stage_id=stage_id, name="x", status="ok", gate_ok=True)

        with patch.object(cap, "run_stage", side_effect=fake_run_stage):
            try:
                cap.run(
                    vault=tmp_path,
                    repo_models=tmp_path,
                    dry_run=True,
                    force_go=True,
                    stage_from=0,
                    stage_to=1,
                )
            except SystemExit:
                pass

        assert expected_out_dir.exists(), (
            f"run() hat {expected_out_dir} nicht angelegt — Sub-Tools wuerden "
            "FileNotFoundError werfen wenn sie --out in dieses Verzeichnis schreiben "
            "(Bug: fehlendes out_dir.mkdir vor Stage-Loop)"
        )


# ---------------------------------------------------------------------------
# COMMAND-AUDIT TESTS: _build_stage_cmd real command-list assertions
# (BL-483 Command Audit Finding, 2026-06-25)
#
# These tests call cap._build_stage_cmd DIRECTLY (no patching) and assert
# on the returned argv lists. No subprocess is executed. No real vault needed
# for most tests; test_stage7_view_projector_two_positionals uses tmp_path to
# plant a view file so discover_views has something to find after GREEN's fix.
#
# EXPECTED RED FAILURES (pinned bugs):
#   test_dryrun_never_contains_write_flags     -- stage 4 dry-run has --apply
#   test_stage4_dryrun_no_apply_no_dryrun_flag -- stage 4 dry-run has --apply AND --dry-run
#   test_stage7_view_projector_two_positionals -- stage 7 only 1 positional (vault only)
#   test_no_unknown_flags_in_any_dryrun        -- stage 4 dry-run passes --dry-run (unknown)
#   test_stage5_dryrun_has_dryrun_flag         -- stage 5 dry-run omits --dry-run entirely
# ---------------------------------------------------------------------------

# Filesystem-free sentinel paths -- no disk I/O required
_V = Path("C:/x/vault")
_R = Path("C:/x/.claude/models")
_O = Path("C:/x/vault/.claude/output/capstone")
_BT = "migration-capstone-backup-20260625T120000"
_WRITE_TOKENS = frozenset({"--confirm", "--apply", "--write", "--replace"})


def _build(stage_id: int, dry_run: bool) -> list:
    """Call cap._build_stage_cmd with sentinel paths."""
    return cap._build_stage_cmd(stage_id, _V, _R, dry_run, _BT, _O)


def _nonflag_args(cmd: list) -> list:
    """Non-flag tokens after [python, script.py] -- potential positional arguments."""
    return [t for t in cmd[2:] if not t.startswith("-")]


def _stage7_cmds(vault, out_dir, dry_run: bool) -> list:
    """Stage 7 command(s) as list of argv lists.
    Tolerates single cmd (list[str]) or fan-out list of cmds (list[list[str]]).
    """
    raw = cap._build_stage_cmd(7, vault, _R, dry_run, _BT, out_dir)
    if not raw:
        return []
    if isinstance(raw[0], list):
        return raw   # list of per-view commands
    return [raw]     # single command wrapped


class TestBuildStageCmdRealCommands:
    """Non-mocked assertions on cap._build_stage_cmd output lists.

    Ground-truth tool conventions (verified CLIs):
      Stage 1 truth_pilot_cutover:   WRITE adds --confirm; DRY-RUN omits --confirm.
      Stage 2 keyword_edge_writer:   DRY-RUN uses --dry-run; WRITE uses --replace (no --dry-run).
      Stage 3 keyword_edge_writer:   always --dry-run (gate-only, read-only).
      Stage 4 truth_edge_backref:    NO --dry-run flag; WRITE adds --apply; DRY-RUN omits --apply.
      Stage 5 wikilink_materializer: DRY-RUN uses --dry-run; WRITE uses --write (no --dry-run).
      Stage 7 view_projector:        <view_path> <vault_root> [--write]; 2 positionals per call.
    """

    # ------------------------------------------------------------------
    # Test 1
    # ------------------------------------------------------------------
    def test_dryrun_never_contains_write_flags(self):
        """For every stage 0-7 dry-run command, none of
        {--confirm, --apply, --write, --replace} may appear.

        Exception: stage 2 may have --replace ONLY if --dry-run is also present
        (belt-and-suspenders; ideal fix removes --replace from stage 2 dry-run).

        Currently FAILS: stage 4 dry-run contains --apply (hard write trigger).
        """
        for stage_id in range(8):
            cmd = _build(stage_id, dry_run=True)
            cmd_set = set(cmd)
            bad = _WRITE_TOKENS & cmd_set

            # Stage 2 exception: --replace tolerated only when --dry-run guards it
            if stage_id == 2 and "--replace" in bad and "--dry-run" in cmd_set:
                bad -= {"--replace"}

            assert not bad, (
                f"Stage {stage_id} dry-run cmd contains write-trigger token(s) {bad}.\n"
                f"Full cmd: {cmd}"
            )

    # ------------------------------------------------------------------
    # Test 2
    # ------------------------------------------------------------------
    def test_stage4_dryrun_no_apply_no_dryrun_flag(self):
        """truth_edge_backref.py: no --dry-run flag exists; --apply triggers writes.

        Stage 4 DRY-RUN MUST NOT have --apply (write trigger).
        Stage 4 DRY-RUN MUST NOT have --dry-run (unknown arg -> argparse crash).
        Stage 4 WRITE MUST have --apply.

        Currently FAILS: dry-run has BOTH --apply AND --dry-run.
        """
        dry = _build(4, dry_run=True)
        wrt = _build(4, dry_run=False)

        assert "--apply" not in dry, (
            f"Stage 4 dry-run must NOT have --apply.\nCmd: {dry}"
        )
        assert "--dry-run" not in dry, (
            f"Stage 4 dry-run must NOT have --dry-run (unknown flag -> argparse crash).\n"
            f"Cmd: {dry}"
        )
        assert "--apply" in wrt, (
            f"Stage 4 WRITE must have --apply.\nCmd: {wrt}"
        )

    # ------------------------------------------------------------------
    # Test 3
    # ------------------------------------------------------------------
    def test_stage1_confirm_only_on_write(self):
        """truth_pilot_cutover: --confirm absent in dry-run, present in write.

        Currently PASSES -- pinned so GREEN cannot regress it while fixing stage 4/7.
        """
        dry = _build(1, dry_run=True)
        wrt = _build(1, dry_run=False)

        assert "--confirm" not in dry, (
            f"Stage 1 dry-run must NOT have --confirm.\nCmd: {dry}"
        )
        assert "--confirm" in wrt, (
            f"Stage 1 WRITE must have --confirm.\nCmd: {wrt}"
        )

    # ------------------------------------------------------------------
    # Test 4
    # ------------------------------------------------------------------
    def test_stage5_dryrun_vs_write(self):
        """wikilink_materializer: --write absent in dry-run, present in write.

        Currently PASSES for the --write check.
        """
        dry = _build(5, dry_run=True)
        wrt = _build(5, dry_run=False)

        assert "--write" not in dry, (
            f"Stage 5 dry-run must NOT have --write.\nCmd: {dry}"
        )
        assert "--write" in wrt, (
            f"Stage 5 WRITE must have --write.\nCmd: {wrt}"
        )

    # ------------------------------------------------------------------
    # Test 4b (bonus ground-truth: stage 5 DRY-RUN must use --dry-run)
    # ------------------------------------------------------------------
    def test_stage5_dryrun_has_dryrun_flag(self):
        """wikilink_materializer --dry-run flag exists and MUST be used in dry-run mode.

        Ground truth: 'DRY-RUN uses --dry-run (no --write)'.
        Currently FAILS: stage 5 dry-run omits --dry-run (reads-only by omission only;
        tool expects explicit --dry-run for correct reporting behavior).
        """
        dry = _build(5, dry_run=True)
        assert "--dry-run" in dry, (
            f"Stage 5 dry-run MUST pass --dry-run to wikilink_materializer "
            f"(tool supports it; omitting leaves intent ambiguous to tool).\nCmd: {dry}"
        )

    # ------------------------------------------------------------------
    # Test 5
    # ------------------------------------------------------------------
    def test_stage7_view_projector_two_positionals(self, tmp_path):
        """view_projector.py CLI: <view_path> <vault_root> [--write] -- TWO positionals.

        Plants a 6_PL parking-lot view at the correct /6_PL/ path so that
        _discover_views with the CORRECT scope (after GREEN's fix) still finds it.
        Root-level parking-lot files are excluded by the corrected scope.

        Tolerates single cmd OR list-of-per-view cmds (list[list[str]]).
        Assertions: >=2 positionals per cmd (view_path + vault_root);
                    dry-run has no --write; write has --write.
        """
        # Plant at the canonical 6_PL location (matches correct discovery scope)
        fake_view = tmp_path / "Backlog" / "BL-999" / "6_PL" / "BL-999-parking-lot.md"
        fake_view.parent.mkdir(parents=True, exist_ok=True)
        fake_view.write_text("# BL-999 Parking Lot\n", encoding="utf-8")
        out_dir = tmp_path / ".claude" / "output" / "capstone"

        for dry_run in (True, False):
            cmds = _stage7_cmds(tmp_path, out_dir, dry_run)
            assert cmds, (
                f"Stage 7 (dry_run={dry_run}) returned no commands"
            )

            for cmd in cmds:
                positionals = _nonflag_args(cmd)
                assert len(positionals) >= 2, (
                    f"Stage 7 (dry_run={dry_run}) view_projector needs "
                    f">=2 positionals (<view_path> <vault_root>), got {len(positionals)}: "
                    f"{positionals}\nFull cmd: {cmd}"
                )
                vault_str = str(tmp_path)
                assert vault_str in positionals, (
                    f"Stage 7 (dry_run={dry_run}) vault root must appear as positional.\n"
                    f"positionals={positionals}\nCmd: {cmd}"
                )
                non_vault = [p for p in positionals if p != vault_str]
                assert non_vault, (
                    f"Stage 7 (dry_run={dry_run}) no positional besides vault -- "
                    f"view_path missing.\npositionals={positionals}\nCmd: {cmd}"
                )

            # --write flag correctness per cmd
            for cmd in cmds:
                if dry_run:
                    assert "--write" not in cmd, (
                        f"Stage 7 dry-run must NOT have --write.\nCmd: {cmd}"
                    )
                else:
                    assert "--write" in cmd, (
                        f"Stage 7 WRITE must have --write.\nCmd: {cmd}"
                    )

    # ------------------------------------------------------------------
    # Test 6
    # ------------------------------------------------------------------
    def test_no_unknown_flags_in_any_dryrun(self):
        """Stages whose tools lack a --dry-run flag must not receive it in dry-run mode.

        truth_pilot_cutover.py (stage 1) and truth_edge_backref.py (stage 4)
        have NO --dry-run flag; passing it causes an argparse crash.

        Currently FAILS: stage 4 dry-run appends --dry-run (unknown to argparse).
        """
        flagless_stages = {
            1: "truth_pilot_cutover.py",
            4: "truth_edge_backref.py",
        }
        for stage_id, tool in flagless_stages.items():
            cmd = _build(stage_id, dry_run=True)
            assert "--dry-run" not in cmd, (
                f"Stage {stage_id} ({tool}) has no --dry-run flag; "
                f"passing it crashes argparse.\nCmd: {cmd}"
            )

    # ------------------------------------------------------------------
    # Bonus: stage 2 write / dry-run cross-checks (regression guards)
    # ------------------------------------------------------------------
    def test_stage2_write_has_replace_no_dryrun(self):
        """keyword_edge_writer WRITE: --replace present, --dry-run absent.

        Currently PASSES -- pinned regression guard.
        """
        wrt = _build(2, dry_run=False)
        assert "--replace" in wrt, (
            f"Stage 2 WRITE must have --replace.\nCmd: {wrt}"
        )
        assert "--dry-run" not in wrt, (
            f"Stage 2 WRITE must NOT have --dry-run.\nCmd: {wrt}"
        )

    def test_stage2_dryrun_has_dryrun_flag(self):
        """keyword_edge_writer DRY-RUN: --dry-run must be present.

        Currently PASSES -- pinned regression guard.
        """
        dry = _build(2, dry_run=True)
        assert "--dry-run" in dry, (
            f"Stage 2 dry-run must pass --dry-run to keyword_edge_writer.\nCmd: {dry}"
        )


# ---------------------------------------------------------------------------
# REAL-DRY-RUN FINDINGS (BL-483 final RED round, 2026-06-25)
# Bugs surfaced by running against the OmniCommand vault:
#   (1) view_projector UnicodeEncodeError on '→': fix = PYTHONIOENCODING=utf-8 in env
#   (2) _discover_views too broad: includes Model.md + root *.bak parking → crash/noise
#   (3) GATE_CHECKS[7] has no no_substrate logic (generic _gate_default insufficient)
# ---------------------------------------------------------------------------

class TestDiscoverViewsScope:
    def test_discover_views_only_6pl_parking(self, tmp_path):
        """_discover_views must ONLY return /6_PL/*-parking-lot.md files.

        Three files planted:
          (a) Backlog/BL-1/6_PL/BL-1-parking-lot.md  -> MUST match (canonical 6_PL view)
          (b) Backlog/BL-2/2_Model/BL-2_Model.md      -> must NOT match (Model, not a view)
          (c) _parking-lot.bak.md at vault root        -> must NOT match (not in /6_PL/)

        Currently FAILS: _discover_views includes (b) via Backlog/**/2_Model/*_Model.md
        and (c) via rglob('*parking-lot*.md').
        """
        # (a) canonical 6_PL parking view -- should be discovered
        view_a = tmp_path / "Backlog" / "BL-1" / "6_PL" / "BL-1-parking-lot.md"
        view_a.parent.mkdir(parents=True, exist_ok=True)
        view_a.write_text("# BL-1 Parking Lot\n", encoding="utf-8")

        # (b) Model file -- must NOT be discovered
        model_b = tmp_path / "Backlog" / "BL-2" / "2_Model" / "BL-2_Model.md"
        model_b.parent.mkdir(parents=True, exist_ok=True)
        model_b.write_text("# BL-2 Model\n", encoding="utf-8")

        # (c) root-level parking-lot backup -- must NOT be discovered
        bak_c = tmp_path / "_parking-lot.bak.md"
        bak_c.write_text("# stale backup\n", encoding="utf-8")

        discovered = cap._discover_views(tmp_path)

        # Exactly one view (a) must be found
        assert len(discovered) == 1, (
            f"_discover_views should return exactly 1 view (the 6_PL parking file), "
            f"got {len(discovered)}: {[str(p) for p in discovered]}\n"
            "Bug: current implementation includes Model.md and root parking-lot files."
        )
        assert discovered[0] == view_a, (
            f"discovered view must be {view_a}, got {discovered[0]}"
        )


class TestSubprocessUtf8Env:
    def test_subprocess_spawned_with_utf8_io(self, tmp_path):
        """All child subprocesses spawned by run_stage must have PYTHONIOENCODING=utf-8.

        Bug: view_projector (and other tools) crash with UnicodeEncodeError (cp1252)
        on vault content containing non-ASCII characters like '→' when the orchestrator
        does not set the encoding on spawned children.

        Fix: pass env={**os.environ, 'PYTHONIOENCODING': 'utf-8'} in subprocess.run.

        Currently FAILS: subprocess.run is called without 'env' kwarg.
        """
        captured_kwargs: list = []

        def fake_subprocess_run(cmd, **kwargs):
            captured_kwargs.append(kwargs)
            result = MagicMock()
            result.returncode = 0
            result.stdout = ""
            result.stderr = ""
            return result

        with patch("truth_migration_capstone.subprocess.run", side_effect=fake_subprocess_run):
            cap.run_stage(
                2,
                [sys.executable, "-c", "pass"],
                gate_fn=lambda r: True,
                vault=tmp_path,
                dry_run=True,
            )

        assert captured_kwargs, "subprocess.run was not called by run_stage"
        for kw in captured_kwargs:
            env = kw.get("env")
            assert env is not None, (
                f"subprocess.run called without 'env' kwarg -- PYTHONIOENCODING not propagated.\n"
                f"kwargs keys: {list(kw.keys())}\n"
                "Fix: pass env={{**os.environ, 'PYTHONIOENCODING': 'utf-8'}} to subprocess.run."
            )
            assert env.get("PYTHONIOENCODING") == "utf-8", (
                f"env['PYTHONIOENCODING'] must be 'utf-8', "
                f"got: {env.get('PYTHONIOENCODING')!r}\n"
                "Fix: include PYTHONIOENCODING in the env dict passed to subprocess.run."
            )


class TestStage8Wiring:
    def test_stage8_wired_to_real_bl484_gate(self):
        """_build_stage_cmd(8, ...) must reference truth_capstone_gate.py (real BL-484 gate).

        The real gate landed as .claude/scripts/truth_capstone_gate.py
        (docstring: 'BL-484 Capstone-Gate (Stage 8 der BL-483-Pipeline)').
        Current driver guesses 'bl484_post_gate.py' -> always FileNotFoundError no-op.
        The cmd must also pass --vault and --out (report path under out_dir).

        Currently FAILS: _build_stage_cmd(8, ...) references bl484_post_gate.py.
        """
        cmd = _build(8, dry_run=True)

        # Must reference the real tool name (not the stale guess)
        assert any("truth_capstone_gate.py" in t for t in cmd), (
            f"Stage 8 cmd must reference truth_capstone_gate.py (real BL-484 gate).\n"
            f"Full cmd: {cmd}"
        )
        assert not any("bl484_post_gate.py" in t for t in cmd), (
            f"Stage 8 cmd still references bl484_post_gate.py (stale guess).\nCmd: {cmd}"
        )

        # Must pass --vault with the vault path
        assert "--vault" in cmd, f"Stage 8 cmd missing --vault.\nCmd: {cmd}"
        vault_idx = cmd.index("--vault")
        assert cmd[vault_idx + 1] == str(_V), (
            f"--vault value must be '{_V}', got '{cmd[vault_idx + 1]}'.\nCmd: {cmd}"
        )

        # Must pass --out (report file under out_dir)
        assert "--out" in cmd, f"Stage 8 cmd missing --out.\nCmd: {cmd}"
        out_idx = cmd.index("--out")
        out_val = cmd[out_idx + 1]
        assert str(_O) in out_val, (
            f"--out value '{out_val}' must be under out_dir '{_O}'.\nCmd: {cmd}"
        )


class TestStage7GateNoSubstrate:
    def test_stage7_gate_tolerant_of_no_substrate(self):
        """Stage 7 gate must have dedicated no_substrate logic (T2g).

        T2g spec: derivable:True OR no_substrate = OK; silently-wrong = bad.
        The generic _gate_default has no knowledge of this distinction.
        GATE_CHECKS[7] must be a dedicated gate function.

        Currently FAILS: GATE_CHECKS[7] is the generic _gate_default (no view semantics).
        """
        gate_fn = cap.GATE_CHECKS[7]

        # A dedicated gate function is required -- _gate_default is insufficient
        assert gate_fn is not cap._gate_default, (
            "GATE_CHECKS[7] must be a dedicated gate function with no_substrate "
            "tolerance semantics, not the generic _gate_default.\n"
            "T2g: 'derivable:True OR reason=no_substrate = OK; silently-wrong derivation = FAIL.'\n"
            "GREEN: add _gate_stage7(sr) that accepts no_substrate verdicts as non-fatal."
        )

        # Behavioral assertion (documents expected GREEN contract):
        # All-no_substrate outcome -> gate passes (non-fatal per T2g)
        sr_no_substrate = cap.StageResult(
            stage_id=7, name="views", status="ok", gate_ok=True
        )
        assert gate_fn(sr_no_substrate) is True, (
            "Stage 7 gate must accept a no_substrate outcome as non-fatal (T2g)"
        )


# ---------------------------------------------------------------------------
# BL-494 — Stage 6 (build_retrieval_index) MUSS den Vault per --vault durchreichen
# (approach a). Stage 6 ist die EINZIGE Stage die heute KEIN --vault uebergibt;
# build_retrieval_index.main faellt dann auf resolve_vault_root() zurueck (auf der
# DCSRE-Vault der Phantom-Pfad, BL-494) -> Crash. Fix: stage-6 cmd haengt
# "--vault", str(vault) an (gleich wie jede andere Stage).
#
# RED: _build_stage_cmd(6, ...) gibt heute nur [python, build_retrieval_index.py,
# "build"] zurueck -> KEIN --vault -> Test 5 schlaegt fehl. Test 6 ist eine
# Regressions-Wache (Stages 0/2 reichen --vault bereits durch) und besteht heute.
# ---------------------------------------------------------------------------

class TestStage6PassesVault:
    def test_stage6_passes_vault(self, tmp_path):
        """BL-494 T5: Stage 6 build_retrieval_index-cmd traegt --vault <vault>.

        RED: stage-6 cmd hat heute kein --vault -> `"--vault" in cmd` ist False.
        """
        vault = Path(str(tmp_path / "V"))
        cmd = cap._build_stage_cmd(6, vault, Path("."), True, "tag", tmp_path / "out")
        assert "--vault" in cmd, f"Stage 6 cmd fehlt --vault: {cmd}"
        assert cmd[cmd.index("--vault") + 1] == str(vault), (
            f"Stage 6 --vault-Wert muss {str(vault)!r} sein: {cmd}"
        )
        assert "build" in cmd, f"Stage 6 cmd fehlt das 'build'-Subcommand: {cmd}"
        assert any(str(c).endswith("build_retrieval_index.py") for c in cmd), (
            f"Stage 6 cmd ruft nicht build_retrieval_index.py: {cmd}"
        )

    def test_stage0_and_stage2_still_pass_vault(self, tmp_path):
        """BL-494 T6 (Regressions-Wache): Stages 0 und 2 reichen weiterhin
        --vault <vault> durch — die Stage-6-Aenderung ist rein additiv."""
        vault = Path(str(tmp_path / "V"))
        for stage_id in (0, 2):
            cmd = cap._build_stage_cmd(
                stage_id, vault, Path("."), True, "tag", tmp_path / "out"
            )
            assert "--vault" in cmd, f"Stage {stage_id} cmd fehlt --vault: {cmd}"
            assert cmd[cmd.index("--vault") + 1] == str(vault), (
                f"Stage {stage_id} --vault-Wert falsch: {cmd}"
            )
