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
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items (Frontmatter + Body)", purpose: "Schema-Pruefung der PL-Items"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items", purpose: "Welche Items sind aktuell im Batch"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.df_task", purpose: "Aktueller BL (NNN)"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.validator", purpose: "Validierungs-Resultat fuer PL-Items"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (excluding validator)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.modus / pipeline_route"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "(kein direktes Write auf PL-Items)"}
  calls: []
---

# _SDF_berater_validator

## Zweck

Prueft alle PL-Items eines BL-Features im Vault auf Schema-Konsistenz: Frontmatter-Pflichtfelder,
ID-Konsistenz (Filename vs. Frontmatter `id`), Status-Feld vorhanden (`status: open|done|blocked`),
`blocked_by`-Feld syntaktisch valide (Liste oder leer). Bei FAIL erfolgt Pruning-Empfehlung:
DepAnalyzer/SeqPlanner/BatchPlanner werden geskippt.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _SDF_berater_validator                                     |
+======================================================================+
|  LIEST:    {VAULT}/Backlog/{bl_slug}/6_PL/                |
|              {bl_id}-parking-lot.md (PL-Items inkl. Frontmatter)     |
|            {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded) DF_BATCH_STATE.batch_items                   |
|            {WORKING_DIR}/_manifest.md DF_PIPELINE_STATE.df_task                    |
|                                                                      |
|  SCHREIBT: BERATER_OUTPUTS.validator                                 |
|              {pl_items_total, pl_items_valid, validation_errors[],   |
|               pruning_recommendation}                                |
|                                                                      |
|  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                   |
|                  DF_BATCH_STATE.modus / pipeline_route               |
|                  (kein Write auf PL-Items im Vault, nur lesend)       |
|                                                                      |
|  ACTOR: _SDF_orchestrate Phase 1 (BATCH-PLAN), erster Berater        |
|                                                                      |
|  MODELL-TIER: sonnet (Default, BL-134 W2)                            |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-VAL-1: Read-Only auf Vault-PL (kein Patch der PL-Items hier)  |
|    INV-VAL-2: FAIL-Loud bei Schema-Verletzung (P8 Fail-Loud)         |
|    INV-VAL-3: Pruning-Hint NUR Empfehlung, Aufrufer entscheidet      |
|    INV-VAL-4: Vault-Pfad-Pattern fest verdrahtet (BL-134 AK-2)       |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_SDF_berater_validator, args="{NAME}")

Parameter:
  {NAME} - Feature-Name (z.B. "BL-134")

Ausgabe:
  - BERATER_OUTPUTS.validator (4 Felder)
  - Exitcode: 0=OK (alle valid), 1=PARTIAL (Warnings), 2=FAIL (Pruning empfohlen)

Logging-Format (NFR-4):
  [VALIDATOR] ENTRY feature={NAME} batch_size={n}
  [VALIDATOR] CHECK item={item_id} result={OK|ERR}
  [VALIDATOR] EXIT duration={ms}ms total={n} valid={m} errors={k}
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

SCHRITT 0: Entry-Log
  Logge: "[VALIDATOR] ENTRY feature={NAME} batch_size={|batch_items|}"
  validation_errors = []
  pl_items_total    = 0
  pl_items_valid    = 0

SCHRITT 1: Eigentliche Logik (Schema-Pruefung)
  vault_pl = read({VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md)
  IF vault_pl == null:
    validation_errors.append({code: "PL_MISSING", path: vault_pl_path})
    pruning_recommendation = "SKIP_DOWNSTREAM"
    -> SCHRITT 2

  FOR jedes pl_item IN vault_pl:
    pl_items_total += 1
    errors_item = []
    # Frontmatter-Pflichtfelder
    IF pl_item.frontmatter.id MISSING:
      errors_item.append("MISSING_ID")
    ELIF pl_item.frontmatter.id != filename_id_pattern:
      errors_item.append("ID_MISMATCH")
    IF pl_item.frontmatter.status NOT IN ["open","done","blocked","in_progress"]:
      errors_item.append("INVALID_STATUS")
    IF pl_item.frontmatter.blocked_by EXISTS AND NOT is_list(pl_item.frontmatter.blocked_by):
      errors_item.append("BLOCKED_BY_NOT_LIST")
    IF errors_item == []:
      pl_items_valid += 1
      Logge: "[VALIDATOR] CHECK item={pl_item.id} result=OK"
    ELSE:
      validation_errors.append({item: pl_item.id, errors: errors_item})
      Logge: "[VALIDATOR] CHECK item={pl_item.id} result=ERR errors={errors_item}"

  IF validation_errors.length == 0:
    pruning_recommendation = "PROCEED"
  ELIF validation_errors.length < pl_items_total / 2:
    pruning_recommendation = "PROCEED_WITH_WARNINGS"
  ELSE:
    pruning_recommendation = "SKIP_DOWNSTREAM"

SCHRITT 2: Output schreiben
  BERATER_OUTPUTS.validator = {
    pl_items_total:         pl_items_total,
    pl_items_valid:         pl_items_valid,
    validation_errors:      validation_errors,
    pruning_recommendation: pruning_recommendation
  }
  Aktualisiere {WORKING_DIR}/_manifest.md

SCHRITT 3: Exit-Log
  exitcode = (pruning_recommendation == "PROCEED") ? 0
           : (pruning_recommendation == "PROCEED_WITH_WARNINGS") ? 1
           : 2
  Logge: "[VALIDATOR] EXIT duration={ms}ms total={pl_items_total} valid={pl_items_valid} errors={|validation_errors|}"
  EXIT exitcode
```

### Konkrete Tool-Anweisungen (BL-142)

Worker-Aufruf-Pattern:
1. `pl_path` aus SCHRITT 0a (4-stufiger Slug-Lookup)
2. `pl_content = Read(pl_path)` -- Read-Tool, kein abstraktes `read()`
3. PL-Items extrahieren: Glob `^- \[ \]` Listen-Items ODER Frontmatter-Block-Trennen `---\n.*?\n---`
4. Schema-Check via Regex:
   - `id:\s*"?([A-Z0-9-]+)"?`
   - `status:\s*(open|in_progress|done|blocked|deferred)`
   - `dependencies:\s*\[(.*?)\]`
5. Pruning-Recommendation berechnen (>50% errors -> ABORT, sonst CONTINUE_WITH_WARNINGS oder OK)
6. `Edit({WORKING_DIR}/_manifest.md, ...)` setze `BERATER_OUTPUTS.validator = {pl_items_total, pl_items_valid, validation_errors[], pruning_recommendation}`

## Output-Schema (BERATER_OUTPUTS.validator)

```yaml
BERATER_OUTPUTS:
  validator:
    pl_items_total:         12
    pl_items_valid:         11
    validation_errors:
      - item: "BL-134-PL-7"
        errors: ["INVALID_STATUS"]
    pruning_recommendation: "PROCEED_WITH_WARNINGS"   # PROCEED | PROCEED_WITH_WARNINGS | SKIP_DOWNSTREAM
    last_berater:           "validator"
```

## AK-Mapping

- **AK-2** (Vault-Pfad-Pattern): `{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md` via Slug-Lookup (SCHRITT 0a + SCHRITT 1).
- **AK-6** (Berater-Vertrag): VERTRAG-Block mit LIEST/SCHREIBT/SCHREIBT-NICHT.
- **AK-13** (Pruning-Hint): `pruning_recommendation` als Output-Feld (INV-VAL-3).
