PR-Init: Rohe Daten von TFS holen.

$ARGUMENTS = PR-ID (z.B. "18979")

Fuehre das PowerShell-Skript aus:
```
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\fetch.ps1" -PrId $ARGUMENTS
```

Das Skript:
1. Holt alle PR-Kommentare von TFS
2. Filtert auf aktive Code-Kommentare
3. Speichert ROHE Daten in: .claude/analysis/pr-{id}-raw.json
4. KEINE Gruppierung! Das macht Claude in /pr-planning

**Nach erfolgreichem Abruf:**
Sage dem User: "Rohe Daten geholt. Jetzt /pr-planning fuer intelligente Gruppierung."
