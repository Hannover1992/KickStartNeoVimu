---
status: active
version: 1.0.0
created: 2026-04-26
op: ImplementationPipeline
phase: 1
type: berater
chain_position: middle
model_tier: middle
---

# /_I_berater_teamSetup (Phase 1 — Team-Setup fuer I-Pipeline)

[VERTRAG]
LIEST:
  - {WORKING_DIR}/_manifest.md (NAME, PHASE, I_PIPELINE_STATE) — per-Story (BL-155 AK-1)
  - {VAULT}/_manifest.md (SCHWIERIGKEIT, BDF_PIPELINE_STATE) — global
  - {VAULT}/Task.md
  - {VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md
  - {VAULT}/Backlog/{BL_SLUG}/5_Gap/{NAME}-GAP.md (optional)
  - {VAULT}/Backlog/{BL_SLUG}/SC/{NAME}-HANDOFF.md (optional, BL-151 + PL-D Decision 2026-05-07)
  - {META}/implementation/guards.md
  - {META}/implementation/handoff-protocol.md
  - .claude/meta/implementation/stage_1..5.md (optional)
  - .claude/_session_params.md ($ARGUMENTS.mode, pipeline_mode, GLOBAL_HIL)
  - .claude/merge-instructions/{NAME}-idd-context.md (optional, PARKED)

SCHREIBT:
  - {WORKING_DIR}/_manifest.md → I_PIPELINE_STATE (init/resume) — per-Story (BL-155 AK-1)
  - {VAULT}/_manifest.md → BDF_PIPELINE_STATE.active_team (Standalone) — global
  - {WORKING_DIR}/output/I_DryRun_{NAME}_{Datum}.md (nur bei dryRun)

BERATER_OUTPUTS.teamSetup:
  worker_mode: bool
  team_name: string
  puppet_master_active: bool
  scope_mode: "full"
  rag_collection: string
  handoff_consumed: bool
  handoff_context: object | null
  model_read_verified: bool
  i_dry_run_done: bool  # nur bei dryRun-Modus

CROSS-REFERENCES:
  - Phase 2 (_I_orchestrate PHASE 2: KURZLEBIG_PROMPT) konsumiert BERATER_OUTPUTS.teamSetup
  - SC-Symbiose-Pfad: pipeline_mode == "SC_SYMBIOSE_I_ACTIVE" setzt worker_mode=true
  - /_W_fetch wird in Schritt 1.3 aufgerufen
  - handoff-protocol.md Schritte 0.4a-0.4g werden in Schritt 1.5 ausgefuehrt
[/VERTRAG]

[INVARIANTEN]
- KEIN Agent wird gespawnt bevor HARD GATE (1.8) bestanden ist
- TeamCreate schlaegt fehl → STOPP (kein Workaround)
- Model < 50 Zeilen → STOPP
- scope_mode ist IMMER "full" (BL-054)
- Im worker_mode wird SC-Team wiederverwendet, KEIN eigenes Team
[/INVARIANTEN]

---

## PHASE 1: TEAM SETUP

### 0.5 Dry-Run Short-Circuit (BL-091, Universal_Dry_Run_Pattern)

```
# BL-091: I-Pipeline Dry-Run-Modus (6. Child)
# Vorgaenger: BL-082 BDF, BL-087 SDF, BL-088 IDF, BL-089 A, BL-090 SC
i_mode = $ARGUMENTS.mode ?? _session_params.mode ?? "normal"

IF i_mode == "dryRun":
  Logge: "[BL-091 I DRY-RUN] Mock-Modus — Blueprint/Architect/Code-Pipeline skipped"

  i_dry_run_report = {
    date: {Datum},
    feature: NAME,
    mode: "dryRun",
    would_run: [
      # V14 (2026-05-08): _I_blueprintArchitect deprecated (replaced by _I_patternLibrary).
      "Blueprint-Phase: /_I_cleanCodeArchitect, /_I_patternLibrary, /_I_blueprintQG",
      "Gold-Phase: /_I_goldDefine, /_I_requirementCheck",
      "Code-Phasen: /_I_codeAtomic, /_I_codeSystem, /_I_codeFullSystem",
      "Verify-Phase: /_I_verify, /_I_testSearch"
    ],
    skipped: true,
    note: "I-Pipeline mit ~10 Sub-Commands, keine Code-Aenderungen im dryRun-Modus"
  }

  i_dry_run_report_path = ".claude/output/I_DryRun_{NAME}_{Datum}.md"
  Schreibe {i_dry_run_report_path} mit i_dry_run_report Inhalt

  Schreibe in {WORKING_DIR}/_manifest.md → I_PIPELINE_STATE:
    name: NAME
    modus: dryRun
    phase: DRY_RUN_DONE
    mock_report: {i_dry_run_report_path}

  Logge: "[BL-091 I DRY-RUN] Mock-Completion — Report: {i_dry_run_report_path}"
  BERATER_OUTPUTS.teamSetup.i_dry_run_done = true
  → Return zu Aufrufer
```

### 1.0 Team erstellen (ERSTER SCHRITT — VOR ALLEM ANDEREN)

```
# Phase 1.0a: Worker-Mode-Detektion (RF-19, W244) # (Z2: RF-19)
IF --worker-mode Flag gesetzt ODER pipeline_mode == "SC_SYMBIOSE_I_ACTIVE":
  worker_mode = true
  team_name = "sc-{NAME}"  # SC-Team uebernehmen, kein eigenes Team
  Logge: "Worker-Mode aktiv. Team: sc-{NAME}. TeamCreate SKIP."
  → SKIP TeamCreate (SC-Team bereits vorhanden)
ELSE:
  worker_mode = false
  TeamCreate: team_name="i-pipeline-{NAME}"

# BL-060 T4: active_team mit Amnestie (RF-06, AK-06, INV-BL060-4)
# I-Pipeline hat Stage-basierte Worker (1 pro Stufe), KEIN Wellen-Pattern.
# wellen_tracking_enabled: false → L1/L2 Guards skippen — Amnestie.
IF NOT worker_mode:  # nur Standalone, nicht im SC-Symbiose-Pfad
  Schreibe in {VAULT}/_manifest.md → BDF_PIPELINE_STATE.active_team:
    name: "i-{NAME}"
    created_at: {ISO-8601 jetzt}
    pipeline: "i"
    wellen_tracking_enabled: false

# Puppet Master Erweiterung (nach Worker-Mode-Detektion) # (PM: Puppet-Master-Pattern)
IF worker_mode == true UND GLOBAL_HIL == "off":
  puppet_master_active = true
  Logge: "Puppet-Master-Modus: Sequentielle Worker, keine HiL-Pausen."
  # Alle HiL-Checkpoints in der I-Pipeline werden SKIP
  # Worker arbeiten autonom durch Blueprint → Impl → TDD → Verify

BERATER_OUTPUTS.teamSetup.worker_mode = worker_mode
BERATER_OUTPUTS.teamSetup.team_name = team_name
BERATER_OUTPUTS.teamSetup.puppet_master_active = puppet_master_active ?? false
```

Ohne Team kann KEIN Agent kommunizieren. Im Worker-Mode wird das SC-Team wiederverwendet.
Falls TeamCreate fehlschlaegt (Standalone) → STOPP (kein Workaround).

### 1.1 Kontext laden

1. Lies `{VAULT}/_manifest.md` → NAME, SCHWIERIGKEIT (global); lies `{WORKING_DIR}/_manifest.md` → I_PIPELINE_STATE.PHASE (per-Story, BL-155 AK-1)
2. Lies `{VAULT}/Task.md` → existiert? Sonst STOPP
3. Lies `{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md` → existiert? Sonst STOPP
   # --- MODEL-READ-GUARD (RF-PA-004, W31, W45) ---
   # Existenz allein ist NICHT hinreichend. Read-Nachweis PFLICHT.
   model_content = Read("{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md")
   IF model_content.lines < 50:
     STOPP: "Model existiert aber ist zu kurz (<50 Zeilen) — unvollstaendig."
   model_read_verified = true
   Logge: "[G-MODEL-READ] Model {NAME} gelesen ({model_content.lines} Zeilen). Enforcement OK."
   # Guard-Ergebnis wird im Worker-Prompt als Pflicht-Kontext weitergegeben:
   # Worker erhaelt model_summary (TC-Uebersicht + relevante W{n}) als Teil des Task-Prompts
   BERATER_OUTPUTS.teamSetup.model_read_verified = true
4. Bestimme WORKTREE_PATH (Parameter oder cwd)
5. **[PARKED: IDD-Kontext]** Lies `.claude/merge-instructions/{NAME}-idd-context.md` (falls vorhanden)
   - Falls vorhanden: IDD-Modus aktiv → Mock-Boundary-Constraints fuer Blueprint-Phase verfuegbar
   - Falls nicht vorhanden: SKIP (kein Fehler)
   - **PARKED:** Vollstaendige IDD-Unterstuetzung (`--parent-pr`-Weitergabe, automatisches Slice-Routing
     fuer Interface-Mocks) wartet auf `/_sliceInit`-Implementierung (RF-SC-002, ENTFERNT per
     PL-Review 2026-03-23). Sobald `/_sliceInit` implementiert: PARKED aufloesen,
     `--parent-pr {branch}` als Parameter zu `/_I_orchestrate` hinzufuegen.

### 1.2 Guards ausfuehren

→ Lies `{META}/implementation/guards.md` und fuehre aus:
  1. G-SESSION-INIT (Stale-Task-Cleanup)
  2. G-DARK-FACTORY-READY (nur bei HiL=off aus _session_params.md)
  3. SC-Status pruefen (sc_status aus Manifest)
  4. pipeline_mode State Machine (READY_FOR_I / SC_SYMBIOSE / etc.)

```
# (Z5: RF-04, W191) GAP-Check als LOG-Warnung (kein hartes Gate):
IF worker_mode == false:  # Nur bei I-STANDALONE, nicht im SYMBIOSE Worker-Mode
  lies .claude/analysis/synthese/{NAME}-GAP.md (falls vorhanden):
    gap_score = lies gap_score aus GAP.md Frontmatter (oder 0 wenn nicht vorhanden)
    IF gap_score > 15:
      Logge WARNUNG: "[I-STANDALONE] GAP-Score {gap_score}% > 15% — Empfehlung: Erst SC-Zyklen abschliessen."
      # KEIN STOPP — reine LOG-Warnung (SOLL, kein MUSS)
    ELSE IF gap_score != 0:
      Logge: "[I-STANDALONE] GAP-Score {gap_score}% <= 15% — OK"
    ELSE:
      Logge: "[I-STANDALONE] GAP-Datei nicht vorhanden — GAP-Check SKIP"
```

### 1.2a Scope-Mode-Erkennung (RF-23, W245, BL-054) # (Z2: RF-23)

```
# Scope-Mode (BL-054: IMMER full)

1. I_PIPELINE_STATE.scope_mode existiert (Resume-Fall) → scope_mode = "full"
   # BL-054: IMMER full, auch bei Resume (alter Wert ignoriert)
   Logge: "Scope-Mode: full (Resume — override auf full, BL-054)"

2. Default → scope_mode = "full"
   Logge: "Scope-Mode: full (Default)"

Schreibe in {WORKING_DIR}/_manifest.md → I_PIPELINE_STATE.scope_mode = scope_mode
BERATER_OUTPUTS.teamSetup.scope_mode = "full"
```

### 1.3 W_fetch (bestehendes Wissen holen)

```
Collection = "i_knowledge_{feature_id}" oder "local_knowledge_{feature_id}"
Falls Collection existiert UND nicht leer:
  → /_W_fetch {NAME} ausfuehren
  → Ergebnis in KURZLEBIG_PROMPT als KONTEXT-Block
Falls KEINE Collection: SKIP (Graceful Degradation)
Schreibe in {WORKING_DIR}/_manifest.md → I_PIPELINE_STATE.w_fetch = "DONE" | "SKIP"
```

### 1.4 RAG Collection Init

```
feature_id = sanitize(NAME)  # lowercase, _ statt Sonderzeichen
mcp__cleancodermcp__create_collection(name="i_knowledge_{feature_id}")
Schreibe in {WORKING_DIR}/_manifest.md → I_PIPELINE_STATE.rag_collection = "i_knowledge_{feature_id}"
BERATER_OUTPUTS.teamSetup.rag_collection = "i_knowledge_{feature_id}"
```

### 1.5 HANDOFF-Konsumption

→ Lies `{META}/implementation/handoff-protocol.md` und fuehre Schritte 0.4a-0.4g aus.

→ Lies `{VAULT}/Backlog/{BL_SLUG}/SC/{NAME}-HANDOFF.md` (falls vorhanden, BL-007 + PL-D 2026-05-07).
  Dieses Dokument enthaelt die KONKRETEN SC-Zyklus-Ergebnisse (Hypothesen, Befunde, Entscheidungen).
  handoff-protocol.md beschreibt WIE der Handoff funktioniert (statisches Template).
  {NAME}-HANDOFF.md beschreibt WAS SC herausgefunden hat (konkretes Dokument).
  Falls {NAME}-HANDOFF.md nicht existiert: Logge Warnung, weiter ohne (graceful degradation).

```
Ergebnis: handoff_consumed=true/false, handoff_context im Manifest.
BERATER_OUTPUTS.teamSetup.handoff_consumed = handoff_consumed
BERATER_OUTPUTS.teamSetup.handoff_context = handoff_context | null
```

### 1.6 Manifest initialisieren

```
# Crash-Guard (W258): Bestehenden I_PIPELINE_STATE pruefen # (Z2: W258)
IF I_PIPELINE_STATE existiert UND I_PIPELINE_STATE.phase NOT IN ["done", "POST_PIPELINE"]:
  Logge WARNUNG: "Bestehender I_PIPELINE_STATE gefunden (Phase: {phase})."
  IF worker_mode == false:
    → HiL: "I-Pipeline-State existiert bereits (Phase: {phase}).
            [RESUME] Bestehenden State fortsetzen
            [RESET]  State zuruecksetzen (Verlust!)
            [ABORT]  Abbrechen"
  ELSE:
    Logge: "Worker-Mode: State ueberschreiben (SC kontrolliert Lifecycle)."
```

```yaml
I_PIPELINE_STATE:
  start: "{YYYY-MM-DD HH:MM}"
  scope_mode: "full"  # BL-054: IMMER full
  phase: "BLUEPRINT"
  aktuelle_stufe: 1
  stufen_status: {blueprint_phase: pending, tdd: pending, verify: pending, fanIn: pending}
  blueprint_retry_count: 0
  resume_zaehler: {}
  worktrees: {}
  impl_test_stages:
    1: {status: pending}
    2: {status: pending}
    3: {status: pending}
    4: {status: pending}
    5: {status: pending}
  current_stage: 1
  last_stage_completed: 0
  handschuh_wechsel_pending: false
  worker_mode: false
  tdd_stage_result:
    stage: null
    iterations: null
    gold_reached: []
    overall_status: null
```

### 1.7 Stufen-Metadaten laden

```
Falls .claude/meta/implementation/stage_1.md existiert → Stufen-Modus aktivieren
Lade stage_1..5.md, validiere Pflichtfelder
IF stage_N.md hat status != "placeholder" UND testbefehl == "TBD":
  → HiL: "Stufe {N} ist aktiv aber testbefehl=TBD. Framework konfigurieren oder SKIP?"
  → Falls SKIP: impl_test_stages[N].status = "skipped"
```

### 1.7a zone_advisory Wiring (BL-330 AK-3)

> **advisory_only — NIEMALS bindend.** Der Berater emittiert einen Vorschlag, kein Kommando.
> Analog INV-MODUS-1: der Lead / Param-Owner entscheidet, nicht der Berater.

```
# BL-330 AK-3: zone_advisory-Emission (advisory_only=True, NICHT bindend)
# Zweck: Lead bekommt einen strukturierten Vehicle-Hinweis direkt aus der ZONE_REGISTRY,
# ohne dass der Berater den Vehicle-Entscheid vorwegnimmt.

from workflow_zones import zone_advisory  # .claude/scripts/workflow_zones.py

activity = "dispatch_implement"  # oder die konkrete Pipeline-Aktivitaet dieses Batches
mode = _session_params.workflow ?? "false"  # session_params_resolver Dial

advisory = zone_advisory(activity, mode=mode)
# Ergebnis-Shape:
#   advisory["zone"]               -> "green" | "yellow" | "red"
#   advisory["recommended_vehicle"]-> "workflow" | "advisory" | "worker"
#   advisory["motor_faehig"]       -> True NUR wenn recommended_vehicle=="workflow"
#   advisory["advisory_only"]      -> IMMER True (BL-330 AK-3 Invariante)
#   advisory["rationale"]          -> non-empty str (Erklaerung)

BERATER_OUTPUTS.teamSetup.zone_advisory = advisory
# Lead integriert in vehicle-Entscheidung — advisory_only=True, NICHT Auto-Routing.
Logge: "[BL-330] zone_advisory: zone={advisory['zone']} motor_faehig={advisory['motor_faehig']} advisory_only={advisory['advisory_only']}"
```

**Wichtig:** `advisory_only` ist strukturell `True` — der Berater empfiehlt, der Lead entscheidet
(INV-VEHIKEL-1: Vehicle-Entscheidung via `workflow_zones.py vehicle`-CLI durch den Lead).
Kein Auto-Routing aus dem Advisory heraus.

### 1.8 HARD GATE — Phase 1 Checkliste (PFLICHT vor Phase 2)

```
BEVOR du IRGENDEINEN Agent spawnst, pruefe:
[ ] Team "i-pipeline-{NAME}" existiert (Schritt 1.0)
[ ] Manifest I_PIPELINE_STATE geschrieben (Schritt 1.6)
[ ] Stufen-Metadaten geladen (Schritt 1.7)

ALLE 3 muessen TRUE sein. Sonst: STOPP.
Kein "Soll ich...?" — Einfach machen oder STOPP bei Fehler.
```
