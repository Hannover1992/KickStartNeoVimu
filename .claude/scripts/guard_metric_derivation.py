#!/usr/bin/env python3
"""
guard_metric_derivation.py — BL-174 AK-18 PreToolUse Hook

Blockiert (oder warnt vor) PL-Item-Writes ohne derivation_source-Feld.
Enforcement basiert auf enforceProcess-Flag in _session_params.md.

INV-DERIV-1: Worker schreibt KEINE PL-Item-File ohne derivation_source-Marker.
Pattern: guard_modus_writer.py (BL-165 AK-5) — identische Hook-Struktur.
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# Matcher: PL-Item-Files in jedem 6_PL-Subfolder (cross-platform separators)
PL_FILE_PATTERN = re.compile(r"[/\\]6_PL[/\\][^/\\]*_PL_Items\.md$")

# derivation_source muss AK-15, AK-16, AK-17 oder AK-18 referenzieren
# AK-18 = self-reference fuer Linter/Hook-Items (PL-RUN-10 2026-05-17)
# Gueltiger Wert: "AK-15", "AK-16", "AK-17", "AK-18" (auch in Quotes oder mit Leerzeichen um :)
DERIVATION_SOURCE_PATTERN = re.compile(
    r"derivation_source\s*:\s*[\"']?\s*AK-(?:15|16|17|18)[\"']?",
    re.IGNORECASE,
)

# metric_provenance: derived ist positiv (optional check)
PROVENANCE_DERIVED_PATTERN = re.compile(
    r"metric_provenance\s*:\s*[\"']?\s*derived[\"']?",
    re.IGNORECASE,
)

# metric_provenance: hand_waved ist VERBOTEN (per AK-15 + INV-DERIV-1)
PROVENANCE_HAND_WAVED_PATTERN = re.compile(
    r"metric_provenance\s*:\s*[\"']?\s*hand_waved[\"']?",
    re.IGNORECASE,
)


def _resolve_session_params():
    """Sucht _session_params.md — zuerst via resolve_vault_root.py, dann Fallback."""
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
                    candidate = Path(vault_root_str) / "_session_params.md"
                    if candidate.exists():
                        return candidate
    except Exception:
        pass
    # Fallback: ROOT_DIR direkt
    return ROOT_DIR / "_session_params.md"


SESSION_PARAMS = _resolve_session_params()


def read_enforce_process() -> bool:
    """
    Liest enforceProcess aus _session_params.md.
    Test-Override: OMNI_ENFORCE_METRIC_GUARD=1 erzwingt enforce=true.
    Default: False (WARN-Mode) wenn Datei fehlt oder unlesbar.
    """
    if os.environ.get("OMNI_ENFORCE_METRIC_GUARD") == "1":
        return True
    try:
        if not SESSION_PARAMS.exists():
            return False
        content = SESSION_PARAMS.read_text(encoding="utf-8")
        m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
        if m:
            return m.group(1).strip().lower() == "true"
    except Exception:
        pass
    return False


def append_guard_log(file_path: str, violations: list, mode: str) -> None:
    """Appendet Log-Eintrag in _guard_log.md (analog guard_modus_writer.py)."""
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if mode == "HARD" else "WARNED"
        violation_str = "; ".join(violations)
        entry = (
            f"- [{timestamp}] **INV-DERIV-1** [{action}]: "
            f"{file_path} — {violation_str}\n"
        )
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def append_debug_log(msg: str) -> None:
    """Schreibt in .hook_debug.log bei unerwarteten Exceptions."""
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] guard_metric_derivation: {msg}\n")
    except Exception:
        pass


def is_pl_item_file(file_path: str) -> bool:
    """Prueft ob file_path ein PL-Item-File in einem 6_PL-Ordner ist."""
    if not file_path:
        return False
    # Normalisiere auf Forward-Slashes fuer konsistenten Match
    normalized = file_path.replace("\\", "/")
    return bool(PL_FILE_PATTERN.search(normalized)) or bool(
        PL_FILE_PATTERN.search(file_path)
    )


def check_content(content: str) -> list:
    """
    Prueft Content auf INV-DERIV-1 Violations.
    Returns: Liste von Violation-Strings (leer = kein Fehler).
    """
    violations = []

    # Pflicht-Check: derivation_source muss vorhanden und gueltig sein
    if not DERIVATION_SOURCE_PATTERN.search(content):
        violations.append(
            "Missing/invalid derivation_source (expected: AK-15, AK-16, AK-17, or AK-18)"
        )

    # Verbots-Check: metric_provenance=hand_waved ist nie erlaubt
    if PROVENANCE_HAND_WAVED_PATTERN.search(content):
        violations.append(
            "Forbidden value: metric_provenance=hand_waved (use 'derived' or 'unresolved')"
        )

    return violations


def build_block_output(violations: list, file_path: str) -> dict:
    """Erstellt das Hook-Output-Dict fuer HARD-Block."""
    violation_str = "; ".join(violations)
    message = (
        f"[INV-DERIV-1 BLOCKED] guard_metric_derivation: {file_path} — "
        f"{violation_str}. "
        f"Add `derivation_source: AK-15|AK-16|AK-17|AK-18` and "
        f"`metric_provenance: derived` per BL-174 AK-18."
    )
    return {"continue": False, "message": message}


def build_warn_output(violations: list, file_path: str) -> dict:
    """Erstellt das Hook-Output-Dict fuer WARN-Mode (passthrough)."""
    return {"continue": True}


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
        raw = sys.stdin.read()
        hook_data = json.loads(raw)

        tool_name = hook_data.get("tool_name", "")
        tool_input = hook_data.get("tool_input", {})

        # Nur Edit und Write sind relevant
        if tool_name not in ("Edit", "Write"):
            print(json.dumps({"continue": True}))
            return

        if not isinstance(tool_input, dict):
            print(json.dumps({"continue": True}))
            return

        file_path = tool_input.get("file_path", "")

        # Frueh-Exit: kein PL-Item-File
        if not is_pl_item_file(file_path):
            print(json.dumps({"continue": True}))
            return

        # Content extrahieren: Edit -> new_string, Write -> content
        change_content = tool_input.get("new_string") or tool_input.get("content") or ""

        # Leerer Content ist kein Fehler (z.B. Delete-ähnliche Ops)
        if not change_content.strip():
            print(json.dumps({"continue": True}))
            return

        violations = check_content(change_content)

        if not violations:
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()
        mode = "HARD" if enforce else "WARN"

        # Log immer schreiben (unabhaengig vom Mode)
        append_guard_log(file_path, violations, mode)

        if enforce:
            # HARD-Block: stderr-Ausgabe + exit(1)
            sys.stderr.write(
                f"[guard_metric_derivation BLOCK] {file_path}\n"
            )
            for v in violations:
                sys.stderr.write(f"  - {v}\n")
            sys.stderr.write(
                "Fix: Add `derivation_source: AK-15|AK-16|AK-17|AK-18` "
                "and `metric_provenance: derived` (BL-174 INV-DERIV-1).\n"
            )
            print(json.dumps(build_block_output(violations, file_path)))
            sys.exit(1)
        else:
            # WARN-Mode: stderr-Warnung, exit(0), passthrough
            sys.stderr.write(
                f"[guard_metric_derivation WARN] {file_path}: "
                f"{violations}\n"
                f"  Add derivation_source (BL-174 INV-DERIV-1) — "
                f"enforceProcess=false, warning only.\n"
            )
            print(json.dumps(build_warn_output(violations, file_path)))

    except json.JSONDecodeError as e:
        append_debug_log(f"JSONDecodeError: {e}")
        print(json.dumps({"continue": True}))
    except Exception as e:
        append_debug_log(f"Unexpected error: {e}")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
