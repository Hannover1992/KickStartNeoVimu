# /_I_codeSystem

**Status:** NEU v3.0 (Implementierungs-Pipeline Phase 5)
**Actor:** SYSTEM-TESTER
**Zweck:** System/E2E Tests via Red-Green-Refactor (Gesamtsystem-Verifikation)

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_I_codeSystem {SLICE_NAME}                                    ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                ║
║    1. .claude/analysis/_manifest.md                                      ║
║    2. .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md                      ║
║       → System Test-Liste (ST1, ST2, ...)                               ║
║       → E2E-Szenarien (User Flows)                                     ║
║    3. .claude/analysis/synthese/{NAME}-INTEGRATION-{SLICE}.md           ║
║       → Abgeschlossene Integration Tests (Voraussetzung)               ║
║       → Boundary-Entscheidungen (welche Boundaries verdrahtet)         ║
║    4. .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md                 ║
║       → Abgeschlossene Unit Tests (Kontext)                            ║
║    5. .claude/Task.md                                                    ║
║       → Akzeptanzkriterien (System Tests validieren diese!)            ║
║    6. Codebase (Production Code, Konfiguration, Cypress Tests)         ║
║    7. MCP Clean Code (Uncle Bob System Test Guidance)                   ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    1. Code: System/E2E Tests (*.feature / *.cy.ts / *SystemTests.cs)   ║
║    2. Code: System-Konfiguration (falls noetig fuer E2E)              ║
║    3. .claude/analysis/synthese/{NAME}-SYSTEM-{SLICE}.md                ║
║       → Abgeschlossene System Test-Liste (alle Tests mit Status)       ║
║       → RGR-Zyklen Protokoll                                           ║
║       → Akzeptanzkriterien-Mapping (Test → AK)                        ║
║       → Slice-Abschluss-Erklaerung                                    ║
║    4. .claude/analysis/_manifest.md (Slice als ABGESCHLOSSEN markieren)║
║                                                                          ║
║  SCHREIBT (Output) - OPTIONAL:                                           ║
║    .claude/patterns/_pattern-library.md (E2E Test Patterns)            ║
║    .claude/_parking-lot.md (APPEND, falls Incidental Findings)          ║
║                                                                          ║
║  MCP INTEGRATION (IN-LOOP):                                              ║
║    - mcp__cleancoder__query() bei System-Test Unsicherheit             ║
║    - Query Topics:                                                       ║
║      * "system testing strategy for {E2E scenario}"                    ║
║      * "GUI testing principles {framework}"                            ║
║      * "acceptance criteria verification through tests"                ║
║                                                                          ║
║  MCP-BREMSE:                                                             ║
║    ┌─────────────────────────────────────────────────────────┐           ║
║    │  IMMER MIN-Modus → max 1 Query, limit=1                │           ║
║    │  Ausfuehrende Phase: NUR bei echter Unsicherheit fragen │           ║
║    │  Modi:  min=1Q/1R  middle=3Q/3R  max=5Q/5R            │           ║
║    └─────────────────────────────────────────────────────────┘           ║
║                                                                          ║
║  RED-GREEN-REFACTOR LOOP:                                                ║
║    Fuer JEDEN System Test aus PLAN.md:                                   ║
║      RED:      E2E Test schreiben (MUSS fehlschlagen)                   ║
║      GREEN:    System konfigurieren (MUSS Test bestehen)                ║
║      REFACTOR: Test-Code bereinigen (Page Objects, Helpers)             ║
║      CHECKPOINT: Manifest aktualisieren                                  ║
║                                                                          ║
║  VORAUSSETZUNG:                                                          ║
║    /_I_codeIntegration {SLICE} MUSS abgeschlossen sein                 ║
║    → Alle Unit Tests gruen                                              ║
║    → Alle Integration Tests gruen                                       ║
║    → INTEGRATION-{SLICE}.md existiert                                   ║
║                                                                          ║
║  PIPELINE-POSITION:                                                      ║
║    [/_I_codeIntegration] → [/_I_codeSystem] → [SLICE ABGESCHLOSSEN]    ║
║                                                                          ║
║  ACTOR: SYSTEM-TESTER                                                    ║
║    Schreibt System/E2E Tests via TDD.                                   ║
║    Validiert Akzeptanzkriterien aus Task.md.                            ║
║    Erklaert den Slice als ABGESCHLOSSEN nach allen gruenen Tests.      ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

Der **SYSTEM-TESTER** Actor hat eine einzige Verantwortung:

**System/E2E Tests via Red-Green-Refactor + Slice-Abschluss-Erklaerung**

Was der System-Tester **TUT**:
- ✅ System/E2E Tests schreiben (Gesamtsystem End-to-End)
- ✅ Akzeptanzkriterien aus Task.md durch Tests validieren
- ✅ System-Konfiguration anpassen (falls noetig fuer E2E)
- ✅ Red-Green-Refactor Zyklus fuer System Tests
- ✅ Slice als ABGESCHLOSSEN erklaeren (alle 3 Test-Ebenen gruen)
- ✅ Uncle Bob MCP bei E2E-Unsicherheit befragen
- ✅ Manifest final aktualisieren (Slice-Status)

Was der System-Tester **NICHT TUT**:
- ❌ Unit Tests schreiben (→ /_I_codeAtomic, abgeschlossen)
- ❌ Integration Tests schreiben (→ /_I_codeIntegration, abgeschlossen)
- ❌ Production Business Logic aendern (nur Konfiguration)
- ❌ Naechsten Slice planen (→ /_I_cleanCodeSlice)

---

## Pipeline-Position

```
CODEINTEGRATION → **CODESYSTEM** → [SLICE ABGESCHLOSSEN]
                       |
                       ↓
                 E2E Tests + Config
                 SYSTEM-{SLICE}.md
                 → Naechster Slice ODER Feature fertig
```

**Prev:** /_I_codeIntegration (Integration Tests)
**Next:** /_I_cleanCodeSlice {NAECHSTER_SLICE} ODER Feature abgeschlossen

**Eskalation:** Bei Stagnation → /_SC_observe

---

## Uncle Bob ueber System Tests

> "Tests are the foundation of confidence. The higher-level tests give us
> confidence that the whole system works together. But we want fewer of
> these because they are slow and fragile."

> "We don't need to test the GUI through the GUI. We test the business
> rules through a more stable interface. The GUI tests should only test
> that the GUI is properly connected to the business rules."

**Bedeutung fuer diese Phase:**
- WENIGE, aber WERTVOLLE System Tests
- Testen dass Gesamtsystem VERBUNDEN ist, nicht Business Logic (die ist in Unit Tests)
- GUI Tests: Nur Verbindung GUI → Business Rules pruefen
- Langsam + fragil → bewusst minimieren, aber nicht weglassen
- Akzeptanzkriterien als Leitfaden (was der User sehen/tun kann)

---

## Schritt 0: Voraussetzungen pruefen

### 0.1 Integration Phase abgeschlossen?

```
1. Lies _manifest.md → Pruefe Integration Status fuer {SLICE}
2. Lies INTEGRATION-{SLICE}.md → Alle ITs gruen?
3. Lies ATOMIC-{SLICE}.md → Alle Unit Tests gruen?
4. Falls NICHT:
   → ABBRUCH: "/_I_codeIntegration {SLICE} muss zuerst abgeschlossen werden"
   → KEIN Uebergang zu System ohne gruene Unit + Integration Tests
```

### 0.2 Inputs lesen

```
1. Lies plans/{NAME}-{SLICE}-PLAN.md
   → System Test-Liste (ST1, ST2, ...)
   → E2E-Szenarien definiert
2. Lies Task.md
   → Akzeptanzkriterien (System Tests validieren diese!)
3. Lies INTEGRATION-{SLICE}.md
   → Boundary-Entscheidungen verstehen
   → Welche Boundaries sind verdrahtet?
4. Pruefe: Welche STs sind bereits abgeschlossen? (Resume-Faehigkeit)
5. Bestehende E2E Tests scannen:
   - Cypress: **/cypress/e2e/**/*.cy.ts
   - Cucumber: **/cypress/e2e/**/*.feature
   - .NET System: **/*SystemTests.cs
```

---

## Schritt 1: Akzeptanzkriterien-Mapping

### Task.md → System Tests

```markdown
| AK# | Akzeptanzkriterium (aus Task.md) | System Test | Typ |
|-----|----------------------------------|------------|-----|
| AK1 | {User kann X tun} | ST1 | E2E |
| AK2 | {System zeigt Y an} | ST2 | E2E |
| AK3 | {Fehlerfall Z wird abgefangen} | ST3 | E2E |
```

### Luecken-Analyse

```
Fuer jedes Akzeptanzkriterium in Task.md:
  - Hat es einen System Test? → Gut
  - Hat es KEINEN System Test? → PLAN.md ergaenzen oder AK durch
    Unit/Integration Tests abgedeckt (explizit dokumentieren)
```

---

## Schritt 2: E2E Test-Strategie

### 2.1 Test-Typen

| Typ | Framework | Beschreibung | Wann |
|-----|-----------|-------------|------|
| **Cypress E2E** | Cypress + Cucumber | Full-Stack Browser Test | FE + BE zusammen |
| **API System** | HTTP Client / Supertest | API ohne Browser | Nur BE |
| **.NET System** | xUnit + TestServer | Full .NET Stack | BE ohne FE |

### 2.2 Test-Umgebung

```
System Tests brauchen:
  - Laufenden Backend-Server (oder TestServer)
  - Laufendes Frontend (oder Cypress Component Mount)
  - Datenbank (Test-DB, nicht InMemory fuer System Tests)
  - Mock fuer External Services (DIC, S3 → Mock-Server)

WICHTIG: System Tests sind LANGSAM
  → Nur das Noetigste testen
  → Keine Business Logic duplizieren (ist in Unit Tests)
  → Nur "sind die Teile verbunden?" pruefen
```

### 2.3 Uncle Bob's "Test Through Stable Interface" Prinzip

```
NICHT testen:                    STATTDESSEN testen:
─────────────                    ────────────────────
Button-Farbe                     Button loest Aktion aus
CSS Layout                       Daten werden angezeigt
Animation                        Navigation funktioniert
Pixel-Position                   Formular sendet Daten
```

---

## Schritt 3: RGR-Loop (System Tests)

### Fuer JEDEN System Test aus PLAN.md:

```
╔═══════════════════════════════════════════════════════════════╗
║  RED-GREEN-REFACTOR ZYKLUS (System)                           ║
╠═══════════════════════════════════════════════════════════════╣
║                                                                ║
║  ┌─────────────────────────────────────────┐                   ║
║  │  RED: E2E Test schreiben                 │                   ║
║  │  - ST aus PLAN.md nehmen                │                   ║
║  │  - User-Flow definieren (Given/When/Then)│                  ║
║  │  - Erwartung: Akzeptanzkriterium        │                   ║
║  │  - Test MUSS fehlschlagen               │                   ║
║  └─────────────────┬───────────────────────┘                   ║
║                    │                                            ║
║                    ▼                                            ║
║  ┌─────────────────────────────────────────┐                   ║
║  │  GREEN: System konfigurieren             │                   ║
║  │  - Feature Toggle aktivieren            │                   ║
║  │  - Routing konfigurieren (FE + BE)      │                   ║
║  │  - Testdaten seeden (DB)                │                   ║
║  │  - NUR Config, KEINE neue Business Logic│                   ║
║  └─────────────────┬───────────────────────┘                   ║
║                    │                                            ║
║                    ▼                                            ║
║  ┌─────────────────────────────────────────┐                   ║
║  │  REFACTOR: Test-Code bereinigen          │                   ║
║  │  - Page Objects extrahieren             │                   ║
║  │  - Step Definitions wiederverwenden     │                   ║
║  │  - Test-Data Builder Pattern            │                   ║
║  │  - ALLE Tests (Unit+Int+System) gruen   │                   ║
║  └─────────────────┬───────────────────────┘                   ║
║                    │                                            ║
║                    ▼                                            ║
║  ┌─────────────────────────────────────────┐                   ║
║  │  CHECKPOINT: Manifest Update             │                   ║
║  │  - ST als abgeschlossen markieren       │                   ║
║  │  - AK-Mapping aktualisieren             │                   ║
║  │  - Compact-Safe nach jedem ST           │                   ║
║  └─────────────────────────────────────────┘                   ║
║                                                                ║
╚═══════════════════════════════════════════════════════════════╝
```

### RED Phase (Detail - System)

```
1. Nimm naechsten ST aus PLAN.md System Test-Liste
2. Identifiziere Akzeptanzkriterium (AK-Mapping)
3. Schreibe den E2E Test:

   Cypress/Cucumber:
     Feature: {Feature-Name}
       Scenario: {AK-Beschreibung}
         Given {Vorbedingung}
         When {User-Aktion}
         Then {Erwartetes Ergebnis}

   API System Test:
     Arrange: Server starten, Testdaten seeden
     Act: HTTP Request an echten Endpoint
     Assert: Response + DB State

   .NET System Test:
     Arrange: WebApplicationFactory mit echter DB
     Act: HTTP Client Request
     Assert: Response validieren

4. Fuehre den Test aus
5. VERIFIZIERE: Test MUSS fehlschlagen
   - Typisch: Route nicht erreichbar, Feature nicht sichtbar, Daten fehlen
6. Dokumentiere: "RED: {ST-Name} fehlgeschlagen weil {Grund}"
```

### GREEN Phase (Detail - System)

```
1. MINIMALE System-Konfiguration:
   - FE: Route registrieren, Component in Navigation einbinden
   - BE: Endpoint erreichbar machen (falls noch nicht durch Integration)
   - DB: Testdaten seeden (Seed Migration oder Fixture)
   - Config: Feature Toggle, Environment Variables
2. REGELN:
   - NUR Konfiguration aendern, KEINE Business Logic
   - Code existiert bereits aus /_I_codeAtomic + /_I_codeIntegration
   - Falls Code fehlt → ZURUECK zu fruehere Phase
3. Fuehre den System Test aus
4. VERIFIZIERE: Test MUSS gruen sein
5. VERIFIZIERE: ALLE Tests gruen (Unit + Integration + System)
6. Dokumentiere: "GREEN: {ST-Name} bestanden mit {Config-Beschreibung}"
```

### REFACTOR Phase (Detail - System)

```
1. ALLE Tests sind gruen (Unit + Integration + System)
2. Bereinige E2E Test-Code:
   - Page Objects: UI-Interaktionen kapseln
     class {Feature}Page {
       visit() { cy.visit('/feature-url') }
       fillForm(data) { ... }
       submit() { ... }
       assertSuccess() { ... }
     }
   - Step Definitions: Cucumber Steps wiederverwenden
   - Test-Data Builders: Testdaten-Erstellung kapseln
   - Custom Commands: Wiederkehrende Cypress-Aktionen
3. Pattern-Check:
   - E2E Pattern erkannt? → Pattern Library
   - Wiederverwendbare Page Objects? → Shared
4. Fuehre ALLE Tests aus (Unit + Integration + System)
5. VERIFIZIERE: ALLE Tests gruen
6. Dokumentiere: "REFACTOR: {Was bereinigt}"
```

---

## Schritt 4: Stagnations-Erkennung

### Stagnations-Zaehler (identisch zu vorherigen Phasen)

```
RGR_OHNE_FORTSCHRITT = 0

Nach jedem RGR-Zyklus:
  Falls ST neu gruen → RGR_OHNE_FORTSCHRITT = 0
  Falls ST NICHT gruen → RGR_OHNE_FORTSCHRITT += 1

Schwellen:
  <= 3: NORMAL (weitermachen)
  4:    WARNUNG (Uncle Bob MCP + System-Analyse)
  5+:   ESKALATION
```

### Eskalations-Pfad (System-spezifisch)

```
/_I_codeSystem stagniert (5+ RGR)
    │
    ├── Typische Ursachen:
    │   - E2E-Umgebung nicht korrekt (Server nicht gestartet)
    │   - Timing-Probleme (async Operationen)
    │   - Testdaten nicht korrekt geseeded
    │   - CSS-Selektoren instabil (fragile Tests)
    │
    ├── MCP Query: "system test failure for {E2E problem}"
    │
    ├── Falls Timing-Problem:
    │   → cy.wait() / Retry-Logic / Polling
    │
    ├── Falls Umgebungs-Problem:
    │   → Docker-Compose / TestServer Konfiguration pruefen
    │
    └── Falls weiterhin stuck:
        → /_SC_observe (System-Verhalten verstehen)
        → zurueck zu /_I_codeSystem
```

---

## Schritt 5: Slice-Abschluss

### 5.1 Alle 3 Test-Ebenen gruen?

```
╔═══════════════════════════════════════════╗
║  SLICE-ABSCHLUSS CHECKLISTE               ║
╠═══════════════════════════════════════════╣
║                                            ║
║  Unit Tests:        {N}/{N} ✅ GRUEN      ║
║  Integration Tests: {N}/{N} ✅ GRUEN      ║
║  System Tests:      {N}/{N} ✅ GRUEN      ║
║                                            ║
║  Akzeptanzkriterien:                       ║
║    AK1: ✅ Durch ST1 validiert            ║
║    AK2: ✅ Durch ST2 validiert            ║
║    AK3: ✅ Durch IT2 + T5 abgedeckt      ║
║                                            ║
║  SLICE STATUS: ✅ ABGESCHLOSSEN           ║
╚═══════════════════════════════════════════╝
```

### 5.2 Naechster Schritt bestimmen

```
Falls weitere Slices im ARCHITECT.md:
  → /_I_cleanCodeSlice {NAECHSTER_SLICE}
  → Manifest: Naechsten Slice als aktuell markieren

Falls ALLE Slices abgeschlossen:
  → Feature KOMPLETT
  → Manifest: Feature als ABGESCHLOSSEN markieren
  → Optional: /_SC_modelMaintain (Model.md aktualisieren)
```

---

## Output-Format: SYSTEM-{SLICE}.md

**Pfad:** `.claude/analysis/synthese/{NAME}-SYSTEM-{SLICE}.md`

```markdown
---
name: {NAME}
slice: {SLICE_NAME}
phase: system
pipeline: implementation
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
date: {YYYY-MM-DD}
reads: plans/{NAME}-{SLICE}-PLAN.md, Task.md, INTEGRATION-{SLICE}.md
status: final
---

# System: {NAME} - {SLICE_NAME}

**Feature:** {NAME}
**Slice:** {SLICE_NAME}
**RGR-Zyklen:** {N}
**Tests geschrieben:** {N} System Tests
**Konfiguration:** {N} Dateien angepasst

## Voraussetzung

- **Atomic Phase:** ✅ Abgeschlossen ({N} Unit Tests gruen)
- **Integration Phase:** ✅ Abgeschlossen ({N} Integration Tests gruen)

## Akzeptanzkriterien-Mapping

| AK# | Akzeptanzkriterium | Test(s) | Ebene | Status |
|-----|-------------------|---------|-------|--------|
| AK1 | {Beschreibung} | ST1 | System | ✅ |
| AK2 | {Beschreibung} | ST2, IT1 | System + Integration | ✅ |
| AK3 | {Beschreibung} | T3, T4 | Unit | ✅ |

## Test-Ergebnisse

| # | Test | Szenario | Status | RGR-Zyklen | AK |
|---|------|----------|--------|-----------|-----|
| ST1 | {Test-Name} | {E2E Flow} | ✅ GRUEN | 1 | AK1 |
| ST2 | {Test-Name} | {E2E Flow} | ✅ GRUEN | 2 | AK2 |

## RGR-Protokoll

### ST1: {Test-Name}
- RED: System Test geschrieben, fehlgeschlagen weil {Grund}
- GREEN: Konfiguriert: {Route, Seed, Toggle}
- REFACTOR: Page Object extrahiert: {Name}

### ST2: {Test-Name}
- RED: ...
- GREEN: ...
- REFACTOR: ...

## Slice-Abschluss

### Test-Pyramide Zusammenfassung

```
        /  {N} System Tests    \        ✅ GRUEN
       / {N} Integration Tests  \       ✅ GRUEN
      /   {N} Unit Tests          \     ✅ GRUEN
```

### Akzeptanzkriterien

- [x] AK1: {Beschreibung} → ST1
- [x] AK2: {Beschreibung} → ST2 + IT1
- [x] AK3: {Beschreibung} → T3 + T4

### Slice-Erklaerung

**{SLICE_NAME} ist ABGESCHLOSSEN.**
Alle {N_TOTAL} Tests auf 3 Ebenen sind gruen.
Alle Akzeptanzkriterien sind durch Tests validiert.

## Naechster Schritt

{OPTION A:} /_I_cleanCodeSlice {NAECHSTER_SLICE}
{OPTION B:} Feature {NAME} ist KOMPLETT. Alle Slices abgeschlossen.
```

---

## Manifest-Update (Slice-Abschluss)

```markdown
**PHASE:** _I_codeSystem {SLICE_NAME} → ABGESCHLOSSEN
**PIPELINE:** Implementation
**UNIT TESTS:** {N}/{N} gruen ✅
**INTEGRATION TESTS:** {N}/{N} gruen ✅
**SYSTEM TESTS:** {N}/{N} gruen ✅
**AKZEPTANZKRITERIEN:** {N}/{N} validiert ✅
**SLICE STATUS:** ✅ ABGESCHLOSSEN

### Slice-Uebersicht - {NAME}
- [x] {SLICE_1}: ✅ ABGESCHLOSSEN (T:{N} IT:{N} ST:{N})
- [ ] {SLICE_2}: ⏳ NAECHSTER SLICE
- [ ] {SLICE_3}: ⏳ WARTEND

### Naechster Schritt
/_I_cleanCodeSlice {NAECHSTER_SLICE}
```

**COMPACT-SICHER:** Nach Slice-Abschluss kann /compact ausgefuehrt werden.
Resume liest Manifest → weiss welcher Slice als naechstes dran ist.

---

## Qualitaetskriterien

- **Drei Gesetze TDD:** Strikt eingehalten (auch bei System Tests!)
- **RED:** Jeder ST MUSS fehlschlagen bevor GREEN
- **GREEN:** NUR Konfiguration (keine neue Business Logic!)
- **REFACTOR:** Page Objects, Step Definitions, Test-Data Builders
- **ALLE Tests gruen:** Unit + Integration + System nach jedem Schritt
- **AK-Mapping:** Jedes Akzeptanzkriterium hat mindestens 1 Test
- **Wenige, wertvolle Tests:** Uncle Bob's Prinzip (nicht Business Logic duplizieren)
- **Stabile Selektoren:** data-testid statt CSS-Klassen
- **Manifest aktuell:** Slice-Abschluss klar dokumentiert
- **Keine Regression:** Vorherige Test-Ebenen duerfen NICHT brechen

---

## Kompakt-Sicherheit

Nach JEDEM gruenen System Test:
- State: Manifest mit ST-Fortschritt aktualisiert
- Resume: Naechster ST aus PLAN.md + Manifest-Status

Nach SLICE-ABSCHLUSS:
- State: Slice als ABGESCHLOSSEN im Manifest
- Resume: Naechster Slice oder Feature-Abschluss

**Granularitaet:** Jeder System Test + Slice-Abschluss = Compact-Checkpoint.

---

## Obsidian-Tags

```yaml
tags:
  - type/system
  - pipeline/implementation
  - op/{FEATURE}
  - topic/TDD
  - topic/System-Tests
  - topic/E2E-Tests
  - topic/Acceptance-Criteria
  - topic/Red-Green-Refactor
pipeline-position: system
prev: [[I_codeIntegration]]
next: [[I_cleanCodeSlice]] (naechster Slice)
slice: {SLICE_NAME}
```

---

## Siehe auch

- [[I_codeIntegration]] - Vorheriger Schritt (Integration Tests)
- [[I_cleanCodeSlice]] - Naechster Slice planen (falls weitere Slices)
- [[I_cleanCodeArchitect]] - Slice-Uebersicht und Reihenfolge
- [[Task.md]] - Akzeptanzkriterien (Input fuer System Tests)
- [[SC_observe]] - Eskalation bei Stagnation
