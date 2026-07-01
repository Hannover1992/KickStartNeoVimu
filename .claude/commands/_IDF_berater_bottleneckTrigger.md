---
status: active
version: 1.0.0
created: 2026-05-24
feature: BL-206
ak_implements: [AK-1]
type: berater
phase: "3.8e"
chain_position: after-plBewertung-3.8d-before-dependencyAnalyzer-4
model_tier: middle
contract:
  reads:
    - {file: "_manifest.md", purpose: "DF_BATCH_STATE.per_pl_evaluation (aus Phase 3.8d), session_param.bottleneck_max_loops"}
  writes:
    - {output: "DF_BATCH_STATE.bottleneck_queue", purpose: "Queue-Struktur {queue_for_sc, queue_for_wp, loop_counts, deferred}"}
    - {output: "DF_BATCH_STATE.bottleneck_trigger_done", purpose: "Idempotenz-Flag"}
    - {output: "BERATER_OUTPUTS.bottleneckTrigger", purpose: "Status + Queue-Statistik"}
  not_writes:
    - modus
    - recommended_modus
    - sdf_mode
    - sdf_mode_hint
    - mode_recommendation
    - expected_sdf_mode
---

# _IDF_berater_bottleneckTrigger (Phase 3.8e)

Liest `DF_BATCH_STATE.per_pl_evaluation` (aus Phase 3.8d), gruppiert Bottleneck-PLs in Queues
(`queue_for_sc` + `queue_for_wp`) und schreibt `DF_BATCH_STATE.bottleneck_queue`.
Downstream-Konsument: SDF Phase 1.1 `_SDF_berater_modusEntscheidung` (C3 SCHRITT 2.5).

## INVARIANTEN

- INV-MODUS-1: Schreibt NIEMALS `modus` -- bottleneck_queue ist Signal, kein Modus-Entscheid
- INV-MODUS-5: Alle verbotenen Felder in contract.not_writes
- INV-SRS-4: bottleneck_route = BEOBACHTUNG aus Phase 3.8d -- kein Modus-Vorschlag
- INV-LOOP-1: Max-Loop-Schutz PFLICHT -- kein Endlos-Loop ohne DEFERRED-Mechanismus

## Ablauf

### Schritt 0: Idempotenz-Gate

```python
# [bottleneckTrigger] ENTRY
LOG "[bottleneckTrigger] Phase 3.8e gestartet"

IF DF_BATCH_STATE.bottleneck_trigger_done == true:
  LOG "[bottleneckTrigger] IDEMPOTENZ-GATE -- bereits ausgefuehrt, SKIP"
  RETURN exitcode=0
```

### Schritt 1: per_pl_evaluation pruefen

```python
per_pl_evaluation = DF_BATCH_STATE.per_pl_evaluation ?? None

IF per_pl_evaluation is None:
  LOG "[bottleneckTrigger] per_pl_evaluation fehlt -- SKIP (Phase 3.8 nicht ausgefuehrt?)"
  RETURN exitcode=0
```

### Schritt 2: Queues aufbauen

```python
queue_for_sc = []
queue_for_wp = []

FOR pl_id, pl_eval IN per_pl_evaluation.items():
  IF pl_eval.bottleneck == true:
    IF pl_eval.bottleneck_route == "WP":
      queue_for_wp.append(pl_id)
      LOG f"[bottleneckTrigger] {pl_id}: bottleneck_route=WP -> queue_for_wp"
    ELSE:  # SC oder no_refs
      queue_for_sc.append(pl_id)
      LOG f"[bottleneckTrigger] {pl_id}: bottleneck_route={pl_eval.bottleneck_route} -> queue_for_sc"

LOG f"[bottleneckTrigger] Queues: sc={queue_for_sc}, wp={queue_for_wp}"
```

### Schritt 3: Loop-Zaehler initialisieren (bestehende erhalten)

```python
# Bestehende loop_counts aus vorherigem Run erhalten (Re-Entry-Faehigkeit)
existing_queue = DF_BATCH_STATE.bottleneck_queue ?? {}
loop_counts = existing_queue.loop_counts ?? {}

# Neue Bottleneck-PLs initialisieren (falls noch nicht vorhanden)
FOR pl_id IN (queue_for_sc + queue_for_wp):
  IF pl_id NOT IN loop_counts:
    loop_counts[pl_id] = 0
    LOG f"[bottleneckTrigger] {pl_id}: loop_count initialisiert auf 0"
```

### Schritt 4: Max-Loop-Filter (INV-LOOP-1)

```python
max_loops = session_param.bottleneck_max_loops ?? 3
deferred = []

FOR pl_id IN list(queue_for_sc + queue_for_wp):
  IF loop_counts[pl_id] >= max_loops:
    deferred.append(pl_id)
    IF pl_id IN queue_for_sc:
      queue_for_sc.remove(pl_id)
    IF pl_id IN queue_for_wp:
      queue_for_wp.remove(pl_id)
    # HiL-Signal: PL-Item status auf DEFERRED_BOTTLENECK setzen
    Append PL-Item: pl_id -> status="DEFERRED_BOTTLENECK"
    LOG f"[bottleneckTrigger] {pl_id}: loop_count={loop_counts[pl_id]} >= max_loops={max_loops} -> DEFERRED_BOTTLENECK"

IF len(deferred) > 0:
  LOG f"[bottleneckTrigger] WARN: {len(deferred)} PLs auf DEFERRED_BOTTLENECK gesetzt: {deferred}"
```

### Schritt 5: Output schreiben

```python
Write(_manifest.md -> DF_BATCH_STATE.bottleneck_queue = {
  queue_for_sc:  queue_for_sc,
  queue_for_wp:  queue_for_wp,
  loop_counts:   loop_counts,
  deferred:      deferred,
  computed_at:   today()
})

Write(_manifest.md -> DF_BATCH_STATE.bottleneck_trigger_done = true)

Write(BERATER_OUTPUTS.bottleneckTrigger = {
  status:             "DONE",
  queue_for_sc_count: len(queue_for_sc),
  queue_for_wp_count: len(queue_for_wp),
  deferred_count:     len(deferred),
  max_loops_used:     max_loops
})

LOG f"[bottleneckTrigger] DONE -- sc={len(queue_for_sc)}, wp={len(queue_for_wp)}, deferred={len(deferred)}"
# [bottleneckTrigger] EXIT status=OK
RETURN exitcode=0
```

## Aufruf-Kontext

Dieser Berater wird aufgerufen von:
- `_IDF_orchestrate` Phase 3.8e (nach Phase 3.8d plBewertung, vor Phase 4 dependencyAnalyzer)
- Bei IDF Re-Entry (nach SC/WP-Return): erneuter Aufruf nach SRS-Refresh betroffener PLs (AK-7)

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| `per_pl_evaluation` fehlt | LOG + SKIP (exitcode=0, kein FAIL) |
| Alle PLs non-bottleneck | queue_for_sc=[], queue_for_wp=[], DONE |
| `bottleneck_max_loops` nicht in session_param | Default 3 verwenden |
| PL loop_count >= max_loops | DEFERRED_BOTTLENECK Status + HiL-Signal (auch bei HiL=off) |
| Re-Entry ohne bestehende loop_counts | Initialisierung auf 0 (idempotent) |

## Downstream-Integrationen

- **SDF Phase 1.1 `_SDF_berater_modusEntscheidung` (C3 SCHRITT 2.5)**: liest `bottleneck_queue` -> M5 (SC) oder M9 (WP) fuer betroffene Batches
- **SDF Phase 2.1 Dispatch**: M5 -> `_SC_orchestrate`, M9 -> `_WP_orchestrate` (BL-206 AK-4)
- **IDF Loop-Check Re-Entry** (AK-7): nach SC/WP-Return -> erneuter Aufruf dieser Phase fuer aktualisierte PLs
