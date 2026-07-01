---
status: active
version: 1.4  # BL-255 AK-8 metric_per_batch +no_truth_refs_count 2026-06-10 | BL-238 AK-2 metric_per_batch-Contract-Deklaration (NC-8) 2026-06-03 | BL-NEW-7 Early-Exit-Gate 2026-05-11
type: berater
parent: _SDF_orchestrate
model_tier: ceiling
actor: _SDF_PostBerater_orchestrate (C9c) — Schritt 2
sdf_quelle: Z1525-1581
tc: TC5
feature: BL-124
batch_aware: true  # BL-140
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.modus", purpose: "M1-Skip-Check pro Batch"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.current_round_start_ts", purpose: "Round-Start fuer Early-Exit-Gate (BL-NEW-7)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.modusEntscheidung.gewaehlter_modus", purpose: "Sekundaere Pruefung (Fallback)"}
    - {file: "{VAULT}/Backlog/{bl_slug}/2_Model/*.md", path: "mtime", purpose: "model_diff-Check fuer Early-Exit-Gate"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items kategorie", purpose: "Grundsubstanz-Check fuer Early-Exit-Gate"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.recalibrate_batch", purpose: "Aggregat K-Score + SRS nach Batch-Ende"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.sc_srs_last", purpose: "Direkter Metriken-State (OQ-4 Resolution)"}
    # BL-238 AK-2 (GAP2-KRITISCH): metric_per_batch[batch]-Slot additiv deklariert (Body R3 Schritt 2.5 schrieb ihn bereits, Vertrag holt das nach -> kein Gate-7-ALARM). Scope: INV-RECOMPUTE-SCOPE-1 (nur current_batch.batch_items, kein BL-globaler Recompute).
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.metric_per_batch[batch]", purpose: "Pro-Sub-Batch-Aggregat {srs_max, srs_avg, k_score_max, k_score_avg, items_with_data, recompute_ts, no_truth_refs_count (BL-255 AK-8)} — INV-RECOMPUTE-SCOPE-1 scoped (current_batch.batch_items only)"}
---

# _SDF_berater_recalibrate (C5)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_recalibrate (C5)                              ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST: {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                 ║
║           BERATER_OUTPUTS.modusEntscheidung.gewaehlter_modus         ║
║           (per Parameter-Uebergabe vom Orchestrator C9c)            ║
║           A_PIPELINE_STATE (k_score, srs_score, complexity,         ║
║             fragility — NACH Skill-Calls aktualisiert)              ║
║         .claude/specs/{NAME}_Spec.md (Existenzpruefung fuer R2a)    ║
║  SCHREIBT: BERATER_OUTPUTS.recalibrate                               ║
║            {k_score_new, srs_new, model_updated_at}                 ║
║            + _berater_outputs.md Frontmatter: last_update,          ║
║              last_berater="C5"                                       ║
║  SCHREIBT AUCH (OQ-4 Resolution):                                    ║
║    DF_PIPELINE_STATE.sc_srs_last = srs_new (direkter Metriken-State)║
║  SCHREIBT AUCH (BL-238 AK-2, GAP2-KRITISCH, PT-CMD-001):            ║
║    DF_BATCH_STATE.metric_per_batch[batch] = {srs_max, srs_avg,      ║
║      k_score_max, k_score_avg, items_with_data, recompute_ts,       ║
║      no_truth_refs_count (BL-255 AK-8 Flag-Propagation)}            ║
║    Pro-Sub-Batch-Aggregat (R3 Schritt 2.5). Scope:                  ║
║    INV-RECOMPUTE-SCOPE-1 (nur current_batch.batch_items —           ║
║    kein BL-globaler/Cross-Sub-Batch/DONE-Item-Recompute).          ║
║  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                  ║
║                  A_PIPELINE_STATE direkt (schreiben _SC_modelMaintain║
║                  + _K_score selbst)                                  ║
║  ACTOR: _SDF_PostBerater_orchestrate (C9c) — Schritt 2             ║
║  MODELL-TIER: ceiling — TC5, SDF-Quelle Z1525-1581                  ║
║  INVARIANTEN: INV-2 (Write-Isolation), INV-6 (SKIP bei M1 —        ║
║               BL-014 ADR: Overhead unverhaeltnismaessig),           ║
║               NFR-3 (Idempotenz: gleicher Manifest-State → gleicher ║
║               k_score_new nach 10x Aufruf)                          ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_SDF_berater_recalibrate, args="{NAME} --modus {gewaehlter_modus}")

Parameter:
  {NAME}              — Feature-Name
  --modus {modus}     — gewaehlter_modus aus BERATER_OUTPUTS.modusEntscheidung
                        (M1 → sofortiger SKIP, NFR-4 Status=SKIP)

Vorbedingung:
  - _berater_outputs.md.BERATER_OUTPUTS.modusEntscheidung.gewaehlter_modus gesetzt (C3 gelaufen)
  - A_PIPELINE_STATE aus vorherigem Pipeline-Durchlauf vorhanden (oder null-safe)

Ausgabe:
  - BERATER_OUTPUTS.recalibrate (3 Felder)
  - Exitcode: 0=OK, 1=SKIP (M1), 2=FAIL (Spec-Missing bei R2a)

Logging-Format (NFR-4):
  [C5_recalibrate] ENTRY item_id={item_id} modus={modus} cycle_nr={cycle_nr}
  [C5_recalibrate] EXIT duration={ms}ms status={OK|SKIP|FAIL}
```

## Schritte (aus SDF Z1525-1583 extrahiert)

```
SCHRITT 0: Entry-Log + Skip-Guard (INV-6, BL-014 ADR, BL-140)
  [C5_recalibrate] ENTRY modus={modus} cycle_nr={cycle_nr}
  # BL-140: DF_BATCH_STATE.modus ist primaere M1-Quelle (einmal pro Batch gesetzt)
  batch_modus = DF_BATCH_STATE.modus  # liest aus {WORKING_DIR}/_manifest.md
  effective_modus = batch_modus ?? gewaehlter_modus  # Fallback auf Parameter
  IF effective_modus == "M1":
    Logge: "[C5-SKIP] modus=M1 — Recalibrate-Overhead unverhaeltnismaessig (BL-014 ADR)"
    BERATER_OUTPUTS.recalibrate_batch = { k_score_new: null, srs_new: null, model_updated_at: null, skipped: true, skip_reason: "M1_modus" }
    _berater_outputs.md Frontmatter: last_update={jetzt}, last_berater="C5"
    [C5_recalibrate] EXIT status=SKIP
    → RETURN exitcode=1

SCHRITT 0.5: Early-Exit-Gate (NEU 2026-05-11, BL-NEW-7, INV-7)
  # Conditional: Wenn weder Model noch Grundsubstanz-PL in dieser Round
  # geaendert wurden, ist Recalibrate Verschwendung. SKIP mit Exitcode=1.
  # Greift NACH M1-Skip (Schritt 0), gilt fuer M2/M3+ wenn Round substanzfrei.
  #
  # Trigger (ODER):
  #   (a) model_diff:       2_Model/*.md mtime > round_start_ts
  #   (b) pl_grundsubstanz: neue PL-Items mit kategorie ∈ Grundsubstanz
  #
  # Grundsubstanz = strukturelles Lernen, das K-Score+Model betrifft.
  # Open-Questions/TODOs sind KEIN Grund fuer Recalibrate.

  round_start_ts = DF_BATCH_STATE.current_round_start_ts ?? DF_BATCH_STATE.batch_start_ts
  bl_folder      = BERATER_OUTPUTS.teamSetup.bl_folder

  # (a) Model-Diff via mtime
  model_diff = false
  FOR model_file IN glob({bl_folder}/2_Model/*.md):
    IF mtime(model_file) > round_start_ts:
      model_diff = true
      BREAK

  # (b) PL-Grundsubstanz
  GRUNDSUBSTANZ_KATEGORIEN = {"layer", "pattern", "anti-pattern", "konvention", "architektur-decision"}
  pl_grundsubstanz = false
  pl_path = {bl_folder}/6_PL/{bl_id}-parking-lot.md
  IF exists(pl_path):
    pl_items_in_round = parse_pl_items_since(Read(pl_path), round_start_ts)
    FOR item IN pl_items_in_round:
      IF item.kategorie IN GRUNDSUBSTANZ_KATEGORIEN:
        pl_grundsubstanz = true
        BREAK

  IF NOT model_diff AND NOT pl_grundsubstanz:
    Logge: "[C5-EARLY-EXIT] no model_diff && no Grundsubstanz-PL — SKIP recalibrate (BL-NEW-7)"
    BERATER_OUTPUTS.recalibrate_batch = {
      k_score_new: null, srs_new: null, model_updated_at: null,
      skipped: true, skip_reason: "early_exit_no_trigger",
      gate: { model_diff: false, pl_grundsubstanz: false }
    }
    _berater_outputs.md Frontmatter: last_update={jetzt}, last_berater="C5"
    [C5_recalibrate] EXIT status=SKIP_EARLY_EXIT
    → RETURN exitcode=1

  Logge: "[C5-GATE-PASS] model_diff={model_diff} pl_grundsubstanz={pl_grundsubstanz} — proceed"

SCHRITT 0.7: Sub-Batch-Selection (PL-14-03, BL-165 AK-14)
  # Sub-Batch-aware: lese aktuellen Sub-Batch aus DF_BATCH_STATE
  current_batch_id   = DF_BATCH_STATE.current_sub_batch_id ?? "single"
  batch_items_local  = DF_BATCH_STATE.current_sub_batch_items
                    ?? DF_BATCH_STATE.batch_items
  Logge: "[C5] Sub-Batch={current_batch_id} items={|batch_items_local|}"

SCHRITT 0.8: Terminal-Item-Filter (PL-14-02, BL-165 AK-14)
  # terminal-skip: DONE-Items nicht recomputen (INV-RECOMPUTE-SCOPE-1)
  batch_items_active = []
  FOR pl_item IN batch_items_local:
    IF pl_item.status == "DONE":
      Logge: "[C5] terminal-skip item={pl_item.id} status=DONE"
      CONTINUE  # terminal-skip
    batch_items_active.append(pl_item)
  Logge: "[C5] active_items={|batch_items_active|} (skipped_done={|batch_items_local|-|batch_items_active|})"

SCHRITT 1: Phase R1 — SRS-Recompute (PL-13-01, BL-165 AK-13)
  # STRICT-Sequence: R1 muss komplett abgeschlossen sein bevor R2 startet
  Logge: "[C5] R1: SRS-Recompute START fuer {|batch_items_active|} Items"
  FOR pl_item IN batch_items_active:
    W_before = Model.snapshot(pl_item.source_w, pl_item.last_recompute)
    W_after  = Model.current(pl_item.source_w)
    delta    = diff(W_before, W_after)
    pl_item.srs = compute_srs(delta, pl_item.source_aks)
    pl_item.last_recompute = NOW()
  Logge: "[C5] R1: SRS-Recompute DONE — alle {|batch_items_active|} Items aktualisiert"
  # R1 ABGESCHLOSSEN — R2 darf jetzt starten (STRICT-SEQUENCE enforced)

SCHRITT 2: Phase R2 — K-Score-Recompute (PL-13-02, BL-165 AK-13, depends_on R1)
  # MUSS nach R1 laufen (STRICT-SEQUENCE: R1 → R2 → R3, parallelisierung verboten)
  Logge: "[C5] R2: K-Score-Recompute START (depends_on R1 ABGESCHLOSSEN)"
  FOR pl_item IN batch_items_active:
    pl_item.k_score, pl_item.k_components = compute_k_score(
      srs        = pl_item.srs,           # R1-Output
      aks        = pl_item.source_aks,
      complexity = Model.complexity(pl_item.source_w)
    )
    pl_item.derived_from_srs = true
  Logge: "[C5] R2: K-Score-Recompute DONE — alle {|batch_items_active|} Items aktualisiert"
  # R2 ABGESCHLOSSEN — R3 darf jetzt starten

SCHRITT 2.5: Phase R3 — Batch-Aggregat (PL-13-03, BL-165 AK-13, depends_on R1+R2)
  # KEIN BL-globales Aggregat — nur aktueller Sub-Batch (INV-RECOMPUTE-SCOPE-1)
  Logge: "[C5] R3: Batch-Aggregat START (depends_on R1+R2 ABGESCHLOSSEN)"
  DF_BATCH_STATE.metric_per_batch[current_batch_id] = {
    srs_max:         max(pl.srs for pl in batch_items_active),
    srs_avg:         avg(pl.srs for pl in batch_items_active),
    k_score_max:     max(pl.k_score for pl in batch_items_active),
    k_score_avg:     avg(pl.k_score for pl in batch_items_active),
    items_with_data: count(pl for pl in batch_items_active IF pl.srs != null),
    recompute_ts:    NOW(),
    # BL-255 AK-8 (2026-06-10): Flag-Propagation blind != unsicher — zaehlt das BESTEHENDE
    # _srs_compute-Flag (INV-SRS-3: no_truth_refs -> srs=100; inkl. PL-Items ohne AK-Anker, W10).
    # KEINE neue Berechnung (Spec V5) — downstream trennt modusEntscheidung damit
    # "blind" (keine W-Basis -> Wissensaufbau noetig) von "unsicher" (all-OFFEN -> Confirm-Arbeit).
    no_truth_refs_count: count(pl for pl in batch_items_active IF pl.flag == "no_truth_refs")
  }
  Logge: "[C5] R3: Batch-Aggregat DONE batch={current_batch_id}"
  # Persistiere Aggregat im Manifest
  Aktualisiere DF_BATCH_STATE.metric_per_batch in {WORKING_DIR}/_manifest.md

SCHRITT 3: Model maintain (legacy-R1 hook, SDF Z1549-1550)
  Logge: "[C5] legacy-R1: Model maintain nach {modus}-Handschuh-Rueckweg"
  Skill(_SC_modelMaintain, args="{NAME} --out-of-cycle")
  # _SC_modelMaintain schreibt selbst ins Manifest — C5 liest danach

SCHRITT 4a: K-Score Re-Evaluation (legacy-R2, SDF Z1552-1570)
  spec_path = "{VAULT}/Backlog/{bl_slug}/3_Spec/{NAME}_Spec.md"
  IF exists(spec_path):
    Logge: "[C5] R2a: K-Score Re-Evaluation"
    Skill(_K_score, args="{NAME} easy")
    # _K_score schreibt A_PIPELINE_STATE — C5 liest danach
    Lies A_PIPELINE_STATE aus {WORKING_DIR}/_manifest.md
    k_score_new = A_PIPELINE_STATE.k_score ?? null
    Logge: "[C5] R2a: k_score_new={k_score_new}"
  ELSE:
    Logge: "[C5] R2a: SKIP K-Score (keine Spec vorhanden)"
    k_score_new = null

SCHRITT 2b: SRS aus aktualisiertem Model (R2b, SDF Z1573-1578)
  Lies A_PIPELINE_STATE aus {WORKING_DIR}/_manifest.md
  srs_new = A_PIPELINE_STATE.srs_score ?? null
  Logge: "[C5] R2b: srs_new={srs_new}"

SCHRITT 3: State-Update DF_PIPELINE_STATE (R3, SDF Z1581)
  DF_PIPELINE_STATE.sc_srs_last = srs_new
  Aktualisiere Manifest

SCHRITT 4: Output in BERATER_OUTPUTS.recalibrate_batch schreiben (BL-140 Pro-Batch)
  BERATER_OUTPUTS.recalibrate_batch = {
    k_score_new: {k_score_new},
    srs_new: {srs_new},
    model_updated_at: {jetzt},
    skipped: false
  }
  _berater_outputs.md Frontmatter: last_update={jetzt}, last_berater="C5"

SCHRITT 5: Exit-Log
  [C5_recalibrate] EXIT duration={ms}ms status=OK
```

## Output an BERATER_OUTPUTS.recalibrate_batch (BL-140 Pro-Batch)

```yaml
recalibrate_batch:
  k_score_new: 55        # null wenn Spec fehlt oder M1-SKIP
  srs_new: 42            # null bei SKIP
  model_updated_at: "2026-04-18T14:30:00Z"  # null bei SKIP
  skipped: false         # true bei M1-SKIP (BL-014 ADR)
```

## Hinweis: Delegation-Muster

Alle anderen Manifest-Felder (k_score, complexity, fragility etc.) schreiben
`_SC_modelMaintain` + `_K_score` selbst. C5 liest sie NUR danach.
Einziger direkter Manifest-Write von C5: `DF_PIPELINE_STATE.sc_srs_last`.

## INV-RECOMPUTE-SCOPE-1 (PL-14-01, BL-165 AK-14)

```
INV-RECOMPUTE-SCOPE-1: Recompute beruehrt AUSSCHLIESSLICH current_batch.batch_items.
  Verboten: BL-globaler Recompute, Cross-Sub-Batch-Recompute, DONE-Item-Recompute.
  Erlaubt: Sub-Batch-N Recompute, BL-Aggregat-Refresh am batchEnde.
```
