# /_R_WP_research - RAG Source Ingestion

```yaml
status: active
version: 1.0.0
created: 2026-02-08
op: WritePaper
phase: Knowledge
type: research
chain_position: research
difficulty_scaling: true
mcp_critical: true
```

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════════╗
║ VERTRAG: /_R_WP_research                                                ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ ACTOR: RESEARCH BOOTSTRAPPER                                             ║
║   TUT:                                                                   ║
║     - /quellen/ Ordner scannen (PDF, LaTeX, MD, TXT)                     ║
║     - BibTeX-Metadaten extrahieren                                       ║
║     - MCP research_ingest aufrufen (SOURCES Collection)                  ║
║     - references.bib generieren                                          ║
║     - Budget-Tracking initialisieren                                     ║
║   NICHT:                                                                 ║
║     - Neue Quellen suchen (→ discovery)                                  ║
║     - Luecken fuellen (→ chapterGap)                                     ║
║                                                                          ║
║ LIEST (Input) - PFLICHT:                                                 ║
║   1. _manifest.md                                                        ║
║   2. session-state.json                                                  ║
║   3. config/project.yaml (research_questions)                            ║
║   4. quellen/ (Ordner-Scan)                                              ║
║                                                                          ║
║ SCHREIBT (Output) - PFLICHT:                                             ║
║   1. output/references.bib (BibTeX-Datei)                                ║
║   2. output/research-gaps-initial.json (research_gaps Output)            ║
║   3. _manifest.md (UPDATE: sources_count, next_step=discovery)           ║
║   4. session-state.json (UPDATE: research_budget_remaining)              ║
║                                                                          ║
║ POSITION:                                                                ║
║   TYPE: LOOP                                                             ║
║   LOOP-CONTEXT:                                                          ║
║     LOOP-NAME: Gap-Loop                                                  ║
║     LOOP-LEVEL: MIDDLE                                                   ║
║     ITERATION-VARIABLE: gap_research_count                               ║
║     MAX-ITERATIONS: extern kontrolliert von /_R_WP_chapterGap (max 3)   ║
║   ENTRY:                                                                 ║
║     NORMAL: /_R_WP_assess → THIS                                        ║
║   EXIT:                                                                  ║
║     NORMAL: THIS → /_R_WP_discovery                                     ║
║   PHASE: Knowledge                                                      ║
║   CHAIN: [assess] → [research] → [discovery]                            ║
║                                                                          ║
║ MCP-BREMSE:                                                              ║
║   Tools: mcp__cleancoder__research_ingest,                               ║
║          mcp__cleancoder__research_gaps,                                  ║
║          mcp__cleancoder__extract_keywords                               ║
║   Call-Limits: easy=8, normal=15, hard=30                                ║
║   Parameter: chunk_strategy="hybrid", chunk_size=512                     ║
║   KRITISCH: BLOCKING - Kein SOURCES → kein Writing                       ║
║                                                                          ║
║ SCHWIERIGKEIT:                                                           ║
║   easy:   5-10 Quellen, min_coverage=2                                   ║
║   normal: 10-20 Quellen, min_coverage=3                                  ║
║   hard:   20-40 Quellen, min_coverage=5                                  ║
║                                                                          ║
║ NOTIFY:                                                                  ║
║   powershell -Command "notify 'WritePaper RAG-Ingest: {N} Quellen'"     ║
║                                                                          ║
║ TAGS:                                                                    ║
║   type: research                                                         ║
║   op: WritePaper                                                         ║
║   chapter: {N}                                                           ║
║   chain-position: research                                               ║
╚══════════════════════════════════════════════════════════════════════════╝
```

## Verantwortlichkeit

**TUT (Claude):**
- Scannt `/quellen/` Ordner nach allen Quelldateien (PDF, LaTeX, MD, TXT)
- Extrahiert BibTeX-Metadaten aus jeder Datei
- Ruft `mcp__cleancoder__research_ingest()` auf → SOURCES Collection
- Generiert `output/references.bib` (vollständige BibTeX-Bibliographie)
- Analysiert Coverage mit `mcp__cleancoder__research_gaps()`
- Initialisiert Budget-Tracking basierend auf Difficulty
- Aktualisiert `_manifest.md` und `session-state.json` mit Ingest-Ergebnissen

**TUT NICHT (Claude):**
- Neue Quellen suchen oder herunterladen (→ `/_R_WP_discovery`)
- Lücken aktiv füllen (→ `/_R_WP_chapterGap`)
- Quellen bewerten oder filtern
- SOURCES Collection modifizieren nach Ingest

**ESKALATION (User):**
- `/quellen/` Ordner fehlt oder ist leer
- MCP-Server nicht erreichbar
- Alle Dateien fehlgeschlagen (0 sources ingested)
- Budget-Limits bereits überschritten vor Start

## Ablauf

### Schritt 0: Inputs lesen

**Ziel:** Kontext und Parameter für Ingest sammeln

**Aktionen:**
1. Lies `_manifest.md` → Aktuelles Kapitel, Phase, Projekt-Pfad
2. Lies `session-state.json` → Difficulty, `research_budget_remaining`
3. Lies `config/project.yaml` → `research_questions` (Array)
4. Scanne `quellen/` Ordner (rekursiv):
   - Sammle alle Dateien: `*.pdf`, `*.md`, `*.txt`, `*.tex`, `*.latex`
   - Erstelle Liste: `[{path, size, type}, ...]`

**Erfolgskriterium:**
- Mindestens 1 Datei in `quellen/` gefunden
- `research_questions` ist nicht leer
- `difficulty` ist gesetzt (easy/normal/hard)

---

### Schritt 1: Quellen-Scan & Validierung

**Ziel:** Quellen zählen und Coverage-Anforderung prüfen

**Aktionen:**
1. Zähle Dateien nach Typ:
   - PDF: `{count}`
   - Markdown: `{count}`
   - LaTeX: `{count}`
   - Text: `{count}`
2. Prüfe Mindestanforderung basierend auf `difficulty`:
   - `easy`: min. 5 Quellen
   - `normal`: min. 10 Quellen
   - `hard`: min. 20 Quellen
3. Falls unter Minimum:
   - **WARNUNG** in Konsole ausgeben (nicht STOP)
   - Notiere in `session-state.json`: `initial_source_warning: true`
   - Grund: `/_R_WP_discovery` kann Lücken später füllen

**Erfolgskriterium:**
- Quellen gezählt und klassifiziert
- Warnung ausgegeben falls unter Minimum
- Keine BLOCKADE (Ingest läuft trotzdem)

---

### Schritt 2: MCP Research Ingest

**Ziel:** Alle Quellen in SOURCES Collection ingestieren

**Aktionen:**
1. Rufe `mcp__cleancoder__research_ingest()` auf:
   ```python
   result = await mcp__cleancoder__research_ingest(
       project_path="{current_project_path}",
       source_folder="quellen",
       options={
           "chunk_strategy": "hybrid",
           "chunk_size": 512,
           "overlap_percent": 0.175,
           "enable_nlp": True,
           "generate_bibtex": True
       }
   )
   ```
2. Tracke Ergebnis:
   - `sources_ingested`: Anzahl erfolgreich ingestierter Dateien
   - `chunks_created`: Gesamtzahl erstellter Chunks
   - `bibtex_entries`: Liste der BibTeX-Keys
   - `duration_seconds`: Zeit für Ingest
   - `errors`: Liste fehlgeschlagener Dateien
3. Bei Fehlern:
   - Logge in `logs/research-errors.log`:
     ```
     [2026-02-08 14:30] INGEST FAILED: {file_path}
     Error: {error_message}
     ```
   - **Fahre fort** mit nächsten Dateien (kein STOP)
4. Speichere `output/references.bib` (wird von MCP generiert)

**Erfolgskriterium:**
- `sources_ingested > 0` (mindestens 1 Quelle erfolgreich)
- `output/references.bib` existiert
- Fehler dokumentiert aber nicht blockierend

---

### Schritt 3: Keyword-Extraktion

**Ziel:** Keywords aus Research Questions extrahieren für Gap-Analyse

**Aktionen:**
1. Pro `research_question` in `config/project.yaml`:
   ```python
   keywords = await mcp__cleancoder__extract_keywords(
       text=question,
       count=8
   )
   ```
2. Sammle alle Keywords in Liste:
   ```json
   {
     "question_1": ["keyword1", "keyword2", ...],
     "question_2": ["keyword3", "keyword4", ...],
     ...
   }
   ```
3. Speichere in `session-state.json`:
   ```json
   {
     "research_keywords": {
       "question_1": [...],
       "question_2": [...]
     }
   }
   ```

**Erfolgskriterium:**
- Für jede Research Question mindestens 5 Keywords extrahiert
- Keywords gespeichert in `session-state.json`

---

### Schritt 4: Gap-Analyse

**Ziel:** Coverage pro Research Question analysieren

**Aktionen:**
1. Bestimme `min_coverage` basierend auf `difficulty`:
   - `easy`: 2 Chunks pro Frage
   - `normal`: 3 Chunks pro Frage
   - `hard`: 5 Chunks pro Frage
2. Rufe `mcp__cleancoder__research_gaps()` auf:
   ```python
   gaps = await mcp__cleancoder__research_gaps(
       project_path="{current_project_path}",
       research_questions=[...],
       options={
           "min_coverage": {min_coverage},
           "suggest_sources": True,
           "check_bibliography": True
       }
   )
   ```
3. Speichere Ergebnis in `output/research-gaps-initial.json`:
   ```json
   {
     "analysis_date": "2026-02-08",
     "total_sources": 15,
     "total_chunks": 342,
     "questions_analyzed": 3,
     "coverage": {
       "question_1": "FULL",
       "question_2": "PARTIAL",
       "question_3": "MINIMAL"
     },
     "topics": [
       {
         "question": "...",
         "coverage": "PARTIAL",
         "chunks_found": 8,
         "sources": ["Martin2008", "Fowler2018"],
         "suggestions": ["Search for: refactoring patterns"]
       }
     ],
     "action_required": [
       "Frage 3 hat nur 1 Chunk - weitere Quellen nötig"
     ]
   }
   ```
4. Berechne `initial_coverage_score`:
   - FULL: 3 Punkte
   - PARTIAL: 2 Punkte
   - MINIMAL: 1 Punkt
   - MISSING: 0 Punkte
   - Score = Summe / (Anzahl Fragen * 3) → 0.0 - 1.0

**Erfolgskriterium:**
- `output/research-gaps-initial.json` existiert
- Coverage für jede Research Question bekannt
- `initial_coverage_score` berechnet

---

### Schritt 5: Budget-Tracking initialisieren

**Ziel:** MCP-Call-Budget setzen für Gap-Loop

**Aktionen:**
1. Setze `research_budget_initial` basierend auf `difficulty`:
   - `easy`: 8 MCP-Calls
   - `normal`: 15 MCP-Calls
   - `hard`: 30 MCP-Calls
2. Berechne bereits verbrauchte Calls in diesem Command:
   - 1x `research_ingest`
   - 1x `research_gaps`
   - Nx `extract_keywords` (N = Anzahl Research Questions)
   - Summe: `calls_used = 2 + N`
3. Setze `research_budget_remaining`:
   ```
   research_budget_remaining = research_budget_initial - calls_used
   ```
4. Speichere in `session-state.json`:
   ```json
   {
     "research_budget_initial": 15,
     "research_budget_remaining": 12,
     "research_calls_used": 3
   }
   ```

**Erfolgskriterium:**
- `research_budget_remaining > 0`
- Budget korrekt berechnet und gespeichert

---

### Schritt 6: State aktualisieren

**Ziel:** Manifest und Session-State mit Ingest-Ergebnissen aktualisieren

**Aktionen:**
1. Update `_manifest.md`:
   ```markdown
   ## Research Status
   - **Sources Count:** 15
   - **Chunks Created:** 342
   - **Coverage Score:** 0.73
   - **Next Step:** discovery
   - **Budget Remaining:** 12 MCP-Calls
   ```
2. Update `session-state.json`:
   ```json
   {
     "last_command": "_R_WP_research",
     "sources_ingested": 15,
     "chunks_created": 342,
     "initial_gaps": {
       "total": 3,
       "full": 1,
       "partial": 2,
       "minimal": 0
     },
     "research_budget_remaining": 12,
     "coverage_status": "PARTIAL",
     "next_step": "discovery"
   }
   ```
3. **NOTIFY:**
   ```powershell
   powershell -Command "notify 'WritePaper RAG-Ingest: 15 Quellen, 342 Chunks, Coverage 73%'"
   ```

**Erfolgskriterium:**
- `_manifest.md` und `session-state.json` aktualisiert
- `next_step = "discovery"` gesetzt
- Notification gesendet

---

## Output-Format

### output/research-gaps-initial.json

**Zweck:** Initiale Coverage-Analyse für Gap-Loop

**Schema:**
```json
{
  "analysis_date": "2026-02-08T14:30:00Z",
  "project_path": "/path/to/project",
  "total_sources": 15,
  "total_chunks": 342,
  "questions_analyzed": 3,
  "coverage_score": 0.73,
  "coverage": {
    "question_1": "FULL",
    "question_2": "PARTIAL",
    "question_3": "PARTIAL"
  },
  "topics": [
    {
      "question": "What are the principles of clean code?",
      "keywords": ["clean code", "principles", "readability"],
      "coverage": "FULL",
      "chunks_found": 12,
      "sources": ["Martin2008", "Fowler2018", "McConnell2004"],
      "suggestions": []
    },
    {
      "question": "How does TDD improve software quality?",
      "keywords": ["TDD", "test-driven", "quality"],
      "coverage": "PARTIAL",
      "chunks_found": 8,
      "sources": ["Beck2002", "Martin2008"],
      "suggestions": [
        "Search for: test-driven development case studies",
        "Search for: TDD empirical studies"
      ]
    },
    {
      "question": "What are refactoring patterns?",
      "keywords": ["refactoring", "patterns", "code smells"],
      "coverage": "PARTIAL",
      "chunks_found": 5,
      "sources": ["Fowler2018"],
      "suggestions": [
        "Search for: refactoring catalog",
        "Search for: code smell detection"
      ]
    }
  ],
  "summary": {
    "full_coverage": 1,
    "partial_coverage": 2,
    "minimal_coverage": 0,
    "missing": 0
  },
  "action_required": [
    "Frage 2 hat nur 8 Chunks (min: 10 für normal) - weitere Quellen empfohlen",
    "Frage 3 hat nur 5 Chunks (min: 10 für normal) - weitere Quellen empfohlen"
  ]
}
```

---

### output/references.bib

**Zweck:** Vollständige BibTeX-Bibliographie (wird von MCP generiert)

**Format:**
```bibtex
@book{Martin2008,
  author = {Robert C. Martin},
  title = {Clean Code: A Handbook of Agile Software Craftsmanship},
  year = {2008},
  publisher = {Prentice Hall},
  isbn = {978-0132350884}
}

@book{Fowler2018,
  author = {Martin Fowler},
  title = {Refactoring: Improving the Design of Existing Code},
  year = {2018},
  edition = {2nd},
  publisher = {Addison-Wesley},
  isbn = {978-0134757599}
}
```

---

## Qualitätskriterien

### Vollständigkeit
- [ ] Alle Dateien in `/quellen/` gescannt
- [ ] `output/references.bib` enthält alle BibTeX-Einträge
- [ ] `output/research-gaps-initial.json` enthält Coverage für alle Research Questions
- [ ] `_manifest.md` und `session-state.json` vollständig aktualisiert

### Korrektheit
- [ ] `sources_ingested` == Anzahl erfolgreich ingestierter Dateien
- [ ] `chunks_created` == Summe aller Chunks aus MCP-Response
- [ ] `coverage_score` korrekt berechnet (0.0 - 1.0)
- [ ] `research_budget_remaining` = initial - verbrauchte Calls

### Robustheit
- [ ] Fehler bei einzelnen Dateien stoppt nicht gesamten Ingest
- [ ] `logs/research-errors.log` enthält Details zu fehlgeschlagenen Dateien
- [ ] Warnung bei zu wenig Quellen (nicht STOP)
- [ ] Budget-Tracking verhindert Überschreitung in späteren Commands

### Performance
- [ ] MCP-Calls parallelisiert wo möglich (z.B. Keyword-Extraktion)
- [ ] Keine redundanten Ingest-Calls (gleiche Datei nicht mehrfach)
- [ ] `chunk_strategy=hybrid` optimiert für 512-Token-Chunks

---

## NOTIFY

**Success:**
```powershell
powershell -Command "notify 'WritePaper RAG-Ingest: 15 Quellen, 342 Chunks, Coverage 73%'"
```

**Warning:**
```powershell
powershell -Command "notify 'WritePaper RAG-Ingest: Nur 7/10 Quellen (normal) - siehe discovery'"
```

**Error:**
```powershell
powershell -Command "notify 'WritePaper RAG-Ingest FAILED: 0 Quellen ingestiert - siehe Logs'"
```

---

## Hinweise

### MCP-Bremse
- **KRITISCH:** Dieser Command ist BLOCKING für alle Writing-Commands
- Ohne SOURCES Collection können `/_R_WP_chapterWrite` und `/_R_WP_chapterGap` nicht arbeiten
- Budget-Tracking verhindert unkontrollierte MCP-Calls im Gap-Loop

### Difficulty-Scaling
- `easy`: 5-10 Quellen, min_coverage=2, Budget=8
- `normal`: 10-20 Quellen, min_coverage=3, Budget=15
- `hard`: 20-40 Quellen, min_coverage=5, Budget=30

### Gap-Loop Integration
- `research` ist der EINSTIEG in den Gap-Loop
- Nach `research` folgt `discovery` (wenn Lücken erkannt)
- Loop-Bedingung: `research_budget_remaining > 0 && coverage_score < 0.9`
- Exit: `coverage_score >= 0.9` → `/_R_WP_chapterWrite`

### Error Handling
- Einzelne fehlgeschlagene Dateien → Log + Continue
- 0 Quellen ingestiert → ESKALATION (User muss `/quellen/` prüfen)
- MCP-Server nicht erreichbar → ESKALATION (User muss Server starten)
- Budget überschritten VOR Start → ESKALATION (Difficulty falsch?)
