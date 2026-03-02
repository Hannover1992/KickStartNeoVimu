# /_R_WP_discovery - Research Source Discovery

**STATUS:** v1.0.0 | 2026-02-08 | ACTIVE
**AUTOR:** OmniCommand System
**ZWECK:** Aktive Quellensuche basierend auf Gap-Analyse, Web-Recherche, MCP-Ingest

---

```
╔══════════════════════════════════════════════════════════════════════════╗
║ VERTRAG: /_R_WP_discovery                                               ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ ACTOR: SOURCE DISCOVERER                                                 ║
║   TUT:                                                                   ║
║     - Gap-Keywords aus assess lesen                                      ║
║     - Web-Search durchfuehren (Arxiv, Google Scholar)                    ║
║     - MCP summarize fuer Preview-Qualitaet                               ║
║     - Neue Quellen in /quellen/ speichern                                ║
║     - MCP research_ingest fuer neue Quellen                              ║
║   NICHT:                                                                 ║
║     - Bestehende Quellen re-ingestieren (→ research)                     ║
║     - Entscheiden ob Gap geschlossen (→ chapterGap)                      ║
║                                                                          ║
║ LIEST (Input) - PFLICHT:                                                 ║
║   1. _manifest.md                                                        ║
║   2. session-state.json                                                  ║
║   3. output/research-gaps-initial.json                                   ║
║   4. output/references.bib                                               ║
║                                                                          ║
║ SCHREIBT (Output) - PFLICHT:                                             ║
║   1. output/source-suggestions.md (Web-Suche-Queries)                    ║
║   2. output/source-previews.md (summarize Output fuer Top-10 Chunks)     ║
║   3. _manifest.md (UPDATE: missing_topics_count, next_step=chapterModel) ║
║   4. session-state.json (UPDATE: discovery_complete=true)                ║
║                                                                          ║
║ POSITION:                                                                ║
║   TYPE: LOOP                                                             ║
║   LOOP-CONTEXT:                                                          ║
║     LOOP-NAME: Gap-Loop                                                  ║
║     LOOP-LEVEL: MIDDLE                                                   ║
║     ITERATION-VARIABLE: gap_research_count                               ║
║     MAX-ITERATIONS: extern kontrolliert von /_R_WP_chapterGap (max 3)   ║
║   ENTRY:                                                                 ║
║     NORMAL: /_R_WP_research → THIS                                      ║
║   EXIT:                                                                  ║
║     NORMAL: THIS → /_R_WP_chapterModel                                  ║
║   PHASE: Knowledge                                                      ║
║   CHAIN: [research] → [discovery] → [chapterModel]                      ║
║                                                                          ║
║ MCP-BREMSE:                                                              ║
║   Tools: mcp__cleancoder__research_gaps,                                 ║
║          mcp__cleancoder__research_ingest,                                ║
║          mcp__cleancoder__extract_keywords,                               ║
║          mcp__cleancoder__summarize                                       ║
║   Call-Limits: easy=10, normal=18, hard=35                               ║
║   OPTIONAL: Command kann uebersprungen werden                            ║
║                                                                          ║
║ SCHWIERIGKEIT:                                                           ║
║   easy:   min_coverage=2 (PARTIAL ok)                                    ║
║   normal: min_coverage=3 (Standard)                                      ║
║   hard:   min_coverage=5 (FULL-Coverage erforderlich)                    ║
║                                                                          ║
║ NOTIFY:                                                                  ║
║   powershell -Command "notify 'WritePaper Source Discovery done'"        ║
║                                                                          ║
║ TAGS:                                                                    ║
║   type: discovery                                                        ║
║   op: WritePaper                                                         ║
║   chapter: {N}                                                           ║
║   chain-position: discovery                                              ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## VERANTWORTLICHKEIT

**DU TUST (TUT):**
- Gap-Topics aus `output/research-gaps-initial.json` analysieren
- Keywords extrahieren via `mcp__cleancoder__extract_keywords()`
- Web-Search durchfuehren (Arxiv, Google Scholar, IEEE, ACM)
- Previews generieren via `mcp__cleancoder__summarize()`
- Relevante Quellen nach `quellen/discovered/` downloaden
- Neue Quellen ingestieren via `mcp__cleancoder__research_ingest()`
- Output-Dateien schreiben: `source-suggestions.md`, `source-previews.md`
- Manifest + Session-State aktualisieren

**DU TUST NICHT (NICHT):**
- Bestehende Quellen erneut ingestieren (das macht `/_R_WP_research`)
- Entscheiden ob Gap endgueltig geschlossen (das macht `/_R_WP_chapterGap`)
- Quellen manuell bewerten ohne MCP-Tools
- Discovery wiederholen wenn bereits `discovery_complete=true`

**ESKALATION:**
- **Web-Search API Limit:** Reduziere auf Top-3 pro Topic statt Top-5
- **Download-Fehler:** Markiere Source als "pending_manual" in `source-previews.md`
- **MCP-Budget ueberschritten:** Breche Discovery ab, setze `discovery_complete=false`, empfehle manuelle Recherche

---

## ABLAUF

### Schritt 0: Inputs lesen
```markdown
**WAS:** Lade alle Pflicht-Inputs
**WIE:**
1. Lies `_manifest.md` → `current_chapter`, `phase`, `next_step`
2. Lies `session-state.json` → `difficulty`, `research_budget_remaining`, `discovery_complete`
3. Lies `output/research-gaps-initial.json` → Gap-Topics mit Coverage-Level
4. Lies `output/references.bib` → Existierende Quellen-Keys

**PRUEFUNG:**
- Falls `discovery_complete=true` → STOP mit Meldung "Discovery bereits abgeschlossen"
- Falls `research-gaps-initial.json` fehlt → FEHLER, empfehle `/_R_WP_assess` zuerst
```

### Schritt 1: Gap-Analyse auswerten
```markdown
**WAS:** Identifiziere Topics mit unzureichender Coverage
**WIE:**
1. Bestimme `min_coverage` aus `difficulty`:
   - easy: 2 Chunks
   - normal: 3 Chunks
   - hard: 5 Chunks
2. Filtere Topics mit `chunks_found < min_coverage`
3. Sortiere nach Prioritaet: MISSING (0) > MINIMAL (1) > PARTIAL (2+)
4. Falls ALLE Topics >= `min_coverage`:
   - Setze `discovery_complete=true` in `session-state.json`
   - Setze `next_step=chapterModel` in `_manifest.md`
   - AUSGABE: "Alle Topics ausreichend abgedeckt. Discovery uebersprungen."
   - → STOP

**PRUEFUNG:**
- Mindestens 1 Gap-Topic vorhanden
- Sortierung korrekt (MISSING first)
```

### Schritt 2: Search-Queries generieren
```markdown
**WAS:** Erstelle praezise Suchbegriffe fuer fehlende Topics
**WIE:**
1. Pro Gap-Topic:
   - Extrahiere Keywords via `mcp__cleancoder__extract_keywords(text=question, count=5)`
   - Generiere 2-3 Suchbegriffe aus Keywords + Research-Question
   - Verwende akademische Operatoren: "empirical study", "systematic review", "meta-analysis"
2. Schreibe `output/source-suggestions.md`:
   - Pro Topic: Question, Keywords, 2-3 Suchbegriffe
   - Format: Markdown mit klarer Struktur

**BEISPIEL:**
## Gap: Clean Code Principles (Coverage: 1/3)
**Keywords:** clean code, software craftsmanship, SOLID principles
**Suchbegriffe:**
1. "clean code principles software engineering"
2. "SOLID principles empirical study"
3. "Robert C. Martin clean code impact"

**PRUEFUNG:**
- Jedes Gap-Topic hat 2-3 Suchbegriffe
- Keywords sind relevant und praezise
```

### Schritt 3: Web-Recherche
```markdown
**WAS:** Fuehre Web-Search fuer jeden Suchbegriff durch
**WIE:**
1. Pro Gap-Topic (max. 5 Topics parallel):
   - Fuehre `WebSearch()` fuer jeden Suchbegriff aus
   - Targets: Arxiv, Google Scholar, IEEE Xplore, ACM Digital Library
   - Sammle Top-5 Ergebnisse pro Suchbegriff
2. Duplikats-Check gegen `references.bib`:
   - Vergleiche Titel + Autor + Jahr
   - Markiere Duplikate als "EXISTING"
3. Tracke Ergebnisse:
   - Total gefunden, Unique, Duplikate, Relevante

**LIMITS:**
- easy: max. 10 Web-Searches
- normal: max. 18 Web-Searches
- hard: max. 35 Web-Searches

**PRUEFUNG:**
- Mindestens 3 neue Quellen pro Gap-Topic gefunden
- Keine offensichtlichen Duplikate
```

### Schritt 4: Quellen-Preview
```markdown
**WAS:** Qualitaets-Preview fuer Top-Ergebnisse generieren
**WIE:**
1. Pro Top-Ergebnis (max. 10):
   - Lade Abstract/Zusammenfassung via `WebFetch()`
   - Generiere Summary via `mcp__cleancoder__summarize(text=abstract, max_length=150)`
   - Bewerte Relevanz (heuristisch):
     - RELEVANT (>0.7): Keywords matchen + akademische Quelle
     - MARGINAL (0.4-0.7): Teilweise relevant
     - IRRELEVANT (<0.4): Kein Keyword-Match
2. Schreibe `output/source-previews.md`:
   - Pro Topic gruppiert
   - Format: Titel, Relevanz, Summary, Status

**BEISPIEL:**
## Topic: Clean Code Principles

### [1] Martin2008 - Clean Code: A Handbook
**Relevanz:** 0.92 (RELEVANT)
**Summary:** Definiert 5 Kern-Prinzipien: Bedeutungsvolle Namen, kleine Funktionen...
**Status:** PENDING_INGEST

**PRUEFUNG:**
- Alle RELEVANT-Quellen haben Summary
- Relevanz-Score nachvollziehbar
```

### Schritt 5: Neue Quellen ingestieren
```markdown
**WAS:** RELEVANT-Quellen downloaden und in RAG ingestieren
**WIE:**
1. Erstelle `quellen/discovered/` falls nicht vorhanden
2. Pro RELEVANT-Quelle:
   - Download nach `quellen/discovered/{BibtexKey}.pdf` (falls verfuegbar)
   - Falls kein PDF: Speichere Abstract als `.txt`
3. Rufe `mcp__cleancoder__research_ingest()` auf:
   - `project_path` aus `_manifest.md`
   - `source_folder="quellen"`
   - `options={chunk_strategy: "hybrid", chunk_size: 512}`
4. Tracke Ergebnisse:
   - `new_sources_count`, `new_chunks_created`, `sources_failed`
5. Aktualisiere `output/references.bib`:
   - Fuege neue BibTeX-Entries hinzu
   - Markiere mit `note = {discovered via /_R_WP_discovery}`

**FEHLERBEHANDLUNG:**
- Download-Fehler: Markiere als "pending_manual" in `source-previews.md`
- Ingest-Fehler: Logge in `session-state.json` unter `errors[]`

**PRUEFUNG:**
- Mindestens 1 Quelle erfolgreich ingestiert
- `references.bib` aktualisiert
```

### Schritt 6: State aktualisieren
```markdown
**WAS:** Manifest + Session-State mit Discovery-Ergebnissen aktualisieren
**WIE:**
1. `_manifest.md` UPDATE:
   - `missing_topics_count`: Anzahl verbleibender Gaps
   - `new_sources_discovered`: Anzahl neu ingestierter Quellen
   - `next_step`: "chapterModel"
2. `session-state.json` UPDATE:
   - `discovery_complete`: true
   - `new_sources`: Array mit BibtexKeys
   - `research_budget_remaining`: Reduziere um verbrauchte MCP-Calls
   - `gap_research_count`: Inkrementiere

**BEISPIEL:**
{
  "discovery_complete": true,
  "new_sources": ["Martin2008", "Beck2003", "Fowler1999"],
  "research_budget_remaining": 25,
  "gap_research_count": 1
}

**PRUEFUNG:**
- `discovery_complete=true` gesetzt
- `next_step=chapterModel` in Manifest
```

---

## OUTPUT-FORMAT

### output/source-suggestions.md
```markdown
# Source Discovery Suggestions

**Generiert:** 2026-02-08 15:32
**Kapitel:** 3 - Methodology
**Gap-Topics:** 3

---

## Gap: Clean Code Principles (Coverage: 1/3 - MINIMAL)
**Keywords:** clean code, software craftsmanship, SOLID principles, naming conventions
**Suchbegriffe:**
1. "clean code principles software engineering empirical"
2. "SOLID principles impact code quality study"
3. "Robert C. Martin clean code maintainability"

**Ziel:** 2 zusaetzliche Quellen (Target: 3 total)

---

## Gap: Test-Driven Development (Coverage: 0/3 - MISSING)
**Keywords:** TDD, test-driven development, red-green-refactor, unit testing
**Suchbegriffe:**
1. "TDD effectiveness empirical evidence systematic review"
2. "test-driven development impact software quality meta-analysis"
3. "TDD adoption barriers case study"

**Ziel:** 3 Quellen (Target: 3 total)

---

## Gap: Refactoring Strategies (Coverage: 2/3 - PARTIAL)
**Keywords:** refactoring, code smells, technical debt, design patterns
**Suchbegriffe:**
1. "refactoring strategies empirical comparison"
2. "code smell detection automated tools survey"
3. "technical debt refactoring ROI study"

**Ziel:** 1 zusaetzliche Quelle (Target: 3 total)
```

### output/source-previews.md
```markdown
# Source Previews - Discovery Results

**Generiert:** 2026-02-08 15:45
**Kapitel:** 3 - Methodology
**Neue Quellen:** 7 (5 RELEVANT, 2 MARGINAL)

---

## Topic: Clean Code Principles

### [1] Martin2008 - Clean Code: A Handbook of Agile Software Craftsmanship
**Relevanz:** 0.92 (RELEVANT)
**Quelle:** ACM Digital Library
**Summary:** Definiert 5 Kern-Prinzipien fuer Clean Code: Bedeutungsvolle Namen, kleine Funktionen, minimale Parameter, keine Kommentare als Ersatz fuer schlechten Code, testbarer Code. Basiert auf 40 Jahren Erfahrung in Software-Entwicklung.
**Status:** INGESTIERT (15 Chunks)
**BibTeX:** `Martin2008`

### [2] Shore2007 - The Art of Agile Development
**Relevanz:** 0.78 (RELEVANT)
**Quelle:** Google Scholar
**Summary:** Kapitel zu Code-Qualitaet und Clean Code Praktiken in agilen Teams. Fokus auf Pair Programming und Refactoring als Quality Gates.
**Status:** INGESTIERT (8 Chunks)
**BibTeX:** `Shore2007`

---

## Topic: Test-Driven Development

### [3] Beck2003 - Test-Driven Development: By Example
**Relevanz:** 0.95 (RELEVANT)
**Quelle:** IEEE Xplore
**Summary:** Erklaert TDD-Zyklus (Red-Green-Refactor) mit praktischen Beispielen. Zeigt wie TDD Design verbessert und Regression Prevention ermoeglicht.
**Status:** INGESTIERT (22 Chunks)
**BibTeX:** `Beck2003`

### [4] Janzen2005 - Test-Driven Development: Concepts, Taxonomy, and Future Direction
**Relevanz:** 0.88 (RELEVANT)
**Quelle:** Arxiv
**Summary:** Systematisches Review von TDD-Studien. Identifiziert 4 Hauptvorteile und 3 Barrieren fuer Adoption.
**Status:** INGESTIERT (18 Chunks)
**BibTeX:** `Janzen2005`

### [5] George2003 - An Initial Investigation of Test Driven Development in Industry
**Relevanz:** 0.62 (MARGINAL)
**Quelle:** Google Scholar
**Summary:** Fallstudie mit 24 Entwicklern. Mixed Results fuer Produktivitaet.
**Status:** PENDING_MANUAL (PDF nicht verfuegbar)
**BibTeX:** N/A

---

## Topic: Refactoring Strategies

### [6] Fowler1999 - Refactoring: Improving the Design of Existing Code
**Relevanz:** 0.94 (RELEVANT)
**Quelle:** ACM Digital Library
**Summary:** Katalog von 72 Refactoring-Patterns mit Before/After Beispielen. Definiert Code Smells und systematische Refactoring-Strategien.
**Status:** INGESTIERT (28 Chunks)
**BibTeX:** `Fowler1999`

### [7] Mens2004 - A Survey of Software Refactoring
**Relevanz:** 0.71 (MARGINAL)
**Quelle:** IEEE Xplore
**Summary:** Ueberblick ueber Refactoring-Tools und Techniken. Fokus auf automatisierte Ansaetze.
**Status:** SKIPPED (zu tool-fokussiert)
**BibTeX:** N/A

---

## ZUSAMMENFASSUNG

**Total gefunden:** 12 Quellen
**Duplikate (bereits in Bibliothek):** 3
**Neue Quellen:** 9
**RELEVANT (>0.7):** 5 Quellen → INGESTIERT
**MARGINAL (0.4-0.7):** 2 Quellen → PENDING_MANUAL
**IRRELEVANT (<0.4):** 2 Quellen → SKIPPED

**Neue Chunks:** 91
**Verbleibende Gaps:** 0 (alle Topics jetzt >= min_coverage)

**MCP-Calls verbraucht:** 17/18 (Budget: normal)
```

---

## QUALITAETSKRITERIEN

**ERFOLG, wenn:**
1. Alle Gap-Topics haben Web-Recherche erhalten
2. Mindestens 3 neue Quellen RELEVANT bewertet
3. Mindestens 1 Quelle erfolgreich ingestiert
4. `source-suggestions.md` + `source-previews.md` existieren
5. `discovery_complete=true` in `session-state.json`
6. `next_step=chapterModel` in `_manifest.md`
7. MCP-Call-Limit nicht ueberschritten

**FEHLER, wenn:**
1. Gap-Topics ohne Suchbegriffe bleiben
2. Web-Search komplett fehlschlaegt (0 Ergebnisse)
3. Keine einzige Quelle als RELEVANT bewertet
4. Alle Ingests fehlschlagen
5. MCP-Budget ueberschritten ohne Abbruch

**WARNUNGEN:**
1. Download-Fehler bei >50% der RELEVANT-Quellen → Empfehle manuelle Recherche
2. Duplikats-Rate >70% → Empfehle spezifischere Suchbegriffe
3. Kein Gap geschlossen nach Discovery → Empfehle `/_R_WP_chapterGap` skip

---

## NOTIFY

Nach erfolgreichem Abschluss:
```powershell
powershell -Command "notify 'WritePaper Source Discovery done'"
```

**FEHLSCHLAG:**
```powershell
powershell -Command "notify 'WritePaper Source Discovery FAILED'"
```

---

**VERSION:** v1.0.0
**CHANGELOG:**
- 2026-02-08: Initiale Version, 6-Sektionen-Blueprint, LOOP-Position, MCP-Bremse integriert
