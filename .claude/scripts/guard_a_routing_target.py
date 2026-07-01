#!/usr/bin/env python3
"""
guard_a_routing_target.py — A-Pipeline Phase 5 Routing-Target Rail Guard

Blockiert (oder warnt vor) Manifest-Writes mit ungueltigem `routing_target`-Wert.
Whitelist: {BDF, ROADMAP, IDF, STOP}.
DIRECT_I ist RETIRED (Refit 2026-05-17) — wird IMMER geblockt.

INV-RT-RAILGUARD: routing_target MUSS in der Whitelist sein.
Pattern: guard_modus_writer.py + guard_metric_derivation.py.

Refit-Anchor: BL-165 INV-MODUS-1 — DIRECT_I umging SDF Phase 1.1 modusEntscheidung.
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

# Whitelist V3 (INV-RT-RAILGUARD-V3)
# A-Routing erlaubt NUR 3 Targets — SC/SDF/I sind verboten als A-direct-target,
# weil sie via Pipeline-Hierarchie erreicht werden:
#   A -> IDF -> (Phase 8.5 Auto-Chain) -> SDF Phase 1.1 modusEntscheidung -> M{N}
#   M2/M3 -> I_orchestrate, M4-M7 -> SC_orchestrate
VALID_TARGETS = {"BDF", "ROADMAP", "IDF", "STOP"}

# Retired alt-Vokabular (immer blocken)
RETIRED_TARGETS = {"DIRECT_I", "I_DIRECT", "DIRECT_SC", "SC_DIRECT"}

# Invalid AS A-routing target — Skills existieren, aber A darf nicht direct routen.
# SC ist Sub-Modus von SDF (M4-M7), SDF braucht IDF-Decomp, I via SDF Phase 2.1 Dispatch.
INVALID_AS_A_TARGET = {"SC", "SDF", "I"}

# Matcher: routing_target Field-Write (YAML oder Markdown-Inline)
# Beispiele:
#   routing_target: "DIRECT_I"
#   routing_target: DIRECT_I
#   A_PIPELINE_STATE.routing_target = "DIRECT_I"
ROUTING_TARGET_PATTERN = re.compile(
    r"routing_target\s*[:=]\s*[\"']?([A-Z_]+)[\"']?",
    re.IGNORECASE,
)

# Matcher: _manifest.md Files (per-Story oder Vault)
MANIFEST_FILE_PATTERN = re.compile(r"[/\\]_manifest\.md$")


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
    return ROOT_DIR / "_session_params.md"


SESSION_PARAMS = _resolve_session_params()


def read_enforce_process() -> bool:
    """Liest enforceProcess aus _session_params.md.
    Test-Override: OMNI_ENFORCE_ROUTING_GUARD=1 erzwingt enforce=true.
    Default: False (WARN-Mode) wenn Datei fehlt oder unlesbar.
    """
    if os.environ.get("OMNI_ENFORCE_ROUTING_GUARD") == "1":
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
            f"- [{timestamp}] **INV-RT-RAILGUARD-V3** [{action}]: "
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
            f.write(f"[{datetime.now()}] guard_a_routing_target: {msg}\n")
    except Exception:
        pass


def is_manifest_file(file_path: str) -> bool:
    """Prueft ob file_path ein _manifest.md ist."""
    if not file_path:
        return False
    normalized = file_path.replace("\\", "/")
    return bool(MANIFEST_FILE_PATTERN.search(normalized)) or bool(
        MANIFEST_FILE_PATTERN.search(file_path)
    )


def check_content(content: str) -> list:
    """Prueft Content auf routing_target-Violations.
    Returns: Liste von Violation-Strings (leer = kein Fehler).
    """
    violations = []

    # Finde alle routing_target-Werte im Content
    matches = ROUTING_TARGET_PATTERN.findall(content)
    if not matches:
        return violations  # kein routing_target im Diff → kein Check

    for target_value in matches:
        target_upper = target_value.upper()

        # RETIRED-Check: DIRECT_I + Varianten (alt-Vokabular)
        if target_upper in RETIRED_TARGETS:
            violations.append(
                f"RETIRED target='{target_value}' detected — DIRECT_I-Familie ist "
                f"aufgehoben (Refit-V3 2026-05-17, BL-165 INV-MODUS-1). "
                f"Verwende stattdessen: IDF (Default-Pfad)."
            )
            continue

        # INVALID_AS_A_TARGET-Check: SC/SDF/I sind als A-direct-target verboten
        # (Refit-V3 2026-05-17, User-Direct-Korrektur)
        if target_upper in INVALID_AS_A_TARGET:
            violations.append(
                f"INVALID_AS_A_TARGET target='{target_value}' — SC/SDF/I sind "
                f"als A-routing target VERBOTEN (Pipeline-Hierarchie-Verletzung). "
                f"Sie sind erreichbar via: A -> IDF -> (Phase 8.5 Auto-Chain) -> "
                f"SDF Phase 1.1 modusEntscheidung -> M{{N}} (M2/M3 -> I, M4-M7 -> SC). "
                f"Use IDF als A-routing target stattdessen."
            )
            continue

        # Whitelist-Check V3
        if target_upper not in VALID_TARGETS:
            violations.append(
                f"Invalid routing_target='{target_value}' — nicht in Whitelist V3 "
                f"{sorted(VALID_TARGETS)}. INV-RT-RAILGUARD-V3 enforced."
            )

    return violations


def build_block_output(violations: list, file_path: str) -> dict:
    """Erstellt das Hook-Output-Dict fuer HARD-Block."""
    violation_str = "; ".join(violations)
    message = (
        f"[INV-RT-RAILGUARD-V3 BLOCKED] guard_a_routing_target: {file_path} — "
        f"{violation_str}. "
        f"Whitelist V3: BDF | IDF | STOP. "
        f"DIRECT_I retired (alt-Vokabular), SC/SDF/I invalid AS A-target (Pipeline-Hierarchie)."
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

        # Frueh-Exit: kein _manifest.md File
        if not is_manifest_file(file_path):
            print(json.dumps({"continue": True}))
            return

        # Content extrahieren: Edit -> new_string, Write -> content
        change_content = tool_input.get("new_string") or tool_input.get("content") or ""

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
                f"[guard_a_routing_target BLOCK] {file_path}\n"
            )
            for v in violations:
                sys.stderr.write(f"  - {v}\n")
            sys.stderr.write(
                f"Fix: Verwende routing_target aus Whitelist "
                f"{sorted(VALID_TARGETS)} (Refit 2026-05-17 INV-RT-RAILGUARD).\n"
            )
            print(json.dumps(build_block_output(violations, file_path)))
            sys.exit(1)
        else:
            # WARN-Mode: stderr-Warnung, exit(0), passthrough
            sys.stderr.write(
                f"[guard_a_routing_target WARN] {file_path}: "
                f"{violations}\n"
                f"  Fix: routing_target Whitelist (BL-165 INV-MODUS-1) — "
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
