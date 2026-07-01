# /_Post_orchestrate - Team Lead Post-Implementation-Phase-Orchestrierung

## Zweck

Finale Pruefung + Aufraeumen NACH Implementation-Phase (I-Pipeline DONE) UND wenn
alle BL/PL-Items des Features DONE sind (PL-Empty-Signal). Ersetzt die ehemaligen
Schritte 9-12 der I-Pipeline, die BL-113a-FIX-14 ausgelagert hat.

```yaml
status: active
version: 1.0.0
created: 2026-04-17
op: PostImplementationPhase
phase: Meta
type: orchestration
chain_position: meta
difficulty_scaling: false
team_based: true
depends_on:
  - _I_orchestrate   # muss DONE sein (I_PIPELINE_STATE.phase == POST_PIPELINE o.ae.)
feeds_into:
  - _BDF_orchestrate  # signalisiert Batch-Complete nach Post-Phase
triggered_by:
  - _SDF_orchestrate  # SDF ruft _Post_orchestrate wenn PL-Empty nach Batch
```

---

```
+======================================================================+
| META-COMMAND: /_Post_orchestrate                                     |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU — reiner Orchestrator)                          |
|   CONSTRAINT: Kein Code schreiben. Nur Skill-Handschuhwechsel.       |
|                                                                        |
| ZWECK: Finale Pruefung + Aufraeumen NACH I DONE + PL-EMPTY.          |
|                                                                        |
| TRIGGER (von SDF, NICHT direkt aufrufbar):                           |
|   - BATCH_LOOP: alle Items DONE                                       |
|   - PL scanning: keine [ ]-Items mehr (alle terminal)                |
|   - SDF ruft: Skill(skill="_Post_orchestrate", args="{NAME}")        |
|                                                                        |
| PIPELINE (Ex-Schritte 9-12 der I-Pipeline):                           |
|   P1: diffAudit       (_I_diffAudit)                                 |
|   P1a: Refactoring-Checkpoint (HiL oder PL-Park)                     |
|   P1b: DiffReduce --fullScan (_DiffReduce)                          |
|   P2: Pre_PR          (_Pre_PR_orchestrate)                          |
|   P2a: Debloat-Check  (optional /_D_orchestrate)                     |
|   P2-PT: PT_extract   (_PT_extract — Pflaster 2026-04-20)            |
|   P2b: Pattern-Konsolidierung (experimental → PROVEN)                |
|   P2c: AC_orchestrate (_AC_orchestrate)                              |
|   P2d: HiL-Presentation (optional, HiL!=off)                         |
|   P2e: R_orchestrate  (_R_orchestrate)                               |
|   P2f: Smoothing      (_smoothing)                                   |
|   P3: W_push          (_W_push_orchestrate)                          |
|   P3a: Fire-Together + ObsidianSync Trigger                          |
|   P3b: BL-236 Finish-Harvest (AK-7/8: code>vault write-back)         |
|   P4: Finish          (_finish)                                      |
|                                                                        |
| ENDE: Post_PIPELINE_STATE.phase = "DONE", BDF_BATCH_DONE=true.      |
+======================================================================+
```

### P3b: BL-236 Finish-Harvest (AK-7 + AK-8 Two-Way-Flow)

Der fehlende Post-Process (User-Vision „Model = Traeger der Wahrheit"): nach Implementation
flieesst die **verifizierte Wahrheit zurueck in den Vault** -> current-by-construction. Schliesst
den Kreis mit der A-Pipeline-Lese-Seite (Drift-Verifikation, `dispatch_model_drift`).
Best-Judgment-OQs: Trigger=hier post-implementation (OQ-4); Schreibrichtung=code-verified->Vault-Model (OQ-5).
Source-only, wirkt bei Redeploy.

```
P3b_harvest:
  drift = Workflow(name="dispatch_model_drift", args={bl_id: NAME, model_path: "{feature_model_pfad}"})
  IF drift != null:
    FOR g IN drift.drifted:      # code_contradicted -> Model-Claim AN DEN CODE anpassen (code>vault)
      Korrigiere W{g.w_id} gemaess g.drift_detail; setze truth_grade=code_verified
    FOR g IN drift.hypotheses:   # vault_hypothesis -> als unbestaetigt markieren (NICHT in PROVEN harvesten)
      Markiere W{g.w_id}.truth_grade=vault_hypothesis
    harvest = [Impl-Lauf-Erkenntnisse, die NICHT im Model stehen]
    FOR f IN harvest: Append an Backlog/_inbox/ ODER neuen W-Knoten (Erfahrungs-Harvest)
    Log: "[BL-236 Harvest] {drift.drift_count} drift-korrigiert + {|harvest|} Erfahrungen -> Vault current-by-construction."
```

---

## VERTRAG

```
LIEST:
  .claude/analysis/_manifest.md       (I_PIPELINE_STATE.phase, i_core_result)
  .claude/analysis/_session_params.md (HiL, ceiling, floor)
  .claude/specs/{NAME}_Spec.md        (AK-Inventar fuer Pruefung)
  .claude/analysis/synthese/{NAME}-GAP.md  (final gap verification)
  .claude/analysis/synthese/{NAME}-VERIFY.md (I-Pipeline Verify-Report)
  .claude/_parking-lot.md             (PL-Empty Check am Start)

SCHREIBT STATE (_manifest.md):
  POST_PIPELINE_STATE:
    phase: {P1|P1a|P1b|P2|...|P4|DONE}
    started: {ISO}
    completed: {ISO | null}
    feature: {NAME}
    results:
      diffaudit: {pfad}
      diffreduce: {pfad}
      pre_pr: {status: PASS|FAIL, gates_failed: []}
      ac: {pfad}
      r_orchestrate: {pfad}
      smoothing: {status: PASS|FINDINGS|FAIL, findings: N}
      w_push: {collections_pushed: N}
      finish: {status: DONE, pl_freeze_items: N}
  GLOBAL_MODUS bleibt unveraendert (post_phase schreibt NICHT GLOBAL_*)

SCHREIBT PROTOKOLL (_manifest_protokoll.md):
  ## Post-Phase Archiv [{Datum}] {NAME}
  (nach Abschluss: vollstaendige POST_PIPELINE_STATE prependen)

HAUPTPRODUKT: Feature-Abschluss-Verifikation + Wissens-Sicherung

INVARIANTEN:
  - Triggert NUR durch SDF (ueber Skill-Aufruf), NICHT von User direkt
  - Setzt I_PIPELINE_STATE.phase = POST_PIPELINE zu Beginn
  - Setzt POST_PIPELINE_STATE.phase = DONE am Ende
  - Signalisiert BDF_BATCH_DONE=true nach P4 Finish
  - Bei FAIL in P1/P2/P2c/P2f: HiL-Entscheidung (continue/abort/park)
  - Kein Post_orchestrate-Aufruf ohne I_PIPELINE_STATE.phase in [POST_PIPELINE, done]
  - Kein Post_orchestrate-Aufruf wenn PL noch offene Items hat (CHECK zu Beginn)
```

---

## Aufruf

```
/_Post_orchestrate NAME
```

| Parameter | Default | Beschreibung |
|-----------|---------|-------------|
| `NAME` | (aus Manifest) | Feature-Name. Falls nicht angegeben: lese NAME aus _manifest.md |

**Wer ruft auf:** NUR `_SDF_orchestrate` nach BATCH_LOOP-Ende + PL-EMPTY-Check.
User-Direct-Calls werden mit Warning abgewiesen (Anti-Pattern: "Post ohne Batch-Complete").

---

## PHASE 0: PRE-CHECKS

```
# Phase 0.1: Kontext laden
manifest = Lies .claude/analysis/_manifest.md
NAME = Argument-Wert ?? manifest.NAME
IF NAME NICHT gefunden: STOPP "Post_orchestrate benoetigt NAME"

# Phase 0.2: Vorbedingung — I muss DONE sein
i_phase = manifest.I_PIPELINE_STATE.phase ?? "unknown"
IF i_phase NOT IN ["POST_PIPELINE", "done", "POST_TDD_CONSUMED"]:
  Logge FEHLER: "[POST-GATE] I_PIPELINE_STATE.phase={i_phase} — I-Pipeline nicht abgeschlossen."
  STOPP

# Phase 0.3: Vorbedingung — PL muss empty sein
pl_content = Lies .claude/_parking-lot.md
open_items = Zaehle Items mit "- [ ]" (nicht [x], [~], [?], [!], [SPEC-PROMOTED])
IF open_items > 0:
  Logge FEHLER: "[POST-GATE] PL hat {open_items} offene Items — Post-Phase blockiert."
  STOPP "Post-Phase laeuft erst wenn PL empty."

# Phase 0.4: Manifest initialisieren + PL-Snapshot fuer F15 Triage
# BL-113a-FIX-15 (2026-04-17): Snapshot des PL VOR Post-Phase, damit wir in P5
# neue Items (erzeugt durch Post-Phase) von bestehenden unterscheiden koennen.
pl_snapshot_before = Lies .claude/_parking-lot.md → Hash/Content-Snapshot
# Alternativ: Zaehle Items pro Status (fuer Delta-Berechnung)
pl_items_before = parse_items(pl_snapshot_before)  # Liste von {id, status, text}

Schreibe .claude/analysis/_manifest.md:
  POST_PIPELINE_STATE:
    phase: P1
    started: {ISO-Zeitstempel}
    completed: null
    feature: {NAME}
    results: {}
    pl_snapshot_before: pl_items_before  # fuer F15 Triage am Ende
  I_PIPELINE_STATE.phase: "POST_PIPELINE"  # konsistentes Signal

# Phase 0.5: HiL-Params
params = Lies .claude/analysis/_session_params.md
hil = params.HiL ?? "off"
ceiling = params.ceiling ?? "opus"
floor = params.floor ?? "haiku"
```

---

## PHASE 1: FINALE PRUEFUNG

### P1: diffAudit (PFLICHT)

```
Logge: "[POST] P1: /_I_diffAudit {NAME}"
Skill(skill="_I_diffAudit", args="{NAME}")
# → .claude/analysis/synthese/{NAME}-DIFFAUDIT.md, SPUR-1..7 Check, Cleanup-Liste

POST_PIPELINE_STATE.results.diffaudit = "synthese/{NAME}-DIFFAUDIT.md"
POST_PIPELINE_STATE.phase = "P1a"
manifest.update()
```

### P1a: Refactoring-Checkpoint (HiL oder PL-Park)

```
Lies .claude/analysis/synthese/{NAME}-DIFFAUDIT.md → categorize REFACTORING/CLEANUP/SPUR

IF refactoring_findings > 0:
  IF hil == "off":
    # Autonom: alle Refactoring-Findings in Parking-Lot parken
    FOR finding IN refactoring_findings:
      APPEND zu .claude/_parking-lot.md: "- [ ] [REFACTOR] {finding}"
    Logge: "[POST] P1a: {N} Refactoring-Findings in PL geparkt (autonom)."
  ELSE:
    HiL: "{N} Refactoring-Findings. [1] Alle parken [2] Einzelne [3] Keine"
    # Process answer

POST_PIPELINE_STATE.phase = "P1b"
```

### P1b: DiffReduce --fullScan (PFLICHT)

```
Logge: "[POST] P1b: /_DiffReduce {NAME} --theoretic --fullScan"
Skill(skill="_DiffReduce", args="{NAME} --theoretic --fullScan")
# → .claude/analysis/synthese/{NAME}-DIFFREPORT.md

POST_PIPELINE_STATE.results.diffreduce = "synthese/{NAME}-DIFFREPORT.md"

# SPUR-8 Findings behandeln
Lies DIFFREPORT.md → spur8_findings
IF spur8_findings > 0:
  IF hil == "off":
    FOR finding IN spur8_findings:
      APPEND zu .claude/_parking-lot.md: "- [ ] [SPUR-8] {finding}"
  ELSE:
    HiL: "{N} verwaiste Artefakte. [1] Einzeln [2] Alle parken [3] Ignorieren"

POST_PIPELINE_STATE.phase = "P2"
manifest.update()
```

---

## PHASE 2: QUALITY GATES + AUFRAEUMEN

### P2: Pre_PR (PFLICHT)

```
Logge: "[POST] P2: /_Pre_PR_orchestrate {NAME}"
Skill(skill="_Pre_PR_orchestrate", args="{NAME}")
# → Pre-PR Reports (9 Gates parallel)

pre_pr_result = Lies Pre-PR Synthese-Datei → status
POST_PIPELINE_STATE.results.pre_pr = pre_pr_result

IF pre_pr_result.status == "FAIL":
  IF hil == "off":
    Logge WARNUNG: "[POST] Pre-PR FAIL — Gates: {pre_pr_result.gates_failed}"
    # autonom: Findings in PL parken, weiter zu P2a (non-blocking fuer Post-Phase)
  ELSE:
    HiL: "Pre-PR FAIL. [1] Fixen (STOPP) [2] Parken [3] Akzeptieren"
    IF "Fixen": STOPP

POST_PIPELINE_STATE.phase = "P2a"
manifest.update()
```

### P2a: Debloat-Check (optional)

```
model_size = Zeilen in .claude/models/{NAME}_Model.md
IF model_size > 500:
  IF hil == "off":
    Logge: "[POST] P2a: Model {model_size} LOC — Debloat-Check SKIP (autonom)"
    # Autonom: NICHT automatisch Debloat (zu riskant ohne User-Entscheidung)
  ELSE:
    HiL: "Model {model_size} LOC. /_D_orchestrate ausfuehren? [JA/NEIN]"
    IF JA: Skill(skill="_D_orchestrate", args="{NAME}")

POST_PIPELINE_STATE.phase = "P2-PT"
```

### P2-PT: PT_extract (Pflaster 2026-04-20)

```
# Pflaster-Scope (klein): Nur PT_extract in die Kette einhaengen.
# Volles Feature (PL-Extract + Pre_PR Metadata fuer semantische Patterns)
# wird im separaten Backlog-Item abgedeckt (siehe Parking-Lot 2026-04-20).

Logge: "[POST] P2-PT: /_PT_extract {NAME}"
Skill(skill="_PT_extract", args="{NAME}")
POST_PIPELINE_STATE.results.pt_extract = "(ausgefuehrt)"
POST_PIPELINE_STATE.phase = "P2b"
manifest.update()
```

### P2b: Pattern-Konsolidierung

```
# Experimental patterns die S3/S4 bestanden → PROVEN
Lies .claude/patterns/*.md → find status="experimental"
FOR p IN experimental_patterns:
  IF p.s3_passed AND p.s4_passed:
    Schreibe p.status = "PROVEN"
    Logge: "[POST] P2b: Pattern {p.name} experimental → PROVEN"

POST_PIPELINE_STATE.phase = "P2c"
```

### P2c: AC_orchestrate

```
Logge: "[POST] P2c: /_AC_orchestrate {NAME}"
Skill(skill="_AC_orchestrate", args="{NAME}")
POST_PIPELINE_STATE.results.ac = "(ausgefuehrt)"
POST_PIPELINE_STATE.phase = "P2d"
```

### P2d: HiL-Presentation (optional)

```
Erstelle .claude/presentation/{NAME}-STATUS.md (Summary des Post-Phase-Laufs bisher)
IF hil != "off":
  HiL: "Post-Phase bis P2c DONE. Weiter mit Review (P2e)?"
```

### P2e: R_orchestrate (Review)

```
Logge: "[POST] P2e: /_R_orchestrate {NAME}"
Skill(skill="_R_orchestrate", args="{NAME}")
POST_PIPELINE_STATE.results.r_orchestrate = "(ausgefuehrt)"
POST_PIPELINE_STATE.phase = "P2f"
```

### P2f: Smoothing (PFLICHT)

```
Logge: "[POST] P2f: /_smoothing {NAME}"
Skill(skill="_smoothing", args="{NAME}")
smoothing_result = Lies .claude/analysis/synthese/SMOOTHING-{NAME}-*.md → status

POST_PIPELINE_STATE.results.smoothing = smoothing_result

IF smoothing_result.status IN ["FINDINGS", "FAIL"]:
  IF hil == "off":
    # Findings in PL parken, weiter (non-blocking)
    FOR finding IN smoothing_result.findings:
      APPEND zu .claude/_parking-lot.md: "- [ ] [SMOOTHING] {finding}"
  ELSE:
    HiL: "Smoothing: {N} Findings ({kritisch} kritisch). [1] Fixen [2] Parken [3] Akzeptieren"

POST_PIPELINE_STATE.phase = "P3"
manifest.update()
```

---

## PHASE 3: WISSENS-SICHERUNG

### P3: W_push_orchestrate (PFLICHT)

```
Logge: "[POST] P3: /_W_push_orchestrate {NAME} normal {ceiling} {floor}"
Skill(skill="_W_push_orchestrate", args="{NAME} normal {ceiling} {floor}")
# → Model finish, gap, push_global, modelSplit, sync, retrospektive

POST_PIPELINE_STATE.results.w_push = "(ausgefuehrt)"
POST_PIPELINE_STATE.phase = "P3a"
```

### P3a: Fire-Together + ObsidianSync Trigger

```
# NON-BLOCKING (fehler-isoliert, Post-Phase laeuft weiter bei CATCH)
TRY:
  Skill(skill="_W_fireTogether", args="{NAME} model")
CATCH:
  Logge WARNUNG: "[POST] P3a: Fire-Together model fehlgeschlagen — Weiter."
TRY:
  Skill(skill="_W_fireTogether", args="{NAME} gap")
CATCH:
  Logge WARNUNG: "[POST] P3a: Fire-Together gap fehlgeschlagen — Weiter."
TRY:
  Skill(skill="_W_sync_orchestrate", args="{NAME} normal --co-work")
CATCH:
  Logge WARNUNG: "[POST] P3a: Sync-Trigger fehlgeschlagen — Weiter."

POST_PIPELINE_STATE.phase = "P4"
```

---

## PHASE 4: FEATURE-ABSCHLUSS

### P4: Finish (PFLICHT)

```
Logge: "[POST] P4: /_finish {NAME}"
Skill(skill="_finish", args="{NAME}")
# → Parking-Lot Review, Task.md finalize, Konsistenz-Check, PHASE=READY

POST_PIPELINE_STATE.results.finish = "(ausgefuehrt)"
POST_PIPELINE_STATE.phase = "DONE"
POST_PIPELINE_STATE.completed = {ISO-Zeitstempel}
manifest.update()
```

---

## PHASE 5a: PL-TRIAGE (BL-113a-FIX-15, 2026-04-17)

```
# BL-113a-FIX-15: Post-Phase hat in P1a/P1b/P2/P2f neue PL-Items eingefuegt.
# Diese muessen klassifiziert + priorisiert werden BEVOR BDF den naechsten Batch startet.
# Ohne Triage: BDF sieht alle neuen Items als "OFFEN", startet naechsten Batch
# ohne Prioritaet, ohne Scope-Entscheidung, ohne Blocker-Check.

Logge: "[POST] P5a: PL-Triage"
pl_snapshot_before = POST_PIPELINE_STATE.pl_snapshot_before ?? []
pl_now = Lies .claude/_parking-lot.md → pl_items_current

# Delta: Neue Items (in pl_now, nicht in pl_snapshot_before)
neue_items = [item FOR item IN pl_now IF item.id NOT IN pl_snapshot_before.ids AND item.startswith("- [ ]")]

IF len(neue_items) == 0:
  Logge: "[POST] P5a: Keine neuen PL-Items durch Post-Phase — Triage SKIP."
ELSE:
  Logge: "[POST] P5a: {len(neue_items)} neue PL-Items durch Post-Phase — Triage startet."
  triage_results = {done: 0, freeze: 0, offen_high: 0, offen_normal: 0, blocked: 0}

  FOR item IN neue_items:
    # Tag-basierte Auto-Klassifikation
    IF "[PRE-PR-FAIL]" IN item.tags:
      # Pre-PR-Fail ist Blocker → bleibt [ ] mit hoher Prioritaet
      APPEND "[PRIO: HIGH]" zu item.text
      triage_results.offen_high += 1
      Logge: "[POST] P5a: Item {item.id} → OFFEN HIGH (PRE-PR-FAIL)"

    ELIF "[SMOOTHING]" IN item.tags AND item.severity == "kritisch":
      APPEND "[PRIO: HIGH]" zu item.text
      triage_results.offen_high += 1
      Logge: "[POST] P5a: Item {item.id} → OFFEN HIGH (Smoothing kritisch)"

    ELIF "[SMOOTHING]" IN item.tags AND item.severity == "niedrig":
      # Autonome FREEZE (triviale Findings)
      IF hil == "off":
        Ersetze "- [ ]" mit "- [~] [FREEZE] [AUTO-TRIAGE]" in item.text
        triage_results.freeze += 1
        Logge: "[POST] P5a: Item {item.id} → FREEZE (Smoothing niedrig, auto)"
      ELSE:
        # HiL entscheidet
        HiL_choice = AskUserQuestion("Smoothing-Finding '{item.text}': [OFFEN/FREEZE/DONE]")
        IF HiL_choice == "FREEZE":
          Ersetze "- [ ]" mit "- [~] [FREEZE]"
          triage_results.freeze += 1
        ELIF HiL_choice == "DONE":
          Ersetze "- [ ]" mit "- [x] (DONE: {Datum})"
          triage_results.done += 1

    ELIF "[REFACTOR]" IN item.tags:
      # Refactoring meist out-of-scope → FREEZE Default bei autonomer Ausfuehrung
      IF hil == "off":
        Ersetze "- [ ]" mit "- [~] [FREEZE] [AUTO-TRIAGE: Refactor-Kandidat]"
        triage_results.freeze += 1
        Logge: "[POST] P5a: Item {item.id} → FREEZE (Refactor, auto)"
      ELSE:
        HiL_choice = AskUserQuestion("Refactor '{item.text}': [OFFEN/FREEZE/DONE]")
        # HiL-Pfad wie oben

    ELIF "[SPUR-8]" IN item.tags:
      # Verwaiste Artefakte — meist gruen abarbeitbar im naechsten Batch
      APPEND "[PRIO: NORMAL]" zu item.text
      triage_results.offen_normal += 1
      Logge: "[POST] P5a: Item {item.id} → OFFEN NORMAL (SPUR-8)"

    ELSE:
      # Unklassifiziertes Item (kein bekannter Post-Tag) — bleibt OFFEN NORMAL
      APPEND "[PRIO: NORMAL]" zu item.text
      triage_results.offen_normal += 1

  # Manifest-Log
  POST_PIPELINE_STATE.results.pl_triage = {
    new_items: len(neue_items),
    done: triage_results.done,
    freeze: triage_results.freeze,
    offen_high: triage_results.offen_high,
    offen_normal: triage_results.offen_normal,
    blocked: triage_results.blocked
  }
  Logge: "[POST] P5a: Triage abgeschlossen. {triage_results.offen_high} HIGH, {triage_results.offen_normal} NORMAL, {triage_results.freeze} FREEZE, {triage_results.done} DONE."

POST_PIPELINE_STATE.phase = "BDF_SIGNAL"
manifest.update()
```

## PHASE 5b: BDF-SIGNAL + PROTOKOLL-ROLLOVER

```
# BDF-Signal: Batch inkl. Post-Phase komplett
Schreibe .claude/analysis/_manifest.md:
  BDF_PIPELINE_STATE.bdf_batch_done = true
  BDF_PIPELINE_STATE.last_post_phase_feature = {NAME}
  BDF_PIPELINE_STATE.post_phase_completed = {ISO}

# Protokoll-Rollover (Pattern B, W18)
Prepend zu _manifest_protokoll.md:
  ## Post-Phase Archiv [{Datum}] {NAME}
  [Vollstaendiger POST_PIPELINE_STATE YAML-Block]
  last_append={Datum}, append_count++

# State-Cleanup: POST_PIPELINE_STATE aus _manifest.md entfernen
Entferne POST_PIPELINE_STATE-Block aus _manifest.md
Logge: "[POST] Feature {NAME}: Post-Phase DONE. BDF_BATCH_DONE=true signalisiert."

# Final Summary
AUSGABE: """
═══════════════════════════════════════════════════════════
POST-PHASE ABGESCHLOSSEN
Feature: {NAME}
DiffAudit: {POST_PIPELINE_STATE.results.diffaudit}
DiffReduce: {POST_PIPELINE_STATE.results.diffreduce}
Pre-PR: {POST_PIPELINE_STATE.results.pre_pr.status}
Smoothing: {POST_PIPELINE_STATE.results.smoothing.status}
W_push: {POST_PIPELINE_STATE.results.w_push}
Finish: {POST_PIPELINE_STATE.results.finish}
═══════════════════════════════════════════════════════════
"""

RETURN  # Kontrolle zurueck an SDF → BDF
```

---

## Fehlerbehandlung

| Fehler | Aktion |
|--------|--------|
| Phase-Pre-Check FAIL (I nicht DONE) | STOPP |
| Phase-Pre-Check FAIL (PL hat offene Items) | STOPP |
| Pre-PR FAIL + HiL=off | Findings parken, weiter |
| Pre-PR FAIL + HiL aktiv | HiL-Entscheidung (Fixen/Parken/Akzeptieren) |
| Smoothing FINDINGS + HiL=off | Parken, weiter |
| Fire-Together FAIL | WARNING, Post-Phase laeuft weiter (non-blocking) |
| Finish FAIL | STOPP + HiL |
| Skill nicht verfuegbar | Logge Error, Schritt SKIP mit Warning |

---

## Referenzen

- `_I_orchestrate.md` (ex-Schritte 9-12, jetzt hier)
- `_SDF_orchestrate.md` (Trigger: nach BATCH_LOOP + PL-EMPTY)
- `_BDF_orchestrate.md` (empfaengt BDF_BATCH_DONE=true nach Post-Phase)
- `_Pre_PR_orchestrate.md` (in P2 gerufen)
- `_DiffReduce.md` (in P1b gerufen)
- `_smoothing.md` (in P2f gerufen)
- `_W_push_orchestrate.md` (in P3 gerufen)
- `_finish.md` (in P4 gerufen)
