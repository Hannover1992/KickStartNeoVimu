# /_I_codeIntegration

**Status:** NEU v3.0 (Implementierungs-Pipeline Phase 4)
**Actor:** INTEGRATIONS-CODER
**Zweck:** Integration Tests + Boundary Code via Red-Green-Refactor

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_I_codeIntegration {SLICE_NAME}                               ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                ║
║    1. .claude/analysis/_manifest.md                                      ║
║    2. .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md                      ║
║       → Integration Test-Liste (IT1, IT2, ...)                          ║
║       → Boundary Crossings (API Endpoints, DB Zugriff)                 ║
║       → Architektur-Entscheidungen (DIP, Interfaces)                   ║
║    3. .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md                 ║
║       → Abgeschlossene Unit Tests (Voraussetzung)                      ║
║       → Refactoring-Entscheidungen (Interface-Design)                  ║
║       → Pattern Library Updates aus Atomic Phase                        ║
║    4. .claude/patterns/_pattern-library.md (Integration Patterns)       ║
║    5. Codebase (Production Code aus Atomic + bestehende IntTests)       ║
║    6. MCP Clean Code (Uncle Bob Boundary Guidance)                      ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    1. Code: Integration Tests (*IntegrationTests.cs / *.int.spec.ts)   ║
║    2. Code: Boundary Code (Wiring, DI Config, DB Migrations)           ║
║    3. .claude/analysis/synthese/{NAME}-INTEGRATION-{SLICE}.md           ║
║       → Abgeschlossene Integration Test-Liste (alle Tests mit Status)  ║
║       → RGR-Zyklen Protokoll                                           ║
║       → Boundary-Entscheidungen dokumentiert                           ║
║       → Gefundene Integrations-Probleme + Loesungen                   ║
║    4. .claude/analysis/_manifest.md (nach JEDEM gruenen Test update)    ║
║                                                                          ║
║  SCHREIBT (Output) - OPTIONAL:                                           ║
║    .claude/patterns/_pattern-library.md (Integration Patterns)          ║
║    .claude/_parking-lot.md (APPEND, falls Incidental Findings)          ║
║                                                                          ║
║  MCP INTEGRATION (IN-LOOP):                                              ║
║    - mcp__cleancoder__query() bei Boundary-Unsicherheit                ║
║    - Query Topics:                                                       ║
║      * "integration testing for {boundary description}"                ║
║      * "dependency inversion at {layer crossing}"                      ║
║      * "mock vs real implementation for {boundary}"                    ║
║      * "test isolation for {integration scenario}"                     ║
║                                                                          ║
║  MCP-BREMSE:                                                             ║
║    ┌─────────────────────────────────────────────────────────┐           ║
║    │  IMMER MIN-Modus → max 1 Query, limit=1                │           ║
║    │  Ausfuehrende Phase: NUR bei echter Unsicherheit fragen │           ║
║    │  Modi:  min=1Q/1R  middle=3Q/3R  max=5Q/5R            │           ║
║    └─────────────────────────────────────────────────────────┘           ║
║                                                                          ║
║  RED-GREEN-REFACTOR LOOP:                                                ║
║    Fuer JEDEN Integration Test aus PLAN.md:                              ║
║      RED:      Integration Test schreiben (MUSS fehlschlagen)           ║
║      GREEN:    Boundary Code verdrahten (MUSS Test bestehen)            ║
║      REFACTOR: Wiring bereinigen (DI, Config, Abstraktion)             ║
║      CHECKPOINT: Manifest aktualisieren                                  ║
║                                                                          ║
║  VORAUSSETZUNG:                                                          ║
║    /_I_codeAtomic {SLICE} MUSS abgeschlossen sein                      ║
║    → Alle Unit Tests gruen                                              ║
║    → ATOMIC-{SLICE}.md existiert                                        ║
║                                                                          ║
║  PIPELINE-POSITION:                                                      ║
║    [/_I_codeAtomic] → [/_I_codeIntegration] → [/_I_codeSystem]         ║
║                                                                          ║
║  ACTOR: INTEGRATIONS-CODER                                               ║
║    Schreibt Integration Tests + Boundary Code via TDD.                  ║
║    Testet Boundary Crossings (API, DB, Service-zu-Service).             ║
║    Machist-Stil an DIP-Grenzen, Statist wo moeglich.                  ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

Der **INTEGRATIONS-CODER** Actor hat eine einzige Verantwortung:

**Integration Tests + Boundary Code via Red-Green-Refactor schreiben**

Was der Integrations-Coder **TUT**:
- ✅ Integration Tests schreiben (Boundary Crossings)
- ✅ Boundary Code verdrahten (DI Container, DB Config, API Routing)
- ✅ Mock-Strategien anwenden (Machist an DIP-Grenzen)
- ✅ Test-Isolation sicherstellen (Container, InMemory DB, TestServer)
- ✅ Red-Green-Refactor Zyklus fuer Integration Tests
- ✅ Uncle Bob MCP bei Boundary-Unsicherheit befragen
- ✅ Manifest nach jedem gruenen Integration Test aktualisieren

Was der Integrations-Coder **NICHT TUT**:
- ❌ Unit Tests schreiben (→ /_I_codeAtomic, bereits abgeschlossen)
- ❌ System Tests schreiben (→ /_I_codeSystem)
- ❌ Production Business Logic aendern (nur Wiring + Boundary Code)
- ❌ Architektur planen (→ /_I_cleanCodeSlice)

---

## Pipeline-Position

```
CODEATOMIC → **CODEINTEGRATION** → CODESYSTEM
                    |
                    ↓
              Integration Tests + Boundary Code
              INTEGRATION-{SLICE}.md
```

**Prev:** /_I_codeAtomic (Unit Tests + Production Code)
**Next:** /_I_codeSystem (System Tests)

**Eskalation:** Bei Stagnation (5+ RGR ohne Fortschritt) → /_SC_observe

---

## Uncle Bob ueber Boundary Testing

> "Machist-style tests are most useful when testing things that cross
> dependency inversion boundaries. When an object crosses a significant
> architectural boundary, mocking the far side of that boundary is
> essential for test isolation."

> "The reason we choose TDD is not because it tells us whether the code
> works. The reason we do TDD is that it allows us to make changes to
> the code with confidence."

**Bedeutung fuer diese Phase:**
- Machist (London School) an JEDER DIP-Grenze
- Statist (Detroit School) wo keine Boundary Crossing
- Test-Isolation durch Mocks, nicht durch Infrastruktur
- Integration Tests pruefen: Verdrahtung korrekt, Boundaries respektiert

---

## Schritt 0: Voraussetzungen pruefen

### 0.1 Atomic Phase abgeschlossen?

```
1. Lies _manifest.md → Pruefe Atomic Status fuer {SLICE}
2. Lies ATOMIC-{SLICE}.md → Alle Unit Tests gruen?
3. Falls NICHT:
   → ABBRUCH: "/_I_codeAtomic {SLICE} muss zuerst abgeschlossen werden"
   → KEIN Uebergang zu Integration ohne gruene Unit Tests
```

### 0.2 Inputs lesen

```
1. Lies plans/{NAME}-{SLICE}-PLAN.md
   → Integration Test-Liste (IT1, IT2, ...)
   → Boundary Crossings identifiziert
   → API Endpoints definiert
2. Lies ATOMIC-{SLICE}.md
   → Welche Interfaces wurden erstellt?
   → Welche Patterns wurden angewandt?
   → Production Code Struktur verstehen
3. Lies _pattern-library.md (falls vorhanden)
   → Integration Test Patterns
   → DI Configuration Patterns
4. Pruefe: Welche ITs sind bereits abgeschlossen? (Resume-Faehigkeit)
```

---

## Schritt 1: Boundary-Analyse

### 1.1 Boundary-Typen identifizieren

Aus PLAN.md und ATOMIC-{SLICE}.md die Boundaries klassifizieren:

| Boundary-Typ | Beschreibung | Test-Strategie |
|---------------|-------------|----------------|
| **API** | HTTP Controller → Service | WebApplicationFactory, TestServer |
| **DB** | Repository → Datenbank | InMemory DB oder Container |
| **Service** | Service → Service (via Interface) | Mock (Machist) |
| **External** | Service → Externer Dienst (DIC, S3) | Mock (Machist, immer) |
| **Event** | Event Publisher → Handler | Mock oder InMemory Bus |

### 1.2 Test-Isolation Strategie

```
Pro Boundary-Typ:
  API:      WebApplicationTestFactory (TestServer in-process)
  DB:       InMemory oder Docker Container (je nach Komplexitaet)
  Service:  Interface-Mock (DIP Boundary)
  External: Interface-Mock (IMMER, nie echte externe Dienste)
  Event:    InMemory Event Bus
```

---

## Schritt 2: RGR-Loop (Integration Tests)

### Fuer JEDEN Integration Test aus PLAN.md:

```
╔═══════════════════════════════════════════════════════════════╗
║  RED-GREEN-REFACTOR ZYKLUS (Integration)                      ║
╠═══════════════════════════════════════════════════════════════╣
║                                                                ║
║  ┌─────────────────────────────────────────┐                   ║
║  │  RED: Integration Test schreiben         │                   ║
║  │  - IT aus PLAN.md nehmen                │                   ║
║  │  - Boundary-Setup (TestServer, Mocks)   │                   ║
║  │  - Request/Aufruf ueber Boundary       │                   ║
║  │  - Erwartung: Ende-zu-Ende Verhalten    │                   ║
║  │  - Test MUSS fehlschlagen               │                   ║
║  └─────────────────┬───────────────────────┘                   ║
║                    │                                            ║
║                    ▼                                            ║
║  ┌─────────────────────────────────────────┐                   ║
║  │  GREEN: Boundary Code verdrahten         │                   ║
║  │  - DI Registration (Service → Interface) │                   ║
║  │  - API Routing (Controller → Endpoint)  │                   ║
║  │  - DB Mapping (Entity → Table)          │                   ║
║  │  - Config (ConnectionStrings, Options)  │                   ║
║  │  - NUR Wiring, KEINE neue Business Logic│                   ║
║  └─────────────────┬───────────────────────┘                   ║
║                    │                                            ║
║                    ▼                                            ║
║  ┌─────────────────────────────────────────┐                   ║
║  │  REFACTOR: Wiring bereinigen             │                   ║
║  │  - DI Module extrahieren                │                   ║
║  │  - Config Sections organisieren         │                   ║
║  │  - Test-Helper fuer Boundary Setup      │                   ║
║  │  - ALLE Tests (Unit + Integration) gruen│                   ║
║  └─────────────────┬───────────────────────┘                   ║
║                    │                                            ║
║                    ▼                                            ║
║  ┌─────────────────────────────────────────┐                   ║
║  │  CHECKPOINT: Manifest Update             │                   ║
║  │  - IT als abgeschlossen markieren       │                   ║
║  │  - Compact-Safe nach jedem IT           │                   ║
║  └─────────────────────────────────────────┘                   ║
║                                                                ║
╚═══════════════════════════════════════════════════════════════╝
```

### RED Phase (Detail - Integration)

```
1. Nimm naechsten IT aus PLAN.md Integration Test-Liste
2. Erstelle Test-Setup:
   - WebApplicationTestFactory ODER Container-Setup
   - Mock-Registrierung fuer External Boundaries
   - Testdaten vorbereiten (Seed oder Arrange)
3. Schreibe den Test:
   - Arrange: Boundary-Setup, Mocks konfigurieren
   - Act: Request ueber Boundary senden
     - HTTP Request (API Boundary)
     - Service-Aufruf (Service Boundary)
     - Repository-Aufruf (DB Boundary)
   - Assert: Ende-zu-Ende Verhalten pruefen
     - Response Status + Body (API)
     - State Change (DB)
     - Side Effects (Events, Calls)
4. Fuehre den Test aus
5. VERIFIZIERE: Test MUSS fehlschlagen
   - Typisch: 404 (Route fehlt), DI Exception, DB fehlt
6. Dokumentiere: "RED: {IT-Name} fehlgeschlagen weil {Grund}"
```

### GREEN Phase (Detail - Integration)

```
1. Schreibe MINIMALEN Boundary Code:
   - DI: services.AddScoped<I{Service}, {Service}>()
   - Routing: [HttpGet("{route}")] / app.MapGet()
   - DB: modelBuilder.Entity<{Entity}>() Config
   - Config: appsettings.json / Options Pattern
2. REGELN:
   - NUR Wiring-Code (Verdrahtung), KEINE neue Business Logic
   - Business Logic existiert bereits aus /_I_codeAtomic
   - Falls Business Logic fehlt → ZURUECK zu /_I_codeAtomic
   - Blueprint aus existierenden Integration Tests nutzen
3. Fuehre den Integration Test aus
4. VERIFIZIERE: Test MUSS gruen sein
5. VERIFIZIERE: ALLE bisherigen Tests gruen (Unit + Integration!)
6. Dokumentiere: "GREEN: {IT-Name} bestanden mit {Wiring-Beschreibung}"
```

### REFACTOR Phase (Detail - Integration)

```
1. ALLE Tests sind gruen (Unit + Integration)
2. Bereinige Wiring-Code:
   - DI Module: Extension Methods fuer Service Registration
     services.Add{Feature}Services()
   - Config: Dedicated Config Sections
   - Startup/Program.cs: Sauber organisiert
3. Bereinige Test-Infrastructure:
   - Shared TestServer Setup (Fixture)
   - Test-Helper fuer wiederkehrende Boundary Setups
   - Shared Mock Configurations
4. Pattern-Check:
   - Integration Pattern erkannt? → Pattern Library Update
   - Wiederverwendbares Test-Setup? → Pattern Library
5. Fuehre ALLE Tests aus (Unit + Integration)
6. VERIFIZIERE: ALLE Tests gruen
7. Dokumentiere: "REFACTOR: {Was bereinigt}"
```

---

## Schritt 3: Machist vs Statist Entscheidungsmatrix

### Wann Machist (London School)?

```
Machist (Mocks/Spies) verwenden WENN:
  ✅ Boundary Crossing (DIP-Grenze)
  ✅ Externer Dienst (DIC, S3, SFTP)
  ✅ Datenbank (in Unit-artigen Integration Tests)
  ✅ Event Bus / Message Queue
  ✅ Time/Clock Dependencies
```

### Wann Statist (Detroit School)?

```
Statist (echte Objekte) verwenden WENN:
  ✅ Innerhalb eines Boundary (Service → Service im selben Layer)
  ✅ InMemory DB verfuegbar und schnell
  ✅ WebApplicationTestFactory (TestServer = echt, aber in-process)
  ✅ Value Objects, DTOs, Mapper
```

### Uncle Bob MCP bei Zweifelsfaellen

```python
mcp__cleancoder__query(
    "mock vs real implementation for {boundary description},
     test isolation vs test confidence tradeoff,
     machist vs statist for integration testing"
)
```

---

## Schritt 4: Stagnations-Erkennung

### Stagnations-Zaehler (identisch zu /_I_codeAtomic)

```
RGR_OHNE_FORTSCHRITT = 0

Nach jedem RGR-Zyklus:
  Falls IT neu gruen → RGR_OHNE_FORTSCHRITT = 0
  Falls IT NICHT gruen → RGR_OHNE_FORTSCHRITT += 1

Schwellen:
  <= 3: NORMAL (weitermachen)
  4:    WARNUNG (Uncle Bob MCP + Boundary-Analyse)
  5+:   ESKALATION
```

### Eskalations-Pfad (Integration-spezifisch)

```
/_I_codeIntegration stagniert (5+ RGR)
    │
    ├── Typische Ursachen:
    │   - DI Konfiguration fehlerhaft
    │   - Interface-Mismatch (Atomic → Integration)
    │   - DB Schema passt nicht zu Entity
    │   - Missing Middleware/Pipeline Config
    │
    ├── MCP Query: "integration test failure for {boundary problem}"
    │
    ├── Falls MCP hilft → weitermachen
    │
    ├── Falls Interface-Mismatch:
    │   → Zurueck zu /_I_codeAtomic (Interface anpassen)
    │
    └── Falls weiterhin stuck:
        → /_SC_observe (Boundary-Verhalten verstehen)
        → /_SC_modelMaintain (Model aktualisieren)
        → zurueck zu /_I_codeIntegration
```

---

## Schritt 5: Integritaetspruefung

### Nach ALLEN Integration Tests gruen:

```
1. ALLE Unit Tests ausfuehren → Muessen gruen bleiben
2. ALLE Integration Tests ausfuehren → Muessen gruen sein
3. Keine Regressionen in Atomic Phase
4. Boundary Code korrekt verdrahtet
5. DI Container valid (keine zirkulaeren Dependencies)
```

### Regressions-Check

```
Falls Unit Tests nach Integration Tests fehlschlagen:
  → Integration hat Business Logic veraendert (VERBOTEN!)
  → Sofort rueckgaengig machen
  → NUR Wiring-Code anpassen, NICHT Business Logic
```

---

## Output-Format: INTEGRATION-{SLICE}.md

**Pfad:** `.claude/analysis/synthese/{NAME}-INTEGRATION-{SLICE}.md`

```markdown
---
name: {NAME}
slice: {SLICE_NAME}
phase: integration
pipeline: implementation
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
date: {YYYY-MM-DD}
reads: plans/{NAME}-{SLICE}-PLAN.md, synthese/{NAME}-ATOMIC-{SLICE}.md
status: final
---

# Integration: {NAME} - {SLICE_NAME}

**Feature:** {NAME}
**Slice:** {SLICE_NAME}
**RGR-Zyklen:** {N}
**Tests geschrieben:** {N} Integration Tests
**Boundary Code:** {N} Dateien, {M} LOC Wiring

## Voraussetzung

- **Atomic Phase:** ✅ Abgeschlossen ({N} Unit Tests gruen)
- **ATOMIC-{SLICE}.md:** Vorhanden

## Boundary-Analyse

| Boundary | Typ | Test-Strategie | Mock/Real |
|----------|-----|----------------|-----------|
| {Controller → Service} | API | TestServer | Real (in-process) |
| {Service → Repository} | DB | InMemory DB | Real (InMemory) |
| {Service → ExternalService} | External | Mock | Mock (Machist) |

## Test-Ergebnisse

| # | Test | Boundary | Status | RGR-Zyklen | Stil |
|---|------|----------|--------|-----------|------|
| IT1 | {Test-Name} | {API} | ✅ GRUEN | 1 | Machist |
| IT2 | {Test-Name} | {DB} | ✅ GRUEN | 2 | Statist |
| IT3 | {Test-Name} | {External} | ✅ GRUEN | 1 | Machist |

## RGR-Protokoll

### IT1: {Test-Name}
- RED: Integration Test geschrieben, fehlgeschlagen weil {Grund}
- GREEN: Boundary verdrahtet: {DI, Routing, Config}
- REFACTOR: {Was bereinigt}

### IT2: {Test-Name}
- RED: ...
- GREEN: ...
- REFACTOR: ...

## Boundary-Entscheidungen

| # | Boundary | Entscheidung | Begruendung |
|---|----------|-------------|-------------|
| 1 | {API} | TestServer in-process | Schnell, zuverlaessig |
| 2 | {DB} | InMemory SQLite | Keine Docker-Dependency |
| 3 | {External} | Mock via Interface | Test-Isolation |

## Integritaets-Check

- [ ] ALLE Unit Tests gruen nach Integration Phase
- [ ] ALLE Integration Tests gruen
- [ ] Keine Business Logic in Wiring-Code
- [ ] DI Container valid

## Naechster Schritt

/_I_codeSystem {SLICE_NAME}
```

---

## Manifest-Update (nach JEDEM gruenen IT)

```markdown
**PHASE:** _I_codeIntegration {SLICE_NAME}
**PIPELINE:** Implementation
**UNIT TESTS:** {N}/{N} gruen (alle aus Atomic Phase)
**INTEGRATION TESTS:** {N}/{M} gruen (IT1 ✅, IT2 ✅, IT3 🔄, IT4 ⏳)
**NAECHSTER TEST:** IT{N+1}: {Test-Name}
**STAGNATION:** {RGR_OHNE_FORTSCHRITT}
**LETZTER GRUENER TEST:** {Datum, IT{N}}

### Integration Progress - {SLICE_NAME}
- [x] IT1: {Test-Name} (RGR: 1, Boundary: API)
- [x] IT2: {Test-Name} (RGR: 2, Boundary: DB)
- [ ] IT3: {Test-Name} (IN ARBEIT)
- [ ] IT4: {Test-Name}
```

**COMPACT-SICHER:** Nach jedem gruenen Integration Test kann /compact ausgefuehrt werden.
Resume liest Manifest → weiss welcher IT als naechstes dran ist.

---

## Qualitaetskriterien

- **Drei Gesetze TDD:** Strikt eingehalten (auch bei Integration Tests!)
- **RED:** Jeder IT MUSS fehlschlagen bevor GREEN
- **GREEN:** NUR Wiring-Code (keine neue Business Logic!)
- **REFACTOR:** DI Module, Config, Test-Helper bereinigen
- **ALLE Tests gruen:** Unit + Integration nach jedem Schritt
- **Machist an Boundaries:** Mocks an JEDER DIP-Grenze
- **Keine Regression:** Unit Tests duerfen NICHT brechen
- **Manifest aktuell:** Nach jedem gruenen IT
- **Stagnation erkannt:** Bei 5+ RGR ohne Fortschritt eskalieren

---

## Kompakt-Sicherheit

Nach JEDEM gruenen Integration Test:
- State: Manifest mit IT-Fortschritt aktualisiert
- Resume: Naechster IT aus PLAN.md + Manifest-Status
- Integritaet: Unit Tests + Integration Tests Status dokumentiert

**Granularitaet:** Jeder Integration Test ist ein Compact-Checkpoint.

---

## Obsidian-Tags

```yaml
tags:
  - type/integration
  - pipeline/implementation
  - op/{FEATURE}
  - topic/TDD
  - topic/Integration-Tests
  - topic/Boundary-Testing
  - topic/Red-Green-Refactor
pipeline-position: integration
prev: [[I_codeAtomic]]
next: [[I_codeSystem]]
slice: {SLICE_NAME}
```

---

## Siehe auch

- [[I_codeAtomic]] - Vorheriger Schritt (Unit Tests + Production Code)
- [[I_codeSystem]] - Naechster Schritt (System Tests)
- [[I_cleanCodeSlice]] - PLAN.md mit Integration Test-Liste
- [[SC_observe]] - Eskalation bei Stagnation
