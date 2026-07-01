# /_I_push_temp

```yaml
status: active
version: 1.0.0
created: 2026-02-27
updated: 2026-02-27
op: ImplementationPipeline
phase: Knowledge
type: building-block
chain_position: post-slice
team_based: false
```

---

```
+===============================================================+
|  COMMAND: /_I_push_temp {SLICE}                               |
+===============================================================+
|                                                               |
|  KERN-PROBLEM (W146+W147):                                    |
|    Wissen aus Slice N (Architektur-Entscheide, Block-Gruende, |
|    Pattern-Erkenntnisse, VERIFY-Findings) steht Slice N+1    |
|    NICHT zur Verfuegung. Cross-Slice-Lernen strukturell       |
|    unmoeglich ohne expliziten Push-Mechanismus.               |
|                                                               |
|  LOESUNG:                                                     |
|    Slice-Synthese-Dokumente nach verify_status=final in die   |
|    feature-lokale i_knowledge_ Collection pushen.             |
|    Naechste Slices koennen dann via MCP query() auf Slice-N   |
|    Wissen zugreifen.                                          |
|                                                               |
|  MODI:                                                        |
|    /_I_push_temp {SLICE}  → Einzelnen Slice pushen           |
|    /_I_push_temp auto     → Alle fertigen Slices pushen       |
|                                                               |
|  TRIGGER (WANN aufrufen):                                     |
|    → Nach /_I_verify (verify_status=final fuer diesen Slice)  |
|    → VOR /_I_fanIn (damit Wissen fuer uebergeordnete Phase)  |
|    → Team Lead ruft Command auf (kein Worker-Command)         |
|                                                               |
|  LIEST (Input) - PFLICHT:                                     |
|    1a. {VAULT}/_manifest.md  (global)                |
|       → NAME-Feld → feature_id → Collection-Name             |
|    1b. {WORKING_DIR}/_manifest.md  (per-Story BL-155 AK-1)   |
|       → I_PIPELINE_STATE.rag_collection (aus Schritt 1.1b)   |
|    2. {WORKTREE}/.claude/analysis/synthese/VERIFY-{SLICE}.md  |
|       → verify_status pruefen (muss "final" sein)             |
|    3. {WORKTREE}/.claude/analysis/synthese/ATOMIC-{SLICE}.md  |
|    4. {WORKTREE}/.claude/analysis/synthese/INTEGRATION-{SLICE}.md |
|                                                               |
|  SCHREIBT (Output) - PFLICHT:                                 |
|    1. RAG Collection: i_knowledge_{feature_id}                |
|       → Via MCP create_collection() + ingest()               |
|    2. {WORKING_DIR}/_manifest.md  (per-Story BL-155 AK-1)    |
|       → I_PIPELINE_STATE.worktrees.{SLICE}.push_status        |
|                                                               |
|  SCHREIBT NICHT:                                              |
|    - local_knowledge_ (das macht _W_push_temp)               |
|    - global_knowledge (das macht W_push_global)              |
|    - Slice-Dokumente selbst (nur LESEN fuer Ingest)          |
|                                                               |
|  PIPELINE-POSITION:                                           |
|    ... → /_I_verify → [/_I_push_temp] → /_I_fanIn → ...     |
|                                                               |
+===============================================================+
```

---

## Verantwortlichkeit

**KNOWLEDGE-PUSHER (I-Pipeline):** Pusht Slice-Wissen in die feature-lokale i_knowledge_ Collection.

**TUT:** Manifest lesen, verify_status pruefen, Collection sicherstellen,
Slice-Synthesen ingestieren, Manifest aktualisieren.

**NICHT:** Vault aendern, local_knowledge_ beschreiben, globale Collections schreiben,
Dokumente modifizieren.

---

## Schritt 0: Feature-ID + Collection ermitteln

```
1. Lies {VAULT}/_manifest.md  (global: NAME)
2. Extrahiere NAME-Feld (erste Zeile mit "**NAME:**")
   → Beispiel: **NAME:** DCSRE-881 → Feature-ID = "dcsre881"

2a. Lies {WORKING_DIR}/_manifest.md  (per-Story: I_PIPELINE_STATE — BL-155 AK-1)

3. Pruefe ob I_PIPELINE_STATE.rag_collection vorhanden:
   → JA: Collection-Name = I_PIPELINE_STATE.rag_collection
   → NEIN: Sanitize NAME → "i_knowledge_{feature_id}"
     Sanitize: lowercase, Sonderzeichen entfernen (nur a-z, 0-9, _ erlaubt)

4. Collection-Name = "i_knowledge_{feature_id}"

AUSGABE:
  "Feature: {NAME}"
  "Collection: i_knowledge_{feature_id}"
```

---

## Schritt 1: Slice validieren + Dokumente identifizieren

### Modus A: Einzelner Slice ({SLICE} angegeben)

```
1. SLICE-Parameter = Slice-Bezeichnung (z.B. "S1", "S2", "UserLogin")

2. verify_status pruefen (PFLICHT):
   → Lies {WORKTREE_PATH}/.claude/analysis/synthese/VERIFY-{SLICE}.md
   → ODER Lies aus Manifest: I_PIPELINE_STATE.worktrees.{SLICE}.verify_status
   → verify_status = "final"?
     → JA: WEITER
     → NEIN: FEHLER "Slice {SLICE} verify_status != final. Erst /_I_verify abschliessen."
              → ABBRUCH

3. Dokumente identifizieren (in Prioritaets-Reihenfolge):
   HOCH (immer pushen wenn vorhanden):
     → {WORKTREE}/.claude/analysis/synthese/VERIFY-{SLICE}.md      (Findings + Verif.)
     → {WORKTREE}/.claude/analysis/synthese/ATOMIC-{SLICE}.md      (Architektur-Entscheide)
   MITTEL (pushen wenn final):
     → {WORKTREE}/.claude/analysis/synthese/INTEGRATION-{SLICE}.md (Integration-Kontext)
   OPTIONAL:
     → {WORKTREE}/.claude/analysis/synthese/SYSTEM-{SLICE}.md      (System-Kontext)

4. Existenz-Check pro Datei:
   → Vorhanden + .md → Push-Kandidat
   → Nicht vorhanden → Ueberspringen (kein Fehler)

5. Falls 0 Push-Kandidaten:
   FEHLER: "Keine Synthese-Dokumente fuer Slice {SLICE} gefunden."
   HINWEIS: "Erwartete Pfade: {WORKTREE}/.claude/analysis/synthese/"
   → ABBRUCH

AUSGABE:
  "Slice: {SLICE} (verify_status=final)"
  "Push-Kandidaten: {N} Dokumente"
  "  HOCH: VERIFY-{SLICE}.md, ATOMIC-{SLICE}.md"
  "  MITTEL: INTEGRATION-{SLICE}.md"
```

### Modus B: Auto-Scan ("auto" angegeben)

```
Falls {SLICE} = "auto":

1. Lies I_PIPELINE_STATE.worktrees aus Manifest
2. Fuer jeden Slice:
   → verify_status = "final" UND push_status != "COMPLETED"?
   → JA: Slice in Push-Queue aufnehmen

3. Falls 0 Slices in Queue:
   INFO: "Keine neuen fertigen Slices zum Pushen."
   → ENDE

4. Pro Slice in Queue: Schritt 1-4 (Modus A) ausfuehren

AUSGABE:
  "Auto-Modus: {N} fertige Slices ohne Push gefunden"
  "Queue: {SLICE_1}, {SLICE_2}, ..."
```

---

## Schritt 2: Collection sicherstellen

```
MCP Aufruf (idempotent):
  → mcp__cleancodermcp__create_collection(name="i_knowledge_{feature_id}")
  → Return: {"status": "created"|"exists", "collection": str, "count": int}
  → "created" oder "exists" → BEIDE OK (kein Fehler)

AUSGABE:
  "Collection: i_knowledge_{feature_id} (Status: {STATUS}, Docs: {COUNT})"
```

---

## Schritt 3: Slice-Dokumente ingestieren

```
Fuer jedes Dokument in Push-Kandidaten-Liste (in Prioritaets-Reihenfolge):

1. Absoluten Pfad ermitteln

2. Metadaten vorbereiten (falls kein Frontmatter):
   → doc_type aus Dateiname:
     VERIFY-*    → "verify"
     ATOMIC-*    → "atomic-spec"
     INTEGRATION-* → "integration-spec"
     SYSTEM-*    → "system-spec"
   → citation_info = {
       "source_type": "{doc_type}",
       "slice": "{SLICE}",
       "feature": "{NAME}",
       "file_path": "{ABSOLUTER_PFAD}"
     }

3. MCP Aufruf:
   → ingest(
       file_path="{ABSOLUTER_PFAD}",
       collection="i_knowledge_{feature_id}",
       options={"citation_info": citation_info}  (falls kein Frontmatter)
     )
   → Return: {status, chunks_created, total_duration_seconds, error}

4. Ergebnis:
   → status="completed": Erfolgs-Liste aufnehmen
   → status="failed": Fehler-Liste aufnehmen, WEITER (kein Abbruch)

AUSGABE pro Dokument:
  "[OK] VERIFY-{SLICE}.md → {chunks} chunks in {duration}s"
  "[FAIL] ATOMIC-{SLICE}.md → {error}"
```

---

## Schritt 4: Manifest aktualisieren

```
In {WORKING_DIR}/_manifest.md  (per-Story BL-155 AK-1):

1. PUSH_STATUS fuer diesen Slice setzen:
   → I_PIPELINE_STATE.worktrees.{SLICE}.push_status = "COMPLETED ({DATUM})"

2. Globalen PUSH_STATUS aktualisieren (falls alle Slices gepusht):
   → Pruefe: Alle verify_status=final Slices haben push_status=COMPLETED?
   → JA: "PUSH_STATUS: COMPLETED ({DATUM}, i_knowledge_{feature_id}, alle Slices)"

3. Eintrag in RAG Push Tabelle:
   | {SLICE}/VERIFY-{SLICE}.md | {chunks} | {DATUM} | PUSHED |
   | {SLICE}/ATOMIC-{SLICE}.md | {chunks} | {DATUM} | PUSHED |
   usw.

AUSGABE:
  "Manifest aktualisiert: Slice {SLICE} push_status=COMPLETED"
```

---

## Schritt 5: Verifikation + Zusammenfassung

```
1. MCP query (Sanity-Check):
   → mcp__cleancodermcp__query(
       query_text="Slice {SLICE} Architektur-Entscheide",
       collection="i_knowledge_{feature_id}",
       limit=3
     )
   → Gibt es relevante Chunks? → JA: OK | NEIN: WARNUNG

2. AUSGABE:
   "=== I-Knowledge Push Abgeschlossen ==="
   ""
   "Collection: i_knowledge_{feature_id}"
   "Slice: {SLICE}"
   ""
   "Gepushte Dokumente:"
   "  [OK] VERIFY-{SLICE}.md → {chunks} chunks in {duration}s"
   "  [OK] ATOMIC-{SLICE}.md → {chunks} chunks in {duration}s"
   ""
   "Verifikation: {chunks_found} relevante Chunks in Collection"
   ""
   "Naechste Schritte:"
   "  → /_I_fanIn (Slice-Abschluss)"
   "  → Naechster Slice kann via query('i_knowledge_{feature_id}') Wissen aus {SLICE} finden"
```

---

## Abgrenzung

```
/_I_push_temp  = I-Pipeline Slice-Wissen (i_knowledge_ Collection)
                 Trigger: nach /_I_verify (Slice-DONE)
                 Scope: Slice-Synthesen (VERIFY, ATOMIC, INTEGRATION, SYSTEM)

/_W_push_temp  = Feature-weites Wissen (local_knowledge_ Collection)
                 Trigger: nach SC-Zyklen, ad-hoc
                 Scope: Models, OBSERVE, ERGEBNIS, HYPOTHESEN

/_W_push_global= Globales Wissen (global_knowledge Collection)
                 Trigger: Feature-Ende
                 Scope: Wissen mit dauerhafter Relevanz fuer andere Features

i_knowledge_{feature_id}   → Cross-Slice-Lernen INNERHALB Feature
local_knowledge_{feature_id} → Feature-weites Wissen (SC-Cycle, Specs)
global_knowledge             → Permanentes Wissen fuer alle Features
```

---

## Fehlerbehandlung

| Fehler | Ursache | Loesung |
|--------|---------|---------|
| verify_status != final | /_I_verify nicht abgeschlossen | /_I_verify fuer diesen Slice ausfuehren |
| Keine Synthese-Dokumente | Slice-Dateien nicht im erwarteten Pfad | Pruefen ob WORKTREE_PATH korrekt |
| mcp__cleancodermcp__create_collection fehlt | MCP nicht erreichbar | Graceful Degradation: WARNUNG, kein Abbruch |
| ingest fehlschlaegt | Datei zu gross, Format | WARNUNG pro Datei, weiter mit naechster |

---

## Rollback-Anleitung

**Wann relevant:** Wenn `ingest()` fuer ein oder mehrere Dokumente fehlschlaegt (Schritt 3 FAIL-Eintrag).

### Schritt A: push_status NICHT auf COMPLETED setzen

`push_status = "COMPLETED"` wird in Schritt 4 NUR bei erfolgreichem Ingest gesetzt.
Falls `ingest()` fehlschlug → push_status bleibt leer oder auf vorherigem Wert.
**Explizit:** Manifest NICHT aktualisieren solange FAIL-Eintraege fuer diesen Slice existieren.
Auto-Modus (Modus B) ueberspringt Slices mit push_status != COMPLETED automatisch beim naechsten Aufruf.

### Schritt B: Recovery-Optionen nach teilweisem oder vollstaendigem Ingest-Fehler

**Option 1 — Erneuter Aufruf (empfohlen):**
`/_I_push_temp {SLICE}` erneut aufrufen ist idempotent:
- `mcp__cleancodermcp__create_collection()` gibt "exists" zurueck (kein Fehler, keine Duplikate)
- `ingest()` ueberschreibt bestehende Chunks fuer dieselbe Datei (kein Duplikat-Risiko)
- Fehlgeschlagene Dokumente werden erneut versucht, bereits gepushte bleiben erhalten

**Option 2 — Manuelle Bereinigung (bei Bedarf):**
Falls eine Collection vollstaendig geleert werden muss (z.B. nach Korruption):
- MCP `delete_from_collection(collection="i_knowledge_{feature_id}", ...)` aufrufen (falls verfuegbar)
- Danach `/_I_push_temp {SLICE}` erneut ausfuehren (frische Ingestierung)

**Option 3 — Graceful Degradation (bei MCP-Ausfall):**
Falls MCP dauerhaft nicht erreichbar: push_status leer lassen, WARN im Manifest eintragen,
mit `/_I_fanIn` fortfahren — Slice-Wissen fehlt im RAG, aber Pipeline ist nicht blockiert.

---

## Qualitaetskriterien

- verify_status=final PFLICHT vor Push (Schlecht-Qualitaets-Schutz)
- Collection-Name: i_knowledge_{feature_id} (GETRENNT von local_knowledge_)
- mcp__cleancodermcp__create_collection() IMMER aufrufen (idempotent, kein Fehler bei Wiederholung)
- Absoluter Pfad an ingest() (MCP Server Requirement)
- Manifest-Update NUR bei erfolgreichem Ingest
- Sanity-Check via mcp__cleancodermcp__query() nach Push
- Quell-Dokumente werden NIE modifiziert

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist:**

```bash
powershell -Command "notify '{SLICE} /_I_push_temp abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
