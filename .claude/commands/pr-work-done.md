---
type: satellite
---

Beendet Arbeit an der aktiven Gruppe und ordnet Commits zu.

$ARGUMENTS = Commit-Hashes (komma-separiert), z.B. "abc123,def456"

## Ablauf

1. **Pruefe aktive Arbeit:**
   Lies `ActiveWork` aus der State-Datei `.claude/analysis/pr-18979-state.json`
   - Wenn keine aktive Arbeit: Fehler anzeigen
   - Sonst: GroupNr aus ActiveWork nehmen

2. **Commits zuordnen:**
   Fuer jeden Commit-Hash in $ARGUMENTS:
   - Hole Commit-Details mit `git show --format="%H|%s|%ci" -s <hash>`
   - Fuege zur Gruppe hinzu: `{ Hash, Message, Date }`

3. **Status aktualisieren:**
   - Setze Gruppe.Status auf "done"
   - Loesche ActiveWork aus State

4. **Ausgabe:**
   ```
   Gruppe X abgeschlossen!

   Commits zugeordnet:
     - abc123: Commit message 1
     - def456: Commit message 2

   Naechste Schritte:
     /pr-findings X    → Im Browser antworten
     /pr-link X        → Commit-URLs kopieren
   ```

## Beispiel

```
/pr-work-done f8de0f5,a1b2c3d
```

Ordnet beide Commits der aktiven Gruppe zu und schliesst die Arbeit ab.
