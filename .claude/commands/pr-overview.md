---
type: satellite
---

PR-Overview: Detailansicht einer oder mehrerer Gruppen.

$ARGUMENTS = Gruppen-Nummern (z.B. "2" oder "2,4,11")

## Aufgabe

Zeige die vollstaendige Planning-Analyse fuer die angegebenen Gruppen.

## Schritte

1. **Lade State-Datei:**
   Lies `.claude/analysis/pr-18979-state.json`

2. **Fuer jede angegebene Gruppe zeige:**

```
============================================
 GRUPPE {Nr}: {Theme}
============================================

ZUSAMMENFASSUNG:
  {Planning.Summary}

AUFWAND:
  Geschaetzt: {Planning.EstimatedTime}
  Komplexitaet: {Planning.Complexity} (S=Klein, M=Mittel, L=Gross)

BETROFFENE DATEIEN:
  - {Planning.AffectedFiles[0]}
  - {Planning.AffectedFiles[1]}
  ...

LOESUNGSANSATZ:
  {Planning.SolutionApproach}

THREADS ({Anzahl}):
  Thread {Id}: {File}:{Line}
    Kommentar: "{Erster Satz des Kommentars}..."
    Status: {TfsStatus}
    Letzter: {LastAuthor}

COMMITS:
  - {Hash}: {Message}
  (oder: Keine Commits zugeordnet)

============================================
```

3. **Falls keine Planning-Daten vorhanden:**
   ```
   WARNUNG: Gruppe {Nr} hat keine Planning-Daten.
   Fuehre /pr-planning {Nr} aus um die Analyse zu starten.
   ```

4. **Am Ende zeige:**
   ```
   Naechste Schritte:
     /pr-work {Nr}      -> Gruppe bearbeiten
     /pr-findings {Nr}  -> Im Browser oeffnen
     /pr-planning {Nr}  -> Neu analysieren
   ```

## Beispiel

```
/pr-overview 2       # Nur Gruppe 2
/pr-overview 2,4,11  # Mehrere Gruppen
```
