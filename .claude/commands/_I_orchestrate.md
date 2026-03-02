# /_I_orchestrate - Team Lead I-Pipeline-Orchestrierung

```yaml
status: active
version: 2.5.0
created: 2026-02-15
updated: 2026-02-27
op: ImplementationPipeline
phase: Meta
type: orchestration
chain_position: meta
team_based: true
changelog: |
  v1.0: Initialer Entwurf (SC-Cycle Ergebnis).
  v1.1: FIX - TeamCreate + Task-Spawn + "1 Task = 1 Command" Prinzip.
        Identische Team-Architektur wie SC_orchestrate.
        Worker arbeitet im WORKTREE-Ordner (absoluter Pfad).
  v2.0: WellenRedesign (W7-Compliance).
        Option 3: Stufen-Modell - Team Lead steuert STUFEN statt langlebige Worker.
        Kurzlebige Single-Command-Agents (KURZLEBIG_PROMPT) statt Worker-Loop.
        Resume-Zaehler persistent im Manifest (_manifest.md YAML-Frontmatter).
        Stagnation-Check Manifest-basiert (/compact-sicher).
        Agent-Naming: i-sc-{SLICE}-{CMD}-b{N}.
        VERTRAG-Block hinzugefuegt.
  v2.1: Debloat-Hook (EC-F, ModelBloat 2026-02-26).
        Schritt 10a: Debloat-Check nach codeSystem-Stufe (>500Z → /_D_orchestrate vorschlagen).
        HiL: User entscheidet ob Debloat jetzt oder spaeter.
  v2.2: Welle-0 Entity-Readiness-Check (EC-3/OP-5).
        Schritt 0.3: haiku Pre-Check ob alle Entities existieren bevor Pipeline startet.
        CLEAR → weiter, BLOCKED → STOPP mit Blocker-Bericht + HiL.
        Verhindert 100% Artefakt-Verschwendung bei fehlenden Entities (DCSRE-93 v1).
  v2.3: I-ExitReport + ParkingLot-Aktivierung (PN-1, 2026-02-27).
        KURZLEBIG_PROMPT: Parking-Lot APPEND Pflicht bei Findings.
        KURZLEBIG_PROMPT: SendMessage erweitert um block_reason={reason}.
        Manifest worktrees-Schema: blocker + findings Felder ergaenzt.
  v2.4: Refactoring-Checkpoint (SC-Cycle I-18, W174, 2026-02-27).
        Schritt 9a: HiL-Checkpoint zwischen diffAudit und Pre_PR.
        DiffAudit-Findings mit Refactoring-Charakter → Parking-Lot Eintrag.
        Schliesst Luecke zwischen "Probleme identifiziert" und "Clean Code erwartet".
  v2.5: Query-Guard + exit_report query_status (SC-Cycle I-14+I-05b, 2026-02-27).
        KURZLEBIG_PROMPT: query_status Pflichtfeld im exit_report (executed|skipped|missing).
        PHASE 3: Guard-Check nach warte_bis_alle_completed, HiL bei >=50% missing.
        Manifest: query_guard_warnings Zaehler. Adressiert W173+W183 (EC-I2 DONE).
```

---

```
+======================================================================+
| META-COMMAND: /_I_orchestrate                                        |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU - die ausfuehrende Claude-Instanz)              |
| AGENTS: Kurzlebige Single-Command-Agents (Modell: sonnet)            |
|         1 Agent = 1 Command = 1 Batch. Kein Worker-Loop.             |
|                                                                        |
| ZWECK: Orchestriert alle Worktree-Slices durch die I-Pipeline via    |
|        STUFEN-MODELL. Team Lead steuert STUFEN (nicht Worktrees).    |
|        Pro Stufe: alle aktiven Slices PARALLEL (kurzlebige Agents).  |
|        Team Lead erstellt Team, Tasks, spawnt Agents, liest Manifest.|
|                                                                        |
| PRINZIP: STUFEN-MODELL (W7-compliant, WellenRedesign Option 3).      |
|          Stufe = 1 Command-Typ fuer ALLE parallelen Slices.           |
|          1 Agent = 1 Command = 1 Batch (kurzlebig, kein Loop).       |
|          Kein Worker spawnt Sub-Agents (W7: Workers haben kein Task-Tool). |
|          Resume-Zaehler persistent im Manifest (compact-sicher).      |
|          Team Lead fuehrt KEINE Commands selbst aus.                  |
|                                                                        |
| PIPELINE (pro Slice/Worktree):                                        |
|   MOTHERSHIP:                                                          |
|   1. /_I_cleanCodeArchitect {NAME}                                    |
|   2. [/_I_mitose] (OPTIONAL bei >1 Slice)                            |
|   3. [/_I_fanOut] (OPTIONAL nach mitose)                              |
|   WORKTREE-STUFEN (pro Welle, alle Slices parallel):                  |
|   4. STUFE 1: /_I_cleanCodeSlice (alle Slices parallel)              |
|   5. STUFE 2: /_I_codeAtomic (Batch-Resume, alle parallel)           |
|   6. STUFE 3: /_I_codeIntegration (Batch-Resume, alle parallel)      |
|   7. STUFE 4: /_I_codeSystem (Batch-Resume, alle parallel)           |
|   HiL: Test-Suite                                                      |
|   8. STUFE 5: /_I_verify (alle Slices parallel)                      |
|   HiL: Commits                                                         |
|   9. STUFE 6: /_I_fanIn (sequentiell pro Slice, Mothership)          |
|   GLOBAL:                                                              |
|  10. /_I_verify global                                                |
|  11. /_I_diffAudit                                                    |
|  11a. Refactoring-Checkpoint (HiL) — Refactoring-Items → Parking-Lot |
|  12. /_Pre_PR_orchestrate                                              |
|  13. /_W_push_orchestrate {NAME} normal (Post-Pipeline Wissens-Push)   |
|                                                                        |
| HUMAN-IN-THE-LOOP (2 Checkpoints):                                    |
|   1. Nach codeSystem-Stufe: User fuehrt volle Test-Suite aus         |
|   2. Nach verify-Stufe: User committet in ALLEN Worktrees            |
|                                                                        |
| FLOW:                                                                  |
|   SETUP → MOTHERSHIP → [STUFEN-LOOP pro Welle] → GLOBAL → HiL       |
+======================================================================+
```

---

## VERTRAG

```
LIEST:
  .claude/analysis/_manifest.md          (NAME, PHASE, SYSTEM-MODEL, SCHWIERIGKEIT, I_PIPELINE_STATE)
  sc_status aus _manifest.md             (Pre-Check vor Pipeline-Start — QW-2b)
  .claude/Task.md                        (Task-Definition, PFLICHT)
  .claude/models/{NAME}_Model.md         (Feature-Modell, PFLICHT)
  output/po/user-stories.json            (PO-Pipeline Output, falls vorhanden — W27)
  .claude/analysis/synthese/{NAME}-ARCHITECT.md  (Slice-Definition, nach cleanCodeArchitect)
  .claude/analysis/synthese/{NAME}-HANDOFF.md  ← ADR-Kontext (Architektur-Entscheidungen aus SC, falls vorhanden)
  pipeline_mode aus _manifest.md         (Pre-Check Schritt 0.2b — EC-4, EC-5: READY_FOR_I erwartet)
  sc_i_gate aus _manifest.md             (Gate-Status lesen — EC-5: SC-seitiges Gate)
  {WORKTREE_PATH}/.claude/analysis/synthese/ATOMIC-{SLICE}.md   (status: partial|final)
  {WORKTREE_PATH}/.claude/analysis/synthese/INTEGRATION-{SLICE}.md
  {WORKTREE_PATH}/.claude/analysis/synthese/SYSTEM-{SLICE}.md

SCHREIBT:
  .claude/analysis/_manifest.md          (I_PIPELINE_STATE: stufen_status, resume_zaehler, worktrees)
  Tasks (via TaskCreate)
  Agents (via Task-Tool, KURZLEBIG_PROMPT)
  pipeline_mode: I_RUNNING               (Schritt 0.5 nach HANDOFF-Konsumption — EC-4)
  i_gate_response                        (Schritt 0.4: accept_start|reject_needs_more_sc — EC-5)
  handoff_consumed, handoff_consumed_at  (Schritt 0.4: Konsumptions-Flags — EC-6)
  handoff_context                        (Schritt 0.4: Strukturierter HANDOFF-Inhalt — EC-6)
  i_sc_return                            (Phase 3 Query-Guard I-14: Rueckkehr-Signal — EC-3)
  recovery_cycle_count                   (Phase 3: Recovery-Zaehler — EC-3)

HAUPTPRODUKT: CODE
  (Zentrales Artefakt dieser Phase: Implementierter Code)

PRODUZIERT (via Agents):
  Implementierter Code (*.cs, *.ts, Migrations, Config)  ← HAUPTPRODUKT
  .claude/analysis/synthese/{NAME}-ARCHITECT.md  (via cleanCodeArchitect-Agent)
  {WORKTREE}/.claude/analysis/synthese/CLEANCODE-{SLICE}.md
  {WORKTREE}/.claude/analysis/synthese/ATOMIC-{SLICE}.md
  {WORKTREE}/.claude/analysis/synthese/INTEGRATION-{SLICE}.md
  {WORKTREE}/.claude/analysis/synthese/SYSTEM-{SLICE}.md
  {WORKTREE}/.claude/analysis/synthese/VERIFY-{SLICE}.md

INVARIANTEN:
  - Team Lead fuehrt KEINE Commands selbst aus (R2)
  - 1 Agent = 1 Command = 1 Batch (R3, R4)
  - Kein Agent spawnt Sub-Agents (W7, R9)
  - Resume-Zaehler IMMER im Manifest (nie im Kontext) (R7)
  - Manifest-Update VOR /compact und nach JEDER Stufe (R7)
  - Stagnation = 5x resume_zaehler[slice][cmd] >= 5 (Manifest-basiert)
```

---

## Aufruf

```
/_I_orchestrate {NAME} [worktree_path]
```

**Parameter:**

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `NAME` | (PFLICHT) | String | Feature-Name (fuer Team, Tasks, Manifest) |
| `difficulty` | normal | easy, normal, hard | Steuert Agent-Anzahl, Wellen-Tiefe |
| `ceiling` | sonnet | haiku, sonnet, opus | Hoechstes Modell (Synthese-Wellen) |
| `floor` | haiku | haiku, sonnet | Niedrigstes Modell (Exploration-Wellen) |
| `worktree_path` | (cwd) | Pfad | Absoluter Pfad zum Arbeits-Ordner. Worker arbeitet HIER. |

**Beispiele:**
```
/_I_orchestrate DCSRE-93                           → normal, sonnet/haiku
/_I_orchestrate DCSRE-881 hard opus haiku C:\...   → hard, opus ceiling
/_I_orchestrate QuickFix easy                       → easy, 1 Agent solo
```

**Modell-Zuordnung und Skalierung (universelles Wellen-Pattern):**

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
Gilt fuer ALLE Commands die Wellen unterstuetzen (cleanCodeArchitect, cleanCodeSlice, etc.).

---

## GLOBALE PARAMETER (/_param Override)

Lies `.claude/analysis/_manifest.md` und suche nach GLOBAL_* Feldern.
Falls gesetzt, ueberschreiben sie die lokalen Parameter-Defaults:

| Manifest-Feld | Wirkung |
|---|---|
| `GLOBAL_DIFFICULTY` | Ueberschreibt lokalen `difficulty` Default |
| `GLOBAL_CEILING` | Kappt lokales ceiling: `effektiv = min(lokal, GLOBAL_CEILING)` |
| `GLOBAL_FLOOR` | Hebt lokalen floor an: `effektiv = max(lokal, GLOBAL_FLOOR)` |

**Berechnung:**
```
Hierarchie: opus=3, sonnet=2, haiku=1
IF GLOBAL_DIFFICULTY gesetzt UND != "(nicht gesetzt)": difficulty = GLOBAL_DIFFICULTY
IF GLOBAL_CEILING gesetzt UND != "(nicht gesetzt)":    ceiling = min(ceiling, GLOBAL_CEILING)
IF GLOBAL_FLOOR gesetzt UND != "(nicht gesetzt)":      floor = max(floor, GLOBAL_FLOOR)
Validierung: ceiling >= floor (sonst ceiling = floor + Warning ausgeben)
middle = sonnet wenn ceiling=opus, haiku wenn ceiling=sonnet, haiku wenn ceiling=haiku
```

**Falls KEINE GLOBAL_* Felder gesetzt:** Lokale Defaults gelten unveraendert.

---

## PHASE 1: TEAM SETUP

### Schritt 1.1: Kontext laden

Lies folgende Dateien (falls vorhanden):
1. `.claude/analysis/_manifest.md` → aktueller Stand, NAME, Phase
2. `.claude/Task.md` → existierende Aufgabendefinition
3. `.claude/models/{NAME}_Model.md` → existierendes Model
4. `.claude/analysis/synthese/{NAME}-ARCHITECT.md` → Slice-Definition

Bestimme **WORKTREE_PATH:**
- Falls `worktree_path` Parameter gegeben → nutze diesen
- Falls nicht → nutze aktuelles Arbeitsverzeichnis (cwd)
- Ermittle den ABSOLUTEN Pfad (z.B. `C:\Users\...\DCSRE-93_Einrichtungsdetails_Analyse`)

Bestimme Startpunkt:
- Kein ARCHITECT.md → Ab cleanCodeArchitect (Schritt 1)
- ARCHITECT.md vorhanden → Ab cleanCodeSlice (Schritt 4)

### Schritt 1.1a: G-SESSION-INIT (Stale-Task-Cleanup)

**Zweck:** Erkennt und bereinigt stale `in_progress` Tasks aus einer vorangegangenen abgebrochenen Session (F06-Guard, W162).

```
G-SESSION-INIT Algorithmus:

1. TaskList aufrufen → alle Tasks lesen
2. Gibt es Tasks mit status=in_progress?
   → NEIN: Keine stale Tasks → WEITER zu Schritt 1.1b
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

### Schritt 1.1a: W_fetch — Bestehendes Wissen holen (v2.4+, I-04)

**Zweck:** Vor Pipeline-Start bestehendes Wissen aus der feature-lokalen RAG Collection abrufen,
damit Cross-Slice-Lernen und SC-Erkenntnisse in die I-Pipeline einfliessen (W146, W173).

```
1. Pruefe ob feature-lokale RAG Collection existiert:
   → Collection-Name: "i_knowledge_{feature_id}" oder "local_knowledge_{feature_id}"
   → mcp__cleancodermcp__list_collections() → Suche nach passendem Namen

2. Falls Collection existiert UND nicht leer (count > 0):
   → Rufe /_W_fetch {NAME} auf
   → Ergebnis (relevante W{n}, Patterns, Erkenntnisse) in KURZLEBIG_PROMPT
     als KONTEXT-Block an nachfolgende Worker uebergeben

3. Falls KEINE Collection oder Collection leer:
   → SKIP (Graceful Degradation)
   → Logge: "W_fetch: Keine feature-lokale Collection gefunden → SKIP"

4. Ergebnis im Manifest notieren:
   → I_PIPELINE_STATE.w_fetch = "DONE" | "SKIP (no collection)"
```

**Graceful Degradation:** Kein Abbruch bei fehlender Collection. W_fetch wird erst nach
erstem _W_push_temp oder SC-Zyklus nuetzlich (Bootstrapping-Problem, W173).

---

### Schritt 1.1b: I-Knowledge Collection Init (RAG Rueckkanal)

**Zweck:** Feature-lokale RAG Collection fuer Cross-Slice-Lernen initialisieren (F01+F02-Kern, W146+W147).

```
1. Feature-ID aus Manifest extrahieren:
   → NAME-Feld → Sanitize (lowercase, Sonderzeichen → _)
   → feature_id = Beispiel: "dcsre881" fuer "DCSRE-881"

2. Collection-Name bilden:
   → "i_knowledge_{feature_id}"
   → GETRENNT von "local_knowledge_" (Qualitaets-Level unterschiedlich, W146)

3. MCP Collection sicherstellen (idempotent):
   → mcp__cleancodermcp__create_collection(name="i_knowledge_{feature_id}")
   → "created" oder "exists" → BEIDE OK

4. Ergebnis im Manifest notieren:
   → I_PIPELINE_STATE.rag_collection = "i_knowledge_{feature_id}"
   → I_PIPELINE_STATE.rag_init = "{HEUTE}"
```

**Graceful Degradation:** Falls MCP nicht erreichbar → WARNUNG ausgeben, Pipeline NICHT abbrechen.
Collection-Name in KURZLEBIG_PROMPT an Worker uebergeben (benoetigt fuer /_I_push_temp).

---

### Schritt 1.2: Team erstellen

```
TeamCreate:
  team_name: "i-pipeline-{NAME}"
  description: "I-Pipeline - {NAME}"
```

### Schritt 1.3: Initiale Tasks erstellen

**NUR MOTHERSHIP-Tasks initial erstellen** (Stufen-Tasks werden dynamisch pro Stufe erstellt):

| # | Task Subject | Wer fuehrt aus | Blocked By |
|---|-------------|----------------|------------|
| 1 | Architektur definieren: /_I_cleanCodeArchitect {NAME} | Team Lead spawnt 1 Agent | - |
| (Weitere Stufen-Tasks werden dynamisch nach ARCHITECT.md erstellt) |

**Stufen-Sequenz (blocked_by Abhaengigkeiten fuer dynamische Task-Erstellung):**

| Stufe | Command | Blocked By |
|-------|---------|------------|
| 1 | cleanCodeArchitect | - (Startpunkt) |
| 2 | cleanCodeSlice (pro Slice) | cleanCodeArchitect |
| 3 | codeAtomic (pro Slice, Batch-Resume) | cleanCodeSlice (gleicher Slice) |
| 4 | codeIntegration (pro Slice, Batch-Resume) | codeAtomic (gleicher Slice) |
| 5 | codeSystem (pro Slice, Batch-Resume) | codeIntegration (gleicher Slice) |
| 6 | verify (pro Slice) | codeSystem (gleicher Slice) |
| 7 | fanIn (pro Slice, sequentiell) | verify (gleicher Slice) + User-Commit HiL |

HINWEIS: Innerhalb einer Stufe laufen alle aktiven Slices PARALLEL (keine gegenseitige Blockierung). Nur aufeinanderfolgende Stufen blockieren sich.

**DYNAMISCH (nach ARCHITECT.md gelesen, pro Stufe pro Slice):**

Pro Stufe erstellt Team Lead Tasks dynamisch - NICHT upfront:
- STUFE cleanCodeSlice: N Tasks (1 pro Slice in Welle)
- STUFE codeAtomic: N Tasks pro Batch-Zyklus
- etc.

Task-Format pro Stufen-Task:
```
subject: "[{SLICE}] {command} Batch {N}"
description: "[WORKER-MODE] {command} {SLICE} Batch {N}
              Worktree: {WORKTREE_PATH}"
```

### Schritt 1.4: Stufen-Agents spawnen (pro Stufe)

Agents werden NICHT initial gespawnt, sondern STUFEN-WEISE:

```
Pro Stufe und pro Batch-Zyklus:

FOR EACH slice IN aktive_slices:
  task_id = TaskCreate(
    subject: "[{SLICE}] {COMMAND} Batch {BATCH_NUM}",
    description: "[WORKER-MODE] {COMMAND} {SLICE} Batch {BATCH_NUM}
                  Worktree: {WORKTREE_PATH}"
  )
  Task(
    name: "i-sc-{SLICE}-{COMMAND}-b{BATCH_NUM}",
    subagent_type: "general-purpose",
    model: "sonnet",
    team_name: "i-pipeline-{NAME}",
    mode: "bypassPermissions",
    prompt: KURZLEBIG_PROMPT(SLICE, COMMAND, BATCH_NUM, task_id, WORKTREE_PATH)
  )
  manifest.aktive_agent_ids.append("i-sc-{SLICE}-{COMMAND}-b{BATCH_NUM}")

manifest.update()  # Sofort persistieren
```

**WICHTIG (Stufen-Modell):**
- Alle Slices einer Stufe werden GLEICHZEITIG gespawnt (parallel)
- Nach Stufen-Abschluss: naechste Stufe spawnen (reaktiv)
- Kein Agent wird initial fuer alle Stufen gespawnt

---

## PHASE 2: KURZLEBIG_PROMPT (Single-Command-Agent)

Pro Stufe spawnt Team Lead N kurzlebige Agents - je 1 pro aktivem Slice.
Jeder Agent bekommt diesen minimalen Prompt (kein Worker-Loop, kein TaskList-Looping):

```
Du bist ein Single-Command-Agent fuer die I-Pipeline.
Agent-Name: i-sc-{SLICE}-{COMMAND}-b{BATCH_NUM}
Team: i-pipeline-{NAME}

═══ DEIN AUFTRAG ═══

Genau 1 Command ausfuehren, dann fertig.

Command:     /_I_{COMMAND} {SLICE}
Worktree:    {WORKTREE_PATH}
Batch-Nr:    {BATCH_NUM}  (1 = erster Lauf, 2+ = Resume)
Task-ID:     {TASK_ID}

═══ WISSEN ABRUFEN (PFLICHT) ═══

Feature-lokales Wissen MUSS abgefragt werden:
  mcp__cleancodermcp__query(
    query_text="[dein Fokus]",
    collection="i_knowledge_{FEATURE_ID}",
    limit=3
  )
  {FEATURE_ID} = sanitized Feature-Name (lowercase, underscores)
  Beispiel: "dcsre881" fuer DCSRE-881
  WICHTIG: Dieser Schritt ist NICHT optional. Fehlende Query = Wissens-Verlust (W173).
  PFLICHT: Im exit_report MUSS query_status gesetzt werden (I-05b):
    query_status: "executed"   # Query wurde ausgefuehrt (Normalfall)
    query_status: "skipped"    # Query bewusst ausgelassen (Begruendung erforderlich)
    query_status: "missing"    # Query vergessen / nicht ausfuehrbar

═══ ADR-KONTEXT (Optional) ═══

Falls vorhanden, lies .claude/analysis/synthese/{NAME}-HANDOFF.md Sektion 4 (Architektur-Entscheidungen).
Diese enthaelt Entscheidungen aus dem SC-Forschungszyklus die fuer deine Implementation relevant sein koennten.

Falls pipeline_mode=READY_FOR_I UND handoff_consumed=true im Manifest:
  → Nutze handoff_context.sections aus dem Manifest (strukturierter Extrakt):
    - handoff_context.sections.architectural_decisions: ADRs mit Rationale und W{n}-Bezug
    - handoff_context.sections.offene_aufgaben: Priorisierte offene Aufgaben aus SC
    - handoff_context.sections.discovery_summary: Topics mit unzureichender RAG-Abdeckung
    - handoff_context.sections.srs_trend: Stabilitaets-Verlauf (Kontext fuer Komplexitaets-Einschaetzung)
  → Diese Felder sind BEREITS STRUKTURIERT — kein manuelles Parsen von HANDOFF.md noetig.
  → Relevante ADRs und offene Aufgaben in deine Implementierungs-Entscheidungen einbeziehen.

Falls vorhanden, nutze handoff_context aus Manifest:
  handoff_context: "{HANDOFF_CONTEXT}"  ← vom Team Lead befuellt (Schritt 0.4g)
  Dieser Kontext fasst SRS-Trend, offene Gaps und ADR-Rationale aus dem SC-Zyklus zusammen.

═══ ARBEITSVERZEICHNIS ═══

Nutze fuer ALLE Datei-Operationen ABSOLUTE Pfade:
  {WORKTREE_PATH}/.claude/...
Beispiel: {WORKTREE_PATH}/.claude/analysis/synthese/ATOMIC-{SLICE}.md

═══ SCHRITTE ═══

1. Lies Command-Datei:
   {WORKTREE_PATH}/.claude/commands/_I_{COMMAND}.md
2. Fuehre Command aus (Batch-Modus).
   Falls BATCH_NUM > 1: Resume-Modus (lese bestehende Synthese-Datei
   und setze Arbeit ab next_item_index fort).
3. Schreibe exit_report Block in Synthese-Datei (PFLICHT, vor TaskUpdate).
   Falls findings nicht leer: APPEND an {WORKTREE_PATH}/.claude/analysis/_parking-lot.md
   exit_report MUSS query_status enthalten (I-05b):
     query_status: "executed" | "skipped" | "missing"  (Pflichtfeld, kein Default)
4. TaskUpdate {TASK_ID} status=completed
5. SendMessage an "team-lead":
   "{COMMAND} {SLICE} Batch {BATCH_NUM}: [partial|final]. block_reason={reason}. [2-3 Saetze Summary]"
   (block_reason leer lassen bei status=final)

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (kein Task-Tool vorhanden)
- NUR dieser eine Command, dann fertig (KEIN TaskList-Loop)
- ABSOLUTE Pfade fuer alles: {WORKTREE_PATH}/...
```

### Agent-Naming-Konvention

| Stufe | Agent-Name | Beispiel |
|-------|-----------|---------|
| cleanCodeSlice | `i-sc-{SLICE}-cleanCode-b1` | i-sc-S1_DBSchema-cleanCode-b1 |
| codeAtomic | `i-sc-{SLICE}-atomic-b{N}` | i-sc-S1_DBSchema-atomic-b2 |
| codeIntegration | `i-sc-{SLICE}-integration-b{N}` | i-sc-S2_S3Key-integration-b1 |
| codeSystem | `i-sc-{SLICE}-system-b{N}` | i-sc-S1_DBSchema-system-b1 |
| verify | `i-sc-{SLICE}-verify-b1` | i-sc-S2_S3Key-verify-b1 |

---

## PHASE 3: TEAM LEAD STEUERUNG

### Verantwortlichkeit

**TEAM LEAD (DU):** Orchestriert I-Pipeline via STUFEN-MODELL. Spawnt kurzlebige Agents pro Stufe, liest Manifest, managed State, Human-in-the-Loop.

**TUT:** Tasks erstellen, Agent-Messages lesen, HiL-Checkpoints einbauen, Manifest nach JEDER Stufe und jedem Batch-Zyklus persistieren, Resume-Tasks erstellen bei partial.

**NICHT:** Commands selbst ausfuehren, Code/Tests schreiben, Git-Commits, Merges.

### Stufen-Loop (Kern-Algorithmus)

Pro Welle und pro Batch-Command (codeAtomic, codeIntegration, codeSystem):

```
WHILE nicht_alle_slices_final:
  aktive_slices = [s fuer s in slices wenn nicht stufe_final[s]]
  batch_num = manifest.I_PIPELINE_STATE.resume_zaehler[slice][command] + 1

  # Spawn: 1 Agent pro aktivem Slice (alle gleichzeitig)
  FOR EACH slice IN aktive_slices:
    task_id = TaskCreate(
      subject: "[{slice}] {command} Batch {batch_num}",
      description: "[WORKER-MODE] {command} {slice} Batch {batch_num}
                    Worktree: {WORKTREE_PATH(slice)}"
    )
    Task(
      name: "i-sc-{slice}-{command}-b{batch_num}",
      team: "i-pipeline-{NAME}",
      model: "sonnet",
      prompt: KURZLEBIG_PROMPT(slice, command, batch_num, task_id)
    )

  # Warten bis alle Agents completed (via SendMessage + TaskList-Check)
  warte_bis_alle_completed(aktive_slices, command, batch_num)

  # Query-Guard-Check (I-14): Pruefe query_status im exit_report aller Agents
  query_guard_warnings = manifest.I_PIPELINE_STATE.get("query_guard_warnings", 0)
  FOR EACH slice IN aktive_slices:
    exit_report = lese_exit_report(slice, command)
    IF exit_report.query_status == "executed":
      PASS  # Normalfall, kein Eintrag noetig
    ELIF exit_report.query_status == "skipped":
      logge_manifest_warnung(slice, command, "query_status=skipped (I-14 soft-warning)")
    ELSE:  # "missing" oder Feld fehlt
      query_guard_warnings += 1
      manifest.I_PIPELINE_STATE.query_guard_warnings = query_guard_warnings
      logge_manifest_warnung(slice, command, "query_status=missing (I-14 guard)")
      agents_mit_missing = query_guard_warnings
      agents_gesamt = len(aktive_slices) * batch_num
      IF agents_gesamt > 0 AND agents_mit_missing / agents_gesamt >= 0.5:
        AskUserQuestion("QUERY-GUARD HiL: >50% Agents haben query_status=missing. "
                        + "I-Knowledge-Konsumption ausgefallen? Fortfahren? (j/n)")
  manifest.I_PIPELINE_STATE.query_guard_warnings = query_guard_warnings

  # I→SC Rueckkehr-Trigger Check (EC-3, D6-D11)
  # Prueft ob Implementation auf fundamentale SC-Probleme gestossen ist

  FOR EACH slice IN aktive_slices:
    exit_report = lese_exit_report(slice, command)

    # T1: Inkompatibilitaet mit SC-Model
    t1_triggered = (exit_report.get("query_status") == "INCOMPATIBLE_WITH_SC_MODEL")

    # T2: Widerlegungsrate > 30%
    total_wn = len(manifest.get("w_register", {}))
    widerlegt_count = sum(1 fuer w in manifest.w_register.values()
                          wenn w.get("status") == "WIDERLEGT")
    t2_triggered = (total_wn > 0 AND widerlegt_count / total_wn > 0.30)

    # T3: Systemische Blockade (Mini-SC-Loop erschoepft)
    mini_sc_attempts = manifest.I_PIPELINE_STATE.get("mini_sc_attempts", {}).get(slice, 0)
    t3_triggered = (mini_sc_attempts >= 3 AND
                    exit_report.get("query_status") == "BLOCKED_SYSTEMIC")

    # T4: Spezifikations-Konflikte
    spec_conflicts_count = exit_report.get("spec_conflicts_count", 0)
    t4_triggered = (spec_conflicts_count > 2)

    any_trigger = t1_triggered OR t2_triggered OR t3_triggered OR t4_triggered

    IF any_trigger:
      # D7: i_sc_return Manifest-Struktur setzen
      i_sc_return = manifest.get("i_sc_return", {})
      i_sc_return.triggered = true
      i_sc_return.trigger_time = {jetzt ISO8601}
      i_sc_return.trigger_reason = "FULL_RETURN"
      i_sc_return.trigger_source = "query-guard-i14"

      i_sc_return.classification = {
        type: "FULL_RETURN",
        trigger_signals: {
          incompatible_with_sc_model: t1_triggered,
          assumptions_refuted_percent: round(widerlegt_count / max(total_wn, 1) * 100),
          mini_sc_attempts: mini_sc_attempts,
          spec_conflicts_count: spec_conflicts_count
        }
      }

      # D8: Widerlegte W{n} in refuted_wn[] schreiben
      i_sc_return.refuted_wn = [
        {
          wn_id: wn_id,
          title: wn_data.get("title", ""),
          contraevidence: wn_data.get("widerlegung_grund", ""),
          severity: "HIGH",
          recovery_priority: idx + 1
        }
        fuer idx, (wn_id, wn_data) in enumerate(
          manifest.w_register.items()
          wenn wn_data.get("status") == "WIDERLEGT"
        )
      ]

      # D9: sc_recommendations[] generieren (priorisiert nach Trigger)
      i_sc_return.sc_recommendations = []
      IF t1_triggered:
        i_sc_return.sc_recommendations.append({
          priority: 1,
          title: "SC-Model-Inkompatibilitaet klaeren",
          suggested_approach: "Widerlegte Annahmen neu evaluieren",
          affected_wn: [wn.wn_id fuer wn in i_sc_return.refuted_wn],
          effort_estimate: "1-2 Zyklen"
        })
      IF t2_triggered:
        i_sc_return.sc_recommendations.append({
          priority: 1 if NOT t1_triggered else 2,
          title: "Widerlegungsrate > 30% — Recovery-Fokus",
          suggested_approach: "w_focus_list aus refuted_wn[] ableiten",
          affected_wn: [wn.wn_id fuer wn in i_sc_return.refuted_wn],
          effort_estimate: "1-2 Zyklen"
        })
      IF t3_triggered:
        i_sc_return.sc_recommendations.append({
          priority: len(i_sc_return.sc_recommendations) + 1,
          title: "Systemische Blockade loesen (Mini-SC erschoepft)",
          suggested_approach: "Voller SC-Zyklus mit gerichteter Forschung",
          affected_wn: [],
          effort_estimate: "2+ Zyklen"
        })
      IF t4_triggered:
        i_sc_return.sc_recommendations.append({
          priority: len(i_sc_return.sc_recommendations) + 1,
          title: "Spezifikations-Konflikte ({spec_conflicts_count}) aufloesen",
          suggested_approach: "ADR-Review + SC-Neustrukturierung",
          affected_wn: [],
          effort_estimate: "1 Zyklus"
        })

      i_sc_return.recovery_status = "PENDING"
      i_sc_return.recovery_completion_percent = 0

      # D10: recovery_cycle_count pruefen (max 2)
      recovery_cycle_count = manifest.get("recovery_cycle_count", 0)
      IF recovery_cycle_count >= 2:
        AUSGABE: "WARNUNG: Max Recovery-Zyklen (2) erreicht. HiL-Intervention erforderlich."
        AskUserQuestion(
          "I→SC-Rueckkehr: Max. 2 Recovery-Zyklen erschoepft. " +
          "Optionen: (a) SC-Zyklus manuell starten, " +
          "(b) FORCE_ACCEPT (I-Pipeline fortsetzen auf eigenes Risiko), " +
          "(c) Projekt abbrechen"
        )

      # Manifest updaten
      manifest.i_sc_return = i_sc_return
      manifest.I_PIPELINE_STATE.pipeline_mode = "SC_RECOVERY"
      manifest.update()

      AUSGABE: "I→SC-RUECKKEHR AUSGELOEST: Trigger(s): " +
               "{[T1 wenn t1_triggered] + [T2 wenn t2_triggered] + [T3 wenn t3_triggered] + [T4 wenn t4_triggered]}"

      # D10 (Fortfuehrung): SC-Recovery-Pfad vorschlagen
      AUSGABE: "Empfehlung: /_SC_orchestrate {NAME} --mode=recovery"
      AUSGABE: "Recovery-Fokus: {[wn.wn_id fuer wn in i_sc_return.refuted_wn]}"
      AUSGABE: "recovery_cycle_count aktuell: {recovery_cycle_count} (Max: 2)"

      → I-Pipeline STOPP (HARD STOP — Recovery hat Vorrang)

  # Pruefe Synthese-Status pro Slice (File-basiert)
  FOR EACH slice IN aktive_slices:
    synthese = lese_synthese_datei(slice, command)
    IF synthese.status == 'final':
      stufe_final[slice] = True
      manifest.I_PIPELINE_STATE.worktrees[slice].{command}_status = 'final'
    ELSE:  # partial
      manifest.I_PIPELINE_STATE.resume_zaehler[slice][command] += 1
      manifest.I_PIPELINE_STATE.worktrees[slice].{command}_status = 'partial'
      IF manifest.I_PIPELINE_STATE.resume_zaehler[slice][command] >= 5:
        STOPP_STAGNATION(slice, command)

  # Manifest NACH JEDEM Batch-Zyklus updaten (compact-sicher!)
  manifest.update()
```

### Batch-Resume Handling

Nach JEDEM Stufen-Abschluss (alle Agents einer Stufe completed):

1. Team Lead liest Synthese-Dateien pro Slice (File-basiert, NICHT Kontext-basiert)
2. Falls `status: partial` fuer Slice: Resume-Zaehler im Manifest erhoehen + naechsten Batch spawnen
3. Falls `status: final` fuer Slice: Slice aus aktiver Liste entfernen
4. Falls ALLE Slices `final`: Stufe abgeschlossen → naechste Stufe

```
Manifest-Update (Pflicht nach jedem Batch-Zyklus):

I_PIPELINE_STATE:
  resume_zaehler:
    S1_DBSchema:
      codeAtomic: 2        # <- wird inkrementiert
    S2_S3Key:
      codeAtomic: 0
```

### Stagnation-Check (Manifest-basiert, /compact-sicher)

```
Stagnation-Erkennung:
  IF manifest.I_PIPELINE_STATE.resume_zaehler[slice][command] >= 5:
    → STOPP
    → AUSGABE: "Stagnation erkannt: {COMMAND} {SLICE} hat 5x status:partial geliefert."
    → AUSGABE: "Synthese-Datei: {WORKTREE_PATH}/.claude/analysis/synthese/{COMMAND}-{SLICE}.md"
    → AUSGABE: "Bitte Datei pruefen und dann Orchestrator neu starten."
```

**WICHTIG:** Zaehler liegt IMMER im Manifest (nie im Kontext). /compact verliert ihn NICHT.

---

## Schritt 0: Voraussetzungen + State-Init

### 0.1 Manifest lesen

```bash
# Lies Manifest
cat .claude/analysis/_manifest.md
```

**Prüfe:**
- **NAME:** Feature-Name (z.B. "DateiabholungAnalyse")
- **PHASE:** Sollte "pre-cycle" oder "model" sein (nicht mitten in Pipeline)
- **SYSTEM-MODEL:** opus/sonnet/haiku (bestimmt Agent-Modelle)
- **SCHWIERIGKEIT:** easy/normal/hard (bestimmt Agent-Anzahl)

**Falls PHASE = "I-Pipeline" UND Status ≠ "abgeschlossen":**
→ RESUME-Modus (später implementieren, Cycle 1 nur Fresh-Start)

### 0.2 Task.md + Model.md prüfen

```bash
# Prüfe Task.md existiert
test -f .claude/Task.md && echo "✅ Task.md vorhanden" || echo "❌ Task.md fehlt → STOPP"

# Prüfe Model.md existiert
test -f .claude/models/{NAME}_Model.md && echo "✅ Model vorhanden" || echo "❌ Model fehlt → STOPP"
```

**Falls Task.md oder Model FEHLT:**
→ AUSGABE: "Bitte zuerst /_taskDefinition und /_model ausführen"
→ STOPP

### 0.2a SC-Status prüfen (W93)

Falls ein SC-Zyklus vorausging: Lies `sc_status` aus `.claude/analysis/_manifest.md`.

| sc_status | Bedeutung | Aktion |
|-----------|-----------|--------|
| `DONE` | SC-Zyklus abgeschlossen ✅ | I-Pipeline startet normal |
| `DONE_DISCOVERY_ONLY` | Discovery fertig ✅ | I-Pipeline startet (kein SC-Review-Zyklus noetig) |
| `RUNNING` | SC laeuft noch ⚠️ | User fragen: "SC noch nicht abgeschlossen (sc_status=RUNNING). Sicher fortfahren?" |
| `BLOCKED` | SC blockiert ❌ | STOPP. SC-Zyklus zuerst abschliessen. |
| (kein sc_status) | Kein SC-Vorzyklus | Normal weiter, kein Check |

**Empfehlung bei sc_status=RUNNING:** AskUserQuestion statt hartem STOPP — User kann bewusst entscheiden.

### 0.2b pipeline_mode Pre-Check (EC-4, EC-5, W200)

Falls `pipeline_mode` im Manifest vorhanden: Pruefe auf Uebergangs-Bereitschaft.

| pipeline_mode | Bedeutung | Aktion |
|---------------|-----------|--------|
| `READY_FOR_I` | SC-Gate PASS + Finale Verifikation OK | I-Pipeline startet normal |
| `pending_approval` | TIER-1+2 OK, HiL-Signatur ausstehend | HiL-Warnung: Frage User ob Fortfahren |
| `POST_CYCLE` | SC-Phase laeuft noch (POST-CYCLE aktiv) | STOPP: "POST-CYCLE noch aktiv. Warten bis pipeline_mode=READY_FOR_I." |
| `POST_CYCLE_RETRY` | Gate FAIL — SC muss weiterlaufen | STOPP: "SC-Gate FAILED. Weitere SC-Zyklen erforderlich." |
| `SC_RECOVERY` | I→SC-Rueckkehr laeuft | STOPP: "SC-Recovery laeuft. Warten bis SC-Recovery abgeschlossen." |
| `SC` | SC noch aktiv | STOPP: "SC-Phase noch nicht abgeschlossen." |
| (kein pipeline_mode) | Kein SC-Vorzyklus oder altes Manifest | Graceful Degradation: Weiter (sc_status-Tabelle gilt) |

```
Auswertungslogik:

pm = manifest.get("pipeline_mode", None)

IF pm == "READY_FOR_I":
  # Normalfall — weiter
  i_gate_response.i_decision = "accept_start" (vorlaeufig, final nach Schritt 0.4)
  Logge: "pipeline_mode=READY_FOR_I bestaetigt. I-Pipeline berechtigt."

ELIF pm == "pending_approval":
  AskUserQuestion(
    "SC-Gate ausstehend (pipeline_mode=pending_approval). " +
    "TIER-3 HiL-Signatur noch nicht gesetzt. " +
    "Fortfahren? (j=Ja, n=STOPP)"
  )
  → j: weiter (User uebernimmt Verantwortung)
  → n: STOPP

ELIF pm IN ["POST_CYCLE", "POST_CYCLE_RETRY", "SC_RECOVERY", "SC"]:
  AUSGABE: "STOPP: pipeline_mode={pm}. I-Pipeline darf nicht starten."
  AUSGABE: "Warten bis SC-Phase abgeschlossen und pipeline_mode=READY_FOR_I."
  i_gate_response:
    i_decision: reject_needs_more_sc
    handoff_completeness: MISSING
    rejection_reason: "pipeline_mode={pm} — SC nicht abgeschlossen"
    approved_by: "i-orchestrate-agent"
    approved_at: {jetzt ISO8601}
  → Manifest updaten + HARD STOP

ELIF pm IS None:
  Logge: "pipeline_mode nicht im Manifest — Graceful Degradation (kein SC-Vorzyklus)."
  # Kein Hard-Stop, sc_status-Pruefung (0.2a) gilt als alleinige Absicherung
```

Schreibe nach Pre-Check in Manifest (bei READY_FOR_I oder None/Graceful):
  pipeline_mode: I_RUNNING
  i_gate_response: ACKNOWLEDGED  (bestaetigt sc_i_gate aus SC-Zyklus)

### 0.3 Welle-0: Entity-Readiness-Check (W97, OP-5)

**ZWECK:** Verhindert vollstaendige Pipeline-Abbrueche durch fehlende Entities.
DCSRE-93 I-Pipeline v1: 100% Artefakte verschwendet weil VersorgungsvertragEntity.cs
aus DCSRE-1212 noch nicht existierte. Ein 2-3 Min haiku-Check haette das verhindert.

**WANN:** VOR Pipeline-Start, NACH Model+Task-Pruefung (Schritt 0.2).

**AKTION:**

```
Team Lead spawnt 1 haiku-Agent (sc-entity-check):

Du bist ein Entity-Readiness-Checker.

═══ DEIN AUFTRAG ═══

Pruefe ob alle Entities aus dem ARCHITECT-Scope im Code existieren.

═══ SCHRITTE ═══

1. Lies .claude/models/{NAME}_Model.md
   → Extrahiere alle referenzierten Entities (Klassen, Dateien, DB-Tabellen)
2. Lies .claude/Task.md
   → Extrahiere Scope-Dateien und Abhaengigkeiten
3. Pruefe fuer JEDE referenzierte Entity:
   a) Existiert die Datei? (Glob-Suche)
   b) Ist die Klasse compilierbar? (Grundstruktur vorhanden)
   c) Sind referenzierte Navigation-Properties vorhanden?
4. Erstelle Entity-Readiness-Report

═══ OUTPUT FORMAT ═══

CLEAR:   Alle Entities vorhanden → Pipeline kann starten
BLOCKED: {N} Entities fehlen → Liste mit Blockern

Sende Ergebnis an Team Lead.
```

**Auswertung durch Team Lead:**

```
Falls CLEAR:
  → Weiter mit Schritt 0.5 (Manifest initialisieren)
  → Manifest: entity_readiness=CLEAR

Falls BLOCKED:
  → STOPP mit konkretem Blocker-Bericht:

  ╔══════════════════════════════════════════════════════════════╗
  ║  ENTITY-READINESS: BLOCKED                                  ║
  ╠══════════════════════════════════════════════════════════════╣
  ║  Fehlende Entities:                                         ║
  ║  1. {EntityName} - {Grund} (z.B. "Datei existiert nicht")  ║
  ║  2. {EntityName} - {Grund}                                  ║
  ║                                                              ║
  ║  Empfehlung: Fehlende Entities zuerst erstellen/mergen.    ║
  ║  Pipeline-Start ERST wenn alle Entities vorhanden.          ║
  ╚══════════════════════════════════════════════════════════════╝

  → AskUserQuestion:
    "Entity-Readiness-Check FEHLGESCHLAGEN. {N} Entities fehlen:
     {blocker_liste}
     Optionen:
     A) WARTEN  → Pipeline stoppt. Entity zuerst erstellen/mergen, dann neu starten.
     B) SCOPE-AENDERN → Entity aus Scope entfernen, Pipeline mit reduziertem Scope starten.
     C) FORCE   → Auf eigenes Risiko starten. Manifest: entity_readiness=OVERRIDE"
```

### 0.4 HANDOFF-Konsumption (EC-6, W181, W180-D)

**ZWECK:** Explizite Konsumption des HANDOFF.md aus dem SC-Zyklus. Verhindert W181 (informeller Zugang) und W180-D (Konsumptions-Luecke). Stellt sicher dass alle Worker denselben strukturierten Kontext erhalten.

**WANN:** Nach Schritt 0.3 (Entity-Check CLEAR), VOR Schritt 0.5 (Manifest-Init).

**0.4a: HANDOFF.md vorhanden?**

```
handoff_path = ".claude/analysis/synthese/{NAME}-HANDOFF.md"

Falls NICHT vorhanden:
  → Logge: "HANDOFF.md nicht gefunden — HANDOFF-Konsumption SKIP."
  → handoff_consumed = false
  → Warnung in Manifest: handoff_warning = "HANDOFF.md nicht vorhanden (kein SC-Vorzyklus?)"
  → Weiter mit Schritt 0.5 (keine Blockierung — optional)
```

**0.4b: HANDOFF.md lesen**

```
Lies HANDOFF.md komplett:
  → YAML-Frontmatter (Version, Datum, Ersteller)
  → Markdown-Sektionen 1-8:
    Pflicht (4): [LOESCHEN], [BEHALTEN], [OFFENE AUFGABEN], [ARCHITEKTUR]
    Optional-Erwartet (4): [KRITISCHE HINWEISE], [SRS-TREND], [DISCOVERY-GAPS], [ADR-RATIONALE]
```

**0.4c: Pflicht-Sektionen pruefen**

```
pflicht_sektionen = ["[LOESCHEN]", "[BEHALTEN]", "[OFFENE AUFGABEN]", "[ARCHITEKTUR]"]
fehlende = [s fuer s in pflicht_sektionen wenn s NICHT in HANDOFF.md]

Falls fehlende nicht leer:
  i_gate_response:
    i_decision: reject_needs_more_sc
    handoff_completeness: MISSING
    rejection_reason: "Pflicht-Sektionen fehlen: {fehlende}"
    approved_by: "i-orchestrate-agent"
    approved_at: {jetzt ISO8601}
  Manifest updaten
  AUSGABE: "HANDOFF-Konsumption FEHLGESCHLAGEN: Pflicht-Sektionen fehlen: {fehlende}"
  AUSGABE: "SC-Phase muss HANDOFF.md vervollstaendigen. I-Pipeline STOPP."
  → HARD STOP
```

**0.4d: Strukturierte Daten extrahieren**

```
handoff_context = {
  source_file: handoff_path,
  extracted_at: {jetzt ISO8601},
  sections: {
    loeschen:               extrahiere_sektion("[LOESCHEN]"),
    behalten:               extrahiere_sektion("[BEHALTEN]"),
    offene_aufgaben:        extrahiere_offene_aufgaben("[OFFENE AUFGABEN]"),
    architektur_constraints: extrahiere_liste("[ARCHITEKTUR]"),
    kritische_hinweise:     extrahiere_sektion("[KRITISCHE HINWEISE]") oder null,
    srs_trend:              extrahiere_srs_tabelle("[SRS-TREND]") oder null,
    discovery_summary:      extrahiere_tabelle("[DISCOVERY-GAPS]") oder null,
    architectural_decisions: extrahiere_tabelle("[ADR-RATIONALE]") oder null
  }
}
```

**0.4e: handoff_context im Manifest speichern**

```
Schreibe ins Manifest:
  handoff_context: {handoff_context}
```

**0.4f: Konsumptions-Flags setzen**

```
Schreibe ins Manifest:
  handoff_consumed: true
  handoff_consumed_at: {jetzt ISO8601}
  handoff_consumed_by: "i-orchestrate-agent"

  i_gate_response:
    i_decision: accept_start
    handoff_completeness: OK
    approved_by: "i-orchestrate-agent"
    approved_at: {jetzt ISO8601}
    rejection_reason: null
```

**0.4g: handoff_context an KURZLEBIG_PROMPT uebergeben**

```
KURZLEBIG_PROMPT-Erweiterung:
  Der handoff_context (ADRs, offene Aufgaben, Discovery-Gaps) wird als
  KONTEXT-Block in KURZLEBIG_PROMPT der Worker eingefuegt (siehe Phase 2
  ADR-KONTEXT Sektion — bereits vorhanden, wird um handoff_context-Felder ergaenzt).
```

**Logging:**
```
Logge: "HANDOFF-Konsumption erfolgreich: {n} offene Aufgaben, {m} ADRs, srs_trend: {interpretation}"
```

### 0.5 Manifest auf I-Pipeline initialisieren

Fuege I_PIPELINE_STATE in das YAML-Frontmatter von `_manifest.md` ein
(persistent, /compact-sicher). Initial-Zustand (vor Slice-Erkennung):

```yaml
# In _manifest.md YAML-Frontmatter hinzufuegen:

I_PIPELINE_STATE:
  start: "{YYYY-MM-DD HH:MM}"
  welle: 0
  aktuelle_stufe: cleanCodeArchitect
  stufen_status:
    cleanCodeSlice: pending
    codeAtomic: pending
    codeIntegration: pending
    codeSystem: pending
    verify: pending
    fanIn: pending
  resume_zaehler: {}
  worktrees: {}
  aktive_agent_ids: []
  hil:
    test_suite: PENDING
    commits: PENDING
```

**AUSGABE:**
```
═══════════════════════════════════════════════════════════
I-Pipeline Orchestrator v2.0 (WellenRedesign)
Feature: {NAME}
Schwierigkeit: {SYSTEM-MODEL} / {DIFFICULTY}
═══════════════════════════════════════════════════════════

Manifest initialisiert: I_PIPELINE_STATE
Starte Pipeline via Stufen-Modell (Option 3)...
```

---

## Schritt 1: cleanCodeArchitect (Slices definieren)

### 1.1 Command aufrufen

```bash
# Rufe cleanCodeArchitect auf
/_I_cleanCodeArchitect {NAME}
```

**Wartet auf Command-Completion.**

### 1.2 ARCHITECT.md lesen

```bash
# Prüfe ARCHITECT.md existiert
test -f .claude/analysis/synthese/{NAME}-ARCHITECT.md && echo "✅ ARCHITECT.md vorhanden" || echo "❌ ARCHITECT.md fehlt → STOPP"

# Lies ARCHITECT.md
cat .claude/analysis/synthese/{NAME}-ARCHITECT.md
```

**Extrahiere:**
1. **Slice-Liste:** Welche Slices gibt es? (z.B. S1_DBSchema, S2_S3Key, S3_Retry)
2. **Dependency-Graph:** Welche Slices haben Abhängigkeiten?
3. **Wellen:** Welle 1 = Slices OHNE Abhängigkeiten, Welle 2+ = Slices MIT Abhängigkeiten

**Beispiel:**
```markdown
## Dependency-Graph

| Slice | Welle | Abhängigkeit |
|-------|-------|--------------|
| S1_DBSchema | 1 | - |
| S2_S3Key | 1 | - |
| S3_Retry | 2 | braucht S1 |
```

**AUSGABE:**
```
✅ ARCHITECT.md erstellt
   Slices gefunden: 3 (S1_DBSchema, S2_S3Key, S3_Retry)
   Welle 1: 2 Slices (S1, S2)
   Welle 2: 1 Slice (S3)
```

### 1.3 Manifest Update

```markdown
## I-Pipeline Status

**PHASE:** cleanCodeArchitect → mitose
**SLICES:** 3 (2× Welle 1, 1× Welle 2)
**WELLE:** 1 (Vorbereitung)
```

---

## Schritt 2: Entscheidung - Single Slice vs Multi-Worktree

### 2.1 Slice-Anzahl prüfen

**Falls Welle 1 hat NUR 1 Slice:**
→ **SINGLE-SLICE-Modus** (SKIP mitose/fanOut/fanIn)
→ Springe zu Schritt 4 (cleanCodeSlice, direkt im Mothership)

**Falls Welle 1 hat >1 Slice:**
→ **MULTI-WORKTREE-Modus** (mitose → fanOut → Pro-Worktree-Agents)
→ Weiter mit Schritt 3

**AUSGABE (Multi-Worktree):**
```
⚙️ Multi-Worktree-Modus (2 Slices in Welle 1)
   → Starte Mitose + FanOut
```

**AUSGABE (Single-Slice):**
```
⚙️ Single-Slice-Modus (nur 1 Slice)
   → SKIP Mitose/FanOut, arbeite direkt im Mothership
```

---

## Schritt 3: Mitose + FanOut (nur bei Multi-Worktree)

### 3.1 Mitose (Git Worktrees + Branches erstellen)

```bash
# Extrahiere Feature-Prefix aus Branch-Name
CURRENT_BRANCH=$(git branch --show-current)
FEATURE_PREFIX=$(echo "$CURRENT_BRANCH" | sed 's|^feature/||')

# Rufe mitose auf (nur Welle 1)
/_I_mitose "$FEATURE_PREFIX"
```

**Wartet auf mitose-Completion.**

**Erwartetes Ergebnis:**
- N Worktrees erstellt (1 pro Welle 1 Slice)
- N Feature-Branches erstellt (feature/{PREFIX}_{SLICE})
- Worktree-Pfade: `../{REPO}-{SLICE}/`

**AUSGABE:**
```
✅ Mitose abgeschlossen
   Worktrees erstellt: 2
   - S1_DBSchema: C:\...\DCSRE-881-S1_DBSchema
   - S2_S3Key: C:\...\DCSRE-881-S2_S3Key
```

### 3.2 FanOut (.claude/ verteilen)

```bash
# Rufe fanOut auf
/_I_fanOut
```

**Wartet auf fanOut-Completion.**

**Erwartetes Ergebnis:**
- .claude/ in jeden Worktree kopiert
- CURRENT_SLICE.md pro Worktree gesetzt
- Mothership Manifest mit FanOut-Status updated

**AUSGABE:**
```
✅ FanOut abgeschlossen
   .claude/ verteilt in 2 Worktrees
   CURRENT_SLICE.md gesetzt pro Worktree
```

### 3.3 Manifest Update

Schreibe YAML-Frontmatter-Erweiterung in `_manifest.md`:

```yaml
# Erweiterung des _manifest.md YAML-Frontmatter (persistent, /compact-sicher):

I_PIPELINE_STATE:
  welle: 1
  aktuelle_stufe: cleanCodeSlice
  stufen_status:
    cleanCodeSlice: in_progress
    codeAtomic: pending
    codeIntegration: pending
    codeSystem: pending
    verify: pending
    fanIn: pending
  resume_zaehler:
    S1_DBSchema:
      codeAtomic: 0
      codeIntegration: 0
      codeSystem: 0
    S2_S3Key:
      codeAtomic: 0
      codeIntegration: 0
      codeSystem: 0
  worktrees:
    S1_DBSchema:
      pfad: "C:\\...\\DCSRE-881-S1_DBSchema"
      cleanCode_status: pending
      atomic_status: pending
      integration_status: pending
      system_status: pending
      verify_status: pending
      fanIn_status: pending
      blocker: ""              # Aktueller Blocker (aus exit_report.block_reason)
      findings: []             # Gesammelte Findings (aus exit_report.findings)
    S2_S3Key:
      pfad: "C:\\...\\DCSRE-881-S2_S3Key"
      cleanCode_status: pending
      atomic_status: pending
      integration_status: pending
      system_status: pending
      verify_status: pending
      fanIn_status: pending
      blocker: ""              # Aktueller Blocker (aus exit_report.block_reason)
      findings: []             # Gesammelte Findings (aus exit_report.findings)
  aktive_agent_ids:
    - "i-sc-S1_DBSchema-cleanCode-b1"
    - "i-sc-S2_S3Key-cleanCode-b1"
  hil:
    test_suite: PENDING
    commits: PENDING
```

**AUSGABE:**
```
Manifest initialisiert: I_PIPELINE_STATE
Worktrees registriert: 2 (S1_DBSchema, S2_S3Key)
Aktuelle Stufe: cleanCodeSlice
```

---

## Schritt 4: Worker begleiten (Team Lead Monitoring)

### 4.1 Stufen-Steuerung durch Team Lead

Team Lead steuert STUFEN - nicht langlebige Worker. Pro Stufe:

1. Team Lead erstellt N Tasks (1 pro aktivem Slice)
2. Team Lead spawnt N kurzlebige Agents (alle gleichzeitig)
3. Team Lead wartet auf SendMessages von allen Agents
4. Nach allen Agents: Manifest aktualisieren, naechste Stufe oder Batch-Resume

**Team Lead reagiert auf Agent-Messages:**
- **"final"** → Slice abgeschlossen fuer diese Stufe
- **"partial"** → Resume noetig: resume_zaehler inkrementieren, neuen Batch spawnen
- Kein Message nach >30 Min: TaskList pruefen, Status-Query senden

### 4.2 Manifest Update (nach JEDER Stufe UND nach JEDEM Batch-Zyklus)

```yaml
# Nach cleanCodeSlice-Stufe:
I_PIPELINE_STATE:
  aktuelle_stufe: codeAtomic
  stufen_status:
    cleanCodeSlice: done
    codeAtomic: in_progress

# Worktree-Status aktualisieren:
  worktrees:
    S1_DBSchema:
      cleanCode_status: final
    S2_S3Key:
      cleanCode_status: final
```

**PFLICHT:** Manifest SOFORT nach Stufen-/Batch-Abschluss persistieren (Write-Tool).
/compact darf keinen State-Verlust verursachen.

### 4.3 Multi-Worktree: Stufen-basiertes Monitoring (Manifest-basiert)

Bei Multi-Worktree arbeiten alle Slices EINER STUFE gleichzeitig (parallel).
Team Lead monitort ALLE Agents via SendMessage + Manifest (nicht via Kontext).

```
STUFEN-MONITORING LOOP (compact-sicher):

Fuer jede Stufe (cleanCodeSlice, codeAtomic, codeIntegration, codeSystem, verify):

  WHILE aktive_slices nicht leer:
    # Warten auf Agent-Messages
    empfange SendMessages von Agents

    Pro eingehender Message von "i-sc-{SLICE}-{CMD}-b{N}":
      1. Extrahiere: slice, command, batch_num, status (partial|final)
      2. Lese Synthese-Datei (File-basiert, nicht nur Message):
         {WORKTREE_PATH}/.claude/analysis/synthese/{CMD}-{SLICE}.md
      3. Falls status final:
         - Manifest: worktrees[slice].{cmd}_status = 'final'
         - Entferne slice aus aktive_slices
      4. Falls status partial:
         - Manifest: resume_zaehler[slice][cmd] inkrementieren
         - Falls zaehler >= 5: STOPP_STAGNATION
         - Sonst: neuen Batch-Task erstellen + Agent spawnen (naechste Iteration)
      5. Manifest SOFORT persistieren (Write-Tool)

    # Timeout-Check (Manifest-basiert)
    Falls aktive_agent in manifest.aktive_agent_ids seit >30 Min kein Message:
      → TaskList pruefen ob Task noch in_progress
      → Falls ja: Status-Query senden
      → Falls Task unexpectedly completed: Manifest korrigieren

  # Stufe abgeschlossen
  manifest.I_PIPELINE_STATE.stufen_status[stufe] = 'done'
  manifest.I_PIPELINE_STATE.aktuelle_stufe = naechste_stufe
  manifest.update()
```

**WICHTIG:** Nach /compact liest Team Lead `_manifest.md` → weiss genau welche Agents noch aktiv, welche Stufe laeuft, welche Resume-Zaehler aktuell sind.

---

## Schritt 5: Checkpoint 1 - Human-in-the-Loop (Commits)

### 5.1 STOPP vor fanIn

**AUSGABE:**
```
═══════════════════════════════════════════════════════════
⏸️  CHECKPOINT 1: GIT-COMMITS
═══════════════════════════════════════════════════════════

Alle Worktrees haben ihre Arbeit abgeschlossen.
ABER: Agents dürfen NICHT committen!

Bitte committe MANUELL in ALLEN Worktrees:

1. cd C:\...\DCSRE-881-S1_DBSchema
   git add .
   git commit -m "Slice S1_DBSchema: ..."

2. cd C:\...\DCSRE-881-S2_S3Key
   git add .
   git commit -m "Slice S2_S3Key: ..."

Wenn alle Commits done: Antworte "Commits done"
═══════════════════════════════════════════════════════════
```

### 5.2 Warte auf User-Bestätigung

```
Warte auf User-Input: "Commits done" oder "Commits FAIL"

Falls User "Commits done":
  → Manifest Update: Commits = DONE
  → Weiter mit Schritt 6 (fanIn)

Falls User "Commits FAIL":
  → STOPP
  → AUSGABE: "Commit-Problem. Bitte fixen, dann Orchestrator neu starten."
```

### 5.3 Manifest Update

```markdown
**HUMAN-IN-THE-LOOP:**
- Commits: ✅ DONE ({YYYY-MM-DD HH:MM})
- Test-Suite: ✅ DONE (alle Worktrees)
```

---

## Schritt 6: fanIn (Ergebnisse einsammeln)

### 6.1 fanIn aufrufen

```bash
# Pro Slice: fanIn
/_I_fanIn S1_DBSchema
/_I_fanIn S2_S3Key
```

**Wartet auf fanIn-Completion pro Slice.**

**Erwartetes Ergebnis:**
- .claude/ Artefakte von Worktree → Mothership kopiert
- User merged (Advisory, fanIn macht KEIN git merge)
- Manifest mit Merge-Status updated

**AUSGABE:**
```
✅ fanIn S1_DBSchema abgeschlossen
   .claude/ Artefakte kopiert
   User merged: branch feature/DCSRE-881_S1_DBSchema
   Build: OK, Tests: OK

✅ fanIn S2_S3Key abgeschlossen
   .claude/ Artefakte kopiert
   User merged: branch feature/DCSRE-881_S2_S3Key
   Build: OK, Tests: OK
```

### 6.2 Agents shutdownen

```
Pro Worktree-Agent:
  SendMessage(
    type: "shutdown_request",
    recipient: "worktree-agent-{SLICE}",
    content: "Slice {SLICE_NAME} abgeschlossen, fanIn erfolgreich. Worktree nicht mehr benötigt."
  )
```

**AUSGABE:**
```
✅ Worktree-Agents shutdownen
   worktree-agent-S1: shutdown requested
   worktree-agent-S2: shutdown requested
```

### 6.3 Manifest Update

```markdown
**PHASE:** fanIn → welle2-check
**WELLE:** 1 (abgeschlossen)
```

---

## Schritt 7: Wellen-Iteration prüfen

### 7.1 ARCHITECT.md re-lesen

```bash
# Lies ARCHITECT.md Dependency-Graph
cat .claude/analysis/synthese/{NAME}-ARCHITECT.md | grep "Welle 2"
```

**Prüfe:** Gibt es Welle 2+ Slices?

**Falls JA:**
→ **Welle 2 existiert**
→ AUSGABE: "Welle 1 abgeschlossen. Welle 2 hat 1 Slice (S3_Retry)."
→ **Springe zurück zu Schritt 3.1** (mitose für Welle 2, dann fanOut, Agents, fanIn)

**Falls NEIN:**
→ **Feature KOMPLETT** (alle Slices abgeschlossen)
→ Weiter mit Schritt 8 (verify global)

**AUSGABE (Welle 2 existiert):**
```
⚙️ Welle 1 abgeschlossen
   Welle 2 hat 1 Slice: S3_Retry (entblockt durch S1_DBSchema)

   Starte Welle 2: Mitose → FanOut → Agents → fanIn
```

**AUSGABE (Feature KOMPLETT):**
```
✅ Alle Wellen abgeschlossen
   Feature ist komplett (alle Slices fertig)

   Weiter mit: verify global → diffAudit → Refactoring-Checkpoint → Pre_PR
```

### 7.2 Manifest Update (Welle 2 Start ODER Feature KOMPLETT)

**Falls Welle 2:**
```markdown
**PHASE:** mitose (Welle 2)
**WELLE:** 2 (Vorbereitung)
**AKTIVE SLICES:** S3_Retry
```

**Falls Feature KOMPLETT:**
```markdown
**PHASE:** verify-global
**WELLE:** - (alle abgeschlossen)
**AKTIVE SLICES:** - (Feature komplett)
```

---

## Schritt 8: verify global (Feature-Gesamt-Verifikation)

### 8.1 verify global aufrufen

```bash
# Rufe verify global auf (im Mothership)
/_I_verify global
```

**Wartet auf verify-Completion.**

**Erwartetes Ergebnis:**
- VERIFY.md erstellt (nicht VERIFY-{SLICE}.md)
- SPEC ↔ Tests Mapping für GESAMTES Feature
- GAP-Test Report (was fehlt?)

**AUSGABE:**
```
✅ verify global abgeschlossen
   SPEC ↔ Tests: 95% Coverage
   GAP-Test: 5% (2 Specs ohne Tests)
```

### 8.2 Manifest Update

```markdown
**PHASE:** verify-global → diffAudit
```

---

## Schritt 9: diffAudit (Diff gegen develop)

### 9.1 diffAudit aufrufen

```bash
# Rufe diffAudit auf
/_I_diffAudit
```

**Wartet auf diffAudit-Completion.**

**Erwartetes Ergebnis:**
- DIFFAUDIT.md erstellt
- Jede Änderung gegen Model/Spec gerechtfertigt
- SPUR-1..7 Explorations-Reste erkannt
- Cleanup-Liste (falls nötig)

**AUSGABE:**
```
✅ diffAudit abgeschlossen
   Diff gegen develop: 131 Dateien
   SPUR-Check: 3 SPUR-Findings (auskommentierter Debug-Code)
   Cleanup: 3 Dateien
```

### 9.2 Manifest Update

```markdown
**PHASE:** diffAudit → refactoring-checkpoint
```

---

## Schritt 9a: Refactoring-Checkpoint (HiL)

**WANN:** Nach diffAudit abgeschlossen, vor Pre_PR
**WARUM:** DiffAudit identifiziert Probleme (SPUR-Findings, Cleanup-Liste). Pre_PR erwartet sauberen Code (9 Quality Gates). Der Refactoring-Checkpoint faengt Refactoring-Items ab, die NICHT im Spike gefixt werden sollen, und leitet sie in den Parking-Lot um. Dies verhindert Scope-Creep (ad-hoc Fixes waehrend des Spikes) und Informationsverlust (Findings ohne Parking-Lot-Eintrag).

### 9a.1 DiffAudit-Findings auswerten

```
# Lies das DiffAudit-Ergebnis (DIFFAUDIT.md im Worktree/Mothership)
# Kategorisiere Findings:
#   REFACTORING: Code-Smell, Naming, Struktur-Verbesserung (→ Parking-Lot)
#   CLEANUP:     Debug-Code, Kommentare, TODOs (→ Pre_PR fixbar)
#   SPUR:        Explorations-Reste (→ Pre_PR fixbar)
#
# Filter: Nur REFACTORING-Findings sind relevant fuer diesen Checkpoint.
# CLEANUP und SPUR werden von Pre_PR Quality Gates abgefangen.
```

### 9a.2 HiL: Refactoring-Items parken (Human-in-the-Loop)

**AUSGABE:**
```
═══════════════════════════════════════════════════════
REFACTORING-CHECKPOINT (nach diffAudit, vor Pre_PR)
═══════════════════════════════════════════════════════

DiffAudit hat {N} Findings mit Refactoring-Charakter identifiziert:

{Tabellarische Auflistung der REFACTORING-Findings:}
| # | Datei | Finding | Typ |
|---|-------|---------|-----|
| 1 | {Pfad} | {Beschreibung} | REFACTORING |
| ... | ... | ... | ... |

Diese Items sollten NICHT waehrend des Spikes gefixt werden
(Scope-Creep-Risiko), sondern in den Parking-Lot eingetragen werden.

Optionen:
  [1] Alle Items in Parking-Lot eintragen (EMPFOHLEN)
  [2] Einzelne Items auswaehlen
  [3] Keine Items parken — weiter zu Pre_PR
═══════════════════════════════════════════════════════
```

**HiL-Aktion:**
```
# User waehlt Option:
#   [1] → ALLE Refactoring-Findings als Items in _parking-lot.md APPEND
#   [2] → User waehlt einzelne Findings → ausgewaehlte in _parking-lot.md APPEND
#   [3] → Keine Items geparkt. Weiter zu Pre_PR.
#
# Parking-Lot-Format pro Item:
#   - [ ] [REFACTORING] {Finding-Beschreibung} (Quelle: diffAudit, {Datei}:{Zeile})
#
# Ziel-Datei: .claude/analysis/_parking-lot.md
```

### 9a.3 Falls KEINE Refactoring-Findings

Falls diffAudit keine Findings mit Refactoring-Charakter liefert:
```
Kein Refactoring-Checkpoint noetig (0 Refactoring-Findings).
Weiter mit Pre_PR.
```
→ Direkt zu Schritt 10 (Pre_PR). Kein HiL erforderlich.

### 9a.4 Manifest Update

```markdown
**PHASE:** refactoring-checkpoint → Pre_PR
**REFACTORING_CHECKPOINT:** {N} Items geparkt | 0 Findings | SKIPPED ({YYYY-MM-DD HH:MM})
```

---

## Schritt 10: Pre_PR (9 Quality Gates)

### 10.1 Pre_PR aufrufen

```bash
# Rufe Pre_PR auf
/_Pre_PR
```

**Wartet auf Pre_PR-Completion.**

**Erwartetes Ergebnis:**
- 9 Gates geprüft (Tests, Naming, Cleanup, Doku, Konstanten, Logging, Architektur, Analyzer, Migration)
- Pro Gate: PASS/FAIL + Report
- Falls ALLE PASS: Feature bereit für PR
- Falls 1+ FAIL: Cleanup-Liste

**AUSGABE (ALL PASS):**
```
✅ Pre_PR abgeschlossen (ALL PASS)

   ═══════════════════════════════════════════════════════
   FEATURE BEREIT FÜR PR
   ═══════════════════════════════════════════════════════

   Alle 9 Quality Gates: PASS
   Feature: {NAME}
   Slices: {N}
   Tests: {M} Unit + {K} Integration + {L} System

   Nächster Schritt: PR erstellen
   ═══════════════════════════════════════════════════════
```

**AUSGABE (1+ FAIL):**
```
⚠️ Pre_PR abgeschlossen (FAIL)

   ═══════════════════════════════════════════════════════
   QUALITY GATES FAILED
   ═══════════════════════════════════════════════════════

   FAIL-Gates: 2
   - Gate 3 (Cleanup): 3 Dateien mit Debug-Code
   - Gate 5 (Konstanten): 5 Magic Numbers

   Bitte fixen, dann:
   /_Pre_PR_orchestrate (Re-Run)

   (Re-Run prüft nur FAIL-Gates, nicht alle)
   ═══════════════════════════════════════════════════════
```

### 10.2 Falls Pre_PR FAIL: User muss fixen

**STOPP:**
- Orchestrator stoppt NICHT automatisch
- User fixt FAIL-Gates
- User ruft `/_Pre_PR_orchestrate (Re-Run)` auf
- Orchestrator wartet auf User-Meldung: "Pre_PR PASS"

### 10.3 Manifest Update (FINAL)

```markdown
**PHASE:** Pre_PR → FEATURE DONE
**STATUS:** ✅ BEREIT FÜR PR
**PRE_PR:** ALL PASS ({YYYY-MM-DD HH:MM})
```

---

## Schritt 10a: Debloat-Check (EC-F Hook)

**WANN:** Nach codeSystem-Stufe abgeschlossen (alle Slices system_status=final), vor Checkpoint 1 (Commits)
**WARUM:** Model waechst waehrend Implementation — fruehzeitiger Check verhindert Bloat

```
# Debloat-Check (EC-F Hook)
Falls Model > 500 Zeilen nach codeSystem-Stufe:
  → Team Lead schlaegt /_D_orchestrate {NAME} vor
  → User kann annehmen oder ueberspringen (Human-in-the-Loop)
  → Falls angenommen: /_D_orchestrate {NAME} ausfuehren, dann weiter mit Checkpoint
  → Falls uebersprungen: Hinweis in _parking-lot.md, weiter mit Checkpoint

# Nach /_W_push_orchestrate (Post-Pipeline): Falls Model ausgeartet → /_D_orchestrate {NAME}
```

**MANIFEST-UPDATE:**
```markdown
**DEBLOAT_CHECK:** {SKIPPED|TRIGGERED} ({YYYY-MM-DD HH:MM})
```

---

## Schritt 11: Post-Pipeline Wissens-Push (via /_W_push_orchestrate)

**WANN:** Nach Pre_PR PASS, vor Final Summary
**WARUM:** Synchronisiert implementiertes Feature-Wissen zurueck (RAG + Vault + Retrospektive)

**AKTION:**
```
TaskCreate:
  subject: "Wissens-Push orchestrieren"
  description: |
    Post-Pipeline Wissens-Push (via /_W_push_orchestrate).
    Feature-Implementation abgeschlossen — Wissen sichern.
    Ausfuehrung: /_W_push_orchestrate {NAME} normal {ceiling} {floor}
    Handhabt intern: model finish → gap → push_global →
      modelSplit → sync_orchestrate hard --co-work → retrospektive.
    (sync_orchestrate ersetzt obsidianSync-Direktaufruf, mit Co-Working-Links)
```

**CONSTRAINT:** Ceiling-Vererbung — Schwierigkeit = min(Pipeline-Ceiling, normal). Blockiert NICHT die Pipeline (parallel erlaubt, aber vor PR empfohlen).

**MANIFEST-UPDATE:**
```markdown
**W_PUSH_ORCHESTRATE:** normal ({YYYY-MM-DD HH:MM})
```

---

## Schritt 12: Feature finalisieren (via /_finish)

**WANN:** Nach W_push_orchestrate abgeschlossen, vor Final Summary
**WARUM:** Offene Items pruefen, Parking-Lot abarbeiten, Manifest auf READY setzen

**AKTION:**
```
TaskCreate:
  subject: "Feature finalisieren"
  description: |
    /_finish {NAME} ausfuehren.
    Offene Items pruefen (parking-lot, Task.md, Model W{n}).
    User fragt: PARKEN / DISCARD / ERLEDIGT.
    .claude/* Konsistenz-Check.
    Manifest: PHASE=READY.
  blocked_by: (W_push_orchestrate Task)
```

**MANIFEST-UPDATE:**
```markdown
**PHASE:** READY
**DONE_TIMESTAMP:** {YYYY-MM-DD HH:MM}
```

---

## Schritt 13: Final Summary

**AUSGABE:**
```
═══════════════════════════════════════════════════════════
✅ I-PIPELINE ORCHESTRATION ABGESCHLOSSEN
═══════════════════════════════════════════════════════════

Feature: {NAME}
Pipeline-Dauer: {HH:MM:SS}
Commands ausgeführt: 13
Slices: {N}
Wellen: {M}
Tests: {X} Unit + {Y} Integration + {Z} System
Human-in-the-Loop: 2× (Commits + Test-Suite × N Slices)

Pipeline-Verlauf:
1. ✅ cleanCodeArchitect
2. ✅ mitose (Welle 1)
3. ✅ fanOut
4. ✅ cleanCodeSlice × {N}
5. ✅ codeAtomic × {N} (Batch-Resume)
6. ✅ codeIntegration × {N} (Batch-Resume)
7. ✅ codeSystem × {N} (Batch-Resume)
8. ✅ verify × {N}
9. ✅ fanIn × {N}
[10. ✅ mitose (Welle 2) - falls vorhanden]
11. ✅ verify global
12. ✅ diffAudit
12a. ✅ Refactoring-Checkpoint ({N} Items geparkt | 0 Findings)
13. ✅ Pre_PR (ALL PASS)
14. ✅ W_push_orchestrate (normal, Post-Pipeline: model finish → gap → push_global → modelSplit → sync_orchestrate hard --co-work → retro)

Nächster Schritt: PR erstellen
═══════════════════════════════════════════════════════════
```

---

## Fehlerbehandlung

### Fehler 1: Command FAIL (z.B. cleanCodeArchitect)

**Ursache:** Command liefert FAIL-Status

**Lösung:**
1. AUSGABE: "Command {NAME} FAILED. Siehe Synthese-Datei für Details."
2. AUSGABE: "Fehler beheben, dann Orchestrator neu starten."
3. STOPP

### Fehler 2: Agent-Timeout (>30 Minuten keine Message)

**Ursache:** Agent sendet >30 Minuten keine Message

**Lösung:**
1. SendMessage(recipient="worktree-agent-{SLICE}", content="Status-Query: Bist du noch am Arbeiten?")
2. Warte 5 Minuten
3. Falls keine Antwort: AUSGABE: "Agent {NAME} Timeout. Bitte prüfen."
4. STOPP

### Fehler 3: Resume-Stagnation (5× status:partial)

**Ursache:** Batch-Command (codeAtomic/Integration/System) liefert 5× hintereinander `status: partial`

**Lösung:**
1. AUSGABE: "Stagnation erkannt bei {COMMAND} {SLICE}."
2. AUSGABE: "Command ist blockiert. Bitte prüfen: Ist Command festgefahren?"
3. AUSGABE: "Synthese-Datei: {PATH}"
4. STOPP

### Fehler 4: User reject (Test-Suite FAIL)

**Ursache:** User meldet "Tests FAIL" bei Checkpoint 2

**Lösung:**
1. AUSGABE: "Test-Suite FAIL für Slice {SLICE}."
2. AUSGABE: "Bitte Tests fixen, dann Orchestrator neu starten."
3. Manifest Update: Test-Suite = FAIL (Slice {SLICE})
4. STOPP

### Fehler 5: User reject (Commits FAIL)

**Ursache:** User meldet "Commits FAIL" bei Checkpoint 1

**Lösung:**
1. AUSGABE: "Commit-Problem. Bitte fixen (Konflikte? Merge-Error?)."
2. AUSGABE: "Wenn Commits OK: Orchestrator neu starten."
3. Manifest Update: Commits = FAIL
4. STOPP

### Fehler 6: Pre_PR FAIL (Quality Gates)

**Ursache:** Pre_PR liefert 1+ FAIL-Gates

**Lösung:**
1. AUSGABE: "Pre_PR FAIL. {N} Gates failed."
2. AUSGABE: "FAIL-Liste:"
3. Pro FAIL-Gate: AUSGABE: "  - Gate {N} ({NAME}): {REASON}"
4. AUSGABE: ""
5. AUSGABE: "Bitte fixen, dann: /_Pre_PR_orchestrate (Re-Run)"
6. PAUSE (nicht STOPP, User kann fixen + re-run)

---

## Qualitätskriterien

- ✅ Stufen-Modell: Team Lead steuert STUFEN (W7-compliant, Option 3)
- ✅ Kurzlebige Single-Command-Agents (kein langlebiger Worker-Loop)
- ✅ Kein Agent spawnt Sub-Agents (W7: Workers haben kein Task-Tool)
- ✅ Agent-Naming: i-sc-{SLICE}-{CMD}-b{N}
- ✅ Resume-Zaehler persistent im Manifest (nie im Kontext)
- ✅ Stagnation-Check Manifest-basiert (/compact-sicher)
- ✅ Manifest-Update nach JEDER Stufe UND nach jedem Batch-Zyklus
- ✅ Human-in-the-Loop an 2 Stellen (Test-Suite nach codeSystem, Commits nach verify)
- ✅ Wellen-Iteration (Welle 1 → fanIn → Welle 2 falls vorhanden)
- ✅ VERTRAG-Block vorhanden (LIEST/SCHREIBT/INVARIANTEN)
- ✅ Error-Handling fuer 6 Fehler-Faelle
- ✅ Final Summary mit Pipeline-Verlauf

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (Pre_PR PASS, Feature DONE):

```bash
# Windows:
powershell -Command "notify '{FEATURE} /_I_orchestrate abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
