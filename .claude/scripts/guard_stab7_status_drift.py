#!/usr/bin/env python3
"""
guard_stab7_status_drift.py — Intra-Skill Stabilization Hook S#7

Schicht: Stabilization (intra-Skill, drift-pattern-based) — nicht Geist-zentrisch.

Drift-Pattern (Enforce_Refactor_Master_Analyse_2026-05-27.md):
  `_backlog_index.md` Status-Spalte sagt "DONE" aber Vault-Knoten Frontmatter sagt
  "READY" (oder umgekehrt). Inkonsistenz fuehrt zu Lead-Decisions auf falscher Datenbasis.

PreToolUse-Hook fuer Edit/Write auf:
  - `_backlog_index.md` (Status-Spalte in Tabelle)
  - `Backlog/BL-*.md` (Frontmatter `status:` Feld)
  - `Backlog/BL-*-*/BL-*.md` (Per-Folder-Knoten, BL-160+ Schema)

Logik:
  1. Bestimme welche Quelle modifiziert wird (Index oder Vault-Knoten).
  2. Extrahiere modifizierte BL-IDs + neue Status-Werte aus tool_input.
  3. Lies die ANDERE Quelle und vergleiche Status pro BL-ID.
  4. Bei Diskrepanz: WARN (Default — User koennte gerade synchronisieren).
  5. Bei `enforce=true` UND `OMNI_STATUS_DRIFT_STRICT=1`: BLOCK.

Konservativ:
  - Vault-Knoten fehlt -> passthrough (kann legitimer Erst-Write sein).
  - Index-Zeile fehlt -> passthrough.
  - Status nicht parsebar -> passthrough.

Style-Reference: guard_modus_writer.py, guard_a_routing_target.py.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

GUARD_LOG = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# Status-Vokabular (BL-Lifecycle): READY/PLANNED/IN_PROGRESS/DONE/ARCHIVIERT/DRAFT/DECOMPOSED
KNOWN_STATUS = {
    "READY", "PLANNED", "IN_PROGRESS", "DONE", "ARCHIVIERT",
    "DRAFT", "DECOMPOSED", "BLOCKED", "DEFERRED",
}

# Matcher: _backlog_index.md File (cross-platform separators)
INDEX_FILE_PATTERN = re.compile(r"[/\\]_backlog_index\.md$")

# Matcher: Vault BL-Knoten — entweder direkt `Backlog/BL-NNN-*.md` oder
# `Backlog/BL-NNN-*/BL-NNN-*.md` (Per-Folder-Schema BL-160+).
BL_FILE_PATTERN = re.compile(
    r"[/\\]Backlog[/\\]BL-(\d{3})[A-Za-z0-9_\-]*\.md$",
    re.IGNORECASE,
)

# Index-Table-Row: | BL-NNN | Title | STATUS | path | ... |
INDEX_ROW_PATTERN = re.compile(
    r"\|\s*BL-(\d{3})\s*\|\s*[^|]+\|\s*([A-Z_]+)\s*\|",
)

# Frontmatter `status: STATUS` (YAML, einfache Quotes optional)
FRONTMATTER_STATUS_PATTERN = re.compile(
    r"(?:^|\n)\s*status\s*:\s*[\"']?([A-Z_]+)[\"']?",
    re.IGNORECASE,
)

# id: BL-NNN aus Frontmatter (zur Disambiguation wenn BL-Folder mehrere BLs hat)
FRONTMATTER_ID_PATTERN = re.compile(
    r"(?:^|\n)\s*(?:bl|id)\s*:\s*[\"']?(BL-\d{3})[\"']?",
    re.IGNORECASE,
)


def _resolve_vault_root() -> Path:
    """Resolves Vault-Root via resolve_vault_root.py, fallback ROOT_DIR-parent."""
    try:
        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True, text=True, timeout=5,
                cwd=str(ROOT_DIR),
            )
            if proc.returncode == 0:
                out = proc.stdout.strip()
                if out:
                    return Path(out)
    except Exception:
        pass
    return ROOT_DIR


VAULT_ROOT = _resolve_vault_root()
SESSION_PARAMS = VAULT_ROOT / "_session_params.md"


def read_enforce_process() -> bool:
    """Liest enforceProcess aus _session_params.md (Vault-Root).
    Test-Override: OMNI_ENFORCE_STAB7=1 erzwingt enforce=true.
    """
    if os.environ.get("OMNI_ENFORCE_STAB7") == "1":
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


def read_strict_mode() -> bool:
    """OMNI_STATUS_DRIFT_STRICT=1 + enforce=true => BLOCK statt WARN."""
    return os.environ.get("OMNI_STATUS_DRIFT_STRICT") == "1"


def append_guard_log(file_path: str, drifts: list, blocked: bool) -> None:
    """Appendet Eintrag in _guard_log.md (analog guard_modus_writer.py)."""
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        drift_str = "; ".join(drifts)
        entry = (
            f"- [{timestamp}] **STAB7_STATUS_DRIFT** [{action}]: "
            f"{file_path} — {drift_str}\n"
        )
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def append_debug_log(msg: str) -> None:
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] guard_stab7_status_drift: {msg}\n")
    except Exception:
        pass


def is_index_file(file_path: str) -> bool:
    if not file_path:
        return False
    return bool(INDEX_FILE_PATTERN.search(file_path.replace("\\", "/"))) or \
        bool(INDEX_FILE_PATTERN.search(file_path))


def match_bl_file(file_path: str) -> str:
    """Gibt BL-NNN string zurueck falls Pfad ein Vault-BL-Knoten ist, sonst ''."""
    if not file_path:
        return ""
    normalized = file_path.replace("\\", "/")
    m = BL_FILE_PATTERN.search(normalized) or BL_FILE_PATTERN.search(file_path)
    if m:
        return f"BL-{m.group(1)}"
    return ""


def extract_index_rows(content: str) -> dict:
    """Extrahiert {BL-NNN: STATUS} aus Index-Tabellen-Zeilen im Content."""
    rows = {}
    for m in INDEX_ROW_PATTERN.finditer(content):
        bl_id = f"BL-{m.group(1)}"
        status = m.group(2).strip().upper()
        if status in KNOWN_STATUS:
            rows[bl_id] = status
    return rows


def extract_frontmatter_status(content: str) -> str:
    """Extrahiert status-Wert aus YAML-Frontmatter (nur erstes Match)."""
    m = FRONTMATTER_STATUS_PATTERN.search(content)
    if m:
        s = m.group(1).strip().upper()
        if s in KNOWN_STATUS:
            return s
    return ""


def extract_frontmatter_id(content: str) -> str:
    """Extrahiert bl/id-Feld aus Frontmatter."""
    m = FRONTMATTER_ID_PATTERN.search(content)
    if m:
        return m.group(1).strip().upper()
    return ""


def read_index_status(bl_id: str) -> str:
    """Liest aktuellen Status fuer bl_id aus _backlog_index.md.
    Sucht zuerst im Vault-Root, dann in .claude/analysis/ (lokaler Fallback).
    Returns leer-string wenn nicht gefunden/lesbar.
    """
    candidates = [
        VAULT_ROOT / "_backlog_index.md",
        ROOT_DIR / ".claude" / "analysis" / "_backlog_index.md",
    ]
    for cand in candidates:
        try:
            if cand.is_file():
                content = cand.read_text(encoding="utf-8")
                rows = extract_index_rows(content)
                if bl_id in rows:
                    return rows[bl_id]
        except Exception:
            continue
    return ""


def find_vault_bl_file(bl_id: str) -> Path:
    """Sucht Vault-BL-Knoten-Datei fuer bl_id. Returns Path oder leer-Path.
    Schemata:
      - Vault/Backlog/BL-NNN-*.md (legacy single-file)
      - Vault/Backlog/BL-NNN-*/BL-NNN.md (Per-Folder BL-160+, optional)
    """
    backlog_dir = VAULT_ROOT / "Backlog"
    if not backlog_dir.is_dir():
        return Path()

    num_part = bl_id.split("-")[-1] if "-" in bl_id else ""
    if not num_part:
        return Path()

    prefix_lower = f"bl-{num_part}-"
    short_lower = f"bl-{num_part}"
    try:
        # Legacy: BL-NNN-*.md im Backlog-Root (case-insensitive)
        for child in backlog_dir.iterdir():
            name_lc = child.name.lower()
            if child.is_file() and name_lc.startswith(prefix_lower) and name_lc.endswith(".md"):
                return child
        # Per-Folder: BL-NNN-*/BL-NNN_*.md
        for child in backlog_dir.iterdir():
            if child.is_dir() and child.name.lower().startswith(prefix_lower):
                for sub in child.iterdir():
                    sub_lc = sub.name.lower()
                    if sub.is_file() and sub_lc.startswith(short_lower) and sub_lc.endswith(".md"):
                        return sub
    except Exception:
        pass
    return Path()


def read_vault_status(bl_id: str) -> str:
    """Liest aktuellen Status aus Vault-BL-Knoten-Frontmatter."""
    path = find_vault_bl_file(bl_id)
    if not path or not path.is_file():
        return ""
    try:
        content = path.read_text(encoding="utf-8")
        return extract_frontmatter_status(content)
    except Exception:
        return ""


def check_index_edit(new_content: str) -> list:
    """Edit auf _backlog_index.md: extrahiere Index-Status pro BL-ID + vergleiche
    gegen Vault-Knoten. Returns Liste von Drift-Strings.
    """
    drifts = []
    new_rows = extract_index_rows(new_content)
    if not new_rows:
        return drifts

    for bl_id, new_status in new_rows.items():
        vault_status = read_vault_status(bl_id)
        if not vault_status:
            # Vault-Knoten existiert nicht oder kein Status-Feld -> passthrough konservativ
            continue
        if vault_status != new_status:
            drifts.append(
                f"{bl_id}: Index='{new_status}' vs Vault-Frontmatter='{vault_status}'"
            )
    return drifts


def check_vault_edit(file_path: str, new_content: str) -> list:
    """Edit auf Vault BL-NNN.md: extrahiere Frontmatter-Status + vergleiche
    gegen _backlog_index.md. Returns Liste von Drift-Strings.
    """
    drifts = []
    bl_id_from_path = match_bl_file(file_path)
    bl_id_from_fm = extract_frontmatter_id(new_content)
    # Path hat Vorrang, Frontmatter als Fallback
    bl_id = bl_id_from_path or bl_id_from_fm
    if not bl_id:
        return drifts

    new_status = extract_frontmatter_status(new_content)
    if not new_status:
        # Kein status-Feld im Diff -> nicht unser Drift (z.B. nur Title-Update)
        return drifts

    index_status = read_index_status(bl_id)
    if not index_status:
        # Index-Zeile fehlt -> passthrough konservativ
        return drifts

    if index_status != new_status:
        drifts.append(
            f"{bl_id}: Vault-Frontmatter='{new_status}' vs Index='{index_status}'"
        )
    return drifts


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

        if tool_name not in ("Edit", "Write"):
            print(json.dumps({"continue": True}))
            return

        if not isinstance(tool_input, dict):
            print(json.dumps({"continue": True}))
            return

        file_path = tool_input.get("file_path", "")
        if not file_path:
            print(json.dumps({"continue": True}))
            return

        # Edit -> new_string, Write -> content
        new_content = tool_input.get("new_string") or tool_input.get("content") or ""
        if not new_content.strip():
            print(json.dumps({"continue": True}))
            return

        # Welche Quelle wurde modifiziert?
        drifts = []
        if is_index_file(file_path):
            drifts = check_index_edit(new_content)
        elif match_bl_file(file_path):
            drifts = check_vault_edit(file_path, new_content)
        else:
            print(json.dumps({"continue": True}))
            return

        if not drifts:
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()
        strict = read_strict_mode()
        block = enforce and strict

        # Log immer
        append_guard_log(file_path, drifts, block)

        drift_str = "; ".join(drifts)
        if block:
            message = (
                f"[GUARD-VIOLATION] STAB7_STATUS_DRIFT [BLOCKED]: {file_path} — "
                f"{drift_str}. _backlog_index.md Status-Spalte und Vault-Knoten "
                f"Frontmatter MUESSEN identisch sein (enforce=true + "
                f"OMNI_STATUS_DRIFT_STRICT=1). "
                f"Fix: synchronisiere beide Quellen in derselben Edit-Sequenz, "
                f"dann setze OMNI_STATUS_DRIFT_STRICT=0 fuer den Sync-Schritt."
            )
            sys.stderr.write(f"[guard_stab7_status_drift BLOCK] {file_path}\n")
            for d in drifts:
                sys.stderr.write(f"  - {d}\n")
            print(json.dumps({"continue": False, "message": message}))
            sys.exit(1)
        else:
            message = (
                f"[GUARD-WARN] STAB7_STATUS_DRIFT: {file_path} — {drift_str}. "
                f"_backlog_index.md Status-Spalte und Vault-Knoten Frontmatter "
                f"stimmen nicht ueberein. Falls dies ein Sync-Edit ist: ignoriere. "
                f"Sonst: synchronisiere beide Quellen. "
                f"(enforce={enforce}, strict={strict} — passthrough)"
            )
            sys.stderr.write(f"[guard_stab7_status_drift WARN] {file_path}\n")
            for d in drifts:
                sys.stderr.write(f"  - {d}\n")
            print(json.dumps({"continue": True, "message": message}))

    except json.JSONDecodeError as e:
        append_debug_log(f"JSONDecodeError: {e}")
        print(json.dumps({"continue": True}))
    except Exception as e:
        append_debug_log(f"Unexpected error: {e}")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
