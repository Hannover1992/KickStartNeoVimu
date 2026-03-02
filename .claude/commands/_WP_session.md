---
status: active
version: 1.0
created: 2026-02-08
updated: 2026-02-08
author: Command-System
tags: [research, writepaper, setup, session-planning]
---

# /_WP_session - Session Parameter Configuration

```
╔══════════════════════════════════════════════════════════════════════════╗
║ VERTRAG: /_WP_session                                                 ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║ ACTOR: SESSION PLANNER                                                   ║
║   TUT:                                                                   ║
║     - Schwierigkeitsgrad festlegen (easy/normal/hard)                    ║
║     - Kapitel-Archetypen erkennen (A: Exploration, B: Technical)         ║
║     - Temperatur-Profil berechnen (Gradient ueber Kapitel)               ║
║     - Agenten-Anzahl pro Kapitel bestimmen                               ║
║   NICHT:                                                                 ║
║     - Commands ausfuehren (nur planen)                                   ║
║     - Quellen recherchieren (→ research)                                 ║
║                                                                          ║
║ LIEST (Input) - PFLICHT:                                                 ║
║   1. _manifest.md                                                        ║
║   2. session-state.json                                                  ║
║   3. config/project.yaml                                                 ║
║   4. User-Input: difficulty (easy|normal|hard)                           ║
║                                                                          ║
║ SCHREIBT (Output) - PFLICHT:                                             ║
║   1. session-state.json (UPDATE: difficulty, dimension-parameters)       ║
║   2. _manifest.md (UPDATE: difficulty, next_step=structure)              ║
║                                                                          ║
║ POSITION:                                                                ║
║   TYPE: LINEAR                                                           ║
║   AFTER: /_WP_init                                                     ║
║   BEFORE: /_WP_structure                                               ║
║   PHASE: Setup                                                           ║
║   CHAIN: [init] → [session] → [structure]                                ║
║                                                                          ║
║ SCHWIERIGKEIT:                                                           ║
║   Speichert Dimensionen fuer alle nachfolgenden Commands:                ║
║   easy:   3 Agents, 2 Quality-Loop, 5 RAG-Queries                       ║
║   normal: 5 Agents, 3 Quality-Loop, 10 RAG-Queries                      ║
║   hard:   9 Agents, 5 Quality-Loop, 20 RAG-Queries                      ║
║                                                                          ║
║ NOTIFY:                                                                  ║
║   powershell -Command "notify 'WritePaper /_WP_session: {difficulty}'" ║
║                                                                          ║
║ TAGS:                                                                    ║
║   type: setup                                                            ║
║   op: WritePaper                                                         ║
║   chain-position: session                                                ║
║   prev: "[[WritePaper-init]]"                                            ║
║   next: "[[WritePaper-structure]]"                                       ║
╚══════════════════════════════════════════════════════════════════════════╝
```

## Verantwortlichkeit

### TUT
- Schwierigkeitsgrad vom User erfragen (easy/normal/hard)
- Dimensions-Parameter basierend auf Schwierigkeitsgrad berechnen
- Kapitel-Archetypen aus _manifest.md extrahieren (falls vorhanden)
- Temperatur-Profil fuer jedes Kapitel generieren
- Agenten-Anzahl pro Kapitel bestimmen
- Quality-Gates basierend auf Schwierigkeitsgrad aktivieren
- session-state.json mit allen berechneten Parametern updaten
- _manifest.md mit difficulty und next_step=structure updaten

### TUT NICHT
- Commands ausfuehren (nur Planung)
- Quellen recherchieren (das macht /_WP_research)
- Kapitel-Struktur erstellen (das macht /_WP_structure)
- Paper-Inhalte generieren
- RAG-Queries durchfuehren

### Eskalation
- Bei unklarem difficulty-Input → Default: normal
- Bei fehlender _manifest.md → ERROR, User muss zuerst /_WP_init ausfuehren
- Bei fehlendem session-state.json → ERROR, User muss zuerst /_WP_init ausfuehren

---

## Ablauf

### Schritt 0: Inputs validieren und lesen

**Lese-Operationen:**
1. `_manifest.md` → Pruefe phase=setup, next_step=session
2. `session-state.json` → Pruefe phase=setup
3. `config/project.yaml` → research_questions fuer Umfangs-Schaetzung

**User-Input erfragen:**
- Schwierigkeitsgrad: easy | normal | hard
- Default: normal (falls User keine Angabe macht)

**Validierung:**
- Wenn _manifest.md fehlt → STOP, User muss /_WP_init ausfuehren
- Wenn session-state.json fehlt → STOP, User muss /_WP_init ausfuehren
- Wenn next_step != session → STOP, falscher Workflow-Step

### Schritt 1: Dimensions-Parameter berechnen

**Schwierigkeitsgrad-Tabelle:**

| Dimension | easy | normal | hard |
|-----------|------|--------|------|
| Agenten pro Kapitel | 3 | 5 | 9 |
| Quality-Loop max | 2 | 3 | 5 |
| RAG-Queries pro Agent | 5 | 10 | 20 |
| Peer-Review Matrix | 3x2=6 | 5x4=20 | 9x8=72 |
| Quality Gates | 3 (1,2,5) | 5 (+3,4) | 8 (alle) |
| Seiten pro Kapitel | 10-15 | 20-25 | 30-35 |
| Retry-Loop max | 1 | 2 | 3 |

**Berechne fuer gewaehlten Schwierigkeitsgrad:**
- agents_per_chapter
- quality_loop_max
- rag_queries_per_agent
- peer_review_matrix_size (agents * (agents-1))
- quality_gates_active (Array von Gate-IDs)
- pages_per_chapter (Min-Max Range)
- retry_loop_max

### Schritt 2: Temperatur-Profil berechnen

**Kapitel-Archetypen:**
- A = Exploration (Introduction, Background, Discussion)
- B = Technical (Methods, Results, Conclusion)

**EXPLORATION_LEVEL Mapping:**
- high → temperature: 1.1 - 1.2 (Archetyp A, kreative Kapitel)
- medium → temperature: 1.0 (Archetyp B, Uebergang)
- low → temperature: 0.8 - 0.9 (Archetyp B, technische Kapitel)

**Standard-Profil (5 Kapitel Paper):**

| Kapitel | Archetyp | EXPLORATION_LEVEL | temperature |
|---------|----------|-------------------|-------------|
| 1 | A (Intro) | high | 1.2 |
| 2 | A (Background) | high | 1.1 |
| 3 | B (Methods) | medium | 1.0 |
| 4 | B (Results) | low | 0.9 |
| 5 | B (Conclusion) | low | 0.8 |

**Falls _manifest.md bereits Kapitel-Struktur enthaelt:**
- Nutze vorhandene Kapitel-Titles
- Klassifiziere Archetyp basierend auf Keywords:
  - A: introduction, background, literature, discussion, future
  - B: method, approach, implementation, result, experiment, conclusion
- Berechne temperature-Gradient

### Schritt 3: State-Files aktualisieren

**session-state.json UPDATE:**
```json
{
  "phase": "session",
  "difficulty": "{easy|normal|hard}",
  "dimensions": {
    "agents_per_chapter": {3|5|9},
    "quality_loop_max": {2|3|5},
    "rag_queries_per_agent": {5|10|20},
    "peer_review_matrix": {6|20|72},
    "quality_gates_active": [1,2,3,4,5,6,7,8],
    "pages_per_chapter": [10, 15],
    "retry_loop_max": {1|2|3}
  },
  "temperature_profile": {
    "1": {"archetyp": "A", "level": "high", "temperature": 1.2},
    "2": {"archetyp": "A", "level": "high", "temperature": 1.1},
    "3": {"archetyp": "B", "level": "medium", "temperature": 1.0},
    "4": {"archetyp": "B", "level": "low", "temperature": 0.9},
    "5": {"archetyp": "B", "level": "low", "temperature": 0.8}
  },
  "timestamp": "{ISO8601}"
}
```

**_manifest.md UPDATE:**
```markdown
## Session Configuration

**Difficulty:** {easy|normal|hard}
**Configured:** {ISO8601}
**Next Step:** structure

### Dimensions
- Agents per Chapter: {3|5|9}
- Quality Loops: {2|3|5}
- RAG Queries: {5|10|20}
- Peer Review Matrix: {6|20|72}
- Pages per Chapter: {10-15|20-25|30-35}

### Temperature Profile
[Tabelle mit Kapitel → temperature]
```

---

## Output-Format

### Konsolen-Output

```
╔══════════════════════════════════════════════════════════════════════════╗
║ /_WP_session - Session Configuration                                  ║
╚══════════════════════════════════════════════════════════════════════════╝

[✓] Inputs validated
    - _manifest.md (phase=setup, next_step=session)
    - session-state.json (phase=setup)
    - config/project.yaml (3 research questions)

[✓] Difficulty: HARD selected

[✓] Dimensions calculated:
    - Agents per Chapter: 9
    - Quality Loop max: 5
    - RAG Queries per Agent: 20
    - Peer Review Matrix: 9x8 = 72
    - Quality Gates active: [1,2,3,4,5,6,7,8]
    - Pages per Chapter: 30-35
    - Retry Loop max: 3

[✓] Temperature Profile generated:
    Chapter 1 (Introduction)   → A, high,   temp=1.2
    Chapter 2 (Background)     → A, high,   temp=1.1
    Chapter 3 (Methods)        → B, medium, temp=1.0
    Chapter 4 (Results)        → B, low,    temp=0.9
    Chapter 5 (Conclusion)     → B, low,    temp=0.8

[✓] State files updated:
    - session-state.json
    - _manifest.md (next_step=structure)

╔══════════════════════════════════════════════════════════════════════════╗
║ NEXT STEP: /_WP_structure                                             ║
╚══════════════════════════════════════════════════════════════════════════╝
```

### session-state.json (Beispiel HARD)

```json
{
  "phase": "session",
  "difficulty": "hard",
  "dimensions": {
    "agents_per_chapter": 9,
    "quality_loop_max": 5,
    "rag_queries_per_agent": 20,
    "peer_review_matrix": 72,
    "quality_gates_active": [1,2,3,4,5,6,7,8],
    "pages_per_chapter": [30, 35],
    "retry_loop_max": 3
  },
  "temperature_profile": {
    "1": {"archetyp": "A", "level": "high", "temperature": 1.2},
    "2": {"archetyp": "A", "level": "high", "temperature": 1.1},
    "3": {"archetyp": "B", "level": "medium", "temperature": 1.0},
    "4": {"archetyp": "B", "level": "low", "temperature": 0.9},
    "5": {"archetyp": "B", "level": "low", "temperature": 0.8}
  },
  "timestamp": "2026-02-08T10:30:00Z"
}
```

---

## Qualitaetskriterien

### ERFOLG, wenn
- [✓] User-Input fuer difficulty erhalten (oder Default: normal)
- [✓] Alle 7 Dimensions-Parameter berechnet
- [✓] Temperature-Profil fuer alle Kapitel generiert
- [✓] session-state.json erfolgreich geupdatet
- [✓] _manifest.md erfolgreich geupdatet (next_step=structure)
- [✓] Alle Werte validiert (keine NULL, keine negativen Zahlen)

### FEHLER, wenn
- [✗] _manifest.md fehlt → User muss /_WP_init ausfuehren
- [✗] session-state.json fehlt → User muss /_WP_init ausfuehren
- [✗] next_step != session → Falscher Workflow-Step
- [✗] Ungültiger difficulty-Wert (nicht easy/normal/hard)
- [✗] File-Write fehlgeschlagen

### NOTIFY

Nach Abschluss:
```powershell
powershell -Command "notify 'WritePaper /_WP_session: {difficulty} configured, {agents_per_chapter} agents/chapter, temp {temp_min}-{temp_max}'"
```

---

## Notizen

- Dieser Command ist der zweite Schritt in der WritePaper-Chain
- Alle nachfolgenden Commands (structure, research, draft, etc.) nutzen die hier gesetzten Parameter
- Temperatur-Profil kann spaeter manuell angepasst werden (in session-state.json)
- Quality-Gates koennen bei easy/normal reduziert werden (Performance vs. Qualitaet Trade-off)
- Peer-Review Matrix waechst quadratisch mit Agenten-Anzahl (hard=72 Reviews pro Kapitel!)
