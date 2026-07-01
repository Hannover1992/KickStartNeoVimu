---
type: satellite
created: 2026-05-24
version: 1.0
governing_skill: /_BL_orchestrate
parent_help: /_help
created_for_bl: BL-210 M6
---

# BL-Lifecycle-Manager - Hilfe & Uebersicht

Zeige die Uebersicht des /_BL_orchestrate Backlog-Lifecycle-Managers (Block A, WAS-Schicht).

## Aufruf

```
/_BL_help
```

---

## POSITION IN DER PIPELINE-REISE (3er-Doppel-Sicht)

> **Cross-Reference:** Vollstaendige Reise + Geister-Tabelle: `/_help` TEIL 10
> Methodik: `.claude/INSTRUCTION_full_scan_2026-05-24.md`

**Wo sitzt /_BL_orchestrate in der Gesamt-Reise?**

```
/_backlog (DRAFT-Item) → ★G#1 → /_BDF_orchestrate Phase 2 SCANNING
                                                  │
                                                  │ reifegrad=UNREIF? → REIFUNGS-GATE
                                                  ▼
                                              ★G#1.5 → /_BL_orchestrate
                                                            │
                                                            │ Phase 7 A_PIPELINE_TRIGGER
                                                            ▼
                                                        ★G#2 → /_A_orchestrate
```

**3er-Doppel-Fenster:**

| Position | Vertrag                          | Lese-Fokus                          |
|----------|----------------------------------|-------------------------------------|
| [N-1]    | `/_BDF_orchestrate` Phase 2      | needs_reifung-Liste, items_stucked  |
| [N  ]    | `/_BL_orchestrate`               | LIEST + SCHREIBT (lifecycle, A-Trigger) |
| [N+1]    | `/_A_orchestrate` (bei UNREIF)   | A-Pipeline Frontmatter Updates      |

**Geister-Beteiligung:**

- **Input-Geist G#1.5:** `/_BDF Phase 2 SCANNING` → `/_BL_orchestrate` (reifegrad=UNREIF)
- **Output-Geist G#2:** `/_BL_orchestrate Phase 7` → `/_A_orchestrate` (needs_a_pipeline=true)
- **Re-Loop-Geist:** Phase 9 AUTO-CHAIN → `/_BDF_orchestrate` wenn items_routed_ready > 0

---

## SYSTEM-UEBERSICHT

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  BL-LIFECYCLE-MANAGER v1.3.0 (BL-078b Slim Refactor)                      ║
║                                                                         ║
║  ZWECK: BL = Einmal-Lauf (On-Demand, kein Loop).                       ║
║         Bewertet Backlog-Items, routet zu A/WP/SC, eskaliert.          ║
║         Reifungs-Routing fuer DRAFT/UNREIF-Items.                       ║
║                                                                         ║
║  SINGLE-RESPONSIBILITY:                                                ║
║    BL DARF:        Lebenszyklus-Check + Wahrheiten-Routing + A-Trigger ║
║    BL DARF NICHT:  Code generieren / Modi entscheiden / direkte SDF    ║
║                    Aufrufe (Skill_SDF_orchestrate verboten — INV-4)    ║
║                                                                         ║
║  ═══ STATE-MACHINE (5 aktive Phasen, terminiert nach 1 Lauf) ═══       ║
║                                                                         ║
║    INIT → LIFECYCLE_CHECK → WAHRHEITEN_ROUTING → A_PIPELINE_TRIGGER →   ║
║    DONE                                                                 ║
║                                                                         ║
║    Phase 4/5/6/8 ENTFERNT (BL-078b: TRIAGE/DEPENDENCY/MITOSE/STATUS    ║
║    wanderten zu IDF Phase 4-6 + BDF Phase 2b)                           ║
║                                                                         ║
║  ═══ PHASEN-DIAGRAMM ═══                                                ║
║                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │                                                                 │    ║
║  │   Phase 1     INIT                                              │    ║
║  │               BL_LIFECYCLE_STATE initialisieren                 │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 2     LIFECYCLE_CHECK                                   │    ║
║  │               Teil A: gap_percent + model_maturity → Phase       │    ║
║  │                       (INITIAL | LAUFEND | UEBERGANG)            │    ║
║  │               Teil B: items_stucked-Backward-Kanal lesen        │    ║
║  │                       Reifungsrunden++ pro Item                 │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 3     WAHRHEITEN_ROUTING                                │    ║
║  │               Model-Reife berechnen (W{n} zaehlen)               │    ║
║  │               HIGH/MED/LOW Klassifikation                       │    ║
║  │               intern/extern → RESYNC_KANDIDAT | WP_KANDIDAT      │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 7     A_PIPELINE_TRIGGER                                │    ║
║  │               needs_a_pipeline=true → Skill(_A_orchestrate)     │    ║
║  │               Pro Item: A-Pipeline Fresh-Lauf                    │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   Phase 9     DONE                                              │    ║
║  │               BL_LIFECYCLE_STATE finalisieren                    │    ║
║  │               AUTO-CHAIN: items_routed_ready > 0 → BDF starten  │    ║
║  │                                                                 │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
║                                                                         ║
║  ═══ AUFRUF ═══                                                        ║
║                                                                         ║
║    /_BL_orchestrate [ceiling=opus] [floor=haiku]                       ║
║                     [--mode=normal|recheck]                            ║
║                     [--from=direct|bdf_empty|sdf_finish|idf_plan]      ║
║                                                                         ║
║    Beispiele:                                                           ║
║      /_BL_orchestrate                  # Default, vollstaendiger Lauf  ║
║      /_BL_orchestrate --mode=recheck --from=bdf_empty                  ║
║                                        # Recheck ohne Phase 9 Auto-Chain║
║                                                                         ║
║  ═══ INPUTS ═══                                                        ║
║                                                                         ║
║    {VAULT}/_manifest.md → BL_LIFECYCLE_STATE, items_stucked            ║
║    {VAULT}/_backlog_index.md → status DRAFT/READY                     ║
║    {VAULT}/Backlog/*.md → reifegrad, dependencies, needs_a_pipeline    ║
║    {WORKING_DIR}/.claude/models/{NAME}_Model.md → W{n} count            ║
║                                                                         ║
║  ═══ OUTPUTS ═══                                                       ║
║                                                                         ║
║    {VAULT}/_manifest.md → BL_LIFECYCLE_STATE (bl_status, lifecycle_    ║
║                            phase, routing_empfehlung, items_routed_*)   ║
║    {VAULT}/_backlog_index.md → status DRAFT→READY                     ║
║    {VAULT}/Backlog/*.md → reifegrad nach A-Pipeline                    ║
║                                                                         ║
║  ═══ AUTONOMIE-MATRIX ═══                                              ║
║                                                                         ║
║    | --mode | --from | Phase 9 AUTO-CHAIN | Use-Case                  ║
║    |--------|--------|---------------------|--------------------------║
║    | normal | direct | YES (zu BDF)        | Standard-Lauf            ║
║    | recheck| bdf_empty | NO              | BDF EMPTY-Loop (BL-075)  ║
║    | recheck| sdf_finish | NO             | SDF Post-finish (BL-078) ║
║    | recheck| idf_plan  | NO              | IDF Recheck (BL-076)     ║
║                                                                         ║
║  ═══ ABGRENZUNG ═══                                                    ║
║                                                                         ║
║    /_backlog          → Single-Writer fuer BL-Items (Vault-Datei)      ║
║    /_BL_orchestrate   → Lifecycle-Bewertung + Reifungs-Routing         ║
║    /_BDF_orchestrate  → Outer-Loop ueber alle Items (Dispatcher)       ║
║    /_A_orchestrate    → Wissensbasis-Bauer fuer UNREIF-Items           ║
║    /_IDF_orchestrate  → PL-Verwalterin + Batching                       ║
║                                                                         ║
║  ═══ VERWANDTE COMMANDS ═══                                            ║
║                                                                         ║
║    /_help             → Komplette Pipeline-Reise + 11 Geister-Tabelle  ║
║    /_backlog          → Single-Writer fuer BL-Item-Erstellung          ║
║    /_BDF_orchestrate  → Outer-Loop, ruft BL_orchestrate bei UNREIF     ║
║    /_A_orchestrate    → Wissensbasis-Bauer (von BL Phase 7 getriggert) ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Dann lies `{VAULT}/_manifest.md → BL_LIFECYCLE_STATE` und zeige aktuellen Lifecycle-Status.

ARGUMENTS: $ARGUMENTS
