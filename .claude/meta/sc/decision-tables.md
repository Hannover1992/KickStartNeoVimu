# SC Decision Tables (Zyklus-Entscheidung)

**Quelle:** Extrahiert aus `_SC_orchestrate.md` v2.4 → v3.0 (Decomposition)
**Geladen von:** Team Lead in Phase 3.2 (nach /_SC_ergebnis)

---

## Signale fuer Zyklus-Entscheidung

**Aus Worker-Message (/_SC_ergebnis):**
- SRS-Score und SRS-Trend
- Offene vs widerlegte W{n}
- Stagnations-Zaehler
- Fortschritts-Bewertung

**Aus /_SC_qualityGate:**
- Gate 3: Feature-Abschluss Coverage-%
- Gate 5: Stagnation (Schwellen)
- BSD-Trigger (T1-T5)

---

## Decision-Table: FULL + INLINE Modus (Standard)

```
+--------------------------+---------------------+----------+---------------+
| Signal                   | Bedingung           | Decision | Aktion        |
+--------------------------+---------------------+----------+---------------+
| Feature-Coverage         | >= 90%              | DONE     | Post-Cycle    |
| SRS-Trend                | Konvergent + stabil | DONE     | Post-Cycle    |
| GAP%-Delta               | GAP% stagniert      | DONE     | Post-Cycle    |
|                          | ueber 2+ Zyklen     |          | (kein Fortsch)|
| Stagnation               | >= 7.0              | ABORT    | Post-Cycle*   |
| Stagnation               | >= 5.0              | FORCE    | Post-Cycle    |
| Fortschritt              | STARK oder SCHWACH  | CONTINUE | Neuer Zyklus  |
| Max Zyklen erreicht      | easy=3, norm=5, h=8 | FORCE    | Post-Cycle    |
| User-Override            | (via HiL)           | varies   | nach Feedback |
+--------------------------+---------------------+----------+---------------+

* ABORT: Post-Cycle OHNE /_model finish. Direkt zu /_retrospektive
  mit ABORT-Vermerk. Meta-Analyse statt Feature-Abschluss.

HINWEIS v2.2: Diese Tabelle gilt fuer BEIDE Modi (FULL und INLINE).
  FULL-Modus: /_I_orchestrate laeuft INNERHALB des Zyklus.
    → Fortschritt KANN STARK sein (echte Implementation, echte GAP%-Reduktion).
    → Endlos-Loop UNMOEGLICH weil GAP% tatsaechlich sinken kann.
  INLINE-Modus: /_SC_implement laeuft INNERHALB des Zyklus.
    → Kleinere Aenderungen (1 IC, 5 Dateien, 100 LOC).
    → Fortschritt typischerweise SCHWACH, aber GAP% kann leicht sinken.
```

---

## Decision-Table: REVIEW-Modus (--mode=review)

```
+--------------------------+--------------------------+----------+---------------+
| Signal                   | Bedingung                | Decision | Aktion        |
+--------------------------+--------------------------+----------+---------------+
| Review-Items             | Alle RESOLVED/DEFERRED   | DONE     | Post-Cycle    |
| Gate 6 (Reality-Check)   | Code<->Model konsistent  | DONE     | Post-Cycle    |
| Fortschritt              | Items noch OPEN          | CONTINUE | Neuer Zyklus  |
| Max Zyklen erreicht      | easy=2, norm=3, hard=5   | FORCE    | Post-Cycle    |
| User-Override            | (via HiL)                | varies   | nach Feedback |
+--------------------------+--------------------------+----------+---------------+

REVIEW-Modus nutzt Gate 6 statt Gate 1 (Battle-Royale). SRS-Tracking DEAKTIVIERT.
Findings gehen nach .claude/analysis/post-impl/{NAME}-REVIEW-PROTOKOLL.md, NICHT ins Model.
```

---

## Decision-Table: ANALYSE-Modus (--mode=analyse, v2.3)

```
+--------------------------+----------------------------------+----------+---------------+
| Signal                   | Bedingung                        | Decision | Aktion        |
+--------------------------+----------------------------------+----------+---------------+
| Analyse-Saettigung       | delta_wn == 0 (keine neuen W{n}) | DONE     | Post-Cycle    |
| Model-Stabilitaet        | Model unveraendert ueber         | DONE     | Post-Cycle    |
|                          | 2 Zyklen                         |          |               |
| Max Zyklen erreicht      | easy=1, normal=2, hard=3         | FORCE    | Post-Cycle    |
| Neue W{n} gefunden       | delta_wn > 0 UND Zyklen < Max   | CONTINUE | Neuer Zyklus  |
| User-Override            | (via HiL)                        | varies   | nach Feedback |
+--------------------------+----------------------------------+----------+---------------+

sc_status bei DONE: DONE_DISCOVERY_ONLY (existierender Wert!)
SRS-Tracking DEAKTIVIERT (keine Implementation → kein SRS sinnvoll).
Kein Endlos-Loop: Max-Zyklen NIEDRIG (1/2/3) UND Saettigung als Exit-Kriterium.

ANALYSE-Zyklus-Tasks (reduziert gegenueber FULL/INLINE):
  observe → modelMaintain → qualityGate(reduziert) → hypothese(Forschungsfragen)
  → SKIP implement → ergebnis(Analyse-Metrik) → push_temp

SKIP implement: Task 7 wird bei ANALYSE-Modus NICHT erstellt/ausgefuehrt.
qualityGate(reduziert): Nur Model-Konsistenz, kein SRS, kein Battle-Royale.
hypothese(Forschungsfragen): Fokus auf WAS-noch-erforscht-werden-muss.
ergebnis(Analyse-Metrik): Misst delta_wn und Model-Stabilitaet statt GAP%-Delta.
```

---

## Max-Zyklen Uebersicht

| Modus | easy | normal | hard |
|-------|------|--------|------|
| FULL | 3 | 5 | 8 |
| INLINE | 3 | 5 | 8 |
| REVIEW | 2 | 3 | 5 |
| ANALYSE | 1 | 2 | 3 |
