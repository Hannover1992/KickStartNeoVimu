"""
BL-470: PostBatch-orchestrate contract-driven (Spawn-Haertung) — strukturelle pytest-Tests
RED-Worker: BL-470 batch_1 Slice 1 Iteration 1

Tests pruefen den Inhalt von .claude/commands/_PostBatch_orchestrate.md via grep/parse.
AK-1/AK-2/AK-3-Tests MUESSEN JETZT FAILEN (RED) — Marker fehlen noch.
AK-4-Tests sind Charakterisierung/Regression (initial GREEN, duerfen NICHT brechen).

Blueprint: BL-470_blueprint.md (Gold-Definition + RED!=GREEN-Trennung)
RED-Baseline (verifiziert 2026-06-25):
  [INV-SPAWN]=0, [GATE P]=0, ## STATE-MACHINE=0, ## WORKER-SPAWN-PATTERN=0,
  [M2-SEAM-HARDENED]=0, ABORTED_PROCESS_VIOLATION=0.
  BERATER_OUTPUTS.=4 Vorkommen, ABER 0 echte Slot-Deklarationen
    (alle 4 sind VERTRAG-negativ: reads/not_writes-Zeilen).
  Regression-Literale: {arch_dirty=5, tests_dirty=4, BDF_NEXT_TRIGGER=4, escalation_queued=6, INV-POSTBATCH-1=2}.
  Orchestrator-Loads: {_T_orchestrate=10, _stage_orchestrate=6, _I_cleanCodeArchitect=6}.
  LOC=211.
"""

import re
from pathlib import Path

REPO_ROOT = Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA")
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"

POSTBATCH_ORCH = COMMANDS_DIR / "_PostBatch_orchestrate.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── RED-Hebel (AK-1): INV-SPAWN-Marker + WORKER-SPAWN-PATTERN ──────────────────

def test_ak1_inv_spawn_marker_count():
    """
    AK-1 / DoD-1 (RED): _PostBatch_orchestrate.md muss >= 4 [INV-SPAWN]-Marker enthalten.

    Blueprint: Blocks C..F setzen je 1 [INV-SPAWN]-Marker pro Berater-Call-Stelle.
    4 Marker geplant: [INV-SPAWN] vor Z95/Z122/Z178/Z185.
    (ArchConformance, PatternConformance, garbageCollection, stateMaintain)

    RED-Baseline: [INV-SPAWN]=0 -> MUSS FAILEN.
    GREEN-Ziel: 4 Marker (>= 4 erfuellt).

    Verschachtelungs-Warnung (AE-5/W13): [INV-SPAWN] NUR vor Berater-Zeilen,
    NIEMALS vor _I_cleanCodeArchitect (Z104/Z132) — die KEIN [INV-SPAWN] kriegen duerfen.
    """
    text = _read(POSTBATCH_ORCH)

    inv_spawn_count = text.count("[INV-SPAWN]")
    assert inv_spawn_count >= 4, (
        f"'[INV-SPAWN]' Phasen-Marker zu selten in _PostBatch_orchestrate.md — "
        f"gefunden: {inv_spawn_count} (erwartet: >= 4, je 1 fuer die 4 Berater-Call-Stellen). "
        f"BL-470 Edit-Blocks C..F muessen '[INV-SPAWN]'-Kommentar-Marker vor jedem Berater-Call einfuegen "
        f"(C=Z95 ArchConformance, D=Z122 PatternConformance, E=Z178 garbageCollection, F=Z185 stateMaintain). "
        f"ACHTUNG: [INV-SPAWN] NIEMALS vor _I_cleanCodeArchitect-Zeilen (Z104/Z132) — "
        f"diese sind Orchestrator-Loads (INV-AO-CALLER), KEINE Berater-Spawns."
    )


def test_ak1_worker_spawn_pattern_block():
    """
    AK-1 / DoD-2+3 (RED): _PostBatch_orchestrate.md muss genau 1x '## WORKER-SPAWN-PATTERN'
    enthalten + der Block muss Agent()-Spawn-Schablone mit postbatch-Team-Konvention und
    Worker-stirbt-Semantik deklarieren.

    Blueprint: Edit-Block A (nach ## VERTRAG, vor ## Pipeline-Logik) — 1:1 BL-468-Schwester-Spiegel.

    RED-Baseline: ## WORKER-SPAWN-PATTERN=0 -> MUSS FAILEN.
    GREEN-Ziel: Count==1 + Agent(subagent_type + team_name="postbatch-" + "Worker stirbt".
    """
    text = _read(POSTBATCH_ORCH)

    pattern_count = len(re.findall(r"^## WORKER-SPAWN-PATTERN", text, re.MULTILINE))
    assert pattern_count == 1, (
        f"'## WORKER-SPAWN-PATTERN' Block fehlt oder mehrfach in _PostBatch_orchestrate.md — "
        f"gefunden: {pattern_count} (erwartet: genau 1). "
        f"BL-470 Edit-Block A muss den WORKER-SPAWN-PATTERN-Header einfuegen "
        f"(nach ## VERTRAG-Block Zeile Z67, vor ## Pipeline-Logik Z69 — "
        f"1:1 Spiegel BL-468-Schwester _SDF_orchestrate.md)."
    )

    has_agent_spawn = bool(re.search(r"Agent\(\s*subagent_type", text))
    assert has_agent_spawn, (
        "'Agent(subagent_type' fehlt in _PostBatch_orchestrate.md — "
        "der WORKER-SPAWN-PATTERN-Block muss ein Agent()-Spawn-Template mit subagent_type-Parameter "
        "enthalten (BL-470 Edit-Block A, PostBatch-Spawn-Schablone)."
    )

    has_postbatch_team = 'team_name="postbatch-' in text
    assert has_postbatch_team, (
        "'team_name=\"postbatch-' Konvention fehlt in _PostBatch_orchestrate.md — "
        "das Agent()-Template muss team_name=\"postbatch-{NAME}\" als PostBatch-Team-Konvention "
        "deklarieren (BL-470 Edit-Block A, analog BL-468-Schwester team_name=\"sdf-\")."
    )

    has_worker_stirbt = "Worker stirbt nach Skill-Ausfuehrung" in text
    assert has_worker_stirbt, (
        "'Worker stirbt nach Skill-Ausfuehrung' Semantik fehlt in _PostBatch_orchestrate.md — "
        "das WORKER-SPAWN-PATTERN muss die Kurzlebig-Worker-Semantik "
        "('Worker stirbt nach Skill-Ausfuehrung') explizit deklarieren (BL-470 Edit-Block A)."
    )


def test_ak1_spawn_template_present():
    """
    AK-1 / DoD-3 (RED): Agent()-Spawn-Schablone enthaelt subagent_type + team_name="postbatch-"
    + "Worker stirbt" — prueft kumulativ, ob das WORKER-SPAWN-PATTERN eine vollstaendige
    Schablone mit allen 3 Pflicht-Literalen (BL-470 Blueprint Block A) enthaelt.

    RED-Baseline: alle 3 Literale fehlen -> MUSS FAILEN (implizit von test_ak1_worker_spawn_pattern_block
    abgedeckt, aber als eigenstaendiger Test fuer Klarheit).
    GREEN-Ziel: alle 3 Literale vorhanden.
    """
    text = _read(POSTBATCH_ORCH)

    # Kombinierter Test: alle 3 Komponenten der Spawn-Schablone muessen vorhanden sein
    missing = []
    if not bool(re.search(r"Agent\(\s*subagent_type", text)):
        missing.append("'Agent(subagent_type' (Agent()-Spawn-Template)")
    if 'team_name="postbatch-' not in text:
        missing.append("'team_name=\"postbatch-' (PostBatch-Team-Konvention)")
    if "Worker stirbt nach Skill-Ausfuehrung" not in text:
        missing.append("'Worker stirbt nach Skill-Ausfuehrung' (Kurzlebig-Semantik)")

    assert not missing, (
        f"Agent-Schablonen-Signatur unvollstaendig in _PostBatch_orchestrate.md — "
        f"fehlende Komponenten: {missing}. "
        f"BL-470 Edit-Block A muss eine vollstaendige Spawn-Schablone mit allen 3 Literalen "
        f"im WORKER-SPAWN-PATTERN-Block deklarieren."
    )


def test_ak1_scope_note_two_call_classes():
    """
    AK-1 / DoD-4 (RED): SCOPE-NOTE muss die 2 Call-Klassen + NICHT-Targets explizit benennen.

    Blueprint: SCOPE-NOTE in Block A (BL-470-Spezifikum, AK-1/AK-4-KRITISCH — Verschachtelungs-Warning):
    (a) Berater-Spawns (4, INV-SPAWN-Targets):
        _PostBatch_ArchConformance, _PostBatch_PatternConformance,
        _SDF_berater_garbageCollection, _SDF_berater_stateMaintain
    (b) Orchestrator-Handschuh-Loads (KEIN [INV-SPAWN], INV-AO-CALLER):
        _T_orchestrate, _stage_orchestrate, _I_cleanCodeArchitect (ALLE 3 NICHT-Targets!)
    (c) Motor-Start: ENTFAELLT (PostBatch hat keinen Workflow()-Aufruf)

    Der Test prueft: SCOPE-NOTE vorhanden + alle 4 Berater-Spawn-Targets + alle 3 Orchestrator-NICHT-Targets genannt.

    RED-Baseline: SCOPE-NOTE=0 -> MUSS FAILEN.
    GREEN-Ziel: SCOPE-NOTE + alle 4 Targets + alle 3 NICHT-Targets vorhanden.
    """
    text = _read(POSTBATCH_ORCH)

    has_scope_note = "SCOPE-NOTE" in text
    assert has_scope_note, (
        "'SCOPE-NOTE' fehlt in _PostBatch_orchestrate.md — "
        "Block A muss eine SCOPE-NOTE einfuegen, die die 2 Call-Klassen explizit benennt: "
        "(a) 4 Berater-Spawn-Targets (_PostBatch_ArchConformance, _PostBatch_PatternConformance, "
        "_SDF_berater_garbageCollection, _SDF_berater_stateMaintain), "
        "(b) 3 Orchestrator-Handschuh-Loads (KEIN [INV-SPAWN], INV-AO-CALLER: _T_orchestrate, "
        "_stage_orchestrate, _I_cleanCodeArchitect), "
        "(c) Motor-Start: ENTFAELLT (PostBatch ruft kein Workflow()). "
        "BL-470 Edit-Block A, AK-1/AK-4-KRITISCH + Verschachtelungs-Warning."
    )

    # Pruefe alle 4 Berater-Spawn-Targets (SCOPE-NOTE muss sie alle nennen)
    spawn_targets = [
        "_PostBatch_ArchConformance",
        "_PostBatch_PatternConformance",
        "_SDF_berater_garbageCollection",
        "_SDF_berater_stateMaintain",
    ]
    missing_targets = [t for t in spawn_targets if t not in text]
    assert not missing_targets, (
        f"SCOPE-NOTE Spawn-Targets nicht vollstaendig in _PostBatch_orchestrate.md — "
        f"fehlende Targets: {missing_targets}. "
        f"BL-470 Edit-Block A SCOPE-NOTE muss alle 4 Berater-Spawn-Targets explizit benennen "
        f"(ArchConformance/PatternConformance/garbageCollection/stateMaintain). BL-470 AK-1d."
    )

    # Pruefe alle 3 Orchestrator-NICHT-Targets (SCOPE-NOTE muss sie als NICHT-Spawn-Targets benennen)
    # _T_orchestrate + _stage_orchestrate + _I_cleanCodeArchitect muessen alle im Text sein
    # (schon heute vorhanden als Load-Calls; hier pruefen wir ob SCOPE-NOTE sie als NICHT-Ziele deklariert)
    # Der Haupt-RED-Hebel ist SCOPE-NOTE fehlt (oben); zusaetzlich pruefe die 3 Orchestrator-Keywords
    orchestrator_anti_targets = [
        "_T_orchestrate",
        "_stage_orchestrate",
        "_I_cleanCodeArchitect",
    ]
    missing_orch = [o for o in orchestrator_anti_targets if o not in text]
    assert not missing_orch, (
        f"Orchestrator-NICHT-Target-Referenzen fehlen in _PostBatch_orchestrate.md — "
        f"fehlende Keywords: {missing_orch}. "
        f"SCOPE-NOTE Block A muss _T_orchestrate/_stage_orchestrate/_I_cleanCodeArchitect als "
        f"NICHT-Spawn-Ziele (INV-AO-CALLER) explizit benennen. "
        f"BL-470 Edit-Block A Punkt (b): Orchestrator-NICHT-Targets."
    )


# ── RED-Hebel (AK-2): BERATER_OUTPUTS echte Slot-Deklarationen ──────────────────

def test_ak2_berater_slots_declared():
    """
    AK-2 / DoD-4a (RED): _PostBatch_orchestrate.md muss >= 4 echte BERATER_OUTPUTS-Slot-Deklarationen
    fuer die 4 Berater enthalten (NEUE Slots, NICHT die VERTRAG-negativen Zeilen).

    Blueprint: Die 4 neuen echten Slots sind:
      BERATER_OUTPUTS.archConformance, BERATER_OUTPUTS.patternConformance,
      BERATER_OUTPUTS.garbageCollection, BERATER_OUTPUTS.stateMaintain

    RED-Baseline: 4 BERATER_OUTPUTS.-Vorkommen, aber ALLE VERTRAG-negativ (reads/not_writes-Kontext).
    KEIN einziger echter {archConformance|patternConformance|garbageCollection|stateMaintain}-Slot existiert heute.
    -> MUSS FAILEN.

    HINWEIS: Test zaehlt ECHTE neue Slots via Regex-Suche nach den 4 distinct Slot-Namen.
    VERTRAG-negativ-Zeilen (reads BERATER_OUTPUTS.executionDispatch / SCHREIBT NICHT BERATER_OUTPUTS.*)
    enthalten NICHT diese 4 Slot-Namen -> kein False-Positive.
    GREEN-Ziel: alle 4 distinct Slot-Namen >= 1x vorhanden (Summe >= 4 distinct).
    """
    text = _read(POSTBATCH_ORCH)

    # Die 4 echten neuen Slot-Namen (durch GREEN-Edit eingefuehrt, heute=0)
    new_slot_names = [
        "BERATER_OUTPUTS.archConformance",
        "BERATER_OUTPUTS.patternConformance",
        "BERATER_OUTPUTS.garbageCollection",
        "BERATER_OUTPUTS.stateMaintain",
    ]

    found_slots = [slot for slot in new_slot_names if slot in text]
    missing_slots = [slot for slot in new_slot_names if slot not in text]

    assert len(found_slots) >= 4, (
        f"Echte BERATER_OUTPUTS-Slot-Deklarationen fehlen in _PostBatch_orchestrate.md — "
        f"gefunden: {len(found_slots)}/4 echte Slots (erwartet: alle 4). "
        f"Fehlende Slots: {missing_slots}. "
        f"BL-470 AK-2: NEUE Slot-Deklarationen fuer die 4 Berater-Spawns (Block A+B). "
        f"HINWEIS: Heute existieren 4 BERATER_OUTPUTS.-Vorkommen (Z12/Z18/Z48/Z56), "
        f"aber ALLE sind VERTRAG-negativ (reads executionDispatch / SCHREIBT NICHT .*). "
        f"KEIN einziger dieser 4 Slot-Namen ist heute vorhanden -> RED korrekt."
    )


# ── RED-Hebel (AK-3): STATE-MACHINE + [GATE P] + exit_code=99 + [M2-SEAM-HARDENED] ──────────────

def test_ak3_state_machine_block():
    """
    AK-3 / DoD-5 (RED): _PostBatch_orchestrate.md muss genau 1x '## STATE-MACHINE'
    enthalten (Bindestrich-Form, Grossbuchstaben).

    Blueprint: Edit-Block B (direkt nach Edit-Block A, vor ## Pipeline-Logik Z69) — Spiegel BL-468-Schwester.
    Transitions-Kette: INIT -> ARCH_CONF_DONE -> PATTERN_CONF_DONE -> GC_DONE ->
    STATEMAINTAIN_DONE -> COMPLETED | ABORTED_PROCESS_VIOLATION.

    RED-Baseline: ## STATE-MACHINE=0 -> MUSS FAILEN.
    GREEN-Ziel: Count==1.

    Header-Disambiguierung (BL-470-Spezifikum): PostBatch hat heute KEINEN ## State Machine-Header
    (im Gegensatz zu _SDF_orchestrate.md Z77) -> noch klarer als BL-468.
    Neuer Block heisst EXAKT '## STATE-MACHINE' (Bindestrich, Grossbuchstaben, kein Suffix).
    """
    text = _read(POSTBATCH_ORCH)

    state_machine_count = len(re.findall(r"^## STATE-MACHINE$", text, re.MULTILINE))
    assert state_machine_count == 1, (
        f"'## STATE-MACHINE' Block (Bindestrich-Form, exakter Match) fehlt oder mehrfach "
        f"in _PostBatch_orchestrate.md — "
        f"gefunden: {state_machine_count} (erwartet: genau 1). "
        f"BL-470 Edit-Block B muss '## STATE-MACHINE' (EXAKT, Bindestrich, Grossbuchstaben, kein Suffix) "
        f"einfuegen (direkt nach Block A, vor ## Pipeline-Logik Z69). "
        f"Transitions-Kette: INIT -> ARCH_CONF_DONE -> PATTERN_CONF_DONE -> GC_DONE -> "
        f"STATEMAINTAIN_DONE -> COMPLETED | ABORTED_PROCESS_VIOLATION."
    )


def test_ak3_gate_p_count():
    """
    AK-3 / DoD-6 (RED): _PostBatch_orchestrate.md muss >= 4 [GATE P]-Marker enthalten.

    Blueprint: Edit-Blocks C..F setzen je 1 [GATE P{N}] pro Berater-Call-Stelle.
    4 Gates geplant ([GATE P1]..[GATE P4]).

    RED-Baseline: [GATE P]=0 -> MUSS FAILEN.
    GREEN-Ziel: 4 Gates (>= 4 erfuellt).

    AE-3 ([GATE P]-Semantik, 1:1 BL-468-Schwester AE-3): == 99 ABORT statt != 0 (Skip-Toleranz fuer
    ArchConformance-EMPTY_SEED-Graceful-Skip + garbageCollection-"kein Bloat"-SKIP).
    Tabelle: C=P1(ArchConformance Z95), D=P2(PatternConformance Z122),
             E=P3(garbageCollection Z178), F=P4(stateMaintain Z185).
    """
    text = _read(POSTBATCH_ORCH)

    gate_count = text.count("[GATE P")
    assert gate_count >= 4, (
        f"'[GATE P' Marker zu selten in _PostBatch_orchestrate.md — "
        f"gefunden: {gate_count} (erwartet: >= 4). "
        f"BL-470 Edit-Blocks C..F muessen '[GATE P1]' bis '[GATE P4]' als State-Read-Marker "
        f"vor jedem Berater-Call einfuegen (AE-3: exit_code==99-ABORT-Semantik, "
        f"NOT != 0, wegen EMPTY_SEED-Graceful-Skip / garbageCollection-kein-Bloat-SKIP). "
        f"Tabelle: C=P1(ArchConf Z95), D=P2(PatternConf Z122), "
        f"E=P3(garbageCollection Z178), F=P4(stateMaintain Z185)."
    )


def test_ak3_exit_code_99_abort():
    """
    AK-3 / DoD-7 (RED): _PostBatch_orchestrate.md muss exit_code-99 + ABORTED_PROCESS_VIOLATION
    Konvention dokumentieren.

    Blueprint: Edit-Block B (STATE-MACHINE) muss exit_code=0=DONE, exit_code=2=FAIL,
    exit_code=99=ABORTED_PROCESS_VIOLATION deklarieren. Literal 'exit_code' + '99' matchbar.

    RED-Baseline: exit_code.*99=0 + ABORTED_PROCESS_VIOLATION=0 -> MUSS FAILEN.
    GREEN-Ziel: beide vorhanden.

    Hinweis: Bestehende Datei hat KEIN exit_code-99-Literal (exit_code nur in Pipeline-Logik
    implizit via T_ORCHESTRATE_STATE-Checks). ABORTED_PROCESS_VIOLATION existiert NICHT (nur
    "FAIL"/"false"-Terminierung). Beides kommt ausschliesslich durch Block B hinzu.
    """
    text = _read(POSTBATCH_ORCH)

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
        "'exit_code' mit '99' Konvention fehlt in _PostBatch_orchestrate.md — "
        "der STATE-MACHINE-Block (Edit-Block B) muss exit_code=99 als ABORTED_PROCESS_VIOLATION "
        "deklarieren (neben exit_code=0=DONE + exit_code=2=FAIL). "
        "Muster: re.search(r'exit_code[^\\n]*99', text) muss treffen (BL-470 AK-3 AE-3)."
    )

    has_aborted_process = "ABORTED_PROCESS_VIOLATION" in text
    assert has_aborted_process, (
        "'ABORTED_PROCESS_VIOLATION' fehlt in _PostBatch_orchestrate.md — "
        "der STATE-MACHINE-Block muss den ABORTED_PROCESS_VIOLATION Terminal-Zustand "
        "explizit benennen (exit_code=99, any phase). BL-470 Edit-Block B. "
        "Hinweis: Bestehende Datei enthaelt NUR 'FAIL'/'false'-Terminierung "
        "— 'ABORTED_PROCESS_VIOLATION' existiert heute gar nicht."
    )


def test_ak3_m2_seam_hardened():
    """
    AK-3 / DoD-8 (RED): _PostBatch_orchestrate.md muss [M2-SEAM-HARDENED]-Marker enthalten.

    Blueprint: Edit-Block B (STATE-MACHINE) muss '[M2-SEAM-HARDENED]' + KEIN-Motor-Note setzen:
    "Transitions-Kette haengt am STATE-HANDOFF, NICHT an arch_dirty/tests_dirty/escalation_queued-Branch-Flag.
    KEIN Motor -> der State-Seam ist der EINZIGE Megaworker-Schutz"
    (BL-468 hatte Motor als zweiten Schutz; PostBatch NICHT).

    RED-Baseline: [M2-SEAM-HARDENED]=0 -> MUSS FAILEN.
    GREEN-Ziel: vorhanden (mindestens 1, Block B).
    """
    text = _read(POSTBATCH_ORCH)

    has_m2_seam = "[M2-SEAM-HARDENED]" in text
    assert has_m2_seam, (
        "'[M2-SEAM-HARDENED]' Marker fehlt in _PostBatch_orchestrate.md — "
        "BL-470 Edit-Block B (STATE-MACHINE) muss '[M2-SEAM-HARDENED]' setzen + "
        "KEIN-Motor-Note: 'KEIN Motor -> der State-Seam ist der EINZIGE Megaworker-Schutz'. "
        "(BL-468/SDF hatte den Motor als zweiten Schutz; PostBatch NICHT -> "
        "die STATE-MACHINE ist der EINZIGE Trenner, darum explizit markiert). "
        "BL-470 AK-3 AE-2."
    )


# ── Kanarienvoegel/Charakterisierung (AK-4 — initial GREEN, duerfen NICHT brechen) ──

def test_ak4_conformance_literals_intact():
    """
    AK-4 / DoD-4a (Charakterisierung, initial GREEN): Konformanz-Literale muessen erhalten sein.

    RED-Baseline alle vorhanden (bereits GRUEN):
      - 'arch_dirty': Count >= 5 (Z154/Z155/Z157)
      - 'tests_dirty': Count >= 4 (Z155/Z157/Z160)
      - 'BDF_NEXT_TRIGGER': Count >= 4 (Z55/Z192/Z193/Z194)
      - 'POSTBATCH_PIPELINE_STATE': Count >= 5 (mehrfach Manifest-Write-Zeilen)

    Kanarienvogel: bricht wenn Conformance-/BDF-Logik durch GREEN-Edit entfernt wird (Regression).
    """
    text = _read(POSTBATCH_ORCH)

    arch_dirty_count = text.count("arch_dirty")
    assert arch_dirty_count >= 5, (
        f"'arch_dirty' Literal zu selten in _PostBatch_orchestrate.md — "
        f"gefunden: {arch_dirty_count} (erwartet: >= 5). "
        f"ArchConformance-Re-Run-Gate (Z154/Z155/Z157) wurde durch GREEN-Edit entfernt (Regression). "
        f"BL-470 AK-4 Regression-Sperre: arch_dirty NICHT anfassen."
    )

    tests_dirty_count = text.count("tests_dirty")
    assert tests_dirty_count >= 4, (
        f"'tests_dirty' Literal zu selten in _PostBatch_orchestrate.md — "
        f"gefunden: {tests_dirty_count} (erwartet: >= 4). "
        f"PatternConformance-Re-Run-Gate (Z155/Z157/Z160) wurde durch GREEN-Edit entfernt (Regression). "
        f"BL-470 AK-4 Regression-Sperre: tests_dirty NICHT anfassen."
    )

    bdf_count = text.count("BDF_NEXT_TRIGGER")
    assert bdf_count >= 4, (
        f"'BDF_NEXT_TRIGGER' Literal zu selten in _PostBatch_orchestrate.md — "
        f"gefunden: {bdf_count} (erwartet: >= 4). "
        f"SCHRITT 5 BDF-Freigabe wurde durch GREEN-Edit entfernt (Regression). "
        f"BL-470 AK-4 Regression-Sperre: BDF_NEXT_TRIGGER NICHT anfassen."
    )

    postbatch_state_count = text.count("POSTBATCH_PIPELINE_STATE")
    assert postbatch_state_count >= 5, (
        f"'POSTBATCH_PIPELINE_STATE' Literal zu selten in _PostBatch_orchestrate.md — "
        f"gefunden: {postbatch_state_count} (erwartet: >= 5). "
        f"POSTBATCH_PIPELINE_STATE-Slot-Writes wurden durch GREEN-Edit entfernt (Regression). "
        f"BL-470 AK-4 Regression-Sperre: POSTBATCH_PIPELINE_STATE NICHT anfassen."
    )


def test_ak4_orchestrator_loads_not_spawn_marked():
    """
    AK-4 / DoD-4b (Charakterisierung, initial GREEN): KEIN [INV-SPAWN]-Marker an Orchestrator-Loads.

    Anti-Marker: Keine Zeile die sowohl '[INV-SPAWN]' als auch einen Orchestrator-Load enthaelt.
    Orchestrator-Loads (INV-AO-CALLER, Lead-Skill-Load-Pflicht, KEIN Agent()-Spawn):
      - _T_orchestrate (SCHRITT 1 Z78 + Re-Run-2 Z158)
      - _stage_orchestrate (SCHRITT 2 Z166)
      - _I_cleanCodeArchitect (SCHRITT 1.3 Z104 + SCHRITT 1.5 Z132 — VERSCHACHTELT!)

    RED-Baseline: [INV-SPAWN]=0 -> dieser Test ist heute GRUEN (keine False-Positives).
    GREEN-Ziel: bleibt GRUEN nach Edit-Blocks C..F (die nur Berater-Calls markieren duerfen).

    KRITISCH (AE-5/W13, VERSCHACHTELUNG): _I_cleanCodeArchitect (Z104/Z132) steht im SELBEN
    IF-Branch wie ArchConformance/PatternConformance (Z95/Z122). Marker MUSS ZEILEN-GENAU
    NUR vor Z95/Z122 gesetzt werden, NIEMALS vor Z104/Z132.
    Load-bearing Anti-Marker: bricht wenn GREEN-Worker faelschlich cleanCodeArchitect mit [INV-SPAWN] markiert.
    """
    text = _read(POSTBATCH_ORCH)

    orchestrator_patterns = [
        "_T_orchestrate",
        "_stage_orchestrate",
        "_I_cleanCodeArchitect",
    ]

    for line in text.splitlines():
        if "[INV-SPAWN]" in line:
            for orch in orchestrator_patterns:
                assert orch not in line, (
                    f"[INV-SPAWN]-Marker an Orchestrator-Load '{orch}' gefunden in "
                    f"_PostBatch_orchestrate.md — "
                    f"Zeile: '{line.strip()}'. "
                    f"INV-AO-CALLER: Orchestrator-Loads sind Lead-Skill-Load-pflichtig, "
                    f"KEINE Agent()-Spawns, KEIN [INV-SPAWN]-Marker erlaubt. "
                    f"Nur _PostBatch_ArchConformance/_PostBatch_PatternConformance/"
                    f"_SDF_berater_garbageCollection/_SDF_berater_stateMaintain "
                    f"duerfen [INV-SPAWN]-markiert werden. "
                    f"BL-470 AK-4b Anti-Marker (Verschachtelungs-Warning AE-5/W13)."
                )

    # Zusaetzlicher ZEILEN-genauer Check: pruefe auch die UNMITTELBAR VORANGEHENDE
    # Kommentar-Zeile jeder Orchestrator-Zeile — kein [INV-SPAWN] im Kommentar davor
    lines = text.splitlines()
    for i, line in enumerate(lines):
        for orch in orchestrator_patterns:
            if orch in line:
                # Pruefe die 1-2 Zeilen davor auf [INV-SPAWN]
                for prev_offset in [1, 2]:
                    if i >= prev_offset:
                        prev_line = lines[i - prev_offset]
                        assert "[INV-SPAWN]" not in prev_line or (
                            # Toleranz: nur wenn ein anderer Berater auch in der Vorherzeile ist
                            # (kein legitimer Fall, da Marker direkt vor dem Call steht)
                            any(b in prev_line for b in [
                                "_PostBatch_ArchConformance",
                                "_PostBatch_PatternConformance",
                                "_SDF_berater_garbageCollection",
                                "_SDF_berater_stateMaintain",
                            ])
                        ), (
                            f"[INV-SPAWN]-Marker {prev_offset} Zeile(n) vor Orchestrator '{orch}' "
                            f"gefunden in _PostBatch_orchestrate.md — "
                            f"Orchestrator-Zeile: '{line.strip()}', "
                            f"Vorher-Zeile ({prev_offset}): '{prev_line.strip()}'. "
                            f"ZEILEN-GENAU: [INV-SPAWN] muss DIREKT vor Berater-Call stehen, "
                            f"NICHT vor der verschachtelten Orchestrator-Zeile "
                            f"(VERSCHACHTELUNGS-WARNUNG AE-5/W13, BL-470)."
                        )


def test_ak4_inv_postbatch_1_intact():
    """
    AK-4 / DoD-4d (Charakterisierung, initial GREEN): INV-POSTBATCH-1 muss erhalten sein.

    RED-Baseline vorhanden (bereits GRUEN):
      - 'INV-POSTBATCH-1': Count >= 2 (Z64 VERTRAG-Box + Z207 Nachtext-Abschnitt)

    Kanarienvogel: bricht wenn INV-POSTBATCH-1-Invariante durch GREEN-Edit entfernt wird.
    INV-POSTBATCH-1 = kein git/gh/Shell inline (AK-13, BL-133).
    """
    text = _read(POSTBATCH_ORCH)

    inv_count = text.count("INV-POSTBATCH-1")
    assert inv_count >= 2, (
        f"'INV-POSTBATCH-1' Literal zu selten in _PostBatch_orchestrate.md — "
        f"gefunden: {inv_count} (erwartet: >= 2). "
        f"INV-POSTBATCH-1 (kein git/gh/Shell inline, AK-13/BL-133) wurde durch GREEN-Edit entfernt "
        f"oder beschaedigt (Regression). "
        f"BL-470 AK-4d Regression-Sperre: INV-POSTBATCH-1 NICHT anfassen."
    )

    # Zusaetzlich: kein neues git/gh-Inline durch GREEN-Edit eingefuehrt
    lines = text.splitlines()
    for line in lines:
        # Pruefe auf echte Shell-/git-Calls (kein Kommentar-Kontext-Artefakt)
        stripped = line.strip()
        if stripped.startswith("#") or stripped.startswith("//"):
            # Kommentar-Zeile: erlaubt zu erwaehnen
            continue
        # Kein direkt ausfuehrbares git/gh in Pipeline-Logik (ausser innerhalb Code-Bloecken die Kommentare enthalten)
        # Toleranter Check: nur offensichtliche Inline-Shell-Calls flaggen
        for shell_pattern in ["git push", "git commit", "gh pr", "gh release"]:
            assert shell_pattern not in stripped.lower() or "kein" in stripped.lower() or "NICHT" in stripped, (
                f"Moeglicher Inline-Shell-Call '{shell_pattern}' in _PostBatch_orchestrate.md gefunden — "
                f"Zeile: '{stripped}'. "
                f"INV-POSTBATCH-1 verbietet git/gh/Shell inline (AK-13/BL-133). "
                f"Falls dies ein Kommentar-Kontext ist, bitte pruefen."
            )
