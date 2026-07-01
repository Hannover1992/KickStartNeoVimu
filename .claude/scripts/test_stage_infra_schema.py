"""
test_stage_infra_schema.py — Tests fuer AK-4 Prozess-Infra-Schema (BL-329 batch_2).

Der Normalisierer nimmt einen stage_N.md setup.commands-Eintrag (String ODER dict)
und gibt ein normalisiertes {cmd, cwd, background, pid_capture} zurueck.

KERN-CONTRACT (ABWAERTSKOMPATIBEL): ein nackter String = heutige Semantik
(run-to-completion: background=False, foreground; cwd=None=default;
pid_capture=False). Voll-dict wird durchgereicht. None/leer wird tolerant
behandelt.

Lauf (beide cwds, BL-336-Lehre):
  py -3 -m pytest .claude/scripts/test_stage_infra_schema.py        (repo-root)
  py -3 -m pytest test_stage_infra_schema.py                        (scripts-cwd)
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Lauffaehig aus repo-root ODER scripts-dir (BL-336: BEIDE cwds pruefen).
sys.path.insert(0, str(Path(__file__).parent))

from stage_infra_schema import (
    NormalizedCommand,
    normalize_setup_command,
    normalize_setup_commands,
)

# ---------------------------------------------------------------------------
# AK-4 Kern: nackter String -> Default-dict (Abwaertskompat)
# ---------------------------------------------------------------------------


def test_bare_string_to_defaults() -> None:
    """Nackter String = heutige Semantik: foreground, run-to-completion, cwd=default."""
    nc = normalize_setup_command("docker-compose up -d")
    assert nc.cmd == "docker-compose up -d"
    assert nc.cwd is None  # default-cwd
    assert nc.background is False  # foreground (run-to-completion)
    assert nc.pid_capture is False


def test_bare_string_with_whitespace_preserved() -> None:
    """Der Befehl wird NICHT veraendert (kein trim, kein re-quote) — Abwaertskompat."""
    cmd = '  powershell .claude/scripts/Wait-ForHealthCheck.ps1 -Url "https://x"  '
    nc = normalize_setup_command(cmd)
    assert nc.cmd == cmd


# ---------------------------------------------------------------------------
# AK-4: voll-dict durchgereicht
# ---------------------------------------------------------------------------


def test_full_dict_passthrough() -> None:
    """Voll-dict mit allen Feldern wird unveraendert durchgereicht."""
    entry = {
        "cmd": "dotnet run --project src/WebHost",
        "cwd": "src/WebHost",
        "background": True,
        "pid_capture": True,
    }
    nc = normalize_setup_command(entry)
    assert nc.cmd == "dotnet run --project src/WebHost"
    assert nc.cwd == "src/WebHost"
    assert nc.background is True
    assert nc.pid_capture is True


def test_partial_dict_fills_defaults() -> None:
    """Teil-dict (nur cmd) -> fehlende Felder Default (background/pid_capture=False, cwd=None)."""
    nc = normalize_setup_command({"cmd": "npm run dev"})
    assert nc.cmd == "npm run dev"
    assert nc.cwd is None
    assert nc.background is False
    assert nc.pid_capture is False


# ---------------------------------------------------------------------------
# AK-4: WebHost-Klasse (background + pid_capture)
# ---------------------------------------------------------------------------


def test_webhost_background_pid_capture() -> None:
    """Prozess-Klasse: lokaler WebHost via background-Start + PID-Capture."""
    entry = {
        "cmd": "dotnet run --urls https://localhost:5443",
        "cwd": "src/Api",
        "background": True,
        "pid_capture": True,
    }
    nc = normalize_setup_command(entry)
    assert nc.background is True
    assert nc.pid_capture is True
    # Teardown-Relevanz: pid_capture impliziert "Teardown killt diese PID"
    assert nc.expects_pid_kill() is True


def test_foreground_command_no_pid_kill() -> None:
    """run-to-completion (foreground, kein pid_capture) -> Teardown killt NICHTS."""
    nc = normalize_setup_command("docker-compose up -d")
    assert nc.expects_pid_kill() is False


# ---------------------------------------------------------------------------
# AK-4: leere/None-Toleranz
# ---------------------------------------------------------------------------


def test_none_entry_tolerated() -> None:
    """None-Eintrag -> None (Skip-Signal), kein Crash."""
    assert normalize_setup_command(None) is None


def test_empty_string_tolerated() -> None:
    """Leerer/whitespace-only String -> None (Skip-Signal)."""
    assert normalize_setup_command("") is None
    assert normalize_setup_command("   ") is None


def test_empty_dict_without_cmd_tolerated() -> None:
    """dict ohne cmd (oder leerer cmd) -> None (Skip-Signal, kein Crash)."""
    assert normalize_setup_command({}) is None
    assert normalize_setup_command({"cwd": "x", "background": True}) is None
    assert normalize_setup_command({"cmd": ""}) is None


# ---------------------------------------------------------------------------
# AK-4: Listen-Normalisierung (normalize_setup_commands)
# ---------------------------------------------------------------------------


def test_list_mixed_string_and_dict() -> None:
    """Liste aus nackten Strings UND dicts -> Liste normalisierter Eintraege."""
    raw = [
        "docker-compose up -d",
        {"cmd": "dotnet run", "background": True, "pid_capture": True},
        "powershell Wait-ForHealthCheck.ps1",
    ]
    out = normalize_setup_commands(raw)
    assert len(out) == 3
    assert out[0].background is False
    assert out[1].background is True
    assert out[1].pid_capture is True
    assert out[2].cmd == "powershell Wait-ForHealthCheck.ps1"


def test_list_skips_empty_and_none() -> None:
    """Leere/None-Eintraege in der Liste werden uebersprungen (kein None im Output)."""
    raw = ["docker up", None, "", {"cmd": ""}, {"cmd": "real"}]
    out = normalize_setup_commands(raw)
    assert [nc.cmd for nc in out] == ["docker up", "real"]


def test_list_none_or_empty_returns_empty() -> None:
    """None oder leere Liste -> leere Liste (kein Crash)."""
    assert normalize_setup_commands(None) == []
    assert normalize_setup_commands([]) == []


# ---------------------------------------------------------------------------
# AK-4: Type-Robustheit (background/pid_capture truthy-Normalisierung)
# ---------------------------------------------------------------------------


def test_background_truthy_normalized_to_bool() -> None:
    """background/pid_capture werden zu echtem bool normalisiert (truthy-tolerant)."""
    nc = normalize_setup_command({"cmd": "x", "background": "true", "pid_capture": 1})
    assert nc.background is True
    assert nc.pid_capture is True
    nc2 = normalize_setup_command({"cmd": "x", "background": "false", "pid_capture": 0})
    # explizite falsy-Strings/0 -> False
    assert nc2.background is False
    assert nc2.pid_capture is False


def test_cwd_blank_normalized_to_none() -> None:
    """Leerer cwd-String -> None (default), nicht ein leerer Pfad."""
    nc = normalize_setup_command({"cmd": "x", "cwd": "   "})
    assert nc.cwd is None


def test_to_dict_roundtrip() -> None:
    """NormalizedCommand.to_dict() liefert das kanonische 4-Feld-dict."""
    nc = normalize_setup_command({"cmd": "x", "cwd": "d", "background": True, "pid_capture": True})
    assert nc.to_dict() == {
        "cmd": "x",
        "cwd": "d",
        "background": True,
        "pid_capture": True,
    }
