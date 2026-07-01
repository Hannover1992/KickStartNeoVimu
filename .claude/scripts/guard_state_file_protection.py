#!/usr/bin/env python3
"""
Claude Code Hook — State-File Protection (Guard-Enforcement CS9)

Pre-Hook auf Edit/Write Tool-Calls: Erkennt direkte Edits an geschuetzten
State-Dateien die NUR durch Pipeline-Orchestratoren geaendert werden duerfen.

CS9: Team Lead editierte _backlog_index.md direkt (BL-022 READY→DONE)
statt den Rueckweg SC→SDF→BDF einzuhalten. SDF haette GAP pruefen,
RECALIBRATE ausfuehren und BDF_NEXT_TRIGGER setzen muessen.

Geschuetzte Dateien:
  _backlog_index.md  — Status-Aenderungen NUR durch SDF/BDF Pipeline
  _parking-lot.md    — [x]/[?]/[!] NUR durch SDF (Ausnahme: STUCKED durch BDF)

enforceProcess=true (Default): BLOCKIERT Violations (continue=false)
enforceProcess=false: NUR Warning (continue=true)
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"


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


def resolve_artifact_path(key: str, bl_slug: str | None = None) -> tuple[str, bool]:
    """Resolve artifact output path for pipeline agents.

    Returns (path, free_mode):
      - free_mode=True  (bl_slug=None): writes to .claude/analysis/drafts/
      - free_mode=False (bl_slug set):  writes to Vault Backlog subfolder

    The existing _resolve_vault_path() is for process-state files only
    (manifest, session_params, etc.) and remains unchanged.
    """
    SUBFOLDER_MAP = {
        "model":          "2_Model/",
        "spec":           "3_Spec/",
        "gap":            "5_Gap/",
        "k_score":        "4_K-Score/",
        "implementation": "Implementation/",
        "crumbs":         "Crumbs/",
        "sc":             "SC/",
        "task":           "1_Task/",
    }

    if bl_slug is None:
        # FREE_MODE — no DCS_VAULT_ROOT required
        import os as _os
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        path = str(ROOT_DIR / ".claude" / "analysis" / "drafts" / f"{key}-{timestamp}.md")
        print("FREE_MODE active — writing to .claude/analysis/drafts/")
        return path, True

    # BL-Mode — DCS_VAULT_ROOT required
    import os as _os
    vault_root = _os.environ.get("DCS_VAULT_ROOT")
    if not vault_root:
        raise EnvironmentError("DCS_VAULT_ROOT not set")

    if key not in SUBFOLDER_MAP:
        raise KeyError(f"Unknown artifact key: {key}")

    subfolder = SUBFOLDER_MAP[key]
    path = f"{vault_root}/OmniCommand/Backlog/{bl_slug}/{subfolder}"
    return path, False


SESSION_PARAMS_FILE = _resolve_vault_path("session_params")
LOG_FILE = ROOT_DIR / ".hook_debug.log"

# State-Dateien die geschuetzt sind + ihre Status-Keywords
PROTECTED_STATE_FILES = {
    "_backlog_index.md": {
        "keywords": ["DONE", "IN_PROGRESS", "PLANNED", "ARCHIVIERT"],
        "reason": "BL-Status NUR durch SDF/BDF Pipeline aendern (CS9: Rueckweg SC→SDF→BDF einhalten)",
    },
    "_parking-lot.md": {
        "keywords": ["[x]", "[?]", "[!]", "[~]", "DONE:", "STUCKED", "QUESTION"],
        "reason": "PL-Status NUR durch SDF aendern (W16, Ausnahme: BDF STUCKED-Promotion)",
    },
}


def read_enforce_process():
    """Liest enforceProcess aus _session_params.md. Default: true."""
    try:
        if not SESSION_PARAMS_FILE.exists():
            return True
        content = SESSION_PARAMS_FILE.read_text(encoding="utf-8")
        match = re.search(r'\*\*enforceProcess:\*\*\s*(true|false)', content)
        if match:
            return match.group(1) == "true"
    except Exception:
        pass
    return True


def is_dark_factory_active():
    """Prueft ob SDF/BDF Pipeline aktiv ist (GLOBAL_MODUS in Manifest).
    Wenn Dark Factory aktiv → SDF/BDF DUERFEN State-Files editieren.
    CS9 Fix: Guard soll nur MANUELLES Editieren blocken, nicht Pipeline-Edits."""
    try:
        manifest_path = _resolve_vault_path("manifest")
        if not manifest_path.exists():
            return False
        content = manifest_path.read_text(encoding="utf-8")
        if "big_dark_factory" in content or "small_dark_factory" in content:
            # Zusaetzlich: GLOBAL_MODUS muss gesetzt sein (nicht nur irgendwo erwaehnt)
            match = re.search(r'\*\*GLOBAL_MODUS:\*\*\s*(big_dark_factory|small_dark_factory)', content)
            return match is not None
    except Exception:
        pass
    return False


def append_guard_log(violation_type, details, blocked):
    """Appende Violation an GUARD_LOG Datei."""
    try:
        GUARD_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        entry = f"- [{timestamp}] **{violation_type}** [{action}]: {details}\n"
        with open(GUARD_LOG_FILE, "a", encoding='utf-8') as f:
            f.write(entry)
    except Exception:
        pass


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

        if tool_name not in ["Edit", "Write"]:
            print(json.dumps({"continue": True}))
            return

        # Datei-Pfad aus Tool-Input extrahieren
        file_path = ""
        new_string = ""
        content = ""
        if isinstance(tool_input, dict):
            file_path = tool_input.get("file_path", "")
            new_string = tool_input.get("new_string", "")  # Edit tool
            content = tool_input.get("content", "")  # Write tool

        edit_content = new_string or content

        if not file_path or not edit_content:
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()

        # CS9 Fix: SDF/BDF Pipeline DARF State-Files editieren
        # Guard blockt NUR manuelles Editieren (ohne Pipeline-Kontext)
        if is_dark_factory_active():
            print(json.dumps({"continue": True}))
            return

        # Pruefe ob die editierte Datei geschuetzt ist
        for protected_file, config in PROTECTED_STATE_FILES.items():
            if protected_file in file_path:
                # Pruefe ob Status-Keywords in der Aenderung vorkommen
                found_keywords = [
                    kw for kw in config["keywords"]
                    if kw.lower() in edit_content.lower()
                ]

                if found_keywords:
                    warning = (
                        f"[GUARD-VIOLATION] DIREKTE STATE-AENDERUNG an {protected_file}! "
                        f"Gefundene Status-Keywords: {found_keywords}. "
                        f"{config['reason']} "
                        f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
                    )
                    print(json.dumps({
                        "continue": not enforce,
                        "message": warning
                    }))
                    append_guard_log(
                        "STATE_FILE_DIRECT_EDIT",
                        f"{protected_file}: Keywords {found_keywords} direkt editiert statt Pipeline",
                        enforce
                    )
                    return

        # Kein Verstoss
        print(json.dumps({"continue": True}))

    except Exception as e:
        try:
            with open(LOG_FILE, "a", encoding='utf-8') as log:
                log.write(f"[{datetime.now()}] guard_state_file_protection Error: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
