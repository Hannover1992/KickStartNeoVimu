#!/usr/bin/env python3
"""
guard_geist4_bdf_to_idf.py — Geist G#4 BDF -> IDF (Decomposition-Entry) Pre-Hook

PreToolUse-Hook fuer das Skill-Tool. Triggert wenn Skill(_IDF_orchestrate)
geladen wird. Prueft Pre-Conditions, bevor die IDF-Pipeline startet.

Contract (Geist G#4):
  SOLL: BDF laedt Skill(_IDF_orchestrate); BL ist in einem READY-aequivalenten Status
        (READY, SC-REIF, PLANNED, IN_PROGRESS). Bei `--pl-only --from=sdf_finish`
        muss der per-BL Vault-Folder bereits existieren.
  IST-Drift: IDF kann mit beliebigem BL-Status starten (UNREIF/DRAFT/DONE/FREEZE).
             Kein Pre-IDF-Gate.

Was geblockt wird (enforceProcess=true):
  - BL-Status in {UNREIF, DRAFT}  -> "IDF braucht READY-BL — A-Pipeline zuerst"
  - BL-Status in {DONE, FREEZE, DECOMPOSED} -> "BL bereits terminal"
  - `--pl-only` mit `--from=sdf_finish` aber Vault-Folder fehlt -> Block

enforceProcess=false (Default fuer diesen Hook): NUR Warning (continue=true).

Quelle BL-Status: {vault_root}/_backlog_index.md
Tabellen-Spalte 3 (Status) ist Source-of-Truth, Spalte 4 (Vault-Pfad)
zeigt auf die per-BL Markdown-Datei (Sibling-Folder = per-BL Verzeichnis).

Pattern: guard_modus_writer.py + guard_a_routing_target.py.
Master-Analyse: .claude/output/Enforce_Refactor_Master_Analyse_2026-05-27.md (G#4)
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

# Skill auf den dieser Geist triggert
TARGET_SKILL = "_IDF_orchestrate"

# Status-Kategorien (Source: _backlog_index.md Spalte 3)
READY_STATES = {"READY", "SC-REIF", "PLANNED", "IN_PROGRESS"}
PRE_READY_STATES = {"UNREIF", "DRAFT"}
TERMINAL_STATES = {"DONE", "FREEZE", "DECOMPOSED", "ARCHIVIERT"}

# Regex: BL-Reference in Skill-args
BL_PATTERN = re.compile(r"BL-(\d+)", re.IGNORECASE)

# Regex: --pl-only Flag in Skill-args
PL_ONLY_PATTERN = re.compile(r"--pl-only(?:\b|=|\s)")

# Regex: --from=sdf_finish Flag in Skill-args
FROM_SDF_FINISH_PATTERN = re.compile(r"--from\s*=\s*sdf_finish", re.IGNORECASE)

# Backlog-Index Row-Parser (markdown table)
# Format: | BL-NNN | Title | Status | Vault-Pfad | Created | Updated | Spec-Link | Reifegrad |
BL_INDEX_ROW = re.compile(
    r"^\|\s*BL-(?P<id>\d+)\s*\|"          # BL-ID
    r"\s*(?P<title>[^|]+?)\s*\|"           # Title
    r"\s*(?P<status>[A-Z_\-]+)\s*\|"      # Status
    r"\s*(?P<vault>[^|]+?)\s*\|",          # Vault-Pfad
    re.MULTILINE,
)


def _resolve_vault_root() -> Path:
    """Sucht Vault-Root via resolve_vault_root.py. Fallback: ROOT_DIR."""
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
    """Sucht _session_params.md im Vault-Root, dann lokaler Fallback.

    Test-Override: OMNI_GEIST4_SESSION_PARAMS (Pfad zur Test-Datei).
    """
    override = os.environ.get("OMNI_GEIST4_SESSION_PARAMS")
    if override:
        return Path(override)
    vault_root = _resolve_vault_root()
    candidate = vault_root / "_session_params.md"
    if candidate.exists():
        return candidate
    return ROOT_DIR / ".claude" / "analysis" / "_session_params.md"


def _resolve_backlog_index() -> Path:
    """Sucht _backlog_index.md im Vault-Root, dann lokaler Fallback.

    Test-Override: OMNI_GEIST4_BACKLOG_INDEX (Pfad zur Test-Index-Datei).
    """
    override = os.environ.get("OMNI_GEIST4_BACKLOG_INDEX")
    if override:
        return Path(override)

    vault_root = _resolve_vault_root()
    candidate = vault_root / "_backlog_index.md"
    if candidate.exists():
        return candidate
    return ROOT_DIR / ".claude" / "analysis" / "_backlog_index.md"


SESSION_PARAMS = _resolve_session_params()


def read_enforce_process() -> bool:
    """Liest enforceProcess aus _session_params.md.
    Test-Override: OMNI_ENFORCE_GEIST4_GUARD=1 erzwingt enforce=true.
    Default: False (WARN-Mode) wenn Datei fehlt oder unlesbar.
    """
    if os.environ.get("OMNI_ENFORCE_GEIST4_GUARD") == "1":
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


def append_guard_log(bl_id: str, violations: list, blocked: bool) -> None:
    """Appendet Log-Eintrag in _guard_log.md."""
    try:
        GUARD_LOG.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        action = "BLOCKED" if blocked else "WARNED"
        violation_str = "; ".join(violations)
        entry = (
            f"- [{timestamp}] **GEIST4_BDF_TO_IDF** [{action}]: "
            f"BL-{bl_id} — {violation_str}\n"
        )
        with open(GUARD_LOG, "a", encoding="utf-8") as f:
            f.write(entry)
    except Exception:
        pass


def append_debug_log(msg: str) -> None:
    """Schreibt in .hook_debug.log bei unerwarteten Exceptions."""
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.now()}] guard_geist4_bdf_to_idf: {msg}\n")
    except Exception:
        pass


def extract_bl_id(args: str) -> str | None:
    """Extrahiert die erste BL-NNN Referenz aus Skill-args."""
    if not args:
        return None
    m = BL_PATTERN.search(args)
    if m:
        return m.group(1).zfill(3)  # zero-pad to 3 digits
    return None


def has_pl_only_from_sdf_finish(args: str) -> bool:
    """Prueft ob args sowohl --pl-only als auch --from=sdf_finish enthaelt."""
    if not args:
        return False
    return bool(PL_ONLY_PATTERN.search(args)) and bool(
        FROM_SDF_FINISH_PATTERN.search(args)
    )


def lookup_bl_status_and_vault(bl_id: str) -> tuple[str | None, str | None]:
    """Liest Status (Spalte 3) + Vault-Pfad (Spalte 4) fuer BL-{bl_id} aus
    _backlog_index.md. Returnt (status, vault_path) oder (None, None) wenn
    nicht gefunden.
    """
    index_file = _resolve_backlog_index()
    try:
        if not index_file.exists():
            return None, None
        content = index_file.read_text(encoding="utf-8")
    except Exception:
        return None, None

    bl_id_int = int(bl_id)
    for m in BL_INDEX_ROW.finditer(content):
        try:
            row_id = int(m.group("id"))
        except ValueError:
            continue
        if row_id == bl_id_int:
            status = (m.group("status") or "").strip().upper()
            vault = (m.group("vault") or "").strip()
            return status, vault
    return None, None


def vault_folder_exists(bl_id: str, vault_path_from_index: str | None) -> bool:
    """Prueft ob der per-BL Vault-Folder existiert.

    Erwartetes Layout (BL-NEW-58 Per-BL-Folder-Schema):
      {vault_root}/Backlog/BL-{NNN}-{slug}/

    Wenn _backlog_index.md auf die .md-Datei zeigt, suchen wir den Sibling-
    Folder ohne .md-Suffix.
    """
    candidates: list[Path] = []

    if vault_path_from_index:
        p = Path(vault_path_from_index)
        # Wenn .md-Datei: Sibling-Folder ohne Suffix
        if p.suffix.lower() == ".md":
            candidates.append(p.with_suffix(""))
        elif p.is_dir() or not p.suffix:
            candidates.append(p)
        # Fallback: Sibling-Verzeichnisse mit BL-Prefix
        parent = p.parent
        if parent and str(parent) not in ("", "."):
            candidates.append(parent / f"BL-{bl_id}")
            try:
                for child in parent.iterdir() if parent.exists() else []:
                    if child.is_dir() and child.name.startswith(f"BL-{bl_id}"):
                        candidates.append(child)
            except Exception:
                pass

    # Zusaetzliche Vault-Root Suche
    vault_root = _resolve_vault_root()
    backlog_dir = vault_root / "Backlog"
    if backlog_dir.exists():
        try:
            for child in backlog_dir.iterdir():
                if child.is_dir() and child.name.startswith(f"BL-{bl_id}"):
                    candidates.append(child)
        except Exception:
            pass

    for c in candidates:
        try:
            if c.exists() and c.is_dir():
                return True
        except Exception:
            continue
    return False


def check_idf_preconditions(skill_args: str) -> tuple[list, str | None]:
    """Fuehrt alle G#4-Checks aus.
    Returns: (violations, bl_id_or_None)
    """
    violations: list[str] = []
    bl_id = extract_bl_id(skill_args)

    if not bl_id:
        # Kein BL-ID in args -> Skill-Spezial-Modus (z.B. --resume).
        # Wir lassen das passthrough; das ist ggfs. Job eines anderen Geistes.
        return violations, None

    status, vault_path = lookup_bl_status_and_vault(bl_id)

    if status is None:
        violations.append(
            f"BL-{bl_id} nicht in _backlog_index.md gefunden — "
            f"IDF kann keinen non-existierenden BL dekomponieren."
        )
        return violations, bl_id

    if status in PRE_READY_STATES:
        violations.append(
            f"BL-{bl_id} Status={status} — IDF braucht READY-BL — "
            f"A-Pipeline zuerst (UNREIF/DRAFT brauchen A-Phase 5 Routing nach "
            f"IDF oder direkter READY-Promotion via /_backlog update)."
        )
        return violations, bl_id

    if status in TERMINAL_STATES:
        violations.append(
            f"BL-{bl_id} Status={status} — BL bereits terminal. "
            f"IDF darf nicht erneut auf einen abgeschlossenen/eingefrorenen/"
            f"dekomponierten BL angewendet werden."
        )
        return violations, bl_id

    if status not in READY_STATES:
        # Unbekannter Status - sicherheitshalber blocken
        violations.append(
            f"BL-{bl_id} Status={status} ist nicht in der READY-Whitelist "
            f"{sorted(READY_STATES)}. IDF abgelehnt."
        )
        return violations, bl_id

    # Pl-only --from=sdf_finish Sonderfall: Vault-Folder muss existieren
    if has_pl_only_from_sdf_finish(skill_args):
        if not vault_folder_exists(bl_id, vault_path):
            violations.append(
                f"BL-{bl_id} --pl-only --from=sdf_finish, aber Vault-Folder "
                f"{{vault_root}}/Backlog/BL-{bl_id}-*/ existiert nicht. "
                f"PL-Only Re-Entry braucht persistenten BL-Folder mit "
                f"_manifest.md / Spec / etc."
            )

    return violations, bl_id


def build_block_output(violations: list, bl_id: str | None) -> dict:
    """Erstellt das Hook-Output-Dict fuer Block."""
    violation_str = "; ".join(violations)
    bl_ref = f"BL-{bl_id}" if bl_id else "<unknown BL>"
    message = (
        f"[GEIST4_BDF_TO_IDF BLOCKED] Skill({TARGET_SKILL}) Pre-Check failed "
        f"({bl_ref}): {violation_str}. "
        f"Erlaubte BL-Status fuer IDF: {sorted(READY_STATES)}."
    )
    return {"continue": False, "message": message}


def build_warn_output(violations: list, bl_id: str | None) -> dict:
    """Erstellt das Hook-Output-Dict fuer WARN-Mode (passthrough)."""
    violation_str = "; ".join(violations)
    bl_ref = f"BL-{bl_id}" if bl_id else "<unknown BL>"
    message = (
        f"[GEIST4_BDF_TO_IDF WARN] Skill({TARGET_SKILL}) Pre-Check warned "
        f"({bl_ref}): {violation_str}. enforceProcess=false — passthrough."
    )
    return {"continue": True, "message": message}


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

        # Nur Skill-Tool ist relevant
        if tool_name != "Skill":
            print(json.dumps({"continue": True}))
            return

        if not isinstance(tool_input, dict):
            print(json.dumps({"continue": True}))
            return

        skill = tool_input.get("skill", "")
        # Nur fuer Skill(_IDF_orchestrate) triggern
        if skill != TARGET_SKILL:
            print(json.dumps({"continue": True}))
            return

        skill_args = tool_input.get("args", "") or ""

        violations, bl_id = check_idf_preconditions(skill_args)

        if not violations:
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()

        # Log immer (unabhaengig vom Mode)
        append_guard_log(bl_id or "?", violations, enforce)

        if enforce:
            sys.stderr.write(
                f"[guard_geist4_bdf_to_idf BLOCK] Skill({TARGET_SKILL}) "
                f"BL-{bl_id or '?'}\n"
            )
            for v in violations:
                sys.stderr.write(f"  - {v}\n")
            print(json.dumps(build_block_output(violations, bl_id)))
        else:
            sys.stderr.write(
                f"[guard_geist4_bdf_to_idf WARN] Skill({TARGET_SKILL}) "
                f"BL-{bl_id or '?'}\n"
            )
            for v in violations:
                sys.stderr.write(f"  - {v}\n")
            print(json.dumps(build_warn_output(violations, bl_id)))

    except json.JSONDecodeError as e:
        append_debug_log(f"JSONDecodeError: {e}")
        print(json.dumps({"continue": True}))
    except Exception as e:
        append_debug_log(f"Unexpected error: {e}")
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
