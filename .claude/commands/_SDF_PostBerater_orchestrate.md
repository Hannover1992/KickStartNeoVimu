---
status: active
version: 1.0
type: orchestrator
sub_type: post_berater
model_tier: middle
feature: BL-124
handschuh_nr: 3
created: 2026-04-18
scope_ext: "C12 garbageCollection + C13 stateMaintain (2026-04-18)"
---

# _SDF_PostBerater_orchestrate (C9c)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_PostBerater_orchestrate (C9c)                         ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST: _manifest.md (I_PIPELINE_STATE: needs_tdd,                   ║
║           handschuh_wechsel_pending, last_stage_completed,           ║
║           phase, GAP-Daten, PL/BL-Status)                            ║
║         _berater_outputs.md (modusEntscheidung.gewaehlter_modus,     ║
║           sdfHub.tdd_signal_pending, postItem.gap_ready              ║
║           als Schalt-Bedingungen)                                    ║
║  SCHREIBT: _berater_outputs.md Frontmatter (last_update)             ║
║            I_PIPELINE_STATE.needs_tdd (NUR nach POST_TDD-Bestaetigt)║
║            I_PIPELINE_STATE.handschuh_wechsel_pending (nach TDD OK) ║
║            WP_PIPELINE_STATE Block (M9-Kontext, OQ-4)               ║
║            → delegiert Berater-Writes an C12/C13/C4/C5/C6/C7        ║
║            → inline Guards: REGRESSIONS-GUARD W16, Commit-Gate W15  ║
║  SCHREIBT NICHT: BERATER_OUTPUTS-Sub-Felder direkt                   ║
║                  I_PIPELINE_STATE AUSSER needs_tdd/hw_pending        ║
║                  (R1-Guard Ausnahme — INV-2 via Orchestrator-Recht)  ║
║  ACTOR: Team Lead (Skill-Load) — Handschuh #3 von 3 (INV-5)         ║
║  SEQUENZ: Phase 1 GarbageCollection (C12, NEU) →                     ║
║           Phase 2 StateMaintain (C13, NEU) →                         ║
║           Phase 3 sdfHub (C4, nur M2/M3/M5/M6) →                    ║
║             [R1-Guard: TDD-Clear nach POST_TDD-Bestaetigung] →       ║
║           Phase 4 recalibrate (C5, skip M1) →                        ║
║           Phase 5 postItem-Loop (max 5) →                            ║
║           Phase 6 W20-Mitigation (TDD-Signal-Clear) →                ║
║           Phase 7 stage_orchestrate (wenn gap_ready + !blocked) →    ║
║           Phase 8 statusTransition (C7) →                            ║
║           Phase 9 T_orchestrate (Ausbaustufe 2, optional)            ║
║  INVARIANTEN: INV-1/INV-FACTORY-1 (SHOW MUST GO ON, explizit hier), ║
║               INV-3 (Contract-Struktur stabil),                      ║
║               INV-4 (Signal-Felder I_PIPELINE_STATE via I schreib., ║
║                 Ausnahme: needs_tdd-Clear durch C9c per OQ-3/OQ-5), ║
║               INV-5 (genau 3 Handschuh-Wechsel: dieser ist #3),     ║
║               INV-6 (gap_ready=true → Loop sofort abbrechen),        ║
║               W13-W16 (PostItem-Guards + Regressions-Verify)         ║
╚══════════════════════════════════════════════════════════════════════╝
```

## INVARIANTEN — SHOW MUST GO ON

```
INV-FACTORY-1 (INV-1): GLOBAL_HIL=off → VOLLAUTOMATISCH
  # PFLASTER 2026-06-11 (BL-295 AK-5): HiL-Quelle ist AUSSCHLIESSLICH der hil-Param/GLOBAL_HIL,
  # NICHT GLOBAL_MODUS (PL-S2-06: BDF/Modus und HiL sind ORTHOGONAL). Vollautomatik haengt nur
  # an hil=off — unabhaengig vom Modus. Frueher: "GLOBAL_MODUS=dark_factory + GLOBAL_HIL=off" —
  # der Modus-Konjunkt war HiL-Proxy-Kopplung (entfernt).
  ENDE-BEDINGUNGEN (einzig erlaubte Stops):
    PL-EMPTY | SDF-MAX-ITERATIONS | ABORT (harter Pipeline-Failure)

VERBOTEN (auch bei Context-Druck):
  - Fresh-Session-Empfehlung durch Team Lead
  - Mid-Run-Pause / "Soll ich fortfahren?" / "Darf ich weitermachen?"
  - AskUserQuestion ohne harten Pipeline-Failure (ABORT-Pfad)
  - Context-Budget als Abbruch-Grund

HARD_FAILURE → Fail-Loud (ABORT + BDF-Signal ABORTED):
  - postItem-Loop: max 5 Iterationen ohne gap_ready
  - REGRESSIONS-GUARD FAIL post-commit (W16)
  - T_orchestrate FAIL Regressions-Verify M1-M6 (W14)

SOFT_DEGRADATION → Fail-Safe (CONTINUE + Warnung-Log):
  - recalibrate SKIP bei M1 (BL-014 ADR)
  - statusTransition SKIP wenn item_type=null (INV-6)
  - TDD-Return ohne POST_TDD: Signal retained, naechste Hub-Iteration (kein Stop)
  - C12/C13 SKIP wenn kein Bloat erkannt (gc.status="SKIP")

K5-FIX (in C1 implementiert — hier als Enforcement-Reminder):
  Kein AskUserQuestion wegen GLOBAL_HIL=off + IDLE.
  Context-Erschoepfung → RF-09 Resume-Guard nach Wiederaufnahme (C1).

W20-INVARIANTE (INV-2-Ausnahme fuer C9c):
  C9c DARF I_PIPELINE_STATE.needs_tdd schreiben (Orchestrator-Recht, OQ-3/OQ-5).
  C4 (Berater) darf das NICHT (INV-2 Write-Isolation).
  needs_tdd-Clear geschieht NACH bestaetigtem POST_TDD (Phase 3 R1-Guard).
  Vor TDD-Call: needs_tdd bleibt true (Kern-Unterschied zu SDF v0.8.0 Z1294-1296).
```

## Aufruf-Interface

```
Skill(_SDF_PostBerater_orchestrate, args="{NAME}")

Parameter:
  {NAME} — Feature-Name (z.B. "BL-124")

Vorbedingung:
  - C9b (_SDF_PreBerater_orchestrate) abgeschlossen (Exitcode 0)
  - BERATER_OUTPUTS.modusEntscheidung gesetzt (C3 via C9b DONE)
  - Main-Skill abgeschlossen (I_orchestrate / SC_orchestrate)

Ausgabe:
  - Item-Status aktualisiert (via C6/C7-Delegation)
  - Exitcodes: 0=OK, 2=FAIL

Logging-Format (NFR-4):
  [C9c_PostBerater] ENTRY item_id={item_id} cycle_nr={cycle_nr} modus={modus}
  [C9c_PostBerater] EXIT duration={ms}ms status={OK|FAIL} item_id={item_id}
```

## Sequenz Pseudo-Code

```
[C9c_PostBerater] ENTRY item_id={item_id} cycle_nr={cycle_nr} modus={modus}

modus = BERATER_OUTPUTS.modusEntscheidung.gewaehlter_modus

# ═══ PHASE 1: GarbageCollection (C12, NEU — Scope-Ext 2026-04-18) ═══
# Trigger: automatisch nach JEDEM Orchestrator-Return (immer, kein Opt-In)
# Begruendung: _manifest.md 380→110 LOC manuell 2026-04-18 — State-Log-Degradation verhindert
PHASE 1: GarbageCollection
  Skill(_SDF_berater_garbageCollection, args="{NAME}")
  gc = BERATER_OUTPUTS.garbageCollection

  IF gc.status == "CLEANED":
    Logge: "[C9c_PostBerater] PHASE 1 GC: {gc.items_removed} State-Log-Eintraege bereinigt."
  ELSE:
    # SOFT_DEGRADATION: Kein Bloat erkannt — SKIP ist OK, kein Fail
    Logge: "[C9c_PostBerater] PHASE 1 GC: Kein Bloat erkannt (SKIP=clean)."

# ═══ PHASE 2: StateMaintain (C13, NEU — Scope-Ext 2026-04-18) ═══
# Integrity-Check + Auto-Korrektur obsoleter Felder (laeuft immer nach GC)
PHASE 2: StateMaintain
  Skill(_SDF_berater_stateMaintain, args="{NAME}")
  sm = BERATER_OUTPUTS.stateMaintain

  IF sm.integrity == "FAIL":
    # SOFT_DEGRADATION: Auto-korrigiert, kein Stop
    Logge WARNUNG: "[C9c_PostBerater] PHASE 2 StateMaintain WARN: {sm.corrections}. Auto-korrigiert."
  ELSE:
    Logge: "[C9c_PostBerater] PHASE 2 StateMaintain: integrity=OK."

# ═══ PHASE 3: sdfHub (C4) — BL-140 DELETED ═══
# C4 (_SDF_berater_sdfHub) ist redundant. Hub-Loop vollstaendig in executionDispatch SCHRITT 2.
# NICHT MEHR AUFRUFEN. Dieser Block bleibt als Audit-Artefakt.
# W10: 3 Signal-Felder aus I_PIPELINE_STATE (readonly fuer C4)
# R1-Guard (W20-Mitigation Option B): needs_tdd-Clear NACH POST_TDD-Bestaetigung durch C9c
PHASE 3: SDF-Hub Loop
  IF modus IN ["M2", "M3", "M5", "M6"]:
    # BL-140: Skill(_SDF_berater_sdfHub) DEAKTIVIERT — C4 DELETED.
    Skill(_SDF_berater_sdfHub, args="{NAME}")  # TODO BL-140: Durch executionDispatch Hub-Loop ersetzen
    hub = BERATER_OUTPUTS.sdfHub

    # R1-Guard: TDD-Signal von C4 → C9c dispatch (INV-2: C4 schreibt Signal, C9c clear)
    IF hub.tdd_signal_pending != null:
      Logge: "[C9c_PostBerater] PHASE 3 R1-GUARD: tdd_signal_pending erkannt. TDD-Skill aufrufen."

      # needs_tdd bleibt TRUE bis POST_TDD bestaetigt (W20-Invariante oben)
      Skill(_TDD_orchestrate, args="{NAME}")
      manifest.reload()

      IF manifest.I_PIPELINE_STATE.phase == "POST_TDD":
        # NUR nach bestaetigtem TDD-Erfolg clearen (INV-4 Ausnahme: C9c = Orchestrator)
        manifest.I_PIPELINE_STATE.needs_tdd = false
        manifest.I_PIPELINE_STATE.handschuh_wechsel_pending = false
        manifest.update()
        Logge: "[C9c_PostBerater] PHASE 3 R1-GUARD: POST_TDD bestaetigt. needs_tdd=false, hw_pending=false."
      ELSE:
        # TDD gecrasht — Signal BEHALTEN fuer Retry (INV-FACTORY-1: kein Stop)
        Logge WARNUNG: "[C9c_PostBerater] PHASE 3 R1-GUARD WARN: TDD ohne POST_TDD. Signal retained. SOFT_DEGRADATION."

    # stage_progression_pending: Vorbereitung, Verarbeitung in Phase 7
    IF hub.stage_progression_pending != null:
      Logge: "[C9c_PostBerater] PHASE 3 Hub stage_progression pending: naechste={hub.stage_progression_pending.naechste_stufe}"

    Logge: "[C9c_PostBerater] PHASE 3 sdfHub DONE — iter={hub.iterations}, tdd_routed={hub.tdd_routed}, stage_prog={hub.stage_progressions}"

  ELSE:
    # M1/M4/M7/M8/M9: kein Hub-Loop noetig
    Logge: "[C9c_PostBerater] PHASE 3 sdfHub SKIP — Modus={modus} braucht keinen Hub-Loop."

# ═══ PHASE 4: recalibrate (C5) — skip bei M1 ═══
PHASE 4: Recalibrate
  IF modus != "M1":
    Skill(_SDF_berater_recalibrate, args="{NAME}")
    recal = BERATER_OUTPUTS.recalibrate
    Logge: "[C9c_PostBerater] PHASE 4 recalibrate DONE — k_score_new={recal.k_score_new}, srs_new={recal.srs_new}"
  ELSE:
    # SOFT_DEGRADATION: M1 = kein Recalibrate (BL-014 ADR)
    Logge: "[C9c_PostBerater] PHASE 4 recalibrate SKIP (M1, BL-014 ADR)."

# ═══ PHASE 5: postItem-Loop (max 5 Iterationen, INV-6 Alpha-Beta-Pruning) ═══
# Deterministisches Terminierungs-Guard — 5 Iterationen ohne gap_ready → ABORT (HARD_FAILURE)
PHASE 5: postItem-Loop
  post_iteration = 0
  MAX_POST_ITER  = 5

  LOOP:
    post_iteration += 1

    IF post_iteration > MAX_POST_ITER:
      # HARD_FAILURE: Loop-Limit ohne gap_ready
      Logge FEHLER: "[C9c_PostBerater] PHASE 5 postItem-Loop MAX_ITER={MAX_POST_ITER} erreicht. GAP noch > 0%. ABORT."
      Schreibe BDF-Signal: ABORTED, reason="postItem: MAX_ITER ohne gap_ready"
      [C9c_PostBerater] EXIT duration={ms}ms status=FAIL
      → RETURN exitcode=2

    Skill(_SDF_berater_postItem, args="{NAME}")
    post = BERATER_OUTPUTS.postItem

    Logge: "[C9c_PostBerater] PHASE 5 postItem iter={post_iteration}/{MAX_POST_ITER} — gap_percent={post.gap_percent}, gap_ready={post.gap_ready}"

    # Alpha-Beta-Pruning Gate (INV-6): gap_ready=true → sofortiger Loop-Abbruch
    IF post.gap_ready == true:
      Logge: "[C9c_PostBerater] PHASE 5 gap_ready=true — BREAK (Pruning, INV-6)."
      BREAK

    # Noch nicht bereit → naechste Iteration
    Logge: "[C9c_PostBerater] PHASE 5 gap nicht bereit (iter={post_iteration}/{MAX_POST_ITER}). Weiter."

  # post.gap_ready == true ab hier sichergestellt (sonst ABORT in Loop)

# ═══ PHASE 6: W20-Mitigation Post-Verify ═══
# Sicherstellen dass tdd_signal_pending sauber ist nach Phase 3 TDD-Routing (W20)
PHASE 6: TDD-Signal-Cleanup
  IF BERATER_OUTPUTS.sdfHub.tdd_signal_pending != null:
    IF manifest.I_PIPELINE_STATE.needs_tdd == false:
      # Signal bereits gecleart in Phase 3 → Cleanup-Confirmation
      BERATER_OUTPUTS.sdfHub.tdd_signal_pending = null
      Logge: "[C9c_PostBerater] PHASE 6 W20: tdd_signal_pending gecleart (Verify OK)."
    ELSE:
      # needs_tdd noch true → TDD noch pending, kein Clear
      Logge WARNUNG: "[C9c_PostBerater] PHASE 6 W20: needs_tdd noch true. tdd_signal_pending retained."
  ELSE:
    Logge: "[C9c_PostBerater] PHASE 6 W20: kein tdd_signal_pending — skip."

# ═══ PHASE 7: stage_orchestrate (gap_ready=true + GAP=0%) ═══
# Commit-Gate: GAP=0% UND W14 Regressions-Verify PASS (W15)
PHASE 7: Stage + Regressions-Verify
  # W14: T_orchestrate Regressions-Verify (M2-M6 PFLICHT; M7-M9: skip)
  IF modus IN ["M2", "M3", "M4", "M5", "M6"]:
    Logge: "[C9c_PostBerater] PHASE 7 Regressions-Verify T_orchestrate aufrufen (M2-M6 PFLICHT, W14)."
    # Regressions-Logik liegt in C6 _SDF_berater_postItem (testSearch W13)
    # C9c = Orchestrator-Level-Guard nach Stage-Commit (W16 Domain)

  # Commit-Gate: stage_orchestrate (W15)
  IF post.gap_ready == true AND post.gap_percent == 0:
    Logge: "[C9c_PostBerater] PHASE 7 stage_orchestrate aufrufen (GAP=0%, W15)."
    Skill(_stage_orchestrate, args="{NAME}")
    manifest.reload()

    # W16: REGRESSIONS-GUARD post-commit (Quick testRun)
    Logge: "[C9c_PostBerater] PHASE 7 REGRESSIONS-GUARD post-commit — Quick testRun (W16)."
    regressions_result = run_quick_test()
    IF regressions_result == FAIL:
      # HARD_FAILURE: Regressions-Guard post-commit
      Logge FEHLER: "[C9c_PostBerater] REGRESSIONS-GUARD FAIL! PL-Item erstellen + ABORT."
      Schreibe _parking-lot.md APPEND: "[ ] REGRESSION nach Stage-Commit {item_id} — Quick-testRun FAIL"
      Schreibe BDF-Signal: ABORTED, reason="REGRESSIONS-GUARD: post-commit testRun FAIL"
      [C9c_PostBerater] EXIT duration={ms}ms status=FAIL
      → RETURN exitcode=2
    ELSE:
      Logge: "[C9c_PostBerater] PHASE 7 REGRESSIONS-GUARD PASS."
  ELSE:
    Logge: "[C9c_PostBerater] PHASE 7 stage_orchestrate SKIP (gap_percent={post.gap_percent} != 0)."

# ═══ PHASE 8: statusTransition (C7) ═══
# Skip wenn item_type=null (INV-6)
PHASE 8: Status-Transition
  ctx_item_type = BERATER_OUTPUTS.itemContext.item_type

  IF ctx_item_type == null:
    # SOFT_DEGRADATION: item_type fehlt → Skip (kein Stop)
    Logge: "[C9c_PostBerater] PHASE 8 statusTransition SKIP (item_type=null, INV-6)."
  ELSE:
    Skill(_SDF_berater_statusTransition, args="{NAME}")
    st = BERATER_OUTPUTS.statusTransition
    Logge: "[C9c_PostBerater] PHASE 8 statusTransition DONE — pl={st.pl_transition}, bl={st.bl_transition}"

# ═══ PHASE 9: T_orchestrate (Ausbaustufe 2, optional) ═══
# Wird aktiviert wenn Ausbaustufe 2 deployed (nach BL-124 M4-Gate)
PHASE 9: T_orchestrate Post-Item
  # IF AUSBAUSTUFE_2_AKTIV:
  #   Skill(_T_orchestrate, args="{NAME}")
  # ELSE:
  Logge: "[C9c_PostBerater] PHASE 9 T_orchestrate: Ausbaustufe 2 — noch nicht aktiv."

[C9c_PostBerater] EXIT duration={ms}ms status=OK item_id={item_id}
→ RETURN exitcode=0
```

## Exitcode-Semantik

| Exitcode | Status | Bedeutung | SDF-Reaktion |
|----------|--------|-----------|-------------|
| 0 | OK | Alle Phasen PASS, Item abgeschlossen | CONTINUE (naechstes Item in Batch) |
| 2 | FAIL | Hard-Failure (postItem-Loop max / Regressions-Guard) | ABORT + BDF-Signal |

## Architektur-Notizen

- **Handschuh #3 von 3** (INV-5): C9c laeuft EINMAL nach Main-Skill. Kein Wiederaufruf innerhalb einer Item-Iteration.
- **C12/C13 als Phase 1+2** (Scope-Ext 2026-04-18): GarbageCollection + StateMaintain IMMER zuerst nach Orchestrator-Return. Kein Flag, kein Opt-In. Verhindert State-Log-Degradation (Vorfall 380→110 LOC 2026-04-18).
- **R1-Guard in Phase 3** (W20-Mitigation, Option B): C9c = Orchestrator darf I_PIPELINE_STATE schreiben. C4 (Berater) darf das NICHT (INV-2). needs_tdd-Clear geschieht NACH bestaetigtem POST_TDD, nicht vor TDD-Call (Kern-Unterschied zu SDF v0.8.0 Z1294-1296).
- **OQ-4 Resolution (Phase 1-2)**: GC + StateMaintain = Orchestrator-Verantwortung. WP_PIPELINE_STATE-Block schreiben in C9c (M9-Kontext). Kein eigener Berater noetig.
- **postItem-Loop max 5** (INV-6): Deterministisches Terminierungs-Guard. Nach 5 Iterationen ohne gap_ready → ABORT (HARD_FAILURE). Kein unendlicher Loop.
- **W16 REGRESSIONS-GUARD**: Post-commit Quick-testRun liegt in C9c (Orchestrator-Level-Guard), nicht in C6 oder C7. C6 postItem = GAP-Messung + testSearch (W13). C9c = Guard nach Stage-Commit.
- **G20/G21**: C12/C13 sind KEINE konditionellen Calls — sie laufen immer in Phase 1+2. Nur die Reaktion (CLEANED vs SKIP) variiert.
