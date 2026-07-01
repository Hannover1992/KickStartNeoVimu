#!/usr/bin/env python3
"""Tests fuer guard_redeploy_health.py (BL-337 PL-337-1, Redeploy->Health-Seam, INV-HEALTH-1).

TDD Stage 1 (Atomic), Modus M3. Spiegel von test_guard_idf_sdf_handoff.py (1:1-Form).
Schliesst die Asymmetrie auf der Engine-Austausch-Achse: ein Redeploy tauscht den Motor,
nicht den State -> nach JEDEM Redeploy MUSS /_health_orchestrate (report-only Self-Check)
laufen, BEVOR der neue Motor State beruehrt (INV-HEALTH-1, feedback_machine_not_context).
Der Guard ist die 4. HookGuard-Mirror-Instanz (nach guard_a_idf / guard_idf_sdf /
guard_stage_seam): er blockt einen Edit/Write, wenn der audit einen 'SKILL_LOAD _redeploy'
ohne nachfolgenden 'SKILL_LOAD _health_orchestrate' zeigt — Ausnahme: Kill-Switch
(OMNI_REDEPLOY_HEALTH_OFF=1) und der Fall, dass das Gate bereits erfuellt ist (Health lief
nach Redeploy) bzw. gar kein Redeploy im audit steht (nichts zu pruefen).

Detekt-Substrat (KEIN neuer Marker): audit.jsonl SKILL_LOAD-Scan. health_ran_since_redeploy()
= exaktes Analogon zu sdf_ran_since_idf() in guard_idf_sdf_handoff.py: juengster
'SKILL_LOAD _redeploy' vs juengster 'SKILL_LOAD _health_orchestrate', health_since =
pos_health >= pos_redeploy.

RED-Beweis (Greenfield = RED): guard_redeploy_health.py existiert beim Schreiben dieser
Tests NICHT. Der subprocess-Aufruf `py -3 .claude/scripts/guard_redeploy_health.py` schlaegt
mit "can't open file" (returncode 2, leeres stdout) fehl. Damit erroren/failen die
exit-code- + Meldungs-Assertions IN UNERWARTETER Weise (z.B. T2/T3/T4/T5 erwarten exit 0,
bekommen 2; T1 erwartet zwar exit 2, findet aber den RECOVERY_HINT nicht). DAS IST RED.
GREEN entsteht erst, wenn guard_redeploy_health.py den Gold-Contract erfuellt.

RED-Ring 1 (Edge Case = Fail-Loud BLOCK-Pfad): test_redeploy_without_health_blocked.
RED-Ring 2 (Ausnahme = Kill-Switch): test_kill_switch_not_blocked.
RED-Ring 3 (Gate erfuellt = Health nach Redeploy): test_health_ran_since_redeploy_not_blocked.
RED-Ring 4 (enforce=false -> WARN-only): test_enforce_false_warns_not_blocks.
RED-Ring 5 (kein Redeploy = no-op): test_no_redeploy_no_op.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_redeploy_health.py"


def run_guard(audit_lines, enforce=True, off=False):
    """Schreibt eine synthetische audit.jsonl (+ _session_params.md fuer enforce), ruft
    den Guard via subprocess (PreToolUse-Edit-Event auf eine beliebige Datei) und gibt das
    JSON-Verdikt zurueck. enforce=True (Default) -> Gate aktiv (BLOCK-Pfad). enforce=False ->
    "**enforceProcess:** false" -> WARN-only-Pfad. off=True -> OMNI_REDEPLOY_HEALTH_OFF=1
    (lokaler Kill-Switch). Der Guard liest den audit-Pfad aus OMNI_REDEPLOY_HEALTH_AUDIT
    (Spiegel von OMNI_IDF_SDF_HANDOFF_AUDIT)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name
    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8") as sp:
        sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
        sp_path = sp.name
    env = os.environ.copy()
    env["OMNI_REDEPLOY_HEALTH_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    env.pop("OMNI_ENFORCE_ALL_OFF", None)
    if off:
        env["OMNI_REDEPLOY_HEALTH_OFF"] = "1"
    else:
        env.pop("OMNI_REDEPLOY_HEALTH_OFF", None)
    event = {"tool_name": "Edit", "tool_input": {
        "file_path": str(SCRIPT_DIR / "_manifest.md"),
        "new_string": "irgendein produktiver State-Write nach Redeploy",
    }}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    return proc, (json.loads(proc.stdout.strip()) if proc.stdout.strip() else {})


def test_redeploy_without_health_blocked():
    """RED Ring 1 (Edge Case): audit hat 'SKILL_LOAD _redeploy' aber KEIN nachfolgendes
    'SKILL_LOAD _health_orchestrate', enforce=true -> BLOCK (exit 2) + Recovery-Hint
    'Rufe Skill(_health_orchestrate, args={vault})'. INV-HEALTH-1: der neue Motor darf
    State nicht beruehren, bevor /_health (report-only) lief."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_redeploy"}]
    proc, r = run_guard(audit)
    assert proc.returncode == 2, f"erwartet exit 2 (BLOCK), war {proc.returncode}"
    assert "Skill(_health_orchestrate" in (r.get("message", "") + proc.stderr), \
        "Recovery-Hint 'Rufe Skill(_health_orchestrate, args={vault})' fehlt"


def test_kill_switch_not_blocked():
    """RED Ring 2 (Ausnahme = Kill-Switch): IDENTISCHES Bypass-Szenario wie T1
    ('SKILL_LOAD _redeploy' ohne nachfolgenden Health-Lauf) ABER mit
    OMNI_REDEPLOY_HEALTH_OFF=1 -> Guard no-op (Spiegel des globalen Kill-Switch-Musters)
    -> exit 0 (continue), KEIN BLOCK."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_redeploy"}]
    proc, r = run_guard(audit, off=True)
    assert proc.returncode == 0, \
        f"erwartet exit 0 (Kill-Switch endet nicht im Block), war {proc.returncode}"
    assert r.get("continue") is True, \
        "OMNI_REDEPLOY_HEALTH_OFF=1 darf NICHT blocken (continue=true erwartet)"


def test_health_ran_since_redeploy_not_blocked():
    """RED Ring 3 (Gate erfuellt): audit hat 'SKILL_LOAD _redeploy' UND danach (ts >)
    ein 'SKILL_LOAD _health_orchestrate' -> Self-Check lief bereits -> exit 0 (continue),
    KEIN BLOCK."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_redeploy"},
        {"event": "SKILL_LOAD", "skill_name": "_health_orchestrate"},
    ]
    proc, r = run_guard(audit)
    assert proc.returncode == 0, \
        f"erwartet exit 0 (Health lief nach Redeploy, kein BLOCK), war {proc.returncode}"
    assert r.get("continue") is True, \
        "legitimer Health-Lauf nach Redeploy darf NICHT blocken (continue=true erwartet)"


def test_enforce_false_warns_not_blocks():
    """RED Ring 4 (AK-2 verify d): IDENTISCHES Bypass-Szenario wie T1
    ('SKILL_LOAD _redeploy' ohne nachfolgenden Health-Lauf) ABER enforceProcess=false.
    -> der Guard feuert als WARN, NICHT als Block: exit 0 (KEIN exit 2) UND continue=true
    UND Recovery-Hint im message. Belegt, dass enforce=false den Block-Pfad auf WARN-only
    herunterstuft (Opt-out, nicht Stille)."""
    audit = [{"event": "SKILL_LOAD", "skill_name": "_redeploy"}]
    proc, r = run_guard(audit, enforce=False)
    assert proc.returncode == 0, \
        f"erwartet exit 0 (enforce=false -> WARN, NICHT Block), war {proc.returncode}"
    assert r.get("continue") is True, \
        "enforce=false muss continue=true setzen (WARN-only, kein Block)"
    assert "Skill(_health_orchestrate" in r.get("message", ""), \
        "Recovery-Hint 'Skill(_health_orchestrate, args={vault})' muss auch im WARN-Pfad im message stehen"
    assert "WARN" in r.get("message", "").upper(), \
        "WARN-Markierung muss im message-Text stehen (enforce=false -> WARNED)"


def test_no_redeploy_no_op():
    """RED Ring 5 (kein Redeploy = no-op): audit OHNE jeglichen 'SKILL_LOAD _redeploy'
    -> es gibt nichts zu pruefen (kein Motor-Austausch) -> exit 0 (continue), KEIN BLOCK.
    Fail-safe gegen Over-Triggering: der Guard feuert ausschliesslich nach einem Redeploy."""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"},
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate"},
    ]
    proc, r = run_guard(audit)
    assert proc.returncode == 0, \
        f"erwartet exit 0 (kein Redeploy -> nichts zu pruefen), war {proc.returncode}"
    assert r.get("continue") is True, \
        "ohne vorausgehenden _redeploy darf der Guard NICHT blocken (continue=true erwartet)"


def test_load_method_read_redeploy_does_not_count():
    """BL-367 F12: ein 'SKILL_LOAD _redeploy' mit load_method='read' ist ein Doc-READ von
    _redeploy.md (Mega-Agent-Detection), KEIN echter Redeploy. Szenario: echter Redeploy
    (load_method=skill) -> Health -> danach ein load_method=read _redeploy (nur die Doc
    gelesen). Das Gate ist erfuellt (Health lief nach dem ECHTEN Redeploy); der spaetere
    Doc-Read darf es NICHT re-armen -> exit 0 (continue), KEIN BLOCK. (Live-Bug 2026-06-15:
    Lesen von _redeploy.md re-armte das Health-Gate faelschlich + blockte Write/Edit.)"""
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_redeploy", "load_method": "skill"},
        {"event": "SKILL_LOAD", "skill_name": "_health_orchestrate", "load_method": "skill"},
        {"event": "SKILL_LOAD", "skill_name": "_redeploy", "load_method": "read"},
    ]
    proc, r = run_guard(audit)
    assert proc.returncode == 0, \
        f"erwartet exit 0 (load_method=read Doc-Read re-armt NICHT), war {proc.returncode}"
    assert r.get("continue") is True, \
        "ein load_method=read _redeploy (Doc-Read) darf das Health-Gate nicht re-armen"


if __name__ == "__main__":
    tests = [
        test_redeploy_without_health_blocked,
        test_kill_switch_not_blocked,
        test_health_ran_since_redeploy_not_blocked,
        test_enforce_false_warns_not_blocks,
        test_no_redeploy_no_op,
        test_load_method_read_redeploy_does_not_count,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"[PASS] {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"[FAIL] {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"[ERROR] {t.__name__}: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n=== {passed}/{passed+failed} ===")
    sys.exit(0 if failed == 0 else 1)
