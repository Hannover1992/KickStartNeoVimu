# Implementierungs-Pipeline - Hilfe & Uebersicht

Zeige die Uebersicht der Implementation Pipeline (/_I_*) Commands.

## Aufruf

```
/_I_help
```

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  IMPLEMENTIERUNGS-PIPELINE v4.0 (11 Commands)                          ║
║                                                                         ║
║  TDD-basiert, Vertical Slicing, FanOut/In fuer parallele Arbeit.       ║
║  Resume-faehig, Batch-Verarbeitung, inkrementelle Synthese-Dateien.    ║
║                                                                         ║
║  ═══ PIPELINE-KETTE ═══                                                ║
║                                                                         ║
║  /_I_cleanCodeArchitect {NAME} [easy|normal|hard]                      ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  PHASE 1: System-Dekomposition in vertikale Slices               │   ║
║  │  Actor: ARCHITEKT                                                │   ║
║  │  → Vertikale Slices (FE → BE → DB pro Feature-Teil)             │   ║
║  │  → Abhaengigkeiten-Graph + Architektur-Entscheidungen           │   ║
║  │  → Test-Pyramide + Slice-Reihenfolge                            │   ║
║  │  → SCHREIBT: ARCHITECT.md                                       │   ║
║  │  KEINE Code-Aenderungen, KEINE Tests                            │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_I_mitose {FEATURE_PREFIX} (optional, fuer parallele Arbeit)         ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  MITOSE: Git Worktrees + Feature-Branches erstellen              │   ║
║  │  Actor: MITOSE-ORCHESTRATOR (NUR Git-Operationen)               │   ║
║  │  → Wellen aus ARCHITECT.md Abhaengigkeiten ableiten             │   ║
║  │  → Pro Slice: eigener Worktree + Branch                         │   ║
║  │  → KEIN .claude/ kopieren (→ FanOut macht das)                  │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_I_fanOut (immer nach Mitose)                                        ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  FAN-OUT: .claude/ in Worktrees verteilen                        │   ║
║  │  Actor: MOTHERSHIP-OPERATOR                                      │   ║
║  │  → .claude/ in jeden Worktree kopieren                          │   ║
║  │  → CURRENT_SLICE.md pro Worktree setzen                         │   ║
║  │  → Mothership Manifest mit FanOut-Status updaten                │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_I_cleanCodeSlice {SLICE_NAME} (pro Worktree/Slice)                  ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  PHASE 2: Slice PLANEN (Test-Strategie, Pattern Reuse)           │   ║
║  │  Actor: SLICE-PLANER                                             │   ║
║  │  → Kent Beck Test-Liste (Tests VOR dem Code)                    │   ║
║  │  → Datei-Mapping (konkrete Pfade pro Layer)                     │   ║
║  │  → Horizontale Suche (Pattern-Reuse, 3-Farb-System)            │   ║
║  │  → SCHREIBT: plans/{SLICE}-PLAN.md                              │   ║
║  │  KEINE Code-Aenderungen, KEINE Tests                            │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_I_codeAtomic {SLICE_NAME}                                           ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  PHASE 3: Unit Tests + Production Code (Red-Green-Refactor)      │   ║
║  │  Actor: ATOMIC-CODER                                             │   ║
║  │  → Statist/Detroit TDD (echte Objekte, KEINE Mocks)            │   ║
║  │  → Batch 3-5 Tests pro Aufruf, Resume-faehig                   │   ║
║  │  → 30s RGR-Zyklen, Stagnation: 5+ ohne Fortschritt → Eskalation│   ║
║  │  → SCHREIBT: Unit Tests + Code + ATOMIC-{SLICE}.md              │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_I_codeIntegration {SLICE_NAME}                                      ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  PHASE 4: Integration Tests + Boundary Code (RGR)                │   ║
║  │  Actor: INTEGRATIONS-CODER                                       │   ║
║  │  → Machist/London TDD an Boundaries (API, DB, External)        │   ║
║  │  → Batch 2-3 Tests pro Aufruf, Resume-faehig                   │   ║
║  │  → NUR Wiring-Code (keine neue Business Logic)                  │   ║
║  │  → SCHREIBT: IT + Boundary Code + INTEGRATION-{SLICE}.md       │   ║
║  │  VORAUSSETZUNG: /_I_codeAtomic MUSS abgeschlossen sein          │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_I_codeSystem {SLICE_NAME}                                           ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  PHASE 5: System/E2E Tests (Red-Green-Refactor)                  │   ║
║  │  Actor: SYSTEM-TESTER                                            │   ║
║  │  → AK-Mapping: Akzeptanzkriterien → System-Tests                │   ║
║  │  → Batch 1-2 Tests pro Aufruf, Resume-faehig                   │   ║
║  │  → Slice-Abschluss-Erklaerung + Regressions-Check              │   ║
║  │  → SCHREIBT: E2E Tests + SYSTEM-{SLICE}.md                     │   ║
║  │  VORAUSSETZUNG: /_I_codeIntegration MUSS abgeschlossen sein     │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_I_verify {SLICE_NAME|global}                                        ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  VERIFY: SPEC ↔ Test Mapping                                     │   ║
║  │  Actor: VERIFIER                                                 │   ║
║  │  → Tests sind die Wahrheit, nicht der Code                      │   ║
║  │  → Stufe 1: Tests lesen (IMMER) — Stufe 2: Code (bei Unklarheit)│  ║
║  │  → Bidirektional: SPEC→Tests + Tests→SPEC                       │   ║
║  │  → Per Slice: nach codeSystem — Global: nach allen Slices       │   ║
║  │  → Komplementaer zu /_gap (GAP-Code + GAP-Test)                 │   ║
║  │  → SCHREIBT: VERIFY-{SLICE}.md oder VERIFY.md                  │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_I_fanIn {SLICE_NAME}                                                ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  FAN-IN: Worktree-Ergebnisse einsammeln + Merge begleiten        │   ║
║  │  Actor: MOTHERSHIP-OPERATOR                                      │   ║
║  │  → Phase 1: .claude/ Artefakte Worktree → Mothership            │   ║
║  │  → Phase 2: User macht git merge (Advisory)                     │   ║
║  │  → Phase 3: Build + Tests validieren (gestuft)                  │   ║
║  │  → Phase 4: Manifest + ARCHITECT updaten                        │   ║
║  │  → Phase 5: Entblockte Slices → Neue Welle (Mitose + FanOut)   │   ║
║  │  KEIN Git! User merged selbst. FanIn BERAET + VALIDIERT.        │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_I_diffAudit                                                         ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  DIFF-AUDIT: Gesamten Feature-Diff gegen develop auditieren      │   ║
║  │  Actor: DIFF-AUDITOR (read-only bis User OK)                    │   ║
║  │  → Rueckwaerts-Audit: Jede Aenderung rechtfertigen              │   ║
║  │  → SPUR-1..7: Explorations-Reste erkennen                       │   ║
║  │  → Opus→Sonnet→Opus Sandwich (3 Wellen)                        │   ║
║  │  → SCHREIBT: DIFFAUDIT.md (Cleanup-Liste)                      │   ║
║  │  VORAUSSETZUNG: /_gap abgeschlossen                              │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                          │                                              ║
║                          ▼                                              ║
║  /_I_orchestrate {FEATURE} [easy|normal|hard] [sonnet|opus]           ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  ORCHESTRATOR: Vollstaendige I-Pipeline orchestrieren            │   ║
║  │  Actor: TEAM LEAD (spawnt Pro-Worktree-Agents)                  │   ║
║  │  → Multi-Worktree-Management (Mitose/FanOut/FanIn)              │   ║
║  │  → Pro-Worktree-Agents via Agent Teams API                      │   ║
║  │  → Human-in-the-Loop 2× (Commits + Test-Suite)                  │   ║
║  │  → Wellen-Iteration (Welle 1 → fanIn → Welle 2+)               │   ║
║  │  → Hybrid aus SC_orchestrate + WP_orchestrate                   │   ║
║  │  → SCHREIBT: _manifest.md, spawnt Agents, koordiniert Tasks     │   ║
║  │  ALTERNATIVE: Manuell Command-fuer-Command                       │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  GESAMTE PIPELINE-KETTE:                                               ║
║                                                                         ║
║  /_taskDefinition → /_spec → /_model → /_gap                          ║
║    → /_I_cleanCodeArchitect                                            ║
║    → [/_I_mitose] → [/_I_fanOut]                                       ║
║    → /_I_cleanCodeSlice                                                ║
║    → /_I_codeAtomic → /_I_codeIntegration → /_I_codeSystem            ║
║    → /_I_verify (per Slice)                                            ║
║    → [/_I_fanIn]                                                       ║
║    → (Welle 2 oder Feature KOMPLETT)                                   ║
║    → /_I_verify global → /_model finish → /_gap                       ║
║    → /_I_diffAudit → /_Pre_PR                                         ║
║    → /_W_push_orchestrate (Post-Pipeline Wissens-Push)                 ║
║    → /_finish (Feature-Abschluss: Parking-Lot, Konsistenz, READY)      ║
║    → PR                                                                 ║
║                                                                         ║
║  WISSENS-KOALESZENZ (Post-Pipeline):                                   ║
║  Die I-Pipeline KONSUMIERT Wissen (aus Model/Spec) und PRODUZIERT Code.║
║  W_push_temp/W_push_global sind nicht relevant (Code != Wissens-Dok.). ║
║  POST-PIPELINE nutzt:                                                  ║
║    /_W_modelSplit    Model → thematische Teile (Vault)                 ║
║    /_W_obsidianSync  Synthese-Dokumente in Obsidian Vault              ║
║                                                                         ║
║  SLICE-ITERATION:                                                      ║
║    Welle 1: Unabhaengige Slices parallel (Mitose + FanOut)            ║
║    Pro Worktree: Phase 2→3→4→5→Verify durchlaufen                    ║
║    FanIn: Worktree fertig → Merge → entblockte Slices                ║
║    Welle 2+: Abhaengige Slices (nach FanIn von Welle 1)              ║
║                                                                         ║
║  ESKALATION:                                                           ║
║    Pipeline → /_gap (Re-Eval) → GAP wachsend?                        ║
║      → JA: /_SC_observe → /_SC_modelMaintain → zurueck               ║
║      → NEIN: Weiter mit naechstem Slice                               ║
║                                                                         ║
║  MODEL-BLOAT (Debloat-Hook v2.1, nach codeSystem-Stufe):              ║
║    Falls Model >500 Zeilen → /_D_orchestrate {FEATURE} empfohlen     ║
║    Detail: /_D_help (Debloat-System: SOFT/HARD-Trigger, 4 Commands)  ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Dann lies `.claude/analysis/_manifest.md` falls vorhanden und zeige den aktuellen Pipeline-Stand.

ARGUMENTS: $ARGUMENTS
