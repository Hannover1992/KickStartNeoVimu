---
status: active
version: 1.0.0
type: berater
parent: _IDF_orchestrate
phase: phase_A
model_tier: middle
created: 2026-05-24
feature_anchor: BL-199
bl_312_ak5: "Entry-3-Verdrahtung — ein PL-Item OHNE per_pl_evaluation-Eintrag (egal welcher Entry: Trickle/Entry-3) wird beim FULL_LOOP automatisch in die IDF-Erstbewertung (plBewertung 3.8) geroutet. loopCheck (FULL_LOOP) ist der Traeger; KEIN neuer Loop-Mechanismus."
bl_312_ak9: "W-state-change Re-Bewertung — bei FULL_LOOP_WITH_REVERSE (modelSync 3.7 Reverse-Naht) werden die affected_pl_items (PL-Items mit w_refs auf geaenderte W{n}) selektiert + zur selektiven 3.8-Re-Bewertung markiert. Traeger = BL-206-Re-Entry-Mechanik; KEIN neuer Mechanismus."
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.pl_snapshot", purpose: "vorheriger PL-Snapshot fuer Vergleich"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items", purpose: "BATCH_ONLY-Pfad: aktuelle Sub-Batch-Liste"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.completed_sub_batches", purpose: "BATCH_ONLY-Pfad: bereits abgeschlossene Batches"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.parking_lot_modified_since_last_idf", purpose: "/_parking-lot Eingriff-Erkennung (BL-201)"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/*.md", path: "PL-Item-Dateien + modtime", purpose: "aktueller PL-Stand fuer Hash-Berechnung"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/*.md", path: "PL-Item typ + status + resurface_trigger", purpose: "BL-323 AK-3: deferred-stage/deferred-ak Items mit erfuelltem Trigger re-surfen (FULL_LOOP / Stage-Resume)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.completed_sub_batches", purpose: "BL-323 AK-3: Trigger-Auswertung (welche Dependency-Batches DONE) + infra-Marker"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.per_pl_evaluation", purpose: "BL-312 AK-5: erkennt PL-Items OHNE Bewertungs-Eintrag (Entry-3/Trickle) — diese braucht 3.8 Erstbewertung im FULL_LOOP. Nur LESEND (Detection); plBewertung 3.8 schreibt."}
    - {file: "{bl_folder}/2_Model/*.md", path: "W{n}-Status + W{n}-Changelog/last_synced", purpose: "BL-312 AK-9: erkennt W-state-changes (bestaetigt/widerlegt/neu seit letztem Snapshot) fuer affected_pl_items-Selektion (FULL_LOOP_WITH_REVERSE)"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.loopCheck", purpose: "decision: FULL_LOOP | BATCH_ONLY | FULL_LOOP_WITH_REVERSE + naechster_batch + reeval_pending_items (AK-5) + affected_pl_items (AK-9)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.pl_snapshot", purpose: "Snapshot-Update nach FULL_LOOP / FULL_LOOP_WITH_REVERSE"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.loopCheck.affected_pl_items", purpose: "BL-312 AK-9: PL-Items mit w_refs auf geaenderte W{n} — Marker fuer selektive 3.8-Re-Bewertung. KEINE Bewertung hier (Detection-only); 3.8 plBewertung rechnet."}
optional: false
invariants:
  - "INV-IDF-LOOP-1: Phase A laeuft VOR resumeGuard (Phase 0) — kein anderer IDF-Berater darf vorher laufen"
  - "INV-IDF-LOOP-2: Snapshot MUSS von loopCheck geschrieben werden — kein anderer Berater schreibt pl_snapshot"
  - "INV-IDF-LOOP-3: BATCH_ONLY-Pfad triggert KEINE Phasen 4-7.6 — nur Sub-Batch-Weitergabe"
  - "INV-IDF-LOOP-4: /_parking-lot Eingriff (parking_lot_modified=true) MUSS FULL_LOOP_WITH_REVERSE ergeben"
  - "INV-IDF-LOOP-5: Hash = SHA256(concat(sorted(item_id + ':' + modtime_iso) fuer alle *.md in 6_PL/))"
  - "INV-IDF-LOOP-6 (BL-323 AK-3): Ein offenes PL-Item typ ∈ {deferred-stage, deferred-ak} mit ERFUELLTEM resurface_trigger MUSS einen FULL_LOOP (Stage-Resume) triggern — wie ein Entry-3-PL-Item, aber 'am Ende' (nach den Dependency-Batches). Ein deferred-Item mit NOCH-NICHT-erfuelltem Trigger bleibt liegen (kein Loop, kein Loch)."
  - "INV-IDF-LOOP-7 (BL-312 AK-5): Jedes PL-Item OHNE Eintrag in DF_BATCH_STATE.per_pl_evaluation (egal welcher Entry: A-Masse, /_parking-lot-Trickle/Entry-3, deferred-Re-Surface) MUSS beim FULL_LOOP die IDF-Erstbewertung (plBewertung Phase 3.8) durchlaufen. Der vorhandene FULL_LOOP (pl_snapshot-Hash-Diff erkennt neue Items) ist der Traeger — KEIN neuer Loop-Mechanismus. 3.8 ist idempotent (bereits bewertete Items werden NICHT re-gerechnet) → genau die un-bewerteten Items werden erstbewertet. Kein Item entgeht der Single-Bewertung, egal wann es entsteht."
  - "INV-IDF-LOOP-8 (BL-312 AK-9): Bei FULL_LOOP_WITH_REVERSE (W-state-change via SC-Mode → modelSync 3.7 Reverse-Naht) MUSS loopCheck die affected_pl_items selektieren = PL-Items mit w_refs auf die geaenderten W{n}. Diese Items werden zur SELEKTIVEN 3.8-Re-Bewertung markiert (nicht-betroffene Items bleiben unveraendert — kein Voll-Recompute). Traeger = BL-206-Re-Entry-Mechanik; KEINE neue Loop-Infra. SRS-only (K-Re-Bewertung DEFERRED an AK-10/BL-311)."
---

# _IDF_berater_loopCheck — IDF Loop-Check + Re-Entry-Mechanik (BL-199)

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_loopCheck — BL-199 (Phase A NEU)             |
+======================================================================+
|  LIEST:                                                              |
|    IDF_PIPELINE_STATE.pl_snapshot  (vorheriger Snapshot, optional)  |
|    DF_BATCH_STATE.batch_items[]    (Sub-Batch-Liste fuer BATCH_ONLY) |
|    DF_BATCH_STATE.completed_sub_batches[]  (bereits fertige Batches) |
|    DF_BATCH_STATE.parking_lot_modified_since_last_idf (BL-201 Guard)|
|    {VAULT}/Backlog/{bl_slug}/6_PL/*.md  (PL-Item-Dateien + mtime)   |
|                                                                       |
|  SCHREIBT:                                                           |
|    BERATER_OUTPUTS.loopCheck = {                                     |
|      decision: "FULL_LOOP" | "BATCH_ONLY" | "FULL_LOOP_WITH_REVERSE"|
|      naechster_batch: batch_id | null,                               |
|      reason: text,                                                    |
|      pl_item_count_current: N,                                       |
|      pl_item_count_snapshot: N | null,                               |
|      snapshot_hash_match: bool | null,                               |
|      reeval_pending_items: [pl_id,...]  (AK-5: un-bewertete Items,   |
|                            die 3.8-Erstbewertung brauchen)          |
|      affected_pl_items: [pl_id,...]     (AK-9: PL-Items mit w_ref    |
|                            auf geaenderte W{n} — selektive Re-Eval)  |
|    }                                                                  |
|    IDF_PIPELINE_STATE.pl_snapshot  (nur bei FULL_LOOP / F_L_W_R)    |
|                                                                       |
|  AUFRUF: Skill(_IDF_berater_loopCheck, args="{BL_ID}")              |
|  PHASE:  Phase A — VOR resumeGuard (Phase 0)                        |
|  ZWECK:  PL-Neuheits-Detection: neue Items → volle Schleife,        |
|          kein Aenderung → nur naechster Batch direkt an SDF         |
|  ANTI:   KEIN Skill()-Aufruf (reine Detection-Logik)                |
+======================================================================+
```

## LOGIK

### SCHRITT 0: Entry — PL-Dateien laden

```
manifest_path = WORKING_DIR + "/_manifest.md"
pl_dir = VAULT + "/Backlog/" + bl_slug + "/6_PL/"

# Alle PL-Item-Dateien einlesen (*.md)
pl_files = list_files(pl_dir, pattern="*.md")
pl_item_count = len(pl_files)

Logge: "[LOOP-CHECK] pl_dir={pl_dir} item_count={pl_item_count}"

IF pl_item_count == 0:
  # Kein PL vorhanden — lasse resumeGuard den Fehler diagnostizieren
  schreibe(manifest_path, BERATER_OUTPUTS.loopCheck, {
    decision: "FULL_LOOP",
    naechster_batch: null,
    reason: "PL-Verzeichnis leer — resumeGuard wird ABORT ausloesen (AK5-PL-1)",
    pl_item_count_current: 0,
    pl_item_count_snapshot: null,
    snapshot_hash_match: null
  })
  RETURN
```

### SCHRITT 1: PL-Hash berechnen (INV-IDF-LOOP-5)

```
# Hash-Input: sorted(item_id + ":" + mtime_iso8601) fuer alle *.md
hash_components = []
FOR f IN sorted(pl_files, key=filename):
  item_id = filename_ohne_extension(f)  # z.B. "PL-199-1"
  mtime = file_mtime_iso8601(f)         # z.B. "2026-05-24T10:00:00Z"
  hash_components.append(item_id + ":" + mtime)

hash_input = "\n".join(hash_components)
current_hash = sha256_hex(hash_input)
current_item_ids = [filename_ohne_extension(f) for f in sorted(pl_files)]

Logge: "[LOOP-CHECK] current_hash={current_hash[:12]}... items={pl_item_count}"
```

### SCHRITT 2: Snapshot laden + vergleichen

```
stored_snapshot = lies(manifest_path).IDF_PIPELINE_STATE.pl_snapshot ?? null
parking_lot_modified = lies(manifest_path).DF_BATCH_STATE.parking_lot_modified_since_last_idf ?? false
```

### SCHRITT 2.5: Deferred-PL Re-Surface-Scan (BL-323 AK-3)

```
# Re-Surfacing-Rail: ein beim Stage/AK-Defer materialisiertes Folge-PL-Item
# (deferral_materialize.py, BL-323 AK-1/AK-4) traegt {typ: deferred-stage|deferred-ak,
# status: deferred, re_surface: true, resurface_trigger: "<Bedingung>"}. Es wird wie ein
# Entry-3-PL-Item behandelt: sobald sein Trigger erfuellt ist, triggert es einen FULL_LOOP
# (Stage-Resume) — aber 'AM ENDE', nach den Dependency-Batches (matcht "Stage 3 nach PL7").
# Solange der Trigger NICHT erfuellt ist, bleibt das Item liegen (kein Loop, kein Loch im
# Work-Stream — es ist getrackt, nicht vergessen). [[feedback_machine_not_context]].

resurfacable = []
FOR f IN pl_files:
  item = parse_frontmatter_or_indexline(f)   # typ, status, re_surface, resurface_trigger
  IF item.typ IN ["deferred-stage", "deferred-ak"] AND item.status == "deferred" AND item.re_surface == true:
    # Trigger-Auswertung deterministisch gegen den AKTUELLEN Vault-State:
    #   - Dependency-Teil ("PL7 done"): pruefe completed_sub_batches enthaelt den Batch.
    #   - Infra-Teil ("docker_up"): pruefe den Infra-Marker (z.B. DF_BATCH_STATE.infra_ready
    #     oder Build-Phase-Signal). Konservativ: unentscheidbar → NICHT erfuellt (liegen lassen).
    trigger_met = evaluate_trigger(item.resurface_trigger, completed_sub_batches, infra_marker)
    IF trigger_met:
      resurfacable.append(item.id)
      Logge: "[LOOP-CHECK] RE-SURFACE: deferred-Item {item.id} Trigger '{item.resurface_trigger}' erfuellt → FULL_LOOP (Stage-Resume, am Ende)"
    ELSE:
      Logge: "[LOOP-CHECK] deferred-Item {item.id} Trigger '{item.resurface_trigger}' NOCH NICHT erfuellt — liegen lassen (getrackt, kein Loop)"

has_resurfacable_defer = len(resurfacable) > 0
```

### SCHRITT 2.6: Un-bewertete PL-Items erkennen (BL-312 AK-5 — Entry-3 → IDF-Erstbewertung)

```
# AK-5 Entry-3-Verdrahtung (INV-IDF-LOOP-7):
# Jedes PL-Item, das (noch) KEINEN Eintrag in DF_BATCH_STATE.per_pl_evaluation traegt,
# braucht die IDF-Erstbewertung (plBewertung Phase 3.8). Das gilt fuer JEDEN Entry-Typ —
# egal ob A-Masse-Item, /_parking-lot-Trickle (Entry-3) oder ein re-surfacendes deferred-Item.
# loopCheck RECHNET hier NICHTS (Detection-only, Berater-Isolation, ANTI: kein Skill()-Aufruf).
# Es ERKENNT nur die un-bewerteten Items und reicht sie als reeval_pending_items weiter; die
# eigentliche Erstbewertung macht Phase 3.8 plBewertung — idempotent: bewertete Items werden
# NICHT re-gerechnet (Schritt-0-Idempotenz-Gate + per-Item-srs-SKIP in plBewertung).
#
# WICHTIG — warum loopCheck der Traeger ist (kein neuer Mechanismus):
#   - Ein NEU eingelegtes /_parking-lot-Item AENDERT den PL-Hash (neue Datei + mtime, INV-IDF-LOOP-5)
#     → SCHRITT 3 entscheidet ohnehin FULL_LOOP (Hash-Mismatch oder parking_lot_modified → F_L_W_R).
#   - Der FULL_LOOP laeuft die volle IDF-Schleife inkl. Phase 3.8 plBewertung.
#   - 3.8 bewertet GENAU die Items ohne per_pl_evaluation-srs → das frische Item wird erstbewertet,
#     ohne dass ein separater Trigger noetig ist. AK-5 macht diese Kausalkette EXPLIZIT + dokumentiert,
#     dass kein Item dem Single-Bewertungs-Ort (P-01 Sanduhr) entgeht, egal wann es entsteht.

evaluated_ids = set(lies(manifest_path).DF_BATCH_STATE.per_pl_evaluation?.keys() ?? [])
reeval_pending_items = [item_id for item_id in current_item_ids IF item_id NOT IN evaluated_ids]

IF len(reeval_pending_items) > 0:
  Logge: f"[LOOP-CHECK] AK-5: {len(reeval_pending_items)} PL-Item(s) OHNE per_pl_evaluation → 3.8-Erstbewertung im FULL_LOOP: {reeval_pending_items}"
ELSE:
  Logge: "[LOOP-CHECK] AK-5: alle PL-Items bereits in per_pl_evaluation bewertet (kein Erstbewertungs-Backlog)"
```

### SCHRITT 2.7: W-state-change → affected_pl_items selektieren (BL-312 AK-9 — Re-Bewertung referenzierender Items)

```
# AK-9 W-state-change-Re-Bewertung (INV-IDF-LOOP-8):
# Waehrend SDF Batches abarbeitet, aendert der Scientific-Mode (SC) W-Zustaende
# (bestaetigt/widerlegt/neu) und modelSync 3.7 promoviert/aktualisiert W{n} (REVERSE-Naht).
# PL-Items, die ein geaendertes W{n} referenzieren (w_refs), haben damit STALE SRS-Werte
# (reused_a4k / alte 3.8-Bewertung). Diese muessen im naechsten Re-Entry SELEKTIV re-bewertet
# werden — NICHT alle Items (kein Voll-Recompute).
#
# Traeger = die VORHANDENE BL-206-Re-Entry-Mechanik: ein FULL_LOOP_WITH_REVERSE (W-state-change →
# parking_lot_modified / Reverse-Naht, INV-IDF-LOOP-4) laeuft die volle Schleife inkl. modelSync 3.7
# und plBewertung 3.8. loopCheck SELEKTIERT hier nur die betroffenen Items (Detection-only, kein
# Skill()-Aufruf) und markiert sie als affected_pl_items; die eigentliche Re-Bewertung macht 3.8.
#
# K-Re-Bewertung ist DEFERRED (AK-10/BL-311 — erst Pin der Code-K-Skala). NUR SRS wird re-bewertet.

affected_pl_items = []
# REVERSE greift, wenn /_parking-lot eingriff (parking_lot_modified=true, INV-IDF-LOOP-4).
# Der Eingriff umfasst auch W-state-changes, die ueber die Entry-3/Reverse-Naht zurueckfliessen.
will_be_reverse = (parking_lot_modified == true)
IF will_be_reverse:
  # Welche W{n} haben sich seit dem letzten Snapshot geaendert?
  #   Quelle: Model-W{n}-Changelog / last_synced > pl_snapshot.snapshot_taken_at,
  #   ODER W{n}-Status-Transition (BESTAETIGT/WIDERLEGT/neu) seit letztem Lauf.
  changed_w_ids = detect_changed_w_nodes(model_path, since=stored_snapshot?.snapshot_taken_at)

  FOR f IN pl_files:
    item = parse_frontmatter_or_indexline(f)   # w_refs / model_refs
    item_w_refs = item.w_refs ?? item.model_refs ?? []
    IF any(w_id IN changed_w_ids for w_id IN item_w_refs):
      affected_pl_items.append(item.id)

  Logge: f"[LOOP-CHECK] AK-9: W-state-change ({changed_w_ids}) → {len(affected_pl_items)} affected_pl_items (selektive 3.8-Re-Bewertung, SRS-only): {affected_pl_items}"
ELSE:
  Logge: "[LOOP-CHECK] AK-9: kein REVERSE-Loop → keine W-state-change-Selektion (affected_pl_items=[])"
```

### SCHRITT 3: Decision-Tree

```
# Prioritaet der Checks (oben gewinnt):
# 1. parking-lot-Eingriff → FULL_LOOP_WITH_REVERSE (INV-IDF-LOOP-4)
# 2. Deferred-PL re-surfacable (Trigger erfuellt) → FULL_LOOP (BL-323 AK-3, INV-IDF-LOOP-6)
# 3. Kein Snapshot → FULL_LOOP (Erst-Eintritt)
# 4. Hash stimmt nicht → FULL_LOOP (neue PL-Items)
# 5. Hash stimmt → BATCH_ONLY (PL unveraendert)
#
# Hinweis: Re-surfacable-Defer steht VOR dem Hash-Check, weil das deferred-Item beim
# Anlegen bereits in den Snapshot-Hash einfloss (es existierte schon) — ein reiner
# Hash-Vergleich wuerde es als 'unveraendert' (BATCH_ONLY) durchwinken und nie nachholen.
# Der Trigger-Wechsel (not-met → met) ist ein STATE-Wechsel, kein PL-Datei-Wechsel.

IF parking_lot_modified == true:
  # /_parking-lot hat neue Items hinzugefuegt (BL-201 Marker)
  decision = "FULL_LOOP_WITH_REVERSE"
  reason = "/_parking-lot Eingriff erkannt (parking_lot_modified=true) — Phase 3.7 REVERSE Sync noetig"
  snapshot_hash_match = null  # irrelevant bei parking-lot-Trigger
  Logge: "[LOOP-CHECK] FULL_LOOP_WITH_REVERSE — parking_lot_modified=true"

ELIF stored_snapshot == null:
  # Erst-Eintritt: kein vorheriger Snapshot
  decision = "FULL_LOOP"
  reason = "Erst-Eintritt — kein Snapshot vorhanden, volle IDF-Schleife (Phase 3.5-7.6)"
  snapshot_hash_match = null
  Logge: "[LOOP-CHECK] FULL_LOOP — Erst-Eintritt, kein Snapshot"

ELIF stored_snapshot.hash != current_hash:
  # Neuer Snapshot weicht ab → neue PL-Items oder aeltere modifiziert
  decision = "FULL_LOOP"
  reason = f"PL-Items veraendert seit letztem IDF-Lauf (hash {stored_snapshot.hash[:8]} ≠ {current_hash[:8]}, old_count={stored_snapshot.item_count} new_count={pl_item_count})"
  snapshot_hash_match = false
  Logge: "[LOOP-CHECK] FULL_LOOP — Hash-Mismatch: neue PL-Items oder Modifikationen"

ELSE:
  # Hash identisch → PL unveraendert
  # → BATCH_ONLY: naechsten offenen Sub-Batch aus DF_BATCH_STATE bestimmen
  batch_items = lies(manifest_path).DF_BATCH_STATE.batch_items ?? []
  completed = lies(manifest_path).DF_BATCH_STATE.completed_sub_batches ?? []
  remaining = [b for b in batch_items IF b NOT IN completed]

  IF len(remaining) == 0:
    # Alle Batches abgeschlossen
    decision = "BATCH_ONLY"
    naechster_batch = null
    reason = "PL unveraendert + alle Sub-Batches DONE — TERMINATE Signal an Orchestrator"
    Logge: "[LOOP-CHECK] BATCH_ONLY — alle Sub-Batches DONE, TERMINATE"
  ELSE:
    decision = "BATCH_ONLY"
    naechster_batch = remaining[0]  # naechster offener Batch
    reason = f"PL unveraendert (hash match) — naechster Sub-Batch: {naechster_batch}"
    snapshot_hash_match = true
    Logge: "[LOOP-CHECK] BATCH_ONLY — naechster_batch={naechster_batch}"
```

### SCHRITT 4: BERATER_OUTPUTS schreiben

```
schreibe(manifest_path, BERATER_OUTPUTS.loopCheck, {
  decision: decision,
  naechster_batch: naechster_batch ?? null,
  reason: reason,
  pl_item_count_current: pl_item_count,
  pl_item_count_snapshot: stored_snapshot.item_count ?? null,
  snapshot_hash_match: snapshot_hash_match ?? null,
  reeval_pending_items: reeval_pending_items,   # AK-5: un-bewertete Items → 3.8-Erstbewertung
  affected_pl_items: affected_pl_items,          # AK-9: W-state-change-betroffene → selektive 3.8-Re-Bewertung (SRS-only)
  evaluated_at: jetzt_iso8601()
})
```

> **AK-5/AK-9 — keine Doppel-Maschine:** `reeval_pending_items` und `affected_pl_items` sind reine
> Detection-Listen fuer Phase 3.8 plBewertung. loopCheck rechnet NICHTS (Berater-Isolation, ANTI:
> kein Skill()-Aufruf). Die Erstbewertung (AK-5) bzw. selektive Re-Bewertung (AK-9) macht der vorhandene
> FULL_LOOP / FULL_LOOP_WITH_REVERSE → Phase 3.8. 3.8 ist idempotent: ein Item ohne `per_pl_evaluation.srs`
> wird bewertet, eines mit srs wird nur dann re-gerechnet, wenn es in `affected_pl_items` steht (W-state-change).

### SCHRITT 5: Snapshot aktualisieren (NUR bei FULL_LOOP / FULL_LOOP_WITH_REVERSE)

```
IF decision IN ["FULL_LOOP", "FULL_LOOP_WITH_REVERSE"]:
  neuer_snapshot = {
    hash: current_hash,
    item_count: pl_item_count,
    item_ids: current_item_ids,
    snapshot_taken_at: jetzt_iso8601(),
    snapshot_source: "idf_loop_check"
  }
  schreibe(manifest_path, IDF_PIPELINE_STATE.pl_snapshot, neuer_snapshot)
  Logge: "[LOOP-CHECK] Snapshot aktualisiert: {current_hash[:12]}... ({pl_item_count} Items)"
  
  # parking_lot_modified Reset nach Verarbeitung
  IF parking_lot_modified == true:
    schreibe(manifest_path, DF_BATCH_STATE.parking_lot_modified_since_last_idf, false)
    Logge: "[LOOP-CHECK] parking_lot_modified-Flag zurueckgesetzt"

ELSE:
  # BATCH_ONLY: kein Snapshot-Update (INV-IDF-LOOP-2 respektiert alter Snapshot)
  Logge: "[LOOP-CHECK] BATCH_ONLY — Snapshot unveraendert"
```

## ANTI-PATTERN

| Anti-Pattern | Folge |
|---|---|
| Snapshot auch bei BATCH_ONLY updaten | Snapshot-Drift — naechster Vergleich falsch |
| parking_lot_modified ignorieren | BL-201 Eingriffe unentdeckt → veraltetes Modell |
| Phase 4-7.6 bei BATCH_ONLY trotzdem laufen | Verletzt INV-IDF-LOOP-3 — unnoetige Reclustering |
| Skill()-Aufruf im Berater | Verletzt Berater-Isolation-Pattern |
| Snapshot ohne item_ids schreiben | Spaeters Debugging unmoeglich |
| SRS in loopCheck rechnen (AK-5/AK-9) | Verletzt Berater-Isolation + Single-Bewertungs-Ort (3.8). loopCheck DETEKTIERT nur, 3.8 RECHNET |
| Eigene Loop-Maschine fuer Entry-3/W-Change bauen | Verletzt INV-IDF-LOOP-7/8 — FULL_LOOP (BL-199) / Reverse-Re-Entry (BL-206) sind die Traeger |
| Bei W-state-change ALLE Items re-bewerten | Verletzt INV-IDF-LOOP-8 — nur affected_pl_items (w_ref auf geaenderte W{n}), kein Voll-Recompute |
| K in affected_pl_items re-rechnen | K-Migration DEFERRED (AK-10/BL-311) — AK-9 ist SRS-only |

## INTEGRATION MIT _IDF_orchestrate

Nach Berater-Return liest Orchestrator `BERATER_OUTPUTS.loopCheck.decision`:

```
decision = BERATER_OUTPUTS.loopCheck.decision

SWITCH decision:
  "FULL_LOOP":
    → normaler IDF-Lauf ab resumeGuard (Phase 0) → Phase 3.5 → 7.6
    → Phase 3.8 plBewertung bewertet GENAU die reeval_pending_items erst (AK-5,
      idempotent: bereits bewertete Items unangetastet) — Entry-3/Trickle gedeckt.
  
  "FULL_LOOP_WITH_REVERSE":
    → normaler IDF-Lauf ab resumeGuard
    → Phase 3.7 modelSync MUSS im REVERSE-Modus laufen (args.reverse_sync=true)
    → Phase 3.8 plBewertung re-bewertet SELEKTIV die affected_pl_items (AK-9, SRS-only;
      W-state-change-betroffene Items) — plus reeval_pending_items (Erstbewertung neuer Items).
      Nicht-betroffene + bereits bewertete Items bleiben unveraendert (kein Voll-Recompute).
  
  "BATCH_ONLY":
    naechster_batch = BERATER_OUTPUTS.loopCheck.naechster_batch
    IF naechster_batch == null:
      → TERMINATE (alle Batches DONE)
    ELSE:
      → GOTO Stufe 6 (TeamDelete) + Auto-Chain zu SDF mit naechster_batch
      → kein resumeGuard, kein Phase 1-7.6 Lauf
```

## AK-5 + AK-9: Single-Bewertungs-Ort, vollstaendig verdrahtet (BL-312)

> **AK-5 (Entry-3 → Erstbewertung):** Heute laufen /_parking-lot-Trickle-Items (Entry-3) am A-Pfad
> vorbei — genau der 486-Schmerz-Pfad. Mit AK-1 wird IDF 3.8 plBewertung der EINE SRS-Erstbewertungs-Ort.
> AK-5 verdrahtet, dass JEDES Item ohne `per_pl_evaluation`-Eintrag (egal welcher Entry) beim naechsten
> IDF-Lauf via loopCheck automatisch dort landet: ein neu eingelegtes PL-Item aendert den pl_snapshot-Hash
> (neue Datei + mtime) → SCHRITT 3 → FULL_LOOP → Phase 3.8 erstbewertet es. **Kein Item entgeht der
> Single-Bewertung, egal wann es entsteht** (Sanduhr-Doktrin P-01 mechanisch wahr). Der Traeger ist der
> vorhandene BL-199-FULL_LOOP — KEIN neuer Mechanismus. Verzahnung AK-8: ein Entry-3-Item ohne w_refs wird
> in 3.8 VOR der Bewertung via W_fetch-light geknuepft (sonst no_truth_refs-Kollaps srs=100).
>
> **AK-9 (W-state-change → selektive Re-Bewertung):** Waehrend SDF Batches abarbeitet, aendert SC W-Zustaende
> (bestaetigt/widerlegt/neu). PL-Items, die ein geaendertes W{n} referenzieren, tragen STALE SRS. AK-9
> verdrahtet ueber die vorhandene BL-206-Re-Entry-Mechanik: bei FULL_LOOP_WITH_REVERSE selektiert loopCheck
> die `affected_pl_items` (w_ref auf geaenderte W{n}), 3.8 re-bewertet GENAU diese (SRS-only). Staleness ist
> by-construction ausgeschlossen — die Bewertung lebt dort, wo die Aenderungen passieren (IDF/Loop). K-Re-Bewertung
> DEFERRED (AK-10/BL-311). KEINE neue Loop-Infra.
>
> **Forward-Verify (AK-6, dormant):** Der Beweis, dass ein Trickle-Item und ein A-Item identische
> Bewertungs-Provenance (`provenance=idf_first_eval`, frischer SRS) tragen, erscheint erst im naechsten
> Live-IDF-Lauf, der beide Entry-Typen mischt (feedback_forward_verification_pattern, BL-173-Praezedenz).
> AK-6 ist daher ein dormant Companion (BL-312-AK-6-PL-1) — kein Bau-Artefakt hier.
