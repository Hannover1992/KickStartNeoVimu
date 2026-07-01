---
type: satellite
---

PR-Planning: 3-Wellen-Analyse der PR-Kommentare (ULTRATHINK).

$ARGUMENTS = Gruppen-Nummern (z.B. "2,4,11") - optional, ohne = ALLE offenen Gruppen

## Uebersicht

Dieses Planning analysiert PR-Gruppen in 3 Wellen und erstellt:
- Aufwandsschaetzung pro Gruppe (15min / 30min / 45min / 1h+ )
- Kurze Beschreibung der Aufgabe
- Betroffene Dateien
- Loesungsansatz

## Schritte

### 0. Vorbereitung

1. Lies die State-Datei: `.claude/analysis/pr-18979-state.json`
2. Identifiziere offene Gruppen:
   - Wenn $ARGUMENTS angegeben: Nur diese Gruppen
   - Sonst: Alle Gruppen mit Status != "done"
3. Zeige Uebersicht: "Analysiere X Gruppen..."

### Welle 1: Kartografie (Haiku-Agenten, PARALLEL)

Fuer JEDE offene Gruppe starte einen Task-Agent mit `subagent_type="Explore"` und `model="haiku"`:

**Prompt fuer jeden Haiku-Agenten:**
```
Analysiere PR-Gruppe {Nr}: "{Theme}"

Thread-Details:
{Liste aller Threads mit File, Line, Kommentar-Text}

Aufgaben:
1. Lies die betroffenen Dateien (nur die relevanten Zeilen +/- 20)
2. Verstehe was der Reviewer will
3. Identifiziere ALLE betroffenen Code-Stellen
4. Schaetze den Aufwand:
   - 15min: Trivial (1 Datei, kleine Aenderung)
   - 30min: Klein (1-2 Dateien, moderate Aenderung)
   - 45min: Mittel (2-3 Dateien, komplexere Logik)
   - 1h+: Gross (4+ Dateien oder architekturelle Aenderung)

Ausgabe als JSON:
{
  "GroupNr": {Nr},
  "Summary": "1-2 Saetze was zu tun ist",
  "AffectedFiles": ["datei1.cs", "datei2.cs"],
  "EstimatedTime": "30min",
  "Complexity": "S|M|L",
  "Notes": "Besonderheiten falls vorhanden"
}
```

Starte bis zu 5 Agenten parallel pro Batch. Warte auf Ergebnisse.

### Welle 2: Verification (Sonnet-Agenten, SEQUENTIAL)

Fuer jede Gruppe mit Haiku-Ergebnis starte einen Task-Agent mit `subagent_type="general-sonnet"`:

**Prompt:**
```
Verifiziere und verfeinere die Haiku-Analyse fuer Gruppe {Nr}:

Haiku-Ergebnis:
{JSON vom Haiku}

Original-Kommentare:
{Thread-Details}

Aufgaben:
1. Pruefe ob die identifizierten Dateien korrekt sind
2. Lies den Code und verstehe den Kontext
3. Erstelle einen kurzen Loesungsansatz (2-3 Saetze)
4. Validiere/korrigiere die Aufwandsschaetzung

Ausgabe als JSON:
{
  "GroupNr": {Nr},
  "Summary": "Verfeinerte Beschreibung",
  "AffectedFiles": ["..."],
  "EstimatedTime": "korrigiert falls noetig",
  "Complexity": "S|M|L",
  "SolutionApproach": "Kurzer Loesungsansatz",
  "Validated": true/false,
  "ValidationNotes": "Falls Haiku falsch lag"
}
```

### Welle 3: Consolidation (Opus, EINMAL)

Nachdem alle Sonnet-Ergebnisse vorliegen:

1. **State-Datei aktualisieren:**
   Fuer jede Gruppe fuege `Planning`-Objekt hinzu:
   ```json
   {
     "Nr": 2,
     "Status": "pending",
     "Theme": "...",
     "Planning": {
       "Summary": "...",
       "EstimatedTime": "30min",
       "Complexity": "M",
       "AffectedFiles": ["..."],
       "SolutionApproach": "...",
       "AnalyzedAt": "2026-01-20T..."
     },
     "Threads": [...]
   }
   ```

2. **Gesamtuebersicht erstellen:**
   ```
   ============================================
    PR-PLANNING ERGEBNIS
   ============================================

   OFFENE GRUPPEN (5):
   -------------------
   Gruppe 2:  "SetupController XML Doku"        | 15 min | S
   Gruppe 4:  "Ausgaben in Deutsch"             | 45 min | M
   Gruppe 11: "DicPortAllocator Kommentar"      | 15 min | S
   Gruppe 16: "Program.cs Struktur"             | 30 min | M
   Gruppe 18: "StoredFile Dokumentation"        | 15 min | S
                                         ──────────────────
                                 Gesamt: ~2h 00min

   Details mit: /pr-overview <nr>
   ```

3. **Notify senden:**
   ```
   powershell -Command "notify 'PR-Planning fertig - X Gruppen analysiert, Gesamt: ~Y Stunden'"
   ```

## WICHTIG

- Haiku-Agenten laufen PARALLEL (max 5 gleichzeitig)
- Sonnet-Agenten laufen SEQUENTIAL (einer nach dem anderen)
- Bei Fehlern: Gruppe ueberspringen, am Ende melden
- Ergebnisse IMMER in State-Datei speichern
- Am Ende IMMER Notify senden

## Beispiel-Aufruf

```
/pr-planning         # Alle offenen Gruppen
/pr-planning 2,4     # Nur Gruppe 2 und 4 neu analysieren
```
