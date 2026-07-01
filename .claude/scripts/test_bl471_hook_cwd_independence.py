"""
BL-471 RED-Tests: Hook-Commands cwd-Unabhaengigkeit via $CLAUDE_PROJECT_DIR.

RED-Hebel (muessen jetzt FAILEN — IST-Stand: alle 56 bare-relativ, Recovery-Doku fehlt):
- test_all_commands_project_dir_prefixed: 0/56 praefixiert -> FAIL
- test_no_bare_relative_script_path: 56 bare-Treffer -> FAIL
- test_args_preserved: kombinierter Praefix+Arg-Assert -> FAIL (Praefix fehlt)
- test_recovery_doku_exists: Recovery-Abschnitt fehlt in _worktree_parallel.md -> FAIL

Kanarien / Regression-Floors (muessen JETZT SCHON passen — bleiben GREEN durch GREEN-Bau):
- test_command_count_56: 56 commands gesamt
- test_all_matchers_present: matcher-Menge unveraendert
- test_json_valid: settings.json parst
- test_hook_event_types: PreToolUse/PostToolUse/Stop/Notification

Behavioral-Tests (SELF-CONTAINED via tmp_path — testen das Prinzip, NICHT den IST-settings.json-Zustand):
- test_bare_relative_fails_from_subdir: reproduziert den Lockout-Defekt (AK-2, Mechanismus-Beweis)
- test_abs_resolves_from_subdir: belegt den Fix via absolutem Pfad (AK-2, Mechanismus-Beweis)
- test_dollar_expansion_via_bash: belegt $-Expansion wie echter Hook-Mechanismus (AK-2, Mechanismus-Beweis)

HINWEIS: die 3 behavioral-Tests sind SELF-CONTAINED (tmp_path) und sollten SCHON JETZT passen —
sie testen das Prinzip (Defekt+Fix kontrastiert), NICHT den IST-settings.json-Zustand.
Sie sind der Mechanismus-Beweis (AC-2), KEINE RED-Hebel im settings.json-Sinne.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Pfad-Anker: settings.json + _worktree_parallel.md relativ zu dieser Datei
# (wie test_bl473-Konvention: Path(__file__).parent.parent /.../settings.json)
# ---------------------------------------------------------------------------

_SCRIPTS_DIR = Path(__file__).parent.absolute()
_CLAUDE_DIR = _SCRIPTS_DIR.parent       # .claude/
_REPO_ROOT = _CLAUDE_DIR.parent         # OmniCommand-wtA/
_SETTINGS_JSON = _CLAUDE_DIR / "settings.json"
_WORKTREE_PARALLEL_MD = _CLAUDE_DIR / "commands" / "_worktree_parallel.md"


# ---------------------------------------------------------------------------
# Hilfsfunktion: alle hooks[].command-Strings aus settings.json sammeln
# ---------------------------------------------------------------------------

def _load_all_commands(settings_path: Path) -> list:
    """Walkt PreToolUse/PostToolUse/Stop/Notification -> [].hooks[].command."""
    with open(settings_path, encoding="utf-8") as f:
        data = json.load(f)

    hooks_root = data.get("hooks", {})
    commands = []
    for event_type in ("PreToolUse", "PostToolUse", "Stop", "Notification"):
        blocks = hooks_root.get(event_type, [])
        for block in blocks:
            for hook_entry in block.get("hooks", []):
                cmd = hook_entry.get("command")
                if cmd is not None:
                    commands.append(cmd)
    return commands


# ---------------------------------------------------------------------------
# STRUKTUR-TESTS (RED-Hebel)
# ---------------------------------------------------------------------------

class TestStructuralPrefixAssertions:
    """AK-1: alle 56 Commands muessen $CLAUDE_PROJECT_DIR-praefixiert sein."""

    def test_all_commands_project_dir_prefixed(self):
        """RED-HEBEL: JEDES command das .claude/scripts/ referenziert enthaelt
        '$CLAUDE_PROJECT_DIR/.claude/'. IST: 0/56 praefixiert -> FAIL."""
        commands = _load_all_commands(_SETTINGS_JSON)
        script_commands = [c for c in commands if ".claude/scripts/" in c]
        assert len(script_commands) == 56, (
            f"Erwartet 56 script-commands, got {len(script_commands)}"
        )
        missing_prefix = [c for c in script_commands
                          if "$CLAUDE_PROJECT_DIR/.claude/" not in c]
        assert missing_prefix == [], (
            f"{len(missing_prefix)} Commands ohne $CLAUDE_PROJECT_DIR-Praefix:\n"
            + "\n".join(f"  {c!r}" for c in missing_prefix[:10])
        )

    def test_no_bare_relative_script_path(self):
        """RED-HEBEL: KEIN command matcht bare 'py -3 .claude/scripts/' oder
        'bash .claude/scripts/' (ohne $CLAUDE_PROJECT_DIR-Praefix davor).
        IST: 56 bare-Treffer -> FAIL."""
        commands = _load_all_commands(_SETTINGS_JSON)
        # bare = Interpreter gefolgt von .claude/scripts/ OHNE vorangehendes "$CLAUDE_PROJECT_DIR"
        bare_pattern = re.compile(r'^(?:py -3|bash) \.claude/scripts/')
        bare_hits = [c for c in commands if bare_pattern.search(c)]
        assert bare_hits == [], (
            f"{len(bare_hits)} bare-relative Commands gefunden (erwartet 0):\n"
            + "\n".join(f"  {c!r}" for c in bare_hits[:10])
        )

    def test_no_percent_cmd_form(self):
        """KANARIENVOGEL (heute GREEN, bleibt GREEN): kein Command enthaelt
        '%CLAUDE_PROJECT_DIR%' (cmd-Form verboten, bash-Hook-Shell expandiert $ nicht %)."""
        commands = _load_all_commands(_SETTINGS_JSON)
        percent_hits = [c for c in commands if "%CLAUDE_PROJECT_DIR%" in c]
        assert percent_hits == [], (
            f"Verbotene cmd-%-Form in {len(percent_hits)} Commands:\n"
            + "\n".join(f"  {c!r}" for c in percent_hits)
        )

    def test_args_preserved(self):
        """RED-HEBEL (kombinierter Praefix+Arg-Assert):
        - worktree_hook_router-Command endet auf ' hook'
        - notify_stale Stop-Command endet auf ' stop'
        - notify_stale Notification-Command endet auf ' notification'
        IST: Args zwar da, aber Praefix fehlt -> kombinierter Assert failt."""
        commands = _load_all_commands(_SETTINGS_JSON)

        # worktree_hook_router -> mit arg 'hook'
        router_cmds = [c for c in commands if "worktree_hook_router" in c]
        assert len(router_cmds) >= 1, "worktree_hook_router-Command fehlt"
        router_cmd = router_cmds[0]
        # Muss den $CLAUDE_PROJECT_DIR-Praefix enthalten UND auf ' hook' enden
        assert "$CLAUDE_PROJECT_DIR/.claude/" in router_cmd, (
            f"worktree_hook_router fehlt Praefix: {router_cmd!r}"
        )
        assert router_cmd.endswith(" hook"), (
            f"worktree_hook_router endet nicht auf ' hook': {router_cmd!r}"
        )

        # notify_stale stop
        stop_cmds = [c for c in commands if "notify_stale.sh" in c and c.endswith(" stop")]
        assert len(stop_cmds) >= 1, "notify_stale.sh stop-Command fehlt"
        stop_cmd = stop_cmds[0]
        assert "$CLAUDE_PROJECT_DIR/.claude/" in stop_cmd, (
            f"notify_stale stop fehlt Praefix: {stop_cmd!r}"
        )
        assert stop_cmd.endswith(" stop"), (
            f"notify_stale stop-Command endet nicht auf ' stop': {stop_cmd!r}"
        )

        # notify_stale notification
        notif_cmds = [c for c in commands if "notify_stale.sh" in c and c.endswith(" notification")]
        assert len(notif_cmds) >= 1, "notify_stale.sh notification-Command fehlt"
        notif_cmd = notif_cmds[0]
        assert "$CLAUDE_PROJECT_DIR/.claude/" in notif_cmd, (
            f"notify_stale notification fehlt Praefix: {notif_cmd!r}"
        )
        assert notif_cmd.endswith(" notification"), (
            f"notify_stale notification-Command endet nicht auf ' notification': {notif_cmd!r}"
        )


# ---------------------------------------------------------------------------
# BEHAVIORAL-TESTS (SELF-CONTAINED via tmp_path — Mechanismus-Beweis AC-2)
# HINWEIS: diese Tests sind SELF-CONTAINED und sollten SCHON JETZT passen.
# Sie testen das Prinzip (bare-relativ failt / absolut/expandiert findet),
# NICHT den IST-settings.json-Zustand. Sie sind Mechanismus-Beweis (AC-2).
# ---------------------------------------------------------------------------

@pytest.fixture
def probe_env(tmp_path):
    """Legt ein isoliertes tmp-Verzeichnis mit Probe-Skript an.

    Struktur:
      tmp_path/
        .claude/scripts/probe_ok.py  <- minimales Probe-Skript
        sub/deep/                    <- Unterordner (simuliert cd-Lockout-Situation)
    """
    scripts_dir = tmp_path / ".claude" / "scripts"
    scripts_dir.mkdir(parents=True)

    probe = scripts_dir / "probe_ok.py"
    probe.write_text('import sys\nprint("OK")\nsys.exit(0)\n', encoding="utf-8")

    subdir = tmp_path / "sub" / "deep"
    subdir.mkdir(parents=True)

    return tmp_path, subdir, probe


class TestBehavioralCwdMechanism:
    """AK-2: Behavioral-Beweise — Defekt (bare-relativ) vs. Fix ($-absolut/expandiert).

    Alle 3 Tests sind SELF-CONTAINED via probe_env-Fixture.
    Sie sollten SCHON JETZT passen (Mechanismus-Beweis, kein RED-Hebel im settings.json-Sinne).
    """

    def test_bare_relative_fails_from_subdir(self, probe_env):
        """Mechanismus-Beweis (AC-2): reproduziert den Lockout-Defekt.
        'py -3 .claude/scripts/probe_ok.py' aus einem Unterordner heraus
        findet das Skript NICHT -> returncode != 0 (FileNotFound).
        Dies ist der Defekt den BL-471 behebt."""
        tmp_root, subdir, _ = probe_env
        result = subprocess.run(
            ["py", "-3", ".claude/scripts/probe_ok.py"],
            cwd=str(subdir),
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, (
            f"Erwartet Fehler (FileNotFound aus Unterordner), "
            f"aber rc={result.returncode}, stdout={result.stdout!r}"
        )

    def test_abs_resolves_from_subdir(self, probe_env):
        """Mechanismus-Beweis (AC-2): belegt den Fix via absolutem Pfad.
        'py -3 <absoluter-Pfad>/probe_ok.py' aus dem Unterordner
        findet das Skript -> returncode == 0, stdout 'OK'."""
        tmp_root, subdir, probe = probe_env
        result = subprocess.run(
            ["py", "-3", str(probe)],
            cwd=str(subdir),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Erwartet rc=0 (absoluter Pfad findet Skript), "
            f"rc={result.returncode}, stderr={result.stderr!r}"
        )
        assert "OK" in result.stdout, (
            f"Erwartet 'OK' in stdout, got {result.stdout!r}"
        )

    def test_dollar_expansion_via_bash(self, probe_env):
        """Mechanismus-Beweis (AC-2): belegt $-Expansion = echter Hook-Mechanismus.
        bash -c 'py -3 "$CLAUDE_PROJECT_DIR/.claude/scripts/probe_ok.py"'
        mit env CLAUDE_PROJECT_DIR=<tmp_root> aus Unterordner -> rc==0, stdout 'OK'.

        Wenn bash nicht auffindbar: pytest.skip (nicht fail) — kein bash im PATH."""
        bash_exe = shutil.which("bash")
        if bash_exe is None:
            pytest.skip("bash nicht im PATH — $-Expansion-Test uebersprungen")

        tmp_root, subdir, _ = probe_env
        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(tmp_root)

        result = subprocess.run(
            [bash_exe, "-c", 'py -3 "$CLAUDE_PROJECT_DIR/.claude/scripts/probe_ok.py"'],
            cwd=str(subdir),
            env=env,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"Erwartet rc=0 (bash $-Expansion findet Skript), "
            f"rc={result.returncode}, stderr={result.stderr!r}, stdout={result.stdout!r}"
        )
        assert "OK" in result.stdout, (
            f"Erwartet 'OK' in stdout, got {result.stdout!r}"
        )


# ---------------------------------------------------------------------------
# KANARIEN / REGRESSION-FLOORS (heute GREEN, muessen GREEN bleiben)
# ---------------------------------------------------------------------------

class TestCanaryFloors:
    """AK-3: Immunsystem-Floor — heute GREEN, durch GREEN-Bau NICHT umkippen."""

    def test_json_valid(self):
        """KANARIENVOGEL: settings.json ist valides JSON."""
        with open(_SETTINGS_JSON, encoding="utf-8") as f:
            data = json.load(f)
        assert isinstance(data, dict), "settings.json top-level muss dict sein"

    def test_hook_event_types(self):
        """KANARIENVOGEL: settings.json.hooks enthaelt PreToolUse, PostToolUse,
        Stop, Notification — alle 4 Event-Typen vorhanden."""
        with open(_SETTINGS_JSON, encoding="utf-8") as f:
            data = json.load(f)
        hooks = data.get("hooks", {})
        for event in ("PreToolUse", "PostToolUse", "Stop", "Notification"):
            assert event in hooks, f"Event-Typ '{event}' fehlt in hooks"

    def test_command_count_56(self):
        """KANARIENVOGEL: genau 56 hooks[].command gesamt (54 py + 2 bash)."""
        commands = _load_all_commands(_SETTINGS_JSON)
        assert len(commands) == 56, (
            f"Erwartet 56 commands, got {len(commands)}"
        )

    def test_all_matchers_present(self):
        """KANARIENVOGEL: die Menge der matcher-Strings == die erwartete IST-Menge.
        Hartkodierte EXPECTED-Menge aus dem aktuellen settings.json (2026-06-25).
        Assert: unveraendert nach Bau (nur command-FORM aendert sich, nicht matcher)."""
        with open(_SETTINGS_JSON, encoding="utf-8") as f:
            data = json.load(f)

        hooks_root = data.get("hooks", {})

        # Extrahiere alle matcher-Strings aus allen Event-Typen (None fuer matcher-lose Bloecke)
        found_matchers = []
        for event_type in ("PreToolUse", "PostToolUse", "Stop", "Notification"):
            blocks = hooks_root.get(event_type, [])
            for block in blocks:
                matcher = block.get("matcher")  # None wenn fehlt (Stop/Notification)
                found_matchers.append(matcher)

        # Erwartete IST-Menge (hartkodiert aus settings.json 2026-06-25, Reihenfolge-unabhaengig)
        # PreToolUse: 9 Bloecke mit Matchern
        # PostToolUse: 3 Bloecke mit Matchern
        # Stop: 1 Block ohne matcher (None)
        # Notification: 1 Block ohne matcher (None)
        expected_matchers = [
            # PreToolUse (9 Bloecke)
            "Skill|Agent|TaskCreate|SendMessage|Edit|Write|Read",  # worktree_hook_router + audit_hook
            "Skill|Agent|TaskCreate|SendMessage|Edit|Write|Read",  # audit_hook (2. Block gleicher matcher)
            "Read",
            "Agent|TaskCreate|SendMessage",
            "Skill",
            "Skill|Agent",
            "Agent|Task",
            "Edit|Write",
            "Bash|PowerShell",
            # PostToolUse (3 Bloecke)
            ".*",
            "Skill",
            "Edit|Write",
            # Stop (1 Block, matcher-los)
            None,
            # Notification (1 Block, matcher-los)
            None,
        ]

        assert found_matchers == expected_matchers, (
            f"Matcher-Liste weicht vom IST-Stand ab.\n"
            f"Gefunden: {found_matchers}\n"
            f"Erwartet: {expected_matchers}"
        )


# ---------------------------------------------------------------------------
# AK-4: Recovery-Doku (RED-Hebel — fehlt heute)
# ---------------------------------------------------------------------------

class TestRecoveryDokuExists:
    """AK-4: Recovery-Doku im Engine-Kanon (_worktree_parallel.md)."""

    def test_recovery_doku_exists(self):
        """RED-HEBEL: _worktree_parallel.md enthaelt 'cwd-Lockout' UND 'Session-Neustart'
        (Recovery-Doku). IST: fehlt heute -> FAIL."""
        assert _WORKTREE_PARALLEL_MD.exists(), (
            f"_worktree_parallel.md existiert nicht: {_WORKTREE_PARALLEL_MD}"
        )
        content = _WORKTREE_PARALLEL_MD.read_text(encoding="utf-8")
        assert "cwd-Lockout" in content, (
            "'cwd-Lockout' fehlt in _worktree_parallel.md (Recovery-Abschnitt nicht materialisiert)"
        )
        assert "Session-Neustart" in content, (
            "'Session-Neustart' fehlt in _worktree_parallel.md (Recovery-Abschnitt nicht materialisiert)"
        )
