# /_PO_orchestrate - Team Lead PO-Pipeline-Orchestrierung

```yaml
status: active
version: 1.0.0
created: 2026-02-23
op: ProductOwnerPipeline
phase: Meta
type: orchestration
chain_position: meta
difficulty_scaling: true
team_based: true
changelog: |
  v1.0: Initialer Entwurf. Modelliert nach /_WP_orchestrate v3.0 Muster.
        KURZLEBIG_PROMPT Pattern. 3 Rollen-Agents: PO, PE, ARC.
        Paper → Epic → User Story → Obsidian Pipeline.
        Tandem-Entscheidungsmatrix: PO_value, PE_evidence, ARC_complexity.
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

Lies `.claude/analysis/_manifest.md` und suche nach GLOBAL_* Feldern.
Falls gesetzt, ueberschreiben sie die lokalen Parameter-Defaults:

| Manifest-Feld | Wirkung |
|---|---|
| `GLOBAL_DIFFICULTY` | Ueberschreibt lokalen `difficulty` Default |
| `GLOBAL_CEILING` | Kappt lokales ceiling: `effektiv = min(lokal, GLOBAL_CEILING)` |
| `GLOBAL_FLOOR` | Hebt lokalen floor an: `effektiv = max(lokal, GLOBAL_FLOOR)` |

**Berechnung:**
Hierarchie: opus=3, sonnet=2, haiku=1
IF GLOBAL_DIFFICULTY gesetzt UND != "(nicht gesetzt)": difficulty = GLOBAL_DIFFICULTY
IF GLOBAL_CEILING gesetzt UND != "(nicht gesetzt)":    ceiling = min(ceiling, GLOBAL_CEILING)
IF GLOBAL_FLOOR gesetzt UND != "(nicht gesetzt)":      floor = max(floor, GLOBAL_FLOOR)
Validierung: ceiling >= floor (sonst ceiling = floor + Warning ausgeben)
middle = sonnet wenn ceiling=opus, haiku wenn ceiling=sonnet, haiku wenn ceiling=haiku

**Falls KEINE GLOBAL_* Felder gesetzt:** Lokale Defaults gelten unveraendert.

---

## PIPELINE-PHASEN

### Phase 1: SETUP

```
T0: paperRead     → Paper lesen, Insights clustern
T1: epicExtract   → PO + PE PARALLEL: Epics extrahieren und validieren
T2: archConstrain → ARC: Constraints pro Epic einarbeiten
```

### Phase 2: USER STORY PHASE

```
T3: storyDraft     → PO primary, PE + ARC annotieren (PARALLEL)
T4a: valueScore    → PO + PE + ARC: Scoring (PARALLEL)
T4b: depMap        → Abhaengigkeiten kartieren
```

### Phase 3: SYNTHESE

```
T5: synthesis  → Alle Rollen: Konsens + finales Dokument
```

### Phase 4: HiL-PAUSE

```
AskUserQuestion: ACCEPT / RETRY / ABORT
```

### Phase 5: VAULT SYNC (nur bei ACCEPT)

```
T6: obsidianSync → Vault Integration
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
