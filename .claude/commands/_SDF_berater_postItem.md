---
status: active
version: 1.1
type: berater
parent: _SDF_orchestrate
model_tier: middle
actor: _SDF_PostBerater_orchestrate (C9c) — Schritt 3
sdf_quelle: Z1653-1716
tc: TC6
feature: BL-124
created: 2026-04-18
batch_aware: true
deprecated_alias: postItem
---

# _SDF_berater_postItem (C6)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_postItem (C6) — BL-140: postBatch-Logik       ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST: {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded) (A_PIPELINE_STATE.gap_percent,                  ║
║           A_PIPELINE_STATE.spec_extension_candidates,                ║
║           DF_PIPELINE_STATE.task_source, aktiver_modus)              ║
║         DF_BATCH_STATE.batch_items[] (alle Items im Batch)           ║
║         DF_BATCH_STATE.modus (Batch-Modus)                           ║
║         {VAULT}/.../6_PL/{bl_id}-parking-lot.md (SPEC-PROMOTE Tags) ║
║  SCHREIBT: BERATER_OUTPUTS.postBatch_aggregate                        ║
║            {gap_percent, spec_extensions[], gap_ready,               ║
║             batch_done_count}                                        ║
║            + _berater_outputs.md Frontmatter: last_update,           ║
║              last_berater="C6"                                        ║
║  SCHREIBT AUCH (OQ-4 Resolution, Regressions-Guard-Domain):          ║
║    {VAULT}/.../6_PL/{bl_id}-parking-lot.md APPEND bei Regression     ║
║  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                   ║
║                  {WORKING_DIR}/_manifest.md direkt (ausser via Skills)             ║
║  ACTOR: _SDF_orchestrate — Phase 3, SCHRITT 3.2 (BL-140)            ║
║  MODELL-TIER: middle — TC6, SDF-Quelle Z1653-1716                   ║
║  INVARIANTEN: INV-2 (Write-Isolation), INV-6 (gap_ready=true →      ║
║               SDF bricht Iterations-Loop sofort ab), W13             ║
║               (testSearch Szenario-Weiche a/b/c/skip), W14           ║
║               (T_orchestrate Regressions-Verify M1-M6 PFLICHT),      ║
║               W15 (stage_orchestrate Commit-Gate GAP=0%),            ║
║               W16 (REGRESSIONS-GUARD post-commit)                    ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_SDF_berater_postItem, args="{NAME}")

Parameter:
  {NAME} — Feature-Name (z.B. "BL-124")

Vorbedingung:
  - recalibrate (C5) abgeschlossen
  - DF_BATCH_STATE.batch_items[] befuellt
  - A_PIPELINE_STATE.gap_percent in Manifest aktuell

Ausgabe:
  - BERATER_OUTPUTS.postBatch_aggregate (4 Felder)
  - Exitcode: 0=OK, 1=ABORTED (hard failure), 2=FAIL

Logging-Format (NFR-4):
  [C6_postBatch] ENTRY batch_count={batch_count} cycle_nr={cycle_nr}
  [C6_postBatch] EXIT duration={ms}ms status={OK|ABORTED|FAIL}
```

## Schritte (BL-140: postBatch-Logik — Batch-Level)

```
SCHRITT 0: Entry-Log
  [C6_postBatch] ENTRY batch_count={DF_BATCH_STATE.batch_items.length} cycle_nr={cycle_nr}
  aktiver_modus = DF_PIPELINE_STATE.aktiver_modus
  batch_items = DF_BATCH_STATE.batch_items[]
  spec_extensions = []
  batch_done_count = 0
  exitcode = 0

SCHRITT A: Aggregat-GAP-Check (Pro Batch — nicht pro Item)
  Skill(_gap, args="{NAME}")
  Lies A_PIPELINE_STATE aus {WORKING_DIR}/_manifest.md
  gap_percent = A_PIPELINE_STATE.gap_percent ?? 100
  # Vault-PL-Items des Batches: wieviele DONE
  FOR item IN batch_items:
    IF item.status == "DONE":
      batch_done_count += 1
  Logge: "[C6] Aggregat-GAP={gap_percent}% | batch_done_count={batch_done_count}/{batch_items.length}"

SCHRITT B: SPEC-PROMOTE-Filter ueber ganzen Batch (RF-11 — BL-140: Batch-Level)
  IF task_source IN ["pl", "backlog"]:
    pl_path = "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"
    # Sammle alle SPEC-PROMOTE Tags fuer alle Items im Batch
    promote_items = []
    FOR item IN batch_items:
      promote_items += filtere "[SPEC-PROMOTE]" aus pl_path WHERE item_id==item.id
    IF A_PIPELINE_STATE.spec_extension_candidates != null:
      merge A_PIPELINE_STATE.spec_extension_candidates in promote_items
  IF promote_items.length > 0:
    Skill(_spec, args="{NAME} --extend --candidates={promote_items}")
    Skill(_gap, args="{NAME}")  # GAP nach Batch-Promotes neu berechnen
    Lies gap_percent aus A_PIPELINE_STATE neu
    spec_extensions = promote_items.ids
    FOR item IN promote_items WHERE source=="PL":
      pl_path: Ersetze "[SPEC-PROMOTE]" mit "[SPEC-PROMOTED:{Datum}]"
  Logge: "[C6] SPEC-PROMOTE Batch: {spec_extensions.length} Items promoviert"

SCHRITT C: gap_ready-Flag (BL-277 FIX — POST-BUILD-Signal, NICHT stale pre-build gap_percent)
  # BL-277 (Live-Beweis BL-242): gap_percent stammt aus _gap (A-Pipeline / 5_Gap-{name}-GAP.md) und misst den
  # WISSENS-Gap (Spec/Model, initial-evaluation VOR dem Bau). Es wird post-build NICHT gegen den gebauten Code
  # re-computed → bleibt permanent stale (BL-242: 92.6% / 8 MISSING trotz 3 Sub-Batches gebaut+gruen, coverage
  # 2/2 je Batch, GOLD, 51/51 Kanarienvogel). Der alte Gate gap_ready=(gap_percent==0) konnte daher NIE
  # auto-DONE ausloesen → jeder BL brauchte Hand-Close (sabotiert die autonome Finish-Gate BL-272).
  #
  # KORREKTUR (AK-S1b): gap_ready haengt am POST-BUILD-Signal, NICHT am pre-build Wissens-Gap. Der Batch hat
  # postItem (C6) erreicht = er wurde gebaut; das autoritative Post-Build-Verify ist der Regressions-Guard
  # (SCHRITT E), der gap_ready bei ABORT auf false setzt. Der pre-build gap_percent bleibt erhalten fuer
  # Report + SPEC-PROMOTE (SCHRITT B), gated das Auto-DONE/Loop-Abbruch (INV-6) aber NICHT mehr.
  gap_ready = true   # Default post-build; SCHRITT E setzt false bei Regressions-ABORT (M1-M6). M7-M9: SC-Loop entscheidet Done-ness separat.
  # AK-S2 Stale-Marker: Provenance des gap_percent explizit kennzeichnen, damit Konsumenten wissen, dass es
  # post-build NICHT autoritativ ist.
  gap_percent_provenance = "initial-evaluation (pre-build A-GAP, Spec/Model-Wissen) — stale_after_build=true; NICHT post-build coverage (BL-277 AK-S2)"
  Logge: "[C6] gap_ready={gap_ready} (POST-BUILD; pre-build Wissens-Gap gap_percent={gap_percent}% gated NICHT mehr — BL-277)"

SCHRITT D: testSearch-Szenario-Weiche (W13 — nur wenn gap_ready==true)
  IF gap_ready == true:
    Skill(_I_testSearch, args="{NAME}")
    # Weiche: a=verify-only / b=nachziehen / c=betroffen / else=skip (W13)
    Logge: "[C6] testSearch Szenario-Weiche ausgefuehrt (W13)"

SCHRITT E: T_orchestrate Regressions-Verify EINMAL pro Batch (W14 — BL-140: nicht pro Item)
  IF aktiver_modus IN ["M1","M2","M3","M4","M5","M6"]:
    Skill(_T_orchestrate, args="{NAME}")
    IF T_orchestrate.exitcode != 0:
      # W14: M1-M6 PFLICHT → FAIL = ABORT
      # Regressions-PL-Item fuer betroffene Items im Batch appenden
      FOR item IN batch_items:
        pl_path: APPEND Regressions-PL-Item fuer {item.id} (W16-Domain)
      Logge: "[C6] REGRESSIONS-GUARD BATCH FAIL → ABORT"
      exitcode = 1  # ABORTED
      gap_ready = false  # INV-6: Loop-Abbruch verhindert
  ELSE:
    Logge: "[C6] T_orchestrate skip (M7-M9, W14)"

SCHRITT F: Output schreiben
  BERATER_OUTPUTS.postBatch_aggregate = {
    gap_percent: {gap_percent},                       # pre-build Wissens-Gap (Report-only, NICHT Auto-DONE-Gate; BL-277)
    gap_percent_provenance: {gap_percent_provenance}, # AK-S2 Stale-Marker (initial-evaluation, stale_after_build)
    spec_extensions: {spec_extensions},
    gap_ready: {gap_ready},                            # POST-BUILD (gebaut + Regression-grün), BL-277 AK-S1b
    batch_done_count: {batch_done_count}
  }
  _berater_outputs.md Frontmatter: last_update={jetzt}, last_berater="C6"

SCHRITT G: Exit-Log
  [C6_postBatch] EXIT duration={ms}ms status={OK wenn exitcode==0 else ABORTED}
```

## Output an BERATER_OUTPUTS.postBatch_aggregate

```yaml
postBatch_aggregate:
  gap_percent: 0          # 0..100, nach Batch-Spec-Erweiterung aktuell
  spec_extensions: []     # IDs aller promovierter Items im Batch (leer wenn keine)
  gap_ready: true         # true wenn gap_percent==0 UND kein ABORT
  batch_done_count: 3     # Anzahl DONE-Items im Batch (fuer Aggregat-Status)
```

## Hinweis: INV-6 Alpha-Beta-Pruning

`gap_ready=true` ist Signal an SDF Phase 3: C7 statusTransition wird aufgerufen.
`gap_ready=false` (z.B. nach Regressions-GUARD FAIL) haelt Loop aktiv — C7 wird NICHT aufgerufen.
C6 setzt das Flag deterministisch — kein LLM-Aufruf fuer diese Entscheidung.
