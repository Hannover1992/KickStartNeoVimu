# /_I_codeComponent

**Status:** NEU v3.0 (Implementierungs-Pipeline Phase 4 - Stufe 2)
**Actor:** COMPONENT-CODER
**Zweck:** Component Tests (mehrere Klassen zusammen, externe Grenzen gemockt)

---

## Vertrag

```
+===============================================================================+
|  COMMAND: /_I_codeComponent {SLICE_NAME}                                      |
+===============================================================================+
|  LIEST (Input) - PFLICHT:                                                     |
|    1. .claude/analysis/_manifest.md                                           |
|    2. .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md                           |
|       -> Test-Liste (Component Tests: CT1, CT2, ...)                          |
|       -> Architektur-Entscheidungen (DIP, Interfaces)                         |
|       -> Pattern Reuse (Blueprint aus Horizontaler Suche)                     |
|    3. .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md                      |
|       -> Abgeschlossene Unit Tests (Voraussetzung)                            |
|       -> Refactoring-Entscheidungen (Interface-Design)                        |
|    4. .claude/meta/DCSRE-BE-TestStufenArchitektur.md                          |
|       -> Stufe 2 Definition: Mehrere Klassen, externe Grenzen gemockt         |
|    5. Codebase (Production Code aus Atomic + bestehende Tests)                |
|    6. MCP Clean Code (Uncle Bob Component Guidance)                           |
|                                                                               |
|  SCHREIBT (Output) - PFLICHT:                                                 |
|    1. Code: Component Tests (*ComponentTests.cs / *Tests.cs)                  |
|    2. Code: Ggf. Wiring zwischen internen Klassen                             |
|    3. .claude/analysis/synthese/{NAME}-COMPONENT-{SLICE}.md                   |
|       -> Abgeschlossene Component Test-Liste (alle Tests mit Status)          |
|       -> RGR-Zyklen Protokoll                                                 |
|       -> Interne Verdrahtungs-Entscheidungen                                  |
|    4. .claude/analysis/_manifest.md (nach JEDEM gruenen Test update)          |
|                                                                               |
|  MCP-BREMSE:                                                                  |
|    IMMER MIN-Modus -> max 1 Query, limit=1                                    |
|    Ausfuehrende Phase: NUR bei echter Unsicherheit fragen                     |
|                                                                               |
|  RED-GREEN-REFACTOR LOOP:                                                     |
|    Fuer JEDEN Component Test aus PLAN.md:                                     |
|      RED:      Component Test schreiben (MUSS fehlschlagen)                   |
|      GREEN:    Internes Wiring + minimaler Code                               |
|      REFACTOR: Code bereinigen (Patterns anwenden, DRY)                       |
|      CHECKPOINT: Manifest aktualisieren                                       |
|                                                                               |
|  VORAUSSETZUNG:                                                               |
|    /_I_codeAtomic {SLICE} MUSS abgeschlossen sein                             |
|    -> Alle Unit Tests gruen                                                   |
|    -> ATOMIC-{SLICE}.md existiert                                             |
|                                                                               |
|  PIPELINE-POSITION:                                                           |
|    [/_I_codeAtomic] -> [/_I_codeComponent] -> [/_I_codePartialSystem]         |
|                                                                               |
|  ACTOR: COMPONENT-CODER                                                       |
|    Schreibt Component Tests via TDD.                                          |
|    Testet Zusammenspiel mehrerer interner Klassen.                            |
|    KEINE Docker Container, KEINE echte Infrastruktur.                         |
|    Externe Grenzen (DB, S3, DIC etc.) sind gemockt.                           |
+===============================================================================+
```

---

## Verantwortlichkeit

Der **COMPONENT-CODER** Actor hat eine einzige Verantwortung:

**Component Tests via Red-Green-Refactor schreiben (mehrere Klassen zusammen)**

Was der Component-Coder **TUT**:
- Mehrere interne Klassen zusammen testen (z.B. Service + Provider)
- Externe Grenzen mocken (DB, S3, DIC etc.)
- Red-Green-Refactor Zyklus fuer Component Tests
- Internes Wiring zwischen Klassen herstellen
- Uncle Bob MCP bei Unsicherheit befragen (in-loop)
- Manifest nach jedem gruenen Test aktualisieren

Was der Component-Coder **NICHT TUT**:
- Unit Tests schreiben (-> /_I_codeAtomic, bereits abgeschlossen)
- Docker Container starten (-> /_I_codePartialSystem)
- Echte Infrastruktur nutzen (-> /_I_codePartialSystem)
- Architektur planen (-> /_I_cleanCodeSlice)

---

## Pipeline-Position

```
CODEATOMIC -> **CODECOMPONENT** -> CODEPARTIALSYSTEM -> CODESINGLESLICE
                    |
                    v
              Component Tests
              COMPONENT-{SLICE}.md
```

**Prev:** /_I_codeAtomic (Unit Tests + Production Code)
**Next:** /_I_codePartialSystem (Partial System Tests mit Docker)

**Eskalation:** Bei Stagnation (5+ RGR ohne Fortschritt) -> /_SC_observe

---

## Abgrenzung Stufe 1 (Atomic) vs Stufe 2 (Component)

| Kriterium | Stufe 1 Atomic | Stufe 2 Component |
|-----------|---------------|-------------------|
| **Scope** | 1 Klasse | Mehrere Klassen |
| **Mocking** | Alles gemockt | Nur externe Grenzen |
| **Ziel** | Klasse funktioniert isoliert | Klassen funktionieren zusammen |
| **Beispiel** | ProviderTest (DB gemockt) | Service + Provider (DB gemockt) |
| **Docker** | Nein | Nein |

---

## Schritt 0: Voraussetzungen pruefen

1. Lies _manifest.md -> Pruefe Atomic Status fuer {SLICE}
2. Lies ATOMIC-{SLICE}.md -> Alle Unit Tests gruen?
3. Falls NICHT:
   -> ABBRUCH: "/_I_codeAtomic {SLICE} muss zuerst abgeschlossen werden"

---

## Schritt 1: RGR-Loop (Component Tests)

Identisch zu /_I_codeAtomic RGR-Loop, aber:
- Tests kombinieren mehrere reale Klassen
- Nur externe Abhaengigkeiten (DB, S3, HTTP) werden gemockt
- Interne Interfaces werden mit echten Implementierungen verdrahtet

---

## Output-Format: COMPONENT-{SLICE}.md

**Pfad:** `.claude/analysis/synthese/{NAME}-COMPONENT-{SLICE}.md`

```markdown
---
name: {NAME}
slice: {SLICE_NAME}
phase: component
pipeline: implementation
date: {YYYY-MM-DD}
reads: plans/{NAME}-{SLICE}-PLAN.md, synthese/{NAME}-ATOMIC-{SLICE}.md
status: final
---

# Component: {NAME} - {SLICE_NAME}

**Feature:** {NAME}
**Slice:** {SLICE_NAME}
**Tests geschrieben:** {N} Component Tests

## Test-Ergebnisse

| # | Test | Klassen | Status | RGR-Zyklen |
|---|------|---------|--------|-----------|
| CT1 | {Test-Name} | {Klassen} | GRUEN | 1 |

## Naechster Schritt

/_I_codePartialSystem {SLICE_NAME}
```

---

## Kompakt-Sicherheit

Nach JEDEM gruenen Component Test:
- State: Manifest mit CT-Fortschritt aktualisiert
- Resume: Naechster CT aus PLAN.md + Manifest-Status

---

## Siehe auch

- [[I_codeAtomic]] - Vorheriger Schritt (Unit Tests)
- [[I_codePartialSystem]] - Naechster Schritt (Partial System Tests)
- [[I_cleanCodeSlice]] - PLAN.md mit Component Test-Liste
