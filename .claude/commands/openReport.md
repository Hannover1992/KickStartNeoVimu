Oeffne alle Analysis-Reports im Browser als gerenderte HTML-Seiten.

## Ablauf

### Schritt 1: Existierenden Server pruefen und stoppen
Pruefe ob bereits ein Report-Server laeuft:
```bash
# Windows: Pruefe ob Port 4200 belegt ist
netstat -ano | findstr :4200
```
Falls ja, kill den Prozess.

### Schritt 2: Report-Server als Background-Task starten
Starte den Node.js Server als Background-Task:
```bash
node .claude/tools/report-server.js 4200
```
- Verwende `run_in_background: true`
- Der Server hostet alle .md Dateien aus `.claude/analysis/` als gerenderte HTML
- Keine npm-Dependencies noetig

### Schritt 3: Reports identifizieren
Scanne `.claude/analysis/` nach allen Reports. Prioritaet:
1. `opus/` -- Finale Analyse-Dokumente (hoechste Prioritaet)
2. `sonnet/` -- Tiefenanalysen
3. Root-Level `.md` Dateien
4. `haiku/` -- Kartografie-Findings

### Schritt 4: Chrome in NEUEM FENSTER oeffnen
Oeffne Chrome als NEUES FENSTER mit allen Reports als Tabs (ein einziger Befehl):
```bash
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --new-window "http://localhost:4200/" "http://localhost:4200/report/opus/REPORT1.md" "http://localhost:4200/report/sonnet/REPORT2.md"
```
WICHTIG: `--new-window` MUSS verwendet werden, damit ein separates Browser-Fenster geoeffnet wird.
Alle URLs in EINEM Befehl uebergeben -- Chrome oeffnet jede als eigenen Tab im neuen Fenster.

### Schritt 5: Bestaetigung
Zeige dem User:
- Anzahl gehosteter Reports
- Server-URL (http://localhost:4200/)
- Hinweis: Server laeuft als Background-Task, kann mit `netstat -ano | findstr :4200` und `taskkill` gestoppt werden

## Wichtig
- Server braucht KEINE npm install -- nur Node.js built-in Module
- Reports werden bei jedem Seitenaufruf frisch gelesen (Live-Updates!)
- Dark Theme mit Syntax-Highlighting
- Navigation zwischen Reports ueber Top-Bar
