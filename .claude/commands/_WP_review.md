# /_WP_review - Cross-Review & Scoring

```yaml
status: active
version: 1.0.0
created: 2026-02-09
op: REVIEW
phase: core_transformation
type: standard
chain_position: 3_of_4
difficulty_scaling: true
```

## VERTRAG

```
╔════════════════════════════════════════════════════════════════════════════╗
║ STANDARD-COMMAND VERTRAG v1.1                                              ║
╠════════════════════════════════════════════════════════════════════════════╣
║ 1. ACTOR     │ Sonnet 4.5 - Review & Scoring Operator                     ║
║ 2. LIEST     │ output/drafts/chapter-{N}/*.md + metadata.json             ║
║              │ _manifest.md, session-state.json, config/project.yaml      ║
║ 3. SCHREIBT  │ output/reviews/chapter-{N}/review-matrix.json              ║
║              │ output/reviews/chapter-{N}/review-summary.md               ║
║              │ _manifest.md (UPDATE), session-state.json (UPDATE)         ║
║ 4. POSITION  │ TYPE: LINEAR                                               ║
║              │ AFTER: /_WP_convergence (Quality-Loop CONVERGED)         ║
║              │ BEFORE: /_WP_synthesis                                   ║
║              │ PHASE: Core Transformation (Kapitel-Loop Schritt 4)        ║
║              │ CHAIN: [convergence]→[REVIEW]→[synthesis]→[reflect]        ║
║ 9. SCHWIERIGK│ DIFFICULTY-SCALING:                                        ║
║              │ easy   → 3 Agents × 2 Reviews = 6 Cross-Reviews            ║
║              │ normal → 5 Agents × 4 Reviews = 20 Cross-Reviews           ║
║              │ hard   → 9 Agents × 8 Reviews = 72 Cross-Reviews           ║
║              │ Min-Score: easy=6.0, normal=7.0, hard=7.5                  ║
║              │ Top-K: easy=Top-1, normal=Top-2, hard=Top-3                ║
║ 10. NOTIFY   │ Success → "✓ Cross-Review completed: {N} drafts ranked"   ║
║              │ Warning → "⚠ {X} reviews failed, matrix reduced"           ║
║              │ Error   → "✗ No drafts found, run /_WP_write first"     ║
╚════════════════════════════════════════════════════════════════════════════╝
```

---

## DUAL-MODE

_WP_review läuft in drei Modi. Erkenne deinen Modus via TaskGet (Task-Beschreibung lesen):

### MODUS 1: SOLO (User ruft /_WP_review direkt auf)
Erkennungs-Signal: Task-Beschreibung enthält KEIN "Agent A{NN}", "Worker-Reviewer" oder "Score aggregieren".
Verhalten:
- Führe Schritte 0-5 vollständig durch
- Schritt 2a: M4 Parallel-Spawning aller N Review-Agents (Task-Tool verfügbar)
- Schritt 3-5: Score-Aggregation + Report + State-Update

### MODUS 2: WORKER-REVIEWER (Task "WP Cross-Review (Agent A{NN})")
Erkennungs-Signal: Task-Beschreibung enthält "Agent A{NN}" oder "Worker-Reviewer".
Verhalten:
- Schritt 0: Inputs validieren
- Schritt 1: Review-Matrix konfigurieren (nur für eigene Assignments)
- Schritt 2b: NUR eigene Reviews durchführen (N-1 Reviews), KEIN Spawning
- Schreibe NUR `output/reviews/chapter-{N}/agent-A{NN}-reviews.json`
- Schritte 3-5 NICHT ausführen (macht Worker-Synthesist)
- TaskUpdate completed + SendMessage an Team Lead

### MODUS 3: WORKER-SYNTHESIST (Task "WP Review Score aggregieren")
Erkennungs-Signal: Task-Beschreibung enthält "Score aggregieren" oder "Review-Synthesis".
Verhalten:
- Lese ALLE `agent-A{NN}-reviews.json` (alle Review-Agents)
- Führe Schritt 3-5 aus: Aggregation + Ranking + Report + State-Update
- Schreibe `review-matrix.json` + `review-summary.md`
- TaskUpdate completed + SendMessage an Team Lead

---

## VERTRAG (File-basiert)

```
INPUT von _WP_write:
  output/drafts/chapter-{N}/draft-A01.md ... draft-A{N}.md
  output/drafts/chapter-{N}/metadata.json   (draft_count, agent_roles)
  _manifest.md                               (current_chapter, phase)
  session-state.json                         (difficulty)
  config/project.yaml                        (current_chapter)

OUTPUT für _WP_synthesis:
  output/reviews/chapter-{N}/review-matrix.json    (aggregiert, top_k_drafts)
  output/reviews/chapter-{N}/review-summary.md     (human-readable)
  output/reviews/chapter-{N}/agent-A{NN}-reviews.json  (pro Reviewer)
  _manifest.md UPDATE                        (review_completed: true)
  session-state.json UPDATE                  (review_results, next_step)
```

---

## SKALIERUNGS-TABELLE

| Difficulty | Review-Agents (Welle 1) | Synthese (Welle 2) | Reviews/Agent | Total Reviews | Min-Score | Top-K |
|------------|------------------------|---------------------|---------------|---------------|-----------|-------|
| hard       | 9 middle               | 1 ceiling           | 8 (N-1)       | 72            | 7.5       | 3     |
| normal     | 5 middle               | 1 ceiling           | 4 (N-1)       | 20            | 7.0       | 2     |
| easy       | 1 ceiling (solo)       | —                   | 2 (N-1)       | 6             | 6.0       | 1     |

**easy:** 1 Worker führt alle 3 Rollen sequentiell aus (kein Task-Splitting).
**normal:** 5 parallele Review-Worker + 1 Synthese-Worker (blocked_by alle 5).
**hard:** 9 parallele Review-Worker + 1 Synthese-Worker (blocked_by alle 9).

---

## VERANTWORTLICHKEIT

### TUT dieser Command
- Cross-Review Matrix generieren (M2 Multi-Agent-Review Pattern)
- Im SOLO-Modus: N Review-Agents parallel spawnen (M4 Parallel-Spawning)
- Im WORKER-REVIEWER-Modus: Nur eigene Reviews (N-1), kein Spawning
- Im WORKER-SYNTHESIST-Modus: Score-Aggregation ohne Spawning
- N×(N-1) Reviews durchführen (jeder Agent reviewt alle anderen Drafts)
- Score-Aggregation pro Draft (Durchschnitt aller Reviewer-Scores)
- Top-K Selektion basierend auf difficulty
- Review-Report generieren (Matrix JSON + Human-readable Summary)
- State aktualisieren (_manifest.md + session-state.json)

### TUT NICHT dieser Command
- Drafts neu schreiben (das macht /_WP_write)
- Quality-Loop Entscheidungen treffen (das macht /_WP_convergence)
- Synthese ausführen (das macht /_WP_synthesis)
- Kapitel-Fortschritt steuern (das macht /_WP_orchestrate)
- Git-Operationen (user macht git selbst)
- MCP-Tools aufrufen (kein RAG in diesem Command)

### ESKALATION
- BLOCKING Error: Keine Drafts gefunden → NOTIFY Error + empfehle /_WP_write
- Pipeline-Abbruch: output/drafts/ Verzeichnis fehlt → NOTIFY Error + prüfe Setup
- Alle Reviews fehlgeschlagen: Score-Matrix leer → NOTIFY Error + empfehle Re-Run

---

## ABLAUF

### Schritt 0: Inputs validieren

**Ziel:** Alle benötigten Dateien lesen und Kontext aufbauen

**Aktionen:**
1. Lese `_manifest.md` → extrahiere `current_chapter`, `phase`, `quality_iteration`
2. Lese `session-state.json` → extrahiere `difficulty`, `current_step`
3. Lese `config/project.yaml` → validiere `current_chapter` konsistent
4. Prüfe `output/drafts/chapter-{N}/` Verzeichnis existiert
5. Lese `output/drafts/chapter-{N}/metadata.json` → extrahiere `draft_count`, `agent_roles`
6. Lese ALLE `output/drafts/chapter-{N}/draft-A{NN}.md` Dateien (N Drafts)

**Validierung:**
- [ ] `current_chapter` ist konsistent zwischen allen Dateien
- [ ] `phase` ist "core_transformation" oder "iteration"
- [ ] `difficulty` ist "easy" | "normal" | "hard"
- [ ] `draft_count` ≥ 1 (mindestens 1 Draft vorhanden)
- [ ] Anzahl .md Dateien = draft_count aus metadata.json
- [ ] Alle agent_roles haben entsprechende draft-A{NN}.md Dateien

**Erfolgskriterium:** Alle N Drafts eingelesen, Metadaten konsistent

**Fallback:** Falls Drafts fehlen → BLOCKING Error + NOTIFY

---

### Schritt 1: Review-Matrix konfigurieren

**Ziel:** Difficulty-abhängige Parameter setzen und Reviewer-Assignments erstellen

**Aktionen:**
1. Bestimme N (Agent-Count) basierend auf difficulty:
   - easy: N=3
   - normal: N=5
   - hard: N=9
2. Berechne Total-Reviews: N × (N-1)
   - easy: 3×2=6
   - normal: 5×4=20
   - hard: 9×8=72
3. Setze Min-Score Schwellwert:
   - easy: 6.0
   - normal: 7.0
   - hard: 7.5
4. Setze Top-K Anzahl:
   - easy: 1
   - normal: 2
   - hard: 3
5. Erstelle Reviewer-Assignment-Matrix:
   ```
   Agent A01 → reviewt [A02, A03, ..., A{N}]
   Agent A02 → reviewt [A01, A03, ..., A{N}]
   ...
   Agent A{N} → reviewt [A01, A02, ..., A{N-1}]
   ```

**Validierung:**
- [ ] N entspricht draft_count aus metadata.json
- [ ] Assignment-Matrix ist vollständig (jeder Agent hat N-1 Assignments)
- [ ] Kein Agent reviewt seinen eigenen Draft

**Erfolgskriterium:** Review-Matrix konfiguriert, alle Parameter gesetzt

---

### Schritt 2: Cross-Review ausführen (Multi-Agent)

**Ziel:** N Review-Agents parallel ausführen, jeder führt N-1 Reviews durch

**Agent-Briefing (gilt für alle Modi):**
```
Du bist Review-Agent A{NN} mit Rolle: {agent_roles[NN]}.
Du reviewst {N-1} Drafts für Kapitel {current_chapter}.

DEINE AUFGABE:
- Lies alle {N-1} anderen Drafts (draft-A{XX}.md, XX ≠ NN)
- Bewerte JEDEN Draft auf 5 Dimensionen (Score 0-10):

1. QUELLEN-TREUE (0-10)
   - Sind alle Citations korrekt referenziert?
   - Sind Aussagen durch Quellen belegt?
   - Werden Quellen angemessen interpretiert?

2. THEMEN-ABDECKUNG (0-10)
   - Sind alle Sections aus dem Model vorhanden?
   - Wird das Kapitel-Thema vollständig behandelt?
   - Fehlen wichtige Aspekte?

3. SPRACHLICHE QUALITÄT (0-10)
   - Ist der Text akademisch formuliert?
   - Ist die Terminologie präzise und konsistent?
   - Gibt es Grammatik- oder Stilfehler?

4. ARGUMENTATION (0-10)
   - Ist der Aufbau logisch?
   - Gibt es einen roten Faden?
   - Sind Übergänge zwischen Absätzen klar?

5. ORIGINALITÄT (0-10)
   - Bietet der Draft eine einzigartige Perspektive?
   - Gibt es kreative Verknüpfungen?
   - Unterscheidet sich der Draft von anderen?

SCORING:
- Pro Dimension: Integer 0-10
- Gesamt-Score: Gewichteter Durchschnitt:
  Quellen-Treue × 0.30 +
  Themen-Abdeckung × 0.25 +
  Sprachliche Qualität × 0.20 +
  Argumentation × 0.15 +
  Originalität × 0.10

OUTPUT FORMAT (JSON):
{
  "reviewer": "A{NN}",
  "reviewer_role": "{agent_roles[NN]}",
  "reviews": [
    {
      "draft_id": "A{XX}",
      "draft_role": "{agent_roles[XX]}",
      "scores": {
        "quellen_treue": 8,
        "themen_abdeckung": 7,
        "sprachliche_qualitaet": 9,
        "argumentation": 8,
        "originalitaet": 6
      },
      "gesamt_score": 7.7,
      "feedback": {
        "staerken": ["Punkt 1", "Punkt 2", ...],
        "schwaechen": ["Punkt 1", "Punkt 2", ...],
        "empfehlungen": ["Punkt 1", "Punkt 2", ...]
      }
    },
    ... (N-1 Reviews total)
  ]
}
```

### Schritt 2a: SOLO-Modus (User ruft /_WP_review direkt auf)

**Parallel-Spawning (M4):**
- Spawne alle N Agents gleichzeitig via Task-Tool
- Jeder Agent arbeitet unabhängig
- Kein sequenzielles Warten zwischen Agents
- Output sammeln: Pro Agent `output/reviews/chapter-{N}/agent-A{NN}-reviews.json`

### Schritt 2b: WORKER-REVIEWER-Modus (Task "WP Cross-Review (Agent A{NN})")

Du bist Review-Agent {REVIEWER_ID} mit Rolle {REVIEWER_ROLE}.
Kein Spawning. Führe nur DEINE eigenen Reviews durch:

1. Lies alle anderen `draft-A{XX}.md` (alle außer draft-{REVIEWER_ID}.md)
2. Bewerte jeden Draft auf 5 Dimensionen (Scoring wie im Agent-Briefing oben)
3. Schreibe `output/reviews/chapter-{N}/agent-{REVIEWER_ID}-reviews.json`
4. Schreibe KEINE anderen Dateien (kein review-matrix.json, kein review-summary.md)

**Output sammeln:**
- Pro Agent: `output/reviews/chapter-{N}/agent-A{NN}-reviews.json`
- Falls Agent fehlschlägt: NON-BLOCKING Warning + reduzierte Matrix

**Validierung:**
- [ ] Pro Agent: genau (N-1) Reviews produziert
- [ ] Alle Scores sind Integer 0-10
- [ ] Gesamt-Score ist korrekt berechnet (gewichteter Durchschnitt)
- [ ] Feedback enthält mindestens 1 Stärke + 1 Schwäche pro Review

**Erfolgskriterium:** Mindestens (N-1) Agents haben erfolgreich reviewt (1 Ausfall tolerierbar)

**Fallback:** Falls Agent fehlschlägt → speichere Warning in metadata, fahre fort

---

### Schritt 3: Score-Aggregation & Ranking

**Ziel:** Pro Draft Gesamt-Score berechnen, Drafts ranken, Top-K selektieren

**Aktionen:**
1. **Pro Draft A{XX}:**
   - Sammle alle Reviewer-Scores für Draft A{XX} aus allen `agent-A{NN}-reviews.json`
   - Berechne Draft-Score = Durchschnitt aller Reviewer-Gesamt-Scores
   - Beispiel (Draft A01):
     ```
     Reviewer A02 → 7.5
     Reviewer A03 → 8.0
     Reviewer A04 → 7.2
     → Draft-Score A01 = (7.5 + 8.0 + 7.2) / 3 = 7.57
     ```

2. **Ranking erstellen:**
   - Sortiere alle Drafts nach Draft-Score (absteigend)
   - Beispiel:
     ```
     Rank 1: A03 (8.25)
     Rank 2: A01 (7.57)
     Rank 3: A02 (6.83)
     ```

3. **Min-Score Filter anwenden:**
   - Entferne Drafts mit Draft-Score < Min-Score (difficulty-abhängig)
   - Falls kein Draft Min-Score erreicht → BLOCKING Error

4. **Top-K Selektion:**
   - Wähle Top-K Drafts aus Ranking (difficulty-abhängig)
   - easy: Top-1
   - normal: Top-2
   - hard: Top-3
   - Falls weniger als K Drafts verfügbar → nimm alle verfügbaren

**Validierung:**
- [ ] Draft-Score für alle N Drafts berechnet
- [ ] Ranking ist absteigend sortiert
- [ ] Top-K enthält mindestens 1 Draft
- [ ] Alle Top-K Drafts erfüllen Min-Score

**Erfolgskriterium:** Top-K Liste erstellt, mindestens 1 Draft selektiert

**Fallback:** Falls 0 Drafts Min-Score erreichen → BLOCKING Error + empfehle niedrigere difficulty

---

### Schritt 4: Review-Report generieren

**Ziel:** Human-readable Summary + maschinell-lesbare Matrix schreiben

**Aktionen:**
1. **Schreibe `output/reviews/chapter-{N}/review-matrix.json`:**
   ```json
   {
     "chapter": N,
     "difficulty": "normal",
     "agent_count": 5,
     "total_reviews": 20,
     "min_score_threshold": 7.0,
     "top_k": 2,
     "drafts": [
       {
         "draft_id": "A03",
         "draft_role": "Critical Analyst",
         "draft_score": 8.25,
         "rank": 1,
         "selected_for_synthesis": true,
         "reviewer_scores": [
           {"reviewer": "A01", "score": 8.5},
           {"reviewer": "A02", "score": 7.8},
           {"reviewer": "A04", "score": 8.2},
           {"reviewer": "A05", "score": 8.5}
         ],
         "dimension_averages": {
           "quellen_treue": 8.3,
           "themen_abdeckung": 8.5,
           "sprachliche_qualitaet": 8.0,
           "argumentation": 8.2,
           "originalitaet": 8.5
         }
       },
       ... (all N drafts)
     ],
     "cross_review_matrix": [
       ["—", 7.5, 8.0, 7.2, 8.5],
       [8.5, "—", 6.5, 7.0, 7.8],
       [9.0, 7.0, "—", 8.2, 8.0],
       [7.8, 7.5, 8.5, "—", 7.2],
       [8.2, 7.8, 8.0, 7.5, "—"]
     ]
   }
   ```

2. **Schreibe `output/reviews/chapter-{N}/review-summary.md`:**
   ```markdown
   # Review Summary - Kapitel {N}

   **Difficulty:** {difficulty}
   **Agent Count:** {N}
   **Total Reviews:** {N×(N-1)}
   **Min Score Threshold:** {min_score}
   **Top-K Selection:** {K}

   ---

   ## Ranking

   | Rank | Draft | Role | Score | Selected |
   |------|-------|------|-------|----------|
   | 1 | A03 | Critical Analyst | 8.25 | ✓ |
   | 2 | A01 | Synthesizer | 7.57 | ✓ |
   | 3 | A02 | Detail Expert | 6.83 | ✗ |
   | ... | ... | ... | ... | ... |

   ---

   ## Top-K Drafts (Selected for Synthesis)

   ### Draft A03 (Rank 1, Score 8.25)
   **Role:** Critical Analyst

   **Dimension Averages:**
   - Quellen-Treue: 8.3 / 10
   - Themen-Abdeckung: 8.5 / 10
   - Sprachliche Qualität: 8.0 / 10
   - Argumentation: 8.2 / 10
   - Originalität: 8.5 / 10

   **Stärken (aggregiert):**
   - Exzellente Quellenarbeit mit präzisen Citations
   - Vollständige Abdeckung aller Model-Sections
   - Kreative Verknüpfung von Konzepten

   **Schwächen (aggregiert):**
   - Einzelne Absätze könnten kompakter formuliert sein
   - Gelegentlich redundante Formulierungen

   **Empfehlungen:**
   - Sprachliche Straffung in Sektion 2.3
   - Übergänge zwischen Absätzen optimieren

   ---

   (Repeat for all Top-K drafts)

   ---

   ## Excluded Drafts

   | Draft | Role | Score | Reason |
   |-------|------|-------|--------|
   | A05 | Detail Expert | 5.8 | Below min score (6.0) |

   ---

   ## Review Statistics

   - **Average Draft Score:** 7.3
   - **Highest Score:** 8.25 (A03)
   - **Lowest Score:** 5.8 (A05)
   - **Standard Deviation:** 0.9

   ---

   ## Next Steps

   1. Run `/_WP_synthesis` to merge Top-{K} drafts
   2. Top-K drafts will be used as input for synthesis
   3. Excluded drafts are archived for reference
   ```

**Validierung:**
- [ ] JSON ist valide und enthält alle N Drafts
- [ ] Markdown ist formatiert und human-readable
- [ ] Top-K Drafts sind klar markiert
- [ ] Dimension Averages sind korrekt berechnet

**Erfolgskriterium:** Beide Dateien geschrieben, Report ist vollständig

---

### Schritt 5: State aktualisieren (M6 Reihenfolge)

**Ziel:** Manifest und Session-State mit Review-Ergebnissen aktualisieren

**Aktionen (exakt in dieser Reihenfolge, M6 State-Update-Pattern):**

1. **OUTPUT (bereits in Schritt 4 geschrieben):**
   - `output/reviews/chapter-{N}/review-matrix.json`
   - `output/reviews/chapter-{N}/review-summary.md`
   - `output/reviews/chapter-{N}/agent-A{NN}-reviews.json` (pro Agent)

2. **UPDATE `_manifest.md`:**
   ```markdown
   ## Current Status
   - current_chapter: {N}
   - phase: core_transformation
   - step: review_completed
   - next_step: synthesis
   - quality_iteration: {Q}

   ## Review Results (Kapitel {N})
   - review_completed: true
   - top_k_count: {K}
   - top_k_drafts: ["A03", "A01"]
   - average_score: 7.3
   - min_score_threshold: 7.0
   - excluded_drafts: ["A05"]
   ```

3. **UPDATE `session-state.json`:**
   ```json
   {
     "current_chapter": N,
     "difficulty": "normal",
     "phase": "core_transformation",
     "step": "review_completed",
     "next_step": "synthesis",
     "review_results": {
       "top_k_drafts": ["A03", "A01"],
       "ranking": [
         {"draft": "A03", "score": 8.25, "rank": 1},
         {"draft": "A01", "score": 7.57, "rank": 2}
       ],
       "average_score": 7.3,
       "excluded_count": 1
     },
     "timestamp": "2026-02-09T14:30:00Z"
   }
   ```

4. **NOTIFY (Success/Warning/Error basierend auf Ergebnis):**
   - Success: `✓ Cross-Review completed: {N} drafts ranked, Top-{K} selected for synthesis`
   - Warning: `⚠ {X} reviews failed, matrix reduced but proceeding`
   - Error: `✗ No drafts reached min score ({min_score}), consider lowering difficulty`

**Validierung:**
- [ ] _manifest.md enthält review_completed: true
- [ ] session-state.json enthält top_k_drafts Array
- [ ] next_step ist "synthesis"
- [ ] NOTIFY Nachricht ist ausgegeben

**Erfolgskriterium:** State konsistent aktualisiert, nächster Schritt klar

---

## OUTPUT-FORMAT

### review-matrix.json Schema
```json
{
  "chapter": INTEGER,
  "difficulty": STRING (easy|normal|hard),
  "agent_count": INTEGER,
  "total_reviews": INTEGER,
  "min_score_threshold": FLOAT,
  "top_k": INTEGER,
  "drafts": [
    {
      "draft_id": STRING (A{NN}),
      "draft_role": STRING,
      "draft_score": FLOAT (0-10, 2 Dezimalstellen),
      "rank": INTEGER,
      "selected_for_synthesis": BOOLEAN,
      "reviewer_scores": [
        {"reviewer": STRING, "score": FLOAT}
      ],
      "dimension_averages": {
        "quellen_treue": FLOAT,
        "themen_abdeckung": FLOAT,
        "sprachliche_qualitaet": FLOAT,
        "argumentation": FLOAT,
        "originalitaet": FLOAT
      }
    }
  ],
  "cross_review_matrix": ARRAY[ARRAY[FLOAT|STRING]] (NxN, diagonal="—")
}
```

### agent-A{NN}-reviews.json Schema
```json
{
  "reviewer": STRING (A{NN}),
  "reviewer_role": STRING,
  "reviews": [
    {
      "draft_id": STRING (A{XX}),
      "draft_role": STRING,
      "scores": {
        "quellen_treue": INTEGER (0-10),
        "themen_abdeckung": INTEGER (0-10),
        "sprachliche_qualitaet": INTEGER (0-10),
        "argumentation": INTEGER (0-10),
        "originalitaet": INTEGER (0-10)
      },
      "gesamt_score": FLOAT (gewichteter Durchschnitt),
      "feedback": {
        "staerken": ARRAY[STRING],
        "schwaechen": ARRAY[STRING],
        "empfehlungen": ARRAY[STRING]
      }
    }
  ]
}
```

---

## QUALITÄTSKRITERIEN

### Pre-Flight Checks
- [ ] Alle N Drafts aus output/drafts/chapter-{N}/ eingelesen
- [ ] metadata.json konsistent mit tatsächlichen Dateien
- [ ] difficulty ist valid (easy|normal|hard)
- [ ] Agent-Count entspricht difficulty

### Review-Execution Checks
- [ ] SOLO-Modus: N Review-Agents parallel gespawnt (M4)
      WORKER-REVIEWER-Modus: `agent-A{NN}-reviews.json` existiert (N-1 Reviews)
      WORKER-SYNTHESIST-Modus: `review-matrix.json` und `review-summary.md` existieren
- [ ] Jeder Agent hat (N-1) Reviews produziert
- [ ] Alle Scores sind Integer 0-10 (vor Aggregation)
- [ ] Gesamt-Scores korrekt berechnet (gewichteter Durchschnitt)
- [ ] Feedback enthält Stärken + Schwächen pro Review

### Score-Aggregation Checks
- [ ] Draft-Score pro Draft berechnet (Durchschnitt aller Reviewer-Scores)
- [ ] Ranking absteigend sortiert
- [ ] Min-Score Filter angewendet
- [ ] Top-K korrekt selektiert (difficulty-abhängig)
- [ ] Mindestens 1 Draft in Top-K (sonst BLOCKING Error)

### Output Checks
- [ ] review-matrix.json ist valides JSON
- [ ] cross_review_matrix ist NxN (diagonal="—")
- [ ] review-summary.md ist formatiert und vollständig
- [ ] Alle Top-K Drafts haben Dimension Averages
- [ ] Excluded Drafts mit Grund dokumentiert

### State-Update Checks (M6 Reihenfolge)
- [ ] OUTPUT zuerst geschrieben
- [ ] _manifest.md danach aktualisiert (review_completed: true)
- [ ] session-state.json zuletzt aktualisiert (top_k_drafts Array)
- [ ] next_step ist "synthesis"
- [ ] NOTIFY ausgeführt

---

## NOTIFY

### Success (NOTIFY wenn alles erfolgreich)
```
✓ Cross-Review completed for Chapter {N}
  - {N} drafts ranked
  - Top-{K} selected for synthesis: {draft_ids}
  - Average score: {avg_score}
  - Next: Run /_WP_synthesis
```

### Warning (NOTIFY wenn partieller Erfolg)
```
⚠ Cross-Review completed with warnings for Chapter {N}
  - {X} review agents failed, matrix reduced
  - Top-{K} selected: {draft_ids}
  - Recommendation: Verify review quality manually
```

### Error (NOTIFY + STOP bei kritischen Fehlern)
```
✗ Cross-Review failed for Chapter {N}
  - Reason: {error_reason}
  - Action: {recommended_action}
  - Examples:
    - "No drafts found" → "Run /_WP_write first"
    - "No draft reached min score" → "Lower difficulty or re-run quality loop"
    - "All reviews failed" → "Check agent configuration"
```

---

## ERROR HANDLING

| Kategorie | Trigger | Response | NOTIFY |
|-----------|---------|----------|--------|
| **BLOCKING** | 0 Drafts vorhanden | STOP + NOTIFY Error + empfehle /_WP_write | ✗ ERROR |
| **BLOCKING** | output/drafts/ fehlt | STOP + NOTIFY Error + prüfe Setup | ✗ ERROR |
| **BLOCKING** | 0 Drafts erreichen Min-Score | STOP + NOTIFY Error + empfehle niedrigere difficulty | ✗ ERROR |
| **BLOCKING** | Alle Reviews fehlgeschlagen | STOP + NOTIFY Error + prüfe Agent-Config | ✗ ERROR |
| **NON-BLOCKING** | 1 Agent-Review fehlgeschlagen | CONTINUE + reduzierte Matrix + Warning | ⚠ WARNING |
| **NON-BLOCKING** | 1-2 Reviews pro Draft fehlen | CONTINUE + Score-Berechnung mit verfügbaren Reviews | ⚠ WARNING |
| **FALLBACK** | Alle Reviews für 1 Draft fehlgeschlagen | Draft bekommt Score 0.0 + nicht in Top-K | ℹ INFO |
| **FALLBACK** | Top-K > verfügbare Drafts über Min-Score | Nimm alle verfügbaren Drafts | ℹ INFO |

---

## HINWEISE

### Difficulty-Scaling Referenz
| Difficulty | Agents | Reviews/Agent | Total Reviews | Min-Score | Top-K |
|------------|--------|---------------|---------------|-----------|-------|
| easy       | 3      | 2 (N-1)       | 6             | 6.0       | 1     |
| normal     | 5      | 4 (N-1)       | 20            | 7.0       | 2     |
| hard       | 9      | 8 (N-1)       | 72            | 7.5       | 3     |

### Score-Gewichtung (für Agent-Briefing)
```
Gesamt-Score =
  Quellen-Treue      × 0.30 (wichtigste Dimension, akademische Integrität)
+ Themen-Abdeckung   × 0.25 (Vollständigkeit)
+ Sprachliche Qualität × 0.20 (Lesbarkeit)
+ Argumentation      × 0.15 (Struktur)
+ Originalität       × 0.10 (Kreativität, niedrigste Priorität)
```

### Pipeline-Kontext
```
QUALITY-LOOP (bis CONVERGED):
  /_WP_visual → /_WP_convergence (prüft Konvergenz)
  → wenn RETRY → zurück zu /_WP_write (neue Drafts)
  → wenn CONVERGED → weiter zu /_WP_review (HIER)

POST-REVIEW:
  /_WP_review → /_WP_synthesis (Top-K mergen)
  → /_WP_reflect (Meta-Analyse)
  → zurück zu /_WP_orchestrate (nächstes Kapitel oder Feature-Ende)
```

### Multi-Agent Pattern (M2 + M4)
- **M2 (Multi-Agent-Review):** N Agents produzieren N×(N-1) Cross-Reviews
- **M4 (Parallel-Spawning):** Alle N Agents gleichzeitig starten, keine sequenzielle Abhängigkeit
- Cross-Review Matrix ist KERN-Feature (jeder reviewt jeden)
- Dimension-basiertes Scoring (5 Dimensionen, gewichtet)

### State-Update Pattern (M6)
1. OUTPUT schreiben (review-matrix.json, review-summary.md)
2. _manifest.md aktualisieren (review_completed, top_k_drafts)
3. session-state.json aktualisieren (review_results)
4. NOTIFY ausführen

### Referenzen
- Model: WritePaper_Model.md (M2 Multi-Agent-Review, M4 Parallel-Spawning, M6 State-Update)
- Spec: WritePaper_Spec_v1.1.md (W2 Pipeline-Position, W3 Difficulty-Scaling)
- Blueprint: /_WP_write.md (Struktur-Vorlage)
- Previous: /_WP_convergence.md (Quality-Loop Entscheidung)
- Next: /_WP_synthesis.md (Top-K Merger)

---

**Command-Operator:** Sonnet 4.5
**Command-Version:** 1.0.0
**Letzte Änderung:** 2026-02-09
