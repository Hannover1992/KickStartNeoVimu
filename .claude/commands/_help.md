---
type: satellite
status: active
version: 3.0.0
created: 2026-05-06
updated: 2026-06-26
op: System-Overview
revision_log:
  - "2026-05-09 v2.1.0: BL-166/168/169 — SDF Outer-Loop + Stage-Inner-Loop; IDF Phase 7 batch_stages; TDD-Absorption in I-Pipeline Steps 9-18 am Pipeline-Ende; _TDD_orchestrate DEPRECATED."
  - "2026-05-10 v2.2.0: BL-171 — SDF Phase 2.2 stageElevation Decision-Berater (FOR→WHILE Refactor); I_orchestrate Phase 0 STAGE-ARG-SYNC fuer --stage Override; Stage-Outcome-Check + Retry/Abort/Halt-Branches."
  - "2026-05-10 v2.3.0: BL-172/173 — IDF Phase 7.6 metricPlanner (per-Batch K-Score/SRS-Aggregation aus K-SCORE.md per_ak); SDF Phase 1.1 INV-METRIC-1 Per-Batch-Konsumption; IDF Phase 8.5 Auto-Chain zu SDF bei --from=direct + HiL-Gate; INV-LIFECYCLE-5b TeamDelete-Ausnahme bei Auto-Chain."
  - "2026-05-19 v2.4.0: BL-173 AK-7 — Manifest-Scope-Split Topologie dokumentiert: _factory_manifest.md (BDF+GLOBAL) vs. {slug}/_manifest.md (A/IDF/SDF/SC/I per-Story); TEIL 8c + INV-MANIFEST-SPLIT-1..4 hinzugefuegt; TEIL 2/3/6 aktualisiert."
  - "2026-05-24 v2.5.0: BL-205 AK-8 — SRS-Berechnung v2 (Epistemik-Score) dokumentiert: _srs_compute Skill, kanonische Status-Tabelle, Granularitaet AK/PL/Batch/Global, INTERN/EXTERN-Routing-Signal; P-03/P-13 aktualisiert; TEIL 2 _srs_compute Eintrag."
  - "2026-05-24 v2.6.0: BL-204 AK-10/12 — IDF Phase 8.0 finalSummary (Vektor-Output) in TEIL 1 Flow-Diagramm + TEIL 8b DF_BATCH_STATE-Schema; IDF_FINAL_SUMMARY als Architektur-Pattern (READ-ONLY Konsolidierungsberater, INV-MODUS-1 Disclaimer Pflicht)."
  - "2026-05-24 v2.7.0: BL-201 AK-8 — TEIL 1 um 3 Entry-Points erweitert (Entry 3: /_parking-lot Leichtgewicht-Direkt-Pfad, INV-ENTRY-3, INV-PL-WRITER-1, Sanduhren-Prinzip)."
  - "2026-05-24 v2.8.0: TEIL 10 NEU — Vollstaendige Pipeline-Reise mit 3er-Doppel-Floating-Window + 11 Geister-Tabelle + ASCII-Flowchart Top-to-Bottom + Step-Anzahl pro Orchestrator. Cross-Reference zu INSTRUCTION_full_scan_2026-05-24.md + GOAL_full_scan_2026-05-24.md. Pipeline-Helps (_A/_IDF/_SDF/_SC/_I/_TDD/_PrePR) bekommen jeweils POSITION-IN-DER-REISE Sektion."
  - "2026-06-26 v3.0.0: VDD contract-driven Orchestratoren (I/SDF/SDF-post/PostBatch) + Workflow-Motor-Trio (dispatch_implement) + atomic-truths Capstone (truth_migration_capstone 8 Stufen + G1-G6 truth_capstone_gate) + Worktree-Parallel-Lanes/merge_seam FF-gate (BL-490) + Vehikel-Doktrin (BL-330) + Stage/Resource-Lock (BL-407) + Guard-Haertung (BL-439/423/490). TEIL 11-17 NEU. Surgical: doppelter version-Key bereinigt; INV-MODUS-7 Konditional-Neufassung (DCSRE-486); BL-209-Korrektur in TEIL 1+2 (specParse/akExtraktion/plAggregation = A-Pipeline 5a/5b/5c, in IDF DEPRECATED); Versions-/Berater-Zahlen-Resync (_A v3.6.0/13, _IDF ~19, _SDF v3.2.0, _I v4.1.0, _SC v3.5.0)."
---

# /_help — System-Uebersicht (Vault-Driven-Development, BL-151)

**Zweck:** End-to-End-Flow einer User-Story durchs OmniCommand-System.
Zeigt: Top-Level-Pipelines, Datenfluss (read/write), Vault-vs-Lokal-Trennung,
Projekt-Scope (cross-projekt vs. story-spezifisch), Pattern-/SemanticLibrary-
Bidirektionalitaet, Single-Unit-of-Work + Stateless-Worker.

---

## Aufruf

```
/_help
```

Gib dem User folgende Uebersicht aus (kompletter ASCII-Block, NICHT kuerzen):

---

## TEIL 0 — Mentales Modell: Was ist was

```
+================================================================================+
| KERN-PRINZIPIEN (NICHT VERHANDELBAR)                                           |
+================================================================================+
|                                                                                |
| 1. SINGLE UNIT OF WORK = 1 Agent = 1 Command = stirbt danach                   |
|    Worker tragen KEINEN State zwischen Aufrufen.                               |
|    State lebt im MANIFEST (per-BL-Folder im Vault).                            |
|                                                                                |
| 2. STATELESS WORKER                                                            |
|    Worker bekommt PROMPT mit args. Liest Vault-Vertraege. Schreibt Vault-      |
|    Vertraege. SendMessage an team-lead. STIRBT.                                |
|                                                                                |
| 3. TEAM LEAD = REINER ORCHESTRATOR                                             |
|    Schreibt KEINEN Code, fuehrt KEINE Tests aus, baut KEIN Build.              |
|    NUR: spawnen, tracken, Handschuh-Wechsel.                                   |
|                                                                                |
| 4. HANDSCHUH-WECHSEL (Puppet Master)                                           |
|    Skill(skill="_X_orchestrate") = Team-Lead laedt frischen Kontext SELBST     |
|    Agent(...) statt Skill() = INV-PM-2 Verletzung (auch wenn Resultat OK).     |
|                                                                                |
| 5. VAULT-DRIVEN-DEVELOPMENT (BL-151)                                           |
|    BL-{NNN}-{slug}/ Folder im Vault ist EINE HEIMAT pro Story.                 |
|    Pipeline-State + Artefakte + Libraries leben dort.                          |
|    .claude/ ist NUR Source-of-Truth fuer Commands+Scripts (Code).              |
|                                                                                |
| 6. PROJEKT-SCOPE                                                               |
|    PROJEKT-LOKAL (per BL):  1_Task, 2_Model, 3_Spec, 4_K-Score, 5_Gap, 6_PL    |
|    CROSS-PROJEKT (Vault):   Libraries/PatternLibrary, Libraries/SemanticLibrary|
|                              ParkingLotGlobal/, _backlog_index, _manifest      |
|    PROZESS-WEIT (.claude):  commands/, scripts/, meta/, agents/                |
|                                                                                |
+================================================================================+
```

---

## TEIL 0.5 — DIE 14 GRUNDPFEILER (Doktrin, NICHT VERHANDELBAR)

```
+================================================================================+
|  Diese 14 Pfeiler sind die mentale Architektur auf der das System ruht.        |
|  Sie sind aus User-Doktrin (Audio-Transkript 2026-05-21) extrahiert und        |
|  als BL-179..BL-192 als verifizierbare Case-Studies hinterlegt (DCSRE-486).    |
+================================================================================+

  P-01 PIPELINE-TOPOLOGIE
       Backlog → A-Pipeline → IDF → SDF → I/SC. Linear, deterministisch.
       BDF als Outer-Loop-Dispatcher. → BL-179

  P-02 A-PIPELINE = THEORIE-vs-PRAXIS-KONFRONTATION
       Liefert abstraktes Modell (W{n}) UND Spezifikation (AKs), damit Gap-
       Analyse die Differenz "Was wir haben" vs. "Was gefordert ist" sichtbar
       macht. Modell+Spec sind die ZWEI SEITEN derselben Wahrheit. → BL-180

  P-03 DREI WAEHRUNGEN (Messgroessen unseres Systems)
       (1) SRS (Epistemik-Score) — Wissens-Unsicherheit (Model-Seite) [BL-205]
           srs = w_offen/w_total × 100; orthogonal zu K-Score
           Konsument: SDF Phase 1.1, _srs_compute Skill
       (2) K-SCORE          — Aufwand + Kopplung + Fragilitaet (Code-Seite)
       (3) MODELLREIFE      — wie reif ist die Modellierung (Knowledge-Seite)
       Jede Waehrung hat eigene Skala, eigene Quelle, eigenen Konsumenten.
       → BL-181, BL-205

  P-04 REIFEGRAD-ROUTING (UNREIF | SC-REIF | REIF)
       Berechnet aus den drei Waehrungen. Entscheidet welche Pipeline laeuft.
       UNREIF→A, SC-REIF→IDF, REIF→SDF. Pflicht-Gate vor jedem Worker-Spawn.
       → BL-182

  P-05 PARKING-LOT = UNTERSTE ARBEITSEINHEIT
       Atomare Tasks, jede an Spec+Model geknuepft (Theorie+Praxis Hand-in-Hand).
       IDF dekomponiert AK→PL-Items, SDF verpackt in Sub-Batches, Agenten
       arbeiten Items ab. Granularitaet erlaubt korrekte Komplexitaets-Schaetzung.
       → BL-183

  P-06 MODI M1..M9 (Pro-Batch-Entscheidung)
       SDF Phase 1.1 waehlt PRO Sub-Batch das richtige Vorgehen:
       Skelett (M1), TDD-light (M2), TDD-full (M3), SC-inline (M4), SC-full
       (M5/M6), Analyse-only (M7), Test/Smoothing (M8), Research (M9).
       INV-MODUS-1: Nur SDF entscheidet — niemand sonst. → BL-184

  P-07 DREI FEHLERQUELLEN (was wir hart minimieren)
       (1) SEMANTISCHE FEHLER — Code-Stil/Pattern-Konsistenz (aufwendig, nicht
           komplex; Pre-PR-Naming/Logging/Doc-Gates)
       (2) ABGABE-FEHLER     — PR-Normen, Architektur-Konformitaet, Quality-
           Gates (9× _Pre_PR_*)
       (3) ANFORDERUNGS-FEHLER — Falsche Interpretation, durch Test-Stufen-
           Pyramide spaet erkannt
       → BL-185

  P-08 TEST-PYRAMIDE BOTTOM-UP (Unit → Integration → E2E)
       Wir fangen bei isolierten Inseln (Backend-Unit) an, arbeiten uns nach
       oben zu Integration und E2E mit Klick-Tests. Bei jeder Stufe wachsen
       Aussagekraft UND Kosten. Reihenfolge ist Pflicht. → BL-186

  P-09 PATTERN-LIBRARY + ADR-DISZIPLIN
       Existierende Pattern sind PFLICHT-Konsum (PT-Lookup). Neue Pattern nur
       mit explizitem ADR. Bidirektionaler Fluss: Forward (PT→Story) +
       Reverse (Story→PT-Kandidat→Battle-Test→PROMOTED). → BL-187

  P-10 BERATER-VERTRAEGE + SINGLE-WRITER
       Jeder kurzlebige Worker liest eine definierte Stelle, macht EINEN Job,
       schreibt eine definierte Stelle, stirbt. Single-Writer-Prinzip pro
       Artefakt. Verbindungs-Punkte (Verträge) sind die einzige Kopplung.
       → BL-188

  P-11 WEB/RAG-RESEARCH FUER KNOWLEDGE-GAPS
       Wenn Stakeholder-Input Luecken/Widersprueche hat, darf der Prozess
       online recherchieren (_W_fetch, Wikipedia, Confluence). Befunde
       MUESSEN mit Backlinks belegt werden. Schutzmechanismus: nur bei
       echtem Knowledge-Gap, nicht prophylaktisch. → BL-189

  P-12 VAULT = RUECKVERFOLGBARE WAHRHEIT
       Jede Aussage im Vault ist mit Backlinks belegt. Rueckwaerts-Verfolgung
       von These → Evidenz → Quelle muss jederzeit moeglich sein. Vault ist
       Single-Source-of-Truth, nicht Code-Branch. → BL-190

  P-13 K-SCORE = AUFWAND + KOPPLUNG + FRAGILITAET (Misch-Metrik)
       Sub-Dimensionen:
        - Aufwand     — Umfang der Aenderung (LOC, Files, Komplexitaets-Proxy)
        - Kopplung    — Wie viele andere Komponenten haengen daran
        - Fragilitaet — Blast-Radius, wie viele Hausarbeiten triggern
       K-Score Penalty = 1.0 + (w_offen/w_bezug) × 0.5 (hoeherer K bei unsicheren W{n}).
       SRS ist ORTHOGONAL zu K-Score (keine gemeinsamen Inputs). [BL-205]
       → BL-191

  P-14 PROZESS-VERBESSERUNG BEI WEITER ABWEICHUNG
       Wenn Test-Stufen zeigen "Anforderung war falsch verstanden": kein
       Rad-Neu-Erfinden, sondern A-Pipeline-Re-Sync. Wenn Anforderung sich
       fundamental geaendert hat: Prozess-Retrospektive mit Stakeholdern.
       Drittes Szenario: Modell+Spec waren korrekt, aber Test-Coverage fehlt
       — dann Test-Pyramide hochfahren. → BL-192
```

---

## TEIL 1 — TOP-LEVEL FLOW (vertikal, oben→unten)

```
+======================================================================+
|  DIE 3 ENTRY-POINTS (BL-201, INV-ENTRY-3)                           |
+======================================================================+
|                                                                      |
|  Entry 1 — FRESH (Schwergewicht):                                    |
|    User-Story / Voice → /_backlog → BDF → A-Pipeline                |
|    Zweck: Vollstaendige Wissensbasis-Erzeugung fuer neues BL         |
|                                                                      |
|  Entry 2 — RESYNC (Mittelgewicht):                                   |
|    /_A_orchestrate --resync auf bestehendes BL                       |
|    Zweck: BL existiert, Wissens-Update noetig                        |
|                                                                      |
|  Entry 3 — DIREKT (Leichtgewicht, NEU BL-201):                      |
|    /_parking-lot → PL-Item direkt                                    |
|    Zweck: Kleine Korrekturen, nachgereichte Tasks, Lern-Feedback     |
|    INV-ENTRY-3: Jeder Aufruf = genau 1 PL-Item (Stream, nicht Batch)|
|    Integration: Triggert IDF Loop-Check (BL-199) beim naechsten Lauf|
|    Reverse-Learning: Phase 3.7 modelSync bringt Korrektur ins Model  |
|                                                                      |
|  SANDUHREN-PRINZIP (architecture-vision-2026-05-22.md):              |
|    BACKLOG (Reservoir) → [Sanduhren-Hals: BDF] → A-Pipeline         |
|    → PARKING-LOT (Stream) ←── Entry 3 schreibt hier direkt           |
|    → IDF Loop-Check → SDF → I/SC                                     |
+======================================================================+

                              +----------------------------------+
                              |  USER  (Sprachnotiz / Voice / Text)
                              |  z.B.: "wir sollten X angehen..."
                              +--------------+-------------------+
                                             | /_backlog DATEI.md
                                             |   (oder PL-Eintrag)
                                             v
+======================================================================+
|  STUFE 0 — INTAKE (Single Writer)                                    |
|  Skill: /_backlog (mode=create|intake|update)                        |
|                                                                      |
|  LIEST:                                                              |
|    .claude/config/vault-routing.json    (welcher Vault?)            |
|    {VAULT}/_manifest.md                 (BACKLOG_STATE.counter)     |
|    {VAULT}/_backlog_index.md            (Fallback-Counter)          |
|                                                                      |
|  SCHREIBT (3-Phasen, Crash-Safe):                                    |
|    1) {VAULT}/Backlog/BL-{NNN}-{slug}.md        (Vault-Knoten)      |
|    2) {VAULT}/_backlog_index.md APPEND          (Tabelle + Mirror)  |
|    3) {VAULT}/_manifest.md                       (BACKLOG_STATE++)  |
|    + Subfolder-Struktur:                                            |
|      Backlog/{slug}/{1_Task,2_Model,3_Spec,4_K-Score,5_Gap,6_PL}    |
|                                                                      |
|  Bei Datei-Drop (mode=intake):                                       |
|    .claude/pileOfMud/{NAME}_RAW_{DATE}.md (Roh-Transkript persist.) |
|    Item: reifegrad=UNREIF, needs_a_pipeline=true                    |
+======================================================================+
                                             |
                                             v
+======================================================================+
|  STUFE 1 — BDF: BIG DARK FACTORY (OUTER LOOP)                       |
|  Skill: /_BDF_orchestrate                                            |
|  ROLLE: Dispatcher ueber alle offenen Items                          |
|                                                                      |
|  LIEST (loop):                                                       |
|    {VAULT}/_parking-lot.md      (alle [ ] Items)                    |
|    {VAULT}/_backlog_index.md    (BL-Items READY)                    |
|    Per BL: {VAULT}/Backlog/BL-{NNN}-*.md (reifegrad)                |
|                                                                      |
|  STATE-MACHINE (8):                                                  |
|    INIT -> SCANNING -> BATCH_PLANNING -> ITEM_RUNNING               |
|         -> ITEM_DONE -> SCANNING (loop)                              |
|         -> EMPTY -> TEST_RUNNING -> DONE                             |
|         -> ABORTED                                                   |
|                                                                      |
|  HANDSCHUH-WECHSEL pro Iteration:                                    |
|    +-- reifegrad=UNREIF ---> Skill(_A_orchestrate)    [STUFE 2]     |
|    |                                                                 |
|    +-- reifegrad=SC-REIF --> Skill(_IDF_orchestrate)  [STUFE 3]     |
|    |                                                                 |
|    +-- reifegrad=REIF -----> Skill(_SDF_orchestrate)  [STUFE 4]     |
|                              --batch={items} --task-source=backlog  |
|                                                                      |
|  ANTI-PATTERN: BDF spawnt NIE Code-Worker direkt!                    |
|                Nur SDF entscheidet 9-Modi-Logik.                     |
+======================================================================+
                          |                       |                       |
        +-----------------+                       |                       |
        v                                         v                       v
+================================+   +================================+   +========+
|  STUFE 2 — A_orchestrate       |   |  STUFE 3 — IDF_orchestrate     |   STUFE 4
|  WISSENSBASIS-BAUER            |   |  PL-VERWALTERIN (post-BL-209)  |   (siehe
|  (~18 Phasen, 13 Berater)      |   |  (~16 Phasen, ~19 Berater)     |    unten)
+================================+   +================================+
| phase 0.1 modusErkennung       |   | phase 0.5 teamSetup            |
| phase 0.2 discovery            |   | phase 1   resumeGuard + init   |
| phase 0.5 findingsExtraction   |   | phase 2/3.1/3.2 ENTFERNT       |
| phase 0.5.2 findingsReview HiL |   | (specParse/akExtr/plAggr ->    |
| phase 0.6 taskDefinition       |   | A-Pipeline 5a/5b/5c)           |
| phase 1.5 git_analyse (PR-mode)|   | phase 3.5 validator            |
| phase 2   iddContext --pr      |   | phase 3.6 itemContext          |
| phase 2.5 W_fetch (RAG)        |   | phase 3.7 modelSync (PL->Model)|
| phase 3   model (Wellen 5-3-1) |   | phase 3.8 plBewertung (BL-203) |
|                                |   |   3.8a SRS-Refresh pro PL-Item |
|                                |   |   3.8b Bottleneck-Filter >=60  |
|                                |   |   3.8c K-Score (non-bottleneck)|
|                                |   |   3.8d Intern/Extern-Routing   |
|                                |   |   → per_pl_evaluation           |
|                                |   | phase 3.8e bottleneckTrigger   |
|                                |   |   (BL-206)                     |
|                                |   |   liest per_pl_evaluation      |
|                                |   |   → bottleneck_queue           |
|                                |   |     queue_for_sc [pl_ids]      |
|                                |   |     queue_for_wp [pl_ids]      |
|                                |   |     loop_counts {pl:N}         |
|                                |   |   Max-Loop-Schutz (default=3)  |
|                                |   |   DEFERRED_BOTTLENECK bei N>=3 |
|                                |   | ↓ BOTTLENECK-PFAD (BL-206)   |
|                                |   |   SDF 1.1 liest queue →       |
|                                |   |   intern: M5→SC-Pipeline      |
|                                |   |   extern: M9→WP-Pipeline      |
|                                |   |   SC/WP schreibt Re-Entry-Sig.|
|                                |   |   IDF Re-Entry (sdf_finish):  |
|                                |   |   SRS-Refresh betroffene PLs  |
|                                |   |   → Loop oder K-Score-Pfad    |
|                                |   | phase 4   dependencyAnalyzer   |
| phase 4   spec + AK Review HiL |   | phase 5   clustering           |
| phase 4k  K_score (pro AK)     |   | phase 6   sequencePlanner      |
| phase 4g  gap                  |   | phase 7   batchPlan (Opus)     |
| phase 4.2a metadatenAggregation|   | phase 7.5 stagePlanner (BL-168)|
| phase 4.4 gitTracking          |   |   liest stage_*.md dynamisch  |
| phase 4.3 stateMaintain        |   |   → batch_stages              |
| phase 5   routing              |   | phase 7.6 metricPlanner NEU    |
|                                |   |   (BL-172) liest K-SCORE.md   |
|                                |   |   per_ak → metric_per_batch    |
|                                |   |   (srs_max,srs_avg,k_avg,k_max)|
|                                |   | phase 8.0 finalSummary NEU     |
|                                |   |   (BL-204) READ-ONLY Konsol.   |
|                                |   |   Tabelle+YAML Vektor-Output   |
|                                |   | phase 8   IDF_DONE             |
|                                |   | phase 8.5 Auto-Chain (BL-173)  |
|                                |   |   bei --from=direct + HiL=off  |
|                                |   |   → Skill(_SDF_orchestrate)    |
|                                |   |   ohne TeamDelete (5b-Ausnahme)|
|                                |   |                                |
| OUTPUT (Vault):                |   | OUTPUT (Vault):                |
|                                |   |   {bl}/6_PL/{tc}_PL_Items.md  |
|                                |   |   PL_Master_{date}.md          |
|                                |   |   DF_BATCH_STATE.batch_items   |
|                                |   |   DF_BATCH_STATE.batch_stages |
|                                |   |     {batch_1: [1], batch_3:    |
|                                |   |      [1,3], batch_5: [1,3,6]} |
|                                |   |   stage_begruendung_per_batch |
|                                |   |   DF_BATCH_STATE.metric_per_b. |
|                                |   |     {batch_N: {srs_max,srs_avg,|
|                                |   |       k_score_max, k_score_avg,|
|                                |   |       items_with_data,...}}   |
|                                |   |   (BL-172 Per-Batch-Aggregat)  |
|   {bl}/2_Model/{NAME}_Model.md |   |                                |
|   {bl}/3_Spec/{NAME}_Spec.md   |   +================================+
|   {bl}/4_K-Score/...K-SCORE.md |
|   {bl}/5_Gap/...GAP.md         |
|   {bl}/Crumbs/findings_crumbs  |
|   _manifest.md A_PIPELINE_STATE|
|   BL-Item Frontmatter setzen   |
|   + reifegrad neu berechnen    |
+================================+
        |                                         |
        | A->BDF (post-A-decision)                | IDF->BDF (batch ready)
        | route in {A_RETRY,DEFER,IDF,IDF+SDF,SDF}|
        v                                         v
        +---------> zurueck zu BDF SCANNING <-----+
                                             |
                                             v
+======================================================================+
|  STUFE 4 — SDF: SMALL DARK FACTORY (SPLIT-ARCHITEKTUR, BL-NEW-12)    |
|                                                                      |
|  ZWEI SKILLS (BL-NEW-12, 2026-05-11):                                |
|    Pre-SDF  /_SDF_orchestrate       (Phase 0-2 — Setup + Dispatch)  |
|    Post-SDF /_SDF_orchestrate_post  (Phase 3-4 — Cleanup + Decision)|
|                                                                      |
|  Grund: Skill-Context-Override-Problem — Lead vergisst Phase 3 wenn |
|  I-Skill den SDF-Skill-Context im HEAD ueberlagert. Mit Split:      |
|  Frischer Skill-Context fuer Phase 3 via Skill-Load-Refresh.        |
|                                                                      |
|  +--- Pre-SDF (Phase 0-2) ---------------------------------------+   |
|  | PHASE 0   resumeGuard       (DF_BATCH_STATE.batch_status)     |   |
|  | PHASE 0.5 testRun-Fork      (--mode=testRun)                  |   |
|  | PHASE 1.0 architecturalBrief (PT-Layer-Lookup, cached)        |   |
|  |                                                               |   |
|  | OUTER-LOOP/Sub-Batch - Motor ODER altmodisch (TEIL 11-13)     |   |
|  |  WEG-B altmodisch: FOR batch_key IN pending_sub_batches:      |   |
|  |     IF batch_key IN completed_sub_batches: SKIP               |   |
|  |     PHASE 1.1 modusEntscheidung   (M1..M9 pro Batch)          |   |
|  |     PHASE 1.5 patternBrief        (Pattern-Lookup)            |   |
|  |     PHASE 1.6 IDF-GATE                                        |   |
|  |     PHASE 2.1 EXECUTION DISPATCH:                             |   |
|  |        Skill(_I_orchestrate  --stage --tdd)  (M2/M3)         |   |
|  |        Skill(_I_orchestrate  --scope=skeleton) (M1 BL-174)   |   |
|  |        Skill(_SC_orchestrate)                 (M5/M6/M7)     |   |
|  |     completed_sub_batches.append(batch_key)                   |   |
|  |   END LOOP                                                    |   |
|  | PHASE FINAL: TeamDelete + Protokoll-Rollover + Checkpoint C   |   |
|  +---------------------------------------------------------------+   |
|                              |                                       |
|              Skill(_I_orchestrate) — I-Pipeline laeuft               |
|              NACHPHASE → POST_HANDOVER:                              |
|                              |                                       |
|                              v                                       |
|  +--- Post-SDF (Phase 3-4) -------------------------------------+   |
|  | PHASE 0     Entry-Log (SKILL_LOAD audit.jsonl)                |   |
|  | PHASE 3.0.5 BUILD-Sanity (modus-bedingt: M1/worker-mode)      |   |
|  |                                                               |   |
|  | WAVE 1 (parallel):                                            |   |
|  |   3.1 recalibrate (CONDITIONAL: model_diff || Grundsubstanz)  |   |
|  |   3.2 postItem (GAP-Check)                                    |   |
|  | WAVE 2 (parallel):                                            |   |
|  |   3.3 statusTransition                                        |   |
|  |   3.5 modelSync (intra-Spec)                                  |   |
|  | SCHRITT 3.3.5 stage_orchestrate Commit                        |   |
|  |                                                               |   |
|  | PHASE 3.4 batchEnde (NUR letzte Round, Wave 3 PT/SL parallel) |   |
|  |   WAVE 3: PT_promoteFromPL || SL_promoteFromPL                |   |
|  |                                                               |   |
|  | PHASE 4 loopDecision (3-Wege BL-429, sdf_last_item_detect):   |   |
|  |   RE-BATCH    -> RETURN (Pre-SDF outer-loop iteriert)         |   |
|  |   SOFT-REPRIO -> Skill(_IDF_orchestrate --recluster)          |   |
|  |   ROLLBACK    -> Skill(_IDF_orchestrate --recheck)            |   |
|  |   TERMINATE   -> RETURN (Pre-SDF Phase FINAL)                 |   |
|  +---------------------------------------------------------------+   |
|                                                                      |
|  EXECUTION DISPATCH MODI:                                            |
|     +-------------------------------------------------------------+  |
|     |  Modus  |  Pre-SDF Phase 2.1 Dispatch                       |  |
|     |---------+---------------------------------------------------|  |
|     |  M1     |  Skill(_I_orchestrate --worker-mode --scope=skel) |  |
|     |         |  (BL-174 Skelett-Modus — 4-Step-Subset)           |  |
|     |  M2     |  Skill(_I_orchestrate --tdd=false)                |  |
|     |  M3     |  Skill(_I_orchestrate --tdd=true)                 |  |
|     |         |    -> TDD Steps 9-18 inline am Pipeline-Ende      |  |
|     |  M4     |  Skill(_SC_orchestrate -I)     SC INLINE          |  |
|     |  M5     |  Skill(_SC_orchestrate)        SC FULL Symbiose   |  |
|     |  M6     |  Skill(_SC_orchestrate)  + tdd=true (via I-call)  |  |
|     |  M7     |  Skill(_SC_orchestrate --analyse)  ANALYSE pure   |  |
|     |  M8     |  Skill(_T_orchestrate->smoothing->presentation)   |  |
|     |  M9     |  Skill(_WP_orchestrate)        WP-Research        |  |
|     +-------------------------------------------------------------+  |
|     KEIN separater Skill(_TDD_orchestrate) mehr (DEPRECATED BL-169). |
+======================================================================+
                          |                  |
                          |                  |
                          v                  v
              +========================+   +================================+
              |  STUFE 5a — SC          |   |  STUFE 5b — I (BL-169 ABSORBED)|
              |  /_SC_orchestrate       |   |  /_I_orchestrate ~20 Steps     |
              |  FORSCHUNGSZYKLUS       |   |  IMPLEMENTATION + TDD INLINE   |
              +========================+   +================================+
              | Phase 1: teamSetup      |   | VORPHASE:                      |
              | Phase 2: kurzlebigPrompt|   |  Phase 0  ResumeGuard           |
              | Phase 3: teamLeadSteuer.|   |  Phase 1  teamSetup             |
              |                         |   |  Phase 2  kurzlebigPrompt       |
              | ZYKLUS-LOOP (max 5):    |   |  Phase 3  teamLeadSteuerung     |
              |  observe   (W2 Drafter) |   |                                |
              |  modelMaint(W3 Synth.)  |   | PER STAGE (--stage=N, BL-168): |
              |  qualityGate            |   |  BLUEPRINT (Steps 1-8):         |
              |  hypothese              |   |   1. cleanCodeArchitect (5-3-1)|
              |  implement (FULL/INLINE)|   |   2. requirementCheck           |
              |  ergebnis               |   |   3. patternLibrary  <-PT      |
              |  CONTINUE? -> Loop      |   |   4. testSearch                 |
              |  DONE?     -> Exit      |   |   5. goldDefine                 |
              |                         |   |   6. blueprintQG                |
              | OUTPUT:                 |   |   7. cleanCodeSlice (3-1)      |
              |  {bl}/SC/HANDOFF.md     |   |   8. mitose + fanOut            |
              |  {bl}/SC/OBSERVE-N.md   |   |  TDD-PHASE (Steps 9-18,         |
              |  {bl}/2_Model/...Model  |   |    NUR --tdd=true, BL-169):    |
              |    (via modelMaintain)  |   |   9. _TDD_init (HiL+Ring-Plan) |
              |  i_gate_response        |   |  10. _TDD_red (RED-Test)        |
              | NEEDS_IMPL -> SDF Hub   |   |  11. _TDD_execute (RED-Assert) |
              +========================+   |  12. _TDD_green (min Code)     |
                          |                |  13. _TDD_execute (GREEN-Assert)|
                          | via SDF        |  14. _TDD_refactorCode (Opus)  |
                          v (Hub)          |  15. _TDD_execute (GREEN-Stay) |
                                            |  16. _TDD_refactorTests        |
                                            |  17. _TDD_execute (GREEN-Stay) |
                                            |  18. _TDD_check (GOLD?)        |
                                            |  CLOSURE (Steps 19-20):         |
                                            |  19. _I_verify pro Slice        |
                                            |  20. _I_fanIn + Stage-QG (HiL) |
                                            |                                |
                                            | NACHPHASE (nach allen Stages): |
                                            |  21. _I_verify global           |
                                            |  22. Scope-Gate                 |
                                            |  23. Rollover Pattern B         |
                                            |                                |
                                            | TOTAL: ~20 Steps pro Stage,    |
                                            | bei --tdd=false nur 1-8+19-20  |
                                            +================================+

                                            HINWEIS: STUFE 5c "TDD" ist
                                            DEPRECATED 2026-05-09 (BL-169).
                                            Alle ehemaligen TDD-Schritte
                                            (7a, 7b, 8a-8i, 9, 10, 11) sind
                                            jetzt Top-Level-Steps 9-20 der
                                            I-Pipeline am Pipeline-Ende.
                                            _TDD_orchestrate.md bleibt als
                                            Rollback-Backup bis 2026-Q3.
                                             |
                                             v
                              alle Items DONE -> BDF EMPTY -> TEST_RUNNING -> DONE
                                             |
                                             v
+======================================================================+
|  STUFE 6 — STANDALONE (jederzeit, nicht Pflicht-Pipeline)            |
|                                                                      |
|  /_R_orchestrate     (Code-Review Uncle Bob, 3 Wellen)               |
|     LIEST:  .claude/review-{feature}-queue.md                        |
|     SCHREIBT: .claude/review/PRAESENTATION-{feature}-{date}.md       |
|     KEIN Code-Output, NUR Analyse                                    |
|                                                                      |
|  /_parking-lot       (APPEND-only Queue von ALLEN Commands)          |
|     SCHREIBT: {VAULT}/Backlog/{slug}/6_PL/{bl_id}-parking-lot.md    |
|     LIEST:    /_taskDefinition (bei Cycle-Ende)                      |
+======================================================================+
```

---

## TEIL 2 — DATENFLUSS-TABELLE (wer schreibt wohin, wer liest woher)

```
+-------------------------+-------------------------------------+----------------------------+
| ARTEFAKT                | SCHREIBT                            | LIEST                       |
+-------------------------+-------------------------------------+----------------------------+
| {VAULT}/_factory_manifest.md    | BDF + BACKLOG_STATE + GLOBAL_*      | BDF, /_backlog, Cross-Pipeline-Resume |
|   (BL-173, 2026-05-18)  |   Counter, BDF_BATCH_STATE          |                            |
| {VAULT}/Backlog/{slug}/  | A/IDF/SDF/SC/I Orchestrators       | Pipeline-interne Resume    |
|   _manifest.md           |   PIPELINE_STATE + BERATER_OUTPUTS  | + Routing pro Story        |
|                          |   + DF_BATCH_STATE (BL-173 Split)   |                            |
|   Migration: Big-Bang via migrate_manifest_split.py (BL-173, 2026-05-18)              |
| _backlog_index.md       | /_backlog (single writer)           | BDF, IDF, SDF              |
| Backlog/BL-NNN-{slug}.md| /_backlog (frontmatter)             | BDF (reifegrad)            |
|                         | A-Pipeline phase 4.2a (update)      |                            |
| Backlog/{slug}/         |                                      |                            |
|   1_Task/Task.md        | A.phase 0.6 taskDefinition          | A, IDF, SDF, SC, I         |
|   2_Model/Model.md      | A.phase 3 (_model)                  | ALLE Pipelines             |
|                         | SC.modelMaintain (Update)           |                            |
|                         | IDF.phase 3.7 modelSync (PL->Model) |                            |
|   3_Spec/Spec.md        | A.phase 4 (_spec)                   | A.specParse(5a), SDF, I    |
|   4_K-Score/K-SCORE.md  | A.phase 4k (_K_score)               | /_backlog ak_anchors       |
|                         |                                      | SDF (Modus-Decision)       |
|   5_Gap/GAP.md          | A.phase 4g (_gap)                   | SDF, BDF (decision)        |
|   6_PL/{bl_id}-parking-lot.md | ALLE Commands (APPEND)         | /_taskDefinition           |
|                         | HiL Checkpoint C (SDF Phase FINAL)  | IDF.plAggregation          |
|                         |                                      | _PT_promoteFromPL          |
|                         |                                      | _SL_promoteFromPL          |
|   6_PL/{TC}_PL_Items.md | A.phase 5b akExtraktion (BL-209)    | IDF.dependencyAnalyzer     |
|   6_PL/PL_Master.md     | A.phase 5c plAggregation (BL-209)   | IDF, SDF                   |
|   Crumbs/findings_*.md  | A.phase 0.5.2 findingsReview        | A.phase 3 model            |
|   SC/HANDOFF.md         | SC POST-CYCLE                       | I-Pipeline (Phase 0)       |
|   SC/OBSERVE-N.md       | SC.observe pro Zyklus               | SC.modelMaintain           |
|                                                                                              |
| {VAULT}/Libraries/                                                                           |
|   PatternLibrary/                                                                            |
|     _index.md           | _PT_extract, _PT_update             | I.patternLibrary           |
|                         |                                      | SDF.patternBrief           |
|                         |                                      | SDF.architecturalBrief     |
|     _project/{LAYER}/   | _PT_extract --parking-lot-walk      | alle Brief-Berater         |
|       {pattern}.md      |   (DRAFT, confidence:low)           |                            |
|                         | Pre-PR Battle-Test -> PROMOTED      |                            |
|   SemanticLibrary/                                                                           |
|     _global/glossary.md | _SL_init, _SL_promoteFromPL         | _SL_conformance            |
|     _project/{LAYER}/   | _SL_init, _SL_promoteFromPL         | _SL_pre_pr                 |
|       naming-conv.md    |                                      |                            |
|       domain-terms.md   |                                      |                            |
|                                                                                              |
| {VAULT}/                                                                                     |
|   ParkingLotGlobal/     | _PT_promoteFromPL                   | _PT_extract --pl-walk      |
|     PT-Kandidaten-*.md  |   (Bruecke zu PT-Library)           |                            |
|                                                                                              |
| Metriken-Datenfluss (BL-205 v2.5.0)                                                          |
|   _srs_compute          | compute_srs(item, model) [IN-MEMORY] | _K_score (per-AK srs_pro_ak)|
|   (kein File-Write)     | → {srs, flag, breakdown}            | IDF.metricPlanner (Aggregat)|
|                         |                                      | SDF.modusEntscheidung (P1.1)|
|   _K_score.md           | srs_pro_ak Formel v2 [BL-205]       | SRS = w_offen/w_total × 100|
|                         | Epistemik-Score, 0-100              | INTERN/EXTERN Routing-Signal|
|                                                                                              |
| .claude/ (LOKAL, projekt-eigen)                                                              |
|   commands/             | User editiert + /_redeploy verteilt | Skill-Loader bei Aufruf    |
|   scripts/              | (resolve_*, current_context.py)     | Berater + Workers          |
|   meta/                 | Konventionen + Templates            | Pre-PR Gates, Workers      |
|   pileOfMud/            | /_backlog intake (RAW)              | A.findingsExtraction       |
|   review-{feat}-queue   | User schreibt direkt                | /_R_orchestrate           |
|   review/*.md           | /_R_orchestrate Wellen              | User                       |
|   evidence/*.md         | A-Pipeline (analyse)                | /_R_orchestrate W3        |
|   analysis/             | Workers (Drafts/Synthese, FALLBACK) | Workers (Legacy-Read)      |
|   audit/audit.jsonl     | ModelLeakGuard hooks                | runtime_watchdog          |
+-------------------------+-------------------------------------+----------------------------+
```

**Datenfluss-Ergaenzungen (v3.0.0 — Atom/Edge/View + Motor + VDD + Capstone):**

| ARTEFAKT / KANAL | SCHREIBT | LIEST |
|---|---|---|
| {VAULT} Atom/Edge-Substrat (BL-451): Wahrheiten=Nodes, Edges=Struktur | `truth_atomizer`, `keyword_edge_writer`, `truth_edge_backref` | arc42-/Model-/Spec-/PL-/Doc-**Views** |
| view `source_atoms` (BL-460/491, View→Atom-Referent) | `view_projector`, `wikilink_materializer` | `_arc42_*`, `_origin`, `truth_*` |
| DF_BATCH_STATE Implement-Loop | `dispatch_implement.js` (Motor) ODER `_SDF_berater_*` (altmodisch) | Lead (`loop_decision`-RETURN) |
| I_PIPELINE_STATE.phase + BERATER_OUTPUTS.{phase}.{status,exit_code} (VDD, payload-frei) | `_I_berater_*` (1 Slot/Phase) | `_I_orchestrate` (liest NUR exit_code, INV-DATA-I-1) |
| migration-capstone State (8 Stufen) | `truth_migration_capstone.py` | `truth_capstone_gate.py` (G1-G6) |

> **WICHTIG (Atom/Edge/View, BL-451):** Model / Spec / arc42 / Parking-Lot / Doc sind seit
> BL-451 nicht mehr die Wahrheit *selbst*, sondern **Views ueber die atomaren Wahrheiten**
> (Nodes + bidirektionale Edges). Details: TEIL 17.

---

## TEIL 3 — VAULT vs. LOKAL (visuelle Trennung)

```
+----------------------------------------------------------------------------------+
|  CROSS-PROJEKT (im Vault)            PROJEKT-LOKAL (per BL)         PROZESS (.claude)
|  ------------------------             ------------------------       ------------
|  C:\...\OmniCommand\ ODER             C:\...\OmniCommand\           OmniCommand\
|  C:\...\DCS\DCSRE\                      Backlog\BL-{NNN}-{slug}\     .claude\
|                                                                                   |
|  Libraries\                            1_Task\Task.md                commands\    |
|   PatternLibrary\                      2_Model\Model.md (W{n})       scripts\     |
|     _index.md                          3_Spec\Spec.md (AKs)          meta\        |
|     _project\BE-CONT\                  3_Audit\CaseStudy*.md         pileOfMud\   |
|     _project\BE-CORE\                  4_K-Score\K-SCORE.md          analysis\    |
|     _project\BE-DOMAIN\                5_Gap\GAP.md                     (legacy)  |
|     _project\BE-DTO\                   6_PL\{bl_id}-parking-lot.md    evidence\   |
|     _project\BE-MAP\                   6_PL\TC-A_PL_Items.md          review-*-queue.md
|     _project\BE-MID\                   6_PL\PL_Master_{date}.md      review\     |
|     _project\BE-AUTH\                  Crumbs\findings_*.md          audit\      |
|     _project\BE-MIGRATION\             Assays\Assay_*.md             hooks\      |
|     _project\BE-TEST\                  Blueprint\blueprint.md         config\     |
|     _project\_generic\                 Implementation\               vault-routing|
|                                        SC\HANDOFF.md                              |
|   SemanticLibrary\                     SC\OBSERVE-{N}.md             (Source-Code |
|     _global\domain-glossary.md         W_fetch\W_fetch_*.md           der Tools   |
|     _project\BE-CONT\naming-conv.md    Routing\Routing_*.md            selbst)    |
|     _project\BE-CORE\domain-terms.md   HiL_Decisions_*.md                         |
|     _archive_DCSRE\...                                                            |
|                                                                                   |
|  ParkingLotGlobal\                                                                |
|    PT-Kandidaten-{BL_ID}-{date}.md                                                |
|                                                                                   |
|  Backlog\                                                                         |
|    BL-001-...md (Index-Knoten)                                                    |
|    BL-002-...md                                                                   |
|    ...                                                                            |
|  _backlog_index.md (Tabelle)                                                      |
|  _factory_manifest.md (BDF+GLOBAL_*+Counter) [BL-173]                            |
|    Process-State-Files (Vault-global):                                            |
|      _factory_manifest.md  -- BDF_BATCH_STATE, BACKLOG_STATE, GLOBAL_* Counter   |
|      _manifest_protokoll.md -- Pattern-B Rollover (bleibt Vault-global)          |
|    Process-State-Files (per-Story):                                               |
|      Backlog\{slug}\_manifest.md -- A/IDF/SDF/SC/I PIPELINE_STATE                |
|                                     + BERATER_OUTPUTS + DF_BATCH_STATE            |
|  _manifest_protokoll.md (Rollover)                                                |
|  _parking-lot.md (legacy, READ-ONLY)                                              |
|  _session_params.md                                                               |
+----------------------------------------------------------------------------------+

WANN VAULT, WANN LOKAL?
-----------------------------------------------------------------
- Wissen ueber Story        -> Vault (per BL: Model/Spec/AK/PL)
- Story-Pipeline-State     -> Vault (_manifest.md im BL-Folder)
- Cross-Story-Patterns     -> Vault (Libraries/PatternLibrary)
- Cross-Story-Naming       -> Vault (Libraries/SemanticLibrary)
- Roh-Transkripte (RAW)    -> LOKAL (.claude/pileOfMud)
- Code (Commands+Scripts)  -> LOKAL (.claude/commands, scripts)
- Konventionen (HOW)       -> LOKAL (.claude/meta, deployed via /_redeploy)
- Reviews (Standalone)     -> LOKAL (.claude/review*)
- Drafts/Synthese (Legacy) -> LOKAL (.claude/analysis) — FALLBACK only
-----------------------------------------------------------------
```

---

## TEIL 4 — PATTERN- UND SEMANTIC-LIBRARY: BIDIREKTIONALER FLUSS

```
                              FORWARD-PFAD (Library -> Story)
                          +======================================+
                          |                                       |
   +----------------------+=======================================+-----------------+
   |                       |                                       |                  |
   |  SDF Phase 1.0       |                                       |   I Phase 1b     |
   |  architecturalBrief  |                                       |   patternLibrary |
   |     (PT-Lookup)      |                                       |     (Detail)     |
   |   liest: _index.md  -+------> PatternLibrary/_project/      +-< liest matched  |
   |   liest: BE-{LAYER}/ |         BE-CONT/                     |                  |
   |           *.md       |         BE-CORE/                     |   I cleanCodeSlice|
   |                       |         _generic/                    |   (Re-Use Score) |
   |  SDF Phase 1.5       |                                       |                  |
   |  patternBrief        |                                       |                  |
   |   liest: _index.md  -+         Confidence-Stufen:           |                  |
   |   propagiert in      |         experimental -> battle-tested|                  |
   |   KURZLEBIG_PROMPT   |                       -> stable       |                  |
   |                       |                                       |                  |
   |  SL_conformance      |         SemanticLibrary/             |   SL_pre_pr      |
   |   prueft Branch-Diff -+------>   _global/glossary.md       -+-< prueft Branch  |
   |   gegen Naming       |          _project/{LAYER}/           |   pre-PR         |
   |                       |            naming-conventions.md    |                  |
   |                       |            domain-terms.md          |                  |
   |                       |                                       |                  |
   +----------------------+=======================================+-----------------+
                          |                                       |
                          +======================================+

                              REVERSE-PFAD (Story -> Library)
                          +======================================+
                          |                                       |
                  Phase 3 (Batch-Ende, SDF):                       |
                  +------------------------------------+          |
                  | {bl}/6_PL/{bl_id}-parking-lot.md   |          |
                  |   (Items mit "synced-..."-Marker)  |          |
                  +-------------+----------------------+          |
                                |                                  |
       +------------------------+------------------------+         |
       |                         |                         |         |
       v                         v                         v         |
  /_IDF_berater_modelSync   /_PT_promoteFromPL        /_SL_promoteFromPL
  (intra-projekt)           (cross-projekt-BRUECKE)   (cross-projekt-DIREKT)
       |                         |                         |
       |                         | schreibt:               | schreibt:
       v                         v                         v
  {bl}/2_Model/                  Vault/ParkingLotGlobal/   Vault/Libraries/
   Model.md (W{n}+)              PT-Kandidaten-{BL}-...md  SemanticLibrary/
   Spec.md (Promote)              [PT-Kandidat]              _global/glossary.md
                                  Tag, conf:low              _project/{LAYER}/
                                                              naming-conv.md
                                  v                          domain-terms.md
                            /_PT_extract --parking-lot-walk
                                  |
                                  v schreibt:
                            Libraries/PatternLibrary/
                              _project/{LAYER}/{name}.md
                              status: experimental
                              confidence: low
                                  |
                                  v via /_Pre_PR_orchestrate Battle-Test
                            confidence: battle-tested -> stable
                                  |
                                  v konsumiert NAECHSTER Story
                            FORWARD-PFAD reaktiviert
                          +======================================+
```

---

## TEIL 5 — STATELESS WORKER: ANATOMIE EINER WELLE

```
                         TEAM LEAD (Orchestrator, lebt durch ganze Story)
                         ----------------------------------------------
                         liest: Vault-Manifest (eigener PIPELINE_STATE)
                         entscheidet: Skill() oder Agent()
                         schreibt: nach Worker-Return, Status-Update

                            +------------------------------------+
                            |  Welle 1 (Explorer, floor=haiku)   |
                            |   N Worker = N Tasks PARALLEL      |
                            |                                    |
                            |   spawnt: Agent(general-haiku)     |
                            |     team_name: "{pipeline}-{NAME}" |
                            |     prompt: KURZLEBIG_PROMPT inkl. |
                            |       worker_context (BL-ID,       |
                            |       branch, vault_root)          |
                            |                                    |
                            |   Worker:                          |
                            |     Schritt 0: log [SPAWN]         |
                            |     liest: Vault-Vertrag           |
                            |     fuehrt: 1 Skill aus            |
                            |     schreibt: Vault-Vertrag        |
                            |     SendMessage("team-lead", ...)  |
                            |     STIRBT (return)                |
                            +------------+-----------------------+
                                         | alle DONE?
                                         v
                            +------------------------------------+
                            |  Welle 2 (Drafter, middle=sonnet)  |
                            |   M Worker PARALLEL                |
                            |   liest: Vorgaenger-Welle als KOMPASS
                            |   liest: Primaerquelle DIREKT (INV-SP)
                            +------------+-----------------------+
                                         |
                                         v
                            +------------------------------------+
                            |  Welle 3 (Synthese, ceiling=opus)  |
                            |   1 Worker SEQUENTIELL             |
                            |   konsolidiert + persistiert       |
                            +------------+-----------------------+
                                         |
                                         v
                              Manifest-Update + Welle DONE
                              ---------------------------
   Skalierung (difficulty):
     easy:   1 (nur Synthese)
     normal: 5-3-1
     hard:   9-5-1
```

---

## TEIL 6 — ROLLE DES VAULT (zentrale Wahrheit)

```
+================================================================================+
| VAULT = EINE HEIMAT pro Story (BL-151 Direktive)                              |
|                                                                                |
| Was DRIN steht:                                                                |
|   - State Vault-global: _factory_manifest.md (BDF + GLOBAL_* + Counter) [BL-173]|
|       Felder: BDF_BATCH_STATE, BACKLOG_STATE, GLOBAL_COUNTER                    |
|   - State per-Story: {BL}/_manifest.md (A/IDF/SDF/SC/I + BERATER_OUTPUTS       |
|       + DF_BATCH_STATE) — isoliert pro Story-Slug [BL-173]                      |
|   - State-Rollover: _manifest_protokoll.md (Pattern B Append, last_append...)  |
|   - Counter: _backlog_index.md (Mirror, BL-Counter)                            |
|   - Pro Story: Backlog/BL-{NNN}-{slug}/ — alle Artefakte (Model->Spec->Gap->PL)|
|   - Cross-Story: Libraries/PatternLibrary + SemanticLibrary + ParkingLotGlobal |
|   - Session: _session_params.md (HiL, difficulty, ceiling, floor)              |
|                                                                                |
| Was NICHT drin steht:                                                          |
|   - Code (Commands, Scripts) — die liegen in .claude/ pro Projekt-Repo         |
|   - Roh-Transkripte — die liegen in .claude/pileOfMud (Pre-Backlog-Phase)      |
|   - Reviews (R-Pipeline) — standalone in .claude/review/                       |
|                                                                                |
| Aufloesung:                                                                    |
|   resolve_vault_root.py + resolve_bl_path.py + current_context.py              |
|   nutzen vault-routing.json (ticket_prefix_map: BL->DCS, DCSRE->DCS, CCC->...) |
|   und liefern: {branch, bl_id, vault_root, bl_folder, cwd}                     |
|                                                                                |
| Worker-Awareness (BL-151 NEW-L2):                                              |
|   Jeder Worker erhaelt im Spawn-Prompt seinen worker_context.                  |
|   Damit weiss er WO er ist (welche BL-ID, welcher Vault, welcher Branch).      |
|                                                                                |
| Warum Vault-zentriert:                                                         |
|   1) Multi-Maschinen-Sync (OneDrive/Obsidian) — Repo-clone + Vault-sync genug  |
|   2) Wissens-Persistenz unabhaengig von Code-Branch (Branch-Wechsel = Vault    |
|      bleibt stabil)                                                            |
|   3) Cross-Story-Lernen lebt zentral (Libraries) — PT/SL waechst durch alle    |
|      Storys                                                                    |
|   4) Audit-Trail im Markdown (Obsidian-Graph macht Verbindungen sichtbar)      |
+================================================================================+
```

---

## TEIL 7 — PROZESS-WEIT vs. PROJEKT-WEIT vs. STORY-WEIT (3-Schichten-Trennung)

```
                                  +------------------------------+
                                  |  PROZESS-WEIT (.claude\)     |
                                  |  Identisch in ALLEN Projekten|
                                  |  Quelle: OmniCommand          |
                                  |  Verteilung: /_redeploy       |
                                  +------------------------------+
                                  |  - commands\ (Orchestrators) |
                                  |  - scripts\ (resolve, hooks) |
                                  |  - meta\ (Konventionen)      |
                                  |  - agents\                   |
                                  +-------------+----------------+
                                                | /_redeploy
                                                |  (Whitelist:
                                                |   session_params_default,
                                                |   model_tiers.yaml)
                                                v
                          +-------------------------------------------+
                          |  PROJEKT-WEIT (per Repo, .claude\)       |
                          |  Identisch fuer alle Storys IM Projekt    |
                          +-------------------------------------------+
                          |  - config\layers.yaml (BE-{LAYER} Glob)  |
                          |  - config\vault-routing.json             |
                          |  - .vault_root (Per-Projekt-Pin)         |
                          |  - config\_session_params.md (laufend)   |
                          |  - analysis\ (Legacy-Drafts, Fallback)   |
                          |  - pileOfMud\ (RAW vor Backlog)          |
                          |  - review\ (Standalone-R-Pipeline)       |
                          +-----------------+-------------------------+
                                            | pro Story emergiert
                                            |  durch /_backlog + Pipelines
                                            v
              +-------------------------------------------------------------+
              |  STORY-WEIT ({VAULT}\Backlog\BL-{NNN}-{slug}\)              |
              |  EINMALIG pro Story, isoliert von anderen Storys             |
              +-------------------------------------------------------------+
              |  - 1_Task\Task.md          (Aufgabendefinition)             |
              |  - 2_Model\Model.md        (W{n} Wissensbasis)              |
              |  - 3_Spec\Spec.md          (AKs)                            |
              |  - 3_Audit\...             (CaseStudy / Audit-Reports)       |
              |  - 4_K-Score\K-SCORE.md    (pro AK + global)                |
              |  - 5_Gap\GAP.md            (Coverage)                       |
              |  - 6_PL\{bl_id}-parking-lot.md  (Findings, append-only)     |
              |  - 6_PL\TC-{X}_PL_Items.md (IDF-Decomposition)              |
              |  - Crumbs\, Assays\, SC\, W_fetch\, ...                     |
              |                                                              |
              |  + Cross-Story-Konsumenten:                                  |
              |    {VAULT}\Libraries\PatternLibrary\...                      |
              |    {VAULT}\Libraries\SemanticLibrary\...                     |
              |    {VAULT}\ParkingLotGlobal\PT-Kandidaten-{BL}-{date}.md     |
              +-------------------------------------------------------------+
```

---

## TEIL 8 — BEISPIEL-LAUF "User-Story zum ersten Mal durchs System"

```
+---------------------------------------------------------------------------+
|  USER:                                                                     |
|    "Wir sollten X angehen, hier ist meine Sprachnotiz: voice_2026-05-06.md"|
+--------------------------------------+------------------------------------+
                                        |
                                        v
1. /_backlog voice_2026-05-06.md          ->  pileOfMud\ + BL-{NNN}-x.md (UNREIF)
                                              _manifest BACKLOG_STATE.counter+1
                                        |
                                        v
2. BDF SCANNING                            ->  reifegrad=UNREIF erkannt
                                                + needs_a_pipeline=true
                                        |
                                        v
3. BDF Skill(_A_orchestrate)               ->  voller Lauf: discovery -> findings
                                                Review HiL -> taskDefinition ->
                                                W_fetch -> Model -> Spec (AK) ->
                                                K-Score -> Gap -> metadatenAggreg
                                                /_backlog UPDATE: reifegrad neu
                                                routing -> BDF post-A-decision
                                        |
                                        v
4. BDF post-A-decision routing             ->  Default: IDF+SDF
                                        |
                                        v
5. BDF Skill(_IDF_orchestrate)             ->  specParse 42 AKs
                                                akExtraktion (|| pro Cluster)
                                                plAggregation (PL_Master)
                                                validator -> itemContext ->
                                                modelSync (PL->Model) ->
                                                Phase 3.8 plBewertung (BL-203):
                                                  3.8a SRS-Refresh pro PL-Item
                                                  3.8b Bottleneck-Filter (SRS>=60)
                                                  3.8c K-Score-Refresh (non-bottleneck)
                                                  3.8d Intern/Extern-Klassifikation
                                                  → DF_BATCH_STATE.per_pl_evaluation
                                                dependencyAnalyzer ->
                                                clustering -> sequencePlanner ->
                                                batchPlan (DF_BATCH_STATE.batch_items)
                                        |
                                        v
6. BDF Skill(_SDF_orchestrate --batch=...) ->  Phase 0 resumeGuard (Resume-aware
                                                                     completed_sub_batches +
                                                                     completed_stages_per_batch)
                                                Phase 1.0 analyse + architecturalBrief
                                                OUTER-LOOP pro Sub-Batch (BL-166):
                                                  Phase 1.1 modusEntscheidung -> M2/M3/...
                                                  Phase 1.5 patternBrief
                                                  Phase 1.6 IDF-Gate
                                                  STAGE-INNER-LOOP (BL-168):
                                                    FOR stage IN batch_stages[batch]:
                                                      Phase 2.1 Skill(_I_orchestrate
                                                                  --stage=N --tdd={t|f})
                                                  Phase 3.1-3.5 (recalibrate,
                                                    postBatch, statusTransition,
                                                    modelSync — Continuous-Learning)
                                                  completed_sub_batches.append(batch_key)
                                        |
                                        v
7. I_orchestrate (BL-169 ABSORBED)         ->  pro Stage (--stage=N):
                                                  BLUEPRINT (Steps 1-8):
                                                    cleanCodeArchitect (5-3-1)
                                                    requirementCheck
                                                    patternLibrary lookup PT
                                                    testSearch + goldDefine
                                                    blueprintQG
                                                    cleanCodeSlice (3-1)
                                                    mitose + fanOut
                                                  TDD (Steps 9-18, --tdd=true):
                                                    9. _TDD_init (HiL+Ring-Plan)
                                                    10. _TDD_red (RED-Test)
                                                    11. _TDD_execute (RED-Assert)
                                                    12. _TDD_green (min Code)
                                                    13. _TDD_execute (GREEN-Assert)
                                                    14. _TDD_refactorCode (Opus)
                                                    15. _TDD_execute (GREEN-Stay)
                                                    16. _TDD_refactorTests
                                                    17. _TDD_execute (GREEN-Stay)
                                                    18. _TDD_check (GOLD?)
                                                  CLOSURE (Steps 19-20):
                                                    19. _I_verify pro Slice
                                                    20. _I_fanIn + Stage-QG (HiL)
                                                Stage-Transition (commit)
                                                NACHPHASE (nach allen Stages):
                                                  21. _I_verify global
                                                  22. Scope-Gate
                                                  23. Rollover Pattern B
                                        |
                                        v
8. SDF Phase 3 BATCH-ENDE                  ->  recalibrate (K-Score)
                                                postItem (GAP-Check)
                                                statusTransition (PL [x] / BL DONE)
                                                _IDF_berater_modelSync (PL->Model)
                                                /_PT_promoteFromPL (PL->Vault-PT-Kand.)
                                                /_SL_promoteFromPL (PL->SemLib direkt)
                                                _SDF_berater_batchEnde
                                                  BDF_BATCH_DONE=true
                                                  BDF_NEXT_TRIGGER=true
                                        |
                                        v
9. SDF Phase 4 loopDecision                ->  ROLLBACK | RE-BATCH | TERMINATE
                                        |
                                        v
10. BDF SCANNING (next iteration)          ->  alle Items DONE -> EMPTY
                                                -> testRun-Guard
                                                -> DONE
                                        |
                                        v
   USER: PR-Erstellung + /_R_orchestrate (optional, standalone Code-Review)
```

---

## TEIL 8b — DF_BATCH_STATE FIELD-DISAMBIGUIERUNG (BL-165)

```
FIELD-OWNER-TABELLE: DF_BATCH_STATE (aus {VAULT}/{bl}/_manifest.md)

| Feld                          | Wertebereich              | Owner / Schreiber                          | Konsumenten                          |
|-------------------------------|---------------------------|--------------------------------------------|--------------------------------------|
| routing_decision              | refine, proceed, defer    | A-Pipeline (BDF-Post-A-Entscheid)          | _BDF_orchestrate Phase 5D            |
| pipeline_route                | A, IDF, SDF, IDF+SDF, ... | A-Pipeline (BDF-Post-A-Entscheid)          | _BDF_orchestrate Phase 5D            |
| modus                         | M1..M9                    | _SDF_berater_modusEntscheidung (Phase 1.1) | SDF-Berater, SC, executionDispatch   |
| modus_begruendung             | Freitext                  | _SDF_berater_modusEntscheidung (Phase 1.1) | Logging, SC                          |
| modus_begruendung_per_batch   | {batch_N: text}           | _SDF_berater_modusEntscheidung (Phase 1.1) | Logging                              |
| batch_modes                   | {batch_N: M1..M9}         | _SDF_berater_modusEntscheidung (Phase 1.1) | executionDispatch                    |
| batch_items                   | [PL-item-ids]             | _IDF_berater_batchPlan                     | SDF resumeGuard, executionDispatch   |
| batch_stages                  | {batch_N: [1,3,...]}      | _IDF_berater_stagePlanner                  | SDF Stage-Inner-Loop                 |
| metric_per_batch              | {batch_N: {srs,k,...}}    | _IDF_berater_metricPlanner                 | _SDF_berater_modusEntscheidung       |
| per_pl_evaluation             | {pl_id: {srs, srs_flag, k_score, bottleneck, bottleneck_route, evaluated_at}} | _IDF_berater_plBewertung (Phase 3.8) | Phase 4 dependencyAnalyzer (k_score), Phase 7.6 metricPlanner (srs_max/k_score_avg) |
| bottleneck_queue              | {queue_for_sc: [pl_ids], queue_for_wp: [pl_ids], loop_counts: {pl_id: N}, deferred: [pl_ids], computed_at: date} | _IDF_berater_bottleneckTrigger (Phase 3.8e, BL-206) | _SDF_berater_modusEntscheidung SCHRITT 2.5 (M5/M9 hint), _SDF_orchestrate SCHRITT 2.1 (bottleneck_trigger flag) |
| IDF_FINAL_SUMMARY             | {batches:[{id,one_liner,k,srs,modus_hint,stages,...}], aggregate:{...}, recommended_next:[...]} | _IDF_berater_finalSummary (Phase 8.0, BL-204) | Operator (direkt), SDF Phase 1.1 modus_hint-Kontext (INV-MODUS-1: C3 entscheidet) |
| aggregat_score                | 0..100                    | A-Pipeline metadatenAggregation            | BDF Post-A-Decision (Logging)        |

WICHTIG (INV-MODUS-1/BL-165):
  DF_BATCH_STATE.modus        = SDF-exklusiv. NIEMALS mit refine|proceed|defer belegen.
  DF_BATCH_STATE.routing_decision = BDF-Post-A-exklusiv. NIEMALS mit M1..M9 belegen.
```

---

## TEIL 8c — MANIFEST-SCOPE-SPLIT (BL-173)

```
HINTERGRUND (BL-173, Big-Bang-Migration 2026-05-18):
  Vorher: ein einzelnes {VAULT}/_manifest.md fuer alle State-Typen.
  Nachher: ZWEI klar getrennte Dateien mit Single-Writer-Disziplin.

SPLIT-UEBERSICHT:
  _factory_manifest.md       (Vault-global, 1x pro Vault)
    Owner: BDF + /_backlog
    Felder: BDF_BATCH_STATE, BACKLOG_STATE, GLOBAL_COUNTER, BDF-FLAGS

  Backlog/{slug}/_manifest.md  (per-Story, 1x pro BL-Slug)
    Owner: A/IDF/SDF/SC/I Orchestrators
    Felder: A_PIPELINE_STATE, IDF_PIPELINE_STATE, SDF_PIPELINE_STATE,
            SC_PIPELINE_STATE, I_PIPELINE_STATE,
            BERATER_OUTPUTS (alle Phasen-Outputs), DF_BATCH_STATE

OWNER-MANIFEST-KONSUMENT (kompakt):
| Owner                        | Manifest-Datei              | Konsumenten                        |
|------------------------------|-----------------------------|------------------------------------|
| _BDF_orchestrate             | _factory_manifest.md        | BDF selbst (Resume), /_backlog     |
| /_backlog                    | _factory_manifest.md        | BDF (Counter), /_backlog-Folgelauf |
| _A_orchestrate               | {slug}/_manifest.md         | IDF, SDF (reifegrad-Check)         |
| _IDF_orchestrate             | {slug}/_manifest.md         | SDF (batch_items, batch_stages)    |
| _SDF_orchestrate             | {slug}/_manifest.md         | I, SC, SDF-Post (Resume)           |
| _I_orchestrate / _SC_orch.   | {slug}/_manifest.md         | SDF-Post (POST_HANDOVER)           |

INVARIANTEN (INV-MANIFEST-SPLIT):
  INV-MANIFEST-SPLIT-1: _factory_manifest.md darf AUSSCHLIESSLICH von BDF +
    /_backlog geschrieben werden. Kein A/IDF/SDF/SC/I-Zugriff auf dieses File.
  INV-MANIFEST-SPLIT-2: {slug}/_manifest.md ist story-isoliert. Kein BDF-
    State, kein GLOBAL_COUNTER, keine BDF-FLAGS in dieser Datei.
  INV-MANIFEST-SPLIT-3: Bei Resume liest jeder Orchestrator SEINEN Manifest-
    Typ: BDF -> _factory_manifest, A/IDF/SDF/SC/I -> {slug}/_manifest.
  INV-MANIFEST-SPLIT-4: Cross-referenzieren ist READ-only erlaubt (BDF liest
    {slug}/_manifest fuer reifegrad-Auswertung), aber SCHREIBEN verbleibt
    beim jeweiligen Single-Owner.

Cross-Reference: .claude/meta/schemas/manifest_scope_split.md
Migration-Script: .claude/scripts/migrate_manifest_split.py
```

---

## TEIL 8d — INDEX-VS-CONTENT-SPLIT (BL-178, 2026-05-19)

```
PROBLEM: _backlog_index.md + _parking-lot.md enthalten ~88% Dead-Weight
         (DONE/DECOMPOSED/archivierte Items). Jeder SCANNING-Read schlept
         6000+ LOC mit — davon ~5300 LOC irrelevant.

LOESUNG (BL-178): Active vs. Archive Index-Split

  Active-Index (SCANNING-relevant, NUR diese lesen):
    {vault_root}/_backlog_index.md      ~25 LOC  (active only)
    {vault_root}/_parking-lot.md        ~700 LOC (open [ ] + [~] + [?])

  Archive-Index (NUR auf explizite Anfrage):
    {vault_root}/_backlog_index_done.md ~146 LOC (DONE/DECOMPOSED/etc.)
    {vault_root}/_parking-lot_done.md   ~5200 LOC ([x]-Items)

TOKEN-SAVING: ~85-90% bei SCANNING-Phase (BDF Phase 2).

INVARIANTEN (INV-INDEX-SPLIT-1..6):
  INV-INDEX-SPLIT-1: Kein BL-Item in BEIDEN Indizes gleichzeitig.
  INV-INDEX-SPLIT-2: Status-Wechsel → DONE triggert sofortige Migration.
  INV-INDEX-SPLIT-3: Archive-Index ist append-only (nie editieren).
  INV-INDEX-SPLIT-4: Re-Activation via /_backlog reopen BL-XXX.
  INV-INDEX-SPLIT-5: BDF Phase 2 SCANNING liest NUR Active-Index.
  INV-INDEX-SPLIT-6: Pointer-Integrität muss nach jeder Migration geprüft werden.

KOMMANDOS:
  /_backlog show-archive         Zeigt Archive-Index
  /_backlog reopen BL-XXX        Re-Aktiviert DONE-Item → DRAFT

SCRIPTS:
  .claude/scripts/migrate_backlog_index_split.py   Einmalige Migration
  .claude/scripts/migrate_parking_lot_split.py     Parking-Lot Migration
  .claude/scripts/quality_index_pointer_verify.py  Pointer-Check
  .claude/scripts/token_cost_tracker.py            Token-Saving Messung
```

---

## TEIL 9 — KURZ-MERKZETTEL (was musst du als Operator wissen)

```
1. ROLLE: Du bist Team Lead. Du fuehrst KEINEN Code aus, nur Skill() / Agent().

2. EINSTIEG:
   - Neue Story (Voice): /_backlog DATEI.md  (intake)
   - Bestehende Story: /_BDF_orchestrate     (loop bis leer)

3. HANDSCHUH-WECHSEL (INV-AO-CALLER, INV-PM-2):
   - Skill(_X_orchestrate)   = Team-Lead laedt frischen Kontext SELBST
   - Agent(_X_berater_Y)     = Team-Lead spawnt Worker (kurzlebig)
   - NIEMALS: Skill() durch Worker. NIEMALS Orchestrator via Agent()
     (weder /_X_orchestrate noch Skill(_X_orchestrate) im Agent-Prompt —
      BEIDE Formen guard-geblockt seit BL-439). Details: TEIL 15.

4. STATE:
   - Quelle der Wahrheit: {VAULT}/_manifest.md (per BL-Folder)
   - Resume = Berater liest eigenen BERATER_OUTPUTS-Slot, ueberspringt fertige Arbeit

5. PIPELINE-REIHENFOLGE + DISPATCH (BL-166/168/169/204 + BL-222/330/467):
   /_backlog -> BDF -> A (UNREIF) -> IDF (SC-REIF) -> SDF (REIF)
   IDF Phase 7 plant batch_stages-Map; Phase 8.0 finalSummary READ-ONLY.
   SDF Implement-Loop laeuft via GENAU EINEM Pfad (VEHIKEL-Gate, TEIL 12/13):
     MOTOR-Pfad     : Workflow(dispatch_implement) — Engine, 1 agent()=1 Skill
     ALTMODISCH-Pfad: _SDF_orchestrate Outer-Loop (Default, OHNE Motor)
   Pro Sub-Batch: 1.1 modusEntscheidung (C3, M1..M9, INV-MODUS-1) ->
     1.5 patternBrief -> 2.1 DISPATCH Skill(_I_orchestrate ODER _SC_orchestrate)
       -> I-Pipeline ~20 Steps (Blueprint + TDD inline bei M3 + Closure)
       -> KEIN separater _TDD_orchestrate (DEPRECATED BL-169)
   Phase 3+4 nach JEDEM Batch (INV-MODUS-7 KONDITIONAL, DCSRE-486):
     MOTOR macht Phase 3.x selbst | ALTMODISCH -> Skill(_SDF_orchestrate_post)
   VDD (BL-467, TEIL 11): jeder Orchestrator = State-Machine + 1 Vertrag-Slot
     pro Phase + Spawn-pro-Unit-of-Work -> megaworker-sicher AUCH ohne Motor.
   -> batchEnde -> 3-Wege-Routing (BL-429) -> BDF/IDF/SDF naechster

6. LIBRARIES:
   - PT (PatternLibrary): cross-projekt, Bruecke ueber Vault-PT-Kandidaten +
     Battle-Test, gelesen von SDF.{architectural,pattern}Brief + I.patternLibrary
   - SL (SemanticLibrary): cross-projekt, direkt promoviert (kein Battle-Test),
     gelesen von _SL_conformance / _SL_pre_pr

7. VAULT vs. LOKAL:
   - Story-Wissen (Model/Spec/AK/PL) -> Vault
   - Cross-Story-Patterns/Naming    -> Vault/Libraries
   - Code (Commands/Scripts)        -> .claude/ (Repo-lokal)
   - RAW-Transkripte                -> .claude/pileOfMud (Pre-Backlog)

8. WAS BDF NICHT DARF:
   - Direct-Spawn von Code-Workers
   - Komplexitaet/Modus selbst bewerten (das ist SDF C3-Aufgabe)
   - Skill(_I_orchestrate) direkt — IMMER ueber SDF (Hub-Invariante)

9. NEUE OPERATING-MODEL-DOKTRINEN (v3.0.0 — Pflichtlektuere):
   TEIL 11 VDD (contract-driven)   | TEIL 12 Workflow-Motor-Trio
   TEIL 13 Vehikel (Team/Workflow) | TEIL 14 Worktree-Parallel-Lanes
   TEIL 15 Guard-Enforcement       | TEIL 16 Architekt-Pflicht
   TEIL 17 Atomic-Truths+Capstone  | TEIL 18 Stage/Resource-Lock

10. ROADMAP-KOMPASS (read-only, dispatcht NIE selbst):
   /_roadmap_stern (Nordstern) > /_roadmap_backlog (Macro: welches BL) >
   /_roadmap_parkingLot {BL} (Micro: wo IM BL). /_lane_watchdog = Mothership.
```

---

## TEIL 10 — VOLLSTAENDIGE PIPELINE-REISE (3ER-DOPPEL FLOATING-WINDOW)

> **NEU 2026-05-24 (v2.8.0):** Vollstaendiger Step-by-Step Flowchart der Pipeline-
> Reise mit allen Geistern (Handover-Punkten) und dem 3er-Doppel-Loader-Pattern.
> Dient als operative Sicht fuer System-Scans (siehe `.claude/INSTRUCTION_full_scan_2026-05-24.md`).

### 10.1 Was ist das 3er-Doppel-Floating-Window?

Pro Step werden 3 Vertraege geladen:

```
   ┌────────────────────────────┐
   │  [N-1]  Vorgaenger-Vertrag │  ← Was wurde geschrieben?
   ├────────────────────────────┤
   │  [N  ]  Aktueller Vertrag  │  ← Was wird gelesen + geschrieben?
   ├────────────────────────────┤
   │  [N+1]  Nachfolger-Vertrag │  ← Was wird als naechstes gelesen?
   └────────────────────────────┘
```

Das Fenster bewegt sich entlang der Pipeline-Reise. Bei jedem Step pruefen wir:
1. **Schreib-Lese-Kohaerenz** zwischen N-1 und N
2. **Frontmatter-Vertrag** zwischen N und N+1
3. **State-Marker-Konsistenz** (Manifest-Felder)
4. **Asynchrone Aspekte** (Lock-Pfade, Race-Conditions)
5. **Invarianten-Konformitaet** (INV-*)

### 10.2 Die 11 GEISTER (Hauptsaechliche Handover-Punkte)

Ein **Geist** ist ein Handover-Punkt zwischen zwei Pipelines. Hier feuert das
3er-Doppel besonders kritisch — der "Handschuhwechsel" ist die haeufigste
Bruchstelle.

| Geist | Von                        | Zu                          | Trigger / Bedingung                  |
|-------|----------------------------|-----------------------------|--------------------------------------|
| G#1   | /_backlog                  | /_BDF_orchestrate           | BL-Item DRAFT in _backlog_index      |
| G#1.5 | /_BDF Phase 2 SCANNING     | /_BL_orchestrate            | reifegrad=UNREIF (Reifungs-Routing)  |
| G#2   | /_BL_orchestrate           | /_A_orchestrate             | A-Pipeline-Trigger fuer UNREIF       |
| G#2.5 | /_A Phase 4.2a metadaten   | /_backlog (Update-Modus)    | BL-Update mit ak_anchors             |
| G#3   | /_A_berater_routing        | /_A_postRoute               | Exit-Router (completion_signal)      |
| G#4   | /_A_postRoute              | /_IDF_orchestrate           | routing_decision=proceed (Default)   |
| G#5   | /_IDF Phase 8.5 Auto-Chain | /_SDF_orchestrate           | IDF_DONE + --from=direct + HiL=off   |
| G#6   | /_SDF Phase 2.1 dispatch   | /_I_orch ODER /_SC_orch     | SWITCH modus M1..M9                  |
| G#7   | /_I_orch ODER _SC_orch     | /_SDF_orchestrate_post      | POST_HANDOVER (INV-HANDOVER-1)       |
| G#8   | /_SDF_orchestrate_post     | /_SDF_orch / /_IDF / BDF    | Phase 4.2 Exit-Routing               |
| G#9   | /_BDF EMPTY-Handler        | /_PostBatch_orchestrate     | bdf_all_items_done + testRun_done    |
| G#10  | /_PostBatch_orchestrate    | /_Pre_PR_orchestrate        | Tests + Commit-Stage GREEN           |
| G#11  | /_Pre_PR_orchestrate       | /_BDF (Loop next BL)        | PR erstellt / BDF freigegeben        |

Zusaetzlich: dutzende interne Sub-Geister zwischen Beratern innerhalb eines
Orchestrators (Wave-Splits, Stage-Inner-Loops, Sub-Skill-Aufrufe).

### 10.3 Vollstaendiger ASCII-Flowchart (Top-to-Bottom)

```
LEGENDE:
  ╔══╗  Orchestrator-Skill (Lead laedt via Skill())
  ┌──┐  Berater/Sub-Command (Worker via Agent() spawnt + laedt Skill)
  ▼     sequenzieller Step
  ⤷     Skill-Call innerhalb derselben Pipeline
  ◄┄┄   RETURN / Auto-Chain zurueck
  ★G#N  GEIST (Handover-Punkt — 3er-Doppel-Loader feuert)
  ⟲     Loop (Outer-Loop / Stage-Inner-Loop / Round)

================================================================================
START: User droppt Audio-Transkript: /_backlog raw_2026-05-24.md
================================================================================
                                    │
                                    ▼
╔════════════════════════════════════════════════════════════════════════╗
║  [0] /_backlog   (Satellite, Single-Writer fuer BL-Items)              ║
║      10 Schritte: Auto-Intake, GUARD, BL-Nr, Metriken, Reifegrad,      ║
║                   Hint-Override, Vault-Write, Ordnerstruktur, Index,   ║
║                   Manifest-Counter+1                                    ║
║      Output: BL-NNN UNREIF, needs_a_pipeline=true                      ║
╚═══════════════════════════════╤════════════════════════════════════════╝
                                ▼
                ★ GEIST #1  [_backlog → _BDF_orchestrate]
                                ▼
╔════════════════════════════════════════════════════════════════════════╗
║  [1] /_BDF_orchestrate   (Outer Loop, BL-175 Factory-Lock aktiv)       ║
║      Phasen: Worker-Aware → INIT → SCANNING → INTEREST_RADIUS →        ║
║              BATCH_PLANNING → ITEM_RUNNING → Post-DONE → Stop-Guard    ║
║      Berater: _BDF_berater_blDependencyAnalyzer/Clustering/Sequence/   ║
║               ParallelBucketPlanner (Phase 2.5)                        ║
║      Sub-Calls: _BDF_batchPlan (Phase 2b)                              ║
╚═══════════════════════════════╤════════════════════════════════════════╝
                                │ (UNREIF → Reifungs-Branch)
                                ▼
                ★ GEIST #1.5  [_BDF → _BL_orchestrate]
                                ▼
╔════════════════════════════════════════════════════════════════════════╗
║  [1.5] /_BL_orchestrate   (Reifungs-Routing: UNREIF → A-Pipeline)      ║
╚═══════════════════════════════╤════════════════════════════════════════╝
                                ▼
                ★ GEIST #2  [_BL_orchestrate → _A_orchestrate]
                                ▼
╔════════════════════════════════════════════════════════════════════════╗
║  [2] /_A_orchestrate v3.6.0   (Wissensbasis-Bauer, 13 Berater)         ║
║      Phasen 0.1..5 (~20 Phasen mit Sub-Calls):                         ║
║        0.1 modusErkennung → 0.2 discovery → 0.5 findingsExtraction →   ║
║        0.5.2 findingsReview → 0.6 taskDefinition → 1.5 gitAnalyse →    ║
║        2 iddContext → 2.5 W_fetch → 3 model → 4 spec → 4k K-Score →   ║
║        4g gap → 5a specParse → 5b akExtraktion → 5c plAggregation →   ║
║        4.2a metadatenAggregation → 4.4 gitTracking → 4.3 stateMaintain ║
║        → 5 routing (ruft _A_postRoute)                                 ║
║      ★ GEIST #2.5 (4.2a) — ruft /_backlog im Update-Modus              ║
╚═══════════════════════════════╤════════════════════════════════════════╝
                                ▼
                ★ GEIST #3  [_A_berater_routing → _A_postRoute]
                                ▼
                ★ GEIST #4  [_A_postRoute → _IDF_orchestrate]
                                ▼
╔════════════════════════════════════════════════════════════════════════╗
║  [3] /_IDF_orchestrate v2.1.0   (PL-Verwalterin nach BL-209 Hard-Cut)  ║
║      ~16 Phasen + 19 Berater:                                          ║
║        A loopCheck → 0.5 teamSetup → 0 resumeGuard → 0.9 (Phase        ║
║        2/3.1/3.2 entfernt) → 1 init → 3.5 validator → 3.6 itemContext  ║
║        → 3.7 modelSync (REVERSE) → 3.8 plBewertung → 3.8e bottleneck   ║
║        → 4 dependencyAnalyzer → 5 clustering → 6 sequencePlanner →    ║
║        7 batchPlan → 7.5 stagePlanner → 7.6 metricPlanner →           ║
║        8.0 finalSummary → 8.5 Auto-Chain                              ║
╚═══════════════════════════════╤════════════════════════════════════════╝
                                ▼
                ★ GEIST #5  [_IDF Phase 8.5 → _SDF_orchestrate]
                                ▼
╔════════════════════════════════════════════════════════════════════════╗
║  [4] /_SDF_orchestrate v3.2.0   (Pre-SDF: Phase 0-2, BL-NEW-12 Split)  ║
║      Phase 0 RESUME → 0.5 testRun → 1.0 analyse + architecturalBrief → ║
║      1.6 IDF-Gate                                                       ║
║      ⟲ OUTER-LOOP pro Sub-Batch:                                        ║
║         1.1 modusEntscheidung (M1..M9) → 1.5 patternBrief →            ║
║         ⟲ STAGE-INNER-LOOP (WHILE+Decision, BL-171):                   ║
║            2.0a Per-Batch-Dispatch → 2.1 Team-Lead-Dispatcher          ║
║            SWITCH modus → 1 von 9 Skill-Routes:                        ║
║              M1: _I_orch --scope=skeleton  M2: _I_orch --tdd=false     ║
║              M3: _I_orch --tdd=true        M4: _SC_orch -I             ║
║              M5: _SC_orch                  M6: _SC_orch +tdd           ║
║              M7: _SC_orch --analyse        M8: _T+_smoothing+_present. ║
║              M9: _WP_orch                                              ║
║            2.2 stageElevation (Decision)                                ║
║         (Phase 3+4 wandert zu /_SDF_orchestrate_post via POST_HANDOVER)║
╚═══════════════════════════════╤════════════════════════════════════════╝
                                ▼
                ★ GEIST #6  [_SDF Phase 2.1 → _I_orch ODER _SC_orch]
                                ▼
                ┌───────────────┴───────────────┐
                ▼ (M1-M3)                       ▼ (M4-M7)
╔══════════════════════════════╗   ╔═════════════════════════════════╗
║ [5a] /_I_orchestrate v4.1.0  ║   ║ [5b] /_SC_orchestrate v3.5.0    ║
║      ~20 Steps pro Stage:    ║   ║      SC-Cycle (6 Berater):      ║
║      BLUEPRINT (1-8):         ║   ║      observe → modelMaintain → ║
║       1. cleanCodeArchitect   ║   ║      qualityGate → hypothese → ║
║       2. requirementCheck     ║   ║      implement → ergebnis      ║
║       3. patternLibrary       ║   ║                                 ║
║       4. testSearch           ║   ║      Phase 5 AUTOCHAIN-EXIT    ║
║       5. goldDefine           ║   ║      (INV-MODUS-7 Pflicht)     ║
║       6. blueprintQG          ║   ║                                 ║
║       7. cleanCodeSlice       ║   ║      → POST_HANDOVER            ║
║       8. mitose + fanOut      ║   ║                                 ║
║      TDD (9-18, --tdd=true):  ║   ║                                 ║
║       9  _TDD_init            ║   ║                                 ║
║       10 _TDD_red             ║   ║                                 ║
║       9b _TDD_setup (BL-53)   ║   ║                                 ║
║       11 _TDD_execute+monitor ║   ║                                 ║
║       12 _TDD_green           ║   ║                                 ║
║       13 _TDD_execute+monitor ║   ║                                 ║
║       14 _TDD_refactorCode    ║   ║                                 ║
║       15 _TDD_execute+monitor ║   ║                                 ║
║       16 _TDD_refactorTests   ║   ║                                 ║
║       17 _TDD_execute+monitor ║   ║                                 ║
║       18b _TDD_teardown       ║   ║                                 ║
║       18 _TDD_check           ║   ║                                 ║
║      CLOSURE (19-20):         ║   ║                                 ║
║       19 _I_verify            ║   ║                                 ║
║       20 _I_fanIn + Stage-QG  ║   ║                                 ║
║      NACHPHASE: verify global ║   ║                                 ║
╚═══════════════╤══════════════╝   ╚═══════════════╤═════════════════╝
                │                                  │
                └───────────────┬──────────────────┘
                                ▼
                ★ GEIST #7  [_I/_SC → _SDF_orchestrate_post]
                                ▼
╔════════════════════════════════════════════════════════════════════════╗
║  [6] /_SDF_orchestrate_post   (BL-NEW-12 Post-Phase 3+4)               ║
║      Phase 0 Entry-Log → 3.0.5 BUILD-Sanity (M1/worker-mode)           ║
║      WAVE 1: 3.1 recalibrate + 3.2 postItem (parallel)                 ║
║      Anti-Mega-Worker Wave-1-JOIN-Check (INV-POST-4)                   ║
║      WAVE 2: 3.3 statusTransition + 3.5 modelSync (parallel)           ║
║      3.3.5 _stage_orchestrate (Commit pro Round)                       ║
║      3.4 batchEnde (nur letzte Round, Wave 3 PT+SL parallel)           ║
║      3.6.0 PLAN-IMMUTABLE-Check (BL-NEW-44.1)                          ║
║      3.6.1 _SDF_berater_stageElevation                                  ║
║              ELEVATE → Skill(_I_orch --stage=N+1)                       ║
║              BATCH_DONE → falle durch zu Phase 4                       ║
║              RETRY/ABORT/HALT                                          ║
║      3.6b post_sc_pl_resync (BL-208)                                    ║
║      3.99 Phase-3-Exit Backstop (INV-POST-5)                            ║
║      Phase 4.1 loopDecision → 4.1.5 Orphan-Scan-Gate (BL-NEW-60)       ║
║      Phase 4.2 Exit-Routing:                                            ║
║        RE-BATCH      → Skill(_SDF_orch, --resume)                      ║
║        SOFT-REPRIO   → Skill(_IDF_orch, --mode=recluster)              ║
║        ROLLBACK      → Skill(_IDF_orch, --mode=recheck)                ║
║        TERMINATE     → RETURN to BDF                                   ║
╚═══════════════════════════════╤════════════════════════════════════════╝
                                ▼
                ★ GEIST #8  [_SDF_post → _SDF_orch / _IDF / BDF]
                                │
                                │ (nach allen Batches: PHASE FINAL)
                                ▼
╔════════════════════════════════════════════════════════════════════════╗
║  /_SDF_orchestrate PHASE FINAL                                         ║
║      Checkpoint C (HiL nach Finish, BL-042)                            ║
║      TeamDelete (sdf-{NAME})                                           ║
║      Protokoll-Rollover (_manifest_protokoll.md, W18 Prepend)          ║
║      DF_PIPELINE_STATE = DONE → IDLE                                    ║
╚═══════════════════════════════╤════════════════════════════════════════╝
                                │  ◄┄┄ RETURN to BDF Phase 3
                                ▼
                  BDF Phase 3 ITEM_DONE → ⟲ zurueck zu Phase 2 SCANNING
                  (naechster BL-Item wird gepickt → ★G#1 wiederholt)
                                │
                                │ (alle Items DONE → EMPTY-Handler)
                                ▼
                ★ GEIST #9  [BDF EMPTY-Handler → _PostBatch_orchestrate]
                                ▼
╔════════════════════════════════════════════════════════════════════════╗
║  [7] /_PostBatch_orchestrate v1.0   (Batch-Qualitaet nach Item-Loop)   ║
║      Schritt 0 Entry → 1 _T_orchestrate → 1.3 _ArchConformance →       ║
║      1.5 _PatternConformance → 2 _stage_orchestrate →                  ║
║      3 _garbageCollection → 4 _stateMaintain → 5 BDF_NEXT_TRIGGER=true ║
╚═══════════════════════════════╤════════════════════════════════════════╝
                                ▼
                ★ GEIST #10  [_PostBatch → _Pre_PR_orchestrate]
                                ▼
╔════════════════════════════════════════════════════════════════════════╗
║  [8] /_Pre_PR_orchestrate v3.0.0   (9 Quality Gates PARALLEL)          ║
║      Phase 0a prePr-Modus → 0 Datei-Listen → 0b Gate-Selektor →        ║
║      Phase 1 Team Setup → Phase 2 KURZLEBIG_PROMPT                     ║
║      9 Gates PARALLEL: Tests / Naming / Cleanup / Dokumentation /     ║
║              Konstanten / Logging / Architektur / Analyzer / Migration ║
║      Phase 3 Aggregation → 3.5 Finding-Persistenz                      ║
║      Phase 4 Build+Test → 4b FAN_IN → 4c Pattern-Battle-Test →         ║
║              4d SkillLoadSelfTest (BL-159) →                            ║
║      Phase 5 Summary + Shutdown (oder 5a/6/7 Report-Modus)             ║
╚═══════════════════════════════╤════════════════════════════════════════╝
                                ▼
                ★ GEIST #11  [_Pre_PR → BDF (Loop next BL)]
                                ▼
            ⟲ ZURUECK ZU BDF Phase 2 SCANNING (naechstes BL-Item)
                  oder
            ⟲ BDF Phase 6 Terminal (Protokoll-Rollover, Factory-Lock release)
```

### 10.4 Schritt-Anzahl pro Orchestrator (1-BL-Reise)

| # | Orchestrator                | Steps | Berater | Sub-Calls |
|---|-----------------------------|-------|---------|-----------|
| 0 | /_backlog                   | 10    | —       | —         |
| 1 | /_BDF_orchestrate           | 8     | 4       | 1 (_batchPlan) |
| 2 | /_A_orchestrate             | ~18   | 13      | 7         |
| 3 | /_IDF_orchestrate           | ~16   | ~19     | —         |
| 4 | /_SDF_orchestrate (Pre)     | ~10 + Loop | 6   | dispatcht zu I/SC |
| 5 | /_I_orchestrate             | ~20/Stage | 6  | 10 TDD-Steps + sub-Skills |
| 5 | /_SC_orchestrate            | ~15   | 6       | 6 SC-Berater + opt. I-Call |
| 6 | /_SDF_orchestrate_post      | ~15   | 8       | 1 (_stage_orchestrate) |
| 7 | /_PostBatch_orchestrate     | 5     | 2       | 5 (_T, _Arch, _Pattern, _stage, _GC) |
| 8 | /_Pre_PR_orchestrate        | ~16   | —       | 9 Gates |
|---|-----------------------------|-------|---------|-----------|
|   | **TOTAL pro 1-BL-Reise**    | **~110** | **~64** | **~40** |

Von ~250 Commands im System beruehrt eine Standard-Reise also ~110-200 unique Skills
(modus-abhaengig: M2 ist kuerzer, M3+M5+M9 brauchen mehr).

### 10.5 Verwendung dieser Sicht

**Operator-Sicht:** Verstehen wo man in der Pipeline ist + welche Geister-Uebergaenge
gerade laufen.

**Scan-Sicht:** Mit dem 3er-Doppel-Floating-Window pro Step die Vertraege pruefen.
Siehe `.claude/INSTRUCTION_full_scan_2026-05-24.md` (Methodik) und
`.claude/GOAL_full_scan_2026-05-24.md` (Ziel + Termination).

**Help-Sicht:** Jeder Pipeline-Help (`/_A_help`, `/_IDF_help`, `/_SDF_help`,
`/_SC_help`, `/_I_help`, `/_TDD_help`, `/_PrePR_help`) hat seine eigene Detail-
Sektion. Diese hier ist die uebergreifende Reise-Sicht.

### 10.6 Cross-References

- **Methodik:** `.claude/INSTRUCTION_full_scan_2026-05-24.md`
- **Ziele:** `.claude/GOAL_full_scan_2026-05-24.md`
- **Vision (Sanduhren-Prinzip):** `Crumbs/architecture-vision-2026-05-22.md`
- **Per-Pipeline Detail-Helps:** `/_A_help`, `/_IDF_help`, `/_SDF_help`, `/_SC_help`,
  `/_I_help`, `/_TDD_help`, `/_PrePR_help`
- **Tiefen-Narrative:** `/_A_help_extended`, `/_IDF_help_extended`, `/_SDF_help_extended`

---

## TEIL 11 — VDD: VERTRAG-DRIVEN-DEVELOPMENT (BL-467, contract-driven)

```
+================================================================================+
|  DAS BAU-PRINZIP fuer Orchestratoren (hoechste Prio, INSTRUCTION 2026-06-24)    |
+================================================================================+

KRANKHEIT vs SYMPTOM:
  Megaworker (1 Agent macht alle Phasen inline) war das SYMPTOM.
  Die KRANKHEIT war: fehlende Vertrag-Architektur. A/IDF waren von Geburt an
  contract-driven (State lesen / 1 Unit-of-Work pro Spawn / eigenen Slot
  schreiben) = stabil. I/SDF/SDF-post/PostBatch waren es NICHT (SPAWN=0,
  inline) -> Megaworker. BL-467 heilt die Architektur, nicht das Symptom.

DIE DREI VDD-SAEULEN (jeder umgebaute Orchestrator bekommt sie):
  1) STATE-MACHINE mit benannten DONE-Zustaenden
     I:        blueprint -> goldDefine -> testSearch -> RED -> GREEN ->
               refactor -> verify   (*_RUNNING / *_DONE)
     SDF-post: INIT -> BUILD_SANITY_DONE -> WAVE1_DONE -> WAVE2_DONE ->
               COMMIT_DONE -> BATCHENDE_DONE -> STAGE_ELEVATION_DONE ->
               PL_RESYNC_DONE -> LOOPDECISION_DONE -> ORPHAN_SCAN_DONE ->
               EXIT_ROUTED -> COMPLETED | ABORTED_PROCESS_VIOLATION
  2) EIN BERATER_OUTPUTS-SLOT PRO PHASE   { status, exit_code, last_berater }
     PAYLOAD-FREI. Der Lead liest NUR den Zustand (exit_code), NIE die
     fachliche Berater-Payload. Fachdaten reisen ueber Vault-Vertragsdateien
     zwischen den Beratern (DATENFLUSS-PRINZIP, INV-DATA-I-1).
  3) [GATE P] exit_code-Gate VOR JEDEM SPAWN (skip-tolerant):
     0 = DONE, 2 = FAIL (Vertrags-/Post-Check), 99 = ABORTED_PROCESS_VIOLATION
     NUR ==99 bricht ab. Legitime Skips degenerieren zu einem 0-Pass-Through.

INV-SPAWN (= INV-PM-5-aequivalent, BL-465):
  Jede Top-Level-Berater-Phase MUSS per Worker-Spawn laufen. Der Lead laedt
  Berater NIE inline. "Skill(_X_berater_Y)" im Pseudocode = Kurzschrift fuer
  Agent(prompt="Lade Skill _X_berater_Y, schreibe BERATER_OUTPUTS-Slot, stirb").
  Lead-direkt-Load = Megaworker (verboten).

LOAD-BEARING DOKTRIN (M2-SEAM-HARDENED, BL-466):
  Die Transitions-Kette haengt am STATE-HANDOFF, NICHT an einem TDD-/Modus-Flag.
  Modus-unabhaengig (M1-M9). KEINE Phase wird je aus der Kette entfernt; im
  M2-Pfad (tdd=false) degenerieren RED/refactor zu reinen exit_code=0-State-
  Transitions (kein Skip). Wuerde man Phasen modus-konditional entfernen,
  hinge der Seam wieder an TDD -> der M2-Megaworker waere zurueck.
  => Der state-getriebene Vertrag ist der PRIMAERE Megaworker-Schutz.
     TDD/RED!=GREEN + Guards (TEIL 15) sind nur noch der "2. Notnagel".

AUSROLL-STATUS (orchestrator-weise):
  PILOT  I-Orchestrator : BL-464 (Fundament) -> BL-465 (INV-SPAWN) ->
                          BL-466 (M2-SEAM-HARDENED)   [DONE]
  SDF-Familie          : BL-468 _SDF_orchestrate (5 Pre-Calls, [GATE P1-P7])
                         BL-469 _SDF_orchestrate_post (31 Slots, [GATE P1-P10])
                         BL-470 _PostBatch_orchestrate (fragilster Umbau, KEIN
                           Motor -> State-Seam EINZIGER Schutz)
  NOCH NICHT VDD       : _SC_orchestrate (berater-phasen-strukturiert, teilt
                         nur das aeltere Fundament — kein 7-Phasen-State-Vertrag)
  REPLIKATION/FORWARD  : BL-472 Pattern via /_PT_orchestrate; jeder NEUE
                         Orchestrator ist von Geburt an contract-driven.
```

---

## TEIL 12 — DIE HEILIGE TRIO: WORKFLOW-MOTOR (BL-222 + FIX2/BL-210)

```
+================================================================================+
|  OmniCommand (Verstand/Skills) + WORKFLOW-MOTOR + Hooks (Immunsystem)           |
+================================================================================+

WARUM:
  SDF's Implement-Inner-Loop lief frueher als interpretiertes Skill-Pseudocode
  (in-Skill WHILE-Stage-Loop). Dieses Fenster konnte als "spawn 1 Dispatch-
  Worker" fehlinterpretiert werden -> Mega-Worker (DCSRE-486 Round-17). Der
  Motor schliesst das Fenster PHYSISCH.

dispatch_implement.js (.claude/workflows/) — deterministischer Dispatch:
  Phasen: Modus -> PatternBrief -> Implement -> Elevate -> BatchClose ->
          LoopDecision. Pro Sub-Batch FLAT-SEQUENCE:
          BLUEPRINT_STEPS -> (TDD_CORE wenn M3/M6) -> CLOSURE_STEPS,
          jeder Eintrag = ein eigener agent().
  runPhase3(sb): spawnt recalibrate/postItem/statusTransition/modelSync NUR
          @BATCH_DONE (Phase-3-Aequivalent im Motor). Die motor-gespawnten
          I/SC-Worker chainen _SDF_orchestrate_post NICHT (kein Doppel-Call).

INV-MOTOR-1: Step-Skeleton ausschliesslich aus feststehendem modus;
             1 agent() = 1 Sub-Skill-Load. Mega-Worker strukturell unmoeglich
             (kein Self-Assign, keine Step-Buendelung).
INV-MOTOR-2: Der Workflow RETURNED nur loop_decision an den Lead. ROUTING
             (ROLLBACK/RE-BATCH/SOFT-REPRIO/TERMINATE) macht der LEAD.
             Loop-OWNERSHIP beim Lead, Loop-AUSFUEHRUNG in der Engine.

HAERTUNGEN: safeSchemaAgent (BL-228 Schema-Crash-Fang), verify_mode tdd/
  scenario/convention (BL-276), Infra-Setup modus-frei (BL-329), persistenter
  phase3_fired-Guard + Idempotenz (BL-319), runStageCommit-Security-Gate (BL-299).

MOTOR vs VDD (Verhaeltnis):
  Motor = PROZEDURALER Schutz (Engine erzwingt 1-Step=1-Agent).
  VDD   = STRUKTURELLER Datenvertrag (State-Handoff + exit_code-Gate pro Slot),
          greift AUCH ohne Motor und ohne TDD — genau dort wo das M2-Loch war.
  Heute primaer VDD; Motor ist das deterministische Gegenstueck (DEFAULT OFF,
          via VEHIKEL-Gate TEIL 13).
  Weitere Workflows: dispatch_findings / dispatch_arc42 / dispatch_model_drift.
```

---

## TEIL 13 — VEHIKEL-DOKTRIN: TEAM vs WORKFLOW (BL-330)

```
+================================================================================+
|  Vor jedem Dispatch routet der Lead per Karte WELCHES Vehikel.                  |
|  Volldoktrin: .claude/commands/_vehikel.md (Engine-Kanon)                       |
+================================================================================+

KARTE:
  py -3 .claude/scripts/workflow_zones.py vehicle --activity={X} --mode={workflow}

  GRUEN  = WORKFLOW   deterministisch, fire-and-collect (Motor, TEIL 12)
  GELB   = ADVISORY   Workflow rechnet, Member/Lead bestaetigt das Urteil
  ROT    = TEAM       benanntes TeamCreate + benannte Member + Task-DAG
                      (TaskCreate blockedBy) + SendMessage = "altmodisch"

EIN DIAL:  workflow in {false, normal, fast}, default=false (session_params_
           resolver). Bypass-Felder -> ValueError. Default-Zustand = ALTMODISCH.

INV-VEHIKEL-2: ROT ist NIE Workflow (Kurzschluss in resolve_vehicle; unbekannt
  -> rot fail-safe). Rote Zone = C3-modusEntscheidung, TDD-Kern (red/green/
  refactor/check), goldDefine/cleanCode*/_I_verify, modelSync, batchPlan,
  specParse, sc_verdict.
INV-VEHIKEL-3 (WARUM Team): Member-gegenseitige-Sichtbarkeit faengt false-GREEN
  ("GREEN bei TDD auf einer Migration? Kannst du dir abschminken") — was ein
  Workflow strukturell durchwinkt. Teams seit vor-Opus-4.8 bewaehrt.
INV-VEHIKEL-6 (Ketten-Granularitaet): Dispatch-Einheit = die zusammenhaengende
  gleich-Vehikel-KETTE in Pipeline-Reihenfolge, NICHT der einzelne Step. Lone
  gruener Step zwischen roten -> Team-Member fuehrt ihn INLINE aus. Workflow ab
  >=2-3 konsekutiven gruenen/advisory Schritten. Laengste gruene Ketten:
  SDF Pre-Plan len-7 + SDF Post-Bookkeeping len-7.
INV-VEHIKEL-6b: ZONE_REGISTRY ist NICHT optional fuer deterministische Berater —
  jeder green/yellow MUSS registriert sein, sonst zerhackt der rot-Fail-Safe
  korrekt-gruene Ketten. Muster: Determinismus an Pipeline-RAENDERN, rote Seams
  als isolierte Inseln in der Mitte.   Command: /_vehikel
```

---

## TEIL 14 — WORKTREE-PARALLEL-LANES (BL-431, BL-490)

```
+================================================================================+
|  Offizieller Parallel-Weg: mehrere BLs in getrennten Git-Worktrees/Lanes.       |
|  Volldoktrin: .claude/commands/_worktree_parallel.md (Engine-Kanon)             |
+================================================================================+

MODELL:
  Jeder Worktree = 1 Roadmap-Lane (BL-430 ROADMAP-ORDER). Lanes datei-DISJUNKT
  zwischen Lanes, SEQUENZIELL innerhalb einer Lane. IDs: WT-{N}
  (worktree_registry.py, kollisionsfrei). Registry: {vault}/_worktree_registry.md.

INV-WT-SEQUENZ (load-bearing): Den Parallel-Mechanismus ZUERST seriell auf
  EINEM Terminal bauen + nach develop mergen — ERST DANN Worktree-Split.
  Erst die Maschine bauen, dann parallel. Kein Split vor Registry+Handoff-Infra.
INV-WT-DIAL: bl_parallel default=False (orthogonal zu parallel_mode), opt-in via
  session_params_resolver.
INV-WT-ID:   Handoff CLEAN -> merge_seam.py / CONFLICT -> PL + Hold.

INV-WT-FFSAFE (BL-490) — die geteilte develop/main NIE ad-hoc force-moven:
  Lane -> develop NUR ueber das FF-safe-Gate
    py -3 .claude/scripts/merge_seam.py advance --ref develop --to <lane>
  non-FF -> REFUSE (exit 2). Strukturell erzwungen durch
  guard_branch_force_develop.py (PreToolUse blockt `git branch -f` auf geteilter
  develop). Wurzel: ein `git branch -f` verwarf beinahe develop-only-Commits
  (reflog-gerettet). + Reflog-Recovery-Runbook.

MOTHERSHIP:
  /_lane_watchdog = Watchdog (crown+sanity) ueber die Lanes, kein zusaetzlicher
  Worker. Tiefen-agnostisch (BL-351 nested Mothership, Cap=3). Lane-Closure im
  SDF-TERMINATE-Zweig: optionaler merge_seam (BL-425, default OFF) -> develop-
  Resync (BL-442) -> Lane-Queue-Pointer-Advance -> guard_lane_closure_stop.py
  (BL-444) backstoppt.
```

---

## TEIL 15 — GUARD-ENFORCEMENT / IMMUNSYSTEM (das 3. Bein der Trio)

```
+================================================================================+
|  Hooks (.claude/scripts/guard_*.py) erzwingen die Prozess-Invarianten          |
|  STRUKTURELL — nicht als Bitte, als PreToolUse-BLOCK.                            |
+================================================================================+

INV-AO-CALLER (CLAUDE.md Rule 6, GUARD-ENFORCED BL-439):
  _X_orchestrate-Skills MUESSEN vom Team-Lead SELBST geladen werden (direkt nach
  Skill(_X_orchestrate)-Load). VERBOTEN: Orchestrator via Agent(prompt=
  "...orchestrate...") delegieren -> Mega-Agent (interpretiert Skill(_X_berater_
  Y)-Pseudocode als Inline-Logik). guard_agent_prompt_validator.py Check 3 faengt
  BEIDE Formen:
    Slash-Form   /_X_orchestrate        im Agent-Prompt
    Klammer-Form Skill(_X_orchestrate)  im Agent-Prompt   (BL-439-Fix)

INV-BUILD-GRAIN (CLAUDE.md Rule 7, BL-423):
  M1   -> Einzel-Worker/inline erlaubt (einziger Abkuerzungs-Tier).
  M2/M3-> STRIKT die volle I-Pipeline als GETRENNTE Single-Phase-Worker, gefahren
          ueber Lead-geladenes Skill(_I_orchestrate). NIE 1 Worker pro Batch
          (= monolithic-build-worker = Mega-Worker).
  RED-Worker != GREEN-Worker = der load-bearing false-GREEN-Fang (wer einen Test
          erfuellt, hat ihn NICHT selbst geschrieben).

PFAD-MATRIX "kein Bau-Eingang ab batch_status=READY ohne Guard":
  | Bau-Eingang ab READY                          | Gefangen von                 |
  |-----------------------------------------------|------------------------------|
  | Manifest IDF_DONE, SDF erwartet, ohne         | guard_idf_sdf_handoff.py     |
  |   Skill(_SDF_orchestrate)                     |   AK-a Write-Trigger (BL-313) |
  | Agent/TaskCreate Build-Spawn @ READY ohne     | guard_idf_sdf_handoff.py     |
  |   Skill(_SDF_orchestrate) seit IDF            |   AK-a Seam-Trigger (BL-423)  |
  | Build-Worker test+impl gebuendelt (M2/M3)     | guard_agent_prompt_validator |
  |                                               |   Check 5 detect_monolithic_ |
  |                                               |   build_worker (BL-423)       |
  | I/SC-Build-Ende ohne nachfolgendes            | guard_sdf_post_handoff.py    |
  |   _SDF_orchestrate_post vor naechstem Resume  |   (BL-427)                    |
  | M1-Skelett-Scope-Ueberschreitung / M1-Lead-   | guard_agent_prompt_validator |
  |   inline-Code ohne _I_orchestrate-Handschuh   |   Check 6 detect_m1_skeleton_ |
  |                                               |   overreach (BL-400)          |
  => jeder Aktivierungs-Pfad ab READY trifft einen Guard. Kein stiller Bypass.

WEITERE GUARDS (Auszug):
  guard_a_idf_handoff.py (INV-A-GUARD-1: A-Ende ohne IDF-Handoff bei
    idf_invoke_required; Ausnahme DEFER/A_RETRY) · guard_branch_force_develop.py
  (BL-490 FF-safe) · guard_autochain_stop.py (BL-394, RE-BATCH+hil=off Sofort-
  Chain) · guard_lane_closure_stop.py (BL-444) · guard_modus_writer.py
  (INV-MODUS) · geist9/geist9b (Phase-3.x + [ ]->[x] Gate) · ModelLeakGuard
  (audit.jsonl) · Checks 8/9 (block general-opus-Phantom / general-haiku-
  Reasoning, BL-452/461).
```

---

## TEIL 16 — OMNICOMMAND-ARCHITEKT-PFLICHT (OBERSTE Standing-Rule)

```
+================================================================================+
|  Der Team-Lead IST der OmniCommand-Architekt — Eigentuemer der Kohaerenz,       |
|  Gesundheit + Evolution des Meta-Systems, nicht nur Ausfuehrer. (2026-06-13)    |
+================================================================================+

ARCHITEKT-1 (Anti-Pflaster-Pflicht, IMMER ausnahmslos):
  Sobald ad-hoc ein Pflaster gelegt wird (Workaround/Soften/Bypass/Deviation —
  least-stall erlaubt, das Pflaster selbst ist OK), MUSS im selben Flow ein
  proper-fix Backlog-Item entstehen (/_backlog, single-writer, priority=hoch,
  type=bug, parent_epic=BL-322 bei Engine-Health; Pflaster + Wurzel + Fix-Skizze
  im Body). NIE still, NIE nur Pflaster liegen lassen. Konsolidieren erlaubt.

ARCHITEKT-2 (OmniCommand-selbst = OBERSTE Prioritaet):
  Items am OmniCommand-Meta-System selbst (Engine/Skills/Hooks/Pipeline/Health)
  rangieren UEBER aller Projekt-/Feature-Arbeit. heal_optimize_first: erst
  heilen/optimieren, dann ausbauen.

ARCHITEKT-3 (Automatisierung von ARCHITEKT-1):
  /_crown2_orchestrate (System-Health-Deviation-Observer, Crown-2, BL-252) +
  /_disciplinary_report (Feldjaeger, Lead-Abweichungs-Capture, BL-324) + BL-323
  (Deferral->materialize, DONE). Bis vollstaendig gebaut ist ARCHITEKT-1 die
  manuelle Standing-Disziplin.

VERWANDTE STANDING-COMMANDS:
  /_crown (Worker-Watchdog, Cron-Doppelcheck gegen Worker-Stall) ·
  /_sanity_check / _sanity_check_pre / _sanity_check_post (Schweizer-Uhrmacher) ·
  /_health_orchestrate (STATE-Format-Drift Scan + Heilung) ·
  /_goal_backlog / _goal_parking_lot (Goal-Driven-Lauf mit Process-Enforce).
```

---

## TEIL 17 — ATOMIC-TRUTHS: ATOM/EDGE/VIEW-SUBSTRAT + CAPSTONE (BL-451/483/484)

```
+================================================================================+
|  GROESSTER Wissensmodell-Umbau: Wahrheiten sind atomare NODES, Edges sind die   |
|  Struktur, und Model/Spec/arc42/Parking/Doc werden VIEWS ueber die Atome.       |
+================================================================================+

SUBSTRAT (BL-451 Epic):
  - Wahrheiten = atomare Nodes (type=truth, id endet auf "."+local_id,
    content_hash = sha256(text)). ~1171 Atome verdrahtet (BL-242).
  - Edges = Struktur: keyword_edge_writer (truth-only-scope, BL-479) +
    truth_edge_backref (Inversion B<-A, BL-451). Edge-Index atom-aware.
  - VIEWS-als-Referenten: view_projector + wikilink_materializer schreiben
    view.source_atoms (BL-460); das Atom nennt die View-id in referenced_by
    (BL-491 path-derived view-id). View-Forward-Garantie (BL-480/388): eine neue
    View ohne source_atoms wird beim Write self-maintaining verdrahtet.
  - Typ-Reinheit: De-Merge keywords vs referenced_by (BL-489).

NEUE VIEW-FAMILIE:
  /_arc42_orchestrate + 13 _arc42_berater_* (arc42 §1-12) rendert arc42-Sichten
  als "Views auf Wahrheiten" (Thin-Manager; Workflow dispatch_arc42).
  Migrations-Invoker: /_W_atom_migration_orchestrator (Wahrheits-Atomisierung).

CAPSTONE (BL-483) — bombensicherer 8-Stufen-Migrations-Orchestrator:
  /_truth_migration_capstone (Thin-Invoker) -> truth_migration_capstone.py.
  dry-run=DEFAULT (--write braucht --force-go ODER interaktives "GO"); per-Stufe
  gegatet; backup-tag vorab; Gate-Fail -> ROLLBACK (git checkout backup-tag) ->
  exit 2. Stufen:
    0 preflight_and_backup -> 1 atomize -> 2 edges ->
    3 edge_quality_gate (dangling==0, <=15 edges/atom, BL-455) ->
    4 backref_inversion -> 5 wikilinks -> 6 edge_index ->
    7 views (Fan-out pro PL-View) -> 8 post_gate (truth_capstone_gate.py).

CAPSTONE-GATE G1-G6 (BL-484, truth_capstone_gate.py) — beweist der Vault ist
"auf der atomaren Seite": vollstaendig + verbunden + verlustfrei + forward-
garantiert. migration_complete == alle 6 GRUEN. NO-FALSE-GREEN (leerer Vault /
nicht-lauffaehiger Check -> ROT). Read-only; G4 nutzt eine TEMP-Sandbox.
  G1 truths_are_nodes      Substrat vollstaendig (id/local_id konsistent)
  G2 edges_bidirectional   0 dangling forward + invertierte backrefs aufloesbar
  G3 views_are_referents   jede View-source resolved, Atom nennt die View-id
  G4 forward_garantie_live LIVE-Probe: Engine PRODUZIERT Referent (write=True)
  G5 loss_zero             content_hash == sha256(text), 0 id-Kollisionen
  G6 navigable             edge_index sauber + Wikilink-Sektion pro Edge-Atom
```

---

## TEIL 18 — STAGE/RESOURCE-LOCK-SYSTEM (BL-407)

```
+================================================================================+
|  Atomare Vault-Stage-Doc-Slices + Stage-Lifecycle + zentraler Ressourcen-       |
|  Allocator. IDF-Planung liest Divisibilitaet.                                    |
+================================================================================+

STAGE-SLICES (BL-392/419):
  1 Slice pro Concern (atomar). Stage-Lifecycle setup -> test -> teardown als
  Einzel-Steps (nicht 1 Monolith). Command-Familie:
    /_stage {nr}            step-relevante Slice(s) in-Context laden
    /_stage_init  /_stage_add  /_stage_update (single-slice-only)  /_stage_help
    /_stage_sanity_check    strukturell verifizieren (BL-486: 6 Verhaltens-Checks)

STAGE-LIFECYCLE-EXECUTION (BL-408/414):
  In _I_orchestrate eingezogen; Orchestrator-Stage-Awareness + Stage-State
  (INV-STAGE-STATE-1).

RESSOURCEN-ALLOCATOR (BL-247):
  teilbar/unteilbar, claim/lease/wait/release. Region-Lock: line-range-claim ->
  DISJUNKTE Regionen parallel bearbeitbar. IDF-Planung (parallelSuitability,
  Phase 7.8) liest Divisibilitaet fuer die Parallel-Bucket-Bildung.

COMMIT-NORMIERUNG (/_stage_orchestrate, v2.0.0, post-I-fanIn):
  TL macht KEINE git-Ops (Rollentrennung). Prueft Produkt-Commits gegen
  stage.md-Normen + Security-Gate (leak_patterns.py): kein Co-Authored-By/
  Anthropic/Claude, keine Prozess-Cross-Refs (BDF/SDF/BL-/PL/_-Commands).
  Commit-Freeze-Gate (INV-STAGE-FREEZE-1) -> Handover statt Commit.
```

---

## INV-MODUS-Sektion (BL-165)

Vollstaendige Spezifikation: `Vault/Backlog/BL-165-df-batch-state-modus-naming-conflict/3_Spec/BL-165_Spec.md`

| INV-ID | Regel (1 Satz) | Scope |
|--------|---------------|-------|
| INV-MODUS-1 | `DF_BATCH_STATE.modus` darf AUSSCHLIESSLICH von `_SDF_berater_modusEntscheidung` (SDF Phase 1.1) gesetzt werden. | SDF, alle Pre-SDF-Skills |
| INV-MODUS-2 | SDF Phase 1.1 ist NICHT skippbar — auch nicht wenn upstream-Daten bereits eine Empfehlung enthalten. | SDF Phase 1.1 |
| INV-MODUS-3 | `_SDF_berater_modusEntscheidung` MUSS in `modus_begruendung` eine nachvollziehbare Ableitung aus Daten dokumentieren. | _SDF_berater_modusEntscheidung |
| INV-MODUS-4 | Bei heterogenen Sub-Batches entscheidet SDF Phase 1.1 PRO BATCH (nicht einmalig global); `batch_modes`-Map akkumuliert. | SDF Outer-Loop |
| INV-MODUS-5 | Verbotene Bypass-Felder fuer alle Pre-SDF-Skills: `recommended_modus`, `sdf_mode`, `sdf_mode_hint`, `expected_sdf_mode`, `mode_recommendation`. | A/IDF/K-Score/Gap/SRS/BDF |
| INV-MODUS-6 | SDF Outer-Loop: Phase 1.1 entscheidet PRO ROUND mit aktuellem Vault-State; Phase 3.5 persistiert Erkenntnisse vor naechster Round. | SDF Outer-Loop |
| INV-MODUS-7 (KONDITIONAL-NEUFASSUNG, DCSRE-486 2026-05-29) | Phase 3 + 4 laufen nach JEDEM Batch-Implement via GENAU EINEM von zwei Pfaden — NIE skippen, NIE inline: **MOTOR-Pfad** (Engine `dispatch_implement` ruft Phase-3.x intern, KEIN Doppel-Call) ODER **SKILL-HANDSCHUH-Pfad** (Lead `Skill(_SDF_orchestrate_post)`, INV-HANDOVER-1). `_SC_orchestrate`/`_I_orchestrate` haben im Handschuh-Pfad kein Selbst-Exit-Recht. | SDF, _I/_SC, _SDF_orchestrate_post |
| INV-MODUS-8 | `_SC_implement` = reiner Handover-Step; schreibt AUSSCHLIESSLICH `sc_handover.md`, kein Code. | _SC_implement |
| INV-MODUS-9 | SDF Phase 4 loopDecision setzt `sc_resume_from = "ergebnis"` bei SC-Re-Entry, `null` bei Erst-Eintritt. | SDF Phase 4, loopDecision |

Enforcement: `guard_modus_writer.py` + `regression_test_modus_keys.py` + `pre_commit_modus_check.sh` (BL-165). INV-MODUS-7 zusaetzlich: **geist9** (blockt `loopDecision`/`PostBatch` ohne Phase-3.x-Outputs) + **geist9b** (blockt `[ ]→[x]`/completed_batches ohne vorausgehenden `_SDF_orchestrate_post`) + `guard_sdf_post_handoff.py` (BL-427, blockt `_SDF_orchestrate`-Resume ohne vorausgehendes `_SDF_orchestrate_post` SKILL_LOAD).

---

## Verwandte Hilfe-Commands

- `/_A_help` / `/_A_help_extended` — A-Pipeline Detail
- `/_IDF_help` / `/_IDF_help_extended` — IDF-Pipeline Detail
- `/_SDF_help` / `/_SDF_help_extended` — SDF-Pipeline Detail
- `/_SC_help` — SC-Forschungszyklus Detail
- `/_I_help` — I-Pipeline Detail
- `/_TDD_help` — TDD-Sub-Skills Detail (Top-Level _TDD_orchestrate ist DEPRECATED 2026-05-09 BL-169; TDD-Steps 9-18 jetzt in I-Pipeline am Pipeline-Ende)
- `/_W_help` — Wissens-Koaleszenz (Vault-Sync)
- `/_PrePR_help` — Pre-PR Quality Gates
- `/_obsidianHelp` — Obsidian-Integration
- `/_D_help` — Debloat-System

**Doktrin- & Meta-Commands (v3.0.0 — siehe TEIL 11-18):**

- `/_vehikel` — Vehikel-Doktrin: Team vs Workflow (TEIL 13)
- `/_worktree_parallel` — Offizieller Parallel-Weg via Worktrees (TEIL 14)
- `/_truth_migration_capstone` — atomic-truths 8-Stufen-Capstone (TEIL 17)
- `/_arc42_orchestrate` — arc42-Sichten-Renderer (Views auf Wahrheiten, TEIL 17)
- `/_W_atom_migration_orchestrator` — Wahrheits-Atomisierungs-Migration
- `/_stage_help` — Stage-Slice-Kanal-Familie (TEIL 18)
- `/_roadmap` / `/_roadmap_backlog` / `/_roadmap_parkingLot` / `/_roadmap_stern` — Roadmap-Kompass (Macro/Micro/Nordstern)
- `/_lane_watchdog` — Mothership-Watchdog ueber die Parallel-Lanes
- `/_crown` / `/_crown2_orchestrate` — Worker-Watchdog / System-Health-Deviation-Observer
- `/_disciplinary_report` — Feldjaeger (Lead-Abweichungs-Capture)

---

ARGUMENTS: $ARGUMENTS
