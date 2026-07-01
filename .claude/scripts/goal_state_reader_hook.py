#!/usr/bin/env python3
"""Stop-Hook: Goal-State-Reader (BL-221, 2026-06-01).

ECHTE Goal-State-Validierung statt Termination-PROSA: liest .claude/GOAL.md, resolvet
die target_bls gegen ihren WAHREN Status (BL-File-Frontmatter, NICHT den stale
_backlog_index.md) und meldet X/N DONE + offene. Loest das Problem, das diese Session
mehrfach zeigte — der Goal-Stop-Hook feuerte auf 'nicht erfuellt', weil er nur die
Termination-Prosa las, nicht den echten State.

GOAL.md-Shape (real, AK-2 Drift-Fix): Frontmatter `mode` in {backlog_drain, backlog,
parking_lot} + `target_bls: [BL-229, ...]`. (NICHT `target_batch_key` — das war die BL-Annahme.)

Env:
  OMNI_GOAL_STATE_READER_OFF=1     -> Hook deaktiviert (continue:true)
  OMNI_GOAL_STATE_READER_ENFORCE=1 -> Hard-Block (continue:false) solange nicht alle DONE
  OMNI_GOAL_MD=<pfad>              -> GOAL.md-Override (Test)
  OMNI_GOAL_VAULT_ROOT=<pfad>      -> Vault-Override (Test)
  Default: Warn-Mode (continue:true + Real-State-Message).

Audit-Event: GOAL_STATE_VALIDATION.
JSON-Response: {"continue": true|false, "message": "..."}.
"""
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"
DONE_STATES = {"DONE"}   # terminal = Goal-erfuellt


def log_debug(msg):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] goal_state_reader_hook: {msg}\n")
    except Exception:
        pass


def _vault_root():
    ov = os.environ.get("OMNI_GOAL_VAULT_ROOT")
    if ov:
        return Path(ov)
    try:
        r = SCRIPT_DIR / "resolve_vault_root.py"
        if r.is_file():
            p = subprocess.run([sys.executable, str(r)], capture_output=True,
                               text=True, timeout=5, cwd=str(ROOT_DIR))
            if p.returncode == 0 and p.stdout.strip():
                return Path(p.stdout.strip())
    except Exception:
        pass
    return None


def _goal_path():
    ov = os.environ.get("OMNI_GOAL_MD")
    return Path(ov) if ov else (ROOT_DIR / ".claude" / "GOAL.md")


def parse_goal(goal_text):
    """Extrahiert (mode, target_bls) aus dem GOAL.md-Frontmatter (AK-2 reale Shape)."""
    mode = None
    m = re.search(r"^mode:\s*(\S+)", goal_text, re.MULTILINE)
    if m:
        mode = m.group(1).strip()
    bls = []
    # Inline-Liste: target_bls: [BL-229, BL-230, ...]
    m = re.search(r"^target_bls:\s*\[([^\]]*)\]", goal_text, re.MULTILINE)
    if m:
        bls = [b.strip() for b in m.group(1).split(",") if b.strip()]
    # Fallback: YAML-Block-Liste (- BL-x)
    if not bls:
        block = re.search(r"^target_bls:\s*\n((?:\s*-\s*\S+\s*\n?)+)", goal_text, re.MULTILINE)
        if block:
            bls = re.findall(r"-\s*(BL-\d+)", block.group(1))
    # nur echte BL-IDs (Sentinels wie ALL_OPEN ignorieren)
    bls = [b for b in bls if re.match(r"^BL-\d+$", b)]
    return mode, bls


def resolve_bl_status(vault, bl_id):
    """WAHRER Status aus dem BL-File-Frontmatter (autoritativ; der Index ist stale)."""
    if vault is None:
        return None
    backlog = vault / "Backlog"
    cands = list(backlog.glob(f"{bl_id}-*.md")) + list(backlog.glob(f"{bl_id}-*/{bl_id}-*.md"))
    cands = [c for c in cands if c.is_file()]
    if not cands:
        return None
    try:
        txt = cands[0].read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^status:\s*(\S+)", txt, re.MULTILINE)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return None


def emit_audit(payload):
    try:
        audit = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"
        if audit.parent.is_dir():
            with open(audit, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
    except Exception:
        pass


def evaluate(goal_text, vault):
    """Kern (test-bar): -> (all_done, done[], open[], mode, target_bls)."""
    mode, target_bls = parse_goal(goal_text)
    done, openn = [], []
    for bl in target_bls:
        st = resolve_bl_status(vault, bl)
        if st in DONE_STATES:
            done.append(bl)
        else:
            openn.append(f"{bl}({st or '?'})")
    return (len(openn) == 0 and len(target_bls) > 0), done, openn, mode, target_bls


def _terminal_ok_marker(goal_text):
    """Erkennt terminal-OK-Marker (gated/deferred/multi-session/user-closed/superseded).

    Reine, deterministische Funktion: -> (True, "<welcher Marker>") beim ersten Treffer,
    sonst (False, ""). SCOPED — markerloser Text (z.B. 'mode: backlog') liefert (False, '')
    (no-false-pass AK-4). 'mode:'-Wert muss /longrun|gated/ matchen, NICHT /backlog/.
    """
    if not goal_text:
        return (False, "")
    # Frontmatter-Marker (MULTILINE, case-insensitive)
    fm = [
        (r"^\s*fresh_session_gated:\s*true\b", "fresh_session_gated:true"),
        (r"^\s*multi_session:\s*true\b", "multi_session:true"),
        (r"^\s*dont_halt:\s*true\b", "dont_halt:true"),
        (r"^\s*user_closed:\s*true\b", "user_closed:true"),
        (r"^\s*superseded_by:\s*\S+", "superseded_by:"),
        (r"^\s*mode:\s*\S*(?:longrun|gated)\S*", "mode:longrun|gated"),
    ]
    for pat, label in fm:
        if re.search(pat, goal_text, re.MULTILINE | re.IGNORECASE):
            return (True, label)
    # Prose-Marker (case-insensitive). Reihenfolge: spezifischere zuerst.
    prose = [
        ("fresh-session-gated", "fresh-session-gated"),
        ("FRESH-SESSION", "FRESH-SESSION"),
        ("SINGLE-STEP", "SINGLE-STEP"),
        ("multi-session", "multi-session"),
        ("multi_session", "multi_session"),
        ("deferiert", "deferiert"),
        ("deferred", "deferred"),
        ("CLOSURE", "CLOSURE"),
        ("superseded", "superseded"),
    ]
    low = goal_text.lower()
    for needle, label in prose:
        if needle.lower() in low:
            return (True, label)
    return (False, "")


def main():
    if os.environ.get("OMNI_GOAL_STATE_READER_OFF") == "1":
        print(json.dumps({"continue": True}))
        return
    try:
        try:
            _ = sys.stdin.read()
        except Exception:
            pass

        goal = _goal_path()
        if not goal.is_file():
            print(json.dumps({"continue": True}))
            return
        try:
            gtext = goal.read_text(encoding="utf-8", errors="replace")
        except Exception:
            print(json.dumps({"continue": True}))
            return

        _, target_bls0 = parse_goal(gtext)
        if not target_bls0:
            # kein target_bls (z.B. ALL_OPEN self-discovering) -> nichts zu validieren
            print(json.dumps({"continue": True}))
            return

        # LOCUS-2: terminal-OK-Marker kurzschliesst VOR dem ENFORCE-Branch.
        # gated/deferred/multi-session/user-closed -> Goal pausiert legitim, KEIN Loop, KEIN Block.
        ok_marker, reason = _terminal_ok_marker(gtext)
        if ok_marker:
            emit_audit({"type": "GOAL_STATE_VALIDATION", "terminal_ok": True,
                        "marker": reason, "timestamp": datetime.now().isoformat()})
            log_debug(f"[GOAL-STATE] terminal-OK ({reason}) — kein Loop, Goal pausiert legitim.")
            print(json.dumps({"continue": True, "message": (
                f"[GOAL-STATE] terminal-OK ({reason}): gated/deferred/multi-session/user-closed "
                "— kein Loop, Goal pausiert legitim.")}))
            return

        vault = _vault_root()
        all_done, done, openn, mode, target_bls = evaluate(gtext, vault)

        emit_audit({"type": "GOAL_STATE_VALIDATION", "mode": mode, "target_bls": target_bls,
                    "done": done, "open": openn, "all_done": all_done,
                    "timestamp": datetime.now().isoformat()})

        if all_done:
            msg = (f"[GOAL-STATE] alle {len(done)} target_bls DONE (echte BL-File-Validierung, "
                   f"nicht Prosa) — Goal erfuellt: {', '.join(done)}")
            log_debug(msg)
            print(json.dumps({"continue": True, "message": msg}))
            return

        msg = (f"[GOAL-STATE] {len(done)}/{len(target_bls)} target_bls DONE (echte BL-File-Validierung). "
               f"Offen: {', '.join(openn)}.")
        log_debug(msg)
        if os.environ.get("OMNI_GOAL_STATE_READER_ENFORCE") == "1":
            print(json.dumps({"continue": False, "message": msg + " [ENFORCE] Stop blockiert bis alle DONE."}))
            return
        print(json.dumps({"continue": True, "message": msg}))
    except Exception:
        print(json.dumps({"continue": True}))
        return


if __name__ == "__main__":
    main()
