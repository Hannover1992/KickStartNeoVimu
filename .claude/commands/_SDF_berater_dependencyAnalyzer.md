---
status: deprecated
version: 1.0
created: 2026-04-25
type: berater
parent: _SDF_orchestrate
model_tier: middle
floor: sonnet
ceiling: opus
feature: BL-134
ak_implements: [AK-2, AK-6, AK-13]
contract:
  reads:
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items[*].frontmatter.blocked_by", purpose: "DAG-Aufbau aus blocked_by-Kanten"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items", purpose: "Aktueller Batch-Scope (optional Filter)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.validator.pruning_recommendation", purpose: "Skip-Hint von Validator"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.dependency", purpose: "DAG + blocked/runnable-Listen"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-dependency-graph.md", path: "Mermaid + Tabelle", purpose: "Visualisierung DAG"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (excluding dependency)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.modus / pipeline_route"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "(kein direktes Write auf PL-Items)"}
  calls: []
---

# _SDF_berater_dependencyAnalyzer

## Zweck

Liest `blocked_by`-Felder aller PL-Items aus dem Vault, baut einen DAG, identifiziert
`blocked` (mind. 1 unfullfilled Predecessor) vs. `runnable` (alle Predecessors `done`).
Erkennt zyklische Abhaengigkeiten als Warnings. Schreibt zusaetzlich ein
Dependency-Graph-Markdown (Mermaid + Tabelle) in den Vault.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _SDF_berater_dependencyAnalyzer                            |
+======================================================================+
|  LIEST:    {VAULT}/Backlog/{bl_slug}/6_PL/                |
|              {bl_id}-parking-lot.md (PL-Items + blocked_by)          |
|            {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded) DF_BATCH_STATE.batch_items                   |
|            {WORKING_DIR}/_manifest.md BERATER_OUTPUTS.validator.pruning_recom...   |
|                                                                      |
|  SCHREIBT: BERATER_OUTPUTS.dependency                                |
|              {dag_path, blocked_items[], runnable_items[],           |
|               cyclic_warnings[]}                                     |
|            {VAULT}/Backlog/{bl_slug}/6_PL/                |
|              {bl_id}-dependency-graph.md (Mermaid + Tabelle)         |
|                                                                      |
|  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                   |
|                  DF_BATCH_STATE.modus / pipeline_route               |
|                  PL-Items selbst (nur read-only)                     |
|                                                                      |
|  ACTOR: _SDF_orchestrate Phase 1, nach Validator                     |
|                                                                      |
|  MODELL-TIER: sonnet (Default, BL-134 W3)                            |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-DEP-1: Skip falls validator.pruning_recommendation =          |
|                "SKIP_DOWNSTREAM"                                      |
|    INV-DEP-2: DAG-Output ist deterministisch (sortierte Knoten)      |
|    INV-DEP-3: Zyklen erzeugen Warnings, nicht ABORT (P8 Fail-Safe)   |
|    INV-DEP-4: Vault-Pfad-Pattern fest verdrahtet (BL-134 AK-2)       |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_SDF_berater_dependencyAnalyzer, args="{NAME}")

Parameter:
  {NAME} - Feature-Name (z.B. "BL-134")

Vorbedingung:
  - BERATER_OUTPUTS.validator gesetzt (Skip falls SKIP_DOWNSTREAM)

Ausgabe:
  - BERATER_OUTPUTS.dependency (4 Felder)
  - DAG-Markdown im Vault
  - Exitcode: 0=OK, 1=WARN (Zyklen), 2=SKIP

Logging-Format (NFR-4):
  [DEPANALYZE] ENTRY feature={NAME}
  [DEPANALYZE] DAG nodes={n} edges={m}
  [DEPANALYZE] CYCLE detected={items}
  [DEPANALYZE] EXIT duration={ms}ms blocked={a} runnable={b} cycles={c}
```

## Schritte

```
SCHRITT 0a: bl_slug + bl_id aufloesen (BL-143 Erweiterung)
  bl_id = DF_PIPELINE_STATE.df_task  # z.B. "BL-141"

  # Stufe 1: BDF_BATCH_STATE (PRIMAER, wenn big_dark_factory=true)
  IF BDF_BATCH_STATE.bl_items != null AND not empty:
    bl_item = BDF_BATCH_STATE.bl_items.find(item => item.id == bl_id)
    IF bl_item AND bl_item.vault_path:
      bl_slug = extract_slug(bl_item.vault_path)  # z.B. "BL-141-sanity-check-end-to-end"
      Logge: "[BL-140-Pfad-Fix] bl_slug={bl_slug} (Quelle: BDF)"
      -> DONE

  # Stufe 2: IDF_PIPELINE_STATE (wenn big_dark_factory=false aber IDF aktiv)
  IF IDF_PIPELINE_STATE.bl_slug != null:
    bl_slug = IDF_PIPELINE_STATE.bl_slug
    Logge: "[BL-143-Fallback] bl_slug={bl_slug} (Quelle: IDF)"
    -> DONE

  # Stufe 3: Glob-Fallback (Vault-Suche)
  candidates = Glob("{VAULT}/Backlog/{bl_id}-*.md")
  IF |candidates| == 1:
    bl_slug = extract_filename_without_ext(candidates[0])
    Logge: "[BL-143-Fallback] bl_slug={bl_slug} (Quelle: Glob)"
    -> DONE
  ELIF |candidates| > 1:
    FAIL: "Mehrere Vault-Items fuer {bl_id} gefunden -- mehrdeutig: {candidates}"
  ELSE:
    # Stufe 4: Letzter Fallback fuer direct-Modus
    bl_slug = bl_id
    Logge: "[BL-143-Fallback] bl_slug={bl_id} (Quelle: direct, kein Vault-Item)"

SCHRITT 0: Entry-Log + Skip-Guard
  Logge: "[DEPANALYZE] ENTRY feature={NAME}"
  IF BERATER_OUTPUTS.validator.pruning_recommendation == "SKIP_DOWNSTREAM":
    Logge: "[DEPANALYZE] SKIP (validator pruning)"
    BERATER_OUTPUTS.dependency = {dag_path: null, blocked_items: [], runnable_items: [], cyclic_warnings: ["SKIPPED_BY_VALIDATOR"]}
    EXIT 2

SCHRITT 1: Eigentliche Logik (DAG-Bau)
  vault_pl  = read({VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md)
  nodes     = [item.id FOR item IN vault_pl]
  edges     = []
  done_set  = {item.id FOR item IN vault_pl WHERE item.status == "done"}

  FOR item IN vault_pl:
    FOR pred IN (item.blocked_by ?? []):
      edges.append({from: pred, to: item.id})

  cyclic_warnings = detect_cycles(nodes, edges)   # Tarjan/Kahn
  blocked_items   = []
  runnable_items  = []
  FOR item IN vault_pl:
    IF item.status == "done": CONTINUE
    preds = (item.blocked_by ?? [])
    unfulfilled = [p FOR p IN preds WHERE p NOT IN done_set]
    IF unfulfilled.length == 0:
      runnable_items.append(item.id)
    ELSE:
      blocked_items.append({id: item.id, waiting_for: unfulfilled})

SCHRITT 2: Output schreiben (Manifest + DAG-Markdown)
  dag_path = "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-dependency-graph.md"
  write(dag_path, render_mermaid(nodes, edges, done_set) + render_table(blocked_items, runnable_items))

  BERATER_OUTPUTS.dependency = {
    dag_path:        dag_path,
    blocked_items:   blocked_items,
    runnable_items:  runnable_items,
    cyclic_warnings: cyclic_warnings
  }
  Aktualisiere {WORKING_DIR}/_manifest.md

SCHRITT 3: Exit-Log
  exitcode = (cyclic_warnings.length > 0) ? 1 : 0
  Logge: "[DEPANALYZE] EXIT duration={ms}ms blocked={|blocked_items|} runnable={|runnable_items|} cycles={|cyclic_warnings|}"
  EXIT exitcode
```

### Konkrete Tool-Anweisungen (BL-142)

Worker-Aufruf-Pattern:
1. `pl_path` aus SCHRITT 0a
2. `pl_content = Read(pl_path)` -- Read-Tool, kein abstraktes `read()`
3. Pro Item: `dependencies` Field-Parse via Regex `dependencies:\s*\[(.*?)\]`
4. DAG-Bau: dict `{item_id: [deps]}` -> Adjazenz-Liste
5. Cycle-Check via DFS
6. Output schreiben + DAG-Doc nach `{VAULT}/.../6_PL/{bl_id}-dependency-graph.md` via Edit-Tool (falls Datei existiert) oder Write-Tool (neu)

## Output-Schema (BERATER_OUTPUTS.dependency)

```yaml
BERATER_OUTPUTS:
  dependency:
    dag_path: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-dependency-graph.md"
    blocked_items:
      - {id: "BL-134-PL-5", waiting_for: ["BL-134-PL-2"]}
    runnable_items:  ["BL-134-PL-1", "BL-134-PL-2", "BL-134-PL-11"]
    cyclic_warnings: []
    last_berater:    "dependencyAnalyzer"
```

## AK-Mapping

- **AK-2** (Vault-Pfad-Pattern): `{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-*.md` via Slug-Lookup (SCHRITT 0a + SCHRITT 1).
- **AK-6** (Berater-Vertrag): VERTRAG-Block + INV-DEP-1..4.
- **AK-13** (Pruning-Hint): `cyclic_warnings` + Skip-Guard via Validator.
