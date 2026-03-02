---
name: _Pre_PR_Analyzer
description: Pre-PR Analyzer Quality Gate - prueft und repariert Analyzer-Konfiguration in .csproj Dateien
---

# /_Pre_PR_Analyzer

**Zweck:** Sicherstellen dass alle .csproj Dateien SonarAnalyzer.CSharp und Rulesets korrekt eingebunden haben.

**Abdeckung:** 6 Kommentare (2.2% aller Code-Review-Kommentare)

**Schwierigkeit:** EASY (Ceiling: sonnet, Floor: haiku)

**Auto-Fix:** JA (kann .csproj Dateien automatisch korrigieren)

---

## Vertrag

```
╔══════════════════════════════════════════════════════════════╗
║  COMMAND: /_Pre_PR_Analyzer                                  ║
╠══════════════════════════════════════════════════════════════╣
║  LIEST:                                                      ║
║    1. .claude/meta/codeKonvention/analyzer.md                ║
║    2. Git Diff (develop...HEAD)                              ║
║    3. Alle *.csproj Dateien (neue + geaenderte)              ║
║    4. .editorconfig (fuer R3)                                ║
║  SCHREIBT:                                                   ║
║    1. *.csproj Dateien (SonarAnalyzer + Ruleset einfuegen)   ║
║    2. Bericht mit Warnungen fuer EditorConfig-Aenderungen    ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: DIRTY-Scope ermitteln

**Aktion:** Git Diff auf .csproj und .editorconfig Dateien.

```bash
git diff --name-status develop...HEAD -- "*.csproj" ".editorconfig"
```

**Kategorisierung:**
```
A Backend.API/Backend.API.csproj              → NEUE .csproj
M Backend.Core/Backend.Core.csproj            → GEAENDERTE .csproj
M .editorconfig                               → GEAENDERTE EditorConfig
```

**Output:**
```
DIRTY-SCOPE:
  Neue .csproj: [N]
  Geaenderte .csproj: [N]
  Geaenderte .editorconfig: [1/0]
```

---

## Schritt 1: Regeln lesen

**Aktion:** Konvention laden.

```bash
cat .claude/meta/codeKonvention/analyzer.md
```

**Fehlerbehandlung:** Falls die Datei nicht existiert → FEHLER: "Knowledge-Datei .claude/meta/codeKonvention/analyzer.md nicht gefunden. Starte _I_fanOut oder erstelle die Datei manuell." → EXIT 1

**Regeln extrahieren:**
- R1: SonarAnalyzer.CSharp in .csproj (BLOCKER, Auto-Fix JA)
- R2: Rulesets in .csproj referenziert (BLOCKER, Auto-Fix JA)
- R3: EditorConfig-Regeln nicht loeschen (WARNUNG, Auto-Fix NEIN)

---

## Welle 1: Exploration

### Task 1.1: SonarAnalyzer.CSharp pruefen

**Aktion:** Fuer jede .csproj Datei im DIRTY-Scope:

1. **Lese .csproj Datei**
2. **Suche nach Pattern:**
   ```xml
   <PackageReference Include="SonarAnalyzer.CSharp"
   ```

3. **Wenn NICHT gefunden:**
   - Markiere fuer Auto-Fix
   - Speichere Dateiname

**Output Task 1.1:**
```
[BLOCKER] SonarAnalyzer.CSharp fehlt:
  1. Backend.API/Backend.API.csproj
  2. Backend.Infrastructure/Backend.Infrastructure.csproj

  Auto-Fix: Analyzer hinzufuegen (wird automatisch durchgefuehrt)
```

---

### Task 1.2: Ruleset-Referenz pruefen

**Aktion:** Fuer jede .csproj Datei im DIRTY-Scope:

1. **Lese .csproj Datei**
2. **Suche nach Pattern:**
   ```xml
   <CodeAnalysisRuleSet>
   ```

3. **Wenn NICHT gefunden:**
   - Markiere fuer Auto-Fix
   - Speichere Dateiname

4. **Pruefe auch AdditionalFiles fuer .editorconfig:**
   ```xml
   <AdditionalFiles Include="...\.editorconfig"
   ```

**Output Task 1.2:**
```
[BLOCKER] CodeAnalysisRuleSet fehlt:
  1. Backend.API/Backend.API.csproj
  2. Backend.Core/Backend.Core.csproj

[WARNUNG] .editorconfig Referenz fehlt:
  1. Backend.API/Backend.API.csproj

  Auto-Fix: Ruleset-Referenzen hinzufuegen (wird automatisch durchgefuehrt)
```

---

### Task 1.3: EditorConfig-Aenderungen pruefen

**Aktion:** Wenn .editorconfig im DIRTY-Scope:

1. **Git Diff auf .editorconfig abrufen**
   ```bash
   git diff develop...HEAD -- .editorconfig
   ```

2. **Suche nach geloeschten Analyzer-Regeln:**
   - Pattern: `^- dotnet_diagnostic\..*\.severity`
   - Pattern: `^- .*CA\d{4}.*`
   - Pattern: `^- .*SA\d{4}.*`
   - Pattern: `^- .*IDE\d{4}.*`

3. **Fuer jede geloeschte Regel:**
   - Pruefe ob Kommentar darueber (innerhalb 3 Zeilen)
   - Wenn KEIN Kommentar: WARNUNG

**Output Task 1.3:**
```
[WARNUNG] EditorConfig-Regeln geloescht ohne Begruendung:

1. **Zeile 45:**
   ```diff
   - dotnet_diagnostic.CA1031.severity = warning
   ```
   Problem: Regel geloescht ohne Kommentar
   Empfehlung: Begruendung hinzufuegen oder Regel wiederherstellen

2. **Zeile 67:**
   ```diff
   - dotnet_diagnostic.SA1200.severity = error
   + dotnet_diagnostic.SA1200.severity = none
   ```
   Problem: Severity von error → none ohne Begruendung
   Empfehlung: Kommentar hinzufuegen der Ausnahme erklaert

  Hinweis: Kein Auto-Fix, manuelle Review erforderlich
```

---

## Welle 2: Auto-Fix

### Fix 2.1: SonarAnalyzer.CSharp einfuegen

**Fuer jede .csproj ohne SonarAnalyzer.CSharp:**

**Algorithmus:**

1. **Parse XML-Struktur**
2. **Finde oder erstelle `<ItemGroup>` mit PackageReference-Elementen**
   - Suche bestehende `<ItemGroup>` mit `<PackageReference>`
   - Wenn nicht gefunden: Erstelle neue `<ItemGroup>` vor `</Project>`

3. **Fuege SonarAnalyzer.CSharp hinzu:**
   ```xml
   <PackageReference Include="SonarAnalyzer.CSharp" Version="9.12.0.78982">
     <PrivateAssets>all</PrivateAssets>
     <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
   </PackageReference>
   ```

4. **Speichere Datei mit korrekter Formatierung**
   - Behalte Einrueckung bei
   - Verwende gleiche Einrueckung wie andere PackageReferences

**Version-Ermittlung:**
- Pruefe andere .csproj Dateien im Projekt nach verwendeter Version
- Wenn nicht gefunden: Verwende neueste stabile Version (z.B. 9.12.0.78982)

**Output Fix 2.1:**
```
[AUTO-FIX] SonarAnalyzer.CSharp eingefuegt:
  1. Backend.API/Backend.API.csproj
     Version: 9.12.0.78982
  2. Backend.Infrastructure/Backend.Infrastructure.csproj
     Version: 9.12.0.78982

  Status: ERFOLG
```

---

### Fix 2.2: CodeAnalysisRuleSet einfuegen

**Fuer jede .csproj ohne CodeAnalysisRuleSet:**

**Algorithmus:**

1. **Parse XML-Struktur**
2. **Finde erste `<PropertyGroup>`**
   - Meist die mit `<TargetFramework>`

3. **Fuege CodeAnalysisRuleSet hinzu:**
   ```xml
   <CodeAnalysisRuleSet>$(SolutionDir)CodeAnalysis\DCSRE.ruleset</CodeAnalysisRuleSet>
   ```

   **Position:** Nach `<TargetFramework>` oder am Ende der PropertyGroup

4. **Speichere Datei**

**Ruleset-Pfad Ermittlung:**
- Standard: `$(SolutionDir)CodeAnalysis\DCSRE.ruleset`
- Fuer Test-Projekte: `$(SolutionDir)CodeAnalysis\DCSRE.Tests.ruleset`
- Heuristik: Projekt-Name enthaelt "Test" → Tests.ruleset

**Output Fix 2.2:**
```
[AUTO-FIX] CodeAnalysisRuleSet eingefuegt:
  1. Backend.API/Backend.API.csproj
     Ruleset: $(SolutionDir)CodeAnalysis\DCSRE.ruleset
  2. Backend.Core.Tests/Backend.Core.Tests.csproj
     Ruleset: $(SolutionDir)CodeAnalysis\DCSRE.Tests.ruleset

  Status: ERFOLG
```

---

### Fix 2.3: AdditionalFiles fuer .editorconfig einfuegen

**Fuer jede .csproj ohne .editorconfig Referenz:**

**Algorithmus:**

1. **Parse XML-Struktur**
2. **Finde oder erstelle `<ItemGroup>` mit `<AdditionalFiles>`**
   - Wenn nicht gefunden: Erstelle neue nach PropertyGroup

3. **Fuege .editorconfig Referenz hinzu:**
   ```xml
   <AdditionalFiles Include="$(SolutionDir).editorconfig" Link=".editorconfig" />
   ```

4. **Speichere Datei**

**Output Fix 2.3:**
```
[AUTO-FIX] .editorconfig Referenz eingefuegt:
  1. Backend.API/Backend.API.csproj
  2. Backend.Core/Backend.Core.csproj

  Status: ERFOLG
```

---

## Welle 3: Bericht generieren

**Berichts-Format:**

```markdown
# Pre-PR Analyzer Quality Gate Report

**Branch:** [Branch-Name]
**Datum:** [ISO-8601]
**Analysierte .csproj:** [Anzahl]

---

## Zusammenfassung

| Level | Anzahl | Status |
|-------|--------|--------|
| BLOCKER (SonarAnalyzer fehlt) | [N] | [AUTO-FIX APPLIED] |
| BLOCKER (Ruleset fehlt) | [N] | [AUTO-FIX APPLIED] |
| WARNUNG (EditorConfig) | [N] | [MANUAL REVIEW] |

**Gesamtstatus:** [PASS/FAIL]

---

## Details

### R1: SonarAnalyzer.CSharp (BLOCKER)

**Status:** [AUTO-FIX APPLIED]

**Analyzer eingefuegt in:**
1. Backend.API/Backend.API.csproj
2. Backend.Infrastructure/Backend.Infrastructure.csproj

**Version:** 9.12.0.78982

**Eingefuegter Code:**
```xml
<PackageReference Include="SonarAnalyzer.CSharp" Version="9.12.0.78982">
  <PrivateAssets>all</PrivateAssets>
  <IncludeAssets>runtime; build; native; contentfiles; analyzers; buildtransitive</IncludeAssets>
</PackageReference>
```

**Naechste Schritte:**
- `dotnet restore` ausfuehren
- Projekt rebuilden
- Neue Analyzer-Warnings beheben

---

### R2: CodeAnalysisRuleSet (BLOCKER)

**Status:** [AUTO-FIX APPLIED]

**Ruleset-Referenzen eingefuegt:**

1. **Backend.API/Backend.API.csproj**
   ```xml
   <CodeAnalysisRuleSet>$(SolutionDir)CodeAnalysis\DCSRE.ruleset</CodeAnalysisRuleSet>
   ```

2. **Backend.Core.Tests/Backend.Core.Tests.csproj**
   ```xml
   <CodeAnalysisRuleSet>$(SolutionDir)CodeAnalysis\DCSRE.Tests.ruleset</CodeAnalysisRuleSet>
   ```

**EditorConfig-Referenzen eingefuegt:**
- Backend.API/Backend.API.csproj
- Backend.Core/Backend.Core.csproj

**Naechste Schritte:**
- Pruefe ob Ruleset-Dateien existieren:
  - CodeAnalysis/DCSRE.ruleset
  - CodeAnalysis/DCSRE.Tests.ruleset
- Falls nicht: Erstelle Standard-Rulesets

---

### R3: EditorConfig-Aenderungen (WARNUNG)

**Status:** [MANUAL REVIEW REQUIRED]

**Geloeschte Regeln ohne Begruendung:**

1. **.editorconfig, Zeile 45**
   ```diff
   - dotnet_diagnostic.CA1031.severity = warning
   ```
   **Problem:** Regel geloescht ohne Kommentar
   **Empfehlung:**
   ```ini
   # CA1031: Ausnahme fuer Infrastructure-Layer
   # Catching Exception ist hier erlaubt fuer Logging
   dotnet_diagnostic.CA1031.severity = none
   ```

2. **.editorconfig, Zeile 67**
   ```diff
   - dotnet_diagnostic.SA1200.severity = error
   + dotnet_diagnostic.SA1200.severity = none
   ```
   **Problem:** Severity-Downgrade ohne Begruendung
   **Empfehlung:** Kommentar hinzufuegen oder auf error zuruecksetzen

**Naechste Schritte:**
- Fuer jede geloeschte Regel entscheiden:
  - Regel wiederherstellen ODER
  - Begruendung als Kommentar hinzufuegen
- .editorconfig committen mit Begruendungen

---

## Statistik

- **.csproj Dateien analysiert:** [N]
- **SonarAnalyzer eingefuegt:** [N]
- **Ruleset-Referenzen eingefuegt:** [N]
- **EditorConfig-Referenzen eingefuegt:** [N]
- **EditorConfig-Warnungen:** [N]

---

## Checkliste nach Auto-Fix

- [ ] `dotnet restore` ausgefuehrt
- [ ] `dotnet build` erfolgreich
- [ ] Neue Analyzer-Warnings gesichtet
- [ ] EditorConfig-Begruendungen hinzugefuegt
- [ ] Ruleset-Dateien existieren

---

**Hinweis:** Auto-Fixes fuer .csproj wurden angewendet.
EditorConfig-Aenderungen erfordern manuelle Review.
```

---

## Qualitaetskriterien

### PASS-Bedingungen
- Alle .csproj haben SonarAnalyzer.CSharp (R1 = PASS)
- Alle .csproj haben CodeAnalysisRuleSet (R2 = PASS)
- EditorConfig-Warnungen sind dokumentiert (R3 = WARNUNG, kein Blocker)

### FAIL-Bedingungen
- Nach Auto-Fix fehlt immer noch SonarAnalyzer (R1 = BLOCKER)
- Nach Auto-Fix fehlt immer noch Ruleset (R2 = BLOCKER)

### Auto-Fix Erfolg
- .csproj Dateien sind valides XML nach Edit
- `dotnet restore` laeuft ohne Fehler
- `dotnet build` zeigt Analyzer-Output

---

## Verwendung

```bash
# Standard-Ausfuehrung
/_Pre_PR_Analyzer

# Output:
# - Auto-Fixes in .csproj Dateien
# - Bericht mit EditorConfig-Warnungen
# - Exit-Code 0 bei PASS, 1 bei FAIL
```

**Erwartete Laufzeit:** 30 Sekunden - 1 Minute

---

## Debugging

**Haeufige Probleme:**

1. **"Auto-Fix hat XML zerstoert"**
   - XML-Parser validiert vor Schreiben
   - Backup wird erstellt (.csproj.backup)
   - Rollback moeglich

2. **"SonarAnalyzer Version falsch"**
   - Version wird aus anderen Projekten uebernommen
   - Manuell anpassen falls noetig
   - Oder: Zentral in Directory.Build.props definieren

3. **"Ruleset-Datei existiert nicht"**
   - Auto-Fix fuegt Referenz ein, auch wenn Datei fehlt
   - Erstelle Ruleset-Datei manuell oder mit Template
   - Template: meta/templates/DCSRE.ruleset

---

## Erweiterte Checks (Optional)

### Verify Analyzer funktioniert

```bash
# Nach Auto-Fix: Build mit Analyzer-Output
dotnet build /p:RunAnalyzersDuringBuild=true

# Erwarte: Analyzer-Warnings im Output
# z.B. "warning CA1031: Do not catch general exception types"
```

### Verify Ruleset geladen

```bash
# Pruefe ob Ruleset-Datei existiert
ls CodeAnalysis/DCSRE.ruleset

# Pruefe ob EditorConfig existiert
ls .editorconfig
```

---

**Ende des Commands**
