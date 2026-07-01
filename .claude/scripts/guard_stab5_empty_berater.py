#!/usr/bin/env python3
"""
Claude Code Hook — Stab S#5 Empty-Berater Guard
(Phantom-DONE-Detector fuer BERATER_OUTPUTS-Bloecke)

PreToolUse-Hook fuer Edit/Write auf _manifest.md (BL/Factory/Backlog-Index).

Hintergrund:
  DCSRE-486 Round 11 Korrekturlauf: BERATER_OUTPUTS-Bloecke wurden mit
  exit_code=0 geschrieben, aber der Block enthielt nur set_by/exit_code/ts —
  KEIN Inhalt. Das ist "Validating-Only Drift": Status sagt DONE, der Berater
  hat aber faktisch keine Arbeit geleistet (F9 Sanity-Report).

Vertrag (S#5):
  Jeder NEUE BERATER_OUTPUTS.{name}- (oder BERATER_OUTPUTS_*.{name})-Block mit
    exit_code: 0
  MUSS substantielles Content haben:
    * mindestens 3 nicht-leere Datenzeilen NACH den Provenance-Headern
      (set_by, exit_code, ts, schema_version)
    * ODER ein explizites empty_reason / skip_reason-Feld als Begruendung
      fuer einen legitimen Leer-Output

Sonderfaelle:
  exit_code != 0 (Fail/Skip):  Berater darf Content leer lassen
  empty_reason / skip_reason gesetzt:  legitimer Skip mit Begruendung -> OK
  Edit auf andere Datei (kein _manifest.md):  passthrough

enforceProcess=true (Default): BLOCKIERT (continue=false)
enforceProcess=false: NUR Warning (continue=true)

Style-Quelle: guard_modus_writer.py (BL-165 AK-5).
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


# ───── Session-Param Resolver (analog guard_modus_writer.py) ─────


def _resolve_vault_session_params():
    try:
        import subprocess

        resolver = SCRIPT_DIR / "resolve_vault_root.py"
        if resolver.is_file():
            proc = subprocess.run(
                [sys.executable, str(resolver)],
                capture_output=True,
                text=True,
                timeout=5,
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
    """OMNI_ENFORCE_STAB5=1 erzwingt enforce=true (fuer pytest)."""
    if os.environ.get("OMNI_ENFORCE_STAB5") == "1":
        return True
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


# ───── BERATER_OUTPUTS Block-Parser ─────

# Erkennt Block-Header der Form:
#   BERATER_OUTPUTS.foo_round11:
#   BERATER_OUTPUTS_IDF.bar_round12:
#   BERATER_OUTPUTS_FE.baz:
# Header darf YAML-style (Doppelpunkt) ODER Markdown-Heading sein:
#   ## BERATER_OUTPUTS.foo_round11
BERATER_BLOCK_HEADER = re.compile(
    r"(?:^|\n)"
    r"(?:#+\s+|\s*)"
    r"(BERATER_OUTPUTS(?:_[A-Za-z0-9]+)?\.[A-Za-z0-9_]+)"
    r"\s*:?\s*(?:\n|$)"
)

# Provenance-Header-Felder (zaehlen NICHT als Content)
PROVENANCE_KEYS = frozenset(
    {
        "set_by",
        "exit_code",
        "ts",
        "timestamp",
        "schema_version",
        "round",
        "round_id",
        "batch",
        "batch_id",
        "phase",
    }
)

# Legitime Leer-Begruendungs-Felder
EMPTY_REASON_KEYS = frozenset(
    {
        "empty_reason",
        "skip_reason",
        "noop_reason",
    }
)

# exit_code: 0 Pattern (YAML / Markdown)
EXIT_CODE_PATTERN = re.compile(
    r"^\s*[-*]?\s*exit_code\s*[:=]\s*(\d+)",
    re.MULTILINE,
)


def _split_block_body(text):
    """Liefert (header_lines, content_lines) eines Block-Bodys.

    Provenance-Lines (set_by/exit_code/ts/...) wandern in header_lines,
    der Rest in content_lines. Leerzeilen werden uebersprungen.
    """
    header_lines = []
    content_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        # YAML-Block-Header (BERATER_OUTPUTS.foo:) ignorieren
        if BERATER_BLOCK_HEADER.match("\n" + raw_line):
            continue
        # Markdown-Heading ignorieren
        if line.startswith("#"):
            continue
        # Provenance-Key?
        m = re.match(r"^[-*]?\s*([a-z_]+)\s*[:=]", line)
        if m and m.group(1) in PROVENANCE_KEYS:
            header_lines.append(line)
            continue
        content_lines.append(line)
    return header_lines, content_lines


def _extract_blocks(content):
    """Extrahiert alle BERATER_OUTPUTS-Bloecke aus content.

    Block-Ende: naechster BERATER_OUTPUTS-Header, naechstes Top-Level-YAML-Key
    (Pattern ^[A-Z_]+:) oder Ende des Textes.
    """
    blocks = []
    matches = list(BERATER_BLOCK_HEADER.finditer(content))
    for i, m in enumerate(matches):
        block_name = m.group(1)
        body_start = m.end()
        if i + 1 < len(matches):
            body_end = matches[i + 1].start()
        else:
            # Suche naechsten Top-Level-Key (DF_BATCH_STATE:, POST_SDF_*: etc.)
            tail = content[body_start:]
            next_top = re.search(
                r"\n(?:#+\s+)?[A-Z][A-Z0-9_]{3,}\s*:",
                tail,
            )
            body_end = body_start + (next_top.start() if next_top else len(tail))
        body = content[body_start:body_end]
        blocks.append((block_name, body))
    return blocks


def _is_phantom_block(body):
    """True wenn block exit_code=0 hat aber keinen substantiellen Content.

    Regeln:
      - exit_code != 0  -> kein Phantom (Fail/Skip ist OK ohne Content)
      - exit_code = 0 + empty_reason / skip_reason gesetzt  -> OK
      - exit_code = 0 + mind. 3 Datenzeilen Content  -> OK
      - sonst  -> Phantom-Verdacht
    """
    # exit_code extrahieren
    ec_match = EXIT_CODE_PATTERN.search(body)
    if not ec_match:
        # Kein exit_code -> nicht beurteilbar, lass passieren
        return False, "kein_exit_code"

    exit_code = int(ec_match.group(1))
    if exit_code != 0:
        return False, f"exit_code={exit_code}_fail_oder_skip"

    # empty_reason / skip_reason vorhanden?
    for key in EMPTY_REASON_KEYS:
        # Match key in Body als YAML/Markdown-Feld
        pattern = re.compile(
            rf"(?:^|\n)\s*[-*]?\s*{re.escape(key)}\s*[:=]\s*\S",
            re.MULTILINE,
        )
        if pattern.search(body):
            return False, f"legitimer_skip_via_{key}"

    # Content-Zeilen zaehlen
    _, content_lines = _split_block_body(body)
    if len(content_lines) >= 3:
        return False, f"content_lines={len(content_lines)}"

    return True, f"content_lines={len(content_lines)}_kein_empty_reason"


# ───── Hook Main ─────


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
        if isinstance(tool_input, dict):
            file_path = tool_input.get("file_path", "")
            new_content = tool_input.get("new_string", "") or tool_input.get(
                "content", ""
            )

        # Triggert nur bei Manifest-Edits
        if not file_path or "_manifest.md" not in file_path:
            print(json.dumps({"continue": True}))
            return

        if not new_content:
            print(json.dumps({"continue": True}))
            return

        # Extrahiere alle BERATER_OUTPUTS-Bloecke aus new_content
        blocks = _extract_blocks(new_content)
        if not blocks:
            print(json.dumps({"continue": True}))
            return

        enforce = read_enforce_process()
        phantom_blocks = []
        for block_name, body in blocks:
            is_phantom, reason = _is_phantom_block(body)
            if is_phantom:
                phantom_blocks.append((block_name, reason))

        if not phantom_blocks:
            print(json.dumps({"continue": True}))
            return

        details = "; ".join(
            f"{name} ({reason})" for name, reason in phantom_blocks
        )
        message = (
            f"[GUARD-VIOLATION] STAB_S5_EMPTY_BERATER (Phantom-DONE-Pattern, "
            f"DCSRE-486 Round 11 F9): "
            f"Phantom-Output erkannt — exit_code=0 aber kein Content + kein "
            f"empty_reason/skip_reason: {details}. "
            f"Berater-Outputs mit exit_code:0 MUESSEN mindestens 3 Datenzeilen "
            f"Content liefern, oder ein explizites empty_reason/skip_reason "
            f"setzen. "
            f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
        )
        print(
            json.dumps(
                {
                    "continue": not enforce,
                    "message": message,
                }
            )
        )
        append_guard_log("STAB5_PHANTOM_BERATER", details, enforce)

    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(
                    f"[{datetime.now()}] guard_stab5_empty_berater Error: {e}\n"
                )
        except Exception:
            pass
        # Bei Crash: passthrough (no-fail-policy fuer Hooks)
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
