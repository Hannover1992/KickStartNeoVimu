#!/usr/bin/env python3
"""Tests fuer guard_idf_sdf_handoff.py (BL-313 AK-1, IDF->SDF-Seam).

TDD Stage 1 (Atomic), Modus M3. Spiegel von test_guard_a_idf_handoff.py.
Schliesst die Asymmetrie: A->IDF hat guard_a_idf_handoff.py (INV-A-GUARD-1),
IDF->SDF hatte bisher nur Lead-Pseudocode. Der Guard blockt das IDF-Ende-Signal
(idf_status: "IDF_DONE" + SDF-erwartet im synthetischen _manifest.md) wenn KEIN
_SDF_orchestrate-Handoff nach dem letzten _IDF_orchestrate vorausging — Ausnahme:
HiL-Modus (GLOBAL_HIL: on, manuelle Steuerung, Spiegel von DEFER/A_RETRY).

RED-Ring 1 (Edge Case = Fail-Loud BLOCK-Pfad): test_idf_done_without_sdf_blocked.
RED-Ring 2 (Ausnahme = HiL-Modus endet nicht im Block): test_hil_on_not_blocked.
RED-Ring 3 (legitimer Handoff = SDF nach IDF im audit): test_sdf_handoff_already_ran_not_blocked.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_idf_sdf_handoff.py"


def run_guard(manifest_text, audit_lines, enforce=True):
    """Schreibt ein synthetisches _manifest.md + audit.jsonl, ruft den Guard via
    subprocess (PreToolUse-Event auf das _manifest.md) und gibt das JSON-Verdikt
    zurueck. enforce=True (Default) -> Gate aktiv (BLOCK-Pfad). enforce=False ->
    "**enforceProcess:** false" ins _session_params.md -> WARN-only-Pfad (AK-1 verify d)."""
    with tempfile.NamedTemporaryFile(mode="w", suffix="_manifest.md", delete=False, encoding="utf-8") as mf:
        mf.write(manifest_text)
        manifest_path = mf.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name
    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8") as sp:
        sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
        sp_path = sp.name
    env = os.environ.copy()
    env["OMNI_IDF_SDF_HANDOFF_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    event = {"tool_name": "Edit", "tool_input": {"file_path": manifest_path, "new_string": manifest_text}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    Path(manifest_path).unlink(missing_ok=True)
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    return proc, (json.loads(proc.stdout.strip()) if proc.stdout.strip() else {})


def test_idf_done_without_sdf_blocked():
    """RED Ring 1 (Edge Case): IDF-Ende idf_status=IDF_DONE + routing_target=SDF,
    KEIN _SDF_orchestrate-Handoff nach _IDF_orchestrate -> BLOCK (exit 2) + Recovery-Hint."""
    manifest = (
        "IDF_PIPELINE_STATE:\n"
        "  idf_status: \"IDF_DONE\"\n"
        "  routing_target: \"SDF\"\n"
        "  recommended_next: [\"SB-guard\"]\n"
    )
    audit = [{"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"}]
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 2, f"erwartet exit 2 (BLOCK), war {proc.returncode}"
    assert "Skill(_SDF_orchestrate" in (r.get("message", "") + proc.stderr), \
        "Recovery-Hint 'Rufe Skill(_SDF_orchestrate, args={bl-id} --resume)' fehlt"


def test_hil_on_not_blocked():
    """RED Ring 2 (Ausnahme = HiL-Modus): IDF-Ende-Signal (idf_status=IDF_DONE,
    routing_target=SDF) ABER mit GLOBAL_HIL: on -> manuelle Steuerung, kein Auto-Chain
    erzwungen (Spiegel von DEFER/A_RETRY, INV-A-EXCEPT-1) -> exit 0 (continue),
    KEIN BLOCK -- auch ohne vorausgegangenen _SDF_orchestrate-Call."""
    manifest = (
        "IDF_PIPELINE_STATE:\n"
        "  idf_status: \"IDF_DONE\"\n"
        "  routing_target: \"SDF\"\n"
        "  GLOBAL_HIL: on\n"
    )
    audit = [{"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"}]
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 0, \
        f"erwartet exit 0 (HiL-Modus endet nicht im Block), war {proc.returncode}"
    assert r.get("continue") is True, \
        "GLOBAL_HIL: on darf NICHT blocken (continue=true erwartet)"


def test_sdf_handoff_already_ran_not_blocked():
    """RED Ring 3 (legitimer Handoff): IDF-Ende-Signal (idf_status=IDF_DONE,
    routing_target=SDF) UND _SDF_orchestrate-SKILL_LOAD NACH dem letzten
    _IDF_orchestrate im audit -> legitimer Handoff lief bereits -> exit 0 (continue),
    KEIN BLOCK."""
    manifest = (
        "IDF_PIPELINE_STATE:\n"
        "  idf_status: \"IDF_DONE\"\n"
        "  routing_target: \"SDF\"\n"
    )
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"},
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate"},
    ]
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 0, \
        f"erwartet exit 0 (SDF-Handoff lief bereits, kein BLOCK), war {proc.returncode}"
    assert r.get("continue") is True, \
        "legitimer SDF-Handoff nach IDF darf NICHT blocken (continue=true erwartet)"


def test_enforce_false_warns_not_blocks():
    """RED Ring 4 (AK-1 verify d): IDF-Ende-Signal (idf_status=IDF_DONE +
    routing_target=SDF) OHNE _SDF_orchestrate-Handoff — IDENTISCHES Bypass-Szenario
    wie T1 — ABER enforceProcess=false. -> der Guard feuert als WARN, NICHT als Block:
    exit 0 (KEIN exit 2) UND continue=true UND Recovery-Hint im message. Belegt, dass
    enforce=false den Block-Pfad auf WARN-only herunterstuft (Opt-out, nicht Stille)."""
    manifest = (
        "IDF_PIPELINE_STATE:\n"
        "  idf_status: \"IDF_DONE\"\n"
        "  routing_target: \"SDF\"\n"
        "  recommended_next: [\"SB-guard\"]\n"
    )
    audit = [{"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"}]
    proc, r = run_guard(manifest, audit, enforce=False)
    assert proc.returncode == 0, \
        f"erwartet exit 0 (enforce=false -> WARN, NICHT Block), war {proc.returncode}"
    assert r.get("continue") is True, \
        "enforce=false muss continue=true setzen (WARN-only, kein Block)"
    assert "Skill(_SDF_orchestrate" in r.get("message", ""), \
        "Recovery-Hint 'Skill(_SDF_orchestrate, ... --resume)' muss auch im WARN-Pfad im message stehen"
    assert "WARN" in r.get("message", "").upper(), \
        "WARN-Markierung muss im message-Text stehen (enforce=false -> WARNED)"


def run_guard_seam(tool_name, batch_status_text, audit_lines, enforce=True):
    """Seam-Variante von run_guard: schreibt eine SEPARATE Batch-Status-Manifest-Datei
    (OMNI_IDF_SDF_HANDOFF_MANIFEST), sendet ein synthetisches PreToolUse-Event mit
    dem angegebenen tool_name (Agent/TaskCreate), und gibt das Guard-Verdikt zurueck.

    Ermoeglicht T-a1..T-a4 (BL-423 AK-a RED-Ring): der neue Seam-Zweig triggert bei
    tool_name in ("Agent","TaskCreate") + batch_status=READY (aus MANIFEST-Datei)
    + idf_active=true + sdf_since=false — unabhaengig vom Write-Target-Inhalt.

    Die bestehenden 4 BL-313-Tests rufen run_guard (tool_name="Edit") weiterhin unveraendert.
    """
    # Batch-Status-Manifest (fuer OMNI_IDF_SDF_HANDOFF_MANIFEST)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_batch_manifest.md", delete=False, encoding="utf-8"
    ) as bm:
        bm.write(batch_status_text)
        batch_manifest_path = bm.name

    # Audit-Datei
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name

    # Session-Params (enforce)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_session_params.md", delete=False, encoding="utf-8"
    ) as sp:
        sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
        sp_path = sp.name

    env = os.environ.copy()
    env["OMNI_IDF_SDF_HANDOFF_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    env["OMNI_IDF_SDF_HANDOFF_MANIFEST"] = batch_manifest_path

    # Event mit dem angegebenen tool_name (kein _manifest.md im file_path noetig)
    event = {
        "tool_name": tool_name,
        "tool_input": {"prompt": "spawn next step"},
    }
    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(event),
        capture_output=True, text=True, env=env,
    )

    Path(batch_manifest_path).unlink(missing_ok=True)
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)

    return proc, (json.loads(proc.stdout.strip()) if proc.stdout.strip() else {})


# Batch-Status-Manifest-Template (READY)
_BATCH_MANIFEST_READY = 'batch_status: "READY"\n'
# Batch-Status-Manifest mit IDF+SDF in audit (fuer T-a3: legitimer Handoff)
_AUDIT_IDF_ONLY = [{"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"}]
_AUDIT_IDF_THEN_SDF = [
    {"event": "SKILL_LOAD", "skill_name": "_IDF_orchestrate"},
    {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate"},
]


def test_seam_agent_spawn_at_ready_without_sdf_blocked():
    """T-a1 (BL-423 AK-a RED-Ring 1 — Edge Case BLOCK-Pfad, neuer Seam-Zweig):
    tool_name=Agent + batch_status=READY + audit=[IDF SKILL_LOAD, kein SDF] + enforce=true
    -> BLOCK: exit 2 + Recovery-Hint 'Skill(_SDF_orchestrate' in message/stderr.

    RED-Begruendung: Guard prueft aktuell nur Edit/Write (Zeile 182) — Agent faellt sofort
    auf continue=True durch. Der neue Seam-Zweig (AK-a) muss Agent/TaskCreate + MANIFEST-
    batch_status=READY erkennen und blocken. Solange nicht implementiert: exit 2 = FAIL."""
    proc, r = run_guard_seam(
        tool_name="Agent",
        batch_status_text=_BATCH_MANIFEST_READY,
        audit_lines=_AUDIT_IDF_ONLY,
        enforce=True,
    )
    assert proc.returncode == 2, (
        f"T-a1: erwartet exit 2 (BLOCK — neuer Seam Agent+READY+kein-SDF), war {proc.returncode}. "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert "Skill(_SDF_orchestrate" in (r.get("message", "") + proc.stderr), (
        "T-a1: Recovery-Hint 'Skill(_SDF_orchestrate' fehlt in message/stderr"
    )


def test_seam_agent_at_ready_enforce_false_warns():
    """T-a2 (BL-423 AK-a RED-Ring 2 — WARN-Pfad, enforce=false):
    tool_name=Agent + batch_status=READY + audit=[IDF] + enforce=false
    -> exit 0 (continue=True) + message enthaelt 'Skill(_SDF_orchestrate' UND 'WARN'.

    RED-Begruendung: Guard faellt aktuell bei tool_name=Agent auf continue=True durch (Zeile 182).
    Das Ergebnis hier ist exit 0 + continue=True — aber AUS DEM FALSCHEN GRUND (fruehes Bypass
    ohne WARN-Nachricht). Sobald der Seam-Zweig existiert, muss die message 'WARN' enthalten.
    Aktuell fehlt die WARN-Meldung -> T-a2 FAILT auf den message-Assert."""
    proc, r = run_guard_seam(
        tool_name="Agent",
        batch_status_text=_BATCH_MANIFEST_READY,
        audit_lines=_AUDIT_IDF_ONLY,
        enforce=False,
    )
    assert proc.returncode == 0, (
        f"T-a2: erwartet exit 0 (enforce=false -> WARN, kein Block), war {proc.returncode}"
    )
    assert r.get("continue") is True, (
        "T-a2: enforce=false muss continue=True liefern"
    )
    combined = r.get("message", "") + proc.stderr
    assert "Skill(_SDF_orchestrate" in combined, (
        "T-a2: Recovery-Hint 'Skill(_SDF_orchestrate' fehlt in message/stderr"
    )
    assert "WARN" in combined.upper(), (
        "T-a2: WARN-Markierung fehlt in message/stderr (enforce=false -> WARNED)"
    )


def test_seam_agent_at_ready_with_sdf_handoff_not_blocked():
    """T-a3 (BL-423 AK-a RED-Ring 3 — legitimer Handoff, kein Block):
    tool_name=Agent + batch_status=READY + audit=[IDF, dann _SDF_orchestrate] + enforce=true
    -> exit 0 (continue=True), KEIN Block (SDF lief bereits nach IDF).

    RED-Begruendung: Guard faellt aktuell bei tool_name=Agent immer auf continue=True durch.
    Dieser Test PASST daher bereits im RED-Zustand (exit 0 aus falschem Grund). Sobald der
    Seam-Zweig implementiert ist, muss er den legitimen Handoff erkennen und weiterhin
    exit 0 zurueckgeben — diesmal aus dem RICHTIGEN Grund. T-a3 validiert keine Regression."""
    proc, r = run_guard_seam(
        tool_name="Agent",
        batch_status_text=_BATCH_MANIFEST_READY,
        audit_lines=_AUDIT_IDF_THEN_SDF,
        enforce=True,
    )
    assert proc.returncode == 0, (
        f"T-a3: erwartet exit 0 (legitimer SDF-Handoff -> kein Block), war {proc.returncode}. "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert r.get("continue") is True, (
        "T-a3: legitimer Handoff (SDF nach IDF) darf NICHT blocken"
    )


def test_seam_taskcreate_at_ready_without_sdf_blocked():
    """T-a4 (BL-423 AK-a RED-Ring 4 — TaskCreate-Variante, BLOCK-Pfad):
    tool_name=TaskCreate + batch_status=READY + audit=[IDF, kein SDF] + enforce=true
    -> BLOCK: exit 2 + Recovery-Hint 'Skill(_SDF_orchestrate'.

    RED-Begruendung: Identisch mit T-a1, aber mit tool_name=TaskCreate statt Agent.
    Beide muessen vom Seam-Zweig abgedeckt werden (tool_name in ('Agent','TaskCreate')).
    Aktuell: faellt auf continue=True durch -> exit 0 statt 2 -> T-a4 FAILT."""
    proc, r = run_guard_seam(
        tool_name="TaskCreate",
        batch_status_text=_BATCH_MANIFEST_READY,
        audit_lines=_AUDIT_IDF_ONLY,
        enforce=True,
    )
    assert proc.returncode == 2, (
        f"T-a4: erwartet exit 2 (BLOCK — TaskCreate+READY+kein-SDF), war {proc.returncode}. "
        f"stdout={proc.stdout!r} stderr={proc.stderr!r}"
    )
    assert "Skill(_SDF_orchestrate" in (r.get("message", "") + proc.stderr), (
        "T-a4: Recovery-Hint 'Skill(_SDF_orchestrate' fehlt in message/stderr"
    )


if __name__ == "__main__":
    tests = [
        test_idf_done_without_sdf_blocked,
        test_hil_on_not_blocked,
        test_sdf_handoff_already_ran_not_blocked,
        test_enforce_false_warns_not_blocks,
        test_seam_agent_spawn_at_ready_without_sdf_blocked,
        test_seam_agent_at_ready_enforce_false_warns,
        test_seam_agent_at_ready_with_sdf_handoff_not_blocked,
        test_seam_taskcreate_at_ready_without_sdf_blocked,
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
