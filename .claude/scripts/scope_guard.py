#!/usr/bin/env python3
"""
scope_guard.py — BL-460 B-1: OmniCommand-Vault-Scope-Guard (AK-5-PL-1).

Prueft ob ein Ziel-Pfad innerhalb des OmniCommand-Vaults liegt.
Blockt DCS-Vault und alle anderen fremden Pfade.

Patterns:
  NC-4: guard_-Prefix (Modul-Dateiname scope_guard.py per Planvorgabe)
  DT-4: stdin-JSON Hook-Mode (continue/message Output)
  DT-5: exit-Code 0=allow, 1=block, 2=usage
  DT-7: enforceProcess aus _session_params.md (true=block, false=warn)
  DT-13: resolve_vault_root.py als Lead-Resolver (kein inline resolver)

Fail-open ist HEILIG: jede Exception -> continue:true, exit 0.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()


# ---------------------------------------------------------------------------
# enforceProcess (DT-7)
# ---------------------------------------------------------------------------

def _read_enforce_process(vault_root: Path | None = None) -> bool:
    """Liest enforceProcess aus _session_params.md. Default: True (sicher)."""
    try:
        # Test-Override via ENV
        override = os.environ.get("OMNI_SCOPE_GUARD_ENFORCE")
        if override == "1":
            return True
        if override == "0":
            return False

        # Suche _session_params.md
        candidates = []
        if vault_root is not None:
            candidates.append(Path(vault_root) / "_session_params.md")
        candidates.append(SCRIPT_DIR.parent / "analysis" / "_session_params.md")

        for candidate in candidates:
            try:
                if candidate.exists():
                    content = candidate.read_text(encoding="utf-8")
                    m = re.search(r"\*\*enforceProcess:\*\*\s*(true|false)", content)
                    if m:
                        return m.group(1).strip().lower() == "true"
            except Exception:
                pass
    except Exception:
        pass
    return True


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

def check_vault_scope(
    target_path: str | Path | None,
    vault_root: str | Path | None = None,
) -> tuple[bool, str]:
    """
    Prueft ob target_path innerhalb des OmniCommand-Vaults liegt.

    Returns:
        (True, "")           — Pfad ist im OmniCommand-Vault (ALLOW)
        (False, reason_str)  — Pfad ist ausserhalb / DCS-Vault (BLOCK)

    vault_root:
        None -> resolve_vault_root.py via DT-13-Delegation
        Explizit -> Override fuer Tests

    Fail-open: jede Exception -> (True, "") — Guard darf Betrieb nicht lahmlegen.
    """
    try:
        # Fail-open: ungueltige Eingaben
        if target_path is None or target_path == "":
            return (True, "")

        # vault_root via DT-13 falls nicht explizit angegeben
        if vault_root is None:
            try:
                sys.path.insert(0, str(SCRIPT_DIR))
                from resolve_vault_root import resolve_vault_root as _resolve
                vault_root = _resolve()
            except Exception:
                return (True, "")

        # Normalisiere Pfade (Windows-kompatibel: normcase + resolve-Simulation)
        try:
            resolved_target = Path(os.path.normcase(os.path.abspath(str(target_path))))
            resolved_vault = Path(os.path.normcase(os.path.abspath(str(vault_root))))
        except Exception:
            return (True, "")

        # Vault-Root muss existieren — fail-open wenn nicht
        if not resolved_vault.exists():
            return (True, "")

        # Pruefe Zugehoerigkeit via os.path.commonpath (schuetzt vor startswith-Prefix-Bug)
        try:
            common = Path(os.path.commonpath([str(resolved_target), str(resolved_vault)]))
            # Target ist im Vault wenn commonpath == vault_root
            if common == resolved_vault:
                return (True, "")
            else:
                reason = (
                    f"Path '{target_path}' is outside OmniCommand vault "
                    f"(vault_root='{vault_root}')"
                )
                return (False, reason)
        except ValueError:
            # commonpath wirft ValueError bei Pfaden auf unterschiedlichen Laufwerken (Windows)
            reason = (
                f"Path '{target_path}' is on a different drive than vault_root '{vault_root}'"
            )
            return (False, reason)

    except Exception:
        return (True, "")


# ---------------------------------------------------------------------------
# CLI (DT-4 stdin-JSON hook-mode + DT-5 exit codes)
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """
    CLI-Interface fuer scope_guard.

    Args:
        --path PATH         Ziel-Pfad (explizit)
        --vault-root PATH   Vault-Root Override

    Stdin (hook-mode, wenn kein --path):
        JSON: {"tool_name": "...", "tool_input": {"file_path": "..."}}

    Stdout:
        {"continue": true|false, "message": "..."}

    Exit-Codes (DT-5):
        0 — ALLOW oder WARN (enforceProcess=false)
        1 — BLOCK (enforceProcess=true + scope-Verletzung)
        2 — Usage-Fehler
    """
    if argv is None:
        argv = sys.argv[1:]

    target_path: str | None = None
    vault_root: str | None = None

    # Parsen der bekannten Flags
    i = 0
    unknown_flags = []
    while i < len(argv):
        arg = argv[i]
        if arg == "--path" and i + 1 < len(argv):
            target_path = argv[i + 1]
            i += 2
        elif arg == "--vault-root" and i + 1 < len(argv):
            vault_root = argv[i + 1]
            i += 2
        elif arg.startswith("--"):
            unknown_flags.append(arg)
            i += 1
        else:
            i += 1

    # Stdin hook-mode: lese target aus JSON wenn kein --path
    if target_path is None:
        # Pruefe ob stdin verfuegbar (kein TTY)
        if not sys.stdin.isatty():
            try:
                raw = sys.stdin.read()
                data = json.loads(raw)
                tool_input = data.get("tool_input", {})
                target_path = tool_input.get("file_path") or tool_input.get("path")
            except Exception:
                pass

    # Usage-Fehler: weder --path noch stdin-JSON geliefert
    if target_path is None:
        print(json.dumps({"continue": False, "message": "Usage: scope_guard.py --path PATH [--vault-root PATH]"}))
        return 2

    # enforceProcess lesen
    vr_for_enforce = Path(vault_root) if vault_root else None
    enforce = _read_enforce_process(vault_root=vr_for_enforce)

    # Core-Pruefung
    allowed, reason = check_vault_scope(target_path, vault_root=vault_root)

    if allowed:
        result = {"continue": True, "message": "ALLOW: path is within OmniCommand vault"}
        print(json.dumps(result))
        return 0
    else:
        if enforce:
            result = {"continue": False, "message": f"BLOCK: {reason}"}
            print(json.dumps(result))
            return 1
        else:
            result = {"continue": True, "message": f"WARN scope out of OmniCommand vault: {reason}"}
            print(json.dumps(result))
            return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
