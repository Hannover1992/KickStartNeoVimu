---
type: satellite
---

# Small Dark Factory - Hilfe & Uebersicht

Zeige die Uebersicht der SDF-Pipeline (/_SDF_*) post-BL-142.

## Aufruf

```
/_SDF_help
```

---

## Updates 2026-05-19 (BL-173/174/175 Cross-Cutting)

**Manifest-Routing (BL-173):**
- SDF schreibt `DF_BATCH_STATE` und `DF_PIPELINE_STATE` in `{bl_folder}/_manifest.md` (pipeline-spezifisch)
- `{vault}/_factory_manifest.md` behaelt ausschliesslich BDF+GLOBAL_*-Bloecke
- Helper: `manifest_reader.read_factory_block(...)`, `manifest_reader.read_bl_block(bl_id, ...)`
- Migration: `migrate_manifest_split.py migrate --vault-root=... --rollback-tag=YYYY-MM-DD`

**Session-Params Per-BL (BL-174):**
- 3-Stufen-Inheritance: BL-Override → Vault-Default → Framework-Default
- Resolver: `session_params_resolver.resolve_param(name, bl_id=None)`
- `/_param` mit `--bl-id=BL-XXX` schreibt BL-spezifisch (SDF-Params pro BL isoliert)

**BDF Factory-Lock (BL-175):**
- Factory-Lock optional aktivierbar via BL-175 fuer parallele SDF-Instanzen
- `acquire/release/heartbeat` via `factory_lock.py`, eigenes `_factory_lock.md`
- TTL+Heartbeat, kein fcntl, Race-Condition-safe fuer 5-10 parallele BDFs

(siehe `/_help` TEIL 8c, BL-173/174/175 Spec-Dateien)

---

## POSITION IN DER PIPELINE-REISE (3er-Doppel-Sicht, NEU 2026-05-24)

> **Cross-Reference:** Vollstaendige Reise + Geister-Tabelle: `/_help` TEIL 10
> Methodik: `.claude/INSTRUCTION_full_scan_2026-05-24.md`

**Wo sitzt /_SDF_orchestrate in der Gesamt-Reise?**

```
/_IDF_orchestrate → ★G#5 → /_SDF_orchestrate (Pre-SDF, Phase 0-2 + Outer-Loop)
                                  │
                                  │ Phase 2.1 SWITCH modus
                                  ▼
                              ★G#6 → /_I_orch ODER /_SC_orch (M2/M3 vs M4-M9)
                                          │
                                          │ POST_HANDOVER
                                          ▼
                                      ★G#7 → /_SDF_orchestrate_post (Post-SDF, Phase 3+4)
                                                  │
                                                  ▼
                                              ★G#8 → /_SDF_orch / /_IDF / BDF
                                                     (Phase 4.2 Exit-Routing)
```

**3er-Doppel-Fenster (Pre-SDF):**

| Position | Vertrag                          | Lese-Fokus                          |
|----------|----------------------------------|-------------------------------------|
| [N-1]    | `/_IDF_orchestrate` Phase 8.5    | DF_BATCH_STATE.batch_items + batch_stages + metric_per_batch |
| [N  ]    | `/_SDF_orchestrate` (Pre-SDF)    | LIEST + SCHREIBT (Outer-Loop dispatch zu I/SC) |
| [N+1]    | `/_I_orch` ODER `/_SC_orch`      | Was wird als naechstes gelesen (modus-abhaengig)? |

**3er-Doppel-Fenster (Post-SDF):**

| Position | Vertrag                          | Lese-Fokus                          |
|----------|----------------------------------|-------------------------------------|
| [N-1]    | `/_I_orchestrate` POST_HANDOVER  | Was hat I geschrieben (BERATER_OUTPUTS, stage-Output)? |
| [N  ]    | `/_SDF_orchestrate_post`         | LIEST + SCHREIBT (Wave 1+2, batchEnde, loopDecision) |
| [N+1]    | `/_SDF_orch` ODER `/_IDF_orch` ODER BDF | Exit-Routing-Target (RE-BATCH / ROLLBACK / TERMINATE) |

**Geister-Beteiligung:**

- **Input-Geist G#5:** `/_IDF Phase 8.5 → /_SDF_orchestrate` (Auto-Chain ohne TeamDelete)
- **Intra-Geist G#6:** `/_SDF Phase 2.1 dispatch → /_I_orch ODER /_SC_orch` (SWITCH M1..M9)
- **Output-Geist G#7:** `/_I/_SC → /_SDF_orchestrate_post` (POST_HANDOVER, INV-HANDOVER-1)
- **Re-Entry-Geist G#8:** `/_SDF_orchestrate_post → /_SDF_orch / /_IDF / BDF` (Phase 4.2)

**Outer-Loop + Stage-Inner-Loop:**

```
⟲ OUTER-LOOP (pro Sub-Batch):
   1.1 modusEntscheidung → 1.5 patternBrief →
   ⟲ STAGE-INNER-LOOP (WHILE+Decision, BL-171):
      2.1 dispatch → ★G#6 → [I/SC laeuft] → ★G#7 → [Post-SDF Phase 3+4]
      2.2 stageElevation → ELEVATE/BATCH_DONE/RETRY/ABORT/HALT
```

**Step-Anzahl im 1-Pipeline-Durchlauf:**

- Pre-SDF: 10 Top-Level-Phasen + Outer-Loop (pro Sub-Batch ~3 Phasen + Inner-Loop)
- Post-SDF: 15 Schritte (3.0.5, Wave 1+2, 3.3.5, 3.4, 3.6.0, 3.6.1, 3.6b, 3.99, 4.1, 4.1.5, 4.2)
- 6 Pre-SDF Berater + 8 Post-SDF Berater = 14 SDF-Berater insgesamt
- 1 Sub-Command-Call: `_stage_orchestrate` (Phase 3.3.5 Commit pro Round)

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  SMALL DARK FACTORY v0.18 (post-BL-142) — Mode-Decision + Dispatch     ║
║                                                                         ║
║  ZWECK: SDF konsumiert den BATCH-PLAN von IDF, entscheidet pro Batch    ║
║         den Modus (M1-M9) und dispatched zu I/SC/TDD/WP/PR. SDF baut    ║
║         keinen Code; SDF entscheidet, WIE gebaut wird.                  ║
║                                                                         ║
║  SINGLE-RESPONSIBILITY (post-BL-142):                                  ║
║    SDF DARF:        Mode (M1-M9) pro Batch + Dispatch + Lifecycle      ║
║    SDF DARF NICHT:  Spec parsen (-> IDF Phase 2)                       ║
║                     PL-Items erfinden (-> IDF Phase 3.2)               ║
║                     DAG / Cluster bauen (-> IDF Phase 4-5)             ║
║                                                                         ║
║  ═══ UNIVERSAL 6-STUFEN-LIFECYCLE ═══                                  ║
║                                                                         ║
║    1. Vorgaenger-Team Cleanup (Stale-Detection >24h)                   ║
║    2. TeamCreate (Naming: sdf-{NAME}, z.B. sdf-BL-142)                ║
║    3. Modus-Erkennung (fresh / resume — bestimmt Tasks)               ║
║    4. Tasks + Dependencies vorab (Dependency-Graph)                    ║
║    5. Phasen-Ausfuehrung (Berater-Skill-Calls + Worker-Spawns)        ║
║    6. Team-Aufloesung (TeamDelete, active_team=null)                   ║
║                                                                         ║
║  ═══ PHASEN-DIAGRAMM (BL-NEW-12 SPLIT 2026-05-11) ═══                  ║
║                                                                         ║
║  SDF ist in zwei Skills aufgeteilt (Skill-Context-Override-Fix):       ║
║    Pre-SDF  /_SDF_orchestrate       (Phase 0-2 + Outer-Loop + FINAL)  ║
║    Post-SDF /_SDF_orchestrate_post  (Phase 3-4, von I/SC gerufen)    ║
║                                                                         ║
║  ┌──── Pre-SDF /_SDF_orchestrate ────────────────────────────────┐    ║
║  │   Phase 0     Lite-Resume-Guard (batch_status check)            │    ║
║  │   Phase 0.5   testRun-Fork (--mode=testRun)                     │    ║
║  │   Phase 1.0   architecturalBrief (1×, cached)                   │    ║
║  │                                                                  │    ║
║  │   OUTER-LOOP-WRAPPER (Z528-543):                                │    ║
║  │     FOR batch_key IN batch_items_per_batch:                     │    ║
║  │       IF batch_key IN completed_sub_batches: SKIP               │    ║
║  │       Phase 1.1 modusEntscheidung (M1..M9)                      │    ║
║  │       Phase 1.5 patternBrief                                    │    ║
║  │       Phase 1.6 IDF-GATE                                        │    ║
║  │       Phase 2.1 EXECUTION DISPATCH:                             │    ║
║  │          Skill(_I_orchestrate ...) [oder _SC_orchestrate]       │    ║
║  │             |                                                    │    ║
║  │             | NACHPHASE + POST_HANDOVER                          │    ║
║  │             v                                                    │    ║
║  │          Skill(_SDF_orchestrate_post)  ← SIEHE UNTEN            │    ║
║  │             |                                                    │    ║
║  │             | RETURN (RE-BATCH/TERMINATE) oder                   │    ║
║  │             | Skill(_IDF_orchestrate) (SOFT-REPRIO/ROLLBACK)    │    ║
║  │             v                                                    │    ║
║  │       completed_sub_batches.append(batch_key)                   │    ║
║  │     END LOOP                                                    │    ║
║  │                                                                  │    ║
║  │   Phase FINAL: TeamDelete + Protokoll-Rollover + Checkpoint C   │    ║
║  └──────────────────────────────────────────────────────────────┘    ║
║                                                                         ║
║  ┌──── Post-SDF /_SDF_orchestrate_post (von I/SC gerufen) ──────┐    ║
║  │   Phase 0       Entry-Log (SKILL_LOAD audit.jsonl)             │    ║
║  │   Phase 3.0.5   BUILD-Sanity (modus-bedingt: M1/worker-mode)   │    ║
║  │                                                                 │    ║
║  │   WAVE 1 (parallel):                                            │    ║
║  │     3.1 recalibrate (Early-Exit: model_diff || Grundsubstanz)   │    ║
║  │     3.2 postItem (GAP-Check)                                    │    ║
║  │   WAVE 2 (parallel):                                            │    ║
║  │     3.3 statusTransition                                        │    ║
║  │     3.5 modelSync (intra-Spec)                                  │    ║
║  │   Schritt 3.3.5: stage_orchestrate Commit                       │    ║
║  │                                                                 │    ║
║  │   Phase 3.4 batchEnde (NUR letzte Round im Batch):              │    ║
║  │     WAVE 3 (parallel): PT_promoteFromPL || SL_promoteFromPL    │    ║
║  │                                                                 │    ║
║  │   Phase 3.6 stageElevation (nach BATCH_DONE):                  │    ║
║  │   Phase 3.6b post_sc_pl_resync (BL-208 NEU):                   │    ║
║  │     Guard: sc_cycle_done=true (sonst SKIP)                      │    ║
║  │     SC-Delta → PL-Items (REMOVE/Scope/NO-OP/HOLD-Append)       │    ║
║  │     INV-PL-RESYNC-1..4 aktiv                                    │    ║
║  │                                                                 │    ║
║  │   Phase 4 loopDecision:                                         │    ║
║  │     RE-BATCH    -> RETURN (Pre-SDF outer-loop iteriert)         │    ║
║  │     SOFT-REPRIO -> Skill(_IDF_orchestrate --recluster)          │    ║
║  │     ROLLBACK    -> Skill(_IDF_orchestrate --recheck)            │    ║
║  │     TERMINATE   -> RETURN (Pre-SDF Phase FINAL erreicht)        │    ║
║  └────────────────────────────────────────────────────────────────┘    ║
║                                                                         ║
║  INVARIANTEN (BL-NEW-12 + BL-208):                                       ║
║    INV-HANDOVER-1     I/SC MUSS Skill(_SDF_orchestrate_post) am Ende    ║
║    INV-NO-RESUME-RECURSION  Post-SDF RE-BATCH = RETURN, kein Skill-Call ║
║    INV-AUDIT-CHAIN   audit.jsonl: SKILL_LOAD(_SDF_orchestrate) → ...    ║
║    INV-PL-RESYNC-1   Phase 3.6b MUSS nach SC-Cycle, VOR loopDecision   ║
║    INV-PL-RESYNC-2   Input: NUR SC-Output-Aenderungs-Set (kein Mega-RF) ║
║    INV-PL-RESYNC-3   Schreibt NUR resync_*-Prefix-Felder in PL-Items   ║
║    INV-PL-RESYNC-4   HOLD Side-Findings werden APPENDED (nicht merged)  ║
║                                                                         ║
║  ═══ MODE-MAPPING (M1-M9) ═══                                          ║
║                                                                         ║
║    M1   Skip / Recalibrate (BL-014: kein Code-Aufwand noetig)          ║
║    M2   Inline / Direct (kleine Aenderung, /_I_orchestrate -I)         ║
║    M3   I-Pipeline standalone (volle I, scope=full)                    ║
║    M4   SC-Inline (SC-Zyklen mit Inline-Implement)                     ║
║    M5   SC-Symbiose (SC⟲I, I scope=core)                              ║
║    M6   SC-Analyse (reine Analyse, kein Code)                          ║
║    M7   TDD-fokussiert (TDD-Pipeline)                                  ║
║    M8   PR-Review-Modus                                                 ║
║    M9   WP / Paper-Pipeline                                             ║
║                                                                         ║
║    Entscheidung in Phase 1 (C3) basiert auf:                           ║
║      - aggregat_k_score (Reife der Wissensbasis)                       ║
║      - aggregat_srs_score (System-Reflection)                          ║
║      - aggregat_gap_percent (IST vs SOLL Delta)                        ║
║      - aggregat_freiheitsgrade (wie viele Wege?)                       ║
║      - unreife_typ (was fehlt?)                                        ║
║      - reifegrad (REIF / FRISCH)                                       ║
║                                                                         ║
║  ═══ AUFRUF ═══                                                        ║
║                                                                         ║
║  /_SDF_orchestrate {NAME} [easy|normal|hard] [ceiling] [floor]         ║
║                                                                         ║
║  Beispiele:                                                              ║
║    /_SDF_orchestrate BL-142                                             ║
║    /_SDF_orchestrate BL-142 hard opus haiku                             ║
║                                                                         ║
║  ═══ INPUTS ═══                                                        ║
║                                                                         ║
║    BATCH-PLAN-{N}.md (von IDF Phase 7) — autoritativ                   ║
║    BL-Item.md (von A, REIF) — Aggregate                                ║
║    PL-Items im Parking-Lot — pro Batch                                 ║
║                                                                         ║
║  ═══ BERATER-INVENTAR (post-BL-142) ═══                                ║
║                                                                         ║
║    Pre-SDF Berater (Phase 0-2):                                        ║
║      _SDF_berater_resumeGuard (Phase 0)                                ║
║      _SDF_berater_analyse (Phase 1.0)                                  ║
║      _SDF_berater_architecturalBrief (Phase 1.0, cached)               ║
║      _SDF_berater_modusEntscheidung (Phase 1.1)                        ║
║      _SDF_berater_patternBrief (Phase 1.5)                             ║
║      _SDF_berater_executionDispatch (Phase 2.1)                        ║
║                                                                         ║
║    Post-SDF Berater (Phase 3-4):                                       ║
║      _SDF_berater_recalibrate (Wave 1 — Early-Exit-Gate BL-NEW-7)      ║
║      _SDF_berater_postItem (Wave 1)                                    ║
║      _SDF_berater_statusTransition (Wave 2)                            ║
║      _SDF_berater_modelSync (Wave 2)                                   ║
║      _SDF_berater_batchEnde (Phase 3.4 + Wave 3 PT/SL)                 ║
║      _SDF_berater_loopDecision (Phase 4 — RE-BATCH/SOFT-REPRIO/...)    ║
║                                                                         ║
║    Migriert zu IDF (4):                                                ║
║      resumeGuard, validator, batchPlanner, itemContext                 ║
║                                                                         ║
║    Absorbiert in IDF-Phasen (2):                                       ║
║      dependencyAnalyzer (IDF Phase 4)                                  ║
║      sequencePlanner (IDF Phase 6)                                     ║
║                                                                         ║
║  ═══ AGENT-TYPEN (vordefiniert) ═══                                    ║
║                                                                         ║
║    NUR: general-haiku, general-sonnet, general-opus                    ║
║    KEINE custom-Agent-Typen in SDF (nur in Sub-Orchestratoren)         ║
║    Tier-Cap via session_params (ceiling/floor)                         ║
║                                                                         ║
║    Phase 1 C3 Ziel-Tier=opus (Mode-Decision ist heuristisch + komplex) ║
║      → effektives Tier = min(opus, ceiling)                            ║
║      → bei ceiling=sonnet laeuft C3 auf sonnet (gecappt)               ║
║                                                                         ║
║  ═══ LOOP-DECISION (Phase 4, 3 Pfade) ═══                              ║
║                                                                         ║
║    1. ROLLBACK zu IDF Phase 4-7:                                       ║
║       Phase 2 hat NEUE PL-Items entdeckt (Spec-Drift, Sub-Tasks).      ║
║       SDF schickt zurueck an IDF, das DAG / Cluster / BATCH neu baut.  ║
║                                                                         ║
║    2. TERMINATE:                                                        ║
║       Alle Batches durch, alle BL-Items DONE.                          ║
║       SDF schliesst Pipeline ab.                                       ║
║                                                                         ║
║    3. RE-BATCH (IDF Phase 7 direkt):                                   ║
║       Naechster Batch im gleichen BATCH-PLAN. Kein Re-Init.            ║
║                                                                         ║
║  ═══ AUTONOMIE ═══                                                     ║
║                                                                         ║
║    GLOBAL_HIL=off (Default fuer Dark Factory)                          ║
║    HiL-Checkpoints NUR bei:                                            ║
║      - SC-ABORT (Stagnation >= 7.0)                                    ║
║      - TDD-MAX (Backtrack erschoepft)                                  ║
║      - Mode-Decision-Konflikt (C3 unsicher)                            ║
║                                                                         ║
║  ═══ ABGRENZUNG ═══                                                    ║
║                                                                         ║
║    Small Dark Factory: EIN Batch autonom (1 BL-Item, n PL-Items)       ║
║    Big Dark Factory:   N Batches autonom (BDF orchestriert mehrere SDF)║
║                                                                         ║
║  ═══ VERWANDTE COMMANDS ═══                                            ║
║                                                                         ║
║    /_A_orchestrate    → Wissensbasis-Bauer (Vor-Vorgaenger)            ║
║    /_IDF_orchestrate  → Decomposition (direkter Vorgaenger)            ║
║    /_BDF_orchestrate  → Multi-Batch-Orchestrator (Container fuer SDF)  ║
║    /_I_orchestrate    → Mode M2/M3 Dispatch-Ziel                       ║
║    /_SC_orchestrate   → Mode M4/M5/M6 Dispatch-Ziel                    ║
║    /_TDD_orchestrate  → Mode M7 Dispatch-Ziel                          ║
║    /_WP_orchestrate   → Mode M9 Dispatch-Ziel                          ║
║    /_Post_PR_orchestrate → Mode M8 Dispatch-Ziel                       ║
║    /_param            → Session-Parameter setzen                        ║
║    /_parking-lot      → PL-Items / Incidental Findings                  ║
║    /_SDF_help_extended → Tiefe Narrative pro Phase (Assay-Format)     ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Dann lies `.claude/_manifest.md` falls vorhanden und zeige den aktuellen Stand
der SDF-Pipeline.

Zeige auch: `/_SDF_help_extended` fuer Assay-tiefe Narrative pro Phase.

ARGUMENTS: $ARGUMENTS
