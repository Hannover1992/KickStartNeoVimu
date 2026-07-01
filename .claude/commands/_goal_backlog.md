---
status: active
version: 1.0.0
created: 2026-05-27
op: GoalBacklog
type: command
chain_position: meta
governing_doc: Enforce_Refactor_Master_Analyse_2026-05-27.md
hard_constraint: "Voller Weg via /_help. ALLE Process-Enforce-Hooks aktiv (Geister G#2-G#11 + Stab S#1-S#10)."
---

# /_goal_backlog — Goal-Driven Backlog-Lauf mit Process-Enforce

## Zweck

Startet einen **Goal-Hook-gepowerten Lauf** der ALLE als READY/PLANNED markierten Backlog-Items
im aktiven Vault systematisch abarbeitet. **Voll Process-Enforce: jeder Hook der seit RCA-Refactor
2026-05-27 aktiv ist (Geister G#2-G#11, Stab S#1-S#10) blockiert Drift automatisch.**

Nach JEDEM Item-Done: `/_sanity_process --bl={ID}` zur Compliance-Verifikation.

> **IDF-Chain via _A_postRoute (BL-226/BL-211):** Nach erfolgreicher A-Pipeline (`routing=proceed`)
> chaint `_A_orchestrate` deterministisch direkt zu `_IDF_orchestrate` ueber `_A_postRoute` — kein
> `completion_signal=ready_for_bdf`-Polling, kein BDF-Roundtrip. `_goal_backlog` erwartet hier KEIN
> `ready_for_bdf`-Signal als Dispatch-Trigger (INV-A-EXCEPT-1).

## INTEGRATION MIT /goal — KRITISCH

**Single-Source-of-Truth-Pfad:** `.claude/GOAL.md` (relativ zum Projekt-Root).

```
Projekt-Root/
  .claude/
    GOAL.md          ← HIER schreibt /_goal_backlog die Goal-Definition
    GOAL.md.bak      ← Backup (vorherige GOAL.md beim Ueberschreiben)
    commands/
      _goal_backlog.md
      _goal_parking_lot.md
```

**Workflow mit /goal:**

```
1. User ruft /_goal_backlog [args]
   → Schreibt .claude/GOAL.md mit Termination-Kriterien
   → enforceProcess=true setzen
   → Starte Skill(_BDF_orchestrate, args="--resume")
   → Wenn /goal-Hook bereits aktiv: feuert weiter bis Termination
   → Wenn /goal-Hook nicht aktiv: User aktiviert mit /goal (liest dieselbe Datei)

2. /goal liest IMMER .claude/GOAL.md
   → Pruefe Termination-Kriterien
   → Wenn nicht erfuellt: feuert User-Prompt erneut
   → Wenn erfuellt: Termination-Notification

3. /_goal_backlog erneut → ueberschreibt .claude/GOAL.md
   → Vorheriges GOAL.md wird zu .claude/GOAL.md.bak
   → Neuer Scope, neuer Lauf
```

**INV-GOAL-PATH-1:** `.claude/GOAL.md` ist EINZIGER gueltiger Pfad. Keine `GOAL_*.md`,
keine Suffix-Variationen, keine alternativen Locations.

**INV-GOAL-PATH-2:** Beim Ueberschreiben: existing `.claude/GOAL.md` → `.claude/GOAL.md.bak`
(rolling 1 Backup, kein Verlauf).

## Architektur

```
┌─ /_goal_backlog ─┐
│                  │
│ 1. Lese          │  _backlog_index.md → filtere READY/PLANNED
│ 2. Schreibe      │  .claude/GOAL.md (Termination = alle BLs DONE + sanity GREEN)
│ 3. Setze         │  enforceProcess=true im aktiven Vault
│ 4. Starte        │  Skill(_BDF_orchestrate, args="--resume")
│ 5. Goal-Hook     │  feuert immer wieder bis Termination
│ 6. Pro Batch-DONE│  Skill(_sanity_process --bl={ID})
│ 7. Process-Audit │  process_audit_stop_hook.py blockt bei RED
└──────────────────┘
```

## Pre-Conditions

- `enforceProcess: true` im aktiven Vault `_session_params.md`
- Alle 13 neuen Hooks in `settings.json` registriert (gilt seit 2026-05-27)
- Mindestens 1 BL mit status=READY oder status=PLANNED in `_backlog_index.md`
- Branch `feature/bdf-{YYYY-MM-DD}` existiert oder kann erstellt werden

## Aufruf

```
/_goal_backlog [--max-items=N] [--include-sc-reif=true|false] [--enforce-process=MODE]
```

| Parameter | Default | Beschreibung |
|---|---|---|
| `--max-items` | 10 | Sicherheits-Stop nach N abgearbeiteten BLs |
| `--include-sc-reif` | true | Auch SC-REIF (nicht nur READY) einbeziehen |
| `--enforce-process` | **warn** | Process-Enforce-Mode (off/warn/hard) |
| `--dry-run` | false | Schreibt GOAL.md aber startet BDF nicht (zum Review) |

### Param `--enforce-process` Modi

| Mode | Verhalten | Wann nutzen |
|---|---|---|
| **`hard`** | `enforceProcess=true` in _session_params.md → Hooks BLOCKIEREN (continue:false) | Wenn Compatibility-Gap zw. Skills + Hooks bekannt + behoben (BL-218++ DONE). Sicherer Production-Mode. |
| **`warn`** (Default) | Hooks LOGGEN + WARNEN aber blocken nicht | **Erster echter Lauf** — wir sehen welche Hooks feuern wuerden ohne Pipeline-Abbruch. Liste der False-Positives + True-Positives sammeln. |
| **`off`** | Hooks komplett ueberbrueckt (env `OMNI_*_GUARD=0` fuer ALLE neuen Hooks) | Bei kritischer Production-Drift wo Hooks faelschlich blocken. Recovery-Mode. |

**Empfohlener Workflow:**
```
1. /_goal_backlog --max-items=1 --enforce-process=warn  ← ERSTER Lauf
   → Lauf laeuft durch, _guard_log.md zeigt alle Trigger
   → wir analysieren: legitime Blocks vs False-Positives
   → fixen die Compatibility-Gaps in existing Skills

2. /_goal_backlog --max-items=1 --enforce-process=hard  ← ZWEITER Lauf
   → mit gefixten Skills hart enforcen
   → Production-Ready
```

## Pseudocode

```python
def goal_backlog(args):
    # 1. Discovery: lese aktive BLs
    vault = resolve_vault_root()
    index_path = vault / "_backlog_index.md"
    target_bls = []
    for row in parse_backlog_index(index_path):
        if row.status in ("READY", "PLANNED"):
            target_bls.append(row.id)
        elif args.include_sc_reif and row.status == "SC-REIF":
            target_bls.append(row.id)

    if not target_bls:
        print("[GOAL-BACKLOG] Keine READY-BLs gefunden. Termination.")
        return 0

    print(f"[GOAL-BACKLOG] {len(target_bls)} BLs gefunden: {target_bls}")

    # 2. Schreibe GOAL.md — IMMER an .claude/GOAL.md (INV-GOAL-PATH-1)
    project_root = find_project_root()  # Verzeichnis das .claude/ enthaelt
    goal_path = project_root / ".claude" / "GOAL.md"
    if goal_path.exists():
        backup = project_root / ".claude" / "GOAL.md.bak"
        backup.unlink(missing_ok=True)  # vorheriges Backup loeschen
        goal_path.rename(backup)

    write_goal_md(goal_path, target_bls=target_bls, mode="backlog")
    print(f"[GOAL-BACKLOG] GOAL.md geschrieben: {goal_path}")
    print(f"[GOAL-BACKLOG] /goal liest diese Datei automatisch")

    # 3. enforce-process Mode anwenden
    enforce_mode = args.enforce_process or "warn"
    if enforce_mode == "hard":
        set_enforce_process(vault, True)
        # Plus: alle OMNI_*_GUARD env-vars auf "1" setzen (Test-Override)
    elif enforce_mode == "warn":
        set_enforce_process(vault, False)
        # Hooks loggen + warnen, blocken nicht
    elif enforce_mode == "off":
        set_enforce_process(vault, False)
        # Plus: alle OMNI_*_GUARD env-vars auf "0" (komplett aus)
        os.environ["OMNI_ALL_HOOKS_OFF"] = "1"
    print(f"[GOAL-BACKLOG] enforce-process Mode: {enforce_mode}")

    if args.dry_run:
        print(f"[GOAL-BACKLOG] DRY-RUN: GOAL.md geschrieben, BDF nicht gestartet.")
        return 0

    # 4. Starte BDF Pipeline (Team Lead direkt, INV-AO-CALLER)
    print("[GOAL-BACKLOG] Starte Skill(_BDF_orchestrate, args='--resume')")
    Skill(_BDF_orchestrate, args="--resume")

    # 5. Nach BDF-Completion: process_audit.py Sweep
    print("[GOAL-BACKLOG] BDF DONE. Starte /_sanity_process Master-Sweep.")
    Skill(_sanity_process, args="--scope=session")

    # 6. Final-Report
    write_enforce_test_report(vault, target_bls)
```

## GOAL.md Termination-Kriterien

Goal-Hook prueft folgende Bedingungen — Termination wenn ALLE erfuellt:

1. **Alle Target-BLs** haben status=DONE in `_backlog_index.md`
2. **process_audit.py** gegen jedes Target-BL gibt GREEN (exit 0) zurueck
3. **`_guard_log.md`** zeigt 0 noch-aktive BLOCKED-Events (alle gefixed)
4. **Pro BL** ein Sanity-Process-Report unter `.claude/output/Sanity_Process_{BL}_{DATE}.md`
5. **0 stuck Items** (BL_LIFECYCLE_STATE.items_stucked leer)

## Process-Enforce-Wirkung pro Pipeline-Phase

Aktive Hooks im Lauf (alle blocken automatisch):

| Pipeline-Stage | Aktiver Hook | Wirkung |
|---|---|---|
| BDF Phase 1.0 Post-A-Decision | guard_a_routing_target | routing_target nur in {BDF,IDF,STOP} |
| BDF→A | guard_geist2_bdf_to_a | nur UNREIF-BLs erlaubt |
| BDF→IDF | guard_geist4_bdf_to_idf | BL-Status ∈ {READY,SC-REIF,PLANNED} |
| IDF→SDF | guard_geist5_idf_to_sdf | IDF-Contract: batch_mode_hints + batch_stages |
| SDF Phase 1.1 | guard_modus_writer | batch_modes nur via SDF-Berater |
| SDF Phase 2.1 | guard_geist6_sdf_internal | BERATER_OUTPUTS.modusEntscheidung Pflicht |
| SDF→I | guard_geist7_sdf_to_i | Min 5 (M2) bzw 10 (M3) Skill-Loads |
| SDF→SC | guard_geist8_sdf_to_sc | Min Skill-Loads pro Modus |
| Post-SDF | guard_geist9_post_sdf | 4 Berater-Outputs Pflicht |
| SDF→PostBatch | guard_geist10_sdf_to_postbatch | TERMINATE muss PostBatch triggern |
| PostBatch→Pre_PR | guard_geist11_postbatch_to_pre_pr | batch_done muss Pre_PR triggern |
| Manifest-Edits | guard_stab1/2/4/5/7/8/9 | Provenance + Sequence + Anti-Drift |
| Code-Edits | guard_stab3_red_first | M3: RED-Test vor Code |
| Skill-Loads | guard_stab10_skill_args | Pflicht-Args |
| Batch-Start | guard_stab6_branch_hygiene | Branch-Sauberkeit |

**Bei Drift:** Hook gibt `continue:false` → Edit/Skill bricht ab → Lead muss korrekt nachfahren → Goal-Hook bleibt offen.

## Sanity-Process Auto-Integration

Nach jedem BL-Done (zwischen ITEM_DONE und naechstem SCANNING):

```python
# Im BDF Phase 4 Post-DONE-Check erweitern:
Skill(_sanity_process, args=f"--bl={current_bl_id} --auto-mode")
sanity_result = read_last_sanity_report()
if sanity_result.verdict == "RED":
    # Goal-Hook bleibt offen, items_failed += current_bl
    # Pipeline kann nicht progressieren bis fix
    items_failed.append(current_bl_id)
elif sanity_result.verdict == "YELLOW":
    # Warning, weiter aber loggen
    logger.warn(f"BL {current_bl_id} sanity YELLOW: {sanity_result.findings}")
else:
    # GREEN, items_done += current_bl
    items_done.append(current_bl_id)
```

## Output-Files

- `.claude/GOAL.md` (uberschrieben mit Target-BLs)
- `.claude/output/GoalBacklog_Run_{DATE}.md` (Final-Report)
- `.claude/output/Sanity_Process_{BL}_{DATE}.md` (pro BL)
- `_guard_log.md` (alle BLOCKED-Events des Laufs)
- `audit.jsonl` (alle Skill-Loads + Hook-Triggers)

## Beispiel

```
User: /_goal_backlog --max-items=3

[GOAL-BACKLOG] Discovery: 4 BLs gefunden: [BL-193, BL-218, BL-219, BL-220]
[GOAL-BACKLOG] max-items=3 → erste 3: BL-193, BL-218, BL-219
[GOAL-BACKLOG] GOAL.md geschrieben (Termination = 3 BLs DONE + Sanity GREEN)
[GOAL-BACKLOG] enforceProcess=true gesetzt
[GOAL-BACKLOG] Starte BDF...

Skill(_BDF_orchestrate, args="--resume")
[BDF] Phase 1: Initialisierung
[BDF] Phase 2: SCANNING — 3 Items im unified Pool (BL: 3)
[BDF] Phase 2.5: INTEREST_RADIUS — Matrix gebaut
[BDF] Phase 2b: BATCH_PLANNING
[BDF] Phase 3: ITEM_RUNNING [BL-193]
  Skill(_IDF_orchestrate, args="BL-193 --refresh-aks")
    [guard_geist4_bdf_to_idf] BL-193 status=READY → continue
    [IDF] Phase 7.6 metricPlanner...
      [guard_modus_writer] batch_modes ohne writer → BLOCK (enforce=true)
      [IDF] Retry mit batch_mode_hints → continue
    ...
  Skill(_SDF_orchestrate, args="BL-193 --task-source=backlog --batch=v3_01")
    [guard_geist5_idf_to_sdf] Contract OK → continue
    [SDF] Phase 1.1 modusEntscheidung → M3
    [SDF] Phase 2.1 EXECUTION DISPATCH → I-Pipeline
    Skill(_I_orchestrate, args="--stage=2 --tdd=true")
      Step 1: _I_cleanCodeArchitect → done
      Step 2: _I_requirementCheck → done
      ...
      Step 19: _I_verify → done
    [guard_geist7_sdf_to_i] 10/10 Min-Skills → continue
    Skill(_SDF_orchestrate_post)
      [guard_geist9_post_sdf] 4 Berater-Outputs OK → continue
      [Phase 4 loopDecision] TERMINATE
    [guard_geist10_sdf_to_postbatch] State armed
  Skill(_PostBatch_orchestrate, args="BL-193 --stages=1,2")
    [guard_geist10] PostBatch geladen → reset state
    Tests Stage 1: GREEN, Stage 2: GREEN
  Skill(_sanity_process, args="--bl=BL-193")
    [Sanity] Verdict: GREEN
[BDF] ITEM_DONE: BL-193

... Wiederhole fuer BL-218, BL-219 ...

[Goal-Hook] Termination-Check: 3/3 DONE + 3 Sanity GREEN → ERREICHT
[GOAL-BACKLOG] Final-Report: .claude/output/GoalBacklog_Run_2026-05-27.md
```

## INV-FRESH-SESSION-1 (Fresh-Session pro schwerem BL — BL-441)

**Bedingung:** Ein "schweres" BL (volle A/IDF/SDF-Pipeline, 30+ Worker-Spawns,
`needs_a_pipeline=true` ODER hoher k_score) laeuft NICHT im Marathon einer bereits
geladenen/kompaktierten Session.

**Aktion:** Vor dem Start eines schweren BL eine FRISCHE Session ziehen (Lead-Kontext
sauber). Im Goal-Backlog-Lauf bedeutet das: pro schwerem BL eine Fresh-Session-Grenze
(Cron/Schedule, siehe BL-441 AK-3) ODER — falls in-Session noetig — Berater
AUSSCHLIESSLICH als PLAIN synchrone Agent-Spawns (KEIN `team_name`), der
SYNC-DRIVE-W2-Bypass (BL-364/BL-441: PLAIN-sync-Returns liefern zuverlaessig,
async/SendMessage-Resume ist hook-blockiert).

**Begruendung:** SYNC-DRIVE-DOKTRIN H1 (BL-364/BL-441): in geladener Session rasten
async-Team-Worker vorzeitig (~6-12 tool-calls) + SendMessage-Resume ist PreToolUse-
hook-blockiert -> 30+-Worker-Marathon turn-fuer-turn unfahrbar.

**Auditierbarkeit:** Dieser Hinweis ist via git-diff sichtbar; Verstoss =
Marathon-Stall-Risiko.

## Caveats

- `enforceProcess=true` macht Hooks hart. Bei unerwartetem Drift bricht der Lauf ab. Recovery: `OMNI_*_GUARD=0` env oder zurueck auf `enforceProcess=false`.
- Mega-Worker-Pattern aus Round 11 wuerde JETZT von guard_geist7_sdf_to_i abgebrochen.
- IDF-Worker die noch `batch_modes` schreiben (vor BL-218 fix) wuerden von guard_modus_writer geblockt.

## Verwandte Commands

- `/_goal_parking_lot` — Schwester-Command fuer PL-Items
- `/_sanity_process` — Compliance-Check post-Pipeline (wird automatisch nach jedem BL gerufen)
- `/_BDF_orchestrate` — die Pipeline-Engine die das Goal-Backlog antreibt
- `/_help` — Pipeline-Spec (SOLL-Quelle)

## Changelog

### v1.0.0 (2026-05-27) — Initial Release
- Goal-Hook-driven Backlog-Lauf
- Voll Process-Enforce mit 13 Hooks aus Welle 1+2 (Geister G#2-G#11 + Stab S#1-S#10)
- Per-BL Sanity-Process Auto-Integration
- Termination = alle BLs DONE + alle Sanity GREEN
- Anchor: RCA DCSRE-486 Round 11 — verhindert die 4 CRITICAL-Drifts (F1/F2/F4/F5/F10)
