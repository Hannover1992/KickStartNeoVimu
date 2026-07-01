"""
BL-414: Stage-State Single-Writer Conformance Tests
RED-Worker: BL-414 Slice 1 Stage 1 Iteration 1

2 RED-Tests (INV-STAGE-STATE-1 fehlt in _I_orchestrate.md + _SDF_orchestrate.md):
  - test_i_orchestrate_has_inv_stage_state_1
  - test_sdf_orchestrate_has_inv_stage_state_1

3 Characterization-Tests (GRUEN — beschreiben bestehenden Zustand):
  - test_hardwired_default_stage_1
  - test_resolution_via_resolve_vault_stage
  - test_stageelevation_writes_current_stage
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA")
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"
SCRIPTS_DIR = REPO_ROOT / ".claude" / "scripts"

I_ORCHESTRATE = COMMANDS_DIR / "_I_orchestrate.md"
SDF_ORCHESTRATE = COMMANDS_DIR / "_SDF_orchestrate.md"
SDF_STAGE_ELEVATION = COMMANDS_DIR / "_SDF_berater_stageElevation.md"
RESOLVE_VAULT_STAGE = SCRIPTS_DIR / "resolve_vault_stage.py"


# ── RED Tests (INV-STAGE-STATE-1 fehlt — diese Tests MUESSEN failen) ───────────

def test_i_orchestrate_has_inv_stage_state_1():
    """
    RED: _I_orchestrate.md muss einen expliziten Single-Writer-Stage-State-Vertrag
    namens INV-STAGE-STATE-1 enthalten.

    Der Vertrag muss beschreiben:
      - dass current_stage einen kanonischen Single-Writer hat
      - dass kein anderer Caller current_stage inferiert oder schreibt ("raten" / "Inferenz" verboten)

    Erwartet: INV-STAGE-STATE-1 + (Single-Writer ODER ein Writer ODER einem Writer)
               + (keine/NICHT + Inferenz/raten)
    """
    text = I_ORCHESTRATE.read_text(encoding="utf-8")

    assert "INV-STAGE-STATE-1" in text, (
        "INV-STAGE-STATE-1 fehlt in _I_orchestrate.md — "
        "Single-Writer-Stage-State-Vertrag nicht dokumentiert"
    )

    has_single_writer = bool(
        re.search(r"(Single-Writer|ein\s+Writer|einem\s+Writer)", text, re.IGNORECASE)
    )
    assert has_single_writer, (
        "INV-STAGE-STATE-1 gefunden, aber kein Single-Writer-Begriff "
        "(Single-Writer / ein Writer / einem Writer) in _I_orchestrate.md"
    )

    has_no_inference = bool(
        re.search(
            r"(keine\s+Inferenz|NICHT\s+Inferenz|nicht\s+raten|NICHT\s+raten|keine\s+.*raten)",
            text,
            re.IGNORECASE,
        )
    )
    assert has_no_inference, (
        "INV-STAGE-STATE-1 gefunden, aber Inferenz/Raten-Verbot fehlt "
        "(keine/NICHT + Inferenz/raten) in _I_orchestrate.md"
    )


def test_sdf_orchestrate_has_inv_stage_state_1():
    """
    RED: _SDF_orchestrate.md muss INV-STAGE-STATE-1 referenzieren —
    als Beleg dass SDF die Writer-Disziplin fuer current_stage kennt und einhalt.

    Erwartet: INV-STAGE-STATE-1 + current_stage (kanonisch + Writer-Kontext)
    """
    text = SDF_ORCHESTRATE.read_text(encoding="utf-8")

    assert "INV-STAGE-STATE-1" in text, (
        "INV-STAGE-STATE-1 fehlt in _SDF_orchestrate.md — "
        "SDF referenziert den Stage-State Single-Writer-Vertrag nicht"
    )

    assert "current_stage" in text, (
        "INV-STAGE-STATE-1 gefunden, aber 'current_stage' fehlt in _SDF_orchestrate.md — "
        "Writer-Disziplin-Kontext fehlt"
    )


# ── Characterization Tests (beschreiben bestehenden Zustand — GRUEN) ───────────

def test_hardwired_default_stage_1():
    """
    CHARACTERIZATION (GRUEN): _I_orchestrate.md hat einen hardwired Default
    current_stage=1 via STAGE-ARG-SYNC (BL-171).

    Bestaetigt: STAGE-ARG-SYNC-Block setzt current_stage = 1 wenn kein --stage Arg.
    """
    text = I_ORCHESTRATE.read_text(encoding="utf-8")

    assert "STAGE-ARG-SYNC" in text, (
        "STAGE-ARG-SYNC Block fehlt in _I_orchestrate.md"
    )

    assert "current_stage = 1" in text or "current_stage=1" in text, (
        "Kein hardwired Default 'current_stage = 1' in _I_orchestrate.md"
    )


def test_resolution_via_resolve_vault_stage():
    """
    CHARACTERIZATION (GRUEN): resolve_vault_stage.py exportiert resolve_stage(n) -> StageHandle.

    Bestaetigt: Funktion resolve_stage und Klasse StageHandle sind vorhanden.
    """
    text = RESOLVE_VAULT_STAGE.read_text(encoding="utf-8")

    assert "def resolve_stage(" in text, (
        "resolve_stage() Funktion fehlt in resolve_vault_stage.py"
    )

    assert "class StageHandle" in text, (
        "StageHandle Klasse fehlt in resolve_vault_stage.py"
    )

    # Rueckgabetyp: StageHandle in Signatur oder Docstring dokumentiert
    assert "StageHandle" in text, (
        "StageHandle nicht als Rueckgabetyp in resolve_vault_stage.py dokumentiert"
    )


def test_stageelevation_writes_current_stage():
    """
    CHARACTERIZATION (GRUEN): _SDF_berater_stageElevation.md liest DF_BATCH_STATE.current_stage
    und ist der kanonische Schreib-Punkt fuer Stage-Elevation-Decisions (der EINE Writer/increment).

    Bestaetigt: current_stage erscheint im LIEST-Vertrag und im SCHREIBT-Block
    (BERATER_OUTPUTS.stageElevation).
    """
    text = SDF_STAGE_ELEVATION.read_text(encoding="utf-8")

    assert "DF_BATCH_STATE.current_stage" in text, (
        "DF_BATCH_STATE.current_stage fehlt in _SDF_berater_stageElevation.md — "
        "kein Read-Vertrag fuer current_stage"
    )

    assert "BERATER_OUTPUTS.stageElevation" in text, (
        "BERATER_OUTPUTS.stageElevation fehlt in _SDF_berater_stageElevation.md — "
        "kein Write-Output-Block"
    )

    assert "current_stage" in text, (
        "current_stage fehlt komplett in _SDF_berater_stageElevation.md"
    )
