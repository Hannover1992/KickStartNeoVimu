# /_W_fetch

**Status:** v3.0 (Wellen-Architektur + Schwierigkeitsstufen + Dual-Mode)
**Actor:** KNOWLEDGE-SCOUT
**Zweck:** Bei Feature-Start existierendes Wissen + Models aus Obsidian UND RAG suchen und wiederverwenden

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
|  KERN-PRINZIP:                                                 |
|    VOR Feature-Start: Vault UND RAG durchsuchen.               |
|    Was existiert → in .claude/ ziehen als Basis.               |
|    Was fehlt → notieren fuer spaetere Erstellung.              |
|    "Standing on the shoulders of giants."                      |
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. .claude/analysis/_manifest.md                             |
|       → SYSTEM-MODEL, SCHWIERIGKEIT (Ceiling-Hierarchie)       |
|    2. .claude/Task.md ODER User-Beschreibung                   |
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
|    1. .claude/wissen/{THEMA}_Wissen.md (konsolidierte Basis)   |
|    2. .claude/models/{THEMA}_Model.md (Kopie aus Vault)        |
|    3. .claude/analysis/_manifest.md                            |
|       → "## Wissens-Basis" Sektion mit Herkunft               |
|       → Vault-Hits UND RAG-Hits mit Source + Score             |
|                                                                |
|  SCHREIBT (Output) - WELLEN-MODUS (bei normal/hard):           |
|    Welle 1: drafts/{NAME}-fetch-D{NN}-{fokus}.md              |
|    Welle 2: drafts/{NAME}-fetch-filter.md                      |
|    Welle 3: Konsolidierung (Synthese)                          |
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
|  VAULT-PFAD (konfigurierbar):                                  |
|    1. Environment: $OBSIDIAN_VAULT_PATH                        |
|    2. Fallback: Manifest "## Obsidian Sync" VAULT-Wert         |
|    3. Default Linux: /home/uczen/Documents/DCS                 |
|    4. Default Windows: C:\Users\Administrator\Documents\DCS    |
|    Falls Vault nicht erreichbar → NUR RAG-Suche (degraded)     |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**KNOWLEDGE-SCOUT:** Sucht existierendes Wissen und stellt es bereit.

**TUT:** Vault durchsuchen, RAG semantisch durchsuchen, Tag-Index nutzen,
relevante Dokumente identifizieren, in .claude/ kopieren als Arbeits-Basis,
Manifest dokumentieren.

**NICHT:** Wissen erstellen, Models schreiben, Vault aendern, RAG aendern.

---

## Schwierigkeits-Parameter

| Schwierigkeit | Welle 1 (Kartographierung) | Welle 2 (Filterung) | Welle 3 (Entscheidung) | User-Input |
|---------------|---------------------------|---------------------|----------------------|------------|
| **easy** | --- (skip) | --- (skip) | 1 ceiling-Agent: Auto-Scan + Auto-Accept | KEIN (Auto-Accept, Score > 0.5) |
| **normal** | 3 floor-Agents: Vault + RAG kartographieren | 1 middle-Agent: Relevanz filtern | 1 ceiling-Agent: Konsolidieren + User-Bestaetigung | User bestaetigt Auswahl |
| **hard** | 5 floor-Agents: Breit kartographieren (Vault + RAG + Cross-Feature) | 3 middle-Agents: Relevanz + Qualitaet filtern | 1 ceiling-Agent: Konsolidieren + User-Bestaetigung | User bestaetigt Auswahl |

**System-Model (aus Manifest):** Bestimmt welches Modell pro Welle laeuft.
- opus: floor=haiku, middle=sonnet, ceiling=opus
- sonnet: floor=haiku, middle=sonnet, ceiling=sonnet
- haiku: floor=haiku, middle=haiku, ceiling=haiku

**Ceiling-Hierarchie (W21):** W_fetch erbt Schwierigkeit vom Parent-Prozess.
Falls Parent easy ist, darf W_fetch maximal easy sein (Sub-Prozess <= Parent).

---

## Dual-Mode: Solo vs. Wellen-Worker

**SOLO-MODUS** (User ruft direkt auf: `/_W_fetch {THEMA} normal`)
- easy: Nur Welle 3 (du selbst, Auto-Scan + Auto-Accept)
- normal: 3 Kartographierungs-Durchlaufe SEQUENTIELL, dann Filterung + Konsolidierung (du selbst)
- hard: 5 Kartographierungen SEQUENTIELL → 3 Filterungen SEQUENTIELL → Konsolidierung
- Schreibe Wellen-Dateien selbst, sequentiell, dann konsolidiere

**WELLEN-WORKER-MODUS** (Orchestrator steuert, Task enthaelt "Welle X:")
- Lies Task-Beschreibung um Rolle zu erkennen
- "Welle 1: Kartographierung, Fokus: {fokus}, Agent-ID: D{NN}"
  → Fuehre NUR Welle 1 aus. KEIN Spawning.
  → Lese: Vault + RAG fuer zugewiesenen Fokus-Bereich
  → Schreibe: .claude/analysis/drafts/{NAME}-fetch-D{NN}-{fokus}.md
  → TaskUpdate completed + SendMessage an Team Lead
- "Welle 2: Filterung"
  → Fuehre NUR Welle 2 aus. KEIN Spawning.
  → Lese: drafts/{NAME}-fetch-D*.md (ALLE Kartographierungen)
  → Schreibe: .claude/analysis/drafts/{NAME}-fetch-filter.md
  → TaskUpdate completed + SendMessage an Team Lead
- "Welle 3: Konsolidierung"
  → Fuehre NUR Welle 3 aus. KEIN Spawning.
  → Lese: drafts/{NAME}-fetch-filter.md
  → Schreibe: Wissen + Models + Manifest
  → TaskUpdate completed + SendMessage an Team Lead
- Kein Wellen-Hinweis → Solo-Modus (alles selbst machen)

**VERTRAG (Wellen-Worker-Modus):**
```
+===============================================================+
|  WELLEN-WORKER VERTRAG                                         |
+===============================================================+
|  Welle 1 Worker (Kartograph D{NN}):                            |
|    LIEST:   Vault ({fokus}-Bereich) + RAG ({fokus}-Queries)    |
|    LIEST:   _manifest.md "## W_fetch Keyword-Pool" (PFLICHT)   |
|             → Keywords aus Pool verwenden, NICHT selbst         |
|               extrahieren (verhindert Keyword-Drift, W14)      |
|    SCHREIBT: drafts/{NAME}-fetch-D{NN}-{fokus}.md              |
|    MELDET:  TaskUpdate completed + SendMessage team-lead        |
|                                                                |
|  Welle 2 Worker (Filter):                                      |
|    LIEST:   drafts/{NAME}-fetch-D*.md (ALLE)                   |
|    SCHREIBT: drafts/{NAME}-fetch-filter.md                     |
|    MELDET:  TaskUpdate completed + SendMessage team-lead        |
|                                                                |
|  Welle 3 Worker (Konsolidierer):                               |
|    LIEST:   drafts/{NAME}-fetch-filter.md                      |
|    SCHREIBT: wissen/ + models/ + _manifest.md                  |
|    MELDET:  TaskUpdate completed + SendMessage team-lead        |
|                                                                |
|  NIEMALS: Sub-Agents spawnen (kein Task-Tool in Worker-Modus)  |
+===============================================================+
```

---

## Schritt 0: Manifest lesen + Keyword-Pipeline

**IMMER als Erstes:**

### Schritt 0a: Manifest lesen

1. Lies `.claude/analysis/_manifest.md`
   - Ermittle **SYSTEM-MODEL** und **SCHWIERIGKEIT** aus System-Konfiguration
   - Bestimme effektives Modell: `min(SYSTEM-MODEL, Command-Max=opus)`
   - Leite Modell-Zuordnung pro Welle ab (Welle 1=floor, Welle 2=middle, Welle 3=ceiling)
   - Pruefe Ceiling-Hierarchie: Parent-Schwierigkeit >= W_fetch-Schwierigkeit

### Schritt 0b: Thema erkennen

```
Falls {THEMA} angegeben:
  → Direkt nach diesem Thema suchen

Falls {FEATURE} angegeben:
  → Lies Task.md / User-Beschreibung
  → Feature-Name als erstes Keyword uebernehmen
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

### Schritt 0d: Tag-Index als Keyword-Seed

```
Lies {VAULT}/_Tag-Index.md (falls Vault erreichbar)

Fuer jeden Haiku-Keyword:
  1. Exact-Match: "topic/{keyword}" im Tag-Index registriert?
     → JA: Tag als zusaetzliches Keyword uebernehmen
  2. Synonym-Match: Keyword als registriertes Synonym?
     → JA: Zugehoeriges Tag uebernehmen
  3. Substring-Match: Keyword in Tag-Name enthalten (oder umgekehrt)?
     → JA: Tag uebernehmen

Falls Vault nicht erreichbar:
  → Schritt 0d SKIP (nur Haiku-Keywords verwenden)
  → INFO: "Tag-Index nicht verfuegbar. Pool basiert nur auf Haiku."
```

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

## Welle 1: Kartographierung (Haiku kartographiert)

### Zweck

Breit suchen. Alles finden was zum Thema passt — ohne zu filtern.
Haiku ist schnell und guenstig, perfekt fuer breite Kartographierung.

### Kartographierungs-Bereiche (Fokus pro Agent)

| Agent | Fokus | Suchbereich |
|-------|-------|-------------|
| D01 | vault-models | Vault: *_Model.md, *_Wissen.md, Tag-Index topic/{THEMA} |
| D02 | vault-features | Vault: Feature-Notes, _parking-lot.md, Prev-Feature Links |
| D03 | rag-global | RAG: global_knowledge Collection, alle Keywords |
| D04 | rag-local | RAG: local_knowledge_{FEATURE} + verwandte Collections |
| D05 | cross-feature | Vault + RAG: Verwandte Features, semantische Nachbarn (nur hard) |

**Bei normal:** D01, D02, D03 (3 Agents)
**Bei hard:** D01-D05 (5 Agents)
**Bei easy:** Ueberspringen (Welle 3 macht alles)

### Kartographierungs-Ablauf pro Agent

```
1. Vault-Kartographierung (D01, D02):
   VAULT-VERFUEGBARKEIT pruefen:
     1. $OBSIDIAN_VAULT_PATH gesetzt? → Verwende diesen Pfad
     2. Manifest "## Obsidian Sync" -> VAULT-Wert? → Verwende diesen Pfad
     3. Default: Linux=/home/uczen/Documents/DCS, Windows=C:\...\DCS
     4. Nichts? → "Vault nicht erreichbar. Skip."

   Falls Vault erreichbar:
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
   Fuer jedes Keyword:
     → MCP query(collection="global_knowledge", query_text={KW}, limit=10)
     → Ergebnisse mit Score, metadata, source_file sammeln

   Lokale Collections:
     → MCP list_collections()
     → local_knowledge_{FEATURE} falls existent
     → MCP query(collection="local_knowledge_{FEATURE}", query_text={KW}, limit=5)

3. Cross-Feature Kartographierung (D05, nur hard):
   → Suche in ALLEN local_knowledge_* Collections
   → Identifiziere thematische Ueberlappungen mit anderen Features
   → Dokumentiere Cross-Feature Links

AUSGABE pro Agent:
  drafts/{NAME}-fetch-D{NN}-{fokus}.md mit:
  - Gefundene Dokumente (Pfad, Typ, Score, Tags)
  - Chunk-Zusammenfassungen (bei RAG)
  - Empfehlung: "RELEVANT" / "GRENZWERTIG" / "IRRELEVANT"
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

| # | Dokument | Typ | Source | Score | Tags | Empfehlung |
|---|----------|-----|--------|-------|------|------------|

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

## Welle 2: Filterung (Sonnet filtert)

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

4. Filter-Schwellen (auf final_score anwenden):
     → Score >= 0.5: EMPFOHLEN (in Ausgabe aufnehmen)
     → Score 0.3-0.5: GRENZWERTIG (erwaehnen, nicht automatisch uebernehmen)
     → Score < 0.3: VERWORFEN (nicht in Ausgabe)

4. Gefilterte Fundliste erstellen:

   | # | Dokument | Typ | Source | Score | Aktion-Empfehlung |
   |---|----------|-----|--------|-------|-------------------|
   | 1 | X_Model.md | model | BOTH | 0.87 | KOPIEREN |
   | 2 | Y_Wissen.md | knowledge | Vault | 0.72 | KOPIEREN |
   | 3 | Z-E42.txt | - | RAG:global | 0.55 | REFERENZ |
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

## Welle 3: Entscheidung + Konsolidierung (Opus entscheidet)

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
  1. Vault + RAG DIREKT durchsuchen (keine Welle 1/2)
     → Tag-Index + Glob + MCP query()
  2. Auto-Accept: Score >= 0.5 → automatisch uebernehmen
  3. KEIN User-Input (prozessbegleitend, paralleler Worker)
  4. Nur KOPIEREN, nie fragen

Fuer jedes bestaetigte/akzeptierte Dokument:

  VAULT-Hits (Source = "Vault" oder "BOTH"):
    → Kopiere von Vault nach .claude/:
      Model → .claude/models/{THEMA}_Model.md
      Wissen → .claude/wissen/{THEMA}_Wissen.md
      Linux: cp "{VAULT}/{DATEI}" ".claude/models/{DATEI}"

    → Frontmatter ergaenzen:
      source: vault
      fetched: {DATUM}
      original-feature: {HERKUNFT}

  RAG-only Hits (Source = "RAG:*"):
    → NICHT als Datei kopieren (nur Chunks verfuegbar)
    → Als Referenz in Manifest listen
    → "Chunks abrufbar via MCP query()"

  Parking-Lot Items (falls relevant):
    → In .claude/_parking-lot.md uebernehmen (APPEND)
```

### Manifest-Wellen-Tracking (nach JEDER Welle, /compact-sicher)

```
NACH JEDER abgeschlossenen Welle Manifest aktualisieren (R7 Resumability):

  ## W_fetch Wellen-Fortschritt
  **PHASE:** /_W_fetch {THEMA} {SCHWIERIGKEIT}
  **WELLE:** {1|2|3} abgeschlossen, {naechste} ausstehend
  **NAECHSTER SCHRITT:** Welle {N+1} starten (oder Konsolidierung)

  ### Schritt 0 (Keywords) - {Datum}
  - [x] Keywords extrahiert: {N} Keywords via Haiku + Tag-Seed
  - [x] Pool im Manifest dokumentiert (## W_fetch Keyword-Pool)

  ### Welle 1 (Kartographierung) - {Datum}
  - [x] D01-{fokus}.md
  - [x] D02-{fokus}.md
  - [x] D03-{fokus}.md
  - [ ] D04-{fokus}.md (nur hard)
  - [ ] D05-{fokus}.md (nur hard)

  ### Welle 2 (Filterung) - {Datum}
  - [x] {NAME}-fetch-filter.md

  ### Welle 3 (Konsolidierung) - {Datum}
  - [x] Wissen + Models kopiert, Manifest finalisiert

Dieses Tracking ermoeglicht /compact zwischen Wellen ohne Zustandsverlust.
Vorbild: _SC_observe.md Manifest-Tracking Pattern.
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

AUSGABE:
  "Wissens-Basis fuer {FEATURE} aufgebaut."
  "{N} Models, {M} Wissens-Dokumente, {K} Parking-Items uebernommen."
  "{R} RAG-Referenzen notiert (abrufbar via MCP query)."
  "Naechster Schritt: /_taskDefinition (Aufgabe definieren)"
```

---

## Ablauf: Easy (Auto-Scan + Auto-Accept)

```
         ┌──────────────────────┐
WELLE 3  │  1 ceiling-Agent     │  ──LIEST──▶ Vault + RAG (direkt)
ONLY     │  Auto-Scan           │  ──FILTERT──▶ Score >= 0.5 → ACCEPT
         │  Auto-Accept (W27)   │  ──SCHREIBT──▶ wissen/ + models/ + manifest
         └──────────────────────┘

Kein User-Input. Perfekt fuer prozessbegleitenden Einsatz als paralleler Worker.
```

---

## Ablauf: Normal

```
Welle 1:  ┌───┐ ┌───┐ ┌───┐
KARTOGR.  │ D │ │ D │ │ D │  ──LIEST──▶ Vault + RAG (je nach Fokus)
(Haiku)   └─┬─┘ └─┬─┘ └─┬─┘  ──SCHREIBT──▶ drafts/{NAME}-fetch-D*.md
            └─────┼─────┘
                  │
             [/compact moeglich]
                  │
                  ▼
Welle 2:  ┌──────────────────┐
FILTER    │  1 middle-Agent   │  ──LIEST──▶ drafts/{NAME}-fetch-D*.md
(Sonnet)  │  Deduplizieren    │  ──SCHREIBT──▶ drafts/{NAME}-fetch-filter.md
          └────────┬─────────┘
                   │
                   ▼
Welle 3:  ┌──────────────────┐
ENTSCHEID │  1 ceiling-Agent  │  ──LIEST──▶ drafts/{NAME}-fetch-filter.md
(Opus)    │  User bestaetigt  │  ──SCHREIBT──▶ wissen/ + models/ + manifest
          └──────────────────┘
```

---

## Ablauf: Hard

```
Welle 1:  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐
KARTOGR.  │D01│ │D02│ │D03│ │D04│ │D05│  ──LIEST──▶ Vault + RAG + Cross-Feature
(Haiku)   └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘  ──SCHREIBT──▶ drafts/{NAME}-fetch-D*.md
            └─────┼─────┼─────┼─────┘
                  │     │     │
             [/compact moeglich]
                  │     │     │
                  ▼     ▼     ▼
Welle 2:  ┌───┐ ┌───┐ ┌───┐
FILTER    │F01│ │F02│ │F03│  ──LIEST──▶ drafts/{NAME}-fetch-D*.md (ALLE)
(Sonnet)  └─┬─┘ └─┬─┘ └─┬─┘  ──SCHREIBT──▶ drafts/{NAME}-fetch-filter-F*.md
            └─────┼─────┘
                  ▼
Welle 3:  ┌──────────────────┐
ENTSCHEID │  1 ceiling-Agent  │  ──LIEST──▶ drafts/{NAME}-fetch-filter-F*.md
(Opus)    │  User bestaetigt  │  ──SCHREIBT──▶ wissen/ + models/ + manifest
          └──────────────────┘
```

---

## Abgrenzung

```
/_W_fetch      = Wissen HOLEN (Feature-Start, Vault + RAG → .claude/)
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
- Vault-Suche ist OPTIONAL (degraded mode ohne Vault)
- Tag-Index bleibt PRIMAERE Vault-Suchquelle (Welle 1 erweitert um semantische Nachbarn)
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
- Dual-Mode: Solo (sequentiell) und Worker (Orchestrator steuert) (R10)

---

## Fehlerbehandlung

| Fehler | Ursache | Loesung |
|--------|---------|---------|
| Vault nicht erreichbar | Pfad nicht konfiguriert oder nicht gemountet | NUR RAG-Suche (degraded mode) |
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
