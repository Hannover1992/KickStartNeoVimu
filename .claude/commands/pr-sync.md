---
type: satellite
---

PR-Sync: TFS-Status aktualisieren und analysieren.

## Schritte

1. **Fuehre Sync-Skript aus:**
   ```
   powershell -ExecutionPolicy Bypass -File "C:\Users\Administrator\Documents\Work\Code2\DCSRE\.claude\scripts\pr\sync.ps1" -PrId 18979
   ```

2. **Analysiere die Ausgabe (DEINE AUFGABE):**

   Nach dem Sync zeigt das Skript den Antwort-Status pro Gruppe.
   DU analysierst und schlägst Status-Aenderungen vor:

   a) **100% beantwortet (IsMyResponse=true fuer alle Threads):**
      - User hat auf alle Findings geantwortet
      - Schlage vor: Status auf "waiting" setzen
      - "Gruppe X: Alle 21 Findings beantwortet -> Status 'waiting' setzen?"

   b) **Teilweise beantwortet:**
      - Zeige welche noch offen sind
      - "Gruppe X: 15/21 beantwortet. Noch offen: Thread Y in Datei Z"

   c) **Architekt hat nochmal geantwortet (IsMyResponse=false nach vorheriger Antwort):**
      - Status zurueck auf "in_progress"
      - "Gruppe X: Architekt hat nochmal geantwortet -> anschauen!"

   d) **TFS-Status geaendert (fixed/closed):**
      - Wenn alle Threads fixed/closed -> Status auf "done"
      - "Gruppe X: Alle Threads vom Architekt geschlossen -> 'done'?"

3. **Warte auf User-Bestaetigung:**
   Aendere Status NUR wenn User bestaetigt!
   Manuelle Pflege hat Vorrang.

## Beispiel-Ausgabe

Nach Analyse:
```
Sync-Ergebnis:

[OK] Gruppe 1: 21/21 beantwortet -> Status 'waiting' setzen?
[>>] Gruppe 2: 17/18 beantwortet
     Noch offen: Thread 121017 in SetupController.cs:279
[!!] Gruppe 4: Architekt hat nochmal geantwortet (3 Threads)
[+]  Gruppe 6: Status bereits 'done'

Soll ich Gruppe 1 auf 'waiting' setzen?
```
