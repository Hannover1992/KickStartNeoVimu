Oeffnet die PR-Findings (Kommentare von Christian) einer Gruppe im Browser.

$ARGUMENTS = Gruppen-Nummer (z.B. "1", "6", "14")

Fuehre das PowerShell-Skript aus:
```
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\findings.ps1" -PrId 18979 -GroupNr $ARGUMENTS
```

Das Skript:
1. Liest die Thread-IDs der Gruppe aus der State-Datei
2. Oeffnet jeden PR-Kommentar in einem neuen Browser-Tab
3. Status wird NICHT automatisch geaendert

Bestaetigen: "X Findings im Browser geoeffnet fuer Gruppe Y"

Workflow:
- /pr-link $nr    → Zeigt Commit-URLs zum Kopieren
- /pr-findings $nr → Oeffnet die Findings zum Beantworten
