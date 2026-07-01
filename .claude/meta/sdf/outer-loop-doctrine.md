# SDF Outer-Loop-Doctrine — Stale-Handoff, Vehikel-Gate, Motor-vs-altmodisch

Referenz fuer `/_SDF_orchestrate` PHASE OUTER-LOOP-WRAPPER. Der Conductor behaelt die ausfuehrbaren
Branches (Stale-Handoff-Materialisierung, Vehikel-Gate-Entscheidung, Motor-Pfad, altmodischer Pfad,
loop_decision-Routing); die Narrativ-/Begruendungs-Bloecke + INV-MODUS-Doktrin liegen hier.
Ausgelagert aus BL-401 (SRP-Refactor).

---

## OUTER-LOOP-Architektur (BL-134 / BL-165 INV-MODUS-4 D-Architektur)

Phase 1.1, 1.5, 2.1 + Phase 3.1-3.5 laufen in einer **OUTER-LOOP** pro Sub-Batch
(`batch_items_per_batch[]`). Jede Round = 1 Sub-Batch mit komplettem
Decision→Dispatch→Cleanup-Cycle + modelSync zwischen Rounds (Continuous Learning).

---

## STALE-HANDOFF-RECOVERY (DCSRE-486 --no-chain/Compact-Live-Fix)

**Problem (Live-Beobachtung):** IDF lief mit --no-chain/--pl-only (oft Compact-Anomalie: der
Post-Compact-Resume rannte IDF standalone ohne Auto-Chain). IDF schrieb
metric_per_batch/coverage_per_batch/IDF_FINAL_SUMMARY fuer den NEUEN Batch — ABER die kanonische
DF_BATCH_STATE.batch_items_per_batch blieb STALE (voriger Round, alle completed). Folge: SDF
resumed (--resume/STAB10-Auto-Resume) aber findet KEINEN pending Batch -> laeuft leer durch
(stiller No-Op) obwohl IDF einen Batch geplant hat.

**Fix:** IDF_FINAL_SUMMARY.recommended_next ist die AUTORITATIVE IDF-Ausgabe. Wenn
batch_items_per_batch keinen non-completed Batch liefert ABER recommended_next einen geplanten
Batch hat -> materialisiere batch_items_per_batch + batch_stages + batch_items aus
IDF_FINAL_SUMMARY.batches (self-heal, kein Re-IDF-Run noetig). INV-MODUS-1 bleibt gewahrt: KEIN
modus/batch_modes geschrieben (das macht C3).

---

## VEHIKEL-GATE (BL-373): der Motor-Aufruf ist NIE unbedingt

Bug vor BL-373: jeder Multi-Sub-Batch-BL (per_batch != null) lief ZWANGS in den
dispatch_implement-Motor — VERBOTEN vor Gate-D (CLAUDE.md BL-222/BL-330,
feedback_motor_erst_nach_stabilisierung). Fix: zwei unabhaengige, default-sichere Bedingungen —
beide muessen halten, damit der Motor laeuft.

1. **gate_d_passed** — TEMPORALER Stabilitaets-Lock (session-param motor_production_ready, default
   false → vor Gate-D IMMER off). Der Motor ist strukturell deterministisch (workflow_zones:
   dispatch_implement=green), aber erst NACH Gate-D produktions-VERTRAUT.
2. **Vehikel-Router** (BL-330, INV-VEHIKEL-1) — waehlt der Dial ueberhaupt ein Workflow-Vehikel?
   vehicle_for(dispatch_implement, workflow) → "workflow" nur bei normal/fast, sonst "worker".

`motor_allowed = gate_d_passed AND (motor_vehicle == "workflow")`.

---

## Motor-Pfad vs altmodischer Pfad

**Single-Batch auch durch den Motor (User-Insight + Workflow-Feature-Synthese):** der
Single-Mode-Pfad (ELSE) ist das ALTE Puppet-Master-Muster — der Team Lead laedt Berater
nacheinander in SEINEN Kontext (architecturalBrief -> patternBrief -> modusEntscheidung ->
_I_orchestrate{teamSetup -> kurzlebigPrompt -> teamLeadSteuerung -> blueprintLoop}) =>
Lead-Context-Bloat ueber jeden Auto-Compact. Der Motor (dispatch_implement = nativer
Claude-Code-Workflow) haelt den Loop IM SKRIPT, jeder Berater/Step ist ein agent() (Sub-Agent,
Output -> Skript-Variable NICHT Lead-Fenster) -> Lead bleibt schlank, nur loop_decision kehrt
zurueck. -> Jeder non-null per_batch (auch 1 Sub-Batch) laeuft durch den Motor. Single-Mode (ELSE)
bleibt NUR fuer per_batch==null (gar kein Batch-Plan).

**ALTMODISCHER Multi-Sub-Batch-Pfad (Lead-driven, KEIN Motor) — BL-373:** RE-ENTRANT via
INV-MODUS-7 SKILL-HANDSCHUH-Pfad — NICHT ein FOR-Loop, NICHT inline-loop_decision (das waere
DOPPEL-ANTRIEB: _SDF_orchestrate_post BESITZT bereits den Stage-Loop UND das RE-BATCH-Re-Entry).
Der Lead dispatcht GENAU EINEN pending Sub-Batch; Resume-SKIP (completed_sub_batches) hat den Rest
gefiltert. Der dispatchte _I_/_SC_orchestrate chained als letzten Pflicht-Schritt
Skill(_SDF_orchestrate_post) (INV-HANDOVER-1). Dieser fuehrt Phase 3 (recalibrate/postItem/
statusTransition/modelSync) + Phase 3.6 stageElevation (ELEVATE → Skill(_I_orchestrate --resume
--stage=N+1), selbst-re-entrant je Stage) + Phase 4 loopDecision: BATCH_DONE + weitere pending →
RE-BATCH → Skill(_SDF_orchestrate "{NAME} --resume --next-batch"); alle durch → TERMINATE → BDF.
Bewiesenes Muster: BL-321 (A→IDF→SDF→I×2→Post×2→TERMINATE, 1 Worker=1 Step).

**FIX echte Keys (BL-228 Live-Befund, DCSRE-486 Round-18-Worker):** batch_items_per_batch ist ein
DICT {echter_key: items} — die Keys sind SEMANTISCH (SB-2/SB-3, batch_C2/batch_PL18), NICHT
batch_1/batch_2 (INV-METRIC-5: keys()==metric_per_batch.keys()). FRUEHER (Motor-Refactor-Regression):
enumerate(per_batch) + batch_key="batch_"+i verwarf die echten Keys → completed_sub_batches-Skip +
coverage_per_batch-/batch_stages-Lookup matchten NIE → erledigte Sub-Batches wurden neu angefasst.
Jetzt: echte Keys.

---

## INV-MODUS-6 (BL-165 D-Architektur)

Bei `batch_items_per_batch != null AND |Batches|>1` MUSS SDF als Outer-Loop laufen mit Phase
1.1+1.5+2+3.1-3.5 PRO ROUND. Ein Round = ein Sub-Batch. Phase 1.1 entscheidet PRO ROUND mit
aktuellem Vault-State (NICHT vorab als Map). Phase 3.5 modelSync persistiert Round-Erkenntnisse
zurueck zu Model.md/Spec.md bevor naechster Round startet.

> **BL-222/FIX2:** Die WHILE-Stage-Loop + stageElevation-Decision (INV-MODUS-8/9) laufen im
> Workflow-Motor `.claude/workflows/dispatch_implement.js`, NICHT mehr inline im SDF-Skill. Die
> DECISION-SEMANTIK (per-Stage ELEVATE/BATCH_DONE/RETRY/ABORT/HALT, Phase 3.x nur @BATCH_DONE)
> bleibt 1:1 erhalten — nur der Ausfuehrungs-Ort wanderte von interpretiertem Pseudocode in
> deterministisches Engine-Skript (Mega-Worker-Praevention). INV-MODUS-8/9 gelten als Anforderung
> an den Workflow.

## INV-MODUS-8 (BL-171 — WHILE statt FOR)

Bei `batch_stages != null` und mehreren Stages pro Sub-Batch MUSS Stage-Inner-Loop als
**WHILE-Loop mit Decision-Berater** laufen:
- `DF_BATCH_STATE.completed_stages_per_batch[batch_key]` trackt durchgefuehrte Stages
- Initial-Stage: erste nicht-abgeschlossene aus stages_for_batch (Resume-aware)
- Pro Iteration: Phase 2.1 dispatcher_with_stage → Skill(_SDF_berater_stageElevation)
- Decision-Branch entscheidet ELEVATE / BATCH_DONE / RETRY / ABORT / HALT
- completed_sub_batches.append(batch_key) NUR bei BATCH_DONE (nie bei ABORT/HALT)
- completed_stages_per_batch DARF NICHT bei Resume reset werden (`??=` Operator)
- Audit-Slot `BERATER_OUTPUTS.executionDispatch.dispatches[]` enthaelt `stage`+`tdd_flag`-Felder
- Audit-Slot `BERATER_OUTPUTS.stageElevation` enthaelt next_action+next_stage+rationale

Beweis: naive FOR-Iteration (alt) ignoriert I_orchestrate-Outcome — bei FAIL/PARTIAL wuerde SDF
blind weiterfahren. WHILE+Decision-Berater (neu) prueft pro Stage und kann Retry/Abort/Halt
anstossen.

## INV-MODUS-9 (BL-171)

SDF Phase 2.2 (stageElevation) MUSS direkt nach Phase 2.1 (dispatcher_with_stage) aufgerufen
werden, BEVOR Outer-Loop die naechste Iteration startet. Berater ist reine Decision-Logik (kein
Skill()-Aufruf, INV-STAGE-ELEV-5). Outer-Loop ist alleinige Ausfuehrungs-Instanz fuer next_action.

---

## Was EINMALIG / PRO ROUND / EINMALIG-NACH

**Was EINMALIG (vor Outer-Loop):**
- Phase 0 resumeGuard
- Phase 1.0 analyse + architecturalBrief (story-weit)
- Pre-Berater (C9b)

**Was PRO ROUND (in Outer-Loop):**
- Phase 1.1 modusEntscheidung — mit current_sub_batch_items + AKTUELLEM Model/Spec
- Phase 1.5 patternBrief — pro Sub-Batch
- Phase 2.1 Dispatch — pro Sub-Batch (current_sub_batch_mode → I/SC/TDD)
- Phase 3.1 recalibrate — pro Sub-Batch (K-Score-Update)
- Phase 3.2 postBatch — pro Sub-Batch (GAP-Check)
- Phase 3.3 statusTransition — pro Sub-Batch (DONE-Markierung)
- Phase 3.5 modelSync — pro Sub-Batch (Round-Erkenntnisse → Model.md/Spec.md)

**Was EINMALIG (nach Outer-Loop):**
- Phase 3.4 Batch-Ende-Aggregat
- Phase 4 loopDecision — Story-Level (TERMINATE / RE-BATCH next STORY)

---

## loop_decision-Routing (Lead/BDF, NACH Workflow-RETURN)

- **RE-BATCH**     → Lead chaint `Skill(_SDF_orchestrate --resume)` (frische Phase 1.1 naechste Round, INV-MODUS-4/6)
- **SOFT-REPRIO**  → Lead chaint `Skill(_IDF_orchestrate, --mode=recluster)`
- **ROLLBACK**     → Lead chaint `Skill(_IDF_orchestrate, --mode=recheck)`
- **TERMINATE**    → fertig — Phase FINAL (TeamDelete, Protokoll-Rollover, Checkpoint C)

Re-Entry-Cap LEAD-seitig (`MAX_REBATCH = 5`): der Motor-outerRounds-Cap zaehlt Re-Entries NICHT.
Fail-safe: unbekanntes/leeres loop_decision → TERMINATE (NIE re-implement-Default).

## Phase 2 EXIT-POINT (BL-NEW-12 → BL-222/FIX2)

Der frueher beschriebene Caller-Self-Chain (I/SC ruft selbst `_SDF_orchestrate_post`) +
interpretierter Pre-SDF-Outer-Loop ist ERSETZT durch den deterministischen Dispatch-Motor.
Pre-SDF macht NUR noch: Phase 0 resumeGuard → Phase 1.0 analyse → pending Sub-Batches sammeln
(completed_sub_batches-SKIP, Resume) → `Workflow(name="dispatch_implement")` STARTEN → Phase 3.4
batchEnde-Aggregat → `loop_decision` auswerten. KEIN in-Skill Stage-Loop, KEIN
`Skill(_I_orchestrate)`-Inline-Call, KEIN Caller-Self-Chain.

Vorteile (BL-222 Trio-Motor):
- Mega-Worker STRUKTURELL unmoeglich (Engine erzwingt 1-Step=1-agent; kein Self-Assign, keine Step-Buendelung)
- Signal-Konsum deterministisch (kein interpretierter Lead-Loop → kein "Phase 3 vergessen")
- `completed_sub_batches`-SKIP faengt Idempotenz natuerlich ab

**INV-AUDIT-CHAIN:** audit.jsonl muss pro Round die Sequenz haben:
SKILL_LOAD(_SDF_orchestrate) → SKILL_LOAD(_I_orchestrate ODER _SC_orchestrate)
→ SKILL_LOAD(_SDF_orchestrate_post) → PHASE_3_STEP × N → POST_SDF_EXIT.
