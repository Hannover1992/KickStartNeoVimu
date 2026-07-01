#!/usr/bin/env python3
"""
Claude Code Hook — Berater-Output Provenance Guard (RCA DCSRE-486 Round 11, Stab S#1).

PreToolUse-Hook fuer Edit/Write auf _manifest.md / _factory_manifest.md:
  Jeder NEUE `## BERATER_OUTPUTS.{name}` oder `## BERATER_OUTPUTS_*.{name}`-Block
  MUSS Provenance-Felder enthalten:
    - set_by:     (Skill-Name beginnend mit `_`)
    - exit_code:  (Zahl 0-2)
    - ts:         (ISO-Timestamp / Datum)

  Optional aber empfohlen:
    - worker_id:
    - provenance_round:

RCA-Hintergrund (DCSRE-486 Round 11 Layer L3 + L7 + F9/F10):
  - Skills sind Spec-only, kein Enforcement.
  - BERATER_OUTPUTS-Bloecke werden vom Lead inline geschrieben ohne Provenance.
  - Folge: Audit-Trail-Inversion — Manifest hat Werte, niemand weiss wer geschrieben hat.
  - Phantom-DONEs erlauben (siehe modusEntscheidung_round11 Mega-Worker-Bypass).

Edge-Cases:
  - Write-Tool: Vollstaendiger Inhalt — alle Bloecke werden geprueft.
  - Edit-Tool: Nur new_string wird geprueft. Wenn ein bereits-existierender Block
    (im old_string vorhanden) ohne Provenance ist, wird er NICHT erneut geblockt —
    nur was NEU dazukommt (Block in new_string aber nicht in old_string).

enforceProcess=true (Default): BLOCKIERT (continue=false).
enforceProcess=false: NUR Warning (continue=true).

Test-Override: OMNI_ENFORCE_STAB1_GUARD=1 erzwingt enforce=true (fuer pytest).
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

# Erfasse alle BERATER_OUTPUTS-Header-Varianten:
#   ## BERATER_OUTPUTS.modusEntscheidung
#   ## BERATER_OUTPUTS.modusEntscheidung_round11
#   ## BERATER_OUTPUTS_IDF.plAggregation_round11
#   ## BERATER_OUTPUTS_FE.i_round1_stage7
# Header-Pattern: '##' (1-6 #), 'BERATER_OUTPUTS' optional '_SUFFIX', '.', name
BERATER_HEADER_RE = re.compile(
    r"^(#{2,6})\s+BERATER_OUTPUTS(?:_[A-Za-z0-9]+)?\.([A-Za-z0-9_]+)\s*$",
    re.MULTILINE,
)

# Pflicht-Provenance-Felder (mit YAML-ish Match)
SET_BY_RE = re.compile(r"(?m)^\s*set_by\s*[:=]\s*[\"']?(_[A-Za-z0-9_]+)[\"']?")
EXIT_CODE_RE = re.compile(r"(?m)^\s*exit_code\s*[:=]\s*[\"']?([0-9])[\"']?")
# ts: 2026-05-27 oder 2026-05-27T13:45:12 oder "2026-05-27 13:45"
TS_RE = re.compile(r"(?m)^\s*ts\s*[:=]\s*[\"']?(\d{4}-\d{2}-\d{2}[T\s0-9:Z+.-]*)[\"']?")


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
    """Default true. Override via OMNI_ENFORCE_STAB1_GUARD=1 (Tests)."""
    if os.environ.get("OMNI_ENFORCE_STAB1_GUARD") == "1":
        return True
    if os.environ.get("OMNI_ENFORCE_STAB1_GUARD") == "0":
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


def extract_blocks(content: str):
    """Zerlegt Inhalt in (header_full, block_name, block_body)-Tupel.

    block_body = Alles nach dem Header bis zum naechsten Header der gleichen oder
    hoeheren Ebene ODER bis zum naechsten BERATER_OUTPUTS-Header.

    Wir nutzen eine einfache Heuristik: ein Block geht bis zum naechsten Header
    der mit `## ` oder `### ` beginnt UND nicht einer Block-Fortsetzung gehoert
    (unwichtig fuer Provenance-Check: 4-6 Zeilen reichen). Fuer Robustheit nehmen
    wir den Body bis zum naechsten `^#{1,6} ` Header.
    """
    blocks = []
    matches = list(BERATER_HEADER_RE.finditer(content))
    for i, m in enumerate(matches):
        header_full = m.group(0)
        name = m.group(2)
        start = m.end()
        # Suche naechsten Header (egal welche Ebene) AB start
        next_header = re.search(r"(?m)^#{1,6}\s+\S", content[start:])
        if next_header:
            end = start + next_header.start()
        else:
            end = len(content)
        body = content[start:end]
        blocks.append((header_full, name, body))
    return blocks


def check_provenance(body: str):
    """Gibt Liste fehlender Pflicht-Felder zurueck. Leer = OK."""
    missing = []
    if not SET_BY_RE.search(body):
        missing.append("set_by")
    if not EXIT_CODE_RE.search(body):
        missing.append("exit_code")
    if not TS_RE.search(body):
        missing.append("ts")
    return missing


def old_block_names(old_string: str):
    """Gibt Namen aller BERATER_OUTPUTS-Bloecke aus dem alten Inhalt zurueck.

    Dient als Filter: nur NEUE Bloecke (Name nicht in alt-Liste) werden geprueft.
    """
    if not old_string:
        return set()
    return {m.group(2) for m in BERATER_HEADER_RE.finditer(old_string)}


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
                # Bei Write existiert die Datei evtl. — wir koennten sie lesen,
                # aber per Spec: Write ueberschreibt. Alle Bloecke gelten als NEU.
                old_string = ""
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

        if not new_content:
            print(json.dumps({"continue": True}))
            return

        # Sammle NEUE BERATER_OUTPUTS-Bloecke (nicht im old_string vorhanden)
        existing_names = old_block_names(old_string)
        new_blocks = extract_blocks(new_content)

        violations = []
        for header_full, name, body in new_blocks:
            if name in existing_names:
                # Block war schon da — wir pruefen ihn NICHT erneut
                continue

            missing = check_provenance(body)
            if missing:
                # set_by zusaetzlich validieren falls vorhanden: muss mit _ beginnen
                set_by_match = SET_BY_RE.search(body)
                if set_by_match and not set_by_match.group(1).startswith("_"):
                    missing.append("set_by_invalid (kein '_'-prefix)")

                violations.append({
                    "block": header_full.strip(),
                    "name": name,
                    "missing": missing,
                })

        # Zusatzcheck: set_by vorhanden aber nicht mit _ → auch Violation
        # (auch wenn missing leer war, weil SET_BY_RE nur _-prefix matched — kein
        #  Extra-Check noetig. SET_BY_RE matched bewusst nur Skill-Namen mit _).

        if not violations:
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()

        # Bauen Violation-Beschreibung
        details_lines = []
        for v in violations:
            details_lines.append(
                f"  - {v['block']} (name={v['name']}): missing {v['missing']}"
            )
        details_str = "\n".join(details_lines)

        message = (
            f"[GUARD-VIOLATION] STAB1_BERATER_PROVENANCE (RCA-486-Round11 Layer L3+L7): "
            f"{len(violations)} neue BERATER_OUTPUTS-Block(s) ohne Pflicht-Provenance "
            f"in {Path(file_path).name}. "
            f"Pflicht-Felder: set_by (Skill mit '_'-prefix), exit_code (0-2), ts (ISO). "
            f"Details:\n{details_str}\n"
            f"Hintergrund: Skills schreiben BERATER_OUTPUTS-Bloecke. Lead darf NICHT "
            f"inline schreiben ohne Provenance — sonst sind Audits unmoeglich und "
            f"Phantom-DONEs entstehen (siehe DCSRE-486 Round 11 modusEntscheidung-Bypass). "
            f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
        )

        print(json.dumps({
            "continue": not enforce,
            "message": message,
        }))
        append_guard_log(
            "STAB1_BERATER_PROVENANCE",
            f"{len(violations)} block(s) ohne Provenance: "
            + "; ".join(f"{v['name']}={v['missing']}" for v in violations),
            enforce,
        )

    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_stab1_berater_provenance Error: {e}\n")
        except Exception:
            pass
        # Fail-open bei Hook-Fehler — Pipeline darf nicht durch Guard-Bug stehen
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
