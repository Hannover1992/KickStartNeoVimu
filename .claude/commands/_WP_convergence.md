# /_WP_convergence - Quality Loop Convergence Controller

```yaml
status: active
version: 1.0.0
created: 2026-02-10
op: WritePaper
phase: Core Transformation
type: convergence
chain_position: convergence
difficulty_scaling: true
mcp_critical: false
loop_controller: true
loop_level: INNER
decision_type: true
```

---

```
╔══════════════════════════════════════════════════════════════════════════╗
║ VERTRAG: /_WP_convergence                                             ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ ACTOR: CONVERGENCE CONTROLLER                                            ║
║   TUT:                                                                   ║
║     - quality_history[] Array pflegen (Score + Delta + Timestamp)        ║
║     - Delta berechnen (current_score - previous_score)                   ║
║     - Stagnation erkennen (delta < epsilon fuer k Iterationen)          ║
║     - Decision treffen: CONVERGE / ITERATE / FORCE                      ║
║     - ITERATE → write direkt routen (autoGen deferred, C9+)            ║
║     - CONVERGE → review routen (Loop beendet)                           ║
║     - FORCE → review routen mit WARNUNG (Loop erzwungen)               ║
║     - Optional HiL bei FORCE (CONTINUE/RETRY/ABORT)                    ║
║   NICHT:                                                                 ║
║     - Quality Gates evaluieren (→ qualityGate)                          ║
║     - Drafts schreiben oder verbessern (→ write, autoGen)              ║
║     - Drafts reviewen oder ranken (→ review)                           ║
║     - Figures generieren (→ visual)                                     ║
║     - Gap-Analyse durchfuehren (→ chapterGap)                          ║
║   ESKALIERT:                                                             ║
║     - quality-report.json fehlt → STOP + empfehle /_WP_qualityGate  ║
║     - quality_iteration > max → FORCE Decision                         ║
║     - Stagnation erkannt → FORCE Decision + WARNUNG                    ║
║                                                                          ║
║ LIEST (Input) - PFLICHT:                                                 ║
║   1. _manifest.md (current_chapter, phase, quality_iteration)           ║
║   2. session-state.json (difficulty, quality_history,                    ║
║      quality_iteration, stagnation_count)                               ║
║   3. output/quality/chapter-{N}/quality-report.json (Gate-Results)     ║
║                                                                          ║
║ SCHREIBT (Output) - PFLICHT:                                             ║
║   1. output/quality/chapter-{N}/convergence-decision.json              ║
║   2. _manifest.md (UPDATE: convergence_decision, next_step)             ║
║   3. session-state.json (UPDATE: quality_history, quality_iteration,    ║
║      stagnation_count, convergence_decision)                            ║
║                                                                          ║
║ POSITION:                                                                ║
║   TYPE: LOOP                                                             ║
║   LOOP-CONTEXT:                                                          ║
║     LOOP-NAME: Quality-Loop                                              ║
║     LOOP-LEVEL: INNER                                                    ║
║     ITERATION-VARIABLE: quality_iteration                                ║
║     MAX-ITERATIONS: 2 (easy) | 3 (normal) | 5 (hard)                  ║
║   ENTRY:                                                                 ║
║     NORMAL: /_WP_qualityGate → THIS                                  ║
║   EXIT:                                                                  ║
║     CONVERGE: THIS → /_WP_review (Qualitaet ausreichend)            ║
║     ITERATE: THIS → /_WP_write (weitere Iteration noetig)           ║
║     FORCE: THIS → /_WP_review (max Iterations oder Stagnation)      ║
║   PHASE: Core Transformation                                            ║
║   CHAIN: [qualityGate] → [convergence] → [review|write]               ║
║                                                                          ║
║ ENTSCHEIDET:                                                             ║
║   Decision-Table:                                                        ║
║   ┌─────────────────────────────────────────┬──────────┬──────────────┐ ║
║   │ Bedingung                                │ Decision │ Next Step    │ ║
║   ├─────────────────────────────────────────┼──────────┼──────────────┤ ║
║   │ composite >= threshold                   │ CONVERGE │ review       │ ║
║   │   AND overall_result == QUALITY_PASSED   │          │              │ ║
║   │ quality_iteration >= max_iterations      │ FORCE    │ review(WARN) │ ║
║   │ stagnation_count >= stagnation_limit     │ FORCE    │ review(WARN) │ ║
║   │ delta >= epsilon (Fortschritt)           │ ITERATE  │ write        │ ║
║   │ delta < epsilon (kein Fortschritt)       │ ITERATE  │ write        │ ║
║   │   (stagnation_count incremented)         │          │ (+ WARNUNG)  │ ║
║   └─────────────────────────────────────────┴──────────┴──────────────┘ ║
║                                                                          ║
║ MCP-BREMSE: N/A (kein MCP-Verbrauch)                                   ║
║                                                                          ║
║ HiL-PAUSE:                                                               ║
║   Trigger: FORCE Decision                                                ║
║   Optionen: CONTINUE (→ review) | RETRY (→ write) | ABORT (→ STOP)    ║
║   Timeout: 5 min (Default: CONTINUE)                                    ║
║   Status: OPTIONAL (User-Interaktion nur bei FORCE)                     ║
║                                                                          ║
║ SCHWIERIGKEIT:                                                           ║
║   easy:   max_iterations=2, threshold=6.0                               ║
║   normal: max_iterations=3, threshold=7.0                               ║
║   hard:   max_iterations=5, threshold=7.5                               ║
║   Stagnation-Parameter (alle Schwierigkeitsgrade):                      ║
║     epsilon: 0.3 (minimaler Fortschritt)                                ║
║     stagnation_limit: 2 (max aufeinanderfolgende Stagnationen)          ║
║                                                                          ║
║ NOTIFY:                                                                  ║
║   powershell -Command "notify 'WritePaper Kapitel {N} Convergence:     ║
║   {CONVERGE|ITERATE|FORCE} (Score {composite}/10, Iter {I}/{max})'"    ║
║                                                                          ║
║ TAGS:                                                                    ║
║   type: convergence                                                      ║
║   op: WritePaper                                                         ║
║   chapter: {N}                                                           ║
║   chain-position: convergence                                            ║
║   loop-level: INNER                                                      ║
║   loop-controller: true                                                  ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## Verantwortlichkeit

**TUT (Claude):**
- Liest quality-report.json fuer aktuellen Composite Score und Gate-Results
- Pflegt quality_history[] Array (Score + Delta + Timestamp pro Iteration)
- Berechnet Delta: `current_score - previous_score` (0 bei erster Iteration)
- Prueft Stagnation: `delta < epsilon` fuer `stagnation_limit` aufeinanderfolgende Iterationen
- Evaluiert Decision-Table (CONVERGE/ITERATE/FORCE)
- Routet ITERATE → write direkt (autoGen nicht implementiert, C9+)
- Routet CONVERGE und FORCE → review
- Generiert convergence-decision.json mit History und Begruendung
- Aktualisiert _manifest.md und session-state.json nach M6 Reihenfolge
- Optional: HiL bei FORCE (User-Entscheidung CONTINUE/RETRY/ABORT)

**TUT NICHT (Claude):**
- Quality Gates evaluieren (→ `/_WP_qualityGate`)
- Drafts schreiben oder verbessern (→ `/_WP_write`, `/_WP_autoGen`)
- Drafts reviewen oder ranken (→ `/_WP_review`)
- Figures generieren (→ `/_WP_visual`)
- Gap-Analyse oder Wissens-Model (→ `/_WP_chapterGap`, `/_WP_chapterModel`)
- autoGen ausfuehren (→ `/_WP_autoGen`, nicht implementiert C8)

**ESKALATION:**
- quality-report.json fehlt → BLOCKING STOP + empfehle `/_WP_qualityGate` zuerst
- session-state.json fehlt quality_history → Default: leeres Array (erste Iteration)
- quality_iteration undefiniert → Default: 0 (erste Iteration)
- stagnation_count undefiniert → Default: 0

---

## Ablauf

### Schritt 0: Inputs lesen

**Ziel:** Quality-Report und History-Daten laden

**Aktionen:**
1. Lies `_manifest.md` → `current_chapter`, `phase`, `quality_iteration`
2. Lies `session-state.json`:
   - `difficulty` (easy|normal|hard)
   - `quality_history` (Array mit bisherigen Scores, Default: [])
   - `quality_iteration` (aktuelle Iteration, Default: 0)
   - `stagnation_count` (aufeinanderfolgende Stagnationen, Default: 0)
3. Lies `output/quality/chapter-{N}/quality-report.json`:
   - `composite_score`
   - `overall_result` (QUALITY_PASSED | QUALITY_FAILED)
   - `gates_passed`, `gates_failed`
   - `composite_threshold`

**Validierung:**
- quality-report.json muss existieren → sonst BLOCKING STOP
- difficulty muss gesetzt sein (easy|normal|hard) → sonst Default: normal
- quality-report muss fuer aktuelles Kapitel sein → sonst FEHLER

**Erfolgskriterium:**
- Composite Score, Overall Result und Gate-Results geladen
- quality_history Array verfuegbar (leer oder mit bisherigen Eintraegen)
- Difficulty und Stagnation-Parameter bestimmt

---

### Schritt 1: History aktualisieren

**Ziel:** Aktuellen Score in quality_history[] eintragen

**Aktionen:**
1. Erstelle neuen History-Eintrag:
   ```json
   {
     "iteration": quality_iteration,
     "composite_score": composite_score,
     "overall_result": "QUALITY_PASSED|QUALITY_FAILED",
     "gates_passed": N,
     "gates_failed": M,
     "timestamp": "2026-02-10T12:00:00Z"
   }
   ```

2. Berechne Delta:
   ```
   IF quality_history.length == 0:
       delta = 0  # Erste Iteration, kein Vergleich moeglich
   ELSE:
       previous_score = quality_history[last].composite_score
       delta = composite_score - previous_score
   ```

3. Ergaenze History-Eintrag um Delta:
   ```json
   {
     "iteration": 1,
     "composite_score": 7.8,
     "delta": 0.6,
     "overall_result": "QUALITY_PASSED",
     "gates_passed": 8,
     "gates_failed": 0,
     "timestamp": "2026-02-10T12:30:00Z"
   }
   ```

4. Fuege Eintrag zu quality_history[] hinzu

**Erfolgskriterium:**
- History-Eintrag mit Score, Delta, Timestamp erstellt
- quality_history[] Array aktualisiert
- Delta korrekt berechnet (0 bei erster Iteration)

---

### Schritt 2: Stagnation-Pruefung

**Ziel:** Erkennen ob Qualitaet stagniert

**Aktionen:**
1. Bestimme Stagnation-Parameter:
   ```
   epsilon = 0.3        # Minimaler Fortschritt (alle Schwierigkeitsgrade)
   stagnation_limit = 2  # Max aufeinanderfolgende Stagnationen
   ```

2. Pruefe aktuellen Delta gegen epsilon:
   ```
   IF delta < epsilon AND quality_iteration > 0:
       stagnation_count += 1
       stagnation_detected = true
   ELSE:
       stagnation_count = 0  # Reset bei Fortschritt
       stagnation_detected = false
   ```

3. Pruefe ob Stagnation-Limit erreicht:
   ```
   stagnation_limit_reached = (stagnation_count >= stagnation_limit)
   ```

**Sonderfaelle:**
- Erste Iteration (quality_iteration == 0): Kein Stagnation-Check moeglich, delta = 0, stagnation_count bleibt 0
- Negativer Delta (Score verschlechtert): Zaehlt als Stagnation (delta < epsilon)
- Delta genau gleich epsilon (0.3): Zaehlt NICHT als Stagnation (>= epsilon = Fortschritt)

**Erfolgskriterium:**
- stagnation_count korrekt aktualisiert
- stagnation_limit_reached korrekt bestimmt
- Reset bei Fortschritt (delta >= epsilon)

---

### Schritt 3: Decision-Logic

**Ziel:** Naechsten Schritt in der Pipeline bestimmen

**Aktionen:**
1. Bestimme max_iterations und threshold aus difficulty:

   | Difficulty | max_iterations | threshold |
   |------------|---------------|-----------|
   | easy       | 2             | 6.0       |
   | normal     | 3             | 7.0       |
   | hard       | 5             | 7.5       |

2. Evaluiere Decision-Table (Prioritaet beachten):

   | # | Bedingung | Decision | Next Step | Bemerkung |
   |---|-----------|----------|-----------|-----------|
   | D1 | composite_score >= threshold AND overall_result == QUALITY_PASSED | **CONVERGE** | review | Qualitaet erreicht |
   | D2 | quality_iteration >= max_iterations | **FORCE** | review (WARN) | Max Iterations |
   | D3 | stagnation_limit_reached | **FORCE** | review (WARN) | Stagnation |
   | D4 | delta >= epsilon (Fortschritt) | **ITERATE** | write | Weitere Iteration |
   | D5 | delta < epsilon (kein Fortschritt, unter Limit) | **ITERATE** | write (WARN) | Stagnation-WARNUNG |

3. **Prioritaet:** D1 vor D2 vor D3 vor D4 vor D5
   - D1 (CONVERGE) hat hoechste Prioritaet: Qualitaet erreicht → Loop beendet
   - D2/D3 (FORCE) vor D4/D5 (ITERATE): Abbruch-Bedingungen vor Weiter-Machen

4. Bei **CONVERGE:**
   - next_step = "review"
   - Nachricht: "Qualitaet erreicht ({composite}/10 >= {threshold}). Weiter zu Review."
   - quality_iteration bleibt (wird von review/synthesis nicht veraendert)

5. Bei **FORCE:**
   - next_step = "review" (mit WARNUNG)
   - force_reason = "max_iterations" | "stagnation"
   - WARNUNG: "FORCE: Qualitaet {composite}/10 unter Threshold {threshold}. Grund: {force_reason}."
   - **Optional HiL (siehe Schritt 3a)**

6. Bei **ITERATE:**
   - next_step = "write"
   - quality_iteration += 1
   - Nachricht: "Iteration {I}: Score {composite}/10, Delta {delta}. Weiter zu Write."
   - Falls delta < epsilon: Zusatz-WARNUNG "Stagnation erkannt ({stagnation_count}/{stagnation_limit})"

**Erfolgskriterium:**
- Genau 1 Decision getroffen (CONVERGE, ITERATE, oder FORCE)
- next_step korrekt gesetzt (review oder write)
- WARNUNG bei FORCE und bei ITERATE mit Stagnation

---

### Schritt 3a: Optional HiL bei FORCE

**Ziel:** User-Entscheidung bei erzwungenem Loop-Abbruch

**Bedingung:** NUR bei FORCE Decision

**Aktionen:**
1. Zeige User Summary:
   ```
   FORCE CONVERGENCE - Kapitel {N}
   Score: {composite}/10 (Threshold: {threshold})
   Iterations: {quality_iteration}/{max_iterations}
   Stagnation: {stagnation_count}/{stagnation_limit}
   Force-Grund: {force_reason}
   Quality History: {quality_history als Tabelle}
   ```

2. Biete Optionen (AskUserQuestion, OPTIONAL):
   - **CONTINUE** (Default): Weiter zu review mit aktueller Qualitaet
   - **RETRY**: Eine weitere Iteration zu write (ignoriert max_iterations)
   - **ABORT**: Pipeline stoppen, manuelles Eingreifen

3. Bei Timeout (5 min): Default CONTINUE

4. Verarbeite User-Entscheidung:
   - CONTINUE: next_step = "review" (FORCE bleibt)
   - RETRY: next_step = "write", quality_iteration += 1, force_reason = null
   - ABORT: next_step = "STOPPED", NOTIFY Error

**Hinweis:** HiL bei FORCE ist OPTIONAL. Falls Claude im Batch-Modus laeuft oder keine User-Interaktion moeglich ist, wird Default CONTINUE angewendet.

---

### Schritt 4: State aktualisieren (M6 Reihenfolge)

**Ziel:** Convergence-Ergebnis persistent speichern

**Aktionen:**

#### 4a. OUTPUT: convergence-decision.json

Schreibe `output/quality/chapter-{N}/convergence-decision.json`:

```json
{
  "chapter": 1,
  "quality_iteration": 1,
  "difficulty": "hard",
  "timestamp": "2026-02-10T12:30:00Z",
  "composite_score": 7.8,
  "composite_threshold": 7.5,
  "overall_result": "QUALITY_PASSED",
  "delta": 0.6,
  "delta_history": [
    {"iteration": 0, "score": 7.2, "delta": 0},
    {"iteration": 1, "score": 7.8, "delta": 0.6}
  ],
  "stagnation": {
    "epsilon": 0.3,
    "stagnation_limit": 2,
    "stagnation_count": 0,
    "stagnation_limit_reached": false
  },
  "decision": "CONVERGE",
  "force_reason": null,
  "next_step": "review",
  "hil_response": null,
  "quality_history": [
    {
      "iteration": 0,
      "composite_score": 7.2,
      "delta": 0,
      "overall_result": "QUALITY_FAILED",
      "gates_passed": 6,
      "gates_failed": 1,
      "timestamp": "2026-02-10T12:00:00Z"
    },
    {
      "iteration": 1,
      "composite_score": 7.8,
      "delta": 0.6,
      "overall_result": "QUALITY_PASSED",
      "gates_passed": 8,
      "gates_failed": 0,
      "timestamp": "2026-02-10T12:30:00Z"
    }
  ]
}
```

#### 4b. _manifest.md UPDATE

```markdown
## Convergence - Kapitel {N}, Iteration {I}
- **Decision:** CONVERGE | ITERATE | FORCE
- **Score:** {composite}/10 (Threshold: {threshold})
- **Delta:** {delta} (epsilon: 0.3)
- **Stagnation:** {stagnation_count}/{stagnation_limit}
- **Force-Grund:** {null | max_iterations | stagnation}
- **Next Step:** review | write
```

#### 4c. session-state.json UPDATE

```json
{
  "last_command": "_WP_convergence",
  "convergence_decision": "CONVERGE|ITERATE|FORCE",
  "quality_iteration": 1,
  "quality_score": 7.8,
  "quality_delta": 0.6,
  "stagnation_count": 0,
  "quality_history": [
    {"iteration": 0, "composite_score": 7.2, "delta": 0, "timestamp": "2026-02-10T12:00:00Z"},
    {"iteration": 1, "composite_score": 7.8, "delta": 0.6, "timestamp": "2026-02-10T12:30:00Z"}
  ],
  "next_step": "review"
}
```

#### 4d. NOTIFY

```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Convergence: {DECISION} (Score {composite}/10, Iter {I}/{max})'"
```

**Erfolgskriterium:**
- convergence-decision.json vollstaendig geschrieben
- _manifest.md und session-state.json aktualisiert
- quality_history[] persistent gespeichert
- NOTIFY gesendet mit Decision

---

## Decision-Table (Referenz)

| # | Score vs Threshold | Iteration vs Max | Stagnation | Decision | Next Step | Bemerkung |
|---|-------------------|------------------|------------|----------|-----------|-----------|
| D1 | >= threshold AND PASSED | any | any | **CONVERGE** | review | Qualitaet erreicht |
| D2 | < threshold | >= max | any | **FORCE** | review (WARN) | Max Iterations |
| D3 | < threshold | < max | >= limit | **FORCE** | review (WARN) | Stagnation |
| D4 | < threshold | < max | < limit, delta >= eps | **ITERATE** | write | Fortschritt |
| D5 | < threshold | < max | < limit, delta < eps | **ITERATE** | write (WARN) | Stagnation-WARNUNG |

**Prioritaet:** D1 > D2 > D3 > D4 > D5

**Loop-Flow bei ITERATE:**
```
convergence → write → visual → qualityGate → convergence
     ↑                                             │
     └──────────── ITERATE (Loop zurueck) ─────────┘
```

**Exit bei CONVERGE oder FORCE:**
```
convergence → review (CONVERGE: Qualitaet gut, FORCE: Max/Stagnation)
```

**Hinweis:** autoGen ist NICHT im Loop (C8). Bei ITERATE geht es direkt zu write.
Geplante Erweiterung (C9+): convergence → autoGen → write statt convergence → write.

---

## Stagnation-Detection (Detail)

### Algorithmus

```
INPUT: quality_history[], current_score, epsilon=0.3, stagnation_limit=2

# Delta berechnen
IF len(quality_history) == 0:
    delta = 0  # Erste Iteration
ELSE:
    previous = quality_history[-1].composite_score
    delta = current_score - previous

# Stagnation pruefen
IF quality_iteration > 0 AND delta < epsilon:
    stagnation_count += 1
ELIF quality_iteration > 0 AND delta >= epsilon:
    stagnation_count = 0  # Reset bei Fortschritt

# Limit pruefen
stagnation_limit_reached = (stagnation_count >= stagnation_limit)
```

### Beispiel-Szenarien

**Szenario A: Normaler Konvergenz-Verlauf (hard)**
```
Iter 0: Score 6.2, Delta 0.0 → ITERATE (erste Iteration)
Iter 1: Score 7.0, Delta 0.8 → ITERATE (Fortschritt, stagnation=0)
Iter 2: Score 7.6, Delta 0.6 → CONVERGE (7.6 >= 7.5 AND PASSED)
```

**Szenario B: Stagnation (hard)**
```
Iter 0: Score 5.5, Delta 0.0 → ITERATE
Iter 1: Score 5.7, Delta 0.2 → ITERATE (delta < 0.3, stagnation=1, WARNUNG)
Iter 2: Score 5.8, Delta 0.1 → FORCE (stagnation=2 >= limit=2)
```

**Szenario C: Max Iterations (normal)**
```
Iter 0: Score 5.0, Delta 0.0 → ITERATE
Iter 1: Score 5.8, Delta 0.8 → ITERATE (Fortschritt)
Iter 2: Score 6.5, Delta 0.7 → FORCE (iter 2 >= max 3... NEIN, iter < max)
Iter 2 nochmal: Score 6.5, Delta 0.7 → ITERATE (6.5 < 7.0, iter 2 < max 3)
Iter 3: quality_iteration >= max_iterations → FORCE (vor D4/D5)
```

**Hinweis:** quality_iteration wird bei ITERATE inkrementiert. D2 prueft VOR Delta-Check.

---

## Output-Format

### output/quality/chapter-{N}/convergence-decision.json

**Zweck:** Convergence-Entscheidung mit vollstaendiger History fuer Traceability

**Schema:**
```json
{
  "chapter": 1,
  "quality_iteration": 1,
  "difficulty": "hard",
  "timestamp": "2026-02-10T12:30:00Z",
  "composite_score": 7.8,
  "composite_threshold": 7.5,
  "overall_result": "QUALITY_PASSED|QUALITY_FAILED",
  "delta": 0.6,
  "delta_history": [
    {"iteration": 0, "score": 7.2, "delta": 0},
    {"iteration": 1, "score": 7.8, "delta": 0.6}
  ],
  "stagnation": {
    "epsilon": 0.3,
    "stagnation_limit": 2,
    "stagnation_count": 0,
    "stagnation_limit_reached": false
  },
  "decision": "CONVERGE|ITERATE|FORCE",
  "force_reason": "null|max_iterations|stagnation",
  "next_step": "review|write|STOPPED",
  "hil_response": "null|CONTINUE|RETRY|ABORT",
  "quality_history": []
}
```

**Konsumenten:**
- `/_WP_write`: Liest bei ITERATE — quality_history fuer Verbesserungs-Fokus
- `/_WP_review`: Liest bei CONVERGE/FORCE — Decision + History fuer Review-Kontext
- `/_WP_reflect`: Liest — Gesamte Convergence-History fuer Kapitel-Retrospektive

---

## Qualitaetskriterien

### Vollstaendigkeit
- [ ] quality-report.json gelesen und Composite Score extrahiert
- [ ] quality_history[] Array aktualisiert mit neuem Eintrag
- [ ] Delta korrekt berechnet (0 bei erster Iteration)
- [ ] Decision getroffen (CONVERGE, ITERATE, oder FORCE)
- [ ] convergence-decision.json geschrieben
- [ ] _manifest.md und session-state.json aktualisiert
- [ ] NOTIFY gesendet

### Korrektheit
- [ ] Delta = current_score - previous_score (nicht umgekehrt)
- [ ] Stagnation-Check: delta < epsilon fuer k aufeinanderfolgende Iterationen
- [ ] stagnation_count Reset bei Fortschritt (delta >= epsilon)
- [ ] Decision-Table Prioritaet: D1 > D2 > D3 > D4 > D5
- [ ] CONVERGE nur bei composite >= threshold AND QUALITY_PASSED
- [ ] FORCE bei max_iterations ODER stagnation_limit_reached
- [ ] max_iterations aus difficulty (2|3|5)
- [ ] threshold aus difficulty (6.0|7.0|7.5)

### Robustheit
- [ ] quality-report.json fehlt → BLOCKING STOP + empfehle qualityGate
- [ ] quality_history leer → Delta = 0, stagnation_count = 0 (erste Iteration)
- [ ] quality_iteration undefiniert → Default: 0
- [ ] stagnation_count undefiniert → Default: 0
- [ ] HiL Timeout bei FORCE → Default: CONTINUE

### Performance
- [ ] Kein MCP-Verbrauch (reines State-Management)
- [ ] O(1) Decision-Logic (keine Iteration ueber Drafts)
- [ ] quality_history O(n) mit n = max_iterations (max 5)

---

## NOTIFY

**CONVERGE:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Convergence: CONVERGE (Score {composite}/10 >= {threshold}, Iter {I})'"
```

**ITERATE:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Convergence: ITERATE (Score {composite}/10, Delta {delta}, Iter {I}/{max})'"
```

**FORCE:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Convergence: FORCE (Score {composite}/10, Grund: {force_reason})'"
```

**Error:**
```powershell
powershell -Command "notify 'WritePaper Kapitel {N} Convergence FAILED: Quality-Report fehlt'"
```

---

## Error Handling

| Kategorie | Trigger | Response | NOTIFY |
|-----------|---------|----------|--------|
| **BLOCKING** | quality-report.json fehlt | STOP + empfehle /_WP_qualityGate | ERROR |
| **BLOCKING** | quality-report.json fuer falsches Kapitel | STOP + Kapitel-Mismatch Warnung | ERROR |
| **FALLBACK** | quality_history fehlt in session-state | Default: [] (erste Iteration) | INFO |
| **FALLBACK** | stagnation_count fehlt | Default: 0 | INFO |
| **FALLBACK** | HiL Timeout bei FORCE | Default: CONTINUE | WARNING |

---

## Hinweise

### Loop-Controller
- convergence ist der INNER-Level Controller fuer den Quality-Loop (W1)
- OUTER-Loop (Retry): Controller ist /_WP_reflect
- MIDDLE-Loop (Gap): Controller ist /_WP_chapterGap
- Max Iterationen: easy=2, normal=3, hard=5 (W1)

### ITERATE ohne autoGen (C8 Einschraenkung)
- autoGen ist nicht implementiert (geplant C9+)
- convergence routet ITERATE → write direkt
- write bekommt quality-report.json als Input fuer Verbesserungen
- Geplante Erweiterung: convergence → autoGen → write (targeted section-rewrite)
- gap-autoGen.json aus qualityGate wird aktuell von write gelesen (manueller Verbesserungsfokus)

### Delta-Interpretation
- Positiver Delta: Verbesserung (gut)
- Delta >= epsilon (0.3): Signifikanter Fortschritt → stagnation_count Reset
- Delta < epsilon: Stagnation → stagnation_count Increment
- Negativer Delta: Verschlechterung → Zaehlt als Stagnation (< epsilon)
- Delta = 0: Keine Veraenderung → Stagnation (bei Iter > 0)

### FORCE Begruendung
- "max_iterations": Pipeline hat max Iterationen erreicht (D2)
- "stagnation": Pipeline stagniert seit {stagnation_limit} Iterationen (D3)
- User wird via NOTIFY gewarnt
- review-Command beruecksichtigt FORCE in seinem Workflow
- FORCE-Grund wird in convergence-decision.json dokumentiert

### Chain-Integration
- ENTRY: qualityGate → convergence (nach Quality-Evaluation)
- EXIT CONVERGE: convergence → review (Qualitaet erreicht)
- EXIT ITERATE: convergence → write (weitere Iteration)
- EXIT FORCE: convergence → review (mit WARNUNG ueber Sub-Threshold-Qualitaet)
- reflect liest convergence-decision.json fuer Kapitel-Retrospektive

### Referenzen
- Model: WritePaper_Model.md (W1 Three Loops, TC4 Convergence-Pattern, M1 Convergence-Loop)
- Blueprint: /_WP_chapterGap.md (Decision-Type, Loop-Controller Pattern)
- Previous: /_WP_qualityGate.md (Quality-Report Input)
- Next CONVERGE: /_WP_review.md (Peer-Review)
- Next ITERATE: /_WP_write.md (Draft-Verbesserung)

---

**Command-Version:** 1.0.0
**Letzte Aenderung:** 2026-02-10
