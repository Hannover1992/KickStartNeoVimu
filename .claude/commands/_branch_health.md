# /_branch_health — Branch-Hygiene Guard

```yaml
status: active
version: 1.0.0
created: 2026-03-12
op: StageGate
phase: Pre-Stage
type: building-block
chain_position: guard
team_based: false
```

---

```
╔══════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_branch_health [--base {branch}]                          ║
╠══════════════════════════════════════════════════════════════════════╣
║  ACTOR: DU direkt (kein Worker-Spawn). Read-only Guard.              ║
║                                                                      ║
║  ZWECK:                                                              ║
║    Prueft Feature-Branch-Hygiene VOR Stage/Commit-Normierung.       ║
║    Erkennt Merge-Commits, veraltete Basis, Conflicts.                ║
║    Gibt CLEAN/WARN/KRITISCH zurueck mit konkreter Empfehlung.       ║
║                                                                      ║
║  PIPELINE-POSITION:                                                  ║
║    **/_branch_health** → /_stage_orchestrate → /_Pre_PR             ║
║                                                                      ║
║  LIEST:                                                              ║
║    git log (Branch-History)                                          ║
║    git merge-base (gemeinsamer Vorfahre mit base)                   ║
║    git rev-list (Commit-Zaehlung)                                    ║
║                                                                      ║
║  SCHREIBT: NICHTS (nur Terminal-Output)                              ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    NIE git Befehle mit Seiteneffekten (kein rebase, merge, push)    ║
║    NUR lesende git-Operationen                                       ║
║    Entscheidung liegt beim User (Guard empfiehlt nur)                ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
/_branch_health [--base {branch}]
```

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `--base` | develop | Basis-Branch fuer Vergleich |

**Beispiele:**
```
/_branch_health                     → Prueft gegen develop
/_branch_health --base main         → Prueft gegen main
/_branch_health --base origin/develop → Prueft gegen remote develop
```

---

## ABLAUF

### Schritt 1: Branch-Kontext ermitteln

```bash
CURRENT_BRANCH=$(git branch --show-current)
BASE_BRANCH=${--base || "develop"}
MERGE_BASE=$(git merge-base $CURRENT_BRANCH $BASE_BRANCH)
COMMITS_AHEAD=$(git rev-list --count $MERGE_BASE..$CURRENT_BRANCH)
COMMITS_BEHIND=$(git rev-list --count $MERGE_BASE..$BASE_BRANCH)
```

### Schritt 2: Merge-Commit-Detection

```bash
MERGE_COMMITS=$(git log $MERGE_BASE..$CURRENT_BRANCH --merges --oneline)
MERGE_COUNT=$(echo "$MERGE_COMMITS" | grep -c .)
```

**Bewertung:**
- 0 Merge-Commits → CLEAN
- 1-2 Merge-Commits → WARN ("Rebase empfohlen, Merge-Commits erschweren Review")
- 3+ Merge-Commits → KRITISCH ("Branch-History verschmutzt, Rebase dringend empfohlen")

### Schritt 3: Basis-Aktualitaet pruefen

```
IF COMMITS_BEHIND > 0:
  BEHIND_DAYS = Tage seit MERGE_BASE Commit-Datum
  IF BEHIND_DAYS > 7 OR COMMITS_BEHIND > 50:
    → WARN: "Branch ist {COMMITS_BEHIND} Commits / {BEHIND_DAYS} Tage hinter {BASE}"
  IF BEHIND_DAYS > 14 OR COMMITS_BEHIND > 100:
    → KRITISCH: "Branch stark veraltet — Rebase auf {BASE} vor Stage"
```

### Schritt 4: Conflict-Vorhersage

```bash
# Dry-run merge (kein tatsaechlicher merge)
git merge-tree $(git merge-base HEAD $BASE_BRANCH) HEAD $BASE_BRANCH
# Oder: git diff $MERGE_BASE..$BASE_BRANCH --name-only vs. eigene geaenderte Dateien
OWN_FILES=$(git diff $MERGE_BASE..HEAD --name-only)
BASE_FILES=$(git diff $MERGE_BASE..$BASE_BRANCH --name-only)
OVERLAP=$(comm -12 <(echo "$OWN_FILES" | sort) <(echo "$BASE_FILES" | sort))
```

**Bewertung:**
- 0 Overlap-Dateien → CLEAN
- 1-5 Overlap → WARN ("Potenzielle Konflikte in {N} Dateien")
- 6+ Overlap → KRITISCH ("Hohe Konflikt-Wahrscheinlichkeit")

### Schritt 5: Ergebnis berechnen

```
OVERALL = max(merge_severity, behind_severity, conflict_severity)

CLEAN:    Alle 3 Checks CLEAN
WARN:     Mindestens 1 Check WARN, keiner KRITISCH
KRITISCH: Mindestens 1 Check KRITISCH
```

### Schritt 6: Output

```
/_branch_health: {CLEAN | WARN | KRITISCH}

Branch:  {CURRENT_BRANCH}
Base:    {BASE_BRANCH}
Commits: {COMMITS_AHEAD} ahead, {COMMITS_BEHIND} behind

Checks:
  Merge-Commits:    {CLEAN|WARN|KRITISCH} ({MERGE_COUNT} gefunden)
  Basis-Aktualitaet: {CLEAN|WARN|KRITISCH} ({BEHIND_DAYS} Tage, {COMMITS_BEHIND} Commits)
  Conflict-Risiko:  {CLEAN|WARN|KRITISCH} ({OVERLAP_COUNT} ueberlappende Dateien)

{Falls WARN oder KRITISCH:}
Empfehlung:
  {Merge-Commits → "git rebase -i {BASE_BRANCH} (Merge-Commits eliminieren)"}
  {Veraltet → "git fetch && git rebase origin/{BASE_BRANCH}"}
  {Conflicts → "Vor Stage rebasen. Betroffene Dateien: {Liste}"}

{Falls CLEAN:}
→ Branch ist sauber. Weiter zu /_stage_orchestrate.
```

---

## Integration mit /_stage_orchestrate

`/_stage_orchestrate` kann `/_branch_health` als optionalen Guard aufrufen:

```
Schritt 0 (optional): /_branch_health --base develop
  IF KRITISCH: User warnen, Stage pausieren bis Rebase
  IF WARN: User informieren, Stage fortsetzen mit Warnung
  IF CLEAN: Weiter ohne Unterbrechung
```

Der Guard ist NICHT blockierend — er gibt eine Empfehlung.
Ob der User rebased oder nicht, liegt bei ihm.

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| Base-Branch existiert nicht | ABBRUCH: "{BASE} nicht gefunden. Verfuegbar: {branches}" |
| Kein git-Repo | ABBRUCH: "Kein git-Repository im aktuellen Verzeichnis" |
| Detached HEAD | WARNING: "Detached HEAD — Branch-Name nicht ermittelbar" |
| Remote nicht erreichbar | Degraded: Nur lokale Checks (kein behind-Vergleich mit remote) |

---

## Case Study: DCSRE-882 MetaDaten

**Haette /_branch_health den AP-7 Failure verhindert?**

In DCSRE-882 scheiterte /_stage_orchestrate an einem nicht-behebbaren
Gate-Failure der durch verschmutzte Branch-History verursacht wurde.
Der Fehler wurde erst nach 2 Tagen Debugging erkannt.

`/_branch_health` haette am Anfang von stage_orchestrate gewarnt:
- KRITISCH: 3+ Merge-Commits in Branch-History
- Empfehlung: "Rebase vor Stage"
- Zeitersparnis: ~2 Tage Debugging

---

ARGUMENTS: $ARGUMENTS
