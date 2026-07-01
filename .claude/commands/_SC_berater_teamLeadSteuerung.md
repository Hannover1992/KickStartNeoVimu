---
status: active
version: 1.0.0
created: 2026-04-26
op: ResearchCycle
phase: 3
type: berater
chain_position: middle
model_tier: ceiling
---

# /_SC_berater_teamLeadSteuerung (Phase 3 — SC Team-Lead-Steuerung)

[VERTRAG: LIEST BERATER_OUTPUTS.teamSetup + kurzlebigPrompt + modusMatrix; SCHREIBT BERATER_OUTPUTS.teamLeadSteuerung.{pipelineSequenz, zyklusEntscheidung, modeSwitchResult, continueDecision, doneDecision, abortDecision}]

---

## 3.1 Pipeline-Sequenz (Team Lead spawnt aktiv)

```
sc-{name}-W_fetch
  → sc-{name}-taskDef
    → sc-{name}-model (oder Wellen-Worker)
      → sc-{name}-observe (oder Wellen-Worker)
        → sc-{name}-modelMaintain
          → sc-{name}-qualityGate
            → sc-{name}-hypothese
              → MODUS-ABHAENGIG:
                 FULL (Default):  /_I_orchestrate {NAME} (core I-Pipeline, SYMBIOSE)
                 INLINE (-I):     sc-{name}-implement (/_SC_implement, klein)
                 REVIEW:          SKIP (kein Implement im Review-Modus)
                 ANALYSE:         SKIP (kein Implement im Analyse-Modus)
              → [OPTIONAL, FULL/INLINE] sc-{name}-pt_extract (/_PT_extract, Pattern-Kandidaten)
                (Guard: nur wenn _PT_extract.md existiert + MODUS != REVIEW + MODUS != ANALYSE)
                # Modell-Default: {middle} (mechanische Aufgabe, ceiling nicht noetig)
              → sc-{name}-ergebnis (oder Wellen-Worker)
                → sc-{name}-push_temp
                  # Modell-Default: {middle} (mechanische Aufgabe, ceiling nicht noetig)
```

**SC_PIPELINE_STATE im Manifest (aktualisieren nach jedem Agent):**
```yaml
SC_PIPELINE_STATE:
  cycle_nr: {N}
  stufe: "{aktueller-command}"
  sc_status: RUNNING
  sc_mode: "{FULL|INLINE|REVIEW|ANALYSE}"
  resume_zaehler: {command: count, ...}
  aktive_agent_ids: []
```

Pro Agent-Message:
1. Pruefe Ergebnis
2. Erfolg → naechsten Agent spawnen
3. Problem → Retry-Agent mit Korrektur-Kontext
4. Nach ergebnis → Phase 3.2
5. Nach push_temp → Phase 3.2 auswerten

---

## 3.2 Zyklus-Entscheidung (nach /_SC_ergebnis + /_W_push_temp)

→ Lies `{META}/sc/decision-tables.md` fuer die modus-spezifische Decision Table.

Team Lead wertet Signale aus Worker-Messages aus:
- SRS-Score, SRS-Trend, offene/widerlegte W{n}, Stagnation, Feature-Coverage
- Entscheidung: **CONTINUE** | **DONE** | **FORCE** | **ABORT**

### 3.2.0 ANALYSE-Modus: Saettigungs-Logik (Z5: RF-09, W241)

```
# NUR wenn sc_mode == "ANALYSE":

# Saettigungs-Check (vor normaler Decision-Table):
delta_wn_aktuell = (anzahl_W{n} - anzahl_W{n}_vorheriger_zyklus)
delta_wn_vorige  = manifest.SC_Z{N-1}_DELTA_WN  # aus letztem Zyklus (falls vorhanden)

IF delta_wn_aktuell == 0 UND delta_wn_vorige == 0:
  → sc_status = DONE_DISCOVERY_ONLY
  → Logge: "[ANALYSE] Saettigung: delta_wn==0 in 2 aufeinanderfolgenden Zyklen"
  → GOTO Phase 3.4 (DONE-Decision)

model_stability_index = manifest.SC_PIPELINE_STATE.model_stability_index  # optional
IF model_stability_index existiert UND model_stability_index >= 0.85:
  → sc_status = DONE_DISCOVERY_ONLY
  → Logge: "[ANALYSE] Saettigung: model_stability_index={model_stability_index} >= 0.85"
  → GOTO Phase 3.4 (DONE-Decision)

# Manifest: delta_wn fuer naechsten Zyklus speichern
Manifest: SC_Z{N}_DELTA_WN = delta_wn_aktuell
```

### 3.2.1 Mode-Switch-Check (Z5: RF-32, RF-35, NUR bei CONTINUE + Zyklus >= 2)

```
# Voraussetzung: Decision == CONTINUE AND cycle_nr >= 2
# (gate6_forced = true ueberschreibt die Zyklus-Bedingung)

IF decision != CONTINUE:
  → SKIP (Mode-Switch nur bei CONTINUE relevant)

IF cycle_nr < 2 AND NOT gate6_forced:
  → SKIP (Gate 6 erst ab Zyklus 2 aktiv, ausser --symbiose erzwingt es)

IF gate6_skip == true:
  → SKIP (--full-symbiose: Gate 6 nicht ausgefuehrt)

# RF-09 Idempotenz-Guard (AK-M5): Verhindert Doppel-Switch
# NE-1: sc_mode kann FULL (Z983) oder FULL_SYMBIOSE (Z984) sein
Lies Manifest: SC_PIPELINE_STATE.sc_mode → CURRENT_SC_MODE
IF CURRENT_SC_MODE IN ["FULL_SYMBIOSE", "FULL"]:
  LOG: "[MODE-SWITCH] IDEMPOTENZ: sc_mode={CURRENT_SC_MODE} — bereits maximal, kein Switch"
  → GOTO AUTO_TDD_CHECK

# RF-09: Idempotenz-Guards. Kein Doppel-Switch wenn SRS und COMPLEXITY gleichzeitig feuern.

# GUARD-1 (tdd-Idempotenz):
Lies Manifest: aggregat_auto_tdd_pending -> GUARD1_TDD_PENDING
Lies _session_params.md: tdd -> GUARD1_TDD_AKTUELL
IF GUARD1_TDD_PENDING == true AND GUARD1_TDD_AKTUELL == true:
  Manifest: aggregat_auto_tdd_pending = false
  LOG: "[RF-09] Idempotenz: tdd bereits true, Skip Auto-tdd"
  → SKIP (kein tdd-Auto-Switch noetig)

# GUARD-2 (sc_mode-Idempotenz):
Lies Manifest: aggregat_switch_recommendation -> GUARD2_AGGREGAT_REC
IF GUARD2_AGGREGAT_REC == "FULL_SYMBIOSE" AND CURRENT_SC_MODE == "FULL_SYMBIOSE":
  Manifest: aggregat_switch_recommendation = "NONE"
  LOG: "[RF-09] Idempotenz: sc_mode bereits FULL_SYMBIOSE, Skip"
  → SKIP (kein Mode-Switch noetig)

# GUARD-3 (Doppel-Signal-Idempotenz):
Lies QUALITYGATE{N}.md → gate6_recommendation_raw
IF gate6_recommendation_raw == "FULL_SYMBIOSE" AND GUARD2_AGGREGAT_REC == "FULL_SYMBIOSE" AND CURRENT_SC_MODE == "FULL_SYMBIOSE":
  LOG: "[RF-09] Idempotenz: Beide Signale aktiv, sc_mode bereits FULL_SYMBIOSE"
  → SKIP (Doppel-Signal ohne Wirkung — sc_mode bereits maximal)

# Lese mode_switch_recommendation aus QUALITYGATE{N}.md:
lies QUALITYGATE{N}.md → mode_switch_recommendation, Konfidenz

# RF-10: Dual-Source + MAX-Regel (W21). Liest BEIDE Quellen (QUALITYGATE{N}.md + Manifest).
# Hierarchie: FULL_SYMBIOSE(3) > INLINE(2) > NONE(1) — SC-2 Monotonie-Invariante
# aggregat_switch_recommendation bereits in Manifest (VERIFIZIERT, BL-142 RF-A-RENAME)
# KONSISTENZ mit 2D-Matrix (_A_orchestrate Phase 4.2):
# Matrix-Zellen Q7-Q9 (SRS>85) → SC-FULL ist korrekte Eskalation.
# Schwellen 20/60/85 identisch Gate-6 (Quelle: _SC_qualityGate.md Z247-273).
mode_switch_recommendation_gate = mode_switch_recommendation  # Quelle 1: QUALITYGATE{N}.md

# RF-10 Phase 3.2.1: Lese Quelle 2 (Manifest aggregat_switch_recommendation)
Lies Manifest: aggregat_switch_recommendation -> mode_switch_recommendation_aggregat  # Quelle 2
Lies Manifest: aggregat_auto_tdd_pending -> AGGREGAT_TDD_PENDING  # fuer Konfidenz-Berechnung

SCORE_GATE = 3 IF mode_switch_recommendation_gate == "FULL_SYMBIOSE" ELSE 2 IF mode_switch_recommendation_gate == "INLINE" ELSE 1
SCORE_AGGREGAT = 3 IF mode_switch_recommendation_aggregat == "FULL_SYMBIOSE" ELSE 2 IF mode_switch_recommendation_aggregat == "INLINE" ELSE 1

# KONFLIKT-Behandlung (W21 MAX-Regel):
IF mode_switch_recommendation_gate == "INLINE" AND mode_switch_recommendation_aggregat == "FULL_SYMBIOSE":
  effective_recommendation = "FULL_SYMBIOSE"
  mode_switch_recommendation = "FULL_SYMBIOSE"
  Konfidenz = "high"
  LOG: "[KONFLIKT] Gate-6 INLINE vs AGGREGAT FULL_SYMBIOSE → MAX-Regel → FULL_SYMBIOSE"

ELIF SCORE_AGGREGAT > SCORE_GATE:
  effective_recommendation = mode_switch_recommendation_aggregat
  mode_switch_recommendation = mode_switch_recommendation_aggregat
  # Konfidenz: "high" wenn beide Signale vorhanden und uebereinstimmen, sonst "moderate"
  Konfidenz = "high" IF (mode_switch_recommendation_gate != "NONE" AND mode_switch_recommendation_aggregat != "NONE") ELSE "moderate"
  LOG: "[RF-10] Dual-Source MAX-Regel: aggregat_rec ({mode_switch_recommendation_aggregat}) > gate_rec ({mode_switch_recommendation_gate}) — aggregat gewinnt (Konfidenz: {Konfidenz})"

ELSE:
  effective_recommendation = mode_switch_recommendation_gate
  mode_switch_recommendation = mode_switch_recommendation_gate
  # Konfidenz: "high" wenn beide Signale vorhanden (gate gewinnt, aber aggregat bestaetigt)
  Konfidenz = "high" IF (mode_switch_recommendation_aggregat != "NONE") ELSE Konfidenz  # behalte gate Konfidenz wenn aggregat NONE
  LOG: "[RF-10] Dual-Source MAX-Regel: gate_rec ({mode_switch_recommendation_gate}) >= aggregat_rec ({mode_switch_recommendation_aggregat}) — gate gewinnt (Konfidenz: {Konfidenz})"

IF mode_switch_recommendation == "NONE":
  LOG: "[MODE-SWITCH] Dual-Source: NONE — kein Wechsel, pruefe AUTO_TDD_CHECK"
  → GOTO AUTO_TDD_CHECK

# recommendation != NONE: Handlung je HiL-Modus:
IF GLOBAL_HIL == "off":
  # Auto-Switch (MANDATORY — CaseStudy PatternLibrary Z2 2026-03-18):
  # KEIN pragmatisches Override erlaubt. Wenn Gate 6 empfiehlt, wird gewechselt.
  # Hintergrund: Team Lead blieb in INLINE obwohl Gate 6 FULL empfahl,
  # weil der IC "zu klein fuer I-Pipeline" schien. User musste manuell korrigieren.
  # Der Switch betrifft die DENKWEISE (Kaskaden sehen), nicht nur den LOC-Scope.
  altes_sc_mode = SC_PIPELINE_STATE.sc_mode
  SC_PIPELINE_STATE.sc_mode = "FULL" IF mode_switch_recommendation == "FULL_SYMBIOSE" ELSE mode_switch_recommendation
  Manifest: SC_PIPELINE_STATE.sc_mode = mode_switch_recommendation
  Logge: "[MODE-SWITCH] Gate 6 MANDATORY auto-switch: {altes_sc_mode} → {mode_switch_recommendation} (Konfidenz: {Konfidenz})"
  # GUARD: Der naechste Implement-Schritt MUSS den neuen Modus verwenden.
  # INLINE→FULL: /_I_orchestrate (oder groesserer /_SC_implement Scope)
  # FULL→INLINE: /_SC_implement (kleinerer Scope)
  # KEIN Zurueckfallen auf alten Modus "weil der IC klein ist" (Anti-Pattern).

ELIF GLOBAL_HIL IN ["cycle", "phase"]:
  # HiL-Prompt:
  HiL:
    "Gate 6 empfiehlt Mode-Switch: {mode_switch_recommendation} (Konfidenz: {Konfidenz})
     Aktueller Modus: {SC_PIPELINE_STATE.sc_mode}
     [WECHSELN zu {mode_switch_recommendation}]
     [BLEIBEN bei {SC_PIPELINE_STATE.sc_mode}]
     [MANUELL waehlen: FULL | INLINE]"
  → Bei WECHSELN: SC_PIPELINE_STATE.sc_mode = mode_switch_recommendation (Manifest update)
  → Bei BLEIBEN: SKIP (kein Wechsel)
  → Bei MANUELL: User-Eingabe, dann Manifest update

ELSE:  # hil=manual
  → Logge: "Mode-Switch-Recommendation: {mode_switch_recommendation} — Konfidenz: {Konfidenz} (hil=manual, kein Auto-Handling)"
  → Empfehlung nachlesbar in QUALITYGATE{N}.md
```

### AUTO_TDD_CHECK (RF-05, AK-M4-3)

```pseudocode
# GOTO-Target fuer: RF-AM-003 Idempotenz-Guard (Z980) + RF-AM-004 Block B (NONE-Fall)
# GLOBAL_HIL ist hier im Scope (Schritt 1.1c liest es) — kein Re-Read noetig
Lies Manifest: aggregat_auto_tdd_pending -> AUTO_TDD_PENDING
IF AUTO_TDD_PENDING != true:
  → SKIP (kein Auto-tdd pending)

Lies _session_params.md: tdd -> TDD_AKTUELL
IF TDD_AKTUELL == true:
  Manifest: aggregat_auto_tdd_pending = false
  LOG: "[RF-05] AUTO-TDD pending geloescht (tdd bereits true — INV-4 gewahrt)"
  → SKIP

IF GLOBAL_HIL == "off":
  _session_params.md: tdd = true
  Manifest: aggregat_auto_tdd_pending = false
  LOG: "[RF-05] AUTO-TDD aktiviert (hil=off, Phase 3.2.1 — puppet_master)"
ELIF GLOBAL_HIL IN ["cycle", "phase"]:
  HiL: "AUTO-TDD: AGGREGAT=HIGH empfiehlt tdd=true.
        [AKTIVIEREN] → tdd=true, pending=false
        [IGNORIEREN] → pending=false, tdd_user_locked=true"
  → AKTIVIEREN: _session_params.md: tdd = true; Manifest: aggregat_auto_tdd_pending = false
  → IGNORIEREN: Manifest: aggregat_auto_tdd_pending = false; _session_params.md: tdd_user_locked = true
ELSE:  # hil=manual
  LOG: "[RF-05] AUTO-TDD pending vorhanden (hil=manual, kein Auto-Switch)"
  # Pending bleibt — naechster Zyklus prueft erneut
```

---

## 3.2a SYMBIOSE (Task 7, NUR FULL-Modus) — SDF-HUB Redesign

→ Lies `{META}/sc/symbiose-protocol.md` fuer vollstaendiges Protokoll.
→ **NEU (CaseStudy DCSRE-1430):** SC ruft I NICHT mehr direkt auf.
→ SC setzt SC_NEEDS_IMPL → EXIT → SDF routet I → (TDD) → SC --resume-at=ergebnis.

### Phase 1 — SC setzt SDF-HUB Signal (CaseStudy DCSRE-1430)

```
# SC Phase 1 wird NICHT mehr hier ausgefuehrt — der Implement-Step in der
# Puppet-Master-Loop (Schritt 5) setzt SC_NEEDS_IMPL und gibt an SDF zurueck.
# SDF uebernimmt: I_orchestrate → (TDD_orchestrate) → SC --resume-at=ergebnis.
#
# VERALTET (Pre-DCSRE-1430):
#   SC rief /_I_orchestrate direkt auf (Agent-Spawn oder Skill)
#   → Verletzt SDF-HUB Invariante: "SDF ist IMMER dazwischen"
#   → Verletzt Puppet-Master: Agent() statt Skill() (CaseStudy Zeile 1067)
#
# NEU: SC Schritt 5 schreibt ins Manifest:
#   SC_PIPELINE_STATE.stufe = "SC_NEEDS_IMPL"
#   SC_PIPELINE_STATE.sc_impl_request = {mode, cycle_nr, hypothese_ref}
#   → EXIT (SC pausiert)
#
# SDF Schritt 2.2a liest SC_NEEDS_IMPL und fuehrt aus:
#   1. Skill(_I_orchestrate) → I setzt SC_SYMBIOSE_I_DONE + i_core_result
#   2. (Optional) TDD-Stufen via Skill(_TDD_orchestrate) pro Stufe
#   3. Skill(_SC_orchestrate --resume-at=ergebnis) → SC sammelt Ergebnis
```

### Phase 3 — SC nach I-Rueckkehr (Post-I) (Z3: RF-18)

```
1. manifest.reload()
2. IF pipeline_mode != SC_SYMBIOSE_I_DONE:
   # (Z3: RF-22) Deadlock-Prevention: Timeout-Check
   IF symbiose_start_time gesetzt UND (jetzt - symbiose_start_time) > 4h:
     Logge WARNUNG: "SYMBIOSE-Timeout: I-Pipeline antwortet nicht seit {elapsed}h."
     Manifest: pipeline_mode = SC_SYMBIOSE_I_ABORTED
     SC_I_LIFECYCLE.transition_log APPEND:
       from_mode: SC_SYMBIOSE_I_ACTIVE
       to_mode: SC_SYMBIOSE_I_ABORTED
       timestamp: {jetzt ISO8601}
       reason: "Timeout: I antwortet nicht seit {elapsed}h"
     # Weiter mit ergebnis im Abort-Modus (i_core_result leer/null)
     i_core_result = null
     GOTO Phase3_ergebnis
   ELSE:
     Logge WARNUNG: "pipeline_mode != SC_SYMBIOSE_I_DONE. I noch aktiv oder Fehler."
     → WARTEN (HiL-Hinweis: "[WARTEN — I laeuft noch] [ABBRUCH]")

3. Lies i_core_result aus Manifest
4. Manifest: pipeline_mode = SC (zurueck)
5. SC_I_LIFECYCLE.transition_log APPEND:
     from_mode: SC_SYMBIOSE_I_DONE
     to_mode: SC
     timestamp: {jetzt ISO8601}
     reason: "I core abgeschlossen, SC prueft i_core_result"

# (Z3: RF-18) Pruefe i_core_result Felder
6. verify_status = i_core_result.verify_status
   scope_mode = i_core_result.scope_mode       # Erwartet: "full" (BL-054)
   completed_at = i_core_result.completed_at
   Logge: "I-Rueckkehr: verify={verify_status}, scope={scope_mode}, abgeschlossen={completed_at}"

# (Z3: RF-21) GAP-Gate Guards — VOR ergebnis spawnen
LABEL Phase3_ergebnis:
7. IF i_core_result != null AND i_core_result.model_maintain_required == true:
     Logge: "[GAP-Gate] model_maintain_required=true → spawne /_SC_modelMaintain VOR ergebnis"
     Spawne sc-{NAME}-model-maintain (SEQUENTIELL — BlockedBy: Task 7)
     Warte auf Completion

8. IF i_core_result != null AND i_core_result.gap_required == true:
     Logge: "[GAP-Gate] gap_required=true → spawne /_gap VOR ergebnis"
     Spawne sc-{NAME}-gap (SEQUENTIELL — BlockedBy: model-maintain falls vorhanden)
     Warte auf Completion

# --- Schritt 8a: next_cycle_context (Z3: P2, RF-08, W36-Fix) ---
# IMMER geschrieben — auch ohne VETO (RF-08: "IMMER next_cycle_context schreiben")
8a. IF i_core_result != null:
     unimplemented = [Slices die NICHT in i_core_result.slices_completed]
     SC_PIPELINE_STATE.next_cycle_context = {
       verify_status: i_core_result.verify_status,
       unimplemented_slices: unimplemented,
       next_focus_override: i_core_result.sc_recommendations.next_focus (falls triggered),
       i_loc_delta: i_core_result.LOC,
       sc_recommendations_triggered: i_core_result.sc_recommendations.triggered,
       pre_filter_veto: false,          # wird von PRE-FILTER aktualisiert
       pre_filter_reason: []            # wird von PRE-FILTER aktualisiert
     }
     Logge: "[next_cycle_context] Geschrieben: verify={verify_status}, unimpl={len(unimplemented)}"

# --- PRE-FILTER (Z3: P2, RF-04..RF-07, W35-Fix) ---
# Prueft 3 Felder aus i_core_result VOR Decision-Table.
# TC-2 Compliance: Decision-Table wird NICHT direkt geaendert.
8b. IF i_core_result != null:
     VETO = false
     VETO_REASONS = []

     # RF-04: verify_status Check
     IF i_core_result.verify_status == "failed":
       VETO = true
       VETO_REASONS += "verify_status=failed"
       Logge: "[PRE-FILTER] verify_status=failed → VETO gegen DONE"

     # RF-06: Slice-Coverage (symbiose-protocol.md: >30% failed = Trigger)
     ELIF i_core_result.verify_status == "partial":
       failed_count = i_core_result.slices - len(i_core_result.slices_completed)
       IF i_core_result.slices > 0 AND (failed_count / i_core_result.slices) > 0.30:
         VETO = true
         VETO_REASONS += "verify_status=partial, {failed_count}/{slices} > 30% unvollstaendig"
         Logge: "[PRE-FILTER] Slice-Coverage < 70% → VETO gegen DONE"

     # RF-05: sc_recommendations.triggered
     IF i_core_result.sc_recommendations.triggered == true:
       VETO = true
       VETO_REASONS += "sc_recommendations.triggered=true: {sc_recommendations.reason}"
       Logge: "[PRE-FILTER] sc_recommendations.triggered → VETO gegen DONE"

     # RF-07: VETO-Aufloesung bei Stagnation (Anti-Endlosschleifen-Guard)
     IF VETO == true:
       IF manifest.stagnation_index >= 5.0:
         Logge: "[PRE-FILTER] VETO aufgehoben: Stagnation={stagnation_index} >= 5.0"
         VETO = false
         VETO_REASONS += "VETO aufgehoben: Stagnation >= 5.0"
       ELIF manifest.cycle_nr >= max_cycles[difficulty]:
         Logge: "[PRE-FILTER] VETO aufgehoben: Max-Zyklen erreicht"
         VETO = false
         VETO_REASONS += "VETO aufgehoben: max_cycles erreicht"

     # Manifest schreiben
     SC_PIPELINE_STATE.pre_filter_veto = VETO
     SC_PIPELINE_STATE.pre_filter_reason = VETO_REASONS
     # next_cycle_context aktualisieren mit PRE-FILTER-Ergebnis
     SC_PIPELINE_STATE.next_cycle_context.pre_filter_veto = VETO
     SC_PIPELINE_STATE.next_cycle_context.pre_filter_reason = VETO_REASONS

     # Kontrollflusswirkung
     IF VETO == true:
       Logge: "[PRE-FILTER] FORCE_CONTINUE — Decision-Table SKIP"
       → Ueberspringe Schritt 9 (/_SC_ergebnis)
       → Direkt zu Phase 3.3 (CONTINUE-Decision) mit FORCE_CONTINUE-Markierung
       GOTO Phase3_continue

# Invariante: /_finish DARF ERST nach aktuellem /_gap-Ergebnis ausgefuehrt werden.

9. Spawne /_SC_ergebnis (Task 8) — Ergebnis-Agent liest i_core_result
```

---

## 3.3 Bei CONTINUE-Decision

**[NEU: Sub-Schritt 3.3.0 — State-Lifecycle-Rollover (Pattern B, W3)]**

Vor dem Erstellen neuer Zyklus-Tasks: SC_Z{N-2}_* aus State ins Protokoll rotieren.

```
N = aktuelle Zyklus-Nummer (laufender Zyklus)
Falls SC_Z{N-2}_QUALITYGATE oder SC_Z{N-2}_ERGEBNIS im {WORKING_DIR}/_manifest.md State vorhanden:

  Schritt 3.3.0a — Protokoll-Write (ZUERST):
  Prepend an _manifest_protokoll.md (W18 — Prepend-Mechanismus):
    1. Frontmatter aktualisieren: last_append={Datum}, append_count++
    2. Eintrag prependen (nach YAML-Frontmatter-Block + Leerzeile):
       ## SC Zyklus Z{N-2} Archiv [{Datum}]
       SC_Z{N-2}_QUALITYGATE: {Wert}
       SC_Z{N-2}_ERGEBNIS: {Wert}
       SC_Z{N-2}_ENTSCHEIDUNG: {Wert}
       SC_HYPOTHESE_Z{N-2}: {YAML-Block vollstaendig}

  Schritt 3.3.0b — State-Cleanup (DANACH):
  Entferne aus {WORKING_DIR}/_manifest.md:
    SC_Z{N-2}_QUALITYGATE, SC_Z{N-2}_ERGEBNIS, SC_Z{N-2}_ENTSCHEIDUNG, SC_HYPOTHESE_Z{N-2}

  Behalte in {WORKING_DIR}/_manifest.md:
    SC_Z{N-1}_* (letzter abgeschlossener Zyklus — State, W3)
    SC_Z{N}_* (laufender Zyklus — State, W3)

Falls kein SC_Z{N-2}_* vorhanden: Sub-Schritt 3.3.0 SKIP (Zyklus 1 oder bereits rotiert)
```

**POST-CYCLE sc_i_gate Rollover (Pattern C, bei POST-CYCLE Schritt 2):**

Nach I-Pipeline-Abschluss — sc_i_gate YAML-Block ins Protokoll rotieren:

```
Schritt P1: Prepend an _manifest_protokoll.md:
  1. Frontmatter: last_append={Datum}, append_count++
  2. Eintrag prependen:
     ## sc_i_gate [{Datum}]
     [Vollstaendiger sc_i_gate YAML-Block: status, criteria_met, tier-Felder, justification]

Schritt P2: State-Update {WORKING_DIR}/_manifest.md:
  i_gate_response: {ERGEBNIS-Einzeiler} (Pattern A — nur Einzeiler)
  [sc_i_gate YAML-Block ENTFERNEN aus State]
```

1. **Pruefe Max-Zyklen** (modus-abhaengig, siehe decision-tables.md)
   - Ueberschritten? → FORCE statt CONTINUE

2. **Erstelle neue CYCLE Tasks** (T3-T9 fuer naechste Iteration)
   → Lies `{META}/sc/task-templates.md` fuer Task-Beschreibungen.
   - _SC_observe und _SC_ergebnis als Wellen-Tasks (normal/hard)
   - Pattern: 9-5-1 / 5-3-1 / 1 (identisch zu _model)

3. **Starte naechsten Zyklus:**
   ```
   Spawne sc-{name}-observe: "CONTINUE: Neuer Zyklus {C+1}."
   ```

TaskCreate: "Quality Gates pruefen (Zyklus {C+1})"
  blocked_by: (modelMaintain Task)

TaskCreate: "Hypothese formulieren (Zyklus {C+1})"
  blocked_by: (qualityGate Task)

TaskCreate: "Implementieren (Zyklus {C+1})"
  description: "FULL: /_I_orchestrate {NAME} (core I-Pipeline, SYMBIOSE-Protokoll).
    INLINE (-I): /_SC_implement ausfuehren (klein, 1 IC).
    REVIEW: SKIP (kein Implement im Review-Modus).
    ANALYSE: SKIP (kein Implement im Analyse-Modus).
    Team Lead entscheidet anhand SC_PIPELINE_STATE.sc_mode.
    FULL-Protokoll: pipeline_mode=SC_SYMBIOSE_I_ACTIVE VOR I-Aufruf setzen,
    nach I-Rueckkehr i_core_result lesen und pipeline_mode=SC zuruecksetzen."
  blocked_by: (hypothese Task)

TaskCreate: "Pattern extrahieren (optional, Zyklus {C+1})" [NUR wenn Guards erfuellt]
  description: "/_PT_extract {NAME} ausfuehren (OPTIONAL).
    Prueft ob Implement-Ergebnis neue Pattern-Kandidaten enthaelt.
    Guard: Nur bei FULL/INLINE, nur wenn _PT_extract.md existiert.
    Output: _pattern-library.md Update (neue Kandidaten) oder SKIP."
  blocked_by: (implement Task)

TaskCreate: "Ergebnis sammeln (Zyklus {C+1})"
  blocked_by: (pt_extract Task oder implement Task)

TaskCreate: "Wissen temporaer pushen (Zyklus {C+1})"
  blocked_by: (ergebnis Task)

---

## 3.3a Prozessbegleitende W_sync_orchestrate Trigger (NEU v2.0)

Nach bestimmten Tasks spawnt der Team Lead einen **parallelen easy-Sync Worker**,
OHNE den Haupt-Worker zu unterbrechen.

**Trigger-Punkte im SC-CYCLE:**

| Nach Task | Sync-Schwierigkeit | Was wird gesynct | Wann | --co-work |
|-----------|-------------------|-----------------|------|-----------|
| T4 (modelMaintain) | easy | models/{NAME}_Model.md | Jeder Zyklus | Kein --co-work |
| T8 (ergebnis) | easy/normal --co-work | ERGEBNIS + OBSERVE + QUALITYGATE + HYPOTHESEN | Jeder Zyklus | Mit --co-work (Zyklus-Abschluss) |
| T9 (W_push_temp) | easy | wissen/*.md | Jeder Zyklus | Kein --co-work |

**Parallel-Worker-Pattern:**

```
1. Team Lead erkennt Task-Completion (modelMaintain, ergebnis, W_push_temp)
2. Team Lead entscheidet: Sync sinnvoll? (z.B. nach modelMaintain wenn Model signifikant geaendert)
3. Team Lead spawnt Sync-Agent:
   Task tool: sc-{name}-syncOrchestrate
     "W_sync_orchestrate {NAME} easy [--co-work wenn nach ergebnis]: Sync nach {TASK}."
   ODER TaskCreate mit nicht-blockierendem Task.
4. Sync-Agent laeuft PARALLEL zum aktuellen Pipeline-Agent (nicht-blockierend)
5. Worker meldet Ergebnis, Team Lead protokolliert

CONSTRAINT (WellenRedesign R8+R9):
  - Auch easy spawnt 1 Worker (Team Lead fuehrt Sync NICHT selbst aus)
  - Team Lead steuert DIREKT (kein Worker spawnt weitere Worker)

CEILING-VERERBUNG:
  - Sync-Schwierigkeit = min(Parent-Schwierigkeit, requested)
  - Easy SC-Zyklus → maximal easy Sync
  - Normal SC-Zyklus → maximal normal Sync
  - Hard SC-Zyklus → maximal hard Sync (aber prozessbegleitend bleibt easy/normal)
```

**Hinweis:** T13 (POST-CYCLE) bleibt als **hard** Sync fuer vollstaendigen Feature-Ende-Sync.
Prozessbegleitende Triggers sind **zusaetzlich** zu T13, nicht als Ersatz.

### 3.3a-P3: ObsidianSync Graph-Kanten Trigger (nach ergebnis)

```
# P3 Trigger: ObsidianSync Graph-Kanten (Anchor-Nodes + Co-Working)
# Fehler-Isolation: Sync-Fehler blockiert NIEMALS den Parent-Prozess
TRY:
  Spawne Worker: /_W_sync_orchestrate {FEATURE} normal --co-work
CATCH:
  WARN: "P3 Sync-Trigger fehlgeschlagen. Weiter ohne Sync."
```

### 3.3b Archive-Hook: Explorer/Drafter archivieren (CaseStudy MV-2c, v3.1+)

**WANN:** Nach OBSERVE-Worker Abschluss (synthese/{NAME}-OBSERVE{N}.md existiert mit status:final), VOR modelMaintain-Spawn.
**WER:** Team Lead direkt (reine Datei-Operationen).

```
OBSERVE_FILE = synthese/{NAME}-OBSERVE{cycle_nr}.md
IF NOT exists(OBSERVE_FILE) OR frontmatter.status != "final":
  → SKIP (OBSERVE noch nicht abgeschlossen)

# Archivierungs-Ziel
ARCHIVE_DIR = ".claude/analysis/archive/{NAME}/observe{cycle_nr}/"
mkdir -p ARCHIVE_DIR

# Explorer archivieren
EXPLORER_FILES = Glob("exploration/{NAME}-E*.md") + Glob("exploration/{NAME}-observe{cycle_nr}-E*.md")
# Drafter archivieren (SC-Phase Pattern)
DRAFTER_FILES = Glob("drafts/{NAME}-observe{cycle_nr}-D*.md") + Glob("drafts/{NAME}-D*.md")

ALL_FILES = EXPLORER_FILES + DRAFTER_FILES

# Feature-Prefix-Isolation: NUR {NAME}-* Dateien (SV-2 Guard)
ALL_FILES = ALL_FILES.filter(f => f.startsWith("{NAME}-"))

IF COUNT(ALL_FILES) == 0:
  → SKIP (nichts zu archivieren)

IF COUNT(ALL_FILES) > 50:
  → HiL: "{COUNT} Dateien fuer Archivierung. Fortfahren? (j/n)"

# SCHUTZ: Synthese-Dateien NIEMALS archivieren
ALL_FILES = ALL_FILES.filter(f => f NOT in synthese/)

Fuer jede DATEI in ALL_FILES:
  mv DATEI → ARCHIVE_DIR/

Log: "Archive-Hook: {COUNT} Dateien → {ARCHIVE_DIR}"

Manifest: cleanup_log APPEND: "observe{cycle_nr}: {COUNT} Dateien archiviert nach {ARCHIVE_DIR}"
```

---

## 3.4 Bei DONE/FORCE-Decision

**Manifest aktualisieren:**
```
PHASE: DONE
DONE_TIMESTAMP: {ISO_DATETIME}
sc_status: DONE  (oder DONE_DISCOVERY_ONLY bei ANALYSE-Modus)
```

**ANALYSE-DONE HiL-Prompt (Z5: RF-10, NUR wenn sc_status == DONE_DISCOVERY_ONLY):**
```
# (Z5: RF-10) Nach DONE_DISCOVERY_ONLY: Modi-spezifischer HiL-Prompt
IF sc_status == "DONE_DISCOVERY_ONLY":
  HiL:
    "{NAME} — ANALYSE-Zyklus abgeschlossen (DONE_DISCOVERY_ONLY).
     Erkenntnisse gesichert. Naechster Schritt?

     [INLINE]   Neuer SC-Zyklus mit -I (Implementierung via /_SC_implement)
     [SYMBIOSE] Neuer SC-Zyklus als FULL SYMBIOSE (/_I_orchestrate core)
     [FERTIG]   Keine weitere Implementierung. Feature als Analyse-Done markieren."
  → Bei INLINE:   Manifest sc_mode = INLINE, neuer Zyklus starten
  → Bei SYMBIOSE: Manifest sc_mode = FULL, neuer Zyklus starten
  → Bei FERTIG:   Weiter mit POST-CYCLE (normaler DONE-Pfad)
```

**POST-CYCLE Schritt 0: Modus-Transition**
→ Lies `{META}/sc/sc-i-gate.md` fuer pipeline_mode Transition.
```
pipeline_mode: POST_CYCLE
SC_I_LIFECYCLE.current_mode: POST_CYCLE
```

**POST-CYCLE Schritt 1: HandOff generieren (Team Lead direkt, W99)**
→ Lies `{META}/sc/handoff-template.md` fuer Template.
→ Schreibe `{VAULT}/Backlog/{BL_SLUG}/SC/{NAME}-HANDOFF.md` (BL-151 + PL-D Decision 2026-05-07; vorher: .claude/analysis/synthese/)

**POST-CYCLE Schritt 2: sc_i_gate schreiben**
→ Lies `{META}/sc/sc-i-gate.md` fuer Gate-Block + Kriterien.

**POST-CYCLE Schritt 3: Post-Cycle Tasks erstellen + spawnen**
→ Lies `{META}/sc/task-templates.md` (Task 11).

```
# T10: _W_push_orchestrate — OBSOLET (BL-050 Vault-First DirectWrite)
# Vault-Sync erfolgt direkt in Synthese-Commands (DirectWrite).
# _W_push_orchestrate wird nicht mehr gespawnt. (wpush=SKIPPED_OBSOLET)
T11: /_finish {NAME}
```

**POST-CYCLE Schritt 4: Finale Verifikation (nach T10+T11 fertig)**
→ Lies `{META}/sc/sc-i-gate.md` fuer sc_i_gate_check() 3-Tier Verifikation.
→ Bei PASS: pipeline_mode = READY_FOR_I

**POST-CYCLE Schritt 5: PT-Signal (NON-BLOCKING)**

```
Guard:
  IF .claude/patterns/ EXISTIERT UND .claude/wissen/pattern-usage.log EXISTIERT:
    → PT-Signal durchfuehren (Schritt 5 aktiv)
  ELSE:
    → SKIP: "Pattern Library nicht initialisiert — PT-Signal uebersprungen."
    → pipeline_mode = READY_FOR_I (unveraenderter Pfad, Schritt 4 hat gesetzt)

Aktion (Team Lead direkt, kein Agent):
  1. Lies .claude/wissen/pattern-usage.log
     Filtere: Eintraege mit DATUM >= feature_start (aus Manifest SC_PIPELINE_STATE.start_date)
     Filtere: Nur DRAFT-Status-Eintraege (Spalte 5 = "DRAFT")

  2. Zaehle:
     draft_count    = Anzahl DRAFT-Eintraege seit feature_start
     promoted_count = Anzahl PROMOTED-Eintraege seit feature_start

  3. Schreibe Manifest-Feld:
     pt_feature_summary: "{draft_count} DRAFTs, {promoted_count} PROMOTED (Feature: {NAME})"

  4. IF draft_count > 0:
       → Log: "PT: {draft_count} DRAFT-Pattern vorhanden → /_PT_update empfohlen fuer PROMOTION"
       # Kein AskUserQuestion, kein Blocking — nur Manifest-Eintrag
     ELSE:
       → pt_feature_summary: "0 DRAFTs, 0 PROMOTED (Feature: {NAME}) — keine Pattern-Aktivitaet"

  5. READY_FOR_I: UNVERAENDERTER Pfad
     → pipeline_mode = READY_FOR_I (bleibt — Schritt 4 hat bereits gesetzt)
     → Schritt 5 fuegt INFO hinzu, blockiert NICHTS
```

---

## 3.5 Bei ABORT-Decision

```
1. /_retrospektive mit ABORT-Modus (Meta-Analyse, KEIN /_model finish)
2. Optional: /_W_push_temp als Sicherung
```

---

## 3.6 Nach Retrospektive: HiL-Pause

```
AskUserQuestion:
  "{NAME} — Forschungszyklus abgeschlossen.
   Zyklen: {C}, Decision: {DONE|FORCE|ABORT}
   SRS: {srs}, W{n}: {confirmed} BEST/{refuted} WIDERL/{open} OFFEN
   GAP: {gap}%

   Optionen: ACCEPT / RETRY / PIVOT / ABORT"
```

---

## 3.7 User-Decision verarbeiten

**ACCEPT:**
- TeamDelete, Manifest: feature_status=ACCEPTED
- Melde: "Feature fertig. Model: {path}, Wissen: RAG"

**RETRY:**
- Frage nach Feedback (Freitext)
- Neue Tasks ab /_SC_observe (NICHT ab W_fetch)
- Zurueck zu Phase 3.1

**PIVOT:**
- Frage nach neuem Fokus
- Neue Tasks ab /_taskDefinition mit neuem Fokus
- Altes Model als Basis behalten

**ABORT:**
- /_W_push_temp (Wissen sichern)
- TeamDelete, Manifest: phase=ABORTED

---

## INVARIANTEN

- I-1: Team Lead spawnt JEDEN Agent via Task-Tool (nie direkt via Skill in Loop)
- I-2: SC_PIPELINE_STATE nach jedem Agent-Abschluss ins Manifest schreiben
- I-3: Mode-Switch ist MANDATORY bei hil=off (kein pragmatisches Override)
- I-4: tdd-Flag darf nur via AUTO_TDD_CHECK gesetzt werden (nie direkt)
- I-5: Synthese-Dateien NIEMALS in Archive-Hook verschieben
- I-6: PRE-FILTER VETO setzt FORCE_CONTINUE ohne Decision-Table-Aenderung (TC-2)
- I-7: SC ruft I NICHT direkt auf — immer via SDF-HUB (DCSRE-1430)
- I-8: SYMBIOSE-Timeout nach 4h → SC_SYMBIOSE_I_ABORTED (RF-22)
