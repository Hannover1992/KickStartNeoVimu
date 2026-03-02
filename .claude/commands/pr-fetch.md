PR-Kommentare von TFS abrufen und Arbeitsplan erstellen.

Fuehre das PowerShell-Skript aus:
```
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\fetch.ps1" -PrId $ARGUMENTS
```

Das Skript:
1. Holt alle Kommentare vom PR via TFS REST API
2. Filtert auf aktive Code-Kommentare
3. Gruppiert nach aehnlichem Kommentar-Inhalt
4. Erstellt `pr-{id}-arbeitsplan.md` mit allen Gruppen

Nach Ausfuehrung: Oeffne die Arbeitsplan-Datei in VS Code und nutze `/pr-open` um Kommentare im Browser zu oeffnen.
