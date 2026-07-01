---
status: active
version: 3.0.0
created: 2026-05-27
updated: 2026-05-27 (v3.0 — Auto-Loop alle Batches bis Parking-Lot leer)
op: GoalParkingLot
type: command
chain_position: meta
governing_doc: Enforce_Refactor_Master_Analyse_2026-05-27.md
hard_constraint: "Voller Weg via /_help. enforceProcess=true. EINMAL aufrufen → ALLE PLs durchlaufen."
---

# /_goal_parking_lot v3.0 — Goal-Lauf bis Parking-Lot leer

## v3.0 Semantik (BREAKING)

**EIN Aufruf** = **ALLE offenen PL-Items abarbeiten**. Auto-Loop durch alle Batches.

```
v2.0 (alt): /_goal_parking_lot → 1 Batch → STOP → User ruft erneut
v3.0 (neu): /_goal_parking_lot → 1..N Batches sequentiell → STOP wenn 0 [ ] uebrig
```

**Termination:** parking-lot.md hat **0 offene `[ ]`-Items** (von den target_pls beim Start).

## Integration mit /goal — KRITISCH

**INV-GOAL-PATH-1:** `.claude/GOAL.md` ist EINZIGER gueltiger Pfad. /goal liest IMMER diese Datei.

**INV-GOAL-INVOKE-1:** Nutze **`/goal .claude/GOAL.md`** (Pfad-Form), NICHT `/goal {inline text}`.
- Pfad-Form: KEIN 4000-Char-Limit (Datei kann beliebig gross sein)
- Inline-Form: 4000-Char-Limit (Claude Code Built-in-Constraint)

**INV-GOAL-CONCISE-1:** GOAL.md hat eine **Concise-Prompt-Section (max 3500 chars)** als ersten
Inhalt, damit falls jemand `/goal {text}` mit Copy-Paste-Inhalt aus GOAL.md macht, das funktioniert.

## Aufruf

```
/_goal_parking_lot [--single-batch] [--prio=HIGH|MED|LOW] [--dry-run]
```

| Parameter | Default | Beschreibung |
|---|---|---|
| `--single-batch` | false | Falls true: v2.0-Verhalten (1 Batch und STOP) |
| `--prio` | alle | Filter (z.B. nur HIGH) |
| `--dry-run` | false | IDF clustert + GOAL.md schreiben, KEIN BDF-Start |

## Pseudocode (v3.0 Auto-Loop)

```python
def goal_parking_lot_v3(args):
    vault = resolve_vault_root()
    pl_path = vault / "_parking-lot.md"

    # 1. Discovery: alle offenen [ ]-Items
    target_pls = parse_open_pl_items(pl_path, prio_filter=args.prio)
    if not target_pls:
        return 0

    # 2. enforceProcess=true sichern
    set_enforce_process(vault, True)

    # 3. Concise GOAL.md schreiben (≤3500 chars Section 1)
    write_goal_md_v3(
        path=vault / ".claude" / "GOAL.md",
        mode="parking_lot_loop",
        target_pls=target_pls,
        auto_loop=not args.single_batch,
    )

    if args.dry_run:
        return 0

    # 4. AUTO-LOOP bis Parking-Lot leer
    iteration = 0
    MAX_ITERATIONS = 20  # Anti-Endlos
    while iteration < MAX_ITERATIONS:
        iteration += 1
        # 4a. IDF clustert pending PLs
        Skill(_IDF_orchestrate, args="--pl-only --from=sdf_finish")
        df_state = read_df_batch_state(vault)
        if not df_state.current_sub_batch:
            break  # Keine pending Batches mehr

        # 4b. BDF picks current_sub_batch
        Skill(_BDF_orchestrate, args="--resume")
        # → BDF → SDF → I → Auto-Chain PostBatch → Pre_PR
        # IDF-Dispatch via _A_postRoute (BL-226/BL-211): KEIN aktiver IDF-Dispatch via
        # BDF Phase 1.0 im proceed-Fall — A chaint direkt zu IDF (INV-A-EXCEPT-1).

        # 4c. Sanity-Process pro Batch
        Skill(_sanity_process, args=f"--batch={df_state.current_sub_batch}")

        # 4d. Pruefe ob noch offene PLs aus target_pls
        remaining = count_remaining_open_pls(pl_path, target_pls)
        if remaining == 0:
            break  # ALLE DONE

        if args.single_batch:
            break  # v2.0-Verhalten

    # 5. Final-Report
    write_enforce_test_report(vault, target_pls)
    return 0
```

## GOAL.md Template v3.0 (≤3500 chars Section 1)

```markdown
---
type: goal
mode: parking_lot_loop
auto_loop: true
target_pls: [LISTE_DER_10_PL_IDs]
date: 2026-05-27
session_origin: /_goal_parking_lot v3.0
enforce_process: true
max_iterations: 20
---

## CONCISE PROMPT (≤3500 chars für /goal-inline-Fallback)

```
Goal: Alle 10 offenen PL-Items im _parking-lot.md DCSRE-486 abarbeiten bis 0 [ ] uebrig.

Pipeline strikt pro Batch: IDF clustert → BDF picks → SDF Phase 1.1 modus → I-Pipeline min 5 Steps (M2) / 10 Steps (M3) → PostBatch → Pre_PR → Sanity-Process.

Auto-Loop: nach Batch DONE → IDF re-cluster pending → nächster Batch → bis 0 [ ] uebrig.

Termination wenn ALLE:
1. target_pls auf [x] in _parking-lot.md (0 offene aus Start-Liste)
2. process_audit.py GREEN pro Batch (kumuliert)
3. _guard_log.md: 0 ungelöste BLOCKED-Events
4. Sanity-Process-Reports pro Batch unter .claude/output/

Bei Hook-Block: Lead fixt Drift, Lauf läuft weiter mit nächstem Step. Goal-Hook bleibt offen bis alle Kriterien erfüllt + Parking-Lot-Section leer.

enforceProcess=true: Hooks blockieren HART. Mega-Worker → BLOCK. IDF schreibt batch_mode_hints (nicht batch_modes). SDF Phase 1.1 PFLICHT (kein lead_fallback). I-Pipeline mind 5/10 Skill-Loads. PostBatch + Pre_PR Auto-Chain.

Max 20 Iterationen (Anti-Endlos-Loop), dann ABORT mit Report.
```

---

# GOAL: Parking-Lot Loop — alle Target-PLs DONE

## Scope

**Start-Snapshot:** target_pls (Liste oben im Frontmatter)
**Auto-Loop:** EIN Aufruf → ALLE durchlaufen
**Stop-Bedingung:** 0 offene `[ ]` aus target_pls in _parking-lot.md

## Termination-Kriterien

1. **`grep -c "^### \[ \]" 6_PL/DCSRE-486-parking-lot.md` für target_pls == 0**
2. **`process_audit.py --multi-batch` GREEN** (alle Batches GREEN)
3. **`_guard_log.md`** zeigt 0 unresolved BLOCKED-Events
4. **Pro Batch ein Sanity-Process-Report**

## Pipeline (pro Iteration)

```
IDF (--pl-only) → DF_BATCH_STATE.current_sub_batch
  → BDF (--resume) picks
    → SDF Phase 1.1 modusEntscheidung (M2 oder M3)
    → SDF Phase 2.1 dispatch
    → I-Pipeline (min 5 Steps M2 / 10 Steps M3)
    → SDF Phase 3 (4 Berater)
    → SDF Phase 4 loopDecision TERMINATE
  → Auto-Chain PostBatch_orchestrate
  → Auto-Chain Pre_PR_orchestrate
  → Sanity-Process pro Batch

WENN remaining open == 0: STOP
SONST: Re-Run IDF mit verbleibenden pending PLs
```

## Hooks aktiv (enforceProcess=true)

- guard_geist5 → IDF batch_mode_hints PFLICHT
- guard_geist6 → SDF Phase 1.1 PFLICHT
- guard_geist7 → I-Pipeline min Skill-Loads (5/10)
- guard_geist9 → 4 Post-SDF Berater PFLICHT
- guard_geist10 → SDF→PostBatch Auto-Chain
- guard_geist11 → PostBatch→Pre_PR Auto-Chain
- guard_stab1 → BERATER_OUTPUTS-Provenance
- guard_stab3 → M3: RED-Test vor Code-Edit
- guard_stab4 → Mega-Edit BLOCK
- process_audit_stop_hook → Stop blocked bei RED

## Resume-Pfad

Wenn unterbrochen:
1. `cat .claude/GOAL.md` → erkennt mode=parking_lot_loop + target_pls
2. `Skill(_BDF_orchestrate, args="--resume")` weiterlaufen mit current_sub_batch
3. Auto-Loop fängt verbleibende target_pls auf

## Max-Iterations (Anti-Endlos)

20 Iterationen. Bei jeder Iteration:
- 1 IDF-Cluster (~30-60s)
- 1 BDF→SDF→I-Pipeline (~5-15min M2)
- 1 PostBatch + Pre_PR (~2-5min)
- 1 Sanity-Process (~30s)

= ~10-25min pro Batch × 1-3 Batches je nach Cluster-Größe

10 PLs → vermutlich 2-3 Batches → ~30-75min total
```

## Wie /goal aufrufen (KRITISCH!)

```
RICHTIG:
  /goal .claude/GOAL.md       ← Pfad-Form, KEIN Limit

FALSCH (4000-Char-Limit):
  /goal "Goal: Alle 10 PL-Items... (>4000 chars)"   ← BLOCKED
```

## Verwandte Commands

- `/_goal_backlog` — Schwester für BL-Items (atomare 1-BL-Unit)
- `/_sanity_process --multi-batch` — Compliance über alle Batches
- `/_BDF_orchestrate` — Pipeline-Engine
- `/_IDF_orchestrate` — Cluster-Engine

## Changelog

### v3.0.0 (2026-05-27) — Auto-Loop bis Parking-Lot leer
- **BREAKING:** Default-Verhalten ist Auto-Loop über alle Batches
- `--single-batch` Flag für v2.0-Backward-Compat
- GOAL.md hat Concise-Prompt-Section (≤3500 chars für /goal-inline)
- INV-GOAL-INVOKE-1: Pfad-Form bevorzugen (KEIN Limit)
- Max-Iterations=20 (Anti-Endlos)

### v2.0.0 — IDF-driven 1-Batch-at-a-time (deprecated durch v3.0)

### v1.0.0 — Initial Release (Bulk-Pickup mit --max-items)
