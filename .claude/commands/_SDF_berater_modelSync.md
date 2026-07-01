---
status: active
version: 1.2
created: 2026-05-09
last_synced: 2026-06-10
op: SmallDarkFactory
phase: 3.5
type: berater
parent: _SDF_orchestrate
chain_position: middle
model_tier: ceiling
feature_anchor: BL-166
ak_implements: [BL-238-AK-5, BL-238-AK-6, BL-255-AK-1, BL-255-AK-2, BL-255-AK-3, BL-255-AK-5, BL-255-AK-6, BL-255-AK-10]
---

# /_SDF_berater_modelSync (Phase 3.5 — Round-Erkenntnisse → Model/Spec)

> **Zweck:** Continuous-Learning-Phase **PRO ROUND** im SDF-Outer-Loop.
> Erkenntnisse aus Round-N (neue PL-Items, Code-Pattern-Discoveries, Test-
> Findings, Mode-Wahl-Erfolg/Fehler) werden zurueck zu Model.md/Spec.md/PL
> synchronisiert BEVOR Round-N+1 startet — naechster Phase 1.1 sieht
> aktualisierten Vault-State.
>
> **Big Picture (BL-165 D-Architektur 2026-05-09):**
> Analog `_IDF_berater_modelSync` (Phase 3.7) — aber pro Round im SDF-Loop,
> nicht einmalig in IDF. SDF schliesst den Feedback-Loop:
> Implementation → Erkenntnisse → Model → naechste Mode-Decision.

[VERTRAG]
LIEST:
  - {WORKING_DIR}/_manifest.md
    → DF_BATCH_STATE.current_sub_batch_id (welcher Round)
    → DF_BATCH_STATE.current_sub_batch_items (welche Items)
    → BERATER_OUTPUTS.executionDispatch.dispatches[-1] (letzter Round-Dispatch)
    → BERATER_OUTPUTS.recalibrate (K-Score-Updates aus Round)
    → BERATER_OUTPUTS.postBatch (GAP-Updates aus Round)
  - {bl_folder}/6_PL/{bl_id}-parking-lot.md (NEUE PL-Items aus Implementation)
  - {bl_folder}/2_Model/{NAME}_Model.md (existing W{n} fuer Idempotenz)
  - {bl_folder}/3_Spec/{NAME}_Spec.md (existing Constraints + AK-Status/model_refs fuer 3.5c)
  - {bl_folder}/2_Model/_modelSync_log_{DATE}.md (existing Log fuer Append-Only)
  - {bl_folder}/Implementation/{NAME}-VERIFY-{SLICE}.md (verify_report: _I_verify-Verdikte pro AK,
    FALLBACK .claude/analysis/synthese/{NAME}-VERIFY-{SLICE}.md — Input fuer SCHRITT 3.5c, BL-255 AK-1)

SCHREIBT:
  - {bl_folder}/2_Model/{NAME}_Model.md (NEUE W{n}, append, mit Source-Ref;
    + W-Status-Transitionen "AKTIV (BESTAETIGT)"/WIDERLEGT + Provenance + Frontmatter-Zaehler
      via _SC_modelMaintain-Konvention — SCHRITT 3.5c, BL-255 AK-2/AK-6)
  - {bl_folder}/3_Spec/{NAME}_Spec.md (NEUE Constraints, append;
    + AK-Status-Felder status/confirmed_by/confirmed_at/verify_ref/gap_reason — SCHRITT 3.5c, BL-255 AK-1)
  - {bl_folder}/6_PL/{bl_id}-parking-lot.md (synced-to-model Marker pro Item)
  - {bl_folder}/2_Model/_modelSync_log_{DATE}.md (Append-Only Log)
  - {WORKING_DIR}/_manifest.md
    → BERATER_OUTPUTS.modelSync_round_{batch_key} = {schema unten}
    → DF_BATCH_STATE.truth_to_batches[W{n}] = [{batch, pl_item, k_score, srs}]   # BL-238-AK-5/AK-6: Cross-Batch-Index beim W{n}->PL-Promote (Schema SOA-2 bindend)
    → DF_BATCH_STATE.per_pl_evaluation[pl_item] (frischer srs/k_score, additiv) # BL-238-AK-5: Cross-Batch-Propagations-Ziel (Slot-Isolation PT-CMD-008)
    → DF_BATCH_STATE.batch_items[batch] (frischer srs/k_score, additiv)         # BL-238-AK-5: Cross-Batch-Propagations-Ziel (Slot-Isolation PT-CMD-008)
  # INV-MODUS-1: KEIN Write an DF_BATCH_STATE.modus / kein INV-MODUS-5-Bypass-Feld — Cross-Batch betrifft SRS/K-Score-Metrik, NICHT modus.

BERATER_OUTPUTS.modelSync_round_{batch_key}:
  round_id:                 {batch_key}        # e.g. "batch_2"
  promoted_truths_count:    int                # neue W{n}
  promoted_constraints_count: int              # neue Spec-Constraints
  new_pl_items_count:       int                # neue PL-Items aus Round
  skipped_items_count:      int                # nicht-stabil
  total_items_evaluated:    int
  promoted_items_ids:       list[string]
  log_path:                 string
  exit_code:                0 OK | 1 WARN | 2 ABORT
  confirm_collapse:                            # BL-255 AK-10 (SCHRITT 3.5c; No-Op-Round => Nullwerte)
    collapsed_aks:          int                # AKs -> confirmed
    collapsed_ws:           int                # W{n} -> AKTIV (BESTAETIGT), nur ECHTE Transitionen
    falsified_aks:          int                # AKs -> widerlegt
    deferred_shared_w:      list[W{n}]         # Shared-W mit offenen Traegern (AK-3)
    skipped_experiment_provable: list[W{n}]    # M5-Kategorie, nie via Abnahme (AK-5)
    gap_reasons:            map[ak_id->string] # GAP-Verdikte (AK-6)

PFLICHT-LOGGING:
  [SDF-modelSync] ROUND={batch_key} reading PL: {path} ({n_new_items} items)
  [SDF-modelSync] ROUND={batch_key} promote: {item_id} → W{n} "{truth}"
  [SDF-modelSync] ROUND={batch_key} skip:    {item_id} (reason: ...)
  [SDF-modelSync] 3.5c ROUND={batch_key} {confirm|gap|falsify}: {ak_id} → {aktion} (BL-255)
  [SDF-modelSync] 3.5c ROUND={batch_key} DONE — {A} AKs confirmed, {W} W kollabiert, {D} deferred, {S} skipped
  [SDF-modelSync] ROUND={batch_key} DONE — {N} truths, {M} constraints persisted

[/VERTRAG]

[INVARIANTEN]

- INV-MS-SDF-1: IDEMPOTENT — Items mit Marker `synced-to-model:` werden uebersprungen
- INV-MS-SDF-2: CONSERVATIVE — nur STABILE Erkenntnisse promoviert. Kriterien:
    a) PL-Item hat `[x]` Status (Round-Item DONE)
    b) PL-Item hat Test-Pass-Marker (Tests gruen) ODER
    c) PL-Item hat Audit-Marker ODER
    d) PL-Item hat Pattern-Discovery-Tag (neuer Code-Pattern erkannt)
  ELSE: skip (lieber zu wenig als falsche Wahrheit)
- INV-MS-SDF-3: SOURCED — jede neue W{n} hat Source-Reference:
    "Source: BL-{ID}-PL-{NR} (Round-{batch_key} {DATE})"
- INV-MS-SDF-4: APPEND-ONLY — Model + Spec werden NUR erweitert, nie ueberschrieben
- INV-MS-SDF-5: VERSIONING — Model + Spec Frontmatter-Update:
    version: X.Y → X.(Y+1)
    last_synced: {ISO_DATE}
    synced_from_round: {batch_key} (Audit-Trail)
- INV-MS-SDF-6: PFLICHT-LOG — _modelSync_log_{DATE}.md mit kompletter Round-Traceability
- INV-MS-SDF-7: CONFLICT-DETECTION — wenn neue Truth existiertem W{n} widerspricht:
    Logge WARNING + skip (User-HiL-Direktive: bei Konflikt manuell aufloesen)
- INV-MS-SDF-8 (NEU): ROUND-AWARE — Output-Schluessel `modelSync_round_{batch_key}`
    statt Single — pro Round ein eigener Eintrag fuer Audit ueber Outer-Loop
- INV-MS-SDF-9 (BL-238-AK-5/AK-6): CROSS-BATCH — geaenderte W{n} propagieren index-getrieben
    (NUR `truth_to_batches[W{n}]`, kein Voll-Scan) frischen SRS via `_srs_compute` (BL-205,
    EINZIGE SRS-Quelle) in fremde PL-Items; additiv (INV-MS-SDF-4), idempotent (INV-MS-SDF-1),
    konflikt-bewusst (INV-MS-SDF-7); KEIN Modus-Write (INV-MODUS-1).
- INV-MS-SDF-10 (BL-255, 2026-06-10): CONFIRM-KOLLAPS (SCHRITT 3.5c) —
    a) DETERMINISTISCH (NFR-5): Verdikt-Weiche, Filter-Ordnung und Traeger-Lookup sind
       regelbasiert auswertbar (sortierte Traversal-Ordnung) — KEIN LLM-Ermessen im
       Transition-Entscheid.
    b) IDEMPOTENT (NFR-1): Re-Run auf bereits kollabierten AKs/W{n} ist No-Op — keine
       Doppel-Transitionen, keine Doppel-Zaehler-Inkremente, identischer confirm_collapse-Block.
    c) INV-SRS-5-KONFORM (NFR-2): AUSSCHLIESSLICH Status-Transitionen — an KEINER Stelle wird
       eine srs-Zahl direkt geschrieben; der srs faellt mechanisch beim naechsten C5-Recompute.
    d) INV-SRS-6-KONFORM (NFR-3): jede BESTAETIGT-Transition traegt whitelisted `confirmed_by`
       + Pflicht-Evidenz (`verify_ref` + `confirmed_at`); Whitelist-SINGLE-SOURCE ist
       `_srs_compute.md` INV-SRS-6 (hier KEINE Kopie pflegen).
    e) ABGRENZUNG zu INV-MS-SDF-4: Status-/Provenance-FELD-Transitionen an bestehenden
       AKs/W{n} nach der BL-255/_SC_modelMaintain-Konvention sind ERLAUBT (analog
       modelMaintain selbst) — Inhalt/Aussage der W{n} wird NIE ueberschrieben.

[/INVARIANTEN]

## Aufruf-Interface

```
Skill(_SDF_berater_modelSync, args="{NAME} {batch_key}")

Parameter:
  {NAME}      - Feature/BL-Name
  {batch_key} - aktuelle Round (e.g. "batch_2")

Vorbedingung:
  - DF_BATCH_STATE.current_sub_batch_id == {batch_key}
  - Phase 3.1 (recalibrate) + 3.2 (postBatch) + 3.3 (statusTransition) DONE
  - Outer-Loop aktiv (sonst SKIP)

Ausgabe:
  - BERATER_OUTPUTS.modelSync_round_{batch_key}
  - Exitcode: 0=OK, 1=WARN (nichts promoviert), 2=ABORT
```

## Schritte

```
SCHRITT 0: Entry + Vorbedingungen
  batch_key = args[1]
  Logge: "[SDF-modelSync] ROUND={batch_key} ENTRY"

  IF DF_BATCH_STATE.current_sub_batch_id != batch_key:
    Logge FEHLER: "[SDF-modelSync] state mismatch — current_sub_batch={DF_BATCH_STATE.current_sub_batch_id} vs args={batch_key}"
    EXIT exitcode=2

SCHRITT 1: Lese aktuelle Round-Outputs
  exec_dispatch  = BERATER_OUTPUTS.executionDispatch.dispatches[-1]  # letzter Eintrag = aktuelle Round
  recalibrate    = BERATER_OUTPUTS.recalibrate
  postBatch      = BERATER_OUTPUTS.postBatch

SCHRITT 2: Lese Vault-PL fuer NEUE Items
  pl_items = read({bl_folder}/6_PL/{bl_id}-parking-lot.md)
  # Filter: nur Items mit created/updated nach Round-Start
  round_new_items = filter(pl_items, item => item.last_modified >= round_start_ts)

  Logge: "[SDF-modelSync] ROUND={batch_key} reading PL: {n_new_items} new items"

SCHRITT 3: Promotion-Loop pro neuem Item
  promoted_truths = []
  promoted_constraints = []
  skipped = []

  FOR item IN round_new_items:
    IF item.has_marker("synced-to-model:"):
      skipped.append(item.id, "already_synced")
      CONTINUE

    # INV-MS-SDF-2 Stable-Check
    IF NOT (item.status == "[x]" OR item.has_test_pass OR item.has_audit OR item.has_pattern_discovery):
      skipped.append(item.id, "not_stable")
      CONTINUE

    # INV-MS-SDF-7 Conflict-Detection
    truth_text = extract_truth(item)
    existing_w = find_existing_W(model, truth_text)
    IF existing_w AND existing_w.contradicts(truth_text):
      Logge WARNING: "[SDF-modelSync] CONFLICT — {item.id} vs {existing_w.id}"
      skipped.append(item.id, "conflict")
      CONTINUE

    # Promotion
    new_w = generate_new_W(truth_text, source=item.id, round=batch_key)
    append_to_model(new_w, source_ref="BL-{ID}-{item.id} (Round-{batch_key} {DATE})")
    promoted_truths.append(new_w.id)

    # BL-238-AK-6 Index-Write (Producer): truth_to_batches[W{n}]-Eintrag beim W{n}->PL-Promote.
    # Schema SOA-2 bindend {batch, pl_item, k_score, srs} (PT-CMD-016 maschinenlesbar). Append-only,
    # per-W{n}-Key MERGE-additiv (PT-CMD-015); kein Voll-Ueberschrieb (INV-MS-SDF-4).
    DF_BATCH_STATE.truth_to_batches[new_w.id].append({
      batch:    DF_BATCH_STATE.current_sub_batch_id,
      pl_item:  item.id,
      k_score:  item.k_score,
      srs:      item.srs
    })

    # Spec-Constraints (falls anwendbar)
    IF item.has_constraints:
      append_to_spec(item.constraints, source_ref="BL-{ID}-{item.id}")
      promoted_constraints.extend(item.constraints)

    # Marker setzen in PL
    set_marker(item, "synced-to-model: {DATE}")

  Logge: "[SDF-modelSync] ROUND={batch_key} promote summary: {|promoted_truths|} W, {|promoted_constraints|} Constraints, {|skipped|} skipped"

SCHRITT 3.5c: Confirm-Kollaps — Abnahme-Verdikt → AK-Status → W-Propagation (BL-255, 2026-06-10)
  # Die Ausgangs-Seite des Wahrheits-Kreises (BL-251 = Eingang): _I_verify-Verdikte kollabieren
  # AKs und getragene W{n} von OFFEN → BESTAETIGT/WIDERLEGT. Der srs faellt dadurch MECHANISCH
  # beim naechsten recalibrate-C5-Recompute (BESTAETIGT-Familie → srs_weight 0.0) — KEINE
  # Formel-Aenderung (NFR-4), KEIN direktes srs-Schreiben (INV-SRS-5/NFR-2). Design: Option A
  # (W-Propagation) mit Shared-W-Schutz, BL-255_Spec Sektion 1.1 (W30/W32-Entscheidung).
  #
  # POSITION: VOR SCHRITT 3.5 (Cross-Batch), damit kollabierte W{n} noch in DIESER Round in
  # fremde Batches ausstrahlen. "3.5c" ist der kanonische BL-255-Phase-Name (SDF Phase 3.5,
  # Sub-Schritt c), nicht die Dokument-Numerik.
  # REIHENFOLGE-KONTRAKT (BL-255 AK-7, W33): 3.5c persistiert Status VOR dem NAECHSTEN C5-Lauf.
  # Im heutigen Post-Flow laeuft C5 VOR Phase 3.5 (Off-by-one-Latenz, W33 empirisch belegt) —
  # der Order-Swap/C5-Re-Run ist batch_PL3 (dispatch_implement.js), NICHT Teil dieses Schritts.

  # ── (a) Eingang: verify_report der Round [BL-255 AK-1] ──
  # Schema (BL-255_Spec Sektion 5): pro AK {ak_id, verdict: VERIFIED|GAP, verify_mode:
  # tdd|scenario|convention, evidence_ref, timestamp}. Quelle: _I_verify-Report der Round
  # ({bl_folder}/Implementation/{NAME}-VERIFY-{SLICE}.md, FALLBACK .claude/analysis/synthese/).
  # Bis die V2-Formalisierung in _I_verify deployed ist: Verdikt-Zeilen des VERIFY-Reports
  # tolerant parsen — nur Verdikte mit EINDEUTIGEM AK-Anker (ak_id) konsumieren, Rest skip+Log.
  verify_reports = read_verify_verdicts(round=batch_key)
  IF verify_reports leer:
    Logge: "[SDF-modelSync] 3.5c ROUND={batch_key}: kein verify-Verdikt — No-Op"
    confirm_collapse = {collapsed_aks: 0, collapsed_ws: 0, falsified_aks: 0,
                        deferred_shared_w: [], skipped_experiment_provable: [], gap_reasons: {}}
    collapsed_ws_ids = []
    → weiter SCHRITT 3.5 (kein Blocker)

  confirm_collapse = {collapsed_aks: 0, collapsed_ws: 0, falsified_aks: 0,
                      deferred_shared_w: [], skipped_experiment_provable: [], gap_reasons: {}}
  collapsed_ws_ids = []     # Andock an SCHRITT 3.5 Cross-Batch (kollabierte W strahlen aus)

  FOR report IN sort(verify_reports, by=ak_id):        # deterministische Ordnung (NFR-5)
    ak = spec.find_ak(report.ak_id)                     # 3_Spec der {bl_folder}

    # ── (b) Signal-Weiche [BL-255 AK-6]: GAP ≠ Widerlegung ──
    SWITCH:
      CASE report.verdict == "GAP":
        # Coverage-Luecke, KEINE Widerlegung: AK bleibt/wird open + gap_reason. KEIN W-Touch.
        IF ak.status == "confirmed":
          # Konflikt (bereits bestaetigte AK vs. neue Luecke): NICHT zurueckstufen —
          Logge WARNING: "[SDF-modelSync] 3.5c CONFLICT — {ak_id} confirmed, GAP-Verdikt; manuell aufloesen (INV-MS-SDF-7)"
        ELSE:
          ak.status = "open"
          ak.gap_reason = report.begruendung
        confirm_collapse.gap_reasons[report.ak_id] = report.begruendung
        Logge: "[SDF-modelSync] 3.5c ROUND={batch_key} gap: {ak_id} → open (gap_reason gesetzt) (BL-255)"
        CONTINUE

      CASE explizites Widerlegungs-Signal:
        # NUR: Test schlaegt GEGEN die AK-Behauptung fehl MIT Begruendung, oder SC-Verdikt
        # widerlegt. Eine blosse Coverage-Luecke (GAP) ist NIE ein Widerlegungs-Signal.
        ak.status = "widerlegt"                         # Vokabular-Erweiterung, _spec.md (AK-1)
        ak.verify_ref = report.evidence_ref             # Widerlegungs-Evidenz dokumentieren
        confirm_collapse.falsified_aks += 1
        # W-Falsify NUR fuer exklusiv getragene W{n} — SYMMETRISCHER Shared-Schutz (AK-3):
        FOR w IN sort(ak.model_refs):
          traeger = alle AKs der Spec mit w in model_refs/W{n}-Edge   # deterministischer Lookup
          IF alle(t.status == "widerlegt" for t IN traeger):
            # exklusiv von widerlegten AKs getragen → BESTEHENDER _SC_modelMaintain-
            # WIDERLEGT/GC-Pfad (Sektion "Garbage Collection": ~~WIDERLEGT~~ + Grund).
            # Wiederverwenden, NICHT neu bauen. RETRACTED zaehlt nie im Nenner (INV-SRS-2).
            w → WIDERLEGT via _SC_modelMaintain-GC-Konvention (Grund: Widerlegungs-Signal {ak_id})
            Logge: "[SDF-modelSync] 3.5c falsify-gc: W={w.id} (exklusiver Traeger widerlegt)"
          ELSE:
            Logge: "[SDF-modelSync] 3.5c falsify-shared-erhalten: W={w.id} (Traeger offen/confirmed — kein GC)"
        Logge: "[SDF-modelSync] 3.5c ROUND={batch_key} falsify: {ak_id} → widerlegt (BL-255)"
        CONTINUE

      CASE report.verdict == "VERIFIED":
        # ── Confirm-Transition der AK [BL-255 AK-1] ──
        IF ak.status != "confirmed":                    # Idempotenz: kein Doppel-Provenance-Write
          ak.status       = "confirmed"
          ak.confirmed_by = "abnahme_verdikt"           # Whitelist-SINGLE-SOURCE: _srs_compute.md
                                                        # INV-SRS-6 (abnahme_verdikt|experiment|user_hil)
                                                        # — hier KEINE Kopie der Liste pflegen
          ak.confirmed_at = {ISO-Date}
          ak.verify_ref   = {Pfad zum verify_report}    # Pflicht-Evidenz fuer abnahme_verdikt
          confirm_collapse.collapsed_aks += 1
          Logge: "[SDF-modelSync] 3.5c ROUND={batch_key} confirm: {ak_id} → confirmed (verify_ref={...}) (BL-255)"

        # ── (c) W-Kollaps-Traversal [BL-255 AK-2, der Kern] ──
        # Traversal laeuft auch bei bereits-confirmed AK (heilt fruehere deferred_shared_w,
        # W-seitig idempotent). Filter-Ordnung KRITISCH + deterministisch (NFR-5):
        FOR w IN sort(ak.model_refs):
          # ── (d1) ERSTE Bedingung [BL-255 AK-5, NICHT verhandelbar]: experiment_provable ──
          IF w.status == "experiment_provable":
            # M5-Kategorie kollabiert NIE durch ein Abnahme-Verdikt — nur ein echtes
            # Experiment (SC-Pfad) darf diese W{n} bestaetigen. Der M5-Trigger (KATEGORIE,
            # nicht srs-Hoehe — BL-239 AK-2) bleibt intakt; model_refs_status fuehrt roh (BL-269).
            confirm_collapse.skipped_experiment_provable.append(w.id)
            Logge: "[SDF-modelSync] 3.5c skip-experiment: W={w.id} (experiment_provable, AK-5)"
            CONTINUE

          # ── (d2) ZWEITE Bedingung [BL-255 AK-3]: Shared-W Alle-Traeger-confirmed-Regel ──
          traeger = alle AKs der Spec mit w in model_refs/W{n}-Edge   # deterministischer Lookup
          IF NOT alle(t.status == "confirmed" for t IN traeger):
            # Die Abnahme EINES Teilaspekts bestaetigt NIE eine Wahrheit, auf die andere,
            # noch offene Annahmen bauen. Deferral ist nachvollziehbar, KEIN stilles Skippen.
            # Heilung: sobald der letzte Traeger confirmed wird, kollabiert w in DESSEN Traversal.
            confirm_collapse.deferred_shared_w.append(w.id)
            Logge: "[SDF-modelSync] 3.5c defer-shared: W={w.id} (offene Traeger: {ids}, AK-3)"
            CONTINUE

          # Idempotenz (NFR-1): bereits sichere W{n} (BESTAETIGT-Familie, srs_weight 0.0) → No-Op
          IF w.status IN BESTAETIGT-Familie:
            CONTINUE                                    # kein Doppel-Zaehler-Inkrement

          # ── Transition via _SC_modelMaintain-Konvention [BL-255 AK-2] ──
          # Format der BESTAETIGT-Transition inkl. Provenance (siehe _SC_modelMaintain
          # "Confirm-Provenance an der BESTAETIGT-Transition", BL-255 AK-4) — ausgefuehrt
          # ueber den BESTEHENDEN modelSync-Schreibpfad (W18), KEIN Skill-Spawn, kein Parallel-Pfad:
          w.status       = "AKTIV (BESTAETIGT)"
          w.confirmed_by = "abnahme_verdikt"
          w.confirmed_at = {ISO-Date}
          w.verify_ref   = {Pfad zum verify_report}
          Model-Frontmatter: w-confirmed += 1, w-open -= 1   # NUR bei echter Transition (Idempotenz-Guard)
          confirm_collapse.collapsed_ws += 1
          collapsed_ws_ids.append(w.id)
          # KEIN srs-Write (INV-SRS-5): srs_pro_ak/SRS_batch/SRS_global fallen mechanisch
          # beim naechsten C5-Recompute, weil alle dieselbe Quelle (W-Status) lesen.
          Logge: "[SDF-modelSync] 3.5c collapse: {ak_id} → W={w.id} AKTIV (BESTAETIGT)"

  # ── (e) Dokumenten-Zyklus-Abschluss [BL-255 AK-10]: bestehender 3.5-Schreibpfad (W18) ──
  # AK-Status-Felder → {bl_folder}/3_Spec (oben, Weiche/Confirm)
  # W-Status + Provenance + Frontmatter-Zaehler → {bl_folder}/2_Model (oben, Traversal)
  # Versionierung beider Dateien → SCHRITT 4 (bestehend, unveraendert)
  # confirm_collapse-Block → Manifest SCHRITT 5 (bestehend, additiv erweitert)
  # collapsed_ws_ids → SCHRITT 3.5 Cross-Batch-Iteration (Andock-Zeile dort)
  # KEIN neuer Skill, KEIN Parallel-Pfad — die Kette _I_verify → modelSync 3.5 → recalibrate C5
  # traegt den gesamten Mechanismus (W19, Task-Erfolgskriterium 9).
  Logge: "[SDF-modelSync] 3.5c ROUND={batch_key} DONE — {collapsed_aks} AKs confirmed, {collapsed_ws} W kollabiert, {|deferred_shared_w|} deferred, {|skipped_experiment_provable|} skipped"

SCHRITT 3.5: Cross-Batch-Propagation (BL-238-AK-5, der Consumer des AK-6-Index)
  # Eine in dieser Round promovierte/geaenderte Wahrheit W{n} (z.B. jetzt BESTAETIGT statt OFFEN)
  # strahlt in FREMDE Batches aus: re-rechnet SRS/K-Score der PL-Items die W{n} referenzieren.
  # Index-getrieben (NUR truth_to_batches[W{n}], KEIN Voll-Scan, PT-CMD-015).

  # Pre-Flight (PT-CMD-018): VAULT_ROOT aufloesen + leerer-Index No-Op (kein Teil-Write/Crash).
  VAULT_ROOT = exec("python {WORKING_DIR}/.claude/scripts/resolve_vault_root.py")
  IF VAULT_ROOT leer/ENOENT:
    Logge WARNING: "[SDF-modelSync] AK-5 Pre-Flight: VAULT_ROOT nicht aufloesbar — skip Cross-Batch (No-Op)"
    cross_batch_propagated = []      # No-Op, weiter zu SCHRITT 4
  ELSE:
    cross_batch_propagated = []
    FOR w_id IN promoted_truths + collapsed_ws_ids:     # nur die in DIESER Round geaenderten Wahrheiten
                                     # collapsed_ws_ids: in 3.5c kollabierte W{n} (BL-255 AK-2) —
                                     # "jetzt BESTAETIGT statt OFFEN" strahlt noch in DIESER Round aus
      index_entries = DF_BATCH_STATE.truth_to_batches[w_id]    # index-getrieben, kein Voll-Scan
      IF index_entries leer/EXISTS==false:
        # leerer truth_to_batches[W] (kein fremder Batch / nur eigener) => No-Op (PT-CMD-018, E5)
        Logge: "[SDF-modelSync] AK-5 ROUND={batch_key} W={w_id}: empty truth_to_batches — No-Op"
        CONTINUE

      FOR entry IN index_entries:    # entry = {batch, pl_item, k_score, srs}
        # Idempotenz (INV-MS-SDF-1): 1x pro Round/W{n} pro pl_item — Marker-Check, kein ungedeckelter Loop.
        IF entry.has_marker("cross_batch_synced: {batch_key}/{w_id}"):
          CONTINUE

        # SRS frisch via _srs_compute (BL-205, EINZIGE SRS-Quelle, In-Memory-Return) — KEINE eigene Formel.
        srs_result = Skill(_srs_compute, args="--item={entry.pl_item} --model={bl_folder}/2_Model/{NAME}_Model.md")
        # compute_srs liefert {srs, flag, breakdown}; K-Score-Derivation analog (DT-META-010).

        # Konflikt-Bewusstsein (INV-MS-SDF-7): frischer Wert widerspricht hartem Bestand => WARNING+skip, kein Blind-Overwrite.
        IF srs_result.flag == "conflict":
          Logge WARNING: "[SDF-modelSync] AK-5 CONFLICT — {entry.pl_item} (W={w_id}) skip, manuell aufloesen"
          CONTINUE

        # Slot-Isolation (PT-CMD-008): frischer SRS additiv NUR in definierte DF_BATCH_STATE-Slots,
        # NICHT in fremde BERATER_OUTPUTS, NICHT in metric_per_batch[B-x]-recalibrate-Slots. KEIN Modus-Write (INV-MODUS-1).
        DF_BATCH_STATE.per_pl_evaluation[entry.pl_item].srs = srs_result.srs            # additiv, frisch
        DF_BATCH_STATE.batch_items[entry.batch].srs_refreshed = true                    # additiv, Propagations-Marker
        set_marker(entry, "cross_batch_synced: {batch_key}/{w_id}")                     # INV-MS-SDF-1 idempotent
        cross_batch_propagated.append({w: w_id, pl_item: entry.pl_item, batch: entry.batch, srs: srs_result.srs})
        Logge: "[SDF-modelSync] AK-5 ROUND={batch_key} propagate W={w_id} -> {entry.pl_item}@{entry.batch} srs={srs_result.srs}"

  Logge: "[SDF-modelSync] AK-5 ROUND={batch_key} cross-batch DONE — {|cross_batch_propagated|} PL-Items refreshed"

SCHRITT 4: Versioning + Log
  bump_version(model)   # X.Y → X.(Y+1)
  bump_version(spec)
  set_frontmatter(model, last_synced=now(), synced_from_round=batch_key)
  set_frontmatter(spec,  last_synced=now(), synced_from_round=batch_key)

  log_entry = {
    round: batch_key,
    timestamp: now(),
    promoted_truths: promoted_truths,
    promoted_constraints: promoted_constraints,
    skipped: skipped
  }
  append_to_log({bl_folder}/2_Model/_modelSync_log_{DATE}.md, log_entry)

SCHRITT 5: Manifest-Update
  Write BERATER_OUTPUTS.modelSync_round_{batch_key} = {
    round_id: batch_key,
    promoted_truths_count: |promoted_truths|,
    promoted_constraints_count: |promoted_constraints|,
    new_pl_items_count: |round_new_items|,
    skipped_items_count: |skipped|,
    total_items_evaluated: |round_new_items|,
    promoted_items_ids: promoted_truths,
    log_path: "{bl_folder}/2_Model/_modelSync_log_{DATE}.md",
    exit_code: 0 IF |promoted_truths|+|promoted_constraints|>0 ELSE 1,
    confirm_collapse: confirm_collapse           # BL-255 AK-10 (SCHRITT 3.5c-Ergebnis:
                                                 # collapsed_aks/collapsed_ws/falsified_aks/
                                                 # deferred_shared_w/skipped_experiment_provable/
                                                 # gap_reasons — No-Op-Round => Nullwerte)
  }

  Logge: "[SDF-modelSync] ROUND={batch_key} DONE"
  EXIT exitcode={0|1}
```

## Begruendung Modell-Tier

opus — Truth-Extraction aus PL-Items + Conflict-Detection vs Model + Schreib-
Konsistenz auf Vault-Files. Sonnet uebersieht subtile Konflikte (analog IDF Phase 3.7).

## Verschachtelung

- **Vorgaenger:** Phase 3.3 statusTransition (Items markiert DONE)
- **Nachfolger:** Outer-Loop iteriert weiter → Phase 1.1 naechste Round liest aktualisierten Vault-State
- **Sister:** `_IDF_berater_modelSync` (Phase 3.7 in IDF, einmal pro Story) — `_SDF_berater_modelSync` ist Per-Round-Variante (BL-165 D-Architektur)

## Changelog

- v1.2 (2026-06-10, BL-255 batch_PL2): SCHRITT 3.5c Confirm-Kollaps — Abnahme-Verdikt (_I_verify)
  → AK-Status (confirmed/widerlegt/open+gap_reason → 3_Spec) → W-Propagation "AKTIV (BESTAETIGT)"
  via _SC_modelMaintain-Konvention (Option A + Shared-W-Schutz, BL-255_Spec 1.1). Filter-Ordnung:
  experiment_provable-SKIP (AK-5) VOR Shared-W-Alle-Traeger (AK-3); Falsify-Weiche GAP≠Widerlegung
  (AK-6); confirm_collapse-Manifest-Block (AK-10); Andock collapsed_ws_ids → SCHRITT-3.5-Cross-Batch;
  INV-MS-SDF-10 (deterministisch/idempotent/INV-SRS-5+6-konform).
- v1.1 (2026-06-03, BL-238 AK-5/AK-6): Cross-Batch-Propagation via truth_to_batches-Index
  (SCHRITT 3.5) + Index-Write beim W{n}->PL-Promote (INV-MS-SDF-9).
- v1.0 (2026-05-09, BL-165/BL-166): Initiale Per-Round-Variante (Sister: _IDF_berater_modelSync).

## Source

User-Direktive 2026-05-09: "ich werd ma auch nach jed[em] das model resync, wenn etwas neu rein kommt"
+ Big-Picture-Audit: SDF-Outer-Loop braucht Model-Aktualisierung zwischen Rounds
fuer Continuous-Learning-Pattern (BL-166).
