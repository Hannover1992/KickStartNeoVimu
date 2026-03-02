# Spezifikation: Ziel-Architektur & Anforderungen

Du erstellst die Spezifikation (SPEC) - das Leuchtfeuer fuer die Ziel-Architektur.
SPEC beschreibt WIE ES SEIN SOLL. Model beschreibt WIE ES IST.
SPEC aendert sich selten, Model aendert sich staendig.

**Status:** NEU v3.0
**Actor:** SPEZIFIKATEUR
**Zweck:** Ziel-Architektur und Anforderungen aus Kruemmeln extrahieren

## Aufruf

```
/_spec {NAME} [easy|normal|hard]
```

- **NAME** (Pflicht): Eindeutiger Name (identisch mit /_taskDefinition und /_model)
- **Schwierigkeit** (Optional): Default `hard` bei Erstinitialisierung, `normal` bei Review

---

## VERTRAG (Pflicht-I/O)

```
+===============================================================+
|  COMMAND: /_spec {NAME} [easy|normal|hard]                     |
+===============================================================+
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. .claude/analysis/_manifest.md (falls vorhanden)          |
|    2. .claude/crumbs/{NAME}_crumbs.md                          |
|       --> Primaere Quelle: Kruemmel mit Architektur-Detail     |
|    3. .claude/Task.md                                          |
|       --> Akzeptanzkriterien, Scope-Grenzen                    |
|    4. .claude/pileOfMud/* (ergaenzend, falls Crumbs duenn)     |
|       --> Architektur-Diagramme, Confluence-Exports, RFCs      |
|    5. User-Input (Architekten-Vorgaben, muendliche Spec)       |
|                                                                |
|  LIEST (Input) - OPTIONAL:                                     |
|    6. .claude/models/{NAME}_Model.md (falls vorhanden)         |
|       --> IST-Zustand als Kontext (Gap-Bewusstsein)            |
|    7. Codebase (via Glob/Grep/Read)                            |
|       --> Bestehende Interfaces, Namenskonventionen             |
|    8. MCP Clean Code (Uncle Bob Queries)                       |
|       --> Architektur-Patterns, Clean Architecture Guidance    |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|                                                                |
|    Welle 1 (Drafts, bei normal+hard):                          |
|      .claude/analysis/drafts/{NAME}-spec-D01-{fokus}.md        |
|      .claude/analysis/drafts/{NAME}-spec-D02-{fokus}.md        |
|      ... (pro Agent eine Datei)                                |
|                                                                |
|    Welle 2 (Synthese = DU, Hauptagent):                        |
|      .claude/specs/{NAME}_Spec.md                              |
|                                                                |
|    Manifest (IMMER):                                           |
|      .claude/analysis/_manifest.md (aktualisieren)             |
|                                                                |
|  SCHREIBT (Output) - OPTIONAL:                                 |
|    .claude/_parking-lot.md (APPEND, Incidental Findings)       |
|                                                                |
|  MCP INTEGRATION (OPTIONAL, Uncle Bob Clean Code):             |
|    - mcp__cleancoder__query() fuer Architektur-Guidance        |
|    - Query Topics:                                             |
|      * "clean architecture for {domain description}"           |
|      * "interface design for {component type}"                 |
|      * "dependency inversion for {boundary}"                   |
|                                                                |
|  MCP-BREMSE:                                                   |
|    +-----------------------------------------------------+     |
|    |  easy:   MIN-Modus    --> max 1 Query,  limit=1     |     |
|    |  normal: MIDDLE-Modus --> max 3 Queries, limit=3    |     |
|    |  hard:   MAX-Modus    --> max 5 Queries, limit=5    |     |
|    |                                                     |     |
|    |  Modi:  min=1Q/1R  middle=3Q/3R  max=5Q/5R        |     |
|    +-----------------------------------------------------+     |
|                                                                |
|  PRE-CYCLE POSITION:                                           |
|    [/_taskDefinition] --> [/_spec] --> [/_model] --> Zyklus     |
|                                                                |
|  COMPACT-SICHER:                                               |
|    Spec-Datei ueberlebt /compact.                              |
|    /_model, /_SC_observe, /_I_cleanCodeArchitect lesen von     |
|    Disk.                                                       |
|                                                                |
|  ACTOR: SPEZIFIKATEUR                                          |
|    Extrahiert Ziel-Architektur aus Kruemmeln/Vorgaben.         |
|    KEINE Code-Aenderungen, KEINE Tests.                        |
|    KEINE IST-Zustand-Analyse (das macht /_model).              |
+===============================================================+
```

---

## Verantwortlichkeit

Der **SPEZIFIKATEUR** Actor hat eine einzige Verantwortung:

**Ziel-Architektur und Anforderungen definieren (WIE ES SEIN SOLL)**

Was der Spezifikateur **TUT**:
- Kruemmel nach Architektur-Vorgaben durchsuchen
- Ziel-Klassen, Ziel-Interfaces, Ziel-Endpoints extrahieren
- Nicht-funktionale Anforderungen (NFR) sammeln
- Namenskonventionen und Patterns aus Vorgaben ableiten
- Akzeptanzkriterien in testbare Spezifikationen umwandeln
- Architektur-Diagramme (Mermaid) aus Kruemmeln erstellen
- Uncle Bob MCP befragen fuer Architektur-Guidance

Was der Spezifikateur **NICHT TUT**:
- IST-Zustand analysieren (das macht /_model)
- Code schreiben (das macht /_I_codeAtomic)
- Hypothesen aufstellen (das macht /_SC_hypothese)
- Model aktualisieren (das macht /_SC_modelMaintain)

---

## SPEC vs MODEL: Zwei Seiten einer Medaille

```
SPEC (/_spec)                      MODEL (/_model)
+---------------------------+      +---------------------------+
| WIE ES SEIN SOLL          |      | WIE ES IST               |
|                           |      |                           |
| - Ziel-Architektur        |      | - IST-Architektur         |
| - Erwartete Klassen       |      | - Vorhandene Klassen (W{n})|
| - Soll-Interfaces         |      | - Gefundene Interfaces    |
| - NFR (Performance, etc.) |      | - Gemessene Performance   |
| - Namenskonventionen      |      | - Beobachtete Patterns    |
| - Akzeptanzkriterien      |      | - Test-Ergebnisse         |
|                           |      |                           |
| Aendert sich SELTEN       |      | Aendert sich STAENDIG     |
| Quelle: Architekt/Crumbs  |      | Quelle: Codebase/Analyse  |
| Geschrieben: 1x am Anfang |      | Geschrieben: Jeder Zyklus |
+---------------------------+      +---------------------------+
         |                                    |
         +-----------> GAP-ANALYSE <----------+
                   (Was fehlt noch?)
```

**Kernprinzip:** SPEC ist das Leuchtfeuer. MODEL ist die Landkarte.
Die Distanz zwischen beiden ist die verbleibende Arbeit.

---

## Pipeline-Position

```
TASKDEFINITION --> **SPEC** --> MODEL --> Zyklus / Pipeline
                     |
                     v
               {NAME}_Spec.md
               (Ziel-Architektur)
```

**Prev:** /_taskDefinition (Task.md + Crumbs erstellt)
**Next:** /_model → dann /_gap (nutzt SPEC fuer Delta-Analyse)

**Wann ausfuehren:**
- NACH /_taskDefinition (Crumbs muessen existieren)
- VOR /_model (SPEC informiert die Model-Erstellung)
- OPTIONAL: Nur wenn Crumbs Architektur-Detail enthalten
- Wenn keine High-Detail-Crumbs vorhanden → direkt zu /_model

---

## Wann ist SPEC sinnvoll?

| Situation | SPEC noetig? |
|-----------|-------------|
| Crumbs enthalten Architektur-Diagramme | JA |
| Crumbs enthalten Klassen-/Interface-Vorgaben | JA |
| Crumbs enthalten NFR (Performance, Security) | JA |
| Architect hat muendliche Vorgaben gemacht | JA |
| Crumbs sind nur User Stories ohne Technik | NEIN → direkt /_model |
| Greenfield ohne Vorgaben | NEIN → direkt /_model |
| Bug-Fix ohne Architektur-Aenderung | NEIN → direkt /_model |

---

## Schritt 0: Manifest + Inputs lesen

**IMMER als Erstes:**

1. Lies `.claude/analysis/_manifest.md` falls vorhanden
   - Ermittle aktuellen {NAME}
   - Lies **SYSTEM-MODEL** und **SCHWIERIGKEIT** aus System-Konfiguration
   - Bestimme effektives Modell: `min(SYSTEM-MODEL, Command-Max=opus)`
   - Leite Modell-Zuordnung pro Welle ab
2. Lies `.claude/Task.md`
   - Akzeptanzkriterien → werden zu testbaren Spezifikationen
   - Scope-Grenzen → begrenzen die SPEC
3. Lies `.claude/crumbs/{NAME}_crumbs.md`
   - Suche nach Architektur-Vorgaben, Klassen-Definitionen, Interface-Beschreibungen
   - Identifiziere Mermaid-Diagramme mit Ziel-Architektur
   - Extrahiere NFR (Performance, Skalierbarkeit, Security)
4. Falls `.claude/models/{NAME}_Model.md` existiert:
   - Lies als KONTEXT (IST-Zustand)
   - Nutze fuer Gap-Bewusstsein (was existiert bereits?)
5. Pruefe pileOfMud auf ergaenzende Architektur-Dokumente

---

## Schritt 1: Uncle Bob MCP Queries (optional)

### Query 1: Architektur-Pattern

```python
mcp__cleancoder__query(
    "clean architecture for {DOMAIN_DESCRIPTION},
     interface design, dependency inversion,
     component responsibilities"
)
```

**Ergebnis:** Architektur-Empfehlungen fuer die Ziel-Architektur

### Query 2: Namenskonventionen (bei Unsicherheit)

```python
mcp__cleancoder__query(
    "naming conventions for {COMPONENT_TYPE},
     clean code naming, intention-revealing names"
)
```

---

## Schritt 2: Ziel-Architektur extrahieren

### 2.1 Kruemmel-Analyse

Pro Kruemmel-Sektion:
1. Enthaelt Architektur-Information? → Extrahieren
2. Enthaelt Klassen-/Interface-Vorgaben? → In SPEC-Format uebersetzen
3. Enthaelt NFR? → Strukturiert dokumentieren
4. Enthaelt Sequenz-/Datenfluss-Diagramme? → In Mermaid uebertragen

### 2.2 Kategorisierung

| Kategorie | Beschreibung | Beispiel |
|-----------|-------------|---------|
| **ARCH** | Architektur-Entscheidungen | "3-Layer mit DI" |
| **COMP** | Erwartete Komponenten/Klassen | "UserService, IUserRepository" |
| **IFACE** | Erwartete Interfaces | "IFileImporter mit ImportAsync()" |
| **ENDPT** | Erwartete API-Endpoints | "POST /api/users" |
| **NFR** | Nicht-funktionale Anforderungen | "Response < 200ms" |
| **CONV** | Namenskonventionen | "{Entity}Controller, I{Service}" |
| **DATA** | Datenmodell-Vorgaben | "User hat Email, Name, Role" |
| **SEC** | Security-Anforderungen | "JWT Auth, Role-Based Access" |

---

## Schwierigkeits-Parameter

| Schwierigkeit | Drafts (Welle 1) | Synthese (Welle 2) |
|---------------|-----------------|-------------------|
| **easy** | --- | 1 (DU, Hauptagent) |
| **normal** | 2-3 Subagenten | 1 (DU, Hauptagent) |
| **hard** | 3-5 Subagenten | 1 (DU, Hauptagent) |

**System-Model (aus Manifest):** Bestimmt welches Modell pro Welle laeuft.
- opus: Drafts=sonnet, Synthese=opus
- sonnet: Drafts=sonnet, Synthese=sonnet
- haiku: Drafts=haiku, Synthese=haiku

---

## Ablauf: Normal (Standard)

```
Welle 1:  +---+ +---+ +---+
DRAFTS    | D | | D | | D |  --LIEST--> CRUMBS + TASK + pileOfMud
          +-+-+ +-+-+ +-+-+  --SCHREIBT--> drafts/{NAME}-spec-D*.md
            +-----+-----+
                  |
             [/compact moeglich]
                  |
                  v
Welle 2:  +------------------+
SYNTHESE  |  DU, Hauptagent  |  --LIEST--> drafts/{NAME}-spec-D*.md
          |                  |  --SCHREIBT--> specs/{NAME}_Spec.md
          +------------------+
```

---

## Welle 1: Drafts (Architektur-Extraktion)

### Agent-Auftraege

```
Du bist Drafter D{NN} fuer die Spezifikations-Extraktion von "{NAME}".

INPUT - LIES ZUERST DIESE DATEIEN:
  1. .claude/crumbs/{NAME}_crumbs.md
  2. .claude/Task.md

AUFTRAG: {Fokus-Beschreibung}

SCHREIB-PFLICHT:
Du MUSST deine Findings in folgende Datei schreiben:
  .claude/analysis/drafts/{NAME}-spec-D{NN}-{fokus}.md

DATEI-FORMAT (Pflicht):
  ---
  name: {NAME}
  phase: spec
  wave: drafts
  tier: {SYSTEM-MODEL}
  model: {TATSAECHLICHES-MODELL}
  agent: D{NN}
  fokus: {fokus}
  date: {YYYY-MM-DD}
  reads: crumbs/{NAME}_crumbs.md, Task.md
  status: final
  ---

  # Spec-Extraktion D{NN}: {Fokus-Titel}

  ## Gelesene Inputs
  - CRUMBS: {Anzahl Sektionen}, {Architektur-Dichte}
  - TASK: {Akzeptanzkriterien Anzahl}

  ## Extrahierte Architektur-Vorgaben
  | # | Kategorie | Vorgabe | Quelle (Crumb-Sektion) |
  |---|-----------|---------|------------------------|

  ## Erwartete Komponenten
  | Komponente | Typ | Layer | Beschreibung |
  |-----------|-----|-------|-------------|

  ## Erwartete Interfaces
  | Interface | Methoden | Zweck |
  |-----------|----------|-------|

  ## NFR (Nicht-funktionale Anforderungen)
  | NFR | Metrik | Grenzwert | Quelle |
  |-----|--------|-----------|--------|

  ## Offene Fragen
  {Was ist in den Kruemmeln NICHT abgedeckt?}

  ## Zusammenfassung
  {5-10 Saetze}

WICHTIG:
- EXTRAHIERE aus Kruemmeln, ERFINDE NICHT
- Wenn Kruemmel vage sind: Als "UNKLAR" markieren, nicht raten
- Quelle IMMER angeben (welche Crumb-Sektion)
- KEINE IST-Zustand-Analyse (das macht /_model)
```

### Drafter-Fokus-Bereiche

| Agent | Fokus | Aufgabe |
|-------|-------|---------|
| D01 | architektur | Architektur-Patterns, Layer, Boundaries |
| D02 | komponenten | Klassen, Interfaces, Endpoints, Datenmodell |
| D03 | qualitaet | NFR, Security, Namenskonventionen, Constraints |
| D04-D05 | (bei hard) | Tiefere Analyse, Edge Cases, Abhaengigkeiten |

### Nach Welle 1: Manifest aktualisieren

**NACH dem Manifest-Update kann /compact ausgefuehrt werden.**

---

## Welle 2: Synthese (DU, Hauptagent)

### Voraussetzung

Lies ALLE Dateien in `.claude/analysis/drafts/{NAME}-spec-D*.md`

### Dein Auftrag

1. Lies alle Draft-Reports
2. Konsolidiere Architektur-Vorgaben (Deduplizierung)
3. Erstelle Ziel-Architektur-Diagramm (Mermaid)
4. Strukturiere in SPEC-Format (siehe Output-Format)
5. Markiere UNKLARE Vorgaben explizit
6. Schreibe `.claude/specs/{NAME}_Spec.md`

---

## Output-Format: {NAME}_Spec.md

**Pfad:** `.claude/specs/{NAME}_Spec.md`

```markdown
---
name: {NAME}
phase: spec
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
agent: Hauptagent
date: {YYYY-MM-DD}
reads: crumbs/{NAME}_crumbs.md, Task.md
status: final
version: 1.0
---

# Spezifikation: {NAME}

**Feature:** {Beschreibung aus Task.md}
**Datum:** {YYYY-MM-DD}
**Version:** 1.0

## 1. Ziel-Architektur

### Architektur-Typ
{Clean Architecture / Layered / Hexagonal / ...}

### Architektur-Diagramm

```mermaid
graph TD
    {Mermaid-Diagramm der Ziel-Architektur}
```

### Architektur-Entscheidungen

| # | Entscheidung | Begruendung | Quelle |
|---|-------------|-------------|--------|
| A1 | {Entscheidung} | {Warum} | {Crumb-Sektion} |

## 2. Erwartete Komponenten

### Backend

| # | Komponente | Typ | Layer | Beschreibung |
|---|-----------|-----|-------|-------------|
| C1 | {KlassenName} | Service/Controller/Repository | {Layer} | {Beschreibung} |

### Frontend

| # | Komponente | Typ | Beschreibung |
|---|-----------|-----|-------------|
| C{n} | {KomponentenName} | Component/Service/Model | {Beschreibung} |

### Datenbank

| # | Entity | Felder | Beschreibung |
|---|--------|--------|-------------|
| C{n} | {EntityName} | {Key Fields} | {Beschreibung} |

## 3. Erwartete Interfaces

| # | Interface | Methoden | Zweck | Layer-Boundary |
|---|-----------|----------|-------|---------------|
| I1 | I{ServiceName} | {Method1}, {Method2} | {Zweck} | {z.B. Service->Repository} |

## 4. Erwartete API-Endpoints

| # | Methode | Pfad | Request | Response | Beschreibung |
|---|---------|------|---------|----------|-------------|
| E1 | {GET/POST/...} | {/api/...} | {Body/Params} | {Response-Typ} | {Beschreibung} |

## 5. Nicht-funktionale Anforderungen (NFR)

| # | Kategorie | Anforderung | Metrik | Grenzwert |
|---|-----------|-------------|--------|-----------|
| N1 | Performance | {Beschreibung} | {z.B. Response Time} | {z.B. < 200ms} |
| N2 | Security | {Beschreibung} | {Metrik} | {Grenzwert} |

## 6. Namenskonventionen

| Typ | Konvention | Beispiel |
|-----|-----------|---------|
| Controller | {Entity}Controller | UserController |
| Service | {Entity}Service / I{Entity}Service | UserService / IUserService |
| Repository | {Entity}Repository / I{Entity}Repository | UserRepository |
| DTO | {Entity}Dto / {Entity}ResponseDto | UserDto |
| Component | {feature}-{type}.component.ts | user-detail.component.ts |

## 7. Datenfluss (Sequenz)

```mermaid
sequenceDiagram
    {Mermaid-Sequenzdiagramm des Haupt-Datenflusses}
```

## 8. Akzeptanzkriterien (Testbar)

| # | AK | Testbare Formulierung | Typ |
|---|----|--------------------|-----|
| AK1 | {aus Task.md} | Given {X} When {Y} Then {Z} | {Unit/Integration/E2E} |

## 9. Offene Fragen / Unklarheiten

| # | Frage | Kontext | Kritikalitaet |
|---|-------|---------|--------------|
| Q1 | {Was ist unklar?} | {Wo kam es her?} | HOCH/MITTEL/NIEDRIG |

## 10. Zusammenfassung

{3-5 Saetze: Was soll gebaut werden? Welche Architektur? Welche Kern-Interfaces?}

Naechster Schritt: /_model {NAME} → dann /_gap {NAME} (Delta: SPEC vs IST)
```

---

## Wer liest die SPEC?

| Command | Wie SPEC gelesen wird |
|---------|----------------------|
| **/_model** | Kontext: SOLL als Referenz beim IST-Aufbau |
| **/_gap** | **PRIMAER**: Delta-Analyse SPEC (SOLL) vs MODEL (IST) → Was fehlt? |
| **/_SC_observe** | Fokus-Orientierung: Welche SPEC-Komponenten beobachten? |
| **/_I_cleanCodeArchitect** | Slice-Dekomposition: SPEC als Architektur-Vorgabe |
| **/_I_codeAtomic** | **NICHT** (nur in Finish-Phase als Validierung) |
| **/_SC_qualityGate** | Feature-Abschluss: Alle SPEC-Komponenten implementiert? |

---

## SPEC-Pflege (selten)

SPEC aendert sich NUR bei:
1. Architekt aendert Vorgaben
2. Neue Anforderungen kommen hinzu
3. NFR werden angepasst

**Bei Aenderung:** Neue Version (`version: 1.1`), Aenderungs-Log im Dokument.
**SPEC wird NICHT bei jedem Zyklus aktualisiert** (im Gegensatz zu Model).

---

## Ablauf: Easy

```
             +------------------+
SYNTHESE     |  DU, Hauptagent  |  --LIEST--> CRUMBS + TASK + pileOfMud
             |                  |  --SCHREIBT--> specs/{NAME}_Spec.md
             +------------------+
```

Keine Drafts noetig. Direkte Extraktion und Strukturierung.

---

## Qualitaetskriterien

- Jede Vorgabe hat eine **Quelle** (Crumb-Sektion oder User-Input)
- UNKLARE Vorgaben sind als "UNKLAR" markiert (nicht geraten!)
- Mindestens 1 Architektur-Diagramm (Mermaid)
- Alle Akzeptanzkriterien aus Task.md in testbarer Form
- Namenskonventionen dokumentiert (falls in Kruemmeln vorhanden)
- SPEC enthaelt KEINE IST-Zustand-Analyse (das macht /_model)
- SPEC enthaelt KEINEN Code (das machen die I_ Phasen)

---

## Dateisystem-Erweiterung

```
.claude/
+-- Task.md                        <-- Aufgaben-Definition
+-- specs/                         <-- NEU: Spezifikationen
|   +-- {NAME}_Spec.md            <-- Ziel-Architektur (SOLL)
+-- models/                        <-- Persistente Models
|   +-- {NAME}_Model.md           <-- IST-Zustand
+-- crumbs/                        <-- Strukturierte Kruemmel
|   +-- {NAME}_crumbs.md
+-- analysis/
    +-- drafts/
    |   +-- {NAME}-spec-D*.md      <-- NEU: Spec-Drafts
    +-- ...
```

---

## Manifest-Update nach Abschluss

```markdown
**PHASE:** _spec abgeschlossen
**NAECHSTER SCHRITT:** /_model {NAME}

### Spec - {Datum}
- [x] .claude/specs/{NAME}_Spec.md (v{VERSION})
- [x] Architektur-Vorgaben: {N} extrahiert
- [x] Erwartete Komponenten: {N} (BE: {n}, FE: {n}, DB: {n})
- [x] Interfaces: {N}
- [x] Endpoints: {N}
- [x] NFR: {N}
- [x] Offene Fragen: {N}
```

---

## Kompakt-Sicherheit

Nach Command-Abschluss:
- State: {NAME}_Spec.md geschrieben
- Resume: /_model kann Spec.md lesen

---

## Obsidian-Tags

```yaml
tags:
  - type/spec
  - pipeline/pre-cycle
  - op/{FEATURE}
  - topic/Architecture
  - topic/Specification
pipeline-position: spec
prev: [[_taskDefinition]]
next: [[_model]]
```

---

## Siehe auch

- [[_taskDefinition]] - Vorheriger Schritt (Crumbs erstellen)
- [[_model]] - Naechster Schritt (IST-Zustand aufbauen)
- [[gap]] - Gap-Analyse: Delta SPEC (SOLL) vs MODEL (IST)
- [[I_cleanCodeArchitect]] - Nutzt GAP + SPEC fuer Slice-Dekomposition
- [[SC_observe]] - Nutzt GAP fuer gerichtete Observation

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_spec abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
