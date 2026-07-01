# /_TDD_monitor — Docker + Parallelism + FQN-Match Monitor (BL-NEW-62)

```yaml
status: active
model_tier: sonnet
forbidden_models: [haiku]   # BL-NEW-51 — mehrstufige Polling-Sequenz, Haiku ungeeignet
version: 1.0.0
created: 2026-05-12
type: building-block
op: TDD-SubCommand
phase: Monitor
chain_position: parallel-zu-Step-11/13/15/17
feature_anchor: BL-NEW-62
```

## ═══ SOFORT-ANWEISUNG (LIES DIES ZUERST) ═══

**DU BIST EIN READ-ONLY MONITOR. DU DARFST NICHTS AENDERN.**

- KEINE Code-Edits.
- KEINE Tests ausfuehren.
- KEINE Container starten/stoppen.
- KEINE Konfiguration anfassen.

**ERLAUBT (read-only):**
- `Bash("docker stats --no-stream")` / `Bash("docker ps")`
- `Bash("ps -ef | grep dotnet")` (oder PS-Aequivalent unter Windows)
- `Read(TRX-Datei)` (poll Test-Progress)
- `Read(TDD-STATE.md)` (Termination-Detection)
- `Schreibe TDD-STATE.md.monitor.{...}` (eigene Section, nicht state)
- `SendMessage(team-lead, "ALERT: ...")` bei Anomalie

**Du LAEUFST PARALLEL zu `_TDD_execute`-Worker. Sterbe wenn der fertig ist.**

## ═══ ENDE SOFORT-ANWEISUNG ═══

---

## SCHRITT 0.0 (PFLICHT — BL-NEW-45 SKILL-LOAD-VERIFIKATION)

```
VOR allem — verifiziere Skill-Load via Skill(_TDD_monitor), nicht inline.
Bei Inline-Pattern: ABORT mit BL_NEW_45_VIOLATION audit.
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
║  VERTRAG: _TDD_monitor                                                ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    KURZLEBIG_PROMPT.{fqn_list, parallelitaet_max, expected_test_count}║
║    {WORKTREE_PATH}/.claude/meta/implementation/stage_{N}.md          ║
║      → infrastruktur, ressourcen_constraints.parallelitaet_max,     ║
║         timeout_per_test_min                                        ║
║    {WORKTREE_PATH}/.claude/TDD-STATE.md  → state (Termination-Check)║
║    TRX-File (path aus testbefehl --logger trx;LogFileName=...)      ║
║    Docker daemon (stats/ps via Bash)                                ║
║    Process-Liste (ps -ef | grep dotnet)                             ║
║                                                                      ║
║  SCHREIBT (eigene Section, kollidiert nicht mit _TDD_execute):     ║
║    {WORKTREE_PATH}/.claude/TDD-STATE.md                             ║
║      monitor:                                                        ║
║        scan_count: int                                               ║
║        last_scan_at: ISO                                             ║
║        parallelism: {expected: N, actual: M, ratio: 0.xx}           ║
║        cpu_usage_avg: 0.xx                                           ║
║        mem_usage_avg_mb: int                                         ║
║        docker_containers_active: N                                  ║
║        docker_containers_healthy: N                                 ║
║        trx_test_count: N (running)                                   ║
║        trx_pass: N                                                   ║
║        trx_fail: N                                                   ║
║        fqn_match: PASS | MISMATCH (mit details)                      ║
║        stuck_detection: false | true (wenn TRX 5min stale)         ║
║        timing_outliers: [{test_name, duration_sec, threshold}]      ║
║        alerts: [{type, message, timestamp}]                          ║
║                                                                      ║
║  RUFT:                                                               ║
║    KEINE Skills (Monitor ist atomar).                               ║
║    SendMessage(team-lead, "ALERT: ...") bei Anomalie.               ║
║                                                                      ║
║  AKTOR:  parallel zu _TDD_execute-Worker (Steps 11/13/15/17)        ║
║  MODELL: sonnet (BL-NEW-51 verbietet haiku)                         ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    INV-MON-1: Read-only — KEIN State-Patch ausserhalb TDD-STATE.monitor ║
║    INV-MON-2: Termination wenn TDD-STATE.state IN {GREEN_VERIFIED,  ║
║               RED_VERIFIED, GREEN_FAILED, BUILD_FAILED, ABORT}      ║
║    INV-MON-3: Hard-Timeout 30min (sonst Zombie-Worker)              ║
║    INV-MON-4: Poll-Interval 30s — keine Tight-Loops (Token-Schonung)║
║    INV-MON-5: Bei Anomalie SOFORT SendMessage, nicht warten         ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## METHODOLOGIE (Poll-Loop)

### Schritt 1: Kontext laden (1x)

```
fqn_list             = KURZLEBIG_PROMPT.fqn_list ?? []
parallelitaet_max    = KURZLEBIG_PROMPT.parallelitaet_max
                     ?? stage_N.md.ressourcen_constraints.parallelitaet_max
                     ?? 8
expected_test_count  = |fqn_list|
infrastruktur        = stage_N.md.infrastruktur   # docker | testcontainers | docker-compose | none
trx_path             = parse testbefehl_template fuer --logger trx;LogFileName=...
                     ?? "$env:TEMP/it-latest.trx" (Default-Convention)

scan_count = 0
scan_start_at = now
alerts = []

Logge: "[MONITOR-INIT] expected_parallel={parallelitaet_max} expected_tests={expected_test_count} trx={trx_path}"
```

### Schritt 2: Poll-Loop

```
WHILE TDD-STATE.state NOT IN ["GREEN_VERIFIED", "RED_VERIFIED", "GREEN_FAILED", "BUILD_FAILED", "ABORT"]:

  # Hard-Timeout
  IF now - scan_start_at > 30 * 60:   # 30min
    alerts.append({type: "MONITOR_TIMEOUT", message: "Monitor lief 30min — Worker_A nicht DONE"})
    SendMessage(team-lead, "MONITOR-TIMEOUT: Worker A laeuft >30min ohne DONE — Stuck-Verdacht")
    BREAK

  Sleep(30s)
  scan_count += 1

  # ─── Docker-Stats ───────────────────────────────────────────
  IF infrastruktur IN ["docker", "testcontainers", "docker-compose"]:
    docker_stats = Bash("docker stats --no-stream --format '{{.Name}} {{.CPUPerc}} {{.MemUsage}}'")
    docker_ps    = Bash("docker ps --format '{{.Names}} {{.Status}}'")

    containers_active  = count_lines(docker_ps)
    containers_healthy = count(docker_ps matching "healthy")
    cpu_usage_avg      = avg(docker_stats.cpu_perc)
    mem_usage_avg_mb   = avg(docker_stats.mem_mb)

  # ─── Parallelism-Check ──────────────────────────────────────
  dotnet_procs = Bash("ps -ef | grep -c 'dotnet test'")   # Linux/Mac
                OR Bash("(Get-Process dotnet).Count")     # PowerShell
  parallelism_actual = dotnet_procs
  parallelism_ratio  = parallelism_actual / parallelitaet_max

  IF parallelism_ratio < 0.3 AND parallelism_actual < expected_test_count:
    alerts.append({
      type: "PARALLELISM_UNDERUSED",
      message: "Nur {parallelism_actual}/{parallelitaet_max} cores genutzt ({pct}%) bei {expected_test_count} Tests"
    })
    SendMessage(team-lead, "ALERT: Parallelism unter-genutzt — moegliche Single-Thread-Test-Run, Test-Discovery-Problem oder Container-Bottleneck")

  # ─── TRX-Progress ───────────────────────────────────────────
  IF EXISTS(trx_path):
    trx_content = Read(trx_path)
    trx_test_count = parse_trx_running_count(trx_content)
    trx_pass = parse_trx_passed(trx_content)
    trx_fail = parse_trx_failed(trx_content)
    trx_actual_fqns = parse_trx_test_names(trx_content)

    # FQN-Match-Check
    expected_set = set(fqn_list)
    actual_set   = set(trx_actual_fqns)
    extra_running = actual_set - expected_set

    IF |extra_running| > 0:
      alerts.append({
        type: "FQN_MISMATCH",
        message: "Tests laufen die NICHT in fqn_list: {extra_running.list()}"
      })
      SendMessage(team-lead, "ALERT: --filter scheint nicht zu wirken — {N} Extra-Tests laufen ausserhalb fqn_list")

    # Stuck-Detection
    IF scan_count > 10 AND trx_test_count == previous_trx_count:
      # 30s × 10 = 5min kein Progress
      stuck_detected = true
      alerts.append({
        type: "TRX_STUCK",
        message: "TRX-Test-Count seit 5min unveraendert ({trx_test_count}) — moeglicher Hang"
      })
      SendMessage(team-lead, "ALERT: Test-Run stuck — TRX zeigt seit 5min kein Progress")

  # ─── Timing-Profile (bei Test-Done) ─────────────────────────
  IF trx_test_count > previous_trx_count:
    new_tests = trx_test_count - previous_trx_count
    FOR each new test in TRX:
      duration_sec = parse_test_duration(trx, test_name)
      timeout_threshold = stage_N.md.ressourcen_constraints.timeout_per_test_min * 60

      IF duration_sec > timeout_threshold * 0.8:   # 80% von Timeout = Slow
        timing_outliers.append({
          test_name: test_name,
          duration_sec: duration_sec,
          threshold_sec: timeout_threshold
        })

  # ─── Output schreiben ───────────────────────────────────────
  TDD-STATE.md monitor section UPDATE mit:
    scan_count, last_scan_at, parallelism, cpu/mem, containers,
    trx_*, fqn_match, stuck_detection, timing_outliers, alerts

  previous_trx_count = trx_test_count

  audit_jsonl_append({
    type: "MONITOR_SCAN",
    scan: scan_count,
    parallel: parallelism_ratio,
    trx_progress: f"{trx_test_count}/{expected_test_count}",
    alerts_added: |alerts_this_scan|
  })

  Logge: "[MONITOR-{scan_count}] parallel={parallelism_actual}/{parallelitaet_max} TRX={trx_test_count}/{expected_test_count} alerts={|alerts|}"
```

### Schritt 3: Termination + Final-Report

```
# WHILE-Exit-Reason:
# - TDD-STATE.state = GREEN_VERIFIED / RED_VERIFIED / GREEN_FAILED / BUILD_FAILED / ABORT
# - Hard-Timeout 30min
# - Eigener BREAK

final_report = {
  scan_count: scan_count,
  duration_min: (now - scan_start_at) / 60,
  total_alerts: |alerts|,
  parallelism_avg_ratio: avg(history.parallelism_ratio),
  cpu_avg: avg(history.cpu_usage),
  test_throughput_per_min: expected_test_count / duration_min,
  exit_reason: TDD-STATE.state OR "TIMEOUT"
}

TDD-STATE.md.monitor.final_report = final_report

audit_jsonl_append({
  type: "MONITOR_DONE",
  exit_reason: final_report.exit_reason,
  alerts: |alerts|,
  parallelism_avg: final_report.parallelism_avg_ratio
})

SendMessage(team-lead, "MONITOR-DONE: {scan_count} scans, {|alerts|} alerts, parallelism_avg={parallelism_avg*100|round=1}%, throughput={throughput}/min")

EXIT
```

---

## OUTPUT-SCHEMA (TDD-STATE.md.monitor)

```yaml
monitor:
  spawned_at: 2026-05-12T14:00:00Z
  scan_count: 12
  last_scan_at: 2026-05-12T14:06:00Z
  parallelism:
    expected: 8
    actual_max: 6
    actual_avg: 4.5
    ratio_avg: 0.56
  cpu_usage_avg_pct: 42.3
  mem_usage_avg_mb: 1240
  docker_containers_active: 1
  docker_containers_healthy: 1
  trx_test_count: 10
  trx_pass: 10
  trx_fail: 0
  expected_test_count: 10
  fqn_match: PASS
  stuck_detection: false
  timing_outliers: []
  alerts: []
  final_report:
    scan_count: 12
    duration_min: 6.1
    total_alerts: 0
    parallelism_avg_ratio: 0.56
    cpu_avg: 42.3
    test_throughput_per_min: 1.64
    exit_reason: GREEN_VERIFIED
```

---

## INVARIANTEN

- **INV-MON-1:** Read-only auf System-State (kein Docker-Start/Stop, kein File-Edit ausser TDD-STATE.monitor)
- **INV-MON-2:** Termination wenn TDD-STATE.state setzt eindeutigen Final-Status
- **INV-MON-3:** Hard-Timeout 30min (Anti-Zombie)
- **INV-MON-4:** Poll-Interval 30s (Token-Schonung — bei 60min Run ~120 Polls, jeder ~1k tokens)
- **INV-MON-5:** Bei Anomalie SOFORT SendMessage (nicht batchen)
- **INV-MON-6:** BL-NEW-51 — Monitor lief NUR mit sonnet (haiku verboten)
- **INV-MON-7:** Parallel zum _TDD_execute-Worker, niemals als dessen Sub-Worker (W7 — kein Sub-Spawn)

---

## REGELN

- Kein Code editieren — NUR Monitoring
- Kein Container-Mgmt (BL-NEW-52 — Container-Lifecycle ist _TDD_init's Job)
- Kein --filter-Bypass (FQN-Liste aus KURZLEBIG_PROMPT ist source of truth)
- TRX-Path-Auto-Discovery: aus testbefehl-Template `LogFileName=...` parsen
- Bei fehlender TRX nach 2min: ALERT "TRX wird nicht geschrieben — Logger-Config falsch?"
- Stuck-Detection-Schwelle: 5min ohne Progress (10 Scans á 30s)

---

## VERWENDUNG (Dual-Worker-Spawn-Pattern, BL-NEW-62)

Im Lead (`_I_orchestrate` TDD-Phase Steps 11/13/15/17 ODER `_T_orchestrate` Test-Execution):

```
stage_meta = read("{WORKTREE_PATH}/.claude/meta/implementation/stage_{N}.md")

IF stage_meta.infrastruktur != "none":
  # PARALLEL Dual-Worker:
  PARALLEL_SPAWN([
    {
      worker_name: "i-tddexec-{slice}-s{N}-{red|green}-iN",
      skill: "_TDD_execute",
      model: "sonnet"   # BL-NEW-51
    },
    {
      worker_name: "i-tddmonitor-{slice}-s{N}-iN",
      skill: "_TDD_monitor",
      model: "sonnet"   # BL-NEW-51
    }
  ])

  # Crown fuer beide armieren:
  Skill(_crown, args="i-tddexec-{slice}-s{N}-iN _TDD_execute --model=sonnet --integration=true --buffer-pct=80")
  Skill(_crown, args="i-tddmonitor-{slice}-s{N}-iN _TDD_monitor --model=sonnet --buffer-pct=30 --max-rechecks=1")

ELSE:
  # Stage 1 Unit-Tests: Monitor unnoetig (lokale dotnet build + run, schnell)
  SINGLE_SPAWN _TDD_execute only
```

---

## BL-NEW-62 — Lehre (Projekt-agnostisch)

Bei Test-Execution mit externer Infrastruktur (Docker/Container/Compose) ist Black-Box-Verhalten Risiko: Tests koennen stuck sein, --filter koennte falsch wirken, Parallelism koennte unter-genutzt sein. Dual-Worker-Pattern macht diese Klassen detectable in Echtzeit:

- **Worker A (Test-Runner):** _TDD_execute, schreibt Test-State
- **Worker B (Monitor):** _TDD_monitor, schreibt System-State + Alerts

Beide parallel via Lead-Spawn. Lead's UI zeigt beide als Teammates. Anomalien werden via SendMessage gemeldet, nicht erst post-mortem in TRX gefunden.

Case-Anchor: `.claude/_parking-lot.md` BL-NEW-62.
