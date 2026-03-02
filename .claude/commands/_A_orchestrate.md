# /_A_orchestrate - Team Lead Analyse-Orchestrierung

```yaml
status: active
version: 2.0.0
created: 2026-02-19
updated: 2026-02-21
op: AnalysisPipeline
phase: Meta
type: orchestration
chain_position: meta
difficulty_scaling: true
team_based: true
changelog: |
  v2.0: Wellen-Skalierung eingefuehrt (EC-C, Stateless Agents Redesign).
        floor-Parameter hinzugefuegt.
        Skalierungs-Tabelle: 9-5-1 / 5-3-1 / 1 (Explorer/Drafter/Synthese).
        Wellen-Tasks fuer _model und _spec (bei normal/hard).
        Wellen-Prompt-Vorlagen fuer Explorer/Drafter/Synthese.
        W_fetch, taskDefinition, gap bleiben sequentiell (1 Agent).
  v1.0: Initialer Entwurf. Lineare Analyse-Pipeline.
        Pile of Mud → taskDef → model → spec → gap.
        Gleiche Team-Architektur wie /_SC_orchestrate + /_I_orchestrate.
        Kurzlebige Single-Command-Agents (R4, W7-compliant).
        Optional: Resync-Modus (modelMaintain statt model).
```

---

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_A_orchestrate                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    .claude/analysis/_manifest.md  (Startpunkt, NAME, Phase)         ║
║    .claude/Task.md                (optional, falls schon vorhanden)  ║
║    .claude/models/{NAME}_Model.md (optional, fuer Resync-Modus)     ║
║    .claude/pileOfMud/             (Rohmaterial: US, Figma, Bilder)   ║
║    .claude/crumbs/                (falls schon vorhanden)            ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    .claude/analysis/_manifest.md  (nach jedem Schritt aktualisieren)║
║    (alle anderen Outputs via Worker-Tasks)                           ║
║                                                                      ║
║  AUSGABEN DURCH WORKER:                                              ║
║    .claude/Task.md                       (via _taskDefinition)       ║
║    .claude/crumbs/{NAME}_crumbs.md       (via _taskDefinition)       ║
║    .claude/models/{NAME}_Model.md        (via _model / _modelMaint)  ║
║    .claude/analysis/synthese/{NAME}-SPEC.md  (via _spec)             ║
║    .claude/analysis/synthese/{NAME}-GAP.md   (via _gap)              ║
║                                                                      ║
║  HAUPTPRODUKT: SPEC                                                  ║
║    (Zentrales Artefakt dieser Phase: Spezifikation + Gap-Analyse)    ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

```
+======================================================================+
| META-COMMAND: /_A_orchestrate                                        |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU - die ausfuehrende Claude-Instanz)              |
| AGENTS: Kurzlebige Single-Command-Agents (1 Agent = 1 Command)       |
|                                                                        |
| ZWECK: Lineare Analyse-Pipeline die aus Rohmaterial (Pile of Mud)     |
|        saubere Artefakte baut: Task.md, Model, Spec, Gap.            |
|        KEIN Zyklus (kein observe/hypothese/implement/ergebnis).       |
|        Baut die Wissensbasis auf die /_SC_orchestrate und             |
|        /_I_orchestrate als VORAUSSETZUNG brauchen.                    |
|                                                                        |
| ZWEI MODI:                                                             |
|   FRESH:  Pile of Mud → taskDef → model → spec → gap (alles neu)    |
|   RESYNC: → modelMaintain → spec (update) → gap (Delta pruefen)     |
|                                                                        |
| PRINZIP: EIN Command pro Agent. KEIN Buendeln.                       |
|          Agents sind kurzlebig: spawn → 1 Command → shutdown (R4).   |
|          Kein Agent spawnt Sub-Agents (W7-Constraint).                |
|          Team Lead fuehrt KEINE Commands selbst aus (R2).             |
|                                                                        |
| FLOW:                                                                  |
|   FRESH:  [W_fetch] → taskDef → model → spec → gap → [HiL]         |
|   RESYNC: [diff] → modelMaintain → [spec] → gap → [HiL]            |
+======================================================================+
```

---

## Aufruf

```
/_A_orchestrate [name] [modus] [difficulty] [ceiling] [floor]
```

**Parameter:**

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `name` | (PFLICHT) | String | Feature-/Analyse-Name |
| `modus` | fresh | fresh, resync | Fresh = von Null. Resync = Model aktualisieren |
| `difficulty` | normal | easy, normal, hard | Steuert Agent-Modelle und Tiefe |
| `ceiling` | sonnet | haiku, sonnet, opus | Hoechstes Modell fuer Agents |
| `floor` | haiku | haiku, sonnet | Niedrigstes Modell (Exploration-Wellen) |

**Beispiele:**
```
/_A_orchestrate DCSRE-93                          → fresh, normal, sonnet, haiku
/_A_orchestrate DCSRE-93 resync                   → resync, normal, sonnet, haiku
/_A_orchestrate ServiceHostDI fresh hard opus haiku → fresh, hard, opus, haiku
/_A_orchestrate QuickCheck resync easy haiku haiku  → resync, easy, haiku, haiku
```

**Modell-Zuordnung und Skalierung:**

| Rolle | easy | normal | hard |
|-------|------|--------|------|
| Team Lead | DU (Opus) | DU (Opus) | DU (Opus) |
| Synthese (Welle 3) | 1 {ceiling} solo | 1 {ceiling} | 1 {ceiling} |
| Drafter (Welle 2) | --- | 3 {middle} PARALLEL | 5 {middle} PARALLEL |
| Explorer (Welle 1) | --- | 5 {floor} PARALLEL | 9 {floor} PARALLEL |
| Sequentielle Steps | 1 {ceiling} | 1 {ceiling} | 1 {ceiling} |

{middle} = sonnet wenn ceiling=opus, haiku wenn ceiling=sonnet, haiku wenn ceiling=haiku

**WELLEN-PRINZIP:** Innerhalb einer Welle laufen ALLE Agents PARALLEL.
Nur die NAECHSTE Welle wird durch Abschluss der vorherigen Welle blockiert.

**Wellen-Commands (A_orchestrate):** _model, _spec
**Sequentielle Commands:** _W_fetch, _taskDefinition, _SC_modelMaintain, _gap

WICHTIG: Team Lead spawnt ALLE Wellen-Tasks PARALLEL. Agent spawnt NICHTS.
- hard:   9 {floor} (Explorer PARALLEL) → 5 {middle} (Drafter PARALLEL) → 1 {ceiling} (Synthese)
- normal: 5 {floor} (Explorer PARALLEL) → 3 {middle} (Drafter PARALLEL) → 1 {ceiling} (Synthese)
- easy:   1 {ceiling} (Synthese solo, Team Lead spawnt 1 Agent)

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

## PHASE 1: MODUS-ERKENNUNG

### Schritt 1.1: Kontext laden

Lies folgende Dateien (falls vorhanden):
1. `.claude/analysis/_manifest.md` → aktueller Stand, NAME, Phase
2. `.claude/Task.md` → existierende Aufgabendefinition
3. `.claude/models/{NAME}_Model.md` → existierendes Model
4. `.claude/pileOfMud/` → Rohmaterial vorhanden?
5. `.claude/crumbs/{NAME}_crumbs.md` → existierende Crumbs

### Schritt 1.2: Modus bestimmen

**Falls `modus` explizit angegeben:** Nutze diesen.

**Falls `modus` nicht angegeben — Auto-Detect:**

```
IF Model existiert UND Task.md existiert:
  → RESYNC (Model + Task.md schon da, nur aktualisieren)
ELSE IF pileOfMud/ nicht leer ODER Task.md fehlt:
  → FRESH (von Null aufbauen)
ELSE:
  → Frage User via AskUserQuestion
```

### Schritt 1.3: Git-Baseline erfassen (fuer Resync)

```bash
# Aktuellen Commit-Hash erfassen
git rev-parse HEAD → {CURRENT_COMMIT}

# Falls Model existiert UND last_sync_commit im Frontmatter:
#   git diff {last_sync_commit}..HEAD --stat → {DIFF_SINCE_MODEL}
# Sonst:
#   Kein Diff moeglich (erstes Mal)
```

**Ausgabe:**
```
Modus: {FRESH|RESYNC}
Aktueller Commit: {CURRENT_COMMIT}
Model last_sync: {last_sync_commit | "NICHT VORHANDEN"}
Diff seit Model: {N Dateien | "N/A"}
```

---

## PHASE 2: TEAM SETUP

### Schritt 2.1: Team erstellen

```
TeamCreate:
  team_name: "a-{name}"
  description: "Analysis Pipeline - {name} ({modus})"
```

### Schritt 2.2: Tasks erstellen (abhaengig vom Modus)

**FRESH-Modus:**

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 1 | Wissen holen (Vault + RAG) | /_W_fetch {NAME} | - | Fetching knowledge |
| 2 | Aufgabe definieren | /_taskDefinition {NAME} | Task 1 | Defining task |
| 3 | Model aufbauen | /_model {NAME} {difficulty} | Task 2 | Building model |
| 4 | Spec schreiben | /_spec {NAME} {difficulty} | Task 3 | Writing specification |
| 5 | Gap-Analyse | /_gap {NAME} | Task 4 | Running gap analysis |

**Hinweis:** Tasks 3 (model) und 4 (spec) werden bei normal/hard als Wellen-Tasks aufgesplittet (siehe unten).

**WELLEN-TASKS fuer Wellen-Commands (Team Lead erstellt N Tasks statt 1):**

Tasks 3 (model) und 4 (spec) werden nach difficulty aufgesplittet.
Team Lead erstellt Wellen-Tasks NACH Abschluss des vorherigen sequentiellen Tasks:

| difficulty | Wellen-Tasks (Beispiel fuer Task 3: model) | blocked_by |
|------------|---------------------------------------------|------------|
| easy | 3a: Model Synthese (solo) | Task 2 |
| normal | 3a-3e: Explorer E01-E05 (Welle 1 PARALLEL) → 3f-3h: Drafter D01-D03 (Welle 2 PARALLEL) → 3i: Synthese | Task 2 → 3a-3e → 3f-3h |
| hard | 3a-3i: Explorer E01-E09 (Welle 1 PARALLEL) → 3j-3n: Drafter D01-D05 (Welle 2 PARALLEL) → 3o: Synthese | Task 2 → 3a-3i → 3j-3n |

Analog fuer Task 4 (spec): 4a-4e (Explorer) → 4f-4h (Drafter) → 4i (Synthese) bei normal.

**Wellen-Task-Erkennung:** Team Lead schreibt "[WORKER-MODE] Welle N:" in Task-Beschreibung.
Agent liest Task-Beschreibung und fuehrt NUR die zugewiesene Welle aus.

**RESYNC-Modus:**

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 1 | Model aktualisieren | /_SC_modelMaintain {NAME} | - | Updating model |
| 2 | Spec pruefen/updaten | /_spec {NAME} normal | Task 1 | Updating specification |
| 3 | Gap-Analyse (Delta) | /_gap {NAME} | Task 2 | Running gap analysis |

**RESYNC ohne Spec-Aenderung (easy):**

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 1 | Model aktualisieren | /_SC_modelMaintain {NAME} | - | Updating model |
| 2 | Gap-Analyse (Delta) | /_gap {NAME} | Task 1 | Running gap analysis |

---

## PHASE 3: AGENT-PROMPTS

### Fresh-Modus Agent-Prompt (pro Task)

```
Du bist ein Single-Command-Agent fuer die Analyse-Pipeline.
Agent-Name: a-{name}-{command}
Team: a-{name}

═══ DEIN AUFTRAG ═══

Genau 1 Command ausfuehren, dann fertig.

Command:     /{COMMAND} {NAME} {DIFFICULTY}
Task-ID:     {TASK_ID}
Projekt:     {PROJEKT_PFAD}

═══ SCHRITTE ═══

1. Lies Command-Datei: .claude/commands/{COMMAND}.md
2. Fuehre Command aus.
3. TaskUpdate {TASK_ID} status=completed
4. SendMessage an "team-lead":
   "{COMMAND} {NAME}: [2-3 Saetze Summary]"

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- NUR dieser eine Command, dann fertig
- Absolute Pfade fuer alles: {PROJEKT_PFAD}/...
```

### Wellen-Task-Vorlage fuer Explorer (Welle 1)

```
Subject: "[WORKER-MODE] {Command}: Welle 1 - Explorer E{NN} {fokus}"
ActiveForm: "Exploring {fokus}"
Description: |
  [WORKER-MODE] Welle 1: Explorer E{NN} fuer {NAME}
  FOKUS: {fokus_beschreibung}
  INPUT: .claude/crumbs/{NAME}_crumbs.md, Task.md
  OUTPUT: .claude/analysis/exploration/{NAME}-E{NN}-{fokus}.md
  Frontmatter-Pflicht: wave=exploration, agent=E{NN}, status=final, primaerquelle_gelesen: true
  Aufgabe: Kartographiere den Fokus-Bereich. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

### Wellen-Task-Vorlage fuer Drafter (Welle 2)

```
Subject: "[WORKER-MODE] {Command}: Welle 2 - Drafter D{NN} {fokus}"
ActiveForm: "Drafting {fokus}"
Description: |
  [WORKER-MODE] Welle 2: Drafter D{NN} fuer {NAME}
  FOKUS: {fokus_beschreibung}
  # SP-FIX-3: Stille-Post-Schutz (Explorer nur als Kompass)
  INPUT: .claude/crumbs/{NAME}_crumbs.md, Task.md PLUS .claude/analysis/exploration/{NAME}-E*.md (NUR als Kompass)
  STILLE-POST-SCHUTZ: Nutze Explorer-Outputs nur zur Scope-Einteilung. Mache DEINE EIGENE Analyse an den Primaerquellen (Crumbs, Task).
  OUTPUT: .claude/analysis/drafts/{NAME}-{command}-D{NN}-{fokus}.md
  Frontmatter-Pflicht: wave=drafts, agent=D{NN}, status=final, primaerquelle_gelesen: true
  Aufgabe: Tiefenanalyse des Fokus-Bereichs. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

### Wellen-Task-Vorlage fuer Synthese (Welle 3)

```
Subject: "[WORKER-MODE] {Command}: Welle 3 - Synthese"
ActiveForm: "Synthesizing {command} results"
Description: |
  [WORKER-MODE] Welle 3: Synthese fuer {NAME}
  # SP-FIX-4: Stille-Post-Schutz (Drafts nur als Kompass)
  INPUT: .claude/crumbs/{NAME}_crumbs.md, Task.md, exploration/{NAME}-E*.md PLUS .claude/analysis/drafts/{NAME}-{command}-D*.md (NUR als Kompass)
  STILLE-POST-SCHUTZ: Drafts sind Inspiration, NICHT Faktenquelle. Verifiziere JEDE Aussage an Primaerquellen (Crumbs, Task).
  OUTPUT: {final artifact} (z.B. models/{NAME}_Model.md oder analysis/synthese/{NAME}-SPEC.md)
  Frontmatter-Pflicht: wave=synthese, status=final, primaerquelle_gelesen: true
  Aufgabe: Synthetisiere alle Drafts zu finalem Artefakt. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

### Resync-Modus: modelMaintain Agent-Prompt

```
Du bist ein Single-Command-Agent fuer Model-Resync.
Agent-Name: a-{name}-modelMaintain
Team: a-{name}

═══ DEIN AUFTRAG ═══

Model aktualisieren basierend auf Code-Aenderungen seit letztem Sync.

Command:     /_SC_modelMaintain {NAME} {DIFFICULTY}
Task-ID:     {TASK_ID}
Projekt:     {PROJEKT_PFAD}

═══ RESYNC-KONTEXT ═══

Letzter Sync-Commit: {LAST_SYNC_COMMIT}
Aktueller Commit: {CURRENT_COMMIT}
Diff seit Model-Erstellung:
{DIFF_STAT}

WICHTIG: Lies den git diff um zu verstehen was sich geaendert hat.
Aktualisiere das Model mit den neuen Erkenntnissen:
- Neue W{n} fuer neue Code-Aenderungen
- GC fuer Annahmen die durch Code widerlegt wurden
- Kap. 6a aktualisieren

Falls KEIN OBSERVE-File existiert (out-of-cycle):
→ Nutze den git diff als Input STATT OBSERVE-File.
→ Der Diff IST deine Observation.

Nach Update: Setze Model-Frontmatter:
  last_sync_commit: {CURRENT_COMMIT}
  last_sync_date: {HEUTE}

═══ SCHRITTE ═══

1. Lies .claude/commands/_SC_modelMaintain.md
2. Lies git diff {LAST_SYNC_COMMIT}..{CURRENT_COMMIT}
3. Fuehre modelMaintain aus (Diff als Input statt OBSERVE)
4. Update Model-Frontmatter (last_sync_commit)
5. TaskUpdate {TASK_ID} status=completed
6. SendMessage an "team-lead": Summary

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- NUR dieser eine Command, dann fertig
```

---

## PHASE 4: TEAM LEAD STEUERUNG

### 4.1 Agent-Messages empfangen

Team Lead empfaengt Messages automatisch. Pro Agent:

```
1. Agent meldet: "{COMMAND} {NAME}: Summary"
2. Team Lead prueft: Passt das Ergebnis?
3. Bei Erfolg: Naechsten Agent spawnen (naechster Task)
4. Bei Problem: Neuen Agent spawnen mit Korrektur-Kontext
```

### 4.1a Wellen-Orchestrierung (bei normal/hard)

Team Lead orchestriert Wellen-Commands (model, spec) in 3 Schritten:

1. **Welle 1 (Explorer):** Spawne N Explorer PARALLEL (run_in_background: true)
   → Warte auf ALLE Explorer
2. **Welle 2 (Drafter):** Spawne M Drafter PARALLEL (run_in_background: true)
   → Warte auf ALLE Drafter
3. **Welle 3 (Synthese):** Spawne 1 Synthese-Agent (foreground)
   → Warte auf Synthese
4. Naechster sequentieller Task (z.B. spec nach model, gap nach spec)

Pro Wellen-Agent:
```
Task tool:
  name: "a-{name}-{command}-E{NN}" | "a-{name}-{command}-D{NN}" | "a-{name}-{command}-synthese"
  subagent_type: "general-purpose"
  model: "{floor}" (Welle 1) | "{middle}" (Welle 2) | "{ceiling}" (Welle 3)
  team_name: "a-{name}"
  mode: "bypassPermissions"
  run_in_background: true (Welle 1+2), false (Welle 3)
  prompt: [Wellen-Prompt, siehe Phase 3]
```

### 4.2 Nach letztem Task (Gap-Analyse)

Team Lead liest Gap-Ergebnis und meldet dem User:

```
AskUserQuestion:
  header: "{NAME}"
  question: "Analyse-Pipeline '{name}' ({modus}) abgeschlossen.

    Modus: {FRESH|RESYNC}
    Tasks: {N} abgeschlossen
    Model: v{VERSION} ({M} W{n})
    Spec: {STATUS}
    Gap: {PERCENTAGE}% (IST vs SOLL)
    {Falls RESYNC: Drift seit Commit {LAST_SYNC}: {DIFF_FILES} Dateien}

    Naechster Schritt?"

  options:
    - label: "ACCEPT"
      description: "Artefakte sind gut, weiter (→ /_SC_orchestrate oder /_I_orchestrate)"
    - label: "REFINE"
      description: "Spec/Model nochmal verfeinern (neuer Durchlauf)"
    - label: "SC-CYCLE"
      description: "Direkt in Forschungszyklus starten (/_SC_orchestrate)"
    - label: "I-PIPELINE"
      description: "Direkt in Implementierung starten (/_I_orchestrate)"
```

### 4.3 User-Decision verarbeiten

**Bei ACCEPT:**
```
1. Team aufloesen (TeamDelete)
2. Manifest aktualisieren: phase=ANALYSIS_DONE
3. Melde User: "Artefakte bereit. Starte /_SC_orchestrate oder /_I_orchestrate."
```

**Bei REFINE:**
```
1. Frage User: "Was soll verfeinert werden?" (AskUserQuestion Freitext)
2. Erstelle neue Tasks (modelMaintain → spec → gap)
3. Spawne Agents fuer die neuen Tasks
```

**Bei SC-CYCLE:**
```
1. Team aufloesen (TeamDelete)
2. Manifest aktualisieren: phase=SC_CYCLE_READY
3. Melde User: "Starte jetzt /_SC_orchestrate {NAME} {difficulty} {ceiling}"
```

**Bei I-PIPELINE:**
```
1. Team aufloesen (TeamDelete)
2. Manifest aktualisieren: phase=I_PIPELINE_READY
3. Melde User: "Starte jetzt /_I_orchestrate {NAME}"
```

---

## PHASE 5: GIT COMMIT-TRACKING

### Model-Frontmatter (neues Feature)

Nach JEDEM Model-Update (ob via `/_model` oder `/_SC_modelMaintain`)
wird das Model-Frontmatter erweitert:

```yaml
# Im Model-Header (nach version, vor Kapitel 1):
sync:
  last_sync_commit: "abc123def"
  last_sync_date: "2026-02-19"
  last_sync_command: "/_model"  # oder "/_SC_modelMaintain"
  diff_since_last: 0  # Anzahl geaenderter Dateien seit letztem Sync
```

**Wer schreibt das:**
- `/_model` → setzt initial (nach Model-Erstellung)
- `/_SC_modelMaintain` → aktualisiert (nach jedem Maintain)
- `/_A_orchestrate` → liest (fuer Resync-Modus Diff-Berechnung)

---

## ZUSAMMENFASSUNG: Sequenz-Diagramme

### FRESH-Modus

```
Team Lead                    Agents                          User
    │                              │                          │
    ├─ TeamCreate ─────────────►   │                          │
    ├─ Modus: FRESH ───────────►   │                          │
    │                              │                          │
    ├─ Spawn a-{n}-wfetch ──────►  │  (1 Agent)
    │  ◄── "Wissen geholt" ───────┤
    │                              │
    ├─ Spawn a-{n}-taskDef ──────► │  (1 Agent)
    │  ◄── "Task definiert" ──────┤
    │                              │
    │  ═══ MODEL (Wellen bei normal/hard) ═══
    ├─ Spawn N Explorer ──────────► │  (PARALLEL)
    │  ◄── "Explorer fertig" ─────┤
    ├─ Spawn M Drafter ───────────► │  (PARALLEL)
    │  ◄── "Drafter fertig" ──────┤
    ├─ Spawn 1 Synthese ──────────► │
    │  ◄── "Model v1.0" ──────────┤
    │                              │
    │  ═══ SPEC (Wellen bei normal/hard) ═══
    ├─ Spawn N Explorer ──────────► │  (PARALLEL)
    │  ◄── "Explorer fertig" ─────┤
    ├─ Spawn M Drafter ───────────► │  (PARALLEL)
    │  ◄── "Drafter fertig" ──────┤
    ├─ Spawn 1 Synthese ──────────► │
    │  ◄── "Spec geschrieben" ────┤
    │                              │
    ├─ Spawn a-{n}-gap ──────────► │  (1 Agent)
    │  ◄── "Gap: X%" ────────────┤
    │                              │                          │
    ├─ AskUserQuestion ──────────────────────────────────►   │
    │  ◄── ACCEPT/REFINE/SC/I ───────────────────────────────┤
    │                              │                          │
    ├─ TeamDelete                  │                          │
    ├─ "Artefakte bereit" ────────────────────────────────►  │
```

### RESYNC-Modus

```
Team Lead                    Agents                          User
    │                              │                          │
    ├─ TeamCreate ─────────────►   │                          │
    ├─ Modus: RESYNC ──────────►   │                          │
    ├─ git diff {sync}..HEAD ──►   │                          │
    │                              │                          │
    ├─ Spawn a-{n}-maintain ─────► │                          │
    │  ◄── "Model v{N+1}" ───────┤                          │
    │                              │                          │
    ├─ [Spawn a-{n}-spec] ────────► │  (falls Drift gross)   │
    │  ◄── "Spec updated" ───────┤                          │
    │                              │                          │
    ├─ Spawn a-{n}-gap ──────────► │                          │
    │  ◄── "Gap: X%" ────────────┤                          │
    │                              │                          │
    ├─ AskUserQuestion ──────────────────────────────────►   │
    │  ◄── ACCEPT/REFINE/SC/I ───────────────────────────────┤
    │                              │                          │
    ├─ TeamDelete                  │                          │
    ├─ "Resync fertig" ──────────────────────────────────►   │
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| pileOfMud leer (FRESH) | Agent erstellt Task.md aus Kontext + User-Beschreibung |
| Model fehlt (RESYNC) | Fallback auf FRESH-Modus (User informieren) |
| Agent crashed | Team Lead spawnt neuen Agent fuer gleichen Task |
| Spec bereits aktuell (RESYNC) | Skip Spec-Task, direkt zu Gap |
| Git nicht verfuegbar | Resync ohne Diff (degraded: modelMaintain ohne git context) |
| MCP-Fehler bei W_fetch | Skip W_fetch, weiter mit taskDef (degraded mode) |

---

## LIFECYCLE-INTEGRATION

```
╔══════════════════════════════════════════════════════════════╗
║  WO LEBT /_A_orchestrate IM GESAMTBILD?                     ║
║                                                              ║
║  /_A_orchestrate (FRESH)                                     ║
║      │                                                       ║
║      ├── Pile of Mud → Task.md + Crumbs                     ║
║      ├── Model v1.0                                          ║
║      ├── Spec                                                ║
║      └── Gap → Entscheidung:                                ║
║           ├── /_SC_orchestrate (Forschung vertiefen)        ║
║           └── /_I_orchestrate (direkt implementieren)       ║
║                                                              ║
║  /_A_orchestrate (RESYNC)                                    ║
║      │                                                       ║
║      ├── git diff → modelMaintain (Model updaten)           ║
║      ├── Spec updaten (falls noetig)                        ║
║      └── Gap → Entscheidung:                                ║
║           ├── Weiter implementieren (Drift aufgeloest)      ║
║           └── SC-Cycle (tiefere Analyse noetig)             ║
║                                                              ║
║  EINORDNUNG:                                                 ║
║                                                              ║
║  /_A_orchestrate → /_SC_orchestrate → /_I_orchestrate       ║
║  (Wissensbasis)    (Forschung)        (Implementierung)     ║
║                                                              ║
║  /_A_orchestrate (RESYNC) kann JEDERZEIT aufgerufen werden: ║
║  - Zwischen SC-Zyklen                                        ║
║  - Zwischen I-Pipeline Stufen                                ║
║  - Nach Out-of-Pipeline Arbeit                               ║
║  - Nach Feature-Merge von anderem Branch                     ║
╚══════════════════════════════════════════════════════════════╝
```

---

## QUICK-START

**Neues Feature analysieren:**
```
1. Material in .claude/pileOfMud/ legen (US, Figma, Screenshots)
2. /_A_orchestrate DCSRE-93
3. Pipeline: W_fetch → taskDef → model → spec → gap
4. User entscheidet: SC-Cycle oder I-Pipeline
```

**Model resyncen nach Out-of-Pipeline Arbeit:**
```
1. /_A_orchestrate DCSRE-93 resync
2. Pipeline: git diff → modelMaintain → gap
3. User entscheidet: weiter implementieren oder SC-Cycle
```

**Model + Spec resyncen:**
```
1. /_A_orchestrate DCSRE-93 resync normal opus haiku
2. Pipeline: git diff → modelMaintain → spec → gap
3. User entscheidet: weiter oder vertiefen
```
