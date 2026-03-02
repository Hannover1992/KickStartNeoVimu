# Wissenschaftlicher Forschungszyklus - Hilfe & Uebersicht

Zeige die Uebersicht der Scientific Cycle (/_SC_*) Commands.

## Aufruf

```
/_SC_help
```

---

## SYSTEM-UEBERSICHT

Gib dem User folgende Uebersicht aus:

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  WISSENSCHAFTLICHER FORSCHUNGSZYKLUS v3.0 (6+1 Commands)              ║
║                                                                         ║
║  SRP-konform: Jeder Command hat genau EINE Verantwortlichkeit.         ║
║  Ersetzt den monolithischen /_analyse Command (<v2.2).                 ║
║                                                                         ║
║  ═══ ZYKLUS-KETTE (6 Schritte, iterativ) ═══                          ║
║                                                                         ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │                                                                 │    ║
║  │   /_SC_observe                                                  │    ║
║  │   Actor: OBSERVER                                               │    ║
║  │   → Findings sammeln OHNE Interpretation                        │    ║
║  │   → LIEST: Model, ERGEBNIS (vorheriger Zyklus)                 │    ║
║  │   → SCHREIBT: OBSERVE{N}.md (Sektion A: Findings)              │    ║
║  │   → Optional: _parking-lot.md (Incidental Findings)            │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   /_SC_modelMaintain                                            │    ║
║  │   Actor: MODEL-MAINTAINER                                       │    ║
║  │   → Model pflegen: W{n} hinzufuegen, GC, Split ausfuehren     │    ║
║  │   → LIEST: Model, OBSERVE, ERGEBNIS                            │    ║
║  │   → SCHREIBT: Model.md (W{n}, GC, Kap. 6a)                    │    ║
║  │   → Bei Trigger: Model-Topologie + Teilmodelle                 │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   /_SC_qualityGate                                              │    ║
║  │   Actor: QUALITY-GATE                                           │    ║
║  │   → 5 Quality Gates pruefen + Eskalationen triggern            │    ║
║  │   → Gate 1: Battle-Royale (SRS-Trend, Anti-Patterns)           │    ║
║  │   → Gate 2: Kohaesion (W{n}/TC, Split-Trigger)                 │    ║
║  │   → Gate 3: Feature-Abschluss (Coverage-%)                     │    ║
║  │   → Gate 4: Blind-Spot-Detection (T1-T5 Muster)                │    ║
║  │   → Gate 5: Stagnation (Schwellen, ABORT-Empfehlung)           │    ║
║  │   → SCHREIBT: QUALITYGATE{N}.md                                │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   /_SC_hypothese                                                │    ║
║  │   Actor: HYPOTHESEN-FORMULIERER                                 │    ║
║  │   → KREATIVE Phase: Loesungen ERFINDEN                         │    ║
║  │   → Sektion 0: Garbage Collection (PFLICHT ab Cycle 2)         │    ║
║  │   → Sektion 1: Genau 1 falsifizierbare Hypothese               │    ║
║  │   → Verifikations-Kriterium V1-V5 + Scope-Deklaration         │    ║
║  │   → SCHREIBT: HYPOTHESEN.md                                    │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   /_SC_implement                                                │    ║
║  │   Actor: IMPLEMENTIERER                                         │    ║
║  │   → Genau 1 IC (Implementation Concern) pro Durchgang          │    ║
║  │   → Horizontale Suche: Pattern-Matching im gleichen Layer      │    ║
║  │   → Soft-Limits: 5 Dateien, 100 LOC                            │    ║
║  │   → Verifikations-Anleitung: 3-5 konkrete Test-Schritte        │    ║
║  │   → SCHREIBT: Code + HYPOTHESEN.md (aktualisiert)              │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │   /_SC_ergebnis                                                 │    ║
║  │   Actor: ERGEBNIS-SAMMLER (DATENBANK-MODUS)                    │    ║
║  │   → Rohdaten sammeln + mechanische Ableitungen                  │    ║
║  │   → Drei-Kategorien-Regel: Rohdaten, Mech., KEINE Interpr.    │    ║
║  │   → SRS-Messung + Widerlegungs-Marker + Stagnations-Check     │    ║
║  │   → SCHREIBT: ERGEBNIS{N}.md                                   │    ║
║  │                          │                                      │    ║
║  │                          ▼                                      │    ║
║  │              ┌──── Neuer Zyklus ────┐                           │    ║
║  │              └──▶ /_SC_observe      │                           │    ║
║  │                                     │                           │    ║
║  └─────────────────────────────────────┘                           │    ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  ORCHESTRATOR (automatische Zyklus-Steuerung):                         ║
║                                                                         ║
║  /_SC_orchestrate {NAME} [difficulty] [ceiling] [floor] [-I]           ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Team Lead + Worker orchestrieren kompletten Forschungszyklus    │   ║
║  │  Actor: TEAM LEAD (spawnt Worker pro Task)                      │   ║
║  │                                                                  │   ║
║  │  MODUS (NEU v3.0, OmniCommand EC-3):                           │   ║
║  │  ┌──────────────────────────────────────────────────────────┐   │   ║
║  │  │  THEORETISCH (Default, ohne -I):                         │   │   ║
║  │  │    → _implement wird UEBERSPRUNGEN                       │   │   ║
║  │  │    → _hypothese = Haupt-Produktions-Phase (Spec-Output)  │   │   ║
║  │  │    → Verifikation: V-S1 bis V-S4 (Spec-Pruefung)       │   │   ║
║  │  │    → Output: Model + Spec (KEINE Code-Aenderungen)       │   │   ║
║  │  │                                                          │   │   ║
║  │  │  IMPLEMENT (mit -I Flag):                                │   │   ║
║  │  │    → _implement wird AUSGEFUEHRT                         │   │   ║
║  │  │    → Verifikation: V1-V5 (Code-Pruefung)               │   │   ║
║  │  │    → Output: Model + Code                                │   │   ║
║  │  └──────────────────────────────────────────────────────────┘   │   ║
║  │                                                                  │   ║
║  │  COLD-START (NEU v3.0, OmniCommand EC-1):                      │   ║
║  │    T-1 Checkliste (CS-0 bis CS-6) VOR dem Pre-Cycle:           │   ║
║  │    CS-1 Branch erstellen, CS-2 Manifest archivieren,           │   ║
║  │    CS-3 Neues Manifest, CS-4 Parking-Lot pruefen,             │   ║
║  │    CS-5 W_fetch, CS-6 taskDefinition + model                  │   ║
║  │                                                                  │   ║
║  │  DECISION-TREE (NEU v3.0, OmniCommand EC-2):                   │   ║
║  │    SC (unklar/komplex) vs I (klar+Spec) vs WP (Paper)         │   ║
║  │    Hybride Ketten: SC→I, SC→WP, SC-Spec→I                    │   ║
║  │    KONTEXT-MAPPING: SC-Artefakte → Empfaenger-Konzepte        │   ║
║  │                                                                  │   ║
║  │  PARKING-LOT (NEU v3.0, OmniCommand EC-4):                     │   ║
║  │    3-Phasen: Park → Search → Reactivate                       │   ║
║  │    _parking-lot.md als Incidental Findings Queue               │   ║
║  └──────────────────────────────────────────────────────────────────┘   ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  ERGAENZENDE COMMANDS (vom Zyklus getriggert):                         ║
║                                                                         ║
║  /_architecturalBoundaries   Teilproblem-Dekomposition + Vert. Suche  ║
║                              (einmalig, von qualityGate getriggert)    ║
║                                                                         ║
║  /_blindspotDetection        Blind-Spot-Detection + Canary Probes      ║
║                              (bei Muster T1-T5, max 7 Probes)         ║
║                                                                         ║
║  /_knowledge {THEMA}         Deep-Dive Wissens-Recherche               ║
║                              (parallel zum Zyklus, blockiert NICHT)    ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  MECHANISMEN:                                                          ║
║                                                                         ║
║  Battle-Royale (BR):  SRS-Score, Suchraum verkleinern, R-AP1..R-AP5   ║
║  Model-Split:         >15 W{n}/TC → Teilmodelle (VM-1..VM-6)          ║
║  Garbage Collection:  WIDERLEGT > ELIMINIERT > AKTIV (Sek.0 ab Cy.2)  ║
║  Stagnation:          <3.0 OK, >=5.0 PFLICHT, >=7.0 ABORT             ║
║  Verifikation:     V1-V5 (Code), V-S1-S4 (Spec) je nach MODUS       ║
║  KONTEXT-MAPPING:  SC→I, SC→WP, SC-Spec→I Transformation            ║
║  Eskalation:          P1 ABORT > P2 Re-Expansion > P3 BR > P4 Split   ║
║                                                                         ║
║  OVERRIDE-SYSTEM:                                                      ║
║  SO = Soft-Override (auto-Notiz), HO = Hard-Override (Begruendung)     ║
║  57 Elemente, davon 20 HO-kritisch                                    ║
║                                                                         ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                         ║
║  PRE-CYCLE (vor dem ersten Zyklus):                                    ║
║                                                                         ║
║  /_W_fetch           Vault+RAG → .claude/ (Wissen holen)               ║
║  /_taskDefinition    Task.md + Kruemmel aus pileOfMud                  ║
║  /_spec (optional)   Ziel-Architektur + SOLL-Zustand                   ║
║  /_model             Model.md aufbauen (3-Wellen: Expl→Draft→Synth)   ║
║  /_gap               Gap-Analyse: IST vs SOLL Delta                    ║
║                                                                         ║
║  STRATEGISCH (nach jedem Zyklus):                                      ║
║                                                                         ║
║  /_W_push_temp       .claude/ → RAG local (Wissen sichern)             ║
║                                                                         ║
║  POST-CYCLE (nach Feature-Abschluss):                                  ║
║                                                                         ║
║  /_model finish      Model konsolidieren                               ║
║  /_W_push_global     .claude/ → RAG global + Vault (Wissen global)     ║
║  /_W_obsidianSync    Synthese-Dokumente in Obsidian Vault              ║
║  /_W_modelSplit      Model → thematische Teile (Vault)                 ║
║  /_retrospektive     Feature-Abschluss + Wissenstransfer               ║
║                                                                         ║
║  MODEL-PFLEGE (integriert via _SC_modelMaintain v2.4):                 ║
║                                                                         ║
║  /_D_orchestrate {F} Model-Bloat bekaempfen (SOFT/HARD-Trigger)       ║
║  → Automatisch getriggert wenn Model >=500 Zeilen (SOFT, HiL)         ║
║  → Verpflichtend wenn >=700 Zeilen (HARD, blockiert Post-Cycle)       ║
║  → Detail: /_D_help (Debloat-System Uebersicht)                       ║
║                                                                         ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

Dann lies `.claude/analysis/_manifest.md` falls vorhanden und zeige den aktuellen Stand.

ARGUMENTS: $ARGUMENTS
