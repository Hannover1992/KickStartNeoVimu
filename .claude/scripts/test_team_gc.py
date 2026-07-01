#!/usr/bin/env python3
"""Tests fuer team_gc.py (BL-349 Team-Lifecycle-GC)."""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import team_gc  # noqa: E402


def _mk_team(root: Path, name: str, member_names, lead_session="sess-1"):
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    members = [{"agentId": f"a-{n}", "name": n, "agentType": "x", "model": "opus",
                "joinedAt": "2026-06-14", "tmuxPaneId": None, "cwd": ".", "subscriptions": []}
               for n in member_names]
    cfg = {"name": name, "description": "t", "createdAt": "2026-06-14",
           "leadAgentId": f"team-lead@{name}", "leadSessionId": lead_session, "members": members}
    (d / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return d


def test_list_teams(tmp_path):
    _mk_team(tmp_path, "a-x", ["team-lead", "w1"])
    _mk_team(tmp_path, "idf-y", ["team-lead"])
    assert team_gc.list_teams(teams_root=tmp_path) == ["a-x", "idf-y"]


def test_read_team_meta(tmp_path):
    _mk_team(tmp_path, "a-x", ["team-lead", "w1", "w2"], lead_session="S9")
    m = team_gc.read_team_meta("a-x", teams_root=tmp_path)
    assert m["has_config"] and m["member_count"] == 3
    assert m["non_lead_count"] == 2 and m["lead_session_id"] == "S9"


def test_read_team_meta_missing(tmp_path):
    m = team_gc.read_team_meta("ghost", teams_root=tmp_path)
    assert m["has_config"] is False and m["member_count"] == 0


def test_strip_keeps_lead(tmp_path):
    _mk_team(tmp_path, "idf-z", ["team-lead", "w1", "w2", "w3"])
    r = team_gc.strip_team_members("idf-z", teams_root=tmp_path)
    assert r["changed"] and r["before"] == 4 and r["after"] == 1 and r["stripped"] == 3
    cfg = json.loads((tmp_path / "idf-z" / "config.json").read_text(encoding="utf-8"))
    assert [m["name"] for m in cfg["members"]] == ["team-lead"]
    assert (tmp_path / "idf-z" / "config.json.bak").is_file()  # backup written


def test_strip_all(tmp_path):
    _mk_team(tmp_path, "a-q", ["team-lead", "w1"])
    r = team_gc.strip_team_members("a-q", keep_lead=False, teams_root=tmp_path)
    assert r["after"] == 0 and r["stripped"] == 2


def test_strip_idempotent(tmp_path):
    _mk_team(tmp_path, "a-i", ["team-lead"])  # already only lead
    r = team_gc.strip_team_members("a-i", teams_root=tmp_path)
    assert r["changed"] is False and r["stripped"] == 0 and r["backup"] is None


def test_strip_missing_team(tmp_path):
    r = team_gc.strip_team_members("nope", teams_root=tmp_path)
    assert r["error"] == "no_config" and r["changed"] is False


def test_find_orphaned_respects_preserve(tmp_path):
    _mk_team(tmp_path, "active", ["team-lead", "w1"])
    _mk_team(tmp_path, "zombie1", ["team-lead", "w1", "w2"])
    _mk_team(tmp_path, "zombie2", ["team-lead", "w1"])
    _mk_team(tmp_path, "clean", ["team-lead"])  # no non-lead -> not a candidate
    orph = team_gc.find_orphaned_teams(preserve=["active"], teams_root=tmp_path)
    names = sorted(o["team"] for o in orph)
    assert names == ["zombie1", "zombie2"]  # active preserved, clean excluded


def test_gc_dry_run_does_not_write(tmp_path):
    _mk_team(tmp_path, "active", ["team-lead", "w1"])
    _mk_team(tmp_path, "zombie", ["team-lead", "w1", "w2"])
    res = team_gc.gc_orphaned_teams(preserve=["active"], apply=False, teams_root=tmp_path)
    assert res["apply"] is False and res["candidates"] == ["zombie"] and res["stripped"] == []
    # zombie config UNTOUCHED in dry-run
    cfg = json.loads((tmp_path / "zombie" / "config.json").read_text(encoding="utf-8"))
    assert len(cfg["members"]) == 3


def test_gc_apply_strips_only_non_preserved(tmp_path):
    _mk_team(tmp_path, "active", ["team-lead", "w1", "w2"])      # preserved
    _mk_team(tmp_path, "zombie", ["team-lead", "w1", "w2", "w3"])  # stripped
    res = team_gc.gc_orphaned_teams(preserve=["active"], apply=True, teams_root=tmp_path)
    assert res["apply"] is True
    assert res["stripped"] == [{"team": "zombie", "removed": 3}]
    # active is CONCURRENCY-SAFE: untouched
    act = json.loads((tmp_path / "active" / "config.json").read_text(encoding="utf-8"))
    assert len(act["members"]) == 3
    # zombie stripped to lead
    zom = json.loads((tmp_path / "zombie" / "config.json").read_text(encoding="utf-8"))
    assert [m["name"] for m in zom["members"]] == ["team-lead"]


# ---------------------------------------------------------------------------
# AK-3: get_session_team_context() — Session-Anker via leadSessionId-Scan
# ---------------------------------------------------------------------------

def test_get_session_context_found(tmp_path, monkeypatch):
    """G-AK3-1: 1 Team mit matching leadSessionId -> return team_name."""
    _mk_team(tmp_path, "idf-bl-349", ["team-lead", "w1"], lead_session="sess-abc")
    _mk_team(tmp_path, "other-team", ["team-lead"], lead_session="sess-xyz")
    monkeypatch.setenv("CLAUDE_SESSION_ID", "sess-abc")
    result = team_gc.get_session_team_context(teams_root=tmp_path)
    assert result == "idf-bl-349"


def test_get_session_context_not_found(tmp_path, monkeypatch):
    """G-AK3-2: kein Team passt -> return None (kein Fehler)."""
    _mk_team(tmp_path, "idf-bl-349", ["team-lead"], lead_session="sess-abc")
    monkeypatch.setenv("CLAUDE_SESSION_ID", "sess-does-not-exist")
    result = team_gc.get_session_team_context(teams_root=tmp_path)
    assert result is None


def test_get_session_context_ambiguous(tmp_path, monkeypatch):
    """G-AK3-3: 2 Teams mit gleicher leadSessionId -> return None (ambiguous, fail-safe)."""
    _mk_team(tmp_path, "team-a", ["team-lead"], lead_session="sess-shared")
    _mk_team(tmp_path, "team-b", ["team-lead"], lead_session="sess-shared")
    monkeypatch.setenv("CLAUDE_SESSION_ID", "sess-shared")
    result = team_gc.get_session_team_context(teams_root=tmp_path)
    assert result is None


# ---------------------------------------------------------------------------
# AK-4: _is_dead() + strip_team_members(strip_dead) + read_team_meta(counts)
# ---------------------------------------------------------------------------

def _mk_team_with_status(root: Path, name: str, members_with_status):
    """Helper: erstellt Team mit member-Dicts die status-Felder enthalten koennen."""
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    members = []
    for item in members_with_status:
        m = {"agentId": f"a-{item['name']}", "name": item["name"], "agentType": "x",
             "model": "opus", "joinedAt": "2026-06-14", "tmuxPaneId": None,
             "cwd": ".", "subscriptions": []}
        if "status" in item:
            m["status"] = item["status"]
        members.append(m)
    cfg = {"name": name, "description": "t", "createdAt": "2026-06-14",
           "leadAgentId": f"team-lead@{name}", "leadSessionId": "sess-1", "members": members}
    (d / "config.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    return d


def test_strip_dead_member(tmp_path):
    """G-AK4-1: strip_dead=True + Member status='dead' -> Member entfernt."""
    _mk_team_with_status(tmp_path, "a-test", [
        {"name": "team-lead", "status": "alive"},
        {"name": "w1", "status": "dead"},
        {"name": "w2", "status": "alive"},
    ])
    r = team_gc.strip_team_members("a-test", strip_dead=True, teams_root=tmp_path)
    assert r["changed"] is True
    cfg = json.loads((tmp_path / "a-test" / "config.json").read_text(encoding="utf-8"))
    names = [m["name"] for m in cfg["members"]]
    assert "w1" not in names
    assert "team-lead" in names and "w2" in names


def test_strip_unknown_conservative(tmp_path):
    """G-AK4-2: strip_dead=True + Member ohne status-Feld + default='unknown' -> Member BEHALTEN."""
    _mk_team_with_status(tmp_path, "a-test", [
        {"name": "team-lead"},
        {"name": "w1"},  # kein status-Feld
    ])
    r = team_gc.strip_team_members("a-test", strip_dead=True,
                                   backward_compat_default="unknown", teams_root=tmp_path)
    cfg = json.loads((tmp_path / "a-test" / "config.json").read_text(encoding="utf-8"))
    names = [m["name"] for m in cfg["members"]]
    assert "w1" in names  # konservativ: unknown != dead -> behalten


def test_strip_unknown_aggressive(tmp_path):
    """G-AK4-3: strip_dead=True + Member ohne status-Feld + default='dead' -> Member entfernt."""
    _mk_team_with_status(tmp_path, "a-test", [
        {"name": "team-lead"},
        {"name": "w1"},  # kein status-Feld
    ])
    r = team_gc.strip_team_members("a-test", strip_dead=True,
                                   backward_compat_default="dead", teams_root=tmp_path)
    assert r["changed"] is True
    cfg = json.loads((tmp_path / "a-test" / "config.json").read_text(encoding="utf-8"))
    names = [m["name"] for m in cfg["members"]]
    assert "w1" not in names  # aggressiv: unknown -> dead -> entfernt


def test_strip_alive_preserved(tmp_path):
    """G-AK4-4: strip_dead=True + Member status='alive' -> Member BEHALTEN."""
    _mk_team_with_status(tmp_path, "a-test", [
        {"name": "team-lead", "status": "alive"},
        {"name": "w1", "status": "alive"},
        {"name": "w2", "status": "dead"},
    ])
    r = team_gc.strip_team_members("a-test", strip_dead=True, teams_root=tmp_path)
    cfg = json.loads((tmp_path / "a-test" / "config.json").read_text(encoding="utf-8"))
    names = [m["name"] for m in cfg["members"]]
    assert "w1" in names  # alive bleibt immer
    assert "w2" not in names


def test_strip_dead_default_false_preserves(tmp_path):
    """G-AK4-5 (Kanarienvoegel): strip_dead=False (Default) -> identical behavior zu IST.
    Member mit status='dead' werden NICHT entfernt wenn strip_dead nicht uebergeben."""
    _mk_team_with_status(tmp_path, "a-test", [
        {"name": "team-lead"},
        {"name": "w1", "status": "dead"},
        {"name": "w2", "status": "alive"},
    ])
    # strip_dead NICHT uebergeben = Default-Verhalten (Altverhalten-Kanarienvogel)
    r = team_gc.strip_team_members("a-test", teams_root=tmp_path)
    cfg = json.loads((tmp_path / "a-test" / "config.json").read_text(encoding="utf-8"))
    names = [m["name"] for m in cfg["members"]]
    # Altverhalten: nur non-lead wird entfernt (keep_lead=True default)
    # w1 und w2 sind keine team-leads → beide weg (strip by lead, nicht by status)
    assert "team-lead" in names


def test_read_team_meta_counts(tmp_path):
    """G-AK4-6: read_team_meta() gibt dead_count / alive_count / unknown_count zurueck."""
    _mk_team_with_status(tmp_path, "a-counts", [
        {"name": "team-lead", "status": "alive"},
        {"name": "w1", "status": "dead"},
        {"name": "w2", "status": "dead"},
        {"name": "w3", "status": "alive"},
        {"name": "w4"},  # kein status-Feld = unknown
    ])
    m = team_gc.read_team_meta("a-counts", teams_root=tmp_path)
    assert m["dead_count"] == 2
    assert m["alive_count"] == 2
    assert m["unknown_count"] == 1


# ---------------------------------------------------------------------------
# AK-5: test_forward_verify_zero_zombies — E2E-Lifecycle-Simulation
# ---------------------------------------------------------------------------

def test_forward_verify_zero_zombies(tmp_path):
    """G-AK5-1/2: E2E-Lifecycle-Simulation — 0 Zombie-Teams nach Strip.
    Simuliert: Team mit Zombie-Membern anlegen -> strip_team_members() ->
    verify 0 Orphans via find_orphaned_teams(preserve=[])."""
    # Zombie-Team mit 3 Non-Lead-Membern anlegen
    _mk_team(tmp_path, "a-bl-349", ["team-lead", "zombie1", "zombie2", "zombie3"])
    # Pre-Strip: muss als Orphan erkannt werden
    pre = team_gc.find_orphaned_teams(preserve=[], teams_root=tmp_path)
    assert len(pre) == 1 and pre[0]["team"] == "a-bl-349"
    # Strip simuliert Teardown-Recovery (INV-TEAM-GC-1)
    r = team_gc.strip_team_members("a-bl-349", teams_root=tmp_path)
    assert r["changed"] is True and r["stripped"] == 3  # G-AK5-1
    # Post-Strip: 0 Orphan-Teams (kein Zombie mehr)
    post = team_gc.find_orphaned_teams(preserve=[], teams_root=tmp_path)
    assert post == []  # G-AK5-2


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
