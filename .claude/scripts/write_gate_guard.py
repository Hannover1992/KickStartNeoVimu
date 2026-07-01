#!/usr/bin/env python3
"""
write_gate_guard.py — BL-460 B-1: BL-443-Hard-Gate (AK-CTX-1-PL-1).

Blockt destruktiven --write-Betrieb des BL-460-Schwarms wenn der Vault
null-byte-korrupte .md-Nodes enthaelt (BL-443 offen / nicht geheilt).

Patterns:
  NC-4: guard_-Prefix (Modul-Dateiname write_gate_guard.py per Planvorgabe)
  DT-4: stdin-JSON Hook-Mode (continue/message Output)
  DT-5: exit-Code 0=clean/allow, 1=gated/block, 2=usage
  DT-7: enforceProcess aus _session_params.md (true=block, false=warn)
  DT-13: resolve_vault_root.py als Lead-Resolver (kein inline resolver)

Null-byte-Detection-Logik (BL-443-Gate):
    open(p, 'rb').read().count(0) > 0   fuer alle *.md-Dateien (rglob)

Fail-open ist HEILIG: PermissionError/IOError beim Scan -> continue:true, exit 0.
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
        override = os.environ.get("OMNI_WRITE_GATE_ENFORCE")
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

def _count_corrupt_nodes(vault_root: str | Path) -> int:
    """
    Zaehlt null-byte-korrupte .md-Dateien im vault_root (rekursiv via rglob).

    Nur .md-Dateien werden gescannt.
    Eine Datei mit >=1 null-byte zaehlt als 1 corrupt node.
    PermissionError/IOError pro Datei: fail-open (ignorieren).

    Returns:
        Anzahl korrupter .md-Nodes (int >= 0).
        Gibt 0 zurueck wenn vault_root nicht existiert (fail-open).
    """
    try:
        vault_path = Path(vault_root)
        if not vault_path.exists():
            return 0

        count = 0
        for p in vault_path.rglob("*.md"):
            try:
                if open(p, "rb").read().count(0) > 0:
                    count += 1
            except (PermissionError, IOError, OSError):
                pass  # fail-open: unlesbare Datei ignorieren
        return count
    except Exception:
        return 0


def is_write_gated(
    vault_root: str | Path | None = None,
) -> tuple[bool, str]:
    """
    Prueft ob der destruktive --write fuer BL-460-Schwarm gegattet ist.

    Operationalisierung von AK-CTX-1 / BL-443-Gate:
    Scannt vault_root rekursiv auf null-byte-korrupte .md-Dateien.

    Returns:
        (True,  "N corrupt nodes found — write gated (BL-443 open)")
            -> BLOCK (write muss warten)
        (False, "clean — 0 corrupt nodes")
            -> ALLOW (BL-443 implizit geheilt)

    vault_root:
        None -> resolve_vault_root.py via DT-13-Delegation
        Explizit -> Override fuer Tests

    Fail-open: jede Exception -> (False, "clean — 0 corrupt nodes")
    """
    try:
        # vault_root via DT-13 falls nicht explizit angegeben
        if vault_root is None:
            try:
                sys.path.insert(0, str(SCRIPT_DIR))
                from resolve_vault_root import resolve_vault_root as _resolve
                vault_root = _resolve()
            except Exception:
                return (False, "clean — 0 corrupt nodes")

        vault_path = Path(vault_root)

        # fail-open bei nicht-existentem Vault
        if not vault_path.exists():
            return (False, "clean — 0 corrupt nodes")

        n = _count_corrupt_nodes(vault_path)

        if n > 0:
            return (True, f"{n} corrupt nodes found — write gated (BL-443 open)")
        else:
            return (False, "clean — 0 corrupt nodes")

    except Exception:
        return (False, "clean — 0 corrupt nodes")


# ---------------------------------------------------------------------------
# CLI (DT-4 stdin-JSON hook-mode + DT-5 exit codes)
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    """
    CLI-Interface fuer write_gate_guard.

    Args:
        --vault-root PATH   Vault-Root Override

    Stdin (hook-mode):
        JSON: {"tool_name": "...", "tool_input": {...}}

    Stdout:
        {"continue": true|false, "message": "..."}

    Exit-Codes (DT-5):
        0 — ALLOW (clean vault) oder WARN (enforceProcess=false)
        1 — BLOCK (korrupte Nodes + enforceProcess=true)
        2 — Usage-Fehler
    """
    if argv is None:
        argv = sys.argv[1:]

    vault_root: str | None = None

    # Parsen der bekannten Flags
    i = 0
    unknown_flags = []
    while i < len(argv):
        arg = argv[i]
        if arg == "--vault-root" and i + 1 < len(argv):
            vault_root = argv[i + 1]
            i += 2
        elif arg == "--write":
            # --write Flag erkannt (kein Fehler)
            i += 1
        elif arg.startswith("--"):
            unknown_flags.append(arg)
            i += 1
        else:
            i += 1

    # Usage-Fehler bei unbekannten Flags
    if unknown_flags:
        print(json.dumps({
            "continue": False,
            "message": f"Usage error: unknown flags {unknown_flags}"
        }))
        return 2

    # enforceProcess lesen
    vr_for_enforce = Path(vault_root) if vault_root else None
    enforce = _read_enforce_process(vault_root=vr_for_enforce)

    # Core-Pruefung
    gated, reason = is_write_gated(vault_root=vault_root)

    if not gated:
        result = {"continue": True, "message": f"ALLOW: {reason}"}
        print(json.dumps(result))
        return 0
    else:
        if enforce:
            result = {"continue": False, "message": f"BLOCK: {reason}"}
            print(json.dumps(result))
            return 1
        else:
            result = {"continue": True, "message": f"WARN BL-443 open: {reason}"}
            print(json.dumps(result))
            return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
