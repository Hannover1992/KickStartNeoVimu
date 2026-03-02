# /_finish - Feature-Abschluss & Cleanup

```yaml
status: active
version: 1.1.0
created: 2026-02-21
updated: 2026-02-27
op: FeatureFinish
phase: Cleanup
type: command
chain_position: final
team_based: false
changelog: |
  v1.1.0 (2026-02-27): Schritt 0 PUSH_STATUS Guard hinzugefuegt (F04, W158).
        Verhindert Feature-Abschluss ohne abgeschlossenen Wissens-Push.
        Guard: --skip-push-guard Flag, Manifest-PUSH_STATUS Pruefung,
        Prefix-Match mit FALSE POSITIVE Schutz ("NOT COMPLETED" → kein Match).
        Hintergrund-Text W158 integriert.
  v1.0.0 (2026-02-21): Initialer Entwurf. Einfacher Command (kein Orchestrator).
        4 Schritte: Status-Check → Offene Items (HiL) →
        Konsistenz-Check → Bereit fuer naechstes Feature.
        Liest _manifest, _parking-lot, Task.md, Model.
        Batch-Modus fuer >5 offene Items (AskUserQuestion multiSelect).
```

---

```
+======================================================================+
| COMMAND: /_finish [NAME]                                              |
+======================================================================+
|                                                                        |
| ACTOR: DU (die ausfuehrende Claude-Instanz, KEIN Team, KEIN Worker)  |
|                                                                        |
| ZWECK: Feature sauber abschliessen. Offene Items verarbeiten,         |
|        .claude/* konsistent machen, bereit fuer naechstes Feature.    |
|                                                                        |
| TYP: Einfacher Command — KEIN Orchestrator, kein Team, kein Worker.   |
|      Du fuehrst alle 4 Schritte SELBST aus.                           |
|                                                                        |
| AUFRUF:                                                                |
|   /_finish [NAME]                                                     |
|   NAME ist optional — wenn nicht angegeben, aus _manifest.md lesen.   |
|                                                                        |
| KEIN HiL fuer den Abschluss selbst — aber HiL fuer offene Items!    |
|                                                                        |
| LIEST:                                                                 |
|   .claude/analysis/_manifest.md       (Phase, Coverage, SRS)          |
|   .claude/analysis/_parking-lot.md    (offene [ ] Items)              |
|   .claude/Task.md                     (offene ECs/TCs)                |
|   .claude/models/{NAME}_Model.md      (offene W{n})                   |
|                                                                        |
| SCHREIBT:                                                              |
|   .claude/analysis/_manifest.md       (PHASE=READY)                   |
|   .claude/analysis/_parking-lot.md    (Items aktualisiert)            |
|   .claude/Task.md                     (ECs als erledigt/verworfen)    |
|   .claude/models/{NAME}_Model.md      (W{n} als erledigt/verworfen)  |
+======================================================================+
```

---

## Schritt 0: PUSH_STATUS Guard

**Zweck:** Verhindert Feature-Abschluss ohne abgeschlossenen Wissens-Push (F04-Guard, W158).

```
1. Pruefe ob --skip-push-guard Flag gesetzt:
   → JA: Guard uebersprungen (bewusste Ausnahme). Logge im Manifest.
   → NEIN: Weitermachen

2. Lies .claude/analysis/_manifest.md
3. Suche "PUSH_STATUS:" Zeile im Manifest

4. PUSH_STATUS == "COMPLETED"? (exakte Gleichheitspruefung, kein Substring-Match)
   Suche: Zeile die mit "PUSH_STATUS:" beginnt, gefolgt von " COMPLETED" (Prefix-Match)
   KORREKT: "PUSH_STATUS: COMPLETED" → Guard bestanden → WEITER zu Schritt 1
   FALSE POSITIVE vermeiden: "PUSH_STATUS: NOT COMPLETED" → kein Match (prueft NICHT ob "COMPLETED" irgendwo enthalten ist)
   → NEIN / nicht vorhanden:
     FEHLER: "PUSH_STATUS nicht COMPLETED."
     "        Starte erst: /_W_push_temp auto"
     "        Danach: /_finish erneut aufrufen"
     → Zeige letzten PUSH_STATUS-Wert (falls vorhanden)
     → ABBRUCH
```

**Hintergrund (W158):** Ohne Push geht Feature-Wissen verloren.
Das naechste Feature kann Erkenntnisse nicht via `/_W_fetch` finden.

---

## Schritt 1: Status-Check

Lies folgende Dateien und zaehle offene Items:

### 1.1 Manifest lesen

```
Lies .claude/analysis/_manifest.md
Extrahiere:
  - NAME (falls nicht als Parameter gegeben)
  - PHASE
  - COVERAGE
  - SRS-SCORE
  - STAGNATION
```

### 1.2 Parking-Lot lesen

```
Lies .claude/analysis/_parking-lot.md
Zaehle:
  - [ ] Items (offen)
  - [x] Items (erledigt)
  - [~] Items (verworfen)
Sammle alle [ ] Items als Liste.
```

### 1.3 Task.md lesen

```
Lies .claude/Task.md (falls vorhanden)
Zaehle:
  - Offene ECs (Erfolgskriterien ohne ✅)
  - Offene TCs (Test Cases ohne ✅)
Sammle alle offenen ECs/TCs als Liste.
```

### 1.4 Model lesen

```
Lies .claude/models/{NAME}_Model.md (falls vorhanden)
Zaehle:
  - W{n} mit Status AKTIV oder ZUR_PRUEFUNG
  - W{n} mit Status BESTAETIGT (bereits erledigt)
  - W{n} mit Status WIDERLEGT (bereits verworfen)
Sammle alle AKTIV/ZUR_PRUEFUNG W{n} als Liste.
```

### 1.5 Report

```
AUSGABE:
  "═══════════════════════════════════════════════════════
   /_finish Status-Check: {NAME}
   ═══════════════════════════════════════════════════════

   Feature: {NAME}
   Phase: {PHASE}
   Coverage: {COVERAGE}
   SRS-Score: {SRS-SCORE}

   Offene Items:
     Parking-Lot:  {N} offene [ ] Items
     Task.md:      {M} offene ECs/TCs
     Model W{n}:   {K} AKTIV/ZUR_PRUEFUNG

   Gesamt: {N+M+K} offene Items
   ═══════════════════════════════════════════════════════"
```

Falls 0 offene Items → Springe zu Schritt 3.

---

## Schritt 2: Offene Items verarbeiten (HiL)

### 2.1 Batch-Entscheidung

Falls <= 5 offene Items: Frage EINZELN (ein AskUserQuestion pro Item).
Falls > 5 offene Items: Frage GRUPPIERT (AskUserQuestion mit multiSelect).

### 2.2 Einzeln fragen (<=5 Items)

Pro offenem Item:

```
AskUserQuestion:
  header: "Offenes Item"
  question: "Offenes Item: {ITEM_BESCHREIBUNG}

    Quelle: {parking-lot | Task.md EC | Model W{n}}

    Was soll damit passieren?"

  options:
    - label: "PARKEN"
      description: "In _parking-lot.md belassen/eintragen fuer spaeter"
    - label: "DISCARD"
      description: "Verwerfen — als [~] markieren mit Grund"
    - label: "ERLEDIGT"
      description: "Als [x] markieren (bereits umgesetzt)"
  multiSelect: false
```

### 2.3 Gruppiert fragen (>5 Items)

```
AskUserQuestion:
  header: "Offene Items"
  question: "Es gibt {N} offene Items. Welche sollen GEPARKT werden?
    (Nicht ausgewaehlte werden als DISCARD markiert)

    Items:
    {NUMMERIERTE_LISTE}"

  options:
    - label: "Alle PARKEN"
      description: "Alle offenen Items fuer spaeter parken"
    - label: "Alle DISCARD"
      description: "Alle offenen Items verwerfen"
    - label: "Einzeln entscheiden"
      description: "Jedes Item einzeln durchgehen"
  multiSelect: false
```

Bei "Einzeln entscheiden" → Wechsle zu 2.2 (einzeln fragen).

### 2.4 Entscheidungen umsetzen

Pro Item basierend auf User-Entscheidung:

**PARKEN:**
- Falls aus parking-lot: [ ] belassen
- Falls aus Task.md: Neuen Eintrag in _parking-lot.md:
  `- [ ] [aus Task.md EC] {BESCHREIBUNG}`
- Falls aus Model: Neuen Eintrag in _parking-lot.md:
  `- [ ] [aus Model W{n}] {BESCHREIBUNG}`

**DISCARD:**
- Falls aus parking-lot: `[ ]` → `[~]` mit Grund "Feature-Ende, verworfen"
- Falls aus Task.md: EC als "VERWORFEN" markieren
- Falls aus Model: W{n} Status auf ELIMINIERT setzen

**ERLEDIGT:**
- Falls aus parking-lot: `[ ]` → `[x]`
- Falls aus Task.md: EC als ✅ markieren
- Falls aus Model: W{n} Status auf BESTAETIGT setzen

---

## Schritt 3: .claude/* Konsistenz-Check

### 3.1 Models pruefen

```
Fuer jede Datei in .claude/models/*.md:
  - Hat sync-Block? (Obsidian Sync Metadaten)
  - Ist finalisiert? (status: final im Frontmatter)
```

### 3.2 Synthese pruefen

```
Fuer jede Datei in .claude/analysis/synthese/{NAME}-*.md:
  - Hat Frontmatter? (YAML-Block am Anfang)
  - Ist Status gesetzt? (final/partial/draft)
```

### 3.3 Manifest-Phase pruefen

```
Passt PHASE zum aktuellen Stand?
  - Alle Items verarbeitet → PHASE sollte DONE oder READY sein
  - Post-Cycle durchlaufen → PHASE sollte nicht mehr "SC-CYCLE" sein
```

### 3.4 Stale Teams pruefen

```
Pruefe ob aktive Teams existieren:
  ls ~/.claude/teams/
Gibt es Teams die zu {NAME} gehoeren und noch aktiv sind?
  - sc-{name}/*
  - wp-{name}/*
  - i-pipeline-{name}/*
Falls ja: Melde als Inkonsistenz.
```

### 3.5 Report

```
AUSGABE:
  "{M} Inkonsistenzen gefunden:"
  - {LISTE_DER_INKONSISTENZEN}

  ODER:
  "Alles sauber — keine Inkonsistenzen."
```

Falls Inkonsistenzen: Team Lead behebt sie automatisch (Frontmatter ergaenzen,
Phase korrigieren). Bei stale Teams: Melde dem User.

---

## Schritt 4: Bereit fuer naechstes Feature

### 4.1 Manifest updaten

```
Aktualisiere .claude/analysis/_manifest.md:
  PHASE: READY
  NAECHSTER_SCHRITT: (leer)
  VORHERIGES FEATURE: {NAME} (ABGESCHLOSSEN, SRS {SRS}, {ZYKLEN} Zyklen, {DATUM})
```

### 4.2 Parking-Lot aktualisieren

```
Falls neue Items aus Schritt 2 hinzugefuegt wurden:
  Sauber in _parking-lot.md eintragen mit Quelle und Datum.
```

### 4.3 User informieren

```
AUSGABE:
  "═══════════════════════════════════════════════════════
   Feature '{NAME}' abgeschlossen.
   ═══════════════════════════════════════════════════════

   Geparkt:    {N} Items fuer spaeter
   Verworfen:  {M} Items
   Erledigt:   {K} Items (nachtraeglich)

   Naechste Optionen:
   - /_A_orchestrate {NEUES_FEATURE}  → neues Feature analysieren
   - /_SC_orchestrate {NAME}          → Forschung vertiefen
   - Parking-Lot Item aufgreifen      → offene Items bearbeiten

   ═══════════════════════════════════════════════════════"
```

---

## QUICK-START

Wenn User sagt "Feature abschliessen" oder "/_finish":

```
1. Lies _manifest.md → NAME, Phase, Coverage
2. Zaehle offene Items (parking-lot + Task.md + Model)
3. Frage User pro Item: PARKEN / DISCARD / ERLEDIGT
4. Pruefe .claude/* Konsistenz
5. Manifest: PHASE=READY
6. Melde User: "Feature fertig, naechste Optionen"
```

---

ARGUMENTS: $ARGUMENTS
