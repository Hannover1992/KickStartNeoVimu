#!/usr/bin/env python3
"""
guard_idf_sdf_handoff.py — IDF->SDF Handoff-Guard (BL-313 AK-1).

Spiegel von guard_a_idf_handoff.py (INV-A-GUARD-1-Analogon fuer den IDF->SDF-Seam).
Schliesst die Asymmetrie: A->IDF hat einen Erzwingungs-Guard (guard_a_idf_handoff.py,
INV-A-GUARD-1), IDF->SDF hatte bisher nur Lead-Pseudocode (Phase 8.5). Schreibt der Lead
die IDF-Ende-Transition (idf_status: "IDF_DONE" + SDF erwartet) OHNE vorausgehenden
Skill(_SDF_orchestrate)-Call, ist der Auto-Chain-Seam verletzt -> BLOCK + Recovery-Hint.

Ausnahmen (PASS, Spiegel von DEFER/A_RETRY = INV-A-EXCEPT-1): HiL-Modus (GLOBAL_HIL/hil: on)
-> manuelle Steuerung, kein Auto-Chain erzwungen; no_chain: true; from:-Feld != direct;
'SDF' nicht erwartet (-> has_signal schon false). -> kein Block.

Detektion (PreToolUse Edit/Write):
  WENN Edit/Write auf `_manifest.md`
  UND der Write enthaelt das IDF-Ende-Signal:
       - `idf_status: "IDF_DONE"`  UND  SDF-erwartet (`routing_target: "SDF"` oder 'SDF'-Token)
  UND KEINE Ausnahme (no_chain/HiL/from!=direct)
  UND seit letztem Skill(_IDF_orchestrate) KEIN Skill(_SDF_orchestrate) geladen
  -> IDF-Ende ohne SDF-Handoff (Bypass) -> sys.exit(2) + Recovery-Hint.

Template/Blaupause: guard_a_idf_handoff.py.
DIP-Analogon: Guard kennt NUR Manifest-State + audit, NICHT IDF-interne Ablauflogik.

Hinweis (Scope-Disziplin): enforce=false -> WARN-only (continue=true), harmlos. Das Tuning
des IDF-eigenen-Completion-Writes (false-Warn-Vermeidung) ist AK-5 forward-verify (Nicht-Ziel
dieses Guards).

Test-Override: OMNI_IDF_SDF_HANDOFF_AUDIT (audit-path). enforce: OMNI_SESSION_PARAMS
(enthaelt "enforceProcess: true"). Globaler Owner-Kill-Switch: OMNI_ENFORCE_ALL_OFF=1.
Lokaler Off: OMNI_IDF_SDF_HANDOFF_OFF=1.
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

# IDF-Ende-Signal: idf_status=IDF_DONE UND SDF-erwartet (beide im Manifest-Write)
IDF_DONE_PATTERN = re.compile(r'idf_status\s*:\s*"?IDF_DONE"?', re.IGNORECASE)
# BL-350 F9 Fix: NUR routing-FELD-Wert (routing_target:"SDF" ODER next_skill:_SDF_orchestrate),
# NICHT bare \bSDF\b (matchte 'Handoff -> SDF.' in IDF-internen Completion-Kommentaren -> FALSE POSITIVE
# auf finalSummary). Spiegel-Angleich an guard_a_idf_handoff (Feld-Wert statt Token/Prosa).
SDF_EXPECTED_PATTERN = re.compile(
    r'(routing_target\s*:\s*"?SDF"?|next_skill\s*:\s*"?_SDF_orchestrate)', re.IGNORECASE)
# Ausnahmen (PASS, Spiegel von DEFER/A_RETRY = INV-A-EXCEPT-1)
NO_CHAIN_PATTERN = re.compile(r"no_chain\s*:\s*true", re.IGNORECASE)
HIL_ON_PATTERN = re.compile(r"(GLOBAL_HIL|hil)\s*:?\s*\**\s*on\b", re.IGNORECASE)
# from:-Feld vorhanden UND != direct -> Handoff kam nicht direkt -> kein Auto-Chain erzwungen
FROM_NOT_DIRECT_PATTERN = re.compile(r"from\s*:\s*\"?(?!direct)\w+", re.IGNORECASE)

RECOVERY_HINT = "Rufe Skill(_SDF_orchestrate, args={bl-id} --resume)"

# Batch-Status-Erkennung fuer den Seam-Zweig (AK-a, BL-423)
BATCH_STATUS_READY_PATTERN = re.compile(r'batch_status\s*:\s*"?READY"?', re.IGNORECASE)


def read_batch_status():
    """Liest batch_status aus dem Manifest fuer den Seam-Zweig (IV-a2, BL-423 AK-a).

    Aufloesung:
    1. Env OMNI_IDF_SDF_HANDOFF_MANIFEST (Test-Override) — wenn gesetzt + Datei existiert.
    2. Sonst vault-resolved {vault_root}/_manifest.md via resolve_vault_root.py.
    3. FAIL-OPEN: Datei nicht lesbar / kein batch_status -> return None (kein Block).

    Returns 'READY' bei Match, None sonst. Jede Exception -> None (FAIL-OPEN).
    """
    try:
        manifest_override = os.environ.get("OMNI_IDF_SDF_HANDOFF_MANIFEST")
        if manifest_override:
            p = Path(manifest_override)
            if p.exists():
                txt = p.read_text(encoding="utf-8", errors="replace")
                if BATCH_STATUS_READY_PATTERN.search(txt):
                    return "READY"
                return None
            return None
        # Vault-resolved _manifest.md
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
                        cand = Path(vr) / "_manifest.md"
                        if cand.exists():
                            txt = cand.read_text(encoding="utf-8", errors="replace")
                            if BATCH_STATUS_READY_PATTERN.search(txt):
                                return "READY"
                            return None
        except Exception:
            pass
        return None
    except Exception:
        return None


def get_audit_path():
    return Path(os.environ.get("OMNI_IDF_SDF_HANDOFF_AUDIT", str(AUDIT_FILE)))


def _resolve_session_params():
    """Vault-resolved _session_params.md (kanonisch, wie guard_a_routing_target/guard_a_idf_handoff);
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
    """enforceProcess-Quelle (BL-350 F1-Klasse Fix): OMNI_SESSION_PARAMS (Test-Override) >
    vault-resolved _session_params.md (KANONISCHE Quelle — fehlte vorher, env-only-Bug = D5-Block-Ursache) >
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
            f.write(f"- [{ts}] **IDF_SDF_HANDOFF** [{action}]: {msg}\n")
    except Exception:
        pass


def sdf_ran_since_idf():
    """Scanne audit rueckwaerts. Returns (idf_active, sdf_since).
      idf_active: gab es ein _IDF_orchestrate SKILL_LOAD?
      sdf_since:  _SDF_orchestrate NACH letztem _IDF_orchestrate?
    """
    audit = get_audit_path()
    if not audit.exists():
        return False, True
    try:
        lines = audit.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False, True

    pos_idf = -1
    pos_sdf = -1
    for i in range(len(lines) - 1, -1, -1):
        try:
            ev = json.loads(lines[i])
        except Exception:
            continue
        skill = ev.get("skill_name") or ev.get("skill") or ""
        cmd = ev.get("command") or ""
        if pos_idf == -1 and ev.get("event") == "SKILL_LOAD" and "_IDF_orchestrate" in (skill or cmd):
            pos_idf = i
        if pos_sdf == -1 and ("_SDF_orchestrate" in skill or "_SDF_orchestrate" in cmd):
            pos_sdf = i
        if pos_idf != -1 and pos_sdf != -1:
            break

    idf_active = pos_idf != -1
    sdf_since = pos_sdf != -1 and pos_sdf >= pos_idf
    return idf_active, sdf_since


def main():
    # === Globaler Owner-Kill-Switch (BL-210): enforceProcess=false -> Guard aus ===
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return
    if os.environ.get("OMNI_IDF_SDF_HANDOFF_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    # === Seam-Zweig (AK-a, BL-423): Agent/TaskCreate + batch_status=READY ohne SDF-Handoff ===
    if event.get("tool_name") in ("Agent", "TaskCreate"):
        if read_batch_status() != "READY":
            print(json.dumps({"continue": True}))
            return
        idf_active, sdf_since = sdf_ran_since_idf()      # L133-164 unveraendert wiederverwendet
        if (not idf_active) or sdf_since:
            print(json.dumps({"continue": True}))
            return   # kein IDF / legitimer SDF-Handoff
        # batch_status=READY + IDF lief + KEIN SDF danach -> Build-Spawn-Bypass am Seam
        enforce = read_enforce()
        msg = ("[GUARD-VIOLATION] IDF_SDF_HANDOFF (SEAM): Build-Worker-Spawn ("
               + event.get("tool_name") + ") bei batch_status=READY OHNE Skill(_SDF_orchestrate) "
               "seit _IDF_orchestrate.\n  -> AUTO-CHAIN FEHLT (IDF->SDF Seam, BL-423 AK-a).\n"
               "  -> FIX: Lead laedt " + RECOVERY_HINT + " BEVOR Build-Worker spawnen. "
               + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARNED (enforceProcess=false Opt-out)."))
        append_guard_log("Build-Spawn (" + event.get("tool_name") + ") @ READY ohne _SDF_orchestrate", enforce)
        print(json.dumps({"continue": not enforce, "message": msg}))
        if enforce:
            sys.exit(2)
        return

    if event.get("tool_name") not in ("Edit", "Write"):
        print(json.dumps({"continue": True}))
        return

    ti = event.get("tool_input", {}) or {}
    fp = ti.get("file_path", "")
    new_text = ti.get("new_string", "") or ti.get("content", "")

    if "_manifest.md" not in fp:
        print(json.dumps({"continue": True}))
        return

    # IDF-Ende-Signal? idf_status=IDF_DONE UND SDF-erwartet
    has_signal = bool(IDF_DONE_PATTERN.search(new_text)) and bool(SDF_EXPECTED_PATTERN.search(new_text))
    if not has_signal:
        print(json.dumps({"continue": True}))
        return

    # Ausnahmen (INV-A-EXCEPT-1-Analogon): HiL-Modus / no_chain / from!=direct enden ohne Auto-Chain
    if (NO_CHAIN_PATTERN.search(new_text)
            or HIL_ON_PATTERN.search(new_text)
            or FROM_NOT_DIRECT_PATTERN.search(new_text)):
        print(json.dumps({"continue": True}))
        return

    # BL-365 AK-4: N=1-Fast-Path-Bypass — Manifest-Marker legitimiert das IDF-Ende ohne SDF-Handoff
    _BYPASS_PATTERN = re.compile(r'idf_bypass_reason\s*:\s*"?N=1_fastpath_BL-365"?', re.IGNORECASE)
    if _BYPASS_PATTERN.search(new_text):
        print(json.dumps({"continue": True}))
        return

    idf_active, sdf_since = sdf_ran_since_idf()

    if idf_active and sdf_since:
        # _SDF_orchestrate lief nach IDF -> legitimer Handoff
        print(json.dumps({"continue": True}))
        return

    # IDF-Ende-Signal geschrieben, ABER kein _SDF_orchestrate-Handoff -> Bypass
    enforce = read_enforce()
    msg = (
        f"[GUARD-VIOLATION] IDF_SDF_HANDOFF: IDF-Ende-Signal (idf_status=IDF_DONE, SDF erwartet) "
        f"in {Path(fp).name}, ABER kein Skill(_SDF_orchestrate) seit _IDF_orchestrate.\n"
        f"  -> AUTO-CHAIN FEHLT (IDF->SDF, BL-313 AK-1, Asymmetrie zum A->IDF-Guard).\n"
        f"  -> FIX: {RECOVERY_HINT}. "
        + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARNED (enforceProcess=false Opt-out).")
    )
    append_guard_log(f"IDF-Ende-Signal ohne _SDF_orchestrate ({Path(fp).name})", enforce)
    print(json.dumps({"continue": not enforce, "message": msg}))
    if enforce:
        sys.exit(2)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_idf_sdf_handoff ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
