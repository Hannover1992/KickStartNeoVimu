# /_crown — Worker-Watchdog mit Estimated-Duration + Cron-Wachhund

```yaml
status: active
version: 1.0.0
created: 2026-05-12
op: SubCommand
phase: Watchdog
type: building-block
model_tier: haiku
chain_position: parallel
feature_anchor: BL-NEW-48
related:
  - _I_orchestrate
  - _SDF_orchestrate
  - _TDD_red
  - _TDD_green
  - _TDD_refactorCode
  - _TDD_refactorTests
  - _TDD_check
```

---

## Zweck

**Doppelter Done-Check fuer Worker-Spawns.**

Team Lead spawnt einen Worker und ist danach "blind" bis der Worker via `SendMessage`
zurueckmeldet. In der Praxis stallt das System wenn:
- Worker crasht ohne Notification
- Worker laeuft in Token-Limit
- Worker macht Mega-Agent-Skip (BL-NEW-45) und meldet falsch DONE
- Worker meldet sich nie zurueck (Heartbeat fehlt)
- Build-Failure mit silent abort

`/_crown` setzt einen **passiven Cron-Wachhund** der nach geschaetzter Dauer + Puffer
selbststaendig prueft, ob der Worker tatsaechlich done ist. Doppel-Check:

```
   ┌─────────────────────────────────────────────────────────────────┐
   │                                                                 │
   │   Worker spawnt                                                 │
   │       │                                                         │
   │       ├── PFAD A: Worker meldet selbst DONE → SendMessage        │
   │       │           Team Lead bekommt Heartbeat, Cron wird         │
   │       │           geloescht via CronDelete                       │
   │       │                                                         │
   │       └── PFAD B: Cron feuert nach estimated_duration + 50%     │
   │                   Crown prueft passiv (audit.jsonl + State)     │
   │                   - DONE bestaetigt? → Cleanup                   │
   │                   - STUCK? → Eskalation (Re-Spawn / HiL / ABORT) │
   │                   - PROGRESS? → Neuer Cron mit kleinerem Delta  │
   │                                                                 │
   └─────────────────────────────────────────────────────────────────┘
```

---

## Aufruf

```
/_crown <worker_name> <skill_name> [--model={haiku|sonnet|opus}]
        [--scope-loc={N}] [--scope-tests={N}] [--build-needed={true|false}]
        [--integration={true|false}] [--buffer-pct={50}]
        [--max-rechecks={3}] [--escalation={auto|hil|abort}]

Pflicht:
  <worker_name>   Name des kurzlebigen Worker-Agents (z.B. "i-tddrefactor-pl1-s1-v2")
  <skill_name>    Skill den der Worker laden soll (z.B. "_TDD_refactorCode")

Optional:
  --model          Worker-Modell (default: aus Skill-Frontmatter ableiten)
  --scope-loc      Geschaetzter LOC-Output des Workers (Scope-Multiplier)
  --scope-tests    Geschaetzte Test-Anzahl (Test-Faktor)
  --build-needed   Muss Worker dotnet build ausfuehren? (+2-5 min Buffer)
  --integration    Integration-Tests (Docker/DB)? (+1-3 min Buffer)
  --buffer-pct     Buffer-Prozent auf Estimated Duration (default 50)
  --max-rechecks   Maximale Re-Check-Iterationen vor ABORT (default 3)
  --escalation     Eskalations-Mode bei STUCK (default auto)

Beispiele:

  /_crown i-tddrefactor-pl1-s1-v2 _TDD_refactorCode --model=opus --scope-loc=70 --buffer-pct=50

  /_crown i-tddcheck-pl1-s1 _TDD_check --model=sonnet --buffer-pct=30 --max-rechecks=2

  /_crown i-pattern-batch3-w1 _I_patternLibrary --model=sonnet --scope-loc=0 --escalation=hil
```

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_crown                                                    ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {WORKING_DIR}/_manifest.md                                        ║
║      .CROWN_STATE                              (active_watchdogs[])  ║
║      I_PIPELINE_STATE / DF_BATCH_STATE         (Worker-Kontext)      ║
║    {WORKTREE_PATH}/.claude/TDD-STATE.md        (Worker-Heartbeat)    ║
║    {VAULT}/audit.jsonl                         (SKILL_LOAD events)   ║
║    .claude/commands/{skill_name}.md            (Skill-Metadaten)     ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {WORKING_DIR}/_manifest.md                                        ║
║      .CROWN_STATE.active_watchdogs[]           (cron_id, expected)   ║
║      .CROWN_STATE.history[]                    (Lauf-Historie)       ║
║      audit.jsonl                                (CROWN_*Events)      ║
║    Bei Eskalation:                                                   ║
║      {VAULT}/Backlog/{slug}/6_PL/{bl_id}-parking-lot.md (PL-Append)  ║
║                                                                      ║
║  RUFT:                                                               ║
║    CronCreate(...)         (one-shot, nach estimated + buffer)       ║
║    CronDelete(...)         (bei Worker-Self-Report DONE)             ║
║    SendMessage(to=worker)  (optional Heartbeat-Probe)                ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    INV-CROWN-1: Jeder Watchdog hat eindeutige cron_id im Manifest    ║
║    INV-CROWN-2: Bei Worker-DONE: CronDelete + audit DONE-Event       ║
║    INV-CROWN-3: Bei max_rechecks erreicht: zwingend Eskalation       ║
║                  (Eskalation = HiL-Alert + PL-Append + ABORT)        ║
║    INV-CROWN-4: Read-Only auf Worker-State (kein Patch durch Crown)  ║
║    INV-CROWN-5: Re-Spawn nur via Skill(...)-Load (INV-PM-2),         ║
║                  NIEMALS Agent(general-sonnet, prompt=AUFTRAG)       ║
║                  → Crown's Re-Spawn-Template enforced INV-WORKER-    ║
║                  SKILL-LOAD (BL-NEW-45)                              ║
║    INV-CROWN-6: Crown selbst spawnt KEIN Code/Test/Build —           ║
║                  reines Lifecycle-Monitoring                          ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## SCHRITT 1: PRE-SCHAETZUNG — Pi-mal-Daumen Duration

### 1.0 MODEL-VALIDATION (PFLICHT, BL-NEW-51, 2026-05-12)

```
# Vor JEDEM Estimated-Duration-Lookup:
# Pruefe ob das gewuenschte Modell fuer den Skill erlaubt ist.

forbidden_models = parse Skill-Frontmatter → forbidden_models ?? []

IF model IN forbidden_models:
  Logge: "[CROWN-ABORT] BL-NEW-51 violation — {skill_name} darf NICHT mit {model} gespawned werden"
  audit_jsonl_append({
    type: "BL_NEW_51_VIOLATION",
    skill: skill_name,
    requested_model: model,
    forbidden_models: forbidden_models,
    worker: worker_name,
    timestamp: ISO
  })
  SendMessage an team-lead:
    "ABORT Crown-Arm fuer {worker_name}: BL-NEW-51 — {skill_name} verbietet model={model}. Erlaubt: {non_forbidden_models}. Re-Spawn mit hoeherem Tier."
  EXIT FAIL.

# Spezifischer Anti-Haiku-Block fuer TDD-Zyklus:
IF skill_name IN {_TDD_init, _TDD_red, _TDD_green, _TDD_refactorCode,
                  _TDD_refactorTests, _TDD_check, _TDD_execute}:
  IF model == "haiku":
    Logge: "[CROWN-ABORT] BL-NEW-51 — TDD-Zyklus verbietet haiku (zu komplexe Sequenzen wie Docker-spinup, Polling, Test-Capture, Pattern-Konsultation). Mindest-Tier: sonnet."
    audit_jsonl_append({
      type: "BL_NEW_51_TDD_HAIKU_VIOLATION",
      skill: skill_name,
      worker: worker_name,
      live_case_anchor: "i-tddexec-pl1-s3-verify_2026-05-12_stuck_10min_Docker_spinup",
      timestamp: ISO
    })
    EXIT FAIL.
```

**BL-NEW-51 — Lehre (Projekt-agnostisch, Case-Anchor in `.claude/_parking-lot.md`):**
- TDD-Skills mit mehrstufigen Test-Sequenzen (Container-spinup + Polling + Test-Capture + Log-Parse + Teardown) sind fuer Haiku zu komplex — Worker verlaeuft sich in der Sequenz, stuckt ohne Output, meldet falsch infrastructure-issue.
- **Root Cause:** Haiku-Modell hat begrenzte Konsistenz bei mehrstufigen Befehls-Befolgungen mit Polling/Timeout/Recovery.
- **Fix:** TDD-Skills bekommen `forbidden_models: [haiku]` im Frontmatter. Crown SCHRITT 1.0 blockiert vor-Spawn — Mindest-Tier sonnet.

---

### 1.1 Base-Duration aus Skill-Tabelle

```
ESTIMATED_DURATION_TABLE (Minuten, Median-Range, Pi-mal-Daumen):

┌────────────────────────┬──────────┬───────────┬───────────┬────────────────────┐
│ Skill                  │ haiku    │ sonnet    │ opus      │ Notes              │
├────────────────────────┼──────────┼───────────┼───────────┼────────────────────┤
│ _TDD_init              │ VERBOTEN │ 1-2       │ —         │ BL-NEW-51 Anti-Haiku│
│ _TDD_setup Stage 1     │ VERBOTEN │ 0-1       │ —         │ BL-NEW-53, oft SKIP │
│ _TDD_setup Stage 3     │ VERBOTEN │ 1-3       │ —         │ docker info + build │
│ _TDD_setup Stage 6     │ VERBOTEN │ 5-15      │ —         │ docker-up + WebHost │
│ _TDD_teardown          │ VERBOTEN │ 1-3       │ —         │ BL-NEW-53 best-effort│
│ _TDD_red               │ VERBOTEN │ 3-5       │ 5-7       │ BL-NEW-51 Anti-Haiku│
│ _TDD_execute           │ VERBOTEN │ 2-4       │ —         │ BL-NEW-51 + Docker  │
│ _TDD_green             │ VERBOTEN │ 4-6       │ 6-10      │ BL-NEW-51 Anti-Haiku│
│ _TDD_refactorCode      │ VERBOTEN │ —         │ 7-12      │ BL-NEW-51 + Opus    │
│ _TDD_refactorTests     │ VERBOTEN │ 4-7       │ 5-8       │ BL-NEW-51 Anti-Haiku│
│ _TDD_check             │ VERBOTEN │ 2-3       │ —         │ BL-NEW-51 Anti-Haiku│
├────────────────────────┼──────────┼───────────┼───────────┼────────────────────┤
│ _I_blueprintArchitect  │ —        │ 6-10      │ 8-15      │ Wellen 5-3-1       │
│ _I_requirementCheck    │ —        │ 3-5       │ —         │ AK-Coverage        │
│ _I_patternLibrary      │ —        │ 3-5       │ —         │ Pattern-Lookup     │
│ _I_architecturalLibrary│ —        │ 3-5       │ —         │ Arch-Layer-Check   │
│ _I_testSearch          │ —        │ 4-6       │ —         │ Test-Inventar      │
│ _I_goldDefine          │ —        │ 4-7       │ 5-8       │ Akzeptanzkriterien │
│ _I_blueprintQG         │ —        │ 2-4       │ —         │ QG 7/7             │
│ _I_cleanCodeSlice      │ —        │ 5-10      │ 7-12      │ Slice-Erstellung   │
│ _I_mitose              │ —        │ 1-2       │ —         │ Fan-Out-Setup      │
│ _I_fanIn               │ —        │ 4-7       │ —         │ Slice-Konsolid.    │
│ _I_verify              │ —        │ 3-5       │ —         │ Slice-Verify       │
├────────────────────────┼──────────┼───────────┼───────────┼────────────────────┤
│ _SC_observe            │ —        │ —         │ 5-10      │ W2 Drafter         │
│ _SC_modelMaintain      │ —        │ —         │ 5-10      │ W3 Synthesizer     │
│ _SC_hypothese          │ —        │ —         │ 3-6       │ Hypothese          │
│ _SC_implement          │ —        │ —         │ 5-15      │ FULL/INLINE        │
├────────────────────────┼──────────┼───────────┼───────────┼────────────────────┤
│ _A_berater_*           │ 2-5      │ 3-6       │ —         │ Meist Haiku/Sonnet │
│ _IDF_berater_*         │ 2-5      │ 3-6       │ —         │ Meist Haiku/Sonnet │
│ _SDF_berater_*         │ 1-3      │ 2-4       │ —         │ Meist Haiku        │
└────────────────────────┴──────────┴───────────┴───────────┴────────────────────┘

Lookup:
  base_min, base_max = TABLE[skill_name][model]
  IF nicht gefunden:
    base_min = 3, base_max = 8 (Default Sonnet)
  estimated_base = (base_min + base_max) / 2
```

### 1.2 Scope-Multiplikatoren

```
scope_loc_factor:
  LOC < 50:        1.0x
  LOC 50-200:      1.3x
  LOC > 200:       1.6x
  unknown:         1.2x

scope_tests_factor:
  tests < 5:       1.0x
  tests 5-15:      1.2x
  tests > 15:      1.5x
  unknown:         1.1x

build_factor:
  build_needed=true:    +2 min
  integration=true:     +3 min (Docker spinup)
  beide:                +5 min
  none:                 0 min

context_factor (basierend auf I_PIPELINE_STATE.aktuelle_stufe):
  Stufe 1 (Unit):       1.0x
  Stufe 3 (Integration): 1.3x (Setup-Overhead)
  Stufe 6 (E2E):        1.5x (volle Vertikale)
```

### 1.3 Finale Estimated Duration

```
estimated_minutes = (
    estimated_base
  * scope_loc_factor
  * scope_tests_factor
  * context_factor
  + build_factor
)

cron_delay_minutes = estimated_minutes * (1 + buffer_pct/100)

# Minimum: 3 min (sonst feuert Cron bevor Worker richtig startet)
# Maximum: 30 min (sonst zu spaet)
cron_delay_minutes = clamp(cron_delay_minutes, 3, 30)
```

---

## SCHRITT 2: CRON-WACHHUND ARMIEREN

```
# 2.1 Berechne Fire-Time (lokal, off-:00 / off-:30 zur Lastverteilung)
now = aktuelle Zeit
fire_time = now + cron_delay_minutes
fire_minute = fire_time.minute
# Jitter: vermeide :00, :15, :30, :45 (Spike-Marker)
IF fire_minute IN [0, 15, 30, 45]:
  fire_minute = fire_minute + 3 (oder -3 wenn am Stunden-Ende)

cron_expr = "{fire_minute} {fire_hour} {fire_day} {fire_month} *"

# 2.2 CronCreate
cron_prompt = f"""
/_crown_check {worker_name} {skill_name}
  expected_done_by={fire_time.isoformat()}
  recheck_count=0
  max_rechecks={max_rechecks}
  escalation={escalation}
"""

cron_id = CronCreate(
  cron=cron_expr,
  prompt=cron_prompt,
  recurring=false   # one-shot — feuert einmal nach delay
)

# 2.3 Manifest-Eintrag
Manifest patch:
  CROWN_STATE:
    active_watchdogs:
      - worker: {worker_name}
        skill: {skill_name}
        spawned_at: {now.isoformat()}
        estimated_done: {fire_time.isoformat()}
        cron_id: {cron_id}
        recheck_count: 0
        max_rechecks: {max_rechecks}
        escalation: {escalation}
        scope: {loc, tests, build_needed, integration}

# 2.4 audit.jsonl Event
audit_jsonl_append({
  type: "CROWN_ARMED",
  worker: worker_name,
  skill: skill_name,
  estimated_minutes: estimated_minutes,
  cron_delay_minutes: cron_delay_minutes,
  cron_id: cron_id,
  timestamp: now.isoformat()
})

# 2.5 Logge
"[CROWN-ARMED] Worker={worker_name} Skill={skill_name} Estimated={estimated_minutes}min Buffer=50% Cron-Fires={fire_time}"
```

---

## SCHRITT 3: WORKER-SELF-REPORT (PFAD A — Happy Path)

```
# Wenn Worker via SendMessage DONE meldet:
Team Lead Empfaengt: SendMessage(to=team-lead, message="DONE: {result}")

Team Lead ruft:
  Skill(_crown_resolve, args="{worker_name} {worker_result}")

ODER inline (wenn Team Lead nicht _crown_resolve laden will):
  CROWN_STATE.active_watchdogs → finde entry mit worker_name
  CronDelete(id=entry.cron_id)
  Manifest patch:
    CROWN_STATE.active_watchdogs: remove entry
    CROWN_STATE.history.append({
      worker, skill, spawned, completed, outcome: "WORKER_SELF_REPORT_DONE",
      duration_actual: completed - spawned
    })
  audit_jsonl_append({
    type: "CROWN_DISARMED",
    worker, cron_id, reason: "worker_self_reported_done",
    actual_duration_min: ..., estimated_duration_min: ...,
    accuracy_pct: actual / estimated * 100
  })
  Logge: "[CROWN-DISARMED] {worker_name} self-reported DONE in {actual}min (estimated {estimated}min, accuracy {pct}%)"
```

---

## SCHRITT 4: CRON-FIRE — Passive Check (PFAD B)

Wenn Cron feuert (Worker hat sich nicht selbst gemeldet), wird Team Lead getriggert
mit dem `cron_prompt`. Team Lead laedt:

```
Skill(_crown_check, args="{worker_name} {skill_name} expected_done_by={X} recheck_count={N} max_rechecks={M} escalation={...}")
```

ODER (wenn `/_crown_check` als separates Skill noch nicht existiert): Team Lead
fuehrt inline diese Check-Logik aus.

### 4.1 Worker-Status ermitteln (4 Quellen — Multi-Source-of-Truth)

```
# Quelle 1: audit.jsonl seit Spawn
events = grep audit.jsonl WHERE worker == worker_name AND timestamp >= spawned_at
status_audit = analyze(events):
  IF events enthaelt {type: "SKILL_EXIT", status: "DONE"}: AUDIT_DONE
  IF events enthaelt {type: "BUILD_FAIL"}: AUDIT_BUILD_FAIL
  IF events enthaelt {type: "TOKEN_LIMIT"}: AUDIT_TOKEN_LIMIT
  IF events enthaelt {type: "BL_NEW_45_VIOLATION"}: AUDIT_MEGA_AGENT
  IF events enthaelt {type: "SKILL_LOAD"} aber kein SKILL_EXIT: AUDIT_IN_PROGRESS
  IF |events| == 0: AUDIT_SILENT

# Quelle 2: TDD-STATE.md (worktree-local)
tdd_state = lies {WORKTREE_PATH}/.claude/TDD-STATE.md
status_tdd = tdd_state.state ?? "UNKNOWN"
  ("GREEN_VERIFIED" | "RED_VERIFIED" | "REFACTOR_CODE_DONE" | "GOLD_REACHED" | ...)
  ODER bei Crash: "SKILL_LOAD_VIOLATION" | "PATTERN_DISCOVERY_FAILED"

# Quelle 3: Manifest I_PIPELINE_STATE / DF_BATCH_STATE
status_manifest = manifest.I_PIPELINE_STATE.last_stage_completed VS current_stage
                  + handschuh_wechsel_pending Flag

# Quelle 4: Worker-Heartbeat-Probe (optional)
# NUR wenn audit zeigt SILENT — probe ob Worker noch lebt
IF status_audit == AUDIT_SILENT:
  TRY:
    SendMessage(to=worker_name, message="HEARTBEAT_PROBE: are you alive?")
    WAIT 30s for response
    IF response == "alive": status_heartbeat = ALIVE
    ELSE: status_heartbeat = DEAD
  EXCEPT (worker not found / no response):
    status_heartbeat = DEAD

# Konsolidierung (4 Quellen → 1 Verdict)
worker_verdict = decide(status_audit, status_tdd, status_manifest, status_heartbeat)
```

### 4.2 Entscheidungsmatrix

```
┌─────────────────┬──────────────────┬─────────────────┬──────────────────────┐
│ status_audit    │ status_tdd       │ Verdict          │ Action               │
├─────────────────┼──────────────────┼─────────────────┼──────────────────────┤
│ AUDIT_DONE      │ GREEN_VERIFIED   │ DONE             │ Disarm Cron + Cleanup│
│ AUDIT_DONE      │ GOLD_REACHED     │ DONE             │ Disarm Cron + Cleanup│
│ AUDIT_IN_PROGRESS │ UNKNOWN/active │ PROGRESS         │ Re-Cron (kleineres Δ)│
│ AUDIT_SILENT    │ UNKNOWN          │ STUCK_SILENT     │ Heartbeat-Probe      │
│                 │                  │  → DEAD          │ Eskalation Re-Spawn  │
│ AUDIT_BUILD_FAIL│ —                │ STUCK_BUILD_FAIL │ Eskalation: Build-Fix│
│ AUDIT_TOKEN_LIMIT│ —               │ STUCK_TOKEN      │ Eskalation: Re-Spawn │
│                 │                  │                  │   mit kleinerem Scope│
│ AUDIT_MEGA_AGENT│ SKILL_LOAD_VIOL  │ STUCK_BL_NEW_45  │ Eskalation: Re-Spawn │
│                 │                  │                  │   mit Skill-Load     │
│ —               │ PATTERN_DISC_FAIL│ STUCK_BL_NEW_46  │ Eskalation: Patterns │
│                 │                  │                  │   manuell beistellen │
└─────────────────┴──────────────────┴─────────────────┴──────────────────────┘
```

### 4.3 Decision-Actions

```
DECIDE_DONE:
  CronDelete(active_watchdogs[worker].cron_id)
  Manifest:
    CROWN_STATE.active_watchdogs: remove
    CROWN_STATE.history.append({outcome: "PASSIVE_CHECK_DONE", actual_duration_min})
  audit: CROWN_DISARMED reason="passive_check_done"
  Logge: "[CROWN-DISARMED] Passive Check confirmed DONE for {worker_name}"
  RETURN

DECIDE_PROGRESS:
  recheck_count += 1
  IF recheck_count >= max_rechecks:
    GOTO DECIDE_STUCK (mit reason="max_rechecks_progress_but_not_done")
  ELSE:
    # Neuer Cron mit kleinerem Delta (50% des ursprünglichen)
    new_delay = ursprueng_delay * 0.5
    new_cron_id = CronCreate(cron="...", prompt=re-trigger, recurring=false)
    Manifest patch: active_watchdogs[worker].cron_id = new_cron_id
                     active_watchdogs[worker].recheck_count = recheck_count
    audit: CROWN_RE_ARMED
    Logge: "[CROWN-RE-ARMED] Worker in PROGRESS — Re-Check in {new_delay}min ({recheck_count}/{max_rechecks})"
    RETURN

DECIDE_STUCK_BL_NEW_45:
  # Re-Spawn mit korrekt geladenem Skill
  Schreibe Eskalations-Hint in Manifest:
    CROWN_STATE.history.append({outcome: "ESCALATED_BL_NEW_45", recurrence: ...})
  audit: CROWN_ESCALATION reason="bl_new_45_mega_agent"
  Logge: "[CROWN-ESCALATION] Worker {worker_name} hat Skill nicht geladen — Re-Spawn empfohlen"
  Re-Spawn-Prompt (Lead muss ausfuehren):
    ┌────────────────────────────────────────────────────────────────────┐
    │  ZEILE 1: Skill({skill_name}, args="{slice} {stage} {iteration}")  │
    │  ZEILE 2+: KURZLEBIG_PROMPT:                                       │
    │    polier_kontext: {recovered from Manifest oder Self-Discovery}    │
    │    PFAD-KONTEXT: ...                                                │
    │    GREEN-STATE / RED-STATE: {recovered}                              │
    │    HINWEIS: Vorheriger Worker hat Skill nicht geladen — STRIKT      │
    │             Skill-Vertrag befolgen (BL-NEW-45/46).                   │
    └────────────────────────────────────────────────────────────────────┘
  IF escalation == "auto":
    Team Lead spawnt automatisch Re-Worker mit korrektem Prompt
    new_worker_name = worker_name + "-v" + str(int(suffix)+1)
    /_crown {new_worker_name} {skill_name} {modified_params}   # neuer Wachhund
  IF escalation == "hil":
    SendMessage(to=user) mit Eskalations-Bericht
  IF escalation == "abort":
    Manifest: CROWN_STATE.aborted=true, PL-Item append

DECIDE_STUCK_BUILD_FAIL:
  # Lese letzten Build-Error aus audit.jsonl
  build_error = events WHERE type=BUILD_FAIL → letzter
  audit: CROWN_ESCALATION reason="build_fail"
  Logge: "[CROWN-ESCALATION] Build-Failure detected: {build_error.summary}"
  Re-Spawn-Prompt mit Build-Error als KURZLEBIG_PROMPT-Anhang:
    "BUILD-ERROR (vom Vorgaenger): {build_error}
     Fixe diesen Fehler vor Refactor/Test."

DECIDE_STUCK_TOKEN_LIMIT:
  # Scope verkleinern
  new_scope = halve(scope_loc, scope_tests)
  audit: CROWN_ESCALATION reason="token_limit"
  Logge: "[CROWN-ESCALATION] Token-Limit hit — Re-Spawn mit Scope/2"
  Re-Spawn mit kleinerem Scope (z.B. nur 1 Ring statt 4)

DECIDE_STUCK_SILENT_DEAD:
  # Worker antwortet nicht auf Heartbeat → Crash
  IF recheck_count < max_rechecks:
    Re-Spawn mit gleichem Auftrag
    Logge: "[CROWN-ESCALATION] Worker silent/dead — Re-Spawn ({recheck_count}/{max_rechecks})"
  ELSE:
    HiL-Alert + PL-Append
    Logge: "[CROWN-ABORT] {worker_name} silent nach {max_rechecks} Re-Tries — HiL eskaliert"

DECIDE_STUCK_BL_NEW_46:
  # Pattern-Discovery hat gefailed
  audit: CROWN_ESCALATION reason="pattern_discovery_failed"
  HiL-Alert (Lead muss manuell polier_kontext beistellen):
    "{worker_name} hat keine Patterns in PatternLibrary/SemanticLibrary fuer {sub_batch_id}/{stage} gefunden.
     Optionen:
       (A) Patterns manuell beistellen (Lead waehlt aus sub-{NR}.md)
       (B) sub-{NR}.md erweitern (Pattern-Zuweisung nachtragen)
       (C) Refactor SKIP (akzeptiere weniger generischen Code)"
```

---

## SCHRITT 5: ESKALATIONS-PROTOKOLLE

### 5.1 Schief-Geht-Strategien (Decision-Baum)

```
                       ┌──────────────────────────┐
                       │  Cron feuert nach Δt + 50%│
                       └────────────┬──────────────┘
                                    │
                ┌───────────────────┴───────────────────┐
                │                                       │
        ┌───────▼────────┐                     ┌────────▼────────┐
        │ Worker DONE?   │                     │ Worker IDLE?     │
        │ (audit + tdd)  │                     │ (kein audit-Event│
        └───────┬────────┘                     │  seit X min)     │
                │                              └────────┬────────┘
        YES     │     NO                                │
                │                                       │
   ┌────────────▼──┐  ┌────────────────┐       ┌───────▼──────────┐
   │ Disarm Cron   │  │ Was sagt audit?│       │ Heartbeat-Probe   │
   │ + audit DONE  │  └───────┬────────┘       │ via SendMessage    │
   │ + Cleanup     │          │                 └────────┬──────────┘
   └───────────────┘          │                          │
                              │                  ALIVE   │   DEAD
                              ▼                          │
                  ┌───────────────────────┐              ▼
                  │ BUILD_FAIL? TOKEN?    │     ┌────────────────┐
                  │ BL_NEW_45? BL_NEW_46? │     │ Re-Spawn       │
                  └───────┬───────────────┘     │ (gleicher Auftr│
                          │                     │  aber Heartbeat│
            ┌─────────────┼─────────────┐       │  -Logging an)  │
            │     │       │       │     │       └────────────────┘
            ▼     ▼       ▼       ▼     ▼
        BUILD  TOKEN  BL-NEW-45 BL-NEW-46 PROGRESS
            │     │       │       │     │
            ▼     ▼       ▼       ▼     ▼
     ┌─────────┐ ┌───┐ ┌──────┐ ┌────┐ ┌────────┐
     │ Re-Spawn│ │R-S│ │Re-S  │ │HiL │ │ Re-Cron│
     │ mit     │ │Sm-│ │mit   │ │mit │ │ Δt*0.5 │
     │ Build-  │ │all│ │korr. │ │Pat.│ │        │
     │ Error   │ │er │ │Skill │ │-Inf│ │        │
     │ Context │ │Sc.│ │-Load │ │o   │ │        │
     └─────────┘ └───┘ └──────┘ └────┘ └────────┘
```

### 5.2 Re-Spawn-Template (BL-NEW-45-konform, PFLICHT)

Egal warum re-spawned wird — der neue Worker-Prompt MUSS dem WORKER-PROMPT-TEMPLATE
aus `_I_orchestrate.md` INV-WORKER-SKILL-LOAD folgen:

```
ZEILE 1 (PFLICHT):
  Skill({skill_name}, args="{slice} {stage} {iteration}")

ZEILE 2+: KURZLEBIG_PROMPT (Worker-Kontext-Anhang):
  polier_kontext: { matched_patterns, matched_semantics }
  PFAD-KONTEXT: worktree, vault, BLUEPRINT_BASE
  GREEN-STATE / RED-STATE: {recovered aus Manifest oder TDD-STATE}
  AUFTRAG-DETAIL: {step-spezifisch}
  RE-SPAWN-HINWEIS: "Vorheriger Worker {original_name} hat {reason} —
                    befolge Skill-Vertrag STRIKT (SCHRITT 0.0..7)."
```

### 5.3 HiL-Alert-Format (bei max_rechecks erschoepft)

```
SendMessage(to=user) bzw. AskUserQuestion(...):
  ┌────────────────────────────────────────────────────────────────────┐
  │ [CROWN-HIL-ALERT] Worker-Watchdog erschoepft                       │
  │                                                                    │
  │ Worker:        {worker_name}                                       │
  │ Skill:         {skill_name}                                        │
  │ Spawned at:    {spawned_at}                                        │
  │ Estimated:     {estimated_minutes} min                              │
  │ Actual:        {now - spawned_at} min (Estimated × {ratio})        │
  │ Recheck-Iter:  {recheck_count} / {max_rechecks}                    │
  │ Verdict:       {STUCK_REASON}                                       │
  │                                                                    │
  │ Audit-Events:  {summary, letzte 5}                                  │
  │ TDD-STATE:     {state}                                              │
  │                                                                    │
  │ Optionen:                                                          │
  │   (A) Re-Spawn manuell (Lead waehlt korrigierten Prompt)            │
  │   (B) ABORT — Sub-Batch markieren als FAILED, weiter mit naechstem │
  │   (C) Pause Pipeline — User analysiert root cause                   │
  │   (D) Patterns beistellen (bei BL-NEW-46)                          │
  │                                                                    │
  │ Empfehlung: {auto-Heuristik basierend auf STUCK_REASON}             │
  └────────────────────────────────────────────────────────────────────┘

ZEITGLEICH:
  PL-Append (BL-Folder 6_PL/{bl_id}-parking-lot.md):
    - [ ] CROWN-INCIDENT-{ISO}: {worker_name} stuck nach {N} Re-Tries
      Reason: {STUCK_REASON}
      audit-Events: {Liste}
      Empfehlung: {auto-Heuristik}
```

---

## SCHRITT 6: HISTORIE + LERNEFFEKT

Nach jedem CROWN-Lauf (DONE oder ESCALATED) wird ein Eintrag in
`CROWN_STATE.history[]` geschrieben. Daraus laesst sich:

1. **Estimated-Duration-Tabelle kalibrieren** (post-mortem):
   ```
   actual_duration_avg per skill+model = mean(history WHERE skill, model)
   estimated_accuracy_pct = actual / estimated * 100
   IF accuracy < 70% oder > 130%: Tabelle anpassen
   ```

2. **Eskalations-Recurrence detecten**:
   ```
   IF 3+ ESCALATIONS pro Tag mit gleichem reason: BL-Item erstellen
   ```

3. **Worker-Performance-Metrik**:
   ```
   success_rate per skill = DONE / (DONE + ESCALATED)
   skills mit <80% success_rate: review BL-Item
   ```

---

## INVARIANTEN

- **INV-CROWN-1:** Jeder Watchdog hat eindeutige `cron_id` im Manifest unter
                  `CROWN_STATE.active_watchdogs[]`. Doppelte cron_ids = Bug.
- **INV-CROWN-2:** Bei Worker-Self-Report DONE → CronDelete + Cleanup zwingend.
                   Sonst sammeln sich Zombie-Crons.
- **INV-CROWN-3:** Bei `max_rechecks` erreicht → zwingend Eskalation (HiL-Alert +
                   PL-Append). KEIN stilles Stoppen.
- **INV-CROWN-4:** Read-Only auf Worker-State — Crown patcht NICHT TDD-STATE oder
                   Worker-Code. Nur Manifest.CROWN_STATE + audit.jsonl.
- **INV-CROWN-5:** Re-Spawn nur via Skill(...)-Load (INV-PM-2 + INV-WORKER-SKILL-LOAD
                   BL-NEW-45). NIEMALS `Agent(general-sonnet, prompt="AUFTRAG...")`
                   ohne Skill-Praefix.
- **INV-CROWN-6:** Crown spawnt KEIN Code/Test/Build — reines Monitoring.
                   Code-Worker werden ausserhalb Crown gespawnt (von I-orchestrate/
                   TDD-Skills).
- **INV-CROWN-7:** `recurring=false` fuer alle Crown-CronJobs (one-shot). Re-Cron
                   bei PROGRESS = neuer CronCreate-Call, alter wird automatisch
                   ge-cleanup.
- **INV-CROWN-8:** Maximale `cron_delay_minutes` = 30 min. Bei laengeren Workern
                   muss Crown mehrfach re-checken statt 1× nach 60 min.

---

## BEISPIELE

### Beispiel 1: Step 14 _TDD_refactorCode mit Opus

```
Team Lead nach Spawn:
  Skill(_crown, args="i-tddrefactor-pl1-s1-v2 _TDD_refactorCode --model=opus --scope-loc=70 --buffer-pct=50")

Crown:
  Base-Duration: opus _TDD_refactorCode = 7-12 min → 9.5 min
  Scope-LOC 70: 1.3x → 12.35 min
  Context Stage 1: 1.0x → 12.35 min
  Build: 0 min
  estimated_minutes = 12.35
  cron_delay_minutes = 12.35 * 1.5 = 18.5 → clamp(3, 30) = 18.5 min

  CronCreate(
    cron="33 13 12 5 *",   # 13:33 today (off-marker)
    prompt="/_crown_check i-tddrefactor-pl1-s1-v2 _TDD_refactorCode expected_done_by=2026-05-12T13:33:00",
    recurring=false
  ) → cron_id=42abc

  Manifest: CROWN_STATE.active_watchdogs.append({...})
  audit: CROWN_ARMED
  Logge: "[CROWN-ARMED] i-tddrefactor-pl1-s1-v2 _TDD_refactorCode Estimated=12.4min Cron-Fires=13:33"
```

### Beispiel 2: Step 18 _TDD_check mit Sonnet (schneller)

```
Skill(_crown, args="i-tddcheck-pl1-s1 _TDD_check --model=sonnet --buffer-pct=30 --max-rechecks=2")

Crown:
  Base-Duration: sonnet _TDD_check = 2-3 min → 2.5 min
  Scope = 0 (kein Code, nur Verify): 1.0x → 2.5 min
  estimated_minutes = 2.5
  cron_delay_minutes = 2.5 * 1.3 = 3.25 → clamp(3, 30) = 3.25 min

  CronCreate fires in ~3 min.
```

### Beispiel 3: Eskalations-Fall — Worker silent

```
Cron feuert nach 18 min fuer i-tddrefactor-pl1-s1-v2:
  audit.jsonl: nur SKILL_LOAD-Event, kein SKILL_EXIT
  TDD-STATE.md: state=REFACTOR_CODE_IN_PROGRESS, last_update=14min ago
  → AUDIT_SILENT + TDD-STATE stale

  Heartbeat-Probe:
    SendMessage(to="i-tddrefactor-pl1-s1-v2", "HEARTBEAT_PROBE")
    Wait 30s → no response

  Verdict: STUCK_SILENT_DEAD
  Action: Re-Spawn (recheck_count 1/3)

  Lead spawnt {worker_name}-v{N+1} mit Re-Spawn-Template
  Crown re-armed fuer den neuen Worker
```

---

## TODO / Folge-Patches

- [ ] `/_crown_check` als separates Skill (aktuell inline in cron_prompt)
- [ ] `/_crown_resolve` fuer schnelle Worker-Self-Report-Verarbeitung
- [ ] Estimated-Duration-Tabelle aus `CROWN_STATE.history[]` automatisch kalibrieren
       (Schedule: weekly via CronCreate recurring)
- [ ] Integration mit `_sanity_check_post`: Crown-Eskalationen werden im
       Post-Report aufgefuehrt
- [ ] BL-Item: `/_crown_dashboard` — Live-Uebersicht aller aktiven Watchdogs
       (CronList + Manifest-Read)
- [ ] BL-Item: Anomaly-Detection — wenn 3+ Eskalationen mit gleichem reason in 24h
       → automatisches BL-Item-Creation

---

## Verwandte Patterns

- **Watchdog-Pattern (Embedded Systems):** Hardware-Timer der zurueckgesetzt wird
  vom Programm — wenn Timer ablaeuft, Programm gilt als gestuerzt. Crown ist die
  Software-Variante mit Cron + audit.jsonl als "Heartbeat".

- **Circuit Breaker (Resilience Patterns):** Nach N Fehlern oeffnet sich der
  Kreislauf, weitere Calls werden direkt abgebrochen. Crown's `max_rechecks` ist
  vergleichbar — nach N Re-Tries Eskalation statt blindes Re-Spawn.

- **Liveness vs Safety:** Crown garantiert **Liveness** (Pipeline staut nicht ewig)
  zu Lasten eventueller False-Positives (Worker wird als stuck eingestuft obwohl
  er noch arbeitet). Buffer-Prozent (default 50%) ist der Trade-Off-Hebel.

---

## BL-NEW-48 — Crown-Watchdog-Pattern (2026-05-12)

**Symptom:** Lead spawnt Worker und ist danach "blind" — wartet auf SendMessage.
Wenn Worker crasht ohne Notification, stalled System unbegrenzt. User muss manuell
checken (kostet Aufmerksamkeit + bricht Forrest-Run-Mode).

**Fix:** `/_crown`-Command etabliert Doppel-Check via CronJob nach Pi-mal-Daumen-
Estimated-Duration. Worker-Self-Report (SendMessage) bleibt Happy-Path, Cron-
Passive-Check ist Fallback. Bei Stall → automatische Eskalation (Re-Spawn / HiL).

**User-Direktive 2026-05-12:** "der eam lead er versucht zu schaetzen wie lange der
comadn pi mal duam dauenr wird, und [nach] der ge[shaetzten] zeti dara er zu werde
um zu shc ob der worke wirlkch done ist, wiel gena oft sie ver ihn ien nahc zu
sende das das yste stalled — aber so jabe wri dopplte chek"

**Status:** Initial-Skill DEPLOYED 2026-05-12.
