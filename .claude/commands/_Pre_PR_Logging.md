---
name: _Pre_PR_Logging
description: Pre-PR Logging Quality Gate - Prueft Logging-Konventionen im Branch-Diff
type: building-block
---

# /_Pre_PR_Logging

**Zweck:** Logging-Verstoesse im Branch-Diff erkennen und fixen
**Abdeckung:** 59 von 274 Kommentaren (21.5%)
**Basis:** Christians Feedback zu Logging-Konventionen

---

## Vertrag

```
+------------------------------------------------------------------+
|                    /_Pre_PR_Logging Quality Gate                 |
+------------------------------------------------------------------+
| INPUT:                                                           |
|   - Git Branch Diff (develop...HEAD)                            |
|   - {META}/codeKonvention/logging.md                      |
|   - Codebase *.cs Dateien                                       |
+------------------------------------------------------------------+
| OUTPUT:                                                          |
|   - Code-Fixes (Auto-Fix Regeln R1-R3)                          |
|   - Findings-Bericht (Manuelle Regeln R4-R5)                    |
|   - Quality Gate Status (PASSED / FAILED)                       |
+------------------------------------------------------------------+
| SCOPE:                                                           |
|   - NUR geaenderte Zeilen im Branch-Diff                        |
|   - Kein Full-Repo-Scan                                         |
+------------------------------------------------------------------+
| AGENTS:                                                          |
|   - Welle 1: N x Haiku/Sonnet (Exploration, parallel)           |
|   - Welle 2: 1 x Sonnet (Synthese + Fix-Orchestrierung)         |
|   - Welle 3: M x Haiku (Batch-Fixes, parallel)                  |
+------------------------------------------------------------------+
```

---

## Schritt 0: DIRTY-Scope ermitteln

### 0.1 Branch-Diff abrufen
```bash
git diff develop...HEAD --name-only --diff-filter=ACMR
```

Filter auf `*.cs` Dateien anwenden.

### 0.2 Geaenderte Zeilen extrahieren
Fuer jede geaenderte `*.cs` Datei:
```bash
git diff develop...HEAD -- {datei}
```

Parsen der Diff-Hunks:
- Zeilen mit `+` am Anfang sind NEU/GEAENDERT
- Zeilen mit `-` am Anfang sind GELOESCHT (ignorieren)
- Kontext-Zeilen (ohne +/-) ignorieren

### 0.3 DIRTY-Scope-Liste erstellen
Output: Liste von `(Datei, Zeilennummer, Code-Zeile)`

**Beispiel:**
```
DataStore.cs:42: Log.Information("[DataStore] LoadData: Daten werden geladen");
UserService.cs:15: Console.WriteLine("User logged in: " + userId);
FileProcessor.cs:88: Log.Error($"Failed to process {fileName}");
```

---

## Schritt 1: Konventions-Regeln lesen

Lese `{META}/codeKonvention/logging.md`

**Fehlerbehandlung:** Falls die Datei nicht existiert → FEHLER: "Knowledge-Datei {META}/codeKonvention/logging.md nicht gefunden. Starte _I_fanOut oder erstelle die Datei manuell." → EXIT 1

Extrahiere alle Regeln (R1-R5) mit:
- Schwere (BLOCKER / WARNUNG / INFO)
- Auto-Fix Flag (JA / NEIN)
- Erkennungs-Pattern
- VORHER/NACHHER Beispiele

---

## Welle 1: Exploration (Parallel)

### 1.1 Agent-Pool starten
Pro geaenderter `*.cs` Datei einen Agent (Haiku oder Sonnet):
- **Ceiling:** Sonnet
- **Floor:** Haiku
- **Entscheidung:** Sonnet wenn >100 Zeilen im Diff, sonst Haiku

### 1.2 Agent-Prompt Template
```
Du bist ein Logging-Konventions-Scanner.

KONTEXT:
- Datei: {datei}
- Branch-Diff: {diff_hunks}
- Regeln: {logging.md Inhalt}

AUFGABE:
Scanne NUR die geaenderten Zeilen (+) im Diff nach Logging-Verstoessen.

REGELN:
{R1-R5 aus logging.md}

OUTPUT-FORMAT (JSON):
{
  "file": "{datei}",
  "findings": [
    {
      "rule": "R1",
      "line": 42,
      "severity": "BLOCKER",
      "auto_fix": true,
      "code": "Log.Information(\"[DataStore] LoadData: ...\");",
      "fix": "Log.Information(\"Daten werden geladen von {Path}\", path);",
      "reason": "Redundante Meta-Information [DataStore]"
    }
  ]
}

WICHTIG:
- NUR geaenderte Zeilen pruefen (Zeilen mit + im Diff)
- Keine Findings fuer unveraenderte Zeilen
- Bei Auto-Fix: konkreten Fix-Code liefern
```

### 1.3 Parallele Ausfuehrung
Alle Agents parallel starten (await Task.WhenAll in C#-Analogie).

---

## Welle 2: Synthese + Fix-Orchestrierung

### 2.1 Findings sammeln
Hauptagent (Sonnet) sammelt alle JSON-Findings aus Welle 1.

### 2.2 Deduplizierung
Falls mehrere Agents dieselbe Zeile bemängeln: hoechste Schwere gewinnt.

### 2.3 Kategorisierung
Findings aufteilen in:
- **Auto-Fix:** R1, R2, R3 (BLOCKER mit Auto-Fix=JA)
- **Manual Review:** R4, R5 (Auto-Fix=NEIN)

### 2.4 Fix-Plan erstellen
Pro Datei mit Auto-Fix-Findings: Fix-Plan erstellen.

**Beispiel Fix-Plan:**
```json
{
  "file": "DataStore.cs",
  "fixes": [
    {
      "line": 42,
      "old": "Log.Information(\"[DataStore] LoadData: Daten werden geladen\");",
      "new": "Log.Information(\"Daten werden geladen\");"
    },
    {
      "line": 55,
      "old": "Console.WriteLine(\"Done\");",
      "new": "Log.Information(\"Abgeschlossen\");"
    }
  ]
}
```

---

## Welle 3: Batch-Fixes (Parallel)

### 3.1 Fix-Agents starten
Pro Datei mit Fixes einen Agent (Haiku):
- **Input:** Fix-Plan fuer diese Datei
- **Aufgabe:** Fixes anwenden (Edit-Tool verwenden)
- **Output:** Success / Failure

### 3.2 Agent-Prompt Template
```
Du bist ein Code-Fixer.

DATEI: {datei}
FIX-PLAN: {fix_plan}

AUFGABE:
Wende alle Fixes aus dem Plan an. Verwende das Edit-Tool.

WICHTIG:
- Exakte Zeilen-Matches (old_string muss EXAKT stimmen)
- Bei Fehler: Abbruch + Meldung
- Keine zusaetzlichen Aenderungen
```

### 3.3 Parallele Ausfuehrung
Alle Fix-Agents parallel starten.

### 3.4 Validierung (optional)
Nach Fixes: `dotnet build` ausfuehren (nur wenn explizit aktiviert).
Bei Compile-Fehler: Fixes rueckgaengig machen (git restore).

---

## Schritt 2: Bericht erstellen

### 2.1 Bericht-Struktur
```markdown
# Pre-PR Logging Quality Gate - Bericht

**Branch:** {branch_name}
**Datum:** {datum}
**Scope:** {anzahl_dateien} Dateien, {anzahl_zeilen} geaenderte Zeilen

---

## Zusammenfassung

| Kategorie         | Anzahl |
|-------------------|--------|
| Auto-Fixes        | {n}    |
| Manuelle Reviews  | {m}    |
| BLOCKER           | {x}    |
| WARNUNG           | {y}    |

**Quality Gate Status:** PASSED / FAILED

---

## Auto-Fixes (angewendet)

### R1: Redundante Meta-Informationen
- `DataStore.cs:42` - [DataStore] entfernt
- `UserService.cs:88` - Methodenname entfernt

### R2: Structured Logging
- `FileProcessor.cs:15` - String-Interpolation ersetzt

### R3: Console.WriteLine
- `ApiController.cs:99` - Console.WriteLine durch Log.Information ersetzt

---

## Manuelle Reviews (erforderlich)

### R4: Deutsche Log-Messages
- `DicClient.cs:123` - Englische Message erkannt
  ```csharp
  // VORHER
  Log.Error(ex, "Download failed for file {FileId}", fileId);

  // VORSCHLAG
  Log.Error(ex, "Download fehlgeschlagen fuer Datei {FileId}", fileId);
  ```

### R5: Falsches Log-Level
- `DataStore.cs:200` - Information statt Error
  ```csharp
  // VORHER
  Log.Information("Fehler beim Laden: {Error}", ex.Message);

  // VORSCHLAG
  Log.Error(ex, "Fehler beim Laden der Daten");
  ```

---

## Quality Gate Entscheidung

**FAILED:** 3 BLOCKER-Findings erfordern manuelle Korrektur.

Naechste Schritte:
1. Manuelle Reviews aus Abschnitt "Manuelle Reviews" bearbeiten
2. Erneut /_Pre_PR_Logging ausfuehren
3. Bei PASSED: PR erstellen
```

### 2.2 Bericht speichern
Speichere Bericht als `.claude/reports/pre_pr_logging_{timestamp}.md`

---

## Qualitaetskriterien

### QC1: DIRTY-Scope eingehalten
- [X] NUR geaenderte Zeilen im Branch-Diff geprueft
- [X] Keine Findings fuer unveraenderte Zeilen
- [X] Keine Full-Repo-Scans

### QC2: Alle Regeln geprueft
- [X] R1: Redundante Meta-Informationen
- [X] R2: Structured Logging
- [X] R3: Console.WriteLine
- [X] R4: Deutsche Log-Messages
- [X] R5: Log-Level

### QC3: Auto-Fixes kompilieren
- [X] `dotnet build` nach Fixes erfolgreich (falls aktiviert)
- [X] Keine Syntax-Fehler eingefuehrt
- [X] Keine Breaking Changes

### QC4: Bericht vollstaendig
- [X] Alle Findings dokumentiert
- [X] VORHER/NACHHER fuer Auto-Fixes
- [X] Vorschlaege fuer manuelle Reviews
- [X] Quality Gate Status klar erkennbar

---

## Fehlerbehandlung

### Fall 1: Git Diff schlaegt fehl
- **Ursache:** Nicht im Git-Repo, develop-Branch fehlt
- **Aktion:** Abbruch mit klarer Fehlermeldung

### Fall 2: logging.md nicht gefunden
- **Ursache:** Konventions-Datei fehlt
- **Aktion:** Abbruch, Hinweis auf fehlende Konvention

### Fall 3: Edit-Tool schlaegt fehl
- **Ursache:** old_string nicht eindeutig / nicht gefunden
- **Aktion:** Finding als "Fix fehlgeschlagen" markieren, manuellen Review erfordern

### Fall 4: dotnet build schlaegt fehl
- **Ursache:** Auto-Fix hat Syntax-Fehler eingefuehrt
- **Aktion:** `git restore` fuer betroffene Datei, Finding als "Fix fehlgeschlagen" markieren

---

## Beispiel-Ausfuehrung

```powershell
# Command ausfuehren
/_Pre_PR_Logging

# Output
[Schritt 0] DIRTY-Scope ermittelt: 7 Dateien, 42 geaenderte Zeilen
[Schritt 1] Konventions-Regeln geladen: 5 Regeln
[Welle 1] Exploration gestartet: 7 Agents (4 Haiku, 3 Sonnet)
[Welle 1] Findings gesammelt: 18 Verstoesse
[Welle 2] Kategorisiert: 12 Auto-Fix, 6 Manual Review
[Welle 2] Fix-Plan erstellt: 7 Dateien
[Welle 3] Batch-Fixes gestartet: 7 Agents
[Welle 3] Auto-Fixes angewendet: 12 erfolgreich
[Schritt 2] Bericht erstellt: .claude/reports/pre_pr_logging_20260206_143022.md

Quality Gate: FAILED (6 manuelle Reviews erforderlich)

Naechste Schritte:
1. Oeffne Bericht: .claude/reports/pre_pr_logging_20260206_143022.md
2. Bearbeite manuelle Reviews (R4, R5)
3. Fuehre /_Pre_PR_Logging erneut aus
```

---

## Integration in PR-Workflow

### Empfohlener Workflow
1. Feature-Branch entwickeln
2. Vor `git push`: `/_Pre_PR_Logging` ausfuehren
3. Auto-Fixes committen (separater Commit: "fix: Logging-Konventionen (Auto-Fix)")
4. Manuelle Reviews bearbeiten
5. Erneut `/_Pre_PR_Logging` ausfuehren
6. Bei PASSED: `gh pr create`

### Pre-Commit Hook (optional)
```bash
#!/bin/bash
# .git/hooks/pre-push

echo "Running Pre-PR Logging Quality Gate..."
# TODO: Claude Agent ausfuehren
# TODO: Bei FAILED: Push abbrechen
```

---

## Metriken

Nach Ausfuehrung tracken:
- Anzahl Findings (Auto-Fix vs. Manual)
- Anzahl betroffene Dateien
- Ausfuehrungszeit (Welle 1, 2, 3)
- Quality Gate Pass-Rate

Ziel: 90% der Logging-Kritik automatisch erkennen BEVOR PR erstellt wird.

---

## Erweiterungen (Zukunft)

### E1: Weitere Konventionen
- `/_Pre_PR_Naming` (Naming-Konventionen)
- `/_Pre_PR_Architecture` (Schichtverletzungen)
- `/_Pre_PR_Security` (Secrets im Code)

### E2: IDE-Integration
- VS Code Extension
- Inline-Warnings waehrend des Tippens

### E3: CI/CD-Integration
- Azure DevOps Pipeline Step
- Automatischer PR-Comment mit Findings
