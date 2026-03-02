Zeigt die TFS-Commit-URLs fuer eine PR-Gruppe und generiert fertige PR-Antworten.

$ARGUMENTS = Gruppen-Nummer (z.B. "1", "6")

Fuehre das PowerShell-Skript aus:
```
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\link.ps1" -PrId 18979 -GroupNr $ARGUMENTS
```

Das Skript:
1. Zeigt alle Commits die zu dieser Gruppe gehoeren
2. Generiert TFS-Commit-URLs
3. Erstellt fertige Markdown-Antwort fuer den PR-Kommentar
4. Setzt den Status automatisch auf "waiting"

Zeige dem User:
- Die Commit-Links
- Die fertige PR-Antwort zum Kopieren
- Den aktualisierten Status

Beispiel-Antwort fuer TFS:
```
Umgesetzt in:
- [73f79c47](https://tfs.itsg.de/tfs/.../commit/73f79c47...)
```
