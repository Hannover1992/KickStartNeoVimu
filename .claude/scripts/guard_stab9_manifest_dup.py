#!/usr/bin/env python3
"""
Claude Code Hook — Manifest-Duplicate Guard (Live-Finding F105 2026-05-09, Stab S#9).

PreToolUse-Hook fuer Edit/Write auf _manifest.md / _factory_manifest.md:
  Scannt nach dem Edit/Write den (rekonstruierten) Manifest-Body auf doppelte
  Singleton-Sections und blockiert wenn eine Singleton-Section >1-mal ohne
  Suffix-Disambiguierung vorkommt.

  Singleton-Sections (duerfen nur 1-mal vorkommen ohne Suffix):
    - ## BDF_PIPELINE_STATE
    - ## DF_BATCH_STATE
    - ## FACTORY_STATES
    - ## BL_LIFECYCLE_STATE
    - ## A_PIPELINE_STATE
    - ## IDF_PIPELINE_STATE
    - ## DF_PIPELINE_STATE

  Erlaubte Suffix-Disambiguierungen:
    - ## DF_BATCH_STATE (Round 11)
    - ## DF_BATCH_STATE (Round 12)
    - ## A_PIPELINE_STATE (Round 11)
    - ... d.h. mehrere Round-Varianten koexistieren

  VERBOTEN:
    - 2× `## DF_BATCH_STATE` (ohne Suffix)
    - 1× `## DF_BATCH_STATE` + 1× `## DF_BATCH_STATE` (Duplikate beide ohne Suffix)
    - 2× `## DF_BATCH_STATE (Round 11)` (gleicher Suffix doppelt)

  ERLAUBT:
    - Andere Sections (z.B. `## BERATER_OUTPUTS.foo`) duerfen mehrfach vorkommen
      (kein Singleton)
    - `## DF_BATCH_STATE` + `## DF_BATCH_STATE (Round 11)` koexistiert (unterschiedlich)

Live-Finding F105 (2026-05-09):
  Beobachtet: zwei `## DF_BATCH_STATE`-Sektionen im Manifest. Heute kein Hook
  der das verhindert — guard_modus_writer prueft Felder, nicht Section-Header.

enforceProcess=true (Default): BLOCKIERT (continue=false).
enforceProcess=false: NUR Warning (continue=true).

Test-Override: OMNI_ENFORCE_STAB9_GUARD=1 erzwingt enforce=true (fuer pytest).
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
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# Singleton-Sections (Section-Name ohne Suffix-Bezeichner)
SINGLETON_SECTIONS = [
    "BDF_PIPELINE_STATE",
    "DF_BATCH_STATE",
    "FACTORY_STATES",
    "BL_LIFECYCLE_STATE",
    "A_PIPELINE_STATE",
    "IDF_PIPELINE_STATE",
    "DF_PIPELINE_STATE",
]

# Header-Pattern: `## NAME` optional gefolgt von ` (...)`-Suffix
# Beispiel-Matches:
#   `## DF_BATCH_STATE`                       → name=DF_BATCH_STATE, suffix=""
#   `## DF_BATCH_STATE (Round 11)`            → name=DF_BATCH_STATE, suffix="(Round 11)"
#   `## DF_BATCH_STATE  (Round 12)`           → name=DF_BATCH_STATE, suffix="(Round 12)"
#
# Beachten:
#   `## DF_BATCH_STATE.metric_per_batch`      → NICHT match (Dot-Path = anderes Schema)
#   `## BERATER_OUTPUTS.foo`                  → NICHT match (kein Singleton)
SECTION_HEADER_RE = re.compile(
    r"^(#{2,6})\s+([A-Z][A-Z0-9_]*)(\s*\([^)]*\))?\s*$",
    re.MULTILINE,
)


def _resolve_vault_session_params():
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
                    return Path(vault_root_str) / "_session_params.md"
    except Exception:
        pass
    return ROOT_DIR / ".claude" / "analysis" / "_session_params.md"


SESSION_PARAMS_FILE = _resolve_vault_session_params()


def read_enforce_process():
    """Default true. Override via OMNI_ENFORCE_STAB9_GUARD (Tests)."""
    if os.environ.get("OMNI_ENFORCE_STAB9_GUARD") == "1":
        return True
    if os.environ.get("OMNI_ENFORCE_STAB9_GUARD") == "0":
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


def reconstruct_manifest(file_path: str, tool_name: str, new_content: str, old_string: str) -> str:
    """Rekonstruiert den Manifest-Inhalt NACH dem Edit/Write fuer die Pruefung.

    Write: full content = new_content.
    Edit: Wenn Datei existiert -> Inhalt laden, old_string -> new_string substituieren.
          Wenn Datei nicht existiert -> nur new_string als Approximation.
    """
    if tool_name == "Write":
        return new_content

    # Edit
    fp = Path(file_path)
    if fp.is_file():
        try:
            current = fp.read_text(encoding="utf-8")
            if old_string and old_string in current:
                return current.replace(old_string, new_content, 1)
            # old_string nicht gefunden — Edit wuerde fehlschlagen, aber wir
            # nehmen sicherheitshalber new_content als Approximation
            return current + "\n" + new_content
        except Exception:
            return new_content
    # Datei existiert noch nicht — Edit-Tool wuerde fehlschlagen, aber wir
    # pruefen new_string allein
    return new_content


def find_duplicates(content: str):
    """Scannt content auf doppelte Singleton-Sections.

    Returns:
        List[Tuple[section_name, suffix_str_or_empty, count]] fuer alle Duplikate.
    """
    # Sammle (section_name, suffix_normalized) Tupel
    occurrences = {}  # key=(name, suffix) -> count
    for m in SECTION_HEADER_RE.finditer(content):
        name = m.group(2)
        suffix_raw = (m.group(3) or "").strip()
        # Normalisierte Suffix-Form (Whitespace-stripped)
        suffix_norm = re.sub(r"\s+", " ", suffix_raw).strip()
        key = (name, suffix_norm)
        occurrences[key] = occurrences.get(key, 0) + 1

    duplicates = []
    for (name, suffix), count in occurrences.items():
        if name not in SINGLETON_SECTIONS:
            continue
        # Singleton — darf nur 1-mal je (name, suffix) vorkommen
        if count > 1:
            duplicates.append((name, suffix, count))
    return duplicates


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

        file_path = ""
        new_content = ""
        old_string = ""
        if isinstance(tool_input, dict):
            file_path = tool_input.get("file_path", "")
            if tool_name == "Write":
                new_content = tool_input.get("content", "") or ""
            else:  # Edit
                new_content = tool_input.get("new_string", "") or ""
                old_string = tool_input.get("old_string", "") or ""

        # Trigger nur fuer manifest-Files
        is_manifest = (
            "_manifest.md" in file_path
            or "_factory_manifest.md" in file_path
        )
        if not is_manifest:
            print(json.dumps({"continue": True}))
            return

        # Rekonstruiere Post-Edit-Inhalt
        full_content = reconstruct_manifest(file_path, tool_name, new_content, old_string)
        if not full_content:
            print(json.dumps({"continue": True}))
            return

        duplicates = find_duplicates(full_content)
        if not duplicates:
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()

        # Baue Violation-Beschreibung
        detail_parts = []
        for name, suffix, count in duplicates:
            suffix_disp = f" {suffix}" if suffix else " (ohne Suffix)"
            detail_parts.append(f"{name}{suffix_disp} x{count}")
        details_str = "; ".join(detail_parts)

        # Primaere Section fuer Kurz-Message
        first_name = duplicates[0][0]
        first_suffix = duplicates[0][1] or "(ohne Suffix-Disambiguierung)"
        message = (
            f"[GUARD-VIOLATION] STAB9_MANIFEST_DUP (Live-Finding F105 2026-05-09): "
            f"Duplicate manifest section: {first_name} {first_suffix}. "
            f"Details: {details_str}. "
            f"Singleton-Sections {SINGLETON_SECTIONS} duerfen nur 1-mal vorkommen. "
            f"Mehrere Vorkommen brauchen unterschiedliche Suffix-Disambiguierung "
            f"(z.B. '## DF_BATCH_STATE (Round 11)' + '## DF_BATCH_STATE (Round 12)'). "
            f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
        )

        print(json.dumps({
            "continue": not enforce,
            "message": message,
        }))
        append_guard_log("STAB9_MANIFEST_DUP", details_str, enforce)

    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_stab9_manifest_dup Error: {e}\n")
        except Exception:
            pass
        # Fail-open bei Hook-Fehler — Pipeline darf nicht durch Guard-Bug stehen
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
