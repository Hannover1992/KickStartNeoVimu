"""
BL-469: SDF-orchestrate-post contract-driven (Spawn-Haertung) — strukturelle pytest-Tests
RED-Worker: BL-469 batch_1 Slice 1 Iteration 1

Tests pruefen den Inhalt von .claude/commands/_SDF_orchestrate_post.md via grep/parse.
AK-1/AK-3-Tests MUESSEN JETZT FAILEN (RED) — Marker fehlen noch.
AK-2/AK-4-Tests sind Charakterisierung/Regression (initial GREEN, duerfen NICHT brechen).

Blueprint: BL-469_blueprint.md (Gold-Definition + RED!=GREEN-Trennung)
RED-Baseline (verifiziert 2026-06-24):
  [INV-SPAWN]=0, [GATE P]=0, ## STATE-MACHINE=0, ## WORKER-SPAWN-PATTERN=0,
  BERATER_OUTPUTS.=31, Skip-Literale {C5-SKIP=1, C7-SKIP=1, single_batch=2, not_last_round=1},
  tdd_enabled=0 (kein Gate), ANTI-MEGA=12.
"""

import re
from pathlib import Path

REPO_ROOT = Path("C:/Users/hanno/RiderProjects/OmniCommand-wtA")
COMMANDS_DIR = REPO_ROOT / ".claude" / "commands"

SDF_POST = COMMANDS_DIR / "_SDF_orchestrate_post.md"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ── RED-Hebel (AK-1): INV-SPAWN-Marker + WORKER-SPAWN-PATTERN ──────────────────

def test_ak1_inv_spawn_marker_count():
    """
    AK-1 / DoD-1 (RED): _SDF_orchestrate_post.md muss >= 9 [INV-SPAWN]-Marker enthalten.

    Blueprint: Edit-Blocks C..L setzen je 1 [INV-SPAWN]-Marker pro Phase-3.x-Call-Stelle.
    10 Marker geplant (9 distinct Berater + recalibrate doppelt).

    RED-Baseline: [INV-SPAWN]=0 → MUSS FAILEN.
    GREEN-Ziel: 10 Marker (>= 9 erfuellt).

    false-GREEN-Falle: Falls ein Marker ausversehen bereits existiert -> Test schlaegt
    fehl wegen Count=0. Nur Edit-Blocks C..L (BL-469) duerfen diese Marker setzen.
    """
    text = _read(SDF_POST)

    inv_spawn_count = text.count("[INV-SPAWN]")
    assert inv_spawn_count >= 9, (
        f"'[INV-SPAWN]' Phasen-Marker zu selten in _SDF_orchestrate_post.md — "
        f"gefunden: {inv_spawn_count} (erwartet: >= 9, je 1 fuer die 10 Phase-3.x-Call-Stellen). "
        f"BL-469 Edit-Blocks C..L muessen '[INV-SPAWN]'-Kommentar-Marker vor jedem Phase-3.x-Call einfuegen "
        f"(recalibrate=Z207+Z349, postItem=Z216, statusTransition=Z308, modelSync=Z318, "
        f"batchEnde=Z399, stageElevation=Z493, post_sc_pl_resync=Z671, loopDecision=Z696, orphan_scan=Z761)."
    )


def test_ak1_worker_spawn_pattern_block():
    """
    AK-1 / DoD-2+3 (RED): _SDF_orchestrate_post.md muss genau 1x '## WORKER-SPAWN-PATTERN'
    enthalten + der Block muss Agent()-Spawn-Schablone mit sdf-Team-Konvention und
    Worker-stirbt-Semantik deklarieren.

    Blueprint: Edit-Block A (nach ## VERTRAG, vor ## Aufruf) — 1:1 I-Pilot-Spiegel.

    RED-Baseline: ## WORKER-SPAWN-PATTERN=0 → MUSS FAILEN.
    GREEN-Ziel: Count==1 + Agent(subagent_type + team_name="sdf-" + Worker stirbt.
    """
    text = _read(SDF_POST)

    pattern_count = len(re.findall(r"^## WORKER-SPAWN-PATTERN", text, re.MULTILINE))
    assert pattern_count == 1, (
        f"'## WORKER-SPAWN-PATTERN' Block fehlt oder mehrfach in _SDF_orchestrate_post.md — "
        f"gefunden: {pattern_count} (erwartet: genau 1). "
        f"BL-469 Edit-Block A muss den WORKER-SPAWN-PATTERN-Header einfuegen "
        f"(nach ## VERTRAG-Block, vor ## Aufruf — 1:1 Spiegel I-Pilot _I_orchestrate.md Z689-733)."
    )

    has_agent_spawn = bool(re.search(r"Agent\(\s*subagent_type", text))
    assert has_agent_spawn, (
        "'Agent(subagent_type' fehlt in _SDF_orchestrate_post.md — "
        "der WORKER-SPAWN-PATTERN-Block muss ein Agent()-Spawn-Template mit subagent_type-Parameter "
        "enthalten (BL-469 Edit-Block A, SDF-Spawn-Schablone)."
    )

    has_sdf_team = 'team_name="sdf-' in text
    assert has_sdf_team, (
        "'team_name=\"sdf-' Konvention fehlt in _SDF_orchestrate_post.md — "
        "das Agent()-Template muss team_name=\"sdf-{NAME}\" als SDF-Team-Konvention "
        "deklarieren (BL-469 Edit-Block A, analog I-Pilot team_name=\"i-\")."
    )

    has_worker_stirbt = "Worker stirbt" in text
    assert has_worker_stirbt, (
        "'Worker stirbt' Semantik fehlt in _SDF_orchestrate_post.md — "
        "das WORKER-SPAWN-PATTERN muss die Kurzlebig-Worker-Semantik "
        "('Worker stirbt nach Skill-Ausfuehrung') explizit deklarieren (BL-469 Edit-Block A)."
    )


# ── RED-Hebel (AK-3): STATE-MACHINE + [GATE P] + exit_code=99 ─────────────────

def test_ak3_state_machine_block():
    """
    AK-3 / DoD-5 (RED): _SDF_orchestrate_post.md muss genau 1x '## STATE-MACHINE'
    enthalten.

    Blueprint: Edit-Block B (direkt nach Edit-Block A, vor ## Aufruf) — Transitions-Kette
    INIT -> BUILD_SANITY_DONE -> ... -> COMPLETED | ABORTED_PROCESS_VIOLATION.

    RED-Baseline: ## STATE-MACHINE=0 → MUSS FAILEN.
    GREEN-Ziel: Count==1.
    """
    text = _read(SDF_POST)

    state_machine_count = len(re.findall(r"^## STATE-MACHINE", text, re.MULTILINE))
    assert state_machine_count == 1, (
        f"'## STATE-MACHINE' Block fehlt oder mehrfach in _SDF_orchestrate_post.md — "
        f"gefunden: {state_machine_count} (erwartet: genau 1). "
        f"BL-469 Edit-Block B muss den STATE-MACHINE-Block einfuegen "
        f"(Transitions-Kette INIT->...->COMPLETED|ABORTED_PROCESS_VIOLATION, exit_code-Konvention, "
        f"[M2-SEAM-HARDENED]-Note — Spiegel _I_orchestrate.md Z633-665)."
    )


def test_ak3_gate_p_count():
    """
    AK-3 / DoD-6 (RED): _SDF_orchestrate_post.md muss >= 9 [GATE P]-Marker enthalten.

    Blueprint: Edit-Blocks C..L setzen je 1 [GATE P{N}] pro Phase-3.x-Uebergang.
    10 Gates geplant ([GATE P1]..[GATE P10]).

    RED-Baseline: [GATE P]=0 → MUSS FAILEN.
    GREEN-Ziel: 10 Gates (>= 9 erfuellt).

    AE-3 ([GATE P]-Semantik): == 99 ABORT statt != 0 (Skip-Toleranz fuer SDF-post-Skip-Dichte).
    """
    text = _read(SDF_POST)

    gate_count = text.count("[GATE P")
    assert gate_count >= 9, (
        f"'[GATE P' Marker zu selten in _SDF_orchestrate_post.md — "
        f"gefunden: {gate_count} (erwartet: >= 9). "
        f"BL-469 Edit-Blocks C..L muessen '[GATE P1]' bis '[GATE P10]' als State-Read-Marker "
        f"vor jedem Phase-3.x-Call einfuegen (AE-3: exit_code==99-ABORT-Semantik, "
        f"NOT != 0, wegen SDF-post-Skip-Dichte C5-SKIP/C7-SKIP/single_batch/not_last_round)."
    )


def test_ak3_exit_code_99_abort():
    """
    AK-3 / DoD-7 (RED): _SDF_orchestrate_post.md muss exit_code-99 + ABORTED_PROCESS_VIOLATION
    Konvention dokumentieren.

    Blueprint: Edit-Block B (STATE-MACHINE) muss exit_code=0=DONE, exit_code=2=modelSync-FAIL,
    exit_code=99=ABORTED_PROCESS_VIOLATION deklarieren. Literal 'exit_code' + '99' muss
    matchbar sein (re.search(r'exit_code.*99')).

    RED-Baseline: exit_code.*99=0 + ABORTED_PROCESS_VIOLATION=0 → MUSS FAILEN.
    GREEN-Ziel: beide vorhanden.
    """
    text = _read(SDF_POST)

    # Pruefe exit_code.*99 (tolerant: exit_code=99 oder exit_code == 99 oder exit_code==99)
    has_exit_code_99 = bool(re.search(r"exit_code[^\n]*99", text))
    if not has_exit_code_99:
        # Alternativer Check: exit_code auf einer Zeile, 99 auf naechster (mehrzeilig)
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if re.search(r"exit_code", line):
                context = "\n".join(lines[i:i + 3])
                if "99" in context and "ABORT" in context:
                    has_exit_code_99 = True
                    break

    assert has_exit_code_99, (
        "'exit_code' mit '99' Konvention fehlt in _SDF_orchestrate_post.md — "
        "der STATE-MACHINE-Block (Edit-Block B) muss exit_code=99 als ABORTED_PROCESS_VIOLATION "
        "deklarieren (neben exit_code=0=DONE + exit_code=2=modelSync-FAIL). "
        "Muster: re.search(r'exit_code[^\\n]*99', text) muss treffen (BL-469 AK-3 AE-3)."
    )

    has_aborted = "ABORTED_PROCESS_VIOLATION" in text
    assert has_aborted, (
        "'ABORTED_PROCESS_VIOLATION' fehlt in _SDF_orchestrate_post.md — "
        "der STATE-MACHINE-Block muss den ABORTED_PROCESS_VIOLATION Terminal-Zustand "
        "explizit benennen (exit_code=99, any phase). BL-469 Edit-Block B."
    )


# ── Kanarienvoegel/Charakterisierung (AK-2 + AK-4 — initial GREEN, duerfen NICHT brechen) ──

def test_ak2_berater_outputs_floor():
    """
    AK-2 / DoD-4 (Charakterisierung, initial GREEN): BERATER_OUTPUTS.-Referenzen
    muessen >= 31 in _SDF_orchestrate_post.md vorhanden sein.

    Regression-Lock: der GREEN-Edit darf KEINE bestehenden BERATER_OUTPUTS-Slots entfernen.
    RED-Baseline: BERATER_OUTPUTS.=31 (bereits GRUEN) → darf NICHT fallen.
    GREEN-Ziel: >= 31 (Floor erhalten).

    Kanarienvogel: bricht wenn GREEN-Worker versehentlich einen Slot loescht.
    """
    text = _read(SDF_POST)

    berater_outputs_count = len(re.findall(r"BERATER_OUTPUTS\.", text))
    assert berater_outputs_count >= 31, (
        f"BERATER_OUTPUTS.-Referenzen unter Floor in _SDF_orchestrate_post.md — "
        f"gefunden: {berater_outputs_count} (erwartet: >= 31). "
        f"Ein bestehender BERATER_OUTPUTS-Slot wurde versehentlich entfernt (Regression). "
        f"BL-469 AK-2 Floor-Check: GREEN-Edit darf KEINE Slots loeschen, "
        f"nur additive Marker hinzufuegen (Edit-Blocks A-N sind alle additiv)."
    )


def test_ak4_skip_literals_intact():
    """
    AK-4 / DoD-8a-8d (Charakterisierung, initial GREEN): Alle 4 konditionale Skip-Literale
    muessen unveraendert in _SDF_orchestrate_post.md vorhanden sein.

    Skip-Literale (RED-Baseline alle 1+/1+ vorhanden):
      - 'C5-SKIP': recalibrate M1-Skip (Z212) → Count >= 1
      - 'C7-SKIP': statusTransition gap_ready=false-Skip (Z310) → Count >= 1
      - 'single_batch': modelSync single_batch-Skip (Z316) → Count >= 2
      - 'not_last_round': batchEnde last-round-only-Skip (Z412) → Count >= 1

    Kanarienvogel: bricht wenn eine Skip-Logik durch GREEN-Edit gebrochen wird.
    """
    text = _read(SDF_POST)

    c5_count = text.count("C5-SKIP")
    assert c5_count >= 1, (
        f"'C5-SKIP' Literal fehlt oder zu selten in _SDF_orchestrate_post.md — "
        f"gefunden: {c5_count} (erwartet: >= 1). "
        f"recalibrate M1-Skip (Z212) wurde durch GREEN-Edit entfernt (Regression). "
        f"BL-469 AK-4 Regression-Sperre: C5-SKIP NICHT anfassen."
    )

    c7_count = text.count("C7-SKIP")
    assert c7_count >= 1, (
        f"'C7-SKIP' Literal fehlt oder zu selten in _SDF_orchestrate_post.md — "
        f"gefunden: {c7_count} (erwartet: >= 1). "
        f"statusTransition gap_ready=false-Skip (Z310) wurde durch GREEN-Edit entfernt (Regression). "
        f"BL-469 AK-4 Regression-Sperre: C7-SKIP NICHT anfassen."
    )

    single_batch_count = text.count("single_batch")
    assert single_batch_count >= 2, (
        f"'single_batch' Literal zu selten in _SDF_orchestrate_post.md — "
        f"gefunden: {single_batch_count} (erwartet: >= 2). "
        f"modelSync single_batch-Skip (Z316) wurde durch GREEN-Edit entfernt (Regression). "
        f"BL-469 AK-4 Regression-Sperre: single_batch NICHT anfassen."
    )

    not_last_round_count = text.count("not_last_round")
    assert not_last_round_count >= 1, (
        f"'not_last_round' Literal fehlt oder zu selten in _SDF_orchestrate_post.md — "
        f"gefunden: {not_last_round_count} (erwartet: >= 1). "
        f"batchEnde last-round-only-Skip (Z412) wurde durch GREEN-Edit entfernt (Regression). "
        f"BL-469 AK-4 Regression-Sperre: not_last_round NICHT anfassen."
    )


def test_ak4_no_tdd_gate_at_seam():
    """
    AK-4 / DoD-10 (Charakterisierung, initial GREEN): kein tdd_enabled-Gate am State-Seam.

    W12 [M2-SEAM-HARDENED]: Der Seam haengt am STATE-HANDOFF, NICHT an tdd_enabled.
    Modus-unabhaengig (M1-M8). tdd_enabled DARF NICHT als Gate am Seam eingefuegt werden.

    RED-Baseline: tdd_enabled=0 in _SDF_orchestrate_post.md (bereits korrekt GRUEN).
    GREEN-Ziel: bleibt 0 (kein tdd_enabled-Gate einfuegen).

    Kanarienvogel: bricht wenn GREEN-Worker versehentlich tdd_enabled-Gate einbaut.
    """
    text = _read(SDF_POST)

    tdd_enabled_count = text.count("tdd_enabled")
    assert tdd_enabled_count == 0, (
        f"'tdd_enabled' Gate in _SDF_orchestrate_post.md gefunden — "
        f"gefunden: {tdd_enabled_count} (erwartet: 0). "
        f"W12 [M2-SEAM-HARDENED]: Der State-Seam ist modus-unabhaengig (M1-M8). "
        f"Ein tdd_enabled-Gate macht den Seam modus-konditional → Megaworker-Regression. "
        f"BL-469 AK-4: tdd_enabled-Gate VERBOTEN in _SDF_orchestrate_post.md."
    )


def test_ak4_anti_mega_worker_intact():
    """
    AK-4 / DoD-11 (Charakterisierung, initial GREEN): ANTI-MEGA-WORKER-CHECK bleibt erhalten.

    Blueprint: Der post-hoc ANTI-MEGA-WORKER-CHECK ist nach AK-3 (STATE-MACHINE + [GATE P])
    der REDUNDANTE 2. Notnagel (Edit-Block N — Doku-Note einfuegen, NICHT entfernen).
    Count >= 12 erhalten + '2. Notnagel' oder '2. NOTNAGEL' vorhanden (nach GREEN).

    RED-Baseline: ANTI-MEGA-Count=12 (bereits GRUEN), '2. Notnagel'=0 (RED fuer diese Note).
    GREEN-Ziel: ANTI-MEGA >= 12 + '2. Notnagel' Note vorhanden.

    Kanarienvogel fuer ANTI-MEGA-Count: bricht wenn ANTI-MEGA-CHECK entfernt wird.
    Note-Pruefung: erst nach GREEN erfuellt (Edit-Block N).

    HINWEIS fuer RED-Phase: test prueft NUR den Count-Floor (>= 12) —
    das ist Charakterisierung (initial GREEN). Die Note-Assertion MUSS initial FAILEN
    damit der Test als Kanarienvogel dient (bricht bei Entfernung).
    """
    text = _read(SDF_POST)

    anti_mega_count = len(re.findall(r"ANTI-MEGA", text))
    assert anti_mega_count >= 12, (
        f"'ANTI-MEGA' Vorkommen unter Floor in _SDF_orchestrate_post.md — "
        f"gefunden: {anti_mega_count} (erwartet: >= 12). "
        f"Der ANTI-MEGA-WORKER-CHECK (2. Notnagel nach BL-469 AK-3) wurde entfernt (Regression). "
        f"BL-469 AK-4 Regression-Sperre: ANTI-MEGA-WORKER-CHECK NICHT anfassen "
        f"(Edit-Block N fuegt nur eine Doku-Note hinzu, KEINE Entfernung)."
    )
