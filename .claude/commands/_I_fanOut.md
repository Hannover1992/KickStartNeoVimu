# /_I_fanOut

**Status:** v1.0
**Actor:** MOTHERSHIP-OPERATOR
**Zweck:** .claude/ Artefakte vom Mothership in Worktrees verteilen + Manifest tracken

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
|    1. ARCHITECT.md → Slice-Liste + Abhaengigkeiten            |
|    2. _manifest.md → Aktueller Feature-Status                 |
|    3. SLICE-BRIEFINGS.md → Welcher Slice in welchem Worktree  |
|    4. Worktree-Pfade (User gibt an oder aus Mitose bekannt)   |
|                                                                |
|  KOPIERT (Mothership → jeder Worktree):                        |
|    PFLICHT:                                                    |
|      - analysis/synthese/ARCHITECT.md                         |
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

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_I_fanOut abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
