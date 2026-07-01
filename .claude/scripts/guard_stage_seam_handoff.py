#!/usr/bin/env python3
"""
guard_stage_seam_handoff.py — Stage-/Batch-Ende Commit-Seam-Guard (BL-295 AK-6).

Spiegel von guard_idf_sdf_handoff.py (BL-313) + geist9b (Commit-Seam-Klasse). Schliesst die
BL-295-Wurzel STRUKTURELL: der Commit-Step (_stage_orchestrate = Security-Gate + Commit-Normierung)
darf nicht still uebersprungen werden — und kein Go-Gate bei hil=off eingefuegt werden. Schreibt
der Lead die Stage-/Batch-Ende-Progression (stage_done / completed_sub_batches / [ ]->[x]-Commit-
Marker) WAEHREND Stage-GREEN / I-Ende erreicht ist, OHNE vorausgehenden Skill(_stage_orchestrate)-
Call, ist der Commit-Seam verletzt -> BLOCK + Recovery-Hint.

Ausnahme (PASS, Spiegel von DEFER/A_RETRY = INV-A-EXCEPT-1): hil != off (HiL-Modus DARF ein
Go-Gate setzen / manuell steuern) -> kein Auto-Commit-Seam erzwungen; no_chain: true.

Detektion (PreToolUse Edit/Write):
  Fall (a) — Seam-Skip (primaer, mechanisch testbar, geist9b-Klasse):
    WENN Edit/Write auf `_manifest.md` (oder PL-Master)
    UND der Write enthaelt eine Stage-/Batch-Ende-Progression:
         - `stage_done: true`  ODER  `completed_sub_batches: [...]`  ODER  ein `[x]`-Commit-Marker
    UND hil == off (kein Go-Gate erlaubt) UND KEIN no_chain
    UND seit letztem Stage-GREEN / Skill(_I_orchestrate)-Ende KEIN Skill(_stage_orchestrate) geladen
    -> Commit-Seam (Normierung + Security-Gate) uebersprungen -> sys.exit(2) + Recovery-Hint.
  Fall (b) — Go-Gate-Einfuegung bei hil=off (best-effort):
    Wenn der Write einen Go-Gate/Confirm-Marker traegt (`Go fuer`, `Sag .*go`, `Confirm`) UND
    hil == off -> Gate-Insertion bei hil=off -> ebenfalls FIRE (gleiche msg-Klasse). Wenn der
    Marker NICHT mechanisch im Edit-Text steht: ueber Fall (a) + Recovery-Hint + AK-5-Forward-
    Verify abgedeckt (ehrlich vermerkt, Nicht-Ziel der mechanischen Detektion).

Template/Blaupause: guard_idf_sdf_handoff.py (BL-313), geist9b. PT-GEN-HookGuard-Mirror (3. Instanz).
DIP-Analogon: Guard kennt NUR Manifest-State + audit + Session-Params, NICHT SDF-/I-interne Ablauflogik.

Hinweis (Scope-Disziplin): enforce=false -> WARN-only (continue=true), harmlos. Fall (b) ist
best-effort (nur soweit mechanisch im Edit-Text erkennbar) — der Rest ist AK-5 forward-verify
(Nicht-Ziel der mechanischen Detektion dieses Guards).

Test-Override: OMNI_STAGE_SEAM_AUDIT (audit-path). enforce + HiL: OMNI_SESSION_PARAMS
(enthaelt "enforceProcess: true/false" und "HiL: off/cycle/..."). Globaler Owner-Kill-Switch:
OMNI_ENFORCE_ALL_OFF=1. Lokaler Off: OMNI_STAGE_SEAM_OFF=1. Audit-env: OMNI_STAGE_SEAM_AUDIT.
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

# Stage-/Batch-Ende-Progressions-Signal (eines reicht -> has_signal)
STAGE_DONE_PATTERN = re.compile(r"stage_done\s*:\s*true", re.IGNORECASE)
COMPLETED_SUB_BATCHES_PATTERN = re.compile(r"completed_(round\d+_)?sub_batches\s*:", re.IGNORECASE)
# [x]-Commit/Done-Marker: PL-Item-Checkbox abgehakt ODER status: done
DONE_MARKER_PATTERN = re.compile(r"(^|\n)\s*[-#]*\s*\[x\]", re.IGNORECASE)
STATUS_DONE_PATTERN = re.compile(r"status\s*:?\s*\**\s*done", re.IGNORECASE)
# Ausnahme (PASS, Spiegel von DEFER/A_RETRY = INV-A-EXCEPT-1)
NO_CHAIN_PATTERN = re.compile(r"no_chain\s*:\s*true", re.IGNORECASE)
# Fall (b) — Go-Gate/Confirm-Marker (best-effort)
GO_GATE_PATTERN = re.compile(r"(Go\s+f[uü]r|Sag\b.*\bgo\b|Confirm)", re.IGNORECASE)

RECOVERY_HINT = "Rufe Skill(_stage_orchestrate, args={bl-id})"


def get_audit_path():
    return Path(os.environ.get("OMNI_STAGE_SEAM_AUDIT", str(AUDIT_FILE)))


def read_enforce():
    """enforceProcess fuer den Guard (BL-343 PL-343-2).

    env-PRESENT (OMNI_SESSION_PARAMS gesetzt + existent): byte-gleiche Bestands-Logik
    (enforceProcess:false -> False, sonst BLOCK-Default True) — getragen vom Helper, der
    dieselbe Match-Logik nutzt. env-ABSENT (Normalfall in der Maschine, Harness ruft den
    Guard ohne gesetztes OMNI_SESSION_PARAMS): NICHT mehr blind BLOCK-Default, sondern
    Fallback auf den self-resolvbaren Session-State (resolve_param('enforceProcess'),
    honoriert OMNI_VAULT_ROOT). Resolver-/Import-Fehler -> fail-safe BLOCK-Default True."""
    sp = os.environ.get("OMNI_SESSION_PARAMS")
    try:
        import session_params_resolver as spr
        return spr.read_enforce_with_fallback(sp)
    except Exception:
        # Helper nicht ladbar -> heutige env-only-Logik als fail-safe (BLOCK-Default).
        if sp and Path(sp).exists():
            try:
                txt = Path(sp).read_text(encoding="utf-8", errors="replace")
                if re.search(r"enforceProcess\s*:?\*?\*?\s*false", txt, re.IGNORECASE):
                    return False
            except Exception:
                pass
        return True


def read_hil():
    """HiL-Wert fuer den Guard (BL-343 PL-343-2). hil != off -> HiL DARF Go-Gate (PASS).

    env-PRESENT: byte-gleiche Bestands-Logik (erster Wert lowercased, sonst 'off'). env-
    ABSENT: Fallback auf resolve_param('hil') (self-resolving). Fehler -> 'off' (fail-safe)."""
    sp = os.environ.get("OMNI_SESSION_PARAMS")
    try:
        import session_params_resolver as spr
        return spr.read_hil_with_fallback(sp)
    except Exception:
        if sp and Path(sp).exists():
            try:
                txt = Path(sp).read_text(encoding="utf-8", errors="replace")
                m = re.search(r"(GLOBAL_HIL|HiL|hil)\s*:?\s*\**\s*(\w+)", txt, re.IGNORECASE)
                if m:
                    return m.group(2).lower()
            except Exception:
                pass
        return "off"


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **STAGE_SEAM_HANDOFF** [{action}]: {msg}\n")
    except Exception:
        pass


def stage_orchestrate_ran_since_stage_green():
    """Scanne audit rueckwaerts. Returns (green_active, so_since).
      green_active: gab es ein Stage-GREEN / _I_orchestrate SKILL_LOAD (I-Ende-Proxy)?
      so_since:     _stage_orchestrate NACH letztem Stage-GREEN?
    Kein audit -> (False, True) wie Vorbild (kein I-Ende -> kein Commit-Seam-Kontext)."""
    audit = get_audit_path()
    if not audit.exists():
        return False, True
    try:
        lines = audit.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False, True

    pos_green = -1
    pos_so = -1
    for i in range(len(lines) - 1, -1, -1):
        try:
            ev = json.loads(lines[i])
        except Exception:
            continue
        skill = ev.get("skill_name") or ev.get("skill") or ""
        cmd = ev.get("command") or ""
        marker = ev.get("event") or ""
        # Stage-GREEN-Proxy: _I_orchestrate SKILL_LOAD (I-Ende = Stage-GREEN) ODER Stage-GREEN-Marker
        if pos_green == -1 and (
            (marker == "SKILL_LOAD" and "_I_orchestrate" in (skill or cmd))
            or "STAGE_GREEN" in marker.upper()
        ):
            pos_green = i
        if pos_so == -1 and ("_stage_orchestrate" in skill or "_stage_orchestrate" in cmd):
            pos_so = i
        if pos_green != -1 and pos_so != -1:
            break

    green_active = pos_green != -1
    so_since = pos_so != -1 and pos_so >= pos_green
    return green_active, so_since


def main():
    # === Globaler Owner-Kill-Switch (BL-210): enforceProcess=false global -> Guard aus ===
    if os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(json.dumps({"continue": True}))
        return
    if os.environ.get("OMNI_STAGE_SEAM_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    if event.get("tool_name") not in ("Edit", "Write"):
        print(json.dumps({"continue": True}))
        return

    ti = event.get("tool_input", {}) or {}
    fp = ti.get("file_path", "")
    new_text = ti.get("new_string", "") or ti.get("content", "")

    is_manifest = "_manifest.md" in fp or "_factory_manifest.md" in fp
    is_pl = "parking-lot.md" in fp
    if not (is_manifest or is_pl):
        print(json.dumps({"continue": True}))
        return

    # Stage-/Batch-Ende-Progressions-Signal? (eines reicht)
    has_signal = bool(
        STAGE_DONE_PATTERN.search(new_text)
        or COMPLETED_SUB_BATCHES_PATTERN.search(new_text)
        or DONE_MARKER_PATTERN.search(new_text)
        or STATUS_DONE_PATTERN.search(new_text)
    )
    if not has_signal:
        print(json.dumps({"continue": True}))
        return

    # Ausnahme (INV-A-EXCEPT-1-Analogon): no_chain endet ohne Auto-Seam
    if NO_CHAIN_PATTERN.search(new_text):
        print(json.dumps({"continue": True}))
        return

    # hil-Resolve (Spiegel DEFER/A_RETRY-Ausnahme): hil != off -> HiL DARF Go-Gate -> PASS
    hil = read_hil()
    if hil != "off":
        print(json.dumps({"continue": True}))
        return

    green_active, so_since = stage_orchestrate_ran_since_stage_green()

    if green_active and so_since:
        # _stage_orchestrate lief nach Stage-GREEN -> legitimer Commit-Seam (Gate + Normierung lief)
        print(json.dumps({"continue": True}))
        return

    # Stage-Ende-Progression geschrieben, ABER kein _stage_orchestrate-Seam -> Bypass.
    # Fall (b) (best-effort): Go-Gate-Marker bei hil=off ist dieselbe Verletzungs-Klasse.
    has_go_gate = bool(GO_GATE_PATTERN.search(new_text))
    enforce = read_enforce()
    fall = "Go-Gate bei hil=off eingefuegt" if has_go_gate else "Commit-Seam uebersprungen"
    msg = (
        f"[GUARD-VIOLATION] STAGE_SEAM: Stage-Ende-Progression in {Path(fp).name} ohne "
        f"Skill(_stage_orchestrate) seit Stage-GREEN — {fall} (Normierung + Security-Gate) "
        f"ODER Go-Gate bei hil=off eingefuegt (BL-295 AK-6, DCSRE-1944/486-Bugklasse).\n"
        f"  -> FIX: {RECOVERY_HINT}. "
        + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARNED (enforceProcess=false Opt-out).")
    )
    append_guard_log(f"Stage-Ende-Progression ohne _stage_orchestrate ({Path(fp).name})", enforce)
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
                log.write(f"[{datetime.now()}] guard_stage_seam_handoff ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
