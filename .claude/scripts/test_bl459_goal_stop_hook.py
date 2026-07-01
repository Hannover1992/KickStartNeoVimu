#!/usr/bin/env python3
"""BL-459 RED-Tests fuer goal_state_reader_hook.py:
   - _terminal_ok_marker (neu, existiert noch nicht -> RED)
   - main() behavioral: gated/user_closed terminal-OK + JSON fail-open.
   Fixture-Methode: spiegelt test_goal_state_reader_hook.py (subprocess + OMNI_GOAL_MD/OMNI_GOAL_VAULT_ROOT).
   AK-2 fail-open: monkeypatch auf gh.evaluate (in-process, capsys).
"""
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import goal_state_reader_hook as gh

# _terminal_ok_marker existiert noch NICHT -> ImportError hier wuerde alles killen.
# Daher lazy-Import mit getattr in den Tests (AttributeError statt ImportError).
# (das Modul selbst ist importierbar, aber der Helfer fehlt)

HOOK = Path(gh.__file__)


def _mk_bl(backlog: Path, bl_id: str, status: str) -> None:
    """Spiegelt Floor-Helfer aus test_goal_state_reader_hook.py."""
    backlog.mkdir(parents=True, exist_ok=True)
    (backlog / f"{bl_id}-test-slug.md").write_text(
        f"---\nid: {bl_id}\nstatus: {status}\n---\n# {bl_id}\n", encoding="utf-8")


def _run(goal_text: str, tmp_path: Path, enforce: bool = False) -> dict:
    """Subprocess-Run mit OMNI_GOAL_MD / OMNI_GOAL_VAULT_ROOT / optional ENFORCE=1.
    BL-1 wird immer als DRAFT gesetzt (offene target_bls — das ist der load-bearing Punkt
    fuer AK-1/AK-3: gated GOAL + offene BLs -> SOLL trotzdem terminal-OK liefern).
    """
    _mk_bl(tmp_path / "Backlog", "BL-1", "DRAFT")
    goal = tmp_path / "GOAL.md"
    goal.write_text(goal_text, encoding="utf-8")
    env = os.environ.copy()
    env.update({
        "OMNI_GOAL_MD": str(goal),
        "OMNI_GOAL_VAULT_ROOT": str(tmp_path),
    })
    if enforce:
        env["OMNI_GOAL_STATE_READER_ENFORCE"] = "1"
    else:
        env.pop("OMNI_GOAL_STATE_READER_ENFORCE", None)
    r = subprocess.run(
        [sys.executable, str(HOOK)],
        input="",
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(r.stdout)


# ──────────────────────────────────────────────────────────
# UNIT: _terminal_ok_marker (existiert heute NICHT -> FAIL)
# ──────────────────────────────────────────────────────────

def test_terminal_ok_marker_detects_each():
    """Fuer jeden Marker einzeln: _terminal_ok_marker(text)[0] == True.
    RED heute: AttributeError ('goal_state_reader_hook' has no attribute '_terminal_ok_marker').
    """
    fn = getattr(gh, "_terminal_ok_marker", None)
    assert fn is not None, (
        "goal_state_reader_hook._terminal_ok_marker existiert nicht (AttributeError RED) — "
        "GREEN-Worker muss den Helfer bauen."
    )
    marker_texts = [
        # Frontmatter-Marker
        "dont_halt: true\n",
        "mode: gated-cutover-longrun\n",
        "mode: fresh-session-gated\n",
        "multi_session: true\n",
        "fresh_session_gated: true\n",
        "user_closed: true\n",
        "superseded_by: BL-999\n",
        # Prose-Marker (Body)
        "irgendwas\nFRESH-SESSION-ONLY bitte nicht anhalten\n",
        "SINGLE-STEP mode aktiv\n",
        "multi-session-prozess laueft\n",
        "deferiert bis BL-X fertig\n",
        "CLOSURE: superseded by BL-1\n",
        "superseded (alte BL)\n",
    ]
    for txt in marker_texts:
        ok, reason = fn(txt)
        assert ok is True, f"_terminal_ok_marker({txt!r}) sollte True liefern, got {ok!r}"
        assert reason, f"_terminal_ok_marker({txt!r}) sollte eine reason-str liefern, got {reason!r}"


def test_terminal_ok_marker_markerless_false():
    """NO-FALSE-PASS-SCOPE-Pinner: markerloser Text -> (False, ...).
    'mode: backlog' matcht NICHT /longrun|gated/ -> Helfer muss (False, '') liefern.
    RED heute: AttributeError (Helfer fehlt). Nach Bau: SCOPE-Schranke (pinnt GREEN auf SCOPED).
    """
    fn = getattr(gh, "_terminal_ok_marker", None)
    assert fn is not None, (
        "goal_state_reader_hook._terminal_ok_marker existiert nicht (AttributeError RED)."
    )
    ok, _ = fn("mode: backlog\ntarget_bls: [BL-1]\n")
    assert ok is False, (
        "_terminal_ok_marker('mode: backlog ...') muss False liefern — "
        "SCOPED, NICHT BREIT (no-false-pass AK-4)."
    )


# ──────────────────────────────────────────────────────────
# BEHAVIORAL main: gated terminal-OK (AK-1)
# ──────────────────────────────────────────────────────────

def test_main_gated_terminal_ok_with_open_bls(tmp_path):
    """gated GOAL.md + offene target_bls -> continue:true + terminal-OK-Message,
    SOWOHL ohne ENFORCE als auch MIT ENFORCE=1 (kurzschliesst VOR dem ENFORCE-Branch).
    RED heute:
      - ohne ENFORCE: Warn-Path -> continue:true ABER message "0/1 ...Offen" (kein terminal-OK)
      - mit ENFORCE=1: continue:false + "[ENFORCE]" (KEIN terminal-OK)
    """
    goal_text = "mode: gated-cutover-longrun\ndont_halt: true\ntarget_bls: [BL-1]\n"

    # --- OHNE ENFORCE ---
    out_warn = _run(goal_text, tmp_path, enforce=False)
    assert out_warn["continue"] is True, (
        "gated GOAL ohne ENFORCE: continue muss True sein."
    )
    msg_warn = out_warn.get("message", "")
    assert (
        "terminal-OK" in msg_warn
        or "gated" in msg_warn.lower()
        or "deferred" in msg_warn.lower()
        or "multi-session" in msg_warn.lower()
    ), (
        f"gated ohne ENFORCE: message soll terminal-OK/gated enthalten, got {msg_warn!r}. "
        "RED: ohne Marker-Logik steht hier '0/1 ...Offen' (kein terminal-OK)."
    )
    assert "0/1" not in msg_warn, (
        f"gated ohne ENFORCE: '0/1' in message ist ein RED-Signal (kein terminal-OK), got {msg_warn!r}."
    )

    # --- MIT ENFORCE=1 ---
    out_enforce = _run(goal_text, tmp_path, enforce=True)
    assert out_enforce["continue"] is True, (
        "gated GOAL MIT ENFORCE=1: continue MUSS True sein (kurzschliesst VOR ENFORCE-Branch). "
        f"RED heute: continue=False + '[ENFORCE]', got {out_enforce!r}."
    )
    msg_enforce = out_enforce.get("message", "")
    assert "0/1" not in msg_enforce, (
        f"gated MIT ENFORCE: '0/1' darf nicht in message stehen, got {msg_enforce!r}."
    )


# ──────────────────────────────────────────────────────────
# BEHAVIORAL main: user_closed terminal-OK (AK-3)
# ──────────────────────────────────────────────────────────

def test_main_user_closed_terminal_ok(tmp_path):
    """user_closed: true + offene target_bls + ENFORCE=1 -> continue:true + closed/terminal-OK.
    RED heute: kein Closure-Read -> ENFORCE-Block continue:false.
    """
    goal_text = "user_closed: true\ntarget_bls: [BL-1]\n"
    out = _run(goal_text, tmp_path, enforce=True)
    assert out["continue"] is True, (
        "user_closed GOAL MIT ENFORCE=1: continue MUSS True sein. "
        f"RED heute: continue=False (kein Closure-Read), got {out!r}."
    )
    msg = out.get("message", "").lower()
    assert (
        "terminal-ok" in msg
        or "closed" in msg
        or "superseded" in msg
        or "gated" in msg
        or "deferred" in msg
    ), (
        f"user_closed MIT ENFORCE: message soll closed/superseded/terminal-OK enthalten, got {out.get('message','')!r}."
    )


# ──────────────────────────────────────────────────────────
# BEHAVIORAL main: JSON fail-open bei Exception (AK-2)
# ──────────────────────────────────────────────────────────

def test_main_json_fail_open_on_exception(tmp_path, monkeypatch, capsys):
    """Injizierte Exception in gh.evaluate -> main() MUSS valides JSON ausgeben (continue:true).
    RED heute: kein top-level try/except -> Exception escaped -> kein/kaputtes stdout-JSON.
    Fixture: in-process via monkeypatch + capsys (deterministisch, kein subprocess-Rauschen).
    """
    # GOAL.md mit echten target_bls damit der target_bls0-Early-Return (Z149) NICHT greift
    goal = tmp_path / "GOAL.md"
    goal.write_text("mode: backlog\ntarget_bls: [BL-1]\n", encoding="utf-8")
    _mk_bl(tmp_path / "Backlog", "BL-1", "DRAFT")

    monkeypatch.setenv("OMNI_GOAL_MD", str(goal))
    monkeypatch.setenv("OMNI_GOAL_VAULT_ROOT", str(tmp_path))
    monkeypatch.delenv("OMNI_GOAL_STATE_READER_OFF", raising=False)
    monkeypatch.delenv("OMNI_GOAL_STATE_READER_ENFORCE", raising=False)

    # Exception in evaluate -> main() muss trotzdem JSON liefern
    def _boom(*a, **k):
        raise RuntimeError("injizierter boom fuer fail-open-Test")

    monkeypatch.setattr(gh, "evaluate", _boom)
    # sys.stdin patchen damit stdin.read() nicht blockiert
    monkeypatch.setattr("sys.stdin", io.StringIO(""))

    gh.main()

    captured = capsys.readouterr().out.strip()
    assert captured, (
        "main() hat NICHTS auf stdout ausgegeben nach injizierter Exception. "
        "RED: ohne top-level try/except crasht main() -> kein JSON."
    )
    try:
        out = json.loads(captured)
    except json.JSONDecodeError as e:
        pytest.fail(
            f"main() stdout ist kein valides JSON nach injizierter Exception: {captured!r} ({e}). "
            "RED: Exception escaped -> kaputtes/kein stdout-JSON."
        )
    assert out.get("continue") is True, (
        f"fail-open muss continue:true liefern, got {out!r}."
    )


# ──────────────────────────────────────────────────────────
# NO-FALSE-PASS KANARIE (spiegelt Z69-78 aus Floor-Suite)
# Muss JETZT schon gruen sein + nach GREEN-Build gruenbleiben.
# ──────────────────────────────────────────────────────────

def test_main_nongated_incomplete_still_blocks_under_enforce(tmp_path):
    """NON-gated + markerlos + DRAFT-BL + ENFORCE=1 -> continue:false + '0/1'.
    Spiegelt test_main_enforce_blocks_partial (Z69-78) in der neuen Test-Suite.
    MUSS heute schon gruen sein (Floor-Verhalten unveraendert).
    Pinnt: SCOPED Marker-Logik laesst markerlosen backlog-Mode UNVERAENDERT blockieren.
    """
    goal_text = "mode: backlog\ntarget_bls: [BL-1]\n"
    out = _run(goal_text, tmp_path, enforce=True)
    assert out["continue"] is False, (
        f"NON-gated markerlos ENFORCE: continue MUSS False sein (KANARIE/Floor). got {out!r}."
    )
    assert "0/1" in out.get("message", ""), (
        f"NON-gated markerlos ENFORCE: '0/1' muss in message sein. got {out.get('message','')!r}."
    )
