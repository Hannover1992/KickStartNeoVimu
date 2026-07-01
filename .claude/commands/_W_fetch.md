---
type: building-block
depends_on: []
feeds_into:
  - _SC_orchestrate
  - _A_orchestrate
related:
  - _taskDefinition
  - _model
---

# /_W_fetch

**Status:** v5.1 (Graph-Traversal-Primary + Cache-Semantik + _vault_refs.md + Vault-Routing v2.0 + WARNING-Guard + 7 RAG-Collections + Worker-Vertraege + Ankerpunkt-Persistenz + Dual-Pfad Truth-Direktsuche BL-389)
**Actor:** KNOWLEDGE-SCOUT
**Zweck:** Bei Feature-Start existierendes Wissen via Graph-Traversal im Vault identifizieren, Referenz-Index erstellen, und lokalen Cache aktualisieren

> **SEMANTIK-SHIFT v5.0 (RF-03):** Vault ist PRIMAER-QUELLE. Graph-Traversal ist der
> primaere Modus. Lokale Kopien in .claude/models/ und .claude/wissen/ sind **CACHE**
> (nicht Primaerquelle). Der Referenz-Index `_vault_refs.md` ist das primaere Ergebnis.
> Agenten lesen bei Bedarf direkt aus dem Vault (via _vault_refs.md Pfade).
> Cache-Refresh erfolgt NACH Graph-Traversal als Fallback fuer Offline/Performance.

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_W_fetch {THEMA|FEATURE} [easy|normal|hard]         |
+===============================================================+
|                                                                |
|  KERN-PROBLEM:                                                 |
|    Jedes Feature startet bei Null — obwohl im Vault            |
|    UND im RAG bereits Models und Wissen existieren.            |
|    Wissen geht verloren oder wird dupliziert.                  |
|    Semantisch verwandtes Wissen wird nicht gefunden             |
|    weil nur exakte Tags/Namen gesucht werden.                  |
|                                                                |
|  KERN-PRINZIP (v5.0 Graph-Traversal-Primary):                  |
|    VOR Feature-Start: Vault-Graph traversieren + RAG suchen.   |
|    Graph-Traversal ist PRIMAERER Modus.                        |
|    Ergebnis: _vault_refs.md (Referenz-Index mit Vault-Pfaden). |
|    Lokale Kopien (.claude/models/, .claude/wissen/) = CACHE.   |
|    Cache-Refresh NACH Graph-Traversal (Offline/Performance).   |
|    "Standing on the shoulders of giants."                      |
|  [BL-236 AK-6] 3-Modi fokussierte Retrieval (heisse Themen     |
|    statt Voll-Scan): (a) Anker-basiert (source_node Datei:Zeile|
|    = Drift-Check-Punkt + Entry, da); (b) Git-historische        |
|    Time-Achse (NEU); (c) Wissens-Graph-multi-step (Traversal,  |
|    da). Routing nach Themen-Hitze, nicht Full-Scan.            |
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. {VAULT}/_manifest.md                             |
|       → SYSTEM-MODEL, SCHWIERIGKEIT (Ceiling-Hierarchie)       |
|    2. {VAULT}/Task.md ODER User-Beschreibung                   |
|       → Themen/Keywords des neuen Features                     |
|    3. MCP global_knowledge Collection                          |
|       → Semantische Suche nach Themen-Keywords                 |
|    4. MCP local_knowledge_{FEATURE} Collection (falls exist.)  |
|       → Feature-spezifische vorherige Arbeit                   |
|                                                                |
|  LIEST (Input) - OPTIONAL (Vault):                             |
|    5. {VAULT}/_Tag-Index.md                                    |
|       → Thematischer Index aller Vault-Dokumente               |
|    6. {VAULT}/*_Model.md, *_Wissen.md (Glob)                  |
|       → Existierende thematische Models + Wissens-Dokumente    |
|    7. {VAULT}/_parking-lot.md                                  |
|       → Geparkte Items die zum neuen Feature passen?           |
|    8. {VAULT}/{PREV_FEATURE}.md                                |
|       → Vorheriges Feature-Note mit Links                      |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. .claude/analysis/_vault_refs.md (Referenz-Index, PRIMAER)|
|       → Vault-Pfade, Keywords, Scores, Relationen              |
|       → Agenten lesen bei Bedarf direkt aus Vault via Pfade    |
|    2. .claude/wissen/{THEMA}_Wissen.md (CACHE aus Vault)       |
|    3. .claude/models/{THEMA}_Model.md (CACHE aus Vault)        |
|    4. {bl_folder}/_manifest.md   (Pattern A: State, per-BL)   |
|       → "## W_fetch Keyword-Pool" Sektion (State, bleibt)      |
|       → W_FETCH_STATUS Einzeiler (State-Einzeiler)             |
|    5. {VAULT}/_manifest_protokoll.md  (Pattern C:     |
|       Protokoll-Eintrag)                                        |
|       → W_FETCH Log: Wissens-Basis-Tabelle PREPEND             |
|         (Vault-Hits, RAG-Hits, Score, Datum)                   |
|       → Keyword-Pool bleibt State in _manifest.md (NICHT hier) |
|                                                                |
|  SCHREIBT (Output) - abhaengig von Worker-Rolle:               |
|    Kartograph D{NN}:                                           |
|      drafts/{NAME}-fetch-D{NN}-{fokus}.md                     |
|    Filter:                                                     |
|      drafts/{NAME}-fetch-filter.md                             |
|    Konsolidierer:                                              |
|      wissen/{THEMA}_Wissen.md + models/{THEMA}_Model.md       |
|                                                                |
|  SCHREIBT NICHT:                                               |
|    - Vault-Dateien (nur LESEN, nicht aendern)                  |
|    - RAG Collections (nur LESEN, nicht aendern)                |
|    - Neue Wissens-Dokumente (/_knowledge macht das)            |
|                                                                |
|  PIPELINE:                                                     |
|    [/_W_fetch] → [/_taskDefinition] → [/_model] → ...          |
|    (Ganz am Anfang, VOR allem anderen)                         |
|                                                                |
|  VAULT-PFAD (5-stufig, vault-routing.json zuerst):             |
|    1. vault-routing.json: linux_path/windows_path (Stufe 1)    |
|    2. Environment: $OBSIDIAN_VAULT_PATH (Stufe 2)              |
|    3. Fallback: Manifest "## Obsidian Sync" VAULT-Wert         |
|    4. Default Linux: /home/uczen/Documents/DCS                 |
|    5. Default Windows: C:\Users\Administrator\Documents\DCS    |
|    Falls NICHTS gefunden → SCHRITT W: WARNING-Guard            |
|    (KEIN silent degraded mode — IMMER WARNING+FRAGE)           |
|                                                                |
|  RAG-COLLECTIONS (aus vault-routing.json):                     |
|    Pattern-Match $PWD → MATCHED_RULE.rag_collections           |
|    OmniCommand: 7 Collections (statt 2 hardcoded)              |
|    Fallback (DEGRADED): global_knowledge + local_{FEATURE}     |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**KNOWLEDGE-SCOUT:** Traversiert den Vault-Graph, erstellt Referenz-Index, aktualisiert lokalen Cache.

**TUT:** Vault-Graph traversieren (PRIMAER), RAG semantisch durchsuchen, Tag-Index nutzen,
relevante Dokumente identifizieren, _vault_refs.md Referenz-Index erstellen (PRIMAER-OUTPUT),
lokalen Cache aktualisieren (.claude/models/, .claude/wissen/ als FALLBACK),
Manifest dokumentieren.

**NICHT:** Wissen erstellen, Models schreiben, Vault aendern, RAG aendern.

---

---

## Schritt 0: Manifest lesen + Keyword-Pipeline

**IMMER als Erstes:**

### Schritt 0a: Manifest lesen

1. Lies `{VAULT}/_manifest.md`
   - Ermittle **SYSTEM-MODEL** und **SCHWIERIGKEIT** aus System-Konfiguration
   - Bestimme effektives Modell: `min(SYSTEM-MODEL, Command-Max=opus)`
   - Leite Modell-Zuordnung pro Welle ab (Welle 1=floor, Welle 2=middle, Welle 3=ceiling)
   - Pruefe Ceiling-Hierarchie: Parent-Schwierigkeit >= W_fetch-Schwierigkeit

### Schritt 0a.1: VAULT-ROUTING-LESE-MUSTER

```
SCHRITT 0a.1: VAULT-ROUTING-LESE-MUSTER
─────────────────────────────────────────────
R1: vault-routing.json lokalisieren
    CONFIG_PATH=".claude/config/vault-routing.json"
    Falls CONFIG_PATH nicht existiert → SCHRITT W (WARNING-Guard)

R2: Pattern-Match gegen $PWD (case-insensitiv)
    Fuer jede Regel in detection.rules (sortiert nach priority aufsteigend):
      Falls $PWD enthaelt rule.pattern (case-insensitiv) → VAULT_KEY=rule.vault, MATCHED_RULE=rule; BREAK
    Falls kein spezifischer Match → Wildcard-Regel (priority 999) verwenden

R3: Vault-Pfad aufloesen (5-stufig)
    Stufe 1: vaults[VAULT_KEY].linux_path (Linux) / windows_path (Windows) aus routing.json
             Falls existiert + erreichbar (test -d + .obsidian/) → VAULT_PATH ✓
    Stufe 2: $OBSIDIAN_VAULT_PATH (Env-Var)
             Falls gesetzt + erreichbar → VAULT_PATH ✓
    Stufe 3: Manifest '## Obsidian Sync' VAULT-Wert
             Falls vorhanden + erreichbar → VAULT_PATH ✓
    Stufe 4: Linux-Default /home/uczen/Documents/DCS → Falls erreichbar → VAULT_PATH ✓
    Stufe 5: Windows-Default C:\Users\Administrator\Documents\DCS → Falls erreichbar → VAULT_PATH ✓
    Falls alle Stufen scheitern → SCHRITT W (WARNING-Guard)

R4: RAG_COLLECTIONS lesen
    RAG_COLLECTIONS = MATCHED_RULE.rag_collections
    (Ersetzt hardcoded Collection-Listen in Commands)
```

### Schritt W: WARNING-GUARD

```
SCHRITT W: WARNING-GUARD
────────────────────────
AUSLOESER A: vault-routing.json fehlt unter .claude/config/
  → Ausgabe: "WARNING: vault-routing.json fehlt unter .claude/config/"
  → "Vault-Pfad und RAG-Collections koennen nicht automatisch ermittelt werden."

AUSLOESER B: Vault-Pfad nicht erreichbar (alle 5 Stufen in R3 fehlgeschlagen)
  → Ausgabe: "WARNING: Vault-Pfad nicht erreichbar."
  → "Konfigurierter Pfad: [VAULT_PATH falls bekannt, sonst 'unbekannt']"

GEMEINSAMER ZWEIG:
  Falls HiL=on:
    FRAGE: "Darf ich in DEGRADED MODE weitermachen? (Y/N)"
    Y → DEGRADED MODE aktiv (siehe unten)
    N → STOP + "Bitte vault-routing.json unter .claude/config/ konfigurieren."

  Falls HiL=off:
    Lese Manifest DEGRADED_MODE
    = "erlaubt"  → DEGRADED MODE aktiv
    = "verboten" ODER nicht gesetzt → STOP
      + "Autonomer Betrieb ohne funktionierendes Vault-Routing nicht erlaubt."
      + "Bitte vault-routing.json konfigurieren oder DEGRADED_MODE: erlaubt im Manifest setzen."

DEGRADED MODE (falls aktiviert):
  _W_fetch:        RAG-Suche mit [global_knowledge, local_knowledge_{FEATURE}] (2 Standard-Collections)
  _W_obsidianSync: Vault-Sync SKIP (nur Meldung: "Vault-Sync uebersprungen (DEGRADED MODE)")
  _W_push:         Nur RAG-Ingest (kein Vault-Push)
```

### Schritt 0b: Thema erkennen

```
Falls {THEMA} angegeben:
  → Direkt nach diesem Thema suchen

Falls {FEATURE} angegeben:
  → Lies Task.md / User-Beschreibung
  → Feature-Name als erstes Keyword uebernehmen
```

### Schritt 0b.1: Domain-Hash Mechanismus (RF-SC-003, W246)

**Zweck:** Feature-Namen enthalten oft fachspezifische Kuerzel die direkt als Collection-Key dienen.

```
Domain-Hash Algorithmus:
  1. Feature-Name normalisieren: {FEATURE} → lowercase, Sonderzeichen entfernen
     Beispiel: "DCSRE-881" → "dcsre881"
  2. Collection-Key ableiten: "local_knowledge_{hash}"
     Beispiel: "DCSRE-881" → "local_knowledge_dcsre881"
  3. Fachspezifische Begriff-Injektion:
     → Feature-Kuerzel direkt als hoechst-priorisiertes Keyword in Pool aufnehmen
     → Domain-Prefix extrahieren (z.B. "DCSRE" aus "DCSRE-881") als Keyword
     → Ticket-Nummer als Kontext-Keyword (z.B. "881")
  4. RAG-Abfrage: MCP query(collection="local_knowledge_{hash}", ...)
     → Exakter Collection-Key verhindert Cross-Feature-Kontamination
```

### Schritt 0c: Haiku-Keyword-Extraktion (W30-Fix)

**Primaer:** Haiku-basierte Keyword-Extraktion (ersetzt defektes KeyBERT, W30).

**Prompt-Template (wortwoertlich an Haiku senden):**

```
Lies die folgende Aufgabenbeschreibung sorgfaeltig.
Extrahiere 5-10 Schluesselwoerter, die THEMATISCH relevant sind.

REGELN:
- Nur Substantive/Fachbegriffe (keine Stopwords: der, und, ist, zu)
- Mindestlaenge: 3 Zeichen
- Keine Zahlen allein (W30, W31 nur wenn Feature-Bezeichner)
- Bevorzuge spezifische Begriffe (nicht: "System", "Feature", "Implementierung")
- Deutsch und Englisch mischen erlaubt
- Trenne Keywords mit Komma

FORMAT (exakt):
KEYWORDS: Begriff1, Begriff2, Begriff3, ...

AUFGABENBESCHREIBUNG:
{TASK_BESCHREIBUNG}
```

**Input:** Task.md Inhalt ODER User-Beschreibung ODER Feature-Name
**Output:** Komma-separierte Keyword-Liste (5-10 Keywords)

**Post-Processing (Qualitaetsfilter):**

```
1. Stopwords entfernen (deutsch + englisch)
2. Laengenfilter: Keywords < 3 Zeichen entfernen
3. Alphanumeric-Pattern: Reine Zahlen/Symbole entfernen
4. Deduplizierung (case-insensitive)
5. Fallback wenn < 2 Keywords nach Filtern:
   → Manuelle Erkennung aus {THEMA}/{FEATURE}-Namen
   → WARNUNG: "Zu wenige Keywords extrahierbar"
```

**Fallback-Kette (falls Haiku nicht verfuegbar):**
1. Manuelle Keyword-Erkennung aus {THEMA}/{FEATURE}-Namen
2. Tag-Index vollstaendig durchsuchen (breite Abdeckung)
3. MCP extract_keywords() NUR als letzter Fallback (bekannt defekt, W30)

### Schritt 0d: Tag-Index als Keyword-Seed (Index-First-Read, BL-242 AK-5/J13)

```
PRIMAER (Index-First, pre-computed — BL-242 AK-CTX-2): lies den vorab gebauten Index
  - {VAULT}/_Tag-Index.md                                 (Tag→topic-Markdown-Index, batch_2/J9)
  - .claude/output/retrieval_index/_keyword_index.json    (4-maschinelle-Indizes-Persistenz, batch_3/J12)

Fuer jeden Haiku-Keyword:
  1. Exact-Match: "topic/{keyword}" im Tag-Index registriert?
     → JA: Tag als zusaetzliches Keyword uebernehmen
  2. Synonym-Match: Keyword als registriertes Synonym?
     → JA: Zugehoeriges Tag uebernehmen
  3. Substring-Match: Keyword in Tag-Name enthalten (oder umgekehrt)?
     → JA: Tag uebernehmen
  4. Keyword-Index-Hit (_keyword_index.json vorhanden): "{keyword}" als Schluessel registriert?
     → JA: die verknuepften Knoten-Pfade als pre-computed Seed uebernehmen (KEIN Laufzeit-Glob/Walk noetig)

FALLBACK (graceful, Forward-Compat — KEIN Hard-Cut, Ca=147, PT-CMD-023):
  Falls Index fehlt/veraltet ODER Vault nicht erreichbar:
    → faelle auf den heutigen Laufzeit-Walk zurueck (Tag-Index-Durchsuchung wie bisher, nur Haiku-Keywords)
    → kein Hard-Fail; INFO: "Pre-computed Index nicht verfuegbar. Fallback auf Laufzeit-Walk (nur Haiku/Tag-Seed)."
```

**Szenario-Verify (M2-Disziplin, INV-Markdown-Engine-Bootstrap — kein Python-Test):**
- **Szenario A (Index vorhanden):** `_Tag-Index.md` + `_keyword_index.json` existieren → Schritt 0d liest sie PRIMAER (Index-Hit, kein Graceful-Skip), nutzt Keyword-Index-Treffer als Seed.
- **Szenario B (Index fehlt/stale):** Index nicht vorhanden/Vault nicht erreichbar → Schritt 0d faellt explizit auf den heutigen Laufzeit-Walk zurueck (Forward-Compat, kein Hard-Fail).

### Schritt 0e: Feature-spezifische Keywords aus Task.md

```
Task.md Zeile 1 (Feature-Name): Direkt als Keyword
Erfolgskriterien: Feature-Bezeichner (z.B. W31, EC2) als Keywords
```

### Schritt 0f: Kombinierter Keyword-Pool

```
POOL = deduplicate(
  feature_name         # Hoechste Relevanz
  + haiku_keywords     # Kontextuell (aus 0c)
  + tag_index_seed     # Strukturiert (aus 0d)
  + task_keywords      # Spezifisch (aus 0e)
)

Sortierung:
  1. Feature-Name (hoechste Relevanz)
  2. Haiku-Keywords (mittelhohe Relevanz)
  3. Tag-Index-Seed (niedrigere Relevanz)
  4. Task-Keywords (spezifisch)

LIMIT: Top 15 Keywords (nach Deduplizierung)
WARNUNG wenn > 15 vorhanden: "Pool gekuerzt auf Top 15"
```

### Schritt 0g: User-Bestaetigung + Manifest-Eintrag

```
Bei easy: AUTO-ACCEPT (kein User-Input, W27)
  → Pool direkt uebernehmen
  → Direkt zu Welle 3

Bei normal/hard: User bestaetigt Keyword-Pool
  → Praesentiere Pool dem User:
    "Keywords fuer /_W_fetch {THEMA} {SCHWIERIGKEIT}:
     [Pool-Liste]
     Aenderungen? (Enter=OK, ergaenzen/entfernen/neu)"
  → User-Input verarbeiten

Manifest-Eintrag (IMMER, /compact-sicher):
  ## W_fetch Keyword-Pool
  **Feature:** {THEMA}
  **Schwierigkeit:** {easy|normal|hard}
  **Extraktion:** Haiku (W30-Fix) + Tag-Index Seed
  **Keywords:** {KW1}, {KW2}, ..., {KWn}
  **User-Bestaetigt:** {JA|NEIN (easy Auto-Accept)}
```

**AUSGABE:**
```
"Keyword-Pool ({N} Keywords): {KW1}, {KW2}, {KW3}, ..."
"Methode: Haiku-Extraktion + Tag-Index-Seed"
```

---

## Worker-Vertrag: Kartograph (Kartographierung)

### Zweck

Breit suchen. Alles finden was zum Thema passt — ohne zu filtern.

### Worker-Strategie 4-STUFEN (RF-WF-LIVE-2026-05-08, BL-161 Vorbote)

**Status:** PFLICHT-Worker-Walk seit 2026-05-08. Live-Validierung im DCSRE-486 W_fetch-Lauf
(28 Nodes, 47 Edges, 8 Disambiguierungen, easy=1 Opus-Worker, 5m 20s, 114k Tokens).

**Begruendung:** Quick-Win VOR BL-161 (Vault-Quality-System voll implementiert). Strategie
hat sich live bewaehrt waehrend Sanity-Dynamic-Run — als formaler Vertrag etabliert. Bei
BL-161-Implementierung werden Stufen 1+2+3 durch pre-computed Indizes (Anker-Liste,
Backlinks-Index, Tag-Index) beschleunigt; Stufe 4 (Edges-Pflicht) wird Standard.

**4 Stufen IN REIHENFOLGE auszufuehren:**

#### Stufe 1 — ANKER-FIRST (statt blind grep)

Identifiziere Anker-Knoten BEVOR du Keywords suchst:
- **Schwester-Story:** `Backlog/{PREFIX}-{N}-{aehnliches-thema}/2_Model/{NAME}_Model.md`
- **Pattern-Library Anker:** `Libraries/PatternLibrary/_project/{LAYER}/_index.md`
- **Topic-Anker:** Tag-Index → `topic/{KEYWORD}` exact lookup
- **Crumbs-Anker:** `Backlog/{aktuelle-story}/Crumbs/*_findings_crumbs_master.md`

Output: `anker_nodes: [path1, path2, ...]`. Min 1 Anker, sonst degraded-mode + WARNING.

#### Stufe 2 — DISAMBIGUIERUNG-MAP (Synonyme aufloesen)

Bevor Keywords ueber Vault geworfen werden, baue Synonym-Map.

Beispiel aus DCSRE-486:
- `"Validation"` → `["Validator", "DataAnnotations", "FluentValidation"]`
- `"QDV"` → `["Qualitaetsdarstellung", "Versorgungsqualitaet", "QDVTP", "QDVS"]`
- `"Akkordeon"` → `["Accordion", "section", "panel"]`
- `"Selbstauskunft"` → `["Selbstauskunft", "QDVTP-Selbstauskunft", "PE-Selbstauskunft"]`

Quelle: `Libraries/SemanticLibrary/_global/glossary.md` (falls vorhanden) + LLM-Reasoning
(Worker erkennt Synonyme aus Anker-Files-Frontmatter + Body).

Output: `disambig_map: {keyword: [synonyme]}`. Wird in Stufe 3+4 genutzt, NICHT in Stufe 1
(Anker sind bereits semantisch eindeutig).

#### Stufe 3 — GRAPH-TRAVERSAL (asymptotisch, loop-until-dry)

Ausgehend von `anker_nodes` (Stufe 1):
- **hop_0:** Anker selbst (Read)
- **hop_1:** Aus hop_0 extrahiere `[[wikilinks]]` + `frontmatter.derived_from` + `frontmatter.related_features` + Body-Pfad-Referenzen
- **hop_2+:** Wiederholen pro neuem CORE-Knoten — asymptotisch bis Konvergenz

**Knotenklassifikation (AK-2):**
- **CORE** = Hop-1-direkt-keyword-stark ODER >= 2 erreichende Kanten (confidence HIGH).
  CORE-Knoten treiben Grounding und oeffnen weitere Hops (Expansion).
- **BORDER** = peripher (1 schwache Kante, kein Keyword-Match). BORDER-Knoten sind
  demoted — sie erscheinen als Anhang im Output, werden aber NIE geloescht.
  Keine Expansion ab BORDER.

**Asymptotische Termination (AK-1):**
```
SAFETY_CAP = 6  # modus-invarianter absoluter Sicherheits-Cap
hop = 0
while delta_core > 0 AND hop <= SAFETY_CAP:
    entdecke neue Knoten → klassifiziere als CORE oder BORDER
    delta_core = Anzahl NEUER CORE-Knoten in dieser Runde
    IF delta_core == 0:
        break  # loop-until-dry: keine neuen CORE-Knoten -> konvergiert
    hop += 1
```
`delta_core` (nur CORE-Knoten) ist das Haupt-Terminations-Signal.
`SAFETY_CAP=6` ist absoluter Backup-Cap (modus-invariant).
Muster: dispatch_findings.js BL-235 (new_core_count, break bei delta==0, seen-Liste).

Pruning:
- **Top-N pro Hop:** N=5 bei easy, N=10 bei normal/hard
- **Visited-Cache:** keine Doppel-Reads (bleibt erhalten — Endlos-Schutz, INV)
- **Cross-Worker-Cache:** wenn andere W_fetch-Worker schon liefen, lese deren Output

**Regression-Invarianten (AK-3):**
- **INV-visited:** visited-Cache bleibt ueber alle Runden erhalten — kein Re-Visit moeglich (Endlos-Schutz).
- **INV-BORDER-nie-geloescht:** BORDER-Knoten werden NIE geloescht, nur demoted. Sie bleiben im Graph als Anhang.
- **INV-grounding-only-deepen:** Grounding wird nur vertieft (deepen) — bestehende Outputs
  (anker_nodes/visited_nodes/EDGES-PFLICHT/confidence) bleiben. CORE-Knoten werden vertieft,
  BORDER nicht. Kein Loeschen existierender Grounding-Ergebnisse.

**Output:** CORE-Grounding getrennt von BORDER-Anhang.

Aggregat: `visited_nodes = UNION(hop_0..hop_N)` (N <= SAFETY_CAP).

#### Stufe 4 — GEZIELTE KEYWORD-GLOB (mit Synonymen)

Fuer JEDES Keyword + Synonyme aus Stufe 2:
- **Glob:** `{VAULT}/**/*{keyword|synonym}*.md`
- **Tag-Index:** `topic/{keyword|synonym}`
- **Grep -r:** ueber Vault (Volltext, mit Snippets)

Score-Boost: Hits die AUCH in `visited_nodes` (Stufe 3) → confidence=HIGH.
Max-Hits-Pro-Keyword: 20 (sonst Kontext-Overflow).

#### EDGES-PFLICHT (RF-WF-EDGES, NEU 2026-05-08)

Jedes Finding (W{n} oder Vault-Hit) MUSS Edges referenzieren — kein nackter Bullet-Point:

```yaml
W4:
  text: "Listen-Serialisierung: JsonSerializer fuer Mapping in DataMappingProfile.cs L237-262"
  source_node: ".../Sources/Backend/.../DataMappingProfile.cs:237-262"
  derived_from:
    - "Backlog/DCSRE-94-.../2_Model/QDVS_Model.md (Schwester-Story Anker)"
  supporting_edges:
    - "Libraries/PatternLibrary/_project/BE-MAP/listen-serialisierung.md"
    - "Crumbs/...findings_crumbs_master.md (line 47)"
  confidence: HIGH  # in 3 Quellen bestaetigt
```

Mindest-Felder: `text`, `source_node`, `derived_from` (≥1 Anker), `confidence`.

#### RAG-Toggle Fallback (BL-Stub-RAG-Toggle Vorbote)

- **`rag=false` (Default)** ODER **MCP CleanCoder DISCONNECTED**:
  - SKIP RAG-Stufen (D03, D04 in Kartographierungs-Fokus-Bereiche)
  - Fokus: Vault-only mit 4-Stufen-Strategie oben
  - Logge: `[A_WFETCH] RAG=off — Vault-only mode (4-Stufen-Strategie aktiv)`
- **`rag=true` UND MCP available**:
  - Vault-Stufen + RAG-Stufen kombiniert
  - Vault-Hits gewichten staerker (lokal validierter, frischer Stand)

Live-Beweis: DCSRE-486-Lauf 2026-05-08 mit `rag=false` (impliziert via MCP-Disconnect),
4-Stufen-Strategie hat 15 W{n} extrahiert + 13/15 confirmed in <6min mit 1 Opus-Worker.

---

### Kartographierungs-Fokus-Bereiche

| Agent | Fokus | Suchbereich |
|-------|-------|-------------|
| D01 | vault-models | Vault: *_Model.md, *_Wissen.md, Tag-Index topic/{THEMA} |
| D02 | vault-features | Vault: Feature-Notes, _parking-lot.md, Prev-Feature Links |
| D03 | rag-global | RAG: global_knowledge Collection, alle Keywords (aus RAG_COLLECTIONS Schritt 0a.1) |
| D04 | rag-local | RAG: alle RAG_COLLECTIONS (aus vault-routing.json Schritt 0a.1) |
| D05 | cross-feature | Vault + RAG: Verwandte Features, semantische Nachbarn (nur hard) |

**Bei normal:** D01, D02, D03 (3 Agents)
**Bei hard:** D01-D05 (5 Agents)
**Bei easy:** Ueberspringen (Welle 3 macht alles)

### Kartographierungs-Ablauf pro Agent

```
1. Vault-Kartographierung (D01, D02):
   VAULT-VERFUEGBARKEIT pruefen (via Schritt 0a.1):
     VAULT_PATH aus VAULT-ROUTING-LESE-MUSTER verwenden (5-stufig).
     Falls VAULT_PATH nicht gesetzt → SCHRITT W (WARNING-Guard).

   Falls Vault erreichbar:
     Vault-Index als Kompass (W32, RF-08):
       → Lies .claude/analysis/_vault_index.md (falls vorhanden)
       → Index enthaelt: Vault-Pfad, Typ, Feature, Updated, Nachbar-Links
       → Nutze Index fuer gezielte Navigation statt blinden Glob
       → Identifiziere Nachbar-Knoten via Feature-Match und Typ-Match
       → Max 1-Hop Nachbarn lesen (Kontextfenster-Limit)
       → Falls Index fehlt: Graceful Degradation (Glob + Tag-Index wie bisher)

     Tag-Index durchsuchen:
       → topic/{THEMA} → welche Dokumente tragen diesen Tag?
       → Synonym-Check (z.B. "SSL" → topic/Zertifikate)

     Glob im Vault:
       → *{THEMA}*_Model.md (thematische Models)
       → *{THEMA}*_Wissen.md (Wissens-Dokumente)

     3-Stufen Vault-Suche (EC2):
       Die folgenden 3 Stufen sind ADDITIV (Union). Jede Stufe sucht
       UNABHAENGIG und traegt Treffer bei. Ergebnis = UNION(Stufe 1, Stufe 2, Stufe 3).

       STUFE 1: Exact-Match (bestehend, oben)
         → Tag-Index: topic/{KEYWORD} exact lookup
         → Glob: *{KEYWORD}*_Model.md, *{KEYWORD}*_Wissen.md
         → base_score = 1.0

       STUFE 2: Dateinamen-Match (NEU)
         Fuer JEDE *.md Datei im Vault:
           A. Tokenisierung:
              Dateiname in Tokens splitten (CamelCase + Underscore + Hyphen)
              Beispiel: "WissensKoaleszenz_Model.md" → {Wissens, Koaleszenz, Model}
              Beispiel: "DualSourceRAG_Wissen.md" → {Dual, Source, RAG, Wissen}
           B. Token-Overlap (Primaer):
              overlap = |filename_tokens ∩ keyword_tokens| / min(|filename|, |keywords|)
              Beispiel: keywords={Wissen, RAG} vs filename={Dual, Source, RAG, Wissen}
                → Overlap = 2 / 2 = 1.0
           C. Levenshtein-Fallback (wenn Overlap < 0.3):
              Fuer jedes Keyword vs jeden Filename-Token:
                similarity = 1 - levenshtein_dist / max(len(keyword), len(token))
              Beispiel: "Wissen" vs "Wissens" → 1 - 1/7 = 0.86
           D. Final: max(token_overlap, best_levenshtein)
              Schwelle: >= 0.4 → KANDIDAT
         → base_score = fuzzy_match_score (0.4 - 1.0)

       STUFE 3: Tag-Co-Occurrence (NEU)
         A. Tag-Index VOLLSTAENDIG lesen
         B. Co-Occurrence identifizieren: Tags die auf DEMSELBEN Dokument vorkommen
            Beispiel: Dokument hat topic/RAG + topic/Knowledge-Cycle
              → RAG und Knowledge-Cycle sind Co-Occurrence Nachbarn
         C. Fuer jeden Keyword-Tag aus dem Pool:
            → 1-Hop Nachbarn: Alle Tags die auf mindestens 1 gemeinsamen Dokument vorkommen
            → Max 2 Hops (sonst wird ALLES gefunden bei duennem Graph)
         D. Dokumente mit Nachbar-Tags als Kandidaten aufnehmen
         → base_score = co_occurrence_gewicht (normiert 0.0-1.0)
         → Graceful Degradation: Falls Tag-Index leer oder keine Tags auf Vault-Dateien
           → Stufe 3 SKIP ("Tag-Co-Occurrence nicht verfuegbar, nur Stufe 1+2")

       AGGREGATION:
         alle_treffer = UNION(stufe1_treffer, stufe2_treffer, stufe3_treffer)
         → Deduplizierung: Gleiche Datei aus mehreren Stufen → hoechsten Score behalten
         → Herkunft dokumentieren: welche Stufe(n) den Treffer gefunden haben

     Feature-Notes scannen:
       → Welche Features hatten dieses Thema?
       → Gibt es Parking-Lot Items dazu?

2. RAG-Kartographierung (D03, D04):
   RAG_COLLECTIONS aus Schritt 0a.1 verwenden (vault-routing.json).
   Falls DEGRADED MODE: Fallback auf [global_knowledge, local_knowledge_{FEATURE}].

   Fuer jede Collection in RAG_COLLECTIONS:
     Fuer jedes Keyword:
       → MCP query(collection="{COLLECTION}", query_text={KW}, limit=10)
       → Ergebnisse mit Score, metadata, source_file sammeln

   Zusaetzlich lokale Collections pruefen:
     → MCP list_collections()
     → local_knowledge_{FEATURE} falls existent UND nicht bereits in RAG_COLLECTIONS
     → MCP query(collection="local_knowledge_{FEATURE}", query_text={KW}, limit=5)

3. Cross-Feature Kartographierung (D05, nur hard):
   → Suche in ALLEN local_knowledge_* Collections
   → Identifiziere thematische Ueberlappungen mit anderen Features
   → Dokumentiere Cross-Feature Links

3a. Graph-Traversal (RF-03, PRIMAER-MODUS v5.0) — W{n}-Abhaengigkeiten traversieren:

   **SEMANTIK v5.0:** Graph-Traversal ist der PRIMAERE Suchmodus (nicht additiv).
   Stufen 1-3 (oben) identifizieren Start-Knoten. Graph-Traversal erweitert
   die Treffermenge ueber Vault-interne Relationen. Das Ergebnis fliesst in
   _vault_refs.md (Referenz-Index) als PRIMAER-OUTPUT.

   WENN Vault erreichbar UND co-created-with / cycle-cluster Frontmatter in Vault-Dateien:

   GRAPH-TRAVERSAL Algorithmus (max 2 Hops):
     1. Start-Knoten: Dateien mit direktem Keyword-Match (Stufe 1/2/3 oben)
     2. 1-Hop Nachbarn: Lies Frontmatter jedes Start-Knotens
        → "co-created-with:" Links → Nachbar-Dateien als Kandidaten
        → "cycle-cluster:" Label → Alle Dateien mit demselben Cluster als Kandidaten
        → "backlinks:" (falls vorhanden) → Rueckwaerts-Links verfolgen
     3. 2-Hop Nachbarn: Fuer jeden 1-Hop Kandidaten → erneut Frontmatter lesen
        (MAX 2 Hops, dann stoppen — sonst Explosion bei dichten Graphen)
     4. Score Decay: 1-Hop: base_score * 0.7, 2-Hop: base_score * 0.5
     5. Graceful Degradation: Falls kein co-created-with/cycle-cluster im Frontmatter
        → Graph-Traversal SKIP ("Graph-Metadaten nicht vorhanden, nur direkte Treffer")

AUSGABE pro Agent:
  drafts/{NAME}-fetch-D{NN}-{fokus}.md mit:
  - Gefundene Dokumente (Pfad, Typ, Score, Tags, match_keywords)
  - Chunk-Zusammenfassungen (bei RAG)
  - Empfehlung: "RELEVANT" / "GRENZWERTIG" / "IRRELEVANT"

  KEYWORD-DOKUMENTATION (PFLICHT pro Treffer):
    Notiere pro Treffer die 2-5 Keywords die den Match ausgeloest haben.
    → Vault-Treffer: Keywords die im Dateinamen/Tag-Index/Frontmatter gematcht haben
    → RAG-Treffer: Keywords die im query_text zum Score beigetragen haben
    → Cross-Feature: Keywords die die thematische Verbindung herstellen
    → Eintrag in Spalte "match_keywords" der Gefundene-Dokumente-Tabelle
    → Format: kommasepariert, lowercase (z.B. "rag, wissen, koaleszenz")
    → WARNUNG wenn match_keywords leer: "Kein Keyword-Match dokumentiert"
```

### Kartographierungs-Output Format

```markdown
---
name: {NAME}
phase: fetch
wave: drafts
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
agent: D{NN}
fokus: {fokus}
date: {YYYY-MM-DD}
status: final
---

# W_fetch Kartographierung D{NN}: {Fokus-Titel}

## Gefundene Dokumente

| # | Dokument | Typ | Source | Score | Tags | match_keywords | Empfehlung |
|---|----------|-----|--------|-------|------|----------------|------------|

## Chunk-Details (RAG)

{Pro relevantem Chunk: Text-Ausschnitt, Score, Metadata}

## Semantische Nachbarn (Stufe 2 + Stufe 3 Treffer)

| # | Dokument | Stufe | Score | Methode | Tags/Tokens |
|---|----------|-------|-------|---------|-------------|
{Stufe 2: Dateiname, fuzzy_score, "token_overlap" oder "levenshtein", matched Tokens}
{Stufe 3: Dateiname, co_occurrence_gewicht, "co-occurrence", Nachbar-Tags}

## Zusammenfassung

{3-5 Saetze: Was wurde gefunden, was fehlt}
```

---

## Worker-Vertrag: Filter (Filterung)

### Zweck

Die Kartographierungen aus Welle 1 zusammenfuehren, deduplizieren,
und nach Relevanz filtern. Sonnet ist praeziser als Haiku und
kann Qualitaet + Relevanz besser bewerten.

### Filterungs-Ablauf

```
1. Lies ALLE drafts/{NAME}-fetch-D*.md

2. Fundlisten vereinheitlichen + deduplizieren:

   DEDUPLIZIERUNG:
     Fuer jedes Vault-Dokument:
       → Pruefe ob source_file in RAG-Fundliste vorkommt
       → MATCH: Source = "BOTH", Score aus RAG, Zeilen aus Vault
       → KEIN MATCH: Source = "Vault", Score = 1.0

     Fuer jedes RAG-Dokument ohne Vault-Match:
       → Source = "RAG:{collection}"
       → Zeilen = "-" (nur Chunks verfuegbar)

   SORTIERUNG:
     1. Source "BOTH" zuerst (in beiden Quellen = hohe Relevanz)
     2. Dann nach Score absteigend
     3. Vault-only am Ende

3. Score-Normalisierung (EC2, VOR Filter-Schwellen):

   BASE SCORE (nach Herkunft):
     Stufe 1 (Exact-Match) Vault-Hit:     base_score = 1.0
     Stufe 2 (Dateinamen-Match) Vault-Hit: base_score = fuzzy_score (0.4-1.0)
     Stufe 3 (Co-Occurrence) Vault-Hit:    base_score = co_occurrence_gewicht (normiert)
     RAG-Hit:                              base_score = rag_chunk.score (0.0-1.0)

   BONUS/PENALTY ADJUSTMENTS:
     + BOTH-Bonus:       +0.15  (in Vault UND RAG gefunden)
     + Model-Typ-Bonus:  +0.10  (*_Model.md Dateien)
     + Wissen-Typ-Bonus: +0.05  (*_Wissen.md Dateien)
     - Alter-Penalty:    -0.10  (Datei > 6 Monate alt)
     - Feature-Mismatch: -0.05  (anderes Feature, schwacher Bezug)

   FINAL SCORE:
     final_score = clamp(base_score + bonuses - penalties, 0.0, 1.0)

3a. Knapsack-Scoring (RF-SC-003, W246) — Priorisierung bei Budget-Grenzen:

   KNAPSACK-PROBLEM: Wenn mehr Kandidaten als Budget (Token-Limit, Zeit-Budget),
   priorisiere nach Wert-Gewicht-Verhaltnis:

   DIMENSIONEN:
     Relevanz    = final_score (0.0-1.0, aus 3. oben)
     Proximity   = Naehe zum Feature-Kontext (0.0-1.0)
                   1.0 = same-Feature, 0.7 = same-Domain, 0.3 = cross-domain
     Freshness   = Aktualitaet (0.0-1.0)
                   1.0 = < 30 Tage, 0.7 = < 6 Monate, 0.3 = > 6 Monate

   KNAPSACK-SCORE:
     knapsack_score = (Relevanz * 0.5) + (Proximity * 0.3) + (Freshness * 0.2)

   ANWENDUNG: Bei > 10 Kandidaten → Top-N nach knapsack_score auswaehlen.
   Bei <= 10 Kandidaten → knapsack_score als Tiebreaker bei Gleichstand.

4. Filter-Schwellen (auf final_score anwenden):
     → Score >= 0.5: EMPFOHLEN (in Ausgabe aufnehmen)
     → Score 0.3-0.5: GRENZWERTIG (erwaehnen, nicht automatisch uebernehmen)
     → Score < 0.3: VERWORFEN (nicht in Ausgabe)

4. Gefilterte Fundliste erstellen:

   | # | Dokument | Typ | Source | Score | Aktion-Empfehlung |
   |---|----------|-----|--------|-------|-------------------|
   | 1 | X_Model.md | model | BOTH | 0.87 | REFERENZ+CACHE |
   | 2 | Y_Wissen.md | knowledge | Vault | 0.72 | REFERENZ+CACHE |
   | 3 | Z-E42.txt | - | RAG:global | 0.55 | REFERENZ |
   (v5.0: REFERENZ+CACHE = Eintrag in _vault_refs.md + lokale Cache-Kopie)
```

### Filter-Output Format

```markdown
---
name: {NAME}
phase: fetch
wave: drafts
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
agent: Filter
date: {YYYY-MM-DD}
status: final
---

# W_fetch Filterung: {NAME}

## Kartographierungen gelesen
- D01: {Zusammenfassung}
- D02: {Zusammenfassung}
- ...

## Deduplizierte Fundliste

| # | Dokument | Typ | Source | Score | Empfehlung |
|---|----------|-----|--------|-------|------------|

## Verworfene Dokumente (Score < 0.3)
{Liste mit Begruendung}

## Zusammenfassung
{5-10 Saetze}
```

---

## Worker-Vertrag: Konsolidierer (Entscheidung + Konsolidierung)

### Zweck

Finale Entscheidung treffen: Was wird uebernommen, was nicht.
Bei normal/hard: User bestaetigt. Bei easy: Auto-Accept.

### Konsolidierungs-Ablauf

```
Bei normal/hard:
  1. Lies drafts/{NAME}-fetch-filter.md (Welle 2 Output)
  2. Praesentiere gefilterte Fundliste dem User
  3. "Welche sollen in .claude/ uebernommen werden?"
  4. User bestaetigt oder aendert Auswahl

Bei easy (Auto-Accept, W27):
  1. Vault-Graph DIREKT traversieren + RAG suchen (keine Welle 1/2)
     → Tag-Index + Glob + Graph-Traversal + MCP query()
  2. Auto-Accept: Score >= 0.5 → automatisch uebernehmen
  3. KEIN User-Input (prozessbegleitend, paralleler Worker)
  4. _vault_refs.md erstellen (PRIMAER) + Cache-Refresh (FALLBACK)

Fuer jedes bestaetigte/akzeptierte Dokument:

  SCHRITT A: _vault_refs.md Referenz-Index erstellen (PRIMAER-OUTPUT v5.0):
    → Schreibe .claude/analysis/_vault_refs.md (Format siehe unten)
    → Enthaelt Vault-Pfade, Keywords, Scores, Relationen
    → Agenten koennen bei Bedarf DIREKT aus Vault lesen (via Pfade)
    → _vault_refs.md ist das PRIMAERE Ergebnis von W_fetch

  SCHRITT B: Cache-Refresh (FALLBACK, nach Graph-Traversal):
    VAULT-Hits (Source = "Vault" oder "BOTH"):
      → Cache-Kopie von Vault nach .claude/ (Semantik: CACHE, nicht Primaerquelle):
        Model → .claude/models/{THEMA}_Model.md
        Wissen → .claude/wissen/{THEMA}_Wissen.md
        Linux: cp "{VAULT}/{DATEI}" ".claude/models/{DATEI}"
      → ZWECK: Backward-Kompatibilitaet fuer 66+ Downstream-Commands
        die .claude/models/ und .claude/wissen/ lesen
      → Frontmatter ergaenzen:
        source: vault-cache         # v5.0: "vault-cache" statt "vault" (Semantik-Shift)
        fetched: {DATUM}
        original-feature: {HERKUNFT}
        vault_ref: "{VAULT}/{DATEI}" # v5.0: Rueck-Referenz zum Vault-Original
        verifikation_status: AUSSTEHEND
        letzter_abgleich: {DATUM}
        abgleich_methode: "---"

    RAG-only Hits (Source = "RAG:*"):
      → NICHT als Datei kopieren (nur Chunks verfuegbar)
      → Als Referenz in _vault_refs.md UND Manifest listen
      → "Chunks abrufbar via MCP query()"

  Parking-Lot Items (falls relevant):
    → In {VAULT}/_parking-lot.md uebernehmen (APPEND)

  ANKERPUNKT-PERSISTENZ (nach Konsolidierung, VOR Manifest-Schreiben):

    Zweck: Persistente Verbindungsknoten zwischen dem neuen Feature und
    existierendem Wissen fuer spaetere Graph-Traversals (_W_modelSplit Schritt 0.5).

    1. Kandidaten sammeln:
       → Alle Treffer mit Score >= 0.40 aus Welle 2/3 (bzw. easy: direkte Suche)
       → Jeder Kandidat braucht: file, match_score, match_keywords

    2. Relation-Klassifikation per R1-R5-DEFAULT Heuristik:
       R1: Keyword-Overlap >= 2 UND score >= 0.70 → THEMATISCH_VERWANDT
       R2: source=BOTH UND score >= 0.65         → THEMATISCH_VERWANDT
       R3: Haupt-Model (kein Feature-Kuerzel im Dateinamen) UND score >= 0.50 → UEBERGEORDNET
       R4: split-into im Ziel-Frontmatter vorhanden → UEBERGEORDNET
       R5: hop >= 1 (Graph-Traversal Treffer)     → CO_CREATED
       DEFAULT: score >= 0.50                      → THEMATISCH_VERWANDT

       Prioritaet: R1 > R2 > R3 > R4 > R5 > DEFAULT (erste zutreffende Regel gewinnt)

    3. User-Korrektur (normal/hard):
       → Praesentiere Tabelle mit Vorschlaegen:
         | # | Datei | Score | Keywords | Relation (Vorschlag) | Korrektur? |
         |---|-------|-------|----------|----------------------|------------|
       → User kann Relation aendern oder Eintraege entfernen
       Bei easy: Auto-Accept (keine User-Interaktion)

    4. Soft Limit: Max 5 Ankerpunkte (nach match_score absteigend sortiert)
       → Bei >= 6 Kandidaten: WARNUNG ">{N} Ankerpunkte, Top-5 nach Score behalten"
       → Top-5 behalten, Rest verwerfen (mit WARNUNG-Ausgabe)

    5. Validierung (pro Ankerpunkt):
       → file: PFLICHT (relativer Pfad zur Quelldatei)
       → match_score: PFLICHT, 0.0-1.0 (Float)
       → relation: PFLICHT, Wert aus Enum {THEMATISCH_VERWANDT, UEBERGEORDNET, UNTERGEORDNET, CO_CREATED}
       → match_keywords: PFLICHT-CHECK — leer = WARNUNG "Kein Keyword-Match dokumentiert" (kein Block)
       → match_wn, hop, source, merged_into: OPTIONAL (Default-Werte wenn nicht vorhanden)

    6. Schreibe "## W_fetch Ankerpunkte" Sektion in Manifest (YAML-Block)
       → Positionierung: NACH "## Wissens-Basis", VOR etwaigem SC_PIPELINE_STATE
       → Format: siehe Manifest-Template unten (EP-4)

    7. Graceful Degradation:
       → Keine Treffer mit Score >= 0.40 → anchor_nodes: [] (leere Liste)
       → Sektion "## W_fetch Ankerpunkte" IMMER schreiben (auch bei leerem Array)
       → INFO: "Keine Ankerpunkte identifiziert. anchor_nodes: []"
```

### Manifest + Zusammenfassung (IMMER, auch bei easy)

```
Manifest aktualisieren:

  ## Wissens-Basis (via /_W_fetch)
  **DATUM:** {DATUM}
  **SUCHE:** {N} Themen, {M} Dokumente gefunden
  **QUELLEN:** Vault ({V} Hits), RAG ({R} Hits), BOTH ({B} Hits)
  **SCHWIERIGKEIT:** {easy|normal|hard}
  **WELLEN:** {1|2|3} (abhaengig von Schwierigkeit)

  **Keywords:** {KW1}, {KW2}, {KW3}, ...

  | # | Dokument | Typ | Source | Score | Aktion |
  |---|----------|-----|--------|-------|--------|

  ### RAG-Suche Details
  **Collections durchsucht:** {Liste mit Chunk-Anzahlen}
  **RAG-only Referenzen:** {K} Dokumente (nur via MCP query() abrufbar)

  ## W_fetch Ankerpunkte
  **Erstellt:** {DATUM}
  **Anzahl:** {N} Ankerpunkte (Soft Limit: 5)
  **Lifecycle:** Geschrieben von _W_fetch Welle 3, Gelesen von _W_modelSplit Schritt 0.5

  anchor_nodes:
    - file: "{relativer_pfad_zur_quelldatei}"
      match_score: {0.0-1.0}
      relation: "{THEMATISCH_VERWANDT|UEBERGEORDNET|UNTERGEORDNET|CO_CREATED}"
      match_keywords: ["{kw1}", "{kw2}", ...]
      # --- Optional ---
      match_wn: "{W{n}-Referenz falls vorhanden}"
      hop: {0|1|2}           # 0=direkt, 1=1-Hop Nachbar, 2=2-Hop
      source: "{Vault|RAG|BOTH}"
      merged_into: false      # Default false, wird von _W_modelSplit auf true gesetzt

  **Relation-Enum Schwellen:**
    THEMATISCH_VERWANDT: score >= 0.70 (Keyword-Overlap >= 2 ODER source=BOTH)
    UEBERGEORDNET:       score >= 0.50 (Haupt-Model ODER split-into vorhanden)
    UNTERGEORDNET:       score >= 0.60 (Sub-Model, abgeleitetes Dokument)
    CO_CREATED:          score >= 0.40 (Graph-Traversal hop >= 1)

AUSGABE:
  "Wissens-Basis fuer {FEATURE} via Graph-Traversal aufgebaut."
  "_vault_refs.md erstellt: {N} Vault-Referenzen, {R} RAG-Referenzen."
  "Cache aktualisiert: {N} Models, {M} Wissens-Dokumente in .claude/."
  "{K} Parking-Items uebernommen."
  "Naechster Schritt: /_taskDefinition (Aufgabe definieren)"
```

---

## _vault_refs.md Referenz-Index Format (v5.0, RF-03)

**Pfad:** `.claude/analysis/_vault_refs.md`
**Erstellt von:** /_W_fetch (Welle 3 Konsolidierer bzw. easy-Modus)
**Gelesen von:** Alle Downstream-Commands die Vault-Wissen benoetigen
**Semantik:** Primaeres Ergebnis von W_fetch. Zeigt auf Vault-Originale (nicht lokale Kopien).

```markdown
---
type: vault-reference-index
feature: {FEATURE}
created: {YYYY-MM-DD}
w_fetch_version: v5.0
vault_path: {VAULT_PATH}
---

# Vault Reference Index: {FEATURE}

## Referenzen

| # | Vault-Pfad (absolut) | Typ | Score | Keywords | Relation | Hop | Source | Cache-Pfad |
|---|---------------------|-----|-------|----------|----------|-----|--------|------------|
| 1 | {VAULT}/Models/X_Model.md | model | 0.87 | kw1, kw2 | THEMATISCH_VERWANDT | 0 | BOTH | .claude/models/X_Model.md |
| 2 | {VAULT}/Wissen/Y_Wissen.md | wissen | 0.72 | kw3 | UEBERGEORDNET | 1 | Vault | .claude/wissen/Y_Wissen.md |

## RAG-Referenzen (kein Vault-Pfad)

| # | Collection | Query | Score | Chunk-Summary |
|---|-----------|-------|-------|---------------|
| 1 | global_knowledge | {KW} | 0.65 | {Zusammenfassung} |

## Traversal-Graph

{Optionale Mermaid-Darstellung der Hop-Beziehungen}

## Metadaten

- **Gesamt Referenzen:** {N}
- **Vault-Hits:** {V}
- **RAG-Hits:** {R}
- **Max Hop:** {0|1|2}
- **Graph-Traversal:** {JA|NEIN (kein Frontmatter)}
```

**Lifecycle:**
- Erstellt bei /_W_fetch (einmalig pro Feature-Start)
- Gelesen von Downstream-Commands als Vault-Wegweiser
- Aktualisiert bei erneutem /_W_fetch (Ueberschreiben)
- Archiviert bei /_finish

---

---

## Dual-Pfad Truth-Direktsuche (BL-389, v5.1 — additiv)

> **ADDITIV:** Dieser Abschnitt ergaenzt die bestehende Model/Wissen-Navigation (Stufen 1-4,
> Graph-Traversal, RAG). Die Truth-Direktsuche ist ein ZWEITER, unabhaengiger Pfad.
> Kein bestehender Such-Schritt wird veraendert oder ersetzt.

### Konzept: Zwei koexistierende Such-Pfade

```
PFAD 1 (bestehend, unveraendert):
  Model-View-Navigation (Stufe 1/2/3/4 + Graph-Traversal)
  ├── Einstieg: Vault-Models (*_Model.md), Tag-Index, Wissen-Dokumente
  ├── Geeignet: wenn Kontext/Domain bekannt (z.B. "Wissen/RAG/KoaleszenzModel")
  └── Output: _vault_refs.md + Cache (.claude/models/, .claude/wissen/)

PFAD 2 (NEU, BL-389):
  Truth-Direktsuche auf Atomen (truth_search.py)
  ├── Einstieg: thematische Query → keyword-basierter Atom-Index
  ├── Geeignet: thematische Suche ohne Model-Kenntnis (skaliert auf 1000s Wahrheiten)
  └── Output: [{path, bl_id, vault_origin, node_type, score}, ...] ranked
```

### Wann welcher Pfad

| Situation | Empfohlener Pfad |
|-----------|-----------------|
| Domain/Model-Name bekannt (z.B. "RAG", "Vault-Routing") | Pfad 1 (Model-View-Navigation) |
| Thematische Suche ohne Model-Kenntnis (z.B. "Fehlerbehandlung bei Vault-Ausfall") | Pfad 2 (Truth-Direktsuche) |
| Grosser Corpus mit 1000s atomarer Wahrheiten | Pfad 2 (skaliert via Inverted-Index) |
| Kombination gewuenscht | Beide Pfade nacheinander, Union der Ergebnisse |

### Truth-Direktsuche — Ablauf (Pfad 2)

```
SCHRITT T1: Query formulieren
  Eingabe: thematischer Freitext (z.B. "Fehlerbehandlung Vault-Ausfall DEGRADED")

SCHRITT T2: Keywords extrahieren
  truth_keywords.extract_keywords(query)
  → deterministische keyword-Liste (Stopwords/Kurzwoerter gefiltert)
  → gleicher Input = gleicher Output (deterministische Extraktion)

SCHRITT T3: Atom-Index aufloesen (Index-First + Walk-Fallback)
  Option A — Index vorhanden (primaer, BL-242-Muster):
    build_retrieval_index.build_truth_atom_index(roots)
    → liest _keyword_index.json (pre-computed, {keyword: [{path,bl_id,vault_origin,node_type}]})
    → Kein Laufzeit-Walk noetig

  Option B — Index fehlt/veraltet (graceful Fallback):
    truth_search._build_atom_index_from_roots(roots)
    → Live-Walk via os.walk(root) ueber type:truth-Dateien
    → YAML-Frontmatter parsen (Block-Sequence-Unterstuetzung)
    → Inverted-Index live bauen
    → INFO: "Pre-computed Index nicht verfuegbar. Fallback auf Live-Walk."

SCHRITT T4: Suche ausfuehren
  truth_search.search_truths(query, atom_index=...) ODER
  truth_search.search_truths(query, roots=[...])
  → Score-Akkumulation: Anzahl keyword-Matches pro Truth-Atom
  → Ranking: absteigend score, Tie-Breaker alphabetisch nach path (deterministisch)
  → Ergebnis: [{path, bl_id, vault_origin, node_type, score}, ...]
  → [] bei leerem Index / keinen Matches / None-Eingaben (kein Crash)

SCHRITT T5: Ergebnisse einordnen
  → Truth-Atom-Pfade als zusaetzliche Vault-Referenzen in _vault_refs.md aufnehmen
  → Score als Relevanz-Indikator (nicht normiert; absoluter keyword-Match-Count)
  → Doppel-Hits (Atom UND Model) → Score-Boost (Pfad 1 + Pfad 2 zusammen)
```

### API-Referenz (truth_search.py)

```python
# Primaere Such-Funktion:
from truth_search import search_truths

# Option A: Vorberechneter Inverted-Index (primaer, schneller)
results = search_truths(query, atom_index={keyword: [entries]})

# Option B: Live-Walk ueber Vault-Roots (Fallback)
results = search_truths(query, roots=["/pfad/zum/vault"])

# Ergebnis-Format (absteigend nach score):
# [{"path": "rel/pfad.md", "bl_id": "BL-XYZ", "vault_origin": "/root",
#    "node_type": "truth", "score": 3}, ...]
# [] bei no-match / leerer Query / leerem Index

# Index-Builder:
from build_retrieval_index import build_truth_atom_index

atom_index = build_truth_atom_index(roots=["/pfad/zum/vault"])
# → {keyword: [{path, bl_id, vault_origin, node_type}, ...]}

# Keyword-Extraktion:
from truth_keywords import extract_keywords

keywords = extract_keywords("thematische Suche Vault Fehlerbehandlung")
# → ["vault", "fehlerbehandlung", ...] (deterministisch, Stopwords gefiltert)
```

### Einschraenkungen + GATED-Hinweis

```
DETERMINISTISCH (verfuegbar jetzt, BL-389 batch_1-4):
  - keyword-basierte Suche via extract_keywords + build_truth_atom_index
  - Kein NLP, keine Netz-Abhaengigkeit
  - Funktioniert ohne MCP/Embeddings

GATED — Embeddings (B1, deferred bis cleancoder-MCP verfuegbar):
  - Semantischer Embeddings-Index via cleancoder-MCP als optionaler dritter Pfad
  - Voraussetzung: cleancoder-MCP in .mcp.json registriert
  - Heute: RAG-Toggle-Fallback (rag=false / MCP DISCONNECTED → Vault-only-4-Stufen,
    Schritt T3 Option B greift analog) deckt den Forward-Pfad ab
  - KEINE Hard-Abhaengigkeit der deterministischen Suche (Pfad 2) von MCP
  - Forward-Marker: Embeddings aktivierbar sobald cleancoder-MCP verfuegbar
    (kein Umbau der bestehenden Dual-Pfad-Logik noetig — additiver dritter Pfad)
```

### Integration in W_fetch Ablauf

```
Schritt 0d (Tag-Index als Keyword-Seed) — Schritt T3 Option A PRIMAER:
  _keyword_index.json (BL-242 AK-CTX-2) enthaelt bei verfuegbarem Truth-Atom-Index
  auch die Truth-Atom-Keywords. Laufzeit-Walk (Schritt T3 Option B) als Fallback.

Welle 3 Konsolidierer (_vault_refs.md):
  Truth-Atom-Treffer (Pfad 2) als eigene Sektion aufnehmen:

  ## Truth-Atom-Referenzen (Pfad 2, BL-389)
  | # | Atom-Pfad | BL-ID | Score | node_type |
  |---|-----------|-------|-------|-----------|
  | 1 | rel/pfad.md | BL-XYZ | 3 | truth |
  ...

  → Ergibt additive Erweiterung des Referenz-Index (kein Ueberschreiben der
    bestehenden Vault/RAG-Referenzen aus Pfad 1)
```

---

## Abgrenzung

```
/_W_fetch      = Wissen TRAVERSIEREN (Feature-Start, Vault-Graph → _vault_refs.md + Cache)
/_W_push_temp  = Wissen TEMPORAER PUSHEN (waehrend Feature, .claude/ → RAG local)
/_W_push_global= Wissen GLOBAL PUSHEN (Feature-Ende, .claude/ → RAG global + Vault)
/_W_modelSplit = Wissen EXTRAHIEREN (Feature-Ende, Model → thematische Teile)
/_W_obsidianSync = Synthese TRANSPORTIEREN (Sync, .claude/ → Vault)
/_knowledge    = Wissen ERSTELLEN (waehrend Feature, Deep-Dive)

          /_W_fetch {THEMA} {difficulty}
          (Wellen: Haiku kartographiert, Sonnet filtert, Opus entscheidet)
              ↓
    Feature-Arbeit (/_knowledge, /_model, /_SC_*, etc.)
              ↓
    /_W_push_temp → RAG (local_knowledge_{FEATURE})
              ↓
    /_W_modelSplit → /_W_obsidianSync → Vault
              ↓
    /_W_push_global → RAG (global_knowledge) + Vault
              ↓
          /_W_fetch (naechstes Feature)
```

---

## Qualitaetskriterien

- RAG-Suche ist IMMER verfuegbar (ChromaDB laeuft als Docker-Container)
- Vault-Suche: WARNING-Guard bei fehlendem Vault (kein silent degraded mode)
- Graph-Traversal ist PRIMAERER Modus (v5.0), Tag-Index + Glob als Start-Knoten-Identifikation
- _vault_refs.md ist PRIMAER-OUTPUT (Referenz-Index), lokale Kopien sind CACHE
- Downstream-Commands lesen weiterhin aus .claude/models/ + .claude/wissen/ (Cache, backward-kompatibel)
- Keyword-Extraktion via Haiku-Prompt-Template (primaer, W30-Fix) + Tag-Index-Seed + Post-Processing
- Easy-Mode: Auto-Accept (Score >= 0.5), KEIN User-Input (W27)
- Normal/Hard: User entscheidet was uebernommen wird
- Vault-Dateien werden NUR gelesen, NIE veraendert
- RAG Collections werden NUR gelesen, NIE veraendert
- Herkunft im Frontmatter UND Manifest dokumentieren (Traceability)
- RAG-Hits gruppieren nach Dokument (nicht einzelne Chunks zeigen)
- Parking-Lot Items pruefen (oft wertvolle Hinweise fuer neues Feature)
- Plattform-agnostisch: Linux (cp, md5sum) und Windows (PowerShell)
- Ceiling-Hierarchie: Sub-Prozess W_fetch <= Parent-Schwierigkeit (W21)

---

## Fehlerbehandlung

| Fehler | Ursache | Loesung |
|--------|---------|---------|
| Vault nicht erreichbar | Pfad nicht konfiguriert oder nicht gemountet | SCHRITT W: WARNING-Guard (FRAGE bei HiL=on, STOP bei HiL=off ohne DEGRADED_MODE) |
| MCP query() fehlschlaegt | ChromaDB nicht erreichbar | Warnung, NUR Vault-Suche |
| Collection nicht gefunden | global_knowledge oder local_knowledge_* existiert nicht | Skip mit Hinweis |
| extract_keywords() fehlschlaegt | KeyBERT defekt (W30) | Haiku-basierte Keyword-Extraktion |
| Keine Ergebnisse | Thema nicht in Vault oder RAG | "Keine Treffer. Feature startet bei Null." |
| Write-Tool haengt | Datei > 500 Zeilen | cp (Linux) oder PowerShell Copy-Item |

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
# Linux:
echo "/_W_fetch {FEATURE} abgeschlossen"

# Windows:
powershell -Command "notify '{FEATURE} /_W_fetch abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
