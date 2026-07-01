---
status: active
version: 1.1.0
type: berater
parent: _SDF_orchestrate
phase: phase_2_2
model_tier: middle
created: 2026-05-10
updated: 2026-06-12
feature_anchor: BL-171
feature_anchor_extra: BL-323
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.last_stage_completed", purpose: "welche Stage hat I_orchestrate eben durchgefuehrt"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.phase", purpose: "Pipeline-End-Phase (HANDSCHUH_WECHSEL | POST_TDD_CONSUMED | POST_PIPELINE | PAUSED)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.handschuh_wechsel_pending", purpose: "Marker dass I_orchestrate sauber RETURN gemacht hat"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.impl_test_stages[N].status", purpose: "per-Stage Status (done | partial | failed)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.nachphase.verify_status", purpose: "global verify-Status (PASS | FAIL | PARTIAL) — optional, nur bei letzter Stage"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_stages[current_sub_batch_id]", purpose: "geplante Stages fuer aktuellen Sub-Batch"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.completed_stages_per_batch[current_sub_batch_id]", purpose: "bereits abgeschlossene Stages"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.current_sub_batch_id", purpose: "aktueller Sub-Batch-Key"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.current_stage", purpose: "Stage die eben durchgefuehrt wurde"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.stageElevation.retry_counts", purpose: "Retry-Counter pro Stage (vorheriger Lauf)"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.stageElevation", purpose: "Decision-Output: next_action + next_stage + rationale + retry_counts"}
optional: false
invariants:
  - "INV-STAGE-ELEV-1: Output MUSS next_action enthalten (ELEVATE | BATCH_DONE | RETRY | ABORT | HALT | DEFER)"
  - "INV-STAGE-ELEV-2: Bei next_action=ELEVATE MUSS next_stage in batch_stages[k] sein und NICHT in completed_stages_per_batch[k]"
  - "INV-STAGE-ELEV-3: Bei next_action=RETRY MUSS retry_counts[current_stage] < 2 (RETRY-Limit)"
  - "INV-STAGE-ELEV-4: Bei next_action=BATCH_DONE MUSS alle batch_stages[k] in completed_stages_per_batch[k] (modulo current_stage) sein"
  - "INV-STAGE-ELEV-5: Berater darf KEIN Skill() aufrufen (reiner Decision-Berater) — nur Read+Write Manifest"
  - "INV-STAGE-ELEV-6 (BL-323 AK-1): Bei next_action=DEFER MUSS defer_reason ∈ {dependency, infra} gesetzt sein UND ein Folge-PL-Item via deferral_materialize.py emittiert worden sein (Engine emittiert, nicht der Lead — [[feedback_machine_not_context]]). DEFER ist NICHT ABORT: der Stage ist legitim aufgeschoben (re-surfacing), nicht gescheitert."
  - "INV-STAGE-ELEV-7 (BL-323 AK-2 — completed_sub_batches-Semantik): Hat ein Sub-Batch mindestens einen DEFER genommen (deferred_stages != []), MUSS sein completed_sub_batches-Eintrag `stage_plan_complete: false` + `deferred_stages: [N, ...]` tragen. 'completed' bedeutet 'Stage-gebankt' (die gelaufenen Stages sind grün), NICHT 'durch den geplanten Stage-Plan'. Folge: ein Sub-Batch darf in completed_sub_batches stehen UND zugleich stage-plan-UNVOLLSTÄNDIG sein. Das Story-DONE-Gate (batchEnde / sdf_final_closure / loopDecision) DARF die Story NICHT auf DONE setzen, solange ein offenes deferred-stage/deferred-ak PL-Item existiert (alle via INV-STAGE-ELEV-6 materialisierten Folge-PL-Items MÜSSEN geschlossen sein). So entsteht kein 'überklagtes completed' — der aufgeschobene Stage bleibt strukturell als nachzuholende Arbeit sichtbar, nicht nur als Prosa."
---

# _SDF_berater_stageElevation — Stage-Elevation-Decision (BL-171)

## VERTRAG

```
+======================================================================+
|  VERTRAG: _SDF_berater_stageElevation — BL-171 (Phase 2.2 NEU)       |
+======================================================================+
|  LIEST:                                                              |
|    I_PIPELINE_STATE.{last_stage_completed, phase,                    |
|                      handschuh_wechsel_pending,                      |
|                      impl_test_stages[N].status}                     |
|    BERATER_OUTPUTS.nachphase.verify_status (optional)                |
|    DF_BATCH_STATE.{batch_stages[k], completed_stages_per_batch[k],   |
|                    current_sub_batch_id, current_stage}              |
|    BERATER_OUTPUTS.stageElevation.retry_counts (vorheriger Lauf)     |
|                                                                       |
|  SCHREIBT:                                                            |
|    BERATER_OUTPUTS.stageElevation = {                                 |
|      next_action: ELEVATE | BATCH_DONE | RETRY | ABORT | HALT | DEFER,|
|      next_stage:  int | null,                                          |
|      rationale:   text,                                                |
|      retry_counts: {stage_N: count, ...},                              |
|      current_stage_outcome: GREEN | PARTIAL | RED | PAUSED | DEFERRED, |
|      defer_reason: dependency | infra | null,  # NUR bei DEFER (AK-1) |
|      deferred_stages: [int, ...] | null,        # NUR bei DEFER       |
|      defer_trigger: text | null,                # NUR bei DEFER       |
|      deferral_pl_item_id: text | null  # die emittierte Folge-PL-id   |
|    }                                                                  |
|                                                                       |
|  AUFRUF: Skill(_SDF_berater_stageElevation, args="{NAME}")            |
|  PHASE:  SDF Phase 2.2 — direkt nach Phase_2_1_dispatcher_with_stage |
|  ZWECK:  Decision ob naechste Stage / Retry / Batch-Done / Abort      |
|  ANTI:   KEIN Skill()-Aufruf (reine Decision-Logik)                  |
+======================================================================+
```

## LOGIK

### SCHRITT 0: Entry — Inputs lesen

```
manifest_path = WORKING_DIR + "/_manifest.md"

# I-Output (last run)
i_state           = lies(manifest_path).I_PIPELINE_STATE
last_stage        = i_state.last_stage_completed
i_phase           = i_state.phase
hwp               = i_state.handschuh_wechsel_pending ?? false
stage_status      = i_state.impl_test_stages[last_stage].status ?? null  # done|partial|failed|null

# Nachphase-Verify (optional — nur wenn I_orchestrate Steps 21+ erreicht hat)
nachphase_status  = BERATER_OUTPUTS.nachphase.verify_status ?? null  # PASS|FAIL|PARTIAL|null

# Sub-Batch-Plan
batch_key         = DF_BATCH_STATE.current_sub_batch_id
planned_stages    = DF_BATCH_STATE.batch_stages[batch_key] ?? [1]
completed_stages  = DF_BATCH_STATE.completed_stages_per_batch[batch_key] ?? []
current_stage     = DF_BATCH_STATE.current_stage

# BL-323 AK-1: explizites Stage-Defer-Signal aus der Build-Phase (Infra-absent /
# Dependency-not-ready). null = kein Defer. {reason: dependency|infra, trigger: text}.
stage_defer_signal = DF_BATCH_STATE.stage_defer_signal[current_stage] ?? null

# Retry-Counter persistent ueber Berater-Aufrufe
retry_counts      = BERATER_OUTPUTS.stageElevation.retry_counts ?? {}
retry_for_current = retry_counts[current_stage] ?? 0
```

### SCHRITT 1: Stage-Outcome klassifizieren

```
IF i_phase == "PAUSED":
  outcome = "PAUSED"

ELIF hwp == true AND stage_status == "done":
  # Standard-Erfolg: I_orchestrate hat Sub-Phase G durchgefuehrt
  outcome = "GREEN"

ELIF stage_status == "partial":
  outcome = "PARTIAL"

# BL-323 AK-1 — DEFER-Diskriminator: ein LEGITIM aufgeschobener Stage (Infra-absent
# ODER Dependency-not-ready) — NICHT verwechseln mit echtem RED→ABORT. Der Stage ist
# nicht gescheitert; er kann (noch) nicht laufen. Signal-Quelle: I_PIPELINE_STATE
# (z.B. stage_status="deferred" / phase="STAGE_DEFERRED") ODER ein explizites
# DF_BATCH_STATE.stage_defer_signal[current_stage] = {reason, trigger} aus der
# Build-Phase. Nur EXPLIZITE Defer-Signale → DEFERRED; ein blosses Test-Rot ist KEIN
# Defer (das bleibt RED→ABORT). Konservativ: ohne explizites Defer-Signal NIE DEFERRED.
ELIF stage_defer_signal != null:
  outcome = "DEFERRED"

ELIF stage_status == "failed" OR nachphase_status == "FAIL":
  outcome = "RED"

ELIF hwp == false AND stage_status == null:
  # I_orchestrate ist abgebrochen ohne Sub-Phase G zu erreichen
  # (z.B. Worker-Crash, Skill-Crash)
  outcome = "RED"

ELSE:
  # Default: konservativ als PARTIAL klassifizieren
  outcome = "PARTIAL"
```

### SCHRITT 2: Geplante vs. abgeschlossene Stages bestimmen

```
# completed_stages enthaelt aktuellen Stage NOCH NICHT — den fuegt SDF erst nach
# erfolgreichem ELEVATE/BATCH_DONE in Outer-Loop hinzu.
# Fuer Decision: betrachte current_stage als "wird gleich completed" wenn outcome=GREEN.

remaining_planned = [s for s in planned_stages
                     if s NOT IN completed_stages
                     AND s != current_stage]

# next_stage = naechste geplante Stage (sortiert aufsteigend)
next_stage_candidate = sorted(remaining_planned)[0] IF remaining_planned ELSE null
```

### SCHRITT 3: Decision-Tree

```
SWITCH outcome:
  "GREEN":
    IF next_stage_candidate != null:
      # Standard-Pfad: weitere Stages geplant, naechste fahren
      next_action  = "ELEVATE"
      next_stage   = next_stage_candidate
      rationale    = "Stage {current_stage} GREEN; verbleibende Stages: {remaining_planned} — Elevate auf {next_stage_candidate}"
    ELSE:
      # Alle Stages dieses Batches durch
      next_action  = "BATCH_DONE"
      next_stage   = null
      rationale    = "Stage {current_stage} GREEN; alle {|planned_stages|} geplanten Stages des Sub-Batch {batch_key} abgeschlossen"

  "PARTIAL":
    IF retry_for_current < 2:
      # 2 Retries erlaubt (sonst Endlosschleife)
      next_action       = "RETRY"
      next_stage        = current_stage
      retry_counts[current_stage] = retry_for_current + 1
      rationale         = "Stage {current_stage} PARTIAL (stage_status={stage_status}); Retry {retry_for_current+1}/2"
    ELSE:
      next_action  = "ABORT"
      next_stage   = null
      rationale    = "Stage {current_stage} PARTIAL; Retry-Limit (2) erreicht — Sub-Batch {batch_key} ABORT"

  "RED":
    next_action  = "ABORT"
    next_stage   = null
    rationale    = "Stage {current_stage} RED (stage_status={stage_status}, nachphase={nachphase_status}, hwp={hwp}) — Sub-Batch {batch_key} ABORT"

  "PAUSED":
    next_action  = "HALT"
    next_stage   = null
    rationale    = "Stage {current_stage} PAUSED via HiL — User-Intervention erforderlich"

  "DEFERRED":   # BL-323 AK-1 — Stage legitim aufgeschoben, NICHT gescheitert
    next_action      = "DEFER"
    next_stage       = null
    defer_reason     = stage_defer_signal.reason   # dependency | infra
    deferred_stages  = sorted([current_stage] + remaining_planned)  # current + alle noch nicht gefahrenen
    defer_trigger    = stage_defer_signal.trigger  # z.B. "PL7 done AND docker_up"
    rationale        = "Stage {current_stage} DEFER (reason={defer_reason}, trigger='{defer_trigger}'); aufgeschobene Stages {deferred_stages} re-surfen als getracktes Folge-PL-Item — KEIN ABORT, kein Loch im Work-Stream"

  DEFAULT:
    # Fallback (sollte nie passieren wegen Default in SCHRITT 1)
    next_action  = "ABORT"
    next_stage   = null
    rationale    = "Unklassifizierter Stage-Outcome — defensive ABORT"
```

### SCHRITT 4: Invariants-Pruefung

```
# INV-STAGE-ELEV-1
ASSERT next_action IN ["ELEVATE", "BATCH_DONE", "RETRY", "ABORT", "HALT", "DEFER"]

# INV-STAGE-ELEV-6 (BL-323 AK-1)
IF next_action == "DEFER":
  ASSERT defer_reason IN ["dependency", "infra"]
  ASSERT deferred_stages != null AND len(deferred_stages) > 0
  ASSERT defer_trigger != null

# INV-STAGE-ELEV-2
IF next_action == "ELEVATE":
  ASSERT next_stage IN planned_stages
  ASSERT next_stage NOT IN completed_stages
  ASSERT next_stage != current_stage

# INV-STAGE-ELEV-3
IF next_action == "RETRY":
  ASSERT retry_counts[current_stage] < 2

# INV-STAGE-ELEV-4
IF next_action == "BATCH_DONE":
  # Alle planned_stages MUESSEN in completed_stages oder current_stage sein
  ASSERT set(planned_stages) - set(completed_stages) - {current_stage} == set()
```

### SCHRITT 4.5: DEFER → Folge-PL-Item EMITTIEREN (BL-323 AK-1, machine-not-context)

```
# NUR bei next_action == "DEFER". Die ENGINE materialisiert beim Defer ein getrenntes,
# re-surfacing Folge-PL-Item — NIE ein Prosa-Marker im Manifest ("Stage 3 deferred").
# [[feedback_machine_not_context]]: der Mechanismus ist maschinen-strukturell, nicht
# Lead-Memory. Ohne klugen Lead (Dark Factory) bliebe die Nachhol-Garantie sonst verloren.
#
# WER ruft den Helper? — Der Berater ist reine Decision-Logik (INV-STAGE-ELEV-5, KEIN
# Skill()). Daher: der Berater SCHREIBT die Decision (DEFER + defer_reason/deferred_stages/
# defer_trigger) ins Manifest und RETURNED sie. Der CALLER (dispatch_implement.js-Motor
# bzw. _SDF_orchestrate Outer-Loop) konsumiert next_action="DEFER" — analog zu wie er
# ELEVATE/BATCH_DONE konsumiert — und ruft dann den deterministischen Helper:

IF next_action == "DEFER":   # ← Caller-Schritt nach Berater-Return, KEIN Skill()
  defer_ctx = {
    kind:            "stage",
    bl_id:           {BL_ID},
    batch:           batch_key,
    deferred_stages: deferred_stages,    # z.B. [3, 6]
    defer_reason:    defer_reason,        # "dependency" | "infra"
    defer_trigger:   defer_trigger,       # "PL7 done AND docker_up"
    verify:          "<welche Tests die deferred Stages abdecken>"
  }
  # Reiner Python-Helper-Aufruf (Bash), KEIN Skill():
  #   from deferral_materialize import materialize_deferral, write_deferral_pl
  pl_item = materialize_deferral(defer_ctx)          # rein, deterministisch, idempotente id
  write_deferral_pl(pl_item, pl_master_path)         # append-if-not-present by id (T4-Dedup)
  deferral_pl_item_id = pl_item["id"]                # z.B. "BL-323-DEFER-batch_PL4-ab12cd34"

  # Das emittierte PL-Item ist {status: "deferred", re_surface: true, resurface_trigger:
  # defer_trigger} → IDF loopCheck (BL-199) re-surft es bei erfuelltem Trigger (AK-3).
```

### SCHRITT 5: Output schreiben

```
BERATER_OUTPUTS.stageElevation = {
  status:               "DONE",
  ts:                   jetzt(),
  current_sub_batch_id: batch_key,
  current_stage:        current_stage,
  current_stage_outcome: outcome,        # GREEN | PARTIAL | RED | PAUSED | DEFERRED
  next_action:          next_action,      # ELEVATE | BATCH_DONE | RETRY | ABORT | HALT | DEFER
  next_stage:           next_stage,       # int | null
  retry_counts:         retry_counts,     # {stage_N: count, ...}
  rationale:            rationale,
  # BL-323 AK-1 — NUR bei next_action=DEFER gesetzt, sonst null:
  defer_reason:         defer_reason,        # dependency | infra | null
  deferred_stages:      deferred_stages,     # [int, ...] | null
  defer_trigger:        defer_trigger,       # text | null
  deferral_pl_item_id:  deferral_pl_item_id, # emittierte Folge-PL-id (SCHRITT 4.5) | null
  inputs_snapshot: {
    last_stage_completed: last_stage,
    i_phase:              i_phase,
    handschuh_wechsel:    hwp,
    stage_status:         stage_status,
    nachphase_status:     nachphase_status,
    planned_stages:       planned_stages,
    completed_stages:     completed_stages,
    remaining_planned:    remaining_planned
  }
}

manifest.update()
Logge: "[STAGE-ELEVATION] {batch_key} stage={current_stage} outcome={outcome} → action={next_action} next_stage={next_stage} | {rationale}"
```

## DECISION-MATRIX (Quick-Reference)

| `i_phase` | `stage_status` | `hwp` | `nachphase` | Outcome | Action |
|---|---|---|---|---|---|
| HANDSCHUH_WECHSEL | done | true | * | GREEN | ELEVATE / BATCH_DONE |
| POST_TDD_CONSUMED | done | true | * | GREEN | ELEVATE / BATCH_DONE |
| POST_PIPELINE | done | true | PASS | GREEN | BATCH_DONE |
| * | partial | * | * | PARTIAL | RETRY / ABORT |
| * | failed | * | * | RED | ABORT |
| * | * | * | FAIL | RED | ABORT |
| PAUSED | * | * | * | PAUSED | HALT |
| (crash) | null | false | null | RED | ABORT |
| * (stage_defer_signal!=null) | * | * | * | DEFERRED | **DEFER** (BL-323 AK-1) |

**DEFER vs ABORT (BL-323 — kritische Unterscheidung):** ABORT = der Stage ist
**gescheitert** (RED, Retry-Limit). DEFER = der Stage kann **legitim (noch) nicht
laufen** (Dependency-not-ready / Infra-absent) — er wird als getracktes, re-surfacing
Folge-PL-Item materialisiert (SCHRITT 4.5) und kehrt zurueck, sobald `defer_trigger`
erfuellt ist. Nie als blosser Prosa-Marker, nie als ABORT verschluckt.

## RESUME-VERHALTEN

Berater ist **idempotent** — bei Re-Run mit gleichen Inputs wird gleiche
Decision produziert. `retry_counts` werden ueber Aufrufe persistiert
(im Berater-Output-Block); Outer-Loop muss `retry_counts` in
`BERATER_OUTPUTS.stageElevation.retry_counts` durchreichen.

## ANTI-PATTERN

1. **NICHT Skill() aufrufen** — Berater ist reine Decision-Logik (INV-STAGE-ELEV-5).
2. **NICHT current_stage in completed_stages_per_batch[k] schreiben** — das ist
   Aufgabe des SDF Outer-Loop NACH Erhalt der Decision (SDF: bei ELEVATE/BATCH_DONE
   appendet er current_stage an completed_stages_per_batch[k]).
3. **NICHT batch_stages mutieren** — Plan ist immutable. Adaptive Stage-Decision
   findet via Decision-Tree statt, nicht via Plan-Aenderung.
4. **NICHT INV-STAGE-ELEV-2 verletzen** — `next_stage` MUSS aus geplantem Plan
   stammen. Cross-Stage-Hopping (z.B. von 1 direkt auf 6 ohne 3 in batch_stages)
   ist UNZULAESSIG.

## TEST-CASES (TDD-Vorlage fuer separate Story)

| Case | Setup | Expected |
|---|---|---|
| TC-1 GREEN+remaining | hwp=true, stage_status=done, planned=[1,3], current=1, completed=[] | ELEVATE → next_stage=3 |
| TC-2 GREEN+last | hwp=true, stage_status=done, planned=[1,3], current=3, completed=[1] | BATCH_DONE → next_stage=null |
| TC-3 PARTIAL+retry-1 | stage_status=partial, retry=0 | RETRY → next_stage=current_stage, retry=1 |
| TC-4 PARTIAL+retry-limit | stage_status=partial, retry=2 | ABORT |
| TC-5 RED | stage_status=failed | ABORT |
| TC-6 PAUSED | i_phase=PAUSED | HALT |
| TC-7 Crash | hwp=false, stage_status=null | ABORT |
| TC-8 DEFER-dependency | stage_defer_signal={reason:dependency, trigger:"PL7 done"}, planned=[1,3], current=3, completed=[1] | DEFER → deferred_stages=[3], defer_reason=dependency, deferral_pl_item_id gesetzt (BL-323 AK-1) |
| TC-9 DEFER-infra | stage_defer_signal={reason:infra, trigger:"docker_up"}, current=3 | DEFER → defer_reason=infra, Folge-PL-Item emittiert |
| TC-10 RED≠DEFER | stage_status=failed, stage_defer_signal=null | ABORT (Test-Rot ist KEIN Defer) |

## CHANGELOG

- **2026-06-12 v1.1.0** — BL-323 AK-1: DEFER-Branch ergaenzt. Enum
  {ELEVATE,BATCH_DONE,RETRY,ABORT,HALT} → +DEFER. Ein legitim aufgeschobener Stage
  (Dependency-not-ready / Infra-absent, via explizitem `stage_defer_signal`) → Decision
  DEFER (kein ABORT) + Engine emittiert ein re-surfacing Folge-PL-Item via
  `deferral_materialize.py` (SCHRITT 4.5, [[feedback_machine_not_context]]). INV-STAGE-ELEV-6.
- **2026-05-10 v1.0.0** — Initial. BL-171 Stage-Elevation-Decision-Berater zwischen
  Phase 2.1 (I_orchestrate-Dispatch) und Outer-Loop-Continue. Ersetzt naive
  FOR-Iteration durch WHILE-Loop mit Decision-Branch.
