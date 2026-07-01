# SDF Param-Setup — Aufruf, Parameter-Validierung, GLOBAL_MODUS, max_cycles

Referenz fuer `/_SDF_orchestrate` — der Conductor ruft den Setup (SCHRITT 0.1/0.2/0.3) aus und
verweist fuer die Detail-Tabellen + Validierungslogik hierher. Ausgelagert aus BL-401 (SRP-Refactor).

---

## Aufruf (RF-01)

```
/_SDF_orchestrate NAME [difficulty] [ceiling] [floor] [--task-source=auto|pl|direct|backlog] [--batch=ID1,ID2,...] [--mode=testRun|dryRun]
```

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `NAME` | (PFLICHT) | String | Feature-Name. Keine Auto-Erkennung — MUSS angegeben werden. |
| `difficulty` | normal | easy, normal, hard | Steuert max_cycles, Wellen-Tiefe, TDD-Iterations |
| `ceiling` | (session) | haiku, sonnet, opus | Hoechstes erlaubtes Modell |
| `floor` | (session) | haiku, sonnet | Niedrigstes Modell fuer Exploration |
| `--task-source` | direct | auto, pl, direct, backlog | Woher die Aufgabe kommt (W233, RF-SDF-008) |
| `--batch` | null | Komma-sep. PL-Item-IDs | Batch-Liste von BDF (RF-SDF-006). Wenn angegeben: Batch-Modus aktiv. |
| `--mode` | null | testRun, dryRun | testRun: A-Pipeline-Skip + Phase-0.5-Fork. dryRun: Mock-Modus, simuliert Phase 2 ohne SC/I/TDD-Aufrufe. |

**task-source Semantik (W233):**

| Wert | Verhalten |
|------|-----------|
| `direct` | NAME ist Feature-Name, Task.md existiert oder wird erstellt |
| `pl` | NAME ist Parking-Lot Item ID, Pipeline markiert PL-Item als [x] nach DONE |
| `auto` | Liest Parking-Lot, waehlt naechstes offenes Item (halbautomatisch, Modus 3) |
| `backlog` | NAME ist BL-Item aus _backlog_index.md. SDF liest BL-Frontmatter (spec_link, Reifegrad). Bei GAP=0%: BL-Status DONE (nicht PL [x]). Reifegrad-Signal aus Manifest (RF-SDF-008) |

**Batch-Modus (RF-SDF-006):**

Wenn `--batch` angegeben: SDF erhaelt Liste von PL-Items. Batch wird sequentiell abgearbeitet.
Alternativ: BDF schreibt `batch_items` ins Manifest (BDF_BATCH_STATE) bevor Handschuh-Wechsel.
SDF liest Batch-Liste aus Manifest (primaer) oder CLI-Parameter (sekundaer).

---

## SCHRITT 0.1: Parameter parsen + validieren

```
IF NAME nicht angegeben:
  → FEHLER: "/_SDF_orchestrate benoetigt NAME als erstes Argument."
  → ABBRUCH

IF difficulty angegeben UND difficulty NOT IN {easy, normal, hard}:
  → FEHLER: "Ungueltiger difficulty-Wert: {difficulty}. Erlaubt: easy, normal, hard."
  → ABBRUCH

# Session-Params laden (Capping-Formel aus _param.md)
# INTELLIGENZ-BUDGET-CAP-INVARIANTE (BL-129):
# Session-Params sind IMMER Obergrenze. CLI darf NIEMALS darueber gehen.
# Hierarchie difficulty: easy<normal<hard ; ceiling/floor: haiku<sonnet<opus
params = lies("{VAULT}/_session_params.md")
difficulty = min_level(CLI-Wert, params.difficulty) ?? params.difficulty ?? "normal"
ceiling    = min(CLI-ceiling, params.ceiling) ?? params.ceiling ?? "sonnet"
floor      = max(CLI-floor, params.floor) ?? params.floor ?? "haiku"

# Validierung: ceiling >= floor
hierarchie = {opus: 3, sonnet: 2, haiku: 1}
IF hierarchie[ceiling] < hierarchie[floor]:
  → FEHLER: "ceiling ({ceiling}) darf nicht unter floor ({floor}) liegen."
  → ABBRUCH

# middle berechnen (fuer Wellen-Drafter)
middle = sonnet WENN ceiling == opus, sonnet WENN ceiling == sonnet, haiku WENN ceiling == haiku

# task_source parsen und in State schreiben (RF-08, F5, RF-SDF-008 Backlog)
task_source = CLI-Wert("--task-source") ?? "direct"
IF task_source NOT IN {auto, pl, direct, backlog}:
  → FEHLER: "Ungueltiger task-source: {task_source}. Erlaubt: auto, pl, direct, backlog."
  → ABBRUCH

# testRun-Modus parsen (Phase-0.5-Fork, ADR-FTR-01)
testRun_mode = CLI-Wert("--mode") == "testRun"
IF testRun_mode:
  Logge: "[testRun] Modus aktiv — A-Pipeline SKIP, Phase-0.5-Fork aktiv."

# BL-133 Slice-3: postPhase-Modus ENTFERNT. Phasen 4-7 wandern in Berater/Skills.
```

## SCHRITT 0.2: GLOBAL_MODUS-Setup (W220, ADR-4)

```
# Session-Params setzen (PRIMAER)
Schreibe {VAULT}/_session_params.md:
  # Session-Parameter
  **HiL:** off
  **difficulty:** {difficulty}
  **ceiling:** {ceiling}
  **floor:** {floor}

# Manifest aktualisieren (SEKUNDAER, Audit-Trail)
In {VAULT}/_manifest.md:
  Setze: **GLOBAL_MODUS:** small_dark_factory
  Setze: **GLOBAL_HIL:** off
  Setze: **GLOBAL_DIFFICULTY:** {difficulty}
  Setze: **GLOBAL_CEILING:** {ceiling}
  Setze: **GLOBAL_FLOOR:** {floor}
```

## SCHRITT 0.3: max_cycles berechnen (W225, ADR-5)

```
max_cycles_tabelle = {easy: 3, normal: 5, hard: 9}
max_cycles = max_cycles_tabelle[difficulty]

# Manifest-Feld fuer SC-Override (RF-07) — per-Story (BL-155 AK-1)
In {WORKING_DIR}/_manifest.md:
  Setze: dark_factory_max_cycles_override: {max_cycles}
```

---

## DF_PIPELINE_STATE Schema-Detail (B5-Rest)

```yaml
DF_PIPELINE_STATE:
  df_status:          IDLE | INIT | PRE_LOAD_DONE | ANALYSE | AK_PLAN | ITEM_LOOP | ITEM_DONE |
                      ITEM_STAGE | DONE | ABORTED
  df_phase:           0..3
  current_worker:     "a-sdf-{phase}" | null
  last_completed:     {phase_name}
  resume_point:       {phase}.{step}
  pipeline_route:     A_I | A_SC_I | A_SC_ANALYSE
  df_start:           {ISO-8601}
  df_task:            {NAME}
  dark_factory_ready: true | false
  max_cycles:         3 | 5 | 9
  sc_srs_last:        {letzter SRS-Wert}
  difficulty:         easy | normal | hard
  task_source:        auto | pl | direct | backlog
  # Batch-Felder: MIGRIERT nach DF_BATCH_STATE (BL-134 Architektur-Split)
  # ak_plan-Felder: MIGRIERT nach IDF_PIPELINE_STATE.ak_plan (BL-076)
  testrun_mode:       true | false
  testrun_stages:     [1, 2, 3, 4, 5]
  testrun_current:    {N}
  testrun_result:
    pass:             {N}
    fail:             {M}
    new_pl_items:     [{id1, ...}]
  phase_indicators:
    srs_delta:        {SRS-Veraenderung pro Phase}
    gap_delta:        {GAP-Veraenderung pro Phase}
    ak_count:         {aktuelle AK-Anzahl}
    interpretation_score: {Interpretationsspielraum-Indikator}
  # Post-GAP Checklist (BL-035 SDF_Ketten_Enforcement, RF-01, AK-01-01)
  # 6 Pflichtschritte nach GAP=0% — Zustaende: OPEN → REQUIRED → DONE | ABORTED
  # INV-01: Kein Schritt ist optional. INV-02: Alle DONE vor BDF_NEXT_TRIGGER.
  sdf_post_gap_checklist:
    bl_done: OPEN              # BL/PL-Item Status-Update
    checks5: OPEN              # 5 prozessbegleitende Checks
    testSearch: OPEN           # testSearch mit 3-Szenarien-Weiche
    stage: OPEN                # stage_orchestrate pro Item
    regressionGuard: OPEN      # Regressions-Guard bei Code-Aenderungen
    final: OPEN                # PHASE FINAL: Protokoll-Rollover, DONE→IDLE
```

**HINWEIS:** SDF endet nach Phase 3 (Batch-Ende). Quality/Delivery/Finish wandern in Berater/Skills
(siehe BL-133 Blueprint Sektion 6). Vollstaendige Transitionen + State-Transition-Funktion +
DEFER-Funktion: `{META}/sdf/state-machine.md`.
