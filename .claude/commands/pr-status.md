PR-Status Uebersicht anzeigen.

Fuehre das PowerShell-Skript aus:
```
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\status.ps1" -PrId 18979
```

Das Skript zeigt 3 klare Kategorien:

1. **AKTION ERFORDERLICH** (rot)
   - Threads wo der Reviewer geantwortet hat
   - Ich muss noch reagieren/antworten

2. **WARTET AUF REVIEWER** (gelb)
   - Threads wo ich zuletzt geantwortet habe
   - Ball liegt beim Reviewer

3. **ABGESCHLOSSEN** (gruen)
   - Fertige Gruppen

Biete an: "Welche Gruppe moechtest du bearbeiten? Nutze `/pr-work <nr>` fuer Details."
