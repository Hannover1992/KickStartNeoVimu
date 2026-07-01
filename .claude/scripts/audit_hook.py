#!/usr/bin/env python3
"""
Claude Code Hook — Process Audit Logger (v1.0)

PreToolUse + PostToolUse Hook: Loggt JEDEN Handschuh-Wechsel (Skill-Aufruf)
und State-relevante Edits als JSONL in .claude/audit/audit.jsonl.

79 Audit-Punkte aus ProcessMap-COMPLETE.md abgedeckt durch:
  - Skill()-Aufrufe (57 Handschuh-Wechsel)
  - Edit/Write an _manifest.md (79 State-Writes)
  - Agent()-Aufrufe (Worker-Spawns in Wellen)

Format: 1 JSONL-Zeile pro Event, append-only, querybar mit jq.
"""

import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
AUDIT_DIR = ROOT_DIR / ".claude" / "audit"
AUDIT_FILE = AUDIT_DIR / "audit.jsonl"


def _resolve_vault_path(key):
    """Resolve process state file path from vault-routing.json."""
    routing_path = Path(__file__).parent.parent / "config" / "vault-routing.json"
    if routing_path.exists():
        try:
            with open(routing_path, encoding='utf-8') as f:
                routing = json.load(f)
            for rule in routing.get("detection", {}).get("rules", []):
                psf = rule.get("process_state_files", {})
                if key in psf:
                    return Path(psf[key])
        except Exception:
            pass
    # Fallback: alte lokale Pfade
    fallbacks = {
        "manifest": ROOT_DIR / ".claude" / "analysis" / "_manifest.md",
        "manifest_protokoll": ROOT_DIR / ".claude" / "analysis" / "_manifest_protokoll.md",
        "backlog_index": ROOT_DIR / ".claude" / "analysis" / "_backlog_index.md",
        "session_params": ROOT_DIR / ".claude" / "analysis" / "_session_params.md",
        "task": ROOT_DIR / ".claude" / "Task.md",
        "parking_lot": ROOT_DIR / ".claude" / "analysis" / "_parking-lot.md",
    }
    return fallbacks.get(key)


# AK-3 (BL-364): MANIFEST_FILE ist KEINE Modul-Level-Konstante mehr — lazy per Call.
# Aufloesung erfolgt in read_active_context() frisch per Aufruf (kein Import-Zeit-Cache).

# Bekannte Orchestrator-Commands fuer Level-Zuordnung
ORCHESTRATOR_LEVELS = {
    "_BDF_orchestrate": "BDF",
    "_BDF_batchPlan": "BDF",
    "_SDF_orchestrate": "SDF",
    "_A_orchestrate": "A",
    "_SC_orchestrate": "SC",
    "_SC_observe": "SC",
    "_SC_hypothese": "SC",
    "_SC_ergebnis": "SC",
    "_SC_qualityGate": "SC",
    "_SC_implement": "SC",
    "_SC_modelMaintain": "SC",
    "_I_orchestrate": "I",
    "_I_blueprintArchitect": "I",
    "_I_cleanCodeSlice": "I",
    "_I_codeAtomic": "I",
    "_I_codeSystem": "I",
    "_I_codeE2E": "I",
    "_I_codeIntegration": "I",
    "_I_codeFullSystem": "I",
    "_I_goldDefine": "I",
    "_I_fanIn": "I",
    "_I_fanOut": "I",
    "_I_verify": "I",
    "_I_testSearch": "I",
    "_I_diffAudit": "I",
    "_TDD_orchestrate": "TDD",
    "_TDD_red": "TDD",
    "_TDD_green": "TDD",
    "_TDD_execute": "TDD",
    "_TDD_check": "TDD",
    "_TDD_refactorCode": "TDD",
    "_TDD_refactorTests": "TDD",
    "_TDD_init": "TDD",
    "_WP_orchestrate": "WP",
    "_WP_init": "WP",
    "_WP_session": "WP",
    "_WP_structure": "WP",
    "_WP_assess": "WP",
    "_WP_chapterModel": "WP",
    "_WP_write": "WP",
    "_WP_synthesis": "WP",
    "_WP_review": "WP",
    "_WP_convergence": "WP",
    "_WP_reflect": "WP",
    "_WP_qualityGate": "WP",
    "_WP_chapterPDF": "WP",
    "_W_fetch": "OBSIDIAN",
    "_W_fireTogether": "OBSIDIAN",
    "_W_obsidianSync": "OBSIDIAN",
    "_W_push_orchestrate": "OBSIDIAN",
    "_W_push_global": "OBSIDIAN",
    "_W_modelSplit": "OBSIDIAN",
    "_W_sync_orchestrate": "OBSIDIAN",
    "_model": "A",
    "_spec": "A",
    "_gap": "A",
    "_K_score": "A",
    "_backlog": "A",
    "_taskDefinition": "A",
    "_DiffReduce": "POST",
    "_AC_orchestrate": "POST",
    "_PT_extract": "POST",
    "_smoothing": "POST",
    "_Pre_PR_orchestrate": "POST",
    "_Pre_PR": "POST",
    "_W_push_orchestrate": "POST",
    "_finish": "POST",
    "_stage_orchestrate": "POST",
    "_presentation": "POST",
    "_T_orchestrate": "TEST",
    "_param": "CONFIG",
    "_analyse": "SC",
}

# State-Dateien deren Edits geloggt werden (Bugfix W28: 6 statt 4)
STATE_FILES = [
    "_manifest.md",
    "_manifest_protokoll.md",
    "_backlog_index.md",
    "_parking-lot.md",
    "_session_params.md",
    "Task.md",
]

# BL-159 AK-4: SKILL_LOAD-Event Erkennungs-Pattern
SKILL_PATH_PATTERN = re.compile(
    r"(?:^|[\\/])\.claude[\\/]commands[\\/](_[A-Za-z0-9_]+)\.md$"
)


def read_active_context():
    """Liest aktuellen Kontext aus Manifest (BDF/SDF Status, aktives Item).

    AK-3 (BL-364): Lazy Resolution — MANIFEST_FILE wird frisch pro Aufruf aufgeloest,
    kein Import-Zeit-Cache. Unterstuetzt OMNI_TEST_MANIFEST_PATH als Test-Override.
    Silent-Degradation bei fehlendem Vault (AK-10): leeres dict, kein stderr-Print.
    """
    try:
        # AK-3: lazy Aufloesung pro Call (kein Modul-Level-Cache)
        test_override = os.environ.get("OMNI_TEST_MANIFEST_PATH")
        if test_override:
            manifest_file = Path(test_override)
        else:
            manifest_file = _resolve_vault_path("manifest")

        if manifest_file is None or not manifest_file.exists():
            return {}
        content = manifest_file.read_text(encoding="utf-8")
        ctx = {}
        # BDF Status
        m = re.search(r'bdf_status:\s*(\w+)', content)
        if m:
            ctx["bdf_status"] = m.group(1)
        # SDF Status
        m = re.search(r'df_status:\s*(\w+)', content)
        if m:
            ctx["sdf_status"] = m.group(1)
        # Aktiver Modus
        m = re.search(r'aktiver_modus:\s*(\w+)', content)
        if m:
            ctx["modus"] = m.group(1)
        # Feature
        m = re.search(r'df_task:\s*(\S+)', content)
        if m:
            ctx["feature"] = m.group(1)
        # GLOBAL_MODUS
        m = re.search(r'\*\*GLOBAL_MODUS:\*\*\s*(\w+)', content)
        if m:
            ctx["global_modus"] = m.group(1)
        return ctx
    except Exception:
        return {}


def detect_skill_name(tool_input):
    """Extrahiert Skill-Name aus Tool-Input."""
    if isinstance(tool_input, dict):
        skill = tool_input.get("skill", "")
        args = tool_input.get("args", "")
        return skill, args
    return "", ""


def detect_command_in_agent(tool_input):
    """Erkennt Command-Namen in Agent-Prompts."""
    if isinstance(tool_input, dict):
        prompt = tool_input.get("prompt", "")
        desc = tool_input.get("description", "")
        for cmd in ORCHESTRATOR_LEVELS:
            if cmd in prompt or cmd in desc:
                return cmd
    return None


def detect_skill_load(tool_name, tool_input):
    """BL-159 AK-4: Erkenne SKILL_LOAD-Events.

    Returnt (skill_name, load_method, vertrag_bound) oder (None, None, None).
      Skill(skill="_X")              -> ("_X", "skill", True)
      Read(.claude/commands/_X.md)   -> ("_X", "read",  False)
      sonst                          -> (None, None, None)
    """
    if not isinstance(tool_input, dict):
        return None, None, None
    if tool_name == "Skill":
        skill = tool_input.get("skill", "")
        if skill:
            return skill, "skill", True
    elif tool_name == "Read":
        file_path = tool_input.get("file_path", "")
        if file_path:
            normalized = file_path.replace("\\", "/")
            m = SKILL_PATH_PATTERN.search(file_path) or SKILL_PATH_PATTERN.search(normalized)
            if m:
                return m.group(1), "read", False
    return None, None, None


def detect_state_file_edit(tool_input):
    """Erkennt Edits an State-Dateien."""
    if isinstance(tool_input, dict):
        file_path = tool_input.get("file_path", "")
        for sf in STATE_FILES:
            if sf in file_path:
                # Extrahiere was geaendert wird
                new_string = tool_input.get("new_string", "")
                content = tool_input.get("content", "")
                change = new_string or content
                # Kurze Zusammenfassung (erste 200 Zeichen)
                summary = change[:200].replace("\n", " ").strip() if change else ""
                return sf, summary
    return None, None


def worker_id_fields(
    parallelism_budget,
    worker_id,
    lane=None,
    worktree_id=None,
    bl_parallel=False,
    batch_id=None,
) -> dict:
    """BL-194-N9 + BL-230-SB-2 (AK-PER-BATCH-TRACE): worker_id-Felder fuer parallele Audit-Eintraege.

    parallel_aktiv = (int(parallelism_budget) > 1) OR bool(bl_parallel).
    Nicht-parallel ODER worker_id leer/None -> {} (serielle Laeufe byte-identisch, BL-194-N9).
    Parallel + worker_id -> {"worker_id": ...} + "lane"/"worktree_id"/"batch_id" wenn nicht-None.

    batch_id (BL-230-SB-2): batch-id-keyed Stream. Graceful analog worktree_id — leer im
    seriellen Lauf (parallel inaktiv ODER batch_id=None -> KEIN batch_id-Feld).
    """
    try:
        budget = int(parallelism_budget) if parallelism_budget is not None else 0
    except (ValueError, TypeError):
        budget = 0

    parallel_aktiv = (budget > 1) or bool(bl_parallel)

    if not parallel_aktiv or not worker_id:
        return {}

    result = {"worker_id": worker_id}
    if lane is not None:
        result["lane"] = lane
    if worktree_id is not None:
        result["worktree_id"] = worktree_id
    if batch_id is not None:
        result["batch_id"] = batch_id
    return result


def merge_per_batch_streams(streams):
    """BL-230-SB-2 (AK-PER-BATCH-TRACE): merged per-Batch-Audit-Streams deterministisch.

    Beim Fan-In schreibt jeder parallele Worker einen worker-/batch-lokalen Audit-Stream
    (batch-id-keyed, kein Interleaving im geteilten audit.jsonl). Diese Funktion fuehrt die
    per-Batch-Streams DETERMINISTISCH nach batch_id zusammen:
      - stabile Sortierung nach batch_id (reihenfolge-/permutations-invariant),
      - liefert zusaetzlich eine Inventur-Liste der batch_ids (vollstaendig, dedupliziert,
        in sortierter Reihenfolge) fuer sequenz-abhaengige Reader (geist9-Familie).

    streams: Iterable von Listen von Eintraegen (jeder Eintrag ein dict mit "batch_id").
    Returns (merged_stream, inventory).
      merged_stream: alle Eintraege, stabil nach batch_id sortiert.
      inventory: deduplizierte, sortierte Liste der vorkommenden batch_ids.

    EC-BT-4: leere Stream-Liste -> ([], []), kein Crash.
    """
    all_entries = []
    for stream in (streams or []):
        for entry in (stream or []):
            all_entries.append(entry)

    # Stabile Sortierung nach batch_id (Python sort ist stabil -> Eingabe-Reihenfolge
    # innerhalb gleicher batch_id bleibt erhalten -> permutations-invariant ueber Streams).
    def _bid(e):
        return e.get("batch_id", "") if isinstance(e, dict) else ""

    merged = sorted(all_entries, key=_bid)

    # Inventur: deduplizierte, sortierte Liste der batch_ids.
    inventory = sorted({_bid(e) for e in all_entries if _bid(e) != ""})

    return merged, inventory


def write_audit_entry(entry):
    """Schreibt 1 JSONL-Zeile in audit.jsonl."""
    try:
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main():
    try:
        hook_data = json.loads(sys.stdin.read())
        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})
        hook_type = hook_data.get("hook_type", "pre")  # pre oder post

        ts = datetime.now().isoformat(timespec="seconds")
        ctx = read_active_context()

        entry = None

        # --- Skill-Aufrufe (Handschuh-Wechsel) ---
        if tool_name == "Skill":
            skill_name, skill_args = detect_skill_name(tool_input)
            level = ORCHESTRATOR_LEVELS.get(skill_name, "UNKNOWN")
            entry = {
                "ts": ts,
                "event": "HANDOFF",
                "level": level,
                "skill": skill_name,
                "args": skill_args[:300] if skill_args else "",
                "ctx": ctx,
            }

        # --- Agent-Aufrufe (Worker-Spawns) ---
        elif tool_name in ("Agent", "TaskCreate", "SendMessage"):
            cmd = detect_command_in_agent(tool_input)
            if cmd:
                level = ORCHESTRATOR_LEVELS.get(cmd, "WORKER")
            else:
                level = "WORKER"
            desc = ""
            if isinstance(tool_input, dict):
                desc = tool_input.get("description", "")[:200]
            entry = {
                "ts": ts,
                "event": "WORKER_SPAWN",
                "level": level,
                "command": cmd or "custom",
                "description": desc,
                "ctx": ctx,
            }

        # --- State-File Edits ---
        elif tool_name in ("Edit", "Write"):
            state_file, summary = detect_state_file_edit(tool_input)
            if state_file:
                entry = {
                    "ts": ts,
                    "event": "STATE_WRITE",
                    "level": "STATE",
                    "file": state_file,
                    "summary": summary,
                    "ctx": ctx,
                }

        # BL-194-N9: worker_id-Anreicherung fuer parallele Audit-Eintraege (GRACEFUL)
        try:
            _budget = 1
            _bl_parallel = False
            try:
                import sys as _sys
                import importlib as _il
                _resolver = _il.import_module("session_params_resolver")
                _budget = int(_resolver.resolve("parallelism_budget") or 1)
                _bl_parallel = bool(_resolver.resolve("bl_parallel"))
            except Exception:
                pass  # fehlender Resolver oder Fehler -> serielle Defaults
            _worker_id = (
                os.environ.get("OMNI_WORKER_ID")
                or ctx.get("worktree_id")
                or None
            )
            _anno = worker_id_fields(
                _budget,
                _worker_id,
                lane=ctx.get("lane"),
                worktree_id=ctx.get("worktree_id"),
                bl_parallel=_bl_parallel,
            )
        except Exception:
            _anno = {}

        # Logge wenn relevant
        if entry:
            if _anno:
                entry.update(_anno)
            write_audit_entry(entry)

        # BL-159 AK-4: SKILL_LOAD-Event (additiv, parallel zu HANDOFF/STATE_WRITE)
        skill_name, load_method, vertrag_bound = detect_skill_load(tool_name, tool_input)
        if skill_name:
            skill_entry = {
                "ts": ts,
                "event": "SKILL_LOAD",
                "skill_name": skill_name,
                "load_method": load_method,
                "vertrag_bound": vertrag_bound,
                "ctx": ctx,
            }
            if _anno:
                skill_entry.update(_anno)
            write_audit_entry(skill_entry)

        # Hook laesst IMMER durch (Audit = Logging, kein Blocking)
        print(json.dumps({"continue": True}))

    except Exception as e:
        # Bei Fehler: durchlassen, nicht blockieren
        try:
            err_entry = {
                "ts": datetime.now().isoformat(timespec="seconds"),
                "event": "AUDIT_ERROR",
                "error": str(e),
            }
            write_audit_entry(err_entry)
        except Exception:
            pass
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
