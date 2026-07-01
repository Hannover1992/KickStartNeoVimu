# /_WP_orchestrate - Team Lead Kapitel-Orchestrierung

```yaml
status: active
version: 3.3.0
created: 2026-02-14
updated: 2026-04-03
op: WritePaper
phase: Meta
type: orchestration
chain_position: meta
difficulty_scaling: true
team_based: true
bl_134_pflaster: true
bl_134_pflaster_inserted: 2026-04-25
bl_134_pflaster_real_refactor_in: BL-138
bl_140_pflaster_code: true
```

---

```
+======================================================================+
| META-COMMAND: /_WP_orchestrate                                       |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU - die ausfuehrende Claude-Instanz)              |
| WORKER: Kurzlebige Single-Command-Agents (1 Agent = 1 Command)       |
|         + N Wellen-Agents (PARALLEL: Draft/Review bei normal/hard)   |
|                                                                        |
| ZWECK: Orchestriert kurzlebige Agents durch den kompletten            |
|        Kapitel-Schreib-Zyklus. Team Lead erstellt Team, Tasks und     |
|        spawnt pro Pipeline-Step einen frischen Agent. Jeder Agent     |
|        fuehrt genau 1 Command aus und stirbt danach. Team Lead        |
|        steuert aktiv: Agent-Ergebnis pruefen, naechsten Agent         |
|        spawnen, ITERATE/CONVERGE Entscheidung treffen.                |
|                                                                        |
| PRINZIP: 1 Agent = 1 Command = stirbt danach (KURZLEBIG_PROMPT).    |
|          State lebt in DOKUMENTEN (Vertraegen), nicht im Agenten.     |
|          Kein Worker-Loop, kein TaskList-Polling.                      |
|          Team Lead entscheidet nach jedem Task den naechsten Schritt. |
|                                                                        |
| WELLEN-STEUERUNG: Commands die intern Wellen haben (Exploration →    |
|   Drafts → Synthese) werden VOM TEAM LEAD direkt orchestriert.      |
|   Team Lead erstellt pro Welle separate parallele Tasks (nicht der  |
|   Agent). Bei Write/Review: N parallele Tasks statt 1 Task           |
|   (difficulty-abhaengig). Agents fuehren NUR ihren Task aus.        |
|                                                                        |
| FLOW:                                                                  |
|   SETUP → KNOWLEDGE → WRITING ⟲ QUALITY → PDF → REFLECT → HiL     |
+======================================================================+
```

---

## Aufruf

```
/_WP_orchestrate [chapter_number] [difficulty] [ceiling] [floor] [--bl-source=BL-NNN]
```

**Parameter:**

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `chapter_number` | 1 | 1-N | Welches Kapitel |
| `difficulty` | normal | easy, normal, hard | Steuert Agent-Anzahl, Iterations, RAG-Queries |
| `ceiling` | sonnet | haiku, sonnet, opus | Hoechstes Modell (Worker + Synthese-Wellen) |
| `floor` | haiku | haiku, sonnet | Niedrigstes Modell (Exploration-Wellen) |
| `--bl-source` | null | BL-NNN | BL-043 AK-02-03: Quell-BL-Item ID (optional, von SDF M9 uebergeben) |

**Beispiele:**
```
/_WP_orchestrate 1                     → Kap. 1, normal, sonnet/haiku
/_WP_orchestrate 2 hard opus haiku     → Kap. 2, hard, opus ceiling
/_WP_orchestrate 1 easy sonnet sonnet  → Kap. 1, easy, alles sonnet
/_WP_orchestrate 1 normal sonnet haiku --bl-source=BL-043  → mit Quell-BL-Item
```

**Voraussetzungen:**
- Quellen liegen im Projekt-Ordner unter `quellen/` (PDFs, Markdown, TXT)
- KEINE Voraussetzung fuer Init/Ingest - der Orchestrator macht das selbst!
- Falls Projekt noch nicht existiert: Team Lead ruft `research_init_project` auf
- Falls Quellen noch nicht ingestiert: Worker fuehrt `/_WP_init` als Task 0 aus

**Modell-Zuordnung:**

**Skalierungs-Tabelle (universelles Wellen-Pattern 9-5-1 / 5-3-1 / 1):**

| Rolle | easy | normal | hard |
|-------|------|--------|------|
| Team Lead | DU (Opus) | DU (Opus) | DU (Opus) |
| Synthese (Welle 3) | 1 {ceiling} | 1 {ceiling} | 1 {ceiling} |
| Drafter (Welle 2) | --- | 3 {middle} | 5 {middle} |
| Explorer (Welle 1) | --- | 5 {floor} | 9 {floor} |

**Pattern: easy=1, normal=5-3-1, hard=9-5-1**

- hard:   9 {floor} (Explorer PARALLEL) → 5 {middle} (Drafter PARALLEL) → 1 {ceiling} (Synthese)
- normal: 5 {floor} (Explorer PARALLEL) → 3 {middle} (Drafter PARALLEL) → 1 {ceiling} (Synthese)
- easy:   1 {ceiling} (solo)

**WELLEN-PRINZIP:** Innerhalb einer Welle laufen ALLE Agents PARALLEL (keine gegenseitige Blockierung).
Nur die NAECHSTE Welle wird durch Abschluss der vorherigen Welle blockiert.

Freiheitsgrad 1 (Schwierigkeit): easy=1 solo / normal=5-3-1 / hard=9-5-1
Freiheitsgrad 2 (Modell): floor=haiku (Explorer) / middle=sonnet (Drafter) / ceiling=opus (Synthese)

---

## GLOBALE PARAMETER (/_param Override)

Lies `{VAULT}/_session_params.md` (4 Zeilen, 4 Parameter):

**Berechnung:**
```
params = lies("_session_params.md")
difficulty = params.difficulty
ceiling    = min(ceiling, params.ceiling)
floor      = max(floor, params.floor)
```

---

## VERTRAG

```
LIEST:
  - config/project.yaml           (paper_title, chapters, rag_collection)
  - _manifest.md                  (aktueller Stand, vorherige Kapitel)
  - session-state.json            (vorherige Session-Parameter, optional)

SCHREIBT (Team Lead direkt):
  - _manifest.md                  (nach jeder Welle/Phase: Status-Update)
  - session-state.json            (next_chapter nach ACCEPT)

DELEGIERT AN AGENT-TASKS:
  - config/project.yaml           (Task 0: Init)
  - references.bib                (Task 0: Init)
  - session-state.json            (Task 1: Session, Task 6m, Task 10s)
  - output/chapter-structure.md  (Task 2: Structure)
  - output/assess/chapter-{N}-assessment.json  (Task 3: Assessment)
  - output/models/chapter-{N}-model.md         (Task 4: ChapterModel)
  - output/assess/chapter-{N}-gaps.json        (Task 5: ChapterGap)
  - output/drafts/chapter-{N}/draft-A{NN}.md  (Tasks 6a-6e: Write-Agents)
  - output/drafts/chapter-{N}/metadata.json   (Task 6m: Aggregation)
  - output/figures/chapter-{N}/fig-{NN}.tikz  (Task 7: Visual)
  - output/quality/chapter-{N}/quality-report.json    (Task 8: QualityGate)
  - output/quality/chapter-{N}/convergence-decision.json (Task 9: Convergence)
  - output/reviews/chapter-{N}/agent-A{NN}-reviews.json (Tasks 10a-10e: Review-Agents)
  - output/reviews/chapter-{N}/review-matrix.json       (Task 10s: Aggregation)
  - output/reviews/chapter-{N}/review-summary.md        (Task 10s: Aggregation)
  - output/synthesis/chapter-{N}/final-draft.md  (Task 11: Synthesis)
  - output/pdf/chapter-{N}/chapter-{N}.pdf       (Task 12: PDF)
  - output/reflection/chapter-{N}/reflection-report.json (Task 13: Reflect)

DELEGIERT NACH ACCEPT (BL-010, v3.2):
  - /_backlog {wp_task_name} --mode=create  (WP→BL Rueckkopplung, non-blocking)

SCHREIBT NACH ACCEPT (BL-043, v3.3, BL-050 Vault-First):
  - PRIMAER: {VAULT}/Backlog/{BL_SLUG}/Crumbs/{bl_source_name}_wp_crumbs.md
  - FALLBACK: .claude/crumbs/{bl_source_name}_wp_crumbs.md  (wenn Vault nicht erreichbar)
  - {VAULT_BASE}/BL-{NNN}-{slug}.md → raw_source APPEND  (WP-Crumbs-Pfad, non-blocking)

LIEST FUER BL-043:
  - {VAULT}/_backlog_index.md  (bl_source_id → bl_source_name Lookup)
  - output/reflection/chapter-{N}/reflection-report.json  (Crumbs-Quelle: Learnings)
  - output/synthesis/chapter-{N}/final-draft.md  (Crumbs-Quelle: Kern-Thesen, erste 3 Absaetze)

WICHTIG:
  - Team Lead fuehrt KEINE /_WP_* Commands selbst aus (nur Workers)
  - Team Lead schreibt KEIN metadata.json oder review-matrix.json direkt
  - Manifest-Update nach JEDER Welle/Phase VOR /compact ist PFLICHT
  - Im Team-Modus: Write-Agents schreiben KEIN metadata.json (Race Condition)
  - Im Team-Modus: Review-Agents schreiben KEIN review-matrix.json (Race Condition)
```

---

## SCHRITT 0: BL-140 Batch-Pflaster (echter Branch)

<!-- BL-144 L4: Echter Branch-Header fuer Batch-Pflaster. INV-WP-PFLASTER-3 unten. -->

## BL-134 PFLASTER: Batch-Input-Adapter (Sub-Pipeline)

**Eingefuegt:** 2026-04-25 als Teil von BL-134 Slice 3.

Diese Pipeline akzeptiert ab BL-134 oberflaechlich einen `batch={PL-Items}` Parameter
vom SDF-executionDispatch und iteriert intern **sequentiell** durch die Items
(kein paralleler Batch-Refactor).

### Vertrag (Pflaster)

- **LIEST:** Wenn `batch=` Param gesetzt -> Liste der PL-Items aus `DF_BATCH_STATE.batch_items` (vom executionDispatch durchgereicht).
- **ITERIERT INTERN:** `FOR item IN batch_items: pipeline_aufruf(item)` (sequentiell).
- **SCHREIBT pro Item:** `DF_BATCH_STATE.item_done.append(item_id)` nach erfolgreichem Pipeline-Durchlauf (Recovery-Hook).
- **EXIT:** Wenn alle Items DONE.

### BL-134-PFLASTER-MARKER (Pseudo-Code)

```
batch = lies CLI_PARAM("batch") ?? null
IF batch != null:
  Logge: "[BL-134-PFLASTER] wp_orchestrate batch-modus: {len(batch)} Items sequentiell."
  FOR item IN batch:
    skip_if_done = item IN DF_BATCH_STATE.item_done
    IF skip_if_done: Logge "[BL-134-PFLASTER] SKIP {item} (bereits done)"; CONTINUE
    pipeline_aufruf(item)
    DF_BATCH_STATE.item_done.append(item)
    manifest.update()
  RETURN

# kein batch-Param -> normaler Single-Item-Pfad (Legacy)
```

### Echter Batch-Refactor

Dieser Pflaster ist Uebergangs-Loesung. Echter Batch-Support (paralleler
intern-Loop, Aggregat-Kontext) folgt im jeweiligen Pipeline-Refactor:

- **wp_orchestrate echter Refactor:** BL-138 (pruefen ob WP separates BL benoetigt)

### INV-WP-PFLASTER-1

Pflaster-Pfad MUSS sequentiell bleiben bis Folge-BL den echten Refactor liefert.
Paralleler intern-Loop ohne explizite BATCH_STATE-Race-Locks ist VERBOTEN.

### BL-140 PFLASTER-CODE (echte Implementation)

```
# CLI-Param oder Manifest
batch = lies CLI_PARAM("batch") OR DF_BATCH_STATE.batch_items
IF batch != null AND |batch| > 0:
  Logge: "[BL-140-PFLASTER] wp_orchestrate Batch-Modus: {len(batch)} Items sequentiell"
  FOR item IN batch:
    # Skip falls schon DONE
    IF item IN DF_BATCH_STATE.item_done:
      Logge: "[BL-140-PFLASTER] SKIP {item} (bereits in item_done)"
      CONTINUE

    # Original-Pipeline-Aufruf fuer dieses Item
    pipeline_main_logic(item)

    # Recovery-Hook
    DF_BATCH_STATE.item_done.append(item)
    manifest.update()

  RETURN  # Batch-Modus fertig

# Fallback: kein batch -> Single-Item-Pfad (Legacy)
pipeline_main_logic(NAME)
```

INV-WP-PFLASTER-2 (NEU, BL-140):
Pflaster-Code MUSS sequentiell iterieren (kein paralleler Loop ohne Race-Lock).
Pflaster-Code MUSS item_done.append nach JEDEM erfolgreichen Item.
Pflaster-Code MUSS RETURN am Ende des batch-Pfads (NICHT in den Legacy-Pfad fallen).

INV-WP-PFLASTER-3 (BL-144):
Echter Batch-Branch IM Pipeline-Body -- NICHT nur Doku am Datei-Ende.
Der SCHRITT-0-Block MUSS vor PHASE 1 aktiv ausgefuehrt werden (kein toter Doku-Anhang).

---

## PHASE 1: TEAM SETUP

### Schritt 1.1: Kontext laden

Lies folgende Dateien:
1. `config/project.yaml` → paper_title, chapters, rag_collection, research_questions
2. `_manifest.md` → aktueller Stand, vorherige Kapitel
3. `session-state.json` → falls vorhanden, vorherige Session-Parameter

Extrahiere:
- `{paper_title}` aus project.yaml
- `{chapter_title}` aus chapters[{N}]
- `{rag_collection}` aus rag.collection
- `{project_path}` aus Projekt-Root
- `{total_chapters}` aus chapters.length

### Schritt 1.1a: G-SESSION-INIT (Stale-Task-Cleanup)

**Zweck:** Erkennt und bereinigt stale `in_progress` Tasks aus einer vorangegangenen abgebrochenen Session (F06-Guard, W162).

```
G-SESSION-INIT Algorithmus:

1. TaskList aufrufen → alle Tasks lesen
2. Gibt es Tasks mit status=in_progress?
   → NEIN: Keine stale Tasks → WEITER zu Schritt 1.2
   → JA: Pruefe ob laufendes Team vorhanden

3. Laufendes Team erkennbar (SendMessage-Partner erreichbar)?
   → JA:  HiL: "Bestehendes Team mit offenen Tasks gefunden. Fortsetzen? (j/n)"
          → j: WEITER (Team-Resume Modus)
          → n: ABBRUCH
   → NEIN: Auto-Cancel (Schritt 4)

4. Auto-Cancel:
   → Logge: "G-SESSION-INIT: {N} stale in_progress Tasks gefunden."
   → Fuer jeden in_progress Task:
     TaskUpdate(taskId=..., status="completed",
       subject="[STALE-CANCELLED] {original_subject}")
   → Logge: "SESSION_RESUME: Stale Tasks bereinigt, starte neu."
```

**Schutz:** Nur `in_progress` Tasks werden gecancelt. Pending Tasks bleiben unberuehrt.

---

### Schritt 1.2: Team erstellen

```
TeamCreate:
  team_name: "wp-chapter-{N}"
  description: "Paper Writing - Kapitel {N}: {chapter_title}"
```

### Schritt 1.3: Tasks erstellen (1 Task pro Command)

Erstelle Tasks fuer den ERSTEN Durchlauf. INNER-Loop Tasks werden
bei ITERATE dynamisch neu erstellt.

**INIT-Phase (einmalig pro Paper, uebersprungen wenn bereits initialisiert):**

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 0 | WP Init + Quellen Ingest | /_WP_init | - | Initializing project and ingesting sources |

**SETUP-Phase (einmalig pro Kapitel):**

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 1 | WP Session konfigurieren | /_WP_session | Task 0 | Configuring session |
| 2 | WP Struktur extrahieren | /_WP_structure | Task 1 | Extracting structure |

**KNOWLEDGE-Phase (einmalig, es sei denn Discovery noetig):**

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 3 | WP Knowledge Assessment | /_WP_assess | Task 2 | Assessing knowledge |
| 4 | WP Chapter Model erstellen | /_WP_chapterModel | Task 3 | Building chapter model |
| 5 | WP Chapter Gap Analyse | /_WP_chapterGap | Task 4 | Analyzing gaps |

**WRITING-Phase (INNER-LOOP, Iteration 1) - DIFFICULTY-ABHAENGIG:**

WICHTIG: Erstelle Task 6 basierend auf difficulty (aus session-state.json):

Bei easy (1 Draft-Agent):

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 6  | WP Draft schreiben (Iter 1, Solo) | /_WP_write | Task 5 | Writing draft (solo) |
| 6m | WP Draft Metadata aggregieren | /_WP_write | Task 6 | Aggregating draft metadata |
| 7  | WP Visuals erstellen (Iter 1) | /_WP_visual | Task 6m | Creating visuals |
| 8  | WP Quality Gate (Iter 1) | /_WP_qualityGate | Task 7 | Running quality gates |
| 9  | WP Convergence Check (Iter 1) | /_WP_convergence | Task 8 | Checking convergence |

Bei normal (3 Draft-Agents parallel):

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 6a | WP Draft schreiben (Iter 1, Agent A01) | /_WP_write | Task 5 | Writing draft A01 |
| 6b | WP Draft schreiben (Iter 1, Agent A02) | /_WP_write | Task 5 | Writing draft A02 |
| 6c | WP Draft schreiben (Iter 1, Agent A03) | /_WP_write | Task 5 | Writing draft A03 |
| 6m | WP Draft Metadata aggregieren | /_WP_write | Tasks 6a+6b+6c | Aggregating draft metadata |
| 7  | WP Visuals erstellen (Iter 1) | /_WP_visual | Task 6m | Creating visuals |
| 8  | WP Quality Gate (Iter 1) | /_WP_qualityGate | Task 7 | Running quality gates |
| 9  | WP Convergence Check (Iter 1) | /_WP_convergence | Task 8 | Checking convergence |

Bei hard (5 Draft-Agents parallel):

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 6a | WP Draft schreiben (Iter 1, Agent A01) | /_WP_write | Task 5 | Writing draft A01 |
| 6b | WP Draft schreiben (Iter 1, Agent A02) | /_WP_write | Task 5 | Writing draft A02 |
| 6c | WP Draft schreiben (Iter 1, Agent A03) | /_WP_write | Task 5 | Writing draft A03 |
| 6d | WP Draft schreiben (Iter 1, Agent A04) | /_WP_write | Task 5 | Writing draft A04 |
| 6e | WP Draft schreiben (Iter 1, Agent A05) | /_WP_write | Task 5 | Writing draft A05 |
| 6m | WP Draft Metadata aggregieren | /_WP_write | Tasks 6a-6e | Aggregating draft metadata |
| 7  | WP Visuals erstellen (Iter 1) | /_WP_visual | Task 6m | Creating visuals |
| 8  | WP Quality Gate (Iter 1) | /_WP_qualityGate | Task 7 | Running quality gates |
| 9  | WP Convergence Check (Iter 1) | /_WP_convergence | Task 8 | Checking convergence |

Task 6m (Metadata): Liest alle draft-A{NN}.md, schreibt metadata.json + aktualisiert
_manifest.md + session-state.json. Im Worker-Modus schreiben Write-Agents KEIN
metadata.json (Race Condition vermeiden).

**POST-CONVERGENCE (nach CONVERGE/FORCE) - DIFFICULTY-ABHAENGIG:**

Tasks 10-13 werden erst erstellt wenn Convergence CONVERGE oder FORCE entscheidet.
Bei ITERATE werden stattdessen neue Tasks 6-9 fuer die naechste Iteration erstellt.

Bei easy (1 Review-Agent):

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 10  | WP Cross-Review (Solo) | /_WP_review | Task 9 | Reviewing chapter |
| 10s | WP Review Score aggregieren | /_WP_review | Task 10 | Aggregating review scores |
| 11  | WP Draft Synthesis | /_WP_synthesis | Task 10s | Synthesizing drafts |
| 12  | WP Chapter PDF | /_WP_chapterPDF | Task 11 | Generating PDF |
| 13  | WP Reflect + Summary | /_WP_reflect | Task 12 | Reflecting on chapter |

Bei normal (3 Review-Agents parallel):

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 10a | WP Cross-Review (Agent A01) | /_WP_review | Task 9 | Reviewing as A01 |
| 10b | WP Cross-Review (Agent A02) | /_WP_review | Task 9 | Reviewing as A02 |
| 10c | WP Cross-Review (Agent A03) | /_WP_review | Task 9 | Reviewing as A03 |
| 10s | WP Review Score aggregieren | /_WP_review | Tasks 10a+10b+10c | Aggregating review scores |
| 11  | WP Draft Synthesis | /_WP_synthesis | Task 10s | Synthesizing drafts |
| 12  | WP Chapter PDF | /_WP_chapterPDF | Task 11 | Generating PDF |
| 13  | WP Reflect + Summary | /_WP_reflect | Task 12 | Reflecting on chapter |

Bei hard (5 Review-Agents parallel):

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 10a | WP Cross-Review (Agent A01) | /_WP_review | Task 9 | Reviewing as A01 |
| 10b | WP Cross-Review (Agent A02) | /_WP_review | Task 9 | Reviewing as A02 |
| 10c | WP Cross-Review (Agent A03) | /_WP_review | Task 9 | Reviewing as A03 |
| 10d | WP Cross-Review (Agent A04) | /_WP_review | Task 9 | Reviewing as A04 |
| 10e | WP Cross-Review (Agent A05) | /_WP_review | Task 9 | Reviewing as A05 |
| 10s | WP Review Score aggregieren | /_WP_review | Tasks 10a-10e | Aggregating review scores |
| 11  | WP Draft Synthesis | /_WP_synthesis | Task 10s | Synthesizing drafts |
| 12  | WP Chapter PDF | /_WP_chapterPDF | Task 11 | Generating PDF |
| 13  | WP Reflect + Summary | /_WP_reflect | Task 12 | Reflecting on chapter |

Task 10s (Review-Aggregation): Liest alle agent-A{NN}-reviews.json, berechnet Ranking,
schreibt review-matrix.json + review-summary.md. Review-Agents schreiben NUR ihre
eigene agent-A{NN}-reviews.json (kein review-matrix.json, keine Race Condition).

### Schritt 1.4: Agents spawnen (KURZLEBIG_PROMPT v3.0)

Team Lead spawnt Agents JE NACH PHASE:

**SEQUENTIELLE PHASE** (Pipeline-Tasks: init, session, structure, assess, chapterModel, chapterGap, aggregation, synthesis, pdf, reflect):

KEIN persistenter Worker. Team Lead spawnt PRO PIPELINE-STEP einen frischen Agent:
```
Task tool:
  name: "wp-{chapter}-{command}"    ← z.B. "wp-1-session", "wp-1-chapterModel"
  subagent_type: "general-purpose"
  model: "{ceiling}"                 ← aus Parameter (default: sonnet)
  team_name: "wp-chapter-{N}"
  mode: "bypassPermissions"
  prompt: [KURZLEBIG_PROMPT, siehe Phase 2]
```

Jeder Agent fuehrt genau 1 Command aus und stirbt danach.
Team Lead spawnt den naechsten Agent ERST wenn der aktuelle fertig ist (Phase 3).

**PARALLELE PHASE (Tasks 6a-6e): N Draft-Agents GLEICHZEITIG**

```
Bei easy:   1 Agent (wp-draft-solo)  → Task 6 solo
Bei normal: 3 Agents PARALLEL        → Tasks 6a, 6b, 6c
Bei hard:   5 Agents PARALLEL        → Tasks 6a, 6b, 6c, 6d, 6e

Pro Draft-Agent:
  Task tool:
    name: "wp-draft-A{NN}"     ← z.B. "wp-draft-A01", "wp-draft-A02"
    subagent_type: "general-purpose"
    model: "{middle}"           ← Drafter = middle-Modell
    team_name: "wp-chapter-{N}"
    mode: "bypassPermissions"
    run_in_background: true     ← PARALLEL!
    prompt: [WELLEN-PROMPT mit Agent-ID + Rolle, siehe Phase 2]
```

AGENT-NAMING HINWEIS (Wellen-Pattern):
Draft-Agents heissen "wp-draft-A{NN}" (OHNE chapter-Prefix), NICHT "wp-{chapter}-draft-A{NN}".
Grund: Wellen-Pattern trennt parallele Agents vom sequentiellen Kapitel-Flow.
Sequentielle Agents (1 Kapitel, 1 Command): wp-{chapter}-{command} (z.B. "wp-1-session")
Parallele Wellen-Agents (N Agents pro Welle): wp-draft-A{NN} / wp-review-A{NN}
→ Eindeutige Identifikation in Teams + klar welche Phase laeuft

Nach Abschluss ALLER Draft-Agents: Team Lead spawnt wp-{chapter}-aggregation.

**PARALLELE PHASE (Tasks 10a-10e): N Review-Agents GLEICHZEITIG**

```
Bei easy:   1 Agent (wp-review-solo)  → Task 10 solo
Bei normal: 3 Agents PARALLEL         → Tasks 10a, 10b, 10c
Bei hard:   5 Agents PARALLEL         → Tasks 10a, 10b, 10c, 10d, 10e

Pro Review-Agent:
  Task tool:
    name: "wp-review-A{NN}"
    subagent_type: "general-purpose"
    model: "{middle}"
    team_name: "wp-chapter-{N}"
    mode: "bypassPermissions"
    run_in_background: true
    prompt: [WELLEN-PROMPT mit Reviewer-ID, siehe Phase 2]
```

Nach Abschluss ALLER Review-Agents: Team Lead spawnt wp-{chapter}-reviewAggregation.

**easy:** Team Lead spawnt pro Step 1 Agent (wp-{chapter}-{command}).

---

## PHASE 2: KURZLEBIG_PROMPT (Single-Command-Agent)

Pro Pipeline-Step spawnt Team Lead 1 kurzlebigen Agent.
Jeder Agent bekommt diesen minimalen Prompt (kein Worker-Loop, kein TaskList-Polling):

```
Du bist ein Single-Command-Agent fuer die Paper-Writing-Pipeline.
Agent-Name: wp-{chapter}-{command}
Team: wp-chapter-{N}

═══ DEIN AUFTRAG ═══

Genau 1 Command ausfuehren, dann fertig.

Command:     /_WP_{COMMAND}
Task-ID:     {TASK_ID}
Kapitel:     {N} - {chapter_title}
Projekt:     {project_path}
RAG:         {rag_collection}

═══ SCHRITTE ═══

1. Lade den Command via Skill-Tool:
   Skill(skill="_WP_{COMMAND}", args="Kap.{N}")
   Beispiele:
     Skill(skill="_WP_write", args="Kap.3")
     Skill(skill="_WP_review", args="Kap.3")
     Skill(skill="_WP_qualityGate", args="Kap.3")
   WICHTIG: Nutze das Skill-Tool — NICHT die .md-Datei direkt lesen!
2. Fuehre den geladenen Skill vollstaendig aus.
3. TaskUpdate {TASK_ID} status=completed
4. SendMessage an "team-lead":
   "WP_{COMMAND} Kap.{N}: [2-3 Saetze Summary]"

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- IMMER Skill-Tool verwenden — niemals .md-Datei manuell lesen als Ersatz
- NUR dieser eine Command, dann fertig (KEIN TaskList-Loop)
- NUR RAG-Quellen zitieren. KEIN eigenes Wissen einbringen.
- Alle Outputs in den Projekt-Ordner schreiben ({project_path}/output/).
- Arbeite gruendlich, nicht schnell
```

**Wellen-Phase Prompt** (fuer Draft/Review-Agents bei normal/hard):

Draft- und Review-Agents erhalten einen spezifischen Prompt der ihre Rolle direkt enthaelt:

```
Du bist ein Wellen-Agent fuer die Paper-Writing-Pipeline.
Agent-Name: wp-{wellen-name}
Team: wp-chapter-{N}

═══ DEIN AUFTRAG ═══

Genau 1 Rolle ausfuehren, dann fertig.

Rolle:       {ROLLEN-BESCHREIBUNG}
Task-ID:     {TASK_ID}
Kapitel:     {N} - {chapter_title}
Projekt:     {project_path}
RAG:         {rag_collection}

═══ SP-FIX-8: Stille-Post-Schutz (Draft/Review-Kaskade) ═══

STILLE-POST-SCHUTZ fuer Draft-Agents:
  Drafts anderer Agents sind INSPIRATION, nicht Faktenquelle.
  Zitiere NUR aus RAG-Quellen ({rag_collection}). Verifiziere JEDE Aussage
  an den PRIMAERQUELLEN (RAG-Chunks, chapter-model, research_questions).
  Uebernimm KEINE Behauptungen blind aus anderen Drafts oder Assessment-Outputs.

STILLE-POST-SCHUTZ fuer Review-Agents (SP-FIX-9):
  Draft-Texte sind Pruefgegenstand, nicht Wahrheitsquelle.
  Pruefe Zitate und Aussagen gegen RAG-Quellen. Markiere ungestuetzte
  Behauptungen als FINDING. Dein Review basiert auf EIGENER RAG-Pruefung.

═══ ROLLEN-ERKENNUNG ═══

Deine Rolle kommt direkt aus diesem Prompt (KEIN TaskGet noetig):

  Draft-Agent A{NN} ({AGENT_ROLE}):
  → Schreibe NUR output/drafts/chapter-{N}/draft-A{NN}.md
  → metadata.json NICHT schreiben (das macht Aggregations-Agent)

  Review-Agent A{NN}:
  → Reviewe ALLE Drafts ausser draft-A{NN}.md
  → Schreibe NUR output/reviews/chapter-{N}/agent-A{NN}-reviews.json
  → KEIN review-matrix.json (das macht Aggregations-Agent)

WICHTIG: Falls Command-Datei "Spawne N Agents" oder "M4 Parallel-Spawning" sagt:
  → Im Team-Modus ignorierst du das.
  → Fuehre NUR deine Rolle aus (was dieser Prompt sagt).

═══ SCHRITTE ═══

1. Fuehre die zugewiesene Rolle aus.
2. TaskUpdate {TASK_ID} status=completed
3. SendMessage an "team-lead":
   "{ROLLE} Kap.{N}: [2-3 Saetze Summary]"

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- NUR diese eine Rolle, dann fertig
- NUR RAG-Quellen zitieren
```

---

## PHASE 3: TEAM LEAD STEUERUNG (Aktives Spawning v3.0)

### 3.1 Agent-Messages empfangen und naechsten Agent spawnen

Team Lead (DU) empfaengst Agent-Messages automatisch.
Pro Message:

```
1. Agent meldet: "WP_{COMMAND} Kap.{N}: Summary"
2. Team Lead prueft: Passt das Ergebnis?
3. Bei Erfolg: Naechsten Agent spawnen (naechster Pipeline-Step)
   → wp-{chapter}-{naechster-command} mit KURZLEBIG_PROMPT
4. Bei Problem: Neuen Agent spawnen mit Korrektur-Kontext
   → wp-{chapter}-{command}-retry mit erweitertem Prompt
5. Nach /_WP_convergence: → Phase 3.2 (ITERATE/CONVERGE Entscheidung)
6. Nach /_WP_reflect: → Phase 3.4 (HiL-Pause)
```

**Pipeline-Sequenz (Team Lead spawnt aktiv):**
```
wp-{chapter}-init
  → wp-{chapter}-session
    → wp-{chapter}-structure
      → wp-{chapter}-assess
        → wp-{chapter}-chapterModel
          → wp-{chapter}-chapterGap
            → [Draft-Agents PARALLEL oder wp-{chapter}-write (easy)]
              → wp-{chapter}-aggregation
                → wp-{chapter}-visual
                  → wp-{chapter}-qualityGate
                    → wp-{chapter}-convergence
```

**WP_PIPELINE_STATE im Manifest (Team Lead aktualisiert nach jedem Agent):**
```yaml
WP_PIPELINE_STATE:
  chapter_nr: {N}
  iteration: {I}
  phase: "{aktuelle-phase}"
  bl_source_id: {BL-NNN | null}     # BL-043 AK-02-01: Quell-BL-Item (aus SDF oder --bl-source Parameter)
  bl_source_name: {NAME | null}     # BL-043 AK-02-02: Abgeleitet aus bl_source_id via _backlog_index.md Lookup. Fallback: wp_task_name
  resume_zaehler:
    init: 0
    session: 0
    structure: 0
    assess: 0
    chapterModel: 0
    chapterGap: 0
    write: 0
    aggregation: 0
    visual: 0
    qualityGate: 0
    convergence: 0
    review: 0
    reviewAggregation: 0
    synthesis: 0
    chapterPDF: 0
    reflect: 0
  aktive_agent_ids: []
```

## WP_STEPS Enum (AK-06-01, BL-036)

WP_PIPELINE_STATE.phase nimmt exakt diese 16 Werte an:

| # | Step              | Manifest-Wert       | Parallel? |
|---|-------------------|----------------------|-----------|
| 1 | init              | init                 | nein      |
| 2 | session           | session              | nein      |
| 3 | structure         | structure            | nein      |
| 4 | assess            | assess               | nein      |
| 5 | chapterModel      | chapterModel         | nein      |
| 6 | chapterGap        | chapterGap           | nein      |
| 7 | write             | write                | ja (N Agents) |
| 8 | aggregation       | aggregation          | nein      |
| 9 | visual            | visual               | nein      |
|10 | qualityGate       | qualityGate          | nein      |
|11 | convergence       | convergence          | nein      |
|12 | review            | review               | ja (N Agents) |
|13 | reviewAggregation | reviewAggregation    | nein      |
|14 | synthesis         | synthesis            | nein      |
|15 | chapterPDF        | chapterPDF           | nein      |
|16 | reflect           | reflect              | nein      |

## Konvergenz-Enforcement (AK-06-02, BL-036)

Manifest-Feld: WP_PIPELINE_STATE.convergence_count (Zaehler, startet bei 0)
Max-Iterationen pro Schwierigkeit:
  easy=2, normal=3, hard=5

Guard: IF convergence_count >= max_iterations[difficulty]:
  → FORCE convergence (qualityGate PASS erzwingen, WARN loggen)
  → KEIN endloser Loop

### 3.2 Bei ITERATE-Decision

Wenn Worker meldet "Convergence: ITERATE":

1. **Pruefe Iteration-Counter:**
   - easy: max 2 Iterationen
   - normal: max 3 Iterationen
   - hard: max 5 Iterationen
   - Ueberschritten? → FORCE statt ITERATE

2. **Erstelle neue INNER-LOOP Tasks (difficulty-abhaengig):**

Lese difficulty aus session-state.json.

```
Bei easy (1 Draft-Agent):
  TaskCreate: "WP Draft schreiben (Iter {I+1}, Solo)"
    description: "/_WP_write ausfuehren. Solo-Modus (1 Agent = du).
      Iteration {I+1}. Verbesserungen aus Quality-Report einarbeiten.
      Lies output/quality/chapter-{N}/quality-report.json."
    blocked_by: (letzter completed Task)
  TaskCreate: "WP Draft Metadata aggregieren"
    blocked_by: (Write-Task)
  TaskCreate: "WP Visuals aktualisieren (Iter {I+1})"
    blocked_by: (Metadata-Task)
  TaskCreate: "WP Quality Gate (Iter {I+1})"
    blocked_by: (Visual-Task)
  TaskCreate: "WP Convergence Check (Iter {I+1})"
    blocked_by: (Quality-Task)

Bei normal (3 parallele Draft-Agents):
  TaskCreate: "WP Draft schreiben (Iter {I+1}, Agent A01)"
    description: "/_WP_write ausfuehren. Worker-Modus, Rolle: A01 (Foundational Expert).
      Iteration {I+1}. Verbesserungen aus Quality-Report einarbeiten.
      Schreibe NUR draft-A01.md. Lies quality-report.json."
    blocked_by: (letzter completed Task)
  TaskCreate: "WP Draft schreiben (Iter {I+1}, Agent A02)"
    description: [analog, Rolle: A02 Methodological Expert]
    blocked_by: (letzter completed Task)   [PARALLEL zu A01]
  TaskCreate: "WP Draft schreiben (Iter {I+1}, Agent A03)"
    description: [analog, Rolle: A03 Applied Expert]
    blocked_by: (letzter completed Task)   [PARALLEL zu A01+A02]
  TaskCreate: "WP Draft Metadata aggregieren"
    blocked_by: (ALLE 3 Write-Tasks der neuen Iteration)
  TaskCreate: "WP Visuals aktualisieren (Iter {I+1})"
    blocked_by: (Metadata-Task)
  TaskCreate: "WP Quality Gate (Iter {I+1})"
    blocked_by: (Visual-Task)
  TaskCreate: "WP Convergence Check (Iter {I+1})"
    blocked_by: (Quality-Task)

Bei hard: analog mit 5 parallelen Draft-Agents (A01-A05).
```

3. **Starte naechste Iteration (Team Lead spawnt Draft-Agents):**

```
Bei easy: Team Lead spawnt wp-{chapter}-write mit KURZLEBIG_PROMPT:
  "ITERATE: Iteration {I+1}. /_WP_write ausfuehren."

Bei normal/hard: Team Lead spawnt N Draft-Agents PARALLEL:
  FUER JEDEN Draft-Agent (A01..A{N}):
    wp-draft-A{NN} mit WELLEN-PROMPT
```

### 3.3 Bei CONVERGE/FORCE-Decision

Wenn Worker meldet "Convergence: CONVERGE" oder "FORCE":

1. **Erstelle POST-CONVERGENCE Tasks (difficulty-abhaengig):**

Lese difficulty aus session-state.json. Erstelle Review-Tasks basierend auf difficulty:

```
Bei easy:
  TaskCreate: "WP Cross-Review (Solo)"
    description: [Review-Beschreibung, Solo-Modus, alle Reviews sequentiell]
    blocked_by: (letzter Convergence-Task)
  TaskCreate: "WP Review Score aggregieren"
    blocked_by: (Review-Task)

Bei normal (3 Review-Agents parallel):
  TaskCreate: "WP Cross-Review (Agent A01)"
    description: [Review-Beschreibung, Reviewer-ID: A01, schreibt agent-A01-reviews.json]
    blocked_by: (letzter Convergence-Task)
  TaskCreate: "WP Cross-Review (Agent A02)"
    description: [analog, Reviewer-ID: A02]
    blocked_by: (letzter Convergence-Task)   [PARALLEL zu A01]
  TaskCreate: "WP Cross-Review (Agent A03)"
    description: [analog, Reviewer-ID: A03]
    blocked_by: (letzter Convergence-Task)   [PARALLEL zu A01+A02]
  TaskCreate: "WP Review Score aggregieren"
    blocked_by: (ALLE 3 Review-Tasks)

Bei hard: analog mit 5 Review-Agents (A01-A05).

Dann fuer alle difficulty-Level:
  TaskCreate: "WP Draft Synthesis"
    blocked_by: (Review-Score-Task)
  TaskCreate: "WP Chapter PDF"
    blocked_by: (Synthesis-Task)
  TaskCreate: "WP Reflect + Summary"
    blocked_by: (PDF-Task)
```

2. **Starte Post-Convergence (Team Lead spawnt Review-Agents):**

```
Bei easy: Team Lead spawnt wp-{chapter}-review mit KURZLEBIG_PROMPT:
  "CONVERGE: /_WP_review ausfuehren (Solo)."

Bei normal/hard: Team Lead spawnt N Review-Agents PARALLEL:
  FUER JEDEN Review-Agent (A01..A{N}):
    wp-review-A{NN} mit WELLEN-PROMPT
```

### 3.4 Nach Reflect (Worker meldet "Reflect fertig")

Team Lead fuehrt HiL-Pause durch:

```
AskUserQuestion:
  header: "Kapitel {N}"
  question: "Kapitel {N} '{chapter_title}' wurde geschrieben und
    PDF per Email gesendet.

    Score: {score}/10
    Woerter: {words}
    Zitate: {cites}
    Iterationen: {iterations}
    Learnings: {learnings_summary}

    Bitte PDF pruefen und entscheiden:"

  options:
    - label: "ACCEPT"
      description: "Kapitel fertig, weiter zum naechsten"
    - label: "RETRY"
      description: "Kapitel ueberarbeiten (ich gebe Feedback)"
    - label: "ABORT"
      description: "Pipeline stoppen"
```

### 3.5 User-Decision verarbeiten

**Bei ACCEPT:**
```
1. Keine aktiven Agents (kurzlebig, bereits terminiert)
2. TeamDelete
2a. Fire-Together Trigger — ENTFERNT (BL-050 Vault-First DirectWrite)
    # _W_fireTogether ist OBSOLET. Synthese-Commands schreiben direkt in Vault.
2b. P3 Trigger: ObsidianSync — ENTFERNT (BL-050 Vault-First DirectWrite)
    # _W_sync_orchestrate / _W_obsidianSync sind OBSOLET. Vault-Sync inline erledigt.
3. _W_push_orchestrate — ENTFERNT (BL-050 Vault-First DirectWrite)
   # wpush=SKIPPED_OBSOLET — DirectWrite macht post-hoc Vault-Sync ueberfluessig.
4. Optional: /_finish {chapter_title}
   → Offene Items pruefen (parking-lot, Task.md, offene ECs)
   → Manifest auf READY setzen
   → Nur wenn Kapitel vollstaendig abgeschlossen (letztes Kapitel oder Paper-Ende)
4a. BL-Item erzeugen (automatische Rueckkopplung WP→Backlog, BL-010):
    # Nach WP DONE: Neues BL-Item fuer WP-Ergebnisse im Backlog persistieren
    # Damit WP-Recherche-Ergebnisse als implementierungsfaehiges Paket verfuegbar sind
    IF WP_PIPELINE_STATE.phase == "DONE" OR WP_PIPELINE_STATE.phase == "ACCEPTED":
      wp_task_name = WP_PIPELINE_STATE.wp_task_name
      TRY:
        Skill(skill="_backlog", args="{wp_task_name} --mode=create --source=wp --reifegrad=SC-REIF")
        Logge: "[WP→BL] BL-Item erzeugt fuer WP-Ergebnis '{wp_task_name}'"
      CATCH:
        WARN: "BL-Item-Erzeugung fehlgeschlagen fuer '{wp_task_name}'. Weiter ohne BL-Item (non-blocking)."
4b. WP-Crumbs erzeugen (Rueckkanal WP→Crumbs, BL-043 RF-01):
    # Nach ACCEPT: Strukturierte Crumbs aus Reflection-Report extrahieren
    # ADR-01: Reflection-Report als Quelle (nicht full-draft — bereits strukturierte Learnings)
    # AK-01-02: Non-blocking — Fehler blockiert Pipeline NICHT
    TRY:
      # AK-02-01/AK-02-02: bl_source_name bestimmen
      bl_source_id = WP_PIPELINE_STATE.bl_source_id      # z.B. "BL-043" oder null
      IF bl_source_id != null:
        # Lookup in _backlog_index.md: bl_source_id → Feature-Name
        index_zeile = LIES _backlog_index.md → Zeile mit {bl_source_id}
        bl_source_name = index_zeile.name                 # z.B. "WP_Crumbs_Rueckkanal"
      ELSE:
        bl_source_name = WP_PIPELINE_STATE.wp_task_name   # Fallback: wp_task_name
      Logge: "[WP→CRUMBS] bl_source_name='{bl_source_name}' (bl_source_id={bl_source_id})"

      # AK-01-01: Crumbs-Datei aus Reflection-Report + final-draft erzeugen
      N = WP_PIPELINE_STATE.chapter_nr
      reflection = LIES "output/reflection/chapter-{N}/reflection-report.json"
      final_draft = LIES "output/synthesis/chapter-{N}/final-draft.md" → erste 3 Absaetze
      learnings = reflection.learnings   # Array von {text, kategorie, konfidenz}

      # AK-01-03: Dateiname folgt bestehendem Schema ({NAME}_wp_crumbs.md)
      # BL-050 Vault-First: Crumbs PRIMAER in Vault, FALLBACK lokal
      vault_crumbs_pfad = vault_resolve(
        "{VAULT}/Backlog/{BL_SLUG}/Crumbs/{bl_source_name}_wp_crumbs.md"
      )
      IF vault_erreichbar(vault_crumbs_pfad):
        crumbs_pfad = vault_crumbs_pfad
      ELSE:
        crumbs_pfad = ".claude/crumbs/{bl_source_name}_wp_crumbs.md"
        WARN: "Vault nicht erreichbar, FALLBACK auf .claude/crumbs/"

      SCHREIBE crumbs_pfad:
        ---
        type: crumbs
        feature: {bl_source_name}
        bl-item: {bl_source_id}
        source_chapter: {N}
        bl_source_id: {bl_source_id}
        bl_source_name: {bl_source_name}
        wp_task_name: {WP_PIPELINE_STATE.wp_task_name}
        created: {HEUTE}
        updated: {HEUTE}
        crumbs_count: {|learnings|}
        tags:
          - bl/{bl_source_id}
          - type/crumbs
          - pipeline/post-phase
        ---

        # WP-Crumbs: {bl_source_name} (Kapitel {N})

        ## Kern-Thesen (aus final-draft)
        {final_draft_erste_3_absaetze}

        ## Learnings (aus Reflection-Report)
        FUER JEDES learning IN learnings:
          ### Crumb: {learning.text | erste 60 Zeichen}
          - **Kategorie:** {learning.kategorie}
          - **Konfidenz:** {learning.konfidenz}
          - **Detail:** {learning.text}

      Logge: "[WP→CRUMBS] {|learnings|} Crumbs geschrieben nach {crumbs_pfad}"
    CATCH:
      WARN: "WP-Crumbs-Erzeugung fehlgeschlagen (non-blocking, AK-01-02). Weiter ohne Crumbs."
4c. raw_source Append im Quell-BL-Item (BL-043 RF-03):
    # Nach Crumbs-Erzeugung: WP-Crumbs-Pfad in raw_source des Quell-BL-Items anhaengen
    # AK-03-01: APPEND — bestehende raw_source Eintraege bleiben erhalten
    # AK-03-02: crumbs_ref bleibt single-value (kein Schema-Breaking-Change)
    # AK-03-03: Non-blocking — Fehler blockiert Pipeline NICHT
    IF bl_source_id != null:
      TRY:
        # Vault-Pfad aus _backlog_index.md Lookup
        vault_pfad = index_zeile.vault_pfad  # z.B. "{VAULT_BASE}/BL-043-wp-crumbs-rueckkanal.md"
        IF DATEI EXISTIERT(vault_pfad):
          # Frontmatter lesen
          bestehende_raw_source = LIES Frontmatter(vault_pfad).raw_source  # String oder Liste
          # APPEND: WP-Crumbs-Pfad anhaengen
          IF bestehende_raw_source IST String:
            neue_raw_source = [bestehende_raw_source, crumbs_pfad]
          ELIF bestehende_raw_source IST Liste:
            neue_raw_source = bestehende_raw_source + [crumbs_pfad]
          ELSE:
            neue_raw_source = [crumbs_pfad]
          # Frontmatter-Feld aktualisieren (NUR raw_source, Rest bleibt)
          SCHREIBE Frontmatter(vault_pfad).raw_source = neue_raw_source
          Logge: "[WP→RAW_SOURCE] raw_source erweitert in {vault_pfad}: +{crumbs_pfad}"
        ELSE:
          WARN: "Vault-Datei nicht gefunden: {vault_pfad}. raw_source-Append uebersprungen."
      CATCH:
        WARN: "raw_source-Append fehlgeschlagen fuer {bl_source_id} (non-blocking, AK-03-03). Weiter ohne Append."
    ELSE:
      Logge: "[WP→RAW_SOURCE] SKIP — bl_source_id ist null (kein Quell-BL-Item zugeordnet)"
5. _manifest.md aktualisieren:
   chapter_{N}_status=ACCEPTED
   W_PUSH_ORCHESTRATE: {YYYY-MM-DD HH:MM}  ← (falls W_push_orchestrate ausgefuehrt)
5a. BL-206 AK-6: WP Re-Entry-Signal (NEU 2026-05-24)
    # Wenn WP via BL-206 Bottleneck-Route getriggert wurde (bottleneck_trigger=true),
    # idf_reentry_signal in WP_PIPELINE_STATE schreiben fuer IDF Re-Entry.
    IF WP_PIPELINE_STATE.bottleneck_trigger == true:
      # Welche W{n} wurden durch WP bestaetigt? Aus WP-Crumbs oder reflection.learnings
      confirmed_w_refs = extract_confirmed_w_refs(reflection.learnings) ?? []
      affected_items   = WP_PIPELINE_STATE.bottleneck_affected_items ?? []

      WP_PIPELINE_STATE.idf_reentry_signal = {
        "triggered":          true,
        "reason":             "WP-Done via BL-206 Bottleneck-Route (extern-Bottleneck geloest)",
        "affected_pl_items":  affected_items,
        "updated_w_refs":     confirmed_w_refs,
        "srs_refresh_needed": len(confirmed_w_refs) > 0,
        "loop_count_increment": 1,
        "wp_chapter_nr":      N,
        "completed_at":       now()
      }
      # _manifest.md wird im naechsten Schritt geschrieben
      Logge: f"[BL-206 AK-6] WP Re-Entry-Signal: {len(affected_items)} PLs, {len(confirmed_w_refs)} W{{n}} confirmed"
      audit_jsonl_append({type: "BL206_WP_REENTRY_SIGNAL",
                          affected_items: affected_items, w_updated: confirmed_w_refs})
    ELSE:
      Logge: "[BL-206 AK-6] Kein Bottleneck-WP-Kontext — kein idf_reentry_signal noetig"
6. session-state.json aktualisieren: next_chapter={N+1}
7. Melde User:
   "Kapitel {N} abgeschlossen.
    Naechstes Kapitel: /_WP_orchestrate {N+1} {difficulty} {ceiling} {floor}"
```

**Bei RETRY:**
```
1. Frage User nach Feedback (AskUserQuestion, Freitext)
2. Optional: research_add_exclusion fuer falsche Richtungen
3. Erstelle neue INNER-LOOP Tasks (Write → Visual → Quality → Convergence)
4. Team Lead spawnt naechsten Agent mit KURZLEBIG_PROMPT:
   wp-{chapter}-write mit Kontext "RETRY: User-Feedback: {feedback}"
5. Zurueck zu Phase 3.1 (Aktives Spawning)
```

**Bei ABORT:**
```
1. Keine aktiven Agents (kurzlebig, bereits terminiert)
2. TeamDelete
3. _manifest.md aktualisieren: phase=ABORTED
4. Melde User: "Pipeline gestoppt bei Kapitel {N}."
```

---

## PHASE 4: DISCOVERY-LOOP (v2.1: Source Diversity)

### Trigger-Bedingungen (2 Pfade):

**Pfad A: GAP (Coverage < 0.85)**
Worker meldet: "Coverage unter Threshold, Luecken erkannt"
→ Quellen fehlen komplett (weder intern noch extern)

**Pfad B: DISCOVERY (Coverage >= 0.85, external_ratio < 0.3) [NEU v2.1]**
Worker meldet: "Coverage hoch aber INTERNAL_ONLY, externe Quellen fehlen"
→ Keywords sind durch interne Docs abgedeckt, aber fuer akademisches
  Paper brauchen wir zitierbare externe Quellen (Papers, Surveys, etc.)

### Discovery-Loop Ablauf:

```
1. Team Lead erstellt zusaetzliche Tasks:

   TaskCreate: "WP Source Discovery"
     description: "/_WP_discovery ausfuehren.
       Fehlende EXTERNE akademische Quellen identifizieren via WebSearch.
       Bei DISCOVERY-Trigger: Suche gezielt nach Papers zu den Keywords
       die nur INTERNAL_ONLY Coverage haben.
       Bei GAP-Trigger: Suche nach allen gap_topics.
       Minimum: 7-10 akademische Papers finden.
       Topics: {gap_topics oder internal_only_keywords}"

   TaskCreate: "WP Research Ingest"
     description: "/_WP_research ausfuehren.
       Gefundene Quellen als Markdown in quellen/ schreiben
       (mit BibTeX-Frontmatter: Autor, Titel, Jahr, DOI/URL).
       DANACH: MCP research_ingest ausfuehren.
       MCP: research_ingest"
     blocked_by: (Discovery-Task)

   TaskCreate: "WP Re-Assessment"
     description: "/_WP_assess erneut ausfuehren.
       Pruefen ob Coverage UND external_ratio jetzt ausreichen.
       WICHTIG: Source Diversity Check (Schritt 2.5) ausfuehren!
       external_ratio muss >= 0.3 sein."
     blocked_by: (Research-Task)

2. Blockiere ChapterModel-Task auf Re-Assessment:
   TaskUpdate: chapterModel_task.addBlockedBy(re-assessment_task)

3. Team Lead spawnt wp-{chapter}-discovery mit KURZLEBIG_PROMPT:
   "Discovery-Loop: Externe akademische Quellen fehlen.
    /_WP_discovery ausfuehren."

4. Nach Re-Assessment:
   - external_ratio >= 0.3 → Weiter mit ChapterModel → ChapterGap
   - external_ratio < 0.3 → Nochmal Discovery (max 2 Iterationen)
   - Max Discovery-Iterationen erreicht → FORCE + WARNUNG
```

---

## ZUSAMMENFASSUNG: Sequenz-Diagramm

```
Team Lead                    Agent (wp-{ch}-{cmd})           User
    │                              │                          │
    ├─ TeamCreate ─────────────►   │                          │
    ├─ TaskCreate (Tasks 0-9) ──►  │                          │
    │                              │                          │
    │  ═══ SETUP ═══              │                          │
    │  Spawn wp-{ch}-init ──────►  │                          │
    │                              ├─ T0: /_WP_init           │
    │  ◄── "Init fertig" ─────────┤  (Agent stirbt)          │
    │  Spawn wp-{ch}-session ───►  │                          │
    │                              ├─ T1: /_WP_session        │
    │  ◄── "Session fertig" ───────┤  (Agent stirbt)          │
    │  Spawn wp-{ch}-structure ──► │                          │
    │                              ├─ T2: /_WP_structure      │
    │  ◄── "Struktur fertig" ──────┤  (Agent stirbt)          │
    │  Spawn wp-{ch}-assess ─────► │                          │
    │                              ├─ T3: /_WP_assess         │
    │  ◄── "Assessment fertig" ────┤  (Agent stirbt)          │
    │                              │                          │
    │  [Coverage OK?]              │                          │
    │  JA → weiter                 │                          │
    │  NEIN → Spawn discovery ──►  │                          │
    │                              ├─ T3a: /_WP_discovery     │
    │  ◄── fertig ────────────────┤  (Agent stirbt)          │
    │  Spawn wp-{ch}-research ──►  │                          │
    │                              ├─ T3b: /_WP_research      │
    │  ◄── fertig ────────────────┤  (Agent stirbt)          │
    │  Spawn wp-{ch}-assess ────►  │                          │
    │                              ├─ T3c: /_WP_assess (re)   │
    │  ◄── "Coverage OK" ─────────┤  (Agent stirbt)          │
    │                              │                          │
    │  Spawn wp-{ch}-chapterModel► │                          │
    │                              ├─ T4: /_WP_chapterModel   │
    │  ◄── "Model fertig" ────────┤  (Agent stirbt)          │
    │  Spawn wp-{ch}-chapterGap ►  │                          │
    │                              ├─ T5: /_WP_chapterGap     │
    │  ◄── "Gap fertig" ──────────┤  (Agent stirbt)          │
    │                              │                          │
    │  ┌─── INNER LOOP ───────────────────────────────────┐   │
    │  │  Spawn N Draft-Agents ►   │ (PARALLEL bei norm/hard) │
    │  │                           ├─ T6: /_WP_write       │   │
    │  │ ◄── "Drafts fertig" ─────┤  (Agents sterben)     │   │
    │  │  Spawn wp-{ch}-aggregation│                       │   │
    │  │                           ├─ T6m: Metadata        │   │
    │  │ ◄── "Metadata fertig" ───┤  (Agent stirbt)       │   │
    │  │  Spawn wp-{ch}-visual     │                       │   │
    │  │                           ├─ T7: /_WP_visual      │   │
    │  │ ◄── "Visuals fertig" ────┤  (Agent stirbt)       │   │
    │  │  Spawn wp-{ch}-qualityGate│                       │   │
    │  │                           ├─ T8: /_WP_qualityGate │   │
    │  │ ◄── "Quality fertig" ────┤  (Agent stirbt)       │   │
    │  │  Spawn wp-{ch}-convergence│                       │   │
    │  │                           ├─ T9: /_WP_convergence │   │
    │  │ ◄── "ITERATE" ───────────┤  (Agent stirbt)       │   │
    │  │                           │                       │   │
    │  │  [ITERATE?]               │                       │   │
    │  │  JA → neue T6-T9, Spawn ► │ (naechste Iteration)  │   │
    │  │  NEIN → CONVERGE ─────────┼───────────────────────┘   │
    │  └───────────────────────────┘                          │
    │                              │                          │
    ├─ TaskCreate (T10-T13) ────►  │                          │
    │  Spawn N Review-Agents ──►   │ (PARALLEL bei norm/hard) │
    │                              ├─ T10: /_WP_review        │
    │  ◄── "Reviews fertig" ──────┤  (Agents sterben)        │
    │  Spawn wp-{ch}-reviewAgg ──► │                          │
    │                              ├─ T10s: Score Aggregation │
    │  ◄── "Scores fertig" ───────┤  (Agent stirbt)          │
    │  Spawn wp-{ch}-synthesis ──► │                          │
    │                              ├─ T11: /_WP_synthesis     │
    │  ◄── "Synthesis fertig" ────┤  (Agent stirbt)          │
    │  Spawn wp-{ch}-chapterPDF ►  │                          │
    │                              ├─ T12: /_WP_chapterPDF ──►├─ Email+PDF
    │  ◄── "PDF fertig" ──────────┤  (Agent stirbt)          │
    │  Spawn wp-{ch}-reflect ────► │                          │
    │                              ├─ T13: /_WP_reflect       │
    │  ◄── "Reflect fertig" ──────┤  (Agent stirbt)          │
    │                              │                          │
    ├─ AskUserQuestion ───────────────────────────────────►  │
    │  ◄── ACCEPT / RETRY / ABORT ────────────────────────────┤
    │                              │                          │
    │  [ACCEPT]                    │                          │
    ├─ TeamDelete (keine aktiven Agents)                      │
    ├─ "Kapitel {N} fertig" ──────────────────────────────►  │
    │                              │                          │
    │  === NAECHSTES KAPITEL ===   │                          │
    │  /_WP_orchestrate {N+1}      │                          │
```

---

## TASK-BESCHREIBUNGEN (Vorlagen fuer TaskCreate)

### Task 0: Init + Ingest

```
Subject: "WP Init + Quellen Ingest"
ActiveForm: "Initializing project and ingesting sources"
Description: |
  Fuehre /_WP_init aus.
  Lies .claude/commands/_WP_init.md fuer Details.

  Falls Projekt NOCH NICHT initialisiert (kein config/project.yaml):
    MCP: research_init_project (Projekt-Ordner + config erstellen)

  Dann IMMER:
    MCP: research_ingest (alle Quellen aus quellen/ in RAG aufnehmen)

  Falls quellen/ leer ist:
    Melde "KEINE QUELLEN" an Team Lead. Team Lead entscheidet.

  Input: quellen/*.md, quellen/*.pdf, quellen/*.txt
  Output: config/project.yaml, references.bib, RAG Collection gefuellt

  Melde dem Team Lead:
    - Projekt initialisiert: Ja/Nein (schon vorhanden?)
    - Quellen gefunden: {N} Dateien
    - Chunks erstellt: {N}
    - BibTeX-Keys: {liste}
    - Collection: {name}
```

### Task 1: Session

```
Subject: "WP Session konfigurieren"
ActiveForm: "Configuring session parameters"
Description: |
  Fuehre /_WP_session aus.
  Lies .claude/commands/_WP_session.md fuer Details.

  Parameter:
    difficulty: {difficulty}
    chapter_focus: "{chapter_title}"
    ceiling: {ceiling}
    floor: {floor}

  Input: config/project.yaml, _manifest.md
  Output: session-state.json, _manifest.md (UPDATE)

  Melde dem Team Lead:
    - Difficulty gesetzt
    - Dimensions-Parameter berechnet
    - Agent-Anzahl pro Command
```

### Task 2: Structure

```
Subject: "WP Struktur extrahieren"
ActiveForm: "Extracting paper structure"
Description: |
  Fuehre /_WP_structure aus.
  Lies .claude/commands/_WP_structure.md fuer Details.

  Input: config/project.yaml, vorhandene LaTeX/Markdown-Dateien
  Output: output/chapter-structure.md, _manifest.md (UPDATE)

  Melde dem Team Lead:
    - Anzahl Sections fuer Kapitel {N}
    - Section-Titel
    - Subsection-Tiefe
```

### Task 3: Assessment (v2.1: Source Diversity)

```
Subject: "WP Knowledge Assessment"
ActiveForm: "Assessing knowledge coverage + source diversity"
Description: |
  Fuehre /_WP_assess aus (v1.1 mit Source Diversity Check).
  Lies .claude/commands/_WP_assess.md fuer Details.

  WICHTIG (v1.1): Fuehre Schritt 2.5 "Source Diversity Analysis" aus!
  Unterscheide INTERNAL (Projektdocs) von EXTERNAL (akademische Papers).
  Coverage ist nur COVERED wenn externe Quellen vorhanden sind.
  Keywords die NUR durch interne Docs abgedeckt sind → "INTERNAL_ONLY"
  (zaehlt NICHT als COVERED).

  Decision-Table (v1.1):
    coverage >= 0.85 AND external_ratio >= 0.3 → PASS → chapterModel
    coverage >= 0.85 AND external_ratio < 0.3  → DISCOVERY → discovery
    coverage < 0.85 AND budget > 0             → GAP → research
    coverage < 0.85 AND budget == 0            → FORCE → chapterModel

  MCP: research_query (RAG-Abfragen pro Section)
  Input: config/project.yaml, output/chapter-structure.md
  Output: output/assess/chapter-{N}-assessment.json

  Melde dem Team Lead:
    - Coverage-Score (0-100%)
    - external_ratio (0.0 - 1.0)
    - Source Diversity: X INTERNAL, Y EXTERNAL Dokumente
    - Anzahl Luecken (gap_topics)
    - Anzahl INTERNAL_ONLY Keywords
    - Decision: PASS / DISCOVERY / GAP / FORCE

  WICHTIG:
    - Bei external_ratio < 0.3 → melde "DISCOVERY" (externe Quellen fehlen)
    - Bei Coverage < 0.85 → melde "GAP" (Quellen fehlen komplett)
    - Team Lead erstellt dann Discovery/Research-Tasks.
```

### Task 4: Chapter Model

```
Subject: "WP Chapter Model erstellen"
ActiveForm: "Building chapter knowledge model"
Description: |
  Fuehre /_WP_chapterModel aus.
  Lies .claude/commands/_WP_chapterModel.md fuer Details.

  Input: output/assess/chapter-{N}-assessment.json,
         output/chapter-structure.md, output/references.bib
  Output: output/models/chapter-{N}-model.md

  Melde dem Team Lead:
    - Anzahl Themen
    - Themen-Liste (kurz)
    - Section-Zuordnung
```

### Task 5: Chapter Gap

```
Subject: "WP Chapter Gap Analyse"
ActiveForm: "Analyzing chapter gaps"
Description: |
  Fuehre /_WP_chapterGap aus.
  Lies .claude/commands/_WP_chapterGap.md fuer Details.

  MCP: research_gaps
  Input: output/models/chapter-{N}-model.md, config/project.yaml
  Output: output/assess/chapter-{N}-gaps.json

  Melde dem Team Lead:
    - gap_decision: WRITE | AUTOREVISE
    - gap_severity: NONE | MINOR | MODERATE | SEVERE
    - Betroffene Sections
```

### Task 6: Write (Iteration {I})

Diese Task-Beschreibung wird PRO AGENT erstellt. Ersetze {AGENT_ID},
{AGENT_ROLE}, {AGENT_FOCUS}, {AGENT_KEYWORDS} mit den Werten fuer diesen Agent.

```
Subject: "WP Draft schreiben (Iter {I}, Agent {AGENT_ID})"
  [oder: "WP Draft schreiben (Iter {I}, Solo)" bei easy]
ActiveForm: "Writing chapter draft {AGENT_ID}"
Description: |
  Fuehre /_WP_write aus.
  Lies .claude/commands/_WP_write.md fuer Details.

  MODUS: Du bist Agent {AGENT_ID} ({AGENT_ROLE}).
  DU BIST: Agent {AGENT_ID} von {TOTAL_AGENTS} parallelen Draft-Agents.
    Fokus: {AGENT_FOCUS}
    Keywords (RAG-Bias): {AGENT_KEYWORDS}

  DEINE AUFGABE:
    Schreibe NUR output/drafts/chapter-{N}/draft-{AGENT_ID}.md
    Fuehre {rag_queries_per_agent} RAG-Queries mit deinen Keywords durch.
    Andere Worker schreiben die anderen Drafts gleichzeitig.

  WICHTIG:
    - Bei easy (Solo): Schreibe alle Rollen sequentiell (alle draft-A{NN}.md).
    - Bei normal/hard: Schreibe NUR DEINEN Draft (draft-{AGENT_ID}.md).
    - metadata.json NICHT schreiben (das macht Task 6m / Aggregations-Task).
    - session-state.json NICHT schreiben (Race Condition vermeiden).

  MCP: research_query (Kap.1) oder research_query_r2 (Kap.2+)
  Input: output/models/chapter-{N}-model.md,
         output/assess/chapter-{N}-gaps.json,
         session-state.json
  Output: output/drafts/chapter-{N}/draft-{AGENT_ID}.md

  Bei Iteration > 1: Lies auch
    output/quality/chapter-{N}/quality-report.json
    (Verbesserungsvorschlaege einarbeiten)

  Melde dem Team Lead:
    - Draft {AGENT_ID} erstellt
    - Word Count
    - Citation Count
    - [FIGURE: ...] Placeholder Count
```

### Task 6m: Draft Metadata aggregieren

```
Subject: "WP Draft Metadata aggregieren"
ActiveForm: "Aggregating draft metadata"
Description: |
  Lies alle output/drafts/chapter-{N}/draft-A{NN}.md (alle vorhandenen).
  Erstelle output/drafts/chapter-{N}/metadata.json mit:
    - draft_count: Anzahl vorhandener Drafts
    - drafts: [{id, word_count, citation_count, figure_count}]
    - total_word_count
    - timestamp
  Aktualisiere _manifest.md: write_completed, draft_count.
  Aktualisiere session-state.json: draft_metadata.

  Melde dem Team Lead:
    - Anzahl Drafts aggregiert
    - Total Word Count
    - metadata.json erstellt
```

### Task 7: Visual (Iteration {I})

```
Subject: "WP Visuals erstellen (Iter {I})"
ActiveForm: "Creating visual figures"
Description: |
  Fuehre /_WP_visual aus.
  Lies .claude/commands/_WP_visual.md fuer Details.

  Input: output/drafts/chapter-{N}/draft-A*.md (alle Drafts),
         [FIGURE: ...] Placeholders
  Output: output/figures/chapter-{N}/fig-{NN}.tikz

  Falls KEINE [FIGURE: ...] Placeholders in den Drafts:
    Melde "Keine Visuals noetig" und markiere Task als completed.

  Melde dem Team Lead:
    - Anzahl Figures erstellt
    - Figure-Typen (TikZ, pgfplots, Tabelle)
```

### Task 8: Quality Gate (Iteration {I})

```
Subject: "WP Quality Gate (Iter {I})"
ActiveForm: "Running quality gates"
Description: |
  Fuehre /_WP_qualityGate aus.
  Lies .claude/commands/_WP_qualityGate.md fuer Details.

  8 Gates pruefen:
    G1: Structure  G2: Word Count  G3: Citations  G4: Figures
    G5: RAG-Verify G6: Style       G7: Coherence  G8: Cross-Refs

  MCP: research_verify (G5)
  Input: output/drafts/chapter-{N}/*, output/figures/chapter-{N}/*
  Output: output/quality/chapter-{N}/quality-report.json

  Melde dem Team Lead:
    - Composite Score (0-10)
    - Gates PASSED / FAILED (Liste)
    - Groesste Schwachstelle
```

### Task 9: Convergence (Iteration {I})

```
Subject: "WP Convergence Check (Iter {I})"
ActiveForm: "Checking convergence"
Description: |
  Fuehre /_WP_convergence aus.
  Lies .claude/commands/_WP_convergence.md fuer Details.

  Decision-Logik:
    composite >= threshold AND QUALITY_PASSED → CONVERGE
    quality_iteration >= max → FORCE
    Stagnation erkannt → FORCE
    Fortschritt vorhanden → ITERATE

  Input: output/quality/chapter-{N}/quality-report.json,
         session-state.json (quality_history)
  Output: output/quality/chapter-{N}/convergence-decision.json

  WICHTIG: Melde dem Team Lead die DECISION:
    "CONVERGE: Score {X}/10, Qualitaet ausreichend"
    oder "ITERATE: Score {X}/10, Verbesserung moeglich"
    oder "FORCE: Score {X}/10, Max Iterationen erreicht"

  Team Lead entscheidet basierend auf deiner Meldung
  ob neue Tasks erstellt werden.
```

### Task 10: Review (pro Review-Agent)

Diese Task-Beschreibung wird PRO REVIEW-AGENT erstellt. Ersetze {REVIEWER_ID}
mit A01, A02, ... je nach difficulty.

```
Subject: "WP Cross-Review (Agent {REVIEWER_ID})"
  [oder: "WP Cross-Review (Solo)" bei easy]
ActiveForm: "Reviewing chapter as {REVIEWER_ID}"
Description: |
  Fuehre /_WP_review aus.
  Lies .claude/commands/_WP_review.md fuer Details.

  MODUS: Du bist Review-Agent {REVIEWER_ID}.

  DEINE AUFGABE:
    Reviewe ALLE anderen Drafts ausser draft-{REVIEWER_ID}.md.
    Bewerte jeden Draft auf 5 Dimensionen (gemaess /_WP_review Schritt 2).
    Schreibe NUR output/reviews/chapter-{N}/agent-{REVIEWER_ID}-reviews.json

  WICHTIG:
    - Bei easy (Solo): Fuehre alle Reviews sequentiell durch, schreibe alle Outputs.
    - Bei normal/hard: Schreibe NUR deine agent-{REVIEWER_ID}-reviews.json.
    - KEIN review-matrix.json schreiben (das macht Task 10s).
    - KEIN review-summary.md schreiben (das macht Task 10s).

  Input: output/drafts/chapter-{N}/draft-A*.md
         (alle ausser draft-{REVIEWER_ID}.md bei normal/hard)
  Output: output/reviews/chapter-{N}/agent-{REVIEWER_ID}-reviews.json

  Melde dem Team Lead:
    - Reviews abgeschlossen als {REVIEWER_ID}
    - Anzahl bewerteter Drafts
    - Lowest Score (erste Einschaetzung)
```

### Task 10s: Review Score aggregieren

```
Subject: "WP Review Score aggregieren"
ActiveForm: "Aggregating review scores"
Description: |
  Alle Review-Agents sind fertig. Jetzt: Score-Aggregation + Matrix erstellen.
  Lies /_WP_review Schritt 3-5 fuer Details.

  Lies alle output/reviews/chapter-{N}/agent-A{NN}-reviews.json

  Fuehre /_WP_review Schritt 3-5 aus:
    - Score pro Draft berechnen (Durchschnitt aller Reviewer-Scores)
    - Ranking erstellen
    - Min-Score Filter anwenden
    - Top-K selektieren

  Schreibe:
    - output/reviews/chapter-{N}/review-matrix.json
    - output/reviews/chapter-{N}/review-summary.md
    - _manifest.md UPDATE (review_completed: true, top_k_drafts)
    - session-state.json UPDATE (review_results)

  Melde dem Team Lead:
    - Review-Score (Durchschnitt)
    - Top 3 Verbesserungsvorschlaege
    - Gewinner-Draft (hoechster Score)
```

### Task 11: Synthesis

```
Subject: "WP Draft Synthesis"
ActiveForm: "Synthesizing final draft"
Description: |
  Fuehre /_WP_synthesis aus.
  Lies .claude/commands/_WP_synthesis.md fuer Details.

  Fuehre alle Drafts + Review-Feedback zusammen zu einem
  finalen Kapitel-Draft.

  Input: output/drafts/chapter-{N}/draft-A*.md,
         output/reviews/chapter-{N}/review-summary.md
  Output: output/synthesis/chapter-{N}/final-draft.md,
          output/synthesis/chapter-{N}/merge-report.json

  Melde dem Team Lead:
    - Word Count (final)
    - Citation Count (final)
    - Merge-Konflikte (falls welche)
```

### Task 12: Chapter PDF

```
Subject: "WP Chapter PDF generieren"
ActiveForm: "Generating PDF and sending email"
Description: |
  Fuehre /_WP_chapterPDF aus.
  Lies .claude/commands/_WP_chapterPDF.md fuer Details.

  Schritte:
  a) final-draft.md → LaTeX konvertieren
  b) pdflatex + bibtex (3-Pass)
  c) Email senden (Gmail SMTP, source ~/.bashrc)

  NON-BLOCKING: Bei PDF-Fehlern trotzdem weiter.
  Sende Markdown-Draft als Fallback.

  Input: output/synthesis/chapter-{N}/final-draft.md,
         output/references.bib
  Output: output/pdf/chapter-{N}/chapter-{N}.pdf

  Melde dem Team Lead:
    - PDF erstellt: Ja/Nein
    - Seitenzahl
    - Email gesendet: Ja/Nein
    - Fehler (falls welche)
```

### Task 13: Reflect

```
Subject: "WP Reflect + Summary"
ActiveForm: "Reflecting on chapter"
Description: |
  Fuehre /_WP_reflect aus.
  Lies .claude/commands/_WP_reflect.md fuer Details.

  Schritte:
  a) MCP: research_mark_covered (Kapitel-Content → COVERED)
  b) Kapitel-Summary erstellen:
     - Score, Iterations, Word Count, Citations
     - Learnings (3-7 Bullet Points)
  c) reflection-report.json schreiben

  Input: output/synthesis/chapter-{N}/final-draft.md,
         output/quality/chapter-{N}/convergence-decision.json
  Output: output/reflection/chapter-{N}/reflection-report.json,
          output/reflection/chapter-{N}/kapitel-learnings.md

  Melde dem Team Lead (AUSFUEHRLICH):
    - Finaler Score
    - Gesamt-Iterationen
    - Word Count + Citation Count
    - Top 3 Learnings
    - "Kapitel {N} bereit fuer User-Review"

  DANACH: WARTE. Team Lead holt User-Feedback.
```

---

## MULTI-WORKER PATTERN (v3.0: kurzlebig)

```
SEQUENTIELLE PHASE:
  Team Lead spawnt pro Step 1 kurzlebigen Agent wp-{chapter}-{command}
  (init, session, structure, assess, chapterModel, chapterGap,
   aggregation, visual, qualityGate, convergence,
   reviewAggregation, synthesis, chapterPDF, reflect)

PARALLELE PHASE (normal/hard):
  N Agents PARALLEL pro Welle:
  - wp-draft-A{NN} ({middle}): Draft-Agents PARALLEL
  - wp-review-A{NN} ({middle}): Review-Agents PARALLEL
  run_in_background: true fuer alle parallelen Agents

WICHTIG:
  - Spawne parallele Agents mit run_in_background: true
  - Warte auf ALLE parallelen Agents bevor Aggregations-Agent startet
  - Draft-Agents nutzen {middle}-Modell (nicht ceiling)
  - Review-Agents nutzen {middle}-Modell (nicht ceiling)
  - Synthese/Aggregation/Sequentielle nutzen {ceiling}-Modell
```

## Wellen-Konfiguration write/review (AK-06-03, BL-036)

| Step   | easy | normal | hard | Modell  |
|--------|------|--------|------|---------|
| write  | 1    | 3      | 5    | ceiling |
| review | 1    | 2      | 3    | ceiling |

State-Transition: write → PARALLEL(N agents) → aggregation → sequential
                   review → PARALLEL(N agents) → reviewAggregation → sequential

---

## QUICK-START

Wenn User sagt "schreibe Kapitel 1":

```
1. /_WP_orchestrate 1
2. Team Lead erstellt Team "wp-chapter-1" + Tasks
3. Team Lead spawnt pro Step kurzlebigen Agent wp-1-{command}
4. Agents: init → session → structure → assess → chapterModel → chapterGap
5. Team Lead spawnt Draft-Agents (PARALLEL bei normal/hard)
6. Bei ITERATE: Team Lead erstellt neue Loop-Tasks, spawnt Agents
7. Bei CONVERGE: Team Lead erstellt Post-Convergence Tasks, spawnt Review-Agents
8. Nach Reflect: Team Lead holt User-Feedback (HiL)
9. ACCEPT → TeamDelete → "/_WP_orchestrate 2"
10. RETRY → Neue Loop-Tasks → Team Lead spawnt Agents
11. ABORT → TeamDelete → Pipeline gestoppt
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| Agent meldet MCP-Fehler | Team Lead: MCP health_check. Bei Timeout: Warte + Retry. |
| Agent stagniert (keine Message >5min) | Team Lead: SendMessage "Status?" an Agent |
| Agent meldet fehlende Datei | Team Lead: Pruefe ob vorheriger Task korrekt war. Ggf. wiederholen. |
| PDF-Kompilierung fehlschlaegt | NON-BLOCKING. Sende Markdown-Draft per Email. |
| RAG Collection leer | BLOCKING. Melde User: "/_WP_init oder /_WP_research noetig." |
| Agent crashed | Team Lead: Neuen Agent spawnen (wp-{chapter}-{command}), gleichen Task zuweisen. |

---

ARGUMENTS: $ARGUMENTS
