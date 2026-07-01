---
status: active
version: 1.0.0
created: 2026-04-01
op: Zeiterfassung
type: satellite
coldstart: true
---

# /_zep — Stundenauswertung fuer Zeiterfassung

```
╔══════════════════════════════════════════════════════════════╗
║  VERTRAG: /_zep                                              ║
╠══════════════════════════════════════════════════════════════╣
║  LIEST:    Git Repository (ALLE Branches + Worktrees)       ║
║  SCHREIBT: nichts (reiner Terminal-Output)                   ║
║  TOOLS:    Bash (git commands)                               ║
║  AUTOR:    Patryk Krzyzanski (hardcoded)                     ║
║  REPO:     C:/Users/Administrator/Documents/Work/Code2/     ║
║            DCSRE_Azure/DCSRE                                 ║
╚══════════════════════════════════════════════════════════════╝
```

## Aufruf

```
/_zep {VON} {BIS}
/_zep {VON}                → bis heute
/_zep letzte-woche         → letzte 7 Tage
/_zep maerz                → 01.03. bis 31.03.
/_zep april                → 01.04. bis 30.04.
/_zep 14                   → letzte 14 Tage
```

**$ARGUMENTS:** Zeitraum-Angabe (siehe Schritt 1)

---

## Schritt 1: Zeitraum bestimmen

Interpretiere `$ARGUMENTS`:

| Eingabe | von | bis |
|---------|-----|-----|
| `2026-03-12 2026-03-27` | 2026-03-12 | 2026-03-27 |
| `2026-03-12` | 2026-03-12 | heute |
| `letzte-woche` / `last-week` | 7 Tage zurueck | heute |
| `letzter-monat` / `last-month` | 30 Tage zurueck | heute |
| `maerz` / `march` / `03` | 2026-03-01 | 2026-03-31 |
| `april` / `04` | 2026-04-01 | 2026-04-30 |
| `februar` / `02` | 2026-02-01 | 2026-02-28 |
| `14` (Zahl) | 14 Tage zurueck | heute |
| leer | 30 Tage zurueck | heute |

Bestimme `SINCE` und `UNTIL` als ISO-Daten.

---

## Schritt 2: Alle Commits sammeln (ALLE Branches + Worktrees)

```bash
REPO="C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/DCSRE"
AUTHOR="Patryk Krzyzanski"

cd "$REPO" && git log --all \
  --author="$AUTHOR" \
  --since="$SINCE" --until="$UNTIL" \
  --no-merges \
  --pretty=format:"%aI|%H|%D|%s" \
  --date=iso
```

**WICHTIG:**
- `--all` erfasst ALLE Branches (lokal + remote + worktrees)
- `--no-merges` filtert Merge-Commits raus (verfaelschen LOC)
- `%aI` = ISO-8601 Author-Date (mit Uhrzeit!)
- `%D` = Branch-Referenzen (fuer Ticket-Zuordnung)

---

## Schritt 3: Pro Tag auswerten

Fuer JEDEN Tag im Zeitraum der Commits hat:

### 3a: Commits + LOC pro Tag

```bash
cd "$REPO" && git log --all \
  --author="$AUTHOR" \
  --since="$TAG 00:00:00" --until="$TAG 23:59:59" \
  --no-merges \
  --pretty=format:"%aI|%s" --shortstat
```

### 3b: Stunden-Interpolation pro Tag

```
erster_commit  = frueheste Uhrzeit des Tages
letzter_commit = spaeteste Uhrzeit des Tages
spanne_minuten = (letzter - erster)
stunden        = (spanne_minuten / 60) + 1.0   ← +1h Puffer (Vorbereitung/Nacharbeit)

MINIMUM: 1.0h (auch bei nur 1 Commit)
MAXIMUM: 12.0h (Cap — niemand arbeitet laenger)
```

### 3c: Ticket-Erkennung pro Commit

Aus Commit-Message extrahieren:
```
DCSRE-\d+     → Ticket-ID
```

Falls kein Ticket in Message → Branch-Name pruefen (`%D`):
```
feature/DCSRE-881_...  → DCSRE-881
```

Falls weder Message noch Branch → "SONSTIGE"

---

## Schritt 4: Stunden auf Tickets verteilen

Pro Tag: Wenn mehrere Tickets an einem Tag bearbeitet wurden:

```
anteil_ticket = commits_ticket / commits_total_tag
stunden_ticket = stunden_tag * anteil_ticket
```

Runde auf 0.5h (ZEP-kompatibel: 0.5, 1.0, 1.5, 2.0, ...).

---

## Schritt 5: Output — Tages-Tabelle

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║  ZEP Stundenauswertung: Patryk Krzyzanski                                          ║
║  Zeitraum: {VON} bis {BIS}                                                         ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

┌────────────┬───────────┬──────────┬───────────┬──────────┬───────────────────────────┐
│   Datum    │ Wochentag │ ~Stunden │ Commits   │ LOC      │ Tickets                   │
├────────────┼───────────┼──────────┼───────────┼──────────┼───────────────────────────┤
│ 12.03.     │ Do        │ 7.5h     │ 20        │ 7.742    │ DCSRE-882, DCSRE-1051     │
│ 13.03.     │ Fr        │ 5.0h     │ 3         │ 315      │ DCSRE-882, DCSRE-1051     │
│ 14.03.     │ Sa        │ —        │ —         │ —        │ (Wochenende)              │
│ ...        │           │          │           │          │                           │
└────────────┴───────────┴──────────┴───────────┴──────────┴───────────────────────────┘
```

---

## Schritt 6: Output — ZEP-Eintragstabelle (Ticket x Tag)

**DAS ist die Kerntabelle fuer die Zeiterfassung:**

```
ZEP-EINTRAEGE (gerundet auf 0.5h):

┌────────────┬───────────┬────────────┬────────────┬────────────┬────────────┬───────┐
│   Datum    │ DCSRE-882 │ DCSRE-1051 │ DCSRE-98   │ DCSRE-1430 │ DCSRE-1513 │ TOTAL │
├────────────┼───────────┼────────────┼────────────┼────────────┼────────────┼───────┤
│ 12.03.     │ 7.0h      │ 0.5h       │ —          │ —          │ —          │ 7.5h  │
│ 13.03.     │ 4.5h      │ 0.5h       │ —          │ —          │ —          │ 5.0h  │
│ 17.03.     │ —         │ —          │ —          │ —          │ 3.5h       │ 3.5h  │
│ 18.03.     │ —         │ —          │ 12.0h      │ —          │ —          │ 12.0h │
│ ...        │           │            │            │            │            │       │
├────────────┼───────────┼────────────┼────────────┼────────────┼────────────┼───────┤
│ TOTAL      │ 11.5h     │ 1.0h       │ 55.0h      │ 10.0h      │ 3.5h       │ 81.0h │
└────────────┴───────────┴────────────┴────────────┴────────────┴────────────┴───────┘
```

---

## Schritt 7: Output — Ticket-Zusammenfassung

```
TICKET-ZUSAMMENFASSUNG:

┌────────────┬──────────┬─────────┬────────────────┬──────────────────────────────────┐
│   Ticket   │ Stunden  │ Commits │    Zeitraum    │ Beschreibung (aus Commit-Msgs)   │
├────────────┼──────────┼─────────┼────────────────┼──────────────────────────────────┤
│ DCSRE-98   │ 55.0h    │ 101     │ 18.03.–27.03.  │ QDVS Selbstauskunft Anzeigen     │
│ DCSRE-1430 │ 10.0h    │ 15      │ 25.03.–26.03.  │ QDVTP Selbstauskunft             │
│ DCSRE-882  │ 11.5h    │ 23      │ 12.03.–13.03.  │ MetaDaten                        │
│ ...        │          │         │                │                                  │
├────────────┼──────────┼─────────┼────────────────┼──────────────────────────────────┤
│ GESAMT     │ 81.0h    │ 150     │ 12.03.–27.03.  │                                  │
└────────────┴──────────┴─────────┴────────────────┴──────────────────────────────────┘
```

---

## Schritt 8: Output — Branches

Liste ALLE Branches in denen Commits von Patryk im Zeitraum gefunden wurden:

```bash
cd "$REPO" && git log --all \
  --author="$AUTHOR" \
  --since="$SINCE" --until="$UNTIL" \
  --no-merges \
  --pretty=format:"%D" | tr ',' '\n' | sed 's/^ //' | grep -v '^$' | sort -u
```

```
BRANCHES:
  - feature/DCSRE-98_QDVS_Selbstauskunft_Anzeigen
  - feature/DCSRE-882_MetaDaten_Analyse
  - feature/DCSRE-882_MetaDaten_Analyse_Retry
  - feature/DCSRE-1430_QDVTP_Selbstauskunft
  - feature/DCSRE-1513_Dashboard_Pflegeeinrichtung
  - ...
```

---

## Schritt 9: Hinweise ausgeben

```
HINWEISE:
  - Stunden basieren auf Commit-Zeitstempel (erster → letzter + 1h Puffer)
  - Reale Arbeitszeit ist HOEHER (Analyse, Meetings, Reviews ohne Commits)
  - ZEP-Eintraege auf 0.5h gerundet
  - Cap: max 12h pro Tag
  - Wochenende/Feiertage: nur angezeigt wenn Commits vorhanden
  - --all erfasst: lokale Branches, Remote-Branches, Worktrees
```

---

## Fehler-Handling

| Fehler | Reaktion |
|--------|----------|
| Kein Zeitraum angegeben | Default: letzte 30 Tage |
| Keine Commits im Zeitraum | "Keine Commits von Patryk Krzyzanski im Zeitraum {VON}–{BIS}" |
| Repo nicht erreichbar | FEHLER + Pfad anzeigen |
| Ticket nicht aus Commit/Branch erkennbar | Kategorie "SONSTIGE" |
