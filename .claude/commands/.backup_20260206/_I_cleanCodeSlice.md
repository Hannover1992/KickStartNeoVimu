# /_I_cleanCodeSlice

**Status:** NEU v3.0 (Implementierungs-Pipeline Phase 2)
**Actor:** SLICE-PLANER (Uncle Bob via MCP)
**Zweck:** Einzelnen Slice PLANEN (Test-Strategie, Pattern Reuse, Architektur)

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_I_cleanCodeSlice {SLICE_NAME} [easy|normal|hard]              ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                ║
║    1. .claude/analysis/_manifest.md                                      ║
║    2. .claude/analysis/synthese/{NAME}-ARCHITECT.md                      ║
║       → Slice-Definition (Komponenten, Dependencies, Reihenfolge)       ║
║    3. .claude/models/{NAME}_Model.md (falls vorhanden, IST-Zustand)     ║
║    4. .claude/patterns/_pattern-library.md                               ║
║       → Bekannte Patterns fuer Horizontale Suche                        ║
║       (Graceful Degradation: Ohne Library = direkte Codebase-Suche)     ║
║    5. Codebase (via Glob/Grep/Read fuer aehnliche Impl.)               ║
║    6. MCP Clean Code (Uncle Bob Queries)                                 ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md                         ║
║      → Test-Liste (Kent Beck Style: Tests VOR Code auflisten)          ║
║      → Test-Strategie (Outside-In, Canary)                              ║
║      → Pattern Reuse (Horizontale Suche Ergebnisse)                     ║
║      → Architektur-Entscheidungen (DIP, Interfaces)                    ║
║      → Uncle Bob Empfehlungen (MCP Queries)                             ║
║      → Implementierungs-Checkpoints                                     ║
║    .claude/analysis/_manifest.md (aktualisieren)                         ║
║                                                                          ║
║  SCHREIBT (Output) - OPTIONAL:                                           ║
║    .claude/patterns/_pattern-library.md (Update bei neuen Patterns)     ║
║    .claude/_parking-lot.md (APPEND, falls Incidental Findings)          ║
║                                                                          ║
║  MCP INTEGRATION:                                                        ║
║    - mcp__cleancoder__query() fuer Uncle Bob Weisheiten                 ║
║    - Query Topics:                                                       ║
║      * "testable architecture for {SLICE description}"                  ║
║      * "test-first approach for {component type}"                       ║
║      * "pattern reuse for {similar functionality}"                      ║
║      * "dependency inversion for {boundary crossing}"                   ║
║                                                                          ║
║  MCP-BREMSE:                                                             ║
║    ┌─────────────────────────────────────────────────────────┐           ║
║    │  easy:   MIN-Modus    → max 1 Query,  limit=1          │           ║
║    │  normal: MIDDLE-Modus → max 3 Queries, limit=3         │           ║
║    │  hard:   MAX-Modus    → max 5 Queries, limit=5         │           ║
║    │                                                         │           ║
║    │  Modi:  min=1Q/1R  middle=3Q/3R  max=5Q/5R            │           ║
║    │  Planer-Phase: Schwierigkeit bestimmt Modus             │           ║
║    └─────────────────────────────────────────────────────────┘           ║
║                                                                          ║
║  PIPELINE-POSITION:                                                      ║
║    [/_I_cleanCodeArchitect] → [/_I_cleanCodeSlice] → [/_I_codeAtomic]       ║
║                                                                          ║
║  ACTOR: SLICE-PLANER (Uncle Bob)                                         ║
║    Plant die Implementierung eines einzelnen Slice:                     ║
║    - Test-Liste (SOLL-Model als Spezifikation)                          ║
║    - Pattern Reuse (Horizontale Suche)                                   ║
║    - Architektur-Entscheidungen (Testbarkeit)                           ║
║    KEINE Code-Aenderungen, KEINE Tests schreiben.                       ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

Der **SLICE-PLANER** Actor hat eine einzige Verantwortung:

**Einen einzelnen Slice so planen, dass TDD effizient ausfuehrbar ist**

Was der Slice-Planer **TUT**:
- ✅ Test-Liste erstellen (Kent Beck: Tests VOR Code auflisten)
- ✅ Test-Reihenfolge festlegen (Outside-In, Canary-First)
- ✅ Horizontale Suche (Pattern Library + Codebase-Scan)
- ✅ Blueprint auswaehlen (bester Reuse-Kandidat)
- ✅ Architektur-Entscheidungen (DIP, Interfaces fuer Testbarkeit)
- ✅ Uncle Bob MCP befragen fuer Slice-spezifische Guidance
- ✅ Implementierungs-Checkpoints definieren

Was der Slice-Planer **NICHT TUT**:
- ❌ Code schreiben (→ /_I_codeAtomic)
- ❌ Tests schreiben (→ /_I_codeAtomic)
- ❌ Andere Slices planen (→ erneut /_I_cleanCodeSlice)
- ❌ Architektur-Ueberblick erstellen (→ /_I_cleanCodeArchitect)

---

## Pipeline-Position

```
ARCHITECT → **CLEANCODESLICE** → CODEATOMIC → CODEINTEGRATION
                  |
                  ↓
            {SLICE}-PLAN.md
            (Test-Liste + Patterns + Architektur)
```

**Prev:** /_I_cleanCodeArchitect (ARCHITECT.md)
**Next:** /_I_codeAtomic (TDD Red-Green-Refactor)

**Wiederholung:** Pro Slice einmal ausfuehren

---

## Uncle Bob's Leitprinzip

> "An experienced test-driven developer will very often write down a list
> of tests that they think need to be passed before they write any code.
> This is something that Kent Beck taught me some time ago."

**Bedeutung fuer diese Phase:**
- Test-Liste ZUERST (SOLL-Model als Spezifikation)
- Tests definieren WAS, nicht WIE
- Outside-In: Peripherie-Tests vor Core-Tests
- Kent Beck Pattern: Tests auflisten → Tests priorisieren → TDD starten

---

## Schritt 0: Inputs lesen

1. Lies `_manifest.md` → aktueller {NAME}
2. Lies `{NAME}-ARCHITECT.md` → Slice-Definition fuer {SLICE_NAME}
   - Vertikale Komponenten (FE, BE, DB)
   - Dependencies
   - API-Schnittstellen
3. Lies `_pattern-library.md` (falls vorhanden)
4. Lies `{NAME}_Model.md` (falls vorhanden) → IST-Zustand als Kontext

---

## Schritt 1: Uncle Bob MCP Queries

### Query 1: Testbare Architektur

```python
mcp__cleancoder__query(
    "testable architecture for {SLICE_DESCRIPTION},
     test-first approach, outside-in testing,
     {TECH_STACK: Angular frontend, .NET backend}"
)
```

**Ergebnis:** Test-Reihenfolge, DIP-Empfehlungen

### Query 2: Pattern Reuse

```python
mcp__cleancoder__query(
    "pattern reuse for {COMPONENT_TYPE},
     similar implementations, common patterns,
     {SPECIFIC_PATTERN_QUESTION}"
)
```

**Ergebnis:** Welche Patterns aus Codebase wiederverwendbar

### Query 3: Dependency Inversion (bei Boundary Crossings)

```python
mcp__cleancoder__query(
    "dependency inversion for {BOUNDARY_DESCRIPTION},
     interface design, testability with mocks"
)
```

**Ergebnis:** Interface-Design fuer Testbarkeit

---

## Schritt 2: Horizontale Suche

### 2.1 Layer bestimmen

Pro Komponente im Slice:

| Komponente | Layer-ID | Glob-Basis-Pattern |
|------------|----------|-------------------|
| {Component} | FE-COMP | `**/src/app/**/*.component.ts` |
| {Service FE} | FE-SVC | `**/src/app/**/*.service.ts` |
| {Controller} | BE-CTRL | `**/Controllers/**/*Controller.cs` |
| {Service BE} | BE-SVC | `**/Services/**/*Service.cs` |
| {Repository} | BE-REPO | `**/Repositories/**/*Repository.cs` |
| {Entity} | BE-ENT | `**/Entities/**/*.cs` |

### 2.2 Aehnliche Implementierungen finden (Glob)

Pro Komponente:
1. Glob-Suche im gleichen Layer
2. Top-3 Kandidaten auswaehlen (Namens-/Funktions-Aehnlichkeit)
3. Kandidaten lesen (Read-Tool)

### 2.3 Reuse-Bewertung (0-1 Score)

```
Score startet bei 1.0

Reduktionen:
  -0.1  Mehr/weniger Parameter als Ziel
  -0.1  Anderer Return-Typ
  -0.2  Signifikant mehr Dependencies
  -0.15 Keine Tests vorhanden
  -0.2  Hohe zyklomatische Komplexitaet
  -0.3  Anderer Layer (LAYER-CONSTRAINT-VERLETZUNG!)

Erhoehungen:
  +0.1  Folgt Naming-Conventions
  +0.15 Hat Tests als Vorlage
  +0.2  Gleicher Layer (Basis-Erwartung)
```

### 2.4 3-Farb-Klassifikation

| Score | Farbe | Bedeutung |
|-------|-------|-----------|
| > 0.8 | **GRAY** | Fast 1:1 kopierbar |
| 0.5-0.8 | **ORANGE** | Anpassungen noetig |
| < 0.5 | **RED** | Custom Implementation |

---

## Schritt 3: Test-Liste erstellen (Kent Beck Style)

### SOLL-Model als Spezifikation

> "When we write tests, even the unit tests of test-driven development,
> what we are really writing are specifications."

Erstelle eine geordnete Liste aller Tests, die geschrieben werden muessen:

```markdown
## Test-Liste (SOLL-Model)

### Unit Tests (/_I_codeAtomic)

1. [ ] **{Komponente}.{Methode} - {Szenario}**
   - RED: Test schreiben (erwartet {VERHALTEN})
   - GREEN: Minimal {CODE_BESCHREIBUNG}
   - Typ: Statist / Machist

2. [ ] **{Komponente}.{Methode} - {Edge Case}**
   - RED: Test schreiben
   - GREEN: Minimal Code
   - Typ: Statist

### Integration Tests (/_I_codeIntegration)

3. [ ] **{API_ENDPOINT} - {Szenario}**
   - RED: HTTP-Test schreiben
   - GREEN: Controller + Service verdrahten
   - Typ: Machist (Boundary Crossing)

### System Tests (/_I_codeSystem)

4. [ ] **{E2E_SZENARIO}**
   - RED: Full-Stack Test schreiben
   - GREEN: Gesamtsystem konfigurieren
```

### Test-Reihenfolge (Outside-In)

```
Empfohlene Reihenfolge (Canary-First):

1. API Contract Test (Integration)     ← Canary: aeusserste Schicht
2. Service Unit Test                    ← Business Logic
3. Repository Unit Test                 ← Data Access
4. Frontend Component Test             ← UI Layer
5. Frontend Service Test               ← FE Business Logic
```

**Warum Outside-In?**
- Peripherie-Tests = Canary (zeigen Probleme frueh)
- Core-Tests kommen spaeter (wenn Interfaces klar sind)
- Vermeidet "zu tief zu frueh" (kombinatorische Explosion)

---

## Output-Format: PLAN.md

**Pfad:** `.claude/analysis/plans/{NAME}-{SLICE}-PLAN.md`

```markdown
---
name: {NAME}
slice: {SLICE_NAME}
phase: plan
pipeline: implementation
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
agent: Hauptagent
date: {YYYY-MM-DD}
reads: synthese/{NAME}-ARCHITECT.md, patterns/_pattern-library.md
status: final
---

# Plan: {SLICE_NAME}

**Feature:** {NAME}
**Slice:** {SLICE_NAME}
**Datum:** {YYYY-MM-DD}
**Uncle Bob Architekt:** Clean Code MCP

## Slice-Ueberblick

**Vertikale Komponenten:**
- **FE:** {Komponenten}
- **BE:** {Komponenten}
- **DB:** {Komponenten}

**Abhaengigkeiten:**
- {Dependencies}

**Schnittstellen:**
- {API Endpoints}

## Uncle Bob's Weisheit

> {Relevantes Zitat aus MCP Query}

## Test-Liste (SOLL-Model, Kent Beck Style)

### Unit Tests (Phase: /_I_codeAtomic)

| # | Test | Komponente | Typ | Reihenfolge |
|---|------|-----------|-----|-------------|
| T1 | {Test-Beschreibung} | {Klasse} | Statist | 1 |
| T2 | {Test-Beschreibung} | {Klasse} | Statist | 2 |
| T3 | {Test-Beschreibung} | {Klasse} | Machist | 3 |

### Integration Tests (Phase: /_I_codeIntegration)

| # | Test | Endpoint/Boundary | Typ | Reihenfolge |
|---|------|------------------|-----|-------------|
| IT1 | {Test-Beschreibung} | {API Endpoint} | Machist | 1 |
| IT2 | {Test-Beschreibung} | {DB Boundary} | Machist | 2 |

### System Tests (Phase: /_I_codeSystem)

| # | Test | Szenario | Reihenfolge |
|---|------|----------|-------------|
| ST1 | {Test-Beschreibung} | {E2E Flow} | 1 |

## Test-Reihenfolge (Outside-In)

```
Phase 3 (/_I_codeAtomic):
  T1 → T2 → T3 → ...

Phase 4 (/_I_codeIntegration):
  IT1 → IT2 → ...

Phase 5 (/_I_codeSystem):
  ST1 → ...
```

## Pattern Reuse (Horizontale Suche)

### Gefundene Patterns

| Pattern | Kandidat | Reuse-Score | Farbe |
|---------|----------|-------------|-------|
| {Pattern} | {Pfad} | {0.xx} | GRAY/ORANGE/RED |

### Ausgewaehlter Blueprint

- **Datei:** {Pfad des besten Kandidaten}
- **Reuse-Score:** {Score}
- **Farbe:** {GRAY/ORANGE/RED}
- **Uebernehmbare Elemente:** {Liste}
- **Anzupassende Elemente:** {Liste}

## Architektur-Entscheidungen

### Dependency Inversion

```
{Controller} → I{Service} (interface)
{Service} → I{Repository} (interface)
```

**Warum:** Testbarkeit + Austauschbarkeit

### Interface-Design

```csharp
// Interfaces die erstellt werden muessen:
public interface I{ServiceName}
{
    Task<{ReturnType}> {Method}({ParamType} param);
}
```

## Implementierungs-Checkpoints

| # | Checkpoint | Erwartung |
|---|-----------|-----------|
| 1 | Alle Unit Tests gruen | /_I_codeAtomic abgeschlossen |
| 2 | Integration Tests gruen | /_I_codeIntegration abgeschlossen |
| 3 | System Test gruen | /_I_codeSystem abgeschlossen |

## Naechster Schritt

/_I_codeAtomic {SLICE_NAME}
```

---

## Schwierigkeits-Parameter

| Schwierigkeit | MCP Queries | Horizontale Suche |
|---------------|-------------|-------------------|
| **easy** | 1 Query | Top-1 Kandidat |
| **normal** | 2-3 Queries | Top-3 Kandidaten |
| **hard** | 3-5 Queries + Subagenten | Top-5 Kandidaten + Deep Analysis |

---

## Kompakt-Sicherheit

Nach Command-Abschluss:
- State: PLAN.md geschrieben
- Resume: /_I_codeAtomic kann PLAN.md lesen

---

## Obsidian-Tags

```yaml
tags:
  - type/slice-plan
  - pipeline/implementation
  - op/{FEATURE}
  - topic/TDD-Planning
  - topic/Pattern-Reuse
pipeline-position: slice
prev: [[I_cleanCodeArchitect]]
next: [[I_codeAtomic]]
slice: {SLICE_NAME}
```

---

## Siehe auch

- [[I_cleanCodeArchitect]] - Vorheriger Schritt (Gesamtarchitektur)
- [[I_codeAtomic]] - Naechster Schritt (TDD Red-Green-Refactor)
- [[_implement]] - Bestehender Implement-Command (wissenschaftlicher Zyklus)
- [[_pattern-library]] - Pattern-Katalog
