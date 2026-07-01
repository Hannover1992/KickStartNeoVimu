#!/usr/bin/env python3
"""
guard_geist5_idf_to_sdf.py — Geist G#5 Contract-Level Hook (CRITICAL).

Adressiert Geist G#5 (IDF -> SDF, Batch-Handover) — Round 11 Drift-Epizentrum.
Pre-SDF Contract-Level-Check (statt Field-Pattern-Patch wie guard_modus_writer.py).

PreToolUse-Hook fuer Skill-Tool:
  - Triggert wenn Skill(_SDF_orchestrate) geladen wird (von IDF/BDF)
  - Prueft POST-IDF-Contract gegen den AKTUELLEN Manifest-State

Contract-Checks (POSITIV, IDF muss diese Felder geliefert haben):
  1. IDF_PIPELINE_STATE.status == "IDF_DONE"
  2. DF_BATCH_STATE.batch_items_per_batch (Map mit >=1 Batch)
  3. DF_BATCH_STATE.batch_mode_hints (Map) ODER
     legitimer Re-Entry: batch_modes mit batch_modes_set_by: _SDF_berater_modusEntscheidung
  4. DF_BATCH_STATE.batch_stages (Map)

KANONISCHE CONTRACT-OWNER pro Vertrags-Feld (BL-313 AK-2, Single-Source pro Feld) —
jedes hier geforderte Feld hat genau EINEN dokumentierten Producer/Owner:
  - IDF_DONE (idf_status)     -> _IDF_orchestrate (Phase 8)
  - batch_items_per_batch     -> batchPlanner / Phase 7
                                 (_IDF_berater_metricPlanner LIEST es nur, ist KONSUMENT,
                                  KEIN Owner — Korrektur der frueheren 'Beispiel :362'-
                                  Ownership-Fehldeutung, anker_drift_check BL-313)
  - batch_mode_hints          -> _IDF_berater_batchPlan (SCHRITT 5b Happy-Path-Producer,
                                 ADVISORY aus build_klasse; BL-313 AK-3). ADVISORY ONLY —
                                 C3/_SDF_berater_modusEntscheidung (SDF Phase 1.1) entscheidet
                                 den Modus AUTORITATIV; batch_mode_hints != batch_modes != modus.
  - batch_stages              -> _IDF_berater_stagePlanner (Phase 7.5)
batch_modes bleibt C3-exklusiv (INV-MODUS-1) — IDF darf es NIE als Erst-Eintritts-Feld
liefern; hier nur als legitimer Re-Entry (set_by-Whitelist) akzeptiert (siehe check unten).
Diese Owner-Doku aendert KEINE Guard-Logik — die Akzeptanz-Kriterien bleiben unveraendert.

IDF-LIGHT-KOMPATIBEL (2026-06-01): Bei idf_light_mode IN {light, ultralight} (<=3 Items) skippt
IDF die ORGANISATIONS-Berater (clustering/dependency/sequence — No-Ops bei wenig Items), behaelt
aber die ESSENZIELLEN (validator/batchPlan/stagePlanner/metricPlanner/testSearch/finalSummary).
Die 4 Contract-Felder oben kommen von genau diesen essenziellen Beratern -> geist5 PASST IDF-light
BY DESIGN: dieser Guard prueft OUTPUT-FELDER, NICHT die Phasen-/SKILL_LOAD-Sequenz. Kein Skip-Feld
fehlt (der Orchestrator schreibt fuer geskippte Phasen Trivial-Outputs). idf_light_mode wird nur ins
Audit aufgenommen (Transparenz) — KEINE Lockerung der 4 Pflicht-Felder.

Verboten-Checks (NEGATIV, Pre-SDF-Drift):
  - batch_modes ohne batch_modes_set_by -> Round 11 Bug (IDF schrieb statt SDF)
  - mode: lead_fallback ohne pragmatik_reason -> Lead-Bypass-Drift

Modi:
  enforceProcess=true  (Default) -> BLOCK (continue=false)
  enforceProcess=false           -> WARN (continue=true, message=...)
  Override: OMNI_ENFORCE_GEIST5_GUARD=1 erzwingt enforce=true (pytest)

Audit:
  audit.jsonl event=GEIST5_CONTRACT_VIOLATION mit Details
  _guard_log.md Markdown-Eintrag

Beweis-Run: DCSRE-486 Round 11 (2026-05-27). Round 11 hatte:
  - batch_modes statt batch_mode_hints (IDF Phase 7.6 metricPlanner Drift)
  - mode: lead_fallback ohne pragmatik_reason
  - SDF Phase 1.1 wurde komplett uebersprungen
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

AUDIT_DIR = ROOT_DIR / ".claude" / "audit"
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"
GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# Skills die G#5-Uebergang triggern (SDF-Entry-Points)
TRIGGER_SKILLS = {"_SDF_orchestrate"}

# Whitelist fuer legitimen Re-Entry (batch_modes durch SDF gesetzt)
ALLOWED_BATCH_MODES_WRITERS = {"_SDF_berater_modusEntscheidung"}

# Manifest-Pfad-Kandidaten (factory_manifest = neu, _manifest = legacy)
MANIFEST_CANDIDATES = ("_factory_manifest.md", "_manifest.md")


def _resolve_vault_root() -> Path:
    """Resolve Vault-Root via resolve_vault_root.py (analog guard_modus_writer.py).

    Test-Override: OMNI_GEIST5_VAULT_ROOT setzt Vault-Root direkt
    (fuer pytest mit Temp-Vault).
    """
    test_override = os.environ.get("OMNI_GEIST5_VAULT_ROOT")
    if test_override:
        return Path(test_override)
    try:
        import subprocess
        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True, text=True, timeout=5,
                cwd=str(ROOT_DIR),
            )
            if proc.returncode == 0:
                vault_root_str = proc.stdout.strip()
                if vault_root_str:
                    return Path(vault_root_str)
    except Exception:
        pass
    return ROOT_DIR


def _resolve_session_params() -> Path:
    """Sucht _session_params.md analog zu guard_modus_writer.py."""
    test_override = os.environ.get("OMNI_GEIST5_SESSION_PARAMS")
    if test_override:
        return Path(test_override)
    vault_root = _resolve_vault_root()
    candidate = vault_root / "_session_params.md"
    if candidate.exists():
        return candidate
    return ROOT_DIR / ".claude" / "analysis" / "_session_params.md"


def read_enforce_process() -> bool:
    """Liest enforceProcess aus _session_params.md.
    Test-Override: OMNI_ENFORCE_GEIST5_GUARD=1 erzwingt enforce=true.
    Default: True wenn Datei fehlt (sicher).
    """
    if os.environ.get("OMNI_ENFORCE_GEIST5_GUARD") == "1":
        return True
    if os.environ.get("OMNI_ENFORCE_GEIST5_GUARD") == "0":
        return False
    params = _resolve_session_params()
    try:
        if not params.exists():
            return True
        content = params.read_text(encoding="utf-8")
        m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
        if m:
            return m.group(1).strip().lower() == "true"
    except Exception:
        pass
    return True


def read_manifest_content() -> tuple[str, Path | None]:
    """Liest Manifest-Inhalt — per-BL-folder-aware (BL-RCA-Round17).

    bl_manifest_path ZUERST (DCSRE per-BL-folder), dann factory/legacy/vault-Fallback.
    Fixt flat-vault-Annahme die SDF-Handoff false-positiv blockte ("Manifest nicht gefunden").

    Returns:
        (content, path) — content="" wenn keine Datei gefunden.
    """
    # Test-Mode: expliziter Vault-Override → ambient current_context.py UEBERSPRINGEN
    test_vault = os.environ.get("OMNI_GEIST5_VAULT_ROOT")
    if not test_vault:
        # Production: per-BL-folder-Resolution via shared helper
        try:
            sys.path.insert(0, str(SCRIPT_DIR))
            from _manifest_resolver import read_active_manifest
            content, path = read_active_manifest(SCRIPT_DIR, ROOT_DIR, vault_root=_resolve_vault_root())
            if content:
                return content, path
        except Exception:
            pass
    # Fallback / Test-Mode: direkt vault_root (flat-vault Logik)
    vault_root = _resolve_vault_root()
    for name in MANIFEST_CANDIDATES:
        candidate = vault_root / name
        if candidate.is_file():
            try:
                return candidate.read_text(encoding="utf-8"), candidate
            except Exception:
                continue
    return "", None


# ============================================================================
# CONTRACT-CHECKS
# ============================================================================


def check_idf_done(content: str) -> bool:
    """Pruefe ob IDF_PIPELINE_STATE.status == IDF_DONE."""
    pat = re.compile(
        r"IDF_PIPELINE_STATE[.\s]*?(?:status|idf_status)\s*[:=]\s*[\"']?IDF_DONE[\"']?",
        re.IGNORECASE,
    )
    if pat.search(content):
        return True
    # Fallback: kompakte YAML-Form (status: IDF_DONE direkt unter IDF_PIPELINE_STATE)
    block_pat = re.compile(
        r"IDF_PIPELINE_STATE[^#]*?(?:^|\n)\s{0,8}(?:status|idf_status)\s*:\s*[\"']?IDF_DONE[\"']?",
        re.IGNORECASE | re.DOTALL,
    )
    return bool(block_pat.search(content))


def check_batch_items_per_batch(content: str) -> bool:
    """Pruefe ob DF_BATCH_STATE.batch_items_per_batch existiert + min. 1 Batch.

    Kanonischer Owner (BL-313 AK-2): batchPlanner / Phase 7.
    _IDF_berater_metricPlanner ist KONSUMENT (liest es), KEIN Owner.
    """
    # Field-Anker (case-insensitive, optional indent)
    anchor = re.compile(
        r"(?:^|\n)\s*batch_items_per_batch\s*:",
        re.MULTILINE,
    )
    m = anchor.search(content)
    if not m:
        return False
    # Pruefe >=1 Sub-Key (batch_*) im Bereich nach dem Anchor
    tail = content[m.end():m.end() + 4000]  # naechste 4kB
    sub_key_pat = re.compile(
        r"(?:^|\n)\s{2,}(?:batch_|v\d+_)[a-zA-Z0-9_]+\s*:",
        re.MULTILINE,
    )
    return bool(sub_key_pat.search(tail))


def check_batch_mode_hints_or_legitimate_reentry(content: str) -> tuple[bool, str]:
    """Pruefe entweder batch_mode_hints existiert ODER legitimer Re-Entry
    (batch_modes mit batch_modes_set_by: _SDF_berater_modusEntscheidung).

    Kanonischer Owner (BL-313 AK-2/AK-3): batch_mode_hints -> _IDF_berater_batchPlan
    (SCHRITT 5b Happy-Path-Producer, ADVISORY aus build_klasse). Damit ist
    batch_mode_hints auf sauberen INV-MODUS-1-Laeufen vorhanden BEVOR C3
    (_SDF_berater_modusEntscheidung, SDF Phase 1.1) batch_modes setzt — schliesst
    die BL-313-Entry-Time-Block-Luecke. batch_modes bleibt C3-exklusiv und wird hier
    NUR als legitimer Re-Entry (set_by-Whitelist) akzeptiert.

    Returns:
        (ok, reason) — ok=True wenn Contract erfuellt
    """
    # Erst-Eintritt: batch_mode_hints
    hints_pat = re.compile(
        r"(?:^|\n)\s*batch_mode_hints\s*:",
        re.MULTILINE,
    )
    if hints_pat.search(content):
        return True, "batch_mode_hints present (Erst-Eintritt)"

    # Re-Entry: batch_modes MIT batch_modes_set_by Whitelist
    batch_modes_pat = re.compile(
        r"(?:^|\n)\s*batch_modes\s*:",
        re.MULTILINE,
    )
    if batch_modes_pat.search(content):
        set_by_pat = re.compile(
            r"batch_modes_set_by\s*[:=]\s*[\"']?([A-Za-z_]+)[\"']?",
        )
        m = set_by_pat.search(content)
        if m:
            writer = m.group(1).strip()
            if writer in ALLOWED_BATCH_MODES_WRITERS:
                return True, f"batch_modes legitime Re-Entry (set_by={writer})"
            else:
                return False, (
                    f"batch_modes set_by='{writer}' nicht in Whitelist "
                    f"{sorted(ALLOWED_BATCH_MODES_WRITERS)} — Bypass (Round-11-Drift)"
                )
        # batch_modes OHNE set_by = Round-11-Bug
        return False, "batch_modes ohne batch_modes_set_by (= Round-11-Drift, IDF schrieb statt SDF)"

    return False, "weder batch_mode_hints noch legitime batch_modes-Re-Entry vorhanden"


def check_batch_stages(content: str) -> bool:
    """Pruefe ob DF_BATCH_STATE.batch_stages existiert + min. 1 Batch.

    Kanonischer Owner (BL-313 AK-2): _IDF_berater_stagePlanner (Phase 7.5).
    """
    anchor = re.compile(
        r"(?:^|\n)\s*batch_stages\s*:",
        re.MULTILINE,
    )
    m = anchor.search(content)
    if not m:
        return False
    tail = content[m.end():m.end() + 4000]
    sub_key_pat = re.compile(
        r"(?:^|\n)\s{2,}(?:batch_|v\d+_)[a-zA-Z0-9_]+\s*:",
        re.MULTILINE,
    )
    return bool(sub_key_pat.search(tail))


def _current_batch_scope(content: str) -> str:
    """Slice ab dem LETZTEN '## DF_BATCH_STATE'-Header = aktueller Round.

    BL-RCA-Round17b: Manifest ist append-only — historische round11-Bloecke
    (lead_fallback ohne pragmatik_reason) duerfen den aktuellen SDF-Start NICHT
    blockieren. Negative Checks scopen auf den aktuellen (= letzten) Batch-State-Block.
    """
    headers = list(re.finditer(r"(?:^|\n)#{1,4}\s+DF_BATCH_STATE", content))
    if headers:
        return content[headers[-1].start():]
    return content


def check_lead_fallback_without_reason(content: str) -> bool:
    """Pruefe ob `mode: lead_fallback` ohne pragmatik_reason im AKTUELLEN Block.

    Returns True wenn DRIFT (= lead_fallback ohne reason im current DF_BATCH_STATE).
    Historische round11-lead_fallback (append-only) werden via Scope ignoriert.
    """
    scope = _current_batch_scope(content)
    lead_fallback_pat = re.compile(
        r"(?:^|\n)\s*mode\s*[:=]\s*[\"']?lead_fallback[\"']?",
        re.MULTILINE,
    )
    if not lead_fallback_pat.search(scope):
        return False
    # Wenn lead_fallback da ist, MUSS pragmatik_reason im selben (aktuellen) Block sein
    reason_pat = re.compile(
        r"(?:^|\n)\s*pragmatik_reason\s*[:=]\s*\S",
        re.MULTILINE,
    )
    return not reason_pat.search(scope)


# ============================================================================
# LOG-HELPERS
# ============================================================================


def append_guard_log(violations: list[str], blocked: bool) -> None:
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        violation_str = "; ".join(violations)
        entry = (
            f"- [{timestamp}] **GEIST5_CONTRACT_VIOLATION** [{action}]: "
            f"IDF->SDF Contract verletzt — {violation_str}\n"
        )
        with open(GUARD_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def write_audit_event(violations: list[str], blocked: bool, manifest_path: Path | None) -> None:
    """Schreibt GEIST5_CONTRACT_VIOLATION Event in audit.jsonl."""
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "event": "GEIST5_CONTRACT_VIOLATION",
            "geist": "G#5_IDF_TO_SDF",
            "trigger_skill": "_SDF_orchestrate",
            "blocked": blocked,
            "violations": violations,
            "manifest": str(manifest_path) if manifest_path else None,
            "guard": "guard_geist5_idf_to_sdf.py",
        }
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def append_debug_log(msg: str) -> None:
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] guard_geist5_idf_to_sdf: {msg}\n")
    except Exception:
        pass


# ============================================================================
# MAIN
# ============================================================================


def run_contract_checks(content: str) -> list[str]:
    """Fuehrt alle Contract-Checks aus und gibt Violations-Liste zurueck."""
    violations: list[str] = []

    # Positiv-Contracts (IDF muss geliefert haben)
    if not check_idf_done(content):
        violations.append(
            "IDF_PIPELINE_STATE.status != IDF_DONE — IDF not completed "
            "(SDF darf nicht starten ohne IDF-Output)"
        )

    if not check_batch_items_per_batch(content):
        violations.append(
            "DF_BATCH_STATE.batch_items_per_batch fehlt oder leer — "
            "IDF contract missing (kein Batch-Mapping vorhanden)"
        )

    hints_ok, hints_reason = check_batch_mode_hints_or_legitimate_reentry(content)
    if not hints_ok:
        violations.append(
            f"DF_BATCH_STATE.batch_mode_hints fehlt — IDF contract missing "
            f"({hints_reason})"
        )

    if not check_batch_stages(content):
        violations.append(
            "DF_BATCH_STATE.batch_stages fehlt oder leer — "
            "IDF contract missing (kein Stage-Mapping pro Batch)"
        )

    # Negativ-Contracts (Pre-SDF-Drift)
    if check_lead_fallback_without_reason(content):
        violations.append(
            "mode: lead_fallback ohne pragmatik_reason — Lead-Bypass-Drift "
            "(Round-11-Pattern: SDF Phase 1.1 wurde umgangen)"
        )

    return violations


def main() -> None:
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
        raw = sys.stdin.read()
        hook_data = json.loads(raw)
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        # Frueh-Exit: Nur Skill-Tool relevant
        if tool_name != "Skill":
            print(json.dumps({"continue": True}))
            return

        if not isinstance(tool_input, dict):
            print(json.dumps({"continue": True}))
            return

        skill_name = tool_input.get("skill", "")
        if skill_name not in TRIGGER_SKILLS:
            # Anderer Skill -> Passthrough
            print(json.dumps({"continue": True}))
            return

        # ── Trigger gefunden: G#5-Contract pruefen ────────────────────────
        content, manifest_path = read_manifest_content()
        if not content:
            # Kein Manifest gefunden -> Hard-Block (oder Warn), weil SDF
            # ohne IDF-Output nicht starten darf.
            violations = [
                "Manifest-Datei (_factory_manifest.md oder _manifest.md) nicht gefunden — "
                "SDF darf nicht starten ohne IDF-Output"
            ]
        else:
            violations = run_contract_checks(content)

        if not violations:
            # Contract erfuellt -> Passthrough
            print(json.dumps({"continue": True}))
            return

        # Violations gefunden
        enforce = read_enforce_process()
        violation_str = "; ".join(violations)
        message = (
            f"[GUARD-VIOLATION] GEIST5_IDF_TO_SDF_CONTRACT (Round-11-Drift-Epizentrum): "
            f"{violation_str}.\n"
            f"  Geist G#5 (IDF->SDF Batch-Handover) — SDF darf nicht starten ohne "
            f"vollstaendigen IDF-Contract (IDF_DONE + batch_items_per_batch + "
            f"batch_mode_hints + batch_stages).\n"
            f"  -> FIX (setzt Prozess fort): IDF-Contract vervollstaendigen — "
            f"Skill(_IDF_orchestrate) Phase 3.5 (validator) re-laeuft + persistiert die "
            f"fehlenden Felder, dann SDF erneut. Lief IDF bereits durch: pruefe ob das "
            f"per-BL-folder-Manifest gelesen wird (current_context.py bl_manifest_path).\n"
            f"  {'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
        )
        print(json.dumps({
            "continue": not enforce,
            "message": message,
        }))
        append_guard_log(violations, enforce)
        write_audit_event(violations, enforce, manifest_path)

    except json.JSONDecodeError as e:
        append_debug_log(f"JSONDecodeError: {e}")
        print(json.dumps({"continue": True}))
    except Exception as e:
        append_debug_log(f"Unexpected error: {e}")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
