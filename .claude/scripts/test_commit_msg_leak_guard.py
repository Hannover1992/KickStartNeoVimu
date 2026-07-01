#!/usr/bin/env python3
"""Tests fuer commit_msg_leak_guard.py + leak_patterns.py (BL-295 SB-commitmsg).

TDD Stage 1 (Atomic), Modus M3. Spiegel-Stil von test_guard_idf_sdf_handoff.py.

Defense-in-depth gegen internen Prozess-Info-Leak in Commit-Messages — UNABHAENGIG
wer committet (Motor/Hand/MANUELL). Zwei Ebenen:
  A) Unit auf leak_patterns.scan_message(text) -> list (leer = clean, sonst Treffer).
  B) Hook-Integration auf commit_msg_leak_guard.py via subprocess: temp Message-File,
     `py -3 commit_msg_leak_guard.py <tempfile>`, returncode (1=reject / 0=accept).

RED-Zustand: leak_patterns.py + commit_msg_leak_guard.py existieren NOCH NICHT
  -> Import schlaegt fehl (scan_message-Asserts ERROR) UND subprocess findet den
     Hook nicht / liefert nicht 0|1 -> Hook-Asserts FAIL. GREEN = naechster Worker.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
GUARD = SCRIPT_DIR / "commit_msg_leak_guard.py"

# Modul existiert in der RED-Phase NOCH NICHT -> ImportError ist erwartet.
# Wir importieren lazy-tolerant: scan_message bleibt None -> Unit-Asserts schlagen
# fail-loud fehl (das IST der RED-Beweis fuer die leak_patterns-Ebene).
try:
    from leak_patterns import scan_message  # type: ignore
except Exception:  # ModuleNotFoundError in RED, evtl. spaeter ImportError-Varianten
    scan_message = None


def _scan(text):
    """Ruft scan_message; in RED (Modul fehlt) fail-loud mit klarer Meldung."""
    assert scan_message is not None, (
        "leak_patterns.scan_message nicht importierbar — Modul leak_patterns.py "
        "existiert noch nicht (RED-Zustand)"
    )
    return scan_message(text)


def run_hook(message_text):
    """Schreibt die Commit-Message in eine temp-Datei (git commit-msg-Konvention:
    argv[1] = Pfad zur Message-Datei), ruft den Hook via subprocess und gibt
    (returncode, stdout, stderr) zurueck. exit 1 = reject (Leak), exit 0 = accept."""
    fd, msg_path = tempfile.mkstemp(suffix="_COMMIT_EDITMSG.txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(message_text)
        env = os.environ.copy()
        # Kill-Switch in den Tests NICHT setzen (Default = Gate aktiv).
        env.pop("OMNI_COMMIT_MSG_GUARD_OFF", None)
        proc = subprocess.run(
            [sys.executable, str(GUARD), msg_path],
            capture_output=True, text=True, env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr
    finally:
        Path(msg_path).unlink(missing_ok=True)


# ----------------------------------------------------------------------------
# T1 leak: PROC_XREF (PR-Review / Gr.N / PL-Item)
# ----------------------------------------------------------------------------
def test_leak_proc_xref():
    """`feat: X (PR-Review Gr.2, PL-Item CODE_CHANGE)` -> scan nicht-leer (PROC_XREF)
    UND Hook exit 1 (reject)."""
    msg = "feat: X (PR-Review Gr.2, PL-Item CODE_CHANGE)"
    hits = _scan(msg)
    assert hits, f"scan_message muss PROC_XREF-Leak finden, war leer: {hits!r}"
    assert any("PROC_XREF" in str(h) for h in hits), \
        f"erwarteter pattern_id PROC_XREF fehlt in den Treffern: {hits!r}"
    rc, out, err = run_hook(msg)
    assert rc == 1, f"Hook muss Leak rejecten (exit 1), war {rc}\nstdout={out}\nstderr={err}"


# ----------------------------------------------------------------------------
# T2 leak: Co-Authored-By / anthropic
# ----------------------------------------------------------------------------
def test_leak_coauthor_anthropic():
    """`Fix Y\\n\\nCo-Authored-By: Claude <noreply@anthropic.com>` -> scan nicht-leer
    (COAUTH/ANTHROPIC) UND Hook exit 1."""
    msg = "Fix Y\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
    hits = _scan(msg)
    assert hits, f"scan_message muss COAUTH/ANTHROPIC-Leak finden, war leer: {hits!r}"
    ids = " ".join(str(h) for h in hits)
    assert ("COAUTH" in ids) or ("ANTHROPIC" in ids), \
        f"erwartet COAUTH oder ANTHROPIC in den Treffern: {hits!r}"
    rc, out, err = run_hook(msg)
    assert rc == 1, f"Hook muss Co-Author/anthropic rejecten (exit 1), war {rc}\nstdout={out}\nstderr={err}"


# ----------------------------------------------------------------------------
# T3 leak: PLACEHOLDER
# ----------------------------------------------------------------------------
def test_leak_placeholder():
    """`Unwichtig.` -> scan nicht-leer (PLACEHOLDER) UND Hook exit 1."""
    msg = "Unwichtig."
    hits = _scan(msg)
    assert hits, f"scan_message muss PLACEHOLDER-Leak finden, war leer: {hits!r}"
    assert any("PLACEHOLDER" in str(h) for h in hits), \
        f"erwarteter pattern_id PLACEHOLDER fehlt in den Treffern: {hits!r}"
    rc, out, err = run_hook(msg)
    assert rc == 1, f"Hook muss Platzhalter rejecten (exit 1), war {rc}\nstdout={out}\nstderr={err}"


# ----------------------------------------------------------------------------
# T4 clean: fachliche Message mit JIRA-Ticket DCSRE-98
# ----------------------------------------------------------------------------
def test_clean_jira_ticket_passes():
    """`DCSRE-98: Service ReadByIdWithFullIncludes als eigene Methode` -> scan LEER
    UND Hook exit 0 (accept). DCSRE-\\d+ ist JIRA-Ticket, KEIN interner Leak."""
    msg = "DCSRE-98: Service ReadByIdWithFullIncludes als eigene Methode"
    hits = _scan(msg)
    assert hits == [], f"saubere fachliche Message darf KEINEN Treffer haben, war: {hits!r}"
    rc, out, err = run_hook(msg)
    assert rc == 0, f"Hook muss saubere Message akzeptieren (exit 0), war {rc}\nstdout={out}\nstderr={err}"


# ----------------------------------------------------------------------------
# T5 leak: mehrzeilig, Body enthaelt SDF / BL-295
# ----------------------------------------------------------------------------
def test_leak_multiline_body():
    """`Feature Z\\n\\nDetails: SDF Round 3, BL-295` -> scan nicht-leer
    (PROC_XREF: SDF/BL-295 im Body) UND Hook exit 1. Der Hook muss den GESAMTEN
    Message-Text scannen, nicht nur die Titelzeile."""
    msg = "Feature Z\n\nDetails: SDF Round 3, BL-295"
    hits = _scan(msg)
    assert hits, f"scan_message muss SDF/BL-295 im Body finden, war leer: {hits!r}"
    assert any("PROC_XREF" in str(h) for h in hits), \
        f"erwarteter pattern_id PROC_XREF (SDF/BL-295) fehlt in den Treffern: {hits!r}"
    rc, out, err = run_hook(msg)
    assert rc == 1, f"Hook muss mehrzeiligen Body-Leak rejecten (exit 1), war {rc}\nstdout={out}\nstderr={err}"


# ----------------------------------------------------------------------------
# T6 ausnahme: DCSRE-1944 ist JIRA-Ticket, NICHT als interner BL-\d+ werten
# ----------------------------------------------------------------------------
def test_dcsre_ticket_not_treated_as_internal():
    """`DCSRE-1944: Endpoint X hinzugefuegt` -> scan LEER (DCSRE-\\d+ ist JIRA-Ticket,
    KEIN interner BL-\\d+) UND Hook exit 0. Abgrenzung gegen die BL-\\d+/PROC_XREF-Regel:
    die Ausnahme darf das JIRA-Ticket nicht als Leak fehl-klassifizieren."""
    msg = "DCSRE-1944: Endpoint X hinzugefuegt"
    hits = _scan(msg)
    assert hits == [], \
        f"DCSRE-1944 (JIRA-Ticket) darf NICHT als Leak gewertet werden, war: {hits!r}"
    rc, out, err = run_hook(msg)
    assert rc == 0, f"Hook muss JIRA-Ticket-Message akzeptieren (exit 0), war {rc}\nstdout={out}\nstderr={err}"


# ----------------------------------------------------------------------------
# T7 (optional) Kill-Switch: OMNI_COMMIT_MSG_GUARD_OFF=1 -> exit 0 trotz Leak
# ----------------------------------------------------------------------------
def test_kill_switch_overrides_leak():
    """Owner-Override: OMNI_COMMIT_MSG_GUARD_OFF=1 -> Hook exit 0 selbst bei klarem
    Leak (scan_message bleibt nicht-leer, aber der Hook honoriert den Kill-Switch)."""
    msg = "feat: X (PR-Review Gr.2, PL-Item CODE_CHANGE)"
    # scan bleibt unabhaengig vom Kill-Switch ein Treffer:
    hits = _scan(msg)
    assert hits, f"scan_message ist Kill-Switch-unabhaengig und muss Treffer liefern: {hits!r}"
    fd, msg_path = tempfile.mkstemp(suffix="_COMMIT_EDITMSG.txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(msg)
        env = os.environ.copy()
        env["OMNI_COMMIT_MSG_GUARD_OFF"] = "1"
        proc = subprocess.run(
            [sys.executable, str(GUARD), msg_path],
            capture_output=True, text=True, env=env,
        )
        assert proc.returncode == 0, (
            f"Kill-Switch OMNI_COMMIT_MSG_GUARD_OFF=1 muss exit 0 erzwingen, "
            f"war {proc.returncode}\nstdout={proc.stdout}\nstderr={proc.stderr}"
        )
    finally:
        Path(msg_path).unlink(missing_ok=True)


if __name__ == "__main__":
    tests = [
        test_leak_proc_xref,
        test_leak_coauthor_anthropic,
        test_leak_placeholder,
        test_clean_jira_ticket_passes,
        test_leak_multiline_body,
        test_dcsre_ticket_not_treated_as_internal,
        test_kill_switch_overrides_leak,
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
