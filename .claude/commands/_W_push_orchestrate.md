# /_W_push_orchestrate - Team Lead Wissens-Push-Orchestrierung

```yaml
status: active
version: 1.1.0
created: 2026-02-21
updated: 2026-02-26
op: KnowledgePush
phase: Meta
type: orchestration
chain_position: meta
difficulty_scaling: true
team_based: true
changelog: |
  v1.0: Initialer Entwurf. Extrahiert POST-CYCLE Wissens-Push
        aus SC_orchestrate (Tasks 10-15) in eigenen Orchestrator.
        Gleiche Architektur: KURZLEBIG_PROMPT, Team-basiert.
        6 Steps sequentiell: model finish → gap → push_global →
        modelSplit → sync_orchestrate hard --co-work → retrospektive.
        DRY: SC, I, WP koennen alle den gleichen Push nutzen.
  v1.1: Pattern-Extraktion (EC-6/E6, Global RAG Transfer).
        Task 3 (push_global) erweitert: exportierbare W{n} identifizieren
        und mit source_feature-Attribut in global_knowledge schreiben.
        Verhindert Valley-of-Death (Feature-Wissen stirbt in lokaler Collection).
```

---

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_W_push_orchestrate                                      ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    .claude/analysis/_manifest.md  (NAME, Phase, Zyklen-Info)        ║
║    .claude/models/{NAME}_Model.md (Feature-Model)                    ║
║    .claude/analysis/synthese/{NAME}-*.md  (Synthese-Dokumente)      ║
║    .claude/wissen/*_Wissen.md     (Wissens-Dokumente)               ║
║                                                                      ║
║  SCHREIBT (Team Lead direkt):                                        ║
║    .claude/analysis/_manifest.md  (nach jedem Step aktualisieren)   ║
║                                                                      ║
║  PRODUZIERT (via Agents):                                            ║
║    .claude/models/{NAME}_Model.md           (via /_model finish)    ║
║    .claude/analysis/synthese/{NAME}-GAP.md  (via /_gap)             ║
║    RAG global_knowledge                     (via /_W_push_global)   ║
║    .claude/wissen/{NAME}_GlobalExport.md    (via /_W_push_global)   ║
║    .claude/models/{NAME}_*_Model.md         (via /_W_modelSplit)    ║
║    Vault-Dateien                            (via /_W_obsidianSync)  ║
║    .claude/analysis/synthese/{NAME}-RETROSPEKTIVE.md (via /_retro)  ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    - Team Lead fuehrt KEINE Commands selbst aus                     ║
║    - 1 Agent = 1 Command = stirbt danach (KURZLEBIG_PROMPT)        ║
║    - Kein Agent spawnt Sub-Agents (W7-Constraint)                   ║
║    - Alle 6 Steps sequentiell (keine Wellen)                        ║
║    - Nach retrospektive: TeamDelete (kein HiL hier)                 ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

```
+======================================================================+
| META-COMMAND: /_W_push_orchestrate                                    |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU - die ausfuehrende Claude-Instanz)              |
| AGENTS: Kurzlebige Single-Command-Agents (1 Agent = 1 Command)       |
|                                                                        |
| ZWECK: Orchestriert den POST-CYCLE Wissens-Push nach Feature-Ende.    |
|        6 Steps sequentiell: Model konsolidieren, Gap pruefen,         |
|        Wissen global pushen, Model splitten, Vault syncen,            |
|        Retrospektive durchfuehren.                                    |
|                                                                        |
| PRINZIP: 1 Agent = 1 Command = stirbt danach (KURZLEBIG_PROMPT).    |
|          State lebt in DOKUMENTEN (Vertraegen), nicht im Agenten.     |
|          Kein Worker-Loop, kein TaskList-Polling.                      |
|          Team Lead spawnt pro Step 1 Agent, wartet auf Ergebnis,     |
|          spawnt naechsten Agent.                                      |
|                                                                        |
| WARUM EIGENER ORCHESTRATOR:                                           |
|   - SC_orchestrate POST-CYCLE (Tasks 10-15) war INLINE definiert     |
|   - I_orchestrate braucht die gleiche Sequenz am Feature-Ende        |
|   - WP_orchestrate kann Kapitel-Wissen damit pushen                  |
|   - DRY: 6 Steps nur 1x definiert statt 3x kopiert                  |
|                                                                        |
| FLOW (6 Steps, alle sequentiell):                                     |
|   model finish → gap → push_global → modelSplit →                   |
|   sync_orchestrate hard --co-work → retrospektive → TeamDelete       |
|                                                                        |
| KEINE WELLEN: Alle Steps sind sequentiell (1 Agent nach dem anderen) |
| KEIN HiL: Team Lead raeumt auf und gibt Kontrolle an Parent zurueck  |
+======================================================================+
```

---

## Aufruf

```
/_W_push_orchestrate {NAME} [difficulty] [ceiling] [floor]
```

**Parameter:**

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `NAME` | (PFLICHT) | String | Feature-/Forschungsname |
| `difficulty` | normal | easy, normal, hard | Steuert obsidianSync Tiefe |
| `ceiling` | sonnet | haiku, sonnet, opus | Hoechstes Modell fuer Agents |
| `floor` | (nicht genutzt) | — | Konfigurierbar, aber nicht verwendet — alle 6 Steps sind sequentiell |

**Beispiele:**
```
/_W_push_orchestrate OmniCommand                     → normal, sonnet
/_W_push_orchestrate TwoTierBridge hard opus haiku    → hard obsidianSync
/_W_push_orchestrate QuickFix easy sonnet sonnet      → easy, minimal
```

**Voraussetzungen:**
- Model existiert: `.claude/models/{NAME}_Model.md`
- Manifest existiert: `.claude/analysis/_manifest.md`
- Mindestens 1 Zyklus durchlaufen (Synthese-Dokumente vorhanden)

**Modell-Zuordnung (vereinfacht, keine Wellen):**

| Rolle | easy | normal | hard |
|-------|------|--------|------|
| Team Lead | DU (Opus) | DU (Opus) | DU (Opus) |
| Agents (alle Steps) | 1 {ceiling} | 1 {ceiling} | 1 {ceiling} |

**KEINE Wellen:** Alle 6 Steps sind sequentiell mit je 1 Agent.
Difficulty beeinflusst nur obsidianSync-Tiefe (easy/normal/hard).

---

## GLOBALE PARAMETER (/_param Override)

Lies `.claude/analysis/_manifest.md` und suche nach GLOBAL_* Feldern.
Falls gesetzt, ueberschreiben sie die lokalen Parameter-Defaults:

| Manifest-Feld | Wirkung |
|---|---|
| `GLOBAL_DIFFICULTY` | Ueberschreibt lokalen `difficulty` Default |
| `GLOBAL_CEILING` | Kappt lokales ceiling: `effektiv = min(lokal, GLOBAL_CEILING)` |
| `GLOBAL_FLOOR` | Hebt lokalen floor an | Akzeptiert aber **nicht genutzt** — alle 6 Steps sind sequentiell |

**Berechnung:**
Hierarchie: opus=3, sonnet=2, haiku=1
IF GLOBAL_DIFFICULTY gesetzt UND != "(nicht gesetzt)": difficulty = GLOBAL_DIFFICULTY
IF GLOBAL_CEILING gesetzt UND != "(nicht gesetzt)":    ceiling = min(ceiling, GLOBAL_CEILING)
IF GLOBAL_FLOOR gesetzt UND != "(nicht gesetzt)":      floor = max(floor, GLOBAL_FLOOR)
Validierung: ceiling >= floor (sonst ceiling = floor + Warning ausgeben)

**Falls KEINE GLOBAL_* Felder gesetzt:** Lokale Defaults gelten unveraendert.

**Strukturelle Ausnahme (6-Step-Sequenz):**
_W_push_orchestrate arbeitet mit 6 semantisch abhaengigen Steps:
model finish → gap → push_global → modelSplit → sync → retrospektive.
Jeder Step MUSS auf dem Ergebnis des Vorgaengers aufbauen.
floor (Explorer-Qualitaet) ist nicht relevant, da keine Exploration-Wellen existieren.
ceiling wirkt: Alle Steps verwenden {ceiling} als Modell.

---

## PHASE 1: TEAM SETUP

### Schritt 1.1: Kontext laden

Lies folgende Dateien:
1. `.claude/analysis/_manifest.md` → NAME, Phase, Zyklen-Info
2. `.claude/models/{NAME}_Model.md` → Model existiert?
3. `.claude/analysis/synthese/{NAME}-*.md` → Synthese-Dokumente vorhanden?
4. `.claude/wissen/*_Wissen.md` → Wissens-Dokumente vorhanden?

**Validierung:**
- Model MUSS existieren → Sonst STOPP mit Meldung
- Manifest MUSS existieren → Sonst STOPP mit Meldung

### Schritt 1.1b: Out-of-Pipeline Check

**ZWECK:** Erkennt Arbeit die nach `PHASE=DONE` entstanden ist, aber noch nicht
durch einen W_push konsolidiert wurde. Verhindert stilles Wissensleck (W68).

**Vorbedingung:** Schritt 1.1 hat Manifest und Model bereits geladen.

```
PHASE_CHECK:
  Lies Manifest-PHASE aus Schritt 1.1
  Falls PHASE != DONE und PHASE != READY:
    → Kein Out-of-Pipeline moeglich → SKIP (weiter mit Schritt 1.2)
```

**4 Checks (alle unabhaengig, jeder einzeln genuegt als Signal):**

```
CHECK 1: Manifest-PHASE-Check
  Lies Manifest: PHASE
  Lies Manifest: DONE_TIMESTAMP (falls vorhanden, gesetzt von _SC_orchestrate 3.4)
  Lies Manifest: letzter RAG-Push-Eintrag (Sektion "RAG Push Status")
  Referenz-Zeitpunkt:
    Falls DONE_TIMESTAMP vorhanden → nutze DONE_TIMESTAMP (praezise)
    Sonst → nutze Datei-Timestamp von _manifest.md (Workaround)
  Falls PHASE=DONE aber es gibt Manifest-Eintraege (SC-Cycle, modelMaintain,
  etc.) die NACH dem Referenz-Zeitpunkt liegen:
    → SIGNAL: "Manifest hat Eintraege nach DONE_TIMESTAMP"

CHECK 2: Commands-Dir-Check
  Lies Frontmatter aller Dateien in .claude/commands/*.md
  Vergleiche Feld "updated:" oder "created:" mit letztem RAG-Push-Datum
  Falls mindestens 1 Command-Datei neuer als letzter RAG-Push:
    → SIGNAL: "{N} Command-Dateien neuer als letzter Push"

CHECK 3: Model-Versions-Check
  Lies Model-Frontmatter: version (z.B. "4.4")
  Lies Manifest RAG-Push-Status: zuletzt gepushte Model-Version
  Falls Model-Version > gepushte Version:
    → SIGNAL: "Model {version} neuer als gepushte Version {pushed}"

CHECK 4: Git-Commit-Check (OPTIONAL, benoetigt Bash-Zugriff)
  Falls Bash verfuegbar:
    git log --oneline --after="{letzter-push-datum}" -- .claude/ src/
  Falls Commits gefunden:
    → SIGNAL: "{N} Commits seit letztem Push"
  Falls Bash NICHT verfuegbar:
    → SKIP (Checks 1-3 kompensieren)
```

**Auswertung:**

```
Falls KEIN Signal aus allen 4 Checks:
  → Kein Alarm. Direkt weiter mit Schritt 1.2 (Team erstellen).

Falls mindestens 1 Signal:
  → Diagnose-Report anzeigen:

  ╔══════════════════════════════════════════════════════════════╗
  ║  OUT-OF-PIPELINE ALARM: {NAME}                              ║
  ╠══════════════════════════════════════════════════════════════╣
  ║  MANIFEST: PHASE={PHASE}, aber neue Arbeit erkannt           ║
  ║                                                              ║
  ║  Checks die ausgeloest haben:                               ║
  ║  [{x/ }] Manifest-Check: {Detail oder "keine"}              ║
  ║  [{x/ }] Commands-Dir:   {Detail oder "keine"}              ║
  ║  [{x/ }] Model-Check:    {Detail oder "keine"}              ║
  ║  [{x/ }] Git-Check:      {Detail oder "uebersprungen"}      ║
  ║                                                              ║
  ║  Letzter RAG-Push: {Datum} (Model {Version})                ║
  ║  Aktueller Stand:  Model {Version}, {N} Signale             ║
  ╚══════════════════════════════════════════════════════════════╝

  → AskUserQuestion:
    "Out-of-Pipeline Arbeit erkannt. Wissen ist nicht gesichert.
     Was soll geschehen?"

    A) "Extended SC-Zyklus (THEORETISCH)"
       → Empfehlung: /_SC_orchestrate {NAME} (ohne -I Flag)
       → Fuer: Vollstaendige Wissens-Konsolidierung
       → Gegen: Aufwaendig wenn Code bereits fertig

    B) "Direkter Push (minimal)"
       → Sofort weiter mit Schritt 1.2 (normaler W_push-Flow)
       → Fuer: Schnell, Wissen gesichert
       → Gegen: Kein Observe/Hypothese-Dokument

    C) "Ignorieren (RISKY)"
       → Manifest-Warnung schreiben, weiter mit Schritt 1.2
       → Fuer: Weitermachen ohne Unterbrechung
       → Gegen: Wissen geht verloren

  Ausfuehrung:
    Option A: STOPP. Melde Parent/User:
              "Empfehlung: /_SC_orchestrate {NAME} ausfuehren."
              W_push wird NICHT fortgesetzt.
    Option B: Weiter mit Schritt 1.2 (Team erstellen).
    Option C: Schreibe in Manifest:
              "[WARN] Out-of-Pipeline Alarm ignoriert am {Datum}"
              Weiter mit Schritt 1.2 (Team erstellen).
```

### Schritt 1.2: Team erstellen

```
TeamCreate:
  team_name: "wp-{name}"
  description: "Knowledge Push - {name}"
```

### Schritt 1.3: Tasks erstellen (6 Tasks, alle sequentiell)

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 1 | Model finalisieren | /_model {NAME} finish | - | Finalizing model |
| 2 | Gap-Analyse (final) | /_gap {NAME} | Task 1 | Running final gap analysis |
| 3 | Wissen global pushen | /_W_push_global auto | Task 2 | Pushing verified knowledge globally |
| 4 | Model splitten | /_W_modelSplit {NAME} | Task 3 | Splitting model thematically |
| 5 | Obsidian Sync (via sync_orchestrate) | /_W_sync_orchestrate {NAME} {difficulty} --co-work | Task 4 | Syncing to Obsidian Vault with co-work links |
| 6 | Retrospektive | /_retrospektive {NAME} | Task 5 | Running retrospective |

### Schritt 1.4: Ersten Agent spawnen

```
Task tool:
  name: "wp-{name}-model-finish"
  subagent_type: "general-purpose"
  model: "{ceiling}"
  team_name: "wp-{name}"
  mode: "bypassPermissions"
  prompt: [KURZLEBIG_PROMPT fuer /_model {NAME} finish]
```

---

## PHASE 2: KURZLEBIG_PROMPT (Single-Command-Agent)

Pro Step spawnt Team Lead 1 kurzlebigen Agent.
Jeder Agent bekommt diesen minimalen Prompt:

```
Du bist ein Single-Command-Agent fuer den Wissens-Push.
Agent-Name: wp-{name}-{command}
Team: wp-{name}

═══ DEIN AUFTRAG ═══

Genau 1 Command ausfuehren, dann fertig.

Command:     {COMMAND_PATH} {NAME} {ARGS}
Task-ID:     {TASK_ID}

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

---

## PHASE 3: TEAM LEAD STEUERUNG (Aktives Spawning)

### 3.1 Agent-Messages empfangen und naechsten Agent spawnen

Team Lead (DU) empfaengst Agent-Messages automatisch.
Pro Message:

```
1. Agent meldet: "{COMMAND} {NAME}: Summary"
2. Team Lead prueft: Passt das Ergebnis?
3. Bei Erfolg: Naechsten Agent spawnen (naechster Step)
4. Bei Problem: Neuen Agent spawnen mit Korrektur-Kontext
5. Nach retrospektive: → Phase 3.2 (Cleanup)
```

**Pipeline-Sequenz (Team Lead spawnt aktiv):**
```
wp-{name}-model-finish
  → wp-{name}-gap
    → wp-{name}-push-global
      → wp-{name}-modelSplit
        → wp-{name}-syncOrchestrate
          → wp-{name}-retrospektive
```

### 3.2 Nach Retrospektive (Agent meldet "Retrospektive fertig")

Team Lead raeumt auf:

```
1. Keine aktiven Agents (kurzlebig, bereits terminiert)
2. TeamDelete
3. _manifest.md aktualisieren: PUSH_STATUS=COMPLETED
4. Melde Parent-Orchestrator (oder User):
   "Wissens-Push '{NAME}' abgeschlossen.
    Model: finalisiert + gesplittet
    RAG: global_knowledge gepusht
    Vault: synchronisiert ({difficulty}, Co-Working-Links gesetzt)
    Retrospektive: dokumentiert"
```

**KEIN HiL hier** — der Parent-Orchestrator (SC/I/WP) oder /_finish
uebernimmt die User-Interaktion.

---

## TASK-BESCHREIBUNGEN (Vorlagen fuer TaskCreate)

### Task 1: Model finalisieren

```
Subject: "Model finalisieren"
ActiveForm: "Finalizing model"
Description: |
  Fuehre /_model {NAME} finish aus.
  Lies .claude/commands/_model.md fuer Details.

  Model konsolidieren: W{n} sortieren, GC aufraeumen,
  Zusammenfassung schreiben. Finale Version des Models.

  Input: .claude/models/{NAME}_Model.md
  Output: .claude/models/{NAME}_Model.md (UPDATE, finalisiert)

  Melde dem Team Lead:
    - W{n}: {confirmed} BESTAETIGT, {refuted} WIDERLEGT, {open} OFFEN
    - GC durchgefuehrt: {N} Eintraege bereinigt
    - Model-Status: finalisiert
```

### Task 2: Gap-Analyse (final)

```
Subject: "Gap-Analyse (final)"
ActiveForm: "Running final gap analysis"
Description: |
  Fuehre /_gap {NAME} aus.
  Lies .claude/commands/_gap.md fuer Details.

  Finaler IST vs SOLL Vergleich.
  Wie viel vom urspruenglichen Ziel wurde erreicht?

  Input: .claude/models/{NAME}_Model.md, .claude/Task.md
  Output: .claude/analysis/synthese/{NAME}-GAP.md

  Melde dem Team Lead:
    - GAP: {X}% (IST vs SOLL)
    - Offene Punkte: {N}
    - Abgedeckte ECs: {M}/{total}
```

### Task 3: Wissen global pushen (mit Pattern-Extraktion)

```
Subject: "Wissen global pushen (mit Pattern-Extraktion)"
ActiveForm: "Extracting patterns and pushing verified knowledge globally"
Description: |
  Fuehre /_W_push_global auto aus.
  Lies .claude/commands/_W_push_global.md fuer Details.

  **ZUSAETZLICH (v1.1 Pattern-Extraktion, E6):**
  VOR dem Push: Identifiziere "exportierbare" W{n} im finalisierten Model.

  Exportierbar = generalisierbar (Pattern-Wahrheiten, Architecture Decisions):
    ✅ Architektur-Patterns (z.B. "3-stufige Mapping-Chain", "Separate Provider")
    ✅ EF Core Best Practices (z.B. "Multi-Level ThenInclude", "LV-Filter Self-Check")
    ✅ Workflow-Learnings (z.B. "Entity-Readiness vor Pipeline-Start")
    ❌ Feature-spezifische Details (z.B. "EinrichtungsdetailDto hat Feld X")
    ❌ Implementierungs-Artefakte (z.B. "Datei XY Zeile 42 geaendert")

  Export-Kriterien (Filter bevor RAG-Push):
    → Nur W{n} mit w-confirmed=true exportieren (ungeprueft = kein Transfer)
    → Nur W{n} deren scope NICHT "feature-internal" ist
    → Ausschluss: W{n} die explizit Entitaeten/DTOs/Felder des Features nennen
    → Ausschluss: temporaere Workarounds (w-type=workaround oder aehnlich)

  Fuer jede exportierbare W{n}:
    → Schreibe als Chunk in global_knowledge MIT Attribut:
      source_feature: {NAME}
      w_id: W{n}
      export_type: pattern|architecture|workflow
    → Damit findet W_fetch bei Folge-Features diese Patterns

  NACH dem RAG-Push: Schreibe Export-Summary-Datei:
    Pfad: .claude/wissen/{NAME}_GlobalExport.md
    Inhalt:
      ---
      source_feature: {NAME}
      export_date: {DATUM}
      exported_count: {N}
      total_wn: {M}
      ---
      # GlobalExport: {NAME}

      ## Exportierte W{n} ({N} von {M})
      | W{n} | Titel | export_type |
      |------|-------|-------------|
      | W{n} | {Titel} | {pattern|architecture|workflow} |
      ...

      ## Nicht exportiert (Begruendung)
      - W{n}: feature-internal (Entitaet XY)
      - W{n}: w-confirmed=false
      ...

  Quality Gate fuer alle Wissens-Dokumente.
  Push in global_knowledge Collection.

  Input: .claude/models/*.md (finalisiert), .claude/wissen/*.md,
         .claude/analysis/synthese/*.md
  Output: RAG global_knowledge, _manifest.md,
          .claude/wissen/{NAME}_GlobalExport.md

  Melde dem Team Lead:
    - Exportierbare W{n}: {N} identifiziert (von {M} gesamt), w-confirmed+non-internal
    - Dokumente gepusht: {K}
    - Quality Gate: {passed}/{total} bestanden
    - Collection: global_knowledge
    - GlobalExport: .claude/wissen/{NAME}_GlobalExport.md erstellt
```

### Task 4: Model splitten

```
Subject: "Model splitten"
ActiveForm: "Splitting model thematically"
Description: |
  Fuehre /_W_modelSplit {NAME} aus.
  Lies .claude/commands/_W_modelSplit.md fuer Details.

  Feature-Model in thematische Teile aufsplitten.
  Wiederverwendbare Wissens-Bloecke extrahieren.

  Input: .claude/models/{NAME}_Model.md
  Output: .claude/models/{NAME}_*_Model.md (thematische Splits)

  Melde dem Team Lead:
    - Splits erstellt: {N}
    - Themen: {liste}
    - Vault-Kandidaten: {M} Dateien
```

### Task 5: Obsidian Sync

```
Subject: "Obsidian Sync ({difficulty}, Post-Cycle)"
ActiveForm: "Syncing to Obsidian Vault"
Description: |
  Fuehre /_W_sync_orchestrate {NAME} {difficulty} --co-work aus.
  Lies .claude/commands/_W_sync_orchestrate.md fuer Details.
  (Delegiert intern an /_W_obsidianSync + G-COWORK Guard fuer Co-Working-Links)

  Schwierigkeit: {difficulty} (Post-Cycle).
  Synthese-Dokumente + gesplittete Models in Obsidian Vault
  transportieren. Frontmatter, Wiki-Links, Chain-Erkennung,
  Mermaid, Feature-Note.

  HINWEIS: Wird NACH modelSplit ausgefuehrt, damit die
  gesplitteten Models ebenfalls in den Vault gelangen.

  Input: .claude/models/*.md, .claude/analysis/synthese/*.md,
         .claude/wissen/*.md
  Output: Vault-Dateien (synchronisiert)

  Melde dem Team Lead:
    - Dateien synchronisiert: {N}
    - Neue Vault-Dateien: {M}
    - Aktualisierte Vault-Dateien: {K}
    - Chain-Links: {L}
```

### Task 6: Retrospektive

```
Subject: "Retrospektive"
ActiveForm: "Running retrospective"
Description: |
  Fuehre /_retrospektive {NAME} aus.
  Lies .claude/commands/_retrospektive.md fuer Details.

  Feature-Abschluss: Was funktioniert, was nicht?
  Wissenstransfer dokumentieren.
  Anti-Patterns und Learnings extrahieren.

  Input: .claude/analysis/_manifest.md,
         .claude/models/{NAME}_Model.md,
         .claude/analysis/synthese/{NAME}-*.md
  Output: .claude/analysis/synthese/{NAME}-RETROSPEKTIVE.md

  Melde dem Team Lead:
    - Learnings: {N} Punkte
    - Anti-Patterns: {M} identifiziert
    - Architektur-Entscheidungen: {K} dokumentiert
    - "Retrospektive abgeschlossen"
```

---

## ZUSAMMENFASSUNG: Sequenz-Diagramm

```
Team Lead                    Agent (wp-{name}-{cmd})
    │                              │
    ├─ TeamCreate ─────────────►   │
    ├─ TaskCreate (Tasks 1-6) ──►  │
    │                              │
    │  ═══ WISSENS-PUSH ═══       │
    │                              │
    ├─ Spawn model-finish ──────►  │
    │                              ├─ T1: /_model {NAME} finish
    │  ◄── "Model final" ─────────┤  (Agent stirbt)
    │                              │
    ├─ Spawn gap ───────────────►  │
    │                              ├─ T2: /_gap {NAME}
    │  ◄── "GAP: X%" ─────────────┤  (Agent stirbt)
    │                              │
    ├─ Spawn push-global ───────►  │
    │                              ├─ T3: /_W_push_global auto
    │  ◄── "Global gepusht" ───────┤  (Agent stirbt)
    │                              │
    ├─ Spawn modelSplit ────────►  │
    │                              ├─ T4: /_W_modelSplit {NAME}
    │  ◄── "Model gesplittet" ─────┤  (Agent stirbt)
    │                              │
    ├─ Spawn syncOrchestrate ───►  │
    │                              ├─ T5: /_W_sync_orchestrate {NAME} {difficulty} --co-work
    │  ◄── "Vault synced + co-work" ┤  (Agent stirbt)
    │                              │
    ├─ Spawn retrospektive ─────►  │
    │                              ├─ T6: /_retrospektive {NAME}
    │  ◄── "Retro fertig" ─────────┤  (Agent stirbt)
    │                              │
    ├─ TeamDelete                  │
    ├─ Melde Parent: "Push done"   │
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| Agent meldet MCP-Fehler | Team Lead: MCP health_check. Bei Timeout: Warte + Retry. |
| Agent stagniert (keine Message >5min) | Team Lead: SendMessage "Status?" an Agent |
| Agent meldet fehlende Datei | Team Lead: Pruefe ob vorheriger Task korrekt war. Ggf. wiederholen. |
| Vault nicht erreichbar | Degraded Mode: obsidianSync Skip, nur RAG push. |
| push_global Quality Gate FAIL | Team Lead: Melde Parent mit WARN. Weiter mit modelSplit. |
| Agent crashed | Team Lead: Neuen Agent spawnen, gleichen Task zuweisen. |

---

## LIFECYCLE-INTEGRATION

```
╔══════════════════════════════════════════════════════════════════╗
║  WER RUFT /_W_push_orchestrate AUF?                             ║
║                                                                  ║
║  /_SC_orchestrate  → POST-CYCLE (nach DONE-Decision)           ║
║  /_I_orchestrate   → Post-Pipeline (nach Pre_PR)               ║
║  /_WP_orchestrate  → ACCEPT (Kapitel-Wissen sichern)           ║
║  /_finish          → NICHT (/_finish kommt NACH dem Push)       ║
║  User direkt       → Manueller Push (z.B. nach Abbruch)        ║
║                                                                  ║
║  FLOW:                                                           ║
║    Orchestrator → /_W_push_orchestrate → /_finish              ║
║                   (Wissen sichern)       (Aufraumen)            ║
╚══════════════════════════════════════════════════════════════════╝
```

---

ARGUMENTS: $ARGUMENTS
