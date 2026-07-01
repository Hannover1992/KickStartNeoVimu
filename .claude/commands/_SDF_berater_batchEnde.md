---
status: active
version: 1.1.0  # BL-NEW-10 Wave 3 parallel PT/SL 2026-05-11
created: 2026-04-26
updated: 2026-05-11
op: SmallDarkFactory
phase: 3
type: berater
chain_position: middle
model_tier: floor
parent: _SDF_orchestrate
actor: _SDF_orchestrate — Phase 3, Schritt 3.4 (Batch-Abschluss)
sdf_quelle: Z704-759
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.sdf_post_gap_checklist", purpose: "Vollstaendigkeitspruefung vor BDF_NEXT_TRIGGER"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BDF_PIPELINE_STATE.bdf_status", purpose: "Guard fuer BDF-Signal-Schreiben"}
    - {file: "_session_params.md", path: "enforceProcess", purpose: "Warn-Modus vs Enforce-Modus (AK-03-03)"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.current_worker", purpose: "null"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.last_completed", purpose: "BATCH_DONE"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BDF_PIPELINE_STATE.BDF_BATCH_DONE", purpose: "true (Signal an BDF)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BDF_PIPELINE_STATE.BDF_NEXT_TRIGGER", purpose: "true (Signal an BDF)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.batchEnde", purpose: "next_action + bdf_handover"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "AUDIT_JSONL", purpose: "GUARD_BLOCK Event bei Checklist-Fehler"}
  writes_not:
    - sdf_post_gap_checklist direkt (schreibt Phase FINAL / andere Berater)
    - BDF_PIPELINE_STATE bei enforceProcess=true (ABBRUCH statt Signal)
---

# /_SDF_berater_batchEnde (Phase 3 — Batch-Ende + Ruecksprung zu BDF)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_batchEnde (Phase 3, Schritt 3.4)              ║
╠══════════════════════════════════════════════════════════════════════╣
║  REFERENZEN: RF-SDF-007, RF-BDF-020, BL-035, BL-133 Slice-3         ║
║  LIEST: DF_PIPELINE_STATE.sdf_post_gap_checklist (6 Felder)          ║
║         BDF_PIPELINE_STATE.bdf_status                                ║
║         _session_params.md: enforceProcess                           ║
║  SCHREIBT: DF_PIPELINE_STATE.{current_worker=null, last_completed}   ║
║            BDF_PIPELINE_STATE.{BDF_BATCH_DONE=true, BDF_NEXT_TRIGGER=true} ║
║            BERATER_OUTPUTS.batchEnde.{next_action, bdf_handover?}    ║
║            AUDIT_JSONL: GUARD_BLOCK Event (bei Checklist-Fehler)     ║
║  ACTOR: _SDF_orchestrate Phase 3 Schritt 3.4                        ║
║  MODELL-TIER: sonnet                                                  ║
║  INVARIANTEN:                                                         ║
║    INV-1: TRANSITIONS-GUARD MUSS vor BDF_NEXT_TRIGGER laufen (INV-02)║
║    INV-2: enforceProcess=true → ABBRUCH wenn Checklist unvollstaendig║
║    INV-3: enforceProcess=false → Warnung, Pipeline laeuft weiter     ║
║    INV-4: BDF_BATCH_DONE=true NUR wenn BDF_PIPELINE_STATE.bdf_status ║
║           == "ITEM_RUNNING" (Guard gegen Doppelung)                   ║
║    INV-5: SDF endet nach dieser Phase (BL-133 Slice-3)               ║
╚══════════════════════════════════════════════════════════════════════╝
```

## INPUT / OUTPUT

```
INPUT:
  NAME        - Feature-Name (aus SDF-Kontext)
  batch_total - Anzahl Items im Batch (aus DF_BATCH_STATE)

OUTPUT (BERATER_OUTPUTS.batchEnde):
  next_action:  "BDF_HANDOVER" | "ABORTED"   # Ergebnis
  bdf_handover: true | false                  # BDF-Signal gesetzt?
  guard_status: "OK" | "WARN" | "BLOCK"       # Checklist-Guard Ergebnis
  missing_fields: [{feld}]                    # NUR bei WARN/BLOCK
```

## Pseudocode

```
# Phase 3: Batch-Ende — stage_orchestrate wurde BEREITS aufgerufen (BL-299 AK-5: pfad-abhaengiger Owner):
#   MOTOR-Pfad (dispatch_implement.js): der Motor chaint Skill(_stage_orchestrate) am ELEVATE-Seam
#     (jede gruene Test-Stage, Grain=Stage) UND am BATCH_DONE-Seam (letzte Stage, nach runPhase3) — BL-299.
#   SKILL-Pfad (_SDF_orchestrate_post): SCHRITT 3.3.5 ruft Skill(_stage_orchestrate) als Round-Commit.
# (Die fruehere 'pro Item in Phase 2'-Formulierung war verwaist — der BL-222-Motor ersetzte die per-Item-
#  Inner-Loop, trug den Commit-Tail aber zunaechst NICHT mit; BL-299 hat ihn als Stage-Grain wiederhergestellt.)
# RF-SDF-007: Der gruene Stage-Stand wurde gestaged + gate-gepruefte committet (Security-Gate Pruefung 1-6).
# RF-BDF-020: BDF uebernimmt nach Batch-Ende: prueft PL → naechster Batch ODER Post-Phase.
# SDF-Lifecycle endet nach dieser Phase (BL-133 Slice-3).

# ─── Schritt 3.5: PL-Items frontmatter aktualisieren (C7 OWNS [x]-Write) ────
# AK-4 BL-428: C7 (_SDF_berater_statusTransition) OWNS die [x]-Markierung.
# batchEnde aktualisiert NUR frontmatter (kein Replace_in_file mehr — Doppel-Write/Format-Konflikt eliminiert).
batch_items = Read(_manifest.md).DF_BATCH_STATE.batch_items
ts_paths    = Read(_manifest.md).BERATER_OUTPUTS.teamSetup
pl_path     = ts_paths.bl_folder + "/6_PL/" + ts_paths.bl_id + "-parking-lot.md"

Update(pl_path).frontmatter.last_updated = DATE
Update(pl_path).frontmatter.items_done_count += len(batch_items)
Logge: "[batchEnde 3.5] PL-Frontmatter aktualisiert ({len(batch_items)} Items, C7 OWNS [x]-Writes)"

DF_PIPELINE_STATE.current_worker = null
DF_PIPELINE_STATE.last_completed = "BATCH_DONE"
df_state_transition(DONE, 3, null, "Batch {batch_total} Items erledigt + staged + PL-marked")

# ═══ TRANSITIONS-GUARD: Checklist-Vollstaendigkeitspruefung (BL-035, AK-03-01, INV-02) ═══
# VOR BDF_NEXT_TRIGGER=true: ALLE 6 Felder von sdf_post_gap_checklist MUESSEN DONE sein.
# Guard liest NUR Manifest-Felder (positives Enforcement, ADR-02 — kein Keyword-Matching).
# enforceProcess bestimmt Warn-Modus vs Enforce-Modus (AK-03-03, ADR-03).

Lies enforceProcess aus _session_params.md
checklist = DF_PIPELINE_STATE.sdf_post_gap_checklist
fehlende_felder = []
FUER feld IN [bl_done, checks5, testSearch, stage, regressionGuard, final]:
  IF checklist.{feld} != DONE:
    fehlende_felder.append(feld)

IF fehlende_felder.length > 0:
  Logge WARNUNG: "[TRANSITIONS-GUARD] Checklist NICHT komplett! Fehlende Felder: {fehlende_felder}"
  # Audit-Log: GUARD_BLOCK Event (AK-06-02)
  audit_jsonl_append({
    type: "GUARD_BLOCK",
    reason: "Checklist nicht komplett",
    missing_fields: fehlende_felder,
    checklist_snapshot: checklist,
    item_id: "{item_id}",
    timestamp: "{ISO}"
  })

  IF enforceProcess == true:
    # Enforce-Modus: BDF_NEXT_TRIGGER blockiert (AK-03-03: Exit-Code 2)
    Logge FEHLER: "[TRANSITIONS-GUARD] BLOCK: enforceProcess=true — BDF_NEXT_TRIGGER bleibt false."
    Logge FEHLER: "[TRANSITIONS-GUARD] Fehlende Schritte: {fehlende_felder}. Pipeline-Abbruch."
    IF BDF_PIPELINE_STATE.bdf_status == "ITEM_RUNNING":
      Schreibe {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
        BDF_BATCH_DONE: false
        BDF_NEXT_TRIGGER: false
    Schreibe {WORKING_DIR}/_manifest.md → BERATER_OUTPUTS.batchEnde:
      next_action:    "ABORTED"
      bdf_handover:   false
      guard_status:   "BLOCK"
      missing_fields: fehlende_felder
    → ABBRUCH  # Guard blockiert — fehlende Post-GAP-Schritte muessen nachgeholt werden
  ELSE:
    # Warn-Modus: Warnung loggen, Pipeline laeuft weiter (AK-03-03: continue:true)
    Logge WARNUNG: "[TRANSITIONS-GUARD] WARN: enforceProcess=false — Warnung geloggt, weiter."
    Logge WARNUNG: "[TRANSITIONS-GUARD] ACHTUNG: {fehlende_felder.length} Pflichtschritte fehlen!"
    guard_status = "WARN"
ELSE:
  guard_status = "OK"

# ═══ Ende TRANSITIONS-GUARD ═══

# BDF-Signal: DONE (alle Items staged, bereit fuer naechsten Batch).
# BL-133 Slice-3: BDF_NEXT_TRIGGER=true direkt nach Phase 3 (SDF endet hier).
IF BDF_PIPELINE_STATE.bdf_status == "ITEM_RUNNING":
  Schreibe {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
    BDF_BATCH_DONE: true    # Signal: Batch vollstaendig + alle Items einzeln staged
    BDF_NEXT_TRIGGER: true  # BDF: weiter (naechster Batch ODER Post-Flow via Berater)
  bdf_handover = true
ELSE:
  bdf_handover = false

Logge: "[POST-GAP] Checklist KOMPLETT: 6/6 DONE — BDF_BATCH_DONE freigegeben."
Logge: "Phase 3 DONE. Batch {batch_total} Items erledigt + je einzeln gestaged. BDF uebernimmt."

# ─── NEU 2026-05-04 (BL-151) Schritt 3.6: AUTO-CONTINUATION (MODE-AWARE) ─
# GAP-Fix: ohne diesen Block bleibt Pipeline am Batch-Ende stehen.
# WICHTIG (User-Korrektur 2026-05-04): Routing ist MODE-DEPENDENT:
#
#   GLOBAL_MODUS == "small_dark_factory":
#     BDF ist OUT-OF-SCOPE. Loop ist SDF↔IDF↔PL.
#     1. PL-Drift-Check: neue Items im parking-lot.md (vom User mid-batch dazu)?
#     2. IF neue Items → Skill(_IDF_orchestrate --pl-only) (re-plan mit neuem Stand)
#     3. ELSE remaining batches > 0 → Skill(_SDF_orchestrate) (naechster geplanter Batch)
#     4. ELSE alle Batches DONE → Skill(_finish) (Post-Phase)
#
#   GLOBAL_MODUS == "big_dark_factory":
#     BDF ist primaerer Orchestrator → Skill(_BDF_orchestrate)
#
# INV-PM-2: Orchestrator-Wechsel via Skill(), NIEMALS Agent().
# INV-BE-9: Recheck/dryRun skipt Auto-Continuation (Anti-Zirkel).
session = Read("_session_params.md")
global_modus = session.GLOBAL_MODUS ?? "small_dark_factory"   # Default: SDF
bdf_mode_local = Read({WORKING_DIR}/_manifest.md).BDF_PIPELINE_STATE.bdf_mode
recheck = (bdf_mode_local IN ["recheck", "dryRun"])

items_done_count = len(Read({WORKING_DIR}/_manifest.md).DF_PIPELINE_STATE.batch_done)
items_total = Read({WORKING_DIR}/_manifest.md).BL_LIFECYCLE_STATE.items_routed_ready
Logge: "[batchEnde 3.6] Pipeline-State: {items_done_count}/{items_total} items done"
Logge: "[batchEnde 3.6] GLOBAL_MODUS={global_modus}"

IF recheck:
  Logge: "[batchEnde 3.6] Recheck-Modus, kein Auto-Continuation (Anti-Zirkel)"
  GOTO PT_FEEDBACK
IF bdf_handover == false:
  Logge: "[batchEnde 3.6] bdf_handover=false (Checklist WARN/BLOCK) — manueller Eingriff"
  GOTO PT_FEEDBACK

# ─── small_dark_factory: SDF↔IDF Loop (BDF out-of-scope) ─────────────────
IF global_modus == "small_dark_factory":
  # 1) PL-Drift-Check: User hat evtl. neue Items mid-batch dazu geadded
  pl_path = Read({WORKING_DIR}/_manifest.md).BERATER_OUTPUTS.teamSetup.bl_folder + "/6_PL/" + bl_id + "-parking-lot.md"
  pl = Read(pl_path)
  current_open_items = pl.count("- [ ] **")
  last_idf_open_count = Read({WORKING_DIR}/_manifest.md).IDF_PIPELINE_STATE.last_pl_open_count ?? 0
  pl_drift = current_open_items > (last_idf_open_count - len(batch_items))

  IF pl_drift:
    Logge: "[batchEnde 3.6] PL-DRIFT erkannt ({current_open_items} offen, erwartet {last_idf_open_count - len(batch_items)})"
    Logge: "[batchEnde 3.6] User hat neue PL-Items mid-batch dazu geadded → IDF re-plan"
    Skill(_IDF_orchestrate, args=BL_ID + " --pl-only --from=sdf_finish")
    # IDF aggregiert neu, plant Batches neu, ruft danach automatisch SDF
  ELSE:
    # 2) Naechster Batch aus IDF batchPlan
    remaining_batches = Read({WORKING_DIR}/_manifest.md).IDF_PIPELINE_STATE.batches_remaining ?? 0
    IF remaining_batches > 0:
      Logge: "[batchEnde 3.6] {remaining_batches} Batches verbleibend → SDF naechster Batch"
      Skill(_SDF_orchestrate, args=BL_ID)
    ELSE:
      # 3) Alle Batches DONE → Post-Phase
      Logge: "[batchEnde 3.6] Alle Batches DONE — Post-Phase (finalize)"
      Skill(_finish, args=BL_ID)

# ─── big_dark_factory: BDF Loop ──────────────────────────────────────────
ELIF global_modus == "big_dark_factory":
  Logge: "[batchEnde 3.6] HANDSCHUH-WECHSEL: SDF → BDF (big_dark_factory mode)"
  Skill(_BDF_orchestrate, args=BL_ID)

ELSE:
  Logge: "[batchEnde 3.6] WARN: unbekannter GLOBAL_MODUS={global_modus} — manueller Eingriff"

LABEL: PT_FEEDBACK

# PL-Feedback Learning Loop (ARCH-21, BL-153) — INV-EINSCHUB, NON-BLOCKING
# Zweck: Nach jedem Batch-DONE PatternConformance-PL-Items konsumieren und Confidence updaten.
# NON-BLOCKING: Kein PT_update Befehl = SKIP. Fehler in _PT_update brechen batchEnde NICHT ab.
IF Skill("_PT_update") verfuegbar:
  Logge: "[PT-Feedback] Starte _PT_update --from-pl-feedback (NON-BLOCKING)"
  Skill(_PT_update, args="--from-pl-feedback")
  Logge: "[PT-Feedback] DONE (oder NON-BLOCKING-Skip)"
ELSE:
  Logge: "[PT-Feedback] _PT_update nicht verfuegbar — SKIP (NON-BLOCKING, ADR-PL-008)"

LABEL: LIBRARY_PROMOTION

# ─── WAVE 3 (NEU 2026-05-11, BL-NEW-10): PARALLEL Library-Promotion ─────────
# PL → Library Promotion (BL-XXX, 2026-05-06) — INV-EINSCHUB, NON-BLOCKING.
# Zweck: Stabile PL-Items aus diesem Batch in die globalen Vault-Libraries promovieren.
#
# DISJUNKTE Vault-Ziele:
#   _PT_promoteFromPL  schreibt nach {VAULT}/Libraries/PatternLibrary/
#   _SL_promoteFromPL  schreibt nach {VAULT}/Libraries/SemanticLibrary/
# → keine Write-Konflikte, voneinander unabhaengig → PARALLEL ausfuehrbar.
#
# Lead-Side Pattern: Beide Skill-Calls in EINEM Tool-Call-Block (parallele Tool-Uses).
# Worker-Side: Falls dieser Berater von Worker ausgefuehrt wird, spawnt der Worker
#              ZWEI Sub-Agents parallel (eine Agent-Tool-Call mit 2 Inhaltsbloecken).
#
# NON-BLOCKING: Fehler in einem Schritt brechen batchEnde NICHT ab — Pipeline laeuft weiter.

# ── FORK Wave 3 ──
Logge: "[Wave-3 FORK] PT + SL parallel promotion starting"
audit_jsonl_append({type: "WAVE_FORK", wave: 3, parallel_skills: ["_PT_promoteFromPL", "_SL_promoteFromPL"], batch_id: BL_ID, timestamp: ISO})

# Spawn beide PARALLEL (single dispatch round, kein sequentielles Warten):
PARALLEL_DISPATCH:
  TRACK_A:
    IF Skill("_PT_promoteFromPL") verfuegbar:
      Logge: "[Wave-3 Track-A] _PT_promoteFromPL (parallel)"
      Skill(_PT_promoteFromPL, args=BL_ID)
      Logge: "[Wave-3 Track-A] PT promoted"
    ELSE:
      Logge: "[Wave-3 Track-A] _PT_promoteFromPL nicht verfuegbar — SKIP"

  TRACK_B:
    IF Skill("_SL_promoteFromPL") verfuegbar:
      Logge: "[Wave-3 Track-B] _SL_promoteFromPL (parallel)"
      Skill(_SL_promoteFromPL, args=BL_ID)
      Logge: "[Wave-3 Track-B] SL promoted"
    ELSE:
      Logge: "[Wave-3 Track-B] _SL_promoteFromPL nicht verfuegbar — SKIP"

# ── JOIN Wave 3 ──
Logge: "[Wave-3 JOIN] PT + SL parallel promotion done"
audit_jsonl_append({type: "WAVE_JOIN", wave: 3, batch_id: BL_ID, timestamp: ISO})

# Output schreiben
Schreibe {WORKING_DIR}/_manifest.md → BERATER_OUTPUTS.batchEnde:
  next_action:    "BDF_HANDOVER"
  bdf_handover:   bdf_handover
  guard_status:   guard_status
  missing_fields: []
```

## INVARIANTEN

```
INV-1: TRANSITIONS-GUARD laeuft IMMER vor BDF_NEXT_TRIGGER=true (INV-02, BL-035).
INV-2: enforceProcess=true + fehlende_felder → ABBRUCH. Kein BDF_NEXT_TRIGGER=true.
INV-3: enforceProcess=false + fehlende_felder → WARN, Pipeline laeuft weiter.
INV-4: BDF_BATCH_DONE/BDF_NEXT_TRIGGER NUR schreiben wenn bdf_status=="ITEM_RUNNING".
INV-5: SDF endet nach Phase 3. Phasen 4-7 (Quality/Delivery/Finish) sind Berater/Skills (BL-133 Slice-3).
INV-6: df_state_transition(DONE) VOR dem Guard — Guard blockiert nur BDF-Signal, nicht State.
```
