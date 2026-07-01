---
type: satellite
---

# IDF-Pipeline (Parking-Lot-Verwalter) - Hilfe & Uebersicht

Zeige die Uebersicht der IDF-Pipeline (/_IDF_orchestrate) post-BL-142.

## Aufruf

```
/_IDF_help
```

---

## Updates 2026-05-19 (BL-173/174/175 Cross-Cutting)

**Manifest-Routing (BL-173):**
- IDF schreibt `IDF_PIPELINE_STATE` und `BERATER_OUTPUTS` in `{bl_folder}/_manifest.md` (pipeline-spezifisch)
- `{vault}/_factory_manifest.md` behaelt ausschliesslich BDF+GLOBAL_*-Bloecke
- Helper: `manifest_reader.read_factory_block(...)`, `manifest_reader.read_bl_block(bl_id, ...)`
- Migration: `migrate_manifest_split.py migrate --vault-root=... --rollback-tag=YYYY-MM-DD`

**Session-Params Per-BL (BL-174):**
- 3-Stufen-Inheritance: BL-Override → Vault-Default → Framework-Default
- Resolver: `session_params_resolver.resolve_param(name, bl_id=None)`
- `/_param` mit `--bl-id=BL-XXX` schreibt BL-spezifisch (IDF-Params pro BL isoliert)

**BDF Factory-Lock (BL-175):**
- `acquire/release/heartbeat` via `factory_lock.py`
- TTL+Heartbeat, kein fcntl, eigenes `_factory_lock.md`
- Race-Condition-safe fuer 5-10 parallele BDFs

(siehe `/_help` TEIL 8c, BL-173/174/175 Spec-Dateien)

---

## UPDATE BL-199 (2026-05-24) — IDF Loop-Check + Re-Entry-Mechanik

**Nach BL-199** hat IDF eine neue Phase A am Eingang:
- `_IDF_berater_loopCheck` vergleicht PL-Hash mit gespeichertem Snapshot
- `FULL_LOOP` (Erst-Eintritt oder neue PL-Items) → volle Phase 3.5-7.6
- `FULL_LOOP_WITH_REVERSE` (/_parking-lot Eingriff) → volle Schleife + Phase 3.7 REVERSE
- `BATCH_ONLY` (PL unveraendert) → naechsten Sub-Batch direkt an SDF, keine Phase 4-7.6

INV-IDF-LOOP-1..5 aktiv. Snapshot: `IDF_PIPELINE_STATE.pl_snapshot` im Manifest.

Referenz: BL-199, architecture-vision-2026-05-22.md Sanduhren-Prinzip

---

## UPDATE BL-209 (2026-05-24) — IDF Hard-Cut: Phase 2/3.1/3.2 ENTFERNT

**Nach BL-197 + BL-198 + BL-209** ist IDF eine WIRKLICH reine PL-Verwalterin:
- **PL-Erzeugung** kommt aus A-Pipeline Phase 5a/5b/5c — NICHT mehr aus IDF
- **IDF Entry** IMMER bei Phase 3.5 (validator) — Hard-Cut, kein Skip-Check mehr
- Phase 2/3.1/3.2 PHYSISCH ENTFERNT (BL-209) — kein Code, kein Skip, kein Fallback

**Was IDF NICHT mehr macht (nach BL-209 Hard-Cut):**
- Phase 2 specParse ENTFERNT → Single-Source: A-Pipeline Phase 5a (_A_berater_specParse)
- Phase 3.1 akExtraktion ENTFERNT → Single-Source: A-Pipeline Phase 5b (_A_berater_akExtraktion)
- Phase 3.2 plAggregation ENTFERNT → Single-Source: A-Pipeline Phase 5c (_A_berater_plAggregation)

**Was IDF weiterhin macht (als PL-Verwalterin):**
- Phase 3.5 validator (PL-Vollstaendigkeit pruefen)
- Phase 3.6 itemContext (PL-Frontmatter anreichern)
- Phase 3.7 modelSync (REVERSE: PL → Model, INV-IDF-REVERSE-1, Entry-3-Mechanik)
- Phase 4–7.6: DAG + Cluster + Batch-Plan + Stage + Metrics

**Entry-Points nach BL-198:**
- Entry 1 (Standard): A-Pipeline → pl_pre_filled_after=true → IDF ab Phase 3.5
- Entry 2 (Resync): _A_orchestrate --resync → IDF ab Phase 3.5
- Entry 3 (Direkt-PL): /_parking-lot → IDF (Phase 3.7 Reverse-Sync aktiv)

Referenz: BL-197 (A-Pipeline Phase 5a/5b/5c), BL-198 AK-1/2/3/6/7, INV-IDF-SKIP-1, INV-BC-1

---

## POSITION IN DER PIPELINE-REISE (3er-Doppel-Sicht, NEU 2026-05-24)

> **Cross-Reference:** Vollstaendige Reise + Geister-Tabelle: `/_help` TEIL 10
> Methodik: `.claude/INSTRUCTION_full_scan_2026-05-24.md`

**Wo sitzt /_IDF_orchestrate in der Gesamt-Reise?**

```
/_A_orchestrate → ★G#3 → /_A_postRoute → ★G#4 → /_IDF_orchestrate
                                                       │
                                                       │ (16 Phasen, 14 Berater)
                                                       ▼
                                                  ★G#5 → /_SDF_orchestrate
                                                  (Phase 8.5 Auto-Chain)
```

**3er-Doppel-Fenster:**

| Position | Vertrag                          | Lese-Fokus                          |
|----------|----------------------------------|-------------------------------------|
| [N-1]    | `/_A_postRoute`                  | Was wurde via DF_BATCH_STATE.routing_decision festgelegt? |
| [N  ]    | `/_IDF_orchestrate`              | LIEST + SCHREIBT (PL-Items + Batch-Plan)  |
| [N+1]    | `/_SDF_orchestrate`              | Was wird als naechstes gelesen (DF_BATCH_STATE.batch_items + batch_stages)? |

**Geister-Beteiligung:**

- **Input-Geist G#4:** `/_A_postRoute → /_IDF_orchestrate` (routing_decision=proceed + pl_pre_filled_after=true nach BL-209)
- **Output-Geist G#5:** `/_IDF Phase 8.5 → /_SDF_orchestrate` (Auto-Chain, INV-LIFECYCLE-5b kein TeamDelete)

**Re-Entry-Pfade (Loop-Wiedereintritte):**

- Von `/_SDF_orchestrate_post` Phase 4.2 SOFT-REPRIO → IDF `--mode=recluster --from=sdf_drift`
- Von `/_SDF_orchestrate_post` Phase 4.2 ROLLBACK → IDF `--mode=recheck --from=sdf_finish`
- Von `/_SDF_orchestrate_post` Phase 4.1.5 Orphan-Scan → IDF `--orphan-only --sticky-ids`
- Von Entry-3 `/_parking-lot` → IDF Phase A loopCheck (BL-199) erkennt PL-Drift

**Step-Anzahl im 1-Pipeline-Durchlauf:**

- 16 Top-Level-Phasen (A loopCheck → 1 init → 3.5..7.6 → 8.0 → 8.5)
- 14 Berater (alle gespawnt via Agent(), sonnet-floor wegen User-Direktive 2026-05-17)
- 0 Sub-Command-Calls (alles via Berater)
- Phase 2/3.1/3.2 ENTFERNT nach BL-209 Hard-Cut (PL-Items kommen aus A-Pipeline)

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  IDF-PIPELINE v2.2 (post-BL-199) — Reine PL-Verwalterin + Loop-Check  ║
║                                                                         ║
║  ZWECK (nach BL-198): IDF verwaltet PL-Items, baut DAG + Cluster +      ║
║         Batch-Plan und legt einen autoritativen Batch fuer SDF ab.      ║
║         PL-Erzeugung kommt aus A-Pipeline (Phase 5a/5b/5c).            ║
║                                                                         ║
║  NEU (BL-198): IDF Entry bei Phase 3.5 (validator) wenn A-Pipeline     ║
║         pl_pre_filled_after=true gesetzt hat. Phase 2/3.1/3.2 SKIP.    ║
║                                                                         ║
║  SINGLE-RESPONSIBILITY (post-BL-142/BL-198):                           ║
║    IDF DARF:        PL-Items verwalten + DAG + Cluster + Batch-Plan +  ║
║                     EXTERN/INTERN-Scan + Reverse-Sync (Phase 3.7)      ║
║    IDF DARF NICHT:  Mode entscheiden (-> SDF C3)                       ║
║                     Code generieren (-> SDF dispatchet zu I/SC/...)    ║
║                     PL-Items erzeugen (-> A-Pipeline Phase 5a/5b/5c)   ║
║                                                                         ║
║  ═══ UNIVERSAL 6-STUFEN-LIFECYCLE ═══                                  ║
║                                                                         ║
║    1. Vorgaenger-Team Cleanup (Stale-Detection >24h)                   ║
║    2. TeamCreate (Naming: idf-{BL_ID}, z.B. idf-BL-142)               ║
║    3. Modus-Erkennung (fresh / resync — bestimmt Tasks)               ║
║    4. Tasks + Dependencies vorab (Dependency-Graph)                    ║
║    5. Phasen-Ausfuehrung (Berater-Skill-Calls + Worker-Spawns)        ║
║    6. Team-Aufloesung (TeamDelete, active_team=null)                   ║
║                                                                         ║
║  ═══ PHASEN-DIAGRAMM ═══                                               ║
║                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │                                                                 │    ║
║  │   Phase A     Loop-Check (NEU BL-199 2026-05-24)               │    ║
║  │               [_IDF_berater_loopCheck]                         │    ║
║  │               PL-Hash vs Snapshot:                             │    ║
║  │                 FULL_LOOP          → normaler IDF-Lauf          │    ║
║  │                 FULL_LOOP_W_REVERSE → + Phase 3.7 REVERSE      │    ║
║  │                 BATCH_ONLY         → naechster Sub-Batch an SDF│    ║
║  │               INV-IDF-LOOP-1..5 aktiv                          │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 0     Resume-Detection                                  │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 0.9   BL-209 Hard-Cut (SIMPLIFIED): immer SKIP 2/3.1/3.2║    ║
║  │               Phase 2/3.1/3.2 ENTFERNT — IDF startet bei 3.5  │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 1     INIT [_IDF_berater_init]                         │    ║
║  │               Resume + State + TeamCreate                       │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   [Phase 2    ENTFERNT BL-209: → A-Pipeline Phase 5a]          │    ║
║  │   [Phase 3.1  ENTFERNT BL-209: → A-Pipeline Phase 5b]          │    ║
║  │   [Phase 3.2  ENTFERNT BL-209: → A-Pipeline Phase 5c]          │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 3.5   Validator (PL-Vollstaendigkeit, MIGR aus SDF)    │    ║
║  │               [_IDF_berater_validator]                         │    ║
║  │               *** IMMER Entry-Point (BL-209 Hard-Cut)          │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 3.6   Item-Context (PL-Frontmatter, MIGR aus SDF)      │    ║
║  │               [_IDF_berater_itemContext]                       │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 4     DEPENDENCY_MATRIX                                 │    ║
║  │               [_IDF_berater_dependencyAnalyzer]                │    ║
║  │               (absorbiert Ex-SDF-Berater)                       │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 5     CLUSTERING                                        │    ║
║  │               [_IDF_berater_clustering]                        │    ║
║  │               Kohaesion + Aggregate pro Cluster (Hint)          │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 6     BATCH_SEQUENCE                                    │    ║
║  │               [_IDF_berater_sequencePlanner]                   │    ║
║  │               (absorbiert Ex-SDF-Berater)                       │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 7     BATCH_PLAN (NEU)                                  │    ║
║  │               [_IDF_berater_batchPlan]                         │    ║
║  │               wraps batchPlanner                                │    ║
║  │               + EXTERN/INTERN-Scan                              │    ║
║  │               + Aggregate pro Batch                             │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 8.0   FINAL_SUMMARY (NEU BL-204)                        │    ║
║  │               [_IDF_berater_finalSummary]                       │    ║
║  │               READ-ONLY Konsolidierung aller IDF-Outputs        │    ║
║  │               Mensch: 9-Spalten-Tabelle (4_Blueprint/)          │    ║
║  │               Maschine: _manifest.md IDF_FINAL_SUMMARY YAML     │    ║
║  │               INV-MODUS-1: modus_hint != modus (Vorhersage)     │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 8     IDF_DONE → Recheck-Guard                         │    ║
║  │               liefert Batch an SDF                              │    ║
║  │                                                                 │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
║                                                                         ║
║  ═══ AUFRUF ═══                                                        ║
║                                                                         ║
║  /_IDF_orchestrate {BL_ID} [easy|normal|hard]                          ║
║                                                                         ║
║  Beispiele:                                                              ║
║    /_IDF_orchestrate BL-142                                             ║
║    /_IDF_orchestrate BL-142 hard                                        ║
║                                                                         ║
║  ═══ INPUTS ═══                                                        ║
║                                                                         ║
║    BL-Item.md (REIF)  — A's Output mit ak_anchors + Aggregate          ║
║    Spec.md            — AKs mit Anchors                                ║
║    Model.md           — W{n} mit TC{n}                                 ║
║    K-SCORE.md         — pro AK: k_score + srs + refs                   ║
║                                                                         ║
║  ═══ OUTPUTS ═══                                                       ║
║                                                                         ║
║    PL-Items (Parking-Lot)  — aus A-Pipeline Phase 5a/5b/5c (BL-198)   ║
║                               IDF verwaltet, erzeugt NICHT mehr        ║
║    DEPENDENCY-MATRIX.md    — Phase 4                                   ║
║    CLUSTER-MAP.md          — Phase 5                                   ║
║    BATCH-SEQUENCE.md       — Phase 6                                   ║
║    BATCH-PLAN-{N}.md       — Phase 7 (autoritativ)                     ║
║                                                                         ║
║  ═══ MIGRATIONS-MATRIX (post-BL-142) ═══                               ║
║                                                                         ║
║    4 Berater migriert von SDF nach IDF:                                ║
║      _IDF_berater_resumeGuard      (war: _SDF_berater_resumeGuard)    ║
║      _IDF_berater_validator        (war: _SDF_berater_validator)      ║
║      _IDF_berater_batchPlanner     (war: _SDF_berater_batchPlanner)   ║
║      _IDF_berater_itemContext      (war: _SDF_berater_itemContext)    ║
║                                                                         ║
║    2 Ex-SDF-Berater absorbiert in Phasen:                              ║
║      Phase 4: _IDF_berater_dependencyAnalyzer (war SDF-Berater)        ║
║      Phase 6: _IDF_berater_sequencePlanner    (war SDF-Berater)        ║
║                                                                         ║
║    5 Berater bleiben in SDF:                                           ║
║      _SDF_berater_modusEntscheidung (C3, kann nur SDF)                 ║
║      _SDF_berater_executionDispatch                                    ║
║      _SDF_berater_recalibrate                                          ║
║      _SDF_berater_postItem                                             ║
║      _SDF_berater_statusTransition                                     ║
║                                                                         ║
║  ═══ AGENT-TYPEN (vordefiniert) ═══                                    ║
║                                                                         ║
║    NUR: general-haiku, general-sonnet, general-opus                    ║
║    KEINE custom-Agent-Typen in IDF (nur in Sub-Orchestratoren)         ║
║    Tier-Cap via session_params (ceiling/floor)                         ║
║                                                                         ║
║  ═══ ANCHOR-KONVENTION ═══                                             ║
║                                                                         ║
║    spec_anchor:  { section: "## Phase A AK-A-1", ak_id: "AK-A-1" }   ║
║    model_anchor: { tc_id: "TC-2", w_id: "W-03" }                      ║
║    KEINE Zeilennummern                                                 ║
║                                                                         ║
║  ═══ DATENTRAEGER-KETTE ═══                                            ║
║                                                                         ║
║    BL-Item (REIF, von A)                                                ║
║         │                                                               ║
║         ▼                                                               ║
║    Phase 3.1 ak_metadata pro AK                                        ║
║         │                                                               ║
║         ▼                                                               ║
║    Phase 3.2 PL-Aggregat (k_score_pl, srs_pl, layer)                  ║
║         │                                                               ║
║         ▼                                                               ║
║    Phase 5 Cluster-Aggregat (Hint)                                     ║
║         │                                                               ║
║         ▼                                                               ║
║    Phase 7 BATCH-PLAN (Batch-Aggregat + EXTERN/INTERN)                 ║
║         │                                                               ║
║         ▼                                                               ║
║    SDF C3 (Mode M1-M9)                                                  ║
║                                                                         ║
║  ═══ VERWANDTE COMMANDS ═══                                            ║
║                                                                         ║
║    /_A_orchestrate    → Vorgaenger (liefert reifes BL-Item)            ║
║    /_SDF_orchestrate  → Nachfolger (konsumiert BATCH-PLAN)             ║
║    /_BDF_orchestrate  → Alternativ-Pfad (bei big_dark_factory=true)    ║
║    /_IDF_help_extended → Tiefe Narrative pro Phase (Assay-Format)     ║
║                                                                         ║
║  ═══ ABGRENZUNG ═══                                                    ║
║                                                                         ║
║    A_orchestrate:   Wissensbasis aufbauen, BL-Item + PL erzeugen       ║
║                     (Phase 5a specParse, 5b akExtraktion, 5c plAgg)    ║
║    IDF_orchestrate: PL verwalten + DAG + Cluster + Batch-Plan          ║
║                     (reine PL-Verwalterin nach BL-198, Entry ab 3.5)  ║
║    SDF_orchestrate: Mode (M1-M9) pro Batch + Dispatch + Lifecycle      ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Dann lies `.claude/_manifest.md` falls vorhanden und zeige den aktuellen Stand
der IDF-Pipeline.

Zeige auch: `/_IDF_help_extended` fuer Assay-tiefe Narrative pro Phase.

ARGUMENTS: $ARGUMENTS
