---
type: satellite
---

Commit erstellen und mit PR-Gruppe verknuepfen.

$ARGUMENTS = Gruppen-Nummer (z.B. "1", "6", "14")

1. Pruefe zuerst `git status` - gibt es Aenderungen zum Committen?

2. Wenn KEINE staged Aenderungen:
   - Zeige "Keine Aenderungen staged. Erst `git add` oder `/pr-stage` ausfuehren."

3. Wenn Aenderungen vorhanden:
   - Lese Gruppen-Thema aus State-Datei
   - Schlage Commit-Message vor: `DCSRE-946: <Thema>`

4. Frage User: "Commit mit dieser Message erstellen? (ja/nein/andere Message)"

5. Bei Bestaetigung, fuehre aus:
```
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\commit.ps1" -PrId 18979 -GroupNr $ARGUMENTS -Message "<message>"
```

6. Nach erfolgreichem Commit:
   - Zeige den Commit-Hash
   - Zeige die TFS-Commit-URL fuer die PR-Antwort
   - Bestaetigen: "Gruppe X auf 'done' gesetzt"
