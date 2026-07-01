---
status: active
version: 0.2.0
type: berater
parent: _IDF_orchestrate
phase: phase_3.6
model_tier: middle
created: 2026-04-25
feature_anchor: BL-142
optional: false
migrated_from: _SDF_berater_itemContext
batch_aware: true
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items / IDF_PIPELINE_STATE.task_source / BDF_BATCH_STATE.bl_items", purpose: "Item-Liste fuer Per-Item-Berater"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Item-Texte", purpose: "PL-Zweig"}
    - {file: "Vault-Frontmatter (BL-Items)", path: "blocked_by, reifegrad, status, spec_link, title", purpose: "BL-Zweig"}
    - {file: ".claude/models/{NAME}_Model.md", path: "TC-Headers", purpose: "tc_scope-Selektion"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.itemContext_per_item[]", purpose: "Per-Item ak_metadata"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.itemContext.batch_summary", purpose: "Aggregat (total, blocked_count)"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "Item-Status [STATUS: IN_ARBEIT] (PL-Zweig)", purpose: "Status-Annotation"}
    - {file: "Vault-Frontmatter (BL)", path: "status=BLOCKED|IN_PROGRESS", purpose: "BL-Zweig"}
    - {file: ".claude/analysis/_backlog_index.md", path: "Status-Spalte", purpose: "Index-Sync"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser itemContext / itemContext_per_item)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE direkt"}
  calls: []
---

# _IDF_berater_itemContext (Phase 3.6 in _IDF_orchestrate)

> **Zweck:** Migriert aus SDF. Per-Item Kontextaufbau (PL/BL-Zweig), Blocker-Pruning, TC-Scope-Selektion. Batch-aware.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_itemContext                                   |
+======================================================================+
|  LIEST:                                                              |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      DF_BATCH_STATE.batch_items                                      |
|      IDF_PIPELINE_STATE.task_source ("pl" | "backlog")               |
|      BDF_BATCH_STATE.bl_items (BL-Zweig)                             |
|    {VAULT}/Backlog/{bl_slug}/6_PL/                       |
|      {bl_id}-parking-lot.md (PL-Zweig)                               |
|    Vault-Frontmatter (BL-Items)                                      |
|      blocked_by[], reifegrad, status, spec_link, title               |
|    Blocker-Vault-Items (blocked_by[]-Traversal)                      |
|    .claude/models/{NAME}_Model.md (TC-Headers)                       |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      BERATER_OUTPUTS.itemContext_per_item[]                          |
|      BERATER_OUTPUTS.itemContext.batch_summary                       |
|    PL-Zweig:                                                         |
|      {VAULT}/.../{bl_id}-parking-lot.md (Item [STATUS: IN_ARBEIT])  |
|    BL-Zweig:                                                         |
|      Vault-Frontmatter.status = BLOCKED | IN_PROGRESS                |
|      _backlog_index.md Status-Spalte                                 |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser itemContext + itemContext_per_item)     |
|    IDF_PIPELINE_STATE direkt                                         |
|    Modus (BL-405: itemContext gibt KEINEN Modus vor —               |
|      INV-MODUS-1: NUR C3 _SDF_berater_modusEntscheidung entscheidet)  |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 3.6                                   |
|                                                                      |
|  MODELL-TIER: sonnet (User-Direktive 2026-05-17 — haiku verboten)    |
|    Begruendung: haiku war Original (TC2) aber unzuverlaessig bei     |
|    mehrstufigen Vault-Reads/Map-Aggregation. Permanent sonnet.        |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-2 (Write-Isolation auf BERATER_OUTPUTS.itemContext)           |
|    INV-6 (blocked=true → Alpha-Beta-Pruning)                         |
|    NFR-3 (Idempotenz: "[STATUS: IN_ARBEIT]" Guard)                  |
|    INV-MODUS-1 (BL-405: itemContext gibt KEINEN Modus vor; reifegrad |
|      routet bereits upstream A/IDF/SDF — C3 entscheidet allein aus    |
|      k-score/srs/coverage)                                           |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - _berater_outputs.md existiert (M1 GATE PASS)                    |
|    - item_id + cycle_nr in _berater_outputs.md gesetzt               |
|    - task_source bekannt                                             |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - BERATER_OUTPUTS.itemContext_per_item[] vollstaendig             |
|    - BERATER_OUTPUTS.itemContext.batch_summary gesetzt               |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_itemContext, args="{NAME}")

Parameter:
  {NAME} - Feature-Name oder bl_id

Ausgabe:
  - BERATER_OUTPUTS.itemContext_per_item[]
  - BERATER_OUTPUTS.itemContext.batch_summary
  - Exitcode: 0=OK, 1=PRUNED (alle blocked), 2=FAIL

Logging-Format:
  [IDF_IC] ENTRY cycle_nr={n} batch_size={k}
  [IDF_IC] EXIT duration={ms}ms batch_total={k} blocked={n}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  itemContext_per_item:
    - {item_id: "BL-142-PL-1", item_type: "PL", blocked: false, tc_scope: ["TC-2"]}
  itemContext:
    batch_summary:
      total: 1
      blocked_count: 0
    last_berater: "itemContext"
```

> **BL-405 (INV-MODUS-1-Bereinigung):** itemContext liefert NUR noch `{item_id, item_type, blocked, tc_scope}` — **KEIN Modus-Feld mehr**. Der frueher hier berechnete `reifegrad→Modus (M1/M7/null)`-Pfad war Altschuld: er verletzte INV-MODUS-1 (Modus wird AUSSCHLIESSLICH von C3 = _SDF_berater_modusEntscheidung aus k-score/srs/coverage entschieden). reifegrad routet bereits upstream (A/IDF/SDF) — itemContext gibt keinen Modus mehr vor.

## Schritte (aus SDF Z930-1037 extrahiert, IDF-Pfad-Adaption)

```
SCHRITT 0: Entry-Log + item_type bestimmen
  [IDF_IC] ENTRY cycle_nr={cycle_nr} batch_size={len(DF_BATCH_STATE.batch_items)}
  item_type = IDF_PIPELINE_STATE.task_source
    ("pl" -> "PL", "backlog" -> "BL", sonst -> "direct")
  batch_items = DF_BATCH_STATE.batch_items  # BL-140: Batch-Aware

SCHRITT 1: FOR item IN batch_items (BL-140 Batch-Loop)
  item_id = item.id
  item_context_result = {}

SCHRITT 1a: PL-Zweig (wenn item_type == "PL")
  pl_path = "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"
  Lies pl_path -> suche Item mit ID/Name = {item_id}
  IF pl_item nicht gefunden:
    Logge WARNUNG: "[IDF_IC] PL-Item '{item_id}' nicht gefunden"
    blocked = false; tc_scope = "ALL"
    -> SCHRITT 3 (Output)
  ELSE:
    # Idempotenz-Guard (NFR-3)
    IF "[STATUS: IN_ARBEIT]" NOT IN pl_item.text:
      pl_path: Ersetze "[ ] {item_id}" mit "[ ] {item_id} [STATUS: IN_ARBEIT]"
    blocked = false  # PL-Items haben kein blocked_by-Konzept

SCHRITT 1b: BL-Zweig (wenn item_type == "BL")
  bl_batch_info = BDF_BATCH_STATE.bl_items.find(bl.id == item_id)
  bl_vault_path = bl_batch_info.vault_path ?? null
  bl_reifegrad  = bl_batch_info.reifegrad ?? "UNREIF"
  bl_frontmatter = Lies bl_vault_path -> Frontmatter (YAML)

  # Blocker-Verifikation (SDF Z967-994, BL-113a-FIX-10)
  blocked_by_list = bl_frontmatter.blocked_by ?? []
  blocker_not_done = []
  FUER blocker_id IN blocked_by_list:
    blocker_path = finde Vault-Item mit id = blocker_id
    IF blocker_path == null:
      Logge WARNUNG: "[IDF_IC] Blocker {blocker_id} nicht gefunden — Guard skip"
      CONTINUE
    blocker_fm = Lies blocker_path -> Frontmatter
    IF blocker_fm.status != "DONE":
      blocker_not_done.append({id: blocker_id, status: blocker_fm.status})

  IF len(blocker_not_done) > 0:
    # Alpha-Beta-Pruning Ausloeser (INV-6)
    Schreibe Vault-Frontmatter.status = "BLOCKED"
    Schreibe Vault-Frontmatter.blocked_reason = "Blockers: " + join(ids)
    Aktualisiere _backlog_index.md (Status: BLOCKED fuer {item_id})
    blocked = true
    -> SCHRITT 3 (Output — exitcode PRUNED)

  ELSE:
    # Status-Transition IN_PROGRESS (SDF Z996-999)
    Schreibe Vault-Frontmatter.status = "IN_PROGRESS"
    Aktualisiere _backlog_index.md (Status: IN_PROGRESS)

    # BL-405 (INV-MODUS-1-Bereinigung): KEIN reifegrad-zu-Modus Mapping mehr.
    # itemContext gibt KEINEN Modus vor — der Modus wird AUSSCHLIESSLICH von C3
    # (_SDF_berater_modusEntscheidung) aus k-score/srs/coverage entschieden.
    # reifegrad routet bereits upstream (A/IDF/SDF), C3 braucht hier keinen Override.

    blocked = false

SCHRITT 2: TC-Selektion (SDF Z1020-1036)
  model_tcs = parse_tc_headers(".claude/models/{NAME}_Model.md")
  matched_tcs = keyword_match(item_text, item_tags, model_tcs)
  IF matched_tcs.length == 0:
    tc_scope = "ALL"  # Degraded Mode
    Logge WARNUNG: "[IDF_IC] Kein TC-Match — lade gesamtes Model (degraded)"
  ELSE:
    tc_scope = expand_tc_dependencies(matched_tcs)
    Logge: "[IDF_IC] TC-Scope: {tc_scope}"

SCHRITT 3: Item-Output sammeln (BL-140 Batch-Loop)
  item_context_result = {
    item_id: {item_id},
    item_type: {item_type},        # BL | PL | direct
    blocked: {blocked},
    tc_scope: {tc_scope}
  }
  # BL-405: kein Modus-Feld mehr (INV-MODUS-1: C3 entscheidet Modus allein).
  BERATER_OUTPUTS.itemContext_per_item.append(item_context_result)

END_FOR  # Ende batch_items Loop

SCHRITT 4: Batch-Aggregat schreiben (BL-140)
  blocked_items = [i FOR i IN itemContext_per_item IF i.blocked == true]
  # BL-405: kein Modus-Aggregat mehr (itemContext gibt keinen Modus vor — INV-MODUS-1).
  BERATER_OUTPUTS.itemContext.batch_summary = {
    total: len(batch_items),
    blocked_count: len(blocked_items)
  }
  _berater_outputs.md Frontmatter: last_update={jetzt}, last_berater="itemContext"

SCHRITT 5: Exit-Log
  blocked_count = BERATER_OUTPUTS.itemContext.batch_summary.blocked_count
  [IDF_IC] EXIT duration={ms}ms batch_total={len(batch_items)} blocked={blocked_count}
```

## Risiko-Hinweis

HD01-OBS-1 (R4 LOW): haiku evtl. zu niedrig bei vielen blocked_by-Eintraegen (mehrere Vault-Reads). AK-4 prueft nach Deployment; Tier-Upgrade zu sonnet ohne Spec-Aenderung moeglich (ADR-D). **AUFGEHOBEN 2026-05-17: User-Direktive verbietet haiku — Tier permanent sonnet.**

## Begruendung Modell-Tier

**sonnet** (User-Direktive 2026-05-17). Vorher haiku (TC2) — aufgehoben weil haiku bei mehrstufigen Sequenzen (Vault-Reads + Map-Aggregation) zu unzuverlaessig (BL-NEW-51 Geist). Tier ist PERMANENT sonnet, kein Downgrade erlaubt.
