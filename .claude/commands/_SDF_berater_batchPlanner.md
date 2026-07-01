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
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items (k_score Frontmatter)", purpose: "Aggregat-K-Score-Bestimmung"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.sequence.ordered_items", purpose: "Eingangs-Sequenz"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.validator.pruning_recommendation", purpose: "Skip-Hint"}
    - {file: "_session_params.md", path: "GLOBAL_MODUS", purpose: "easy/normal/hard fuer Batch-Size-Default"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items", purpose: "Finale Batch-Liste"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.k_score_aggregate", purpose: "Aggregat-K-Score (Mitose-Trigger)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.batch", purpose: "Batch-Plan inkl. Eskalations-Hint"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (excluding batch)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.modus / pipeline_route"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "(kein direktes Write auf PL-Items)"}
  calls: []
---

# _SDF_berater_batchPlanner

## Zweck

Aus der `sequence.ordered_items` einen **Batch** ableiten: 1, 4 oder alle Items, je nach
Komplexitaets-Heuristik (`k_score` pro Item, Aggregat). Default Batch-Size 1-3 (sonnet).
Bei `k_score_aggregate >= 70` -> Mitose-Hint: opus-Eskalation. Schreibt direkt
`DF_BATCH_STATE.batch_items[]` und `DF_BATCH_STATE.k_score_aggregate`.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _SDF_berater_batchPlanner                                  |
+======================================================================+
|  LIEST:    {VAULT}/Backlog/{bl_slug}/6_PL/                |
|              {bl_id}-parking-lot.md (k_score je Item)                |
|            {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded) BERATER_OUTPUTS.sequence.ordered_items       |
|            {WORKING_DIR}/_manifest.md BERATER_OUTPUTS.validator.pruning_recom...   |
|            _session_params.md GLOBAL_MODUS                           |
|                                                                      |
|  SCHREIBT: DF_BATCH_STATE.batch_items[]                              |
|            DF_BATCH_STATE.k_score_aggregate                          |
|            BERATER_OUTPUTS.batch                                     |
|              {batch_size, batch_items[], k_score_aggregate,          |
|               escalation_hint}                                       |
|                                                                      |
|  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                   |
|                  DF_BATCH_STATE.modus / pipeline_route               |
|                  PL-Items selbst                                     |
|                                                                      |
|  ACTOR: _SDF_orchestrate Phase 1, letzter Berater vor Phase 2        |
|                                                                      |
|  MODELL-TIER: sonnet (Default, BL-134 W7)                            |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-BATCH-1: Batch-Size respektiert GLOBAL_MODUS                  |
|                 (easy=1, normal=1-3, hard=1-5)                       |
|    INV-BATCH-2: Aggregat-K-Score = mean(k_score Items im Batch)      |
|    INV-BATCH-3: Eskalations-Hint NUR Empfehlung                      |
|                 (Aufrufer entscheidet Tier-Wechsel)                  |
|    INV-BATCH-4: Skip falls validator.pruning_recommendation =        |
|                 "SKIP_DOWNSTREAM"                                     |
|    INV-BATCH-5: Vault-Pfad-Pattern fest verdrahtet (BL-134 AK-2)     |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_SDF_berater_batchPlanner, args="{NAME}")

Parameter:
  {NAME} - Feature-Name (z.B. "BL-134")

Vorbedingung:
  - BERATER_OUTPUTS.sequence gesetzt (ordered_items vorhanden)

Ausgabe:
  - DF_BATCH_STATE.batch_items[] gesetzt
  - DF_BATCH_STATE.k_score_aggregate gesetzt
  - BERATER_OUTPUTS.batch (4 Felder)
  - Exitcode: 0=OK, 1=ESCALATE (k>=70), 2=SKIP

Logging-Format (NFR-4):
  [BATCHPLAN] ENTRY feature={NAME} sequence_size={n} modus={easy|normal|hard}
  [BATCHPLAN] DEFAULT batch_size={k}
  [BATCHPLAN] AGGREGATE k_score={k} -> {sonnet|opus_hint}
  [BATCHPLAN] EXIT duration={ms}ms batch={items}
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
  Logge: "[BATCHPLAN] ENTRY feature={NAME} sequence_size={|sequence.ordered_items|} modus={GLOBAL_MODUS}"
  IF BERATER_OUTPUTS.validator.pruning_recommendation == "SKIP_DOWNSTREAM":
    BERATER_OUTPUTS.batch = {batch_size: 0, batch_items: [], k_score_aggregate: 0, escalation_hint: "SKIPPED"}
    EXIT 2
  IF sequence.ordered_items.length == 0:
    BERATER_OUTPUTS.batch = {batch_size: 0, batch_items: [], k_score_aggregate: 0, escalation_hint: "EMPTY"}
    EXIT 2

SCHRITT 1: Eigentliche Logik (Heuristik + Aggregat)
  vault_pl  = read({VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md)
  k_scores  = {item.id: (item.frontmatter.k_score ?? 30) FOR item IN vault_pl}

  default_size = (GLOBAL_MODUS == "easy")   ? 1
               : (GLOBAL_MODUS == "hard")   ? 5
               :                              3   # normal

  candidates       = sequence.ordered_items[0 : default_size]
  k_score_per_item = [k_scores[id] FOR id IN candidates]
  aggregate        = (sum(k_score_per_item) / |k_score_per_item|) IF |k_score_per_item|>0 ELSE 0

  IF aggregate >= 70:
    escalation_hint = "OPUS_MITOSE_HINT"
    # Bei hohem k zieh den Batch enger (Risiko-Reduktion)
    candidates = candidates[0 : max(1, default_size-1)]
    k_score_per_item = [k_scores[id] FOR id IN candidates]
    aggregate        = (sum(k_score_per_item) / |k_score_per_item|) IF |k_score_per_item|>0 ELSE 0
  ELSE:
    escalation_hint = "SONNET_OK"

  Logge: "[BATCHPLAN] AGGREGATE k_score={aggregate} -> {escalation_hint}"

SCHRITT 2: Output schreiben (DF_BATCH_STATE + BERATER_OUTPUTS.batch)
  DF_BATCH_STATE.batch_items       = candidates
  DF_BATCH_STATE.k_score_aggregate = aggregate

  BERATER_OUTPUTS.batch = {
    batch_size:        |candidates|,
    batch_items:       candidates,
    k_score_aggregate: aggregate,
    escalation_hint:   escalation_hint
  }
  Aktualisiere {WORKING_DIR}/_manifest.md

SCHRITT 3: Exit-Log
  exitcode = (escalation_hint == "OPUS_MITOSE_HINT") ? 1 : 0
  Logge: "[BATCHPLAN] EXIT duration={ms}ms batch={candidates} hint={escalation_hint}"
  EXIT exitcode
```

### Konkrete Tool-Anweisungen (BL-142)

Worker-Aufruf-Pattern:
1. Lies `BERATER_OUTPUTS.sequence.ordered_items` aus Manifest via Read-Tool
2. Pro Item: k_score aus Vault-Frontmatter mit Regex `k_score:\s*(\d+)`
   - Zugriff auf PL-File via Read-Tool: `pl_content = Read(pl_path)`
3. k_score_aggregate = mean of next 1-3 items (je nach GLOBAL_MODUS)
4. Batch-Heuristik anwenden (>=70 Mitose-Hint, batch_size=1; 40-69: batch=3; <40: batch=5)
5. `Edit({WORKING_DIR}/_manifest.md, ...)` setze `DF_BATCH_STATE.batch_items` + `DF_BATCH_STATE.k_score_aggregate` + `DF_BATCH_STATE.batch_status="PLANNED"` via Edit-Tool

## Output-Schema (BERATER_OUTPUTS.batch)

```yaml
DF_BATCH_STATE:
  batch_items:        ["BL-134-PL-1", "BL-134-PL-11"]
  k_score_aggregate:  35

BERATER_OUTPUTS:
  batch:
    batch_size:        2
    batch_items:       ["BL-134-PL-1", "BL-134-PL-11"]
    k_score_aggregate: 35
    escalation_hint:   "SONNET_OK"        # SONNET_OK | OPUS_MITOSE_HINT | SKIPPED | EMPTY
    last_berater:      "batchPlanner"
```

## AK-Mapping

- **AK-2** (Vault-Pfad-Pattern): `{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md` via Slug-Lookup (SCHRITT 0a + SCHRITT 1).
- **AK-6** (Berater-Vertrag): VERTRAG-Block + INV-BATCH-1..5.
- **AK-13** (Pruning-Hint): `escalation_hint` (OPUS_MITOSE_HINT) + Skip-Guard via Validator.
