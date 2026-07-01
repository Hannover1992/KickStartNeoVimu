#!/usr/bin/env python3
"""
guard_a_idf_handoff.py — A->IDF Handoff-Guard (BL-226 AK-4, INV-A-GUARD-1; BL-350 enforce-AFTER-write).

Schliesst die A-Ende-Luecke (BL-226): bei `routing=proceed` + `idf_invoke_required=true`
im `_manifest.md` MUSS der A-Exit deterministisch ueber `_A_postRoute` -> `_IDF_orchestrate`
laufen (1-Seam-Chain, kein BDF-Polling-Roundtrip).

BL-350 AK-2 (enforce-AFTER-write Redesign): Der Enforcement-Punkt liegt NICHT mehr auf dem
Signal-Write (PreToolUse Edit/Write) — der war ein un-erfuellbares Pre-Block (Henne-Ei):
`_A_postRoute` SCHREIBT genau dieses A-Ende-Signal legitim, ein Pre-Block des Writes ist eine
Wand. Stattdessen wird der FOLGE-Schritt geprueft: der IDF-Eintritt (Skill-Load `_IDF_orchestrate`).
Vorbild: guard_geist9b_sdf_post_inline.py (Enforcement am Folge-Schritt statt am Write).

Detektion:
  TRIGGER A (enforce-AFTER-write, BL-350 AK-2) — Skill-Load `_IDF_orchestrate`:
    WENN PreToolUse Skill-Load von `_IDF_orchestrate`
    UND seit letztem Skill(_A_orchestrate) KEIN Skill(_A_postRoute) geladen (Handoff-Seam verletzt)
    -> IDF-Eintritt ohne A_postRoute-Handoff (Bypass) -> sys.exit(2) + Recovery-Hint.

  TRIGGER B (Signal-Write, Edit/Write auf `_manifest.md`):
    Der Signal-Write (idf_invoke_required: true + routing_target: "IDF" im A_PIPELINE_STATE-Block)
    wird IMMER durchgelassen (continue=True). Kein Pre-Block mehr — `_A_postRoute` muss diesen
    Write machen koennen. Block-scoped Detektion (BL-350 AK-1, F2) bleibt fuer korrektes
    Signal-Logging/Recognition erhalten (kein Over-Match auf BERATER_OUTPUTS-Prosa).

Ausnahme (INV-A-EXCEPT-1): DEFER- oder A_RETRY-Marker enden A-intern (kein IDF-Handoff erwartet)
-> kein Block (sowohl auf Write-Pfad als auch beim IDF-Eintritt irrelevant, da A-intern beendet).

Template/Blaupause: guard_geist9b_sdf_post_inline.py.
DIP-Analogon: Guard kennt NUR Manifest-State + audit, NICHT A-interne Ablauflogik.

Test-Override: OMNI_A_IDF_HANDOFF_AUDIT (audit-path). enforce: OMNI_SESSION_PARAMS
(enthaelt "enforceProcess: true"). Globaler Owner-Kill-Switch: OMNI_ENFORCE_ALL_OFF=1.
Lokaler Off: OMNI_A_IDF_HANDOFF_OFF=1.
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
AUDIT_FILE = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# A-Ende-Signal (routing=proceed): beide Marker im Manifest-Write
IDF_REQUIRED_PATTERN = re.compile(r"idf_invoke_required\s*:\s*true", re.IGNORECASE)
ROUTING_TARGET_IDF_PATTERN = re.compile(r'routing_target\s*:\s*"?IDF"?', re.IGNORECASE)
# A-interne Endzustaende (INV-A-EXCEPT-1): kein IDF-Handoff erwartet
DEFER_RETRY_PATTERN = re.compile(r"\b(DEFER|A_RETRY)\b")

RECOVERY_HINT = "Rufe Skill(_A_postRoute, args={bl-id}) -> _IDF_orchestrate"

# Patterns matching block headers (top-level heading or YAML-key at col 0)
_BLOCK_HEADER_PATTERN = re.compile(
    r"^(?:#{1,6}\s+\S|[A-Z][A-Z_0-9]*:)", re.MULTILINE
)
# Pattern matching the A_PIPELINE_STATE block header itself
_A_STATE_HEADER_PATTERN = re.compile(
    r"^(?:#{1,6}\s+)?A_PIPELINE_STATE\s*:?\s*$", re.MULTILINE | re.IGNORECASE
)


def _extract_a_pipeline_state_block(text: str) -> str:
    """Extracts only the A_PIPELINE_STATE block from a manifest text.

    Searches for a header matching 'A_PIPELINE_STATE' (YAML-key or heading),
    then returns all lines up to (but not including) the next top-level block
    header or end of file.  Returns '' when no such block is present (fail-safe).
    """
    m = _A_STATE_HEADER_PATTERN.search(text)
    if not m:
        return ""

    block_start = m.start()
    # Look for the next top-level block header after the A_PIPELINE_STATE header
    search_from = m.end()
    # Find next separator: "---" line OR another top-level heading/YAML-key
    _next_block = re.compile(
        r"^(?:---+\s*$|#{1,6}\s+\S|[A-Z][A-Z_0-9]*:\s*$)", re.MULTILINE
    )
    next_m = _next_block.search(text, search_from)
    if next_m:
        return text[block_start:next_m.start()]
    return text[block_start:]


def get_audit_path():
    return Path(os.environ.get("OMNI_A_IDF_HANDOFF_AUDIT", str(AUDIT_FILE)))


def _resolve_session_params():
    """Vault-resolved _session_params.md (kanonisch, wie guard_a_routing_target);
    Fallback ROOT_DIR/_session_params.md."""
    try:
        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True, text=True, timeout=5, cwd=str(ROOT_DIR),
            )
            if proc.returncode == 0:
                vr = proc.stdout.strip()
                if vr:
                    cand = Path(vr) / "_session_params.md"
                    if cand.exists():
                        return cand
    except Exception:
        pass
    return ROOT_DIR / "_session_params.md"


def _enforce_in_text(txt):
    """True/False aus enforceProcess-Zeile (bold **..** oder plain); None wenn nicht gefunden."""
    m = re.search(r"enforceProcess[\s:*]*\b(true|false)\b", txt, re.IGNORECASE)
    if m:
        return m.group(1).strip().lower() == "true"
    return None


def read_enforce():
    """enforceProcess-Quelle (BL-350 Fix): OMNI_SESSION_PARAMS (Test-Override) >
    vault-resolved _session_params.md (KANONISCHE Quelle — fehlte vorher, env-only-Bug) >
    Default true. BLOCK bleibt Default NUR wenn KEINE Config gefunden (Handoff-Seam-Intent)."""
    sp = os.environ.get("OMNI_SESSION_PARAMS")
    if sp and Path(sp).exists():
        try:
            v = _enforce_in_text(Path(sp).read_text(encoding="utf-8", errors="replace"))
            if v is not None:
                return v
        except Exception:
            pass
        return True
    try:
        vsp = _resolve_session_params()
        if vsp.exists():
            v = _enforce_in_text(vsp.read_text(encoding="utf-8", errors="replace"))
            if v is not None:
                return v
    except Exception:
        pass
    return True


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **A_IDF_HANDOFF** [{action}]: {msg}\n")
    except Exception:
        pass


def _is_idf_orchestrate_skill_load(tool_name, tool_input):
    """True wenn der PreToolUse-Event ein Skill-Load von _IDF_orchestrate ist (BL-350 AK-2, SOA-1).

    Skill-Loads erscheinen als Tool-Event mit dem Skill-Namen im tool_input. Wir matchen
    tolerant ueber mehrere moegliche Schluessel (skill_name/skill/name) und akzeptieren den
    execute_skill-Tool-Namen (mcp__claude_ai__execute_skill o.ae.). Substring-Match auf
    '_IDF_orchestrate' deckt args-Varianten ab.
    """
    if not tool_name or "execute_skill" not in str(tool_name).lower():
        return False
    if not isinstance(tool_input, dict):
        return False
    skill = (
        tool_input.get("skill_name")
        or tool_input.get("skill")
        or tool_input.get("name")
        or ""
    )
    return "_IDF_orchestrate" in str(skill)


def postroute_ran_since_a_pipeline():
    """Scanne audit rueckwaerts. Returns (a_active, postroute_since).
      a_active:        gab es ein _A_orchestrate SKILL_LOAD?
      postroute_since: _A_postRoute NACH letztem _A_orchestrate?
    """
    audit = get_audit_path()
    if not audit.exists():
        return False, True
    try:
        lines = audit.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False, True

    pos_a = -1
    pos_pr = -1
    for i in range(len(lines) - 1, -1, -1):
        try:
            ev = json.loads(lines[i])
        except Exception:
            continue
        skill = ev.get("skill_name") or ev.get("skill") or ""
        cmd = ev.get("command") or ""
        if pos_a == -1 and ev.get("event") == "SKILL_LOAD" and "_A_orchestrate" in (skill or cmd):
            pos_a = i
        if pos_pr == -1 and ("_A_postRoute" in skill or "_A_postRoute" in cmd):
            pos_pr = i
        if pos_a != -1 and pos_pr != -1:
            break

    a_active = pos_a != -1
    postroute_since = pos_pr != -1 and pos_pr >= pos_a
    return a_active, postroute_since


def main():
    # === Globaler Owner-Kill-Switch (BL-210): enforceProcess=false -> Guard aus ===
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return
    if os.environ.get("OMNI_A_IDF_HANDOFF_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    tool_name = event.get("tool_name")
    ti = event.get("tool_input", {}) or {}

    # === TRIGGER A (enforce-AFTER-write, BL-350 AK-2): Skill-Load _IDF_orchestrate ===
    # Der ECHTE Enforcement-Punkt: nicht der Write, sondern der IDF-Eintritt.
    # _IDF_orchestrate darf nur via _A_postRoute -> _IDF_orchestrate-Seam aufgerufen werden.
    if _is_idf_orchestrate_skill_load(tool_name, ti):
        a_active, postroute_since = postroute_ran_since_a_pipeline()
        if (not a_active) or postroute_since:
            # Keine A-Pipeline lief (nicht A-Exit-Kontext) ODER _A_postRoute lief -> legitim
            print(json.dumps({"continue": True}))
            return
        # BL-365 AK-4: N=1-Fast-Path-Bypass — Env-Marker legitimiert den Eintritt ohne postRoute
        bypass_reason = os.environ.get("OMNI_IDF_BYPASS_REASON", "")
        if bypass_reason == "N=1_fastpath_BL-365":
            print(json.dumps({"continue": True}))
            return

        # A-Pipeline lief, ABER kein _A_postRoute danach -> IDF-Eintritt umgeht den Handoff-Seam
        enforce = read_enforce()
        msg = (
            f"[GUARD-VIOLATION] A_IDF_HANDOFF: Skill-Load _IDF_orchestrate OHNE vorausgehenden "
            f"Skill(_A_postRoute) seit _A_orchestrate.\n"
            f"  -> HANDOFF FEHLT: A chaint deterministisch ueber _A_postRoute -> _IDF_orchestrate "
            f"(1-Seam, kein BDF-Polling-Roundtrip; INV-A-GUARD-1).\n"
            f"  -> FIX: {RECOVERY_HINT}. "
            + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARNED (enforceProcess=false Opt-out).")
        )
        append_guard_log("IDF-Eintritt (_IDF_orchestrate) ohne _A_postRoute", enforce)
        print(json.dumps({"continue": not enforce, "message": msg}))
        if enforce:
            sys.exit(2)
        return

    # === TRIGGER B (Signal-Write, Edit/Write): IMMER durchlassen (enforce-AFTER-write) ===
    # Kein Pre-Block mehr: _A_postRoute SCHREIBT das A-Ende-Signal legitim — ein Pre-Block
    # waere eine un-erfuellbare Wand (Henne-Ei). Enforcement liegt am Folge-Schritt (TRIGGER A).
    # Block-scoped Signal-Detektion (BL-350 AK-1, F2) bleibt fuer korrektes Recognition/Logging.
    if tool_name not in ("Edit", "Write"):
        print(json.dumps({"continue": True}))
        return

    fp = ti.get("file_path", "")
    new_text = ti.get("new_string", "") or ti.get("content", "")

    if "_manifest.md" not in fp:
        print(json.dumps({"continue": True}))
        return

    # A-Ende-Signal (routing=proceed)? — block-scoped (BL-350 F2/AK-1):
    # BEIDE Signal-Strings muessen im A_PIPELINE_STATE-Block stehen (nicht im ganzen Manifest).
    _state_block = _extract_a_pipeline_state_block(new_text)
    has_signal = bool(IDF_REQUIRED_PATTERN.search(_state_block)) and bool(ROUTING_TARGET_IDF_PATTERN.search(_state_block))
    if has_signal and not DEFER_RETRY_PATTERN.search(new_text):
        # Signal erkannt (block-scoped) — protokolliere zur Nachvollziehbarkeit, blocke aber NICHT.
        # (enforce-AFTER-write: der Write ist immer erlaubt; Enforcement am IDF-Eintritt, TRIGGER A.)
        append_guard_log(f"A-Ende-Signal-Write durchgelassen (enforce-AFTER-write, {Path(fp).name})", False)

    # Signal-Write IMMER durchlassen (BL-350 AK-2).
    print(json.dumps({"continue": True}))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_a_idf_handoff ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
