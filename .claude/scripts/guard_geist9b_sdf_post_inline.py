#!/usr/bin/env python3
"""
guard_geist9b_sdf_post_inline.py — SDF-Post Inline-Bypass-Detektor.

Schliesst die Luecke aus Independent_Observer_DCSRE-486_2026-05-28:
  Lead macht Phase 3/4 (PL-Items [x], completed_batches) INLINE statt via
  Skill(_SDF_orchestrate_post). guard_geist9 fing es nicht (triggert nur bei
  Skill-Load von loopDecision/PostBatch — inline umgeht den Trigger).

Detektion (PreToolUse Edit/Write):
  WENN Edit/Write auf parking-lot.md ODER _manifest.md
  UND der Write enthaelt eine Batch-Completion-Transition:
       - PL-Item [ ] → [x]  (DONE-Markierung)
       - completed_*_batches Append
  UND seit letztem Skill(_I_orchestrate) KEIN Skill(_SDF_orchestrate_post) geladen
  → das ist SDF-Post inline (Bypass).

Default BLOCK (DCSRE-486 Fix 2026-05-29, Owner-approved): der I->SDF_post Rueck-
Handschuh-Skip wird HART gestoppt, nicht nur gewarnt. Legitime Kontexte sind bereits
sauber gescoped (KEIN Block wenn: keine I-Pipeline lief [i_active=False, z.B. IDF/A
schreiben PLs] ODER _SDF_orchestrate_post lief danach [post_since=True]).
E1-FIX (BL-486 AK-E E1, POST-ROOT-1): Dieser Pfad ist vom file-basierten enforce_active()-
Gate ENTKOPPELT — `enforceProcess=false` (agent-erreichbar via _session_params.md) schaltet
geist9b NICHT mehr aus (kein Self-Unlock-Generalschluessel). NUR die agent-UNERREICHBARE
OMNI_ENFORCE_ALL_OFF-Env (Owner, BL-210) oeffnet den Pfad. Explizit-WARN (Debug): OMNI_GEIST9B_ENFORCE=0.

Test-Override: OMNI_GEIST9B_AUDIT (audit-path). Off: OMNI_GEIST9B_OFF=1.
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

# Batch-Completion-Transitions (Phase-3-Arbeit die normalerweise SDF-post macht)
PL_DONE_PATTERN = re.compile(r"###\s*\[x\]\s*PL-", re.IGNORECASE)
COMPLETED_BATCHES_PATTERN = re.compile(r"completed_(round\d+_)?(sub_)?batches\s*:\s*\[[^\]]*\w", re.IGNORECASE)


def get_audit_path():
    return Path(os.environ.get("OMNI_GEIST9B_AUDIT", str(AUDIT_FILE)))


def read_enforce():
    # BLOCK ist Default (DCSRE-486 Fix 2026-05-29, Owner-approved): an diesem Punkt ist der
    # Post-SDF-Inline-Bypass bereits detektiert, also HART blocken (der I->SDF_post Rueck-
    # Handschuh-Skip darf nicht nur gewarnt werden). E1-FIX (BL-486): seit der Entkopplung vom
    # enforce_active()-file-Gate kann `enforceProcess=false` (agent-erreichbar) das nicht mehr
    # zu WARN aufweichen; nur OMNI_ENFORCE_ALL_OFF (env, @main) laesst den Pfad ganz durch.
    # Explizit-WARN nur via OMNI_GEIST9B_ENFORCE=0 (Debug/Opt-out).
    if os.environ.get("OMNI_GEIST9B_ENFORCE") == "0":
        return False
    return True


def append_guard_log(msg, blocked):
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(f"- [{ts}] **GEIST9B_SDF_POST_INLINE** [{action}]: {msg}\n")
    except Exception:
        pass


def post_phase_ran_since_i_pipeline():
    """Scanne audit rueckwaerts. Returns:
      (i_pipeline_active, post_ran_since)
      i_pipeline_active: bool — gab es ein _I_orchestrate SKILL_LOAD?
      post_ran_since: bool — _SDF_orchestrate_post NACH letztem _I_orchestrate?
    """
    audit = get_audit_path()
    if not audit.exists():
        return False, True
    try:
        lines = audit.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception:
        return False, True

    pos_i = -1
    pos_post = -1
    for i in range(len(lines) - 1, -1, -1):
        try:
            ev = json.loads(lines[i])
        except Exception:
            continue
        skill = ev.get("skill_name") or ev.get("skill") or ""
        cmd = ev.get("command") or ""
        if pos_i == -1 and ev.get("event") == "SKILL_LOAD" and "_I_orchestrate" in (skill or cmd):
            pos_i = i
        if pos_post == -1 and ("_SDF_orchestrate_post" in skill or "_SDF_orchestrate_post" in cmd):
            pos_post = i
        if pos_i != -1 and pos_post != -1:
            break

    i_active = pos_i != -1
    post_since = pos_post != -1 and pos_post >= pos_i
    return i_active, post_since


def main():
    # === Owner-Kill-Switch (BL-210): NUR die agent-UNERREICHBARE env-Notbremse ===
    # E1-FIX (BL-486 AK-E E1, POST-ROOT-1, Variante b): Der Post-SDF-Inline-Pfad ist
    # vom file-basierten `enforce_active()`-Gate ENTKOPPELT. Wurzel: `enforce_active()`
    # liest `enforceProcess` aus `_session_params.md` — ein Sub-Agent KANN diese Datei
    # schreiben (`enforceProcess: false`) und damit seinen eigenen Waechter abschalten
    # (agent-erreichbarer Self-Unlock = Generalschluessel). Schablone: die zwei
    # Souveraenitaets-Guards in _enforce_gate.py:18-26 (param_writer/hook_prep) honorieren
    # AUS GENAU DIESEM GRUND nur die env-Notbremse, nicht den file-Gate. geist9b zieht jetzt
    # gleich. enforceProcess=false (BL-210) bleibt respektiert NUR ueber die agent-
    # unerreichbare OMNI_ENFORCE_ALL_OFF-Env (Owner-Souveraenitaet), NICHT ueber den file-Gate.
    import os as _os, json as _json
    if _os.environ.get("OMNI_ENFORCE_ALL_OFF") == "1":
        print(_json.dumps({"continue": True}))
        return
    try:
        event = json.loads(sys.stdin.read())
    except Exception:
        print(json.dumps({"continue": True}))
        return

    if os.environ.get("OMNI_GEIST9B_OFF") == "1":
        print(json.dumps({"continue": True}))
        return

    if event.get("tool_name") not in ("Edit", "Write"):
        print(json.dumps({"continue": True}))
        return

    ti = event.get("tool_input", {}) or {}
    fp = ti.get("file_path", "")
    new_text = ti.get("new_string", "") or ti.get("content", "")

    is_pl = "parking-lot.md" in fp
    is_manifest = "_manifest.md" in fp or "_factory_manifest.md" in fp
    if not (is_pl or is_manifest):
        print(json.dumps({"continue": True}))
        return

    # Batch-Completion-Transition im Write?
    has_pl_done = is_pl and bool(PL_DONE_PATTERN.search(new_text))
    has_completed = is_manifest and bool(COMPLETED_BATCHES_PATTERN.search(new_text))
    if not (has_pl_done or has_completed):
        print(json.dumps({"continue": True}))
        return

    i_active, post_since = post_phase_ran_since_i_pipeline()

    if not i_active:
        # Keine I-Pipeline gelaufen → diese Transition ist nicht SDF-Post-Kontext
        print(json.dumps({"continue": True}))
        return

    if post_since:
        # _SDF_orchestrate_post lief nach I-Pipeline → legitime Phase-3-Persistenz
        print(json.dumps({"continue": True}))
        return

    # I-Pipeline lief, ABER kein _SDF_orchestrate_post danach, und jetzt Batch-Completion-Edit
    # → SDF-Post inline (Bypass)
    enforce = read_enforce()
    transition = "PL [ ]→[x]" if has_pl_done else "completed_batches Append"
    msg = (
        f"[GUARD-VIOLATION] GEIST9B_SDF_POST_INLINE: Batch-Completion-Transition ({transition}) "
        f"in {Path(fp).name} nach I-Pipeline, ABER kein Skill(_SDF_orchestrate_post) geladen.\n"
        f"  -> RUECK-HANDSCHUH FEHLT: Skill(_I_orchestrate) endet mit Pflicht-Chain zu "
        f"Skill(_SDF_orchestrate_post) (INV-HANDOVER-1). Phase 3/4 (recalibrate/postItem/"
        f"statusTransition/modelSync + loopDecision) NICHT inline/direkt-committen.\n"
        f"  -> FIX: ZUERST Skill(_SDF_orchestrate_post, args=\"<NAME> --vault=<VAULT>\") ausfuehren, "
        f"DANN die [x]-Markierung/Completion. (DCSRE-486 Live-Skip 2026-05-29.) "
        + ("BLOCKIERT (enforceProcess=true)." if enforce else "WARNED (OMNI_GEIST9B_ENFORCE=0 Opt-out).")
    )
    append_guard_log(f"{transition} ohne _SDF_orchestrate_post ({Path(fp).name})", enforce)
    print(json.dumps({"continue": not enforce, "message": msg}))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_geist9b ERROR: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))
