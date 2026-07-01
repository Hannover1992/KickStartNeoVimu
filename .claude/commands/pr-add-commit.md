---
type: satellite
---

Existierenden Commit einer PR-Gruppe zuweisen.

$ARGUMENTS = "Gruppen-Nummer Commit-Hash" (z.B. "1 abc123", "6 f8de0f5")

Parse $ARGUMENTS in GroupNr und CommitHash.

Fuehre das PowerShell-Skript aus:
```
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\add-commit.ps1" -PrId 18979 -GroupNr <nr> -CommitHash <hash>
```

Das Skript:
1. Holt Commit-Info von Git (Message, Datum)
2. Fuegt Commit zur Gruppe hinzu
3. Speichert in State-Datei

Workflow:
- User sagt: "Gruppe 1 hat Commits abc, def, ghi"
- Claude fuehrt /pr-add-commit fuer jeden aus
- Danach /pr-link zeigt alle Commit-URLs
