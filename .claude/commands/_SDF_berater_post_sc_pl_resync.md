---
status: active
version: 1.0.0
type: berater
parent: _SDF_orchestrate
phase: phase_3_6b
model_tier: floor
created: 2026-05-24
feature_anchor: BL-208
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.sc_cycle_done", purpose: "Guard: nur ausfuehren wenn SC-Cycle stattgefunden hat"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.current_sub_batch_id", purpose: "aktiver Batch-Key"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.qualityGate.aenderungs_set", purpose: "SC-Output: was hat sich veraendert (REMOVE/Scope/NO-OP/HOLD)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.modelMaintain.delta", purpose: "SC-Output: delta der Model-Aenderungen"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items aktiver Batch", purpose: "Basis fuer PL-Updates"}
  writes:
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Item-Frontmatter (resync_* Felder)", purpose: "Audit-Trail + Status-Update"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.pl_resync_batch_{batch_id}", purpose: "Resync-Summary pro Batch"}
optional: false
invariants:
  - "INV-PL-RESYNC-1: Phase 3.6b MUSS nach SC-Cycle (sc_cycle_done=true) und VOR loopDecision (Phase 4) laufen"
  - "INV-PL-RESYNC-2: Input AUSSCHLIESSLICH SC-Output-Aenderungs-Set (qualityGate + modelMaintain delta)"
  - "INV-PL-RESYNC-3: Berater schreibt NUR Felder mit resync_-Prefix im PL-Item-Frontmatter"
  - "INV-PL-RESYNC-4: Side-Findings HOLD werden als neue PL-Items APPENDED (nicht inline merged)"
  - "INV-PL-RESYNC-5: SKIP wenn sc_cycle_done != true (BERATER_OUTPUTS.pl_resync_batch_X.status = SKIP)"
---

# _SDF_berater_post_sc_pl_resync — Post-SC PL-Resync (BL-208)

## VERTRAG

```
+======================================================================+
|  VERTRAG: _SDF_berater_post_sc_pl_resync — BL-208 (Phase 3.6b NEU)  |
+======================================================================+
|  LIEST:                                                              |
|    DF_BATCH_STATE.sc_cycle_done          (Guard-Bedingung)          |
|    DF_BATCH_STATE.current_sub_batch_id   (aktiver Batch)            |
|    BERATER_OUTPUTS.qualityGate.aenderungs_set  (SC-Delta)           |
|    BERATER_OUTPUTS.modelMaintain.delta         (Model-Delta)        |
|    {VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md (PL-Basis) |
|                                                                       |
|  SCHREIBT:                                                           |
|    {VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md                    |
|      → PL-Item-Frontmatter: resync_at, resync_reason,               |
|                              resync_status, original_hypothesis,     |
|                              resync_scope (bei Scope-Reduktion)      |
|    BERATER_OUTPUTS.pl_resync_batch_{batch_id} = {                   |
|      updated_items: [list],                                          |
|      removed_items: [list],                                          |
|      noop_items: [list],                                             |
|      appended_hold_items: [list],                                    |
|      status: DONE | SKIP | PARTIAL                                   |
|    }                                                                  |
|                                                                       |
|  AUFRUF: Skill(_SDF_berater_post_sc_pl_resync, args="{NAME}")       |
|  PHASE:  SDF Phase 3.6b — nach stageElevation, VOR loopDecision    |
|  ZWECK:  SC-Erkenntnisse in PL-Items propagieren → kein Wissens-Drift|
|  ANTI:   KEIN Mega-Refactor der PL — NUR Aenderungs-Set aus SC     |
+======================================================================+
```

## LOGIK

### SCHRITT 0: Entry — Guard-Check

```
manifest_path = WORKING_DIR + "/_manifest.md"
sc_cycle_done = lies(manifest_path).DF_BATCH_STATE.sc_cycle_done ?? false
batch_id = lies(manifest_path).DF_BATCH_STATE.current_sub_batch_id

IF sc_cycle_done != true:
  # Kein SC-Cycle in diesem Sub-Batch → SKIP
  schreibe(manifest_path, BERATER_OUTPUTS.pl_resync_batch_{batch_id}, {
    status: "SKIP",
    reason: "sc_cycle_done=false — kein SC-Cycle in sub_batch={batch_id}",
    updated_items: [],
    removed_items: [],
    noop_items: [],
    appended_hold_items: []
  })
  RETURN
```

### SCHRITT 1: SC-Output laden

```
qualityGate = lies(manifest_path).BERATER_OUTPUTS.qualityGate.aenderungs_set ?? {}
modelMaintain_delta = lies(manifest_path).BERATER_OUTPUTS.modelMaintain.delta ?? {}

# Aufbereitung des Aenderungs-Sets
aenderungen = merge(qualityGate, modelMaintain_delta)
# aenderungen = {
#   pl_item_id: {
#     signal: "REMOVE" | "SCOPE_REDUCE" | "NO-OP" | "HOLD",
#     neue_scope: text | null,
#     side_finding: text | null,
#     begruendung: text
#   }
# }

IF len(aenderungen) == 0:
  # SC hat keine PL-relevanten Aenderungen gemeldet
  schreibe(manifest_path, BERATER_OUTPUTS.pl_resync_batch_{batch_id}, {
    status: "SKIP",
    reason: "SC hat keine PL-Aenderungen gemeldet (leeres aenderungs_set)",
    ...leere Listen...
  })
  RETURN
```

### SCHRITT 2: PL-Items laden

```
pl_path = VAULT + "/Backlog/" + bl_slug + "/6_PL/" + bl_id + "-parking-lot.md"
pl_items = lies(pl_path).PL-Items  # Liste aller aktiven PL-Items im Batch
```

### SCHRITT 3: Pro PL-Item entscheiden (INV-PL-RESYNC-2)

```
updated_items = []
removed_items = []
noop_items = []
appended_hold_items = []

resync_timestamp = jetzt_iso8601()

FOR pl_item IN pl_items:
  IF pl_item.id NOT IN aenderungen:
    # Keine SC-Aenderung fuer dieses Item → unveraendert lassen
    CONTINUE

  aenderung = aenderungen[pl_item.id]
  original_hypothesis = pl_item.beschreibung  # Originalbeschreibung sichern

  SWITCH aenderung.signal:

    CASE "REMOVE":
      # SC hat erkannt: dieses Item ist nicht mehr relevant / falsch
      # INV-PL-RESYNC-3: NUR resync_* Felder schreiben
      schreibe_pl_item_frontmatter(pl_item, {
        resync_at: resync_timestamp,
        resync_status: "REMOVE",
        resync_reason: aenderung.begruendung,
        original_hypothesis: original_hypothesis
      })
      removed_items.append(pl_item.id)

    CASE "SCOPE_REDUCE":
      # SC hat erkannt: Scope kleiner als urspruenglich angenommen
      alte_scope = pl_item.scope ?? pl_item.beschreibung
      schreibe_pl_item_frontmatter(pl_item, {
        resync_at: resync_timestamp,
        resync_status: "SCOPE_REDUCED",
        resync_reason: aenderung.begruendung,
        original_hypothesis: original_hypothesis,
        resync_scope: aenderung.neue_scope
      })
      # Auch Beschreibung aktualisieren (als sichtbares Signal an I-Worker)
      aktualisiere_pl_item_beschreibung(pl_item, aenderung.neue_scope)
      updated_items.append(pl_item.id)

    CASE "NO-OP":
      # SC bestaetigt: Item bleibt unveraendert, aber ist klar
      schreibe_pl_item_frontmatter(pl_item, {
        resync_at: resync_timestamp,
        resync_status: "NO-OP",
        resync_reason: aenderung.begruendung,
        original_hypothesis: original_hypothesis
      })
      noop_items.append(pl_item.id)

    CASE "HOLD":
      # SC hat Side-Finding: neues PL-Item appenden (INV-PL-RESYNC-4)
      neues_item = {
        id: generiere_hold_id(pl_item.id),
        beschreibung: aenderung.side_finding,
        resync_status: "HOLD",
        resync_at: resync_timestamp,
        resync_reason: "SC Side-Finding: " + aenderung.begruendung,
        original_hypothesis: "N/A (neues Item aus SC Side-Finding)"
      }
      appende_pl_item(pl_path, neues_item)  # INV-PL-RESYNC-4: APPEND, nicht merge
      appended_hold_items.append(neues_item.id)
```

### SCHRITT 4: BERATER_OUTPUTS schreiben

```
status = "DONE"
IF len(updated_items) + len(removed_items) + len(noop_items) + len(appended_hold_items) == 0:
  status = "SKIP"  # Guard passiert aber keine Aenderungen noetig

schreibe(manifest_path, BERATER_OUTPUTS.pl_resync_batch_{batch_id}, {
  status: status,
  updated_items: updated_items,
  removed_items: removed_items,
  noop_items: noop_items,
  appended_hold_items: appended_hold_items,
  resync_timestamp: resync_timestamp,
  sc_aenderungs_set_size: len(aenderungen)
})
```

### SCHRITT 5: Log-Ausgabe

```
Logge: "[POST-SC-PL-RESYNC] batch={batch_id} status={status}"
Logge: "  updated={len(updated_items)} removed={len(removed_items)}"
Logge: "  noop={len(noop_items)} hold_appended={len(appended_hold_items)}"
```

## ANTI-PATTERN

| Anti-Pattern | Folge |
|---|---|
| PL gesamt-refresh (nicht nur SC-Delta) | Verletzt INV-PL-RESYNC-2 — Mega-Refactor |
| resync ohne sc_cycle_done-Guard | Berater laeuft sinnlos ohne SC-Context |
| Side-Finding inline in bestehendes PL-Item mergen | Verletzt INV-PL-RESYNC-4 |
| Felder ohne resync_-Prefix schreiben | Verletzt INV-PL-RESYNC-3 |
| Berater ruft Skill() auf | Verletzt INV-STAGE-ELEV-5-Analogie (reine Decision-Logik) |

## MOTIVATION (BL-208, DCSRE-486)

SC erkannte in DCSRE-486 batch_v3_05 (2026-05-22):
- F13 = REMOVE (nicht IMPL)
- H2 = 3 Felder statt 10

Ohne Phase 3.6b: I-Worker haette 10 VERALTETE PL-Items gelesen → 10 falsche Impl.
BL-193 BATCH-4 nutzte manuellen DEFER-Workaround → jetzt prozessual verankert.
