---
status: DEPRECATED 2026-05-01 (Architektur-Bug — Subagent ruft Skill())
deprecation_reason: |
  Verstoss gegen INV-PM-2: Handschuh-Wechsel = Team-Lead-Aufgabe.
  Ein Berater (Subagent) kann keinen Skill() rufen, weil Skill() den
  ORCHESTRATOR-Kontext laedt, nicht den Worker-Kontext. Frueher gerufene
  Skill(_I_orchestrate)/Skill(_SC_orchestrate)/etc. liefen ins Leere.
  CaseStudy BL-154 Batch 1 2026-05-01: Worker schrieb Manifest in falschen
  Pfad, I_orchestrate startete ohne Kontext.
replacement:
  location: .claude/commands/_SDF_orchestrate.md
  section: SCHRITT 2.1 (Team-Lead-Dispatcher INLINE)
  pattern: |
    SDF-Team-Lead liest DF_BATCH_STATE.modus selbst und ruft Skill(...)
    direkt mit --vault={resolve_bl_path(BL_ID)}-Pfad (INV-VAULT-9 +
    INV-DISPATCH-INLINE-1/2).
do_not_call: true                # Team Lead spawnt diesen Berater NICHT mehr
keep_for_history: true            # Datei bleibt als Audit-Trail erhalten
version: 1.0
created: 2026-04-25
deprecated_at: 2026-05-01
type: berater
sub_type: dispatch
parent: _SDF_orchestrate
ceiling: sonnet
floor: sonnet
actor: _SDF_orchestrate Phase 2 (BATCH-ITEM-LOOP, Schritt 2.2)
feature: BL-133
adr_reference: ADR-9 (Q1-neu Resolution: Quelle SDF, Landeplatz dieser Berater)
ak_implements: [AK-8-01, AK-8-02, AK-8-03, AK-8-04, AK-8-05, AK-8-06]
absorbs:
  - SDF_orchestrate.md SCHRITT 2.2 + 2.2a (Handschuh-Wechsel + SDF-HUB Routing, ~300 LOC vor Slice-4)
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.modus", purpose: "PRIMAER (BL-134): Welcher Modus M1-M9 fuer den Batch"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items", purpose: "BL-134: Liste der zu verarbeitenden PL-Items"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.item_done", purpose: "BL-134: Schon verarbeitete Items (Recovery)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.modusEntscheidung.gewaehlter_modus", purpose: "FALLBACK (BL-133-Pfad + NULL-Schutz)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.df_task", purpose: "Aktuelles BL-Item (NAME)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.batch_current", purpose: "Aktueller Batch-Index"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.handschuh_wechsel_pending", purpose: "Stage-Progression Signal"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.needs_tdd", purpose: "SDF-HUB TDD-Signal (Hub-Invariante #8)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.last_stage_completed", purpose: "Stage-Resume-Anker"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "SC_PIPELINE_STATE.stufe", purpose: "SC pausiert auf SC_NEEDS_IMPL?"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "SC_PIPELINE_STATE.sc_impl_request", purpose: "SC Impl-Mode (FULL/INLINE)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "WP_PIPELINE_STATE.phase", purpose: "M9 WP-Result Pruefung"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.wp_trigger_question", purpose: "M9 WP-Trigger-Frage"}
    - {file: "_session_params.md", path: "GLOBAL_HIL", purpose: "M9 Fallback-Pfad"}
    - {file: "_session_params.md", path: "tdd_stages", purpose: "TDD-Stufen-Liste (M3, M4-M6 SYMBIOSE)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.patternBrief", purpose: "ARCH-15 BL-153: Pattern-Kontext fuer alle Modi (M1 war blind)"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.executionDispatch", purpose: "Dispatch-Result + gewaehlter Skill-Pfad"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.pipeline_route", purpose: "Active route (A_I/A_SC_I/A_SC_ANALYSE/A_PR_REVIEW/A_WP_RESEARCH)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.current_stage", purpose: "Stage-Progression bei Stage N+1"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.handschuh_wechsel_pending", purpose: "Reset Stage-Progression Signal nach Verarbeitung"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.needs_tdd", purpose: "Reset TDD-Signal nach Verarbeitung"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.worker_mode", purpose: "M4-M6 SYMBIOSE Worker-Mode-Flag"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.parent_team", purpose: "M4-M6 SYMBIOSE parent_team=sc-{NAME}"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.pipeline_mode", purpose: "M4-M6 SYMBIOSE Pipeline-Mode"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "WP_PIPELINE_STATE", purpose: "M9 INIT-State + bl_source_id"}
    - {file: "_session_params.md", path: "impl_mode", purpose: "TEMP: SDF -> Skill Vorgabe (loescht nach Skill-Return)"}
    - {file: "_session_params.md", path: "tdd", purpose: "TEMP: TDD-Flag fuer M3/M6 (loescht nach Skill-Return)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.*", excluding: "executionDispatch"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.df_status (Status-Transitions sind Aufgabe von C7)"}
  calls:
    - {skill: "_I_orchestrate", optional: true, purpose: "M1-M3 + M4-M6 SYMBIOSE Implementation"}
    - {skill: "_SC_orchestrate", optional: true, purpose: "M4-M6 SC-Zyklus + M7 ANALYSE"}
    - {skill: "_SC_implement", optional: true, purpose: "M4-M6 SYMBIOSE INLINE-Mode"}
    - {skill: "_TDD_orchestrate", optional: true, purpose: "M3 + M4-M6 SYMBIOSE TDD-Stufen"}
    - {skill: "_T_orchestrate", optional: true, purpose: "M8 Test-Verifikation"}
    - {skill: "_smoothing", optional: true, purpose: "M8 Quality Gates"}
    - {skill: "_presentation", optional: true, purpose: "M8 Finale Presentation"}
    - {skill: "_WP_orchestrate", optional: true, purpose: "M9 Whitepaper-Research"}
related:
  - _SDF_berater_modusEntscheidung (C3 - liefert Modus-Input fuer Dispatch)
  - _SDF_PostBerater_orchestrate (C9c - ruft Dispatch im Item-Loop)
  - _SDF_berater_recalibrate (C5 - laeuft NACH Dispatch via SCHRITT 2.2b)
---

# _SDF_berater_executionDispatch (Slice-4 NEU)

## Zweck

Modus-Dispatch-Logik fuer SDF Phase 2 (BATCH-ITEM-LOOP). Liest den von C3 gewaehlten Modus
(M1-M9) und routet die Implementation zum richtigen Skill-Pfad. Enthaelt zusaetzlich den
SDF-HUB Routing-Loop (Hub-Invariante #8: I ↔ SDF ↔ TDD ↔ SC).

Wird im Item-Loop nach `_SDF_PreBerater_orchestrate` (C9b) aufgerufen, sobald
`BERATER_OUTPUTS.modusEntscheidung.gewaehlter_modus` gesetzt ist. Ersetzt die ehemals in
`_SDF_orchestrate.md` SCHRITT 2.2 + 2.2a hartcodierten ~300 LOC.

**Warum eigener Berater (BL-133 PL-6):** k_fragilitaet=95 (KERN-LUECKE AK-8). Dispatch-Logik
ist die fragilste Komponente von SDF und musste mechanisch isoliert werden, bevor weitere
SDF-Slices die Hub-Invariante beruehren koennen.

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_executionDispatch                             ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:  BERATER_OUTPUTS.modusEntscheidung.gewaehlter_modus          ║
║          DF_PIPELINE_STATE.df_task / batch_current                   ║
║          I_PIPELINE_STATE.handschuh_wechsel_pending / needs_tdd      ║
║          SC_PIPELINE_STATE.stufe / sc_impl_request                   ║
║          WP_PIPELINE_STATE.phase                                     ║
║          _session_params.md: GLOBAL_HIL, tdd_stages                  ║
║                                                                       ║
║  SCHREIBT: BERATER_OUTPUTS.executionDispatch                          ║
║              {gewaehlter_modus, pipeline_route, skill_chain,         ║
║               started_at, ended_at, status}                          ║
║            DF_PIPELINE_STATE.pipeline_route                           ║
║            I_PIPELINE_STATE.current_stage / handschuh_wechsel_pending║
║            I_PIPELINE_STATE.needs_tdd / worker_mode / parent_team    ║
║            WP_PIPELINE_STATE.phase / wp_trigger_question /           ║
║              wp_task_name / chapter_nr / iteration / bl_source_id    ║
║            _session_params.md: impl_mode, tdd (TEMP)                 ║
║                                                                       ║
║  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                   ║
║                  DF_PIPELINE_STATE.df_status (siehe C7)              ║
║                  Recalibrate-Felder (siehe C5)                       ║
║                                                                       ║
║  RUFT: _I_orchestrate, _SC_orchestrate, _SC_implement,                ║
║        _TDD_orchestrate, _T_orchestrate, _smoothing,                 ║
║        _presentation, _WP_orchestrate                                ║
║                                                                       ║
║  ACTOR: _SDF_orchestrate Phase 2 BATCH-ITEM-LOOP, Schritt 2.2       ║
║                                                                       ║
║  MODELL-TIER: sonnet (Default).                                       ║
║    K-Score §9.2 empfiehlt Opus-Override fuer hohe Edge-Case-Last.    ║
║    Override via _session_params.md: berater_executionDispatch_tier=opus
║                                                                       ║
║  INVARIANTEN:                                                         ║
║    INV-DISPATCH-1: KEINE Test-Logik (das ist _T_orchestrate's Job)   ║
║    INV-DISPATCH-2: Schreibt NUR BERATER_OUTPUTS.executionDispatch    ║
║                    + DF_PIPELINE_STATE.pipeline_route +              ║
║                    Pflicht-Felder I/SC/WP_PIPELINE_STATE fuer Routing║
║    INV-DISPATCH-3: Hub-Invariante #8: I ↔ SDF ↔ TDD ↔ SC bleibt     ║
║                    erhalten (M3 + M4-M6 SYMBIOSE).                  ║
║    INV-DISPATCH-4: M1-SKIP fuer Recalibrate bleibt aufrufer-seitig  ║
║                    (SDF SCHRITT 2.2b), Berater entscheidet das nicht ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_SDF_berater_executionDispatch, args="{NAME}")

Parameter:
  {NAME} — Feature-Name (z.B. "BL-133")

Vorbedingung (alle PASS, sonst NICHT aufgerufen):
  - BERATER_OUTPUTS.modusEntscheidung gesetzt (C3 DONE)
  - BERATER_OUTPUTS.itemContext.blocked == false
  - DF_PIPELINE_STATE.df_status == ITEM_LOOP

Ausgabe:
  - BERATER_OUTPUTS.executionDispatch (siehe Schema unten)
  - DF_PIPELINE_STATE.pipeline_route gesetzt
  - Exitcode: 0=OK, 2=FAIL (unbekannter Modus / unerwarteter State)

Logging-Format (NFR-4):
  [DISPATCH] ENTRY item_id={item_id} modus={modus}
  [DISPATCH] ROUTE={pipeline_route} CHAIN=[{skill1},{skill2},...]
  [DISPATCH] SKILL_CALL skill={skill} args={args}
  [DISPATCH] SKILL_RETURN skill={skill} status={status}
  [DISPATCH] HUB_LOOP iter={n} signal={needs_tdd|stage_progression|none}
  [DISPATCH] EXIT duration={ms}ms status={OK|FAIL}
```

## Modus-Mapping-Tabelle

| Modus | pipeline_route   | Skill-Chain                                                | Args                                          | Anmerkung |
|-------|------------------|------------------------------------------------------------|-----------------------------------------------|-----------|
| M1    | A_I              | _I_orchestrate                                             | `{NAME} --worker-mode`                        | inline, kein Blueprint |
| M2    | A_I              | _I_orchestrate (FULL)                                      | `{NAME}`                                      | KEIN --worker-mode (M2-Fix #16) + Stage-Progression-Loop |
| M3    | A_I              | _I_orchestrate + _TDD_orchestrate (SDF-HUB Loop)           | `{NAME} --worker-mode`                        | Hub-Invariante #8: I↔SDF↔TDD |
| M4    | A_SC_I           | _SC_orchestrate (-I)                                       | `{NAME} {difficulty} {ceiling} {floor} -I`   | SC-INLINE |
| M5    | A_SC_I           | _SC_orchestrate                                            | `{NAME} {difficulty} {ceiling} {floor}`      | SC-FULL Default (haeufigster Weg) |
| M6    | A_SC_I           | _SC_orchestrate + TDD                                      | `{NAME} {difficulty} {ceiling} {floor}`      | SC + TDD |
| M7    | A_SC_ANALYSE     | _SC_orchestrate --mode=analyse                             | `{NAME} {difficulty} {ceiling} {floor} --mode=analyse` | NUR Analyse |
| M8    | A_PR_REVIEW      | _T_orchestrate -> _smoothing -> _presentation              | `{NAME}`                                      | NUR Review, kein Code |
| M9    | A_WP_RESEARCH    | _WP_orchestrate                                            | `{difficulty} {ceiling} {floor} --bl-source={current_bl_id}` | WP heavy loading |

**Quelle:** Explorer E02 Z1399-1403 (Original), nach Slice-3 verschoben in `_SDF_orchestrate.md`
SCHRITT 2.2 (vor Slice-4: Z1382-1582). M4-M6 SYMBIOSE-Routing siehe SCHRITT 2.2a (Z1604-1675).

## Output-Schema (BERATER_OUTPUTS.executionDispatch)

```yaml
BERATER_OUTPUTS:
  executionDispatch:
    item_id:           "BL-133-PL-6"
    cycle_nr:          1
    gewaehlter_modus:  "M2"                  # aus C3
    pipeline_route:    "A_I"                  # gemappt
    skill_chain:                              # gerufene Skills (Reihenfolge)
      - { skill: "_I_orchestrate", args: "BL-133", status: "DONE" }
    sdf_hub_iterations: 0                     # SDF-HUB Loop-Durchgaenge (M3/M4-M6)
    started_at:        "2026-04-25T10:46:00Z"
    ended_at:          "2026-04-25T11:02:30Z"
    status:            "OK"                   # OK | FAIL_UNKNOWN_MODE | FAIL_SKILL_ERROR
    last_berater:      "executionDispatch"
```

## Decision-Tree Pseudo-Code

```
SCHRITT 0: Entry + Input laden (BL-134 Batch-Aware)
  Logge: "[DISPATCH] ENTRY batch_index={DF_BATCH_STATE.batch_index}"

  # BL-134: Modus PRIMAER aus BATCH_STATE, FALLBACK auf BL-133-Pfad
  modus = DF_BATCH_STATE.modus  # PRIMAER (BL-134)
  IF modus == null:
    modus = BERATER_OUTPUTS.modusEntscheidung.gewaehlter_modus  # FALLBACK
  batch_items     = DF_BATCH_STATE.batch_items ?? []
  item_done       = DF_BATCH_STATE.item_done ?? []
  items_to_process = [i FOR i IN batch_items IF i NOT IN item_done]

  difficulty  = DF_PIPELINE_STATE.difficulty
  ceiling     = lies _session_params.md > ceiling ?? "opus"
  floor       = lies _session_params.md > floor ?? "haiku"
  GLOBAL_HIL  = lies _session_params.md > GLOBAL_HIL

  IF modus == null:
    Logge: "[DISPATCH] FAIL: kein Modus (DF_BATCH_STATE.modus + BERATER_OUTPUTS.modusEntscheidung beide leer)"
    BERATER_OUTPUTS.executionDispatch.status = "FAIL_UNKNOWN_MODE"
    Aktualisiere Manifest
    EXIT 2

  # BL-134: Recovery-Edge -- alle Items schon verarbeitet
  IF items_to_process == []:
    Logge: "[DISPATCH] RESUME_DONE: items_to_process leer (alle Items in item_done) -- skip Skill-Call"
    BERATER_OUTPUTS.executionDispatch.status = "RESUME_DONE"
    BERATER_OUTPUTS.executionDispatch.skill_chain = []
    BERATER_OUTPUTS.executionDispatch.ended_at = now()
    Aktualisiere Manifest
    EXIT 0

  # pipeline_route deterministisch aus modus ableiten (E02-Mapping)
  pipeline_route = (modus IN ["M1","M2","M3"]) ? "A_I"
                 : (modus == "M7")             ? "A_SC_ANALYSE"
                 : (modus == "M8")             ? "A_PR_REVIEW"
                 : (modus == "M9")             ? "A_WP_RESEARCH"
                 :                               "A_SC_I"

  DF_PIPELINE_STATE.pipeline_route = pipeline_route
  BERATER_OUTPUTS.executionDispatch.gewaehlter_modus = modus
  BERATER_OUTPUTS.executionDispatch.pipeline_route   = pipeline_route
  BERATER_OUTPUTS.executionDispatch.skill_chain      = []
  BERATER_OUTPUTS.executionDispatch.started_at       = now()
  Aktualisiere Manifest
  Logge: "[DISPATCH] ROUTE={pipeline_route} MODUS={modus}"

  # patternBrief propagieren (ARCH-15, BL-153) — INV-EINSCHUB, NON-BLOCKING
  # Schreibt in KURZLEBIG_PROMPT damit ALLE Modi (inkl. M1-Inline) zugreifen koennen.
  # M1 war bisher pattern-blind: _I_orchestrate --worker-mode bekam kein patternBrief.
  pattern_brief = lies Manifest → BERATER_OUTPUTS.patternBrief ?? null
  IF pattern_brief != null AND (|pattern_brief.matched_patterns ?? []| > 0
                                OR |pattern_brief.matched_semantics ?? []| > 0):
    Schreibe KURZLEBIG_PROMPT.pattern_brief = pattern_brief
    Logge: "[DISPATCH] patternBrief propagiert: {|pattern_brief.matched_patterns ?? []|} Patterns + {|pattern_brief.matched_semantics ?? []|} Semantics — gilt fuer Modus={modus}"
  ELSE:
    Logge: "[DISPATCH] Kein patternBrief (null/leer) — NON-BLOCKING (EMPTY_SEED oder kein Treffer)"

SCHRITT 1: Modus-Switch (M1-M9, Reihenfolge wie SDF Z1382-1582)

  # BL-134-PFLASTER: Sub-Pipelines erhalten in Slice 3 zusaetzlich batch={items_to_process}.
  # Sie iterieren intern sequentiell ueber die Items. Echter parallel-Batch-Refactor folgt
  # in BL-135 (I), BL-136 (SC), BL-137 (TDD), BL-138 (A). Hier wird der Modus EINMAL fuer
  # den gesamten Batch dispatcht; items_to_process geht als Zusatz-Argument an die Sub-Skills.

  IF modus == "M1":
    # Inline: klitzeklein, kein Blueprint
    Schreibe _session_params.md: impl_mode=inline, tdd=false
    Skill(_I_orchestrate, args="{NAME} --worker-mode --batch={items_to_process}")
    skill_chain.append({skill: "_I_orchestrate", args: "{NAME} --worker-mode --batch={items_to_process}", status: "DONE"})
    Loesche impl_mode aus _session_params.md

  ELIF modus == "M2":
    # Standard FULL — KEIN --worker-mode (M2-Fix #16, INV-HW-2)
    Schreibe _session_params.md: impl_mode=standard, tdd=false
    Skill(_I_orchestrate, args="{NAME} --batch={items_to_process}")
    skill_chain.append({skill: "_I_orchestrate", args: "{NAME} --batch={items_to_process}", status: "DONE"})

    # RF-10 STAGE-PROGRESSION LOOP (HiL=off auto, HiL=on User-Bestaetigung)
    manifest.reload()
    m2_stages = [1, 2, 3, 4, 5]
    WHILE true:
      manifest.reload()
      IF manifest.I_PIPELINE_STATE.handschuh_wechsel_pending != true:
        BREAK
      letzte = manifest.I_PIPELINE_STATE.last_stage_completed
      naechste = letzte + 1
      IF naechste > max(m2_stages):
        Logge: "[STAGE-PROGRESSION] M2: alle Stufen done"
        BREAK
      params_hil_m2 = lies _session_params.md
      IF params_hil_m2.HiL == "off":
        Logge: "[STAGE-PROGRESSION] M2 HiL=off: Stage {naechste} automatisch (AK-10-01)"
      ELSE:
        AskUserQuestion: "M2 Stage {letzte} DONE. Stage {naechste}? [JA/ABORT]"
        IF user_choice == "ABORT": BREAK
      manifest.I_PIPELINE_STATE.current_stage = naechste
      manifest.I_PIPELINE_STATE.handschuh_wechsel_pending = false
      manifest.update()
      Skill(_I_orchestrate, args="{NAME} --batch={items_to_process}")
      skill_chain.append({skill: "_I_orchestrate", args: "{NAME} --batch={items_to_process}", status: "DONE"})
    Loesche impl_mode aus _session_params.md

  ELIF modus == "M3":
    # I + TDD via SDF-HUB Loop (Hub-Invariante #8)
    Schreibe _session_params.md: impl_mode=standard, tdd=true
    Skill(_I_orchestrate, args="{NAME} --worker-mode --batch={items_to_process}")
    skill_chain.append({skill: "_I_orchestrate", args: "{NAME} --worker-mode --batch={items_to_process}", status: "DONE"})

    manifest.reload()
    params_tdd = lies _session_params.md
    tdd_stages_m3 = params_tdd.tdd_stages ?? [1, 2, 3, 4, 5]
    WHILE true:
      manifest.reload()
      IF manifest.I_PIPELINE_STATE.needs_tdd == true:
        tdd_stage = manifest.I_PIPELINE_STATE.current_stage
        manifest.I_PIPELINE_STATE.needs_tdd = false
        manifest.I_PIPELINE_STATE.handschuh_wechsel_pending = false
        manifest.update()
        Logge: "[SDF-HUB] I Stage {tdd_stage}: NEEDS_TDD -> TDD"
        Skill(_TDD_orchestrate, args="{NAME} --batch={items_to_process}")
        skill_chain.append({skill: "_TDD_orchestrate", args: "{NAME} --batch={items_to_process}", status: "DONE"})
        Skill(_I_orchestrate, args="{NAME} --worker-mode --batch={items_to_process}")
        skill_chain.append({skill: "_I_orchestrate", args: "{NAME} --worker-mode --batch={items_to_process}", status: "DONE"})
        sdf_hub_iterations += 1
        CONTINUE
      IF manifest.I_PIPELINE_STATE.handschuh_wechsel_pending == true:
        letzte = manifest.I_PIPELINE_STATE.last_stage_completed
        naechste = letzte + 1
        IF naechste > max(tdd_stages_m3):
          Logge: "[STAGE-PROGRESSION] M3: alle Stufen done"
          BREAK
        manifest.I_PIPELINE_STATE.current_stage = naechste
        manifest.I_PIPELINE_STATE.handschuh_wechsel_pending = false
        manifest.update()
        Skill(_I_orchestrate, args="{NAME} --worker-mode --batch={items_to_process}")
        skill_chain.append({skill: "_I_orchestrate", args: "{NAME} --worker-mode --batch={items_to_process}", status: "DONE"})
        sdf_hub_iterations += 1
        CONTINUE
      BREAK
    Loesche impl_mode + tdd aus _session_params.md

  ELIF modus == "M4":
    # SC + Inline (extrem unsicher, kleine Schritte)
    Schreibe _session_params.md: impl_mode=inline, tdd=false
    Skill(_SC_orchestrate, args="{NAME} {difficulty} {ceiling} {floor} -I --batch={items_to_process}")
    skill_chain.append({skill: "_SC_orchestrate", args: "{NAME} ... -I --batch={items_to_process}", status: "DONE"})
    Loesche impl_mode aus _session_params.md

  ELIF modus == "M5":
    # SC + Standard (HAEUFIGSTER WEG, SC-FULL Default)
    Schreibe _session_params.md: impl_mode=standard, tdd=false
    Skill(_SC_orchestrate, args="{NAME} {difficulty} {ceiling} {floor} --batch={items_to_process}")
    skill_chain.append({skill: "_SC_orchestrate", args: "{NAME} ... --batch={items_to_process}", status: "DONE"})
    Loesche impl_mode aus _session_params.md

  ELIF modus == "M6":
    # SC + TDD
    Schreibe _session_params.md: impl_mode=standard, tdd=true
    Skill(_SC_orchestrate, args="{NAME} {difficulty} {ceiling} {floor} --batch={items_to_process}")
    skill_chain.append({skill: "_SC_orchestrate", args: "{NAME} ... --batch={items_to_process}", status: "DONE"})
    Loesche impl_mode + tdd aus _session_params.md

  ELIF modus == "M7":
    # SC pure (NUR Analyse) — kein impl_mode
    Skill(_SC_orchestrate, args="{NAME} {difficulty} {ceiling} {floor} --mode=analyse --batch={items_to_process}")
    skill_chain.append({skill: "_SC_orchestrate", args: "{NAME} ... --mode=analyse --batch={items_to_process}", status: "DONE"})

  ELIF modus == "M9":
    # WP-Modus (Externe Recherche, heavy loading)
    # SCHREIB-REIHENFOLGE (HC-3): WP_PIPELINE_STATE INIT
    Schreibe Manifest:
      WP_PIPELINE_STATE.phase               = "INIT"
      WP_PIPELINE_STATE.wp_trigger_question = A_PIPELINE_STATE.wp_trigger_question
      WP_PIPELINE_STATE.wp_task_name        = NAME
      WP_PIPELINE_STATE.chapter_nr          = 1
      WP_PIPELINE_STATE.iteration           = 0
      WP_PIPELINE_STATE.bl_source_id        = DF_PIPELINE_STATE.current_bl_id
    Logge: "[DISPATCH] M9: WP startet. Frage: '{WP_PIPELINE_STATE.wp_trigger_question}'"
    Skill(_WP_orchestrate, args="{difficulty} {ceiling} {floor} --bl-source={DF_PIPELINE_STATE.current_bl_id} --batch={items_to_process}")
    skill_chain.append({skill: "_WP_orchestrate", args: "... --batch={items_to_process}", status: "DONE"})

    # WP-FAIL-Pruefung (INV-7: WP-FAILED blockiert Pipeline NICHT, OQ-2)
    IF WP_PIPELINE_STATE.phase == "ERROR":
      IF GLOBAL_HIL == "off":
        Logge: "[DISPATCH] M9-FEHLER: Auto-Fallback M7 (non-blocking)"
        # Re-Dispatch als M7 (rekursiver Aufruf intern: SC analyse-only)
        Skill(_SC_orchestrate, args="{NAME} {difficulty} {ceiling} {floor} --mode=analyse")
        skill_chain.append({skill: "_SC_orchestrate", args: "M7-FALLBACK --mode=analyse", status: "DONE"})
      ELSE:
        AskUserQuestion: "WP fehlgeschlagen. RETRY_M9 / FALLBACK_M7 / STOP?"
        IF choice == "RETRY_M9": Skill(_WP_orchestrate, ...) ; skill_chain.append(...)
        ELIF choice == "FALLBACK_M7": Skill(_SC_orchestrate, ... --mode=analyse) ; skill_chain.append(...)
        ELSE: Logge: "[DISPATCH] M9 STOP durch User"
    ELSE:
      Logge: "[DISPATCH] M9-DONE: WP abgeschlossen. Ergebnis: {WP_PIPELINE_STATE.wp_result_ref}"

  ELIF modus == "M8":
    # PR-Review (NUR Analyse + Bewertung, KEIN Code)
    # ANTI-PATTERN-GUARD: KEIN _I_orchestrate, KEIN Worker-Spawn
    Logge: "[DISPATCH] M8 PR-Review: NUR Analyse, KEINE Implementierung"

    # PR-8.1: Test-Verifikation
    Skill(_T_orchestrate, args="{NAME}")
    skill_chain.append({skill: "_T_orchestrate", args: "{NAME}", status: "DONE"})

    # PR-8.2: Quality Gates (AC + Smoothing)
    Skill(_smoothing, args="{NAME}")
    skill_chain.append({skill: "_smoothing", args: "{NAME}", status: "DONE"})

    # PR-8.3: Finale Presentation
    Skill(_presentation, args="{NAME}")
    skill_chain.append({skill: "_presentation", args: "{NAME}", status: "DONE"})
    Logge: "[DISPATCH] M8 PR-Review DONE — Presentation erstellt"

  ELSE:
    # Edge-Case: unbekannter Modus
    Logge: "[DISPATCH] FAIL: unbekannter Modus '{modus}' — Eskalation an SDF"
    BERATER_OUTPUTS.executionDispatch.status = "FAIL_UNKNOWN_MODE"
    Aktualisiere Manifest
    EXIT 2

SCHRITT 2: SDF-HUB Routing (SC-Modi M4/M5/M6 SYMBIOSE, Z1604-1664)

  # HEILIGE TRINITAET: SC ↔ SDF ↔ I ↔ SDF ↔ TDD
  # SC pausiert nach Hypothese (stufe=SC_NEEDS_IMPL) und gibt Handschuh an SDF zurueck.
  # ADR-SDF-HUB-001: TDD via SDF-HUB direkt, kein Blueprint-Duplikat.

  IF modus IN ["M4","M5","M6"]:
    Lies SC_PIPELINE_STATE aus {WORKING_DIR}/_manifest.md
    IF SC_PIPELINE_STATE.stufe == "SC_NEEDS_IMPL":
      sc_impl_request = SC_PIPELINE_STATE.sc_impl_request
      Logge: "[SDF-HUB] SC Z{sc_impl_request.cycle_nr}: Hypothese DONE. Route Implementation"

      IF sc_impl_request.mode == "FULL":
        Manifest: I_PIPELINE_STATE.worker_mode = true
        Manifest: I_PIPELINE_STATE.parent_team = "sc-{NAME}"
        Manifest: pipeline_mode = SC_SYMBIOSE_I_ACTIVE
        Skill(_I_orchestrate, args="{NAME} --worker-mode")
        skill_chain.append({skill: "_I_orchestrate", args: "SYMBIOSE", status: "DONE"})

        # SDF-HUB ROUTING LOOP (Hub-Invariante #8, SC-SYMBIOSE)
        manifest.reload()
        params_sc = lies _session_params.md
        tdd_stages_sc = params_sc.tdd_stages ?? [1, 2, 3, 4, 5]
        WHILE true:
          manifest.reload()
          IF manifest.I_PIPELINE_STATE.needs_tdd == true:
            tdd_stage_sc = manifest.I_PIPELINE_STATE.current_stage
            manifest.I_PIPELINE_STATE.needs_tdd = false
            manifest.I_PIPELINE_STATE.handschuh_wechsel_pending = false
            manifest.update()
            Skill(_TDD_orchestrate, args="{NAME}")
            skill_chain.append({skill: "_TDD_orchestrate", args: "SYMBIOSE", status: "DONE"})
            Skill(_I_orchestrate, args="{NAME} --worker-mode")
            skill_chain.append({skill: "_I_orchestrate", args: "POST_TDD", status: "DONE"})
            sdf_hub_iterations += 1
            CONTINUE
          IF manifest.I_PIPELINE_STATE.handschuh_wechsel_pending == true:
            letzte_sc = manifest.I_PIPELINE_STATE.last_stage_completed
            naechste_sc = letzte_sc + 1
            IF naechste_sc > max(tdd_stages_sc):
              Logge: "[STAGE-PROGRESSION] SC-SYMBIOSE: alle Stufen done"
              BREAK
            manifest.I_PIPELINE_STATE.current_stage = naechste_sc
            manifest.I_PIPELINE_STATE.handschuh_wechsel_pending = false
            manifest.update()
            Skill(_I_orchestrate, args="{NAME} --worker-mode")
            skill_chain.append({skill: "_I_orchestrate", args: "SYMBIOSE-NEXT", status: "DONE"})
            sdf_hub_iterations += 1
            CONTINUE
          BREAK
      ELIF sc_impl_request.mode == "INLINE":
        Skill(_SC_implement, args="{NAME}")
        skill_chain.append({skill: "_SC_implement", args: "{NAME}", status: "DONE"})

      # 2.2a.3: SC --resume-at=ergebnis (Ergebnis sammeln)
      Skill(_SC_orchestrate, args="{NAME} {difficulty} {ceiling} {floor} --resume-at=ergebnis")
      skill_chain.append({skill: "_SC_orchestrate", args: "--resume-at=ergebnis", status: "DONE"})
      Logge: "[SDF-HUB] SC Ergebnis gesammelt"

  # B) M3 + TDD: nach I-Return alle TDD-Stufen sequentiell (kein needs_tdd-Signal)
  ELIF modus == "M3":
    params = lies _session_params.md
    IF params.tdd == true:
      tdd_stages = params.tdd_stages ?? [1, 2, 3, 4, 5]
      Logge: "[SDF-HUB] M3 + TDD: {|tdd_stages|} Stufen nach I-Completion"
      FUER stufe IN tdd_stages:
        Manifest: I_PIPELINE_STATE.current_stage = stufe
        Skill(_TDD_orchestrate, args="{NAME}")
        skill_chain.append({skill: "_TDD_orchestrate", args: "stufe={stufe}", status: "DONE"})

SCHRITT 3: Output-State persist + Exit
  BERATER_OUTPUTS.executionDispatch.skill_chain        = skill_chain
  BERATER_OUTPUTS.executionDispatch.sdf_hub_iterations = sdf_hub_iterations
  BERATER_OUTPUTS.executionDispatch.ended_at           = now()
  BERATER_OUTPUTS.executionDispatch.status             = "OK"
  BERATER_OUTPUTS.executionDispatch.last_berater       = "executionDispatch"
  Aktualisiere Manifest
  Logge: "[DISPATCH] EXIT duration={ms}ms status=OK chain_size={|skill_chain|} hub_iters={sdf_hub_iterations}"
  EXIT 0
```

## Edge-Cases

| Fall                              | Verhalten                                                          |
|-----------------------------------|--------------------------------------------------------------------|
| `modus == null`                   | EXIT 2 (FAIL_UNKNOWN_MODE), SDF eskaliert (Worker-FAIL-Pruefung)   |
| Modus nicht in M1..M9             | EXIT 2 (FAIL_UNKNOWN_MODE), SDF eskaliert                          |
| M9 + WP-Pipeline ERROR + HiL=off  | Auto-Fallback M7 (non-blocking, INV-7)                             |
| M9 + WP-Pipeline ERROR + HiL=on   | AskUserQuestion: RETRY_M9 / FALLBACK_M7 / STOP                     |
| Multi-Modus innerhalb Batch       | Pro Item separat dispatchen (Item-Loop in SDF, INV-DISPATCH-1)     |
| SDF-HUB Loop endlos               | Defensive: Loop bricht bei `needs_tdd=false` UND `handschuh_wechsel_pending=false` (INV-DISPATCH-3) |
| M2/M3 Stage > tdd_stages.max      | Loop-Exit (`alle Stufen done`), `[STAGE-PROGRESSION] alle Stufen done` |
| M1 nach Skill-Return              | KEINE Recalibrate (M1-SKIP, AK-02-05) — nicht hier, sondern in SDF SCHRITT 2.2b (INV-DISPATCH-4) |

## Invarianten

- **INV-DISPATCH-1:** Kein Test-Code in diesem Berater. Test-Logik (`_T_orchestrate`)
  wird via Skill-Call gerufen (M8), aber nicht hier definiert.
- **INV-DISPATCH-2:** Schreib-Isolation. Nur `BERATER_OUTPUTS.executionDispatch` und
  `DF_PIPELINE_STATE.pipeline_route` plus die Pflicht-Felder fuer das Routing
  (I/SC/WP_PIPELINE_STATE Init/Reset). Keine `df_status`-Transitions (siehe C7),
  keine Recalibrate-Felder (siehe C5).
- **INV-DISPATCH-3:** Hub-Invariante #8 bleibt erhalten. SDF ist IMMER zwischen I, TDD
  und SC. Direkter `_TDD_orchestrate`-Aufruf aus M3 nutzt das `needs_tdd`-Signal,
  M4-M6 SYMBIOSE-Loop konsumiert dasselbe Signal.
- **INV-DISPATCH-4:** Recalibrate-Skip fuer M1 ist Aufrufer-Sache. Berater erfaehrt
  keine M1-Sonderbehandlung -- SDF SCHRITT 2.2b (RECALIBRATE-GUARD) liest `modus != M1`
  und ruft C5.
- **INV-DISPATCH-5:** Batch-Aware (BL-134). Liest Modus aus `DF_BATCH_STATE.modus`
  (PRIMAER), faellt zurueck auf `BERATER_OUTPUTS.modusEntscheidung.gewaehlter_modus`
  (BL-133 Legacy/NULL-Schutz). Gibt `batch={items_to_process}` als Pflaster-Parameter
  an Sub-Pipelines weiter (echter parallel-Batch in BL-135ff). Bei `items_to_process==[]`
  Recovery-Pfad: kein Skill-Call, Status `RESUME_DONE`.

## Akzeptanzkriterien-Mapping (BL-133 AK-8)

| AK-Item | Erfuellt durch |
|---------|----------------|
| AK-8-01 (Quelle: SDF SCHRITT 2.2 + 2.2a) | Modus-Switch (M1-M9) + SDF-HUB Routing aus SDF Z1382-1664 vollstaendig erfasst |
| AK-8-02 (Landeplatz: dieser Berater)     | Datei `_SDF_berater_executionDispatch.md` erstellt, Frontmatter `type: berater` |
| AK-8-03 (alle 9 Modi M1-M9)              | Modus-Mapping-Tabelle + Decision-Tree decken M1..M9 ab |
| AK-8-04 (Edge-Cases)                     | Edge-Case-Tabelle (8 Faelle) + INV-DISPATCH-1..4 |
| AK-8-05 (Hub-Invariante #8)              | INV-DISPATCH-3 + SCHRITT 2 SDF-HUB SYMBIOSE-Loop |
| AK-8-06 (State-Schreibrechte minimal)    | INV-DISPATCH-2 + VERTRAG-NOT_WRITES-Liste |

## Schnitt-Begruendung (vs. C3 modusEntscheidung)

C3 entscheidet WELCHEN Modus (M1..M9). Dieser Berater entscheidet WIE der Modus
ausgefuehrt wird (Skill-Pfad, Args, Hub-Routing). Beide bleiben getrennt, weil:

1. **C3 ist deterministisch** (gleicher Input -> gleicher Modus, ausser begruendung).
2. **executionDispatch ist stateful** (SDF-HUB Loop liest/schreibt I_PIPELINE_STATE
   ueber mehrere Iterationen, nicht-deterministisch nach Anzahl Iterationen).
3. **Fragility unterscheidet sich:** C3 fragility=70 (Logik-Tiefe), Dispatch fragility=95
   (Skill-Reihenfolge + Hub-Loop + State-Mutationen).

## Test-Hinweise (fuer spaeteres _T_orchestrate)

Nicht Aufgabe dieses Beraters, aber als Erinnerung:
- T1: Pro Modus 1 Happy-Path-Test (M1..M9, 9 Tests)
- T2: Edge-Case `modus == null` (EXIT 2)
- T3: SDF-HUB Loop M3 mit `needs_tdd=true` Sequenz (mind. 2 Iterationen)
- T4: M9 WP-FAIL + HiL=off Auto-Fallback M7
- T5: INV-DISPATCH-2 Property-Test: keine Writes ausserhalb erlaubter Pfade
