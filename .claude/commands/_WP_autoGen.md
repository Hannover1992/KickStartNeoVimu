# /_WP_autoGen - Gap-Driven Section Rewrite

```yaml
status: active
version: 1.0.0
created: 2026-02-10
op: WritePaper
phase: Core Transformation
type: Standard + MCP
chain_position: autoGen
difficulty_scaling: true
mcp_critical: false
loop_level: INNER
```

## VERTRAG

```
+======================================================================+
| VERTRAG: /_WP_autoGen                                               |
+======================================================================+
|                                                                        |
| ACTOR: GAP-DRIVEN SECTION-REWRITE WORKER                              |
|   TUT:                                                                 |
|     - gap-autoGen.json lesen (FAIL-Gates, Section-IDs, Findings)      |
|     - Falls alle Gates PASS (gap leer) -> SKIP zu convergence         |
|     - Findings nach Section gruppieren (Priority: Gate-Gewicht)       |
|     - Pro Section mit Findings: 1 Agent spawnen (M4)                  |
|     - Agent: RAG-Query (research_query_r2), Section-Rewrite,          |
|       Citations aktualisieren                                          |
|     - Rewrites in chapter-draft.tex mergen (lokales Update)           |
|     - autoGen-report.json mit Rewrite-Stats generieren                |
|     - session-state.json + _manifest.md aktualisieren                 |
|   NICHT:                                                               |
|     - Vollstaendige Drafts schreiben (-> write)                       |
|     - Quality Gates evaluieren (-> qualityGate)                       |
|     - Entscheiden ob Iteration noetig (-> convergence)                |
|     - Neue Quellen suchen (-> discovery)                              |
|     - Figures generieren (-> visual)                                  |
|     - Kapitel-Retrospektive (-> reflect)                              |
|   ESKALIERT:                                                           |
|     - gap-autoGen.json fehlt -> STOP + empfehle qualityGate           |
|     - chapter-draft.tex fehlt -> STOP + empfehle synthesis            |
|     - Alle Sections in ALLEN Gates FAIL -> WARNUNG + User-Info        |
|     - MCP-Budget erschoepft -> WARNUNG + Continue mit vorhandenen     |
|       Rewrites (M5)                                                    |
|                                                                        |
| LIEST (Input) - PFLICHT:                                               |
|   1. _manifest.md (current_chapter, quality_iteration, phase)         |
|   2. session-state.json (difficulty, quality_iteration,                |
|      mcp_budget_remaining)                                             |
|   3. config/project.yaml (current_chapter, research_questions)        |
|   4. output/quality/chapter-{N}/gap-autoGen.json                      |
|      (FAIL-Gates, Section-IDs, Findings, improvement_actions)         |
|   5. output/synthesis/chapter-{N}/chapter-draft.tex                   |
|      (aktuelle Draft-Version fuer IN-PLACE Update)                    |
|   6. output/models/chapter-{N}-model.md (Sections, Keywords)          |
|                                                                        |
| SCHREIBT (Output) - PFLICHT:                                           |
|   1. output/synthesis/chapter-{N}/chapter-draft.tex (UPDATED)         |
|   2. output/quality/chapter-{N}/autoGen-report.json                   |
|   3. _manifest.md (UPDATE: autogen_status, sections_improved)         |
|   4. session-state.json (UPDATE: autogen_executed,                    |
|      rag_queries_used, quality_iteration)                              |
|                                                                        |
| POSITION:                                                              |
|   TYPE: LOOP                                                           |
|   LOOP-CONTEXT:                                                        |
|     LOOP-NAME: Quality-Loop                                            |
|     LOOP-LEVEL: INNER                                                  |
|     ITERATION-VARIABLE: quality_iteration                              |
|     MAX-ITERATIONS: extern kontrolliert von /_WP_convergence        |
|                      (max 2|3|5)                                       |
|   ENTRY:                                                               |
|     NORMAL: /_WP_qualityGate -> THIS (>= 1 FAIL-Gate)              |
|     SKIP: /_WP_qualityGate -> /_WP_convergence                   |
|            (alle Gates PASS, gap-autoGen.json leer)                    |
|   EXIT:                                                                |
|     NORMAL: THIS -> /_WP_convergence (nach Rewrites)                |
|   PHASE: Core Transformation                                          |
|   CHAIN: [qualityGate] -> [autoGen] -> [convergence]                  |
|                                                                        |
| MCP-BREMSE:                                                            |
|   Tools: mcp__cleancoder__research_query_r2,                           |
|          mcp__cleancoder__extract_keywords                             |
|   Call-Limits:                                                         |
|     easy:   6-10  (2 Queries x 2-3 Sections + extract_keywords)       |
|     normal: 15-20 (3 Queries x 3-5 Sections + extract_keywords)      |
|     hard:   40-50 (5 Queries x 4-8 Sections + extract_keywords)      |
|   Parameter:                                                           |
|     research_query_r2: limit=10, temperature={from profile},           |
|                        exclusion_threshold=0.85, covered_penalty=0.7   |
|     extract_keywords: count=5                                          |
|   KRITISCH: NON-BLOCKING (Rewrites moeglich ohne RAG, Qualitaet      |
|             sinkt)                                                      |
|                                                                        |
| SCHWIERIGKEIT:                                                         |
|   easy:   max 3 Sections, 2 RAG-Queries/Section, Gates: 3             |
|   normal: max 5 Sections, 3 RAG-Queries/Section, Gates: 5             |
|   hard:   max 8 Sections, 5 RAG-Queries/Section, Gates: 8             |
|   Difficulty-Dependent-Thresholds:                                     |
|   | Dimension           | easy | normal | hard |                      |
|   |---------------------|------|--------|------|                      |
|   | max_sections        | 3    | 5      | 8    |                      |
|   | rag_queries_section | 2    | 3      | 5    |                      |
|   | mcp_budget          | 6-10 | 15-20  | 40-50|                      |
|                                                                        |
| NOTIFY:                                                                |
|   powershell -Command "notify 'WritePaper Kapitel {N} autoGen:        |
|   {X} Sections verbessert (Gates: {failed_gates})'"                   |
|                                                                        |
| TAGS:                                                                  |
|   type: autoGen                                                        |
|   op: WritePaper                                                       |
|   chapter: {N}                                                         |
|   chain-position: autoGen                                              |
|   loop-level: INNER                                                    |
+======================================================================+
```

---

## Verantwortlichkeit

**TUT (Claude):**
- Liest gap-autoGen.json fuer FAIL-Gate Findings mit Section-IDs und Improvement-Actions
- Prueft ob gap-autoGen.json leer ist (alle Gates PASS) → Skip zu convergence
- Gruppiert Findings nach Section (Section-ID als Schluessel)
- Sortiert Sections nach Gate-Prioritaet (priority_order aus gap-autoGen.json)
- Pro Section: Spawnt 1 Agent fuer gezieltes Section-Rewrite (M4)
- Jeder Agent: Fuehrt RAG-Queries (research_query_r2) fuer Section-Keywords durch
- Jeder Agent: Schreibt UPDATED Section basierend auf Gate-Feedback + RAG-Results
- Merged Section-Rewrites zurueck in chapter-draft.tex (IN-PLACE Update)
- Generiert autoGen-report.json mit Rewrite-Statistiken
- Aktualisiert _manifest.md und session-state.json nach M6 Reihenfolge

**TUT NICHT (Claude):**
- Vollstaendige Drafts schreiben (→ `/_WP_write`)
- Quality Gates evaluieren (→ `/_WP_qualityGate`)
- Entscheiden ob weitere Iteration noetig (→ `/_WP_convergence`)
- Neue Quellen suchen oder herunterladen (→ `/_WP_discovery`)
- Figures generieren oder reviewen (→ `/_WP_visual`)
- Kapitel-Retrospektive oder COVERED marking (→ `/_WP_reflect`)
- COVERED Collection modifizieren (→ `/_WP_reflect`)

**ESKALATION:**
- gap-autoGen.json fehlt → BLOCKING STOP + empfehle `/_WP_qualityGate` zuerst
- chapter-draft.tex fehlt → BLOCKING STOP + empfehle `/_WP_synthesis` zuerst
- Alle Sections in allen Gates FAIL → WARNUNG + weiter (Rewrites fuer Top-Priority)
- MCP-Budget erschoepft → WARNUNG + Continue mit vorhandenen Rewrites (M5)
- Section-Boundary-Fehler bei Merge → WARNUNG + Skip betroffene Section + dokumentieren

---

## Ablauf

### Schritt 0: Inputs lesen

**Ziel:** Kontext und Gate-Findings laden

**Aktionen:**
1. Lies `_manifest.md` → `current_chapter`, `quality_iteration`, `phase`
2. Lies `session-state.json` → `difficulty`, `quality_iteration`, `mcp_budget_remaining`
3. Lies `config/project.yaml` → `current_chapter`, `research_questions`
4. Lies `output/quality/chapter-{N}/gap-autoGen.json` → FAIL-Gates, Findings, Priority
5. Lies `output/synthesis/chapter-{N}/chapter-draft.tex` → aktuelle Draft-Version
6. Lies `output/models/chapter-{N}-model.md` → Sections, Keywords

**Validierung:**
- gap-autoGen.json MUSS existieren → sonst BLOCKING STOP
- chapter-draft.tex MUSS existieren → sonst BLOCKING STOP
- difficulty MUSS gesetzt sein → sonst Default: normal

**Erfolgskriterium:**
- Alle 6 Input-Dateien gelesen
- FAIL-Gates und Findings extrahiert
- Difficulty und Budget bestimmt

---

### Schritt 1: Skip-Pruefung

**Ziel:** Pruefen ob autoGen noetig ist oder uebersprungen werden kann

**Aktionen:**
1. Pruefe gap-autoGen.json:
   ```
   IF failed_gates.length == 0 AND warned_gates.length == 0:
       SKIP autoGen
       next_step = "convergence"
       NOTIFY "autoGen: Skip (alle Gates PASS)"
       UPDATE _manifest.md: autogen_status=SKIPPED
       UPDATE session-state.json: autogen_executed=false
       EXIT (Schritt 7 direkt)
   ```

2. Falls NICHT Skip:
   ```
   total_issues = gap-autoGen.json.total_issues
   priority_order = gap-autoGen.json.priority_order
   CONTINUE zu Schritt 2
   ```

**Erfolgskriterium:**
- Skip korrekt erkannt bei leerer gap-autoGen.json
- Bei Skip: State aktualisiert, NOTIFY gesendet
- Bei Nicht-Skip: Weiter mit Schritt 2

---

### Schritt 2: Section-Gruppierung

**Ziel:** Findings nach Section organisieren fuer gezielte Rewrites

**Aktionen:**
1. Extrahiere alle Issues aus failed_gates[] und warned_gates[]:
   ```
   sections = {}
   FOR gate IN failed_gates + warned_gates:
       FOR issue IN gate.issues:
           section_id = issue.section
           IF section_id NOT IN sections:
               sections[section_id] = {issues: [], actions: [], gates: []}
           sections[section_id].issues.append(issue)
           sections[section_id].actions.extend(gate.improvement_actions)
           sections[section_id].gates.append(gate.gate)
   ```

2. Sortiere Sections nach Prioritaet:
   - Sections mit mehr FAIL-Gate-Issues zuerst
   - Bei Gleichstand: Reihenfolge aus priority_order

3. Limitiere auf max_sections (difficulty-abhaengig):
   ```
   max_sections = {easy: 3, normal: 5, hard: 8}[difficulty]
   target_sections = sections[:max_sections]
   ```

**Erfolgskriterium:**
- Issues korrekt nach Section gruppiert
- Sections nach Prioritaet sortiert
- Max-Sections-Limit respektiert

---

### Schritt 3: Agent-Konfiguration

**Ziel:** Pro Section 1 Agent konfigurieren

**Aktionen:**
1. Bestimme `rag_queries_per_section` aus difficulty:
   - easy: 2 Queries
   - normal: 3 Queries
   - hard: 5 Queries

2. Pro Section ein Agent-Briefing erstellen:
   ```
   Agent-Briefing:
   - section_id: "1.2"
   - section_title: aus chapter-model
   - current_content: aus chapter-draft.tex (Section-Extrakt)
   - issues: [{type, description}]
   - improvement_actions: ["Erhoehe Citation-Density..."]
   - rag_keywords: aus chapter-model + extract_keywords
   - rag_queries: rag_queries_per_section
   ```

3. Pruefe MCP-Budget:
   ```
   total_rag_needed = len(target_sections) * rag_queries_per_section
   total_extract_needed = len(target_sections)
   total_needed = total_rag_needed + total_extract_needed
   IF total_needed > mcp_budget_remaining:
       WARNUNG "Budget knapp: {total_needed} noetig, {budget} verfuegbar"
       Reduziere rag_queries_per_section proportional
   ```

**Erfolgskriterium:**
- Agent-Briefing pro Section erstellt
- RAG-Budget geprueft und angepasst
- Keywords zugewiesen

---

### Schritt 4: Keyword-Extraktion (MCP)

**Ziel:** Praezise RAG-Keywords pro Section generieren

**Aktionen:**
1. Pro Section:
   ```python
   section_keywords = await mcp__cleancoder__extract_keywords(
       text="{section_title}: {improvement_actions_text}",
       count=5
   )
   ```

2. Merge mit Model-Keywords:
   - Model-Keywords haben Vorrang
   - Extrahierte Keywords ergaenzen

3. Budget-Tracking:
   ```
   mcp_calls_used += len(target_sections)
   ```

**Erfolgskriterium:**
- Keywords pro Section extrahiert
- Budget korrekt getrackt

---

### Schritt 5: RAG-Queries und Section-Rewrites (Multi-Agent)

**Ziel:** ALLE Section-Agents parallel spawnen fuer gezielte Rewrites

**KERN-MECHANISMUS (M4 Parallel-Spawning):**

ALLE Agents in EINER Message via Task-Tool starten.
Kein Agent haengt vom anderen ab. Jeder Agent arbeitet unabhaengig auf seiner Section.

**Agent-Auftrag (Pro Section):**

```
Du bist Section-Rewrite Agent fuer Section {section_id} in Kapitel {N}.

DEIN INPUT:
- Aktuelle Section aus chapter-draft.tex:
  {current_section_content}
- Gate-Findings:
  {issues_list}
- Improvement-Actions:
  {actions_list}
- Keywords: [{keyword_list}]
- quality_iteration: {I}

DEIN AUFTRAG:
1. Fuehre {rag_queries_per_section} RAG-Queries durch mit deinen Keywords
2. Analysiere Gate-Findings und identifiziere spezifische Schwaechen
3. Schreibe UPDATED Section:
   - Behebe Gate-Findings (z.B. erhoehe Citation-Density)
   - Fuege neue RAG-basierte Citations hinzu (\cite{key})
   - Behalte existierenden guten Content bei
   - Verbessere nur die identifizierten Schwaechen
4. Output: Rewritten Section als Markdown

RAG-QUERY METHODE:
  mcp__cleancoder__research_query_r2(
      project_path="{project_path}",
      query_text=keyword,
      limit=10,
      exclusion_threshold=0.85,
      covered_penalty=0.7,
      temperature={mcp_temperature}
  )
  Fallback: Bei Fehler -> mcp__cleancoder__research_query()

REGELN:
- NUR die angegebene Section umschreiben (nicht andere Sections)
- Bestehende Citations BEHALTEN (nur ergaenzen, nicht entfernen)
- Stil und Terminologie des bestehenden Drafts beibehalten
- Bei Citation-Gaps: Neue \cite{key} aus RAG-Results einfuegen
- Bei fehlender Coverage: Text mit RAG-Belegen ergaenzen
- KEINE Aussagen ohne RAG-Beleg (M3 RAG-Constraint)
```

**Spawning:**
1. Starte ALLE Section-Agents GLEICHZEITIG in EINER Message (Task-Tool)
2. Warte auf Abschluss aller Agents
3. Sammle rewritten Sections

**Erfolgskriterium:**
- Alle Section-Agents gestartet und abgeschlossen
- Jeder Agent liefert rewritten Section
- MCP-Budget eingehalten

---

### Schritt 6: Section-Merge in chapter-draft.tex

**Ziel:** Rewritten Sections zurueck in chapter-draft.tex integrieren

**Aktionen:**
1. Pro rewritten Section:
   - Identifiziere Section-Boundaries in chapter-draft.tex via LaTeX `\section{...}` oder Markdown `## ...` Marker
   - Ersetze Original-Section mit Rewritten-Section
   - Behalte Sections die NICHT rewritten wurden unveraendert

2. Validierung nach Merge:
   - Alle Original-Sections vorhanden (keine versehentlich geloescht)?
   - Section-Reihenfolge korrekt?
   - LaTeX/Markdown-Syntax intakt?

3. Falls Section-Boundary-Fehler:
   - WARNUNG + Skip betroffene Section
   - Dokumentiere in autoGen-report.json: `merge_failed_sections: ["1.3"]`

**Erfolgskriterium:**
- chapter-draft.tex IN-PLACE aktualisiert
- Alle nicht-rewritten Sections unveraendert
- Keine Syntax-Fehler eingefuehrt

---

### Schritt 7: State aktualisieren (M6 Reihenfolge)

**Ziel:** autoGen-Ergebnis persistent speichern

**Aktionen:**

#### 7a. OUTPUT: autoGen-report.json

Schreibe `output/quality/chapter-{N}/autoGen-report.json`:

```json
{
  "chapter": 1,
  "quality_iteration": 1,
  "difficulty": "hard",
  "timestamp": "2026-02-10T13:00:00Z",
  "skipped": false,
  "sections_targeted": 4,
  "sections_rewritten": 4,
  "sections_failed": 0,
  "merge_failed_sections": [],
  "gates_addressed": ["G5", "G4"],
  "total_rag_queries": 20,
  "total_extract_keywords": 4,
  "mcp_budget_used": 24,
  "agent_stats": [
    {
      "section_id": "1.2",
      "issues_addressed": 2,
      "rag_queries": 5,
      "citations_added": 3,
      "word_count_delta": "+120"
    }
  ],
  "next_step": "convergence"
}
```

#### 7b. _manifest.md UPDATE

```markdown
## autoGen - Kapitel {N}, Iteration {I}
- **Status:** {COMPLETED|SKIPPED}
- **Sections:** {rewritten}/{targeted}
- **Gates addressed:** {gate_list}
- **RAG Queries:** {total}
- **Next Step:** convergence
```

#### 7c. session-state.json UPDATE

```json
{
  "last_command": "_WP_autoGen",
  "autogen_executed": true,
  "autogen_sections_rewritten": 4,
  "autogen_rag_queries_used": 24,
  "next_step": "convergence"
}
```

#### 7d. NOTIFY

```powershell
powershell -Command "notify 'WritePaper Kapitel {N} autoGen: {X} Sections verbessert (Gates: {failed_gates})'"
```

**Erfolgskriterium:**
- autoGen-report.json geschrieben
- _manifest.md und session-state.json aktualisiert
- NOTIFY gesendet

---

## Output-Format

### output/quality/chapter-{N}/autoGen-report.json

**Zweck:** Rewrite-Statistiken fuer Traceability und convergence-Input

**Schema:**
```json
{
  "chapter": 1,
  "quality_iteration": 0,
  "difficulty": "normal",
  "timestamp": "2026-02-10T13:00:00Z",
  "skipped": false,
  "sections_targeted": 3,
  "sections_rewritten": 3,
  "sections_failed": 0,
  "merge_failed_sections": [],
  "gates_addressed": ["G5", "G1"],
  "total_rag_queries": 9,
  "total_extract_keywords": 3,
  "mcp_budget_used": 12,
  "agent_stats": [
    {
      "section_id": "1.2",
      "gate_ids": ["G5"],
      "issues_addressed": 2,
      "rag_queries": 3,
      "citations_added": 3,
      "word_count_delta": "+120"
    },
    {
      "section_id": "1.3",
      "gate_ids": ["G5"],
      "issues_addressed": 1,
      "rag_queries": 3,
      "citations_added": 2,
      "word_count_delta": "+85"
    },
    {
      "section_id": "1.1",
      "gate_ids": ["G1"],
      "issues_addressed": 1,
      "rag_queries": 3,
      "citations_added": 0,
      "word_count_delta": "+200"
    }
  ],
  "next_step": "convergence"
}
```

**Konsumenten:**
- `/_WP_convergence`: Liest autoGen-report fuer Verbesserungs-Tracking
- `/_WP_reflect`: Liest als Teil der Kapitel-Retrospektive

---

## Qualitaetskriterien

### Vollstaendigkeit
- [ ] gap-autoGen.json gelesen und Findings extrahiert
- [ ] Skip-Logik korrekt (leere gap → Skip zu convergence)
- [ ] Sections nach Prioritaet gruppiert und limitiert
- [ ] Alle Section-Agents spawned und abgeschlossen
- [ ] chapter-draft.tex IN-PLACE aktualisiert
- [ ] autoGen-report.json geschrieben
- [ ] _manifest.md und session-state.json aktualisiert
- [ ] NOTIFY gesendet

### Korrektheit
- [ ] Nur FAIL/WARN-Gate Sections werden rewritten (nicht PASS)
- [ ] Bestehende Citations BEHALTEN (nur ergaenzt)
- [ ] Section-Boundaries korrekt erkannt (LaTeX/Markdown Marker)
- [ ] MCP-Namespace korrekt: `mcp__cleancoder__*`
- [ ] max_sections aus difficulty (3|5|8)
- [ ] rag_queries_section aus difficulty (2|3|5)

### Robustheit
- [ ] gap-autoGen.json fehlt → BLOCKING STOP
- [ ] chapter-draft.tex fehlt → BLOCKING STOP
- [ ] MCP-Budget erschoepft → WARNUNG + Continue (M5)
- [ ] Section-Boundary-Fehler → Skip Section + dokumentieren
- [ ] Einzelner Agent-Fehler → Skip Section + Warnung
- [ ] Fallback: research_query_r2 Fehler → research_query

### Performance
- [ ] ALLE Agents in EINER Message (M4 Parallel-Spawning)
- [ ] MCP-Budget respektiert (6-10|15-20|40-50)
- [ ] Keywords dedupliziert pro Section
- [ ] Keine redundanten RAG-Queries

---

## NOTIFY

**Success:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} autoGen: {X}/{Y} Sections verbessert (Gates: {gates})'"
```

**Skip:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} autoGen: SKIP (alle Gates PASS)'"
```

**Warning (Budget/Merge):**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} autoGen: {X}/{Y} (Budget/Merge Warning)'"
```

**Error:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} autoGen FAILED: {reason}'"
```

---

## Error Handling

| Kategorie | Trigger | Response | NOTIFY |
|-----------|---------|----------|--------|
| BLOCKING | gap-autoGen.json fehlt | STOP + empfehle /_WP_qualityGate | ERROR |
| BLOCKING | chapter-draft.tex fehlt | STOP + empfehle /_WP_synthesis | ERROR |
| NON-BLOCKING | 1 Agent fehlgeschlagen | Skip Section + Warnung + weiter | WARNING |
| NON-BLOCKING | Section-Boundary nicht erkannt | Skip Section + dokumentieren | WARNING |
| NON-BLOCKING | MCP-Budget erschoepft | Continue mit vorhandenen Rewrites (M5) | WARNING |
| FALLBACK | research_query_r2 Fehler | Retry mit research_query | INFO |
| FALLBACK | extract_keywords Fehler | Nutze Model-Keywords als Fallback | INFO |
| FALLBACK | 0 RAG-Results | Rewrite basierend auf Gate-Findings Text | INFO |

---

## Hinweise

### Unterschied zu write
- **write**: Erstellt vollstaendige Drafts (alle Sections, N Agents, viele RAG-Queries)
- **autoGen**: Verbessert gezielte Sections (nur FAIL-Sections, 1 Agent/Section, wenige RAG-Queries)
- autoGen ist der "Chirurg", write ist der "Architekt"

### Skip-Pfad
- Wenn qualityGate ALLE Gates PASS evaluiert → gap-autoGen.json hat leere failed_gates
- autoGen erkennt dies in Schritt 1 und ueberspringt die gesamte Verarbeitung
- Routing geht direkt zu convergence (NORMAL-Pfad bei guter Qualitaet)
- Skip ist der GEWUENSCHTE Zustand (keine Verbesserung noetig)

### Section-Boundaries
- chapter-draft.tex nutzt LaTeX `\section{...}` oder Markdown `## ...` Marker
- autoGen identifiziert Sections anhand dieser Marker
- Falls Marker fehlen oder ambig: WARNUNG + Skip Section

### LOOP-CONTEXT (W1)
- autoGen ist WORKER im INNER Quality-Loop
- Controller: /_WP_convergence (entscheidet CONVERGE|ITERATE|FORCE)
- autoGen wird nach JEDEM qualityGate-Durchlauf aufgerufen (wenn FAIL-Gates)
- autoGen hat KEIN eigenes MAX-ITERATIONS (Controller-Verantwortung)

### Chain-Integration
- ENTRY: qualityGate → autoGen (bei FAIL-Gates) ODER qualityGate → convergence (bei PASS)
- EXIT: autoGen → convergence (immer, nach Rewrites)
- ITERATE: convergence → write → visual → qualityGate → autoGen → convergence
- CONVERGE: convergence → review → synthesis → reflect

### MCP-Bremse
- Budget niedriger als write (lokaler Scope: nur FAIL-Sections)
- research_query_r2 weil Kapitel 2+ Kontext (W8)
- NON-BLOCKING: Rewrites sind auch ohne RAG moeglich (basierend auf Gate-Findings-Text)
- Budget-Exhaustion-Handler (M5): WARNUNG + Continue

### Difficulty-Scaling
- easy: 3 Sections max, 2 Queries/Section, Gates 3, Budget 6-10
- normal: 5 Sections max, 3 Queries/Section, Gates 5, Budget 15-20
- hard: 8 Sections max, 5 Queries/Section, Gates 8, Budget 40-50

### Referenzen
- Model: WritePaper_Model.md (W1 INNER-Loop, W3 VERTRAG, W5 QualityGates, W8 3-Collection, M4 Parallel-Spawning, M5 Budget-Exhaustion)
- Blueprint: /_WP_write.md (Worker-Pattern, RAG-Query-Muster)
- Input: /_WP_qualityGate.md (gap-autoGen.json Schema)
- Next: /_WP_convergence.md (CONVERGE/ITERATE/FORCE Decision)

---

**Command-Version:** 1.0.0
**Letzte Aenderung:** 2026-02-10
