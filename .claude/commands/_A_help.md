---
type: satellite
---

# A-Pipeline (Wissensbasis-Bauer) - Hilfe & Uebersicht

Zeige die Uebersicht der A-Pipeline (/_A_orchestrate) post-BL-142.

## Aufruf

```
/_A_help
```

---

## Updates 2026-05-19 (BL-173/174/175 Cross-Cutting)

**Manifest-Routing (BL-173):**
- A-Pipeline schreibt `A_PIPELINE_STATE` jetzt in `{bl_folder}/_manifest.md` (pipeline-spezifisch)
- `{vault}/_factory_manifest.md` behaelt ausschliesslich BDF+GLOBAL_*-Bloecke
- Helper: `manifest_reader.read_factory_block(...)`, `manifest_reader.read_bl_block(bl_id, ...)`
- Migration: `migrate_manifest_split.py migrate --vault-root=... --rollback-tag=YYYY-MM-DD`

**Session-Params Per-BL (BL-174):**
- 3-Stufen-Inheritance: BL-Override → Vault-Default → Framework-Default
- Resolver: `session_params_resolver.resolve_param(name, bl_id=None)`
- `/_param` mit `--bl-id=BL-XXX` schreibt BL-spezifisch (A-Pipeline-Params pro BL isoliert)

**BDF Factory-Lock (BL-175):**
- `acquire/release/heartbeat` via `factory_lock.py`
- TTL+Heartbeat, kein fcntl, eigenes `_factory_lock.md`
- Race-Condition-safe fuer 5-10 parallele BDFs

(siehe `/_help` TEIL 8c, BL-173/174/175 Spec-Dateien)

---

## POSITION IN DER PIPELINE-REISE (3er-Doppel-Sicht, NEU 2026-05-24)

> **Cross-Reference:** Vollstaendige Reise + Geister-Tabelle: `/_help` TEIL 10
> Methodik: `.claude/INSTRUCTION_full_scan_2026-05-24.md`

**Wo sitzt /_A_orchestrate in der Gesamt-Reise?**

```
/_backlog → ★G#1 → /_BDF_orchestrate → ★G#1.5 → /_BL_orchestrate → ★G#2 → /_A_orchestrate
                                                                            │
                                                                            ▼
                                                                          ★G#3 → /_A_postRoute → ★G#4 → /_IDF_orchestrate
                                                                          (Phase 5 routing)
                                                                          (intern: G#2.5 → /_backlog update)
```

**3er-Doppel-Fenster (Standardfall: Fresh-BL via BL-Reifungs-Routing):**

| Position | Vertrag                          | Lese-Fokus                          |
|----------|----------------------------------|-------------------------------------|
| [N-1]    | `/_BL_orchestrate`               | Was wird ueber das BL-Item geschrieben?  |
| [N  ]    | `/_A_orchestrate`                | LIEST + SCHREIBT (12 Berater, ~20 Phasen) |
| [N+1]    | `/_A_postRoute` → `/_IDF_orchestrate` | Was wird als naechstes gelesen (routing_decision)? |

**Geister-Beteiligung:**

- **Input-Geist G#2:** `/_BL_orchestrate → /_A_orchestrate` (Reifungs-Trigger, UNREIF/DRAFT)
- **Intra-Geist G#2.5:** `/_A Phase 4.2a → /_backlog (Update-Modus)` (BL-Item-Update)
- **Intra-Geist G#3:** `/_A_berater_routing → /_A_postRoute` (Exit-Router-Wechsel)
- **Output-Geist G#4:** `/_A_postRoute → /_IDF_orchestrate` (Default: routing_decision=proceed)

**Step-Anzahl im 1-Pipeline-Durchlauf (modus=fresh):**

- 19 Top-Level-Phasen
- 12 Berater (alle gespawnt via Agent())
- 7 Sub-Command-Calls (`_taskDefinition`, `_git_analyse`, `_W_fetch`, `_model`/`_SC_modelMaintain`, `_spec`, `_K_score`, `_gap`, `_backlog`)
- Geschaetzt 80-150 Worker-Spawns insgesamt (bei normal-difficulty)

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  A-PIPELINE v2.0 (post-BL-142) — Wissensbasis-Bauer                    ║
║                                                                         ║
║  ZWECK: A baut die Wissensbasis fuer eine Aufgabe auf — Task, Model,    ║
║         Spec, K-Score, Gap — und legt eine REIFE BL-Item-Huelle ab.    ║
║         A zerlegt NICHT, A entscheidet KEINE Modi, A routet binaer.    ║
║                                                                         ║
║  SINGLE-RESPONSIBILITY (post-BL-142):                                  ║
║    A DARF:        Wissensbasis aufbauen + BL-Item-Huelle erzeugen      ║
║    A DARF NICHT:  Mode entscheiden (-> SDF C3)                         ║
║                   PL-Items / Decomposition (-> IDF)                    ║
║                   Routing-Detail waehlen (nur Binary BDF/IDF)          ║
║                                                                         ║
║  ═══ UNIVERSAL 6-STUFEN-LIFECYCLE ═══                                  ║
║                                                                         ║
║    1. Vorgaenger-Team Cleanup (Stale-Detection >24h)                   ║
║    2. TeamCreate (Naming: a-{NAME}, z.B. a-BL-142)                    ║
║    3. Modus-Erkennung (fresh / resync — bestimmt Tasks)               ║
║    4. Tasks + Dependencies vorab (Dependency-Graph)                    ║
║    5. Phasen-Ausfuehrung (Berater-Skill-Calls + Worker-Spawns)        ║
║    6. Team-Aufloesung (TeamDelete, active_team=null)                   ║
║                                                                         ║
║  ═══ PHASEN-DIAGRAMM ═══                                               ║
║                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │                                                                 │    ║
║  │   Phase 0.0   Cleanup + TeamCreate                             │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 0.1   Modus-Erkennung (fresh/resync)                   │    ║
║  │               [_A_berater_modusErkennung]                      │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 0.15  Tasks + Dependencies vorab                       │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 0.2   Discovery (optional name=auto)                   │    ║
║  │               [_A_berater_discovery]                           │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 0.5   Findings-Extraktion (Wellen 3D+1S Opus)          │    ║
║  │               [_A_berater_findingsExtraction]                  │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 0.5.2 HiL Findings Review                              │    ║
║  │               [_A_berater_findingsReview]                      │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 0.6   /_taskDefinition (DIREKT nach HiL Findings)      │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 1.5   Git-Analyse (optional pr=true)                   │    ║
║  │               [/_git_analyse]                                  │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 2     IDD-Context (optional --parent-pr)               │    ║
║  │               [_A_berater_iddContext]                          │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 3     /_model (liefert Such-Anker fuer W_fetch)        │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 3a    /_W_fetch (NEU SPAET, nutzt Task.md+Model)       │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 4     /_spec                                           │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 4k    /_K_score (Pro-AK)                               │    ║
║  │               srs_pro_ak + spec_anchor + model_refs + rf_refs  │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 4g    /_gap                                            │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 4.2a  Metadaten-Aggregation (+ /_backlog Spawn)        │    ║
║  │               [_A_berater_metadatenAggregation]                │    ║
║  │               6 Felder: aggregat_k_score / aggregat_srs_score /│    ║
║  │                         aggregat_gap_percent /                 │    ║
║  │                         aggregat_model_maturity /              │    ║
║  │                         aggregat_freiheitsgrade /              │    ║
║  │                         aggregat_is_meta_command               │    ║
║  │               + BL-Item-Huelle: reifegrad=REIF +               │    ║
║  │                 ak_anchors + srs_per_ak + k_score_per_ak       │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 4.4   Git-Tracking (last_sync_commit)                  │    ║
║  │               [_A_berater_gitTracking]                         │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 4.3   State-Maintain (Pattern B Rollover)              │    ║
║  │               [_A_berater_stateMaintain]                       │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 5     Routing 2-Path Binary (LAST)                     │    ║
║  │               [_A_berater_routing]                             │    ║
║  │               big_dark_factory=true → BDF, sonst → IDF         │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 0.0X  TeamDelete                                       │    ║
║  │                                                                 │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
║                                                                         ║
║  ═══ AUFRUF ═══                                                        ║
║                                                                         ║
║  /_A_orchestrate [NAME] [name=auto] [pr=true] [--parent-pr]            ║
║                                                                         ║
║  Beispiele:                                                              ║
║    /_A_orchestrate BL-142                       # Standard               ║
║    /_A_orchestrate name=auto                    # Discovery               ║
║    /_A_orchestrate BL-142 pr=true               # mit Git-Analyse        ║
║                                                                         ║
║  ═══ OUTPUTS ═══                                                       ║
║                                                                         ║
║    Task.md         — Aufgabe + Kruemmel aus pileOfMud                  ║
║    Model.md        — W{n} Wissens-Knoten                               ║
║    Spec.md         — Ziel-Architektur (## Phase A AK-A-1 etc.)         ║
║    K-SCORE.md      — Per-AK: srs + anchors + refs                      ║
║    Gap.md          — IST vs SOLL Delta                                 ║
║    BL-Item.md      — Huelle: reifegrad=REIF + Aggregate                ║
║                                                                         ║
║  ═══ REIFEGRAD (2-stufig) ═══                                          ║
║                                                                         ║
║    REIF    — A komplett durchgelaufen, BL-Item bereit fuer IDF-Pickup  ║
║    FRISCH  — BL-Stub, A muss noch laufen                               ║
║                                                                         ║
║  ═══ AGENT-TYPEN (vordefiniert) ═══                                    ║
║                                                                         ║
║    NUR: general-haiku, general-sonnet, general-opus                    ║
║    KEINE custom-Agent-Typen in A (nur in Sub-Orchestratoren)           ║
║    Tier-Cap via session_params (ceiling/floor)                         ║
║                                                                         ║
║  ═══ ANCHOR-KONVENTION ═══                                             ║
║                                                                         ║
║    spec_anchor:  { section: "## Phase A AK-A-1", ak_id: "AK-A-1" }   ║
║    model_anchor: { tc_id: "TC-2", w_id: "W-03" }                      ║
║    KEINE Zeilennummern (fragil)                                        ║
║                                                                         ║
║  ═══ DATENTRAEGER-KETTE (durch alle Schichten) ═══                     ║
║                                                                         ║
║    A.K_score (Phase 3d)    → pro AK: k_score, srs, anchor, refs       ║
║         │                                                               ║
║         ▼                                                               ║
║    A./_backlog (Phase 4.2b) → BL-Item: REIF + Aggregate                ║
║         │                                                               ║
║         ▼                                                               ║
║    IDF Phase 3.1+3.2       → AK-Metadata + PL-Aggregate                ║
║         │                                                               ║
║         ▼                                                               ║
║    IDF Phase 7 BATCH_PLAN  → Batch-Aggregat + EXTERN/INTERN            ║
║         │                                                               ║
║         ▼                                                               ║
║    SDF C3 modusEntscheidung → M1-M9                                    ║
║                                                                         ║
║  ═══ VERWANDTE COMMANDS ═══                                            ║
║                                                                         ║
║    /_IDF_orchestrate   → Decomposition (Phase nach A bei IDF-Routing)  ║
║    /_BDF_orchestrate   → Big-Dark-Factory (bei Routing big_dark)       ║
║    /_taskDefinition    → Phase 0.6 Sub-Command                         ║
║    /_model             → Phase 3 Sub-Command                           ║
║    /_W_fetch           → Phase 3a Sub-Command (nach _model)            ║
║    /_spec              → Phase 4 Sub-Command                           ║
║    /_K_score           → Phase 4k Sub-Command                          ║
║    /_gap               → Phase 4g Sub-Command                          ║
║    /_backlog           → Phase 4.2a (durch metadatenAggregation)       ║
║    /_git_analyse       → Phase 1.5 (optional pr=true)                  ║
║    /_A_help_extended   → Tiefe Narrative pro Phase (Assay-Format)     ║
║                                                                         ║
║  ═══ ABGRENZUNG ═══                                                    ║
║                                                                         ║
║    A_orchestrate:   Wissensbasis aufbauen, BL-Item-Huelle erzeugen     ║
║    IDF_orchestrate: Spec→PL-Items + DAG + Cluster + Batch-Plan         ║
║    SDF_orchestrate: Mode (M1-M9) pro Batch + Dispatch + Lifecycle      ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Dann lies `.claude/_manifest.md` falls vorhanden und zeige den aktuellen Stand der A-Pipeline.

Zeige auch: `/_A_help_extended` fuer Assay-tiefe Narrative pro Phase.

ARGUMENTS: $ARGUMENTS
