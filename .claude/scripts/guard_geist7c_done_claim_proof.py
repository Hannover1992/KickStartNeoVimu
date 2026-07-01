#!/usr/bin/env python3
"""
guard_geist7c_done_claim_proof.py — DONE-Claim-ohne-Test-Beweis-Detektor.

Schliesst die letzte Blindstelle (Independent_Observer_DCSRE-486_2026-05-28):
  Kein Hook prueft ob "verifiziert gruen" einen ECHTEN Test-Lauf hatte oder nur
  eine Behauptung ist. Round 16 hat es RICHTIG gemacht (verify_alt_marker, echte
  Re-Verify) — aber kein Hook ERZWINGT es.

Problem-Klasse:
  PL-Item wird [x] DONE markiert mit "verifiziert gruen" — aber ohne Test-Evidenz.
  = Behaupten statt Beweisen (Phantom-DONE auf Stage-Ebene).

Detektion (PreToolUse Edit/Write auf parking-lot.md / _manifest.md):
  WENN ein PL-Item auf [x] gesetzt wird (DONE-Transition)
  UND WEDER:
    (a) Test-Evidenz-Token im Claim-Text: \d+/\d+ (z.B. 813/813) ODER
        (passed|gruen|GREEN|PASS) + (build|test|karma|nx|dotnet|e2e|cypress)
    NOCH:
    (b) Test-Execution-Event im audit-Trail seit Batch-Start:
        SKILL_LOAD _TDD_execute / _I_verify / _T_orchestrate
  → WARN: DONE-Claim ohne sichtbaren Test-Beweis.

Default WARN (Sichtbarkeit) — Begruendung: Bash-Test-Laeufe (nx test/dotnet test)
landen NICHT in audit.jsonl (audit_hook matcht kein Bash). Daher kann ein echter
Test-Lauf unsichtbar sein. WARN macht "[x] ohne Zahlen/Beweis" sichtbar ohne legit
Done-Markierungen mit Evidenz zu brechen. Eskalation: OMNI_GEIST7C_ENFORCE=1.

Test-Override: OMNI_GEIST7C_AUDIT, OMNI_GEIST7C_ENFORCE. Off: OMNI_GEIST7C_OFF=1.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
AUDIT_FILE = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

PL_DONE_PATTERN = re.compile(r"###\s*\[x\]\s*PL-", re.IGNORECASE)

# Test-Evidenz im Claim-Text
NUM_RATIO = re.compile(r"\b\d+\s*/\s*\d+\b")  # 813/813, 188 / 188
PROOF_KEYWORDS = re.compile(
    r"(passed|gr[uü]en|GREEN|PASS)\b[\s\S]{0,40}\b(build|test|karma|nx|dotnet|e2e|cypress|suite)"
    r"|(build|test|karma|nx|dotnet|e2e|cypress|suite)\b[\s\S]{0,40}\b(passed|gr[uü]en|GREEN|PASS)",
    re.IGNORECASE,
)

# Test-Execution-Skills im audit
TEST_EXEC_SKILLS = ("_TDD_execute", "_I_verify", "_T_orchestrate")


def get_audit_path():
    return Path(os.environ.get("OMNI_GEIST7C_AUDIT", str(AUDIT_FILE)))


def read_enforce():
    return os.environ.get("OMNI_GEIST7C_ENFORCE") == "1"


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **GEIST7C_DONE_CLAIM_PROOF** [{action}]: {msg}\n")
    except Exception:
        pass


def has_audit_test_exec():
    """Gab es ein Test-Execution-Skill seit dem letzten _I_orchestrate / _SDF_orchestrate?"""
    audit = get_audit_path()
    if not audit.exists():
        return False
    try:
        lines = audit.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False
    # Scanne rueckwaerts bis zum letzten _I_orchestrate/_SDF_orchestrate (Batch-Anker)
    for i in range(len(lines) - 1, -1, -1):
        try:
            ev = json.loads(lines[i])
        except Exception:
            continue
        skill = ev.get("skill_name") or ev.get("skill") or ev.get("command") or ""
        if any(t in skill for t in TEST_EXEC_SKILLS):
            return True
        if skill in ("_I_orchestrate", "_SDF_orchestrate", "_BDF_orchestrate"):
            # Batch-Anker erreicht ohne Test-Exec gefunden → kein Beweis
            return False
    return False


def main():
    # === Globaler Owner-Kill-Switch (BL-210): enforceProcess=false -> Guard aus ===
    import os as _os, json as _json
    if _os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(_json.dumps({"continue": True}))
        return
    try:
        import sys as _sys
        from pathlib import Path as _P
        _sd = str(_P(__file__).parent.absolute())
        if _sd not in _sys.path:
            _sys.path.insert(0, _sd)
        from _enforce_gate import enforce_active
        if not enforce_active():
            print(_json.dumps({"continue": True}))
            return
    except Exception:
        pass
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    if os.environ.get("OMNI_GEIST7C_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    if event.get("tool_name") not in ("Edit", "Write"):
        print(json.dumps({"continue": True}))
        return

    ti = event.get("tool_input", {}) or {}
    fp = ti.get("file_path", "")
    new_text = ti.get("new_string", "") or ti.get("content", "")

    if "parking-lot.md" not in fp and "_manifest.md" not in fp:
        print(json.dumps({"continue": True}))
        return

    if not PL_DONE_PATTERN.search(new_text):
        print(json.dumps({"continue": True}))
        return

    # DONE-Transition. Evidenz im Text?
    has_text_proof = bool(NUM_RATIO.search(new_text)) or bool(PROOF_KEYWORDS.search(new_text))
    if has_text_proof:
        print(json.dumps({"continue": True}))  # konkrete Test-Zahlen/Beweis im Claim
        return

    # Kein Text-Beweis → audit-Trail?
    if has_audit_test_exec():
        print(json.dumps({"continue": True}))
        return

    # DONE-Claim ohne Text-Evidenz UND ohne audit-Test-Exec → Behaupten-Verdacht
    enforce = read_enforce()
    msg = (
        f"[GUARD-VIOLATION] GEIST7C_DONE_CLAIM_PROOF: PL-Item auf [x] gesetzt OHNE "
        f"Test-Beweis (weder Zahlen wie '813/813'/'passed'+Tool im Claim, noch "
        f"_TDD_execute/_I_verify/_T_orchestrate im audit-Trail). Behaupten statt Beweisen? "
        f"DONE-Markierung braucht Test-Evidenz (verify_alt_marker-Prinzip). "
        + ("BLOCKIERT." if enforce else "WARNED (Bash-Tests unsichtbar in audit; OMNI_GEIST7C_ENFORCE=1 fuer Block).")
    )
    append_guard_log(f"PL [x] ohne Test-Beweis ({Path(fp).name})", enforce)
    print(json.dumps({"continue": not enforce, "message": msg}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_geist7c ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
