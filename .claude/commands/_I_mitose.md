---
type: building-block
---

# /_I_mitose

**Status:** v1.1 (NUR Git-Operationen, .claude/ Verteilung → /_I_fanOut)
**Actor:** MITOSE-ORCHESTRATOR
**Zweck:** Git Worktrees + Branches erstellen fuer parallele Slice-Bearbeitung

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_I_mitose {FEATURE_PREFIX} [--slices S1,S2,S3]      |
+===============================================================+
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. {VAULT}/_manifest.md                            |
|    2. PRIMAER: {VAULT}/.../Blueprint/{NAME}-ARCHITECT.md       |
|       FALLBACK: .claude/analysis/synthese/{NAME}-ARCHITECT.md  |
|       → Slice-Liste + Abhaengigkeiten                         |
|    3. .claude/SLICE-BRIEFINGS.md (falls vorhanden)             |
|    4. Git Status (aktueller Branch)                            |
|                                                                |
|  ERSTELLT (Output) - NUR GIT:                                  |
|    1. Git Worktrees pro Slice:                                 |
|       ../{REPO}-{SLICE}/                                       |
|    2. Branch pro Worktree:                                     |
|       feature/{FEATURE_PREFIX}_{SLICE}                         |
|                                                                |
|  ERSTELLT NICHT (→ /_I_fanOut):                                |
|    - .claude/ Kopie in Worktrees                              |
|    - CURRENT_SLICE.md                                          |
|    - Manifest FanOut-Status                                    |
|                                                                |
|  PIPELINE:                                                     |
|    [/_I_cleanCodeArchitect] → [/_I_mitose] → [/_I_fanOut] →   |
|    [/_I_cleanCodeSlice pro Worktree]                           |
|                                                                |
|  NAECHSTER SCHRITT: /_I_fanOut (immer!)                        |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**MITOSE-ORCHESTRATOR:** NUR Git Worktrees + Branches erstellen.

**TUT:** Slices aus ARCHITECT.md lesen, Abhaengigkeiten pruefen (Wellen),
Git Worktrees erstellen, Feature-Branches erstellen, Uebersicht ausgeben.

**NICHT:** .claude/ kopieren (→ FanOut), Code/Tests schreiben, Slices planen,
Worktrees mergen (→ FanIn).

---

## Schritt 0: Inputs lesen

```
1. Aktuellen Branch ermitteln (Mothership)
2. Feature-Prefix extrahieren
3. ARCHITECT.md lesen → Slices + Abhaengigkeiten
4. Wellen bestimmen:
   Welle 1: Slices OHNE Abhaengigkeiten (parallel)
   Welle 2+: Slices MIT Abhaengigkeiten (nach FanIn von Welle 1)
```

---

## Schritt 1: Abhaengigkeiten → Wellen

```
Aus ARCHITECT.md Dependency-Graph:

| Slice | Welle | Abhaengigkeit |
|-------|-------|---------------|
| S4_S3Key | 1 | - |
| S1S2_DBSchema | 1 | - |
| S5_Retry | 1 | - |
| S6_Locking | 2 | braucht S1 |

Erstelle NUR Welle 1 Worktrees (oder --welle Parameter).
Welle 2 wird spaeter durch /_I_fanIn → /_I_mitose → /_I_fanOut erstellt.
```

---

## Schritt 2: Worktrees erstellen

### Fuer JEDEN Slice in der aktiven Welle:

```
REPO_ROOT = git rev-parse --show-toplevel
PARENT_DIR = dirname(REPO_ROOT)
FEATURE_PREFIX = aus Branch extrahiert

Pro Slice:
  WORKTREE_DIR = {PARENT_DIR}/{REPO_NAME}-{SLICE}
  BRANCH_NAME = feature/{FEATURE_PREFIX}_{SLICE}

  git worktree add -b {BRANCH_NAME} {WORKTREE_DIR}
```

---

## Schritt 3: Uebersicht + Naechster Schritt

```
AUSGABE pro Worktree:
  "Worktree: {PFAD}"
  "Branch: {BRANCH_NAME}"
  "Slice: {SLICE_NAME}"

AUSGABE Zusammenfassung:
  "{N} Worktrees erstellt (Welle {W})."
  ""
  "NAECHSTER SCHRITT: /_I_fanOut"
  "  → Kopiert .claude/ in jeden Worktree"
  "  → Setzt CURRENT_SLICE.md"
  "  → Aktualisiert Mothership-Manifest"

Falls Welle 2+ existiert:
  "Welle 2 (spaeter nach FanIn): {SLICE_LIST}"
```

---

## Optionale Parameter

| Parameter | Beschreibung | Beispiel |
|-----------|-------------|----------|
| `--slices` | Nur bestimmte Slices | `--slices S4,S5` |
| `--welle` | Nur Welle N | `--welle 1` |
| `--dry-run` | Nur zeigen, nicht erstellen | `--dry-run` |

---

## Cleanup (nach FanIn + Merge)

```
git worktree remove ../DCSRE-881-S4_S3Key/
git worktree list
git worktree prune
```

---

## Qualitaetskriterien

- NUR Git-Operationen (kein .claude/)
- Wellen korrekt aus ARCHITECT.md Abhaengigkeiten abgeleitet
- Nur aktive Welle erstellt (nicht blockierte Slices)
- Naechster Schritt klar: /_I_fanOut
- Bei Fehler: Rollback-Anweisungen ausgeben

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (alle Schritte abgeschlossen, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_I_mitose abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
