---
status: active
version: 0.2.0
type: berater
parent: _IDF_orchestrate
phase: phase_4
model_tier: middle
created: 2026-04-25
feature_anchor: BL-142
optional: false
absorbs: _SDF_berater_dependencyAnalyzer
contract:
  reads:
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items + Frontmatter", purpose: "Dependencies + Datei-Refs"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.plAggregation", purpose: "PL-Aggregat-Anchor"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.per_pl_evaluation", purpose: "Optional: k_score pro PL-Item fuer Dep-Gewichtung (BL-203 AK-7). Bottleneck-PLs (k_score=null) erhalten niedrigere Dep-Prioritaet."}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.dependencyAnalyzer", purpose: "DAG-Matrix + Mermaid"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser dependencyAnalyzer)"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "(read-only)"}
  calls: []
---

# _IDF_berater_dependencyAnalyzer (Phase 4 in _IDF_orchestrate)

> **Zweck:** PL-Items in DAG-Matrix abbilden, Mermaid-Diagramm ableiten. Absorbiert SDF-Berater.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_dependencyAnalyzer                            |
+======================================================================+
|  LIEST:                                                              |
|    {VAULT}/Backlog/{bl_slug}/6_PL/                       |
|      {bl_id}-parking-lot.md (PL-Items, blocked_by, file_refs)       |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      BERATER_OUTPUTS.plAggregation (Aggregat-Anchor)                 |
|      DF_BATCH_STATE.per_pl_evaluation (Optional, BL-203 AK-7)       |
|        k_score pro PL-Item fuer Dep-Gewichtung:                      |
|        Bottleneck-PLs (k_score=null) → niedrigere Dep-Prioritaet    |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      BERATER_OUTPUTS.dependencyAnalyzer = {                          |
|        nodes[], edges[], cycles[],                                   |
|        mermaid_text, file_refs_total                                 |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser dependencyAnalyzer)                     |
|    PL-Items selbst (read-only)                                       |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 4 (absorbiert SDF-Berater)            |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Listen-Aggregation + Topo-Verifikation +            |
|    Mermaid-Generierung. Sonnet ausreichend.                         |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-DA-1: Cycle-Detection — cycles[] FAIL-Loud bei Zyklus        |
|    INV-DA-2: nodes-Deduplikation                                     |
|    INV-DA-3: Schreib-Isolation auf BERATER_OUTPUTS.dependencyAna...  |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - plAggregation done                                              |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - BERATER_OUTPUTS.dependencyAnalyzer vollstaendig                 |
|    - Bei cycles[]: Pruning-Hint fuer downstream                      |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_dependencyAnalyzer, args="{NAME}")

Parameter:
  {NAME} - Feature-Name oder bl_id

Ausgabe:
  - BERATER_OUTPUTS.dependencyAnalyzer
  - Exitcode: 0=OK, 1=CYCLES_FOUND, 2=FAIL

Logging-Format:
  [IDF_DEP] ENTRY name={NAME}
  [IDF_DEP] EXIT duration={ms}ms nodes={n} edges={k} cycles={c}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  dependencyAnalyzer:
    nodes: ["BL-142-PL-1", "BL-142-PL-2"]
    edges:
      - {from: "BL-142-PL-2", to: "BL-142-PL-1"}
    cycles: []
    mermaid_text: "graph TD\n  BL-142-PL-1\n  BL-142-PL-2 --> BL-142-PL-1"
    file_refs_total: 23
    last_berater: "dependencyAnalyzer"
```

## Logik

```
SCHRITT 0: Entry-Log + Vorbedingung
  Logge: "[IDF_DEP] ENTRY name={NAME}"
  manifest = Read({WORKING_DIR}/_manifest.md)
  bl_id = manifest.IDF_PIPELINE_STATE.bl_id
  bl_slug = manifest.IDF_PIPELINE_STATE.bl_slug
  pl_path = "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"

SCHRITT 1: PL-Items lesen + Nodes ableiten (INV-DA-2 Deduplikation)
  pl_content = Read(pl_path)
  pl_items = parse_pl_items(pl_content)
  nodes = unique([i.id FOR i in pl_items])
  file_refs_total = sum([|i.dateien_geplant| FOR i in pl_items])

SCHRITT 2: Edges aus blocked_by + dependencies + Datei-Naehe
  edges = []
  # explizite Dependencies
  FOR item in pl_items:
    FOR dep in (item.blocked_by + item.dependencies):
      # nur PL-IDs zaehlen (AK-Refs gehen nicht ins DAG)
      IF dep startswith "{bl_id}-PL-":
        edges.append({from: item.id, to: dep})

  # impliziter Datei-Naehe-Hinweis (INFO, nicht hart)
  FOR i in pl_items:
    FOR j in pl_items WHERE j.id != i.id:
      shared = intersect(i.dateien_geplant, j.dateien_geplant)
      IF |shared| >= 2:
        edges.append({from: i.id, to: j.id, kind: "soft_file_proximity"})

SCHRITT 3: Cycle-Detection via DFS (INV-DA-1 FAIL-Loud)
  # nur harte Edges (kind != soft_*) zaehlen fuer DAG-Pruefung
  hard_edges = [e FOR e in edges IF e.kind != "soft_file_proximity"]
  cycles = detect_cycles_dfs(nodes, hard_edges)
  IF |cycles| > 0:
    Logge: "[IDF_DEP] WARN cycles_found={|cycles|}"
    # nicht abbrechen — sequencePlanner muss das spaeter handhaben

SCHRITT 4: Mermaid generieren
  mermaid_text = "graph TD\n"
  FOR node in nodes:
    mermaid_text += "  {node}\n"
  FOR e in hard_edges:
    mermaid_text += "  {e.from} --> {e.to}\n"
  FOR e in soft_edges:
    mermaid_text += "  {e.from} -.-> {e.to}\n"  # gestrichelt fuer soft

SCHRITT 5: Output (INV-DA-3 Schreib-Isolation)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.dependencyAnalyzer = {
    nodes: nodes,
    edges: edges,
    cycles: cycles,
    mermaid_text: mermaid_text,
    file_refs_total: file_refs_total,
    last_berater: "dependencyAnalyzer"
  })

SCHRITT 6: Exit
  exitcode = |cycles| > 0 ? 1 : 0
  Logge: "[IDF_DEP] EXIT duration={ms}ms nodes={n} edges={k} cycles={c}"
  EXIT exitcode
```

## Begruendung Modell-Tier

sonnet — Listen-Aggregation, Standard-Algorithmus (DFS), Mermaid-Output. Kein Reasoning-Bedarf.
