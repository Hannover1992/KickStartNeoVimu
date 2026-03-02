---
status: v1.0
version: "1.0"
created: 2026-02-28
updated: 2026-02-28
op: SprintMonitor
---

# /_S_Monitor — Sprint Monitor

```
╔══════════════════════════════════════╗
║  VERTRAG: /_S_Monitor               ║
╠══════════════════════════════════════╣
║  LIEST:                             ║
║    .claude/session-params.md        ║
║    (Worktree-Registry, YAML)        ║
║  SCHREIBT: nichts                   ║
║  RUFT AUF: /_S_FanOut (intern)     ║
╚══════════════════════════════════════╝
```

**Status:** v1.0
**Actor:** TEAM_LEAD
**Typ:** Monitoring-Loop (langlebig, periodisch)
**Modus:** READONLY (kein Schreiben auf Worktrees)

---

## Aufruf

```
/_S_Monitor [speed] [worktrees...]
```

| Parameter   | Bedeutung                                        |
|-------------|--------------------------------------------------|
| `speed`     | `slow` (300s) \| `normal` (60s, default) \| `fast` (20s) |
| `worktrees` | Optionaler Label-Filter, z.B. `V1-Param V3-SCI` |

**Beispiele:**
```bash
/_S_Monitor                        # normal (60s), alle Worktrees
/_S_Monitor slow                   # 300s Interval, alle Worktrees
/_S_Monitor fast                   # 20s Interval, alle Worktrees
/_S_Monitor normal V1-Param V3-SCI # 60s Interval, nur V1 + V3
/_S_Monitor fast V2-Audit          # 20s Interval, nur V2
```

---

## Verhalten

### Phase 0: Loop-Modus waehlen

Bevor der Monitor startet, fragt er den User nach dem Kontroll-Modus:

```
Sprint Monitor — Modus-Auswahl:

Option A (empfohlen): Nach jedem Durchlauf fragen "Weiter?"
  → Explizite User-Kontrolle pro Iteration
  → Kein echter Sleep noetig

Option B: Vollautomatisch mit Bash sleep {INTERVAL}s
  → Loop laeuft ohne Unterbrechung
  → Stoppen nur mit Ctrl+C

Welchen Modus moechtest du?
```

AskUserQuestion: "Loop-Modus?"
Options: ["Option A: Manuell (empfohlen)", "Option B: Vollautomatisch"]

- Antwort A: LOOP_MODE = "manual"
- Antwort B: LOOP_MODE = "auto"

---

### Phase 1: Initialisierung

**Schritt 1.1 — Argumente parsen:**
```
speed  = args[0] oder "normal"   # slow | normal | fast
filter = args[1:] oder []        # Optionale Label-Filter
```

**Schritt 1.2 — Speed validieren:**
```
WENN speed NICHT IN {slow, normal, fast}:
  WARN: "Unbekannter Speed '{speed}', verwende Fallback: normal"
  speed = "normal"

SPEED_MAP:
  slow   -> interval = 300
  normal -> interval = 60
  fast   -> interval = 20

interval = SPEED_MAP[speed]
```

**Schritt 1.3 — session-params.md lesen:**

Lese mit dem Read-Tool:
`C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V5-Monitor/.claude/session-params.md`

```
VERSUCH:
  params = Read ".claude/session-params.md"
  worktrees = parse_yaml(params).sprint.worktrees
  WENN worktrees leer:
    STOP: "FEHLER: session-params.md gelesen, aber keine Worktrees gefunden."
BEI FEHLER (Datei fehlt oder nicht lesbar):
  WARN: "WARNING: session-params.md nicht gefunden, nutze hardcoded Defaults"
  worktrees = HARDCODED_DEFAULTS (s.u.)
```

**Hardcoded Fallback-Defaults:**
```
V1-Param   -> C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V1-Param   | vorhaben/1-global-param
V2-Audit   -> C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V2-Audit   | vorhaben/2-kern-audit
V3-SCI     -> C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V3-SCI-Uebergang | vorhaben/3-sci-uebergang
V4-Mermaid -> C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V4-Mermaid | vorhaben/4-mermaid-first
V5-Monitor -> C:/Users/Administrator/Documents/Work/Code2/DCSRE_Azure/OmniCommand-V5-Monitor | vorhaben/5-sprint-monitor
```

**Schritt 1.4 — Filter anwenden:**
```
WENN filter nicht leer:
  worktrees = worktrees.filter(wt => wt.label IN filter)
  WENN worktrees leer:
    STOP: "FEHLER: Keine Worktrees nach Filter '{filter}'.
           Verfuegbar: V1-Param, V2-Audit, V3-SCI, V4-Mermaid, V5-Monitor"
```

**Schritt 1.5 — Willkommens-Meldung ausgeben:**
```
Sprint Monitor gestartet
  Speed:     {speed} ({interval}s Interval)
  Worktrees: {anzahl} ({labels kommagetrennt})
  Modus:     {LOOP_MODE}
  Stop:      Ctrl+C (Auto) oder 'Stop' antworten (Manuell)
```

---

### Phase 2: Monitor-Loop

```
iteration = 0

REPEAT (bis User stoppt):

  iteration += 1
  timestamp = jetzt()   # Format: YYYY-MM-DD HH:MM:SS
```

#### Schritt 2.1 — FanOut aufrufen

Rufe `/_S_FanOut` auf (intern, als Command-Referenz).

`/_S_FanOut` spawnt N haiku Worker PARALLEL (einen pro Worktree in `worktrees`).
Jeder Worker liest:
1. `{PATH}/INSTRUCTION.md` (limit=20) -> SCOPE_TEXT
2. `{PATH}/.claude/analysis/_manifest.md` (limit=50) -> PHASE_STRING
3. `git -C {PATH} log --oneline -1` -> COMMIT_HASH + COMMIT_MESSAGE

Warte auf alle Worker-Reports (max 30s Timeout).

**Timeout-Verhalten:** Worktrees ohne Report nach 30s erhalten:
```json
{ "label": "{LABEL}", "status": "BLOCKED", "phase": "UNKNOWN",
  "issue": "Worker timeout (>30s)", "lastCommit": "?", "scope": "N/A" }
```

#### Schritt 2.2 — Status-Mapping anwenden

Fuer jeden empfangenen Report: mappe `report.phase` auf `dashboardStatus`:

| PHASE_STRING          | dashboardStatus | Col3-Anzeige          |
|-----------------------|-----------------|-----------------------|
| `DONE`                | DONE            | `Phase: DONE`         |
| `POST-CYCLE`          | DONE            | `Phase: POST-CYCLE`   |
| `FINISHED`            | DONE            | `Phase: FINISHED`     |
| `IMPLEMENT`           | RUNNING         | `Phase: IMPLEMENT`    |
| `REVIEW`              | RUNNING         | `Phase: REVIEW`       |
| `CONCEPT`             | RUNNING         | `Phase: CONCEPT`      |
| `SPEC`                | RUNNING         | `Phase: SPEC`         |
| `INTEGRATE`           | RUNNING         | `Phase: INTEGRATE`    |
| `TEST`                | RUNNING         | `Phase: TEST`         |
| `REFACTOR`            | RUNNING         | `Phase: REFACTOR`     |
| `HYPOTHESE`           | RUNNING         | `Phase: HYPOTHESE`    |
| `OBSERVE`             | RUNNING         | `Phase: OBSERVE`      |
| `I_PIPELINE_RUNNING`  | RUNNING         | `Phase: I_PIPELINE_RUNNING` |
| `READY`               | IDLE            | `Phase: READY`        |
| `DESIGN`              | IDLE            | `Phase: DESIGN`       |
| `I_PIPELINE_READY`    | IDLE            | `Phase: I_PIPELINE_READY`   |
| `BLOCKED`             | BLOCKED         | `Issue: BLOCKED`      |
| `ERROR`               | BLOCKED         | `Issue: ERROR`        |
| `WAITING_*` (Muster)  | BLOCKED         | `Issue: WAITING`      |
| Manifest fehlt        | BLOCKED         | `Issue: No Manifest`  |
| Parse-Fehler          | BLOCKED         | `Issue: Parse Error`  |
| Worker-Timeout (>30s) | BLOCKED         | `Issue: Timeout`      |
| Pfad nicht gefunden   | UNKNOWN         | `Issue: Path Error`   |
| PHASE-Feld fehlt      | UNKNOWN         | `Issue: No PHASE`     |
| Unbekannter Wert      | UNKNOWN         | `Phase: {RAW_VALUE}`  |

Sekundaer-Check:
```
WENN dashboardStatus == RUNNING UND (jetzt - manifest_timestamp) > 24h:
  Pruefe Manifest auf BLOCKED/ERROR-Hinweise.
  WENN gefunden: dashboardStatus = BLOCKED (ueberschreibt RUNNING)
```

#### Schritt 2.3 — Dashboard rendern

Gib folgende ASCII-Box aus:

```
╔══════════════════════════════════════════╗
║  SPRINT MONITOR — {TIMESTAMP}           ║
╠══════════╦═══════════╦══════════════════╣
║ {LABEL}  ║ {STATUS}  ║ {PHASE_SHORT}   ║
║ {LABEL}  ║ {STATUS}  ║ {PHASE_SHORT}   ║
...
╚══════════╩═══════════╩══════════════════╝
Next check in: {INTERVAL}s ({speed} mode)
Iteration: {N} | Workers: {anzahl} | Done: {done} | Running: {running} | Idle: {idle} | Blocked: {blocked}
```

**Spalten-Spezifikation:**
| Spalte | Breite | Inhalt |
|--------|--------|--------|
| Col 1 (Label)  | 10 Zeichen | Worktree-Label, linksjustiert |
| Col 2 (Status) | 11 Zeichen | dashboardStatus, zentriert |
| Col 3 (Phase/Issue) | 17 Zeichen | Col3-Anzeige aus Status-Mapping, linksjustiert |

**Rendering-Pseudocode:**
```python
box_width = 42
PRINT "╔" + "═"*(box_width-2) + "╗"
header = f"  SPRINT MONITOR — {timestamp}"
PRINT "║" + header.ljust(box_width-2) + "║"
PRINT "╠" + "═"*10 + "╦" + "═"*11 + "╦" + "═"*17 + "╣"

FUER JEDEN report IN reports:
  label  = report.label.ljust(10)[:10]
  status = report.dashboardStatus.center(11)[:11]
  col3   = (f"Issue: {report.issue}" WENN report.issue
            SONST f"Phase: {report.phase}").ljust(17)[:17]
  PRINT "║" + label + "║" + status + "║" + col3 + "║"

PRINT "╚" + "═"*10 + "╩" + "═"*11 + "╩" + "═"*17 + "╝"
PRINT f"Next check in: {interval}s ({speed} mode)"
```

**Beispiel-Output (Iteration 1, normal mode):**
```
╔══════════════════════════════════════════╗
║  SPRINT MONITOR — 2026-02-28 14:30:15   ║
╠══════════╦═══════════╦══════════════════╣
║ V1-Param ║  RUNNING  ║ Phase: IMPLEMENT ║
║ V2-Audit ║   IDLE    ║ Phase: READY     ║
║ V3-SCI   ║   DONE    ║ Phase: POST-CYCLE║
║ V4-Merm. ║  BLOCKED  ║ Issue: Timeout   ║
║ V5-Monitor  RUNNING  ║ Phase: IMPLEMENT ║
╚══════════╩═══════════╩══════════════════╝
Next check in: 60s (normal mode)
Iteration: 1 | Workers: 5 | Done: 1 | Running: 2 | Idle: 1 | Blocked: 1
```

#### Schritt 2.4 — Warnung bei allen BLOCKED

```
WENN alle reports.dashboardStatus == "BLOCKED":
  PRINT "!!! WARNUNG: Alle Worktrees BLOCKED — pruefe Pfade und Manifeste. Loop laeuft weiter."
```

#### Schritt 2.5 — Naechster Durchlauf (Option A oder B)

**Option A (LOOP_MODE = "manual"):**
```
AskUserQuestion: "Iteration {N} abgeschlossen. Naechster Durchlauf?"
Options: ["Ja, weiter", "Stop"]

WENN "Stop":
  -> Goto Phase 3 (Beendigung)
WENN "Ja, weiter":
  -> Goto REPEAT
```

**Option B (LOOP_MODE = "auto"):**
```
PRINT "Warte {interval}s bis zum naechsten Durchlauf... (Ctrl+C zum Stoppen)"
BASH: sleep {interval}
-> Goto REPEAT
```

---

### Phase 3: Loop-Beendigung

```
PRINT "Sprint Monitor beendet nach {iteration} Durchlaeufen."
PRINT "Letzter Stand ({timestamp_letzter_durchlauf}):"
PRINT [letztes Dashboard erneut ausgeben]
PRINT "Zum Neustart: /_S_Monitor {speed}"
```

---

## Dashboard-Format (Detail)

**Gesamte Box-Breite:** 42 Zeichen (inkl. Raender)
**Farb-Mapping:** Kein Terminal-Farb-Code (Claude-Output ist Plain Text)
**Scrolling Output:** Jeder Durchlauf gibt eine neue Box aus. Alte Boxen bleiben im Scroll-Log sichtbar.

**Spalten (nochmal zusammengefasst):**
| Spalte | Breite | Werte | Kuerzel |
|--------|--------|-------|---------|
| Label  | 10 | V1-Param, V2-Audit, V3-SCI, V4-Mermaid, V5-Monitor | Ggf. kuerzen: `V4-Merm.` |
| Status | 11 | `RUNNING`, `IDLE`, `DONE`, `BLOCKED`, `UNKNOWN` | Zentriert |
| Phase/Issue | 17 | `Phase: IMPLEMENT`, `Issue: Timeout`, `Issue: Path Error` | Linksjustiert |

---

## Fehlerbehandlung

| Nr | Fehler | Verhalten |
|----|--------|-----------|
| F1 | `session-params.md` fehlt | Hardcoded Fallback-Liste (V1-V5), WARN ausgeben, Loop fortsetzen |
| F2 | Worktree-Pfad nicht erreichbar | Worker meldet `status=UNKNOWN`, `issue="Path Error"` im Dashboard |
| F3 | `INSTRUCTION.md` fehlt | Worker setzt `scope="NO-SCOPE"`, Status-Ermittlung laeuft weiter |
| F4 | `_manifest.md` nicht lesbar | Worker setzt `status=BLOCKED`, `issue="No Manifest"` |
| F5 | Worker sendet kein Report (Timeout) | Nach 30s: `status=BLOCKED`, `issue="Timeout"` im Dashboard |
| F6 | Alle Worker BLOCKED | Warnung ausgeben (`!!! WARNUNG`), Loop laeuft trotzdem weiter |
| F7 | `speed` nicht erkannt | WARN + Fallback auf `normal` (60s), kein Stop |
| F8 | Keine Worktrees nach Filter | STOP mit Fehlermeldung, Monitor beendet sich |
| F9 | User Ctrl+C (Option B) | Loop endet, letztes Dashboard bleibt sichtbar |
| F10 | User fragt waehrend Sleep (Option B) | Monitor ignoriert Anfrage bis Sleep endet (Ctrl+C zum Stoppen) |

---

## Technische Hinweise

**Loop-Mechanismus:**
- Option A (empfohlen): `AskUserQuestion` nach jedem Durchlauf gibt User explizite Kontrolle. Kein echter Sleep noetig — User wartet selbst.
- Option B: `Bash sleep {interval}` — vollautomatisch. User kann nur mit Ctrl+C stoppen.
- Beim Start wird immer erst nach dem Modus gefragt (Phase 0).

**FanOut-Aufruf:**
- `/_S_FanOut` wird als interner Command aufgerufen (Command-Referenz).
- `/_S_FanOut` spawnt seinerseits N haiku Worker PARALLEL via Task-Tool.
- Worker-Reports kommen per SendMessage (type="message", recipient="team-lead") zurueck.
- Schnittstelle: `/_S_FanOut` gibt aggregiertes JSON-Objekt zurueck (s. `_S_FanOut.md` Phase 4).

**Worker-Report-Format (von /_S_FanOut empfangen):**
```json
{
  "label": "V1-Param",
  "status": "RUNNING",
  "phase": "IMPLEMENT",
  "lastCommit": "abc1234 Fix: Param validation",
  "scope": "Global Parameter Orchestrator",
  "timestamp": "2026-02-28T14:30:15Z",
  "issue": null
}
```

**Fehlerfall-Report:**
```json
{
  "label": "V4-Mermaid",
  "status": "UNKNOWN",
  "phase": "N/A",
  "lastCommit": "?",
  "scope": "ERROR: Path not found",
  "timestamp": "2026-02-28T14:30:15Z",
  "issue": "Path not found"
}
```

**Performance-Uebersicht:**
| Modus  | Interval | FanOut-Aufrufe/h | Anmerkung |
|--------|----------|------------------|-----------|
| slow   | 300s     | 12               | Niedrig-Overhead |
| normal | 60s      | 60               | Standard-Balance |
| fast   | 20s      | 180              | Hoch, nur kurzzeitig |

---

## Vollstaendiger Ablauf (End-to-End)

```
t=0.0s   | User: /_S_Monitor normal
t=0.1s   | Phase 0: AskUserQuestion — Modus-Auswahl (A oder B)
t=0.2s   | Phase 1: Parse speed=normal, filter=[], interval=60
t=0.3s   | Phase 1: Read session-params.md -> 5 Worktrees geladen
t=0.4s   | Phase 1: Filter anwenden (leer -> alle 5)
t=0.5s   | Phase 1: Willkommens-Meldung ausgeben
t=0.6s   | Phase 2 (Iteration 1): Timestamp erfassen
t=0.7s   | Phase 2: /_S_FanOut aufrufen -> 5 haiku Worker PARALLEL starten
t=0.8-5s | Worker lesen Manifeste, INSTRUCTION.md, git log, senden Reports
t=5s     | Phase 2: Alle Reports empfangen (max 30s)
t=5.1s   | Phase 2: Status-Mapping anwenden
t=5.2s   | Phase 2: ASCII-Dashboard ausgeben
t=5.3s   | Phase 2: "Next check in: 60s (normal mode)"
t=5.4s   | OPTION A: AskUserQuestion "Weiter?" -> User antwortet "Ja, weiter"
         | OPTION B: Bash sleep 60 (blockiert 60s)
t=65s    | Phase 2 (Iteration 2): Timestamp erfassen -> REPEAT
...
```

---

## Voraussetzungen

| Nr | Voraussetzung | Fehlerbehandlung |
|----|---------------|-----------------|
| P1 | `.claude/session-params.md` existiert | Fallback auf Hardcoded-Defaults (F1) |
| P2 | Alle Worktree-Pfade erreichbar | UNKNOWN-Status fuer nicht erreichbare (F2) |
| P3 | Jeder Worktree hat `_manifest.md` | BLOCKED-Status wenn fehlt (F4) |
| P4 | `/_S_FanOut.md` Command existiert | Pflicht — ohne FanOut kein Monitor |
| P5 | Haiku-Worker-Pool verfuegbar | BLOCKED bei Spawn-Fehler |

---

**Erstellt:** 2026-02-28
**Version:** 1.0
**SPEC-Referenz:** OmniCommand-SPEC.md Abschnitt 2c
**Abhaengigkeiten:** session-params.md (A1), _S_FanOut.md (A2)
