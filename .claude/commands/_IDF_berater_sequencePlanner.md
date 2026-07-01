---
status: active
version: 0.2.0
type: berater
parent: _IDF_orchestrate
phase: phase_6
model_tier: middle
created: 2026-04-25
feature_anchor: BL-142
optional: false
absorbs: _SDF_berater_sequencePlanner
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.clustering", purpose: "Cluster-Liste"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.dependencyAnalyzer", purpose: "DAG fuer Topo-Sort"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "Per-Item Reifegrad", purpose: "Reife-Gewicht im Sort"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.sequencePlanner", purpose: "Topo-Sort flat list"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser sequencePlanner)"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "(read-only)"}
  calls: []
---

# _IDF_berater_sequencePlanner (Phase 6 in _IDF_orchestrate)

> **Zweck:** Topo-Sort der PL-Items als flache Liste — Eingang fuer batchPlan. Absorbiert SDF-Berater.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_sequencePlanner                               |
+======================================================================+
|  LIEST:                                                              |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      BERATER_OUTPUTS.clustering (Cluster-Liste)                      |
|      BERATER_OUTPUTS.dependencyAnalyzer (DAG)                        |
|    {VAULT}/Backlog/{bl_slug}/6_PL/                       |
|      {bl_id}-parking-lot.md (Reifegrad pro Item)                    |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      BERATER_OUTPUTS.sequencePlanner = {                             |
|        ordered_items[], topology_pass, total_items                  |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser sequencePlanner)                        |
|    PL-Items / DAG / Cluster (read-only)                              |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 6 (absorbiert SDF-Berater)            |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Topo-Sort + Reife-Gewicht. Standard-Algorithmus,    |
|    keine Reasoning-Tiefe.                                           |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-SQ-1: Topo-Order respektiert blocked_by                      |
|    INV-SQ-2: Bei DAG-Cycle FAIL (delegiert an depAnalyzer)          |
|    INV-SQ-3: Schreib-Isolation auf BERATER_OUTPUTS.sequencePlanner   |
|    INV-SQ-DEFER-1 (BL-304 AK-3): Defer-markierte PL-Items ([~] ODER  |
|      DEFER-Token) erscheinen NICHT in ordered_items (vor Sort        |
|      gefiltert + final aus sorted_basis ausgeschlossen via           |
|      pl_defer_filter). NICHT geloescht — nur aktive Batch-Formation. |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - dependencyAnalyzer done, cycles[] = []                          |
|    - clustering done                                                 |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - BERATER_OUTPUTS.sequencePlanner vollstaendig                    |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_sequencePlanner, args="{NAME}")

Parameter:
  {NAME} - Feature-Name oder bl_id

Ausgabe:
  - BERATER_OUTPUTS.sequencePlanner
  - Exitcode: 0=OK, 2=FAIL (Cycle erkannt)

Logging-Format:
  [IDF_SEQ] ENTRY name={NAME} nodes={n}
  [IDF_SEQ] EXIT duration={ms}ms ordered={n}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  sequencePlanner:
    ordered_items: ["BL-142-PL-1", "BL-142-PL-2", "BL-142-PL-3"]
    topology_pass: true
    total_items: 3
    last_berater: "sequencePlanner"
```

## Logik

```
SCHRITT 0: Entry-Log + Vorbedingungen
  Logge: "[IDF_SEQ] ENTRY name={NAME}"
  manifest = Read({WORKING_DIR}/_manifest.md)
  dep = manifest.BERATER_OUTPUTS.dependencyAnalyzer
  cl = manifest.BERATER_OUTPUTS.clustering
  IF dep == null OR cl == null:
    FAIL: "dependencyAnalyzer ODER clustering fehlt"
  IF |dep.cycles| > 0:
    FAIL: "DAG-Cycle vorhanden ({|dep.cycles|}). sequencePlanner kann nicht topo-sortieren."

  pl_items = parse_pl_items(Read("{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"))

SCHRITT 0.5: Defer-Exclusion (BL-304 AK-3 — INV-SQ-DEFER-1)
  # Defer-markierte PL-Items ([~] ODER DEFER-Token) gehoeren NICHT in die aktive
  # Sequenz/Batch — sie bleiben im PL fuer eine spaetere/eigene Runde (NICHT loeschen).
  # Kanonischer Filter: .claude/scripts/pl_defer_filter.py -> filter_active_batch_items.
  # KONSERVATIV: nur eindeutige Defer-Marker, kein Ueber-Filter von [ ]/[x].
  active_items = filter_active_batch_items(pl_items)
  defer_ids = {p.id FOR p in pl_items} - {p.id FOR p in active_items}
  pl_items = active_items
  Logge: "[IDF_SEQ] DEFER-FILTER active={|active_items|} excluded={|defer_ids|} (BL-304 AK-3)"

SCHRITT 1: Kahn-Topo-Sort (Standard)
  in_degree = compute_in_degrees(dep.nodes, dep.hard_edges)
  queue = [n FOR n in dep.nodes IF in_degree[n] == 0]
  sorted_basis = []

  WHILE |queue| > 0:
    # Tie-Break (INV-SQ-1, INV-SQ-2): hier sortieren
    queue = sort(queue, key=tie_break_key)
    n = queue.pop(0)
    sorted_basis.append(n)
    FOR neighbor in successors(n, dep.hard_edges):
      in_degree[neighbor] -= 1
      IF in_degree[neighbor] == 0:
        queue.append(neighbor)

  IF |sorted_basis| != |dep.nodes|:
    FAIL: "Topo-Sort unvollstaendig — versteckter Cycle?"

SCHRITT 2: tie_break_key(node) Funktion
  def tie_break_key(n):
    item = pl_items.find(p => p.id == n)
    # Primaer: Reifegrad (REIF=0 vor sonst=1)
    primary = 0 IF item.reifegrad == "REIF" ELSE 1
    # Sekundaer: Cluster-Naehe (gleicher Cluster wie letztes sorted_basis -> bevorzugt)
    last_cluster = cluster_of(sorted_basis[-1]) IF |sorted_basis| > 0 ELSE null
    secondary = 0 IF cluster_of(n) == last_cluster ELSE 1
    # Tertiaer: k_score (klein zuerst)
    tertiary = item.k_score_pl OR 100
    return (primary, secondary, tertiary)

  def cluster_of(node_id):
    FOR c in cl.clusters:
      IF node_id in c.items:
        return c.id
    return null

SCHRITT 3: Output (INV-SQ-3, INV-SQ-DEFER-1)
  # Defer-Item-ids final aus der geordneten Liste ausschliessen (die DAG-Nodes koennen
  # ein defer-Item enthalten — der aktive Batch-Eingang darf es NICHT). BL-304 AK-3.
  ordered_active = [n FOR n in sorted_basis IF n NOT IN defer_ids]
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.sequencePlanner = {
    ordered_items: ordered_active,
    topology_pass: true,
    total_items: |ordered_active|,
    last_berater: "sequencePlanner"
  })

SCHRITT 4: Exit
  Logge: "[IDF_SEQ] EXIT duration={ms}ms ordered={|sorted_basis|}"
  EXIT 0
```

## Begruendung Modell-Tier

sonnet — Standard-Algorithmus + Tie-Break. Kein Reasoning.
