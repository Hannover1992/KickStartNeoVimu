#!/usr/bin/env python3
"""
Claude Code Hook — Geist G#6: SDF Phase 1.1 (modusEntscheidung) -> SDF Phase 2.1 (Dispatch)

PreToolUse-Hook fuer Skill-Tool. Triggert wenn im SDF-Kontext folgende Skills
geladen werden (= "Phase 2.1 Dispatch-Entry"):
  - _SDF_berater_executionDispatch (Phase 2 internal dispatcher)
  - _I_orchestrate                  (M2/M3 Code-Pipeline)
  - _SC_orchestrate                 (M4-M7 Forschungs-Pipeline)

Contract (Geist G#6):
  Phase 1.1 modusEntscheidung MUSS gelaufen sein BEVOR Phase 2.1 dispatcht:
    (1) BERATER_OUTPUTS.modusEntscheidung* existiert im Manifest (mindestens 1 Block,
        bei Multi-Round dann mindestens ein round{N}-Block fuer die aktuelle Round).
    (2) DF_BATCH_STATE.modus ∈ {M1..M9}  ODER
        DF_BATCH_STATE.batch_modes[current_batch] ∈ {M1..M9}.
    (3) modus_set_by == "_SDF_berater_modusEntscheidung"  ODER
        batch_modes_set_by == "_SDF_berater_modusEntscheidung".

Verletzung (eines der drei):
  enforceProcess=true (Default) -> BLOCK   (continue=false)
  enforceProcess=false           -> WARN   (continue=true + additionalContext)

Style-Quelle: guard_modus_writer.py + guard_post_gap_sequence.py.
Master-Analyse: .claude/output/Enforce_Refactor_Master_Analyse_2026-05-27.md (Abschnitt G#6).
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
AUDIT_DIR = ROOT_DIR / ".claude" / "audit"
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# Skills die G#6 triggern (= Phase 2.1 Dispatch-Entry-Punkte)
TRIGGER_SKILLS = frozenset(
    [
        "_SDF_berater_executionDispatch",
        "_I_orchestrate",
        "_SC_orchestrate",
    ]
)

# Modus-Werte die akzeptiert werden
VALID_MODES = frozenset({"M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9"})

# Whitelisted Writer fuer modus / batch_modes (INV-MODUS-1, BL-165)
ALLOWED_MODUS_WRITERS = frozenset({"_SDF_berater_modusEntscheidung"})

# SDF df_status-Werte bei denen Phase 2.1 erreichbar ist (= Pipeline aktiv)
SDF_ACTIVE_STATES = frozenset(
    {
        "ITEM_LOOP",
        "ITEM_DONE",
        "ITEM_STAGE",
        "BATCH_LOOP",
        "DISPATCH",
        "PHASE_2",
        "PHASE_2_1",
    }
)


def _resolve_vault_path(key):
    """Resolve process state file path from vault-routing.json (gleiche Logik wie guard_post_gap_sequence)."""
    routing_path = ROOT_DIR / ".claude" / "config" / "vault-routing.json"
    if routing_path.exists():
        try:
            with open(routing_path, encoding="utf-8") as f:
                routing = json.load(f)
            for rule in routing.get("detection", {}).get("rules", []):
                psf = rule.get("process_state_files", {})
                if key in psf:
                    return Path(psf[key])
        except Exception:
            pass
    fallbacks = {
        "manifest": ROOT_DIR / ".claude" / "analysis" / "_manifest.md",
        "session_params": ROOT_DIR / ".claude" / "analysis" / "_session_params.md",
    }
    return fallbacks.get(key)


def _resolve_vault_session_params():
    """Fallback-Resolver via resolve_vault_root.py (gleiche Logik wie guard_modus_writer)."""
    try:
        import subprocess

        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True,
                text=True,
                timeout=5,
                cwd=str(ROOT_DIR),
            )
            if proc.returncode == 0:
                vault_root_str = proc.stdout.strip()
                if vault_root_str:
                    return Path(vault_root_str) / "_session_params.md"
    except Exception:
        pass
    return ROOT_DIR / ".claude" / "analysis" / "_session_params.md"


SESSION_PARAMS_FILE = _resolve_vault_session_params()
MANIFEST_FILE = _resolve_vault_path("manifest")


def read_enforce_process():
    """Liest enforceProcess aus _session_params.md. Default: true.

    Test-Override: OMNI_ENFORCE_GEIST6=1 erzwingt enforce=true (fuer pytest).
    OMNI_ENFORCE_GEIST6=0 erzwingt enforce=false.
    """
    override = os.environ.get("OMNI_ENFORCE_GEIST6")
    if override == "1":
        return True
    if override == "0":
        return False
    try:
        if not SESSION_PARAMS_FILE.exists():
            return True
        content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
        m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
        if m:
            return m.group(1) == "true"
    except Exception:
        pass
    return True


def read_manifest():
    """Liest aktuellen Manifest-Inhalt (Vault-pfad bevorzugt).

    Test-Override: OMNI_GEIST6_MANIFEST=<path> erlaubt Tests einen Stub-Manifest zu setzen.
    """
    override = os.environ.get("OMNI_GEIST6_MANIFEST")
    if override:
        try:
            return Path(override).read_text(encoding="utf-8")
        except Exception:
            return None
    # Per-BL-folder-aware Resolution (BL-RCA-Round17): bl_manifest_path zuerst
    try:
        sys.path.insert(0, str(SCRIPT_DIR))
        from _manifest_resolver import read_active_manifest
        vroot = MANIFEST_FILE.parent if MANIFEST_FILE else ROOT_DIR
        content, _path = read_active_manifest(SCRIPT_DIR, ROOT_DIR, vault_root=vroot)
        if content:
            return content
    except Exception:
        pass
    # Harter Fallback (alte Logik)
    if not MANIFEST_FILE or not MANIFEST_FILE.exists():
        return None
    try:
        return MANIFEST_FILE.read_text(encoding="utf-8")
    except Exception:
        return None


def detect_sdf_active(content):
    """Prueft ob SDF-Pipeline aktiv ist (siehe guard_post_gap_sequence.detect_sdf_active).

    Wir suchen den LETZTEN df_status, da das den aktuellen Pipeline-Zustand widerspiegelt.
    Wenn kein df_status gefunden wird, ist das auch "potentiell aktiv" — wir wollen
    nicht still skippen wenn das Pipeline-Status-Feld fehlt.
    """
    matches = re.findall(r"df_status\s*[:=]\s*(\w+)", content)
    if not matches:
        # Kein df_status → wir gehen davon aus dass G#6 trotzdem evaluiert werden soll
        # (besser Pre-Check fehlschlagen lassen als still durchlassen)
        return True
    current = matches[-1]
    return current in SDF_ACTIVE_STATES


def check_berater_outputs_modus(content):
    """Check (1): BERATER_OUTPUTS.modusEntscheidung* existiert im Manifest.

    Pattern matcht:
      - 'modusEntscheidung:'              (Standard)
      - 'modusEntscheidung_round{N}:'     (Multi-Round)
      - 'modusEntscheidung_round_{N}:'    (Variante mit Underscore)

    Returns (found: bool, blocks: list[str] of matched header names).
    """
    pattern = re.compile(
        r"(?:^|\n)\s*(modusEntscheidung(?:_round_?\d+)?)\s*:",
        re.MULTILINE,
    )
    blocks = pattern.findall(content)
    return (len(blocks) > 0, blocks)


def check_modus_field(content):
    """Check (2): DF_BATCH_STATE.modus OR batch_modes[current_batch] in {M1..M9}.

    Returns (found_valid: bool, modus_value: str|None, source: str).
    source ∈ {"singular_modus", "batch_modes", "none"}.
    """
    # Singular: DF_BATCH_STATE.modus: M{N}  ODER  modus: M{N}  innerhalb DF_BATCH_STATE-Block
    m_sing = re.search(
        r"(?:^|\n)\s*modus\s*[:=]\s*[\"']?(M[1-9])[\"']?",
        content,
    )
    if m_sing:
        mode_val = m_sing.group(1)
        if mode_val in VALID_MODES:
            return True, mode_val, "singular_modus"

    # Plural: batch_modes:\n  <key>: M{N}
    m_plur = re.search(
        r"(?:^|\n)\s*batch_modes\s*:\s*\n((?:\s+[A-Za-z0-9_\-]+\s*:\s*M[1-9]\s*\n?)+)",
        content,
    )
    if m_plur:
        block = m_plur.group(1)
        modes_in_block = re.findall(r":\s*(M[1-9])", block)
        valid_modes = [m for m in modes_in_block if m in VALID_MODES]
        if valid_modes:
            return True, valid_modes[0], "batch_modes"

    return False, None, "none"


def check_modus_writer(content):
    """Check (3): modus_set_by ODER batch_modes_set_by ∈ ALLOWED_MODUS_WRITERS.

    Returns (is_whitelisted: bool, writer: str|None).
    """
    m = re.search(
        r"(?:^|\n)\s*(?:modus_set_by|batch_modes_set_by)\s*[:=]\s*[\"']?([A-Za-z_]+)[\"']?",
        content,
    )
    if not m:
        return False, None
    writer = m.group(1).strip()
    return writer in ALLOWED_MODUS_WRITERS, writer


def append_guard_log(violation_type, details, blocked):
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = f"- [{timestamp}] **{violation_type}** [{action}]: {details}\n"
        with open(GUARD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def write_audit_entry(entry):
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def log_error(error):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as log:
            log.write(f"[{datetime.now()}] guard_geist6_sdf_internal Error: {error}\n")
    except Exception:
        pass


def extract_skill_name(tool_input):
    """Skill-Tool-Input kann 'skill' oder 'name' fuehren. Wir akzeptieren beide."""
    if not isinstance(tool_input, dict):
        return None
    return tool_input.get("skill") or tool_input.get("name") or tool_input.get("skill_name")


def main():
    # === Globaler Owner-Kill-Switch (BL-223): enforceProcess=false -> Guard aus ===
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
        hook_data = json.loads(sys.stdin.read())
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        # Nur auf Skill-Aufrufe triggern
        if tool_name != "Skill":
            print(json.dumps({"continue": True}))
            return

        skill_name = extract_skill_name(tool_input)
        if not skill_name or skill_name not in TRIGGER_SKILLS:
            # Nicht G#6-Trigger → passthrough
            print(json.dumps({"continue": True}))
            return

        # Manifest lesen
        content = read_manifest()
        if content is None:
            # Ohne Manifest kein Pre-Check moeglich — passthrough (fail-open wie post_gap)
            print(json.dumps({"continue": True}))
            return

        # SDF aktiv? (vermeidet false-positives bei BDF/A-Lauf der zufaellig SC ruft)
        sdf_active = detect_sdf_active(content)
        if not sdf_active:
            # SC/I koennen auch ohne SDF-Kontext gerufen werden (Bypass-Faelle) → passthrough
            print(json.dumps({"continue": True}))
            return

        # 3-Check Contract
        has_outputs, modusEntscheidung_blocks = check_berater_outputs_modus(content)
        has_modus, modus_value, modus_source = check_modus_field(content)
        is_whitelisted, writer = check_modus_writer(content)

        violations = []
        if not has_outputs:
            violations.append(
                "BERATER_OUTPUTS.modusEntscheidung* fehlt im Manifest "
                "(Phase 1.1 modusEntscheidung wurde nicht abgeschlossen)"
            )
        if not has_modus:
            violations.append(
                "DF_BATCH_STATE.modus oder batch_modes[current_batch] in {M1..M9} fehlt"
            )
        if not is_whitelisted:
            if writer is None:
                violations.append(
                    "modus_set_by/batch_modes_set_by-Marker fehlt komplett "
                    f"(erwartet: {sorted(ALLOWED_MODUS_WRITERS)})"
                )
            else:
                violations.append(
                    f"modus_set_by={writer!r} ist nicht whitelisted "
                    f"(erlaubt: {sorted(ALLOWED_MODUS_WRITERS)})"
                )

        if not violations:
            # Geist G#6 OK: Pre-Conditions erfuellt
            write_audit_entry(
                {
                    "ts": datetime.now().isoformat(timespec="seconds"),
                    "event": "GEIST_PRE_CHECK",
                    "geist": "G#6",
                    "trigger_skill": skill_name,
                    "state": "PASS",
                    "modusEntscheidung_blocks": modusEntscheidung_blocks,
                    "modus_value": modus_value,
                    "modus_source": modus_source,
                    "writer": writer,
                }
            )
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()
        violation_str = "; ".join(violations)
        message = (
            f"[GUARD-VIOLATION] GEIST_G6_SDF_INTERNAL (BL-165 / Master-Analyse G#6): "
            f"Phase 2.1 Dispatch ({skill_name}) ohne abgeschlossene Phase 1.1 modusEntscheidung. "
            f"Verletzungen: {violation_str}. "
            f"Vor Skill({skill_name}) muss _SDF_berater_modusEntscheidung gelaufen sein. "
            f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
        )

        write_audit_entry(
            {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "event": "GEIST_PRE_CHECK",
                "geist": "G#6",
                "trigger_skill": skill_name,
                "state": "FAIL",
                "violations": violations,
                "enforce": enforce,
                "modusEntscheidung_blocks": modusEntscheidung_blocks,
                "modus_value": modus_value,
                "modus_source": modus_source,
                "writer": writer,
            }
        )
        append_guard_log("GEIST_G6_SDF_INTERNAL", violation_str, enforce)

        result = {
            "continue": not enforce,
            "message": message,
        }
        if not enforce:
            # Warn-Modus: zusaetzlicher additionalContext-Hinweis
            result["additionalContext"] = (
                f"[Geist G#6] Phase 2.1 Pre-Check verletzt: {violation_str}. "
                f"Trigger: Skill({skill_name}). "
                f"Naechster Schritt: Skill(_SDF_berater_modusEntscheidung) ausfuehren."
            )

        print(json.dumps(result))

    except Exception as e:
        log_error(e)
        # Fail-safe: niemals false-block bei Fehlern
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
