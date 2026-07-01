---
status: active
version: 1.0.0
created: 2026-02-08
modified: 2026-02-08
author: OmniCommand
chain: WritePaper
position: init
phase: Setup
type: building-block
tags: [setup, WritePaper, init, RAG]
---

# /_WP_init - WritePaper Projekt-Initialisierung

```
╔══════════════════════════════════════════════════════════════════════════╗
║ VERTRAG: /_WP_init                                                    ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ ACTOR: INITIALIZER                                                       ║
║   TUT:                                                                   ║
║     - Projektordner erstellen (research/, output/, config/, logs/)       ║
║     - ChromaDB-Kollektionen initialisieren (SOURCES, COVERED, EXCLUSION)║
║     - MCP health_check + init aufrufen                                   ║
║     - project.yaml + _manifest.md anlegen                                ║
║     - session-state.json initialisieren                                  ║
║   NICHT:                                                                 ║
║     - Quellen ingestieren (→ research)                                   ║
║     - Paper-Struktur extrahieren (→ structure)                           ║
║                                                                          ║
║ LIEST (Input) - PFLICHT:                                                 ║
║   1. User-Input: project_name, research_questions (CLI-Parameter)       ║
║                                                                          ║
║ SCHREIBT (Output) - PFLICHT:                                             ║
║   1. config/project.yaml                                                 ║
║   2. quellen/ (leerer Ordner)                                            ║
║   3. output/ (leerer Ordner)                                             ║
║   4. _manifest.md (INITIAL: status=setup, next_step=session)             ║
║   5. session-state.json (INITIAL: phase=setup, iteration=0)              ║
║                                                                          ║
║ POSITION:                                                                ║
║   TYPE: LINEAR                                                           ║
║   AFTER: --- (Startpunkt)                                                ║
║   BEFORE: /_WP_session                                                 ║
║   PHASE: Setup                                                           ║
║   CHAIN: [START] → [init] → [session]                                    ║
║                                                                          ║
║ MCP-BREMSE:                                                              ║
║   Tools: mcp__cleancoder__health_check, mcp__cleancoder__init            ║
║   Call-Limits: easy=2, normal=2, hard=2                                  ║
║   KRITISCH: BLOCKING - Init schlaegt fehl → Pipeline STOP               ║
║                                                                          ║
║ SCHWIERIGKEIT:                                                           ║
║   Keine Dimensionen (Setup-Command, immer identisch)                     ║
║                                                                          ║
║ NOTIFY:                                                                  ║
║   powershell -Command "notify 'WritePaper /_WP_init abgeschlossen'"   ║
║                                                                          ║
║ TAGS:                                                                    ║
║   type: setup                                                            ║
║   op: WritePaper                                                         ║
║   chain-position: init                                                   ║
║   next: "[[WritePaper-session]]"                                         ║
╚══════════════════════════════════════════════════════════════════════════╝
```

## Verantwortlichkeit

### TUT (Kernaufgaben)
1. **Projektstruktur** anlegen:
   - Verzeichnisse: `quellen/`, `output/`, `output/assess/`, `output/models/`, `output/figures/`, `config/`, `logs/`
   - Alle Ordner müssen existieren, bevor Session startet

2. **ChromaDB initialisieren**:
   - MCP health_check ausführen → Server erreichbar?
   - MCP init ausführen → 3 Collections (SOURCES, COVERED, EXCLUSION)
   - Bei Fehler → Pipeline STOPPEN (BLOCKING)

3. **Config-Dateien** erstellen:
   - `config/project.yaml` mit Name, Forschungsfragen, Datum, Schwierigkeit
   - `_manifest.md` mit Initial-Status (status=setup, next=session)
   - `session-state.json` mit Phase=setup, Iteration=0

4. **Validierung** durchführen:
   - Alle Ordner existieren?
   - YAML parsebar?
   - JSON parsebar?
   - MCP Collections angelegt?

### TUT NICHT
- **Keine Quellen ingestieren**: Das macht `/_WP_research` später
- **Keine Struktur extrahieren**: Das macht `/_WP_structure` später
- **Kein Kapitel-Schreiben**: Das ist Research-Phase
- **Keine User-Interaktion**: Init ist vollautomatisch

### Eskalation an User
- **MCP Server nicht erreichbar**: User muss MCP-Server starten
- **Projektordner existiert bereits**: User muss entscheiden (überschreiben/abbrechen)
- **Fehlende Schreibrechte**: User muss Permissions prüfen

---

## Ablauf-Schritte

### Schritt 0: User-Input validieren
**Input**: `project_name` (String), `research_questions` (List[String])

**Prüfungen**:
```
WENN project_name leer ODER research_questions leer:
  → FEHLER: "Pflichtparameter fehlen: project_name und research_questions"
  → STOP

WENN project_path bereits existiert:
  → WARNUNG: "Projekt existiert bereits: {project_path}"
  → User-Entscheidung einholen: (O)überschreiben, (A)bbrechen?
  → Bei Abbruch: STOP
```

**Beispiel-Aufruf**:
```bash
# User gibt an:
project_name: "Clean Code Prinzipien"
research_questions:
  - "Was sind die Kernprinzipien von Clean Code?"
  - "Wie beeinflusst TDD die Code-Qualität?"
```

---

### Schritt 1: Projektstruktur erstellen
**Aktion**: Alle Verzeichnisse anlegen

**Verzeichnisbaum**:
```
{project_path}/
├── quellen/              # PDF, MD, TXT → werden später ingested
├── output/               # LaTeX, Paper, Figures
│   ├── assess/           # Quality-Gate-Reports
│   ├── models/           # Knowledge Models (Session-Output)
│   └── figures/          # Grafiken, Diagramme
├── config/               # project.yaml
└── logs/                 # MCP-Logs, Pipeline-Logs
```

**PowerShell**:
```powershell
$projectPath = "C:\path\to\project"
$folders = @("quellen", "output", "output\assess", "output\models", "output\figures", "config", "logs")

foreach ($folder in $folders) {
  $fullPath = Join-Path $projectPath $folder
  if (-not (Test-Path $fullPath)) {
    New-Item -Path $fullPath -ItemType Directory -Force
  }
}
```

**Validierung**:
- Alle 7 Ordner existieren? → JA: weiter, NEIN: FEHLER

---

### Schritt 2: MCP-Initialisierung
**Aktion**: RAG-Datenbank vorbereiten

**2.1 Health Check**:
```python
result = mcp__cleancoder__health_check()

WENN result.status != "healthy":
  → FEHLER: "MCP-Server nicht erreichbar. Bitte prüfen: {result.message}"
  → STOP (BLOCKING)
```

**2.2 Init**:
```python
result = mcp__cleancoder__init()

WENN result.status != "initialized":
  → FEHLER: "ChromaDB-Initialisierung fehlgeschlagen: {result.message}"
  → STOP (BLOCKING)

# Erwartete Collections:
# - {project_name}_SOURCES   (für research_ingest)
# - {project_name}_COVERED   (für mark_covered)
# - {project_name}_EXCLUSION (für add_exclusion)
```

**Validierung**:
- 3 Collections angelegt? → JA: weiter, NEIN: FEHLER

---

### Schritt 3: Config-Dateien erstellen

#### 3.1 `config/project.yaml`
**Schema**:
```yaml
name: "{project_name}"
research_questions:
  - "{frage_1}"
  - "{frage_2}"
  - ...
created: "{YYYY-MM-DD}"
difficulty: "normal"  # Default, kann später geändert werden
collections:
  sources: "{project_name}_SOURCES"
  covered: "{project_name}_COVERED"
  exclusion: "{project_name}_EXCLUSION"
```

**Beispiel**:
```yaml
name: "Clean Code Prinzipien"
research_questions:
  - "Was sind die Kernprinzipien von Clean Code?"
  - "Wie beeinflusst TDD die Code-Qualität?"
created: "2026-02-08"
difficulty: "normal"
collections:
  sources: "Clean_Code_Prinzipien_SOURCES"
  covered: "Clean_Code_Prinzipien_COVERED"
  exclusion: "Clean_Code_Prinzipien_EXCLUSION"
```

---

#### 3.2 `_manifest.md`
**Schema**:
```markdown
---
status: setup
phase: Setup
next_step: session
created: {YYYY-MM-DD}
---

# Paper: {project_name}

## Research Questions
1. {frage_1}
2. {frage_2}

## Status
- **Phase**: Setup
- **Next Step**: /_WP_session (Session-Planning)
- **Chapters**: [] (noch keine Kapitel)

## Pipeline
1. [DONE] init - Projekt initialisiert
2. [NEXT] session - Session planen
3. [TODO] research - Quellen ingestieren
4. [TODO] structure - Paper-Struktur extrahieren
5. [TODO] write - Kapitel schreiben (iterativ)
6. [TODO] verify - RAG-Verifikation
```

---

#### 3.3 `session-state.json`
**Schema**:
```json
{
  "phase": "setup",
  "difficulty": "normal",
  "iteration": 0,
  "chapters": [],
  "current_chapter": null,
  "research_budget_remaining": null,
  "knowledge_state": {},
  "quality_history": [],
  "created": "2026-02-08T10:30:00Z",
  "last_updated": "2026-02-08T10:30:00Z"
}
```

**Felder erklärt**:
- `phase`: Setup → Session → Research → Write → Verify → Done
- `difficulty`: easy/normal/hard (bestimmt MCP-Call-Limits)
- `iteration`: 0 (wird in Write-Phase hochgezählt)
- `chapters`: [] (wird von structure gefüllt)
- `current_chapter`: null (wird von write gesetzt)
- `research_budget_remaining`: null (wird von session berechnet)
- `knowledge_state`: {} (wird von research gefüllt)
- `quality_history`: [] (wird von verify gefüllt)

---

### Schritt 4: Validierung & Abschluss
**Final Checks**:
```
1. Ordner existieren?
   → ls quellen/, output/, config/, logs/
   → Alle 7 vorhanden? JA: ✓

2. project.yaml parsebar?
   → Versuche YAML zu laden
   → Fehler? NEIN: ✓

3. session-state.json parsebar?
   → Versuche JSON zu laden
   → Fehler? NEIN: ✓

4. MCP Collections?
   → Query ChromaDB: List Collections
   → 3 Collections vorhanden? JA: ✓

WENN alle Checks ✓:
  → Ausgabe: "✓ Projekt initialisiert: {project_path}"
  → Ausgabe: "➜ Nächster Schritt: /_WP_session"
  → NOTIFY: "WritePaper /_WP_init abgeschlossen"
  → EXIT 0

SONST:
  → Ausgabe: "✗ Initialisierung fehlgeschlagen"
  → Ausgabe: Fehlerdetails
  → EXIT 1
```

---

## Output-Format

### Beispiel-Projektstruktur (nach Init)
```
C:\Research\CleanCode\
├── quellen\                  # [LEER] - User legt später PDFs ab
├── output\
│   ├── assess\               # [LEER] - Quality-Reports kommen später
│   ├── models\               # [LEER] - Knowledge Models kommen später
│   └── figures\              # [LEER] - Grafiken kommen später
├── config\
│   └── project.yaml          # [ERSTELLT]
├── logs\                     # [LEER] - Logs kommen später
├── _manifest.md              # [ERSTELLT]
└── session-state.json        # [ERSTELLT]
```

### Beispiel `config/project.yaml`
```yaml
name: "Clean Code Prinzipien"
research_questions:
  - "Was sind die Kernprinzipien von Clean Code?"
  - "Wie beeinflusst TDD die Code-Qualität?"
created: "2026-02-08"
difficulty: "normal"
collections:
  sources: "Clean_Code_Prinzipien_SOURCES"
  covered: "Clean_Code_Prinzipien_COVERED"
  exclusion: "Clean_Code_Prinzipien_EXCLUSION"
```

### Beispiel `_manifest.md`
```markdown
---
status: setup
phase: Setup
next_step: session
created: 2026-02-08
---

# Paper: Clean Code Prinzipien

## Research Questions
1. Was sind die Kernprinzipien von Clean Code?
2. Wie beeinflusst TDD die Code-Qualität?

## Status
- **Phase**: Setup
- **Next Step**: /_WP_session (Session-Planning)
- **Chapters**: [] (noch keine Kapitel)

## Pipeline
1. [DONE] init - Projekt initialisiert
2. [NEXT] session - Session planen
3. [TODO] research - Quellen ingestieren
4. [TODO] structure - Paper-Struktur extrahieren
5. [TODO] write - Kapitel schreiben (iterativ)
6. [TODO] verify - RAG-Verifikation
```

### Beispiel `session-state.json`
```json
{
  "phase": "setup",
  "difficulty": "normal",
  "iteration": 0,
  "chapters": [],
  "current_chapter": null,
  "research_budget_remaining": null,
  "knowledge_state": {},
  "quality_history": [],
  "created": "2026-02-08T10:30:00Z",
  "last_updated": "2026-02-08T10:30:00Z"
}
```

---

## Qualitätskriterien

### MUSS-Kriterien (Blocking)
1. **Alle Ordner existieren**: quellen/, output/, config/, logs/ + Unterordner
2. **project.yaml valide**: YAML parsebar, alle Pflichtfelder vorhanden
3. **session-state.json valide**: JSON parsebar, Schema korrekt
4. **MCP initialisiert**: 3 Collections (SOURCES, COVERED, EXCLUSION) angelegt
5. **_manifest.md existiert**: Markdown-Datei mit Frontmatter

**Prüfung**:
```bash
# Alle Ordner?
Test-Path C:\Research\CleanCode\quellen
Test-Path C:\Research\CleanCode\output\assess
# ... (7 Checks)

# YAML valide?
ConvertFrom-Yaml (Get-Content config\project.yaml -Raw)

# JSON valide?
ConvertFrom-Json (Get-Content session-state.json -Raw)

# MCP Collections?
# (via MCP-Tool oder ChromaDB-Client)
```

### SOLL-Kriterien (Warnung)
1. **project_name eindeutig**: Kein anderes Projekt mit gleichem Namen
2. **research_questions spezifisch**: Min. 10 Wörter pro Frage
3. **Schreibrechte**: User kann in Projektordner schreiben

---

## NOTIFY

**Bei Erfolg**:
```powershell
powershell -Command "notify 'WritePaper /_WP_init abgeschlossen'"
```

**Console-Output**:
```
✓ Projekt initialisiert: C:\Research\CleanCode
  ✓ Ordnerstruktur angelegt (7 Verzeichnisse)
  ✓ MCP-Server erreichbar
  ✓ ChromaDB initialisiert (3 Collections)
  ✓ Config-Dateien erstellt (project.yaml, _manifest.md, session-state.json)

➜ Nächster Schritt: /_WP_session
  Tipp: Session plant Budget + Iterationen
```

**Bei Fehler**:
```
✗ Initialisierung fehlgeschlagen

Fehler: MCP-Server nicht erreichbar
  → Prüfe: Ist der MCP-Server gestartet?
  → Kommando: mcp__cleancoder__health_check()

➜ Abbruch: Pipeline gestoppt
```

---

## Checkliste für User

Vor dem Init:
- [ ] MCP-Server läuft (`mcp__cleancoder__health_check`)
- [ ] Projektname festgelegt (eindeutig, keine Sonderzeichen)
- [ ] Forschungsfragen formuliert (min. 1, besser 2-3)
- [ ] Schreibrechte im Zielordner

Nach dem Init:
- [ ] Ordnerstruktur vorhanden (7 Verzeichnisse)
- [ ] `config/project.yaml` existiert + valide
- [ ] `_manifest.md` existiert (Status=setup)
- [ ] `session-state.json` existiert (Phase=setup)
- [ ] ChromaDB Collections angelegt (3 Stück)
- [ ] Console-Output zeigt "✓ Projekt initialisiert"

---

## Nächster Command

**Chain-Flow**:
```
[START] → /_WP_init → [/_WP_session]
```

**Aufruf**:
```bash
# User führt aus:
/_WP_session
```

**Übergabe**:
- `session` liest `config/project.yaml` + `session-state.json`
- `session` plant Budget, Iterationen, Schwierigkeit
- `session` updated `session-state.json` mit research_budget_remaining

---

## Tags & Metadaten

```yaml
type: setup
operation: WritePaper
chain-position: init
phase: Setup
difficulty: none  # Setup hat keine Schwierigkeitsgrade
mcp-tools:
  - mcp__cleancoder__health_check
  - mcp__cleancoder__init
next-command: "[[WritePaper-session]]"
blocking: true  # MCP-Fehler stoppen Pipeline
estimated-duration: "30 Sekunden"
```
