---
status: active
version: 1.0.0
created: 2026-04-26
op: ImplementationPipeline
phase: stufenLoop
type: berater
chain_position: middle
model_tier: ceiling
---

# /_I_berater_blueprintLoop (STUFEN-LOOP — Blueprint-Phase pro Stufe N)

[VERTRAG]
- LIEST:  manifest.I_PIPELINE_STATE.current_stage, impl_test_stages, tdd_pipeline_mode,
          tdd_alarm, tdd_stage_result, tdd_start_time, stage_metadaten
          .claude/meta/implementation/stage_{N}.md
          _session_params.md (testRun, GLOBAL_HIL)
- SCHREIBT: manifest.I_PIPELINE_STATE.current_stage, impl_test_stages[N].status,
            stage_metadaten, tdd_pipeline_mode, tdd_start_time, tdd_alarm,
            last_stage_completed, handschuh_wechsel_pending, phase
- OUTPUT:   BERATER_OUTPUTS.blueprintLoop.stageResult,
            BERATER_OUTPUTS.blueprintLoop.handschuhWechsel,
            BERATER_OUTPUTS.blueprintLoop.postTddResult
- CROSS-REF: Phase 3 teamLeadSteuerung (SDF_berater_sdfHub NEEDS_TDD-Signal,
             Hub-Invariante #8: I ↔ SDF ↔ TDD — SDF ist IMMER dazwischen)
             _TDD_orchestrate (via SDF-Routing, NICHT direkt)
             _stage_orchestrate (PLAYBOOK-WECHSEL nach Stage-DONE)

---

## INVARIANTEN

- INV-1: Team Lead spawnt fuer JEDEN Post-Blueprint-Schritt einen eigenen Worker
- INV-2: Team Lead schreibt/liest NUR Manifest + Tasks zwischen Schritten
- INV-3: Workers lesen Primaerquellen, fuehren 1 Command aus, Shutdown
- INV-4: NIEMALS einen Mega-Agent fuer "Impl + Tests + Build + Docker + dotnet test"
- INV-5: Team Lead laedt Skills SELBST via Skill-Tool, nicht per Agent delegieren
- INV-6: Handschuh-Wechsel am Ende Blueprint: I → SDF (needs_tdd=true), NICHT direkt zu TDD
- INV-7: SDF ist IMMER zwischen I und TDD (Hub-Invariante #8)

---

## PSEUDOCODE

```
# Single-Stage-Execution: I_orchestrate bearbeitet NUR current_stage.
# SDF ist verantwortlich fuer Stage-Progression (N → N+1).
# Nach TDD-GREEN gibt I_orchestrate via handschuh_wechsel_signal() Kontrolle an SDF zurueck.
# SDF erhoeht current_stage und startet I_orchestrate neu (Puppet-Master-Pattern).
N = manifest.I_PIPELINE_STATE.current_stage
```

---

## SUB-PHASE A: Stage-Entry + Metadaten

```
  metadaten = lade_stage_n(N)
  # lade_stage_n: Liest {WORKTREE_PATH}/.claude/meta/implementation/stage_{N}.md
  # Felder: stufe, name, fokus, testbefehl, blueprint_perspektive, fanout,
  #         mocks_erlaubt, ressourcen_constraints, exit_criteria, parallelitaet_max
  IF metadaten.status == "placeholder" OR (metadaten.status != "placeholder" AND metadaten.testbefehl == "TBD"):
    → HiL: "Stufe {N}: status={metadaten.status}, testbefehl={metadaten.testbefehl}. [KONFIGURIEREN] [SKIP] [ABORT]"
    → Falls SKIP: impl_test_stages[N].status = "skipped", CONTINUE naechste Stufe

  # Stage-Entry-Contract (AK9/AK18, TestStufen Spec):
  # Stage N darf NUR starten wenn Stage N-1 exit_criteria alle PASS (impl_test_stages[N-1].status == "done").
  IF N > 1 AND manifest.I_PIPELINE_STATE.impl_test_stages[N-1].status != "done":
    Logge: "[STAGE-ENTRY-CONTRACT] Stage {N} BLOCKIERT: Stage {N-1} nicht 'done' (status={manifest.I_PIPELINE_STATE.impl_test_stages[N-1].status})"
    → STOPP

  # Stage-Metadaten ins Manifest fuer nachgelagerte Worker (AK6/AK7: Blueprint Stage-Awareness)
  manifest.I_PIPELINE_STATE.current_stage = N
  manifest.I_PIPELINE_STATE.impl_test_stages[N].status = "running"
  manifest.I_PIPELINE_STATE.stage_metadaten = {
    blueprint_perspektive: metadaten.blueprint_perspektive,  # Laserpointer|Taschenlampe|Scheinwerfer|Flutlicht
    testbefehl: metadaten.testbefehl,
    mocks_erlaubt: metadaten.mocks_erlaubt,                 # ja|nein (AK12)
    fanout: metadaten.fanout,
    fokus: metadaten.fokus
  }
  manifest.update()
  Logge: "[STAGE-METADATEN] Stage {N}: perspektive={metadaten.blueprint_perspektive}, mocks={metadaten.mocks_erlaubt}, test={metadaten.testbefehl}"
```

---

## SUB-PHASE B: testRun-GUARD

```
  # ═══ testRun-GUARD (TestStufen Z1) ═══
  # testRun = true → Abkuerzung: KEIN Blueprint, KEIN Architect, KEIN goldDefine
  # NUR: testSearch → TDD_orchestrate(testRun=true) → handschuh_wechsel
  testRun = lies(_session_params.md → testRun) ?? false
  IF testRun == true:
    Logge: "[testRun] Stage {N}: Abkuerzung aktiv — nur testSearch + execute"
    # Schritt 1: testSearch (Tests fuer aktuelle Stufe finden)
    Skill(skill="_I_testSearch", args="{NAME} --stufe {N}")
    # Schritt 2: TDD execute-only (keine Red/Green/Refactor)
    Skill(skill="_TDD_orchestrate", args="{NAME} --testRun")
    # Schritt 3: handschuh_wechsel an SDF (wie normal)
    → handschuh_wechsel_signal(stage=N, status=COMPLETE)
    RETURN
  # ═══ Ende testRun-GUARD ═══
```

---

## SUB-PHASE C: Blueprint (Arch + RequirementCheck + PatternLibrary + TestSearch + GoldDefine + QG + Slice)

```
  # Bootstrap Kanarienvogel (NUR Stufe 1)
  IF N == 1:
    verify_output = suche_datei("synthese/{NAME}-VERIFY*.md")
    IF vorhanden: guard_tests als Kanarienvogel-Kandidaten
    ELSE: Architect leitet aus Spec-Systemgrenze ab

  # Schritt 1: cleanCodeArchitect (5-3-1 Wellen, W3=opus — HOCH: Architektur-Entscheidungen)
  # AK6/AK7: Blueprint liest stage_metadaten.blueprint_perspektive aus Manifest:
  #   S1=Laserpointer (atomare Einheiten), S2=Taschenlampe (Module),
  #   S3=Scheinwerfer (Integration), S4=Flutlicht (System)
  # Worker nutzt perspektive als Granularitaets-Signal fuer Slice-Schnitt.
  spawne_wellen("cleanCodeArchitect", slice, N)  # W3 = ceiling (Default opus, gecappt durch session.ceiling)

  # Schritt 1a: requirementCheck (BLOCKER-faehig) [NEU: CaseStudy KV-1]
  spawne_worker("requirementCheck", "--stufe N")
  → REQCHECK-S{N}.md: Feld-Coverage-Matrix, AK-Text-Verifikation
  → BEI BLOCKER: Pipeline stoppt (kein codeAtomic bis Klaerung)
  → BEI PASS/WARN: weiter zu patternLibrary

  # Schritt 1b: patternLibrary (1 Agent, mechanisch — KEINE Wellen) [NEU: BL-044]
  # Verschoben von Schritt 4 auf 1b (nach Architect, VOR Slicing).
  # Pattern-Zuweisung frueh verfuegbar fuer testSearch, goldDefine und cleanCodeSlice.
  spawne_worker("patternLibrary", "--stufe N")

  # Schritt 1c: architecturalLibrary (1 Agent, mechanisch — KEINE Wellen) [NEU: BL-154]
  # Nach patternLibrary, vor testSearch.
  # Prueft Blueprint gegen ARCH-VERTRAG-Block (architecturalBrief von SDF Phase 1.0).
  # NON-BLOCKING: Falls architecturalBrief fehlt oder EMPTY_SEED → SKIP, kein Abbruch.
  spawne_worker("architecturalLibrary", "--stufe N")

  # Schritt 2: testSearch (1 Agent, mechanisch — KEINE Wellen)
  spawne_worker("testSearch", "--stufe N")

  # Schritt 3: goldDefine (1 Agent, mechanisch — KEINE Wellen)
  # PFLICHT-HINWEIS (RF-CS-011, W10): goldDefine MUSS Content-Assertions liefern.
  # Content-Assertion = konkreter Pruefpunkt fuer Gold-Standard (nicht nur "Test X vorhanden").
  # Beispiel: "UserService.CreateUser gibt UserId != null zurueck" (NICHT: "Test laeuft durch").
  spawne_worker("goldDefine", "--stufe N")

  # Schritt 4: blueprintQG (max 3 Retries, 1 Agent pro Versuch)
  qg_retries = 0
  WHILE qg_retries < 3:
    spawne_worker("blueprintQG", "--stufe N")
    IF blueprint.qg_blueprint == "pass": BREAK
    qg_retries += 1
    IF qg_retries >= 3: HiL ("3x FAIL: (a) Fix (b) FORCE (c) ABORT")
  Manifest: I_PIPELINE_STATE.blueprint_retry_count = qg_retries  # AK-04-03, BL-036

  # Schritt 5: cleanCodeSlice (1 Slice bei slicing=false — BL-NEW-29 Batch-as-Slice)
  # BL-NEW-29 2026-05-11: Bei slicing=false produziert dieser Schritt EXAKT 1 Slice
  # (= ganzer Batch). cleanCodeSlice-Worker macht Code-Planung + Pattern-Reuse
  # fuer den 1 Slice. Bei slicing=true (Legacy/Forward-Compat) Multi-Slice-Modus.
  IF slicing == false:
    slices = [batch_as_single_slice]   # 1 Eintrag, deckt den ganzen Batch ab
    Logge: "[BL-NEW-29] slicing=false: 1 Slice = ganzer Batch (Batch-as-Slice)"
  ELSE:
    slices = extrahiere_slices_aus_blueprint(N)
    Logge: "slicing=true (Legacy): {len(slices)} Sub-Slices aus Blueprint extrahiert"
  FOR EACH slice: spawne_wellen("cleanCodeSlice", slice, N)
  warte_bis_alle_completed(slices)

  # WARNING-CHECK nach cleanCodeSlice-Loop (RF-CS-012, W16)
  # Baseline-Erfassung VOR Aenderungen (im Architect-Schritt) + Delta nach Slice-Abschluss.
  # Wenn warnungen_neu > 0: Logge Liste der neuen Warnungen. KEIN Abbruch — nur Sichtbarkeit.
  warnungen_neu = [w fuer w in aktuelle_warnungen wenn w NOT IN warnungen_baseline]
  IF len(warnungen_neu) > 0:
    Logge WARNUNG: "[WARNING-CHECK] {len(warnungen_neu)} neue Warnungen nach Stufe {N}:"
    FOR w IN warnungen_neu: Logge: "  - {w}"

  # Schritt 6: mitose + fanOut (NUR bei slicing=true UND Multi-Slice)
  IF worktree_parallel == true AND len(slices) > 1:
    spawne_wellen("mitose", NAME, N)
    spawne_wellen("fanOut", slice, N)
  ELIF worktree_parallel == false:
    Logge: "slicing=false: SKIP mitose/fanOut — Slices sequentiell im gleichen Branch"
  ELSE:
    Logge: "Single-Slice: SKIP mitose/fanOut"
```

---

## SUB-PHASE D: Puppet-Master-Block (nach Blueprint DONE, vor TDD-Handoff)

```
  # ═══════════════════════════════════════════════════════════════════════
  # PFLASTER 2026-04-20 — PUPPET-MASTER-REGELN I→TDD (uebernommen von A-Pipeline)
  # ═══════════════════════════════════════════════════════════════════════
  # Analog zu _A_orchestrate.md Zeile 316-331 "Autonomie-Guard (Puppet Master)".
  # Gilt BEGINNEND bei Blueprint-Phase DONE (Schritte 1-6) bis POST_TDD-Rueckkehr.
  #
  # I-PIPELINE PUPPET-MASTER REGELN (CaseStudy BL-125 AK-6):
  #   1. Team Lead spawnt fuer JEDEN Post-Blueprint-Schritt einen eigenen Worker
  #   2. Team Lead schreibt/liest NUR Manifest + Tasks zwischen Schritten
  #   3. Workers lesen Primaerquellen, fuehren 1 Command aus, Shutdown
  #   4. NIEMALS einen Mega-Agent fuer "Impl + Tests + Build + Docker + dotnet test"
  #   5. Team Lead laedt Skills SELBST via Skill-Tool, nicht per Agent delegieren
  #   6. Handschuh-Wechsel am Ende Blueprint: I → SDF (needs_tdd=true), NICHT direkt zu TDD
  #
  # EXPLIZITE TDD-HANDOFF-SEQUENZ (Team Lead direkt, KEINE Agent()-Calls):
  #   TDD_HANDOFF = [
  #     {step: "P1.0", aktion: "TBD-Guard + tdd_stages-Filter"},
  #     {step: "P1.1", aktion: "TDD_INSTRUCTIONS.md befuellen"},
  #     {step: "P1.2", aktion: "tdd_start_time + Alarm-Reset"},
  #     {step: "P1.3", aktion: "tdd_pipeline_mode = I_TDD_ACTIVE"},
  #     {step: "P1.4", aktion: "needs_tdd=true, handschuh_wechsel_pending=true"},
  #     {step: "P1.5", aktion: "RETURN an SDF (PAUSE I)"},
  #   ]
  #   Nach P1.5: Team Lead PAUSIERT — kein Code, kein Worker, keine Agent()-Calls.
  #   SDF uebernimmt: ruft TDD_orchestrate, das seine 7b-11 Schritte mit
  #   eigenen Workers orchestriert. Erst POST_TDD Rueckkehr reaktiviert I.
  # ═══════════════════════════════════════════════════════════════════════

  # ═══════════════════════════════════════════════════════════════════════
  # PFLASTER 2026-04-20 — MEGA-WORKER-BLOCK (BL-125 AK-6 Case Study)
  # ═══════════════════════════════════════════════════════════════════════
  # NACH Blueprint-Phase DONE (Schritte 1-6) UND VOR P1.5 Handschuh-Wechsel
  # der Team Lead DARF AB HIER KEINE Agent()-Calls mehr machen bis SDF
  # zurueckkommt mit POST_TDD-Signal.
  #
  # VERBOTEN (AK-6 Session-Fehler — Mega-Worker-Anti-Pattern):
  #   - Agent(prompt="Impl + Tests + Build + Docker + dotnet test")  ← BLOCK
  #   - Agent(prompt="impl-tests-ak{N}")                              ← BLOCK
  #   - Agent(prompt="Controller schreiben + Integration-Tests")      ← BLOCK
  #   - Skill("_TDD_orchestrate") direkt vom Team Lead hier           ← BLOCK
  #
  # ERLAUBT (Hub-Invariante #8, Heilige Trinitaet):
  #   1. P1.0-P1.4 (TBD-Guard, TDD_INSTRUCTIONS, Alarm-Reset, Mode-Wechsel)
  #   2. P1.5: needs_tdd=true setzen, handschuh_wechsel_pending=true, RETURN
  #   3. SDF erkennt needs_tdd=true, ruft _TDD_orchestrate
  #   4. TDD fuehrt Ring-Planung (7b) + RED-First (8a-8i) durch
  #   5. TDD-DONE → SDF ruft I fuer POST_TDD Resume (R1-R4)
  #
  # BEGRUENDUNG: Team Lead hat in BL-125 AK-6 einen Mega-Worker gespawnt
  # der Impl + TestBase-Helper + 6 Integration-Tests + Docker + dotnet test
  # in EINEM Agent-Call erledigen sollte. Das verletzt:
  #   - INV-PM-1 (kein Mega-Agent)
  #   - Hub-Invariante #8 (I ↔ SDF ↔ TDD, kein Direct-Call)
  #   - Strict-TDD Ring-Planung (Schritt 7b uebersprungen)
  #   - RED-First (Code vor Test geschrieben)
  #
  # CONTROL-FLOW-BEWEIS: Nach diesem Pflaster MUSS der Code-Pfad strikt
  # von Schritt 6 → P1.0 → P1.1 → ... → P1.5 RETURN gehen. Jeder
  # Agent()-Call in diesem Block ist eine Prozess-Verletzung.
  # ═══════════════════════════════════════════════════════════════════════
```

---

## SUB-PHASE E: TDD-Uebergabe (P1.0-P1.5)

```
  # ═══ UEBERGABE AN TDD-PHASE (Phase 1: P1.0-P1.5) ═══

  # P1.0: TBD-Guard + tdd_stages-Filter (RF-02)
  IF N NOT IN tdd_stages:
    Logge: "[TDD-SKIP] Stufe {N} nicht in tdd_stages={tdd_stages}. SKIP."
    impl_test_stages[N].status = "skipped"
    CONTINUE

  testbefehl = lade_stage_n(N).testbefehl
  IF testbefehl starts_with "TBD":
    IF GLOBAL_HIL == "off":
      tdd_pipeline_mode_wechsel("I", "I_TDD_SKIPPED", N, "testbefehl=TBD + HiL=off")
      impl_test_stages[N].status = "skipped"
      CONTINUE
    ELSE:
      testbefehl = AskUserQuestion("Stufe {N}: testbefehl=TBD. Konkreten Befehl angeben:")

  # P1.1: tdd_pipeline_mode = I_TDD_PREP
  tdd_pipeline_mode_wechsel("I", "I_TDD_PREP", N, "TDD-Vorbereitung Stufe {N}")

  # P1.2: TDD_INSTRUCTIONS.md befuellen (Schritt 7a-Logik, bereits in TDD implementiert)

  # P1.3: Zeitmarkierung + Alarm-Reset
  manifest.I_PIPELINE_STATE.tdd_start_time = jetzt_iso8601()
  manifest.I_PIPELINE_STATE.tdd_alarm = { triggered: false }

  # P1.4: tdd_pipeline_mode = I_TDD_ACTIVE
  tdd_pipeline_mode_wechsel("I_TDD_PREP", "I_TDD_ACTIVE", N, "Playbook-Wechsel")

  # P1.5: TDD aufrufen — SDF-HUB Routing (Hub-Invariante #8)
  # ═══ ANTI-PATTERN: Skill("_TDD_orchestrate") direkt ← VERBOTEN (Hub-Invariante) ═══
  # RICHTIG: Signal an SDF → SDF routet zu TDD → TDD DONE → SDF routet zurueck zu I
  # Heilige Trinitaet: I ↔ SDF ↔ TDD — SDF ist IMMER dazwischen.
  manifest.I_PIPELINE_STATE.phase = "NEEDS_TDD"
  manifest.I_PIPELINE_STATE.needs_tdd = true
  manifest.I_PIPELINE_STATE.handschuh_wechsel_pending = true
  manifest.update()
  Logge: "[SDF-HUB] I Stage {N}: NEEDS_TDD → Handschuh zurueck an SDF."
  RETURN  # I pausiert — SDF uebernimmt TDD-Routing
  # SDF erkennt needs_tdd=true, ruft TDD, dann I fuer POST_TDD Resume (R1-R4).
```

---

## SUB-PHASE F: POST_TDD Resume (R1-R4)

```
  # ═══ RUECKKEHR AUS TDD-PHASE (Phase 3: R1-R4) ═══ # (Z2: W257, Hub-Invariante #8)

  # Schritt R1: Manifest neu laden (TDD hat geschrieben)
  manifest.reload()

  # Schritt R2: tdd_pipeline_mode pruefen + 2h-Timeout
  aktueller_tdd_mode = manifest.I_PIPELINE_STATE.tdd_pipeline_mode ?? "I_TDD_ACTIVE"
  IF aktueller_tdd_mode NOT IN ["I_TDD_DONE", "I_TDD_ABORTED", "I_TDD_ALARM", "I_TDD_SKIPPED"]:
    tdd_start = manifest.I_PIPELINE_STATE.tdd_start_time
    IF tdd_start != null:
      elapsed = jetzt() - parse_iso8601(tdd_start)
      IF elapsed > 2h:
        Logge WARNUNG: "[TDD-TIMEOUT] Stufe {N}: TDD antwortet nicht seit {elapsed}."
        tdd_pipeline_mode_wechsel("I_TDD_ACTIVE", "I_TDD_ABORTED", N, "Timeout >2h")
        manifest.I_PIPELINE_STATE.tdd_stage_result = {
          stufe: N, stufen_ergebnis: "STUCK",
          stuck_grund: "Timeout: TDD antwortet nicht seit {elapsed}",
          alarm_empfehlung: "SC_ANALYSE"
        }
        manifest.update()
        aktueller_tdd_mode = "I_TDD_ABORTED"
      ELSE:
        IF GLOBAL_HIL != "off":
          HiL: "TDD-Phase: tdd_pipeline_mode={aktueller_tdd_mode}. [WARTEN] [SKIP] [ABORT]"
        ELSE:
          tdd_pipeline_mode_wechsel(aktueller_tdd_mode, "I_TDD_ABORTED", N, "HiL=off Fallback")
          aktueller_tdd_mode = "I_TDD_ABORTED"
    ELSE:
      Logge WARNUNG: "[TDD-TIMEOUT] tdd_start_time fehlt -> Skip Timeout-Check."

  # Schritt R3a: tdd_alarm pruefen (Kern E3)
  tdd_alarm = manifest.I_PIPELINE_STATE.tdd_alarm
  IF tdd_alarm.triggered == true:
    Logge: "[TDD-ALARM] S{N}: {tdd_alarm.stuck_stage} -> {tdd_alarm.recommendation}"
    tdd_pipeline_mode_wechsel(aktueller_tdd_mode, "I_TDD_ALARM", N,
      "tdd_alarm.triggered=true")
    aktueller_tdd_mode = "I_TDD_ALARM"

    IF tdd_alarm.recommendation == "SC_ANALYSE":
      IF GLOBAL_HIL != "off":
        antwort = AskUserQuestion(
          "[TDD-ALARM] S{N}: {tdd_alarm.grund}\n"
          "[SC_ANALYSE] [SKIP_STUFE] [WEITER] [ABORT]")
        SWITCH antwort:
          "SC_ANALYSE": manifest.pipeline_mode = "SC_ANALYSE"
          "SKIP_STUFE": impl_test_stages[N].status = "skipped"
          "WEITER":     Logge: "User ueberstimmt Alarm."
          "ABORT":      manifest.pipeline_mode = "SC_RECOVERY"
      ELSE:
        Logge: "[TDD-ALARM] HiL=off -> Auto: pipeline_mode=SC_ANALYSE"
        manifest.pipeline_mode = "SC_ANALYSE"

    ELIF tdd_alarm.recommendation == "SKIP_STUFE":
      impl_test_stages[N].status = "skipped"

    ELIF tdd_alarm.recommendation == "ABORT":
      manifest.pipeline_mode = "SC_RECOVERY"

  # Schritt R3b: tdd_stage_result konsumieren (erweitertes Schema)
  tdd_result = manifest.I_PIPELINE_STATE.tdd_stage_result
  IF tdd_result != null:
    impl_test_stages[N].status = tdd_result.stufen_ergebnis
    impl_test_stages[N].tdd_details = tdd_result
  ELSE:
    impl_test_stages[N].status = "partial"

  # Schritt R4: Zuruecksetzen
  tdd_pipeline_mode_wechsel(manifest.I_PIPELINE_STATE.tdd_pipeline_mode, "I", N,
    "Phase 3 abgeschlossen")
  manifest.I_PIPELINE_STATE.tdd_alarm.triggered = false  # Reset (AK-03-5)
  manifest.I_PIPELINE_STATE.phase = "POST_TDD_CONSUMED"
  manifest.update()
```

---

## SUB-PHASE G: QP-Block + Stage-Transition + Handschuh-Wechsel

```
  # ═══ QP-BLOCK (Inline-Stub, Slice 2 Δ7) ═══
  # Prueft ob Stage N die exit_criteria erfuellt (Kanarienvogel + diffAudit light).
  # STUB: vollstaendige Implementierung folgt in einem spaeteren Zyklus.
  stage_N_qp_done = false
  IF impl_test_stages[N].status IN ["done", "PASS"]:
    kanarienvogel_ok = (impl_test_stages[N].kanarienvogel_status == "PASS") OR (impl_test_stages[N].kanarienvogel_status == null)
    diffAudit_light_flag = true  # STUB: immer PASS bis diffAudit-Integration (AK10)
    stage_N_qp_done = kanarienvogel_ok AND diffAudit_light_flag
    IF NOT stage_N_qp_done:
      Logge WARNUNG: "[QP-BLOCK] Stage {N}: QP nicht bestanden (kanarienvogel={impl_test_stages[N].kanarienvogel_status})."

  # ═══ STAGE-TRANSITION: Commit + Weiter zur naechsten Stufe ═══
  #
  # Nach jeder abgeschlossenen Stufe: Arbeit committen, dann naechste Stufe.
  # Bei HiL=off: AUTONOM (kein Fragen, kein Warten).
  # Bei HiL=on: User entscheidet.

  IF impl_test_stages[N].status == "done" OR impl_test_stages[N].status == "PASS":
    # Stufe erfolgreich — Stage committen via /_stage_orchestrate
    # WICHTIG: /_stage_orchestrate ist ein PLAYBOOK-WECHSEL (wie /_TDD_orchestrate).
    # Es ist ein Dialog zwischen Team Lead und Stage-Worker:
    #   TL = Richtlinie + Quality Gate (kein git, nur Dialog)
    #   Stage-Worker = Staging + Grouping + Hunks + Commit
    #   Worker fragt TL vor JEDEM Commit. TL begleitet durch Prozess.
    # Daher: Team Lead laedt /_stage_orchestrate als Skill, NICHT spawne_worker.

    IF GLOBAL_HIL == "off":
      # AUTONOM: /_stage_orchestrate als Playbook laden + durchfuehren
      Logge: "[STAGE-TRANSITION] S{N} DONE → /_stage_orchestrate (autonom, HiL=off)"
      manifest.I_PIPELINE_STATE.phase = "STAGE_COMMIT"
      manifest.update()
      # [PLAYBOOK-WECHSEL] Team Lead laedt /_stage_orchestrate
      # /_stage_orchestrate hat dark_factory_capable: true — laeuft autonom bei HiL=off
      Skill(skill="_stage_orchestrate")
      Logge: "[STAGE-TRANSITION] S{N} committed. Weiter zu Stufe {N+1}."
      manifest.I_PIPELINE_STATE.phase = "POST_TDD_CONSUMED"
      manifest.update()
      # KEIN AskUserQuestion — direkt CONTINUE zum naechsten Loop-Durchlauf
    ELSE:
      # HiL aktiv: User fragen
      antwort = AskUserQuestion(
        "Stufe {N} abgeschlossen (GOLD). Naechste Schritte:\n"
        "  [COMMIT+WEITER] /_stage_orchestrate + Stufe {N+1}\n"
        "  [WEITER]        Ohne Commit zu Stufe {N+1}\n"
        "  [PAUSE]         Hier stoppen (manuell weiter)")
      IF antwort IN ["COMMIT+WEITER", "COMMIT"]:
        manifest.I_PIPELINE_STATE.phase = "STAGE_COMMIT"
        manifest.update()
        Skill(skill="_stage_orchestrate")
        manifest.I_PIPELINE_STATE.phase = "POST_TDD_CONSUMED"
        manifest.update()
      IF antwort != "PAUSE":
        Logge: "Stufe {N} abgeschlossen. Handschuh-Wechsel an SDF → Stage {N+1}."
      ELSE:
        Logge: "PAUSE — User steuert manuell weiter."
        # POST_PIPELINE-Phase sicherstellen (R1: kein Handschuh-Wechsel bei PAUSE)
        → SPRING ZU: "NACHPHASE (Post-Pipeline)"

  # ═══ HANDSCHUH-WECHSEL AN SDF (Stage-Progression) ═══
  # ERSETZT das ehemalige CONTINUE.
  # I_orchestrate gibt Kontrolle zurueck an SDF.
  # SDF erhoecht current_stage (N → N+1) und startet I_orchestrate neu.
  # Wenn N == letzte Stage: POST_PIPELINE via SDF (SDF erkennt N+1 > max_stage).

  # Stage-Completion Persistenz (AK14, BugFix #4):
  # KRITISCH: last_stage_completed MUSS hier gesetzt werden, nicht nur in TDD.
  # Ohne dieses Update: SDF liest last_stage_completed=0 → Loop auf Stage 1 (bei tdd=false).
  manifest.I_PIPELINE_STATE.last_stage_completed = N
  manifest.I_PIPELINE_STATE.impl_test_stages[N].status = "done"
  manifest.I_PIPELINE_STATE.impl_test_stages[N].completed_at = jetzt()
  manifest.I_PIPELINE_STATE.handschuh_wechsel_pending = true
  manifest.I_PIPELINE_STATE.phase = "HANDSCHUH_WECHSEL"
  manifest.update()
  Logge: "[HANDSCHUH-WECHSEL] Stufe {N} DONE. last_stage_completed={N}, handschuh_wechsel_pending=true → Kontrolle an SDF."
  RETURN  # I_orchestrate endet — SDF startet I_orchestrate neu fuer Stufe N+1

NACH LETZTER STUFE (N=5 DONE oder alle tdd_stages abgearbeitet):
  manifest.I_PIPELINE_STATE.phase = "POST_PIPELINE"
  IF GLOBAL_HIL == "off":
    Logge: "[STAGE-TRANSITION] Alle Stufen DONE → /_stage_orchestrate (final)"
    Skill(skill="_stage_orchestrate")
```
