# SYMBIOSE Manifest-Protokoll (v2.3, FULL-Modus)

**Quelle:** Extrahiert aus `_SC_orchestrate.md` v2.4 → v3.0 (Decomposition)
**Geladen von:** Team Lead bei Task 7 (FULL-Modus) und nach I-Rueckkehr

**Zweck:** Kommunikation zwischen SC und I im FULL-Modus (SC-I Symbiose).
I laeuft als Core-Pipeline (Schritte 0-8) statt voller Pipeline (0-13).

---

## SC vor I-Aufruf (Task 7, FULL-Modus)

```
1. Manifest: pipeline_mode = SC_SYMBIOSE_I_ACTIVE
2. SC_I_LIFECYCLE.transition_log APPEND:
   from_mode: SC
   to_mode: SC_SYMBIOSE_I_ACTIVE
   timestamp: {jetzt ISO8601}
   reason: "SC Task 7 (FULL): I-Pipeline core starten"
3. I-Pipeline starten: /_I_orchestrate {NAME}
   → I erkennt SC_SYMBIOSE_I_ACTIVE in Schritt 0.2b
   → I laeuft core (Schritte 0-8)
   → I setzt SC_SYMBIOSE_I_DONE + i_core_result in Schritt 8.5
   → I macht TeamDelete + EXIT
```

---

## SC nach I-Rueckkehr (Task 7, nach I beendet)

```
1. Lies Manifest: pipeline_mode == SC_SYMBIOSE_I_DONE
2. Lies i_core_result (siehe Struktur unten)
3. Manifest: pipeline_mode = SC (zurueck)
4. SC_I_LIFECYCLE.transition_log APPEND:
   from_mode: SC_SYMBIOSE_I_DONE
   to_mode: SC
   reason: "I core abgeschlossen, SC spawnt ergebnis"
5. Spawne /_SC_ergebnis (Task 8) — Ergebnis-Agent kann i_core_result lesen
```

---

## i_core_result Struktur (Pflichtfelder)

```yaml
i_core_result:
  # PFLICHTFELDER (MUSS von /_I_orchestrate gesetzt werden):
  slices_completed: []          # Liste: [S1, S2, ...]
  verify_status: done|partial|failed
  gap_delta: number|null        # GAP%-Delta (null wenn scope_mode=core)
  scope_mode: core|full
  completed_at: "YYYY-MM-DD"

  # ERGEBNIS-DETAIL:
  key_changes:                  # Was wurde implementiert
    - description: ""
      files_changed: []

  # OPTIONALE RUECKKANAL-FELDER:
  sc_recommendations:
    triggered: false            # true = I empfiehlt SC-Fokus-Aenderung
    reason: ""
    next_focus: []
```

---

## i_sc_return.triggered Kriterien

sc_recommendations.triggered = true wenn:
1. verify_status = partial UND kritischer Blocker identifiziert
2. Implementation weicht signifikant von SPEC ab (> 20% Abweichung)
3. Mehr als 30% der Slices verify = failed

**Lese-Prioritaet in /_SC_ergebnis (Task 8):**
i_core_result hat PRIORITAET ueber SC-Hypothese bei Widerspruch.
Begruendung: i_core_result = gemessene Implementierungsrealitaet, Hypothese = Erwartung vor I.
