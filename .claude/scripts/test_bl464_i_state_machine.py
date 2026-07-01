"""
BL-464: I-Pipeline State-Machine Fundament — strukturelle pytest-Tests
RED-Worker: BL-464 batch_1 Stage 1 Iteration 1

Tests pruefen den Inhalt von .claude/commands/_I_orchestrate.md via grep/parse.
Diese Tests MUESSEN JETZT FAILEN (RED), weil die Struktur noch nicht existiert.
Ausnahme: test_ac4_regression_aidf_untouched (A/IDF-Dateien untouched -> initial GREEN).

Blueprint: BL-464_blueprint.md (TST-1..TST-5 + AC-1..AC-7)
Muster: analog test_bl414_stage_state.py / test_bl408_stage_lifecycle.py
"""

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA")
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"

I_ORCHESTRATE   = COMMANDS_DIR / "_I_orchestrate.md"
A_ORCHESTRATE   = COMMANDS_DIR / "_A_orchestrate.md"
IDF_ORCHESTRATE = COMMANDS_DIR / "_IDF_orchestrate.md"

# Baseline commit where A/IDF were last touched (pre-BL-464)
BASELINE_COMMIT = "f8e17d8"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── RED Tests (Struktur noch nicht vorhanden — MUESSEN FAILEN) ─────────────────

def test_ac1_state_machine_block_present():
    """
    TST-1 / AC-1 (RED): _I_orchestrate.md muss mind. 1 '## STATE-MACHINE'-Block enthalten.

    Heute: 0 STATE-MACHINE-Bloecke -> FAIL.
    Nach GREEN: >= 1 -> PASS.
    """
    text = _read(I_ORCHESTRATE)

    count = text.count("## STATE-MACHINE")
    assert count >= 1, (
        f"'## STATE-MACHINE' Block fehlt in _I_orchestrate.md — "
        f"gefunden: {count} (erwartet: >= 1). "
        f"BL-464 EDIT-BLOCK 1 muss eingefuegt werden."
    )


def test_ac1_seven_phase_transitions():
    """
    TST-2 / AC-1 + AC-5 (RED): _I_orchestrate.md muss alle 14 Phasen-Literale enthalten:
      BLUEPRINT_RUNNING, BLUEPRINT_DONE,
      GOLDDEFINE_RUNNING, GOLDDEFINE_DONE,
      TESTSEARCH_RUNNING, TESTSEARCH_DONE,
      RED_RUNNING, RED_DONE,
      GREEN_RUNNING, GREEN_DONE,
      REFACTOR_RUNNING, REFACTOR_DONE,
      VERIFY_RUNNING, VERIFY_DONE
    sowie das Wort 'exit_code'.

    Heute: keines dieser Literale vorhanden -> FAIL.
    """
    text = _read(I_ORCHESTRATE)

    required_literals = [
        "BLUEPRINT_RUNNING",  "BLUEPRINT_DONE",
        "GOLDDEFINE_RUNNING", "GOLDDEFINE_DONE",
        "TESTSEARCH_RUNNING", "TESTSEARCH_DONE",
        "RED_RUNNING",        "RED_DONE",
        "GREEN_RUNNING",      "GREEN_DONE",
        "REFACTOR_RUNNING",   "REFACTOR_DONE",
        "VERIFY_RUNNING",     "VERIFY_DONE",
    ]

    missing = [lit for lit in required_literals if lit not in text]
    assert not missing, (
        f"Fehlende Phasen-Literale in _I_orchestrate.md: {missing}. "
        f"BL-464 EDIT-BLOCK 1 (STATE-MACHINE) muss alle 14 Status-Transitionen deklarieren."
    )

    assert "exit_code" in text, (
        "'exit_code' fehlt in _I_orchestrate.md — "
        "exit_code-Konvention (0=DONE, 99=ABORTED) muss im STATE-MACHINE-Block stehen."
    )


def test_ac5_exit_code_convention():
    """
    TST / AC-5 (RED): _I_orchestrate.md muss die exit_code-Konvention GENERALISIERT im
    STATE-MACHINE-Block deklarieren. Konkret: der STATE-MACHINE-Block muss enthalten:
      - 'exit_code-Konvention' (Generalisierungs-Phrase aus EDIT-BLOCK 1)
      - 'exit_code=0' (DONE-Semantik, generalisiert)
      - 'ABORTED_PROCESS_VIOLATION' im SM-Block (als explizite Referenz, nicht nur Z891)

    Der bestehende Z891-892-Praezedenzfall ALLEINE genuegt nicht — der SM-Block muss
    die Konvention EXPLIZIT als Block-Level-Deklaration wiederholen/generalisieren.

    Heute: kein STATE-MACHINE-Block -> keine generalisierende exit_code-Konvention-Phrase -> FAIL.
    """
    text = _read(I_ORCHESTRATE)

    # Der STATE-MACHINE-Block muss eine explizite exit_code-Konventions-Deklaration tragen.
    # Marker: 'exit_code-Konvention' (die Generalisierungs-Ueberschrift aus EDIT-BLOCK 1).
    has_convention_phrase = bool(
        re.search(r"exit_code.Konvention", text, re.IGNORECASE)
    )
    assert has_convention_phrase, (
        "'exit_code-Konvention' (Generalisierungs-Phrase) fehlt in _I_orchestrate.md — "
        "der STATE-MACHINE-Block muss die exit_code-Konvention explizit als "
        "Block-Level-Deklaration tragen (BL-464 AC-5, EDIT-BLOCK 1 'exit_code-Konvention (generalisiert...)')."
    )

    # exit_code=0 Semantik muss als Generalisierung (nicht nur RETURN exit_code=99) erscheinen
    assert "exit_code=0" in text, (
        "'exit_code=0' Literal fehlt in _I_orchestrate.md — "
        "die generalisierte exit_code-Konvention (0=DONE, 99=ABORTED) im SM-Block "
        "muss exit_code=0 als DONE-Semantik deklarieren (BL-464 AC-5)."
    )


def test_ac2_berater_outputs_slots():
    """
    TST-3 / AC-2 (RED): _I_orchestrate.md muss >= 7 distinct BERATER_OUTPUTS.{key}-Slot-Deklarationen
    mit den 7 neuen Phase-Keys enthalten:
      blueprint, goldDefine, testSearch, red, green, refactor, verify

    Heute: nur 4 distinct Slots (teamSetup, teamLeadSteuerung, nachphase, patternBrief) -> FAIL.
    """
    text = _read(I_ORCHESTRATE)

    required_keys = [
        "blueprint",
        "goldDefine",
        "testSearch",
        "red",
        "green",
        "refactor",
        "verify",
    ]

    missing_keys = [
        key for key in required_keys
        if f"BERATER_OUTPUTS.{key}" not in text
    ]

    assert not missing_keys, (
        f"Fehlende BERATER_OUTPUTS-Slot-Keys in _I_orchestrate.md: {missing_keys}. "
        f"BL-464 EDIT-BLOCK 2 muss alle 7 Phase-Slots deklarieren "
        f"(BERATER_OUTPUTS.blueprint / .goldDefine / .testSearch / .red / .green / .refactor / .verify)."
    )

    # Zaehle distinct BERATER_OUTPUTS.{key} Vorkommen der neuen Keys
    found_slots = [key for key in required_keys if f"BERATER_OUTPUTS.{key}" in text]
    assert len(found_slots) >= 7, (
        f"Nur {len(found_slots)} der 7 erforderlichen BERATER_OUTPUTS-Slots gefunden: {found_slots}. "
        f"Alle 7 neuen Phase-Slots muessen vorhanden sein (BL-464 AC-2)."
    )


def test_ac3_datenfluss_prinzip():
    """
    TST / AC-3 (RED): _I_orchestrate.md muss einen 'DATENFLUSS-PRINZIP'-Block UND 'INV-DATA-I-1' enthalten.

    Heute: weder DATENFLUSS-PRINZIP noch INV-DATA-I-1 vorhanden -> FAIL.
    """
    text = _read(I_ORCHESTRATE)

    assert "DATENFLUSS-PRINZIP" in text, (
        "'DATENFLUSS-PRINZIP' fehlt in _I_orchestrate.md — "
        "BL-464 EDIT-BLOCK 3a muss den DATENFLUSS-PRINZIP-Textblock in den VERTRAG einfuegen "
        "(analog IDF Z56-60 / Z345-362)."
    )

    assert "INV-DATA-I-1" in text, (
        "'INV-DATA-I-1' fehlt in _I_orchestrate.md — "
        "BL-464 EDIT-BLOCK 3b muss die INV-DATA-I-1-Invariante in den INVARIANTEN-Block einfuegen "
        "(Schwester von IDF INV-DATA-1 + A INV-DATA-1)."
    )


def test_ac6_modus_unabhaengig_seam():
    """
    TST-6 / AC-6 (RED): _I_orchestrate.md muss eine Note enthalten, dass der State-Seam
    modus-unabhaengig ist (haengt am State-Handoff, NICHT an tdd_enabled).

    Marker: 'STATE-HANDOFF' UND ('modus-unabhaengig' ODER 'M2' + 'dieselbe Kette' / 'NICHT an tdd_enabled')

    Heute: kein STATE-MACHINE-Block -> diese Marker fehlen -> FAIL.
    """
    text = _read(I_ORCHESTRATE)

    assert "STATE-HANDOFF" in text, (
        "'STATE-HANDOFF' fehlt in _I_orchestrate.md — "
        "die modus-unabhaengige Seam-Note (BL-464 AC-6, EDIT-BLOCK 5) muss im STATE-MACHINE-Block stehen."
    )

    has_modus_note = bool(
        re.search(
            r"modus.unabh[aä]ngig|NICHT\s+an\s+tdd_enabled|M2.*dieselbe\s+Kette",
            text,
            re.IGNORECASE,
        )
    )
    assert has_modus_note, (
        "Modus-unabhaengiger Seam-Hinweis fehlt in _I_orchestrate.md — "
        "der STATE-MACHINE-Block muss erklaeren, dass M2 dieselbe 7-Phasen-Kette durchlaeuft "
        "und der Seam NICHT an tdd_enabled haengt (BL-464 AC-6)."
    )


def test_ac7_scope_sperre():
    """
    TST / AC-7 (RED): _I_orchestrate.md muss einen Scope-Sperre-Block enthalten mit
    expliziten Referenzen auf 'BL-465' UND 'BL-466' als Out-of-Scope.

    Heute: kein STATE-MACHINE-Block, kein SCOPE-SPERRE-Block -> FAIL.
    """
    text = _read(I_ORCHESTRATE)

    assert "SCOPE-SPERRE" in text, (
        "'SCOPE-SPERRE' fehlt in _I_orchestrate.md — "
        "BL-464 EDIT-BLOCK 6 muss den Scope-Sperre-Block im STATE-MACHINE-Block einfuegen."
    )

    assert "BL-465" in text, (
        "'BL-465' fehlt im SCOPE-SPERRE-Block von _I_orchestrate.md — "
        "der Block muss BL-465 (Spawn-Migration) explizit als Out-of-Scope markieren."
    )

    assert "BL-466" in text, (
        "'BL-466' fehlt im SCOPE-SPERRE-Block von _I_orchestrate.md — "
        "der Block muss BL-466 (M2-Haertung) explizit als Out-of-Scope markieren."
    )


# ── Regression / Characterization Test (initial GREEN fuer A/IDF; I bleibt beobachtet) ──

def test_ac4_regression_aidf_untouched():
    """
    TST-5 / AC-4 (initial GREEN fuer A/IDF-Teil):
      1. git diff --quiet gegen Baseline f8e17d8 fuer A_orchestrate.md + IDF_orchestrate.md
         -> erwarte exit_code 0 (keine Aenderungen) — dieser Teil ist initial GREEN.
      2. Pattern-B-Rollover-Zeilen in _I_orchestrate.md vorhanden bleiben:
         'resume_zaehler' + 'INVARIANTE W11' + 'Pattern B'
         -> ebenfalls initial GREEN (unveraendert).

    Nach BL-464 GREEN (Edit an _I_orchestrate.md): A/IDF muessen noch immer byte-identisch sein.
    """
    # 1. A/IDF byte-identisch zur Baseline
    a_rel   = ".claude/commands/_A_orchestrate.md"
    idf_rel = ".claude/commands/_IDF_orchestrate.md"

    result = subprocess.run(
        ["git", "diff", "--quiet", BASELINE_COMMIT, "--", a_rel, idf_rel],
        cwd=str(REPO_ROOT),
        capture_output=True,
    )
    assert result.returncode == 0, (
        f"_A_orchestrate.md oder _IDF_orchestrate.md haben sich gegenueber Baseline {BASELINE_COMMIT} "
        f"geaendert — BL-464 darf diese Dateien NICHT anfassen (AC-4, EDIT-BLOCK 7). "
        f"git diff output: {result.stdout.decode(errors='replace')}"
    )

    # 2. Pattern-B-Rollover-Zeilen in _I_orchestrate.md unveraendert vorhanden
    text = _read(I_ORCHESTRATE)

    assert "resume_zaehler" in text, (
        "'resume_zaehler' fehlt in _I_orchestrate.md — "
        "INVARIANTE W11 / Pattern-B-Rollover muss unveraendert erhalten bleiben (AC-4)."
    )

    assert "INVARIANTE W11" in text, (
        "'INVARIANTE W11' fehlt in _I_orchestrate.md — "
        "der Rollover-Wachpunkt (Z364-366) muss byte-identisch erhalten bleiben (AC-4)."
    )

    assert "Pattern B" in text, (
        "'Pattern B' fehlt in _I_orchestrate.md — "
        "der Pattern-B-Rollover-Kontext (Step 23) muss unveraendert bleiben (AC-4)."
    )
