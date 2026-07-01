"""
BL-422 AK-2: guard_wellen_reminder soll bei enforceProcess=true einen
Single-Agent-fuer-Wellen-Command-Spawn BLOCKIEREN (exit/continue=false),
nicht nur soft-loggen/warnen.

RED-Tests: alle failen bis GREEN-Worker enforce-Logik haertet.

Harness-Konventionen (analog test_guard_agent_prompt_validator.py):
- Subprocess-Helper _run_wellen() schreibt temp _session_params.md + setzt
  OMNI_SESSION_PARAMS, schreibt optional temp manifest fuer difficulty-Aufloesung.
- guard_wellen_reminder liest difficulty primaer aus _session_params.md.
- detect_single_agent_for_wellen_command(prompt) -> (bool, cmd|None)
- read_enforce_process() -> bool (Default true)
- Hook-verdict: {"continue": bool, "message": str}
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD_SCRIPT = SCRIPT_DIR / "guard_wellen_reminder.py"
sys.path.insert(0, str(SCRIPT_DIR))
import guard_wellen_reminder as g  # noqa: E402


# ─── subprocess helper ───────────────────────────────────────────────────────

def _run_wellen(prompt, enforce=True, difficulty="normal", tool_name="Agent"):
    """Schreibt temp _session_params.md mit difficulty + enforceProcess.
    Setzt OMNI_SESSION_PARAMS (analog OMNI_SESSION_PARAMS in guard_agent_prompt_validator).
    Gibt (proc, verdict_dict) zurueck.

    Hinweis: guard_wellen_reminder.py liest enforceProcess und difficulty aus
    SESSION_PARAMS_FILE (via _resolve_vault_path -> Fallback). Es existiert
    KEIN direkter Env-Override fuer den Session-Params-Pfad in guard_wellen_reminder
    wie in guard_agent_prompt_validator (OMNI_SESSION_PARAMS). Daher patchen wir
    SESSION_PARAMS_FILE via Environment-Override-Pattern: wir setzen
    OMNI_SESSION_PARAMS_WELLEN (neuer Env-Key den GREEN einfuehren muss) ODER
    schreiben direkt in den default-Pfad (unsafe in CI). Fuer RED-Tests reicht
    ein subprocess-Aufruf der den guard direkt via stdin treibt UND wir pruefen
    das Verdikt anhand der Funktion-Interfaces direkt (Unit-Tests).

    Da der Guard derzeit NUR einen einzigen Pfad-Aufloeser (_resolve_vault_path)
    hat und keinen Env-Override, nutzen wir fuer subprocess-Tests einen
    OMNI_SESSION_PARAMS_WELLEN Env-Var (den GREEN implementieren muss) als
    Test-Seam. Bis dahin: subprocess-Test prueft Verhalten via stdin-Hook-Event.
    """
    env = os.environ.copy()
    env["OMNI_ENFORCE_ALL_OFF"] = "0"  # Kill-Switch aus

    # Temp-Datei fuer session_params (Guard-Wellen liest aus SESSION_PARAMS_FILE)
    sp = tempfile.NamedTemporaryFile(
        mode="w", suffix="_session_params.md", delete=False, encoding="utf-8"
    )
    sp.write(f"**difficulty:** {difficulty}\n")
    sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
    sp.close()
    # GREEN muss OMNI_SESSION_PARAMS_WELLEN-Override in guard_wellen_reminder einfuehren
    env["OMNI_SESSION_PARAMS_WELLEN"] = sp.name

    ev = {"tool_name": tool_name, "tool_input": {"prompt": prompt}}
    proc = subprocess.run(
        [sys.executable, str(GUARD_SCRIPT)],
        input=json.dumps(ev), capture_output=True, text=True, env=env,
    )
    Path(sp.name).unlink(missing_ok=True)
    verdict = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, verdict


# ─── Unit-Tests (direkte Funktions-Aufrufe ohne subprocess) ──────────────────

def test_detect_single_agent_for_wellen_command_returns_true():
    """Rauch-Test: detect_single_agent_for_wellen_command erkennt einen Wellen-Command
    ohne Wellen-Marker als Single-Agent-Spawn. Muss jetzt schon gruen sein."""
    # _W_fetch in WELLEN_COMMANDS, kein Wellen-Marker im Prompt
    prompt = "_W_fetch: lese alle relevanten Quellen und liefere ein Gesamtergebnis."
    is_single, cmd = g.detect_single_agent_for_wellen_command(prompt)
    assert is_single is True, (
        f"Erwartet (True, '_W_fetch'), bekam ({is_single}, {cmd!r}). "
        "detect_single_agent_for_wellen_command muss diesen Prompt als Violation erkennen."
    )
    assert cmd == "_W_fetch", f"cmd erwartet '_W_fetch', bekam {cmd!r}"


def test_read_enforce_process_default_true():
    """read_enforce_process() gibt True zurueck wenn keine session_params-Datei
    existiert (Default). Muss jetzt schon gruen sein."""
    # SESSION_PARAMS_FILE existiert normalerweise nicht in Test-Isolation
    result = g.read_enforce_process()
    # Default ist True — falls eine echte session_params-Datei existiert kann das
    # variieren; wir testen nur dass die Funktion nicht crasht.
    assert isinstance(result, bool), "read_enforce_process() muss bool liefern"


# ─── AK-2 RED-Tests: Block bei enforceProcess=true ───────────────────────────

def test_single_agent_wellen_blocks_when_enforce():
    """T-422b-1 (RED): Single-Agent-Spawn fuer Wellen-Command bei enforceProcess=true
    soll BLOCKIEREN (continue=false).

    AKTUELL: Guard gibt {"continue": false} NUR wenn read_enforce_process() true liefert.
    Aber guard_wellen_reminder liest enforce aus SESSION_PARAMS_FILE (via _resolve_vault_path),
    nicht aus OMNI_SESSION_PARAMS_WELLEN. Damit ist der Test-Seam nicht verdrahtet und
    der Guard faellt auf den lokalen session_params-Wert zurueck.

    Zwei moegliche RED-Szenarien:
    a) enforceProcess=true aus env-Seam nicht lesbar -> Guard loggt nur WARN ->
       continue=true statt false (FAIL).
    b) Env-Seam fehlt komplett -> Guard returned continue=true (FAIL-OPEN statt BLOCK).

    RED-Erwartung: Test FAILET weil guard_wellen_reminder keinen OMNI_SESSION_PARAMS_WELLEN
    Env-Override implementiert -> enforce-Wert nicht aus Temp-Datei gelesen -> kein Block.
    GREEN muss Env-Override + harte-Block-Logik implementieren. [BL-422 AK-2]
    """
    # _spec in WELLEN_COMMANDS -> detect_single_agent_for_wellen_command True
    prompt = "_spec: analysiere alle Anforderungen und erstelle die vollstaendige Spec."
    proc, r = _run_wellen(prompt, enforce=True, difficulty="normal", tool_name="Agent")
    assert r.get("continue") is False, (
        f"T-422b-1 RED: erwartet BLOCK (continue=false) bei enforceProcess=true, "
        f"bekam {r} | stderr: {proc.stderr[:500]}"
    )
    msg = r.get("message", "")
    assert "BLOCKIERT" in msg or "block" in msg.lower() or "enforceProcess=true" in msg, (
        f"T-422b-1: Nachricht soll Block-Hinweis enthalten, bekam: {msg[:300]}"
    )


def test_single_agent_wellen_soft_when_not_enforce():
    """T-422b-2 (Backward-compat): enforceProcess=false -> WARN/continue=true (kein Block).

    Dieser Test prueft ob das Soft-Warn-Verhalten ERHALTEN bleibt wenn
    enforceProcess=false (Backward-Compat-Constraint).

    Da der Env-Override noch nicht implementiert ist, liest guard_wellen_reminder den
    enforce-Wert aus der echten session_params-Datei (oder Default=true). Der Test
    ist daher auch RED wenn der Override nicht verdrahtet ist — aber die INTENTION
    ist: wenn enforce=false gesetzt werden kann, soll kein Block kommen.

    HINWEIS: Dieser Test kann gruen sein wenn die echte session_params-Datei
    enforceProcess=false enthaelt oder OMNI_ENFORCE_ALL_OFF=1 gesetzt ist.
    Wir setzen enforceProcess=false explizit im Temp-File und erwarten continue=true.
    [BL-422 AK-2 Backward-Compat]
    """
    prompt = "_spec: analysiere alle Anforderungen und erstelle die vollstaendige Spec."
    proc, r = _run_wellen(prompt, enforce=False, difficulty="normal", tool_name="Agent")
    # Mit enforce=false soll kein Block kommen (WARN-Modus, continue=true)
    # RED: wenn Env-Override nicht verdrahtet ist, liest Guard Default=true -> blockt
    # -> Test failt ebenfalls (aber aus anderem Grund als T-422b-1).
    # Nach GREEN muss dieser Test gruen sein.
    assert r.get("continue") is True, (
        f"T-422b-2: erwartet kein Block (continue=true) bei enforceProcess=false, "
        f"bekam {r} | stderr: {proc.stderr[:500]}"
    )


def test_named_teammate_wellen_allowed():
    """T-422b-3 (PASS): Benannter-Teammate-Wellen-Spawn (is_wellen_worker_marker=True)
    -> kein Block (kein Single-Agent-Spawn erkannt).

    detect_single_agent_for_wellen_command gibt (False, None) wenn is_wellen_worker_marker
    True ist. Dieser Test muss JETZT schon gruen sein (Whitelist-Logik bereits implementiert).
    [BL-422 AK-2 FP-Schutz]
    """
    # Wellen-Worker-Marker im Prompt-Header -> ist kein Single-Agent
    prompt = (
        "Explorer E01 — Welle fuer _spec: lies Quellen A/B und liefere Findings. "
        "Kein Orchestrator-Aufruf. Du bist ein Recherche-Worker."
    )
    # Unit-Test auf detect_single_agent_for_wellen_command direkt
    is_single, cmd = g.detect_single_agent_for_wellen_command(prompt)
    assert is_single is False, (
        f"T-422b-3: Wellen-Worker-Marker 'Explorer' soll (False, None) liefern, "
        f"bekam ({is_single}, {cmd!r}). FP-Schutz fehlt!"
    )
    # Auch via subprocess: kein Block erwartet
    proc, r = _run_wellen(prompt, enforce=True, difficulty="normal", tool_name="Agent")
    assert r.get("continue") is True, (
        f"T-422b-3: Wellen-Worker-Spawn mit Wellen-Marker darf NICHT geblockt werden. "
        f"Bekam {r} | stderr: {proc.stderr[:300]}"
    )
