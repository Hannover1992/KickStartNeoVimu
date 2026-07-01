---
status: active
version: 1.1.0
created: 2026-02-24
updated: 2026-02-26
op: ReviewCycle
phase: Meta
type: orchestration
chain_position: standalone
difficulty_scaling: true
team_based: true
---

# /_R_orchestrate - Code Review Pipeline (Uncle Bob)

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: /_R_orchestrate                                            ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    .claude/review-{FEATURE}-queue.md  (Queue mit Code-Stellen)      ║
║    {VAULT}/_manifest.md                 (R_PIPELINE_STATE, Resume)    ║
║    .claude/models/{FEATURE}_Model.md  (optional, Kontext)           ║
║    .claude/evidence/*.md     (optional, Architektur-Kontext║
║                                        fuer W1 RAG-Scan + W3 DickBob║
║    {META}/codeKonvention/*.md   (projektspezifische Normen    ║
║                                        fuer W2 Bob + W3 DickBob,   ║
║                                        W213, RF-PI-005)             ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {VAULT}/_manifest.md                 (R_PIPELINE_STATE nach Welle) ║
║    .claude/review-{FEATURE}-queue.md  (Header: PENDING→REVIEWED)    ║
║                                                                      ║
║  AUSGABEN DURCH WORKER:                                              ║
║    .claude/review/ragscan-{item}.md         (Welle 1, floor/haiku)  ║
║    .claude/review/bob-monolog-{item}.md     (Welle 2, ceiling (min. sonnet))║
║    .claude/review/PRAESENTATION-{FEATURE}-{YYYY-MM-DD}.md (Welle 3) ║
║                                                                      ║
║  INVARIANTEN (W27):                                                  ║
║    NIE Code schreiben oder aendern (Analysis-only, kein _implement)  ║
║    NIE Queue-Datei loeschen/verschieben (nur Header-Update)          ║
║    NIE Wellen parallel starten (N+1 erst nach N komplett)           ║
║    NIE mcp__cleancoder__query im Team Lead selbst (nur W1-Workers)  ║
║    NIE DickBob bei easy-Modus spawnen (W26, W8, YAGNI)             ║
║    NIE /_R_orchestrate ohne aktive User-Session starten (W225: HiL) ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

```
+======================================================================+
| META-COMMAND: /_R_orchestrate                                        |
+======================================================================+
|                                                                      |
| ACTOR: TEAM LEAD (DU - die ausfuehrende Claude-Instanz)             |
| WORKER: 3 Wellen-Typen:                                             |
|   W1: floor/haiku  → r-{feature}-{item}-ragscan (MCP RAG-Scan)     |
|   W2: ceiling (min. sonnet) → r-{feature}-{item}-bob (Uncle Bob Monolog)   |
|   W3: ceiling/opus  → r-{feature}-synthese-dickbob (Synthese)      |
|                                                                      |
| ZWECK: User zeigt Code-Stellen via Queue-Datei. Uncle Bob analysiert|
|   durch Clean-Code-Linse (RAG + Monolog + Synthese). Praesentation  |
|   mit WARUM/WOFUER-Ankern und KRITISCH/WARN/INFO Schweregrad.       |
|                                                                      |
| PRINZIP: 1 Agent = 1 Aufgabe = stirbt danach (KURZLEBIG_PROMPT).   |
|   State lebt in Dateien (File-Vertraege R1), nicht im Agenten.      |
|   Team Lead steuert ALLE Wellen. Kein Worker spawnt Sub-Agents.     |
|                                                                      |
| PIPELINE: PRE → WELLE 1 (RAG-Scan) → WELLE 2 (Bob-Monolog) →      |
|           WELLE 3 (DickBob-Synthese) → POST                         |
|   Kein Zyklus-Loop: nach Welle 3 ist die Pipeline FERTIG.          |
|                                                                      |
| ABGRENZUNG:                                                          |
|   NICHT SC (keine Hypothesen-Zyklen, kein Model-Building)           |
|   NICHT I (kein Code-Writing, keine Tests)                          |
|   R = "User zeigt Code, Uncle Bob urteilt, Praesentation raus"      |
+======================================================================+
```

---

## Aufruf

```
/_R_orchestrate [feature] [difficulty] [ceiling] [floor]
```

**Parameter:**

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `feature` | (PFLICHT) | String | Feature-Name (z.B. "DCSRE-881"). Queue-Datei: `.claude/review-{feature}-queue.md` |
| `difficulty` | normal | easy, normal, hard | Steuert Anzahl Worker pro Welle |
| `ceiling` | sonnet | haiku, sonnet, opus | Hoechstes Modell (W3 DickBob) |
| `floor` | haiku | haiku, sonnet | Niedrigstes Modell (W1 RAG-Scan) |

**Beispiele:**
```
/_R_orchestrate DCSRE-881                        → normal, sonnet/haiku
/_R_orchestrate DCSRE-881 hard opus haiku        → hard, 9-5-1 Skalierung
/_R_orchestrate DCSRE-881 easy                   → easy, 1 Bob-Agent (kein DickBob)
/_R_orchestrate MyFeature normal sonnet haiku    → normal, sonnet ceiling
```

**Wellen-Skalierung (N = Anzahl PENDING Queue-Items):**

| Difficulty | Welle 1 (RAG-Scan, floor) | Welle 2 (Bob, ceiling) | Welle 3 (DickBob, ceiling) |
|------------|--------------------------|----------------------|---------------------------|
| easy | SKIP | 1 Agent | SKIP (Bob = Endprodukt) |
| normal | min(N, 5) Agents PARALLEL | min(N, 3) Agents PARALLEL | 1 Agent |
| hard | min(N, 9) Agents PARALLEL | min(N, 5) Agents PARALLEL | 1 Agent |

**Modell-Zuordnung:**

| Rolle | Modell | Agent-Name | Naming-Beispiel |
|-------|--------|------------|-----------------|
| W1 RAG-Scan | {floor} (haiku) | r-{feature}-{item}-ragscan | r-DCSRE881-item1-ragscan |
| W2 Bob | {bob_model} (ceiling, min. sonnet) | r-{feature}-{item}-bob | r-DCSRE881-item1-bob |
| W3 DickBob | {ceiling} (opus) | r-{feature}-synthese-dickbob | r-DCSRE881-synthese-dickbob |

---

## GLOBALE PARAMETER (/_param Override)

Lies `{VAULT}/_session_params.md` (4 Zeilen, 4 Parameter):

**Berechnung:**
```
params = lies("_session_params.md")
difficulty = params.difficulty
ceiling    = min(ceiling, params.ceiling)
floor      = max(floor, params.floor)
# PFLASTER (BL-363): Uncle Bob (Welle 2) faehrt IMMER den ceiling (dynamisch aus /_param),
# NIE den middle/sonnet-Default und auf GAR KEINEN FALL haiku. ceiling=haiku -> sonnet-Floor.
bob_model  = ceiling if ceiling != "haiku" else "sonnet"
# DOKTRIN: Urteil=ceiling / Sammeln=floor
# Urteil-Rollen (Bob W2, DickBob W3) = Aufgabe erfordert Abwaegung/Entscheidung → ceiling
# Sammeln-Rollen (W1 RAG-Scan) = mechanische Faktenerhebung, kein Urteil → floor genuegt
# Bob (W2): Code durch Clean-Code-Linse beurteilen = Urteil → ceiling (min. sonnet)
# DickBob (W3): Synthese aller Urteile = Urteil → ceiling (bereits korrekt)
# W1 RAG-Scan: Chunks suchen/strukturieren = Sammeln → floor (haiku genuegt)
# Floor-Guard: ceiling=haiku verboten fuer Urteil-Rollen → bob_model=sonnet als Minimum
```

---

## PHASE 1: TEAM SETUP

### Schritt 1.1: Queue laden + parsen

Team Lead liest `.claude/review-{FEATURE}-queue.md` einmalig (kein Polling).

**Queue-Parser Pseudocode (W31):**
```
1. Split Inhalt nach "## Item" Sektions-Marker
2. Pro Sektion:
   a. Pruefen ob Header "(PENDING)" enthaelt
      → "(REVIEWED ...)"? → UEBERSPRINGEN
      → "(PENDING)"? → extrahieren
3. Felder extrahieren via Bold-Marker:
   **BEZEICHNUNG:**, **DATEI:**, **ZEILEN:**, **FRAGE:**
   **UNCLE_BOB_FOCUS:** (optional), **PRIORITAET:** (optional)
4. CODE-Block: alles zwischen ``` Fence-Markers nach **CODE:**
5. N = Anzahl PENDING-Items

Falls N = 0 → W28 HANDLER (Leere Queue, siehe unten)
Falls N > 0 → weiter mit Schritt 1.2
```

**W28 Leere Queue Handler:**
```
Falls review-{FEATURE}-queue.md fehlt ODER keine PENDING Items:
  → Team Lead informiert User:
    "Queue leer -- keine PENDING Items in review-{FEATURE}-queue.md.
     Queue anlegen oder Items als PENDING markieren."
  → Pipeline stoppt (kein PRAESENTATION-Output)
  → _manifest.md NICHT mit R_PIPELINE_STATE befuellt
  → FERTIG (kein Team, keine Tasks)
```

### Schritt 1.2: Team erstellen

```
TeamCreate:
  team_name: "r-{feature}"
  description: "Code Review Pipeline - {feature} ({N} Items)"
```

### Schritt 1.3: Tasks erstellen

Team Lead erstellt nach difficulty folgende Tasks:

**PRE-Task:**

| # | Task Subject | ActiveForm | Blocked By |
|---|-------------|-----------|------------|
| 0 | PRE: Queue parsen + R_PIPELINE_STATE init | Parsing queue and initializing state | - |

**Wellen-Tasks (pro Queue-Item, NACH PRE):**

Bei `easy`:
```
Task 1: "W2 Bob: {ITEM_BEZEICHNUNG}"
  activeForm: "Bob analysiert {ITEM_BEZEICHNUNG}"
  description: [Welle-2-Easy-Prompt, siehe Phase 2]
  blocked_by: Task 0
```

Bei `normal` (Beispiel fuer 3 Items):
```
Tasks 1-3: "W1 RAG-Scan: {ITEM_N}"
  activeForm: "Scanne {ITEM_N} via RAG"
  blocked_by: Task 0

Tasks 4-6: "W2 Bob: {ITEM_N}"
  activeForm: "Bob analysiert {ITEM_N}"
  blocked_by: entspr. W1-Task (Task 1/2/3)

Task 7: "W3 DickBob Synthese"
  activeForm: "DickBob synthetisiert alle Items"
  blocked_by: Tasks 4-6 (ALLE W2 muessen fertig sein)
```

**POST-Task:**

| # | Task Subject | ActiveForm | Blocked By |
|---|-------------|-----------|------------|
| POST | POST: Manifest finalisieren + User informieren | Finalizing review pipeline | W3-Task (oder letztem W2-Task bei easy) |

### Schritt 1.4: R_PIPELINE_STATE initialisieren

Team Lead schreibt in `_manifest.md`:

```yaml
R_PIPELINE_STATE:
  feature: {FEATURE}
  difficulty: {easy|normal|hard}
  queue_file: .claude/review-{FEATURE}-queue.md
  items_total: {N}
  items_processed: 0
  current_welle: {1|bob_only}
  status: RUNNING
  ceiling_model: {opus|sonnet}
  floor_model: {haiku|sonnet}
  timestamp: {ISO-8601}
  items:
    - bezeichnung: "{ITEM_BEZEICHNUNG}"
      status: pending
      w1_agent: "r-{feature}-{item}-ragscan"
      w2_agent: "r-{feature}-{item}-bob"
      rag_chunks: null
      schweregrad: null
```

### Schritt 1.5: Agents spawnen

Team Lead spawnt W1-Agents (oder direkt W2 bei easy) PARALLEL:

```
FUER JEDES PENDING Item (Welle 1, normal/hard):
  Task tool:
    name: "r-{feature}-{item}-ragscan"
    subagent_type: "general-purpose"
    model: "{floor}"
    team_name: "r-{feature}"
    mode: "bypassPermissions"
    run_in_background: true        ← PARALLEL innerhalb Welle
    prompt: [Welle-1-Prompt, siehe Phase 2]

NACH Welle 1 komplett (alle W1 SendMessage empfangen):
FUER JEDES Item (Welle 2):
  Task tool:
    name: "r-{feature}-{item}-bob"
    subagent_type: "general-purpose"
    model: "{bob_model}"   # PFLASTER BL-363 (war {middle}): Uncle Bob immer ceiling, nie sonnet-Default, nie haiku
    team_name: "r-{feature}"
    mode: "bypassPermissions"
    run_in_background: true        ← PARALLEL innerhalb Welle
    prompt: [Welle-2-Prompt, siehe Phase 2]

NACH Welle 2 komplett (ALLE W2 SendMessage empfangen, NUR normal/hard):
  Task tool:
    name: "r-{feature}-synthese-dickbob"
    subagent_type: "general-purpose"
    model: "{ceiling}"
    team_name: "r-{feature}"
    mode: "bypassPermissions"
    prompt: [Welle-3-Prompt, siehe Phase 2]
```

---

## PHASE 2: KURZLEBIG_PROMPT Vorlagen

### Welle 1: RAG-Scanner (floor/haiku)

```
[WORKER-MODE] Welle 1: RAG-Scan

Du bist ein RAG-Scanner (haiku). Dein Job: Fakten sammeln, KEIN Urteil.
Agent-Name: r-{FEATURE}-{ITEM_BEZEICHNUNG}-ragscan
Team: r-{FEATURE}
Task-ID: {TASK_ID}

LIES:
- Item-Bezeichnung: {ITEM_BEZEICHNUNG}
- Code-Snippet:
{CODE_SNIPPET}
- Focus: {UNCLE_BOB_FOCUS}   ← aus Queue-Item (optional, sonst "Clean Code best practices")
- Datei: {DATEIPFAD}:{VON}-{BIS}
- User-Frage: {USER_FRAGE}
- Evidence-Kontext: .claude/evidence/*.md  ← optional, falls Dateien vorhanden: kurz lesen (Architektur-Entscheidungen beachten)

FUEHRE AUS:
1. mcp__cleancoder__query(
     query_text="Clean Code: {UNCLE_BOB_FOCUS} principles and violations",
     limit=5)
2. mcp__cleancoder__query(
     query_text="code smell {CODE_ASPECT} detection and refactoring",
     limit=3)
   wobei {CODE_ASPECT} aus dem Code abgeleitet wird (z.B. "long method", "many dependencies")
3. NUR wenn Query 1 < 3 Treffer:
   mcp__cleancoder__query(
     query_text="clean code {DATEITYP} best practices",
     limit=3)

SCHREIBE: .claude/review/ragscan-{ITEM_BEZEICHNUNG}.md
FORMAT:
---
item: {ITEM_BEZEICHNUNG}
welle: 1
agent: r-{FEATURE}-{ITEM_BEZEICHNUNG}-ragscan
status: final
---
# RAG-Scan: {ITEM_BEZEICHNUNG}

## Relevante Prinzipien (Top 3-5)
### P1: {PRINZIP_NAME} (Score: {SCORE})
> {ZITAT_AUS_RAG_CHUNK}
> -- Episode {N}: {TITEL}

## Code-Smells (Top 2-3)
### S1: {SMELL_NAME} (Score: {SCORE})
> {BESCHREIBUNG}

## Meta
- Queries: {ANZAHL}, Chunks: {TOTAL}, Top-Episode: {EP}, Confidence: {HIGH|MED|LOW}

REGELN:
- KEIN Urteil, KEINE Interpretation, NUR RAG-Chunks strukturieren
- KEIN Sub-Agent, KEIN Task-Tool

ABSCHLUSS:
TaskUpdate {TASK_ID} status=completed
SendMessage an "team-lead": "W1 {ITEM_BEZEICHNUNG}: {N} Prinzipien, Confidence {HIGH|MED|LOW}"
```

---

### Welle 2: Uncle Bob Monolog (ceiling/min. sonnet, normal/hard)

```
[WORKER-MODE] Welle 2: Uncle Bob Monolog

Du bist Uncle Bob (Robert C. Martin) -- "Maximum Value Density".
Direkt. Schonungslos. Prinzipien-basiert.
Agent-Name: r-{FEATURE}-{ITEM_BEZEICHNUNG}-bob
Team: r-{FEATURE}
Task-ID: {TASK_ID}

LIES:
- Queue-Item: {ITEM_BEZEICHNUNG}
- Code-Snippet:
{CODE_SNIPPET}
  (Datei: {DATEIPFAD}:{VON}-{BIS})
- User-Frage: {USER_FRAGE}
- RAG-Kontext: .claude/review/ragscan-{ITEM_BEZEICHNUNG}.md

# SP-FIX-10: Stille-Post-Schutz (RAG-Scan nur als Kompass)
STILLE-POST-SCHUTZ: ragscan-Output ist KONTEXT, nicht Faktenquelle.
Lies den CODE SELBST (Read-Tool: {DATEIPFAD} Zeilen {VON}-{BIS}).
Bilde dein Urteil an der PRIMAERQUELLE (Code). RAG-Chunks sind
Inspiration fuer Prinzipien-Zuordnung, NICHT Beweis fuer Verletzungen.

DEINE 5 FRAGEN (beantworte ALLE):
F1: Welches Clean-Code-Prinzip wird hier verletzt -- und WIE GENAU?
F2: Warum ist diese Verletzung ein echtes Problem -- nicht nur aesthetisch?
F3: Was waere die Maximum-Value-Density-Loesung (minimaler Aufwand, maximaler Gewinn)?
F4: Stimmt mein Urteil mit den RAG-Findings ueberein -- oder widerspreche ich?
F5: Habe ich das DIREKT und OHNE Beschoenigung gesagt?

SCHREIBE: .claude/review/bob-monolog-{ITEM_BEZEICHNUNG}.md
FORMAT:
---
item: {ITEM_BEZEICHNUNG}
welle: 2
agent: r-{FEATURE}-{ITEM_BEZEICHNUNG}-bob
schweregrad: {KRITISCH|WARN|INFO}
status: final
---
# Bob-Monolog: {ITEM_BEZEICHNUNG}

## F1: Das Problem
{Diagnose: konkret, benannt, Episode-referenziert}

## F2: Uncle Bob sagt
> Clean Code Principle: {PRINZIP} (Episode {N})
> {WARUM das kostet -- wirtschaftlich, nicht aesthetisch}

## F3: Die Empfehlung
{Schritte 1-3, priorisiert, Optionen mit Aufwand-Schaetzung}

## F4: RAG-Kongruenz
{Uebereinstimmung oder Ergaenzung zu Welle-1-Findings}

## F5: Klarsprache
{1 Satz: Kernaussage ohne Beschoenigung}

## Schweregrad: {KRITISCH|WARN|INFO}

SPRACHE:
- CAPS fuer Kernwoerter (ZEHN, PUNKT, KEIN)
- Stage directions in *Kursiv* (*leans forward*, *pounds table*)
- Keine Hedge-Woerter ("vielleicht", "koennte man", "eventuell")
- Episode-Referenzen immer mit Nummer
- 150-300 Woerter pro Monolog

REGELN:
- KEIN Code aendern, NUR analysieren
- KEIN Sub-Agent, KEIN Task-Tool

ABSCHLUSS:
TaskUpdate {TASK_ID} status=completed
SendMessage an "team-lead": "W2 {ITEM_BEZEICHNUNG}: {SCHWEREGRAD} -- {1 Satz}"
```

---

### Welle 2 (Easy-Modus): Uncle Bob Direkt (ceiling/min. sonnet, KEIN ragscan-Input)

Bei `easy` entfaellt Welle 1 (RAG-Scan). Bob analysiert Code direkt (W26):

```
[WORKER-MODE] Easy-Modus: Uncle Bob Direkt-Analyse

Du bist Uncle Bob (Robert C. Martin) -- "Maximum Value Density".
Direkt. Schonungslos. Prinzipien-basiert.
Agent-Name: r-{FEATURE}-{ITEM_BEZEICHNUNG}-bob
Team: r-{FEATURE}
Task-ID: {TASK_ID}

KEIN ragscan-Input (easy-Modus, W1 entfaellt).

LIES (Code direkt):
- Queue-Item: {ITEM_BEZEICHNUNG}
- Code-Snippet:
{CODE_SNIPPET}
  (Datei: {DATEIPFAD}:{VON}-{BIS})
  Falls kein CODE-Feld: Lies Datei via Read-Tool (Zeilen {VON}-{BIS})
- User-Frage: {USER_FRAGE}
- Uncle Bob Focus: {UNCLE_BOB_FOCUS}  ← optional

DEINE 5 FRAGEN (beantworte ALLE):
F1: Welches Clean-Code-Prinzip wird hier verletzt -- und WIE GENAU?
F2: Warum ist diese Verletzung ein echtes Problem -- nicht nur aesthetisch?
F3: Was waere die Maximum-Value-Density-Loesung (minimaler Aufwand, maximaler Gewinn)?
F4: Welche Clean-Code-Prinzipien aus meinem Wissen sind hier relevant?
F5: Habe ich das DIREKT und OHNE Beschoenigung gesagt?

SCHREIBE: .claude/review/bob-monolog-{ITEM_BEZEICHNUNG}.md
          (dieses File IS die finale Praesentation im easy-Modus)
FORMAT: [identisch mit normalem Bob-Monolog, aber F4 = Prinzipien-Kontext aus eigenem Wissen]

REGELN:
- KEIN Code aendern, NUR analysieren
- KEIN Sub-Agent, KEIN Task-Tool
- Dieses Dokument ist das ENDPRODUKT (kein DickBob im easy-Modus)

ABSCHLUSS:
TaskUpdate {TASK_ID} status=completed
SendMessage an "team-lead": "Easy W2 {ITEM_BEZEICHNUNG}: {SCHWEREGRAD} -- {1 Satz}"
```

---

### Welle 3: DickBob Tournament Synthese (ceiling/opus, NUR normal/hard)

```
[WORKER-MODE] Welle 3: DickBob Tournament Synthese

Du bist DickBob -- Tournament Champion. Maximum Value Density.
Du hast ALLE Bob-Monologe. Jetzt urteilst du. Nicht analysieren -- ENTSCHEIDEN.
Agent-Name: r-{FEATURE}-synthese-dickbob
Team: r-{FEATURE}
Task-ID: {TASK_ID}

LIES:
- ALLE Bob-Monologe: .claude/review/bob-monolog-*.md  (N Stueck)
- ALLE RAG-Scans: .claude/review/ragscan-*.md  (als Hintergrund)
- Feature-Name: {FEATURE}
- Items: {ITEM_LISTE}   ← alle N Bezeichnungen
- Evidence-Kontext: .claude/evidence/*.md  ← optional, falls vorhanden: Architektur-Entscheidungen als Hintergrund (verhindert False Positives)

# SP-FIX-10b: Stille-Post-Schutz (Bob-Monologe nur als Kompass)
STILLE-POST-SCHUTZ: Bob-Monologe sind Analyseperspektiven, KEINE verifizierten Fakten.
Lies den CODE SELBST (via Read-Tool) bevor du Findings als Root Cause einstufst.
Verifiziere Prinzipien-Verletzungen an der PRIMAERQUELLE (Code-Dateien), nicht am Bob-Monolog.

DEIN AUFTRAG:
1. Lies alle bob-monolog-*.md (N Stueck)
2. Erkenne Querverbindungen: Verursacht Problem A das Problem B?
3. Identifiziere Root Causes vs Symptome
4. Erstelle Rangliste: Root Causes OBEN, Symptome UNTEN
5. Vergib Severity: KRITISCH (Root Cause, Architektur-Bruch) |
                   WARN (isolierte Verletzung, mittlere Auswirkung) |
                   INFO (Verbesserungswuerdig, nicht schaedlich)
6. Schreibe finale Praesentation mit WARUM + WOFUER Ankern

SCHREIBE: .claude/review/PRAESENTATION-{FEATURE}-{YYYY-MM-DD}.md
FORMAT:
---
type: review-praesentation
feature: {FEATURE}
date: {YYYY-MM-DD}
difficulty: {DIFFICULTY}
items_reviewed: {N}
pipeline: ragscan(haiku) -> bob-monolog(sonnet) -> dickbob-synthese(ceiling)
author: Uncle Bob (Robert C. Martin) via DickBob Tournament Champion
status: final
primaerquelle_gelesen: true
---
# Code Review -- {FEATURE} ({DATUM})

> "The only way to go fast is to go well." -- Robert C. Martin

---

## Zusammenfassung (DickBob-Synthese)

> *pounds table*
> Von {N} Code-Stellen identifiziere ich {K} mit echten Problemen.

### Rang 1: {BEZEICHNUNG} ({KRITISCH|WARN|INFO})
**Warum Rang 1:** {1-2 Saetze Begruendung}

### Rang 2: {BEZEICHNUNG} ({KRITISCH|WARN|INFO})
...

**Verbindungen:** {Items die sich bedingen}

---

## Item: {BEZEICHNUNG}

**Code-Stelle:** `{DATEIPFAD}` Z. {VON}-{BIS}

```{SPRACHE}
{CODE_SNIPPET_AUSZUG}
```

**Uncle Bob sagt:**
> *{stage direction}*
> {Bob-Zitat aus Monolog, 2-4 Saetze}

**Warum:** {PRINZIP}-Verletzung (Episode {N}).
{1-2 Saetze: was verletzt wird und warum es kostet}

**Wofuer:** {HANDLUNGS-OPTIONEN}
| Option | Aufwand | Risiko | SRP-Konformitaet |
|--------|---------|--------|-----------------|
| {A} | {X Tage} | {Niedrig/Mittel/Hoch} | {Niedrig/Mittel/Hoch} |

**Schweregrad:** {KRITISCH|WARN|INFO}
**RAG-Quellen:** {Top 2-3 Zitate mit Score}

---

## Architectural Decisions (aus Evidence)

NUR wenn .claude/evidence/*.md vorhanden UND relevant fuer review items:

| Evidence-ID | Typ | Entscheidung |
|-------------|-----|-------------|
| {EVIDENCE_ID} | {constraint/analyse/risk} | {entscheidung aus YAML-Frontmatter} |

Falls keine relevante Evidence vorhanden: Sektion weglassen.
Evidence verhindert False Positives: Wenn Code WEGEN einer Architektur-Constraint so aussieht
(z.B. kein TrackableEntityBase bei Junction-Tabelle), KEIN WARN/KRITISCH dafuer vergeben.

---

## Uncle Bob Signatur

> *steht auf, richtet die Brille*
>
> {2-3 Saetze Zusammenfassung + Empfehlung}
>
> Remember: {Passendes Bob-Zitat}
>
> -- Robert C. Martin, via DickBob Tournament Champion
> -- Analysiert am {DATUM} | Pipeline: floor -> ceiling(min.sonnet) -> ceiling

ENTSCHEIDUNGS-REGELN:
- KRITISCH: Kern-Prinzip (SRP/OCP/DIP), verursacht andere Smells, Architektur-Bruch
- WARN: Verletzt Prinzip, aber isoliert, mittlere Auswirkung
- INFO: Verbesserungswuerdig, nicht schaedlich
- Querverbindung: Problem A verursacht B → A=KRITISCH, B=WARN
- 1 kombinierte Praesentation (NICHT pro Item -- DickBob rankt ALLE zusammen)

REGELN:
- KEIN Code aendern, NUR urteilen
- KEIN Sub-Agent, KEIN Task-Tool

ABSCHLUSS:
TaskUpdate {TASK_ID} status=completed
SendMessage an "team-lead": "W3 Synthese: PRAESENTATION-{FEATURE}-{DATUM}.md fertig.
  KRITISCH: {K}, WARN: {W}, INFO: {I}"
```

---

## PHASE 3: TEAM LEAD STEUERUNG (Aktives Spawning)

### Live-Session Modus (Default)

**HINWEIS W225 — Human-in-the-Loop (User-Phase):**
Diese Pipeline enthaelt eine explizite User-Phase (HiL). Team Lead operiert in Rolle A
als INTERVIEW-PARTNER mit dem User. Dieser Dialog IST die Human-in-the-Loop-Interaktion —
kein separater Checkpoint noetig. Queue-Befuellung durch User = HiL-Eingabe.

Team Lead operiert in 2 gleichzeitigen Rollen:

**Rolle A: Interview-Partner (mit User)** [USER-PHASE / HiL W225]
```
User: "diese Methode — 200 Zeilen, alles drin"
Team Lead: Item in review-{feature}-queue.md eintragen
Team Lead: sofort Worker spawnen (run_in_background: true) wenn >=1 Item
User: "und noch dieser Controller..."
Team Lead: Item 2 eintragen → Worker 2 spawnen
```

**Rolle B: Pipeline-Prozessor (im Hintergrund)**
- Worker laufen PARALLEL zum Gespraech (run_in_background: true)
- Team Lead empfaengt Worker-Messages automatisch
- Sobald DickBob fertig: Ergebnis dem User praesentieren
- Naechstes Item? → Loop weiter

**Kein Batch-Modus noetig:** User muss Queue nicht vorab befuellen.
Queue waechst dynamisch waehrend Analyse laeuft.

---

### 3.1 Agent-Messages empfangen und Wellen steuern

Team Lead empfaengt Agent-Messages automatisch:

```
WELLE 1 AGENT meldet: "W1 {ITEM}: {N} Prinzipien, Confidence {HIGH|MED|LOW}"
  → Team Lead prueft: ragscan-{item}.md vorhanden + status:final?
  → Bei ALLEN W1-Agents fertig: Welle 2 starten
  → Manifest aktualisieren: current_welle = 2
  → W2-Agents spawnen (PARALLEL)

WELLE 2 AGENT meldet: "W2 {ITEM}: {SCHWEREGRAD} -- {1 Satz}"
  → Team Lead prueft: bob-monolog-{item}.md vorhanden + status:final?
  → Bei ALLEN W2-Agents fertig:
    easy: → Phase 4 direkt (Bob = Endprodukt)
    normal/hard: → Welle 3 starten (DickBob)
  → Manifest: items[{item}].status = w2_done, schweregrad = {SCHWEREGRAD}

WELLE 3 AGENT meldet: "W3 Synthese: PRAESENTATION-{FEATURE}.md fertig."
  → Team Lead prueft: PRAESENTATION-*.md vorhanden?
  → Manifest: current_welle = done, items_processed = {N}
  → Phase 4 starten (POST)
```

**Bei Agent-Problem:**
```
Agent meldet Fehler oder kommt nicht (>5min keine Message):
  → Team Lead: Erneut spawnen mit gleichem Prompt + Fehler-Kontext
  → Name: {original-name}-retry
  → Gleichem Task zuweisen
```

**R_PIPELINE_STATE nach jeder Welle aktualisieren:**
```yaml
R_PIPELINE_STATE:
  current_welle: {1|2|3|done}
  status: {RUNNING|COMPLETED|FAILED}
  items:
    - bezeichnung: "{ITEM}"
      status: {pending|w1_done|w2_done|done}
      rag_chunks: {N}     ← aus W1-Ergebnis
      schweregrad: {...}  ← aus W2-Ergebnis
```

---

## PHASE 4: POST-REVIEW

### 4.1 Manifest finalisieren

```yaml
R_PIPELINE_STATE:
  status: COMPLETED
  current_welle: done
  items_total: {N}
  items_processed: {N}
  praesentation_file: .claude/review/PRAESENTATION-{FEATURE}-{DATUM}.md
```

### 4.2 Queue-Header aktualisieren (W14: REVIEWED markieren)

Team Lead aendert AUSSCHLIESSLICH den Header der Queue-Datei:
```
Vorher: # Review Queue -- {FEATURE} (PENDING)
Nachher: # Review Queue -- {FEATURE} (REVIEWED {YYYY-MM-DD})
```

Einzelne Items bleiben unveraendert (inkrementelle Erweiterung moeglich, W14).

### 4.3 User informieren (Text-Output)

Team Lead gibt kompakte Zusammenfassung aus:

```
=== Code Review {FEATURE} fertig ===

Analysiert: {N} Items | Pipeline: haiku -> sonnet -> DickBob
Praesentation: .claude/review/PRAESENTATION-{FEATURE}-{DATUM}.md

Ergebnis:
  KRITISCH ({K}): {Item-Bezeichnungen}
  WARN     ({W}): {Item-Bezeichnungen}
  INFO     ({I}): {Item-Bezeichnungen}

Empfehlung: {Top-1 Item} zuerst angehen ({Begruendung}).
```

### 4.4 AskUserQuestion: Naechster Schritt

Nach der Zusammenfassung wartet Team Lead auf User-Entscheidung:

| User-Antwort | Team Lead Aktion |
|--------------|-----------------|
| "Deep-Dive {Item}" | bob-monolog-{item}.md lesen, Details zeigen |
| "Naechste Items" | User editiert Queue, neuer `/_R_orchestrate` Run |
| "Done" | TeamDelete, Pipeline beendet |
| "Option {X} fuer {Item}" | Notieren (KEIN Code schreiben -- R ist Analysis-only) |

### 4.5 TeamDelete (nach User-Entscheidung "Done")

```
Keine aktiven Agents (kurzlebig, bereits terminiert).
TeamDelete: "r-{feature}"
```

---

## Queue-Format: review-{FEATURE}-queue.md

### Pflicht-Felder

| Feld | Pflicht | Beschreibung |
|------|---------|-------------|
| `## Item N: {BEZEICHNUNG}` | PFLICHT | Section-Header = Item-ID |
| `**Datei:**` | PFLICHT | Pfad zur Code-Stelle |
| `**Zeilen:**` | PFLICHT | VON-BIS Eingrenzung |
| `**Frage:**` | PFLICHT | User-Verdacht/Frage (lenkt Bob) |
| `**Code:**` Code-Block | PFLICHT | Code-Snippet (50 Zeilen empfohlen) |
| `**Uncle Bob Focus:**` | optional | Lenkt RAG-Query (z.B. "SOLID: SRP") |
| `**Prioritaet:**` | optional | HIGH / NORMAL / LOW |
| `**Kontext:**` | optional | Zusatz-Info |

### Minimal-Beispiel

```markdown
# Review Queue -- DCSRE-881 (PENDING)

## Item 1: Controller-God-Class

**Datei:** Modules/FileRetrieval/Controllers/FileRetrievalController.cs
**Zeilen:** 1-60
**Frage:** 12 Dependencies im Controller. God Class? SRP verletzt?
**Uncle Bob Focus:** SOLID: SRP
**Prioritaet:** HIGH

```csharp
public class FileRetrievalController : ControllerBase
{
    private readonly IFileService _fileService;
    // ... 11 weitere Dependencies
    public FileRetrievalController(/* 12 params */) { ... }
    public async Task<IActionResult> GetFile(string id) { /* 80 LOC */ }
}
```

---

## Item 2: Retry-Long-Method

**Datei:** Modules/FileRetrieval/Services/RetryService.cs
**Zeilen:** 45-160
**Frage:** ExecuteWithRetry ist 115 Zeilen. Zu lang?

```csharp
public async Task<T> ExecuteWithRetry<T>(
    Func<Task<T>> operation, RetryConfig config)
{
    // 115 Zeilen: Retry + Backoff + CircuitBreaker + Fallback + Metrics
}
```
```

**Empfehlung Code-Snippets:** SOLLTEN 50 Zeilen nicht ueberschreiten.
Bei laengeren Stellen: aufteilen in mehrere Items (1 Fokus pro Item).

---

## INVARIANTEN (W27)

```
NIE: Code aendern oder schreiben (R ist Analysis-only, kein _implement)
NIE: Queue-Datei loeschen oder verschieben (User-Kontrolle; nur Header-Update)
NIE: Parallel mehrere Wellen starten (Welle N+1 erst nach Welle N KOMPLETT)
NIE: mcp__cleancoder__query im Team Lead selbst aufrufen (nur W1-Workers)
NIE: DickBob bei easy-Modus spawnen (1 Item → Bob = Endprodukt, YAGNI)
NIE: /_R_orchestrate ohne aktive User-Session starten (W225 — /_R = User-Phase, kein vollautomatisierter Agent-Step)
KEIN Warten auf vollstaendige Queue (Live-Session: sofort spawnen bei >=1 Item)
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| Queue-Datei fehlt | W28 Handler: User informieren, Pipeline stoppt |
| Keine PENDING Items | W28 Handler: User informieren, Pipeline stoppt |
| MCP-Fehler (0 Treffer) | TODO: Welle-1-Agent schreibt ragscan mit "0 Treffer, Confidence LOW" — Bob analysiert trotzdem direkt |
| Agent stagniert (>5min keine Message) | Team Lead: neuen Agent spawnen mit -retry Suffix |
| bob-monolog-*.md fehlt nach W2 | Team Lead: W2-Agent erneut spawnen fuer fehlendes Item |
| PRAESENTATION-*.md fehlt nach W3 | Team Lead: DickBob erneut spawnen |
| TODO: Timeout-Handling (Gate 4 WARN) | Timeout-Strategie noch nicht spezifiziert (Parking Lot) |

---

## QUICK-START

Wenn User sagt "reviewe Code-Stelle X":

```
1. User schreibt .claude/review-{FEATURE}-queue.md (1-N Items)
2. /_R_orchestrate {FEATURE} [normal]
3. Team Lead: Queue parsen → N Items → Team + Tasks erstellen
4. Welle 1: haiku-Agents (PARALLEL) → ragscan-*.md
5. Welle 2: ceiling-Agents (bob_model, PARALLEL) → bob-monolog-*.md
6. Welle 3: ceiling-Agent (1x) → PRAESENTATION-*.md
7. Team Lead: Queue als REVIEWED markieren, User informieren
8. User: Deep-Dive / Naechste Items / Done
```

---

## ABGRENZUNG: SC vs R vs I

| Dimension | /_SC_orchestrate | /_R_orchestrate | /_I_orchestrate |
|-----------|-----------------|-----------------|----------------|
| **Zweck** | Forschungszyklus: Hypothesen, Model-Building | Code-Review: Uncle Bob urteilt | Implementation: Code schreiben, Tests |
| **Input** | Task.md, Crumbs, Wissen aus Vault | review-{feature}-queue.md (Code-Stellen) | Model.md, Hypothesen, Spec |
| **Output** | Model.md, HYPOTHESEN.md, ERGEBNIS.md | PRAESENTATION-*.md (bob-monolog-*.md) | Code-Aenderungen, Tests |
| **Loop** | Zyklus-Loop (CONTINUE/DONE) | Einmalig (PRE→W1→W2→W3→POST) | Batch-Loop (Slices) |
| **Uncle Bob** | Nein | JA -- Kernrolle (via RAG + Agent) | Nein |
| **Code** | Nein | NIE (Analysis-only) | JA (Haupt-Output) |
| **Pipeline-Position** | Vor I (optional) | Jederzeit standalone | Nach SC (optional) |

**Wann /_R_orchestrate nutzen:**
- Vor einer PR: Kritische Code-Stellen durch Uncle Bob pruefen
- Nach einem Feature: Refactoring-Kandidaten identifizieren
- Ad-hoc: "Was sagt Clean Code zu dieser Methode?"

---

## PR-REPLY-GUIDELINES (RF-SC-004, AC-SC-005, W247)

Nach einer Code-Review-Praesentation koennen Reviewer-Kommentare und PR-Antworten entstehen.
Diese Regeln strukturieren wie auf Review-Findings geantwortet wird — "in einem Command ODER Artefakt".

### PR-Kommunikationsregeln

**Grundregel:** IMMER strukturierte Antworten, NIE vage Zusagen.

**Doing-Regel (Was wurde konkret umgesetzt):**
```
Format fuer "Doing"-Antwort:
  → NUR konkrete Commits verlinken (kein "wurde erledigt" ohne Nachweis)
  → Commit-Format: "{COMMIT_HASH}: {Beschreibung der Aenderung}"
  → Mehrere Commits: chronologisch auflisten
  → Kein Commit verfuegbar → AUSSTEHEND markieren, nicht behaupten "erledigt"
```

**Abweichungs-Regel (Wenn Reviewer-Vorschlag nicht umgesetzt wird):**
```
Format fuer Abweichungs-Antwort (3 Pflicht-Elemente):
  1. VERSTAENDNIS: "Ich verstehe, dass {Reviewer-Punkt}."
  2. BEGRUENDUNG: "Wir weichen ab, weil {technische/fachliche Begruendung}."
  3. EVIDENCE-VERWEIS: "Siehe {Evidence-Datei ODER Architektur-Entscheidung ODER W{n}-Grundlage}."

Beispiel:
  "Ich verstehe, dass ein separater Service empfohlen wird.
   Wir weichen ab, weil die Logik in diesem Kontext atomar ist (SRP: 1 Grund zum Aendern).
   Siehe EVIDENCE-DCSRE881-SRP-2026-02-24.md (constraint: Service-Extraktion erhoehte
   Kopplung ohne Testbarkeitsgewinn)."
```

**Scope-Regel (Was NICHT geaendert wird):**
```
Format fuer Scope-Antwort:
  → Explizit benennen: "Ausserhalb Scope dieses PRs."
  → Parking-Lot-Verweis: "Eingetragen in {VAULT}/_parking-lot.md als [TITEL]."
  → Kein "werden wir machen" ohne konkreten Tracking-Eintrag.
```

**INVARIANTE:** /_R_orchestrate schreibt NIEMALS Code (Analysis-only). PR-Antworten
sind textuelle Kommunikation. Code-Fixes entstehen via /_I_orchestrate oder manuell.

---

## PARKING LOT

| # | Item | Beschreibung | Prioritaet |
|---|------|-------------|-----------|
| PL-1 | `/_R_modelReview` | Quality Gate SC→I: Model-Reife pruefen, PASS/FAIL. Separater Command (SRP). | NIEDRIG |
| PL-2 | `/bob` Skill Integration | Post-Synthese TDD-Check. --tdd Flag. | NIEDRIG |
| PL-3 | `--separate` Flag | Separate Praesentation pro Item (50+ Items, CI/CD). | NIEDRIG |
| PL-4 | Resume-Mechanismus | R_PIPELINE_STATE Resume bei Abbruch mid-Pipeline. | NIEDRIG |
| PL-5 | Timeout-Handling | MCP-Timeout-Strategie fuer Welle-1-Agents. | MITTEL (Gate 4 WARN) |
| PL-6 | Code-Snippet Security | Injection-Risiko bei User-kontrollierten Snippets. | NIEDRIG (Nutzer-Verantwortung) |

---

ARGUMENTS: $ARGUMENTS
