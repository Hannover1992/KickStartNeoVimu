# /_transkriptRaffinieren

**Status:** v1.0
**Actor:** RAFFINERIE-OPERATOR
**Zweck:** Rohes Meeting-Transkript in strukturiertes, scanbares Obsidian-Markdown transformieren

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_transkriptRaffinieren {FILE} [--output] [--date]   |
+===============================================================+
|                                                                |
|  KERN-PROBLEM:                                                 |
|    Meeting-Transkripte sind dicht, unstrukturiert, stundenlang.|
|    Keine Speaker-Tags, Action Items in Nebensaetzen vergraben, |
|    Entscheidungen in letzten 5 Minuten — niemand hat notiert.  |
|    Wissen geht verloren oder ist unzugaenglich.                |
|                                                                |
|  KERN-PRINZIP:                                                 |
|    "Weizen vom Stroh trennen."                                 |
|    Dump Transkript → strukturiertes, scanbares Ergebnis.       |
|    Key Decisions oben, Open Questions markiert, Action Items   |
|    mit Owners und Deadlines extrahiert.                        |
|    Output = Obsidian Markdown → direkt in Vault nutzbar.       |
|                                                                |
|  TIER: 0 (Input-Transformation, VOR W-Commands)               |
|    TranskriptRaffinerie ERZEUGT Wissen.                        |
|    W-Commands BEWEGEN Wissen.                                  |
|    Kein W-Command-Aufruf aus Tier 0.                           |
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. {FILE} (.txt Transkript-Datei)                           |
|       → Rohes Meeting-Transkript, beliebig lang                |
|                                                                |
|  LIEST (Input) - OPTIONAL:                                     |
|    2. .claude/analysis/_manifest.md                             |
|       → Vault-Pfad fuer Output-Location                        |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. {VAULT}/Meetings/Meeting_{DATE}_{THEMA}.md               |
|       → Strukturiertes Meeting-Ergebnis (Obsidian Markdown)    |
|       → Fallback: .claude/output/ falls Vault nicht erreichbar |
|    2. Quality-Report (am Ende der Output-Datei)                |
|       → Textreduktion, Extraction-Stats, Confidence-Scores     |
|                                                                |
|  SCHREIBT NICHT:                                               |
|    - RAG Collections (User ruft W_push_temp separat auf)       |
|    - Andere .claude/ Dateien                                   |
|    - Manifest (kein SC-Zyklus-Command)                         |
|                                                                |
|  PARAMETER:                                                    |
|    {FILE}    (Pflicht)  Path zu .txt Transkript                |
|    --output  (Optional) Vault-Pfad, Default: {VAULT}/Meetings/ |
|    --date    (Optional) Meeting-Datum, Default: heute           |
|                                                                |
|  SCHWIERIGKEIT:                                                |
|    Skaliert NICHT mit Difficulty. Immer gleicher Ablauf.        |
|    Laenge des Transkripts bestimmt Aufwand (Chunks).           |
+===============================================================+
```

---

## Ablauf

### Schritt 0: Input validieren

```
1. Pruefe: Existiert {FILE}?
   → NEIN: ABBRUCH mit "Datei nicht gefunden: {FILE}"

2. Pruefe: Ist {FILE} eine .txt Datei?
   → NEIN: WARNUNG "Erwarte .txt, versuche trotzdem..."

3. Lies {FILE} vollstaendig
   → Merke: Wort-Anzahl, Zeilen-Anzahl

4. Bestimme Output-Pfad:
   → --output Flag gesetzt? → Nutze den
   → Manifest hat Vault-Pfad? → {VAULT}/Meetings/
   → Fallback: .claude/output/

5. Bestimme Datum:
   → --date Flag gesetzt? → Nutze den
   → Default: heutiges Datum (YYYY-MM-DD)
```

### Schritt 1: Chunking (bei langen Transkripten)

```
WENN Transkript > 6000 Woerter (~8000 tokens):
   → Nutze MCP-Tool chunk_document:
     mcp__cleancodermcp__chunk_document(
       text = {TRANSKRIPT_TEXT},
       strategy = "hybrid",
       params = {
         "target_size": 8000,
         "overlap_percent": 0.125
       }
     )
   → Ergebnis: Array von Chunks mit Overlap
   → Verarbeite jeden Chunk einzeln in Schritt 2

WENN Transkript <= 6000 Woerter:
   → Kein Chunking noetig, ganzer Text ist 1 "Chunk"
```

### Schritt 2: Multi-Pass Extraktion (pro Chunk)

Fuehre fuer JEDEN Chunk 3 separate Extraktions-Durchgaenge durch.
Du BIST das LLM — fuehre die Extraktion direkt aus, kein API-Call noetig.

**Pass 1: Key Decisions extrahieren**
```
Analysiere den Chunk-Text und extrahiere NUR finale Entscheidungen:
- Eine Decision = etwas das ENTSCHIEDEN wurde (nicht "wir sollten")
- Ignoriere Diskussionen, Meinungen, Vorschlaege
- Pro Decision: Text, Kontext (warum), Confidence (0.0-1.0)
- Ohne Speaker-Tags: Fokus auf INHALT, nicht Person

Merke alle Decisions in einer strukturierten Liste.
```

**Pass 2: Action Items extrahieren**
```
Analysiere den Chunk-Text und extrahiere NUR Action Items:
- Ein Action Item = etwas das GETAN werden muss
- Owner: falls erkennbar (Person/Rolle), sonst "TBD"
- Deadline: falls erkennbar, sonst "TBD"
- Pro Action: Text, Owner, Deadline, Confidence (0.0-1.0)

Merke alle Actions in einer strukturierten Liste.
```

**Pass 3: Open Questions extrahieren**
```
Analysiere den Chunk-Text und extrahiere NUR offene Fragen:
- Eine Question = unbeantwortete, projektrelevante Frage
- Ignoriere rhetorische Fragen
- Pro Question: Frage-Text, Kontext, Confidence (0.0-1.0)

Merke alle Questions in einer strukturierten Liste.
```

**Nach allen Chunks: Deduplizierung**
```
Wenn mehrere Chunks: Merge die Ergebnisse.
- Identische/sehr aehnliche Items zusammenfassen
- Confidence-Scores mitteln bei Duplikaten
- Chunk-Grenz-Items erkennen (gleicher Inhalt, zwei Chunks)
```

### Schritt 3: Themen-Clustering

```
WENN mehr als 5 extrahierte Items UND MCP verfuegbar:
   1. Nutze MCP extract_keywords fuer jedes Item:
      mcp__cleancodermcp__extract_keywords(text = {item_context}, count = 3)

   2. Gruppiere Items nach gemeinsamen Keywords
      → 3-7 Themen-Cluster (nicht mehr, nicht weniger)
      → Label jedes Cluster mit dem dominanten Keyword

   3. Ordne ALLE Items einem Cluster zu

WENN weniger als 5 Items ODER MCP nicht verfuegbar:
   → Ueberspringe Clustering
   → Schreibe Items in flacher Liste (kein Themen-Abschnitt)
```

### Schritt 4: Output formatieren

Erstelle die Obsidian-Markdown-Datei nach diesem Template:

```markdown
---
id: Meeting_{DATE}_{THEMA}
aliases:
  - {Erkannte Aliases/Projektnamen}
tags:
  - type/meeting
  - topic/{Cluster-Labels}
date: {DATE}
participants: {Falls erkennbar, sonst TBD}
duration: {Falls erkennbar, sonst TBD}
confidence:
  decisions: {Durchschnitts-Score}
  actions: {Durchschnitts-Score}
  questions: {Durchschnitts-Score}
extraction:
  chunks: {Anzahl}
  input_words: {Woerter im Original}
  output_words: {Woerter im Output}
  timestamp: {Jetzt ISO-8601}
---

# Meeting: {THEMA} ({DATE})

**Duration:** {Falls erkennbar}
**Participants:** {Falls erkennbar oder TBD}

---

## Key Decisions

1. **{Decision-Text}**
   - **Context:** {Warum wurde das entschieden?}
   - *Confidence: {Score}*

2. ...

---

## Action Items

- [ ] **{Action-Text}**
  - **Owner:** {Person oder TBD}
  - **Deadline:** {Datum oder TBD}
  - *Confidence: {Score}*

- [ ] ...

---

## Open Questions

- **Q:** {Frage}
  - **Context:** {Wer hat gefragt / warum relevant?}
  - *Confidence: {Score}*

- ...

---

## Themen-Gliederung

### Thread 1: {Thema-Label}
- {Kurze Zusammenfassung dieses Gespraechsfadens}
- **Related:** Decision #1, Action #3

### Thread 2: {Thema-Label}
- ...

---

## Extraction Quality Report

**Input:** {N} Woerter ({Seiten} Seiten)
**Output:** {N} Woerter ({Seiten} Seiten)
**Reduction:** {Prozent}%

**Extracted:** {N} Decisions, {N} Actions, {N} Questions
**Avg Confidence:** {Score} (Decisions), {Score} (Actions), {Score} (Questions)
**Read Time:** {Minuten} min

**Chunks:** {N} (Target: 8K tokens, Overlap: 12.5%)
**Themen:** {N} Cluster

**Status:** {PASS | PASS WITH WARNING | FAIL}
{Warnings falls vorhanden}
```

### Schritt 5: Quality Gates

```
Gate 1 (Technisch - BLOCKING):
  - YAML-Frontmatter ist gueltig?
  - Alle Pflicht-Sektionen vorhanden (Decisions, Actions, Questions)?
  → FAIL: Korrigiere und wiederhole Schritt 4

Gate 2 (Content - WARNING):
  - Mindestens 1 Decision ODER 1 Action ODER 1 Question extrahiert?
  → FAIL: WARNUNG "Keine Items extrahiert — Transkript evtl. kein Meeting?"

  - Textreduktion > 50%?
  → FAIL: WARNUNG "Geringe Textreduktion — Output evtl. zu ausfuehrlich"

  - Read-Time < 5 Minuten? (Output-Woerter / 200)
  → FAIL: WARNUNG "Output evtl. zu lang zum Scannen"
```

### Schritt 6: Datei schreiben

```
1. Schreibe Output-Datei an bestimmten Pfad
   → {OUTPUT_PATH}/Meeting_{DATE}_{THEMA}.md

2. Bestimme THEMA aus:
   → Haeufigstes Cluster-Label
   → ODER erstes erkanntes Projektwort
   → ODER "Transkript" als Fallback

3. Melde dem User:
   "Meeting raffiniert:
    - Output: {PFAD}
    - {N} Decisions, {N} Actions, {N} Questions
    - Textreduktion: {X}%
    - Read-Time: {Y} min
    - Status: {PASS/WARNING}"

4. HINWEIS an User:
   "Fuer RAG-Ingest: /_W_push_temp --files {OUTPUT_PFAD}"
```

---

## Error-Handling

```
┌──────────────────────────┬──────────────┬──────────────────────────┐
│ Fehler                   │ Typ          │ Reaktion                 │
├──────────────────────────┼──────────────┼──────────────────────────┤
│ Datei nicht gefunden     │ BLOCKING     │ ABBRUCH mit Meldung      │
│ Datei leer               │ BLOCKING     │ ABBRUCH "Leere Datei"    │
│ MCP chunk_document fail  │ NON-BLOCKING │ Ganzen Text als 1 Chunk  │
│ MCP extract_keywords fail│ NON-BLOCKING │ Skip Clustering          │
│ Keine Items extrahiert   │ NON-BLOCKING │ WARNING + leere Sektionen│
│ Vault nicht erreichbar   │ NON-BLOCKING │ Fallback .claude/output/ │
│ Transkript > 100K Woerter│ WARNING      │ "Sehr langes Transkript" │
└──────────────────────────┴──────────────┴──────────────────────────┘
```

---

## Beispiel-Aufruf

```bash
# Einfach:
/_transkriptRaffinieren meeting-2026-02-16.txt

# Mit Optionen:
/_transkriptRaffinieren sprint-review.txt --output /home/user/Vault/Meetings --date 2026-02-14
```

**Erwartetes Ergebnis:**
```
Meeting raffiniert:
  - Output: /home/user/Vault/Meetings/Meeting_2026-02-14_SprintReview.md
  - 5 Decisions, 8 Actions, 3 Questions
  - Textreduktion: 92%
  - Read-Time: 2.1 min
  - Status: PASS

Fuer RAG-Ingest: /_W_push_temp --files /home/user/Vault/Meetings/Meeting_2026-02-14_SprintReview.md
```

---

## Design-Entscheidungen

| Entscheidung | Wahl | Begruendung |
|---|---|---|
| Implementierung | Claude-Prompt (kein Bash) | Alle /_* Commands sind Prompts. Claude IST das LLM. |
| Chunking | MCP chunk_document | Verfuegbar, getestet, custom params moeglich |
| Clustering | MCP extract_keywords | Verfuegbar, leichtgewichtig, kein K-Means noetig |
| Output | Obsidian Markdown | User-Korrektur: kein HTML, Vault-kompatibel |
| RAG-Ingest | Separater W_push_temp | Separation of Concerns, User entscheidet |
| Speaker-Tags | Optional (Context > Person) | Muss ohne funktionieren (Kern-Requirement) |
| Confidence | Anzeigen, nicht filtern | User entscheidet, v2.0 Flag moeglich |

---

## Obsidian-Tags

```yaml
tags:
  - type/command
  - op/TranskriptRaffinerie
  - tier/0
  - topic/knowledge-extraction
  - topic/meeting-processing
version: 1.0
chain-position: standalone (Tier 0, pre-W-Commands)
prev: null
next: /_W_push_temp (optional, manuell)
```
