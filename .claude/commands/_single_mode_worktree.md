# /_single_mode_worktree — Single-Mode Fan-Out/Fan-In Betriebspfad (N=1, altmodisch)

```yaml
status: active
version: 1.0.0
created: 2026-06-12
op: SingleModeWorktree
phase: Implement-Betriebspfad
type: orchestration
chain_position: SDF-Implement-Inner-Loop (altmodischer N=1-Worktree-Pfad)
team_based: true
hil_capable: true
dark_factory_capable: true
bl-item: BL-328
gate: BL-230-Gate-B
```

---

## Zweck

Der **altmodische Lead+Team-getriebene Betriebspfad** fuer den Single-Mode-Worktree-Lauf
(BL-328, N=1). Pro Produktions-Batch faehrt der Team Lead **9 Schritte** durch einen echten
git-Worktree: Clean-Tree-Gate -> Base-Ref-Pin -> Bootstrap+Messung -> Stage-Loop IM Worktree ->
Worktree-Commits -> Fan-In-Merge -> Post-Merge-Green-Gate -> Windows-robuster Cleanup ->
Telemetrie. Jeder Batch wird zum gemessenen Mechanik-Test, der **U1/U4/U5 einbrennt, BEVOR**
echte Wellen (BL-230 Phase C-E) kommen.

**Exakt N=1 pro Welle (INV-SM-2)** — null Concurrency-Risiko. Der CODE-Pfad fuer Fan-Out/Fan-In
existiert dann (Lock-Klammer, Merge, 0-Orphan-Assertion), trivial-konfliktfrei bei N=1, bereit
fuer N>=2.

### Aufruf

```
/_single_mode_worktree <bl-id> [--target-tree <pfad>] [--n 1] [--audit <tmp-audit-pfad>]
```

- `<bl-id>` — der zu fahrende Backlog-Batch (z.B. BL-328).
- `--target-tree` — der Fan-Out-ZIEL-Tree (Produkt-/Worktree-Base-Repo). Default: das aktuelle
  Produktions-Repo des Batches. **NICHT** das Engine-Repo (OQ-D, INV-SM-1).
- `--n` — bleibt hart `1` (INV-SM-2). Ein anderer Wert wird ignoriert/abgelehnt; Nebenlaeufigkeit
  ist BL-230 Phase C-E, NICHT dieses Skill.
- `--audit` — Telemetrie-Ziel (`emit_telemetry`-Pfad). In Tests/Trockenlaeufen ein tmp-audit;
  im Produktions-Lauf der etablierte `audit.jsonl`-Stream.

### Vertrag

```
+===============================================================+
| VERTRAG: /_single_mode_worktree v1.0 (BL-328, N=1)            |
+===============================================================+
|                                                               |
| ROLLEN:                                                       |
|   TEAM LEAD (TL) = Pfad-Steuerung + Green-Klarheits-Urteil   |
|     - Faehrt die 9 Schritte in Reihenfolge                   |
|     - Git-Lifecycle (1/2/3/6/8/9) = INLINE Tool-Ops          |
|       (single_mode_worktree.py-Funktionen via Bash/py)       |
|     - Spawnt Build-Worker (Schritt 4) + Green-Urteil (7)     |
|     - Faellt das GREEN-KLARHEITS-URTEIL selbst (M2)          |
|     - Cleanup IMMER in finally (INV-SM-5), auch bei Abbruch  |
|                                                               |
|   BUILD-WORKER (Schritt 4) = Stage-Loop IM Worktree (rot/TDD)|
|     - cwd = Worktree-Pfad (NICHT Mothership)                 |
|     - Code-Writes worktree-relativ; Vault-Writes abs/G0      |
|     - Hooks/Guards via worktree_hook_router (LIVE)           |
|                                                               |
|   GREEN-URTEIL-MEMBER (Schritt 7) = Post-Merge-Bewertung     |
|     - faellt "ist dieser gruene Build WIRKLICH korrekt?"     |
|       (kognitiv, M2) — NICHT der done/hold-Wrapper allein    |
|                                                               |
| VEHIKEL (INV-VEHIKEL / OQ-A — komplett ALTMODISCH):          |
|   Git-Lifecycle = deterministische INLINE Tool-Ops           |
|   Build (4) + Green-Urteil (7) = benanntes TEAM (rot)        |
|   KEIN dispatch_implement-Motor (Motor bleibt OFF, OQ-A)     |
|                                                               |
+===============================================================+
```

---

## Die 9 Schritte (mit Vehikel je Schritt)

> **Vehikel-Doktrin (BL-330, [[_vehikel]]):** deterministische Schritte (festes I/O, kein
> Urteils-Seam) laufen als **INLINE Tool-Ops** ueber die `single_mode_worktree.py`-Funktionen;
> kognitive Schritte (Build, Green-Klarheits-Urteil) laufen als **benanntes Team-Member (rot)**.
> Der Lead wechselt den Handschuh zwischen beiden. **KEIN Workflow-Motor im Betriebspfad**
> (OQ-A, [[feedback_motor_erst_nach_stabilisierung]]).

Alle inline-Ops rufen die getestete Funktion via:
`py -3 .claude/scripts/single_mode_worktree.py` ist NICHT der Einstieg — die Funktionen werden
als Modul genutzt (`from single_mode_worktree import ...`) bzw. per kurzem `py -3 -c "..."`-Aufruf.
Jeder Aufruf reicht den **ZIEL-Tree explizit** durch (`git -C`), nie implizit gegen cwd.

### Schritt 1 — Clean-Tree-Gate (deterministisch, INLINE)

- **Vehikel:** inline Tool-Op `clean_tree_gate(target_tree)`.
- **Repo-Anwesenheits-Guard zuerst (T9):** ein git-loser ZIEL-Tree -> `decision="na"`, sauberer
  N/A-Pfad statt Improvisation.
- `decision=="abort"` (dirty ZIEL-Tree) -> **HARTES Abort** mit korrektivem Recovery-Hint
  ([[feedback_corrective_enforcement]]): committe/stashe im ZIEL-Tree, dann Welle erneut starten.
- `decision=="proceed"` -> weiter zu Schritt 2.
- **INV-SM-1:** prueft AUSSCHLIESSLICH den ZIEL-Tree (OQ-D), NIE die `.claude`-Churn des
  Engine-Repos — sonst Dauer-Abort (Findings #D U4).

### Schritt 2 — Base-Ref-Pin + Branch-Namens-Generator (deterministisch, INLINE)

- **Vehikel:** inline `pin_base_sha(target_tree, manifest_sha)` + `generate_worktree_branch_name(...)`.
- Base-SHA aus dem Manifest-Feld lesen (OQ-C, analog `BASE_BRANCH`); leer/ungueltig ->
  reproduzierbarer `git rev-parse HEAD`-Pin; persistiere den gepinnten SHA (G0/Lock).
- Kollisionsfreien Worktree-Branch-Namen nach dem `_B-N`-Schema generieren (gegen `existing`).
- **INV-SM-7:** Base-SHA reproduzierbar gepinnt; Branch-Name kollisionsfrei.

### Schritt 3 — Bootstrap + Messung (deterministisch, INLINE)

- **Vehikel:** inline `bootstrap_worktree(target_tree, worktree_path, branch, base_sha, build_cmd=...)`.
- `git worktree add <pfad> -b <branch> <base-sha>`; optionaler projekt-Bootstrap (dotnet restore /
  npm ci — Verfahren je Projekt = M2-Anteil: der Lead waehlt den `build_cmd`) IM Worktree-cwd.
- Misst `bootstrap_seconds` + `disk_bytes` -> Telemetrie-Quelle (Schritt 9).
- **U5:** Worktree-Ablage-Ort + 260-Zeichen-Pfadlimit beim Bootstrap beachten.

### Schritt 4 — Stage-Loop IM Worktree (KOGNITIV, TEAM-Member, rot/TDD)

- **Vehikel:** benanntes **Team-Member** (rot) — KEIN inline Tool, KEIN Workflow.
- Der Build-Worker arbeitet mit **cwd = Worktree-Pfad** (NICHT Mothership). Code-Writes sind
  cwd-relativ IM Worktree; Vault-Writes bleiben UNVERAENDERT abs/G0 (INV-SM-3).
- Hooks/Guards laufen via `worktree_hook_router` (LIVE `settings.json:36`); bei N=1
  (`namespace==None`) verhaelt sich der Router bit-identisch zu heute.
- **`resolve_code_write` bleibt DORMANT (OQ-B / INV-SM-6):** bei N=1 reicht Worker-cwd = Worktree;
  das Primitiv existiert, wird aber NICHT pipeline-weit verdrahtet.
- Der Lead erfasst die **Hook-Verdikte** dieses Schritts -> `hook_green_rate(hook_results)` (AK-5)
  fuer die Telemetrie (Schritt 9).

### Schritt 5 — Worktree-Branch-Commits (deterministisch, INLINE; Seam = M2-Verdrahtung)

- **Vehikel:** inline `commit_in_worktree(worktree_path, message)` (`git -C <worktree>`), bzw. die
  ELEVATE/BATCH_DONE-Commits ueber `_stage_orchestrate` mit **Worker-cwd = Worktree** (Leak-Guard,
  hil=off-autonom). NICHT Mothership-cwd (GAP-7).
- Repo-aware-Guard (T9): ein git-loser Pfad -> `committed=False` + N/A statt Crash.
- Der Mothership-HEAD bewegt sich hier NICHT — erst beim Fan-In (Schritt 6).

### Schritt 6 — Fan-In-Merge (deterministisch, INLINE; wave_fanin-Lock-Klammer)

- **Vehikel:** inline `fan_in_merge(target_tree, worktree_branch, lock_dir=...)`.
- `git merge --no-ff <worktree-branch>` in den Mothership, geklammert in
  `vault_lock zweck="wave_fanin"` (Fan-In-Barrier-Lock-CODE-Pfad existiert auch bei N=1,
  trivial-konfliktfrei).
- Konflikt -> `merge --abort` (Mothership bleibt sauber) + `merged=False`/`conflict=True` -> der
  Lead loest Recovery aus (Revert/Re-Batch, INV-SM-4).
- Telemetrie-Stream-Fan-In via `audit_fanin` (kommutativ, Schritt 9).

### Schritt 7 — Post-Merge-Green-Gate (HYBRID: inline Gating + KOGNITIVES Green-Urteil)

- **Vehikel-A (inline):** `run_post_merge_check(target_tree, build_cmd, test_cmd)` fuehrt Build+Unit
  IM Mothership-cwd NACH dem Merge aus -> Exit-Codes; dann `post_merge_gate(build_ok, test_ok)` ->
  deterministisch `done`/`hold`.
- **Vehikel-B (Team-Member, rot/M2):** das **GREEN-KLARHEITS-URTEIL** ("ist dieser gruene Build
  WIRKLICH korrekt — oder gruen-aber-falsch?") faellt ein Team-Member/der Lead. Das ist die
  BL-330-Zonen-Grenze: das Exit-Code-Gate ist deterministisch, das Urteil ist kognitiv.
- **INV-SM-4:** ein Batch zaehlt erst als `done`, NACHDEM das Gate `done` UND das kognitive Urteil
  "wirklich gruen" sagt. `hold` (oder zweifelhaftes Gruen) -> Batch bleibt OFFEN + Recovery
  (Revert/Re-Batch). **KEIN stilles `done` bei rot** — der billige Regressions-Anker gegen
  semantische Merge-Konflikte (U1/FK-11).

### Schritt 8 — Cleanup Windows-robust + 0-Orphan-Assertion (deterministisch, INLINE, IMMER `finally`)

- **Vehikel:** inline `cleanup_worktree(target_tree, worktree_path, retries=2)` +
  `assert_zero_orphans(target_tree, baseline)`.
- `git worktree remove --force` + `git worktree prune` IMMER in `finally` (auch bei Abbruch /
  rotem Gate). File-Lock-Behandlung (gecrashter Build haelt Handle, B-3-Leichen-Klasse): Retry mit
  Backoff -> als letzte Stufe best-effort `rmtree` + prune.
- **INV-SM-5:** nach jedem Batch MUSS `git worktree list` == Baseline sein (Set-Subtraktion
  post\baseline = leer). Ein erkannter Orphan -> erneuter Cleanup auf den genannten Pfad.

### Schritt 9 — Telemetrie + Gate-B-Auswertung (deterministisch, INLINE)

- **Vehikel:** inline `emit_telemetry(audit_path, **fields)` + `gate_b_status(telemetry_events, min_batches=10)`.
- Emittiere EIN append-only `single_mode_batch_telemetry`-Event mit den 5 Gate-B-Feldern:
  `bootstrap_seconds` / `disk_bytes` / `hook_green_rate` (aus Schritt 4) / `orphan_count` (aus
  Schritt 8) / `merge_result` (aus Schritt 6). **INV-SM-8:** als `audit.jsonl`-Event (OQ-E), NIE als
  quiescenz-pflichtiges Manifest-Feld; Fan-In via `audit_fanin` (kommutativ).
- `gate_b_status(...)` liest die akkumulierten Events und meldet `PASS` (>=10 luecklos gruene
  Batches) oder `PENDING (X/10)`.

---

## INVs (aus Spec #3 — der Betriebspfad MUSS sie halten)

- **INV-SM-1 (Clean-Tree-Scope = ZIEL-Tree):** Schritt 1 prueft NUR den Fan-Out-ZIEL-Tree, NIE die
  `.claude`-Churn des Engine-Repos (OQ-D). Repo-Anwesenheits-Guard zuerst (T9).
- **INV-SM-2 (N bleibt 1):** exakt 1 Worktree pro Welle. `effective_fanout` hart 1; KEIN echter
  Parallel-Spawn. Nebenlaeufigkeit = BL-230 Phase C-E.
- **INV-SM-3 (Vault-Write unveraendert abs/G0):** Vault-State-Writes bleiben absolut unter
  `resolve_vault_root()` + G0-Lock (BL-334). Nur Surface a (Code-Writes) ist worktree-relativ.
- **INV-SM-4 (Post-Merge-Green bevor batch_done):** ein Batch zaehlt erst `done` nach gruenem
  Post-Merge-Gate (Build+Unit auf Mothership) UND kognitivem Green-Urteil. Rot/zweifelhaft -> offen
  + Recovery, kein stilles Weiterlaufen.
- **INV-SM-5 (0-Orphan-Assertion):** nach jedem Batch MUSS `git worktree list` == Baseline sein.
  Cleanup IMMER in `finally`; File-Lock-Reste per Force/Retry (B-3-Leichen-Klasse).
- **INV-SM-6 (write_surface dormant):** `resolve_code_write` bleibt DORMANT bis N>=2 (OQ-B). Bei
  N=1 reicht Worker-cwd = Worktree; das Primitiv wird NICHT pipeline-weit verdrahtet.
- **INV-SM-7 (Base-Ref-Pin reproduzierbar):** Base-SHA bei Welle-Start aus Manifest gelesen/dort
  persistiert; kein impliziter HEAD-Pin pro Worktree; Branch-Name kollisionsfrei (`_B-N`).
- **INV-SM-8 (Telemetrie kommutativ append-only):** alle Gate-B-Felder als `audit.jsonl`-Events
  (OQ-E), NIE als Manifest-Feld; Fan-In via `audit_fanin` (kommutativ).

---

## AK-6 Gate-B als Forward-Verify (dormant-bauend)

Die `>=10-konsekutive-Batches`-Messlatte (`gate_b_status(...)`) ist **dormant-bauend** und ein
**Forward-Verify** ([[feedback_forward_verification_pattern]]): der CODE-Pfad existiert + ist
unit-getestet (synthetische Events), der **echte** >=10-Batch-Nachweis faellt erst bei realem
Single-Mode-Produktions-Betrieb an. `gate_b_status` ist **fail-safe**: zu wenige / nicht-gruene /
uneindeutige Events -> IMMER `PENDING`, NIE faelschlich `PASS`. Gate-B PASS gdw ueber >=10 Batches:
`hook_green_rate==1.0` ∧ `orphan_count==0` ∧ `merge_result` gruen.

---

## Verbote / Abgrenzung

- **N bleibt 1 (INV-SM-2).** KEIN echter Parallel-Spawn, kein Wellen-Scheduling, kein
  Partial-Failure-Handling, keine Truth-Lease — das ist BL-230 Phase C-E.
- **KEINE Vault-Write-Surface-Aenderung (INV-SM-3).** Surface b bleibt G0/BL-334.
- **`write_surface`-Durchsetzung bleibt DORMANT (INV-SM-6).** `resolve_code_write` wird NICHT
  pipeline-weit verdrahtet bis N>=2.
- **KEIN dispatch_implement-Motor im Betriebspfad (OQ-A).** Der altmodische Pfad liest denselben
  Dial-Wert (`parallel_mode`/`N`), spawnt aber NICHT ueber den Motor. Motor bleibt Produktions-OFF
  ([[feedback_motor_erst_nach_stabilisierung]]).
- **Clean-Check NUR auf ZIEL-Tree (INV-SM-1)** — nie Engine-weit (Dauer-Abort-Falle).

---

## Szenario-Verify (statt TDD — M2: dieser Skill ist Markdown, nicht RED-faehig)

> Der Skill ist **markdown_uncoverable** ([[feedback_markdown_engine_bootstrap]]): er hat kein
> testbares Artefakt, das RED werden koennte. Verifikation = **M2 Bootstrap-Direkt + Szenario-Check**
> gegen die getesteten `single_mode_worktree.py`-Funktionen (deren Verhalten ist TDD-bewiesen). KEIN
> erzwungener TDD-Pfad (das waere der 30-Iter-Burn).

| # | Szenario | Erwarteter Pfad | Beleg |
|---|---|---|---|
| **S1** | sauberer Batch | Schritt 1 `proceed` -> 2 pin+name -> 3 bootstrap `ok` -> 4 Build (Team, gruene Hooks) -> 5 commit `committed` -> 6 merge `merged` -> 7 Gate `done` + Green-Urteil "wirklich gruen" -> 8 cleanup `pruned` + 0-Orphan -> 9 Telemetrie emittiert, `merge_result="merged"`, `orphan_count=0`, `hook_green_rate=1.0` | `test_inv_sm4_batch_done_only_after_green_post_merge`, `test_sb4_full_cleanup_telemetry_cycle` |
| **S2** | dirty ZIEL-Tree | Schritt 1 `decision=="abort"` -> HARTES Abort + korrektiver Hint (Anzahl Aenderungen); KEIN Worktree angelegt, KEIN Batch-Lauf | `test_clean_tree_gate_abort_on_dirty` |
| **S3** | Post-Merge rot | Schritt 7 `run_post_merge_check` test_cmd rot -> `post_merge_gate` `hold`; Batch bleibt OFFEN (NICHT done), Recovery (Revert/Re-Batch); Cleanup laeuft trotzdem in `finally` (0-Orphan) | `test_post_merge_gate_hold_when_test_red`, `test_inv_sm4_batch_done_only_after_green_post_merge` (ROT-Fall) |
| **S4** | git-loser ZIEL-Tree (T9) | Schritt 1 `decision=="na"` -> sauberer N/A-Pfad statt Crash/Improvisation; Welle wird nicht gefahren | `test_clean_tree_gate_na_on_git_less_path`, `test_bootstrap_worktree_na_on_git_less_target` |
| **S5** | gehaltenes File-Handle beim Cleanup (B-3) | Schritt 8 Retry -> Force -> best-effort `rmtree` + prune -> 0-Orphan trotzdem erreicht | `test_cleanup_worktree_still_zero_orphan_after_held_handle` |
| **S6** | Gate-B-Auswertung | Schritt 9 `gate_b_status`: <10 oder ein nicht-gruener Batch -> `PENDING (X/10)`; >=10 luecklos gruen -> `PASS` | `test_gate_b_status_pass_on_10_all_green`, `test_gate_b_status_pending_when_one_has_orphan` |

**Szenario-Verify-Ergebnis:** alle 6 Szenarien sind durch die TDD-bewiesenen
`single_mode_worktree.py`-Funktionen abgedeckt (64 Tests gruen). Der Skill orchestriert diese
Funktionen in der dokumentierten Reihenfolge; die kognitiven Schritte (4 Build, 7 Green-Urteil)
bleiben Team-getrieben. Kein Test-Code fuer den Skill selbst (markdown_uncoverable, M2).
