---
status: DEPRECATED
deprecated_at: 2026-05-24
deprecated_by: BL-209
deprecated_reason: "Hard-Cut. _A_berater_plAggregation (A-Pipeline Phase 5c) ist Nachfolger und Single-Source."
version: 0.2.0
type: berater
parent: _IDF_orchestrate
phase: phase_3.2
model_tier: middle
created: 2026-04-25
feature_anchor: BL-142
optional: false
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.akExtraktion[*]", purpose: "Per-AK Metadaten aggregieren"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.bl_id / bl_slug", purpose: "Vault-Pfad"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "Existenz + bestehende Items", purpose: "Idempotenz / Merge"}
  writes:
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items + Aggregat-Block", purpose: "Aus AK-Extraktion abgeleitete Items"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.plAggregation", purpose: "Schema (s.u.)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser plAggregation)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.idf_status"}
  calls: []
---

# _IDF_berater_plAggregation (Phase 3.2 in _IDF_orchestrate)

> **Zweck:** Aus Per-AK-Outputs PL-Items im Vault aggregieren — sequenziell.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_plAggregation                                 |
+======================================================================+
|  LIEST:                                                              |
|    {WORKING_DIR}/_manifest.md (INV-VAULT-9 Path-Resolver)            |
|      BERATER_OUTPUTS.akExtraktion[*] (Per-AK Outputs, sofern present)|
|      IDF_PIPELINE_STATE.bl_id / bl_slug                              |
|    .claude/config/vault-routing.json (Pfad-Resolution!)              |
|      vaults.{detected_vault}.windows_path                            |
|      detection.rules[matched].backlog.subfolder                      |
|    {VAULT_BL_FOLDER}/6_PL/  (PFLICHT: ALLE PL-Files lesen!)          |
|      - {bl_id}-parking-lot.md  (BL-praefix Variante)                 |
|      - parking-lot.md          (slug-only Variante, falls vorhanden) |
|      - {bl_id}-pl-matrix.md    (Matrix-View)                         |
|      - {bl_id}-maxlength-reference.md (Referenz)                     |
|      - PL-NN-{slug}/* (Per-Item Subfolders, falls vorhanden)         |
|                                                                      |
|  SCHREIBT:                                                           |
|    {VAULT_BL_FOLDER}/6_PL/{bl_id}-parking-lot.md                     |
|      (Master-File, Aggregat + neue PL-Items)                         |
|    {WORKING_DIR}/_manifest.md                                        |
|      BERATER_OUTPUTS.plAggregation = {                               |
|        items_total, items_new, items_existing,                       |
|        aggregate_k_score, aggregate_unreife_typ,                     |
|        sources_read[],   (NEU: Liste der gelesenen Files)            |
|        master_file       (NEU: Welche File ist Schreib-Master)       |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser plAggregation)                          |
|    IDF_PIPELINE_STATE.idf_status (das ist statusTransition)          |
|                                                                      |
|  PFLICHT-LOGGING (NEU 2026-05-04):                                   |
|    [plAgg] vault_root={path}                                         |
|    [plAgg] bl_folder={path}                                          |
|    [plAgg] reading: {file_a} ({n_lines} Zeilen, {n_open} offen)      |
|    [plAgg] reading: {file_b} ({n_lines} Zeilen, {n_open} offen)      |
|    [plAgg] master_file={path} (wo geschrieben wird)                  |
|    [plAgg] items_total={N} (new={A}, existing={B})                   |
|                                                                      |
|  VERTRAG: Schema-Pruefung PL-Items (PL-12-04, BL-165 AK-12):        |
|    Pflicht-Felder pro PL-Item gemaess pl_item_schema.yaml:           |
|      id (string), source_aks (array), source_w (string|null),        |
|      srs (int 0..100), k_score (int 0..100),                         |
|      k_components.aufwand/kopplung/fragilitaet (int 0..100),         |
|      derived_from_srs (bool), last_recompute (ISO date),             |
|      batch_id (string), recompute_source (string)                    |
|    Bei Aggregation: pruefe srs und k_score auf numerischen Typ.      |
|    FAIL falls kategorisch (LOW/MED/MEDIUM/HIGH statt int).           |
|    Log bei Fehler: [plAgg] SCHEMA-FAIL item={id} field={f} val={v}  |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 3.2 (Per-PL, sequenziell)             |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Aggregation aus Per-AK-Outputs in Vault-PL,         |
|    Markdown-Listen-Schreiben. Kein Reasoning.                       |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-PLA-1: Idempotent — bestehende Items mergen, nicht ueberschr.|
|    INV-PLA-2: Aggregate (k_score, unreife_typ) als Frontmatter      |
|    INV-PLA-3: Schreib-Isolation auf BERATER_OUTPUTS.plAggregation    |
|    INV-PLA-4 (NEU): MUSS ALLE 6_PL/*.md Dateien lesen, nicht nur    |
|                     {bl_id}-parking-lot.md (es gibt mehrere Varianten|
|                     in laufenden Projekten — siehe BL-151 Resolver-  |
|                     Chaos)                                           |
|    INV-PLA-5 (NEU): MUSS Pfade explizit loggen — User muss im       |
|                     Terminal sehen WELCHE Dateien angefasst wurden   |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - akExtraktion done fuer alle AKs                                 |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - parking-lot.md existiert mit allen PL-Items                     |
|    - BERATER_OUTPUTS.plAggregation vollstaendig                      |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_plAggregation, args="{NAME}")

Parameter:
  {NAME} - Feature-Name oder bl_id

Ausgabe:
  - parking-lot.md aktualisiert
  - BERATER_OUTPUTS.plAggregation
  - Exitcode: 0=OK, 2=FAIL

Logging-Format:
  [IDF_PLA] ENTRY name={NAME} aks={n}
  [IDF_PLA] EXIT duration={ms}ms items_total={n} new={k}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  plAggregation:
    items_total: 12
    items_new: 12
    items_existing: 0
    aggregate_k_score: 35
    aggregate_unreife_typ: "ok"
    last_berater: "plAggregation"
```

## Logik (RF-IDF4b Critical-Berater)

```
SCHRITT 0: Entry-Log + Vorbedingung
  Logge: "[IDF_PLA] ENTRY name={NAME}"
  manifest = Read({WORKING_DIR}/_manifest.md)
  ak_outputs = manifest.BERATER_OUTPUTS.akExtraktion
  IF ak_outputs == null OR |ak_outputs| == 0:
    FAIL: "akExtraktion fehlt — Phase 3.1 zuerst"
  bl_id = manifest.IDF_PIPELINE_STATE.bl_id
  bl_slug = manifest.IDF_PIPELINE_STATE.bl_slug

SCHRITT 1: PL-Pfad + Idempotenz-Check
  pl_path = "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"
  existing_items = []
  IF exists(pl_path):
    pl_content = Read(pl_path)
    existing_items = parse_pl_items(pl_content)  # by id

SCHRITT 2: Per-AK -> PL-Item ableiten (PL-Gruppierung-Heuristik)
  # AKs mit gemeinsamen layer_hint OR sich ueberschneidenden dateien_hint
  # werden in 1 PL-Item gruppiert. Sonst 1:1 Mapping.
  groups = []
  ungrouped = ak_outputs.values()

  WHILE |ungrouped| > 0:
    seed = ungrouped.pop(0)
    group = [seed]
    FOR ak in ungrouped:
      IF ak.layer_hint == seed.layer_hint
         AND ak.layer_hint != null
         AND |intersect(ak.dateien_hint, seed.dateien_hint)| > 0:
        group.append(ak)
        ungrouped.remove(ak)
    groups.append(group)

SCHRITT 2.5: Schema-Pruefung (PL-12-04, BL-165 AK-12)
  FOR pl_item IN pl_items_neu:
    FOR field IN [srs, k_score]:
      IF pl_item[field] IN ["LOW", "MED", "MEDIUM", "HIGH"]:
        Logge: "[plAgg] SCHEMA-FAIL item={pl_item.id} field={field} val={pl_item[field]} — kategorisch verboten"
        FAIL: "PL-Item {pl_item.id}: {field} muss int 0..100, nicht kategorisch"
    IF pl_item.source_aks == null OR |pl_item.source_aks| == 0:
      Logge: "[plAgg] SCHEMA-FAIL item={pl_item.id} field=source_aks — leer"
    IF pl_item.source_w == null:
      Logge: "[plAgg] SCHEMA-WARN item={pl_item.id} field=source_w — null (akzeptiert)"

SCHRITT 3: Per-Gruppe PL-Item-Aggregat berechnen (AK-IDF4b-02)
  pl_items = []
  pl_counter = 0
  FOR jede group in groups:
    pl_counter += 1
    pl_id = "{bl_id}-PL-{pl_counter}"

    # Aggregate (mean fuer numerische, union fuer Listen)
    k_scores = [ak.k_score FOR ak in group IF ak.k_score != null]
    srs_scores = [ak.srs_pro_ak FOR ak in group IF ak.srs_pro_ak != null]

    pl_item = {
      id: pl_id,
      ak_refs: [ak.ak_id FOR ak in group],
      k_score_pl: |k_scores| > 0 ? mean(k_scores) : null,
      srs_pl: |srs_scores| > 0 ? mean(srs_scores) : null,
      k_aufwand_pl: mean_or_null([ak.k_aufwand FOR ak in group]),
      k_kopplung_pl: mean_or_null([ak.k_kopplung FOR ak in group]),
      k_fragilitaet_pl: mean_or_null([ak.k_fragilitaet FOR ak in group]),
      spec_refs: union([ak.ak_id FOR ak in group] +
                       flatten([ak.rf_refs FOR ak in group])),
      model_refs: union(flatten([ak.model_refs FOR ak in group])),
      w_offen: sum([ak.w_offen_count FOR ak in group]),
      layer: group[0].layer_hint,                  # Gruppe ist layer-homogen
      dateien_geplant: union(flatten([ak.dateien_hint FOR ak in group])),
      unreife_typ: aggregate_unreife([ak.unreife_typ FOR ak in group]),
      dependencies: union(flatten([ak.dependencies FOR ak in group])) - ak_refs,
      status: "open",
      generated_at: iso_date()  # 2026-04-26 (today)
    }

    # AK-IDF4b-03: suggested_mode-Heuristik (NUR Hint, SDF C3 entscheidet final)
    IF pl_item.k_score_pl != null:
      IF pl_item.k_score_pl < 33:
        pl_item.suggested_mode = "M2"          # Inline / Direct
      ELIF pl_item.k_score_pl < 66:
        pl_item.suggested_mode = "M5"          # SC-Symbiose
      ELSE:
        pl_item.suggested_mode = "M5_OR_M6_OR_M7"  # SC-Symbiose / Analyse / TDD
    ELSE:
      pl_item.suggested_mode = null

    pl_items.append(pl_item)

SCHRITT 4: Idempotenz-Merge mit existing_items (INV-PLA-1)
  merged_items = []
  items_new = 0
  items_existing = 0
  FOR new_item in pl_items:
    existing = existing_items.find(e => e.id == new_item.id)
    IF existing:
      # Merge: behalte status / blocked_by / user-edits, ueberschreibe Aggregate
      merged = {
        ...existing,                    # User-Felder
        ak_refs: new_item.ak_refs,      # ueberschreibe
        k_score_pl: new_item.k_score_pl,
        srs_pl: new_item.srs_pl,
        # ... alle berechneten Felder
        suggested_mode: new_item.suggested_mode,
        regenerated_at: iso_date()
      }
      merged_items.append(merged)
      items_existing += 1
    ELSE:
      merged_items.append(new_item)
      items_new += 1

SCHRITT 5: parking-lot.md schreiben (INV-PLA-2 Aggregat-Block)
  pl_markdown = render_parking_lot(
    bl_id=bl_id,
    items=merged_items,
    aggregate_header={
      total_items: |merged_items|,
      generated_at: iso_date(),
      aggregate_k_score: mean_or_null([i.k_score_pl FOR i in merged_items]),
      aggregate_unreife_typ: aggregate_unreife([i.unreife_typ FOR i in merged_items])
    }
  )
  Write(pl_path, pl_markdown)

SCHRITT 6: BERATER_OUTPUTS.plAggregation schreiben (INV-PLA-3)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.plAggregation = {
    items_total: |merged_items|,
    items_new: items_new,
    items_existing: items_existing,
    aggregate_k_score: mean_or_null([i.k_score_pl FOR i in merged_items]),
    aggregate_unreife_typ: aggregate_unreife([i.unreife_typ FOR i in merged_items]),
    last_berater: "plAggregation"
  })

SCHRITT 7: Exit
  exitcode = |merged_items| > 0 ? 0 : 2
  Logge: "[IDF_PLA] EXIT duration={ms}ms items_total={n} new={items_new} existing={items_existing}"
  EXIT exitcode
```

## aggregate_unreife-Funktion

Hierarchie: `model_unreif > EXTERN > INTERN > ok`. Wenn auch nur ein AK
`model_unreif` ist, ist der ganze PL `model_unreif`. Wenn keiner unreif aber
mind. einer EXTERN, dann EXTERN. Etc.

## Begruendung Modell-Tier

sonnet — Aggregation, Markdown-Listen, Idempotenz-Merge. Sequenziell — kein opus-Bedarf.
