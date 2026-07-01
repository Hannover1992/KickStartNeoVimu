---
status: NEU v1.0
version: 1.0
created: 2026-04-25
type: orchestrator
chain_position: BATCH-Qualitaet-nach-Item-Loop
ceiling: sonnet
floor: sonnet
contract:
  reads:
    - {file: "_manifest.md", path: "DF_PIPELINE_STATE.batch_current", purpose: "Welcher Batch fertig"}
    - {file: "_manifest.md", path: "BERATER_OUTPUTS.executionDispatch", purpose: "Was wurde im Batch gemacht"}
    - {file: "_session_params.md", path: "tdd_stages", purpose: "Welche Test-Stufen fuer T-Orchestrator"}
  writes:
    - {file: "_manifest.md", path: "POSTBATCH_PIPELINE_STATE", purpose: "Eigener State-Slot"}
    - {file: "_manifest.md", path: "DF_PIPELINE_STATE.BDF_NEXT_TRIGGER", value: "true", purpose: "BDF darf naechsten Batch holen"}
  not_writes:
    - {file: "_manifest.md", path: "BERATER_OUTPUTS.*", excluding: "(none — schreibt KEINE Berater-Slots)"}
  calls:
    - {skill: "_T_orchestrate", purpose: "Test-Stufen-Verifikation post-Batch"}
    - {skill: "_stage_orchestrate", purpose: "Commit-Stage nach Tests"}
related:
  - _PrePhase_orchestrate (Schwester-Wrapper PRE-Item)
  - _SDF_PostBerater_orchestrate (laeuft NACH PostBatch)
  - _Post_orchestrate (FEATURE-Ende, NICHT Schwester sondern andere Ebene)
absorbs: [BL-041 Phasen 4-7 SDF-Inline]
---

# _PostBatch_orchestrate — BATCH-Qualitaet nach Item-Loop

## Zweck

Dieser Command laeuft nach Abschluss des Batch-Item-Loops — wenn alle Items eines Batches
durch die Berater-Pipeline gelaufen sind. Er stellt sicher, dass Tests gruen sind und der
Batch korrekt committed wird, bevor BDF den naechsten Batch holen darf.

Aufruf-Reihenfolge: SDF Item-Loop DONE → **_PostBatch_orchestrate** → _SDF_PostBerater_orchestrate
(Housekeeping) → bei Feature-Ende: _Post_orchestrate.

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _PostBatch_orchestrate v1.0                                ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:   _manifest.md                                               ║
║             DF_PIPELINE_STATE.batch_current                          ║
║             BERATER_OUTPUTS.executionDispatch                        ║
║           _session_params.md                                         ║
║             tdd_stages                                               ║
║  SCHREIBT: _manifest.md                                              ║
║             POSTBATCH_PIPELINE_STATE.batch_done                      ║
║             POSTBATCH_PIPELINE_STATE.t_state                         ║
║             POSTBATCH_PIPELINE_STATE.stage_state                     ║
║             DF_PIPELINE_STATE.BDF_NEXT_TRIGGER = true                ║
║  SCHREIBT NICHT: BERATER_OUTPUTS.*  (kein Berater-Slot)              ║
║  RUFT AUF: _T_orchestrate,                                            ║
║    _PostBatch_ArchConformance (BL-154, AK-3-1, SCHRITT 1.3),          ║
║    _PostBatch_PatternConformance (M-4, AK-B-5, SCHRITT 1.5),          ║
║    _stage_orchestrate, _SDF_berater_garbageCollection,                 ║
║    _SDF_berater_stateMaintain,                                          ║
║    _I_cleanCodeArchitect (--mode impact-check, nur bei                  ║
║      escalation_queued=true, ARCH-7)                                    ║
║  INV-POSTBATCH-1: Enthaelt NUR Skill-Calls, KEINE Inline-Logik       ║
║    (kein git-push, kein gh, kein Shell — AK-13, BL-133)             ║
╚══════════════════════════════════════════════════════════════════════╝
```

## WORKER-SPAWN-PATTERN (INV-SPAWN = INV-PM-5-aequivalent)

INV-SPAWN (= INV-PM-5-aequivalent, AKTIVER STRUKTURVERTRAG): Die vier
  Berater-Calls (ArchConformance / PatternConformance / garbageCollection /
  stateMaintain) MUESSEN ueber Worker-Spawn aufgerufen werden — der Team Lead
  laedt diese Berater-Skills NIE selbst inline. Pseudocode-Notation
  "Skill(_PostBatch_ArchConformance, args=...)" wird semantisch interpretiert als:
     Agent(subagent_type=tier, prompt="Lade Skill _X via Skill-Tool und fuehre
     Vertrag aus + schreibe BERATER_OUTPUTS.{phase}.{status,exit_code,
     last_berater} + stirb", team_name="postbatch-{NAME}")
  Datenfluss = Vertraege (Berater lesen/schreiben Vault-Vertragsdateien);
  Manifest = NUR Zustand (exit_code-Marker). Lead liest NIE Berater-Payload aus
  dem Manifest, nur den Zustand. (Spiegelt _SDF_orchestrate WORKER-SPAWN-PATTERN
  BL-468 + _SDF_orchestrate_post BL-469 + _I_orchestrate + A INV-PM-5 + IDF INV-SPAWN.)

Jedes `Skill(_PostBatch_X / _SDF_berater_X, args=...)` der vier Berater-Steps
unten ist KURZSCHRIFT fuer:

  Agent(
    subagent_type="general-sonnet" | "general-haiku" | "general-purpose",
                                      # Tier laut Berater-Spec
    description="PostBatch Phase {N} {berater_name}",
    prompt="""
      Du bist kurzlebiger Worker fuer PostBatch Phase {N}.
      ENV: CLAUDE_BL_ID={bl_id}

      AUFGABE: Lade Skill _X via Skill-Tool und fuehre den dort definierten
      Vertrag aus mit args="{args}".

      REGELN:
      - W7-Constraint: KEIN Sub-Agent-Spawning durch dich.
      - Schreibe BERATER_OUTPUTS.{phase}.{status,exit_code,last_berater} ins _manifest.md.
      - SendMessage an "team-lead" mit Ergebnis-Summary.
      - Worker stirbt nach Skill-Ausfuehrung.
    """,
    team_name="postbatch-{NAME}"
  )

**Verbotene Anti-Pattern:**
- (X) Team Lead ruft `Skill(_PostBatch_X / _SDF_berater_X)` direkt auf -> Direkt-Load (Megaworker)
- (X) Team Lead liest Berater-Skill-Markdown selbst und fuehrt die Phase inline aus
- (OK) Team Lead spawnt Worker via Agent(), Worker laedt Skill, schreibt Slot, stirbt

**DATENFLUSS-PRINZIP (INV-DATA-Aequivalent):** Lead liest NIE Berater-Payload,
nur den Zustand (`exit_code`-Marker im BERATER_OUTPUTS-Slot). Die fachlichen
Outputs (Arch-/Pattern-Conformance-Findings, GC-Report, State-Maintain-Verdict)
reisen via Vault-Vertragsdateien zwischen den Beratern — NICHT als Lead-Inline-Payload.

**SCOPE-NOTE (2 Call-Klassen — AK-1/AK-4 KRITISCH):**
- **(a) Berater-Spawn-Targets** (INV-SPAWN gilt, je `Agent()`-Spawn, KEIN Lead-Inline-Load):
  `_PostBatch_ArchConformance` (SCHRITT 1.3), `_PostBatch_PatternConformance` (SCHRITT 1.5),
  `_SDF_berater_garbageCollection` (SCHRITT 3), `_SDF_berater_stateMaintain` (SCHRITT 4).
  Nur DIESE 4 distinct Berater-Calls duerfen Spawn-markiert werden.
- **(b) Orchestrator-Handschuh-Loads** (KEIN Spawn-Marker, INV-AO-CALLER, Lead-Skill-Load-
  Pflicht — KEINE Agent()-Spawns): `_T_orchestrate` (SCHRITT 1 + Re-Run-2), `_stage_orchestrate`
  (SCHRITT 2), `_I_cleanCodeArchitect` (SCHRITT 1.3 + 1.5 conditional).
  Ein Spawn-Marker an einer dieser drei Zeilen waere ein INV-AO-CALLER-Verstoss.
- **(c) Motor-Start: ENTFAELLT** — PostBatch ruft KEINEN `Workflow()`. Es gibt keinen Motor-Pfad.
  Der State-Seam ist der EINZIGE Megaworker-Trenner (anders als BL-468, wo der Motor zweiter Schutz war).
- **VERSCHACHTELUNGS-NOTE (load-bearing, W13):** Der Architekt-Impact-Orchestrator-Load steht im
  SELBEN SCHRITT-1.3/1.5-Branch wie ArchConformance/PatternConformance (9-10 Zeilen entfernt im
  selben IF-Block). Marker-Setzung ZEILEN-genau: der Spawn-Marker NUR vor die Berater-Zeile
  (ArchConformance/PatternConformance), NIEMALS vor die Architekt-Impact-Orchestrator-Zeile.

---

## STATE-MACHINE

```
INIT -> ARCH_CONF_DONE -> PATTERN_CONF_DONE -> GC_DONE -> STATEMAINTAIN_DONE
     -> COMPLETED | ABORTED_PROCESS_VIOLATION (exit_code=99, any phase)
```

**exit_code-Konvention:** Jede `<PHASE>_DONE`-Transition setzt `exit_code=0` (0=DONE).
`exit_code=2` = Vertrags-/Post-Check-FAIL (PL-Item + RETURN, bestehend erhalten). Prozess-/
Vertrags-Verletzung in JEDER Phase -> `phase="ABORTED_PROCESS_VIOLATION"` + `exit_code=99`
(kein neu erfundenes Schema — derselbe Marker wie im I-Pilot + _SDF_orchestrate + _SDF_orchestrate_post
STATE-MACHINE-Block; hier als Block-Level-Konvention: `exit_code=0`=DONE, `exit_code=2`=FAIL,
`exit_code=99`=ABORTED_PROCESS_VIOLATION).

**[M2-SEAM-HARDENED] (BL-470 — Spiegel I-Pilot BL-466 + _SDF_orchestrate BL-468 + _SDF_orchestrate_post
BL-469):** Die Transitions-Kette haengt am STATE-HANDOFF, NICHT an einem `arch_dirty`/`tests_dirty`/
`escalation_queued`-Branch-Flag. Modus-/branch-flag-unabhaengig — der State-Seam traegt die Phasen-
Trennung in JEDEM Modus identisch. **KEIN Motor -> der State-Seam ist der EINZIGE Megaworker-Schutz**
(BL-468/SDF hatte den Motor als zweiten Schutz; PostBatch NICHT — PostBatch ruft kein `Workflow()`,
darum ist die STATE-MACHINE der EINZIGE Trenner). Branch/Skip degeneriert zu einem `exit_code=0`-
Durchlauf (legitime Faelle: `escalation_queued=false`-RETURN, ArchConformance-EMPTY_SEED-Graceful-Skip,
garbageCollection-"kein Bloat"-SKIP) — KEINE Phase wird aus der Kette entfernt. TDD/RED!=GREEN ist nur
der **2. Notnagel**; der **primaere** Megaworker-Schutz ist dieser state-getriebene Vertrag
(BERATER_OUTPUTS-Slot pro Berater + State-Handoff + [GATE P]-exit_code-Gate).

| Phase / SCHRITT | Status-Wert (DONE) | Slot (neu) | Berater (Spawn, KURZSCHRIFT) | Branch/Skip (erhalten) |
|---|---|---|---|---|
| 1.3 ArchConformance | `ARCH_CONF_DONE` | `BERATER_OUTPUTS.archConformance` | `_PostBatch_ArchConformance` | blocker_count>0 & !escalation -> RETURN (erhalten); EMPTY_SEED -> Graceful Skip |
| 1.5 PatternConformance | `PATTERN_CONF_DONE` | `BERATER_OUTPUTS.patternConformance` | `_PostBatch_PatternConformance` | blocker_count>0 & !escalation -> RETURN (erhalten) |
| 3 garbageCollection | `GC_DONE` | `BERATER_OUTPUTS.garbageCollection` | `_SDF_berater_garbageCollection` | idempotent "kein Bloat" -> SKIP (erhalten) |
| 4 stateMaintain | `STATEMAINTAIN_DONE` | `BERATER_OUTPUTS.stateMaintain` | `_SDF_berater_stateMaintain` | HARD-Violation -> _guard_log APPEND (erhalten) |
| END | `COMPLETED` / `ABORTED_PROCESS_VIOLATION` | — | — | BDF_NEXT_TRIGGER=true (SCHRITT 5, erhalten) |

> **SCOPE-NOTE (BL-470):** Dieser Block DEKLARIERT die State-Kette + koppelt die vier Berater-
> Spawns an exit_code-Gates (additiv). Er entfernt KEINE Conformance-/Branch-/Re-Run-/PL-FAIL-Logik,
> reduziert KEINE LOC und macht KEINEN Step branch-konditional. KEIN Motor (PostBatch ruft kein
> `Workflow()`) — der State-Seam ist der EINZIGE Trenner.

---

## Pipeline-Logik

```
SCHRITT 0: Entry-Log
  Lies batch_current aus DF_PIPELINE_STATE (_manifest.md)
  Lies tdd_stages aus _session_params.md
  Logge: "[POSTBATCH] ENTRY batch={batch_current} stages={tdd_stages}"

SCHRITT 1: Test-Verifikation
  Skill(_T_orchestrate, args="--name {NAME} --stages {tdd_stages}")
  # _T_orchestrate schreibt T_ORCHESTRATE_STATE ins Manifest
  Lies T_ORCHESTRATE_STATE aus _manifest.md
  POSTBATCH_PIPELINE_STATE.t_state = T_ORCHESTRATE_STATE

  IF T_ORCHESTRATE_STATE == "DONE_FAIL":
    Schreibe PL-Item: "[POSTBATCH] Batch {batch_current} Tests FAIL — manuelle Pruefung noetig"
    POSTBATCH_PIPELINE_STATE.batch_done = false
    Logge: "[POSTBATCH] EXIT batch={batch_current} → FAIL (Tests rot)"
    RETURN

SCHRITT 1.3: ArchConformance-Check (BL-154, AK-3-1, AK-3-2)

> **Einschub-Strategie (W30, ADR-1):** Nach _T_orchestrate-Run 1, VOR PatternConformance.
> Scope: unstaged Git-Diff. Scannt architektonische Verletzungen. Schreibt arch_dirty Flag.
> NON-BLOCKING bei leerer PatternLibrary (INV-ARCH-4, EMPTY_SEED Graceful-Skip).

  # [INV-SPAWN] [GATE P1] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline.
  #   exit_code-Check Vorgaenger (INIT, Entry) VOR Spawn (== 99 ABORT, Skip-tolerant, NICHT != 0):
  #   IF DF_PIPELINE_STATE.last_phase_exit_code == 99: ABORT "[INV-SPAWN] Phase 1 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)".
  Skill(_PostBatch_ArchConformance, args="--scope unstaged --batch {batch_current}")
  # Worker schreibt BERATER_OUTPUTS.archConformance.{status,exit_code,last_berater} (ARCH_CONF_DONE) + stirbt.
  # _PostBatch_ArchConformance schreibt ARCH_CONFORMANCE_STATE ins Manifest

  Lies ARCH_CONFORMANCE_STATE aus _manifest.md
  POSTBATCH_PIPELINE_STATE.arch_conformance = ARCH_CONFORMANCE_STATE

  IF ARCH_CONFORMANCE_STATE.blocker_count > 0:
    IF ARCH_CONFORMANCE_STATE.escalation_queued == true:
      Logge: "[POSTBATCH] ARCH-BLOCKER escalation_queued=true → _I_cleanCodeArchitect impact-check (ARCH-7)"
      Skill(_I_cleanCodeArchitect, args="--mode impact-check --batch {batch_current}")
      verdicts = lies _manifest.md → ARCHITECT_IMPACT_VERDICTS ?? []
      needs_pl_list = [v for v in verdicts if v.needs_pl == true]
      FÜR jedes v IN needs_pl_list:
        Schreibe PL-Item: "[ARCH-IC] needs_pl: {v.finding_id} — {v.reasoning}"
      Logge: "[POSTBATCH] Architekt-Verdicts (ARCH) verarbeitet. Queue geleert. Pipeline fortsetzen."
    ELSE:
      Schreibe PL-Item: "[POSTBATCH] ArchConformance BLOCKER: {blocker_count} Findings nicht eskalierbar — manuelle Pruefung noetig"
      POSTBATCH_PIPELINE_STATE.batch_done = false
      Logge: "[POSTBATCH] EXIT batch={batch_current} → ARCH-BLOCKER nicht eskalierbar ({blocker_count})"
      RETURN

SCHRITT 1.5: PatternConformance-Check (AK-B-5, BL-153, M-4)

> **Einschub-Strategie (INV-EINSCHUB, AK-B-5):** Nach _T_orchestrate-Run 1 UND ArchConformance, VOR _stage_orchestrate.
> Scope: unstaged Git-Diff (alle im Batch angefassten Dateien, NICHT HEAD-Diff).
> NON-BLOCKING bei WARN/INFO — BLOCKER bei BLOCKER-Findings (tests_dirty-Flag Logik).

  # [INV-SPAWN] [GATE P2] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline.
  #   exit_code-Check Vorgaenger (archConformance) VOR Spawn (== 99 ABORT, Skip-tolerant, NICHT != 0):
  #   IF BERATER_OUTPUTS.archConformance.exit_code == 99: ABORT "[INV-SPAWN] Phase 2 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)".
  Skill(_PostBatch_PatternConformance, args="--scope unstaged --batch {batch_current}")
  # Worker schreibt BERATER_OUTPUTS.patternConformance.{status,exit_code,last_berater} (PATTERN_CONF_DONE) + stirbt.
  # _PostBatch_PatternConformance schreibt PATTERN_CONFORMANCE_STATE ins Manifest

  Lies PATTERN_CONFORMANCE_STATE aus _manifest.md
  POSTBATCH_PIPELINE_STATE.pattern_conformance = PATTERN_CONFORMANCE_STATE

  IF PATTERN_CONFORMANCE_STATE.blocker_count > 0:
    IF PATTERN_CONFORMANCE_STATE.escalation_queued == true:
      # ARCH-7: Architekten-Eskalation statt Hard-Stop — Pipeline laeuft weiter
      Logge: "[POSTBATCH] BLOCKER escalation_queued=true → _I_cleanCodeArchitect impact-check (ARCH-7)"
      Skill(_I_cleanCodeArchitect, args="--mode impact-check --batch {batch_current}")

      # ARCH-12: Queue-Cleanup + needs_pl Handling nach Architekt-Aufruf
      verdicts = lies _manifest.md → ARCHITECT_IMPACT_VERDICTS ?? []
      needs_pl_list = [v for v in verdicts if v.needs_pl == true]
      FÜR jedes v IN needs_pl_list:
        Schreibe PL-Item: "[ARCH-IC] needs_pl: {v.finding_id} — {v.reasoning}"
        Logge: "[POSTBATCH] PL-Item fuer needs_pl-Verdict: {v.finding_id}"
      IF |needs_pl_list| > 0:
        Logge: "[POSTBATCH] {|needs_pl_list|} PL-Items aus Architekt-Verdicts erstellt"
      # Queue ist bereits in _I_cleanCodeArchitect --mode impact-check geleert worden
      # (INV-ARCH-IC-2: ARCHITECT_ESCALATION_QUEUE = [] nach Verarbeitung)
      Logge: "[POSTBATCH] Architekt-Verdicts verarbeitet. Queue geleert. Pipeline fortsetzen (ARCH-7)"
      # Architekten-Analyse abgeschlossen — Pipeline fortsetzen (kein RETURN)
    ELSE:
      # Nicht-eskalierbare BLOCKER (escalation_queued=false, sollte nicht vorkommen)
      Schreibe PL-Item: "[POSTBATCH] PatternConformance BLOCKER: {blocker_count} Findings nicht eskalierbar — manuelle Pruefung noetig"
      POSTBATCH_PIPELINE_STATE.batch_done = false
      Logge: "[POSTBATCH] EXIT batch={batch_current} → PATTERN-BLOCKER nicht eskalierbar ({blocker_count})"
      RETURN

  # AK-3-2: OR-Check — beide Conformance-Flags kombiniert (W11, BL-154)
  arch_dirty = ARCH_CONFORMANCE_STATE.arch_dirty ?? false
  IF arch_dirty OR PATTERN_CONFORMANCE_STATE.tests_dirty:
    # arch_dirty=true (AK-3-1) ODER tests_dirty=true (AK-E-6) → _T_orchestrate erneut
    Logge: "[POSTBATCH] arch_dirty={arch_dirty} OR tests_dirty={PATTERN_CONFORMANCE_STATE.tests_dirty} → _T_orchestrate Run-2 (AK-3-2)"
    Skill(_T_orchestrate, args="--name {NAME} --stages {tdd_stages}")
    Lies T_ORCHESTRATE_STATE aus _manifest.md
    IF T_ORCHESTRATE_STATE == "DONE_FAIL":
      Schreibe PL-Item: "[POSTBATCH] Tests nach PatternConformance-Apply FAIL"
      POSTBATCH_PIPELINE_STATE.batch_done = false
      RETURN

SCHRITT 2: Commit-Stage
  Skill(_stage_orchestrate)
  # _stage_orchestrate schreibt stage_gate_status ins Manifest
  Lies stage_gate_status aus _manifest.md
  POSTBATCH_PIPELINE_STATE.stage_state = stage_gate_status

  IF stage_gate_status == "FAIL":
    Schreibe PL-Item: "[POSTBATCH] Batch {batch_current} Stage FAIL — Commit fehlgeschlagen"
    POSTBATCH_PIPELINE_STATE.batch_done = false
    Logge: "[POSTBATCH] EXIT batch={batch_current} → FAIL (Stage)"
    RETURN

SCHRITT 3: garbageCollection (C12 — BL-140 verdrahtet)
  # [INV-SPAWN] [GATE P3] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline.
  #   exit_code-Check Vorgaenger (patternConformance, nach Re-Run + Stage) VOR Spawn (== 99 ABORT, Skip-tolerant):
  #   IF BERATER_OUTPUTS.patternConformance.exit_code == 99: ABORT "[INV-SPAWN] Phase 3 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)".
  Skill(_SDF_berater_garbageCollection)
  # Worker schreibt BERATER_OUTPUTS.garbageCollection.{status,exit_code,last_berater} (GC_DONE) + stirbt.
  # Manifest scrubben (*_PREV/*_ARCHIVED entfernen)
  # PL-Items >30d archivieren
  # _session_params obsolete Felder entfernen
  # Idempotent: bei "kein Bloat" -> SKIP

SCHRITT 4: stateMaintain (C13 — BL-140 verdrahtet)
  # [INV-SPAWN] [GATE P4] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline.
  #   exit_code-Check Vorgaenger (garbageCollection) VOR Spawn (== 99 ABORT, Skip-tolerant):
  #   IF BERATER_OUTPUTS.garbageCollection.exit_code == 99: ABORT "[INV-SPAWN] Phase 4 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)".
  Skill(_SDF_berater_stateMaintain)
  # Worker schreibt BERATER_OUTPUTS.stateMaintain.{status,exit_code,last_berater} (STATEMAINTAIN_DONE) + stirbt.
  # Cross-Reference-Check (Pfad-Felder existieren?)
  # Duplikat-Check in Manifest-Bloecken
  # Timestamp-Plausibilitaet
  # HARD-Violations -> _guard_log.md APPEND (Pipeline laeuft weiter, SOFT-Degradation)

SCHRITT 5: BDF freigeben
  DF_PIPELINE_STATE.BDF_NEXT_TRIGGER = true
  POSTBATCH_PIPELINE_STATE.batch_done = true
  Logge: "[POSTBATCH] Batch {batch_current} DONE → BDF_NEXT_TRIGGER=true"
```

## Drei-Ebenen-Hinweis

PostBatch ist eine von drei Post-Ebenen und darf NICHT mit den anderen verwechselt werden:

| Ebene   | Command                        | Wann                              |
|---------|--------------------------------|-----------------------------------|
| BATCH   | `_PostBatch_orchestrate` (hier)| Nach Batch-Item-Loop: Tests+Stage |
| ITEM    | `_SDF_PostBerater_orchestrate` | Nach Batch-Ende: Housekeeping+Re-Plan |
| FEATURE | `_Post_orchestrate`            | Einmal am Feature-Ende            |

## INV-POSTBATCH-1

Diese Datei enthaelt ausschliesslich Skill-Calls (`_T_orchestrate` und `_stage_orchestrate`)
sowie State-Lesen/-Schreiben. Kein git, kein gh, keine Shell-Kommandos inline. AK-13
verbietet Inline-Operationen systemweit ab BL-133.
