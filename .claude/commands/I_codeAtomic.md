# /_I_codeAtomic

**Status:** NEU v3.0 (Implementierungs-Pipeline Phase 3)
**Actor:** ATOMARER CODER
**Zweck:** Unit Tests + Production Code via Red-Green-Refactor (30-Sekunden-Zyklen)

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_I_codeAtomic {SLICE_NAME}                                    ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                ║
║    1. .claude/analysis/_manifest.md                                      ║
║    2. .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md                      ║
║       → Test-Liste (SOLL-Model, Kent Beck Style)                        ║
║       → Architektur-Entscheidungen (DIP, Interfaces)                    ║
║       → Pattern Reuse (Blueprint aus Horizontaler Suche)                ║
║    3. .claude/patterns/_pattern-library.md (Blueprint-Vorlage)          ║
║    4. Codebase (Produktion + bestehende Tests)                          ║
║    5. MCP Clean Code (Uncle Bob In-Loop Guidance)                        ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    1. Code: Unit Tests (*.spec.ts / *Tests.cs)                          ║
║    2. Code: Production Code (Minimal, durch Tests getrieben)            ║
║    3. .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md                 ║
║       → Abgeschlossene Test-Liste (alle Tests mit Status)              ║
║       → RGR-Zyklen Protokoll (Anzahl, Dauer-Klasse)                   ║
║       → Refactoring-Entscheidungen dokumentiert                         ║
║       → Pattern Library Updates (falls neue Patterns)                   ║
║    4. .claude/analysis/_manifest.md (nach JEDEM gruenen Test update)    ║
║                                                                          ║
║  SCHREIBT (Output) - OPTIONAL:                                           ║
║    .claude/patterns/_pattern-library.md (Update nach Refactor)          ║
║    .claude/_parking-lot.md (APPEND, falls Incidental Findings)          ║
║                                                                          ║
║  MCP INTEGRATION (IN-LOOP):                                              ║
║    - mcp__cleancoder__query() bei Unsicherheit WAEHREND TDD             ║
║    - Query Topics:                                                       ║
║      * "how to test {specific component behavior}"                      ║
║      * "refactoring {specific code smell}"                              ║
║      * "design pattern for {emerging structure}"                        ║
║                                                                          ║
║  MCP-BREMSE:                                                             ║
║    ┌─────────────────────────────────────────────────────────┐           ║
║    │  IMMER MIN-Modus → max 1 Query, limit=1                │           ║
║    │  Ausfuehrende Phase: NUR bei echter Unsicherheit fragen │           ║
║    │  Modi:  min=1Q/1R  middle=3Q/3R  max=5Q/5R            │           ║
║    └─────────────────────────────────────────────────────────┘           ║
║                                                                          ║
║  RED-GREEN-REFACTOR LOOP:                                                ║
║    Fuer JEDEN Test aus PLAN.md:                                          ║
║      RED:      Test schreiben (MUSS fehlschlagen)                       ║
║      GREEN:    MINIMALER Code (MUSS Test bestehen)                      ║
║      REFACTOR: Code bereinigen (Patterns anwenden, DRY)                ║
║      CHECKPOINT: Manifest aktualisieren                                  ║
║                                                                          ║
║  PIPELINE-POSITION:                                                      ║
║    [/_I_cleanCodeSlice] → [/_I_codeAtomic] → [/_I_codeIntegration]        ║
║                                                                          ║
║  ACTOR: ATOMARER CODER                                                   ║
║    Schreibt Unit Tests + Production Code via TDD.                       ║
║    Folgt strikt dem Red-Green-Refactor Zyklus.                          ║
║    30-Sekunden-Zyklen, emergentes Design.                               ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

Der **ATOMARE CODER** Actor hat eine einzige Verantwortung:

**Unit Tests + Production Code via Red-Green-Refactor schreiben**

Was der Atomare Coder **TUT**:
- ✅ Unit Tests schreiben (RED Phase)
- ✅ Minimalen Production Code schreiben (GREEN Phase)
- ✅ Code refactoren (REFACTOR Phase)
- ✅ Blueprint aus PLAN.md als Vorlage nutzen
- ✅ Pattern Library aktualisieren (nach erfolgreichem Refactor)
- ✅ Uncle Bob MCP bei Unsicherheit befragen (in-loop)
- ✅ Manifest nach jedem gruenen Test aktualisieren

Was der Atomare Coder **NICHT TUT**:
- ❌ Integration Tests schreiben (→ /_I_codeIntegration)
- ❌ System Tests schreiben (→ /_I_codeSystem)
- ❌ Architektur planen (→ /_I_cleanCodeSlice)
- ❌ Ueber Unit-Grenzen hinaus testen

---

## Pipeline-Position

```
CLEANCODESLICE → **CODEATOMIC** → CODEINTEGRATION → CODESYSTEM
                      |
                      ↓
                 Unit Tests + Code
                 ATOMIC-{SLICE}.md
```

**Prev:** /_I_cleanCodeSlice (PLAN.md mit Test-Liste)
**Next:** /_I_codeIntegration (Integration Tests)

**Eskalation:** Bei Stagnation (5+ RGR ohne Fortschritt) → /_SC_observe

---

## Uncle Bob's Drei Gesetze des TDD

> **Gesetz 1:** Du darfst keinen Production Code schreiben, bis ein
> Unit Test fehlschlaegt.
>
> **Gesetz 2:** Du darfst nicht mehr Test schreiben als noetig ist,
> um fehlzuschlagen (auch Kompilierfehler zaehlt als Fehlschlag).
>
> **Gesetz 3:** Du darfst nicht mehr Production Code schreiben als
> noetig ist, um den fehlschlagenden Test zu bestehen.

> "Following these three laws will lock you into a cycle that is
> perhaps 30 seconds long."

---

## Schritt 0: Inputs lesen

1. Lies `_manifest.md` → aktueller {NAME}, Slice-Status
2. Lies `plans/{NAME}-{SLICE}-PLAN.md`
   - Test-Liste (SOLL-Model)
   - Test-Reihenfolge (Outside-In)
   - Blueprint (aus Horizontaler Suche)
   - Architektur-Entscheidungen (Interfaces)
3. Lies `_pattern-library.md` (falls vorhanden)
   - Blueprint-Code als Vorlage
4. Pruefe: Welche Tests sind bereits abgeschlossen? (Resume-Faehigkeit)

---

## Schritt 1: RGR-Loop (Hauptschleife)

### Fuer JEDEN Test aus PLAN.md Test-Liste:

```
╔═══════════════════════════════════════════════════════╗
║  RED-GREEN-REFACTOR ZYKLUS (30 Sekunden)              ║
╠═══════════════════════════════════════════════════════╣
║                                                        ║
║  ┌─────────────────────────────────────┐               ║
║  │  RED: Test schreiben                 │               ║
║  │  - 1 Test aus PLAN.md nehmen        │               ║
║  │  - Test MUSS fehlschlagen           │               ║
║  │  - Kompilierfehler = fehlgeschlagen │               ║
║  └─────────────┬───────────────────────┘               ║
║                │                                        ║
║                ▼                                        ║
║  ┌─────────────────────────────────────┐               ║
║  │  GREEN: Minimaler Code              │               ║
║  │  - NUR genug Code um Test zu passen │               ║
║  │  - NICHT elegant, NICHT vollstaendig│               ║
║  │  - "Fake it till you make it"       │               ║
║  │  - Blueprint als Vorlage nutzen     │               ║
║  └─────────────┬───────────────────────┘               ║
║                │                                        ║
║                ▼                                        ║
║  ┌─────────────────────────────────────┐               ║
║  │  REFACTOR: Code bereinigen          │               ║
║  │  - DRY: Duplikate eliminieren       │               ║
║  │  - Extract Method/Class             │               ║
║  │  - Naming verbessern                │               ║
║  │  - Pattern Library pruefen          │               ║
║  │  - ALLE Tests muessen GRUEN bleiben │               ║
║  └─────────────┬───────────────────────┘               ║
║                │                                        ║
║                ▼                                        ║
║  ┌─────────────────────────────────────┐               ║
║  │  CHECKPOINT: Manifest Update        │               ║
║  │  - Test als abgeschlossen markieren │               ║
║  │  - Compact-Safe nach jedem Test     │               ║
║  └─────────────────────────────────────┘               ║
║                                                        ║
╚═══════════════════════════════════════════════════════╝
```

### RED Phase (Detail)

```
1. Nimm naechsten Test aus PLAN.md Test-Liste
2. Schreibe den Test:
   - Arrange: Setup (Mocks, Testdaten)
   - Act: Methoden-Aufruf
   - Assert: Erwartetes Verhalten
3. Fuehre den Test aus
4. VERIFIZIERE: Test MUSS fehlschlagen
   - Falls Test sofort gruen: Test ist trivial oder falsch
   - Ueberdenke den Test
5. Dokumentiere: "RED: {Test-Name} fehlgeschlagen weil {Grund}"
```

### GREEN Phase (Detail)

```
1. Schreibe MINIMALEN Code um Test zu passen
2. REGELN:
   - Fake Daten sind OK ("Fake it till you make it")
   - Hardcoded Werte sind OK (werden spaeter refactored)
   - Keine Extras, keine Eleganz
   - Blueprint aus PLAN.md als Struktur-Vorlage
3. Fuehre den Test aus
4. VERIFIZIERE: Test MUSS gruen sein
   - Falls nicht gruen: Debug, minimal anpassen
5. VERIFIZIERE: ALLE bisherigen Tests MUESSEN gruen bleiben
6. Dokumentiere: "GREEN: {Test-Name} bestanden mit {Beschreibung}"
```

### REFACTOR Phase (Detail)

```
1. ALLE Tests sind gruen (Voraussetzung!)
2. Bereinige Code:
   - DRY: Duplikate zwischen Produktionscode eliminieren
   - Extract Method: Lange Methoden aufteilen
   - Extract Class: Grosse Klassen aufteilen
   - Rename: Bessere Namen verwenden
   - Move: Code in richtige Layer verschieben
3. Bereinige Tests:
   - DRY: Duplikate zwischen Tests eliminieren
   - Setup-Methoden extrahieren
   - Test-Helper erstellen
4. Pattern-Check:
   - Entsteht ein bekanntes Pattern? (aus Pattern Library)
   - Neues Pattern erkannt? → Kandidat fuer Library Update
5. Fuehre ALLE Tests aus
6. VERIFIZIERE: ALLE Tests MUESSEN gruen bleiben
7. Dokumentiere: "REFACTOR: {Was bereinigt, welches Pattern}"
```

---

## Schritt 2: MCP In-Loop Guidance (bei Bedarf)

### Wann Uncle Bob fragen?

| Situation | Query |
|-----------|-------|
| Unsicher wie testen | "how to test {behavior}" |
| Code Smell erkannt | "refactoring {smell description}" |
| Pattern entsteht | "design pattern for {structure}" |
| Stuck (>3 Versuche) | "getting unstuck in TDD {problem}" |

### Beispiel In-Loop Query

```python
# Waehrend REFACTOR, wenn Pattern entsteht:
mcp__cleancoder__query(
    "design pattern for separating {high-level policy}
     from {low-level detail}, strategy vs template method"
)
```

---

## Schritt 3: Stagnations-Erkennung

### Stagnations-Zaehler

```
RGR_OHNE_FORTSCHRITT = 0

Nach jedem RGR-Zyklus:
  Falls Test neu gruen → RGR_OHNE_FORTSCHRITT = 0
  Falls Test NICHT gruen → RGR_OHNE_FORTSCHRITT += 1

Schwellen:
  <= 3: NORMAL (weitermachen)
  4:    WARNUNG (Uncle Bob MCP befragen)
  5+:   ESKALATION (→ wissenschaftlicher Zyklus)
```

### Eskalations-Pfad

```
/_I_codeAtomic stagniert (5+ RGR ohne Fortschritt)
    │
    ├── MCP Query: "getting unstuck in TDD for {problem}"
    │
    ├── Falls MCP hilft → weitermachen
    │
    └── Falls weiterhin stuck:
        → /_SC_observe (System verstehen)
        → /_SC_modelMaintain (Model aktualisieren)
        → /_SC_hypothese (neue Hypothese)
        → zurueck zu /_I_codeAtomic
```

---

## Output-Format: ATOMIC-{SLICE}.md

**Pfad:** `.claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md`

```markdown
---
name: {NAME}
slice: {SLICE_NAME}
phase: atomic
pipeline: implementation
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
date: {YYYY-MM-DD}
reads: plans/{NAME}-{SLICE}-PLAN.md
status: final
---

# Atomic: {NAME} - {SLICE_NAME}

**Feature:** {NAME}
**Slice:** {SLICE_NAME}
**RGR-Zyklen:** {N}
**Tests geschrieben:** {N} Unit Tests
**Production Code:** {N} Dateien, {M} LOC

## Test-Ergebnisse

| # | Test | Status | RGR-Zyklen | Pattern |
|---|------|--------|-----------|---------|
| T1 | {Test-Name} | ✅ GRUEN | 1 | GRAY (Blueprint) |
| T2 | {Test-Name} | ✅ GRUEN | 2 | ORANGE (Angepasst) |
| T3 | {Test-Name} | ✅ GRUEN | 1 | RED (Custom) |

## RGR-Protokoll

### T1: {Test-Name}
- RED: Test geschrieben, fehlgeschlagen weil {Grund}
- GREEN: {Beschreibung des minimalen Codes}
- REFACTOR: {Was bereinigt}

### T2: {Test-Name}
- RED: ...
- GREEN: ...
- REFACTOR: ...

## Refactoring-Entscheidungen

| # | Refactoring | Begruendung | Pattern |
|---|-------------|-------------|---------|
| 1 | Extract Method: {Name} | DRY | - |
| 2 | Extract Interface: I{Name} | DIP | Strategy |

## Pattern Library Updates

| Pattern | Aktion | Begruendung |
|---------|--------|-------------|
| {Pattern} | NEU / AKTUALISIERT | {Beschreibung} |

## Naechster Schritt

/_I_codeIntegration {SLICE_NAME}
```

---

## Manifest-Update (nach JEDEM gruenen Test)

```markdown
**PHASE:** _I_codeAtomic {SLICE_NAME}
**PIPELINE:** Implementation
**TESTS:** {N}/{M} gruen (T1 ✅, T2 ✅, T3 🔄, T4 ⏳, T5 ⏳)
**NAECHSTER TEST:** T{N+1}: {Test-Name}
**STAGNATION:** {RGR_OHNE_FORTSCHRITT}
**LETZTER GRUENER TEST:** {Datum, T{N}}

### Atomic Progress - {SLICE_NAME}
- [x] T1: {Test-Name} (RGR: 1)
- [x] T2: {Test-Name} (RGR: 2)
- [ ] T3: {Test-Name} (IN ARBEIT)
- [ ] T4: {Test-Name}
- [ ] T5: {Test-Name}
```

**COMPACT-SICHER:** Nach jedem gruenen Test kann /compact ausgefuehrt werden.
Resume liest Manifest → weiss welcher Test als naechstes dran ist.

---

## Qualitaetskriterien

- **Drei Gesetze TDD:** Strikt eingehalten
- **RED:** Jeder Test MUSS fehlschlagen bevor GREEN
- **GREEN:** MINIMALER Code (kein Over-Engineering)
- **REFACTOR:** Nach JEDEM gruenen Test (nicht aufschieben!)
- **ALLE Tests gruen:** Nach jedem Schritt ALLE Tests ausfuehren
- **Blueprint genutzt:** Pattern aus PLAN.md als Vorlage
- **Manifest aktuell:** Nach jedem gruenen Test
- **Stagnation erkannt:** Bei 5+ RGR ohne Fortschritt eskalieren
- **Tests lesen wie Spezifikationen:** Klare Namen, Arrange-Act-Assert

---

## Kompakt-Sicherheit

Nach JEDEM gruenen Test:
- State: Manifest mit Test-Fortschritt aktualisiert
- Resume: Naechster Test aus PLAN.md + Manifest-Status

**Granularitaet:** Jeder einzelne Test ist ein Compact-Checkpoint.
Das ist feiner als im wissenschaftlichen Zyklus (dort: Welle = Checkpoint).

---

## Obsidian-Tags

```yaml
tags:
  - type/atomic
  - pipeline/implementation
  - op/{FEATURE}
  - topic/TDD
  - topic/Unit-Tests
  - topic/Red-Green-Refactor
pipeline-position: atomic
prev: [[I_cleanCodeSlice]]
next: [[I_codeIntegration]]
slice: {SLICE_NAME}
```

---

## Siehe auch

- [[I_cleanCodeSlice]] - Vorheriger Schritt (PLAN.md mit Test-Liste)
- [[I_codeIntegration]] - Naechster Schritt (Integration Tests)
- [[SC_implement]] - Bestehender Implement-Command (wissenschaftlicher Zyklus)
- [[SC_observe]] - Eskalation bei Stagnation
