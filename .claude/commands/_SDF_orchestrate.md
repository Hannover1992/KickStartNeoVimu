# /_SDF_orchestrate - Small Dark Factory Meta-Orchestrator

```yaml
status: active
version: 3.2.0
op: SmallDarkFactory
phase: Meta
type: factory
chain_position: meta
team_based: true
depends_on:
  - _I_orchestrate
  - _PrePhase_orchestrate
  - _PostBatch_orchestrate
feeds_into:
  - _SC_orchestrate
related:
  - _A_orchestrate
```

> **Thin-Conductor (BL-401 SRP-Refactor).** Dieser Conductor haelt NUR die eine Zustaendigkeit:
> Resume-Guard → Outer-Loop → modusEntscheidung-Gate → Dispatch → loop_decision-Routing → FINAL.
> Doku/Schemas/Narrative sind ausgelagert. Siehe:
> - `{META}/sdf/param-setup.md` — Aufruf, Parameter-Validierung, GLOBAL_MODUS/max_cycles, DF_PIPELINE_STATE-Schema
> - `{META}/sdf/state-machine.md` — Transitionen, State-Transition-Funktion, DEFER, ABORT-Handling, HiL-Punkte
> - `{META}/sdf/outer-loop-doctrine.md` — Stale-Handoff-Narrativ, Vehikel-Gate-Begruendung, INV-MODUS-6/8/9, Motor-vs-altmodisch
> - `{META}/sdf/modus-dispatch-reference.md` — Phase-1.1-Gate-Doktrin, INV-MODUS-4 Per-Batch, M1..M9-Mapping-Referenz

## VERTRAG — Invarianten-Leitplanken (BLEIBEN im Conductor, User-Direktive)

```
ACTOR: TEAM LEAD (DU — reiner Orchestrator). Fuehrt KEINE Sub-Commands selbst aus. NUR Handschuhe
wechseln (Skill-Load), tracken, entscheiden. AUSNAHME: Phase 0 (Pre-Load) direkt. State lebt im
MANIFEST (DF_PIPELINE_STATE / DF_BATCH_STATE). 1 Agent = 1 Phase-Command.

INV-PM-1: Worker-Pflicht ABSOLUT — auch bei Inline/Easy/Trivial. "Code existiert" ist KEIN Skip-Grund.
INV-PM-2: Handschuh-Wechsel = frischer Skill-Load. IMMER via Skill(skill="..."), nie Agent().
INV-AO-CALLER: Skill(_SDF_orchestrate) MUSS vom Team Lead SELBST geladen werden. VERBOTEN: via
          Agent(general-sonnet, prompt="orchestrate ...") — Sub-Agent wird Mega-Agent.
INV-HW-1: SC ↔ SDF ↔ I — Wechsel zwischen SC und I geht IMMER ueber SDF.
INV-HW-2: M2 Standard = I_orchestrate FULL. NUR M1 Inline darf abkuerzen.
INV-MODUS-1: DF_BATCH_STATE.modus/batch_modes wird AUSSCHLIESSLICH via
          Skill(_SDF_berater_modusEntscheidung) (C3) gesetzt. Kein anderer Schreiber.
INV-HANDOVER-1: Implement-Dispatch = Workflow dispatch_implement (Motor) ODER Lead-driven
          Sub-Batch-Dispatch (altmodisch). Caller-Self-Chain OBSOLET im Motor-Pfad.
INV-MOTOR-1: Step-Skeleton ausschliesslich aus feststehendem modus. 1 agent() = 1 Sub-Skill-Load.
INV-MOTOR-2: Workflow RETURNED loop_decision an den Lead; Routing macht der LEAD.
INV-DISPATCH-INLINE-1: Skill-Loads IMMER beim Team Lead. Berater ruft NIE Skill(_X_orchestrate).
INV-DISPATCH-INLINE-2: Jeder Skill-Aufruf MUSS --vault={VAULT} mitgeben.

ANTI-PATTERN (VERBOTEN — Delegations-Invariante): Team Lead editiert/schreibt KEINEN Code/Tests/
  Dateien selbst, fuehrt KEIN dotnet build/test selbst aus, nutzt KEIN spawn_agent()/Agent() fuer
  Code-Worker oder Orchestrator-Calls, KEIN Worker-Skip weil "Code existiert". ERLAUBT: LIEST
  Artefakte/Code (Analyse). RICHTIG: Handschuh-Wechsel via Skill() zu I/SC; I/SC spawnen IHRE Worker.
```

## WORKER-SPAWN-PATTERN (INV-SPAWN = INV-PM-5-aequivalent)

INV-SPAWN (= INV-PM-5-aequivalent, AKTIVER STRUKTURVERTRAG): Die Pre-SDF-
  Berater-Calls (testRun / analyse / architecturalBrief / patternBrief /
  modusEntscheidung) MUESSEN ueber Worker-Spawn aufgerufen werden — der Team
  Lead laedt diese Berater-Skills NIE selbst inline. Pseudocode-Notation
  "Skill(_SDF_berater_X, args=...)" wird semantisch interpretiert als:
     Agent(subagent_type=tier, prompt="Lade Skill _SDF_berater_X und fuehre
     Vertrag aus + schreibe BERATER_OUTPUTS.{phase}.{status,exit_code,
     last_berater} + stirb", team_name="sdf-{NAME}")
  Datenfluss = Vertraege (Berater lesen/schreiben Vault-Vertragsdateien);
  Manifest = NUR Zustand (exit_code-Marker). Lead liest NIE Berater-Payload aus
  dem Manifest, nur den Zustand. (Spiegelt _SDF_orchestrate_post WORKER-SPAWN-
  PATTERN + _I_orchestrate + A INV-PM-5 + IDF INV-SPAWN.)

Jedes `Skill(_SDF_berater_X, args=...)` der Pre-SDF-Steps unten ist
KURZSCHRIFT fuer:

  Agent(
    subagent_type="general-sonnet" | "general-haiku" | "general-purpose",
                                      # Tier laut Berater-Spec
    description="SDF Pre-Phase {N} {berater_name}",
    prompt="""
      Du bist kurzlebiger Worker fuer SDF Pre-Phase {N}.
      ENV: CLAUDE_BL_ID={bl_id}

      AUFGABE: Lade Skill _SDF_berater_X via Skill-Tool und fuehre den dort
      definierten Vertrag aus mit args="{args}".

      REGELN:
      - W7-Constraint: KEIN Sub-Agent-Spawning durch dich.
      - Schreibe BERATER_OUTPUTS.{phase}.{status,exit_code,last_berater} ins _manifest.md.
      - SendMessage an "team-lead" mit Ergebnis-Summary.
      - Worker stirbt nach Skill-Ausfuehrung.
    """,
    team_name="sdf-{NAME}"
  )

**Verbotene Anti-Pattern:**
- (X) Team Lead ruft `Skill(_SDF_berater_X)` direkt auf -> Direkt-Load (Megaworker)
- (X) Team Lead liest Berater-Skill-Markdown selbst und fuehrt die Pre-SDF-Phase inline aus
- (OK) Team Lead spawnt Worker via Agent(), Worker laedt Skill, schreibt Slot, stirbt

**DATENFLUSS-PRINZIP (INV-DATA-Aequivalent):** Lead liest NIE Berater-Payload,
nur den Zustand (`exit_code`-Marker im BERATER_OUTPUTS-Slot). Die fachlichen
Outputs (A-Pipeline-Analyse, Pattern-Brief, Modus-Entscheidung) reisen via
Vault-Vertragsdateien zwischen den Beratern — NICHT als Lead-Inline-Payload.

**SCOPE-NOTE (3 Call-Klassen — AK-1/AK-4 KRITISCH):**
- **(a) Berater-Spawn-Targets** (INV-SPAWN gilt, je `Agent()`-Spawn, KEIN Lead-Inline-Load):
  `_SDF_berater_testRun`, `_SDF_berater_analyse`, `_SDF_berater_architecturalBrief`,
  `_SDF_berater_patternBrief`, `_SDF_berater_modusEntscheidung`. Nur DIESE 5 distinct
  `_SDF_berater_*`-Calls duerfen [INV-SPAWN]-markiert werden.
- **(b) Orchestrator-Handschuh-Loads** (KEIN [INV-SPAWN], INV-AO-CALLER, Lead-Skill-Load-
  Pflicht — KEINE Agent()-Spawns): `_I_orchestrate` / `_SC_orchestrate` / `_IDF_orchestrate` /
  `_WP_orchestrate` / `_T_orchestrate` / `_smoothing` / `_presentation` (Dispatcher-SWITCH
  M1..M9). Ein [INV-SPAWN]-Marker an einer dieser Zeilen waere ein INV-AO-CALLER-Verstoss.
- **(c) Motor-Start** (byte-intakt, KEIN Spawn-Marker): `Workflow(dispatch_implement)` — der
  Lead startet den Motor selbst (INV-MOTOR-1/2), kein Berater-Spawn.

**INV-MODUS-Reminder:** Worker darf modus-Feld NICHT setzen ausser via _SDF_berater_modusEntscheidung (BL-165 INV-MODUS-1).

---

## STATE-MACHINE

```
INIT -> TESTRUN_DONE -> ANALYSE_DONE -> ARCH_BRIEF_DONE -> PATTERN_BRIEF_DONE
     -> MODUS_DONE -> DISPATCHED
     -> COMPLETED | ABORTED_PROCESS_VIOLATION (exit_code=99, any phase)
```

**exit_code-Konvention:** Jede `<PHASE>_DONE`-Transition setzt `exit_code=0` (0=DONE).
`exit_code=2` = Vertrags-/Post-Check-FAIL (bestehend erhalten, Phase 1.1 Pre/Post-Check).
Prozess-/Vertrags-Verletzung in JEDER Phase -> `phase="ABORTED_PROCESS_VIOLATION"` +
`exit_code=99` (kein neu erfundenes Schema — derselbe Marker wie im I-Pilot + _SDF_orchestrate_post
STATE-MACHINE-Block; hier als Block-Level-Konvention generalisiert: `exit_code=0`=DONE,
`exit_code=2`=FAIL, `exit_code=99`=ABORTED_PROCESS_VIOLATION).

**[M2-SEAM-HARDENED] (BL-468 — Spiegel I-Pilot BL-466 + _SDF_orchestrate_post BL-469):** Die
Transitions-Kette haengt am STATE-HANDOFF, NICHT an einem TDD-/Modus-Flag. Modus-unabhaengig
(M1-M9) — der State-Seam traegt die Phasen-Trennung in JEDEM Modus identisch. Skip degeneriert
zu einem `exit_code=0`-Durchlauf (legitime konditionale Skips: testRun-only-SKIP / single_batch /
N=1-Fast-Path / STALE-HANDOFF-Recovery) — KEINE Phase wird aus der Kette entfernt. Wuerde man eine
Phase modus-konditional (an `motor_allowed`/`tdd_enabled`, W11/W5) entfernen, haengt der Seam wieder
an TDD/Modus (Anti-Pattern) und der M2-Megaworker bleibt offen. TDD/RED!=GREEN ist damit nur noch
der **2. Notnagel** (Handoff-/Guard-Schicht: guard_agent_prompt_validator / guard_idf_sdf_handoff);
der **primaere** Megaworker-Schutz ist dieser state-getriebene Vertrag (BERATER_OUTPUTS-Slot pro
Berater + State-Handoff + [GATE P]-exit_code-Gate).

| Phase | Status-Wert (DONE) | Slot | Berater (Spawn, KURZSCHRIFT) | Skip-Bedingung (erhalten) |
|-------|---------------------|------|------------------------------|---------------------------|
| 0.5 testRun | `TESTRUN_DONE` | `BERATER_OUTPUTS.testRun` | `_SDF_berater_testRun` | NUR --mode=testRun (sonst SKIP) |
| 1.0 analyse | `ANALYSE_DONE` | `BERATER_OUTPUTS.analyse` | `_SDF_berater_analyse` | — (immer) |
| 1.0 architecturalBrief | `ARCH_BRIEF_DONE` | `BERATER_OUTPUTS.architecturalBrief` | `_SDF_berater_architecturalBrief` | leere Library → Graceful Skip |
| 1.5 patternBrief | `PATTERN_BRIEF_DONE` | `BERATER_OUTPUTS.patternBrief` | `_SDF_berater_patternBrief` | leere Library → Graceful Skip |
| 1.1 modusEntscheidung | `MODUS_DONE` | `BERATER_OUTPUTS.modusEntscheidung_*` | `_SDF_berater_modusEntscheidung` | — (nicht skippbar, INV-MODUS-2) |
| 2.1 dispatch | `DISPATCHED` | `BERATER_OUTPUTS.executionDispatch` | (`_I_/_SC_/...orchestrate` ODER Motor, KEIN Berater) | — |
| END | `COMPLETED` / `ABORTED_PROCESS_VIOLATION` | — | — | — |

> **SCOPE-NOTE (BL-468):** Dieser Block DEKLARIERT die State-Kette + koppelt die Pre-SDF-Berater-
> Spawns an exit_code-Gates (additiv). Er entfernt KEINE bestehende Skip-/Branch-/Check-Logik,
> reduziert KEINE LOC und macht KEINEN Step modus-konditional. WEG B altmodisch (kein Motor).

---

## Phase 0a: Worker-Awareness (BL-151)

```python
# Worker-Self-Awareness (im Spawn-Prompt mitgegeben): {branch, bl_id, vault_root, bl_folder, cwd}.
worker_context = json.loads(subprocess(.claude/scripts/current_context.py --format=json).stdout)
```

## Parameter-Setup (SCHRITT 0.1 / 0.2 / 0.3)

> Aufruf-Syntax, Parameter-/task-source-Tabellen, Capping-Formel, GLOBAL_MODUS-Setup, max_cycles
> und das vollstaendige DF_PIPELINE_STATE-Schema: **Lies `{META}/sdf/param-setup.md`.**

```
SCHRITT 0.1: Parameter parsen + validieren (NAME Pflicht; difficulty/ceiling/floor cappen gegen
             Session-Params; task_source ∈ {auto,pl,direct,backlog}; testRun_mode = --mode==testRun)
SCHRITT 0.2: GLOBAL_MODUS-Setup — _session_params.md (HiL/difficulty/ceiling/floor) +
             _manifest.md (GLOBAL_MODUS=small_dark_factory, GLOBAL_HIL=off, ...)
SCHRITT 0.3: max_cycles = {easy:3, normal:5, hard:9}[difficulty] → dark_factory_max_cycles_override
```

## State Machine: DF_PIPELINE_STATE

```
# Normal-Flow (Batch):
IDLE → INIT → PRE_LOAD_DONE → ANALYSE → AK_PLAN → ITEM_LOOP → ITEM_DONE → ITEM_STAGE → ITEM_LOOP / DONE / ABORTED
DONE → IDLE (automatisch nach Protokoll-Rollover, Phase FINAL)
```
Terminale Zustaende: DONE (BDF uebernimmt), ABORTED.
→ Vollstaendige Transitionen, State-Transition-Funktion, DEFER-Funktion: **Lies `{META}/sdf/state-machine.md`.**

## PHASE 0: LITE-RESUME-GUARD (eigenes DF_BATCH_STATE)

> Phase 0 prueft nur eigenen Batch-State. PL-Item-Level Resume macht IDF (Phase 7 BATCH_PLAN ist
> autoritativ). Berater-Calls (resumeGuard/validator/dependencyAnalyzer/...) sind nach IDF migriert.

```
IF DF_BATCH_STATE existiert AND batch_status == "STARTED":  → SCHRITT 1 (Recovery, SKIP Phase 0)
ELIF DF_BATCH_STATE existiert AND batch_status == "READY":  → SCHRITT 1.6 (IDF-GATE/Outer-Loop Entry)
       # READY = voriger Batch DONE, naechster wartet (Auto-Chain). SKIP Phase 1.0/1.5 (cached).
ELIF DF_BATCH_STATE existiert AND batch_status == "DONE":   Logge: "[SDF-RESUME] DONE — kein Re-Run"; EXIT
ELSE:                                                       Logge: "[SDF-INIT] Frischer Start — Phase 1"
```

## PHASE 0.5 / 1.0 / 1.6 (Pre-Outer-Loop Handschuh-Wechsel)

```
# PHASE 0.5 TESTRUN-STUFEN-LOOP (NUR bei --mode=testRun, ADR-FTR-01) — ersetzt Phase 1-3.
IF testRun_mode:
  # [INV-SPAWN] [GATE P1] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN) — NICHT Lead-Inline.
  #   exit_code-Check Vorgaenger (INIT, Entry) VOR Spawn (== 99 ABORT, Skip-tolerant, NICHT != 0):
  #   IF DF_PIPELINE_STATE.last_phase_exit_code == 99: ABORT "ABORTED_PROCESS_VIOLATION".
  Skill(skill="_SDF_berater_testRun", args="{NAME} {difficulty} {ceiling} {floor}")   # → BERATER_OUTPUTS.testRun, df_status=DONE
  # Worker schreibt BERATER_OUTPUTS.testRun.{status,exit_code,last_berater} (TESTRUN_DONE) + stirbt.
  → STOP (Phase 1, 2, 3 nicht ausfuehren)

# PHASE 1.0 ANALYSE (vor Modus-Entscheidung — A-Pipeline + Batch-Size-Eval).
# ANTI-PATTERN: spawn_agent(command="/_A_orchestrate ...") ← VERBOTEN
# [INV-SPAWN] [GATE P2] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN) — NICHT Lead-Inline.
#   exit_code-Check Vorgaenger (testRun ODER INIT) VOR Spawn (== 99 ABORT, Skip-tolerant):
#   IF BERATER_OUTPUTS.testRun.exit_code == 99: ABORT "ABORTED_PROCESS_VIOLATION".
Skill(skill="_SDF_berater_analyse", args="{NAME} {difficulty} {ceiling} {floor}")
# Worker schreibt BERATER_OUTPUTS.analyse.{status,exit_code,last_berater} (ANALYSE_DONE) + stirbt.
IF BERATER_OUTPUTS.analyse.a_phase != "COMPLETED": → ABBRUCH (BERATER_OUTPUTS.analyse.abbruch_grund)

# PHASE 1.6 IDF-GATE — Inner-Entry (aktiv bei direktem SDF-Aufruf). Idempotent. NUR task_source=backlog.
IF task_source == "backlog":
  idf_plan_status = IDF_PIPELINE_STATE.ak_plan.status if IDF_PIPELINE_STATE exists else null
  IF idf_plan_status != "DONE":   # sonst SKIP (Outer-Entry via BDF hat schon geplant)

    # ─── BL-365 N=1 FAST-PATH (AK-1/2/3/5) ───
    # Dial: n1_fastpath_bl365 (session_params_resolver, default-OFF). Muster BL-327/BL-403.
    # Bedingung: Dial==true UND actionable_count==1 (post-prune, aus A-Pipeline pl_pre_filled).
    #   actionable_count = Anzahl actionable Items aus BERATER_OUTPUTS.analyse.pl_pre_filled
    #                      (Felder mit status in {open, in_progress, unblocked})
    n1_dial          = resolve_param("n1_fastpath_bl365")  # False = default-OFF
    actionable_count = len([i for i in (BERATER_OUTPUTS.analyse.pl_pre_filled ?? [])
                            if i.status in {"open", "in_progress", "unblocked"}])

    IF n1_dial == True AND actionable_count == 1:
      # N=1 Fast-Path: IDF-Hop wird uebersprungen — kein Skill(_IDF_orchestrate)-Aufruf.
      # Inline-Planung (AK-2): befuellt DF_BATCH_STATE + BERATER_OUTPUTS_IDF-Namespace.
      Logge: "[N=1-FASTPATH] Dial=ON, actionable_count=1 -> IDF-bypass (BL-365 AK-1/2)"
      item = BERATER_OUTPUTS.analyse.pl_pre_filled[0]

      # DF_BATCH_STATE Inline-Befuellung (Trivial-Batch: 1 Item, 1 Batch)
      DF_BATCH_STATE.batch_items              = [item.id]
      DF_BATCH_STATE.batch_items_per_batch    = {"batch_1": [item.id]}
      DF_BATCH_STATE.current_sub_batch_id     = "batch_1"
      DF_BATCH_STATE.batch_total              = 1
      DF_BATCH_STATE.batch_stages             = {"batch_1": [1]}
      DF_BATCH_STATE.idf_bypass_reason        = "N=1_fastpath_BL-365"

      # IDF_PIPELINE_STATE: legitimen Skip markieren (Guards erkennen AK-4-konformen Bypass)
      IDF_PIPELINE_STATE.idf_status           = "IDF_DONE"
      IDF_PIPELINE_STATE.ak_plan.status       = "DONE"
      IDF_PIPELINE_STATE.ak_plan.bypass       = "N=1_fastpath_BL-365"

      # BERATER_OUTPUTS_IDF-Namespace Trivial-Inline (modelSync + testSearch bleiben REAL-KEEP)
      BERATER_OUTPUTS_IDF.dependencyAnalyzer  = {deps: [], trivial: True}
      BERATER_OUTPUTS_IDF.clustering          = {clusters: [{"batch_1": [item.id]}], trivial: True}
      BERATER_OUTPUTS_IDF.sequencePlanner     = {sequence: ["batch_1"], trivial: True}
      BERATER_OUTPUTS_IDF.batchPlan           = {batches: [{"id": "batch_1", "items": [item.id]}], trivial: True}
      BERATER_OUTPUTS_IDF.stagePlanner        = {stages: {"batch_1": [1]}, trivial: True}
      BERATER_OUTPUTS_IDF.metricPlanner       = {metrics: {}, trivial: True}
      BERATER_OUTPUTS_IDF.parallelSuitability = {suitable: False, reason: "N=1 trivial", trivial: True}
      BERATER_OUTPUTS_IDF.finalSummary        = {recommended_next: ["batch_1"], total_batches: 1, trivial: True}
      # INV-MODUS-1: Phase 1.6 N=1-Fast-Path setzt NUR batch_mode_hints (ADVISORY),
      #              NIE batch_modes/modus — C3 Phase 1.1 (_SDF_berater_modusEntscheidung)
      #              bleibt einziger modus-Writer. Kein Bypass von INV-MODUS-1 hier.
      DF_BATCH_STATE.batch_mode_hints         = {"batch_1": "M1_hint_advisory_only"}  # ADVISORY — C3 entscheidet endgueltig

      Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE.* + IDF_PIPELINE_STATE.*)
      Logge: "[N=1-FASTPATH] DF_BATCH_STATE + IDF_PIPELINE_STATE inline befuellt; idf_bypass_reason=N=1_fastpath_BL-365"

    ELSE:
      # AK-5 Regression: N>=2 ODER Dial=OFF -> unveraenderter bestehender IDF-Pfad (byte-identisch)
      Logge: "[IDF-GATE] n1_dial={n1_dial} actionable_count={actionable_count} -> normaler IDF-Hop"
      Skill(skill="_IDF_orchestrate", args="{NAME}")
      IF IDF_PIPELINE_STATE.ak_plan.status != "DONE": → FEHLER "[IDF-GATE] IDF ohne ak_plan.status=DONE — ABBRUCH"
    # ─── ENDE BL-365 N=1 FAST-PATH ───
```

## PHASE OUTER-LOOP-WRAPPER (pro Sub-Batch)

> Stale-Handoff-Narrativ, Vehikel-Gate-Begruendung, Motor-vs-altmodisch-Doktrin, INV-MODUS-6/8/9
> + "Was EINMALIG/PRO ROUND"-Listen: **Lies `{META}/sdf/outer-loop-doctrine.md`.**

```
per_batch = DF_BATCH_STATE.batch_items_per_batch ?? null

# ═══ STALE-HANDOFF-RECOVERY ═══ (self-heal: IDF --no-chain/Compact-Handoff; INV-MODUS-1 gewahrt)
# Wenn batch_items_per_batch keinen non-completed Batch hat ABER IDF_FINAL_SUMMARY.recommended_next
# einen geplanten Batch -> materialisiere batch_items_per_batch/batch_stages/batch_items daraus.
idf_final         = read IDF_FINAL_SUMMARY (aus _manifest.md, letzter Block)
completed         = DF_BATCH_STATE.completed_sub_batches ?? []
pending_from_idf  = [b FOR b IN (idf_final?.recommended_next ?? []) IF b NOT IN completed]
per_batch_pending = [k FOR k IN (per_batch ?? {}).keys() IF k NOT IN completed]
IF pending_from_idf != [] AND per_batch_pending == []:
  DF_BATCH_STATE.batch_items_per_batch ??= {}; DF_BATCH_STATE.batch_stages ??= {}
  FOR b IN pending_from_idf:
    fb = idf_final.batches.find(bx => bx.id == b); IF fb == null: CONTINUE
    DF_BATCH_STATE.batch_items_per_batch[b] = [it.id FOR it IN fb.items]
    DF_BATCH_STATE.batch_stages[b]          = fb.stages ?? [1]
  IF |pending_from_idf| == 1:
    DF_BATCH_STATE.batch_items          = DF_BATCH_STATE.batch_items_per_batch[pending_from_idf[0]]
    DF_BATCH_STATE.current_sub_batch_id = pending_from_idf[0]
  DF_BATCH_STATE.batch_status = "READY"; Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE.*)
  Logge: "[STALE-HANDOFF-RECOVERY] materialisiert aus IDF_FINAL_SUMMARY: {pending_from_idf}"
  per_batch = DF_BATCH_STATE.batch_items_per_batch
ELSE:
  Logge: "[STALE-HANDOFF-RECOVERY] SKIP — kein Heilbedarf."

# ═══ |per_batch| >= 1 — Single-Batch AUCH durch den Motor (Lead-schlank) ═══
IF per_batch != null AND |per_batch| >= 1:
  # Resume-aware Init (NICHT pauschal reset — sonst geht Resume-State verloren).
  DF_BATCH_STATE.completed_sub_batches ??= []; DF_BATCH_STATE.batch_modes ??= {}
  DF_BATCH_STATE.modus_begruendung_per_batch ??= {}; DF_BATCH_STATE.completed_stages_per_batch ??= {}

  # PENDING Sub-Batches sammeln (Resume-SKIP via completed_sub_batches — echte semantische Keys).
  pending_sub_batches = []
  FOR batch_key, batch_items_sub IN per_batch.items():
    IF batch_key IN DF_BATCH_STATE.completed_sub_batches: CONTINUE   # Resume-SKIP
    pending_sub_batches.append({"id": batch_key, "items": batch_items_sub,
      "stages": DF_BATCH_STATE.batch_stages[batch_key] ?? [1],
      "coverage_stages": DF_BATCH_STATE.coverage_per_batch?.[batch_key]?.stages_with_tests ?? null})
  IF pending_sub_batches == []:
    Logge: "[OUTER-LOOP] alle Sub-Batches completed — direkt Phase 3.4"; GOTO Phase 3.4

  # ═══ VEHIKEL-GATE: der Motor-Aufruf ist NIE unbedingt (beide Bedingungen muessen halten) ═══
  gate_d_passed  = json_parse(run("py -3 .claude/scripts/session_params_resolver.py resolve --param=motor_production_ready --bl-id={BL_ID} --json")).value IN [true,"true"]
  workflow_param = json_parse(run("py -3 .claude/scripts/session_params_resolver.py resolve --param=workflow --bl-id={BL_ID} --json")).value ?? "false"
  motor_vehicle  = json_parse(run("py -3 .claude/scripts/workflow_zones.py vehicle --activity=dispatch_implement --mode={workflow_param} --json")).vehicle
  motor_allowed  = gate_d_passed AND (motor_vehicle == "workflow")
  Logge: "[OUTER-LOOP] VEHIKEL-GATE motor_allowed={motor_allowed} (gate_d={gate_d_passed} workflow={workflow_param} vehicle={motor_vehicle})"

  IF NOT motor_allowed:
    # [M2-SEAM-HARDENED] (BL-468): Dieser altmodische Pfad ist OHNE Motor megaworker-sicher, weil die
    #   Phasen-Trennung am STATE-HANDOFF haengt (modusEntscheidung/patternBrief = je eigener BERATER_OUTPUTS-
    #   Slot + [GATE P]-exit_code-Gate), NICHT an motor_allowed/tdd_enabled. Modus-unabhaengig (M1-M9).
    # ── ALTMODISCHER Pfad (Lead-driven, KEIN Motor) — GENAU EINEN pending Sub-Batch dispatchen. ──
    # Re-entrant via INV-MODUS-7 SKILL-HANDSCHUH: I/SC chained _SDF_orchestrate_post (besitzt
    # Stage-Loop + RE-BATCH-Re-Entry + TERMINATE). KEIN GOTO Phase 3.4 hier.
    sub_batch = pending_sub_batches[0]
    DF_BATCH_STATE.current_sub_batch_id    = sub_batch.id
    DF_BATCH_STATE.current_sub_batch_items = sub_batch.items
    # INV-STAGE-STATE-1 (BL-414): DF_BATCH_STATE.current_stage ist kanonisch — SDF liest nur.
    # Writer-Disziplin: stageElevation/increment schreibt current_stage, SDF/I lesen.
    DF_BATCH_STATE.current_stage           = (sub_batch.stages[0] ?? 1)
    Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE.*)
    # [INV-SPAWN] [GATE P3] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN) — NICHT Lead-Inline.
    #   exit_code-Check Vorgaenger (analyse, Outer-Loop-Entry) VOR Spawn (== 99 ABORT, Skip-tolerant):
    #   IF BERATER_OUTPUTS.analyse.exit_code == 99: ABORT "ABORTED_PROCESS_VIOLATION".
    Skill(_SDF_berater_modusEntscheidung, args="{NAME}")   # Phase 1.1 — INV-MODUS-1 (PRO Sub-Batch)
    # Worker schreibt BERATER_OUTPUTS.modusEntscheidung_*.{status,exit_code,last_berater} (MODUS_DONE) + stirbt.
    # [INV-SPAWN] [GATE P4] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN) — NICHT Lead-Inline.
    #   exit_code-Check Vorgaenger (modusEntscheidung) VOR Spawn (== 99 ABORT, Skip-tolerant):
    #   IF BERATER_OUTPUTS.modusEntscheidung_*.exit_code == 99: ABORT "ABORTED_PROCESS_VIOLATION".
    Skill(_SDF_berater_patternBrief, args="{NAME}")        # Phase 1.5
    # Worker schreibt BERATER_OUTPUTS.patternBrief.{status,exit_code,last_berater} (PATTERN_BRIEF_DONE) + stirbt.
    EXEC SCHRITT 2.1 (Team-Lead-Dispatcher Modus-SWITCH M1..M9, mit --vault={VAULT})
    RETURN   # Handoff: I/SC → _SDF_orchestrate_post → (ELEVATE/RE-BATCH/TERMINATE)-Chain.

  # ── motor_allowed == true: Motor-Pfad. Der LEAD startet den Workflow SELBST. ──
  # modusEntscheidung (INV-MODUS-1, PRO Sub-Batch), patternBrief, FLAT-SEQUENCE, stageElevation,
  # Phase 3.x (NUR @BATCH_DONE), loopDecision laufen ALLE deterministisch IM Workflow.
  WORKFLOW_RESULT = Workflow(name="dispatch_implement", args={
    "bl_id": BL_ID, "name": NAME, "vault": VAULT, "working_dir": WORKING_DIR,
    "difficulty": difficulty, "ceiling": ceiling, "floor": floor, "sub_batches": pending_sub_batches})
  # WORKFLOW_RESULT = {sub_batch_results[], terminated_reason, loop_decision}
  SWITCH WORKFLOW_RESULT.terminated_reason:
    "completed":
      DF_BATCH_STATE.sdf_loop_decision = WORKFLOW_RESULT.loop_decision
      MAX_REBATCH = 5; DF_BATCH_STATE.sdf_rebatch_count ??= 0
      SWITCH WORKFLOW_RESULT.loop_decision:                 # Routing macht der LEAD (INV-MOTOR-2)
        "TERMINATE":  GOTO Phase 3.4
        "RE-BATCH":
          DF_BATCH_STATE.sdf_rebatch_count += 1
          IF DF_BATCH_STATE.sdf_rebatch_count > MAX_REBATCH:
            df_status="ABORTED"; DF_BATCH_STATE.last_failure="rebatch_cap_exceeded"; GOTO Phase 3.4
          Skill(skill="_SDF_orchestrate", args="{NAME} --resume"); RETURN   # frische Phase 1.1
        "ROLLBACK":     Skill(skill="_IDF_orchestrate", args="{NAME} --mode=recheck"); RETURN
        "SOFT-REPRIO":  Skill(skill="_IDF_orchestrate", args="{NAME} --mode=recluster"); RETURN
        DEFAULT:        GOTO Phase 3.4   # Fail-safe: unbekanntes loop_decision → TERMINATE
    "halt_user":  df_status = "HALTED"
    DEFAULT:      df_status = "ABORTED"; DF_BATCH_STATE.last_failure = WORKFLOW_RESULT.terminated_reason
  GOTO Phase 3.4 (batchEnde-Aggregat — einmal nach allen Rounds)

ELSE:
  Logge: "[OUTER-LOOP] SKIP — single_batch_path (fall-through Phase 1.1 / 2 / 3 single-pass)"
```

## PHASE 1: BATCH-MODUS — SCHRITT 1.1 Modus-Entscheidung (Gate)

> Gate-Doktrin (Pre-Check-Begruendung, "nicht skippbar", INV-MODUS-4 Per-Batch, M1..M9-Mapping):
> **Lies `{META}/sdf/modus-dispatch-reference.md`.**

```
# INV-MODUS-PRE-WRITE-1 Pre-Check: batch_modes/modus DARF nicht gesetzt sein ohne vorausgehendes
# BERATER_OUTPUTS.modusEntscheidung_* (sonst Lead/Pre-SDF-Skill hat Modus geschrieben → INV-MODUS-1-Bruch).
IF (DF_BATCH_STATE.batch_modes != null OR DF_BATCH_STATE.modus != null)
   AND grep(BERATER_OUTPUTS, prefix="modusEntscheidung") == null:
  APPEND .claude/audit/audit.jsonl event=INV-MODUS-1-PRE-WRITE-VIOLATION
  APPEND parking-lot.md PL-Item HIGH "Phase 1.1 Pre-Check failed"
  Logge: "[SDF Phase 1.1 Pre-Check] INV-MODUS-1-PRE-WRITE-VIOLATION — ABORT"; exit_code = 2; RETURN

# SCHRITT 1.0/1.5 Einschub (vor C3): architecturalBrief WEITER AUSSEN als patternBrief; beide NON-BLOCKING
# (leere Library → Graceful Skip). Verifikation (BL-154): architectural_brief_at < pattern_brief_at.
# [INV-SPAWN] [GATE P5] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN) — NICHT Lead-Inline.
#   exit_code-Check Vorgaenger (analyse) VOR Spawn (== 99 ABORT, Skip-tolerant, NICHT != 0):
#   IF BERATER_OUTPUTS.analyse.exit_code == 99: ABORT "ABORTED_PROCESS_VIOLATION".
Skill(_SDF_berater_architecturalBrief, args="{NAME}")
# Worker schreibt BERATER_OUTPUTS.architecturalBrief.{status,exit_code,last_berater} (ARCH_BRIEF_DONE) + stirbt.
# [INV-SPAWN] [GATE P6] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN) — NICHT Lead-Inline.
#   exit_code-Check Vorgaenger (architecturalBrief) VOR Spawn (== 99 ABORT, Skip-tolerant):
#   IF BERATER_OUTPUTS.architecturalBrief.exit_code == 99: ABORT "ABORTED_PROCESS_VIOLATION".
Skill(_SDF_berater_patternBrief, args="{NAME}")          # → BERATER_OUTPUTS.patternBrief
# Worker schreibt BERATER_OUTPUTS.patternBrief.{status,exit_code,last_berater} (PATTERN_BRIEF_DONE) + stirbt.

# SCHRITT 1.1 Modus-Entscheidung (C3 = ALLEINIGER Schreiber, INV-MODUS-1; nicht skippbar)
# [INV-SPAWN] [GATE P7] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN) — NICHT Lead-Inline.
#   exit_code-Check Vorgaenger (patternBrief) VOR Spawn (== 99 ABORT, Skip-tolerant):
#   IF BERATER_OUTPUTS.patternBrief.exit_code == 99: ABORT "ABORTED_PROCESS_VIOLATION".
Skill(_SDF_berater_modusEntscheidung, args="{NAME}")
# Worker schreibt BERATER_OUTPUTS.modusEntscheidung_*.{status,exit_code,last_berater} (MODUS_DONE) + stirbt.
DF_BATCH_STATE.modus wird gesetzt   # + modus_begruendung + pipeline_route (von C3)
IF Skill exit != 0 OR DF_BATCH_STATE.modus not in {M1..M9}:   # Post-Check: Vertrag erfuellt?
  Logge: "[SDF Phase 1.1 Post-Check] Modus-Vertrag verletzt"; exit_code = 2; RETURN
```

## PHASE 2: WORKING — SCHRITT 2.1 Team-Lead-Dispatcher (INLINE — kein Berater!)

> Zwei-Pfad-Status (Motor vs altmodisch), KURZLEBIG_PROMPT-Propagation-Doku, M1..M9-Mapping-Detail:
> **Lies `{META}/sdf/modus-dispatch-reference.md`.** Die SWITCH unten ist die ausfuehrbare Wahrheit
> (im altmodischen Pfad LIVE vom Lead, im Motor-Pfad Referenz fuer die Step-Skeletons).

```
VAULT = subprocess.check_output(["python3", ".claude/scripts/resolve_bl_path.py", BL_ID]).strip()  # INV-VAULT-9

# Modus + Items lesen — Per-Batch-Override falls Sub-Batch aktiv (INV-MODUS-4)
modus            = DF_BATCH_STATE.current_sub_batch_mode ?? DF_BATCH_STATE.modus
batch_items_use  = DF_BATCH_STATE.current_sub_batch_items ?? DF_BATCH_STATE.batch_items
items_to_process = [i FOR i IN batch_items_use IF i NOT IN (DF_BATCH_STATE.item_done ?? [])]
batch_arg        = ",".join(items_to_process)
sub_batch_id     = DF_BATCH_STATE.current_sub_batch_id ?? "single"
stage_arg        = "--stage=" + str(DF_BATCH_STATE.current_stage ?? 1)

# patternBrief + architecturalBrief in KURZLEBIG_PROMPT propagieren (ARCH-15/BL-154), wenn vorhanden.
IF has_matches(BERATER_OUTPUTS.patternBrief):       KURZLEBIG_PROMPT.pattern_brief = BERATER_OUTPUTS.patternBrief
IF has_content(BERATER_OUTPUTS.architecturalBrief): KURZLEBIG_PROMPT.architectural_brief = BERATER_OUTPUTS.architecturalBrief

SWITCH modus:   # M1..M9-Mapping-Detail (impl_mode/tdd/scope): siehe modus-dispatch-reference.md
  "M1":  Skill(_I_orchestrate, args="{NAME} --worker-mode --scope=skeleton --batch={batch_arg} {stage_arg} --tdd=false --vault={VAULT}")   # Skelett
  "M2":  Skill(_I_orchestrate, args="{NAME} --batch={batch_arg} {stage_arg} --tdd=false --vault={VAULT}")   # I FULL, TDD off (LOW-Komplexitaet)
  "M3":  Skill(_I_orchestrate, args="{NAME} --batch={batch_arg} {stage_arg} --tdd=true  --vault={VAULT}")   # I + TDD-Inline (BL-169)
  "M4":  Skill(_SC_orchestrate, args="{NAME} {difficulty} {ceiling} {floor} -I --batch={batch_arg} --vault={VAULT}")             # SC INLINE
  "M5":  Skill(_SC_orchestrate, args="{NAME} {difficulty} {ceiling} {floor} --batch={batch_arg} --vault={VAULT}")               # SC FULL SYMBIOSE
  "M6":  Skill(_SC_orchestrate, args="{NAME} {difficulty} {ceiling} {floor} --batch={batch_arg} --vault={VAULT}")               # SC FULL + TDD (tdd=true)
  "M7":  Skill(_SC_orchestrate, args="{NAME} {difficulty} {ceiling} {floor} --mode=analyse --batch={batch_arg} --vault={VAULT}") # SC PURE ANALYSE
  "M8":  # PR-Review — Exit-Code-gated zwischen den 3 Calls (BL-210): bei FAIL → ABORTED, Folge-Calls SKIP
    IF Skill(_T_orchestrate, args="{NAME} --vault={VAULT}") != 0:  DF_BATCH_STATE.last_failure="m8_test_fail"; df_status="ABORTED"; EXIT
    IF Skill(_smoothing,     args="{NAME} --vault={VAULT}") != 0:  DF_BATCH_STATE.last_failure="m8_smoothing_fail"; df_status="ABORTED"; EXIT
    Skill(_presentation, args="{NAME} --vault={VAULT}")
  "M9":  # WP-Research (HiL in C3 eingeholt). Bottleneck-Trigger (BL-206): bei Route via BL-206 SCHRITT 2.5 →
         # WP_PIPELINE_STATE.bottleneck_trigger=true + bottleneck_affected_items (siehe modus-dispatch-reference.md).
    Skill(_WP_orchestrate, args="{difficulty} {ceiling} {floor} --bl-source={BL_ID} --vault={VAULT}")
  DEFAULT: Logge FEHLER: "[DISPATCH-INLINE] Unbekannter Modus: {modus}"; df_status = "ABORTED"; EXIT

# Audit-Slot fuellen (Self-Audit). Per-Batch → dispatches[]-Liste (sub_batch_id/stage/tdd_flag/
# gewaehlter_modus/items/pipeline_route/vault/batch_arg/ts); Single-Mode → Single-Eintrag (source=team_lead_inline).
IF DF_BATCH_STATE.current_sub_batch_id != null:
  BERATER_OUTPUTS.executionDispatch ??= {source: "per_batch_loop", dispatches: []}
  BERATER_OUTPUTS.executionDispatch.dispatches.append({sub_batch_id: sub_batch_id, stage: current_stage,
    tdd_flag: (modus IN ["M3","M6"]), gewaehlter_modus: modus, items: items_to_process,
    pipeline_route: DF_BATCH_STATE.pipeline_route, vault: VAULT, batch_arg: batch_arg, ts: now()})
ELSE:
  BERATER_OUTPUTS.executionDispatch = {source: "team_lead_inline", gewaehlter_modus: modus,
    pipeline_route: DF_BATCH_STATE.pipeline_route, vault: VAULT, batch_arg: batch_arg, ts: now()}
```

### SCHRITT 2.2: Worker-FAIL-Pruefung
Bei `BERATER_OUTPUTS.executionDispatch.status == "FAIL_*"`: Logge Error → `df_status = ABORTED` → EXIT.

## PHASE 3 + PHASE 4 — VERLAGERT (BL-NEW-12 → BL-222/FIX2)

> Phase 3 (BUILD-Sanity, batchEnde) + Phase 4 (loopDecision + Routing) wurden in `/_SDF_orchestrate_post`
> ausgelagert (Skill-Context-Refresh erzwingt Phase 3 strukturell). Loop-Pattern + INV-HANDOVER-1 /
> INV-MOTOR-1/2 / INV-AUDIT-CHAIN + loop_decision-Routing-Doku: **Lies `{META}/sdf/outer-loop-doctrine.md`.**

```
# Pre-SDF macht NUR: Phase 0 → 1.0 analyse → pending Sub-Batches → Workflow(dispatch_implement)
# → Phase 3.4 batchEnde → loop_decision auswerten. KEIN in-Skill Stage-Loop / Inline-_I_orchestrate /
# Caller-Self-Chain. loop_decision-Routing (Lead, NACH Workflow-RETURN) — siehe OUTER-LOOP-WRAPPER:
#   RE-BATCH → Skill(_SDF_orchestrate --resume) · SOFT-REPRIO → _IDF_orchestrate --mode=recluster ·
#   ROLLBACK → _IDF_orchestrate --mode=recheck · TERMINATE → Phase FINAL.
# Im altmodischen Pfad besitzt _SDF_orchestrate_post (via I/SC-Chain) Stage-Loop + RE-BATCH + TERMINATE.
```

## PHASE FINAL: DONE (nach Phase 3)

```
# Terminal-Zustand — SDF endet nach Phase 3. BDF uebernimmt (prueft PL → naechster Batch / Post-Flow).

# CHECKLIST final (BL-035): sdf_post_gap_checklist.final = DONE; Manifest aktualisieren;
# audit_jsonl_append SEQUENCE_CHECK (step=final, checklist 6/6 DONE).
# Protokoll-Rollover (Pattern B): prepend DF_orchestrate-Zusammenfassung (Route/Batch/difficulty/
# max_cycles/sc_srs_last/df_start/df_end/Ergebnis DONE/Post-GAP 6/6) an _manifest_protokoll.md (W18).

# CHECKPOINT C: HiL nach Finish (BL-042) — nach Rollover, VOR TeamDelete.
Lies GLOBAL_HIL aus {VAULT}/_session_params.md
IF GLOBAL_HIL == "off":  Logge: "[HiL-SKIP] Checkpoint C auto-skipped (HiL=off)"
ELSE: AskUserQuestion("Checkpoint C: Beobachtungen?"): (1) nichts → weiter; (2) "PL: {text}" → Append
    "- [ ] OBSERVATION: {text} (Quelle: Checkpoint C, {NAME})" an {VAULT}/_parking-lot.md;
    (3) Freitext → Append "  Checkpoint-C-Kommentar: {text}" an _manifest_protokoll.md
# Volle 3-Optionen-Konditional-Logik (Option-1 Logge / Option-2 PL-Append mit Datum / Option-3 Freitext→_manifest_protokoll.md): Lies `{META}/sdf/checkpoint-c.md`.

TeamDelete: "sdf-{NAME}"
# BL-349 / INV-TEAM-GC-1: scheitert TeamDelete mit "Cannot cleanup team with N active member(s)" →
# tote Worker DIESER Session → `py .claude/scripts/team_gc.py strip sdf-{NAME}` → TeamDelete erneut.
df_state_transition(IDLE, 0, null, "Pipeline IDLE — bereit fuer naechsten Aufruf")
# BL-376 Fund#2 (INV-PROV-TRENNUNG): SDF erhaelt die Provenance via propagate_provenance —
# batchEnde registriert source_provenance-Ketten der implementierten Docs (NICHT BERATER_OUTPUTS-
# Provenance, 2 getrennte Welten). Aufruf: propagate_provenance.py update {doc} --vault {VAULT_ROOT}
Logge: "=== SDF BATCH DONE === Batch {NAME}: {batch_total} Items staged. BDF prueft PL."
```

## ABORT-Handling und HiL-Punkte

→ **Lies `{META}/sdf/state-machine.md`** fuer: ABORT-Handling (Protokoll-Rollover, BDF-Signal,
Resume-Hinweis) + HiL-Punkte Gesamtuebersicht (SC-ABORT, TDD-MAX, SDF-MAX).
