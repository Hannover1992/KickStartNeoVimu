---
name: _Pre_PR_Dokumentation
description: Pre-PR Dokumentation Quality Gate - prueft XML-Dokumentation und Markdown-Struktur
type: building-block
---

# /_Pre_PR_Dokumentation

**Zweck:** Sicherstellen dass Code-Dokumentation vollstaendig ist und XML-Referenzen nicht versehentlich durch KI-Tools zerstoert wurden.

**Abdeckung:** 16 Kommentare (5.8% aller Code-Review-Kommentare)

**Schwierigkeit:** NORMAL (Ceiling: sonnet, Floor: sonnet)

**Auto-Fix:** TEILWEISE (Geruest fuer XML-Docs, Markdown-Formatierung)

---

## KRITISCH: Umlaute in XML-Dokumentation

```
ECHTE UMLAUTE (ä, ö, ü, ß) MUESSEN BLEIBEN!

  ✗ VERBOTEN: "fuer", "oeffentlich", "ueber", "Groesse"
  ✓ RICHTIG:  "für",  "öffentlich",  "über",  "Größe"

  XML-Docs in C#-Dateien verwenden IMMER echte Unicode-Umlaute.
  NIEMALS ä→ae, ö→oe, ü→ue, ß→ss konvertieren.

  NUR in .md Command-Dateien (wie dieser hier) werden ASCII-Umlaute
  verwendet — weil Commands als Prompts gelesen werden.

  Zusammenfassung:
    *.cs XML-Docs  → echte Umlaute (ä, ö, ü, ß)
    *.md Commands   → ASCII-Umlaute (ae, oe, ue, ss)
```

---

## Vertrag

```
╔══════════════════════════════════════════════════════════════╗
║  COMMAND: /_Pre_PR_Dokumentation                             ║
╠══════════════════════════════════════════════════════════════╣
║  LIEST:                                                      ║
║    1. {META}/codeKonvention/dokumentation.md           ║
║    2. Git Diff (develop...HEAD)                              ║
║    3. Alle *.cs und *.md Dateien im DIRTY-Scope              ║
║  SCHREIBT:                                                   ║
║    1. XML-Dokumentations-Gerueste (TODO-Marker)              ║
║    2. Markdown-Formatierung-Fixes                            ║
║    3. Bericht mit BLOCKER fuer geloeschte see-cref Tags      ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: DIRTY-Scope ermitteln

**Aktion:** Git Diff analysieren.

```bash
# Im Backend-Root ausfuehren
git diff --name-status develop...HEAD
```

**Filter fuer Dokumentations-relevante Dateien:**
- `*.cs` (C#-Dateien mit XML-Dokumentation)
- `*.md` (Markdown-Dateien)
- AUSSCHLUSS: `*.Designer.cs`, `Migrations/*.cs`

**Output:**
```
DIRTY-SCOPE: [Anzahl] Dateien gefunden
  CS-Dateien: [Anzahl]
  MD-Dateien: [Anzahl]
```

---

## Schritt 1: Regeln lesen

**Aktion:** Konvention laden.

```bash
cat {META}/codeKonvention/dokumentation.md
```

**Fehlerbehandlung:** Falls die Datei nicht existiert → FEHLER: "Knowledge-Datei {META}/codeKonvention/dokumentation.md nicht gefunden. Starte _I_fanOut oder erstelle die Datei manuell." → EXIT 1

**Regeln extrahieren:**
- R1: XML see-cref Referenzen (BLOCKER, kein Auto-Fix)
- R2: Public Members XML-Dokumentation (WARNUNG, Auto-Fix TEILWEISE)
- R3: Markdown-Struktur (WARNUNG, Auto-Fix TEILWEISE)
- R4: Kryptische interne Referenzen in XML-Docs (WARNUNG, Auto-Fix JA)
- R5: Ausgeschriebene Umlaute in XML-Kommentaren (FAIL, kein Auto-Fix)

---

## Welle 1: Exploration

### Task 1.1: Geloeschte see-cref Tags finden (BLOCKER)

**Aktion:** Git Diff Zeile-fuer-Zeile analysieren.

**Pattern:**
```diff
# KRITISCH: Geloeschte see-cref Tags
- /// Verwendet <see cref="IBenutzerProvider"/> fuer Zugriff.
+ /// Verwendet IBenutzerProvider fuer Zugriff.

# ODER
- /// <param name="benutzer">Die <see cref="Benutzer"/>-Instanz.</param>
+ /// <param name="benutzer">Die Benutzer-Instanz.</param>

# ODER
- /// Wirft <see cref="ValidationException"/> bei Fehler.
+ /// Wirft ValidationException bei Fehler.
```

**Algorithmus:**
1. Extrahiere alle Diff-Chunks mit `///` Zeilen
2. Fuer jede geloeschte Zeile (`-`):
   - Enthaelt sie `<see cref="`?
   - Gibt es eine hinzugefuegte Zeile (`+`) mit aehnlichem Text?
   - Fehlt in der neuen Zeile das `<see cref=` Tag?
3. Wenn ja: BLOCKER-Finding erstellen

**Output Task 1.1:**
```
[BLOCKER] Datei: BenutzerService.cs, Zeile 45
  VORHER: /// Verwendet <see cref="IBenutzerProvider"/> fuer Zugriff.
  NACHHER: /// Verwendet IBenutzerProvider fuer Zugriff.
  Problem: XML-Referenz wurde entfernt (vermutlich durch KI-Tool)
  Action: Manuell wiederherstellen
```

**Wenn Blocker gefunden:**
- Sofortiger Abbruch (FAIL)
- Keine Auto-Fixes durchfuehren
- Bericht mit allen Blocker-Stellen generieren

---

### Task 1.2: Fehlende XML-Dokumentation finden

**Aktion:** Alle CS-Dateien im DIRTY-Scope scannen.

**Pattern:**
```csharp
// Suche nach public Members OHNE XML-Docs darüber

// Klassen
public class Benutzer
// Prüfe: Steht darüber "/// <summary>"?

// Properties
public int Id { get; set; }
// Prüfe: Steht darüber "/// <summary>"?

// Methoden
public async Task<Benutzer> GetByIdAsync(int id)
// Prüfe: Steht darüber "/// <summary>"?
```

**Regex-Patterns:**
```regex
# Klasse ohne XML-Doc
^(?!.*\/\/\/.*\n).*public\s+(class|interface|enum)\s+\w+

# Property ohne XML-Doc
^(?!.*\/\/\/.*\n).*public\s+\w+\s+\w+\s*\{\s*get;

# Methode ohne XML-Doc
^(?!.*\/\/\/.*\n).*public\s+.*\s+\w+\s*\(
```

**Output Task 1.2:**
```
[WARNUNG] Fehlende XML-Dokumentation:
  1. BenutzerService.cs:23 - public class BenutzerService
  2. BenutzerService.cs:45 - public async Task<Benutzer> GetByIdAsync(int id)
  3. Benutzer.cs:12 - public int Id { get; set; }

  Anzahl: 3 undokumentierte Members
  Auto-Fix: Geruest einfuegen (JA/NEIN)?
```

---

### Task 1.3: Markdown-Struktur pruefen

**Aktion:** Alle MD-Dateien im DIRTY-Scope scannen.

**Pruefungen:**

1. **Ueberschriften-Hierarchie**
```markdown
# H1
#### H4  ← FEHLER: H2 und H3 uebersprungen
```

2. **Code-Blocks ohne Sprach-Tag**
```markdown
```
dotnet build
```
← FEHLER: Sollte ```bash sein
```

3. **Unvollstaendige Tabellen**
```markdown
| Spalte1 | Spalte2 |
|---------|---------|
| Wert1   | Wert2
← FEHLER: Fehlende Pipe am Ende
```

**Output Task 1.3:**
```
[WARNUNG] Markdown-Probleme in README.md:
  1. Zeile 15: Ueberschriften-Sprung H1 → H4
  2. Zeile 23: Code-Block ohne Sprach-Tag
  3. Zeile 45: Unvollstaendige Tabellen-Zeile

  Auto-Fix: Formatierung korrigieren (JA/NEIN)?
```

---

### Task 1.4: Kryptische interne Referenzen finden (R4)

**Aktion:** Alle XML-Summaries in CS-Dateien auf interne Referenzen pruefen.

**VERBOTENE Muster in XML-Docs:**
```
KRYPTISCH (Reviewer versteht es NICHT):
  ✗ T0, T1, T2, ... T{N}           (Test-IDs aus PLANs)
  ✗ S1, S2, ... S{N}               (Slice-Nummern)
  ✗ W1, W2, ... W{N}               (Wahrheiten aus Model)
  ✗ AK1, AK2, ...                  (Akzeptanzkriterien-IDs)
  ✗ ST1, ST2, ...                  (Sub-Test-IDs)
  ✗ Slice4, Slice-1, ...           (Slice-Referenzen)
  ✗ PLAN.md, ATOMIC.md, VERIFY.md  (interne Pipeline-Dokumente)
  ✗ Referenz: {DATEI}.md           (Referenzen auf .md Dateien)
  ✗ "ist das FUNDAMENT"            (interne Jargon-Sprache)
  ✗ GRAY/ORANGE/RED Pattern        (interne Komplexitaets-Level)

RICHTIG (Reviewer versteht es SOFORT):
  ✓ Einfaches Deutsch: was tut die Klasse/Methode?
  ✓ Fachbegriffe nur wenn noetig (MinIO, AutoMapper, EF Core)
  ✓ Kurz und praegnant (1-2 Saetze)
```

**Beispiel VORHER (kryptisch):**
```csharp
/// <summary>
/// MinIO Canary Tests  Verifiziert dass die MinIO Container-Infrastruktur funktioniert.
/// T0 ist das FUNDAMENT: Wenn T0 fehlschlaegt, ist die Infrastruktur kaputt.
/// Referenz: DIC-IntegrationTests-Slice4-E2E-HappyPath-PLAN.md, T0.
/// </summary>
```

**Beispiel NACHHER (klar):**
```csharp
/// <summary>
/// Verifiziert die MinIO-Objektspeicher-Infrastruktur.
/// Grundlegender Konnektivitaetstest — wenn dieser fehlschlaegt,
/// ist der Objektspeicher nicht verfuegbar.
/// </summary>
```

**Regex-Patterns fuer Erkennung:**
```regex
# Test-IDs: T0, T1, T15, ST1
\b[ST]T?\d{1,3}\b

# Slice-Referenzen: S1, Slice4, Slice-2
\b(S\d{1,2}|Slice[-_]?\d{1,2})\b

# Wahrheiten/AK: W1, W12, AK1, AK15
\b(W|AK)\d{1,3}\b

# Interne Dokument-Referenzen: PLAN.md, ATOMIC.md, VERIFY.md
\b\w+[-_]?(PLAN|ATOMIC|VERIFY|MODEL|SPEC|GAP|ARCHITECT)\b
\bReferenz:.*\.md\b
```

**Auto-Fix Strategie:**
```
1. Kryptische Referenzen ENTFERNEN (nicht ersetzen — Halluzinationsrisiko)
2. Summary auf Kern-Aussage reduzieren
3. Falls Summary danach LEER → TODO-Marker setzen:
   /// <summary>
   /// TODO: Beschreibung in einfachem Deutsch verfassen.
   /// </summary>
4. Falls Summary noch sinnvollen Rest hat → bereinigt beibehalten
```

**Output Task 1.4:**
```
[WARNUNG] Kryptische Referenzen in XML-Dokumentation:
  1. MinioCanaryTests.cs:12 — "T0 ist das FUNDAMENT" + "Referenz: ...PLAN.md"
     Auto-Fix: Kryptische Teile entfernt, Kern-Aussage beibehalten
  2. DicImportIntegrationTests_S4.cs:8 — "S4", "Slice4", "T1-T5"
     Auto-Fix: Interne Referenzen entfernt

  Anzahl: 2 Dateien mit kryptischen Referenzen
```

---

### Task 1.5: Ausgeschriebene Umlaute in XML-Kommentaren finden (R5) (CaseStudy DCSRE-1430)

**Aktion:** Alle CS-Dateien im DIRTY-Scope auf ASCII-Umlaute innerhalb von XML-Kommentar-Bloecken scannen.

**Hintergrund:** In DCSRE-1430 mussten 6+ Dateien manuell gefixt werden (z.B. `Prueft→Prüft`, `durchlaeuft→durchläuft`). XML-Summaries MUESSEN echte Umlaute verwenden.

**Scan-Bereich:** NUR innerhalb von `/// <summary>...</summary>`, `/// <param>`, `/// <returns>`, `/// <remarks>` und anderen XML-Doc-Bloecken. NICHT scannen: Code-Zeilen, Variablennamen, Methodennamen.

**Pattern-Liste (haeufigste Faelle):**
```
# FAIL-Pattern → korrektes Umlaut
Prueft|prueft          → Prüft|prüft
Ueberprueft            → Überprüft
ueberprueft            → überprüft
Aendern|aendern        → Ändern|ändern
Aenderung              → Änderung
Loeschen|loeschen      → Löschen|löschen
Rueckgabe|rueckgabe    → Rückgabe|rückgabe
durchlaeuft            → durchläuft
uebergibt              → übergibt
Uebersicht             → Übersicht
zurueck                → zurück
fuer                   → für  (NUR in XML-Kommentaren, NICHT in Code)
```

**Regex-Pattern fuer Erkennung (nur in /// Zeilen):**
```regex
# Zeile ist ein XML-Kommentar (beginnt mit optionalem Whitespace + ///)
^(\s*\/\/\/.*)(Prueft|prueft|Ueberprueft|ueberprueft|Aendern|aendern|Aenderung|Loeschen|loeschen|Rueckgabe|rueckgabe|durchlaeuft|uebergibt|Uebersicht|zurueck|\bfuer\b)
```

**Algorithmus:**
1. Extrahiere alle Zeilen die mit `///` beginnen (XML-Doc-Zeilen)
2. Pruefe jede Zeile gegen die Pattern-Liste
3. Fuer jeden Treffer: FAIL-Finding mit konkretem Fix-Vorschlag erstellen
4. Beachte: `fuer` nur flaggen wenn es als deutsches Wort vorkommt (nicht in Code-Identifier-Kontext innerhalb von `<see cref="..."/>`)

**NICHT flaggen:**
- Code-Identifier in `<see cref="..."/>` Tags (z.B. `<see cref="PrueftVerbindung"/>`)
- Parameter-Namen in `<param name="...">` Attribut (der Name selbst, nicht der Inhalt)
- Zeilen die kein `///` haben (normaler Code)

**Output Task 1.5:**
```
[FAIL] Ausgeschriebene Umlaute in XML-Dokumentation (R5):
  1. DateiabholungService.cs:45 — "Prueft ob die Verbindung aktiv ist"
     Fix: "Prüft ob die Verbindung aktiv ist"
  2. AbrufController.cs:112 — "durchlaeuft alle Eintraege"
     Fix: "durchläuft alle Einträge"
  3. ImportHelper.cs:78 — "Rueckgabe des Status-Objekts"
     Fix: "Rückgabe des Status-Objekts"

  Anzahl: 3 Stellen mit ASCII-Umlauten in XML-Kommentaren
  Auto-Fix: NEIN (Entwickler muss manuell korrigieren — Kontext-Verstaendnis erforderlich)
```

**Wenn FAIL gefunden:**
- Status = FAIL (nicht BLOCKER, aber Pflicht-Korrektur vor Merge)
- Kein Auto-Fix (zu hohes Risiko fuer falsche Ersetzungen in Randfaellen)
- Konkreten Fix-Vorschlag pro Fundstelle ausgeben (Datei + Zeile + Alt → Neu)

---

## Welle 2: Synthese + Fix

### Fix 2.1: XML-Dokumentations-Gerueste einfuegen

**Nur wenn Task 1.1 KEINE Blocker gefunden hat!**

**Fuer jeden undokumentierten Member aus Task 1.2:**

**Klassen:**
```csharp
/// <summary>
/// TODO: Beschreibung fuer BenutzerService
/// </summary>
public class BenutzerService
{
    // ...
}
```

**Properties:**
```csharp
/// <summary>
/// TODO: Beschreibung fuer Id
/// </summary>
public int Id { get; set; }
```

**Methoden:**
```csharp
/// <summary>
/// TODO: Beschreibung fuer GetByIdAsync
/// </summary>
/// <param name="id">TODO: Beschreibung fuer Parameter id</param>
/// <returns>TODO: Beschreibung fuer Return-Wert</returns>
public async Task<Benutzer> GetByIdAsync(int id)
{
    // ...
}
```

**WICHTIG:**
- TODO-Marker einfuegen
- Entwickler MUSS TODOs vor Merge aufloesen
- Keine Halluzination von Beschreibungen (nur Geruest)

**Output Fix 2.1:**
```
[AUTO-FIX] XML-Dokumentation Gerueste eingefuegt:
  - BenutzerService.cs: 5 Members dokumentiert (TODO-Marker)
  - Benutzer.cs: 3 Properties dokumentiert (TODO-Marker)

  Action: Entwickler muss TODOs mit echten Beschreibungen ersetzen
```

---

### Fix 2.2: Markdown-Formatierung korrigieren

**Fuer jedes Problem aus Task 1.3:**

1. **Ueberschriften-Hierarchie reparieren**
```markdown
# H1
## H2  ← Eingefuegt
### H3  ← Eingefuegt
#### H4
```

2. **Code-Block Sprach-Tags ergaenzen**
```markdown
# Heuristik:
# - dotnet/nuget → bash
# - using/namespace → csharp
# - { "key": → json

```bash
dotnet build
```
```

3. **Tabellen vervollstaendigen**
```markdown
| Spalte1 | Spalte2 |
|---------|---------|
| Wert1   | Wert2   |
```

**Output Fix 2.2:**
```
[AUTO-FIX] Markdown-Formatierung korrigiert:
  - README.md: 3 Ueberschriften-Ebenen eingefuegt
  - README.md: 2 Code-Blocks getaggt
  - README.md: 1 Tabellen-Zeile vervollstaendigt
```

---

## Welle 3: Bericht generieren

**Berichts-Format:**

```markdown
# Pre-PR Dokumentation Quality Gate Report

**Branch:** [Branch-Name]
**Datum:** [ISO-8601]
**Analysierte Dateien:** [Anzahl CS + MD]

---

## Zusammenfassung

| Level | Anzahl | Status |
|-------|--------|--------|
| BLOCKER | [N] | [PASS/FAIL] |
| WARNUNG | [N] | [PASS/FAIL] |
| AUTO-FIX | [N] | [APPLIED] |

**Gesamtstatus:** [PASS/FAIL]

---

## Details

### R1: XML see-cref Referenzen (BLOCKER)

**Status:** [PASS/FAIL]

[Wenn FAIL:]
Die folgenden see-cref Tags wurden entfernt und MÜSSEN wiederhergestellt werden:

1. **Datei:** BenutzerService.cs, Zeile 45
   ```diff
   - /// Verwendet <see cref="IBenutzerProvider"/> fuer Zugriff.
   + /// Verwendet IBenutzerProvider fuer Zugriff.
   ```
   **Action:** Manuell korrigieren - <see cref="IBenutzerProvider"/> wiederherstellen

[Weitere Blocker...]

**Naechste Schritte:**
- Alle see-cref Tags wiederherstellen
- Git Diff manuell pruefen vor naechstem Commit
- /_Pre_PR_Dokumentation erneut ausfuehren

---

### R2: Public Members XML-Dokumentation (WARNUNG)

**Status:** [AUTO-FIX APPLIED]

**Gerueste eingefuegt fuer:**
- BenutzerService.cs: 5 Members
- Benutzer.cs: 3 Properties

**TODO-Marker:** 8 Stellen

**Naechste Schritte:**
- Alle TODO-Marker mit echten Beschreibungen ersetzen
- Ggf. <see cref="..."/> Referenzen hinzufuegen
- Bei Methoden: Parameter und Return-Werte dokumentieren

---

### R3: Markdown-Struktur (WARNUNG)

**Status:** [AUTO-FIX APPLIED]

**Korrekturen:**
- README.md: Ueberschriften-Hierarchie repariert
- README.md: Code-Blocks getaggt
- README.md: Tabellen vervollstaendigt

**Naechste Schritte:**
- Markdown-Dateien manuell pruefen
- Inhaltliche Luecken ergaenzen

---

### R5: Ausgeschriebene Umlaute in XML-Kommentaren (FAIL)

**Status:** [PASS/FAIL]

[Wenn FAIL:]
Die folgenden XML-Kommentare enthalten ASCII-Umlaute und MUESSEN manuell korrigiert werden:

1. **Datei:** DateiabholungService.cs, Zeile 45
   ```diff
   - /// Prueft ob die Verbindung aktiv ist
   + /// Prüft ob die Verbindung aktiv ist
   ```

2. **Datei:** AbrufController.cs, Zeile 112
   ```diff
   - /// durchlaeuft alle Eintraege
   + /// durchläuft alle Einträge
   ```

[Weitere Fundstellen...]

**Naechste Schritte:**
- Alle gemeldeten Stellen manuell im Editor korrigieren
- Echte Unicode-Umlaute eintippen (ä, ö, ü, Ä, Ö, Ü, ß)
- /_Pre_PR_Dokumentation erneut ausfuehren

---

## Statistik

- **Geloeschte see-cref Tags:** [N] (KRITISCH)
- **Undokumentierte Members:** [N] (Auto-Fix angewendet)
- **Markdown-Probleme:** [N] (Auto-Fix angewendet)
- **TODO-Marker eingefuegt:** [N] (Entwickler-Action erforderlich)
- **ASCII-Umlaute in XML-Kommentaren:** [N] (Manuell zu korrigieren)

---

**Hinweis:** Bei BLOCKER-Status muessen alle Probleme manuell behoben werden
bevor das Quality Gate PASS meldet.
```

---

## Qualitaetskriterien

### PASS-Bedingungen
- KEINE geloeschten `<see cref=` Tags (R1 = PASS)
- Alle public Members haben XML-Docs (manuell oder Auto-Fix Geruest)
- Markdown-Formatierung konsistent
- KEINE kryptischen internen Referenzen in XML-Docs (R4 = PASS)
- Alle Summaries in einfachem Deutsch (beschreiben WAS die Funktion tut)
- KEINE ASCII-Umlaute (ae, oe, ue, ss) in XML-Kommentaren (R5 = PASS)

### FAIL-Bedingungen
- Mindestens ein geloeschter `<see cref=` Tag (R1 = BLOCKER)
- Mindestens eine Stelle mit ASCII-Umlaut in XML-Kommentar (R5 = FAIL)

### Auto-Fix Grenzen
- **JA:** XML-Geruest mit TODO-Marker
- **JA:** Markdown-Formatierung
- **NEIN:** see-cref Tags wiederherstellen (zu komplex, Typnamen mehrdeutig)
- **NEIN:** Inhaltliche Beschreibungen generieren (Halluzinations-Risiko)

---

## Verwendung

```bash
# Standard-Ausfuehrung
/_Pre_PR_Dokumentation

# Output:
# - Bericht als Markdown
# - Auto-Fixes in betroffenen Dateien
# - Exit-Code 0 bei PASS, 1 bei FAIL (Blocker)
```

**Erwartete Laufzeit:** 1-3 Minuten

---

## Debugging

**Haeufige Probleme:**

1. **"Falsche see-cref Blocker"**
   - Pruefe ob Diff-Kontext korrekt erkannt wurde
   - Manuell Git Diff pruefen: `git diff develop...HEAD -- *.cs`

2. **"TODO-Marker nicht eingefuegt"**
   - Pruefe ob Member wirklich public ist
   - Private/internal Members benoetigen keine XML-Docs

3. **"Markdown-Fix zerstoert Code-Beispiele"**
   - Pruefe ob Code-Blocks korrekt erkannt wurden
   - Manuell nachbessern falls Heuristik falsch lag

---

**Ende des Commands**
