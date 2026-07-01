---
skill: _PC_orchestrate
status: scaffold
version: 0.1
bl_ref: BL-194
spec_ref: BL-194_Spec.md
created: 2026-05-21
implementation_modus: M1_skeleton
---

# _PC_orchestrate — Project-Coordinator Master Skill

## VERTRAG

**Zweck:** 1× pro Vault-Session-Start. Akquiriert `_master.lock`,
scannt Backlog nach READY-BLs, erstellt `dispatch_plan.txt` (WAL),
spawnt BL-Worker bis `parallelism_budget - 1` Slots belegt, ueberwacht
Heartbeats, bereinigt stale-Locks, released Master-Lock bei Abschluss.

**Pre-Condition (INV-PC-8):**
```
_session_params.parallelism_budget > 1
```
Bei `parallelism_budget=1` → SKIP (kein Aufruf, kein `.locks/`).

**Aufruf-Konvention:** Nur von Team-Lead (INV-AO-CALLER). Kein Sub-Agent-Spawn.

**Invarianten:**
- INV-PC-1: Max. 1 aktive PC-Instance pro Vault
- INV-PC-2: PC schreibt `.locks/`; Worker schreibt nur `heartbeat.txt` + `phase.txt`
- INV-PC-11: `dispatch_plan.txt` VOR Worker-Spawn schreiben (WAL-Prinzip)

---

## Abhängigkeiten

- BL-172 AK-3 DONE (git worktree add Bootstrap) — BLOCKER
- BL-176 DONE (Dep-Matrix fuer Dispatch-Set-Berechnung)
- BL-178 DONE (Index-Split — PC scannt nur Aktiv-Teil)
- `factory_lock.py` mit `acquire_bl()` + `release_bl()` vorhanden

---

## Phase 1: Master-Lock-Acquire (INV-PC-1)

```pseudocode
MASTER_LOCK_DIR = {VAULT_ROOT}/.locks/_master.lock/

Step 1.1: Check parallelism_budget
  budget = read_session_param("parallelism_budget")
  if budget <= 1:
    log("PC SKIP: parallelism_budget=1, no-op mode")
    EXIT 0

Step 1.2: Attempt _master.lock via mkdir-Pattern
  result = mkdir({VAULT_ROOT}/.locks/_master.lock/)
  if mkdir FAILS (exists):
    heartbeat_age = read_heartbeat_age(_master.lock)
    if heartbeat_age < 300s:
      // Another PC is alive — Observer Mode
      GOTO Phase 1.3 (Observer-Mode)
    else:
      // Stale master lock — reclaim (INV-PC-9: PC does reclaim)
      rmtree(_master.lock/)
      mkdir(_master.lock/)  // retry
      emit_audit("master_lock_stale_reclaim", {stale_age_seconds: heartbeat_age})

Step 1.3: Observer-Mode (wenn aktiver PC existiert)
  owner = read(_master.lock/owner.txt)
  active_bls = list_active_bl_locks()
  budget_used = len(active_bls)
  print(f"OBSERVER: PC active (owner={owner}), {budget_used}/{budget} slots used")
  print(f"Active BLs: {active_bls}")
  EXIT 0

Step 1.4: Write master lock metadata
  write(_master.lock/owner.txt, "claude-sess-{hex}")
  write(_master.lock/host.txt, hostname())
  write(_master.lock/started.txt, now_iso())
  write(_master.lock/heartbeat.txt, now_iso())
  emit_audit("pc_started", {owner: worker_id, budget: budget})
```

---

## Phase 2: Backlog-Scan + Dependency-Resolution

```pseudocode
Step 2.1: Scan _backlog_index.md (Aktiv-Teil via BL-178 Index-Split)
  ready_bls = [bl for bl in backlog if bl.status == "READY"]

Step 2.2: Filter via dependency_matrix (BL-176)
  dispatchable = [bl for bl in ready_bls
                  if all deps completed or not blocked]

Step 2.3: Filter already-locked BLs (running Workers)
  active_lock_bls = list_active_bl_locks()
  dispatchable = [bl for bl in dispatchable
                  if bl.id not in active_lock_bls]

Step 2.4: Pre-work Sanity-Check (INV-PC-12 — PL-10, DEFERRED)
  // TODO PL-10: check completed_bls list
  // dispatchable = [bl for bl in dispatchable
  //                 if bl.id not in factory_manifest.completed_bls]
```

---

## Phase 3: dispatch_plan.txt schreiben (WAL — INV-PC-11)

```pseudocode
// MUSS vor Worker-Spawn passieren (AK-1, INV-PC-11)
dispatch_plan = {
  created_at: now_iso(),
  budget: budget,
  planned_bls: [
    {bl_id: bl.id, status: "PENDING"} for bl in dispatchable[:budget-1]
  ]
}
write({VAULT_ROOT}/dispatch_plan.txt, yaml_dump(dispatch_plan))
emit_audit("dispatch_plan_written", {bls: [bl.id for bl in planned_bls]})
```

---

## Phase 4: Stale-Lock-Cleanup (INV-PC-9)

```pseudocode
// PC ist einzige Instanz die stale Locks reclaimt (INV-PC-9)
for lock_dir in list_all_bl_locks():
  heartbeat_age = age_seconds(lock_dir / "heartbeat.txt")
  if heartbeat_age > 300s:  // INV-PC-4: stale > 5min same-machine
    bl_id = lock_dir.stem.replace("BL-", "BL-")
    rmtree(lock_dir)
    // Update dispatch_plan.txt: mark bl_id as STALE_RECLAIMED
    emit_audit("lock_reclaim", {bl_id: bl_id, stale_age_minutes: heartbeat_age/60})
```

---

## Phase 5: BL-Worker-Spawn

```pseudocode
slots_available = budget - 1 - len(active_bl_locks())

for bl in planned_bls[:slots_available]:
  Step 5.1: Acquire BL-Lock (factory_lock.py acquire_bl)
    ok = factory_lock.acquire_bl(
      bl_id=bl.id,
      worker_id="claude-sess-{hex}",
      ttl=600
    )
    if not ok:
      log(f"WARN: Could not acquire lock for {bl.id}, skipping")
      continue

  Step 5.2: Update dispatch_plan.txt
    update_dispatch_status(bl.id, "SPAWNED")

  Step 5.3: Spawn BL-Worker via BDF --single-bl (PL-5, DEFERRED)
    // TODO PL-5: Skill(_BDF_orchestrate --single-bl={bl.id}
    //               --worktree={worktree_path}
    //               --lock-owner={worker_id})
    emit_audit("worker_spawned", {bl_id: bl.id, worker_id: worker_id})
```

---

## Phase 6: Heartbeat-Loop (PC selbst)

```pseudocode
// PC haelt _master.lock lebendig waehrend Workers aktiv sind
while active_workers_exist():
  write(_master.lock/heartbeat.txt, now_iso())
  sleep(60)  // INV-PC-4: 60s Intervall

  // Check fuer stale BL-Locks (Passe 4 Logik)
  GOTO Phase 4 (Stale-Cleanup)

  // Check fuer abgeschlossene Workers
  for lock in active_bl_locks():
    if lock.phase == "DONE":
      update_dispatch_status(lock.bl_id, "DONE")
      release_bl_lock(lock.bl_id)
```

---

## Phase 7: Resume-Logik (Crash-Recovery — PL-6, DEFERRED)

```pseudocode
// Beim Start: pruefen ob dispatch_plan.txt aus vorherigem Crash existiert
if dispatch_plan.txt exists and is_fresh(dispatch_plan.txt, max_age=3600):
  for bl in dispatch_plan.planned_bls:
    if bl.status == "SPAWNED":
      active_lock = check_bl_lock(bl.bl_id)
      if active_lock:
        log(f"Resume: {bl.bl_id} still running, skip re-spawn")
      else:
        log(f"Resume: {bl.bl_id} lock lost, re-spawning")
        GOTO Phase 5 (re-spawn this BL)
    elif bl.status == "PENDING":
      GOTO Phase 5 (spawn)
  emit_audit("dispatch_resumed", {recovered_from_crash: true})
```

---

## Phase 8: Release + Cleanup

```pseudocode
// Alle Workers fertig
rmtree({VAULT_ROOT}/.locks/_master.lock/)
emit_audit("pc_completed", {
  completed_bls: [bl.id for bl in done_bls],
  duration_seconds: elapsed
})
// dispatch_plan.txt BEHALTEN (WAL-Archiv fuer forensics)
// .locks/ Verzeichnis sollte jetzt leer sein (AK-11)
```

---

## Failure-Mode-Mapping (W7 → Schutzmechanismen)

| FM | Beschreibung | Schutz |
|----|-------------|--------|
| FM-1: PC-Crash waehrend Dispatch | WAL (dispatch_plan.txt) + Resume-Phase 7 | PL-6 |
| FM-2: Worker-Crash (stale heartbeat) | Phase 4 Stale-Cleanup (INV-PC-9) | PL-7 |
| FM-3: Lock-Steal (Rogue-Process) | Pre-write Lock-Validity-Check (AK-12) | PL-5 |
| FM-4: PT-Promotion Race | `_pt_promotion.lock` (INV-PC-6) | PL-8 |
| FM-5: _parking-lot.md concurrent write | READ-ONLY enforcement bei budget>1 | PL-11 |

---

## Implementierungs-Status

```
Phase 1: SKELETT (Observer-Mode + Master-Lock-Acquire Pseudocode)
Phase 2: SKELETT (Scan-Logik skizziert, Dep-Matrix-Integration TODO)
Phase 3: SKELETT (WAL-Format definiert, Impl DEFERRED PL-6)
Phase 4: SKELETT (Stale-Cleanup-Logik beschrieben, Impl DEFERRED PL-7)
Phase 5: SKELETT (Spawn-Logik, BDF --single-bl DEFERRED PL-5)
Phase 6: SKELETT (Heartbeat-Loop beschrieben)
Phase 7: DEFERRED (PL-6 — Resume/Crash-Recovery)
Phase 8: SKELETT (Release-Logik)
```

Vollimpl: Folge-BL (FOLGE-BL-194_full_implementation).
