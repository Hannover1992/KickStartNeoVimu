#!/usr/bin/env python3
"""
pytest tests fuer guard_session_params_protection.py — Param-Mutation-Guard (BL-159 AK-5).
5 Test-Cases: T1-T5 per Ring-Plan (T5->T3->T2->T1->T4).

Tests pruefen das Ownership-Semantik-Modell:
  - _owner=user Parameter MUESSEN durch Worker-Kontext geblockt werden
  - _owner=system / kein _owner darf NICHT geblockt werden
  - Non-Worker-Kontext darf _owner=user Parameter schreiben
  - Non-_param Skill wird immer durchgelassen
  - Block-Event muss in audit.jsonl als PARAM_MUTATION_BLOCKED erscheinen
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_session_params_protection.py"


def run_guard(tool_name: str, tool_input: dict, env_extra: dict = None) -> dict:
    """Ruft guard_session_params_protection.py mit simuliertem Hook-Input auf."""
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    hook_data = {"tool_name": tool_name, "tool_input": tool_input}
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(hook_data),
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    try:
        return json.loads(proc.stdout.strip())
    except Exception:
        return {"continue": True, "_parse_error": proc.stdout}


# T5 — Non-_param Skill passthrough (Ring 1, einfachster Test)
def test_non_param_skill_passthrough():
    """Skill(_BDF_orchestrate) -> immer continue=true (Guard nur fuer _param)."""
    result = run_guard(
        tool_name="Skill",
        tool_input={"skill_name": "_BDF_orchestrate", "args": ""},
    )
    assert result["continue"] is True, f"Expected passthrough for non-_param skill, got: {result}"


# T3 — Non-Worker-Kontext darf _owner=user Parameter schreiben (Ring 2)
def test_non_worker_user_owned_param_allowed():
    """Non-Worker-Kontext (leerer agent_name) + _owner=user Parameter -> continue=true.

    Wenn kein Worker-Kontext erkannt wird (z.B. Team-Lead selbst), darf auch
    _owner=user Parameter geaendert werden — safe default, kein False-Positive.
    """
    result = run_guard(
        tool_name="Skill",
        tool_input={
            "skill_name": "_param",
            "args": "hil=off",
            "_owner": "user",
            "_caller_context": "",
        },
        env_extra={"OMNI_AGENT_NAME": ""},
    )
    assert result["continue"] is True, f"Expected allow for non-worker context, got: {result}"


# T2 — Worker + Parameter ohne _owner (system) erlaubt (Ring 3)
def test_writer_whitelist_system_param_allowed():
    """Worker-Kontext + Parameter ohne _owner (Fallback=system) -> continue=true (kein Block).

    Worker darf system-eigene Parameter selbst aendern (z.B. dark_factory).
    """
    result = run_guard(
        tool_name="Skill",
        tool_input={
            "skill_name": "_param",
            "args": "dark_factory=true",
        },
        env_extra={"OMNI_AGENT_NAME": "general-sonnet-worker"},
    )
    assert result["continue"] is True, f"Expected allow for system param, got: {result}"


# T1 — Worker + _owner=user Parameter geblockt (Ring 4, Core-Test)
def test_worker_blocked_user_owned_param():
    """Worker-Agent-Name-Suffix + _owner=user Parameter -> continue=false, PARAM_MUTATION_BLOCKED.

    F90-Reproduktion: BDF-Worker setzt /_param dark_factory=true und
    mutiert implizit hil=phase -> hil=off. Guard muss das blocken.
    """
    result = run_guard(
        tool_name="Skill",
        tool_input={
            "skill_name": "_param",
            "args": "hil=off",
            "_owner": "user",
        },
        env_extra={"OMNI_AGENT_NAME": "general-sonnet-worker", "OMNI_ENFORCE_PARAM_GUARD": "1"},
    )
    assert result["continue"] is False, f"Expected block for user-owned param, got: {result}"
    msg = result.get("message", "")
    assert "PARAM_MUTATION_BLOCKED" in msg, f"Expected PARAM_MUTATION_BLOCKED in message, got: {msg}"


# T4 — Block-Event in audit.jsonl (Ring 5, Audit-Trail)
def test_audit_logged_on_block():
    """Block-Event -> audit.jsonl enthaelt PARAM_MUTATION_BLOCKED mit Pflichtfeldern.

    Pflichtfelder: event, ts, param_name, attempted_value, blocker
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        audit_path = Path(tmpdir) / "audit.jsonl"
        result = run_guard(
            tool_name="Skill",
            tool_input={
                "skill_name": "_param",
                "args": "hil=off",
                "_owner": "user",
            },
            env_extra={
                "OMNI_AGENT_NAME": "general-sonnet-worker",
                "OMNI_ENFORCE_PARAM_GUARD": "1",
                "OMNI_AUDIT_JSONL_PATH": str(audit_path),
            },
        )
        # Guard should have blocked
        assert result["continue"] is False, f"Expected block, got: {result}"

        # Audit file should have been written
        assert audit_path.exists(), f"Expected audit.jsonl at {audit_path}, not found"

        lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 1, f"Expected at least 1 audit entry, got: {lines}"

        last_entry = json.loads(lines[-1])
        assert last_entry.get("event") == "PARAM_MUTATION_BLOCKED", f"Wrong event: {last_entry}"
        for field in ("ts", "param_name", "attempted_value", "blocker"):
            assert field in last_entry, f"Missing audit field '{field}': {last_entry}"
