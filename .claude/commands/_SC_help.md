---
type: satellite
---

# Wissenschaftlicher Forschungszyklus - Hilfe & Uebersicht

Zeige die Uebersicht der Scientific Cycle (/_SC_*) Commands.

## Aufruf

```
/_SC_help
```

---

## Updates 2026-05-19 (BL-173/174/175 Cross-Cutting)

**Manifest-Routing (BL-173):**
- SC schreibt `SC_PIPELINE_STATE` in `{bl_folder}/_manifest.md` (pipeline-spezifisch)
- `{vault}/_factory_manifest.md` behaelt ausschliesslich BDF+GLOBAL_*-Bloecke
- Helper: `manifest_reader.read_factory_block(...)`, `manifest_reader.read_bl_block(bl_id, ...)`
- Migration: `migrate_manifest_split.py migrate --vault-root=... --rollback-tag=YYYY-MM-DD`

**Session-Params Per-BL (BL-174):**
- 3-Stufen-Inheritance: BL-Override → Vault-Default → Framework-Default
- Resolver: `session_params_resolver.resolve_param(name, bl_id=None)`
- `/_param` mit `--bl-id=BL-XXX` schreibt BL-spezifisch (SC-Params pro BL isoliert)

**BDF Factory-Lock (BL-175):**
- `acquire/release/heartbeat` via `factory_lock.py`
- TTL+Heartbeat, kein fcntl, eigenes `_factory_lock.md`
- Race-Condition-safe fuer 5-10 parallele BDFs

(siehe `/_help` TEIL 8c, BL-173/174/175 Spec-Dateien)

---

## POSITION IN DER PIPELINE-REISE (3er-Doppel-Sicht, NEU 2026-05-24)

> **Cross-Reference:** Vollstaendige Reise + Geister-Tabelle: `/_help` TEIL 10
> Methodik: `.claude/INSTRUCTION_full_scan_2026-05-24.md`

**Wo sitzt /_SC_orchestrate in der Gesamt-Reise?**

```
/_SDF_orchestrate Phase 2.1 dispatch (modus IN [M4, M5, M6, M7])
                                  │
                                  ▼
                              ★G#6 → /_SC_orchestrate
                                          │
                                          │ SC-Cycle (6 Berater)
                                          ▼
                              Phase 5 AUTOCHAIN-EXIT (INV-MODUS-7)
                                          │
                                          ▼
                              ★G#7 → /_SDF_orchestrate_post
```

**3er-Doppel-Fenster:**

| Position | Vertrag                          | Lese-Fokus                          |
|----------|----------------------------------|-------------------------------------|
| [N-1]    | `/_SDF_orchestrate` Phase 2.1    | DF_BATCH_STATE.modus + current_sub_batch_items |
| [N  ]    | `/_SC_orchestrate`               | LIEST + SCHREIBT (SC-Cycle, sc_handover.md) |
| [N+1]    | `/_SDF_orchestrate_post`         | sc_handover.md.idf_reentry_signal + BERATER_OUTPUTS |

**Geister-Beteiligung:**

- **Input-Geist G#6:** `/_SDF Phase 2.1 → /_SC_orchestrate` (modus M4/M5/M6/M7)
- **Intra-Geist:** SC-Cycle Berater-Sequence (observe → modelMaintain → qualityGate → hypothese → implement → ergebnis)
- **Sub-Geist (FULL-Modus):** `/_SC_orchestrate → /_I_orchestrate` (Symbiose-Pattern, scope=core)
- **Output-Geist G#7:** `/_SC_orchestrate → /_SDF_orchestrate_post` (POST_HANDOVER, INV-HANDOVER-1)

**Re-Entry-Pfade:**

- SDF Phase 4 loopDecision setzt `sc_resume_from="ergebnis"` → SC Phase 0 Resume-Check springt direkt zu `_SC_ergebnis`
- BL-206 Bottleneck-Pfad: SC schreibt `idf_reentry_signal` in sc_handover.md → IDF Phase 3.8 plBewertung refresht SRS
- Standalone-Modus (`--standalone`): kein POST_HANDOVER (User-Direct-Call)

**Step-Anzahl im 1-Pipeline-Durchlauf:**

- Phase 0 Resume-Check → 1 teamSetup → 2 kurzlebigPrompt → 3 teamLeadSteuerung
- SC-Cycle iterativ (max 5-8 Zyklen je difficulty)
- 4 SC-Berater (teamSetup, modusMatrix, kurzlebigPrompt, teamLeadSteuerung)
- 6 SC-Cycle Berater (observe, modelMaintain, qualityGate, hypothese, implement, ergebnis)
- Optional Sub-Calls: `_I_orchestrate` (FULL-Modus), `_architecturalBoundaries`, `_blindspotDetection`, `_knowledge`

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
║  /_SC_orchestrate {NAME} [difficulty] [ceiling] [floor] [-I] [--standalone] ║
║  ┌──────────────────────────────────────────────────────────────────┐   ║
║  │  Team Lead + Worker orchestrieren kompletten Forschungszyklus    │   ║
║  │  Actor: TEAM LEAD (spawnt Worker pro Task)                      │   ║
║  │                                                                  │   ║
║  │  NEU BL-NEW-12 (2026-05-11) — POST_HANDOVER (conditional):       │   ║
║  │    Default-Aufruf (von SDF dispatched): SC ruft am Ende          │   ║
║  │      Skill(_SDF_orchestrate_post, ...) — Phase 3+4 muss laufen!  │   ║
║  │    --standalone Flag (Direct/BDF/W-Aufruf): SKIP Handover        │   ║
║  │    INV-HANDOVER-1: ohne Handover bleibt SDF Phase 3 ungelaufen   │   ║
║  │                                                                  │   ║
║  │  4 MODI (v2.3, SC⟲I Symbiose-Architektur):                     │   ║
║  │  ┌──────────────────────────────────────────────────────────┐   │   ║
║  │  │  FULL (Default, OHNE -I):                                │   │   ║
║  │  │    → Voller Zyklus inkl. /_I_orchestrate (SYMBIOSE)      │   │   ║
║  │  │    → SC⟲I SYMBIOSE: I laeuft core (0-8) innerhalb SC   │   │   ║
║  │  │    → Output: Model + Code (via I-Pipeline core)          │   │   ║
║  │  │                                                          │   │   ║
║  │  │  INLINE (mit -I, kleine ICs):                            │   │   ║
║  │  │    → _implement direkt in SC (1 IC pro Zyklus)           │   │   ║
║  │  │    → Output: Model + kleine Code-Aenderungen             │   │   ║
║  │  │                                                          │   │   ║
║  │  │  REVIEW (--mode=review):                                 │   │   ║
║  │  │    → Bestehendes Artefakt reviewen (kein implement)      │   │   ║
║  │  │    → Output: Review-Report                                │   │   ║
║  │  │                                                          │   │   ║
║  │  │  ANALYSE (--mode=analyse, NEU v2.3):                     │   │   ║
║  │  │    → Reine Analyse/Discovery OHNE Implementation         │   │   ║
║  │  │    → Saettigungs-basierter Exit (delta_wn, Stabilitaet) │   │   ║
║  │  │    → Output: Model + Wissensbasis (KEINE Code-Aenderung) │   │   ║
║  │  └──────────────────────────────────────────────────────────┘   │   ║
║  │                                                                  │   ║
║  │  META-DATEIEN (v3.0 Decomposition):                               │   ║
║  │    Orchestrator = reiner Prozess-Manager (18.6KB permanent)       │   ║
║  │    Domain-Logik in .claude/meta/sc/ (on-demand per Read-Tool):   │   ║
║  │    • task-templates.md    (Task 0-11 Beschreibungen)             │   ║
║  │    • decision-tables.md   (3 Decision Tables)                    │   ║
║  │    • sc-i-gate.md         (Gate + Finale Verifikation)           │   ║
║  │    • symbiose-protocol.md (SC⟲I FULL-Modus)                     │   ║
║  │    • review-modus.md      (Post-I Review Details)                │   ║
║  │    • handoff-template.md  (HandOff-Dokument Template)            │   ║
║  │                                                                  │   ║
║  │  GEPLANT (noch nicht implementiert):                              │   ║
║  │    /_sliceInit (W245): Cold-Start Satellite-Command              │   ║
║  │    Decision-Tree SC/I/WP Routing (OmniCommand EC-2)             │   ║
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
║  Verifikation:     V1-V5 (Code/FULL), V-S1-S4 (Spec/ANALYSE)        ║
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

Dann lies `{VAULT}/_manifest.md` falls vorhanden und zeige den aktuellen Stand.

ARGUMENTS: $ARGUMENTS
