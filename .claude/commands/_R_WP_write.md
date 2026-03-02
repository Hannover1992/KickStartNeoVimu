# /_R_WP_write - Chapter Draft Writing

```yaml
status: active
version: 1.0.0
created: 2026-02-09
op: WritePaper
phase: Core Transformation
type: write
chain_position: write
difficulty_scaling: true
mcp_critical: true
```

## VERTRAG

```
+======================================================================+
| VERTRAG: /_R_WP_write                                                  |
+======================================================================+
|                                                                          |
| ACTOR: CHAPTER DRAFT WRITER                                              |
|   TUT:                                                                   |
|     - chapter-{N}-model.md lesen (Themen, Sections, Keywords)           |
|     - N Agents parallel spawnen (3|5|9 basierend auf difficulty)        |
|     - Pro Agent: RAG-Query (research_query Kap.1, research_query_r2     |
|       Kap.2+)                                                            |
|     - Pro Agent: Draft schreiben (Markdown, Sections aus Model)         |
|     - BibTeX-Citations einfuegen (\cite{key})                           |
|     - [FIGURE: ...] Placeholder erstellen                                |
|     - Drafts speichern (output/drafts/chapter-{N}/draft-A{NN}.md)      |
|     - metadata.json mit Agent-Stats generieren                           |
|   NICHT:                                                                 |
|     - Figures generieren (-> visual)                                     |
|     - Quality-Check durchfuehren (-> qualityGate)                       |
|     - Drafts zusammenfuehren (-> synthesis)                              |
|     - Neue Quellen suchen (-> discovery)                                 |
|     - Entscheiden ob Iteration noetig (-> convergence)                  |
|   ESKALIERT:                                                             |
|     - MCP research_query fehlschlaegt fuer ALLE Agents -> STOP +        |
|       NOTIFY Error                                                       |
|     - chapter-{N}-model.md fehlt -> empfehle /_R_WP_chapterModel       |
|     - gap_decision == FORCE + gap_severity == SEVERE -> WARNUNG +       |
|       [GAP: topic] Markierung in Drafts                                  |
|                                                                          |
| LIEST (Input) - PFLICHT:                                                 |
|   1. _manifest.md (current_chapter, phase)                               |
|   2. session-state.json (difficulty, temperature_profile,                |
|      quality_iteration)                                                   |
|   3. config/project.yaml (research_questions, current_chapter)           |
|   4. output/models/chapter-{N}-model.md (Themen, Sections, Keywords)    |
|   5. output/assess/chapter-{N}-gaps.json (gap_decision, gap_severity)   |
|                                                                          |
| SCHREIBT (Output) - PFLICHT:                                             |
|   1. output/drafts/chapter-{N}/draft-A{NN}.md (N Drafts)               |
|   2. output/drafts/chapter-{N}/metadata.json (Agent-Stats)              |
|   3. _manifest.md (UPDATE: draft_count, next_step=visual)               |
|   4. session-state.json (UPDATE: drafts_created, rag_queries_used)      |
|                                                                          |
| POSITION:                                                                |
|   TYPE: LOOP                                                             |
|   LOOP-CONTEXT:                                                          |
|     LOOP-NAME: Quality-Loop                                              |
|     LOOP-LEVEL: INNER                                                    |
|     ITERATION-VARIABLE: quality_iteration                                |
|     MAX-ITERATIONS: extern kontrolliert von /_R_WP_convergence          |
|                      (max 2|3|5)                                         |
|   ENTRY:                                                                 |
|     NORMAL: /_R_WP_chapterGap -> THIS (gap_decision=PASS|FORCE)        |
|     ITERATE: /_R_WP_autoGen -> THIS (Verbesserungen aus Gates)          |
|   EXIT:                                                                  |
|     NORMAL: THIS -> /_R_WP_visual                                       |
|   PHASE: Core Transformation                                            |
|   CHAIN: [chapterGap] -> [write] -> [visual] -> [qualityGate] ->       |
|          [autoGen] -> [convergence]                                      |
|                                                                          |
| MCP-BREMSE:                                                              |
|   Tools: mcp__cleancoder__research_query,                                |
|          mcp__cleancoder__research_query_r2,                             |
|          mcp__cleancoder__extract_keywords                               |
|   Call-Limits:                                                           |
|     easy:   15 (5 per Agent x 3 Agents)                                 |
|     normal: 50 (10 per Agent x 5 Agents)                                |
|     hard:   180 (20 per Agent x 9 Agents)                               |
|   Parameter:                                                             |
|     research_query: limit=20                                             |
|     research_query_r2: limit=20, temperature={from profile},             |
|                        exclusion_threshold=0.85, covered_penalty=0.7     |
|     extract_keywords: count=8                                            |
|   KRITISCH: BLOCKING - Kein RAG -> kein Text                            |
|                                                                          |
| SCHWIERIGKEIT:                                                           |
|   easy:   3 Agents, 5 RAG-Queries/Agent, 10-15 Seiten                  |
|           (~2500-3750 Worte)                                             |
|   normal: 5 Agents, 10 RAG-Queries/Agent, 20-25 Seiten                 |
|           (~5000-6250 Worte)                                             |
|   hard:   9 Agents, 20 RAG-Queries/Agent, 30-35 Seiten                 |
|           (~7500-8750 Worte)                                             |
|                                                                          |
| NOTIFY:                                                                  |
|   powershell -Command "notify 'WritePaper Kapitel {N} Drafts:           |
|   {X}/{Y} erstellt'"                                                     |
|                                                                          |
| TAGS:                                                                    |
|   type: write                                                            |
|   op: WritePaper                                                         |
|   chapter: {N}                                                           |
|   chain-position: write                                                  |
+======================================================================+
```

---

## Verantwortlichkeit

**TUT (Claude):**
- Liest chapter-{N}-model.md fuer Themen, Sections und Keywords des aktuellen Kapitels
- Bestimmt Agent-Anzahl basierend auf difficulty (3 | 5 | 9)
- Spawnt ALLE Agents parallel in EINER Message (M4 Parallel-Spawning)
- Pro Agent: Fuehrt RAG-Queries durch (research_query fuer Kap.1, research_query_r2 fuer Kap.2+)
- Pro Agent: Extrahiert zusaetzliche Keywords via extract_keywords fuer praezisere Queries
- Pro Agent: Schreibt Draft-Markdown mit BibTeX-Citations (\cite{key}) und [FIGURE: ...] Placeholdern
- Speichert Drafts in output/drafts/chapter-{N}/draft-A{NN}.md
- Generiert metadata.json mit Agent-Stats (Queries, Citations, Word-Count)
- Aktualisiert _manifest.md und session-state.json mit Draft-Ergebnissen

**TUT NICHT (Claude):**
- Figures generieren (-> `/_R_WP_visual`)
- Quality-Check durchfuehren (-> `/_R_WP_qualityGate`)
- Drafts zusammenfuehren oder bewerten (-> `/_R_WP_synthesis`)
- Neue Quellen suchen oder herunterladen (-> `/_R_WP_discovery`)
- Entscheiden ob weitere Iteration noetig (-> `/_R_WP_convergence`)
- COVERED Collection modifizieren (-> `/_R_WP_reflect`)

**ESKALATION:**
- MCP-Server nicht erreichbar -> STOP + NOTIFY Error "MCP-Server offline"
- chapter-{N}-model.md fehlt -> STOP + empfehle `/_R_WP_chapterModel` zuerst
- 0 RAG-Results fuer ALLE Agents -> WARNUNG + Draft mit [GAP: topic] Markierungen
- gap_severity == SEVERE -> WARNUNG + Markiere Luecken mit [GAP: topic]
- Budget erschoepft vor Abschluss -> WARNUNG + Continue mit vorhandenen Daten (M5)

---

## Ablauf

### Schritt 0: Inputs lesen

**Ziel:** Kontext und Parameter fuer Draft-Generierung sammeln

**Aktionen:**
1. Lies `_manifest.md` -> `current_chapter` (z.B. 1), `phase`, `next_step`
2. Lies `session-state.json` -> `difficulty`, `temperature_profile`, `quality_iteration`
3. Lies `config/project.yaml` -> `research_questions`, `current_chapter`
4. Lies `output/models/chapter-{N}-model.md` -> Themen, Sections, Keywords
5. Lies `output/assess/chapter-{N}-gaps.json` -> `gap_decision`, `gap_severity`

**Validierung:**
- chapter-{N}-model.md MUSS existieren -> sonst FEHLER + empfehle /_R_WP_chapterModel
- difficulty MUSS gesetzt sein (easy/normal/hard) -> sonst Default: normal
- quality_iteration auslesen (0 = erster Durchlauf, 1+ = Iteration nach autoGen)

**Erfolgskriterium:**
- Alle 5 Input-Dateien gelesen
- Sections und Keywords fuer aktuelles Kapitel extrahiert
- Difficulty, Temperature und Iteration bestimmt

---

### Schritt 1: Agent-Konfiguration

**Ziel:** Agent-Anzahl und Rollen basierend auf Difficulty bestimmen

**Aktionen:**
1. Bestimme `agent_count` aus `difficulty`:
   - easy: 3 Agents
   - normal: 5 Agents
   - hard: 9 Agents
2. Bestimme `rag_queries_per_agent` aus `difficulty`:
   - easy: 5 Queries
   - normal: 10 Queries
   - hard: 20 Queries
3. Bestimme `target_word_count` pro Agent:
   - easy: ~800-1250 Worte (2500-3750 / 3)
   - normal: ~1000-1250 Worte (5000-6250 / 5)
   - hard: ~830-970 Worte (7500-8750 / 9)
4. Weise Agent-Rollen zu basierend auf `agent_count`:

**3 Agents (easy):**

| Agent | Rolle | Fokus | RAG-Bias |
|-------|-------|-------|----------|
| A01 | Foundational Expert | Grundlagen, Definitionen, Literatur-Review | Model Sections 1-2 |
| A02 | Methodological Expert | Methodik, Forschungsdesign, technische Details | Model Sections 3-4 |
| A03 | Applied Expert | Implementierung, Beispiele, Fallstudien | Model Sections 4-5 |

**5 Agents (normal) - Wie easy + 2 weitere:**

| Agent | Rolle | Fokus | RAG-Bias |
|-------|-------|-------|----------|
| A04 | Critical Analyst | Vergleiche, Einschraenkungen, offene Fragen | Cross-Section Keywords |
| A05 | Synthesis Expert | Verbindungen zwischen Sections, roter Faden | Research-Questions Keywords |

**9 Agents (hard) - Wie normal + 4 weitere:**

| Agent | Rolle | Fokus | RAG-Bias |
|-------|-------|-------|----------|
| A06 | Empirical Expert | Studien, Statistiken, Daten | Empirical Keywords |
| A07 | Historical Expert | Entwicklung, Meilensteine, Evolution | Historical Keywords |
| A08 | Comparative Expert | Alternativ-Ansaetze, Trade-Offs | Comparative Keywords |
| A09 | Future Expert | Trends, offene Forschungsfragen, Ausblick | Emerging Keywords |

**Erfolgskriterium:**
- Agent-Anzahl korrekt basierend auf Difficulty
- Jeder Agent hat Rolle, Fokus und RAG-Bias

---

### Schritt 2: Keyword-Anreicherung

**Ziel:** RAG-Keywords pro Agent aus Model-Sections extrahieren und anreichern

**Aktionen:**
1. Pro Section im chapter-{N}-model.md:
   ```python
   section_keywords = await mcp__cleancoder__extract_keywords(
       text="{section_title}: {section_description}",
       count=8
   )
   ```
2. Merge Model-Keywords mit extrahierten Keywords:
   - Model-Keywords haben Vorrang (aus chapterModel)
   - Extrahierte Keywords ergaenzen
3. Weise Keywords den Agents zu basierend auf RAG-Bias:
   - A01: Keywords aus Sections 1-2
   - A02: Keywords aus Sections 3-4
   - A03: Keywords aus Sections 4-5
   - A04+: Cross-Section und Research-Question Keywords

**MCP-Budget-Tracking:**
- Pro Section: 1 extract_keywords Call
- Total: {sections_count} Calls verbraucht
- Kumulativ tracken gegen Call-Limit

**Erfolgskriterium:**
- Jeder Agent hat mindestens 5 zugewiesene Keywords
- MCP-Budget nicht ueberschritten
- Keywords sind unique pro Agent (keine Duplikate)

---

### Schritt 3: RAG-Queries und Draft-Generierung (Multi-Agent)

**Ziel:** ALLE Agents parallel spawnen, jeder Agent schreibt einen Draft

**KERN-MECHANISMUS (M4 Parallel-Spawning):**

ALLE N Agents werden in EINER Message via Task-Tool gestartet.
Kein Agent haengt vom anderen ab. Jeder Agent arbeitet unabhaengig.

**Agent-Auftrag (Pro Agent):**

Jeder Agent erhaelt folgendes Briefing:

```
Du bist Agent A{NN} ({rolle}) fuer Kapitel {N}.

DEIN INPUT:
- chapter-{N}-model.md (Themen, Sections, Keywords)
- Deine Keywords: [{keyword_list}]
- gap_decision: {PASS|FORCE}
- gap_severity: {MINOR|MODERATE|SEVERE}
- quality_iteration: {0|1|2|...}
- EXPLORATION_LEVEL: {high|medium|low}

DEIN AUFTRAG:
1. Fuehre {rag_queries_per_agent} RAG-Queries durch mit deinen Keywords
2. Nutze RAG-Results als Quellenbasis fuer deinen Draft
3. Schreibe Draft-Markdown fuer ALLE Sections des Kapitels
4. Fuer jede Aussage die auf RAG-Results basiert: \cite{bibtex_key}
5. Setze [FIGURE: beschreibung] Placeholder wo Visualisierung sinnvoll
6. Bei gap_severity == SEVERE: Markiere Luecken mit [GAP: topic]
7. Bei quality_iteration > 0: Fokussiere auf Gate-Feedback aus autoGen

DEIN OUTPUT:
- Draft-Markdown (output/drafts/chapter-{N}/draft-A{NN}.md)
  mit Frontmatter: agent, role, chapter, iteration, rag_queries,
  citations, word_count, status

RAG-QUERY METHODE:
{Falls Kapitel 1:}
  mcp__cleancoder__research_query(
      project_path="{project_path}",
      query_text=keyword,
      limit=20
  )
{Falls Kapitel 2+:}
  mcp__cleancoder__research_query_r2(
      project_path="{project_path}",
      query_text=keyword,
      limit=20,
      exclusion_threshold=0.85,
      covered_penalty=0.7,
      temperature={mcp_temperature}
  )
  Fallback: Bei Fehler -> mcp__cleancoder__research_query()

STIL-ANFORDERUNGEN:
- Akademisch, praezise, quellenbasiert
- EXPLORATION_LEVEL bestimmt Perspektive:
  high: Explorative Perspektiven, breite Literatur-Suche
  medium: Ausgewogene Darstellung, fokussiert auf zentrale Methoden
  low: Praezise, technisch, direkt zur Implementierung
- Jeder Abschnitt MUSS mindestens 1 \cite{} haben
- Keine Aussagen ohne RAG-Beleg (M3 RAG-Constraint)
```

**Spawning-Reihenfolge:**
1. Erstelle output/drafts/chapter-{N}/ Ordner falls nicht vorhanden
2. Starte ALLE Agents GLEICHZEITIG in EINER Message (Task-Tool)
3. Warte auf Abschluss aller Agents
4. Sammle Output-Dateien und Stats

**Erfolgskriterium:**
- Alle N Agents erfolgreich gestartet und abgeschlossen
- N Draft-Dateien in output/drafts/chapter-{N}/ vorhanden
- Jeder Draft hat Frontmatter mit Stats
- MCP-Budget eingehalten

---

### Schritt 4: Kap.1 vs Kap.2+ Unterscheidung

**Ziel:** Korrekte RAG-Query-Methode basierend auf Kapitel-Nummer

**Logik:**
- **Kapitel 1 (SOURCES-only):**
  - Nutze `mcp__cleancoder__research_query()` (nur SOURCES Collection)
  - Keine temperature, exclusion_threshold, covered_penalty Parameter
  - Begruendung: Kein COVERED Content vorhanden, EXCLUSION leer

- **Kapitel 2+ (3-Collection-Query):**
  - Nutze `mcp__cleancoder__research_query_r2()` (SOURCES - COVERED - EXCLUSION)
  - temperature aus temperature_profile: Kap.2=1.1, Kap.3=1.0, Kap.4=0.9, Kap.5=0.8
  - exclusion_threshold=0.85, covered_penalty=0.7
  - Begruendung: Vorherige Kapitel sind COVERED, Exclusions moeglich

- **Fallback (research_query_r2 Fehler):**
  - Bei Fehler/Timeout -> Retry mit research_query (SOURCES-only)
  - Logge Fallback in metadata.json: `r2_fallback: true`
  - WARNUNG ausgeben: "research_query_r2 nicht verfuegbar, Fallback zu research_query"

**Erfolgskriterium:**
- Kapitel 1 nutzt NUR research_query
- Kapitel 2+ nutzt research_query_r2 mit korrekten Parametern
- Fallback funktioniert bei r2-Fehlern

---

### Schritt 5: FORCE-Handling (Gap-Decision)

**Ziel:** Korrekte Behandlung von FORCE-Decision aus chapterGap

**Logik:**
- Falls `gap_decision == "PASS"`:
  - Normaler Ablauf, keine Sonderbehandlung
- Falls `gap_decision == "FORCE"`:
  - **gap_severity == "SEVERE":**
    - WARNUNG an User via NOTIFY: "Kapitel {N} schreiben mit SEVERE Gaps"
    - Agent-Prompt ergaenzen: "Markiere Luecken mit [GAP: topic] wo Coverage fehlt"
    - Gates tolerieren niedrigere Citation-Dichte bei FORCE
  - **gap_severity == "MODERATE":**
    - Agent-Prompt ergaenzen: "Bei fehlenden Quellen auf allgemeine Literatur zurueckgreifen"
  - **gap_severity == "MINOR":**
    - Keine Sonderbehandlung, wenige Luecken erwartbar

**Erfolgskriterium:**
- FORCE-Decision korrekt aus gaps.json gelesen
- Agents wissen ueber Gap-Severity Bescheid
- [GAP: ...] Markierungen nur bei SEVERE

---

### Schritt 6: Output sammeln und validieren

**Ziel:** Draft-Ergebnisse sammeln, metadata.json generieren

**Aktionen:**
1. Lese alle Draft-Dateien aus output/drafts/chapter-{N}/
2. Pro Draft: Extrahiere Stats aus Frontmatter:
   - agent, role, rag_queries, citations, word_count, figures, gaps
3. Berechne Aggregate:
   - total_rag_queries: Summe aller Agent-Queries
   - total_citations: Summe aller Citations
   - avg_word_count: Durchschnitt der Word-Counts
   - total_figures: Summe aller [FIGURE: ...] Placeholder
   - total_gaps: Summe aller [GAP: ...] Markierungen
4. Generiere output/drafts/chapter-{N}/metadata.json:
   ```json
   {
     "chapter": {N},
     "difficulty": "{difficulty}",
     "agent_count": {N},
     "quality_iteration": {I},
     "created": "{timestamp}",
     "drafts": [
       {
         "agent": "A01",
         "role": "Foundational Expert",
         "file": "draft-A01.md",
         "rag_queries": 10,
         "citations": 15,
         "word_count": 2300,
         "figures": 2,
         "gaps": 0
       }
     ],
     "total_rag_queries": 50,
     "total_citations": 87,
     "avg_word_count": 2400,
     "total_figures": 8,
     "total_gaps": 1,
     "r2_fallback": false,
     "next_step": "visual"
   }
   ```
5. Validierung:
   - Mindestens 1 Draft vorhanden
   - Jeder Draft hat > 500 Worte
   - Mindestens 1 Citation pro Draft

**Erfolgskriterium:**
- metadata.json generiert mit korrekten Stats
- Alle Drafts haben Mindest-Qualitaet (Worte, Citations)
- Aggregate korrekt berechnet

---

### Schritt 7: State aktualisieren

**Ziel:** Manifest und Session-State mit Draft-Ergebnissen aktualisieren

**Aktionen (M6 Multi-State-Sync-Reihenfolge):**

1. **OUTPUT** (bereits in Schritt 6):
   - output/drafts/chapter-{N}/draft-A{NN}.md (N Drafts)
   - output/drafts/chapter-{N}/metadata.json

2. **Manifest aktualisieren:**
   ```markdown
   ## Draft Status - Kapitel {N}
   - **Drafts erstellt:** {agent_count}/{agent_count}
   - **Total Word Count:** {total_words}
   - **Total Citations:** {total_citations}
   - **Total Figures:** {total_figures}
   - **Quality Iteration:** {quality_iteration}
   - **Next Step:** visual
   ```

3. **Session-State aktualisieren:**
   ```json
   {
     "last_command": "_R_WP_write",
     "drafts_created": {agent_count},
     "total_rag_queries_used": {total_rag_queries},
     "quality_iteration": {quality_iteration},
     "draft_avg_word_count": {avg_word_count},
     "draft_total_citations": {total_citations},
     "next_step": "visual"
   }
   ```

4. **NOTIFY:**
   ```powershell
   powershell -Command "notify 'WritePaper Kapitel {N} Drafts: {X}/{Y} erstellt'"
   ```

**Erfolgskriterium:**
- _manifest.md und session-state.json aktualisiert
- next_step = "visual" gesetzt
- NOTIFY gesendet

---

## Output-Format

### output/drafts/chapter-{N}/draft-A{NN}.md

**Zweck:** Einzelner Agent-Draft fuer ein Kapitel

**Schema:**
```markdown
---
agent: A01
role: Foundational Expert
chapter: 1
iteration: 0
rag_queries: 10
citations: 15
word_count: 2300
figures: 2
gaps: 0
status: draft
created: 2026-02-09T10:30:00Z
---

# 1. Einleitung

## 1.1 Motivation

Clean Code ist ein zentrales Prinzip der Softwareentwicklung \cite{Martin2008}.
Studien zeigen dass gut strukturierter Code die Wartbarkeit um 40% steigert
\cite{McConnell2004}.

[FIGURE: code_quality_metrics - Balkendiagramm Clean vs Legacy Code]

## 1.2 Forschungsfragen

Diese Arbeit untersucht drei zentrale Fragen:
1. Welche Prinzipien definieren Clean Code?
2. Wie messbar sind diese Prinzipien?
3. Welche Tools unterstuetzen Clean Code Metriken?

[GAP: empirical_validation - Coverage unzureichend, siehe discovery]

## 1.3 Zielsetzung
[...]
```

### output/drafts/chapter-{N}/metadata.json

**Zweck:** Aggregierte Agent-Stats fuer nachgelagerte Commands

**Schema:**
```json
{
  "chapter": 1,
  "difficulty": "normal",
  "agent_count": 5,
  "quality_iteration": 0,
  "created": "2026-02-09T10:30:00Z",
  "drafts": [
    {
      "agent": "A01",
      "role": "Foundational Expert",
      "file": "draft-A01.md",
      "rag_queries": 10,
      "citations": 15,
      "word_count": 2300,
      "figures": 2,
      "gaps": 0
    },
    {
      "agent": "A02",
      "role": "Methodological Expert",
      "file": "draft-A02.md",
      "rag_queries": 12,
      "citations": 18,
      "word_count": 2500,
      "figures": 3,
      "gaps": 0
    }
  ],
  "total_rag_queries": 58,
  "total_citations": 87,
  "avg_word_count": 2400,
  "total_figures": 8,
  "total_gaps": 1,
  "r2_fallback": false,
  "next_step": "visual"
}
```

---

## Qualitaetskriterien

### Vollstaendigkeit
- [ ] Alle N Agents spawned und abgeschlossen
- [ ] N Draft-Dateien in output/drafts/chapter-{N}/ vorhanden
- [ ] metadata.json mit korrekten Aggregates
- [ ] Jeder Draft hat Frontmatter mit Stats
- [ ] _manifest.md und session-state.json aktualisiert

### Korrektheit
- [ ] Kapitel 1 nutzt research_query, Kapitel 2+ nutzt research_query_r2
- [ ] MCP-Namespace korrekt: `mcp__cleancoder__*`
- [ ] temperature aus temperature_profile (nicht hardcoded)
- [ ] Citations referenzieren echte BibTeX-Keys aus RAG-Results
- [ ] [FIGURE: ...] Placeholder sind deskriptiv und eindeutig
- [ ] [GAP: ...] nur bei gap_severity == SEVERE

### Robustheit
- [ ] Fallback: research_query_r2 Fehler -> research_query
- [ ] Budget-Exhaustion (M5): WARNUNG + Continue mit vorhandenen Daten
- [ ] Einzelne Agent-Fehler stoppen nicht gesamtes Schreiben
- [ ] FORCE-Handling: [GAP: topic] bei SEVERE
- [ ] MCP-Server offline -> BLOCKING STOP + ESKALATION

### Performance
- [ ] ALLE Agents in EINER Message gestartet (M4)
- [ ] Keywords dedupliziert pro Agent
- [ ] MCP-Budget respektiert (easy=15, normal=50, hard=180)
- [ ] Keine redundanten RAG-Queries

---

## NOTIFY

**Success:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Drafts: {X}/{Y} erstellt'"
```

**Warning (FORCE/Budget):**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Drafts: {X}/{Y} (FORCE/Budget)'"
```

**Error:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Drafts FAILED: MCP-Server offline'"
```

---

## Error Handling

| Kategorie | Trigger | Response | NOTIFY |
|-----------|---------|----------|--------|
| BLOCKING | MCP-Server offline, chapter-model fehlt, Dateisystem readonly | STOP Execution + NOTIFY Error + User-Intervention PFLICHT | JA (ERROR) |
| NON-BLOCKING | 1 Agent fehlgeschlagen, 1 RAG-Query Timeout, 1 Draft leer | CONTINUE + Log Warnung + Reduzierte Draft-Zahl in metadata | Optional (WARNING) |
| FALLBACK | research_query_r2 fehlerhaft, temperature_profile fehlt, gap_severity unbekannt | Standard-Strategie: research_query, temperature=1.0, gap_severity=MINOR | JA (INFO) |

**Spezifische Fehlerbehandlung:**
- research_query_r2 FAIL -> Retry mit research_query (Fallback, wie assess Z230)
- temperature_profile fehlt -> Fixed temperature=1.0 fuer alle Kapitel
- Agent-Timeout -> Skip Agent, Draft-Zahl reduzieren, metadata anpassen
- Budget bei 0 vor Start -> WARNUNG + Skip RAG-Queries, Draft nur aus Model-Keywords

---

## Hinweise

### MCP-Bremse
- **KRITISCH:** Dieser Command ist BLOCKING fuer visual, qualityGate, review, synthesis, reflect, convergence
- Ohne Drafts kann die Quality-Loop nicht starten
- Budget-Tracking pro Agent: `rag_queries_per_agent * agent_count = total_budget`
- Budget-Exhaustion-Handler (M5): WARNUNG + Continue bei budget == 0

### Difficulty-Scaling
- easy: 3 Agents, 5 Queries/Agent, 10-15 Seiten, Budget=15
- normal: 5 Agents, 10 Queries/Agent, 20-25 Seiten, Budget=50
- hard: 9 Agents, 20 Queries/Agent, 30-35 Seiten, Budget=180

### Multi-Agent-Pattern (M4)
- ALLE N Agents in EINER Message spawnen (Task-Tool)
- KEINE Dependencies zwischen Agents
- Output: N unabhaengige Draft-Dateien
- Jeder Agent arbeitet auf GLEICHEM Input (chapter-{N}-model.md)
- Unterschied: Jeder Agent betont unterschiedliche RAG-Keywords (RAG-Bias)

### Temperatur-Gradient (W7)
- EXPLORATION_LEVEL + mcp_temperature aus temperature_profile in session-state.json
- Kap.1: high / 1.2, Kap.2: high / 1.1, Kap.3: medium / 1.0, Kap.4: low / 0.9, Kap.5: low / 0.8
- Fallback: temperature=1.0 falls temperature_profile fehlt

### 3-Collection-Query (W8)
- Kapitel 1: NUR SOURCES Collection -> research_query
- Kapitel 2+: SOURCES - COVERED - EXCLUSION -> research_query_r2
- covered_penalty=0.7 und exclusion_threshold=0.85 sind Defaults
- Fallback bei r2-Fehler: research_query (W8-Degradation)

### LOOP-CONTEXT (W1)
- write ist WORKER im INNER Quality-Loop
- Controller: /_R_WP_convergence (entscheidet CONVERGE|ITERATE|FORCE)
- Bei ITERATE: write wird erneut aufgerufen mit quality_iteration + 1
- Bei ITERATE: autoGen liefert Gate-Feedback als zusaetzlichen Input
- write hat KEIN eigenes MAX-ITERATIONS (Controller-Verantwortung)

### Chain-Integration
- ENTRY: chapterGap -> write (erster Durchlauf) ODER autoGen -> write (Iteration)
- EXIT: write -> visual (immer, ausser BLOCKING Error)
- ITERATE: convergence -> autoGen -> write (Quality-Loop Iteration)
- CONVERGE: convergence -> review -> synthesis -> reflect (Exit Quality-Loop)
