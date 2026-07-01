---
type: satellite
---

PR-Kommentare im Browser oeffnen.

Fuehre das PowerShell-Skript aus:
```
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\open.ps1" -Ids "$ARGUMENTS"
```

Verwendung:
- `/pr-open 121074` - Einzelnen Kommentar oeffnen
- `/pr-open 121074,121075,121076` - Mehrere Kommentare oeffnen

Jeder Kommentar wird in einem neuen Browser-Tab geoeffnet, direkt an der richtigen Stelle im PR.
