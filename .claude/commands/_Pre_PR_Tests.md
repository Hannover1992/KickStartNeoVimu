---
type: building-block
---

# /_Pre_PR_Tests - Test-Klassen Quality Gate

**Version:** 1.0
**Schwierigkeit:** EASY
**Ceiling:** sonnet
**Floor:** haiku
**Auto-Fix:** JA

## Vertrag

```
+---------------------------------------------------------------------+
|  /_Pre_PR_Tests - TestBase-Ableitung Quality Gate                  |
+---------------------------------------------------------------------+
|  LIEST:                                                             |
|    - git diff --name-only develop...HEAD (*.cs in *Tests* Projekten) |
|    - {META}/codeKonvention/testbase.md                        |
|    - Test-Dateien im DIRTY-Scope                                    |
|                                                                     |
|  SCHREIBT:                                                          |
|    - Test-Dateien (Auto-Fix: TestBase-Vererbung)                    |
|    - .claude/reports/pre_pr_tests_YYYYMMDD_HHMMSS.md                |
|                                                                     |
|  BEDINGUNGEN:                                                       |
|    PRE:  - Git-Repository vorhanden                                 |
|          - Mindestens 1 geaenderte *.cs Test-Datei                  |
|    POST: - Alle Test-Klassen erben von TestBase<T>                  |
|          - Kein sealed Modifier bei Test-Klassen                    |
|          - Keine _sut Fields (nur Sut Property)                     |
+---------------------------------------------------------------------+
```

## Zweck

Automatische Pruefung und Korrektur von Test-Klassen vor Pull Requests:
- **R1:** Test-Klassen muessen von `TestBase<T>` erben (BLOCKER)
- **R2:** Kein `sealed` Modifier (WARNUNG)
- **R3:** `_sut` Field durch `Sut` Property ersetzen (WARNUNG)
- **R4:** Logiklose Tests erkennen → ENTFERNEN markieren (WARNUNG)

**R4 — Logiklose Tests:**
Tests die NUR Framework-Verhalten verifizieren haben keinen Wert.
Sie blaehen die Test-Suite auf und erzeugen falsches Sicherheitsgefuehl.

```
LOGIKLOS wenn ALLE diese Kriterien zutreffen:
  1. Arrange: Nur Properties setzen (kein Setup mit Logik)
  2. Act: Nur ein Framework-Aufruf (mapper.Map, container.Resolve)
  3. Assert: Nur Assert.Equal(input.Prop, output.Prop)
  → Kein eigener Production-Code wird getestet

TYPISCHE MUSTER:
  ✗ AutoMapper: entity.Prop → mapper.Map → bo.Prop (reines Property-Mapping)
  ✗ DI-Container: services.GetService<T>() != null
  ✗ Getter/Setter: obj.Prop = X; Assert.Equal(X, obj.Prop)
  ✗ DTO-Konstruktor: new Dto() → Assert Defaults

NICHT LOGIKLOS (behalten!):
  ✓ Mapping MIT Konvertierung (string → enum, Datum → Format)
  ✓ Mapping MIT Bedingung (wenn X dann Y sonst Z)
  ✓ Mapping MIT Berechnung (Summe, Aggregation)
  ✓ Tests die bei Entfernung keinen Production-Code-Coverage-Verlust haben
    → ABER: wenn sie Randfall-Verhalten testen → behalten
```

Verhindert 27+ wiederkehrende Review-Kommentare.

## DIRTY-Scope Ermittlung

```bash
# Geaenderte Test-Dateien im Branch (gegen develop)
git diff --name-only develop...HEAD | findstr /i "Tests.*\.cs$"

# Falls immernoch leer: alle Test-Dateien
dir /s /b *Tests\*.cs
```

**Scope-Filter:**
- Nur `*.cs` Dateien
- Nur in Projekten mit `Tests` im Namen
- Nur tatsaechlich geaenderte Dateien (git diff)

## Ablauf

### Phase 0: Initialisierung

```markdown
1. DIRTY-Scope ermitteln (git diff Test-Dateien)
2. Konventions-Metadatei laden ({META}/codeKonvention/testbase.md)
3. Falls keine Test-Dateien: EXIT mit INFO
```

### Welle 1: Analyse (Haiku)

**Agent:** haiku
**Aufgabe:** Schnelles Scanning aller Test-Dateien

```markdown
FUER JEDE Test-Datei im DIRTY-Scope:
  1. Datei einlesen
  2. Pruefen:
     - [ ] Erbt von TestBase<T>? (R1)
     - [ ] Hat sealed Modifier? (R2)
     - [ ] Hat _sut Field? (R3)
     - [ ] Enthaelt logiklose Tests? (R4)
  3. R4-Pruefung pro Test-Methode:
     → Arrange: Nur Property-Zuweisungen?
     → Act: Nur Framework-Aufruf (Map, Resolve, Get)?
     → Assert: Nur Assert.Equal(input.Prop, output.Prop)?
     → Wenn ALLE drei JA → Test ist LOGIKLOS
  4. Klassifizierung:
     - CLEAN: Alle Regeln erfuellt, keine logiklosen Tests
     - FIXABLE: R1/R2/R3 verletzt, Auto-Fix moeglich
     - BLOCKER: R1 verletzt
     - ENTFERNEN: R4 — logiklose Test-Methoden gefunden

OUTPUT: JSON-Liste
[
  {
    "file": "path/to/FooTests.cs",
    "class": "FooTests",
    "status": "FIXABLE",
    "violations": ["R1", "R2", "R3"],
    "sut_type": "FooController"
  },
  {
    "file": "path/to/BarMappingTests.cs",
    "class": "BarMappingTests",
    "status": "ENTFERNEN",
    "violations": ["R4"],
    "logiklose_tests": ["T15_Map_LockedBy", "T16_Map_LockedAt"],
    "grund": "Reines AutoMapper Property-Mapping ohne Logik"
  }
]
```

### Welle 2: Batch-Fix (Haiku/Sonnet)

**Strategie:** 1 Agent = 1 Datei, parallel

**FUER JEDE Datei mit Status=FIXABLE:**

```markdown
Agent: haiku (EASY Pattern-Ersetzung)

Schritt 1: Using hinzufuegen
  - Pruefen: `using VDEK.DCSP.Test;` vorhanden?
  - Falls NEIN: Nach letztem using einfuegen

Schritt 2: TestBase-Vererbung (R1)
  - Suchen: `public (sealed )?class (\w+Tests?) : `
  - Ersetzen: `: TestBase<{sut_type}>, ` (vor anderen Interfaces)
  - Falls keine Vererbung: `: TestBase<{sut_type}>` anhaengen

Schritt 3: sealed entfernen (R2)
  - Suchen: `public sealed class`
  - Ersetzen: `public class`

Schritt 4: _sut Field ersetzen (R3)
  - Suchen: `private readonly {sut_type} _sut;`
  - Loeschen: Diese Zeile
  - Suchen: `_sut = new {sut_type}(`
  - Ersetzen: `Sut = new {sut_type}(`
  - Suchen: `_sut.` (alle Vorkommen)
  - Ersetzen: `Sut.`

Schritt 5: Validierung
  - Pruefen: TestBase-Vererbung vorhanden
  - Pruefen: Kein sealed Modifier
  - Pruefen: Kein _sut Field
  - Falls PASS: Status = FIXED
  - Falls FAIL: Status = MANUAL_REVIEW
```

### Phase 3: Reporting

**Agent:** haiku
**Output:** `.claude/reports/pre_pr_tests_YYYYMMDD_HHMMSS.md`

```markdown
# Pre-PR Quality Gate: Tests
**Datum:** 2026-02-06 14:30:00
**Scope:** 12 Test-Dateien (git diff)

## Zusammenfassung
- CLEAN: 4 Dateien (33.3%)
- FIXED: 5 Dateien (41.7%)
- ENTFERNEN: 2 Dateien / 8 Tests (16.7%)
- BLOCKER: 1 Datei (8.3%)

## Details

### FIXED (5)
1. FooControllerTests.cs
   - [x] R1: TestBase<FooController> hinzugefuegt
   - [x] R2: sealed entfernt
   - [x] R3: _sut durch Sut ersetzt

### ENTFERNEN (2 Dateien, 8 logiklose Tests)
1. DicFileImportMappingTests.cs — 8 Test-Methoden
   - R4: Reines AutoMapper Property-Mapping (Entity↔BO)
   - Tests: T15-T22 (LockedBy, LockedAt, ErrorMessage, RetryCount x2)
   - Grund: Kein eigener Production-Code — nur mapper.Map() + Assert.Equal
   - Action: Gesamte Datei entfernen oder Tests loeschen
2. ConfigDtoMappingTests.cs — 3 Test-Methoden
   - R4: DTO → Config Property-Mapping
   - Action: Test-Methoden loeschen

### BLOCKER (1)
1. BarServiceTests.cs
   - [ ] R1: Komplexe Vererbungs-Hierarchie (MANUAL)
   - Grund: Erbt bereits von CustomTestBase
   - Action: Christian fragen

## Qualitaetskriterien
- [x] Alle Auto-Fixable Violations behoben
- [ ] BLOCKER vorhanden -> PR NICHT READY

## Naechste Schritte
1. BLOCKER manuell beheben
2. /_Pre_PR_Tests erneut ausfuehren
3. Bei PASS: git add + commit + push
```

## Qualitaetskriterien

### PASS (PR Ready)
- [ ] Alle Test-Dateien CLEAN oder FIXED
- [ ] Keine BLOCKER
- [ ] 100% TestBase-Vererbung
- [ ] 0% sealed Test-Klassen
- [ ] 0% _sut Fields

### FAIL (PR Blocked)
- [ ] Mindestens 1 BLOCKER vorhanden
- [ ] Auto-Fix fehlgeschlagen (MANUAL_REVIEW)
- [ ] Git-Konflikte nach Fix

## Error Handling

### Fehler 1: Kein Git-Repository
```
ERROR: Kein Git-Repository gefunden
ACTION: In Repository-Root wechseln
EXIT: 1
```

### Fehler 2: Keine geaenderten Test-Dateien
```
INFO: Keine Test-Dateien im DIRTY-Scope
ACTION: Keine
EXIT: 0
```

### Fehler 3: Auto-Fix fehlgeschlagen
```
WARNUNG: Auto-Fix fehlgeschlagen fuer FooTests.cs
REASON: Komplexe Vererbungs-Hierarchie
ACTION: Status = MANUAL_REVIEW
CONTINUE: Ja (andere Dateien weiter fixen)
```

### Fehler 4: Konventions-Datei fehlt
```
ERROR: {META}/codeKonvention/testbase.md nicht gefunden
ACTION: Datei erstellen (Template verwenden)
EXIT: 1
```

## Beispiel-Ausfuehrung

```
USER: /_Pre_PR_Tests

ASSISTANT:
Phase 0: Initialisierung
  - DIRTY-Scope: 12 Test-Dateien (git diff)
  - Konventions-Metadatei: testbase.md geladen

Welle 1: Analyse (haiku)
  - 12 Dateien gescannt
  - CLEAN: 5, FIXABLE: 6, BLOCKER: 1

Welle 2: Batch-Fix (6 Agents parallel)
  [haiku-1] FooControllerTests.cs -> FIXED
  [haiku-2] BarServiceTests.cs -> BLOCKER (Custom-Base)
  [haiku-3] BazRepositoryTests.cs -> FIXED
  [haiku-4] QuxHandlerTests.cs -> FIXED
  [haiku-5] QuuxValidatorTests.cs -> FIXED
  [haiku-6] CorgeMapperTests.cs -> FIXED

Phase 3: Reporting
  - Report: .claude/reports/pre_pr_tests_20260206_143000.md

ERGEBNIS: 1 BLOCKER -> PR NICHT READY
NAECHSTER SCHRITT: BarServiceTests.cs manuell pruefen
```

## Integration in Workflow

```bash
# Vor jedem Pull Request
1. git add .
2. /_Pre_PR_Tests
3. Falls PASS: git commit -m "..." && git push
4. Falls FAIL: BLOCKER beheben, goto 2
```

## Metriken

- **Review-Zeit gespart:** ~5 Minuten pro PR (27 Kommentare vermieden)
- **Auto-Fix-Rate:** ~85% (15% MANUAL_REVIEW)
- **Durchlaufzeit:** <30 Sekunden fuer 10 Test-Dateien
- **False-Positive-Rate:** <5%

## Erweiterungen (Future)

- [x] R4: Logiklose Tests erkennen → ENTFERNEN (v1.1, implementiert)
- [ ] R5: Test-Naming-Convention (`Should_When_` Pattern)
- [ ] R6: Assert-Message-Pflicht
- [ ] R7: IDisposable bei TestBase (redundant)
- [ ] Integration in CI/CD Pipeline (Pre-Commit Hook)
