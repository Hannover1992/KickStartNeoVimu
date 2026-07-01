# /_TDD_teardown — Stage-Teardown-Executor (BL-NEW-53)

```yaml
status: active
version: 1.0.0
created: 2026-05-12
type: building-block
op: TDD-SubCommand
phase: Teardown
chain_position: 18b (in _I_orchestrate TDD-Phase, NACH _TDD_check)
model_tier: sonnet
forbidden_models: [haiku]   # BL-NEW-51 — mehrstufige Cleanup-Sequenz
feature_anchor: BL-NEW-53
related:
  - _TDD_setup     (Step 9b, kommt VOR Test-Cycles, schreibt setup_artifacts)
  - _TDD_check     (Step 18, kommt VOR _TDD_teardown)
```

## ═══ SOFORT-ANWEISUNG (LIES DIES ZUERST) ═══

**DU FUEHRST `teardown.commands` AUS `stage_{STUFE}.md` AUS — BEST-EFFORT.**

- Du liest TDD-STATE.md.setup_artifacts (PIDs, Container-IDs).
- Du stoppst Prozesse + Container in umgekehrter Reihenfolge.
- Du fuehrst teardown.commands aus stage_N.md aus.
- Du **laeufst auch bei vorherigem ABORT/FAIL** (finally-Semantik).
- Du **brichst NICHT ab** bei einzelnen command-Failures (best-effort).

**REGEL: Setup ist Garantie. Teardown ist Hygiene.**
- Setup-FAIL → ABORT Stage
- Teardown-FAIL → log + continue (kein Zombie-Container ist akzeptabel, aber Pipeline darf nicht haengen)

## ═══ ENDE SOFORT-ANWEISUNG ═══

---

## SCHRITT 0.0 (PFLICHT — BL-NEW-45 SKILL-LOAD-VERIFIKATION)

```
Verifiziere Skill-Load. Bei Inline-AUFTRAG: ABORT mit BL_NEW_45_VIOLATION.
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
║  VERTRAG: _TDD_teardown                                              ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {WORKTREE_PATH}/.claude/meta/implementation/stage_{STUFE}.md      ║
║      → teardown.commands, teardown.timeout_min, teardown.always_run ║
║      → infrastruktur                                                 ║
║    {BL_FOLDER}/meta-overrides/stage_{STUFE}.md (optional)            ║
║    {WORKTREE_PATH}/.claude/TDD-STATE.md                              ║
║      → setup_artifacts.{pids, container_ids} (von _TDD_setup)        ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {WORKTREE_PATH}/.claude/TDD-STATE.md                              ║
║      state: TEARDOWN_DONE | TEARDOWN_PARTIAL                         ║
║      teardown_artifacts:                                             ║
║        pids_stopped: [int, ...]                                      ║
║        pids_failed: [int, ...]                                       ║
║        resources_released: [str, ...]  (BL-247 AK-6)                 ║
║        commands_executed: [...]                                      ║
║        commands_failed: [...]                                        ║
║        finished_at: ISO                                              ║
║                                                                      ║
║  AKTOR:  _I_orchestrate Step 18b (NACH _TDD_check, VOR _I_verify)    ║
║  MODELL: sonnet                                                      ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    INV-TEARDOWN-1: Best-Effort — command-FAIL stoppt NICHT die       ║
║                     Sequenz (anders als Setup)                       ║
║    INV-TEARDOWN-2: Reverse-Order — PIDs zuerst stoppen, dann         ║
║                     Container teardown                               ║
║    INV-TEARDOWN-3: Finally-Semantik — laeuft auch nach ABORT/FAIL    ║
║                     (always_run: true) — deckt auch BL-247           ║
║                     resource-release (SCHRITT 2.5) ab                ║
║    INV-TEARDOWN-4: State NIE ABORT — entweder TEARDOWN_DONE oder     ║
║                     TEARDOWN_PARTIAL (bei einzelnen Fails)           ║
║    INV-TEARDOWN-5: Auto-SKIP bei infrastruktur=none AND keine        ║
║                     teardown.commands AND keine setup_artifacts      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## SCHRITT 0.4: Stage-Kontext laden

> **Stage-Resolution (BL-392 AK-CONSUMER-REWRITE):** Die Stage-Doc-Aufloesung laeuft ueber den
> kanonischen `resolve_vault_stage`-Resolver (Dual-Read). Ist die Stage in den Vault migriert
> (`{VAULT}/Stage/stage_N_<name>/`), liest der Teardown-Worker NUR den `teardown`-Slice (single unit
> of work); sonst faellt der Resolver auf den Legacy-Monolith
> `.claude/meta/implementation/stage_N.md` zurueck (IDENTISCH zu heute). Der folgende
> `parse_yaml_frontmatter(...stage_N.md)`-Pseudocode beschreibt den Legacy-Fallback-Pfad; kanonisch
> ist `resolve_vault_stage.resolve_slice(STUFE, "teardown")`.

```
stage_meta = parse_yaml_frontmatter("{WORKTREE_PATH}/.claude/meta/implementation/stage_{STUFE}.md")

override_path = "{BL_FOLDER}/meta-overrides/stage_{STUFE}.md"
IF EXISTS(override_path):
  stage_meta = merge(stage_meta, parse_yaml_frontmatter(override_path))

infrastruktur        = stage_meta.infrastruktur            # none | testcontainers | docker | docker-compose
teardown_commands    = stage_meta.teardown.commands        ?? []
teardown_timeout_min = stage_meta.teardown.timeout_min     ?? 2
teardown_always_run  = stage_meta.teardown.always_run      ?? true

audit_jsonl_append({type: "STAGE_CONTEXT_LOADED", skill: "_TDD_teardown", stage: STUFE})
```

---

## SCHRITT 1: setup_artifacts lesen + Auto-SKIP-Detection

```
tdd_state = read TDD-STATE.md (falls vorhanden)
setup_artifacts = tdd_state.setup_artifacts ?? null

# Auto-SKIP: keine externe Infra, keine teardown commands, keine PIDs/Container
IF infrastruktur == "none" AND |teardown_commands| == 0 AND setup_artifacts == null:
  Logge: "[TDD-TEARDOWN] Auto-SKIP — kein Teardown-Bedarf"
  TDD-STATE.md UPDATE:
    state: TEARDOWN_DONE
    teardown_artifacts: { skipped: true, reason: "no_infra" }
  audit_jsonl_append({type: "TEARDOWN_SKIPPED", reason: "no_infra"})
  SendMessage(team-lead, "TEARDOWN SKIPPED — kein Cleanup noetig")
  EXIT SUCCESS
```

---

## SCHRITT 2: PIDs stoppen (Reverse-Order, INV-TEARDOWN-2)

```
teardown_artifacts = {
  pids_stopped: [],
  pids_failed: [],
  commands_executed: [],
  commands_failed: [],
  started_at: now_iso
}

IF setup_artifacts AND |setup_artifacts.pids| > 0:
  # Reverse-Order: zuletzt gestartete Prozesse zuerst stoppen
  FOR pid_entry IN reversed(setup_artifacts.pids):
    pid = pid_entry.pid
    cmd_label = pid_entry.cmd[:40]
    Logge: "[TDD-TEARDOWN] Stopping PID {pid} ({cmd_label})..."

    # Gentle stop zuerst (SIGTERM equivalent)
    result = Bash(f"taskkill /PID {pid} /T 2>nul || kill -TERM {pid} 2>/dev/null", timeout=10s)

    IF result.exit_code == 0:
      teardown_artifacts.pids_stopped.append(pid)
      Logge: "[TDD-TEARDOWN] PID {pid} stopped"
    ELSE:
      # Force-stop (SIGKILL equivalent) als Fallback
      Bash(f"taskkill /PID {pid} /F 2>nul || kill -9 {pid} 2>/dev/null", timeout=5s)
      Bash_check = Bash(f"taskkill /PID {pid} 2>nul; ps -p {pid} 2>/dev/null", timeout=3s)
      IF Bash_check.exit_code != 0:
        teardown_artifacts.pids_stopped.append(pid)   # process gone after force-kill
        Logge: "[TDD-TEARDOWN] PID {pid} force-stopped"
      ELSE:
        teardown_artifacts.pids_failed.append(pid)
        Logge: "[TDD-TEARDOWN] WARN PID {pid} konnte nicht gestoppt werden"
        audit_jsonl_append({type: "TEARDOWN_PID_FAIL", pid: pid})
```

---

## SCHRITT 2.5: Ressourcen-release (BL-247 AK-6, INV-TEARDOWN-3 finally + INV-TEARDOWN-2 Reverse-Order)

```
# ── BL-247: die in _TDD_setup (SCHRITT 2.5) acquirierten non-shareable Ressourcen
#    werden hier wieder freigegeben. Liegt in der bestehenden INV-TEARDOWN-3-finally-
#    Semantik (always_run) → release laeuft AUCH nach ABORT/FAIL/Crash, kein
#    verwaister Lock durch normalen Abbruch. release selbst ist NICHT hier gebaut —
#    es kommt aus stage_resource_registry.release (AK-3 TDD-gedeckt).

# Quelle der gehaltenen resource_ids: setup_artifacts.acquired_resources (von _TDD_setup
# geschrieben, sortiert wie acquire_all sie acquiriert hat). Fehlt das Feld (Stage war
# PARALLEL/teilbar, kein acquire) → nichts freizugeben → SKIP.
acquired_resources = setup_artifacts?.acquired_resources ?? []

IF |acquired_resources| > 0:
  # INV-TEARDOWN-2: REVERSE-Order der acquire-Reihenfolge (symmetrisch zu PIDs).
  # acquire_all hielt sorted(resource_ids) → reverse(sorted) beim release.
  FOR rid IN reversed(acquired_resources):
    Logge: "[TDD-TEARDOWN] BL-247 releasing resource {rid} (reverse-order)..."
    # owner-gated release; nutzt factory_locks _robust_rmtree (gone-Wahrheit).
    # KEIN direkter res__-Key — die API kapselt das FS-Encoding (resource_id rein).
    released = stage_resource_registry.release(rid, worker_id = {WORKER_ID})
    IF released:
      teardown_artifacts.resources_released = (teardown_artifacts.resources_released ?? []) + [rid]
      audit_jsonl_append({type: "RESOURCE_RELEASED", resource: rid})
    ELSE:
      # Best-Effort (INV-TEARDOWN-1): nicht-owner / schon frei → log + weiter.
      Logge: "[TDD-TEARDOWN] WARN BL-247 release {rid} not-owner/bereits-frei (kein Fehler)"
      audit_jsonl_append({type: "RESOURCE_RELEASE_NOOP", resource: rid})
ELSE:
  Logge: "[TDD-TEARDOWN] BL-247 SKIP release — keine acquirierten Ressourcen (Stage war teilbar)"
```

> **Verwaiste Locks bei HART-Crash (AK-8):** Bricht der Prozess so hart ab, dass auch
> dieser finally-Teardown nicht mehr laeuft, faengt die geerbte BL-229-TTL-Stale-Mechanik
> den Lock (`is_bl_stale` reclaimt ihn beim naechsten `acquire`-Versuch). Dieser Schritt
> deckt den NORMALEN Abbruch (ABORT/FAIL/Test-Crash mit laufendem Teardown) ab —
> nicht neu gebaut, geerbt.

---

## SCHRITT 3: teardown.commands ausfuehren (INV-TEARDOWN-1 Best-Effort)

```
FOR cmd IN teardown_commands:
  Logge: "[TDD-TEARDOWN] Executing: {cmd[:80]}..."
  audit_jsonl_append({type: "TEARDOWN_CMD_START", cmd_preview: cmd[:80]})

  result = Bash(cmd, timeout_min=teardown_timeout_min)

  IF result.exit_code == 0:
    teardown_artifacts.commands_executed.append({
      cmd: cmd[:200],
      exit_code: 0,
      duration_sec: result.duration_sec
    })
    audit_jsonl_append({type: "TEARDOWN_CMD_DONE", cmd_preview: cmd[:80]})
  ELSE:
    # Best-Effort: log, dann WEITER (INV-TEARDOWN-1)
    Logge: "[TDD-TEARDOWN] WARN command failed: {cmd[:80]} (exit={result.exit_code})"
    teardown_artifacts.commands_failed.append({
      cmd: cmd[:200],
      exit_code: result.exit_code,
      stderr_preview: result.stderr[:200]
    })
    audit_jsonl_append({
      type: "TEARDOWN_CMD_FAIL_CONTINUE",
      cmd_preview: cmd[:80],
      exit_code: result.exit_code
    })
    # KEIN EXIT — weitermachen
```

---

## SCHRITT 4: Orphan-Cleanup (generic)

```
# Container-Orphan-Cleanup (best-effort, generisch)
IF infrastruktur IN ["docker", "testcontainers", "docker-compose"]:
  orphan_check = Bash("docker ps -a --filter 'status=exited' --format '{{.ID}}'", timeout=10s)
  IF orphan_check.exit_code == 0 AND orphan_check.stdout.strip():
    orphan_ids = orphan_check.stdout.strip().split("\n")
    Bash(f"docker rm {' '.join(orphan_ids)} 2>/dev/null || true", timeout=15s)
    Logge: "[TDD-TEARDOWN] Cleaned {|orphan_ids|} exited containers"
    audit_jsonl_append({type: "TEARDOWN_ORPHAN_CLEANUP", count: |orphan_ids|})
```

---

## SCHRITT 5: Final-State schreiben

```
teardown_artifacts.finished_at = now_iso
teardown_artifacts.duration_sec = (now - teardown_artifacts.started_at).seconds

# State-Entscheidung (INV-TEARDOWN-4)
IF |teardown_artifacts.pids_failed| == 0 AND |teardown_artifacts.commands_failed| == 0:
  final_state = "TEARDOWN_DONE"
ELSE:
  final_state = "TEARDOWN_PARTIAL"

TDD-STATE.md UPDATE:
  state: final_state
  teardown_artifacts: teardown_artifacts

audit_jsonl_append({
  type: "TEARDOWN_DONE",
  state: final_state,
  pids_stopped: |teardown_artifacts.pids_stopped|,
  pids_failed: |teardown_artifacts.pids_failed|,
  commands_executed: |teardown_artifacts.commands_executed|,
  commands_failed: |teardown_artifacts.commands_failed|
})

SendMessage(team-lead,
  "TEARDOWN {final_state} Stage {STUFE}: "
  "{N} PIDs stopped (failed={F}), "
  "{M} commands done (failed={E}). "
  "{advice}")
  # advice = "Pipeline kann weiter" wenn DONE, "Manual cleanup checken" wenn PARTIAL

EXIT SUCCESS
```

---

## PROZESS-KLASSE (BL-329 AK-4 — captured PID-Kill, WebHost-Klasse)

Symmetrisch zum `_TDD_setup`-Schema (`{cmd,cwd,background,pid_capture}`): ein
setup.commands-Eintrag mit `background: true` + `pid_capture: true` (WebHost-Klasse)
hat seine PID nach `TDD-STATE.setup_artifacts.pids` geschrieben. Der Teardown stoppt
sie als **Prozess-Kill** (SCHRITT 2, reverse-order) — nicht nur via
`docker-compose down`. So deckt der Teardown auch lokal-gestartete WebHosts/Dev-Server
ab, die kein Container sind. Die `teardown.commands` koennen denselben String-ODER-dict-
Schema-Eintrag tragen (Normalisierung: `.claude/scripts/stage_infra_schema.py`); ein
nackter String bleibt unveraenderte Abwaertskompat-Semantik.

---

## INVARIANTEN

- INV-TEARDOWN-1: Best-Effort (anders als Setup) — command-FAIL stoppt NICHT die Sequenz
- INV-TEARDOWN-2: Reverse-Order — PIDs zuerst (zuletzt-gestartete zuerst stoppen)
- INV-TEARDOWN-3: Finally-Semantik — laeuft auch nach ABORT/FAIL
- INV-TEARDOWN-4: State entweder TEARDOWN_DONE oder TEARDOWN_PARTIAL — nie ABORT
- INV-TEARDOWN-5: Auto-SKIP nur wenn infrastruktur=none + keine commands + keine artifacts
- INV-TEARDOWN-6 (BL-329 AK-4): captured PIDs der WebHost-Klasse (setup.commands mit
  pid_capture=true) werden als Prozess-Kill gestoppt (reverse-order), nicht nur docker-down.
- INV-TEARDOWN-7 (BL-247 AK-6): in _TDD_setup acquirierte non-shareable Ressourcen
  (setup_artifacts.acquired_resources) werden via stage_resource_registry.release in
  REVERSE-Order der acquire-Reihenfolge freigegeben (SCHRITT 2.5). Liegt in der
  INV-TEARDOWN-3-finally-Semantik (laeuft auch nach ABORT/FAIL/Crash) → kein verwaister
  Lock durch normalen Abbruch. Best-Effort (not-owner/bereits-frei = log + weiter).
  HART-Crash-Locks fangen die geerbte BL-229-TTL-Stale-Mechanik (AK-8), nicht hier.

---

## REGELN

- Niemals fail-fast bei einzelnem command (Hygiene > Garantie)
- PIDs gentle-stop zuerst, dann force-stop (verhindert Datenverlust bei DB-Containern)
- Orphan-Cleanup ist immer best-effort und projekt-agnostisch (generic `docker ps`)
- Teardown muss schnell sein — Crown-Watchdog 5 min reicht typisch

---

## VERWENDUNG (in `_I_orchestrate.md` Step 18b)

```
# Nach _TDD_check (Step 18), VOR _I_verify (Step 19):
stage_meta = read("{WORKTREE_PATH}/.claude/meta/implementation/stage_{N}.md")

# Run teardown ALWAYS (finally-Semantik), auch wenn TDD-Cycle ABORTED:
IF stage_meta.infrastruktur != "none" OR setup_artifacts existed:
  spawn @i-tddteardown-{slice}-s{N} mit:
    ZEILE 1: Skill(_TDD_teardown, args="{SLICE} {STUFE} {ITERATION}")
    KURZLEBIG_PROMPT: { PFAD-KONTEXT, NAME }

  Skill(_crown, args="i-tddteardown-{slice}-s{N} _TDD_teardown --model=sonnet --buffer-pct=50")

  # Lead wartet auf TEARDOWN_DONE/PARTIAL — KEIN ABORT bei PARTIAL
  IF TEARDOWN_PARTIAL: log + continue
  IF TEARDOWN_DONE:   continue
ELSE:
  Logge: "[I-PIPELINE] Step 18b SKIP — kein Teardown noetig"
```

---

## Ressourcen-Release (BL-368 resource_allocator)

`resource_allocator.py` ist die benannte THIN-Fassade ueber `stage_resource_registry`
(srr) und `factory_lock` (fl). Der Teardown SOLL diese Fassade verwenden statt
`stage_resource_registry.release` direkt aufzurufen.

**Fassade ist THIN:** keine eigene Lock-Semantik, kein mkdir/os.replace/rmtree —
delegiert ausschliesslich an srr und fl.

### Signatur fuer Release (aus `.claude/scripts/resource_allocator.py`)

```python
# Owner-gated release — Gegenstueck zu claim/lease/acquire_with_wait/acquire_all
release(resource_id: str, *, worker_id: str, vault_root=None) -> bool
# True  = caller war Owner, Ressource freigegeben
# False = caller nicht Owner ODER Ressource war bereits frei (kein Fehler, log + weiter)
```

### Verwendung in SCHRITT 2.5 (INV-TEARDOWN-7, finally-Semantik)

```python
from resource_allocator import release

# acquired_resources kommt aus setup_artifacts.acquired_resources (von _TDD_setup geschrieben)
for rid in reversed(acquired_resources):   # REVERSE-Order (symmetrisch zu acquire)
    released = release(rid, worker_id=WORKER_ID, vault_root=VAULT_ROOT)
    # Best-Effort (INV-TEARDOWN-1): False = log + weiter, kein Abbruch
```

**Abgrenzung:** Setup acquired (via `claim`/`acquire_all`), Teardown released (via
`release`) — symmetrisch, der Allocator ist der benannte 4-Verben-Vertrag.
`stage_resource_registry` ist die Implementierung darunter (kein direkter Aufruf
aus Teardown-Worker). INV-TEARDOWN-3 (finally) gilt auch fuer den release-Schritt:
release laeuft AUCH nach ABORT/FAIL, kein normaler Abbruch hinterlaesst einen
verwaisten Lock. HART-Crash-Locks faengt die BL-229-TTL-Stale-Mechanik (AK-8).

**Forward-Naht (T5/batch_5):** `register_teardown_hook` wird in batch_5 ergaenzt
und erlaubt es, den release automatisch als Hook zu registrieren (statt manuell in
SCHRITT 2.5). Bis dahin laeuft der release als expliziter Schritt in dieser Sektion.

---

## BL-NEW-53 — Lehre

Teardown ist Hygiene, nicht Garantie. Anders als Setup darf Teardown best-effort
sein — ein nicht-gestopptes Container-Orphan ist akzeptabel, ein endlos-haengender
Teardown ist es nicht. Always-run (finally-Semantik) sichert dass auch bei ABORT
keine Zombie-Prozesse bleiben.

Case-Anchor: `.claude/_parking-lot.md` BL-NEW-53.
