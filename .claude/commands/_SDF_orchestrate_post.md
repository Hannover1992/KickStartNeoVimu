---
name: _SDF_orchestrate_post
description: /_SDF_orchestrate_post - Post-Phase (Phase 3 + Phase 4) nach I_orchestrate/SC_orchestrate Return. Erzwungener Handschuh-Wechsel vom Implement-Skill, damit Phase 3 nicht via Skill-Context-Override verloren geht.
status: active
version: 1.2.0
created: 2026-05-11
updated: 2026-06-10
feature_anchor: BL-NEW-12
changelog:
  - {version: "1.2.0", date: "2026-06-10", change: "BL-255 AK-7 GAP-Fix: recalibrate-postCollapse-Schritt nach Wave-2-JOIN eingefuegt. Wenn modelSync 3.5c collapsed_ws > 0 meldet, wird _SDF_berater_recalibrate erneut gespawnt damit der srs-Drop same-round modus-wirksam wird (kein Off-by-one). No-Op bei collapsed_ws=0 oder M1. Spiegel der Motor-Variante-b dfc7d5a."}
  - {version: "1.1.1", date: "2026-05-17", change: "Schema-Bugfix Anti-Mega-Worker-Reflex: audit-Events nutzen `event` (NICHT type) + `skill_name` (NICHT command/berater_skill). Detector nutzt SKILL_LOAD-Events filtered by _SDF_berater_*-Prefix (statt WORKER_SPAWN.command, das wegen ORCHESTRATOR_LEVELS-Gap immer 'custom' war). Wave-1-Check tolerant gegen legitime Early-Exits."}
  - {version: "1.1.0", date: "2026-05-17", change: "Anti-Mega-Worker-Reflex: Wave-1-JOIN-Check (INV-POST-4) + Phase-3-Exit-Backstop (INV-POST-5). BL-173 AK-6 in-flight Korrespondenz. Heilt PL-RUN-09 Pattern."}
  - {version: "1.0.0", date: "2026-05-11", change: "Initial — Post-SDF split aus _SDF_orchestrate (BL-NEW-12)"}
type: orchestrator
model_tier: middle
parent: _SDF_orchestrate
chain_position: after_I_or_SC
op: SmallDarkFactory
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE", purpose: "modus, worker_mode, current_round, batch_done"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.architecturalBrief.project_root", purpose: "Build-Sanity Path"}
    - {file: "{WORKING_DIR}/_session_params.md", path: "PROJECT_ROOT", purpose: "Build-Sanity Fallback Path"}
    - {file: "{VAULT}/Backlog/{bl_slug}/2_Model/*.md", path: "mtime", purpose: "model_diff (via recalibrate-Berater)"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items", purpose: "Grundsubstanz + Promotion-Pool"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.completed_sub_batches", purpose: "Round-Markierung (NUR via statusTransition-Berater)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.build_sanity", purpose: "Phase 3.0.5 Output"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "audit.jsonl", purpose: "Wave-FORK/JOIN + Phase-3-Step-Audits"}
    - {file: "{VAULT}/Libraries/PatternLibrary/", purpose: "Wave 3 PT_promoteFromPL (via batchEnde)"}
    - {file: "{VAULT}/Libraries/SemanticLibrary/", purpose: "Wave 3 SL_promoteFromPL (via batchEnde)"}
exit_routes:
  - target: _SDF_orchestrate
    trigger: "decision in {RE-BATCH}"
    args: "{BL_ID} --resume --next-batch"
  - target: _IDF_orchestrate
    trigger: "decision == SOFT-REPRIO"
    args: "{BL_ID} {BL_SLUG} --mode=recluster --from=sdf_drift"
  - target: _IDF_orchestrate
    trigger: "decision == ROLLBACK"
    args: "{BL_ID} {BL_SLUG} --mode=recheck --from=sdf_finish"
  - target: _BDF_orchestrate
    trigger: "decision == TERMINATE"
    args: "(BDF picks up via batch_done signal)"
---

## BL-173 Manifest-Routing (NEU 2026-05-18)

**Manifest-Scope-Split aktiv** (siehe BL-173, INV-MANIFEST-SPLIT-1..4):

| State-Block | Heimat | Helper |
|---|---|---|
| DF_PIPELINE_STATE | `{bl_folder}/_manifest.md` | `manifest_reader.read_bl_block(bl_id, "DF_PIPELINE_STATE")` |
| DF_BATCH_STATE | `{bl_folder}/_manifest.md` | `manifest_reader.read_bl_block(bl_id, "DF_BATCH_STATE")` |
| BERATER_OUTPUTS | `{bl_folder}/_manifest.md` | `manifest_reader.read_bl_block(bl_id, "BERATER_OUTPUTS")` |
| GLOBAL_* (read-only) | `{vault_root}/_factory_manifest.md` | `manifest_reader.read_factory_block("GLOBAL_*")` |

**Pfad-Aufloesung:**
- Factory-State: `manifest_reader.read_factory_block(...)` ODER direkt `{vault_root}/_factory_manifest.md`
- BL-State: `manifest_reader.read_bl_block(bl_id, ...)` ODER direkt `{bl_folder}/_manifest.md`
- Legacy-Fallback aktiv solange `is_split_active() == False` (1-Sprint-Uebergang)

**Migration:** `py -3 .claude/scripts/migrate_manifest_split.py migrate --vault-root="..." --rollback-tag=YYYY-MM-DD`

# /_SDF_orchestrate_post — Post-Phase Orchestrator (Phase 3 + Phase 4)

> **NEU 2026-05-11 (BL-NEW-12):** Eigener Skill für Phase 3 + 4, von I_orchestrate/SC_orchestrate
> per Handschuh-Wechsel gerufen. Loest das Skill-Context-Override-Problem
> ("Lead vergisst Phase 3 nach I-Skill-Return"). Process-Compliance via Skill-Load-Pflicht.

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_orchestrate_post (Phase 3 + Phase 4)                      ║
╠══════════════════════════════════════════════════════════════════════════╣
║  AUFRUFER: _I_orchestrate (Nachphase, letzter Schritt PFLICHT)           ║
║            _SC_orchestrate (analog, falls parent=="SDF")                 ║
║                                                                          ║
║  NICHT-AUFRUFER: BDF, Lead direkt, andere Pipelines                     ║
║                  (Aufruf ausserhalb der I/SC-Kette ist INV-Bruch)        ║
║                                                                          ║
║  EINTRITTSZUSTAND:                                                       ║
║    - Phase 2 EXECUTION DISPATCH ist done (Code geschrieben)              ║
║    - I-Pipeline returned (alle scope-konformen Steps gelaufen)           ║
║    - DF_BATCH_STATE.current_sub_batch_id ist gesetzt                     ║
║    - BERATER_OUTPUTS.architecturalBrief existiert (von Pre-SDF)          ║
║                                                                          ║
║  AUSTRITTSZUSTAND:                                                       ║
║    - Genau EIN Exit-Skill aufgerufen (RE-BATCH/SOFT-REPRIO/ROLLBACK/TERM)║
║    - audit.jsonl HANDOVER_TRACE komplett                                 ║
║    - Round-Commit via stage_orchestrate persistiert                      ║
║                                                                          ║
║  INVARIANTEN:                                                            ║
║    INV-POST-1 (NEU): Post-SDF darf NIE inline returnen — IMMER via       ║
║                       expliziten Skill(_Exit_..., ...) Call.            ║
║    INV-POST-2 (NEU): Phase 3 Schritte 3.0.5/Wave1/Wave2/3.4/4 sind       ║
║                       PFLICHT — kein Lead-Inline-Skip erlaubt.           ║
║    INV-PM-1: Worker-Pflicht — alle Phase-3-Schritte via Berater-Spawn.   ║
║    INV-HANDOVER-1 (NEU): Caller-Skill (I/SC) MUSS Post-SDF aufgerufen    ║
║                       haben — GUARD-ENFORCED via guard_sdf_post_handoff  ║
║                       (BL-427, PreToolUse-Hook, enforce-AFTER-write).    ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## WORKER-SPAWN-PATTERN (INV-SPAWN = INV-PM-5-aequivalent)

INV-SPAWN (= INV-PM-5-aequivalent, AKTIVER STRUKTURVERTRAG): Die Phase-3.x-
  Berater-Calls (recalibrate / postItem / statusTransition / modelSync /
  batchEnde / stageElevation / post_sc_pl_resync / loopDecision / orphan_scan)
  MUESSEN ueber Worker-Spawn aufgerufen werden — der Team Lead laedt diese
  Berater-Skills NIE selbst inline. Pseudocode-Notation
  "Skill(_SDF_berater_X, args=...)" wird semantisch interpretiert als:
     Agent(subagent_type=tier, prompt="Lade Skill _SDF_berater_X und fuehre
     Vertrag aus + schreibe BERATER_OUTPUTS.{phase}.{status,exit_code,
     last_berater} + stirb", team_name="sdf-{NAME}")
  Datenfluss = Vertraege (Berater lesen/schreiben Vault-Vertragsdateien);
  Manifest = NUR Zustand (exit_code-Marker). Lead liest NIE Berater-Payload aus
  dem Manifest, nur den Zustand. (Spiegelt _I_orchestrate WORKER-SPAWN-PATTERN
  + A INV-PM-5 + IDF INV-SPAWN.)

Jedes `Skill(_SDF_berater_X, args=...)` der Phase-3.x-Steps unten ist
KURZSCHRIFT fuer:

  Agent(
    subagent_type="general-sonnet" | "general-haiku" | "general-purpose",
                                      # Tier laut Berater-Spec (Phase-3.x: general-sonnet)
    description="SDF-post Phase {N} {berater_name}",
    prompt="""
      Du bist kurzlebiger Worker fuer SDF-post Phase {N}.
      ENV: CLAUDE_BL_ID={bl_id}

      AUFGABE: Lade Skill _SDF_berater_X via Skill-Tool und fuehre den dort
      definierten Vertrag aus mit args="{args}".

      REGELN:
      - W7-Constraint: KEIN Sub-Agent-Spawning durch dich.
      - Schreibe BERATER_OUTPUTS.{phase}.{status,exit_code,last_berater} ins _manifest.md.
      - SendMessage an "team-lead" mit Ergebnis-Summary.
      - Worker stirbt nach Skill-Ausfuehrung.
    """,
    team_name="sdf-{NAME}"
  )

**Verbotene Anti-Pattern:**
- (X) Team Lead ruft `Skill(_SDF_berater_X)` direkt auf -> Direkt-Load (Megaworker)
- (X) Team Lead liest Berater-Skill-Markdown selbst und fuehrt Phase-3.x inline aus
- (OK) Team Lead spawnt Worker via Agent(), Worker laedt Skill, schreibt Slot, stirbt

**DATENFLUSS-PRINZIP (INV-DATA-Aequivalent):** Lead liest NIE Berater-Payload,
nur den Zustand (`exit_code`-Marker im BERATER_OUTPUTS-Slot). Die fachlichen
Outputs (Modus-Entscheidung, PL-Promotion, Stage-Plan) reisen via Vault-Vertrags-
dateien zwischen den Beratern — NICHT als Lead-Inline-Payload.

**SCOPE-NOTE:** Diese INV-SPAWN-Direktive deckt die Phase-3.x-`_SDF_berater_*`-Calls.
NICHT erfasst (KEINE Berater, bleiben Lead-Skill-Load per INV-AO-CALLER):
`Skill(_stage_orchestrate)` (3.3.5 Commit, separater Orchestrator),
`Skill(_I_/_IDF_/_A_/_SDF_orchestrate)` (Exit-Routing WEG1/2/3), sowie der
`Agent(...)` BUILD-Sanity-Spawn in Phase 3.0.5 (bereits Agent()-Spawn, KEIN Berater).

**INV-MODUS-Reminder:** Worker darf modus-Feld NICHT setzen ausser via _SDF_berater_modusEntscheidung (BL-165 INV-MODUS-1).

---

## STATE-MACHINE

```
INIT -> BUILD_SANITY_DONE -> WAVE1_DONE -> WAVE2_DONE -> COMMIT_DONE
     -> BATCHENDE_DONE -> STAGE_ELEVATION_DONE -> PL_RESYNC_DONE
     -> LOOPDECISION_DONE -> ORPHAN_SCAN_DONE -> EXIT_ROUTED
     -> COMPLETED | ABORTED_PROCESS_VIOLATION (exit_code=99, any phase)
```

**exit_code-Konvention:** Jede `<PHASE>_DONE`-Transition setzt `exit_code=0` (0=DONE).
`exit_code=2` = modelSync-FAIL (bestehend erhalten, Phase 3.5). Prozess-/Vertrags-
Verletzung in JEDER Phase -> `phase="ABORTED_PROCESS_VIOLATION"` + `exit_code=99`
(kein neu erfundenes Schema — derselbe Marker wie im I-Pilot STATE-MACHINE-Block;
hier als Block-Level-Konvention generalisiert: `exit_code=0`=DONE, `exit_code=2`=modelSync-FAIL,
`exit_code=99`=ABORTED_PROCESS_VIOLATION).

**[M2-SEAM-HARDENED] (BL-469 — Spiegel I-Pilot BL-466):** Die Transitions-Kette haengt
am STATE-HANDOFF, NICHT an einem TDD-/Modus-Flag. Modus-unabhaengig (M1-M8) — der State-Seam
traegt die Phasen-Trennung in JEDEM Modus identisch. Skip degeneriert zu einem
`exit_code=0`-Durchlauf (legitime konditionale Skips: C5-SKIP/C7-SKIP/single_batch/
not_last_round) — KEINE Phase wird aus der Kette entfernt. Wuerde man eine Phase
modus-konditional entfernen, haengt der Seam wieder an TDD/Modus (Anti-Pattern) und der
M2-Megaworker bleibt offen. TDD/RED!=GREEN ist damit nur noch der **2. Notnagel**
(Handoff-/Guard-Schicht: guard_sdf_post_handoff / guard_agent_prompt_validator); der
**primaere** Megaworker-Schutz ist dieser state-getriebene Vertrag (BERATER_OUTPUTS-Slot
pro Step + State-Handoff + [GATE P]-exit_code-Gate).

| Phase | Status-Wert (DONE) | Berater (Spawn, KURZSCHRIFT) | Skip-Bedingung (erhalten) |
|-------|---------------------|------------------------------|---------------------------|
| 3.0.5 build_sanity | `BUILD_SANITY_DONE` | (Agent BUILD-Sanity, KEIN Berater) | M2/M3 ohne worker-mode → SKIP |
| 3.1 recalibrate | `WAVE1_DONE` | `_SDF_berater_recalibrate` | C5-SKIP modus=M1 |
| 3.2 postItem | `WAVE1_DONE` | `_SDF_berater_postItem` | — (immer) |
| 3.3 statusTransition | `WAVE2_DONE` | `_SDF_berater_statusTransition` | C7-SKIP gap_ready=false |
| 3.5 modelSync | `WAVE2_DONE` | `_SDF_berater_modelSync` | single_batch (current_sub_batch_id=null) |
| 3.5 postCollapse | `WAVE2_DONE` | `_SDF_berater_recalibrate` (re-run) | collapsed_ws=0 OR M1 |
| 3.3.5 commit | `COMMIT_DONE` | (`_stage_orchestrate`, KEIN Berater) | — |
| 3.4 batchEnde | `BATCHENDE_DONE` | `_SDF_berater_batchEnde` | not_last_round |
| 3.6.1 stageElevation | `STAGE_ELEVATION_DONE` | `_SDF_berater_stageElevation` | — (immer) |
| 3.6b post_sc_pl_resync | `PL_RESYNC_DONE` | `_SDF_berater_post_sc_pl_resync` | sc_cycle_done=false → SKIP (Berater-intern) |
| 4.1 loopDecision | `LOOPDECISION_DONE` | `_SDF_berater_loopDecision` | — (immer) |
| 4.1.5 orphan_scan | `ORPHAN_SCAN_DONE` | `_SDF_berater_orphan_scan` | orphan_scan_active=false OR TERMINATE |
| END | `COMPLETED` / `ABORTED_PROCESS_VIOLATION` | — | — |

> **SCOPE-NOTE (BL-469):** Dieser Block DEKLARIERT die State-Kette + koppelt die Phase-3.x-
> Spawns an exit_code-Gates (additiv). Er entfernt KEINE bestehende Skip-/Branch-/Check-Logik,
> reduziert KEINE LOC und macht KEINEN Step modus-konditional. WEG B altmodisch (kein Motor).

---

## Aufruf

```
Skill(_SDF_orchestrate_post, args="{NAME} [--vault={VAULT}] [--worker-mode]")

Parameter:
  {NAME}          Feature-Name / BL-ID (Story-Identifier des aktuellen Backlog-Items)
  --vault         Optional, Vault-Root (Fallback aus _session_params)
  --worker-mode   Optional, propagiert aus I-Pipeline (beeinflusst Build-Sanity-Path)

Vorbedingung:
  - _I_orchestrate ODER _SC_orchestrate (parent=SDF) ist done
  - Letzter Step des Callers ist DIESER Skill-Aufruf (INV-HANDOVER-1)
  - Hinweis: guard_sdf_post_handoff.py (BL-427) BLOCKIERT das naechste _SDF_orchestrate-Resume
    wenn dieses Skill-Load NICHT im audit.jsonl sichtbar ist (enforce-AFTER-write-Pattern)

Ausgabe:
  - Genau EINER der Exit-Skills wird gerufen
  - Manifest persistiert
  - audit.jsonl ergaenzt
```

---

## PHASE 0: ENTRY-LOG (BL-NEW-12 Audit-Trail)

```
# Audit-Eintrag fuer SKILL_LOAD — Lead-Skip-Detection via /_sanity_check_dynamic
# (PIPELINE_CALL_STACK-Check entfernt — Feld wird nicht maintained, daher
#  vereinfacht auf reines Skill-Load-Audit).
audit_jsonl_append({
  type: "SKILL_LOAD",
  skill: "_SDF_orchestrate_post",
  round: DF_BATCH_STATE.current_sub_batch_id,
  timestamp: ISO
})

Logge: "[POST-SDF] Phase 3 + 4 starting for round={DF_BATCH_STATE.current_sub_batch_id}"
```

---

## PHASE 3.0.5: BUILD-Sanity (NEU, BL-NEW-NN M1-Compile-Check)

```
# Modus-bedingt: M1 hat KEIN Inline-TDD (kein RED/GREEN aus _I_orchestrate scope=skeleton)
# und kein automatisches dotnet build via T_orchestrate. Ohne Sanity-Check landet
# ein Typo unentdeckt als DONE im Manifest. Pflicht: minimum dotnet build.
#
# M2/M3 ohne worker-mode: T_orchestrate fuehrt build implizit aus → SKIP hier.
# M2/M3 mit worker-mode (kein T_orchestrate-Aufruf): build-sanity wie M1.

batch_modus = DF_BATCH_STATE.modus
worker_mode = DF_BATCH_STATE.worker_mode ?? false
needs_build_sanity = (batch_modus == "M1") OR (worker_mode == true AND batch_modus != "M8")

IF needs_build_sanity:
  project_root = BERATER_OUTPUTS.architecturalBrief.project_root
                  ?? Read({WORKING_DIR}/_session_params.md).PROJECT_ROOT
                  ?? WORKING_DIR

  Logge: "[Phase-3.0.5] BUILD-Sanity (modus={batch_modus}, worker_mode={worker_mode})"
  Agent(
    subagent_type="general-haiku",
    description="Phase-3.0.5 BUILD-Sanity",
    prompt="cd '{project_root}' && dotnet build --no-incremental --nologo --verbosity:minimal
            Erwartung: Exit-Code 0. Falls FAIL: SendMessage 'STUCK: build failed at {file}:{line}'"
  )
  # Output: BERATER_OUTPUTS.build_sanity.{status: PASS|FAIL, errors: [...]}

  audit_jsonl_append({type: "PHASE_3_STEP", step: "3.0.5", status: BERATER_OUTPUTS.build_sanity.status})

  IF BERATER_OUTPUTS.build_sanity.status == "FAIL":
    Logge FEHLER: "[Phase-3.0.5] BUILD FAIL — Round-Rollback nach Phase 4 loopDecision"
    DF_BATCH_STATE.last_failure = "build_sanity"
    → GOTO Phase 4 (loopDecision mit ROLLBACK-Hint)

  Logge: "[Phase-3.0.5] BUILD PASS — proceed to Wave 1"
ELSE:
  Logge: "[Phase-3.0.5] SKIP — T_orchestrate uebernimmt Build implizit (modus={batch_modus})"
  audit_jsonl_append({type: "PHASE_3_STEP", step: "3.0.5", status: "SKIP", reason: "modus_{batch_modus}_no_worker_mode"})
```

---

## WAVE 1 (PARALLEL): SCHRITT 3.1 + 3.2

```
# Lead-Side FORK: spawnt 3.1 und 3.2 PARALLEL (zwei Skill-Calls in einem Dispatch-Block).
# Disjunkte BERATER_OUTPUTS-Felder → kein Write-Konflikt.

Logge: "[Wave-1 FORK] 3.1 recalibrate + 3.2 postItem parallel"
audit_jsonl_append({type: "WAVE_FORK", wave: 1, parallel_skills: ["recalibrate", "postItem"], timestamp: ISO})

PARALLEL_DISPATCH:
  TRACK_3_1:
    # [GATE P1] exit_code-Check Vorgaenger (build_sanity, Wave-1-Entry) VOR diesem Spawn
    #   (toleriert exit_code=0-Skip-Durchlauf; prueft NUR ABORT-Bedingung == 99, NICHT != 0):
    IF BERATER_OUTPUTS.build_sanity.exit_code == 99: ABORT "[INV-SPAWN] Phase 3.1 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)"
    IF DF_BATCH_STATE.modus != "M1":
      # [INV-SPAWN] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline:
      Skill(_SDF_berater_recalibrate, args="{NAME}")
      # Worker schreibt BERATER_OUTPUTS.recalibrate.{status,exit_code,last_berater} + stirbt.
      # Berater hat 2-stufige Skip-Logik:
      #   Schritt 0:  M1-Skip (BL-014 ADR)
      #   Schritt 0.5: Early-Exit-Gate (BL-NEW-7) — model_diff || PL-Grundsubstanz
    ELSE:
      Logge: "[C5-SKIP] modus=M1 — kein Recalibrate (BL-014 ADR)"
    audit_jsonl_append({type: "PHASE_3_STEP", step: "3.1", status: "DONE"})

  TRACK_3_2:
    # [GATE P2] exit_code-Check (Wave-1-FORK-intern, disjunkt zu 3.1) VOR diesem Spawn (== 99 ABORT, Skip-tolerant):
    IF BERATER_OUTPUTS.build_sanity.exit_code == 99: ABORT "[INV-SPAWN] Phase 3.2 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)"
    # [INV-SPAWN] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline:
    Skill(_SDF_berater_postItem, args="{NAME}")
    # Worker schreibt BERATER_OUTPUTS.postItem.{status,exit_code,last_berater} + stirbt.
    audit_jsonl_append({type: "PHASE_3_STEP", step: "3.2", status: "DONE"})

# ── JOIN Wave 1 ──
Logge: "[Wave-1 JOIN] aggregating outputs"
audit_jsonl_append({type: "WAVE_JOIN", wave: 1, timestamp: ISO})

# [2. NOTNAGEL — BL-469] Dieser POST-HOC ANTI-MEGA-WORKER-CHECK ist nach AK-3 (STATE-MACHINE + [GATE P])
# der REDUNDANTE 2. Notnagel (analog TDD im I-Pilot [M2-SEAM-HARDENED]). PRIMAERER Schutz = state-getriebener
# Vertrag (BERATER_OUTPUTS-Slot pro Step + [GATE P]-exit_code-Gate). Reflex -> Struktur, hier als Backstop belassen.
# ─── ANTI-MEGA-WORKER CHECK (NEU 2026-05-17 v1.1.1, BL-173 AK-6 Reflex) ───
# Detektor: SKILL_LOAD-Events fuer _SDF_berater_* Skills (vom Worker-Kontext
# nach Agent()-Spawn). Wenn erwartete Berater FEHLEN im audit-Trail → Lead
# hat sie inline ausgefuehrt statt zu spawnen.
#
# Audit-Schema-Kontrakt (audit_hook.py Z313-321):
#   {"event": "SKILL_LOAD", "skill_name": "...", "ts": "...", ...}
# Schluesselfelder: `event` (NICHT type), `skill_name` (NICHT skill), `ts` (NICHT timestamp)
#
# Warum SKILL_LOAD statt BERATER_OUTPUTS-presence: recalibrate hat legitime
# Early-Exit-Pfade (M1-Skip + model_diff-Gate). Wenn Worker GESPAWNT wurde
# aber early-exitete → SKILL_LOAD existiert, BERATER_OUTPUTS evtl. nicht.
# SKILL_LOAD = "wurde der Pfad gestartet" ist truthier als Output-Presence.
#
# Warum nicht WORKER_SPAWN-Event: detect_command_in_agent() (audit_hook.py
# Z188-196) sucht nur ORCHESTRATOR_LEVELS, kennt _SDF_berater_* nicht →
# command-Feld waere "custom" fuer alle Beraters, Distinct-Count broken.

audit_path = ".claude/audit/audit.jsonl"
audit_events = [json.loads(line) for line in Read(audit_path).split("\n") if line.strip()]

# Phase-0-Entry: SKILL_LOAD von _SDF_orchestrate_post selbst (vom Lead-Skill-Call)
phase_0_loads = [e for e in audit_events
                  if e.get("event") == "SKILL_LOAD"
                  AND e.get("skill_name") == "_SDF_orchestrate_post"]
phase_0_ts = phase_0_loads[-1].get("ts") if phase_0_loads else None

expected_beraters = ["_SDF_berater_postItem"]  # 3.2 IMMER
IF DF_BATCH_STATE.modus != "M1":
  expected_beraters.append("_SDF_berater_recalibrate")  # 3.1 nur wenn non-M1

# Hat Worker den Berater geladen? (SKILL_LOAD vom Worker-Kontext nach Spawn)
loaded_beraters = set(
  e["skill_name"] for e in audit_events
  if e.get("event") == "SKILL_LOAD"
  AND isinstance(e.get("skill_name"), str)
  AND (phase_0_ts is None OR e.get("ts", "") > phase_0_ts)
)
missing_spawns = [b for b in expected_beraters if b not in loaded_beraters]

IF len(missing_spawns) > 0:
  Logge FEHLER: "[ANTI-MEGA-WORKER] Wave-1-JOIN missing Berater-Spawns: {missing_spawns}"
  Logge FEHLER: "[ANTI-MEGA-WORKER] Lead inlined Phase 3.1/3.2 statt Berater zu spawnen."
  Logge FEHLER: "[ANTI-MEGA-WORKER] INV-PM-1 + INV-POST-2 Violation."
  audit_jsonl_append({
    "event": "MEGA_WORKER_DETECTED",
    "phase": "Wave_1_JOIN",
    "missing_spawns": missing_spawns,
    "expected": expected_beraters,
    "loaded": list(loaded_beraters),
    "modus": DF_BATCH_STATE.modus,
    "severity": "HIGH",
    "bl_reference": "BL-173_AK6_in_flight_reflex"
  })
  DF_BATCH_STATE.last_failure = "anti_mega_worker_wave1"
  IF GLOBAL_HIL == "off":
    Logge WARNUNG: "[ANTI-MEGA-WORKER] HiL=off → Pipeline-Continue, Phase 4 bekommt ABORT-Hint."
    → GOTO Phase 4 (loopDecision via last_failure)
  ELSE:
    AskUserQuestion(
      "MEGA-WORKER detected: Wave-1 ohne Berater-Spawns {missing_spawns}.\n"
      "Lead hat Phase 3.1/3.2 inline ausgefuehrt statt Workers zu spawnen.\n"
      "  [RESPAWN]  Wave 1 nochmal sauber via Berater-Spawns\n"
      "  [CONTINUE] Akzeptieren (loggt INV-PM-1-Violation)\n"
      "  [ABORT]    Pipeline abbrechen, Lead-Self-Review noetig"
    )
ELSE:
  audit_jsonl_append({"event": "WAVE_1_JOIN_CHECK_OK", "loaded_beraters": list(expected_beraters)})

gap_ready = BERATER_OUTPUTS.postBatch_aggregate.gap_ready
IF NOT gap_ready:
  Logge: "[Wave-1] Batch nicht ready (GAP={BERATER_OUTPUTS.postBatch_aggregate.gap_percent}%) - Loop continues"
```

---

## WAVE 2 (PARALLEL): SCHRITT 3.3 + 3.5

```
Logge: "[Wave-2 FORK] 3.3 statusTransition + 3.5 modelSync parallel"
audit_jsonl_append({type: "WAVE_FORK", wave: 2, parallel_skills: ["statusTransition", "modelSync"], timestamp: ISO})

PARALLEL_DISPATCH:
  TRACK_3_3:
    # [GATE P3] exit_code-Check Vorgaenger (postItem / postBatch_aggregate.gap_ready) VOR Spawn (== 99 ABORT, Skip-tolerant):
    IF BERATER_OUTPUTS.postItem.exit_code == 99: ABORT "[INV-SPAWN] Phase 3.3 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)"
    IF BERATER_OUTPUTS.postBatch_aggregate.gap_ready == true:
      # [INV-SPAWN] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline:
      Skill(_SDF_berater_statusTransition, args="{NAME}")
      # Worker schreibt BERATER_OUTPUTS.statusTransition.{status,exit_code,last_berater} + stirbt.
    ELSE:
      Logge: "[C7-SKIP] gap_ready=false — statusTransition uebersprungen"
    audit_jsonl_append({type: "PHASE_3_STEP", step: "3.3", status: "DONE"})

  TRACK_3_5:
    IF DF_BATCH_STATE.current_sub_batch_id == null:
      Logge: "[SDF-modelSync] SKIP single_batch_path"
      audit_jsonl_append({type: "PHASE_3_STEP", step: "3.5", status: "SKIP", reason: "single_batch"})
    ELSE:
      # [GATE P4] exit_code-Check Vorgaenger (statusTransition, Wave-2-FORK disjunkt) VOR Spawn (== 99 ABORT, Skip-tolerant):
      IF BERATER_OUTPUTS.statusTransition.exit_code == 99: ABORT "[INV-SPAWN] Phase 3.5 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)"
      # [INV-SPAWN] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline:
      Skill(_SDF_berater_modelSync, args="{NAME} {batch_key}")
      # Worker schreibt BERATER_OUTPUTS.modelSync_round_{batch_key}.{status,exit_code,last_berater} + stirbt.
      sync_result = BERATER_OUTPUTS.modelSync_round_{batch_key}
      IF sync_result.exit_code == 2:
        Logge FEHLER: "[SDF-modelSync] FAIL — abort outer-loop"
        DF_BATCH_STATE.last_failure = "model_sync"
      audit_jsonl_append({type: "PHASE_3_STEP", step: "3.5", status: "DONE"})

# ── JOIN Wave 2 ──
Logge: "[Wave-2 JOIN] aggregating outputs"
audit_jsonl_append({type: "WAVE_JOIN", wave: 2, timestamp: ISO})

IF DF_BATCH_STATE.last_failure == "model_sync":
  → GOTO Phase 4 (loopDecision mit ABORT)

# ── recalibrate-postCollapse (BL-255 AK-7 GAP-Fix, 2026-06-10 — Spiegel der Motor-Variante-b dfc7d5a) ──
# Wave-1-recalibrate (3.1) lief auf prä-Kollaps-Stand: modelSync 3.5c transitiert W{n} → AKTIV (BESTAETIGT)
# ERST in Wave 2. Wenn collapsed_ws > 0 sind frische srs_weight-0.0-Traeger vorhanden, die recalibrate 3.1
# noch nicht sah. Der Re-Run macht den 3.5c-Kollaps same-round modus-wirksam (kein Off-by-one).
# INV-MODUS-1 KONFORM: dieser Schritt delegiert an _SDF_berater_recalibrate; er entscheidet selbst keinen Modus.
# ADDITIV: kein Step entfernt, kein Order-Swap (modelSync benoetigt recalibrate-Outputs der aktuellen Round).
collapse_ws = sync_result.confirm_collapse.collapsed_ws ?? 0

IF collapse_ws > 0 AND DF_BATCH_STATE.modus != "M1":
  Logge: "[recalibrate-postCollapse] collapsed_ws={collapse_ws} — Re-Run recalibrate auf POST-Kollaps-W-Status (BL-255 AK-7)"
  audit_jsonl_append({
    type: "PHASE_3_STEP",
    step: "3.5_recalibrate_postcollapse",
    collapsed_ws: collapse_ws,
    trigger: "modelSync_3.5c_non_empty",
    bl_reference: "BL-255_AK7_GAP-Fix"
  })
  # [GATE P5] exit_code-Check Vorgaenger (modelSync_round, collapsed_ws-Quelle) VOR Re-Spawn (== 99 ABORT, Skip-tolerant):
  IF BERATER_OUTPUTS.modelSync_round_{batch_key}.exit_code == 99: ABORT "[INV-SPAWN] Phase 3.5-postCollapse ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)"
  # [INV-SPAWN] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline (recalibrate Re-Run):
  Skill(_SDF_berater_recalibrate, args="{NAME} --reason=postCollapse --collapsed_ws={collapse_ws}")
  # Worker schreibt BERATER_OUTPUTS.recalibrate.{status,exit_code,last_berater} (re-run) + stirbt.
  # Idempotenter Recompute auf frischem W-Status (BESTAETIGT-Familie → srs_weight 0.0).
  # metric_per_batch[{batch_key}] wird danach post-Kollaps-frisch fuer Phase 1.1 der naechsten Round.
  audit_jsonl_append({type: "PHASE_3_STEP", step: "3.5_recalibrate_postcollapse", status: "DONE"})
ELSE:
  Logge: "[recalibrate-postCollapse] collapsed_ws={collapse_ws} — No-Op (kein Kollaps oder M1)"
  audit_jsonl_append({
    type: "PHASE_3_STEP",
    step: "3.5_recalibrate_postcollapse",
    status: "SKIP",
    reason: IF collapse_ws == 0 THEN "no_collapse" ELSE "modus_M1"
  })

Logge: "[Phase-3] Wave 1 + Wave 2 + postCollapse fertig — proceed to stage_orchestrate (Commit)"
```

---

## SCHRITT 3.3.5: stage_orchestrate (Commit pro Round)

```
# Per-Round-Commit: jede abgeschlossene Round wird isoliert gestaged + committed.
# Verhindert Mega-Diffs. Falls Round-1 + Round-2 in einem Branch laufen, sind sie
# getrennte Commits → einfache Rollback-Granularitaet.

Skill(_stage_orchestrate, args="{NAME} --round={DF_BATCH_STATE.current_sub_batch_id} --message='SDF Round {round} {batch_modus} {ak_list}'")
# Output: BERATER_OUTPUTS.stage_orchestrate.{commit_sha, files_staged, message}

audit_jsonl_append({type: "PHASE_3_STEP", step: "3.3.5_commit", status: "DONE", commit: BERATER_OUTPUTS.stage_orchestrate.commit_sha})
Logge: "[Phase-3.3.5] Round commit: {BERATER_OUTPUTS.stage_orchestrate.commit_sha}"
```

---

## SCHRITT 3.4: Batch-Abschluss (NUR wenn letzte Round im Batch)

```
# 3.4 läuft nur EINMAL pro Batch (nach allen Rounds).
# Interner Aufruf: _SDF_berater_batchEnde (Wave 3 PT+SL parallel).
#
# BL-NEW-12 Fix B1 (2026-05-11): is_last_round verwendet existierendes Schema
# (completed_sub_batches + batch_items_per_batch), NICHT undefinierte _index/_total Felder.

completed_count = len(DF_BATCH_STATE.completed_sub_batches ?? [])
total_count     = len(DF_BATCH_STATE.batch_items_per_batch.keys() ?? [])
# Diese Round wird gleich completed → +1 fuer den Check
is_last_round = (completed_count + 1 >= total_count)

IF is_last_round:
  Logge: "[Phase-3.4] Letzte Round im Batch ({completed_count+1}/{total_count}) — batchEnde + Wave 3 PT/SL"
  # [GATE P6] exit_code-Check Vorgaenger (modelSync / Wave-2-JOIN) VOR Spawn (== 99 ABORT, Skip-tolerant):
  IF BERATER_OUTPUTS.modelSync_round_{batch_key}.exit_code == 99: ABORT "[INV-SPAWN] Phase 3.4 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)"
  # [INV-SPAWN] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline:
  Skill(_SDF_berater_batchEnde, args="{NAME}")
  # Worker schreibt BERATER_OUTPUTS.batchEnde.{status,exit_code,last_berater} + stirbt.
  # batchEnde fuehrt INTERN aus:
  #   - Transitions-Guard (Checklist)
  #   - BDF_BATCH_DONE Signal
  #   - Wave 3 PARALLEL: PT_promoteFromPL + SL_promoteFromPL (BL-NEW-10)

  audit_jsonl_append({type: "PHASE_3_STEP", step: "3.4", status: BERATER_OUTPUTS.batchEnde.next_action})

  IF BERATER_OUTPUTS.batchEnde.next_action == "ABORTED":
    DF_BATCH_STATE.last_failure = "batch_ende_blocked"
    → GOTO Phase 4 (loopDecision mit ABORT)
ELSE:
  Logge: "[Phase-3.4] SKIP — nicht letzte Round ({completed_count+1} von {total_count})"
  audit_jsonl_append({type: "PHASE_3_STEP", step: "3.4", status: "SKIP", reason: "not_last_round"})
```

---

## SCHRITT 3.6: stageElevation-Berater (BL-171 + BL-NEW-44, NEU 2026-05-11)

> **BL-NEW-44 Anti-Bypass (Case-Anchor `.claude/_parking-lot.md`):**
> Lead inline'te zuvor den Pre-SDF Outer-Loop Code aus `_SDF_orchestrate.md`
> (`completed_stages_per_batch[batch_key].append(current_stage); current_stage = next_stage`)
> ohne den Berater zu spawnen + ohne durable Manifest-Update. Folge: Manifest stale,
> Stage nicht commited, kein audit-Trail, ELEVATE-Decision ohne Validation.
>
> **BL-NEW-44.1 Plan-Mutation-Block (Case-Anchor `.claude/_parking-lot.md`):**
> Lead mutierte `batch_stages[batch_key]` (z.B. von `[1, 3]` auf `[1]`) BEVOR stageElevation lief
> (oft Begruendung: "HiL-Deferral, Setup fehlt"). Anschliessend lief stageElevation auf
> falsifiziertem Plan und gab BATCH_DONE statt ELEVATE zurueck. Stage wurde silently skipped.
> Pattern-Drift wie BL-NEW-41 Mega-Worker. Plus Manifest erhielt Duplicate-Keys durch
> wiederholte Lead-Inline-Schreibungen.
>
> **Fix:** stageElevation laeuft als Pflicht-Step IN Post-SDF (statt nur in Pre-SDF
> Outer-Loop Phase 2.2). Bei `next_action == ELEVATE` macht Post-SDF den
> Skill-Wechsel zu I_orchestrate DIREKT — kein Pre-SDF-Round-Trip noetig. Damit
> entfaellt das Bypass-Window zwischen Post-SDF Phase 4 RE-BATCH und Pre-SDF Phase 2.2.

### SCHRITT 3.6.0: PLAN-IMMUTABLE-PRE-CHECK (BL-NEW-44.1 ABSOLUT)

```
# Vor Berater-Spawn: pruefe ob batch_stages mutiert wurde
batch_key = DF_BATCH_STATE.current_sub_batch_id
current_plan  = DF_BATCH_STATE.batch_stages[batch_key]
original_plan = DF_BATCH_STATE.batch_stages_original[batch_key] ?? current_plan

IF current_plan != original_plan:
  # Plan-Mutation detected — Stage-Plan wurde nach IDF-stagePlanner falsifiziert
  Logge FEHLER: "[Phase-3.6.0] PLAN-MUTATION DETECTED — batch_stages.{batch_key}={current_plan} vs original={original_plan}"
  Logge FEHLER: "[Phase-3.6.0] Lead hat batch_stages mutiert. _SDF_berater_stageElevation ANTI-PATTERN #3 Verstoss."
  Logge FEHLER: "[Phase-3.6.0] Verboten per BL-NEW-44.1: batch_stages ist immutable nach IDF Phase 7.5 stagePlanner."
  audit_jsonl_append({
    type: "BL_NEW_44_1_VIOLATION",
    batch: batch_key,
    current_plan: current_plan,
    original_plan: original_plan,
    severity: "HIGH"
  })

  IF GLOBAL_HIL == "off":
    # AUTO-REVERT: setze batch_stages zurueck auf Original
    DF_BATCH_STATE.batch_stages[batch_key] = original_plan
    manifest.update()
    Logge: "[Phase-3.6.0] AUTO-REVERT — batch_stages.{batch_key} restored to {original_plan}"
  ELSE:
    AskUserQuestion(
      "BL-NEW-44.1 Plan-Mutation detected fuer {batch_key}:\n"
      "  current:  {current_plan}\n"
      "  original: {original_plan}\n"
      "Lead hat batch_stages mutiert (verboten per ANTI-PATTERN #3).\n"
      "  [REVERT]  batch_stages zuruecksetzen auf Original\n"
      "  [ACCEPT]  Mutation akzeptieren (loggt als HiL-Deferral)\n"
      "  [ABORT]   Stage-Elevation abbrechen → Phase 4 mit ABORT-Hint"
    )

# Auch: Pruefe ob neue Top-Level YAML-Keys angelegt wurden (Lead-Self-Inline-Adds)
# Diese sind Manifest-Korruption (siehe Live-Beobachtung: duplicate keys)
forbidden_inline_keys = ["stages_deferred_per_batch", "current_round_stages"]
FOR key IN forbidden_inline_keys:
  IF manifest[key] EXISTS AND created_by != "_SDF_berater_stageElevation":
    Logge WARNUNG: "[Phase-3.6.0] Lead-Inline-Key {key} detected — Manifest-Korruption-Hinweis"
    audit_jsonl_append({type: "MANIFEST_INLINE_KEY_WARN", key: key})
```

**INV-3.6.0:**
- INV-3.6.0-1: batch_stages MUSS == batch_stages_original (modulo bekannte legitime Re-Plan-Cycles via IDF re-run)
- INV-3.6.0-2: Lead darf KEINE neuen Top-Level YAML-Keys schreiben — nur Berater duerfen das
- INV-3.6.0-3: Auto-Revert bei HiL=off — schuetzt Pipeline vor Plan-Falsification

---

### SCHRITT 3.6.1: stageElevation-Berater spawn

```
# [GATE P7] exit_code-Check Vorgaenger (batchEnde / 3.6.0 plan-immutable) VOR Spawn (== 99 ABORT, Skip-tolerant):
IF BERATER_OUTPUTS.batchEnde.exit_code == 99: ABORT "[INV-SPAWN] Phase 3.6.1 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)"
# [INV-SPAWN] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline:
Skill(_SDF_berater_stageElevation, args="{NAME}")
# Worker schreibt BERATER_OUTPUTS.stageElevation.{status,exit_code,last_berater} + stirbt.
elevation = BERATER_OUTPUTS.stageElevation
audit_jsonl_append({type: "PHASE_3_STEP", step: "3.6_stageElevation", action: elevation.next_action, next_stage: elevation.next_stage})

# Decision-Branch:
IF elevation.next_action == "ELEVATE":
  # Stage-Elevation im SELBEN Sub-Batch — kein Pre-SDF-Round-Trip noetig.
  # Berater hat next_stage gewaehlt aus batch_stages[batch_key] minus completed.

  # Durable Manifest-Update (Berater darf das NICHT machen — INV-STAGE-ELEV-5)
  DF_BATCH_STATE.completed_stages_per_batch[batch_key].append(elevation.inputs_snapshot.current_stage)
  DF_BATCH_STATE.current_stage = elevation.next_stage
  I_PIPELINE_STATE.last_stage_completed = elevation.inputs_snapshot.current_stage
  I_PIPELINE_STATE.current_stage = elevation.next_stage
  I_PIPELINE_STATE.handschuh_wechsel_pending = true
  I_PIPELINE_STATE.phase = "HANDSCHUH_WECHSEL"
  manifest.update()

  audit_jsonl_append({
    type: "STAGE_ELEVATION",
    batch: batch_key,
    from_stage: elevation.inputs_snapshot.current_stage,
    to_stage: elevation.next_stage,
    rationale: elevation.rationale
  })
  Logge: "[Phase-3.6] ELEVATE Stage {elevation.inputs_snapshot.current_stage} → {elevation.next_stage} (batch {batch_key}, planned={elevation.inputs_snapshot.planned_stages})"

  # Exit-Route: direkt zu I_orchestrate mit --stage=N — KEIN Pre-SDF Outer-Loop
  audit_jsonl_append({type: "POST_SDF_EXIT", target: "_I_orchestrate", mode: "stage_elevation_direct", stage: elevation.next_stage})
  # [INV-SPAWN] stageElevation-Spawn (Block I, Phase 3.6.1) ist VOR diesem RETURN auditiert — INV-3-EXIT-4-Bypass geschlossen.
  Skill(_I_orchestrate, args="{NAME} --resume --stage={elevation.next_stage} --vault={VAULT}")
  RETURN  # Post-SDF exit

ELIF elevation.next_action == "BATCH_DONE":
  # Alle geplanten Stages des Sub-Batches durch → fortfahren zu Phase 4 (loopDecision)
  # → loopDecision entscheidet ROLLBACK / TERMINATE / SOFT-REPRIO / RE-BATCH
  DF_BATCH_STATE.completed_stages_per_batch[batch_key].append(elevation.inputs_snapshot.current_stage)
  manifest.update()
  audit_jsonl_append({type: "BATCH_STAGES_DONE", batch: batch_key, all_stages: elevation.inputs_snapshot.planned_stages})
  Logge: "[Phase-3.6] BATCH_DONE — alle Stages {elevation.inputs_snapshot.planned_stages} fuer {batch_key} durch — fortfahren zu Phase 4"
  # Falle durch zu Phase 4 (kein RETURN)

ELIF elevation.next_action == "RETRY":
  # Stage-Outcome PARTIAL — retry erlaubt
  I_PIPELINE_STATE.handschuh_wechsel_pending = true
  I_PIPELINE_STATE.phase = "STAGE_RETRY"
  manifest.update()
  audit_jsonl_append({type: "STAGE_RETRY", batch: batch_key, stage: elevation.inputs_snapshot.current_stage, retry_count: elevation.retry_counts[elevation.inputs_snapshot.current_stage]})
  Logge: "[Phase-3.6] RETRY Stage {elevation.inputs_snapshot.current_stage} (count={elevation.retry_counts[elevation.inputs_snapshot.current_stage]})"
  # [INV-SPAWN] stageElevation-Spawn (Block I, Phase 3.6.1) ist VOR diesem RETURN auditiert — INV-3-EXIT-4-Bypass geschlossen.
  Skill(_I_orchestrate, args="{NAME} --resume --stage={elevation.inputs_snapshot.current_stage} --vault={VAULT}")
  RETURN  # Post-SDF exit

ELIF elevation.next_action == "ABORT":
  # Stage-Outcome RED oder Retry-Limit erreicht
  DF_BATCH_STATE.last_failure = "stage_elevation_abort"
  audit_jsonl_append({type: "STAGE_ABORT", batch: batch_key, rationale: elevation.rationale})
  Logge: "[Phase-3.6] ABORT — Stage {elevation.inputs_snapshot.current_stage} {elevation.current_stage_outcome} (siehe loopDecision fuer Exit-Routing)"
  → GOTO Phase 4 (loopDecision entscheidet ROLLBACK/SOFT-REPRIO basierend auf last_failure)

ELIF elevation.next_action == "HALT":
  # User-PAUSE
  audit_jsonl_append({type: "STAGE_HALT", batch: batch_key, rationale: elevation.rationale})
  Logge: "[Phase-3.6] HALT — User-Intervention erforderlich"
  # [INV-SPAWN] stageElevation-Spawn (Block I, Phase 3.6.1) ist VOR diesem RETURN auditiert — INV-3-EXIT-4-Bypass geschlossen.
  RETURN  # Post-SDF exit (User uebernimmt)
```

**INV-PHASE-3.6:**
- **INV-3.6-1:** Schritt 3.6 ist PFLICHT vor Phase 4 — Lead darf nicht direkt zu loopDecision.
- **INV-3.6-2:** Bei ELEVATE/RETRY MUSS Post-SDF mit Skill(_I_orchestrate, ...) exiten — NICHT inline.
- **INV-3.6-3:** Bei BATCH_DONE MUSS Phase 4 folgen — kein direkter RE-BATCH-Skip.
- **INV-3.6-4 (ABSOLUT):** Lead darf NICHT `current_stage = N+1` oder `completed_stages_per_batch[k].append(...)` inline machen — diese Mutationen sind EXKLUSIV in Phase 3.6 erlaubt. Inline-Manipulation = BL-NEW-44 Violation.

---

## SCHRITT 3.99: PHASE-3-EXIT BERATER-SPAWN BACKSTOP (NEU 2026-05-17 v1.1.1, BL-173 AK-6 Reflex)

```
# [2. NOTNAGEL — BL-469] Dieser ANTI-MEGA-WORKER-Backstop ist nach AK-3 (STATE-MACHINE + [GATE P])
# der REDUNDANTE 2. Notnagel (analog TDD im I-Pilot [M2-SEAM-HARDENED]). PRIMAERER Schutz = state-getriebener
# Vertrag (BERATER_OUTPUTS-Slot pro Step + [GATE P]-exit_code-Gate). Reflex -> Struktur, hier als Backstop belassen.
# Catch-All-Backstop: zaehle distinct _SDF_berater_*-SKILL_LOAD-Events seit
# Phase-0-Entry. Faengt Mega-Worker-Drift wenn Wave-1-JOIN-Check umgangen.
#
# Audit-Schema (audit_hook.py Z313-321):
#   {"event": "SKILL_LOAD", "skill_name": "_SDF_berater_X", "ts": ISO, ...}
#
# Warum SKILL_LOAD nicht WORKER_SPAWN: command-Feld ist "custom" fuer
# Beraters (audit_hook ORCHESTRATOR_LEVELS-Map enthaelt KEINE _SDF_berater_*).
# Distinct-Count via SKILL_LOAD.skill_name ist reliable.
#
# Lead darf audit.jsonl direkt lesen (Status-IO, kein Worker-Job). Spawn eines
# weiteren Workers wuerde den Sinn aushebeln (Lead koennte ihn skipen).

audit_path = ".claude/audit/audit.jsonl"
events = [json.loads(line) for line in Read(audit_path).split("\n") if line.strip()]

# Phase-0-Entry: SKILL_LOAD von _SDF_orchestrate_post (letzter Eintrag dieses Runs)
phase_0_entries = [e for e in events
                    if e.get("event") == "SKILL_LOAD"
                    AND e.get("skill_name") == "_SDF_orchestrate_post"]
phase_0_ts = phase_0_entries[-1].get("ts") if phase_0_entries else None

IF phase_0_ts == null:
  Logge WARNUNG: "[ANTI-MEGA-BACKSTOP] Kein Phase-0-Entry — Audit-Trail moeglicherweise broken."
  audit_jsonl_append({"event": "AUDIT_TRAIL_GAP", "phase": "3_exit_backstop"})
  → SKIP Backstop (defensiver Default — keep pipeline alive)
ELSE:
  # SKILL_LOAD-Events fuer _SDF_berater_* seit Phase-0
  berater_loads = [e for e in events
                    if e.get("event") == "SKILL_LOAD"
                    AND isinstance(e.get("skill_name"), str)
                    AND e["skill_name"].startswith("_SDF_berater_")
                    AND e.get("ts", "") > phase_0_ts]
  distinct_beraters = set(e["skill_name"] for e in berater_loads)

  # Erwartungsbasis (minimal-garantiert nach Phase 3.6):
  #   postItem (3.2, immer)
  #   stage_orchestrate ist KEIN _SDF_berater_* (separater Skill), zaehlt nicht hier
  #   stageElevation (3.6, immer)
  # Plus modus-abhaengig recalibrate (3.1 non-M1), statusTransition (3.3 gap_ready),
  # modelSync (3.5 multi-batch), batchEnde (3.4 last_round).
  # Konservatives Minimum: 2 (postItem + stageElevation).
  # Bei non-M1 erwartet zusaetzlich recalibrate → 3.
  expected_min = 3 if DF_BATCH_STATE.modus != "M1" else 2

  IF len(distinct_beraters) < expected_min:
    Logge FEHLER: "[ANTI-MEGA-BACKSTOP] Phase 3 spawned {len(distinct_beraters)} distinct beraters"
    Logge FEHLER: "[ANTI-MEGA-BACKSTOP] Expected >= {expected_min} (modus={DF_BATCH_STATE.modus})"
    Logge FEHLER: "[ANTI-MEGA-BACKSTOP] Distinct: {distinct_beraters}"
    Logge FEHLER: "[ANTI-MEGA-BACKSTOP] INV-PM-1 Violation — Lead inlined Berater-Arbeit."
    audit_jsonl_append({
      "event": "INV_PM_1_VIOLATION",
      "phase": "Phase_3_Exit_Backstop",
      "distinct_berater_count": len(distinct_beraters),
      "distinct_beraters": list(distinct_beraters),
      "expected_minimum": expected_min,
      "modus": DF_BATCH_STATE.modus,
      "severity": "HIGH",
      "bl_reference": "BL-173_AK6_backstop"
    })
    DF_BATCH_STATE.last_failure = "anti_mega_worker_exit_backstop"

    IF GLOBAL_HIL == "off":
      Logge WARNUNG: "[ANTI-MEGA-BACKSTOP] HiL=off → Pipeline-Continue. BL-173 AK-6 wird FAIL geben."
    ELSE:
      AskUserQuestion(
        "INV-PM-1 Violation: nur {len(distinct_beraters)} distinct Beraters in Phase 3 (erwartet >={expected_min}, modus={DF_BATCH_STATE.modus}).\n"
        "Mega-Worker-Drift wahrscheinlich.\n"
        "  [CONTINUE]  Pipeline fortfahren (Drift wird audit-markiert)\n"
        "  [ABORT]     Pipeline abbrechen, Lead-Self-Review erforderlich"
      )
  ELSE:
    Logge: "[ANTI-MEGA-BACKSTOP] Phase 3 spawned {len(distinct_beraters)} Beraters — OK (>= {expected_min})"
    audit_jsonl_append({
      "event": "PHASE_3_EXIT_OK",
      "distinct_berater_count": len(distinct_beraters),
      "distinct_beraters": list(distinct_beraters)
    })
```

**INV-PHASE-3-EXIT:**
- **INV-3-EXIT-1:** Anzahl distinct `_SDF_berater_*`-SKILL_LOAD-Events seit Phase-0-Entry MUSS >= 2 (M1) bzw >= 3 (non-M1). Anderfalls = INV-PM-1 Violation.
- **INV-3-EXIT-2:** Bei Detection in HiL=off → Pipeline laeuft fort, audit-Marker `INV_PM_1_VIOLATION` gesetzt fuer Post-Hoc-BL-173-Pruefung.
- **INV-3-EXIT-3:** Audit-Trail-Gap (kein Phase-0-Entry findable) → defensive SKIP statt Hard-Fail (Pipeline-Liveness > Strenge).
- **INV-3-EXIT-4 (Limitation):** 3.6 ELEVATE/RETRY/HALT RETURN-Pfade umgehen Phase 3.99. Wave-1-JOIN-Check (INV-POST-4) fangt den haeufigsten Fall früh. Vollstaendige Coverage erfordert Pre-Return-Helper-Refactoring (BL-NEW-XX future).

---

## SCHRITT 3.6b: Post-SC PL-Resync (NEU BL-208, 2026-05-24)

```
# Phase 3.6b laeuft nach stageElevation (BATCH_DONE-Pfad) und VOR loopDecision.
# INV-PL-RESYNC-1: Pflicht nach SC-Cycle, VOR loopDecision.
# SKIP wenn sc_cycle_done != true (M5/M3 ohne SC-Cycle).

IF elevation.next_action == "BATCH_DONE":
  # Guard: nur nach SC-Cycle relevant
  sc_done = DF_BATCH_STATE.sc_cycle_done ?? false

  Logge: "[Phase-3.6b] post_sc_pl_resync: sc_cycle_done={sc_done}"
  audit_jsonl_append({type: "PHASE_3_STEP", step: "3.6b_post_sc_pl_resync", sc_cycle_done: sc_done})

  # [GATE P8] exit_code-Check Vorgaenger (stageElevation, BATCH_DONE-Pfad) VOR Spawn (== 99 ABORT, Skip-tolerant):
  IF BERATER_OUTPUTS.stageElevation.exit_code == 99: ABORT "[INV-SPAWN] Phase 3.6b ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)"
  # [INV-SPAWN] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline:
  Skill(_SDF_berater_post_sc_pl_resync, args="{NAME}")
  # Worker schreibt BERATER_OUTPUTS.pl_resync_batch_{id}.{status,exit_code,last_berater} + stirbt.
  # Output: BERATER_OUTPUTS.pl_resync_batch_{batch_id}
  # Bei sc_cycle_done=false: status=SKIP (Berater schreibt Skip, kein PL-Update)
  # Bei sc_cycle_done=true: status=DONE + Audit-Trail in PL-Items

  audit_jsonl_append({
    type: "PHASE_3_STEP",
    step: "3.6b_done",
    status: BERATER_OUTPUTS["pl_resync_batch_" + batch_id].status ?? "SKIP"
  })
  # Falle durch zu Phase 4 loopDecision
```

**INV-PHASE-3.6b (BL-208):**
- **INV-3.6b-1:** Phase 3.6b MUSS im BATCH_DONE-Pfad laufen (nach stageElevation, vor loopDecision).
- **INV-3.6b-2:** Phase 3.6b wird NICHT im ELEVATE/RETRY/HALT-Pfad ausgefuehrt (nur BATCH_DONE).
- **INV-3.6b-3:** Berater-Spawn PFLICHT (INV-PM-1) — Lead darf PL-Sync NICHT inline machen.

---

## PHASE 4: LOOP-DECISION + EXIT-ROUTING

### 4.1: loopDecision-Berater

```
# [GATE P9] exit_code-Check Vorgaenger (stageElevation / pl_resync) VOR Spawn (== 99 ABORT, Skip-tolerant):
IF BERATER_OUTPUTS.stageElevation.exit_code == 99: ABORT "[INV-SPAWN] Phase 4.1 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)"
# [INV-SPAWN] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline:
Skill(_SDF_berater_loopDecision, args="{NAME}")
# Worker schreibt BERATER_OUTPUTS.loopDecision.{status,exit_code,last_berater} + stirbt.
# Output: BERATER_OUTPUTS.loopDecision.{decision, reason, k_drift, ...}
# decision IN {ROLLBACK, TERMINATE, SOFT-REPRIO, RE-BATCH}

audit_jsonl_append({type: "PHASE_4_STEP", step: "4.1_decision", decision: BERATER_OUTPUTS.loopDecision.decision})
```

#### 4.1-WELLE: Welle-aggregiertes loopDecision (BL-230 SB-3b, AK-G7-KONFORM + AK-WELLE-LOOPDEC)

> Im **parallelen Wellen-Pfad** (`effective_fanout>1`) liefert der Fan-In **N** Batch-Returns (ein
> Phase-3.x-Befund pro lebendem Batch) statt eines Single-Batch-Rounds. Die Barrier (Schritt 5 in
> `dispatch_implement.js::runFanInBarrier`) bildet daraus **EIN** welle-aggregiertes loopDecision —
> aber erst, nachdem das **Konformitaets-Gate als Vorbedingung** durchlief.

```
# Vorbedingung (G7): N-Report-Konformitaets-Check VOR dem Aggregat.
gate = wave_conformance_gate(reports)   # guard_geist9_wave_conformance.py — ALL-konjunktiv ueber N lebende Reports
#   pro lebendem batch_id: alle 4 Phase-3.x-Outputs (recalibrate/postItem/statusTransition/modelSync;
#   modelSync:SKIP nur mit reason) vorhanden? 1 toter Batch (None) wird via filter(Boolean) ignoriert.

IF NOT gate.ok:
  # Gate-FAIL (fail-loud): KEIN Aggregat. Befund nennt die divergente(n) batch_id(s).
  → fail-loud STOP, gate.divergent_batch_ids reporten (kein loopDecision, kein [x])

# Gate-GRUEN (ALLE N konform): loop_decision-VEKTOR (BL-230 SB-4, AK-WELLE-LOOPDEC) — PRO lebendem
#   Batch EIN loop_decision-Eintrag (N Eintraege ueber liveSortedIds, batch_id-sortiert, deterministisch
#   — konsistent SB-3a Schritt 3/4; nur lebende Batches), NICHT ein einzelnes welle-aggregiertes Skalar.
loop_decision = [ decision_for(b) for b in liveSortedIds ]     # N Returns -> N-elementiger VEKTOR
# INV-MODUS-9-Wellen-Neufassung (SB-4): sc_resume_from ist EBENFALLS ein VEKTOR (pro Batch ein Wert),
#   NICHT ein globaler Singular. Pro Batch: "ergebnis" bei SC-Re-Entry, null bei Erst-Eintritt.
sc_resume_from = [ ("ergebnis" if sc_re_entry(b) else None) for b in liveSortedIds ]
```

> **INV-MODUS-9 (Wellen-Neufassung, BL-230 SB-4):** der frueher single-batch `sc_resume_from`
> (`"ergebnis"` bei SC-Re-Entry, `null` bei Erst-Eintritt) gilt im Wellen-Pfad **pro Batch** als
> VEKTOR ueber `liveSortedIds` — ein `sc_resume_from`-Wert je lebendem Batch, parallel zum
> `loop_decision`-VEKTOR. **N=1 (OFF/Single-Mode):** beide Vektoren degradieren byte-identisch auf
> das heutige Skalar (1-elementig == Skalar; Single-Batch-Verhalten erhalten).

**Szenario-A (N konform → Vektor laeuft):** alle N lebenden Batches haben ihre 4 Phase-3.x-Outputs.
`wave_conformance_gate` gibt `ok=True`; der `loop_decision`-VEKTOR + `sc_resume_from`-VEKTOR werden
ueber `liveSortedIds` gebildet (ein Eintrag pro Batch) und an den Lead RETURNED (Routing = Lead, INV-MOTOR-2).

**Szenario-B (1 divergent → Gate-FAIL fail-loud):** ein file-disjunkt-aber-prozess-divergenter Batch
liess Phase-3.x aus. Ohne Gate liefe er still durch (heutiger Blindspot) und faellt erst beim globalen
`[x]` auf. Mit dem Gate faengt der Fan-In ihn **fail-loud** (`ok=False`, `divergent_batch_ids=[<id>]`)
→ **KEIN** loop_decision-VEKTOR, kein `[x]`. **N=1 == heutiger geist9 / Skalar** (KOM-G7-3, Null-Regression).

### 4.1.5: Orphan-Scan-Gate (BL-NEW-60 NEU 2026-05-12, Hybrid Severity-Threshold + Stage-Level)

> **Zweck:** Nach loopDecision aber VOR Exit-Routing pruefen ob waehrend des Batches
> neue Orphans entstanden sind (PL-Items oder Stage-Level-Phantom-Done). Bei Severity
> >= Threshold wird IDF Re-Cluster getriggert BEFORE RE-BATCH/ROLLBACK/SOFT-REPRIO.
> Iterative-Adaptive Pipeline statt Waterfall-Plan.

```
# Feature-Flag (Default true)
orphan_scan_active = DF_BATCH_STATE.orphan_scan_after_each_batch ?? true

# Nur sinnvoll bei decisions die weiter-iterieren — TERMINATE skipt
relevant_decisions = ["RE-BATCH", "ROLLBACK", "SOFT-REPRIO"]

IF orphan_scan_active AND BERATER_OUTPUTS.loopDecision.decision IN relevant_decisions:
  Logge: "[Phase 4.1.5] Orphan-Scan triggered (decision={BERATER_OUTPUTS.loopDecision.decision})"

  # [GATE P10] exit_code-Check Vorgaenger (loopDecision) VOR Spawn (== 99 ABORT, Skip-tolerant):
  IF BERATER_OUTPUTS.loopDecision.exit_code == 99: ABORT "[INV-SPAWN] Phase 4.1.5 ohne Vorgaenger-DONE (ABORTED_PROCESS_VIOLATION)"
  # [INV-SPAWN] Worker-Spawn (KURZSCHRIFT, siehe WORKER-SPAWN-PATTERN oben) — NICHT Lead-Inline:
  Skill(_SDF_berater_orphan_scan, args="{NAME}")
  # Worker schreibt BERATER_OUTPUTS.orphan_scan.{status,exit_code,last_berater} + stirbt.
  # Output: BERATER_OUTPUTS.orphan_scan.{pl_orphans, stage_orphans, severity_summary, decision}

  scan = BERATER_OUTPUTS.orphan_scan

  audit_jsonl_append({
    type: "PHASE_4_STEP",
    step: "4.1.5_orphan_scan",
    pl_orphans: scan.pl_orphans.length,
    stage_orphans: scan.stage_orphans.length,
    severity_summary: scan.severity_summary,
    trigger_recluster: scan.decision.trigger_recluster
  })

  IF scan.decision.trigger_recluster == true:
    # Max-Iteration-Schutz (INV-ORPH-Loop, BL-NEW-60)
    recluster_count = DF_BATCH_STATE.orphan_scan_history.count(WHERE trigger_recluster=true)

    IF recluster_count >= 3:
      Logge: "[Phase 4.1.5] Max 3 Re-Cluster-Iterations erreicht — HiL-Decision noetig"
      audit_jsonl_append({
        type: "ORPHAN_SCAN_MAX_RECLUSTER_REACHED",
        recluster_count: recluster_count,
        pending_orphans: scan.severity_summary
      })
      SendMessage(team-lead/user, "Orphan-Scan hat Re-Cluster 3x getriggert. Restliche Orphans: {scan.severity_summary}. HiL: weiter mit RE-BATCH ohne Re-Cluster ODER ABORT?")
      # User-Confirm via UI ODER Default-Fortsetzung mit original decision
      # Annahme: ohne User-Antwort → original decision ausfuehren (Pipeline-Liveness > Adaptivitaet)
    ELSE:
      # ORPHAN-SCAN-INDUCED RE-CLUSTER — uebersteuere original decision
      Logge: "[Phase 4.1.5] Orphan-Scan triggered Re-Cluster (overrides {BERATER_OUTPUTS.loopDecision.decision}): {scan.decision.reason}"
      audit_jsonl_append({
        type: "POST_SDF_EXIT",
        target: "_IDF_orchestrate",
        mode: "recluster-orphan-induced",
        original_decision: BERATER_OUTPUTS.loopDecision.decision,
        override_reason: scan.decision.reason,
        recluster_iteration: recluster_count + 1
      })
      Skill(_IDF_orchestrate, args="{BL_ID} {BL_SLUG} {scan.decision.recluster_args}")
      # IDF Re-Cluster mit --orphan-only --sticky-ids --from=orphan_scan (recluster_args traegt --from, BL-298)
      # BL-298 2026-06-10 (Auto-Build-Bounded, User-Entscheid): IDF chained SELBST via Phase 8.5a
      #   (orphan_scan-Zweig) zurueck zu Skill(_SDF_orchestrate, "{BL_ID} --resume") (RE-BATCH) — frueher
      #   (vor BL-298) lief das in den stillen no_chain (Gate war auf from==direct verengt). >=3 Iter: HiL-Alert.
      # Orphan-Scan wird im naechsten Phase 4 wieder laufen → konvergiert wenn 0 HIGH/CRITICAL Orphans
      RETURN   # Skip 4.2 Exit-Routing — Re-Cluster + Phase-8.5a-Chain haben naechsten Schritt uebernommen

  ELSE:
    Logge: "[Phase 4.1.5] Orphan-Scan: 0 HIGH/CRITICAL Orphans — kein Re-Cluster, weiter mit Phase 4.2 Exit"

ELIF NOT orphan_scan_active:
  Logge: "[Phase 4.1.5] orphan_scan_after_each_batch=false — SKIP Orphan-Scan"

# Wenn KEIN Re-Cluster triggert: weiter zu 4.2 Exit-Routing mit original loopDecision
```

---

### 3-WEGE-ROUTING-MODELL (BL-429 AK-1/2/3/4/5/6/8/9)

> **Kanonischer Klassifikator:** `sdf_last_item_detect.classify_route(idf_items, batch_done, completed_sub_batches, open_pl_deferred, stage_orphans)` (`.claude/scripts/sdf_last_item_detect.py`, BL-429 batch_1).
> Die intern verwendeten Routing-Tokens bleiben erhalten — das 3-Wege-Framing ist eine **Doku-Schicht** obendrauf, kein Breaking-Rename.

**Auswertungs-Reihenfolge: WEG1 > WEG3 > WEG2 (AK-6)**

| Weg | Kurzname | Routing-Token(s) | Ziel |
|-----|----------|------------------|------|
| **WEG 1** | neue-PL → IDF | `ROLLBACK` / orphan-induced recluster | `_IDF_orchestrate --mode=recheck` oder `--mode=recluster` |
| **WEG 3** | alles-zu → Roadmap/BDF | `TERMINATE` | df_status=DONE, BDF picks up |
| **WEG 2** | bekannte-PL → SDF | `RE-BATCH` | `_SDF_orchestrate --resume` |

**WEG 1 — "neue PL → IDF" (konsolidiert, AK-2)**

WEG 1 fasst alle bisher verstreuten IDF-Rücklauf-Pfade zusammen:
- ROLLBACK (neue Vault-PL-Items, len(vault_pl_items) > len(idf_items))
- Phase 4.1.5 orphan_scan — stage_orphans / HIGH-CRITICAL-Orphans → Re-Cluster
- SOFT-REPRIO (K-Drift > 30%) — IDF Re-Cluster via `--mode=recluster`

Alle drei bedeuten: "neue oder veränderte Konfiguration → IDF muss neu clustern".

**WEG 2 — "bekannte PL → SDF" (RE-BATCH, AK-3)**

WEG 2 übergibt den Modus an C3 (`_SDF_berater_modusEntscheidung`, Phase 1.1). **INV-MODUS-1:** loopDecision und das Exit-Routing setzen **nie** `batch_modes` oder `modus`. Die Modus-Entscheidung pro neuer Round ist ausschließlich Aufgabe von `_SDF_berater_modusEntscheidung`.

**WEG 3 — "alles zu → Roadmap/BDF" (TERMINATE, AK-4/AK-5)**

WEG 3 feuert nur bei `is_last == True` des Klassifikators. Pure Set-Equality reicht NICHT:
1. `set(idf_items) == set(batch_done)` (alle bekannten Items done)
2. `open_pl_deferred` leer (INV-LD-7: kein offenes deferred-stage/deferred-ak)
3. `stage_orphans` leer (kein Stage-Phantom)

**Endlos-Loop-Counter → 3-Wege-Mapping (AK-8)**

| Counter | Weg | Token |
|---------|-----|-------|
| `loop_counters.rollback` + `loop_counters.soft_reprio` | WEG 1 | ROLLBACK / SOFT-REPRIO |
| `loop_counters.re_batch` | WEG 2 | RE-BATCH |

WEG 3 hat keinen Counter (nicht-iterativer Abschluss). Schwelle: `MAX_LOOPS_PER_DECISION` (Default 3, BL-210).

**Konsistenz mit INV-LD-1..7 + INV-POST-1 (AK-9):** Decision-Enum {ROLLBACK/TERMINATE/SOFT-REPRIO/RE-BATCH} unverändert. INV-LD-7 (kein TERMINATE bei offenem deferred) exakt abgebildet in `is_last`-Bedingung. INV-POST-1 (kein inline-Return) gilt unverändert für alle drei Wege.

---

### 4.2: Exit-Routing

> **BL-NEW-12 Fix B3 (2026-05-11)** — RE-BATCH war RETURN ohne Skill-Call.
> **THEORIE:** Pre-SDF OUTER-LOOP-WRAPPER iteriert von selbst (FOR-Loop in Pre-SDF
> Z535-636), basierend auf `completed_sub_batches`-SKIP-Logik. Control wuerde
> via I-orch zurueck zu Pre-SDF's outer-loop gehen.
>
> **REALITAET (BL-NEW-39, Case-Anchor `.claude/_parking-lot.md`):**
> Nach Post-SDF RETURN kehrt Control NICHT zur Pre-SDF FOR-Loop zurueck.
> Lead wird "Idle" — Pipeline stuck nach jedem Batch. User muss manuell
> Skill(_SDF_orchestrate) re-invocieren fuer naechsten Batch.
>
> **REVISION 2026-05-11 BL-NEW-39 Fix:** RE-BATCH macht JETZT explizit
> Skill(_SDF_orchestrate, --resume). Das ist KEINE Stack-Recursion sondern
> fresh Skill-Load. Pre-SDF Phase 0 RESUME-GUARD + Outer-Loop FOR (Z538-540
> `IF batch_key IN completed_sub_batches: CONTINUE`) verhindert Doppel-
> Verarbeitung der bereits abgeschlossenen Batches. Auto-Chain wirkt:
> Pre-SDF startet, skipt batch_1+batch_2 (done), processes batch_3 etc.

```
decision = BERATER_OUTPUTS.loopDecision.decision

# BL-210 M11 Fix 2026-05-24: Endlos-Loop-Schutz SDF↔IDF.
# Max-Schutz analog zu Phase 4.1.5 Orphan-Scan-Gate (recluster_count >= 3 → HiL).
# Counter pro Decision-Type im DF_BATCH_STATE.
DF_BATCH_STATE.loop_counters ??= {rollback: 0, soft_reprio: 0, re_batch: 0}
MAX_LOOPS_PER_DECISION = DF_BATCH_STATE.max_loops_per_decision ?? 3

IF decision == "ROLLBACK":
  DF_BATCH_STATE.loop_counters.rollback += 1
  IF DF_BATCH_STATE.loop_counters.rollback >= MAX_LOOPS_PER_DECISION:
    Logge: "[LOOP-DECISION] HARD-BREAK: ROLLBACK-Counter erreicht {MAX_LOOPS_PER_DECISION} — HiL-Alert"
    audit_jsonl_append({type: "ENDLOS_LOOP_DETECTED", decision: "ROLLBACK", count: DF_BATCH_STATE.loop_counters.rollback, severity: "HIGH"})
    SendMessage(team-lead/user, "ENDLOS-LOOP: ROLLBACK {MAX_LOOPS_PER_DECISION}x in Folge — IDF konvergiert nicht. Optionen: (A) max_loops erhoehen + retry, (B) ABORT + manuelle Analyse")
    IF GLOBAL_HIL == "off":
      # Auto-Fortsetzung mit ABORT — Pipeline-Liveness > Adaptivitaet
      Logge: "[LOOP-DECISION] HiL=off → AUTO-ABORT bei Endlos-Loop"
      df_status = "ABORTED"
      RETURN
  # ROLLBACK = neue PL-Items im Vault → IDF muss re-clustern
  # Pre-SDF Outer-Loop bricht ab (alle bekannten Batches done), IDF macht neu
  Logge: "[LOOP-DECISION] Neue PL-Items im Vault → ROLLBACK zu IDF Phase 4-7 (Counter: {DF_BATCH_STATE.loop_counters.rollback}/{MAX_LOOPS_PER_DECISION})"
  audit_jsonl_append({type: "POST_SDF_EXIT", target: "_IDF_orchestrate", mode: "recheck", loop_counter: DF_BATCH_STATE.loop_counters.rollback})
  Skill(_IDF_orchestrate, args="{BL_ID} {BL_SLUG} --mode=recheck --from=sdf_finish")
  # IDF re-run von Phase 4 (DEPENDENCY_MATRIX) bis Phase 7 (BATCH_PLAN)

ELIF decision == "TERMINATE":
  # TERMINATE = alle Items in batch_done → Pre-SDF outer-loop wird natuerlich exiten
  Logge: "[LOOP-DECISION] Alle PL-Items DONE → TERMINATE (kein weiterer Skill-Call)"
  df_status = "DONE"
  audit_jsonl_append({type: "POST_SDF_EXIT", target: "outer_loop_exit", mode: "terminate"})

  # [AK-1 BL-444: AKTIVER Closure-Block — deterministische atomare Closure-Sequenz, nicht mehr Kommentar-Pseudocode]
  # atomare Closure-Sequenz: merge_seam (Schritt 1) + current-advance (Schritt 2) + redirect-chain (Schritt 3+4)
  # GUARD: guard_lane_closure_stop.py (INV-CLOSURE-1, BL-444) ist der Stop-Hook-Backstop —
  #        blockiert Turn-Ende wenn hil=off + lane + next_bl vorhanden + kein Chain ausgeloest
  #        (analog guard_autochain_stop.py fuer INV-AUTOCHAIN-1/BL-394).
  #
  # BDF-Redirect-Backstop (non-lane-Modus, aus BL-442 AK-1 — Logik getestet: sdf_post_bdf_redirect.py 5/5):
  from sdf_post_bdf_redirect import should_chain_bdf, redirect_target
  IF should_chain_bdf(mode=global_modus, all_items_done=True, no_chain=args.no_chain,
                      bdf_loop_active=(global_modus=="big_dark_factory")):
    audit_jsonl_append({type:"POST_SDF_EXIT", target: redirect_target(), mode:"bdf-redirect-bl442-ak1"})
    Skill(redirect_target(), args="--resume")   # INV-AO-CALLER: Lead-Skill-Load
    RETURN

  # ── MERGE-SEAM (BL-425, default-OFF) ────────────────────────────────────────
  # Nur aktiv wenn merge==true (session-param, default false).
  # Default: reiner No-Op — byte-identisch mit bisherigem Verhalten, kein Behaviour-Change.
  # Opt-In via session_params: merge=true, merge_target=develop (default), merge_timing=per_bl (default).
  #
  # merge_timing-Varianten:
  #   per_bl   (default): sofort am BL-Ende (TERMINATE) — jedes BL wird einzeln gegated
  #   end_only          : akkumulieren, gebündelt am Roadmap-Ende; jedes BL einzeln gegated
  #
  # Helper: .claude/scripts/merge_seam.py
  #   mergeable_check(current_branch, merge_target) → {status: CLEAN|CONFLICT|DIRTY, detail}
  #   merge_exec(current_branch, merge_target)      → ff-bevorzugt, kein --force
  #   conflict_to_pl(bl_id, bl_slug, detail)        → PL-Item + Hold
  #   do_merge_if_clean(current_branch, merge_target, bl_id, bl_slug) → kombiniert check+exec|conflict_to_pl
  #
  # ── BL-442 AK-3 (GAP-3): develop-Resync-Disziplin (Anti-Lane-Divergenz) ──────────────────────
  # Multi-Lane: die Lane darf nicht von develop wegdriften (Lane B war live 4 ahead). Entscheider
  # lane_develop_sync.develop_sync_action(ahead, behind) (ahead/behind = git rev-list --left-right
  # --count {merge_target}...{current_branch}):
  #   "merge"      -> should_merge_after_bl_done==True -> merge_seam.do_merge_if_clean (per-BL nach Done)
  #   "pull-first" -> develop ist voraus: VOR naechstem BL-Start develop integrieren (sonst Divergenz)
  #   "diverged"   -> beide voraus -> HiL/Lane-Koordination (Merge/Rebase-Aufloesung)
  #   "in-sync"    -> nichts zu tun
  # (Logik getestet: .claude/scripts/lane_develop_sync.py + test_lane_develop_sync.py, 5/5.)

  merge_enabled    = session_params.get("merge", false)
  merge_target     = session_params.get("merge_target", "develop")
  merge_timing     = session_params.get("merge_timing", "per_bl")
  current_branch   = git.current_branch()

  IF merge_enabled AND merge_timing == "per_bl":
    Logge: "[MERGE-SEAM] merge=true, timing=per_bl — pruefe {current_branch} → {merge_target}"
    audit_jsonl_append({
      type: "MERGE_SEAM_CHECK",
      bl_id: BL_ID,
      branch: current_branch,
      merge_target: merge_target,
      timing: "per_bl"
    })

    result = merge_seam.mergeable_check(current_branch, merge_target)
    # result.status ∈ {CLEAN, CONFLICT, DIRTY}

    IF result.status == "CLEAN":
      Logge: "[MERGE-SEAM] CLEAN → merge_exec ff-bevorzugt ({current_branch} → {merge_target})"
      merge_seam.merge_exec(current_branch, merge_target)
      audit_jsonl_append({
        type: "MERGE_SEAM_DONE",
        bl_id: BL_ID,
        branch: current_branch,
        merge_target: merge_target,
        result: "merged"
      })
      Logge: "[MERGE-SEAM] BL-Commit nach {merge_target} gemerged (ff-bevorzugt)"

    ELSE:  # CONFLICT oder DIRTY
      Logge WARNUNG: "[MERGE-SEAM] merge held: {result.status} — conflict_to_pl + Hold, {merge_target} unveraendert"
      merge_seam.conflict_to_pl(BL_ID, BL_SLUG, result.detail)
      audit_jsonl_append({
        type: "MERGE_SEAM_HELD",
        bl_id: BL_ID,
        branch: current_branch,
        merge_target: merge_target,
        reason: result.status,
        detail: result.detail
      })
      Logge: "[MERGE-SEAM] PL-Item angelegt, develop unveraendert. BL-Commit bleibt auf {current_branch}."

  ELIF merge_enabled AND merge_timing == "end_only":
    Logge: "[MERGE-SEAM] merge=true, timing=end_only — BL akkumuliert, kein sofortiger Merge (gebündelt am Roadmap-Ende)"
    audit_jsonl_append({type: "MERGE_SEAM_DEFERRED", bl_id: BL_ID, branch: current_branch, merge_target: merge_target})

  ELSE:
    # merge=false (default) — absoluter No-Op
    Logge: "[MERGE-SEAM] merge=false (default) — No-Op, kein Merge"
  # ── MERGE-SEAM ENDE ────────────────────────────────────────────────────────

  # ── LANE-CLOSURE: Schritt 2 (Queue-Pointer-Advance, AK-3) + Schritt 3/4 (next-BL-Chain, AK-2/AK-5) ──
  # atomare Closure-Sequenz — Schritt 1 (merge_seam) oben bereits gelaufen.
  # GUARD: guard_lane_closure_stop.py (INV-CLOSURE-1, BL-444) blockiert Turn-Ende bei Verletzung
  #        (hil=off + lane + next_bl vorhanden + kein Chain → BLOCK, analog guard_autochain_stop.py).

  my_lane = session_params.get("lane", null)
  IF my_lane != null:
    # Schritt 2: Queue-Pointer-Advance (AK-3)
    from lane_plan import parse_lane_plan, advance_current, write_lane_plan
    lane_plan_path = vault_root + "/_lane_plan.md"
    plan = parse_lane_plan(lane_plan_path)
    plan = advance_current(my_lane, BL_ID, plan)
    write_lane_plan(lane_plan_path, plan)
    audit_jsonl_append({type: "LANE_CURRENT_ADVANCED", lane: my_lane, completed_bl: BL_ID})

    # Schritt 3: Naechstes BL bestimmen (AK-2)
    from lane_plan import next_bl_for_lane
    done_set = set(plan[my_lane].get("done", []))
    next_bl = next_bl_for_lane(my_lane, plan, done_set)

    # Schritt 4: HiL-Gabelung (AK-5) — INV-CLOSURE-3
    IF next_bl == null:
      Logge: "[LANE-CLOSURE] Lane {my_lane} leer — passives DONE"
      audit_jsonl_append({type: "LANE_CLOSURE_DONE", lane: my_lane, reason: "queue_empty"})
      RETURN

    from session_params_resolver import read_hil_with_fallback
    hil = read_hil_with_fallback()

    IF hil == "off":
      # Auto-Chain: deterministisch (INV-CLOSURE-1) — INV-AO-CALLER: Lead-Skill-Load
      Logge: "[LANE-CLOSURE] hil=off → AUTO-CHAIN zu {next_bl}"
      audit_jsonl_append({type: "LANE_CLOSURE_CHAIN", lane: my_lane, next_bl: next_bl, hil: "off"})
      Skill(_A_orchestrate, args="{next_bl}")
      RETURN
    ELIF hil == "on":
      # User-Checkpoint (kein Auto-Chain)
      Logge: "[LANE-CLOSURE] hil=on → User-Checkpoint vor {next_bl}"
      audit_jsonl_append({type: "LANE_CLOSURE_CHECKPOINT", lane: my_lane, next_bl: next_bl, hil: "on"})
      ASK_USER: "Lane {my_lane} abgeschlossen: {BL_ID} done. Naechstes BL: {next_bl}. Starten?"
      # kein auto-RETURN — User antwortet

  ELSE:
    # Non-Lane-Modus — passives BDF-Signal (df_status=DONE bereits gesetzt)
    Logge: "[LANE-REDIRECT] Non-lane-Modus (lane=null) — passives BDF-Signal (df_status=DONE)"
    # BDF_BATCH_DONE-Signal triggert BDF-naechste-Iteration wie bisher
  # ── LANE-CLOSURE ENDE ─────────────────────────────────────────────────────

  RETURN  # Pipeline-Ende, BDF/User/lane picks up

ELIF decision == "SOFT-REPRIO":
  # BL-210 M11 Fix: Loop-Counter + Max-Schutz
  DF_BATCH_STATE.loop_counters.soft_reprio += 1
  IF DF_BATCH_STATE.loop_counters.soft_reprio >= MAX_LOOPS_PER_DECISION:
    Logge: "[LOOP-DECISION] HARD-BREAK: SOFT-REPRIO-Counter erreicht {MAX_LOOPS_PER_DECISION} — HiL-Alert"
    audit_jsonl_append({type: "ENDLOS_LOOP_DETECTED", decision: "SOFT-REPRIO", count: DF_BATCH_STATE.loop_counters.soft_reprio, severity: "HIGH"})
    IF GLOBAL_HIL == "off":
      df_status = "ABORTED"
      RETURN
  k_drift = BERATER_OUTPUTS.loopDecision.k_drift
  Logge: "[LOOP-DECISION] SOFT-REPRIO — K-Drift {k_drift*100|round=1}% > 30% → IDF Re-Cluster (Counter: {DF_BATCH_STATE.loop_counters.soft_reprio}/{MAX_LOOPS_PER_DECISION})"
  audit_jsonl_append({type: "POST_SDF_EXIT", target: "_IDF_orchestrate", mode: "recluster", k_drift: k_drift, loop_counter: DF_BATCH_STATE.loop_counters.soft_reprio})
  Skill(_IDF_orchestrate, args="{BL_ID} {BL_SLUG} --mode=recluster --from=sdf_drift")
  # IDF: Phase 5 (Clustering) + Phase 6 (SeqPlanner) + Phase 7 (BatchPlan)

ELIF decision == "RE-BATCH":
  # ═══════════════════════════════════════════════════════════════════════
  # BL-NEW-39 Fix 2026-05-11 — AUTO-CHAIN per Skill-Re-Invocation
  # ═══════════════════════════════════════════════════════════════════════
  # Vorher (BL-NEW-12 Fix B3): RETURN — basierend auf Theorie dass Pre-SDF's
  #   FOR-Loop bei Stack-Unwinding weiterlaeuft.
  # Realitaet: Lead wird Idle, Pipeline stuck.
  # Loesung: explizite Skill-Re-Invocation. KEINE Stack-Recursion (fresh
  # Skill-Load), KEIN Doppel-Verarbeitung (Pre-SDF FOR-Loop Z538-540 skipt
  # completed_sub_batches CONTINUE).
  Logge: "[LOOP-DECISION] RE-BATCH — auto-chain Skill(_SDF_orchestrate, --resume) fuer naechsten Batch"
  audit_jsonl_append({type: "POST_SDF_EXIT", target: "_SDF_orchestrate", mode: "auto-chain", reason: "BL-NEW-39 Auto-Iteration"})
  Skill(_SDF_orchestrate, args="{BL_ID} --resume")
  # Pre-SDF Phase 0 erkennt batch_status=READY → goto outer-loop → skipt done batches → processes next
```

> ╔══════════════════════════════════════════════════════════════════════════╗
> ║  INV-AUTOCHAIN-1 (BL-394, IV-11): RE-BATCH + hil=off — SOFORT-CHAIN   ║
> ╠══════════════════════════════════════════════════════════════════════════╣
> ║  Bei decision == "RE-BATCH" UND GLOBAL_HIL == "off":                   ║
> ║  Der Lead MUSS sofort `Skill(_SDF_orchestrate, args="{BL_ID} --resume  ║
> ║  --next-batch")` chainen — kein Zwischenstopp, kein Angebot.           ║
> ║                                                                          ║
> ║  VERBOTEN: jede Formulierung der Form "Soll ich fortfahren?",           ║
> ║  "Meld dich wenn du bereit bist", "Ich warte auf Bestaetigung" oder    ║
> ║  vergleichbare HiL-Anfragen, die den Auto-Chain unterbrechen.           ║
> ║                                                                          ║
> ║  Begruendung: hil=off bedeutet vollautomatische Pipeline ohne manuelle  ║
> ║  Unterbrechung. Ein Angebot-Emit erzeugt einen stillen Dead-Stop —      ║
> ║  der Lead haelt inne, kein Mensch antwortet, Pipeline stuck.            ║
> ║  Strukturell erzwungen: guard_autochain_stop.py (Stop-Hook) detektiert  ║
> ║  Angebot-Patterns im Stop-Kontext und blockiert bei hil=off + RE-BATCH. ║
> ║                                                                          ║
> ║  guard-enforced via guard_autochain_stop.py (INV-AUTOCHAIN-1, BL-394)  ║
> ╚══════════════════════════════════════════════════════════════════════════╝

---

## INVARIANTEN

- **INV-POST-1:** Post-SDF darf NIE inline returnen. Jeder Pfad endet in genau einem Skill-Call (oder TERMINATE → BDF).
- **INV-POST-2:** Phase 3 Schritte 3.0.5 / Wave 1 / Wave 2 / 3.3.5 / 3.4 / 4.1+4.2 sind PFLICHT — kein Lead-Inline-Skip erlaubt.
- **INV-POST-3:** Audit-Trail vollstaendig — jeder Phase 3 Step + jeder Wave-Event + Exit-Skill ist in audit.jsonl.
- **INV-POST-4 (NEU 2026-05-17):** Anti-Mega-Worker Wave-1-JOIN-Check ist PFLICHT. Wenn `BERATER_OUTPUTS.recalibrate` (modus != M1) ODER `BERATER_OUTPUTS.postBatch_aggregate` null/missing → MEGA_WORKER_DETECTED audit + Phase 4 ABORT-Hint. Heilt PL-RUN-09-Pattern (Mega-Worker bei Post-SDF). Siehe Schritt Wave 1 JOIN.
- **INV-POST-5 (NEU 2026-05-17):** Phase-3-Exit Worker-Count Backstop (Schritt 3.99) zaehlt distinct `WORKER_SPAWN`-Events seit Phase-0-Entry — MUSS >= 3 sein. Anderfalls INV_PM_1_VIOLATION audit. Catch-All falls Wave-1-Check umgangen. BL-173 AK-6 wird die Marker post-hoc lesen.
- **INV-HANDOVER-1:** Aufrufer (I/SC) MUSS Post-SDF als letzten Step gerufen haben — sonst INV-Bruch (warn-audit).
- **INV-PM-1:** Worker-Pflicht — Lead darf nicht dotnet build / git commit / Vault-Write selbst ausführen.

### Anti-Mega-Worker-Reflex-Kette (NEU 2026-05-17)

```
Wave 1 JOIN (Schritt Wave-1 nach Z195)
   ↓ Check BERATER_OUTPUTS.recalibrate + .postBatch_aggregate
   ↓ FAIL → audit_jsonl MEGA_WORKER_DETECTED + Phase 4 ABORT-Hint
   ↓ PASS → weiter
Phase 3.99 Exit-Backstop (NEU)
   ↓ Read audit.jsonl, count distinct WORKER_SPAWN since Phase-0-Entry
   ↓ <3 distinct → audit_jsonl INV_PM_1_VIOLATION + (HiL=on AskUserQuestion / HiL=off warn-continue)
   ↓ >=3 distinct → PHASE_3_EXIT_OK audit
Phase 4 loopDecision (existing)
   ↓ liest DF_BATCH_STATE.last_failure ("anti_mega_worker_*")
   ↓ Bei gesetztem Failure-Marker: SOFT-REPRIO oder ROLLBACK begruendet
BL-173 AK-6 (post-hoc, naechster Audit-Run)
   ↓ Read audit.jsonl → suche MEGA_WORKER_DETECTED + INV_PM_1_VIOLATION Events
   ↓ Wenn Events vorhanden → AK-6 FAIL (Mega-Worker passierte trotz Reflex)
   ↓ Wenn keine Events + WORKER_SPAWN-Spread OK → AK-6 PASS
```

**Korrespondenz:** In-Flight-Reflex (INV-POST-4/5) und Post-Hoc-Verifikation (BL-173 AK-6) lesen dieselben audit.jsonl-Marker. In-Flight fangt am Lauf, Post-Hoc archiviert die Lehre.

---

## CALLER-CHAIN (Doc-Referenz)

```
BDF SCANNING
  ↓ Skill(_SDF_orchestrate)                  ← Pre-SDF (Phase 0-2)
        Phase 2 EXECUTION DISPATCH:
        ↓ Skill(_I_orchestrate) [oder _SC]
              I-Pipeline Steps
              LAST STEP (PFLICHT):
              ↓ Skill(_SDF_orchestrate_post)  ← THIS SKILL
                  Phase 3 + 4
                  EXIT (one of):
                  ├─ Skill(_SDF_orchestrate, --resume)    [RE-BATCH]
                  ├─ Skill(_IDF_orchestrate, --recluster) [SOFT-REPRIO]
                  ├─ Skill(_IDF_orchestrate, --recheck)   [ROLLBACK]
                  └─ Manifest-Update → BDF picks up       [TERMINATE]
```

---

## Hinweise zur Migration (BL-NEW-12 Rollout)

1. **Alte Phase 3 + Phase 4 in `_SDF_orchestrate.md`** sind ENTFERNT, ersetzt durch
   "Pipeline endet nach Phase 2 — Post-Phase via Handschuh-Wechsel im I/SC-Skill"-Hinweis.
2. **I_orchestrate.md** hat einen NEUEN letzten Schritt: `Skill(_SDF_orchestrate_post, ...)`.
3. **SC_orchestrate.md** analog, conditional auf `parent == SDF`.
4. **Resume in Pre-SDF**: Phase 0 ResumeGuard erkennt `--resume --next-batch` und liest
   DF_BATCH_STATE.current_sub_batch_index, springt direkt zu naechstem Batch.
