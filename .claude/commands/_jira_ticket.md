---
status: v1.2
version: "1.2"
created: 2026-03-10
updated: 2026-06-12
op: JiraTicket
type: satellite
---

# /_jira_ticket — Jira Ticket Generator (Wiki Markup)

**Status:** v1.2
**Typ:** Satelliten-Command (Output-Generator)
**Actor:** DU (direkt, kein Team)
**Modus:** WRITE (3 Dateien)

---

## Vertrag

```
+==============================================================+
|  COMMAND: /_jira_ticket <TYP> [Kontext]                      |
+==============================================================+
|                                                              |
|  SYNTAX:                                                     |
|    /_jira_ticket story Dateiabholung implementieren          |
|    /_jira_ticket bug Flaky Test UserProvider                 |
|    /_jira_ticket task DB-Migration ausfuehren                |
|    /_jira_ticket refactoring Sortierung ueberpruefen         |
|    /_jira_ticket impediment Testumgebung nicht erreichbar    |
|                                                              |
|  TYPEN:                                                      |
|    story | bug | task | refactoring | impediment             |
|                                                              |
|  INPUT:                                                      |
|    - Kontext aus Argument ODER aus laufender Konversation    |
|    - Optional: Code-Snippets, Dateipfade, Fehlermeldungen    |
|                                                              |
|  OUTPUT (1 Datei):                                           |
|    .claude/tickets/{NAME}_{TYP}.md                           |
|    Inhalt: # Titel + # Metadaten + # Description             |
|                                                              |
|  NAMING:                                                     |
|    {NAME} = Kurztitel, PascalCase, keine Sonderzeichen       |
|    {TYP}  = Story|Bug|Task|Refactoring|Impediment            |
|    Beispiel: FK_Konfiguration_Refactoring.md                 |
|              FlakyTest_UserProvider_Bug.md                    |
|              Dateiabholung_Story.md                           |
|                                                              |
|  CLIPBOARD: Voller Pfad der Datei wird in Clipboard kopiert  |
|                                                              |
|  LIEST: Konversations-Kontext, ggf. referenzierte Dateien   |
|  SCHREIBT: .claude/tickets/{NAME}_{TYP}.md                  |
|                                                              |
+==============================================================+
```

---

## Schritt 1: Typ bestimmen

Aus dem Argument den Ticket-Typ extrahieren. Falls kein Typ angegeben → User fragen.

| Typ | Jira-Typ | Epic-Default |
|-----|----------|-------------|
| `story` | Story | — (User muss angeben) |
| `bug` | Fehler | — |
| `task` | Aufgabe | — |
| `refactoring` | Story | Refactoring |
| `impediment` | Impediment | — |

---

## Schritt 2: Kontext sammeln

Aus dem Argument und/oder der laufenden Konversation extrahieren:

1. **Titel** — kurz, praegnant (wird Jira-Summary)
2. **Beschreibung** — Was, Warum, Wie
3. **Akzeptanzkriterien** — messbare Bedingungen (nur bei story/refactoring)
4. **Technische Details** — Code, Dateien, Fehlermeldungen (nur bei bug)

Falls der Kontext nicht ausreicht: FRAGE den User gezielt nach fehlenden Informationen.
NICHT raten. NICHT auffuellen mit Platzhaltern.

---

## Schritt 3: Wiki Markup generieren

### WICHTIG: Jira Wiki Markup Syntax-Referenz

```
Ueberschriften:     h1. Text    h2. Text    h3. Text
Fett:               *fetter Text*
Kursiv:             _kursiver Text_
Aufzaehlung:        * Punkt 1\n* Punkt 2\n** Unterpunkt
Nummeriert:         # Punkt 1\n# Punkt 2\n## Unterpunkt
Code inline:        {{codeHier}}
Codeblock:          {code:java}...{code}   (Sprache NUR aus Whitelist, s.u.!)
Noformat:           {noformat}...{noformat}
Link:               [Anzeige|https://url]
Tabelle:            ||Kopf1||Kopf2||\n|Zelle1|Zelle2|
Zitat:              {quote}...{quote}
Farbe:              {color:red}Text{color}
Panel:              {panel:title=Titel}Inhalt{panel}
Trennlinie:         ----
Zeilenumbruch:      \\
```

### Code-Sprachen-WHITELIST (v1.2, Live-Fehler 2026-06-12)

Das Jira rendert `{code:SPRACHE}` NUR fuer diese Sprachen — alles andere erzeugt
im Ticket den Fehler "Unable to find source-code formatter for language: ...":

```
actionscript, ada, applescript, bash, c, c#, c++, cpp, css, erlang, go,
groovy, haskell, html, java, javascript, js, json, lua, none, nyan, objc,
perl, php, python, r, rainbow, ruby, scala, sh, sql, swift, visualbasic,
xml, yaml
```

**PFLICHT-MAPPING vor dem Schreiben jedes `{code:...}`-Blocks:**

| Quell-Sprache (Kontext) | → Jira-Tag |
|---|---|
| typescript, ts, tsx (Angular/FE!) | `js` |
| csharp, cs | `c#` |
| razor, cshtml | `html` |
| scss, less | `css` |
| powershell, ps1, dockerfile, markdown, gherkin, sonstiges Unbekanntes | `none` |

Regel: Sprache nicht in der Whitelist → IMMER auf das Mapping ausweichen;
im Zweifel `{code:none}` (rendert immer) oder `{noformat}`. NIEMALS den
Original-Sprachnamen durchreichen, nur weil der Code so heisst.

### REGELN:
- KEIN Markdown verwenden! NUR Jira Wiki Markup
- Keine `**fett**` → stattdessen `*fett*`
- Keine `# Heading` → stattdessen `h2. Heading`
- Keine `- Liste` → stattdessen `* Liste`
- Keine ``` Codeblocks → stattdessen `{code}...{code}`
- Ueberschriften IMMER mit Punkt und Leerzeichen: `h2. Text` (NICHT `h2.Text`)
- `{code:SPRACHE}` NUR mit Whitelist-Sprache (s.o.) — `typescript` existiert in Jira NICHT → `js`

---

## Schritt 4: Template pro Typ anwenden

### 4a: Story

```
h2. UserStory

<User-Story im Format: "Als [Rolle] moechte ich [Aktion], damit [Nutzen]." ODER freier Text>

h2. Anmerkung

<Technische Hinweise, Verweise, Kontext>

h2. Akzeptanzkriterien

* <Kriterium 1>
* <Kriterium 2>
* <Kriterium 3>
```

**Akzeptanzkriterien** (als Jira-Feld, ZUSAETZLICH zur Beschreibung):
```
<Kriterium 1>
<Kriterium 2>
<Kriterium 3>
```

**Standard-Subtasks** (als Vorschlag auflisten):
```
1. Story Kickoff
2. BE implementieren
3. PR Review (BE)
4. DoD
5. Abnahme durch PO
```

Falls Frontend beteiligt:
```
1. Story Kickoff
2. BE implementieren
3. FE implementieren
4. PR Review (BE)
5. PR Review (FE)
6. DoD
7. Abnahme durch PO
```

---

### 4b: Bug (Fehler)

```
h2. Fehlerbeschreibung

<Was passiert? Wann? Unter welchen Bedingungen?>

h2. Erwartetes Verhalten

<Was sollte stattdessen passieren?>

h2. Ursache

<Root Cause, falls bekannt>

h2. Betroffene Komponente

* Datei: {{<Dateipfad>}}
* Methode: {{<Methodenname>}}

h2. Reproduktion

# <Schritt 1>
# <Schritt 2>
# <Schritt 3>

h2. Workaround

<Temporaere Loesung, falls vorhanden. Sonst: "Kein Workaround bekannt.">

h2. Loesungsvorschlag

<Technischer Fix-Vorschlag>
```

---

### 4c: Task (Aufgabe)

```
h2. Aufgabe

<Was muss getan werden?>

h2. Kontext

<Warum ist das noetig? Hintergrund.>

h2. Abnahmekriterien

* <Kriterium 1>
* <Kriterium 2>
```

---

### 4d: Refactoring

```
h2. Refactoring

<Was soll refactored werden?>

h2. Aktueller Zustand

<Problem/Code-Smell beschreiben>

{code:<sprache-aus-WHITELIST — TypeScript → js, C# → c#, unbekannt → none>}
<Betroffener Code-Ausschnitt, falls relevant>
{code}

h2. Zielzustand

<Wie soll es danach aussehen?>

h2. Akzeptanzkriterien

* <Kriterium 1 - z.B. "Tests sind aktualisiert">
* <Kriterium 2 - z.B. "Keine Flakyness mehr">
```

**Akzeptanzkriterien** (Jira-Feld):
```
<Kriterium 1>
<Kriterium 2>
```

---

### 4e: Impediment (Hindernis)

```
h2. Hindernis

<Was blockiert?>

h2. Auswirkung

<Welche Stories/Tasks sind blockiert? Welches Risiko?>

h2. Betroffene Vorgaenge

* [DCSRE-XXX|https://projekte.itsg.de/browse/DCSRE-XXX]

h2. Loesungsvorschlag

<Wie kann das Hindernis beseitigt werden?>

h2. Verantwortlich

<Wer muss handeln?>
```

---

## Schritt 5: Datei schreiben

### 5.0 Dateiname bestimmen

```
DATEI_NAME = {Kurztitel_PascalCase}_{Typ}.md
PFAD       = .claude/tickets/{DATEI_NAME}
```

Regeln fuer {Kurztitel}:
- PascalCase, Woerter mit Unterstrich getrennt
- Keine Umlaute (ue, ae, oe statt ü, ä, ö)
- Keine Sonderzeichen ausser Unterstrich
- Max 40 Zeichen
- Beispiele: `FK_Konfiguration_Refactoring.md`, `FlakyTest_UserProvider_Bug.md`

### 5.1 Datei-Struktur

EINE Datei mit 3 Sektionen als Markdown-Headern:

```markdown
# Titel

FK-Konfiguration von DbContext (Fluent API) auf Entity-Attribute verschieben

---

# Metadaten

| Feld | Wert |
|------|------|
| Typ | Story |
| Prioritaet | Medium |
| Epic Link | Refactoring |
| Story Points | 8 |
| Sprint | — |

**Akzeptanzkriterien:**
- Kriterium 1
- Kriterium 2

**Subtasks:**
1. Story Kickoff
2. BE implementieren
3. PR Review (BE)
4. DoD
5. Abnahme durch PO

---

# Description

<!-- JIRA WIKI MARKUP — Copy-Paste in Jira Beschreibungsfeld -->

h2. UserStory

Die DCS-Pflege kann eine PB-Datei im DIC-Verfahren abholen.

h2. Anmerkung
...
```

**REGELN:**
- `# Titel` = reiner Text, Einzeiler
- `# Metadaten` = Markdown-Tabelle + Listen (fuer Lesbarkeit)
- `# Description` = reiner Jira Wiki Markup (1:1 in Jira pastebar)
- Felder die nicht zutreffen: mit `—` markieren (NICHT weglassen)
- Trennlinie `---` zwischen jeder Sektion

### 5.2 Clipboard + Terminal-Ausgabe

Nach dem Schreiben der Datei:

1. **Voller Pfad in Clipboard kopieren** (via `echo -n "<VOLLER_PFAD>" | clip.exe`)
2. **Terminal-Ausgabe:**

```
TICKET GESPEICHERT:
  .claude/tickets/{DATEI_NAME}
  (Pfad in Clipboard kopiert)
```

3. **Description-Inhalt als Codeblock ausgeben** (zum schnellen Kopieren in Jira)

---

## ANTI-PATTERNS

- KEIN Markdown in der Wiki-Markup-Ausgabe mischen
- KEINE Platzhalter wie `<TODO>` oder `<TBD>` im Output — lieber FRAGEN
- KEINE erfundenen Akzeptanzkriterien — nur was aus dem Kontext ableitbar ist
- NICHT den Titel in die Beschreibung wiederholen
- KEIN `h1.` in der Beschreibung verwenden — Jira nutzt `h2.` als hoechste Ebene in Beschreibungen

---

## Beispiel: Bug (aus DCSRE-1317)

**Input:** `/_jira_ticket bug Flaky Test UserProviderUpdateTests`

**Datei:** `.claude/tickets/FlakyTest_UserProvider_Bug.md`

```markdown
# Titel

Der Test User_UpdateWithPflegeeinrichtung_Success in UserProviderUpdateTests ist flaky.

---

# Metadaten

| Feld | Wert |
|------|------|
| Typ | Fehler |
| Prioritaet | Undefined |
| Epic Link | — |
| Story Points | — |
| Sprint | — |

**Akzeptanzkriterien:**
—

**Subtasks:**
—

---

# Description

<!-- JIRA WIKI MARKUP — Copy-Paste in Jira Beschreibungsfeld -->

h2. Fehlerbeschreibung

Der Test {{User_UpdateWithPflegeeinrichtung_Success}} in {{UserProviderUpdateTests}} ist flaky.

h2. Ursache

SQL Server Container meldet "ready for client connections" bevor das Passwort-Hashing abgeschlossen ist. Login-Versuche scheitern mit:

{noformat}
Login failed for user 'sa'. Reason: An error occurred while evaluating the password.
{noformat}

h2. Betroffene Komponente

* Datei: {{VDEK.DCSP.IntegrationTests/Providers/UserProviderUpdateTests.cs}}

h2. Workaround

Test ist aktuell mit {{[Fact(Skip = "...")]}} deaktiviert.

h2. Loesungsvorschlag

{{WaitForDatabaseReadyAsync()}} in {{ContainerIntegrationTestBase}} verbessern — zusaetzliche Wartezeit nach "ready" Signal oder robustere Retry-Logik fuer Login-Fehler.
```

---

## Beispiel: Story (aus DCSRE-881)

**Input:** `/_jira_ticket story Dateiabholung implementieren`

**Datei:** `.claude/tickets/Dateiabholung_Story.md`

```markdown
# Titel

Dateiabholung implementieren

---

# Metadaten

| Feld | Wert |
|------|------|
| Typ | Story |
| Prioritaet | Highest |
| Epic Link | PB-Datei abholen |
| Story Points | 8 |
| Sprint | — |

**Akzeptanzkriterien:**
- DIC-Verfahren ist fuer eine Bsp. Umgebung funktional einrichtet
- Eine PB-Datei kann in der Bsp. Umgebung abgerufen werden
- Die PB-Datei wird im S3 Storage abgelegt
- Die Konfigurbarkeit der Verfahren ist moeglich
- Die Persistierung der Lieferung in die Datenbank ist erfolgt

**Subtasks:**
1. Story Kickoff
2. BE implementieren
3. PR Review (BE)
4. DoD
5. Abnahme durch PO

---

# Description

<!-- JIRA WIKI MARKUP — Copy-Paste in Jira Beschreibungsfeld -->

h2. UserStory

Die DCS-Pflege kann eine PB-Datei im DIC-Verfahren abholen.

h2. Anmerkung

In dieser Story ist das DIC-Verfahren einzurichten (Simulator) und auf der DEV Umgebung funktionieren. Verfahrensbeschreibung siehe EPIC.

Es wird hier KEINE Fehlerbehandlung erwartet.

Weitere Infos zum Status unter:
[SM006 Lieferungsstatus|https://wiki.itsg.de/display/DCSP/SM006+Lieferungsstatus]

DIC-Anbindung:
[Anbindung DIC|https://wiki.itsg.de/display/DCSP/Anbindung+DIC]

Es kann bzgl. S3-Storage Code vom frueheren Projekt "TEP" oder "FGW" zugegriffen werden.
```

---

## Changelog

### v1.2 (2026-06-12) — Pflaster: Code-Sprachen-Whitelist (Live-Fehler)

- **Anlass:** Generiertes Ticket enthielt `{code:typescript}` → Jira renderte
  "Unable to find source-code formatter for language: typescript" statt des
  Code-Blocks (TS-Snippet aus FE-Kontext, DCSRE-1944).
- Whitelist der 35 vom Jira unterstuetzten Sprachen eingebettet (aus der
  Original-Fehlermeldung) + PFLICHT-MAPPING: typescript/ts/tsx→js, csharp→c#,
  razor→html, scss→css, powershell/unbekannt→none.
- 4d-Refactoring-Template-Platzhalter auf Whitelist-Hinweis umgestellt;
  REGELN-Block um Sprach-Regel ergaenzt.
- Analog-Pflaster zu /_assay v2.1.0 (selber Tag, selbe Session).
