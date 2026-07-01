---
type: satellite
description: Interaktiver Stundeneintrag-Assistent — Termine aus Kalender + Jira-Activity + Git-Commits zu stundenscharfer ZEP-Tabelle (Ziel: 42 h/Woche)
argument-hint: [von-datum] [bis-datum]
allowed-tools: Bash(git:*), Bash(awk:*), Bash(grep:*), Bash(date:*), Bash(ls:*), WebFetch, Read, Write, Edit
---

# /ZEP — Stundenerfassung Assistent

Erstellt eine **stundenscharfe Zeiterfassung** für die ZEP-Eintragstabelle. Nutzt drei Quellen:

1. **Kalender-Termine** (vom User abgefragt — haben **Vorrang**)
2. **Jira Activity Stream** (Status-Wechsel, neue Tickets, Reviews)
3. **Git-Commits** (alle Branches, alle Worktrees)

**Zielwert:** **42 h/Woche** (Minimum, das erreicht werden muss).

---

## Konstanten

```
USER          = Patryk Krzyzanski
JIRA_USER     = patryk.krzyzanski
REPO          = C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/DCSRE
JIRA_ACTIVITY = https://projekte.itsg.de/activity?maxResults=500&streams=user+IS+patryk.krzyzanski&providers=issues
ARBEITSTAG    = 08:00–18:00 (9 h netto)
MITTAGSPAUSE  = 13:15–14:15 (1 h)
WOCHENSOLL    = 42 h
TAG_CAP       = 16 h (für Ausnahme-Tage wie Workshop+Reise)
```

---

## Schritt 1 — Zeitraum + Kontext erfragen (interaktiv)

Wenn `$ARGUMENTS` leer ist oder kein vollständiges Datumspaar enthält, **frage den User**:

```
Zeitraum für die Stundenerfassung?

  1) Von wann bis wann? (z. B. "27.04 bis heute" oder "diese Woche" oder "letzte 14 Tage")
  2) Gibt es Sondertage in dem Zeitraum?
       - Urlaub / Krankheit (mit Datum)
       - Workshop / Off-Site (mit Datum + ggf. Zugfahrt)
       - Feiertag / Brückentag
       - Wochenend-/Abend-Arbeit (Überstunden, ja/nein buchbar?)
  3) Welche Kalender-Termine waren in dem Zeitraum?
       - Bitte als Bullet-Liste pro Tag mit Uhrzeit + Ticket falls bekannt
       - (Daily, Refinement, Retro, Review, Planning, Story-Kickoffs, externe Termine)
  4) Welches ist das aktuelle Haupt-Ticket?
       - Fallback: Wenn keine Zuordnung möglich → diese Stunden auf das Haupt-Ticket buchen
```

**Wichtig:** Diese Information ist **Pflicht**, weil:
- Kalender ist programmatisch nicht erreichbar (Outlook/Teams)
- Workshop-Tage sehen in Git wie "Lücke" aus, sind aber 8 h Arbeit
- Wochenend-/Feiertags-Commits sind ggf. nicht buchbar

---

## Schritt 2 — Datenerhebung (parallel)

### 2a) Git-Commits aller Worktrees + Repos

```bash
# Worktrees enumerieren
cd "$REPO" && git worktree list

# Alle Commits im Zeitraum (ALLE Branches, ALLE Worktrees, OHNE Merges)
cd "$REPO" && git log --all --author="$USER" \
  --since="$SINCE 00:00" --until="$UNTIL 23:59" \
  --no-merges \
  --pretty=format:"%aI | %h | %s" --date=iso
```

Falls weiteres Repo unter `C:/Users/Administrator/Documents/Work/Code2/DCSRE` existiert, dort dasselbe ausführen.

**Pro Tag aggregieren:**
- Erste + letzte Commit-Uhrzeit
- Anzahl Commits
- LOC (insertions+deletions, via `--shortstat`)
- Alle Ticket-Keys aus Commit-Messages: `grep -oE 'DCSRE-[0-9]+'` (NICHT nur Branch-Präfix — Branches haben oft DCSRE-X als Präfix, aber Commits referenzieren mehrere Tickets)

### 2b) Jira Activity Stream

```
WebFetch: https://projekte.itsg.de/activity?maxResults=500&streams=user+IS+patryk.krzyzanski&providers=issues
```

Atom-XML parsen:
- `<published>` → Zeitstempel
- `<title>` → Event-Text (HTML-entity-decoded)
- `<category term="…">` → Verb (created, started, transitioned, …)
- Issue-Key per Regex `DCSRE-\d+`

Filter auf Zeitraum, sortiere chronologisch pro Tag.

**Falls WebFetch scheitert** (Auth/SSL), den User bitten, den Activity-Tab im Browser zu öffnen und den `<pre>`-Inhalt einzufügen.

---

## Schritt 3 — Tag-für-Tag-Plan bauen

Für **jeden Tag** im Zeitraum (Mo–Fr regulär, Sa/So/Feiertag separat):

### Regelwerk

1. **Kalender-Termine zuerst** in den Tagesplan eintragen (Daily, Refinement, etc.) mit ihrer realen Dauer.
2. **Sondertage** (Urlaub, Workshop, krank) **vollständig** auf entsprechende Buchungs-Kategorie:
   - Urlaub → "Urlaub" (kein Ticket)
   - Workshop → interner Workshop-Code oder Haupt-Ticket lt. User
   - Krank → "Krank"
3. **Mittagspause** 13:15–14:15 fix einplanen (außer User sagt anders).
4. **Restliche Stunden** auf gearbeitete Tickets verteilen, priorisiert nach:
   1. Jira-Events (Status-Wechsel, Sub-Task-Anlage, PR-Review) → exakte Uhrzeit
   2. Git-Commits → Cluster nach Uhrzeit + Ticket-Key in Message
   3. **Fallback:** unzuordenbare Zeit → aktuelles Haupt-Ticket (lt. User-Antwort)
5. **Cap:** max 16 h/Tag (für Workshop+Reise-Tage); regulär 9 h.
6. **Wochensoll:** 42 h. Wenn Summe < 42 h → User fragen, ob Restzeit auf Haupt-Ticket gepuffert werden soll.

### Pro Tag eine Tabelle erzeugen

```
### {Wochentag} {Datum} — {Σ h}
| Zeit         |  h   | Buchung              | Inhalt                              |
|--------------|------|----------------------|-------------------------------------|
| 08:00–09:00  | 1,0  | DCSRE-94             | Vorbereitung / Kontext-Switch       |
| 09:00–09:15  | 0,25 | DCSRE Daily          | Daily Standup                       |
| 09:15–13:15  | 4,0  | DCSRE-94             | Implementierung                     |
| 13:15–14:15  | 1,0  | Mittagspause         | —                                   |
| 14:15–18:00  | 3,75 | DCSRE-94             | Tests + Refactor                    |
```

---

## Schritt 4 — Wochen-Aggregation (ZEP-kompatibel)

Erzeuge die **ZEP-Eintragstabelle** (Ticket × Tag, gerundet auf 0,25 h):

```
ZEP-EINTRÄGE (Woche {KW})

| Datum  | Wochentag | DCSRE-94 | DCSRE-1932 | DCSRE-1990 | Daily | Workshop | Urlaub | TOTAL |
|--------|-----------|----------|------------|------------|-------|----------|--------|-------|
| 27.04. | Mo        | 4,75     | 4,0        | —          | 0,25  | —        | —      | 9,0   |
| 28.04. | Di        | —        | —          | —          | —     | 9,0      | —      | 9,0   |
| 29.04. | Mi        | 13,5     | —          | —          | 0,5   | 2,0      | —      | 16,0  |
| 30.04. | Do        | —        | —          | —          | —     | —        | 9,0    | 9,0   |
| 02.05. | Sa        | (1,75)   | —          | —          | —     | —        | —      | (1,75)|
| Σ      |           | 18,25    | 4,0        | —          | 0,75  | 11,0     | 9,0    | 42,0  |
```

**Regel:** Wochenende/Feiertag in Klammern → Überstunden-Pool (separat ausweisen).

---

## Schritt 5 — Soll-Ist-Abgleich

```
WOCHEN-PRÜFUNG:
  Soll:        42,0 h
  Ist:         {SUMME} h
  Differenz:   {DIFF} h
  
  ✓ Soll erreicht                → fertig
  ✗ Soll unterschritten ({DIFF}) → User fragen:
      - Stunden auf Haupt-Ticket auffüllen?
      - Vergessene Termine/Tickets nachtragen?
      - Aus Überstunden-Pool ergänzen?
```

---

## Schritt 6 — Ausgabe

Schreibe drei Blöcke:

1. **Tages-Tabellen** (Schritt 3) — chronologisch
2. **ZEP-Eintragstabelle** (Schritt 4) — ein Block pro Woche
3. **Ticket-Zusammenfassung** mit Beschreibung pro Ticket (aus Commit-Messages thematisch zusammengefasst)
4. **Soll-Ist-Abgleich** (Schritt 5) pro Woche

Frage am Ende:
```
Soll ich die ZEP-Tabelle als CSV/Markdown-Datei exportieren?
  Pfad-Vorschlag: ./zep-{KW}-{JAHR}.csv
```

---

## Wichtige Heuristiken

- **Branch-Präfix ≠ Ticket-Realität:** Wenn der ganze Branch `feature/DCSRE-94_…` heißt, heißt das nicht, dass alle Stunden auf DCSRE-94 gehen. Prüfe Jira-Events parallel — der User hat oft DoD-Checks, PR-Reviews oder Sub-Task-Anlagen für andere Tickets gemacht.
- **Lücken im Git ≠ Lücken im Tag:** Workshop, Meetings, Analyse, Code-Review hinterlassen keine Commits. Diese Zeit muss aus Kalender + Jira-Activity rekonstruiert werden.
- **Commits-Cluster ≠ einzelne Tickets:** 32 Commits in 10 Stunden zu DCSRE-94 mit 1 Story-Kickoff dazwischen → Story-Kickoff bekommt seine 30 min, der Rest auf DCSRE-94.
- **Reise-/Workshop-Tage** können legitim 12–16 h Buchung haben (Cap = 16 h).
- **Wochenend-/Feiertags-Commits** in Klammern ausweisen, separat fragen ob buchbar.
- **Daily/Refinement/Retro:** als eigene Zeile oder pauschal auf "DCSRE Sprint Overhead" buchen — je nach User-Vorgabe.
- **Fallback-Ticket** (vom User in Schritt 1 erfragt) ist der Buffer für nicht-zuordenbare Zeit.

---

## Argument-Parsing

```
$ARGUMENTS                       → frage interaktiv ab
$ARGUMENTS = "27.04"             → SINCE=2026-04-27, UNTIL=heute, frage Sondertage + Termine
$ARGUMENTS = "27.04 06.05"       → SINCE=2026-04-27, UNTIL=2026-05-06, frage Sondertage + Termine
$ARGUMENTS = "letzte-woche"      → SINCE=heute-7, UNTIL=heute
$ARGUMENTS = "diese-woche"       → SINCE=Montag-dieser-Woche, UNTIL=heute
$ARGUMENTS = "kw18"              → KW 18 des laufenden Jahres
```

Auch wenn ein Zeitraum gegeben ist: **Sondertage und Kalender-Termine IMMER erfragen** (außer User sagt explizit "keine besonderen Termine").

---

## Output-Stil

- Deutsche Markdown-Tabellen
- Stunden mit Komma als Dezimaltrenner (deutsche Notation): `4,75 h`
- Datum: `DD.MM.` (kurz) oder `DD.MM.YYYY` (lang)
- Ticket-Keys: `DCSRE-XXXX` immer mit Bindestrich
- Fett: Workshop-Tage, Sondertage, Wochen-Soll-Verfehlung
- Klammern: Wochenende/Feiertag/Überstunden (optional buchbar)
