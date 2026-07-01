---
name: _Pre_PR_Konstanten
description: Pre-PR Konstanten Quality Gate - findet Magic Strings und Magic Numbers
type: building-block
---

# /_Pre_PR_Konstanten

**Zweck:** Magic Strings und Magic Numbers in benannte Konstanten auslagern um Lesbarkeit und Wartbarkeit zu verbessern.

**Abdeckung:** 12 Kommentare (4.4% aller Code-Review-Kommentare)

**Schwierigkeit:** NORMAL (Ceiling: sonnet, Floor: sonnet)

**Auto-Fix:** TEILWEISE (String-Literale bei 2+ Vorkommen)

---

## Vertrag

```
╔══════════════════════════════════════════════════════════════╗
║  COMMAND: /_Pre_PR_Konstanten                                ║
╠══════════════════════════════════════════════════════════════╣
║  LIEST:                                                      ║
║    1. {META}/codeKonvention/konstanten.md              ║
║    2. Git Diff (develop...HEAD)                              ║
║    3. Alle *.cs Dateien im DIRTY-Scope                       ║
║  SCHREIBT:                                                   ║
║    1. Konstanten-Klassen (Auto-generiert)                    ║
║    2. Code-Fixes fuer String-Literale                        ║
║    3. Bericht mit Empfehlungen fuer Magic Numbers (INFO)     ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: DIRTY-Scope ermitteln

**Aktion:** Git Diff analysieren.

```bash
git diff --name-status develop...HEAD -- "*.cs"
```

**Filter:**
- Nur `*.cs` Dateien
- AUSSCHLUSS: `*.Designer.cs`, `Migrations/*.cs`, `*.g.cs`

**Output:**
```
DIRTY-SCOPE: [Anzahl] CS-Dateien gefunden
```

---

## Schritt 1: Regeln lesen

**Aktion:** Konvention laden.

```bash
cat {META}/codeKonvention/konstanten.md
```

**Fehlerbehandlung:** Falls die Datei nicht existiert → FEHLER: "Knowledge-Datei {META}/codeKonvention/konstanten.md nicht gefunden. Starte _I_fanOut oder erstelle die Datei manuell." → EXIT 1

**Regeln extrahieren:**
- R1: String-Literale in Konstanten (WARNUNG, Auto-Fix TEILWEISE)
- R2: Wiederkehrende Zahlen in Konstanten (INFO, kein Auto-Fix)
- R3: Konstanten-Organisation (INFO, kein Auto-Fix)

---

## Welle 1: Exploration

### Task 1.1: String-Literale finden

**Aktion:** Alle CS-Dateien im DIRTY-Scope nach String-Literalen scannen.

**Pattern (Regex):**
```regex
# Pattern 1: String-Vergleich
(\w+)\s*(==|!=)\s*"([^"]+)"

# Pattern 2: Switch-Case
case\s+"([^"]+)"\s*:

# Pattern 3: Zuweisung
(\w+)\s*=\s*"([^"]+)"\s*;

# Pattern 4: Return
return\s+"([^"]+)"\s*;
```

**Ausschluesse:**
- Logging: `_logger.Log*("...")`
- Exception-Messages: `throw new Exception("...")`
- Format-Strings: `$"...{variable}..."`
- Einmalige Strings (nur 1 Vorkommen)
- Leere Strings: `""`
- Whitespace: `" "`, `"\n"`, `"\t"`

**Gruppierung:**
```csharp
// Beispiel-Output
String-Literal: "AKTIV"
  Vorkommen: 5
  Dateien:
    - BenutzerService.cs:45 (Vergleich)
    - BenutzerService.cs:78 (Switch-Case)
    - BenutzerController.cs:23 (Zuweisung)
    - BenutzerValidator.cs:12 (Vergleich)
    - BenutzerProvider.cs:89 (Return)

String-Literal: "GESPERRT"
  Vorkommen: 3
  Dateien:
    - BenutzerService.cs:52 (Switch-Case)
    - BenutzerService.cs:95 (Vergleich)
    - BenutzerController.cs:67 (Zuweisung)
```

**Output Task 1.1:**
```
[WARNUNG] Magic Strings gefunden: [Anzahl]
  1. "AKTIV" (5 Vorkommen)
  2. "GESPERRT" (3 Vorkommen)
  3. "BEREIT" (2 Vorkommen)

  Auto-Fix: Konstanten generieren (JA/NEIN)?
```

---

### Task 1.2: Magic Numbers finden

**Aktion:** Zahlen-Literale in relevanten Kontexten finden.

**Pattern (Regex):**
```regex
# Pattern 1: Vergleich
(\w+)\s*(==|!=|>|<|>=|<=)\s*(\d+)

# Pattern 2: Zuweisung
(\w+)\s*=\s*(\d+)\s*;

# Pattern 3: Method-Parameter
\w+\(.*,\s*(\d+)\s*\)

# Pattern 4: Dezimalzahlen
(\d+\.\d+)m?
```

**Ausschluesse:**
- Offensichtliche Werte: 0, 1, -1, 2 (bei Division/Multiplikation)
- Array-Indizes: `items[0]`, `items[1]`
- Boolean-Konvertierung: `status == 1`
- Kleine Schleifen: `for (int i = 0; i < 10; i++)`

**Heuristik fuer "Magic Number":**
1. Zahl > 10 (oder < -1)
2. Oder Dezimalzahl (ausser 0.0, 1.0)
3. Oder in Business-Logik-Kontext (nicht in Loop/Index)

**Output Task 1.2:**
```
[INFO] Magic Numbers gefunden: [Anzahl]
  1. BenutzerValidator.cs:23 → name.Length <= 50
     Empfehlung: public const int MaxBenutzerNameLaenge = 50;

  2. LoginService.cs:45 → _fehlversuche >= 3
     Empfehlung: public const int MaxLoginVersuche = 3;

  3. PreisBerechnung.cs:12 → netto * 1.19m
     Empfehlung: public const decimal MwstSatz = 0.19m;

  Hinweis: Automatische Korrektur NICHT moeglich (zu viele False Positives)
  Entwickler muss manuell entscheiden.
```

---

### Task 1.3: Bestehende Konstanten finden

**Aktion:** Suche nach bestehenden Konstanten-Klassen im Projekt.

**Pattern:**
```csharp
public static class \w+Constants
public static class \w+Status
public static class \w+Codes
```

**Zweck:** Neue Konstanten sollen in passende bestehende Klassen integriert
werden, nicht neue Klassen erstellen.

**Output Task 1.3:**
```
Bestehende Konstanten-Klassen gefunden:
  1. Constants/BenutzerConstants.cs
     → BenutzerConstants.Status (3 Konstanten)
     → BenutzerConstants.Rollen (5 Konstanten)

  2. Constants/HttpConstants.cs
     → HttpConstants.StatusCodes (10 Konstanten)

  3. Constants/ValidationConstants.cs
     → ValidationConstants.ErrorMessages (8 Konstanten)
```

---

## Welle 2: Synthese + Fix

### Fix 2.1: Konstanten-Klasse generieren/erweitern

**Algorithmus:**

1. **Gruppiere String-Literale nach Semantik**
   - Analysiere Namen und Kontext
   - Beispiel: "AKTIV", "INAKTIV", "GESPERRT" → Gruppe "Status"

2. **Pruefe bestehende Klassen**
   - Gibt es bereits `BenutzerConstants.Status`?
   - Wenn ja: Erweitere diese Klasse
   - Wenn nein: Erstelle neue Klasse

3. **Generiere Konstanten-Namen**
   - Aus String-Wert: "AKTIV" → `Aktiv`
   - Aus String-Wert: "BEREIT_ZUR_FREIGABE" → `BereitZurFreigabe`
   - PascalCase Konvention

**Beispiel-Output (Neue Klasse):**

```csharp
// Auto-generiert durch /_Pre_PR_Konstanten
// TODO: Ueberpruefen und ggf. in passende Datei verschieben

namespace DCSRE.Backend.Constants
{
    /// <summary>
    /// Konstanten fuer Benutzer-bezogene Werte.
    /// Auto-generiert - bitte Review und Integration in bestehende Struktur.
    /// </summary>
    public static class BenutzerConstants
    {
        /// <summary>
        /// Status-Werte fuer Benutzer.
        /// </summary>
        public static class Status
        {
            public const string Aktiv = "AKTIV";
            public const string Inaktiv = "INAKTIV";
            public const string Gesperrt = "GESPERRT";
            public const string Bereit = "BEREIT";
        }
    }
}
```

**Beispiel-Output (Bestehende Klasse erweitern):**

```csharp
// Bestehende Datei: Constants/BenutzerConstants.cs

public static class BenutzerConstants
{
    public static class Status
    {
        public const string Aktiv = "AKTIV";
        public const string Inaktiv = "INAKTIV";

        // NEU: Auto-generiert durch /_Pre_PR_Konstanten
        public const string Gesperrt = "GESPERRT";
        public const string Bereit = "BEREIT";
    }
}
```

---

### Fix 2.2: String-Literale ersetzen

**Fuer jedes Vorkommen eines String-Literals:**

**VORHER:**
```csharp
public class BenutzerService
{
    public bool IstAktiv(Benutzer benutzer)
    {
        return benutzer.Status == "AKTIV";
    }

    public void SetzeStatus(Benutzer benutzer, string neuerStatus)
    {
        switch (neuerStatus)
        {
            case "AKTIV":
                // Logik
                break;
            case "GESPERRT":
                // Logik
                break;
        }
    }
}
```

**NACHHER:**
```csharp
using DCSRE.Backend.Constants;

public class BenutzerService
{
    public bool IstAktiv(Benutzer benutzer)
    {
        return benutzer.Status == BenutzerConstants.Status.Aktiv;
    }

    public void SetzeStatus(Benutzer benutzer, string neuerStatus)
    {
        switch (neuerStatus)
        {
            case BenutzerConstants.Status.Aktiv:
                // Logik
                break;
            case BenutzerConstants.Status.Gesperrt:
                // Logik
                break;
        }
    }
}
```

**Auto-Fix Schritte:**
1. Using-Statement hinzufuegen (falls nicht vorhanden)
2. String-Literal durch Konstanten-Referenz ersetzen
3. Formatierung beibehalten

**Output Fix 2.2:**
```
[AUTO-FIX] String-Literale ersetzt:
  - BenutzerService.cs: 5 Ersetzungen
  - BenutzerController.cs: 3 Ersetzungen
  - BenutzerValidator.cs: 2 Ersetzungen

  Gesamt: 10 String-Literale durch Konstanten ersetzt
```

---

## Welle 3: Bericht generieren

**Berichts-Format:**

```markdown
# Pre-PR Konstanten Quality Gate Report

**Branch:** [Branch-Name]
**Datum:** [ISO-8601]
**Analysierte Dateien:** [Anzahl CS]

---

## Zusammenfassung

| Level | Anzahl | Status |
|-------|--------|--------|
| WARNUNG (String-Literale) | [N] | [AUTO-FIX APPLIED] |
| INFO (Magic Numbers) | [N] | [MANUAL REVIEW] |

**Gesamtstatus:** [PASS/FAIL]

---

## Details

### R1: String-Literale (WARNUNG)

**Status:** [AUTO-FIX APPLIED]

**Konstanten-Klassen generiert/erweitert:**

1. **BenutzerConstants.Status** (neu erstellt)
   ```csharp
   public const string Aktiv = "AKTIV";
   public const string Inaktiv = "INAKTIV";
   public const string Gesperrt = "GESPERRT";
   ```
   Dateipfad: `Constants/BenutzerConstants.cs`

**Ersetzungen:**
- BenutzerService.cs: 5 Literale → Konstanten
- BenutzerController.cs: 3 Literale → Konstanten
- BenutzerValidator.cs: 2 Literale → Konstanten

**Gesamt:** 10 String-Literale eliminiert

---

### R2: Magic Numbers (INFO)

**Status:** [MANUAL REVIEW REQUIRED]

**Gefundene Magic Numbers:**

1. **BenutzerValidator.cs:23**
   ```csharp
   // VORHER
   return name.Length <= 50;

   // EMPFEHLUNG
   public const int MaxBenutzerNameLaenge = 50;
   return name.Length <= BenutzerConstants.Limits.MaxBenutzerNameLaenge;
   ```

2. **LoginService.cs:45**
   ```csharp
   // VORHER
   if (_fehlversuche >= 3)

   // EMPFEHLUNG
   public const int MaxLoginVersuche = 3;
   if (_fehlversuche >= SecurityConstants.MaxLoginVersuche)
   ```

3. **PreisBerechnung.cs:12**
   ```csharp
   // VORHER
   return netto * 1.19m;

   // EMPFEHLUNG
   public const decimal MwstSatz = 0.19m;
   return netto * (1 + TaxConstants.MwstSatz);
   ```

**Hinweis:** Automatische Korrektur NICHT durchgefuehrt.
Entwickler muss manuell entscheiden ob Konstanten sinnvoll sind.

---

### R3: Konstanten-Organisation (INFO)

**Bestehende Struktur:**
```
/Constants
  BenutzerConstants.cs (erweitert)
  HttpConstants.cs
  ValidationConstants.cs
```

**Empfehlung:**
- Neue Konstanten in bestehende Struktur integriert
- Bei Bedarf weitere Unter-Klassen erstellen (z.B. TaxConstants)

---

## Naechste Schritte

1. **Auto-Fix Review:**
   - Pruefe generierte Konstanten-Klassen
   - Passe Konstanten-Namen ggf. an
   - Verschiebe in passende Namespace-Struktur

2. **Magic Numbers (manuell):**
   - Pruefe jede Empfehlung einzeln
   - Erstelle Konstanten wo sinnvoll
   - Dokumentiere Ausnahmen (wenn Zahl semantisch klar ist)

3. **Tests anpassen:**
   - Unit-Tests muessen ggf. Konstanten verwenden
   - Integration-Tests pruefen

---

## Statistik

- **String-Literale gefunden:** [N]
- **String-Literale eliminiert:** [N] (Auto-Fix)
- **Magic Numbers gefunden:** [N]
- **Magic Numbers eliminiert:** 0 (manuell erforderlich)
- **Konstanten-Klassen erstellt:** [N]
- **Konstanten-Klassen erweitert:** [N]

---

**Hinweis:** String-Literale wurden automatisch korrigiert.
Magic Numbers erfordern manuelle Review und Entscheidung.
```

---

## Qualitaetskriterien

### PASS-Bedingungen
- Alle String-Literale (2+ Vorkommen) wurden in Konstanten ausgelagert
- Magic Numbers wurden dokumentiert (INFO-Level, kein Blocker)

### FAIL-Bedingungen
- String-Literale (2+ Vorkommen) existieren noch nach Auto-Fix
- Auto-Fix hat Syntax-Fehler produziert

### Auto-Fix Grenzen
- **JA:** String-Literale mit 2+ Vorkommen
- **JA:** Konstanten-Klassen generieren/erweitern
- **JA:** Using-Statements hinzufuegen
- **NEIN:** Magic Numbers (zu viele False Positives)
- **NEIN:** Log-Messages
- **NEIN:** Exception-Messages
- **NEIN:** SQL-Queries

---

## Verwendung

```bash
# Standard-Ausfuehrung
/_Pre_PR_Konstanten

# Output:
# - Auto-Fix fuer String-Literale
# - Bericht mit Magic Numbers Empfehlungen
# - Exit-Code 0 bei PASS, 1 bei FAIL
```

**Erwartete Laufzeit:** 1-2 Minuten

---

## Debugging

**Haeufige Probleme:**

1. **"Falsche Konstanten-Namen"**
   - Auto-generierte Namen sind Vorschlaege
   - Manuell anpassen nach Review

2. **"String-Literal nicht erkannt"**
   - Pruefe ob Pattern zutrifft (Vergleich, Switch, Zuweisung)
   - Einmalige Strings werden ignoriert

3. **"Zu viele Magic Number Warnings"**
   - INFO-Level, kein Blocker
   - Entwickler entscheidet pro Fall

---

**Ende des Commands**
