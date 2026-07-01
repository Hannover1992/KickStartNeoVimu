---
status: active
version: 0.2.0
type: berater
parent: _IDF_orchestrate
phase: phase_5
model_tier: middle
created: 2026-04-25
feature_anchor: BL-142
optional: false
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.dependencyAnalyzer", purpose: "DAG-Matrix als Cluster-Eingang"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items (k_score, file_refs)", purpose: "Cluster-Heuristik-Inputs"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.clustering", purpose: "Cluster + Mitose-Signal"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser clustering)"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "(read-only)"}
  calls: []
---

# _IDF_berater_clustering (Phase 5 in _IDF_orchestrate)

> **Zweck:** PL-Items in Clusters gruppieren (Datei-Naehe / Modul-Naehe), Mitose-Signal ableiten.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_clustering                                    |
+======================================================================+
|  LIEST:                                                              |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      BERATER_OUTPUTS.dependencyAnalyzer (nodes, edges)               |
|    {VAULT}/Backlog/{bl_slug}/6_PL/                       |
|      {bl_id}-parking-lot.md (k_score, file_refs)                    |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      BERATER_OUTPUTS.clustering = {                                  |
|        clusters[], cluster_aggregates[], mitose_signal               |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser clustering)                             |
|    PL-Items / DAG (read-only)                                        |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 5 (Cluster-Aggregate)                 |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Heuristik (Datei-Naehe, k_score-Mean) +             |
|    Cluster-Aggregat. Kein Volltext-Reasoning.                       |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-CL-1: Jeder Node in genau einem Cluster                      |
|    INV-CL-2: mitose_signal=true bei aggregat_k >= 70                |
|    INV-CL-3: Schreib-Isolation auf BERATER_OUTPUTS.clustering       |
|    INV-CL-DEFER-1 (BL-304 AK-3): Defer-markierte PL-Items ([~] ODER |
|      DEFER-Token) werden VOR dem Clustern aus der aktiven Auswahl    |
|      gefiltert (pl_defer_filter.filter_active_batch_items). NICHT    |
|      geloescht — nur aus aktiver Batch-Formation. Kein Ueber-Filter  |
|      von [ ]/[x]. Orthogonal zum Modus (INV-MODUS-1 unberuehrt).     |
|    INV-CL-HETERO-1 (BL-304 AK-1/AK-2): Ein effort-HETEROGENER        |
|      Cluster (k_max>=15 UND eine triviale Teilmenge k<15 existiert)  |
|      wird VOR der Batch-Schnitt-Finalisierung in trivial/rigorous    |
|      Sub-Cluster getrennt (pl_effort_split.split_by_effort_class,    |
|      threshold=15 = die M1-MULTI-Decke). So kommen homogene Batches  |
|      bei modusEntscheidung an -> der UNVERAENDERTE k_max<15-Gate     |
|      feuert fuer die triviale Mehrheit (schliesst die [15,80)-Luecke |
|      die BL-279/split-at-80 NICHT abdeckt). Homogene Cluster bleiben |
|      unveraendert (kein unnoetiger Split). Orthogonal zum Modus      |
|      (INV-MODUS-1 unberuehrt — Split ist upstream, nicht im Gate).   |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - dependencyAnalyzer done                                         |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - BERATER_OUTPUTS.clustering vollstaendig                         |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_clustering, args="{NAME}")

Parameter:
  {NAME} - Feature-Name oder bl_id

Ausgabe:
  - BERATER_OUTPUTS.clustering
  - Exitcode: 0=OK, 1=MITOSE_HINT, 2=FAIL

Logging-Format:
  [IDF_CL] ENTRY name={NAME} nodes={n}
  [IDF_CL] EXIT duration={ms}ms clusters={c} mitose={bool}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  clustering:
    clusters:
      - {id: "C-1", items: ["BL-142-PL-1", "BL-142-PL-2"]}
    cluster_aggregates:
      - {cluster_id: "C-1", k_score_mean: 35, items_count: 2}
    mitose_signal: false
    last_berater: "clustering"
```

## Logik

```
SCHRITT 0: Entry-Log + Vorbedingung
  Logge: "[IDF_CL] ENTRY name={NAME}"
  manifest = Read({WORKING_DIR}/_manifest.md)
  dep = manifest.BERATER_OUTPUTS.dependencyAnalyzer
  IF dep == null:
    FAIL: "dependencyAnalyzer fehlt"
  pl_items = parse_pl_items(Read("{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"))

SCHRITT 0.5: Defer-Exclusion (BL-304 AK-3 — INV-CL-DEFER-1)
  # Ein als Defer markiertes PL-Item ([~] ODER DEFER-Token im Text) darf NICHT in die
  # aktive Batch-Formation geclustert werden — es bleibt im PL fuer eine spaetere/eigene
  # Runde (NICHT loeschen, nur aus aktiver Auswahl filtern). Live-Fall DCSRE-486 batch_PL23:
  # T2076 war [~] DEFER ("eigener Batch"), blieb aber im Cluster -> inflationierte k_max ->
  # erzwang M2 fuer alle 11 Items statt M1-MULTI fuer die trivialen.
  # Kanonischer Filter (EINE Wahrheit, nicht 3 divergente Inline-Filter):
  #   .claude/scripts/pl_defer_filter.py -> filter_active_batch_items(items)
  #   Defer == Status-Marker [~] ODER DEFER-Token (Wort-Grenze). KONSERVATIV: [ ]/[x]
  #   werden NICHT angefasst (kein Ueber-Filter). Orthogonal zum Modus (INV-MODUS-1 unberuehrt).
  pl_items = filter_active_batch_items(pl_items)   # pl_defer_filter.filter_active_batch_items
  Logge: "[IDF_CL] DEFER-FILTER active={|pl_items|} (defer-markierte ausgeschlossen, BL-304 AK-3)"

SCHRITT 1: Primaere Heuristik — Datei-Naehe-Gruppen
  # Items mit >= 2 gemeinsamen file_refs landen im selben Cluster
  clusters_by_files = group_by_file_overlap(pl_items, threshold=2)

SCHRITT 2: Sekundaer — DAG-Connected-Components
  # Items, die uber harte Edges verbunden sind, fallen tendentiell zusammen
  components = connected_components(dep.nodes, dep.hard_edges)

SCHRITT 3: Cluster-Synthese (Datei-Naehe gewinnt bei Konflikt)
  clusters = []
  c_counter = 0
  assigned = set()
  FOR file_group in clusters_by_files:
    c_counter += 1
    cluster_id = "C-{c_counter}"
    items = file_group
    clusters.append({id: cluster_id, items: items})
    assigned.update(items)

  # Restliche Items (kein File-Overlap) ueber DAG-Components
  FOR comp in components:
    unassigned = [i for i in comp if i not in assigned]
    IF |unassigned| > 0:
      c_counter += 1
      clusters.append({id: "C-{c_counter}", items: unassigned})
      assigned.update(unassigned)

  # Singletons (uebrig)
  FOR item in pl_items:
    IF item.id not in assigned:
      c_counter += 1
      clusters.append({id: "C-{c_counter}", items: [item.id]})

SCHRITT 3.5: Effort-Homogenisierung (BL-304 AK-1/AK-2 — INV-CL-HETERO-1)
  # Datei-Naehe-Clusterung (SCHRITT 1-3) gruppiert NUR nach Datei-Naehe + DAG, NIE nach
  # Aufwands-Klassen-Homogenitaet. Folge: ein Cluster kann 10 triviale Items (k<15) + 1
  # schweres (k>=15) enthalten -> k_max>=15 -> die M1-MULTI-Lane in modusEntscheidung
  # (Z429: k_score_max<15) faellt aus -> der GANZE Cluster wird M2, obwohl 10/11 trivial.
  # BL-279 splittet erst bei k_max>=80; die Luecke [15,80) hat KEINEN Split. Live-Fall
  # DCSRE-486 batch_PL23 (k_avg=12.5, 1x M-sized T2076 k>=15 -> ganzer Batch M2).
  #
  # FIX: hier UPSTREAM splitten (wo per-Item-k lebt), NICHT in modusEntscheidung (RED-Zone,
  # INV-MODUS-1/INV-VEHIKEL-2 — der Gate-Code bleibt byte-identisch). Ein heterogener Cluster
  # wird in einen trivial- + einen rigorous-Sub-Cluster getrennt, BEVOR die Aggregate (S4)
  # berechnet und der Batch-Schnitt finalisiert wird. So kommt der trivial-Sub-Cluster mit
  # k_max<15 bei modusEntscheidung an -> der unveraenderte k_max<15-Gate feuert korrekt.
  #
  # Kanonischer Primitiv (EINE Wahrheit, wie pl_defer_filter fuer AK-3):
  #   .claude/scripts/pl_effort_split.py
  #     is_heterogeneous(items, threshold=15)     -> True gdw. k_max>=15 UND ∃ k<15
  #     split_by_effort_class(items, threshold=15) -> {"trivial": [k<15], "rigorous": [k>=15]}
  #   threshold=15 = die EXISTIERENDE M1-MULTI-Decke (KEIN neuer Magic-Number).
  #   Komponiert MIT dem AK-3-Defer-Filter (laeuft auf den schon defer-gefilterten Items).
  #   None-k_score-Items -> konservativ rigorous (Aufwand nicht als trivial bewiesen).
  homogenized = []
  c_split_counter = c_counter
  FOR c in clusters:
    cluster_items = [pl FOR pl in pl_items IF pl.id in c.items]
    IF is_heterogeneous(cluster_items, threshold=15):   # pl_effort_split.is_heterogeneous
      buckets = split_by_effort_class(cluster_items, threshold=15)  # pl_effort_split.split_by_effort_class
      # trivial-Sub-Cluster behaelt die Cluster-id; rigorous bekommt ein -R-Suffix
      # (eindeutige neue id, INV-CL-1 — jeder Node bleibt in genau EINEM (Sub-)Cluster).
      homogenized.append({id: c.id, items: [pl.id FOR pl in buckets["trivial"]]})
      c_split_counter += 1
      homogenized.append({id: "C-{c_split_counter}", items: [pl.id FOR pl in buckets["rigorous"]]})
      Logge: "[IDF_CL] HETERO-SPLIT {c.id} -> trivial={|buckets['trivial']|} + rigorous={|buckets['rigorous']|} (BL-304 AK-1, threshold=15)"
    ELSE:
      # Homogen (alle <15 ODER alle >=15/None) -> unveraendert (AK-4: kein unnoetiger Split).
      homogenized.append(c)
  clusters = [c FOR c in homogenized IF |c.items| > 0]   # leere Sub-Cluster verwerfen
  c_counter = c_split_counter

SCHRITT 4: Cluster-Aggregate berechnen (Hint-Charakter, RF-IDF5)
  cluster_aggregates = []
  FOR c in clusters:
    cluster_items = [pl for pl in pl_items IF pl.id in c.items]
    k_scores = [pl.k_score_pl FOR pl in cluster_items IF pl.k_score_pl != null]
    cluster_aggregates.append({
      cluster_id: c.id,
      k_score_mean: |k_scores| > 0 ? mean(k_scores) : null,
      items_count: |c.items|,
      model_refs_cluster: union(flatten([pl.model_refs FOR pl in cluster_items])),
      layer: most_common_layer([pl.layer FOR pl in cluster_items])
    })

SCHRITT 5: Mitose-Signal (INV-CL-2; BL-279: k_max-Extrem zusaetzlich)
  cluster_ks = [ca.k_score_mean FOR ca in cluster_aggregates IF ca.k_score_mean != null]
  agg_k = mean(cluster_ks)
  max_k = max(cluster_ks) IF cluster_ks else null
  # BL-279 (batch_3-Lehre): NICHT nur der Durchschnitt — ein einzelnes Extrem-Cluster (k_max) ist auch ein
  # Schnitt-Signal (batch_3 hatte agg_k=60.5 < 70, aber k_max=100). Die verify_mode-Homogenitaet wird
  # downstream bewertet (testSearch het-Flag → modusEntscheidung SCHRITT 7); ABER: nur INTER-AK-Heterogenitaet
  # loest split_required=true aus (BL-456 INV-SPLIT-SCOPE-1). INTRA-AK-Heterogenitaet (Script+Doc desselben AK,
  # per Re-Cut unaufloesbar) → KEIN split → C3 faehrt Misch-Modus im selben Batch. Clustering clustert weiter
  # nach Datei-Kohaesion; der Scope-Entscheid (intra vs inter) faellt Consumer-seitig in C3 SCHRITT 7.
  # hier das Groessen-Signal an den Plan-Schnitt.
  mitose_signal = (agg_k != null AND agg_k >= 70) OR (max_k != null AND max_k >= 80)
  IF mitose_signal:
    Logge: "[IDF_CL] MITOSE_HINT agg_k={agg_k} max_k={max_k} (BL-279: agg>=70 ODER max>=80)"

SCHRITT 6: Output (INV-CL-1, INV-CL-3)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.clustering = {
    clusters: clusters,
    cluster_aggregates: cluster_aggregates,
    mitose_signal: mitose_signal,
    last_berater: "clustering"
  })

SCHRITT 7: Exit
  exitcode = mitose_signal ? 1 : 0
  Logge: "[IDF_CL] EXIT duration={ms}ms clusters={c} mitose={mitose_signal}"
  EXIT exitcode
```

## Begruendung Modell-Tier

sonnet — Heuristik + Standard-Aggregation. Kein Reasoning-Bedarf.
