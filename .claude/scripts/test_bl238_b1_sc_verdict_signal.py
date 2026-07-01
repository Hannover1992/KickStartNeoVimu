#!/usr/bin/env python3
"""
test_bl238_b1_sc_verdict_signal.py — BL-238 Sub-Batch B-1 / Stage 1 (TDD RED)

Feature: Scientific SDF-Post Recalc-Loop / Modus-Neu-Bestimmung
Sub-Batch B-1 = SC-Saettigungs-Signal-Verdrahtung (DAG-Root L0+L1).
  Producer (AK-7-PL-1): _SC_orchestrate.md schreibt SC_PIPELINE_STATE.sc_verdict.
  Consumer (AK-1-PL-1): dispatch_implement.js liest sc_verdict nach SC-Stage und
                        triggert runPhase3(sb) AUSSERHALB des BATCH_DONE-Tors.

Stage 1 = powershell-verification (PATCH BL-111: kein dotnet/docker). "Test" =
Grep/Test-Path-Assertion gegen die zwei Zieldateien (.md/.js) bzw. statischer
Verdrahtungs-Nachweis des Consumer-Branches. Dies ist die Python-Realisierung der
Repo-Konvention (test_*.py in .claude/scripts/) fuer Grep-Asserts gegen Source.

Die 7 Tests spiegeln 1:1 die Test-Liste (T1-T7) aus sub-1.md (SOLL-Model, Kent-Beck
Outside-In, Canary-First) und die Gold-Definition-Exit-Kriterien des Sub-Blueprints.

TDD-PHASE: RED. Diese Tests MUESSEN initial fehlschlagen (Gesetz 2: assert-Fail = RED),
weil weder sc_verdict noch der Consumer-Branch gegen HEAD 24bbf75 existieren
(0 Grep-Treffer code-verifiziert). GREEN macht _TDD_green/_I_cleanCodeSlice.

Run: python .claude/scripts/test_bl238_b1_sc_verdict_signal.py
Exit 0 = alle PASS (GREEN), 1 = mindestens 1 FAIL (RED).
"""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
ROOT_DIR = SCRIPT_DIR.parent.parent
COMMANDS_DIR = ROOT_DIR / ".claude" / "commands"
WORKFLOWS_DIR = ROOT_DIR / ".claude" / "workflows"

SC_ORCH = COMMANDS_DIR / "_SC_orchestrate.md"
DISPATCH = WORKFLOWS_DIR / "dispatch_implement.js"

# INV-MODUS-5 verbotene Bypass-Felder (Slot-Isolation-Negativliste, sub-1.md PT-CMD-008,
# CLAUDE.md INV-MODUS-5). Diese Felder duerfen NICHT neu eingefuehrt werden.
#
# WICHTIG (6g-Verschaerfung, _TDD_refactorTests): Matching erfolgt per WORT-GRENZE (\b...\b),
# NICHT per naivem Substring. Grund: das standalone-Token `sdf_mode` ist verboten, aber die
# PRE-EXISTING, load-bearing Bestand-Felder `sdf_mode_original` / `sdf_mode_override` /
# `sdf_mode_normalized` (gelesen von teamSetup + modusMatrix, SC-Mode-Matrix-Kontrakt) sind
# LEGITIM. Ein naiver `"sdf_mode" in sc`-Substring-Check matchte diese Bestand-Felder und
# machte T3 mit korrektem Production-Code UNERREICHBAR (RED-Test-Design-Bug). Die Wort-Grenze
# trennt das verbotene standalone `sdf_mode` sauber von der legitimen `sdf_mode_*`-Familie.
BYPASS_FIELDS = [
    "recommended_modus",
    "sdf_mode",            # standalone-Token: \bsdf_mode\b matcht NICHT sdf_mode_original etc.
    "sdf_mode_hint",
    "expected_sdf_mode",
    "mode_recommendation",
]


def find_introduced_bypass_fields(text: str) -> list:
    """Whole-word Detection neu eingefuehrter INV-MODUS-5-Bypass-Felder.

    Nutzt Wort-Grenzen (\\b{feld}\\b) statt Substring-`in`, damit das verbotene standalone
    `sdf_mode` von den legitimen Bestand-Feldern `sdf_mode_original/_override/_normalized`
    unterschieden wird. `\\b` greift NICHT zwischen `sdf_mode` und `_original` (Underscore +
    Buchstaben sind Wort-Zeichen), also matcht `\\bsdf_mode\\b` nur das alleinstehende Token.
    Gibt die Liste der praezise gefundenen Bypass-Felder zurueck (leer = Slot-Isolation OK).
    """
    return [f for f in BYPASS_FIELDS if re.search(rf"\b{re.escape(f)}\b", text)]

LABEL = "[test_bl238_b1_sc_verdict_signal]"
PASS_COUNT = 0
FAIL_COUNT = 0


def assert_true(name, condition, hint=""):
    global PASS_COUNT, FAIL_COUNT
    if condition:
        PASS_COUNT += 1
        print(f"  PASS  {name}")
    else:
        FAIL_COUNT += 1
        msg = f"  FAIL  {name}"
        if hint:
            msg += f": {hint}"
        print(msg)


def load(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def frontmatter_version(text: str) -> str:
    """Liest den ersten `version:`-Wert aus dem Frontmatter (Top-of-File)."""
    m = re.search(r"^version:\s*([0-9]+\.[0-9]+\.[0-9]+)", text, re.MULTILINE)
    return m.group(1) if m else ""


def main():
    sc = load(SC_ORCH)
    di = load(DISPATCH)

    print(f"\n{LABEL} START (TDD RED — erwarte FAIL bis B-1 implementiert)")
    print(f"  _SC_orchestrate.md:    {'FOUND' if sc else 'MISSING'}")
    print(f"  dispatch_implement.js: {'FOUND' if di else 'MISSING'}")
    print()

    # ------------------------------------------------------------------
    # AK-7 (Producer, _SC_orchestrate.md) — T1..T3
    # ------------------------------------------------------------------

    # T1: sc_verdict-Write im SC_PIPELINE_STATE-Block + Literal SATURATED_READY_FOR_IMPL
    assert_true(
        "T1: _SC_orchestrate schreibt sc_verdict + Literal SATURATED_READY_FOR_IMPL",
        ("sc_verdict" in sc) and ("SATURATED_READY_FOR_IMPL" in sc),
        "Erwarte SC_PIPELINE_STATE.sc_verdict-Write am Phase-5 AUTOCHAIN-EXIT "
        "(:582-607, VOR Skill(_SDF_orchestrate_post)) + GROSS_SNAKE-Literal "
        "SATURATED_READY_FOR_IMPL (Gold AK-7 a)",
    )

    # T2: VERTRAG-SCHREIBT deklariert sc_verdict + Frontmatter version 3.5.0
    sc_writes_section = ""
    msec = re.search(
        r"SCHREIBT\s*\(?Output\)?(.*?)(?:\n#{1,3}\s|\nSCHREIBT-NICHT|\Z)",
        sc,
        re.DOTALL | re.IGNORECASE,
    )
    if msec:
        sc_writes_section = msec.group(1)
    assert_true(
        "T2: VERTRAG-SCHREIBT deklariert sc_verdict + version 3.5.0",
        ("sc_verdict" in sc_writes_section) and (frontmatter_version(sc) == "3.5.0"),
        "Erwarte sc_verdict in der VERTRAG-`SCHREIBT (Output)`-Sektion (PT-CMD-001, "
        "sonst Gate-7-ALARM) UND Frontmatter version: 3.5.0 (NC-8, war 3.4.0). "
        f"gefunden version={frontmatter_version(sc) or 'NONE'}, "
        f"sc_verdict_in_SCHREIBT={'sc_verdict' in sc_writes_section} (Gold AK-7 b)",
    )

    # T3: Slot-Isolation — kein NEUES INV-MODUS-5-Bypass-Feld eingefuehrt.
    # Wort-Grenzen-Detection (find_introduced_bypass_fields): unterscheidet das verbotene
    # standalone `sdf_mode` praezise von den legitimen Bestand-Feldern sdf_mode_*. Zusatz-
    # Assert: sc_verdict liegt nachweislich im SC_PIPELINE_STATE-Slot (kein getarntes
    # Modus-Feld), nicht nur "irgendwo" in der Datei.
    introduced_bypass = find_introduced_bypass_fields(sc)
    in_pipeline_state_slot = bool(
        re.search(r"SC_PIPELINE_STATE[^\n]{0,80}?sc_verdict", sc)
        or re.search(r"sc_verdict[^\n]{0,80}?SC_PIPELINE_STATE", sc)
    )
    assert_true(
        "T3: Slot-Isolation — kein INV-MODUS-5-Bypass-Feld (PT-CMD-008)",
        ("sc_verdict" in sc)
        and (len(introduced_bypass) == 0)
        and in_pipeline_state_slot,
        "sc_verdict MUSS im SC_PIPELINE_STATE-Slot liegen, NICHT als Modus-Empfehlung "
        "getarnt. Neu eingefuehrte (wort-genaue) Bypass-Felder: "
        f"{introduced_bypass or 'keine'}; sc_verdict_im_SC_PIPELINE_STATE_slot="
        f"{in_pipeline_state_slot}. Wort-Grenze ignoriert legitime Bestand-Felder "
        "sdf_mode_original/_override/_normalized (Gold AK-7 c)",
    )

    # ------------------------------------------------------------------
    # AK-1 (Consumer, dispatch_implement.js) — T4..T7
    # ------------------------------------------------------------------

    # T4: Consumer liest sc_verdict + ruft runPhase3 NEBEN (nicht IN) BATCH_DONE-Block.
    # 6g-Verschaerfung: Der frueher vage 400-Zeichen-Fenster-Match ("irgendein runPhase3 nahe
    # sc_verdict") belegte NICHT, dass der Trigger AUSSERHALB des BATCH_DONE-Tors liegt — genau
    # das ist aber die Gold-Forderung (AK-1 d: NEBEN, nicht IN). Jetzt praeziser strukturell:
    #   (a) Consumer liest sc_verdict (fam==='SC'-Branch),
    #   (b) es existiert ein runPhase3-Call in einem `sc_verdict`-Branch,
    #   (c) dieser Call liegt NICHT im `if (batchOutcome === 'BATCH_DONE')`-Block.
    reads_verdict = bool(re.search(r"fam\s*===\s*'SC'[^\n]{0,80}?sc_verdict", di)) or (
        "sc_verdict" in di
    )

    # (b) runPhase3 innerhalb eines sc_verdict-Saettigungs-Branches
    branch_pat = re.search(
        r"sc_verdict[^\n]{0,400}?runPhase3\s*\(",
        di,
        re.DOTALL,
    )

    # (c) Beweis "NEBEN, nicht IN": der sc_verdict-getriebene runPhase3-Call darf nicht
    # innerhalb des BATCH_DONE-Gates stehen. Wir isolieren den BATCH_DONE-Block-Korpus und
    # stellen sicher, dass mindestens ein runPhase3-Call EXISTIERT, der ausserhalb davon und
    # zugleich in Reichweite eines sc_verdict-Branches liegt.
    batch_done_block = re.search(
        r"if\s*\(\s*batchOutcome\s*===\s*'BATCH_DONE'\s*\)\s*\{(.*?)\n\s*\}",
        di,
        re.DOTALL,
    )
    batch_done_body = batch_done_block.group(1) if batch_done_block else ""
    sc_branch_block = re.search(
        r"if\s*\(\s*fam\s*===\s*'SC'\s*&&\s*sc_verdict\s*\)\s*\{(.*?)\n\s{0,4}\}\s*\n\s*\n",
        di,
        re.DOTALL,
    )
    sc_branch_body = sc_branch_block.group(1) if sc_branch_block else ""
    runphase3_in_sc_branch_not_batchdone = (
        ("runPhase3" in sc_branch_body) and ("runPhase3" not in batch_done_body)
        if sc_branch_block
        else False
    )

    assert_true(
        "T4: dispatch_implement liest sc_verdict + runPhase3-Trigger NEBEN BATCH_DONE",
        reads_verdict
        and (branch_pat is not None)
        and runphase3_in_sc_branch_not_batchdone,
        "Erwarte neuen Lese-Branch fuer sc_verdict nach runImplementStage(fam='SC') der "
        "runPhase3(sb) im `if (fam === 'SC' && sc_verdict)`-Block aufruft — AUSSERHALB des "
        "`if (batchOutcome === 'BATCH_DONE')`-Tors. "
        f"reads_sc_verdict={reads_verdict}, sc_verdict->runPhase3-Branch={branch_pat is not None}, "
        f"runPhase3_in_SC_branch_not_in_BATCH_DONE={runphase3_in_sc_branch_not_batchdone} "
        "(Gold AK-1 d: NEBEN, nicht IN)",
    )

    # T5: Saettigungs-Verdikte (SATURATED_READY_FOR_IMPL/EXPERIMENT_OPEN) -> runPhase3, KEIN ABORT
    has_saturation_branch = ("SATURATED_READY_FOR_IMPL" in di) or ("EXPERIMENT_OPEN" in di)
    assert_true(
        "T5: sc_verdict-Saettigung (SATURATED_READY_FOR_IMPL/EXPERIMENT_OPEN) -> runPhase3",
        reads_verdict and has_saturation_branch and (branch_pat is not None),
        "Motor-Replay-SOLL: SC-saettigt ⇒ runPhase3 genau 1×, KEIN break outer/ABORT. "
        "Statischer Nachweis: Saettigungs-Enum-Literal triggert runPhase3-Branch. "
        f"saturation_literal_present={has_saturation_branch} (Gold AK-1 d)",
    )

    # T6: ABORT-Pfad-Bestand — break outer bleibt fail-safe (Kanarienvogel)
    abort_branch = re.search(r"sc_verdict[^\n]{0,200}?ABORT", di, re.DOTALL) is not None
    abort_fallthrough = ("sc_verdict" in di) and ("break outer" in di)
    assert_true(
        "T6: sc_verdict==ABORT -> bestehendes break outer (fail-safe, Kanarienvogel)",
        reads_verdict and (abort_branch or abort_fallthrough),
        "Bei sc_verdict==ABORT MUSS der bestehende fail-safe `break outer`-Pfad "
        "(:350-354) unveraendert greifen — kein Verhaltens-Change vs HEAD 24bbf75 "
        "(Gold AK-1 e)",
    )

    # T7: Idempotenz — Trigger resume-idempotent (PT-CMD-007, analog statusTransition :236)
    idempotency_guard = bool(
        re.search(
            r"(phase3_done|phase3_fired|runphase3_done|already.{0,20}phase3|"
            r"idempoten|sc_verdict_consumed|recalc.{0,20}done)",
            di,
            re.IGNORECASE,
        )
    )
    assert_true(
        "T7: runPhase3-Trigger resume-idempotent (kein Doppel-Feuer, PT-CMD-007)",
        reads_verdict and idempotency_guard,
        "Erwarte Idempotenz-Guard am neuen Trigger (analog statusTransition-Idempotenz "
        ":236): 2× Replay desselben sub_batch ⇒ runPhase3-Count bleibt 1. "
        f"idempotency_marker_found={idempotency_guard} (Gold AK-1 f)",
    )

    print()
    total = PASS_COUNT + FAIL_COUNT
    print(f"{LABEL} RESULT: {PASS_COUNT}/{total} PASS, {FAIL_COUNT} FAIL")

    if FAIL_COUNT > 0:
        print(f"{LABEL} STATUS: RED")
        sys.exit(1)
    else:
        print(f"{LABEL} STATUS: GREEN")
        sys.exit(0)


if __name__ == "__main__":
    main()
