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
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items (Prioritaet, done-Liste)", purpose: "Tie-Breaking via Prioritaet/done-Status"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.dependency.runnable_items", purpose: "Eingangs-Set runnable Items"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.dependency.blocked_items", purpose: "Negation/Diagnostik"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.validator.pruning_recommendation", purpose: "Skip-Hint"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.sequence", purpose: "Topologische Reihenfolge runnable-Items"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (excluding sequence)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items / modus / pipeline_route"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "(kein direktes Write auf PL-Items)"}
  calls: []
---

# _SDF_berater_sequencePlanner

## Zweck

Aus dem DAG (DependencyAnalyzer-Output) eine **topologische Sortierung** der `runnable_items`
ableiten. Tie-Breaking via Prioritaet (PL-Frontmatter `priority`) und (sekundaer) PL-Reihenfolge
im Vault. Liefert ausserdem `next_runnable` als Pointer fuer den BatchPlanner.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _SDF_berater_sequencePlanner                               |
+======================================================================+
|  LIEST:    {VAULT}/Backlog/{bl_slug}/6_PL/                |
|              {bl_id}-parking-lot.md (priority, Reihenfolge)          |
|            {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded) BERATER_OUTPUTS.dependency.runnable_items    |
|            {WORKING_DIR}/_manifest.md BERATER_OUTPUTS.dependency.blocked_items     |
|            {WORKING_DIR}/_manifest.md BERATER_OUTPUTS.validator.pruning_recom...   |
|                                                                      |
|  SCHREIBT: BERATER_OUTPUTS.sequence                                  |
|              {ordered_items[], tie_breaks[], next_runnable}          |
|                                                                      |
|  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                   |
|                  DF_BATCH_STATE.batch_items / modus / pipeline_route |
|                  PL-Items selbst                                     |
|                                                                      |
|  ACTOR: _SDF_orchestrate Phase 1, nach DependencyAnalyzer            |
|                                                                      |
|  MODELL-TIER: sonnet (Default, BL-134 W7)                            |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-SEQ-1: Topologische Sortierung deterministisch                |
|                (gleicher DAG -> gleiche Order)                       |
|    INV-SEQ-2: Skip falls validator.pruning_recommendation =          |
|                "SKIP_DOWNSTREAM"                                      |
|    INV-SEQ-3: Tie-Breaking dokumentiert (tie_breaks[])               |
|    INV-SEQ-4: Vault-Pfad-Pattern fest verdrahtet (BL-134 AK-2)       |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_SDF_berater_sequencePlanner, args="{NAME}")

Parameter:
  {NAME} - Feature-Name (z.B. "BL-134")

Vorbedingung:
  - BERATER_OUTPUTS.dependency gesetzt (DAG vorhanden)

Ausgabe:
  - BERATER_OUTPUTS.sequence (3 Felder)
  - Exitcode: 0=OK, 2=SKIP (kein runnable_item)

Logging-Format (NFR-4):
  [SEQPLAN] ENTRY feature={NAME} runnable={n}
  [SEQPLAN] TIE_BREAK item={item_id} criterion={priority|pl_order}
  [SEQPLAN] EXIT duration={ms}ms ordered={n} next={item_id}
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
  Logge: "[SEQPLAN] ENTRY feature={NAME} runnable={|dependency.runnable_items|}"
  IF BERATER_OUTPUTS.validator.pruning_recommendation == "SKIP_DOWNSTREAM":
    BERATER_OUTPUTS.sequence = {ordered_items: [], tie_breaks: [], next_runnable: null}
    EXIT 2
  IF dependency.runnable_items.length == 0:
    BERATER_OUTPUTS.sequence = {ordered_items: [], tie_breaks: [], next_runnable: null}
    EXIT 2

SCHRITT 1: Eigentliche Logik (Topo-Sortierung mit Tie-Break)
  vault_pl    = read({VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md)
  pl_index    = {item.id: idx FOR idx, item IN enumerate(vault_pl)}
  priorities  = {item.id: (item.frontmatter.priority ?? 50) FOR item IN vault_pl}
  candidates  = dependency.runnable_items
  tie_breaks  = []

  # Stable Topo-Sort:
  #   Primaer: priority desc (hoehere prio zuerst)
  #   Sekundaer: pl_index asc (Reihenfolge im PL-File)
  ordered_items = sort(candidates, key=lambda x: (-priorities[x], pl_index[x]))

  FOR i IN range(len(ordered_items)-1):
    a, b = ordered_items[i], ordered_items[i+1]
    IF priorities[a] == priorities[b]:
      tie_breaks.append({between: [a, b], criterion: "pl_order", winner: a})
      Logge: "[SEQPLAN] TIE_BREAK item={a}<{b} criterion=pl_order"

  next_runnable = ordered_items[0]

SCHRITT 2: Output schreiben
  BERATER_OUTPUTS.sequence = {
    ordered_items: ordered_items,
    tie_breaks:    tie_breaks,
    next_runnable: next_runnable
  }
  Aktualisiere {WORKING_DIR}/_manifest.md

SCHRITT 3: Exit-Log
  Logge: "[SEQPLAN] EXIT duration={ms}ms ordered={|ordered_items|} next={next_runnable}"
  EXIT 0
```

### Konkrete Tool-Anweisungen (BL-142)

Worker-Aufruf-Pattern:
1. Lies `BERATER_OUTPUTS.dependency.runnable_items` aus Manifest via Read-Tool
2. Topologische Sortierung via Kahn-Algorithmus
3. Tie-Breaking: Sortiere nach Frontmatter-Field `priority` (high>med>low), dann nach `created` (Datum aufsteigend)
   - Regex fuer priority: `priority:\s*(high|med|low|\d+)`
   - Regex fuer created: `created:\s*(\d{4}-\d{2}-\d{2})`
4. Filter `DF_PIPELINE_STATE.batch_done` raus (Glob auf manifest-Feld)
5. Output `BERATER_OUTPUTS.sequence` schreiben via Edit-Tool auf `{WORKING_DIR}/_manifest.md`

## Output-Schema (BERATER_OUTPUTS.sequence)

```yaml
BERATER_OUTPUTS:
  sequence:
    ordered_items:  ["BL-134-PL-1", "BL-134-PL-11", "BL-134-PL-2"]
    tie_breaks:
      - {between: ["BL-134-PL-1","BL-134-PL-11"], criterion: "pl_order", winner: "BL-134-PL-1"}
    next_runnable:  "BL-134-PL-1"
    last_berater:   "sequencePlanner"
```

## AK-Mapping

- **AK-2** (Vault-Pfad-Pattern): `{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md` via Slug-Lookup (SCHRITT 0a + SCHRITT 1).
- **AK-6** (Berater-Vertrag): VERTRAG-Block + INV-SEQ-1..4.
- **AK-13** (Pruning-Hint): Skip-Guard via Validator.
