# Forschung Phase 1: Analyse

> **LEGACY (v2.2): Dieser Command wurde durch 3 SRP-Commands ersetzt:**
> - `/_SC_observe` — Findings sammeln (Sektion A)
> - `/_SC_modelMaintain` — Model pflegen, GC, Split (Sektion B)
> - `/_SC_qualityGate` — Quality Gates pruefen (BR, Kohaesion, BSD)
>
> **Dieser Command bleibt als Referenz erhalten, sollte aber NICHT mehr aufgerufen werden.**
> **Nutze stattdessen die 3 Einzel-Commands in der Kette: observe → modelMaintain → qualityGate**

Du fuehrst eine tiefgehende Analyse durch, interpretierst Ergebnisse und aktualisierst das Model.
Dies ist die HOCH-KOGNITIVE Phase: Beobachten, Verstehen, Model aktualisieren. KEINE Hypothesen!

**Sektions-Sequenzierung (v2.0+):**
Sektion A (Findings) VOLLSTAENDIG ABSCHLIESSEN bevor Sektion B (Model-Update) beginnt.
KEIN Hin-und-Her-Springen zwischen Beobachtung und Model-Aenderung.

## Aufruf

```
/_analyse [easy|normal|hard]
```

Default ohne Parameter: **normal**

---

## VERTRAG (Pflicht-I/O)

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_analyse                                                      ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║  LIEST (Input) - PFLICHT:                                                ║
║    1. .claude/analysis/_manifest.md                                      ║
║    2. .claude/models/{NAME}_Model.md  ◄── MUSS EXISTIEREN               ║
║    3. .claude/analysis/synthese/{NAME}-ERGEBNIS{CYCLE}.md                ║
║       ◄── Falls vorhanden (Folge-Zyklen)                                ║
║       NEU: Enthaelt SRS-Score, Widerlegungs-Marker, Stagnations-Check   ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║                                                                          ║
║    Welle 1 (Drafts, bei normal+hard):                                    ║
║      .claude/analysis/drafts/{NAME}-analyse{CYCLE}-D01-{f}.md           ║
║      .claude/analysis/drafts/{NAME}-analyse{CYCLE}-D02-{f}.md           ║
║      ... (pro Agent eine Datei)                                          ║
║                                                                          ║
║    Welle 2 (Synthese = DU, Hauptagent):                                  ║
║      .claude/analysis/synthese/{NAME}-ANALYSE{CYCLE}.md                  ║
║      → Sektion A: Analyse-Findings (WAS beobachtet?)                     ║
║      → Sektion B: Model-Update (WAS bedeutet das?)                       ║
║                                                                          ║
║    Model-Update (ab Zyklus 2):                                           ║
║      .claude/models/{NAME}_Model.md (aktualisiert)                       ║
║      → Neue W{n} / korrigierte W{n} / Version erhoehen                  ║
║      → GC: WIDERLEGT/ELIMINIERT markieren (aus ERGEBNIS-Marker)         ║
║      → Kap. 6a pflegen (Offene Bereiche, Aktive TCs)                    ║
║                                                                          ║
║    Model-Split (bei PFLICHT-Trigger aus Kohaesion-Check):               ║
║      .claude/models/{NAME}_Model-Topologie.md (erstellen/aktualisieren) ║
║      .claude/models/{NAME}_{TC}_Model.md (pro Teilmodel)                ║
║      → W{n} nach TC verteilen, FOKUS setzen, VM-1..VM-6 aktivieren     ║
║                                                                          ║
║    Manifest (IMMER):                                                     ║
║      .claude/analysis/_manifest.md (aktualisieren)                       ║
║                                                                          ║
║  NEUE Pflicht-Abschnitte im ANALYSE-Dokument (Sektion B):               ║
║    ┌─────────────────────┬──────┬──────┬─────────────────────────────┐   ║
║    │ Abschnitt            │ Typ  │ Ovrd │ Inhalt                     │   ║
║    ├─────────────────────┼──────┼──────┼─────────────────────────────┤   ║
║    │ BR-Bewertung        │ PC2  │ HO   │ SRS-Trend interpretieren,  │   ║
║    │                      │      │      │ Anti-Pattern-Check          │   ║
║    │ Kohaesion-Check     │ PC2  │ SO   │ W{n}/TC zaehlen,           │   ║
║    │                      │      │      │ Split-Trigger pruefen      │   ║
║    │ Model-Split Ausf.   │ PC2  │ SO   │ Bei PFLICHT-Trigger:       │   ║
║    │                      │      │      │ Split ausfuehren (Kap.2.2)│   ║
║    │ Blind-Spot-Trigger  │ OPT  │ SO   │ Muster T1-T5 pruefen,     │   ║
║    │                      │      │      │ BSD empfehlen              │   ║
║    │ Feature-Abschluss   │ PC2  │ SO   │ W{n}-Status zaehlen,      │   ║
║    │   Erkennung (v2.1)  │      │      │ ABGESCHLOSSEN erkennen,   │   ║
║    │                      │      │      │ Model-Finish vorschlagen  │   ║
║    └─────────────────────┴──────┴──────┴─────────────────────────────┘   ║
║                                                                          ║
║  SEKTIONS-SEQUENZIERUNG (HO-03):                                        ║
║    Sektion A (Findings) → VOLLSTAENDIG → Sektion B (Model-Update)       ║
║    KEIN Hin-und-Her-Springen!                                            ║
║                                                                          ║
║  COMPACT-SICHER:                                                         ║
║    Nach Welle 1 kann /compact ausgefuehrt werden.                        ║
║    Welle 2 liest aus drafts/{NAME}-analyse{CYCLE}-D*.md.                ║
║                                                                          ║
║  3-TUPEL POSITION:                                                       ║
║    [_ergebnis] ──▶ [_analyse] ──▶ [_hypothese]                          ║
║    Liest Output von _ergebnis (SRS + Rohdaten + Marker),                ║
║    schreibt Input fuer _hypothese (Findings + Model-Update)              ║
║                                                                          ║
║  MCP INTEGRATION (OPTIONAL, Uncle Bob Clean Code):                       ║
║    - mcp__cleancoder__query() fuer Code-Quality-Bewertung               ║
║    - Query Topics:                                                       ║
║      * "code quality assessment for {finding description}"              ║
║      * "architectural smell in {component interaction}"                 ║
║      * "refactoring strategy for {identified problem}"                  ║
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

## Schritt 0: Manifest + Model lesen + Zyklus-Nummer bestimmen

**IMMER als Erstes:**

1. Lies `.claude/analysis/_manifest.md`
   - Ermittle den aktuellen {NAME}
   - Pruefe ob Phase _model abgeschlossen ist
   - Lies **SYSTEM-MODEL** und **SCHWIERIGKEIT** aus der System-Konfiguration
   - Bestimme effektives Modell: `min(SYSTEM-MODEL, Command-Max=opus)`
   - Leite Modell-Zuordnung pro Welle ab (siehe Manifest → Modell-Zuordnung)
   - Lies **STAGNATION** Zaehler (falls vorhanden)
2. Lies `.claude/models/{NAME}_Model.md`
   - Falls nicht vorhanden → FEHLER: "Kein Model gefunden. Starte erst /_model {NAME} hard"
3. Falls Folge-Zyklus: Lies `.claude/analysis/synthese/{NAME}-ERGEBNIS*.md`
   - Strukturierte Rohdaten aus /_ergebnis als Basis fuer Interpretation
   - **NEU (v2.0+):** Lies SRS-Score (VORHER/NACHHER-Tabelle)
   - **NEU (v2.0+):** Lies Widerlegungs-Marker (DIREKT WIDERSPRUCHLICH / ZUR PRUEFUNG / KONSISTENT)
   - **NEU (v2.0+):** Lies Stagnations-Check (Fortschritts-Typ, Zaehler, Schwelle)
   - Falls nicht vorhanden: Erster Zyklus, /_ergebnis wurde uebersprungen
4. Identifiziere relevante Sektionen und offene Fragen aus dem Model
5. **Auto-Increment: Bestimme naechste Zyklus-Nummer {CYCLE}**
   - Scanne `.claude/analysis/synthese/{NAME}-ANALYSE*.md` auf Disk
   - Zaehle bestehende: ANALYSE=1, ANALYSE2=2, ANALYSE3=3, ...
   - `{CYCLE}` = hoechste gefundene Nummer + 1
   - Suffix-Konvention: `""` fuer 1, `"2"` fuer 2, `"3"` fuer 3, etc.
   - Gib aus: **"Dies wird Analyse {CYCLE} (Datei: {NAME}-ANALYSE{CYCLE}.md)"**

**Variablen fuer den Rest des Ablaufs:**
- `{CYCLE}` = Zyklus-Suffix (z.B. "", "2", "3", "4", "5", "6")
- Drafts-Pfad: `drafts/{NAME}-analyse{CYCLE}-D{NN}-{fokus}.md`
- Synthese-Pfad: `synthese/{NAME}-ANALYSE{CYCLE}.md`

---

## Kontext

```
    [/_ergebnis] ──▶ [/_analyse] ──▶ /_hypothese ──▶ /_implement ──▶ /_ergebnis
                        ▲                                                │
                        └────────────────────────────────────────────────┘

    INPUT:  {NAME}_Model.md (Single Source of Truth)
            {NAME}-ERGEBNIS{CYCLE}.md (SRS + Rohdaten + Marker, Folge-Zyklen)
    OUTPUT: {NAME}-ANALYSE{CYCLE}.md (Sek.A: Findings, Sek.B: Model-Update)
            {NAME}_Model.md (aktualisiert: W{n}, GC, Kap. 6a)
```

---

## Schwierigkeits-Parameter

| Schwierigkeit | Exploration (Welle 1) | Drafts (Welle 2) | Synthese (Welle 3) |
|---------------|----------------------|------------------|-------------------|
| **easy** | --- | --- | 1 (DU, Hauptagent) |
| **normal** | --- | 2-3 Subagenten | 1 (DU, Hauptagent) |
| **hard** | 5-10 Subagenten | 3-5 Subagenten | 1 (DU, Hauptagent) |

**System-Model (aus Manifest):** Bestimmt welches Modell pro Welle laeuft.
- opus: Exploration=haiku, Drafts=sonnet, Synthese=opus
- sonnet: Exploration=haiku, Drafts=sonnet, Synthese=sonnet
- haiku: Exploration=haiku, Drafts=haiku, Synthese=haiku

---

## Ablauf: Normal (Standard)

```
Welle 1:  ┌───┐ ┌───┐ ┌───┐
DRAFTS    │ D │ │ D │ │ D │  ──LIEST──▶ models/{NAME}_Model.md
          └─┬─┘ └─┬─┘ └─┬─┘  ──SCHREIBT──▶ drafts/{NAME}-analyse{CYCLE}-D*.md
            └─────┼─────┘
                  │
             [/compact moeglich]
             [Manifest: "Welle 1 done, Welle 2 pending"]
                  │
                  ▼
Welle 2:  ┌──────────────────┐
SYNTHESE  │  DU, Hauptagent  │  ──LIEST──▶ drafts/{NAME}-analyse{CYCLE}-D*.md
          │  Sek.A → Sek.B   │  ──SCHREIBT──▶ synthese/{NAME}-ANALYSE{CYCLE}.md
          └──────────────────┘  ──UPDATED──▶ models/{NAME}_Model.md
                  │
             [Manifest: "_analyse done, naechster: /_hypothese"]
```

---

## Welle 1: Drafts (Heavy Lifting)

### Voraussetzung

{NAME}_Model.md existiert und wurde gelesen.

### Agent-Auftraege

Starte Drafter-Agenten **parallel**. JEDER Agent erhaelt:

```
Du bist Drafter D{NN} fuer die Analyse von "{NAME}".

INPUT - LIES ZUERST DIESE DATEIEN:
  1. .claude/models/{NAME}_Model.md
  2. .claude/analysis/synthese/{NAME}-ERGEBNIS{CYCLE}.md (falls vorhanden)

AUFTRAG: {Fokus-Beschreibung}

SCHREIB-PFLICHT:
Du MUSST deine Findings in folgende Datei schreiben:
  .claude/analysis/drafts/{NAME}-analyse{CYCLE}-D{NN}-{fokus}.md

DATEI-FORMAT (Pflicht):
  ---
  name: {NAME}
  phase: analyse{CYCLE}
  wave: drafts
  tier: {SYSTEM-MODEL}
  model: {TATSAECHLICHES-MODELL}
  agent: D{NN}
  fokus: {fokus}
  date: {YYYY-MM-DD}
  reads: models/{NAME}_Model.md
  status: final
  ---

  # Analyse D{NN}: {Fokus-Titel}

  ## Model-Kontext
  {Relevante Sektionen aus {NAME}_Model.md}

  ## Findings

  ### F1: {Finding-Titel}
  - **Datei:** {Pfad}:{Zeile}
  - **Model-Bezug:** W{n} oder "Neu"
  - **Beschreibung:** ...

  ## Zusammenfassung
  {5-10 Saetze}

WICHTIG:
- IMMER Model als Kontext nutzen
- Falls ERGEBNIS-Dateien vorhanden: SRS-Score + Marker als Kontext nutzen
- Findings mit Datei:Zeile belegen
- Model-Bezug angeben: bestaetigt W{n}, widerspricht W{n}, oder NEU
- KEINE Hypothesen-Kandidaten! Nur beobachten und dokumentieren
- Die Datei MUSS geschrieben werden, NICHT nur als Text zurueckgeben
```

### Drafter-Fokus-Bereiche

| Agent | Fokus | Aufgabe |
|-------|-------|---------|
| D01 | code-analyse | Relevante Code-Pfade, Methoden-Aufrufe, Abhaengigkeiten |
| D02 | infrastruktur | Config-Dateien, Environment, Container, Netzwerk |
| D03 | patterns | Cross-Cutting Concerns, Architektur-Patterns, Anomalien |
| D04-D05 | (bei hard) | Externe Abhaengigkeiten, Gegen-Hypothesen |

### Nach Welle 1: Manifest aktualisieren

```markdown
**PHASE:** _analyse{CYCLE}
**WELLE:** 1 abgeschlossen, 2 ausstehend
**NAECHSTER SCHRITT:** Welle 2 (Synthese) starten - liest drafts/{NAME}-analyse{CYCLE}-D*.md

### Drafts (_analyse{CYCLE} - Welle 1)
- [x] .claude/analysis/drafts/{NAME}-analyse{CYCLE}-D01-code-analyse.md
- [x] .claude/analysis/drafts/{NAME}-analyse{CYCLE}-D02-infrastruktur.md
- [x] .claude/analysis/drafts/{NAME}-analyse{CYCLE}-D03-patterns.md
```

**NACH dem Manifest-Update kann /compact ausgefuehrt werden.**

---

## Welle 2: Synthese (DU, Hauptagent - Sektions-Sequenzierung)

### Voraussetzung

Lies ALLE Dateien in `.claude/analysis/drafts/{NAME}-analyse{CYCLE}-D*.md`

Falls nicht vorhanden → FEHLER: "Welle 1 nicht abgeschlossen."

### Dein Auftrag

**SEKTIONS-SEQUENZIERUNG (HO-03): A ERST ABSCHLIESSEN, DANN B.**

#### SEKTION A: Analyse-Findings

1. Lies alle Draft-Reports aus `.claude/analysis/drafts/{NAME}-analyse{CYCLE}-D*.md`
2. **Pruefe ob die Findings stimmen** - schlag im Code nach wenn noetig
3. Verwirf was nicht belegt werden kann
4. Identifiziere Widersprueche zwischen Drafts
5. Synthetisiere die finale Analyse
6. Markiere was NEU ist gegenueber dem Model-Stand
7. Dokumentiere offene Fragen

**→ SEKTION A VOLLSTAENDIG ABSCHLIESSEN bevor du weitergehst.**

#### SEKTION B: Model-Update-Vorschlag

8. **Battle-Royale-Bewertung (PC2/HO):**
   - Lies SRS-Score aus ERGEBNIS (VORHER/NACHHER/Delta)
   - INTERPRETIERE den Trend: GESCHRUMPFT / STAGNIERT / GEWACHSEN
   - Anti-Pattern-Check: R-AP1..R-AP5 pruefen
   - Status: GESUND / WARNUNG / ESKALATION
   - Bei ESKALATION (R-AP3/R-AP4): Pflicht-Massnahme bestimmen
     (BSD durchfuehren ODER Model-Split ODER Fokus-Wechsel)
   - Eliminierte Bereiche im Model markieren
   - **Override:** HO-02. Bei Override: Begruendung dokumentieren.

9. **Kohaesion-Check (PC2/SO):**
   - Zaehle W{n} pro Technologie-Concern (TC)
   - Pruefe Model-Split-Trigger:
     - T-MS1: >15 W{n}/TC ODER >30 gesamt → EMPFEHLUNG (Pflicht bei >5 TC)
     - T-MS2: >3 verschiedene TCs → EMPFEHLUNG (Pflicht bei >5)
     - T-MS3: R-AP4 ausgeloest → PFLICHT
     - T-MS4: >3 unabhaengige Teilprobleme → EMPFEHLUNG
   - Falls Trigger: Model-Split empfehlen
   - **Override:** SO. Automatische Manifest-Notiz bei Override.

9a. **Model-Split Ausfuehrung (PC2/SO, falls Kohaesion-Check PFLICHT):**

    **Wann:**
    - PFLICHT-Trigger (T-MS1 bei >5 TC, T-MS2 bei >5, T-MS3): SOFORT ausfuehren
    - EMPFEHLUNG: Im Manifest dokumentieren, User entscheidet
    - Bereits gesplittet: NUR Model-Topologie aktualisieren (→ Schritt 12)

    **Ausfuehrungs-Schritte:**

    a) **TC-Identifikation:**
       - Gruppiere alle AKTIVEN W{n} nach Technologie-Concern (TC)
       - Jede W{n} → genau 1 TC (bei Unklarheit: PRIMAERER TC)
       - Cross-Cutting W{n} (>1 TC): Als Abhaengigkeit im Index dokumentieren

    b) **Model-Topologie erstellen:** `models/{NAME}_Model-Topologie.md`

       Folge dem **Topologie-Pattern** aus `.claude/reference/Topologie-OmniCommand.md`
       und dem Template in `/_model` (Abschnitt "Model-Topologie Dokument-Template").

       **Pflicht-Inhalte (mindestens 4 verschiedene Mermaid-Diagramm-Typen):**

       ```markdown
       # Model-Topologie: {NAME}

       **Version:** 1.0
       **Erstellt:** {DATUM}, ANALYSE{CYCLE}
       **Referenz-Muster:** .claude/reference/Topologie-OmniCommand.md
       **Fokus:** {TC mit hoechstem SRS-Anteil}

       ## 1. Gesamtdiagramm
       {Mermaid flowchart LR: Alle Teilmodelle + Cross-Cutting Abhaengigkeiten}

       ## 2. Vertrags-Matrix
       | # | Von | Nach | Shared W{n} | Typ |
       |---|-----|------|-------------|-----|

       ## 3. Kohaesion/Kopplung-Metriken
       {Mermaid mindmap: W-Anzahl, Kohaesion, Externe Deps pro TC}

       ## 4. Fokus-Transition
       {Mermaid stateDiagram-v2: Wechsel-Logik zwischen Teilmodellen}

       ## 5. SRS pro Teilmodel
       | # | Teilmodel | D1 | D2 | D3 | D4 | SRS | Fokus |
       |---|-----------|----|----|----|----|-----|-------|

       ## 6. Teilmodel-Index
       | # | Teilmodel | Status | Fokus | W{n} | Pfad | Deps |
       |---|-----------|--------|-------|------|------|------|
       | 1 | {TC-Name} | AKTIV | **JA** | {N} | models/{NAME}_{TC}_Model.md | {Liste} |
       | 2 | {TC-Name} | AKTIV | --- | {N} | models/{NAME}_{TC}_Model.md | {Liste} |

       ## 7. Evolution (Split-Historie)
       | Version | Datum | Aktion | Details |
       |---------|-------|--------|---------|

       ## 8. VM-Regeln (Referenz)
       | Regel | Beschreibung |
       |-------|-------------|
       | VM-1..VM-6 | (aus /_model) |
       ```

       **QUALITAETS-GATE:** Mindestens 3 Mermaid-Typen, SRS berechenbar,
       Cross-Cutting explizit, Referenz auf Topologie-OmniCommand.md.

    c) **Teilmodelle erstellen:** Pro TC eine Datei `models/{NAME}_{TC}_Model.md`
       - Kopiere zugehoerige W{n} (globale Nummerierung beibehalten, VM-5)
       - Uebernimm relevante Sektionen aus dem Monolith-Model
       - Fuege Kap. 6a hinzu (Offene Bereiche + Aktive TCs fuer diesen TC)

    d) **FOKUS setzen (VM-1):** TC mit hoechstem SRS-Beitrag wird FOKUS
       - SRS pro Teilmodel: D1_teil * 3 + W{n}_teil * 1 + Dateien_teil * 0.5 + 1 * 5
       - D4_teil = immer 1 (jedes Teilmodel hat genau 1 TC)

    e) **Monolith archivieren:** Header in `{NAME}_Model.md` setzen:
       "GESPLITTET ab v{X.Y} → siehe `{NAME}_Model-Topologie.md`"

    **VM-Regeln (ab sofort gueltig):**

    | Regel | Beschreibung |
    |-------|-------------|
    | VM-1 | Nur 1 Teilmodel darf FOKUS sein |
    | VM-2 | _hypothese bezieht sich NUR auf FOKUS-Teilmodel |
    | VM-3 | _implement aendert NUR Dateien des FOKUS-TC |
    | VM-4 | Cross-TC-Abhaengigkeiten im Index dokumentieren |
    | VM-5 | Globale W{n}-Nummerierung bleibt erhalten |
    | VM-6 | Max 6 Teilmodelle; bei >6 zusammenlegen |

    **Cross-Cutting-Schutz:** Ab dem naechsten Zyklus liest mindestens 1 Drafter
    ALLE Teilmodelle (Cross-Cutting-Drafter, adressiert GH-4).

    **SRS nach Split:** SRS_gesamt = Summe(SRS_aktive_teilmodelle).
    Elimination eines Teilmodels senkt SRS sofort signifikant.

9b. **Triggering-Heuristik-Check (OPT/SO, W29):**

    **Zweck:** Automatische Erkennung, wann `/_architecturalBoundaries` noetig ist.

    **Methodik:**
    1. Pruefe ob ERGEBNIS vorhanden (Cycle 2+) ODER nicht vorhanden (Cycle 1)
    2. Falls Cycle 2+: Lese ERGEBNIS → Zaehle betroffene Dateien, Schichten (W38: 4-fold), TCs
    3. Falls Cycle 1: Lese Model → Zaehle L{n}, TCs, W{n}
    4. Pruefe PFLICHT-Trigger (>5 Dateien OR >3 Schichten OR >5 L{n} OR >4 TCs)
    5. Falls Trigger: Schreibe Empfehlung in ANALYSE + Update Manifest

    **Trigger-Heuristik (aus W29):**
    - **PFLICHT (Auto-Trigger):**
      - Cycle 2+: betroffene_Dateien > 5 OR betroffene_Schichten > 3 (aus W38: 4-fold Layers)
      - Cycle 1: offene_Luecken > 5 OR aktive_TCs > 4
    - **OPTIONAL (User-gesteuert):** Architektonisch komplex, neue Feature-Domaene
    - **SKIP:** Single-File-Fix, Bug-Fix ohne Architektur-Aenderung

    **Prozess:**

    a) **Cycle-Detection:**
       - ergebnis_vorhanden = file_exists(".claude/analysis/synthese/{NAME}-ERGEBNIS.md")

    b) **Cycle 2+ Pfad (falls ergebnis_vorhanden):**
       - Lese ERGEBNIS.md
       - Zaehle betroffene_Dateien (aus SEKTION "Durchgefuehrte Aenderungen")
       - Zaehle betroffene_Schichten (aus W38: Task/BOUNDARIES/Pattern/Implementation)
       - Zaehle aktive_TCs (aus ERGEBNIS SEKTION "Battle-Royale" D4)

       **PFLICHT-Trigger:**
       - IF (betroffene_Dateien > 5 OR betroffene_Schichten > 3):
         - trigger = TRUE
         - grund = "Cycle hat {N} Dateien in {M} Schichten betroffen"

    c) **Cycle 1 Pfad (falls NICHT ergebnis_vorhanden):**
       - Lese Model → Zaehle L{n}, TCs, W{n} (aus Kap. 6a)
       - **Graceful Degradation (W17):** Falls w_count < 20: skip Trigger (Model zu jung)
       - ELSE:
         - **PFLICHT-Trigger:**
         - IF (offene_Luecken > 5 OR aktive_TCs > 4):
           - trigger = TRUE
           - grund = "Model hat {N} offene Luecken und {M} TCs"

    d) **Output generieren:**
       - **Falls trigger = TRUE:**
         - Schreibe in ANALYSE.md (neue SEKTION C.1 nach SEKTION B):
           ```markdown
           ### SEKTION C.1: Triggering-Empfehlung

           **EMPFEHLUNG**: Nutzen Sie `/_architecturalBoundaries` vor `/_hypothese`.

           **Grund**: {grund}

           **Begruendung**: Task betrifft {Details} → BOUNDARIES hilft bei:
           - Teilproblem-Dekomposition (W2: Abstrakt-vor-Konkret)
           - Layer-Mapping (W38: 4-fold Layers)
           - Vertrags-Definitionen zwischen Schichten
           - Horizontale Suche (W6: Pattern-Library-Match)
           ```
         - Update Manifest "Next-Step: /_architecturalBoundaries (Grund: {grund})"

       - **Falls trigger = FALSE:**
         - Schreibe in ANALYSE.md:
           ```markdown
           ### SEKTION C.1: Triggering-Info

           **INFO**: `/_architecturalBoundaries` optional (Task ist einfach genug fuer direkten `/_hypothese`).

           **Metriken**: {Details der Metriken}

           **Empfehlung**: Fahren Sie direkt mit `/_hypothese` fort.
           ```
         - Manifest bleibt bei Standard Next-Step (`/_hypothese`)

    **Override:** SO. Automatische Manifest-Notiz bei Override.

    **Output-Beispiel (bei Trigger):**
    ```markdown
    **EMPFEHLUNG**: Nutzen Sie `/_architecturalBoundaries` vor `/_hypothese`.

    **Grund**: Cycle hat 12 Dateien in 4 Schichten betroffen (Task/BOUNDARIES/Pattern/Implementation gemaess W38).

    **Begruendung**: Task betrifft > 5 Dateien UND > 3 Schichten → BOUNDARIES hilft bei:
    - Teilproblem-Dekomposition (W2: Abstrakt-vor-Konkret)
    - Layer-Mapping (W38: 4-fold Layers)
    - Vertrags-Definitionen zwischen Schichten
    - Horizontale Suche (W6: Pattern-Library-Match)
    ```

    **Output-Beispiel (kein Trigger):**
    ```markdown
    **INFO**: `/_architecturalBoundaries` optional (Task ist einfach genug fuer direkten `/_hypothese`).

    **Metriken**: Cycle hat 3 Dateien in 2 Schichten betroffen → unterhalb PFLICHT-Trigger (>5 Dateien OR >3 Schichten).

    **Empfehlung**: Fahren Sie direkt mit `/_hypothese` fort.
    ```

10. **Blind-Spot-Trigger (OPT/SO):**
    - Pruefe Muster T1-T5:
      - T1: Gleiche Hypothesen-Richtung 2+ mal widerlegt
      - T2: Stagnation 3+ Loops ohne neue W{n} oder Widerlegung
      - T3: Phantom-Erfolg (teilweise PASS aber Gesamtproblem ungeloest)
      - T4: Fokus-Drift (Fokus weicht von Boundaries ab)
      - T5: Model-Explosion (R-AP4)
    - Falls Muster erkannt: /_blindspotDetection empfehlen
    - **Override:** SO. Kann uebersprungen werden.

11. **Stagnations-Bewertung:**
    - Lies Stagnations-Zaehler aus ERGEBNIS / Manifest
    - Bei >= 3.0: WARNUNG an User ausgeben
    - Bei >= 5.0: PFLICHT-Entscheidung erzwingen (P1-Vorrang, IR-1)
    - Bei >= 7.0: ABORT empfehlen
    - Dokumentiere Massnahme/Entscheidung

11a. **Feature-Abschluss-Erkennung (NEU v2.1, PC2/SO):**

    **Zweck:** Automatische Erkennung, wann ein Feature als abgeschlossen gilt
    und Model-Finish/Split vorgeschlagen werden soll.

    **Pruefung:**
    1. Zaehle aktive W{n} im Model (Status=AKTIV)
    2. Zaehle davon BESTAETIGT (durch mindestens 1 Experiment)
    3. Zaehle davon WIDERLEGT (durch Experiment widerlegt)
    4. Zaehle OFFEN (noch nie getestet)

    **Trigger:**
    ```
    FEATURE_ABGESCHLOSSEN wenn:
      - OFFEN = 0 (alle W{n} wurden getestet)
      - UND (BESTAETIGT + WIDERLEGT) / AKTIV >= 0.9 (90%+ abgedeckt)
      - UND kein PFLICHT-Trigger aus Kohaesion-Check aktiv

    FEATURE_FAST_FERTIG wenn:
      - OFFEN <= 2 (fast alle getestet)
      - UND (BESTAETIGT + WIDERLEGT) / AKTIV >= 0.75 (75%+ abgedeckt)

    FEATURE_OFFEN sonst
    ```

    **Output bei FEATURE_ABGESCHLOSSEN:**
    ```markdown
    ### Feature-Abschluss-Erkennung (v2.1)

    **STATUS: FEATURE ABGESCHLOSSEN**

    Alle Wahrheiten wurden getestet:
    - BESTAETIGT: {N} W{n}
    - WIDERLEGT: {N} W{n}
    - OFFEN: 0

    **EMPFEHLUNG:** Fuehren Sie `/_model {NAME} finish` aus.
    Dies konsolidiert das Model, verfeinert Formulierungen und
    prueft ob ein Model-Split sinnvoll ist.

    Alternativ: Neuen Task im bestehenden Feature hinzufuegen
    via `/_taskDefinition {NAME}` (Task-Kontinuitaet).
    ```

    **Output bei FEATURE_FAST_FERTIG:**
    ```markdown
    ### Feature-Abschluss-Erkennung (v2.1)

    **STATUS: FAST FERTIG**

    {N} von {M} Wahrheiten getestet. Noch {K} offene W{n}:
    - W{x}: {Beschreibung}
    - W{y}: {Beschreibung}

    **EMPFEHLUNG:** Noch {K} Zyklen fuer die offenen W{n},
    dann `/_model {NAME} finish`.
    ```

    **Override:** SO. Kann uebersprungen werden.

12. **Model-Update durchfuehren:**
    - Neue W{n} hinzufuegen mit Finding-Referenz
    - Korrigierte W{n} aktualisieren
    - GC: WIDERLEGT/ELIMINIERT markieren (aus ERGEBNIS Widerlegungs-Marker)
    - GC: Markierte W{n} in Sektion "Widerlegte/Eliminierte Annahmen" verschieben
    - Kap. 6a aktualisieren: "Offene Hypothesen-Bereiche" + "Aktive TCs"
    - Model-Topologie aktualisieren (falls Model-Split aktiv, IR-8)
    - Version erhoehen

### Analyse-Dokument Struktur

**Pfad**: `.claude/analysis/synthese/{NAME}-ANALYSE{CYCLE}.md`

```markdown
---
name: {NAME}
phase: analyse{CYCLE}
wave: synthese
tier: {SYSTEM-MODEL}
model: {TATSAECHLICHES-MODELL}
agent: Hauptagent
date: {YYYY-MM-DD}
reads: drafts/{NAME}-analyse{CYCLE}-D*.md, synthese/{NAME}-ERGEBNIS{CYCLE}.md
status: final
---

# Analyse: {NAME}

**Datum:** YYYY-MM-DD
**Iteration:** N
**Model-Basis:** {NAME}_Model.md v{X.Y}
**Schwierigkeit:** easy|normal|hard
**System-Model:** {SYSTEM-MODEL}

## Executive Summary
{3-5 Saetze}

============================================================
SEKTION A: ANALYSE-FINDINGS
============================================================

## Model-Kontext
{Relevante Sektionen aus MODEL, offene Fragen die adressiert werden}

## Findings

### Finding 1: {Titel}
- **Quelle**: Drafter D{NN} F{M}, verifiziert gegen {Datei}:{Zeile}
- **Model-Bezug**: W{n} bestaetigt / widerspricht / NEU
- **Beschreibung**: ...

## Neue Erkenntnisse vs. Model

| Erkenntnis | Im Model? | Status |
|------------|-----------|--------|
| ... | Neu | Muss untersucht werden |
| ... | Bestaetigt | W{n} gilt weiterhin |
| ... | Widerspruch! | Model muss geprueft werden |

## Offene Fragen
{Was ist noch ungeklaert?}

============================================================
SEKTION A ABGESCHLOSSEN
============================================================

============================================================
SEKTION B: MODEL-UPDATE
============================================================

## Battle-Royale-Bewertung (PC2/HO)

| Metrik | Wert |
|--------|------|
| SRS VORHER | {aus ERGEBNIS} |
| SRS NACHHER | {aus ERGEBNIS} |
| Delta | {+/- %} |
| Trend | GESCHRUMPFT / STAGNIERT / GEWACHSEN |
| Anti-Pattern-Status | GESUND / WARNUNG({R-APx}) / ESKALATION({R-APx}) |

Eliminierte Bereiche: {Liste}
Verbliebene Bereiche: {Liste}
Empfehlung: {Keine / BSD / Model-Split / Fokus-Wechsel}

## Kohaesion-Check (PC2/SO)

| TC | W{n}-Anzahl | Status |
|----|-------------|--------|
| {TC-Name} | {Zahl} | AKTIV / ELIMINIERT |

Trigger: {Keiner / T-MS1 / T-MS2 / T-MS3 / T-MS4}
Empfehlung: {Kein Split noetig / Split empfohlen / Split PFLICHT}

## Model-Split Ausfuehrung (falls PFLICHT)

Status: {Nicht noetig / Empfohlen (User entscheidet) / AUSGEFUEHRT}

Falls AUSGEFUEHRT:
- Model-Topologie: models/{NAME}_Model-Topologie.md
- Teilmodelle: {Anzahl} erstellt
- FOKUS: {TC-Name} (hoechster SRS-Anteil)
- Cross-Cutting W{n}: {Liste oder "keine"}
- VM-Regeln VM-1..VM-6 ab sofort aktiv

| # | Teilmodel | W{n} | SRS-Anteil | Fokus |
|---|-----------|------|------------|-------|
| 1 | {TC} | {N} | {Zahl} | JA/--- |
| 2 | {TC} | {N} | {Zahl} | --- |

## Blind-Spot-Trigger (OPT/SO)

Muster geprueft: T1[ ] T2[ ] T3[ ] T4[ ] T5[ ]
Erkannt: {Keines / T{x}: Beschreibung}
Empfehlung: {Kein BSD noetig / BSD empfohlen}

## Stagnations-Bewertung

| Feld | Wert |
|------|------|
| Zaehler (aus ERGEBNIS/Manifest) | {N} |
| Schwelle | NORMAL / WARNUNG / PFLICHT / ABORT |
| Massnahme | {Keine / Scope-Wechsel / User konsultieren / ABORT} |

## Feature-Abschluss-Erkennung (v2.1)

| Feld | Wert |
|------|------|
| Aktive W{n} gesamt | {N} |
| BESTAETIGT | {N} ({%}) |
| WIDERLEGT | {N} ({%}) |
| OFFEN | {N} ({%}) |
| Status | FEATURE_ABGESCHLOSSEN / FEATURE_FAST_FERTIG / FEATURE_OFFEN |
| Empfehlung | {/_model finish / Noch {K} Zyklen / Weiter} |

## Model-Update

### Neue Wahrheiten
- W{n+1}: {Erkenntnis} [aus Finding F{m}, Zyklus {k}]

### Korrigierte Wahrheiten
- W{n}: KORRIGIERT: {neue Formulierung} [Grund: F{m}]

### GC: Widerlegte und Eliminierte W{n}
- W{x}: [WIDERLEGT, ERGEBNIS{K}: {Grund}] (aus Widerlegungs-Marker)
- W{y}: [ELIMINIERT, ANALYSE{N}: Battle-Royale] (aus BR-Bewertung)
- (oder: "Keine GC-Aenderungen in diesem Zyklus")

### Kap. 6a Update
Offene Hypothesen-Bereiche: {aktualisierte Liste}
Aktive Technologie-Concerns: {aktualisierte Liste}

### Model-Topologie (falls Model-Split aktiv, IR-8)
- Fokus-Teilmodel: {TC-Name} ({Aenderung oder "unveraendert"})
- W{n}-Verteilung: {Aenderungen durch neue/korrigierte/GC W{n}}
- Status-Aenderungen: {ELIMINIERT/PAUSIERT/RE-AKTIVIERT oder "keine"}

### Model-Version
- Version: {X.Y} → {X.Y+1}
- Aenderungen in {NAME}_Model.md durchfuehren

============================================================
SEKTION B ABGESCHLOSSEN
============================================================

## Referenzen
| Quelle | Pfad |
|--------|------|
| Drafter D01 | .claude/analysis/drafts/{NAME}-analyse{CYCLE}-D01-code-analyse.md |
| Drafter D02 | .claude/analysis/drafts/{NAME}-analyse{CYCLE}-D02-infrastruktur.md |
| ERGEBNIS | .claude/analysis/synthese/{NAME}-ERGEBNIS{CYCLE}.md |
```

### Nach Welle 2: Manifest finalisieren

```markdown
**PHASE:** _analyse{CYCLE} abgeschlossen
**NAECHSTER SCHRITT:** /_hypothese (oder /_blindspotDetection falls empfohlen, oder /_architecturalBoundaries nach erster Analyse)
**STAGNATION:** {Zaehler aus Bewertung}

### Synthese (_analyse{CYCLE} - Welle 2)
- [x] .claude/analysis/synthese/{NAME}-ANALYSE{CYCLE}.md
- [x] BR-Status: {GESUND/WARNUNG/ESKALATION}
- [x] Kohaesion: {OK / Split empfohlen / Split PFLICHT}
- [x] Model-Split: {Nicht noetig / Empfohlen / AUSGEFUEHRT ({N} Teilmodelle, Fokus: {TC})}
- [x] BSD-Trigger: {Keiner / T{x} erkannt}
- [x] Model-Update: v{X.Y} → v{X.Y+1} ({N} neue W{n}, {M} korrigiert, {K} GC)
- [x] Feature-Status: {FEATURE_ABGESCHLOSSEN / FEATURE_FAST_FERTIG / FEATURE_OFFEN}
```

---

## Ablauf: Easy

```
             ┌──────────────────┐
SYNTHESE     │  DU, Hauptagent  │  ──LIEST──▶ models/{NAME}_Model.md + Code
             │  Sek.A → Sek.B   │  ──SCHREIBT──▶ synthese/{NAME}-ANALYSE{CYCLE}.md
             └──────────────────┘
```

Keine Drafts noetig. Du machst alles selbst. Sektions-Sequenzierung gilt trotzdem.
Manifest trotzdem aktualisieren.

---

## Ablauf: Hard

```
Optional:      ┌───┐ ┌───┐ ┌───┐
EXPLORATION    │ E │ │ E │ │ E │  ──SCHREIBT──▶ exploration/{NAME}-analyse{CYCLE}-E*.md
               └─┬─┘ └─┬─┘ └─┬─┘  (Nur bei Kartografie-Luecken)
                 └─────┼─────┘
                       ▼
Welle 1:  ┌───┐ ┌───┐ ┌───┐ ┌───┐ ┌───┐
DRAFTS    │ D │ │ D │ │ D │ │ D │ │ D │  ──LIEST──▶ MODEL + ggf. exploration/*
          └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘ └─┬─┘  ──SCHREIBT──▶ drafts/{NAME}-analyse{CYCLE}-D*.md
            └─────┴─────┼─────┴─────┘
                        ▼
Welle 2:  ┌──────────────────┐
SYNTHESE  │  DU, Hauptagent  │  ──LIEST──▶ drafts/{NAME}-analyse{CYCLE}-D*.md
          │  Sek.A → Sek.B   │  ──SCHREIBT──▶ synthese/{NAME}-ANALYSE{CYCLE}.md
          └──────────────────┘  ──UPDATED──▶ models/{NAME}_Model.md
```

---

## Qualitaetskriterien

- Sektions-Sequenzierung eingehalten (A vollstaendig vor B, HO-03)
- Alle Findings mit Datei:Zeile referenziert
- Model-Bezug: Was ist neu, was bestaetigt, was widerspricht
- KEINE Hypothesen-Kandidaten (das macht /_hypothese)
- Keine Annahmen - nur verifizierte Fakten
- Model-Update: Neue W{n} klar formuliert mit Finding-Referenz
- Draft-Quellen in Referenzen dokumentiert
- Battle-Royale-Bewertung: SRS-Trend interpretiert (PC2/HO)
- Kohaesion-Check: W{n}/TC gezaehlt, Trigger geprueft (PC2/SO)
- Blind-Spot-Trigger: T1-T5 geprueft (OPT/SO)
- Stagnations-Bewertung: Schwellen geprueft, Massnahme dokumentiert
- GC: Widerlegungs-Marker aus ERGEBNIS verarbeitet
- Kap. 6a im Model aktualisiert (Offene Bereiche, Aktive TCs)
- Model-Split: Bei PFLICHT-Trigger ausgefuehrt (Model-Topologie + Teilmodelle + VM-1..6)
- Model-Topologie aktualisiert (falls Split aktiv, IR-8)
- **NEU (v2.1):** Feature-Abschluss-Erkennung durchgefuehrt (W{n}-Status gezaehlt)
- **NEU (v2.1):** Bei FEATURE_ABGESCHLOSSEN: Model-Finish vorgeschlagen
- **NEU (v2.1):** Feature-Status im Manifest dokumentiert

---

## Naechster Schritt

- Bei **FEATURE_OFFEN**: `/_hypothese` (oder `/_blindspotDetection` / `/_architecturalBoundaries`)
- Bei **FEATURE_FAST_FERTIG**: `/_hypothese` fuer offene W{n}, dann `/_model finish`
- Bei **FEATURE_ABGESCHLOSSEN**: `/_model {NAME} finish` (Model verfeinern + Split-Pruefung)

ARGUMENTS: $ARGUMENTS
