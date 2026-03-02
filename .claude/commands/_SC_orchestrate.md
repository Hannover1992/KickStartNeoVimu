# /_SC_orchestrate - Team Lead Forschungszyklus-Orchestrierung

```yaml
status: active
version: 2.1.0
created: 2026-02-15
updated: 2026-02-26
op: ScientificCycle
phase: Meta
type: orchestration
chain_position: meta
difficulty_scaling: true
team_based: true
changelog: |
  v1.0: Initialer Entwurf. Spiegelt /_WP_orchestrate v2.1 Struktur.
        1 Task = 1 Command. Team Lead + N Worker (Wellen-PARALLEL).
        PRE-CYCLE → SC-CYCLE ⟲ → POST-CYCLE → HiL.
        Integriert _W_fetch (Start), _W_push_temp (strategisch),
        _W_push_global + _W_obsidianSync + _W_modelSplit (Ende).
  v1.1: -I Flag (SC-Spec-Modus, OmniCommand EC-3).
        Default=THEORETISCH (skip _implement). -I=IMPLEMENT.
        Cold-Start T-1 Checkliste (EC-1).
        Decision-Tree SC/I/WP (EC-2).
        MODUS-Feld im Manifest.
  v2.0: KURZLEBIG_PROMPT Migration (Stateless Agents Redesign EC-A, EC-E).
        Persistenter Worker (sc-worker) eliminiert.
        PHASE 2: KURZLEBIG_PROMPT statt WORKER-PROMPT (37 LOC statt 98).
        PHASE 3: Aktives Spawning statt passives Monitoring.
        Agent-Naming: sc-{name}-{command} statt sc-worker.
        SC_PIPELINE_STATE Block im Manifest.
        Wellen-Phase und Sub-Commands UNVERAENDERT (bereits R-konform).
  v2.1: ImplementationHandOff (EC-2/OP-9) + Post-I Review-Modus (EC-7/E5).
        POST-CYCLE: HandOff-Dokument als Pflicht-Step vor W_push_orchestrate.
        --mode=review Flag: Post-I SC-Zyklen mit Gate 6, separater Protokoll-Pfad.
        Verhindert semantischen ModelBloat bei Post-Implementation-Quality-Review.
```

---

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_SC_orchestrate                                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    .claude/analysis/_manifest.md  (Startpunkt, NAME, Phase)         ║
║    .claude/Task.md                (Aufgabendefinition, optional)     ║
║    .claude/models/{NAME}_Model.md (existierendes Model, optional)    ║
║    .claude/pileOfMud/             (Rohmaterial, optional)            ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    .claude/analysis/_manifest.md  (nach jeder Welle aktualisieren)  ║
║    sc_status im Manifest (RUNNING/DONE/DONE_DISCOVERY_ONLY/BLOCKED) ║
║    (alle anderen Outputs via Worker-Tasks)                           ║
║                                                                      ║
║  AUSGABEN DURCH WORKER:                                              ║
║    .claude/models/{NAME}_Model.md         (via _model)               ║
║    .claude/analysis/synthese/{NAME}-OBSERVE{N}.md  (via _SC_observe) ║
║    .claude/analysis/synthese/{NAME}-ERGEBNIS{N}.md (via _SC_ergebnis)║
║    .claude/analysis/exploration/{NAME}-E*.md  (Welle 1, Explorer)   ║
║    .claude/analysis/drafts/{NAME}-*-D*.md     (Welle 2, Drafter)    ║
║    .claude/analysis/synthese/{NAME}-HANDOFF.md (Team Lead, DONE)    ║
║    .claude/analysis/post-impl/{NAME}-REVIEW-PROTOKOLL.md            ║
║      (nur bei --mode=review: Reparatur-Findings, NICHT ins Model)   ║
║                                                                      ║
║  HAUPTPRODUKT: MODEL                                                 ║
║    (Zentrales Artefakt dieser Phase: Wissensbasis / Model)           ║
╚══════════════════════════════════════════════════════════════════════╝
```

### Lifecycle-Guard: Artefakt-Namespaces (v2.2+, I-11)

Artefakte in `.claude/analysis/` folgen einer Phase-Prefix-Konvention.
Keine Vermischung zwischen Phasen-Namespaces erlaubt.

| Phase | Prefix/Ordner | Beispiel-Artefakte | Erzeuger |
|-------|---------------|-------------------|----------|
| A-Phase (Analyse) | `exploration/{NAME}-E*`, `drafts/{NAME}-model-D*` | E01-architektur.md, model-D01-validierung.md | `/_model`, `/_A_orchestrate` |
| SC-Phase (Scientific Cycle) | `drafts/{NAME}-observe*-D*`, `synthese/{NAME}-OBSERVE*`, `synthese/{NAME}-HYPOTHESEN*` | observe3-D01-code.md, OBSERVE3.md, HYPOTHESEN-I3.md | `/_SC_observe`, `/_SC_hypothese` |
| I-Phase (Implementation) | `synthese/{NAME}-HANDOFF.md`, `post-impl/{NAME}-REVIEW-*` | HANDOFF.md, REVIEW-PROTOKOLL.md | `/_SC_orchestrate` (DONE), `/_I_orchestrate` |

**Regel:** Ein SC-Worker darf KEINE A-Phase-Artefakte (exploration/) ueberschreiben.
Ein I-Worker darf KEINE SC-Synthese-Dokumente (OBSERVE, HYPOTHESEN) ueberschreiben.
Verletzung → Lifecycle-Guard-Alarm im Manifest dokumentieren.

---

```
+======================================================================+
| META-COMMAND: /_SC_orchestrate                                       |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU - die ausfuehrende Claude-Instanz)              |
| WORKER: Kurzlebige Single-Command-Agents (1 Agent = 1 Command)       |
|         + N Wellen-Agents (PARALLEL: Explorer/Drafter/Synthese)      |
|                                                                        |
| ZWECK: Orchestriert kurzlebige Agents durch den kompletten            |
|        wissenschaftlichen Forschungszyklus. Team Lead erstellt Team,   |
|        Tasks und spawnt pro Pipeline-Step einen frischen Agent.        |
|        Jeder Agent fuehrt genau 1 Command aus und stirbt danach.      |
|        Team Lead steuert aktiv: Agent-Ergebnis pruefen, naechsten     |
|        Agent spawnen, Zyklen-Entscheidung treffen.                    |
|                                                                        |
| PRINZIP: 1 Agent = 1 Command = stirbt danach (KURZLEBIG_PROMPT).    |
|          State lebt in DOKUMENTEN (Vertraegen), nicht im Agenten.     |
|          Kein Worker-Loop, kein TaskList-Polling.                      |
|          Team Lead entscheidet nach jedem Zyklus den naechsten Schritt.|
|                                                                        |
| WELLEN-STEUERUNG: Commands die intern Wellen haben (Exploration →    |
|   Drafts → Synthese) werden vom TEAM LEAD orchestriert via           |
|   Wellen-Tasks. Workers fuehren NUR die ihnen zugewiesene Welle aus. |
|   KEIN Worker spawnt Sub-Agents. (W7-Constraint)                     |
|                                                                        |
| FLOW:                                                                  |
|   W_FETCH → PRE-CYCLE → SC-CYCLE ⟲ → POST-CYCLE → HiL              |
|                                                                        |
| MODUS: THEORETISCH (Default) | IMPLEMENT (mit -I Flag)               |
|         | REVIEW (mit --mode=review Flag)                              |
|   THEORETISCH: _implement wird UEBERSPRUNGEN, _hypothese = Haupt-     |
|                Produktions-Phase, Verifikation V-S1 bis V-S4          |
|   IMPLEMENT:   _implement wird AUSGEFUEHRT, Verifikation V1-V5       |
|   REVIEW:      Post-Implementation-Quality-Review. Gate 6 statt       |
|                Standard-Gates. Findings in .claude/analysis/post-impl/ |
|                statt ins Haupt-Model. Kein SRS-Baseline noetig.       |
+======================================================================+
```

---

## Aufruf

```
/_SC_orchestrate [name] [difficulty] [ceiling] [floor] [-I] [--mode=review]
```

**Parameter:**

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `name` | (PFLICHT) | String | Feature-/Forschungsname (fuer Task.md, Model, Team) |
| `difficulty` | normal | easy, normal, hard | Steuert Agent-Anzahl, Wellen-Tiefe, MCP-Queries |
| `ceiling` | sonnet | haiku, sonnet, opus | Hoechstes Modell (Worker + Synthese-Wellen) |
| `floor` | haiku | haiku, sonnet | Niedrigstes Modell (Exploration-Wellen) |
| `-I` | (nicht gesetzt) | Flag | SC-Spec-Modus: `-I` = IMPLEMENT (inkl. _SC_implement), ohne = THEORETISCH (Default, nur Spec-Output) |
| `--mode=review` | (nicht gesetzt) | Flag | Post-I Review-Modus: Gates auf Post-Implementation kalibriert, Findings in separatem Protokoll-Pfad. **INKOMPATIBEL mit -I** (review = NACH Implementation, -I = WAEHREND Implementation) |

**Beispiele:**
```
/_SC_orchestrate ChapterPDF                  → normal, sonnet/haiku
/_SC_orchestrate TwoTierBridge hard opus haiku  → hard, opus ceiling
/_SC_orchestrate QuickFix easy sonnet sonnet    → easy, alles sonnet
/_SC_orchestrate OmniCommand normal opus haiku       → THEORETISCH (Default, kein _implement)
/_SC_orchestrate MyFeature normal opus haiku -I       → IMPLEMENT (inkl. _implement)
/_SC_orchestrate MyFeature normal opus haiku --mode=review  → Post-I Review (Gate 6, separater Pfad)
```

**Voraussetzungen:**
- KEINE — der Orchestrator startet den kompletten Zyklus von Null.
- Falls Model/Task.md bereits existieren: Worker prueft und baut darauf auf.
- Falls Vault/RAG bereits Wissen hat: W_fetch findet es automatisch.

**Modell-Zuordnung und Skalierung:**

| Rolle | easy | normal | hard |
|-------|------|--------|------|
| Team Lead | DU (Opus) | DU (Opus) | DU (Opus) |
| Synthese (Welle 3) | 1 {ceiling} | 1 {ceiling} | 1 {ceiling} |
| Drafter (Welle 2) | --- | 3 {middle} | 5 {middle} |
| Explorer (Welle 1) | --- | 5 {floor} | 9 {floor} |

**WICHTIG:** Team Lead spawnt ALLE Wellen-Tasks PARALLEL. Worker spawnt NICHTS.
- hard:   9 {floor} (Explorer PARALLEL) → 5 {middle} (Drafter PARALLEL) → 1 {ceiling} (Synthese)
- normal: 5 {floor} (Explorer PARALLEL) → 3 {middle} (Drafter PARALLEL) → 1 {ceiling} (Synthese)
- easy:   1 {ceiling} (Synthese solo, Team Lead spawnt 1 Worker)

**WELLEN-PRINZIP:** Innerhalb einer Welle laufen ALLE Agents PARALLEL (keine gegenseitige Blockierung).
Nur die NAECHSTE Welle wird durch Abschluss der vorherigen Welle blockiert.

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
4. `.claude/pileOfMud/` → Rohmaterial vorhanden?

Bestimme Startpunkt:
- Kein Manifest, kein Task.md → Voller Zyklus ab W_fetch
- Task.md vorhanden, kein Model → Ab /_model
- Model vorhanden → Ab /_SC_observe (Zyklus direkt)

**Modus-Erkennung:**

```
WENN --mode=review UND -I gesetzt:
  → FEHLER: "--mode=review ist INKOMPATIBEL mit -I.
     -I = WAEHREND Implementation (SC-Spec-Modus).
     --mode=review = NACH Implementation (Post-I Quality-Review).
     Nur eines von beiden verwenden."
  → ABBRUCH

WENN --mode=review:
  → Setze MODUS=REVIEW im Manifest (SC_PIPELINE_STATE.modus: REVIEW)
  → Pruefe: Existiert I-Pipeline-Ergebnis?
    (Manifest: I_PIPELINE_STATE vorhanden ODER implementierte Dateien in git)
    WENN NEIN: WARNUNG an User:
      "Review-Modus erfordert vorherige Implementation.
       Keine I-Pipeline-Spuren gefunden. Fortfahren? (HiL)"
  → Erstelle post-impl/ Verzeichnis: .claude/analysis/post-impl/
  → Max Zyklen: easy=2, normal=3, hard=5 (statt 3/5/8)

WENN -I gesetzt:
  → Setze MODUS=IMPLEMENT

SONST:
  → Setze MODUS=THEORETISCH (Default)
```

**pipeline_mode Lifecycle-Initialisierung (EC-4, W200):**

```
Schreibe ins Manifest nach Modus-Erkennung:
  pipeline_mode: SC

  SC_I_LIFECYCLE.current_mode: SC
  SC_I_LIFECYCLE.transition_log APPEND:
    from_mode: (vorheriger Wert oder "init")
    to_mode: SC
    timestamp: {jetzt ISO8601}
    reason: "PRE-CYCLE gestartet, Modus={MODUS}"
    agent: "sc-orchestrate-agent"

RUECKWAERTSKOMPATIBILITAET: Wenn pipeline_mode noch nicht im Manifest vorhanden →
  initialisiere mit SC (Default gemaess ManifestSchema-SCIUebergang Abschnitt 2).
```

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
  team_name: "sc-{name}"
  description: "Scientific Cycle - {name}"
```

### Schritt 1.3: Tasks erstellen

Erstelle Tasks fuer den ERSTEN Durchlauf. Zyklus-Tasks werden
bei CONTINUE dynamisch neu erstellt.

**PRE-CYCLE (einmalig, uebersprungen wenn bereits vorhanden):**

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 0 | Wissen holen (Vault + RAG) | /_W_fetch {NAME} | - | Fetching knowledge from Vault and RAG |
| 1 | Aufgabe definieren | /_taskDefinition {NAME} | Task 0 | Defining task and collecting crumbs |
| 2 | Model aufbauen (Wellen-Tasks, siehe unten) | /_model {NAME} {difficulty} | Task 1 | Building knowledge model |

**SC-CYCLE (Iteration 1):**

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 3 | Observe: Findings sammeln | /_SC_observe | Task 2 | Collecting observations |
| 4 | Model pflegen | /_SC_modelMaintain | Task 3 | Maintaining model |
| 5 | Quality Gates pruefen | /_SC_qualityGate | Task 4 | Running quality gates |
| 6 | Hypothese formulieren | /_SC_hypothese | Task 5 | Formulating hypothesis |
| 7 | Implementieren | /_SC_implement | Task 6 | Implementing changes |
| 8 | Ergebnis sammeln | /_SC_ergebnis | Task 7 | Collecting results |

**STRATEGISCHER PUSH (nach jedem Zyklus):**

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 9 | Wissen temporaer pushen | /_W_push_temp auto | Task 8 | Pushing knowledge to RAG |

**Hinweis:** Tasks 3-9 werden bei CONTINUE dynamisch fuer die naechste
Iteration neu erstellt. Der strategische Push (Task 9) sichert
Zwischen-Ergebnisse nach jedem Zyklus im RAG.

**WELLEN-TASKS fuer Wellen-Commands (Team Lead erstellt N Tasks statt 1):**

Task 2 (_model) wird nach difficulty aufgesplittet — Team Lead erstellt diese Tasks
NACH Task 1 (taskDefinition) abgeschlossen ist (reaktiv, Option B):

| difficulty | Wellen-Tasks (Beispiel) | blocked_by |
|------------|------------------------|------------|
| easy | 2a: Model Synthese (solo) | Task 1 |
| normal | 2a-2e: Explorer E01-E05 (Welle 1 PARALLEL) → 2f-2h: Drafter D01-D03 (Welle 2 PARALLEL) → 2i: Synthese | Task 1 → 2a-2e → 2f-2h |
| hard | 2a-2i: Explorer E01-E09 (Welle 1 PARALLEL) → 2j-2n: Drafter D01-D05 (Welle 2 PARALLEL) → 2o: Synthese | Task 1 → 2a-2i → 2j-2n |

Analog fuer _SC_observe (Task 3) und _SC_ergebnis (Task 8) — siehe Phase 3.3.

**Wellen-Task-Erkennung:** Team Lead schreibt "[WORKER-MODE] Welle N:" in Task-Beschreibung.
Worker liest Task-Beschreibung via TaskGet und fuehrt NUR die zugewiesene Welle aus.

**POST-CYCLE (nach DONE-Decision):**

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 10 | ImplementationHandOff generieren | (Team Lead generiert Dokument) | Task 9 | Generating implementation handoff |
| 11 | Wissens-Push orchestrieren | /_W_push_orchestrate {NAME} {difficulty} {ceiling} {floor} | Task 10 | Orchestrating knowledge push |
| 12 | Feature finalisieren | /_finish {NAME} | Task 11 | Finalizing feature |

HINWEIS: Task 10 (HandOff) wird direkt vom Team Lead erstellt (kein Agent noetig).
Das HandOff-Dokument fasst SC-Ergebnisse fuer /_I_orchestrate zusammen.
HINWEIS: /_W_push_orchestrate handhabt intern die 6 Steps:
model finish → gap → push_global → modelSplit → sync_orchestrate hard --co-work → retrospektive.
Siehe .claude/commands/_W_push_orchestrate.md fuer Details.

### Schritt 1.4: Agents spawnen (KURZLEBIG_PROMPT v2.0)

Team Lead spawnt Agents JE NACH PHASE:

**SEQUENTIELLE PHASE** (Pipeline-Tasks: W_fetch, taskDef, modelMaintain, qualityGate, hypothese, implement, push_temp):

KEIN persistenter Worker. Team Lead spawnt PRO PIPELINE-STEP einen frischen Agent:
```
Task tool:
  name: "sc-{name}-{command}"       ← z.B. "sc-OmniCommand-observe"
  subagent_type: "general-purpose"
  model: "{ceiling}"                 ← aus Parameter (default: sonnet)
  team_name: "sc-{name}"
  mode: "bypassPermissions"
  prompt: [KURZLEBIG_PROMPT, siehe Phase 2]
```

Jeder Agent fuehrt genau 1 Command aus und stirbt danach.
Team Lead spawnt den naechsten Agent ERST wenn der aktuelle fertig ist (Phase 3).

**WELLEN-PHASE** (model, observe, ergebnis bei normal/hard):
Team Lead spawnt N Worker GLEICHZEITIG pro Welle:

```
Welle 1 (Explorer, PARALLEL):
  FUER JEDEN Explorer-Task (E01..E{N}):
    Task tool:
      name: "sc-explorer-E{NN}"
      subagent_type: "general-purpose"
      model: "{floor}"                ← haiku fuer Explorer
      team_name: "sc-{name}"
      mode: "bypassPermissions"
      run_in_background: true         ← PARALLEL!
      prompt: [WORKER-PROMPT mit "[WORKER-MODE] Welle 1:" Task-Beschreibung]

Welle 2 (Drafter, PARALLEL — erst NACH Welle 1 komplett):
  FUER JEDEN Drafter-Task (D01..D{N}):
    Task tool:
      name: "sc-drafter-D{NN}"
      subagent_type: "general-purpose"
      model: "{middle}"               ← sonnet fuer Drafter
      team_name: "sc-{name}"
      mode: "bypassPermissions"
      run_in_background: true         ← PARALLEL!
      prompt: [WORKER-PROMPT mit "[WORKER-MODE] Welle 2:" Task-Beschreibung]

Welle 3 (Synthese, 1 Agent — erst NACH Welle 2 komplett):
    Task tool:
      name: "sc-synthese"
      subagent_type: "general-purpose"
      model: "{ceiling}"              ← opus fuer Synthese
      team_name: "sc-{name}"
      mode: "bypassPermissions"
      prompt: [WORKER-PROMPT mit "[WORKER-MODE] Synthese:" Task-Beschreibung]
```

**easy:** Kein Wellen-Modus, Team Lead spawnt pro Step 1 Agent (sc-{name}-{command}).

---

## PHASE 2: KURZLEBIG_PROMPT (Single-Command-Agent)

Pro Pipeline-Step spawnt Team Lead 1 kurzlebigen Agent.
Jeder Agent bekommt diesen minimalen Prompt (kein Worker-Loop, kein TaskList-Polling):

```
Du bist ein Single-Command-Agent fuer den Scientific Cycle.
Agent-Name: sc-{name}-{command}
Team: sc-{name}

═══ DEIN AUFTRAG ═══

Genau 1 Command ausfuehren, dann fertig.

Command:     {COMMAND_PATH} {NAME} {DIFFICULTY}
Task-ID:     {TASK_ID}

═══ WISSEN ABRUFEN (Optional) ═══

Falls feature-lokales Wissen vorhanden:
  mcp__cleancoder__query(
    query_text="[dein Fokus]",
    collection="local_knowledge_{FEATURE_ID}",
    limit=3
  )
  {FEATURE_ID} = sanitized Feature-Name (lowercase, underscores)
  Beispiel: "dcsre881" fuer DCSRE-881
  → .claude/analysis/synthese/{NAME}-HANDOFF.md (ADR-Kontext, falls vorhanden)

═══ SCHRITTE ═══

1. Lies Command-Datei: .claude/commands/{COMMAND_FILE}.md
2. Fuehre Command aus.
3. TaskUpdate {TASK_ID} status=completed
4. SendMessage an "team-lead":
   "{COMMAND} {NAME}: [2-3 Saetze Summary]"

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- NUR dieser eine Command, dann fertig (KEIN TaskList-Loop)
- Manifest (_manifest.md) nach Command aktualisieren
- Arbeite gruendlich, nicht schnell
```

**Wellen-Phase Prompt** (fuer Wellen-Worker bei model, observe, ergebnis):

Wellen-Worker erhalten einen spezifischen Prompt der ihre Rolle direkt enthaelt:

```
Du bist ein Wellen-Worker fuer den Scientific Cycle.
Agent-Name: sc-{wellen-name}
Team: sc-{name}

═══ DEIN AUFTRAG ═══

Genau 1 Welle ausfuehren, dann fertig.

Welle:       {WELLEN-BESCHREIBUNG}
Task-ID:     {TASK_ID}

═══ ROLLEN-ERKENNUNG ═══

Deine Rolle kommt direkt aus diesem Prompt (KEIN TaskGet noetig):
- Welle 1 (Exploration): Lies Crumbs/Model, schreibe exploration/{NAME}-E{NN}-{fokus}.md
- Welle 1 (Drafts): Lies Model, schreibe drafts/{NAME}-{phase}-D{NN}-{fokus}.md
# SP-FIX-2: Stille-Post-Schutz (Wellen-Rollen)
- Welle 2 (Drafts): Lies Crumbs + Model + Exploration (NUR als Kompass), schreibe drafts/*-D{NN}-*.md
- Welle 2/3 (Synthese): Lies Crumbs + Model + Drafts (NUR als Kompass), verifiziere JEDE Aussage an Primaerquellen, schreibe finales Dokument

═══ SCHRITTE ═══

1. Fuehre die zugewiesene Welle aus.
2. TaskUpdate {TASK_ID} status=completed
3. SendMessage an "team-lead":
   "{WELLE} {NAME}: [2-3 Saetze Summary]"

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- NUR diese eine Welle, dann fertig
```

---

## PHASE 3: TEAM LEAD STEUERUNG (Aktives Spawning v2.0)

### 3.1 Agent-Messages empfangen und naechsten Agent spawnen

Team Lead (DU) empfaengst Agent-Messages automatisch.
Pro Message:

```
1. Agent meldet: "{COMMAND} {NAME}: Summary"
2. Team Lead prueft: Passt das Ergebnis?
3. Bei Erfolg: Naechsten Agent spawnen (naechster Pipeline-Step)
   → sc-{name}-{naechster-command} mit KURZLEBIG_PROMPT
4. Bei Problem: Neuen Agent spawnen mit Korrektur-Kontext
   → sc-{name}-{command}-retry mit erweitertem Prompt
5. Nach /_SC_ergebnis: → Phase 3.2 (Zyklus-Entscheidung)
6. Nach /_W_push_temp: → Phase 3.2 Ergebnis auswerten (CONTINUE/DONE)
```

**Pipeline-Sequenz (Team Lead spawnt aktiv):**
```
sc-{name}-W_fetch
  → sc-{name}-taskDef
    → sc-{name}-model (oder Wellen-Worker)
      → sc-{name}-observe (oder Wellen-Worker)
        → sc-{name}-modelMaintain
          → sc-{name}-qualityGate
            → sc-{name}-hypothese
              → sc-{name}-implement (nur bei -I Modus, SKIP bei REVIEW)
                → sc-{name}-ergebnis (oder Wellen-Worker)
                  → sc-{name}-push_temp
```

**SC_PIPELINE_STATE im Manifest (Team Lead aktualisiert nach jedem Agent):**
```yaml
SC_PIPELINE_STATE:
  cycle_nr: {N}
  stufe: "{aktueller-command}"
  sc_status: RUNNING            # RUNNING | DONE | DONE_DISCOVERY_ONLY | BLOCKED
  resume_zaehler:
    W_fetch: 0
    taskDef: 0
    model: 0
    observe: 0
    modelMaintain: 0
    qualityGate: 0
    hypothese: 0
    implement: 0
    ergebnis: 0
    push_temp: 0
  aktive_agent_ids: []
```

### 3.2 Zyklus-Entscheidung (nach /_SC_ergebnis)

Team Lead wertet folgende Signale aus:

**Aus Worker-Message (/_SC_ergebnis):**
- SRS-Score und SRS-Trend
- Offene vs widerlegte W{n}
- Stagnations-Zaehler
- Fortschritts-Bewertung

**Aus /_SC_qualityGate (falls Worker gemeldet hat):**
- Gate 3: Feature-Abschluss Coverage-%
- Gate 5: Stagnation (Schwellen)
- BSD-Trigger (T1-T5)

**Decision-Table (Standard-Modus: THEORETISCH / IMPLEMENT):**

```
┌──────────────────────────┬─────────────────────┬──────────┬───────────────┐
│ Signal                   │ Bedingung           │ Decision │ Aktion        │
├──────────────────────────┼─────────────────────┼──────────┼───────────────┤
│ Feature-Coverage         │ >= 90%              │ DONE     │ Post-Cycle    │
│ SRS-Trend                │ Konvergent + stabil │ DONE     │ Post-Cycle    │
│ Stagnation               │ >= 7.0              │ ABORT    │ Post-Cycle*   │
│ Stagnation               │ >= 5.0              │ FORCE    │ Post-Cycle    │
│ Fortschritt              │ STARK oder SCHWACH  │ CONTINUE │ Neuer Zyklus  │
│ Max Zyklen erreicht      │ easy=3, norm=5, h=8 │ FORCE    │ Post-Cycle    │
│ User-Override            │ (via HiL)           │ varies   │ nach Feedback │
└──────────────────────────┴─────────────────────┴──────────┴───────────────┘

* ABORT: Post-Cycle OHNE /_model finish. Direkt zu /_retrospektive
  mit ABORT-Vermerk. Meta-Analyse statt Feature-Abschluss.
```

**Decision-Table (REVIEW-Modus: --mode=review):**

```
┌──────────────────────────┬──────────────────────────┬──────────┬───────────────┐
│ Signal                   │ Bedingung                │ Decision │ Aktion        │
├──────────────────────────┼──────────────────────────┼──────────┼───────────────┤
│ Review-Items             │ Alle RESOLVED/DEFERRED   │ DONE     │ Post-Cycle    │
│ Gate 6 (Reality-Check)   │ Code↔Model konsistent    │ DONE     │ Post-Cycle    │
│ Fortschritt              │ Items noch OPEN          │ CONTINUE │ Neuer Zyklus  │
│ Max Zyklen erreicht      │ easy=2, norm=3, hard=5   │ FORCE    │ Post-Cycle    │
│ User-Override            │ (via HiL)                │ varies   │ nach Feedback │
└──────────────────────────┴──────────────────────────┴──────────┴───────────────┘

REVIEW-Modus nutzt Gate 6 statt Gate 1 (Battle-Royale). SRS-Tracking ist DEAKTIVIERT.
Findings gehen nach .claude/analysis/post-impl/{NAME}-REVIEW-PROTOKOLL.md, NICHT ins Model.
Nur strukturelle Erkenntnisse die das Model AENDERN muessen → manuell als W{n} ins Model.
```

### 3.3 Bei CONTINUE-Decision

Wenn Zyklus weitergehen soll:

1. **Pruefe Iteration-Counter:**
   - Standard-Modus: easy=3, normal=5, hard=8
   - Review-Modus:   easy=2, normal=3, hard=5
   - Ueberschritten? → FORCE statt CONTINUE

2. **Erstelle neue CYCLE Tasks:**

_SC_observe und _SC_ergebnis werden ebenfalls als Wellen-Tasks erstellt (normal/hard).
Pattern 9-5-1 / 5-3-1 / 1 (identisch zu _model):
Fuer easy: 1 Task (solo). Fuer normal: 5 Explorer PARALLEL → 3 Drafter PARALLEL → 1 Synthese. Fuer hard: 9 Explorer PARALLEL → 5 Drafter PARALLEL → 1 Synthese.
Innerhalb einer Welle: ALLE Agents PARALLEL (keine gegenseitige Blockierung).
Naechste Welle blockiert durch Abschluss der vorherigen Welle.

```
TaskCreate: "Observe: Findings sammeln (Zyklus {C+1})"
  description: "/_SC_observe ausfuehren. Zyklus {C+1}.
    Lies vorheriges ERGEBNIS{C}.md als Input.
    Bei easy: Solo. Bei normal/hard: Team Lead erstellt Wellen-Tasks (D01..DN + Synthese).
    Sammle Findings OHNE Interpretation."
  blocked_by: (letzter completed Task, z.B. W_push_temp)

TaskCreate: "Model pflegen (Zyklus {C+1})"
  blocked_by: (observe Task)

TaskCreate: "Quality Gates pruefen (Zyklus {C+1})"
  blocked_by: (modelMaintain Task)

TaskCreate: "Hypothese formulieren (Zyklus {C+1})"
  blocked_by: (qualityGate Task)

TaskCreate: "Implementieren (Zyklus {C+1})"
  blocked_by: (hypothese Task)

TaskCreate: "Ergebnis sammeln (Zyklus {C+1})"
  blocked_by: (implement Task)

TaskCreate: "Wissen temporaer pushen (Zyklus {C+1})"
  blocked_by: (ergebnis Task)
```

3. **Starte naechsten Zyklus (Team Lead spawnt ersten Agent):**

```
Team Lead spawnt sc-{name}-observe mit KURZLEBIG_PROMPT:
  "CONTINUE: Neuer Zyklus {C+1}. Fuehre /_SC_observe aus."
```

### 3.3a Prozessbegleitende W_sync_orchestrate Trigger (NEU v2.0)

Nach bestimmten Tasks spawnt der Team Lead einen **parallelen easy-Sync Worker**,
OHNE den Haupt-Worker zu unterbrechen.

**Trigger-Punkte im SC-CYCLE:**

| Nach Task | Sync-Schwierigkeit | Was wird gesynct | Wann | --co-work |
|-----------|-------------------|-----------------|------|-----------|
| T4 (modelMaintain) | easy | models/{NAME}_Model.md | Jeder Zyklus | Kein --co-work |
| T8 (ergebnis) | easy/normal --co-work | ERGEBNIS + OBSERVE + QUALITYGATE + HYPOTHESEN | Jeder Zyklus | Mit --co-work (Zyklus-Abschluss) |
| T9 (W_push_temp) | easy | wissen/*.md | Jeder Zyklus | Kein --co-work |

**Parallel-Worker-Pattern:**

```
1. Team Lead erkennt Task-Completion (modelMaintain, ergebnis, W_push_temp)
2. Team Lead entscheidet: Sync sinnvoll? (z.B. nach modelMaintain wenn Model signifikant geaendert)
3. Team Lead spawnt Sync-Agent:
   Task tool: sc-{name}-syncOrchestrate
     "W_sync_orchestrate {NAME} easy [--co-work wenn nach ergebnis]: Sync nach {TASK}."
   ODER TaskCreate mit nicht-blockierendem Task.
4. Sync-Agent laeuft PARALLEL zum aktuellen Pipeline-Agent (nicht-blockierend)
5. Worker meldet Ergebnis, Team Lead protokolliert

CONSTRAINT (WellenRedesign R8+R9):
  - Auch easy spawnt 1 Worker (Team Lead fuehrt Sync NICHT selbst aus)
  - Team Lead steuert DIREKT (kein Worker spawnt weitere Worker)

CEILING-VERERBUNG:
  - Sync-Schwierigkeit = min(Parent-Schwierigkeit, requested)
  - Easy SC-Zyklus → maximal easy Sync
  - Normal SC-Zyklus → maximal normal Sync
  - Hard SC-Zyklus → maximal hard Sync (aber prozessbegleitend bleibt easy/normal)
```

**Hinweis:** T13 (POST-CYCLE) bleibt als **hard** Sync fuer vollstaendigen Feature-Ende-Sync.
Prozessbegleitende Triggers sind **zusaetzlich** zu T13, nicht als Ersatz.

### 3.4 Bei DONE/FORCE-Decision

Wenn Forschung abgeschlossen oder erzwungen:

0. **Manifest DONE_TIMESTAMP setzen:**

```
Aktualisiere .claude/analysis/_manifest.md:
  PHASE: DONE
  DONE_TIMESTAMP: {ISO_DATETIME}  (z.B. 2026-02-22T14:30:00)
  sc_status: DONE              ← W93: Formales SC-Abschluss-Signal fuer /_I_orchestrate Pre-Check
```

HINWEIS fuer DONE_DISCOVERY_ONLY (wenn Discovery abgeschlossen aber Implementation noch nicht spezifiziert):
  → Schreibe `sc_status: DONE_DISCOVERY_ONLY` statt `DONE`
  → /_I_orchestrate akzeptiert beide als gueltigen Start-Status.

#### SC-I Handoff-Gate (v2.2+, I-31)

**Zweck:** Formalisiert die SC-QUELL-Verantwortung fuer sc_status.
Bevor die I-Pipeline gestartet wird, MUSS der SC-Orchestrator pruefen ob
der SC-Zyklus abgeschlossen ist und den passenden sc_status setzen.
Dies ist das Komplement zur EMPFAENGER-Seite in `_I_orchestrate` (Schritt 0.2a, Z.556-568).

**Gate-Logik (SC-Orchestrator prueft VOR I-Pipeline-Start):**

| sc_status (aktuell) | Bedeutung | Gate-Entscheidung |
|----------------------|-----------|-------------------|
| `DONE` | SC-Zyklus vollstaendig abgeschlossen | I-Pipeline starten (alle SC-Artefakte uebergeben) |
| `DONE_DISCOVERY_ONLY` | Discovery fertig, Implementation nicht spezifiziert | I-Pipeline starten (kein SC-Review noetig) |
| `RUNNING` | SC-Zyklus laeuft noch | HiL: "SC noch aktiv. Warten oder parallel starten?" |
| `BLOCKED` | SC blockiert (externer Blocker) | STOPP: Blocker zuerst loesen, sc_status auf DONE setzen |
| (kein Feld) | Kein SC-Kontext vorhanden | Normal weiter (I-Pipeline ohne SC-Vorzyklus) |

**Referenz:** `_I_orchestrate` Schritt 0.2a (Z.556-568) liest diesen sc_status
und fuehrt die EMPFAENGER-Pruefung durch. SC setzt den Wert, I liest ihn.
Bidirektionale Konsistenz: SC-Orchestrator = Schreiber, I-Orchestrator = Leser.

Dieser Timestamp wird von /_W_push_orchestrate Schritt 1.1b (CHECK 1) genutzt,
um Out-of-Pipeline Arbeit praezise zu erkennen (praeziser als Datei-Timestamps).

**POST-CYCLE Lifecycle-Schritt 0: Modus-Transition (EC-4, W180-E)**

```
Schreibe ins Manifest VOR HANDOFF-Generierung:
  pipeline_mode: POST_CYCLE

  SC_I_LIFECYCLE.current_mode: POST_CYCLE
  SC_I_LIFECYCLE.transition_log APPEND:
    from_mode: SC
    to_mode: POST_CYCLE
    timestamp: {jetzt ISO8601}
    reason: "SC-Zyklus abgeschlossen ({Decision}: DONE|FORCE), POST-CYCLE gestartet"
    agent: "sc-orchestrate-agent"

ZWECK: I-Orchestrator Schritt 0.2a liest pipeline_mode.
  POST_CYCLE → I-Start ABGELEHNT (POST-CYCLE noch aktiv).
  Erst nach Finaler Verifikation (Patch 5) → pipeline_mode: READY_FOR_I.
```

1. **ImplementationHandOff generieren (Team Lead direkt, W99):**

Team Lead erstellt strukturiertes HandOff-Dokument als SC→I Uebergabe-Vertrag.
Dieses Dokument fasst den SC-Zyklus fuer /_I_orchestrate zusammen.

```
Schreibe .claude/analysis/synthese/{NAME}-HANDOFF.md:

---
type: handoff
feature: {NAME}
date: {YYYY-MM-DD}
cycles: {C}
sc_status: {DONE|FORCE}
srs_final: {score}
---

# ImplementationHandOff: {NAME}

## 1. LOESCHEN (Prototypen-Artefakte, untracked files)
- {Liste der Dateien die VOR I-Pipeline bereinigt werden muessen}
- Untracked files aus `git status` die nicht produktiv sind

## 2. BEHALTEN (produktive Dateien + Status)
- {Datei}: {Status} (AKTIV / ZUR_PRUEFUNG / FERTIG)

## 3. OFFENE AUFGABEN (W{n} AKTIV + ZUR_PRUEFUNG)
| # | W{n} | Beschreibung | Prioritaet |
|---|------|-------------|-----------|
| 1 | W{x} | {kurz} | HOCH/MITTEL/NIEDRIG |

## 4. ARCHITEKTUR-ENTSCHEIDUNGEN (ADR-Zusammenfassung)
- ADR {v}: {Entscheidung} (Status: BESTAETIGT/OFFEN)

## 5. KRITISCHE HINWEISE
- Externe Abhaengigkeiten: {Liste}
- Risiken: {Liste}
- Scope-Einschraenkungen: {was ist RAUS}

## 6. SRS-TREND (EC-2, W180-B)
| Zyklus | Score | Trend | Diff |
|--------|-------|-------|------|
| 1      | {srs_zyklus_1} | -    | -    |
| {C}    | {srs_final}    | ↓/↑  | {diff_percent}% |

Quelle: Manifest `sc_final_srs` pro Zyklus (OBSERVE{N}-Frontmatter).
Interpretation: {z.B. "Substantielle Reduktion", "Stagnation", "Komplexitaets-Anstieg"}

## 7. DISCOVERY-GAPS (EC-2, W180-B)
Topics mit unzureichender RAG-Abdeckung (< 3 Chunks) oder offenen W{n}:
| Topic | W{n} | Status | Chunks | Empfehlung |
|-------|------|--------|--------|------------|
| {topic_1} | W{x} | ZUR_PRUEFUNG | {n} | I-Phase vertiefen |
| {topic_2} | W{y} | AKTIV        | 0   | Grundlagen fehlen |

Quelle: `w_register where status IN (AKTIV, ZUR_PRUEFUNG)` + RAG gap-Analyse.
Leer wenn alle kritischen W{n} BESTAETIGT: `- (keine offenen Gaps)`

## 8. ADR-RATIONALE (EC-2, W180-B)
Architektur-Entscheidungen mit vollstaendiger Begruendung fuer I-Agenten:
| ADR | Entscheidung | Begruendung | Kontext | Status |
|-----|-------------|-------------|---------|--------|
| ADR-{v} | {Was entschieden} | {Warum} | W{n}-Referenz | BESTAETIGT/OFFEN |

Quelle: Model.md ADR-Sektion + W{n}-Notizen.
Zweck: I-Agenten verstehen das WARUM hinter Architektur-Entscheidungen
       (nicht nur das WAS aus Sektion 4 ARCHITEKTUR-ENTSCHEIDUNGEN).
```

**POST-CYCLE Lifecycle-Schritt 1: SC-Gate schreiben (EC-5, EC-1, W180-C)**

```
Schreibe sc_i_gate Block ins Manifest (NACH HANDOFF-Generierung, VOR _W_push):

sc_i_gate:
  status: pending                     # → wird in Patch 5 auf approved/rejected gesetzt
  criteria_met: []                    # → Checkliste: wird in sc_i_gate_check() gefuellt
  criteria_pending:                   # 3-Tier Checkliste (C1-C7):
    - "C1: srs_under_70"              # TIER-1 BLOCKING: SRS < 70
    - "C2: critical_wn_coverage_85"   # TIER-1 BLOCKING: >= 85% BESTAETIGT
    - "C3: w51_w56_confirmed"         # TIER-1 BLOCKING: Beide BESTAETIGT
    - "C4: ec_done_2_of_3"            # TIER-2 (EC-1, EC-2, EC-5 >= 2/3)
    - "C5: stagnation_under_075"      # TIER-2
    - "C6: handoff_valid_4_sections"  # TIER-2 (mind. 4 Pflicht-Sektionen)
    - "C7: hil_signature"             # TIER-3 (HiL-Bestaetigung, approved_by)
  tier_1_passed: null                 # → gesetzt in finale Verifikation
  tier_2_decision: null               # → gesetzt in finale Verifikation
  tier_3_approved: null               # → gesetzt in finale Verifikation
  approved_by: null                   # → Team Lead traegt hier ein (C7)
  approved_at: null
  justification: null

HINWEIS FORCE_ACCEPT Sonderfall:
  Wenn Team Lead Gate manuell ueberstimmt:
    sc_i_gate.status: approved
    sc_i_gate.approved_by: "{user}"
    sc_i_gate.justification: "{Begruendung}"
    sc_i_gate.override_warning: "Gate-Kriterien nicht erfuellt, manuell ueberstimmt"
  → pipeline_mode: READY_FOR_I setzen (trotz Gate-Fail)
  → I-Orchestrator respektiert override_warning als Warnung
```

**Gate-Symmetrie-Doku:**
SC schreibt `sc_i_gate` (dieser Schritt).
I antwortet mit `i_gate_response` (in _I_orchestrate Schritt 0.2a).
Beide Gates bilden zusammen das bidirektionale Uebergangs-Protokoll (W202).

2. **Erstelle POST-CYCLE Tasks:**

```
TaskCreate: "Wissens-Push orchestrieren"
  description: "/_W_push_orchestrate {NAME} {difficulty} {ceiling} {floor} ausfuehren.
    Eigener Orchestrator fuer den kompletten POST-CYCLE Wissens-Push.
    Handhabt intern 6 Steps:
      model finish → gap → push_global → modelSplit → obsidianSync → retrospektive.
    Erstellt eigenes Team, spawnt kurzlebige Agents pro Step.
    Bei FORCE: Retrospektive mit FORCE-Vermerk."
  blocked_by: (letzter W_push_temp Task)

TaskCreate: "Feature finalisieren"
  description: "/_finish {NAME} ausfuehren.
    Offene Items pruefen (parking-lot, Task.md, Model W{n}).
    User fragt: PARKEN / DISCARD / ERLEDIGT.
    .claude/* Konsistenz-Check.
    Manifest: PHASE=READY."
  blocked_by: (W_push_orchestrate Task)
```

2. **Starte Post-Cycle (Team Lead spawnt W_push_orchestrate Agent):**

```
Team Lead spawnt sc-{name}-wpush mit KURZLEBIG_PROMPT:
  "DONE: Forschungszyklus abgeschlossen nach {C} Zyklen.
   Fuehre /_W_push_orchestrate {NAME} {difficulty} {ceiling} {floor} aus."
```

### 3.4b POST-CYCLE Finale Verifikation und Gate-Abschluss (EC-4, EC-1, W180-A, W180-E)

TIMING: Dieser Schritt findet statt NACHDEM W_push_orchestrate-Agent fertig gemeldet hat
        UND _finish-Task abgeschlossen ist.

```
sc_i_gate_check() — 3-Tier Verifikation:

TIER-1 (BLOCKING — alle drei muessen PASS sein):
  C1: sc_final_srs < 70?
    → JA:  criteria_met APPEND "srs_under_70"
    → NEIN: TIER-1 FAIL — pipeline_mode: POST_CYCLE_RETRY, sc_i_gate.status: rejected
            Logge: "Gate FAIL C1: SRS={srs} >= 70. SC-Zyklen fortsetzen."
            STOP (kein READY_FOR_I)

  C2: Kritische W{n} (Kategorie architektur/mechanismen) >= 85% BESTAETIGT?
    → JA:  criteria_met APPEND "critical_wn_coverage"
    → NEIN: TIER-1 FAIL — wie oben

  C3: W51 BESTAETIGT UND W56 BESTAETIGT?
    → JA:  criteria_met APPEND "w51_w56_confirmed"
    → NEIN: TIER-1 FAIL — wie oben

TIER-2 (Conditional — mind. 2/3 muessen PASS sein):
  C4: Kritische ECs DONE >= 2 von 3 (EC-1, EC-2, EC-5)?
    → JA: tier2_count++
  C5: STAGNATION < 0.75?
    → JA: tier2_count++
  C6: HANDOFF.md hat mind. 4 Pflicht-Sektionen
       (LOESCHEN, BEHALTEN, OFFENE AUFGABEN, ARCHITEKTUR)?
    → JA: tier2_count++

  IF tier2_count < 2:
    TIER-2 FAIL → pipeline_mode: POST_CYCLE_RETRY, sc_i_gate.status: rejected
    Logge: "Gate FAIL TIER-2: {tier2_count}/3 Conditional erfuellt."
    STOP

TIER-3 (Governance — HiL-Signatur):
  C7: sc_i_gate.approved_by gesetzt (Team Lead Signatur)?
    → JA:  tier_3_approved: true
    → NEIN: status: pending_approval (kein Hard-Stop, HiL-Benachrichtigung)
            Logge: "Gate CONDITIONAL: TIER-1+2 OK, warte auf HiL-Signatur (C7)."
            HiL: "Forschung abgeschlossen. SC→I Gate bereit fuer Bestaetigung.
                  SRS={srs}, W{n}-Abdeckung={coverage}%. Genehmigen?"
            → Nach HiL-Bestaetigung: approved_by setzen, weiter zu PASS

GATE PASS (alle Tier erfuellt):
  sc_i_gate.status: approved
  sc_i_gate.tier_1_passed: true
  sc_i_gate.tier_2_decision: pass
  sc_i_gate.tier_3_approved: true
  sc_i_gate.approved_by: "{team-lead-user}"
  sc_i_gate.approved_at: {jetzt ISO8601}

  pipeline_mode: READY_FOR_I

  SC_I_LIFECYCLE.current_mode: READY_FOR_I
  SC_I_LIFECYCLE.sc_cycles_completed: {C}
  SC_I_LIFECYCLE.transition_log APPEND:
    from_mode: POST_CYCLE
    to_mode: READY_FOR_I
    timestamp: {jetzt ISO8601}
    reason: "Finale Verifikation PASS (W204), sc_i_gate APPROVED, alle {C} Zyklen abgeschlossen"
    agent: "sc-orchestrate-agent"

  Logge: "READY_FOR_I: Gate bestanden. I-Pipeline kann starten."
  Melde User: "SC-Phase abgeschlossen. pipeline_mode=READY_FOR_I.
               I-Pipeline kann mit /_I_orchestrate {NAME} gestartet werden."
```

### 3.5 Bei ABORT-Decision

Wenn Stagnation >= 7.0 oder unueberwindbares Hindernis:

1. **Erstelle ABORT-Tasks (verkuerzt):**

```
TaskCreate: "Retrospektive (ABORT)"
  description: "/_retrospektive ausfuehren mit ABORT-Modus.
    Meta-Analyse: Warum stagniert der Ansatz?
    Was wurde gelernt? Welcher alternative Ansatz?
    KEIN /_model finish (Model bleibt unfertig als Dokument)."
  blocked_by: (letzter completed Task)
```

2. **Optional: W_push_temp als Sicherung:**
   - Auch bei ABORT: Bisheriges Wissen temporaer sichern

### 3.6 Nach Retrospektive (Worker meldet "Retrospektive fertig")

Team Lead fuehrt HiL-Pause durch:

```
AskUserQuestion:
  header: "{NAME}"
  question: "Forschungszyklus '{name}' abgeschlossen.

    Zyklen: {C}
    Decision: {DONE|FORCE|ABORT}
    SRS-Score: {final_srs}
    W{n}: {confirmed} BESTAETIGT, {refuted} WIDERLEGT, {open} OFFEN
    Stagnation: {stagnation_counter}
    GAP: {gap_percentage}% (IST vs SOLL)

    Bitte entscheiden:"

  options:
    - label: "ACCEPT"
      description: "Feature abgeschlossen, weiter"
    - label: "RETRY"
      description: "Nochmal von vorne (ich gebe Feedback)"
    - label: "PIVOT"
      description: "Ansatz aendern (neuen Zyklus mit anderem Fokus)"
    - label: "ABORT"
      description: "Feature aufgeben, nur Wissen sichern"
```

### 3.7 User-Decision verarbeiten

**Bei ACCEPT:**
```
1. Keine aktiven Agents (kurzlebig, bereits terminiert)
2. TeamDelete
3. _manifest.md aktualisieren: feature_status=ACCEPTED
5. Melde User:
   "Feature '{name}' abgeschlossen.
    Model: .claude/models/{name}_Model.md
    Wissen: global_knowledge (RAG)
    Vault: /_W_obsidianSync (falls konfiguriert)"
```

**Bei RETRY:**
```
1. Frage User nach Feedback (AskUserQuestion, Freitext)
2. Erstelle neue PRE-CYCLE Tasks (ab /_SC_observe, NICHT ab W_fetch)
3. Team Lead spawnt sc-{name}-observe mit KURZLEBIG_PROMPT:
   "RETRY: User-Feedback: {feedback}. Fuehre /_SC_observe aus."
4. Zurueck zu Phase 3.1 (Aktives Spawning)
```

**Bei PIVOT:**
```
1. Frage User nach neuem Fokus (AskUserQuestion, Freitext)
2. Erstelle neue PRE-CYCLE Tasks (ab /_taskDefinition mit neuem Fokus)
3. Altes Model behalten als Basis, aber neues Task.md
4. Team Lead spawnt sc-{name}-taskDef mit KURZLEBIG_PROMPT:
   "PIVOT: Neuer Fokus: {neuer_fokus}. Fuehre /_taskDefinition aus.
    Bestehendes Model als Basis nutzen."
5. Zurueck zu Phase 3.1 (Aktives Spawning)
```

**Bei ABORT:**
```
1. Team Lead spawnt sc-{name}-push_temp: /_W_push_temp auto (Wissen sichern)
2. Keine aktiven Agents (kurzlebig, bereits terminiert)
3. TeamDelete
5. _manifest.md aktualisieren: phase=ABORTED
6. Melde User: "Feature '{name}' abgebrochen. Zwischen-Wissen in RAG gesichert."
```

---

## PHASE 4: OPTIONALE ESKALATIONEN (vom Zyklus getriggert)

### 4.1 Architectural Boundaries (von qualityGate getriggert)

Wenn Worker aus /_SC_qualityGate meldet "BSD Trigger T1-T5" oder
"Architectural Boundaries empfohlen":

```
Team Lead erstellt Zusatz-Task:

  TaskCreate: "Architectural Boundaries"
    description: "/_architecturalBoundaries ausfuehren.
      Teilproblem-Dekomposition + Vertikale Suche.
      Dateipfade identifizieren fuer Implementierung."
    blocked_by: (qualityGate Task)
    blocks: (hypothese Task)  ← VOR Hypothese einschieben

Team Lead spawnt sc-{name}-architecturalBoundaries:
  "Architectural Boundaries Task. /_architecturalBoundaries ausfuehren."
```

### 4.2 Blind-Spot Detection (von qualityGate getriggert)

Wenn Worker aus /_SC_qualityGate meldet "BSD T1-T5 Muster erkannt":

```
Team Lead erstellt Zusatz-Task:

  TaskCreate: "Blind-Spot Detection"
    description: "/_blindspotDetection ausfuehren.
      Max 7 Canary Probes AUSSERHALB des aktuellen Fokus.
      Epistemologische Grenze → Mensch-in-the-Loop."
    blocked_by: (qualityGate Task)
    blocks: (hypothese Task)

Team Lead spawnt sc-{name}-blindspotDetection:
  "Blind-Spot Detection. /_blindspotDetection ausfuehren."
```

### 4.3 Knowledge Deep-Dive (parallel)

Wenn waehrend des Zyklus ein Thema auftaucht das tiefere Recherche
braucht, kann Team Lead einen parallelen Task erstellen:

```
TaskCreate: "Knowledge Deep-Dive: {THEMA}"
  description: "/_knowledge {THEMA} {difficulty} ausfuehren.
    Parallele Wissens-Recherche. Blockiert NICHT den Hauptzyklus.
    Ergebnis: .claude/wissen/{THEMA}_Wissen.md"
  blocked_by: (KEINE — parallel)

HINWEIS: Dieser Task laeuft parallel. Worker kann ihn zwischen
         anderen Tasks oder nach dem Zyklus abarbeiten.
```

---

## ZUSAMMENFASSUNG: Sequenz-Diagramm

```
Team Lead                    Agent (sc-{name}-{cmd})         User
    │                              │                          │
    ├─ TeamCreate ─────────────►   │                          │
    ├─ TaskCreate (Tasks 0-9) ──►  │                          │
    ├─ Spawn Worker ────────────►  │                          │
    │                              │                          │
    │  ═══ PRE-CYCLE ═══          │                          │
    │                              ├─ T0: /_W_fetch           │
    │  ◄── "Wissen geholt" ───────┤                          │
    │                              ├─ T1: /_taskDefinition    │
    │  ◄── "Task definiert" ──────┤                          │
    │                              ├─ T2: /_model             │
    │  ◄── "Model gebaut" ────────┤                          │
    │                              │                          │
    │  ═══ SC-CYCLE (Iteration 1) ═══                        │
    │                              │                          │
    │  ┌─── ZYKLUS-LOOP ────────────────────────────────┐    │
    │  │                           │                     │    │
    │  │                           ├─ T3: /_SC_observe   │    │
    │  │ ◄── "Findings" ─────────┤                     │    │
    │  │                           ├─ T4: /_SC_modelMaint│    │
    │  │ ◄── "Model updated" ────┤                     │    │
    │  │                           ├─ T5: /_SC_qualGate  │    │
    │  │ ◄── "Gates checked" ────┤                     │    │
    │  │                           │                     │    │
    │  │  [BSD/Boundaries?]        │                     │    │
    │  │  JA → Zusatz-Tasks ────►  │ (Escalation)       │    │
    │  │                           │                     │    │
    │  │                           ├─ T6: /_SC_hypothese │    │
    │  │ ◄── "Hypothese" ────────┤                     │    │
    │  │                           ├─ T7: /_SC_implement │    │
    │  │ ◄── "Implementiert" ────┤                     │    │
    │  │                           ├─ T8: /_SC_ergebnis  │    │
    │  │ ◄── "SRS, Trend" ───────┤                     │    │
    │  │                           │                     │    │
    │  │  [CONTINUE?]              │                     │    │
    │  │  JA → neue T3-T9 ─────►  │ (naechster Zyklus)  │    │
    │  │  NEIN → DONE ────────────┼─────────────────────┘    │
    │  └──────────────────────────┘                          │
    │                              │                          │
    │                              ├─ T9: /_W_push_temp auto │
    │  ◄── "RAG gepusht" ────────┤                          │
    │                              │                          │
    │  ═══ POST-CYCLE ═══         │                          │
    │                              │                          │
    ├─ TaskCreate (T10-T11) ────►  │                          │
    │                              ├─ T10: /_W_push_orchestrate│
    │                              │  (intern: model finish →  │
    │                              │   gap → push_global →     │
    │                              │   modelSplit → obsidianSync│
    │                              │   → retrospektive)        │
    │  ◄── "Push done" ──────────┤                          │
    │                              ├─ T11: /_finish            │
    │  ◄── "Feature finalisiert" ┤                          │
    │                              │                          │
    ├─ AskUserQuestion ───────────────────────────────────►  │
    │  ◄── ACCEPT/RETRY/PIVOT/ABORT ─────────────────────────┤
    │                              │                          │
    │  [ACCEPT]                    │                          │
    ├─ Shutdown Worker ─────────►  │                          │
    ├─ TeamDelete                  │                          │
    ├─ "Feature fertig" ──────────────────────────────────►  │
```

---

## TASK-BESCHREIBUNGEN (Vorlagen fuer TaskCreate)

### Task 0: W_fetch

```
Subject: "Wissen holen (Vault + RAG)"
ActiveForm: "Fetching knowledge from Vault and RAG"
Description: |
  Fuehre /_W_fetch {NAME} aus.
  Lies .claude/commands/_W_fetch.md fuer Details.

  Suche in Vault UND RAG nach existierendem Wissen zu "{name}".
  Kopiere relevante Models und Wissens-Dokumente in .claude/.
  RAG-only Hits als Referenz notieren.

  Falls Vault nicht konfiguriert: Nur RAG-Suche (degraded mode).

  Input: Task.md (falls vorhanden), User-Keywords
  Output: .claude/models/*.md, .claude/wissen/*.md, _manifest.md

  Melde dem Team Lead:
    - Vault-Hits: {V} Dokumente
    - RAG-Hits: {R} Dokumente
    - BOTH-Hits: {B} Dokumente
    - Kopiert: {N} Dateien nach .claude/
    - "Keine Treffer" falls nichts gefunden
```

### Task 1: TaskDefinition

```
Subject: "Aufgabe definieren"
ActiveForm: "Defining task and collecting crumbs"
Description: |
  Fuehre /_taskDefinition {NAME} aus.
  Lies .claude/commands/_taskDefinition.md fuer Details.

  Sammle Material aus .claude/pileOfMud/ (Screenshots, PDFs, alte Models).
  Erstelle Task.md mit Aufgabe, Scope, Erfolgskriterien.
  Erstelle crumbs/{NAME}_crumbs.md mit strukturierten Kruemmeln.

  Falls pileOfMud/ leer: Erstelle Task.md direkt aus dem Kontext.

  Input: .claude/pileOfMud/*, User-Beschreibung, W_fetch-Ergebnisse
  Output: Task.md, crumbs/{NAME}_crumbs.md

  Melde dem Team Lead:
    - Aufgabe in 1-2 Saetzen
    - Scope (was ist DRIN, was ist RAUS)
    - Erfolgskriterien (3-5 Punkte)
```

### Task 2: Model

HINWEIS FUER TEAM LEAD: Task 2 ist ein PLATZHALTER. Der Team Lead erstellt nach
Abschluss von Task 1 (taskDefinition) MEHRERE Wellen-Tasks statt eines einzigen Tasks.
Siehe WELLEN-TASKS Sektion in Schritt 1.3 fuer die genaue Task-Struktur.

**Wellen-Task-Vorlage fuer _model (easy):**
```
Subject: "[WORKER-MODE] Model: Welle 3 - Synthese (solo)"
ActiveForm: "Building knowledge model"
Description: |
  [WORKER-MODE] Welle 3: Synthese fuer {NAME} (easy, solo)
  INPUT: crumbs/{NAME}_crumbs.md, Task.md, bestehende Models
  OUTPUT: .claude/models/{NAME}_Model.md
  Frontmatter-Pflicht: wave=synthese, status=final, primaerquelle_gelesen: true
  Aufgabe: Synthetisiere alle Inputs zu finalem Model. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

**Wellen-Task-Vorlage fuer _model (Explorer, Welle 1 bei hard):**
```
Subject: "[WORKER-MODE] Model: Welle 1 - Explorer E{NN} {fokus}"
ActiveForm: "Exploring {fokus} for knowledge model"
Description: |
  [WORKER-MODE] Welle 1: Explorer E{NN} fuer {NAME}
  FOKUS: {fokus_beschreibung}
  INPUT: .claude/crumbs/{NAME}_crumbs.md, Task.md
  OUTPUT: .claude/analysis/exploration/{NAME}-E{NN}-{fokus}.md
  Frontmatter-Pflicht: wave=exploration, agent=E{NN}, status=final, primaerquelle_gelesen: true
  Aufgabe: Kartographiere den Fokus-Bereich. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

**Wellen-Task-Vorlage fuer _model (Drafter, Welle 2):**
```
Subject: "[WORKER-MODE] Model: Welle 2 - Drafter D{NN} {fokus}"
ActiveForm: "Drafting {fokus} analysis"
Description: |
  [WORKER-MODE] Welle 2: Drafter D{NN} fuer {NAME}
  FOKUS: {fokus_beschreibung}
  # SP-FIX-1: Stille-Post-Schutz (Explorer nur als Kompass)
  INPUT: .claude/crumbs/{NAME}_crumbs.md, models/{NAME}_Model.md PLUS .claude/analysis/exploration/{NAME}-E*.md (NUR als Kompass)
  STILLE-POST-SCHUTZ: Nutze Explorer-Outputs nur zur Scope-Einteilung. Mache DEINE EIGENE Analyse an den Primaerquellen (Crumbs, Model).
  OUTPUT: .claude/analysis/drafts/{NAME}-model-D{NN}-{fokus}.md
  Frontmatter-Pflicht: wave=drafts, agent=D{NN}, status=final, primaerquelle_gelesen: true
  Aufgabe: Tiefenanalyse des Fokus-Bereichs. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

### Task 3: SC_observe (Zyklus {C})

```
Subject: "Observe: Findings sammeln (Zyklus {C})"
ActiveForm: "Collecting observations"
Description: |
  Fuehre /_SC_observe aus.
  Lies .claude/commands/_SC_observe.md fuer Details.

  ACTOR: OBSERVER — sammle Findings OHNE Interpretation.
  Lies Model + vorheriges ERGEBNIS (falls Zyklus > 1).
  Schreibe OBSERVE{C}.md mit Findings.
  Optional: Incidental Findings in _parking-lot.md.

  REVIEW-MODUS (wenn SC_PIPELINE_STATE.modus=REVIEW):
    Vergleiche Code mit Model. Suche Divergenzen:
    - Code-Patterns ohne W{n} (unerklaerter Code)
    - W{n} ohne Code-Entsprechung (nicht implementiert)
    - Quality-Issues (Tests, Naming, Style)
    Findings in post-impl/{NAME}-REVIEW-PROTOKOLL.md, NICHT ins Model.

  Input: models/{NAME}_Model.md, ERGEBNIS{C-1}.md (falls vorhanden)
  Output: analysis/synthese/{NAME}-OBSERVE{C}.md

  Melde dem Team Lead:
    - Anzahl Findings
    - Top 3 Findings (kurz)
    - Incidental Findings: {N} (falls welche)
```

### Task 4: SC_modelMaintain (Zyklus {C})

```
Subject: "Model pflegen (Zyklus {C})"
ActiveForm: "Maintaining model"
Description: |
  Fuehre /_SC_modelMaintain aus.
  Lies .claude/commands/_SC_modelMaintain.md fuer Details.

  ACTOR: MODEL-MAINTAINER — pflege das Model.
  Neue W{n} hinzufuegen, GC durchfuehren, ggf. Split ausfuehren.
  Aktualisiere Kap. 6a (Statusaenderungen).

  REVIEW-MODUS (wenn SC_PIPELINE_STATE.modus=REVIEW):
    Reparatur-Findings → post-impl/{NAME}-REVIEW-PROTOKOLL.md (NICHT ins Model)
    Nur strukturelle Erkenntnisse die das Model AENDERN muessen → als W{n} ins Model
    Bug-Fixes, Refactoring-Hints, Style-Issues → post-impl/ Protokoll

  Input: Model.md, OBSERVE{C}.md, ERGEBNIS{C-1}.md
  Output: Model.md (UPDATE), ggf. Model-Topologie.md
         [REVIEW: + post-impl/{NAME}-REVIEW-PROTOKOLL.md]

  Melde dem Team Lead:
    - Neue W{n}: {N}
    - GC: {N} WIDERLEGT, {N} ELIMINIERT
    - Split: Ja/Nein (falls Trigger)
    - Gesamte W{n}: {total} AKTIV
```

### Task 5: SC_qualityGate (Zyklus {C})

```
Subject: "Quality Gates pruefen (Zyklus {C})"
ActiveForm: "Running quality gates"
Description: |
  Fuehre /_SC_qualityGate aus.
  Lies .claude/commands/_SC_qualityGate.md fuer Details.

  ACTOR: QUALITY-GATE — 5 Gates pruefen (6 bei REVIEW-Modus):
    Gate 1: Battle-Royale (SRS-Trend, Anti-Patterns R-AP1..R-AP5)
           [REVIEW-Modus: DEAKTIVIERT, ersetzt durch Gate 6]
    Gate 2: Kohaesion (W{n}/TC Ratio, Split-Trigger)
    Gate 3: Feature-Abschluss (Coverage-%)
           [REVIEW-Modus: Code-Quality Coverage statt W{n} Coverage]
    Gate 4: Blind-Spot-Detection (T1-T5 Muster)
    Gate 5: Stagnation (Schwellen, ABORT-Empfehlung)
    Gate 6: Post-Implementation-Reality-Check (NUR bei REVIEW-Modus)
           → Code↔Model Konsistenz, W{n} Coverage im Code, unerklaerter Code

  Input: Model.md, OBSERVE{C}.md, ERGEBNIS{C-1}.md, Model-Topologie
  Output: analysis/synthese/{NAME}-QUALITYGATE{C}.md

  WICHTIG: Melde dem Team Lead:
    - Gate 1-5 Ergebnisse (PASS/WARN/FAIL pro Gate)
    - Feature-Coverage: {X}%
    - Stagnation: {zaehler}
    - BSD-Trigger: Ja/Nein (welches T-Muster)
    - Empfehlung: CONTINUE / DONE / ESCALATE
```

### Task 6: SC_hypothese (Zyklus {C})

```
Subject: "Hypothese formulieren (Zyklus {C})"
ActiveForm: "Formulating hypothesis"
Description: |
  Fuehre /_SC_hypothese aus.
  Lies .claude/commands/_SC_hypothese.md fuer Details.

  ACTOR: HYPOTHESEN-FORMULIERER — KREATIVE Phase.
  Sektion 0: GC-Pruefung (PFLICHT ab Zyklus 2).
  Sektion 1: Genau 1 falsifizierbare Hypothese.
  Verifikations-Kriterium V1-V5 + Scope-Deklaration.

  Input: Model.md, QUALITYGATE{C}.md
  Output: analysis/synthese/{NAME}-HYPOTHESEN.md (UPDATE/APPEND)

  Melde dem Team Lead:
    - Hypothese in 1 Satz
    - Scope: {welche Dateien/Module betroffen}
    - Verifikations-Plan: {V1-V5 zusammengefasst}
    - GC: {N} Hypothesen als WIDERLEGT/ELIMINIERT markiert
```

### Task 7: SC_implement (Zyklus {C})

```
Subject: "Implementieren (Zyklus {C})"
ActiveForm: "Implementing changes"
Description: |
  Fuehre /_SC_implement aus.
  Lies .claude/commands/_SC_implement.md fuer Details.

  ACTOR: IMPLEMENTIERER — genau 1 IC pro Durchgang.
  Horizontale Suche: Pattern-Matching im gleichen Layer.
  Soft-Limits: 5 Dateien, 100 LOC.
  Verifikations-Anleitung: 3-5 konkrete Test-Schritte.

  Input: HYPOTHESEN.md, Model.md, Pattern-Library
  Output: Code-Aenderungen, HYPOTHESEN.md (aktualisiert)

  Melde dem Team Lead:
    - IC: {was implementiert wurde}
    - Dateien geaendert: {N}
    - LOC: +{added} / -{removed}
    - Verifikation: {bestanden/fehlgeschlagen}
    - Hypothese: BESTAETIGT / WIDERLEGT / OFFEN
```

### Task 8: SC_ergebnis (Zyklus {C})

```
Subject: "Ergebnis sammeln (Zyklus {C})"
ActiveForm: "Collecting results"
Description: |
  Fuehre /_SC_ergebnis aus.
  Lies .claude/commands/_SC_ergebnis.md fuer Details.

  ACTOR: ERGEBNIS-SAMMLER — DATENBANK-MODUS.
  Drei-Kategorien-Regel:
    ROHDATEN: sammeln, zaehlen, woertlich zitieren
    MECHANISCHE ABLEITUNG: Formeln, Zaehler, boolesche Ausdruecke
    INTERPRETATION: VERBOTEN (gehoert in /_SC_observe)

  SRS-Messung + Widerlegungs-Marker + Stagnations-Check.

  Input: HYPOTHESEN.md, Model.md, vorheriges ERGEBNIS, Logs/Tests
  Output: analysis/synthese/{NAME}-ERGEBNIS{C}.md

  WICHTIG — Melde dem Team Lead AUSFUEHRLICH:
    - SRS-Score: {score}
    - SRS-Trend: {steigend|fallend|stagnierend}
    - Offene W{n}: {N} AKTIV, {M} ZUR_PRUEFUNG
    - Widerlegte W{n}: {N} neu in diesem Zyklus
    - Stagnations-Zaehler: {zaehler}
    - Fortschritt: STARK / SCHWACH / KEINER
    Team Lead entscheidet basierend auf diesen Daten.
```

### Task 9: W_push_temp (strategisch)

```
Subject: "Wissen temporaer pushen (nach Zyklus {C})"
ActiveForm: "Pushing knowledge to RAG"
Description: |
  Fuehre /_W_push_temp auto aus.
  Lies .claude/commands/_W_push_temp.md fuer Details.

  Strategischer Push nach jedem Zyklus:
  → Model, OBSERVE, ERGEBNIS in local_knowledge_{feature_id}
  → Sichert Zwischen-Wissen fuer spaetere W_fetch-Aufrufe

  Input: .claude/models/*.md, .claude/analysis/synthese/*
  Output: RAG local_knowledge_{feature_id}, _manifest.md

  Melde dem Team Lead:
    - Dokumente gepusht: {N}
    - Chunks erstellt: {total}
    - Collection: local_knowledge_{feature_id}
```

### Task 10: W_push_orchestrate (Post-Cycle)

```
Subject: "Wissens-Push orchestrieren"
ActiveForm: "Orchestrating knowledge push"
Description: |
  Fuehre /_W_push_orchestrate {NAME} {difficulty} {ceiling} {floor} aus.
  Lies .claude/commands/_W_push_orchestrate.md fuer Details.

  Eigener Orchestrator fuer den POST-CYCLE Wissens-Push.
  Erstellt eigenes Team, spawnt kurzlebige Agents pro Step:
    1. /_model {NAME} finish (Model konsolidieren)
    2. /_gap {NAME} (Finaler IST vs SOLL Vergleich)
    3. /_W_push_global auto (Quality Gate + RAG push)
    4. /_W_modelSplit {NAME} (Thematisch splitten)
    5. /_W_sync_orchestrate {NAME} {difficulty} --co-work (Vault sync + Co-Working-Links)
    6. /_retrospektive {NAME} (Wissenstransfer)

  Melde dem Team Lead:
    - Alle 6 Steps abgeschlossen
    - GAP: {X}% (IST vs SOLL)
    - RAG: global_knowledge gepusht
    - Vault: synchronisiert
```

### Task 11: Feature finalisieren (Post-Cycle)

```
Subject: "Feature finalisieren"
ActiveForm: "Finalizing feature"
Description: |
  Fuehre /_finish {NAME} aus.
  Lies .claude/commands/_finish.md fuer Details.

  HINWEIS: ImplementationHandOff bereits vorhanden:
    .claude/analysis/synthese/{NAME}-HANDOFF.md
    (erstellt von Team Lead in Phase 3.4 / Task 10)
    → Nutze HandOff fuer Scope-Verifikation und offene Aufgaben.

  HANDOFF-Konsumption und Gate-Antwort (EC-6, W181):
  _I_orchestrate fuehrt Schritt 0.4 aus (HANDOFF-Konsumption):
    0.4a-0.4b: HANDOFF.md lesen (alle 8 Sektionen inkl. SRS-TREND, DISCOVERY-GAPS, ADR-RATIONALE)
    0.4c:      Pflicht-Sektionen pruefen (LOESCHEN, BEHALTEN, ARCHITEKTUR, OFFENE AUFGABEN)
               Fehlen Pflicht-Sektionen → i_gate_response.i_decision: reject_needs_more_sc → ABORT
    0.4d-0.4g: Extraktion in handoff_context + Flags setzen:
               handoff_consumed: true
               handoff_consumed_by: "i-orchestrate-agent"
               i_gate_response.i_decision: accept_start
               i_gate_response.handoff_completeness: OK

  SC-Recovery-Auswertung (Schritt PRE-CYCLE 0.1b, naechster Zyklus falls noetig):
    IF i_sc_return.triggered == true:
      → i_sc_return.sc_recommendations lesen (priorisierte Forschungs-Hinweise)
      → recovery_cycle_count pruefen (Max: 2)
      → pipeline_mode: SC_RECOVERY setzen
      → Neue Zyklen mit w_focus_list aus i_sc_return.refuted_wn

  Offene Items pruefen und User fragen:
    - Parking-Lot [ ] Items
    - Task.md offene ECs/TCs
    - Model W{n} AKTIV/ZUR_PRUEFUNG
  Pro Item: PARKEN / DISCARD / ERLEDIGT (HiL).
  .claude/* Konsistenz-Check.
  Manifest: PHASE=READY.

  Melde dem Team Lead:
    - Geparkt: {N} Items
    - Verworfen: {M} Items
    - Naechste Optionen fuer User
```

---

## QUICK-START

Wenn User sagt "starte Forschungszyklus fuer X":

```
1. /_SC_orchestrate X
2. Team Lead erstellt Team "sc-x" + Tasks 0-9
3. Team Lead spawnt pro Step kurzlebigen Agent sc-{name}-{command}
4. Agents: W_fetch → TaskDef → Model → Observe → ... → Ergebnis
5. Team Lead: SRS-Trend gut? → CONTINUE (neue Zyklus-Tasks)
6. Agents: Observe → ... → Ergebnis (Zyklus 2)
7. Team Lead: Feature-Coverage 90%? → DONE (Post-Cycle Tasks)
8. Agent: /_W_push_orchestrate (model finish → gap → push_global → modelSplit → sync_orchestrate hard --co-work → retro)
9. Agent: /_finish (offene Items, Konsistenz-Check, READY)
10. Team Lead: HiL → User entscheidet ACCEPT/RETRY/PIVOT/ABORT
11. ACCEPT → Cleanup → "Feature '{name}' abgeschlossen"
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| Agent meldet MCP-Fehler | Team Lead: MCP health_check. Bei Timeout: Warte + Retry. |
| Agent stagniert (keine Message >5min) | Team Lead: SendMessage "Status?" an Agent |
| Agent meldet fehlende Datei | Team Lead: Pruefe ob vorheriger Task korrekt war. Ggf. wiederholen. |
| /_SC_implement bricht ab | NON-BLOCKING. Hypothese als "OFFEN" markieren, weiter. |
| Stagnation >= 7.0 | ABORT-Decision. Post-Cycle (verkuerzt) + Retrospektive. |
| Agent crashed | Team Lead: Neuen Agent spawnen (sc-{name}-{command}), gleichen Task zuweisen. |
| Vault nicht erreichbar | Degraded Mode: W_fetch/push nur RAG. ObsidianSync Skip. |
| Budget erschoepft (MCP-Calls) | FORCE-Decision. Mit vorhandenen Ergebnissen weiter. |

---

## LIFECYCLE-INTEGRATION

```
╔══════════════════════════════════════════════════════════════╗
║  VOLLSTAENDIGER FEATURE-LEBENSZYKLUS                        ║
║                                                              ║
║  /_W_fetch ──► /_SC_orchestrate ──► /_I_* Pipeline         ║
║      ↑          (dieser Command)        │                   ║
║      │              │                   │                   ║
║      │         Forschung + Model    Code + Tests            ║
║      │              │                   │                   ║
║      │              ▼                   ▼                   ║
║      │         /_W_push_global    /_I_verify               ║
║      │              │                   │                   ║
║      │              ▼                   ▼                   ║
║      │         /_W_obsidianSync  /_Pre_PR_orchestrate       ║
║      │              │                   │                   ║
║      │              ▼                   ▼                   ║
║      └───── /_W_modelSplit ◄── /_retrospektive             ║
║                                                              ║
║  Forschung (/_SC_*) → liefert Model + Hypothesen           ║
║  Pipeline (/_I_*) → nutzt Model + Hypothesen fuer Code     ║
║  Paper (/_WP_*) → nutzt RAG fuer akademisches Schreiben    ║
║                                                              ║
║  DREI WELTEN, EINE Wissens-Schicht:                         ║
║    _W_fetch (HOLEN) → Arbeit → _W_push (SICHERN)          ║
╚══════════════════════════════════════════════════════════════╝
```

---

## POST-I REVIEW-MODUS (--mode=review, v2.1)

### Zweck

Post-Implementation SC-Zyklen (SC→I→SC) unterscheiden sich fundamental von Discovery-Zyklen:
- Code existiert bereits → kein SRS-Baseline noetig
- Findings sind Reparatur-Findings → gehoeren NICHT ins Haupt-Model
- Gates muessen auf Code-Quality kalibriert sein, nicht auf Wissens-Expansion

**Evidenz:** DCSRE-93 Cycles 5+6 waren inhaltlich wertvoll (IK-Bug, DTO-Kompatibilitaet),
aber hatten keine passende Pipeline-Struktur. Reparatur-Findings trieben ModelBloat.

### Aktivierung

```
/_SC_orchestrate {NAME} [difficulty] [ceiling] [floor] --mode=review
```

### Unterschiede zum Standard-Modus

| Aspekt | Standard (Discovery) | Review (Post-I) |
|--------|---------------------|-----------------|
| Gate 1 (Battle-Royale) | SRS-Tracking aktiv | SRS-Tracking DEAKTIVIERT (kein Baseline) |
| Gate 3 (Feature-Abschluss) | W{n} Coverage | Code-Quality Coverage (Tests, Audit) |
| Gate 6 (Post-Impl-Check) | NICHT AKTIV | AKTIV (Reality-Check gegen Prod-Code) |
| Findings-Pfad | Haupt-Model (models/) | Separater Pfad (analysis/post-impl/) |
| W{n}-Schreibziel | {NAME}_Model.md | {NAME}-REVIEW-PROTOKOLL.md |
| Max Zyklen | easy=3, normal=5, hard=8 | easy=2, normal=3, hard=5 |
| DONE-Bedingung | Feature-Coverage 90% | Alle Review-Items RESOLVED oder DEFERRED |

### Gate 6: Post-Implementation-Reality-Check

Gate 6 ersetzt Gate 1 (Battle-Royale) im Review-Modus:

```markdown
## Gate 6: Post-Implementation-Reality-Check

### Code-Quality Pruefung

| Pruefung | Status | Details |
|----------|--------|---------|
| Tests vorhanden fuer alle Aenderungen | ✅/❌ | {N}/{M} Tests |
| Keine Regressions-Findings | ✅/❌ | {Details} |
| ADR-Konformitaet geprueft | ✅/❌ | {Abweichungen} |
| Model↔Code-Konsistenz | ✅/❌ | {Divergenzen} |

**Empfehlung:** {RESOLVED | REPARATUR NOETIG | DEFERRED}
```

### Separater Findings-Pfad

Review-Findings werden NICHT ins Haupt-Model geschrieben:

```
Standard: .claude/models/{NAME}_Model.md           → W{n} direkt
Review:   .claude/analysis/post-impl/{NAME}-REVIEW-PROTOKOLL.md → Reparatur-Findings
```

Dies verhindert semantischen ModelBloat durch kurzlebige Code-Quality-Findings.
Nur Findings die nach Review als "permanent relevant" bewertet werden,
werden vom Team Lead manuell ins Haupt-Model uebernommen.

### Manifest-Flags (Review-Modus)

```yaml
SC_PIPELINE_STATE:
  modus: REVIEW                    # statt THEORETISCH/IMPLEMENT
  review_target: post-impl         # Separater Pfad
  review_items_total: {N}
  review_items_resolved: {M}
  review_items_deferred: {K}
```

---

## MULTI-WORKER PATTERN (v2.0: kurzlebig)

```
SEQUENTIELLE PHASE:
  Team Lead spawnt pro Step 1 kurzlebigen Agent sc-{name}-{command}
  (W_fetch, taskDef, modelMaintain, qualityGate, hypothese, implement, push_temp)

WELLEN-PHASE (normal/hard):
  N Worker PARALLEL pro Welle:
  - sc-explorer-E{NN} ({floor}): Exploration PARALLEL
  - sc-drafter-D{NN} ({middle}): Drafts PARALLEL
  - sc-synthese ({ceiling}): Synthese (1 Agent)
  run_in_background: true fuer Welle 1+2

PROZESSBEGLEITEND:
  Separate Sync-Worker fuer W_sync_orchestrate (siehe 3.3a)
```

---

ARGUMENTS: $ARGUMENTS
