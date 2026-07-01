# /_PO_orchestrate - Team Lead PO-Pipeline-Orchestrierung

```yaml
status: active
version: 1.1.0
created: 2026-02-23
updated: 2026-02-28
op: ProductOwnerPipeline
phase: Meta
type: orchestration
chain_position: meta
difficulty_scaling: true
team_based: true
```

---

```
+======================================================================+
| META-COMMAND: /_PO_orchestrate                                       |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU - die ausfuehrende Claude-Instanz)              |
| WORKER: Kurzlebige Single-Command-Agents (1 Agent = 1 Command)       |
|         + 3 Rollen-Agents PARALLEL (PO, PE, ARC bei Epic/Story)     |
|                                                                        |
| ZWECK: Orchestriert den Paper-to-UserStory Tandem-Prozess.            |
|        3 Rollen (PO, PE, ARC) analysieren gemeinsam akademische       |
|        Paper und uebersetzen Forschungsergebnisse in:                  |
|          → Priorisierte Epics (mit Evidenz + Constraints)             |
|          → User Stories (mit Akzeptanzkriterien aus Forschung)        |
|          → Obsidian-Vault-Integration (verlinkt, getaggt)             |
|                                                                        |
| TANDEM-ROLLEN:                                                        |
|   PO  (Product Owner)      = Nutzernutzen, Priorisierung              |
|   PE  (Principal Engineer) = Forschungsvalidierung, Evidenz           |
|   ARC (Architect)          = Technische Machbarkeit, Constraints      |
|   CXO (optional)           = Budget, Komplexitaet, Delivery           |
|                                                                        |
| PRINZIP: 1 Agent = 1 Command = stirbt danach (KURZLEBIG_PROMPT).    |
|          State lebt in DOKUMENTEN, nicht im Agenten.                  |
|          Tandem-Phase: PO + PE parallel → ARC sequential.            |
|          HiL-Pause nach Synthese.                                     |
+======================================================================+
```

---

## Aufruf

```
/_PO_orchestrate [paper_path] [difficulty] [ceiling] [floor]
```

**Parameter:**

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `paper_path` | . | Pfad/URL | Paper oder Projektordner mit Quellen |
| `difficulty` | normal | easy, normal, hard | Steuert Rollen-Tiefe und Iterations |
| `ceiling` | sonnet | haiku, sonnet, opus | Hoechstes Modell (Synthese) |
| `floor` | haiku | haiku, sonnet | Niedrigstes Modell (Exploration) |

**Skalierungs-Tabelle:**

| Rolle | easy | normal | hard |
|-------|------|--------|------|
| PO Agents | 1 | 2 | 3 |
| PE Agents | 1 | 2 | 3 |
| ARC Agents | 1 | 1 | 2 |
| Synthese | 1 {ceiling} | 1 {ceiling} | 1 {ceiling} |

---

## GLOBALE PARAMETER (/_param Override)

Lies `{VAULT}/_manifest.md` und suche nach GLOBAL_* Feldern.
Falls gesetzt, ueberschreiben sie die lokalen Parameter-Defaults:

| Quelle | Wirkung |
|---|---|
| `_session_params.md` | 4 Parameter: HiL, difficulty, ceiling, floor |

**Berechnung:**
Hierarchie: opus=3, sonnet=2, haiku=1
params = lies("_session_params.md")
difficulty = params.difficulty
ceiling    = min(ceiling, params.ceiling)
floor      = max(floor, params.floor)
Validierung: ceiling >= floor (sonst ceiling = floor + Warning ausgeben)
middle = sonnet wenn ceiling=opus, sonnet wenn ceiling=sonnet, haiku wenn ceiling=haiku

---

## PIPELINE-PHASEN

### Phase 0: TEAM-SETUP (Team Lead, kein Agent-Spawn)

```
TeamCreate:
  team_name: "po-{name}"
  description: "PO-Pipeline - {name}"
```

Tasks erstellen (TaskCreate pro Pipeline-Step):
```
T0: paperRead      → Team Lead direkt (kein Spawn)
T1a: epicExtract-PO → PO-Agent(s) PARALLEL
T1b: epicExtract-PE → PE-Agent(s) PARALLEL (gleichzeitig mit T1a)
T2: archConstrain   → ARC-Agent(s) SEQUENTIAL (nach T1)
T3: storyDraft      → PO + PE + ARC PARALLEL
T4a: valueScore     → PO + PE + ARC PARALLEL (nach T3)
T4b: depMap         → ARC-Agent SEQUENTIAL (nach T4a)
T5: synthesis       → 1x Synthese-Agent {ceiling} (nach T4)
T6: obsidianSync    → 1x Sync-Agent (nach HiL ACCEPT)
```

---

### Phase 1: SETUP

**T0: paperRead** (Team Lead direkt, kein Spawn)

Team Lead liest Paper/Quellen selbst und clustert Insights.
```
Kein Agent-Spawn. Team Lead liest paper_path direkt.
Output: Internes Insight-Clustering fuer T1-Prompts.
```

**T1: epicExtract** (PO + PE PARALLEL)

Team Lead spawnt PO-Agent(s) und PE-Agent(s) gleichzeitig:

```
FUER JEDEN PO-Agent (1..{po_count} je difficulty):
  Agent tool:
    name: "po-{name}-PO-{NN}"
    subagent_type: "general-purpose"
    model: "{floor}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: true              # PARALLEL mit PE
    prompt: |
      [PO-Agent KURZLEBIG_PROMPT, siehe unten]
      PHASE: T1-epicExtract
      AUFTRAG: Extrahiere Epics aus Paper mit Nutzernutzen-Fokus.
      Paper-Insights: {INSIGHTS_AUS_T0}
      Output: output/po/epics-PO-{NN}.json
      TaskUpdate {TASK_ID} status=completed wenn fertig.

FUER JEDEN PE-Agent (1..{pe_count} je difficulty):
  Agent tool:
    name: "po-{name}-PE-{NN}"
    subagent_type: "general-purpose"
    model: "{floor}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: true              # PARALLEL mit PO
    prompt: |
      [PE-Agent KURZLEBIG_PROMPT, siehe unten]
      PHASE: T1-epicExtract
      AUFTRAG: Validiere Paper-Insights mit Forschungsevidenz.
      Paper-Insights: {INSIGHTS_AUS_T0}
      Output: output/po/epics-PE-{NN}.json
      TaskUpdate {TASK_ID} status=completed wenn fertig.
```

**T2: archConstrain** (ARC SEQUENTIAL, nach T1)

Erst NACH Abschluss ALLER T1-Agents (PO + PE):

```
FUER JEDEN ARC-Agent (1..{arc_count} je difficulty):
  Agent tool:
    name: "po-{name}-ARC-{NN}"
    subagent_type: "general-purpose"
    model: "{middle}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: false             # SEQUENTIAL (wartet auf T1)
    prompt: |
      [ARC-Agent KURZLEBIG_PROMPT, siehe unten]
      PHASE: T2-archConstrain
      AUFTRAG: Constraints pro Epic einarbeiten.
      Lies PO-Epics: output/po/epics-PO-*.json
      Lies PE-Validierung: output/po/epics-PE-*.json
      Output: output/po/epics-constrained.json
      TaskUpdate {TASK_ID} status=completed wenn fertig.
```

---

### Phase 2: USER STORY PHASE

**T3: storyDraft** (PO + PE + ARC PARALLEL)

Team Lead spawnt alle 3 Rollen parallel fuer User Story Drafts:

```
PO-Agent (primary drafter):
  Agent tool:
    name: "po-{name}-story-PO"
    subagent_type: "general-purpose"
    model: "{middle}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: true              # PARALLEL
    prompt: |
      [PO-Agent KURZLEBIG_PROMPT, siehe unten]
      PHASE: T3-storyDraft
      AUFTRAG: Formuliere User Stories aus constrained Epics.
      Lies: output/po/epics-constrained.json
      Format: "Als [User] moechte ich [Feature], damit [Nutzen]"
      Output: output/po/stories-draft-PO.json
      TaskUpdate {TASK_ID} status=completed wenn fertig.

PE-Agent (evidence annotator):
  Agent tool:
    name: "po-{name}-story-PE"
    subagent_type: "general-purpose"
    model: "{middle}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: true              # PARALLEL
    prompt: |
      [PE-Agent KURZLEBIG_PROMPT, siehe unten]
      PHASE: T3-storyDraft
      AUFTRAG: Annotiere User Stories mit Forschungsevidenz.
      Lies: output/po/epics-constrained.json
      Output: output/po/stories-annotated-PE.json
      TaskUpdate {TASK_ID} status=completed wenn fertig.

ARC-Agent (constraint annotator):
  Agent tool:
    name: "po-{name}-story-ARC"
    subagent_type: "general-purpose"
    model: "{middle}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: true              # PARALLEL
    prompt: |
      [ARC-Agent KURZLEBIG_PROMPT, siehe unten]
      PHASE: T3-storyDraft
      AUFTRAG: Annotiere User Stories mit technischen Constraints.
      Lies: output/po/epics-constrained.json
      Output: output/po/stories-annotated-ARC.json
      TaskUpdate {TASK_ID} status=completed wenn fertig.
```

**T4a: valueScore** (PO + PE + ARC PARALLEL, nach T3)

Erst NACH Abschluss ALLER T3-Agents:

```
PO-Agent (value scoring):
  Agent tool:
    name: "po-{name}-score-PO"
    subagent_type: "general-purpose"
    model: "{middle}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: true              # PARALLEL
    prompt: |
      [PO-Agent KURZLEBIG_PROMPT, siehe unten]
      PHASE: T4a-valueScore
      AUFTRAG: PO_value Score 1-10 pro Story.
      Lies: output/po/stories-draft-PO.json + stories-annotated-PE.json + stories-annotated-ARC.json
      Output: output/po/scores-PO.json
      TaskUpdate {TASK_ID} status=completed wenn fertig.

PE-Agent (evidence scoring):
  Agent tool:
    name: "po-{name}-score-PE"
    subagent_type: "general-purpose"
    model: "{middle}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: true              # PARALLEL
    prompt: |
      [PE-Agent KURZLEBIG_PROMPT, siehe unten]
      PHASE: T4a-valueScore
      AUFTRAG: PE_evidence Score 1-10 pro Story.
      Lies: output/po/stories-draft-PO.json + stories-annotated-PE.json + stories-annotated-ARC.json
      Output: output/po/scores-PE.json
      TaskUpdate {TASK_ID} status=completed wenn fertig.

ARC-Agent (complexity scoring):
  Agent tool:
    name: "po-{name}-score-ARC"
    subagent_type: "general-purpose"
    model: "{middle}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: true              # PARALLEL
    prompt: |
      [ARC-Agent KURZLEBIG_PROMPT, siehe unten]
      PHASE: T4a-valueScore
      AUFTRAG: ARC_complexity Score 1-10 + ARC_constraints Liste pro Story.
      Lies: output/po/stories-draft-PO.json + stories-annotated-PE.json + stories-annotated-ARC.json
      Output: output/po/scores-ARC.json
      TaskUpdate {TASK_ID} status=completed wenn fertig.
```

**T4b: depMap** (ARC SEQUENTIAL, nach T4a)

Erst NACH Abschluss ALLER T4a-Agents:

```
ARC-Agent (dependency mapping):
  Agent tool:
    name: "po-{name}-depmap"
    subagent_type: "general-purpose"
    model: "{ceiling}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: false             # SEQUENTIAL (wartet auf T4a)
    prompt: |
      [ARC-Agent KURZLEBIG_PROMPT, siehe unten]
      PHASE: T4b-depMap
      AUFTRAG: Kartiere Abhaengigkeiten zwischen Stories.
      Lies: output/po/scores-PO.json + scores-PE.json + scores-ARC.json
      Wende TANDEM-ENTSCHEIDUNGSMATRIX an (IMPLEMENT/RESEARCH_FIRST/SPIKE/PARK/NEGOTIATE).
      Output: output/po/dependency-graph.json
      TaskUpdate {TASK_ID} status=completed wenn fertig.
```

---

### Phase 3: SYNTHESE

**T5: synthesis** (1x Synthese-Agent {ceiling}, nach T4b)

```
Synthese-Agent:
  Agent tool:
    name: "po-{name}-synthesis"
    subagent_type: "general-purpose"
    model: "{ceiling}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: false             # blockierend (Team Lead wartet)
    prompt: |
      Du bist der Synthese-Agent in der PO-Pipeline.
      Team: po-{name}

      AUFTRAG: Konsolidiere alle Rollen-Outputs zu finalem Dokument.

      LIES (Primaerquellen — KEIN Stille-Post):
        - output/po/stories-draft-PO.json (User Stories)
        - output/po/stories-annotated-PE.json (Evidenz-Annotationen)
        - output/po/stories-annotated-ARC.json (Constraint-Annotationen)
        - output/po/scores-PO.json (PO_value Scores)
        - output/po/scores-PE.json (PE_evidence Scores)
        - output/po/scores-ARC.json (ARC_complexity Scores)
        - output/po/dependency-graph.json (Abhaengigkeiten + Entscheidungen)

      SCHREIBE:
        - output/po/user-stories.json (finale User Stories mit allen Scores)
        - output/po/epics.json (priorisierte Epic-Liste)
        - output/po/synthesis-report.md (finales Konsens-Dokument)

      TANDEM-ENTSCHEIDUNGSMATRIX anwenden:
        IMPLEMENT:      PO_value >= 7 AND PE_evidence >= 6 AND ARC_complexity <= 7
        RESEARCH_FIRST: PE_evidence < 4
        SPIKE:          ARC_complexity > 8
        PARK:           PO_value < 4
        NEGOTIATE:      Grenzbereich

      TaskUpdate {TASK_ID} status=completed wenn fertig.
      SendMessage an "team-lead": "Synthese {name}: {N} Stories, {M} Epics. Status: {IMPLEMENT/PARK/...}."
```

---

### Phase 4: HiL-PAUSE

```
AskUserQuestion:
  "{name} - PO-Pipeline Ergebnis

  Epics: {N}
  User Stories: {M}
  IMPLEMENT: {n1}  |  RESEARCH_FIRST: {n2}
  SPIKE: {n3}      |  PARK: {n4}
  NEGOTIATE: {n5}

  Siehe: output/po/synthesis-report.md

  Naechster Schritt?"

  Optionen:
    ACCEPT  → Weiter zu Vault Sync
    RETRY   → Neuer Zyklus (zurueck zu T1)
    ABORT   → Pipeline abbrechen
```

### Phase 5: VAULT SYNC (nur bei ACCEPT)

**T6: obsidianSync**

```
Sync-Agent:
  Agent tool:
    name: "po-{name}-vaultSync"
    subagent_type: "general-purpose"
    model: "{floor}"
    team_name: "po-{name}"
    mode: "bypassPermissions"
    run_in_background: false             # blockierend
    prompt: |
      Du bist der Vault-Sync-Agent in der PO-Pipeline.
      Team: po-{name}

      AUFTRAG: Synchronisiere PO-Outputs nach Obsidian Vault.

      LIES:
        - output/po/epics.json
        - output/po/user-stories.json
        - output/po/dependency-graph.json
        - output/po/synthesis-report.md

      SYNC nach obsidian/ (via /_PO_obsidianSync oder direkt):
        - 1 Epic-Note pro Epic (verlinkt, getaggt)
        - 1 Story-Note pro User Story (verlinkt zu Epic)
        - Dependency-Graph als Mermaid-Diagramm

      TaskUpdate {TASK_ID} status=completed wenn fertig.
      SendMessage an "team-lead": "Vault Sync {name}: {N} Notes erstellt."
```

---

## KURZLEBIG_PROMPT (Rollen-Agents)

### PO-Agent (Product Owner)

```
Du bist PO-Agent (Product Owner) in der PO-Pipeline.
Team: po-pipeline-{session}

DEINE ROLLE:
  Product Owner - du vertrittst den Nutzer und bewertest Wert.

FOKUS:
  - Welchen konkreten Nutzernutzen bringt jedes Feature?
  - Wie priorisierst du aus Business-Sicht?
  - Was wuerde ein echter User als "wertvoll" empfinden?
  - Formuliere User Stories: "Als [User] moechte ich [Feature], damit [Nutzen]"
  - Bewerte: PO_value Score 1-10 pro Epic/Story

KEIN technisches Deep-Dive. Kein Architektur-Denken.
NUR Nutzernutzen, NUR User-Perspektive.
```

### PE-Agent (Principal Engineer)

```
Du bist PE-Agent (Principal Engineer) in der PO-Pipeline.
Team: po-pipeline-{session}

DEINE ROLLE:
  Principal Engineer - du validierst Forschungsevidenz und theoretische Machbarkeit.

FOKUS:
  - Was sagt die Forschung (RAG) ueber dieses Feature?
  - Ist es theoretisch machbar laut aktuellem Forschungsstand?
  - Welche Papers/Studien belegen das?
  - Bewerte: PE_evidence Score 1-10 (1=keine Evidenz, 10=starke Evidenz)
  - Annotiere User Stories mit Zitaten und Research-Backing

MCP: research_query fuer Evidenz-Suche.
NUR Forschungsevidenz. Kein Business-Denken. Kein Architektur-Denken.
```

### ARC-Agent (Architect)

```
Du bist ARC-Agent (Architect) in der PO-Pipeline.
Team: po-pipeline-{session}

DEINE ROLLE:
  Architect - du definierst technische Machbarkeit und Constraints.

FOKUS:
  - Was sind die technischen Grenzen dieses Features?
  - Welche Architektur-Constraints muessen beachtet werden?
  - Was sind Abhaengigkeiten zu anderen System-Komponenten?
  - Technische Schulden? Risiken?
  - Bewerte: ARC_complexity Score 1-10 (1=trivial, 10=sehr komplex)
  - Definiere: ARC_constraints Liste pro Epic/Story

NUR technische Sicht. Kein Business-Denken. Keine Forschungsevidenz.
```

---

## TANDEM-ENTSCHEIDUNGSMATRIX

Pro Epic/Story entscheidet das Tandem:

```
IMPLEMENT:      PO_value >= 7 AND PE_evidence >= 6 AND ARC_complexity <= 7
RESEARCH_FIRST: PE_evidence < 4 → Mehr Paper benoetigt, kein Implement
SPIKE:          ARC_complexity > 8 → Technisches Risiko zuerst angehen
PARK:           PO_value < 4 → Kein Nutzernutzen, zurueck in Backlog
NEGOTIATE:      Werte im Grenzbereich → Tandem-Diskussion noetig
```

---

## VERTRAG

```
LIEST:
  - paper(s) aus quellen/ (via RAG oder direkt)
  - _manifest.md (aktueller Stand)
  - session-state.json (optional)

SCHREIBT:
  - output/po/epics.json          (priorisierte Epic-Liste)
  - output/po/user-stories.json   (alle User Stories)
  - output/po/dependency-graph.json (Abhaengigkeiten)
  - output/po/synthesis-report.md  (finales Dokument)
  - obsidian/ (via /_PO_obsidianSync)
```

---

## QUICK-START

```
/_PO_orchestrate paper.pdf normal sonnet haiku

1. Team Lead liest paper.pdf (oder quellen/)
2. Spawnt PO + PE parallel: Epic-Extraktion (PO) + Evidenz-Check (PE)
3. Spawnt ARC: Constraints pro Epic
4. Spawnt alle 3 parallel: User Story Drafts + Scoring + Dependency Map
5. Synthesize: Konsens-Dokument
6. Sync nach Obsidian
7. HiL-Pause: ACCEPT / RETRY / ABORT
```

ARGUMENTS: $ARGUMENTS
