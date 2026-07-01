---
status: active
version: 1.0.0
created: 2026-04-26
op: ImplementationPipeline
phase: post
type: berater
chain_position: middle
model_tier: middle
---

# /_I_berater_nachphase (Nachphase — Post-Pipeline Cleanup + Routing)

[VERTRAG]
LIEST:
  - manifest.I_PIPELINE_STATE (slices, stufen_status, resume_zaehler)
  - manifest.worker_mode
  - manifest._manifest_protokoll.md (fuer Rollover-Schritt)
SCHREIBT:
  - manifest.i_core_result (BEDINGUNGSLOS, F03-Fix BL-054)
  - manifest.pipeline_mode ("SC_SYMBIOSE_I_DONE" | "I_COMPLETE")
  - _manifest_protokoll.md (Frontmatter + Prepend-Block bei Rollover)
  - manifest.I_PIPELINE_STATE (Rollover: historische Bloecke entfernen, resume_zaehler behalten)
OUTPUT: BERATER_OUTPUTS.nachphase.{verify_status, scope_gate_log, rollover_done, final_summary}
CROSS-REFERENCES:
  - Vorphase: _I_berater_* (slices, stufen aus I_PIPELINE_STATE)
  - Scope-Gate: symbiose-protocol.md Z47-74 (i_core_result Pflichtfelder)
  - Rollover-Pattern: W11, BL-054 (resume_zaehler NIEMALS rotieren)
  - SC-Rueckkanal: W37-Fix, symbiose-protocol.md Z61-74
[/VERTRAG]

---

## INVARIANTEN

- I1: i_core_result IMMER schreiben — unabhaengig vom Ergebnis (F03-Fix, BL-054)
- I2: resume_zaehler NIEMALS ins Protokoll rotieren (W11) — bleibt in {WORKING_DIR}/_manifest.md
- I3: worker_mode bestimmt pipeline_mode-Wert und TeamDelete-Verhalten
- I4: sc_recommendations.triggered nur true wenn Trigger-Kriterien zutreffen (symbiose-protocol.md)

---

## Schritt 8: verify global

```
spawne_wellen("verify", "global")
→ VERIFY.md (Feature-Gesamt), SPEC↔Tests Mapping, GAP-Report
```

---

## Schritt 8.5: Scope-Gate (universaler Exit, BL-054)

```
Logge: "SCOPE-GATE: Blueprint-Pipeline abgeschlossen."

# i_core_result: BEDINGUNGSLOS schreiben (F03-Fix, BL-054)
manifest.i_core_result = {
  # PFLICHTFELDER (W248, symbiose-protocol.md Z47-65)
  verify_status: "done",                   # "done" | "partial" | "failed"
  slices_completed: [I_PIPELINE_STATE.slices],
  slices: [Anzahl aus I_PIPELINE_STATE.slices],
  LOC: [aggregiert aus Implementierungsschritten],
  files_changed: [Best-Effort-Zaehler, Fallback: 0],
  gap_delta: null,                         # I macht kein /_gap (SDF Post-Phase entscheidet)
  scope_mode: "full",                      # BL-054: IMMER "full"
  completed_at: "{{DATUM}}T{{UHRZEIT}}Z",
  model_maintain_required: true,           # IMMER true (SDF Post-Phase ausstehend)
  gap_required: true,                      # IMMER true (SDF Post-Phase ausstehend)

  # SC-RUECKKANAL (Z3: P2, W37-Fix, symbiose-protocol.md Z61-74)
  sc_recommendations: {
    triggered: false,                      # true wenn Trigger-Kriterium zutrifft
    reason: "",
    next_focus: []
  },
  # Trigger-Logik (symbiose-protocol.md) UNVERAENDERT:
  #   triggered = true wenn:
  #   1. verify_status = partial UND kritischer Blocker identifiziert
  #   2. Implementation weicht signifikant von SPEC ab (> 20% Abweichung)
  #   3. Mehr als 30% der Slices verify = failed
  # Bei triggered=true: reason + next_focus befuellen

  # SC-KONTEXT-TRANSFER (Z3: P2, RF-05 Vorbedingung)
  key_changes: [
    { file: "pfad/datei", change: "Beschreibung der Aenderung" }
  ]
}

AUSGABE: "SCOPE-GATE: Blueprint-Pipeline abgeschlossen. i_core_result geschrieben."

# pipeline_mode: KONTEXTABHAENGIG — worker_mode als Trigger (W16, BL-054)
IF worker_mode == true:
  manifest.pipeline_mode = "SC_SYMBIOSE_I_DONE"
  Logge: "Worker-Mode: pipeline_mode = SC_SYMBIOSE_I_DONE (SC-Team erwartet Signal)."
  Logge: "Worker-Mode: TeamDelete SKIP (SC-Team bleibt aktiv)."
ELSE:
  manifest.pipeline_mode = "I_COMPLETE"
  Logge: "Standalone-Mode: pipeline_mode = I_COMPLETE."
  TeamDelete
→ EXIT
```

---

## Schritt 8.6: I_PIPELINE_STATE Rollover (Pattern B, W11, BL-054)

```
Bei I-Abschluss (nach Exit-Gate, BL-054):

Falls historische abgeschlossene I_PIPELINE_STATE-Bloecke im State vorhanden:

  Schritt R1 — Protokoll-Write (ZUERST, W18 Prepend):
  1. Frontmatter _manifest_protokoll.md aktualisieren:
     last_append={Datum}, append_count++
  2. Eintrag prependen (nach YAML-Frontmatter + Leerzeile):
     ## I-Pipeline Archiv [{Datum}]
     [Alter I_PIPELINE_STATE Block vollstaendig — scope_mode, slices, stufen_status]

  Schritt R2 — State-Update (DANACH):
  Entferne aus {WORKING_DIR}/_manifest.md:
    Historische I_PIPELINE_STATE-Bloecke (scope_mode=done, aeltere Laeufe)
  Behalte in {WORKING_DIR}/_manifest.md:
    Aktueller I_PIPELINE_STATE MIT resume_zaehler (PFLICHT — W11)
    i_core_result (letzter abgeschlossener Lauf)

ACHTUNG W11: resume_zaehler BLEIBT IMMER IN {WORKING_DIR}/_manifest.md STATE
  → Auch wenn gesamter I_PIPELINE_STATE-Block "abgeschlossen" scheint
  → resume_zaehler ist Stagnations-Detektor (= Live-State)
  → NIEMALS ins Protokoll rotieren (R5 Risiko: Resume-Faehigkeit bricht zusammen)
```

---

## Schritt 13: Final Summary

```
═══════════════════════════════════════════════════════════
I-PIPELINE ORCHESTRATION ABGESCHLOSSEN
Feature: {NAME}  |  Slices: {N}  |  Stufen: {M}
Pipeline-Dauer: {HH:MM:SS}
Tests: {X} Unit + {Y} Integration + {Z} System
═══════════════════════════════════════════════════════════
```
