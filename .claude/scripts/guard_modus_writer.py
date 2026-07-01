#!/usr/bin/env python3
"""
Claude Code Hook — Modus-Writer Guard (BL-165 AK-5 PL-5-02).

PreToolUse-Hook fuer Edit/Write auf _manifest.md:
  1. Blockiert Writes/Edits die forbidden_keys setzen (recommended_modus,
     sdf_mode, sdf_mode_hint, expected_sdf_mode, mode_recommendation).
  2. Blockiert Writes auf DF_BATCH_STATE.modus wenn kein Whitelist-Marker
     (modus_set_by: _SDF_berater_modusEntscheidung) im neuen Inhalt gesetzt wird.

BL-380 B2/AK-4 (QDSA-Antrieb, INV-MODUS-5-Haertung): Check 1 (forbidden_keys) +
forbidden_value_patterns greifen ZUSAETZLICH auf Nicht-Manifest-Dateien, wenn der
Write eine QDSA-Struktur traegt (quality_goals[]-Block in 1_Task/BL-SLUG_Task.md
oder type: quality_scenario-Node in 2_Model/*.md). Ein quality_goal/quality_scenario
darf KEIN Modus-Feld encoden (kein Naming-Bypass). Die DF_BATCH_STATE-modus-Write-
Pruefung (Check 2/3) bleibt manifest-only, weil taskDefinition den Modus nie schreibt.

BL-382 AK-11 + BL-383 AK-9: dieselbe content-getriggerte Erweiterung gilt fuer
type: adr-Nodes (BL-382) und type: eval_finding-Nodes (BL-383, Eval-Gate-Output) —
verschachtelte Verbotskeys unter adr:/eval_finding: werden gefangen (das Eval-Gate ist
Bewerter/Konsument, KEIN Modus-Setzer).

BL-367 AK-2 (Doktrin-Note mode_recommendation — Option C, Status-Quo):
`mode_recommendation` BLEIBT auf der Verbotsliste (DEFAULT_FORBIDDEN_KEYS) — defensiv
und korrekt, da kein aktiver Schreiber mehr existiert (_A_berater_routing schreibt es
NICHT, 0 grep-Treffer). Kuenftige advisory-Routing-Hints heissen `routing_advisory_hint`
(kein Naming-Conflict mit INV-MODUS-5). Kein Code-Change an Guard oder Skill-Doc.

Schema-Quelle: .claude/config/modus_writer_whitelist.yaml (PL-9-03).
Pattern wie guard_skill_load_compliance.py (BL-159 AK-2).

enforceProcess=true (Default): BLOCKIERT (continue=false)
enforceProcess=false: NUR Warning (continue=true)
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent

WHITELIST_FILE = ROOT_DIR / ".claude" / "config" / "modus_writer_whitelist.yaml"
GUARD_LOG_FILE = ROOT_DIR / ".claude" / "analysis" / "_guard_log.md"
DEBUG_LOG = ROOT_DIR / ".hook_debug.log"

# Defaults wenn YAML nicht ladbar
DEFAULT_ALLOWED_WRITERS = ["_SDF_berater_modusEntscheidung"]
DEFAULT_FORBIDDEN_KEYS = [
    "recommended_modus",
    "sdf_mode",
    "sdf_mode_hint",
    "expected_sdf_mode",
    "mode_recommendation",
]
DEFAULT_FORBIDDEN_VALUE_PATTERNS = [
    r"Empfehlung\s+M[1-9]",
    r"recommend.*M[1-9]",
    r"naechster\s+Modus",
]

# Modus-Felder die nur whitelisted Writers setzen duerfen
# BL-165 AK-5 Original: nur Singular DF_BATCH_STATE.modus
# BL-RCA-486-Round11 2026-05-27: Plural batch_modes ergaenzt (LIVE-BEWEIS Round 11
# Manifest Z5986 — IDF schrieb batch_modes ohne Block, weil Singular-Pattern nicht matched)
MODUS_FIELD_PATTERN = re.compile(
    r"DF_BATCH_STATE\.modus\s*[:=]"     # Singular (BL-165)
    r"|(?:^|\n)\s*batch_modes\s*:"      # Plural (BL-RCA-486-Round11)
    r"|DF_BATCH_STATE\.batch_modes\s*[:=]"
)
MODUS_SET_BY_PATTERN = re.compile(
    r"modus_set_by\s*[:=]\s*[\"']?([A-Za-z_]+)[\"']?"
    r"|batch_modes_set_by\s*[:=]\s*[\"']?([A-Za-z_]+)[\"']?"
)

# BL-380 B2/AK-4 (QDSA-Antrieb, INV-MODUS-5-Haertung):
# Der QDSA-Antrieb erfasst Qualitaetsziele frueh als `quality_goals[]` (taskDefinition
# Phase 0.6, 1_Task/BL-SLUG_Task.md) + `type: quality_scenario`-Nodes (2_Model/*.md).
# Diese Strukturen leben NICHT in _manifest.md, duerfen aber KEIN INV-MODUS-5-Verbotsfeld
# tragen (ein quality_goal darf keinen Modus encoden = kein Naming-Bypass). Wenn der Write
# eine dieser Strukturen traegt, laufen forbidden_keys + forbidden_value_patterns AUCH auf
# Nicht-Manifest-Dateien (content-getriggert, additiv; die modus-Write-Whitelist-Pruefung
# Check 3 bleibt manifest-only, weil taskDefinition DF_BATCH_STATE.modus nie schreibt).
QDSA_STRUCTURE_PATTERN = re.compile(
    r"(?:^|\n)\s*quality_goals\s*:"                                  # quality_goals[]-Block
    r"|(?:\*\*\s*type\s*:\*\*|(?:^|\n)\s*(?:-\s*)?type\s*:)\s*[`\"']?quality_scenario\b",  # quality_scenario-Node
    re.MULTILINE,
)

# BL-382 AK-11 (ADR-Truth-Node, INV-MODUS-5-Haertung): analog der QDSA-Erweiterung.
# Ein `type: adr`-Node (2_Model/*.md) traegt einen verschachtelten `adr:`-Block. Weder der
# Block noch adr.status noch der Materialize-Override duerfen ein INV-MODUS-5-Verbotsfeld
# encoden (kein Naming-Bypass). Der Node lebt NICHT in _manifest.md — darum content-getriggert
# (additiv). Die forbidden_keys-Pruefung (check_forbidden_keys) matcht eingerueckte Keys bereits
# (`(?:^|\n)\s*{key}`), faengt also auch unter `adr:` verschachtelte Verbotskeys.
ADR_STRUCTURE_PATTERN = re.compile(
    r"(?:\*\*\s*type\s*:\*\*|(?:^|\n)\s*(?:-\s*)?type\s*:)\s*[`\"']?adr\b",  # type: adr-Node
    re.MULTILINE,
)

# BL-383 batch_PL1 (AK-9 / Eval-Gate, INV-MODUS-5-Haertung): analog der QDSA-/ADR-Erweiterung.
# Ein `type: eval_finding`-Node (2_Model/*.md o.ae.) traegt einen verschachtelten
# `eval_finding:`-Block. Das Eval-Gate ist Bewertungs-KONSUMENT, KEIN Modus-Setzer — weder der
# Record noch ein abgeleitetes GO/NO-GO-Feld duerfen ein INV-MODUS-5-Verbotsfeld encoden (kein
# Naming-Bypass). Der Node lebt NICHT in _manifest.md — darum content-getriggert (additiv). Die
# forbidden_keys-Pruefung (check_forbidden_keys) matcht eingerueckte Keys bereits
# (`(?:^|\n)\s*(?:-\s*)?{key}`), faengt also auch unter `eval_finding:` verschachtelte Verbotskeys.
EVAL_FINDING_STRUCTURE_PATTERN = re.compile(
    r"(?:\*\*\s*type\s*:\*\*|(?:^|\n)\s*(?:-\s*)?type\s*:)\s*[`\"']?eval_finding\b",  # type: eval_finding-Node
    re.MULTILINE,
)


def load_whitelist():
    if HAS_YAML and WHITELIST_FILE.exists():
        try:
            with open(WHITELIST_FILE, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if isinstance(data, dict):
                return {
                    "allowed_writers": data.get("allowed_writers_for_modus_field", DEFAULT_ALLOWED_WRITERS),
                    "forbidden_keys": data.get("forbidden_keys", DEFAULT_FORBIDDEN_KEYS),
                    "forbidden_value_patterns": data.get("forbidden_value_patterns", DEFAULT_FORBIDDEN_VALUE_PATTERNS),
                }
        except Exception:
            pass
    return {
        "allowed_writers": DEFAULT_ALLOWED_WRITERS,
        "forbidden_keys": DEFAULT_FORBIDDEN_KEYS,
        "forbidden_value_patterns": DEFAULT_FORBIDDEN_VALUE_PATTERNS,
    }


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
    # Test-Override: OMNI_ENFORCE_MODUS_GUARD=1 erzwingt enforce=true (fuer pytest)
    import os
    if os.environ.get("OMNI_ENFORCE_MODUS_GUARD") == "1":
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


def check_forbidden_keys(content, forbidden_keys):
    """Gibt Liste der gefundenen forbidden_keys zurueck.

    BL-382 AK-11: matcht den Key auch als VERSCHACHTELTEN YAML-Listen-Eintrag
    (optionaler '- '-Dash nach Einrueckung) — sonst rutscht ein Verbotskey unter einem
    `adr:`-Listen-Block (`    - sdf_mode: heavy`) durch (analog _key_present im Validator)."""
    found = []
    for key in forbidden_keys:
        # Match key als YAML/Markdown-Feld: key: oder key = — bare ODER Listen-Dash-Eintrag.
        pattern = re.compile(rf"(?:^|\n)\s*(?:-\s*)?{re.escape(key)}\s*[:=]", re.MULTILINE)
        if pattern.search(content):
            found.append(key)
    return found


def check_forbidden_value_patterns(content, patterns):
    """Gibt Liste der matchenden forbidden_value_patterns zurueck."""
    found = []
    for pat in patterns:
        try:
            if re.search(pat, content):
                found.append(pat)
        except re.error:
            pass
    return found


def check_modus_write_whitelisted(content, allowed_writers):
    """
    Falls content auf DF_BATCH_STATE.modus ODER batch_modes schreibt:
    pruefe ob modus_set_by / batch_modes_set_by in allowed_writers vorkommt.
    Gibt (writes_modus, is_whitelisted) zurueck.

    BL-RCA-486-Round11 (2026-05-27): batch_modes (plural) jetzt auch geblockt.
    """
    writes_modus = bool(MODUS_FIELD_PATTERN.search(content))
    if not writes_modus:
        return False, True  # kein Modus-Write → kein Problem

    m = MODUS_SET_BY_PATTERN.search(content)
    if m:
        # Group 1 = modus_set_by, Group 2 = batch_modes_set_by
        writer = (m.group(1) or m.group(2) or "").strip()
        return True, writer in allowed_writers
    # modus_set_by / batch_modes_set_by fehlt komplett
    return True, False


def has_qdsa_structure(content):
    """BL-380 B2/AK-4 + BL-382 AK-11 + BL-383 AK-9: True, wenn der Write eine Truth-Node-/
    Eval-Gate-Struktur traegt, die auch ausserhalb von _manifest.md auf INV-MODUS-5-
    Verbotsfelder geprueft werden muss:
      - QDSA: quality_goals[]-Block ODER type: quality_scenario-Node (BL-380), ODER
      - ADR:  type: adr-Node mit verschachteltem adr:-Block (BL-382), ODER
      - EVAL-GATE: type: eval_finding-Node mit verschachteltem eval_finding:-Block (BL-383).
    Content-getriggert, dateiname-unabhaengig, additiv (kein Naming-Bypass via Subtyp-Node)."""
    return (
        bool(QDSA_STRUCTURE_PATTERN.search(content))
        or bool(ADR_STRUCTURE_PATTERN.search(content))
        or bool(EVAL_FINDING_STRUCTURE_PATTERN.search(content))
    )


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
            # Edit: new_string; Write: content
            new_content = tool_input.get("new_string", "") or tool_input.get("content", "")

        # Gating: _manifest.md (BL-165 AK-5) ODER Truth-Node-Struktur (BL-380 B2/AK-4 QDSA +
        # BL-382 AK-11 ADR). QDSA (quality_goals[] / quality_scenario) bzw. type:adr-Nodes leben
        # in Task-/Model-Dateien, nicht im Manifest — werden aber auf INV-MODUS-5-Verbotsfelder
        # geprueft (kein Naming-Bypass via verschachteltem Subtyp-Block).
        is_manifest = bool(file_path) and "_manifest.md" in file_path
        is_qdsa = bool(file_path) and has_qdsa_structure(new_content)
        if not (is_manifest or is_qdsa):
            print(json.dumps({"continue": True}))
            return

        whitelist = load_whitelist()
        forbidden_keys = whitelist["forbidden_keys"]
        forbidden_patterns = whitelist["forbidden_value_patterns"]
        allowed_writers = whitelist["allowed_writers"]

        enforce = read_enforce_process()
        violations = []

        # Check 1: forbidden_keys
        found_keys = check_forbidden_keys(new_content, forbidden_keys)
        if found_keys:
            violations.append(f"forbidden_keys gefunden: {found_keys}")

        # Check 2: forbidden_value_patterns
        found_patterns = check_forbidden_value_patterns(new_content, forbidden_patterns)
        if found_patterns:
            violations.append(f"forbidden_value_patterns gefunden: {found_patterns}")

        # Check 3: modus-write ohne Whitelist-Marker (Singular + Plural) — NUR _manifest.md.
        # BL-RCA-486-Round11: batch_modes auch geblockt.
        # BL-380 B2/AK-4: DF_BATCH_STATE.modus/batch_modes ist Manifest-State; taskDefinition
        # (QDSA-Produzent) schreibt es nie. Fuer reine QDSA-Dateien (Task/Model ohne Manifest)
        # ist diese Manifest-State-Pruefung nicht zustaendig — INV-MODUS-5 wird dort allein
        # ueber forbidden_keys/forbidden_value_patterns (Check 1+2) erzwungen.
        if is_manifest:
            writes_modus, is_whitelisted = check_modus_write_whitelisted(new_content, allowed_writers)
            if writes_modus and not is_whitelisted:
                violations.append(
                    "DF_BATCH_STATE.modus oder batch_modes-Write ohne gueltigen "
                    f"modus_set_by/batch_modes_set_by-Marker (erlaubt: {allowed_writers})"
                )

        if not violations:
            print(json.dumps({"continue": True}))
            return

        violation_str = "; ".join(violations)
        message = (
            f"[GUARD-VIOLATION] MODUS_WRITER_GUARD (BL-165 AK-5, INV-MODUS-1): "
            f"{violation_str}. "
            f"DF_BATCH_STATE.modus darf NUR von _SDF_berater_modusEntscheidung gesetzt werden. "
            f"Forbidden-Keys (recommended_modus, sdf_mode, sdf_mode_hint, expected_sdf_mode, "
            f"mode_recommendation) sind in allen Skills verboten. "
            f"{'BLOCKIERT (enforceProcess=true).' if enforce else 'WARNING (enforceProcess=false).'}"
        )
        print(json.dumps({
            "continue": not enforce,
            "message": message,
        }))
        append_guard_log("MODUS_WRITER_VIOLATION", violation_str, enforce)

    except Exception as e:
        try:
            with open(DEBUG_LOG, "a", encoding="utf-8") as log:
                log.write(f"[{datetime.now()}] guard_modus_writer Error: {e}\n")
        except Exception:
            pass
        print(json.dumps({"continue": True}))


if __name__ == "__main__":
    main()
