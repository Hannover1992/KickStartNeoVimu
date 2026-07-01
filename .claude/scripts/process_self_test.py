#!/usr/bin/env python3
"""
Process-Self-Test (BL-159 AK-6 PL-6-06 + PL-6-08).

CLI:
  python process_self_test.py synthetic-mega-agent
  python process_self_test.py audit-replay
  python process_self_test.py verify

Exit-Codes:
  0 = ok        — alle Checks bestanden
  1 = warn      — Schwellen schwach (keine harten Fehler, aber Drift-Signale)
  2 = error     — Mega-Agent-Drift erkannt oder ROLLBACK-Schema-Fehler

Bericht wird nach .claude/output/process_self_test_{DATE}.md geschrieben.
"""

import json
import re
import sys
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
AUDIT_FILE = ROOT_DIR / ".claude" / "audit" / "audit.jsonl"
OUTPUT_DIR = ROOT_DIR / ".claude" / "output"

# Pflichtfelder fuer ROLLBACK-Events (INV-ROLL-1)
ROLLBACK_PFLICHTFELDER = {"ts", "event", "tool", "target", "reason", "guard"}

# Mindest-SKILL_LOAD-Schwellen pro Pipeline-Phase (Audit-Replay Plausibilitaet)
PHASE_SCHWELLEN = {
    "SDF": 3,    # mindestens 3 Berater-Loads pro SDF-Round erwartet
    "I": 2,      # mindestens 2 I-Skill-Loads pro I-Phase erwartet
    "SC": 2,     # mindestens 2 SC-Loads pro SC-Zyklus erwartet
    "A": 3,      # mindestens 3 A-Berater-Loads fuer A-Pipeline
}

# Kommandos-Datei-Pfad-Muster fuer Mega-Agent-Erkennung
SKILL_READ_PATTERN = re.compile(
    r"(?:^|[\\/])\.claude[\\/]commands[\\/](_[A-Za-z0-9_]+)\.md$"
)


def _resolve_audit_file() -> Path:
    """Liest Audit-Pfad aus vault-routing.json falls vorhanden."""
    routing_path = SCRIPT_DIR.parent / "config" / "vault-routing.json"
    if routing_path.exists():
        try:
            with open(routing_path, encoding="utf-8") as f:
                routing = json.load(f)
            for rule in routing.get("detection", {}).get("rules", []):
                if "OmniCommand" in rule.get("pattern", ""):
                    psf = rule.get("process_state_files", {})
                    if "manifest" in psf:
                        manifest_path = Path(psf["manifest"])
                        audit_candidate = (
                            manifest_path.parent.parent
                            / ".claude" / "audit" / "audit.jsonl"
                        )
                        if audit_candidate.exists():
                            return audit_candidate
        except Exception:
            pass
    return AUDIT_FILE


def load_audit_events(audit_file: Path) -> list[dict]:
    """Laedt alle validen JSONL-Eintraege aus audit.jsonl."""
    events = []
    if not audit_file.exists():
        return events
    with open(audit_file, encoding="utf-8") as f:
        for line_nr, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass  # korrupte Zeilen werden uebersprungen
    return events


def validate_rollback_schema(event: dict) -> list[str]:
    """Prueft ob ein ROLLBACK-Event alle Pflichtfelder hat. Gibt Fehler-Liste zurueck."""
    fehler = []
    if event.get("event") != "ROLLBACK":
        return fehler  # nicht unser Event
    fehlende = ROLLBACK_PFLICHTFELDER - set(event.keys())
    for feld in sorted(fehlende):
        fehler.append(f"Pflichtfeld fehlt: '{feld}'")
    return fehler


# ---------------------------------------------------------------------------
# Modus 1: synthetic-mega-agent
# ---------------------------------------------------------------------------

def run_synthetic_mega_agent(report_lines: list[str]) -> int:
    """
    Spawnt einen Test-Prozess der guard_skill_load_compliance.py mit einer
    Read-Anfrage auf eine Commands-Datei aufruft — simuliert Mega-Agent.

    Prueft danach ob audit.jsonl ein ROLLBACK-Event mit den Pflichtfeldern enthaelt.
    """
    report_lines.append("## Modus: synthetic-mega-agent")
    report_lines.append("")

    # Test-Eingabe: Read auf .claude/commands/_backlog.md (klassischer Mega-Agent-Versuch)
    test_tool_input = {
        "hook_type": "pre",
        "tool_name": "Read",
        "tool_input": {
            "file_path": str(ROOT_DIR / ".claude" / "commands" / "_backlog.md")
        }
    }
    guard_script = SCRIPT_DIR / "guard_skill_load_compliance.py"

    if not guard_script.exists():
        report_lines.append(f"- FEHLER: Guard-Skript nicht gefunden: {guard_script}")
        return 2

    report_lines.append(f"- Sende synthetischen Read-Aufruf an `{guard_script.name}`")
    report_lines.append(f"- Ziel: `.claude/commands/_backlog.md`")

    audit_events_vorher = load_audit_events(_resolve_audit_file())
    rollback_count_vorher = sum(
        1 for e in audit_events_vorher if e.get("event") == "ROLLBACK"
    )

    try:
        proc = subprocess.run(
            [sys.executable, str(guard_script)],
            input=json.dumps(test_tool_input),
            capture_output=True,
            text=True,
            timeout=10,
        )
        stdout_text = proc.stdout.strip()
        report_lines.append(f"- Guard-Ausgabe: `{stdout_text[:300]}`")

        try:
            response = json.loads(stdout_text)
            guard_blocked = not response.get("continue", True)
        except (json.JSONDecodeError, ValueError):
            guard_blocked = False

        if guard_blocked:
            report_lines.append("- Guard hat **BLOCKIERT** (continue=false) — korrekt")
        else:
            report_lines.append("- WARN: Guard hat NICHT blockiert (enforceProcess=false oder Override)")

    except subprocess.TimeoutExpired:
        report_lines.append("- FEHLER: Guard-Timeout nach 10s")
        return 2
    except Exception as e:
        report_lines.append(f"- FEHLER: Guard-Aufruf fehlgeschlagen: {e}")
        return 2

    # Audit-Events nach Guard-Lauf pruefen
    audit_events_nachher = load_audit_events(_resolve_audit_file())
    rollback_count_nachher = sum(
        1 for e in audit_events_nachher if e.get("event") == "ROLLBACK"
    )
    neue_rollbacks = rollback_count_nachher - rollback_count_vorher

    if neue_rollbacks > 0:
        report_lines.append(
            f"- **ROLLBACK-Event geschrieben** ({neue_rollbacks} neu in audit.jsonl)"
        )
        # Schema-Validierung der neuen Events
        neue_events = audit_events_nachher[len(audit_events_vorher):]
        schema_fehler_gesamt = []
        for evt in neue_events:
            if evt.get("event") == "ROLLBACK":
                schema_fehler = validate_rollback_schema(evt)
                schema_fehler_gesamt.extend(schema_fehler)
        if schema_fehler_gesamt:
            report_lines.append(f"- SCHEMA-FEHLER in ROLLBACK-Event: {schema_fehler_gesamt}")
            return 2
        else:
            report_lines.append("- Schema-Validierung ROLLBACK-Event: **PASS** (alle Pflichtfelder vorhanden)")
            report_lines.append("")
            report_lines.append("**Ergebnis: PASS** — Guard blockiert + ROLLBACK-Event korrekt geschrieben")
            return 0
    else:
        if guard_blocked:
            # Guard hat blockiert aber kein ROLLBACK-Event — Schema-Verletzung
            report_lines.append(
                "- WARN: Guard blockierte, aber kein ROLLBACK-Event in audit.jsonl — "
                "guard_skill_load_compliance.py schreibt noch kein ROLLBACK-Event (PL-6-08 pending)"
            )
            report_lines.append("")
            report_lines.append("**Ergebnis: WARN** — Guard aktiv, ROLLBACK-Persistierung fehlt noch")
            return 1
        else:
            report_lines.append("- ERROR: Kein Guard-Block und kein ROLLBACK-Event")
            report_lines.append("")
            report_lines.append("**Ergebnis: ERROR** — Guard inaktiv oder fehlkonfiguriert")
            return 2


# ---------------------------------------------------------------------------
# Modus 2: audit-replay
# ---------------------------------------------------------------------------

def run_audit_replay(report_lines: list[str]) -> int:
    """
    Liest audit.jsonl, analysiert SKILL_LOAD-Events und ROLLBACK-Events.

    Prueft:
    1. Kein SKILL_LOAD mit load_method="read" (wuerde Mega-Agent-Drift anzeigen)
    2. ROLLBACK-Events haben alle Pflichtfelder (INV-ROLL-1)
    3. SKILL_LOAD-Mindest-Schwellen pro Phase (Plausibilitaets-Check)
    """
    report_lines.append("## Modus: audit-replay")
    report_lines.append("")

    audit_file = _resolve_audit_file()
    if not audit_file.exists():
        report_lines.append(f"- audit.jsonl nicht gefunden: {audit_file}")
        report_lines.append("- WARN: Kein Audit-Log vorhanden (erste Session?)")
        return 1

    events = load_audit_events(audit_file)
    report_lines.append(f"- Geladene Events: {len(events)}")

    # --- SKILL_LOAD-Analyse ---
    skill_load_events = [e for e in events if e.get("event") == "SKILL_LOAD"]
    report_lines.append(f"- SKILL_LOAD-Events gesamt: {len(skill_load_events)}")

    skill_read_violations = [
        e for e in skill_load_events
        if e.get("load_method") == "read"
    ]
    if skill_read_violations:
        report_lines.append(
            f"- **MEGA-AGENT-DRIFT ERKANNT**: {len(skill_read_violations)} SKILL_LOAD via Read:"
        )
        for v in skill_read_violations[:10]:
            report_lines.append(
                f"  - {v.get('ts', '?')} skill={v.get('skill_name', '?')} "
                f"file={v.get('load_method', '?')}"
            )
        if len(skill_read_violations) > 10:
            report_lines.append(f"  ... und {len(skill_read_violations) - 10} weitere")
    else:
        report_lines.append("- Keine SKILL_LOAD-via-Read Violations (kein Mega-Agent-Drift erkannt)")

    # --- Phase-Schwellen-Check ---
    report_lines.append("")
    report_lines.append("### Mindest-Schwellen pro Pipeline-Phase")
    schwellen_verletzt = []
    for phase, schwelle in PHASE_SCHWELLEN.items():
        phase_loads = [
            e for e in skill_load_events
            if e.get("ctx", {}).get("sdf_status") not in (None, "IDLE")
            or phase in ORCHESTRATOR_LEVEL_OF(e.get("skill_name", ""))
        ]
        count = len([
            e for e in skill_load_events
            if ORCHESTRATOR_LEVEL_OF(e.get("skill_name", "")) == phase
        ])
        status = "OK" if count >= schwelle else "SCHWACH"
        report_lines.append(f"- {phase}: {count} Loads (Schwelle: {schwelle}) — {status}")
        if count < schwelle and count > 0:
            schwellen_verletzt.append(phase)

    # --- ROLLBACK-Schema-Validierung ---
    report_lines.append("")
    report_lines.append("### ROLLBACK-Event-Schema-Validierung")
    rollback_events = [e for e in events if e.get("event") == "ROLLBACK"]
    report_lines.append(f"- ROLLBACK-Events gesamt: {len(rollback_events)}")
    schema_fehler_count = 0
    for i, evt in enumerate(rollback_events):
        fehler = validate_rollback_schema(evt)
        if fehler:
            schema_fehler_count += 1
            report_lines.append(
                f"  - Event #{i+1} ({evt.get('ts', '?')}): SCHEMA-FEHLER: {fehler}"
            )
    if schema_fehler_count == 0 and rollback_events:
        report_lines.append("- Schema-Validierung: **PASS** (alle ROLLBACK-Events korrekt)")
    elif schema_fehler_count == 0 and not rollback_events:
        report_lines.append("- Keine ROLLBACK-Events vorhanden (Guard bisher nie ausgeloest)")

    # --- Ergebnis-Bestimmung ---
    report_lines.append("")
    if skill_read_violations or schema_fehler_count > 0:
        report_lines.append(
            f"**Ergebnis: ERROR** — "
            f"{len(skill_read_violations)} Mega-Agent-Violations, "
            f"{schema_fehler_count} Schema-Fehler"
        )
        return 2
    elif schwellen_verletzt:
        report_lines.append(
            f"**Ergebnis: WARN** — Schwellen schwach fuer Phasen: {schwellen_verletzt}"
        )
        return 1
    else:
        report_lines.append("**Ergebnis: PASS** — Kein Mega-Agent-Drift, alle Schema-Checks bestanden")
        return 0


def ORCHESTRATOR_LEVEL_OF(skill_name: str) -> str:
    """Hilfsfunktion: gibt Pipeline-Level eines Skill-Namens zurueck."""
    mapping = {
        "_SDF_": "SDF", "_A_": "A", "_SC_": "SC", "_I_": "I",
        "_TDD_": "I", "_BDF_": "BDF", "_W_": "OBSIDIAN",
        "_WP_": "WP", "_Pre_PR": "POST", "_BL_": "BDF",
    }
    for prefix, level in mapping.items():
        if prefix in skill_name:
            return level
    return "UNKNOWN"


# ---------------------------------------------------------------------------
# Modus 3: verify (kombiniert)
# ---------------------------------------------------------------------------

def run_verify(report_lines: list[str]) -> int:
    """Fuehrt synthetic-mega-agent + audit-replay durch und aggregiert Ergebnis."""
    report_lines.append("## Modus: verify (kombiniert)")
    report_lines.append("")

    exit_1 = run_synthetic_mega_agent(report_lines)
    report_lines.append("")
    exit_2 = run_audit_replay(report_lines)

    gesamt = max(exit_1, exit_2)
    report_lines.append("")
    report_lines.append("---")
    report_lines.append(f"**Gesamt-Ergebnis: {'PASS' if gesamt == 0 else 'WARN' if gesamt == 1 else 'ERROR'}** (exit={gesamt})")
    return gesamt


# ---------------------------------------------------------------------------
# Report-Schreiben
# ---------------------------------------------------------------------------

def write_report(lines: list[str], exit_code: int) -> Path:
    """Schreibt den Bericht nach .claude/output/process_self_test_{DATE}.md."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    datum = datetime.now().strftime("%Y-%m-%d")
    output_file = OUTPUT_DIR / f"process_self_test_{datum}.md"

    header = [
        f"---",
        f"type: process_self_test",
        f"bl_origin: BL-159",
        f"ak_refs: [AK-6]",
        f"generated_at: {datetime.now().isoformat(timespec='seconds')}",
        f"exit_code: {exit_code}",
        f"---",
        "",
        f"# Process-Self-Test Report — {datum}",
        "",
    ]
    content = "\n".join(header + lines) + "\n"
    output_file.write_text(content, encoding="utf-8")
    return output_file


# ---------------------------------------------------------------------------
# Einstiegspunkt
# ---------------------------------------------------------------------------

def main() -> None:
    modi = ["synthetic-mega-agent", "audit-replay", "verify"]

    if len(sys.argv) < 2 or sys.argv[1] not in modi:
        print(f"Verwendung: python process_self_test.py [{' | '.join(modi)}]", file=sys.stderr)
        print("", file=sys.stderr)
        print("  synthetic-mega-agent  — prueft ob Guard bei Read(commands/_*.md) blockiert + ROLLBACK-Event schreibt", file=sys.stderr)
        print("  audit-replay          — validiert audit.jsonl auf Mega-Agent-Drift und ROLLBACK-Schema", file=sys.stderr)
        print("  verify                — kombiniert beide Modi", file=sys.stderr)
        sys.exit(2)

    modus = sys.argv[1]
    report_lines: list[str] = []

    if modus == "synthetic-mega-agent":
        exit_code = run_synthetic_mega_agent(report_lines)
    elif modus == "audit-replay":
        exit_code = run_audit_replay(report_lines)
    else:
        exit_code = run_verify(report_lines)

    output_file = write_report(report_lines, exit_code)
    print(f"Bericht: {output_file}")
    print(f"Exit-Code: {exit_code} ({'ok' if exit_code == 0 else 'warn' if exit_code == 1 else 'error'})")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
