---
type: building-block
---

# /_Pre_PR_Naming - Naming-Konventionen Quality Gate

**Pattern:** /_Pre_PR_* (Pre-PR Quality Gate)
**Zweck:** Automatische Pruefung von Naming-Konventionen vor Pull Request
**Basis:** `{META}/codeKonvention/naming.md`
**Qualitaet:** NORMAL (Floor=sonnet, Ceiling=sonnet)

---

## VERTRAG

### Eingabe

**Parameter:**
- `scope`: DIRTY-Bereich zur Pruefung (siehe DIRTY-Scope)
- `mode`: Pruefmodus (`check` | `fix` | `report`)
  - `check`: Nur Validierung, Exit-Code 1 bei Fehlern (CI-Mode)
  - `fix`: Auto-Fix wo moeglich, Report fuer Rest
  - `report`: Detaillierter Report mit Beispielen

**Kontext:**
- `{META}/codeKonvention/naming.md` (Regel-Quelle)
- Git diff bzw. DIRTY-Files
- C#-Projektdateien (*.cs)

### Ausgabe

**check-Mode (CI):**
```
EXIT 0: Alle Naming-Checks bestanden
EXIT 1: BLOCKER gefunden (Details in stderr)
```

**fix-Mode:**
```
FIXED: Liste der automatisch behobenen Violations
MANUAL: Liste der manuellen Aenderungen (fuer Developer)
```

**report-Mode:**
```markdown
# Naming-Konventionen Report

## BLOCKER (2)
- [R1] Tabellennamen Plural: Addresses.cs:12
- [R4] Dateiname != Klasse: AddressService.cs (Klasse: AddressManagementService)

## WARNUNG (1)
- [R2] Enum ohne fixe Werte: AddressType.cs:5

## INFO (0)

## Statistik
- Dateien geprueft: 47
- Violations: 3 (2 BLOCKER, 1 WARNUNG, 0 INFO)
- Auto-fixable: 0
```

### Erfolgs-Kriterien

**check-Mode:**
- BLOCKER = 0 (sonst Exit 1)
- Laufzeit < 30s fuer typischen PR (20-50 Dateien)

**fix-Mode:**
- Alle auto-fixable Violations behoben
- Korrekte C#-Syntax nach Fix
- Git-saubere Aenderungen (nur relevante Zeilen)

**report-Mode:**
- Alle 6 Regeln (R1-R6) geprueft
- Konkrete Zeilennummern
- Beispiel-Code fuer jede Violation

---

## DIRTY-SCOPE

### Strategie: Git-basiert + Fallback

**Primaer (Git-Repo):**
```bash
git diff --name-only --diff-filter=ACMR develop...HEAD | grep "\.cs$"
```

**Fallback (kein Git):**
- Alle *.cs in `Sources/Backend/**`
- Exklusive: `bin/`, `obj/`, `Migrations/`, `*.Designer.cs`

### Scope-Optionen

**1. PR-Scope (Standard):**
- Alle geaenderten CS-Dateien seit Branch-Abzweigung
- Typisch: 20-50 Dateien

**2. Full-Scope:**
- Komplettes Backend (nur in report-Mode)
- Fuer Baseline-Erstellung

**3. File-Scope:**
- Einzelne Datei (z.B. fuer IDE-Integration)
- Beispiel: `--file AddressService.cs`

---

## WELLEN

### Welle 1: Parse + Struktur (AST-Level)

**Ziel:** C#-Dateien parsen und relevante Strukturen extrahieren

**Aufgaben:**
1. CS-Dateien einlesen
2. AST parsen (Roslyn oder Regex-basiert)
3. Extrahieren:
   - Klassennamen + Dateinamen
   - Tabellennamen (TableAttribute, TableNames-Konstanten)
   - Enum-Deklarationen
   - Property-Namen
   - Methoden-Namen

**Output:**
```json
{
  "file": "Address.cs",
  "className": "Address",
  "tableName": "Addresses",
  "enums": [
    {
      "name": "AddressType",
      "values": ["Billing", "Shipping"],
      "hasExplicitValues": false,
      "hasUndefined": false
    }
  ]
}
```

**Qualitaetskriterien:**
- 100% Parser-Erfolgsrate (fail-fast bei Syntax-Errors)
- Korrekte Extraktion von TableAttribute und Konstanten

---

### Welle 2: Regel-Validierung

**Ziel:** Jede Datei gegen R1-R6 pruefen

**R1: Tabellennamen Singular**
```python
if tableName.endswith('s') and not is_irregular_plural(tableName):
    violation = {
        "rule": "R1",
        "severity": "BLOCKER",
        "message": "Tabellenname im Plural",
        "line": find_line_number(file, tableName),
        "suggestion": singularize(tableName)
    }
```

**R2: Enum fixe Zuordnungen**
```python
if enum.is_persisted() and not enum.hasExplicitValues:
    violation = {
        "rule": "R2",
        "severity": "WARNUNG",
        "message": "Enum ohne fixe Zuordnungen"
    }
```

**R3: Enum Undefined = 0**
```python
if enum.hasExplicitValues and not enum.hasUndefined:
    violation = {
        "rule": "R3",
        "severity": "WARNUNG",
        "message": "Enum ohne Undefined = 0"
    }
```

**R4: Dateiname = Klassenname**
```python
if filename != className:
    violation = {
        "rule": "R4",
        "severity": "BLOCKER",
        "message": f"Dateiname '{filename}' != Klasse '{className}'"
    }
```

**R5/R6: Semantische Checks (INFO)**
- Pattern-basiert (z.B. "StreetNumber")
- Optional, keine BLOCKER

**Output:**
```json
{
  "violations": [
    {
      "rule": "R1",
      "severity": "BLOCKER",
      "file": "Address.cs",
      "line": 12,
      "current": "Addresses",
      "suggested": "Address",
      "autoFixable": true
    }
  ]
}
```

**Qualitaetskriterien:**
- Alle BLOCKER erkannt
- False-Positive-Rate < 5%
- Korrekte Zeilennummern

---

### Welle 3: Auto-Fix (nur fix-Mode)

**Ziel:** Auto-fixable Violations beheben

**R1: Tabellennamen Auto-Fix**
```csharp
// VORHER
[Table("Addresses")]
public const string Addresses = "Addresses";

// NACHHER (Auto-Fix)
[Table("Address")]
public const string Address = "Address";
```

**Strategie:**
1. Regex-basiertes Replace
2. Nur eindeutige Matches
3. Syntax-Validierung nach Fix (Roslyn)

**R3: Undefined hinzufuegen**
```csharp
// VORHER
public enum Status
{
    Active = 1,
    Inactive = 2
}

// NACHHER
public enum Status
{
    Undefined = 0,
    Active = 1,
    Inactive = 2
}
```

**Nicht auto-fixable:**
- R2: Business-Entscheidung fuer Enum-Werte
- R4: Datei-Rename (Git-Konflikt-Risiko)
- R5/R6: Semantische Aenderungen

**Output:**
```json
{
  "fixed": [
    {
      "rule": "R1",
      "file": "Address.cs",
      "change": "Addresses -> Address"
    }
  ],
  "manualActions": [
    {
      "rule": "R4",
      "file": "AddressService.cs",
      "action": "Rename file to 'AddressManagementService.cs'"
    }
  ]
}
```

**Qualitaetskriterien:**
- Korrekte C#-Syntax nach Fix
- Keine ungewollten Aenderungen
- Git-diff nur relevante Zeilen

---

### Welle 4: Report-Generierung

**Ziel:** Entwickler-freundlicher Report

**check-Mode (CI):**
```
[BLOCKER] R1: Tabellennamen Plural in Address.cs:12
  Aktuell: "Addresses"
  Erwartet: "Address"

[BLOCKER] R4: Dateiname != Klassenname in AddressService.cs
  Datei: AddressService.cs
  Klasse: AddressManagementService
  Aktion: Datei umbenennen

RESULT: 2 BLOCKER - Pre-PR Check FAILED
```

**fix-Mode:**
```
AUTO-FIXED (1):
  [R1] Address.cs:12 - Addresses -> Address

MANUAL ACTION REQUIRED (1):
  [R4] AddressService.cs - Rename file to AddressManagementService.cs

RESULT: 1 auto-fixed, 1 manual action
```

**report-Mode:**
- Markdown-Report (siehe Vertrag/Ausgabe)
- Gruppierung nach Severity
- Statistik + Trend (wenn History vorhanden)

**Qualitaetskriterien:**
- Klare Handlungsanweisungen
- Konkrete Codebeispiele
- Verlinkung zu Regel-Dokumentation

---

## QUALITAETSKRITERIEN

### Funktional

**Korrektheit:**
- [x] Alle 6 Regeln (R1-R6) implementiert
- [x] BLOCKER korrekt erkannt (R1, R4)
- [x] Auto-Fix nur fuer R1, R3 (teilweise)
- [x] False-Positive-Rate < 5%

**Performance:**
- [x] < 30s fuer 50 Dateien (check-Mode)
- [x] < 60s fuer 50 Dateien (fix-Mode)
- [x] Inkrementell (nur DIRTY-Files)

**Robustheit:**
- [x] Graceful Degradation bei Parse-Errors
- [x] Keine Aenderungen bei Unsicherheit
- [x] Rollback bei Syntax-Error nach Fix

### CI-Integration

**Pre-PR Quality Gate:**
```yaml
# .github/workflows/pre-pr.yml
- name: Naming Conventions Check
  run: |
    claude run _Pre_PR_Naming --mode check --scope pr
  # Exit 1 bei BLOCKER -> PR blockiert
```

**Exit-Codes:**
- `0`: Alle Checks bestanden
- `1`: BLOCKER gefunden
- `2`: Tool-Fehler (z.B. Parse-Error)

**Developer-Workflow:**
```bash
# Vor PR: Auto-Fix
claude run _Pre_PR_Naming --mode fix --scope pr

# Report fuer komplettes Backend
claude run _Pre_PR_Naming --mode report --scope full
```

---

## IMPLEMENTIERUNGS-HINWEISE

### Parser-Strategie

**Option 1: Roslyn (empfohlen)**
- Vollstaendiger C#-AST
- Syntax-Validierung integriert
- Aber: Roslyn-Dependency noetig

**Option 2: Regex-basiert**
- Lightweight
- Schnell fuer simple Patterns (R1, R4)
- Aber: Fragil bei komplexen Faellen

**Empfehlung:** Hybrid
- Roslyn fuer Enum-Analyse (R2, R3)
- Regex fuer Tabellennamen (R1) und Dateinamen (R4)

### Edge Cases

**R1: Irregular Plurals**
```python
IRREGULAR_PLURALS = {
    "Address": "Addresses",  # Aber: Singular-Form bevorzugt!
    "Person": "People",
    "Child": "Children"
}
```

**R2: Enum-Persistence-Detection**
- Heuristik: Enum in Entity-Property -> wahrscheinlich persistiert
- Oder: Explizite Annotation `[Persisted]` (Custom-Attribute)

**R4: Partial Classes**
- Dateiname darf `.partial.cs` Suffix haben
- Beispiel: `Address.partial.cs` fuer `Address` OK

### Testing

**Unit-Tests:**
- Jede Regel einzeln testbar
- Fixtures mit VORHER/NACHHER-Code
- Edge-Cases abdecken

**Integration-Tests:**
- Reale PR-Diffs
- CI-Workflow simulieren
- Performance-Benchmarks

---

## METADATEN

**Erstellt:** 2026-02-06
**Autor:** Pre-PR Quality Gate System
**Basis:** Christian's Code-Reviews (35 Kommentare, 12.8%)
**Version:** 1.0
**Quality-Level:** NORMAL (sonnet/sonnet)

**Abhaengigkeiten:**
- `{META}/codeKonvention/naming.md` (MUSS existieren - Falls nicht gefunden → FEHLER: "Knowledge-Datei {META}/codeKonvention/naming.md nicht gefunden. Starte _I_fanOut oder erstelle die Datei manuell." → EXIT 1)
- Git (optional, fuer DIRTY-Scope)
- C#-Projekt (*.cs-Dateien)

**Verwandte Commands:**
- `_Pre_PR_Structure` (geplant, 14.6%)
- `_Pre_PR_Comments` (geplant, 10.9%)
- `_Pre_PR_Full` (kombiniert alle Checks)
