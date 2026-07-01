#!/usr/bin/env python3
"""
guard_autochain_stop.py — SDF-Autochain-Stop-Guard (BL-394, INV-AUTOCHAIN-1 — Stop-Hook).

Schliesst die letzte un-geguardete Auto-Chain-Naht: die Sub-Batch->naechster-Sub-Batch-
Grenze im altmodischen (no-Motor) SDF-Pfad. Unter hil=off soll die Kette autonom
durchfliessen; der Lead fuegt aber ein konversationelles Confirm-Gate ein und pausiert.
Dieser Stop-Hook blockt/erinnert bei Turn-Ende, wenn hil=off UND ein pending nicht-
blockierter Sub-Batch offen ist UND kein Auto-Continue seit Batch-Ende sichtbar ist.

altmodisch-Analog von INV-MOTOR-1: weil der Workflow-Motor (dispatch_implement) gated-off
ist, braucht der altmodische Produktions-Pfad seinen eigenen strukturellen Loop-Schutz.

hook_event=Stop: laeuft bei Turn-Ende / Goal-Termination.

Soll-Semantik:
  1. Off-Switches: OMNI_ENFORCE_ALL_OFF=1 + OMNI_AUTOCHAIN_STOP_OFF=1 -> {"continue": true}.
  2. hil = read_hil_with_fallback(); hil != "off" -> {"continue": true}.
  3. pending_unblocked = batch_items_per_batch-Keys minus completed_sub_batches minus blocked.
  4. blocked = Keys mit blocked_by_external in {docker, token, user} (AK-2).
  5. auto_continue = audit-Rueckscan: _SDF_orchestrate --resume/--next-batch NACH letztem
     _SDF_orchestrate_post (Batch-Abschluss).
  6. VIOLATION = hil==off AND pending_unblocked != [] AND NOT auto_continue.
  7. VIOLATION + enforce=true -> {"continue": false} + sys.exit(2) + Recovery-Hint.
  8. VIOLATION + enforce=false -> WARN + {"continue": true}.
  9. Kein Manifest / kein pending / Auto-Continue lief -> fail-open {"continue": true}.

Test-Override:
  OMNI_AUTOCHAIN_STOP_AUDIT       audit-Pfad
  OMNI_SESSION_PARAMS             session_params-Pfad (enforceProcess + GLOBAL_HIL)
  OMNI_AUTOCHAIN_STOP_MANIFEST    manifest-Pfad
Globaler Off-Switch: OMNI_ENFORCE_ALL_OFF=1.
Lokaler Off-Switch: OMNI_AUTOCHAIN_STOP_OFF=1.

Template/Blaupause: guard_post_sdf_stop.py (BL-427) + guard_idf_sdf_handoff.py (BL-313/423,
read_batch_status Manifest-Regex-Read).
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

# AK-2: externe Blocker-Werte (SOA-1, aus DCSRE-1699)
_BLOCKED_EXTERNAL_VALUES = ("docker", "token", "user")

# Auto-Continue-Marker im audit (Resume/Next-Batch nach Batch-Ende)
_AUTOCONTINUE_RE = re.compile(r"--resume|--next-batch", re.IGNORECASE)

# hil-Regex (Fallback wenn session_params_resolver-Import scheitert)
_HIL_RE = re.compile(r"(GLOBAL_HIL|HiL|hil)\s*:?\s*\**\s*(\w+)", re.IGNORECASE)

RECOVERY_HINT = "Skill(_SDF_orchestrate --resume --next-batch); NICHT stoppen/fragen"


def get_audit_path():
    return Path(os.environ.get("OMNI_AUTOCHAIN_STOP_AUDIT", str(AUDIT_FILE)))


def get_manifest_path():
    """Manifest-Pfad: OMNI_AUTOCHAIN_STOP_MANIFEST (Test-Override) >
    vault-resolved {vault_root}/_manifest.md. None wenn nicht aufloesbar."""
    override = os.environ.get("OMNI_AUTOCHAIN_STOP_MANIFEST")
    if override:
        return Path(override)
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
                    return Path(vr) / "_manifest.md"
    except Exception:
        pass
    return None


def _resolve_session_params():
    """Vault-resolved _session_params.md (kanonisch, analog guard_post_sdf_stop);
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


def read_hil_with_fallback():
    """HiL-Wert: OMNI_SESSION_PARAMS (Test-Override) > vault-resolved _session_params.md.
    Bevorzugt session_params_resolver.read_hil_with_fallback (kanonisch); faellt auf
    lokalen _HIL_RE-Scan zurueck wenn Import scheitert. Default 'off' (fail-safe pass)."""
    sp = os.environ.get("OMNI_SESSION_PARAMS")
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from session_params_resolver import read_hil_with_fallback as _rhwf
        return _rhwf(sp)
    except Exception:
        pass
    # Lokaler Fallback (env-present-Pfad byte-gleich zum Resolver)
    try:
        if sp and Path(sp).exists():
            txt = Path(sp).read_text(encoding="utf-8", errors="replace")
        else:
            vsp = _resolve_session_params()
            txt = vsp.read_text(encoding="utf-8", errors="replace") if vsp.exists() else ""
        m = _HIL_RE.search(txt)
        if m:
            return m.group(2).lower()
    except Exception:
        pass
    return "off"


def _enforce_in_text(txt):
    """True/False aus enforceProcess-Zeile (bold **..** oder plain); None wenn nicht gefunden."""
    m = re.search(r"enforceProcess[\s:*]*\b(true|false)\b", txt, re.IGNORECASE)
    if m:
        return m.group(1).strip().lower() == "true"
    return None


def read_enforce():
    """enforceProcess-Quelle: OMNI_SESSION_PARAMS (Test-Override) >
    vault-resolved _session_params.md (kanonisch) > Default true."""
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
            f.write(f"- [{ts}] **AUTOCHAIN_STOP** [{action}]: {msg}\n")
    except Exception:
        pass


def _parse_manifest_sections(txt):
    """Parse DF_BATCH_STATE-Sub-Sektionen aus Manifest-Text.

    Returns (batch_keys, completed, blocked):
      batch_keys: Liste der Keys in batch_items_per_batch (Zeilen '    key: ...').
      completed:  Liste der Keys in completed_sub_batches (Zeilen '    - key').
      blocked:    Set der Keys mit blocked_by_external in {docker,token,user}
                  (aus blocked_sub_batches[] '- key:' + 'blocked_by_external:').
    """
    batch_keys = []
    completed = []
    blocked = set()

    # Aktuelle Sektion: 'items' | 'completed' | 'blocked' | None
    section = None
    pending_blocked_key = None  # Key des aktuellen '- key:'-Eintrags in blocked_sub_batches

    for raw in txt.splitlines():
        stripped = raw.strip()
        # Sektions-Header erkennen (z.B. 'batch_items_per_batch:')
        if re.match(r"^batch_items_per_batch\s*:", stripped):
            section = "items"
            continue
        if re.match(r"^completed_sub_batches\s*:", stripped):
            section = "completed"
            continue
        if re.match(r"^blocked_sub_batches\s*:", stripped):
            section = "blocked"
            pending_blocked_key = None
            continue

        # Neuer Top-Level-Key (kein eingerueckter Inhalt, endet mit ':') beendet Sektion
        # — aber NUR wenn es nicht selbst ein Listen-/Item-Eintrag ist.
        if stripped and not raw.startswith((" ", "\t")) and stripped.endswith(":"):
            section = None
            pending_blocked_key = None
            # weiter — koennte ein neuer Sektions-Header sein (oben schon gematcht)

        if section == "items":
            # '    batch_1: []' -> Key = 'batch_1'
            m = re.match(r"^([\w.\-]+)\s*:", stripped)
            if m and not stripped.startswith("-"):
                batch_keys.append(m.group(1))
        elif section == "completed":
            # '    - batch_1'
            m = re.match(r"^-\s*([\w.\-]+)\s*$", stripped)
            if m:
                completed.append(m.group(1))
        elif section == "blocked":
            # '    - key: batch_2'  /  '      blocked_by_external: docker'
            mkey = re.match(r"^-\s*key\s*:\s*([\w.\-]+)", stripped)
            if mkey:
                pending_blocked_key = mkey.group(1)
                continue
            mreason = re.match(r"^blocked_by_external\s*:\s*([\w.\-]+)", stripped)
            if mreason and pending_blocked_key is not None:
                if mreason.group(1).lower() in _BLOCKED_EXTERNAL_VALUES:
                    blocked.add(pending_blocked_key)

    return batch_keys, completed, blocked


def read_pending_unblocked(manifest_path=None):
    """Liest pending nicht-blockierte Sub-Batch-Keys aus dem Manifest.

    pending_unblocked = batch_items_per_batch-Keys MINUS completed_sub_batches MINUS blocked.
    blocked = Keys mit blocked_by_external in {docker,token,user} (AK-2).

    FAIL-OPEN: [] bei nicht lesbarem/fehlendem Manifest (kein Block ohne State).
    """
    mf = manifest_path if manifest_path is not None else get_manifest_path()
    if mf is None:
        return []
    mf = Path(mf)
    if not mf.exists():
        return []
    try:
        txt = mf.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []

    batch_keys, completed, blocked = _parse_manifest_sections(txt)
    completed_set = set(completed)
    pending = [k for k in batch_keys if k not in completed_set]
    pending_unblocked = [k for k in pending if k not in blocked]
    return pending_unblocked


def autocontinue_ran_since_batch_end(audit_path=None):
    """Scanne audit rueckwaerts. Returns True wenn ein _SDF_orchestrate-Load mit
    --resume/--next-batch NACH dem letzten _SDF_orchestrate_post (Batch-Abschluss)
    sichtbar ist (Auto-Continue lief).

    Analogon zu post_sdf_ran_since_i_sc() in guard_post_sdf_stop.py.
    FAIL-OPEN: kein Audit -> False (kein Auto-Continue bekannt; Block-faehig nur wenn
    pending existiert).
    """
    audit = Path(audit_path) if audit_path is not None else get_audit_path()
    if not audit.exists():
        return False
    try:
        lines = audit.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False

    pos_post = -1   # Index des letzten _SDF_orchestrate_post (Batch-Abschluss)
    pos_resume = -1  # Index des letzten _SDF_orchestrate --resume/--next-batch

    for i in range(len(lines) - 1, -1, -1):
        try:
            ev = json.loads(lines[i])
        except Exception:
            continue
        skill = ev.get("skill_name") or ev.get("skill") or ev.get("command") or ""
        skill_str = str(skill)
        args_str = str(ev.get("args") or ev.get("arguments") or "")

        if pos_post == -1 and "_SDF_orchestrate_post" in skill_str:
            pos_post = i

        # _SDF_orchestrate (NICHT _post) SKILL_LOAD mit --resume/--next-batch
        if pos_resume == -1 and ev.get("event") == "SKILL_LOAD" \
                and "_SDF_orchestrate" in skill_str and "_SDF_orchestrate_post" not in skill_str:
            if _AUTOCONTINUE_RE.search(args_str) or _AUTOCONTINUE_RE.search(skill_str):
                pos_resume = i

        if pos_post != -1 and pos_resume != -1:
            break

    # Auto-Continue gilt als "since batch end" wenn es NACH (groesserer Index) dem
    # letzten Batch-Abschluss kam. Kein Batch-Abschluss bekannt (pos_post==-1) ->
    # jeder gesehene Resume zaehlt.
    if pos_resume == -1:
        return False
    if pos_post == -1:
        return True
    return pos_resume > pos_post


def main():
    # === Off-Switches ===
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return
    if os.environ.get("OMNI_AUTOCHAIN_STOP_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    try:
        _event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    # === hil-Gate: nur unter hil=off greift der Autochain-Schutz ===
    hil = read_hil_with_fallback()
    if hil != "off":
        print(json.dumps({"continue": True}))
        return

    # === Pending-Detektion (AK-1 + AK-2 Blocker-Filter) ===
    pending_unblocked = read_pending_unblocked()
    if not pending_unblocked:
        # kein pending nicht-blockiert (alle completed/blocked ODER fail-open []) -> pass
        print(json.dumps({"continue": True}))
        return

    # === Auto-Continue-Detektion ===
    if autocontinue_ran_since_batch_end():
        print(json.dumps({"continue": True}))
        return

    # === VIOLATION: hil=off + pending nicht-blockiert + kein Auto-Continue ===
    enforce = read_enforce()
    msg = (
        f"[GUARD-VIOLATION] AUTOCHAIN_STOP: Turn-Ende unter hil=off mit pending "
        f"nicht-blockiertem Sub-Batch {pending_unblocked} OHNE Auto-Continue.\n"
        f"  -> INV-AUTOCHAIN-1 verletzt: altmodischer SDF-Pfad muss autonom durchfliessen "
        f"(kein Confirm-Gate an der Batch-Grenze, BL-394).\n"
        f"  -> FIX: hil=off + pending Arbeit -> {RECOVERY_HINT}. "
        + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARN (enforceProcess=false Opt-out).")
    )
    append_guard_log(
        f"Turn-Ende unter hil=off mit pending nicht-blockiert {pending_unblocked} ohne Auto-Continue",
        enforce,
    )

    if enforce:
        print(json.dumps({"continue": False, "message": msg}))
        sys.exit(2)
    else:
        print(json.dumps({"continue": True, "message": msg}), file=sys.stderr)
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_autochain_stop ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
