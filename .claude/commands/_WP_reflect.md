# /_WP_reflect - Kapitel Retrospektive & OUTER-Loop Controller

```yaml
status: active
version: 1.0.0
created: 2026-02-10
op: WritePaper
phase: Core Transformation
type: Decision + MCP + HiL
chain_position: reflect
difficulty_scaling: true
mcp_critical: true
loop_controller: true
loop_level: OUTER
decision_type: true
```

---

```
+======================================================================+
| VERTRAG: /_WP_reflect                                               |
+======================================================================+
|                                                                        |
| ACTOR: KAPITEL-RETROSPEKTIVE + OUTER-LOOP CONTROLLER                   |
|   TUT:                                                                 |
|     - final-draft.md aus synthesis lesen (Kapitel-Inhalt)             |
|     - quality_history[] und convergence-decision.json analysieren      |
|     - review-summary.md lesen fuer Cross-Review-Insights              |
|     - Learnings extrahieren (3-7 Bullet Points basierend auf          |
|       difficulty)                                                      |
|     - research_mark_covered: Kapitel-Content in COVERED Collection    |
|       eintragen (MCP, 1 Call pro Kapitel)                              |
|     - HiL-PAUSE BLOCKING: User reviewt Kapitel-Summary               |
|       (Score, Iterations, Learnings)                                   |
|     - User-Decision verarbeiten: ACCEPT / RETRY / ABORT              |
|     - retry_count pruefen und bei RETRY inkrementieren               |
|     - reflection-report.json + kapitel-learnings.md generieren        |
|   NICHT:                                                               |
|     - Kapitel-Qualitaet bewerten (-> qualityGate, convergence)        |
|     - Drafts schreiben oder verbessern (-> write, autoGen)            |
|     - Figures generieren (-> visual)                                  |
|     - LaTeX/PDF Pipeline (-> finalize)                                |
|     - Research durchfuehren (-> research, discovery)                  |
|     - Drafts reviewen oder ranken (-> review)                         |
|   ESKALIERT:                                                           |
|     - User ABORT -> Pipeline STOP + NOTIFY Error                      |
|     - retry_count >= max -> FORCE ACCEPT + WARNUNG                    |
|     - final-draft.md fehlt -> BLOCKING + empfehle synthesis           |
|     - COVERED marking fehlgeschlagen -> NON-BLOCKING Warning          |
|       (weiter ohne COVERED, MCP-Problem dokumentiert)                  |
|                                                                        |
| LIEST (Input) - PFLICHT:                                               |
|   1. _manifest.md (current_chapter, phase, final_draft_path)         |
|   2. session-state.json (difficulty, retry_count, quality_history,    |
|      convergence_decision)                                             |
|   3. config/project.yaml (current_chapter, difficulty,                |
|      total_chapters)                                                   |
|   4. output/synthesis/chapter-{N}/final-draft.md                      |
|      (Kapitel-Inhalt fuer COVERED + Summary)                          |
|   5. output/synthesis/chapter-{N}/merge-report.json                   |
|      (Stats: word_count, citations, warnings)                         |
|   6. output/quality/chapter-{N}/convergence-decision.json             |
|      (Decision, quality_history, stagnation)                           |
|   7. output/reviews/chapter-{N}/review-summary.md                     |
|      (Peer-Review-Insights)                                            |
|                                                                        |
| SCHREIBT (Output) - PFLICHT:                                           |
|   1. output/reflection/chapter-{N}/reflection-report.json             |
|   2. output/reflection/chapter-{N}/kapitel-learnings.md               |
|   3. _manifest.md (UPDATE: reflection_decision, retry_count,          |
|      next_step, learnings_path)                                        |
|   4. session-state.json (UPDATE: retry_count, reflection_decision,    |
|      learnings, covered_status, next_chapter|phase=ABORTED)           |
|                                                                        |
| POSITION:                                                              |
|   TYPE: LOOP                                                           |
|   LOOP-CONTEXT:                                                        |
|     LOOP-NAME: Retry-Loop                                              |
|     LOOP-LEVEL: OUTER                                                  |
|     ITERATION-VARIABLE: retry_count                                    |
|     MAX-ITERATIONS: 1 (easy) | 2 (normal) | 3 (hard)                 |
|   ENTRY:                                                               |
|     NORMAL: /_WP_chapterPDF -> THIS (PDF generiert + gesendet)     |
|   EXIT:                                                                |
|     ACCEPT: THIS -> /_WP_write (chapter N+1)                       |
|     ACCEPT (letztes Kapitel): THIS -> /_WP_finalize                 |
|     RETRY: THIS -> /_WP_write (chapter N, retry_count++)           |
|     ABORT: THIS -> STOP (phase=ABORTED)                               |
|   PHASE: Core Transformation                                          |
|   CHAIN: [synthesis] -> [chapterPDF] -> [reflect] -> [write(N+1)|finalize|STOP] |
|                                                                        |
| ORCHESTRIERT: N/A (reflect ist Decision-Command, kein Orchestrator)   |
|                                                                        |
| ENTSCHEIDET:                                                           |
|   Decision-Table (Prioritaet D1 > D2 > D3 > D4):                     |
|   +----+----------------------------------------+----------------+    |
|   | #  | Bedingung                               | Decision       |    |
|   +----+----------------------------------------+----------------+    |
|   | D1 | User waehlt ABORT in HiL               | ABORT -> STOP  |    |
|   | D2 | User RETRY AND retry_count < max        | RETRY -> write |    |
|   | D3 | User RETRY AND retry_count >= max       | FORCE ACCEPT   |    |
|   | D4 | User ACCEPT (oder Timeout)              | ACCEPT -> next |    |
|   +----+----------------------------------------+----------------+    |
|                                                                        |
| MCP-BREMSE:                                                            |
|   Tool: mcp__cleancoder__research_mark_covered                         |
|   Call-Limit: 1 pro Kapitel (KEINE Wiederholung bei Retry)            |
|   Parameter:                                                           |
|     project_path: "{project_path}"                                     |
|     content: final_draft_markdown_content                              |
|     round_number: current_chapter                                      |
|     description: "Kapitel {N} abgeschlossen: {chapter_title}"         |
|   KRITISCH: NON-BLOCKING (Fallback: weiter ohne COVERED marking)     |
|                                                                        |
| HiL-PAUSE:                                                             |
|   Trigger: IMMER (BLOCKING)                                           |
|   Optionen:                                                            |
|     [A] ACCEPT - Naechstes Kapitel (Default bei Timeout)              |
|     [R] RETRY  - Kapitel wiederholen (retry_count++)                  |
|     [X] ABORT  - Pipeline stoppen                                     |
|   Timeout: 5 min (easy) | 10 min (normal) | 15 min (hard)            |
|   Default: ACCEPT                                                      |
|   Status: BLOCKING (Pipeline wartet auf User-Input)                   |
|                                                                        |
| SCHWIERIGKEIT:                                                         |
|   | Dimension       | easy | normal | hard |                          |
|   |-----------------|------|--------|------|                          |
|   | max_retry       | 1    | 2      | 3    |                          |
|   | learnings_depth | 3    | 5      | 7    |                          |
|   | HiL-Timeout     | 5min | 10min  | 15min|                          |
|                                                                        |
| NOTIFY:                                                                |
|   ACCEPT:  "Kapitel {N} ACCEPTED: {words} words, {cites} cites"      |
|   RETRY:   "Kapitel {N} RETRY {count}/{max}: User-requested"         |
|   FORCE:   "Kapitel {N} FORCE ACCEPT: Max Retries ({max})"           |
|   ABORT:   "WritePaper ABORTED by User at Kapitel {N}"               |
|   COVERED: "Kapitel {N}: COVERED marking {OK|FAILED}"                |
|                                                                        |
| TAGS:                                                                  |
|   type: reflect                                                        |
|   op: WritePaper                                                       |
|   chapter: {N}                                                         |
|   chain-position: reflect                                              |
|   loop-level: OUTER                                                    |
|   loop-controller: true                                                |
|   decision-type: true                                                  |
+======================================================================+
```

---

## Verantwortlichkeit

**TUT (Claude):**
- Liest final-draft.md fuer Kapitel-Inhalt und Summary-Daten
- Liest convergence-decision.json fuer Quality-History und Loop-Verlauf
- Liest review-summary.md fuer Cross-Review-Insights
- Liest merge-report.json fuer Word-Count, Citations, Warnings
- Extrahiert Learnings (3-7 Bullet Points je nach difficulty)
- Ruft research_mark_covered auf (MCP): Kapitel-Content → COVERED Collection
- Erstellt Kapitel-Summary fuer User-Review
- Zeigt HiL-PAUSE BLOCKING: User waehlt ACCEPT/RETRY/ABORT
- Verarbeitet User-Decision und routet Pipeline entsprechend
- Prueft retry_count gegen max (FORCE ACCEPT wenn Limit erreicht)
- Generiert reflection-report.json und kapitel-learnings.md
- Aktualisiert _manifest.md und session-state.json nach M6 Reihenfolge

**TUT NICHT (Claude):**
- Kapitel-Qualitaet bewerten (→ `/_WP_qualityGate`, `/_WP_convergence`)
- Drafts schreiben oder verbessern (→ `/_WP_write`, `/_WP_autoGen`)
- Figures generieren oder reviewen (→ `/_WP_visual`)
- LaTeX/PDF Pipeline (→ `/_WP_finalize`)
- Research oder Discovery (→ `/_WP_research`, `/_WP_discovery`)
- Drafts reviewen oder ranken (→ `/_WP_review`)

**ESKALATION:**
- User waehlt ABORT → Pipeline STOP + NOTIFY Error + phase=ABORTED
- retry_count >= max UND User waehlt RETRY → FORCE ACCEPT + WARNUNG
- final-draft.md fehlt → BLOCKING STOP + empfehle `/_WP_synthesis` erneut
- COVERED marking fehlschlaegt → NON-BLOCKING Warning + weiter ohne COVERED
- convergence-decision.json fehlt → WARNUNG + Learnings aus merge-report.json allein
- review-summary.md fehlt → WARNUNG + Learnings ohne Review-Insights

---

## Ablauf

### Schritt 0: Inputs lesen

**Ziel:** Kapitel-Ergebnis und History-Daten laden

**Aktionen:**
1. Lies `_manifest.md` → `current_chapter`, `phase`, `final_draft_path`
2. Lies `session-state.json`:
   - `difficulty` (easy|normal|hard)
   - `retry_count` (Default: 0)
   - `quality_history` (Array mit Scores)
   - `convergence_decision` (CONVERGE|FORCE)
3. Lies `config/project.yaml` → `current_chapter`, `total_chapters` (Default: 5)
4. Lies `output/synthesis/chapter-{N}/final-draft.md` → Kapitel-Content
5. Lies `output/synthesis/chapter-{N}/merge-report.json` → Stats
6. Lies `output/quality/chapter-{N}/convergence-decision.json` → Quality-History
7. Lies `output/reviews/chapter-{N}/review-summary.md` → Review-Insights

**Validierung:**
- final-draft.md MUSS existieren → sonst BLOCKING STOP
- difficulty MUSS gesetzt sein → sonst Default: normal
- retry_count fehlt → Default: 0 (erste Reflection)

**Erfolgskriterium:**
- Kapitel-Content geladen
- Quality-History und Convergence-Decision verfuegbar
- Difficulty und retry_count bestimmt

---

### Schritt 1: Kapitel-Summary erstellen

**Ziel:** Kompakte Zusammenfassung des Kapitel-Ergebnisses

**Aktionen:**
1. Extrahiere Stats aus final-draft.md Frontmatter + merge-report.json:
   - word_count, citations, figures, missing_figures, warnings

2. Extrahiere Quality-Verlauf aus convergence-decision.json:
   - quality_iterations, composite_score, delta_history
   - convergence_decision (CONVERGE vs FORCE)

3. Bestimme max_retry aus difficulty:
   - easy: 1, normal: 2, hard: 3

4. Erstelle Summary-Block:
   ```
   KAPITEL {N} REFLECTION - User Review
   =====================================
   Titel: {chapter_title}
   Status: {convergence_decision} (Score {composite}/10)
   Quality-Iterations: {quality_iteration}/{max}
   Retry-Count: {retry_count}/{max_retry}
   Word-Count: {word_count} (Target: 6250-8750)
   Citations: {citations} ({density}/page)
   Figures: {figures} ({missing} missing)
   Warnings: {warnings_count}
   ```

**Erfolgskriterium:**
- Summary-Block mit allen relevanten Metriken erstellt
- Convergence-Decision korrekt angezeigt

---

### Schritt 2: Learnings extrahieren

**Ziel:** Actionable Learnings fuer naechstes Kapitel

**Aktionen:**
1. Bestimme `learnings_depth` aus difficulty:
   - easy: 3 Learnings
   - normal: 5 Learnings
   - hard: 7 Learnings

2. Analysiere quality_history[]:
   - Welche Gates waren durchgehend FAIL?
   - Welche Gates verbesserten sich am meisten?
   - Stagnation-Muster? (delta < epsilon)

3. Analysiere review-summary.md:
   - Recurring Feedback-Themes?
   - Consensus vs Dissent (bei hard)?

4. Analysiere merge-report.json:
   - Word-Count vs Target (zu kurz/lang)?
   - Missing Figures?
   - Citation-Density vs Requirement?

5. Formuliere Learnings als Bullet Points:
   ```markdown
   ## Learnings aus Kapitel {N}

   1. **Citations:** Gate G5 war in 3/4 Iterationen FAIL.
      → Naechstes Kapitel: Mehr RAG-Queries fuer Citation-Density
   2. **Word-Count:** {word_count} unter Target (6250 min).
      → Naechstes Kapitel: Agents mehr Content generieren lassen
   3. **Convergence:** Score stagnierte bei Iter 2-3 (Delta 0.2).
      → Naechstes Kapitel: Fruehzeitig Stagnation erkennen
   ```

**Erfolgskriterium:**
- {learnings_depth} Learnings extrahiert
- Jedes Learning hat konkrete Aktion ("→ Naechstes Kapitel: ...")
- Learnings basieren auf messbaren Daten (Scores, Counts)

---

### Schritt 3: COVERED Collection markieren (MCP)

**Ziel:** Kapitel-Content in COVERED Collection eintragen

**Aktionen:**
1. Extrahiere Markdown-Content aus final-draft.md (ohne Frontmatter)

2. MCP-Aufruf:
   ```python
   result = await mcp__cleancoder__research_mark_covered(
       project_path="{project_path}",
       content=final_draft_markdown_content,
       round_number=current_chapter,
       description="Kapitel {N} abgeschlossen: {chapter_title}"
   )
   ```

3. Verarbeite Ergebnis:
   - Status "completed" → covered_status = "OK"
   - Status "failed" → covered_status = "FAILED" + WARNUNG

4. Fallback bei MCP-Fehler:
   - NON-BLOCKING Warning
   - covered_status = "FAILED"
   - NOTIFY Warning: "COVERED marking fehlgeschlagen"
   - Pipeline WEITER (degradiert: keine Anti-Wiederholung in naechstem Kapitel)

**Erfolgskriterium:**
- research_mark_covered aufgerufen (1 Call)
- covered_status dokumentiert (OK oder FAILED)
- Bei Fehler: Pipeline laeuft weiter (NON-BLOCKING)

---

### Schritt 4: HiL-PAUSE (User Review)

**Ziel:** User entscheidet ueber Kapitel-Ergebnis

**Aktionen:**
1. Zeige Kapitel-Summary (aus Schritt 1):
   ```
   KAPITEL {N} REFLECTION - User Review
   =====================================
   Titel: {chapter_title}
   Status: {convergence_decision} (Score {composite}/10)
   Quality-Iterations: {quality_iteration}/{max}
   Retry-Count: {retry_count}/{max_retry}
   Word-Count: {word_count} (Target: 6250-8750)
   Citations: {citations} ({density}/page)
   Figures: {figures} ({missing} missing)
   COVERED: {covered_status}

   LEARNINGS:
   - {Learning 1}
   - {Learning 2}
   - {Learning 3}
   [...]

   Optionen:
     [A] ACCEPT - Naechstes Kapitel (oder finalize bei letztem)
     [R] RETRY  - Kapitel wiederholen (retry_count: {count}/{max})
     [X] ABORT  - Pipeline stoppen
   ```

2. Warte auf User-Input (AskUserQuestion):
   - Timeout: 5|10|15 min (difficulty-abhaengig)
   - Default bei Timeout: ACCEPT

3. Dokumentiere HiL-Response:
   - hil_response: "ACCEPT" | "RETRY" | "ABORT" | "TIMEOUT_DEFAULT_ACCEPT"

**Erfolgskriterium:**
- Summary angezeigt mit allen Metriken und Learnings
- User-Input empfangen (oder Timeout → Default ACCEPT)
- hil_response dokumentiert

---

### Schritt 5: Decision verarbeiten

**Ziel:** Pipeline-Routing basierend auf User-Decision

**Aktionen:**

#### D1: ABORT (User waehlt ABORT)
```
next_step = "STOPPED"
phase = "ABORTED"
NOTIFY: "WritePaper ABORTED by User at Kapitel {N}. Pipeline STOPPED."
```

#### D2: RETRY (User waehlt RETRY AND retry_count < max)
```
retry_count += 1
next_step = "/_WP_write(chapter={N})"
decision = "RETRY"
NOTIFY: "Kapitel {N} RETRY {retry_count}/{max}: User-requested."
```

#### D3: FORCE ACCEPT (User waehlt RETRY AND retry_count >= max)
```
decision = "FORCE_ACCEPT"
WARNUNG: "Max Retries erreicht ({max}). FORCE ACCEPT."
→ Routing wie D4 (ACCEPT), aber mit WARNUNG
```

#### D4: ACCEPT (User waehlt ACCEPT oder Timeout)
```
IF current_chapter < total_chapters:
    next_step = "/_WP_write(chapter={N+1})"
    next_chapter = current_chapter + 1
ELSE:
    next_step = "/_WP_finalize"
    next_chapter = null
decision = "ACCEPT"
NOTIFY: "Kapitel {N} ACCEPTED: {word_count} words, {citations} cites."
```

**Prioritaet:** D1 > D2 > D3 > D4

**Erfolgskriterium:**
- Genau 1 Decision getroffen
- next_step korrekt gesetzt
- retry_count korrekt verwaltet

---

### Schritt 6: Output generieren

**Ziel:** Reflection-Ergebnis persistent speichern

#### 6a: reflection-report.json

Schreibe `output/reflection/chapter-{N}/reflection-report.json`:

```json
{
  "chapter": 1,
  "difficulty": "hard",
  "timestamp": "2026-02-10T14:00:00Z",
  "retry_count": 0,
  "max_retry": 3,
  "convergence_decision": "CONVERGE",
  "composite_score": 7.8,
  "quality_iterations": 2,
  "word_count": 7200,
  "citations": 45,
  "figures": 4,
  "missing_figures": 1,
  "covered_status": "OK",
  "covered_chunks_created": 12,
  "hil_response": "ACCEPT",
  "decision": "ACCEPT",
  "next_step": "/_WP_write(chapter=2)",
  "learnings": [
    "Gate G5 Citations FAIL in 3/4 Iterationen → mehr RAG-Queries",
    "Word-Count 7200 im Target-Bereich (6250-8750) → beibehalten",
    "Stagnation bei Iter 2-3 (Delta 0.2) → fruehzeitig erkennen"
  ]
}
```

#### 6b: kapitel-learnings.md

Schreibe `output/reflection/chapter-{N}/kapitel-learnings.md`:

```markdown
# Learnings aus Kapitel {N}: {Titel}

**Datum:** {timestamp}
**Score:** {composite}/10 ({convergence_decision})
**Iterations:** {quality_iterations}/{max}
**Retries:** {retry_count}/{max_retry}

## Erkenntnisse

1. **Citations:** Gate G5 war in 3/4 Iterationen FAIL.
   → Naechstes Kapitel: Mehr RAG-Queries fuer Citation-Density

2. **Word-Count:** 7200 Worte im Target-Bereich (6250-8750).
   → Naechstes Kapitel: Aktuelle Strategie beibehalten

3. **Convergence:** Score stagnierte bei Iter 2-3 (Delta 0.2).
   → Naechstes Kapitel: Fruehzeitig Stagnation erkennen

## Empfehlungen fuer Kapitel {N+1}

- Agent-Anzahl: {empfehlung basierend auf Learnings}
- RAG-Fokus: {empfehlung basierend auf Gate-Schwaechen}
- Vermeiden: {Pattern das in diesem Kapitel problematisch war}
```

**Erfolgskriterium:**
- reflection-report.json mit allen Feldern geschrieben
- kapitel-learnings.md mit actionable Learnings geschrieben

---

### Schritt 7: State aktualisieren (M6 Reihenfolge)

**Aktionen:**

#### 7a. OUTPUT (bereits in Schritt 6)
- reflection-report.json
- kapitel-learnings.md

#### 7b. _manifest.md UPDATE

```markdown
## Reflection - Kapitel {N}
- **Decision:** ACCEPT | RETRY | FORCE_ACCEPT | ABORT
- **Score:** {composite}/10 ({convergence_decision})
- **Retry-Count:** {retry_count}/{max_retry}
- **COVERED:** {OK|FAILED}
- **Learnings:** {count} extrahiert
- **Next Step:** write(N+1) | finalize | STOPPED
```

#### 7c. session-state.json UPDATE

```json
{
  "last_command": "_WP_reflect",
  "reflection_decision": "ACCEPT|RETRY|FORCE_ACCEPT|ABORT",
  "retry_count": 0,
  "covered_status": "OK",
  "learnings_path": "output/reflection/chapter-{N}/kapitel-learnings.md",
  "current_chapter": 2,
  "next_step": "/_WP_write(chapter=2)"
}
```

#### 7d. NOTIFY

**ACCEPT:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} ACCEPTED: {word_count} words, {citations} cites. Next: {next_step}'"
```

**RETRY:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} RETRY {retry_count}/{max}: User-requested. Next: write(chapter={N})'"
```

**FORCE ACCEPT:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} FORCE ACCEPT: Max Retries erreicht ({max}). Next: {next_step}'"
```

**ABORT:**
```powershell
powershell -Command "notify 'WritePaper ABORTED by User at Kapitel {N}. Pipeline STOPPED.'"
```

**Erfolgskriterium:**
- _manifest.md und session-state.json aktualisiert
- NOTIFY gesendet mit Decision-spezifischer Nachricht

---

## Decision-Table (Referenz)

| # | User-Input | retry_count vs max | Decision | Next Step | Bemerkung |
|---|-----------|-------------------|----------|-----------|-----------|
| D1 | ABORT | any | **ABORT** | STOP | Pipeline-Abbruch |
| D2 | RETRY | < max | **RETRY** | write(N) | Kapitel wiederholen |
| D3 | RETRY | >= max | **FORCE ACCEPT** | write(N+1) or finalize | Max Retries, WARNUNG |
| D4 | ACCEPT (or Timeout) | any | **ACCEPT** | write(N+1) or finalize | Kapitel abgeschlossen |

**Prioritaet:** D1 > D2 > D3 > D4

**Nachgelagerte Routing:**
- ACCEPT + current_chapter < total_chapters → `/_WP_write(chapter={N+1})`
- ACCEPT + current_chapter == total_chapters → `/_WP_finalize`
- RETRY → `/_WP_write(chapter={N})`, retry_count++
- ABORT → STOPPED, phase=ABORTED

---

## Output-Format

### output/reflection/chapter-{N}/reflection-report.json

**Zweck:** Persistente Reflection-Daten fuer Traceability

**Schema:**
```json
{
  "chapter": 1,
  "difficulty": "hard",
  "timestamp": "2026-02-10T14:00:00Z",
  "retry_count": 0,
  "max_retry": 3,
  "convergence_decision": "CONVERGE",
  "composite_score": 7.8,
  "quality_iterations": 2,
  "word_count": 7200,
  "citations": 45,
  "figures": 4,
  "missing_figures": 1,
  "covered_status": "OK|FAILED",
  "covered_chunks_created": 12,
  "covered_error": null,
  "hil_response": "ACCEPT|RETRY|ABORT|TIMEOUT_DEFAULT_ACCEPT",
  "decision": "ACCEPT|RETRY|FORCE_ACCEPT|ABORT",
  "next_step": "/_WP_write(chapter=2)|/_WP_finalize|STOPPED",
  "learnings": ["..."]
}
```

**Konsumenten:**
- `/_WP_write(N+1)`: Liest kapitel-learnings.md fuer Agent-Prompts
- `/_WP_finalize`: Liest alle reflection-reports fuer Paper-Summary
- `/_WP_session`: Optional fuer Cross-Paper-Learnings

### output/reflection/chapter-{N}/kapitel-learnings.md

**Zweck:** Human-readable Learnings fuer naechstes Kapitel

**Konvention:**
- write(N+1) liest `output/reflection/chapter-{N}/kapitel-learnings.md`
- Learnings werden in Agent-Prompts integriert: "Aus Kapitel {N} lernen: {learnings}"
- Bei RETRY: write(N) liest EIGENE kapitel-learnings.md (reflexive Verbesserung)

---

## Qualitaetskriterien

### Vollstaendigkeit
- [ ] final-draft.md gelesen und Content extrahiert
- [ ] convergence-decision.json und review-summary.md analysiert
- [ ] Learnings extrahiert (3|5|7 basierend auf difficulty)
- [ ] research_mark_covered aufgerufen (1 Call)
- [ ] HiL-PAUSE BLOCKING durchgefuehrt
- [ ] User-Decision verarbeitet (ACCEPT/RETRY/ABORT)
- [ ] reflection-report.json geschrieben
- [ ] kapitel-learnings.md geschrieben
- [ ] _manifest.md und session-state.json aktualisiert
- [ ] NOTIFY gesendet

### Korrektheit
- [ ] Decision-Table Prioritaet: D1 > D2 > D3 > D4
- [ ] retry_count korrekt verwaltet (inkrementiert bei RETRY)
- [ ] max_retry aus difficulty (1|2|3)
- [ ] FORCE ACCEPT bei retry_count >= max
- [ ] HiL-Timeout aus difficulty (5|10|15 min)
- [ ] Default bei Timeout: ACCEPT
- [ ] COVERED marking NUR bei ACCEPT/FORCE (NICHT bei RETRY oder ABORT)
- [ ] Routing: write(N+1) bei ACCEPT + chapter < max, finalize bei letztem

### Robustheit
- [ ] final-draft.md fehlt → BLOCKING STOP
- [ ] COVERED marking fehlschlaegt → NON-BLOCKING Warning
- [ ] convergence-decision.json fehlt → WARNUNG + Learnings degradiert
- [ ] review-summary.md fehlt → WARNUNG + Learnings ohne Review
- [ ] retry_count fehlt in session-state → Default: 0
- [ ] HiL Timeout → Default: ACCEPT

### Performance
- [ ] Genau 1 MCP-Call (research_mark_covered)
- [ ] Keine redundanten Dateizugriffe
- [ ] HiL-Pause ist der einzige Warteblock

---

## NOTIFY

**ACCEPT:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} ACCEPTED: {word_count} words, {citations} cites. Next: Kapitel {N+1}'"
```

**RETRY:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} RETRY {retry_count}/{max}: User-requested. Next: write(chapter={N})'"
```

**FORCE ACCEPT:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} FORCE ACCEPT: Max Retries erreicht ({max}). Next: {next_step}'"
```

**ABORT:**
```powershell
powershell -Command "notify 'WritePaper ABORTED by User at Kapitel {N}. Pipeline STOPPED.'"
```

**COVERED Warning:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N}: COVERED marking fehlgeschlagen (MCP-Problem)'"
```

---

## Error Handling

| Kategorie | Trigger | Response | NOTIFY |
|-----------|---------|----------|--------|
| BLOCKING | final-draft.md fehlt | STOP + empfehle /_WP_synthesis | ERROR |
| BLOCKING | User ABORT | STOP + phase=ABORTED | ERROR |
| NON-BLOCKING | COVERED marking fehlschlaegt | Continue + covered_status=FAILED | WARNING |
| NON-BLOCKING | convergence-decision.json fehlt | Learnings degradiert (nur merge-report) | WARNING |
| NON-BLOCKING | review-summary.md fehlt | Learnings ohne Review-Insights | WARNING |
| FALLBACK | retry_count fehlt in session-state | Default: 0 | INFO |
| FALLBACK | HiL Timeout | Default: ACCEPT | INFO |
| FALLBACK | total_chapters fehlt in project.yaml | Default: 5 | INFO |

---

## Hinweise

### OUTER-Loop Controller
- reflect ist der OUTER-Level Controller (W1): Entscheidet ob Kapitel wiederholt wird
- INNER-Loop Controller: /_WP_convergence (Quality-Loop)
- MIDDLE-Loop Controller: /_WP_chapterGap (Gap-Loop)
- reflect operiert NACH dem vollstaendigen INNER+MIDDLE-Loop

### COVERED Collection (W8)
- research_mark_covered speist Kapitel-Content in COVERED Collection
- write(N+1) nutzt research_query_r2 mit COVERED-Penalty (0.7)
- Effekt: Keine thematische Wiederholung zwischen Kapiteln
- Bei COVERED-Fehler: Pipeline degradiert (Wiederholungen moeglich)
- COVERED wird NUR bei ACCEPT/FORCE markiert (nicht bei RETRY)

### HiL-PAUSE ist BLOCKING
- Im Gegensatz zu convergence (HiL OPTIONAL bei FORCE): reflect HiL ist IMMER BLOCKING
- User MUSS nach jedem Kapitel eingreifen (oder Timeout abwarten)
- Begruendung: W1 fordert "Kapitel-fuer-Kapitel" mit User-Review

### Learnings-Uebergabe
- kapitel-learnings.md wird von write(N+1) in Schritt 0 gelesen
- Learnings fliessen in Agent-Prompts ein: "Aus Kapitel {N-1} lernen: ..."
- Bei RETRY: write(N) liest EIGENE kapitel-learnings.md
- Learnings sind difficulty-skaliert (3|5|7 Bullet Points)

### retry_count Management
- retry_count wird bei RETRY inkrementiert
- Bei ACCEPT/FORCE: retry_count bleibt (wird in reflection-report.json dokumentiert)
- Bei naechstem Kapitel: retry_count wird auf 0 zurueckgesetzt
- Persistenz: session-state.json + reflection-report.json (2-fach)

### Chain-Integration
- ENTRY: chapterPDF → reflect (PDF generiert + gesendet)
- EXIT ACCEPT: reflect → write(N+1) (naechstes Kapitel)
- EXIT ACCEPT (letztes Kapitel): reflect → finalize
- EXIT RETRY: reflect → write(N) (Kapitel wiederholen)
- EXIT ABORT: reflect → STOP

### Referenzen
- Model: WritePaper_Model.md (W1 OUTER-Loop, W6 Drei-State, W8 COVERED, W9 HiL)
- Blueprint: /_WP_convergence.md (Decision-Type, Loop-Controller, HiL Pattern)
- Previous: /_WP_chapterPDF.md (PDF Generation + Email)
- Previous (indirect): /_WP_synthesis.md (final-draft.md Input)
- Next ACCEPT: /_WP_write.md (naechstes Kapitel)
- Next finalize: /_WP_finalize (letztes Kapitel)

---

**Command-Version:** 1.0.0
**Letzte Aenderung:** 2026-02-10
