---
status: active
version: 0.3.0
type: berater
parent: _IDF_orchestrate
phase: phase_3.5
model_tier: middle
created: 2026-04-25
updated: 2026-05-24
feature_anchor: BL-142
optional: false
migrated_from: _SDF_berater_validator
bl_205_srs_validation: true
contract:
  reads:
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items + Frontmatter", purpose: "Schema-Pruefung"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items / IDF_PIPELINE_STATE.bl_id", purpose: "Batch-Scope"}
    - {file: "{VAULT}/Backlog/{bl_slug}/2_Model/{bl_id}-Model.md", path: "W{n}.status", purpose: "BL-205 AK-7: SRS-Status-Validierung (INV-STATUS-1)"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.validator", purpose: "Validierungs-Resultat inkl. srs_validation_errors"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser validator)"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "(read-only)"}
    - {file: "{VAULT}/.../Model.md", path: "(read-only)"}
  calls: []
---

# _IDF_berater_validator (Phase 3.5 in _IDF_orchestrate)

> **Zweck:** Migriert aus SDF. Schema-Pruefung der PL-Items (Frontmatter, ID-Konsistenz, status, blocked_by).

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_validator                                     |
+======================================================================+
|  LIEST:                                                              |
|    {VAULT}/Backlog/{bl_slug}/6_PL/                       |
|      {bl_id}-parking-lot.md (PL-Items + Frontmatter)                 |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      DF_BATCH_STATE.batch_items                                      |
|      IDF_PIPELINE_STATE.bl_id                                        |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      BERATER_OUTPUTS.validator = {                                   |
|        pl_items_total, pl_items_valid,                               |
|        validation_errors[], pruning_recommendation                   |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser validator)                              |
|    PL-Items selbst (read-only)                                       |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 3.5 (zwischen plAggregation und dep)  |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: 1:1 aus SDF (BL-134 W2). Schema-Regex-Pruefung.    |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-VAL-1 (Read-Only auf Vault-PL)                                |
|    INV-VAL-2 (FAIL-Loud bei Schema-Verletzung, P8)                   |
|    INV-VAL-3 (Pruning-Hint NUR Empfehlung)                           |
|    INV-VAL-4 (Vault-Pfad-Pattern fest)                               |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - bl_slug + bl_id aufgeloest (4-stufiger Lookup wie in SDF)       |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - BERATER_OUTPUTS.validator vollstaendig                          |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_validator, args="{NAME}")

Parameter:
  {NAME} - Feature-Name oder bl_id

Ausgabe:
  - BERATER_OUTPUTS.validator
  - Exitcode: 0=OK, 1=PARTIAL (Warnings), 2=FAIL

Logging-Format:
  [IDF_VAL] ENTRY feature={NAME} batch_size={n}
  [IDF_VAL] EXIT duration={ms}ms total={n} valid={m} errors={k}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  validator:
    pl_items_total: 12
    pl_items_valid: 11
    validation_errors:
      - {item: "BL-142-PL-7", errors: ["INVALID_STATUS"]}
    srs_validation_errors:                        # BL-205 AK-7 (leer = OK)
      - {node: "W-FOO-1", invalid_status: "unknown", error: "INV-STATUS-1: ..."}
    pruning_recommendation: "PROCEED_WITH_WARNINGS"
    last_berater: "validator"
```

## Schritte

```
SCHRITT 0a: bl_slug + bl_id aufloesen (BL-143 Erweiterung)
  bl_id = IDF_PIPELINE_STATE.bl_id  # z.B. "BL-141"

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
  Logge: "[IDF_VAL] ENTRY feature={NAME} batch_size={|batch_items|}"
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
      Logge: "[IDF_VAL] CHECK item={pl_item.id} result=OK"
    ELSE:
      validation_errors.append({item: pl_item.id, errors: errors_item})
      Logge: "[IDF_VAL] CHECK item={pl_item.id} result=ERR errors={errors_item}"

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

SCHRITT 2b: SRS-Status-Validierung (BL-205 AK-7 — INV-STATUS-1)
  VALID_SRS_STATUS = {
    "BESTAETIGT", "BESTAETIGT-DB", "STABLE", "AKTIV (BESTAETIGT)",
    "RESOLVED", "RESOLVED-DB", "CLOSED",
    "TENTATIV", "HYPOTHESE", "OFFEN", "RETRACTED",
    "experiment_provable"   # NEU [BL-239 AK-1/AK-8]: nur-experimentell-schliessbare Wahrheit (12 Werte). INV-STATUS-1.
  }

  model_path = "{VAULT}/Backlog/{bl_slug}/2_Model/{bl_id}-Model.md"
  srs_validation_errors = []

  IF model_path EXISTS:
    model_content = Read(model_path)
    FOR jedes W{n} IN model_content:
      IF W{n}.status NOT IN VALID_SRS_STATUS AND W{n}.status IS NOT null:
        srs_validation_errors.append({
          node: "W{n}",
          invalid_status: W{n}.status,
          error: "INV-STATUS-1: Ungueltiger W{n}.status — freie Strings VERBOTEN"
        })
        Logge: "[IDF_VAL] SRS-FAIL node=W{n} status={W{n}.status} — INV-STATUS-1"

    IF srs_validation_errors IS NOT EMPTY:
      IF pruning_recommendation != "SKIP_DOWNSTREAM":
        pruning_recommendation = "PROCEED_WITH_WARNINGS"
      Logge: "[IDF_VAL] SRS-WARN {|srs_validation_errors|} ungueltige Status-Werte in Model.md"
    ELSE:
      Logge: "[IDF_VAL] SRS-OK alle W{n}.status in Model.md valide (INV-STATUS-1)"

SCHRITT 3: Exit-Log
  exitcode = (pruning_recommendation == "PROCEED") ? 0
           : (pruning_recommendation == "PROCEED_WITH_WARNINGS") ? 1
           : 2
  Logge: "[IDF_VAL] EXIT duration={ms}ms total={pl_items_total} valid={pl_items_valid} errors={|validation_errors|} srs_errors={|srs_validation_errors|}"
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

## AK-Mapping

- **AK-2** (Vault-Pfad-Pattern): `{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md` via Slug-Lookup (SCHRITT 0a + SCHRITT 1).
- **AK-6** (Berater-Vertrag): VERTRAG-Block mit LIEST/SCHREIBT/SCHREIBT-NICHT.
- **AK-13** (Pruning-Hint): `pruning_recommendation` als Output-Feld (INV-VAL-3).
- **BL-205 AK-7** (SRS-Status-Validierung): SCHRITT 2b prueft W{n}.status-Werte in Model.md gegen VALID_SRS_STATUS (INV-STATUS-1). Ungueltige Werte → srs_validation_errors[] + PROCEED_WITH_WARNINGS. Konsumiert `srs_conventions.md` als Status-Autoritaet.

## migration_disposition-Pruef-Haken (BL-333, B5 — IDF Phase 3.5, Follow zu B4)

> **Lead = `_A_berater_specParse.md` (B4).** Identische WARN-vs-Block-Semantik (`resolve_format_version.check_migration_disposition`). Prosa-Disziplin, kein Hard-Block.

In IDF Phase 3.5 (Validator) wird zusaetzlich zum Schema-Check geprueft, ob das Spec-/PL-Frontmatter das Pflicht-Metadatum `migration_disposition` traegt (Wertebereich `retroaktiv | forward-compat-only | hybrid`):

- **Fehlt -> WARN (non-blocking):** Fehlt `migration_disposition`, wird eine WARN-Zeile erzeugt und geht in `validation_errors[]`/Report ein — eskaliert aber NIE zu einem Hard-Block. `pruning_recommendation` bleibt von diesem Haken unbeeinflusst (kein zusaetzlicher ABORT-Trigger).
- **Symmetrie zu B4:** gleiche WARN-Semantik wie `_A_berater_specParse.md`; der Loader-Helfer `check_migration_disposition` ist Single-Source der WARN-Logik (kein eigener Reimplementierungs-Pfad).

## Begruendung Modell-Tier

sonnet — wie SDF-Original (BL-134 W2). Schema-Regex-Pruefung erfordert kein opus-Tier.
