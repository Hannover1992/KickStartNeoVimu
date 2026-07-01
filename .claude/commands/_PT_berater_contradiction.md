# _PT_berater_contradiction (Pattern-Extraction Stage 4)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-02
op: PatternExtraction
phase: "4"
chain_position: "vierte Stage in _PT_orchestrate — nach timeAxis, vor classify"
feature_anchor: BL-237 (AK-CTX-PTO-4: Widersprueche/zurueckgebaute Signale isolieren — das DASS)
model_tier: middle  # sonnet — Cluster x TimeAxis kombinieren
```

## Zweck (EIN Job)

**Isoliere die widerspruechlichen und zurueckgebauten Signale** — durch Kombination der Cluster (Stage 2)
mit der Zeitachse (Stage 3). Ergebnis ist die Menge der Signale, deren Pattern-Aussage spaeter revidiert
oder zurueckgebaut wurde. Diese Stage liefert das **DASS** (welche Signale sind contested), **NICHT das
WARUM** — die Hypothesen-Bildung macht Stage 6 (forensic).

> **Single Unit of Work (/_help P-10):** liest .clustering + .timeAxis, isoliert die contested Items,
> schreibt EINEN eigenen Slot (.contradiction), stirbt. Keine Forensik (→ Stage 6), keine Klassifikation
> (→ Stage 5), kein Library-Write.

## VERTRAG

```
LIEST:
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.clustering.clusters[]       (CORE/BORDER-Cluster + member_signal_ids)
    BERATER_OUTPUTS_PT.timeAxis.timeline[]         (temporale Ordnung)
    BERATER_OUTPUTS_PT.timeAxis.reverts_raw[]      (roh markierte Reverts)
  WORKING_DIR via resolve_bl_path.py

SCHREIBT (NUR eigener Slot — INV-PTO-4 Single-Writer):
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.contradiction:
      items: [{
        contradiction_id, # stabile ID (z.B. CTR-1)
        kind,             # reverted | superseded | conflicting   (das DASS, nicht das WARUM)
        cluster_id,       # betroffener Cluster (aus .clustering)
        signal_ids,       # [signal.id, ...] — die contested Signale
        revert_ref,       # Bezug zu timeAxis.reverts_raw (falls reverted) oder null
        evidence          # 1-Satz: WORAN man den Widerspruch sieht (rein faktisch)
      }]
      counts: {reverted, superseded, conflicting, total}
      status: DONE | EMPTY

  NICHT: Libraries/* , andere BERATER_OUTPUTS_PT-Slots, DF_BATCH_STATE.

INVARIANTEN:
  INV-CTR-1 (Single-Writer): schreibt NUR BERATER_OUTPUTS_PT.contradiction.
  INV-CTR-2 (DASS-nicht-WARUM): items enthalten NUR die Tatsache des Widerspruchs + faktische Evidenz — KEINE Hypothese/Deutung (das ist Stage 6 forensic).
  INV-CTR-3 (Quellen-Kombination): jedes item referenziert mind. einen cluster_id (Stage 2) UND nutzt timeAxis (Stage 3) — keine Widerspruchs-Isolierung ohne Zeitbezug.
  INV-CTR-4 (Graceful): leere clustering ODER leere timeAxis → items=[], status=EMPTY, kein Fehler.
```

## Aufruf

```
Skill(_PT_berater_contradiction, args="{BL_ID}")
```
Aufgerufen von `_PT_orchestrate` Stage 4 (Worker-Spawn). KEIN direkter User-Aufruf.

## Ablauf

```
1. WORKING_DIR = resolve_bl_path(BL_ID); bl_folder = WORKING_DIR
   IDEMPOTENZ: IF BERATER_OUTPUTS_PT.contradiction.status == DONE: RETURN (Resume-SKIP)

2. clusters = .clustering.clusters[]; timeline = .timeAxis.timeline[]; reverts = .timeAxis.reverts_raw[]
   IF clusters == [] OR (timeline == [] AND reverts == []):
     SCHREIBE contradiction={items:[], status:EMPTY}; RETURN (INV-CTR-4)

3. reverted (INV-CTR-2 — rein DASS):
   FOR r IN reverts:
     cl = cluster_of(r.related_signal_ids)
     items.append({kind:reverted, cluster_id:cl.cluster_id, signal_ids:r.related_signal_ids,
                   revert_ref:r.revert_ref, evidence:"in timeAxis als revert_raw markiert ({r.source})"})

4. superseded / conflicting:
   FOR cl IN clusters:
     # zwei Signale desselben Clusters mit gegenlaeufiger Aussage in temporaler Folge
     IF temporal_conflict(cl.member_signal_ids, timeline):
       items.append({kind:(later_wins? superseded : conflicting), cluster_id:cl.cluster_id,
                     signal_ids:[...], revert_ref:null, evidence:"temporale Gegenlaeufigkeit in Cluster {cl.cluster_id}"})

5. counts berechnen. Schreibe BERATER_OUTPUTS_PT.contradiction = {items, counts, status: DONE}.
   SendMessage team-lead: "contradiction: {total} contested ({reverted} reverted / {superseded} superseded / {conflicting} conflicting) — DASS isoliert, WARUM -> forensic"
```

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| keine Reverts in timeAxis | nur superseded/conflicting via Cluster-Temporal-Check |
| keine temporalen Konflikte | items aus reverts allein |
| alles leer | status=EMPTY, SendMessage "keine Widersprueche isoliert" |

## Verwandt
- `_PT_berater_clustering` (Stage 2) · `_PT_berater_timeAxis` (Stage 3) — beide Eingaben ·
  `_PT_berater_forensic` (Stage 6, deutet das WARUM) · BL-237 Revert-Detection (Anschluss 5)
