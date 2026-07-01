---
name: _Pre_PR_orchestrate
description: Pre-PR Quality Gates - Team Lead Orchestrierung (9 Gates PARALLEL)
---

# /_Pre_PR_orchestrate - Team Lead Pre-PR Quality Gates

```yaml
status: active
version: 3.0.0
created: 2026-02-18
type: orchestration
team_based: true
```

---

## Vertrag

```
+===============================================================+
| META-COMMAND: /_Pre_PR_orchestrate                             |
+===============================================================+
|                                                                |
| ACTOR: TEAM LEAD (DU - die ausfuehrende Claude-Instanz)       |
| WORKER: bis zu 9 {ceiling}-Agents (1 pro Gate, PARALLEL)      |
|                                                                |
| ZWECK: Alle 9 Pre-PR Quality Gates PARALLEL ausfuehren.       |
|        Team Lead ermittelt Datei-Listen, spawnt Gate-Workers,  |
|        aggregiert Ergebnisse, verifiziert Build+Tests.         |
|                                                                |
| MODI (prePr-Parameter aus _session_params.md):                 |
|   report:  Readonly Scan → Presentation → interaktive Queue   |
|            → Auto-Learn Meta. KEINE Auto-Fixes, KEIN Build.   |
|   execute: Wie v2.0 (Auto-Fix + Build + Test). DEFAULT.       |
|                                                                |
| DIFF-BASIS: git diff develop...HEAD (IMMER!)                   |
|                                                                |
| GATES (9 Stueck, alle PARALLEL):                               |
|   1. Tests         → Test-Dateien      (Auto-Fix: JA)         |
|   2. Naming        → CS-Dateien        (Auto-Fix: JA)         |
|   3. Cleanup       → CS-Dateien        (Auto-Fix: JA)         |
|   4. Dokumentation → CS-Dateien        (Auto-Fix: JA)         |
|   5. Konstanten    → CS-Dateien        (Auto-Fix: TEIL)       |
|   6. Logging       → CS-Dateien        (Auto-Fix: JA)         |
|   7. Architektur   → CS-Dateien        (Auto-Fix: NEIN)       |
|   8. Analyzer      → .csproj Dateien   (Auto-Fix: JA)         |
|   9. Migration     → Migration-Dateien (Auto-Fix: NEIN)       |
|                                                                |
| MODELL: {ceiling} (alle Workers)                               |
| PARALLELISIERUNG: ALLE aktiven Gates GLEICHZEITIG              |
|                                                                |
| LIEST:                                                         |
|   - git diff develop...HEAD (Datei-Listen)                     |
|   - .claude/meta/codeKonvention/*.md (Regeln pro Gate)         |
|   - .claude/commands/_Pre_PR_*.md (Command-Specs)              |
|   - {VAULT}/_session_params.md (prePr Parameter)      |
|                                                                |
| SCHREIBT (execute-Modus):                                      |
|   - Auto-Fixes in CS/csproj Dateien (parallel!)                |
|   - Summary-Bericht (konsolidiert)                             |
|                                                                |
| SCHREIBT (report-Modus):                                       |
|   - .claude/review/prepr-findings-{BRANCH}-{DATE}.md (Log)    |
|   - .claude/meta/codeKonvention/*.md (Auto-Learn nach Queue)  |
|   - KEIN Edit an CS/csproj Dateien!                            |
|                                                                |
| PIPELINE:                                                      |
|   [/_I_diffAudit] → [/_Pre_PR_orchestrate] → [PR erstellen]   |
|                                                                |
+===============================================================+
```

---

## GLOBALE PARAMETER (/_param Override)

Lies `{VAULT}/_manifest.md` und suche nach GLOBAL_* Feldern.

Effektives Gate-Modell: `{ceiling}` (aus _session_params.md).
ceiling wird aus _session_params.md gelesen.

| Quelle | Wirkung |
|---|---|
| `_session_params.md` | difficulty steuert Gate-Anzahl, ceiling konfiguriert Gate-Modell |

**Gate-Skalierung nach difficulty:**

| difficulty | Active Gates | Modell | Besonderheit |
|---|---|---|---|
| easy | 3 (Tests, Naming, Cleanup) | {ceiling} | Ressourcen-sparsam |
| normal | 9 (alle) | {ceiling} | Standard |
| hard | 9 (alle) | {ceiling} | + verbose Analyse in Knowledge-Files |

{ceiling} = ceiling aus _session_params.md (Default: sonnet)

---

## Phase 0a: prePr-Modus erkennen (RF-A-001)

DU (Team Lead) liest den prePr-Parameter:

```
params = lies("{VAULT}/_session_params.md")
PREPR_MODE = params.prePr ?? "execute"

IF PREPR_MODE == "report":
  ACTIVE_MODE = "readonly"
  Ausgabe: "═══ Pre-PR Orchestrator v3.0 (REPORT — READONLY) ═══"
ELSE:
  ACTIVE_MODE = "execute"
  Ausgabe: "═══ Pre-PR Orchestrator v3.0 (EXECUTE) ═══"
  → Weiter mit unveraendertem v2.0 Ablauf (Phase 0 → 5)
```

## Phase 0c: BL-215 2-Phasen-Mode-Decision (NEU 2026-05-24)

```
# BL-215 Fix 2026-05-24: 2-Phasen-Refactor mit HiL-Check.
# Vorher: EXECUTE-Modus fixed Auto-Fix, REPORT-Modus reines Read-Only.
# Neu: 2-Phasen-Flow konditional auf GLOBAL_HIL.

global_hil = Read({VAULT}/_session_params.md).GLOBAL_HIL ?? "off"

IF global_hil == "off":
  TWO_PHASE_MODE = "EXECUTE_DIRECT"  # alter EXECUTE-Modus (Auto-Fix sofort)
  Logge: "[BL-215] HiL=off → EXECUTE_DIRECT Modus (Auto-Fix sofort wie heute)"
ELSE:
  TWO_PHASE_MODE = "DETECT_THEN_RESOLVE"
  Logge: "[BL-215] HiL=on → 2-Phasen-Modus (DETECT → User-Presentation → RESOLVE)"

# Phase A (DETECT): immer alle 9 Gates READ-ONLY scannen (Findings sammeln, kein Fix)
# - 9 Gates in --readonly-Modus spawnen
# - Findings im findings_collected[] sammeln

# IF TWO_PHASE_MODE == "DETECT_THEN_RESOLVE":
#   Phase A.5 (User-Presentation):
#     - Pro Finding: AskUserQuestion mit Optionen Apply | Skip | Discuss | Skip-Rest
#     - Sammle accepted_findings[] + rejected_findings[]
#     - VORHER-NACHHER-Tabelle vorbereiten
#
# Phase B (RESOLVE):
#   - Pro accepted_finding: Auto-Fix anwenden
#   - Pro rejected_finding: in Audit-Log "REJECTED"
#
# Phase B.5 (SemanticLibrary-Sync):
#   - Accepted Findings: R{N} in SemanticLibrary/_project/{LAYER}/naming-conv.md
#   - Rejected Findings: AUSNAHME-Block in derselben Datei
#   - Naechster Pre_PR-Lauf liest SemanticLibrary erst

# Phase C, D (existing): Build + Test, FAN_IN, etc.
# Phase D NEU: Vorher-Nachher-Tabelle mit Haekchen
```

**Scope-Boundary (BL-215 AK-3):** 2-Phasen-Refactor adressiert NUR Gates 2-6 (Naming/Cleanup/
Doku/Konstanten/Logging). Gate 7 (Architektur) bleibt EXECUTE-Modus (kein User-Haekchen,
Architektur ist in I-Phase abgeschlossen).

## Phase B.5: SemanticLibrary-Sync (NEU BL-215 AK-4, 2026-05-24)

```
# Nach Phase B (RESOLVE) — akzeptierte + abgelehnte Findings persistieren in
# SemanticLibrary fuer naechsten Pre_PR-Lauf.

IF TWO_PHASE_MODE == "DETECT_THEN_RESOLVE" AND |accepted_findings| > 0:
  FOR finding IN accepted_findings:
    layer = derive_layer(finding.file)  # z.B. BE-CONT, BE-DOMAIN, _generic
    target_file = f"{VAULT}/Libraries/SemanticLibrary/_project/{layer}/naming-conv.md"
    next_rule_id = next_available_R_id(target_file)
    rule_text = f"""
### R{next_rule_id}: {finding.problem_title}
- **Gate:** {finding.gate}
- **Severity:** {finding.severity}
- **Beschreibung:** {finding.problem}
- **Beispiel-Datei:** {finding.file}:{finding.line}
- **Herkunft:** Auto-Learn Pre_PR ({DATE}) Branch {BRANCH}
- **Akzeptiert via:** User-Haekchen Phase A.5
"""
    APPEND target_file: rule_text
    Logge: "[BL-215 B.5] R{next_rule_id} → {target_file}"

  FOR finding IN rejected_findings:
    layer = derive_layer(finding.file)
    target_file = f"{VAULT}/Libraries/SemanticLibrary/_project/{layer}/naming-conv.md"
    APPEND target_file (AUSNAHME-Block):
"""
### AUSNAHME: {finding.problem_title}
- **Gate:** {finding.gate}
- **Betrifft:** {finding.file_pattern}
- **Begruendung:** {user_comment or "ohne expliziten Grund abgelehnt"}
- **Herkunft:** Auto-Learn Pre_PR ({DATE}) Branch {BRANCH}
"""
    Logge: "[BL-215 B.5] AUSNAHME -> {target_file}"

  Naechster Pre_PR-Lauf liest SemanticLibrary erst (vor Gate-Spawning) und
  passt Regeln/Ausnahmen entsprechend an.

  Manifest-Update:
    BERATER_OUTPUTS.semantic_library_sync = {
      accepted_count: N,
      rejected_count: M,
      synced_files: [list of naming-conv.md paths],
      ts: ISO
    }
```

## Phase D: Vorher-Nachher-Audit-Trail (NEU BL-215 AK-5, 2026-05-24)

```
# Erweitert Phase 5.1 Summary-Report mit Vorher/Nachher-Tabelle bei Haekchen-Modus.

IF TWO_PHASE_MODE == "DETECT_THEN_RESOLVE":
  vor_nach_table = []
  FOR finding IN all_findings:
    status = "Apply" if finding.id in accepted_findings else (
             "Skip" if finding.id in rejected_findings else "Defer")
    applied = "Yes" if finding.id in actually_applied else "No"
    outcome = (
      "Code edit" if applied == "Yes" and finding.gate != "Architektur"
      else "Logged only" if status == "Skip"
      else "Deferred-Queue" if status == "Defer"
      else "Failed-Edit"
    )
    vor_nach_table.append({
      n: finding.index,
      finding: finding.problem_title,
      user_decision: status,
      applied: applied,
      outcome: outcome,
    })

  # Schreibe Audit-Datei
  audit_file = f".claude/review/prepr-2phasen-{BRANCH}-{DATE}.md"
  Write audit_file:
    """
    # Pre-PR 2-Phasen Audit-Trail — {BRANCH} {DATE}

    ## Findings Vorher/Nachher

    | # | Finding | User-Decision | Applied? | Outcome |
    |---|---------|---------------|----------|---------|
    """
    FOR row IN vor_nach_table:
      "| {row.n} | {row.finding} | {row.user_decision} | {row.applied} | {row.outcome} |"

    Add Summary:
    """
    ## Summary
    - Total Findings: {|all_findings|}
    - Apply: {accept_count}
    - Skip: {reject_count}
    - Defer: {defer_count}
    - SemanticLibrary R-Rules added: {r_rules_count}
    - SemanticLibrary AUSNAHMEN added: {ausnahme_count}
    """

  Logge: "[BL-215 D] Vorher-Nachher-Audit -> {audit_file}"

  Manifest-Update:
    BERATER_OUTPUTS.pre_pr_audit_2phasen = {
      audit_file: audit_file,
      total: N,
      apply: a, skip: s, defer: d,
      ts: ISO
    }
```

**REPORT-MODUS Invarianten (RF-A-002, RF-A-003, RF-A-005):**
```
VERBOTEN im Report-Modus:
  - Edit-Tool auf CS/csproj/Migration-Dateien
  - dotnet clean, dotnet build, dotnet test, dotnet format
  - Jeder Shell-Command ausser: git diff develop...HEAD
  - Dateien lesen ausserhalb der Dateiliste (ausser .claude/meta/ fuer Regeln)

ERLAUBT im Report-Modus:
  - Read-Tool auf Dateien in der Dateiliste
  - Read-Tool auf .claude/meta/codeKonvention/*.md
  - Read-Tool auf .claude/commands/_Pre_PR_*.md
  - Write-Tool NUR auf: .claude/review/prepr-findings-*.md
  - Write-Tool NUR auf: .claude/meta/codeKonvention/*.md (nach interaktiver Phase)
```

---

## Warum parallel statt sequentiell?

```
ALT (v1.0): Gates SEQUENTIELL wegen Auto-Fix-Kaskade.
  Problem: 27 Minuten Laufzeit. Overkill - Konflikte sind selten.

NEU (v2.0): Gates PARALLEL. Build+Test am Ende als Safety Net.
  - Tests bearbeitet NUR Test-Dateien → kein Konflikt
  - Analyzer bearbeitet NUR .csproj → kein Konflikt
  - Migration/Architektur sind READ-ONLY → kein Konflikt
  - Naming/Cleanup/Doku/Konstanten/Logging editieren verschiedene
    ASPEKTE derselben CS-Dateien (Namen vs Struktur vs Kommentare
    vs Strings vs Logging) → Konflikte extrem selten
  - Build+Test am Ende fangt die seltenen Konflikte ab
```

---

## Phase 0: Datei-Listen + Scope

DU (Team Lead) fuehrst aus:

```bash
# 1. Alle CS-Dateien
git diff --name-only develop...HEAD -- "*.cs"

# 2. Test-Dateien separieren
git diff --name-only develop...HEAD -- "*.cs" | grep -i "test"

# 3. Non-Test CS-Dateien
git diff --name-only develop...HEAD -- "*.cs" | grep -vi "test"

# 4. .csproj Dateien
git diff --name-only develop...HEAD -- "*.csproj"

# 5. Migration-Dateien
git diff --name-only develop...HEAD -- "*Migrations/*.cs"
```

**Gate-Zuordnung + SKIP:**

| Gate | Dateien | Skip wenn |
|------|---------|-----------|
| Tests | Test-Dateien | 0 Test-Dateien |
| Naming..Architektur | Alle CS | 0 CS-Dateien |
| Analyzer | .csproj | 0 csproj-Dateien |
| Migration | Migrations | 0 Migration-Dateien |

**AUSGABE:**
```
═══ Pre-PR Orchestrator v2.0 (PARALLEL) ═══

DIRTY-SCOPE:
  CS gesamt:    {N} Dateien
  Test-Dateien: {T} Dateien
  Non-Test:     {NT} Dateien
  .csproj:      {P} Dateien  → {SKIP wenn 0}
  Migrations:   {M} Dateien  → {SKIP wenn 0}

  Gates aktiv:  {X}/9
  Gates SKIP:   {Y} (keine Dateien)
```

---

## Phase 0b: Gate-Selektor (difficulty-basiert)

Bestimme ACTIVE_GATES basierend auf effektiver difficulty:

```
IF effektiv_difficulty == "easy":
  ACTIVE_GATES = [gate_tests, gate_naming, gate_cleanup]
  GATE_LIST = "3 Gates (Tests, Naming, Cleanup)"
  PROMPT_VARIANT = "standard"
ELSE:  (normal oder hard)
  ACTIVE_GATES = [alle 9 Gates]
  GATE_LIST = "alle 9 Gates"
  PROMPT_VARIANT = IF difficulty == "hard" THEN "extended" ELSE "standard"
```

TOP_3_GATES (fuer easy):
  1. gate_tests: Testabdeckung und Testqualitaet
  2. gate_naming: Naming-Konventionen und Lesbarkeit
  3. gate_cleanup: Code-Cleanup und offensichtliche Probleme

Spawne nur die Gates in ACTIVE_GATES.

---

## Phase 1: Team Setup

### 1.1 Team erstellen

```
TeamCreate:
  team_name: "pre-pr"
  description: "Pre-PR Quality Gates - Parallel Execution"
```

### 1.2 Tasks erstellen (1 pro aktivem Gate)

```
Pro aktivem Gate → TaskCreate:
  subject: "Gate {N}: {NAME}"
  description: |
    Quality Gate: /_Pre_PR_{NAME}
    Knowledge: .claude/meta/codeKonvention/{name}.md
    Command: .claude/commands/_Pre_PR_{NAME}.md
    Dateien: [LISTE]
    Auto-Fix: {JA/NEIN/TEIL}
  activeForm: "Running {NAME}"
```

KEINE Abhaengigkeiten zwischen Tasks (alle parallel)!

### 1.3 Workers spawnen - ALLE IN EINER MESSAGE

```
Pro aktivem Gate → Task tool (PARALLEL in einer Message!):
  name: "gate-{name}"
  subagent_type: "general-purpose"
  model: "{ceiling}"
  team_name: "pre-pr"
  mode: "bypassPermissions"
  prompt: [KURZLEBIG_PROMPT mit Gate-spezifischen Daten]
```

**KRITISCH:** Alle Task-Calls in EINER Message fuer maximale Parallelitaet!

---

## KURZLEBIG_PROMPT: Pre-PR Gate Worker (Phase 2)

```
Du bist ein Pre-PR Quality Gate Worker.
Agent-Name: gate-{name}
Team: pre-pr

═══ DEIN AUFTRAG ═══

Genau 1 Quality Gate ausfuehren, dann fertig.

Gate:              {N}: {NAME}
Knowledge-File:    {WORKTREE}/.claude/meta/codeKonvention/{name}.md
Command-Spec:      {WORKTREE}/.claude/commands/_Pre_PR_{NAME}.md
Auto-Fix:          {JA|NEIN|TEIL}
Task-ID:           {TASK_ID}
Projekt:           {WORKTREE}

Zu pruefende Dateien:
{DATEI_LISTE}

═══ SCHRITTE ═══

0. TaskUpdate {TASK_ID} status=in_progress

1. Knowledge-File lesen ({WORKTREE}/.claude/meta/codeKonvention/{name}.md)
   → Falls nicht vorhanden: SendMessage FEHLER an "team-lead", TaskUpdate FAIL, STOP

2. Command-Spec lesen ({WORKTREE}/.claude/commands/_Pre_PR_{NAME}.md)
   → Die Spec definiert deine Prueflogik

3. Dateien SEQUENTIELL pruefen (max 10 pro Batch):
   - Read jede Datei einzeln
   - Gegen Regeln aus Knowledge-File pruefen
   - Findings sammeln: Datei:Zeile:Regel:Problem
   - File-Read-Fehler → WARNUNG, naechstes File
   - NOCH KEINE Fixes in diesem Schritt! Erst ALLE scannen.

4. Auto-Fix anwenden (nur wenn Auto-Fix = JA oder TEIL):
   - Pro Finding: Edit-Tool anwenden
   - Success → FIXED++
   - Fehler → BLOCKER++ (kein Retry)

5. Status bestimmen:
   - PASS:  BLOCKER == 0 AND WARNUNG == 0
   - WARN:  BLOCKER == 0 AND WARNUNG > 0
   - FAIL:  BLOCKER > 0

6. TaskUpdate {TASK_ID} status=completed

7. SendMessage an "team-lead":
   "Gate {N} ({NAME}): {PASS|WARN|FAIL}
    Dateien: {TOTAL} geprueft
    CLEAN: {C} | FIXED: {F} | BLOCKER: {B} | WARNUNG: {W}

    [Falls BLOCKER oder WARNUNG > 0, max 10 Findings:]
    BLOCKER: {Datei}:{Zeile} [{Regel}] {Problem}
    WARNUNG: {Datei}:{Zeile} [{Regel}] {Problem}
    FIXED:   {Datei}:{Zeile} [{Regel}] → Auto-Fix angewendet

    [Falls > 10: '...und {N-10} weitere.']"

═══ REGELN ═══

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- NUR dieses eine Gate, dann fertig
- Beruehre keine Dateien ausserhalb deiner Liste
- Absolute Pfade: {WORKTREE}/...
- Andere Gates pruefen gleichzeitig dieselben Dateien
  → Falls Auto-Fix-Konflikt: WARNUNG statt Fehler, kein Retry
- Bei Unsicherheit: lieber WARNUNG melden als falschen Auto-Fix
```

---

## KURZLEBIG_PROMPT: Pre-PR Gate Worker — REPORT-MODUS (Phase 2b)

NUR bei ACTIVE_MODE == "readonly". Ersetzt den Standard-KURZLEBIG_PROMPT.

```
Du bist ein Pre-PR Quality Gate Worker im REPORT-MODUS.
Agent-Name: gate-{name}-report
Team: pre-pr

═══ DEIN AUFTRAG ═══

Genau 1 Quality Gate ausfuehren. NUR LESEN und FINDINGS MELDEN.
KEIN Edit, KEIN Fix, KEIN Shell-Command ausser git diff.

Gate:              {N}: {NAME}
Knowledge-File:    {WORKTREE}/.claude/meta/codeKonvention/{name}.md
Command-Spec:      {WORKTREE}/.claude/commands/_Pre_PR_{NAME}.md
MODE:              READONLY (KEIN Auto-Fix!)
Task-ID:           {TASK_ID}
Projekt:           {WORKTREE}

Zu pruefende Dateien:
{DATEI_LISTE}

═══ SCHRITTE ═══

0. TaskUpdate {TASK_ID} status=in_progress

1. Knowledge-File lesen ({WORKTREE}/.claude/meta/codeKonvention/{name}.md)
   → Falls nicht vorhanden: SendMessage FEHLER an "team-lead", TaskUpdate FAIL, STOP

2. Command-Spec lesen ({WORKTREE}/.claude/commands/_Pre_PR_{NAME}.md)
   → Die Spec definiert deine Prueflogik

3. Dateien SEQUENTIELL pruefen (max 10 pro Batch):
   - Read jede Datei einzeln (NUR Read-Tool!)
   - Gegen Regeln aus Knowledge-File pruefen
   - Findings sammeln: Datei:Zeile:Regel:Severity:Problem

4. KEIN AUTO-FIX. KEIN EDIT. Schritt 4 entfaellt komplett.

5. Status bestimmen:
   - CLEAN: 0 Findings
   - WARN:  Nur WARNUNG-Findings
   - FAIL:  Mindestens 1 BLOCKER-Finding

6. TaskUpdate {TASK_ID} status=completed

7. SendMessage an "team-lead" (STRUKTURIERT fuer Aggregation):
   "REPORT Gate {N} ({NAME}): {CLEAN|WARN|FAIL}
    Dateien: {TOTAL} geprueft
    BLOCKER: {B} | WARNUNG: {W}

    FINDINGS:
    [{DATEI}:{ZEILE}] [{REGEL}] [{BLOCKER|WARNUNG}] {Problem}
    [{DATEI}:{ZEILE}] [{REGEL}] [{BLOCKER|WARNUNG}] {Problem}
    ...

    [Falls > 20: '...und {N-20} weitere.']"

═══ REGELN ═══

- KEIN Edit-Tool, KEIN Write-Tool (ausser Finding-Datei wenn Team Lead vorgibt)
- KEIN git commit, KEIN git push
- KEIN dotnet, KEIN Shell-Command ausser git diff
- KEIN Sub-Agent spawnen (W7-Constraint)
- NUR dieses eine Gate, dann fertig
- Beruehre keine Dateien ausserhalb deiner Liste
- NUR Read-Zugriff auf Dateien
- Absolute Pfade: {WORKTREE}/...
```

---

## Phase 3: Team Lead Monitoring

### 3.1 Auf alle Workers warten

```
LOOP (bis alle Gates completed):
  - Worker-Messages empfangen
  - Gate-Ergebnisse sammeln
  - Fortschritt tracken: "{X}/{Y} Gates abgeschlossen"
```

### 3.2 Ergebnisse aggregieren

Pro Gate sammeln:
- Status: PASS / WARN / FAIL
- Zahlen: Dateien / Clean / Fixed / Blocker / Warnung
- Finding-Details (fuer Summary)

---

## Phase 3.5: Finding-Aggregation + Persistenz (NUR report-Modus, RF-B-001)

**SKIP bei execute-Modus** (weiter mit Phase 4).

Nach ALLEN Gates abgeschlossen (alle Worker-Messages empfangen):

### 3.5.1 Findings konsolidieren

Team Lead sammelt alle FINDINGS aus Worker-Messages und schreibt:

`.claude/review/prepr-findings-{BRANCH}-{DATE}.md`

```markdown
---
type: prepr-findings
branch: {BRANCH}
date: {DATE}
mode: report
gates_total: {N}
gates_active: {X}
findings_total: {TOTAL_FINDINGS}
blocker: {TOTAL_BLOCKER}
warnung: {TOTAL_WARNUNG}
status: OPEN
---

# Pre-PR Findings Report — {BRANCH} ({DATE})

## Summary

| # | Gate           | Status | Dateien | Blocker | Warn | Findings |
|---|----------------|--------|---------|---------|------|----------|
| 1 | Tests          | ...    | ...     | ...     | ...  | ...      |
| ...                                                               |

## Findings pro Gate

### Gate {N}: {NAME} ({CLEAN|WARN|FAIL})

| # | Datei:Zeile | Regel | Severity | Problem | Status |
|---|-------------|-------|----------|---------|--------|
| 1 | {DATEI}:{ZEILE} | {REGEL} | {BLOCKER|WARNUNG} | {Problem} | OPEN |
| 2 | ...                                                          |

[Wiederholen fuer jedes Gate mit Findings]

## Queue

[Wird in Phase 6 befuellt — alle OPEN Findings werden Queue-Items]

## Protokoll

[Wird in Phase 6 befuellt — Entscheidungen der interaktiven Phase]
```

### 3.5.2 Finding-Log schreiben

```
Write-Tool: .claude/review/prepr-findings-{BRANCH}-{DATE}.md
Inhalt: konsolidierter Report (siehe Format oben)
```

**Weiter mit Phase 5a (/_presentation), NICHT Phase 4.**

---

## Phase 4: Build + Test Verification

**SKIP bei report-Modus** (ACTIVE_MODE == "readonly"). Weiter mit Phase 5a.

Nach ALLEN Gates abgeschlossen:

```bash
# 1. Build
dotnet build {SOLUTION_PATH}
# Erwartung: 0 Errors

# 2. Tests
dotnet test {SOLUTION_PATH}
# Erwartung: 0 FAIL
```

### 4.1 Build OK

→ Weiter mit Phase 5 (Summary)

### 4.2 Build FAIL (Konflikt-Erkennung)

Falls Build nach parallelen Auto-Fixes fehlschlaegt:

1. Identifiziere Fehler-Dateien aus Build-Output
2. Pruefe: Wurden diese Dateien von MEHREREN Gates editiert?
3. Falls ja: Das sind Konflikt-Dateien

**Konflikt-Aufloesung:**
```
AUSGABE:
  "Build-Fehler nach parallelen Auto-Fixes."
  "Konflikte in {N} Dateien: {LISTE}"
  "Empfehlung: git restore {DATEIEN} → betroffene Gates sequentiell re-run"
```

---

## Phase 4b: FAN_IN — Norm-Evolution-Schwellenwert-Pruefung (RF-EV-001, RF-EV-003)

**SKIP bei report-Modus** (ACTIVE_MODE == "readonly"). FAN_IN laeuft NUR im execute-Modus.

Nach Abschluss aller Gates und VOR dem Summary Report: Prüfe ob wiederholte identische
Findings auf eine Norm-Grenze hinweisen (W217 — Evidenz-Feedback-Loop).

### 4b.1 Schwellenwert-Zaehler (>=3 identische Findings)

```
FAN_IN-Algorithmus:

1. Sammle alle Findings aus Gate-Ergebnissen (BLOCKER + WARNUNG):
   Fuer jedes Finding: { gate: N, regel: R, typ: "BLOCKER"|"WARNUNG" }

2. Gruppiere nach (gate, regel) — identische Findings = gleiche Gate+Regel-Kombination:
   findings_count[(gate, regel)] += 1

3. Pruefe Schwellenwert: Gibt es Gruppen mit findings_count >= 3?
   → NEIN: Kein Norm-Evolution-Signal → weiter mit Phase 5
   → JA:   Norm-Evolution-Kandidaten erstellen (Schritt 4b.2)

   BEISPIEL:
   Gate 7 (Architektur), Regel R3 (Provider-Pattern) → 5 Vorkommen
   → Schwellenwert ueberschritten: Kandidat erstellen

4. WICHTIG: Dies ist kein sofortiger Norm-Aenderungs-Mechanismus.
   Es ist ein SIGNAL fuer den User. Die Norm selbst aendert sich
   nur nach expliziter Entscheidung (/_R_evidence mit Typ pattern_evolution).
```

### 4b.2 Norm-Evolution-Kandidat erstellen

Fuer jede Gruppe mit findings_count >= 3:

```
Parking-Lot Eintrag APPENDEN an {VAULT}/_parking-lot.md:

---
[NORM-EVOLUTION-KANDIDAT] {DATUM}
Gate:    {N} ({NAME})
Regel:   {REGEL}
Typ:     BLOCKER | WARNUNG
Anzahl:  {COUNT}x identisches Finding in diesem Pre-PR-Lauf

Beobachtung: Regel "{REGEL}" in Gate {NAME} wurde {COUNT}x verletzt.
Schwellenwert >=3 ueberschritten → moegliche Norm-Grenze erreicht.

Empfohlene Aktion:
  → /_R_evidence erstellen mit Typ: pattern_evolution
  → Kausalkette: "Norm {REGEL} systematisch verletzt → Grenze identifiziert → Norm-Update pruefen"
  → Oder: JUSTIFY (Abweichung ist projektspezifisch gerechtfertigt)

pattern_evolution: true
source: _Pre_PR_orchestrate FAN_IN
---
```

**Ausgabe (Summary-Vorbereitung):**
```
FAN_IN Norm-Evolution-Analyse:
  Findings gesamt: {TOTAL}
  Gruppen (gate+regel): {UNIQUE}
  Schwellenwert-Treffer (>=3): {CANDIDATES}

  [Falls CANDIDATES > 0:]
  Norm-Evolution-Kandidaten:
    - Gate {N} ({NAME}), Regel {R}: {COUNT}x (→ Parking-Lot eingetragen)
    - ...
  → Details: {VAULT}/_parking-lot.md
```

---

## Phase 4c: Pattern-Battle-Test Auswertung (RF-PT6, W257)

Nach FAN_IN (Phase 4b) und VOR Summary Report (Phase 5).

**Zweck:** DRAFT-Patterns die alle 9 Quality Gates ueberlebt haben als Battle-Test-Kandidaten
identifizieren. Bei HiL-Bestaetigung: DRAFT→PROMOTED Transition ausfuehren.

### 4c.1 Vorpruefung

```
1. Pruefe: .claude/wissen/pattern-usage.log existiert
   → NEIN: Phase 4c SKIP (Graceful Degradation AC-PT6-4)
     Log: "Phase 4c SKIP: pattern-usage.log nicht vorhanden"
     → Weiter mit Phase 5

2. Pruefe: DRAFT-Patterns in .claude/patterns/_pattern-library.md vorhanden
   → NEIN: Phase 4c SKIP
     Log: "Phase 4c SKIP: Keine DRAFT-Patterns in _pattern-library.md"
     → Weiter mit Phase 5
```

### 4c.2 DRAFT-Filter

```
1. Lese .claude/patterns/_pattern-library.md (oder Cluster-Verzeichnisse wenn Multi-File)
2. Filtere Patterns mit Status: DRAFT
   → Extrahiere: Pattern-ID, Pattern-Name, Layer, Cluster
3. Filtere auf Patterns deren Cluster/Layer im aktuellen Feature-Run beruehrt wurde:
   Abgleich: Pattern-Layer (z.B. BE-MID) vs. geaenderte Dateien-Layer aus Phase 0

   Ergebnis: DRAFT_CANDIDATES = [{pattern_id, pattern_name, layer, cluster}]
```

### 4c.3 Battle-Test Auswertung

```
Fuer jedes Pattern in DRAFT_CANDIDATES:

1. Pruefe: Alle 9 Gates PASS fuer Dateien im Pattern-Cluster/Layer?
   Quelle: Gate-Ergebnisse aus Phase 3 (gate_results[])

   → ALLE Gates PASS (BLOCKER == 0 fuer Pattern-Layer-Dateien):
     Pattern ist battle_test_candidate
   → Mindestens 1 Gate FAIL/BLOCKER fuer Pattern-Layer-Dateien:
     Pattern bleibt DRAFT (kein Fehler, nur nicht promoted)
     Finding: "Pattern {ID} hat Gate {N} nicht bestanden (BLOCKER in {Datei})"

2. Scope-Abgrenzung (AC-PT6-3):
   - Code/Command-Patterns (P-BE-*, P-FE-*, P-CMD-*, P-TEST-*): JA (auswerten)
   - Model-meta-Patterns (W{n}-Schema, SRS-Formel): NEIN (meta-Ebene, uebersprungen)

Ergebnis: BATTLE_TESTED = [patterns die alle Gates bestanden haben]
          BATTLE_FAILED = [patterns die mindestens 1 Gate nicht bestanden haben]
```

### 4c.4 HiL-Bestaetigung (AC-PT6-5)

```
Falls len(BATTLE_TESTED) > 0:

  AUSGABE (AskUserQuestion):
  "Pattern-Battle-Test: {N} DRAFT-Pattern(s) haben alle 9 Gates bestanden.

   Kandidaten fuer PROMOTED:
   | # | Pattern-ID | Pattern-Name | Layer | Finding-Count |
   |---|------------|--------------|-------|---------------|
   | 1 | {ID}       | {Name}       | {L}   | 0             |

   Soll(en) diese Pattern(s) auf PROMOTED gesetzt werden? (ja/nein/defer)"

  Optionen:
  → ja:    Fuer jedes Pattern:
           - pattern-usage.log APPEND (AC-PT6-2):
             "{DATUM} | {pattern-id} | {feature} | -- | BATTLE_PASSED | pre-pr-battletest"
           - Status in _pattern-library.md: DRAFT → PROMOTED
             (via _PT_update.md Transition-Matrix: DRAFT→PROMOTED erlaubt)
  → nein:  Pattern bleibt DRAFT
           - pattern-usage.log APPEND:
             "{DATUM} | {pattern-id} | {feature} | -- | BATTLE_DECLINED | pre-pr-battletest"
  → defer: Parking-Lot Eintrag erstellen
           - APPEND an {VAULT}/_parking-lot.md:
             "[BATTLE-TEST-DEFER] {DATUM} Pattern {ID}: Alle Gates PASS, User deferred"

KEIN Auto-PROMOTED (AC-PT6-5, ADR-PL-008 Invariante).

Falls len(BATTLE_TESTED) == 0 AND len(BATTLE_FAILED) > 0:
  Log: "Phase 4c: {N} DRAFT-Patterns getestet, alle FAILED (Findings vorhanden)"
  → Kein HiL noetig, weiter mit Phase 5

Falls len(DRAFT_CANDIDATES) == 0:
  Log: "Phase 4c: Keine DRAFT-Patterns im betroffenen Layer"
  → Weiter mit Phase 5
```

### 4c.5 Manifest-Update

```
Falls PROMOTED Patterns vorhanden (HiL = ja):
  battle_test_candidates: [{Pattern-IDs der BATTLE_TESTED}]
  battle_test_promoted: [{Pattern-IDs die User mit "ja" bestaetigt hat}]
  battle_test_date: {DATUM}

Falls BATTLE_FAILED vorhanden:
  battle_test_failed: [{Pattern-IDs mit Gate-Failures}]
  battle_test_failed_gates: [{Gate-Nummern die FAIL waren}]

Falls Phase 4c SKIP:
  battle_test_skip: true
  battle_test_skip_reason: "{Grund: keine pattern-usage.log | keine DRAFT-Patterns}"
```

---

## Phase 4d: SkillLoadSelfTest (BL-159 PL-6-01 + PL-6-07)

**Zweck (BL-159 AK-3 BLOCKER-Verhalten W7 + AK-4 audit_hook skill_loaded):**
Process-Self-Test pro batch — validiert dass JEDER gespawnte Batch-Worker
seinen Skill ueber `Skill()`-Tool geladen hat (nicht via `Read(*/commands/_*.md)`).
Erkennt Mega-Agent-Verstoesse Post-Hoc anhand `audit.jsonl skill_loaded`-Events.

**Einschub-Strategie (PL-6-07):**
LAEUFT NACH Phase 4c (Pattern-Battle-Test Auswertung) und VOR Phase 5
(Summary + Shutdown). Failure ist BLOCKER — stoppt Pre-PR Gate.

**Trigger:** Immer im execute-Modus. Bei report-Modus SKIP (kein Spawn-Pattern
zu pruefen — Workers liefen READONLY ohne Skill-Load-Tracking).

### 4d.1 Vorpruefung

```
1. Pruefe: ACTIVE_MODE == "execute"
   → NEIN (report-Modus): Phase 4d SKIP
     Logge: "Phase 4d SKIP: report-Modus (kein Skill-Load-Self-Test noetig)"
     → Weiter mit Phase 5

2. Pruefe: .claude/audit/audit.jsonl existiert
   → NEIN: Phase 4d FAIL (Audit-Hook nicht aktiv)
     Logge: "Phase 4d FAIL: audit.jsonl fehlt — Audit-Hook nicht aktiv (BL-159 AK-4)"
     → BLOCKER, Pre-PR FAIL

3. Bestimme batch_window:
   batch_start = Phase 1 TeamCreate-Timestamp (Beginn dieses Pre-PR-Laufs)
   batch_end   = Phase 4c Abschluss-Timestamp (jetzt)
```

### 4d.2 SKILL_LOAD-Events pro Worker validieren

```
1. Lies audit.jsonl, filter:
   - event.ts IN [batch_start, batch_end]
   - event.type IN ["skill_loaded", "WORKER_SPAWN", "HANDOFF"]

2. Pro WORKER_SPAWN-Event extrahiere worker_id:
   spawned_workers = {worker_id, gate_name, spawn_ts}

3. Pro spawned_worker pruefe ob ein passendes skill_loaded-Event existiert:
   - skill_loaded.worker_id == worker_id
   - skill_loaded.load_method == "skill"  (NICHT "read" oder "other")
   - skill_loaded.ts > worker.spawn_ts

4. Klassifiziere:
   - PASS:  Skill-Load via Skill()-Tool nachweisbar
   - FAIL:  load_method == "read"   → Mega-Agent-Verstoss (PL-6-04 Test-Plan-Pattern)
   - FAIL:  load_method == "other"  → unbekannte Lade-Methode
   - FAIL:  kein skill_loaded-Event → Worker hat Skill nicht geladen
```

### 4d.3 Status bestimmen + Audit-Report

```
violations = [worker FOR worker IN spawned_workers IF worker.status == "FAIL"]

IF violations.length == 0:
  status = "PASS"
  Logge: "Phase 4d PASS: {N} Worker, alle Skill-Loads via Skill()-Tool nachweisbar"
ELSE:
  status = "BLOCKER"
  audit_jsonl_append({
    type: "SKILL_LOAD_SELF_TEST_FAIL",
    pre_pr_run_id: {RUN_ID},
    violations: [{worker_id, gate, load_method, reason}],
    timestamp: ISO
  })
  Logge: "Phase 4d BLOCKER: {N} Worker mit Skill-Load-Verstoss"
  FUER v IN violations:
    Logge: "  [BLOCKER] Worker {v.worker_id} (Gate {v.gate}): load_method={v.load_method}, {v.reason}"
```

### 4d.4 Manifest-Update

```
selftest_status: {PASS|BLOCKER}
selftest_workers_total: {N}
selftest_violations: [{worker_id, gate, load_method}]
selftest_date: {DATUM}
```

### 4d.5 Pre-PR-Gate-Entscheidung

```
IF status == "BLOCKER":
  Pre-PR Gate FAIL — Rollback-Hinweis ausgeben (Synergie mit PL-6-03)
  → KEINE Weiterfahrt zu Phase 5 Summary-PASS
  → Phase 5 Summary mit Gesamtstatus FAIL

IF status == "PASS":
  → Weiter mit Phase 5 (Summary + Shutdown)
```

---

## Phase 5: Summary + Shutdown

### 5.1 Summary Report

```markdown
# Pre-PR Quality Gate Summary

**Branch:** {BRANCH}
**Datum:** {DATE}
**Modus:** PARALLEL (v2.0)
**Diff-Basis:** develop...HEAD
**Dateien:** {N} CS + {P} csproj + {M} Migrations

## Gate-Ergebnisse

| # | Gate           | Status | Dateien | Clean | Fixed | Blocker | Warn |
|---|----------------|--------|---------|-------|-------|---------|------|
| 1 | Tests          | ...    | ...     | ...   | ...   | ...     | ...  |
| 2 | Naming         | ...    | ...     | ...   | ...   | ...     | ...  |
| 3 | Cleanup        | ...    | ...     | ...   | ...   | ...     | ...  |
| 4 | Dokumentation  | ...    | ...     | ...   | ...   | ...     | ...  |
| 5 | Konstanten     | ...    | ...     | ...   | ...   | ...     | ...  |
| 6 | Logging        | ...    | ...     | ...   | ...   | ...     | ...  |
| 7 | Architektur    | ...    | ...     | ...   | ...   | ...     | ...  |
| 8 | Analyzer       | ...    | ...     | ...   | ...   | ...     | ...  |
| 9 | Migration      | ...    | ...     | ...   | ...   | ...     | ...  |

## Build + Tests

**Build:** {0 Errors, X Warnings}
**Tests:** {N PASS, 0 FAIL}

## Norm-Evolution-Kandidaten (FAN_IN, RF-EV-001/RF-EV-003)

{N} Norm-Evolution-Kandidaten (Schwellenwert >=3 identische Findings):
- Gate {N} ({NAME}), Regel {R}: {COUNT}x → Parking-Lot eingetragen
- [Leer wenn keine Kandidaten]

## Gesamtstatus: {PASS|FAIL}

[Falls FAIL: Offene BLOCKER + Naechste Schritte]
```

### 5.2 Workers shutdownen + Team aufraeumen

```
Pro Worker:
  SendMessage type=shutdown_request

Nach allen Shutdowns:
  TeamDelete
```

---

## Phase 5a: Presentation Output (NUR report-Modus, RF-A-004)

**SKIP bei execute-Modus.**

Team Lead gibt dem User die Findings als /_presentation:

```
═══ Pre-PR REPORT — {BRANCH} ({DATE}) ═══

Modus: REPORT (readonly — kein Auto-Fix)
Gates: {X}/{Y} aktiv
Findings: {TOTAL} ({B} Blocker, {W} Warnungen)

┌───┬────────────────┬────────┬─────────┬──────┬──────────────────────────────────┐
│ # │ Gate           │ Status │ Blocker │ Warn │ Top-Finding                      │
├───┼────────────────┼────────┼─────────┼──────┼──────────────────────────────────┤
│ 1 │ Tests          │ CLEAN  │ 0       │ 0    │ —                                │
│ 2 │ Naming         │ WARN   │ 0       │ 3    │ camelCase-Verletzung in Svc      │
│ 3 │ Cleanup        │ FAIL   │ 2       │ 1    │ Auskommentierter Code in Ctrl    │
│ ...                                                                              │
└───┴────────────────┴────────┴─────────┴──────┴──────────────────────────────────┘

Finding-Log: .claude/review/prepr-findings-{BRANCH}-{DATE}.md

Starte interaktive Phase? (Enter=JA, N=Nein → nur Report speichern)
```

Falls User "N": → Phase 5b (Shutdown), SKIP Phase 6+7.
Falls User "JA" (oder Enter): → Phase 6 (interaktive Queue).

---

## Phase 6: Interaktive Queue (NUR report-Modus, RF-C-001 bis RF-C-005)

**SKIP bei execute-Modus.**

### 6.1 Queue aufbauen (RF-C-001)

Team Lead liest .claude/review/prepr-findings-{BRANCH}-{DATE}.md
und baut eine Queue aus allen OPEN Findings:

```
QUEUE = []
index = 1
FUER JEDES Gate mit Findings:
  FUER JEDES Finding im Gate:
    QUEUE.append({
      index: index++,
      gate: {GATE_NAME},
      datei: {DATEI},
      zeile: {ZEILE},
      regel: {REGEL},
      severity: {BLOCKER|WARNUNG},
      problem: {PROBLEM},
      status: OPEN,
      entscheidung: null,
      kommentar: null
    })
```

### 6.2 Item-Diskussion (RF-C-002)

Team Lead geht Items SEQUENTIELL durch:

```
FUER JEDES Item in QUEUE:
  AUSGABE:
  "── Finding {index}/{TOTAL} ──────────────────
   Gate:     {GATE_NAME}
   Datei:    {DATEI}:{ZEILE}
   Regel:    {REGEL}
   Severity: {SEVERITY}
   Problem:  {PROBLEM}

   [A]ccept  — Regel lernen (→ Meta-Datei)
   [R]eject  — Ausnahme lernen (→ Meta-Datei)
   [D]efer   — Uebersprungen (kein Lern-Eintrag)
   [S]kip rest — Alle verbleibenden Items DEFER"

  AskUserQuestion:
    header: "F{index}/{TOTAL}"
    question: "[{GATE}] {DATEI}:{ZEILE} — {PROBLEM}"
    options:
      - label: "Accept"   description: "Regel als R{N} in {gate}.md speichern"
      - label: "Reject"   description: "Ausnahme in {gate}.md speichern (wird kuenftig ignoriert)"
      - label: "Defer"    description: "Uebersprungen, kein Lern-Eintrag"
      - label: "Skip rest" description: "Alle verbleibenden Findings → DEFER"

  User-Antwort verarbeiten:
    Accept → Item.entscheidung = "ACCEPT", Item.status = "CONFIRMED"
    Reject → Item.entscheidung = "REJECT", Item.status = "REJECTED"
             Optional: AskUserQuestion fuer Begruendung (Freitext)
    Defer  → Item.entscheidung = "DEFER", Item.status = "DEFERRED"
    Skip rest → ALLE verbleibenden Items → DEFER
```

### 6.3 User-eigene Findings (RF-C-003)

Nach Ende der automatischen Queue:

```
AskUserQuestion:
  header: "User-Findings"
  question: "Eigene Findings hinzufuegen die der Scan nicht gefunden hat?"
  options:
    - label: "Ja"   description: "Neues Finding beschreiben"
    - label: "Nein" description: "Keine weiteren Findings"

Falls "Ja":
  LOOP:
    AskUserQuestion (Freitext): "Beschreibe das Finding (Gate, Datei, Problem):"
    Team Lead klassifiziert:
      → Gate (aus 9 Gates ableiten)
      → Severity (BLOCKER/WARNUNG)
      → Regel (passende R{N} oder neue)
    QUEUE.append({..., quelle: "USER-FINDING", status: "CONFIRMED"})
    Frage: "Noch ein Finding? (ja/nein)"
```

### 6.4 Protokoll schreiben (RF-C-004)

Team Lead aktualisiert .claude/review/prepr-findings-{BRANCH}-{DATE}.md:

```markdown
## Protokoll

| # | Gate | Datei:Zeile | Regel | Entscheidung | Kommentar |
|---|------|-------------|-------|-------------|-----------|
| 1 | Naming | Service.cs:42 | R3 | ACCEPT | — |
| 2 | Cleanup | Ctrl.cs:15 | R4 | REJECT | "Absichtlich auskommentiert fuer Debugging" |
| 3 | ... | ... | ... | DEFER | — |
| 4 | Architektur | Provider.cs:88 | — | ACCEPT | USER-FINDING: Business-Logik im Controller |

Zusammenfassung:
  ACCEPT:   {A}
  REJECT:   {R}
  DEFER:    {D}
  USER:     {U}
```

Update Finding-Log Frontmatter: `status: REVIEWED`

---

## Phase 7: Meta-Sync — Auto-Learn (NUR report-Modus, RF-B-002 bis RF-B-004, RF-C-005)

**SKIP bei execute-Modus.**

### 7.1 ACCEPT → Neue Regeln (RF-B-002)

Fuer jedes Item mit entscheidung == "ACCEPT":

```
1. Bestimme Ziel-Datei: .claude/meta/codeKonvention/{gate}.md
2. Lies Ziel-Datei → bestimme hoechste R{N}
3. Pruefe Duplikat: Aehnliche Regel vorhanden?
   → JA: "Aehnliche Regel existiert: R{K} '{titel}' — SKIP"
   → NEIN: Neue Regel schreiben:

### R{N+1}: {Problem-Titel}
- **Severity:** {BLOCKER|WARNUNG}
- **Auto-Fix:** NEIN (aus Report-Modus, manuell zu entscheiden)
- **Beschreibung:** {Problem-Beschreibung aus Finding}
- **Beispiel VORHER:**
  ```csharp
  // {Code-Auszug aus Finding, falls vorhanden}
  ```
- **Beispiel NACHHER:**
  ```csharp
  // {Empfohlene Loesung, falls ableitbar, sonst "Manuell zu bestimmen"}
  ```
- **Ausnahmen:** Keine
- **Herkunft:** Auto-Learn PrePR ({DATE}) Branch {BRANCH}

4. Version der Meta-Datei um 0.1 erhoehen
```

### 7.2 REJECT → Ausnahmen (RF-B-003)

Fuer jedes Item mit entscheidung == "REJECT":

```
1. Bestimme Ziel-Datei: .claude/meta/codeKonvention/{gate}.md
2. Suche bestehende Regel die am naechsten passt (gleiche Regel-ID aus Finding)
3. Falls Regel gefunden:
   → Ergaenze im "Ausnahmen:" Feld:
     "Ausnahme: {DATEI-PATTERN} — {User-Begruendung} (Auto-Learn {DATE})"
4. Falls keine passende Regel:
   → Neuer Block am Ende:

### AUSNAHME: {Problem-Titel}
- **Gate:** {GATE}
- **Betrifft:** {DATEI-PATTERN}
- **Begruendung:** {User-Begruendung}
- **Herkunft:** Auto-Learn REJECT PrePR ({DATE}) Branch {BRANCH}

5. Version der Meta-Datei um 0.1 erhoehen
```

### 7.3 Abschluss-Meldung (RF-C-005)

```
═══ Pre-PR REPORT — Meta-Sync abgeschlossen ═══

ACCEPT → Meta:     {A} neue Regeln ({D_SKIP} Duplikate uebersprungen)
REJECT → Ausnahmen: {R} neue Ausnahmen
DEFER:              {D} uebersprungen (kein Lern-Eintrag)
USER-FINDINGS:      {U} hinzugefuegt

Aktualisierte Meta-Dateien:
  - .claude/meta/codeKonvention/{gate1}.md (+{N1} Regeln, +{M1} Ausnahmen)
  - .claude/meta/codeKonvention/{gate2}.md (+{N2} Regeln)
  - ...

Finding-Log: .claude/review/prepr-findings-{BRANCH}-{DATE}.md (status: REVIEWED)

Das naechste /_Pre_PR wird diese neuen Regeln und Ausnahmen automatisch anwenden.
```

---

## Phase 5b: Shutdown (report-Modus, nach Phase 6+7 oder nach User "N" in 5a)

```
Pro Worker:
  SendMessage type=shutdown_request

Nach allen Shutdowns:
  TeamDelete
```

---

## Re-Run Modus

```
Falls /_Pre_PR_orchestrate schon gelaufen:

1. Vorherigen Summary lesen
2. NUR FAIL/WARN Gates erneut spawnen
3. PASS Gates skippen (Ergebnis wiederverwenden)

AUSGABE:
  "Re-Run: {N} Gates uebersprungen (PASS), {M} Gates erneut"
```

---

## Execution Timeline

```
| Phase   | Was                    | Agents | Zeit    |
|---------|------------------------|--------|---------|
| Phase 0 | Datei-Listen           | 1 (DU) | ~1 min  |
| Phase 1 | Team Setup + Spawn     | 1 (DU) | ~1 min  |
| Phase 2 | 9 Gates PARALLEL       | 9      | ~5 min  |
| Phase 3 | Aggregation            | 1 (DU) | ~1 min  |
| Phase 4 | Build + Test           | 1 (DU) | ~5 min  |
| Phase 5 | Summary + Shutdown     | 1 (DU) | ~1 min  |
|---------|------------------------|--------|---------|
| TOTAL   |                        | 9+1    | ~14 min |

vs ALT (v1.0 sequentiell): ~27 min → ~48% schneller
```

---

## TASK-BESCHREIBUNGEN (Vorlagen fuer TaskCreate)

### Gate 1: Tests

```
Subject: "Gate 1: Tests"
ActiveForm: "Running Tests quality gate"
Description: |
  Quality Gate: /_Pre_PR_Tests
  Knowledge: .claude/meta/codeKonvention/testbase.md
  Command: .claude/commands/_Pre_PR_Tests.md
  Dateien: {TEST_DATEI_LISTE}
  Auto-Fix: JA (sealed, TestBase-Vererbung)

  Pruefe:
  - R1: sealed Modifier auf Test-Klassen
  - R2: TestBase/ContainerIntegrationTestBase Vererbung
  - R3: Dispose-Pattern korrekt
  - R4: Test-Isolation

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 2: Naming

```
Subject: "Gate 2: Naming"
ActiveForm: "Running Naming quality gate"
Description: |
  Quality Gate: /_Pre_PR_Naming
  Knowledge: .claude/meta/codeKonvention/naming.md
  Command: .claude/commands/_Pre_PR_Naming.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: JA (Identifier umbenennen)

  Pruefe:
  - R1-R6: PascalCase, camelCase, Prefixes (I, _),
    Provider/Service/Controller Suffixes, Umlaut-Encoding

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 3: Cleanup

```
Subject: "Gate 3: Cleanup"
ActiveForm: "Running Cleanup quality gate"
Description: |
  Quality Gate: /_Pre_PR_Cleanup
  Knowledge: .claude/meta/codeKonvention/cleanup.md
  Command: .claude/commands/_Pre_PR_Cleanup.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: JA (Usings, Leerzeilen, Debug-Code)

  Pruefe:
  - Unused usings, Leerzeilen, auskommentierter Code,
    Debug-Output (Console.Write, Debug.Write),
    TODO/HACK/FIXME Kommentare

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 4: Dokumentation

```
Subject: "Gate 4: Dokumentation"
ActiveForm: "Running Dokumentation quality gate"
Description: |
  Quality Gate: /_Pre_PR_Dokumentation
  Knowledge: .claude/meta/codeKonvention/dokumentation.md
  Command: .claude/commands/_Pre_PR_Dokumentation.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: JA (XML-Kommentare generieren)

  Pruefe:
  - XML-Doku auf public Klassen/Methoden/Properties
  - Umlaut-Konvention (echte Umlaute vs ue/ae/oe)
  - Markdown in .md Dateien

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 5: Konstanten

```
Subject: "Gate 5: Konstanten"
ActiveForm: "Running Konstanten quality gate"
Description: |
  Quality Gate: /_Pre_PR_Konstanten
  Knowledge: .claude/meta/codeKonvention/konstanten.md
  Command: .claude/commands/_Pre_PR_Konstanten.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: TEILWEISE (String-Literale mit 2+ Vorkommen)

  Pruefe:
  - Magic Strings (2+ Vorkommen → Auto-Fix)
  - Magic Numbers (INFO, kein Auto-Fix)
  - Konstanten-Organisation

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 6: Logging

```
Subject: "Gate 6: Logging"
ActiveForm: "Running Logging quality gate"
Description: |
  Quality Gate: /_Pre_PR_Logging
  Knowledge: .claude/meta/codeKonvention/logging.md
  Command: .claude/commands/_Pre_PR_Logging.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: JA (Structured Logging)

  Pruefe:
  - String-Interpolation in Logging → Structured Logging
  - Log-Level Konsistenz
  - Sensitive Daten in Logs

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 7: Architektur

```
Subject: "Gate 7: Architektur"
ActiveForm: "Running Architektur quality gate"
Description: |
  Quality Gate: /_Pre_PR_Architektur
  Knowledge: .claude/meta/codeKonvention/architektur.md
  Command: .claude/commands/_Pre_PR_Architektur.md
  Dateien: {ALL_CS_LISTE}
  Auto-Fix: NEIN (nur Bericht)

  Pruefe:
  - R1-R6: Controller-Logik, Interface-Segregation,
    Provider-Pattern, Config-Zugriff, DI-Registrierung,
    DateTimeOffset.Now Konsistenz

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 8: Analyzer

```
Subject: "Gate 8: Analyzer"
ActiveForm: "Running Analyzer quality gate"
Description: |
  Quality Gate: /_Pre_PR_Analyzer
  Knowledge: .claude/meta/codeKonvention/analyzer.md
  Command: .claude/commands/_Pre_PR_Analyzer.md
  Dateien: {CSPROJ_LISTE}
  Auto-Fix: JA (SonarAnalyzer + Ruleset einfuegen)

  Pruefe:
  - SonarAnalyzer.CSharp in .csproj
  - CodeAnalysisRuleSet Referenz
  - EditorConfig Aenderungen

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

### Gate 9: Migration

```
Subject: "Gate 9: Migration"
ActiveForm: "Running Migration quality gate"
Description: |
  Quality Gate: /_Pre_PR_Migration
  Knowledge: .claude/meta/codeKonvention/migration.md
  Command: .claude/commands/_Pre_PR_Migration.md
  Dateien: {MIGRATION_LISTE}
  Auto-Fix: NEIN (zu hohes Risiko)

  Pruefe:
  - Bestehende Migrationen nicht geaendert (BLOCKER)
  - Down() ist exaktes Gegenteil von Up() (BLOCKER)
  - Reihenfolge umgekehrt
  - Nicht-deterministische Test-Daten (WARNUNG)

  Melde: PASS|WARN|FAIL + Findings pro Datei
```

---

## QUICK-START

Wenn User sagt "Pre-PR ausfuehren":

```
1. /_Pre_PR_orchestrate
2. Team Lead: Datei-Listen generieren (Phase 0)
3. Team Lead: Team "pre-pr" erstellen + 9 Tasks + 9 Workers spawnen
4. 9 Workers PARALLEL: Jeder prueft sein Gate
5. Team Lead: Ergebnisse sammeln
6. Team Lead: Build + Test ausfuehren
7. Team Lead: Summary Report + Shutdown

Bei FAIL: User fixt → /_Pre_PR_orchestrate (Re-Run, nur FAIL-Gates)
Bei PASS: PR erstellen
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| Worker meldet Knowledge-File fehlt | Gate als FAIL markieren, andere Gates laufen weiter |
| Worker-Timeout (>15 Min) | SendMessage "Status?", 5 Min warten, dann FAIL |
| Worker crashed | Gate als FAIL markieren, Re-Run nach Summary |
| Build-Fehler nach Auto-Fixes | Konflikt-Erkennung: welche Dateien von mehreren Gates editiert? Restoren + Re-Run sequentiell |
| Test-Fehler nach Auto-Fixes | Gleiche Konflikt-Erkennung wie Build |
| Alle Workers FAIL | ABORT: "Keine Gates bestanden. Knowledge-Files pruefen." |

---

## SYNTHETIC MEGA-AGENT TEST-PLAN (BL-159 PL-6-04)

**Zweck:** Wiederholbarer Test-Plan, der Phase 4d (SkillLoadSelfTest) verifiziert.
Test-Worker wird gespawnt der versucht `Read(*/commands/_*.md)` direkt auszufuehren
ohne vorherigen `Skill()`-Call. Guard MUSS triggern.

**Abhaengigkeit:** AK-1 (Hook-Detection), AK-2 (guard_skill_load_compliance.py),
AK-3 (Read-Block W7-Verhalten), PL-6-01 (Self-Test-Schritt).

### Test-Szenario T-6-04-1: Synthetischer Mega-Agent

**Vorbedingungen:**
- Guard `guard_skill_load_compliance.py` aktiv in `.claude/hooks/`
- `audit_hook.py` aktiv (schreibt `skill_loaded` Events)
- Saubere `audit.jsonl` Baseline (oder Marker-Event vorher gesetzt)

**Schritt-fuer-Schritt:**
```
1. Lead spawnt Test-Worker mit Prompt:
     "AUFTRAG: Lies _Pre_PR_orchestrate.md direkt (Mega-Agent-Versuch).
      Kein Skill()-Call vorher. Wir wollen einen BLOCK erzwingen."

2. Test-Worker fuehrt aus:
     Read("C:/.../commands/_Pre_PR_orchestrate.md")

3. Pre-Read-Hook prueft:
     - Skill-Context-Active? NEIN
     - Pfad matched */commands/_*.md? JA
     → Hook gibt exit 1 + stderr-Marker "SKILL_LOAD_VIOLATION"

4. Worker-Read scheitert mit Hook-BLOCK
5. audit.jsonl bekommt Event:
     {type: "SKILL_LOAD_VIOLATION", worker_id, attempted_path, hook_action: "block"}
```

**Erwartetes Ergebnis:**
- Hook-Exit-Code: 1 (BLOCK)
- stderr enthaelt `SKILL_LOAD_VIOLATION`
- `audit.jsonl` enthaelt VIOLATION-Event mit Pfad und Worker-ID
- Test-Worker meldet FAIL an Lead (Read-Tool nicht ausfuehrbar)
- Phase 4d (im nachfolgenden Pre-PR-Lauf) klassifiziert Worker als BLOCKER

**Idempotenz:**
- Test schreibt NUR in `audit.jsonl` (Append-Only) + Worker-Heap (ephemer)
- KEIN Vault-Seiteneffekt (keine Edits, kein Commit)
- Wiederholbar: Test kann beliebig oft laufen, jeder Lauf hinterlaesst 1 VIOLATION-Event

**Rollback-Vorschlag-Mechanismus (PL-6-03 Cross-Check):**
- Bei BLOCK soll Hook-Ausgabe `git diff`-Snapshot zur Rollback-Empfehlung enthalten
- PL-6-03 ist defered (OQ-5 Format-Frage offen) — Test-Plan deckt dies ab sobald PL-6-03 implementiert

### Test-Szenario T-6-04-2: Pre-PR Phase 4d Replay (Post-Hoc)

**Vorbedingungen:**
- T-6-04-1 wurde gelaufen (audit.jsonl enthaelt VIOLATION-Event)
- `_audit --skill-load-replay` Skript verfuegbar (siehe `_audit.md`)

**Schritt-fuer-Schritt:**
```
1. Run: /_audit --skill-load-replay
2. Skript liest audit.jsonl, filtert skill_loaded + SKILL_LOAD_VIOLATION events
3. Validiert: alle skill_loaded.load_method == "skill"
4. Wenn FAIL: Skript gibt Worker-Liste + Reason aus
```

**Erwartetes Ergebnis:**
- `_audit` Output enthaelt: `FAIL: 1 worker mit load_method != "skill"`
- Worker-ID, Pfad, Hook-Action sind nachvollziehbar
- Exit-Code: 1 (BLOCKER-Signal)

---

## LIFECYCLE-INTEGRATION

```
╔══════════════════════════════════════════════════════════════╗
║  PRE-PR im Feature-Lebenszyklus                             ║
║                                                              ║
║  /_SC_orchestrate ──► /_I_orchestrate ──► /_Pre_PR_orchestrate
║  (Forschung)         (Code + Tests)       (Quality Gates)    ║
║                                                              ║
║  Innerhalb /_I_orchestrate:                                  ║
║    ... → /_I_verify → /_I_diffAudit → /_Pre_PR_orchestrate  ║
║                                           │                  ║
║                                      PASS → PR erstellen     ║
║                                      FAIL → Fix → Re-Run    ║
╚══════════════════════════════════════════════════════════════╝
```

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist:**

```bash
powershell -Command "notify '{FEATURE} /_Pre_PR_orchestrate abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.

---

## Phase 6 (NEU BL-214 2026-05-24): BDF Auto-Loop conditional Re-Invocation (Geist G#11)

```
# BL-214 Fix 2026-05-24: Auto-Loop-Back zu BDF nach Pre_PR (Geist G#11).
# Vorher BROKEN: Pre_PR endete mit Notify, User musste manuell BDF re-starten.
# Option A aus BL-214 Spec: Pre_PR conditional BDF-Call.
#
# Termination-Schutz: Wenn keine OPEN BLs mehr im Active-Index → Terminal-Exit.
# Endlos-Loop-Schutz: bdf_scan_iterations Counter in BDF Phase 2 (existiert bereits).
# Pflicht-Voraussetzung: Pre_PR Gesamt-Status PASS (kein BDF-Loop bei FAIL).

# Iter 2 R4 Fix 2026-05-24: konkretisiere Pfad fuer pre_pr_status.
# Phase 5 Summary schreibt Gesamt-Status in Manifest BERATER_OUTPUTS.pre_pr_summary.status.
# Fallback: aus build_status + test_status ableiten (beide muessen GREEN sein fuer PASS).
pre_pr_status = (
    Read({bl_folder}/_manifest.md).BERATER_OUTPUTS.pre_pr_summary.status
    ?? (
        "FAIL" if (Read(..).build_status == "FAIL" OR Read(..).test_status == "FAIL")
        else "WARN" if any_gate_status == "WARN"
        else "PASS"
    )
)
IF pre_pr_status == "FAIL":
  Logge: "[BL-214] Pre_PR FAIL — BDF Auto-Loop SKIP (Build/Test rot, User-Intervention noetig)"
  → Terminal-Exit
ELSE:
  # Pruefe Active-Index auf weitere OPEN BL-Items
  active_bls = Read({vault_root}/_backlog_index.md) → Filtere Items mit status IN [DRAFT, READY, PLANNED, IN_PROGRESS, SC-REIF, HOLD, DEFERRED, PARTIAL_DONE, PHANTOM, RUNNING]
  open_count = active_bls.length

  IF open_count > 0:
    Logge: "[BL-214] Pre_PR PASS + {open_count} OPEN BLs im Active-Index — BDF Auto-Loop wird gestartet"
    Skill(skill="_BDF_orchestrate", args="--resume")
    # BDF picks next BL, Pipeline-Reise wiederholt sich
  ELSE:
    Logge: "[BL-214] Pre_PR PASS + 0 OPEN BLs — Terminal-Exit (alle BLs DONE)"
    # User-Notification dass alle BLs abgeschlossen
    powershell -Command "notify 'Alle BLs DONE — Pipeline-Reise abgeschlossen'"
```

**Verifikation:** audit.jsonl muss enthalten:
- `SKILL_LOAD _Pre_PR_orchestrate` → `PHASE_5_DONE` → conditional `SKILL_LOAD _BDF_orchestrate` (wenn open_count>0)

**Termination-Garantie:**
- Wenn alle BLs DONE → kein BDF-Loop
- Wenn BDF dann erneut leeren Active-Index sieht → BDF EMPTY-Handler → kein erneuter Pre_PR-Call
- bdf_scan_iterations Counter (existiert in BDF Phase 2) als zusaetzlicher Safety-Net

ARGUMENTS: $ARGUMENTS
