---
name: _Pre_PR_Migration
description: Pre-PR Migration Quality Gate - prueft Entity Framework Migrationen auf korrekte Down()-Implementierung und Integritaet
type: building-block
---

# /_Pre_PR_Migration

**Zweck:** Sicherstellen dass Entity Framework Migrationen korrekt implementiert sind und keine bestehenden Migrationen geaendert wurden.

**Abdeckung:** 7 Kommentare (2.6% aller Code-Review-Kommentare)

**Schwierigkeit:** HARD (Ceiling: opus, Floor: sonnet)

**Auto-Fix:** NEIN (zu hohes Risiko bei Datenbank-Operationen)

---

## Vertrag

```
╔══════════════════════════════════════════════════════════════╗
║  COMMAND: /_Pre_PR_Migration                                 ║
╠══════════════════════════════════════════════════════════════╣
║  LIEST:                                                      ║
║    1. {META}/codeKonvention/migration.md               ║
║    2. Git Diff (develop...HEAD)                              ║
║    3. Migrations/*.cs Dateien                                ║
║  SCHREIBT:                                                   ║
║    1. Bericht mit BLOCKER bei Fehlern                        ║
║    2. KEINE Code-Fixes (zu hohes Risiko)                     ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: DIRTY-Scope ermitteln

**Aktion:** Git Diff auf Migration-Dateien analysieren.

```bash
git diff --name-status develop...HEAD -- "Migrations/*.cs"
```

**Kategorisierung:**
```
A Migrations/20240115120000_AddBenutzerEmail.cs      → NEUE Migration
M Migrations/20240101120000_InitialCreate.cs         → GEAENDERTE Migration (VERDACHT!)
A Migrations/20240115120000_AddBenutzerEmail.Designer.cs → OK (Auto-generiert)
```

**Output:**
```
DIRTY-SCOPE: [Anzahl] Migration-Dateien
  Neue Migrationen: [N] (Status A)
  Geaenderte Migrationen: [N] (Status M) ← KRITISCH
```

---

## Schritt 1: Regeln lesen

**Aktion:** Konvention laden.

```bash
cat {META}/codeKonvention/migration.md
```

**Fehlerbehandlung:** Falls die Datei nicht existiert → FEHLER: "Knowledge-Datei {META}/codeKonvention/migration.md nicht gefunden. Starte _I_fanOut oder erstelle die Datei manuell." → EXIT 1

**Regeln extrahieren:**
- R1: Down() muss exaktes Gegenteil von Up() sein (BLOCKER)
- R2: Bestehende Migrationen NICHT aendern (BLOCKER)
- R3: Test-Daten deterministisch (WARNUNG)

---

## Welle 1: Exploration

### Task 1.1: Geaenderte Migrationen finden (BLOCKER)

**Aktion:** Git Diff auf Modified-Status pruefen.

**Pattern:**
```bash
# Finde alle M (Modified) Migrations
git diff --name-status develop...HEAD | grep "^M.*Migrations/.*\.cs$"
```

**Ausschluss:**
- `*.Designer.cs` Dateien (Auto-generiert, Aenderungen OK)

**Pruefung fuer jede geaenderte Migration:**
1. Datei lesen
2. Git Diff anzeigen
3. Wurde Up() oder Down() geaendert?

**BLOCKER wenn:**
- Up() Methode geaendert
- Down() Methode geaendert
- Migration ist nicht vom aktuellen Branch (Timestamp-Pruefung)

**Output Task 1.1:**
```
[BLOCKER] Geaenderte Migrationen gefunden:

1. **Migrations/20240101120000_InitialCreate.cs**
   Status: MODIFIED
   Diff:
   ```diff
   protected override void Up(MigrationBuilder migrationBuilder)
   {
   -   nullable: true
   +   nullable: false
   }
   ```

   Problem: Bestehende Migration wurde geaendert
   Action: Aenderung in NEUE Migration auslagern
   Command: Revert + neue Migration erstellen

---
SOFORTIGER ABBRUCH bei Blocker!
---
```

**Wenn Blocker gefunden:**
- Keine weiteren Tasks ausfuehren
- Sofort Bericht generieren
- Exit-Code 1

---

### Task 1.2: Up() und Down() Operationen extrahieren

**Aktion:** Fuer jede NEUE Migration (Status A):

**Parsing-Algorithmus:**

1. **Lese Migration-Datei**
2. **Extrahiere Up() Methode:**
   - Finde `protected override void Up(MigrationBuilder migrationBuilder)`
   - Extrahiere alle `migrationBuilder.*` Aufrufe
   - Speichere in Liste: `UpOperations[]`

3. **Extrahiere Down() Methode:**
   - Finde `protected override void Down(MigrationBuilder migrationBuilder)`
   - Extrahiere alle `migrationBuilder.*` Aufrufe
   - Speichere in Liste: `DownOperations[]`

**Operation-Typen:**
- AddColumn
- DropColumn
- CreateTable
- DropTable
- CreateIndex
- DropIndex
- AddForeignKey
- DropForeignKey
- AlterColumn
- Sql

**Output Task 1.2:**
```
Migration: 20240115120000_AddBenutzerEmail.cs

Up() Operationen (3):
  1. AddColumn: Benutzer.Email (nvarchar(100), nullable: false)
  2. Sql: UPDATE Benutzer SET Email = '...'
  3. CreateIndex: IX_Benutzer_Email (unique: true)

Down() Operationen (2):
  1. DropIndex: IX_Benutzer_Email
  2. DropColumn: Benutzer.Email
```

---

### Task 1.3: Down() Vollstaendigkeit pruefen (BLOCKER)

**Aktion:** Pruefe ob jede Up() Operation eine Gegenaktion in Down() hat.

**Mapping-Tabelle:**
```
Up() Operation          →  Down() Gegenaktion
=====================================
AddColumn               →  DropColumn
DropColumn              →  AddColumn
CreateTable             →  DropTable
DropTable               →  CreateTable
CreateIndex             →  DropIndex
DropIndex               →  CreateIndex
AddForeignKey           →  DropForeignKey
DropForeignKey          →  AddForeignKey
AlterColumn             →  AlterColumn (mit alten Werten)
Sql("CREATE ...")       →  Sql("DROP ...")
InsertData              →  DeleteData
```

**Algorithmus:**

1. **Fuer jede Operation in Up():**
   - Bestimme erwartete Gegenaktion
   - Suche Gegenaktion in Down()
   - Pruefe Parameter (Tabelle, Spalte, Name)

2. **Pruefe Reihenfolge:**
   - Down()[0] sollte Gegenteil von Up()[N-1] sein
   - Down()[1] sollte Gegenteil von Up()[N-2] sein
   - usw. (umgekehrte Reihenfolge)

**BLOCKER wenn:**
- Operation in Up() hat keine Gegenaktion in Down()
- Parameter stimmen nicht ueberein (z.B. Tabellenname)
- Reihenfolge ist nicht umgekehrt

**Output Task 1.3:**
```
[BLOCKER] Down() unvollstaendig:

Migration: 20240115120000_AddBenutzerEmail.cs

Up() Operation 1: AddColumn(Benutzer.Email)
  Erwartet in Down(): DropColumn(Benutzer.Email) ← GEFUNDEN ✓

Up() Operation 2: Sql("UPDATE Benutzer SET Email...")
  Erwartet in Down(): Sql (Rollback) oder Warnung ← WARNUNG (kein Rollback-SQL)

Up() Operation 3: CreateIndex(IX_Benutzer_Email)
  Erwartet in Down(): DropIndex(IX_Benutzer_Email) ← GEFUNDEN ✓

Reihenfolge-Pruefung:
  Down()[0] = DropIndex ← Sollte Gegenteil von Up()[2] sein ✓
  Down()[1] = DropColumn ← Sollte Gegenteil von Up()[0] sein ✗ FEHLER

FEHLER: Reihenfolge ist falsch!
  Down()[1] sollte Gegenteil von Up()[1] sein (Sql-Rollback fehlt)

Action: Down() Reihenfolge korrigieren und Sql-Rollback hinzufuegen
```

---

### Task 1.4: Nicht-deterministische Test-Daten finden (WARNUNG)

**Aktion:** Scanne Up() Methode nach nicht-deterministischen Patterns.

**Pattern-Suche (Regex):**
```regex
# Pattern 1: Random
new Random\(\)
Random\.Next\(

# Pattern 2: Aktuelle Zeit
DateTime\.Now
DateTime\.UtcNow

# Pattern 3: SQL-Funktionen
GETDATE\(\)
NEWID\(\)
RAND\(\)
```

**WARNUNG wenn gefunden in:**
- `migrationBuilder.Sql(...)`
- `migrationBuilder.InsertData(...)`
- Seed-Data Code

**Output Task 1.4:**
```
[WARNUNG] Nicht-deterministische Test-Daten:

Migration: 20240115120000_SeedBenutzer.cs, Zeile 23

Code:
```csharp
var random = new Random();
migrationBuilder.Sql($"INSERT INTO Benutzer (Id) VALUES ({random.Next(1, 1000)})");
```

Problem: Random() macht Daten nicht-deterministisch
Empfehlung: Feste IDs verwenden (z.B. 1, 2, 3)

---

Migration: 20240115120000_SeedBenutzer.cs, Zeile 28

Code:
```csharp
migrationBuilder.Sql("INSERT INTO Benutzer (ErstelltAm) VALUES (GETDATE())");
```

Problem: GETDATE() ist nicht-deterministisch
Empfehlung: Feste DateTime verwenden (z.B. '2024-01-01 12:00:00')
```

---

## Welle 2: Synthese + Bericht

**Berichts-Format:**

```markdown
# Pre-PR Migration Quality Gate Report

**Branch:** [Branch-Name]
**Datum:** [ISO-8601]
**Analysierte Migrationen:** [Anzahl]

---

## Zusammenfassung

| Level | Anzahl | Status |
|-------|--------|--------|
| BLOCKER (Geaenderte Migrationen) | [N] | [PASS/FAIL] |
| BLOCKER (Unvollstaendige Down()) | [N] | [PASS/FAIL] |
| WARNUNG (Nicht-deterministisch) | [N] | [PASS/WARN] |

**Gesamtstatus:** [PASS/FAIL]

---

## Details

### R1: Down() Vollstaendigkeit (BLOCKER)

**Status:** [PASS/FAIL]

[Wenn FAIL:]

**Migration:** 20240115120000_AddBenutzerEmail.cs

**Probleme:**

1. **Fehlende Gegenaktion**
   ```csharp
   // Up()
   migrationBuilder.CreateIndex(
       name: "IX_Benutzer_Email",
       table: "Benutzer",
       column: "Email");

   // Down() - FEHLT!
   // Erwartet: migrationBuilder.DropIndex("IX_Benutzer_Email", "Benutzer");
   ```

2. **Falsche Reihenfolge**
   ```csharp
   // Up() Reihenfolge:
   // 1. AddColumn
   // 2. CreateIndex

   // Down() Reihenfolge (FALSCH):
   // 1. DropColumn  ← Sollte zuletzt sein
   // 2. DropIndex   ← Sollte zuerst sein

   // Down() Reihenfolge (RICHTIG):
   // 1. DropIndex   ← Zuerst
   // 2. DropColumn  ← Danach
   ```

**Naechste Schritte:**
- Down() Methode vervollstaendigen
- Reihenfolge umkehren
- /_Pre_PR_Migration erneut ausfuehren

---

### R2: Bestehende Migrationen (BLOCKER)

**Status:** [PASS/FAIL]

[Wenn FAIL:]

**Geaenderte Migrationen gefunden:**

1. **Migrations/20240101120000_InitialCreate.cs**
   ```diff
   protected override void Up(MigrationBuilder migrationBuilder)
   {
       migrationBuilder.AddColumn<string>(
           name: "Email",
   -       nullable: true,
   +       nullable: false);
   }
   ```

   **Problem:** Bestehende Migration wurde nachtraeglich geaendert
   **Risiko:** Inkonsistenz auf anderen Umgebungen (Test, Prod)

   **Loesung:**
   1. Aenderung in dieser Datei rueckgaengig machen (git checkout)
   2. Neue Migration erstellen:
      ```bash
      dotnet ef migrations add MakeBenutzerEmailRequired
      ```
   3. In neuer Migration:
      - Erst Daten korrigieren (UPDATE SET Email = '...' WHERE Email IS NULL)
      - Dann AlterColumn(nullable: false)

**KRITISCH:** Migration MUSS reverted werden vor Merge!

---

### R3: Test-Daten Determinismus (WARNUNG)

**Status:** [PASS/WARN]

**Nicht-deterministische Patterns gefunden:**

1. **Migration:** 20240115120000_SeedBenutzer.cs, Zeile 23
   ```csharp
   var random = new Random();
   migrationBuilder.Sql($"INSERT INTO Benutzer (Id) VALUES ({random.Next(1, 1000)})");
   ```
   **Problem:** Random() produziert jedes Mal andere IDs
   **Empfehlung:** Feste IDs verwenden (1, 2, 3, ...)

2. **Migration:** 20240115120000_SeedBenutzer.cs, Zeile 28
   ```csharp
   migrationBuilder.Sql("INSERT INTO Benutzer (ErstelltAm) VALUES (GETDATE())");
   ```
   **Problem:** GETDATE() ist aktuelle Zeit
   **Empfehlung:** Feste DateTime ('2024-01-01 12:00:00')

**Hinweis:** WARNUNG-Level, kein Blocker, aber sollte behoben werden.

---

## Statistik

- **Neue Migrationen:** [N]
- **Geaenderte Migrationen:** [N] (BLOCKER wenn > 0)
- **Unvollstaendige Down():** [N] (BLOCKER wenn > 0)
- **Nicht-deterministische Patterns:** [N] (WARNUNG)

---

## Checkliste fuer Entwickler

Vor Merge sicherstellen:

- [ ] Keine bestehenden Migrationen geaendert (R2)
- [ ] Jede Up() Operation hat Gegenaktion in Down() (R1)
- [ ] Down() Operationen in umgekehrter Reihenfolge (R1)
- [ ] Keine Random() oder GETDATE() in Seed-Data (R3)
- [ ] Migration lokal getestet (dotnet ef database update)
- [ ] Migration-Rollback getestet (dotnet ef database update <previous>)

---

**Hinweis:** Alle Migration-Probleme muessen manuell behoben werden.
Keine automatischen Fixes aufgrund des hohen Risikos bei Datenbank-Operationen.
```

---

## Qualitaetskriterien

### PASS-Bedingungen
- KEINE geaenderten Migrationen (R2 = PASS)
- Alle Up() Operationen haben Gegenaktion in Down() (R1 = PASS)
- Down() Reihenfolge ist umgekehrt zu Up() (R1 = PASS)

### FAIL-Bedingungen
- Mindestens eine bestehende Migration geaendert (R2 = BLOCKER)
- Mindestens eine Up() Operation ohne Gegenaktion (R1 = BLOCKER)
- Down() Reihenfolge falsch (R1 = BLOCKER)

### WARNUNG (kein FAIL)
- Nicht-deterministische Test-Daten (R3 = WARNUNG)

### Auto-Fix
- **KEINE Auto-Fixes** bei Migrationen (zu hohes Risiko)

---

## Verwendung

```bash
# Standard-Ausfuehrung
/_Pre_PR_Migration

# Output:
# - Bericht mit Blocker/Warnungen
# - Exit-Code 0 bei PASS, 1 bei FAIL (Blocker)
```

**Erwartete Laufzeit:** 1-3 Minuten (haengt von Anzahl Migrationen ab)

---

## Debugging

**Haeufige Probleme:**

1. **"False Positive: Designer.cs als geaendert erkannt"**
   - Designer.cs Dateien werden explizit ausgeschlossen
   - Pruefe Filter-Logik

2. **"Down() Reihenfolge PASS aber trotzdem falsch"**
   - Manuell verifizieren mit dotnet ef database update
   - Rollback testen

3. **"Sql() Gegenaktion nicht erkannt"**
   - Fuer custom SQL muss Entwickler manuell Rollback-SQL schreiben
   - Quality Gate kann nur warnen, nicht auto-fixen

---

## Erweiterte Pruefungen (Optional)

### Migration-Tests ausfuehren

```bash
# Migration anwenden
dotnet ef database update --project Backend.csproj

# Migration rollbacken
dotnet ef database update <previous-migration> --project Backend.csproj
```

**In CI/CD Pipeline:**
- Temporaere Test-DB erstellen
- Alle Migrationen anwenden
- Alle Migrationen rollbacken
- Bei Fehler: Build failt

---

**Ende des Commands**
