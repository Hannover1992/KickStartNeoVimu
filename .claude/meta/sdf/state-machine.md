# State Machine: DF_PIPELINE_STATE (SDF)

Referenz fuer `/_SDF_orchestrate` — State Machine Details, Transitionen, DEFER-Funktion, ABORT-Handling.

## Gueltige Zustandsuebergaenge (v0.5.0)

```
INIT              → PRE_LOAD_DONE, ABORTED
PRE_LOAD_DONE     → ANALYSE, ABORTED
ANALYSE           → ITEM_LOOP, ABORTED
ITEM_LOOP         → ITEM_DONE, ABORTED       (pro Item: Implement → Post-Impl)
ITEM_DONE         → ITEM_STAGE, ABORTED      (stage_orchestrate PRO ITEM nach GAP=0%)
ITEM_STAGE        → ITEM_LOOP, DONE, ABORTED (naechstes Item ODER Batch fertig)
DONE              → (Terminal — BDF uebernimmt)
ABORTED           → (Terminal)

Veraltete Zustaende (aus SDF entfernt, BDF-Level):
POST_IMPL_STAGE | POST_IMPL_DIFFRED | POST_IMPL_AC | POST_IMPL_SMOOTHING |
POST_IMPL_PREPR | PUSHING | FINISHING | DEBLOATING
```

## Manifest-Pattern B (State + Protokoll-Rollover)

```
STATE (_manifest.md): DF_PIPELINE_STATE wird bei JEDEM Phasenwechsel aktualisiert
PROTOKOLL (_manifest_protokoll.md): Nur nach DONE/ABORTED (Terminal-Zustand)
INVARIANTE: resume_point NIEMALS rotieren (W11 Analogie)

Stale-Detection bei erneutem Start:
  df_status == DONE/ABORTED  → Frischer Start
  df_status laufend          → Auto-Resume bei hil=off
  df_status null             → Frischer Start
```

## State-Transition-Funktion

```
FUNKTION df_state_transition(neuer_status, phase_nr, worker_name, reason):

  aktuell = DF_PIPELINE_STATE.df_status

  # Validierung gegen gueltige Uebergaenge
  IF neuer_status NOT IN GUELTIGE_UEBERGAENGE[aktuell]:
    Logge WARNUNG: "[DF-STATE] Ungueltiger Uebergang: {aktuell} → {neuer_status}"
    → Weiter (defensiv, geloggt)

  # State aktualisieren
  DF_PIPELINE_STATE.df_status      = neuer_status
  DF_PIPELINE_STATE.df_phase       = phase_nr
  DF_PIPELINE_STATE.current_worker = worker_name
  DF_PIPELINE_STATE.last_completed = reason
  DF_PIPELINE_STATE.resume_point   = "{phase_nr}.0"

  # In Manifest schreiben
  Aktualisiere DF_PIPELINE_STATE Block in _manifest.md
```

## DEFER-Funktion (RF-08, W231)

```
FUNKTION df_defer_to_parking_lot(phase_name, reason):
  # Schreibt ein DF-GATE-FAIL Item in _parking-lot.md

  eintrag = """
  - [ ] **DF-GATE-FAIL: {phase_name} {DF_PIPELINE_STATE.df_task}**
    - Beschreibung: {reason}
    - Quelle: /_SDF_orchestrate Phase {DF_PIPELINE_STATE.df_phase}
    - Pipeline-Route: {DF_PIPELINE_STATE.pipeline_route}
    - Prioritaet: HOCH
    - Datum: {ISO-8601}
  """

  Append eintrag an {VAULT}/_parking-lot.md
  Logge: "DEFER: {phase_name} → Parking-Lot (DF-GATE-FAIL: {reason})"
```

## ABORT-Handling

```
# Bei ABORTED: Protokoll-Rollover mit Fehler-Grund

pipeline_zusammenfassung = """
## DF_orchestrate [{Datum}] {NAME} — ABORTED
  Route: {pipeline_route}
  Letzte Phase: {df_phase}
  Fehler: {abort_reason}
  difficulty: {difficulty}
  Ergebnis: ABORTED
"""

Prepend pipeline_zusammenfassung an _manifest_protokoll.md (W18)

# BDF-ABORT-Signal (AK-07g, AK-08k): NUR wenn BDF gerade laeuft
IF BDF_PIPELINE_STATE.bdf_status == "ITEM_RUNNING":
  Schreibe in _manifest.md → BDF_PIPELINE_STATE:
    BDF_ITEM_DONE: ABORTED
    BDF_NEXT_TRIGGER: true

# State bleibt im Manifest fuer Diagnose
# Team NICHT aufloesen bei ABORT (User koennte Resume wollen)

Logge: "=== DARK FACTORY ABORTED ==="
Logge: "Phase {df_phase}: {abort_reason}"
Logge: "Resume moeglich: /_SDF_orchestrate {NAME} (Auto-Resume ab Phase {df_phase})"
```

## HiL-Punkte Gesamtuebersicht (trotz hil=off)

| # | Phase | Trigger | Bedingung |
|---|-------|---------|-----------|
| 1 | 2 (Item-Loop, SC-Worker) | SC-ABORT: Stagnation >= 7.0 | ABORT fuer dieses Item → User-Entscheidung: RESTART_SC / SKIP_SC_TO_I / VOLLABORT |
| 2 | 2 (Item-Loop, I-Worker) | TDD-MAX_ITERATIONS | ABORT fuer dieses Item → User-Entscheidung: RESTART_I / SKIP_ITEM / VOLLABORT |
| 3 | 2 (Item-Loop, SDF) | SDF-MAX_ITERATIONS fuer ein Item | ABORT fuer dieses Item → User-Entscheidung: WEITER / ABBRECHEN |
