---
type: building-block
---

# /_I_fanOut

**Status:** v2.0 (Z2: Sub-Blueprint Verteilung + TDD-Instructions + Kanarienvogel-Verbot)
**Actor:** MOTHERSHIP-OPERATOR
**Zweck:** .claude/ Artefakte vom Mothership in Worktrees verteilen + Sub-Blueprints kopieren + Manifest tracken

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_I_fanOut                                           |
+===============================================================+
|                                                                |
|  VORAUSSETZUNG:                                                |
|    /_I_mitose wurde ausgefuehrt                               |
|    → Worktree-Branches + Ordner existieren bereits            |
|    → Mitose hat Branch-Naming + Erstellung gemacht            |
|    → FanOut macht NUR die .claude/ Verteilung                 |
|                                                                |
|  LIEST:                                                        |
|    1. ARCHITECT.md (PRIMAER: {VAULT}/.../Blueprint/{NAME}-ARCHITECT.md) |
|       FALLBACK: .claude/analysis/synthese/{NAME}-ARCHITECT.md  |
|       → Slice-Liste + Abhaengigkeiten                         |
|    2. _manifest.md → Aktueller Feature-Status                 |
|    3. SLICE-BRIEFINGS.md → Welcher Slice in welchem Worktree  |
|    4. Worktree-Pfade (User gibt an oder aus Mitose bekannt)   |
|    5. analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md       |
|       → Sub-Blueprints pro Slice (falls vorhanden)            |
|                                                                |
|  KOPIERT (Mothership → jeder Worktree):                        |
|    PFLICHT:                                                    |
|      - ARCHITECT.md (PRIMAER: {VAULT}/.../Blueprint/, FALLBACK: analysis/synthese/) |
|      - analysis/_manifest.md                                  |
|      - analysis/plans/{SLICE}-PLAN.md (falls vorhanden)       |
|      - patterns/_pattern-library.md                           |
|      - Task.md                                                |
|      - SLICE-BRIEFINGS.md                                     |
|      - commands/ (ganzer Ordner)                              |
|      - agents/ (ganzer Ordner)                                |
|      - meta/ (ganzer Ordner)                                  |
|    PRO WORKTREE:                                               |
|      - CURRENT_SLICE.md → mit zugewiesenem Slice-Namen        |
|                                                                |
|  KOPIERT (zusaetzlich, Sub-Blueprint-Verteilung):              |
|    analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md          |
|    → In jeden zugehoerigen Worktree kopiert                   |
|    → Graceful Degradation: Falls kein Sub-Blueprint → SKIP    |
|                                                                |
|  SCHREIBT (in Mothership .claude/):                            |
|    _manifest.md → FanOut-Status:                              |
|      - Welche Worktrees aktiv                                 |
|      - Welcher Slice wo zugewiesen                            |
|      - Abhaengigkeiten (wer blockiert wen)                    |
|      - Zeitstempel FanOut                                     |
|                                                                |
|  PIPELINE:                                                     |
|    [/_I_mitose] → [/_I_fanOut] → [Worktrees arbeiten] →      |
|    [/_I_fanIn]                                                 |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**MOTHERSHIP-OPERATOR:** Verteilt .claude/ Artefakte an Worktrees.

**TUT:** .claude/ kopieren, CURRENT_SLICE.md setzen, Manifest mit FanOut-Status updaten.

**NICHT:** Git Branches erstellen (macht Mitose), Code schreiben, Slices planen.

---

## Schritt 0: Voraussetzungen

```
1. Lies ARCHITECT.md → Welche Slices gibt es?
2. Lies SLICE-BRIEFINGS.md → Welcher Slice in welchem Worktree?
3. Frage User: Worktree-Pfade?
   z.B. C:\...\DCSRE-881_S1S2_DBSchema
        C:\...\DCSRE-881_S4_S3Key
4. Pruefe: Existieren die Ordner?
```

---

## Schritt 1: .claude/ Kopieren

### Fuer JEDEN Worktree:

```
1. Erstelle .claude/ Ordner im Worktree (falls nicht vorhanden)
2. Kopiere Pflicht-Artefakte (siehe Vertrag)
3. Erstelle CURRENT_SLICE.md:
   ---
   slice: {SLICE_NAME}
   worktree: {PFAD}
   mothership: {MOTHERSHIP_PFAD}
   fan_out_date: {YYYY-MM-DD}
   ---
   Dieser Worktree bearbeitet: {SLICE_NAME}
4. AUSGABE: "Worktree {NAME}: .claude/ verteilt, Slice {SLICE} zugewiesen"
```

### Kopier-Strategie

| Artefakt | Strategie | Grund |
|----------|-----------|-------|
| commands/ | Komplett kopieren | Worktree braucht alle Commands |
| agents/ | Komplett kopieren | Worktree braucht alle Agents |
| meta/ | Komplett kopieren | Code-Konventionen |
| ARCHITECT.md | Kopieren | Kontext fuer den Slice |
| PLAN.md | Kopieren falls vorhanden | Input fuer Atomic |
| _manifest.md | Kopieren | Startpunkt-Referenz |
| _pattern-library.md | Kopieren | Blueprint-Patterns |
| Task.md | Kopieren | Akzeptanzkriterien |
| SLICE-BRIEFINGS.md | Kopieren | Slice-Kontext |
| Synthese anderer Slices | NICHT kopieren | Gehoert zum anderen Slice |
| Sub-Blueprints | Kopieren falls vorhanden | TDD-Scope fuer Worker |

---

## Schritt 1b: Sub-Blueprint verteilen (Stufen-Modus)

Falls `.claude/analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md` existiert:

```
1. Fuer JEDEN Worktree mit zugewiesenem Slice:
   a) Erstelle Verzeichnis falls noetig:
      {WORKTREE}/.claude/analysis/blueprints/{FEATURE}/{SLICE}/
   b) Kopiere sub-{NR}.md:
      Quelle:  .claude/analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md
      Ziel:    {WORKTREE}/.claude/analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md
   c) AUSGABE: "Sub-Blueprint sub-{NR}.md → Worktree {PFAD} kopiert"

2. Graceful Degradation:
   Falls kein Sub-Blueprint fuer einen Slice vorhanden → SKIP
   (Worker arbeitet wie bisher ohne Sub-Blueprint)
```

---

## Schritt 1b2: Modul-Register verteilen (NUR Stufe 2)

Falls `.claude/analysis/blueprints/{FEATURE}/S2/module-register.md` existiert:

```
1. Kopiere in JEDEN S2-Worktree:
   Quelle: .claude/analysis/blueprints/{FEATURE}/S2/module-register.md
   Ziel:   {WORKTREE}/.claude/analysis/blueprints/{FEATURE}/S2/module-register.md
2. AUSGABE: "Modul-Register → {N} Worktrees verteilt"
3. Graceful Degradation: Falls Register fehlt → WARN und weiter (kein Abbruch)
```

---

## Schritt 1c: TDD-Instructions-Template erstellen (Stufen-Modus)

Pro Worktree wird ein TDD-Instructions-Template erstellt, das Workers strukturierte
Anweisungen fuer ihre Test-Stufe gibt. Basiert auf stage_{N}.md Metadaten.

```
1. Lese .claude/meta/implementation/stage_{N}.md (N = aktuelle Stufe)
   → Extrahiere: fokus, testbefehl, testpfad, mocks_erlaubt, fanout

2. Erstelle {WORKTREE}/.claude/TDD_INSTRUCTIONS.md:

   ---
   stufe: {N}
   slice: {SLICE_NAME}
   fokus: {fokus aus stage_{N}.md}
   testbefehl: {testbefehl}
   testpfad: {testpfad}
   mocks_erlaubt: {mocks_erlaubt}
   max_parallel: {fanout}
   erstellt_von: fanOut
   erstellt_am: {YYYY-MM-DD}
   ---

   # TDD-Instructions fuer {SLICE_NAME} (Stufe {N})

   ## Methodik (PFLICHT — Uncle Bob Red-Green-Refactor-Check)

   **Regel 1 (Red):** Schreibe zuerst den Test, der dich zwingt den Code zu schreiben.
   **Regel 2 (Green):** Minimaler Code. "Don't go for the gold" (Uncle Bob).
   **Regel 3 (Refactor):** DRY + Clean Code fuer SOWOHL Code ALS AUCH Tests.
   **Regel 4 (Check):** Pruefe ob der neue Code zum Sub-Blueprint passt.
     Weicht er ab? → Korrigiere oder dokumentiere Abweichung als Finding.

   ## Gegenlaeufer-Prinzip
   Fange mit Edge Cases an (leere Listen, null, Grenzwerte).
   Dann Normalfall. Dann komplexe Szenarien. NICHT umgekehrt.
   Tests werden spezifischer → Code wird generischer.

   ## 3 Einstiegsfragen (VOR jedem Test)
   1. Was ist der EINFACHSTE Test der mich zwingt, echten Code zu schreiben?
   2. Welchen Edge Case deckt dieser Test ab?
   3. Braucht dieser Test ueberhaupt eigenen Production-Code? (Logiklos → SKIP)

   ## Scope
   - Fokus: {fokus}
   - Testbefehl: {testbefehl}
   - Testpfad: {testpfad}
   - Mocks erlaubt: {mocks_erlaubt}

   ## Kanarienvogel-Regel (VERBOTEN — read-only!)
   Kanarienvogel-Tests (Kategorie 3 der Test-Inventar) sind READ-ONLY.
   Du darfst sie AUSFUEHREN aber NICHT AENDERN oder LOESCHEN.
   Bei Kanarienvogel-Bruch (Test faellt rot):
     → block_reason="kanarienvogel_broken" im exit_report
     → Sofortige Eskalation an Team Lead
   Bei versehentlicher Aenderung:
     → block_reason="kanarienvogel_modified" im exit_report
     → Revert + Eskalation

3. Graceful Degradation:
   Falls stage_{N}.md nicht vorhanden → TDD_INSTRUCTIONS.md mit Defaults erstellen
   (fokus="unit", testbefehl="dotnet test", mocks_erlaubt=true)
```

---

## Schritt 1d: Blueprint-Kopier-Liste generieren

Erstellt eine Uebersicht aller verteilten Artefakte pro Worktree fuer Traceability.

```
1. Pro Worktree: Sammle Liste aller kopierten Dateien
2. Schreibe {WORKTREE}/.claude/FANOUT_MANIFEST.md:

   ---
   erstellt_von: fanOut
   erstellt_am: {YYYY-MM-DD}
   stufe: {N}
   ---

   # FanOut Manifest

   | Artefakt | Quelle | Status |
   |----------|--------|--------|
   | commands/ | Mothership | kopiert |
   | agents/ | Mothership | kopiert |
   | meta/ | Mothership | kopiert |
   | ARCHITECT.md | Mothership | kopiert |
   | Task.md | Mothership | kopiert |
   | sub-{NR}.md | blueprints/{FEATURE}/{SLICE}/ | kopiert |
   | TDD_INSTRUCTIONS.md | generiert | neu |
   | CURRENT_SLICE.md | generiert | neu |

3. AUSGABE: "Blueprint-Kopier-Liste: {N} Artefakte verteilt"
```

---

## Schritt 2: Mothership Manifest Update

```markdown
## FanOut-Status

**Datum:** {YYYY-MM-DD}
**Aktive Worktrees:** {N}

| Worktree | Slice | Pfad | Status | Blocked By |
|----------|-------|------|--------|------------|
| A | S1S2_DBSchema | C:\...\S1S2 | AKTIV | - |
| B | S4_S3Key | C:\...\S4 | AKTIV | - |
| C | S5_Retry | - | BLOCKIERT | S1S2 |
```

---

## Schritt 3: Ausgabe

```
AUSGABE pro Worktree:
  "Worktree {N}: {PFAD}"
  "  Slice: {SLICE_NAME}"
  "  .claude/ kopiert: {N} Dateien"
  "  CURRENT_SLICE.md gesetzt"

AUSGABE Zusammenfassung:
  "{N} Worktrees bereit."
  "Oeffne je ein Terminal, wechsle in den Ordner, starte claude."
  "Jeder Worktree weiss ueber CURRENT_SLICE.md welcher Slice er bearbeitet."
  "Wenn ein Worktree fertig: /_I_fanIn {SLICE}"
```

---

## Qualitaetskriterien

- Alle Pflicht-Artefakte kopiert
- CURRENT_SLICE.md in jedem Worktree korrekt
- Mothership Manifest mit FanOut-Status aktualisiert
- Keine Synthese-Dateien anderer Slices kopiert (Isolation!)
- User weiss genau was als naechstes zu tun ist
- TDD_INSTRUCTIONS.md in jedem Worktree erstellt (Stufen-Modus)
- Kanarienvogel-read-only-Verbot in TDD_INSTRUCTIONS.md dokumentiert
- Sub-Blueprints in zugehoerige Worktrees kopiert (falls vorhanden)
- FANOUT_MANIFEST.md in jedem Worktree erstellt (Traceability)

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_I_fanOut abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
