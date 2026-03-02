# /_W_push_temp

**Status:** v2.1 (+ Schritt 1b: Metadaten-Injection via options.citation_info)
**Actor:** KNOWLEDGE-PUSHER
**Zweck:** Wissens-Dokumente aus .claude/ in die feature-lokale RAG Collection pushen
**Basis:** WissensPipeline-OBSERVE2.md (F1-F8 verifiziert)

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_W_push_temp {DOCUMENT|auto}                        |
+===============================================================+
|                                                                |
|  KERN-PROBLEM:                                                 |
|    Waehrend eines Features entstehen Findings, Models und      |
|    Wissen in .claude/ -- aber sie liegen nur lokal.             |
|    Kein anderes Feature und kein W_fetch kann sie finden.       |
|    Wertvolles Zwischen-Wissen geht verloren.                   |
|                                                                |
|  KERN-PRINZIP:                                                 |
|    Strategische Dokumente in die feature-lokale RAG Collection  |
|    pushen. Nicht alles -- nur was Wissens-Charakter hat.        |
|    "Make knowledge findable."                                   |
|                                                                |
|  MODI:                                                         |
|    /_W_push_temp {PFAD}  → Einzelnes Dokument pushen           |
|    /_W_push_temp auto    → Alle Push-Kandidaten finden + pushen|
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. .claude/analysis/_manifest.md                            |
|       → NAME-Feld → Feature-ID fuer Collection-Name           |
|    2. {DOCUMENT} ODER auto-Scan der erlaubten Ordner           |
|       → Validierung: Existiert? .md? Erlaubter Ordner?         |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. RAG Collection: local_knowledge_{feature_id}             |
|       → Via MCP create_collection() + ingest()                 |
|    2. .claude/analysis/_manifest.md                            |
|       → "## RAG Push Status" Sektion aktualisieren             |
|                                                                |
|  SCHREIBT NICHT:                                               |
|    - Vault-Dateien (das macht _W_obsidianSync)                   |
|    - Das Dokument selbst (nur LESEN fuer Ingest)               |
|    - global_knowledge (das macht W_push_global)                |
|    - Andere Collections                                        |
|                                                                |
|  PIPELINE:                                                     |
|    [/_W_fetch] → Feature-Arbeit → [/_W_push_temp] → ...       |
|    (Waehrend Feature, an strategischen Punkten)                |
|                                                                |
|  STRATEGISCHE PUSH-PUNKTE:                                     |
|    - Nach /_SC_observe (konsolidierte Findings)                |
|    - Nach /_SC_ergebnis (verifizierte Ergebnisse)              |
|    - Nach /_model finish (finales Model)                       |
|    - Nach /_knowledge (neues Wissens-Dokument)                 |
|    - "auto": Alles auf einmal (z.B. vor Feature-Abschluss)    |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**KNOWLEDGE-PUSHER:** Pusht Wissens-Dokumente in die feature-lokale RAG Collection.

**TUT:** Manifest lesen, Dokument validieren, Collection erstellen,
Dokument ingestieren, Manifest aktualisieren, Bestaetigung ausgeben.

**NICHT:** Wissen erstellen, Vault aendern, global_knowledge beschreiben,
Dokumente modifizieren, Quality Gate pruefen (das macht W_push_global).

---

## Schritt 0: Feature-ID ermitteln

```
1. Lies .claude/analysis/_manifest.md
2. Extrahiere NAME-Feld (erste Zeile mit "**NAME:**")
   → Beispiel: **NAME:** TwoTierBridge → Feature-ID = "twotierbridge"

3. Sanitize Feature-ID:
   → Lowercase
   → Leerzeichen → Underscore
   → Sonderzeichen entfernen (nur a-z, 0-9, _ erlaubt)
   → Beispiel: "Two Tier-Bridge" → "two_tierbridge"

4. Collection-Name bilden:
   → "local_knowledge_{feature_id}"
   → Beispiel: "local_knowledge_twotierbridge"

AUSGABE:
  "Feature: {NAME}"
  "Collection: local_knowledge_{feature_id}"
```

---

## Schritt 1: Dokument(e) identifizieren + validieren

### Modus A: Einzelnes Dokument ({DOCUMENT} angegeben)

```
Falls {DOCUMENT} angegeben:

  1. Pfad validieren:
     → Relativer Pfad zu .claude/? → Absolut machen
     → Absoluter Pfad? → Pruefen ob in .claude/
     → Beispiel: "models/Model.md" → ".claude/models/Model.md"

  2. Datei-Checks:
     a) Existiert die Datei?
        → NEIN: FEHLER "Dokument nicht gefunden: {DOCUMENT}"
        → ABBRUCH

     b) Dateiendung = .md?
        → NEIN: FEHLER "Nur .md Dateien unterstuetzt. Erhalten: {EXT}"
        → ABBRUCH

     c) Ordner erlaubt?
        ERLAUBT (Wissens-Charakter, F4):
          → .claude/models/          (technische Models mit W{n})
          → .claude/wissen/           (erklaerende Wissens-Dokumente)
          → .claude/specs/            (Spezifikationen)
          → .claude/analysis/synthese/ (OBSERVE, ERGEBNIS, HYPOTHESEN, GAP, QUALITYGATE)

        NICHT ERLAUBT (temporaer/roh):
          → .claude/crumbs/           (Rohdaten, unsortiert)
          → .claude/analysis/drafts/  (Zwischen-Entwuerfe)
          → .claude/temp/             (temporaere Dateien)
          → .claude/commands/         (Code, kein Wissen)

        → NICHT ERLAUBT: FEHLER "Ordner {ORDNER} ist nicht fuer RAG-Push vorgesehen.
                                 Erlaubt: models/, wissen/, specs/, analysis/synthese/"
        → ABBRUCH

     d) Bereits gepusht? (Optional)
        → Pruefe Manifest "## RAG Push Status" Sektion
        → Falls DOCUMENT bereits gelistet:
          WARNUNG: "Dokument bereits gepusht am {DATUM} ({CHUNKS} chunks).
                    Erneuter Push OHNE --force ueberspringt Duplikate."
        → Standardverhalten: SKIP (kein Duplikat)

  3. Push-Kandidaten-Liste = [DOCUMENT]

AUSGABE:
  "Dokument validiert: {DOCUMENT} ({ZEILEN} Zeilen, Ordner: {ORDNER})"
```

### Modus B: Auto-Scan ("auto" angegeben)

```
Falls {DOCUMENT} = "auto":

  1. Erlaubte Ordner scannen (F4):
     → Glob(.claude/models/*_Model.md)
     → Glob(.claude/wissen/*_Wissen.md)
     → Glob(.claude/analysis/synthese/*-OBSERVE*.md)
     → Glob(.claude/analysis/synthese/*-ERGEBNIS*.md)
     → Glob(.claude/analysis/synthese/*-GAP*.md)
     → Glob(.claude/analysis/synthese/*-QUALITYGATE*.md)
     → Glob(.claude/analysis/synthese/*-HYPOTHESEN*.md)
     → Glob(.claude/specs/*_Spec.md)

  2. Manifest-Check (bereits gepusht?):
     → Falls "## RAG Push Status" Sektion existiert:
       - Lese Tabelle, extrahiere "Dokument" + "Datum" Spalten
       - Filtere Kandidaten: nur neue/geaenderte Dateien
       - Aenderung = Datei-Modifikations-Datum > Manifest-Push-Datum

  3. Push-Kandidaten-Liste erstellen:
     → Sortiere: models → specs → wissen → synthese (OBSERVE/ERGEBNIS/GAP/QUALITYGATE/HYPOTHESEN)
     → AUSGABE: "{N} Push-Kandidaten gefunden"
     → Liste anzeigen (max 10 Zeilen, dann "... und {M} weitere")

  4. Falls N = 0:
     INFO: "Keine neuen Dokumente zum Pushen. Alle bereits in Collection."
     → ENDE (kein Error)

  5. Falls N > 10:
     FRAGE: "{N} Dokumente gefunden. Alle pushen? (j/n)"
     → User entscheidet

AUSGABE:
  "Auto-Modus: {N} Kandidaten validiert"
```

---

## Schritt 1b: Metadaten vorbereiten (falls kein Frontmatter)

```
Fuer jedes Dokument in Push-Kandidaten-Liste:

  1. Pruefen: Hat das Dokument YAML Frontmatter?
     → Erste Zeile == "---" UND zweites "---" vorhanden?
     → JA: Frontmatter vorhanden → SKIP (Pipeline nutzt Frontmatter automatisch)
     → NEIN: Metadaten manuell vorbereiten (fuer options.citation_info)

  2. doc_type ableiten (aus Ordner + Dateiname-Pattern):
     → .claude/models/*_Model.md          → doc_type = "model"
     → .claude/wissen/*_Wissen.md          → doc_type = "knowledge"
     → .claude/specs/*_Spec.md             → doc_type = "spec"
     → .claude/analysis/synthese/*-OBSERVE* → doc_type = "observe"
     → .claude/analysis/synthese/*-ERGEBNIS* → doc_type = "ergebnis"
     → .claude/analysis/synthese/*-HYPOTHESEN* → doc_type = "hypothese"
     → .claude/analysis/synthese/*-GAP*    → doc_type = "gap-analyse"
     → .claude/analysis/synthese/*-QUALITYGATE* → doc_type = "qualitygate"
     → Kein Match                          → doc_type = "document"

  3. Metadaten-Dict fuer options bauen:
     → citation_info = {
         "bibtex_key": None,
         "source_type": "{doc_type}",
         "file_path": "{ABSOLUTER_PFAD}"
       }

     HINWEIS: citation_info wird vom Orchestrator (D1-Fix) in document_metadata
     gemerged. Dadurch erhalten alle Chunks die Felder:
       - source_type (= doc_type)
       - source_file (= Dateiname)

  4. Ergebnis pro Dokument:
     → HAS_FRONTMATTER=true:  options = None (Standard-Pipeline)
     → HAS_FRONTMATTER=false: options = {"citation_info": citation_info}

AUSGABE:
  "{N} Dokumente mit Frontmatter, {M} ohne (Metadaten via options injiziert)"

WICHTIG: Das Quell-Dokument wird NICHT modifiziert.
         Metadaten fliessen ueber den options-Parameter in die Pipeline.
         Dies nutzt den D1-Fix (orchestrator.py: citation_info → document_metadata).
```

---

## Schritt 2: Collection sicherstellen

```
MCP Aufruf (F1, F2 - idempotent):
  → create_collection(name="local_knowledge_{feature_id}")
  → Signature (OBSERVE2 F2):
      - Return: {"status": "created"|"exists", "collection": str, "count": int}
      - Idempotent: Kein Fehler falls Collection bereits existiert (get_or_create)

Ergebnis:
  → status = "created": "Collection erstellt: local_knowledge_{feature_id}"
  → status = "exists":  "Collection existiert bereits ({COUNT} Dokumente)"

AUSGABE:
  "Collection: local_knowledge_{feature_id} (Status: {STATUS}, Docs: {COUNT})"
```

---

## Schritt 3: Dokument(e) ingestieren

```
Fuer jedes Dokument in Push-Kandidaten-Liste:

  1. Absoluten Pfad ermitteln:
     → Falls relativ zu .claude/: Absolut machen
     → Beispiel: "models/Model.md" → "/abs/path/.claude/models/Model.md"

  2. Options aus Schritt 1b holen:
     → HAS_FRONTMATTER=true:  doc_options = None
     → HAS_FRONTMATTER=false: doc_options = {"citation_info": {...}} (aus Schritt 1b)

  3. MCP Aufruf (F1, F6 - .md Dateien direkt):
     → ingest(
         file_path="{ABSOLUTER_PFAD}",
         collection="local_knowledge_{feature_id}",
         options=doc_options
       )
     → Signature (OBSERVE2 F1):
         - Input: file_path (str), collection (str|None), options (dict|None)
         - Return: {
             "status": "completed"|"failed",
             "document_id": str,
             "file_path": str,
             "collection": str,
             "stages_completed": list[str],
             "chunks_created": int,
             "total_duration_seconds": float,
             "error": str|None
           }
         - Pipeline: read → validate → chunk → embed → keywords → store
         - Metadaten-Fluss: options.citation_info → orchestrator → document_metadata → chunks

  4. Ergebnis auswerten:
     a) status = "completed":
        → Erfolgs-Liste: [(DOKUMENT, chunks_created, document_id, duration)]
        → AUSGABE: "[OK] {DOKUMENT} → {chunks_created} chunks in {duration}s"

     b) status = "failed":
        → Fehler-Liste: [(DOKUMENT, error)]
        → AUSGABE: "[FAIL] {DOKUMENT} → {error}"
        → Fortfahren mit naechstem Dokument (kein ABBRUCH)

  5. Gesamtstatistik sammeln:
     → Erfolgreich: S Dokumente, C Chunks
     → Fehlgeschlagen: F Dokumente

METADATEN-STRATEGIE (F5 + D1-Fix):
  - Dokumente MIT Frontmatter: Pipeline extrahiert automatisch doc_type, topics, feature etc.
  - Dokumente OHNE Frontmatter: Schritt 1b injiziert source_type via options.citation_info
  - In beiden Faellen: source_file + ingest_timestamp werden IMMER gesetzt
  - Quell-Dokument wird NIE modifiziert.
```

---

## Schritt 4: Manifest aktualisieren

```
In .claude/analysis/_manifest.md (F8 - neue Sektion):

  1. Suche Sektion "## RAG Push Status"
     → Falls nicht vorhanden: Sektion NEU erstellen (APPEND am Ende, vor letztem "---")

  2. Sektion-Template (falls neu):
     ```
     ## RAG Push Status

     **Collection:** local_knowledge_{feature_id}
     **Letzter Push:** {DATUM}

     | Dokument | Chunks | Datum | Status |
     |----------|--------|-------|--------|
     ```

  3. Zeile pro gepushtem Dokument hinzufuegen/updaten:
     a) Erfolgreich gepusht (status = "completed"):
        → Format: "| {DOKUMENT_NAME} | {chunks_created} | {DATUM} | PUSHED |"
        → DOKUMENT_NAME: Relativ zu .claude/ (z.B. "models/Model.md")
        → DATUM: YYYY-MM-DD (heute)
        → Status: "PUSHED"

     b) Fehlgeschlagen (status = "failed"):
        → Format: "| {DOKUMENT_NAME} | 0 | {DATUM} | FAILED |"
        → Status: "FAILED"

  4. Beispiel-Tabelle (OBSERVE2 F8):
     ```
     | Dokument | Chunks | Datum | Status |
     |----------|--------|-------|--------|
     | models/WissensPipeline_Model.md | 12 | 2026-02-14 | PUSHED |
     | wissen/TwoTierBridge_Wissen.md | 8 | 2026-02-14 | PUSHED |
     | analysis/synthese/WissensPipeline-OBSERVE1.md | 15 | 2026-02-14 | PUSHED |
     | specs/WissensPipeline_Spec.md | 10 | 2026-02-14 | PUSHED |
     ```

  5. PUSH_STATUS-Feld schreiben (Pflicht — wird von /_finish Schritt 0 Guard gelesen):
     → Nach der RAG Push Status Tabelle, in derselben Sektion:
       "**PUSH_STATUS:** COMPLETED ({DATUM}, {collection_name}, {S}/{N} Slices/auto)"
     → Format: exakt "PUSH_STATUS: COMPLETED" als Prefix (Guard prueft Prefix, kein Substring)
     → NUR schreiben wenn mindestens 1 Dokument erfolgreich gepusht wurde (S > 0)
     → Bei S = 0: PUSH_STATUS NICHT auf COMPLETED setzen (kein Push, kein Status)

  6. Manifest schreiben:
     → Edit-Tool verwenden fuer bestehende Sektion
     → NUR erfolgreiche Pushes ins Manifest (failed = Skip)

AUSGABE:
  "Manifest aktualisiert: {S} Dokumente eingetragen (+ {F} fehlgeschlagen)"
```

---

## Schritt 5: Verifikation + Zusammenfassung

```
1. MCP list_collections aufrufen:
   → Pruefe ob "local_knowledge_{feature_id}" in Liste
   → Hole count (Anzahl Dokumente in Collection)

2. AUSGABE:
   "=== RAG Push Abgeschlossen ==="
   ""
   "Collection: local_knowledge_{feature_id}"
   "Dokumente gesamt: {COUNT}"
   ""
   "Neue Pushes:"
   "  Erfolgreich: {S} Dokumente, {C} Chunks"
   "  Fehlgeschlagen: {F} Dokumente"
   ""
   Falls S > 0:
     Pro erfolgreichem Dokument:
       "  [OK] {DOKUMENT} → {chunks} chunks in {duration}s"
   ""
   Falls F > 0:
     Pro fehlgeschlagenem Dokument:
       "  [FAIL] {DOKUMENT} → {error}"
   ""
   "Manifest aktualisiert: .claude/analysis/_manifest.md → ## RAG Push Status"
   ""
   "Naechste Schritte (F7):"
   "  → /_W_fetch kann jetzt lokales Wissen finden"
   "  → MCP query(collection='local_knowledge_{feature_id}', query_text=...)"
   "  → /_W_push_temp auto (weitere Dokumente pushen)"
   "  → /_W_push_global (Feature-Ende, global pushen)"
```

---

## Abgrenzung

```
/_W_push_temp  = Feature-LOKALES Pushen (waehrend Feature, temporaer)
/_W_push_global= GLOBALES Pushen (Feature-Ende, permanentes Wissen)
/_W_fetch      = Wissen HOLEN (Vault + RAG → .claude/, F7)
/_W_obsidianSync = Synthese TRANSPORTIEREN (.claude/ → Vault)
/_W_modelSplit = Wissen EXTRAHIEREN (Model → thematische Teile)

          /_W_fetch (Feature-Start)
                ↓
          Feature-Arbeit (Cycle 1)
                ↓
          /_W_push_temp (Models, OBSERVE1)
                ↓
          Feature-Arbeit (Cycle 2)
                ↓
          /_W_fetch (kann jetzt lokales Wissen finden! F7)
                ↓
          /_W_push_temp auto (neue OBSERVE, ERGEBNIS)
                ↓
          Feature-Ende
                ↓
          /_W_push_global + /_W_obsidianSync

W_push_temp ist EINFACH und SCHNELL:
  → Kein Quality Gate (das macht W_push_global)
  → Keine Vault-Interaktion (das macht _W_obsidianSync)
  → Frontmatter optional: mit FM → automatisch, ohne FM → Metadaten via options
  → Quell-Dokument wird NIE modifiziert (Metadaten via options.citation_info)
  → 3 MCP Calls pro Dokument: create_collection + ingest + list_collections
  → Idempotent: create_collection kann mehrfach aufgerufen werden (F2)

W_push_temp ist FEATURE-ISOLIERT:
  → Collection: local_knowledge_{feature_id} (nur dieses Feature)
  → Andere Features sehen diese Daten NICHT (ausser via uebergreifend-Scope)
  → W_fetch sucht automatisch in der eigenen Feature-Collection (F7)
```

---

## Fehlerbehandlung

| Fehler | Ursache | Loesung |
|--------|---------|---------|
| Manifest nicht gefunden | .claude/analysis/_manifest.md fehlt | FEHLER + Hinweis: "Starte mit /_taskDefinition" |
| NAME nicht im Manifest | Manifest hat kein NAME-Feld | FRAGE User nach Feature-Name |
| Dokument nicht gefunden | Pfad falsch oder Datei geloescht | FEHLER mit korrektem Pfad-Hinweis |
| Nicht-erlaubter Ordner | Dokument in crumbs/drafts/temp | FEHLER mit Liste erlaubter Ordner |
| create_collection fehlschlaegt | ChromaDB nicht erreichbar | FEHLER: "MCP Server nicht erreichbar" |
| ingest fehlschlaegt | Datei zu gross, Format-Fehler, etc. | FEHLER mit ingest-Fehlermeldung |
| Duplikat-Warnung | Dokument bereits gepusht | WARNUNG, User entscheidet |

---

## Qualitaetskriterien

- Feature-ID aus Manifest NAME-Feld (F3: NICHT raten, NICHT hardcoden)
- Collection-Name: local_knowledge_{feature_id} (lowercase, sanitized)
- create_collection() IMMER aufrufen (F2: idempotent, kein Fehler)
- ingest() direkt mit collection-Parameter (F1: ein Call pro Dokument)
- Nur .md Dateien aus erlaubten Ordnern (F4, F6)
- Absoluter Pfad an ingest() uebergeben (MCP Server Requirement)
- Frontmatter optional: Schritt 1b injiziert Metadaten via options wenn kein FM vorhanden
- Quell-Dokument wird NIE modifiziert (Metadaten via options.citation_info, D1-Fix)
- Manifest NUR bei erfolgreichem Ingest aktualisieren (F8)
- Duplikat-Schutz: auto-Modus skippt bereits gepushte Dokumente
- Verifikation via list_collections (Sanity-Check)
- W_fetch findet gepushte Daten automatisch (F7: Cross-Validation)

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Bestaetigung ausgegeben):

```bash
# Linux:
echo "/_W_push_temp {DOCUMENT} abgeschlossen"

# Windows:
powershell -Command "notify '{DOCUMENT} /_W_push_temp abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
