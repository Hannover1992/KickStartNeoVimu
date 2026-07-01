# /_WP_chapterGap - Chapter Gap Analysis & Decision

```yaml
status: active
version: 1.0.0
created: 2026-02-08
op: WritePaper
phase: Knowledge
type: building-block
chain_position: chapterGap
difficulty_scaling: true
mcp_critical: true
loop_controller: true
loop_level: MIDDLE
```

---

```
╔══════════════════════════════════════════════════════════════════════════╗
║ VERTRAG: /_WP_chapterGap                                              ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ ACTOR: GAP DETECTOR                                                      ║
║   TUT:                                                                   ║
║     - Chapter-Model gegen Section-Coverage pruefen                      ║
║     - Coverage pro Section bewerten (COVERED/PARTIAL/MISSING)           ║
║     - Gap-Liste erstellen mit Deficit-Keywords                          ║
║     - Decision treffen: PASS / GAP / FORCE                              ║
║     - Optional: MCP research_gaps fuer Re-Check (bei Loop-Iteration)   ║
║   NICHT:                                                                 ║
║     - Luecken fuellen (→ research + discovery)                           ║
║     - Neue Quellen suchen (→ discovery)                                  ║
║     - Kapitel schreiben (→ write)                                        ║
║     - Wissens-Model erstellen (→ chapterModel)                          ║
║     - Assessment durchfuehren (→ assess)                                ║
║                                                                          ║
║ LIEST (Input) - PFLICHT:                                                 ║
║   1. _manifest.md (current_chapter, phase)                               ║
║   2. session-state.json (coverage_score, research_budget_remaining,     ║
║      gap_research_count)                                                 ║
║   3. output/models/chapter-{N}-model.md (Themen, Keywords, Coverage)   ║
║   4. output/assess/chapter-{N}-assessment.json (Detail-Daten)           ║
║                                                                          ║
║ SCHREIBT (Output) - PFLICHT:                                             ║
║   1. output/assess/chapter-{N}-gaps.json (Gap-Liste, Decision)          ║
║   2. _manifest.md (UPDATE: next_step=research|write, gap_decision)      ║
║   3. session-state.json (UPDATE: gap_research_count, gap_decision)      ║
║                                                                          ║
║ POSITION:                                                                ║
║   TYPE: LOOP                                                             ║
║   LOOP-CONTEXT:                                                          ║
║     LOOP-NAME: Gap-Loop                                                  ║
║     LOOP-LEVEL: MIDDLE                                                   ║
║     ITERATION-VARIABLE: gap_research_count                               ║
║     MAX-ITERATIONS: 3 (danach FORCE)                                    ║
║   ENTRY:                                                                 ║
║     NORMAL: /_WP_chapterModel → THIS                                  ║
║   EXIT:                                                                  ║
║     PASS: THIS → /_WP_write (Coverage ausreichend)                    ║
║     GAP: THIS → /_WP_research (Luecken erkannt, Budget vorhanden)    ║
║     FORCE: THIS → /_WP_write (Budget erschoepft oder max Iterations) ║
║   PHASE: Knowledge                                                      ║
║   CHAIN: [chapterModel] → [chapterGap] → [research|write]              ║
║                                                                          ║
║ ENTSCHEIDET:                                                             ║
║   Decision-Table:                                                        ║
║   ┌────────────────────────────────────────┬──────────┬──────────────┐  ║
║   │ Bedingung                               │ Decision │ Next Step    │  ║
║   ├────────────────────────────────────────┼──────────┼──────────────┤  ║
║   │ coverage >= 0.85 AND gap_list == []    │ PASS     │ write        │  ║
║   │ coverage < 0.85 AND budget > 0         │ GAP      │ research     │  ║
║   │    AND gap_count < 3                    │          │              │  ║
║   │ coverage < 0.85 AND budget == 0        │ FORCE    │ write (WARN) │  ║
║   │ gap_count >= 3                          │ FORCE    │ write (WARN) │  ║
║   └────────────────────────────────────────┴──────────┴──────────────┘  ║
║                                                                          ║
║ MCP-BREMSE:                                                              ║
║   Tools: mcp__cleancoder__research_gaps                                  ║
║   Call-Limits: easy=3, normal=5, hard=10                                 ║
║   KRITISCH: OPTIONAL (nur bei Re-Check nach Loop-Iteration)            ║
║                                                                          ║
║ SCHWIERIGKEIT:                                                           ║
║   easy:   min_coverage=2, max 3 MCP-Calls                              ║
║   normal: min_coverage=3, max 5 MCP-Calls                              ║
║   hard:   min_coverage=5, max 10 MCP-Calls                             ║
║                                                                          ║
║ NOTIFY:                                                                  ║
║   powershell -Command "notify 'WritePaper Kapitel {N} Gap-Decision:     ║
║   {PASS|GAP|FORCE}'"                                                    ║
║                                                                          ║
║ TAGS:                                                                    ║
║   type: chapterGap                                                       ║
║   op: WritePaper                                                         ║
║   chapter: {N}                                                           ║
║   chain-position: chapterGap                                             ║
║   loop-level: MIDDLE                                                     ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

**TUT (Claude):**
- Liest chapter-{N}-model.md fuer Themen, Keywords, Coverage pro Section
- Bewertet Section-Coverage gegen min_coverage Schwelle
- Erstellt Gap-Liste mit Sections unter Schwelle + Deficit-Keywords
- Evaluiert Decision-Table (PASS/GAP/FORCE)
- Optional: Ruft research_gaps auf fuer erneute Coverage-Analyse (bei Loop-Iteration)
- Generiert chapter-{N}-gaps.json mit Decision + Gap-Details
- Aktualisiert _manifest.md und session-state.json

**TUT NICHT (Claude):**
- Luecken fuellen oder neue Quellen suchen (→ `/_WP_research` + `/_WP_discovery`)
- Kapitel-Text schreiben (→ `/_WP_write`)
- Wissens-Model aktualisieren (→ `/_WP_chapterModel`)
- Assessment wiederholen (→ `/_WP_assess`)
- RAG-Collection modifizieren

**ESKALATION:**
- chapter-{N}-model.md fehlt → STOP + empfehle `/_WP_chapterModel` zuerst
- assessment.json fehlt → STOP + empfehle `/_WP_assess` zuerst
- MCP research_gaps fehlschlaegt → NON-BLOCKING, nutze lokale Daten
- Coverage == 0.0 (keine Chunks) → WARNUNG "Keine Quellenabdeckung" + FORCE Decision

---

## Ablauf

### Schritt 0: Inputs lesen

**Ziel:** Alle Model- und Assessment-Daten laden

**Aktionen:**
1. Lies `_manifest.md` → `current_chapter`, `phase`, `next_step`
2. Lies `session-state.json`:
   - `coverage_score` (aus letztem assess)
   - `research_budget_remaining` (verbleibendes MCP-Budget)
   - `gap_research_count` (bisherige Gap-Loop-Iterationen, Default: 0)
3. Lies `output/models/chapter-{N}-model.md` → Themen, Keywords, Section-Coverage
4. Lies `output/assess/chapter-{N}-assessment.json` → Detail-Daten pro Keyword

**Validierung:**
- `next_step` muss `chapterGap` sein → sonst FEHLER
- `model_complete` muss `true` sein → sonst FEHLER
- chapter-{N}-model.md muss existieren → sonst FEHLER

**Erfolgskriterium:**
- Alle 4 Input-Dateien gelesen
- coverage_score, budget, gap_count bekannt
- Model-Daten (Themen, Sections, Keywords) verfuegbar

---

### Schritt 1: Section-Coverage-Check

**Ziel:** Coverage pro Section gegen Schwelle pruefen

**Aktionen:**
1. Bestimme `min_coverage` aus `difficulty`:
   - easy: 2 Chunks
   - normal: 3 Chunks
   - hard: 5 Chunks
2. Pro Section in chapter-{N}-model.md:
   - Zaehle zugeordnete Keywords
   - Zaehle Chunks pro Keyword (aus assessment.json)
   - Berechne `section_coverage`:
     ```
     section_coverage = (Keywords mit >= min_coverage Chunks) / (Total Keywords in Section)
     ```
3. Klassifiziere Section-Status:
   - `section_coverage >= 0.85` → "COVERED"
   - `section_coverage >= 0.50` → "PARTIAL"
   - `section_coverage < 0.50` → "INSUFFICIENT"
4. Berechne `chapter_coverage` (Durchschnitt aller section_coverage)

**Ergebnis:**
```json
{
  "sections": [
    {"id": "1.1", "title": "Motivation", "coverage": 0.92, "status": "COVERED"},
    {"id": "1.2", "title": "Forschungsfragen", "coverage": 0.67, "status": "PARTIAL"},
    {"id": "1.3", "title": "Zielsetzung", "coverage": 0.45, "status": "INSUFFICIENT"},
    {"id": "1.4", "title": "Aufbau", "coverage": 1.00, "status": "COVERED"}
  ],
  "chapter_coverage": 0.76
}
```

**Erfolgskriterium:**
- Jede Section hat Coverage-Status
- chapter_coverage korrekt berechnet

---

### Schritt 2: Gap-Berechnung

**Ziel:** Sections mit unzureichender Coverage identifizieren

**Aktionen:**
1. Filtere Sections mit Status "PARTIAL" oder "INSUFFICIENT"
2. Pro Gap-Section: Identifiziere Deficit-Keywords:
   ```json
   {
     "section_id": "1.3",
     "section_title": "Zielsetzung",
     "section_coverage": 0.45,
     "status": "INSUFFICIENT",
     "deficit_keywords": [
       {"keyword": "research objectives", "chunks": 0, "required": 3, "deficit": 3},
       {"keyword": "scope definition", "chunks": 1, "required": 3, "deficit": 2}
     ],
     "total_deficit": 5
   }
   ```
3. Erstelle `gap_list` (sortiert nach total_deficit, hoechste zuerst)
4. Berechne `gap_severity`:
   - INSUFFICIENT Sections > 30% → "SEVERE"
   - INSUFFICIENT Sections 10-30% → "MODERATE"
   - Nur PARTIAL Sections → "MINOR"
   - Keine Gaps → "NONE"

**Erfolgskriterium:**
- Gap-Liste vollstaendig mit Deficit-Keywords
- Sortierung nach Deficit (hoechste zuerst)
- gap_severity berechnet

---

### Schritt 3: Optional MCP Re-Check (bei Loop-Iteration)

**Ziel:** Bei wiederholtem Durchlauf pruefen ob Discovery Luecken gefuellt hat

**Bedingung:** NUR ausfuehren wenn `gap_research_count > 0` (Loop-Iteration)

**Aktionen:**
1. Falls `gap_research_count > 0`:
   ```python
   gaps_result = await mcp__cleancoder__research_gaps(
       project_path="{project_path}",
       research_questions=[deficit_keyword for section in gap_list for deficit_keyword in section.deficit_keywords],
       options={
           "min_coverage": {min_coverage},
           "suggest_sources": True,
           "check_bibliography": True
       }
   )
   ```
2. Update `chapter_coverage` basierend auf MCP-Ergebnis
3. Update `gap_list` (Luecken die jetzt gefuellt sind → entfernen)
4. Tracke MCP-Call (Budget-Tracking)
5. Falls `gap_research_count == 0`: Skip diesen Schritt (erste Iteration, Daten aus assess genuegen)

**MCP-Budget-Tracking:**
- 1x research_gaps Call (nur bei Loop-Iteration)
- Budget: easy=3, normal=5, hard=10

**Erfolgskriterium:**
- Bei Loop-Iteration: Aktualisierte Coverage basierend auf neuen Quellen
- Bei erster Iteration: Skip (kein MCP-Verbrauch)

---

### Schritt 4: Decision-Logic

**Ziel:** Naechsten Schritt in der Pipeline bestimmen

**Aktionen:**
1. Evaluiere Decision-Table:

   | # | Bedingung | Decision | Next Step | Bemerkung |
   |---|-----------|----------|-----------|-----------|
   | D1 | chapter_coverage >= 0.85 AND len(gap_list) == 0 | **PASS** | write | Kapitel bereit zum Schreiben |
   | D2 | chapter_coverage < 0.85 AND budget > 0 AND gap_count < 3 | **GAP** | research | Loop zurueck zu research→discovery→assess→chapterModel |
   | D3 | chapter_coverage < 0.85 AND budget == 0 | **FORCE** | write | Schreiben mit Luecken (Budget erschoepft) |
   | D4 | gap_count >= 3 | **FORCE** | write | Schreiben mit Luecken (Max Iterations) |

2. **Prioritaet:** D4 vor D3 vor D2 vor D1 (FORCE-Bedingungen zuerst pruefen)

3. Setze `gap_decision` und `next_step`

4. Bei **PASS:**
   - next_step = "write"
   - Nachricht: "Coverage ausreichend ({X}%). Bereit zum Schreiben."

5. Bei **GAP:**
   - next_step = "research"
   - gap_research_count += 1
   - Nachricht: "Gap erkannt ({Y} Sections). Loop zurueck zu research (Iteration {Z})."

6. Bei **FORCE:**
   - next_step = "write"
   - gap_research_count = 0 (Reset)
   - WARNUNG: "Schreiben mit Luecken! Coverage {X}%, Budget={B}, Iterations={I}."

**Erfolgskriterium:**
- Genau 1 Decision getroffen (PASS, GAP, oder FORCE)
- next_step korrekt gesetzt
- WARNUNG bei FORCE

---

### Schritt 5: State aktualisieren

**Ziel:** Gap-Ergebnisse und Decision persistent speichern

**Aktionen:**
1. Schreibe `output/assess/chapter-{N}-gaps.json`:
   ```json
   {
     "chapter": 1,
     "gap_date": "2026-02-08T16:00:00Z",
     "difficulty": "normal",
     "min_coverage": 3,
     "chapter_coverage": 0.76,
     "gap_severity": "MODERATE",
     "gap_count": 2,
     "sections": [
       {
         "id": "1.1",
         "title": "Motivation",
         "coverage": 0.92,
         "status": "COVERED"
       },
       {
         "id": "1.2",
         "title": "Forschungsfragen",
         "coverage": 0.67,
         "status": "PARTIAL",
         "deficit_keywords": [
           {"keyword": "research gap", "chunks": 1, "required": 3, "deficit": 2}
         ]
       },
       {
         "id": "1.3",
         "title": "Zielsetzung",
         "coverage": 0.45,
         "status": "INSUFFICIENT",
         "deficit_keywords": [
           {"keyword": "research objectives", "chunks": 0, "required": 3, "deficit": 3},
           {"keyword": "scope definition", "chunks": 1, "required": 3, "deficit": 2}
         ]
       },
       {
         "id": "1.4",
         "title": "Aufbau",
         "coverage": 1.00,
         "status": "COVERED"
       }
     ],
     "decision": "GAP",
     "next_step": "research",
     "gap_research_count": 1,
     "research_budget_remaining": 18,
     "force_reason": null,
     "mcp_calls_used": 0
   }
   ```

2. Update `_manifest.md`:
   ```markdown
   ## Gap Decision - Kapitel {N}
   - **Decision:** GAP
   - **Coverage:** 0.76
   - **Gap Sections:** 2 (1.2 PARTIAL, 1.3 INSUFFICIENT)
   - **Loop Iteration:** 1
   - **Next Step:** research
   - **Budget Remaining:** 18 MCP-Calls
   ```

3. Update `session-state.json`:
   ```json
   {
     "last_command": "_WP_chapterGap",
     "gap_decision": "GAP",
     "chapter_coverage": 0.76,
     "gap_severity": "MODERATE",
     "gap_research_count": 1,
     "research_budget_remaining": 18,
     "next_step": "research"
   }
   ```

4. **NOTIFY:**
   ```powershell
   powershell -Command "notify 'WritePaper Kapitel {N} Gap-Decision: GAP (Coverage 76%, Iteration 1)'"
   ```

**Erfolgskriterium:**
- gaps.json vollstaendig geschrieben
- _manifest.md und session-state.json aktualisiert
- NOTIFY gesendet mit Decision

---

## Decision-Table (Referenz)

| # | Coverage | Budget | gap_count | Decision | Next Step | Bemerkung |
|---|----------|--------|-----------|----------|-----------|-----------|
| D1 | >= 0.85 AND no gaps | any | any | **PASS** | write | Kapitel bereit |
| D2 | < 0.85 | > 0 | < 3 | **GAP** | research | Loop-Iteration |
| D3 | < 0.85 | == 0 | any | **FORCE** | write | Budget erschoepft |
| D4 | any | any | >= 3 | **FORCE** | write | Max Iterations erreicht |

**Prioritaet:** D4 > D3 > D2 > D1

**Loop-Flow bei GAP:**
```
chapterGap → research → discovery → assess → chapterModel → chapterGap
     ↑                                                           │
     └───────────────── GAP (Loop zurueck) ──────────────────────┘
```

**Exit bei PASS oder FORCE:**
```
chapterGap → write (PASS: Coverage gut, FORCE: Budget/Iterations erschoepft)
```

---

## Output-Format

### output/assess/chapter-{N}-gaps.json

**Zweck:** Gap-Analyse-Ergebnis mit Decision fuer Pipeline-Steuerung

**Schema:**
```json
{
  "chapter": 1,
  "gap_date": "2026-02-08T16:00:00Z",
  "difficulty": "normal",
  "min_coverage": 3,
  "chapter_coverage": 0.76,
  "gap_severity": "MODERATE|SEVERE|MINOR|NONE",
  "gap_count": 2,
  "sections": [
    {
      "id": "1.1",
      "title": "Section Titel",
      "coverage": 0.92,
      "status": "COVERED|PARTIAL|INSUFFICIENT",
      "deficit_keywords": []
    }
  ],
  "decision": "PASS|GAP|FORCE",
  "next_step": "write|research",
  "gap_research_count": 1,
  "research_budget_remaining": 18,
  "force_reason": "null|budget_exhausted|max_iterations",
  "mcp_calls_used": 0
}
```

**Konsumenten:**
- `/_WP_research`: Nutzt deficit_keywords fuer gezielte Quellen-Suche
- `/_WP_write`: Liest gap_severity fuer Schreib-Strategie (bei FORCE: Luecken markieren)

---

## Qualitaetskriterien

### Vollstaendigkeit
- [ ] Alle Sections im chapter-{N}-model.md bewertet
- [ ] Jede Section hat Coverage-Score und Status
- [ ] Gap-Liste mit allen Deficit-Keywords erstellt
- [ ] Decision getroffen (PASS, GAP, oder FORCE)
- [ ] gaps.json geschrieben
- [ ] _manifest.md und session-state.json aktualisiert

### Korrektheit
- [ ] chapter_coverage = Durchschnitt(section_coverage)
- [ ] min_coverage basiert auf difficulty (2|3|5)
- [ ] Decision-Table korrekt evaluiert (Prioritaet: D4 > D3 > D2 > D1)
- [ ] gap_research_count korrekt (Increment bei GAP, Reset bei FORCE)
- [ ] MCP-Budget korrekt reduziert (nur bei Loop-Iteration MCP-Call)

### Robustheit
- [ ] MCP research_gaps Fehler → NON-BLOCKING, lokale Daten nutzen
- [ ] Coverage == 0 → FORCE Decision (nicht endloser Loop)
- [ ] gap_count >= 3 → FORCE (Hard-Limit verhindert endlosen Loop)
- [ ] Budget == 0 → FORCE (kein unendlicher Loop bei leerem Budget)

### Performance
- [ ] MCP-Call nur bei Loop-Iteration (gap_research_count > 0)
- [ ] Erste Iteration: Kein MCP-Verbrauch (Daten aus assess genuegen)
- [ ] Decision-Logic O(n) ueber Sections (nicht quadratisch)

---

## NOTIFY

**PASS:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Gap-Decision: PASS (Coverage {X}%)'"
```

**GAP:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Gap-Decision: GAP (Coverage {X}%, Iteration {Z})'"
```

**FORCE:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Gap-Decision: FORCE (Coverage {X}%, Grund: {Reason})'"
```

**Error:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Gap-Decision FAILED: Model fehlt'"
```

---

## Error Handling

- chapter-{N}-model.md fehlt → BLOCKING STOP + ESKALATION, empfehle /_WP_chapterModel
- assessment.json fehlt → BLOCKING STOP + ESKALATION, empfehle /_WP_assess
- MCP research_gaps fehlschlaegt → NON-BLOCKING, nutze lokale Daten aus assessment.json
- Coverage == 0.0 → FORCE Decision + WARNUNG "Keine Quellenabdeckung"
- session-state.json fehlt gap_research_count → Default: 0 (erste Iteration)
- research_budget_remaining undefiniert → Default: 0 (FORCE)

---

## Hinweise

### Loop-Controller
- chapterGap ist der MIDDLE-Level Controller fuer den Gap-Loop (W1)
- OUTER-Loop (Retry): Controller ist /_WP_reflect
- INNER-Loop (Quality): Controller ist /_WP_convergence
- Max 3 Gap-Loop-Iterationen (D4 FORCE-Bedingung)

### Budget-Schonung
- Erster Durchlauf (gap_count=0): KEIN MCP-Call (Daten aus assess)
- Loop-Iterationen (gap_count>0): 1x research_gaps (Re-Check)
- Hauptbudget wird von research + discovery verbraucht, NICHT von chapterGap

### Chain-Integration
- ENTRY: chapterModel → chapterGap (nach Model-Erstellung)
- EXIT PASS: chapterGap → write (Coverage gut)
- EXIT GAP: chapterGap → research → discovery → assess → chapterModel → chapterGap (Loop)
- EXIT FORCE: chapterGap → write (mit WARNUNG ueber Luecken)

### FORCE-Decision
- Wichtig: User wird via NOTIFY gewarnt
- write-Command beruecksichtigt gap_severity bei FORCE
- FORCE-Grund wird in gaps.json dokumentiert (budget_exhausted | max_iterations)
- User kann in _manifest.md pruefen und manuell eingreifen
