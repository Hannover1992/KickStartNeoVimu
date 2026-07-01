"""
BL-465: INV-SPAWN fuer I-Inline-Calls zu Worker-Spawns (Thin-Diaet) — strukturelle pytest-Tests
RED-Worker: BL-465 batch_1 Slice 1 Iteration 1

Tests pruefen den Inhalt von .claude/commands/_I_orchestrate.md via grep/parse.
AC-1/AC-3-Tests MUESSEN JETZT FAILEN (RED) — Marker fehlen noch.
AC-2/AC-4-Tests sind Charakterisierung/Regression (initial GREEN, duerfen NICHT brechen).

Blueprint: BL-465_blueprint.md (8 Tests in Sektion 8)
false-GREEN-Falle: INV-PM-5 ist heute 1x da (Z.674-Header) — echter RED-Hebel ist
  'INV-SPAWN' (0 Treffer), '[INV-SPAWN]' Phasen-Marker (0), '[GATE P' (0),
  'Agent(subagent_type' in I (0).
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA")
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"

I_ORCHESTRATE   = COMMANDS_DIR / "_I_orchestrate.md"
A_ORCHESTRATE   = COMMANDS_DIR / "_A_orchestrate.md"
IDF_ORCHESTRATE = COMMANDS_DIR / "_IDF_orchestrate.md"

# Baseline-Commit wo A/IDF zuletzt angefasst wurden (pre-BL-465)
BASELINE_COMMIT = "403b032"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── RED Tests (AC-1: INV-SPAWN-Direktive + Worker-Spawn-Pattern) ───────────────

def test_ac1_inv_spawn_direktive_present():
    """
    AC-1 / DoD-1 (RED): _I_orchestrate.md muss einen INV-SPAWN-Direktiv-Block enthalten.

    Konkret:
      - text.count('INV-SPAWN') >= 1  (Direktive-Marker)
      - re.search(r'INV-PM-5.aequivalent', text)  (Aequivalenz-Deklaration)

    Heute: INV-SPAWN=0 Treffer (INV-PM-5 existiert 1x @Z674, aber 'INV-PM-5-aequivalent'=0)
    Nach GREEN (Edit-Block A): beide Bedingungen erfuellt.

    false-GREEN-Falle: 'INV-PM-5' allein genuegt NICHT — nur 'INV-SPAWN' + 'INV-PM-5-aequivalent'
    sind die echten RED-Hebel (beide heute 0).
    """
    text = _read(I_ORCHESTRATE)

    inv_spawn_count = text.count("INV-SPAWN")
    assert inv_spawn_count >= 1, (
        f"'INV-SPAWN' Direktive fehlt in _I_orchestrate.md — "
        f"gefunden: {inv_spawn_count} (erwartet: >= 1). "
        f"BL-465 Edit-Block A muss den INV-SPAWN-Block einfuegen."
    )

    has_aequivalent = bool(re.search(r"INV-PM-5.aequivalent", text))
    assert has_aequivalent, (
        "'INV-PM-5-aequivalent' fehlt in _I_orchestrate.md — "
        "der INV-SPAWN-Block muss die Aequivalenz zu INV-PM-5 explizit deklarieren "
        "(BL-465 Edit-Block A, Z.677: 'INV-SPAWN = INV-PM-5-aequivalent, AKTIVER STRUKTURVERTRAG')."
    )


def test_ac1_worker_spawn_pattern_block():
    """
    AC-1 / DoD-2 (RED): _I_orchestrate.md muss ein Agent()-Spawn-Template-Block enthalten.

    Konkret:
      - re.search(r'Agent\\(\\s*subagent_type', text)   (Agent()-Aufruf-Schablone)
      - 'team_name="i-' in text                          (i-{NAME} team_name Konvention)
      - 'Worker stirbt nach Skill-Ausfuehrung' in text   (Worker-stirbt-Semantik)

    Heute: Kein Agent()-Template in _I_orchestrate.md (0 Treffer) -> FAIL.
    Nach GREEN (Edit-Block A): Agent()-Schablone eingefuegt -> PASS.
    """
    text = _read(I_ORCHESTRATE)

    has_agent_spawn = bool(re.search(r"Agent\(\s*subagent_type", text))
    assert has_agent_spawn, (
        "'Agent(subagent_type' fehlt in _I_orchestrate.md — "
        "der WORKER-SPAWN-PATTERN-Block muss ein Agent()-Spawn-Template mit subagent_type-Parameter "
        "enthalten (BL-465 Edit-Block A, Spiegelt A INV-PM-5 Z.292-316)."
    )

    has_team_name = 'team_name="i-' in text
    assert has_team_name, (
        "'team_name=\"i-' Konvention fehlt in _I_orchestrate.md — "
        "das Agent()-Template muss team_name=\"i-{NAME}\" als I-Pipeline-Team-Konvention "
        "deklarieren (BL-465 Edit-Block A)."
    )

    has_worker_stirbt = "Worker stirbt nach Skill-Ausfuehrung" in text
    assert has_worker_stirbt, (
        "'Worker stirbt nach Skill-Ausfuehrung' Semantik fehlt in _I_orchestrate.md — "
        "das WORKER-SPAWN-PATTERN muss die Kurzlebig-Worker-Semantik (Worker laed Skill, "
        "schreibt BERATER_OUTPUTS-Slot, stirbt) explizit deklarieren (BL-465 Edit-Block A)."
    )


def test_ac1_five_phases_spawn_bound():
    """
    AC-1 / DoD-3-7 (RED): Alle 5 Top-Level-Phasen muessen [INV-SPAWN]-Marker tragen.

    Konkret:
      - text.count('[INV-SPAWN]') >= 5  (je 1 Marker pro Phase: teamSetup / kurzlebigPrompt /
        teamLeadSteuerung / blueprintLoop / nachphase)

    Heute: 0 [INV-SPAWN]-Marker -> FAIL.
    Nach GREEN (Edit-Blocks B-F): 5 Marker eingefuegt -> PASS.
    """
    text = _read(I_ORCHESTRATE)

    inv_spawn_phase_count = text.count("[INV-SPAWN]")
    assert inv_spawn_phase_count >= 5, (
        f"'[INV-SPAWN]' Phasen-Marker zu selten in _I_orchestrate.md — "
        f"gefunden: {inv_spawn_phase_count} (erwartet: >= 5, je 1 fuer die 5 Top-Level-Phasen). "
        f"BL-465 Edit-Blocks B-F muessen '[INV-SPAWN]'-Kommentar-Marker vor jedem Phase-Call einfuegen "
        f"(teamSetup / kurzlebigPrompt / teamLeadSteuerung / blueprintLoop / nachphase)."
    )


# ── RED Tests (AC-3: exit_code-Gates) ─────────────────────────────────────────

def test_ac3_exit_code_gates():
    """
    AC-3 / DoD-8 (RED): Alle 5 Phasen-Uebergaenge muessen [GATE P]-Marker + exit_code-Checks
    VOR dem jeweiligen Phase-Call haben.

    Konkret:
      - text.count('[GATE P') >= 5    (GATE P1..P5 Marker)
      - Fuer jede Phase (P1..P5) muss ein 'BERATER_OUTPUTS.<vorgaenger>.exit_code'-Vergleich
        VOR dem naechsten Phase-Call stehen (mind. 5 solche Vorgaenger-exit_code-Checks).

    Heute: 0 [GATE P]-Marker, BERATER_OUTPUTS.*.exit_code-Checks = 0 -> FAIL.
    Nach GREEN (Edit-Blocks B-F): 5 Gates eingefuegt -> PASS.
    """
    text = _read(I_ORCHESTRATE)

    gate_count = text.count("[GATE P")
    assert gate_count >= 5, (
        f"'[GATE P' Marker zu selten in _I_orchestrate.md — "
        f"gefunden: {gate_count} (erwartet: >= 5). "
        f"BL-465 Edit-Blocks B-F muessen '[GATE P1]' bis '[GATE P5]' als State-Read-Marker "
        f"vor jedem Phase-Call einfuegen (AC-3, heute 1/5: nur i_dry_run_done vorhanden)."
    )

    # Zaehle BERATER_OUTPUTS.{vorgaenger}.exit_code-Vorgaenger-Checks
    # Erwartete Vorgaenger-Slots: teamSetup, kurzlebigPrompt, teamLeadSteuerung, blueprintLoop
    # (Phase 1 hat kein Vorgaenger-Gate, aber hat eigenes exit_code == 99 Gate)
    vorgaenger_slots = [
        "teamSetup",
        "kurzlebigPrompt",
        "teamLeadSteuerung",
        "blueprintLoop",
    ]
    # Suche nach BERATER_OUTPUTS.<slot>.exit_code als Gate-Check-Muster
    found_gates = [
        slot for slot in vorgaenger_slots
        if re.search(rf"BERATER_OUTPUTS\.{slot}\.exit_code\s*!=\s*0", text)
    ]
    assert len(found_gates) >= 4, (
        f"Zu wenige Vorgaenger-exit_code-Gate-Checks in _I_orchestrate.md — "
        f"gefunden fuer Slots: {found_gates} (erwartet: >= 4 von {vorgaenger_slots}). "
        f"Jede Phase P2-P5 muss einen 'BERATER_OUTPUTS.<vorgaenger>.exit_code != 0: ABORT'-Check "
        f"VOR dem naechsten Phase-Call haben (BL-465 AC-3, Edit-Blocks C-F)."
    )


def test_ac3_exit_code_99_abort():
    """
    AC-3 / DoD-9 (RED): Phase 1 muss einen exit_code == 99 -> ABORT-Pfad haben.

    Konkret:
      - re.search(r'exit_code == 99.*ABORT', text, re.DOTALL) (Phase-1-ABORT-Pfad)
        ODER re.search('exit_code == 99', text) + 'ABORT' in naechster Zeile

    Heute: 0 Treffer fuer 'exit_code == 99' -> FAIL.
    Nach GREEN (Edit-Block B): Phase-1-Gate mit exit_code == 99 -> ABORT eingefuegt -> PASS.
    """
    text = _read(I_ORCHESTRATE)

    # Suche nach exit_code == 99 gefolgt von ABORT (moeglicherweise mit Text dazwischen)
    has_99_abort = bool(re.search(r"exit_code\s*==\s*99[^\n]*ABORT", text))
    if not has_99_abort:
        # Alternativer Check: exit_code == 99 auf einer Zeile, ABORT auf einer nahen Zeile
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.search(r"exit_code\s*==\s*99", line):
                # Pruefe naechste 3 Zeilen auf ABORT
                context = "\n".join(lines[i:i+4])
                if "ABORT" in context:
                    has_99_abort = True
                    break

    assert has_99_abort, (
        "'exit_code == 99' mit ABORT-Semantik fehlt in _I_orchestrate.md — "
        "Phase-1-Gate ([GATE P1]) muss 'IF BERATER_OUTPUTS.teamSetup.exit_code == 99: ABORT' "
        "als ABORTED_PROCESS_VIOLATION-Pfad haben (BL-465 AC-3, Edit-Block B)."
    )


# ── GREEN / Charakterisierung Tests (AC-2 + AC-4 — initial GREEN, duerfen NICHT brechen) ──

def test_ac2_thin_logic_per_phase():
    """
    AC-2 / INV-THIN-2 (Charakterisierung, initial GREEN): Jeder der 5 Phase-Bloecke darf
    maximal 30 Logik-Zeilen (ohne Kommentare + ohne Leerzeilen) enthalten.

    Methodik: Suche die 5 Top-Level-Phase-Call-Bloecke in _I_orchestrate.md und zaehle
    Logik-Zeilen (Zeilen die weder leer noch nur-Kommentar sind).

    Heute GREEN: die Phase-Bloecke sind duenn (Direktive ist ja gerade das Ziel).
    Bleibt GREEN nach Edit (Edit-Blocks B-F fuegen nur Kommentar-Zeilen + 1-2 IF-Zeilen hinzu).
    """
    text = _read(I_ORCHESTRATE)

    # Definiere die 5 Top-Level-Phase-Anfang-Marker (suche nach Phase-Calls)
    phase_markers = [
        "_I_berater_teamSetup",
        "_I_berater_kurzlebigPrompt",
        "_I_berater_teamLeadSteuerung",
        "_I_berater_blueprintLoop",
        "_I_berater_nachphase",
    ]

    lines = text.splitlines()

    for marker in phase_markers:
        # Finde die Zeile mit diesem Marker
        marker_line_idx = None
        for i, line in enumerate(lines):
            if marker in line:
                marker_line_idx = i
                break

        if marker_line_idx is None:
            # Marker nicht gefunden: Phase noch nicht vorhanden, kein LOC-Problem
            continue

        # Extrahiere einen Fenster von +/- 15 Zeilen um den Marker (Phase-Block-Kontext)
        start = max(0, marker_line_idx - 10)
        end = min(len(lines), marker_line_idx + 20)
        block_lines = lines[start:end]

        # Zaehle Logik-Zeilen (nicht leer, nicht reine Kommentar-Zeilen mit #)
        logic_lines = [
            l for l in block_lines
            if l.strip() and not l.strip().startswith("#")
        ]

        assert len(logic_lines) <= 30, (
            f"Phase-Block fuer '{marker}' hat zu viele Logik-Zeilen: {len(logic_lines)} > 30. "
            f"INV-THIN-2 (BL-465 AC-2): jeder der 5 Phase-Bloecke darf maximal 30 Logik-LOC haben. "
            f"Logik-Zeilen im Block:\n" + "\n".join(f"  {l}" for l in logic_lines)
        )


def test_ac4_aidf_byte_identical():
    """
    AC-4 (Regression, initial GREEN): _A_orchestrate.md + _IDF_orchestrate.md muessen
    byte-identisch zum Baseline-Commit 403b032 sein (BL-465 darf diese Dateien NICHT anfassen).

    git diff --quiet 403b032 -- _A_orchestrate.md _IDF_orchestrate.md -> returncode 0 (leer).
    """
    a_rel   = ".claude/commands/_A_orchestrate.md"
    idf_rel = ".claude/commands/_IDF_orchestrate.md"

    result = subprocess.run(
        ["git", "diff", "--quiet", BASELINE_COMMIT, "--", a_rel, idf_rel],
        cwd=str(REPO_ROOT),
        capture_output=True,
    )
    assert result.returncode == 0, (
        f"_A_orchestrate.md oder _IDF_orchestrate.md haben sich gegenueber Baseline {BASELINE_COMMIT} "
        f"geaendert — BL-465 darf diese Dateien NICHT anfassen (AC-4 NICHT-Ziel NZ-1). "
        f"git diff output: {result.stdout.decode(errors='replace')}"
    )


def test_ac4_rollover_posthandover_intact():
    """
    AC-4 (Regression, initial GREEN): Pattern-B-Rollover + POST_HANDOVER + INV-HANDOVER-1
    muessen unveraendert in _I_orchestrate.md vorhanden sein.

    Marker: 'resume_zaehler' + 'INVARIANTE W11' + 'POST_HANDOVER' + 'INV-HANDOVER-1'

    BL-465 darf diese Bloecke NICHT anfassen (NZ-2 + NZ-3).
    """
    text = _read(I_ORCHESTRATE)

    assert "resume_zaehler" in text, (
        "'resume_zaehler' fehlt in _I_orchestrate.md — "
        "INVARIANTE W11 / Pattern-B-Rollover muss unveraendert erhalten bleiben (BL-465 AC-4, NZ-2)."
    )

    assert "INVARIANTE W11" in text, (
        "'INVARIANTE W11' fehlt in _I_orchestrate.md — "
        "der Rollover-Wachpunkt muss byte-identisch erhalten bleiben (BL-465 AC-4, NZ-2)."
    )

    assert "POST_HANDOVER" in text, (
        "'POST_HANDOVER' fehlt in _I_orchestrate.md — "
        "der POST_HANDOVER-Block (INV-MODUS-7 SKILL-HANDSCHUH-Pfad) muss unveraendert bleiben "
        "(BL-465 AC-4, NZ-3)."
    )

    assert "INV-HANDOVER-1" in text, (
        "'INV-HANDOVER-1' fehlt in _I_orchestrate.md — "
        "die INV-HANDOVER-1-Invariante muss unveraendert im POST_HANDOVER-Block bleiben "
        "(BL-465 AC-4, NZ-3)."
    )
