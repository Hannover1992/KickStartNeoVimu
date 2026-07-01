# /_TDD_setup — Stage-Setup-Executor (BL-NEW-53)

```yaml
status: active
version: 1.0.0
created: 2026-05-12
type: building-block
op: TDD-SubCommand
phase: Setup
chain_position: 9b (in _I_orchestrate TDD-Phase, NACH _TDD_init)
model_tier: sonnet
forbidden_models: [haiku]   # BL-NEW-51 — mehrstufige Polling-Sequenz mit Healthcheck
feature_anchor: BL-NEW-53
related:
  - _TDD_init      (Step 9, HiL-Wizard, kommt VOR _TDD_setup)
  - _TDD_teardown  (Step 18b, kommt NACH _TDD_check, finally-Semantik)
  - _TDD_execute   (Steps 11/13/15/17, erwartet SETUP_DONE)
```

## ═══ SOFORT-ANWEISUNG (LIES DIES ZUERST) ═══

**DU FUEHRST `setup.commands` AUS `stage_{STUFE}.md` AUS.**

- Du liest stage_N.md.setup.commands sequenziell aus.
- Du fuehrst sie via Bash/PowerShell aus.
- Du wartest auf `health_check` bis Success ODER timeout_min.
- Du trackst PIDs / Container-IDs in TDD-STATE.md.setup_artifacts.
- Du machst KEIN Code-Edit, KEIN Test-Run.

**VERBOTEN:**
- Eigene Commands erfinden (nur was in stage_N.md.setup.commands steht)
- Code-Dateien aendern
- Tests ausfuehren (das ist _TDD_execute's Job)
- Container-Spinup wenn `infrastruktur: testcontainers` (Fixtures regeln das im Test-Code)

**ERLAUBT:**
- `Bash(...)` mit Commands aus stage_N.md.setup.commands
- `Read` von stage_N.md, TDD-STATE.md
- `Schreiben` von TDD-STATE.md.{state, setup_artifacts}
- `SendMessage` an team-lead bei DONE/FAIL

## ═══ ENDE SOFORT-ANWEISUNG ═══

---

## SCHRITT 0.0 (PFLICHT — BL-NEW-45 SKILL-LOAD-VERIFIKATION)

```
VOR allen anderen Schritten — verifiziere Skill-Load via Skill(_TDD_setup).
Bei Inline-AUFTRAG-Prompt: STOPP + audit BL_NEW_45_VIOLATION + EXIT FAIL.
```

## SCHRITT 0 (PFLICHT — BL-NEW-30/43 PATH-RESOLUTION)

```bash
VAULT_ROOT = $(python "{WORKTREE_PATH}/.claude/scripts/resolve_vault_root.py")
BL_FOLDER  = $(python "{WORKTREE_PATH}/.claude/scripts/resolve_bl_path.py" "{FEATURE_ID}")
```

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _TDD_setup                                                 ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {WORKTREE_PATH}/.claude/meta/implementation/stage_{STUFE}.md      ║
║      → setup.commands, setup.timeout_min, setup.idempotent          ║
║      → health_check                                                  ║
║      → infrastruktur                                                 ║
║    {BL_FOLDER}/meta-overrides/stage_{STUFE}.md (optional Override)   ║
║    {WORKTREE_PATH}/.claude/TDD-STATE.md (Idempotency-Check)         ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {WORKTREE_PATH}/.claude/TDD-STATE.md                              ║
║      state: SETUP_DONE | SETUP_FAILED | SETUP_SKIPPED                ║
║      setup_artifacts:                                                ║
║        pids: [{process_name: int}, ...]                              ║
║        container_ids: [...]                                          ║
║        started_at: ISO                                               ║
║        commands_executed: [...]                                      ║
║        health_check_passed_at: ISO                                   ║
║                                                                      ║
║  RUFT:                                                               ║
║    KEINE Skills (atomarer Executor)                                  ║
║    SendMessage(team-lead, "SETUP_DONE: ...") nach Erfolg            ║
║                                                                      ║
║  AKTOR:  _I_orchestrate Step 9b (NACH _TDD_init, VOR _TDD_red)      ║
║  MODELL: sonnet (BL-NEW-51 verbietet haiku)                         ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    INV-SETUP-1: NUR Commands aus stage_N.md.setup.commands           ║
║                  (keine eigenen Befehle erfinden)                    ║
║    INV-SETUP-2: Sequenziell ausfuehren (parallele Setups via         ║
║                  expliziter Wave-Logic in stage_N.md)                ║
║    INV-SETUP-3: Bei command-FAIL: state=SETUP_FAILED + SendMessage   ║
║                  Lead + EXIT (kein Best-Effort bei Setup)            ║
║    INV-SETUP-4: PID-Tracking PFLICHT bei Start-Process-Patterns      ║
║    INV-SETUP-5: Idempotenz bei stage_N.md.setup.idempotent=true      ║
║    INV-SETUP-6: Auto-SKIP bei infrastruktur=none AND empty commands  ║
║    INV-SETUP-7: Healthcheck-Wait mit Timeout (kein infinite loop)    ║
║    INV-SETUP-9 (BL-247 AK-5/10): VOR Container-Spinup acquire der     ║
║                  non-shareable Ressourcen (concurrency_class IN       ║
║                  {DEPENDS,EXCLUSIVE}); acquire-FAIL → SETUP_FAILED +  ║
║                  EXIT (kein Halb-Spinup); all-or-nothing-Rollback     ║
║                  (= Auspraegung von INV-SETUP-3 fuer Ressourcen)      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## SCHRITT 0.4: Stage-Kontext laden (BL-NEW-63)

> **Stage-Resolution (BL-392 AK-CONSUMER-REWRITE):** Die Stage-Doc-Aufloesung laeuft ueber den
> kanonischen `resolve_vault_stage`-Resolver (Dual-Read). Ist die Stage in den Vault migriert
> (`{VAULT}/Stage/stage_N_<name>/`), liest der Setup-Worker den `setup`-Slice (+ `health_check` fuer
> das Health-Gate) — single unit of work, NUR der setup-Concern; sonst faellt der Resolver auf den
> Legacy-Monolith `.claude/meta/implementation/stage_N.md` zurueck (IDENTISCH zu heute). Der folgende
> `parse_yaml_frontmatter(...stage_N.md)`-Pseudocode beschreibt den Legacy-Fallback-Pfad; kanonisch
> ist `resolve_vault_stage.resolve_slice(STUFE, "setup")`.

```
stage_meta = parse_yaml_frontmatter("{WORKTREE_PATH}/.claude/meta/implementation/stage_{STUFE}.md")

# Schicht-3 Override-Merge (BL-NEW-59-vorbereitet):
override_path = "{BL_FOLDER}/meta-overrides/stage_{STUFE}.md"
IF EXISTS(override_path):
  stage_meta = merge(stage_meta, parse_yaml_frontmatter(override_path))

infrastruktur     = stage_meta.infrastruktur     # none | testcontainers | docker | docker-compose
setup_commands    = stage_meta.setup.commands    ?? []
setup_timeout_min = stage_meta.setup.timeout_min ?? 5
setup_idempotent  = stage_meta.setup.idempotent  ?? true
health_check_cmd  = stage_meta.health_check       ?? null

audit_jsonl_append({
  type: "STAGE_CONTEXT_LOADED",
  skill: "_TDD_setup",
  stage: STUFE,
  infrastruktur: infrastruktur,
  command_count: |setup_commands|
})
```

---

## SCHRITT 1: Auto-SKIP-Detection (INV-SETUP-6)

```
IF infrastruktur == "none" AND |setup_commands| == 0:
  Logge: "[TDD-SETUP] infrastruktur=none + keine setup.commands → SKIP"
  TDD-STATE.md UPDATE:
    state: SETUP_SKIPPED
    skip_reason: "infrastruktur=none, no setup needed"
  audit_jsonl_append({type: "SETUP_SKIPPED", reason: "no_infra"})
  SendMessage(team-lead, "SETUP SKIPPED — kein Setup noetig fuer Stage {STUFE}")
  EXIT SUCCESS
```

---

## SCHRITT 2: Idempotency-Check (INV-SETUP-5)

```
IF setup_idempotent == true AND EXISTS(TDD-STATE.md):
  tdd_state = read TDD-STATE.md
  IF tdd_state.state == "SETUP_DONE" AND tdd_state.setup_artifacts:
    # Re-Check via Healthcheck — laeuft Setup noch?
    IF health_check_cmd != null:
      result = Bash(health_check_cmd, timeout=30s)
      IF result.exit_code == 0:
        Logge: "[TDD-SETUP] Idempotent re-confirmed — Setup laeuft noch (healthcheck PASS)"
        audit_jsonl_append({type: "SETUP_IDEMPOTENT_SKIP", health: "ok"})
        SendMessage(team-lead, "SETUP IDEMPOTENT — Setup laeuft bereits + healthy")
        EXIT SUCCESS
      ELSE:
        Logge: "[TDD-SETUP] Idempotent re-check FAILED — Setup neu starten"
        # Fall-through zu Schritt 3
```

---

## SCHRITT 2.5: Ressourcen-acquire VOR Container-Spinup (BL-247 AK-5/AK-10, INV-SETUP-9)

```
# ── BL-247: non-shareable Ressourcen acquiren BEVOR irgendein Container/Service
#    hochgefahren wird. Die acquire/release-Semantik selbst ist NICHT hier gebaut —
#    sie kommt aus .claude/scripts/stage_resource_registry.py (AK-3/4/8 TDD-gedeckt).
#    Dieser Schritt ist nur die Konsumenten-Naht (markdown_uncoverable, Szenario-Verify).

# --- AK-10: Klassen-Lesung (aus BL-318, NICHT neu klassifizieren) ---
# concurrency_class + concurrency_depends_on sind STAGE-Eigenschaften (BL-318).
# PRIMAER-Pfad (SOA-3, INV-STAGE-11/12): der stagePlanner hat sie pro Batch in
#   DF_BATCH_STATE.stage_concurrency_per_batch + (Liste) durchgereicht.
# FALLBACK (SOA-3): direkt aus stage_N.md.frontmatter (existiert geshippt, stage_3.md).
concurrency_class      = null
concurrency_depends_on = []

# PRIMAER: stagePlanner-State (DF_BATCH_STATE), falls im Worker-Kontext sichtbar
IF DF_BATCH_STATE?.stage_concurrency_per_batch?[{BATCH_KEY}]?[STUFE]:
  concurrency_class = DF_BATCH_STATE.stage_concurrency_per_batch[{BATCH_KEY}][STUFE]
# concurrency_depends_on bleibt eine STAGE-Eigenschaft → aus stage_meta (s.u.)
concurrency_depends_on = stage_meta.concurrency_depends_on ?? []

# FALLBACK: Klasse direkt aus stage_N.md, falls State sie nicht traegt (SOA-3-Mitigation)
IF concurrency_class == null:
  concurrency_class = stage_meta.concurrency_class ?? "EXCLUSIVE"   # INV-STAGE-12 sicherer Default

Logge: "[TDD-SETUP] BL-247 concurrency_class={concurrency_class} depends_on={concurrency_depends_on} (gelesen aus BL-318, nicht neu)"
audit_jsonl_append({type: "RESOURCE_CLASS_READ", stage: STUFE, concurrency_class: concurrency_class, depends_on: concurrency_depends_on})

# --- AK-10: NUR DEPENDS/EXCLUSIVE acquiren. PARALLEL = teilbar → KEIN acquire ---
IF concurrency_class == "PARALLEL" OR |concurrency_depends_on| == 0:
  Logge: "[TDD-SETUP] BL-247 SKIP acquire — Stage teilbar (PARALLEL) bzw. keine non-shareable Ressource"
  # kein Eintrag, kein Lock — direkt weiter zu SCHRITT 3
ELSE:
  # --- AK-5 + SOA-4: all-or-nothing acquire VOR Spinup ---
  # acquire_all rollt bei Partial-Fail die bereits gehaltenen automatisch zurueck
  # (Rollback intern, kein verwaister Teil-Lock). worker_id/bl_id aus Worker-Kontext.
  # KEIN direkter res__-Key — die API kapselt das FS-Encoding (resource_id rein).
  acquired = stage_resource_registry.acquire_all(
    concurrency_depends_on,        # die resource_ids dieser Stage (BL-318)
    worker_id = {WORKER_ID},       # dieser Setup-Worker
    bl_id     = {FEATURE_ID}       # das acquirende BL
  )

  IF NOT acquired:
    # --- AK-5 / INV-SETUP-3 / INV-SETUP-9: LOCKED → SETUP_FAILED + EXIT (kein Halb-Spinup) ---
    Logge: "[TDD-SETUP] BL-247 acquire_all FAILED — Ressource(n) {concurrency_depends_on} LOCKED (anderer Lauf haelt sie)"
    TDD-STATE.md UPDATE:
      state: SETUP_FAILED
      setup_error: {phase: "resource_acquire", locked_resources: concurrency_depends_on, concurrency_class: concurrency_class}
    audit_jsonl_append({type: "SETUP_FAILED", phase: "resource_acquire", locked_resources: concurrency_depends_on})
    SendMessage(team-lead,
      "SETUP_FAILED Stage {STUFE}: non-shareable Ressource(n) {concurrency_depends_on} LOCKED "
      "(belegt von anderem Lauf). KEIN Container-Spinup. "
      "Lead-Decision: soft-defer (BL-318 AK-4) auf unabhaengigen PARALLEL-Batch ODER warten.")
    EXIT FAIL    # kein Best-Effort, kein Halb-Spinup (INV-SETUP-3-Klasse)

  # acquire OK → die gehaltenen resource_ids fuer den Teardown merken (AK-6 REVERSE-release).
  # PERSIST in setup_artifacts.acquired_resources (das ist der Handoff-Kanal zu _TDD_teardown,
  # sortiert wie acquire_all sie acquiriert hat). SCHRITT 3 initialisiert setup_artifacts neu
  # → dieser Wert wird dort uebernommen (siehe SCHRITT 3 Init).
  setup_acquired_resources = sorted(concurrency_depends_on)   # acquire_all acquiret sortiert
  Logge: "[TDD-SETUP] BL-247 acquire_all OK — {setup_acquired_resources} gehalten, Spinup darf laufen"
  audit_jsonl_append({type: "RESOURCE_ACQUIRED", resources: setup_acquired_resources})
```

> **Stale-Locks (AK-8):** Ein verwaister Lock eines HART gecrashten Laufs (kein Teardown
> gelaufen) wird NICHT hier behandelt — die geerbte BL-229-TTL-Stale-Mechanik
> (`stage_resource_registry.acquire` → `factory_lock.is_bl_stale`) reclaimt ihn
> automatisch beim naechsten acquire-Versuch. Hier kein Eigen-Reclaim.

---

## SCHRITT 3: Setup-Commands sequenziell ausfuehren (INV-SETUP-1, INV-SETUP-2, INV-SETUP-3)

```
setup_artifacts = {
  pids: [],
  container_ids: [],
  started_at: now_iso,
  commands_executed: [],
  # BL-247 AK-5/6: die in SCHRITT 2.5 acquirierten non-shareable Ressourcen (sortiert).
  # _TDD_teardown liest dieses Feld + released in REVERSE-Order (AK-6, INV-TEARDOWN-7).
  # Leer wenn Stage PARALLEL/teilbar war (kein acquire).
  acquired_resources: (setup_acquired_resources ?? [])
}

FOR cmd IN setup_commands:
  Logge: "[TDD-SETUP] Executing: {cmd[:80]}..."
  audit_jsonl_append({type: "SETUP_CMD_START", cmd_preview: cmd[:80]})

  result = Bash(cmd, timeout_min=setup_timeout_min)

  IF result.exit_code != 0:
    Logge: "[TDD-SETUP] FAIL bei command: {cmd[:80]}"
    Logge: "[TDD-SETUP] stderr: {result.stderr[:500]}"

    # PID-Cleanup von bereits gestarteten Prozessen (best-effort)
    FOR pid IN setup_artifacts.pids:
      Bash(f"kill {pid} 2>/dev/null || true")

    TDD-STATE.md UPDATE:
      state: SETUP_FAILED
      setup_artifacts: setup_artifacts
      setup_error: {cmd: cmd[:200], stderr: result.stderr[:500], exit_code: result.exit_code}

    audit_jsonl_append({
      type: "SETUP_FAILED",
      cmd_preview: cmd[:80],
      exit_code: result.exit_code
    })

    SendMessage(team-lead,
      "SETUP_FAILED Stage {STUFE}: Command '{cmd[:60]}' exit={result.exit_code}. "
      "stderr: {result.stderr[:200]}. "
      "Lead muss entscheiden: Code-Fix + Re-Spawn ODER ABORT.")
    EXIT FAIL

  # PID-Extraction bei Start-Process-Patterns (z.B. 'Write-Host "PID: $($p.Id)"')
  pid_match = regex_search(result.stdout, r"PID[:\s]+(\d+)")
  IF pid_match:
    setup_artifacts.pids.append({cmd: cmd[:40], pid: int(pid_match.group(1))})
    Logge: "[TDD-SETUP] PID tracked: {pid_match.group(1)}"

  # Container-ID-Extraction (docker run/start output)
  container_match = regex_search(result.stdout, r"^[a-f0-9]{12,}$", multiline=true)
  IF container_match:
    setup_artifacts.container_ids.append(container_match.group(0))

  setup_artifacts.commands_executed.append({
    cmd: cmd[:200],
    exit_code: 0,
    duration_sec: result.duration_sec,
    stdout_preview: result.stdout[:200]
  })
  audit_jsonl_append({type: "SETUP_CMD_DONE", cmd_preview: cmd[:80], duration_sec: result.duration_sec})
```

---

## SCHRITT 4: Health-Check + Wait (INV-SETUP-7)

```
IF health_check_cmd != null:
  Logge: "[TDD-SETUP] Health-Check: {health_check_cmd[:80]}"
  max_wait_sec = setup_timeout_min * 60
  poll_interval = 5
  elapsed = 0
  healthy = false

  WHILE elapsed < max_wait_sec:
    result = Bash(health_check_cmd, timeout=10s)
    IF result.exit_code == 0:
      healthy = true
      BREAK
    Sleep(poll_interval)
    elapsed += poll_interval
    Logge: "[TDD-SETUP] Health-Check pending... ({elapsed}s / {max_wait_sec}s)"

  IF NOT healthy:
    # Healthcheck failed — Cleanup PIDs + FAIL
    FOR pid IN setup_artifacts.pids:
      Bash(f"kill {pid} 2>/dev/null || true")

    TDD-STATE.md UPDATE:
      state: SETUP_FAILED
      setup_error: {phase: "health_check", elapsed_sec: elapsed}

    audit_jsonl_append({type: "SETUP_HEALTHCHECK_FAILED", elapsed_sec: elapsed})
    SendMessage(team-lead,
      "SETUP HEALTHCHECK FAILED Stage {STUFE} nach {elapsed}s. "
      "Commands liefen erfolgreich, aber Service nicht erreichbar.")
    EXIT FAIL

  setup_artifacts.health_check_passed_at = now_iso
  Logge: "[TDD-SETUP] Health-Check PASS nach {elapsed}s"
```

---

## SCHRITT 5: SETUP_DONE schreiben + Lead notifizieren

```
TDD-STATE.md UPDATE:
  state: SETUP_DONE
  setup_artifacts: setup_artifacts

audit_jsonl_append({
  type: "SETUP_DONE",
  stage: STUFE,
  commands: |setup_artifacts.commands_executed|,
  pids: |setup_artifacts.pids|,
  containers: |setup_artifacts.container_ids|,
  total_duration_sec: (now - setup_artifacts.started_at).seconds
})

SendMessage(team-lead,
  "SETUP_DONE Stage {STUFE}: {N} commands, {M} PIDs tracked, "
  "{K} containers, healthcheck OK. _TDD_execute kann jetzt starten.")

EXIT SUCCESS
```

---

## OUTPUT-SCHEMA (TDD-STATE.md.setup_artifacts)

```yaml
setup_artifacts:
  pids:
    - cmd: "Start-Process pwsh -ArgumentList 'dotnet run'..."
      pid: 12345
  container_ids:
    - "abc123def456"
  started_at: 2026-05-12T16:00:00Z
  commands_executed:
    - cmd: "powershell.exe -Command 'docker-up.ps1 -Profile dev-backend'"
      exit_code: 0
      duration_sec: 45.2
      stdout_preview: "Containers started: 3"
    - cmd: "powershell.exe -Command 'Wait-ForHealthCheck.ps1 -Url ...'"
      exit_code: 0
      duration_sec: 28.5
      stdout_preview: "Healthy"
  health_check_passed_at: 2026-05-12T16:01:13Z
state: SETUP_DONE
```

---

## SETUP.COMMANDS-SCHEMA (BL-329 AK-4 — Prozess-Infra-Schema, WebHost-Klasse)

Ein `setup.commands`-Eintrag ist entweder ein **nackter String** (heutige Semantik,
ABWAERTSKOMPATIBEL) oder ein **dict** mit dem Prozess-Schema:

```yaml
setup:
  commands:
    # FORM 1 — nackter String (Abwaertskompat): run-to-completion, foreground,
    #          cwd=default, kein PID-Capture. UNVERAENDERT zu vor BL-329.
    - "docker-compose -f docker-compose.yml up -d"

    # FORM 2 — dict (Prozess-Klasse / WebHost): {cmd, cwd, background, pid_capture}
    - cmd: "dotnet run --urls https://localhost:5443"
      cwd: "src/Api"          # optional, default = Aufrufer-cwd
      background: true         # Start-Process/detached, kehrt sofort zurueck (KEIN run-to-completion)
      pid_capture: true        # gestartete PID -> TDD-STATE.setup_artifacts.pids -> Teardown killt sie
```

| Feld | Default (nackter String) | Bedeutung |
|------|--------------------------|-----------|
| `cmd` | (der String selbst) | auszufuehrender Befehl |
| `cwd` | `null` (default-cwd) | Arbeitsverzeichnis |
| `background` | `false` (foreground) | `true` = WebHost-Klasse: detached Start, kein Warten |
| `pid_capture` | `false` | `true` = PID tracken (Teardown = Prozess-Kill statt nur docker-down) |

**Normalisierung (rein, testbar):** `.claude/scripts/stage_infra_schema.py` —
`normalize_setup_command(entry)` / `normalize_setup_commands(list)`. Ein nackter
String → `{cmd, cwd:null, background:false, pid_capture:false}` (heutige Semantik,
KEIN Bruch). `expects_pid_kill()` markiert die WebHost-Klasse (pid_capture=true)
fuer den Teardown. Tests: `test_stage_infra_schema.py`.

**Prozess-Klasse (WebHost):** lokaler WebHost via `background: true` + `pid_capture: true`
→ `_TDD_setup` startet ihn detached, fasst die PID nach `setup_artifacts.pids`; das
spiegelt sich symmetrisch im `_TDD_teardown` (PID-Kill statt nur `docker-compose down`).

---

## INVARIANTEN

- INV-SETUP-1: NUR Commands aus stage_N.md.setup.commands (kein Inline-Erfinden)
- INV-SETUP-2: Sequenziell ausfuehren (parallele Setups via stage_N.md-Wave-Notation)
- INV-SETUP-3: command-FAIL → SETUP_FAILED + SendMessage + EXIT (kein Best-Effort)
- INV-SETUP-4: PID-Tracking PFLICHT bei Start-Process-Patterns (fuer Teardown)
- INV-SETUP-5: Idempotenz wenn stage_N.md.setup.idempotent=true (Healthcheck-Re-Confirm)
- INV-SETUP-6: Auto-SKIP wenn infrastruktur=none AND keine setup.commands
- INV-SETUP-7: Healthcheck-Wait mit Timeout (kein infinite loop)
- INV-SETUP-8 (BL-329 AK-4): setup.commands-Eintraege folgen dem Prozess-Infra-Schema
  (String ODER {cmd,cwd,background,pid_capture}); nackt-String = unveraenderte
  Abwaertskompat-Semantik. Normalisierung via stage_infra_schema.py.
- INV-SETUP-9 (BL-247 AK-5/AK-10): VOR Container-Spinup (SCHRITT 2.5) acquire der
  non-shareable Ressourcen NUR fuer concurrency_class IN {DEPENDS,EXCLUSIVE}
  (PARALLEL = teilbar → kein acquire); all-or-nothing via
  stage_resource_registry.acquire_all (SOA-4 Rollback). acquire-FAIL (LOCKED) →
  state=SETUP_FAILED + SendMessage + EXIT (kein Halb-Spinup) — Auspraegung von
  INV-SETUP-3 fuer Ressourcen. Klasse GELESEN aus BL-318, nicht neu klassifiziert.

---

## REGELN

- Keine Code-Edits (BL-NEW-52 — Setup ist nur Infrastruktur)
- Keine Test-Runs (BL-NEW-52 — Tests sind _TDD_execute's Job)
- PIDs MUESSEN getrackt werden (sonst kann _TDD_teardown sie nicht stoppen)
- Bei Healthcheck-Timeout: PID-Cleanup BEVOR EXIT (kein Zombie-Prozess)
- BL-NEW-58 — KEINE projekt-spezifischen Commands inline im Skill. Alles aus stage_N.md.

---

## VERWENDUNG (in `_I_orchestrate.md` Step 9b)

```
# Nach _TDD_init (Step 9 HiL-Wizard):
stage_meta = read("{WORKTREE_PATH}/.claude/meta/implementation/stage_{N}.md")

IF stage_meta.infrastruktur != "none" OR |stage_meta.setup.commands| > 0:
  # Lead spawnt Setup-Worker
  spawn @i-tddsetup-{slice}-s{N} mit:
    ZEILE 1: Skill(_TDD_setup, args="{SLICE} {STUFE} {ITERATION}")
    KURZLEBIG_PROMPT: { PFAD-KONTEXT, NAME }

  # Crown armieren (Estimated-Duration siehe _crown.md Tabelle)
  Skill(_crown, args="i-tddsetup-{slice}-s{N} _TDD_setup --model=sonnet --buffer-pct=100")

  # Lead wartet auf SETUP_DONE oder SETUP_FAILED
  IF Worker meldet SETUP_FAILED:
    ABORT Stage — Lead-Decision (Code-Fix + Re-Spawn ODER skip Stage)
  IF SETUP_DONE: weiter zu Step 10 _TDD_red
ELSE:
  Logge: "[I-PIPELINE] Step 9b SKIP — infrastruktur=none, kein Setup-Worker noetig"
```

---

## Ressourcen-Acquire (BL-368 resource_allocator)

`resource_allocator.py` ist die benannte THIN-Fassade ueber `stage_resource_registry`
(srr) und `factory_lock` (fl). Sie ist der EINE benannte 4-Verben-Vertrag fuer
non-shareable Ressourcen: **claim / lease / wait / release**. SCHRITT 2.5 SOLL
diese Fassade verwenden statt `stage_resource_registry` direkt aufzurufen.

**Fassade ist THIN:** keine eigene Lock-Semantik, kein mkdir/os.replace/rmtree,
kein eigenes Stale-Handling — delegiert ausschliesslich an srr und fl.

### Signaturen (aus `.claude/scripts/resource_allocator.py`)

```python
# Non-blocking single-attempt — Standardfall fuer Setup (kehrt sofort zurueck)
claim(resource_id: str, *, worker_id: str, ttl: int = 600, vault_root=None) -> bool

# Acquire mit explizitem TTL (Lease-Semantik, sonst identisch zu claim)
lease(resource_id: str, *, ttl: int = 600, worker_id: str, vault_root=None) -> bool

# Blocking mit Backoff-Retry — fuer koordinierte Wartezeiten (default timeout=60s)
acquire_with_wait(resource_id: str, *, worker_id: str, ttl: int = 600,
                  timeout: float = 60, backoff: list = None, vault_root=None) -> bool

# Atomares all-or-nothing acquire fuer mehrere Ressourcen (Rollback geerbt von srr)
acquire_all(resource_ids: list, *, worker_id: str, ttl: int = 600, vault_root=None) -> bool

# Gegenstueck zu allen acquire-Verben — owner-gated release
release(resource_id: str, *, worker_id: str, vault_root=None) -> bool
```

### Verwendung in SCHRITT 2.5 (concurrency_class IN {DEPENDS, EXCLUSIVE})

```python
from resource_allocator import acquire_all

acquired = acquire_all(
    concurrency_depends_on,   # resource_ids dieser Stage (BL-318)
    worker_id=WORKER_ID,
    vault_root=VAULT_ROOT     # optional; None = Standard-Vault
)
# acquired == False → SETUP_FAILED + EXIT (INV-SETUP-9, kein Halb-Spinup)
# acquired == True  → setup_artifacts.acquired_resources = sorted(concurrency_depends_on)
```

Fuer einzelne Ressourcen reicht `claim(...)` (non-blocking) oder
`acquire_with_wait(...)` (blocking mit Retry). `acquire_all` ist der Standardweg
fuer mehrere Ressourcen (all-or-nothing, Rollback intern).

**Abgrenzung:** Setup acquired (via claim/acquire_all), Teardown released (via release) —
symmetrisch. Der Allocator ist der benannte Eingang; `stage_resource_registry` ist
die Implementierung darunter (kein direkter Aufruf aus Setup/Teardown-Worker).
Heartbeat/TTL-Verlängerung während langer Setups: `renew(resource_id, worker_id=..., vault_root=...)`.

---

## BL-NEW-53 — Lehre (Projekt-agnostisch)

Bei Stages mit externer Infrastruktur (Container, DB, WebHost) gehoert Setup
nicht in `_TDD_execute` (verbotet, BL-NEW-52) und nicht in `_TDD_init`
(Single-Responsibility — Wizard). Eigener Setup-Executor erlaubt:
- Sauberen Pipeline-Step (9b conditional)
- Crown-Watchdog mit Setup-spezifischer Duration
- Idempotency-Garantie
- PID/Container-Tracking fuer Teardown

Symmetrisch zu `_TDD_teardown` (Step 18b). Beide skippt bei `infrastruktur=none`.

Case-Anchor: `.claude/_parking-lot.md` BL-NEW-53.
