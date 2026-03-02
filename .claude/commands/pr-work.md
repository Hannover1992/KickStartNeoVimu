Startet Arbeit an einer PR-Gruppe - alle neuen Commits gehoeren zu dieser Gruppe.

$ARGUMENTS = Gruppen-Nummer (z.B. "1", "6")

Fuehre das PowerShell-Skript aus:
```
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\work.ps1" -PrId 18979 -GroupNr $ARGUMENTS
```

Das Skript:
1. Merkt sich den aktuellen Commit als Startpunkt
2. Setzt Status auf "in_progress"
3. Speichert aktive Gruppe in State-Datei

Alle Commits die ab jetzt gemacht werden, gehoeren zu Gruppe $ARGUMENTS.

Wenn fertig: /pr-work-done
