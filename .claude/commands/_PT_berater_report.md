# _PT_berater_report (Pattern-Extraction Stage 8)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-02
op: PatternExtraction
phase: "8"
chain_position: "achte/letzte Stage in _PT_orchestrate — nach materialize, terminal"
feature_anchor: BL-237 (AK-CTX-PTO-8: Sichtbarkeits-Report; speist AK-8 /_pattern_status Dashboard)
model_tier: middle  # sonnet — Aggregation + Report-Formatierung
```

## Zweck (EIN Job)

**Aggregiere den Harvest-Lauf zu einem Sichtbarkeits-Report.** Aus `.materialize` (was angelegt/gereift/
retired wurde) plus dem Lauf-Kontext (deferred/pending) entsteht eine kompakte Bilanz: was wurde
materialisiert, gereift, contested, retired — plus was noch pending ist (quiescenz-deferred /
WORTHINESS-pending). Diese Aggregation ist die Datenquelle fuer das AK-8 `/_pattern_status`-Dashboard.

> **Single Unit of Work (/_help P-10):** liest alle Vorgaenger-Slots (primaer .materialize), aggregiert,
> schreibt EINEN eigenen Slot (.report), stirbt. Kein Library-Write, keine Materialisierung.

## VERTRAG

```
LIEST:
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.materialize.{created,updated,retired,deferred_busy,worthiness_pending}  (primaer)
    BERATER_OUTPUTS_PT.gatherSignals.counts                 (Roh-Eingangs-Volumen fuer Yield)
    BERATER_OUTPUTS_PT.clustering.counts                    (CORE/BORDER)
    BERATER_OUTPUTS_PT.contradiction.counts                 (contested)
    BERATER_OUTPUTS_PT.forensic.counts                      (broken-Kandidaten)
    PT_EXTRACT_STATE.stage_done[]                           (welche Stages liefen)
  WORKING_DIR via resolve_bl_path.py

SCHREIBT (NUR eigener Slot — INV-PTO-4 Single-Writer):
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.report:
      materialized,        # |materialize.created|
      matured,             # |materialize.updated WHERE lifecycle_path=pfad-1| (Reifung)
      contested,           # |contradiction.items| (DASS) bzw. forensic broken-Kandidaten
      retired,             # |materialize.retired|
      pending: {
        quiescenz_deferred,    # materialize.deferred_busy
        worthiness_pending     # materialize.worthiness_pending (batch_C5 Seam)
      }
      yield_ratio,         # materialized / gatherSignals.total (Anti-95%-Leak-Metrik, 486-Lehre)
      stages_run,          # PT_EXTRACT_STATE.stage_done
      summary_line,        # 1-Zeilen-Bilanz (auch fuer Orchestrator Phase 9)
      status: DONE | EMPTY

  NICHT: Libraries/* , andere BERATER_OUTPUTS_PT-Slots, DF_BATCH_STATE.

INVARIANTEN:
  INV-REP-1 (Single-Writer): schreibt NUR BERATER_OUTPUTS_PT.report.
  INV-REP-2 (read-only-Aggregation): aggregiert NUR Vorgaenger-Slots — modifiziert keinen davon, schreibt keine Library.
  INV-REP-3 (Pending-Transparenz): quiescenz_deferred + worthiness_pending werden IMMER ausgewiesen (kein stilles Verschweigen offener Arbeit).
  INV-REP-4 (Graceful): leeres materialize → alle Zaehler 0, status=EMPTY (gueltiger Leer-Report).
```

## Aufruf

```
Skill(_PT_berater_report, args="{BL_ID}")
```
Aufgerufen von `_PT_orchestrate` Stage 8 (Worker-Spawn). KEIN direkter User-Aufruf.

## Ablauf

```
1. WORKING_DIR = resolve_bl_path(BL_ID); bl_folder = WORKING_DIR
   IDEMPOTENZ: IF BERATER_OUTPUTS_PT.report.status == DONE: RETURN (Resume-SKIP)

2. mat = .materialize ?? {created:[], updated:[], retired:[]}
   gs  = .gatherSignals.counts ?? {total:0}
   IF mat leer AND gs.total == 0: SCHREIBE report={...0..., status:EMPTY}; RETURN (INV-REP-4)

3. Aggregation:
   materialized = |mat.created|
   matured      = |mat.updated WHERE lifecycle_path == pfad-1|
   contested    = .contradiction.counts.total ?? 0
   retired      = |mat.retired|
   yield_ratio  = (gs.total > 0) ? materialized / gs.total : 0    # Anti-95%-Leak-Metrik

4. Pending-Transparenz (INV-REP-3):
   pending = {quiescenz_deferred: mat.deferred_busy ?? false,
              worthiness_pending: mat.worthiness_pending ?? false}

5. summary_line = "PT-Harvest {BL_ID}: {materialized} materialisiert / {matured} gereift / {contested} contested / {retired} retired (yield {yield_ratio}); pending: quiescenz={pending.quiescenz_deferred}, worthiness={pending.worthiness_pending}"

6. Schreibe BERATER_OUTPUTS_PT.report = {materialized, matured, contested, retired, pending, yield_ratio, stages_run, summary_line, status: DONE}.
   SendMessage team-lead: summary_line
```

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| materialize=DEFERRED_BUSY | report mit materialized=0, pending.quiescenz_deferred=true (zeigt: Ernte wartet auf Quiescenz) |
| leeres materialize | status=EMPTY, yield_ratio=0 (gueltiger Leer-Report) |
| nur Teil-Stages gelaufen | stages_run zeigt genau die gelaufenen Stages (Transparenz bei BUSY-SKIP/Resume) |

## Verwandt
- `_PT_berater_materialize` (Stage 7, liefert .materialize) · `_PT_orchestrate` (Phase 9 Verdikt nutzt summary_line) ·
  `/_pattern_status` (AK-8 Dashboard, konsumiert .report — batch-spaeter) · BL-237 Sichtbarkeit (Anschluss / AK-8)
