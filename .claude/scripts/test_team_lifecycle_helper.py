#!/usr/bin/env python3
"""
pytest tests fuer team_lifecycle_helper.py (BL-164 AK-6).

T1: get_stuck_workers — leeres Team gibt leere Liste zurueck
T2: get_stuck_workers — markierte stuck Workers werden korrekt erkannt
T3: force_skip_worker — entfernt Worker und schreibt WORKER_SHUTDOWN_TIMEOUT-Audit
T4: audit_team_lifecycle — schreibt konformen 6-Feld JSONL-Eintrag
T5: cleanup_team — team ohne Worker gibt EXIT_CLEAN zurueck
T6: register_team_transition — schreibt TEAM_LIFECYCLE-Block und TEAM_TRANSITION-Audit
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

import team_lifecycle_helper as tlh


@pytest.fixture
def temp_teams_dir(tmp_path, monkeypatch):
    """Setzt TEAMS_DIR auf temporaeres Verzeichnis."""
    teams_dir = tmp_path / "teams"
    teams_dir.mkdir()
    monkeypatch.setattr(tlh, "TEAMS_DIR", teams_dir)
    return teams_dir


@pytest.fixture
def temp_audit(tmp_path, monkeypatch):
    """Leitet Audit-Writes in temporaere Datei um."""
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    audit_file = audit_dir / "audit.jsonl"
    monkeypatch.setattr(tlh, "AUDIT_DIR", audit_dir)
    monkeypatch.setattr(tlh, "AUDIT_FILE", audit_file)
    return audit_file


def _make_team(teams_dir: Path, team_name: str, workers: list[dict]) -> Path:
    """Erstellt Team-Config fuer Tests."""
    team_dir = teams_dir / team_name
    team_dir.mkdir(parents=True)
    config = {"name": team_name, "workers": workers}
    config_path = team_dir / "config.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    return config_path


# T1: get_stuck_workers — leeres Team gibt leere Liste zurueck
def test_get_stuck_workers_empty_team(temp_teams_dir):
    _make_team(temp_teams_dir, "test-team-empty", [])
    result = tlh.get_stuck_workers("test-team-empty")
    assert result == [], "Leeres Team sollte keine stuck Workers haben"


# T2: get_stuck_workers — markierte stuck Workers werden korrekt erkannt
def test_get_stuck_workers_detects_stuck(temp_teams_dir):
    workers = [
        {"name": "worker-a", "stuck": True},
        {"name": "worker-b", "stuck": False},
        {"name": "worker-c", "stuck": True},
    ]
    _make_team(temp_teams_dir, "test-team-mixed", workers)
    result = tlh.get_stuck_workers("test-team-mixed")
    assert "worker-a" in result
    assert "worker-c" in result
    assert "worker-b" not in result
    assert len(result) == 2


# T3: force_skip_worker — entfernt Worker und schreibt WORKER_SHUTDOWN_TIMEOUT-Audit
def test_force_skip_worker_removes_and_audits(temp_teams_dir, temp_audit):
    workers = [
        {"name": "worker-stuck"},
        {"name": "worker-ok"},
    ]
    _make_team(temp_teams_dir, "test-team-skip", workers)

    result = tlh.force_skip_worker("test-team-skip", "worker-stuck", "Kein ACK nach 120s")

    assert result is True

    # Worker wurde aus Config entfernt
    config = tlh._read_team_config("test-team-skip")
    worker_names = [w["name"] for w in config["workers"]]
    assert "worker-stuck" not in worker_names
    assert "worker-ok" in worker_names

    # Audit-Event wurde geschrieben
    assert temp_audit.exists()
    lines = temp_audit.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["event"] == "WORKER_SHUTDOWN_TIMEOUT"
    assert "worker-stuck" in entry["target"]
    # 6 Pflichtfelder (INV-ROLL-1)
    for field in ("ts", "event", "tool", "target", "reason", "guard"):
        assert field in entry, f"Pflichtfeld '{field}' fehlt im Audit-Event"


# T4: audit_team_lifecycle — schreibt konformen 6-Feld JSONL-Eintrag
def test_audit_team_lifecycle_6_fields(temp_audit):
    tlh.audit_team_lifecycle(
        "TEAM_DELETED",
        tool="TeamLifecycle",
        target="test-team",
        reason="TEAM_DELETED: Test",
    )

    assert temp_audit.exists()
    lines = temp_audit.read_text(encoding="utf-8").strip().splitlines()
    entry = json.loads(lines[-1])

    for field in ("ts", "event", "tool", "target", "reason", "guard"):
        assert field in entry, f"Pflichtfeld '{field}' fehlt"
    assert entry["event"] == "TEAM_DELETED"
    assert entry["guard"] == "team_lifecycle_helper.py"

    # INV-ROLL-5: sensible Felder werden redacted
    tlh.audit_team_lifecycle(
        "TEST_REDACT",
        tool="TeamLifecycle",
        target="test",
        reason="Test",
        inputs={"token": "abc123", "team_name": "test-team"},
    )
    lines = temp_audit.read_text(encoding="utf-8").strip().splitlines()
    last = json.loads(lines[-1])
    assert last["inputs"]["token"] == "<redacted>"
    assert last["inputs"]["team_name"] == "test-team"


# T5: cleanup_team — team ohne Worker gibt EXIT_CLEAN zurueck
def test_cleanup_team_no_workers_returns_clean(temp_teams_dir, temp_audit):
    _make_team(temp_teams_dir, "test-team-noworkers", [])
    result = tlh.cleanup_team("test-team-noworkers", shutdown_timeout_sec=1)
    assert result == tlh.EXIT_CLEAN

    # Audit-Event TEAM_DELETED wurde geschrieben
    lines = temp_audit.read_text(encoding="utf-8").strip().splitlines()
    events = [json.loads(l)["event"] for l in lines]
    assert "TEAM_DELETED" in events


# T5b: cleanup_team — nicht-existentes Team gibt EXIT_FATAL zurueck
def test_cleanup_team_nonexistent_returns_fatal(temp_teams_dir, temp_audit):
    result = tlh.cleanup_team("nonexistent-team", shutdown_timeout_sec=1)
    assert result == tlh.EXIT_FATAL


# T6: register_team_transition — schreibt TEAM_LIFECYCLE-Block und Audit
def test_register_team_transition_writes_block_and_audit(tmp_path, temp_audit):
    manifest_path = tmp_path / "_manifest.md"
    manifest_path.write_text("# Manifest\n\nstatus: active\n", encoding="utf-8")

    result = tlh.register_team_transition(
        from_stage="A",
        to_stage="IDF",
        manifest_path=str(manifest_path),
    )

    assert result is True

    content = manifest_path.read_text(encoding="utf-8")
    assert "TEAM_LIFECYCLE" in content
    assert "IDF" in content
    assert "from: A" in content

    # Audit-Event
    lines = temp_audit.read_text(encoding="utf-8").strip().splitlines()
    events = {json.loads(l)["event"] for l in lines}
    assert "TEAM_TRANSITION" in events
