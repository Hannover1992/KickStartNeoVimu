# Pre-PR Cleanup Command

**Zweck:** Automatische Pruefung und Behebung von Cleanup-Verstoessen vor Pull Requests
**Schwierigkeit:** EASY (Floor=haiku, Ceiling=sonnet)
**Auto-Fix:** 80% (Leerzeilen, Usings, .gitkeep), 20% manuell (auskommentierter Code)

---

## Vertrag

```
+==============================================================================+
|                          PRE-PR CLEANUP COMMAND                              |
+==============================================================================+
|                                                                              |
| LIEST:                                                                       |
|   - .claude/meta/codeKonvention/cleanup.md (Konventions-Regeln)            |
|     FEHLER falls nicht gefunden → EXIT 1                                   |
|   - git diff --name-only develop...HEAD (Geaenderte Dateien im DIRTY-Scope)|
|   - *.cs Dateien (C# Source Code)                                           |
|   - .gitkeep Dateien (Git-Platzhalter)                                      |
|   - .editorconfig (Format-Konfiguration)                                    |
|   - Verzeichnisstruktur (fuer .gitkeep-Pruefung)                            |
|                                                                              |
| SCHREIBT:                                                                    |
|   - *.cs Dateien (Auto-Fix fuer Leerzeilen, Usings)                        |
|   - CLEANUP_REPORT.md (Detaillierter Pruef-Report)                          |
|   - .gitkeep Dateien (Loeschung wenn ueberfluessig)                         |
|   - Konsolen-Output (Batch-Fix Zusammenfassung)                             |
|                                                                              |
| PRUEFT:                                                                      |
|   R1: Leerzeile nach } (SA1513)                                             |
|   R2: Keine Leerzeile vor } am Klassen-Ende (SA1508)                        |
|   R3: Ungenutzte using-Direktiven (IDE0005)                                 |
|   R4: Auskommentierter Code (Manuelles Review)                              |
|   R5: .gitkeep in nicht-leeren Ordnern                                      |
|                                                                              |
+==============================================================================+
```

---

## Ausfuehrung

### 1. Scope ermitteln (DIRTY-Scope)

```bash
# Nur geaenderte Dateien pruefen (nicht das gesamte Repo)
git diff --name-only develop...HEAD | grep -E '\.(cs|csproj|sln)$'
```

**Relevante Dateitypen:**
- `*.cs` - C# Source Code
- `*.csproj` - Projekt-Dateien
- `.gitkeep` - Git-Platzhalter

**Ausschluss:**
- `bin/`, `obj/` - Build-Artefakte
- `*.designer.cs` - Generierte Dateien
- `Migrations/` - Entity Framework Migrations

---

### 2. Welle 1: Haiku scannt nach Verstoessen

**Modell:** Claude Haiku (schnell, kostenguenstig)
**Aufgabe:** Violations identifizieren

```markdown
Du bist ein Code-Cleanup Scanner. Pruefe die folgenden Dateien auf Cleanup-Verstoesse:

REGELN:
- R1: Leerzeile nach } (SA1513) - Auto-Fix
- R2: Keine Leerzeile vor } am Klassen-Ende (SA1508) - Auto-Fix
- R3: Ungenutzte using-Direktiven - Auto-Fix
- R4: Auskommentierter Code - Manuelles Review
- R5: .gitkeep in nicht-leeren Ordnern - Auto-Fix

DATEIEN:
[Liste der DIRTY-Scope Dateien]

FORMAT:
Fuer jeden Verstoss gib zurueck:
- Datei: <Pfad>
- Regel: <R1-R5>
- Zeile: <Zeilennummer>
- Typ: AUTO-FIX oder MANUAL
- Beschreibung: <Kurze Erklaerung>

WICHTIG: Nur echte Verstoesse melden, keine false positives.
```

**Erwartete Ausgabe:**
```
VERSTOESSE GEFUNDEN: 12

AUTO-FIX (9):
- Services/UserService.cs:45 [R1] Fehlende Leerzeile nach }
- Services/UserService.cs:78 [R2] Leerzeile vor Klassen-Ende
- Controllers/UserController.cs:5 [R3] Ungenutzte using System.Threading.Tasks
- Data/.gitkeep [R5] Ueberfluessig (Ordner enthaelt 3 Dateien)
...

MANUAL REVIEW (3):
- Services/AuthService.cs:23-27 [R4] Auskommentierter Code (5 Zeilen)
- Helpers/DateHelper.cs:89-92 [R4] Auskommentierter Code (4 Zeilen)
...
```

---

### 3. Welle 2: Batch-Fix ausfuehren

**3.1 Auto-Fix: dotnet format**

```bash
# StyleCop-Warnings beheben (R1, R2, R3)
dotnet format --severity warn --verbosity diagnostic

# Ergebnis pruefen
dotnet format --verify-no-changes --severity warn
```

**Erwartete Ausgabe:**
```
Formatting code files in workspace 'Backend.sln'.
  Fixed: Services/UserService.cs (2 warnings)
  Fixed: Controllers/UserController.cs (1 warning)
  Fixed: Helpers/DateHelper.cs (3 warnings)

Format complete. 6 files formatted.
```

**3.2 Auto-Fix: .gitkeep Bereinigung**

```powershell
# PowerShell-Script fuer .gitkeep Cleanup (R5)
Get-ChildItem -Path . -Recurse -Filter .gitkeep | Where-Object {
    $dir = $_.Directory
    $fileCount = (Get-ChildItem $dir -File).Count
    # Wenn mehr als nur .gitkeep im Ordner
    if ($fileCount -gt 1) {
        Write-Host "Entferne ueberfluessige .gitkeep: $($_.FullName)"
        Remove-Item $_.FullName
        return $true
    }
    return $false
}
```

**Bash-Alternative:**
```bash
find . -name .gitkeep -type f | while read gitkeep; do
    dir=$(dirname "$gitkeep")
    filecount=$(ls -A "$dir" | wc -l)
    if [ $filecount -gt 1 ]; then
        echo "Entferne ueberfluessige .gitkeep: $gitkeep"
        rm "$gitkeep"
    fi
done
```

**3.3 Manual Review: Auskommentierter Code (R4)**

**Modell:** Claude Sonnet (besseres Verstaendnis)
**Aufgabe:** Kontext-basierte Entscheidung

```markdown
Du bist ein Code-Reviewer. Pruefe den folgenden auskommentierten Code und entscheide:

OPTIONEN:
1. LOESCHEN - Kein Wert, einfach entfernen
2. BEHALTEN - Wichtiger Kontext, in Kommentar umwandeln
3. UNCLEAR - Entwickler muss entscheiden

KONTEXT:
- Datei: Services/AuthService.cs
- Zeilen: 23-27
- Code:
```csharp
// var oldToken = GenerateTokenV1(user);
// if (oldToken.IsValid)
// {
//     return oldToken;
// }
var newToken = GenerateTokenV2(user);
```

BEGRUENDUNG:
[Sonnet analysiert den Kontext und entscheidet]

EMPFEHLUNG: LOESCHEN
GRUND: Alte Implementation ohne Erklaerungswert. Versionskontrolle bewahrt Historie.
```

**Fuer jeden UNCLEAR-Fall:**
- Report erstellen mit Kontext
- Entwickler muss manuell entscheiden
- In CLEANUP_REPORT.md dokumentieren

---

## Report-Format

**CLEANUP_REPORT.md:**

```markdown
# Pre-PR Cleanup Report

**Datum:** 2026-02-06 14:32:15
**Branch:** feature/user-authentication
**Scope:** 18 geaenderte Dateien

---

## Zusammenfassung

| Kategorie       | Anzahl | Status        |
|-----------------|--------|---------------|
| Auto-Fixed      | 9      | ✓ Behoben     |
| Manual Review   | 3      | → Aktion      |
| Kein Problem    | 6      | ✓ Sauber      |

---

## Auto-Fix Durchgefuehrt

### R1: Leerzeile nach } (SA1513)
- ✓ Services/UserService.cs:45
- ✓ Services/UserService.cs:67
- ✓ Controllers/UserController.cs:123

### R2: Keine Leerzeile vor } (SA1508)
- ✓ Services/UserService.cs:78
- ✓ Helpers/DateHelper.cs:34

### R3: Ungenutzte using-Direktiven (IDE0005)
- ✓ Controllers/UserController.cs:5 (System.Threading.Tasks)
- ✓ Services/AuthService.cs:3 (System.Linq)

### R5: .gitkeep Bereinigung
- ✓ Data/.gitkeep (entfernt - 3 Dateien im Ordner)
- ✓ Models/.gitkeep (entfernt - 7 Dateien im Ordner)

---

## Manual Review Erforderlich

### R4: Auskommentierter Code

#### 1. Services/AuthService.cs:23-27
**Empfehlung:** LOESCHEN
**Grund:** Alte Token-Generation ohne Erklaerungswert.

```csharp
// var oldToken = GenerateTokenV1(user);
// if (oldToken.IsValid)
// {
//     return oldToken;
// }
```

**Aktion:** Code entfernen oder in Kommentar umwandeln:
```csharp
// HINWEIS: GenerateTokenV1() wurde durch V2 ersetzt (siehe Commit abc123)
```

---

#### 2. Helpers/DateHelper.cs:89-92
**Empfehlung:** UNCLEAR
**Grund:** Moeglicherweise relevanter Algorithmus-Vergleich.

```csharp
// Old calculation approach:
// var offset = TimeZoneInfo.Local.GetUtcOffset(DateTime.Now);
// return dateTime.Add(offset);
```

**Aktion:** Entwickler muss entscheiden:
- Falls relevant: In XML-Dokumentation umwandeln
- Falls veraltet: Loeschen

---

## Saubere Dateien (Keine Probleme)

- Models/User.cs
- Models/Role.cs
- DTOs/UserDto.cs
- Repositories/UserRepository.cs
- Tests/UserServiceTests.cs
- Tests/AuthServiceTests.cs

---

## Naechste Schritte

1. ✓ Auto-Fixes wurden angewendet (dotnet format)
2. ✓ .gitkeep Dateien wurden bereinigt
3. → Review die 2 Manual Review Faelle oben
4. → Commit die Auto-Fixes: `git add . && git commit -m "chore: Pre-PR cleanup"`
5. → Fuehre Tests aus: `dotnet test`
6. → Push und erstelle PR

---

## Qualitaetskriterien Erfuellt

- [x] Keine StyleCop-Warnings (SA1508, SA1513, SA1514)
- [x] Keine ungenutzten using-Direktiven
- [x] Keine ueberfluessigen .gitkeep Dateien
- [ ] Auskommentierter Code reviewed (2 Faelle offen)

**Status:** READY nach Manual Review
```

---

## Qualitaetskriterien

### Erfolg-Kriterien

1. **Auto-Fix Rate > 80%**
   - Leerzeilen, Usings, .gitkeep automatisch behoben

2. **Keine StyleCop-Warnings**
   - `dotnet format --verify-no-changes` = 0 Warnings

3. **Manual Review klar dokumentiert**
   - Jeder R4-Fall mit Empfehlung und Kontext

4. **Report vollstaendig**
   - Alle Violations erfasst
   - Alle Fixes dokumentiert
   - Naechste Schritte klar

### Fehler-Behandlung

**Szenario 1: dotnet format schlaegt fehl**
```
FEHLER: dotnet format konnte nicht ausgefuehrt werden.
URSACHE: [Compiler-Fehler / Syntax-Fehler]
AKTION: Behebe Compiler-Fehler zuerst, dann erneut ausfuehren.
```

**Szenario 2: Zu viele Manual Review Faelle**
```
WARNUNG: 15 Manual Review Faelle gefunden.
EMPFEHLUNG: Cleanup sollte kontinuierlich erfolgen, nicht erst vor PR.
AKTION: Nimm dir Zeit fuer grundliches Review oder splitte PR auf.
```

**Szenario 3: .gitkeep Script findet nichts**
```
INFO: Keine ueberfluessigen .gitkeep Dateien gefunden.
STATUS: Alles sauber.
```

---

## Beispiel-Ausfuehrung

```bash
# Schritt 1: Command ausfuehren
claude /_Pre_PR_Cleanup

# Claude Ausgabe:
# ===== PRE-PR CLEANUP GESTARTET =====
# Scope: 18 geaenderte Dateien
#
# [Welle 1] Haiku scannt...
# Gefunden: 12 Verstoesse (9 Auto-Fix, 3 Manual)
#
# [Welle 2] Auto-Fix...
# ✓ dotnet format: 6 Dateien formatiert
# ✓ .gitkeep: 2 Dateien entfernt
#
# [Welle 2] Manual Review...
# → 2 Faelle erfordern Entwickler-Entscheidung
#
# CLEANUP_REPORT.md erstellt.
# ===== CLEANUP ABGESCHLOSSEN =====

# Schritt 2: Report pruefen
cat CLEANUP_REPORT.md

# Schritt 3: Manual Review durchfuehren
# (Entwickler entscheidet ueber auskommentierten Code)

# Schritt 4: Commit
git add .
git commit -m "chore: Pre-PR cleanup - formatting and unused code removal"

# Schritt 5: Tests
dotnet test

# Schritt 6: Push
git push
```

---

## Integration in Workflow

### Pre-Commit Hook (Optional)

```bash
#!/bin/bash
# .git/hooks/pre-commit

echo "===== Pre-PR Cleanup Hook ====="

# Nur staged .cs Dateien pruefen
staged_files=$(git diff --cached --name-only --diff-filter=ACM | grep '\.cs$')

if [ -z "$staged_files" ]; then
    echo "Keine .cs Dateien im Commit."
    exit 0
fi

# dotnet format fuer staged files
dotnet format --include $staged_files --verify-no-changes --severity warn

if [ $? -ne 0 ]; then
    echo ""
    echo "FEHLER: Code-Formatierung erforderlich."
    echo "Fuehre aus: dotnet format"
    echo "Oder: claude /_Pre_PR_Cleanup"
    exit 1
fi

echo "✓ Cleanup-Pruefung erfolgreich."
exit 0
```

### CI/CD Pipeline (Optional)

```yaml
# .github/workflows/pr-cleanup-check.yml
name: PR Cleanup Check

on:
  pull_request:
    branches: [ main, develop ]

jobs:
  cleanup-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup .NET
        uses: actions/setup-dotnet@v3
        with:
          dotnet-version: '8.0.x'

      - name: Verify Code Format
        run: dotnet format --verify-no-changes --severity warn

      - name: Check for .gitkeep in non-empty dirs
        run: |
          found=0
          for gitkeep in $(find . -name .gitkeep); do
            dir=$(dirname "$gitkeep")
            filecount=$(ls -A "$dir" | wc -l)
            if [ $filecount -gt 1 ]; then
              echo "ERROR: Ueberfluessige .gitkeep: $gitkeep"
              found=1
            fi
          done
          exit $found

      - name: Check for commented code (simple heuristic)
        run: |
          # Warnung bei vielen aufeinanderfolgenden // Zeilen
          found=$(grep -r "^[[:space:]]*//.*" --include="*.cs" . | \
                  awk '{if(NR>1 && prev+1==NR) count++; prev=NR} END{print count}')
          if [ $found -gt 20 ]; then
            echo "WARNUNG: $found aufeinanderfolgende Kommentar-Zeilen gefunden."
            echo "Pruefe auf auskommentierten Code."
          fi
```

---

## Haeufige Fragen

**F: Warum Haiku fuer Scan, Sonnet fuer Manual Review?**
A: Haiku ist schnell/guenstig fuer Pattern-Matching (Leerzeilen etc.). Sonnet versteht Kontext besser (auskommentierter Code).

**F: Was wenn dotnet format nicht verfuegbar?**
A: Fallback auf Editor-spezifische Tools (ReSharper, Rider, VS Code Extensions) oder manuelle Fixes mit Report-Guidance.

**F: Kann ich einzelne Regeln deaktivieren?**
A: Ja, in `.editorconfig`:
```ini
[*.cs]
dotnet_diagnostic.SA1508.severity = none  # Deaktiviert R2
```

**F: Was ist mit anderen Dateitypen (.js, .ts, .py)?**
A: Dieser Command fokussiert auf .NET/C#. Fuer andere Sprachen: Eigene Commands mit jeweiligen Linters (ESLint, Pylint, etc.).

**F: Wie lange dauert der Cleanup?**
A:
- Haiku Scan: 10-30 Sekunden
- dotnet format: 5-60 Sekunden (je nach Dateizahl)
- .gitkeep Cleanup: <5 Sekunden
- Manual Review: 1-5 Minuten (Entwickler-Zeit)

---

## Zusammenfassung

**Pre-PR Cleanup Command:**
- Automatisiert 80% der Cleanup-Aufgaben
- Spart Zeit im Code Review
- Verhindert StyleCop-Warnings
- Dokumentiert Manual Review-Faelle klar
- Integrierbar in Hooks und CI/CD

**Zeitersparnis pro PR:**
- Ohne Command: 10-20 Minuten manuelle Cleanup
- Mit Command: 2-5 Minuten (meist nur Manual Review)

**Resultat:** Professionellerer Code, weniger Review-Kommentare, schnellere PR-Approvals.
