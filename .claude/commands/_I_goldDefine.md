# /_I_goldDefine — Gold-Definition & Akzeptanzkriterien

```yaml
status: active
version: 1.0.0
created: 2026-03-08
updated: 2026-03-08
op: GoldDefine
phase: Architect
type: building-block
chain_position: architect-3-of-5
team_based: false
```

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_I_goldDefine {NAME} --stufe {N}                         ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                            ║
║    1. {VAULT}/_manifest.md                                  ║
║       (Pipeline-State, Blueprint-Pfad)                               ║
║    2. .claude/meta/implementation/stage_{N}.md                       ║
║       (Stufen-Perspektive, Testtyp, Mock-Regeln — bestimmt            ║
║        was "messbar" heisst: Unit-Assertion vs E2E-Journey)           ║
║    3. .claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md        ║
║       (Architektur + ## Test-Inventar von testSearch)                 ║
║    4. .claude/specs/{NAME}_Spec.md                                   ║
║       (Akzeptanzkriterien — WANN ist Feature DONE, BL-008)           ║
║    5. {VAULT}/Task.md                                                ║
║       (Task-Definition — Aufgaben-Kontext)                           ║
║                                                                      ║
║  SCHREIBT (Output) - PFLICHT:                                        ║
║    .claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md           ║
║      UPDATE: ## Gold-Definition                                      ║
║      UPDATE: ## Kanarienvoegel (aus Test-Inventar Kategorie K)       ║
║      UPDATE: ## Nicht-Ziele                                          ║
║    {VAULT}/_manifest.md                                     ║
║      s{N}_goldDefine: done                                           ║
║      s{N}_goldDefine_at: "{DATUM}"                                   ║
║                                                                      ║
║  HAUPTPRODUKT:                                                       ║
║    Aktualisierter Blueprint mit Gold-Definition, Kanarienvoegel      ║
║    und Nicht-Zielen                                                   ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    - Aendert NUR die 3 genannten Sektionen                           ║
║    - Loescht KEINE anderen Blueprint-Sektionen                       ║
║    - Schreibt KEINE Tests, aendert KEINEN Code                       ║
║    - Gold-Definition MUSS messbar sein (nicht "gut genug")           ║
║                                                                      ║
║  PIPELINE-POSITION:                                                  ║
║    [testSearch] -> [goldDefine] -> [patternLibrary]                  ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
/_I_goldDefine {NAME} --stufe {N}

Parameter:
  NAME:    Feature-Name (PFLICHT)
  --stufe: Teststufe 1-5 (PFLICHT)

Beispiele:
  /_I_goldDefine DCSRE-881 --stufe 1   -> Gold fuer Unit-Tests
  /_I_goldDefine DCSRE-31 --stufe 5    -> Gold fuer E2E Journey
```

---

## Gold-Formel

```
GOLD = Kanarienvogel GRUEN
     + Betroffene Tests ANGEPASST und GRUEN
     + Neue Tests (aus TDD-Zyklus) GRUEN
     + Alle Akzeptanzkriterien (aus SPEC) ERFUELLT

GOLD ist die Antwort auf: "WANN hoere ich auf?"
Ohne Gold arbeitet man endlos weiter oder hoert zu frueh auf.
```

---

## Ablauf

### Schritt 1: Kontext laden

```
1. Lies blueprint.md:
   - ## Architektur (Slices, Layer)
   - ## Test-Inventar (Kanarienvogel, Boundary, Betroffen aus Schritt 2)

2. Lies SPEC.md:
   - Akzeptanzkriterien (AK) fuer das Feature
   - Welche AK sind fuer diese Stufe relevant?

3. Lies Task.md:
   - Aufgaben-Kontext (was wurde angefragt?)
```

### Schritt 2: Gold-Definition pro Slice

```
Fuer JEDEN Slice aus blueprint.md ## Architektur:

  1. Welche AK aus der SPEC betreffen diesen Slice?
     → Zuordnung: AK-{N} → Slice-{M}

  2. Messbare Exit-Kriterien formulieren:
     - NICHT: "Controller funktioniert"
     - SONDERN: "GET /api/tickets → 200, Response enthaelt ticketId"
     - Jedes Kriterium MUSS als Test-Assertion formulierbar sein

  3. Kanarienvogel fuer diesen Slice (aus Test-Inventar Kategorie K):
     - Welche K-Tests gehoeren zu DIESEM Slice?
     - Diese MUESSEN bei jedem TDD-Execute mitleufen

  4. Betroffene Tests fuer diesen Slice (aus Test-Inventar Kategorie A):
     - Welche A-Tests gehoeren zu DIESEM Slice?
     - Diese MUESSEN im TDD-Zyklus angepasst werden
     - DANACH muessen sie wieder GRUEN sein
```

### Schritt 3: Nicht-Ziele definieren

```
Fuer JEDEN Slice:
  Was gehoert NICHT zum Scope dieser Stufe?

  Typische Nicht-Ziele:
    - Performance-Optimierung (ausser explizit in AK)
    - Refactoring bestehenden Codes (ausser betroffen)
    - UI-Polish (bei Backend-Stufen)
    - Andere Features die zufaellig nahe liegen

  WARUM Nicht-Ziele?
    Verhindert Scope Creep im TDD-Zyklus.
    Worker weiss: "Das gehoert nicht zu meinem Gold."
```

### Schritt 4: Blueprint aktualisieren

Schreibe/ersetze die 3 Sektionen im Blueprint:

```markdown
## Gold-Definition

<!-- Erstellt von _I_goldDefine, {DATUM} -->
<!-- SPEC-Basis: {SPEC-Datei} -->

### Gold pro Slice

| Slice | AK-Bezug | Exit-Kriterium | Messbar als |
|-------|----------|----------------|-------------|
| {Slice1} | AK-{N} | {Kriterium} | {Test-Assertion} |
| {Slice1} | AK-{M} | {Kriterium} | {Test-Assertion} |
| {Slice2} | AK-{K} | {Kriterium} | {Test-Assertion} |

### Gold-Formel (Zusammenfassung)

GOLD = {K} Kanarienvogel GRUEN
     + {A} betroffene Tests ANGEPASST
     + {E} neue Exit-Kriterien ERFUELLT

## Kanarienvoegel

<!-- Uebernommen aus ## Test-Inventar Kategorie K -->
<!-- Diese Tests MUESSEN bei JEDEM tddExecute mitleufen -->

| Test-Klasse | Slice-Zuordnung | Pfad |
|-------------|----------------|------|
| {Klasse1}   | {Slice1}       | {Pfad} |
| {Klasse2}   | {Slice2}       | {Pfad} |

**Regel:** Kanarienvogel bricht → TDD-Zyklus SOFORT stoppen.

## Nicht-Ziele

| Slice | Nicht-Ziel | Grund |
|-------|-----------|-------|
| {Slice1} | {Was nicht} | {Warum nicht in Scope} |
| {Slice2} | {Was nicht} | {Warum nicht in Scope} |
```

### Schritt 5: Manifest + Exit-Report

```yaml
# Manifest
s{N}_goldDefine: done
s{N}_goldDefine_at: "{DATUM}"
```

```
# SendMessage an team-lead
_I_goldDefine {NAME} --stufe {N}: FINAL
Gold: {E} Exit-Kriterien, {K} Kanarienvogel, {A} betroffene Tests.
Nicht-Ziele: {NZ} Eintraege.
Blueprint aktualisiert.
```

---

## Abgrenzung

- **Sucht KEINE Tests** (-> _I_testSearch hat das bereits gemacht)
- **Schreibt KEINE Tests** (-> TDD-Zyklus)
- **Aendert KEINE Architektur** (-> cleanCodeArchitect)
- **Weist KEINE Patterns zu** (-> _I_patternLibrary)
- **Bewertet NICHT den Blueprint** (-> blueprintQG)

---

## Pipeline-Position

```
[/_I_cleanCodeArchitect]   Schritt 1: Architektur
          |
          v
[/_I_testSearch]           Schritt 2: Test-Suche
          |
          v
[/_I_goldDefine]           Schritt 3: Gold-Definition  <-- DIESER COMMAND
          |
          v
[/_I_patternLibrary]       Schritt 4: Pattern Library
          |
          v
[/_I_blueprintQG]          Schritt 5: Quality Gate
```

**Prev:** `/_I_testSearch` (liefert Test-Inventar mit Kategorien)
**Next:** `/_I_patternLibrary` (sucht passende Patterns fuer Slices)
