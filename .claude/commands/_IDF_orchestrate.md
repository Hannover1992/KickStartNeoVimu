# /_IDF_orchestrate - Team Lead Intermediate Factory Orchestrator

```yaml
status: active
version: 2.1.0
created: 2026-04-11
updated: 2026-05-24
changelog_2_1_0: "BL-209 Hard-Cut: Phase 2/3.1/3.2 physisch entfernt. IDF ist reine PL-Verwalterin. INV-IDF-SKIP-1+INV-BC-1 RETIRED. 3 IDF-Berater DEPRECATED."
op: IntermediateFactory
phase: Meta
type: orchestration
chain_position: middle
difficulty_scaling: true
team_based: true
bl_142_implementation: true
```

---

## BL-173 Manifest-Routing (NEU 2026-05-18)

**Manifest-Scope-Split aktiv** (siehe BL-173, INV-MANIFEST-SPLIT-1..4):

| State-Block | Heimat | Helper |
|---|---|---|
| IDF_PIPELINE_STATE | `{bl_folder}/_manifest.md` | `manifest_reader.read_bl_block(bl_id, "IDF_PIPELINE_STATE")` |
| BERATER_OUTPUTS_IDF_* | `{bl_folder}/_manifest.md` | `manifest_reader.read_bl_block(bl_id, "BERATER_OUTPUTS_IDF_*")` |
| DF_BATCH_STATE | `{bl_folder}/_manifest.md` | `manifest_reader.read_bl_block(bl_id, "DF_BATCH_STATE")` |

**Pfad-Aufloesung:**
- Factory-State: `manifest_reader.read_factory_block(...)` ODER direkt `{vault_root}/_factory_manifest.md`
- BL-State: `manifest_reader.read_bl_block(bl_id, ...)` ODER direkt `{bl_folder}/_manifest.md`
- Legacy-Fallback aktiv solange `is_split_active() == False` (1-Sprint-Uebergang)

**Migration:** `py -3 .claude/scripts/migrate_manifest_split.py migrate --vault-root="..." --rollback-tag=YYYY-MM-DD`

---

```
+======================================================================+
|  VERTRAG: /_IDF_orchestrate (Thin-Manager v0.4.0 — BL-209 Hard-Cut)  |
+======================================================================+
|  ROLLE: TEAM LEAD (DU). REINER ORCHESTRATOR.                         |
|         Beraters via Skill() rufen, NIE Inline-Logik > 30 LOC.       |
|                                                                      |
|  LIEST (Lead, NUR Zustand — KEINE Berater-Payload):                  |
|    _manifest.md (IDF_PIPELINE_STATE, BL_LIFECYCLE_STATE,             |
|                  exit_code-Marker pro Phase)                         |
|                                                                      |
|  SCHREIBT (Lead, NUR Zustand):                                       |
|    _manifest.md                                                      |
|      IDF_PIPELINE_STATE.idf_status (INIT|...|IDF_DONE|ABORTED)       |
|      BL_LIFECYCLE_STATE.items_routed_ready (Phase 6, INV-LIFECYCLE-1)|
|    active_team (TeamCreate/Reaktivierung, TeamDelete-Gegenstueck)    |
|                                                                      |
|  DATENFLUSS (Patch 2026-05-04, INV-SPAWN):                           |
|    Berater lesen+schreiben ueber IHRE Vault-Vertragsdateien          |
|    (Spec/Model/AK/PL/...). Berater schreiben NIE Payload in Manifest |
|    — nur exit_code-Marker. Lead liest NIE Berater-Payload aus        |
|    Manifest. Datenfluss = Vertraege, Manifest = Zustand.             |
|                                                                      |
|  RUFT (12 Berater via Skill()):                                      |
|    Phase A:  _IDF_berater_loopCheck (NEU BL-199 2026-05-24)          |
|               PL-Snapshot-Vergleich → FULL_LOOP|BATCH_ONLY|F_L_W_R  |
|    Phase 0.5: _IDF_berater_teamSetup (NEU 2026-05-04)                |
|    Phase 1:  _IDF_berater_resumeGuard (MIGR aus SDF)                 |
|    Phase 1:  _IDF_berater_init                                       |
|    [Phase 2/3.1/3.2 ENTFERNT BL-209: specParse/akExtraktion/plAggregation →  |
|               A-Pipeline _A_berater_* sind Single-Source]            |
|    Phase 3.5: _IDF_berater_validator (MIGR aus SDF)                  |
|    Phase 3.6: _IDF_berater_itemContext (MIGR aus SDF)                |
|    Phase 3.7: _IDF_berater_modelSync (NEU 2026-05-04, BL-151)        |
|               REVERSE: PL → Model (Entry-3-Mechanik, BL-198,         |
|               INV-IDF-REVERSE-1). Forward (Spec→PL) wandert zu A,   |
|               Reverse (PL→Model) bleibt IDF.                         |
|    Phase 3.8: _IDF_berater_plBewertung (BL-203)                      |
|               SRS-Refresh + Bottleneck-Filter + K-Score + Intern/Extern|
|    Phase 3.8e: _IDF_berater_bottleneckTrigger (BL-206)               |
|               Baut bottleneck_queue (queue_for_sc + queue_for_wp).   |
|               Max-Loop-Schutz (AK-8, bottleneck_max_loops=3 default).|
|    Phase 4:  _IDF_berater_dependencyAnalyzer (ABSORBIERT SDF)        |
|    Phase 5:  _IDF_berater_clustering                                 |
|    Phase 6:  _IDF_berater_sequencePlanner (ABSORBIERT SDF)           |
|    Phase 7:  _IDF_berater_batchPlan (NEU, wraps batchPlanner)        |
|    Phase 7:  _IDF_berater_batchPlanner (MIGR aus SDF, inner)         |
|    Phase 7.5: _IDF_berater_stagePlanner (NEU 2026-05-09 BL-168)      |
|               stage_*.md Discovery → batch_stages-Map (SRP)          |
|    Phase 7.6: _IDF_berater_metricPlanner (NEU 2026-05-10 BL-172)     |
|               K-SCORE per-AK Aggregation → metric_per_batch (SRP)    |
|    Phase 7.7: _IDF_berater_testSearch (BL-231/232; Reg. BL-342)      |
|               Coverage-Map pro Sub-Batch (Plan-Zeit)                 |
|    Phase 7.8: _IDF_berater_parallelSuitability (NEU BL-342)          |
|               file_index→Konflikt-Inseln→parallel_suitability (SRP)  |
|    Phase 8.0: _IDF_berater_finalSummary (NEU 2026-05-24 BL-204)      |
|               Vektor-Output: 9-Spalten-Tabelle (Mensch) + YAML       |
|               (Maschine). READ-ONLY. INV-MODUS-1-Disclaimer Pflicht. |
|    Phase 8.5: Auto-Chain (LOOSENED 2026-05-17 Refit-V3)              |
|               --from=direct + --no-chain != true + IDF_DONE +        |
|               "SDF" in expected (default "IDF+SDF").                 |
|               Reifegrad-Check ENTFERNT (UNREIF/SC-REIF/REIF alle     |
|               erlaubt) — SDF Phase 1.1 modusEntscheidung waehlt M{N}.|
|               → Skill(_SDF_orchestrate) ohne TeamDelete (5b-Ausnahme)|
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-VAULT-9: WORKING_DIR = resolve_bl_path(BL_ID)                |
|    INV-THIN-1: Orchestrator <= 320 LOC                               |
|    INV-THIN-2: Inline-Logik pro Phase <= 30 LOC                      |
|    INV-THIN-3: Berater-Schreib-Isolation (jeder schreibt nur seinen  |
|                BERATER_OUTPUTS-Slot)                                 |
|    INV-DATA-1:  Datentraeger-Kette via BERATER_OUTPUTS / IDF_PIPELINE_STATE
|    INV-SR-3:    Decomposition NUR in IDF Phase 3 (kein SDF-Spec-Parse)
|    INV-LIFECYCLE-1: Stufe 1 Cleanup vor TeamCreate                   |
|    INV-LIFECYCLE-2: Genau 1 Team idf-{BL_ID} pro Lauf                |
|    INV-LIFECYCLE-3: Modus explizit (normal | recheck | dryRun)       |
|    INV-LIFECYCLE-4: TaskCreate vor Phasen-Ausfuehrung                |
|    INV-LIFECYCLE-5: TeamDelete bei jedem Exit (DONE/ABORT)           |
|    INV-LIFECYCLE-5b (NEU 2026-05-10 BL-173): Ausnahme bei Auto-Chain |
|                    Stufe_6_with_chain — KEIN TeamDelete. Team-       |
|                    Lifecycle laeuft durch SDF weiter (SDF Phase 0.5  |
|                    ist Eigentuemer der Team-Transition). Expliciter  |
|                    IDF-TeamDelete wuerde Race-Conditions schaffen.   |
|                    Greift nur bei --from=direct + auto-chain-Pfad.   |
|    INV-01 (AK-09): Phase 6 schreibt items_routed_ready (BL-075)      |
|    INV-02 (AK-10): Phase 7 Recheck-Guard (Anti-Zirkel)               |
|    INV-03 (AK-08): Clustering + Topologie als GETRENNTE States       |
|    INV-04 (W7):    Kein Agent() im Lead AUSSER Berater-Spawn        |
|                    (siehe INV-SPAWN). Skill() inline NUR fuer        |
|                    triviale Lese-Schreibe-Ops (<10 LOC).             |
|    INV-AO-CALLER (V11/V12, 2026-05-07/2026-05-08):                   |
|                    Skill(_IDF_orchestrate) DIREKT vom Team Lead —    |
|                    kein Hub-Delegate via Agent(general-sonnet,        |
|                    prompt="orchestrate ..."). CLAUDE.md Z6 +         |
|                    _A_orchestrate INVARIANTEN. Beweis: DCSRE-2014.   |
|    INV-IDF-REVERSE-1 (BL-198 AK-4): IDF Phase 3.7 modelSync ist      |
|                    AUSSCHLIESSLICH Reverse-Sync (PL → Model). Darf   |
|                    NICHT als Forward-Erzeuger verwendet werden.       |
|                    Verwendung: Entry 3 (/_parking-lot, BL-201)       |
|                    triggert Reverse-Learning. Phase 3.7 BLEIBT in    |
|                    IDF auch nach BL-197/198 Pipeline-Schnitt. Ref:   |
|                    BL-198 AK-4, architecture-vision-2026-05-22.md    |
|    INV-MATURE (NEU 2026-05-04): Wenn alle AKs.status=DONE und        |
|                    NOT --refresh-aks, SKIP Phase 3.1 (akExtraktion). |
|                    --pl-only zwingt zusaetzlich Skip Phase 1+2+3.1   |
|                    (Mature-Mode fuer reife Projekte).                |
|    INV-SPAWN (NEU 2026-05-04): Jeder Berater laeuft im eigenen       |
|                    kurzlebigen Worker (Single-Use-of-Walk).          |
|                    Pattern: Lead -> Agent(general-{tier}) -> Worker  |
|                    fuehrt Skill(_IDF_berater_X) aus -> schreibt      |
|                    BERATER_OUTPUTS.{phase} in _manifest.md -> stirbt.|
|                    Lead liest Manifest, weiter zur naechsten Phase.  |
|                    Datenfluss: AUSSCHLIESSLICH via _manifest.md.     |
|    INV-05:         BL-075 Reifungs-Loop intakt (durch INV-01)        |
|    INV-06:         BL-055 Treue (Phase 3 1:1 Port via Berater)       |
|    INV-07:         BL-069 absorbed_into BL-076                       |
|    INV-IDF-LOOP-1 (BL-199): Phase A laeuft VOR resumeGuard (Phase 0) |
|    INV-IDF-LOOP-2 (BL-199): Snapshot NUR von loopCheck geschrieben   |
|    INV-IDF-LOOP-3 (BL-199): BATCH_ONLY triggert KEINE Phase 4-7.6   |
|    INV-IDF-LOOP-4 (BL-199): parking_lot_modified=true → F_L_W_REVERSE|
|    INV-IDF-LOOP-5 (BL-199): Hash=SHA256(sorted(id+':'+mtime) per PL) |
|    INV-IDF-SKIP-1 (BL-198 AK-6): RETIRED (BL-209 2026-05-24).        |
|                    Phase 2/3.1/3.2 existieren nicht mehr in IDF.     |
|                    A-Pipeline _A_berater_specParse/akExtraktion/      |
|                    plAggregation sind Single-Source (immer aktiv).   |
|                    IDF startet immer bei Phase 3.5 validator.        |
|    INV-BC-1 (BL-198 AK-7): RETIRED (BL-209 2026-05-24).              |
|                    Backward-Compat fuer alte BLs ohne A-Pipeline     |
|                    entfaellt. Hard-Cut: kein Forward-Fallback mehr.  |
|                    Neue BLs MUESSEN A-Pipeline Phase 5a/5b/5c laufen.|
+======================================================================+
```

---

## STATE-MACHINE

```
INIT -> AK_PER_PL -> DEP_MATRIX -> CLUSTER -> SEQUENCE
     -> BATCH_PLAN -> STAGE_PLAN -> METRIC_PLAN -> TEST_SEARCH -> PARALLEL_SUITABILITY -> FINAL_SUMMARY -> IDF_DONE
                                                       \-> ABORTED (any phase)
```
# BL-209 Hard-Cut: Phase 2 (SPEC_PARSE) + 3.1 (akExtraktion) + 3.2 (plAggregation) ENTFERNT.
# A-Pipeline (Phase 5a/5b/5c) ist Single-Source fuer PL-Items.

| Phase | Status-Wert | Berater-Skill | Tier |
|-------|-------------|---------------|------|
| 1 | `INIT` | `_IDF_berater_init` | floor (sonnet) |
| ~~2~~ | ~~`SPEC_PARSE`~~ | ~~`_IDF_berater_specParse`~~ DEPRECATED BL-209 | — |
| ~~3.1~~ | ~~`AK_PER_PL`~~ | ~~`_IDF_berater_akExtraktion`~~ DEPRECATED BL-209 | — |
| ~~3.2~~ | ~~`AK_PER_PL`~~ | ~~`_IDF_berater_plAggregation`~~ DEPRECATED BL-209 | — |
| 3.5 | `AK_PER_PL` | `_IDF_berater_validator` | middle (sonnet) |
| 3.6 | `AK_PER_PL` | `_IDF_berater_itemContext` | middle (sonnet) — haiku verboten User-Direktive 2026-05-17 |
| 3.8 | `AK_PER_PL` | `_IDF_berater_plBewertung` | middle (sonnet) — NEU BL-203 |
| 3.8e | `AK_PER_PL` | `_IDF_berater_bottleneckTrigger` | middle (sonnet) — NEU BL-206 |
| 4 | `DEP_MATRIX` | `_IDF_berater_dependencyAnalyzer` | middle (sonnet) |
| 5 | `CLUSTER` | `_IDF_berater_clustering` | middle (sonnet) |
| 6 | `SEQUENCE` | `_IDF_berater_sequencePlanner` | middle (sonnet) |
| 7 | `BATCH_PLAN` | `_IDF_berater_batchPlan` | ceiling (opus, capped) |
| 7.5 | `STAGE_PLAN` | `_IDF_berater_stagePlanner` | middle (sonnet) |
| 7.6 | `METRIC_PLAN` | `_IDF_berater_metricPlanner` | middle (sonnet) |
| 7.7 | `TEST_SEARCH` | `_IDF_berater_testSearch` | middle (sonnet) — BL-231/232 (Reg. BL-342) |
| 7.8 | `PARALLEL_SUITABILITY` | `_IDF_berater_parallelSuitability` | middle (sonnet) — NEU BL-342 |
| 8.0 | `FINAL_SUMMARY` | `_IDF_berater_finalSummary` | middle (sonnet) — NEU BL-204 |
| END | `IDF_DONE` / `ABORTED` | — | — |

> **INV-TIER-CAP (BL-129 Intelligenz-Budget-Cap):** Tier-Spalte ist die
> **Wunsch-Obergrenze** des Beraters. Der tatsaechliche Worker-Spawn MUSS via
> `min(berater_wunsch, _session_params.ceiling)` gecappt werden. Bsp: Phase 2/7
> wuenschen `opus`, bei `ceiling=sonnet` wird `general-sonnet` gespawnt — NIE
> `general-opus`. Verstoss = Intelligenz-Budget-Leak (CaseStudy BL-154
> 2026-05-01: Phase 2 + 7 wurden faelschlich mit general-opus gespawnt
> obwohl session.ceiling=sonnet).

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

---

## PARAMETER

| Name | Typ | Default | Beschreibung |
|------|-----|---------|--------------|
| `BL_ID` | string | — | Pflicht. BL-Item-ID (z.B. `BL-042`). |
| `BL_SLUG` | string | — | Optional. Vault-Ordner-Slug (Auto-Resolve via init). |
| `--mode` | enum | `normal` | `normal | recheck | dryRun | recluster` |
| `--from` | enum | `direct` | `direct | bdf_plan | sdf_finish | sdf_drift | idf_plan | orphan_scan` (Recheck-Guard). |
| `--pl-only` | bool | `false` | **NEU 2026-05-04 (Mature-Mode):** Skip Phase 1+2+3.1, springe direkt zu Phase 3.2 plAggregation. Use-Case: laufendes Projekt mit fertigen AKs, parking-lot.md hat neue Findings die einsortiert werden muessen — keine AK-Implikationen neu ableiten. |
| `--orphan-only` | bool | `false` | **NEU 2026-05-12 (BL-NEW-60):** Implies `--pl-only`. Delta-Update-Mode: Phase 3.2 plAggregation liest NUR neue PL-Items vs `BERATER_OUTPUTS.plAggregation.pl_items` (Diff). Phase 4-7 incremental: existing DONE-Batches preservieren (Sticky-Batch-IDs), nur Orphans clustern + neuen `batch_PL{N}` einfuegen. Use-Case: nach jedem SDF-Batch-Ende durch `_SDF_berater_orphan_scan` getriggert wenn HIGH/CRITICAL Orphans detected. |
| `--sticky-ids` | bool | `false` | **NEU 2026-05-12 (BL-NEW-60):** Erzwingt Idempotency in Phase 5 clustering + Phase 7 batchPlanner: existierende batch_keys in `completed_sub_batches` und `partial_sub_batches` bleiben **unangetastet**. Re-Cluster darf NUR neue Batches anhaengen, nie alte umsortieren. Implizit bei `--orphan-only`. |
| `--refresh-aks` | bool | `false` | **NEU:** Phase 3.1 trotz Cache neu rechnen (Default: Cache-First wenn AK.status=DONE). |
| `--no-chain` | bool | `false` | **LOOSENED 2026-05-17 Refit-V3:** Auto-Chain zu SDF unterdruecken. Default-ON (chain) bei `--from=direct` + `--no-chain != true` + `IDF_DONE` + `"SDF" in expected_pipeline (default IDF+SDF)`. **BL-298 2026-06-10:** Default-ON gilt JETZT AUCH bei `--from=orphan_scan` (Phase 8.5a, Auto-Build-Bounded) — `<3` Orphan-Iter RE-BATCH-Chain, `>=3` HiL-Alert statt stillem no_chain. Reifegrad-Check ENTFERNT — UNREIF/SC-REIF/REIF alle erlaubt. SDF Phase 1.1 modusEntscheidung waehlt M{N}. Setzen wenn Lead bei IDF_DONE ohne SDF-Glove-Change exit'en soll. |
| ~~`pl_pre_filled`~~ | — | RETIRED | **RETIRED BL-209:** Phase 2/3.1/3.2 existieren nicht mehr. IDF startet immer bei Phase 3.5. INV-IDF-SKIP-1 + INV-BC-1 retired. |

**Aufruf-Form:**
```
Skill(skill="_IDF_orchestrate", args="{BL_ID} [BL_SLUG] [--mode=...] [--from=...] [--pl-only] [--refresh-aks]")
```

**Modus-Matrix (Use-Case → Modus):**

| Projekt-Status | Empfohlener Aufruf |
|---|---|
| Frisches BL-Item, A-Pipeline DONE | `BL-NNN slug` (default normal) |
| Reifes Projekt, AKs alle DONE, neue PL-Items | `BL-NNN slug --pl-only --from=sdf_finish` |
| AK-Iteration neu beginnen (Spec geandert) | `BL-NNN slug --refresh-aks` |
| Recheck nach BDF (Anti-Zirkel) | `BL-NNN slug --mode=recheck --from=bdf_plan` |
| Architektur-Validierung ohne Materialisierung | `BL-NNN slug --mode=dryRun` |
| **Orphan-Scan-induzierter Re-Cluster (BL-NEW-60)** | `BL-NNN slug --mode=recluster --orphan-only --sticky-ids --from=orphan_scan` |
| K-Drift > 30% (SOFT-REPRIO) | `BL-NNN slug --mode=recluster --from=sdf_drift` |

---

## 6-STUFEN-LIFECYCLE (universal, BL-142)

| Stufe | Name | Zweck | Invariante |
|-------|------|-------|------------|
| 1 | **Cleanup** | altes `active_team` (falls vorhanden) shutdown + TeamDelete | INV-LIFECYCLE-1 |
| 2 | **TeamCreate** | neues Team `idf-{BL_ID}` registrieren | INV-LIFECYCLE-2 |
| 3 | **Modus-Erkennung** | `idf_mode` (normal/recheck/dryRun) + `idf_from` parsen | INV-LIFECYCLE-3 |
| 4 | **Tasks vorab** | TaskCreate fuer Phase 1..8 mit Dependency-Graph | INV-LIFECYCLE-4 |
| 5 | **Phasen-Ausfuehrung** | Skill()-Calls Phase 1..8 (Pseudocode unten) | INV-THIN-1..3 |
| 6 | **TeamDelete** | `idf-{BL_ID}` abbauen, `active_team=null` setzen | INV-LIFECYCLE-5 |

---

## WORKER-SPAWN-PATTERN (INV-PM-5, INV-SPAWN)

**WICHTIG:** Jeder `Skill(_IDF_berater_X, args=Y)` im Pseudocode unten wird vom Lead
NICHT inline ausgefuehrt. Stattdessen Single-Use-of-Walk-Spawn:

**INV-MODUS-Reminder:** Worker darf modus-Feld NICHT setzen ausser via _SDF_berater_modusEntscheidung (BL-165 INV-MODUS-1).

## SPAWN-CONVENTION (Patch 2026-05-04, INV-SPAWN)

**WICHTIG:** Jeder `Skill(_IDF_berater_X, args=Y)` im Pseudocode unten wird vom Lead
NICHT inline ausgefuehrt. Stattdessen Single-Use-of-Walk-Spawn:

```
SPAWN-HELPER (logisches Macro):

spawn_berater(skill_name, tier_wunsch, phase_name, args):
  # Tier-Cap (BL-129 INV-TIER-CAP)
  worker_tier = min_tier(tier_wunsch, _session_params.ceiling)
  # PFLICHT: Lead resolved Pfade VOR Spawn (NEU 2026-05-04)
  # WICHTIGE FESTE PFADE (INV-PATH-EXPLICIT, NEU 2026-05-04):
  #   .claude/config/vault-routing.json   ← NICHT .claude/vault-routing.json!
  #   .claude/analysis/_manifest.md       ← Lokal-Manifest (Hook liest hier)
  #   .claude/config/layers.yaml          ← Layer-Config
  paths = resolve_paths_via_vault_routing(BL_ID)
  # Implementation:
  #   routing = Read(".claude/config/vault-routing.json")  # FESTER PFAD!
  #   for rule in routing.detection.rules:
  #     if pattern_matches(cwd, rule.pattern):
  #       vault_root = routing.vaults[rule.vault].windows_path
  #       bl_folder  = vault_root + "/" + rule.backlog.subfolder + "/" + folder_name(BL_ID)
  #       break
  #   pl_files = list(bl_folder + "/6_PL/*.md")
  #   manifest_path = ".claude/analysis/_manifest.md"
  # paths = {vault_root, bl_folder, manifest_path, parking_lot_files[]}
  # 1 Worker spawn, 1 Job, dann stirbt er
  Agent(
    subagent_type   = f"general-{worker_tier}",   # general-sonnet|opus (haiku VERBOTEN User-Direktive 2026-05-17)
    team_name       = f"idf-{BL_ID}",             # einreihen ins IDF-Team
    description     = f"IDF {phase_name} berater={skill_name}",
    prompt          = f"""
                       Du bist ein einmaliger Berater-Worker fuer {skill_name}.
                       Auftrag: Skill({skill_name}, args='{args}').

                       PFAD-KONTEXT (vom Lead resolved via vault-routing.json):
                         vault_root  = {paths.vault_root}
                         bl_folder   = {paths.bl_folder}
                         manifest    = {paths.manifest_path}
                         pl_dir      = {paths.bl_folder}/6_PL/
                         pl_files    = {paths.parking_lot_files}  # ALLE *.md im 6_PL!

                       PFLICHT-LOGGING beim Start (im Terminal sichtbar):
                         "[{phase_name}] vault_root={paths.vault_root}"
                         "[{phase_name}] bl_folder={paths.bl_folder}"
                         "[{phase_name}] reading: ..." (pro File)
                         "[{phase_name}] writing: ..." (pro File)

                       Datenfluss: gemaess DEINEM Vertrag (LIEST/SCHREIBT-Sektion).
                                   Du schreibst in Vault-Vertragsdateien
                                   (Spec/Model/AK/PL), NICHT in den Manifest.
                       Zustand:    Wenn dein Vertrag es vorsieht, schreibe
                                   {phase_name}.exit_code in Manifest — NUR
                                   Status, keine Berater-Payload.

                       Dann: STERBE (return). Keine Folge-Calls.
                       """
  )
  # Lead liest danach: Zustand aus Manifest, Daten aus Vault:
  exit_code = Read(_manifest.md).IDF_PIPELINE_STATE[phase_name].exit_code
  RETURN exit_code

DATENFLUSS-PRINZIP (User-Direktive 2026-05-04):
  Datenfluss laeuft AUSSCHLIESSLICH ueber die Berater-VERTRAEGE (Skill-Dateien).
  Jeder Berater hat in seinem Vertrag definiert, aus welchen Dateien er liest
  und in welche er schreibt — das sind Vault-Dateien (Spec/Model/AK/PL/...).
  Der Manifest dient AUSSCHLIESSLICH dem ZUSTAND ("wo sind wir gerade") und
  liegt im Vault-BL-Folder, nicht lokal in .claude/analysis/.

LESEN-SCHREIBEN-VERTRAG:
  - Worker liest:   Vault-Vertragsdateien gemaess Skill (Spec, Model, vorherige
                    Berater-Outputs als Vault-Dateien)
  - Worker schreibt: Vault-Vertragsdateien gemaess Skill (eigener Output)
                     + ausnahmsweise Status-Marker in Manifest (exit_code)
  - Lead liest:    _manifest.md (NUR Zustand: idf_status, active_team,
                                  BL_LIFECYCLE_STATE, exit_code-Marker)
  - Lead schreibt: _manifest.md.IDF_PIPELINE_STATE.idf_status,
                   active_team, BL_LIFECYCLE_STATE.items_routed_ready
  - Lead delegiert ALLES Domain-Logische an Worker (kein Inline-Reasoning > 30 LOC)
  - Lead liest NIE Berater-Payload aus Manifest — Payload steht im Vault.

LIES PSEUDOCODE UNTEN ALSO SO:
  "Skill(_IDF_berater_X, args=Y)"  ===  spawn_berater("_IDF_berater_X", tier_X, phase_X, Y)
  Tier kommt aus Tier-Tabelle (Phase-Liste oben).
  "Read(_manifest.md).BERATER_OUTPUTS.X" im aktuellen Pseudocode ist HISTORISCH
  und sollte zu "Read({Vault-BL-Folder}/X.md)" migriert werden (FOLGE-TASK).

PARALLELITAET (Phase 3.1):
  AKTUELL sequenziell: 1 Worker pro AK, einer nach dem anderen (zeitkostspielig
  aber datenfluss-sicher). PARALLELISIERUNG ist BL-NEW (siehe FOLGE-TASKS):
  Mehrere Agent()-Calls in einem einzigen Lead-Tool-Call-Block werden vom
  Runtime parallel gespawnt — bis dahin: sequentiell.

MANIFEST-LOKATION:
  AKTUELL: .claude/analysis/_manifest.md (lokal — INKONSISTENT mit BL-151)
  ZIEL:    {Vault}/Backlog/BL-{ID}-{slug}/_manifest.md (im Vault-BL-Folder)
  Migration ist Teil von BL-151 VaultDrivenDevelopment. Bis dahin liest der
  Hook .claude/analysis/_manifest.md.
```

---

## ORCHESTRATOR-PSEUDOCODE

```
ENTRY:
  args = parse_args($ARGUMENTS)
  Logge: "[IDF] ENTRY bl_id={args.BL_ID} mode={args.mode} from={args.from}"

# ─── Stufe 1: Cleanup (INV-LIFECYCLE-1) ─────────────────────────────
active_team = Read(_manifest.md).active_team
IF active_team != null AND active_team != "idf-{args.BL_ID}":
  Logge: "[IDF Stufe 1] Cleanup altes Team: {active_team}"
  Sende shutdown_request, warte ACK
  TeamDelete team_id={active_team}
  Set _manifest.md.active_team = null
# BL-349 AK-2 / INV-TEAM-GC-2 (Team-Transition-Recovery, reaktiv + concurrency-safe): Manifest.active_team
# ist NICHT die einzige Wahrheit (Manifest<->Session-Drift). Scheitert die Stufe-2-TeamCreate (im teamSetup-
# Berater) mit "Already leading team X" -> X gehoert DIESEM Lead-Kontext (nie ein Peer-Team) ->
# `py .claude/scripts/team_gc.py strip X` -> TeamDelete X -> TeamCreate erneut. (Home: team_gc.py-Docstring.)

# ─── Stufe 2: TeamSetup-Berater (NEU 2026-05-04, BL-151) ────────────
# REPLACES inline TeamCreate. Berater macht:
#   1. Vault-Pfad-Resolution (vault-routing.json + ticket_prefix_map)
#   2. TeamCreate ODER Reaktivierung (Resume-Aware)
#   3. BERATER_OUTPUTS.teamSetup (paths, pl_files, ceiling, floor)
#   4. PFLICHT-Logging im Terminal (vault_root, bl_folder, manifest, pl_files)
# Phase 0 ResumeGuard nutzt danach BERATER_OUTPUTS.teamSetup.bl_folder etc.
exit = Skill(_IDF_berater_teamSetup, args=args.BL_ID)
IF exit == 2: → ABORT("teamSetup failed (siehe BERATER_OUTPUTS.teamSetup)")
# active_team + paths jetzt im Manifest gesetzt, weiter mit Stufe 3
state = Read(_manifest.md).BERATER_OUTPUTS.teamSetup
Logge: "[IDF Stufe 2] team_action={state.team_action} bl_folder={state.bl_folder}"

# ─── Stufe 3: Modus-Erkennung (INV-LIFECYCLE-3) ─────────────────────
# args.mode in {normal, recheck, dryRun}, args.from in {direct, bdf_plan, ...}
Logge: "[IDF Stufe 3] mode={args.mode} from={args.from}"

# ─── Stufe 4: Tasks vorab (INV-LIFECYCLE-4) ─────────────────────────
TaskCreate name="phase-A-loopCheck"       depends_on=[]              # NEU BL-199
TaskCreate name="phase-1-init"            depends_on=["phase-A-loopCheck"]
# Phase 2/3.1/3.2 ENTFERNT (BL-209 Hard-Cut): specParse/akExtraktion/plAggregation → A-Pipeline
TaskCreate name="phase-3-5-validator"     depends_on=["phase-1-init"]  # direkt nach init (BL-209)
TaskCreate name="phase-3-6-itemContext"   depends_on=["phase-3-5-validator"]
TaskCreate name="phase-3-7-modelSync"     depends_on=["phase-3-6-itemContext"]
TaskCreate name="phase-3-8-plBewertung"   depends_on=["phase-3-7-modelSync"]      # NEU BL-203
TaskCreate name="phase-3-8e-bottleneck"   depends_on=["phase-3-8-plBewertung"]    # NEU BL-206
TaskCreate name="phase-4-dependency"      depends_on=["phase-3-8e-bottleneck"]
TaskCreate name="phase-5-clustering"      depends_on=["phase-4-dependency"]
TaskCreate name="phase-6-batchSequence"   depends_on=["phase-5-clustering"]
TaskCreate name="phase-7-batchPlan"       depends_on=["phase-6-batchSequence"]
TaskCreate name="phase-7-5-stagePlan"       depends_on=["phase-7-batchPlan"]   # NEU BL-168
TaskCreate name="phase-7-6-metricPlan"     depends_on=["phase-7-5-stagePlan"]  # NEU BL-172
TaskCreate name="phase-7-7-testSearch"     depends_on=["phase-7-6-metricPlan"]  # BL-231/232 (Reg. BL-342)
TaskCreate name="phase-7-8-parallelSuit"   depends_on=["phase-7-7-testSearch"]  # NEU BL-342
TaskCreate name="phase-8-0-finalSummary"   depends_on=["phase-7-8-parallelSuit"] # NEU BL-204 (rewired BL-342)
TaskCreate name="phase-8-idfDone"          depends_on=["phase-8-0-finalSummary"]

# ─── Stufe 5: Phasen-Ausfuehrung ────────────────────────────────────
# ─── Phase A: Loop-Check (NEU BL-199, INV-IDF-LOOP-1) ──────────────
# MUSS VOR resumeGuard laufen. Vergleicht PL-Hash mit Snapshot.
# Ergebnis: FULL_LOOP | BATCH_ONLY | FULL_LOOP_WITH_REVERSE
exit = Skill(_IDF_berater_loopCheck, args=args.BL_ID)
IF exit == 2: → ABORT("loopCheck failed")
loop_decision = Read({bl_folder}/_manifest.md).BERATER_OUTPUTS.loopCheck
Logge: "[IDF Phase A] decision={loop_decision.decision} naechster_batch={loop_decision.naechster_batch}"
TaskUpdate name="phase-A-loopCheck" status=DONE

IF loop_decision.decision == "BATCH_ONLY":
  # PL unveraendert — kein vollstaendiger IDF-Lauf
  IF loop_decision.naechster_batch == null:
    # Alle Sub-Batches abgeschlossen → TERMINATE
    Logge: "[IDF Phase A] BATCH_ONLY + alle Batches DONE → TERMINATE"
    Set IDF_PIPELINE_STATE.idf_status = "IDF_DONE"
    GOTO Stufe 6 (TeamDelete)  # Phase 8.5 Auto-Chain schickt TERMINATE an SDF
  ELSE:
    # Naechster offener Sub-Batch → direkt Auto-Chain zu SDF
    Logge: "[IDF Phase A] BATCH_ONLY → naechster Sub-Batch: {loop_decision.naechster_batch}"
    Set IDF_PIPELINE_STATE.idf_status = "IDF_DONE"
    Set IDF_PIPELINE_STATE.batch_only_next = loop_decision.naechster_batch
    GOTO Stufe 6 (TeamDelete)  # Phase 8.5 Auto-Chain weist SDF auf batch_only_next hin

ELIF loop_decision.decision == "FULL_LOOP_WITH_REVERSE":
  # parking-lot-Eingriff: volle Schleife + Phase 3.7 REVERSE triggern
  args.reverse_sync_forced = true
  Logge: "[IDF Phase A] FULL_LOOP_WITH_REVERSE — Phase 3.7 im REVERSE-Modus"
  # Fallthrough → normaler IDF-Lauf unten

ELSE:
  # FULL_LOOP: Erst-Eintritt oder neue PL-Items → normaler IDF-Lauf
  args.reverse_sync_forced = false
  Logge: "[IDF Phase A] FULL_LOOP — volle IDF-Schleife"

# ─── Phase 0: Resume-Detection (resumeGuard, MIGR aus SDF) ──────────
Skill(_IDF_berater_resumeGuard, args=args.BL_ID)
state = Read(_manifest.md).IDF_PIPELINE_STATE
IF state.idf_status == "IDF_DONE":
  Logge: "[IDF RESUME] Already DONE — No-Op (NFR-7 Idempotenz)"
  GOTO Stufe 6
IF state.idf_status == "ABORTED":
  Logge: "[IDF RESUME] ABORTED — manuelles Reset noetig"
  GOTO Stufe 6
resume_phase = resolve_resume_phase(state.idf_status)   # null = fresh start

# ─── BL-206 AK-7: SC/WP Re-Entry-Detection (NEU 2026-05-24) ────────────────
# Wenn IDF via --from=sdf_finish mit SC/WP Re-Entry-Signal aufgerufen wird,
# wird NUR fuer betroffene PLs SRS-Refresh gemacht (INV-LOOP-2: nicht BL-global).
# Loop-Counter-Increment und Max-Loop-Check in _IDF_berater_bottleneckTrigger (Phase 3.8e).
#
# Re-Entry-Erkennung:
#   SC-Return:  sc_handover.md.idf_reentry_signal.triggered == true
#   WP-Return:  DF_BATCH_STATE.WP_PIPELINE_STATE.idf_reentry_signal.triggered == true
#   (BEIDE gelten als Re-Entry — nicht AND, sondern OR)
#
# Im Re-Entry-Pfad:
#   - Phase 2, 3.1, 3.2 SKIP (analog pl_only_from_a)
#   - Phase 3.5, 3.6 SKIP (PL-Items existieren)
#   - Phase 3.7 modelSync: NUR betroffene PLs (affected_pl_items)
#   - Phase 3.8 plBewertung: NUR affected_pl_items (idempotenz-gate RESET fuer diese PLs)
#   - Phase 3.8e bottleneckTrigger: Loop-Counter-Increment + neue Queue
#   - Phase 4+ normaler Lauf (mit aktualisierten Daten)

sc_reentry_signal = null
wp_reentry_signal = null

IF args.from == "sdf_finish":
  # SC Re-Entry pruefen
  # Iter 2 R3 Fix 2026-05-24: BL-210 M10 schreibt seit dem Fix zu separater
  # idf_reentry_signal.md Datei (Single-Writer-Disziplin _SC_implement fuer sc_handover.md).
  # IDF muss BEIDE Quellen lesen — sc_handover.md (legacy) UND idf_reentry_signal.md (neu).
  sc_handover = Read({bl_folder}/Crumbs/sc_handover.md ?? {bl_folder}/_sc_handover.md)
  reentry_signal_file = Read({bl_folder}/SC/idf_reentry_signal.md ?? null)

  # Quelle-A: sc_handover.md (legacy)
  IF sc_handover.idf_reentry_signal.triggered == true:
    sc_reentry_signal = sc_handover.idf_reentry_signal
    Logge: f"[BL-206 AK-7] SC Re-Entry-Signal erkannt (legacy sc_handover.md): {sc_reentry_signal.affected_pl_items}"

  # Quelle-B: idf_reentry_signal.md (neu seit BL-210 M10)
  ELIF reentry_signal_file != null AND reentry_signal_file.triggered == true:
    sc_reentry_signal = reentry_signal_file
    Logge: f"[BL-206 AK-7 + Iter2 R3] SC Re-Entry-Signal erkannt (Single-Writer-File idf_reentry_signal.md): {sc_reentry_signal.affected_pl_items}"

  # WP Re-Entry pruefen
  wp_state = Read({bl_folder}/_manifest.md).WP_PIPELINE_STATE
  IF wp_state.idf_reentry_signal.triggered == true:
    wp_reentry_signal = wp_state.idf_reentry_signal
    Logge: f"[BL-206 AK-7] WP Re-Entry-Signal erkannt: {wp_reentry_signal.affected_pl_items}"

# Kombiniertes Re-Entry-Signal
active_reentry = sc_reentry_signal ?? wp_reentry_signal  # SC hat Vorrang wenn beide gesetzt

IF active_reentry != null:
  affected_pl_items = active_reentry.affected_pl_items ?? []
  Logge: f"[BL-206 AK-7] BOTTLENECK-REENTRY: affected={affected_pl_items}, srs_refresh={active_reentry.srs_refresh_needed}"

  # Re-Entry-Modus: wie --orphan-only aber nur fuer affected_pl_items
  args.pl_only_from_a = true                    # Skippe Phase 2/3.1/3.2
  args.bottleneck_reentry = true                 # Marker fuer Phase 3.7/3.8
  args.bottleneck_reentry_items = affected_pl_items  # NUR diese PLs refreshen
  args.bottleneck_reentry_signal = active_reentry

  # Idempotenz-Gates von plBewertung RESET fuer affected_pl_items
  # (sonst wuerde Phase 3.8 SKIP wegen plBewertung_done=true)
  Write({bl_folder}/_manifest.md: DF_BATCH_STATE.plBewertung_done = false)
  Write({bl_folder}/_manifest.md: DF_BATCH_STATE.bottleneckTrigger_done = false)
  Logge: "[BL-206 AK-7] Idempotenz-Gates zurueckgesetzt fuer Re-Entry-Run"
ELSE:
  Logge: "[BL-206 AK-7] Kein SC/WP Re-Entry-Signal — normaler IDF-Lauf"
# ─── Ende BL-206 AK-7 ──────────────────────────────────────────────────────

# ─── BL-088 DRY-RUN-Modus ───────────────────────────────────────────
IF args.mode == "dryRun":
  Skill(_IDF_berater_init, args=args.BL_ID)
  write_dry_run_report(args, ".claude/output/IDF_DryRun_{BL_ID}_{DATE}.md")
  Set IDF_PIPELINE_STATE.idf_status = "IDF_DONE"
  Set IDF_PIPELINE_STATE.idf_mode   = "dryRun"
  GOTO Stufe 6

# ─── Phase 0.9: PL-Pre-Filled-Check (SIMPLIFIED BL-209 Hard-Cut) ───────
# Phase 2/3.1/3.2 (specParse/akExtraktion/plAggregation) existieren NICHT mehr in IDF.
# A-Pipeline _A_berater_* sind Single-Source. IDF startet IMMER bei Phase 3.5 validator.
# INV-IDF-SKIP-1 + INV-BC-1 RETIRED (BL-209 2026-05-24).
Logge: "[IDF Phase 0.9] BL-209 Hard-Cut: Phase 2/3.1/3.2 entfernt — IDF startet direkt bei Phase 3.5"
args.pl_only_from_a = true  # immer — kein Forward-Code mehr in IDF

# ─── Phase 1: INIT ──────────────────────────────────────────────────
# NEU 2026-05-04: --pl-only skipt Phase 1 (Vault-Folder existiert bereits)
IF resume_phase IN [null, "INIT"] AND NOT args.pl_only:
  exit = Skill(_IDF_berater_init, args=args.BL_ID)
  IF exit == 2: → ABORT("init failed")
  Set IDF_PIPELINE_STATE.idf_status = "SPEC_PARSE"
  TaskUpdate name="phase-1-init" status=DONE
ELSE IF args.pl_only:
  Logge: "[IDF Phase 1] SKIPPED (--pl-only: Mature-Mode, Vault-Folder vorhanden)"
  TaskUpdate name="phase-1-init" status=SKIPPED reason="pl-only-mature-mode"

# Phase 2 (specParse) ENTFERNT BL-209 Hard-Cut.
# A-Pipeline _A_berater_specParse (Phase 5a) ist Single-Source.
# IDF startet nach Phase 1 (init) direkt bei Phase 3.5 (validator).

# ═══ IDF-EXPRESS-VORAB-GATE (TIER-1, NEU 2026-06-18 BL-403 batch_2/AK-10) ═══
# [Doku-Kommentar: Two-Tier-Reconciliation AK-2<->AK-10. TIER-1 nutzt nur billige
#  Pre-3.5-Signale (Frontmatter/Caller) -> provisorischer Skip der teuren Pre-7.7-Berater
#  (3.5 validator/3.6 itemContext/3.8 plBewertung/3.8e bottleneckTrigger/7 batchPlan/
#  7.5 stagePlanner/7.6 metricPlanner). KEEP 3.7 modelSync + 7.7 testSearch laufen IMMER REAL
#  (sie liefern die Bestaetigungs-Daten). TIER-2 (POST-7.7) bestaetigt -> EXPRESS, oder ABORT
#  bei Mismatch. default-OFF: bei idf_express_lane=false bleibt express_provisional=false ->
#  ALLE Berater spawnen normal (NULL Verhaltensaenderung, AK-8). Quelle: W15-Reconciliation,
#  C3-modusEntscheidung batch_2 (reasoning-resolvable, kein SC).]
#
# ── TIER-1 vs TIER-2 (warum zwei Punkte): ───────────────────────────────────────────────────────
# Der Chicken-Egg (W15/BURDEN-2): c5 (covered) + c6 (harvest leer) sind erst POST-7.7/3.7 bekannt,
# ABER der teure Skip muss VOR Phase 3.5 entschieden werden (sonst ist der Vorwaerts-Pass an den
# Beratern schon vorbei). Aufloesung: TIER-1 entscheidet PROVISORISCH aus billigen Vorab-Signalen
# (vc1-vc4, ohne teure Berater), TIER-2 (POST-7.7, Z~825) BESTAETIGT mit den ECHTEN KEEP-Daten
# (c5+c6) — oder ABORTet fail-loud bei Mismatch (keine stille Korruption, da die Pre-7.7-Berater
# dann bereits provisorisch uebersprungen wurden). AK-2 bleibt gewahrt: die VERBINDLICHE
# Express-Bestaetigung passiert POST-7.7 via KEEP-Daten — TIER-1 ist nur die provisorische Vorab-Auswahl.
#
# ── AK-12 SPAWN-FLOOR sonnet (BL-403, feedback_haiku_verboten): ─────────────────────────────────
# KEEP-Berater im Express-Pfad (modelSync 3.7 + testSearch 7.7) laufen mit Spawn-Floor sonnet —
# NIEMALS haiku. Inline-geschriebene Skip-Berater-Vertraege brauchen keinen Worker (Orchestrator-
# inline schreibt direkt). Der Express-Pfad fuehrt KEINEN neuen haiku-Spawn ein; die vorhandene
# Tier-Tabelle traegt middle=sonnet fuer beide KEEP-Berater (Status quo unveraendert, AK-12 bestaetigt).
# Gegenprobe: KEIN Spawn im Express-Bereich (TIER-1/TIER-2 + KEEP-Spawns 3.7/7.7) mit
# model=haiku, general-haiku, oder tier=haiku. (Beweis: test_no_haiku_in_express_path)
#
# ── DEFAULT-OFF (AK-7/AK-8): bei idf_express_lane=false -> express_provisional bleibt false ──────
# -> ALLE Pre-7.7-Berater spawnen normal (2a-ii liest express_provisional=false => Spawn). Byte-
# identisch zum Status quo.
#
# BL-403 batch_3/AK-7 (2026-06-18): idf_express_lane ist jetzt ein formalisierter Session-Dial
# (session_params_resolver.py FRAMEWORK_DEFAULTS, default false — Muster BL-327 parallel_mode /
# BL-330 workflow). Quellen-Praezedenz (resolver-aware, weiterhin default-OFF):
#   1. args.idf_express_lane           (per-Lauf Caller-Arg, hoechste Prioritaet)
#   2. session_params_resolver(...)    (3-Stufen BL > Vault > Framework; Framework-Default=false)
#   3. false                           (fail-safe; fehlt der Param ueberall -> voller Pfad)
# Aufloesung via: py -3 .claude/scripts/session_params_resolver.py resolve --param=idf_express_lane --bl-id={args.BL_ID}
# default-OFF bleibt erhalten: ohne jeden Override liefert der Resolver den Framework-Default false.
# Der Dial ist die EINZIGE Stellschraube (kein Bypass-Feld). ABGRENZUNG: behavior_identical ist
# KEIN Session-Dial, sondern ein per-ITEM Caller-Arg/PL-Annotation (siehe vc3, Z~621).
idf_express_lane    = (args.idf_express_lane ?? session_params_resolver(idf_express_lane) ?? false)   # AK-7 Session-Dial, default-OFF
express_provisional = false
IF idf_express_lane == true:
  # TIER-1 billige Vorab-Bedingungen (verfuegbar VOR Phase 3.5, ohne teure Berater).
  # Fail-safe (PT-CMD-023): fehlt eine Quelle -> Bedingung false -> kein provisional -> voller Pfad.
  #   vorab_actionable_count: loopCheck (BL-199 Re-Entry) traegt pl_item_count_current; bei Erst-
  #     Eintritt args.express_items (Caller-Hint); sonst PL-Master-Count; sonst 99 (=> vc1 false).
  #   vorab_k: BL/PL-Frontmatter k_score (granular, BL-402-Lehre: NICHT Story-Fallback) ?? A_PIPELINE_
  #     STATE.k_score (A-Pipeline-Aggregat); sonst 99 (=> vc2 false).
  #   vorab_behavior_identical: args.behavior_identical (Caller) ?? PL-Annotation behavior_identical;
  #     sonst false (=> vc3 false).
  #     BL-403 batch_3/AK-7-ABGRENZUNG: behavior_identical ist KEIN Session-Dial (anders als
  #     idf_express_lane, Z607). Es ist ein per-ITEM Caller-Arg/PL-Annotation (item-spezifisch,
  #     nicht session-global) -> bewusst NICHT in session_params_resolver verdrahtet. Bleibt eine
  #     der vc-Vorab-Bedingungen, kein global resolvbarer Param.
  #   vorab_file_count: PL target_files-Annotation count ?? args.express_files (Caller); sonst 99 (=> vc4 false).
  vorab_actionable_count   = BERATER_OUTPUTS_IDF.loopCheck.pl_item_count_current ?? args.express_items ?? pl_master_actionable_count ?? 99
  vorab_k                  = bl_pl_frontmatter.k_score ?? A_PIPELINE_STATE.k_score ?? 99
  vorab_behavior_identical = (args.behavior_identical == true) OR (pl_annotation.behavior_identical == true)
  vorab_file_count         = pl_annotation.target_files_count ?? args.express_files ?? 99
  vc1 = (vorab_actionable_count == 1)       # genau 1 Item (Vorab-Signal)
  vc2 = (vorab_k < 5)                       # k < 5 (granular, BL-402)
  vc3 = (vorab_behavior_identical == true)  # behavior-identical (Caller/PL-Annotation)
  vc4 = (vorab_file_count <= 2)             # <= 2 Dateien (Vorab-Signal)
  Logge: "[IDF-EXPRESS-VORAB] Vorab-Vektor: vc1(items==1)={vc1}[{vorab_actionable_count}] vc2(k<5)={vc2}[{vorab_k}] vc3(behavior_identical)={vc3} vc4(<=2 Dateien)={vc4}[{vorab_file_count}]"
  IF vc1 AND vc2 AND vc3 AND vc4:
    express_provisional = true
    Logge: "[IDF-EXPRESS-VORAB] provisional=TRUE (vc1..vc4 erfuellt) — teure Pre-7.7-Berater werden INLINE (2a-ii); KEEP 3.7+7.7 laufen REAL; Confirm-Gate POST-7.7 bestaetigt oder ABORTet."
  ELSE:
    Logge: "[IDF-EXPRESS-VORAB] provisional=FALSE (mind. 1 Vorab-Bedingung verletzt) — voller IDF-Pfad."
ELSE:
  Logge: "[IDF-EXPRESS-VORAB] idf_express_lane=false (Default) — express_provisional=false, voller Pfad (AK-8)."
Set IDF_PIPELINE_STATE.express_provisional = express_provisional

# ─── Phase 3: AK_PER_PL (BL-209 Hard-Cut: 3.1/3.2 ENTFERNT, startet bei 3.5) ─
# Phase 3.1 (akExtraktion) ENTFERNT — A-Pipeline _A_berater_akExtraktion (Phase 5b) ist Single-Source.
# Phase 3.2 (plAggregation) ENTFERNT — A-Pipeline _A_berater_plAggregation (Phase 5c) ist Single-Source.
# IDF verwaltet PL-Items NUR noch via Reverse-Sync (3.7 modelSync) + Bewertung (3.8 plBewertung).
IF resume_phase IN [null, "INIT", "AK_PER_PL"]:
  # ---- 3.5 Validator ----
  # BL-403 batch_2/2a-ii (AK-5/AK-10): bei express_provisional==true (TIER-1 Vorab-Gate VOR Phase 3.5,
  # Z~628) INLINE-Trivial-Vertrag statt Spawn. Deterministisch fuer 1 triviales Item, schema-identisch
  # zum Echt-Output von _IDF_berater_validator (vgl. _manifest validator-Slot). KEEP 3.7 modelSync +
  # 7.7 testSearch lesen express_provisional NICHT (laufen IMMER REAL, AK-4). default-OFF (AK-8): bei
  # express_provisional==false (Default, idf_express_lane=false) spawnt der ELSE-Zweig den Berater
  # EXAKT unveraendert -> byte-identische volle Sequenz.
  IF express_provisional == true:
    # <item>-Ableitung (deterministisch, 1 Item): per_pl_evaluation-key (falls 3.8 schon lief — bei
    # express_provisional sind 3.8/3.8e weiter unten ebenfalls inline) ?? PL-Master actionable.
    the_item = (keys(DF_BATCH_STATE.per_pl_evaluation) ?? actionable_pl_item_ids ?? [single_actionable_pl_item_id])[0]
    Schreibe BERATER_OUTPUTS_IDF.validator = {pl_items_total: 1, pl_items_valid: 1, validation_errors: [], srs_validation_errors: [], actionable_pl_items: [the_item], pruning_recommendation: "PROCEED", last_berater: "validator(idf-express-skip)", status: "DONE"}
    Logge: "[IDF-EXPRESS 3.5] validator INLINE (express_provisional, 1 Trivial-Item {the_item}) — kein Spawn (AK-5/AK-10)."
  ELSE:
    Skill(_IDF_berater_validator, args=args.BL_ID)
  TaskUpdate name="phase-3-5-validator" status=DONE
  # ---- 3.6 ItemContext ----
  IF express_provisional == true:
    Schreibe BERATER_OUTPUTS_IDF.itemContext = {items_total: 1, items_blocked: 0, blocked_items: [], last_berater: "itemContext(idf-express-skip)", status: "DONE"}  # BL-405: kein Modus-Override-Feld mehr (INV-MODUS-1, C3 entscheidet allein)
    Logge: "[IDF-EXPRESS 3.6] itemContext INLINE (express_provisional, 1 Trivial-Item, 0 blocked) — kein Spawn (AK-5)."
  ELSE:
    Skill(_IDF_berater_itemContext, args=args.BL_ID)
  TaskUpdate name="phase-3-6-itemContext" status=DONE
  # ---- 3.7 ModelSync (REVERSE-Sync: PL → Model, INV-IDF-REVERSE-1, BL-198 AK-4) ----
  # Entry-3-Mechanik via /_parking-lot (BL-201). Forward Spec→PL ist A-Pipeline.
  Skill(_IDF_berater_modelSync, args=args.BL_ID)
  TaskUpdate name="phase-3-7-modelSync" status=DONE

  # ---- 3.8 plBewertung (NEU BL-203) ----
  # SRS-Refresh → Bottleneck-Filter → K-Score-Refresh → Intern/Extern-Klassifikation.
  # Schreibt DF_BATCH_STATE.per_pl_evaluation (Pro-PL-Vektor).
  # Re-Entry-Aware (BL-206 AK-7): args.bottleneck_reentry=true → nur affected_pl_items refreshen.
  TaskCreate name="phase-3-8-plBewertung" depends_on=["phase-3-7-modelSync"]
  # BL-403 batch_2/2a-ii (AK-5): INLINE per_pl_evaluation-Vektor fuer das 1 Trivial-Item. Schema exakt
  # (per_pl_evaluation wird vom idf-light-Gate Z~681 actionable_count + von C3 SDF Phase 1.1 gelesen).
  # AK-11-Linie: k kommt aus dem Frontmatter-k des Items (granular), NICHT Story-Fallback (BL-402).
  IF express_provisional == true:
    the_item = (keys(DF_BATCH_STATE.per_pl_evaluation) ?? actionable_pl_item_ids ?? [single_actionable_pl_item_id])[0]
    the_ak   = (item_frontmatter.source_ak ?? bl_pl_frontmatter.source_ak ?? null)
    fm_k     = item_frontmatter.k_score ?? bl_pl_frontmatter.k_score ?? A_PIPELINE_STATE.k_score   # granular (BL-402-Lehre)
    Schreibe DF_BATCH_STATE.per_pl_evaluation = {the_item: {ak: the_ak, srs: 0, srs_flag: "all_confirmed", k_score: fm_k, bottleneck: false, bottleneck_route: null, intern: true, evaluated_at: ISO_DATE()}}
    Set DF_BATCH_STATE.plBewertung_done = true
    Logge: "[IDF-EXPRESS 3.8] plBewertung INLINE (express_provisional, 1 Item {the_item}: srs=0/all_confirmed, k={fm_k} granular-frontmatter, intern, 0 bottleneck) — kein Spawn (AK-5)."
  ELSE:
    exit = Skill(_IDF_berater_plBewertung, args=args.BL_ID)
    IF exit == 2: → ABORT("plBewertung failed")
  TaskUpdate name="phase-3-8-plBewertung" status=DONE

  # ---- 3.8e bottleneckTrigger (NEU BL-206 AK-1) ----
  # Liest per_pl_evaluation, baut bottleneck_queue (queue_for_sc + queue_for_wp).
  # Max-Loop-Schutz (AK-8): Loop-Counter-Increment bei Re-Entry, DEFERRED_BOTTLENECK bei max_loops.
  TaskCreate name="phase-3-8e-bottleneckTrigger" depends_on=["phase-3-8-plBewertung"]
  # BL-403 batch_2/2a-ii (AK-5): INLINE leere bottleneck_queue. Trivial = 0 Bottlenecks (das 1 Item
  # ist intern/srs=0/all_confirmed -> weder SC- noch WP-Queue). Schema exakt (DF_BATCH_STATE.bottleneck_queue).
  IF express_provisional == true:
    Schreibe DF_BATCH_STATE.bottleneck_queue = {queue_for_sc: [], queue_for_wp: [], loop_counts: {}, deferred: [], computed_at: ISO_DATE()}
    Set DF_BATCH_STATE.bottleneck_trigger_done = true
    Logge: "[IDF-EXPRESS 3.8e] bottleneckTrigger INLINE (express_provisional, 0 Bottlenecks fuer Trivial-Item) — kein Spawn (AK-5)."
  ELSE:
    exit = Skill(_IDF_berater_bottleneckTrigger, args=args.BL_ID)
    IF exit == 2: → ABORT("bottleneckTrigger failed")
  TaskUpdate name="phase-3-8e-bottleneckTrigger" status=DONE

  Set IDF_PIPELINE_STATE.idf_status = "DEP_MATRIX"

# ═══ IDF-LIGHT-GATE (NEU 2026-06-01, User-Idee) — Organisations-Berater bei wenig Items skippen ═══
# Idee: clustering/sequence/dependency ordnen VIELE Items in Batches. Bei <=3 Items sind sie No-Ops
# (trivial 1 Cluster, triviale Reihenfolge). Die ESSENZIELLEN Berater (validator/batchPlan/stagePlanner/
# metricPlanner/testSearch/finalSummary) laufen WEITER — sie sind der Vertrag, den SDF/C3/Guards brauchen
# (Batch+Metriken+Coverage von BERATERN gesetzt, KEIN Hand-Write). Deshalb ist Light LEGITIM, KEIN Drift:
# nur die sinnlose Organisations-Ceremony faellt weg, der Modus kommt weiter sauber von C3.
# Bei skip schreibt der Orchestrator den TRIVIAL-Output SELBST (downstream liest ihn normal — kein
# Berater muss geaendert werden). Gestuft: 1 Item = ultralight (clustering+dependency+sequence skip);
# 2-3 Items = light (nur clustering skip; dependency+sequence laufen quick fuer die Reihenfolge).
actionable_count = |DF_BATCH_STATE.per_pl_evaluation| ?? |BERATER_OUTPUTS_IDF.validator.actionable_pl_items| ?? 99
idf_full         = (args.full == true)   # --full erzwingt Voll-IDF (Override-Hatch fuer Sonderfaelle)
idf_light        = (actionable_count <= 3) AND NOT idf_full
idf_ultralight   = (actionable_count == 1) AND NOT idf_full
Set IDF_PIPELINE_STATE.idf_light_mode = (idf_ultralight ? "ultralight" : (idf_light ? "light" : "full"))
IF idf_light:
  Logge: "[IDF-LIGHT] actionable={actionable_count} <= 3 -> {idf_light_mode}: SKIP clustering" + (idf_ultralight ? " + dependency + sequence (1 Item, keine Deps/Reihenfolge)" : " (dependency+sequence laufen quick)") + ". testSearch/metric/batchPlan/finalSummary laufen normal (Vertrag fuer SDF/C3). Override: /_IDF_orchestrate --full."

# ─── Phase 4: DEP_MATRIX (ABSORBIERT SDF-Berater) ───────────────────
IF resume_phase IN [null,..., "DEP_MATRIX"]:
  IF idf_ultralight:
    # 1 Item -> keine Inter-Deps. Orchestrator schreibt Trivial-Output (kein Berater-Spawn); downstream liest normal.
    only_items = keys(DF_BATCH_STATE.per_pl_evaluation) ?? [single_actionable_pl_item_id]
    Schreibe BERATER_OUTPUTS_IDF.dependencyAnalyzer = {nodes: only_items, edges: [], cycles: [], mermaid_text: "graph TD", file_refs_total: 0, last_berater: "dependencyAnalyzer(idf-light-skip)"}
    Logge: "[IDF-LIGHT] Phase 4 dependencyAnalyzer SKIP (ultralight, 1 Item) — Trivial-DAG geschrieben"
  ELSE:
    exit = Skill(_IDF_berater_dependencyAnalyzer, args=args.BL_ID)
    IF exit == 1: Logge: "[IDF Phase 4] WARN cycles_detected — Mitose empfohlen"
    IF exit == 2: → ABORT("dependencyAnalyzer failed")
  Set IDF_PIPELINE_STATE.idf_status = "CLUSTER"
  TaskUpdate name="phase-4-dependency" status=DONE

# ─── Phase 5: CLUSTER (Kohaesion + Mitose-Signal) ───────────────────
IF resume_phase IN [null,..., "CLUSTER"]:
  IF idf_light:
    # <=3 Items -> trivial 1 Cluster. Orchestrator schreibt Trivial-Output; downstream batchPlan liest .clusters normal.
    cl_items = keys(DF_BATCH_STATE.per_pl_evaluation) ?? all_actionable_pl_item_ids
    Schreibe BERATER_OUTPUTS_IDF.clustering = {clusters: [{id: "C-1", items: cl_items}], cluster_aggregates: [{cluster_id: "C-1", items_count: |cl_items|, k_score_mean: null}], mitose_signal: false, last_berater: "clustering(idf-light-skip)"}
    Logge: "[IDF-LIGHT] Phase 5 clustering SKIP (<=3 Items -> 1 Cluster C-1) — kein Mitose moeglich"
  ELSE:
    exit = Skill(_IDF_berater_clustering, args=args.BL_ID)
    IF exit == 1: Logge: "[IDF Phase 5] MITOSE_HINT — siehe BERATER_OUTPUTS.clustering"
  Set IDF_PIPELINE_STATE.idf_status = "SEQUENCE"
  TaskUpdate name="phase-5-clustering" status=DONE

# ─── Phase 6: SEQUENCE (ABSORBIERT SDF-Berater, AK-09) ──────────────
IF resume_phase IN [null,..., "SEQUENCE"]:
  IF idf_ultralight:
    # 1 Item -> triviale Sequenz. Orchestrator schreibt Trivial-Output; downstream liest ordered_items normal.
    only_item = (keys(DF_BATCH_STATE.per_pl_evaluation) ?? [single_actionable_pl_item_id])[0]
    Schreibe BERATER_OUTPUTS_IDF.sequencePlanner = {ordered_items: [only_item], topology_pass: true, total_items: 1, last_berater: "sequencePlanner(idf-light-skip)"}
    Logge: "[IDF-LIGHT] Phase 6 sequencePlanner SKIP (ultralight, 1 Item) — Trivial-Sequenz geschrieben"
  ELSE:
    exit = Skill(_IDF_berater_sequencePlanner, args=args.BL_ID)
    IF exit == 2: → ABORT("sequencePlanner Cycle erkannt")
  # INV-01 (AK-09): items_routed_ready (BL-075 Reifungs-Loop)
  ordered = Read(_manifest.md).BERATER_OUTPUTS.sequencePlanner.ordered_items
  Set BL_LIFECYCLE_STATE.items_routed_ready = |ordered|
  Set BL_LIFECYCLE_STATE.last_idf_plan      = ISO_NOW()
  Set BL_LIFECYCLE_STATE.last_idf_plan_date = ISO_DATE()
  Set IDF_PIPELINE_STATE.idf_status = "BATCH_PLAN"
  TaskUpdate name="phase-6-batchSequence" status=DONE

# ─── Phase 7: BATCH_PLAN (NEU, wraps batchPlanner + EXTERN/INTERN-Scan) ──
# batchPlan-Berater intern: ruft _IDF_berater_batchPlanner (MIGR aus SDF)
# + EXTERN/INTERN-Scan + DF_BATCH_STATE-Aggregation
IF resume_phase IN [null,..., "BATCH_PLAN"]:
  # INV-02 (AK-10): Recheck-Guard (Anti-Zirkel BDF<->IDF<->BL)
  IF args.mode == "recheck" AND args.from IN ["bdf_plan", "idf_plan"]:
    Logge: "[IDF Phase 7] RECHECK-Modus: SKIP batchPlan, nur Stats schreiben"
    Set IDF_PIPELINE_STATE.last_recheck_from = args.from
  ELIF express_provisional == true:
    # BL-403 batch_2/2a-ii (AK-10 KERN): batchPlan ist der Opus-4min-Kostentreiber — sein Skip ist der
    # eigentliche Grund der Express-Lane. INLINE deterministischer Trivial-Batch (1 Item -> 1 Batch).
    # batch_mode_hints (ADVISORY) gesetzt, NIEMALS batch_modes (INV-MODUS-1: C3 SDF Phase 1.1 ist
    # alleiniger modus-Schreiber). Schema exakt (DF_BATCH_STATE-Batch-Felder + BERATER_OUTPUTS_IDF.batchPlan).
    the_item = (keys(DF_BATCH_STATE.per_pl_evaluation) ?? actionable_pl_item_ids ?? [single_actionable_pl_item_id])[0]
    fm_k     = (DF_BATCH_STATE.per_pl_evaluation[the_item].k_score) ?? item_frontmatter.k_score ?? bl_pl_frontmatter.k_score ?? A_PIPELINE_STATE.k_score   # granular (BL-402)
    Schreibe DF_BATCH_STATE.batch_items_per_batch = {batch_1: [the_item]}
    Set DF_BATCH_STATE.batch_items        = [the_item]
    Set DF_BATCH_STATE.current_sub_batch_id = "batch_1"
    Set DF_BATCH_STATE.batch_total        = 1
    Set DF_BATCH_STATE.k_score_aggregate  = fm_k
    Set DF_BATCH_STATE.srs_aggregate      = 0
    Set DF_BATCH_STATE.batch_type         = "polish"
    Schreibe DF_BATCH_STATE.batch_mode_hints = {batch_1: "M2"}   # ADVISORY (INV-MODUS-1: NICHT batch_modes)
    Set DF_BATCH_STATE.batchPlan_done     = true
    Schreibe BERATER_OUTPUTS_IDF.batchPlan = {batch_size: 1, batch_count: 1, batch_items: [the_item], current_sub_batch_id: "batch_1", escalation_hint: "SONNET_OK", last_berater: "batchPlan(idf-express-skip)", status: "DONE"}
    Logge: "[IDF-EXPRESS 7] batchPlan INLINE (express_provisional, 1 Item {the_item} -> 1 Batch batch_1, k={fm_k}, hint=M2 ADVISORY) — kein Spawn, KEIN Opus-4min (AK-10 Kern). INV-MODUS-1: batch_mode_hints, NICHT batch_modes."
  ELSE:
    # INV-TIER-CAP: Phase 7 wuenscht opus, gecappt durch session.ceiling.
    #   ceiling=sonnet -> general-sonnet (NIE general-opus, auch wenn Berater
    #   batchPlan opus gerne haette — Intelligenz-Budget kapitulier nicht).
    worker_tier = min_tier("opus", _session_params.ceiling)
    exit = Skill(_IDF_berater_batchPlan, args=args.BL_ID)   # via worker_tier-Worker
    # batchPlan ruft intern _IDF_berater_batchPlanner + writes DF_BATCH_STATE
    IF exit == 1: Logge: "[IDF Phase 7] ESCALATE — Opus-required (k>=70 OR srs=high)"
    IF exit == 2: → ABORT("batchPlan failed")

  Set IDF_PIPELINE_STATE.idf_status = "STAGE_PLAN"
  TaskUpdate name="phase-7-batchPlan" status=DONE

# ─── Phase 7.5: STAGE_PLAN (NEU 2026-05-09 BL-168 SRP-Refactor) ──────
# stagePlanner liest stage_*.md (Discovery), batches (Phase 7), sequence (Phase 6),
# layers (Phase 4) → batch_stages-Map fuer SDF Outer-Loop (BL-166).
IF resume_phase IN [null,..., "STAGE_PLAN"]:
  Logge: "[IDF Phase 7.5] STAGE_PLAN — stagePlanner pro Sub-Batch"
  # ─── BL-224 Strang B: allowed_stages-Whitelist-Setter (per-BL, additiv) ───
  # Setzt IDF_PIPELINE_STATE.allowed_stages aus den per-BL Session-Params (BL-234-Resolver),
  # BEVOR stagePlanner liest; stagePlanner filtert batch_stages darauf (INV-STAGE-10). Leer =>
  # kein Filter (heutiges Verhalten = 486-safe). Eigener Param (NICHT tdd_stages = TDD-Step-Filter
  # an anderem Seam; kein globaler Param-Wildwuchs). Wirkt erst bei Redeploy (F-REDEPLOY-DRIFT).
  allowed = `py -3 .claude/scripts/session_params_resolver.py resolve --param=allowed_stages --bl-id={args.BL_ID}`
  IF allowed not in (None, [], ""):
    Set IDF_PIPELINE_STATE.allowed_stages = allowed
    Logge: "[IDF Phase 7.5] allowed_stages-Whitelist (per-BL) = {allowed}"
  # BL-403 batch_2/2a-ii (AK-5): INLINE Trivial-Stage-Plan. Trivial 1-Item -> Stage 1 (INV-STAGE-2
  # PFLICHT: Stage 1 ist immer dabei). Schema exakt (DF_BATCH_STATE.batch_stages + stage_begruendung_per_batch).
  IF express_provisional == true:
    Schreibe DF_BATCH_STATE.batch_stages = {batch_1: [1]}
    Schreibe DF_BATCH_STATE.stage_begruendung_per_batch = {batch_1: "idf-express-skip: trivial 1-Item -> Stage 1 (INV-STAGE-2 PFLICHT)"}
    Set DF_BATCH_STATE.stagePlanner_done = true
    Logge: "[IDF-EXPRESS 7.5] stagePlanner INLINE (express_provisional, batch_1 -> Stage [1], INV-STAGE-2 PFLICHT) — kein Spawn (AK-5)."
  ELSE:
    exit = Skill(_IDF_berater_stagePlanner, args=args.BL_ID)
    # stagePlanner schreibt: DF_BATCH_STATE.batch_stages + stage_begruendung_per_batch
    IF exit == 1: Logge: "[IDF Phase 7.5] WARN — kein Layer-Mapping, fallback Stage 1 only"
    IF exit == 2: → ABORT("stagePlanner failed")

  Set IDF_PIPELINE_STATE.idf_status = "METRIC_PLAN"
  TaskUpdate name="phase-7-5-stagePlan" status=DONE

# ─── Phase 7.6: METRIC_PLAN (NEU 2026-05-10 BL-172 SRP-Refactor) ─────
# metricPlanner liest 4_K-Score/*-K-SCORE.md (per_ak), batch_items_per_batch
# (Phase 7) → metric_per_batch-Map fuer SDF Phase 1.1 Per-Batch-Modus.
IF resume_phase IN [null,..., "METRIC_PLAN"]:
  Logge: "[IDF Phase 7.6] METRIC_PLAN — metricPlanner pro Sub-Batch"
  # BL-403 batch_2/2a-ii (AK-5 + AK-11 SPEZIALFALL): INLINE metric_per_batch fuer das 1 Trivial-Item.
  # AK-11 KRITISCH: k_score_* kommt aus dem FRONTMATTER-k des Items (granular, fm_k), NICHT aus
  # K-SCORE.md (Story-Fallback). fallback_used=false + special_flags=[] => KEIN story_fallback_k_score-
  # Flag => C3 (SDF Phase 1.1) liest granulares k statt Story-k=38 => der BL-402-Story-Fallback-Bug
  # entfaellt fuer Trivial-Items. srs_source="express_inline" markiert die Herkunft. Schema exakt
  # (DF_BATCH_STATE.metric_per_batch[batch_X], vgl. _manifest metric_per_batch-Slot).
  IF express_provisional == true:
    fm_k = (DF_BATCH_STATE.per_pl_evaluation[(keys(DF_BATCH_STATE.per_pl_evaluation) ?? [])[0]].k_score) ?? item_frontmatter.k_score ?? bl_pl_frontmatter.k_score ?? A_PIPELINE_STATE.k_score   # granular (BL-402-Bypass)
    Schreibe DF_BATCH_STATE.metric_per_batch = {batch_1: {srs_max: 0, srs_avg: 0.0, k_score_max: fm_k, k_score_avg: fm_k, pl_k_score_avg: fm_k, items_count: 1, items_with_data: 1, fallback_used: false, pl_bottleneck_ct: 0, special_flags: [], srs_source: "express_inline", w_status_set: [], gap_status: null, gap_status_dominant: null}}
    Set DF_BATCH_STATE.metricPlanner_done = true
    Logge: "[IDF-EXPRESS 7.6] metricPlanner INLINE (express_provisional, batch_1: k={fm_k} GRANULAR-frontmatter, fallback_used=false, special_flags=[] -> KEIN story_fallback => C3 liest granulares k, BL-402-Bug entfaellt fuer Trivial) — kein Spawn (AK-5/AK-11)."
  ELSE:
    exit = Skill(_IDF_berater_metricPlanner, args=args.BL_ID)
    # metricPlanner schreibt: DF_BATCH_STATE.metric_per_batch
    IF exit == 1: Logge: "[IDF Phase 7.6] WARN — mind. 1 Sub-Batch ohne Per-AK-Daten, Story-Fallback aktiv"
    IF exit == 2: → ABORT("metricPlanner failed")

  # ─── Anti-Shadow Post-Check (NEU 2026-05-27, RCA DCSRE-486 Round 11) ───
  # IDF darf NUR batch_mode_hints schreiben, NICHT batch_modes (das ist SDF Phase 1.1).
  # Live-Beweis: Round 11 Manifest Z5986 hatte batch_modes in IDF-Output → SDF Phase 1.1
  # wurde übersprungen → INV-MODUS-1 verletzt.
  #
  # BL-313 AK-3 (2026-06-11): batch_mode_hints hat jetzt einen HAPPY-PATH-PRODUCER —
  # _IDF_berater_batchPlan SCHRITT 5b emittiert batch_mode_hints (ADVISORY, abgeleitet aus
  # build_klasse je Sub-Batch) im NORMAL-Pfad (Phase 7). Damit ist batch_mode_hints auf
  # sauberen INV-MODUS-1-konformen Laeufen ZUVERLAESSIG vorhanden, BEVOR SDF startet →
  # guard_geist5_idf_to_sdf.py blockt den Erst-SDF-Eintritt nicht mehr (BL-313-Luecke).
  # Der Anti-Shadow Post-Check unten ist daher NUR NOCH FALLBACK/KORREKTUR-NETZ:
  # er feuert ausschliesslich wenn IDF FAELSCHLICH batch_modes schrieb (Drift) und
  # benennt es defensiv in batch_mode_hints um. NICHT mehr der einzige Writer.
  # Anti-Shadow-Logik BLEIBT (Korrektur-Netz, nicht entfernen — INV-MODUS-1-Schutz).
  written_batch_modes = Lies DF_BATCH_STATE.batch_modes (nach metricPlanner)
  matching_sdf_berater = grep BERATER_OUTPUTS, key prefix "modusEntscheidung"
  IF written_batch_modes != null AND matching_sdf_berater == null:
    Logge: "[IDF Phase 7.6 Anti-Shadow] INV-MODUS-1-SHADOW-VIOLATION"
    Logge: "  metricPlanner oder voriger IDF-Berater hat batch_modes geschrieben"
    Logge: "  ohne dass SDF _SDF_berater_modusEntscheidung lief — SDF-Bypass-Risiko"
    Logge: "  Auto-Korrektur: batch_modes → batch_mode_hints umbenennen"
    Schreibe DF_BATCH_STATE.batch_mode_hints = DF_BATCH_STATE.batch_modes
    Schreibe DF_BATCH_STATE.batch_modes      = null
    Schreibe DF_BATCH_STATE.shadow_corrected_at = ISO_NOW
    APPEND .claude/audit/audit.jsonl event=INV-MODUS-1-SHADOW-CORRECTED

  Set IDF_PIPELINE_STATE.idf_status = "TEST_SEARCH"
  TaskUpdate name="phase-7-6-metricPlan" status=DONE

# ─── Phase 7.7: TEST_SEARCH (NEU 2026-05-30 BL-231/BL-232 — Coverage-Map, Plan-Zeit) ───
# testSearch wandert von _I_orchestrate (Implement-Zeit, Step 4) HIERHER (Plan-Zeit). Grund:
# Test-Coverage entscheidet den MODUS (M2 vs M3) + welche STAGES laufen — beides Plan-Fragen,
# keine Implement-Fragen. Modus = ART der Aufgabe (Coverage), NICHT Umfang (K-Score).
# Erzeugt coverage_map PERSISTENT (INTAKT fuer Implement: die covering_tests werden spaeter
# ausgefuehrt — User-Constraint B 2026-05-30). Laeuft NACH metricPlanner (Ziel-Dateien bekannt).
IF resume_phase IN [null, ..., "TEST_SEARCH"]:
  Logge: "[IDF Phase 7.7] TEST_SEARCH — Coverage-Map pro Sub-Batch (alle session_params.test_stages PARALLEL)"
  exit = Skill(_IDF_berater_testSearch, args=args.BL_ID)
  # testSearch schreibt: BERATER_OUTPUTS_IDF.testSearch.coverage_map + DF_BATCH_STATE.coverage_per_batch
  # INV-MODUS-1: liefert NUR Coverage-Daten (verdict covered|partial|uncovered + covering_tests), KEIN modus.
  IF exit == 1: Logge: "[IDF Phase 7.7] WARN — mind. 1 Sub-Batch ohne Ziel-Datei-Refs → coverage=unknown (C3 faellt auf gap_status zurueck)"
  IF exit == 2: → ABORT("testSearch failed")
  Set IDF_PIPELINE_STATE.idf_status = "PARALLEL_SUITABILITY"
  TaskUpdate name="phase-7-7-testSearch" status=DONE

# ═══ IDF-EXPRESS-LANE-GATE (NEU 2026-06-18 BL-403 — Trivial-Item-Express-Lane, batch_1/PL-1..5) ═══
# Verallgemeinerung des IDF-LIGHT-Musters (Z619-679) von 3 No-Op-Beratern auf die teuren
# Per-Item-Kosten-Treiber. Bei einem ECHT-TRIVIALEN 1-Item-Fall (6 UND-Bedingungen) werden die
# nachfolgenden Berater NICHT gespawnt, sondern ihre Vertraege schema-identisch INLINE geschrieben.
#
# ── AK-2 CHICKEN-EGG (Gate-Punkt FIX nach Phase 7.7): ──────────────────────────────────────────
# Der Gate kann NICHT vor Phase 7.7 entscheiden, weil Bedingung c5 (covered) erst von testSearch
# (7.7) produziert wird, und c6 (modelSync-harvest leer) erst von modelSync REVERSE (3.7). Beide
# KEEP-Berater liegen VOR diesem Gate-Punkt und laufen daher IMMER ECHT (AK-4) — sie werden NIE
# inline-gefakt. Es existiert KEIN Gate-Pfad, der vor 7.7 Berater ueberspringt. Darum sitzt dieser
# Block FIX hier (POST-7.7, PRE-7.8).
#
# ── AK-3 KLASSIFIKATIONS-MATRIX (welcher Berater inline-fakebar vs. KEEP echte-Messung): ────────
#   ┌──────────────────────────┬──────────────────────────────────────────────────────────────┐
#   │ KEEP (IMMER echt, AK-4)   │ SKIP-inline-KANDIDATEN (deterministisch aus Frontmatter/PL)   │
#   ├──────────────────────────┼──────────────────────────────────────────────────────────────┤
#   │ 3.7 modelSync (REVERSE)   │ 3.5 validator · 3.6 itemContext · 3.8 plBewertung ·          │
#   │ 7.7 testSearch (Coverage) │ 3.8e bottleneckTrigger · 7 batchPlan (Opus-Kostentreiber) ·  │
#   │                          │ 7.5 stagePlanner · 7.6 metricPlanner · 7.8 parallelSuitability│
#   │                          │ 8.0 finalSummary                                            │
#   └──────────────────────────┴──────────────────────────────────────────────────────────────┘
#   (clustering/dependencyAnalyzer/sequencePlanner sind bereits idf-ultralight-inline, Z619-679.)
#   KEEP ist disjunkt von SKIP: weder modelSync noch testSearch stehen je in der Skip-Liste (AK-4).
#
# ── SCOPE-GRENZE / TWO-TIER (batch_1 + batch_2): ────────────────────────────────────────────────
# Die Matrix DOKUMENTIERT alle 9 Skip-Kandidaten. batch_1 schaltete NUR die zwei Phasen NACH dem
# Gate-Punkt auf inline: 7.8 parallelSuitability + 8.0 finalSummary. Die Berater VOR 7.7 (3.5..7.6)
# liefen auf dem Erst-Pass REAL — ihr prospektiver Skip brauchte ein Vorab-Signal (der Vorwaerts-Pass
# ist an ihnen schon vorbei, wenn DIESER POST-7.7-Gate entscheidet).
# >>> GELOEST in batch_2 via TIER-1 Vorab-Gate (AK-10): der Pre-7.7-Skip von batchPlan/stagePlanner/
#     metricPlanner/validator/itemContext/plBewertung/bottleneckTrigger wird jetzt PROVISORISCH vor
#     Phase 3.5 entschieden (TIER-1 Vorab-Gate, express_provisional, aus billigen Frontmatter/Caller-
#     Signalen vc1-vc4). DIESER POST-7.7-Block ist die TIER-2 CONFIRM-Stufe: er bestaetigt die
#     provisorische Entscheidung mit den ECHTEN KEEP-Daten (c5 covered + c6 harvest leer) -> EXPRESS,
#     ODER ABORTet fail-loud bei Mismatch (die provisorisch uebersprungenen Pre-7.7-Berater duerfen
#     keine stille Korruption verursachen — Recovery-Hint: ohne idf_express_lane neu laufen). Das war
#     W15 (BURDEN-2, chicken-egg); die Sicherheit traegt: default-OFF + KEEP-Berater laufen IMMER REAL
#     + Abort-on-Mismatch. (Die Berater-Inline-Wraps der Pre-7.7-Phasen liefert batch_2/2a-ii via
#     express_provisional==true; DIESER Kontrollfluss-Block setzt nur die Flags.) <<<
#
# ── AK-7/AK-8 DEFAULT-OFF (Regression-Schutz): ──────────────────────────────────────────────────
# Der GESAMTE Express-Pfad ist nur erreichbar wenn idf_express_lane == true. Default = false
# (Produktion). Bei false bleibt express_gate = "FULL" -> 7.8/8.0 spawnen normal -> NULL
# Verhaltensaenderung zum Status quo (byte-identische Berater-Spawn-Sequenz).
# BL-403 batch_3/AK-7: idf_express_lane ist ein formalisierter Session-Dial (session_params_resolver,
# Framework-Default false). Quellen-Praezedenz IDENTISCH zum TIER-1-Gate (Z607, Single-Source der
# Aufloesung): args.idf_express_lane ?? session_params_resolver(idf_express_lane) ?? false.
# Pattern-Kanon: BL-327 (parallel_mode=false) + BL-330 (workflow={false,normal,fast}).
#
# ── PT-CMD-023 GRACEFUL DEGRADATION: ────────────────────────────────────────────────────────────
# Fehlt eine Gate-Eingabe (coverage_per_batch, metric_per_batch, per_pl_evaluation, modelSync-
# Slot) -> express_gate bleibt "FULL" (fail-safe zum vollen Pfad), NIE Crash.
idf_express_lane = (args.idf_express_lane ?? session_params_resolver(idf_express_lane) ?? false)   # AK-7 Session-Dial, default-OFF (Single-Source: Z607)
express_gate     = "FULL"                             # AK-8: Default = Regression-Schutz (Status quo)
IF idf_express_lane == true:
  # ── TIER-2 CONFIRM-Stufe (POST-7.7): bestaetigt die provisorische TIER-1-Entscheidung mit den ──
  #    ECHTEN KEEP-Daten. c1-c4 wurden bereits VOR Phase 3.5 von TIER-1 (vc1-vc4, Z~597) geprueft;
  #    HIER verifizieren wir NUR die neuen KEEP-Daten c5 (covered, testSearch 7.7) + c6 (harvest
  #    leer, modelSync 3.7) — sie sind erst jetzt verfuegbar (Chicken-Egg AK-2). Fehlt ein Slot ->
  #    Bedingung = false (fail-safe, PT-CMD-023).
  # Single-Item-Aggregation: bei einem echt-trivialen 1-Item liegt genau 1 Sub-Batch vor; wir lesen
  # dessen granulare KEEP-Daten.
  the_batch_id = (keys(DF_BATCH_STATE.metric_per_batch) ?? [])[0]    # erster (einziger) Sub-Batch
  cov_batch    = DF_BATCH_STATE.coverage_per_batch[the_batch_id] ?? {}
  ms_out       = BERATER_OUTPUTS.modelSync ?? {}
  covered                 = (cov_batch.batch_coverage_verdict == "covered") OR (cov_batch.verdict == "covered")
  modelsync_harvest_empty = ((ms_out.promoted_truths_count ?? 0) == 0) AND ((ms_out.promoted_constraints_count ?? 0) == 0) AND (ms_out != {})
  c5 = (covered == true)                  # covered (aus testSearch 7.7) — c5 chicken-egg-Grund (AK-2)
  c6 = (modelsync_harvest_empty == true)  # modelSync-harvest leer (aus modelSync 3.7)
  Logge: "[IDF-EXPRESS] Confirm-Vektor (TIER-2, c1-c4 via TIER-1/vc1-vc4 bereits geprueft): provisional={express_provisional} c5(covered)={c5} c6(harvest_empty)={c6}"
  IF express_provisional == true:
    IF c5 AND c6:
      express_gate = "EXPRESS"
      Logge: "[IDF-EXPRESS-CONFIRM] provisional bestaetigt (c5 covered + c6 harvest_leer) -> EXPRESS. 7.8+8.0 werden inline (batch_1). Pre-7.7-Berater liefen inline (2a-ii). KEEP 3.7/7.7 liefen REAL."
    ELSE:
      Logge: "[IDF-EXPRESS-MISMATCH] FATAL: Vorab-EXPRESS (vc1-vc4 erfuellt) ABER c5(covered)={c5}/c6(harvest_leer)={c6} widerlegen Trivialitaet. Die teuren Pre-7.7-Berater wurden bereits provisorisch uebersprungen — keine stille Korruption zulassen."
      → ABORT("IDF-EXPRESS-MISMATCH: idf_express_lane=true + Vorab-Bedingungen erfuellt, ABER testSearch covered={c5} / modelSync-harvest-leer={c6} widerlegen die Trivialitaet. Pre-7.7-Berater wurden provisorisch uebersprungen. RECOVERY: erneut OHNE idf_express_lane laufen (voller IDF-Pfad): Skill(_IDF_orchestrate, args='{args.BL_ID}'). [PT-CMD-011 fail-loud, feedback_corrective_enforcement: Recovery-Pfad im Block.]")
  ELSE:
    Logge: "[IDF-EXPRESS-CONFIRM] idf_express_lane=true aber kein provisional (vc1-vc4 nicht erfuellt) -> FULL (kein Teil-Express, Konsistenz)."
ELSE:
  Logge: "[IDF-EXPRESS] idf_express_lane=false (Default) -> express_gate=FULL. NULL Verhaltensaenderung (AK-8 Regression-Schutz)."
Set IDF_PIPELINE_STATE.express_gate = express_gate

# ── SCOPE-CUT (BL-403 AK-13, YAGNI): Die Express-Lane greift AUSSCHLIESSLICH IDF-seitig. ──────────
# SDF/Post-seitige Express-Faehigkeit (recalibrate early-exit, modelSync no_model_truth SDF-seitig)
# ist in diesem Slice OUT-OF-SCOPE / DEFERIERT (W18/BURDEN-4, Folge-Scheibe). Begruendung: Scope eng +
# Risiko gering halten (default-OFF-Sicherheit + Scope-Cut). KEIN Express-Verhalten ausserhalb des
# IDF-Orchestrators. Folge-Scheibe: SDF/Post-Express als eigenes BL nach IDF-Express-Forward-Verify.

# ─── Phase 7.8: PARALLEL_SUITABILITY (NEU 2026-06-15 BL-342 — found parallelism, Plan-Zeit) ───
# parallelSuitability scored welche Sub-Batch-PAARE gefahrlos NEBENEINANDER laufen koennen
# (file_index-Ueberlappung → Konflikt-Inseln, BL-316: Datei-Disjunktheit = 0-Lost-Update-Bedingung).
# ADDITIV. INFO-Feld fuer den Wellen-Scheduler (BL-230 Phase C), NIEMALS Modus-Quelle (INV-MODUS-1).
# Laeuft NACH testSearch (batch_items_per_batch + dependencyAnalyzer.file_index bekannt).
# Deterministisch via .claude/scripts/parallel_suitability_producer.py (machine-not-context).
IF resume_phase IN [null, ..., "PARALLEL_SUITABILITY"]:
  IF express_gate == "EXPRESS":
    # BL-403 AK-5/AK-10: Inline-Trivial-Vertrag (kein Spawn). 1 Item -> keine Parallelitaet ->
    # deterministischer Trivial-Block (recommended_N=1, suitable=false), schema-identisch zum
    # Echt-Output von parallelSuitability (parallel_suitability_producer.py WARN-Pfad). Alle
    # Downstream-Pflicht-Felder (Wellen-Scheduler BL-230 Phase C) getragen. INV-MODUS-1: KEIN modus.
    only_items_es = keys(DF_BATCH_STATE.per_pl_evaluation) ?? [single_actionable_pl_item_id]
    Schreibe DF_BATCH_STATE.parallel_suitability = {format_version: "1.0", story_type: "trivial", conflict_islands: 1, largest_island: 1, build_share: null, recommended_N: 1, suitable: false, reason: "idf-express-skip: 1 Item -> keine Parallelitaet (seriell)", ziel_dateien_per_batch: {}, matrix: [], last_berater: "parallelSuitability(idf-express-skip)"}
    Schreibe BERATER_OUTPUTS.parallelSuitability = {status: "DONE", computed_at: ISO_NOW(), n_sub_batches: 1, recommended_N: 1, suitable: false, exit_code: 0, last_berater: "parallelSuitability(idf-express-skip)"}
    Logge: "[IDF Phase 7.8] EXPRESS — parallelSuitability INLINE (recommended_N=1, seriell), kein Spawn (BL-403 AK-10). KEEP-Berater 3.7/7.7 liefen echt."
  ELSE:
    Logge: "[IDF Phase 7.8] PARALLEL_SUITABILITY — Konflikt-Inseln + recommended_N pro Story"
    exit = Skill(_IDF_berater_parallelSuitability, args=args.BL_ID)
    # schreibt: DF_BATCH_STATE.parallel_suitability (ADDITIV) + BERATER_OUTPUTS.parallelSuitability
    # INV-MODUS-1: liefert NUR found-parallelism-Daten (recommended_N/conflict_islands), KEIN modus.
    IF exit == 1: Logge: "[IDF Phase 7.8] WARN — batch_items_per_batch/file_index fehlt → Trivial-Block (recommended_N=1, seriell), idf_light-kompatibel"
    IF exit == 2: → ABORT("parallelSuitability failed")
  Set IDF_PIPELINE_STATE.idf_status = "FINAL_SUMMARY"
  TaskUpdate name="phase-7-8-parallelSuit" status=DONE

# ─── Phase 8.0: FINAL-SUMMARY (NEU 2026-05-24 BL-204) ───────────────
# finalSummary konsolidiert alle IDF-Outputs READ-ONLY in Vektor-Format.
# Mensch: {bl_folder}/4_Blueprint/idf_final_summary_{date}.md (9-Spalten-Tabelle)
# Maschine: _manifest.md IDF_FINAL_SUMMARY YAML-Block
# INV-RO-1: Schreibt KEIN vorheriges Datenfeld um.
# INV-MODUS-1: modus_hint im Output ist Vorhersage — C3 entscheidet final.
IF resume_phase IN [null, ..., "FINAL_SUMMARY"]:
  IF express_gate == "EXPRESS":
    # BL-403 AK-5: Inline-finalSummary-Vektor (kein Spawn). finalSummary ist READ-ONLY-Konsolidierung
    # (INV-RO-1) -> bei 1 Trivial-Item deterministisch aus den bereits vorhandenen Slots ableitbar.
    # Schreibt den Maschinen-Vektor-Slot IDF_FINAL_SUMMARY (den SDF Phase 1.1 / PostBatch recalibrate
    # liest) + BERATER_OUTPUTS_IDF.finalSummary (Status). INV-MODUS-1: KEIN modus (modus_hint=TBD,
    # C3 entscheidet final). INV-DISCLAIMER-1: inv_modus_1_disclaimer PFLICHT.
    es_batch_id  = (keys(DF_BATCH_STATE.metric_per_batch) ?? ["batch_1"])[0]
    es_m         = DF_BATCH_STATE.metric_per_batch[es_batch_id] ?? {}
    es_items     = DF_BATCH_STATE.batch_items_per_batch[es_batch_id] ?? (keys(DF_BATCH_STATE.per_pl_evaluation) ?? [])
    es_vector    = {id: es_batch_id, sequence_pos: 1, one_liner: es_batch_id, items_count: |es_items|, items_extern_count: 0, items_frozen_count: 0, k_score_avg: (es_m.k_score_avg ?? 0), k_score_max: (es_m.k_score_max ?? 0), srs_max: (es_m.srs_max ?? 0), modus_hint: "TBD", stages: (DF_BATCH_STATE.batch_stages[es_batch_id] ?? [1]), stages_rationale: "idf-express-skip", pain_signals: [], anmerkung: "idf-express-skip (trivial 1-Item)", depends_on: [], difficulty_hint: "S"}
    Schreibe _manifest.md IDF_FINAL_SUMMARY = {generated_at: ISO_NOW(), generated_by: "_IDF_orchestrate(idf-express-skip) BL-403", bl_id: args.BL_ID, inv_modus_1_disclaimer: "modus_hint ist Vorhersage. C3 entscheidet final per Round in SDF Phase 1.1 via _SDF_berater_modusEntscheidung. modus_hint != modus.", batches: [es_vector], aggregate: {total_batches: 1, total_items_active: |es_items|, total_items_extern: 0, total_items_frozen: 0, total_items_deferred: 0, k_score_avg_overall: (es_m.k_score_avg ?? 0), srs_max_overall: (es_m.srs_max ?? 0), opus_required_any: false}, recommended_next: [es_batch_id], blocking_clarifications: []}
    Schreibe BERATER_OUTPUTS_IDF.finalSummary = {status: "DONE", human_output_path: null, machine_output_path: "_manifest.md IDF_FINAL_SUMMARY block", batches_summarized: 1, total_items: |es_items|, recommended_next: [es_batch_id], blocking_clarifications: 0, last_berater: "finalSummary(idf-express-skip)"}
    Logge: "[IDF Phase 8.0] EXPRESS — finalSummary INLINE Vektor-Output (1 Trivial-Batch), kein Spawn (BL-403 AK-5)."
  ELSE:
    Logge: "[IDF Phase 8.0] FINAL_SUMMARY — finalSummary Vektor-Output"
    exit = Skill(_IDF_berater_finalSummary, args=args.BL_ID)
    IF exit == 2: → ABORT("finalSummary failed")
  Set IDF_PIPELINE_STATE.idf_status = "IDF_DONE"
  Set IDF_PIPELINE_STATE.completed  = ISO_NOW()
  TaskUpdate name="phase-8-0-finalSummary" status=DONE
  TaskUpdate name="phase-8-idfDone"        status=DONE
# BL-376 Fund#2 (INV-PROV-TRENNUNG): IDF reicht die A-Provenance via propagate_provenance durch —
# derived_from-Felder bei A-abgeleiteten Docs werden registriert (source_provenance-Welt, nicht
# BERATER_OUTPUTS-Provenance). Aufruf: propagate_provenance.py update {doc} --vault {VAULT_ROOT}

# ─── Phase 8.5: Auto-Chain zu SDF (NEU 2026-05-10 BL-173; LOOSENED 2026-05-17 Refit-V3) ───
# Wenn IDF direkt vom User invoked (--from=direct) UND --no-chain nicht gesetzt:
# Glove-Change zu SDF — egal Reifegrad. SDF Phase 1.1 modusEntscheidung entscheidet M{N}.
# Bei --from=bdf_plan: KEIN Auto-Chain (BDF ist Caller).
# Bei --from=orphan_scan (BL-298 2026-06-10): EIGENER Chain-Zweig Phase 8.5a (unten) — Auto-Build-Bounded:
#   <3 Iterationen RE-BATCH-Chain, >=3 HiL-Alert (INV-IDF-ORPHAN-2). User-Entscheid 2026-06-10.
#
# REFIT-V3 LOOSENING 2026-05-17 (User-Direktive "hast du fuer autochain gesorgt"):
# ALT: reifegrad=REIF Pflicht — blockierte UNREIF-Items komplett, kein Pfad zur Impl.
# NEU: Reifegrad-Check entfernt. SDF Phase 1.1 modusEntscheidung waehlt:
#        UNREIF -> M7 (SC analyse) oder M5/M6 (SC Symbiose)
#        SC-REIF -> M5/M6 (mehr Klaerung)
#        REIF -> M2/M3 (direct I oder TDD)
# expected_pipeline-Default: "IDF+SDF" wenn nicht gesetzt (BL-Items ohne explicit
# Pipeline-Vorgabe gehen den Standard-Pfad).
# ─── Phase 8.5a: Auto-Chain fuer ORPHAN-INDUZIERTEN Re-Cluster (NEU 2026-06-10 BL-298) ───
# Feature-Kollision-Fix: Refit-V3-Loosening (2026-05-17, Z785) verengte das Gate auf from=="direct"
# und schloss den orphan_scan-Pfad (BL-NEW-60) aus -> bei --from=orphan_scan fiel der Lauf in den
# stillen no_chain-Exit (Live 486 v6/v7/v9). User-Entscheidung 2026-06-10: AUTO-BUILD-BOUNDED — der
# Orphan-Re-Cluster baut den neuen Batch autonom weiter (Z924-Intent), gebounded durch INV-IDF-ORPHAN-2
# (>=3 -> HiL). orphan_scan ist der Spezialfall: der Decision-Berater (_SDF_berater_orphan_scan) haelt
# KEINE Kontrolle ueber den Fluss -> IDF MUSS selbst zurueck-chainen.
IF args.from == "orphan_scan" AND args.no_chain != true:
  # orphan_scan_history ist Audit-Trail ALLER Scans -> NUR getriggerte zaehlen (symmetrisch zu
  # Caller _SDF_berater_orphan_scan.md + _SDF_orchestrate_post.md Phase 4.1.5).
  orphan_iters = DF_BATCH_STATE.orphan_scan_history.count(WHERE trigger_recluster=true)
  idf_status   = IDF_PIPELINE_STATE.idf_status   # erwartet "IDF_DONE"
  IF idf_status != "IDF_DONE":
    Logge: "[IDF Phase 8.5a BL-298] kein Orphan-Chain — idf_status={idf_status} (IDF nicht DONE)"
  ELIF orphan_iters >= 3:
    # INV-IDF-ORPHAN-2 mit Recovery-Pfad: KEIN stiller no_chain, sondern aktiver HiL-Alert MIT
    # konkretem Resume-Kommando (feedback_corrective_enforcement — Recovery-Pflicht).
    Logge: "[IDF Phase 8.5a BL-298] Orphan-Loop-Schutz — {orphan_iters}. Re-Cluster fertig, Auto-Chain gestoppt, HiL-Alert"
    SendMessage(user, "[IDF Orphan-Loop-Schutz] {orphan_iters}. Re-Cluster fertig (neuer batch_PL{N}). Auto-Chain gestoppt (INV-IDF-ORPHAN-2). Resume: /_SDF_orchestrate {args.BL_ID} --resume  ODER ABORT (Rest-Orphans als End-of-Story-Items akzeptieren).")
    GOTO Stufe 6        # sauberer Exit MIT aktivem HiL-Hinweis (kein stiller no_chain)
  ELSE:
    Logge: "[IDF Phase 8.5a BL-298] ORPHAN-CHAIN — {orphan_iters} Re-Cluster <3, Glove-Change zu Skill(_SDF_orchestrate, '{args.BL_ID} --resume') (RE-BATCH; SDF Phase 1.1 waehlt M{{N}} fuer neuen batch_PL{N}, INV-MODUS-1 gewahrt)"
    GOTO Stufe_6_with_chain   # wiederverwendet Z822 -> Skill(_SDF_orchestrate, "{BL_ID} --resume")

IF args.from == "direct" AND args.no_chain != true:
  # BL-210 M7 Fix 2026-05-24: routing_decision in DF_BATCH_STATE (autoritativ per BL-165
  # Field-Owner-Tabelle, siehe _help TEIL 8b). A_PIPELINE_STATE-Variante als Backward-Compat-Fallback.
  expected   = DF_BATCH_STATE.routing_decision.expected_pipeline
             ?? A_PIPELINE_STATE.routing_decision.expected_pipeline  # Legacy-Fallback
             ?? "IDF+SDF"
  reifegrad  = A_PIPELINE_STATE.reifegrad                            # nur fuer Logging
  global_hil = _manifest.md.GLOBAL_HIL                               # off | phase | full
  idf_status = IDF_PIPELINE_STATE.idf_status                         # erwartet "IDF_DONE"

  # Gate-Bedingung V3 (loosened): SDF expected + IDF erfolgreich.
  IF "SDF" IN expected AND idf_status == "IDF_DONE":
    # HiL-Gate (BL-173 Refinement 2026-05-10):
    # Nur bei GLOBAL_HIL=off auto-chain ohne Confirm.
    IF global_hil == "off":
      proceed = true
      Logge: "[IDF Phase 8.5 V3] AUTO-CHAIN — HiL=off, expected={expected}, reifegrad={reifegrad} (Modus-Entscheidung delegiert an SDF Phase 1.1)"
    ELSE:
      proceed = HiL_Confirm("Auto-Chain zu SDF? expected={expected} reifegrad={reifegrad} — SDF Phase 1.1 waehlt M{{N}}")
      Logge: "[IDF Phase 8.5 V3] HiL=phase/full — User-Confirm fuer Chain: {proceed}"

    IF proceed:
      Logge: "[IDF Phase 8.5 V3] Glove-Change zu Skill(_SDF_orchestrate, args='{BL_ID} --resume') — SAUBERE Args (BL-ID + --resume), KEIN Kontext-Blob, KEIN --from"
      # KEIN TeamDelete (BL-173 2026-05-10): Team-Lifecycle laeuft durch SDF weiter.
      GOTO Stufe_6_with_chain
    ELSE:
      Logge: "[IDF Phase 8.5 V3] HiL-Confirm abgelehnt — Standard-Exit"
  ELSE:
    Logge: "[IDF Phase 8.5 V3] kein Auto-Chain — expected={expected} OR idf_status={idf_status} (kein SDF erwartet ODER IDF nicht DONE)"

# ─── Stufe 6: TeamDelete (INV-LIFECYCLE-5) ──────────────────────────
LABEL: Stufe 6
Logge: "[IDF Stufe 6] EXIT idf_status={IDF_PIPELINE_STATE.idf_status} bl_id={args.BL_ID}"
TeamDelete team_id="idf-{args.BL_ID}"   # kurzlebig (W7-Constraint)
# BL-349 AK-2 / INV-TEAM-GC-1 (eigener Teardown-Recovery): scheitert TeamDelete mit
# "Cannot cleanup team with N active member(s)" -> tote Worker DIESER Session ->
# `py .claude/scripts/team_gc.py strip idf-{args.BL_ID}` -> TeamDelete erneut (laeuft dann durch).
Set _manifest.md.active_team = null
RETURN 0

LABEL: Stufe_6_with_chain
# (NEU BL-173 2026-05-10) Auto-Chain ohne TeamDelete:
# Team-Lifecycle laeuft durch SDF weiter — SDF spawnt eigenes Team bei Bedarf.
# active_team bleibt vorerst gesetzt (idf-{BL_ID}); SDF Phase 0.5 (falls aktiv)
# uebernimmt + ueberschreibt zu sdf-{BL_ID} oder loescht IDF-Team selbst.
# Direkter Glove-Change ohne explicit Cleanup vermeidet Race-Conditions.
Logge: "[IDF Stufe 6+Chain] HANDOFF idf_status=IDF_DONE bl_id={args.BL_ID} → SDF (kein TeamDelete)"
# INV-AO-CALLER: Skill() direkt vom Lead, nicht Agent-delegiert.
# BL-RESILIENZ 2026-05-29 (DCSRE-486 Live-Stall): args MUSS sauber "{BL_ID} --resume" sein —
# NICHT der GOAL-Prosa-Blob, NICHT das erfundene --from=idf_chain. SDF liest seinen State
# selbst via --resume (DF_BATCH_STATE.current_sub_batch). --resume erfuellt STAB10s Pflicht-Flag
# DIREKT — kein Verlass auf B-Auto-Resume (das war fragil als current_context.py still crashte).
Skill(_SDF_orchestrate, args="{args.BL_ID} --resume")
RETURN 0


SUBROUTINE: ABORT(reason):
  Set IDF_PIPELINE_STATE.idf_status = "ABORTED"
  Set IDF_PIPELINE_STATE.abort_reason = reason
  Logge: "[IDF ABORT] {reason}"
  GOTO Stufe 6
  RETURN 2

SUBROUTINE: resolve_resume_phase(idf_status):
  IF idf_status IN [null, "IDLE"]: RETURN null   # fresh start
  IF idf_status IN ["INIT","SPEC_PARSE","AK_PER_PL","DEP_MATRIX",
                    "CLUSTER","SEQUENCE","BATCH_PLAN","STAGE_PLAN","METRIC_PLAN","TEST_SEARCH","PARALLEL_SUITABILITY","FINAL_SUMMARY"]:
    RETURN idf_status
  RETURN null   # unknown -> restart
```

---

## RESUME-VERHALTEN

| Aktueller Status | Naechste Aktion |
|------------------|-----------------|
| `null` / `IDLE` | Fresh start ab Phase 1 |
| `INIT` | Wiederhole Phase 1 (idempotent dank Berater-Resume-Check) |
| `SPEC_PARSE` | Springe zu Phase 2 |
| `AK_PER_PL` | Springe zu Phase 3.1 (akExtraktion-Cache greift pro AK) |
| `DEP_MATRIX` | Springe zu Phase 4 |
| `CLUSTER` | Springe zu Phase 5 |
| `SEQUENCE` | Springe zu Phase 6 |
| `BATCH_PLAN` | Springe zu Phase 7 |
| `STAGE_PLAN` | Springe zu Phase 7.5 |
| `METRIC_PLAN` | Springe zu Phase 7.6 |
| `TEST_SEARCH` | Springe zu Phase 7.7 |
| `PARALLEL_SUITABILITY` | Springe zu Phase 7.8 |
| `FINAL_SUMMARY` | Springe zu Phase 8.0 |
| `IDF_DONE` | No-Op (NFR-7 Idempotenz) |
| `ABORTED` | Manuelles Reset noetig |

Resume-Idempotenz wird durch Berater selbst abgesichert: Jeder Berater
liest den aktuellen `BERATER_OUTPUTS`-Slot und ueberspringt fertige Arbeit.

---

## RECHECK-GUARD (Anti-Zirkel, INV-LIFECYCLE-2)

`--mode=recheck` + `--from IN [bdf_plan, idf_plan]` SKIPpt Phase 7 batchPlan,
um zu verhindern, dass ein BDF-Recheck einen weiteren IDF-Plan ausloest, der
wiederum BDF triggert. Stattdessen: nur Stats-Update + last_recheck_from.

---

## DRY-RUN-MODUS (BL-088)

`--mode=dryRun` ruft nur `_IDF_berater_init`, schreibt Mock-Report nach
`.claude/output/IDF_DryRun_{BL_ID}_{DATE}.md`, setzt direkt `IDF_DONE`.
Phase 2-7 werden geskippt — keine Spec-Parse, keine PL-Items, keine Matrix.

---

## ORPHAN-INDUZIERTER RE-CLUSTER (`--mode=recluster --orphan-only --sticky-ids`, BL-NEW-60)

**Zweck:** Iterative-Adaptive Pipeline. Wenn SDF Phase 4.1.5 Orphan-Scan
HIGH/CRITICAL Orphans (PL-Level oder Stage-Level) detected, wird IDF mit diesem
Modus aufgerufen — incremental Delta-Update OHNE bestehende DONE-Batches zu beruehren.

**Phasen-Fluss (was laeuft, was skipt):**

```
Phase 1 init:           SKIP (--pl-only implizit, idf_status existiert)
Phase 2 specParse:      SKIP
Phase 3.1 akExtraktion: SKIP (--pl-only)
Phase 3.2 plAggregation: LAUF — aber Delta-Mode:
                        liest Diff(parking-lot.md, BERATER_OUTPUTS.plAggregation.pl_items)
                        nur neue Items werden aggregiert
                        existing Items werden idempotent gemerged (synced-to-model bleibt)
Phase 3.5 validator:    LAUF — nur neue Items validieren
Phase 3.6 itemContext:  LAUF — nur neue Items kontextualisieren
Phase 3.7 modelSync:    SKIP wenn alle neuen Items "synced-to-model"-Marker haben
                        sonst LAUF fuer neue Items only
Phase 4 dependencyAnalyzer: LAUF — neue Items + existing Items in Matrix
                            Sticky-IDs preservieren existing matrix-rows
Phase 5 clustering:     LAUF — nur neue Items clustern in NEUE batch_keys
                        (z.B. batch_PL{N+1}). EXISTING batches UNVERAENDERT.
Phase 6 sequencePlanner: LAUF — neue Batches einsortieren (typisch zwischen
                         current_sub_batch und naechstem PENDING)
Phase 7 batchPlanner:   LAUF — neuen BatchPlan v{N+1} schreiben
                        existing completed_sub_batches/partial_sub_batches bleiben
Phase 7.5 stagePlanner: LAUF — Stages NUR fuer neue Batches setzen
Phase 7.6 metricPlanner: LAUF — Metrics NUR fuer neue Batches
Phase 8.5a IDF_DONE:     Auto-Chain zurueck zu SDF (RE-BATCH) — BL-298: eigener orphan_scan-Zweig
                        (<3 Iterationen: Chain via Stufe_6_with_chain; >=3: HiL-Alert, kein stiller no_chain)
```

**Idempotency-Garantie (INV-IDF-ORPHAN-1):**
- Existierende `batch_keys` in `completed_sub_batches` werden NIE veraendert
- `batch_items_per_batch` fuer existing batches bleibt identisch
- `batch_stages` fuer existing batches bleibt identisch
- `batch_modes`, `modus_begruendung_per_batch` fuer existing batches bleibt identisch
- Nur **neue** batch_keys werden hinzugefuegt (z.B. `batch_PL2`, `batch_PL3` etc.)

**Loop-Termination-Schutz (INV-IDF-ORPHAN-2 — AUSFUEHRBAR in Phase 8.5a, BL-298 2026-06-10):**
- IDF zaehlt `DF_BATCH_STATE.orphan_scan_history.count(WHERE trigger_recluster=true)` als Re-Cluster-Iterations
  (Audit-Trail enthaelt ALLE Scans; nur getriggerte zaehlen — symmetrisch zu Caller _SDF_berater_orphan_scan.md + _SDF_orchestrate_post.md Phase 4.1.5)
- Bei `< 3`: Auto-Chain zurueck zu SDF (RE-BATCH, Auto-Build-Bounded) via Phase 8.5a `GOTO Stufe_6_with_chain`
- Bei `>= 3`: HiL-Alert via SendMessage(user) MIT konkretem Resume-Kommando (`/_SDF_orchestrate {BL_ID} --resume` ODER ABORT) statt stillem no_chain — sauberer Exit via Stufe 6
- User-Decision: ABORT oder akzeptiere Restliche Orphans als End-of-Story-Items

---

## QUICK-START

```
# Normal-Lauf
Skill(_IDF_orchestrate, args="BL-042 bdf-empty-handler")

# Recheck (Anti-Zirkel-Schutz aktiv)
Skill(_IDF_orchestrate, args="BL-042 --mode=recheck --from=bdf_plan")

# Dry-Run (nur Architektur-Validierung, keine Materialisierung)
Skill(_IDF_orchestrate, args="BL-042 --mode=dryRun")

# Resume nach Abbruch (idempotent)
Skill(_IDF_orchestrate, args="BL-042")
```

---

## ABHAENGIGKEITEN

- **BL-142** (in progress): Thin-Manager Refactor (diese Version v0.3.0).
- **BL-076** (DONE): Initial IDF Intermediate Factory (v0.2.0 Vorgaenger).
- **BL-055** (DONE, ABSORBED → BL-209): Phase 3 AK-Materialisierung jetzt in der A-Pipeline
  `_A_berater_plAggregation` + `_A_berater_akExtraktion` (Single-Source). Die IDF-Zwillinge
  `_IDF_berater_plAggregation`/`_IDF_berater_akExtraktion` sind DEPRECATED (BL-209, Tabelle Z184-185) —
  hier nur historisch genannt, NICHT mehr live gerufen [BL-268 Doc-Cleanup].
- **BL-075** (DONE): items_routed_ready Schreibung (Phase 6, BL-075 Schutz).
- **BL-088** (DONE): DRY-RUN-Modus (Universal Pattern Child).

## FOLGE-TASKS

- BL-142 Phase 2D: Berater-Implementierung der `_IDF_berater_validator`
  + `_IDF_berater_itemContext` (derzeit Skelette mit teilweise gefuellter Logik).
- BL-142 Phase 2E: Integration-Test ueber gesamte Pipeline (init -> batchPlan).
- BL-142 Phase 2F: Aufrufer-Anpassung (BDF Phase 2b: `Skill(_IDF_orchestrate)`
  Argumente an neue v0.3.0 Signatur anpassen).
