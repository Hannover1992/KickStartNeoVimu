---
status: active
version: 1.0.0
created: 2026-04-26
op: SmallDarkFactory
phase: 0.5
type: berater
chain_position: middle
model_tier: middle
parent: _SDF_orchestrate
actor: _SDF_orchestrate — Phase 0.5 (NUR bei --mode=testRun, ADR-FTR-01)
sdf_quelle: Z416-491
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.testrun_mode", purpose: "Guard: nur aktiv wenn true"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "T_ORCHESTRATE_STATE", purpose: "Ergebnis nach Skill-Rueckkehr"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "neue Items seit T_orchestrate Start", purpose: "new_pl_items"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.testrun_mode", purpose: "true setzen"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.testrun_stages", purpose: "[1,2,3,4,5]"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.testrun_current", purpose: "Stufen-Fortschritt (Resume-sicher)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.testrun_result", purpose: "pass/fail/new_pl_items Rueckkanal"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BDF_PIPELINE_STATE.BDF_BATCH_DONE", purpose: "true nach Abschluss"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BDF_PIPELINE_STATE.BDF_NEXT_TRIGGER", purpose: "true nach Abschluss"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BDF_PIPELINE_STATE.testRun_result", purpose: "Rueckkanal zu BDF"}
    - {file: "_session_params.md", path: "testRun + tdd_stages", purpose: "VOR T_orchestrate Aufruf setzen"}
    - {file: "_manifest_protokoll.md", path: "Protokoll-Rollover", purpose: "Prepend Pattern B"}
  writes_not:
    - DF_PIPELINE_STATE.df_status (macht df_state_transition DONE)
---

# /_SDF_berater_testRun (Phase 0.5 — TestRun-Stufen-Loop)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_testRun (Phase 0.5)                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  EINGABE: NAME, difficulty, ceiling, floor (aus SDF-Kontext)         ║
║  LIEST: DF_PIPELINE_STATE.testrun_mode                               ║
║         T_ORCHESTRATE_STATE (nach Skill-Rueckkehr)                   ║
║         {VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md        ║
║  SCHREIBT: DF_PIPELINE_STATE.testrun_{mode,stages,current,result}    ║
║            BDF_PIPELINE_STATE.{BDF_BATCH_DONE,BDF_NEXT_TRIGGER,      ║
║              testRun_result}                                          ║
║            _session_params.md: testRun=true, tdd_stages=[1..5]       ║
║            _manifest_protokoll.md: Protokoll-Rollover (Prepend W18)  ║
║  ACTOR: _SDF_orchestrate Phase 0.5 (ADR-FTR-01)                     ║
║  MODELL-TIER: sonnet                                                  ║
║  INVARIANTEN:                                                         ║
║    INV-1: Ersetzt Phase 1-3 komplett (verify-only, kein A/I/SC)      ║
║    INV-2: CS5-konform — Delegation an _T_orchestrate, KEIN direktes  ║
║           I_orchestrate pro Stufe                                     ║
║    INV-3: BDF_NEXT_TRIGGER=true NUR nach allen 5 Stufen              ║
║    INV-4: Resume-sicher via testrun_current (Stufen-Fortschritt)     ║
╚══════════════════════════════════════════════════════════════════════╝
```

## INPUT / OUTPUT

```
INPUT:
  NAME        - Feature-Name (aus SDF-Kontext)
  difficulty  - easy | normal | hard
  ceiling     - haiku | sonnet | opus
  floor       - haiku | sonnet

OUTPUT (BERATER_OUTPUTS.testRun):
  stages_done:   5                          # Anzahl abgeschlossener Stufen
  stage_results: [{stufe, count, result}]   # Pro-Stufe Ergebnisse
  pass:          {N}                        # Anzahl PASS-Stufen
  fail:          {M}                        # Anzahl FAIL-Stufen
  new_pl_items:  [{id1, ...}]              # neu erstellte PL-Item-IDs
```

## Pseudocode

```
# Phase 0.5 ersetzt Phase 1-3 komplett (verify-only, kein A-Pipeline, kein I/SC).
# CS5-konform: Delegation an _T_orchestrate (nicht mehr direkt via I_orchestrate pro Stufe)
# _T_orchestrate uebernimmt: testSearch + TDD_execute pro Stufe, PL-Items bei FAIL

# Initialisierung
DF_PIPELINE_STATE.testrun_mode    = true
DF_PIPELINE_STATE.testrun_stages  = [1, 2, 3, 4, 5]
DF_PIPELINE_STATE.testrun_current = 0
DF_PIPELINE_STATE.testrun_result  = {pass: 0, fail: 0, new_pl_items: []}
Aktualisiere Manifest

# WICHTIG: _session_params.md tdd_stages + testRun setzen VOR T_orchestrate Aufruf
# T_orchestrate liest tdd_stages aus _session_params.md und orchestriert alle Stufen
Schreibe {VAULT}/_session_params.md:
  testRun: true
  tdd_stages: [1, 2, 3, 4, 5]

# HANDSCHUH-WECHSEL: SDF → T_orchestrate (CS5-konform)
# T_orchestrate fuehrt pro Stufe: _I_testSearch + _TDD_execute aus
# Bei FAIL: T_orchestrate erstellt PL-Items selbststaendig
# Bei ALL PASS: T_orchestrate meldet Erfolg
Logge: "[testRun] Delegation an /_T_orchestrate — alle Stufen S1-S5"
Skill(skill="_T_orchestrate", args="{NAME}")

# Nach T_orchestrate: Ergebnis aus Manifest lesen (Handschuh-Wechsel zurueck)
t_result = lies({WORKING_DIR}/_manifest.md → T_ORCHESTRATE_STATE)
# T_ORCHESTRATE_STATE enthaelt: status, stages_passed, stages_failed, started_at, finished_at

DF_PIPELINE_STATE.testrun_result = {
  pass:         len(t_result.stages_passed),
  fail:         len(t_result.stages_failed),
  new_pl_items: lies({VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md → neue Items seit T_orchestrate Start)
}
DF_PIPELINE_STATE.testrun_current = 5
Aktualisiere Manifest
Logge: "[testRun] T_orchestrate zurueck — {t_result.status}"

# MONITORING-AUSGABE (RF-SDF-009, AK-SDF-009b)
Logge:
  | Stufe | Tests gefunden | PASS | FAIL |
  |-------|----------------|------|------|
  | S1    | {testrun_s1_count} | {testrun_s1_result==pass?1:0} | {testrun_s1_result==fail?1:0} |
  | S2    | {testrun_s2_count} | {testrun_s2_result==pass?1:0} | {testrun_s2_result==fail?1:0} |
  | S3    | {testrun_s3_count} | {testrun_s3_result==pass?1:0} | {testrun_s3_result==fail?1:0} |
  | S4    | {testrun_s4_count} | {testrun_s4_result==pass?1:0} | {testrun_s4_result==fail?1:0} |
  | S5    | {testrun_s5_count} | {testrun_s5_result==pass?1:0} | {testrun_s5_result==fail?1:0} |
  | **GESAMT** | — | {testrun_result.pass}/5 | {testrun_result.fail}/5 |

# SCHRITT 0.5.5: Signal zu BDF schreiben (BDF_NEXT_TRIGGER-Erweiterung, ADR-FTR-06)
Schreibe {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
  BDF_BATCH_DONE:  true
  BDF_NEXT_TRIGGER: true
  testRun_result:
    pass:         {testrun_result.pass}
    fail:         {testrun_result.fail}
    new_pl_items: {testrun_result.new_pl_items}

Logge: "=== SDF testRun DONE === Pass={testrun_result.pass}/5, Fail={testrun_result.fail}/5"
df_state_transition(DONE, 0, null, "testRun S1-S5 abgeschlossen, BDF uebernimmt")

# Protokoll (Pattern B)
pipeline_zusammenfassung = """
## DF_orchestrate [{Datum}] {NAME} --mode=testRun
  Route: testRun (Phase-0.5-Fork, A-Pipeline SKIP)
  Stufen: S1-S5 ({testrun_result.pass} PASS, {testrun_result.fail} FAIL)
  Neue PL-Items: {testrun_result.new_pl_items}
  Ergebnis: DONE (BDF: {'SCANNING' if fail > 0 else 'POST-FLOW'})
"""
Prepend pipeline_zusammenfassung an _manifest_protokoll.md (W18)
# Kein TeamDelete (kein TeamCreate in Phase 0.5, Handschuh-Wechsel via Skill braucht kein Team)

# Schreibt BERATER_OUTPUTS.testRun:
Schreibe {WORKING_DIR}/_manifest.md → BERATER_OUTPUTS.testRun:
  stages_done:   5
  stage_results: lies T_ORCHESTRATE_STATE.stages_passed + stages_failed
  pass:          {testrun_result.pass}
  fail:          {testrun_result.fail}
  new_pl_items:  {testrun_result.new_pl_items}
```

## INVARIANTEN

```
INV-1: Phase 0.5 ist exklusiv — wenn aktiv, entfallen Phase 1/2/3 vollstaendig.
INV-2: CS5-Invariante: KEIN direktes I_orchestrate pro Stufe. Immer via _T_orchestrate.
INV-3: BDF_NEXT_TRIGGER=true NUR wenn alle 5 Stufen abgeschlossen (testrun_current==5).
INV-4: Resume via testrun_current — bei Crash kann ab letzter Stufe fortgesetzt werden.
INV-5: _session_params.md MUSS vor Skill(_T_orchestrate) beschrieben sein.
```
