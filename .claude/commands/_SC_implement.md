---
type: building-block
depends_on:
  - _SC_hypothese
feeds_into:
  - _SC_ergebnis
related:
  - _I_codeAtomic
---

# /_SC_implement

Du fuehrst die geplanten Code-Aenderungen durch.

**Scope-Validierung (v2.0+):**
Genau 1 IC pro Durchgang. 3-stufige LOC-Schwellen:
  >100 LOC → Empfehlung: /_I_orchestrate erwaegen (kein Stop, kein Hard-Limit)
  >200 LOC → WARNUNG
  >200 LOC + Dateien>5 → ESKALATION: Moduswechsel zu /_I_orchestrate (Symbiose-Modus)
Verifikations-Anleitung mit 3-5 konkreten Test-Schritten PFLICHT.

**NEU (v2.2): Horizontale Suche (ALT-System Phase 2.2 Integration)**
VOR der Implementation wird eine Horizontale Suche durchgefuehrt:
Finde aehnliche Implementierungen INNERHALB der gleichen Schicht (Layer).
Dies liefert Code-Blueprints, reduziert Inkonsistenz und begrenzt den
Scope natuerlich durch Pattern-basierte Implementation.
3-Farb-System: GRAY (Copy-Paste) / ORANGE (Anpassen) / RED (Custom).

## Aufruf

```
/_SC_implement
```

Kein Schwierigkeits-Parameter. Implementation erfordert Fokus, nicht Breite.

---

## VERTRAG (Pflicht-I/O)

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_SC_implement                                                 ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  LIEST (Input) - PFLICHT:                                                ║
║    1. {VAULT}/_manifest.md                                      ║
║    2. .claude/analysis/synthese/{NAME}-HYPOTHESEN.md ◄── MUSS EXISTIEREN║
║       NEU: Enthaelt Verifikations-Kriterium (V1-V5, PASS/FAIL)         ║
║       NEU: Enthaelt Scope-Deklaration (IC, Dateien, LOC)                ║
║       NEU: Enthaelt Atomaritaets-Check (Soft-Limit-Status)              ║
║    3. .claude/models/{NAME}_Model.md      ◄── KONTEXT                   ║
║    4. .claude/patterns/_pattern-library.md ◄── NEU: Horizontale Suche   ║
║       (Graceful Degradation: Ohne Library = Codebase-Suche direkt)      ║
║    5. .claude/analysis/synthese/{NAME}-BOUNDARIES.md  ◄── OPTIONAL      ║
║       (Falls vorhanden: Datei-Mapping aus Vertikaler Suche nutzen)      ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    1. Code-Aenderungen (die im Plan beschriebenen)                       ║
║    2. .claude/analysis/synthese/{NAME}-HYPOTHESEN.md (aktualisiert)      ║
║       → Sektion "Horizontale Suche" hinzufuegen (NEU, v2.2)             ║
║       → Sektion "Durchgefuehrte Aenderungen" hinzufuegen                 ║
║       → Sektion "Verifikations-Anleitung" hinzufuegen (PFLICHT, HO-10)  ║
║       → Status auf "BEREIT ZUM TESTEN" setzen                            ║
║    3. {VAULT}/_manifest.md (aktualisieren)                      ║
║                                                                          ║
║  NEUE Qualitaetskriterien (Kap. 3.3):                                   ║
║    ┌─────────────────────┬──────┬──────┬──────────┬──────────────────┐   ║
║    │ Kriterium            │ Typ  │ Ovrd │ Grenze   │ Aktion           │   ║
║    ├─────────────────────┼──────┼──────┼──────────┼──────────────────┤   ║
║    │ ICs pro Durchgang   │VERSCH│ HO   │ Genau 1  │ STOP → _SC_hypothese│   ║
║    │ Dateien              │ OPT  │ SO   │ SL 5     │ WARNUNG          │   ║
║    │ LOC > 100            │ OPT  │ SO   │ SL 100   │ EMPFEHLUNG (kein Stop)  │
    ║    │ LOC > 200            │ OPT  │ SO   │ SL 200   │ WARNUNG          │   ║
║    │ LOC>200 + Dat.>5    │ PC2  │ SO   │ Gleichz. │ ESKALATION → /_I_orchestrate (Symbiose)│   ║
║    │ Verifikations-Anl.   │VERSCH│ HO   │ PFLICHT  │ 3-5 Test-Schritte│   ║
║    └─────────────────────┴──────┴──────┴──────────┴──────────────────┘   ║
║                                                                          ║
║  3-TUPEL POSITION:                                                       ║
║    [_SC_hypothese] ──▶ [_SC_implement] ──▶ [_SC_ergebnis]               ║
║    Liest Output von _SC_hypothese (Verif. + Scope + Plan),              ║
║    schreibt Code + Verifikations-Anleitung + aktualisiert HYPOTHESEN     ║
║                                                                          ║
║  MANIFEST-SCHREIB-MUSTER (ManifestSplit, ADR-3):                        ║
║    Pattern A: Reiner State-Write — kein Protokoll-Eintrag               ║
║    SCHREIBT STATE: MANIFEST_SPLIT_SC_IMPLEMENT, sc_status (Einzeiler)  ║
║    SCHREIBT NICHT: _manifest_protokoll.md                               ║
║    (Protokoll-Eintraege via _SC_orchestrate Phase 3.3.0 Rollover)       ║
║                                                                          ║
║  MCP INTEGRATION (OPTIONAL, Uncle Bob Clean Code):                       ║
║    - mcp__cleancoder__query() fuer TDD + Patterns + Refactoring         ║
║    - Query Topics:                                                       ║
║      * "TDD approach for {implementation concern}"                      ║
║      * "clean code pattern for {code structure}"                        ║
║      * "refactoring {specific code smell}"                              ║
║                                                                          ║
║  MCP-BREMSE:                                                             ║
║    ┌─────────────────────────────────────────────────────────┐           ║
║    │  MIDDLE-Modus → max 3 Queries, limit=3                 │           ║
║    │  Modi:  min=1Q/1R  middle=3Q/3R  max=5Q/5R            │           ║
║    └─────────────────────────────────────────────────────────┘           ║
║                                                                          ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## Schritt 0: Manifest + Plan lesen

**IMMER als Erstes:**

1. Lies `{VAULT}/_manifest.md`
   - Ermittle den aktuellen {NAME}
   - Pruefe ob Phase _SC_hypothese abgeschlossen ist
   - Lies **SYSTEM-MODEL** aus der System-Konfiguration
   - Bestimme effektives Modell: `min(SYSTEM-MODEL, Command-Max=sonnet)`
2. Lies `.claude/analysis/synthese/{NAME}-HYPOTHESEN.md`
   - Pruefe ob Status "BEREIT FUER IMPLEMENTATION" ist
   - Falls nicht → FEHLER: "Hypothese nicht bereit. Starte erst /_SC_hypothese"
   - **NEU (v2.0+):** Lies Verifikations-Kriterium (Typ V1-V5, PASS/FAIL-Definition)
   - **NEU (v2.0+):** Lies Scope-Deklaration (IC-Name, erwartete Dateien, erwartete LOC)
   - **NEU (v2.0+):** Lies Atomaritaets-Check (Soft-Limit-Status, Ausnahme-Deklaration)
3. Lies Model fuer System-Kontext:
   - **Bei Model-Split:** Lies Model-Topologie → FOKUS-Teilmodel (`{NAME}_{TC}_Model.md`)
   - **Ohne Split:** Lies `.claude/models/{NAME}_Model.md`
4. **NEU:** Lies `.claude/patterns/_pattern-library.md` (falls vorhanden)
   - Pattern-Katalog (Kap. 5) fuer Blueprint-Auswahl
   - Layer-Definitionen (Kap. 4) fuer Horizontale Suche
   - Reuse-Score-Berechnung (Kap. 3) + 3-Farb-System (Kap. 2)
   - Falls nicht vorhanden: Horizontale Suche direkt in Codebase (ohne Library-Vorfilter)
5. **NEU:** Lies `.claude/analysis/synthese/{NAME}-BOUNDARIES.md` (falls vorhanden)
   - Nutze Datei-Mapping (Sektion 6) aus Vertikaler Suche
   - Layer-Zuordnungen pro TP als Input fuer Horizontale Suche
   - Falls nicht vorhanden: Layer muss in Schritt 1.5 selbst bestimmt werden

---

## Schritt 1: Scope-Validierung (VOR Ausfuehrung)

**PFLICHT vor jeder Code-Aenderung.**

### 1a. IC-Check (VERSCH/HO, HO-09)

- Pruefe: Enthaelt "Geplante Aenderungen" genau 1 IC?
- Falls NEIN (>1 IC):
  → **STOP.** "Mehr als 1 IC erkannt. Zurueck zu /_SC_hypothese fuer Scope-Verkleinerung."
  → Debugging bei FAIL unmoeglich mit >1 IC (W22).
- **Override:** HARD-OVERRIDE (HO-09). Bei Override: Begruendung dokumentieren.

### 1b. Soft-Limit-Check (OPT/SO + PC2/SO)

- Lies erwartete Dateien und LOC aus Scope-Deklaration
- Pruefe:
  - Dateien > 5? → **WARNUNG** ausgeben (OPT/SO)
  - LOC > 100? → **EMPFEHLUNG**: /_I_orchestrate erwaegen (kein Stop, kein Hard-Limit)
  - LOC > 200? → **WARNUNG** ausgeben (OPT/SO)
  - **BEIDE** gleichzeitig ueberschritten? → **ESKALATION** (PC2/SO) # (Z5: RF-14)
    → HiL-Prompt (auch bei HiL=off, da Eskalation):
      "ESKALATION: LOC>{actual_LOC} UND Dateien>{actual_files} — zu gross fuer INLINE.
       Empfehlung: Auf SYMBIOSE-Modus wechseln (/_I_orchestrate core).
       [SYMBIOSE starten]  SC-Modus auf FULL wechseln, /_I_orchestrate {NAME} (scope_mode=core)
       [TROTZDEM INLINE]   Weiter mit _SC_implement (auf eigene Gefahr, LOC ueberschritten)
       [ABBRECHEN]         Implementation abbrechen, zurueck zu /_SC_hypothese"
    → Bei SYMBIOSE starten:
        Manifest: pipeline_mode = SC_SYMBIOSE_I_ACTIVE
        SC_PIPELINE_STATE.sc_mode = FULL
        EXIT: "Eskalation zu SYMBIOSE — Team Lead startet /_I_orchestrate {NAME}"
    → Bei TROTZDEM INLINE: WEITER (Manifest-Notiz: "INLINE-Override: LOC={actual_LOC}")
    → Bei ABBRECHEN: EXIT (kein Code geschrieben)
    → KEIN Zurueck zu /_SC_hypothese — der Scope ist zu gross fuer INLINE.
- **Override:** SOFT-OVERRIDE. Automatische Manifest-Notiz bei Override.

### 1c. Atomaritaets-Ausnahme (falls deklariert)

- Falls HYPOTHESEN.md eine Atomaritaets-Ausnahme deklariert hat:
  - Dokumentiere: "Atomaritaets-Ausnahme akzeptiert: {Begruendung aus HYPOTHESEN}"
  - **User-Signal:** "Durchgang ueberschreitet Soft-Limits. Fortfahren? (J/N)"
  - Bei NEIN → Zurueck zu /_SC_hypothese

---

## Kontext

```
    /_model ──▶ /_SC_observe ──▶ /_SC_modelMaintain ──▶ /_SC_qualityGate ──▶ /_SC_hypothese ──▶ [/_SC_implement] ──▶ /_SC_ergebnis
                                                    │
                                    ┌───────────────┼───────────────┐
                                    ▼               ▼               ▼
                              Scope-Valid.   Horiz. Suche    Implementation
                              (Schritt 1)   (Schritt 1.5)   (Schritt 2+)
                                    │               │               │
                                    │         Pattern-Matching       │
                                    │         Layer-Constraint       │
                                    │         3-Farb-System          │
                                    └───────────────┴───────────────┘

    INPUT:  {NAME}-HYPOTHESEN.md (Plan + Verifikation + Scope)
            {NAME}_Model.md (Kontext)
            _pattern-library.md (Patterns, Layer-Defs, Reuse-Scores)
            {NAME}-BOUNDARIES.md (optional: Datei-Mapping aus Vert. Suche)
    OUTPUT: Code-Aenderungen
            {NAME}-HYPOTHESEN.md (aktualisiert: Horiz.Suche + Aenderungen + Verif.)
```

---

## Agent-Einsatz

DU (Hauptagent) fuehrst die Implementation durch:

```
             ┌──────────────────┐
SCOPE-       │  DU, Hauptagent  │  ──LIEST──▶ HYPOTHESEN (Scope)
VALID.       │  IC + Limits     │  ──PRUEFT──▶ 1 IC, SL 5/100
             └────────┬─────────┘
                      │ OK
                      ▼
             ┌──────────────────┐
HORIZONTALE  │  DU, Hauptagent  │  ──NUTZT──▶ Glob + Grep + Read
SUCHE        │  Pattern-Match   │  ──LIEST──▶ Pattern-Library + BOUNDARIES
             │  (Schritt 1.5)   │  ──LIEFERT──▶ Blueprints + Farb-Klasse
             └────────┬─────────┘
                      │
                      ▼
             ┌──────────────────┐
IMPLEMENT    │  DU, Hauptagent  │  ──LIEST──▶ Blueprints + HYPOTHESEN + MODEL
             │  (Fokus)         │  ──SCHREIBT──▶ Code + HYPOTHESEN-Update
             └──────────────────┘
```

**Command-Max:** sonnet (effektiv = min(SYSTEM-MODEL, sonnet))
**Begruendung:** Implementation erfordert Fokus, nicht Breite. Der Plan ist bereits erstellt.

---

## Aufgabe

Der Hauptagent:
1. Liest `{NAME}-HYPOTHESEN.md` (aktuelles Experiment)
2. Liest `{NAME}_Model.md` (System-Kontext)
3. **Validiert Scope** (Schritt 1: IC-Check + Soft-Limits)
4. **NEU: Horizontale Suche** (Schritt 1.5: Pattern-Matching in gleicher Schicht)
5. Fuehrt die geplanten Aenderungen durch - NUR die geplanten, MIT Blueprint!
6. Dokumentiert die tatsaechlichen Aenderungen in HYPOTHESEN.md
7. **Erstellt Verifikations-Anleitung** (3-5 konkrete Test-Schritte, PFLICHT)

---

## Schritt 1.5: Horizontale Suche (Pattern-Matching)

**NACH Scope-Validierung, VOR Implementation.**

Die Horizontale Suche findet aehnliche Implementierungen INNERHALB der
gleichen Schicht. Dies dient als Blueprint fuer konsistente Implementation.

**Kern-Prinzip (ALT-System Phase 2.2):**
Suche NUR in der gleichen Schicht (Layer-Constraint).
Ein Frontend-Service wird als Blueprint fuer einen anderen Frontend-Service genommen,
NICHT fuer einen Backend-Controller.

### 1.5a: Layer bestimmen

Fuer JEDE Ziel-Datei aus "Geplante Aenderungen" (HYPOTHESEN.md):

1. **Falls BOUNDARIES.md vorhanden:** Nutze Layer aus Sektion 6 (Datei-Mapping)
2. **Falls Pattern-Library vorhanden:** Nutze Layer-Definitionen (Kap. 4)
3. **Fallback:** Bestimme Layer anhand der Datei-Endung / Pfad-Konvention:

| Datei-Muster | Layer-ID |
|-------------|----------|
| `*.component.ts` | FE-COMP |
| `*.service.ts` (in `src/app/`) | FE-SVC |
| `*Controller.cs` | BE-CTRL |
| `*Service.cs` (in Backend) | BE-SVC |
| `*Repository.cs` | BE-REPO |
| `*Dto.cs` | BE-DTO |

> **ARCH-Delta-11:** Suffix→Layer-Mapping ist DCSRE-Beispiel. Projekt-portables
> Mapping via `python3 .claude/scripts/load_layers.py --format=json`.

| `*.spec.ts` | TEST-UNIT |
| `docker-compose*.yml` | INF-DOCK |
| `*.md` in `commands/` | CMD-DOC |
| `*.md` in `patterns/` | PATTERN-DOC |
| `*.md` in `models/` | META-MODEL |
| `*.md` in `meta/` | META-IMPL |
| `*.md` in `merge-instructions/` | META-MERGE |

### 1.5b: Aehnliche Dateien im gleichen Layer finden (Glob)

Pro Ziel-Datei:

1. **Layer-spezifische Glob-Suche:**
   Nutze das Glob-Tool mit dem Layer-Basis-Pattern aus der Pattern-Library:
   ```
   Beispiel fuer FE-COMP: Glob("**/src/app/**/*.component.ts")
   Beispiel fuer BE-SVC:  Glob("**/Services/**/*Service.cs")
   ```

2. **Kandidaten-Filter:**
   - Entferne die Ziel-Datei selbst aus den Ergebnissen
   - Entferne offensichtlich irrelevante Dateien (z.B. `index.ts`, `module.ts`)
   - Sortiere nach Namens-Aehnlichkeit zum Ziel

3. **Top-3 Kandidaten auswaehlen:**
   - Waehle die 3 Dateien mit der hoechsten Namens-/Funktions-Aehnlichkeit
   - Priorisiere Dateien mit aehnlichem Funktions-Typ
     (z.B. fuer eine Detail-Komponente: andere Detail-Komponenten bevorzugen)

4. **0-Treffer-Fallback:**
   Wenn Glob-Suche 0 Treffer liefert:
   - Kein Kandidat im Layer gefunden
   - Farbe: RED, Score: 0.0, Blueprint: KEIN
   - Protokolliere als "Layer leer oder Pattern neu"
   - Fahre fort mit Schritt 1.5e (RED-Klassifikation direkt)
   - Ueberspringe 1.5c und 1.5d (keine Kandidaten zum Analysieren)

### 1.5c: Pattern-Extraktion aus Kandidaten (Read + Grep)

Fuer JEDEN der Top-3 Kandidaten:

1. **Datei lesen:**
   Nutze das Read-Tool, um den Quellcode des Kandidaten zu lesen.

2. **Strukturelle Analyse:**
   - Klassen-Struktur (Constructor, Properties, Methods)
   - Dependency-Injection-Pattern
   - Import-/Using-Statements
   - Naming-Conventions
   - Error-Handling-Pattern
   - Template-Struktur (bei Frontend-Komponenten)

3. **Gemeinsame Elemente extrahieren:**
   - Welche DI-Services werden typischerweise injected?
   - Welches Lifecycle-Pattern wird verwendet (OnInit, OnDestroy, etc.)?
   - Welche HTTP-Methoden/Patterns werden genutzt?
   - Wie wird Error-Handling geloest?
   - Wie sieht das Template-Muster aus?

### 1.5d: Reuse-Bewertung (0-1 Score)

Pro Kandidat:

```
Score startet bei 1.0

Reduktionen:
  -0.1  Kandidat hat mehr/weniger Parameter als Ziel
  -0.1  Kandidat hat anderen Return-Typ als Ziel
  -0.2  Kandidat hat signifikant mehr Dependencies
  -0.15 Kandidat hat keine Tests
  -0.2  Kandidat hat hohe zyklomatische Komplexitaet
  -0.3  Kandidat ist in einem anderen Layer (LAYER-CONSTRAINT-VERLETZUNG!)

Erhoehungen:
  +0.05 Kandidat hat inline-Dokumentation/Kommentare
  +0.1  Kandidat folgt Naming-Conventions des Projekts
  +0.15 Kandidat hat Tests die als Vorlage dienen koennen
  +0.2  Kandidat ist im GLEICHEN Layer (Basis-Erwartung)

Ergebnis: max(0, min(1, Score))
```

**MD-Dokument-Scoring (Pattern Library, Commands, Models):**

Fuer Kandidaten die MD-Dokumente sind (Layer CMD-DOC, PATTERN-DOC, META-MODEL,
META-IMPL, META-MERGE) gelten zusaetzliche Score-Modifikationen:

```
MD-Dokument-spezifische Anpassungen:
  +0.15 wenn Dokument eine VERTRAG/Input-Output Sektion hat
  +0.1  wenn Dokument eine Beispiel-Sektion hat
  -0.2  wenn Dokument nur Ueberschriften und keine Inhalte hat (Stub)

Diese Anpassungen werden ZUSAETZLICH zu den Code-Reduktionen/Erhoehungen
angewendet. Bei reinen MD-Dokumenten entfallen Code-spezifische Kriterien
(zyklomatische Komplexitaet, Dependencies, Parameter/Return-Typ).
```

### 1.5e: 3-Farb-Komplexitaets-Klassifikation

Basierend auf dem besten Reuse-Score:

| Score-Bereich | Farbe | Bedeutung | Empfehlung |
|---------------|-------|-----------|------------|
| > 0.8 | **GRAY** | Einfach, fast 1:1 kopierbar | Copy Blueprint, Namen ersetzen |
| 0.5-0.8 | **ORANGE** | Mittel, Anpassungen noetig | Blueprint als Basis, Logik erweitern |
| < 0.5 | **RED** | Komplex, Custom noetig | Blueprint nur als Inspiration, Custom Implementation |

**Heuristik fuer Klassifikation:**

```
Zaehle Komplexitaets-Punkte:

+3  wenn bester reuseScore < 0.5
+2  wenn >3 Methoden angepasst werden muessen
+1  wenn keine Test-Vorlage vorhanden
+2  wenn kein aehnlicher Kandidat gefunden wurde
+2  wenn Custom-Business-Logik noetig (nicht nur CRUD)

Summe <= 2:  GRAY   → Einfache Pattern-Anwendung
Summe 3-5:   ORANGE → Moderate Anpassung
Summe >= 6:  RED    → Signifikante Custom-Arbeit
```

### 1.5f-pre: Pattern-ID Lookup

Vor der Blueprint-Auswahl:

1. Pruefe ob der beste Kandidat einen Pattern-Library-Eintrag hat:
   - Grep in `.claude/patterns/_pl-index.md` nach dem Dateinamen oder Pattern-Namen
2. Wenn gefunden: Pattern-Library-Match = `{Pattern-ID}`
   - Fuege Pattern-ID in Blueprint-Dokumentation ein
3. Wenn nicht gefunden: Pattern-Library-Match = `Kein Match (Kandidat fuer /_PT_extract)`

### 1.5f: Blueprint auswaehlen und dokumentieren

1. **Besten Kandidaten als Blueprint auswaehlen:**
   - Hoechster Reuse-Score
   - Am besten wartbarer Code
   - Beste Test-Abdeckung

2. **Blueprint-Zusammenfassung erstellen:**
   Fuer die HYPOTHESEN.md-Aktualisierung:

```markdown
### Horizontale Suche (Pattern-Matching)

**Ziel-Datei:** {Pfad der zu implementierenden Datei}
**Layer:** {Layer-ID}
**Komplexitaet:** GRAY / ORANGE / RED

#### Aehnliche Implementierungen (gleicher Layer)

| # | Kandidat | Reuse-Score | Farbe | Beschreibung |
|---|----------|-------------|-------|-------------|
| 1 | {Pfad} | {0.xx} | {GRAY/ORANGE/RED} | {Kurzbeschreibung} |
| 2 | {Pfad} | {0.xx} | {GRAY/ORANGE/RED} | {Kurzbeschreibung} |
| 3 | {Pfad} | {0.xx} | {GRAY/ORANGE/RED} | {Kurzbeschreibung} |

#### Ausgewaehlter Blueprint

- **Datei:** {Pfad des besten Kandidaten}
- **Reuse-Score:** {Score}
- **Farbe:** {GRAY/ORANGE/RED}
- **Uebernehmbare Elemente:**
  - {Element 1: z.B. Constructor-Pattern mit DI}
  - {Element 2: z.B. Error-Handling-Pattern}
  - {Element 3: z.B. Template-Struktur}
- **Anzupassende Elemente:**
  - {Element 1: z.B. Entity-spezifische Properties}
  - {Element 2: z.B. Custom Validierung}
- **Pattern-Library-Match:** {Pattern-ID oder "Kein Match"}
```

### 1.5g: Pattern-Adoption-Entscheidung und Usage-Log

Basierend auf Farbe und Pattern-Library-Match:

**GRAY (Score > 0.8) + Pattern-Library-Match vorhanden:**
- Blueprint 1:1 uebernehmen
- pattern-usage.log APPEND: `{datum} | {pattern-id} | {feature} | -- | VERIFIED | sc-implement`
- WEITER zur Implementation (Schritt 2)

**ORANGE (Score 0.5-0.8) ODER GRAY ohne Library-Match:**
- Blueprint als Basis, eigene Logik ergaenzen
- pattern-usage.log APPEND: `{datum} | {kandidat-id} | {feature} | -- | DRAFT | sc-implement`
- WEITER zur Implementation (Schritt 2)

**RED (Score < 0.5) ODER 0-Treffer:**
- Custom-Implementation (Blueprint nur als Inspiration)
- PT-TRIGGER-CHECK:
  Existiert `.claude/commands/_PT_extract.md`?
  - JA: PT-Trigger: `/_PT_extract` ausfuehren NACH Implementation
    (Extrahiert das neue Pattern in DRAFT-Status)
    Notiere in HYPOTHESEN.md: `PT-Trigger: AKTIV, Command: /_PT_extract`
  - NEIN: PT-SKIP (Manifest-Vermerk: `PT_SKIP_W245_OFFEN`)
    Notiere in HYPOTHESEN.md: `PT-Trigger: SKIP (W245 offen)`
- pattern-usage.log APPEND: `{datum} | KEIN_PATTERN | {feature} | -- | KEIN_PATTERN | sc-implement`

**pattern-usage.log Format:**
- Datei: `.claude/wissen/pattern-usage.log`  # BL-065: removed — Vault-Sync via obsidianSync entfernt (archiviert)
- Eintrag: `{YYYY-MM-DD} | {pattern-id-oder-KEIN_PATTERN} | {feature-name} | {cluster} | {STATUS} | {quelle}`
- Erstelle Datei wenn nicht vorhanden.

**Graceful Degradation:**
Wenn `.claude/patterns/_pattern-library.md` nicht vorhanden:
- Alle Schritte 1.5a-1.5g ueberspringen
- Farbe: RED (Default, kein Blueprint)
- Notiere: `Horizontale Suche: SKIP (Pattern Library nicht vorhanden)`

---

## Implementations-Auftrag

```
Du bist der Implementations-Agent fuer "{NAME}".

INPUT - LIES ZUERST DIESE DATEIEN:
  1. .claude/analysis/synthese/{NAME}-HYPOTHESEN.md (Experiment-Plan)
  2. .claude/models/{NAME}_Model.md (System-Kontext)

SCOPE-VALIDIERUNG (VOR Code-Aenderungen):
  - IC-Check: Genau 1 IC? → Falls >1: STOP (HO-09)
  - Dateien-Check: <= 5? → Warnung wenn ueberschritten
  - LOC-Check: <= 200? → Warnung wenn ueberschritten
  - Beide > Limit? → ESKALATION: pipeline_mode=SC_SYMBIOSE_I_ACTIVE, /_I_orchestrate {NAME} (Symbiose core)
  - Atomaritaets-Ausnahme? → User-Signal falls deklariert

AUFTRAG:
1. Fuehre die Horizontale Suche durch (Schritt 1.5)
2. Fuehre die geplanten Aenderungen aus HYPOTHESEN.md Sektion "Geplante Aenderungen" durch
3. NUTZE den ausgewaehlten Blueprint als Vorlage (aus Horizontaler Suche)

REGELN:
- NUR die geplanten Aenderungen durchfuehren
- KEINE zusaetzlichen Aenderungen, Refactoring oder "Verbesserungen"
- Blueprint aus Horizontaler Suche als Konsistenz-Vorlage nutzen
- Naming-Conventions und Patterns des Blueprints folgen
- Jede Aenderung dokumentieren
- Verifikations-Anleitung erstellen (PFLICHT, HO-10)
- Scope-Einhaltung dokumentieren

SCHREIB-PFLICHT:
Nach Abschluss MUSST du {NAME}-HYPOTHESEN.md aktualisieren:

  ### Horizontale Suche (Pattern-Matching)

  (Ergebnisse aus Schritt 1.5 — siehe Template oben)

  ### Durchgefuehrte Aenderungen

  | # | Datei | Zeile | Aenderung | Status |
  |---|-------|-------|-----------|--------|
  | 1 | ... | ... | ... | DONE |

  ### Scope-Einhaltung

  | Feld | Geplant | Tatsaechlich | Status |
  |------|---------|--------------|--------|
  | IC | {aus Scope-Deklaration} | {tatsaechlich} | OK / ABWEICHUNG |
  | Dateien | {aus Scope-Deklaration} | {tatsaechlich} | OK / WARNUNG (>5) |
  | LOC netto | {aus Scope-Deklaration} | {tatsaechlich} | OK / WARNUNG (>200) |

  ### Verifikations-Anleitung (PFLICHT, HO-10)

  **Typ:** V{1-5} (aus HYPOTHESEN Verifikations-Kriterium)
  **PASS-Definition:** {aus HYPOTHESEN}
  **FAIL-Definition:** {aus HYPOTHESEN}

  **Konkrete Test-Schritte (3-5):**

  1. [ ] {Exakter Befehl oder Aktion}
  2. [ ] {Exakter Befehl oder Aktion}
  3. [ ] {Exakter Befehl oder Aktion}
  4. [ ] {Optional: weiterer Schritt}
  5. [ ] {Optional: weiterer Schritt}

  ### Status

  BEREIT ZUM TESTEN
```

---

## Nach Implementation: Manifest aktualisieren

```markdown
**PHASE:** _SC_implement abgeschlossen
**NAECHSTER SCHRITT:** User testet, dann /_SC_ergebnis

### Implementation - {Datum}
- [x] Scope-Validierung: IC={IC-Name}, Dateien={N}, LOC={M}
- [x] Horizontale Suche: {N} Kandidaten, Blueprint={Pfad}, Farbe={GRAY/ORANGE/RED}
- [x] Code-Aenderungen durchgefuehrt
- [x] Verifikations-Anleitung: V{x} ({Beschreibung}), {N} Test-Schritte
- [x] .claude/analysis/synthese/{NAME}-HYPOTHESEN.md aktualisiert (Status: BEREIT ZUM TESTEN)
- [ ] Atomaritaets-Ausnahme: {Ja, Begruendung / Nein}
```

---

## Qualitaetskriterien

- **IC-Check:** Genau 1 IC pro Durchgang (VERSCH/HO, HO-09)
- **Scope-Einhaltung:** Dateien/LOC Soft-Limits geprueft und dokumentiert
- **NEU: Horizontale Suche (Schritt 1.5)**
  - Layer-Zuordnung fuer jede Ziel-Datei
  - Mindestens 3 Kandidaten im gleichen Layer gesucht (Glob)
  - Reuse-Score pro Kandidat berechnet (0-1)
  - 3-Farb-Klassifikation (GRAY/ORANGE/RED) dokumentiert
  - Blueprint ausgewaehlt und in HYPOTHESEN.md dokumentiert
  - Blueprint als Konsistenz-Vorlage in Implementation genutzt
- Nur geplante Aenderungen durchfuehren (keine Extras!)
- Jede Aenderung dokumentieren mit Datei:Zeile
- **Verifikations-Anleitung:** 3-5 konkrete, ausfuehrbare Test-Schritte (VERSCH/HO, HO-10)
- Test-Schritte basieren auf Verifikations-Kriterium aus HYPOTHESEN (V1-V5)
- Rollback-Moeglichkeit bleibt erhalten
- HYPOTHESEN.md ist aktualisiert (Horiz. Suche + Aenderungen + Scope + Verifikation)
- Bei Atomaritaets-Ausnahme: Explizit dokumentiert + User-Signal

---

## Naechster Schritt

User testet, dann: `/_SC_ergebnis` ausfuehren

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_SC_implement abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

ARGUMENTS: $ARGUMENTS
