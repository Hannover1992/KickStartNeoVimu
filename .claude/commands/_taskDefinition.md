# Task-Definition: Aufgabe & Kruemmel sammeln

Du definierst die Aufgabe und verarbeitest Rohmaterial zu strukturierten Kruemmeln (Crumbs).

## Aufruf

```
/_taskDefinition {NAME} [easy|normal|hard]
```

- **NAME** (Pflicht): Eindeutiger Name, z.B. `Dateiabholung`, `Auth-Flow`
- **Schwierigkeit** (Optional): Default `normal`

---

## VERTRAG (Pflicht-I/O)

```
╔═══════════════════════════════════════════════════════════════╗
║  COMMAND: /_taskDefinition {NAME}                            ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  LIEST (Input):                                               ║
║    1. .claude/analysis/_manifest.md (falls vorhanden)         ║
║    2. .claude/Task.md (falls vorhanden)                       ║
║    3. .claude/pileOfMud/* (Rohmaterial: PDFs, Screenshots,    ║
║       Diagramme, alte Models, Texte, Bilder)                  ║
║    4. .claude/models/{NAME}_Model.md (falls bereits vorh.)    ║
║    5. User-Input (Frage, Kontext, Anforderungen)              ║
║                                                               ║
║  SCHREIBT (Output) - PFLICHT:                                 ║
║    1. .claude/Task.md (erstellen/aktualisieren)               ║
║    2. .claude/crumbs/{NAME}_crumbs.md                         ║
║    3. .claude/analysis/_manifest.md (aktualisieren)           ║
║                                                               ║
║  PRE-CYCLE POSITION:                                          ║
║    [/_taskDefinition] ──▶ [/_spec]* ──▶ [/_model] ──▶ Zyklus  ║
║    * /_spec ist OPTIONAL (nur bei Architektur-Vorgaben)       ║
║    Sammelt Rohmaterial, strukturiert als Crumbs,              ║
║    bereitet Input fuer /_spec oder /_model vor                ║
║                                                               ║
║  COMPACT-SICHER:                                              ║
║    Task.md + Crumbs-Datei ueberleben /compact.               ║
║    /_model liest Crumbs von Disk.                             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Was sind Kruemmel (Crumbs)?

Kruemmel sind **strukturierte Wissens-Fragmente** die aus Rohmaterial extrahiert werden:

```
.claude/pileOfMud/                    .claude/crumbs/
├── architektur-zeichnung.png    ──▶  {NAME}_crumbs.md
├── confluence-export.pdf        ──▶    ├── Mermaid-Diagramme
├── user-story.txt               ──▶    ├── Anforderungen
├── altes-model.md               ──▶    ├── Bekanntes Wissen
├── screenshot-sequenz.jpg       ──▶    ├── Sequenz-Flows
└── kommentar-carsten.txt        ──▶    └── Offene Fragen

ROHMATERIAL (unstrukturiert)          KRUEMMEL (strukturiert, Markdown+Mermaid)
```

**Kernidee:** Aus einem "Haufen Schlamm" (pileOfMud) werden saubere Kruemmel, die das Model fuettern.

---

## pileOfMud - Ablage-Regeln (KRITISCH)

pileOfMud ist der **Schlamm-Haufen**: ALLES was der User liefert wird 1:1 abgelegt.
Nichts weglassen, nichts filtern. Alles rein, auf einen Haufen.

### Screenshots / Bilder von Diagrammen

```
FALSCH (Kunstschule):
  "Das Bild zeigt ein UML-Sequenzdiagramm mit 6 Teilnehmern..."
  "Dunkler Hintergrund, weisse Kaesten..."
  → VERBOTEN. Wir beschreiben keine Bilder.

RICHTIG (Nachbildung):
  ```mermaid
  sequenceDiagram
      Worker->>API: DIC_FA_Assignment()
      ...
  ```
  → Das Diagramm wird als Mermaid NACHGEBAUT.
```

**Regel:** Wenn der User einen Screenshot von einem UML-Diagramm gibt,
wird das Diagramm im pileOfMud als **Mermaid-Nachbildung** abgelegt.
Keine Textbeschreibung. Keine Bildbeschreibung. Mermaid-Code.

### Alle anderen Formate

| User gibt... | pileOfMud bekommt... |
|--------------|----------------------|
| Screenshot UML-Sequenz | Mermaid `sequenceDiagram` |
| Screenshot UML-Klassen | Mermaid `classDiagram` |
| Screenshot UML-Zustand | Mermaid `stateDiagram-v2` |
| Screenshot Flowchart | Mermaid `flowchart` |
| Screenshot ER-Diagramm | Mermaid `erDiagram` |
| Text (Jira, Confluence) | 1:1 als Markdown |
| Code-Snippets | 1:1 als Fenced Code |
| Kommentare / Hinweise | 1:1 als Markdown |
| PDF-Inhalt | Text extrahiert als Markdown |

### Datei-Benennung

```
.claude/pileOfMud/
├── 01_{Beschreibung}.md     ← Nummeriert, kurzer Name
├── 02_{Beschreibung}.md
├── 03_Sequenzdiagramm_{Was}.md  ← Diagramm-Typ im Namen
└── ...
```

---

## Was ist Task.md?

`.claude/Task.md` ist die **globale Aufgaben-Definition**:

```markdown
# Task: {NAME}

**Typ:** Recherche-Plan | Wissenschaftliche Frage | Implementierung | Bug-Fix
**Datum:** YYYY-MM-DD
**User Story:** {TICKET-ID} (falls vorhanden)

## Frage / Auftrag
{Was soll geloest/untersucht/gebaut werden?}

## Kontext
{Warum ist das wichtig? Business-Value?}

## Erfolgskriterien
{Wann ist die Aufgabe erledigt?}

## Verfuegbare Informationen
{Was haben wir schon? Welche Quellen?}

## Einschraenkungen / Scope
{Was ist NICHT Teil der Aufgabe?}

## Initiale Komplexitaets-Einschaetzung (v2.0+, OPTIONAL)
{leicht / mittel / schwer / unbekannt}

## Erwartete Concerns (v2.0+, OPTIONAL)
{Vorab-Identifikation beteiligter Technologie-Bereiche, z.B.:}
{- Netzwerk/SFTP, Zertifikate/TLS, Container/Docker, Datenbank/EF}
{Hilft _model bei der initialen TC-Strukturierung}
```

---

## Schritt 0: Bestandsaufnahme + Kontinuitaets-Pruefung (KRITISCH)

**IMMER als Erstes -- BEVOR du den User fragst:**

1. Lies `.claude/analysis/_manifest.md` falls vorhanden
   - Lies **SYSTEM-MODEL** und **SCHWIERIGKEIT** aus der System-Konfiguration
   - Bestimme effektives Modell: `min(SYSTEM-MODEL, Command-Max=opus)`
   - Leite Modell-Zuordnung pro Welle ab (siehe Manifest → Modell-Zuordnung)
   - **NEU:** Lies **OFFENE TASKS** aus der Task-Sektion (falls vorhanden)
   - **NEU:** Lies **STAGNATION** Zaehler (falls vorhanden)
   - **NEU:** Lies **PHASE** -- wo steht der aktuelle Zyklus?
2. Pruefe ob `.claude/Task.md` existiert
3. Pruefe ob `.claude/models/{NAME}_Model.md` existiert (altes Model)
   - **NEU:** Falls Model existiert: Lies Version, W{n}-Anzahl, Letzte Aktualisierung
   - **NEU:** Falls Model-Topologie existiert (`{NAME}_Model-Topologie.md`):
     Lies Teilmodel-Uebersicht, FOKUS-TC, SRS pro Teilmodel.
     Model-Topologie folgt dem Muster von `Topologie-OmniCommand.md`.
4. Scanne `.claude/pileOfMud/` nach verfuegbarem Rohmaterial
5. Pruefe ob `.claude/analysis/synthese/{NAME}-ERGEBNIS*.md` existiert
   - **NEU:** Falls ja: Lies letzten SRS-Score + Stagnations-Zaehler
6. **Entscheidungsbaum: NEUES Feature oder BESTEHENDES Feature?**

### Entscheidungsbaum: Kontinuitaet

```
Manifest vorhanden?
├── NEIN → NEUES FEATURE (Schritt 1 normal)
└── JA → Pruefe Task.md + Model
         ├── Task.md NICHT vorhanden → NEUES FEATURE
         └── Task.md vorhanden → BESTEHENDES FEATURE
              │
              ├── Pruefe: Alle W{n} bestaetigt/widerlegt?
              │    └── JA → FEATURE ABGESCHLOSSEN
              │         → Vorschlag: "Feature scheint abgeschlossen.
              │           Optionen: (A) Model-Finish (/_model finish),
              │                     (B) Model-Split, (C) Neues Feature"
              │
              ├── Pruefe: Gibt es offene Tasks im Manifest?
              │    └── JA → TASK-KONTINUITAET
              │         → Zeige bestehende Tasks mit Priorisierung
              │         → Schlage naechsten Task vor (Proximity-Prinzip)
              │         → User entscheidet: bestehender Task ODER neuer Task
              │
              └── Keine offenen Tasks, W{n} offen
                   → NORMALER NEUER TASK im bestehenden Feature
                   → Model wird weiterverwendet (NICHT neu erstellt!)
```

### Bei TASK-KONTINUITAET: Priorisierung anzeigen

Falls offene Tasks existieren, zeige sie priorisiert an:

```
Bestehendes Feature: {NAME}
Model-Version: {X.Y} mit {N} aktiven W{n}
Letzte Phase: {PHASE}

Offene Tasks (priorisiert nach Proximity):
┌────┬────────────────────────┬──────────┬──────────────┐
│ #  │ Task                   │ Naehe    │ Status       │
├────┼────────────────────────┼──────────┼──────────────┤
│ 1  │ {nah am aktuellen TC}  │ HOCH     │ offen        │
│ 2  │ {gleicher Bereich}     │ MITTEL   │ offen        │
│ 3  │ {anderer Bereich}      │ NIEDRIG  │ offen        │
└────┴────────────────────────┴──────────┴──────────────┘

Empfehlung: Task #{N} hat die hoechste Naehe zum aktuellen
Arbeitsbereich ({TC-Name}).

Optionen:
  (A) Task #{N} bearbeiten (empfohlen)
  (B) Neuen Task hinzufuegen
  (C) Feature abschliessen (Model-Finish)
```

**Proximity-Prinzip:** Tasks die im gleichen Technologie-Concern (TC) liegen wie
der zuletzt bearbeitete Task werden hoeher priorisiert. Das schont den Kontext
und vermeidet unnoetige Kontext-Wechsel.

### Bei FEATURE ABGESCHLOSSEN: Model-Finish vorschlagen

```
Feature "{NAME}" scheint abgeschlossen!

  Alle W{n} bestaetigt oder widerlegt.
  SRS-Score: {Zahl} (zuletzt {Trend})
  Stagnation: {Zaehler}

Empfohlene naechste Schritte:
  (A) /_model {NAME} finish -- Model verfeinern, konsolidieren + Split-Pruefung
      → Bei Split: Model-Topologie erstellen (Muster: Topologie-OmniCommand.md)
  (B) Neues Feature starten -- Komplett neuer Kontext
  (C) Weitermachen -- Es gibt noch offene Punkte
```

7. Frage den User nach der Aufgabe falls nicht klar

---

## Schritt 1: Task.md erstellen/aktualisieren

### 1a: Falls Task.md NICHT existiert (Neues Feature)

1. Frage den User:
   - Was ist die Aufgabe? (Frage/Problem/Ziel)
   - Welcher Typ? (Recherche, Wissenschaftliche Frage, Implementierung, Bug-Fix)
   - Welche Erfolgskriterien?
   - Was ist NICHT im Scope?
2. Schreibe `.claude/Task.md`

### 1b: Falls Task.md EXISTIERT (Task-Kontinuitaet)

1. Lies bestehende Task.md
2. Zeige dem User den aktuellen Stand (Aufgabe, offene Tasks)
3. Frage: Neuer Task zum bestehenden Feature ODER Update der bestehenden Aufgabe?
4. Falls neuer Task: Haenge an die Task-Liste an (NICHT ueberschreiben!)
5. Falls Update: Aktualisiere die relevanten Sektionen

### Task-Liste in Task.md (NEU v2.1)

Task.md erhaelt eine persistente Task-Liste die ueber Zyklen hinweg gepflegt wird:

```markdown
## Task-Liste

| # | Task | Prioritaet | TC-Naehe | Status | Zyklus |
|---|------|-----------|----------|--------|--------|
| T1 | {Beschreibung} | HOCH | {TC-Name} | erledigt | Cycle 1-3 |
| T2 | {Beschreibung} | MITTEL | {TC-Name} | aktiv | Cycle 4 |
| T3 | {Beschreibung} | NIEDRIG | {anderer TC} | offen | - |
| T4 | {Beschreibung} | HOCH | {TC-Name} | offen | - |

### Priorisierungs-Regeln
- HOCH: Gleicher TC wie aktueller Fokus, blockiert andere Tasks
- MITTEL: Gleicher TC, kann parallel oder danach
- NIEDRIG: Anderer TC, erfordert Kontext-Wechsel
```

**WICHTIG:** Die Task-Liste wird NIEMALS geloescht, nur erweitert.
Erledigte Tasks bleiben als Historie sichtbar.
Neue Tasks werden ANGEHAENGT, nicht eingeschoben.

---

## Schritt 2: pileOfMud scannen und verarbeiten

### Schwierigkeits-Parameter

| Schwierigkeit | Agenten | Rohmaterial-Verarbeitung |
|---------------|---------|--------------------------|
| **easy** | 1 (DU, Hauptagent) | Nur User-Input + Text-Dateien |
| **normal** | 2-3 Subagenten + Hauptagent | + PDFs, Screenshots, Diagramme |
| **hard** | 3-5 Subagenten + Hauptagent | + Tiefe Analyse, Cross-Referencing, alte Models |

**System-Model (aus Manifest):** Bestimmt welches Modell pro Welle laeuft.
- opus: Drafts=sonnet, Synthese=opus
- sonnet: Drafts=sonnet, Synthese=sonnet
- haiku: Drafts=haiku, Synthese=haiku

### Ablauf: normal

```
Scan:     ┌─────────────┐
          │ pileOfMud/* │  ──▶ Liste aller Dateien + Typen
          └──────┬──────┘
                 │
                 ▼
Welle 1:  ┌───┐ ┌───┐ ┌───┐
DRAFTS    │ D │ │ D │ │ D │  ──LIEST──▶ pileOfMud/* + Task.md
          └─┬─┘ └─┬─┘ └─┬─┘  ──SCHREIBT──▶ drafts/{NAME}-crumbs-D*.md
            └─────┼─────┘
                  │
             [/compact moeglich]
                  │
                  ▼
Welle 2:  ┌─────────────┐
SYNTHESE  │  DU, Hauptagent  │  ──LIEST──▶ drafts/{NAME}-crumbs-D*.md
          │   (= DU)    │  ──SCHREIBT──▶ crumbs/{NAME}_crumbs.md
          └─────────────┘
```

### Drafter-Auftraege fuer Rohmaterial

Jeder Drafter verarbeitet einen Teil des Rohmaterials:

```
Du bist Drafter D{NN} fuer die Kruemmel-Extraktion von "{NAME}".

INPUT - LIES ZUERST:
  1. .claude/Task.md (Aufgabe verstehen)
  2. .claude/pileOfMud/{zugewiesene Dateien}
  3. .claude/models/{NAME}_Model.md (falls vorhanden - altes Wissen)

AUFTRAG: Extrahiere strukturierte Kruemmel aus dem Rohmaterial.

VERARBEITUNGSREGELN:
  - pileOfMud-Dateien mit Mermaid-Diagrammen → Direkt uebernehmen, ggf. verfeinern
  - PDFs/Texte → Extrahiere Kern-Informationen als strukturierte Sektionen
  - Alte Models → Identifiziere was noch gueltig ist vs. veraltet
  - Kommentare → Extrahiere Anforderungen und offene Fragen
  HINWEIS: Screenshots wurden bereits in pileOfMud als Mermaid nachgebildet.
  Du musst sie NICHT nochmal konvertieren - lies sie direkt.

SCHREIB-PFLICHT:
Du MUSST deine Kruemmel in folgende Datei schreiben:
  .claude/analysis/drafts/{NAME}-crumbs-D{NN}-{fokus}.md

DATEI-FORMAT (Pflicht):
  ---
  name: {NAME}
  phase: taskDefinition
  wave: drafts
  tier: {SYSTEM-MODEL}
  model: {TATSAECHLICHES-MODELL}
  agent: D{NN}
  fokus: {fokus}
  date: {YYYY-MM-DD}
  quellen: {Liste der verarbeiteten pileOfMud-Dateien}
  status: final
  ---

  # Kruemmel D{NN}: {Fokus-Titel}

  ## Verarbeitete Quellen
  | Datei | Typ | Inhalt |
  |-------|-----|--------|

  ## Extrahierte Kruemmel

  ### K1: {Kruemmel-Titel}
  - **Quelle:** {pileOfMud/dateiname.ext}
  - **Typ:** Diagramm | Anforderung | Architektur | Konfiguration | Frage
  - **Inhalt:**
    {Strukturierter Inhalt, Mermaid wo moeglich}

  ### K2: ...

  ## Offene Fragen
  {Was ist unklar, was muss noch geklaert werden?}

WICHTIG:
- Mermaid-Diagramme aus pileOfMud direkt uebernehmen (schon nachgebildet!)
- JEDE Quelle mit Dateiname referenzieren
- Markdown + Mermaid verwenden, KEIN ASCII-Art in den Crumbs-Dateien
- Die Datei MUSS geschrieben werden
```

### Drafter-Fokus-Bereiche (je nach Rohmaterial)

| Agent | Fokus | Rohmaterial |
|-------|-------|-------------|
| D01 | diagramme | Screenshots, UML-Zeichnungen, Architektur-Bilder |
| D02 | dokumente | PDFs, Confluence-Exports, Texte, User Stories |
| D03 | bestehendes-wissen | Alte Models, Kommentare, bekannte Fakten |

---

## Schritt 3: Synthese → Crumbs-Datei

### Voraussetzung

Lies ALLE Dateien in `.claude/analysis/drafts/{NAME}-crumbs-D*.md`

### Crumbs-Dokument Struktur

**Pfad:** `.claude/crumbs/{NAME}_crumbs.md`

```markdown
# Kruemmel: {NAME}

**Datum:** YYYY-MM-DD
**Task:** .claude/Task.md
**Quellen:** {Anzahl} Dateien aus .claude/pileOfMud/

---

## 1. Aufgabe (aus Task.md)

**Typ:** {Typ}
**Frage:** {Wissenschaftliche Frage / Auftrag}
**Erfolgskriterien:** {Messbare Kriterien}

---

## 2. Architektur-Kruemmel

### K-A1: {Titel}
- **Quelle:** {pileOfMud/datei.ext}

```mermaid
{Diagramm}
```

### K-A2: ...

---

## 3. Anforderungs-Kruemmel

### K-R1: {Anforderung}
- **Quelle:** {pileOfMud/datei.ext}
- **Prioritaet:** MUSS | SOLL | KANN

### K-R2: ...

---

## 4. Wissens-Kruemmel

### K-W1: {Bekanntes Wissen}
- **Quelle:** {pileOfMud/datei.ext oder altes Model}
- **Status:** Aktuell | Veraltet | Unklar

### K-W2: ...

---

## 5. Sequenz-/Flow-Kruemmel

### K-F1: {Flow-Titel}
- **Quelle:** {pileOfMud/datei.ext}

```mermaid
{sequenceDiagram oder flowchart}
```

---

## 6. Offene Fragen

| # | Frage | Quelle | Prioritaet |
|---|-------|--------|------------|
| Q1 | ... | ... | Hoch/Mittel/Niedrig |

---

## 7. Bestehendes Model

Falls `.claude/models/{NAME}_Model.md` existiert:

| Sektion | Status | Aenderungsbedarf |
|---------|--------|------------------|
| Architektur | Aktuell / Veraltet | ... |
| Wahrheiten | W1-W{n} gueltig? | ... |

Falls kein bestehendes Model: "Kein bestehendes Model. /_model wird Erstinitialisierung durchfuehren."

---

## 8. Referenzen

| Quelle | Pfad | Typ |
|--------|------|-----|
| ... | .claude/pileOfMud/... | PDF/Screenshot/Text/... |

---

## Naechster Schritt

`/_model {NAME} [easy|normal|hard]` - Model erstellen/aktualisieren basierend auf diesen Kruemmeln.
```

---

## Schritt 4: Manifest aktualisieren

```markdown
# Forschungs-Manifest

**NAME:** {NAME}
**PHASE:** _taskDefinition abgeschlossen
**NAECHSTER SCHRITT:** /_spec {NAME} (falls Architektur-Vorgaben) ODER /_model {NAME} [easy|normal|hard]
**KONTINUITAET:** NEUES_FEATURE | BESTEHEND_NEUER_TASK | BESTEHEND_FORTSETZUNG

## Task
- [x] .claude/Task.md (Aufgaben-Definition)

## Aktiver Task
- **Task-ID:** T{N}
- **Beschreibung:** {Aktueller Task}
- **TC-Naehe:** {TC-Name oder "initial"}

## Offene Tasks
- [ ] T{M}: {Beschreibung} (Prioritaet: {HOCH|MITTEL|NIEDRIG})
- [ ] T{K}: {Beschreibung} (Prioritaet: {HOCH|MITTEL|NIEDRIG})

## Kruemmel
- [x] .claude/crumbs/{NAME}_crumbs.md ({Anzahl} Kruemmel aus {Anzahl} Quellen)

## Quellen (pileOfMud)
- [x] .claude/pileOfMud/{datei1}
- [x] .claude/pileOfMud/{datei2}
- ...
```

---

## pileOfMud - Unterstuetzte Formate

| Format | Ablage in pileOfMud |
|--------|---------------------|
| Screenshots von Diagrammen | **Mermaid NACHBILDEN** (kein Beschreibungstext!) |
| `.pdf` | Text extrahieren, als Markdown ablegen |
| `.md` | 1:1 uebernehmen |
| `.txt` | 1:1 uebernehmen |
| `.xml`, `.xsd` | 1:1 uebernehmen |
| `.json`, `.yaml` | 1:1 uebernehmen |
| `.cs`, `.ts`, `.py` | 1:1 uebernehmen |
| User-Text (Jira, Chat) | Als Markdown strukturiert ablegen |

---

## Sonderfall: Bestehendes Model

Falls `.claude/models/{NAME}_Model.md` bereits existiert:

```
Bestehendes Model gefunden!

  .claude/models/{NAME}_Model.md
    Version: {X.Y}
    Wahrheiten: W1-W{N}
    Letzte Aktualisierung: {Datum}

Das Model wird als Wissens-Kruemmel (K-W) in die Crumbs aufgenommen.
/_model wird es als Grundlage verwenden und aktualisieren.
```

Das bestehende Model wird NICHT ueberschrieben - es wird als Input behandelt.
`/_model` entscheidet ob Update oder Neuaufbau.

---

## Qualitaetskriterien

- Alle User-Inputs in pileOfMud abgelegt (NICHTS weglassen)
- Screenshots als Mermaid NACHGEBILDET in pileOfMud (NICHT beschrieben!)
- Alle pileOfMud-Dateien in Crumbs verarbeitet und referenziert
- Anforderungen klar als MUSS/SOLL/KANN kategorisiert
- Offene Fragen identifiziert und priorisiert
- Bestehendes Model auf Aktualitaet geprueft
- Task.md ist klar und vollstaendig
- Initiale Komplexitaet eingeschaetzt (v2.0+, OPTIONAL aber empfohlen)
- Erwartete Concerns identifiziert (v2.0+, OPTIONAL, hilft bei Model-Strukturierung)
- **NEU (v2.1):** Kontinuitaets-Pruefung durchgefuehrt (Manifest + Task.md + Model)
- **NEU (v2.1):** Bei bestehendem Feature: Tasks priorisiert nach Proximity-Prinzip
- **NEU (v2.1):** Bei abgeschlossenem Feature: Model-Finish/Split vorgeschlagen
- **NEU (v2.1):** Task-Liste in Task.md gepflegt (NICHT geloescht, nur erweitert)

---

## Naechster Schritt

Nach Abschluss:
- **Falls Crumbs Architektur-Vorgaben enthalten:** `/_spec {NAME} [easy|normal|hard]`
- **Sonst (Standard):** `/_model {NAME} [easy|normal|hard]`

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_taskDefinition abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
