#!/usr/bin/env python3
"""RED-Tests fuer BL-486 AK-E1-FIX (POST-ROOT-1, batch_2 E1-FIX).

SOLL-Verhalten (Variante b, OQ-2 resolved): Der Post-SDF-Inline-Pfad von
guard_geist9b_sdf_post_inline.py wird aus dem `enforce_active()`-file-early-out
(:117-120) ENTKOPPELT und stattdessen NUR an die agent-UNERREICHBARE env-Notbremse
`OMNI_ENFORCE_ALL_OFF` gekoppelt.

Wurzel (POST-ROOT-1, OBSERVE1 F3): `enforce_active()` liest `enforceProcess` aus
`_session_params.md` (regex). Ein Sub-Agent KANN diese Datei schreiben
(`enforceProcess: false`) -> `enforce_active()` -> False -> der early-out @:118-120
laesst den Post-SDF-Bypass durch. Das ist ein agent-erreichbarer Self-Unlock
(Generalschluessel). Variante b schliesst dieses Fenster: bei enforceProcess=false
(file-Gate) MUSS geist9b den Post-SDF-Inline-Bypass weiterhin BLOCKEN; nur die
agent-unerreichbare OMNI_ENFORCE_ALL_OFF-env (Owner, BL-210) darf ihn oeffnen.

DIESE TESTS SIND RED: Das SOLL ist noch nicht implementiert. Heute laesst der
early-out @:118-120 den Bypass bei enforceProcess=false durch -> ASSERTION 1
(erwartet BLOCK) schlaegt fehl. ASSERTION 2 (BL-210-Compat) ist der Regressions-
Schutz und gruen-bleibend.

RED!=GREEN: NUR Tests. Die Entkopplung selbst (Edit an
guard_geist9b_sdf_post_inline.py) macht der GREEN-Worker.
"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_geist9b_sdf_post_inline.py"

# Audit, das den Post-SDF-Kontext herstellt: I-Pipeline lief, ABER KEIN
# _SDF_orchestrate_post danach -> die Batch-Completion-Transition ist inline (Bypass).
_POST_SDF_INLINE_AUDIT = [{"event": "SKILL_LOAD", "skill_name": "_I_orchestrate"}]
# Eine Batch-Completion-Transition (PL [ ]->[x]) als Edit-Payload.
_PL_DONE_EDIT = "### [x] PL-FOO DONE\n"


def _run_guard_e1(*, enforce_all_off, enforce_process):
    """Fuehrt geist9b als Subprozess aus mit kontrolliertem env.

    enforce_all_off : bool  -> setzt OMNI_ENFORCE_ALL_OFF=1 (Owner-Kill-Switch, BL-210)
                               wenn False: Variable wird EXPLIZIT entfernt (nicht gesetzt).
    enforce_process : bool  -> schreibt **enforceProcess:** true|false in eine
                               OMNI_SESSION_PARAMS-Datei. false -> enforce_active()==False
                               OHNE OMNI_ENFORCE_ALL_OFF (= der formerly early-out-Zustand).

    Gibt das geparste {"continue": ...}-Dict zurueck.
    """
    # Audit-Datei (Post-SDF-Inline-Kontext)
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for line in _POST_SDF_INLINE_AUDIT:
            f.write(json.dumps(line) + "\n")
        audit_path = f.name
    # session_params-Datei (steuert enforce_active() ueber den file-Gate)
    with tempfile.NamedTemporaryFile(mode="w", suffix="_session_params.md", delete=False, encoding="utf-8") as sp:
        sp.write(f"**enforceProcess:** {'true' if enforce_process else 'false'}\n")
        sp_path = sp.name

    env = os.environ.copy()
    env["OMNI_GEIST9B_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    # Sauberes Setup/Teardown der agent-unerreichbaren env-Notbremse:
    env.pop("OMNI_ENFORCE_ALL_OFF", None)
    env.pop("OMNI_GEIST9B_ENFORCE", None)  # kein Debug-WARN-Opt-out -> BLOCK ist Default
    env.pop("OMNI_GEIST9B_OFF", None)
    if enforce_all_off:
        env["OMNI_ENFORCE_ALL_OFF"] = "1"

    event = {"tool_name": "Edit",
             "tool_input": {"file_path": "/x/6_PL/parking-lot.md", "new_string": _PL_DONE_EDIT}}
    proc = subprocess.run([sys.executable, str(GUARD)], input=json.dumps(event),
                          capture_output=True, text=True, env=env)
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    return json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}


def test_e1_blocks_post_sdf_bypass_when_enforce_active_false():
    """ASSERTION 1 (RED): enforceProcess=false (enforce_active()==False) + OMNI_ENFORCE_ALL_OFF
    NICHT gesetzt -> der Post-SDF-Inline-Bypass MUSS BLOCKEN (Fail-Loud).

    Heute (early-out @:118-120) laesst geist9b durch (continue:True) -> dieser Test
    schlaegt fehl, bis Variante b den Post-SDF-Pfad vom enforce_active()-file-Gate
    entkoppelt. Genau das ist POST-ROOT-1.
    """
    r = _run_guard_e1(enforce_all_off=False, enforce_process=False)
    assert r.get("continue") is False, (
        "E1-FIX SOLL: bei enforceProcess=false (enforce_active()==False) OHNE "
        "OMNI_ENFORCE_ALL_OFF muss geist9b den Post-SDF-Inline-Bypass BLOCKEN "
        "(kein agent-erreichbarer Self-Unlock). Heute early-out @:118-120 -> RED."
    )
    assert "GEIST9B" in r.get("message", ""), "Fail-Loud: GUARD-VIOLATION-Message erwartet."


def test_e1_owner_kill_switch_preserves_bl210_compat():
    """ASSERTION 2 (BL-210 BEWAHRT): OMNI_ENFORCE_ALL_OFF=1 (agent-unerreichbarer Owner-
    Kill-Switch) -> der Pfad bleibt unveraendert/erlaubt (continue:True).

    Regressions-Schutz: Die Entkopplung (ASSERTION 1) darf die Owner-Souveraenitaet
    via env NICHT brechen. Heute gruen (early-out @:108) und MUSS nach GREEN gruen bleiben.
    """
    r = _run_guard_e1(enforce_all_off=True, enforce_process=False)
    assert r.get("continue") is True, (
        "BL-210: OMNI_ENFORCE_ALL_OFF=1 (Owner-Kill-Switch) muss den Pfad erlauben "
        "(continue:True) — Owner-Souveraenitaet via agent-unerreichbarer env bleibt."
    )


if __name__ == "__main__":
    tests = [test_e1_blocks_post_sdf_bypass_when_enforce_active_false,
             test_e1_owner_kill_switch_preserves_bl210_compat]
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
    print(f"\n=== {passed}/{passed + failed} ===")
    sys.exit(0 if failed == 0 else 1)
