---
type: satellite
---

Status einer PR-Gruppe manuell setzen.

$ARGUMENTS = "Gruppen-Nummer Status" (z.B. "1 done", "6 waiting", "14 wontfix")

Parse $ARGUMENTS in GroupNr und Status.

Gueltige Status-Werte:
- `pending` - Noch nicht bearbeitet
- `in_progress` - Gerade in Arbeit
- `done` - Erledigt (Commit vorhanden)
- `waiting` - Warte auf Reviewer-Feedback
- `wontfix` - Wird nicht umgesetzt

Fuehre aus:
```
powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\set-status.ps1" -PrId 18979 -GroupNr <nr> -Status <status>
```

Bestaetigen: "Gruppe X: alter_status -> neuer_status"
