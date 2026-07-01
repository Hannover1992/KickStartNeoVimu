---
type: satellite
---

Gruppen-Details und Umsetzungsplan anzeigen.

$ARGUMENTS = Gruppen-Nummer (z.B. "1", "6", "14")

Fuehre das PowerShell-Skript aus:
```
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\plan.ps1" -PrId 18979 -GroupNr $ARGUMENTS
```

Analysiere die JSON-Ausgabe und erstelle einen Umsetzungsplan:

1. **Thema:** Was muss gemacht werden?
2. **Dateien:** Welche Dateien sind betroffen? (mit Zeilennummern)
3. **Kommentar:** Was hat der Reviewer geschrieben?
4. **Schritte:**
   - Kommentare ansehen: `/pr-message $ARGUMENTS`
   - Aenderungen implementieren (beschreibe konkret was zu tun ist)
   - Commit erstellen: `/pr-commit $ARGUMENTS`

Wenn der Status "done" ist, zeige die zugehoerigen Commits.
Wenn der Status "waiting" ist, erklaere dass auf Reviewer-Feedback gewartet wird.
