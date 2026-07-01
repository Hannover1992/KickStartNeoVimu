# /_WP_assess - Chapter Knowledge Assessment

```yaml
status: active
version: 1.2.1
created: 2026-02-08
updated: 2026-02-14
op: WritePaper
phase: Knowledge
type: building-block
chain_position: assess
difficulty_scaling: true
mcp_critical: true
decision_command: true
```

---

```
╔══════════════════════════════════════════════════════════════════════════╗
║ VERTRAG: /_WP_assess                                                  ║
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
║   AFTER: /_WP_structure (erstes Kapitel)                               ║
║          /_WP_reflect (naechstes Kapitel nach Retry-Loop)              ║
║   BEFORE: /_WP_research (Gap erkannt, coverage < 0.85)                ║
║           /_WP_chapterModel (Coverage gut, >= 0.85)                    ║
║   PHASE: Knowledge                                                      ║
║   CHAIN: [structure|reflect] → [assess] → [research|chapterModel]      ║
║                                                                          ║
║ ENTSCHEIDET (v1.2 - 2 Dimensionen):                                     ║
║   Decision-Table:                                                        ║
║   ┌──────────────────────┬──────────────────┬──────────┬───────────────┐ ║
║   │ internal_coverage    │ diversity_score   │ Decision │ Next Step     │ ║
║   ├──────────────────────┼──────────────────┼──────────┼───────────────┤ ║
║   │ >= 0.85              │ >= 0.5           │ PASS     │ chapterModel  │ ║
║   │ >= 0.85              │ < 0.5            │ DISC     │ discovery     │ ║
║   │ < 0.85               │ egal             │ GAP      │ research      │ ║
║   │ egal                 │ egal, budget=0   │ FORCE    │ chapterModel  │ ║
║   └──────────────────────┴──────────────────┴──────────┴───────────────┘ ║
║                                                                          ║
║   internal_coverage = (COVERED + INTERNAL_ONLY) / Total Keywords         ║
║     → Misst ob THEMEN abgedeckt sind (egal ob intern oder extern)        ║
║   diversity_score = Composite aus 4 Komponenten (Schritt 2.5):           ║
║     40% source_count_score (Anzahl unique externe Docs)                  ║
║     30% keyword_external_coverage (Keywords mit ext. Chunks)             ║
║     20% document_ratio (ext_docs / total_docs, NICHT Chunks!)            ║
║     10% recency_score (Anteil Quellen >= 2020)                           ║
║   DISC = Themen abgedeckt, aber EXTERNE akademische Quellen fehlen.      ║
║                                                                          ║
║   ESKALATION:                                                            ║
║     IF gap_count >= MAX (extern: chapterGap max 3) →                    ║
║       ESKALIERE zu /_WP_chapterGap (uebergeordneter Controller)      ║
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
- Neue Quellen suchen oder herunterladen (→ `/_WP_discovery`)
- Luecken aktiv fuellen mit research_ingest (→ `/_WP_research`)
- Kapitel-Model erstellen (→ `/_WP_chapterModel`)
- Kapitel schreiben (→ `/_WP_write`)
- RAG-Collection modifizieren (nur lesen, nicht schreiben)

**ESKALATION:**
- MCP-Server nicht erreichbar → STOP + NOTIFY Error "MCP-Server offline"
- chapter-structure.md fehlt → STOP + empfehle `/_WP_structure` zuerst
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

### Schritt 2.5: Source Diversity Analysis (NEU v1.1)

**Ziel:** Unterscheide interne Projektdokumentation von externen akademischen Quellen.
Interne Docs allein reichen NICHT fuer ein akademisches Paper.

**Warum:** Hauseigene Notizen (Specs, Models, READMEs) enthalten die richtigen Keywords,
liefern aber keine zitierbaren akademischen Referenzen. Ein Paper mit nur internen
Quellen ist wertlos.

**Aktionen:**
1. Sammle alle `source_documents` aus den RAG-Chunks (document_id, source_file, metadata)
2. Klassifiziere jedes Quelldokument:

   **EXTERNAL (akademisch zitierbar):**
   - Hat DOI, ISBN, oder arXiv-ID in Metadata
   - Hat Autor + Jahr im BibTeX-Key (z.B. "Lewis2020", "Chen2024")
   - Stammt von Paper-Download (PDF, akademisches Abstract)
   - Kommt aus anerkannter Quelle (Konferenz, Journal, Preprint-Server)

   **INTERNAL (Projektdokumentation):**
   - Dateiname enthaelt _Model, _Spec, _Wissen, README
   - Kein DOI/ISBN
   - BibTeX-Key ist auto-generiert (z.B. "WritePaper_Spec_md")
   - Frontmatter hat `phase:`, `op:`, `feature:` Tags (unsere Conventions)

3. Berechne Source-Diversity-Metriken (v1.2: Document-Level + Composite):
   ```json
   {
     "source_diversity": {
       "total_documents": 16,
       "external_documents": 10,
       "internal_documents": 6,
       "unique_external_sources": 10,
       "classification": {
         "WritePaper_Spec.md": "INTERNAL",
         "Lewis2020_RAG.md": "EXTERNAL"
       },
       "diversity_score": 0.72,
       "components": {
         "source_count_score": 1.0,
         "keyword_external_coverage": 0.6,
         "document_ratio": 0.625,
         "recency_score": 0.8
       }
     }
   }
   ```

4. Berechne `diversity_score` (v1.2: Composite, NICHT simple Chunk-Ratio):
   ```
   diversity_score = weighted_average(
     0.40 * source_count_score,           // Genug VERSCHIEDENE externe Quellen?
     0.30 * keyword_external_coverage,    // Decken externe die Keywords ab?
     0.20 * document_ratio,              // Dokument-Ratio (NICHT Chunk-Ratio!)
     0.10 * recency_score                // Sind Quellen aktuell?
   )
   ```

   **source_count_score** (40% Gewicht - wichtigste Komponente):
     >= 7 unique external docs → 1.0
     5-6 → 0.8
     3-4 → 0.6
     1-2 → 0.3
     0   → 0.0

   **keyword_external_coverage** (30% Gewicht):
     = (Keywords mit mindestens 1 externem Chunk) / (Total Keywords)
     Misst ob externe Quellen thematisch relevant sind

   **document_ratio** (20% Gewicht):
     = external_documents / total_documents
     Auf DOKUMENT-Ebene, nicht Chunk-Ebene (vermeidet Chunk-Flooding-Bias)

   **recency_score** (10% Gewicht):
     = (Externe Docs mit Jahr >= 2020) / (Total externe Docs)
     Bonus fuer aktuelle Quellen, 0.0 wenn keine externen Docs

   **HARD GATES (v1.2.1 - VOR dem Composite):**
   Zwei Minimum-Anforderungen muessen BEIDE erfuellt sein, sonst wird
   diversity_score auf max 0.40 gedeckelt (unter dem 0.5 Threshold):

   **Gate 1: Mindestens 3 verschiedene externe Quellen**
   ```
   unique_external_sources >= 3
   ```
   Verhindert Single-Source-Illusion: 1 Survey Paper das alle Keywords
   abdeckt ist KEINE diverse Quellenlage.

   **Gate 2: Mindestens 30% der Keywords haben externen Chunk**
   ```
   keyword_external_coverage >= 0.3
   ```
   Verhindert irrelevante Papers: 10 externe Papers die KEINEN
   unserer Keywords matchen bringen nichts.

   Wenn BEIDE Gates bestanden:
     → diversity_score = Composite (wie berechnet)
   Wenn mindestens 1 Gate NICHT bestanden:
     → diversity_score = min(Composite, 0.40) (gedeckelt)
     → Erzwingt DISCOVERY (weil 0.40 < 0.50 Threshold)

   **Schwellenwerte (nach Gates):**
   - `diversity_score >= 0.5` → Genuegend diverse externe Quellen → PASS
   - `diversity_score < 0.5` → Unzureichend → DISCOVERY

   **WARUM Hard Gates?**
   Ohne Gates kann der Composite Score durch einzelne starke Komponenten
   ueber den Threshold gehoben werden (z.B. kw_ext=1.0 bei nur 1 Paper).
   Hard Gates stellen sicher dass MINIMUM-Diversitaet vorhanden ist.
   Getestet gegen 20 Szenarien: 20/20 korrekt, 0 False Positives,
   Score-Separation 0.248 (kein Overlap PASS vs DISCOVERY).

**Heuristik fuer Klassifikation (Reihenfolge):**
1. metadata.doi existiert → EXTERNAL
2. metadata.source_type in ["academic", "paper"] → EXTERNAL
3. Dateiname matched `*_Model.md`, `*_Spec.md`, `*_Wissen.md`, `README*` → INTERNAL
4. Frontmatter hat `phase:` oder `op:` oder `feature:` → INTERNAL
5. BibTeX-Key hat Format "AutorJahr" (Grossbuchstabe + 4 Ziffern) → EXTERNAL
6. Default: INTERNAL (im Zweifel konservativ)

**Erfolgskriterium:**
- Jedes Quelldokument klassifiziert (INTERNAL/EXTERNAL)
- external_ratio berechnet (0.0 - 1.0)
- Klassifikation in Assessment-JSON gespeichert

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
3. Coverage-Status pro Keyword (v1.2: Source Diversity beruecksichtigt):
   - `chunks_relevant >= min_coverage AND has_external_chunk` → "COVERED"
   - `chunks_relevant >= min_coverage AND NOT has_external_chunk` → "INTERNAL_ONLY"
   - `chunks_relevant > 0 AND < min_coverage` → "PARTIAL"
   - `chunks_relevant == 0` → "MISSING"

4. Berechne ZWEI Coverage-Scores (v1.2):

   **a) `coverage_score` (streng, fuer Decision):**
   ```
   coverage_score = (Keywords "COVERED") / (Total Keywords)
   ```
   Nur Keywords mit EXTERNEN Quellen zaehlen. Fuer akademisches Paper.

   **b) `internal_coverage_score` (weich, fuer Diagnose):**
   ```
   internal_coverage_score = (Keywords "COVERED" + "INTERNAL_ONLY") / (Total Keywords)
   ```
   Alle Keywords mit genuegend Chunks, egal ob intern oder extern.
   Zeigt ob das THEMA abgedeckt ist (unabhaengig von Quellen-Typ).

   **Warum zwei Scores?**
   Wenn `internal_coverage_score` hoch aber `coverage_score` niedrig ist,
   wissen wir: Die THEMEN sind abgedeckt, aber EXTERNE Quellen fehlen.
   → Das ist DISCOVERY, nicht GAP.
   Wenn BEIDE niedrig sind → echtes GAP (Thema nicht abgedeckt).

5. Identifiziere Gap-Topics:
   - Alle Keywords mit Status "PARTIAL" oder "MISSING" → echte Gaps
   - Keywords mit Status "INTERNAL_ONLY" → Discovery-Kandidaten (NICHT Gap!)
   - Sortiere echte Gaps nach Deficit: MISSING zuerst, dann PARTIAL

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

### Schritt 5: Decision-Logik (v1.2: Robuste 2-Dimensionen-Entscheidung)

**Ziel:** Naechsten Schritt in der Pipeline bestimmen

**Zwei unabhaengige Dimensionen:**
- **THEMA:** Sind die Keywords inhaltlich abgedeckt? → `internal_coverage_score`
- **DIVERSITAET:** Gibt es genug externe akademische Quellen? → `diversity_score`

**Aktionen:**
1. Evaluiere mit 2 Dimensionen + Budget:

   ```
   ┌──────────────────────┬─────────────────────┬──────────┬─────────────┐
   │ internal_coverage    │ diversity_score      │ Decision │ Next Step   │
   ├──────────────────────┼─────────────────────┼──────────┼─────────────┤
   │ >= 0.85              │ >= 0.5              │ PASS     │ chapterModel│
   │ >= 0.85              │ < 0.5               │ DISCOVERY│ discovery   │
   │ < 0.85               │ egal                │ GAP      │ research    │
   │ egal                 │ egal, budget == 0   │ FORCE    │ chapterModel│
   └──────────────────────┴─────────────────────┴──────────┴─────────────┘
   ```

   **Erklaerung der 2 Dimensionen:**
   - `internal_coverage` misst ob die THEMEN abgedeckt sind (intern ODER extern)
   - `diversity_score` misst ob genug EXTERNE akademische Quellen da sind
   - PASS: Themen abgedeckt UND genug externe Quellen → weiter
   - DISCOVERY: Themen abgedeckt ABER externe fehlen → Papers suchen
   - GAP: Themen NICHT abgedeckt → inhaltliche Luecken fuellen
   - FORCE: Budget leer → mit dem arbeiten was da ist

   **WARUM v1.2 robuster als v1.1:**
   In v1.1 konnte `coverage_score = 0.0` bei 100% INTERNAL_ONLY Keywords auftreten.
   Dann war `coverage < 0.85 → GAP`, obwohl DISCOVERY gemeint war.
   v1.2 trennt Themen-Abdeckung (internal_coverage) von Quellen-Diversitaet (diversity_score).
   Jetzt: `internal_coverage = 1.0, diversity_score = 0.0 → DISCOVERY` ✓

2. Setze `next_step` in Manifest + Session-State
3. Logge beide Scores + diversity_score Komponenten + Decision + Begruendung
4. Bei DISCOVERY: "Themen abgedeckt (int_cov={X}%), aber diversity_score nur {Y}. Externe akademische Quellen fehlen."
5. Bei GAP: "Themen nicht ausreichend abgedeckt (int_cov={X}%). Inhaltliche Luecken."
6. Bei FORCE: "Budget erschoepft. Weiter mit vorhandenen Quellen."

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
     "last_command": "_WP_assess",
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
- chapter-structure.md fehlt → BLOCKING STOP + empfehle /_WP_structure
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
