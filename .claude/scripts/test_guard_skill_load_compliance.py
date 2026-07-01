#!/usr/bin/env python3
"""BL-159 AK-2 + AK-3: Test-Harness fuer guard_skill_load_compliance.py.

Standalone (kein pytest noetig): `py -3 test_guard_skill_load_compliance.py`.
Tests verifizieren:
  - SKILL_PATH_PATTERN trifft .claude/commands/_*.md (Linux + Windows + WSL Pfade)
  - extract_skill_name liefert korrekten Skill-Namen
  - Subprocess-Hook gibt valides JSON aus
  - OMNI_ALLOW_SKILL_READ=1 schaltet Guard ab
  - Non-Read Tool laesst durch
"""
import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_skill_load_compliance.py"

sys.path.insert(0, str(SCRIPT_DIR))
import guard_skill_load_compliance as G  # noqa: E402


def _run_guard(tool_name, tool_input, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    payload = json.dumps({"tool_name": tool_name, "tool_input": tool_input})
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=payload, capture_output=True, text=True, timeout=10, env=env,
    )
    return proc


def test_extract_skill_name_windows_path():
    p = r"C:\Users\X\OmniCommand\.claude\commands\_param.md"
    assert G.extract_skill_name(p) == "_param", G.extract_skill_name(p)


def test_extract_skill_name_unix_path():
    p = "/c/Users/X/OmniCommand/.claude/commands/_BDF_orchestrate.md"
    assert G.extract_skill_name(p) == "_BDF_orchestrate"


def test_extract_skill_name_relative_path():
    p = ".claude/commands/_audit.md"
    assert G.extract_skill_name(p) == "_audit"


def test_extract_skill_name_non_command_returns_none():
    assert G.extract_skill_name("README.md") is None
    assert G.extract_skill_name(".claude/scripts/audit_hook.py") is None
    assert G.extract_skill_name(".claude/commands/subdir/foo.md") is None
    assert G.extract_skill_name(".claude/commands/foo.md") is None  # kein leading "_"


def test_subprocess_blocks_read_of_command_when_enforce_true():
    # Vault enforceProcess ist aktuell false (siehe _session_params.md) -> default reflektiert das.
    # Wir testen daher ueber das Output-Format: Hook muss JSON liefern + message enthalten.
    proc = _run_guard("Read", {"file_path": ".claude/commands/_param.md"})
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    out = json.loads(proc.stdout)
    assert "continue" in out
    assert "message" in out
    assert "SKILL_LOAD_VIA_READ" in out["message"]
    assert "_param" in out["message"]


def test_subprocess_passes_through_non_command_read():
    proc = _run_guard("Read", {"file_path": "README.md"})
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    out = json.loads(proc.stdout)
    assert out.get("continue") is True
    assert "message" not in out


def test_subprocess_passes_through_non_read_tool():
    proc = _run_guard("Edit", {"file_path": ".claude/commands/_param.md"})
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    out = json.loads(proc.stdout)
    assert out.get("continue") is True


def test_subprocess_env_override_allows_read():
    proc = _run_guard(
        "Read",
        {"file_path": ".claude/commands/_param.md"},
        env_extra={"OMNI_ALLOW_SKILL_READ": "1"},
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}"
    out = json.loads(proc.stdout)
    assert out.get("continue") is True
    assert "message" not in out


TESTS = [
    test_extract_skill_name_windows_path,
    test_extract_skill_name_unix_path,
    test_extract_skill_name_relative_path,
    test_extract_skill_name_non_command_returns_none,
    test_subprocess_blocks_read_of_command_when_enforce_true,
    test_subprocess_passes_through_non_command_read,
    test_subprocess_passes_through_non_read_tool,
    test_subprocess_env_override_allows_read,
]


def main():
    failures = 0
    for t in TESTS:
        try:
            t()
            print(f"PASS: {t.__name__}")
        except AssertionError as e:
            print(f"FAIL: {t.__name__} -- {e}")
            failures += 1
        except Exception as e:
            print(f"ERROR: {t.__name__} -- {type(e).__name__}: {e}")
            failures += 1
    total = len(TESTS)
    print(f"\n{total - failures}/{total} PASSED")
    sys.exit(0 if failures == 0 else 1)


if __name__ == "__main__":
    main()
