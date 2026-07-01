# /_I_orchestrate - Team Lead I-Pipeline-Orchestrierung

```yaml
status: active
version: 4.1.0
created: 2026-02-15
updated: 2026-06-13   # BL-329: INV-INFRA-MODUS-FREI — Steps 9b/18b von tdd-Klammer geloest (Infra-Phase modus-unabhaengig)
op: ImplementationPipeline
phase: Meta
type: orchestration
chain_position: meta
team_based: true
depends_on:
  - _gap
  - _spec
feeds_into:
  - _SDF_orchestrate
  - _W_push_orchestrate
related:
  - _TDD_orchestrate (DEPRECATED 2026-05-09 BL-169 — Logik in I-Orchestrate Phase 2.2 absorbiert)
  - _SC_orchestrate
bl_134_pflaster: true
bl_134_pflaster_inserted: 2026-04-25
bl_134_pflaster_real_refactor_in: BL-135
bl_140_pflaster_code: true
absorbs_tdd_orchestrate: true        # NEU 2026-05-09 BL-169
stage_aware: true                    # NEU 2026-05-09 BL-168
default_tdd: true                    # NEU 2026-05-09 BL-169
batch_as_slice: true                 # NEU 2026-05-11 BL-NEW-29
default_slicing: false               # NEU 2026-05-11 BL-NEW-29 (war true)
accepted_params:
  - "--stage=N (1=Unit, 3=Integration, 6=E2E; BL-168)"
  - "--tdd=true|false (default: true; BL-169)"
  - "--slicing=true|false (default: false; BL-NEW-29 — Single-Slice = Batch-as-Slice)"
  - "--batch=item_ids"
  - "--vault=path"
```

## REVISION 2026-05-09 (BL-168 + BL-169) — Stage-Aware + TDD-Pipeline-Merge

> **BL-168:** I-Orchestrate akzeptiert `--stage=N` Param. Pro Stage werden
> Stage-spezifische Tests geschrieben (Stage 1=Unit, 3=Integration, 6=E2E).
> Stage-Auswahl pro Sub-Batch durch IDF Phase 7 (siehe `DF_BATCH_STATE.batch_stages`).
>
> **BL-169:** TDD-Pipeline (`_TDD_orchestrate`) wird mit I-Orchestrate **GEMERGED**
> zu einer einzigen flachen Pipeline mit ~20 sequentiellen Schritten pro Stage.
> Statt 2 separater Skill-Handoffs (I + TDD) und verschachtelter Phasen-Hierarchie
> gibt es jetzt eine FLAT-SEQUENCE: Blueprint-Steps → TDD-Steps → Stage-Closure
> als Top-Level-Schritte der I-Pipeline. `--tdd=true` (default) aktiviert
> die TDD-Schritte (Steps 9-18) im Stage-Loop. `--tdd=false` ueberspringt
> Steps 9-18, der Rest der Pipeline laeuft normal.
>
> **NEUE FLAT-SEQUENCE (~20 Steps PRO STAGE, BL-169 Merge):**
> ```
> # BLUEPRINT-PHASE (Steps 1-8 aus Original-I-Pipeline)
> Step 1:  Skill(_I_cleanCodeArchitect --stufe N)
> Step 2:  Skill(_I_requirementCheck --stufe N)
> Step 3:  Skill(_I_patternLibrary --stufe N)
> Step 4:  [ENTFERNT BL-231/BL-232 2026-05-30] Test-Coverage wird jetzt zu PLAN-Zeit in
>          IDF Phase 7.7 (_IDF_berater_testSearch) ermittelt → coverage_map (PERSISTENT).
>          Implement LIEST die coverage_map (covering_tests) statt neu zu suchen.
>          Step-Nummern unveraendert gelassen (Downstream-Refs); Step 4 ist No-Op.
> Step 5:  Skill(_I_goldDefine --stufe N)
> Step 6:  Skill(_I_blueprintQG --stufe N)
> Step 7:  Skill(_I_cleanCodeSlice --stufe N)        # pro Slice
> Step 8:  Skill(_I_mitose) + fanOut                  # Worktrees
>
 # ── INFRA-PHASE (Steps 9b/18b) — MODUS-UNABHAENGIG, NICHT an tdd geklammert (BL-329) ──
> # INV-INFRA-MODUS-FREI (BL-329, 2026-06-13): Setup/Teardown haengen am INFRA-BEDARF DER STAGE
> # (stage_N.infrastruktur != "none" OR setup.commands non-empty), NICHT am Modus/tdd-Flag. tdd=true/false
> # steuert NUR die Red/Refactor-CEREMONY (Steps 10/11/14-17) — NICHT ob Container/WebHost hochfahren.
> # Die INFRA-Steps 9b (_TDD_setup) + 18b (_TDD_teardown, finally/auch-bei-ABORT) laufen daher fuer JEDEN
> # Bau-Modus (M2 wie M3), sobald die geplante Stage Infra braucht. Setup-/Teardown-Wissen lebt in
> # stage_N.md (setup./teardown.-Sektionen + health_check), NIE im Lead-/Worker-Kopf (machine-not-context).
> # Step 9b: Skill(_TDD_setup)  IF stage_N.infrastruktur != "none" OR setup.commands non-empty (BL-NEW-53)
> #          Container/DB/WebHost spinup. 1x pro Stage. Idempotent (spinup-if-not-running). MODUS-UNABHAENGIG.
> # Step 18b: Skill(_TDD_teardown) IF Step 9b lief (BL-NEW-53, finally-Semantik, always-run/auch bei ABORT, best-effort).
> # Proper-Fix LIVE seit BL-329 (2026-06-13): der Motor-M2-Zweig (dispatch_implement.js detectInfraNeed +
> # runInfraSetup VOR _TDD_green + runInfraTeardown im finally) faehrt den IDENTISCHEN bedingten Infra-Rahmen
> # wie der M3-Zweig — der frueher fehlende M2-Maschinen-Step (nur ein Prompt-Satz; 1944-Stage-6-Schmerz) ist
> # ersetzt. Offen (BL-329 batch_2): AK-3 (G-TDD-STAGES-READY um setup/teardown/health_check-Pflichtfelder) +
> # AK-4 (Prozess-Infra-Schema {cmd,cwd,background,pid_capture} im stage_N-Schema).
>
> # TDD-CEREMONY (Steps 9-18 absorbiert aus _TDD_orchestrate, BL-169)
> # NUR die Red/Refactor-Ceremony ist tdd-geklammert (NUR wenn tdd == true). FOR slice IN slices:
> Step 9:  Skill(_TDD_init --stufe N)                 # 1x pro Stage (HiL-Wizard + Infra-Detektion needInfra; modus-frei, BL-329)
> Step 10: Skill(_TDD_red --slice S --stage N)        # Failing-Test schreiben  [CEREMONY — tdd==true]
> Step 9b: Skill(_TDD_setup) IF stage_N.infrastruktur != "none" OR setup.commands non-empty (BL-NEW-53)
>          # INFRA-PHASE (s.o.) — Container/DB/WebHost spinup. 1x pro Stage. Idempotent. MODUS-UNABHAENGIG (INV-INFRA-MODUS-FREI).
> Step 11: Skill(_TDD_execute) + RED-Assert           # bestaetigt FAIL  [CEREMONY — tdd==true]
>          + Skill(_TDD_monitor) PARALLEL if stage_N.infrastruktur != "none" (BL-NEW-62)
> Step 12: Skill(_TDD_green --slice S)                # minimaler Code (tdd) / M2-CODE-EMIT (tdd=false, BL-231 — laeuft IMMER)
> Step 13: Skill(_TDD_execute) + GREEN-Assert         # bestaetigt PASS (M2: bestehende Tests bleiben GREEN)
>          + Skill(_TDD_monitor) PARALLEL if stage_N.infrastruktur != "none" (BL-NEW-62)
> Step 14: Skill(_TDD_refactorCode --slice S)         # Opus  [CEREMONY — tdd==true]
> Step 15: Skill(_TDD_execute) + GREEN-Stay           # bestaetigt PASS  [CEREMONY — tdd==true]
>          + Skill(_TDD_monitor) PARALLEL if stage_N.infrastruktur != "none" (BL-NEW-62)
> Step 16: Skill(_TDD_refactorTests --slice S)        # [CEREMONY — tdd==true]
> Step 17: Skill(_TDD_execute) + GREEN-Stay           # [CEREMONY — tdd==true]
>          + Skill(_TDD_monitor) PARALLEL if stage_N.infrastruktur != "none" (BL-NEW-62)
> Step 18b: Skill(_TDD_teardown) IF Step 9b lief (BL-NEW-53, finally-Semantik)
>          # INFRA-PHASE (s.o.) — Container/Process cleanup. Always-run (auch bei ABORT). Best-effort. MODUS-UNABHAENGIG.
> Step 18: Skill(_TDD_check --slice S)                # GOLD?  [CEREMONY — tdd==true]
>
> # STAGE-CLOSURE (Steps 19-20)
> Step 19: Skill(_I_verify --slice S)                 # pro Slice
> Step 20: Skill(_I_fanIn) + Stage-QG (HiL)           # Slice-Consolidation
> ```
>
> **PRINZIP:** Ein einziger Step-Strom. Keine `Phase 2.2`-Subhierarchie.
> Pro Stage werden 8 Blueprint-Steps + 10 TDD-Steps + 2 Closure-Steps =
> 20 Top-Level-Steps der I-Pipeline ausgefuehrt. Bei `--tdd=false` (M2) laufen
> Steps 1-8 + `_TDD_init` (Infra-Detektion, modus-frei, BL-329) + `_TDD_green` + `_TDD_execute`
> (M2-CODE-EMIT, BL-231 — NICHT mehr "nur Blueprint+Closure"!) + 19, 20 — PLUS die INFRA-PHASE
> (`_TDD_setup` Step 9b + `_TDD_teardown` Step 18b) IF die Stage Infra braucht (INV-INFRA-MODUS-FREI, BL-329).
> M2 SCHREIBT Code via entkoppeltem `_TDD_green`. Das alte "nur 1-8,19-20" war der
> M2-Code-Gap (BL-231) und ist FALSCH; das fehlende M2-Infra-Setup war der M2-Infra-Gap (BL-329) und ist gefixt.
>
> **100% TDD-COVERAGE GARANTIERT (BL-169 2026-05-09):**
> ALLE Faehigkeiten von `_TDD_orchestrate` werden in I-Pipeline am Pipeline-Ende
> beibehalten — nichts wird gestrichen. Vollstaendige Funktions-Liste:
> - `_TDD_init` (HiL-Wizard fuer Test-Stage-Setup, INKL. Docker-spinup/DB-Migration bei Stage 3+) → Step 9
> - `_TDD_red` (Failing-Test schreiben pro Slice/Stage) → Step 10
> - `_TDD_execute` (Test-Suite Run, RED/GREEN-Assert — NUR dotnet test, KEIN Setup, BL-NEW-52) → Steps 11/13/15/17
>
> **WORKER-TRENNUNG SETUP vs EXECUTE (BL-NEW-52, 2026-05-12) — PFLICHT bei Stage 3+:**
>
> Bei Stage 1 (Unit-Tests): keine Trennung noetig — _TDD_init macht minimalen Setup,
> _TDD_execute laeuft `dotnet test --filter` direkt.
>
> Bei Stage 3 (Integration) und Stage 6 (E2E): SETUP und EXECUTE in 2 getrennten Workern:
>
>   1. **Setup-Worker** (`@i-tddinit-{slice}-s{N}`) via `Skill(_TDD_init, --stage={N})`:
>      - Docker-spinup (testcontainers / docker-compose)
>      - DB-Migration / Seed-Daten
>      - Healthchecks (Container ready?)
>      - Config-Setup (stage_N.md Konventionen, TRX-Logger-Path, etc.)
>      - Schreibt: TDD-STATE.md `state: SETUP_DONE` + `setup_artifacts: {...}`
>
>   2. **Lead VERIFIZIERT** Setup-DONE via audit + Heartbeat-Probe + TDD-STATE.md Read
>
>   3. **Execute-Worker** (`@i-tddexec-{slice}-s{N}-{red|green}`) via `Skill(_TDD_execute)`:
>      - NUR `Bash(dotnet test --filter "FullyQualifiedName=<FQN>" --no-build --logger trx)`
>      - Liest TDD-STATE.md fuer Setup-Path
>      - Schreibt: TDD-STATE.md `state: GREEN_VERIFIED | RED_VERIFIED`
>      - **VERBOTEN:** Container-Mgmt, Config-Editing, eigene Polling-Loops (BL-NEW-52)
>
> **VERBOTEN (Anti-Pattern, Case-Anchor `.claude/_parking-lot.md` BL-NEW-52):**
>   1 Worker fuer BEIDES — Worker scope-overstepped automatisch zu Container-Setup
>   wenn `dotnet test` fehlschlaegt (Container nicht da). Worker-Vertrag verletzt.
>
> **Crown-Armierung pro Worker getrennt:**
>   - `_TDD_init` Stage 3: 5-10 min (Docker spinup + Healthcheck)
>   - `_TDD_execute` Stage 3: 2-4 min (NUR test run, kein Setup)

> - `_TDD_green` (Minimaler Code fuer GREEN) → Step 12
> - `_TDD_refactorCode` (Opus, Code generischer machen) → Step 14
> - `_TDD_refactorTests` (Tests spezifischer machen) → Step 16
> - `_TDD_check` (GOLD-Check, OK?) → Step 18
> - **Ring-Planung** (Test-Ring pro Slice, war TDD-7b) → Teil von Step 9 _TDD_init
> - **Verify pro Slice** (war TDD-Schritt 9) → Step 19 (`_I_verify --slice S`)
> - **FanIn pro Stage** (Slice-Konsolidation, war TDD-Schritt 10) → Step 20
> - **Stufen-QG mit HiL** (war TDD-Schritt 11) → Teil von Step 20
> - **CALLER-GUARD** (NEEDS_TDD-Signal-Check) → ELIMINATED (kein Handschuh-Wechsel
>   mehr noetig, weil keine separate TDD-Pipeline). Stattdessen: I-Orchestrate
>   `--tdd`-Param-Validation in Phase 0.
> - **PUPPET-MASTER-REGELN TDD** (1 Worker pro Step) → ueberlebt unveraendert,
>   Team Lead spawnt 1 kurzlebigen Worker pro Step 9-18 (gleiche INV-PM-1/2).
>
> **TDD-Sub-Skills bleiben aktiv** (`_TDD_red`, `_TDD_green`, `_TDD_refactorCode`,
> `_TDD_refactorTests`, `_TDD_execute`, `_TDD_check`, `_TDD_init`) — sie sind
> jetzt Top-Level-Steps der I-Pipeline am Pipeline-Ende, nicht Sub-Skills eines
> separaten TDD-Orchestrators. NUR `_TDD_orchestrate.md` selbst ist DEPRECATED.
>
> **VORPHASE (vor Step 1) und NACHPHASE (nach Step 20)** bleiben unverändert:
> - VORPHASE: Resume-Guard, Team Setup, Kurzlebig-Prompt, Team Lead Steuerung
> - NACHPHASE: verify global, Scope-Gate, Rollover (Pattern B)
>
> **F109-Mitigation:** Mega-Agent-Pattern eliminiert — Worker kann nicht mehr
> "I + TDD" beide skippen, weil nur 1 Pipeline-Skill existiert. Jeder der 20
> Steps muss als eigener `Skill(...)`-HANDOFF im Audit erscheinen, sonst
> Pipeline-Verletzung (siehe BL-167 INV-MODUS-7).

## Stage-Lifecycle (BL-408) — konsolidierter Vertrag

> Festgezurrter Vertrag der INFRA-PHASE Steps 9b/18b als benannte AK-1..5:
>
> **AK-1 setup:** Step 9b `_TDD_setup` bringt das System in den Stage-Zustand.
> Commands werden aus der stage-def via `resolve_vault_stage` gelesen (BL-392-Schema-Read).
> Container/DB/WebHost spinup — 1x pro Stage, idempotent (INV-SETUP-5).
>
> **AK-2 test-run:** Die I-Pipeline-Test-Arbeit (Steps 10-17 TDD-Ceremony + Step 12 M2-emit)
> laeuft sandwiched zwischen setup (AK-1) und teardown (AK-3). Setup muss abgeschlossen
> sein (SETUP_DONE) bevor der erste RED/GREEN-Step startet.
>
> **AK-3 teardown:** Step 18b `_TDD_teardown` laeuft NACH Batch-Ende mit finally-Semantik —
> always-run, auch bei ABORT (INV-TEARDOWN-3). Best-effort: Fehler im Teardown blockieren
> nicht den Pipeline-Fortschritt, werden aber geloggt.
>
> **AK-4 verdrahtung:** setup + teardown sind feste Steps der INFRA-PHASE, modus-unabhaengig
> (INV-INFRA-MODUS-FREI, BL-329). Beide Steps idempotent (INV-SETUP-5) + resume-sicher;
> teardown implementiert try/finally (INV-TEARDOWN-3). Die Infra-Bedingung
> (`stage_N.infrastruktur != "none" OR setup.commands non-empty`) entscheidet ob die
> INFRA-PHASE laeuft — NICHT der tdd-Flag oder Modus.
>
> **AK-5 resources:** setup ACQUIRED alle deklarierten Ressourcen (`acquire_all`, INV-SETUP-9,
> BL-247/BL-368-Lock); teardown RELEASED sie (`resources_released`, INV-TEARDOWN-3).
> Kein Ressourcen-Leak bei ABORT: teardown-finally garantiert Release auch bei Pipeline-Fehler.
>
> Verweise: BL-NEW-53 (setup/teardown-Steps), BL-329 (finally-Infra, INFRA-Phase-Proper-Fix),
> BL-247 (resource acquire/release), BL-392 (resolve_vault_stage schema), BL-368 (Lock-Primitive).

---

## BL-173 Manifest-Routing (NEU 2026-05-18)

**Manifest-Scope-Split aktiv** (siehe BL-173, INV-MANIFEST-SPLIT-1..4):

| State-Block | Heimat | Helper |
|---|---|---|
| I_PIPELINE_STATE | `{bl_folder}/_manifest.md` | `manifest_reader.read_bl_block(bl_id, "I_PIPELINE_STATE")` |

**Pfad-Aufloesung:**
- Factory-State: `manifest_reader.read_factory_block(...)` ODER direkt `{vault_root}/_factory_manifest.md`
- BL-State: `manifest_reader.read_bl_block(bl_id, ...)` ODER direkt `{bl_folder}/_manifest.md`
- Legacy-Fallback aktiv solange `is_split_active() == False` (1-Sprint-Uebergang)

**Migration:** `py -3 .claude/scripts/migrate_manifest_split.py migrate --vault-root="..." --rollback-tag=YYYY-MM-DD`

## REVISION 2026-05-11 (BL-NEW-29) — Batch-as-Slice (Minimal-Surgical)

> **KERN-PRINZIP:** Slice-Count = 1 (Batch IST der Slice). Mit BL-168 (batch_stages)
> + BL-NEW-12 (Pre/Post-SDF Split) ist BATCH bereits der kleinste sinnvolle Scope.
> IDF Phase 7 hat schon pro PL-Item gesliced. Sub-Slicing innerhalb Batch erzeugte
> nur Race-Bedingungen + Token-Waste. Konkrete Live-Run-Daten + Token-Profile in
> `.claude/_parking-lot.md` (BL-NEW-29 Batch-as-Slice Anchor).
>
> **WAS SICH AENDERT (3 Defaults):**
> - `slicing` Default: `true` → **`false`** (Batch-as-Slice)
> - `worktree_parallel`: `slicing` (= false als Default)
> - `_I_cleanCodeArchitect` produziert bei `slicing=false` **1 Slice-Plan-Eintrag**
>   (sub-components als Koordinations-Hints im Slice, nicht als Trenner)
>
> **WAS NICHT GELOESCHT WIRD:**
> - `_I_cleanCodeSlice` bleibt aktiv — sein Wert ist Code-Planung + Pattern-Reuse
>   fuer den 1-Slice (= ganzer Batch)
> - `_I_mitose`, `_I_fanOut`, `_I_fanIn` bleiben aktiv — AUTO-SKIP via existierender
>   `Single-Slice: SKIP`-Logik in `_I_berater_blueprintLoop` (Schritt 6 Zeile 181)
> - Forward-Compat: `slicing=true` + `fanout>1` reaktiviert parallel-Modus
>
> **PIPELINE-FLOW UNVERAENDERT (Step-Nummern stabil):**
> - Steps 1-4 Blueprint, Step 5 cleanCodeSlice (1 Slice produziert), Step 6 SKIP,
>   Steps 9-18 TDD (1 Iteration auf BATCH-Slice), Step 19 verify, Step 20 SKIP
> - TDD-Worker bei Step 10/12 bearbeitet den ganzen Batch in 1 Aufruf
>   (z.B. alle 10 DTOs einer Hierarchie in 1 RED → 1 GREEN → 1 REFACTOR)
>
> **STG-G POST_HANDOVER unveraendert:** Skill(_SDF_orchestrate_post) bleibt Pflicht.
>
> **MULTI-STAGE pro Batch (batch_stages = [1,3,6]):**
> I-Orchestrate laeuft 3× (1 Aufruf pro Stage), jeweils komplett Blueprint→TDD→Closure.
> POST_HANDOVER erst nach LETZTER Stage.
>
> **Multi-Batch-Parallelism (Feature-Ebene):** ueber BL-NEW-14 (BDF spawnt 2-3
> SDF-Instanzen parallel auf verschiedenen Batches), NICHT innerhalb eines Batches.

---

```
+======================================================================+
| META-COMMAND: /_I_orchestrate                                        |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU - die ausfuehrende Claude-Instanz)              |
|   CONSTRAINT: Team Lead fuehrt KEINEN Code aus, KEINE Tests.         |
|   Team Lead = reiner Process Manager (spawn, track, decide).         |
|   ALLES was Code oder Tests betrifft → Worker spawnen.               |
| AGENTS: Kurzlebige Single-Command-Agents (Modell: sonnet)            |
|         1 Agent = 1 Command = 1 Batch. Kein Worker-Loop.             |
|                                                                        |
| ZWECK: I-Pipeline ~20 Steps pro Stage (Blueprint+TDD+Closure absorbiert) |
|                                                                        |
| PIPELINE (BL-169 Flat-Sequence Merge 2026-05-09):                     |
|   VORPHASE (Schritt 0):                                               |
|     Resume-Guard, Team Setup, KurzlebigPrompt, Team Lead Steuerung   |
|     Manifest Init                                                      |
|                                                                        |
|   STUFEN-LOOP (pro Stufe N=current_stage aus --stage Param):          |
|                                                                        |
|     BLUEPRINT-PHASE (Steps 1-8):                                      |
|       1. /_I_cleanCodeArchitect --stufe N                              |
|       2. /_I_requirementCheck --stufe N   [CaseStudy KV-1]            |
|       3. /_I_patternLibrary --stufe N     [BL-044]                    |
|       4. /_I_testSearch --stufe N                                      |
|       5. /_I_goldDefine --stufe N                                      |
|       6. /_I_blueprintQG --stufe N                                     |
|       7. /_I_cleanCodeSlice --stufe N (1 Slice bei slicing=false; BL-NEW-29) |
|       8. /_I_mitose + /_I_fanOut (AUTO-SKIP bei Single-Slice; BL-NEW-29)|
|                                                                        |
|     TDD-PHASE (Steps 9-18, NUR wenn --tdd=true; BL-169 absorbiert):   |
|       9. /_TDD_init --stufe N (HiL-Wizard, 1x pro Stage)              |
|      10. /_TDD_red    --slice S --stage N (RED-Test schreiben)        |
|      11. /_TDD_execute (RED-Assert: Test FAIL)                         |
|      12. /_TDD_green  --slice S (minimaler Code)                       |
|      13. /_TDD_execute (GREEN-Assert: Test PASS)                       |
|      14. /_TDD_refactorCode  --slice S (Opus)                          |
|      15. /_TDD_execute (GREEN-Stay)                                    |
|      16. /_TDD_refactorTests --slice S                                 |
|      17. /_TDD_execute (GREEN-Stay)                                    |
|      18. /_TDD_check  --slice S (GOLD?)                                |
|                                                                        |
|     STAGE-CLOSURE (Steps 19-20):                                      |
|      19. /_I_verify --slice S (pro Slice; bei Single-Slice = ganzer Batch)|
|      20. /_I_fanIn (AUTO-SKIP bei Single-Slice; BL-NEW-29) + Stage-QG  |
|                                                                        |
|     → Stage-Transition (commit + Handschuh-Wechsel zurueck zu SDF)    |
|                                                                        |
|   NACHPHASE (nach allen Stages, BL-054):                              |
|     21. /_I_verify global                                              |
|     22. Scope-Gate (i_core_result + pipeline_mode)                     |
|     23. I_PIPELINE_STATE Rollover (Pattern B, W11)                     |
|                                                                        |
| TOTAL: ~20 Top-Level-Steps PRO STAGE (BL-169 Merge)                   |
|        Bei --tdd=false (M2): 1-8 + _TDD_green/_execute + 19-20 (BL-231)|
| SCOPE: full (IMMER — BL-054)                                          |
| HiL: Step 9 (Test-Suite-Init) + Step 18 (GOLD-Check) + Step 20 (QG)  |
+======================================================================+
```

---

## VERTRAG

```
WORKING_DIR = resolve_bl_path(BL_ID)  # INV-VAULT-9

LIEST (BL-045 Vault-First):
  {WORKING_DIR}/_manifest.md          (I_PIPELINE_STATE — per-Story, BL-155 AK-1)
  {VAULT}/_manifest.md                (NAME, SCHWIERIGKEIT, BDF_PIPELINE_STATE — global)
  {VAULT}/Task.md                     (Task-Definition)
  {VAULT}/.../Model/{NAME}_Model.md   (Feature-Modell — PFLICHT-READ, Guard G-MODEL-READ)
    FALLBACK: .claude/models/{NAME}_Model.md
  Stage-{N}-Metadaten via resolve_vault_stage.resolve_stage(N) (BL-392 AK-CONSUMER-REWRITE):
    migriert -> {VAULT}/Stage/stage_N_<name>/ (Concern-Slices); Dual-Read-Fallback ->
    Legacy-Monolith .claude/meta/implementation/stage_{N}.md (IDENTISCH zu heute). KEIN Direkt-Glob.
  {META}/implementation/guards.md     (Pre-Pipeline Guards)
  {META}/implementation/handoff-protocol.md  (SC→I Uebergabe — WIE)
  {VAULT}/.../SC/{NAME}-HANDOFF.md                  (SC→I Uebergabe — WAS, BL-007)
    FALLBACK: {WORKING_DIR}/.claude/analysis/synthese/{NAME}-HANDOFF.md
  BERATER_OUTPUTS.patternBrief.matched_patterns  (von _SDF_berater_patternBrief, ARCH-9)
    → Single-Source fuer _I_patternLibrary Schritt 1.5 (ARCH-8)
    → Optional: fehlendes patternBrief → _I_patternLibrary faellt auf MCP-Fallback zurueck

SCHREIBT STATE (_manifest.md):
  I_PIPELINE_STATE: Aktueller Block (resume_zaehler IMMER behalten — W11)
  i_core_result: Letzter I-Lauf (kompakt)
  pipeline_mode, i_gate_response, handoff_consumed

SCHREIBT STATE — BERATER_OUTPUTS-Slot PRO Phase (BL-464, distinct dot-Slots 4 -> >=7):
  BERATER_OUTPUTS.blueprint   : { status, exit_code, last_berater }   # Payload-frei (nur Marker)
  BERATER_OUTPUTS.goldDefine  : { status, exit_code, last_berater }
  BERATER_OUTPUTS.testSearch  : { status, exit_code, last_berater }
  BERATER_OUTPUTS.red         : { status, exit_code, last_berater }
  BERATER_OUTPUTS.green       : { status, exit_code, last_berater }
  BERATER_OUTPUTS.refactor    : { status, exit_code, last_berater }
  BERATER_OUTPUTS.verify      : { status, exit_code, last_berater }
  # Slot-Key-Konvention: lowercase camelCase Phasenname (analog A's BERATER_OUTPUTS.modusErkennung).
  # KEINE Berater-Payload im Manifest — nur status/exit_code/last_berater (siehe DATENFLUSS-PRINZIP + INV-DATA-I-1).

SCHREIBT PROTOKOLL (_manifest_protokoll.md, bei I-Abschluss):
  ## I-Pipeline Archiv [{Datum}]
  [Historische abgeschlossene I_PIPELINE_STATE-Bloecke]
  Pattern B: State (resume_zaehler) + Protokoll (historische Bloecke)
  Prepend-Mechanismus (W18): last_append + append_count aktualisieren

INVARIANTE W11 (KRITISCH):
  resume_zaehler[slice][cmd] NIEMALS ins Protokoll rotieren (W11, R5)
  resume_zaehler ist Stagnations-Detektor = Live-State — bleibt IMMER in _manifest.md

DATENFLUSS-PRINZIP (BL-464, analog IDF Z56-60 / Z345-362):
  Berater lesen+schreiben ueber IHRE Vault-Vertragsdateien (Blueprint/Spec/Model/Test/...).
  Berater schreiben NIE Payload ins Manifest — NUR exit_code-Marker (BERATER_OUTPUTS.{phase}).
  Der Lead liest NIE Berater-Payload aus dem Manifest; er liest+schreibt AUSSCHLIESSLICH
  Zustand (I_PIPELINE_STATE.phase + BERATER_OUTPUTS.{phase}.exit_code/status).
  Datenfluss = Vertraege (Vault-Dateien). Manifest = Zustand ("wo sind wir gerade").

HAUPTPRODUKT: CODE (via Worker-Agents)

INVARIANTEN:
  - Team Lead fuehrt KEINE Commands selbst aus (R2)
  - 1 Agent = 1 Command = 1 Batch (R3, R4)
  - Kein Agent spawnt Sub-Agents (W7, R9)
  - Manifest-Update VOR /compact und nach JEDER Stufe (R7)
  - Stagnation = resume_zaehler[slice][cmd] >= 5 (Manifest-basiert)

PROZESS-INVARIANTEN (BL-016 Epic E3):

  INV-DATA-I-1 (BL-464): Der Lead liest/schreibt AUSSCHLIESSLICH I_PIPELINE_STATE +
    BERATER_OUTPUTS.{phase}.exit_code/status — NIE Berater-Payload. Datentraeger-Kette
    laeuft ueber die Berater-Vertragsdateien (Vault), Manifest traegt nur Zustand.
    Schwester von IDF INV-DATA-1 (Z110) + A INV-DATA-1 (Z164).

  INV-PM-1 (RF-06, AK-06-01): Worker-Pflicht ABSOLUT
    Auch bei Inline/Easy/Trivial MUSS ein Worker gespawnt werden.
    Team Lead fuehrt KEINEN Code, KEINE Tests, KEINE Builds selbst aus.

  INV-PM-2 (RF-06, AK-06-02): Handschuh-Wechsel = Skill-Load (frisch)
    Agent() statt Skill() ist Prozess-Verletzung UNABHAENGIG vom Ergebnis.

  INV-AO-CALLER (Sanity-Check V11/V12, 2026-05-07/2026-05-08):
    Skill(_I_orchestrate) DIREKT vom Team Lead — kein Hub-Delegate via
    `Agent(general-sonnet, prompt="orchestrate ...")`. Sub-Agent wird Mega-
    Agent (Berater-Skill-Stellen werden Inline-Logik). CLAUDE.md Z6 +
    _A_orchestrate INVARIANTEN. Beweis: DCSRE-2014 Hot-Fix.

  INV-HW-1 (RF-07) — OBSOLETE 2026-05-09 (BL-169):
    Original-Wortlaut: "SC ↔ SDF ↔ I ↔ SDF ↔ TDD — IMMER durch SDF.
    I ruft TDD NICHT direkt auf. I signalisiert NEEDS_TDD → SDF routet.
    Heilige Trinitaet: Hub-Invariante (CaseStudy DCSRE-1430)."
    --
    Status 2026-05-09: OBSOLETE durch BL-169 (TDD-Absorption in I-Pipeline).
    TDD-Schritte (RED/GREEN/REFACTOR/CHECK/Verify/FanIn/Stage-QG) sind jetzt
    Steps 9-20 der I-Pipeline am Pipeline-Ende. Kein NEEDS_TDD-Signal noetig
    — die TDD-Steps laufen automatisch wenn `--tdd=true` (default). Hub-Routing
    SC ↔ SDF ↔ I bleibt; SDF ↔ TDD entfaellt (TDD ist nicht mehr eigener Pipeline-
    Knoten).

  INV-HW-1-NEU (RF-07-NEU, BL-169 2026-05-09):
    Pro Stage genau 1 Skill-Handoff: Skill(_I_orchestrate --stage=N --tdd=true).
    I-Pipeline fuehrt 100% der TDD-Funktionen am Pipeline-Ende inline aus
    (Steps 9-20). Keine Worker darf TDD-Sub-Skills direkt aufrufen ohne
    vorhergehende Skill(_I_orchestrate)-HANDOFF im Audit. F109-Mitigation.

  INV-PROCESS-STRICT (NEU 2026-05-10 BL-174 — KNOCHENHARTE GEGENLEISTUNG zu M1;
  KORRIGIERT 2026-06-18 — M1-Doc-Drift behoben: _I_orchestrate LAEUFT in ALLEN Modi):
    _I_orchestrate wird in JEDEM Bau-Modus geladen — M1 via --scope=skeleton
    (condensed 4-Step-Subset, worker-mode), M2/M3 als volle ~20-Step-Pipeline. In
    JEDEM Modus MUESSEN die Steps als Skill-Handoffs an GESPAWNTE Worker laufen —
    KEIN Lead-inline, KEIN Lead-Shortcut (INV-PM-1 ABSOLUT, auch fuer M1: Skelett
    heisst weniger Steps, NICHT Lead-selbst).
    
    Folgende "Pragmatik"-Versuche sind ABSOLUT VERBOTEN und MUESSEN ABORT loesen:
      ❌ Lead-inline-Implementation > 30 LOC
      ❌ Direktes Code-Schreiben statt Skill(_I_cleanCodeArchitect/_I_codeAtomic/...)
      ❌ Mega-Agent-Spawn: Agent(general-*, prompt="implementiere X komplett")
      ❌ "Statt 10 Skill-Steps spawne ich einen Implementations-Worker mit komplettem Kontext"
      ❌ Jeder Versuch Phase 1-3 oder Steps 1-20 zu skippen
      ❌ NEU BL-NEW-41 (2026-05-11): "Pattern jetzt etabliert, ich kann das jetzt schneller machen"
      ❌ NEU BL-NEW-41: "Multi-Step-Worker fuer komplettes batch_X Stage Y (Steps 1-20 in 1 Round-Worker)"
      ❌ NEU BL-NEW-41: "Worker bearbeitet alle 4 AKs als Single-Slice mit Steps 1-20"
      ❌ NEU BL-NEW-41: Worker-Name mit "-complete" oder "-round" Suffix (Indikator fuer Mega-Agent)
    
    NEU BL-NEW-41 — WORKER-PROMPT-SIZE-CHECK (Pre-Spawn Pflicht):
      Bevor JEDER Worker-Spawn:
        1. Pruefe Worker-Auftrag-Beschreibung: enthaelt sie >2 Step-Referenzen
           (z.B. "Steps 1-20", "RED+GREEN+REFACTOR", "Blueprint+TDD+Closure")?
        2. JA: ABORT mit "[INV-PROCESS-STRICT] Worker-Auftrag umfasst mehrere Steps —
           muss als separate Skill-Handoffs aufgerufen werden, kein Multi-Step-Worker"
        3. NEIN: weiter
      Diese Regel ist HARTES VERBOT — keine Ausnahme, auch nicht bei "Pattern etabliert"
      oder "Pragmatik-Vorteil". Jedes batch braucht eigene Skill-Handoff-Chain.
    
    Beweis fuer Notwendigkeit — siehe `.claude/_parking-lot.md` BL-NEW-41 fuer
    konkrete Live-Run-Anchors. Kern-Lehre (projekt-agnostisch):
    - Bei trivialen M2-Slice-Operationen (z.B. wenige LOC Konstanten) versucht Lead
      Mega-Agent-Spawn mit Begruendung "trivial". Verbot: "Process > Pragmatik —
      wenn M2 steht, dann M2 durchgezogen unabhaengig von Slice-Groesse".
    - Nach erfolgreichem Batch versucht Lead fuer Folge-Batch einen Multi-Step-
      Worker mit Suffix wie `-complete` / `-round` / `-all` mit Begruendung
      "Pattern jetzt etabliert". Verbot: gleiche Process-Discipline fuer ALLE
      Batches, unabhaengig von Lead-Confidence.
    
    Phase 0 (RESUME-GUARD) MUSS detect:
      - Lead-Plan-Statements wie "Pragmatisch ... statt 10 Skill-Steps spawne ich ..."
      - Lead-Plan-Statements wie "Pattern jetzt etabliert, ich spawne Multi-Step-Worker..."
      - Lead-Plan-Statements wie "Worker bearbeitet alle X AKs als Single-Slice mit Steps 1-Y"
      - Direkte Code-Edits ohne vorhergehenden Step-Skill-Load
      - Agent()-Calls mit Code-Generation-Prompt > 2 Steps
      - Worker-Name-Pattern mit "-complete" / "-round" / "-all" Suffix
      → bei jedem Match: ABORT mit "[I-PIPELINE] INV-PROCESS-STRICT verletzt — BL-NEW-41"
    
    KEIN legitimer Lead-inline-Pfad existiert — auch M1 NICHT (INV-PM-1 ABSOLUT,
    User-Direktive 2026-05-10; bestaetigt _SDF_berater_modusEntscheidung SCHRITT 1.5/9
    + _SDF_orchestrate SCHRITT 9 SWITCH). M1 ERREICHT _I_orchestrate sehr wohl — via
    Skill(_I_orchestrate --worker-mode --scope=skeleton) — und fuehrt das 4-Step-Subset
    (architecturalLibrary -> patternLibrary -> semanticLibrary -> codeAtomic) in einem
    GESPAWNTEN Worker aus (kein Lead-Code). Frueherer Stand ("M1 = Lead-inline ohne
    Skill-Load, _I_orchestrate nicht geladen") war die URSPRUENGLICHE BL-174-Idee,
    SUPERSEDED durch INV-PM-1-Haertung + BL-212 (--scope=skeleton-Verdrahtung 2026-05-24).
    KORRIGIERT 2026-06-18 (M1-Doc-Drift, ARCHITEKT-1 Pflaster).
    
    INV-PROCESS-STRICT ist die ARCHITEKTONISCHE GEGENLEISTUNG zur M1-Reaktivierung:
    Nicht beide locker, nicht beide strikt — M1 locker (Skelett), M2/M3 knochenhart.
    
    BL-NEW-41-WIRKUNG-2026-05-11: Confidence-Bias nach Pattern-Erfolg darf NIE
    Process-Discipline aufweichen. Jedes batch separately. Jeder Step separately.

  INV-WORKER-SKILL-LOAD (NEU 2026-05-12 BL-NEW-45 — TDD-Worker-Bypass-Schliessung):
    Worker-Spawn fuer Steps 1-20 (Blueprint + TDD + Closure) MUSS dem Worker-Prompt
    zwingend einen Skill-Load als ERSTE Action mitgeben. KEIN AUFTRAG-Inline-Prompt
    ohne vorgeschalteten Skill(_X)-Call.

    WORKER-PROMPT-TEMPLATE (PFLICHT, BL-NEW-45):
    ┌──────────────────────────────────────────────────────────────────────┐
    │ ZEILE 1 (PFLICHT, vor allem Detail):                                 │
    │   Skill(_TDD_{step_name}, args="{SLICE} {STAGE} {ITERATION}")        │
    │   (bzw. Skill(_I_{step_name}) bei Blueprint-Steps 1-8 / Closure 19-20)│
    │                                                                       │
    │ ZEILE 2+: KURZLEBIG_PROMPT (Worker-Kontext-Anhang):                   │
    │   polier_kontext: {matched_patterns, matched_semantics}              │
    │   PFAD-KONTEXT: worktree, vault, BLUEPRINT_BASE                      │
    │   GREEN-STATE oder RED-STATE                                          │
    │   AUFTRAG-DETAIL: spezifische Step-Detail-Anweisungen                 │
    └──────────────────────────────────────────────────────────────────────┘

    VERBOTENE Worker-Prompt-Muster (sofortiger ABORT):
      ❌ Worker-Prompt beginnt mit "AUFTRAG:" ohne vorgeschalteten Skill-Load
      ❌ Worker-Prompt enthaelt komplette _TDD_X-Logik inline (kopierter Skill-Inhalt)
      ❌ Worker-Prompt-Beispiel: "Worker fuer Step {N} _TDD_{step} ({model}). {STATE-INFO}. AUFTRAG: {konkrete Code-Anweisung}..."
         → MEGA-AGENT — Case-Anchor `.claude/_parking-lot.md` BL-NEW-45
         → Worker macht Refactor ohne PatternLibrary/SemanticLibrary-Konsultation, ohne Skill-Vertrag-Compliance

    KORREKTES Worker-Prompt-Beispiel (BL-NEW-45-konform):
      ```
      ZEILE 1: Skill(_TDD_refactorCode, args="{SLICE} {STAGE} {ITERATION}")

      ZEILE 2+: KURZLEBIG_PROMPT:
        polier_kontext:
          matched_patterns: [<Patterns aus _I_patternLibrary>]
          matched_semantics: [<Semantics aus _I_architecturalLibrary>]
          twin_file: <falls Twin existiert: Pfad zur Schwester-Implementierung>
        PFAD-KONTEXT:
          worktree: {WORKTREE_PATH}
          vault: {VAULT_PATH}
          BLUEPRINT_BASE: {VAULT}/4_Blueprint
        GREEN-STATE: {N}/{M} Tests passing
        AUFTRAG-DETAIL: <step-spezifische Anweisung, fachlich generisch>
        VERBOTEN: Direkt-Edit ohne Skill-Vertrag-Befolgung (SCHRITT 0..7).
      ```

    Phase 0 (RESUME-GUARD) MUSS auch detect:
      - Worker-Prompts ohne vorgeschalteten Skill(_X)-Call (Pre-Spawn-Validation)
      - Worker-Name-Pattern wie "@i-tddrefactor-*" mit AUFTRAG-only-Prompt
      → bei Match: ABORT mit "[INV-WORKER-SKILL-LOAD] BL-NEW-45 verletzt — Worker-Prompt muss Skill-Load enforcen"

    BL-NEW-45 — Lehre (Projekt-agnostisch, Case-Anchor `.claude/_parking-lot.md`):
    - Bei Worker-Spawn fuer TDD-Sub-Skills (Step 9-18) mit AUFTRAG-only-Prompt
      (kein Skill-Load als ZEILE 1) fuehrt Worker den Step inline aus ohne
      Skill-Vertrag-Compliance.
    - Folge: keine PatternLibrary-Konsultation, keine SemanticLibrary-Konsultation,
             kein polier_kontext-Cross-Check, kein SKILL_LOAD-Event in audit.jsonl.
    - Fix-Wirkung: INV-WORKER-SKILL-LOAD + Worker-Seite SCHRITT 0.0 in allen 6
      TDD-Skills. Worker prueft beim Start ob er via Skill() oder Inline geladen
      wurde — bei Inline-Pattern: ABORT mit BL_NEW_45_VIOLATION audit.

  INV-NO-HAIKU-IN-TDD (NEU 2026-05-12 BL-NEW-51 — Haiku-Verbot im TDD-Zyklus):
    Spawn-Pre-Check VOR jedem TDD-Worker-Spawn (Steps 9-18):
    Wenn worker_model == "haiku" UND skill IN {_TDD_init, _TDD_red, _TDD_green,
    _TDD_refactorCode, _TDD_refactorTests, _TDD_check, _TDD_execute}:
      → ABSOLUT VERBOTEN. ABORT vor Agent()-Spawn.

    DIESE INV ist UNABHAENGIG von /_crown:
      - Crown blockiert nur wenn Crown gerufen wird (post-spawn-arm)
      - INV-NO-HAIKU-IN-TDD greift VOR Agent()-Spawn (pre-spawn-validation)
      - Lead MUSS diesen Check selbst durchfuehren BEVOR `Agent(general-haiku, ...)` ausgefuehrt wird

    PFLICHT-PRE-SPAWN-LOGIK fuer Steps 9-18:
    ┌────────────────────────────────────────────────────────────────────────┐
    │  BEVOR Agent(...) oder Skill-Worker-Spawn fuer TDD-Step:               │
    │                                                                        │
    │  1. Bestimme target_skill (z.B. "_TDD_execute")                        │
    │  2. Bestimme worker_model (z.B. "haiku")                                │
    │  3. IF target_skill startswith "_TDD_" AND worker_model == "haiku":    │
    │       ABORT mit:                                                       │
    │         "[INV-NO-HAIKU-IN-TDD] BL-NEW-51 violation:                    │
    │          {target_skill} darf NICHT mit haiku gespawned werden.         │
    │          Mindest-Tier: sonnet. Erlaubt: sonnet | opus.                 │
    │          Live-Case: i-tddexec-pl1-s3-verify_2026-05-12_stuck_10min."   │
    │       audit_jsonl_append({                                              │
    │         type: "BL_NEW_51_TDD_HAIKU_PRE_SPAWN_BLOCKED",                  │
    │         skill: target_skill, requested_model: haiku, ...                │
    │       })                                                                │
    │       Re-Spawn mit "general-sonnet" statt "general-haiku"               │
    │  4. ELSE: weiter mit Spawn                                              │
    └────────────────────────────────────────────────────────────────────────┘

    BL-NEW-51 — Lehre (Projekt-agnostisch, Case-Anchor `.claude/_parking-lot.md`):
    - TDD-Sub-Skills mit mehrstufigen Test-Sequenzen (Container-spinup, Polling,
      Test-Capture, Log-Parse) sind fuer Haiku zu komplex — Worker stuckt/skipt
      bei polling/timeout/Recovery.
    - Crown SCHRITT 1.0 MODEL-VALIDATION blockiert vor-Spawn — Mindest-Tier sonnet
      via `forbidden_models: [haiku]` im Skill-Frontmatter.
    - Lead muss VOR Agent()-Call diese INV pruefen (zusaetzlich zu Crown).

    PFLICHT-WORKER-TYPE-MAPPING (Steps 9-18):
      Step 9  _TDD_init           → general-sonnet (min) | NIE general-haiku
      Step 10 _TDD_red            → general-sonnet (min) | NIE general-haiku
      Step 11 _TDD_execute        → general-sonnet (min) | NIE general-haiku [BL-NEW-51-CASE]
                                   + PARALLEL _TDD_monitor (sonnet) wenn stage_N.infrastruktur != "none" [BL-NEW-62]
      Step 12 _TDD_green          → general-sonnet (min) | NIE general-haiku
      Step 13 _TDD_execute        → general-sonnet (min) | NIE general-haiku
                                   + PARALLEL _TDD_monitor (sonnet) wenn stage_N.infrastruktur != "none" [BL-NEW-62]
      Step 14 _TDD_refactorCode   → model:opus  (PFLICHT — Opus fuer Pattern-Konsultation; Carrier general-sonnet, Spawn-model treibt, kein general-opus)
      Step 15 _TDD_execute        → general-sonnet (min) | NIE general-haiku
                                   + PARALLEL _TDD_monitor (sonnet) wenn stage_N.infrastruktur != "none" [BL-NEW-62]
      Step 16 _TDD_refactorTests  → general-sonnet (min) | NIE general-haiku
      Step 17 _TDD_execute        → general-sonnet (min) | NIE general-haiku
                                   + PARALLEL _TDD_monitor (sonnet) wenn stage_N.infrastruktur != "none" [BL-NEW-62]

DUAL-WORKER-SPAWN PATTERN (BL-NEW-62, 2026-05-12):
======================================================================
Bei stage_N.md.infrastruktur != "none" (typisch Stage 3+ Docker/testcontainers):
   Lead spawnt PARALLEL 2 Worker:
     - Worker A: _TDD_execute (sonnet)        — Test-Runner, schreibt TDD-STATE.state
     - Worker B: _TDD_monitor (sonnet)        — Docker/Parallelism/FQN-Match Monitor
                                                schreibt TDD-STATE.monitor.{...}
                                                SendMessage ALERT bei Anomalie
   Crown fuer beide armieren (separate Watchdogs).
   Worker B endet wenn Worker A DONE (oder eigener Timeout 30min).

Bei stage_N.md.infrastruktur == "none" (typisch Stage 1 Unit-Tests):
   SINGLE Worker _TDD_execute (Monitor unnoetig — lokale dotnet test, schnell)
      Step 18 _TDD_check          → general-sonnet (min) | NIE general-haiku

    Phase 0 (RESUME-GUARD) MUSS auch detect:
      - Lead-Plan-Statements wie "Agent(general-haiku, prompt='_TDD_execute...')"
      - Worker-Name-Pattern mit "haiku" Suffix bei TDD-Step-Spawn
      - Re-Spawn-Versuche mit haiku nach BL-NEW-51-Blockade
      → bei jedem Match: ABORT mit "[INV-NO-HAIKU-IN-TDD] BL-NEW-51 verletzt"
```

---

## STATE-MACHINE

```
INIT -> BLUEPRINT_RUNNING   -> BLUEPRINT_DONE
     -> GOLDDEFINE_RUNNING   -> GOLDDEFINE_DONE
     -> TESTSEARCH_RUNNING   -> TESTSEARCH_DONE
     -> RED_RUNNING          -> RED_DONE
     -> GREEN_RUNNING        -> GREEN_DONE
     -> REFACTOR_RUNNING     -> REFACTOR_DONE
     -> VERIFY_RUNNING       -> VERIFY_DONE
     -> COMPLETED | ABORTED_PROCESS_VIOLATION (exit_code=99, any phase)
```

**exit_code-Konvention (generalisiert aus dem Praezedenzfall Z891-892):**
Jede `<PHASE>_DONE`-Transition setzt `exit_code=0` (0=DONE). Prozess-/Vertrags-Verletzung in
JEDER Phase -> `phase="ABORTED_PROCESS_VIOLATION"` + `exit_code=99` (kein neu erfundenes
Schema — derselbe Marker, den der INV-PROCESS-STRICT-Self-Check unten (Z891-892) bereits nutzt;
hier nur als Block-Level-Konvention generalisiert: `exit_code=0`=DONE, `exit_code=99`=ABORTED).

**Modus-Geltung (INV-INFRA-MODUS-FREI-Schwester):** Die Transitions-Kette ist FIX 7-phasig und
haengt am STATE-HANDOFF, NICHT an tdd_enabled. Der State-Seam ist modus-unabhaengig — M2 (kein TDD)
durchlaeuft dieselbe Kette — RED/refactor degenerieren zur reinen State-Transition (`exit_code=0`,
kein Step-Effekt), werden NICHT aus der Kette entfernt. Wuerde man sie in M2 entfernen, haengt der
Seam wieder an TDD (Anti-Pattern) und der M2-Megaworker bleibt offen. (M2-Pfad-HAERTUNG selbst = BL-466.)

**[M2-SEAM-HARDENED] (BL-466 — Epic-BL-463-Abschluss, M2-Pfad verifiziert):** Der State-Seam
traegt die Phasen-Trennung modus-unabhaengig — auch im M2-Pfad (`tdd_enabled=false`). M2
degeneriert RED/refactor zur reinen `exit_code=0`-State-Transition (KEIN Phase-Skip, KEINE
Phase-Entfernung); die 7-Phasen-Kette + 5×[GATE P] + die BERATER_OUTPUTS-Slots greifen identisch
wie in M3. TDD/RED!=GREEN ist damit nur noch der **2. Notnagel** (Handoff-/Guard-Schicht:
guard_agent_prompt_validator / guard_idf_sdf_handoff / guard_sdf_post_handoff) — der **primaere**
Megaworker-Schutz ist dieser state-getriebene Vertrag (BERATER_OUTPUTS-Slot pro Step + State-Handoff
+ exit_code-Gate), NICHT TDD. Eingefroren durch `test_bl466_m2_seam.py` (grep-Charakterisierung).

**[EPIC-TERMINATION] BL-463 = TERMINATED/DONE (BL-464 + BL-465 + BL-466):** Das Epic
"I-Orchestrator strukturell megaworker-sicher (manifest-vertrag-driven)" ist abgeschlossen —
BL-464 (STATE-MACHINE + 7 BERATER_OUTPUTS-Slots), BL-465 (5×[INV-SPAWN] + 5×[GATE P]),
BL-466 (M2-Pfad-Verifikation + Regression-Beweis A/IDF byte-identisch + BL-230-Cluster stabil).
TDD ist hier der **2. Notnagel**, der state-getriebene Vertrag der primaere Schutz.

| Phase | Status-Wert (RUNNING/DONE) | Step-Skill (Referenz, KEIN Spawn — Spawn-Umstellung=BL-465) | Modus-Geltung |
|-------|----------------------------|--------------------------------------------------------------|---------------|
| blueprint | `BLUEPRINT_RUNNING` / `BLUEPRINT_DONE` | `_I_cleanCodeArchitect` .. `_I_blueprintQG` (Steps 1-8) | M1/M2/M3 |
| goldDefine | `GOLDDEFINE_RUNNING` / `GOLDDEFINE_DONE` | `_I_goldDefine` (Step 5) | M1/M2/M3 |
| testSearch | `TESTSEARCH_RUNNING` / `TESTSEARCH_DONE` | `_I_testSearch` (Step 4, IDF-7.7-coverage_map) | M1/M2/M3 |
| RED | `RED_RUNNING` / `RED_DONE` | `_TDD_red` (Step 10) | M3 voll; M2 degeneriert (exit_code=0) |
| GREEN | `GREEN_RUNNING` / `GREEN_DONE` | `_TDD_green` (Step 12) | M1/M2/M3 |
| refactor | `REFACTOR_RUNNING` / `REFACTOR_DONE` | `_TDD_refactorCode`/`_refactorTests` (Steps 14-17) | M3 voll; M2 degeneriert (exit_code=0) |
| verify | `VERIFY_RUNNING` / `VERIFY_DONE` | `_I_verify` (Step 19 + global Step 21) | M1/M2/M3 |
| END | `COMPLETED` / `ABORTED_PROCESS_VIOLATION` | — | — |

> **SCOPE-SPERRE (BL-464, gated 464<465<466):** Dieser Block DEKLARIERT die State-Kette + Slots
> (das FUNDAMENT). Er stellt KEINE inline-Skill-Calls auf Worker-Spawns um (BL-465), reduziert
> KEINE LOC (BL-465) und haertet KEINEN M2-Pfad / kein Regression-Termination-Gate (BL-466).
> Die Step-Skill-Spalte benennt NUR den verantwortlichen Step — die Spawn-Umstellung ist BL-465.

## WORKER-SPAWN-PATTERN (INV-SPAWN = INV-PM-5-aequivalent)

INV-SPAWN (= INV-PM-5-aequivalent, AKTIVER STRUKTURVERTRAG): Die 5 Top-Level-
  Berater-Phase-Skills (teamSetup / kurzlebigPrompt / teamLeadSteuerung /
  blueprintLoop / nachphase) MUESSEN ueber Worker-Spawn aufgerufen werden — der
  Team Lead laedt diese Skills NIE selbst inline. Pseudocode-Notation
  "Skill(skill='_I_berater_X', args=...)" wird semantisch interpretiert als:
     Agent(subagent_type=tier, prompt="Lade Skill _I_berater_X und fuehre
     Vertrag aus + schreibe BERATER_OUTPUTS.{phase}.{status,exit_code,
     last_berater} + stirb", team_name="i-{name}")
  Datenfluss = Vertraege (Berater lesen/schreiben Vault-Vertragsdateien);
  Manifest = NUR Zustand (exit_code-Marker). Lead liest NIE Berater-Payload aus
  dem Manifest, nur den Zustand. (Spiegelt A INV-PM-5 Z.209-219 + IDF INV-SPAWN.)

Jedes `Skill(skill="_I_berater_X", args=...)` der 5 Top-Level-Phasen unten ist
KURZSCHRIFT fuer:

  Agent(
    subagent_type="general-sonnet" | "general-haiku" | "general-purpose",
                                      # Tier laut Berater-Spec
    description="I-Pipeline Phase {N} {berater_name}",
    prompt="""
      Du bist kurzlebiger Worker fuer I-Pipeline Phase {N}.
      ENV: CLAUDE_BL_ID={bl_id}

      AUFGABE: Lade Skill _I_berater_X via Skill-Tool und fuehre den dort
      definierten Vertrag aus mit args="{args}".

      REGELN:
      - W7-Constraint: KEIN Sub-Agent-Spawning durch dich.
      - Schreibe BERATER_OUTPUTS.{phase}.{status,exit_code,last_berater} ins _manifest.md.
      - SendMessage an "team-lead" mit Ergebnis-Summary.
      - Worker stirbt nach Skill-Ausfuehrung.
    """,
    team_name="i-{NAME}"
  )

**Verbotene Anti-Pattern:**
- (X) Team Lead ruft `Skill(_I_berater_X)` direkt auf -> Direkt-Load (Megaworker)
- (X) Team Lead liest Skill-Markdown selbst und fuehrt aus
- (OK) Team Lead spawnt Worker via Agent(), Worker laedt Skill, schreibt Slot, stirbt

**SCOPE-NOTE:** Diese INV-SPAWN-Direktive deckt die 5 AEUSSEREN Top-Level-Berater-
Phasen (BL-465). Die INNEREN TDD-Step-Wellen (red/green/refactor/verify) sind
bereits spawn-diszipliniert via blueprintLoop-Berater (unveraendert).

**INV-MODUS-Reminder:** Worker darf modus-Feld NICHT setzen ausser via _SDF_berater_modusEntscheidung (BL-165 INV-MODUS-1).

---

## SCHRITT 0: BL-140 Batch-Pflaster (echter Branch)

<!-- BL-144 L4: Echter Branch-Header fuer Batch-Pflaster. INV-I-PFLASTER-3 unten. -->

## BL-134 PFLASTER: Batch-Input-Adapter (Sub-Pipeline)

**Eingefuegt:** 2026-04-25 als Teil von BL-134 Slice 3.

Diese Pipeline akzeptiert ab BL-134 oberflaechlich einen `batch={PL-Items}` Parameter
vom SDF-executionDispatch und iteriert intern **sequentiell** durch die Items
(kein paralleler Batch-Refactor).

### Vertrag (Pflaster)

- **LIEST:** Wenn `batch=` Param gesetzt -> Liste der PL-Items aus `DF_BATCH_STATE.batch_items` (vom executionDispatch durchgereicht).
- **ITERIERT INTERN:** `FOR item IN batch_items: pipeline_aufruf(item)` (sequentiell).
- **SCHREIBT pro Item:** `DF_BATCH_STATE.item_done.append(item_id)` nach erfolgreichem Pipeline-Durchlauf (Recovery-Hook).
- **EXIT:** Wenn alle Items DONE.

### BL-134-PFLASTER-MARKER (Pseudo-Code)

```
batch = lies CLI_PARAM("batch") ?? null
IF batch != null:
  Logge: "[BL-134-PFLASTER] i_orchestrate batch-modus: {len(batch)} Items sequentiell."
  FOR item IN batch:
    skip_if_done = item IN DF_BATCH_STATE.item_done
    IF skip_if_done: Logge "[BL-134-PFLASTER] SKIP {item} (bereits done)"; CONTINUE
    pipeline_aufruf(item)
    DF_BATCH_STATE.item_done.append(item)
    manifest.update()
  RETURN

# kein batch-Param -> normaler Single-Item-Pfad (Legacy)
```

### Echter Batch-Refactor

Dieser Pflaster ist Uebergangs-Loesung. Echter Batch-Support (paralleler
intern-Loop, Aggregat-Kontext) folgt im jeweiligen Pipeline-Refactor:

- **i_orchestrate echter Refactor:** BL-135

### INV-I-PFLASTER-1

Pflaster-Pfad MUSS sequentiell bleiben bis BL-135 den echten Refactor liefert.
Paralleler intern-Loop ohne explizite BATCH_STATE-Race-Locks ist VERBOTEN.

### BL-140 PFLASTER-CODE (echte Implementation)

```
# CLI-Param oder Manifest
batch = lies CLI_PARAM("batch") OR DF_BATCH_STATE.batch_items
IF batch != null AND |batch| > 0:
  Logge: "[BL-140-PFLASTER] i_orchestrate Batch-Modus: {len(batch)} Items sequentiell"
  FOR item IN batch:
    # Skip falls schon DONE
    IF item IN DF_BATCH_STATE.item_done:
      Logge: "[BL-140-PFLASTER] SKIP {item} (bereits in item_done)"
      CONTINUE

    # Original-Pipeline-Aufruf fuer dieses Item
    pipeline_main_logic(item)

    # Recovery-Hook
    DF_BATCH_STATE.item_done.append(item)
    manifest.update()

  RETURN  # Batch-Modus fertig

# Fallback: kein batch -> Single-Item-Pfad (Legacy)
pipeline_main_logic(NAME)
```

INV-I-PFLASTER-2 (NEU, BL-140):
Pflaster-Code MUSS sequentiell iterieren (kein paralleler Loop ohne Race-Lock).
Pflaster-Code MUSS item_done.append nach JEDEM erfolgreichen Item.
Pflaster-Code MUSS RETURN am Ende des batch-Pfads (NICHT in den Legacy-Pfad fallen).

INV-I-PFLASTER-3 (BL-144):
Echter Batch-Branch IM Pipeline-Body -- NICHT nur Doku am Datei-Ende.
Der SCHRITT-0-Block MUSS vor PHASE 1 aktiv ausgefuehrt werden (kein toter Doku-Anhang).

---

## Aufruf

```
/_I_orchestrate {NAME} [worktree_path] [--worker-mode] [--scope=skeleton|full] [--batch={AK}] [--stage=N] [--tdd=true|false]
```

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `NAME` | (Manifest) | Feature-Name. Falls nicht angegeben: lese `NAME:` aus `{VAULT}/_manifest.md`. Falls kein Manifest: FEHLER. |
| `difficulty` | normal | easy/normal/hard — Agent-Anzahl |
| `ceiling` | sonnet | Hoechstes Modell |
| `floor` | haiku | Niedrigstes Modell |
| `worktree_path` | (cwd) | Absoluter Pfad zum Arbeits-Ordner |
| `--worker-mode` | false | Worker-Mode: SKIP TeamCreate/Delete, nutze SC-Team (sc-{NAME}) |
| `--scope` | full | **NEU BL-174 (2026-05-10):** `skeleton` = M1 Bare-Minimum-Subset (4 Steps). `full` = volle I-Pipeline. Siehe `/_I_help_m1` |
| `--batch` | (Manifest) | AK-Liste fuer den Sub-Batch (z.B. `AK-CTX-2`) |
| `--stage` | 1 | Test-Stage (BL-168): 1=Unit / 3=Integration / 6=Controller-E2E |
| `--tdd` | (params) | true=TDD-Steps 9-18 inline (BL-169), false=skip TDD |

**Skalierung:**

| Rolle | easy | normal | hard |
|-------|------|--------|------|
| Team Lead | Opus | Opus | Opus |
| Synthese (W3) | 1 {ceiling} | 1 {ceiling} | 1 {ceiling} |
| Drafter (W2) | --- | 3 {middle} | 5 {middle} |
| Explorer (W1) | --- | 5 {floor} | 9 {floor} |

**Command-spezifische Wellen-Konfiguration (Blueprint-Phase):**

| Command | Wellen (normal) | Wellen (easy) | Begruendung |
|---------|----------------|---------------|-------------|
| _I_cleanCodeArchitect | 5-3-1 (W3=opus) | 1 opus | HOCH: 9 Quellen, Exploration, Architektur-Entscheidungen |
| _I_requirementCheck | 1 sonnet | 1 sonnet | NIEDRIG: mechanisches Gate, keine Exploration |
| _I_patternLibrary | 1 sonnet | 1 sonnet | NIEDRIG: MCP-Budget-begrenzt (3Q), Wellen sinnlos |
| _I_testSearch | 1 sonnet | 1 sonnet | NIEDRIG: Glob/Grep, mechanische Kategorisierung |
| _I_goldDefine | 1 sonnet | 1 sonnet | NIEDRIG: Zuordnung AK→Inventar, keine Exploration |
| _I_blueprintQG | 1 sonnet | 1 sonnet | NIEDRIG: 7 Pruefpunkte, mechanisches Scoring |
| _I_cleanCodeSlice | 3-1 (W3=opus) | 1 sonnet | MITTEL: horizontale Suche, Reuse-Scoring |

---

## GLOBALE PARAMETER (/_param Override)

```
Lies _session_params.md → difficulty, ceiling, floor, HiL, slicing, tdd, tdd_stages.
difficulty = params.difficulty
ceiling    = min(ceiling, params.ceiling)
floor      = max(floor, params.floor)
slicing    = params.slicing ?? false   # Default: false (BL-NEW-29 Batch-as-Slice; war true)
tdd        = params.tdd ?? true        # Default: true (BL-169: TDD-Steps 9-18 inline)
tdd_stages = params.tdd_stages ?? [1,2,3,4,5]  # Default: alle Stufen
stage      = params.stage ?? 1         # Default: 1 (BL-168: Test-Stage Unit/Integration/E2E)
scope      = args.scope ?? "full"      # Default: "full" (BL-174: "skeleton" = M1 Bare-Minimum-Subset)
Validierung: ceiling >= floor (sonst ceiling = floor + Warning)
middle = sonnet wenn ceiling>=sonnet, sonst haiku
worktree_parallel = slicing  # slicing steuert NUR Worktree-Parallelisierung

# BL-174 M1-Skelett-Subset (NEU 2026-05-10):
# Bei scope="skeleton" werden nur 4 Pflicht-Steps ausgefuehrt:
#   1. _I_architecturalLibrary  (Layer + ARCH-VERTRAG-Block)
#   2. _I_patternLibrary        (architektonische Patterns)
#   3. semanticLibrary lookup   (Naming-Konvention via _SL_conformance read-only)
#   4. _I_codeAtomic            (Bare-Minimum-Implementation)
# Skip: requirementCheck, testSearch, goldDefine, blueprintQG, Stufen-Loop S1..S5,
#       mitose, fanOut, fanIn, TDD-Steps 9-18.
# tdd, slicing werden in scope=skeleton IGNORIERT (auto-false).
# scope=skeleton impliziert worker_mode=true (User-Direktive: INV-PM-1 ABSOLUT).
# Trigger: nur via Skill(_SDF_berater_modusEntscheidung) Schritt 9 SWITCH M1-Eintrag.
# Siehe `/_I_help_m1` fuer vollstaendiges M1-Verhaltens-Bild.
IF scope == "skeleton":
  worker_mode = true                   # impliziert
  tdd         = false                  # M1 hat keine TDD-Phase
  slicing     = false                  # kein FanOut/FanIn
  tdd_stages  = [1]                    # nur Stage 1 erlaubt
  i_steps     = ["architecturalLibrary", "patternLibrary", "semanticLibrary", "codeAtomic"]
  Logge: "[I_orchestrate] SCOPE=SKELETON (BL-174 M1) — 4-Step-Subset, Worker-Mode forced"
ELSE:
  i_steps     = "full"                 # alle Steps

# slicing steuert NUR Worktree-Parallelisierung:
#   slicing=true  → Mitose/FanOut/FanIn aktiv (Slices parallel in Worktrees)
#   slicing=false → Mitose/FanOut/FanIn SKIP (Slices sequentiell im gleichen Branch)
#   Blueprint, Stufen, TDD-Steps 9-18, Architect, CleanCodeSlice laufen IMMER
#
# tdd steuert NUR die Test-First-Ceremony (red/refactorTests) — NICHT ob Code geschrieben wird (BL-231 Decoupling)
# und NICHT ob Infra hochfaehrt (INV-INFRA-MODUS-FREI, BL-329):
#   tdd=true  (M3) → Steps 9-18 (voller TDD-Strom: _TDD_red/_execute/_green/refactorCode/.../_check)
#   tdd=false (M2) → ENTKOPPELTER Code-Emit (NICHT mehr "nur Blueprint+Closure"!):
#                    _TDD_init (Infra-Detektion needInfra, modus-frei, BL-329)
#                    + [_TDD_setup IF needInfra — INFRA-PHASE Step 9b, MODUS-UNABHAENGIG]
#                    + _TDD_green (Code aus Blueprint/Slice, bestehende Tests = GREEN-Referenz, KEINE neuen Tests, kein red-first)
#                    + _TDD_execute (Verify)
#                    + [_TDD_teardown IF needInfra — INFRA-PHASE Step 18b, finally/auch-bei-ABORT] — DANN Closure (19-20).
#   (BL-231: emit_code ist von test_first entkoppelt — M2 schreibt Code via _TDD_green ohne Test-First-Ceremony.
#    BL-329 INV-INFRA-MODUS-FREI: M2 faehrt den IDENTISCHEN bedingten Infra-Rahmen wie M3 — Setup/Teardown haengen
#    am Infra-Bedarf der Stage, NICHT am Modus. Spiegelt dispatch_implement.js runImplementStage non-scenario-else-Zweig
#    [detectInfraNeed -> runInfraSetup -> M2-Emit/M3-TDD -> finally runInfraTeardown]. Vorher: M2 schrieb strukturell
#    0 Code → ABORT [BL-231]; und M2 hatte KEINEN Infra-Maschinen-Step, nur einen Prompt-Satz → 1944-Stage-6-Schmerz [BL-329].)
#
# stage (BL-168) steuert welche Test-Schicht in Step 10 (_TDD_red) generiert wird:
#   stage=1 → Unit-Tests (xUnit + Moq)
#   stage=3 → Integration-Tests (Docker-basiert)
#   stage=6 → Controller/E2E-Tests (PowerShell gegen API)
#   Stage-Auswahl pro Sub-Batch durch IDF Phase 7 batch_stages-Map.
```

---

## Wellen-Statusanzeige RF-9 (Blueprint-Wellen pro Stufe)

Team Lead gibt nach JEDER Wellen-Transition innerhalb einer Blueprint-Phase folgende Tabelle aus:

```
┌───────┬──────────────────────────────────────────┬────────┬─────────┐
│ Welle │ Worker                                   │ Modell │ Status  │
├───────┼──────────────────────────────────────────┼────────┼─────────┤
│ W1    │ {N} Explorer (E01-E{NN})                 │ {floor}│ {status}│
│ W2    │ {M} Drafter (D01-D{MM})                  │ {mid}  │ {status}│
│ W3    │ 1 Synthese (cleanCodeArchitect / Slice)  │ {ceil} │ {status}│
└───────┴──────────────────────────────────────────┴────────┴─────────┘
Command: /_I_cleanCodeArchitect --stufe {N} | Stufe: {N}/5
```

**Status-Werte:** DONE, RUNNING, PENDING
**Wann:** Nach Abschluss jeder Welle innerhalb von _I_cleanCodeArchitect oder _I_cleanCodeSlice
  (einzige Wellen-Commands in I-Pipeline; _I_testSearch, _I_goldDefine, _I_patternLibrary,
  _I_blueprintQG laufen single-agent -- RF-9 SKIP fuer diese)
**Bei easy:** Nur 1 Zeile (1 Synthese solo)

---

## Prozess-Statusanzeige RF-10 (Stufen-Loop)

Team Lead gibt nach JEDEM Stufen- oder Phasenwechsel folgende Tabelle aus.
**Ziel: Alles auf 1 Blick** -- Stufe, Phase, Agenten, Modell, Status, Inhalt.

```
┌───┬───────┬─────────────────────────┬──────────────────────┬────────┬──────────┬──────────────────────────────────┐
│ # │ Stufe │ Phase                   │ Agenten              │ Modell │ Status   │ Inhalt (Mini-Assay, NUR bei DONE)│
├───┼───────┼─────────────────────────┼──────────────────────┼────────┼──────────┼──────────────────────────────────┤
│ 0 │ --    │ Setup / Guards          │ Team Lead direkt     │ opus   │ + DONE   │ Handoff konsumiert, GAP=12%      │
│ 1 │ S1    │ Blueprint (Steps 1-8)   │ Wellen (arch+slice)  │ varies │ + DONE   │ 3 Slices definiert, S1-blueprint │
│ 2 │ S1    │ TDD-Merge (Steps 9-18)  │ _TDD_red/_execute/...│ varies │ + DONE   │ 24/24 Tests GREEN, gold=true     │
│ 3 │ S1    │ Closure (Steps 19-20)   │ _I_verify, _I_fanIn  │ varies │ + DONE   │ Slice-Consolidation OK            │
│ 4 │ S2    │ Blueprint (Steps 1-8)   │ Wellen (arch+slice)  │ varies │ > ACTIVE │                                  │
│ 5 │ S2    │ TDD-Merge (Steps 9-18)  │ _TDD_*               │ varies │ . PENDING│                                  │
│ 6 │ S2    │ Closure (Steps 19-20)   │ _I_verify, _I_fanIn  │ varies │ . PENDING│                                  │
│ 7 │ S3-S5 │ Blueprint+TDD+Closure   │ (wiederholt)         │ varies │ . PENDING│                                  │
│ 8 │ --    │ Nachphase (Steps 21-23) │ verify/Scope/Rollover│ varies │ . PENDING│                                  │
└───┴───────┴─────────────────────────┴──────────────────────┴────────┴──────────┴──────────────────────────────────┘
Stufe {N}/5 | GAP: {gap_score}% | Scope: {scope_mode}
```

**Inhalt-Spalte:** 1-2 Saetze INHALTLICH (was gefunden/produziert), NUR bei DONE.
**Status-Symbole:** + DONE, > ACTIVE, . PENDING, - SKIP, x FAIL
**Modell-Regel:** Explorer={floor}, Drafter={middle}, Synthese={ceiling}
**Fusszeile:** Aktuelle Stufe, GAP-Score aus Manifest, Scope-Mode (core/full).
**Wann:** Nach Abschluss jeder Stufen-Phase (Blueprint DONE, TDD DONE) und vor Start der naechsten.
**Bei easy:** Kompakt-Format (eine Zeile pro abgeschlossener Einheit statt volle Tabelle).

---

## PHASE 0: RESUME-GUARD (Playbook-Rueckkehr)

```
# ═══ INV-PROCESS-STRICT-GUARD (NEU 2026-05-10 BL-174) ═══
#
# _I_orchestrate wird in ALLEN Bau-Modi geladen: M1 via --scope=skeleton (condensed
# 4-Step-Subset, worker-mode), M2/M3 als volle Pipeline. KEIN Modus ist Lead-inline
# — INV-PM-1 ABSOLUT, alle Steps via GESPAWNTE Worker. M2/M3 MUESSEN strikt sein
# (volle Step-Kette, KEIN Lead-Shortcut); M1 ist das condensed Subset, ABER ebenfalls
# Worker-gespawnt. KORRIGIERT 2026-06-18 (BL-174-Doc-Drift: alte Annahme "M1 =
# Lead-inline, nicht geladen" SUPERSEDED durch INV-PM-1 + BL-212 --scope=skeleton).
#
# Wenn der Lead in Phase 0 erkennt, dass er gerade einen Shortcut-Versuch
# faehrt (Pragmatik-Drift), MUSS er ABORT mit klarer Fehlermeldung loesen.
#
# DETECT (Lead-Self-Check):
#   1. Habe ich vor Phase 1 Setup einen Mega-Agent-Spawn geplant?
#      (z.B. Agent(general-*, prompt="implementiere X komplett"))
#   2. Habe ich Plan-Statements wie "Pragmatisch ... statt 10 Skill-Steps spawne ich"?
#   3. Plane ich Steps 1-20 zu skippen weil "trivial"?
#   4. Plane ich Code-Edit direkt im Lead-Frame ohne Step-Skill-Load?
#
# Falls JA bei irgend einem Punkt:
#   ABORT mit Logge: "[I-PIPELINE] INV-PROCESS-STRICT verletzt — Skill-Handoff-Chain PFLICHT.
#                     M2/M3 = strikte Pruef-Stelle, kein Lead-Shortcut. Falls Trivialfall
#                     gemeint war, gehoert er per BL-174 zu M1 — ein CONDENSED 4-Step-Subset
#                     via Skill(_I_orchestrate --worker-mode --scope=skeleton) in einem
#                     GESPAWNTEN Worker (NICHT Lead-inline). Re-Iteration durch SDF Phase 1.1
#                     mit korrekter Modus-Entscheidung (INV-MODUS-1) erforderlich."
#   Set I_PIPELINE_STATE.phase = "ABORTED_PROCESS_VIOLATION"
#   RETURN exit_code=99
#
# Falls NEIN: weiter mit Standard-Resume-Guard.

# ═══ RESUME-GUARD (CaseStudy DCSRE-98 Bug-Fix + Hub-Invariante #8) ═══
#
# Wenn _I_orchestrate via SDF zurueckgeladen wird (nach TDD), steht phase=POST_TDD im Manifest.
# Hub-Invariante: TDD→SDF→I (nicht TDD→I direkt). SDF ruft I nach TDD-Completion.
# In dem Fall: SKIP Phase 1 (Team Setup) und spring direkt zu RUECKKEHR AUS TDD-PHASE.

manifest_global = lies("{VAULT}/_manifest.md")          # global: NAME, BDF_PIPELINE_STATE
manifest_local  = lies("{WORKING_DIR}/_manifest.md")    # per-Story: I_PIPELINE_STATE (BL-155 AK-1)
NAME = manifest_global.NAME  # oder aus Aufruf-Argumenten

# ═══ INV-STAGE-STATE-1 (Stage-State Single-Writer, BL-414) ═══
# DF_BATCH_STATE.current_stage ist die KANONISCHE observable Stage-State.
# Ein Writer (stageElevation/increment = Planner schreibt), alle anderen lesen nur —
# Spiegel INV-MODUS-1 (ein Writer, alle lesen).
# Hardwired Default: Stage 1 (KEINE dynamische Inferenz aus Kontext, kein Raten —
# das ist die Fehlerklasse fiktiver stage_3.md-Pfade).
# Resolution: current_stage -> {vault}/Stage/stage_N_*/ via resolve_vault_stage (BL-392).
# I_orchestrate und SDF lesen current_stage — sie schreiben es NICHT ausserhalb dieses Blocks.

# ═══ STAGE-ARG-SYNC (NEU 2026-05-10 BL-171) ═══
# --stage=N CLI-Arg ist autoritativ: SDF Outer-Loop steuert Stage-Progression
# via --stage Param. Falls Arg gesetzt: I_PIPELINE_STATE.current_stage = arg.
# Sonst: Default 1 oder bestehender Wert aus Resume-State.
stage_arg = parse_arg("--stage")     # int oder null
IF stage_arg != null:
  manifest_local.I_PIPELINE_STATE.current_stage = stage_arg
  Logge: "[STAGE-ARG-SYNC] current_stage = {stage_arg} (aus --stage Arg, BL-171)"
ELSE IF manifest_local.I_PIPELINE_STATE.current_stage == null:
  manifest_local.I_PIPELINE_STATE.current_stage = 1
  Logge: "[STAGE-ARG-SYNC] current_stage = 1 (Default, kein --stage Arg)"
# Sonst: bestehender Wert bleibt (Resume-Pfad)

# --tdd=true|false CLI-Arg ebenfalls autoritativ (BL-169)
tdd_arg = parse_arg("--tdd")
IF tdd_arg != null:
  manifest_local.I_PIPELINE_STATE.tdd_enabled = tdd_arg
  # Wirkt sich auf Step 9-18 (TDD-Phase) aus

manifest_local.update()

IF manifest_local.I_PIPELINE_STATE.phase IN ["POST_TDD", "NEEDS_TDD"]:
  Logge: "[RESUME-GUARD] phase={manifest_local.I_PIPELINE_STATE.phase} → Rueckkehr aus TDD (via SDF)."
  Logge: "[RESUME-GUARD] SKIP Phase 1 (Team Setup). Direkt zu RUECKKEHR AUS TDD-PHASE."
  N = manifest_local.I_PIPELINE_STATE.current_stage
  # Lade Session-Parameter
  params = lies("{VAULT}/_session_params.md")
  slicing = params.slicing
  tdd = params.tdd
  tdd_stages = params.tdd_stages
  worktree_parallel = (slicing == true)
  → SPRING ZU: "RUECKKEHR AUS TDD-PHASE (Phase 3: R1-R4)" (Zeile mit "Schritt R1")

IF manifest.I_PIPELINE_STATE.phase == "POST_TDD_CONSUMED":
  Logge: "[RESUME-GUARD] phase=POST_TDD_CONSUMED → Stage-Transition bereits konsumiert."
  Logge: "[RESUME-GUARD] Weiter mit naechster Stufe im Stufen-Loop."
  N = manifest.I_PIPELINE_STATE.last_stage_completed + 1
  IF N > 5 OR N NOT IN tdd_stages:
    Logge: "[RESUME-GUARD] Alle Stufen abgeschlossen → POST_PIPELINE."
    → SPRING ZU: "NACHPHASE (Post-Pipeline)"
  ELSE:
    → SPRING ZU: "STUFEN-LOOP: BLUEPRINT-PHASE (pro Stufe N)" mit N = naechste Stufe

IF manifest.I_PIPELINE_STATE.phase == "STAGE_COMMIT":
  Logge: "[RESUME-GUARD] phase=STAGE_COMMIT → /_stage_orchestrate laeuft/war aktiv."
  → SPRING ZU: "STAGE-TRANSITION" (nach POST_TDD_CONSUMED)

IF manifest.I_PIPELINE_STATE.handschuh_wechsel_pending == true:
  Logge: "[RESUME-GUARD] handschuh_wechsel_pending=true → Stage-Progression via SDF abgeschlossen."
  Logge: "[RESUME-GUARD] I_orchestrate wird von SDF fuer Stufe {current_stage} neu gestartet."
  # SDF hat current_stage bereits auf N+1 gesetzt — direkt zum Stufen-Loop
  N = manifest.I_PIPELINE_STATE.current_stage
  manifest.I_PIPELINE_STATE.handschuh_wechsel_pending = false
  manifest.update()
  → SPRING ZU: "STUFEN-LOOP: BLUEPRINT-PHASE (pro Stufe N)" mit N = current_stage

# Kein Resume noetig → normaler Start (Phase 1)
```

---

## PHASE 1: TEAM SETUP

# [INV-SPAWN] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline:
Skill(skill="_I_berater_teamSetup", args="{NAME} {worker_mode_flag}")
# Output: BERATER_OUTPUTS.teamSetup.{worker_mode, team_name, puppet_master_active,
#         scope_mode, rag_collection, handoff_consumed, model_read_verified, i_dry_run_done}
# [GATE P1] State-Read NACH Worker (exit_code-Check vor Phase 2):
IF BERATER_OUTPUTS.teamSetup.exit_code == 99: ABORT "[INV-SPAWN] Phase-1 ABORTED_PROCESS_VIOLATION"
IF BERATER_OUTPUTS.teamSetup.i_dry_run_done == true: RETURN
# exit_code == 0 -> proceed zu Phase 2.

---
## PHASE 2: KURZLEBIG_PROMPT (Single-Command-Agent)

# [GATE P2] exit_code-Check Phase-1-Slot VOR Phase-2-Spawn:
IF BERATER_OUTPUTS.teamSetup.exit_code != 0: ABORT "[INV-SPAWN] Phase-2 ohne Phase-1 DONE"
# [INV-SPAWN] Worker-Spawn (KURZSCHRIFT) — NICHT Lead-Inline:
Skill(skill="_I_berater_kurzlebigPrompt", args="...")
# Berater erzeugt Prompt-String aus Phase-1 Output (WORKTREE_PATH, FEATURE_ID)
# + Phase-3 Variablen (COMMAND, SLICE, BATCH_NUM, TASK_ID).
# Regel: KEIN Custom-Prompt, nur Template-Variablen befuellen.

---
## PHASE 3: TEAM LEAD STEUERUNG

# [GATE P3] exit_code-Check Phase-2-Slot VOR Phase-3-Spawn:
IF BERATER_OUTPUTS.kurzlebigPrompt.exit_code != 0: ABORT "[INV-SPAWN] Phase-3 ohne Phase-2 DONE"
# [INV-SPAWN] Worker-Spawn (KURZSCHRIFT) — NICHT Lead-Inline:
Skill(skill="_I_berater_teamLeadSteuerung", args="...")
# Liest BERATER_OUTPUTS.teamSetup (Phase 1) + nutzt _I_berater_kurzlebigPrompt (Phase 2).
# Schreibt: BERATER_OUTPUTS.teamLeadSteuerung.{synthese, manifest_state, stufe_final}
# Steuert die Wellen, spawnt kurzlebige Workers via spawne_wellen().

---
## STUFEN-LOOP: BLUEPRINT-PHASE (pro Stufe N)

# [GATE P4] exit_code-Check Phase-3-Slot VOR LOOP-Spawn:
IF BERATER_OUTPUTS.teamLeadSteuerung.exit_code != 0: ABORT "[INV-SPAWN] LOOP ohne Phase-3 DONE"
# [INV-SPAWN] Worker-Spawn (KURZSCHRIFT) — NICHT Lead-Inline:
Skill(skill="_I_berater_blueprintLoop", args="--stufe {N}")
# Berater deckt Sub-Phasen A-G:
#   A: Stage-Entry + Metadaten
#   B: testRun-GUARD
#   C: Blueprint (arch / requirementCheck / patternLibrary / testSearch /
#                 goldDefine / blueprintQG / slice / fanOut)
#   D: Puppet-Master-Block
#   E: TDD-Uebergabe P1.0-P1.5
#   F: POST_TDD Resume R1-R4
#   G: QP-Block + Stage-Transition + Handschuh-Wechsel an SDF
# Cross-Reference: Phase 3 teamLeadSteuerung Output

---
## NACHPHASE (Post-Pipeline)

# [GATE P5] exit_code-Check blueprintLoop-Slot VOR Nachphase-Spawn:
IF BERATER_OUTPUTS.blueprintLoop.exit_code != 0: ABORT "[INV-SPAWN] Nachphase ohne LOOP DONE"
# [INV-SPAWN] Worker-Spawn (KURZSCHRIFT) — NICHT Lead-Inline:
Skill(skill="_I_berater_nachphase")
# verify global, Scope-Gate (i_core_result), pipeline_mode Routing,
# I_PIPELINE_STATE Rollover (Pattern B), Final Summary.
# Output: BERATER_OUTPUTS.nachphase.{verify_status, scope_gate_log, rollover_done, final_summary}

---
## POST_HANDOVER (BL-NEW-12, PFLICHT 2026-05-11) — Handschuh-Wechsel zu Post-SDF

> **BL-NEW-44 ABSOLUT VERBOTEN (Case-Anchor `.claude/_parking-lot.md`):**
> Lead darf NACH Sub-Phase G (Stage-Commit) NUR EINEN Schritt machen:
> `Skill(_SDF_orchestrate_post, args="{NAME} --vault={VAULT}")`. Verboten sind:
>
>   ❌ Inline `manifest.current_stage = N+1` (siehe _SDF_orchestrate.md Z589 — das Code-Snippet ist NUR fuer Pre-SDF Outer-Loop, NICHT fuer Lead-Eigeninterpretation)
>   ❌ Inline `completed_stages_per_batch[batch_key].append(...)` (siehe oben)
>   ❌ Inline `Skill(_I_orchestrate, --stage=N+1)` (Selbst-Rekursion ohne Berater-Decision)
>   ❌ Inline `impl_test_stages[N].status = "done"` (Phase 3.6 Berater macht das)
>   ❌ Narrative-Phrasen wie "Outer-Loop: ..." oder "Stage X startet jetzt" ohne Skill-Wechsel
>
> Stage-Progression ist EXKLUSIV in Phase 3.6 stageElevation (Post-SDF) oder
> Phase 2.2 stageElevation (Pre-SDF Outer-Loop). Beide spawnen `_SDF_berater_stageElevation`.
> Lead's "ich weiss was kommt → inline" ist genau die BL-NEW-12/41/44 Bypass-Pathologie.
>
> **Erkennungsmuster (User soll bei Sichtung sofort STOP rufen):**
> "Outer-Loop: completed_stages_per_batch.X.append(N)" — kommt nur aus Skill-Pseudo-Code, NICHT aus laufendem Lead.



> **INV-HANDOVER-1:** I_orchestrate darf NICHT mit done-Status enden ohne explizit
> `Skill(_SDF_orchestrate_post, ...)` aufgerufen zu haben (es sei denn `--standalone` Flag).
>
> **Grund:** Skill-Context-Override-Problem — wenn I_orchestrate ohne expliziten
> Handover zurueckkehrt, "vergisst" der Lead die SDF Phase 3 (BUILD-Sanity, Wave 1/2,
> batchEnde, loopDecision). Pattern: Lead skipt alle Phase-3-Schritte und springt
> direkt zu Phase 1.1 naechste Round. Konkrete Live-Faelle in `.claude/_parking-lot.md`.
>
> Mit explizitem Handover wird Phase 3 strukturell erzwungen: Skill-Load von
> `_SDF_orchestrate_post` ist nicht vermeidbar — Skill-Context-Refresh + Phase-3-Pflicht-Code.
>
> **ENFORCEMENT (BL-427):** `guard_sdf_post_handoff.py` ist als PreToolUse-Hook registriert
> (enforce-AFTER-write-Pattern, analog `guard_a_idf_handoff.py` BL-350). Bei Skill-Load von
> `_SDF_orchestrate` (Resume) OHNE vorausgehendes `_SDF_orchestrate_post` SKILL_LOAD seit
> letztem `_I_orchestrate`/`_SC_orchestrate`-Skill-Load → BLOCK (enforceProcess=true) bzw.
> WARN (false). Recovery-Hint: `Skill(_SDF_orchestrate_post, args="{BL_ID} --vault={VAULT}")`.

```
# Allerletzter Schritt VOR NOTIFY — egal welcher scope (skeleton/full),
# egal welcher modus (M1/M2/M3...), egal worker-mode oder nicht.
#
# BL-NEW-12 Fix B2 (2026-05-11): Vereinfacht — kein PIPELINE_CALL_STACK-Check
# (Feld nicht maintained). Default: handover. Bypass nur via --standalone Flag.

standalone_flag = args.standalone ?? false

IF standalone_flag == true:
  # Standalone-Aufruf (Test/Debug ohne SDF-Parent) → SKIP Handover
  Logge: "[POST-HANDOVER] standalone-Modus — SKIP SDF-Post-Handover"
  audit_jsonl_append({type: "POST_HANDOVER_SKIP", reason: "standalone_flag"})

ELSE:
  # Normalfall: I_orchestrate wurde von Pre-SDF Phase 2 dispatched
  Logge: "[POST-HANDOVER] Skill-Wechsel zu Post-SDF (BL-NEW-12)"
  audit_jsonl_append({
    type: "POST_HANDOVER",
    from: "_I_orchestrate",
    to: "_SDF_orchestrate_post",
    name: NAME,
    timestamp: ISO
  })
  Skill(_SDF_orchestrate_post, args="{NAME} --vault={VAULT}")
  # Post-SDF endet mit RETURN (RE-BATCH) oder Skill-Call (ROLLBACK/SOFT-REPRIO).
  # Bei RETURN: Control geht zurueck zu Pre-SDF outer-loop, der die naechste
  # Iteration startet (Pre-SDF Z528-543 OUTER-LOOP-WRAPPER).
```

**INV-HANDOVER-1 Verstoss-Erkennung:**
- audit.jsonl pro Round MUSS einen `{type: "POST_HANDOVER"}`-Eintrag haben
- Fehlt der Eintrag UND `--standalone` war nicht gesetzt → Process-Bug detected
- Sichtbar via `/_sanity_check_dynamic` Audit-Scan

---
## Fehlerbehandlung

| Fehler | Loesung |
|--------|---------|
| Command FAIL | STOPP + Synthese-Datei pruefen |
| Agent-Timeout (>20 Min) | SendMessage Status-Query → 5 Min → STOPP |
| Stagnation (5× partial) | Parking-Lot + HiL (Scope/Fix/ABORT) |
| Test-Suite FAIL (HiL) | STOPP → User fixt → Neustart |
| Pre_PR FAIL | User fixt → Re-Run (nur FAIL-Gates) |

---

## Qualitaetskriterien

- Stufen-Modell (W7-compliant), kurzlebige Agents
- Manifest-Update nach JEDER Stufe + Batch-Zyklus
- HiL an 2 Stellen (Test-Suite, Commits)
- VERTRAG-Block, Error-Handling, Final Summary

---

## NOTIFY (Allerletzter Schritt)

```bash
powershell -Command "notify '{FEATURE} /_I_orchestrate abgeschlossen'"
```
