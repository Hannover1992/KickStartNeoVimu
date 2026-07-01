#!/usr/bin/env python3
"""Tests fuer guard_stage_seam_handoff.py (BL-295 AK-6, Stage-/Batch-Ende-Commit-Seam).

TDD Stage 1 (Atomic), Modus M3. Spiegel von test_guard_idf_sdf_handoff.py (BL-313)
und geist9b (Commit-Seam-Klasse). Schliesst die BL-295-Wurzel STRUKTURELL: der
Commit-Step (_stage_orchestrate = Security-Gate + Commit-Normierung) darf nicht still
uebersprungen werden. Schreibt der Lead die Stage-/Batch-Ende-Progression
(stage_done / completed_sub_batches / [ ]->[x]-Commit-Marker) waehrend Stage-GREEN /
I-Ende erreicht ist, OHNE vorausgehenden Skill(_stage_orchestrate)-Call, ist der
Commit-Seam verletzt -> BLOCK + Recovery-Hint.

Ausnahme (PASS, Spiegel von DEFER/A_RETRY = INV-A-EXCEPT-1): hil != off (HiL-Modus darf
ein Go-Gate setzen / manuell steuern) -> kein Auto-Commit-Seam erzwungen.

RED-Ring 1 (Edge Case = Fail-Loud BLOCK-Pfad): test_seam_skip_blocked.
RED-Ring 2 (legitimer Handoff = _stage_orchestrate nach Stage-GREEN): test_stage_orchestrate_ran_not_blocked.
RED-Ring 3 (Ausnahme = hil != off): test_hil_not_off_not_blocked.
RED-Ring 4 (AK-6 verify d = enforce=false -> WARN): test_enforce_false_warns.

RED-Beweis: guard_stage_seam_handoff.py existiert NOCH NICHT -> subprocess findet GUARD
nicht (returncode != 0/2-Vertrag, leeres stdout) -> alle Asserts failen. Das ist RED.
GREEN = naechster Worker (Guard-Production-Code).
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_stage_seam_handoff.py"


def run_guard(manifest_text, audit_lines, enforce=True, hil="off"):
    """Schreibt ein synthetisches _manifest.md + audit.jsonl + _session_params.md, ruft
    den Guard via subprocess (PreToolUse-Event auf das _manifest.md) und gibt
    (proc, verdikt_json) zurueck.

    Steuerbar:
      enforce=True (Default) -> "**enforceProcess:** true"  -> Gate aktiv (BLOCK-Pfad).
      enforce=False          -> "**enforceProcess:** false" -> WARN-only-Pfad (AK-6 verify d).
      hil="off" (Default)    -> "**HiL:** off"  -> Auto-Commit-Seam erzwungen.
      hil="cycle"/"manual"   -> hil != off     -> HiL darf Go-Gate (Ausnahme, PASS).

    Test-Override: OMNI_STAGE_SEAM_AUDIT (audit-path), OMNI_SESSION_PARAMS (enforce + HiL).
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix="_manifest.md", delete=False, encoding="utf-8") as mf:
        mf.write(manifest_text)
        manifest_path = mf.name
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as af:
        for line in audit_lines:
            af.write(json.dumps(line) + "\n")
        audit_path = af.name
    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8") as sp:
        sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
        sp.write(f"**HiL:** {hil}\n")
        sp_path = sp.name
    env = os.environ.copy()
    env["OMNI_STAGE_SEAM_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    event = {"tool_name": "Edit", "tool_input": {"file_path": manifest_path, "new_string": manifest_text}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    Path(manifest_path).unlink(missing_ok=True)
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    return proc, (json.loads(proc.stdout.strip()) if proc.stdout.strip() else {})


def test_seam_skip_blocked():
    """RED Ring 1 (Edge Case): Stage-/Batch-Ende-Progression (stage_done + ein
    [x]-Commit-Marker + completed_sub_batches) WAEHREND Stage-GREEN/I-Ende erreicht ist,
    audit hat _I_orchestrate-Ende (Stage-GREEN) ABER KEIN _stage_orchestrate seither,
    hil=off + enforceProcess=true -> Commit-Seam uebersprungen -> BLOCK (exit 2) +
    Recovery-Hint 'Skill(_stage_orchestrate'."""
    manifest = (
        "DF_BATCH_STATE:\n"
        "  stage_done: true\n"
        "  completed_sub_batches: [\"SB-stageguard\"]\n"
        "- [x] BL-295-AK-6-PL-1 (Stage 1 GREEN, commit)\n"
    )
    audit = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
    proc, r = run_guard(manifest, audit)  # Default: enforce=True, hil=off
    assert proc.returncode == 2, f"erwartet exit 2 (BLOCK), war {proc.returncode}"
    assert "Skill(_stage_orchestrate" in (r.get("message", "") + proc.stderr), \
        "Recovery-Hint 'Rufe Skill(_stage_orchestrate, args={bl-id})' fehlt"


def test_stage_orchestrate_ran_not_blocked():
    """RED Ring 2 (legitimer Handoff): identische Stage-Ende-Lage, ABER audit hat
    _stage_orchestrate-SKILL_LOAD NACH dem Stage-GREEN (_I_orchestrate) -> der
    Commit-/Security-Gate-Step lief bereits -> exit 0 (continue), KEIN BLOCK."""
    manifest = (
        "DF_BATCH_STATE:\n"
        "  stage_done: true\n"
        "  completed_sub_batches: [\"SB-stageguard\"]\n"
        "- [x] BL-295-AK-6-PL-1 (Stage 1 GREEN, commit)\n"
    )
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"},
        {"event": "SKILL_LOAD", "skill_name": "_stage_orchestrate"},
    ]
    proc, r = run_guard(manifest, audit)
    assert proc.returncode == 0, \
        f"erwartet exit 0 (_stage_orchestrate lief seit Stage-GREEN, kein BLOCK), war {proc.returncode}"
    assert r.get("continue") is True, \
        "legitimer _stage_orchestrate nach Stage-GREEN darf NICHT blocken (continue=true erwartet)"


def test_hil_not_off_not_blocked():
    """RED Ring 3 (Ausnahme = HiL-Modus): identische Seam-Skip-Lage (Stage-Ende-Write,
    audit OHNE _stage_orchestrate seit Stage-GREEN) ABER hil=cycle (hil != off) ->
    HiL darf ein Go-Gate / manuelle Steuerung haben (Spiegel DEFER/A_RETRY,
    INV-A-EXCEPT-1) -> exit 0 (continue), KEIN BLOCK."""
    manifest = (
        "DF_BATCH_STATE:\n"
        "  stage_done: true\n"
        "  completed_sub_batches: [\"SB-stageguard\"]\n"
        "- [x] BL-295-AK-6-PL-1 (Stage 1 GREEN, commit)\n"
    )
    audit = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
    proc, r = run_guard(manifest, audit, hil="cycle")
    assert proc.returncode == 0, \
        f"erwartet exit 0 (hil != off endet nicht im Block), war {proc.returncode}"
    assert r.get("continue") is True, \
        "hil=cycle (hil != off) darf NICHT blocken (continue=true erwartet)"


def test_enforce_false_warns():
    """RED Ring 4 (AK-6 verify d): IDENTISCHES Bypass-Szenario wie T1 (Stage-Ende-Write
    OHNE _stage_orchestrate seit Stage-GREEN, hil=off) ABER enforceProcess=false. -> der
    Guard feuert als WARN, NICHT als Block: exit 0 (KEIN exit 2) UND continue=true UND
    Recovery-Hint + WARN-Markierung im message. Belegt: enforce=false stuft den
    Block-Pfad auf WARN-only herunter (Opt-out, nicht Stille)."""
    manifest = (
        "DF_BATCH_STATE:\n"
        "  stage_done: true\n"
        "  completed_sub_batches: [\"SB-stageguard\"]\n"
        "- [x] BL-295-AK-6-PL-1 (Stage 1 GREEN, commit)\n"
    )
    audit = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
    proc, r = run_guard(manifest, audit, enforce=False, hil="off")
    assert proc.returncode == 0, \
        f"erwartet exit 0 (enforce=false -> WARN, NICHT Block), war {proc.returncode}"
    assert r.get("continue") is True, \
        "enforce=false muss continue=true setzen (WARN-only, kein Block)"
    assert "Skill(_stage_orchestrate" in r.get("message", ""), \
        "Recovery-Hint 'Skill(_stage_orchestrate, args={bl-id})' muss auch im WARN-Pfad im message stehen"
    assert "WARN" in r.get("message", "").upper(), \
        "WARN-Markierung muss im message-Text stehen (enforce=false -> WARNED)"


if __name__ == "__main__":
    tests = [
        test_seam_skip_blocked,
        test_stage_orchestrate_ran_not_blocked,
        test_hil_not_off_not_blocked,
        test_enforce_false_warns,
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
