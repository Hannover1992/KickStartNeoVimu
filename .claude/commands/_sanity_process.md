---
type: satellite
status: NEU
version: 1.0.0
created: 2026-05-21
op: SanityProcess
phase: Audit
chain_position: standalone
team_based: false
---

# /_sanity_process — Post-Process Compliance Audit + Resume-Plan-Generator

## Zweck

Nach einer angeblichen Pipeline-Ausfuehrung (BDF → A → IDF → SDF → I/SC → Post)
PRUEFEN, ob der Prozess **so gelaufen ist, wie /_help es spezifiziert**.

Drei Outputs pro BL:
1. **SOLL** (aus /_help + _*_orchestrate.md abgeleitet): welche Skills + Berater
   in welcher Reihenfolge fuer den jeweiligen reifegrad noetig sind
2. **IST** (aus audit.jsonl + per-BL _manifest.md): was tatsaechlich ausgefuehrt wurde
3. **RESUME-PLAN**: konkrete Anweisung ab wann und wie weitergemacht werden muss
   um process-konform zu werden — mit Skill-Aufrufen, Berater-Sequenz, Args

**Komplement zu /_help:**
- `/_help` = Spec ("so MUSS es laufen")
- `/_sanity_process` = Audit + Resume ("so HAETTE es laufen sollen vs so IST es gelaufen + so KORRIGIERST du")

**Komplement zu /_sanity_check_post:**
- `/_sanity_check_post` = phase-scoped, braucht Pre-Report
- `/_sanity_process` = pipeline-end-scoped, leitet SOLL aus /_help selbst ab,
  generiert Resume-Plan

---

## Aufruf

```
/_sanity_process [--bl={IDs}] [--scope=session|branch|recent-N] [--vault={path}]

Beispiele:
  /_sanity_process --bl=BL-179,BL-180,BL-181
  /_sanity_process --scope=session            # alle BLs der aktuellen Session
  /_sanity_process --scope=recent-50          # letzte 50 audit-Events
  /_sanity_process --scope=branch             # alle BLs auf aktuellem Branch
```

Default: `--scope=session` (alle BLs die in dieser Session beruehrt wurden).

---

## VERTRAG

```
+======================================================================+
|  VERTRAG: /_sanity_process                                            |
+======================================================================+
|                                                                       |
|  ROLLE: TEAM LEAD (DU). READ-ONLY auf Pipeline-State.                |
|         Generiert Audit + Resume-Plan, fuehrt KEINE Korrektur aus.   |
|                                                                       |
|  LIEST:                                                              |
|    .claude/commands/_help.md                  (Pipeline-Spec SOLL)  |
|    .claude/commands/_A_orchestrate.md         (A-Berater-Liste)     |
|    .claude/commands/_IDF_orchestrate.md       (IDF-Berater-Liste)   |
|    .claude/commands/_SDF_orchestrate.md       (SDF-Berater-Liste)   |
|    .claude/commands/_I_orchestrate.md         (I-Steps-Liste)       |
|    .claude/commands/_SC_orchestrate.md        (SC-Phasen-Liste)     |
|    .claude/audit/audit.jsonl                  (IST-Events)          |
|    {VAULT}/_backlog_index.md                  (BL-Status + reifegrad)|
|    {VAULT}/Backlog/BL-*.md                    (BL-Frontmatter)      |
|    {bl_folder}/_manifest.md                   (per-BL Pipeline-State)|
|    {VAULT}/_factory_manifest.md               (Factory-State, opt.) |
|                                                                       |
|  SCHREIBT:                                                           |
|    .claude/output/Sanity_Process_{DATE}_{SCOPE}.md  (Master-Report)|
|    {bl_folder}/Crumbs/Sanity_Process_{DATE}.md      (Per-BL Resume) |
|    {VAULT}/_parking-lot.md                          (PL-Item bei    |
|                                                       HIGH-Findings) |
|                                                                       |
|  SCHREIBT NICHT:                                                     |
|    {bl_folder}/* (NUR Crumbs)                                       |
|    {VAULT}/_backlog_index.md                                        |
|    BL-Vault-Knoten (Frontmatter unveraendert)                       |
|                                                                       |
|  INVARIANTEN:                                                        |
|    INV-SP-1: Read-Only auf BLs (verändert nichts ausser Reports)    |
|    INV-SP-2: Resume-Plan MUSS konkret sein                          |
|              (Skill + Phase + Berater + Args + Reihenfolge)         |
|    INV-SP-3: SHOULD-Liste aus /_help abgeleitet (nicht hardcoded)   |
|              — wenn /_help sich aendert, /_sanity_process anpasst    |
|    INV-SP-4: WAS-Liste aus audit.jsonl + Manifests (Source-of-Truth)|
|    INV-SP-5: Compliance-Score quantifiziert (X erfuellt / Y erwartet)|
|    INV-SP-6: Verdict-Color deterministisch:                         |
|              GREEN  = 95-100% Compliance                            |
|              YELLOW = 60-94%                                         |
|              RED    = < 60%                                          |
+======================================================================+
```

---

## SOLL-Pipeline-Ableitung (aus /_help)

Pro reifegrad welche Skills + Berater zu erwarten sind:

```
+========================================================================+
|  reifegrad   |  SOLL-Skills + Berater (aus /_help TEIL 9 Punkt 5)     |
+========================================================================+
|  UNREIF      |  /_A_orchestrate (16 Phasen via 9 Berater):           |
|              |    Phase 0.1 modusErkennung                             |
|              |    Phase 0.2 discovery                                  |
|              |    Phase 0.5 findingsExtraction                         |
|              |    Phase 0.5.2 findingsReview                           |
|              |    Phase 0.6 taskDefinition (Pipeline-Command)          |
|              |    Phase 2 iddContext (NUR --parent-pr)                 |
|              |    Phase 2.5 W_fetch (Pipeline-Command)                 |
|              |    Phase 3 model (Pipeline-Command)                     |
|              |    Phase 4 spec (Pipeline-Command)                      |
|              |    Phase 4k K_score (Pipeline-Command)                  |
|              |    Phase 4g gap (Pipeline-Command)                      |
|              |    Phase 4.2a metadatenAggregation                      |
|              |    Phase 4.4 gitTracking                                |
|              |    Phase 4.3 stateMaintain                              |
|              |    Phase 5 routing                                      |
|              |  → Erwartete Berater-Spawns: 9                          |
|              |  → Erwartete Pipeline-Skill-Loads: 6 (sub-pipelines)   |
+========================================================================+
|  SC-REIF     |  A (DONE prerequisite) + IDF (14 Berater):              |
|              |    Phase 0.5 teamSetup                                  |
|              |    Phase 1 resumeGuard + init (2)                       |
|              |    Phase 2 specParse                                    |
|              |    Phase 3.1 akExtraktion (parallel pro AK)            |
|              |    Phase 3.2 plAggregation                              |
|              |    Phase 3.5 validator                                  |
|              |    Phase 3.6 itemContext                                |
|              |    Phase 3.7 modelSync                                  |
|              |    Phase 4 dependencyAnalyzer                           |
|              |    Phase 5 clustering                                   |
|              |    Phase 6 sequencePlanner                              |
|              |    Phase 7 batchPlan (wraps batchPlanner)              |
|              |    Phase 7.5 stagePlanner                               |
|              |    Phase 7.6 metricPlanner                              |
|              |  → IDF Berater-Spawns: 14 (+ N für akExtraktion-AKs)   |
|              |  → Dann SDF (siehe unten) + I/SC (siehe unten)         |
+========================================================================+
|  REIF        |  SDF Outer-Loop pro Sub-Batch (8 Berater):              |
|              |    Phase 0 resumeGuard                                  |
|              |    Phase 0.5 testRun-Fork (cond)                       |
|              |    Phase 1.0 architecturalBrief                        |
|              |    Phase 1.1 modusEntscheidung (INV-MODUS-1!)         |
|              |    Phase 1.5 patternBrief                               |
|              |    Phase 1.6 IDF-Gate                                   |
|              |    Phase 2.1 EXECUTION DISPATCH                         |
|              |      → /_I_orchestrate ~20 Steps  ODER                  |
|              |      → /_SC_orchestrate Forschungszyklus               |
|              |    Phase 3 batch-Ende (recalibrate, postItem,           |
|              |                       statusTransition, modelSync)     |
|              |    Phase 4 loopDecision                                 |
|              |  → SDF Berater-Spawns pro Batch: 8                     |
|              |  → I-Pipeline Steps: 20 (Blueprint 1-8 + TDD 9-18 +    |
|              |                          Closure 19-20)                |
|              |  → Plus: /_PostBatch_orchestrate + /_Pre_PR_orchestrate|
+========================================================================+
```

**INV-SP-3** garantiert: diese Liste wird aus _help.md TEIL 9 + Berater-VERTRAG-
Sektionen der _*_orchestrate.md-Files dynamisch generiert, nicht hardcoded.

---

## METHODOLOGIE (7-Schritt-Audit)

### Schritt 1: Scope-Aufloesung

```
1.1 Wenn --bl: explizite BL-Liste
1.2 Wenn --scope=session: scan audit.jsonl seit Session-Start (oder letzte 1000)
1.3 Wenn --scope=branch: alle BLs mit Frontmatter-Aenderung auf aktuellem Branch
1.4 Wenn --scope=recent-N: BLs in letzten N audit-Events
1.5 Default: --scope=session

→ scoped_bls = [BL-179, BL-180, ...]
```

### Schritt 2: SOLL-Pipeline-Ableitung pro BL

```
2.1 Lade /_help.md TEIL 9 (Pipeline-Reihenfolge)
2.2 Lade _*_orchestrate.md (Berater-Listen aus VERTRAG-Sektionen)
2.3 Pro BL:
    reifegrad = Read({bl}.md frontmatter).reifegrad
    spec_aks  = Read({bl_folder}/3_Spec/*.md) → AK-Count (für akExtraktion-Parallel)
    
    should_pipeline = derive_pipeline(reifegrad)
    should_berater  = collect_berater_list(should_pipeline, spec_aks)
    should_skills   = collect_skill_list(should_pipeline)
    
    SHOULD[bl] = {pipeline, berater, skills, total_spawns}
```

### Schritt 3: IST-Verifikation (audit.jsonl + Manifests)

```
3.1 Pro BL:
    audit_events_bl = grep(audit.jsonl, bl_id, since_session_start)
    
    actual_skill_loads     = filter(audit_events_bl, type="SKILL_LOAD")
    actual_berater_spawns  = filter(audit_events_bl, type="HANDOFF" AND
                                                     subagent_skill matches "_*_berater_*")
    actual_phase_steps     = filter(audit_events_bl, type="PHASE_*_STEP")
    
    bl_manifest = Read({bl_folder}/_manifest.md)
    actual_berater_outputs = bl_manifest.BERATER_OUTPUTS_* (alle keys)
    actual_a_pipeline_state = bl_manifest.A_PIPELINE_STATE
    actual_idf_pipeline_state = bl_manifest.IDF_PIPELINE_STATE
    actual_sdf_pipeline_state = bl_manifest.SDF_PIPELINE_STATE
    actual_i_pipeline_state = bl_manifest.I_PIPELINE_STATE
    
    WAS[bl] = {
      skill_loads:     actual_skill_loads,
      berater_spawns:  actual_berater_spawns,
      phase_steps:     actual_phase_steps,
      berater_outputs: actual_berater_outputs,
      pipeline_states: {a, idf, sdf, i, sc}
    }
```

### Schritt 4: DIFF-Bildung

```
4.1 Pro BL:
    missing_skills  = SHOULD[bl].skills  - WAS[bl].skill_loads
    missing_berater = SHOULD[bl].berater - WAS[bl].berater_spawns
    
    inv_violations = []
    
    # INV-PM-5 Check: Berater-Mega-Agent-Detection
    IF count(berater_spawns) << count(SHOULD.berater):
      IF count(skill_loads_orchestrate_in_isolation) > 0:
        inv_violations.append("INV-PM-5_MEGA_AGENT")
    
    # INV-MODUS-1 Check
    IF SHOULD includes SDF AND WAS lacks _SDF_berater_modusEntscheidung:
      IF bl_manifest.DF_BATCH_STATE.modus != null:
        inv_violations.append("INV-MODUS-1_TEAM_LEAD_SET_MODUS")
    
    # INV-AO-CALLER Check
    FOR orchestrate_skill IN [_A, _IDF, _SDF, _I, _SC]:
      IF audit shows Agent(prompt="orchestrate ...") for orchestrate_skill:
        inv_violations.append("INV-AO-CALLER_HUB_DELEGATE")
    
    # I-Pipeline Steps Check
    IF SHOULD includes I AND count(actual.i_steps) < 20:
      missing_i_steps = 20 - count(actual.i_steps)
    
    # PostBatch + Pre-PR Check
    IF actual.bl_status == "DONE":
      IF NOT actual.postbatch_invoked OR NOT actual.pre_pr_invoked:
        inv_violations.append("POST_PHASE_SKIPPED")
    
    DIFF[bl] = {missing_skills, missing_berater, missing_steps, inv_violations}
```

### Schritt 5: Compliance-Score-Berechnung

```
5.1 Pro BL:
    expected_total = SHOULD[bl].total_spawns + SHOULD[bl].total_steps
    actual_total   = count(WAS[bl].berater_spawns) + count(WAS[bl].phase_steps)
    compliance_score_bl = actual_total / expected_total
    
5.2 Global:
    expected_global = sum(SHOULD[bl].total for bl in scoped_bls)
    actual_global   = sum(WAS[bl].total for bl in scoped_bls)
    compliance_score_global = actual_global / expected_global
    
5.3 Verdict-Color:
    IF compliance_score_global >= 0.95: verdict = GREEN
    ELIF compliance_score_global >= 0.60: verdict = YELLOW
    ELSE: verdict = RED
```

### Schritt 6: RESUME-Plan-Generierung

```
6.1 Pro BL mit DIFF != empty:
    resume_steps = []
    
    # Bestimme aktuellen Pipeline-Fortschritt
    current_stage = determine_max_completed_stage(WAS[bl])
    # z.B. "A_DONE" oder "IDF_PHASE_3_PARTIAL"
    
    # Generiere konkrete naechste Aktion
    IF "INV-PM-5_MEGA_AGENT" in inv_violations:
      # A-Pipeline wurde via Mega-Agent gemacht — empfehle Re-Run
      resume_steps.append({
        action: "RE_RUN_A_PIPELINE",
        skill: "_A_orchestrate",
        args: f"{bl_id} fresh --refresh-aks",
        rationale: "Mega-Agent erkannt — A-Pipeline mit 9 echten Berater-Spawns nachfahren",
        berater_sequence: [
          "_A_berater_modusErkennung",
          "_A_berater_discovery",
          "_A_berater_findingsExtraction",
          "_A_berater_findingsReview",
          "_A_berater_iddContext (cond)",
          "_A_berater_metadatenAggregation",
          "_A_berater_gitTracking",
          "_A_berater_stateMaintain",
          "_A_berater_routing"
        ],
        artifacts_preserve: true  # bestehende Vault-Dateien bleiben
      })
    
    IF "IDF_SKIPPED" in DIFF[bl].missing_skills AND reifegrad == "SC-REIF":
      resume_steps.append({
        action: "RUN_IDF_PIPELINE",
        skill: "_IDF_orchestrate",
        args: f"{bl_id} --refresh-aks",
        rationale: "IDF wurde uebersprungen — Dekomposition + Batching nachfahren",
        berater_sequence: [
          "_IDF_berater_teamSetup",
          "_IDF_berater_resumeGuard",
          "_IDF_berater_init",
          "_IDF_berater_specParse",
          "_IDF_berater_akExtraktion x N",  # N = anzahl AKs
          "_IDF_berater_plAggregation",
          "_IDF_berater_validator",
          "_IDF_berater_itemContext",
          "_IDF_berater_modelSync",
          "_IDF_berater_dependencyAnalyzer",
          "_IDF_berater_clustering",
          "_IDF_berater_sequencePlanner",
          "_IDF_berater_batchPlan",
          "_IDF_berater_stagePlanner",
          "_IDF_berater_metricPlanner"
        ]
      })
    
    IF "SDF_SKIPPED" in DIFF[bl].missing_skills:
      resume_steps.append({
        action: "RUN_SDF_PIPELINE",
        skill: "_SDF_orchestrate",
        args: f"--batch={bl_id}",
        rationale: "SDF wurde uebersprungen — Modus-Entscheidung + Dispatch nachfahren",
        berater_sequence: [
          "_SDF_berater_resumeGuard",
          "_SDF_berater_architecturalBrief",
          "_SDF_berater_modusEntscheidung  ← INV-MODUS-1 PFLICHT",
          "_SDF_berater_patternBrief",
          "_SDF_berater_executionDispatch",
          "...dann via Modus: I oder SC"
        ]
      })
    
    IF "I_SKIPPED" in DIFF[bl].missing_skills:
      resume_steps.append({
        action: "RUN_I_PIPELINE",
        skill: "_I_orchestrate",
        args: f"--stage=1 --tdd=true",  # M3 default
        rationale: "I-Pipeline 20 Steps mit TDD",
        steps: [
          "1. cleanCodeArchitect",
          "2. requirementCheck",
          "3. patternLibrary",
          "4. testSearch",
          "5. goldDefine",
          "6. blueprintQG",
          "7. cleanCodeSlice",
          "8. mitose + fanOut",
          "9-18. TDD-Loop (RED → GREEN → REFACTOR)",
          "19. _I_verify pro Slice",
          "20. _I_fanIn + Stage-QG"
        ]
      })
    
    IF "POST_PHASE_SKIPPED" in inv_violations:
      resume_steps.append({
        action: "RUN_POST_PHASE",
        skill: "_PostBatch_orchestrate + _Pre_PR_orchestrate",
        rationale: "Tests + Pre-PR-Gates nachfahren"
      })
    
    RESUME[bl] = resume_steps
```

### Schritt 7: Report-Schreibung + PL-Items

```
7.1 Master-Report:
    .claude/output/Sanity_Process_{DATE}_{SCOPE}.md
    Mit Sections:
      - Executive-Summary (Verdict-Color + Score)
      - Pro BL: SHOULD vs WAS Tabelle + DIFF + RESUME
      - Aggregat-Statistik
      - PL-Items aus dieser Audit
      - Naechste Schritte (konsolidiert)

7.2 Per-BL Crumbs:
    {bl_folder}/Crumbs/Sanity_Process_{DATE}.md
    Konzentriert: nur SHOULD vs WAS + RESUME fuer DIESES BL

7.3 PL-Items (bei HIGH-Severity):
    Append in {VAULT}/_parking-lot.md:
    ## [ ] BL-FOLGE-SANITY-{BL-ID}_{DATE} — HOCH-Prioritaet
       Resume-Pflicht: {kurze Beschreibung}
       Detail: {bl_folder}/Crumbs/Sanity_Process_{DATE}.md
```

---

## OUTPUT-FORMAT (Master-Report)

```markdown
# /_sanity_process — Master-Report {DATE} {SCOPE}

**Scope:** {n} BLs auditiert
**Verdict:** {GREEN | YELLOW | RED}
**Compliance-Score Global:** {X} / {Y} = {pct}%

## Executive-Summary
{1-Absatz: was wurde gemacht, was fehlt, was kommt als naechstes}

## Pro-BL-Detail

### BL-{NNN}

**reifegrad:** {SC-REIF | REIF | UNREIF}
**Compliance-Score:** {X} / {Y} = {pct}%
**Status (Vault-Knoten):** {READY | DONE | PARTIAL_DONE}

#### SOLL-Pipeline (aus /_help)
| Phase | Skill | Berater | Erwartet | Tatsaechlich | Diff |
|---|---|---|---|---|---|
| A.0.1 | _A_orchestrate | _A_berater_modusErkennung | 1 | 1 | ✓ |
| A.0.5 | _A_orchestrate | _A_berater_findingsExtraction | 1 | 0 | ✗ FEHLT |
| ... | ... | ... | ... | ... | ... |

#### INV-Verletzungen
- INV-PM-5 MEGA_AGENT (HIGH)
- INV-MODUS-1 TEAM_LEAD_SET_MODUS (HIGH)
- ...

#### RESUME-PLAN (konkrete Schritte)
**Schritt 1:** RE_RUN_A_PIPELINE
- Aufruf: `Skill(_A_orchestrate, args="BL-XXX fresh --refresh-aks")`
- Erwartete Berater (9 Spawns):
  1. _A_berater_modusErkennung
  2. _A_berater_discovery
  ...
- Artefakte preserve: ja (bestehende Vault-Dateien bleiben)
- Verifikations-Marker nach Abschluss:
  - audit.jsonl: 9 HANDOFF-Events mit subagent_skill="_A_berater_*"
  - manifest.BERATER_OUTPUTS: 9 keys
  - A_PIPELINE_STATE.phase == COMPLETED

**Schritt 2:** RUN_IDF_PIPELINE
- ...

**Schritt 3:** RUN_SDF_PIPELINE
- ...

## Aggregat-Statistik

| Metrik | Wert |
|---|---|
| BLs auditiert | {n} |
| GREEN BLs | {n} |
| YELLOW BLs | {n} |
| RED BLs | {n} |
| Total INV-Verletzungen | {n} |
| HIGH-Severity Findings | {n} |
| PL-Items erzeugt | {n} |

## Naechste Schritte (konsolidiert)

1. **Sofort:** {hoechste Prioritaet}
2. **Diese Session:** {mittlere Prio}
3. **Folge-Session:** {niedrige Prio}

## PL-Items erzeugt
- [PL-FOLGE-SANITY-{BL}_{DATE}](...)
- ...
```

---

## INVARIANTEN

- **INV-SP-1:** Read-Only auf BLs (verändert nichts ausser Reports/PL)
- **INV-SP-2:** Resume-Plan MUSS konkret sein (Skill + Phase + Berater + Args)
- **INV-SP-3:** SHOULD aus /_help abgeleitet (nicht hardcoded)
- **INV-SP-4:** WAS aus audit.jsonl + Manifests (Source-of-Truth)
- **INV-SP-5:** Compliance-Score quantifiziert (X/Y)
- **INV-SP-6:** Verdict deterministisch (GREEN ≥95%, YELLOW 60-94%, RED <60%)
- **INV-SP-7:** Resume-Plan respektiert INV-AO-CALLER (Skill() direkt durch Team Lead),
  INV-PM-5 (Berater via Agent()-Spawn), INV-MODUS-1 (modus von SDF-Berater)

---

## Workflow

```
[Pipeline gleich ausgefuehrt — angeblich DONE fuer X BLs]
   ↓
1. /_sanity_process --bl=X,Y,Z      (ODER --scope=session)
   - liest /_help SOLL
   - liest audit.jsonl IST
   - generiert Master-Report
   ↓
2. User liest Master-Report
   - sieht Verdict (GREEN/YELLOW/RED)
   - sieht RESUME-PLAN pro BL
   ↓
3. User entscheidet:
   - Resume durchfuehren? → folgt RESUME-PLAN Schritt fuer Schritt
   - Akzeptieren mit Caveat? → markiert BLs mit "process_revalidation_needed=false"
   - Reopen? → setzt status zurueck, plant neue Session
   ↓
4. /_sanity_process erneut um zu verifizieren dass Resume erfolgreich war
```

---

## QUICK-START

```
# Audit der aktuellen Session
/_sanity_process

# Audit spezifischer BLs
/_sanity_process --bl=BL-193,BL-194,BL-195

# Audit der letzten 200 audit-Events
/_sanity_process --scope=recent-200

# Audit aller BLs auf Branch
/_sanity_process --scope=branch
```

---

## ABHAENGIGKEITEN

- **`/_help`** (LIEST) — Pipeline-Spec SOLL
- **`/_sanity_check_post`** (KOMPLEMENT) — phase-scoped, Pre-Post-Pair
- **`audit.jsonl`** (LIEST) — IST-Events Source-of-Truth
- Alle `_*_orchestrate.md` (LIEST) — Berater-VERTRAG-Sektionen

## VERWANDTE COMMANDS

- `/_help` — Pipeline-Spec
- `/_sanity_check_pre` — Pre-Phase Audit
- `/_sanity_check_post` — Post-Phase Audit (phase-scoped)
- `/_audit` — Generic Audit-Report
- `/_origin` — Reverse-Lookup Coherenz-Kette

---

## Changelog

### v1.0.0 (2026-05-21) — Initial Release
- Definition als post-pipeline-end Audit-Command mit Resume-Plan
- SOLL aus /_help abgeleitet (dynamisch, nicht hardcoded)
- IST aus audit.jsonl + per-BL Manifests
- Compliance-Score X/Y quantifiziert, Verdict GREEN/YELLOW/RED
- Resume-Plan pro BL mit konkreten Skill+Berater+Args
- INV-SP-1..7 etabliert
- Anlass: Goal-Sequenz 2026-05-21 lieferte Mega-Agent-Artefakte → Bedarf
  fuer formales Process-Audit-mit-Resume-Tool erkannt
