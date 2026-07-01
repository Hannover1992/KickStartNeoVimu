"""
pytest fuer B4 (Audit 2026-05-29): enforce-gate Self-Unlock geschlossen.

Die Luecke: `enforceProcess` war NICHT im SESSION_PARAM_PATTERN → ein Sub-Agent
konnte `**enforceProcess:** false` in _session_params.md schreiben (ungeblockt),
was via Gate-Inject ALLE Guards inkl. Souveraenitaets-Guards ausschaltete =
agent-erreichbarer Generalschluessel.

Fix B4a: enforceProcess ins SESSION_PARAM_PATTERN (nur /_param darf schreiben).
Fix B4b: Souveraenitaets-Guards (param_writer, hook_prep) haengen NICHT mehr am
         file-enforceProcess-Gate — nur an OMNI_ENFORCE_ALL_OFF + eigenem Env-Hatch.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from _enforce_gate import enforce_active

SCRIPT_DIR = Path(__file__).parent.absolute()
PARAM_GUARD = SCRIPT_DIR / "guard_param_writer_identity.py"
HOOKPREP_GUARD = SCRIPT_DIR / "guard_hook_prep_owner_only.py"


def _run(guard, event, env_extra):
    env = os.environ.copy()
    # pytest-Mode-Maskierung von _enforce_gate vermeiden ist irrelevant hier
    env.update(env_extra)
    r = subprocess.run([sys.executable, str(guard)], input=json.dumps(event),
                       capture_output=True, text=True, env=env)
    return json.loads((r.stdout or "").strip())


# ──────────────────── B4a: enforceProcess-Write-Lock ────────────────────

def test_enforceprocess_write_by_orchestrator_blocked():
    """Sub-Agent (Orchestrator aktiv) schreibt enforceProcess:false -> BLOCK (Self-Unlock zu)."""
    ev = {"tool_name": "Edit", "tool_input": {
        "file_path": "C:/x/.claude/analysis/_session_params.md",
        "new_string": "**enforceProcess:** false"}}
    out = _run(PARAM_GUARD, ev, {"OMNI_PARAM_ACTIVE_SKILL": "_SDF_orchestrate"})
    assert out["continue"] is False, f"Self-Unlock NICHT geschlossen: {out}"


def test_enforceprocess_write_by_param_allowed():
    """/_param darf enforceProcess schreiben (autorisierter Writer)."""
    ev = {"tool_name": "Edit", "tool_input": {
        "file_path": "C:/x/.claude/analysis/_session_params.md",
        "new_string": "**enforceProcess:** false"}}
    out = _run(PARAM_GUARD, ev, {"OMNI_PARAM_ACTIVE_SKILL": "_param"})
    assert out["continue"] is True


def test_enforceprocess_write_human_direct_allowed():
    """Human-Direct (kein Skill aktiv) darf schreiben."""
    ev = {"tool_name": "Edit", "tool_input": {
        "file_path": "C:/x/.claude/analysis/_session_params.md",
        "new_string": "**enforceProcess:** true"}}
    out = _run(PARAM_GUARD, ev, {"OMNI_PARAM_ACTIVE_SKILL": ""})
    assert out["continue"] is True


def test_difficulty_write_by_orchestrator_still_blocked():
    """Regression: difficulty-Write durch Orchestrator bleibt geblockt."""
    ev = {"tool_name": "Edit", "tool_input": {
        "file_path": "C:/x/.claude/analysis/_session_params.md",
        "new_string": "**difficulty:** hard"}}
    out = _run(PARAM_GUARD, ev, {"OMNI_PARAM_ACTIVE_SKILL": "_IDF_orchestrate"})
    assert out["continue"] is False


# ──────────────────── B4b: Souveraenitaets-Guards entkoppelt vom file-Gate ────────────────────

def test_hookprep_still_blocks_agent_despite_enforceprocess_false(tmp_path):
    """hook_prep blockt Sub-Agent-/_hook_workaround AUCH wenn enforceProcess=false
    in der Params-Datei steht (entkoppelt vom file-Gate)."""
    sp = tmp_path / "_session_params.md"
    sp.write_text("**enforceProcess:** false\n", encoding="utf-8")
    ev = {"tool_name": "Skill", "tool_input": {"skill": "_hook_workaround", "args": ""}}
    out = _run(HOOKPREP_GUARD, ev,
               {"OMNI_AGENT_NAME": "idf-validator-r17", "OMNI_SESSION_PARAMS": str(sp)})
    assert out["continue"] is False, f"hook_prep liess Agent durch trotz file-enforceProcess=false: {out}"


def test_paramwriter_still_blocks_despite_enforceprocess_false(tmp_path):
    """param_writer blockt Orchestrator-Write AUCH wenn enforceProcess=false (entkoppelt)."""
    sp = tmp_path / "_session_params.md"
    sp.write_text("**enforceProcess:** false\n", encoding="utf-8")
    ev = {"tool_name": "Edit", "tool_input": {
        "file_path": "C:/x/.claude/analysis/_session_params.md",
        "new_string": "**ceiling:** opus"}}
    out = _run(PARAM_GUARD, ev,
               {"OMNI_PARAM_ACTIVE_SKILL": "_SDF_orchestrate", "OMNI_SESSION_PARAMS": str(sp)})
    assert out["continue"] is False


# ──────────────────── Env-Notbremse (agent-unerreichbar) wirkt weiter ────────────────────

def test_omni_enforce_all_off_bypasses_param_writer():
    """OMNI_ENFORCE_ALL_OFF=1 (Env, agent-unerreichbar) laesst param_writer durch."""
    ev = {"tool_name": "Edit", "tool_input": {
        "file_path": "C:/x/.claude/analysis/_session_params.md",
        "new_string": "**enforceProcess:** false"}}
    out = _run(PARAM_GUARD, ev,
               {"OMNI_PARAM_ACTIVE_SKILL": "_SDF_orchestrate", "OMNI_ENFORCE_ALL_OFF": "1"})
    assert out["continue"] is True


def test_omni_hook_prep_off_bypasses_hookprep():
    """OMNI_HOOK_PREP_OFF=1 (Owner-Env-Hatch) laesst hook_prep durch."""
    ev = {"tool_name": "Skill", "tool_input": {"skill": "_hook_workaround", "args": ""}}
    out = _run(HOOKPREP_GUARD, ev,
               {"OMNI_AGENT_NAME": "idf-validator", "OMNI_HOOK_PREP_OFF": "1"})
    assert out["continue"] is True


# ──────────────────── BL-234 AK-1: per-BL enforceProcess (BL-folder-first) ────────────────────

def test_bl234_bl_folder_enforceprocess_overrides_umbrella(tmp_path, monkeypatch):
    """BL-234 AK-1: {bl_folder}/_session_params.md enforceProcess gewinnt gegen Umbrella."""
    bl_sp = tmp_path / "bl" / "_session_params.md"
    bl_sp.parent.mkdir(parents=True)
    bl_sp.write_text("**enforceProcess:** true\n", encoding="utf-8")
    umbrella = tmp_path / "umbrella_session_params.md"
    umbrella.write_text("**enforceProcess:** false\n", encoding="utf-8")

    monkeypatch.setenv("OMNI_BL_SESSION_PARAMS", str(bl_sp))
    monkeypatch.setenv("OMNI_SESSION_PARAMS", str(umbrella))
    assert enforce_active() is True, "BL-File (true) muss gegen Umbrella (false) gewinnen"


def test_bl234_no_bl_file_falls_back_to_umbrella(tmp_path, monkeypatch):
    """486-safe: kein BL-Kontext ('-') -> Umbrella-enforceProcess gilt unveraendert."""
    umbrella = tmp_path / "umbrella_session_params.md"
    umbrella.write_text("**enforceProcess:** false\n", encoding="utf-8")
    monkeypatch.setenv("OMNI_BL_SESSION_PARAMS", "-")  # explizit kein BL-Kontext
    monkeypatch.setenv("OMNI_SESSION_PARAMS", str(umbrella))
    assert enforce_active() is False


def test_bl234_bl_file_without_enforceprocess_falls_back(tmp_path, monkeypatch):
    """486-safe: BL-File ohne enforceProcess -> faellt auf Umbrella zurueck."""
    bl_sp = tmp_path / "bl" / "_session_params.md"
    bl_sp.parent.mkdir(parents=True)
    bl_sp.write_text("**hil:** off\n", encoding="utf-8")  # kein enforceProcess
    umbrella = tmp_path / "umbrella_session_params.md"
    umbrella.write_text("**enforceProcess:** false\n", encoding="utf-8")
    monkeypatch.setenv("OMNI_BL_SESSION_PARAMS", str(bl_sp))
    monkeypatch.setenv("OMNI_SESSION_PARAMS", str(umbrella))
    assert enforce_active() is False


def test_bl234_bl_folder_enforceprocess_write_still_blocked():
    """Self-Unlock-Schutz erstreckt sich auf den BL-Folder: Agent-Write von
    enforceProcess:false in {bl_folder}/_session_params.md wird von param_writer
    geblockt (Z91 matcht jeden '_session_params.md'-Pfad). Kein per-BL Self-Unlock."""
    ev = {"tool_name": "Edit", "tool_input": {
        "file_path": "C:/DCS/DCSRE/Backlog/BL-1944-x/_session_params.md",
        "new_string": "**enforceProcess:** false"}}
    out = _run(PARAM_GUARD, ev, {"OMNI_PARAM_ACTIVE_SKILL": "_SDF_orchestrate"})
    assert out["continue"] is False, f"BL-Folder Self-Unlock NICHT geschlossen: {out}"
