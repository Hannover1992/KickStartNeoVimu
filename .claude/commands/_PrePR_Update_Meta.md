---
type: satellite
---

# /_PrePR_Update_Meta - Meta-Datei mit manuellem Fund ergaenzen

**Zweck:** Dinge die Pre-PR NICHT gefunden hat aber manuell gefixt wurden, als neue Regel in die zustaendige Meta-Datei schreiben. Damit lernt das naechste Pre-PR daraus.

**Kein Git. Keine Code-Aenderungen. Nur Meta-Datei.**

---

## Vertrag

```
╔══════════════════════════════════════════════════════════════╗
║  COMMAND: /_PrePR_Update_Meta                                ║
╠══════════════════════════════════════════════════════════════╣
║  LIEST:                                                      ║
║    1. Raw Input (Text oder Pfad vom User)                    ║
║    2. .claude/meta/codeKonvention/{gate}.md (Ziel-Datei)    ║
║  SCHREIBT:                                                   ║
║    1. .claude/meta/codeKonvention/{gate}.md (+neue Regel)    ║
║  KEIN Git. KEIN Commit. NUR Meta-Datei.                      ║
╚══════════════════════════════════════════════════════════════╝
```

**Gate → Datei Mapping:**

| Gate | Datei |
|------|-------|
| Tests / Teststruktur / xUnit | `.claude/meta/codeKonvention/testbase.md` |
| Naming / Bezeichnung / Benennung | `.claude/meta/codeKonvention/naming.md` |
| Cleanup / toter Code / auskommentiert | `.claude/meta/codeKonvention/cleanup.md` |
| Dokumentation / XML-Kommentar / Summary | `.claude/meta/codeKonvention/dokumentation.md` |
| Konstanten / Magic String / Magic Number | `.claude/meta/codeKonvention/konstanten.md` |
| Logging / ILogger / Serilog | `.claude/meta/codeKonvention/logging.md` |
| Architektur / Controller / Provider / DI | `.claude/meta/codeKonvention/architektur.md` |
| Analyzer / csproj / Roslyn / Warning | `.claude/meta/codeKonvention/analyzer.md` |
| Migration / EF Core / Down() | `.claude/meta/codeKonvention/migration.md` |

---

## Ablauf

### Schritt 1: Raw Input lesen

Der User gibt entweder:
- **Freitext:** Beschreibung was er manuell gefixt hat
- **Pfad:** Pfad zu einer Datei mit der Beschreibung (`.md`, `.txt`)

Falls Pfad: Datei lesen. Falls Freitext: direkt verwenden.

### Schritt 2: Klassifizieren

Analysiere den Raw Input und bestimme:

1. **Welches Gate?** (siehe Mapping oben) — falls unklar: AskUserQuestion mit den 9 Optionen
2. **Severity?**
   - `BLOCKER` — verhindert korrektes Verhalten, muss immer gefixt werden
   - `WARNUNG` — sollte gefixt werden, Ausnahmen moeglich
   - `INFO` — empfohlen aber nicht kritisch
3. **Auto-Fix moeglich?** JA / NEIN / TEILWEISE
4. **Titel** — kurze Bezeichnung der Regel (max 6 Woerter)

Falls Gate unklar:

```
AskUserQuestion:
  header: "Gate"
  question: "Welchem Gate gehoert dieser Fund?"
  options:
    - label: "Tests"         description: "testbase.md"
    - label: "Naming"        description: "naming.md"
    - label: "Cleanup"       description: "cleanup.md"
    - label: "Dokumentation" description: "dokumentation.md"
    - label: "Konstanten"    description: "konstanten.md"
    - label: "Logging"       description: "logging.md"
    - label: "Architektur"   description: "architektur.md"
    - label: "Analyzer"      description: "analyzer.md"
    - label: "Migration"     description: "migration.md"
```

### Schritt 3: Ziel-Datei lesen

Lese `.claude/meta/codeKonvention/{gate}.md`.

Bestimme:
- Hoechste vorhandene Regel-Nummer (z.B. R12 → naechste ist R13)
- Vorhandene Regeln durchlesen: Ist diese Regel bereits abgedeckt?
  - JA → Melde dem User: "Aehnliche Regel existiert bereits: R{N} '{titel}'" → EXIT 0
  - NEIN → weiter

### Schritt 4: Neue Regel formulieren

Formuliere die neue Regel im Standardformat:

```markdown
### R{N}: {Titel}
- **Severity:** {BLOCKER|WARNUNG|INFO}
- **Auto-Fix:** {JA|NEIN|TEILWEISE}
- **Beschreibung:** {Vollstaendige Beschreibung des Problems und warum es ein Problem ist.}
- **Beispiel VORHER:**
  ```csharp
  // {Konkretes Beispiel fuer das Problem}
  ```
- **Beispiel NACHHER:**
  ```csharp
  // {Konkretes Beispiel fuer die Loesung}
  ```
- **Ausnahmen:** {Ausnahmen falls vorhanden, sonst: Keine}
- **Herkunft:** Manueller Fund nach Pre-PR ({datum})
```

**Qualitaets-Check vor dem Schreiben:**
- Beschreibung erklaert WARUM (nicht nur WAS)
- Beispiel VORHER zeigt den echten Fehler
- Beispiel NACHHER zeigt die korrekte Loesung
- Keine doppelte Regelabdeckung

### Schritt 5: In Meta-Datei schreiben

Finde den richtigen Einfuege-Punkt:
- Neue Regel gehoert ans **Ende der `## Regeln` Section** (vor einem optionalen `## Projekt-spezifische Ergaenzungen` Block)

Aktualisiere den Header der Datei:
- `**Version:**` → um 0.1 erhoehen (z.B. 1.1 → 1.2)
- `**Letzte Aenderung:**` → heutiges Datum (YYYY-MM-DD)

### Schritt 6: Bestaetigung ausgeben

```
✓ Neue Regel R{N} in .claude/meta/codeKonvention/{gate}.md geschrieben

Gate:      {gate}
Regel:     R{N} — {Titel}
Severity:  {severity}
Auto-Fix:  {ja/nein}
Datei:     .claude/meta/codeKonvention/{gate}.md

Das naechste /_Pre_PR_{Gate} wird diese Regel automatisch pruefen.
```

---

## Regeln

- **KEIN Git** — weder `git add` noch `git commit` noch `git diff`
- **NUR Meta-Datei** schreiben — kein Code, keine Tests, keine anderen Dateien
- Doppelte Regeln vermeiden — vorher pruefen
- Format strikt einhalten — Gate-Commands lesen es maschinell

---

## Aufruf-Beispiele

```
/_PrePR_Update_Meta
"AutoMapper .ToList() in ProjectTo-Expression wirft Runtime-Exception"

/_PrePR_Update_Meta
"Ich habe drei Include() entfernt die bei ProjectTo Dead Code sind"

/_PrePR_Update_Meta
/pfad/zur/beschreibung.txt
```
