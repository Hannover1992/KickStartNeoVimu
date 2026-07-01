#!/usr/bin/env python3
"""Tests fuer guard_autochain_stop.py (BL-394, INV-AUTOCHAIN-1 Stop-Hook).

TDD Stage 1 (Atomic). Vorbild: test_guard_post_sdf_stop.py (BL-427 FEUER-Mechanismus).

Schliesst die altmodisch-Pfad-Autochain-Luecke: bei Turn-Ende, hil=off,
pending nicht-blockiertem Sub-Batch UND kein Auto-Continue seit Batch-Ende
-> Block (enforce=true) / WARN (enforce=false) + Recovery-Hint.

hook_event=Stop: laeuft bei Turn-Ende / Goal-Termination.

Soll-Semantik (VIOLATION + enforceProcess=true -> BLOCK-STOP):
  1. Lese hil via read_hil_with_fallback(). hil != off -> pass.
  2. Lese Manifest: batch_items_per_batch-Keys minus completed_sub_batches minus blocked
     = pending_unblocked.
  3. Scanne audit rueckwaerts: sah er _SDF_orchestrate --resume/--next-batch
     seit letztem Batch-Ende? -> Auto-Continue -> pass.
  4. VIOLATION = hil==off AND pending_unblocked != [] AND NOT auto_continue.
  5. VIOLATION + enforce=true -> {"continue": false} + sys.exit(2) + Recovery-Hint.
  6. VIOLATION + enforce=false -> WARN + {"continue": true}.
  7. Off-Switches: OMNI_ENFORCE_ALL_OFF=1 + OMNI_AUTOCHAIN_STOP_OFF=1 -> pass.
  8. Kein Manifest / nicht lesbar -> fail-open -> {"continue": true}.
  9. AK-2: blocked_by_external (docker|token|user) -> Sub-Batch zaehlt NICHT als pending.

Test-Override:
  OMNI_AUTOCHAIN_STOP_AUDIT       audit-Pfad
  OMNI_SESSION_PARAMS             session_params-Pfad (enforceProcess)
  OMNI_AUTOCHAIN_STOP_MANIFEST    manifest-Pfad

Globaler Off-Switch: OMNI_ENFORCE_ALL_OFF=1.
Lokaler Off-Switch: OMNI_AUTOCHAIN_STOP_OFF=1.

RED-State: guard_autochain_stop.py existiert noch nicht -> alle Tests FAILEN
  mit FileNotFoundError (importlib) oder subprocess exit != 0.

Tests (T-1..T-10):
  T-1   test_hil_off_pending_no_autocontinue_enforce_true_blocks
        — AK-1 POSITIV enforce=true: Block (continue=false, exit 2)
  T-2   test_hil_off_pending_no_autocontinue_enforce_false_warns
        — AK-1 enforce=false: WARN (continue=true, kein exit 2)
  T-3   test_hil_not_off_passes
        — PASS-2: hil != off -> continue=true
  T-4   test_auto_continue_in_audit_passes
        — PASS-3: Auto-Continue im audit -> continue=true
  T-5   test_no_pending_passes
        — PASS-4: completed_sub_batches == alle Keys -> continue=true
  T-6   test_no_manifest_failopen_passes
        — PASS-5 / FAIL-OPEN: Manifest fehlt -> continue=true
  T-7   test_all_pending_blocked_passes
        — AK-2 PASS: alle pending blocked_by_external -> pending_unblocked=[] -> continue=true
  T-8   test_mixed_blocked_and_unblocked_blocks
        — AK-2 BLOCK: 1 blocked + 1 unblocked -> pending_unblocked=[unblocked] -> exit 2
  T-9   test_off_switch_local_passes
        — PASS-1: OMNI_AUTOCHAIN_STOP_OFF=1 trotz Violation-Lage -> continue=true
  T-10  test_settings_json_contains_autochain_stop_hook
        — AK-3 Struktur: settings.json Stop-Array enthaelt guard_autochain_stop-Command
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "guard_autochain_stop.py"

ROOT_DIR = SCRIPT_DIR.parent.parent
SETTINGS_JSON = ROOT_DIR / ".claude" / "settings.json"


# ---------------------------------------------------------------------------
# Hilfs-Fixtures
# ---------------------------------------------------------------------------

def _make_audit_file(audit_lines):
    """Schreibt audit_lines als JSONL in eine Tempfile, gibt Pfad zurueck."""
    af = tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    )
    for line in audit_lines:
        af.write(json.dumps(line) + "\n")
    af.close()
    return af.name


def _make_session_params(enforce=True, hil="off"):
    """Schreibt eine _session_params.md Tempfile, gibt Pfad zurueck."""
    sp = tempfile.NamedTemporaryFile(
        mode="w", suffix="_session_params.md", delete=False, encoding="utf-8"
    )
    sp.write(f"**enforceProcess:** {'true' if enforce else 'false'}\n")
    sp.write(f"**GLOBAL_HIL:** {hil}\n")
    sp.close()
    return sp.name


def _make_manifest(
    batch_keys=None,
    completed=None,
    blocked=None,
):
    """Schreibt ein minimales _manifest.md mit DF_BATCH_STATE-Block.

    batch_keys:  Liste von Sub-Batch-Bezeichnern (Keys in batch_items_per_batch).
    completed:   Liste von Keys in completed_sub_batches.
    blocked:     Dict {key: blocked_by_external-Wert} (z.B. {"batch_2": "docker"}).
    """
    batch_keys = batch_keys or []
    completed = completed or []
    blocked = blocked or {}

    lines = ["# Manifest\n", "\n", "DF_BATCH_STATE:\n"]

    # batch_items_per_batch
    lines.append("  batch_items_per_batch:\n")
    for k in batch_keys:
        lines.append(f"    {k}: []\n")

    # completed_sub_batches
    lines.append("  completed_sub_batches:\n")
    for k in completed:
        lines.append(f"    - {k}\n")

    # blocked_sub_batches mit blocked_by_external
    if blocked:
        lines.append("  blocked_sub_batches:\n")
        for k, reason in blocked.items():
            lines.append(f"    - key: {k}\n")
            lines.append(f"      blocked_by_external: {reason}\n")

    mf = tempfile.NamedTemporaryFile(
        mode="w", suffix="_manifest.md", delete=False, encoding="utf-8"
    )
    mf.writelines(lines)
    mf.close()
    return mf.name


def _run_stop_hook(
    audit_lines=None,
    enforce=True,
    hil="off",
    batch_keys=None,
    completed=None,
    blocked=None,
    manifest_path=None,
    extra_env=None,
):
    """Simuliert Stop-Event und gibt (proc, result) zurueck.

    Stop-Hook liest Stop-Event von stdin (JSON), scannt audit.jsonl + Manifest.
    """
    audit_lines = audit_lines or []
    audit_path = _make_audit_file(audit_lines)
    sp_path = _make_session_params(enforce=enforce, hil=hil)

    if manifest_path is None:
        mf_path = _make_manifest(
            batch_keys=batch_keys,
            completed=completed,
            blocked=blocked,
        )
    else:
        mf_path = manifest_path

    env = os.environ.copy()
    env["OMNI_AUTOCHAIN_STOP_AUDIT"] = audit_path
    env["OMNI_SESSION_PARAMS"] = sp_path
    env["OMNI_AUTOCHAIN_STOP_MANIFEST"] = mf_path
    if extra_env:
        env.update(extra_env)

    stop_event = {"hook_event": "Stop", "reason": "turn_end"}

    proc = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(stop_event),
        capture_output=True,
        text=True,
        env=env,
    )
    Path(audit_path).unlink(missing_ok=True)
    Path(sp_path).unlink(missing_ok=True)
    if manifest_path is None:
        Path(mf_path).unlink(missing_ok=True)

    result = json.loads(proc.stdout.strip()) if proc.stdout.strip() else {}
    return proc, result


# ---------------------------------------------------------------------------
# T-1: AK-1 POSITIV enforce=true — Block (continue=false, exit 2)
# ---------------------------------------------------------------------------

def test_hil_off_pending_no_autocontinue_enforce_true_blocks():
    """T-1 (AK-1 Kern-RED-Test): hil=off + pending nicht-blockierter Sub-Batch
    + kein Auto-Continue im audit + enforce=true -> BLOCK (continue=false, sys.exit(2)).

    Recovery-Hint muss im Output/Stderr sichtbar sein.

    RED: guard_autochain_stop.py existiert noch nicht -> FileNotFoundError / exit != 0.
    """
    audit = [
        # Batch-Abschluss-Event (kein _SDF_orchestrate --resume/--next-batch danach)
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
    ]
    proc, r = _run_stop_hook(
        audit_lines=audit,
        enforce=True,
        hil="off",
        batch_keys=["batch_1", "batch_2"],
        completed=["batch_1"],
        blocked={},
    )
    assert r.get("continue") is False, (
        f"T-1 AK-1: hil=off + pending nicht-blockiert (batch_2 offen) + kein Auto-Continue "
        f"+ enforce=true -> continue:false (BLOCK) erwartet. War: {r}. "
        f"guard_autochain_stop.py existiert vermutlich noch nicht (RED erwartet)."
    )
    assert proc.returncode == 2, (
        f"T-1: sys.exit(2) erwartet bei Block, war returncode={proc.returncode}."
    )
    combined = (r.get("message", "") or "") + proc.stderr
    assert "Skill(_SDF_orchestrate --resume --next-batch)" in combined or "resume" in combined.lower(), (
        f"T-1: Recovery-Hint 'Skill(_SDF_orchestrate --resume --next-batch)' muss im "
        f"Output/Stderr sichtbar sein. War: '{combined[:300]}'"
    )


# ---------------------------------------------------------------------------
# T-2: AK-1 enforce=false — WARN (continue=true, kein exit 2)
# ---------------------------------------------------------------------------

def test_hil_off_pending_no_autocontinue_enforce_false_warns():
    """T-2 (AK-1 enforce=false): gleiche VIOLATION-Lage + enforce=false
    -> WARN + continue=true (kein BLOCK, kein sys.exit(2)).

    Der Hook darf im enforce=false-Modus den Turn NICHT sperren.

    RED: guard_autochain_stop.py existiert noch nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
    ]
    proc, r = _run_stop_hook(
        audit_lines=audit,
        enforce=False,
        hil="off",
        batch_keys=["batch_1", "batch_2"],
        completed=["batch_1"],
        blocked={},
    )
    assert r.get("continue") is True, (
        f"T-2 AK-1 enforce=false: VIOLATION + enforce=false -> continue:true (WARN, kein Block) "
        f"erwartet. War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-2: exit 0 erwartet (kein Block bei enforce=false), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-3: PASS-2 — hil != off
# ---------------------------------------------------------------------------

def test_hil_not_off_passes():
    """T-3 (PASS-2): hil != off (z.B. 'cycle') -> Guard ignoriert, continue=true.

    Auch bei pending offenem Sub-Batch -> kein Block wenn hil != off.

    RED: guard_autochain_stop.py existiert noch nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
    ]
    proc, r = _run_stop_hook(
        audit_lines=audit,
        enforce=True,
        hil="cycle",  # != off
        batch_keys=["batch_1", "batch_2"],
        completed=["batch_1"],
        blocked={},
    )
    assert r.get("continue") is True, (
        f"T-3 PASS-2: hil=cycle (!= off) -> continue:true erwartet (kein Block). War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-3: exit 0 erwartet, war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-4: PASS-3 — Auto-Continue im audit sichtbar
# ---------------------------------------------------------------------------

def test_auto_continue_in_audit_passes():
    """T-4 (PASS-3): _SDF_orchestrate --resume/--next-batch im audit sichtbar
    nach letztem Batch-Abschluss -> Auto-Continue detektiert -> continue=true.

    RED: guard_autochain_stop.py existiert noch nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
        # Auto-Continue: SDF --resume/--next-batch nach Batch-Ende
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate", "args": "--resume --next-batch"},
    ]
    proc, r = _run_stop_hook(
        audit_lines=audit,
        enforce=True,
        hil="off",
        batch_keys=["batch_1", "batch_2"],
        completed=["batch_1"],
        blocked={},
    )
    assert r.get("continue") is True, (
        f"T-4 PASS-3: Auto-Continue (_SDF_orchestrate --resume) im audit -> "
        f"continue:true erwartet. War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-4: exit 0 erwartet (Auto-Continue detektiert), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-5: PASS-4 — kein pending (alles completed)
# ---------------------------------------------------------------------------

def test_no_pending_passes():
    """T-5 (PASS-4): completed_sub_batches == alle batch_items_per_batch-Keys
    -> pending_unblocked=[] -> kein Block -> continue=true.

    RED: guard_autochain_stop.py existiert noch nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
    ]
    proc, r = _run_stop_hook(
        audit_lines=audit,
        enforce=True,
        hil="off",
        batch_keys=["batch_1", "batch_2"],
        completed=["batch_1", "batch_2"],  # alle completed
        blocked={},
    )
    assert r.get("continue") is True, (
        f"T-5 PASS-4: completed_sub_batches == alle Keys -> continue:true "
        f"(kein pending). War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-5: exit 0 erwartet (kein pending), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-6: PASS-5 / FAIL-OPEN — Manifest fehlt/unlesbar
# ---------------------------------------------------------------------------

def test_no_manifest_failopen_passes():
    """T-6 (PASS-5 FAIL-OPEN): Manifest nicht vorhanden / nicht lesbar
    -> Guard kann pending nicht ermitteln -> fail-open -> continue=true.

    RED: guard_autochain_stop.py existiert noch nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
    ]
    proc, r = _run_stop_hook(
        audit_lines=audit,
        enforce=True,
        hil="off",
        manifest_path="/nonexistent/manifest_BL394_xYz.md",
    )
    assert r.get("continue") is True, (
        f"T-6 FAIL-OPEN: Manifest fehlt -> continue:true erwartet (fail-open). War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-6: exit 0 erwartet (fail-open), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-7: AK-2 — alle pending blocked_by_external -> pass
# ---------------------------------------------------------------------------

def test_all_pending_blocked_passes():
    """T-7 (AK-2 PASS): alle pending Sub-Batches haben blocked_by_external
    (docker|token|user) -> pending_unblocked=[] -> kein Block -> continue=true.

    Echter externer Blocker (z.B. docker down) -> legitimer Stopp.

    RED: guard_autochain_stop.py existiert noch nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
    ]
    proc, r = _run_stop_hook(
        audit_lines=audit,
        enforce=True,
        hil="off",
        batch_keys=["batch_1", "batch_2", "batch_3"],
        completed=["batch_1"],
        blocked={"batch_2": "docker", "batch_3": "token"},  # alle pending blockiert
    )
    assert r.get("continue") is True, (
        f"T-7 AK-2: alle pending blocked_by_external -> pending_unblocked=[] -> "
        f"continue:true erwartet (echter Blocker, kein false-Block). War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-7: exit 0 erwartet (alle blocked), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-8: AK-2 gemischt — 1 blocked + 1 unblocked -> Block
# ---------------------------------------------------------------------------

def test_mixed_blocked_and_unblocked_blocks():
    """T-8 (AK-2 BLOCK): 1 pending blocked_by_external + 1 pending nicht-blockiert
    -> pending_unblocked=[unblocked_key] -> VIOLATION -> Block (enforce=true -> exit 2).

    Der Loop laeuft an blockierten Items vorbei; nur echte nicht-blockierte stoppen.

    RED: guard_autochain_stop.py existiert noch nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
    ]
    proc, r = _run_stop_hook(
        audit_lines=audit,
        enforce=True,
        hil="off",
        batch_keys=["batch_1", "batch_2", "batch_3"],
        completed=["batch_1"],
        blocked={"batch_2": "user"},  # batch_2 blocked, batch_3 NICHT blocked -> pending_unblocked=[batch_3]
    )
    assert r.get("continue") is False, (
        f"T-8 AK-2 gemischt: 1 blocked (batch_2/user) + 1 unblocked (batch_3) + kein Auto-Continue "
        f"+ enforce=true -> continue:false (BLOCK) erwartet. "
        f"pending_unblocked=[batch_3] ist nicht leer. War: {r}."
    )
    assert proc.returncode == 2, (
        f"T-8: sys.exit(2) erwartet bei Block, war returncode={proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-9: Off-Switch lokal — OMNI_AUTOCHAIN_STOP_OFF=1
# ---------------------------------------------------------------------------

def test_off_switch_local_passes():
    """T-9 (PASS-1 Off-Switch): OMNI_AUTOCHAIN_STOP_OFF=1 trotz klarer VIOLATION-Lage
    -> Guard deaktiviert -> continue=true, exit 0.

    RED: guard_autochain_stop.py existiert nicht oder kennt OMNI_AUTOCHAIN_STOP_OFF nicht.
    """
    audit = [
        {"event": "SKILL_LOAD", "skill_name": "_SDF_orchestrate_post"},
    ]
    proc, r = _run_stop_hook(
        audit_lines=audit,
        enforce=True,
        hil="off",
        batch_keys=["batch_1", "batch_2"],
        completed=["batch_1"],
        blocked={},
        extra_env={"OMNI_AUTOCHAIN_STOP_OFF": "1"},
    )
    assert r.get("continue") is True, (
        f"T-9 Off-Switch lokal: OMNI_AUTOCHAIN_STOP_OFF=1 -> continue:true erwartet. War: {r}."
    )
    assert proc.returncode == 0, (
        f"T-9: exit 0 erwartet (Off-Switch), war {proc.returncode}."
    )


# ---------------------------------------------------------------------------
# T-10: AK-3 Struktur — settings.json Stop-Array enthaelt guard_autochain_stop
# ---------------------------------------------------------------------------

def test_settings_json_contains_autochain_stop_hook():
    """T-10 (AK-3 Struktur): settings.json Stop-Hooks-Array muss einen Eintrag
    mit 'guard_autochain_stop' als command enthalten.

    Verifikation: settings.json parsen + assert hook-command im Stop-Array.

    RED: guard_autochain_stop.py noch nicht in settings.json eingetragen.
    """
    assert SETTINGS_JSON.exists(), (
        f"T-10: settings.json nicht gefunden unter {SETTINGS_JSON}. "
        "Pfad korrekt?"
    )
    try:
        data = json.loads(SETTINGS_JSON.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:
        raise AssertionError(
            f"T-10: settings.json konnte nicht geparst werden: {e}"
        ) from e

    hooks = data.get("hooks", {})
    stop_hooks = hooks.get("Stop", [])

    # Kompatibel mit zwei settings.json-Strukturen:
    #   Flach:       [{type: command, command: "py -3 .../guard_autochain_stop.py"}, ...]
    #   Verschachtelt: [{hooks: [{type: command, command: ...}, ...]}, ...]  (aktuell im Projekt)
    def _commands_from_stop_hooks(hooks_list):
        """Yields alle command-Strings aus Stop-Hooks unabhaengig von Verschachtelungstiefe."""
        for entry in hooks_list:
            if isinstance(entry, dict):
                cmd = entry.get("command", "")
                if cmd:
                    yield cmd
                # Verschachtelte hooks-Liste (wie im Projekt-settings.json)
                for sub in entry.get("hooks", []):
                    if isinstance(sub, dict):
                        sub_cmd = sub.get("command", "")
                        if sub_cmd:
                            yield sub_cmd
            elif isinstance(entry, str):
                yield entry

    found = any(
        "guard_autochain_stop" in cmd
        for cmd in _commands_from_stop_hooks(stop_hooks)
    )

    assert found, (
        f"T-10 AK-3: settings.json Stop-Array enthaelt KEINEN Eintrag mit "
        f"'guard_autochain_stop'. Stop-Hooks vorhanden: {stop_hooks}. "
        f"Hook muss analog guard_post_sdf_stop.py eingetragen werden (IV-9, BL-394 AK-3)."
    )


# ---------------------------------------------------------------------------
# __main__ runner (direkt ausfuehrbar ohne pytest)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    tests = [
        test_hil_off_pending_no_autocontinue_enforce_true_blocks,
        test_hil_off_pending_no_autocontinue_enforce_false_warns,
        test_hil_not_off_passes,
        test_auto_continue_in_audit_passes,
        test_no_pending_passes,
        test_no_manifest_failopen_passes,
        test_all_pending_blocked_passes,
        test_mixed_blocked_and_unblocked_blocks,
        test_off_switch_local_passes,
        test_settings_json_contains_autochain_stop_hook,
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
    print(f"\n=== {passed}/{passed + failed} ===")
    sys.exit(0 if failed == 0 else 1)
