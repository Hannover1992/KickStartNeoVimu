---
type: satellite
---

# /_question — Einzelne HiL-Entscheidungsfrage mit Tiefen-Kontext

```yaml
status: active
version: 1.2.0
created: 2026-04-17
updated: 2026-06-16
op: Question
phase: HiL
chain_position: standalone
difficulty_scaling: false
coldstart: true
```

## Zweck

**Strukturierte HiL-Entscheidungsfrage mit Kontext-Tiefe.**

Kombiniert drei Aspekte fuer bessere Entscheidungen:
1. **Assay-Preamble** — kurzer reflektiver Mini-Essay (100-500 Woerter), der die Tiefe der Frage sichtbar macht
2. **AskUserQuestion** — 2-4 strukturierte Optionen mit Beschreibungen (+ "Other" automatisch)
3. **Notes-Feld** — User kann freie Kommentare zur Auswahl hinzufuegen

**Warum One-Question-at-a-Time:**
- Jede Frage bekommt vollen Kontext (Assay) bevor sie gestellt wird
- User kann tief denken statt flach zu ueberspringen
- Antworten werden einzeln persistiert und koennen referenziert werden
- Komplement zu `AskUserQuestion` (wenig Kontext) und `/_assay` (kein Entscheid)

---

## Aufruf

```
/_question {FRAGE} [@kontext] [global=true] [bl=BL-XXX]
```

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|--------------|
| FRAGE | (PFLICHT) | String | Die EINE Frage, die entschieden werden soll |
| @kontext | (optional) | Dateipfad(e) | Kontext-Dateien fuer Assay (Coldstart-Modus) |
| global | false | true, false | **v1.2.0 (BL-339 AK-8 Satelliten-Sweep):** true = Question auf Projekt-Ebene (.claude/output/) erzwingen. Default false = Question gehoert in das Backlog-Item an dem gerade gearbeitet wird ({bl_folder}/Questions/). |
| bl | (optional) | BL-XXX / DCSRE-XXX | Explizite BL-ID — uebersteuert die automatische BL-Kontext-Aufloesung (Schritt 0). |

**Invariante:** EINE Frage pro Aufruf. Mehrere Fragen = mehrere `/_question`-Aufrufe sequentiell.

**Beispiele:**
```
# Architektur-Entscheidung mit Pipeline-Kontext:
/_question "Welcher Scope fuer VOP-Migration?"

# Coldstart mit explizitem Kontext:
/_question "Edge-Richtung BL-110/BL-109" @.claude/pileOfMud/BacklogAbhaengigkeitsgraph_RAW_2026-04-17_transkript.md

# Duplikat-Klaerung:
/_question "BL-049 und BL-065 Duplikat oder Komplement?"
```

---

## VERTRAG

```
+======================================================================+
| VERTRAG: /_question                                                    |
+======================================================================+
|                                                                        |
| ACTOR: QUESTION-MODERATOR (Claude)                                    |
|   TUT:                                                                 |
|     - Analysiert Kontext (Manifest, Model, letzte Artefakte, @kontext)|
|     - Schreibt Assay-Preamble (100-500 Woerter) zur EINEN Frage       |
|     - Definiert 2-4 Optionen mit Label + Description + optional Preview|
|     - Markiert EINE Option mit "(Recommended)" wenn begruendbar        |
|     - Ruft AskUserQuestion mit genau 1 Question auf                    |
|     - Persistiert Frage + Assay + Antwort in Output-Datei              |
|   NICHT:                                                               |
|     - Mehrere Fragen gleichzeitig stellen                              |
|     - Assay ueberspringen (Tiefe geht verloren)                        |
|     - Mehr als 4 Optionen (Uebersicht geht verloren)                   |
|     - "Other"-Option selbst anlegen (wird automatisch ergaenzt)        |
|     - Entscheidung vor User treffen (Assay-Empfehlung okay, aber User  |
|       darf widersprechen)                                              |
|                                                                        |
| LIEST:                                                                 |
|   Kontext-Modus (automatisch erkannt):                                |
|   A) PIPELINE-MODUS (Manifest vorhanden + Feature aktiv):            |
|      1. .claude/analysis/_manifest.md                                 |
|      2. .claude/models/{NAME}_Model.md (falls Feature aktiv)          |
|      3. .claude/analysis/synthese/{NAME}-*.md (letzte Artefakte)     |
|      4. .claude/presentation/*.md (falls Praesentation vorhanden)     |
|   B) COLDSTART-MODUS (@kontext angegeben ODER kein Manifest):        |
|      1. @kontext Dateien (falls angegeben)                            |
|      2. Eigenes Wissen / Gespraechs-Kontext                          |
|                                                                        |
| SCHREIBT (v1.2.0 BL-Routing, BL-339 AK-8 Satelliten-Sweep):           |
|   DEFAULT (BL-Kontext aufloesbar, global!=true):                       |
|     1. {bl_folder}/Questions/Question_{DATE}_{FRAGE_CLEAN}.md          |
|        (Vault, im Backlog-Item an dem gerade gearbeitet wird;          |
|         Questions/-Ordner lazy erstellen — ADR-03)                     |
|   GLOBAL (global=true ODER kein BL-Kontext aufloesbar):                |
|     1. .claude/output/Question_{DATE}_{FRAGE_CLEAN}.md (Projekt-Ebene)|
|      - Status initial: pending                                        |
|      - Nach AskUserQuestion-Antwort: answered + Antwort + Notes       |
|                                                                        |
| POSITION:                                                              |
|   TYPE: STANDALONE (Satellit-Command)                                  |
|   EINSATZ: Vor Entscheidungen, an HiL-Gates, bei Ambiguitaet          |
|   CHAIN: Keine feste Position — frei einsetzbar                       |
+======================================================================+
```

---

## Ablauf

### Schritt 0: Kontext erkennen und laden

```
1. @kontext angegeben?
   → JA: Lies die angegebenen Dateien. COLDSTART-MODUS.
   → NEIN: Weiter zu Schritt 0.2

2. Manifest vorhanden (.claude/analysis/_manifest.md)?
   → JA: Lies Manifest. Bestimme aktuelles Feature/Phase.
         Lies zugehoerige Artefakte (Model, Synthese, Task.md, Praesentation).
         PIPELINE-MODUS.
   → NEIN: COLDSTART-MODUS. Nutze Gespraechs-Kontext + eigenes Wissen.

3. Bestimme Datum (YYYY-MM-DD).
4. Sanitize FRAGE → {FRAGE_CLEAN} (Leerzeichen→Underscore, Sonderzeichen weg, max 50 Zeichen)

5. OUTPUT-ROUTING (v1.2.0 BL-339 AK-8 — Question gehoert ins Backlog-Item):

   IF global == true:
     OUTPUT_PATH = .claude/output/Question_{DATE}_{FRAGE_CLEAN}.md
     → Logge: "[QUESTION] global=true → Projekt-Ebene"
   ELSE:
     BL-KONTEXT-AUFLOESUNG (Prioritaets-Kette, erste Quelle gewinnt):
       a) Expliziter Param: bl=BL-XXX
       b) Branch-Kontext: py -3 .claude/scripts/current_context.py --format=json
          → bl_id (nur wenn != null; auf generischen Branches wie
          feature/bdf-YYYY-MM-DD liefert das null — dann weiter zu c)
       c) Gespraechskontext: An welchem BL-Item wird in dieser Session
          GERADE gearbeitet? (Dieselbe Herleitung wie das feature:-Feld
          im Frontmatter — wenn du dort eine BL-ID einsetzen kannst,
          IST das der BL-Kontext.)
       d) Keine Quelle liefert BL-ID → FALLBACK global:
          OUTPUT_PATH = .claude/output/Question_{DATE}_{FRAGE_CLEAN}.md
          → Logge: "[QUESTION] Kein BL-Kontext aufloesbar → Fallback Projekt-Ebene
            (explizit erzwingen: bl=BL-XXX)"

     IF BL_ID aufgeloest:
       bl_folder = py -3 .claude/scripts/resolve_bl_path.py {BL_ID}
       mkdir -p {bl_folder}/Questions/        # lazy, ADR-03
       OUTPUT_PATH = {bl_folder}/Questions/Question_{DATE}_{FRAGE_CLEAN}.md
       → Logge: "[QUESTION] BL-Kontext: {BL_ID} → {bl_folder}/Questions/"
```

### Schritt 1: Assay-Preamble schreiben (100-500 Woerter)

Schreibe einen reflektiven Mini-Essay der:
- Die **Tiefe** der Frage sichtbar macht (Warum ist das ueberhaupt eine Frage?)
- **Tradeoffs** benennt (Was steht auf dem Spiel? Welche Richtungen gibt es?)
- **Evidenz** aus dem Kontext einbezieht (Transkripte, Modelle, vorherige Entscheidungen)
- **Keine Vollstaendigkeit** anstrebt — EINE Linie der Argumentation
- In eigenen Worten bleibt (Feynman-Prinzip)

**Stil:** expository (Default) — reflective wenn Frage sich auf Gelerntes bezieht.

Nicht:
- Bullet-Points oder Listen
- Executive Summary
- Option-Vorschau (das kommt in der Question)
- Entscheidung vorwegnehmen (darf am Ende eine Empfehlung geben, aber offen lassen)

### Schritt 2: Optionen definieren (2-4)

| Feld | Beschreibung |
|------|-------------|
| `label` | 1-5 Woerter. Bei empfohlener Option: "(Recommended)" anhaengen |
| `description` | 1-3 Saetze. Was passiert wenn diese Option gewaehlt wird? Tradeoff klar machen. |
| `preview` | Optional. Mermaid-Sketch, Folder-Tree, Code-Snippet — visuelle Vergleichshilfe |

**Regeln:**
- 2-4 Optionen (nicht weniger, nicht mehr)
- Mutually exclusive (es sei denn `multiSelect=true` — selten noetig)
- Recommended-Option ZUERST wenn es eine gibt (Reihenfolge signalisiert Default)
- KEINE "Other"-Option anlegen — wird automatisch durch AskUserQuestion ergaenzt

### Schritt 3: Output-Datei schreiben (Status: pending)

Schreibe in {OUTPUT_PATH} (aus Schritt 0.5 — BL-Ordner ODER Projekt-Ebene).

```markdown
---
id: Question_{DATE}_{FRAGE_CLEAN}
type: question
tags:
  - type/question
  - topic/{FRAGE_CLEAN}
  - context/{PIPELINE|COLDSTART}
  - bl/{BL_ID}                      # nur wenn BL-Kontext aufgeloest (v1.2.0)
date: {DATE}
created: {DATE}
updated: {DATE}
feature: {NAME oder "standalone"}
bl-item: {BL_ID oder null}          # v1.2.0 — Pflicht wenn Question im Vault landet
                                    # (vault_document_frontmatter_schema, BL-045 RF-06)
phase: {aktuelle Phase oder "coldstart"}
status: pending
---

# {FRAGE}

## Context-Assay

[Der Assay — 100-500 Woerter, eigene Worte, EINE Linie der Argumentation]

## Options

| # | Label | Description |
|---|-------|-------------|
| A | {label_a} | {desc_a} |
| B | {label_b} | {desc_b} |
| ... | ... | ... |
| Other | (free-text) | User kann eigene Antwort geben |

## Answer

_pending_

## Decision-Rationale

_pending_
```

### Schritt 4: AskUserQuestion aufrufen

Rufe `AskUserQuestion` mit genau 1 question-Objekt auf:

```typescript
AskUserQuestion({
  questions: [{
    question: FRAGE,
    header: {max 12 Zeichen},  // kurze Label fuer UI-Chip
    multiSelect: false,        // Default. true nur wenn nicht-exklusiv
    options: [
      { label, description, preview? },
      ...
    ]
  }]
})
```

### Schritt 5: Antwort verarbeiten

Wenn User geantwortet hat:

1. **Output-Datei aktualisieren:**
   - status: answered
   - Answer-Sektion: gewaehlte Option + Label
   - Notes-Sektion: User-Notes (wenn vorhanden)
   - Decision-Rationale: Claude formuliert in 2-4 Saetzen:
     - Was die Antwort bedeutet
     - Welcher naechste Schritt daraus folgt
     - Welche anderen Fragen jetzt entblockt sind (falls relevant)

2. **Terminal-Output (PFLICHT):**
   ```
   **Question Answered** | {DATE} | {FRAGE_CLEAN}

   User-Wahl: {Option-Label}
   {Notes (falls vorhanden)}

   **Konsequenz:** {2-3 Saetze Decision-Rationale}

   Naechster Schritt: {was jetzt getan werden kann}

   *Ziel: {BL_ID|global} | Datei: {OUTPUT_PATH}*
   ```

### Schritt 6 (optional): Email

Wenn `GMAIL_ADDRESS` + `GMAIL_APP_PASSWORD` gesetzt:
```bash
python3 .claude/scripts/email_sender.py \
  "[OmniCommand] Question Answered: {FRAGE_CLEAN}" \
  --body-from-file "{OUTPUT_PATH}"
```

Fehlschlag non-blocking — Datei + Terminal-Output reichen.

---

## One-Shot-Example (KRITISCH — Assay MUSS in question-Feld)

**Problem-Beobachtung 2026-04-20 (F01-Review BL-124):**
Wenn der Assay nur als Terminal-Text VOR `AskUserQuestion` geschrieben wird,
sieht der User ihn im HiL-Dialog NICHT. Der AskUserQuestion-UI zeigt nur
`question` + `options` an — vorangehender Text geht im Stream verloren.

**Loesung:** Der Assay-Preamble MUSS in das `question`-Feld von `AskUserQuestion`
eingebettet werden (mit `\n\n`-Trennern). So erscheint er im HiL-Dialog
unmittelbar ueber den Optionen.

**Pattern:**

```
AskUserQuestion({
  questions: [{
    question: "{HEADLINE mit Meta (Typ|Kategorie|Konfidenz)}.\n\n" +
              "ASSAY: {Kern-Argument 1-2 Absaetze}\n\n" +
              "{Evidenz-Absatz}\n\n" +
              "DISKUSSION: {Offene Frage / Tradeoff}\n\n" +
              "Wie weiter?",
    header: "{max 12 Zeichen Chip}",
    multiSelect: false,
    options: [
      { label: "Uebernehmen (Recommended)", description: "..." },
      { label: "Praezisieren",              description: "..." },
      { label: "Dismissal",                 description: "..." }
    ]
  }]
})
```

**Konkretes Beispiel — F01 BL-124 Findings-Review (funktionierend):**

```
question: "F01 — Worker-Agenten lesen beim Spawn nur drei Artefakte (PL-Item + Source + Tests). CORE | HIGH-Konfidenz.

ASSAY: Das ist das Fundament-Finding — alles andere in BL-124 baut darauf auf. Fix-, Diagnose- und Blueprint-Agenten konsumieren typischerweise nur drei Input-Klassen, wenn sie gespawnt werden: das Parking-Lot-Item (oft in freiem Text), die zu aendernden Source-Dateien und die fehlschlagenden Tests.

Das klingt harmlos, ist aber die Wurzel der Contract-Starvation. Die drei Artefakte decken Symptom und lokalen Code ab, aber sie sagen dem Agent nichts darueber, *warum* der Code so ist, wie er ist. Kein Model, kein Git-Log, keine ADRs, kein Assay-Archiv — alles historische und architektonische Information bleibt aussen vor. Der Agent sieht einen Querschnitt, aber keine Zeitachse, keine Intention.

Evidenz: der DCSRE-1430-Fall (F03) ist das Symptom, F01 ist die Diagnose der Eingabe-Struktur. Ohne F01 waere F03 ein Einzelfall. Mit F01 wird F03 zu einer klassifizierbaren Erkrankung.

DISKUSSION: CORE+HIGH ist gerechtfertigt. Einzige offene Frage — ist die Zaehlung *genau drei* korrekt? Manche Agents sehen zusaetzlich Task.md, CLAUDE.md oder Orchestrator-Prompts. Verfeinerung moeglich, aber keine Widerlegung. Kern-Aussage bleibt: Symptom + lokalen Kontext, nicht Intention + Historie.

Wie weiter?"

header:       "F01 Review"
multiSelect:  false
options:
  - label:       "Uebernehmen (Recommended)"
    description: "Unveraendert ins Crumbs-File. Praezise Liste der tatsaechlich uebergebenen Artefakte kommt spaeter in der Vertrags-Matrix (Model-Phase)."
  - label:       "Praezisieren"
    description: "Liste erweitern — neben PL/Source/Tests auch Task.md, CLAUDE.md, Skill-Prompt etc. explizit im Finding nennen."
  - label:       "Dismissal"
    description: "Raus — Finding zu generisch oder durch F02 (spezifische Vertragsluecken) bereits abgedeckt."
```

**Was dieses Beispiel zeigt:**
- Headline mit Meta-Tags (Typ | Kategorie | Konfidenz) — sofortige Einordnung
- ASSAY-Block: 3 Absaetze (Kern-Argument, Evidenz, Diskussion) — eingerueckt klar lesbar
- DISKUSSION-Block benennt die offene Frage explizit — kein verstecktes Tradeoff
- Schluss-Satz "Wie weiter?" fuehrt in die Options ueber
- 3 Optionen (nicht 4) — Uebersicht bleibt, "Other" wird automatisch ergaenzt
- Label mit "(Recommended)" Suffix auf Default-Option

**Anti-Pattern (NICHT tun):**
- Assay nur als Text VOR dem Tool-Call schreiben → geht im Stream verloren
- Assay in option.description quetschen → Optionen werden unlesbar
- Assay in option.preview pro Option wiederholen → Duplikation
- Assay ganz weglassen und nur Question-Headline → keine Tiefe, HiL wird oberflaechlich

**Parallele zum Output-File:**
Der vollstaendige Assay (ausfuehrlicher, bis 500 Woerter) bleibt zusaetzlich im
Output-File {OUTPUT_PATH} (aus Schritt 0.5 — `{bl_folder}/Questions/` im Vault
ODER `.claude/output/` auf Projekt-Ebene). Im HiL-Dialog erscheint eine
kompaktere Variante (100-300 Woerter) — darin inhaltlich identisch, nur evtl.
gekuerzt.

---

## Self-Checks (VOR AskUserQuestion)

**G1 — Ein-Frage-Check:**
Ist das GENAU EINE Frage? Wenn mehrere verschachtelt sind: aufteilen in mehrere `/_question`-Aufrufe.

**G2 — Antwortbarkeit-Check:**
Koennen die 2-4 Optionen wirklich alle realen Antworten abdecken (mit "Other" als Escape)? Wenn Antwort-Raum zu gross ist: Frage eingrenzen.

**G3 — Orthogonalitaet-Check:**
Sind die Optionen wirklich alternativ (exclusive)? Wenn sie sich ueberschneiden: neu schneiden.

**G4 — Kontext-Tiefe-Check:**
Hat der Assay genug Tiefe? Wenn er generisch klingt: mehr Evidenz aus Manifest/Model/Transkripten hineinbringen.

---

## Fehler-Handling

```
+-------------------------------+--------------+-----------------------------------+
| Fehler                        | Typ          | Reaktion                          |
+-------------------------------+--------------+-----------------------------------+
| FRAGE fehlt                   | BLOCKING     | ABORT + WARNUNG: /_question braucht eine Frage |
| Mehr als eine Frage im Aufruf | BLOCKING     | ABORT + Aufforderung zur Aufspaltung |
| Manifest nicht lesbar         | NON-BLOCKING | COLDSTART-Modus                   |
| BL-Kontext nicht aufloesbar   | NON-BLOCKING | Fallback Projekt-Ebene + Log-Hint |
|                               |              | "explizit: bl=BL-XXX" (v1.2.0)    |
| resolve_bl_path schlaegt fehl | NON-BLOCKING | Fallback Projekt-Ebene + WARNUNG  |
| User waehlt "Other"           | OK           | Notes-Feld = User-Freitext        |
| User bricht ab (Esc)          | NON-BLOCKING | Datei bleibt status=pending       |
| Email fehlgeschlagen          | NON-BLOCKING | WARNUNG + weiter (Datei existiert)|
| Kontext zu duenn fuer Assay   | NON-BLOCKING | Ehrlich sagen + kuerzerer Assay   |
+-------------------------------+--------------+-----------------------------------+
```

---

## Unterschiede zu verwandten Commands

| Command | Input | Output | Zweck |
|---------|-------|--------|-------|
| `/_assay` | Thema | Essay (Report) | Tiefenverstaendnis sichtbar machen |
| `/_question` | Frage + Optionen | Assay + Antwort | HiL-Entscheidung mit Tiefe |
| `AskUserQuestion` (raw) | Frage + Optionen | Antwort | Schnelle HiL-Entscheidung ohne Kontext |
| `/_presentation` | Feature | Technisches Dokument | Status-Report fuer User |

**Faustregel:** 
- Trivialentscheidung → rohes `AskUserQuestion`
- Entscheidung mit Tiefe → `/_question`
- Reines Verstaendnis-Teilen → `/_assay`
- Technische Zusammenfassung → `/_presentation`

---

## Changelog

### v1.2.0 (2026-06-16) — BL-339 AK-8 Satelliten-Sweep: /_question ins BL-Kontext-Routing

- **Default-Routing geaendert:** Question landet im BL-Ordner an dem gerade gearbeitet
  wird ({bl_folder}/Questions/, lazy mkdir) statt pauschal .claude/output/.
- **BL-Kontext-Aufloesung** (Schritt 0.5): bl=-Param > Branch (current_context.py)
  > Gespraechskontext (analog feature:-Feld) > Fallback Projekt-Ebene mit Log.
- **global=true** Param: erzwingt Projekt-Ebene (.claude/output/) auf expliziten Wunsch.
- **Vault-Frontmatter-Konformitaet:** type/bl-item/created/updated + bl/{BL_ID}-Tag
  ergaenzt (vault_document_frontmatter_schema, BL-045 RF-06) — Pflicht sobald die
  Question im Vault liegt (P-12 Rueckverfolgbarkeit).
- Mirror des /_assay v2.1.0 Output-Routing-Patterns (Satelliten-Sweep der
  output-Commands: /_assay, /_presentation, /_answer, /_handout, /_question).
