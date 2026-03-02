# LOC Statistiken für Patryk Krzyzanski

Berechne die Lines of Code (LOC) Statistiken pro Tag für den angegebenen Zeitraum.

## Parameter
- $ARGUMENTS: Zeitraum (z.B. "dezember", "letzte-woche", "2025-12-01", oder Anzahl Tage wie "30")

## Schritt 1: Zeitraum bestimmen

Interpretiere `$ARGUMENTS` wie folgt:
- Leer oder "heute" oder "today" → --since="midnight" (Standard: heute)
- "dezember" oder "december" → --since="2025-12-01"
- "november" → --since="2025-11-01" --until="2025-12-01"
- "letzte-woche" oder "last-week" → --since="7 days ago"
- "letzter-monat" oder "last-month" → --since="30 days ago"
- Datum im Format YYYY-MM-DD → --since="DATUM"
- Zahl (z.B. "14") → --since="14 days ago"

## Schritt 2: Haupt-LOC-Statistiken berechnen

Führe diesen Befehl aus und ersetze SINCE_DATE mit dem ermittelten Zeitraum:

```bash
cd "C:/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend" && git log --all --author="Patryk Krzyzanski" --since="SINCE_DATE" --pretty=format:"%ad" --date=short --shortstat | awk '
/^[0-9]{4}-[0-9]{2}-[0-9]{2}/ { date=$1 }
/insertion|deletion/ {
  ins=0; del=0
  for(i=1;i<=NF;i++) {
    if($(i+1) ~ /insertion/) ins=$i
    if($(i+1) ~ /deletion/) del=$i
  }
  dates[date] += ins + del
  insertions[date] += ins
  deletions[date] += del
}
END {
  total_ins=0; total_del=0
  n=asorti(dates, sorted)
  for(i=1; i<=n; i++) {
    d=sorted[i]
    printf "%s | +%-6d | -%-6d | = %6d LOC\n", d, insertions[d], deletions[d], dates[d]
    total_ins += insertions[d]
    total_del += deletions[d]
  }
  printf "───────────────────────────────────────────\n"
  printf "TOTAL    | +%-6d | -%-6d | = %6d LOC\n", total_ins, total_del, total_ins+total_del
  if (n > 0) printf "Arbeitstage: %d | Durchschnitt: %d LOC/Tag\n", n, (total_ins+total_del)/n
}'
```

## Schritt 3: Commit-Details anzeigen

Zeige die einzelnen Commits mit Ticket-Nummern:

```bash
cd "C:/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend" && git log --all --author="Patryk Krzyzanski" --since="SINCE_DATE" --pretty=format:"%ad %s" --date=short --shortstat | head -60
```

## Schritt 4: Ticket-Aufteilung berechnen

Für jedes gefundene Ticket (DCSRE-XXXX), berechne die LOC separat:

```bash
cd "C:/Users/Administrator/Documents/Work/Code2/DCSRE/Sources/Backend" && git log --all --author="Patryk Krzyzanski" --since="SINCE_DATE" --grep="DCSRE-TICKET" --pretty=format:"%ad" --date=short --shortstat | awk '
/^[0-9]{4}-[0-9]{2}-[0-9]{2}/ { date=$1 }
/insertion|deletion/ {
  ins=0; del=0
  for(i=1;i<=NF;i++) {
    if($(i+1) ~ /insertion/) ins=$i
    if($(i+1) ~ /deletion/) del=$i
  }
  total += ins + del
}
END { printf "DCSRE-TICKET: %d LOC\n", total }'
```

## Schritt 5: Ausgabe formatieren

Erstelle eine übersichtliche Zusammenfassung mit:

1. **Tages-Tabelle** mit Datum, Hinzugefügt, Gelöscht, Gesamt
2. **Total und Durchschnitt**
3. **Top-Tage** (die 3-5 produktivsten Tage)
4. **Ticket-Aufteilung** (LOC pro DCSRE-Ticket)
5. **Commit-Liste** (die wichtigsten Commits mit Beschreibung)

---

## Technische Erklärung

### Warum `--all`?
Der Parameter `--all` durchsucht ALLE Branches, inklusive:
- Lokale Feature-Branches
- Worktrees (z.B. DCSRE-946_WarnungenBeseitigen)
- Remote-Branches

Ohne `--all` würden nur Commits im aktuellen Branch gezählt.

### AWK-Script Erklärung

```awk
/^[0-9]{4}-[0-9]{2}-[0-9]{2}/ { date=$1 }
```
Erkennt Datumszeilen (z.B. "2025-12-19") und speichert das Datum.

```awk
/insertion|deletion/ { ... }
```
Erkennt Statistik-Zeilen (z.B. "3 files changed, 45 insertions(+), 12 deletions(-)").

```awk
for(i=1;i<=NF;i++) {
  if($(i+1) ~ /insertion/) ins=$i
  if($(i+1) ~ /deletion/) del=$i
}
```
Extrahiert die Zahlen vor "insertion" und "deletion".

```awk
dates[date] += ins + del
insertions[date] += ins
deletions[date] += del
```
Summiert die Werte pro Tag in assoziativen Arrays.

```awk
n=asorti(dates, sorted)
```
Sortiert die Tage chronologisch.

### Worktrees im Projekt

Aktuelle Worktrees:
- `DCSRE` (develop)
- `DCSRE-1189_DiamantenProblem`
- `DCSRE-1189_Implementieren`
- `DCSRE-946_WarnungenBeseitigen`

Alle werden durch `--all` erfasst.
