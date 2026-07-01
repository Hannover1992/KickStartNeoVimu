# /_TDD_execute — TDD Schritt 6b/6d/6f/6h: Test-Suite ausfuehren

## ═══ SOFORT-ANWEISUNG (LIES DIES ZUERST) ═══

**DU DARFST KEINEN CODE EDITIEREN. DU DARFST KEINE DATEIEN AENDERN.**

Execute = NUR Tests ausfuehren + Ergebnis in TDD-STATE.md schreiben.

- Compile-Fehler? → `GREEN_FAILED` + `backtrack_reason` in TDD-STATE.md. KEIN Fix.
- Test FAIL? → `RED_VERIFIED` (bei expected=RED) oder `GREEN_FAILED` (bei expected=GREEN).
- Fehlende Usings? → `GREEN_FAILED`. Der GREEN-Worker fixt das, NICHT du.
- Logger-Problem? → `GREEN_FAILED`. Zurueck an den Orchestrator.

**VERBOTEN:** Edit, Write, Update auf .cs/.csproj Dateien.
**ERLAUBT:** Read, Bash(dotnet test), Schreiben auf TDD-STATE.md.

**ABSOLUT VERBOTEN (BL-NEW-52 2026-05-12):**
- `docker-compose up`, `docker run`, `docker start` (Container-Setup)
- `dotnet ef database update` (DB-Migration)
- TestContainers-Setup-Code, Container-Healthchecks, Setup-Polling-Loops
- Konfigurations-Datei-Editing (appsettings.json, .env, etc.)
- Long-running Setup-Sequenzen mit Polling/Timeout/Recovery

**WENN Container nicht laeuft (Pattern-Anchor BL-NEW-52 in `.claude/_parking-lot.md`):**
1. STOPP — kein eigenes Setup versuchen
2. Schreibe TDD-STATE.md:
   ```
   state: SETUP_REQUIRED
   last_action: _TDD_execute
   error: "Stage 3 Docker-Container nicht verfuegbar. Setup-Worker benoetigt vor diesem _TDD_execute-Spawn."
   audit_event: BL_NEW_52_SCOPE_OVERSTEP_AVOIDED
   ```
3. SendMessage an team-lead:
   "ABORT: BL-NEW-52 — Setup-Worker fehlt. Spawne ZUERST `_TDD_setup` (BL-NEW-53) mit stage_N.md.setup.commands, DANN re-spawne _TDD_execute fuer dotnet test-only."
4. EXIT mit Status SETUP_REQUIRED (kein FAIL — Setup ist Lead's Verantwortung)

**Worker-Trennung-Pattern (Stage 3+ Integration/E2E):**
```
1. Lead spawnt @i-tddinit-{slice}-s{N} via Skill(_TDD_init, --stage={N})
   → HiL-Wizard fuer Stage-Definition / Ring-Planung (KEIN Container-Setup!)
1b. Lead spawnt @i-tddsetup-{slice}-s{N} via Skill(_TDD_setup) (BL-NEW-53)
   → Liest stage_N.md.setup.commands + executet sequenziell
   → Container/DB/WebHost spinup, Healthcheck, PID-Tracking
2. Lead VERIFIZIERT SETUP_DONE in TDD-STATE.md via audit
3. Lead spawnt @i-tddexec-{slice}-s{N}-r{red|green} via Skill(_TDD_execute)
   → NUR dotnet test + TDD-STATE.md write (KEIN Setup, KEIN Container-Mgmt)
4. Nach _TDD_check Step 18: Lead spawnt @i-tddteardown-{slice}-s{N} via Skill(_TDD_teardown)
   → Best-effort cleanup, immer (finally-Semantik)
```

---

**ERLAUBT als FRESHNESS-CHECK (NICHT Setup, BL-NEW-52-Verfeinerung 2026-05-12):**

Build und Daemon-Check sind **lokale, idempotente, Read-only-Operationen** — kein Setup im Sinne von BL-NEW-52 (Container-Lifecycle/Side-Effects). Ohne diese Pre-Steps testest du veralteten Code-Stand (`--no-build` nutzt staden Build-Output).

```
ERLAUBT:
- Bash("dotnet build {test_projekt} --no-restore")
  Zweck:   Letzten Code-Stand kompilieren (Live-Coding: User editiert zwischen Runs)
  Idempotent: 0-2s wenn nichts geaendert, 5-30s incremental, 60s+ rebuild
  Side-Effect: Nur lokales bin/obj — kein externes System

- Bash("docker info") oder Bash("docker ps")
  Zweck:   Daemon-Daseinscheck (read-only)
  Side-Effect: keiner
```

**Pre-Test Decision-Tree:**

```
SCHRITT 0 (Freshness-Check):
  0.1  Bash("dotnet build {test_projekt} --no-restore")
       IF exit_code != 0:
         TDD-STATE: state=BUILD_FAILED + backtrack_reason=<compile_errors>
         audit_jsonl_append({type: "BUILD_FAIL", worker, error})
         SendMessage(team-lead, "Build-Fehler verhindert Test-Run. Lead muss Code fixen ODER GREEN-Worker neu spawnen.")
         EXIT mit Status BUILD_FAILED (KEINE eigene Code-Korrektur, BL-NEW-52-Geist)

  0.2  Bash("docker info")
       IF exit_code != 0:
         TDD-STATE: state=DOCKER_NOT_AVAILABLE
         audit_jsonl_append({type: "DOCKER_DAEMON_DOWN", worker})
         SendMessage(team-lead, "Docker Daemon nicht erreichbar. Lead muss Docker Desktop starten (KEIN eigenes Spinup).")
         EXIT mit Status SETUP_REQUIRED (BL-NEW-52 strict)

SCHRITT 1 (FQN-Routing + Test-Run, BL-NEW-54 + BL-261 SUB-BATCH-TEST-TARGET 2026-06-04):
  fqn_list = lies KURZLEBIG_PROMPT → fqn_list ?? []

  # BL-261 (Wurzel-Fix, Live-Defekt BL-242 batch_2): Das .NET-FQN-Gate ist NICHT das einzige gueltige Test-Ziel.
  # Bei Python/pytest (oder generell wenn der Spawn-Prompt "SUB-BATCH-TEST-TARGET (BL-261)" traegt) IST das
  # Sub-Batch-Test-Artefakt das Ziel — NICHT nur das stage-eingefrorene testbefehl (das trifft bei spaeteren
  # Sub-Batches oft nur batch_1s Datei -> 16/16 GRUEN bei expected=RED -> spurious RED->ABORT, 4M Token).
  IF |fqn_list| == 0:
    sub_batch_targets = TDD-STATE.tests_written[].datei  # Dateien, die _TDD_red fuer DIESEN sub_batch schrieb
      ?? glob(test_{name}_batch{N}.py) + test_{name}.py-Kanarienvogel  # Konvention, falls tests_written leer
    IF |sub_batch_targets| > 0:
      # KEIN EXIT-FAIL: die pytest-Test-Datei IST die "FQN". Sub-Batch-Datei(en) + fruehere als Kanarienvogel.
      Logge: "[BL-261] fqn_list leer -> Sub-Batch-Test-Target aus tests_written abgeleitet: {sub_batch_targets}"
      fqn_list = sub_batch_targets
    ELSE:
      SendMessage(team-lead, "Weder FQN-Liste (KURZLEBIG_PROMPT) noch Sub-Batch-Test-Artefakt (TDD-STATE.tests_written leer) — _TDD_execute hat KEIN Test-Ziel. Lead muss _TDD_red (RED-Tests schreiben) ODER FQN-Liste liefern.")
      EXIT FAIL.

  # Stage-Resolution (BL-392 AK-CONSUMER-REWRITE): kanonisch ueber resolve_vault_stage (Dual-Read).
  # Migriert -> testbefehl aus dem execute-Slice: resolve_vault_stage.resolve_slice(N, "execute").
  # Nicht migriert -> Legacy-Monolith-Fallback stage_N.md (IDENTISCH zu heute). KEIN Direkt-Glob.
  testbefehl_template = lies stage_N.md.testbefehl   # WORTWOERTLICH respektieren (.NET: <FQN>-Substitution); Quelle = execute-Slice (migriert) bzw. Legacy-Monolith (Fallback)
  test_results = []

  FOR fqn IN fqn_list:
    # .NET: testbefehl_template mit <FQN>-Substitution. Python/pytest (BL-261): fqn IST der Test-Datei-Pfad/Node-ID
    # -> direkt als pytest-Ziel fahren (KEINE <FQN>-Platzhalter-Substitution im pytest-Fall).
    cmd = (fqn endet auf ".py" ODER fqn enthaelt "::")
            ? ("python -m pytest " + fqn + " -v")
            : testbefehl_template.replace("<FQN>", fqn)
    Bash(cmd, timeout=stage_N.md.timeout_per_test_min)
    result = (.NET: parse_trx(parse_logger_param(cmd))) ODER (pytest: parse exit_code/Summary)  # GREEN | RED | ERROR
    test_results.append({fqn, result, duration_sec})

  aggregate = all(r.result == "GREEN" for r in test_results)
  TDD-STATE.test_results = test_results
  TDD-STATE.state = (aggregate ? "GREEN_VERIFIED" : "RED_VERIFIED" wenn expected=RED ELSE "GREEN_FAILED")
```

**Konventions-Strenge:**
- `stage_N.md.testbefehl` MUSS wortwoertlich verwendet werden. Worker darf KEINE eigenen
  Flags hinzufuegen ausser FQN-Substitution.
- Wenn stage_N.md.infrastruktur=testcontainers: TestContainers-Fixtures regeln Container-
  Lifecycle im Test-Code selbst. Worker NICHT spinup von aussen.
- Wenn stage_N.md.infrastruktur=docker-compose: separates `_TDD_setup` MUSS vorher gelaufen
  sein (Lead-Verantwortung). Bei Daemon-FAIL → SendMessage statt eigenem Setup.

## ═══ ENDE SOFORT-ANWEISUNG ═══

**BL-NEW-51 — Haiku VERBOTEN.** Dieses Skill MUSS mit Sonnet (oder Opus) gespawned werden. Begruendung: mehrstufige Test-Sequenzen (Container-spinup → Polling → Test-Capture → Log-Parse → Teardown) erfordern striktes Befehls-Befolgen, das Haiku unter Last nicht zuverlaessig durchhaelt. Crown SCHRITT 1.0 MODEL-VALIDATION blockiert haiku-Spawn fuer _TDD_*. Case-Anchor + Live-Run-Details: `.claude/_parking-lot.md` BL-NEW-51.

```yaml
status: active
model_tier: sonnet
forbidden_models: [haiku]
version: 1.2.0
created: 2026-03-07
updated: 2026-03-07
op: TDD-SubCommand
phase: Execute
chain_position: 6b | 6d | 6f | 6h
type: building-block
```

## Aufruf

```
/_TDD_execute {SLICE} {STUFE} {ITERATION} {EXPECTED}
```

`{EXPECTED}` = `RED` oder `GREEN`

Wird von `spawne_tdd_agent(slice, "_TDD_execute", stufe, iteration, expected=...)` in `/_I_orchestrate` gerufen.

---

## VERTRAG

```
LIEST:
  {WORKTREE_PATH}/.claude/TDD-STATE.md                (state + letzter Schritt)
  {WORKTREE_PATH}/.claude/TDD_INSTRUCTIONS.md          (testbefehl, testpfad)
  Bestehende Test-Datei(en)                            (welche Tests laufen)

SCHREIBT:
  {WORKTREE_PATH}/.claude/TDD-STATE.md                 (red_confirmed oder green_confirmed)
```

---

## Ziel

Fuehre die Test-Suite aus und stelle fest ob das Ergebnis dem Erwarteten entspricht.

| Position | Expected | Beweist |
|----------|----------|---------|
| 6b | RED | Neuer Test ist wirklich rot (testet etwas Neues) |
| 6d | GREEN | Minimaler Code macht den Test gruen |
| 6f | GREEN | Code-Refactoring hat Tests NICHT gebrochen |
| 6h | GREEN | Test-Refactoring hat Code NICHT gebrochen |

---

## Ablauf

### Schritt 1: Testbefehl laden

```
1. Lies TDD_INSTRUCTIONS.md:
   - testbefehl: {z.B. "dotnet test --filter {testpfad}"}
   - testpfad: {z.B. "Tests/UnitTests/"}
   - Falls TDD_INSTRUCTIONS.md fehlt: Lies Sub-Blueprint fuer Hinweise
2. Lies TDD-STATE.md:
   - Welcher Test wurde zuletzt geschrieben (aus tests_written)?
   - state: {RED | GREEN_ATTEMPT | ...}
```

### Schritt 2: Test-Suite ausfuehren

```bash
# Exakter Befehl aus TDD_INSTRUCTIONS.md
{testbefehl}
```

**Ergebnis auswerten:**

```
EXPECTED = RED:
  Mindestens 1 Test schlaegt fehl → red_confirmed: true
    WICHTIG: Pruefe dass DER NEUE TEST fehlschlaegt (nicht ein alter).
    Identifiziere den Test-Namen im Output und vergleiche mit tests_written.
  Alle Tests bestehen → red_confirmed: false
    DIAGNOSE PFLICHT: Bestimme WELCHER der 3 Gruende zutrifft:
      A) Test prueft keine neue Logik (trivial) → Test neu schreiben
      B) Production-Code existiert bereits → naechster Ring statt RED
      C) Test-Isolation kaputt (anderer Test laeuft statt des neuen)
         → test_filter im Befehl ueberpruefen
    backtrack_reason: {A | B | C} in STATE schreiben

EXPECTED = GREEN:
  Alle relevanten Tests bestehen → green_confirmed: true
  Mindestens 1 Test schlaegt fehl → green_confirmed: false
    GRUND: Code/Refactoring hat Tests gebrochen.
```

### Schritt 3: TDD-STATE.md aktualisieren

```yaml
# Bei EXPECTED=RED:
state: RED_VERIFIED  # falls red_confirmed=true
# oder
state: RED_FAILED    # falls red_confirmed=false (Test ist NICHT rot)

last_action: _TDD_execute
expected: RED
red_confirmed: {true|false}
backtrack_reason: {A | B | C}  # A=trivial, B=code-exists, C=isolation
backtrack_action: {new-test | next-ring | fix-filter}
test_output: |
  {letzte relevante Zeilen aus Test-Output, max 10 Zeilen}
iteration: {ITERATION}

# Bei EXPECTED=GREEN:
state: GREEN_VERIFIED  # falls green_confirmed=true
# oder
state: GREEN_FAILED    # falls green_confirmed=false

last_action: _TDD_execute
expected: GREEN
green_confirmed: {true|false}
test_output: |
  {letzte relevante Zeilen aus Test-Output, max 10 Zeilen}
iteration: {ITERATION}
```

---

## Output (SendMessage an team-lead)

```
# Bei red_confirmed=true (RED erwartet, gut):
_TDD_execute {SLICE} i{ITERATION}: RED_CONFIRMED.
Test '{TEST_NAME}' schlaegt fehl — erwartetes Verhalten.
Naechster Schritt: _TDD_green.

# Bei red_confirmed=false (RED erwartet, Problem):
_TDD_execute {SLICE} i{ITERATION}: RED_FAILED.
Test ist NICHT rot. Moegliche Ursache: {URSACHE}.
Naechster Schritt: zurueck zu _TDD_red (6a).

# Bei green_confirmed=true (GREEN erwartet, gut):
_TDD_execute {SLICE} i{ITERATION}: GREEN_CONFIRMED.
Alle Tests bestehen — Schritt erfolgreich.
Naechster Schritt: {_TDD_refactorCode | _TDD_refactorTests | _TDD_check}.

# Bei green_confirmed=false (GREEN erwartet, Problem):
_TDD_execute {SLICE} i{ITERATION}: GREEN_FAILED.
{N} Tests schlagen fehl nach {vorheriger_schritt}.
Naechster Schritt: zurueck zu {_TDD_green | _TDD_refactorCode | _TDD_refactorTests}.
```

---

## Regeln

- KEIN Code schreiben (nur ausfuehren)
- KEIN git commit
- Test-Output auf das Wesentliche kuerzen (kein vollstaendiger Stack Trace im State)
- Kanarienvogel-Tests NICHT anfassen -- falls Kanarienvogel-Test rot wird: SOFORT melden
- Bei Compile-Fehler: green_confirmed: false (Compile-Fehler = kein gruenes Ergebnis)

---

## Granularitaets-Selektor (AK-D-COMBINED-Fix, BL-486)

Fuer den Test-Lauf gibt es drei Granularitaets-Stufen (Granularitaet):

- **einzeln** (single): Nur ein spezifischer Test oder eine Datei -- gezieltester Lauf.
- **handvoll** (handful): Subset des Sub-Batches -- Standard-Fall im TDD-Zyklus.
- **alle** (all): Voll-Suite-Lauf -- alle Stages und Tests.

GUARD: Ein Voll-Suite-Lauf (Granularitaet=alle) erfordert explizite Bestaetigung durch den
Lead (Laufzeit 5h+ moeglich). Kein versehentliches Ausloesen -- der Lead muss den Lauf
explizit mit `--granularity=alle` oder `--all-tests` authorisieren.

Default-Granularitaet: testSearch (Standard-Filter aus IDF-testSearch-Phase).
default_granularity=testsearch
