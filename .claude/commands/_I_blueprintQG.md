---
status: active
version: 1.2.0
created: 2026-03-06
updated: 2026-03-08
op: BlueprintQG
phase: Architect
type: building-block
chain_position: architect-5-of-5
team_based: false
---

# /_I_blueprintQG

```
+======================================================================+
| META-COMMAND: /_I_blueprintQG                                        |
+======================================================================+
|                                                                        |
| ACTOR: QUALITY-GATE                                                   |
|        Bewertet den Gross-Blueprint (mit allen 4 Sektionen:           |
|        Architektur, Test-Inventar, Gold-Definition, Pattern-Zuweis.). |
|        PASS -> Freigabe fuer _I_cleanCodeSlice.                       |
|        FAIL -> Feedback-Datei + max 2 Retries -> HiL.                |
|                                                                        |
| PIPELINE-POSITION: Nach _I_patternLibrary (Schritt 4),              |
|                    vor _I_cleanCodeSlice (Schritt 6)                  |
|                                                                        |
| SRP: Einzig verantwortlich fuer Blueprint-Validierung                 |
|      Aendert NICHT den Blueprint (nur Frontmatter: qg_blueprint)      |
|      Erstellt KEINE Sub-Blueprints (-> cleanCodeSlice)                |
|      Fuehrt KEINE Tests aus (-> TDD-Zyklus)                           |
+======================================================================+
```

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_I_blueprintQG {NAME} --stufe {N}                        ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                            ║
║    1. {WORKING_DIR}/_manifest.md  (per-Story BL-155 AK-1)   ║
║       (Pipeline-State, Blueprint-Pfad via s{N}_blueprint_path,       ║
║        retry_count fuer Retry-Protokoll)                             ║
║    2. .claude/meta/implementation/stage_{STUFE}.md                   ║
║       (Stufen-Metadaten: exit_criteria, fanout, mocks_erlaubt)       ║
║    3. .claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md        ║
║       (Komplett, mit Pattern-Zuweisung Sektion -- PFLICHT)           ║
║    4. .claude/specs/{NAME}_Spec.md                                   ║
║       (Ziel-Anforderungen fuer Vollstaendigkeits-Check, BL-008)      ║
║    5. .claude/models/{NAME}_Model.md                                 ║
║       (Wissens-Modell fuer Konsistenz-Check)                         ║
║    6. .claude/analysis/synthese/{NAME}-GAP.md                        ║
║       (GAP-Status, verhindert Doppel-Abdeckung QG-BP-4)              ║
║                                                                      ║
║  SCHREIBT (Output) - PFLICHT:                                        ║
║    .claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md           ║
║      UPDATE: Frontmatter qg_blueprint: pass|fail                     ║
║    {VAULT}/_manifest.md                                     ║
║      qg_blueprint_{N}: pass|fail                                     ║
║      retry_count: {aktueller Wert}                                   ║
║    [NUR BEI FAIL]:                                                   ║
║    .claude/analysis/blueprints/{FEATURE}/S{N}/qg-feedback.md         ║
║      Strukturiertes Feedback fuer cleanCodeArchitect                 ║
║                                                                      ║
║  HAUPTPRODUKT:                                                       ║
║    PASS: Blueprint freigegeben fuer cleanCodeSlice                   ║
║    FAIL: qg-feedback.md mit spezifischen Verbesserungen              ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    - Aendert NUR Blueprint-Frontmatter (qg_blueprint: pass|fail)     ║
║    - Loescht KEINE Blueprint-Inhalte                                 ║
║    - Max 2 Retries, dann HiL (kein endloser Loop)                    ║
║    - Bei PASS: qg-feedback.md wird NICHT erstellt                    ║
║                                                                      ║
║  PIPELINE-POSITION:                                                  ║
║    [cleanCodeArchitect] -> [testSearch] -> [goldDefine]               ║
║      -> [patternLibrary] -> [blueprintQG] -> PASS: [cleanCodeSlice]  ║
║                                           -> FAIL: [cleanCodeArchit] ║
║                                              (mit qg-feedback.md)    ║
║                                                                      ║
║  ACTOR: QUALITY-GATE                                                 ║
║    Bewertet Blueprint, schreibt Urteil in Frontmatter.               ║
║    KEINE Architektur-Entscheidungen, KEINE Blueprint-Aenderungen.    ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
/_I_blueprintQG {NAME} --stufe {N}

Parameter:
  NAME:    Feature-Name (PFLICHT)
  --stufe: Teststufe 1-5 (PFLICHT). Bestimmt welcher Blueprint geprueft wird.

Beispiele:
  /_I_blueprintQG DCSRE-881 --stufe 1   -> Prueft Blueprint fuer Stufe 1
  /_I_blueprintQG MeinFeature --stufe 3  -> Prueft Blueprint fuer Stufe 3 (Integration)
```

---

## Ablauf

### Schritt 1: Blueprint + Kontext laden

1. Lies `{WORKING_DIR}/_manifest.md`  # per-Story I_PIPELINE_STATE (BL-155 AK-1)
   - Extrahiere `s{N}_blueprint_path` (Blueprint-Pfad)
   - Extrahiere `retry_count` (Default: 0 falls nicht vorhanden)
   - Validiere dass `s{N}_pattern_zuweisung: done` gesetzt ist (Vorbedingung)
2. Falls `s{N}_blueprint_path` nicht im Manifest: Default-Pfad verwenden:
   `.claude/analysis/blueprints/{NAME}/S{N}/blueprint.md`
3. Lies `.claude/meta/implementation/stage_{N}.md`
   - Extrahiere `exit_criteria`, `fanout`, `mocks_erlaubt`
   - Extrahiere `fanout`-Wert fuer QG-BP-5 Konsistenz-Check
4. Lies Blueprint vollstaendig (inkl. Pattern-Zuweisung Sektion)
5. Lade SPEC, Model, GAP fuer inhaltliche Pruefung

**Vorbedingungs-Check:**

Falls `s{N}_pattern_zuweisung: done` NICHT gesetzt:
```
FEHLER: Pattern-Zuweisung fuer Stufe {N} noch nicht abgeschlossen.
Vorbedingung nicht erfuellt: _I_patternLibrary muss zuerst ausgefuehrt werden.
Naechster Schritt: /_I_patternLibrary {NAME} --stufe {N}
```

---

### Schritt 2: 7 Pruefpunkte auswerten (RF-PIPE-006 + RF-BP-006)

```
QG-BP-1: Vollstaendigkeit -- Alle SPEC-Ziele dieser Stufe abgedeckt?
  -> Vergleiche Blueprint-Scope mit relevanten SPEC-RFs fuer Stufe N
  -> PASS: Alle kritischen RFs adressiert
  -> FAIL: Liste fehlender RFs (HART -- stoeckt bei FAIL)

QG-BP-2: Pattern-Zuweisung -- Vollstaendig und plausibel?
  -> ## Pattern-Zuweisung Sektion vorhanden?
  -> Mindestens {fanout_anzahl} Slices mit Patterns zugewiesen?
  -> Keine leere Tabelle (ausser begruendete Graceful Degradation)
  -> PASS: Zuweisung vollstaendig
  -> FAIL: Fehlende Slices oder leere Tabelle ohne Begruendung (HART)

QG-BP-3: Test-Inventar + Gold-Definition -- Sektionen vorhanden?
  -> ## Test-Inventar Sektion vorhanden? (von _I_testSearch)
     -> 3 Kategorien: Kanarienvogel (K), Boundary (B), Betroffen (A)
  -> ## Gold-Definition Sektion vorhanden? (von _I_goldDefine)
     -> Gold pro Slice + Gold-Formel
  -> ## Kanarienvoegel Sektion vorhanden? (von _I_goldDefine)
  -> ## Nicht-Ziele Sektion vorhanden? (von _I_goldDefine)
  -> PASS: Alle 4 Sektionen vorhanden (auch wenn minimal mit Begruendung)
  -> FAIL: Eine oder mehrere Sektionen fehlen (WEICH -- kein Stopp, aber WARN)

QG-BP-4: GAP-Kompatibilitaet -- Adressiert nicht bereits COMPLETE Items?
  -> Vergleiche Blueprint-Scope mit GAP-Status (COMPLETE W{n})
  -> PASS: Kein Overlap mit bereits COMPLETE W{n}
  -> PASS_WITH_WARN: Geringer Overlap (<= 30% Scope bereits COMPLETE)
  -> FAIL: Erheblicher Overlap (> 30% Scope bereits COMPLETE) (WEICH)

QG-BP-5: Stufen-Block -- Korrekt fuer diese Stufe?
  -> ## Stufen-Block Sektion vorhanden?
  -> fanout-Wert konsistent mit stage_{N}.md?
  -> mocks_erlaubt konsistent mit stage_{N}.md?
  -> PASS: Korrekte Stufen-Parameter
  -> FAIL: Inkonsistente oder fehlende Felder (HART)

QG-BP-6: Slice-Plan -- Vorhanden und mit fanout_empfehlung?
  -> ## Slice-Plan Sektion vorhanden?
  -> fanout_empfehlung angegeben?
  -> PASS: Slice-Plan mit Empfehlung vorhanden
  -> FAIL: Sektion fehlt oder keine fanout_empfehlung (WEICH)

QG-BP-7: parent_blueprint Ketten-Integritaet (RF-BP-006)
  -> Falls Stufe > 1:
     -> parent_blueprint Feld im Frontmatter vorhanden?
     -> Referenzierte Datei existiert? (Pfad-Plausibilitaet)
     -> PASS: parent_blueprint korrekt gesetzt und Datei existiert
     -> PASS_IMPLICIT: parent_blueprint null ABER Vorstufe im Manifest
        als "done" markiert (impl_test_stages[N-1] = done).
        Grund: Vorstufe lief ohne formales Blueprint (z.B. direkt TDD).
        Logge: "QG-BP-7: parent_blueprint null, Vorstufe done → PASS (implizit)"
     -> FAIL: parent_blueprint fehlt UND Vorstufe NICHT done (HART)
  -> Falls Stufe == 1:
     -> parent_blueprint darf null sein
     -> PASS: Stufe 1, kein Vorstufen-Blueprint erwartet
  -> WARN: parent_blueprint gesetzt aber Datei nicht gefunden
```

**HART-Pruefpunkte** (QG-BP-1, QG-BP-2, QG-BP-5, QG-BP-7): Ein FAIL hier = Gesamt-FAIL, kein PASS_WITH_WARN.
**WEICH-Pruefpunkte** (QG-BP-3, QG-BP-4, QG-BP-6): FAIL hier = PASS_WITH_WARN moeglich wenn alle HART bestanden.

---

### Schritt 3: Gesamt-Urteil

```
PASS:           Alle 7 QG-BP bestanden (inkl. alle HART)
PASS_WITH_WARN: Alle HART (QG-BP-1, QG-BP-2, QG-BP-5, QG-BP-7) bestanden,
                mind. 1 WEICH (QG-BP-3, QG-BP-4, QG-BP-6) mit WARN
FAIL:           Mind. 1 HART-Pruefpunkt gescheitert
```

---

### Schritt 4a: Bei PASS (oder PASS_WITH_WARN)

1. Aktualisiere Blueprint-Frontmatter: `qg_blueprint: pass`
2. Aktualisiere Manifest: `qg_blueprint_{N}: pass`
3. Bei PASS_WITH_WARN: Warnungen in Konsolen-Ausgabe anzeigen (kein Stopp)
4. Ausgabe:
   ```
   Blueprint QG PASS -- Freigabe fuer cleanCodeSlice
   [Falls PASS_WITH_WARN]: Warnungen: {Liste der WEICH-FAILs}
   Naechster Schritt: /_I_cleanCodeSlice {NAME} --stufe {N}
   ```
5. Exit-Report senden (status=final)

---

### Schritt 4b: Bei FAIL -- Retry-Protokoll (max 2)

**1. Erstelle `.claude/analysis/blueprints/{FEATURE}/S{N}/qg-feedback.md`:**

```markdown
---
type: qg-feedback
stufe: {N}
datum: {YYYY-MM-DD}
retry_nr: {retry_count + 1}
fehlgeschlagene_checks: [QG-BP-X, ...]
---

# Blueprint QG FAIL -- Retry {retry_count + 1}/2

## Fehlgeschlagene Pruefpunkte

### QG-BP-X: {Check-Name}
**Problem:** {Spezifische Beschreibung was fehlt oder falsch ist}
**Erwartung:** {Was soll der Blueprint enthalten?}
**Aktion:** {Konkrete Verbesserungsanweisung fuer cleanCodeArchitect}

[Wiederholen fuer jeden fehlgeschlagenen Check]

## Zusammenfassung

{1-2 Saetze: Was muss cleanCodeArchitect aendern?}
```

**2. Aktualisiere Blueprint-Frontmatter:** `qg_blueprint: fail`

**3. Manifest aktualisieren:**
```yaml
retry_count: {retry_count + 1}
qg_blueprint_{N}: fail
```

**4. Retry-Entscheidung:**

```
Falls retry_count < 2:
  AUSGABE:
    "Blueprint QG FAIL (Retry {retry_count+1}/2)"
    "Fehlgeschlagene Checks: {Liste}"
    "Feedback: .claude/analysis/blueprints/{FEATURE}/S{N}/qg-feedback.md"
    "_I_orchestrate: Starte cleanCodeArchitect neu mit qg-feedback.md als Input"
  Exit-Report: status=partial, block_reason="qg_fail_retry_{retry_count+1}"

Falls retry_count >= 2:
  AUSGABE:
    "Blueprint QG FAIL -- Max Retries (2) erschoepft"
    "HiL-Eskalation erforderlich: Blueprint manuell pruefen und korrigieren"
    "Dann: /_I_blueprintQG {NAME} --stufe {N} erneut ausfuehren (setzt retry_count zurueck)"
  Exit-Report: status=partial, block_reason="qg_fail_hil_required"
```

---

### Schritt 5: Exit-Report

Ausgabe an Konsole:

```
_I_blueprintQG {NAME} --stufe {N}: {PASS|PASS_WITH_WARN|FAIL}

QG-Ergebnisse:
  QG-BP-1 Vollstaendigkeit:     {PASS|FAIL}
  QG-BP-2 Pattern-Zuweisung:    {PASS|FAIL}
  QG-BP-3 Test-Inventar+Gold:   {PASS|PASS_WITH_WARN|FAIL}
  QG-BP-4 GAP-Kompatibilitaet:  {PASS|PASS_WITH_WARN|FAIL}
  QG-BP-5 Stufen-Block:         {PASS|FAIL}
  QG-BP-6 Slice-Plan:           {PASS|PASS_WITH_WARN|FAIL}
  QG-BP-7 parent_blueprint:    {PASS|FAIL|WARN}

Gesamt-Urteil: {PASS|PASS_WITH_WARN|FAIL}
Blueprint: .claude/analysis/blueprints/{NAME}/S{N}/blueprint.md
Manifest: qg_blueprint_{N} = {pass|fail}

[Falls PASS]: Naechster Schritt: /_I_cleanCodeSlice {NAME} --stufe {N}
[Falls FAIL]:  Feedback:  .claude/analysis/blueprints/{NAME}/S{N}/qg-feedback.md
               Retry {retry_count+1}/2: /_I_cleanCodeArchitect {NAME} --stufe {N}
               [Falls HiL]: Manuelle Korrektur erforderlich
```

Sende SendMessage an "team-lead":

```
_I_blueprintQG {NAME} --stufe {N}: {PASS|FAIL}
QG-Ergebnis: {Gesamt-Urteil}
Fehlgeschlagene Checks: {Liste oder "keine"}
Blueprint: .claude/analysis/blueprints/{NAME}/S{N}/blueprint.md
Manifest: qg_blueprint_{N} = {pass|fail}
```

---

## Abgrenzung (Was dieser Command NICHT tut)

- **Aendert NICHT den Blueprint-Inhalt** (nur Frontmatter: qg_blueprint: pass|fail)
- **Erstellt KEINE Sub-Blueprints** (-> _I_cleanCodeSlice ist dafuer zustaendig)
- **Weist KEINE Patterns zu** (-> _I_patternLibrary hat das bereits getan)
- **Fuehrt KEINE Tests aus** (-> TDD-Zyklus ist dafuer zustaendig)
- **Bricht NICHT ab bei PASS_WITH_WARN** (Warnungen sind informativ, kein Stopp)
- **Loescht KEINE qg-feedback.md bei PASS** (historische Aufzeichnung behalten)
- **Setzt NICHT retry_count zurueck** (nur _I_orchestrate oder HiL-Eskalation tun das)

---

## Pipeline-Position

```
[/_I_cleanCodeArchitect {NAME} --stufe {N}]
          |
          v  (erstellt blueprint.md mit Scope, Stufen-Block, Slice-Plan)
[/_I_testSearch {NAME} --stufe {N}]
          |
          v  (befuellt ## Test-Inventar Sektion: K/B/A Kategorien)
[/_I_goldDefine {NAME} --stufe {N}]
          |
          v  (befuellt ## Gold-Definition, ## Kanarienvoegel, ## Nicht-Ziele)
[/_I_patternLibrary {NAME} --stufe {N}]
          |
          v  (befuellt ## Pattern-Zuweisung Sektion)
[/_I_blueprintQG {NAME} --stufe {N}]   <-- DIESER COMMAND
          |
          +--PASS--> [/_I_cleanCodeSlice {NAME} --stufe {N}]
          |
          +--FAIL (retry < 2)--> [/_I_cleanCodeArchitect {NAME} --stufe {N}]
          |                       (liest qg-feedback.md als Input)
          |
          +--FAIL (retry >= 2)--> HiL-Eskalation (manuelle Korrektur)
```

**Prev:** `/_I_patternLibrary` (weist Patterns zu, Schritt 4)
**Next (PASS):** `/_I_cleanCodeSlice` (erstellt Sub-Blueprints)
**Next (FAIL):** `/_I_cleanCodeArchitect` (ueberarbeitet Blueprint mit Feedback)

---

## Obsidian-Tags

```yaml
tags:
  - type/quality-gate
  - pipeline/implementation
  - op/{FEATURE}
  - topic/Blueprint
  - topic/QualityGate
pipeline-position: architect-5-of-5
prev: [[I_patternLibrary]]
next: [[I_cleanCodeSlice]]
```

---

## Siehe auch

- [[_I_cleanCodeArchitect]] - Erstellt den Gross-Blueprint (Schritt 1)
- [[_I_testSearch]] - Test-Suche & Kategorisierung (Schritt 2)
- [[_I_goldDefine]] - Gold-Definition & Akzeptanzkriterien (Schritt 3)
- [[_I_patternLibrary]] - Weist Patterns zu (Schritt 4, direkter Vorgaenger)
- [[_I_cleanCodeSlice]] - Erstellt Sub-Blueprints nach QG-Freigabe (Schritt 6)
- [[_I_orchestrate]] - Orchestriert den Retry-Loop bei FAIL
