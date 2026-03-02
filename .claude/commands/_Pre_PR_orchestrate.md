---
name: _Pre_PR_orchestrate
description: Pre-PR Quality Gates - Team Lead Orchestrierung (9 Gates PARALLEL)
---

# /_Pre_PR_orchestrate - Team Lead Pre-PR Quality Gates

```yaml
status: active
version: 2.0.0
created: 2026-02-18
type: orchestration
team_based: true
changelog: |
  v1.0: Sequentielle Gates mit 10 Batch-Agents pro Gate (~27 min)
  v2.0: UMBAU auf Team-basierte parallele Ausfuehrung (9 Gates gleichzeitig, ~14 min)
```

---

## Vertrag

```
+===============================================================+
| META-COMMAND: /_Pre_PR_orchestrate                             |
+===============================================================+
|                                                                |
| ACTOR: TEAM LEAD (DU - die ausfuehrende Claude-Instanz)       |
| WORKER: bis zu 9 {ceiling}-Agents (1 pro Gate, PARALLEL)      |
|                                                                |
| ZWECK: Alle 9 Pre-PR Quality Gates PARALLEL ausfuehren.       |
|        Team Lead ermittelt Datei-Listen, spawnt Gate-Workers,  |
|        aggregiert Ergebnisse, verifiziert Build+Tests.         |
|                                                                |
| DIFF-BASIS: git diff develop...HEAD (IMMER!)                   |
|                                                                |
| GATES (9 Stueck, alle PARALLEL):                               |
|   1. Tests         → Test-Dateien      (Auto-Fix: JA)         |
|   2. Naming        → CS-Dateien        (Auto-Fix: JA)         |
|   3. Cleanup       → CS-Dateien        (Auto-Fix: JA)         |
|   4. Dokumentation → CS-Dateien        (Auto-Fix: JA)         |
|   5. Konstanten    → CS-Dateien        (Auto-Fix: TEIL)       |
|   6. Logging       → CS-Dateien        (Auto-Fix: JA)         |
|   7. Architektur   → CS-Dateien        (Auto-Fix: NEIN)       |
|   8. Analyzer      → .csproj Dateien   (Auto-Fix: JA)         |
|   9. Migration     → Migration-Dateien (Auto-Fix: NEIN)       |
|                                                                |
| MODELL: {ceiling} (alle Workers)                               |
| PARALLELISIERUNG: ALLE aktiven Gates GLEICHZEITIG              |
|                                                                |
| LIEST:                                                         |
|   - git diff develop...HEAD (Datei-Listen)                     |
|   - .claude/meta/codeKonvention/*.md (Regeln pro Gate)         |
|   - .claude/commands/_Pre_PR_*.md (Command-Specs)              |
|                                                                |
| SCHREIBT:                                                      |
|   - Auto-Fixes in CS/csproj Dateien (parallel!)                |
|   - Summary-Bericht (konsolidiert)                             |
|                                                                |
| PIPELINE:                                                      |
|   [/_I_diffAudit] → [/_Pre_PR_orchestrate] → [PR erstellen]   |
|                                                                |
+===============================================================+
```

---

## GLOBALE PARAMETER (/_param Override)

Lies `.claude/analysis/_manifest.md` und suche nach GLOBAL_* Feldern.

Effektives Gate-Modell: `{ceiling}` (nach GLOBAL_CEILING-Berechnung: min(lokal_ceiling, GLOBAL_CEILING)).
Falls GLOBAL_CEILING = haiku: Alle Gates verwenden haiku.
Falls GLOBAL_CEILING = sonnet: Alle Gates verwenden sonnet.
Falls GLOBAL_CEILING = opus: Alle Gates verwenden opus.

| Manifest-Feld | Wirkung |
|---|---|
| `GLOBAL_DIFFICULTY` | Steuert Gate-Anzahl: easy=TOP-3 Gates, normal/hard=alle 9 Gates |
| `GLOBAL_CEILING` | Konfiguriert Gate-Modell (min-Capping) |
| `GLOBAL_FLOOR` | Nicht anwendbar — kein floor-Konzept bei parallelen Gates |

**Gate-Skalierung nach difficulty:**

| difficulty | Active Gates | Modell | Besonderheit |
|---|---|---|---|
| easy | 3 (Tests, Naming, Cleanup) | {ceiling} | Ressourcen-sparsam |
| normal | 9 (alle) | {ceiling} | Standard |
| hard | 9 (alle) | {ceiling} | + verbose Analyse in Knowledge-Files |

{ceiling} = GLOBAL_CEILING falls gesetzt, sonst lokaler Default (sonnet)

---

## Warum parallel statt sequentiell?

```
ALT (v1.0): Gates SEQUENTIELL wegen Auto-Fix-Kaskade.
  Problem: 27 Minuten Laufzeit. Overkill - Konflikte sind selten.

NEU (v2.0): Gates PARALLEL. Build+Test am Ende als Safety Net.
  - Tests bearbeitet NUR Test-Dateien → kein Konflikt
  - Analyzer bearbeitet NUR .csproj → kein Konflikt
  - Migration/Architektur sind READ-ONLY → kein Konflikt
  - Naming/Cleanup/Doku/Konstanten/Logging editieren verschiedene
    ASPEKTE derselben CS-Dateien (Namen vs Struktur vs Kommentare
    vs Strings vs Logging) → Konflikte extrem selten
  - Build+Test am Ende fangt die seltenen Konflikte ab
```

---

## Phase 0: Datei-Listen + Scope

DU (Team Lead) fuehrst aus:

```bash
# 1. Alle CS-Dateien
git diff --name-only develop...HEAD -- "*.cs"

# 2. Test-Dateien separieren
git diff --name-only develop...HEAD -- "*.cs" | grep -i "test"

# 3. Non-Test CS-Dateien
git diff --name-only develop...HEAD -- "*.cs" | grep -vi "test"

# 4. .csproj Dateien
git diff --name-only develop...HEAD -- "*.csproj"

# 5. Migration-Dateien
git diff --name-only develop...HEAD -- "*Migrations/*.cs"
```

**Gate-Zuordnung + SKIP:**

| Gate | Dateien | Skip wenn |
|------|---------|-----------|
| Tests | Test-Dateien | 0 Test-Dateien |
| Naming..Architektur | Alle CS | 0 CS-Dateien |
| Analyzer | .csproj | 0 csproj-Dateien |
| Migration | Migrations | 0 Migration-Dateien |

**AUSGABE:**
```
═══ Pre-PR Orchestrator v2.0 (PARALLEL) ═══

DIRTY-SCOPE:
  CS gesamt:    {N} Dateien
  Test-Dateien: {T} Dateien
  Non-Test:     {NT} Dateien
  .csproj:      {P} Dateien  → {SKIP wenn 0}
  Migrations:   {M} Dateien  → {SKIP wenn 0}

  Gates aktiv:  {X}/9
  Gates SKIP:   {Y} (keine Dateien)
```

---

## Phase 0b: Gate-Selektor (difficulty-basiert)

Bestimme ACTIVE_GATES basierend auf effektiver difficulty:

```
IF effektiv_difficulty == "easy":
  ACTIVE_GATES = [gate_tests, gate_naming, gate_cleanup]
  GATE_LIST = "3 Gates (Tests, Naming, Cleanup)"
  PROMPT_VARIANT = "standard"
ELSE:  (normal oder hard)
  ACTIVE_GATES = [alle 9 Gates]
  GATE_LIST = "alle 9 Gates"
  PROMPT_VARIANT = IF difficulty == "hard" THEN "extended" ELSE "standard"
```

TOP_3_GATES (fuer easy):
  1. gate_tests: Testabdeckung und Testqualitaet
  2. gate_naming: Naming-Konventionen und Lesbarkeit
  3. gate_cleanup: Code-Cleanup und offensichtliche Probleme

Spawne nur die Gates in ACTIVE_GATES.

---

## Phase 1: Team Setup

### 1.1 Team erstellen

```
TeamCreate:
  team_name: "pre-pr"
  description: "Pre-PR Quality Gates - Parallel Execution"
```

### 1.2 Tasks erstellen (1 pro aktivem Gate)

```
Pro aktivem Gate → TaskCreate:
  subject: "Gate {N}: {NAME}"
  description: |
    Quality Gate: /_Pre_PR_{NAME}
    Knowledge: .claude/meta/codeKonvention/{name}.md
    Command: .claude/commands/_Pre_PR_{NAME}.md
    Dateien: [LISTE]
    Auto-Fix: {JA/NEIN/TEIL}
  activeForm: "Running {NAME}"
```

KEINE Abhaengigkeiten zwischen Tasks (alle parallel)!

### 1.3 Workers spawnen - ALLE IN EINER MESSAGE

```
Pro aktivem Gate → Task tool (PARALLEL in einer Message!):
  name: "gate-{name}"
  subagent_type: "general-purpose"
  model: "{ceiling}"
  team_name: "pre-pr"
  mode: "bypassPermissions"
  prompt: [WORKER-PROMPT mit Gate-spezifischen Daten]
```

**KRITISCH:** Alle Task-Calls in EINER Message fuer maximale Parallelitaet!

---

## Phase 2: Worker-Prompt Template

Jeder Worker erhaelt:

```
Du bist "gate-{name}", ein Pre-PR Quality Gate Worker im Team "pre-pr".

═══ DEIN GATE ═══

Gate {N}: {NAME}
Knowledge-File: {WORKTREE}/.claude/meta/codeKonvention/{name}.md
Command-Spec: {WORKTREE}/.claude/commands/_Pre_PR_{NAME}.md

═══ ZU PRUEFENDE DATEIEN ═══

{DATEI_LISTE - vollstaendige relative Pfade, 1 pro Zeile}

═══ ARBEITSWEISE ═══

1. TaskList (limit: 100) → Task mit subject="Gate {N}: {NAME}" finden, taskId merken
2. TaskUpdate status=in_progress
3. Knowledge-File lesen
   → Falls nicht vorhanden: FEHLER an Team Lead melden, Task FAIL
4. Command-Spec lesen (.claude/commands/_Pre_PR_{NAME}.md)
   → Die Command-Spec definiert DEINE Prueflogik!
   → Folge der WELLEN-STRUKTUR aus der Spec:

═══ WELLEN-SYSTEM: DEIN ABLAUF (SEQUENTIELL) ═══

Du arbeitest in 3 Wellen SEQUENTIELL. KEIN Sub-Agent-Spawning.

  WELLE 1: EXPLORATION (5-10 Min)

    a) Datei-Liste in Batches aufteilen (max 10 Dateien pro Batch)

    b) Pro Batch:
       - Read-Tool SEQUENTIELL fuer jede Datei aufrufen
         (1 Call pro File - KEIN paralleles Read mehrerer Files)
       - Gegen Regeln aus Knowledge-File pruefen
       - Findings sammeln: Datei:Zeile:Regel:Problem
       - NOCH KEINE Fixes!

    c) Bei File-Read-Fehler:
       - Dieses File als WARNUNG markieren
       - Naechstes File fortsetzen (kein Abbruch)

    d) ACHTUNG: Andere Gates pruefen gleichzeitig dieselben Dateien.
       Falls du spaeter einen Auto-Fix nicht anwenden kannst:
       WARNUNG statt Fehler, niemals retry.

  WELLE 2: SYNTHESE + AUTO-FIX (5-10 Min)

    a) Alle Findings aus Welle 1 aggregieren
    b) Findings nach Datei + Severity gruppieren
    c) Pro Finding (wenn Auto-Fix: JA oder TEIL erlaubt):
       - Edit-Tool anwenden
       - Success → FIXED++ zaehlen
       - Fehler → BLOCKER++ zaehlen (kein Retry)
    d) Keine Zwischencommits (kein git commit)

  WELLE 3: BERICHT (2 Min)

    a) Zaehlen: TOTAL / CLEAN / FIXED / BLOCKER / WARNUNG
    b) Status bestimmen:
       - PASS:  BLOCKER == 0 AND WARNUNG == 0
       - WARN:  BLOCKER == 0 AND WARNUNG > 0
       - FAIL:  BLOCKER > 0
    c) SendMessage an Team Lead (Format: siehe SCHRITTE unten)

═══ SCHRITTE ═══

5. Welle 1 ausfuehren: Dateien SEQUENTIELL in Batches pruefen
   (Details: siehe WELLEN-SYSTEM Block oben)
6. Welle 2 ausfuehren: Synthese + Auto-Fix
   (Details: siehe WELLEN-SYSTEM Block oben)
7. Welle 3: Status + Bericht erstellen
   (Details: siehe WELLEN-SYSTEM Block oben)
8. TaskUpdate status=completed
9. SendMessage an Team Lead:

   Gate {N} ({NAME}): {PASS|WARN|FAIL}
   Dateien: {TOTAL} geprueft
   CLEAN: {C} | FIXED: {F} | BLOCKER: {B} | WARNUNG: {W}

   [Falls BLOCKER oder WARNUNG > 0, max 10 Findings:]
   BLOCKER: {Datei}:{Zeile} [{Regel}] {Problem} → KEIN Auto-Fix moeglich
   WARNUNG: {Datei}:{Zeile} [{Regel}] {Problem} → {Empfehlung}
   FIXED:   {Datei}:{Zeile} [{Regel}] → Auto-Fix angewendet

   [Falls > 10 Findings: "...und {N-10} weitere. Details in Gate-Spec."]

═══ REGELN ═══

- KEIN git commit, KEIN git push
- Arbeite NUR an deinem Gate (nicht andere Aspekte pruefen)
- Beruehre keine Dateien ausserhalb deiner Liste
- Bei Unsicherheit: lieber WARNUNG melden als falschen Auto-Fix
- Nutze ABSOLUTE Pfade fuer alle Datei-Operationen
```

---

## Phase 3: Team Lead Monitoring

### 3.1 Auf alle Workers warten

```
LOOP (bis alle Gates completed):
  - Worker-Messages empfangen
  - Gate-Ergebnisse sammeln
  - Fortschritt tracken: "{X}/{Y} Gates abgeschlossen"
```

### 3.2 Ergebnisse aggregieren

Pro Gate sammeln:
- Status: PASS / WARN / FAIL
- Zahlen: Dateien / Clean / Fixed / Blocker / Warnung
- Finding-Details (fuer Summary)

---

## Phase 4: Build + Test Verification

Nach ALLEN Gates abgeschlossen:

```bash
# 1. Build
dotnet build {SOLUTION_PATH}
# Erwartung: 0 Errors

# 2. Tests
dotnet test {SOLUTION_PATH}
# Erwartung: 0 FAIL
```

### 4.1 Build OK

→ Weiter mit Phase 5 (Summary)

### 4.2 Build FAIL (Konflikt-Erkennung)

Falls Build nach parallelen Auto-Fixes fehlschlaegt:

1. Identifiziere Fehler-Dateien aus Build-Output
2. Pruefe: Wurden diese Dateien von MEHREREN Gates editiert?
3. Falls ja: Das sind Konflikt-Dateien

**Konflikt-Aufloesung:**
```
AUSGABE:
  "Build-Fehler nach parallelen Auto-Fixes."
  "Konflikte in {N} Dateien: {LISTE}"
  "Empfehlung: git restore {DATEIEN} → betroffene Gates sequentiell re-run"
```

---

## Phase 5: Summary + Shutdown

### 5.1 Summary Report

```markdown
# Pre-PR Quality Gate Summary

**Branch:** {BRANCH}
**Datum:** {DATE}
**Modus:** PARALLEL (v2.0)
**Diff-Basis:** develop...HEAD
**Dateien:** {N} CS + {P} csproj + {M} Migrations

## Gate-Ergebnisse

| # | Gate           | Status | Dateien | Clean | Fixed | Blocker | Warn |
|---|----------------|--------|---------|-------|-------|---------|------|
| 1 | Tests          | ...    | ...     | ...   | ...   | ...     | ...  |
| 2 | Naming         | ...    | ...     | ...   | ...   | ...     | ...  |
| 3 | Cleanup        | ...    | ...     | ...   | ...   | ...     | ...  |
| 4 | Dokumentation  | ...    | ...     | ...   | ...   | ...     | ...  |
| 5 | Konstanten     | ...    | ...     | ...   | ...   | ...     | ...  |
| 6 | Logging        | ...    | ...     | ...   | ...   | ...     | ...  |
| 7 | Architektur    | ...    | ...     | ...   | ...   | ...     | ...  |
| 8 | Analyzer       | ...    | ...     | ...   | ...   | ...     | ...  |
| 9 | Migration      | ...    | ...     | ...   | ...   | ...     | ...  |

## Build + Tests

**Build:** {0 Errors, X Warnings}
**Tests:** {N PASS, 0 FAIL}

## Gesamtstatus: {PASS|FAIL}

[Falls FAIL: Offene BLOCKER + Naechste Schritte]
```

### 5.2 Workers shutdownen + Team aufraeumen

```
Pro Worker:
  SendMessage type=shutdown_request

Nach allen Shutdowns:
  TeamDelete
```

---

## Re-Run Modus

```
Falls /_Pre_PR_orchestrate schon gelaufen:

1. Vorherigen Summary lesen
2. NUR FAIL/WARN Gates erneut spawnen
3. PASS Gates skippen (Ergebnis wiederverwenden)

AUSGABE:
  "Re-Run: {N} Gates uebersprungen (PASS), {M} Gates erneut"
```

---

## Execution Timeline

```
| Phase   | Was                    | Agents | Zeit    |
|---------|------------------------|--------|---------|
| Phase 0 | Datei-Listen           | 1 (DU) | ~1 min  |
| Phase 1 | Team Setup + Spawn     | 1 (DU) | ~1 min  |
| Phase 2 | 9 Gates PARALLEL       | 9      | ~5 min  |
| Phase 3 | Aggregation            | 1 (DU) | ~1 min  |
| Phase 4 | Build + Test           | 1 (DU) | ~5 min  |
| Phase 5 | Summary + Shutdown     | 1 (DU) | ~1 min  |
|---------|------------------------|--------|---------|
| TOTAL   |                        | 9+1    | ~14 min |

vs ALT (v1.0 sequentiell): ~27 min → ~48% schneller
```

---

## TASK-BESCHREIBUNGEN (Vorlagen fuer TaskCreate)

### Gate 1: Tests

```
Subject: "Gate 1: Tests"
ActiveForm: "Running Tests quality gate"
Description: |
  Quality Gate: /_Pre_PR_Tests
  Knowledge: .claude/meta/codeKonvention/testbase.md
  Command: .claude/commands/_Pre_PR_Tests.md
  Dateien: {TEST_DATEI_LISTE}
  Auto-Fix: JA (sealed, TestBase-Vererbung)

  Pruefe:
  - R1: sealed Modifier auf Test-Klassen
  - R2: TestBase/ContainerIntegrationTestBase Vererbung
  - R3: Dispose-Pattern korrekt
  - R4: Test-Isolation

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 2: Naming

```
Subject: "Gate 2: Naming"
ActiveForm: "Running Naming quality gate"
Description: |
  Quality Gate: /_Pre_PR_Naming
  Knowledge: .claude/meta/codeKonvention/naming.md
  Command: .claude/commands/_Pre_PR_Naming.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: JA (Identifier umbenennen)

  Pruefe:
  - R1-R6: PascalCase, camelCase, Prefixes (I, _),
    Provider/Service/Controller Suffixes, Umlaut-Encoding

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 3: Cleanup

```
Subject: "Gate 3: Cleanup"
ActiveForm: "Running Cleanup quality gate"
Description: |
  Quality Gate: /_Pre_PR_Cleanup
  Knowledge: .claude/meta/codeKonvention/cleanup.md
  Command: .claude/commands/_Pre_PR_Cleanup.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: JA (Usings, Leerzeilen, Debug-Code)

  Pruefe:
  - Unused usings, Leerzeilen, auskommentierter Code,
    Debug-Output (Console.Write, Debug.Write),
    TODO/HACK/FIXME Kommentare

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 4: Dokumentation

```
Subject: "Gate 4: Dokumentation"
ActiveForm: "Running Dokumentation quality gate"
Description: |
  Quality Gate: /_Pre_PR_Dokumentation
  Knowledge: .claude/meta/codeKonvention/dokumentation.md
  Command: .claude/commands/_Pre_PR_Dokumentation.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: JA (XML-Kommentare generieren)

  Pruefe:
  - XML-Doku auf public Klassen/Methoden/Properties
  - Umlaut-Konvention (echte Umlaute vs ue/ae/oe)
  - Markdown in .md Dateien

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 5: Konstanten

```
Subject: "Gate 5: Konstanten"
ActiveForm: "Running Konstanten quality gate"
Description: |
  Quality Gate: /_Pre_PR_Konstanten
  Knowledge: .claude/meta/codeKonvention/konstanten.md
  Command: .claude/commands/_Pre_PR_Konstanten.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: TEILWEISE (String-Literale mit 2+ Vorkommen)

  Pruefe:
  - Magic Strings (2+ Vorkommen → Auto-Fix)
  - Magic Numbers (INFO, kein Auto-Fix)
  - Konstanten-Organisation

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 6: Logging

```
Subject: "Gate 6: Logging"
ActiveForm: "Running Logging quality gate"
Description: |
  Quality Gate: /_Pre_PR_Logging
  Knowledge: .claude/meta/codeKonvention/logging.md
  Command: .claude/commands/_Pre_PR_Logging.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: JA (Structured Logging)

  Pruefe:
  - String-Interpolation in Logging → Structured Logging
  - Log-Level Konsistenz
  - Sensitive Daten in Logs

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 7: Architektur

```
Subject: "Gate 7: Architektur"
ActiveForm: "Running Architektur quality gate"
Description: |
  Quality Gate: /_Pre_PR_Architektur
  Knowledge: .claude/meta/codeKonvention/architektur.md
  Command: .claude/commands/_Pre_PR_Architektur.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: NEIN (nur Bericht)

  Pruefe:
  - R1-R6: Controller-Logik, Interface-Segregation,
    Provider-Pattern, Config-Zugriff, DI-Registrierung,
    DateTimeOffset.Now Konsistenz

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 8: Analyzer

```
Subject: "Gate 8: Analyzer"
ActiveForm: "Running Analyzer quality gate"
Description: |
  Quality Gate: /_Pre_PR_Analyzer
  Knowledge: .claude/meta/codeKonvention/analyzer.md
  Command: .claude/commands/_Pre_PR_Analyzer.md
  Dateien: {CSPROJ_LISTE}
  Auto-Fix: JA (SonarAnalyzer + Ruleset einfuegen)

  Pruefe:
  - SonarAnalyzer.CSharp in .csproj
  - CodeAnalysisRuleSet Referenz
  - EditorConfig Aenderungen

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 9: Migration

```
Subject: "Gate 9: Migration"
ActiveForm: "Running Migration quality gate"
Description: |
  Quality Gate: /_Pre_PR_Migration
  Knowledge: .claude/meta/codeKonvention/migration.md
  Command: .claude/commands/_Pre_PR_Migration.md
  Dateien: {MIGRATION_LISTE}
  Auto-Fix: NEIN (zu hohes Risiko)

  Pruefe:
  - Bestehende Migrationen nicht geaendert (BLOCKER)
  - Down() ist exaktes Gegenteil von Up() (BLOCKER)
  - Reihenfolge umgekehrt
  - Nicht-deterministische Test-Daten (WARNUNG)

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

---

## QUICK-START

Wenn User sagt "Pre-PR ausfuehren":

```
1. /_Pre_PR_orchestrate
2. Team Lead: Datei-Listen generieren (Phase 0)
3. Team Lead: Team "pre-pr" erstellen + 9 Tasks + 9 Workers spawnen
4. 9 Workers PARALLEL: Jeder prueft sein Gate
5. Team Lead: Ergebnisse sammeln
6. Team Lead: Build + Test ausfuehren
7. Team Lead: Summary Report + Shutdown

Bei FAIL: User fixt → /_Pre_PR_orchestrate (Re-Run, nur FAIL-Gates)
Bei PASS: PR erstellen
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| Worker meldet Knowledge-File fehlt | Gate als FAIL markieren, andere Gates laufen weiter |
| Worker-Timeout (>15 Min) | SendMessage "Status?", 5 Min warten, dann FAIL |
| Worker crashed | Gate als FAIL markieren, Re-Run nach Summary |
| Build-Fehler nach Auto-Fixes | Konflikt-Erkennung: welche Dateien von mehreren Gates editiert? Restoren + Re-Run sequentiell |
| Test-Fehler nach Auto-Fixes | Gleiche Konflikt-Erkennung wie Build |
| Alle Workers FAIL | ABORT: "Keine Gates bestanden. Knowledge-Files pruefen." |

---

## LIFECYCLE-INTEGRATION

```
╔══════════════════════════════════════════════════════════════╗
║  PRE-PR im Feature-Lebenszyklus                             ║
║                                                              ║
║  /_SC_orchestrate ──► /_I_orchestrate ──► /_Pre_PR_orchestrate
║  (Forschung)         (Code + Tests)       (Quality Gates)    ║
║                                                              ║
║  Innerhalb /_I_orchestrate:                                  ║
║    ... → /_I_verify → /_I_diffAudit → /_Pre_PR_orchestrate  ║
║                                           │                  ║
║                                      PASS → PR erstellen     ║
║                                      FAIL → Fix → Re-Run    ║
╚══════════════════════════════════════════════════════════════╝
```

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist:**

```bash
powershell -Command "notify '{FEATURE} /_Pre_PR_orchestrate abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
