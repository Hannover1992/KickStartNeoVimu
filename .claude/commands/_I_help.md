---
type: satellite
updated: 2026-05-11
revision: BL-NEW-29 Batch-as-Slice (Minimal-Surgical)
---

# Implementierungs-Pipeline - Hilfe & Uebersicht (v6.2 — Batch-as-Slice)

Zeige die Uebersicht der Implementation Pipeline (/_I_* + /_TDD_*) Commands.

## Aufruf

```
/_I_help
```

---

## Updates 2026-05-19 (BL-173/174/175 Cross-Cutting)

**Manifest-Routing (BL-173):**
- I-Pipeline schreibt `I_PIPELINE_STATE` in `{bl_folder}/_manifest.md` (pipeline-spezifisch)
- `{vault}/_factory_manifest.md` behaelt ausschliesslich BDF+GLOBAL_*-Bloecke
- Helper: `manifest_reader.read_factory_block(...)`, `manifest_reader.read_bl_block(bl_id, ...)`
- Migration: `migrate_manifest_split.py migrate --vault-root=... --rollback-tag=YYYY-MM-DD`

**Session-Params Per-BL (BL-174):**
- 3-Stufen-Inheritance: BL-Override → Vault-Default → Framework-Default
- Resolver: `session_params_resolver.resolve_param(name, bl_id=None)`
- `/_param` mit `--bl-id=BL-XXX` schreibt BL-spezifisch (I-Params pro BL isoliert, z.B. tdd, slicing)

**BDF Factory-Lock (BL-175):**
- `acquire/release/heartbeat` via `factory_lock.py`
- TTL+Heartbeat, kein fcntl, eigenes `_factory_lock.md`
- Race-Condition-safe fuer 5-10 parallele BDFs

(siehe `/_help` TEIL 8c, BL-173/174/175 Spec-Dateien)

---

## POSITION IN DER PIPELINE-REISE (3er-Doppel-Sicht, NEU 2026-05-24)

> **Cross-Reference:** Vollstaendige Reise + Geister-Tabelle: `/_help` TEIL 10
> Methodik: `.claude/INSTRUCTION_full_scan_2026-05-24.md`

**Wo sitzt /_I_orchestrate in der Gesamt-Reise?**

```
/_SDF_orchestrate Phase 2.1 dispatch (modus IN [M1, M2, M3])
                                  │
                                  ▼
                              ★G#6 → /_I_orchestrate
                                          │
                                          │ ~20 Steps pro Stage:
                                          │   Blueprint (1-8) → TDD (9-18) → Closure (19-20)
                                          │
                                          │ Nach allen Stages: NACHPHASE + POST_HANDOVER
                                          ▼
                              ★G#7 → /_SDF_orchestrate_post
```

**3er-Doppel-Fenster:**

| Position | Vertrag                          | Lese-Fokus                          |
|----------|----------------------------------|-------------------------------------|
| [N-1]    | `/_SDF_orchestrate` Phase 2.1    | DF_BATCH_STATE.modus + current_sub_batch_items + batch_stages |
| [N  ]    | `/_I_orchestrate`                | LIEST + SCHREIBT (Code + Tests + BERATER_OUTPUTS) |
| [N+1]    | `/_SDF_orchestrate_post`         | BERATER_OUTPUTS + Stage-Output + audit.jsonl POST_HANDOVER-Event |

**Geister-Beteiligung:**

- **Input-Geist G#6:** `/_SDF Phase 2.1 → /_I_orchestrate` (modus M1/M2/M3 — siehe SDF-Help)
- **Intra-Geister (pro Stage):**
  - Blueprint-Phase (Steps 1-8): `_I_cleanCodeArchitect → _I_requirementCheck → _I_patternLibrary → _I_testSearch → _I_goldDefine → _I_blueprintQG → _I_cleanCodeSlice → _I_mitose+_I_fanOut`
  - TDD-Phase (Steps 9-18, --tdd=true): `_TDD_init → _TDD_red → _TDD_setup → _TDD_execute → _TDD_green → _TDD_execute → _TDD_refactorCode → _TDD_execute → _TDD_refactorTests → _TDD_execute → _TDD_teardown → _TDD_check`
  - Closure (Steps 19-20): `_I_verify → _I_fanIn` (FanOut/FanIn auto-skipped bei slicing=false BL-NEW-29)
- **Output-Geist G#7:** `/_I_orchestrate → /_SDF_orchestrate_post` (POST_HANDOVER, INV-HANDOVER-1)

**Modus-Variation:**

| Modus | --scope     | --tdd    | Steps                  |
|-------|-------------|----------|------------------------|
| M1    | skeleton    | false    | 4 (architecturalLib + patternLib + semanticLib + codeAtomic) |
| M2    | full        | false    | 10 (Steps 1-8 + 19-20) |
| M3    | full        | true     | 20 (Steps 1-8 + 9-18 + 19-20) |

**Step-Anzahl im 1-Pipeline-Durchlauf:**

- Pro Stage: 4-20 Steps (scope/tdd-abhaengig)
- Stages pro Sub-Batch: 1-3 (laut DF_BATCH_STATE.batch_stages-Map)
- 6 I-Berater (teamSetup, kurzlebigPrompt, teamLeadSteuerung, blueprintLoop, nachphase, sliceBrief)
- 10 TDD-Sub-Skills (init, red, setup, execute, green, refactorCode, refactorTests, teardown, check, monitor)
- INV-PROCESS-STRICT (BL-174) + INV-WORKER-SKILL-LOAD (BL-NEW-45) + INV-NO-HAIKU-IN-TDD (BL-NEW-51) ABSOLUT bei M2/M3

---

## SYSTEM-UEBERSICHT (v6.2 — Batch-as-Slice, BL-NEW-29 2026-05-11)

Gib dem User folgende Uebersicht aus:

```
╔════════════════════════════════════════════════════════════════════════════╗
║  IMPLEMENTIERUNGS-PIPELINE v6.2 — BATCH-AS-SLICE (Minimal-Surgical)        ║
║                                                                            ║
║  KERN-PRINZIP (BL-NEW-29 2026-05-11):                                      ║
║    Slice-Count = 1 (Batch IST der Slice). Infrastruktur (cleanCodeSlice,   ║
║    mitose, fanOut, fanIn) bleibt — auto-skipt via Single-Slice-Logik.      ║
║    Forward-Compat: slicing=true + fanout>1 reaktiviert parallel-Modus.    ║
║                                                                            ║
║    BEGRUENDUNG: Mit BL-168 (batch_stages) + BL-NEW-12 (Pre/Post-SDF Split) ║
║    ist BATCH bereits der kleinste sinnvolle Scope. IDF Phase 7 hat schon   ║
║    pro PL-Item gesliced. Sub-Slicing innerhalb Batch erzeugte nur Race-    ║
║    Bedingungen + Token-Waste (Beweis: DCSRE-486 2026-05-11 — 10 parallel  ║
║    cleanCodeSlice → ~800k Tokens + premature -impl-b1 Workers).            ║
║                                                                            ║
║  ═══ SESSION-PARAMETER (/_param) ═══                                       ║
║                                                                            ║
║  tdd=true|false       TDD-Zyklus an/aus pro Stage                          ║
║    true:  Steps 9-18 inline auf BATCH-Slice (1 RED→GREEN→Refactor)         ║
║    false: Direkt-Impl ohne Test-First                                      ║
║                                                                            ║
║  slicing=true|false   Sub-Slicing innerhalb Batch (Default: false, NEU)    ║
║    false: 1 Batch = 1 Slice, mitose/fanOut/fanIn AUTO-SKIP                ║
║    true:  Legacy Multi-Slice-Modus (parallel Worktrees) — Forward-Compat   ║
║                                                                            ║
║  ═══ PIPELINE-KETTE (1 Batch = 1 Item = 1 Slice) ═══                       ║
║                                                                            ║
║  ┌─────────────────────────────────────────────────────────────────┐       ║
║  │  STUFEN-LOOP pro Stage N aus batch_stages [1,3,6]               │       ║
║  │                                                                 │       ║
║  │  Wenn batch_stages = [1,3,6]: I-Orchestrate laeuft 3×          │       ║
║  │  Wenn batch_stages = [1]    : I-Orchestrate laeuft 1×           │       ║
║  │                                                                 │       ║
║  │  STG-A  Stage-Entry + Metadaten                                 │       ║
║  │         (lade stage_{N}.md → testbefehl, fokus, fanout)         │       ║
║  │  STG-B  testRun-GUARD                                           │       ║
║  │                                                                 │       ║
║  │  STG-C  Blueprint-Phase (Steps 1-4)                             │       ║
║  │    Step 1   /_I_cleanCodeArchitect --stufe N                   │       ║
║  │             (parallel mit 1a/1b/1c)                              │       ║
║  │             ├─ 1a /_I_requirementCheck (Spec-Coverage)           │       ║
║  │             ├─ 1b /_I_patternLibrary (Patterns pro Stage)        │       ║
║  │             └─ 1c /_I_architecturalLibrary (Layer-Conformance)   │       ║
║  │    Step 2   /_I_testSearch                                       │       ║
║  │    Step 3   /_I_goldDefine                                       │       ║
║  │    Step 4   /_I_blueprintQG (max 2 Retries → HiL)                │       ║
║  │                                                                 │       ║
║  │  STG-C2 Slicing-Phase (Slice-Count = 1 bei slicing=false)        │       ║
║  │    Step 5   /_I_cleanCodeSlice --stufe N (1× aufgerufen)         │       ║
║  │             → Code-Planung + Pattern-Reuse fuer BATCH-Slice      │       ║
║  │             → Liest: PatternLibrary (horizontale Suche)          │       ║
║  │             → Liest: Codebase (Reuse-Scoring)                    │       ║
║  │             → SCHREIBT: sub-1.md (1 Sub-Blueprint)               │       ║
║  │             → BATCH wird als EIN Slice behandelt                │       ║
║  │                                                                 │       ║
║  │    Step 6   mitose + fanOut  ──→  AUTO-SKIP (Single-Slice)       │       ║
║  │             Logge: "Single-Slice: SKIP mitose/fanOut"            │       ║
║  │             (Skill-Files bleiben fuer Forward-Compat)            │       ║
║  │                                                                 │       ║
║  │  STG-D  Puppet-Master-Block (TDD-Vorbereitung)                   │       ║
║  │                                                                 │       ║
║  │  STG-E  TDD-Phase (Steps 9-18, 1 Iteration auf BATCH-Slice)      │       ║
║  │    Step 9_init     (HiL Wizard, 1x pro Stage)                    │       ║
║  │    Step 10_red     (1 Worker: ALLE Failing Tests fuer Stage)     │       ║
║  │    Step 11_exec    (Assert ALL RED)                              │       ║
║  │    Step 12_green   (1 Worker: ALLES Minimal-Code)                │       ║
║  │    Step 13_exec    (Assert ALL GREEN)                            │       ║
║  │    Step 14_refactorCode  (Opus, ueber den Batch-Slice)           │       ║
║  │    Step 15_exec                                                  │       ║
║  │    Step 16_refactorTests                                         │       ║
║  │    Step 17_exec                                                  │       ║
║  │    Step 18_check   (Gold-Content-Assertions aus GOLD-S{N}.md)    │       ║
║  │                                                                 │       ║
║  │  STG-F  POST_TDD                                                 │       ║
║  │                                                                 │       ║
║  │  STG-G  Stage-Closure                                            │       ║
║  │    Step 19  /_I_verify --slice 1 (= ganzer Batch)                │       ║
║  │    Step 20  fanIn  ──→  AUTO-SKIP (Single-Slice-Condition)       │       ║
║  │             Logge: "Single-Slice: SKIP fanIn"                    │       ║
║  │    Stage-QG (Kanarienvogel grün?)                                │       ║
║  │    → wenn weitere Stages in batch_stages: neuer I-Aufruf         │       ║
║  │    → wenn letzte Stage: weiter zu Nachphase                     │       ║
║  └─────────────────────────────────────────────────────────────────┘       ║
║                                                                            ║
║  ═══ NACHPHASE + POST_HANDOVER (BL-NEW-12) ═══                             ║
║                                                                            ║
║  Step 21  /_I_verify --global                                              ║
║   │       Cross-Stage-Verify (alle Stages dieses Batches grün)             ║
║   ▼                                                                        ║
║  Step 22  POST_HANDOVER                                                    ║
║   │       Skill(_SDF_orchestrate_post, args="{NAME} --vault={VAULT}")     ║
║   │       Bypass nur mit --standalone Flag (Test/Debug)                    ║
║   │       INV-HANDOVER-1: ohne diesen Step Phase 3 ungelaufen!             ║
║   ▼                                                                        ║
║   [Pre-SDF Outer-Loop continues with naechstem Batch]                      ║
║                                                                            ║
║  ═══ DATA-FLOW ═══                                                         ║
║                                                                            ║
║  INPUTS (read):                                                            ║
║    Manifest: DF_BATCH_STATE, batch_items_per_batch, batch_stages,          ║
║              batch_modes, BERATER_OUTPUTS.architecturalBrief +             ║
║              patternBrief + modusEntscheidung                              ║
║    Vault:    Spec, Model, GAP, K-Score                                     ║
║    Repo:     .claude/meta/implementation/stage_{N}.md                      ║
║                                                                            ║
║  OUTPUTS (write):                                                          ║
║    Vault 4_Blueprint/:                                                     ║
║      S{N}-cleanCodeArchitect.md     (Blueprint-Hauptdatei)                 ║
║      PATTERN-S{N}.md                 (Pattern-Sidecar)                     ║
║      TESTSEARCH-S{N}.md              (Test-Inventar-Sidecar)               ║
║      GOLD-S{N}.md                    (Gold-Definition-Sidecar)             ║
║      ARCHCONFORMANCE-S{N}.md         (Arch-Conformance-Sidecar)            ║
║      REQCHECK-S{N}.md                (Requirement-Check-Sidecar)           ║
║      sub-1.md                        (1 Sub-Blueprint fuer Batch)         ║
║      VERIFY-S{N}.md                                                        ║
║    Code:                                                                   ║
║      Sources/Backend/.../{BatchEntity}.cs                                  ║
║      Tests/.../{BatchEntity}Tests.cs                                       ║
║    Manifest-Patches:                                                       ║
║      I_PIPELINE_STATE: phase, current_stage, last_stage_completed          ║
║      s{N}_blueprint_path + s{N}_blueprint_sidecars                         ║
║      s{N}_slice_count: 1 (NEU — explicit single-slice marker)              ║
║      qg_blueprint_{N}, stage_{N}_verify, stage_{N}_qg                      ║
║      BERATER_OUTPUTS.{step}.{status, exit_code, timestamp}                 ║
║                                                                            ║
║  ENTFAELLT in Single-Slice-Modus (auto-skipped, infrastruktur erhalten):   ║
║    s{N}_slice_plans: [N paths]   → REDUZIERT zu sub-1.md                  ║
║    s{N}_worktrees: [N paths]     → NICHT erstellt (mitose SKIP)            ║
║    fanIn-Merge-Conflict-Resolution → ENTFAELLT (fanIn SKIP)                ║
║                                                                            ║
║  ═══ MODI-MATRIX ═══                                                       ║
║                                                                            ║
║  ┌────────────┬───────────┬──────────────────────────────────────────┐     ║
║  │ slicing    │ tdd       │ Verhalten                                │     ║
║  ├────────────┼───────────┼──────────────────────────────────────────┤     ║
║  │ false (NEU)│ true      │ Voll-Pipeline 1-Slice + TDD (DEFAULT)    │     ║
║  │ false      │ false     │ Blueprint + Direct-Impl, 1-Slice         │     ║
║  │ true       │ true      │ Legacy Multi-Slice + TDD parallel        │     ║
║  │ true       │ false     │ Legacy Multi-Slice + Direct-Impl         │     ║
║  └────────────┴───────────┴──────────────────────────────────────────┘     ║
║                                                                            ║
║  Multi-Batch-Parallelism (Feature-Ebene) kommt ueber BL-NEW-14:            ║
║  BDF spawnt 2-3 SDF-Instanzen parallel auf verschiedenen Batches.          ║
║  Innerhalb eines Batches: sequentiell (Single-Slice).                      ║
║                                                                            ║
║  ═══ ORCHESTRATOR ═══                                                      ║
║                                                                            ║
║  /_I_orchestrate {NAME} --batch={ITEM} --stage={N} --tdd=true|false        ║
║   │  Steuert STUFEN-LOOP + Blueprint + TDD + POST_HANDOVER                 ║
║   │  Bei slicing=false (Default): 1 Slice = Batch, keine Worktrees         ║
║   │                                                                        ║
║  POST_HANDOVER PFLICHT (BL-NEW-12):                                        ║
║    Allerletzter Step ruft Skill(_SDF_orchestrate_post). Bypass nur mit     ║
║    --standalone Flag. INV-HANDOVER-1.                                      ║
║                                                                            ║
║  ═══ ARCHITEKTUR-INSIGHT (warum Refactor BL-NEW-29) ═══                    ║
║                                                                            ║
║    Pre-Batch-Welt (vor BL-168):                                            ║
║      User-Story → 1 monolith Run → 10 Slices parallel (Worktree-Race)     ║
║      Slicing = Worktree-Parallel-Mechanismus                              ║
║                                                                            ║
║    Post-Batch-Welt (heute, BL-168 + BL-NEW-12):                           ║
║      User-Story → IDF → N Batches (klein) → SDF pro Batch eigener Modus    ║
║      → I-Pipeline pro Batch → BATCH bereits klein genug                    ║
║      → Doppel-Slicing innerhalb Batch = Race + Token-Waste                ║
║                                                                            ║
║    Loesung BL-NEW-29 (Minimal-Surgical):                                   ║
║      - Slice-Count default = 1 (slicing=false als Default)                 ║
║      - cleanCodeSlice bleibt (sein Wert: Pattern-Reuse + Code-Planung)     ║
║      - mitose/fanOut/fanIn AUTO-SKIP via existierender Single-Slice-Logik  ║
║      - Forward-Compat: slicing=true reaktiviert parallel-Modus             ║
║      - 0 Files geloescht, 3 Config-Defaults geaendert                      ║
║                                                                            ║
║    Trade-Off akzeptiert:                                                   ║
║      Sequential Worker innerhalb Batch (1 Worker pro Step), Parallelism    ║
║      wandert auf BATCH-Ebene via BL-NEW-14 (BDF Multi-SDF).                ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
```

Dann lies `{VAULT}/_manifest.md` falls vorhanden und zeige den aktuellen Pipeline-Stand.

Zeige auch: `/_TDD_help` fuer TDD-spezifische Details.

ARGUMENTS: $ARGUMENTS
