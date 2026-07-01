"""
BL-468: SDF-orchestrate (Pre-SDF/Outer-Loop) contract-driven (Spawn-Haertung) — strukturelle pytest-Tests
RED-Worker: BL-468 batch_1 Slice 1 Iteration 1

Tests pruefen den Inhalt von .claude/commands/_SDF_orchestrate.md via grep/parse.
AK-1/AK-3-Tests MUESSEN JETZT FAILEN (RED) — Marker fehlen noch.
AK-2/AK-4-Tests sind Charakterisierung/Regression (initial GREEN, duerfen NICHT brechen).

Blueprint: BL-468_blueprint.md (Gold-Definition + RED!=GREEN-Trennung)
RED-Baseline (verifiziert 2026-06-24):
  [INV-SPAWN]=0, [GATE P]=0, ## STATE-MACHINE=0, ## WORKER-SPAWN-PATTERN=0,
  BERATER_OUTPUTS.=13/16, Motor-Literale {dispatch_implement=4, motor_allowed=4, VEHIKEL-GATE=2, loop_decision=9},
  Skip-Literale {N=1=9, STALE-HANDOFF=3, single_batch=1}.
"""

import re
from pathlib import Path

REPO_ROOT = Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA")
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"

SDF_ORCH = COMMANDS_DIR / "_SDF_orchestrate.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── RED-Hebel (AK-1): INV-SPAWN-Marker + WORKER-SPAWN-PATTERN ──────────────────

def test_ak1_inv_spawn_marker_count():
    """
    AK-1 / DoD-1 (RED): _SDF_orchestrate.md muss >= 5 [INV-SPAWN]-Marker enthalten.

    Blueprint: Edit-Blocks C..I setzen je 1 [INV-SPAWN]-Marker pro Berater-Call-Stelle.
    6 Marker geplant (5 distinct Berater, patternBrief+modusEntscheidung je 2 Call-Stellen).

    RED-Baseline: [INV-SPAWN]=0 -> MUSS FAILEN.
    GREEN-Ziel: 6 Marker (>= 5 erfuellt).

    false-GREEN-Falle: Falls ein Marker ausversehen bereits existiert -> Test schlaegt
    fehl wegen Count=0. Nur Edit-Blocks C..I (BL-468) duerfen diese Marker setzen.
    """
    text = _read(SDF_ORCH)

    inv_spawn_count = text.count("[INV-SPAWN]")
    assert inv_spawn_count >= 5, (
        f"'[INV-SPAWN]' Phasen-Marker zu selten in _SDF_orchestrate.md — "
        f"gefunden: {inv_spawn_count} (erwartet: >= 5, je 1 fuer die 6 Berater-Call-Stellen). "
        f"BL-468 Edit-Blocks C..I muessen '[INV-SPAWN]'-Kommentar-Marker vor jedem Berater-Call einfuegen "
        f"(testRun=Z105, analyse=Z110, altmodisch modusEntscheidung=Z235, altmodisch patternBrief=Z236, "
        f"architecturalBrief=Z285, patternBrief=Z286, modusEntscheidung=Z289)."
    )


def test_ak1_worker_spawn_pattern_block():
    """
    AK-1 / DoD-2+3 (RED): _SDF_orchestrate.md muss genau 1x '## WORKER-SPAWN-PATTERN'
    enthalten + der Block muss Agent()-Spawn-Schablone mit sdf-Team-Konvention und
    Worker-stirbt-Semantik deklarieren.

    Blueprint: Edit-Block A (nach ## VERTRAG, vor ## Phase 0a) — 1:1 BL-469-Schwester-Spiegel.

    RED-Baseline: ## WORKER-SPAWN-PATTERN=0 -> MUSS FAILEN.
    GREEN-Ziel: Count==1 + Agent(subagent_type + team_name="sdf-" + Worker stirbt.
    """
    text = _read(SDF_ORCH)

    pattern_count = len(re.findall(r"^## WORKER-SPAWN-PATTERN", text, re.MULTILINE))
    assert pattern_count == 1, (
        f"'## WORKER-SPAWN-PATTERN' Block fehlt oder mehrfach in _SDF_orchestrate.md — "
        f"gefunden: {pattern_count} (erwartet: genau 1). "
        f"BL-468 Edit-Block A muss den WORKER-SPAWN-PATTERN-Header einfuegen "
        f"(nach ## VERTRAG-Block, vor ## Phase 0a — 1:1 Spiegel BL-469-Schwester _SDF_orchestrate_post.md Z110-165)."
    )

    has_agent_spawn = bool(re.search(r"Agent\(\s*subagent_type", text))
    assert has_agent_spawn, (
        "'Agent(subagent_type' fehlt in _SDF_orchestrate.md — "
        "der WORKER-SPAWN-PATTERN-Block muss ein Agent()-Spawn-Template mit subagent_type-Parameter "
        "enthalten (BL-468 Edit-Block A, SDF-Spawn-Schablone)."
    )

    has_sdf_team = 'team_name="sdf-' in text
    assert has_sdf_team, (
        "'team_name=\"sdf-' Konvention fehlt in _SDF_orchestrate.md — "
        "das Agent()-Template muss team_name=\"sdf-{NAME}\" als SDF-Team-Konvention "
        "deklarieren (BL-468 Edit-Block A, analog BL-469-Schwester team_name=\"sdf-\")."
    )

    has_worker_stirbt = "Worker stirbt nach Skill-Ausfuehrung" in text
    assert has_worker_stirbt, (
        "'Worker stirbt nach Skill-Ausfuehrung' Semantik fehlt in _SDF_orchestrate.md — "
        "das WORKER-SPAWN-PATTERN muss die Kurzlebig-Worker-Semantik "
        "('Worker stirbt nach Skill-Ausfuehrung') explizit deklarieren (BL-468 Edit-Block A)."
    )


def test_ak1_scope_note_three_call_classes():
    """
    AK-1 / DoD-4 (RED): SCOPE-NOTE muss die 3 Call-Klassen explizit benennen.

    Blueprint: SCOPE-NOTE in Block A (BL-468-Spezifikum, AK-1/AK-4-KRITISCH):
    (a) Berater-Spawns (5, INV-SPAWN-Targets): _SDF_berater_testRun, _SDF_berater_analyse,
        _SDF_berater_architecturalBrief, _SDF_berater_patternBrief, _SDF_berater_modusEntscheidung
    (b) Orchestrator-Handschuh-Loads (KEIN [INV-SPAWN], INV-AO-CALLER):
        _I_orchestrate/_SC_orchestrate und _IDF_orchestrate als NICHT-Spawn-Ziele
    (c) Motor-Start (1, byte-intakt): Workflow(dispatch_implement)

    Der Test prueft: SCOPE-NOTE vorhanden + mindestens 1 _SDF_berater_-Spawn-Target
    + mindestens 1 Orchestrator (_I_orchestrate oder _SC_orchestrate oder _IDF_orchestrate)
    als NICHT-Spawn-Kontext.

    RED-Baseline: SCOPE-NOTE=0 -> MUSS FAILEN.
    GREEN-Ziel: SCOPE-NOTE + Spawn-Targets + Orchestrator-Anti-Liste vorhanden.
    """
    text = _read(SDF_ORCH)

    has_scope_note = "SCOPE-NOTE" in text
    assert has_scope_note, (
        "'SCOPE-NOTE' fehlt in _SDF_orchestrate.md — "
        "Block A muss eine SCOPE-NOTE einfuegen, die die 3 Call-Klassen explizit benennt: "
        "(a) 5 Berater-Spawn-Targets (_SDF_berater_*), "
        "(b) Orchestrator-Handschuh-Loads (KEIN [INV-SPAWN], INV-AO-CALLER: _I_orchestrate etc.), "
        "(c) Motor-Start (Workflow(dispatch_implement), byte-intakt). "
        "BL-468 Edit-Block A, AK-1d/AK-1e."
    )

    # SCOPE-NOTE muss Berater-Spawn-Targets erwaehnen
    has_berater_targets = "_SDF_berater_" in text
    # Bestehende _SDF_berater_-Referenzen zählen schon — aber im SCOPE-NOTE-Kontext muss es explizit stehen
    # Pruefe: SCOPE-NOTE-Abschnitt enthaelt mindestens 1 _SDF_berater_- Referenz in Spawn-Targets-Kontext
    # Toleranter Check: mindestens 3 distinct _SDF_berater_-Matches (bestehend hat schon >3)
    sdf_berater_in_scope_note_context = len(re.findall(r"_SDF_berater_\w+", text))
    assert sdf_berater_in_scope_note_context >= 5, (
        f"SCOPE-NOTE enthaelt zu wenige _SDF_berater_*-Spawn-Target-Referenzen in _SDF_orchestrate.md — "
        f"gefunden: {sdf_berater_in_scope_note_context} (erwartet: >= 5, die 5 distinct Berater). "
        f"Block A muss die 5 Berater-Spawns explizit in der SCOPE-NOTE-Punkt-Liste erwaehnen "
        f"(testRun/analyse/architecturalBrief/patternBrief/modusEntscheidung). BL-468 AK-1d."
    )

    # SCOPE-NOTE muss Orchestrator-Anti-Liste enthalten (z.B. _I_orchestrate als NICHT-Spawn)
    # Die bestehende Datei hat schon _I_orchestrate (Z317), aber SCOPE-NOTE muss es als ANTI-Liste explizit benennen.
    # Pruefe: die Datei enthaelt sowohl "_I_orchestrate" als auch "_IDF_orchestrate" (bereits vorhanden in Z166/Z258/Z317)
    # + die SCOPE-NOTE-Sektion muss das Orchestrator-Thema adressieren.
    # Konkreter RED-Hebel: SCOPE-NOTE fehlt (oben schon gefangen) -> dieser Teilcheck prueft
    # dass nach GREEN sowohl Spawn-Targets (a) als auch Orchestrator-Loads (b) in der SCOPE-NOTE stehen.
    # Fuer RED reicht SCOPE-NOTE-fehlt (oben) als primärer Fail.
    # Zusaetzlicher Check: Orchestrator-Keywords muessen in SCOPE-NOTE-Kontext erwaehnt werden.
    has_orchestrator_anti_mention = (
        "_I_orchestrate" in text or "_SC_orchestrate" in text
    ) and "_IDF_orchestrate" in text
    assert has_orchestrator_anti_mention, (
        "Orchestrator-Handschuh-Load-Referenzen fehlen in _SDF_orchestrate.md — "
        "SCOPE-NOTE Block A muss _I_orchestrate/_SC_orchestrate UND _IDF_orchestrate als "
        "NICHT-Spawn-Ziele (INV-AO-CALLER) explizit benennen. "
        "BL-468 Edit-Block A Punkt (b): Orchestrator-Anti-Liste."
    )


# ── RED-Hebel (AK-3): STATE-MACHINE + [GATE P] + exit_code=99 + [M2-SEAM-HARDENED] ──────────────

def test_ak3_state_machine_block():
    """
    AK-3 / DoD-5 (RED): _SDF_orchestrate.md muss genau 1x '## STATE-MACHINE'
    enthalten (Bindestrich-Form, disjunkt zu bestehendem '## State Machine: DF_PIPELINE_STATE').

    Blueprint: Edit-Block B (direkt nach Edit-Block A, vor ## Phase 0a) — Spiegel BL-469-Schwester.
    Transitions-Kette: INIT -> TESTRUN_DONE -> ANALYSE_DONE -> ... -> COMPLETED | ABORTED_PROCESS_VIOLATION.

    RED-Baseline: ## STATE-MACHINE=0 -> MUSS FAILEN.
    GREEN-Ziel: Count==1.

    AE-6 (Header-Disambiguierung): Bestehende '## State Machine: DF_PIPELINE_STATE' (Z77)
    zaehlt NICHT — anderer Header. Neuer Block heisst EXAKT '## STATE-MACHINE' (Bindestrich, kein Suffix).
    """
    text = _read(SDF_ORCH)

    # Bestehende "## State Machine:" (Leerzeichen) darf NICHT mitgezaehlt werden
    state_machine_count = len(re.findall(r"^## STATE-MACHINE$", text, re.MULTILINE))
    assert state_machine_count == 1, (
        f"'## STATE-MACHINE' Block (Bindestrich-Form, exakter Match) fehlt oder mehrfach in _SDF_orchestrate.md — "
        f"gefunden: {state_machine_count} (erwartet: genau 1). "
        f"BL-468 Edit-Block B muss '## STATE-MACHINE' (EXAKT, Bindestrich, kein Suffix) einfuegen — "
        f"NICHT '## State Machine: DF_PIPELINE_STATE' (bereits Z77 vorhanden, zaehlt NICHT). "
        f"Transitions-Kette: INIT -> TESTRUN_DONE -> ANALYSE_DONE -> ARCH_BRIEF_DONE -> "
        f"PATTERN_BRIEF_DONE -> MODUS_DONE -> DISPATCHED -> COMPLETED | ABORTED_PROCESS_VIOLATION."
    )


def test_ak3_gate_p_count():
    """
    AK-3 / DoD-6 (RED): _SDF_orchestrate.md muss >= 5 [GATE P]-Marker enthalten.

    Blueprint: Edit-Blocks C..I setzen je 1 [GATE P{N}] pro Berater-Call-Stelle.
    7 Gates geplant ([GATE P1]..[GATE P7]).

    RED-Baseline: [GATE P]=0 -> MUSS FAILEN.
    GREEN-Ziel: 7 Gates (>= 5 erfuellt).

    AE-3 ([GATE P]-Semantik): == 99 ABORT statt != 0 (Skip-Toleranz fuer Pre-SDF-Skip-Dichte:
    testRun-only-SKIP / single_batch / N=1-Fast-Path).
    """
    text = _read(SDF_ORCH)

    gate_count = text.count("[GATE P")
    assert gate_count >= 5, (
        f"'[GATE P' Marker zu selten in _SDF_orchestrate.md — "
        f"gefunden: {gate_count} (erwartet: >= 5). "
        f"BL-468 Edit-Blocks C..I muessen '[GATE P1]' bis '[GATE P7]' als State-Read-Marker "
        f"vor jedem Berater-Call einfuegen (AE-3: exit_code==99-ABORT-Semantik, "
        f"NOT != 0, wegen Pre-SDF-Skip-Dichte testRun-only/single_batch/N=1-Fast-Path). "
        f"Tabelle: C=P1(testRun), D=P2(analyse), E=P3(alt-modusEnt), F=P4(alt-patternBrief), "
        f"G=P5(architecturalBrief), H=P6(patternBrief), I=P7(modusEntscheidung)."
    )


def test_ak3_exit_code_99_abort():
    """
    AK-3 / DoD-7 (RED): _SDF_orchestrate.md muss exit_code-99 + ABORTED_PROCESS_VIOLATION
    Konvention dokumentieren.

    Blueprint: Edit-Block B (STATE-MACHINE) muss exit_code=0=DONE, exit_code=2=FAIL,
    exit_code=99=ABORTED_PROCESS_VIOLATION deklarieren. Literal 'exit_code' + '99' matchbar.

    RED-Baseline: exit_code.*99=0 + ABORTED_PROCESS_VIOLATION=0 -> MUSS FAILEN.
    GREEN-Ziel: beide vorhanden.

    Hinweis: Bestehende Datei hat exit_code=2 (Z281, Z292) und ABORTED-Zustand (Z82),
    aber NOCH KEIN exit_code=99 + ABORTED_PROCESS_VIOLATION (letzteres nur im IST: "ABORTED",
    nicht "ABORTED_PROCESS_VIOLATION"). Beides muss durch Block B hinzukommen.
    """
    text = _read(SDF_ORCH)

    # Pruefe exit_code.*99 (tolerant: exit_code=99 oder exit_code == 99)
    has_exit_code_99 = bool(re.search(r"exit_code[^\n]*99", text))
    if not has_exit_code_99:
        # Alternativer Check: exit_code auf einer Zeile, 99 in Kontext-Block
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.search(r"exit_code", line):
                context = "\n".join(lines[i:i + 3])
                if "99" in context and "ABORT" in context:
                    has_exit_code_99 = True
                    break

    assert has_exit_code_99, (
        "'exit_code' mit '99' Konvention fehlt in _SDF_orchestrate.md — "
        "der STATE-MACHINE-Block (Edit-Block B) muss exit_code=99 als ABORTED_PROCESS_VIOLATION "
        "deklarieren (neben exit_code=0=DONE + exit_code=2=FAIL). "
        "Muster: re.search(r'exit_code[^\\n]*99', text) muss treffen (BL-468 AK-3 AE-3)."
    )

    has_aborted_process = "ABORTED_PROCESS_VIOLATION" in text
    assert has_aborted_process, (
        "'ABORTED_PROCESS_VIOLATION' fehlt in _SDF_orchestrate.md — "
        "der STATE-MACHINE-Block muss den ABORTED_PROCESS_VIOLATION Terminal-Zustand "
        "explizit benennen (exit_code=99, any phase). BL-468 Edit-Block B. "
        "Hinweis: Bestehende 'ABORTED'-Literale (Z82/Z84) zaehlen NICHT — "
        "der vollstaendige String 'ABORTED_PROCESS_VIOLATION' muss vorhanden sein."
    )


def test_ak3_m2_seam_hardened():
    """
    AK-3 / DoD-8 (RED): _SDF_orchestrate.md muss [M2-SEAM-HARDENED]-Marker enthalten.

    Blueprint: Edit-Block B (STATE-MACHINE) + Edit-Block J (altmodischer-Pfad-Note)
    setzen '[M2-SEAM-HARDENED]'. Mindestens 1 Vorkommen erwartet.

    RED-Baseline: [M2-SEAM-HARDENED]=0 -> MUSS FAILEN.
    GREEN-Ziel: vorhanden (mindestens 1, erwartet 2: Block B + Block J).
    """
    text = _read(SDF_ORCH)

    has_m2_seam = "[M2-SEAM-HARDENED]" in text
    assert has_m2_seam, (
        "'[M2-SEAM-HARDENED]' Marker fehlt in _SDF_orchestrate.md — "
        "BL-468 Edit-Block B (STATE-MACHINE) + Edit-Block J (altmodischer-Pfad-Note) "
        "muessen '[M2-SEAM-HARDENED]' setzen. Dieser Marker dokumentiert: "
        "der altmodische Pfad ist jetzt OHNE Motor megaworker-sicher (state-getrieben). "
        "Der Seam haengt am STATE-HANDOFF, NICHT an motor_allowed/tdd_enabled (W11/W5). "
        "BL-468 AK-3 AE-2."
    )


# ── Kanarienvoegel/Charakterisierung (AK-2 + AK-4 — initial GREEN, duerfen NICHT brechen) ──

def test_ak2_berater_outputs_floor():
    """
    AK-2 / DoD-4 (Charakterisierung, initial GREEN): BERATER_OUTPUTS.-Referenzen
    muessen >= 11 in _SDF_orchestrate.md vorhanden sein.

    Regression-Lock: der GREEN-Edit darf KEINE bestehenden BERATER_OUTPUTS-Slots entfernen.
    RED-Baseline: BERATER_OUTPUTS.=13/16 Vorkommen (bereits GRUEN) -> darf NICHT fallen.
    GREEN-Ziel: >= 11 (Floor erhalten, Vorkommen-Zaehlung).

    Kanarienvogel: bricht wenn GREEN-Worker versehentlich einen Slot loescht.
    """
    text = _read(SDF_ORCH)

    berater_outputs_count = len(re.findall(r"BERATER_OUTPUTS\.", text))
    assert berater_outputs_count >= 11, (
        f"BERATER_OUTPUTS.-Referenzen unter Floor in _SDF_orchestrate.md — "
        f"gefunden: {berater_outputs_count} (erwartet: >= 11). "
        f"Ein bestehender BERATER_OUTPUTS-Slot wurde versehentlich entfernt (Regression). "
        f"BL-468 AK-2 Floor-Check: GREEN-Edit darf KEINE Slots loeschen, "
        f"nur additive Marker hinzufuegen (Edit-Blocks A-J sind alle additiv). "
        f"RED-Baseline: 16 Vorkommen (BERATER_OUTPUTS.testRun/analyse/modusEntscheidung_*/executionDispatch/...)."
    )


def test_ak4_motor_literals_intact():
    """
    AK-4 / DoD-4a (Charakterisierung, initial GREEN): Motor-Pfad-Literale muessen erhalten sein.

    RED-Baseline alle vorhanden (bereits GRUEN):
      - 'dispatch_implement': Count >= 4 (Z243/PHASE3-Kommentar/loop_decision-Block)
      - 'motor_allowed': Count >= 4 (Z221/Z224/Z241 + VEHIKEL-GATE)
      - 'VEHIKEL-GATE': Count >= 2 (Z217/Z222)
      - 'loop_decision': Count >= 9 (Z247-261, Routing-SWITCH)

    Kanarienvogel: bricht wenn Motor-Pfad durch GREEN-Edit veraendert wird (Regression).
    """
    text = _read(SDF_ORCH)

    dispatch_count = text.count("dispatch_implement")
    assert dispatch_count >= 4, (
        f"'dispatch_implement' Literal zu selten in _SDF_orchestrate.md — "
        f"gefunden: {dispatch_count} (erwartet: >= 4). "
        f"Motor-Pfad (Workflow(dispatch_implement)) wurde durch GREEN-Edit veraendert (Regression). "
        f"BL-468 AK-4 Regression-Sperre: dispatch_implement NICHT anfassen."
    )

    motor_allowed_count = text.count("motor_allowed")
    assert motor_allowed_count >= 4, (
        f"'motor_allowed' Literal zu selten in _SDF_orchestrate.md — "
        f"gefunden: {motor_allowed_count} (erwartet: >= 4). "
        f"VEHIKEL-GATE / Motor-Pfad wurde durch GREEN-Edit veraendert (Regression). "
        f"BL-468 AK-4 Regression-Sperre: motor_allowed NICHT anfassen."
    )

    vehikel_gate_count = text.count("VEHIKEL-GATE")
    assert vehikel_gate_count >= 2, (
        f"'VEHIKEL-GATE' Literal zu selten in _SDF_orchestrate.md — "
        f"gefunden: {vehikel_gate_count} (erwartet: >= 2). "
        f"VEHIKEL-GATE-Block (motor_allowed-Berechnung) wurde durch GREEN-Edit veraendert (Regression). "
        f"BL-468 AK-4 Regression-Sperre: VEHIKEL-GATE NICHT anfassen."
    )

    loop_decision_count = text.count("loop_decision")
    assert loop_decision_count >= 9, (
        f"'loop_decision' Literal zu selten in _SDF_orchestrate.md — "
        f"gefunden: {loop_decision_count} (erwartet: >= 9). "
        f"loop_decision-Routing-SWITCH wurde durch GREEN-Edit veraendert (Regression). "
        f"BL-468 AK-4 Regression-Sperre: loop_decision NICHT anfassen."
    )


def test_ak4_orchestrator_loads_not_spawn_marked():
    """
    AK-4 / DoD-4b (Charakterisierung, initial GREEN): KEIN [INV-SPAWN]-Marker an Orchestrator-Loads.

    Anti-Marker: Keine Zeile die sowohl '[INV-SPAWN]' als auch einen Orchestrator-Load enthaelt.
    Orchestrator-Loads (INV-AO-CALLER, Lead-Skill-Load-Pflicht, KEIN Agent()-Spawn):
      - _I_orchestrate
      - _SC_orchestrate
      - _IDF_orchestrate
      - _WP_orchestrate
      - _T_orchestrate
      - _smoothing
      - _presentation
      - dispatch_implement (Motor-Start, Workflow-Aufruf)

    RED-Baseline: [INV-SPAWN]=0 -> dieser Test ist heute GRUEN (keine False-Positives).
    GREEN-Ziel: bleibt GRUEN nach Edit-Blocks C..I (die nur _SDF_berater_*-Calls markieren duerfen).

    Load-bearing Anti-Marker: bricht wenn GREEN-Worker faelschlich einen Orchestrator mit [INV-SPAWN] markiert.
    """
    text = _read(SDF_ORCH)

    orchestrator_patterns = [
        "_I_orchestrate",
        "_SC_orchestrate",
        "_IDF_orchestrate",
        "_WP_orchestrate",
        "_T_orchestrate",
        "_smoothing",
        "_presentation",
        "dispatch_implement",
    ]

    for line in text.splitlines():
        if "[INV-SPAWN]" in line:
            for orch in orchestrator_patterns:
                assert orch not in line, (
                    f"[INV-SPAWN]-Marker an Orchestrator-Load '{orch}' gefunden in _SDF_orchestrate.md — "
                    f"Zeile: '{line.strip()}'. "
                    f"INV-AO-CALLER: Orchestrator-Loads sind Lead-Skill-Load-pflichtig, "
                    f"KEINE Agent()-Spawns, KEIN [INV-SPAWN]-Marker erlaubt. "
                    f"Nur _SDF_berater_*-Calls duerfen [INV-SPAWN]-markiert werden. "
                    f"BL-468 AK-4b Anti-Marker (SCOPE-NOTE Punkt (b) + Punkt (c))."
                )


def test_ak4_skip_literals_intact():
    """
    AK-4 / DoD-4c-4e (Charakterisierung, initial GREEN): Alle Skip-Literale muessen erhalten sein.

    Skip-Literale (RED-Baseline alle vorhanden):
      - 'N=1': N=1-Fast-Path (BL-365) -> Count >= 9 (Z118-168 Block)
      - 'STALE-HANDOFF': STALE-HANDOFF-RECOVERY -> Count >= 3 (Z179-199 Block)
      - 'single_batch': single_batch_path -> Count >= 1 (Z266)

    Kanarienvogel: bricht wenn eine konditionale Skip-Logik durch GREEN-Edit gebrochen wird.
    """
    text = _read(SDF_ORCH)

    n1_count = text.count("N=1")
    assert n1_count >= 9, (
        f"'N=1' Literal zu selten in _SDF_orchestrate.md — "
        f"gefunden: {n1_count} (erwartet: >= 9). "
        f"N=1-Fast-Path (BL-365, Z118-168) wurde durch GREEN-Edit entfernt (Regression). "
        f"BL-468 AK-4 Regression-Sperre: N=1-Fast-Path NICHT anfassen."
    )

    stale_handoff_count = text.count("STALE-HANDOFF")
    assert stale_handoff_count >= 3, (
        f"'STALE-HANDOFF' Literal zu selten in _SDF_orchestrate.md — "
        f"gefunden: {stale_handoff_count} (erwartet: >= 3). "
        f"STALE-HANDOFF-RECOVERY (Z179-199) wurde durch GREEN-Edit entfernt (Regression). "
        f"BL-468 AK-4 Regression-Sperre: STALE-HANDOFF-RECOVERY NICHT anfassen."
    )

    single_batch_count = text.count("single_batch")
    assert single_batch_count >= 1, (
        f"'single_batch' Literal fehlt in _SDF_orchestrate.md — "
        f"gefunden: {single_batch_count} (erwartet: >= 1). "
        f"single_batch-Pfad (Z265-266) wurde durch GREEN-Edit entfernt (Regression). "
        f"BL-468 AK-4 Regression-Sperre: single_batch NICHT anfassen."
    )
