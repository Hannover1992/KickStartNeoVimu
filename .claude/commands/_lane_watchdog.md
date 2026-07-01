# /_lane_watchdog — Mothership-Watchdog ueber die Parallel-Lanes

```yaml
status: active
version: 1.0.0
created: 2026-06-22
op: SubCommand
phase: Watchdog
type: orchestration
model_tier: opus
chain_position: parallel
feature_anchor: BL-322
related:
  - _crown
  - _sanity_check_pre
  - _sanity_check_post
  - _worktree_parallel
  - lane_watchdog.py
provenance: "Destilliert aus dem 6h-Live-Lauf 2026-06-21/22 (3-Lane-Parallel-Begleitung). Der Lauf war gut; dieser Command macht ihn wiederholbar."
```

---

## Zweck

**Der Mensch im Mothership begleitet N Parallel-Lanes (Worktrees A/B/C/...) — ohne 4. Worker zu sein.**

Beim Worktree-Parallel-Bau (INV-WORKTREE-PARALLEL, `/_worktree_parallel`) faehrt jede Lane ein eigenes
Roadmap-Goal in einem eigenen Terminal. Der Lead dieser Session ist NICHT eine weitere Lane — er ist der
**OmniCommand-Architekt im Beobachter-Sitz**: er schaut Tick fuer Tick nach, ob die Lanes **korrekt durch die
Orchestratoren traversieren**, wo sie stehen, ob eine stale/eingefroren ist, und ob ein **echter struktureller
Verstoss** auftritt. Es ist eine **Mischung aus `/_crown`** (Stall/Stuck-Detektion eines Workers) **und
`/_sanity_check`** (Prozess-Drift) — aber ueber MEHRERE Lanes gleichzeitig statt ueber einen Worker.

```
   +-----------------------------------------------------------------------+
   |                       MOTHERSHIP (dieser Lead)                        |
   |   beobachtet read-only, greift NIE in eine Lane ein ("nur")           |
   |                                                                       |
   |   Lane A (wtA/roadmap-a)   Lane B (wtB/roadmap-b)   Lane C (...)       |
   |        |                        |                        |            |
   |   git+audit+plan           git+audit+plan           git+audit+plan    |
   |        \________________________|________________________/           |
   |                       lane_watchdog.py (read-only)                    |
   |                                  |                                    |
   |        PROGRESS / ALIVE / STALL / VIOLATION  pro Lane                 |
   |                                  |                                    |
   |   gesund -> knapp melden                                              |
   |   STALL  -> gated/wartet-auf-User (legitim) vs eingefroren (Nudge)    |
   |   echter Verstoss -> PFLASTER + Parking-Lot/BL (ARCHITEKT-1)          |
   +-----------------------------------------------------------------------+
```

**Langzeit-Durability-Test:** ueber viele Stunden beobachten, ob die Lanes die Pipeline
(A -> IDF -> SDF -> post -> I/SC) prozesstreu traversieren — RED!=GREEN, INV-AO-CALLER, kein Mega-Worker.

---

## Aufruf

```
/_lane_watchdog [begleiten] [--every=14]  # DEFAULT: Cron armen + DURCHGEHEND begleiten (wie /_crown). NICHT einmalig.
                                          #   armt einen recurring Cron, macht sofort den ersten Tick.
/_lane_watchdog tick                      # genau EIN Tick (das was der Cron feuert; auch manuell nutzbar)
/_lane_watchdog disarm                    # Cron pausieren (NUR bei statischem Stand = Laerm-Vermeidung)
/_lane_watchdog deep {A|B|C}              # Tiefen-Check EINER Lane (Audit-Tail: baut sie oder haengt sie?)
```

> **NATUR (User-Direktive 2026-06-22):** Der Watchdog ist ein **Begleiter**, kein Einmal-Befehl. Wie `/_crown`
> einen Cronjob armt und den Worker bis DONE begleitet, armt `/_lane_watchdog` per Default einen recurring Cron
> und begleitet die Lanes durchgehend (Tick fuer Tick) bis sie konvergiert/gated sind. Einmaliges Ticken
> (`tick`) ist die Ausnahme, nicht der Default. `disarm` NUR bei nachweislich statischem Stand (INV-WD-6).

---

## VERTRAG

```
+======================================================================+
|  VERTRAG: /_lane_watchdog                                            |
+======================================================================+
|  ROLLE: MOTHERSHIP-BEOBACHTER. KEIN Worker, KEINE Lane.              |
|         Read-only ueber die GETEILTEN State-Spuren der Lanes.        |
|                                                                      |
|  LIEST (read-only):                                                  |
|    {wt}/.git           git log/-rev-list pro Lane-Branch             |
|    {wt}/.claude/audit/audit.jsonl   BLOCK/VIOLATION/MEGA_WORKER/...   |
|    {vault}/_lane_plan.md            current BL pro Lane              |
|    .claude/analysis/_watchdog_state.json   Baseline (Diff-Quelle)    |
|                                                                      |
|  SCHREIBT (nur eigenes Beobachter-State, NIE Lane-Artefakte):        |
|    .claude/analysis/_watchdog_state.json   neue Baseline             |
|    .claude/analysis/_watchdog_log.md       Observations-Log (append) |
|    Bei echtem Verstoss: Parking-Lot/Backlog via /_backlog            |
|                                                                      |
|  RUFT:                                                               |
|    py -3 .claude/scripts/lane_watchdog.py   (der Mess-Kern)          |
|    CronCreate / CronDelete                  (Tick-Selbst-Taktung)    |
|    /_backlog                                (nur bei echtem Befund)  |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-WD-1 (OBSERVE-ONLY "nur"): NIE in eine Lane eingreifen.       |
|              KEIN Orchestrator-Load, KEIN Build, KEIN merge/push     |
|              fuer eine Lane. Nudge/go sind USER-Entscheidungen.      |
|    INV-WD-2 (KERNPFLICHT): jeder Tick prueft die Orchestrator-       |
|              Traversierung (Trail in kanonischer Reihenfolge +       |
|              Berater als WORKER_SPAWN->SKILL_LOAD, nicht inline).    |
|    INV-WD-3 (ARCHITEKT-1): echter struktureller Verstoss -> sofort   |
|              Pflaster (Log) + proper-fix-BL (prio hoch, parent       |
|              BL-322). NIE still liegen lassen.                       |
|    INV-WD-4 (NO-FALSE-ALARM): Guard-Bursts (Test-Suites, <30s-       |
|              Cluster) + sauberes Immunsystem-Blocken sind KEIN       |
|              Befund. Echter Verstoss = Guard liess durch ODER Lane   |
|              stalled trotz Aktivitaet. Verifizieren vor Flag.        |
|    INV-WD-5 (STALL-DISAMBIG): STALL != Problem. Erst unterscheiden   |
|              gated/wartet-auf-User-go (legitim) vs eingefroren       |
|              (Auto-Advance-Gap, operativer Nudge).                   |
|    INV-WD-6 (LAERM-HYGIENE): N identische Ticks -> Cron pausieren,   |
|              reaktivieren bei Bewegung. Tick-Spam ist kein Wert.     |
+======================================================================+
```

---

## SCHRITT 1: MESSEN (read-only)

```
py -3 .claude/scripts/lane_watchdog.py
```

Liefert pro Lane JSON:
- `sha` / `subj` / `age_min` — letzter Commit + Alter (merge-STABILES Signal)
- `ahead` — Commits vor develop (ungemergt)
- `current_bl` — aus `_lane_plan.md`
- `audit_lines` / `audit_delta` / `last_event` / `last_age_min` — Audit-Aktivitaet
- `progress` (neuer Commit seit Baseline) / `alive` (Audit waechst ODER frisch) / `stalled`
- `trail` — Orchestrator-Sequenz (`A -> IDF -> SDF -> post`) · `last_cmd` · `ao_viol`
- `bad_events` (recency-gefiltert) · `guard_burst_test` (Test-Cluster-Heuristik)
- `flags` (Top-Level) — STALL / GUARD_BLOCK Kandidaten

> **Mess-Subtilitaeten (im Skript gehaertet, hier zur Interpretation):**
> - `audit.jsonl` wird beim `git merge develop` UEBERSCHRIEBEN -> als Stall-Signal allein unzuverlaessig.
>   Darum ist git-Commit-Age der robuste Co-Faktor (STALL nur wenn audit>35 UND commit>35).
> - Naive Audit-Timestamps = LOKALE Zeit (CEST), git %cI = tz-aware. Skript rechnet beides korrekt.
> - Audit-Trails koennen ueber Merges lane-fremde Events tragen (BL-445) -> Trail ist Indiz, nicht Beweis;
>   bei Zweifel `deep {Lane}` (Audit-Tail der Lane direkt).

---

## SCHRITT 2: KLASSIFIZIEREN + ORCHESTRATOR-SANITY (INV-WD-2, Kernpflicht)

Pro Lane:

| Signal | Bedeutung | Aktion |
|---|---|---|
| `progress=true` ODER `alive=true`, `trail` kanonisch | gesund, baut | knapp melden |
| `stalled=true`, current=gated-BL | wartet legitim auf User-go | melden, KEIN Flag (INV-WD-5) |
| `stalled=true`, current=READY-BL, kein Orchestrator | Auto-Advance-Gap | Nudge anbieten (User fuehrt aus) |
| `ao_viol != []` ODER `bad_events` mit AO/MEGA-Block, NICHT burst | INV-AO-CALLER/Mega-Worker | INV-WD-3 (Pflaster + BL) |
| `guard_burst_test=true` | Test-Suite feuert Guards | info, KEIN Flag (INV-WD-4) |

**Orchestrator-Traversierung pruefen (jeder Tick):**
1. `trail` in kanonischer Reihenfolge? (`A -> IDF -> SDF -> post -> I/SC`; Spruenge/Rueckwaerts = Glance).
2. Auf der aktivsten Lane (groesstes `audit_delta`): `deep {Lane}` — sind Berater `WORKER_SPAWN` **dann**
   `SKILL_LOAD` (= Worker-Spawn-Pattern)? Oder fehlen Spawns (= Lead inline = Mega-Worker)?
3. `ao_viol` = Orchestrator via `WORKER_SPAWN` statt `SKILL_LOAD` geladen = INV-AO-CALLER-Verdacht.
   Autoritatives Signal bleibt der `agent_prompt_validator`-GUARD_BLOCK; `ao_viol` allein ist
   false-positive-anfaellig -> verifizieren.

---

## SCHRITT 3: ENTSCHEIDEN + MELDEN

```
gesund         -> knappe Lane-Tabelle (Status + Worauf-es-wartet). Kein Alarm.
STALL legitim  -> melden "wartet auf {go|Nudge}", als USER-Aktion ausweisen (INV-WD-1).
STALL operativ -> kopierbaren Nudge-Befehl anbieten (z.B. "git merge develop; /_A_orchestrate BL-NNN").
                  ABER: der USER fuehrt ihn aus, NICHT der Watchdog.
ECHTER VERSTOSS-> INV-WD-3:
                  1. Pflaster in .claude/analysis/_watchdog_log.md (append: Datum, Lane, Symptom, Wurzel,
                     test-induziert? non-blocking?).
                  2. proper-fix-BL via /_backlog (priority=hoch, type=bug, parent_epic=BL-322,
                     Pflaster + Wurzel + Fix-Skizze im Body). Duplikat-Check zuerst (existierendes BL erweitern).
```

**Melde-Stil (User-Direktive):** Klartext, nicht nur Zahlen. Pro Lane: was ist das Problem, was der Fix.
Lane-Tabelle (Status | Worauf-es-wartet). ASCII-sauber (kein Em-Dash/Pfeil-Unicode in kopierbaren Befehlen).

---

## SCHRITT 4: CRON-BEGLEITUNG (DEFAULT, wie /_crown — INV-WD-6)

Der Default-Aufruf `begleiten` ARMT den Cron und beginnt die durchgehende Begleitung (nicht einmalig):

```
begleiten (DEFAULT): CronCreate(recurring, alle N min [--every], prompt="WATCHDOG-TICK -> /_lane_watchdog tick")
                     + sofort der erste Tick (Schritt 1-3). Der Cron re-armt sich und begleitet Tick fuer Tick.
                     Mechanik = /_crown's Cronjob-Pattern (CronCreate recurring), uebertragen auf N Lanes.
tick:                genau EIN Tick — das, was der Cron feuert; auch manuell.
disarm (Ausnahme):   CronDelete(cron_id) NUR wenn N (>=5-6) Ticks IDENTISCH (statischer Stand = Laerm).
                     Reaktivieren bei Bewegung / "watchdog wieder an".
```

- **Begleitung ist die Natur** (User-Direktive): wie `/_crown` einen Worker bis DONE begleitet, begleitet
  `/_lane_watchdog` die Lanes bis Konvergenz/Gate — durchgehend per Cron, nicht als Momentaufnahme.
- Tick-Intervall 12-20min ueblich; bei reiner Idle/gated-Beobachtung laenger.
- Cache-Hinweis: recurring-Cron feuert ueber Stunden; jeder Tick ist ein frischer, knapper Lauf.

---

## ABGRENZUNG

- **`/_crown`** = ein Worker, Estimated-Duration + Cron-Recheck. `/_lane_watchdog` = N Lanes, git+audit+plan-Diff.
- **`/_sanity_check`** = Prozess-Drift einer Session. `/_lane_watchdog` = Traversierungs-Treue ueber Lanes.
- **`/_worktree_parallel`** = baut/koordiniert die Lanes. `/_lane_watchdog` = beobachtet sie (greift NIE ein).
- **Nicht** der Auto-Advance-Fixer: der Closed-Loop (BL-371) + Auto-Chain (BL-444) sind eigene BLs;
  der Watchdog MELDET den Gap, schliesst ihn nicht.

## Verwandte
- Kern: `.claude/scripts/lane_watchdog.py` · Log: `.claude/analysis/_watchdog_log.md` · State: `_watchdog_state.json`
- `/_worktree_parallel` (INV-WORKTREE-PARALLEL) · `/_crown` · `/_sanity_check_pre|post` · `/_backlog` (ARCHITEKT-1)
- Doktrin: CLAUDE.md OmniCommand-Architekt-Pflicht (ARCHITEKT-1/2/3) + INV-WT-Familie (BL-431)
