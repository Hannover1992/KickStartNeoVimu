---
status: v1.0
version: "1.0"
created: 2026-02-28
op: SprintFanOut
---

# /_S_FanOut — Sprint Monitor Satelliten-Command

**Status:** v1.0
**Typ:** Satelliten-Command (Worker-Pool-Spawner)
**Actor:** TEAM_LEAD
**Modus:** READONLY (keine Writes, keine Commits, kein git push)

---

## Vertrag

```
+==============================================================+
|  COMMAND: /_S_FanOut [worktrees...]                         |
+==============================================================+
|                                                              |
|  STATUS: v1.0                                               |
|                                                              |
|  SYNTAX:                                                     |
|    /_S_FanOut                    # alle Worktrees aus       |
|                                  # session-params.md        |
|    /_S_FanOut V1-Param V3-SCI   # nur Subset               |
|                                                              |
|  LIEST:                                                      |
|    .claude/session-params.md (Worktree-Liste, YAML)         |
|                                                              |
|  SCHREIBT: NICHTS (READONLY-Aggregate)                      |
|                                                              |
|  VORAUSSETZUNG:                                             |
|    1. .claude/session-params.md existiert                   |
|    2. Jeder Worktree hat .claude/analysis/_manifest.md      |
|    3. Jeder Worktree hat INSTRUCTION.md                     |
|                                                              |
|  VERHALTEN:                                                  |
|    Spawnt N haiku Worker PARALLEL (1 pro Worktree),         |
|    aggregiert Reports und gibt strukturiertes Ergebnis       |
|    zurueck.                                                  |
|                                                              |
|  OUTPUT (aggregiert an Aufrufer):                           |
|    [{                                                        |
|      "label": "{LABEL}",                                    |
|      "status": "RUNNING|IDLE|DONE|BLOCKED|UNKNOWN",        |
|      "phase": "{PHASE_STRING}",                            |
|      "lastCommit": "{HASH} {MESSAGE}",                      |
|      "scope": "{VORHABEN_TITLE}",                          |
|      "timestamp": "{ISO_TIMESTAMP}",                        |
|      "issue": null oder "{FEHLERMELDUNG}"                  |
|    }, ...]                                                  |
|                                                              |
|  FEHLERTOLERANZ:                                            |
|    - Einzelne Worker-Fehler blockieren Aggregation nicht    |
|    - Status = UNKNOWN bei Fehler, issue = Fehlermeldung     |
|    - Worker-Timeout (30s) -> Status = BLOCKED               |
|                                                              |
+==============================================================+
```

---

## Phase 1: session-params.md lesen

Lies `.claude/session-params.md` mit dem Read-Tool:

```
Read: C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V5-Monitor/.claude/session-params.md
```

Parse die YAML-Struktur als Text. Extrahiere alle Worktree-Eintraege:

**Bash-Parsing (alternativ):**
```bash
# Labels extrahieren
grep "^\s*- label:" .claude/session-params.md | sed 's/.*label:\s*//'

# Paths extrahieren
grep "^\s*path:" .claude/session-params.md | sed 's/.*path:\s*//'

# Branches extrahieren
grep "^\s*branch:" .claude/session-params.md | sed 's/.*branch:\s*//'
```

**Ergebnis:** Liste von Objekten: `[{label, path, branch}, ...]`

Wenn `.claude/session-params.md` nicht lesbar:
- Nutze Fallback-Defaults (hardcoded):
  - `{label: "V1-Param", path: "C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V1-Param", branch: "vorhaben/1-global-param"}`
  - `{label: "V2-Audit",   path: "C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V2-Audit",   branch: "vorhaben/2-kern-audit"}`
  - `{label: "V3-SCI",     path: "C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V3-SCI-Uebergang", branch: "vorhaben/3-sci-uebergang"}`
  - `{label: "V4-Mermaid", path: "C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V4-Mermaid", branch: "vorhaben/4-mermaid-first"}`
  - `{label: "V5-Monitor", path: "C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V5-Monitor", branch: "vorhaben/5-sprint-monitor"}`
- Gib eine WARN-Meldung aus: `"WARNING: session-params.md nicht gefunden, nutze hardcoded Defaults"`

**Subset-Filter (optional):**
Wenn Argumente uebergeben wurden (z.B. `/_S_FanOut V1-Param V3-SCI`):
- Filtere Worktrees: behalte nur Eintraege, deren `label` in der Argument-Liste enthalten ist.
- Wenn nach Filter leer: STOP mit Fehler "Keine Worktrees nach Filter."

---

## Phase 2: Pro Worktree einen haiku Worker spawnen (PARALLEL)

Spawne fuer jeden Worktree einen haiku Worker mit dem Task-Tool.

**Worker-Name:** `s-worker-{LABEL}` (Beispiel: `s-worker-V1-Param`)

**Wichtig:** Alle Worker werden GLEICHZEITIG gestartet (`run_in_background: true`).
Warte NICHT auf einen Worker bevor der naechste gestartet wird.

**Worker-Prompt-Template:**
(Ersetze {LABEL}, {PATH}, {BRANCH} durch die echten Werte des jeweiligen Worktrees)

```
[WORKER-MODE] Status-Monitor fuer Worktree: {LABEL}

AUFTRAG:
Du bist ein READONLY Monitoring-Agent. Genau 4 Schritte:
1. Lese 3 Dateien (READONLY, kein Schreiben, kein Edit, kein Write-Tool)
2. Extrahiere Status-Informationen
3. Sende Report an Aufrufer (team-lead)
4. Beende dich danach (KEIN Loop!)

KONTEXT:
- Label:  {LABEL}
- Pfad:   {PATH}
- Branch: {BRANCH}

===================================================

SCHRITT 1: LESE INSTRUCTION.md (max. 20 Zeilen)

Pfad: {PATH}/INSTRUCTION.md

Nutze das Read-Tool mit limit=20.
Suche "DEIN SCOPE:" oder "## Scope" Sektion.
Extrahiere den Vorhaben-Titel als SCOPE_TEXT.
Fallback wenn nicht lesbar: SCOPE_TEXT = "NO-SCOPE"

===================================================

SCHRITT 2: LESE _manifest.md (HEAD 50 Zeilen)

Primaerer Pfad:  {PATH}/.claude/analysis/_manifest.md
Fallback-Pfad:   {PATH}/.claude/_manifest.md

Nutze das Read-Tool mit limit=50 (lese nur erste 50 Zeilen).
Suche Zeile mit: **PHASE:** oder phase: (YAML-Feld)
Extrahiere Wert als PHASE_STRING.
Fallback wenn nicht lesbar: PHASE_STRING = "UNKNOWN"

===================================================

SCHRITT 3: LAUFE GIT LOG

Befehl: git -C "{PATH}" log --oneline -1

Extrahiere:
- COMMIT_HASH = erste 7 Zeichen
- COMMIT_MESSAGE = Rest der Zeile

Fallback wenn git fehlschlaegt:
- COMMIT_HASH = "?"
- COMMIT_MESSAGE = "git not available"
(Fehler NICHT blockierend — git ist optional)

===================================================

SCHRITT 4: BESTIMME STATUS (Phase -> Status Mapping)

| PHASE_STRING                        | STATUS  |
|-------------------------------------|---------|
| DONE                                | DONE    |
| POST-CYCLE                          | DONE    |
| FINISHED                            | DONE    |
| IMPLEMENT                           | RUNNING |
| REVIEW                              | RUNNING |
| CONCEPT                             | RUNNING |
| SPEC                                | RUNNING |
| INTEGRATE                           | RUNNING |
| TEST                                | RUNNING |
| REFACTOR                            | RUNNING |
| HYPOTHESE                           | RUNNING |
| OBSERVE                             | RUNNING |
| I_PIPELINE_RUNNING                  | RUNNING |
| READY                               | IDLE    |
| DESIGN                              | IDLE    |
| I_PIPELINE_READY                    | IDLE    |
| BLOCKED                             | BLOCKED |
| ERROR                               | BLOCKED |
| WAITING_* (Muster, beginnt mit WAI) | BLOCKED |
| (default, fehlend, nicht erkannt)   | UNKNOWN |

===================================================

SCHRITT 5: SAMMEL REPORT (JSON)

{
  "label": "{LABEL}",
  "status": "RUNNING|IDLE|DONE|BLOCKED|UNKNOWN",
  "phase": "{PHASE_STRING}",
  "lastCommit": "{COMMIT_HASH} {COMMIT_MESSAGE}",
  "scope": "{SCOPE_TEXT}",
  "timestamp": "{ISO_TIMESTAMP_NOW}",
  "issue": null
}

Fehlerfall (z.B. Pfad nicht gefunden, Manifest nicht lesbar):
{
  "label": "{LABEL}",
  "status": "UNKNOWN",
  "phase": "N/A",
  "lastCommit": "?",
  "scope": "ERROR: {Grund}",
  "timestamp": "{ISO_TIMESTAMP_NOW}",
  "issue": "{Fehlerbeschreibung}"
}

===================================================

SCHRITT 6: SENDE REPORT AN team-lead

Nutze das SendMessage-Tool:
{
  type: "message",
  recipient: "team-lead",
  content: "<JSON-Report als String>",
  summary: "{LABEL}: {STATUS}"
}

Warte NICHT auf Antwort. Beende danach.

===================================================

REGELN (absolut):
- READONLY: Keine Datei-Edits, keine Commits, kein Schreiben, kein Write-Tool
- 3 Dateien: INSTRUCTION.md + _manifest.md + git log
- PARALLEL: Viele Worker gleichzeitig (keine Serialisierung)
- TERMINIERUNG: Nur 1 Report, dann beenden (kein Loop)
- FEHLERTOLERANZ: Einzelne Fehler sind nicht blockierend

DONE.
```

---

## Phase 3: Auf alle Worker warten (Timeout 30s)

Nachdem alle Worker gestartet wurden, warte auf ihre Reports.

**Timeout:** 30 Sekunden. Workers die nicht rechtzeitig antworten erhalten den Status BLOCKED.

Fuer jeden Worker der kein Report sendet (Timeout):
```json
{
  "label": "{LABEL}",
  "status": "BLOCKED",
  "phase": "UNKNOWN",
  "lastCommit": "?",
  "scope": "N/A",
  "timestamp": "{ISO_TIMESTAMP_NOW}",
  "issue": "Worker timeout (>30s)"
}
```

---

## Phase 4: Reports aggregieren und Ergebnis zurueckgeben

Sammle alle Worker-Reports und erstelle das aggregierte Ergebnis:

```
aggregated = {
  timestamp: <jetzt als ISO>,
  worktreeCount: <Anzahl Worktrees>,
  reports: [<alle Worker-Reports>],
  summary: {
    done:    <Anzahl Reports mit status=="DONE">,
    running: <Anzahl Reports mit status=="RUNNING">,
    idle:    <Anzahl Reports mit status=="IDLE">,
    blocked: <Anzahl Reports mit status=="BLOCKED">,
    unknown: <Anzahl Reports mit status=="UNKNOWN">
  }
}
```

Gib das aggregierte Ergebnis an den Aufrufer zurueck (kein SendMessage notwendig —
der Aufrufer, z.B. `/_S_Monitor`, verarbeitet das Ergebnis direkt).

---

## Status-Mapping (vollstaendig)

| Manifest PHASE        | Dashboard Status | Col3-Anzeige         |
|-----------------------|-----------------|----------------------|
| `DONE`                | **DONE**        | `Phase: DONE`        |
| `POST-CYCLE`          | **DONE**        | `Phase: POST-CYCLE`  |
| `FINISHED`            | **DONE**        | `Phase: FINISHED`    |
| `IMPLEMENT`           | **RUNNING**     | `Phase: IMPLEMENT`   |
| `REVIEW`              | **RUNNING**     | `Phase: REVIEW`      |
| `CONCEPT`             | **RUNNING**     | `Phase: CONCEPT`     |
| `SPEC`                | **RUNNING**     | `Phase: SPEC`        |
| `INTEGRATE`           | **RUNNING**     | `Phase: INTEGRATE`   |
| `TEST`                | **RUNNING**     | `Phase: TEST`        |
| `REFACTOR`            | **RUNNING**     | `Phase: REFACTOR`    |
| `HYPOTHESE`           | **RUNNING**     | `Phase: HYPOTHESE`   |
| `OBSERVE`             | **RUNNING**     | `Phase: OBSERVE`     |
| `I_PIPELINE_RUNNING`  | **RUNNING**     | `Phase: I_PIPELINE_RUNNING` |
| `READY`               | **IDLE**        | `Phase: READY`       |
| `DESIGN`              | **IDLE**        | `Phase: DESIGN`      |
| `I_PIPELINE_READY`    | **IDLE**        | `Phase: I_PIPELINE_READY`   |
| `BLOCKED`             | **BLOCKED**     | `Issue: BLOCKED`     |
| `ERROR`               | **BLOCKED**     | `Issue: ERROR`       |
| `WAITING_*` (Muster)  | **BLOCKED**     | `Issue: WAITING`     |
| Manifest fehlt        | **BLOCKED**     | `Issue: No Manifest` |
| Parse-Fehler          | **BLOCKED**     | `Issue: Parse Error` |
| Worker-Timeout (>30s) | **BLOCKED**     | `Issue: Timeout`     |
| Pfad nicht gefunden   | **UNKNOWN**     | `Issue: Path Error`  |
| PHASE-Feld fehlt      | **UNKNOWN**     | `Issue: No PHASE`    |
| Unbekannter Wert      | **UNKNOWN**     | `Phase: {RAW_VALUE}` |

---

## Ablauf-Pseudocode (Zusammenfassung)

```
FUNKTION _S_FanOut(args):

  # Phase 1: Registry laden
  worktrees = Read ".claude/session-params.md" und parse YAML
  BEI FEHLER: nutze hardcoded Defaults (5 Worktrees V1-V5)

  WENN args nicht leer:
    worktrees = worktrees.filter(wt => wt.label IN args)
    WENN leer: STOP "Keine Worktrees nach Filter"

  WENN worktrees leer: RETURN { error: "Keine Worktrees gefunden" }

  # Phase 2: Worker parallel spawnen
  workers = []
  FUER JEDEN worktree IN worktrees (PARALLEL, run_in_background: true):
    prompt = WORKER_PROMPT_TEMPLATE mit {LABEL}={worktree.label},
                                         {PATH}={worktree.path},
                                         {BRANCH}={worktree.branch}
    spawn Task-Tool: agent="haiku", name="s-worker-{worktree.label}", prompt=prompt
    workers.append(worker)
    BEI SPAWN-FEHLER:
      sammle Error-Report:
        { label: worktree.label, status: "UNKNOWN", issue: "Worker spawn failed", phase: "N/A" }

  # Phase 3: Auf alle Worker warten (30s Timeout)
  reports = warte auf alle workers (max 30s)
  FUER JEDEN worker OHNE Report (Timeout):
    reports.append({ label: worktree.label, status: "BLOCKED", issue: "Worker timeout (>30s)" })

  # Phase 4: Aggregieren und zurueckgeben
  aggregated = {
    timestamp: jetzt(),
    worktreeCount: worktrees.length,
    reports: reports,
    summary: { done, running, idle, blocked, unknown }
  }
  RETURN aggregated
```

---

## Fehlertoleranz-Regeln

| Fehler                        | Verhalten                                              |
|-------------------------------|-------------------------------------------------------|
| session-params.md fehlt       | Fallback auf hardcoded Defaults, WARN ausgeben        |
| Worktree-Pfad existiert nicht | UNKNOWN-Report fuer diesen Worktree, andere laufen   |
| INSTRUCTION.md fehlt          | scope = "NO-SCOPE", Status-Ermittlung laeuft weiter  |
| _manifest.md nicht lesbar     | status = BLOCKED, issue = "No Manifest"              |
| PHASE-Feld fehlt              | status = UNKNOWN, issue = "No PHASE"                 |
| git log fehlschlaegt          | lastCommit = "?", kein Blocker                       |
| Worker-Timeout (>30s)         | status = BLOCKED, issue = "Worker timeout (>30s)"    |
| Worker-Spawn fehlgeschlagen   | status = UNKNOWN, issue = "Worker spawn failed"      |

---

## Syntax-Beispiele

```bash
# Alle Worktrees aus session-params.md
/_S_FanOut

# Nur V1 und V3 abfragen
/_S_FanOut V1-Param V3-SCI

# Alle 5 explizit
/_S_FanOut V1-Param V2-Audit V3-SCI V4-Mermaid V5-Monitor
```

---

**Erstellt:** 2026-02-28
**Version:** 1.0
**SPEC-Referenz:** OmniCommand-SPEC.md Abschnitt 2b
