---
type: satellite
---

# SDF-Pipeline - Tiefen-Narrative (Assay-Format)

Zeige Assay-tiefe Phase-Essays der SDF-Pipeline post-BL-142.

## Aufruf

```
/_SDF_help_extended
```

---

## EINE METAPHER VORAUS

Stell dir SDF als **Dirigenten eines Orchesters**. Die Partitur (BATCH-PLAN) hat
IDF geschrieben. Die Musiker (I, SC, TDD, WP, PR) sind verteilt im Saal. Der
Dirigent entscheidet **nicht**, welche Noten gespielt werden — das tut die
Partitur. Er entscheidet **nicht**, ob ein Stueck schoen ist — das ist
Geschmackssache. Er entscheidet **Tempo und Dynamik**: wann setzen die Streicher
ein, wie laut spielen die Blaeser, ob ein Satz wiederholt wird.

Genau so SDF: Mode (M1-M9) ist Tempo. executionDispatch ist Dynamik (welcher
Musiker spielt jetzt). Recalibrate ist eine kurze Pause, in der der Dirigent
schaut, ob die Streicher noch im Takt sind. LOOP-DECISION ist die Frage, ob das
naechste Stueck folgt oder das Konzert vorbei ist.

Die Daseinsberechtigung von SDF ist die **Trennung von Was und Wie**. A liefert
das Material. IDF zerlegt es in Stuecke. SDF entscheidet, wie diese Stuecke
gespielt werden — Mode (M1-M9) ist die einzige Sprache, mit der SDF mit der
Aussenwelt redet.

---

## PHASE 0 — Lite-Resume-Guard

**Was die Phase tut:** Eigenes DF_BATCH_STATE-Resume. Prueft, ob der aktuelle
Batch unterbrochen wurde, springt ggf. zur naechsten Phase.

**Daseins-Berechtigung:** SDF kann Batches sehr lange laufen lassen
(Mode M5 = SC-Symbiose mit vielen Zyklen). Resume verhindert, dass ein
Abbruch mitten in Phase 2 die Mode-Decision wiederholt.

**Inputs:** DF_BATCH_STATE, last_phase_completed.
**Outputs:** Resume-Punkt oder fresh.
**Konsumenten:** Phase 1.

**Drei Beispiele:**
1. Erster Batch-Lauf → fresh, Phase 1 startet.
2. Lauf brach in Phase 2 ab → Resume bei Phase 2 (executionDispatch).
3. Mode war schon entschieden → Resume direkt zu Dispatch.

---

## PHASE 1 — BATCH-MODUS (C3 modusEntscheidung)

**Was die Phase tut:** **Die zentrale Entscheidungs-Stelle** in SDF. Berater
(Opus, 50+ Pfade) liest:

- aggregat_k_score (Reife der Wissensbasis)
- aggregat_srs_score (System-Reflection)
- aggregat_gap_percent (IST vs SOLL)
- aggregat_freiheitsgrade (wie viele Loesungswege?)
- unreife_typ (was genau fehlt?)
- reifegrad (REIF / FRISCH)

Entscheidet einen der 9 Modi (M1-M9).

**Daseins-Berechtigung:** Mode-Decision war frueher in A's Phase 4.2 versteckt.
Das war eine Schichten-Verletzung — A liest Code-State nicht zuverlaessig, A
soll nur Wissen liefern. Mit BL-142 wandert die Entscheidung explizit zu SDF,
wo der Batch-Kontext lebendig ist.

**Inputs:** BATCH-PLAN, BL-Aggregate, PL-Items.
**Outputs:** `mode = M1..M9` + Begruendung.
**Konsumenten:** Phase 2 executionDispatch.

**Drei Beispiele:**
1. aggregat_gap_percent = 80%, aggregat_srs hoch → M5 (SC-Symbiose).
2. aggregat_gap_percent = 5%, aggregat_k_score hoch → M2 (Inline).
3. reifegrad=FRISCH, k_score niedrig → M1 (Skip + Recalibrate).

---

## PHASE 2 — WORKING (executionDispatch)

**Was die Phase tut:** Routet zum Mode-Ziel:

- M2 → /_I_orchestrate -I
- M3 → /_I_orchestrate scope=full
- M4 → /_SC_orchestrate -I
- M5 → /_SC_orchestrate (Symbiose)
- M6 → /_SC_orchestrate --mode=analyse
- M7 → /_TDD_orchestrate
- M8 → /_Post_PR_orchestrate
- M9 → /_WP_orchestrate
- M1 → kein Dispatch, direkt Phase 3.1

**Daseins-Berechtigung:** Dispatch ist **trivial, aber stabil**. Jede neue
Mode-Erweiterung passiert hier. SDF wird nicht zum Aufruf-Wrapper, weil der
Berater nur die Routing-Tabelle pflegt — keine Logik.

**Inputs:** Mode-Entscheidung, Batch-Kontext.
**Outputs:** Sub-Orchestrator-Ergebnis (PL-Items DONE / FAILED / NEW).
**Konsumenten:** Phase 3.1.

**Drei Beispiele:**
1. M5 → SC-Symbiose laeuft, schreibt Code, meldet success.
2. M2 → I-Pipeline inline, kleine Aenderungen committed.
3. M1 → Skip, kein Dispatch.

---

## PHASE 3.1 — Recalibrate (M1-Skip per BL-014)

**Was die Phase tut:** Wenn Mode M1 oder Re-Run nach Phase 2: prueft, ob die
Batch-Aggregate noch passen oder Recalibration noetig ist. Spezial-Case BL-014
erlaubt M1-Skip ohne Re-Eval.

**Daseins-Berechtigung:** Recalibrate verhindert, dass nach erfolgter
Mode-Ausfuehrung alte Aggregate die naechste Decision dominieren. Wenn Code
geaendert wurde, sind k_score / gap_percent veraltet.

**Inputs:** Mode + Phase 2 Outputs.
**Outputs:** Aktualisierte Aggregate oder M1-Skip-Flag.
**Konsumenten:** Phase 3.2.

**Drei Beispiele:**
1. Nach M5 → Recalibrate liest neuen Gap.
2. M1-Skip per BL-014 → kein Recalibrate-Aufwand.
3. Recalibrate findet drift → Phase 4 wird ROLLBACK empfehlen.

---

## PHASE 3.2 — PostBatch (GAP-Check)

**Was die Phase tut:** Berater laeuft GAP-Check ueber den Batch: passt das
geschriebene Ergebnis zur Spec?

**Daseins-Berechtigung:** Ohne Post-Check koennte der Batch fertig erscheinen,
obwohl die Spec nicht erfuellt ist. GAP-Check schliesst die Schleife zwischen
Mode-Output und Spec-Anchor.

**Inputs:** Phase 2 Outputs, Spec.md, Code-State.
**Outputs:** GAP-Report pro PL-Item im Batch.
**Konsumenten:** Phase 3.3.

**Drei Beispiele:**
1. Alle PL-Items erfuellen Spec → DONE.
2. PL-Item-3 hat Gap → markiert FAILED, geht in next Batch.
3. Spec hat sich waehrend Run geaendert → Berater meldet Drift, Rollback.

---

## PHASE 3.3 — StatusTransition (PL/BL Status)

**Was die Phase tut:** Setzt Status fuer jedes PL-Item: DONE / FAILED / SKIPPED.
Aktualisiert BL-Item-Status, wenn alle PL-Items fertig.

**Daseins-Berechtigung:** Status ist die **Gleitschiene** zwischen Pipeline-
Laeufen. Ohne saubere Status-Transition wuerde ein nachfolgender BDF-Lauf nicht
wissen, welche Items er ueberspringen kann.

**Inputs:** GAP-Report aus 3.2.
**Outputs:** Manifest-Status-Update (PL-Items + BL-Item).
**Konsumenten:** Phase 4 LOOP-DECISION, kuenftige BDF-Laeufe.

**Drei Beispiele:**
1. Alle PL DONE → BL = DONE.
2. PL-3 FAILED → BL bleibt PARTIAL.
3. PL SKIPPED durch M1 → BL bleibt FRESH (kein Fortschritt).

---

## PHASE 4 — LOOP-DECISION

**Was die Phase tut:** **Drei Pfade**:

1. **ROLLBACK zu IDF Phase 4-7:** Phase 2 hat neue PL-Items entdeckt (Spec-
   Drift, Sub-Tasks). IDF muss DAG / Cluster / BATCH neu bauen.
2. **TERMINATE:** Alle Batches abgeschlossen. SDF schliesst Pipeline.
3. **RE-BATCH (IDF Phase 7 direkt):** Naechster Batch im gleichen BATCH-PLAN.

**Daseins-Berechtigung:** Ohne LOOP-DECISION wuerde SDF entweder zu frueh
beenden (Items vergessen) oder zu oft IDF neu starten (Lifecycle-Verletzung).
Die drei Pfade sind die einzigen sauberen Exits.

**Inputs:** Status aus 3.3.
**Outputs:** Naechster Schritt (Rollback / Terminate / Re-Batch).
**Konsumenten:** IDF (bei Rollback / Re-Batch), Pipeline-Owner (bei Terminate).

**Drei Beispiele:**
1. Phase 2 meldete 3 neue PL-Items → ROLLBACK.
2. BATCH-PLAN hatte 3 Batches, alle DONE → TERMINATE.
3. BATCH-PLAN hatte 3 Batches, 1 abgeschlossen → RE-BATCH (Batch 2).

---

## C3 ALS ZENTRALE ENTSCHEIDUNGS-STELLE (50+ PFADE)

C3 ist nicht trivial. Die 6 Eingangs-Felder spannen einen mehrdimensionalen
Raum auf. Berater (Opus) entscheidet anhand von Heuristiken, die sich aus
dem Knowledge-Graph entwickelt haben:

- **Hoher gap_percent + niedriger k_score** → Recalibrate (M1) oder Analyse (M6).
- **Hoher gap_percent + hoher k_score** → SC-Symbiose (M5) oder I-Standalone (M3).
- **Niedriger gap_percent + reifegrad=REIF** → Inline (M2).
- **is_meta_command=true** → spezial-Modus (Meta-Pfad).
- **freiheitsgrade hoch** → SC-Analyse (M6) zuerst, dann Mode neu entscheiden.

Genaue Pfade liegen in `_SDF_berater_modusEntscheidung.md`.

---

## MODE-MAPPING M1-M9

| Mode | Sub-Pipeline | Wann |
|------|--------------|------|
| M1 | (Skip / Recalibrate) | reifegrad=FRISCH oder Pseudo-Item |
| M2 | /_I_orchestrate -I | gap klein, Wissen reif |
| M3 | /_I_orchestrate full | gap mittel, Wissen reif |
| M4 | /_SC_orchestrate -I | gap mittel, freiheitsgrade hoch |
| M5 | /_SC_orchestrate (Symbiose) | gap hoch, srs hoch |
| M6 | /_SC_orchestrate --mode=analyse | reine Analyse, kein Code |
| M7 | /_TDD_orchestrate | testgetrieben, klare Ringe |
| M8 | /_Post_PR_orchestrate | PR-Review |
| M9 | /_WP_orchestrate | Paper / Wissens-Produkt |

---

## EXECUTIONDISPATCH ROUTING

Dispatch ist eine reine Tabelle. Mode-ID wird auf Sub-Orchestrator-Aufruf
gemappt. Berater pflegt diese Tabelle. Wenn ein neuer Mode kommt (M10), aendert
sich nur die Tabelle — keine SDF-Logik.

---

## RECALIBRATE-LOGIK (M1-Skip)

BL-014 fuehrte den Spezial-Fall ein: Wenn der Berater erkennt, dass der Item
keine echte Aufgabe ist (z.B. ein Pseudo-Item aus IDF-Drift), dann skippt er
ohne Recalibrate. Das verhindert eine Endlos-Schleife (recalibrate → recalibrate
→ recalibrate).

---

## LOOP-DECISION 3-PFAD-LOGIK

Der Unterschied zwischen ROLLBACK und RE-BATCH ist subtil:

- **ROLLBACK:** Es entstanden **neue PL-Items** (z.B. C-Schicht abgeleitet aus
  A-Schicht). DAG ist veraltet. IDF muss Phase 4-7 neu laufen.
- **RE-BATCH:** Keine neuen PL-Items. Naechster Batch im gleichen BATCH-PLAN.
  IDF startet bei Phase 7 (direkt BATCH_PLAN-Fortsetzung).

Diese Trennung ist die **Anti-Endless-Loop-Garantie**: Re-Batches sind billig,
Rollbacks sind teuer und werden seltener ausgeloest.

---

## SINGLE-RESPONSIBILITY (SDF entscheidet WIE, nicht WAS)

A entscheidet nichts (sammelt nur Material).
IDF entscheidet WAS (welche PL-Items, welche Reihenfolge).
SDF entscheidet WIE (welcher Mode pro Batch).
Sub-Orchestratoren (I, SC, TDD, WP, PR) **machen** (schreiben Code, schreiben
Tests, schreiben Paper).

Diese 4-Schicht-Trennung ist die Architektur-These post-BL-142. Verletzt eine
Schicht ihre Grenze, entstehen Probleme:

- A entscheidet WIE → Stille Post.
- IDF entscheidet WIE → Mode-Wahl ohne Batch-Kontext.
- SDF entscheidet WAS → Mode-Wechsel mitten in einem Run.
- Sub-Orchestratoren entscheiden WIE → unbegrenzte Mode-Drift.

---

## MINI-THESE

SDF ist **kein Macher**, sondern ein **Mode-Setzer**. Die Macher (Sub-
Orchestratoren) machen — aber nur, wenn SDF vorher den richtigen Mode gesetzt
hat. Mode-Setzen heisst: Entscheiden, was sich aus den Aggregaten ableiten
laesst, ohne in den Code zu schauen. Wenn SDF das mit Disziplin tut, bleibt der
Workflow stabil. Wenn nicht, driftet die ganze Pipeline.

---

ARGUMENTS: $ARGUMENTS
