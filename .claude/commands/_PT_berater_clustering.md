# _PT_berater_clustering (Pattern-Extraction Stage 2)

```yaml
type: berater
status: active
version: 1.0.0
created: 2026-06-02
op: PatternExtraction
phase: "2"
chain_position: "zweite Stage in _PT_orchestrate — nach gatherSignals, vor timeAxis"
feature_anchor: BL-237 (AK-CTX-PTO-2: CORE/BORDER-Clustering, dispatch_findings-Reuse + Adapter)
model_tier: middle  # sonnet — semantisches Clustern auf normalisierten Signalen
```

## Zweck (EIN Job)

**Clustere die normalisierte Signal-Liste semantisch in CORE und BORDER.** Stage 1 (gatherSignals) lieferte
die rohe `signals[]`-Buendelung aus 4 Quellen; diese Stage gruppiert sie nach Aehnlichkeit — CORE
(wiederkehrende, hochrelevante Lernsignale) vs. BORDER (Rand-/Einzelfall-Signale). Die Cluster sind die
Einheit, an der Stage 4/5/6 (contradiction/classify/forensic) operieren.

> **Single Unit of Work (/_help P-10):** liest EINEN Vorgaenger-Slot (.gatherSignals), clustert, schreibt
> EINEN eigenen Slot (.clustering), stirbt. Kein Klassifizieren auf 3 Achsen (→ Stage 5), keine Zeitachse
> (→ Stage 3), kein Library-Write.

## Reuse — dispatch_findings / cleancoder (+ Signal→findings-Adapter)

Das CORE/BORDER-Clustering ist dieselbe semantische Aufgabe wie der Findings-Motor (`dispatch_findings`,
BL-235: loop-until-dry → semantisches Clustering CORE/BORDER → Valenz/Pruning). Reuse statt Neubau
(INV-PTO-6):

```
ADAPTER signals[] → findings[]:
  finding = { id: signal.id, text: signal.text, ref: signal.raw_ref,
              source: signal.source, ts: signal.timestamp }
VORBEDINGUNG: mcp__cleancoder__health_check  (falls cleancoder-Reuse geplant)
  IF health_check != ok ODER cleancoder nicht verfuegbar:
    → LLM-FALLBACK: clustere inline per semantischer Aehnlichkeit (gleiche Aufgabe, ohne MCP).
```

## VERTRAG

```
LIEST:
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.gatherSignals.signals[]    (Vorgaenger-Slot — Kompass + Primaereingabe)
    BERATER_OUTPUTS_PT.gatherSignals.status        (EMPTY → leeres Clustering)
  WORKING_DIR via resolve_bl_path.py

SCHREIBT (NUR eigener Slot — INV-PTO-4 Single-Writer):
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.clustering:
      clusters: [{
        cluster_id,        # stabile Cluster-ID (z.B. CL-CORE-1, CL-BORDER-3)
        band,              # CORE | BORDER
        member_signal_ids, # [signal.id, ...] — Mitglieder dieses Clusters
        theme,             # 1-Satz-Cluster-Thema (semantischer Nenner)
        weight             # |member_signal_ids| (Cluster-Groesse als Roh-Gewicht)
      }]
      counts: {core, border, total_clusters, total_signals_clustered}
      adapter_used,        # cleancoder | dispatch_findings | llm_fallback
      status: DONE | EMPTY

  NICHT: Libraries/* , andere BERATER_OUTPUTS_PT-Slots, DF_BATCH_STATE.

INVARIANTEN:
  INV-CL-1 (Single-Writer): schreibt NUR BERATER_OUTPUTS_PT.clustering — kein Vorgaenger-Slot, kein Library.
  INV-CL-2 (Read-only-Eingabe): .gatherSignals.signals[] werden NUR gelesen, nie modifiziert.
  INV-CL-3 (Vollstaendigkeit): jedes Eingabe-Signal landet in GENAU einem Cluster (CORE oder BORDER) — keine Signal-Verluste.
  INV-CL-4 (Graceful): .gatherSignals.status==EMPTY ODER signals=[] → clusters=[], status=EMPTY, kein Fehler.
  INV-CL-5 (Reuse-not-rebuild): dispatch_findings/cleancoder-Logik via Adapter wiederverwenden; LLM-Fallback NUR wenn MCP-health_check fehlschlaegt.
```

## Aufruf

```
Skill(_PT_berater_clustering, args="{BL_ID}")
```
Aufgerufen von `_PT_orchestrate` Stage 2 (Worker-Spawn). KEIN direkter User-Aufruf.

## Ablauf

```
1. WORKING_DIR = resolve_bl_path(BL_ID); bl_folder = WORKING_DIR
   IDEMPOTENZ: IF BERATER_OUTPUTS_PT.clustering.status == DONE: RETURN (Resume-SKIP)

2. signals = manifest.BERATER_OUTPUTS_PT.gatherSignals.signals[]
   IF gatherSignals.status == EMPTY OR signals == []:
     SCHREIBE clustering = {clusters: [], counts: {0..}, status: EMPTY}; RETURN (INV-CL-4)

3. Adapter signals[] → findings[] (id/text/ref/source/ts).

4. Cluster-Strategie (INV-CL-5):
   health = mcp__cleancoder__health_check
   IF health == ok:
     clusters = cleancoder/dispatch_findings-Clustering(findings) ; adapter_used = "cleancoder"
   ELSE:
     clusters = llm_semantic_cluster(findings)                    ; adapter_used = "llm_fallback"

5. Band-Zuweisung CORE/BORDER:
   FOR cluster IN clusters:
     band = (cluster.weight >= 2 OR cluster.theme wiederkehrend) ? CORE : BORDER
   Vollstaendigkeits-Check (INV-CL-3): SUM(member_signal_ids) == |signals| sonst FEHLER.

6. counts berechnen. Schreibe BERATER_OUTPUTS_PT.clustering = {clusters, counts, adapter_used, status: DONE}.
   SendMessage team-lead: "clustering: {total_clusters} Cluster ({core} CORE / {border} BORDER) aus {total_signals_clustered} Signalen (adapter={adapter_used})"
```

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| .gatherSignals.status==EMPTY | clusters=[], status=EMPTY, SendMessage "keine Signale zu clustern" |
| cleancoder health_check != ok | LLM-Fallback (gleiche Clustering-Aufgabe inline), adapter_used=llm_fallback |
| nur 1 Signal | 1 BORDER-Cluster (weight=1), kein Fehler |

## Verwandt
- `_PT_berater_gatherSignals` (Stage 1, liefert .gatherSignals) · `_PT_berater_timeAxis` (Stage 3) ·
  `_PT_berater_contradiction` (Stage 4, konsumiert .clustering)
- `dispatch_findings` (BL-235 CORE/BORDER-Motor, Reuse-Quelle) · BL-237 Anschluss (Stage 2 clustering)
