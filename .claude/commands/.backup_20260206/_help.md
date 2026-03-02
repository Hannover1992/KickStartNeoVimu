# Forschungszyklus - Hilfe & Uebersicht

Zeige die Uebersicht des wissenschaftlichen Forschungszyklus.

## Aufruf

```
/_help
```

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  ZWEI PARALLELE WELTEN: Forschung (v2.2) + Pipeline (v3.0)            ║
║                                                                         ║
║  ═══ WISSENSCHAFTLICHER FORSCHUNGSZYKLUS (v2.2) ═══                    ║
║                                                                         ║
║  Pre-Cycle:  /_taskDefinition  /_spec (optional, Ziel-Architektur)      ║
║  Init:       /_model                                                    ║
║  Zyklus:     /_SC_observe  /_SC_modelMaintain  /_SC_qualityGate         ║
║              /_SC_hypothese  /_SC_implement  /_SC_ergebnis              ║
║  Detektion:  /_SC_architecturalBoundaries  /_SC_blindspotDetection      ║
║  Parallel:   /_knowledge (Deep-Dive Wissens-Recherche)                  ║
║  Parking:    _parking-lot.md (Incidental Findings Queue)                ║
║  Meta:       /_scientific (Full Cycle)  /_presentation (Output)         ║
║  Sync:       /_obsidianSync (Synthese → Obsidian Vault)                ║
║  Referenz:   /_obsidianHelp (Tag-Taxonomie, Graph-Farben, Setup)       ║
║  Hilfe:      /_help (diese Uebersicht)                                  ║
║                                                                         ║
║  ═══ IMPLEMENTIERUNGS-PIPELINE v3.0 (TDD, Vertical Slicing) ═══       ║
║                                                                         ║
║  Pre:        /_taskDefinition  /_spec  /_model (shared mit wiss. Zykl.)║
║  Phase 1:    /_I_cleanCodeArchitect (Slices + Architektur)             ║
║  Phase 2:    /_I_cleanCodeSlice (Kent Beck Test-Liste pro Slice)       ║
║  Phase 3:    /_I_codeAtomic (Unit Tests + Code, Statist TDD)          ║
║  Phase 4:    /_I_codeIntegration (IT + Wiring, Machist TDD)           ║
║  Phase 5:    /_I_codeSystem (E2E + AK-Mapping, Slice-Abschluss)       ║
║  MCP:        Uncle Bob Clean Code (jede Phase)                         ║
║  Topologie:  DATAFLOW_Pipeline-v3.0.md                                 ║                                  ║
║                                                                         ║
║  WICHTIG v2.2: _analyse wurde durch 3 Commands ersetzt (SRP):          ║
║    - /_SC_observe: Findings sammeln (Actor: OBSERVER)                   ║
║    - /_SC_modelMaintain: Model pflegen, GC, Split (Actor: MODEL-MAINT.)║
║    - /_SC_qualityGate: Quality Gates prüfen (Actor: QUALITY-GATE)      ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  PRE-CYCLE (Aufgabe & Kruemmel):                                        ║
║                                                                         ║
║    .claude/pileOfMud/          .claude/Task.md                          ║
║    ├── *.pdf                   (Frage, Scope,                           ║
║    ├── *.png (Screenshots)      Erfolgskriterien)                       ║
║    ├── *.md  (alte Models)          │                                    ║
║    └── ...                          │                                    ║
║         │                           │                                    ║
║         └─────────┬─────────────────┘                                   ║
║                   ▼                                                     ║
║         /_taskDefinition {NAME}                                         ║
║         ┌──────────────────────────────────────────────────┐            ║
║         │  Drafts-Welle: pileOfMud/* lesen + extrahieren    │            ║
║         │  Synthese:     Kruemmel synthetisieren           │            ║
║         │                                                  │            ║
║         │  Screenshots ──▶ Mermaid-Diagramme               │            ║
║         │  PDFs        ──▶ Strukturierte Sektionen          │            ║
║         │  Alte Models ──▶ Wissens-Kruemmel                 │            ║
║         └──────────────────────────────────────────────────┘            ║
║                   │                                                     ║
║                   ▼                                                     ║
║         .claude/crumbs/{NAME}_crumbs.md                                 ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  INIT (Model aufbauen):                                                 ║
║                                                                         ║
║    /_model {NAME} hard                                                  ║
║    ┌──────────────────────────────────────────────────────────────────┐  ║
║    │  LIEST: crumbs/{NAME}_crumbs.md + models/{NAME}_Model.md (alt)  │  ║
║    │                                                                  │  ║
║    │  Welle 1: Exploration (5-10x) ──SCHREIBT──▶ exploration/...     │  ║
║    │  Welle 2: Drafts (3-5x) ──LIEST exploration/ ──SCHREIBT──▶     │  ║
║    │                                     drafts/{NAME}-model-D*.md   │  ║
║    │  Welle 3: Synthese (DU) ──LIEST drafts/ ──SCHREIBT──▶          │  ║
║    │                                     models/{NAME}_Model.md      │  ║
║    │                                                                  │  ║
║    │  *** Nach JEDER Welle: /compact moeglich ***                    │  ║
║    └──────────────────────────────────────────────────────────────────┘  ║
║                            │                                            ║
║                            ▼                                            ║
║  ITERATIVER ZYKLUS (v2.2+ - SRP-konform):                               ║
║                                                                         ║
║  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ ║
║  │/_SC_    │─▶│/_SC_model│─▶│/_SC_     │─▶│/_SC_     │─▶│/_SC_     │─▶│/_SC_     │ ║
║  │observe  │  │Maintain  │  │quality   │  │hypothese │  │implement │  │ergebnis  │ ║
║  │ LIEST:  │  │          │  │Gate      │  │Sek.0: GC │  │1 IC/atom │  │DB-MODUS  │ ║
║  │  MODEL  │  │ LIEST:   │  │ LIEST:   │  │Sek.1: Hyp│  │+Horiz.   │  │          │ ║
║  │  ERGEBNIS  │  MODEL   │  │  MODEL   │  │          │  │          │  │ LIEST:   │ ║
║  │         │  │  OBSERVE │  │  OBSERVE │  │ LIEST:   │  │ LIEST:   │  │ HYPOTHESEN║
║  │SCHREIBT:│  │  ERGEBNIS│  │  ERGEBNIS│  │  MODEL   │  │ HYPOTHESEN  │  MODEL(DB)║
║  │ OBSERVE │  │          │  │  TOPOL.  │  │  QUALITY │  │  MODEL   │  │ vorh.ERG.║
║  │(Findings│  │SCHREIBT: │  │          │  │  GATE    │  │+PatternLib  │          │ ║
║  │nur!)    │  │ MODEL upd│  │SCHREIBT: │  │          │  │+BOUNDARIES  │SCHREIBT: ║
║  │         │  │ +W{n}    │  │ QUALITY  │  │SCHREIBT: │  │          │  │ ERGEBNIS ║
║  │OPTIONAL:│  │ +GC      │  │ GATE     │  │ HYPOTHESEN  │SCHREIBT: │  │+SRS-Score║
║  │_parking │  │ +Split   │  │ +BR-Bew. │  │ +GC-Liste│  │ Code +   │  │+Widerl.  │
║  │-lot.md  │  │ +Kap.6a  │  │ +Kohaesion  │ +Verif.  │  │ HYPOTHESEN  │+Stagn.   ║
║  │(incid.  │  │          │  │ +Feature │  │ +Scope   │  │+Horiz.Such  │          │ ║
║  │findings)│  │OPTIONAL: │  │ Abschluss│  │          │  │+Verifik. │  │OPTIONAL: ║
║  │         │  │_parking  │  │ +BSD-Tri.│  │          │  │          │  │_parking  │
║  │         │  │-lot.md   │  │          │  │          │  │          │  │-lot.md   │
║  └─────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────┘ ║
║                                                                         ║
║          ▲                                                    │         ║
║          └────────────────────────────────────────────────────┘         ║
║  (SRS + Rohdaten → _SC_observe/modelMaintain/qualityGate → neuer Zyklus) ║
║                                                                         ║
║    OPTIONAL (von _SC_qualityGate getriggert):                           ║
║      /_SC_architecturalBoundaries  (einmalig, TP-Zerlegung + Vert.Suche) ║
║      /_SC_blindspotDetection       (bei Muster T1-T5, Canary Probes)  ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║            IMPLEMENTIERUNGS-PIPELINE v3.0 (parallel)                   ║
║                                                                         ║
║  ZWEI PARALLELE WELTEN:                                                ║
║  - Wiss. Zyklus v2.2: Schwer, analytisch (oben)                       ║
║  - Impl. Pipeline v3.0: Schnell, TDD-basiert (unten)                  ║
║                                                                         ║
║  PIPELINE-KETTE (5 Phasen + 2 Pre-Steps):                             ║
║                                                                         ║
║  /_taskDefinition → /_spec → /_model → /_gap → /_I_cleanCodeArchitect  ║
║       → /_I_cleanCodeSlice → /_I_codeAtomic                            ║
║       → /_I_codeIntegration → /_I_codeSystem                           ║
║                                                                         ║
║  PRE-PIPELINE (shared mit wiss. Zyklus):                               ║
║    /_taskDefinition  Task.md + Crumbs erstellen                        ║
║    /_model            Model.md aufbauen                                 ║
║    /_gap              Gap-Analyse: Delta IST↔SOLL (Circuit Breaker)    ║
║                                                                         ║
║  PHASE 1: /_I_cleanCodeArchitect {NAME} [easy|normal|hard]             ║
║    ┌──────────────────────────────────────────────────────────────────┐ ║
║    │  ACTOR: ARCHITEKT                                                │ ║
║    │  LIEST: Task.md, Model.md, BOUNDARIES.md (optional), MCP        │ ║
║    │  SCHREIBT: synthese/{NAME}-ARCHITECT.md                          │ ║
║    │                                                                  │ ║
║    │  → Vertikale Slices (FE → BE → DB pro Feature-Teil)             │ ║
║    │  → Abhaengigkeiten-Graph                                         │ ║
║    │  → Architektur-Entscheidungen (DIP, Patterns)                   │ ║
║    │  → Test-Pyramide + Slice-Reihenfolge                            │ ║
║    │  → Uncle Bob MCP: architecture, vertical slicing, DIP           │ ║
║    │  KEINE Code-Aenderungen, KEINE Tests                            │ ║
║    └──────────────────────────────────────────────────────────────────┘ ║
║                            │                                            ║
║                            ▼                                            ║
║  PHASE 2: /_I_cleanCodeSlice {SLICE_NAME}                              ║
║    ┌──────────────────────────────────────────────────────────────────┐ ║
║    │  ACTOR: SLICE-PLANER                                             │ ║
║    │  LIEST: ARCHITECT.md, Model.md, Pattern-Library, MCP            │ ║
║    │  SCHREIBT: plans/{NAME}-{SLICE}-PLAN.md                         │ ║
║    │                                                                  │ ║
║    │  → Kent Beck Test-Liste (Tests VOR dem Code)                    │ ║
║    │  → Datei-Mapping (konkrete Pfade pro Layer)                     │ ║
║    │  → Horizontale Suche (Pattern-Reuse)                            │ ║
║    │  → DIP-Boundaries + Schnittstellen-Vertrag                      │ ║
║    │  KEINE Code-Aenderungen, KEINE Tests                            │ ║
║    └──────────────────────────────────────────────────────────────────┘ ║
║                            │                                            ║
║                            ▼                                            ║
║  PHASE 3: /_I_codeAtomic {SLICE_NAME}                                 ║
║    ┌──────────────────────────────────────────────────────────────────┐ ║
║    │  ACTOR: ATOMIC-CODER (Red-Green-Refactor, 30s Zyklen)          │ ║
║    │  LIEST: PLAN.md, Model.md, Pattern-Library, MCP                 │ ║
║    │  SCHREIBT: Unit Tests + Production Code +                       │ ║
║    │            synthese/{NAME}-ATOMIC-{SLICE}.md                    │ ║
║    │                                                                  │ ║
║    │  → Statist/Detroit TDD (echte Objekte, KEINE Mocks)            │ ║
║    │  → 1 Test rot → minimal gruen → Refactor                       │ ║
║    │  → Stagnation: 5+ RGR ohne Fortschritt → Eskalation            │ ║
║    └──────────────────────────────────────────────────────────────────┘ ║
║                            │                                            ║
║                            ▼                                            ║
║  PHASE 4: /_I_codeIntegration {SLICE_NAME}                             ║
║    ┌──────────────────────────────────────────────────────────────────┐ ║
║    │  ACTOR: INTEGRATIONS-CODER (RGR an DIP-Boundaries)             │ ║
║    │  LIEST: PLAN.md, ATOMIC.md, Pattern-Library, MCP                │ ║
║    │  SCHREIBT: Integration Tests + Boundary Code +                  │ ║
║    │            synthese/{NAME}-INTEGRATION-{SLICE}.md               │ ║
║    │                                                                  │ ║
║    │  → Machist/London TDD an Boundaries (API, DB, External)        │ ║
║    │  → NUR Wiring-Code (keine neue Business Logic)                  │ ║
║    │  → Regressions-Check: Unit Tests duerfen NICHT brechen          │ ║
║    │  VORAUSSETZUNG: /_I_codeAtomic MUSS abgeschlossen sein          │ ║
║    └──────────────────────────────────────────────────────────────────┘ ║
║                            │                                            ║
║                            ▼                                            ║
║  PHASE 5: /_I_codeSystem {SLICE_NAME}                                 ║
║    ┌──────────────────────────────────────────────────────────────────┐ ║
║    │  ACTOR: SYSTEM-TESTER (RGR durch stabile Interfaces)           │ ║
║    │  LIEST: PLAN.md, INTEGRATION.md, Task.md (AK), MCP             │ ║
║    │  SCHREIBT: E2E Tests + System Config +                          │ ║
║    │            synthese/{NAME}-SYSTEM-{SLICE}.md                    │ ║
║    │                                                                  │ ║
║    │  → AK-Mapping: Akzeptanzkriterien → System-Tests                │ ║
║    │  → Test Through Stable Interface (data-testid, Page Objects)    │ ║
║    │  → Slice-Abschluss-Erklaerung + Regressions-Check              │ ║
║    │  VORAUSSETZUNG: /_I_codeIntegration MUSS abgeschlossen sein     │ ║
║    └──────────────────────────────────────────────────────────────────┘ ║
║                            │                                            ║
║                            ▼                                            ║
║            [SLICE ABGESCHLOSSEN → naechster Slice]                    ║
║                                                                         ║
║  SLICE-ITERATION:                                                      ║
║    ARCHITECT.md definiert N Slices mit Reihenfolge                    ║
║    Fuer JEDEN Slice: Phase 2→3→4→5 durchlaufen                       ║
║    Canary-First: Einfachster Slice zuerst                             ║
║    Re-Eval: /_gap easy nach jedem Slice (Delta-Trend pruefen)          ║
║                                                                         ║
║  ESKALATION bei Stagnation:                                            ║
║    Pipeline → /_gap (Re-Eval) → GAP wachsend?                         ║
║      → JA: /_SC_observe → /_SC_modelMaintain → zurueck in Pipeline   ║
║      → NEIN: Weiter mit naechstem Slice                               ║
║                                                                         ║
║  MCP INTEGRATION (Uncle Bob Clean Code):                               ║
║    mcp__cleancoder__query() in JEDER Phase                             ║
║    Architecture, TDD, Boundaries, Test Strategy, Refactoring           ║
║                                                                         ║
║  SHARED ARTIFACTS:                                                     ║
║    PLAN.md: Geschrieben von Phase 2, gelesen von Phase 3-5            ║
║    Task.md + Model.md: Persistent ueber gesamte Pipeline              ║
║    _pattern-library.md: Gelesen ab Phase 2, aktualisiert in Phase 3  ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  MECHANISMEN (v2.0+, Model Kap. 2):                                    ║
║                                                                         ║
║  1. Battle-Royale (BR): Suchraum progressiv verkleinern                ║
║     Metrik: SRS = (D1*3) + (D2*1) + (D3*0.5) + (D4*5)                ║
║     D1=Offene Bereiche  D2=Aktive W{n}  D3=Dateien  D4=TCs            ║
║     _SC_ergebnis MISST (Rohdaten), _SC_observe BEWERTET (Interpretation) ║
║     Anti-Patterns: R-AP1..R-AP5 (Wachstum/Stagnation/Explosion)       ║
║                                                                         ║
║  2. Model-Split: Monolith → Teilmodelle (1 TC pro Teilmodel)          ║
║     Trigger: >15 W{n}/TC ODER >30 gesamt ODER R-AP4                   ║
║     Ausfuehrung: _SC_modelMaintain Sek.B (Schritt 9a, IN-LOOP)       ║
║     Model-Topologie: Fokus/Status/Pfad/Abhaengigkeiten                 ║
║     Regeln VM-1..VM-6 (u.a. NUR 1 Fokus-Teilmodel gleichzeitig)      ║
║     Cross-Cutting-Schutz: Min. 1 Drafter liest ALLE Teilmodelle      ║
║                                                                         ║
║  3. Garbage Collection (GC): W{n} markieren + archivieren              ║
║     WIDERLEGT (faktisch falsch) ──▶ permanent                          ║
║     ELIMINIERT (strategisch) ──▶ kann re-aktiviert werden              ║
║     Rangfolge: WIDERLEGT > ELIMINIERT > AKTIV                          ║
║     _SC_hypothese Sek.0 = PFLICHT ab Cycle 2                           ║
║     _SC_modelMaintain Sek.B archiviert markierte W{n} im Model        ║
║                                                                         ║
║  4. Blind-Spot-Detection (BSD): Fokus-Korrektheit pruefen             ║
║     Trigger T1-T5 (von _SC_qualityGate empfohlen)                      ║
║     Canary Probes: max 7, min 1 AUSSERHALB aktueller Fokus            ║
║     Epistemologische Grenze → Mensch-in-the-Loop PFLICHT               ║
║                                                                         ║
║  5. Stagnations-ABORT: Endlos-Loops verhindern                         ║
║     Fortschritt: STARK(Reset) / SCHWACH(+0.5) / KEINER(+1.0)          ║
║     Schwellen: >=3.0 WARNUNG, >=5.0 PFLICHT, >=7.0 ABORT              ║
║     ABORT = Ansatz stoppen + Meta-Analyse, NICHT aufgeben              ║
║                                                                         ║
║  6. Vertikale Suche (v2.2, ALT-System Phase 2.1):                      ║
║     Abstrakte TP-Namen → konkrete Dateipfade (File Matcher)            ║
║     Integriert in: /_SC_architecturalBoundaries (Sektionen 6+7)       ║
║     Methode: Glob-Pattern + Grep-Verifikation + Kontext-Expansion     ║
║     Layer-Mapping: FE-COMP, BE-SVC, BE-CTRL, etc.                     ║
║     Kategorien: NEW / MODIFY / EXTEND pro Teilproblem                  ║
║                                                                         ║
║  7. Horizontale Suche (v2.2, ALT-System Phase 2.2):                    ║
║     Finde aehnliche Impl. INNERHALB gleicher Schicht (Pattern Search)  ║
║     Integriert in: /_SC_implement (Schritt 1.5)                        ║
║     Layer-Constraint: NUR im gleichen Layer suchen                     ║
║     Reuse-Score: 0-1 pro Kandidat                                      ║
║     3-Farb-System: GRAY(>0.8) / ORANGE(0.5-0.8) / RED(<0.5)          ║
║     Pattern-Library: .claude/patterns/_pattern-library.md              ║
║                                                                         ║
║  Eskalations-Hierarchie (Kap. 2.7):                                    ║
║    P1 ABORT > P2 Re-Expansion > P3 BR > P4 Split > P5 BSD             ║
║    GC = Hygiene (keine Eskalation, laeuft IMMER ab Cycle 2)           ║
║    IR-1..IR-10: Zaehler-Resets, BSD-Neutralitaet, Override-Transp.    ║
║                                                                         ║
║  Erweiterungs-Taxonomie (Kap. 3 Intro):                                ║
║    OPT   = Optional, graceful-degraded                                 ║
║    PC2   = Pflicht ab Cycle 2 (Cycle 1 unveraendert)                   ║
║    VERSCH = Verschaerfung (bewusst enger)                              ║
║  Override-Stufen:                                                       ║
║    SO = Soft-Override (auto-Notiz im Manifest)                         ║
║    HO = Hard-Override (Begruendung PFLICHT)                            ║
║    NU = Nicht uebersteuerbar (Reserve, aktuell kein Element)           ║
║  Override-Registry: 49 Elemente (11 OPT, 23 PC2, 15 VERSCH),          ║
║    davon 17 HO-kritisch (Model Anhang A)                               ║
║                                                                         ║
║  Drei-Kategorien-Regel (_SC_ergebnis, Kap. 3.4):                       ║
║    ROHDATEN: Sammeln, zaehlen, woertlich zitieren                      ║
║    MECHANISCHE ABLEITUNG: Formeln, Zaehler, boolesche Ausdruecke      ║
║    INTERPRETATION: VERBOTEN (gehoert in _SC_observe)                   ║
║    Test: "Koennen 2 Ausfuehrer verschiedene Ergebnisse bekommen?"      ║
║          JA → VERBOTEN fuer _SC_ergebnis. NEIN → erlaubt.              ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  PARALLEL (Wissens-Deep-Dive, blockiert NICHT den Hauptzyklus):         ║
║                                                                         ║
║    /_knowledge {THEMA} [easy|normal|hard]                               ║
║    ┌──────────────────────────────────────────────────────────────────┐  ║
║    │  LIEST: models/{NAME}_Model.md (Kontext)                        │  ║
║    │                                                                  │  ║
║    │  Welle 1: Exploration (max 10)                                  │  ║
║    │    E01-E03: Kartographie (Codebase + Model nach Thema scannen)  │  ║
║    │    E04-E07: Quellensammlung (WebSearch: RFCs, Docs, Papers)     │  ║
║    │    E08-E10: Dokumentation (Bibliographie + Inhaltssicherung)    │  ║
║    │    ──SCHREIBT──▶ wissen/{THEMA}/exploration/ + quellen/         │  ║
║    │                                                                  │  ║
║    │  Welle 2: Drafts (max 5) - FEYNMAN-ENTWUERFE                   │  ║
║    │    D01: Kern-Mechanismus (Konzeptzerlegung)                     │  ║
║    │    D02: Analogie-Bruecke (Structural Mapping)                   │  ║
║    │    D03: Visuell-Narrativ (Mermaid + Story)                      │  ║
║    │    D04: Fehler-Grenzen (Edge Cases, Missverstaendnisse)         │  ║
║    │    D05: Unser-System (Praxis-Bezug)                             │  ║
║    │    ──SCHREIBT──▶ wissen/{THEMA}/drafts/entwurf_*.md             │  ║
║    │                                                                  │  ║
║    │  Welle 3: Synthese (DU) - SYNTHESE                             │  ║
║    │    ──SCHREIBT──▶ wissen/{THEMA}_Wissen.md (~25 Seiten)          │  ║
║    │                                                                  │  ║
║    │  *** Feynman-Methode: 5-Stufen-Erklaerungssystem ***            │  ║
║    │  *** Nach JEDER Welle: /compact moeglich ***                    │  ║
║    └──────────────────────────────────────────────────────────────────┘  ║
║                                                                         ║
║    Ergebnis kann von _SC_observe, _SC_hypothese, _SC_ergebnis gelesen werden. ║
║    SCOPE-GUARD (W14): Bei aktivem BR nur im Fokus-Teilproblem.         ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  DATEISYSTEM-VERTRAG:                                                   ║
║                                                                         ║
║  .claude/                                                               ║
║  ├── Task.md                        ◄── Aufgaben-Definition             ║
║  ├── pileOfMud/                     ◄── Rohmaterial (PDFs, Screenshots) ║
║  ├── crumbs/                        ◄── Strukturierte Kruemmel          ║
║  │   └── {NAME}_crumbs.md                                              ║
║  ├── specs/                         ◄── NEU v3.0: Ziel-Architektur     ║
║  │   └── {NAME}_Spec.md            ◄── SOLL-Zustand (optional)        ║
║  ├── models/                        ◄── Persistente Models              ║
║  │   ├── {NAME}_Model.md           ◄── Single Source of Truth           ║
║  │   └── {NAME}_Model-Topologie.md ◄── Bei Model-Split (Kap. 2.2)     ║
║  ├── patterns/                     ◄── NEU v2.2: Pattern Library        ║
║  │   └── _pattern-library.md       ◄── Wiederverwendbare Code-Patterns ║
║  │       (Layer-Defs, Reuse-Scores, 3-Farb-System)                     ║
║  ├── analysis/                                                          ║
║  │   ├── _manifest.md              ◄── ZUSTANDSTRACKER                  ║
║  │   ├── exploration/              ◄── Welle 1: Kartografie             ║
║  │   │   └── {NAME}-E{NN}-{fokus}.md                                   ║
║  │   ├── drafts/                   ◄── Welle 2: Deep Analysis           ║
║  │   │   └── {NAME}-{PHASE}-D{NN}-{fokus}.md                           ║
║  │   └── synthese/                 ◄── Welle 3: Synthese               ║
║  │       ├── {NAME}-OBSERVE{CYCLE}.md      ◄── NEU v2.2: Findings      ║
║  │       ├── {NAME}-QUALITYGATE{CYCLE}.md  ◄── NEU v2.2: Quality Gates ║
║  │       ├── {NAME}-GAP.md                ◄── NEU v3.0: IST↔SOLL Delta║
║  │       ├── {NAME}-ANALYSE{CYCLE}.md      ◄── LEGACY <v2.2            ║
║  │       ├── {NAME}-HYPOTHESEN.md                                       ║
║  │       ├── {NAME}-ERGEBNIS{CYCLE}.md ◄── Rohdaten + SRS              ║
║  │       ├── {NAME}-BLINDSPOT{N}.md    ◄── BSD (optional)              ║
║  │       ├── {NAME}-BOUNDARIES.md      ◄── Arch.Bound. (optional)     ║
║  │       ├── {NAME}-ARCHITECT.md       ◄── Pipeline: Slices+Archit.   ║
║  │       ├── {NAME}-ATOMIC-{SLICE}.md  ◄── Pipeline: Unit-Test-Report ║
║  │       ├── {NAME}-INTEGRATION-{SLICE}.md ◄── Pipeline: IT-Report    ║
║  │       └── {NAME}-SYSTEM-{SLICE}.md  ◄── Pipeline: E2E-Report       ║
║  │   └── plans/                        ◄── Pipeline: Slice-Plaene     ║
║  │       └── {NAME}-{SLICE}-PLAN.md   ◄── Kent Beck Test-Liste        ║
║  ├── _parking-lot.md               ◄── NEU v2.2: Incidental Findings   ║
║  ├── wissen/                       ◄── Knowledge Deep-Dives            ║
║  │   ├── {THEMA}/                  ◄── Pro Thema ein Ordner            ║
║  │   │   ├── exploration/          ◄── Kartographie + Quellen           ║
║  │   │   ├── drafts/              ◄── Feynman-Entwuerfe                ║
║  │   │   └── quellen/             ◄── Bibliographie + Inhalte          ║
║  │   └── {THEMA}_Wissen.md        ◄── Finales Wissensdokument          ║
║  └── presentation/                                                      ║
║      └── {TICKET}-{TYPE}.md                                             ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  KOMPLETTE LESE-KETTE:                                                  ║
║                                                                         ║
║  pileOfMud/* ─────────────────────────────────────┐                     ║
║  Task.md ──────────────────────────────────┐      │                     ║
║                                            ▼      ▼                     ║
║  _taskDefinition ── schreibt ──▶ crumbs/{NAME}_crumbs.md               ║
║  _spec           ── liest crumbs + Task.md (optional, Ziel-Architektur)║
║                     ── schreibt ──▶ specs/{NAME}_Spec.md (SOLL)       ║
║                     (Actor: SPEZIFIKATEUR - extrahiert, erfindet NICHT)║
║                                                                         ║
║  _model          ── liest crumbs + SPEC ── schreibt ──▶ models/{NAME}_Model.md║
║                                                                         ║
║  _gap             ── liest SPEC + MODEL + Codebase                     ║
║                     ── schreibt ──▶ synthese/{NAME}-GAP.md (Delta)    ║
║                     (Actor: ANALYST - vergleicht IST↔SOLL, erfindet NICHT)║
║                     (Circuit Breaker: GAP% > 80% → Pipeline STOP)      ║
║                     (Re-Eval: Nach jedem Slice, GAP MUSS schrumpfen)   ║
║                                                                         ║
║  _SC_observe     ── liest MODEL + ERGEBNIS (inkl. BR-Score)            ║
║                     ── schreibt ──▶ OBSERVE (nur Findings!)            ║
║                     + OPTIONAL ──▶ _parking-lot.md (Incidental Tasks)  ║
║                     (Actor: OBSERVER - sammelt, interpretiert NICHT)   ║
║                                                                         ║
║  _SC_modelMaintain ── liest MODEL + OBSERVE + ERGEBNIS                 ║
║                     ── updated ──▶ MODEL (W{n}, GC, Kap.6a)           ║
║                     + bei PFLICHT: Model-Topologie + Teilmodelle       ║
║                     + OPTIONAL ──▶ _parking-lot.md                     ║
║                     (Actor: MODEL-MAINTAINER - pflegt Model)           ║
║                                                                         ║
║  _SC_qualityGate ── liest MODEL + OBSERVE + ERGEBNIS + TOPOLOGIE      ║
║                     ── schreibt ──▶ QUALITYGATE                        ║
║                     (BR-Bewertung, Kohaesion, Feature-Abschluss, BSD)  ║
║                     + OPTIONAL ──▶ _parking-lot.md                     ║
║                     (Actor: QUALITY-GATE - prueft Gates)               ║
║                                                                         ║
║  _SC_hypothese   ── liest MODEL + QUALITYGATE                           ║
║                     ── schreibt ──▶ HYPOTHESEN                          ║
║                     (Sek.0: GC-Pruefung, PFLICHT ab Cycle 2)           ║
║                     (Sek.1: Hypothese + Verif.V1-V5 + Scope-Dekl.)    ║
║                                                                         ║
║  _SC_archBoundaries ── liest MODEL + OBSERVE + Pattern-Library         ║
║                     ── schreibt ──▶ BOUNDARIES (Sek.1-5 + Sek.6-7)   ║
║                     (NEU v2.2: Vertikale Suche = Datei-Mapping)        ║
║                     (Glob + Grep → abstrakt → konkrete Dateipfade)     ║
║                                                                         ║
║  _SC_implement   ── liest HYPOTHESEN + MODEL + Pattern-Library         ║
║                     + BOUNDARIES (optional: Datei-Mapping)              ║
║                     ── schreibt ──▶ Code + HYPOTHESEN (aktualisiert)   ║
║                     (1 IC/Durchgang, Soft-Limits 5 Dateien / 100 LOC)  ║
║                     (NEU v2.2: Horizontale Suche = Pattern-Matching)    ║
║                     (Layer-Constraint, 3-Farb-System, Blueprint)       ║
║                     (Verifikations-Anleitung: 3-5 Schritte PFLICHT)    ║
║                                                                         ║
║  _SC_ergebnis    ── liest HYPOTHESEN + MODEL (DATENBANK-MODUS)         ║
║                     + vorheriges ERGEBNIS + Logs/Tests                  ║
║                     ── schreibt ──▶ ERGEBNIS                            ║
║                     (Drei-Kategorien: Rohdaten + Mech. Ableitung)      ║
║                     (NEU: SRS-Messung, Widerl.-Marker, Stagn.-Check)   ║
║                     (KEINE Interpretation, KEIN Model-Update)           ║
║                                                                         ║
║  IMPLEMENTIERUNGS-PIPELINE (parallel zum wiss. Zyklus):               ║
║                                                                         ║
║  _I_cleanCodeArchitect ── liest GAP + SPEC + MODEL + Task.md + BOUND. ║
║                          ── schreibt ──▶ ARCHITECT.md (Slices)        ║
║                          + MCP Uncle Bob Queries                       ║
║                                                                         ║
║  _I_cleanCodeSlice   ── liest ARCHITECT.md + MODEL + PatternLib       ║
║                          ── schreibt ──▶ plans/{SLICE}-PLAN.md        ║
║                          (Kent Beck Test-Liste + Datei-Mapping)        ║
║                                                                         ║
║  _I_codeAtomic       ── liest PLAN.md + MODEL + PatternLib             ║
║                          ── schreibt ──▶ Unit Tests + Code +          ║
║                             ATOMIC-{SLICE}.md                          ║
║                          (Statist TDD, 30s RGR-Zyklen)                ║
║                                                                         ║
║  _I_codeIntegration  ── liest PLAN.md + ATOMIC.md + PatternLib         ║
║                          ── schreibt ──▶ Integration Tests +          ║
║                             INTEGRATION-{SLICE}.md                     ║
║                          (Machist TDD an DIP-Boundaries)               ║
║                          VORAUSSETZUNG: /_I_codeAtomic abgeschlossen  ║
║                                                                         ║
║  _I_codeSystem       ── liest PLAN.md + INTEGRATION.md + Task.md      ║
║                          ── schreibt ──▶ E2E Tests +                  ║
║                             SYSTEM-{SLICE}.md                          ║
║                          (AK-Mapping, Slice-Abschluss)                 ║
║                          VORAUSSETZUNG: /_I_codeIntegration abgeschl. ║
║                                                                         ║
║  PARALLEL (blockiert NICHT den Zyklus):                                 ║
║  _knowledge      ── liest MODEL ── schreibt ──▶ {THEMA}_Wissen.md      ║
║                      (kann von _SC_observe, _SC_hypothese, _SC_ergebnis ║
║                       als zusaetzlicher Kontext gelesen werden)          ║
║                      SCOPE-GUARD bei aktivem BR (W14)                  ║
║                                                                         ║
║  KEIN Wissen wird im Kontext transportiert.                             ║
║  ALLES steht in Dateien.                                                ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  WELLEN-KETTE (innerhalb eines Commands):                               ║
║                                                                         ║
║  Exploration schreibt ──▶ exploration/{NAME}-E*.md                      ║
║  Drafts LIEST exploration/*.md ──▶ schreibt drafts/{NAME}-*-D*.md      ║
║  Synthese LIEST drafts/*.md ──▶ schreibt models/{NAME}_Model.md        ║
║                                                                         ║
║  *** Zwischen jeder Welle kann /compact ausgefuehrt werden ***          ║
║  *** Das Manifest trackt welche Welle als naechstes dran ist ***        ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  AGENT-STRATEGIE:                                                       ║
║                                                                         ║
║  Phase                 │ easy        │ normal              │ hard           ║
║  ──────────────────────┼─────────────┼─────────────────────┼─────────────  ║
║  /_taskDefinition      │ 1 Hauptagent│ 2-3 Drafter+Haupt.  │ 3-5 D.+H.    ║
║  /_spec                │ 1 Hauptagent│ Drafts+Synthese     │ Expl+D+S     ║
║  /_model               │ 1 Hauptagent│ Drafts+Synthese     │ Expl+D+S     ║
║  /_gap                 │ 1 Hauptagent│ Drafts+Synthese     │ Expl+D+S     ║
║  /_SC_observe          │ 1 Hauptagent│ 2-3 Drafter+Haupt.  │ 3-5 D.+H.    ║
║  /_SC_modelMaintain    │ 1 Hauptagent│ 1-2 Drafter+Haupt.  │ 2-3 D.+H.    ║
║  /_SC_qualityGate      │ 1 Hauptagent│ 1-2 Drafter+Haupt.  │ 2-3 D.+H.    ║
║  /_analyse (LEGACY)    │ 1 Hauptagent│ 2-3 Drafter+Haupt.  │ 3-5 D.+H.    ║
║  /_SC_hypothese        │ 1 Hauptagent│ 2-3 Drafter+Haupt.  │ 3-5 D.+H.    ║
║  /_SC_implement        │ 1 Hauptagent│ 1 Hauptagent        │ 1 Hauptag.   ║
║  /_SC_ergebnis         │ 1 Hauptagent│ 2-3 Subag.+Haupt.   │ 5-10 S.+H.   ║
║  /_knowledge           │ 1 Hauptagent│ Drafts+Synthese     │ Expl+D+S     ║
║  /_SC_blindspotDet.    │ ---         │ 1 Hauptagent        │ 2-5 D.+H.    ║
║  /_SC_archBoundaries   │ ---         │ 1 Hauptagent        │ 2-3 D.+H.    ║
║  ──────────────────────┼─────────────┼─────────────────────┼─────────────  ║
║  PIPELINE v3.0:        │             │                     │              ║
║  /_I_cleanCodeArchit.  │ 1 Hauptag.  │ 1 H.+2-3 MCP       │ 1 H.+3-5 MCP║
║  /_I_cleanCodeSlice    │ 1 Hauptag.  │ 1 H.+1-2 MCP       │ 1 H.+2-3 MCP║
║  /_I_codeAtomic        │ 1 Hauptag.  │ 1 Hauptagent        │ 1 Hauptag.   ║
║  /_I_codeIntegration   │ 1 Hauptag.  │ 1 Hauptagent        │ 1 Hauptag.   ║
║  /_I_codeSystem        │ 1 Hauptag.  │ 1 Hauptagent        │ 1 Hauptag.   ║
║                                                                         ║
║  Modell-Zuweisung: Abhaengig von SYSTEM-MODEL im Manifest.             ║
║  Effektives Modell = min(SYSTEM-MODEL, Command-Max).                    ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  MANIFEST (.claude/analysis/_manifest.md):                              ║
║                                                                         ║
║  Wird von JEDEM Command gelesen und aktualisiert.                       ║
║  Enthaelt: NAME, Phase, Welle, Dateien, Naechster Schritt              ║
║                                                                         ║
║  NEU (v2.0+):                                                           ║
║    STAGNATION: {N} (Dezimalzahl 0.0 bis 7.0+)                          ║
║    LETZTER STARKER FORTSCHRITT: Loop {X}, Typ: {Beschreibung}          ║
║    LETZTER SCHWACHER FORTSCHRITT: Loop {Y}, Typ: {Beschreibung}        ║
║    SYSTEM-MODEL: opus|sonnet|haiku                                      ║
║    SCHWIERIGKEIT: easy|normal|hard                                      ║
║                                                                         ║
║  *** Das Manifest ist die Bruecke ueber /compact ***                    ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Dann lies `.claude/analysis/_manifest.md` falls vorhanden und zeige den aktuellen Stand:

```
AKTUELLER STAND:
  Name: {NAME aus Manifest}
  Phase: {Phase aus Manifest}
  Naechster Schritt: {Command aus Manifest}
  Geschriebene Dateien: {Anzahl}
  Stagnation: {Zaehler aus Manifest, falls vorhanden}
```

Falls kein Manifest existiert:
```
KEIN MANIFEST GEFUNDEN.
Starte mit: /_taskDefinition {NAME}
  (oder /_model {NAME} hard falls keine Kruemmel noetig)
```

ARGUMENTS: $ARGUMENTS
