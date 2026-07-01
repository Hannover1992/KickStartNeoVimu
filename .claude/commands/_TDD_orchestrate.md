# /_TDD_orchestrate — TDD Stufen-Schleife — **DEPRECATED 2026-05-09 (BL-169)**

> **🛑 DEPRECATED 2026-05-09 (BL-169):** Diese Pipeline ist nicht mehr aktiv.
> TDD-Logik (RED/GREEN/REFACTOR-Cycle, Verify, FanIn, Stage-QG) wandert in
> `_I_orchestrate.md` als flache Top-Level-Steps 9-18 am Pipeline-Ende
> (nach Blueprint-Steps 1-8, vor Stage-Closure-Steps 19-20). 100% Coverage
> aller TDD-Faehigkeiten in I-Pipeline.
>
> **Begruendung:** F109 Live-Beobachtung (DCSRE-486 2026-05-09) zeigte dass
> 2 separate Orchestratoren (I + TDD) Worker erlauben, beide zu skippen und
> direkt Code zu generieren ohne TDD-Tests. Single-Orchestrator-Pattern
> (I mit absorbiertem TDD) ist robuster.
>
> **TDD-Sub-Skills bleiben aktiv** und werden von I-Orchestrate aufgerufen:
> - `_TDD_red.md` (RED-Phase)
> - `_TDD_green.md` (GREEN-Phase)
> - `_TDD_refactorCode.md` + `_TDD_refactorTests.md`
> - `_TDD_execute.md` (Test-Run)
> - `_TDD_check.md` (GOLD-Check)
> - `_TDD_init.md` (HiL-Wizard, optional)
>
> **NUR dieser TOP-LEVEL-Orchestrator ist DEPRECATED.** Sub-Skills bleiben.
>
> **Rollback-Pfad:** Datei bleibt bis 2026-Q3 als Backup (NICHT loeschen).
> Falls BL-169 fehlschlaegt → Reaktivieren via Header-Edit `status: active`.
>
> **Caller-Migration:** `Skill(_TDD_orchestrate)` → `Skill(_I_orchestrate, args="... --tdd=true --stage=N")`.

```yaml
status: DEPRECATED
deprecated_at: 2026-05-09
deprecated_by: BL-169
replaced_by: _I_orchestrate.md Steps 9-18 (TDD am Pipeline-Ende, flach gemerged)
keep_until: 2026-Q3
version: 1.1.0
created: 2026-03-08
updated: 2026-05-09
op: ImplementationPipeline
phase: TDD
type: orchestration_deprecated
chain_position: tdd-playbook
team_based: true
depends_on:
  - _SDF_orchestrate
  - _I_codeAtomic
feeds_into:
  - _SDF_orchestrate
  - _W_push_orchestrate
related:
  - _I_codeIntegration
  - _I_codeSystem
bl_134_pflaster: true
bl_134_pflaster_inserted: 2026-04-25
bl_134_pflaster_real_refactor_in: BL-137
bl_140_pflaster_code: true
```

---

> **Registry-Loader (MLG S3 Log-Doppel):** Dieses Command nutzt `.claude/hooks/load_registries.py::resolve()` fuer Model-Resolution (ModelLeakGuard Feature, 4-Stufen-Kette: Welle-Schema → Session-Cap → Command-Override → Spawn).
> Jeder Spawn ruft vor `Agent(...)` das Pattern auf:
> `r = resolve(command="{CMD}", wave="w1|w2|seq", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})`
> → `r.subagent_type` und `r.model` sind die Soll-Werte. Der `[SPAWN]`-Top-Log protokolliert sie VOR dem Agent-Call. Der Worker quittiert spiegelnd mit `[AGENT]`-Bottom-Log (Schritt 0 im KURZLEBIG_PROMPT).
> HINWEIS: `resolve_agent_type()` unten bleibt als COMMAND_MODEL_MAP-Wrapper erhalten; `resolve()` stellt die 4-Stufen-Kaskade davor.

---

## PLAYBOOK-GUARD (PFLICHT — DCSRE-89 Prevention)

DIESES DOKUMENT IST EIN PLAYBOOK FUER DEN TEAM LEAD.
ES DARF NICHT ALS SKILL VON EINEM AGENT AUSGEFUEHRT WERDEN.

Falls du ein Agent bist und diesen Text liest:
→ STOPP. Du darfst dieses Dokument NICHT ausfuehren.
→ SendMessage an Team Lead: "PLAYBOOK-GUARD VERLETZT: Agent hat _TDD_orchestrate geladen"
→ TaskUpdate: status=completed (ABBRUCH)

---

## CALLER-GUARD (PFLICHT — PFLASTER 2026-04-20, CaseStudy BL-125 AK-6)

**Wer darf mich aufrufen?** NUR SDF nach needs_tdd-Signal von I.

PRE-EXECUTION CHECK (Team Lead pruefen VOR Schritt 7b Ring-Planung):

```
manifest.reload()
assert manifest.I_PIPELINE_STATE.needs_tdd == true, \
  "TDD-Aufruf ohne NEEDS_TDD-Signal — I hat nicht korrekt Handschuh uebergeben."
assert manifest.I_PIPELINE_STATE.handschuh_wechsel_pending == true, \
  "TDD-Aufruf ohne Handschuh-Wechsel-Signal — I hat Mega-Worker versucht."
assert manifest.I_PIPELINE_STATE.tdd_pipeline_mode == "I_TDD_ACTIVE", \
  "TDD-Aufruf ohne tdd_pipeline_mode=I_TDD_ACTIVE — SDF-Routing broken."
```

Wenn einer der Checks fehlschlaegt:
→ STOPP. Logge: "[CALLER-GUARD] TDD-Aufruf ohne saubere I→SDF→TDD-Kette."
→ Zurueck an I mit Fehler-Hinweis auf Puppet-Master-Regeln.

**Begruendung:** In BL-125 AK-6 hat Team Lead nach Blueprint-DONE einen
Mega-Worker "impl-tests-ak6" gespawnt statt needs_tdd=true zu setzen. Der
Worker hat Controller + 6 Tests + Docker gleichzeitig versucht, wurde
interrupted, Controller-Code blieb im Working-Tree. Strict RED-First war
uebersprungen. Dieser Caller-Guard verhindert dass TDD so gestartet wird.

---

## PUPPET-MASTER-REGELN TDD (PFLASTER 2026-04-20, analog _A_orchestrate)

Innerhalb TDD (Schritt 7b bis Schritt 11) orchestriert der Team Lead:

1. **Schritt 7b (Ring-Planung)** — 1 Worker pro Slice, NICHT kombiniert mit Impl
2. **Schritt 8a (RED)** — 1 Worker: Test schreiben (muss FAIL), NICHT mit Code
3. **Schritt 8b (Execute-RED)** — 1 Worker: `dotnet test` laufen, bestaetigt FAIL
4. **Schritt 8c (GREEN)** — 1 Worker: minimaler Code fuer GREEN
5. **Schritt 8d (Execute-GREEN)** — 1 Worker: `dotnet test` laufen, bestaetigt PASS
6. **Schritt 8e-8i** — je eigener Worker fuer Refactor/Execute/Check
7. **Schritt 9 (verify)** — 1 Worker pro Slice
8. **Schritt 10 (fanIn)** — 1 Worker sequentiell
9. **Schritt 11 (Stufen-QG)** — 1 Worker

**ANTI-PATTERN (VERBOTEN):**
- `Agent(prompt="Impl + 6 Tests + Build + Docker + dotnet test")` ← BLOCK
- `Agent(prompt="Alle Ring-Iterationen auf einmal")` ← BLOCK
- `Agent(prompt="Nachziehen" bei fehlendem RED-Beweis)` ← BLOCK

**REGEL "RED-FIRST BEWEIS":** Vor Schritt 8c (GREEN) MUSS Schritt 8b
(Execute-RED) dokumentiert haben dass der Test FAIL war. Ohne diesen
Beweis ist TDD verletzt — Code wurde vor Test geschrieben.

---

```
+======================================================================+
| META-COMMAND: /_TDD_orchestrate                                       |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (gleiche Instanz wie _I_orchestrate)                 |
|   CONSTRAINT: Team Lead fuehrt KEINEN Code aus, KEINE Tests.         |
|   NUR spawnen, tracken, entscheiden.                                  |
|                                                                        |
| ZWECK: Fuehrt TDD fuer EINE Stufe (von I_orchestrate aufgerufen):    |
|   I_orchestrate steuert den Stufen-Loop (Blueprint → TDD → naechste) |
|   TDD verarbeitet NUR current_stage: Ring-Planung + 8a-8i + QG       |
|                                                                        |
| AUFGERUFEN VON: Team Lead (Playbook-Wechsel aus _I_orchestrate)      |
| GIBT ZURUECK AN: /_I_orchestrate (Post-Pipeline Phase)               |
|                                                                        |
| PRO STUFE:                                                            |
|   7b. Ring-Planung (pro Slice, Worker)                               |
|   8.  TDD-Zyklus (8a-8i, Backtrack bei Execute-Failure)             |
|   9.  /_I_verify (pro Slice)                                         |
|   HiL: Commits                                                       |
|  10.  /_I_fanIn (sequentiell pro Slice)                              |
|  11.  Stufen-QG (Kanarienvogel-Check + HiL)                         |
|                                                                        |
| UEBERGANG:                                                            |
|   Manifest I_PIPELINE_STATE.phase = "TDD" (Eingang)                 |
|   Manifest I_PIPELINE_STATE.phase = "POST_TDD" (Ausgang)            |
+======================================================================+
```

---

## VERTRAG

```
LIEST:
  {WORKING_DIR}/_manifest.md     (I_PIPELINE_STATE: phase=TDD, slices, worktrees, current_stage,
                                   parent_team, worker_mode — per-Story, BL-155 AK-1)
  .claude/meta/implementation/stage_{N}.md  (Stufen-Metadaten)
  {WORKTREE}/.claude/TDD-STATE.md  (Ring-Position, Gold-Distanz — Worktree-local)
  {BL_FOLDER}/4_Blueprint/S{N}/blueprint.md  (Stufen-Blueprint — Vault-First, BL-NEW-30/43)
    LEGACY-Fallback (NUR wenn Vault-Read ENOENT): {WORKING_DIR}/.claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md
  {BL_FOLDER}/4_Blueprint/{SLICE}/sub-{NR}.md  (Sub-Blueprints — Vault-First, BL-NEW-30/43)
    LEGACY-Fallback (NUR wenn Vault-Read ENOENT): {WORKING_DIR}/.claude/analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md
  # WORKER-PATH-INV-1 (2026-05-11): TDD-Workers MUSS Schritt 0 PATH-RESOLUTION
  # ausfuehren VOR jedem Sidecar-Read/Write — Verstoss bei BL-NEW-43 detected.

MANIFEST-SCHREIB-MUSTER (ManifestSplit, ADR-3):
  Pattern B: State-Write + Protokoll-Rollover (W18)
  SCHREIBT STATE (_manifest.md):
    I_PIPELINE_STATE.impl_test_stages[N].status, current_stage,
    last_stage_completed, worktrees[slice].tdd_status/tdd_iteration
    (nach jeder Stufe: aktuelle Laufzeit-Felder)
  SCHREIBT PROTOKOLL (_manifest_protokoll.md, Rollover):
    Nach Stufe N abschliessen (nach jeweils N-2 TDD-Stufen):
    Rotiere abgeschlossene TDD-Stufen-Eintraege aus _manifest.md:
    Prepend an _manifest_protokoll.md (W18):
      last_append + append_count++ im Frontmatter
      ## TDD_orchestrate [{Datum}] S{N}
      [Archivierte Felder: stage, iterations, gold_reached, tdd_status]

SCHREIBT:
  {WORKTREE}/.claude/TDD_INSTRUCTIONS.md  (pro Slice, Schritt 7a)
    stufe, testbefehl, testpfad, mocks_erlaubt, mock_scope,
    infrastruktur, parallelitaet_max, blueprint_perspektive
    Quelle: stage_{N}.md Frontmatter → TDD_INSTRUCTIONS.md
    Bei slicing=false: WORKTREE = WORKTREE_DEFAULT_PATH
    Guard: testbefehl=="TBD" → HiL-Eskalation (oder Auto-SKIP bei HiL=off)
    Mock-Scope-Mapping: ja→"alle_externen", begrenzt→"extern_only",
                         nein→"keine", default→"unbekannt"+WARNING
  {WORKING_DIR}/_manifest.md:  # per-Story (BL-155 AK-1)
    I_PIPELINE_STATE.impl_test_stages[N].status
    I_PIPELINE_STATE.current_stage
    I_PIPELINE_STATE.last_stage_completed
    I_PIPELINE_STATE.worktrees[slice].tdd_status
    I_PIPELINE_STATE.worktrees[slice].tdd_iteration
    I_PIPELINE_STATE.tdd_stage_result  (stage, iterations, gold_reached, overall_status)
    I_PIPELINE_STATE.phase             (TDD → POST_TDD, bei Blocker: PAUSED)
    I_PIPELINE_STATE.tdd_alarm  (Alarm-Signal, bei Stuck N>=3)
      triggered, stufe, slice_id, severity, grund, stuck_stage,
      tdd_iteration, recommendation
      Reset: Nach Phase 3 R4 durch I_orchestrate (triggered = false)

INVARIANTEN:
  - Team Lead fuehrt KEINE Commands aus (R2)
  - 1 Agent = 1 Command = 1 Batch (R3, R4)
  - Kein Agent spawnt Sub-Agents (W7, R9)
  - Manifest-Update nach JEDER Stufe und jedem Batch-Zyklus
  - I→SC Return Check nach jedem Batch → {META}/implementation/i-sc-return.md
  - INV-AO-CALLER (V11/V12, 2026-05-07/2026-05-08):
    Skill(_TDD_orchestrate) DIREKT vom Team Lead — kein Hub-Delegate
    via Agent(general-sonnet, prompt="orchestrate ..."). Sub-Agent wird
    Mega-Agent (8a..8i Stufen werden Inline-Logik). Siehe CLAUDE.md Z6
    + _A_orchestrate INVARIANTEN. Beweis: DCSRE-2014 Hot-Fix.
```

---

## SCHRITT 0: BL-140 Batch-Pflaster (echter Branch)

<!-- BL-144 L4: Echter Branch-Header fuer Batch-Pflaster. INV-TDD-PFLASTER-3 unten. -->

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
  Logge: "[BL-134-PFLASTER] tdd_orchestrate batch-modus: {len(batch)} Items sequentiell."
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

- **tdd_orchestrate echter Refactor:** BL-137

### INV-TDD-PFLASTER-1

Pflaster-Pfad MUSS sequentiell bleiben bis BL-137 den echten Refactor liefert.
Paralleler intern-Loop ohne explizite BATCH_STATE-Race-Locks ist VERBOTEN.

### BL-140 PFLASTER-CODE (echte Implementation)

```
# CLI-Param oder Manifest
batch = lies CLI_PARAM("batch") OR DF_BATCH_STATE.batch_items
IF batch != null AND |batch| > 0:
  Logge: "[BL-140-PFLASTER] tdd_orchestrate Batch-Modus: {len(batch)} Items sequentiell"
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

INV-TDD-PFLASTER-2 (NEU, BL-140):
Pflaster-Code MUSS sequentiell iterieren (kein paralleler Loop ohne Race-Lock).
Pflaster-Code MUSS item_done.append nach JEDEM erfolgreichen Item.
Pflaster-Code MUSS RETURN am Ende des batch-Pfads (NICHT in den Legacy-Pfad fallen).

INV-TDD-PFLASTER-3 (BL-144):
Echter Batch-Branch IM Pipeline-Body -- NICHT nur Doku am Datei-Ende.
Der SCHRITT-0-Block MUSS vor PHASE 1 aktiv ausgefuehrt werden (kein toter Doku-Anhang).

---

## Aufruf

```
/_TDD_orchestrate {NAME} [--testRun]
```

Wird vom Team Lead als Playbook-Wechsel geladen. Liest alle Parameter aus dem Manifest.

| Parameter | Default | Typ | Beschreibung |
|-----------|---------|-----|-------------|
| `NAME` | (Manifest) | String | Feature-Name |
| `--testRun` | false | Flag | Execute-only Modus: KEIN Red/Green/Refactor. NUR vorhandene Tests ausfuehren und Report generieren. |

---

## Autonomie-Guard (Puppet Master) # (PM: Puppet-Master-Pattern)

```
# Am Anfang, nach Parameter-Validierung (Manifest laden):
IF GLOBAL_HIL == "off":
  tdd_hil_mode = "autonom"
  Logge: "TDD Autonomie: Backtrack-Entscheidungen automatisch (kein HiL)."
  # MAX_BACKTRACK wird normal angewendet, aber HiL-Eskalation → Auto-SKIP
  # Statt AskUserQuestion bei Backtrack-Erschoepfung: Auto-SKIP des Rings, weiter
```

---

## Prozess-Statusanzeige RF-10 (TDD-Schritte fuer aktuelle Stufe)

Team Lead gibt nach JEDEM Schrittwechsel innerhalb der aktuellen Stufe folgende Tabelle aus.
**Stufe N wird von I_orchestrate gesetzt. TDD zeigt Fortschritt der TDD-Schritte 7a-11.**

```
┌────┬─────────────────────────┬──────────────────────┬─────────────┬──────────┬──────────────────────────────────┐
│ #  │ Schritt                 │ Agenten              │ Modell      │ Status   │ Inhalt (Mini-Assay, NUR bei DONE)│
├────┼─────────────────────────┼──────────────────────┼─────────────┼──────────┼──────────────────────────────────┤
│ 7a │ TDD_INSTRUCTIONS        │ Team Lead direkt     │ (TL-Kontext)│ + DONE   │ 3 Slices, testbefehl=dotnet test │
│ 7b │ Ring-Planung            │ {M} Agents sequenz.  │ sonnet      │ + DONE   │ S1: 4 Ringe, Gold = 3 AKs        │
│ 8  │ TDD-Zyklus (8a-8i)      │ {M} Agents sequenz.  │ sonnet*     │ > ACTIVE │ (*opus nur fuer 8e refactorCode) │
│ 9  │ verify (pro Slice)      │ {M} Agents sequenz.  │ sonnet      │ . PENDING│                                  │
│ 10 │ fanIn                   │ {M} Agents sequenz.  │ sonnet      │ . PENDING│                                  │
│ 11 │ Stufen-QG               │ 1 Worker + optional  │ sonnet      │ . PENDING│ (HiL=off: Worker; HiL=on: TL+Q)  │
└────┴─────────────────────────┴──────────────────────┴─────────────┴──────────┴──────────────────────────────────┘
TDD Stufe {N}/5 | Slices: {slice_count} | Iterationen: {tdd_iteration_count}
```

**Inhalt-Spalte:** 1-2 Saetze INHALTLICH (Tests, Rings, Gold-Status), NUR bei DONE.
**Status-Symbole:** + DONE, > ACTIVE, . PENDING, - SKIP, x FAIL
**Fusszeile:** Aktuelle Stufe aus Manifest, Anzahl Slices, TDD-Iterationen kumuliert.
**Wann:** Nach Abschluss jedes TDD-Schritts (7a, 7b, 8, 9, 10, 11) vor Start des naechsten.
**Bei --testRun Modus:** Nur Schritte 7a+8 (Execute-only) -- restliche Zeilen als - SKIP.
**Kein RF-9:** TDD hat kein Wellen-Pattern. Alle Agents sind single-command-Worker (analog SDF).

---

## TDD Sub-Phasen pro Stufe (AK-05-03, BL-036)

Manifest-Feld: I_PIPELINE_STATE.tdd_sub_phase

| Sub-Phase        | Manifest-Wert     | Uebergang zu         |
|------------------|--------------------|----------------------|
| TDD_INSTRUCTIONS | tdd_instructions   | ring_planung         |
| Ring-Planung     | ring_planung       | tdd_zyklus           |
| TDD-Zyklus (8a-8i) | tdd_zyklus      | verify               |
| verify           | tdd_verify         | fan_in               |
| fanIn            | tdd_fan_in         | stufen_qg            |
| Stufen-QG        | stufen_qg          | DONE (→ SDF-HUB)    |

---

## Stufen-Verarbeitung (Einzelne Stufe)

TDD verarbeitet NUR die aktuelle Stufe. I_orchestrate steuert den aeusseren
Stufen-Loop: Blueprint fuer Stufe N → TDD fuer Stufe N → Blueprint N+1 → usw.
Grund: Blueprints muessen VOR TDD pro Stufe erstellt werden.

### Dry-Run Short-Circuit (BL-092, Universal_Dry_Run_Pattern — 7. und letztes Child)

```
# BL-092: TDD-Pipeline Dry-Run-Modus (7. Child, komplettiert das Universal Pattern)
# Vorgaenger: BL-082 BDF, BL-087 SDF, BL-088 IDF, BL-089 A, BL-090 SC, BL-091 I
tdd_mode = $ARGUMENTS.mode ?? _session_params.mode ?? "normal"

IF tdd_mode == "dryRun":
  Logge: "[BL-092 TDD DRY-RUN] Mock-Modus — RED/GREEN/REFACTOR skipped"

  tdd_dry_run_report = {
    date: {Datum},
    feature: NAME,
    mode: "dryRun",
    current_stage: manifest.I_PIPELINE_STATE.current_stage,
    would_run: [
      "Schritt 7a: TDD_INSTRUCTIONS.md befuellen",
      "Schritt 7b: Ring-Planung pro Slice",
      "Schritt 8 TDD-Zyklus: /_TDD_red → /_TDD_execute → /_TDD_green → /_TDD_refactorCode → /_TDD_refactorTests → /_TDD_check",
      "Stufen: S1 Unit → S2 Module → S3 Integration → S4 System → S5 E2E",
      "Keine Tests ausgefuehrt, keine RED/GREEN/REFACTOR-Zyklen"
    ],
    skipped: true
  }

  tdd_dry_run_report_path = "{WORKING_DIR}/.claude/output/TDD_DryRun_{NAME}_{Datum}.md"
  Schreibe {tdd_dry_run_report_path} mit tdd_dry_run_report Inhalt

  Schreibe in _manifest.md → TDD_PIPELINE_STATE:
    name: NAME
    modus: dryRun
    phase: DRY_RUN_DONE
    mock_report: {tdd_dry_run_report_path}

  Logge: "[BL-092 TDD DRY-RUN] Mock-Completion — Universal_Dry_Run_Pattern 7/7 COMPLETE"
  → Return zu Aufrufer
```

```
# Aktuelle Stufe aus Manifest lesen (von I_orchestrate gesetzt)
N = manifest.I_PIPELINE_STATE.current_stage

metadaten = lade_stage_n(N)
IF metadaten.status == "placeholder":
  → HiL-Eskalation (STOPP)

manifest.I_PIPELINE_STATE.impl_test_stages[N].status = "running"
```

---

## Schritt 7a: TDD_INSTRUCTIONS.md befuellen (RF-06, RF-07, RF-08, RF-09)

```
metadaten = lade_stage_n(N)  # bereits fuer Placeholder-Check geladen (Z127-129)

# Guard: TBD-Testbefehl (RF-06 AK-06-3)
IF metadaten.testbefehl starts_with "TBD":
  IF GLOBAL_HIL == "on" OR GLOBAL_HIL == "cycle" OR GLOBAL_HIL == "phase":
    testbefehl_konkret = AskUserQuestion("Stufe {N}: testbefehl=TBD. Konkreten Befehl eingeben:")
    metadaten.testbefehl = testbefehl_konkret
  ELSE:
    Logge: "WARNING: Stufe {N} testbefehl=TBD, HiL=off → Stufe SKIPPED"
    manifest.I_PIPELINE_STATE.impl_test_stages[N].status = "skipped"
    RETURN  # Kein Fall-Through zu Ring-Planung (Schritt 7b)

# Mock-Scope ableiten (RF-08)
mock_scope = SWITCH(metadaten.mocks_erlaubt):
  "ja"       → "alle_externen"
  "begrenzt" → "extern_only"
  "nein"     → "keine"
  default    → "unbekannt" + WARNING Logge: "WARNING: mocks_erlaubt Wert unbekannt: {metadaten.mocks_erlaubt}"

# TDD_INSTRUCTIONS.md per Worktree schreiben (RF-06, RF-07, RF-09)
# Bei slicing=false: aktive_slices aus Blueprint (Architect hat Slices definiert),
# aber worktree_path = WORKTREE_DEFAULT_PATH (gleicher Branch fuer alle Slices, sequentiell)
FOR EACH slice IN aktive_slices:
  SCHREIBE {slice.worktree_path}/.claude/TDD_INSTRUCTIONS.md:
    ---
    stufe: {N}
    testbefehl: {metadaten.testbefehl}
    testpfad: {metadaten.testpfad OR "auto"}
    mocks_erlaubt: {metadaten.mocks_erlaubt}
    mock_scope: {mock_scope}
    infrastruktur: {metadaten.infrastruktur OR "standard"}
    parallelitaet_max: {metadaten.ressourcen_constraints.parallelitaet_max OR "auto"}
    blueprint_perspektive: {metadaten.blueprint_perspektive OR "standard"}
    ---

Logge: "Schritt 7a: TDD_INSTRUCTIONS.md fuer Stufe {N} in {len(aktive_slices)} Worktrees geschrieben."
```

---

## Schritt 7b: Ring-Planung (pro Slice)

```
FOR EACH slice IN aktive_slices:
  task_id = TaskCreate(subject="[S{N}/{slice}] Ring-Planung")
  # MLG S3 Log-Doppel (2026-04-24): resolve() + [SPAWN]-Top-Log
  r = resolve(command="ringPlan", wave="seq", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
  ring_worker = "i-sc-{slice}-ringPlan-b1"
  Logge: "[SPAWN] worker={ring_worker} type={r.subagent_type} model={r.model} cmd=ringPlan wave=seq stufe={N}"
  Task(
    name=ring_worker,
    subagent_type=r.subagent_type,
    model=r.model,
    prompt=KURZLEBIG_PROMPT(slice=slice, command="ringPlan",
           batch_num=1, task_id=task_id,
           extra="--stufe {N}
             AUFTRAG: Lies Sub-Blueprint sub-{NR}.md.
             1. Definiere Gold (Akzeptanzkriterien aus Blueprint).
             2. Identifiziere Kanarienvoegel (bestehende Tests die gruen bleiben muessen).
             3. Plane konzentrische Ringe (code-agnostisch, 1 Ring = 1 Assertion).
             4. Schreibe TDD-STATE.md mit rings[], gold, canary_tests.
             KEIN Code, KEINE Tests — NUR planen.")
  )
warte_bis_alle_completed(slices, "ringPlan")
→ Output: TDD-STATE.md pro Slice
→ Manifest: stufen_status.ringPlan: done
```

---

## Schritt 8: TDD-Zyklus (Innerer Loop)

Uncle Bob TDD in separaten Agents. Vertrag zwischen Agents: TDD-STATE.md.
Methodik lebt in den TDD-Commands + stage_N.md (NICHT hier duplizieren).

```
TDD_SEQUENZ = [
  "_TDD_red",              # 8a: Tests schreiben
  "_TDD_execute:RED",      # 8b: MUSS rot
  "_TDD_green",            # 8c: Minimaler Code
  "_TDD_execute:GREEN",    # 8d: MUSS gruen
  "_TDD_refactorCode",     # 8e: Code refaktorisieren
  "_TDD_execute:GREEN",    # 8f: Nach Refactor gruen?
  "_TDD_refactorTests",    # 8g: Tests refaktorisieren
  "_TDD_execute:GREEN",    # 8h: Nach Test-Refactor gruen?
  "_TDD_check"             # 8i: GOLD erreicht?
]

# Modell-Zuordnung pro TDD-Schritt (PFLASTER 2026-04-20, sync mit COMMAND_MODEL_MAP):
#   _TDD_red:           sonnet (Kreativitaet: Test schreiben)
#   _TDD_execute:       sonnet (User-Override: haiku halluzinierte Bash-Outputs)
#   _TDD_green:         sonnet (Kreativitaet: minimaler Code)
#   _TDD_refactorCode:  OPUS   (Architektur: DRY, Extract, Abstraktion)  ← einziges Opus im TDD-Zyklus
#   _TDD_refactorTests: sonnet (Kreativitaet: Assertions verfeinern)
#   _TDD_check:         sonnet (Synthese: Gold-Entscheidung)

STUFEN_MAX_ITERATIONS = {
  1: {easy: 5, normal: 8,  hard: 12},   # Unit-Tests: schnelle Zyklen
  2: {easy: 5, normal: 8,  hard: 12},   # Integration: Standard
  3: {easy: 6, normal: 10, hard: 15},   # System: mehr Iterationen
  4: {easy: 6, normal: 10, hard: 15},   # System+: erhoehte Toleranz
  5: {easy: 8, normal: 12, hard: 18}    # E2E: maximale Iterationen
}
MAX_BACKTRACK_PER_STEP = 3
```

### Backtrack-Map

```
┌──────────────────────┬──────────┬────────────────────────┐
│ Schritt              │ Erwartet │ Bei Failure → zurueck  │
├──────────────────────┼──────────┼────────────────────────┤
│ 8b: tddExecute(RED)  │ ROT      │ → 8a: tddRed           │
│ 8d: tddExecute(GREEN)│ GRUEN    │ → 8c: tddGreen         │
│ 8f: tddExecute(GREEN)│ GRUEN    │ → 8e: tddRefactorCode  │
│ 8h: tddExecute(GREEN)│ GRUEN    │ → 8g: tddRefactorTests │
└──────────────────────┴──────────┴────────────────────────┘

8i: tddCheck → NOT_YET → zurueck zu 8a (naechster Ring)
8i: tddCheck → GOLD_REACHED → Slice DONE
```

### TDD-Loop pro Slice

```
# ═══ testRun-GUARD (TestStufen Z1) ═══
IF testRun == true:
  Logge: "[testRun] Execute-only Modus — Skip Red/Green/Refactor"
  # NUR execute: Alle vorhandenen Tests fuer aktuelle Stufe ausfuehren
  Skill(skill="_TDD_execute", args="{NAME}")
  # Ergebnis sammeln
  IF alle_tests_gruen:
    Logge: "[testRun] PASS — alle Tests gruen"
    status = COMPLETE
  ELSE:
    Logge: "[testRun] FAIL — {N} Tests fehlgeschlagen"
    status = FAIL
  RETURN status
# ═══ Ende testRun-GUARD ═══

FOR EACH slice IN aktive_slices:
  tdd_iteration = 0
  gold_reached = false

  WHILE NOT gold_reached:
    tdd_iteration += 1
    backtrack_counts = {}

    # 8a: tddRed
    LABEL_8a:
    spawne_worker(slice, "_TDD_red", N, tdd_iteration)

    # 8b: tddExecute(RED)
    result = spawne_worker(slice, "_TDD_execute", N, tdd_iteration, expected="RED")
    IF NOT result.red_confirmed:
      backtrack_counts["8b"] = (backtrack_counts.get("8b") OR 0) + 1
      IF backtrack_counts["8b"] >= MAX_BACKTRACK_PER_STEP:
        IF GLOBAL_HIL == "off":
          IF N <= 2:
            Logge: "[AUTO-SKIP-RING] S{N}/{slice}: 8b->8a {MAX_BACKTRACK_PER_STEP}x gescheitert."
            BREAK_INNER  # Ring ueberspringen, naechste tdd_iteration
          ELSE:
            trigger_alarm(
              grund="Backtrack-Erschoepfung: 8b->8a {MAX_BACKTRACK_PER_STEP}x",
              stuck_stage="BACKTRACK",
              recommendation="SC_ANALYSE"
            )
            manifest.I_PIPELINE_STATE.phase = "POST_TDD"
            manifest.update()
            BREAK_ALL  # Beide Loops verlassen
        ELSE:
          AskUserQuestion("8b→8a {MAX_BACKTRACK_PER_STEP}x gescheitert. HiL noetig.")
      GOTO LABEL_8a

    # Pre-flight 8c: Gate-Timestamp Check (AK-A-1, INV-A1-1, F-001, BL-153)
    # Einschub-Strategie (INV-EINSCHUB): VOR GREEN-Spawn, NACH RED-Bestaetigung
    pattern_brief_at = lies DF_BATCH_STATE.pattern_brief_at aus _manifest.md
    slice_start_at   = NOW()  # Zeitpunkt an dem 8c beginnen soll
    IF pattern_brief_at IS NULL OR pattern_brief_at >= slice_start_at:
      BLOCKER: "[INV-A1-1] Gate-Timestamp-Verletzung (F-001): kein gueltiger patternBrief-Timestamp.
               pattern_brief_at={pattern_brief_at} muss < slice_start_at={slice_start_at}.
               Loesung: _SDF_berater_patternBrief vor diesem Batch laufen lassen."
      BREAK_ALL  # Keine Code-Implementierung ohne gueltigen Gate-Timestamp

    # Pre-8c: green_pattern_context aufbauen (ARCH-14, BL-153)
    # INV-EINSCHUB: NACH Gate-Timestamp-Check, VOR LABEL_8c — bestehender 8c-Schritt unveraendert.
    # Zweck: patternBrief + sliceBrief als Kontext fuer GREEN-Worker → Code wird MIT Patterns geschrieben.
    # NON-BLOCKING: leer/no_match → green_pattern_context=null → GREEN laeuft ohne Kontext (bisheriges Verhalten).
    green_pattern_context = null
    pb_gc  = lies BERATER_OUTPUTS.patternBrief ?? null
    sb_gc  = lies BERATER_OUTPUTS.sliceBrief   ?? null
    IF (pb_gc != null AND pb_gc.no_match == false AND (|pb_gc.matched_patterns| > 0 OR |pb_gc.matched_semantics ?? []| > 0)) OR
       (sb_gc != null AND sb_gc.no_match == false AND |sb_gc.matched_patterns| > 0):
      pat_ctx = (sb_gc?.matched_patterns ?? pb_gc?.matched_patterns ?? []) | ids
      sem_ctx = (pb_gc?.matched_semantics ?? []) | ids
      green_pattern_context = {
        matched_patterns:  (sb_gc?.matched_patterns ?? pb_gc?.matched_patterns ?? []),
        matched_semantics: (pb_gc?.matched_semantics ?? []),
        hinweis: "Schreibe Code der diesen Patterns entspricht: {pat_ctx}. " +
                 "Halte Semantik (Naming/Stil/Kommentare) ein: {sem_ctx}. " +
                 "NON-BLOCKING: Wo Pattern nicht anwendbar → ignorieren."
      }
      Logge: "[Pre-8c] green_pattern_context: {|pat_ctx|} Patterns + {|sem_ctx|} Semantics fuer GREEN-Worker"
    ELSE:
      Logge: "[Pre-8c] kein patternBrief/sliceBrief → green_pattern_context=null (NON-BLOCKING)"

    # 8c: tddGreen
    LABEL_8c:
    spawne_worker(slice, "_TDD_green", N, tdd_iteration, green_pattern_context=green_pattern_context)

    # Post-8c: PATTERN-VERTRAG-Block Validierung (AK-E-2, BL-153)
    # _TDD_green schreibt Block in Schritt 2.5 → TDD-STATE.md.
    # Erst NACH Spawn prüfbar, nicht vorab im KURZLEBIG_PROMPT.
    tdd_state_post_green = lese_tdd_state(slice, N)
    IF tdd_state_post_green.pattern_vertrag IS NULL OR
       tdd_state_post_green.pattern_vertrag.anwendungsbereich IS NULL:
      backtrack_counts["8c_vertrag"] = (backtrack_counts.get("8c_vertrag") OR 0) + 1
      IF backtrack_counts["8c_vertrag"] >= MAX_BACKTRACK_PER_STEP:
        BLOCKER: "[AK-E-2] PATTERN-VERTRAG-Block nach {MAX_BACKTRACK_PER_STEP}x gruen fehlt. BREAK."
        BREAK_ALL
      Logge: "[AK-E-2] PATTERN-VERTRAG-Block fehlt in TDD-STATE.md nach _TDD_green — 8c Backtrack."
      GOTO LABEL_8c

    # Post-8c: matched_patterns vs. verwendete_vorlagen Cross-Check (ARCH-17, BL-153)
    # INV-EINSCHUB: NACH PATTERN-VERTRAG-Block-Existenz-Check — Green_context-bewusstes Gate.
    # Zweck: Wenn Patterns geladen, muss verwendete_vorlagen Bezug nehmen — "Boilerplate" kein Freifahrtschein.
    # NON-BLOCKING-Richtung: Wenn green_pattern_context=null → kein Cross-Check (bisheriges Verhalten).
    IF green_pattern_context != null AND |green_pattern_context.matched_patterns| > 0:
      vorlagen = tdd_state_post_green.pattern_vertrag.verwendete_vorlagen ?? ""
      pat_ids  = green_pattern_context.matched_patterns | ids als Liste
      referenz_ok = (
        IRGENDEINE ID aus pat_ids enthalten in vorlagen
        OR vorlagen enthaelt "kein relevantes Pattern:" mit Layer-Begruendung
        OR vorlagen enthaelt "Library leer:"
      )
      IF NOT referenz_ok:
        backtrack_counts["8c_cross"] = (backtrack_counts.get("8c_cross") OR 0) + 1
        IF backtrack_counts["8c_cross"] >= MAX_BACKTRACK_PER_STEP:
          BLOCKER: "[ARCH-17] Cross-Check erschoepft: verwendete_vorlagen referenziert keine Patterns nach {MAX_BACKTRACK_PER_STEP}x. BREAK."
          BREAK_ALL
        Logge: "[ARCH-17] Cross-Check: verwendete_vorlagen muss mind. 1 ID aus {pat_ids} referenzieren ODER 'kein relevantes Pattern: {Layer}'. 'Boilerplate' nicht ausreichend wenn Patterns existieren — 8c Backtrack."
        GOTO LABEL_8c

    # 8d: tddExecute(GREEN)
    result = spawne_worker(slice, "_TDD_execute", N, tdd_iteration, expected="GREEN")
    IF NOT result.green_confirmed:
      backtrack_counts["8d"] = (backtrack_counts.get("8d") OR 0) + 1
      IF backtrack_counts["8d"] >= MAX_BACKTRACK_PER_STEP:
        IF GLOBAL_HIL == "off":
          IF N <= 2:
            Logge: "[AUTO-SKIP-RING] S{N}/{slice}: 8d->8c {MAX_BACKTRACK_PER_STEP}x gescheitert."
            BREAK_INNER
          ELSE:
            trigger_alarm(
              grund="Backtrack-Erschoepfung: 8d->8c {MAX_BACKTRACK_PER_STEP}x",
              stuck_stage="BACKTRACK",
              recommendation="SC_ANALYSE"
            )
            manifest.I_PIPELINE_STATE.phase = "POST_TDD"
            manifest.update()
            BREAK_ALL
        ELSE:
          AskUserQuestion("8d→8c gescheitert. HiL noetig.")
      GOTO LABEL_8c

    # Pre-8e: Library-Pass + Polier-Auftrag (AK-F-8, AK-B-4, BL-153 ARCH-13)
    # INV-EINSCHUB: VOR LABEL_8e — bestehender 8e-Schritt unveraendert.
    # Zweck: Matched Patterns + Semantics aus patternBrief → Polier-Auftrag fuer Refactor-Worker.
    # NON-BLOCKING: Leere Library oder kein patternBrief → polier_kontext=null → kein Auftrag.
    # ARCH-13 (BL-153): matched_semantics in polier_kontext eingeschlossen (war vorher ignoriert).
    polier_kontext = null
    pb = lies BERATER_OUTPUTS.patternBrief ?? null
    IF pb != null AND pb.no_match == false AND (|pb.matched_patterns| > 0 OR |pb.matched_semantics| > 0):
      pat_ids = pb.matched_patterns | ids als Komma-Liste
      sem_ids = pb.matched_semantics ?? [] | ids als Komma-Liste
      polier_kontext = {
        matched_patterns:  pb.matched_patterns,
        matched_semantics: pb.matched_semantics ?? [],
        auftrag: "Bei JEDEM Umbau: Pruefe ob der Code den registrierten Patterns UND Semantics entspricht. " +
                 "Patterns (strukturell): {pat_ids}. " +
                 "Semantics (Naming/Stil/Kommentare): {sem_ids}. " +
                 "Wo Konformanz erreichbar: anwenden. Wo nicht: WARN im PATTERN-VERTRAG-Block."
      }
      Logge: "[Pre-8e] Polier-Auftrag: {|pb.matched_patterns|} Patterns + {|pb.matched_semantics ?? []|} Semantics als Refactor-Kontext"
    ELSE:
      Logge: "[Pre-8e] Polier-Auftrag: kein patternBrief oder no_match=true → polier_kontext=null (NON-BLOCKING)"

    # 8e: tddRefactorCode
    LABEL_8e:
    spawne_worker(slice, "_TDD_refactorCode", N, tdd_iteration, polier_kontext=polier_kontext)

    # 8f: tddExecute(GREEN)
    result = spawne_worker(slice, "_TDD_execute", N, tdd_iteration, expected="GREEN")
    IF NOT result.green_confirmed:
      backtrack_counts["8f"] = (backtrack_counts.get("8f") OR 0) + 1
      IF backtrack_counts["8f"] >= MAX_BACKTRACK_PER_STEP:
        IF GLOBAL_HIL == "off":
          IF N <= 2:
            Logge: "[AUTO-SKIP-RING] S{N}/{slice}: 8f->8e {MAX_BACKTRACK_PER_STEP}x gescheitert."
            BREAK_INNER
          ELSE:
            trigger_alarm(
              grund="Backtrack-Erschoepfung: 8f->8e {MAX_BACKTRACK_PER_STEP}x",
              stuck_stage="BACKTRACK",
              recommendation="SC_ANALYSE"
            )
            manifest.I_PIPELINE_STATE.phase = "POST_TDD"
            manifest.update()
            BREAK_ALL
        ELSE:
          AskUserQuestion("8f→8e gescheitert. HiL noetig.")
      GOTO LABEL_8e

    # Pre-8g: Polier-Auftrag weitergeben (AK-F-8, AK-B-4, BL-153)
    # polier_kontext aus Pre-8e wiederverwenden (gleicher Batch-Scope).
    Logge: "[Pre-8g] Polier-Auftrag fuer Tests: polier_kontext={polier_kontext != null}"

    # 8g: tddRefactorTests
    LABEL_8g:
    spawne_worker(slice, "_TDD_refactorTests", N, tdd_iteration, polier_kontext=polier_kontext)

    # 8h: tddExecute(GREEN)
    result = spawne_worker(slice, "_TDD_execute", N, tdd_iteration, expected="GREEN")
    IF NOT result.green_confirmed:
      backtrack_counts["8h"] = (backtrack_counts.get("8h") OR 0) + 1
      IF backtrack_counts["8h"] >= MAX_BACKTRACK_PER_STEP:
        IF GLOBAL_HIL == "off":
          IF N <= 2:
            Logge: "[AUTO-SKIP-RING] S{N}/{slice}: 8h->8g {MAX_BACKTRACK_PER_STEP}x gescheitert."
            BREAK_INNER
          ELSE:
            trigger_alarm(
              grund="Backtrack-Erschoepfung: 8h->8g {MAX_BACKTRACK_PER_STEP}x",
              stuck_stage="BACKTRACK",
              recommendation="SC_ANALYSE"
            )
            manifest.I_PIPELINE_STATE.phase = "POST_TDD"
            manifest.update()
            BREAK_ALL
        ELSE:
          AskUserQuestion("8h→8g gescheitert. HiL noetig.")
      GOTO LABEL_8g

    # 8i: tddCheck
    spawne_worker(slice, "_TDD_check", N, tdd_iteration)
    state = lese_tdd_state(slice, N)

    # 8j: Quick Gate Pattern-Konformanz Slice-Ebene (AK-A-2, BL-153)
    # Einschub-Strategie (INV-EINSCHUB): NACH 8i tddCheck, VOR gold_reached-Pruefung
    # Scope: nur Slice-Dateien (nicht vollstaendiger Batch-Diff)
    # NON-BLOCKING: Quick Gate WARN → weiter; BLOCKER → Loop-Exit fuer diesen Slice
    Skill(_PostBatch_PatternConformance,
          args="--scope slice --slice {slice} --batch {batch_current}")
    qg_state = lies PATTERN_CONFORMANCE_STATE aus _manifest.md
    IF qg_state.blocker_count > 0:
      IF GLOBAL_HIL == "off":
        Logge: "[Quick-Gate-8j] BLOCKER: {qg_state.blocker_count} Pattern-Verletzungen in Slice {slice}."
        Logge: "[Quick-Gate-8j] Auto-Apply-Modus — Apply war in _PostBatch_PatternConformance Schritt 3."
        IF qg_state.apply_happened:
          Logge: "[Quick-Gate-8j] Apply ausgefuehrt → erneuter 8h-Execute-Check noetig."
          result = spawne_worker(slice, "_TDD_execute", N, tdd_iteration, expected="GREEN")
          # Bei FAIL: naechste tdd_iteration
      ELSE:
        Logge: "[Quick-Gate-8j] BLOCKER mit HiL=on gemeldet (Report in _PostBatch_PatternConformance)."

    # Nach 8j quick gate — gold_reached-Pruefung
    IF state.gold_reached:
      gold_reached = true
      Logge: "TDD S{N}/{slice}: GOLD REACHED nach {tdd_iteration} Iterationen."
    ELSE:
      IF tdd_iteration >= STUFEN_MAX_ITERATIONS[N][difficulty]:
        max_iter = STUFEN_MAX_ITERATIONS[N][difficulty]
        IF GLOBAL_HIL == "off":
          IF N <= 2:
            # Stufen 1-2: Auto-SKIP (analog Backtrack-Guard)
            Logge: "[AUTO-SKIP] S{N}/{slice}: MAX_ITER erschoepft ({tdd_iteration}/{max_iter}). Auto-SKIP."
            gold_reached = true  # Erzwungener Loop-Exit
            manifest.I_PIPELINE_STATE.worktrees[slice].tdd_status = "AUTO_SKIPPED"
          ELSE:
            # Stufen 3-5: Alarm-Mechanismus (RF-03, RF-04)
            trigger_alarm(
              grund="MAX_TDD_ITERATIONS erschoepft: {tdd_iteration}/{max_iter}",
              stuck_stage="MAX_ITER",
              recommendation="SC_ANALYSE"
            )
            manifest.I_PIPELINE_STATE.tdd_stage_result = {
              stufe: N, stufen_ergebnis: "STUCK",
              tdd_iterations_verbraucht: tdd_iteration,
              max_iterations_fuer_stufe: max_iter,
              stuck_grund: "MAX_TDD_ITERATIONS erschoepft",
              alarm_empfehlung: "SC_ANALYSE"
            }
            manifest.I_PIPELINE_STATE.phase = "POST_TDD"
            manifest.update()
            BREAK  # WHILE-Loop verlassen -> I pollt tdd_alarm
        ELSE:
          # HiL=on: Erweitertes AskUserQuestion mit 4 Optionen
          antwort = AskUserQuestion(
            "TDD S{N}/{slice}: {tdd_iteration}x ohne GOLD (max={max_iter}).\n"
            "[SC_ANALYSE] Alarm setzen -> SC-Analyse\n"
            "[SKIP_STUFE] Stufe ueberspringen\n"
            "[WEITER]     Weitere Iterationen erlauben\n"
            "[ABORT]      Pipeline stoppen"
          )
          SWITCH antwort:
            "SC_ANALYSE":
              trigger_alarm(grund="HiL: SC_ANALYSE", stuck_stage="MAX_ITER",
                recommendation="SC_ANALYSE")
              manifest.I_PIPELINE_STATE.phase = "POST_TDD"
              manifest.update()
              BREAK
            "SKIP_STUFE":
              trigger_alarm(grund="HiL: SKIP_STUFE", stuck_stage="MAX_ITER",
                recommendation="SKIP_STUFE")
              manifest.I_PIPELINE_STATE.phase = "POST_TDD"
              manifest.update()
              BREAK
            "WEITER":
              Logge: "HiL: Weiter nach MAX_ITER."
              # Loop laeuft weiter (kein BREAK)
            "ABORT":
              manifest.pipeline_mode = "SC_RECOVERY"
              manifest.I_PIPELINE_STATE.phase = "POST_TDD"
              manifest.update()
              BREAK

    manifest.I_PIPELINE_STATE.worktrees[slice].tdd_iteration = tdd_iteration

  manifest.I_PIPELINE_STATE.worktrees[slice].tdd_status = "GOLD_REACHED"
```

### Worker spawnen

```
# (Z3: RF-26, ProzessKorrektur P6 RF-20 Punkt 3) Team-Name-Ableitung:
# parent_team als Primaerquelle (robust gegen Team-Naming-Aenderungen)
# Fallback auf "sc-{NAME}" wenn parent_team fehlt (Rueckwaertskompatibilitaet)
worker_mode = manifest.I_PIPELINE_STATE.worker_mode OR false
parent_team = manifest.I_PIPELINE_STATE.parent_team OR null
team_prefix = IF parent_team: parent_team ELIF worker_mode: "sc-{NAME}" ELSE: "i-pipeline-{NAME}"

# ═══════════════════════════════════════════════════════════════════════
# PFLASTER 2026-04-20 — COMMAND_MODEL_MAP (zentrale Modell-Zuordnung)
# ═══════════════════════════════════════════════════════════════════════
# Verteilung nach Komplexitaets-Analyse (BL-125 AK-6 Session-Review):
#   - opus   (4):  Architektur-Reasoning, tiefe Refactoring-Abstraktion
#   - sonnet (13): Worker-Standard (Code, Check, Analyse)
#   - haiku  (5):  Mechanische Ausfuehrung (Bash, Git, Checklist)
# Quelle: Komplexitaets-Tabelle 2026-04-20 (User-genehmigt).
# ═══════════════════════════════════════════════════════════════════════
COMMAND_MODEL_MAP = {
  # opus — Architektur & tiefe Abstraktion
  "_I_blueprintArchitect":  {subagent: "general-sonnet",   model: "opus"},
  "_I_cleanCodeArchitect":  {subagent: "general-sonnet",   model: "opus"},
  "_I_codeFullSystem":      {subagent: "general-sonnet",   model: "opus"},
  "_TDD_refactorCode":      {subagent: "general-sonnet",   model: "opus"},

  # sonnet — Worker-Standard (User-Override 2026-04-20: KEIN Haiku mehr)
  # Begruendung: Haiku halluzinierte Bash-Outputs bei _TDD_execute
  # (generierte Fake-Timestamps ohne echten Test-Run). Vertrauens-Verlust.
  # Ex-haiku-Commands: _TDD_execute, _TDD_check, _TDD_init, _I_mitose, _I_fanOut
  "DEFAULT":                {subagent: "general-sonnet", model: "sonnet"},
}

def resolve_agent_type(command):
  mapping = COMMAND_MODEL_MAP.get(command, COMMAND_MODEL_MAP["DEFAULT"])
  # Model-Cap-Check: session_params.ceiling ist Obergrenze
  ceiling = session_params.ceiling OR "opus"
  IF model_rank(mapping.model) > model_rank(ceiling):
    Logge: "[MODEL-CAP] {command} wollte {mapping.model}, Ceiling={ceiling} — downgrade"
    mapping = {subagent: "general-{ceiling}", model: ceiling}
  return mapping

def spawne_worker(slice, command, stufe, iteration, expected=null):
  # MLG S3 Log-Doppel (2026-04-24): 4-Stufen-Resolver vor COMMAND_MODEL_MAP
  # resolve() kaskadiert: Welle-Schema → Session-Cap → Command-Override → Spawn
  r = resolve(command=command, wave="seq", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
  mapping = resolve_agent_type(command)  # Fallback/Override-Wrapper — bleibt erhalten (rueckwaertskompatibel)
  # Wenn resolve() eine engere Aussage liefert, gewinnt r (4-Stufen-Kette)
  subagent = r.subagent_type OR mapping.subagent
  model    = r.model          OR mapping.model
  worker_name = "{team_prefix}-{slice}-{command}-i{iteration}"

  # PFLICHT-LOG: Transparenz pro Spawn (User sieht IMMER Model)
  # [SPAWN]-Top mit worker= (S2-Watchdog matched Top↔Bottom via worker-Name)
  Logge: "[SPAWN] worker={worker_name} type={subagent} model={model} cmd={command} wave=seq"

  task_id = TaskCreate(subject="[S{stufe}/{slice}] {command} i{iteration}")
  Agent(
    name=worker_name,
    subagent_type=subagent,   # general-haiku | general-sonnet | general-opus
    model=model,              # haiku | sonnet | opus (explizit, NICHT null)
    prompt=KURZLEBIG_PROMPT(slice, command, stufe, iteration, expected, task_id)
  )
  warte_auf_completion(task_id)
  IF command == "_TDD_execute":
    return lese_tdd_state(slice, stufe)
```

**KURZLEBIG_PROMPT:** Gleiche Vorlage wie in `_I_orchestrate` Phase 2.
**Schritt-0 Erweiterung (MLG S3 Log-Doppel, 2026-04-24):** Die KURZLEBIG_PROMPT-Vorlage in `_I_orchestrate` enthaelt am Anfang den INTRO-LOG-Block:
```
=== INTRO-LOG (Schritt 0, PFLICHT) ===
[AGENT] worker={AGENT_NAME} | model={MODEL} | type={SUBAGENT_TYPE} | task={TASK_SUMMARY}
```
Der Watchdog (S2) matcht `worker={name}` gegen den `[SPAWN]`-Top-Log. Muss in `_I_orchestrate` vorhanden sein (Pflaster-Check: es ist).

---

## Alarm-Hilfsfunktionen (E3)

```
FUNKTION trigger_alarm(grund, stuck_stage, recommendation):
  # Stufen-Differenzierung: WARN bei N<=3, CRIT bei N>=4
  severity = IF N >= 4: "CRIT" ELSE: "WARN"

  manifest.I_PIPELINE_STATE.tdd_alarm = {
    triggered:      true,
    stufe:          N,
    slice_id:       slice,
    severity:       severity,
    grund:          grund,
    stuck_stage:    stuck_stage,
    tdd_iteration:  tdd_iteration,
    recommendation: recommendation
  }
  manifest.update()
  Logge: "[TDD-ALARM] S{N}/{slice}: {stuck_stage} -> {recommendation} (severity={severity})"
```

```
FUNKTION tdd_pipeline_mode_wechsel(aktuell, neu, stufe, grund):
  VALID_TDD_TRANSITIONS = {
    "I":             ["I_TDD_PREP", "I_TDD_SKIPPED"],
    "I_TDD_PREP":    ["I_TDD_ACTIVE"],
    "I_TDD_ACTIVE":  ["I_TDD_DONE", "I_TDD_ABORTED"],
    "I_TDD_DONE":    ["I", "I_TDD_ALARM"],
    "I_TDD_ABORTED": ["I", "I_TDD_ALARM"],
    "I_TDD_ALARM":   ["I"],
    "I_TDD_SKIPPED": ["I"]
  }
  IF neu NOT IN VALID_TDD_TRANSITIONS.get(aktuell, []):
    Logge WARNUNG: "[TDD-STATE-MACHINE] Ungueltiger Uebergang: {aktuell} -> {neu}"
    IF GLOBAL_HIL != "off":
      HiL: "Ungueltiger TDD-State-Uebergang. [IGNORIEREN] [ABORT]"
    ELSE:
      RETURN false
  manifest.I_PIPELINE_STATE.tdd_pipeline_mode = neu
  manifest.I_PIPELINE_STATE.tdd_transition_log APPEND:
    { from_mode: aktuell, to_mode: neu, stufe: stufe, timestamp: jetzt(), grund: grund }
  manifest.update()
  Logge: "[TDD-STATE] {aktuell} -> {neu} (Stufe {stufe}): {grund}"
  RETURN true
```

---

## Schritt 9: Verify pro Slice

```
HiL: "Stufe {N} TDD-Zyklus abgeschlossen. Bitte volle Test-Suite ausfuehren."

FOR EACH slice IN slices:
  spawne_worker(slice, "verify", N, 1)
warte_bis_alle_completed(slices, "verify")
→ Manifest: stufen_status.verify: done
```

---

## Schritt 10: fanIn (sequentiell)

```
# fanIn NUR bei Worktree-Modus (slicing=true UND Multi-Slice)
worktree_parallel = manifest.I_PIPELINE_STATE.worktree_parallel ?? (slicing == true)

IF worktree_parallel == true AND len(slices) > 1:
  HiL: "Verify abgeschlossen. Bitte in ALLEN Worktrees committen."

  FOR EACH slice IN slices:
    spawne_worker(slice, "fanIn", N, 1)
    warte_auf_completion()  # Sequentiell (Merge-Konflikte vermeiden)
  → Manifest: stufen_status.fanIn: done
ELIF worktree_parallel == false:
  Logge: "slicing=false: SKIP fanIn — Slices bereits im gleichen Branch"
  → Manifest: stufen_status.fanIn: skipped
ELSE:
  Logge: "Single-Slice: SKIP fanIn"
```

---

## Schritt 11: Stufen-QG (Kanarienvogel)

```
AUSGABE: "Stufe {N} Fan-In abgeschlossen. Stufen-QG:"

IF GLOBAL_HIL == "off":
  # Auto-Pfad: Worker fuehrt Kanarienvogel-Tests aus
  qg_task_id = TaskCreate(subject="[S{N}] Stufen-QG Kanarienvogel HiL=off")
  # PFLASTER 2026-04-20: Stufen-QG = _I_verify-Logik → sonnet (Worker-Standard)
  # MLG S3 Log-Doppel (2026-04-24): resolve() + worker=-Feld im [SPAWN]-Log
  r = resolve(command="_I_verify", wave="seq", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
  qg_mapping = resolve_agent_type("_I_verify")
  qg_subagent = r.subagent_type OR qg_mapping.subagent
  qg_model    = r.model          OR qg_mapping.model
  qg_worker   = "{team_prefix}-stufen-qg-s{N}"
  Logge: "[SPAWN] worker={qg_worker} type={qg_subagent} model={qg_model} cmd=_I_verify wave=seq"
  Agent(
    name=qg_worker,
    subagent_type=qg_subagent,
    model=qg_model,
    prompt=KURZLEBIG_PROMPT(
      command="verify",
      stufe=N, task_id=qg_task_id,
      extra="Fuehre Kanarienvogel-Tests aus (testbefehl aus TDD_INSTRUCTIONS.md).\n"
            "Pruefe: Alle bestehenden Tests GRUEN? Gesamt-Build OK?\n"
            "Schreibe Ergebnis PASS oder FAIL in TDD-STATE.md Feld kanarienvogel_qg_result.\n"
            "KEIN Code schreiben — NUR ausfuehren und berichten."
    )
  )
  warte_auf_completion(qg_task_id)
  qg_state = lese_tdd_state(aktive_slices[0], N)
  kanarienvogel_result = qg_state.kanarienvogel_qg_result OR "FAIL"  # Safe default

  IF kanarienvogel_result == "PASS":
    Logge: "[AUTO-QG] S{N}: Kanarienvogel PASS -> Stufe abschliessen."
    manifest.I_PIPELINE_STATE.impl_test_stages[N].kanarienvogel_status = "PASS"

  ELSE:  # FAIL
    manifest.I_PIPELINE_STATE.impl_test_stages[N].kanarienvogel_status = "FAIL"
    Logge: "[AUTO-QG] S{N}: Kanarienvogel FAIL -> Kaskade starten."

    # Kaskade automatisch ausfuehren (Stufe A->B->C)
    kaskade_result = fuehre_kaskade_aus(N)

    IF kaskade_result == "erschoepft":
      trigger_alarm(
        grund="Stufen-QG FAIL + Kaskade A->B->C erschoepft",
        stuck_stage="STUFEN_QG",
        recommendation="SC_ANALYSE" IF N < 5 ELSE "ABORT"
      )
      manifest.I_PIPELINE_STATE.tdd_stage_result = {
        stufe: N, stufen_ergebnis: "STUCK",
        stuck_grund: "Stufen-QG: Kanarienvogel FAIL nach Kaskade",
        alarm_empfehlung: "SC_ANALYSE" IF N < 5 ELSE "ABORT"
      }
      manifest.I_PIPELINE_STATE.phase = "POST_TDD"
      manifest.update()
      RETURN  # Kein "Stufe abschliessen" — I pollt tdd_alarm

ELSE:  # HiL=on: Unveraendertes Verhalten
  AUSGABE: "  1. Kanarienvogel-Tests ausfuehren (read-only)"
  AUSGABE: "  2. Gesamt-Build pruefen"
  AUSGABE: "  3. Ergebnis: PASS / FAIL"

  ergebnis = AskUserQuestion("Stufen-QG Stufe {N}: PASS/FAIL?")
  IF ergebnis == "FAIL":
    manifest.I_PIPELINE_STATE.impl_test_stages[N].kanarienvogel_status = "FAIL"
    → Lies {META}/implementation/kanarienvogel-kaskade.md
    → Fuehre Eskalationskaskade aus (Stufe A → B → C)
  ELSE:
    manifest.I_PIPELINE_STATE.impl_test_stages[N].kanarienvogel_status = "PASS"
```

### fuehre_kaskade_aus() Hilfsfunktion (E3, RF-05)

```
FUNKTION fuehre_kaskade_aus(N):
  kaskade = lies_kanarienvogel_kaskade_md()
  IF kaskade == null:
    Logge WARNUNG: "[KASKADE] kanarienvogel-kaskade.md nicht gefunden -> erschoepft."
    RETURN "erschoepft"
  FOR stufe_label IN ["A", "B", "C"]:
    kaskade_task = TaskCreate(subject="[S{N}] Kaskade {stufe_label} HiL=off")
    # PFLASTER 2026-04-20: Kaskade = Worker-Check → sonnet (Default)
    # MLG S3 Log-Doppel (2026-04-24): resolve() + worker=
    r = resolve(command="DEFAULT", wave="seq", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
    kask_mapping = resolve_agent_type("DEFAULT")  # sonnet
    kask_subagent = r.subagent_type OR kask_mapping.subagent
    kask_model    = r.model          OR kask_mapping.model
    kask_worker   = "{team_prefix}-kaskade-{stufe_label}-s{N}"
    Logge: "[SPAWN] worker={kask_worker} type={kask_subagent} model={kask_model} cmd=kaskade-{stufe_label} wave=seq"
    Agent(name=kask_worker,
      subagent_type=kask_subagent,
      model=kask_model,
      prompt=KURZLEBIG_PROMPT(command="kaskade", stufe=N, task_id=kaskade_task,
        extra=kaskade.stufen[stufe_label].beschreibung))
    warte_auf_completion(kaskade_task)
    state = lese_tdd_state(aktive_slices[0], N)
    IF state.kanarienvogel_qg_result == "PASS":
      Logge: "[KASKADE] S{N}: Kaskade {stufe_label} -> PASS."
      RETURN "gerettet"
    ELSE:
      Logge: "[KASKADE] S{N}: Kaskade {stufe_label} -> weiter FAIL."
  RETURN "erschoepft"
```

---

## I→SC Return Check

Nach jedem Batch-Zyklus: Pruefe ob fundamentale SC-Probleme vorliegen.

```
→ Lies {META}/implementation/i-sc-return.md
→ Pruefe T1-T4 Trigger
→ Falls any_trigger: Pipeline STOPP, Manifest: pipeline_mode = "SC_RECOVERY"
```

---

## Stufe abschliessen

```
# Nur wenn Kanarienvogel PASS:

# exit_criteria Pruefung (Slice 2 Δ6, TestStufen Fix — AK12/AK13)
# Pruefe stage_N.exit_criteria aus stage-Metadaten (falls definiert)
stage_metadaten = lade_stage_n(N)
exit_criteria = stage_metadaten.exit_criteria ?? {}

# stufen_tests_gruen: Alle Stufen-Tests fuer Stage N sind GRUEN
stufen_tests_gruen = true
IF "stufen_tests_gruen" IN exit_criteria:
  stufen_tests_gruen = (impl_test_stages[N].kanarienvogel_status == "PASS")
  IF NOT stufen_tests_gruen:
    Logge WARNUNG: "[EXIT-CRITERIA] stufen_tests_gruen FAIL fuer Stufe {N}."

# fan_in_merge: fanIn wurde erfolgreich abgeschlossen
fan_in_merge = true
IF "fan_in_merge" IN exit_criteria:
  fan_in_merge = (manifest.I_PIPELINE_STATE.stufen_status.fanIn IN ["done", "skipped"])
  IF NOT fan_in_merge:
    Logge WARNUNG: "[EXIT-CRITERIA] fan_in_merge FAIL fuer Stufe {N}."

IF NOT (stufen_tests_gruen AND fan_in_merge):
  Logge WARNUNG: "[EXIT-CRITERIA] Stufe {N}: exit_criteria nicht erfuellt. Status: PARTIAL statt DONE."
  manifest.I_PIPELINE_STATE.impl_test_stages[N].status = "partial"
ELSE:
  manifest.I_PIPELINE_STATE.impl_test_stages[N].status = "done"

manifest.I_PIPELINE_STATE.impl_test_stages[N].completed_at = jetzt()
manifest.I_PIPELINE_STATE.last_stage_completed = N
manifest.update()
```

### TDD_PIPELINE_STATE Rollover Sub-Schritt (Pattern B, W18)

Nach Stufe N abschliessen (nach Kanarienvogel PASS):

```
1. Lies _manifest.md: Suche impl_test_stages-Eintraege mit status="done" aelter als N-2
   Falls >= 3 abgeschlossene TDD-Stufen vorhanden:

2. Frontmatter _manifest_protokoll.md aktualisieren:
   last_append: {Datum}
   append_count: {N+1}

3. Prepend nach YAML-Frontmatter in _manifest_protokoll.md:
   ## TDD_orchestrate [{Datum}] S{N}
   - stage: S{N}
   - slices: {aktive_slices}
   - tdd_iterations: {max_iterations_across_slices}
   - gold_reached: {Slices die GOLD erreicht haben}
   - completed_at: {completed_at}

4. Entferne archivierten Eintrag aus _manifest.md
   (nur der N-2 Lauf wird rotiert, aktuelle impl_test_stages bleiben)
```

---

## Nach Stufe N: Uebergabe zurueck an I_orchestrate

```
# TDD hat Stufe N abgeschlossen → Kontrolle zurueck an I_orchestrate
# I_orchestrate entscheidet ob Blueprint N+1 → TDD N+1 oder POST_PIPELINE

tdd_alarm_aktiv = manifest.I_PIPELINE_STATE.tdd_alarm.triggered OR false

IF NOT tdd_alarm_aktiv:
  # Normaler PASS-Pfad
  manifest.I_PIPELINE_STATE.phase = "POST_TDD"
  manifest.I_PIPELINE_STATE.tdd_stage_result = {
    stufe: N,
    stufen_ergebnis: "PASS",
    tdd_iterations_verbraucht: tdd_iteration,
    max_iterations_fuer_stufe: STUFEN_MAX_ITERATIONS[N][difficulty],
    rings_completed: [abgeschlossene_ringe],
    testbefehl_ausgefuehrt: TDD_INSTRUCTIONS.testbefehl,
    mock_modus: TDD_INSTRUCTIONS.mock_scope,
    completed_at: jetzt_iso8601(),
    stuck_grund: null,
    alarm_empfehlung: null
  }
  manifest.I_PIPELINE_STATE.impl_test_stages[N].status = "done"
  manifest.I_PIPELINE_STATE.impl_test_stages[N].completed_at = jetzt()
  manifest.I_PIPELINE_STATE.last_stage_completed = N
ELSE:
  # STUCK-Pfad (tdd_alarm + tdd_stage_result bereits von trigger_alarm gesetzt)
  Logge: "[TDD] S{N}: Stufe STUCK — tdd_alarm aktiv."

manifest.update()
AUSGABE: "TDD Stufe {N} abgeschlossen. Kontrolle zurueck an _I_orchestrate."

# ═══ SDF-HUB RUECKKEHR (Hub-Invariante #8 — ersetzt PLAYBOOK-RUECKKEHR) ═══
#
# ANTI-PATTERN: Skill("_I_orchestrate") direkt ← VERBOTEN (Hub-Invariante)
# Alle Orchestrator-Transitionen MUESSEN durch SDF (Heilige Trinitaet).
#
# RICHTIG: TDD setzt phase=POST_TDD und RETURN → SDF routet zurueck zu I.
# SDF erkennt phase=POST_TDD und ruft I_orchestrate fuer R1-R4:
#   R1: Manifest neu laden
#   R2: tdd_pipeline_mode pruefen
#   R3: tdd_alarm + tdd_stage_result konsumieren
#   R4: Zuruecksetzen + STAGE-TRANSITION (/_stage_orchestrate + naechste Stufe)
#
# BEI HiL=off: SDF + I_orchestrate laufen autonom.

manifest.I_PIPELINE_STATE.phase = "POST_TDD"
manifest.update()
Logge: "[SDF-HUB] TDD S{N} DONE → Kontrolle zurueck an SDF (Hub-Invariante)."
RETURN  # TDD endet — SDF liest phase=POST_TDD, ruft I fuer R1-R4, dann Stage-Progression.
```

---

## Resume-Logik (Crash-Recovery)

```
Bei Neustart (innerhalb einer Stufe):
  1. Lies I_PIPELINE_STATE aus Manifest
  2. N = current_stage (von I_orchestrate gesetzt)
  3. Innerhalb Stufe N: stufen_status.{command} == "done" → skip
  4. TDD-Iteration aus worktrees[slice].tdd_iteration lesen
```
