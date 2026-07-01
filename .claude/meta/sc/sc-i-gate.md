# SC-I Gate Protokoll (EC-1, EC-4, EC-5, W180, W202)

**Quelle:** Extrahiert aus `_SC_orchestrate.md` v2.4 → v3.0 (Decomposition)
**Geladen von:** Team Lead in Phase 3.4 (DONE/FORCE) und 3.4b (Finale Verifikation)

---

## SC-I Handoff-Gate (v2.2+, I-31)

**Zweck:** Formalisiert die SC-QUELL-Verantwortung fuer sc_status.
Bevor die I-Pipeline gestartet wird, MUSS SC pruefen ob der Zyklus
abgeschlossen ist und den passenden sc_status setzen.

**Gate-Logik (SC-Orchestrator prueft VOR I-Pipeline-Start):**

| sc_status (aktuell) | Bedeutung | Gate-Entscheidung |
|----------------------|-----------|-------------------|
| `DONE` | SC-Zyklus vollstaendig abgeschlossen | I-Pipeline starten |
| `DONE_DISCOVERY_ONLY` | Discovery fertig, Implementation nicht spezifiziert | I-Pipeline starten |
| `RUNNING` | SC-Zyklus laeuft noch | HiL: "SC noch aktiv. Warten oder parallel starten?" |
| `BLOCKED` | SC blockiert (externer Blocker) | STOPP: Blocker zuerst loesen |
| (kein Feld) | Kein SC-Kontext vorhanden | Normal weiter (I-Pipeline ohne SC-Vorzyklus) |

**Referenz:** `_I_orchestrate` Schritt 0.2a liest diesen sc_status (EMPFAENGER-Pruefung).
SC setzt den Wert, I liest ihn. Bidirektionale Konsistenz (W202).

---

## POST-CYCLE Schritt 0: Modus-Transition (EC-4, W180-E)

```
Schreibe ins Manifest VOR HANDOFF-Generierung:
  pipeline_mode: POST_CYCLE

  SC_I_LIFECYCLE.current_mode: POST_CYCLE
  SC_I_LIFECYCLE.transition_log APPEND:
    from_mode: SC
    to_mode: POST_CYCLE
    timestamp: {jetzt ISO8601}
    reason: "SC-Zyklus abgeschlossen ({Decision}: DONE|FORCE), POST-CYCLE gestartet"
    agent: "sc-orchestrate-agent"

ZWECK: I-Orchestrator Schritt 0.2a liest pipeline_mode.
  POST_CYCLE → I-Start ABGELEHNT (POST-CYCLE noch aktiv).
  Erst nach Finaler Verifikation → pipeline_mode: READY_FOR_I.
```

---

## POST-CYCLE Schritt 1: sc_i_gate schreiben (EC-5, EC-1, W180-C)

```
Schreibe sc_i_gate Block ins Manifest (NACH HANDOFF-Generierung, VOR _W_push):

sc_i_gate:
  status: pending                     # → wird in Finale Verifikation auf approved/rejected gesetzt
  criteria_met: []                    # → Checkliste: wird in sc_i_gate_check() gefuellt
  criteria_pending:                   # 3-Tier Checkliste (C1-C7):
    - "C1: srs_under_70"              # TIER-1 BLOCKING: SRS < 70
    - "C2: critical_wn_coverage_85"   # TIER-1 BLOCKING: >= 85% BESTAETIGT
    - "C3: w51_w56_confirmed"         # TIER-1 BLOCKING: Beide BESTAETIGT
    - "C4: ec_done_2_of_3"            # TIER-2 (EC-1, EC-2, EC-5 >= 2/3)
    - "C5: stagnation_under_075"      # TIER-2
    - "C6: handoff_valid_4_sections"  # TIER-2 (mind. 4 Pflicht-Sektionen)
    - "C7: hil_signature"             # TIER-3 (HiL-Bestaetigung, approved_by)
  tier_1_passed: null
  tier_2_decision: null
  tier_3_approved: null
  approved_by: null
  approved_at: null
  justification: null

FORCE_ACCEPT Sonderfall:
  Wenn Team Lead Gate manuell ueberstimmt:
    sc_i_gate.status: approved
    sc_i_gate.approved_by: "{user}"
    sc_i_gate.justification: "{Begruendung}"
    sc_i_gate.override_warning: "Gate-Kriterien nicht erfuellt, manuell ueberstimmt"
  → pipeline_mode: READY_FOR_I (trotz Gate-Fail)
```

**Gate-Symmetrie:** SC schreibt `sc_i_gate`, I antwortet mit `i_gate_response`.
Beide Gates bilden zusammen das bidirektionale Uebergangs-Protokoll (W202).

---

## POST-CYCLE Finale Verifikation: sc_i_gate_check() (3-Tier)

```
TIER-1 (BLOCKING — alle drei muessen PASS sein):
  C1: sc_final_srs < 70?
    → JA:  criteria_met APPEND "srs_under_70"
    → NEIN: TIER-1 FAIL → pipeline_mode: POST_CYCLE_RETRY, sc_i_gate.status: rejected
            Logge: "Gate FAIL C1: SRS={srs} >= 70. SC-Zyklen fortsetzen."
            STOP (kein READY_FOR_I)

  C2: Kritische W{n} (Kategorie architektur/mechanismen) >= 85% BESTAETIGT?
    → JA:  criteria_met APPEND "critical_wn_coverage"
    → NEIN: TIER-1 FAIL — wie oben

  C3: W51 BESTAETIGT UND W56 BESTAETIGT?
    → JA:  criteria_met APPEND "w51_w56_confirmed"
    → NEIN: TIER-1 FAIL — wie oben

TIER-2 (Conditional — mind. 2/3 muessen PASS sein):
  C4: Kritische ECs DONE >= 2 von 3 (EC-1, EC-2, EC-5)?
    → JA: tier2_count++
  C5: STAGNATION < 0.75?
    → JA: tier2_count++
  C6: HANDOFF.md hat mind. 4 Pflicht-Sektionen
       (LOESCHEN, BEHALTEN, OFFENE AUFGABEN, ARCHITEKTUR)?
    → JA: tier2_count++

  IF tier2_count < 2:
    TIER-2 FAIL → pipeline_mode: POST_CYCLE_RETRY, sc_i_gate.status: rejected
    STOP

TIER-3 (Governance — HiL-Signatur):
  C7: sc_i_gate.approved_by gesetzt?
    → JA:  tier_3_approved: true
    → NEIN: status: pending_approval (kein Hard-Stop, HiL-Benachrichtigung)
            HiL: "Forschung abgeschlossen. SC→I Gate bereit fuer Bestaetigung.
                  SRS={srs}, W{n}-Abdeckung={coverage}%. Genehmigen?"
            → Nach HiL-Bestaetigung: approved_by setzen, weiter zu PASS

GATE PASS (alle Tier erfuellt):
  sc_i_gate.status: approved
  sc_i_gate.tier_1_passed: true
  sc_i_gate.tier_2_decision: pass
  sc_i_gate.tier_3_approved: true
  sc_i_gate.approved_by: "{team-lead-user}"
  sc_i_gate.approved_at: {jetzt ISO8601}

  pipeline_mode: READY_FOR_I

  SC_I_LIFECYCLE.current_mode: READY_FOR_I
  SC_I_LIFECYCLE.sc_cycles_completed: {C}
  SC_I_LIFECYCLE.transition_log APPEND:
    from_mode: POST_CYCLE
    to_mode: READY_FOR_I
    timestamp: {jetzt ISO8601}
    reason: "Finale Verifikation PASS (W204), sc_i_gate APPROVED"
    agent: "sc-orchestrate-agent"

  Melde User: "SC-Phase abgeschlossen. pipeline_mode=READY_FOR_I.
               I-Pipeline kann mit /_I_orchestrate {NAME} gestartet werden."
```
