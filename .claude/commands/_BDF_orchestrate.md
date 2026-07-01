# /_BDF_orchestrate - Big Dark Factory Meta-Orchestrator

```yaml
status: active
version: 3.8.0
created: 2026-03-20
updated: 2026-04-26
op: BigDarkFactory
phase: Meta
type: factory
chain_position: meta
difficulty_scaling: true
team_based: true
```

---

## BL-430: BDF → Roadmap-Engine (Rename-Doku, AK-6)

> **ENTKERNT (BL-430):** Big Dark Factory (BDF) wird konzeptuell zur **Roadmap-Executor-Engine** umbenannt.
> Der Name "Big Dark Factory" sowie alle Datei-/State-Namen bleiben als **Alias erhalten** — kein Hard-Rename
> in diesem Release (Backward-Compat). Der konzeptuelle Wandel ist vollzogen: BDF ist EXECUTOR der
> human-kuratierten Reihenfolge aus ROADMAP.md, nicht mehr autonomer Sortierer.

**Umbenannt (konzeptuell, Alias bleibt):**
- "Big Dark Factory" → "Roadmap-Executor" / "Roadmap-Engine"
- `/_BDF_orchestrate` → Alias für `/_Roadmap_orchestrate` (Datei-Rename via späteres BL)
- `BDF_PIPELINE_STATE` → bleibt als Feldname (State-Rename → späteres BL, ARCHITEKT-1-Folge)

**Bleibt als Alias (Backward-Compat, KEIN Hard-Rename in diesem Release):**
- `_BDF_orchestrate.md` (diese Datei)
- `BDF_PIPELINE_STATE`, `BDF_BATCH_STATE`, `BDF_NEXT_TRIGGER` in Manifest
- `bdf_max_items`, `bdf_status`, `bdf_ceiling`, `bdf_floor`

**Deferiert (ARCHITEKT-1-Folge-BL):** Hard-Rename der Datei + States → separates BL nach BL-430.

---

## BL-430: OUT-OF-SCOPE (AK-8)

**WAS BLEIBT (WIE-Schicht — unberührt von BL-430):**
- SDF-Handschuh-Wechsel (`Skill(_SDF_orchestrate)`) — EXECUTOR-Schicht, nicht WELCHE-Schicht
- BL-076 IDF-Delegation für BL-Items
- BATCH_PLANNING via `_BDF_batchPlan`
- BL-175 Factory-Lock (`factory_lock.py`)
- BL-173 Manifest-Routing (Scope-Split)
- Geist-Kette (Hooks/Guards)
- `/_goal_backlog`, `/_roadmap_backlog` als read-only KOMPASS (Brain)
- `BDF_PIPELINE_STATE`, `BDF_BATCH_STATE` als State-Container
- BL-082 DryRun-Modus
- PostBatch/Pre_PR-Chain

**WAS ENTKERNT WIRD (autonome WELCHE-Schicht, BL-430):**
- Phase 2.5 INTEREST_RADIUS (autonome BL-Dependency-Matrix + Sortierer) → ENTKERNT (AK-1)
- Phase 2 SCANNING autonome Prio-/Reifegrad-Sortierung (RF-BDF-027 unified-Merge + BL-081 Auto-Defer) → ENTKERNT (AK-2)
- BL-075 T2 autonome Reifungs-Such-Schleife → ENTKERNT (AK-3)

**STATTDESSEN (AK-4-Integration):**
Item-Reihenfolge aus `roadmap_status.parse_roadmap_order(.claude/ROADMAP.md)` — human-kuratierte ROADMAP-ORDER.

**BL-442 AK-4 (GAP-4, Multi-Lane zentraler Planer):** Bei aktiven parallelen Lanes (`_lane_plan.md` vorhanden)
waehlt BDF das naechste BL pro Lane KOLLISIONSFREI via `lane_plan.next_bl_for_lane(my_lane, plan, done)` —
das ueberspringt BLs, die eine ANDERE Lane haelt (queue/current), statt blind die globale ROADMAP-ORDER zu
nehmen. So teilt der zentrale Planer jeder Lane ihr naechstes disjunktes BL zu (kein Doppel-Bau, Fences gewahrt).
Single-Lane (kein `_lane_plan.md`): bisheriges ROADMAP-ORDER-Verhalten (backward-compat).
(Logik getestet: `.claude/scripts/lane_plan.py::next_bl_for_lane` + `test_lane_plan_planner.py`, 4/4.)

---

## BL-175 Factory-Lock (NEU 2026-05-19)

**INV-LOCK-1/2/3 aktiv** (siehe BL-175, `factory_lock.py`):

BDF hat KURZEN exklusiven Lock auf `{vault_root}/_factory_lock.md` waehrend Backlog-Index-Koordination.
Lock-frei waehrend Pipeline-Arbeit (A/IDF/SDF/SC/I) — die schreiben nur in `{BL}-Scope`.

| Phase | Lock-Action | Helper |
|---|---|---|
| Phase 1 INIT (vor SCANNING) | `acquire(scope='global', ttl=300, worker_id=terminal_id)` | `factory_lock.acquire(...)` |
| Phase 2 SCANNING | Lock gehalten. HeartbeatDaemon aktiv (alle 30s). | `HeartbeatDaemon(worker_id).start()` |
| Phase 3 BATCH_PLANNING | Lock gehalten. | — |
| Nach BATCH_PLANNING (vor ITEM_RUNNING) | `release(worker_id)` + Daemon stoppen | `factory_lock.release(...)` |
| ITEM_RUNNING (SDF laeuft) | Lock NICHT benoetigt | — |
| ITEM_DONE (vor Status-Update) | `acquire(...)` kurz | `factory_lock.acquire(...)` |
| Nach ITEM_DONE Status-Update | `release(worker_id)` | `factory_lock.release(...)` |

**Lock-File:** `{vault_root}/_factory_lock.md` (YAML-Frontmatter + Markdown-Log)

**Stale-Recovery:** TTL=300s. Nach TTL gibt Lock sich selbst frei (INV-LOCK-2).
Naechster BDF reclaimed automatisch: `factory_lock.acquire()` prueft Stale-Status.

**Contention:** Exponential-Backoff (1s, 2s, 4s, 8s, max 30s). Timeout=60s Default.
User-sichtbare Meldung: `[BDF-LOCK] Warte auf {holder} (lock_held_for={age}s, ttl=300s)`

**Script:** `py -3 .claude/scripts/factory_lock.py status` — zeigt aktuellen Lock-Status.

---

## BL-173 Manifest-Routing (NEU 2026-05-18)

**Manifest-Scope-Split aktiv** (siehe BL-173, INV-MANIFEST-SPLIT-1..4):

| State-Block | Heimat | Helper |
|---|---|---|
| BDF_PIPELINE_STATE | `{vault_root}/_factory_manifest.md` | `manifest_reader.read_factory_block("BDF_PIPELINE_STATE")` |
| BACKLOG_STATE | `{vault_root}/_factory_manifest.md` | `manifest_reader.read_factory_block("BACKLOG_STATE")` |
| GLOBAL_* | `{vault_root}/_factory_manifest.md` | `manifest_reader.read_factory_block("GLOBAL_*")` |
| FACTORY_STATES | `{vault_root}/_factory_manifest.md` | `manifest_reader.read_factory_block("FACTORY_STATES")` |

**Pfad-Aufloesung:**
- Factory-State: `manifest_reader.read_factory_block(...)` ODER direkt `{vault_root}/_factory_manifest.md`
- BL-State: `manifest_reader.read_bl_block(bl_id, ...)` ODER direkt `{bl_folder}/_manifest.md`
- Legacy-Fallback aktiv solange `is_split_active() == False` (1-Sprint-Uebergang)

**Migration:** `py -3 .claude/scripts/migrate_manifest_split.py migrate --vault-root="..." --rollback-tag=YYYY-MM-DD`

---

```
+======================================================================+
| META-COMMAND: /_BDF_orchestrate                                       |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU — reiner Orchestrator)                          |
|   CONSTRAINT: Team Lead fuehrt KEINE Sub-Commands selbst aus.        |
|   NUR spawnen, tracken, entscheiden.                                  |
|                                                                        |
| HANDSCHUH-WECHSEL: BDF → SDF → BDF (Puppet-Master-Pattern)          |
|   Team Lead laedt SDF-Skill SELBST: Skill(skill="_SDF_orchestrate") |
|   KEIN Worker-Spawn fuer SDF. KEIN Sub-Agent. NUR Handschuh-Wechsel.|
|   Nach SDF DONE: Team Lead liest Manifest, wechselt zurueck zu BDF. |
|                                                                        |
| PRINZIP: BDF = OUTER LOOP ueber Parking-Lot Items.                   |
|          Pro Item: 1 SDF-Lauf (INNER LOOP).                           |
|          State lebt im MANIFEST (BDF_PIPELINE_STATE).                 |
|          BDF schreibt NICHT in Parking-Lot (nur SDF via --task-source)|
|          Kommunikation BDF↔SDF: NUR ueber Manifest (R1).             |
|                                                                        |
| AUFRUF:                                                                |
|   /_BDF_orchestrate [max_difficulty=normal] [ceiling=opus]            |
|                     [floor=haiku] [bdf_max_items=10]                  |
|                     [testRun=true]                                     |
|                                                                        |
| LIEST:                                                                 |
|   {VAULT}/_manifest.md                 (BDF_PIPELINE_STATE)          |
|   {VAULT}/_parking-lot.md             (offene [ ] Items)            |
|   {VAULT}/_backlog_index.md           (BL-Items READY,              |
|                                         graceful if missing)          |
|   {VAULT}/Backlog/*.md (BL-Item Vault-Knoten,        |
|                                         Frontmatter: reifegrad)       |
|   {VAULT}/_session_params.md          (globale Parameter)           |
|                                                                        |
| SCHREIBT:                                                              |
|   {VAULT}/_manifest.md                 (BDF_PIPELINE_STATE Updates)  |
|   {VAULT}/_manifest.md                 (BL_LIFECYCLE_STATE.          |
|                                         items_stucked[] — T7)        |
|   {VAULT}/_manifest_protokoll.md       (Terminal-Rollover)           |
|   {VAULT}/_backlog_index.md           (BL-Status: READY->PLANNED)   |
|   {VAULT}/Backlog/BL-{NNN}-*.md (status-Feld)       |
|                                                                        |
| SCHREIBT NICHT:                                                        |
|   {VAULT}/_parking-lot.md             (NUR SDF, W16)                |
|   AUSNAHME: STUCKED [!] Promotion (RF-BDF-024, v2.1.0) —            |
|     BDF markiert Items als [!] wenn Pipeline 3x fehlschlaegt.        |
|   {VAULT}/_backlog_index.md            status DRAFT->READY           |
|     (jetzt BL_orchestrate, v3.0.0 BL-023)                            |
+======================================================================+
```

---

## ANTI-PATTERN Guard (RF-BDF-022, CS3 Root Cause)

```
╔══════════════════════════════════════════════════════════════════════╗
║  KERN-INVARIANTE: BDF ist reiner Dispatcher — KEIN Worker-Spawner   ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  VERBOTEN:                                                           ║
║    Agent(prompt="PL-26 ...") direkt spawnen                         ║
║    spawn_agent("PL-Item ...") aufrufen                              ║
║    Skill("_I_orchestrate") direkt aufrufen fuer Code-Aenderungen    ║
║    Skill("_SC_orchestrate") direkt aufrufen fuer Code-Aenderungen   ║
║    Komplexitaet/Modus selbst bewerten (SRS, COMPLEXITY, Fragilitaet)║
║      → Das ist SDF-Aufgabe (7-Modi-Logik in _SDF_orchestrate)       ║
║    Post-Phase-Schritte als TL-Direkt ausfuehren (INV-PM-3)         ║
║      → Jeder Post-Phase-Schritt braucht eigenen Agent-Spawn         ║
║                                                                      ║
║  RICHTIG:                                                            ║
║    Skill("_BDF_batchPlan") → Batch planen (Workers fuer PLANUNG OK) ║
║    Skill("_SDF_orchestrate", args="... --batch=...") → Code-Arbeit  ║
║    Manifest lesen → BDF_NEXT_TRIGGER pruefen → naechster Batch      ║
║    Post-Phase via Skill-Handschuh-Wechsel (INV-PM-3, AK-06-04)     ║
║                                                                      ║
║  AUSNAHME:                                                           ║
║    /_BDF_batchPlan darf Workers fuer PLANUNG spawnen (keine Code-    ║
║    Aenderungen, nur Lesen + Analyse)                                 ║
║                                                                      ║
║  PROZESS-INVARIANTEN (BL-016 Epic E3):                               ║
║    INV-PM-1: Worker-Pflicht ABSOLUT — auch bei Inline/Easy/Trivial  ║
║    INV-PM-2: Handschuh-Wechsel = Skill() — Agent() ist VERLETZUNG  ║
║    INV-AO-CALLER (V11/V12): Skill(_BDF_orchestrate) DIREKT vom      ║
║      Team Lead — kein Hub-Delegate (CLAUDE.md Z6, DCSRE-2014).      ║
║    INV-PM-4: Weg UND Ziel messen — Korrektheit KEIN Freifahrtschein║
║    INV-HW-1: SC ↔ SDF ↔ I — BDF delegiert IMMER an SDF             ║
║                                                                      ║
║  ROOT CAUSE (CS3, 2026-03-23):                                       ║
║    BDF hat Agent(PL-26 VV-Dependency) direkt gespawnt.              ║
║    Konsequenz: SDF komplett umgangen, 7-Modi-Logik ignoriert,        ║
║    kein Handschuh-Wechsel, kein Post-Implement-Check, kein GAP=0%.  ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

### Phase 0a: Worker-Awareness (BL-151 NEW-L2)

```python
# Worker bekommt Self-Awareness ueber Branch + BL-ID + Vault-Root.
# Wird im Spawn-Prompt mitgegeben damit Worker weiss WO er ist.
ctx = subprocess(.claude/scripts/current_context.py --format=json).stdout
worker_context = json.loads(ctx)
# worker_context = {branch, bl_id, vault_root, bl_folder, cwd}
Logge: "[ORCH-Phase0a] Worker-Context: branch={ctx.branch} bl_id={ctx.bl_id}"
```

### Phase 0d: N-Slot-Sanduhre (BL-200, 2026-05-24)

```python
# BDF bekommt N parallele BL-Lifecycle-Slots (default N=1, opt-in N>1).
# Slot-Allocation via project_coordinator.py (BL-194 Default BCCD).
# Bei N=1 (Default): aequivalent zu klassischem sequenziellen BDF — keine Verhaltensaenderung.
# Bei N>1: BDF kann mehrere READY-BLs gleichzeitig in jeweils eigene Worktrees pumpen.

n_slots = int(getenv("BDF_N_SLOTS", "1"))  # default sequenziell

IF n_slots > 1:
  # Pre-Check: project_coordinator.py erreichbar?
  result = subprocess([sys.executable, ".claude/scripts/project_coordinator.py",
                        "status", "--vault-root", vault_root])
  IF result.returncode != 0:
    Logge: "[BDF-SLOT] Coordinator nicht erreichbar — fallback n_slots=1"
    n_slots = 1
  ELSE:
    # Lese aktive Worktrees aus Coordinator-State
    coord_state = json.load(open("{vault_root}/.coordinator_state/coordinator.json"))
    active_worktrees = [wt for wt in coord_state["worktrees"].values()
                         if wt["status"] in ("idle", "busy")]
    available_slots = min(n_slots, len(active_worktrees))
    Logge: "[BDF-SLOT] n_slots={n_slots} aktiv={len(active_worktrees)} verwendbar={available_slots}"

# In Phase 2 SCANNING dann: nimm bis available_slots READY-BLs statt nur 1
# In Phase 4 ITEM_RUNNING: spawn parallele SDF-Skill-Loads (vorerst NICHT echt parallel,
# nur sequentiell mit Slot-Tracking — echte Parallelitaet bedingt Multi-Process via BL-194)
```

**INV-N-SLOT-1:** Default `BDF_N_SLOTS=1` — Verhalten identisch zu pre-BL-200.
**INV-N-SLOT-2:** Echte Parallelitaet erfordert mehrere Claude-Sessions in
separaten Terminals/Worktrees. BDF selbst spawnt KEIN Multi-Process. Pro Session
bleibt es sequenziell. Slot-Tracking dient nur dem Coordinator-Audit.

---

## Parameter

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `max_difficulty` | normal | easy, normal, hard | Maximale Schwierigkeit fuer SDF-Aufrufe |
| `ceiling` | opus | haiku, sonnet, opus | Hoechstes Modell |
| `floor` | haiku | haiku, sonnet | Niedrigstes Modell |
| `bdf_max_items` | 10 | 1..99 | Sicherheits-Stop nach N Items |
| `testRun` | false | true/false | Erzwingt testRun-Check manuell (OUT_OF_SCOPE Z1). Auto-Trigger bei EMPTY wenn testRun_done=false |
| `bdf_max_reifung_cycles` | 3 | 1..99 | BL-075 T2: max Reifungs-Delegationen an BL_orchestrate bevor Fallthrough in echten EMPTY |
| `bdf_max_scan_iterations` | 20 | 1..999 | BL-075 T4: Anti-Zirkel Hard-Break bei zu vielen SCANNING-Durchlaeufen (RF-BDF-034, INV-5) |
| `mode` | normal | normal, dryRun, testRun, postPhase | BL-082: dryRun mockt Phase 3 SDF-Aufruf, validiert Architektur ohne Code-Produktion |

---

## State-Machine (8 Zustaende)

```
# POST_PHASE via PostBatch (BL-133 Slice-5, AK-4) — frueher SDF Post-Phase-Modus (BL-041)
INIT → SCANNING → BATCH_PLANNING → ITEM_RUNNING → ITEM_DONE → SCANNING (Loop)
                                                            ↘ ABORTED (Terminal)
                ↘ EMPTY → TEST_RUNNING → SCANNING  (fail > 0, neue PL-Items)
                                       ↘ DONE      (fail == 0, SDF postPhase abgeschlossen)
                ↘ EMPTY → DONE         (testRun_done=true, SDF postPhase abgeschlossen)

Zustaende:
  INIT            Initialisierung, Parameter gesetzt
  SCANNING        Parking-Lot wird gescannt, offene [ ]-Items ermittelt
                  Terminal-Items [~][?][!] werden UEBERSPRUNGEN (RF-BDF-023)
  BATCH_PLANNING  /_BDF_batchPlan laeuft, Batch-Plan wird erstellt (RF-BDF-020)
  ITEM_RUNNING    SDF laeuft fuer aktuellen Batch (Handschuh-Wechsel)
  ITEM_DONE       SDF-Batch fertig, BDF_NEXT_TRIGGER gelesen, Ergebnis verarbeitet
  EMPTY           Kein OFFEN-Item mehr (ALLE_TERMINAL) → testRun-Guard prueft (RF-BDF-021, J3)
  TEST_RUNNING    SDF-testRun laeuft (Phase-0.5-Fork, S1→S5) — zwischen EMPTY und DONE
  ABORTED         BDF manuell gestoppt → Terminal (KEIN auto-ABORTED mehr durch SDF ABORT)
  # POST_PHASE entfaellt (BL-041) — PostBatch uebernimmt (BL-133 Slice-5, AK-4)

Terminal-Items (J3, pl-state-machine.md):
  [x] DONE     → BDF ignoriert, KEIN Batch
  [~] FREEZE   → BDF ignoriert, KEIN Batch
  [?] QUESTION → BDF ignoriert (HiL-Entscheidung ausstehend), KEIN Batch
  [!] STUCKED  → BDF ignoriert (max-Zyklen erschoepft), KEIN Batch
  items_blocked → BDF ignoriert (externe Abhaengigkeit fehlt), KEIN Batch

Uebergaenge:
  INIT          → SCANNING        (nach Initialisierung)
  SCANNING      → BATCH_PLANNING  (OFFEN-Items gefunden — RF-BDF-020)
  SCANNING      → EMPTY           (kein OFFEN-Item — ALLE_TERMINAL oder Parkplatz leer)
  BATCH_PLANNING→ ITEM_RUNNING    (Batch-Plan valide, SDF via Skill gestartet)
  BATCH_PLANNING→ SCANNING        (Batch-Plan leer/invalid → erneut scannen)
  ITEM_RUNNING  → ITEM_DONE       (BDF_NEXT_TRIGGER==true)
  ITEM_RUNNING  → SCANNING        (SDF ABORTED → auto-skip, items_failed+1 — RF-BDF-024)
  ITEM_DONE     → SCANNING        (naechstes Item suchen)
  A_PIPELINE_RETURN → SCANNING    (completion_signal empfangen, BL-032 RF-06 AK-06-02)
  EMPTY         → TEST_RUNNING    (testRun_done=false — Auto-Trigger)
  TEST_RUNNING  → SCANNING        (SDF-testRun: fail > 0, neue PL-Items geschrieben)
  TEST_RUNNING  → DONE            (SDF-testRun: fail == 0, SDF postPhase abgeschlossen)
  EMPTY         → DONE            (testRun_done=true, SDF postPhase abgeschlossen)

ANTI-PATTERN (RF-BDF-022):
  SCANNING → Agent() direkt     VERBOTEN — Root Cause CS3
  SCANNING → Skill(I_orch)      VERBOTEN — nur SDF entscheidet Modi
  SCANNING → Skill(SC_orch)     VERBOTEN — nur SDF entscheidet Modi
```

---

## Prozess-Statusanzeige RF-10 (BDF Outer-Loop Phasen)

Team Lead gibt nach JEDEM Phasenwechsel folgende Tabelle aus.
**Ziel: Alles auf 1 Blick** -- Phase, Aktion, Delegation, Status, Inhalt.

```
┌───────┬────────────────────────┬──────────────────────────┬──────────┬──────────────────────────────────────────────┐
│ Phase │ Aktion                 │ Agenten / Delegation     │ Status   │ Inhalt (Mini-Assay, NUR bei DONE)            │
├───────┼────────────────────────┼──────────────────────────┼──────────┼──────────────────────────────────────────────┤
│ 1     │ Initialisierung        │ Team Lead direkt         │ + DONE   │ Ceiling={ceiling}, {N} OFFEN-Items im PL     │
│ 2     │ SCANNING               │ Team Lead direkt         │ + DONE   │ {M} OFFEN, {K} Terminal, Batch: {items}      │
│ 3     │ BATCH_PLANNING         │ Skill(_BDF_batchPlan)    │ + DONE   │ Batch-Plan: {B} Items, Schw.: {diff}         │
│ 4     │ ITEM_RUNNING [{item}]  │ Skill(_SDF_orchestrate)  │ > ACTIVE │                                              │
│ 5     │ ITEM_DONE              │ Team Lead direkt         │ . PENDING│                                              │
│ 6     │ SCANNING (Loop)        │ Team Lead direkt         │ . PENDING│                                              │
│ --    │ POST_PHASE             │ Skill(_SDF --postPhase)  │ . PENDING│ SDF delegiert: Quality-Gates + Delivery       │
└───────┴────────────────────────┴──────────────────────────┴──────────┴──────────────────────────────────────────────┘
Items: {done}/{total} | Failed: {failed_count} | Zustand: {bdf_status} | K-Score: {k_score} ({k_label})
```

**Inhalt-Spalte:** 1-2 Saetze INHALTLICH (was verarbeitet/entschieden), NUR bei DONE.
**Status-Symbole:** + DONE, > ACTIVE, . PENDING, - SKIP, x FAIL
**Fusszeile:** Items done/total aus Manifest, failed_count, aktueller bdf_status.
**Wann:** Nach SCANNING DONE, BATCH_PLANNING DONE, ITEM_DONE -- vor Start der naechsten Phase.
**Kein RF-9:** BDF spawnt KEINE Worker direkt (RF-BDF-022). Wellen-Pattern nicht vorhanden.
**ITEM_RUNNING:** Item-ID in Klammern -- wird pro Batch aktualisiert.

---

## OUTER LOOP

### Phase 1: Initialisierung (RF-BDF-001)

```
# Parameter parsen
# INV-VAULT-9: WORKING_DIR einmalig hier aufloesen — ALLE nachgelagerten Manifest+PL Zugriffe nutzen {WORKING_DIR}/
WORKING_DIR = resolve_bl_path(BL_ID)  # INV-VAULT-9
bdf_default_difficulty = $ARGUMENTS.max_difficulty ?? "normal"
bdf_default_ceiling    = $ARGUMENTS.ceiling ?? "opus"
bdf_default_floor      = $ARGUMENTS.floor ?? "haiku"
bdf_max_items          = $ARGUMENTS.bdf_max_items ?? 10

# ═══ Phase 1.0: BDF-2 Post-A-Decision Entry (BL-130 Quick-Fix, 2026-04-18) ═══
# Wenn A-Pipeline den BDF mit --post-a-decision aufruft, ueberspringt BDF die
# normale Scan/Batch-Logik und springt direkt in den Decision-Modus.
# Entscheidet: weiter (→ IDF+SDF) / defer (→ naechstes BL) / nochmal A.
# BL-131 wird proper Version dokumentieren.
post_a_decision = $ARGUMENTS contains "--post-a-decision"
bl_name_arg = $ARGUMENTS.first_positional  # BL-XXX Name

IF post_a_decision AND bl_name_arg:
  Logge: "[BDF-2] Post-A-Decision fuer {bl_name_arg}"
  # ═══ BL-142 Phase 5D: Caller-Migration (ABGESCHLOSSEN) + BL-165 Naming-Disambiguierung ═══
  # Source-of-Truth: DF_BATCH_STATE.routing_decision + DF_BATCH_STATE.pipeline_route
  # A_PIPELINE_STATE.recommendation ist gestrichen — Mode-Decision wandert in SDF C3.
  # aggregat_score dient als Reifegrad-Hint; pro-Item-Entscheidung faellt in SDF C3.
  #
  # FIELD-DISAMBIGUIERUNG (BL-165):
  #   DF_BATCH_STATE.routing_decision ∈ {refine, proceed, defer}  — BDF-Post-A Routing-Entscheidung
  #                                                                   Owner: A-Pipeline / _A_berater_routing
  #   DF_BATCH_STATE.modus            ∈ {M1..M9}                  — SDF-Execution-Modus
  #                                                                   Owner: _SDF_berater_modusEntscheidung (ALLEIN)
  #   DF_BATCH_STATE.pipeline_route   ∈ {A, IDF, SDF, IDF+SDF, A_RETRY} — explizite Folge-Pipeline
  #   DF_BATCH_STATE.aggregat_score    — Reifegrad-Hint (0-100), optional, fuer Logging

  df_routing_decision = Lies {WORKING_DIR}/_manifest.md → DF_BATCH_STATE.routing_decision ?? null
  df_route            = Lies {WORKING_DIR}/_manifest.md → DF_BATCH_STATE.pipeline_route ?? null
  aggregat_score      = Lies {WORKING_DIR}/_manifest.md → DF_BATCH_STATE.aggregat_score ?? null

  IF df_routing_decision != null OR df_route != null:
    Logge: "[BDF-2] Routing via DF_BATCH_STATE (routing_decision={df_routing_decision}, route={df_route}, aggregat_score={aggregat_score})"
    route = df_route ?? (
      df_routing_decision == "refine" ? "A_RETRY"
      : df_routing_decision == "defer" ? "DEFER"
      : "IDF+SDF"  # proceed-Default
    )
  ELSE:
    # Fallback: kein DF_BATCH_STATE geschrieben (z.B. erster BDF-Lauf ohne A-Phase)
    Logge: "[BDF-2] DF_BATCH_STATE routing_decision+pipeline_route leer — Default-Route IDF+SDF"
    route = "IDF+SDF"

  # BL-226 AK-3 2026-05-30: Routing auf 2 aktive Pfade reduziert (A_RETRY + DEFER).
  # IDF/IDF+SDF/SDF-Dispatch DEPRECATED — die A-Pipeline chaint bei routing=proceed
  # deterministisch direkt ueber _A_postRoute -> _IDF_orchestrate (1-Seam, kein
  # BDF-Polling-Roundtrip; INV-A-EXCEPT-1). BDF Phase 1.0 ist nur noch fuer die
  # A-internen Ausnahme-Routen (refine -> A_RETRY, defer -> DEFER) zustaendig.
  IF route == "A_RETRY":
    Logge: "[BDF-2] A-Output unzureichend -> nochmal A"
    Skill(skill="_A_orchestrate", args="{bl_name_arg} fresh")
    RETURN  # A ruft BDF-2 wieder, max 2x (BL-131 Anti-Zirkel)
  ELIF route == "DEFER":
    Logge: "[BDF-2] DEFER -> naechstes BL"
    # Defer-Marker im BDF_PIPELINE_STATE setzen, Outer-Loop pickt naechstes Item
    Schreibe {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.deferred_items.append(bl_name_arg)
    RETURN
  ELIF route == "IDF" OR route == "IDF+SDF" OR route == "SDF":
    # DEPRECATED (BL-226 AK-3): A chaint direkt via _A_postRoute -> _IDF_orchestrate.
    # Dieser Pfad ist nach BL-226 toter Code und wird nach AK-1-Fix nie mehr getriggert.
    ABORT("[BDF-2] route='{route}' ist veraltet (BL-226): A-Pipeline chaint direkt zu IDF "
          + "via _A_postRoute. Nutze die proceed-Direkt-Chain, KEINEN BDF-IDF-Roundtrip.")
  ELSE:
    Logge FEHLER: "[BDF-2] Unbekannte route '{route}' — kein Handoff"
    RETURN
# ═══ ENDE BDF-2 Post-A-Decision ═══

# Ceiling-Capping (AK-BDF-CEIL): Session-Params sind Obergrenze, BDF darf NIE hoeher
# Semantik: "ceiling" = Maximum. BDF-Default ist angestrebter Wert, nicht Override.
Lies _session_params.md → session_ceiling, session_floor
hierarchy = {opus: 3, sonnet: 2, haiku: 1}

ceiling        = min(bdf_default_ceiling, session_ceiling, key=hierarchy)
floor          = max(bdf_default_floor, session_floor, key=hierarchy)
max_difficulty = bdf_default_difficulty

IF bdf_default_ceiling != ceiling:
  Logge: "Ceiling-Capping: BDF-Default '{bdf_default_ceiling}' gekappt auf '{ceiling}' (Session-Param)"

# Session-Parameter setzen (dark_factory=true → hil=off + GLOBAL_MODUS=big_dark_factory)
# WICHTIG: ceiling/floor werden NICHT an /_param weitergegeben — Session-Params bleiben unangetastet
Fuehre aus: /_param dark_factory=true difficulty={max_difficulty}

# BDF_PIPELINE_STATE initialisieren
Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
  bdf_status: SCANNING
  current_item: null
  items_done: []
  items_failed: []
  bdf_start: {Datum}
  bdf_ceiling: {ceiling}
  bdf_floor: {floor}
  bdf_max_items: {bdf_max_items}
  BDF_ITEM_DONE: null
  BDF_NEXT_TRIGGER: false
  testRun_done:   false   # Guard: testRun noch nicht gelaufen
  testRun_result: null    # SDF-Rueckkanal {pass, fail, new_pl_items}
  active_mode:    null    # Resume-Disambiguierung (normal | testRun)
  feature_branch: null    # Feature-Branch Name (v2.7.0 PR-Workflow)
  # BL-075 T3: Drift-Reset State (RF-BDF-033, AK-08, ADR-1)
  last_testrun_bl_snapshot: null   # Hash ueber BL-Items (Status+Reifegrad)
  testRun_rearm_count: 0           # Session-skoped Rearm-Counter (max 3)
  # BL-075 T2+T4: Anti-Zirkel Zaehler
  bdf_bl_handoff_depth: 0
  reifung_cycles: 0
  bdf_scan_iterations: 0
  # BDF Aggregationsfelder (AK-01-02, BL-029 v1)
  active_sdfs: []       # v1: max 1 Eintrag
  sdfs_done: []
  sdfs_total: 0

# ═══ FACTORY_STATES Schema (RF-01, BL-029 v1) ═══
# Multi-tenant-ready: Jede SDF-Instanz hat eigenen State-Slot
# v1: maximal 1 aktive Instanz (sequentiell). Schema erlaubt N.
# Backward-Kompatibilitaet: DF_PIPELINE_STATE bleibt als SDF_DEFAULT Alias
Schreibe in {WORKING_DIR}/_manifest.md → FACTORY_STATES:
  SDF_DEFAULT:
    instance_id: SDF_DEFAULT
    status: IDLE
    current_item: null
    worktree: null      # v2: Worktree-Pfad
    started: null
    updated: null

# ═══ FEATURE-BRANCH ERSTELLEN (v2.7.0, PR-Workflow) ═══
# BDF arbeitet in Feature-Branch. PR gegen main wird in SDF postPhase gestellt.
# REGEL: Kein direkter Push auf main. Immer ueber PR.
bdf_date = {Datum im Format YYYY-MM-DD}
feature_branch = "feature/bdf-{bdf_date}"
Fuehre aus: git checkout -b {feature_branch}
# Falls Branch bereits existiert (Resume): git checkout {feature_branch}
IF branch_exists(feature_branch):
  Fuehre aus: git checkout {feature_branch}
  Logge: "[PR-WORKFLOW] Resume: Feature-Branch '{feature_branch}' existiert bereits — wiederverwendet"
ELSE:
  Fuehre aus: git checkout -b {feature_branch}
  Logge: "[PR-WORKFLOW] Feature-Branch erstellt: {feature_branch}"
Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.feature_branch: {feature_branch}

# BDF_BATCH_STATE initialisieren (RF-BDF-020)
Schreibe in {WORKING_DIR}/_manifest.md → BDF_BATCH_STATE:
  batch_items: []
  batch_plan_file: null
  batch_status: null  # null | PLANNING | READY | RUNNING | DONE

# Lebenszyklus-Erkennung + WAHRHEITEN-ROUTING → jetzt in /_BL_orchestrate v1.0 (BL-023)

Logge: "=== BIG DARK FACTORY GESTARTET ==="
Logge: "Max Difficulty: {max_difficulty}, Ceiling: {ceiling}, Floor: {floor}"
Logge: "Sicherheits-Stop nach {bdf_max_items} Items"
```

### Phase 2: SCANNING — Parking-Lot Scanner (RF-BDF-002)

### Phase 2 SCANNING — Active-Index Only (BL-178, NEU 2026-05-19)

Liest NUR aktive Indizes (Token-Saving 85-90%):
- `{vault_root}/_backlog_index.md` (active only — DRAFT/READY/PLANNED/IN_PROGRESS/RUNNING/SC-REIF/FREEZE/HOLD/DEFERRED/PARTIAL_DONE/PHANTOM)
- `{vault_root}/_parking-lot.md` (open `[ ]` + freeze `[~]` + question `[?]`)

Archive-Indizes NICHT lesen:
- `_backlog_index_done.md` und `_parking-lot_done.md` nur auf explizite Anfrage (z.B. `/_backlog show-archive`)

Per INV-INDEX-SPLIT-5 (BL-178).

```
# ═══ BL-075 T4: Scan-Iterations Counter + Hard-Break (RF-BDF-034, AK-09) ═══
bdf_scan_iterations = BDF_PIPELINE_STATE.bdf_scan_iterations ?? 0
bdf_max_scan_iterations = $ARGUMENTS.bdf_max_scan_iterations ?? 20
bdf_scan_iterations += 1
Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_scan_iterations: {bdf_scan_iterations}
IF bdf_scan_iterations >= bdf_max_scan_iterations:
  Logge: "[BL-075] HARD-BREAK: bdf_scan_iterations >= {bdf_max_scan_iterations} → ABORTED (INV-5 Anti-Zirkel)"
  bdf_status = ABORTED
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: ABORTED
  → Springe zu Phase 6 (Terminal)

# ═══ ENDLOSSCHLEIFE-SEMANTIK (BL-032, RF-06 AK-06-01) ═══
# BDF SCANNING ist eine beabsichtigte Endlosschleife (nicht Bug, Feature):
#   SCANNING → BATCH_PLANNING → ITEM_RUNNING → ITEM_DONE → SCANNING
# Terminationsbedingungen:
#   1. unified.length == 0 (ALLE Items DONE/Terminal) → EMPTY → SDF(postPhase) → DONE
#   2. items_done.length >= bdf_max_items (Sicherheits-Stop) → EMPTY
#   3. User-ABORT (manuell, nur bei HiL) → ABORTED
# Entry-Points in diese Schleife:
#   a) Frischer Start (Phase 1 → Phase 2)
#   b) Resume nach Context-Verlust (Resume-Detection → Phase 2)
#   c) A_PIPELINE_RETURN (completion_signal empfangen → Phase 2)

# Lese {WORKING_DIR}/_parking-lot.md (IMMER frisch lesen — nie gecacht, AK-BDF-020e)
items = Lies {VAULT}/_parking-lot.md
open_items = Filtere alle [ ] Items (offen, nicht [x], [~], [?] oder [!])
# [~]-Items = FREEZE (PN-7 Z1): bereits durch obigen Filter ausgeschlossen
# [?]-Items = QUESTION (J3): Terminal — HiL-Entscheidung ausstehend, auto-skip
# [!]-Items = STUCKED (J3): Terminal — max_cycles erschoepft, auto-skip
# NIEMALS Terminal-Items ([~], [?], [!]) in valid_items aufnehmen (pl-state-machine.md)

# PRE-CHECK: Items ohne Prioritaets-Feld ueberspringen
valid_items = []
FOR item IN open_items:
  IF item hat KEIN Prioritaets-Feld (KRITISCH|HOCH|MITTEL|NIEDRIG):
    Logge: "WARNING: Item '{item.name}' hat keine Prioritaet — uebersprungen"
    CONTINUE
  IF item.name IN [f.name FOR f IN items_failed]:
    # STUCKED-Promotion (J3): Item > 2 Mal gescheitert → [!] setzen
    item_entry = items_failed[item.name]
    IF item_entry.retry_count >= 2:
      Logge: "STUCKED: Item '{item.name}' nach {item_entry.retry_count} Versuchen → [!] gesetzt"
      # items_stucked Backward-Kanal (T7, RF-03 AK-03-02)
      # Reihenfolge ZWINGEND: Manifest ZUERST, DANN {WORKING_DIR}/_parking-lot.md [!]
      # INV-VAULT-9: resolve_bl_path(ACTIVE_BL_ID) → {WORKING_DIR} MUSS vor diesem Block aufgeloest sein
      Schreibe in {WORKING_DIR}/_manifest.md → BL_LIFECYCLE_STATE.items_stucked APPEND:
        {name: item.name, date: {Datum}, reason: "Max-Zyklen ({item_entry.retry_count} Versuche)"}
      # P1-INVARIANTE: Manifest-Write abgeschlossen. Naechster Schritt: PL-Write (Zeile 415).
      In {WORKING_DIR}/_parking-lot.md:
      # P1-INVARIANTE: Manifest-Write (oben) MUSS vor diesem PL-Write abgeschlossen sein.
      # {WORKING_DIR} ist identisch mit Manifest-Write oben (gleicher resolve_bl_path Aufruf). # INV-VAULT-9 migration
        Ersetze "[ ] {item.name}" mit "[!] **[STUCKED] {item.name}** {Grund: Max-Zyklen ({item_entry.retry_count} Versuche). Letzte Fehler: {item_entry.reason}}"
    CONTINUE  # Im selben Lauf nicht erneut selektieren
  # IDEMPOTENZ-Guard (PN-7 Z1): IN_ARBEIT-Items aus abgebrochenem Lauf behandeln
  IF "[STATUS: IN_ARBEIT]" IN item.text AND item.name IN [d.name FOR d IN items_done]:
    CONTINUE  # IN_ARBEIT + bereits done — inkonsistenter Zustand, skip
  IF "[STATUS: IN_ARBEIT]" IN item.text AND item.name IN [f.name FOR f IN items_failed]:
    CONTINUE  # IN_ARBEIT + gescheitert — nicht erneut aufnehmen
  valid_items.append(item)

# Sortierung: Prioritaet → Datum (aeltestes zuerst)
# KRITISCH > HOCH > MITTEL > NIEDRIG
valid_items = sortiere(valid_items, key=[prioritaet DESC, datum ASC])

# ═══ KANAL 2: Backlog-Index (BDF v3.0 Dual-Kanal, RF-BDF-026) ═══
# Lese _backlog_index.md (graceful if missing — PL-only Fallback, W21, AK-11)
# v3.0 (BL-023): NUR status=READY lesen. DRAFT->READY Transition jetzt in /_BL_orchestrate.
bl_items = []
IF exists("{VAULT}/_backlog_index.md"):
  bl_raw = Lies {VAULT}/_backlog_index.md
  bl_candidates = Filtere Items mit status == "READY"

  FOR bl_item IN bl_candidates:
    # Reifegrad aus Vault-Knoten Frontmatter lesen (read-only, INV-4: BDF berechnet NICHT selbst)
    vault_path = bl_item.vault_path  # z.B. {VAULT}/Backlog/BL-{NNN}-{slug}.md
    IF NOT exists(vault_path):
      Logge: "[BDF] WARN: BL-{bl_item.id} Vault-Knoten nicht lesbar — uebersprungen"
      CONTINUE
    bl_frontmatter = Lies vault_path → Frontmatter (YAML)
    bl_item.reifegrad = bl_frontmatter.reifegrad ?? "UNREIF"

    bl_item.source = "backlog"
    bl_items.append(bl_item)

  Logge: "SCANNING Kanal 2 (Backlog): {bl_items.length} BL-Items gelesen (READY)"
ELSE:
  Logge: "SCANNING Kanal 2 (Backlog): _backlog_index.md nicht vorhanden — PL-only Fallback"

# ═══ REIFUNGS-GATE (RF-05, AK-05-01, BL-029) ═══
# UNREIF-Items werden NICHT in Batch aufgenommen — zurueck an BL_orchestrate
# UNREIF → A-Pipeline/Paper/WP noetig → BL_orchestrate steuert Reifung
unreif_items = []
FOR bl_item IN bl_items[:]:  # Copy fuer sichere Iteration
  IF bl_item.reifegrad == "UNREIF":
    unreif_items.append(bl_item)
    bl_items.remove(bl_item)
    Logge: "[REIFUNGS-GATE] BL-{bl_item.id}: reifegrad=UNREIF → nicht an SDF, zurueck an BL_orchestrate"

IF unreif_items.length > 0:
  # Backward-Kanal: needs_reifung Signal in Manifest
  # BL-210 M5 Fix 2026-05-24: APPEND mit Dedup statt REPLACE
  # Vorher: REPLACE → ueberlappende UNREIF-Markers gingen verloren bei multi-SCANNING-Iterations
  existing_needs_reifung = Read({WORKING_DIR}/_manifest.md → BL_LIFECYCLE_STATE.needs_reifung) ?? []
  new_ids = [bl_item.id for bl_item in unreif_items]
  merged = list(set(existing_needs_reifung + new_ids))  # Dedup via set
  Schreibe in {WORKING_DIR}/_manifest.md → BL_LIFECYCLE_STATE.needs_reifung: merged
  Logge: "[REIFUNGS-GATE] {unreif_items.length} UNREIF-Items zurueckgewiesen (APPEND, {len(merged)} total nach Dedup)"

# ═══ ENTKERNT (BL-430, AK-2): Autonome Prio-/Reifegrad-Sortierung DEPRECATED ═══
# RF-BDF-027 unified-Merge + BL-081 Auto-Defer autonome Reorder-Logik ist no-op.
# Kein Auto-Reorder mehr — Reihenfolge = ROADMAP-ORDER (AK-4-Integration).
# Code-Block bleibt als Referenz (Backward-Compat). NICHT ausfuehren.
#
# [ENTKERNT (BL-430)] MERGE-ALGORITHMUS: Reifegrad-Banding mit PL-Interleaving (RF-BDF-027, AK-03)
# Sortierung (OQ-1 ENTSCHIEDEN): BL-REIF > PL-KRITISCH > BL-SC-REIF > PL-HOCH > BL-UNREIF > PL-MITTEL > PL-NIEDRIG
# [ENTKERNT (BL-430)] bl_reif    = [item for item in bl_items if item.reifegrad == "REIF"]
# [ENTKERNT (BL-430)] bl_sc_reif = [item for item in bl_items if item.reifegrad == "SC-REIF"]
# [ENTKERNT (BL-430)] bl_unreif  = [item for item in bl_items if item.reifegrad == "UNREIF"]
# [ENTKERNT (BL-430)] pl_kritisch = [item for item in valid_items if item.prioritaet == "KRITISCH"]
# [ENTKERNT (BL-430)] pl_hoch     = [item for item in valid_items if item.prioritaet == "HOCH"]
# [ENTKERNT (BL-430)] pl_mittel   = [item for item in valid_items if item.prioritaet == "MITTEL"]
# [ENTKERNT (BL-430)] pl_niedrig  = [item for item in valid_items if item.prioritaet == "NIEDRIG"]
# [ENTKERNT (BL-430)] unified = bl_reif + pl_kritisch + bl_sc_reif + pl_hoch + bl_unreif + pl_mittel + pl_niedrig
#
# STATTDESSEN (AK-4-Integration): ROADMAP-ORDER via roadmap_status.parse_roadmap_order(.claude/ROADMAP.md)
# Engine = EXECUTOR der kuratierten Order; /_roadmap_backlog bleibt der read-only KOMPASS (Brain).
unified = roadmap_status.parse_roadmap_order(".claude/ROADMAP.md", candidates=valid_items + bl_items)
# parse_roadmap_order gibt Items in ROADMAP-Reihenfolge zurueck (Reader-Reuse, batch_1 bestaetigt).
# ═══ ENDE ENTKERNT (BL-430, AK-2) ═══

Logge: "ROADMAP-ORDER: {unified.length} Items (ROADMAP-kuratiert, PL: {len(valid_items)}, BL: {len(bl_items)})"

# A-PIPELINE AUTO-TRIGGER → jetzt in /_BL_orchestrate v1.0 (BL-023)

# ═══ BL-081: DEPENDENCY-CHECK (BL-zu-BL) — reaktiviert nach BDF-Smoke-Test 2026-04-11 ═══
# Zweck: Items mit unmet BL-zu-BL Dependencies werden im unified Pool ans Ende sortiert
#        (deferred, nicht entfernt). Fix des Architektur-Gaps von BL-023 (entfernt) +
#        BL-078b (Phase 5 gestrichen) + BL-076 (IDF Phase 4 nur innerhalb-BL).
# Reason: BDF v3.0 Argument "reiner Dispatcher" war zu strikt — read-only Filtering
#         ist kein State-Transition und bleibt legitim in BDF SCANNING.
# AK-01..09 siehe BL-081-bl-dependency-check-reaktivierung.md
dep_ready     = []
dep_deferred  = []
cycle_stucked = []
FOR item IN unified:
  IF item.source != "backlog":
    # AK-02: PL-Items haben kein strukturiertes dependencies-Feld → unberuehrt
    dep_ready.append(item)
    CONTINUE
  # AK-02: BL-Item → Vault-Frontmatter lesen
  bl_fm = Lies item.vault_path → Frontmatter (YAML)
  deps  = bl_fm.dependencies ?? []
  IF deps.length == 0:
    dep_ready.append(item)
    CONTINUE
  # AK-06: Dependency gilt als erfuellt wenn target status ∈ {DONE, DECOMPOSED, ARCHIVIERT}
  all_met  = true
  blocker  = null
  cycle_detected = false
  FOR dep_id IN deps:
    # dep_id kann Suffix haben (z.B. "BL-050_DONE") → normalisieren
    dep_clean = extract_bl_id(dep_id)  # "BL-050_DONE" → "BL-050"
    IF dep_clean == null:
      CONTINUE  # Nicht-BL Referenz → ignorieren
    dep_row = Lies {VAULT}/_backlog_index.md → Zeile fuer dep_clean
    IF dep_row == null:
      Logge: "[DEPENDENCY] {item.id} depends {dep_clean} — target nicht im Index → ignoriert"
      CONTINUE
    dep_status = dep_row.status
    # AK-08: Zyklus-Erkennung (2-Knoten-Zyklus: A→B, B→A)
    IF dep_clean != item.id:
      dep_target_deps = Lies dep_row.vault_path → Frontmatter.dependencies ?? []
      IF item.id IN [extract_bl_id(d) FOR d IN dep_target_deps]:
        Logge: "[DEPENDENCY] ZYKLUS: {item.id} ↔ {dep_clean} — beide als STUCKED markiert"
        cycle_detected = true
        cycle_stucked.append(item.id)
        cycle_stucked.append(dep_clean)
        BREAK
    IF dep_status NOT IN ["DONE", "DECOMPOSED", "ARCHIVIERT"]:
      all_met = false
      blocker = dep_clean + " (status=" + dep_status + ")"
      BREAK
  # AK-08: Zyklus → STUCKED-Markierung + kein defer, skip
  IF cycle_detected:
    FOR stuck_id IN cycle_stucked:
      Schreibe in {WORKING_DIR}/_manifest.md → BL_LIFECYCLE_STATE.items_stucked APPEND:
        {name: stuck_id, date: {Datum}, reason: "Dependency-Zyklus erkannt"}
    CONTINUE
  # AK-03/04: deferred statt entfernt, Log-Pattern
  IF NOT all_met:
    Logge: "[DEPENDENCY] {item.id} blocked by {blocker} → deferred"
    dep_deferred.append(item)
  ELSE:
    dep_ready.append(item)

# AK-03: Reihenfolge — ready zuerst, deferred ans Ende
unified = dep_ready + dep_deferred
Logge: "[DEPENDENCY] ready={dep_ready.length}, deferred={dep_deferred.length}, stucked={cycle_stucked.length}"

# AK-05: Wenn ALLE Items deferred — behandle Pool als EMPTY
#        (EMPTY-Handler triggert BL-075 T2 Reifungs-Delegation)
IF dep_ready.length == 0 AND dep_deferred.length > 0:
  Logge: "[DEPENDENCY] ALLE Items deferred — treat as EMPTY (Reifungs-Delegation via BL-075 T2)"
  unified = []  # Triggert EMPTY-Handler unten
# ═══ ENDE BL-081 DEPENDENCY-CHECK ═══

# ═══ BL-075 T1: Zaehl-Scan fuer EMPTY-Guard (RF-BDF-030) ═══
# Separater Scan von _backlog_index.md — zaehlt alle OFFEN-Stati
# INV-01 (W3, INV-4): Nur lesen, NICHT reifegrad berechnen oder schreiben
# Ziel: Unterscheidung "echtes EMPTY" (all_bl=0) vs. "nur keine READY" (all_bl>0)
all_open_bl_count = 0
draft_count = 0
unreif_count = 0
IF exists("{VAULT}/_backlog_index.md"):
  bl_all_raw = Lies {VAULT}/_backlog_index.md
  FOR bl_row IN bl_all_raw:
    IF bl_row.status IN ["DRAFT", "READY", "IN_PROGRESS", "SC-REIF", "PLANNED"]:
      all_open_bl_count += 1
      IF bl_row.status == "DRAFT":
        draft_count += 1
      # Reifegrad aus Vault-Frontmatter lesen (read-only, INV-01)
      IF exists(bl_row.vault_path):
        bl_fm = Lies bl_row.vault_path → Frontmatter
        IF bl_fm.reifegrad == "UNREIF":
          unreif_count += 1
open_pl_count = valid_items.length  # bereits oben berechnet (Kanal 1)
Logge: "[BL-075] EMPTY-Scan: unified={unified.length} all_bl={all_open_bl_count} draft={draft_count} unreif={unreif_count} pl={open_pl_count}"

# BL-075 T1: EMPTY-Guard verschaerft (RF-BDF-031, AK-02)
# Terminierungs-Pfad NUR wenn wirklich alles leer. Sonst Reifungs-Delegation (T2 eingefuegt).

# ═══ ENTKERNT (BL-430, AK-3): BL-075 T2 autonome Reifungs-Such-Schleife DEPRECATED ═══
# Die autonome Suche nach reifbaren Items via _BL_orchestrate-Delegation ist no-op.
# Keine autonome Suche mehr — Reihenfolge kommt aus ROADMAP-ORDER (AK-4-Integration).
# Code-Block bleibt als Referenz (Backward-Compat). NICHT ausfuehren.
#
# [ENTKERNT (BL-430, AK-3)] BL-075 T2: Reifungs-Delegation an _BL_orchestrate (RF-BDF-032, AK-03/06/07)
# Dead-Lock-Fix: Wenn unified leer aber BL-Items noch OFFEN → BL_orchestrate reifen lassen
# INV-5 (Spec §4): bdf_bl_handoff_depth max 2 → HARD-BREAK ABORTED (Anti-Zirkel)
# ADR-3: --mode=recheck --from=bdf_empty damit BL_orchestrate Phase 9 AUTO-CHAIN skippt
# Default false; bei Reifungs-Budget-Erschoepfung true → Fallthrough in echten EMPTY-Body
force_true_empty = false

# [ENTKERNT (BL-430, AK-3)] Die folgende Reifungs-Delegation laeuft NICHT mehr:
# IF unified.length == 0 AND all_open_bl_count > 0 AND open_pl_count == 0:
#   ... autonome Delegation an _BL_orchestrate --mode=recheck ...
# STATTDESSEN: unified.length == 0 → direkt EMPTY-Handler (force_true_empty=false, echter Leerstand)
# Die ROADMAP-ORDER-basierte Selektion entscheidet bereits welche Items kandidieren.
# ═══ ENDE ENTKERNT (BL-430, AK-3) ═══

# [ERHALTEN] Hard-Break Anti-Zirkel (INV-5) — bleibt als Safety-Netz
IF unified.length == 0 AND all_open_bl_count > 0 AND open_pl_count == 0:
  bdf_bl_handoff_depth   = BDF_PIPELINE_STATE.bdf_bl_handoff_depth ?? 0
  reifung_cycles         = BDF_PIPELINE_STATE.reifung_cycles ?? 0
  bdf_max_reifung_cycles = $ARGUMENTS.bdf_max_reifung_cycles ?? 3

  # --- Hard-Break Anti-Zirkel (INV-5, erhalten) ---
  IF bdf_bl_handoff_depth >= 2:
    Logge: "[BL-075] HARD-BREAK: BDF↔BL Handoff-Depth >= 2 → ABORTED (Anti-Zirkel INV-5)"
    bdf_status = ABORTED
    Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: ABORTED
    → Springe zu Phase 6 (Terminal)

  # --- Reifungs-Budget erschoepft → Fallthrough in echten EMPTY-Body ---
  IF reifung_cycles >= bdf_max_reifung_cycles:
    Logge: "[BL-075] REIFUNG_CYCLES erschoepft ({reifung_cycles}/{bdf_max_reifung_cycles}) → Fallthrough EMPTY"
    Logge: "[BL-075] Fallthrough: behandle als echtes EMPTY trotz {all_open_bl_count} offener BL-Items"
    force_true_empty = true
    # Faellt durch in den naechsten IF-Block (echter EMPTY-Handler)

  ELSE:
    # [ENTKERNT (BL-430, AK-3)] Delegation an _BL_orchestrate — no-op, direkt Fallthrough
    Logge: "[BL-430] ENTKERNT: autonome Reifungs-Delegation an _BL_orchestrate no-op — EMPTY-Handler"
    # [ENTKERNT (BL-430)] NAME = $ARGUMENTS.name ?? "default"
    # [ENTKERNT (BL-430)] Skill(skill="_BL_orchestrate", args="{NAME} --mode=recheck --from=bdf_empty")
    # INV-5 Dekrement-Garantie (TRY/FINALLY-Pattern): IMMER dekrementieren, auch bei Fehler
    bdf_bl_handoff_depth -= 1
    Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_bl_handoff_depth: {bdf_bl_handoff_depth}

    # --- Ergebnis auswerten ---
    Lies {WORKING_DIR}/_manifest.md → BL_LIFECYCLE_STATE.items_routed_ready
    bl_recheck_ready = BL_LIFECYCLE_STATE.items_routed_ready ?? 0
    Logge: "[BL-075] BL-Recheck: items_routed_ready={bl_recheck_ready} reifung_cycles={reifung_cycles} [ENTKERNT: immer 0]"

    IF bl_recheck_ready > 0:
      Logge: "[BL-075] {bl_recheck_ready} Items gereift → SCANNING neu [ENTKERNT: Pfad nicht mehr erreichbar]"
      reifung_cycles = 0  # erfolgreicher Durchlauf resettet Zaehler
      Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.reifung_cycles: 0
      bdf_status = SCANNING
      Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: SCANNING
      → Springe zu Phase 2 (SCANNING)
    ELSE:
      reifung_cycles += 1
      Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.reifung_cycles: {reifung_cycles}
      Logge: "[BL-075] 0 Items gereift → reifung_cycles++ = {reifung_cycles}"
      # Naechster Durchlauf entscheidet Fallthrough oder erneute Delegation
      bdf_status = SCANNING
      Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: SCANNING
      → Springe zu Phase 2 (SCANNING)

# Echter EMPTY-Body — getriggert durch (a) all_bl=0 AND pl=0 ODER (b) force_true_empty=true (Fallthrough)
IF (unified.length == 0 AND all_open_bl_count == 0 AND open_pl_count == 0) OR force_true_empty:
  Logge: "[BL-075] EMPTY: Echtes EMPTY (all_bl={all_open_bl_count}, pl={open_pl_count}, forced={force_true_empty}) → Terminierung"
  # ═══ PARKPLATZ UND BACKLOG LEER ODER NUR TERMINAL-ITEMS ═══
  # Terminal-Items: DONE [x], FREEZE [~], QUESTION [?], STUCKED [!], BLOCKED (items_blocked)
  # ALLE_TERMINAL-Check (J3): Wenn keine OFFEN-Items mehr → Post-Phase SOFORT
  # PFLICHT: Wenn kein offenes Item mehr → Post-Phase SOFORT ausfuehren!
  # ANTI-PATTERN: Hier NICHT stoppen/beenden! Post-Phase ist PFLICHT!
  bdf_status = EMPTY
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: EMPTY
  # Zaehle Terminal-Items fuer Notification
  terminal_question = Zaehle [?]-Items in {WORKING_DIR}/_parking-lot.md
  terminal_stucked  = Zaehle [!]-Items in {WORKING_DIR}/_parking-lot.md
  terminal_blocked  = items_blocked.length
  IF terminal_question > 0 OR terminal_stucked > 0 OR terminal_blocked > 0:
    Logge: "=== ALLE_TERMINAL: QUESTION={terminal_question}, STUCKED={terminal_stucked}, BLOCKED={terminal_blocked} ==="
    Logge: "=== Keine weiteren OFFEN-Items — SDF postPhase WIRD DELEGIERT ==="
  ELSE:
    Logge: "=== PARKPLATZ LEER — SDF postPhase WIRD DELEGIERT ==="

  # --- SDF postPhase DELEGATION (BL-041, v3.2.0) ---

  # Double-Check: Wirklich alle [x]? (AK-BDF-021a)
  Lies {WORKING_DIR}/_parking-lot.md erneut
  open_check = Filtere alle [ ] Items
  IF open_check.length > 0:
    Logge: "WARNUNG: {open_check.length} Items noch offen nach Double-Check — zurueck zu SCANNING"
    bdf_status = SCANNING
    Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: SCANNING
    # Loop-Back: erneut scannen (Items koennen waehrend SDF hinzugekommen sein)
  ELSE:
    # ═══ BL-075 T3: testRun_done Drift-Reset (RF-BDF-033, AK-08, ADR-1) ═══
    # Backlog-Snapshot-Hash ueber Status+Reifegrad aller BL-Items berechnen.
    # Bei Mismatch → testRun_done zurueckgesetzt (begrenzt durch testRun_rearm_count).
    # Hard-Break bei >=3 Rearms pro Session verhindert testRun-Endlosschleifen.
    bdf_max_rearm_count = 3  # Spec-Default
    current_bl_snapshot = berechne_hash(
      Fuer jedes BL-Item in _backlog_index.md:
        (bl.id + ":" + bl.status + ":" + read_reifegrad(bl.vault_path))
    )
    last_snapshot = BDF_PIPELINE_STATE.last_testrun_bl_snapshot ?? null
    rearm_count   = BDF_PIPELINE_STATE.testRun_rearm_count ?? 0

    IF last_snapshot != null AND last_snapshot != current_bl_snapshot:
      IF rearm_count >= bdf_max_rearm_count:
        Logge: "[BL-075] HARD-BREAK: testRun_rearm_count >= {bdf_max_rearm_count} → ABORTED"
        bdf_status = ABORTED
        Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: ABORTED
        → Springe zu Phase 6 (Terminal)
      Logge: "[BL-075] testRun_done reset (Snapshot-Drift, rearm {rearm_count+1}/{bdf_max_rearm_count})"
      rearm_count += 1
      Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
        testRun_done: false
        testRun_rearm_count: {rearm_count}

    # ═══ testRun-GUARD (RF-BDF-023) ═══
    testRun_done = BDF_PIPELINE_STATE.testRun_done ?? false

    IF testRun_done == false:
      Logge: "=== TEST_RUNNING: testRun_done=false — SDF-testRun starten ==="
      bdf_status = TEST_RUNNING
      active_mode = "testRun"
      Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
        bdf_status: TEST_RUNNING
        active_mode: testRun
        BDF_NEXT_TRIGGER: false
        testRun_result: null

      # HANDSCHUH-WECHSEL: BDF → SDF (testRun-Modus)
      # ANTI-PATTERN (RF-BDF-022): Kein Agent() direkt, kein Skill(I_orchestrate)
      # RICHTIG: Skill(SDF) mit --mode=testRun — SDF entscheidet intern (Phase-0.5-Fork)
      Skill(skill="_SDF_orchestrate", args="{NAME} {max_difficulty} {ceiling} {floor} --mode=testRun")

      # Nach SDF-Completion: testRun_result auswerten
      testRun_result = lies({WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.testRun_result)
                     ?? {pass: 0, fail: 0, new_pl_items: []}

      # ABORT-Behandlung: Wenn SDF-testRun ABORTED (kein BDF_NEXT_TRIGGER) → AskUserQuestion
      IF BDF_PIPELINE_STATE.BDF_NEXT_TRIGGER == false:
        AskUserQuestion: "testRun unterbrochen. Weiter? [skip=DONE direkt | retry=testRun neu | stop=BDF ABORTED]"
        # IF User == "skip" → testRun_done=true, SDF postPhase delegieren → Phase 6 (Terminal)
        # IF User == "retry" → bdf_status=EMPTY, testRun_done=false → Springe zu Phase 2 (SCANNING)
        # IF User == "stop" → bdf_status=ABORTED → Springe zu Phase 6 (Terminal)

      ELIF testRun_result.fail > 0:
        Logge: "TEST_RUNNING FAIL: {testRun_result.fail} Failures, {testRun_result.new_pl_items.length} neue PL-Items → SCANNING"
        bdf_status = SCANNING
        active_mode = "normal"
        Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
          bdf_status: SCANNING
          active_mode: normal
          testRun_done: true    # einmal gelaufen — auch bei FAIL nicht erneut triggern
          last_testrun_bl_snapshot: {current_bl_snapshot}  # BL-075 T3: Snapshot einfrieren
        → Springe zu Phase 2 (SCANNING)

      ELSE:
        Logge: "TEST_RUNNING GREEN: {testRun_result.pass} Tests bestanden → PostBatch delegieren"
        Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
          active_mode: null
          testRun_done: true
          last_testrun_bl_snapshot: {current_bl_snapshot}  # BL-075 T3: Snapshot einfrieren
          bdf_all_items_done: true
        # HANDSCHUH-WECHSEL: BDF -> PostBatch (BL-133 Slice-5, AK-4)
        Skill(skill="_PostBatch_orchestrate", args="{NAME}")
        # PostBatch setzt BDF_NEXT_TRIGGER=true nach Abschluss (Tests + Commit)
        → Springe zu Phase 6 (Terminal / Protokoll-Rollover)

    ELSE:
      # testRun_done=true: bereits gelaufen -> PostBatch delegieren
      Logge: "=== PARKPLATZ LEER — testRun DONE — PostBatch WIRD DELEGIERT ==="
      Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_all_items_done: true
      # HANDSCHUH-WECHSEL: BDF -> PostBatch (BL-133 Slice-5, AK-4)
      # BL-210 M12 Fix 2026-05-24: explizite --stages-Args-Propagation (war implizit via session_params)
      tdd_stages_arg = Read({VAULT}/_session_params.md).tdd_stages ?? "1,3,5"
      Skill(skill="_PostBatch_orchestrate", args="{NAME} --stages={tdd_stages_arg}")
      # PostBatch setzt BDF_NEXT_TRIGGER=true nach Abschluss (Tests + Commit)

      # BL-213 Fix 2026-05-24: Auto-Chain BDF EMPTY-Handler → Pre_PR (Geist G#10).
      # Vorher BROKEN: PostBatch endete, Pre_PR musste manuell vom User gestartet werden.
      # Option B aus BL-213 Spec: BDF orchestriert Pre_PR nach PostBatch (semantisch korrekt —
      # Pre_PR ist Feature-Ende-Aktion, nicht Batch-Ende-Aktion).
      # Guard: nur wenn PostBatch erfolgreich (POSTBATCH_PIPELINE_STATE.batch_done=true).
      Lies {WORKING_DIR}/_manifest.md → POSTBATCH_PIPELINE_STATE.batch_done
      IF POSTBATCH_PIPELINE_STATE.batch_done == true:
        Logge: "=== POSTBATCH DONE — Pre_PR_orchestrate WIRD AUTO-CHAINED (BL-213) ==="
        Skill(skill="_Pre_PR_orchestrate")
      ELSE:
        Logge: "[BL-213] PostBatch nicht abgeschlossen — Pre_PR Auto-Chain SKIP"
      → Springe zu Phase 6 (Terminal / Protokoll-Rollover)
  # --- ENDE EMPTY-HANDLER ---

Logge: "SCANNING: {unified.length} Items im unified Pool (PL: {valid_items.length}, BL: {bl_items.length})"
→ Springe zu Phase 2.5 (INTEREST_RADIUS)
```

### Phase 2.5: INTEREST_RADIUS — BL-Dependency-Matrix (NEU 2026-05-19, BL-176)

> **ENTKERNT (BL-430, AK-1):** Die autonome INTEREST_RADIUS-Auswahl-Maschine ist DEPRECATED/no-op.
> Die 4 BL-Dependency-Berater (`_BDF_berater_blDependencyAnalyzer`, `_BDF_berater_blClustering`,
> `_BDF_berater_blSequencePlanner`, `_BDF_berater_blParallelBucketPlanner`) werden NICHT mehr aufgerufen.
> Die Item-Reihenfolge kommt jetzt aus der **human-kuratierten ROADMAP-ORDER**:
> `roadmap_status.parse_roadmap_order(.claude/ROADMAP.md)` — der Mensch sortiert, die Engine executes.
> Code-Block bleibt als Referenz (Backward-Compat). **KEIN Aufruf dieser Berater mehr.**

```
# ═══ ENTKERNT (BL-430, AK-1) — DEPRECATED/no-op ═══
# Die INTEREST_RADIUS-Maschine ist außer Betrieb. Stattdessen: ROADMAP-ORDER (AK-4-Integration).
# Folgende Berater-Calls sind NICHT mehr aktiv — nur als Referenz erhalten:
#
# State: INTEREST_RADIUS (zwischen SCANNING und BATCH_PLANNING)
# INV-BDF-DEP-1..3, INV-BDF-PARALLEL-1..2, INV-BDF-MATRIX-FRESHNESS, INV-BDF-MIGRATION-COMPAT aktiv.

# Nach SCANNING + vor BATCH_PLANNING: 4 Berater-Calls sequentiell:
# 1. Dependency-Matrix aufbauen
# [ENTKERNT (BL-430)] Skill(_BDF_berater_blDependencyAnalyzer)
# Baut 2D-Adjacency-Matrix aller offenen BLs aus Frontmatter-deps + LLM-Inferenz
# Output: {vault_root}/Vault/Meta/interest_radius/bl_dependency_matrix.json

# 2. Kohaesions-Clustering
# [ENTKERNT (BL-430)] Skill(_BDF_berater_blClustering)
# Gruppiert BLs nach topic-Tags + type + builds_on-Ketten
# Output: {vault_root}/Vault/Meta/interest_radius/bl_cluster_map.json

# 3. Topologische Sequence planen
# [ENTKERNT (BL-430)] Skill(_BDF_berater_blSequencePlanner)
# Kahn's Algorithm + Priority-Tiebreak (KRITISCH>HOCH>MITTEL>NIEDRIG)
# Output: {vault_root}/Vault/Meta/interest_radius/bl_sequence.json

# 4. Parallel-Bucket-Plan erstellen
# [ENTKERNT (BL-430)] Skill(_BDF_berater_blParallelBucketPlanner)
# Bucket-Splitting nach Dependency-Freiheit + foundation_bl-Handling
# Output: {vault_root}/Vault/Meta/interest_radius/bl_parallel_buckets.json

# [ENTKERNT (BL-430)] Persistieren in _factory_manifest.md
# Schreibe in {vault_root}/Vault/Meta/_factory_manifest.md → BACKLOG_STATE.interest_radius_snapshot:
#   ...

# [ENTKERNT (BL-430)] Logge: "INTEREST_RADIUS: Matrix gebaut, {unified.length} BLs, Sequence + Buckets persistiert"
# → STATTDESSEN: ROADMAP-ORDER via roadmap_status.parse_roadmap_order(.claude/ROADMAP.md) (AK-4-Integration)
→ Springe zu Phase 2b (BATCH_PLANNING)
# ═══ ENDE ENTKERNT (BL-430, AK-1) ═══
```

### Phase 2b: BATCH_PLANNING — Batch-Planung via /_BDF_batchPlan (RF-BDF-020)

```
# State: BATCH_PLANNING
bdf_status = BATCH_PLANNING
Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: BATCH_PLANNING
Schreibe in {WORKING_DIR}/_manifest.md → BDF_BATCH_STATE.batch_status: PLANNING

# MITOSE-GUARD → jetzt in /_BL_orchestrate v1.0 (BL-023)
# TRIAGE-KLASSIFIKATION → jetzt in /_BL_orchestrate v1.0 (BL-023)
# K_QUER PRE-CHECK → jetzt in /_BL_orchestrate v1.0 (BL-023)

# ═══ ANTI-PATTERN ERINNERUNG (RF-BDF-022) ═══
# VERBOTEN: BDF bewertet Komplexitaet/Modi selbst (SRS, COMPLEXITY, Fragilitaet)
# VERBOTEN: BDF spawnt Agent() direkt fuer Code-Aenderungen
# RICHTIG:  BDF delegiert Batch-Planung an /_BDF_batchPlan (Wellen-basierter Command)
# RICHTIG:  BDF delegiert Code-Arbeit an SDF via Skill("_SDF_orchestrate")

# ═══ HANDSCHUH-WECHSEL: BDF → BDF_batchPlan ═══
# BDF_batchPlan liest PL + Model + Spec, plant Batches (2 Flavors: Komplexitaet GROB + Abhaengigkeiten)
# BDF_batchPlan schreibt Batch-Plan-Datei: .claude/analysis/drafts/{NAME}-batchPlan.md
NAME = $ARGUMENTS.name ?? "default"
batch_plan_file = "{WORKING_DIR}/.claude/analysis/drafts/{NAME}-batchPlan.md"

Skill(skill="_BDF_batchPlan", args="{NAME}")

# Nach _BDF_batchPlan: Lies Batch-Plan-Ergebnis
Lies {batch_plan_file} → batch_plan

IF batch_plan NICHT valide ODER batch_plan.items.length == 0:
  Logge: "WARNING: _BDF_batchPlan lieferte leeren/invaliden Plan — erneut scannen"
  bdf_status = SCANNING
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: SCANNING
  → Springe zu Phase 2 (SCANNING)

# Batch-Plan valide: Schreibe BDF_BATCH_STATE ins Manifest (AK-BDF-020d)
Schreibe in {WORKING_DIR}/_manifest.md → BDF_BATCH_STATE:
  batch_items: {batch_plan.items}
  batch_plan_file: {batch_plan_file}
  batch_status: READY

Logge: "BATCH_PLANNING: Batch-Plan erstellt — {batch_plan.items.length} Items, Rationale: {batch_plan.rationale}"
FOR item IN batch_plan.items:
  Logge: "  [{item.order}] {item.name} (Aggregat-GROB: {item.aggregat_grob}, Abh.: {item.depends_on})"

# ═══ BL-Status-Transition: READY → PLANNED (RF-BDF-028, AK-12, INV-3) ═══
# Fuer BL-Items im Batch: Status READY → PLANNED setzen
FOR item IN batch_plan.items:
  IF item.source == "backlog" AND item.status == "READY":
    Schreibe item.status = "PLANNED" in Vault-Frontmatter
    Aktualisiere _backlog_index.md (Status-Spalte: PLANNED)
    Logge: "[BDF] BL-{item.id}: READY → PLANNED (Batch eingeplant)"

# ═══ BL-076: IDF-Delegation fuer BL-Items (T9, AK-03) ═══
# Wenn Batch BL-Items enthaelt, laeuft IDF VOR SDF.
# IDF materialisiert Spec-AKs in PL-Items, baut 2D-Matrix, clustert + sequenziert.
# Kanal 1 (globaler PL, task_source=pl) unveraendert — dort kein IDF-Call.
# Kanal 2 (BL-Items, task_source=backlog) wird durch IDF geroutet.
# IDF schreibt BL_LIFECYCLE_STATE.items_routed_ready — wichtig fuer BL-075 T2 Loop.
has_bl_items = ANY(item.source == "backlog" FOR item IN batch_plan.items)
IF has_bl_items:
  # Pro BL-Item in der Batch: IDF aufrufen (sequentiell)
  FOR bl_item IN [item FOR item IN batch_plan.items IF item.source == "backlog"]:
    Logge: "[BL-076] BDF Phase 2b: Delegation an IDF fuer BL-{bl_item.id}"
    Skill(skill="_IDF_orchestrate", args="{bl_item.id}")
    # IDF hat IDF_PIPELINE_STATE.status = DONE gesetzt
    # IDF hat BL_LIFECYCLE_STATE.items_routed_ready = N geschrieben (AK-09)
    # IDF hat pl-Items in {VAULT}/Backlog/BL-{NNN}/6_PL/ erstellt
  Logge: "[BL-076] BDF Phase 2b: Alle {len} BL-Items durch IDF materialisiert"
# Kein ELSE — wenn keine BL-Items, weiter mit normalem PL-Flow (Phase 3 SDF direkt)
```

### Phase 3: ITEM_RUNNING — SDF-Delegation mit Batch (RF-BDF-003, RF-BDF-005, RF-BDF-020)

```
# State: ITEM_RUNNING
Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
  bdf_status: ITEM_RUNNING
  current_item: {batch_plan.items[0].name}  # erstes Item des Batches (Referenz)
  BDF_NEXT_TRIGGER: false
  BDF_ITEM_DONE: null
Schreibe in {WORKING_DIR}/_manifest.md → BDF_BATCH_STATE.batch_status: RUNNING

# Difficulty-Delegation (RF-BDF-005):
# BDF uebergibt max_difficulty als Obergrenze — SDF entscheidet intern (7-Modi-Logik).
# BDF hat KEINEN eigenen Klassifikator — SDF bestimmt Modus per Q1-Q9.
# Difficulty-Capping (AK-005e): max_difficulty = Obergrenze fuer den gesamten Batch
batch_difficulty = max_difficulty  # SDF entscheidet intern per Item, BDF gibt Obergrenze

# Batch-Parameter als --batch vorbereiten (kommaseparierte Item-IDs)
batch_ids = batch_plan.items.map(item → item.name).join(",")

# ═══ Reifegrad-Signal fuer BL-Items an SDF uebergeben (RF-BDF-029, AK-05) ═══
# BDF liest Reifegrad (read-only, INV-4) und uebergibt als Advisory-Signal an SDF.
# Reifegrad informiert Pipeline-Erwartung: REIF→I, SC-REIF→SC, UNREIF→WP (W8).
# RF-BDF-022 intakt: BDF bewertet KEINE Modi — SDF entscheidet autonom innerhalb des Bands.
# Bestimme task_source: "backlog" wenn mind. 1 BL-Item im Batch, sonst "pl" (default)
has_bl_items = ANY(item.source == "backlog" FOR item IN batch_plan.items)
task_source_arg = "backlog" IF has_bl_items ELSE "pl"

# Reifegrad als Manifest-Signal schreiben (SDF liest aus Manifest)
IF has_bl_items:
  # Fuer jeden BL-Item: Reifegrad + Vault-Path + ID ins Manifest schreiben
  bl_batch_items = [item FOR item IN batch_plan.items IF item.source == "backlog"]
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_BATCH_STATE.bl_items:
    FOR bl_item IN bl_batch_items:
      - id: {bl_item.id}
        reifegrad: {bl_item.reifegrad}
        vault_path: {bl_item.vault_path}
  Logge: "[BDF] Reifegrad-Signal an SDF: {bl_batch_items.length} BL-Items mit Reifegrad-Feldern"

# ═══ BL-082 DRY-RUN-MODUS (AK-01..10) ═══
# Verzweigung: active_mode == "dryRun" → Mock-SDF statt echter SDF-Skill-Aufruf
# Zweck: Architektur-Validierung ohne stundenlange Code-Produktion
# Semantik: Phase 1/2/2b/2c (IDF) laufen REAL, nur Phase 3 SDF wird gefakt
# Report: .claude/output/DryRun_{NAME}_{DATE}.md
# Cleanup: Dry-Run erzeugte PL-Items (Prefix "DRY_RUN:") werden am Ende geloescht
active_mode_current = BDF_PIPELINE_STATE.active_mode ?? "normal"

IF active_mode_current == "dryRun":
  # ═══ MOCK-SDF BLOCK (AK-03) ═══
  # KEINE Skill(_SDF_orchestrate) Invokation
  # KEINE Code-Aenderungen in .claude/commands oder _orchestrate.md
  # KEINE Tests ausgefuehrt
  # NUR Manifest-Schreibungen + Dry-Run-Report
  Logge: "[BL-082 DRY-RUN] Mock-SDF aktiviert fuer Batch {batch_ids}"

  # Dry-Run-Report vorbereiten (AK-04)
  dry_run_report = {
    date: {Datum},
    feature_branch: BDF_PIPELINE_STATE.feature_branch,
    mode: "dryRun",
    batch_items: batch_plan.items,
    unified_pool_before_dep: unified_before_dep_count,
    unified_pool_after_dep: unified.length,
    dep_ready: dep_ready.length,
    dep_deferred: dep_deferred.length,
    idf_executed: has_bl_items,
    materialized_pl_items: [],  # gefuellt unten falls IDF lief
    simulated_sdf_path: [],     # welchen Modus HAETTE SDF gewaehlt
    anti_zirkel_counters: {
      bdf_scan_iterations: BDF_PIPELINE_STATE.bdf_scan_iterations,
      bdf_bl_handoff_depth: BDF_PIPELINE_STATE.bdf_bl_handoff_depth,
      reifung_cycles: BDF_PIPELINE_STATE.reifung_cycles
    },
    terminal_state: null  # am Ende gefuellt
  }

  # Pro Batch-Item: SDF-Modus simulieren (Anzeige, kein echter Lauf) (AK-04)
  FOR item IN batch_plan.items:
    # Heuristik fuer Modus-Vorhersage (KEINE echte SDF-Q1-Q9 Logik, nur Anzeige):
    # - k_score < 20 ODER reifegrad=REIF kleinste → M1_INLINE
    # - k_score 20-40 → M2_I_STANDARD
    # - k_score 40-70 → M4_SC_FULL
    # - k_score 70-100 → M5_SC_FULL_I_FULL
    # - k_score > 100 → Mitose_Flag (waere BL-081 dep-check, Epic BL-083 Kategorie)
    k = item.k_score ?? 50  # default medium
    predicted_mode = "M1_INLINE" IF k < 20
                   ELSE "M2_I_STANDARD" IF k < 40
                   ELSE "M4_SC_FULL" IF k < 70
                   ELSE "M5_SC_FULL_I_FULL" IF k < 100
                   ELSE "MITOSE_REQUIRED"
    dry_run_report.simulated_sdf_path.append({
      id: item.id,
      k_score: k,
      reifegrad: item.reifegrad,
      predicted_mode: predicted_mode,
      would_edit: "SKIPPED (dryRun)",
      would_test: "SKIPPED (dryRun)"
    })
    Logge: "[BL-082 DRY-RUN] {item.id}: k={k} → {predicted_mode} (SKIPPED)"

  # Mock SDF-Erfolg ins Manifest schreiben (AK-03)
  Schreibe in {WORKING_DIR}/_manifest.md → DF_PIPELINE_STATE:
    df_status: DRY_RUN_DONE
    pipeline_route: DRY_RUN
    sc_srs_last: "n/a (dryRun)"
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
    BDF_NEXT_TRIGGER: true
    BDF_ITEM_DONE: {batch_plan.items[0].name}

  # Dry-Run-Report schreiben (AK-04)
  dry_run_report_path = "{WORKING_DIR}/.claude/output/DryRun_{NAME}_{Datum}.md"
  Schreibe {dry_run_report_path} mit Frontmatter type=dry_run_report + dry_run_report Inhalt

  # Cleanup der von IDF erzeugten DRY_RUN-prefixed PL-Items (AK-06)
  IF has_bl_items:
    FOR bl_item IN bl_batch_items:
      idf_pl_dir = "{VAULT}/Backlog/BL-{bl_item.id}/6_PL/"
      FOR pl_file IN idf_pl_dir:
        IF pl_file.filename starts_with "DRY_RUN_":
          Loesche pl_file
          Logge: "[BL-082 DRY-RUN] Cleanup: {pl_file} geloescht"

  Logge: "[BL-082 DRY-RUN] Mock-SDF DONE — Report: {dry_run_report_path}"
  # Faellt durch in den normalen Post-SDF-Pfad (BDF_NEXT_TRIGGER wurde true gesetzt)

ELSE:
  # ═══ NORMALER HANDSCHUH-WECHSEL: BDF → SDF (mit Batch) ═══
  # ANTI-PATTERN: Agent(prompt="PL-Item ...") direkt ← VERBOTEN (CS3 Root Cause)
  # ANTI-PATTERN: Skill("_I_orchestrate", ...) direkt ← VERBOTEN
  # RICHTIG: Skill("_SDF_orchestrate") mit Batch-Plan — SDF entscheidet 7-Modi pro Item
  #
  # Der Team Lead ist EINE Instanz die Handschuhe wechselt:
  #   BDF-Handschuh AUS → SDF-Handschuh AN → SDF laeuft → SDF-Handschuh AUS → BDF-Handschuh AN
  # State ueberlebt im Manifest (BDF_PIPELINE_STATE + BDF_BATCH_STATE bleiben erhalten).

  Skill(skill="_SDF_orchestrate", args="{NAME} {batch_difficulty} {ceiling} {floor} --task-source={task_source_arg} --batch={batch_ids}")

# Nach SDF-Completion: Team Lead ist ZURUECK im BDF-Kontext.
# SDF hat BDF_NEXT_TRIGGER + BDF_ITEM_DONE ins Manifest geschrieben.
# Lies Manifest um Ergebnis zu pruefen.
Lies {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE
# ABORT-Diagnose (AK-003i, AK-010a): SDF-Zustand fuer Ursachen-Analyse lesen
Lies {WORKING_DIR}/_manifest.md → DF_PIPELINE_STATE
df_status = DF_PIPELINE_STATE.df_status ?? "unbekannt"
sc_srs_last = DF_PIPELINE_STATE.sc_srs_last ?? "n/a"

IF BDF_NEXT_TRIGGER == true:
  # DONE: SDF hat erfolgreich abgeschlossen
  bdf_status = ITEM_DONE
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: ITEM_DONE

  # Protokoll-Eintrag
  items_done.append({
    name: next_item.name,
    date: {Datum},
    route: (aus DF_PIPELINE_STATE.pipeline_route),
    srs: (aus DF_PIPELINE_STATE.sc_srs_last)
  })
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.items_done: {items_done}

  # HiL-Notification bei Saettigung (RF-BDF-010)
  → Springe zu Phase 4 (Post-DONE Checks)

ELSE:
  # ABORT: SDF wurde abgebrochen
  # VOLLE AUTONOMIE (J3): Kein AskUserQuestion — auto-skip, Loop weiter
  Logge: "SDF ABORTED fuer Item: {next_item.name} — Ursache: df_status={df_status}, SRS={sc_srs_last}"

  # items_failed zaehlen (fuer STUCKED-Promotion nach 2 Versuchen)
  existing_entry = items_failed.find(f => f.name == next_item.name)
  IF existing_entry != null:
    existing_entry.retry_count = (existing_entry.retry_count ?? 1) + 1
    existing_entry.reason = "SDF_ABORTED (Versuch {existing_entry.retry_count}): df_status={df_status}, SRS={sc_srs_last}"
    Logge: "Auto-Skip: Item '{next_item.name}' Versuch {existing_entry.retry_count}/2 — weiter mit naechstem Item"
  ELSE:
    items_failed.append({
      name:        next_item.name,
      date:        {Datum},
      reason:      "SDF_ABORTED: df_status={df_status}, SRS={sc_srs_last}",
      retry_count: 1
    })
    Logge: "Auto-Skip: Item '{next_item.name}' Versuch 1/2 — weiter mit naechstem Item"

  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.items_failed: {items_failed}
  # Stale-Artefakte Warnung (AK-003l): Analyse-Reste koennen verbleiben
  Logge: "Warnung: Analyse-Artefakte von Item '{next_item.name}' koennen in .claude/analysis/* verbleiben (v2: automatisches Cleanup)"
  bdf_status = SCANNING
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: SCANNING
  → Springe zu Phase 2 (SCANNING)
```

### Phase 4: Post-DONE Checks (RF-BDF-010, RF-BDF-011)

```
# RF-BDF-010: HiL-Notification bei SC-ANALYSE Saettigung
# Pruefe DF_PIPELINE_STATE des abgeschlossenen SDF-Laufs
Lies {WORKING_DIR}/_manifest.md → DF_PIPELINE_STATE

IF DF_PIPELINE_STATE zeigt SC-Analyse Stagnation nach >= 2 Zyklen:
  # Notification an User, BDF laeuft WEITER (kein Stop)
  Logge: "NOTIFICATION: SC-Analyse Saettigung fuer '{current_item}' nach 2+ Zyklen"
  Logge: "Item wird als DEFERRED markiert (nicht FAILED, nicht [x])"
  # DEFERRED: Eigener Status — Item bleibt offen aber wird im selben BDF-Lauf nicht erneut versucht
  items_failed.append({name: current_item, date: {Datum}, reason: "SC_DEFERRED"})  # Verhindert Re-Selektion
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.items_failed: {items_failed}

# RF-BDF-011: PL→Spec Promotion Trigger (v1.0 Placeholder)
# Post-DONE Pruefung: Ist das abgeschlossene Item Spec-relevant?
# Logik: Wenn SDF SC-Zyklen SPEC-relevante Erkenntnisse produziert haben:
#   1. Task.md ECs erweitern (neuer EC-Eintrag fuer promoted Items)
#   2. GAP-Score Neuberechnung (Spec erweitert → GAP sinkt)
# TODO v1.1: Automatische Promotion-Erkennung implementieren
Logge: "Spec-Promotion Check: {current_item} (v1.0 Placeholder — manuelle Pruefung)"
```

### Phase 5: Sicherheits-Stop Guard (RF-BDF-012)

```
# Guard: items_done.length >= bdf_max_items
IF items_done.length >= bdf_max_items:
  Logge: "Sicherheits-Stop: {bdf_max_items} Items erreicht"
  bdf_status = EMPTY  # Saubere Terminierung (wie Parkplatz leer)
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: EMPTY
  → Springe zu Phase 6 (Terminal)

# ═══ BL-075 T4: Anti-Zirkel Zaehler Reset nach erfolgreichem Item (AK-09) ═══
# Ein erfolgreich verarbeitetes Item = gesunder Fortschritt → Counter null
bdf_scan_iterations = 0
reifung_cycles = 0
Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
  bdf_scan_iterations: 0
  reifung_cycles: 0

# Kein Stop → Zurueck zu SCANNING
bdf_status = SCANNING
Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: SCANNING
→ Springe zu Phase 2 (SCANNING)
```

### Autonomie-Gradation (RF-BDF-013)

| Situation | Verhalten | HiL? |
|-----------|-----------|------|
| Normaler SDF-Durchlauf (Batch) | BDF wartet auf BDF_NEXT_TRIGGER=true | NEIN |
| _BDF_batchPlan liefert leeren Plan | Skip + Warnung, erneut SCANNING | NEIN |
| _finish mit offenen Items | Dark Factory Guard → automatisch PARKEN | NEIN |
| PL-Item ohne Prioritaet | Skip + Warnung loggen, naechstes Item | NEIN |
| Parkplatz leer | EMPTY → SDF(postPhase) → DONE (BL-041) | NEIN |
| Post-Phase Vorpruefung FAIL | SDF entscheidet intern (Pre-PR uebersprungen) | NEIN |
| bdf_max_items erreicht | Sicherheits-Stop → Terminal | NEIN |
| SDF ABORTED (Stagnation >= 7.0) | auto-skip: items_failed+1, weiter SCANNING | NEIN |
| SDF SC-Saettigung (2 Zyklen) | DEFERRED, Notification, weiter | Notification (kein Block) |
| SDF ABORTED (TDD-MAX) | auto-skip: items_failed+1, weiter SCANNING | NEIN |
| SDF ABORTED (andere Ursache) | auto-skip: items_failed+1, weiter SCANNING | NEIN |
| QUESTION-Item [?] (J3) | auto-skip in SCANNING, BDF_NEXT_TRIGGER=true, Loop weiter | NEIN |
| STUCKED-Item [!] (J3, retry_count>=2) | auto-skip in SCANNING, [!] setzen, Loop weiter | NEIN |
| ALL_TERMINAL (nur [x],[~],[?],[!],blocked) | EMPTY → SDF(postPhase) → DONE, Notification mit Zaehlen | Notification |
| BDF-Versuch Agent() direkt | VERBOTEN (RF-BDF-022) — NIEMALS ausfuehren | — |
| SDF-testRun: fail > 0, neue PL-Items | SCANNING (neue Items normal bearbeiten) | NEIN |
| SDF-testRun: alle GREEN               | SDF(postPhase) → DONE                   | NEIN |
| SDF-testRun: ABORTED                  | AskUserQuestion (skip/retry/stop)       | **JA** |

### Phase 6: Terminal — DONE + Protokoll-Rollover (RF-BDF-004, BL-041)

```
# Terminal-Zustand: DONE (nach SDF postPhase) oder ABORTED(stop)
# POST_PHASE ist NICHT mehr in BDF — PostBatch uebernimmt (BL-133 Slice-5, AK-4; frueher BL-041 v3.2.0)
# PostBatch fuehrt aus: _T_orchestrate (Tests) + _stage_orchestrate (Commit) — Thin-Wrapper, ADR-4
# BDF wartet auf BDF_NEXT_TRIGGER=true von PostBatch (POSTBATCH_PIPELINE_STATE.status=DONE)
# Der Handschuh-Wechsel zu SDF erfolgt im EMPTY-Handler (Phase 2), NICHT hier.

# State: DONE (gesetzt vom EMPTY-Handler nach SDF-Completion)
bdf_status = DONE
Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.bdf_status: DONE

# Protokoll-Rollover: Prepend BDF-Zusammenfassung in _manifest_protokoll.md (AK-02-02)

bdf_zusammenfassung = """
## BDF_orchestrate [{Datum}] — {bdf_status}
  Items verarbeitet: {items_done.length}
  Items fehlgeschlagen: {items_failed.length}
  Items DONE: {items_done als Liste}
  Items FAILED: {items_failed als Liste}
  Ceiling: {ceiling}, Floor: {floor}
  Max Difficulty: {max_difficulty}
  bdf_max_items: {bdf_max_items}
  Ergebnis: {bdf_status}
"""

Prepend bdf_zusammenfassung an _manifest_protokoll.md (W18):
  Frontmatter: last_append={Datum}, append_count++

# BDF_PIPELINE_STATE bereinigen (bdf_status bleibt als Referenz)
Logge: "=== BIG DARK FACTORY {bdf_status} ==="
Logge: "{items_done.length} Items verarbeitet, {items_failed.length} fehlgeschlagen"
```

---

## Resume-Detection (RF-BDF-012)

```
# Beim Start: Pruefe ob BDF_PIPELINE_STATE bereits existiert mit bdf_status != INIT
Lies {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE

# ═══ FACTORY_STATES Resume-Check (RF-02, AK-02-01..02, BL-029) ═══
Lies FACTORY_STATES aus {WORKING_DIR}/_manifest.md (falls vorhanden)
IF FACTORY_STATES != null:
  FOR instance_id, factory IN FACTORY_STATES:
    IF factory.status == "RUNNING":
      # Stale-Factory-Erkennung (AK-02-02): updated aelter als 30 Minuten → STALE
      IF factory.updated != null AND (Datum - factory.updated) > 30_Minuten:
        Logge: "[FACTORY-RESUME] STALE: {instance_id} (updated: {factory.updated}) → ABORTED"
        factory.status = "ABORTED"
        Aktualisiere Manifest
      ELSE:
        Logge: "[FACTORY-RESUME] Aktive Factory gefunden: {instance_id} (status: RUNNING)"

IF BDF_PIPELINE_STATE.bdf_status == "TEST_RUNNING":
  Logge: "Resume: TEST_RUNNING unterbrochen — testRun_done=false, zurueck zu EMPTY-Handler"
  bdf_status = EMPTY
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE:
    bdf_status: EMPTY
    testRun_done: false     # sicherstellen — testRun nochmal laufen
    active_mode: testRun    # Hinweis: war mitten in testRun
  → Springe zu Phase 2 (SCANNING → EMPTY-Handler aktiviert TEST_RUNNING erneut)

IF BDF_PIPELINE_STATE.bdf_status IN ["SCANNING", "BATCH_PLANNING", "ITEM_RUNNING", "ITEM_DONE"]:
  # Vorheriger BDF-Lauf wurde unterbrochen
  Logge: "Resume-Detection: Vorheriger BDF-Lauf gefunden (Status: {bdf_status})"
  Logge: "Items bereits DONE: {items_done.length}, Items FAILED: {items_failed.length}"
  # Uebernehme bestehende items_done + items_failed
  # Setze bdf_status = SCANNING und fahre fort (Batch-Plan neu erstellen)
  bdf_status = SCANNING
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_BATCH_STATE.batch_status: null  # Batch-Plan invalidieren

  # Feature-Branch Resume (v2.7.0): Checkout bestehenden Feature-Branch
  feature_branch = BDF_PIPELINE_STATE.feature_branch
  IF feature_branch != null:
    Fuehre aus: git checkout {feature_branch}
    Logge: "[PR-WORKFLOW] Resume: Feature-Branch '{feature_branch}' ausgecheckt"

  # IDEMPOTENZ-Guard (PN-7 Z1): IN_ARBEIT-Items aus abgebrochenem Lauf sichern
  items_neu = Lies {WORKING_DIR}/_parking-lot.md → alle Items mit "[STATUS: IN_ARBEIT]"
  FOR item IN items_neu:
    IF item.name NOT IN [d.name FOR d IN items_done] AND item.name NOT IN [f.name FOR f IN items_failed]:
      Logge: "Resume-Guard: '{item.name}' ist IN_ARBEIT — als FAILED markieren (F-02/F-05, PN-7)"
      items_failed.append({name: item.name, date: {Datum}, reason: "IN_ARBEIT_ABGEBROCHEN"})
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.items_failed: {items_failed}

  → Springe zu Phase 2 (SCANNING)

IF BDF_PIPELINE_STATE.bdf_status == "EMPTY":
  # ═══ BL-075 T4: Resume-Hook EMPTY → testRun_done=false (RF-BDF-035, AK-12) ═══
  # Pfad 6 Deadlock-Quelle: Beim Resume aus EMPTY darf der "testRun_done=true → direkt postPhase"
  # Pfad NIE getriggert werden. Zwinge einen frischen testRun-Guard-Durchlauf.
  Logge: "[BL-075] Resume EMPTY → testRun_done=false (forced rescan)"
  Schreibe in {WORKING_DIR}/_manifest.md → BDF_PIPELINE_STATE.testRun_done: false
  Logge: "Resume-Detection: EMPTY-Zustand — frischer SCANNING → EMPTY-Handler delegiert"
  → Springe zu Phase 2 (SCANNING → EMPTY-Handler delegiert an SDF)

IF BDF_PIPELINE_STATE.bdf_status IN ["DONE", "ABORTED"]:
  # Vorheriger Lauf ist abgeschlossen — Neustart
  → Springe zu Phase 1 (Initialisierung)
```

---

## QUICK-START

```
1. /_param dark_factory=true → hil=off + GLOBAL_MODUS=big_dark_factory
2. BDF_PIPELINE_STATE: INIT → SCANNING
3. OUTER LOOP:
   a. SCANNING: {WORKING_DIR}/_parking-lot.md lesen → offene Items (Prio-FIFO)
      IF leer → EMPTY → SDF(postPhase) → DONE (Schritt 5)
   b. BATCH_PLANNING: Skill("_BDF_batchPlan") → Batch-Plan-Datei lesen
      KEIN inline Batch-Planen! KEIN Komplexitaets-Bewerten! (RF-BDF-022)
   c. ITEM_RUNNING: Skill("_SDF_orchestrate", "--batch={ids}") — KEIN Agent() direkt!
      SDF entscheidet 7-Modi pro Item (BDF weiss das NICHT)
   d. Warte auf BDF_NEXT_TRIGGER==true (DONE) oder ABORT
   e. Post-DONE: Saettigungs-Check + Spec-Promotion
   f. Sicherheits-Stop: items_done >= bdf_max_items?
   g. → Zurueck zu (a) SCANNING
4. ABORTED: SDF ABORTED + User "stop" → Protokoll-Rollover
5. POST_PHASE (nur wenn PL LEER):
   PostBatch (delegiert, BL-133 Slice-5 AK-4) — 1 Handschuh-Wechsel zum Thin-Wrapper
   PostBatch ruft: _T_orchestrate (Tests) + _stage_orchestrate (Commit). Feature-Ende via _Post_orchestrate.
```

### ANTI-PATTERN Schnell-Referenz (RF-BDF-022)

| Situation | VERBOTEN | RICHTIG |
|-----------|----------|---------|
| Code-Aenderung noetig | `Agent("PL-Item ...")` | `Skill("_SDF_orchestrate", "--batch=...")` |
| Komplexitaet einschaetzen | BDF bewertet SRS/COMPLEXITY | `Skill("_BDF_batchPlan")` delegiert das |
| I_orchestrate aufrufen | `Skill("_I_orchestrate")` direkt | SDF waehlt I_orch intern via 7-Modi |
| SC_orchestrate aufrufen | `Skill("_SC_orchestrate")` direkt | SDF waehlt SC_orch intern via 7-Modi |

---

ARGUMENTS: $ARGUMENTS
