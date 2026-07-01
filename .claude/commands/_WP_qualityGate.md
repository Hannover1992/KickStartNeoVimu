# /_WP_qualityGate - Chapter Quality Gate Orchestrator

```yaml
status: active
version: 1.0.0
created: 2026-02-10
op: WritePaper
phase: Core Transformation
type: building-block
chain_position: qualityGate
difficulty_scaling: true
mcp_critical: partial
loop_worker: true
loop_level: INNER
orchestrator: true
gates_count: 8
```

---

```
╔══════════════════════════════════════════════════════════════════════════╗
║ VERTRAG: /_WP_qualityGate                                             ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ ACTOR: QUALITY GATE ORCHESTRATOR                                         ║
║   TUT:                                                                   ║
║     - Difficulty-abhaengige Gate-Selektion (3|5|8 Gates)               ║
║     - 8 Gates sequentiell inline ausfuehren (Short-Circuit bei FAIL)   ║
║     - Pro Gate: Score 0-10 berechnen, PASS/WARN/FAIL bestimmen         ║
║     - Composite Score berechnen (gewichteter Durchschnitt)              ║
║     - Gap-JSON fuer autoGen generieren (FAIL-Gates → Verbesserungen)   ║
║     - Re-Run Modus: nur FAIL-Gates erneut pruefen                      ║
║     - strict_mode Progression (Iter 1-3: false, 4+: true, hard only)  ║
║   NICHT:                                                                 ║
║     - Drafts schreiben oder verbessern (→ write, autoGen)              ║
║     - Entscheiden ob weitere Iteration noetig (→ convergence)          ║
║     - Figures generieren (→ visual)                                     ║
║     - Drafts reviewen oder ranken (→ review)                           ║
║     - Quellen suchen oder verwalten (→ research, discovery)            ║
║   ESKALIERT:                                                             ║
║     - MCP research_verify fehlschlaegt → Gate 7 SKIP + WARNUNG        ║
║     - Alle aktiven Gates FAIL → quality-report mit composite=0         ║
║     - Drafts fehlen → STOP + empfehle /_WP_write                    ║
║                                                                          ║
║ LIEST (Input) - PFLICHT:                                                 ║
║   1. _manifest.md (current_chapter, phase, quality_iteration)           ║
║   2. session-state.json (difficulty, strict_mode, quality_history)      ║
║   3. config/project.yaml (research_questions, chapter_config)           ║
║   4. output/drafts/chapter-{N}/*.md (ALLE Drafts)                      ║
║   5. output/drafts/chapter-{N}/metadata.json (Draft-Stats)             ║
║   6. output/models/chapter-{N}-model.md (Sections, Keywords, Glossar)  ║
║   OPTIONAL:                                                              ║
║   7. output/quality/chapter-{N}/quality-report.json (bei Re-Run)       ║
║                                                                          ║
║ SCHREIBT (Output) - PFLICHT:                                             ║
║   1. output/quality/chapter-{N}/quality-report.json                     ║
║   2. output/quality/chapter-{N}/gap-autoGen.json                        ║
║   3. _manifest.md (UPDATE: quality_score, gate_results, next_step)      ║
║   4. session-state.json (UPDATE: quality_iteration, quality_history)    ║
║                                                                          ║
║ POSITION:                                                                ║
║   TYPE: LOOP                                                             ║
║   LOOP-CONTEXT:                                                          ║
║     LOOP-NAME: Quality-Loop                                              ║
║     LOOP-LEVEL: INNER                                                    ║
║     ITERATION-VARIABLE: quality_iteration                                ║
║     MAX-ITERATIONS: extern kontrolliert von /_WP_convergence          ║
║                      (max 2|3|5)                                         ║
║   ENTRY:                                                                 ║
║     NORMAL: /_WP_visual → THIS (nach Figure-Review)                  ║
║   EXIT:                                                                  ║
║     NORMAL: THIS → /_WP_convergence                                   ║
║   PHASE: Core Transformation                                            ║
║   CHAIN: [visual] → [qualityGate] → [convergence]                      ║
║                                                                          ║
║ ORCHESTRIERT:                                                            ║
║   Sub-Command-Execution-Table (8 Gates inline):                          ║
║   ┌──────┬───────────────────┬────────┬────────────────────────────┐    ║
║   │ Gate │ Name              │ Weight │ Aktiv bei Difficulty        │    ║
║   ├──────┼───────────────────┼────────┼────────────────────────────┤    ║
║   │ G1   │ ThemeCoverage     │ 15%    │ easy, normal, hard          │    ║
║   │ G2   │ Completeness      │ 10%    │ easy, normal, hard          │    ║
║   │ G3   │ Glossary          │ 10%    │ normal, hard                │    ║
║   │ G4   │ Foundations       │  5%    │ normal, hard                │    ║
║   │ G5   │ Citations         │ 20%    │ easy, normal, hard          │    ║
║   │ G6   │ QualityScore      │ 20%    │ hard                        │    ║
║   │ G7   │ RAGVerify         │ 15%    │ hard                        │    ║
║   │ G8   │ Visual            │  5%    │ hard                        │    ║
║   └──────┴───────────────────┴────────┴────────────────────────────┘    ║
║   Execution: SEQUENTIELL, Short-Circuit bei gate_score < 5.0            ║
║   Re-Run: --rerun {GateList} → nur FAIL-Gates erneut pruefen           ║
║                                                                          ║
║ ENTSCHEIDET:                                                             ║
║   Per-Gate Decision:                                                     ║
║   ┌──────────────────────────────┬──────────┬───────────────────┐      ║
║   │ Bedingung                     │ Result   │ Effect             │      ║
║   ├──────────────────────────────┼──────────┼───────────────────┤      ║
║   │ gate_score >= 7.0            │ PASS     │ Continue next gate │      ║
║   │ gate_score >= 5.0 < 7.0     │ WARN     │ Continue (→ FAIL   │      ║
║   │                               │          │ wenn strict_mode)  │      ║
║   │ gate_score < 5.0            │ FAIL     │ Short-Circuit       │      ║
║   │ G4 WARN (Ausnahme)           │ CONTINUE │ G4 WARN ist immer  │      ║
║   │                               │          │ toleriert (Q4)     │      ║
║   └──────────────────────────────┴──────────┴───────────────────┘      ║
║                                                                          ║
║ MCP-BREMSE:                                                              ║
║   Tools: mcp__cleancoder__research_verify                                ║
║   Call-Limits:                                                           ║
║     easy:   0 (Gate 7 nicht aktiv)                                      ║
║     normal: 0 (Gate 7 nicht aktiv)                                      ║
║     hard:   3 (1 pro Top-Draft, max 3)                                  ║
║   Parameter:                                                             ║
║     research_verify:                                                     ║
║       project_path: {project_path}                                      ║
║       latex_file: "output/drafts/chapter-{N}/draft-A{NN}.md"           ║
║       options: {verify_content: true, strict_mode: false}               ║
║   KRITISCH: OPTIONAL — Gate 7 SKIP bei MCP-Fehler (M7 Fallback)       ║
║                                                                          ║
║ HiL-PAUSE: N/A                                                          ║
║                                                                          ║
║ SCHWIERIGKEIT:                                                           ║
║   easy:   3 Gates (G1, G2, G5), Composite-Threshold 6.0                ║
║   normal: 5 Gates (G1-G5), Composite-Threshold 7.0                     ║
║   hard:   8 Gates (G1-G8), Composite-Threshold 7.5                     ║
║   strict_mode:                                                           ║
║     easy/normal: false (immer)                                           ║
║     hard: quality_iteration 0-2 false, quality_iteration 3+ true        ║
║                                                                          ║
║ NOTIFY:                                                                  ║
║   powershell -Command "notify 'WritePaper Kapitel {N} QualityGate:     ║
║   {composite}/10 ({passed}/{total} PASS)'"                              ║
║                                                                          ║
║ TAGS:                                                                    ║
║   type: qualityGate                                                      ║
║   op: WritePaper                                                         ║
║   chapter: {N}                                                           ║
║   chain-position: qualityGate                                            ║
║   loop-level: INNER                                                      ║
║   orchestrator: true                                                     ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

**TUT (Claude):**
- Liest alle Drafts und chapter-model fuer Kapitel {N}
- Bestimmt aktive Gates basierend auf difficulty (3|5|8)
- Bestimmt strict_mode basierend auf quality_iteration und difficulty
- Fuehrt Gates sequentiell inline aus (kein Sub-Agent-Spawning)
- Berechnet Score pro Gate (0-10 Skala)
- Bestimmt Gate-Status: PASS (>=7.0) / WARN (>=5.0) / FAIL (<5.0)
- Short-Circuit bei FAIL (nachfolgende Gates uebersprungen)
- Berechnet Composite Score (gewichteter Durchschnitt aktiver Gates)
- Generiert Gap-JSON mit Verbesserungsvorschlaegen fuer FAIL/WARN Gates
- Bei Re-Run: Liest vorherigen quality-report, prueft nur FAIL Gates
- Aktualisiert _manifest.md, session-state.json nach M6 Reihenfolge

**TUT NICHT (Claude):**
- Drafts schreiben oder korrigieren (→ `/_WP_write`)
- Automatisch verbessern basierend auf Gates (→ `/_WP_autoGen`)
- Entscheiden ob Iteration noetig (→ `/_WP_convergence`)
- Figures generieren oder pruefen (→ `/_WP_visual`)
- Drafts ranken oder selektieren (→ `/_WP_review`)

**ESKALATION:**
- Drafts fehlen → BLOCKING STOP + empfehle `/_WP_write`
- chapter-model fehlt → BLOCKING STOP + empfehle `/_WP_chapterModel`
- MCP research_verify offline → NON-BLOCKING, Gate 7 SKIP + WARNUNG (M7 Fallback)
- Alle aktiven Gates FAIL → quality-report mit composite=0 + NOTIFY Error

---

## Ablauf

### Schritt 0: Inputs lesen

**Ziel:** Kontext und Drafts fuer Gate-Evaluation laden

**Aktionen:**
1. Lies `_manifest.md` → `current_chapter`, `phase`, `quality_iteration`
2. Lies `session-state.json` → `difficulty`, `quality_history`, Re-Run-Status
3. Lies `config/project.yaml` → `research_questions`, `chapter_config`
4. Lies `output/models/chapter-{N}-model.md` → Sections, Keywords, Glossar-Begriffe
5. Lies ALLE `output/drafts/chapter-{N}/draft-A{NN}.md` Dateien
6. Lies `output/drafts/chapter-{N}/metadata.json` → `draft_count`, Agent-Stats
7. OPTIONAL: Lies `output/quality/chapter-{N}/quality-report.json` (bei Re-Run)

**Validierung:**
- Mindestens 1 Draft vorhanden → sonst BLOCKING STOP
- chapter-model vorhanden → sonst BLOCKING STOP
- difficulty ist gesetzt (easy|normal|hard) → sonst Default: normal

**Erfolgskriterium:**
- Alle Drafts eingelesen mit Inhalten
- Chapter-Model mit Sections und Keywords verfuegbar
- Difficulty und quality_iteration bestimmt

---

### Schritt 1: Gate-Konfiguration

**Ziel:** Aktive Gates, Gewichte und Thresholds basierend auf Difficulty bestimmen

**Aktionen:**
1. Bestimme aktive Gates:
   - easy: G1, G2, G5 (3 Gates)
   - normal: G1, G2, G3, G4, G5 (5 Gates)
   - hard: G1, G2, G3, G4, G5, G6, G7, G8 (8 Gates)

2. Setze Composite-Threshold:
   - easy: 6.0
   - normal: 7.0
   - hard: 7.5

3. Bestimme strict_mode:
   - easy/normal: false (immer)
   - hard: quality_iteration <= 2 → false, quality_iteration >= 3 → true

4. Berechne normalisierte Gewichte (nur aktive Gates):
   ```
   easy (G1,G2,G5):
     G1: 15/(15+10+20) = 0.333
     G2: 10/(15+10+20) = 0.222
     G5: 20/(15+10+20) = 0.444

   normal (G1-G5):
     G1: 15/(15+10+10+5+20) = 0.250
     G2: 10/60 = 0.167
     G3: 10/60 = 0.167
     G4:  5/60 = 0.083
     G5: 20/60 = 0.333

   hard (G1-G8):
     Gewichte wie definiert (Summe = 100%)
     G1=0.15, G2=0.10, G3=0.10, G4=0.05, G5=0.20,
     G6=0.20, G7=0.15, G8=0.05
   ```

5. Bei Re-Run: Lese vorherigen quality-report
   - Identifiziere Gates mit Status FAIL oder WARN
   - Parse `--rerun {GateList}` Flag (z.B. `--rerun Citations,RAGVerify`)
   - Nur spezifizierte FAIL-Gates werden neu evaluiert
   - PASS-Gates behalten Score aus letztem Run

**Erfolgskriterium:**
- Aktive Gates bestimmt mit normalisierten Gewichten
- Composite-Threshold gesetzt
- strict_mode gesetzt
- Re-Run-Liste bestimmt (falls Re-Run)

---

### Schritt 2: Gate-Execution (Sequentiell, Short-Circuit)

**Ziel:** Alle aktiven Gates sequentiell evaluieren

**Kern-Mechanismus:**

```
FOR gate IN active_gates (sequentiell):
    IF re_run AND gate NOT IN re_run_list:
        → Uebernimm Score aus letztem Run
        → CONTINUE

    score = evaluate_gate(gate, drafts, model)

    IF score >= 7.0:
        status = "PASS"
    ELIF score >= 5.0:
        IF strict_mode AND gate != "G4":
            status = "FAIL"  # strict: WARN wird zu FAIL
        ELSE:
            status = "WARN"
    ELSE:
        status = "FAIL"

    gate_results.append({gate, score, status, findings})

    IF status == "FAIL" AND gate != "G4":
        # Short-Circuit: Restliche Gates SKIP
        FOR remaining_gate IN remaining_gates:
            gate_results.append({remaining_gate, 0, "SKIPPED"})
        BREAK

    IF gate == "G4" AND status == "WARN":
        # G4 Ausnahme: WARN ist toleriert (Q4)
        status = "WARN-TOLERATED"
        CONTINUE
```

**Short-Circuit-Regeln:**
- Gate N FAIL → Gates N+1..last werden SKIPPED
- Ausnahme: G4 (Foundations) WARN ist IMMER toleriert (Q4)
- SKIPPED Gates bekommen Score 0 aber zaehlen NICHT in Composite
- Composite wird NUR ueber evaluierte Gates berechnet (nicht SKIPPED)

**Erfolgskriterium:**
- Alle aktiven Gates evaluiert (oder Short-Circuit nach FAIL)
- Pro Gate: Score, Status, Findings dokumentiert
- Short-Circuit korrekt bei FAIL (nicht bei WARN ausser strict_mode)

---

## Gate-Definitionen (8 Gates Inline)

### G1: ThemeCoverage (Gewicht: 15%)

**Aktiv bei:** easy, normal, hard

**Pruefung:** Ist das Kapitel-Thema ausreichend abgedeckt?

**Evaluation:**
1. Extrahiere Kapitel-Thema aus chapter-model Section-Titeln
2. Pro Draft: Zaehle Erwaehnung des Hauptthemas (exakt + semantisch)
3. Pro Section im Model: Pruefe ob mindestens 1 Draft die Section behandelt
4. Berechne Coverage-Rate: `covered_sections / total_sections`

**Scoring:**
```
score = 10 * coverage_rate
Bonus: +0.5 wenn JEDER Draft das Thema >= 3x erwaehnt
Malus: -1.0 pro Section die in KEINEM Draft vorkommt
Min: 0, Max: 10
```

**PASS:** score >= 7.0 (70%+ Sections abgedeckt)
**WARN:** score >= 5.0 (50%+ Sections abgedeckt)
**FAIL:** score < 5.0 (unter 50% Sections abgedeckt)

**Findings-Format:**
```json
{"covered_sections": [...], "missing_sections": [...], "theme_mentions": N}
```

---

### G2: Completeness (Gewicht: 10%)

**Aktiv bei:** easy, normal, hard

**Pruefung:** Sind alle Sections aus dem Model vollstaendig vorhanden?

**Evaluation:**
1. Lese Section-Liste aus chapter-{N}-model.md
2. Pro Draft: Pruefe ob Section-Ueberschriften vorhanden sind (exakte oder semantische Matches)
3. Pro Section: Berechne Abdeckungstiefe (Wortanzahl in Draft / erwartete Wortanzahl)
4. Identifiziere leere oder minimale Sections (< 100 Worte)

**Scoring:**
```
sections_complete = Anzahl Sections mit >= 100 Worte in mindestens 1 Draft
score = 10 * (sections_complete / total_sections)
Malus: -0.5 pro Section mit < 50 Worte (skelettartig)
Min: 0, Max: 10
```

**PASS:** score >= 7.0 (alle Sections substantiell)
**WARN:** score >= 5.0 (einige Sections duenn)
**FAIL:** score < 5.0 (mehrere Sections fehlen oder leer)

**Findings-Format:**
```json
{"complete_sections": [...], "thin_sections": [...], "missing_sections": [...], "avg_words_per_section": N}
```

---

### G3: Glossary (Gewicht: 10%)

**Aktiv bei:** normal, hard

**Pruefung:** Sind alle Fachbegriffe definiert? (100% NICHT VERHANDELBAR, W5)

**Evaluation:**
1. Extrahiere Fachbegriffe aus chapter-{N}-model.md (Glossar-Sektion)
2. Falls kein Glossar im Model: Extrahiere Fachbegriffe aus Keywords (Begriffe mit Grossbuchstaben, Akronyme, Fremdwoerter)
3. Pro Fachbegriff: Pruefe ob mindestens 1 Draft eine Definition oder Erklaerung enthaelt
4. Suche nach Mustern: "{Begriff} ist...", "{Begriff} bezeichnet...", "{Begriff} (auch bekannt als...)"

**Scoring:**
```
defined_terms = Anzahl Fachbegriffe mit Definition in mindestens 1 Draft
score = 10 * (defined_terms / total_terms)
ACHTUNG: 100% ist Ziel, jeder undefinierte Begriff kostet proportional
Min: 0, Max: 10
```

**PASS:** score >= 7.0 (mind. 70% definiert, akzeptabel wenn Rest aus Kontext klar)
**WARN:** score >= 5.0 (50-70% definiert)
**FAIL:** score < 5.0 (unter 50% definiert)

**Findings-Format:**
```json
{"total_terms": N, "defined_terms": [...], "undefined_terms": [...], "definition_rate": 0.XX}
```

---

### G4: Foundations (Gewicht: 5%)

**Aktiv bei:** normal, hard

**Pruefung:** Sind Cross-References und Dependencies korrekt referenziert?

**Evaluation:**
1. Identifiziere Dependencies: Welche Konzepte aus vorherigen Kapiteln werden referenziert?
2. Pro Draft: Pruefe ob vorherige Kapitel explizit erwaehnt werden (z.B. "wie in Kapitel 2 beschrieben")
3. Pruefe ob Foundations (Grundlagen, auf denen aufgebaut wird) erwaehnt werden
4. Pruefe ob externe Referenzen (Standards, Frameworks) genannt werden

**Scoring:**
```
foundation_refs = Anzahl gefundener Cross-References
expected_refs = MAX(1, chapter_number - 1) * 2  # mind. 2 pro Vorgaenger-Kapitel
score = MIN(10, 10 * (foundation_refs / expected_refs))
Kapitel 1: Automatisch 8.0 (keine Vorgaenger)
Min: 0, Max: 10
```

**PASS:** score >= 7.0
**WARN:** score >= 5.0 (G4 WARN ist IMMER toleriert, Q4)
**FAIL:** score < 5.0

**Sonderregel:** G4 WARN loest KEINEN Short-Circuit aus und zaehlt im Composite als WARN-Score (nicht als FAIL), unabhaengig von strict_mode.

**Findings-Format:**
```json
{"found_refs": [...], "expected_refs": N, "chapter_1_bypass": true|false}
```

---

### G5: Citations (Gewicht: 20%)

**Aktiv bei:** easy, normal, hard

**Pruefung:** Sind BibTeX-Citations korrekt und dicht genug?

**Evaluation:**
1. Pro Draft: Extrahiere alle `\cite{key}` Referenzen
2. Pruefe Citation-Density pro Section:
   ```
   density = citations_in_section / (words_in_section / 250)  # per "Seite"
   ```
3. Pruefe ob Citation-Keys gueltig sind (existieren in references.bib oder RAG)
4. Identifiziere Abschnitte OHNE Citations (> 200 Worte ohne \cite{})

**Scoring:**
```
avg_density = Durchschnitt der Section-Densities ueber alle Drafts
valid_rate = valid_citations / total_citations
uncited_sections = Sections mit > 200 Worte ohne Citation

score = (avg_density / 3.0) * 5  # 3.0 density = 5 Punkte
      + valid_rate * 3            # 100% gueltig = 3 Punkte
      + MAX(0, 2 - uncited_sections * 0.5)  # Abzug fuer fehlende Citations
score = MIN(10, MAX(0, score))
```

**PASS:** score >= 7.0 (density >= 3.0, kaum uncited sections)
**WARN:** score >= 5.0 (density >= 2.0, einige uncited sections)
**FAIL:** score < 5.0 (density < 2.0 oder viele uncited sections)

**Findings-Format:**
```json
{
  "avg_density": 3.2,
  "valid_citations": N,
  "invalid_citations": [...],
  "uncited_sections": [...],
  "density_per_section": [{"section": "1.1", "density": 4.0}, ...]
}
```

---

### G6: QualityScore (Gewicht: 20%)

**Aktiv bei:** hard

**Pruefung:** Composite-Bewertung von Textqualitaet (Wortanzahl, Kohaerenz, Struktur)

**Evaluation:**
1. **Wortanzahl-Dimension (0-10):**
   - Ziel: 6250-8750 Worte pro Kapitel (W10: 25 Seiten +-10)
   - Pro Draft: avg_word_count (aus metadata.json)
   - `word_score = 10 - ABS(avg_word_count - 7500) / 625`
   - Min: 0, Max: 10

2. **Kohaerenz-Dimension (0-10):**
   - Pruefe Uebergangs-Phrasen zwischen Sections (z.B. "Aufbauend auf...", "Im Gegensatz zu...")
   - Pro Draft: transition_count / (sections_count - 1)
   - `coherence_score = MIN(10, transition_rate * 10)`

3. **Struktur-Dimension (0-10):**
   - Pruefe Ueberschriften-Hierarchie (H1 → H2 → H3, keine Spruenge)
   - Pruefe Absatz-Laenge (ideal: 100-300 Worte pro Absatz)
   - Pruefe Listen-Nutzung (mindestens 1 Liste pro Draft)
   - `structure_score = 10 - (hierarchy_violations * 2) - (oversized_paragraphs * 0.5)`

**Scoring:**
```
score = word_score * 0.40 + coherence_score * 0.30 + structure_score * 0.30
Min: 0, Max: 10
```

**PASS:** score >= 7.0
**WARN:** score >= 5.0
**FAIL:** score < 5.0

**Findings-Format:**
```json
{
  "word_score": 8.2,
  "coherence_score": 7.0,
  "structure_score": 6.5,
  "avg_word_count": 7200,
  "transition_count": 12,
  "hierarchy_violations": 1,
  "oversized_paragraphs": 3
}
```

---

### G7: RAGVerify (Gewicht: 15%)

**Aktiv bei:** hard

**Pruefung:** Anti-Halluzination via MCP research_verify (M3 RAG-Constraint)

**Evaluation:**
1. Waehle Top-3 Drafts (basierend auf G5 Citation-Density, hoechste zuerst)
2. Pro Draft (max 3 MCP-Calls):
   ```python
   result = await mcp__cleancoder__research_verify(
       project_path="{project_path}",
       latex_file="output/drafts/chapter-{N}/draft-A{NN}.md",
       options={"verify_content": True, "strict_mode": False}
   )
   ```
3. Analysiere Result:
   - `verified`: Citations die in RAG bestaetigt sind
   - `in_bibliography`: Citations die in .bib existieren aber nicht in RAG
   - `missing`: Citations die NIRGENDS existieren (HALLUZINIERT)
4. Berechne Verification-Rate: `verified / total_citations`

**Scoring:**
```
verified_rate = verified / total_citations
missing_rate = missing / total_citations

score = verified_rate * 8           # 100% verified = 8 Punkte
      + (1 - missing_rate) * 2      # 0% missing = 2 Punkte
score = MIN(10, MAX(0, score))
```

**PASS:** score >= 7.0 (>= 70% verified, < 10% missing)
**WARN:** score >= 5.0 (>= 50% verified, < 20% missing)
**FAIL:** score < 5.0 (< 50% verified oder >= 20% missing)

**Fallback (M7):**
- MCP research_verify fehlschlaegt → Gate 7 Status = "SKIPPED"
- SKIPPED zaehlt NICHT im Composite (Gewicht umverteilt auf andere Gates)
- WARNUNG: "Gate 7 SKIPPED: MCP research_verify nicht erreichbar"
- Gewicht-Umverteilung: G7-Gewicht (15%) proportional auf G5 und G6

**Findings-Format:**
```json
{
  "drafts_checked": 3,
  "total_citations_checked": 45,
  "verified": 38,
  "in_bibliography": 5,
  "missing": 2,
  "verified_rate": 0.844,
  "missing_rate": 0.044,
  "hallucinated_keys": ["Smith2025", "Unknown2024"],
  "mcp_status": "OK|SKIPPED"
}
```

---

### G8: Visual (Gewicht: 5%)

**Aktiv bei:** hard

**Pruefung:** Sind Figure-Placeholder vorhanden und qualitativ beschrieben?

**Evaluation:**
1. Pro Draft: Zaehle `[FIGURE: ...]` Placeholder
2. Pro Placeholder: Bewerte Beschreibungsqualitaet:
   - Hat Diagramm-Typ? (Balkendiagramm, Flowchart, Tabelle, etc.)
   - Hat Daten-Beschreibung? (Was wird dargestellt?)
   - Hat Kontext? (Warum ist diese Visualisierung relevant?)
3. Berechne figures_per_draft und description_quality

**Scoring:**
```
min_figures_per_draft = 1  # Mindestens 1 Figure pro Draft erwartet
avg_figures = total_figures / draft_count
description_quality = well_described_figures / total_figures

figure_coverage = MIN(1, avg_figures / min_figures_per_draft)
score = figure_coverage * 5 + description_quality * 5
Min: 0, Max: 10
```

**PASS:** score >= 7.0 (genug Figures, gut beschrieben)
**WARN:** score >= 5.0 (Figures vorhanden, teils schlecht beschrieben)
**FAIL:** score < 5.0 (zu wenige Figures oder schlecht beschrieben)

**Findings-Format:**
```json
{
  "total_figures": 8,
  "avg_figures_per_draft": 1.6,
  "well_described": 6,
  "poorly_described": 2,
  "description_quality": 0.75,
  "figure_types": {"flowchart": 3, "bar_chart": 2, "table": 3}
}
```

---

## Score-Aggregation

### Composite Score Berechnung

```
composite_score = SUM(gate_score * normalized_weight) fuer alle evaluierten Gates

Nur evaluierte Gates zaehlen (nicht SKIPPED):
  normalized_weight = gate_weight / SUM(alle evaluierten gate_weights)

Beispiel (hard, Gate 7 SKIPPED):
  Evaluierte Gewichte: G1=15, G2=10, G3=10, G4=5, G5=20, G6=20, G8=5
  Summe = 85
  G1_norm = 15/85 = 0.176, G5_norm = 20/85 = 0.235, etc.
  composite = G1*0.176 + G2*0.118 + ... + G8*0.059
```

### Composite-Entscheidung

```
all_gates_passed = ALLE evaluierten Gates haben Status PASS
                   ODER (WARN-TOLERATED bei G4)

composite_passed = composite_score >= composite_threshold

overall_result:
  IF all_gates_passed AND composite_passed:
    → "QUALITY_PASSED"
  ELSE:
    → "QUALITY_FAILED"
```

### strict_mode Effekt

```
IF strict_mode == true:
    # WARN wird zu FAIL (ausser G4)
    FOR gate IN gate_results:
        IF gate.status == "WARN" AND gate.gate != "G4":
            gate.status = "FAIL"
            → Short-Circuit Logik greift
```

---

## Re-Run Modus

**Trigger:** Aufruf mit `--rerun {GateList}` Parameter

**Ablauf:**
1. Lies vorherigen `quality-report.json`
2. Identifiziere Gates in `{GateList}` (Komma-separiert, z.B. "Citations,RAGVerify")
3. Fuer Gates NICHT in `{GateList}`: Uebernimm Score und Status aus letztem Run
4. Fuer Gates IN `{GateList}`: Evaluiere neu (frische Analyse)
5. Berechne Composite Score NEU mit aktualisierten Gate-Scores

**Beispiel:**
```
Vorheriger Run: G1=PASS(8.5), G2=PASS(7.2), G5=FAIL(4.1)
--rerun Citations
→ G1: 8.5 (uebernommen), G2: 7.2 (uebernommen), G5: NEU evaluiert
```

**Validierung:**
- Gates in `{GateList}` muessen aktive Gates sein (sonst WARNUNG)
- Vorheriger quality-report muss existieren (sonst Full-Run)

---

## Output-Format

### output/quality/chapter-{N}/quality-report.json

```json
{
  "chapter": 1,
  "quality_iteration": 0,
  "difficulty": "hard",
  "strict_mode": false,
  "timestamp": "2026-02-10T12:00:00Z",
  "gates_total": 8,
  "gates_active": 8,
  "gates_passed": 6,
  "gates_warned": 1,
  "gates_failed": 1,
  "gates_skipped": 0,
  "composite_score": 7.2,
  "composite_threshold": 7.5,
  "composite_passed": false,
  "all_gates_passed": false,
  "overall_result": "QUALITY_FAILED",
  "gate_results": [
    {
      "gate": "G1",
      "name": "ThemeCoverage",
      "weight": 0.15,
      "normalized_weight": 0.15,
      "score": 8.5,
      "status": "PASS",
      "findings": {}
    },
    {
      "gate": "G5",
      "name": "Citations",
      "weight": 0.20,
      "normalized_weight": 0.20,
      "score": 4.1,
      "status": "FAIL",
      "findings": {
        "avg_density": 1.8,
        "uncited_sections": ["1.2", "1.3"]
      }
    }
  ],
  "score_breakdown": {
    "weighted_scores": [1.275, 0.72, 0.85, 0.35, 0.82, 1.40, 1.20, 0.40],
    "total_weight_evaluated": 1.0,
    "composite": 7.2
  },
  "re_run": false,
  "re_run_gates": [],
  "next_step": "convergence"
}
```

### output/quality/chapter-{N}/gap-autoGen.json

```json
{
  "chapter": 1,
  "quality_iteration": 0,
  "timestamp": "2026-02-10T12:00:00Z",
  "overall_result": "QUALITY_FAILED",
  "failed_gates": [
    {
      "gate": "G5",
      "name": "Citations",
      "score": 4.1,
      "issues": [
        {
          "type": "low_density",
          "section": "1.2",
          "current_density": 1.2,
          "required_density": 3.0,
          "description": "Section 1.2 hat Citaion-Density 1.2, erwartet >= 3.0"
        },
        {
          "type": "uncited_paragraph",
          "section": "1.3",
          "paragraph_start": "Die Forschung zeigt...",
          "description": "Absatz in Section 1.3 hat > 200 Worte ohne Citation"
        }
      ],
      "improvement_actions": [
        "Erhoehe Citation-Density in Section 1.2 von 1.2 auf >= 3.0",
        "Fuege Citations zu Absaetzen in Section 1.3 hinzu"
      ]
    }
  ],
  "warned_gates": [
    {
      "gate": "G4",
      "name": "Foundations",
      "score": 5.5,
      "issues": [
        {
          "type": "missing_cross_reference",
          "description": "Keine Referenz auf Kapitel 2 Grundlagen"
        }
      ],
      "improvement_actions": [
        "Fuege Cross-Reference auf Kapitel 2 hinzu"
      ]
    }
  ],
  "total_issues": 3,
  "total_improvement_actions": 3,
  "priority_order": ["G5", "G4"]
}
```

---

## State-Aktualisierung (M6 Reihenfolge)

### 1. OUTPUT (quality-report.json, gap-autoGen.json)
Geschrieben in Schritt 2 nach Gate-Execution.

### 2. _manifest.md UPDATE
```markdown
## QualityGate - Kapitel {N}, Iteration {I}
- **Composite Score:** {composite}/10
- **Threshold:** {threshold}
- **Result:** QUALITY_PASSED | QUALITY_FAILED
- **Gates:** {passed}/{active} PASS, {warned} WARN, {failed} FAIL, {skipped} SKIP
- **strict_mode:** {true|false}
- **Re-Run:** {true|false}
- **Next Step:** convergence
```

### 3. session-state.json UPDATE
```json
{
  "last_command": "_WP_qualityGate",
  "quality_iteration": 0,
  "quality_score": 7.2,
  "quality_result": "QUALITY_FAILED",
  "gates_passed": 6,
  "gates_failed": 1,
  "strict_mode": false,
  "next_step": "convergence"
}
```

### 4. NOTIFY
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} QualityGate: {composite}/10 ({passed}/{total} PASS)'"
```

---

## Qualitaetskriterien

### Vollstaendigkeit
- [ ] Alle aktiven Gates evaluiert (oder Short-Circuit nach FAIL)
- [ ] quality-report.json mit allen Gate-Results geschrieben
- [ ] gap-autoGen.json mit FAIL/WARN Gates und Improvement-Actions geschrieben
- [ ] _manifest.md und session-state.json aktualisiert
- [ ] NOTIFY gesendet

### Korrektheit
- [ ] Gate-Selektion basierend auf difficulty (3|5|8 Gates)
- [ ] Gewichte normalisiert (Summe = 1.0 ueber evaluierte Gates)
- [ ] Short-Circuit bei FAIL korrekt (nicht bei WARN, ausser strict_mode)
- [ ] G4 WARN ist IMMER toleriert (Q4 Sonderregel)
- [ ] strict_mode korrekt: easy/normal=false, hard Iter 0-2=false, hard Iter 3+=true
- [ ] Composite Score = gewichteter Durchschnitt (nur evaluierte Gates)
- [ ] Re-Run: PASS-Gates uebernommen, nur FAIL-Gates neu evaluiert

### Robustheit
- [ ] MCP research_verify Fehler → Gate 7 SKIP (M7 Fallback)
- [ ] G7 SKIP → Gewicht proportional umverteilt auf G5+G6
- [ ] Keine Drafts → BLOCKING STOP + empfehle write
- [ ] Alle Gates FAIL → composite=0, quality-report trotzdem geschrieben

### Performance
- [ ] Gates sequentiell (nicht parallel) — Short-Circuit spart Evaluation
- [ ] MCP-Calls nur bei Gate 7 (hard only, max 3)
- [ ] Re-Run: Nur FAIL-Gates neu evaluiert
- [ ] Keine redundanten Draft-Lesevorgaenge (1x lesen, N Gates nutzen)

---

## NOTIFY

**Success (QUALITY_PASSED):**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} QualityGate: PASSED {composite}/10 ({passed}/{total} Gates)'"
```

**Warning (QUALITY_FAILED, nah am Threshold):**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} QualityGate: FAILED {composite}/10 (Threshold {threshold})'"
```

**Error (Drafts fehlen oder kritischer Fehler):**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} QualityGate FAILED: Keine Drafts gefunden'"
```

---

## Error Handling

| Kategorie | Trigger | Response | NOTIFY |
|-----------|---------|----------|--------|
| **BLOCKING** | Keine Drafts vorhanden | STOP + empfehle /_WP_write | ERROR |
| **BLOCKING** | chapter-model fehlt | STOP + empfehle /_WP_chapterModel | ERROR |
| **NON-BLOCKING** | MCP research_verify offline | Gate 7 SKIP, Gewicht umverteilen | WARNING |
| **NON-BLOCKING** | 1 Draft nicht lesbar | Gate-Evaluation mit verbleibenden Drafts | WARNING |
| **FALLBACK** | quality-report fehlt bei Re-Run | Full-Run statt Re-Run | INFO |
| **FALLBACK** | metadata.json fehlt | Stats manuell aus Drafts berechnen | INFO |

---

## Hinweise

### Orchestrator-Pattern
- qualityGate ist der EINZIGE Orchestrator in der _R_WP Pipeline
- Alle 8 Gates sind INLINE (keine separaten Command-Dateien)
- Sequentielle Ausfuehrung mit Short-Circuit spart Ressourcen
- Refactoring zu separaten Gate-Commands in spaeteren Zyklen moeglich

### INNER Quality-Loop Kontext
- qualityGate ist WORKER im INNER Quality-Loop (Controller: convergence)
- quality_iteration wird von convergence gesteuert (max 2|3|5)
- qualityGate LIEST quality_iteration, SCHREIBT quality_score
- convergence LIEST quality_score, ENTSCHEIDET CONVERGE/ITERATE/FORCE

### Score-Gewichtung Begruendung
- G5 Citations (20%) + G6 QualityScore (20%) = 40%: Akademische Qualitaet
- G1 ThemeCoverage (15%) + G7 RAGVerify (15%) = 30%: Inhaltliche Korrektheit
- G2 Completeness (10%) + G3 Glossary (10%) = 20%: Vollstaendigkeit
- G4 Foundations (5%) + G8 Visual (5%) = 10%: Ergaenzende Qualitaet

### Re-Run Effizienz
- Voller Run: Alle aktiven Gates evaluiert
- Re-Run: Nur FAIL-Gates, PASS-Gates behalten Score
- Typischer Use-Case: autoGen verbessert spezifische Sections → Re-Run prueft nur betroffene Gates
- Re-Run spart bis zu 80% der Evaluationszeit (bei 1-2 FAIL Gates)

### strict_mode Progression
- Iter 0-2: Tolerant (WARN ist OK) — gibt autoGen Raum fuer Verbesserung
- Iter 3+: Strikt (WARN wird FAIL) — erzwingt Qualitaet vor FORCE
- Nur bei hard difficulty — easy/normal sind immer tolerant
- Begruendung: Spaete Iterationen sollten Qualitaet erzwingen, nicht endlos iterieren

### Chain-Integration
- ENTRY: visual → qualityGate (nach Figure-Review)
- EXIT: qualityGate → convergence (immer, ausser BLOCKING Error)
- convergence entscheidet: CONVERGE → review | ITERATE → write | FORCE → review
- gap-autoGen.json wird von autoGen gelesen (wenn implementiert, C9+)
- Ohne autoGen: convergence routet ITERATE → write direkt

### Referenzen
- Model: WritePaper_Model.md (W5 Quality Gates, W10 Seitenzahl, M3 RAG-Constraint, M6 State-Sync, M7 Fallback)
- Blueprint: /_WP_review.md (Scoring-Pattern, Difficulty-Scaling)
- Blueprint: _Pre_PR.md (9-Gate-Orchestrator Pattern)
- Previous: /_WP_visual.md (Figure-Review)
- Next: /_WP_convergence.md (CONVERGE/ITERATE/FORCE Decision)

---

**Command-Version:** 1.0.0
**Letzte Aenderung:** 2026-02-10
