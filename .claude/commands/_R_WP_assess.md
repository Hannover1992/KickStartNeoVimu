# /_R_WP_assess - Chapter Knowledge Assessment

```yaml
status: active
version: 1.0.0
created: 2026-02-08
op: WritePaper
phase: Knowledge
type: assess
chain_position: assess
difficulty_scaling: true
mcp_critical: true
decision_command: true
```

---

```
╔══════════════════════════════════════════════════════════════════════════╗
║ VERTRAG: /_R_WP_assess                                                  ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ ACTOR: KNOWLEDGE ASSESSOR                                                ║
║   TUT:                                                                   ║
║     - Kapitel-Keywords aus Sections extrahieren (MCP extract_keywords)   ║
║     - RAG-Query pro Keyword (research_query / research_query_r2)        ║
║     - Coverage-Score pro Keyword + gesamt berechnen                     ║
║     - Gap-Topics identifizieren (Keywords < min_coverage)               ║
║     - Assessment-JSON generieren                                        ║
║   NICHT:                                                                 ║
║     - Neue Quellen suchen (→ discovery)                                  ║
║     - Luecken fuellen (→ research + discovery)                           ║
║     - Kapitel schreiben (→ write)                                        ║
║     - Wissens-Model aufbauen (→ chapterModel)                           ║
║                                                                          ║
║ LIEST (Input) - PFLICHT:                                                 ║
║   1. _manifest.md (current_chapter, phase, next_step)                    ║
║   2. session-state.json (difficulty, research_budget_remaining)          ║
║   3. output/chapter-structure.md (Sections fuer current_chapter)        ║
║   4. output/temperature-profile.json (temperature, exploration_level)   ║
║   5. config/project.yaml (research_questions)                           ║
║                                                                          ║
║ SCHREIBT (Output) - PFLICHT:                                             ║
║   1. output/assess/chapter-{N}-assessment.json (Keywords, Coverage)     ║
║   2. _manifest.md (UPDATE: coverage_score, next_step)                   ║
║   3. session-state.json (UPDATE: chapter_keywords, coverage_score)      ║
║                                                                          ║
║ POSITION:                                                                ║
║   TYPE: LINEAR                                                           ║
║   AFTER: /_R_WP_structure (erstes Kapitel)                               ║
║          /_R_WP_reflect (naechstes Kapitel nach Retry-Loop)              ║
║   BEFORE: /_R_WP_research (Gap erkannt, coverage < 0.85)                ║
║           /_R_WP_chapterModel (Coverage gut, >= 0.85)                    ║
║   PHASE: Knowledge                                                      ║
║   CHAIN: [structure|reflect] → [assess] → [research|chapterModel]      ║
║                                                                          ║
║ ENTSCHEIDET:                                                             ║
║   Decision-Table:                                                        ║
║   ┌────────────────────────────────────────┬──────────┬──────────────┐  ║
║   │ Bedingung                               │ Decision │ Next Step    │  ║
║   ├────────────────────────────────────────┼──────────┼──────────────┤  ║
║   │ coverage_score >= 0.85                  │ PASS     │ chapterModel │  ║
║   │ coverage_score < 0.85 AND budget > 0   │ GAP      │ research     │  ║
║   │ coverage_score < 0.85 AND budget == 0  │ FORCE    │ chapterModel │  ║
║   └────────────────────────────────────────┴──────────┴──────────────┘  ║
║                                                                          ║
║   ESKALATION:                                                            ║
║     IF gap_count >= MAX (extern: chapterGap max 3) →                    ║
║       ESKALIERE zu /_R_WP_chapterGap (uebergeordneter Controller)      ║
║     chapterGap entscheidet: GAP (weitere Iteration) oder FORCE (weiter) ║
║                                                                          ║
║ MCP-BREMSE:                                                              ║
║   Tools: mcp__cleancoder__extract_keywords,                              ║
║          mcp__cleancoder__research_query,                                ║
║          mcp__cleancoder__research_query_r2                              ║
║   Call-Limits: easy=10, normal=20, hard=40                               ║
║   Parameter:                                                             ║
║     extract_keywords: count={difficulty-based: 3|5|8}                    ║
║     research_query: limit=5                                              ║
║     research_query_r2: limit=5, temperature={from profile},              ║
║                        covered_penalty=0.7, exclusion_threshold=0.85     ║
║   KRITISCH: OPTIONAL (Gap kann 0 sein → Skip zu chapterModel)          ║
║                                                                          ║
║ SCHWIERIGKEIT:                                                           ║
║   easy:   3 Keywords/Section, min_coverage=2, max 10 MCP-Calls         ║
║   normal: 5 Keywords/Section, min_coverage=3, max 20 MCP-Calls         ║
║   hard:   8 Keywords/Section, min_coverage=5, max 40 MCP-Calls         ║
║                                                                          ║
║ NOTIFY:                                                                  ║
║   powershell -Command "notify 'WritePaper Kapitel {N} Assessment:       ║
║   Coverage {X}%'"                                                        ║
║                                                                          ║
║ TAGS:                                                                    ║
║   type: assess                                                           ║
║   op: WritePaper                                                         ║
║   chapter: {N}                                                           ║
║   chain-position: assess                                                 ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

**TUT (Claude):**
- Liest chapter-structure.md fuer Sections des aktuellen Kapitels
- Extrahiert Keywords pro Section via `mcp__cleancoder__extract_keywords()`
- Fuehrt RAG-Query pro Keyword durch:
  - Kapitel 1: `mcp__cleancoder__research_query()` (nur SOURCES)
  - Kapitel 2+: `mcp__cleancoder__research_query_r2()` (SOURCES - COVERED - EXCLUSION)
- Berechnet Coverage-Score pro Keyword und aggregiert
- Identifiziert Gap-Topics (Keywords unter min_coverage Schwelle)
- Generiert chapter-{N}-assessment.json mit allen Ergebnissen
- Aktualisiert _manifest.md und session-state.json

**TUT NICHT (Claude):**
- Neue Quellen suchen oder herunterladen (→ `/_R_WP_discovery`)
- Luecken aktiv fuellen mit research_ingest (→ `/_R_WP_research`)
- Kapitel-Model erstellen (→ `/_R_WP_chapterModel`)
- Kapitel schreiben (→ `/_R_WP_write`)
- RAG-Collection modifizieren (nur lesen, nicht schreiben)

**ESKALATION:**
- MCP-Server nicht erreichbar → STOP + NOTIFY Error "MCP-Server offline"
- chapter-structure.md fehlt → STOP + empfehle `/_R_WP_structure` zuerst
- 0 Chunks fuer ALLE Keywords → WARNUNG + next_step=research (kompletter Gap)
- Budget bereits bei 0 vor Start → WARNUNG + next_step=chapterModel (Skip Assessment)

---

## Ablauf

### Schritt 0: Inputs lesen

**Ziel:** Kontext und Parameter fuer Assessment sammeln

**Aktionen:**
1. Lies `_manifest.md` → `current_chapter` (z.B. 1), `phase`, `next_step`
2. Lies `session-state.json` → `difficulty`, `research_budget_remaining`
3. Lies `output/chapter-structure.md` → Sections fuer Kapitel {N}
4. Lies `output/temperature-profile.json` → `temperature`, `exploration_level` fuer Kapitel {N}
5. Lies `config/project.yaml` → `research_questions` (Array)

**Validierung:**
- `next_step` muss `assess` sein → sonst FEHLER
- `chapter-structure.md` muss Sections fuer Kapitel {N} enthalten → sonst FEHLER
- `difficulty` muss gesetzt sein (easy/normal/hard) → sonst Default: normal

**Erfolgskriterium:**
- Alle 5 Input-Dateien gelesen
- Sections fuer aktuelles Kapitel extrahiert
- Difficulty und Temperature bestimmt

---

### Schritt 1: Keyword-Extraktion pro Section

**Ziel:** Keywords fuer RAG-Queries extrahieren

**Aktionen:**
1. Bestimme `keywords_per_section` aus `difficulty`:
   - easy: 3 Keywords
   - normal: 5 Keywords
   - hard: 8 Keywords
2. Pro Section im aktuellen Kapitel:
   ```python
   keywords = await mcp__cleancoder__extract_keywords(
       text="{section_title}: {section_description}",
       count={keywords_per_section}
   )
   ```
3. Sammle Keywords in strukturierter Liste:
   ```json
   {
     "section_1_1": {
       "title": "Motivation und Kontext",
       "keywords": [
         {"keyword": "software quality", "score": 0.89},
         {"keyword": "clean code", "score": 0.85},
         {"keyword": "maintainability", "score": 0.78}
       ]
     }
   }
   ```
4. Dedupliziere Keywords ueber Sections hinweg (gleicher Keyword → hoechster Score)
5. Aggregiere zu `chapter_keywords` Liste (unique Keywords)

**MCP-Budget-Tracking:**
- Pro Section: 1 extract_keywords Call
- Total: {sections_count} Calls verbraucht

**Erfolgskriterium:**
- Fuer jede Section mindestens 2 Keywords extrahiert
- Keine Duplikate in chapter_keywords
- MCP-Budget nicht ueberschritten

---

### Schritt 2: RAG-Query pro Keyword

**Ziel:** Vorhandenes Wissen pro Keyword pruefen

**Aktionen:**
1. Bestimme RAG-Query-Methode basierend auf Kapitel-Nummer:
   - **Kapitel 1:** `mcp__cleancoder__research_query()` (nur SOURCES Collection)
   - **Kapitel 2+:** `mcp__cleancoder__research_query_r2()` (3-Collection-Exclusion)
2. Pro unique Keyword:

   **Kapitel 1:**
   ```python
   results = await mcp__cleancoder__research_query(
       project_path="{project_path}",
       query_text=keyword,
       limit=5
   )
   ```

   **Kapitel 2+:**
   ```python
   results = await mcp__cleancoder__research_query_r2(
       project_path="{project_path}",
       query_text=keyword,
       limit=5,
       exclusion_threshold=0.85,
       covered_penalty=0.7,
       temperature={temperature_from_profile}
   )
   ```
3. Pro Keyword: Speichere Ergebnis mit Chunks, Scores, BibTeX-Keys
4. Fallback: Falls research_query_r2 fehlschlaegt → Retry mit research_query

**MCP-Budget-Tracking:**
- Pro Keyword: 1 research_query/research_query_r2 Call
- Total: {unique_keywords_count} Calls verbraucht
- Kumulativ: {sections_count} + {unique_keywords_count} Calls

**Erfolgskriterium:**
- Fuer jeden Keyword ein RAG-Result vorhanden (ggf. 0 Chunks)
- MCP-Budget-Limit nicht ueberschritten
- Fallback funktioniert bei r2-Fehlern

---

### Schritt 3: Coverage-Berechnung

**Ziel:** Coverage-Score pro Keyword und gesamt berechnen

**Aktionen:**
1. Bestimme `min_coverage` aus `difficulty`:
   - easy: 2 Chunks
   - normal: 3 Chunks
   - hard: 5 Chunks
2. Pro Keyword: Zaehle Chunks mit `score >= 0.7`:
   ```json
   {
     "keyword": "clean code",
     "chunks_found": 8,
     "chunks_relevant": 5,
     "coverage_status": "COVERED"
   }
   ```
3. Coverage-Status pro Keyword:
   - `chunks_relevant >= min_coverage` → "COVERED"
   - `chunks_relevant > 0 AND < min_coverage` → "PARTIAL"
   - `chunks_relevant == 0` → "MISSING"
4. Berechne `coverage_score`:
   ```
   coverage_score = (Keywords mit status "COVERED") / (Total Keywords)
   ```
   - Score Bereich: 0.0 - 1.0
5. Identifiziere Gap-Topics:
   - Alle Keywords mit Status "PARTIAL" oder "MISSING"
   - Sortiere nach Deficit: MISSING zuerst, dann PARTIAL

**Erfolgskriterium:**
- Jeder Keyword hat Coverage-Status
- coverage_score korrekt berechnet (0.0 - 1.0)
- Gap-Topics identifiziert und nach Deficit sortiert

---

### Schritt 4: Gap-Identifikation

**Ziel:** Gap-Topics strukturiert erfassen fuer nachgelagerte Commands

**Aktionen:**
1. Erstelle `gap_topics` Liste:
   ```json
   [
     {
       "keyword": "test-driven development",
       "section": "1.2",
       "chunks_found": 1,
       "min_required": 3,
       "deficit": 2,
       "status": "PARTIAL",
       "suggested_queries": [
         "TDD empirical studies software quality",
         "test-driven development impact maintainability"
       ]
     }
   ]
   ```
2. Pro Gap-Topic: Generiere 1-2 Suchvorschlaege (basierend auf Keyword + Research-Question Kontext)
3. Berechne `gap_severity`:
   - MISSING Keywords > 30% der Total: "SEVERE"
   - MISSING Keywords 10-30%: "MODERATE"
   - Nur PARTIAL Keywords: "MINOR"

**Erfolgskriterium:**
- Alle Gap-Topics mit Deficit und Suggestions
- Gap-Severity berechnet
- Suggestions sind praezise und akademisch

---

### Schritt 5: Decision-Logik

**Ziel:** Naechsten Schritt in der Pipeline bestimmen

**Aktionen:**
1. Evaluiere Coverage + Budget:

   | Bedingung | Decision | Next Step |
   |-----------|----------|-----------|
   | coverage_score >= 0.85 | COVERED | chapterModel |
   | coverage_score < 0.85 AND budget > 0 | GAP | research |
   | coverage_score < 0.85 AND budget == 0 | FORCE | chapterModel (WARNUNG) |

2. Setze `next_step` in Manifest + Session-State
3. Bei FORCE: WARNUNG ausgeben "Coverage niedrig ({X}%), aber Budget erschoepft. Weiter zu chapterModel."
4. Logge Decision + Begruendung

**Erfolgskriterium:**
- Decision korrekt basierend auf Tabelle
- next_step gesetzt
- WARNUNG bei FORCE

---

### Schritt 6: State aktualisieren

**Ziel:** Assessment-Ergebnisse persistent speichern

**Aktionen:**
1. Schreibe `output/assess/chapter-{N}-assessment.json`:
   ```json
   {
     "chapter": {N},
     "assessment_date": "2026-02-08T15:00:00Z",
     "difficulty": "normal",
     "temperature": 1.1,
     "sections_analyzed": 4,
     "keywords_total": 18,
     "keywords_covered": 14,
     "keywords_partial": 3,
     "keywords_missing": 1,
     "coverage_score": 0.78,
     "gap_severity": "MODERATE",
     "gap_topics": [...],
     "decision": "GAP",
     "next_step": "research",
     "mcp_calls_used": 22,
     "mcp_budget_remaining": 18,
     "sections": {
       "1.1": {
         "title": "Motivation und Kontext",
         "keywords": [...],
         "coverage": 0.85
       }
     }
   }
   ```
2. Update `_manifest.md`:
   ```markdown
   ## Assessment Status - Kapitel {N}
   - **Coverage Score:** 0.78
   - **Gap Severity:** MODERATE
   - **Decision:** GAP
   - **Next Step:** research
   - **Keywords:** 14/18 covered (78%)
   ```
3. Update `session-state.json`:
   ```json
   {
     "last_command": "_R_WP_assess",
     "chapter_keywords": [...],
     "coverage_score": 0.78,
     "gap_severity": "MODERATE",
     "assess_decision": "GAP",
     "next_step": "research"
   }
   ```
4. **NOTIFY:**
   ```powershell
   powershell -Command "notify 'WritePaper Kapitel {N} Assessment: Coverage 78%'"
   ```

**Erfolgskriterium:**
- assessment.json vollstaendig geschrieben
- _manifest.md und session-state.json aktualisiert
- NOTIFY gesendet

---

## Output-Format

### output/assess/chapter-{N}-assessment.json

**Zweck:** Vollstaendige Assessment-Daten fuer nachgelagerte Commands

**Schema:**
```json
{
  "chapter": 1,
  "assessment_date": "2026-02-08T15:00:00Z",
  "difficulty": "normal",
  "temperature": 1.2,
  "exploration_level": "high",
  "sections_analyzed": 4,
  "keywords_total": 18,
  "keywords_covered": 14,
  "keywords_partial": 3,
  "keywords_missing": 1,
  "coverage_score": 0.78,
  "min_coverage": 3,
  "gap_severity": "MODERATE",
  "gap_topics": [
    {
      "keyword": "test-driven development",
      "section": "1.2",
      "chunks_found": 1,
      "min_required": 3,
      "deficit": 2,
      "status": "PARTIAL",
      "suggested_queries": ["TDD empirical studies"]
    }
  ],
  "decision": "GAP",
  "next_step": "research",
  "mcp_calls_used": 22,
  "mcp_budget_remaining": 18,
  "sections": {
    "1.1": {
      "title": "Motivation und Kontext",
      "keywords": [
        {
          "keyword": "clean code",
          "score": 0.85,
          "chunks_found": 8,
          "chunks_relevant": 5,
          "coverage_status": "COVERED",
          "bibtex_keys": ["Martin2008", "Fowler2018"]
        }
      ],
      "section_coverage": 0.85
    }
  }
}
```

---

## Qualitaetskriterien

### Vollstaendigkeit
- [ ] Alle Sections im aktuellen Kapitel analysiert
- [ ] Alle Keywords extrahiert (>= 2 pro Section)
- [ ] RAG-Query fuer jeden Keyword ausgefuehrt
- [ ] Coverage-Score berechnet (0.0 - 1.0)
- [ ] Gap-Topics identifiziert mit Deficit + Suggestions
- [ ] assessment.json vollstaendig geschrieben
- [ ] _manifest.md und session-state.json aktualisiert

### Korrektheit
- [ ] coverage_score = (Keywords COVERED) / (Keywords Total)
- [ ] min_coverage basiert auf difficulty (2|3|5)
- [ ] Kapitel 1 nutzt research_query, Kapitel 2+ nutzt research_query_r2
- [ ] MCP-Namespace korrekt: `mcp__cleancoder__*`
- [ ] temperature aus temperature-profile.json (nicht hardcoded)
- [ ] Decision basiert auf Coverage + Budget (nicht willkuerlich)

### Robustheit
- [ ] Fallback: research_query_r2 Fehler → research_query
- [ ] Budget-Tracking: MCP-Calls werden gezaehlt und limitiert
- [ ] FORCE-Decision bei Budget=0: WARNUNG + Weiter zu chapterModel
- [ ] ESKALATION bei MCP-Server offline: STOP + NOTIFY Error
- [ ] Einzelne Keyword-Fehler stoppen nicht gesamtes Assessment

### Performance
- [ ] Keywords dedupliziert (keine doppelten RAG-Queries)
- [ ] MCP-Budget respektiert (easy=10, normal=20, hard=40)
- [ ] Nur relevante Chunks gezaehlt (score >= 0.7)

---

## NOTIFY

**Success:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Assessment: Coverage {X}%'"
```

**Warning (FORCE):**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Assessment: Coverage {X}% (Budget erschoepft)'"
```

**Error:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Assessment FAILED: MCP-Server offline'"
```

---

## Error Handling

- Einzelne extract_keywords Fehler → Log + Skip Section → Coverage-Score reduziert
- Einzelne research_query Fehler → Log + Keyword als MISSING → Gap-Topic
- research_query_r2 allgemein fehlerhaft → Fallback zu research_query (W8-Degradation)
- MCP-Server nicht erreichbar → BLOCKING STOP + ESKALATION zu User
- chapter-structure.md fehlt → BLOCKING STOP + empfehle /_R_WP_structure
- Budget bei 0 vor Start → WARNUNG + Skip zu chapterModel (kein Assessment)

---

## Hinweise

### MCP-Bremse
- **KRITISCH:** OPTIONAL — Falls Coverage bereits 100% ist (z.B. nach Discovery-Loop), kann assess uebersprungen werden
- Budget-Tracking ist kumulativ ueber Gap-Loop-Iterationen
- research_query_r2 verbraucht MEHR Budget (3 Collections) → Bei knappem Budget research_query nutzen

### Difficulty-Scaling
- Keywords/Section: easy=3, normal=5, hard=8
- min_coverage: easy=2, normal=3, hard=5
- MCP-Budget: easy=10, normal=20, hard=40

### Chain-Integration
- assess ist EINSTIEG in Knowledge-Phase (nach structure oder reflect)
- Bei COVERED (>= 0.85): Direkt zu chapterModel (research + discovery uebersprungen)
- Bei GAP (< 0.85): Zu research → discovery → chapterModel → chapterGap → ggf. zurueck
- LOOP-LEVEL: LINEAR (assess ist KEIN Loop-Controller, wird aber im Gap-Loop erneut aufgerufen)

### 3-Collection-Query (W8)
- Kapitel 1: NUR SOURCES Collection → research_query
- Kapitel 2+: SOURCES - COVERED - EXCLUSION → research_query_r2
- temperature aus output/temperature-profile.json (W7)
- covered_penalty=0.7 und exclusion_threshold=0.85 sind Defaults
