"""
BL-422 AK-4: guard_agent_prompt_validator soll anonyme Agent-Spawns im
Wellen/Team-Kontext ablehnen.

Definition "anonym": Agent-Spawn mit Wellen-Worker-Marker im Prompt, aber
OHNE name UND OHNE team_name im tool_input. Benannte Member (name + team_name
beide gesetzt) werden erlaubt.

Hintergrund: INV-VEHIKEL-3 fordert "altmodisch" = benanntes Team (TeamCreate)
+ benannte Member (Agent name+team_name) + Task-DAG (TaskCreate blockedBy).
Anonyme Einzel-Spawns mit Wellen-Prompts umgehen die Member-gegenseitige-
Sichtbarkeit und verletzen INV-BUILD-GRAIN (false-GREEN-Risiko).

RED-Tests: failen bis GREEN detect_anonymous_wellen_spawn + Block-Logik
in guard_agent_prompt_validator implementiert.

Harness: analog test_guard_agent_prompt_validator.py.
- _run_anon(): subprocess, setzt OMNI_SESSION_PARAMS + OMNI_ENFORCE_ALL_OFF=0
- tool_input shape: {"prompt": ..., "name": ..., "team_name": ...}
  (name/team_name absent = anonym)
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_agent_prompt_validator.py"
sys.path.insert(0, str(SCRIPT_DIR))
import guard_agent_prompt_validator as g  # noqa: E402


# ─── subprocess helper ───────────────────────────────────────────────────────

def _run_anon(prompt, enforce=True, tool_name="Agent", agent_name=None, team_name=None):
    """Baut ein Agent-Hook-Event mit optionalem name/team_name im tool_input.
    Setzt OMNI_SESSION_PARAMS auf temp-Datei mit enforceProcess.
    Gibt (proc, verdict_dict) zurueck."""
    env = os.environ.copy()
    env["OMNI_ENFORCE_ALL_OFF"] = "0"
    env.pop("OMNI_AGENT_PROMPT_VALIDATOR_MANIFEST", None)  # kein modus noetig

    sp = tempfile.NamedTemporaryFile(
        mode="w", suffix="_session_params.md", delete=False, encoding="utf-8"
    )
    sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
    sp.close()
    env["OMNI_SESSION_PARAMS"] = sp.name

    tool_input = {"prompt": prompt}
    if agent_name is not None:
        tool_input["name"] = agent_name
    if team_name is not None:
        tool_input["team_name"] = team_name

    ev = {"tool_name": tool_name, "tool_input": tool_input}
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(ev), capture_output=True, text=True, env=env,
    )
    Path(sp.name).unlink(missing_ok=True)
    verdict = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, verdict


# ─── Unit-Tests auf is_wellen_worker_marker (muss jetzt schon gruen sein) ────

def test_wellen_marker_detected_in_header():
    """Rauch-Test: is_wellen_worker_marker erkennt 'Explorer' im Prompt-Header."""
    prompt = "Explorer E01 — Welle fuer _spec: lies Quellen A/B."
    assert g.is_wellen_worker_marker(prompt) is True


def test_wellen_marker_not_in_berater_prompt():
    """Rauch-Test: reiner Berater-Prompt ohne Wellen-Marker -> False."""
    prompt = "_SDF_berater_modusEntscheidung: analysiere Modus fuer Sub-Batch."
    assert g.is_wellen_worker_marker(prompt) is False


# ─── Unit-Test auf detect_anonymous_wellen_spawn (GREEN muss implementieren) ─

def test_detect_anonymous_wellen_spawn_function_exists():
    """T-422c-0 (RED): guard_agent_prompt_validator.detect_anonymous_wellen_spawn
    muss existieren (Funktion noch nicht implementiert -> AttributeError -> FAIL).

    Signatur-Erwartung:
        detect_anonymous_wellen_spawn(prompt, tool_input_dict) -> (bool, hint|None)
    Returns (True, hint) wenn prompt Wellen-Marker hat UND tool_input_dict kein
    name+team_name enthaelt UND tool_name='Agent'.
    [BL-422 AK-4]
    """
    assert hasattr(g, "detect_anonymous_wellen_spawn"), (
        "T-422c-0 RED: guard_agent_prompt_validator.detect_anonymous_wellen_spawn "
        "existiert nicht. GREEN muss diese Funktion implementieren. [BL-422 AK-4]"
    )


def test_detect_anonymous_wellen_spawn_no_name_returns_violation():
    """T-422c-1 (RED): Wellen-Marker im Prompt + kein name + kein team_name
    -> (True, hint mit 'TaskCreate' und 'name').

    RED: Funktion noch nicht implementiert -> AttributeError ODER (False, None). [BL-422 AK-4]
    """
    fn = getattr(g, "detect_anonymous_wellen_spawn", None)
    assert fn is not None, (
        "T-422c-1 RED: detect_anonymous_wellen_spawn fehlt in guard_agent_prompt_validator."
    )
    prompt = "Drafter D01 — Welle: schreibe einen Entwurf basierend auf den Explorer-Findings."
    tool_input = {"prompt": prompt}  # kein name, kein team_name
    is_v, hint = fn(prompt, tool_input)
    assert is_v is True, (
        f"T-422c-1 RED: erwartet (True, hint), bekam ({is_v}, {hint!r}). "
        "Anonymer Wellen-Spawn ohne name/team_name muss als Violation erkannt werden. "
        "[BL-422 AK-4]"
    )
    assert hint is not None, "T-422c-1: hint darf nicht None sein (Recovery-Hint erwartet)"
    assert "TaskCreate" in hint or "task_create" in hint.lower() or "benannte" in hint.lower(), (
        f"T-422c-1: Recovery-Hint soll 'TaskCreate' erwaehnen, bekam: {hint!r}"
    )
    assert "name" in hint.lower() or "team_name" in hint.lower(), (
        f"T-422c-1: Recovery-Hint soll 'name'/'team_name' erwaehnen, bekam: {hint!r}"
    )


def test_detect_anonymous_wellen_spawn_with_name_and_team_returns_pass():
    """T-422c-2 (PASS nach GREEN): Wellen-Marker + name + team_name -> (False, None).

    RED: Funktion existiert nicht -> AttributeError -> FAIL. [BL-422 AK-4]
    """
    fn = getattr(g, "detect_anonymous_wellen_spawn", None)
    assert fn is not None, (
        "T-422c-2 RED: detect_anonymous_wellen_spawn fehlt."
    )
    prompt = "Drafter D01 — Welle: schreibe einen Entwurf basierend auf den Explorer-Findings."
    tool_input = {"prompt": prompt, "name": "D01-drafter", "team_name": "wellen-team-BL422"}
    is_v, hint = fn(prompt, tool_input)
    assert is_v is False, (
        f"T-422c-2: Benannter Member (name+team_name) soll (False, None) liefern, "
        f"bekam ({is_v}, {hint!r}). FP-Schutz fuer benannte Wellen-Member. [BL-422 AK-4]"
    )


def test_detect_anonymous_wellen_spawn_no_wellen_marker_returns_pass():
    """T-422c-3 (PASS nach GREEN): Kein Wellen-Marker im Prompt -> (False, None)
    auch ohne name/team_name.

    RED: Funktion existiert nicht -> AttributeError -> FAIL. [BL-422 AK-4]
    """
    fn = getattr(g, "detect_anonymous_wellen_spawn", None)
    assert fn is not None, (
        "T-422c-3 RED: detect_anonymous_wellen_spawn fehlt."
    )
    prompt = "_SDF_berater_modusEntscheidung: analysiere Modus fuer Sub-Batch B_r17."
    tool_input = {"prompt": prompt}  # kein name/team_name, aber auch kein Wellen-Marker
    is_v, hint = fn(prompt, tool_input)
    assert is_v is False, (
        f"T-422c-3: Prompt ohne Wellen-Marker soll (False, None) liefern, "
        f"bekam ({is_v}, {hint!r}). [BL-422 AK-4]"
    )


# ─── AK-4 RED-Tests via subprocess ───────────────────────────────────────────

def test_anonymous_wellen_spawn_rejected():
    """T-422c-4 (RED, subprocess): Agent-Spawn mit Wellen-Marker OHNE name/team_name
    -> continue=false (BLOCK) bei enforceProcess=true.
    Recovery-Hint enthaelt 'benannte Member' + 'TaskCreate blockedBy'.

    RED-Erwartung: Guard gibt continue=true (kein AK-4-Check implementiert). [BL-422 AK-4]
    """
    prompt = (
        "Synthese S01 — Welle fuer _K_score: aggregiere alle Explorer- und Drafter-Outputs "
        "und erstelle den finalen K_score-Report."
    )
    # Kein name, kein team_name -> anonym
    proc, r = _run_anon(prompt, enforce=True, tool_name="Agent",
                        agent_name=None, team_name=None)
    assert r.get("continue") is False, (
        f"T-422c-4 RED: erwartet BLOCK (continue=false) fuer anonymen Wellen-Spawn, "
        f"bekam {r} | stderr: {proc.stderr[:500]}"
    )
    msg = r.get("message", "")
    # Recovery-Hint soll benannte Member + TaskCreate erwaehnen
    assert ("benannte" in msg.lower() or "named" in msg.lower()
            or "name" in msg.lower() or "TaskCreate" in msg), (
        f"T-422c-4: Recovery-Hint fehlt oder unvollstaendig: {msg[:400]}"
    )


def test_named_member_spawn_allowed():
    """T-422c-5 (PASS nach GREEN): Agent-Spawn mit Wellen-Marker + name + team_name
    -> continue=true (kein Block).

    AKTUELL: Da detect_anonymous_wellen_spawn noch nicht implementiert ist, gibt Guard
    continue=true -> Test gruen. Muss auch nach GREEN gruen bleiben (FP-Schutz).
    [BL-422 AK-4 FP-Schutz]
    """
    prompt = (
        "Explorer E03 — Welle fuer _model: untersuche Modell-Implikationen fuer BL-422. "
        "Liefere strukturierte Findings."
    )
    proc, r = _run_anon(
        prompt, enforce=True, tool_name="Agent",
        agent_name="E03-explorer", team_name="wellen-team-BL422"
    )
    assert r.get("continue") is True, (
        f"T-422c-5: Benannter Wellen-Member (name+team_name) darf NICHT geblockt werden. "
        f"Bekam {r} | stderr: {proc.stderr[:300]}"
    )


def test_anonymous_non_wellen_spawn_not_blocked_by_ak4():
    """T-422c-6 (PASS): Anonymer Spawn OHNE Wellen-Marker -> AK-4 greift nicht
    (andere Guards koennen noch greifen, aber kein AK-4-Block).

    Dieser Test stellt sicher dass AK-4 NUR Wellen-Marker-Prompts betrifft.
    [BL-422 AK-4 Scope-Begrenzung]
    """
    # Reiner Berater-Prompt ohne Wellen-Marker, kein orchestrator name
    prompt = (
        "_SDF_berater_recalibrate: pruefe Round-Ergebnisse und schlage naechste Aktion vor."
    )
    proc, r = _run_anon(
        prompt, enforce=True, tool_name="Agent",
        agent_name=None, team_name=None
    )
    # AK-4 darf diesen Prompt NICHT blocken (kein Wellen-Marker)
    # Andere Guards (z.B. detect_orchestrator_via_agent) koennen weiterhin greifen,
    # aber der Block-Grund darf nicht AK-4-ANON_WELLEN_SPAWN sein.
    msg = r.get("message", "")
    assert "ANON_WELLEN_SPAWN" not in msg and "anonymen Wellen" not in msg.lower(), (
        f"T-422c-6: AK-4 darf Prompt ohne Wellen-Marker NICHT als anonymen Wellen-Spawn "
        f"blocken. Bekam: {msg[:300]}"
    )
