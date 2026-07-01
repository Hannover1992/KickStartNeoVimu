---
type: satellite
---

# IDF-Pipeline - Tiefen-Narrative (Assay-Format)

Zeige Assay-tiefe Phase-Essays der IDF-Pipeline post-BL-142.

## Aufruf

```
/_IDF_help_extended
```

---

## UPDATE BL-209 (2026-05-24) — IDF Hard-Cut: Phase 2/3.1/3.2 ENTFERNT

Nach BL-197 + BL-198 + BL-209 ist IDF eine WIRKLICH reine PL-Verwalterin:
Phase 2 (specParse), Phase 3.1 (akExtraktion), Phase 3.2 (plAggregation) sind
**physisch entfernt** (Hard-Cut). A-Pipeline Phase 5a/5b/5c ist Single-Source.
IDF startet IMMER bei Phase 3.5 (validator) — kein Skip-Check, kein Fallback.

INV-IDF-SKIP-1 RETIRED. INV-BC-1 RETIRED. _IDF_berater_specParse/akExtraktion/
plAggregation DEPRECATED. _A_berater_* sind alleinige Namespace-Inhaber.

Phase 3.7 modelSync bleibt aktiv als **Reverse-Sync**: PL-Korrekturen
(aus /_parking-lot Entry 3) fliessen zurueck in Model.md (Continuous-Learning).

Referenz: BL-209 Hard-Cut, BL-197 AK-6 (urspruenglich INV-IDF-SKIP-1 — jetzt RETIRED), INV-IDF-REVERSE-1.

---

## DREI ENTRY-POINTS (BL-198, AK8-PL-2)

IDF kennt nach BL-198 drei verschiedene Einstiegspunkte:

**Entry 1 — Standard-Pfad (frisch):**
```
User-Story → BDF → A-Pipeline (Phase 1..5c) → pl_pre_filled_after=true
→ IDF ab Phase 3.5 (validator)
```
A-Pipeline hat bereits PL erzeugt. IDF uebernimmt als PL-Verwalterin.

**Entry 2 — Resync-Pfad:**
```
_A_orchestrate --resync → A-Pipeline erzeugt PL neu → pl_pre_filled_after=true
→ IDF ab Phase 3.5 (validator)
```
Wird verwendet wenn Spec sich geaendert hat und PL neu abgeleitet werden muss.

**Entry 3 — Direkt-PL (/_parking-lot):**
```
User korrigiert PL-Item via /_parking-lot → IDF direkt (Phase 3.7 aktiv)
```
Phase 3.7 modelSync ist der **Continuous-Learning-Mechanismus**: wenn ein
PL-Item durch den User korrigiert wird (neue Erkenntnis, geaenderte Prio),
lernt Model.md davon zurueck (Reverse-Sync PL → Model). INV-IDF-REVERSE-1
sichert: Phase 3.7 ist AUSSCHLIESSLICH Reverse — kein Forward-Erzeuger.

---

## EINE METAPHER VORAUS

Stell dir IDF als **Buchbinder vor, der eine Loseblatt-Sammlung in Kapitel
ordnet**. Nach BL-198 bringt A die sortierten Kapitel (PL-Items) bereits
vorsortiert mit. Der Buchbinder prueft ob alle Kapitel vollstaendig sind
(Phase 3.5), reichert Frontmatter an (Phase 3.6), prueft ob er aus neuen
Randnotizen in den Kapiteln etwas fuer das Inhaltsverzeichnis lernen kann
(Phase 3.7 Reverse), und erstellt dann den Bind-Plan (DAG + Cluster + Batch).

Was der Buchbinder NICHT mehr tut: Er sortiert die Seiten nicht mehr von
Grund auf neu (das hat A schon erledigt). Er ordnet, gruppiert, verbindet —
aber der Rohstoff PL kommt von A.

Die Daseins-Berechtigung von IDF ist die **Brueckenfunktion zwischen
Wissensbasis und Produktion**. Ohne IDF muesste SDF die PL-Items selbst
sequenzieren und clustern, das wuerde SRP verletzen. Mit IDF bekommt SDF
einen fertigen Batch-Plan und muss nur noch entscheiden, wie er produziert wird.

---

## PHASE 0 — Resume-Detection

**Was die Phase tut:** Prueft, ob ein vorheriger IDF-Lauf abgebrochen ist und
fortgesetzt werden soll.

**Daseins-Berechtigung:** IDF kann lange laufen (besonders Phase 2 SPEC_PARSE
mit Wellen). Ein Abbruch nach Phase 4 sollte nicht alles erneut anstossen.
Resume-Detection liest State und springt zur korrekten Phase.

**Inputs:** IDF_PIPELINE_STATE, last_phase_completed.
**Outputs:** Resume-Punkt oder fresh.
**Konsumenten:** Phase 1 INIT.

**Drei Beispiele:**
1. Vorheriger Lauf abgeschlossen → fresh, alle Phasen.
2. Lauf brach nach Phase 4 ab → Resume bei Phase 5.
3. State korrupt → Berater meldet, HiL.

---

## PHASE 1 — INIT [_IDF_berater_init]

**Was die Phase tut:** Resume + State + TeamCreate. Naming `idf-{BL_ID}` (z.B.
`idf-BL-142`).

**Daseins-Berechtigung:** Lifecycle-Klammer Eingang. Ohne saubere INIT laufen
mehrere IDF-Instanzen ggf. parallel im selben State.

**Inputs:** BL_ID, Resume-Punkt aus 0.
**Outputs:** Team-Kontext + IDF_PIPELINE_STATE initialisiert.
**Konsumenten:** Alle nachfolgenden Phasen.

**Drei Beispiele:**
1. Erster Lauf BL-142 → TeamCreate `idf-BL-142`.
2. Zweiter Lauf gleiche BL → Stale-Cleanup, neues Team.
3. Vorgaenger-Team `a-BL-142` aktiv → Cleanup, dann TeamCreate.

---

## PHASE 2 — SPEC_PARSE (Wellen 5+3+1)

**BL-209 Hard-Cut: Phase 2 ENTFERNT**
Phase 2 (_IDF_berater_specParse) existiert nicht mehr in IDF.
A-Pipeline Phase 5a (_A_berater_specParse) ist alleinige Quelle.
INV-IDF-SKIP-1 + INV-BC-1 RETIRED. Kein Skip-Check, kein Fallback.

**Was die Phase tat (historisch, DEPRECATED):** Liest Spec.md, parst Phasen + AKs in 3 Wellen
(5 Discovery + 3 Validation + 1 Synthesis). Ergebnis: strukturierte AK-Liste.

**Daseins-Berechtigung:** Spec.md ist Markdown. AKs muessen maschinell extrahiert
werden, mit Anchors, Constraints, Scope-Markern. Drei Wellen erzwingen
Cross-Check; Synthese eliminiert Ausreisser. Ohne diese Disziplin gibt es
Phantom-AKs (extrahiert, aber existieren in Spec nicht).

**Inputs:** Spec.md, K-SCORE.md (oder: SKIP via pl_pre_filled_after=true).
**Outputs:** AK-Liste mit Anchors (oder: BERATER_OUTPUTS.specParse.status=SKIP).
**Konsumenten:** Phase 3.1.

**Drei Beispiele:**
1. A-Pipeline DONE mit Phase 5a → Phase 2 SKIP, IDF springt weiter.
2. Altes BL ohne A-Pipeline → Phase 2 laeuft normal (INV-BC-1).
3. Spec hat AK ohne Anchor → Berater markiert, Synthese-Welle korrigiert.

---

## PHASE 3.1 — AK-Extraktion (Per-AK, parallel)

**Nach BL-198: SKIP wenn `pl_pre_filled_after=true`**
Phase 3.1 wird uebersprungen wenn A-Pipeline Phase 5b bereits akExtraktion
ausgefuehrt hat. BERATER_OUTPUTS.akExtraktion.status = "SKIP" wird gesetzt.

**Was die Phase tut (wenn aktiv):** Pro AK liest der Berater Spec + Model + K-Score
und schreibt `ak_metadata`. Parallel ueber alle AKs.

**Daseins-Berechtigung:** Pro-AK-Granularitaet ist die **Aufloesung der
Wahrheit**. Ein PL-Item kann mehrere AKs umfassen — aber die Metadaten muessen
pro AK greifbar sein, sonst gehen Anchors verloren.

**Inputs:** AK-Liste aus 2, Spec, Model, K-SCORE (oder: SKIP).
**Outputs:** `ak_metadata.{ak_id}` pro AK (oder: BERATER_OUTPUTS.akExtraktion.status=SKIP).
**Konsumenten:** Phase 3.2.

**Drei Beispiele:**
1. A-Pipeline DONE mit Phase 5b → Phase 3.1 SKIP.
2. AK-A-1 hat klare Anchors → ak_metadata komplett (normaler Lauf).
3. AK ohne K-Score-Eintrag → Berater meldet Drift, A muss nachliefern.

---

## PHASE 3.2 — PL-Aggregation (Per-PL, sequenziell)

**Nach BL-198: SKIP wenn `pl_pre_filled_after=true` + Entry-Point 3.5**
Phase 3.2 wird uebersprungen wenn A-Pipeline Phase 5c bereits plAggregation
ausgefuehrt hat. BERATER_OUTPUTS.plAggregation.status = "SKIP" wird gesetzt.
IDF_PIPELINE_STATE.current_phase = "3.5" — IDF springt direkt zu Phase 3.5 (validator).

**Was die Phase tut (wenn aktiv):** Gruppiert AKs zu PL-Items (1 PL = 1..N AKs).
Aggregiert pro PL-Item: `k_score_pl`, `srs_pl`, `model_refs union`, `layer`.

**Daseins-Berechtigung:** PL-Items sind die **Arbeits-Einheiten** der Pipeline.
Ein PL-Item hat klaren Scope, klare Anchors, klares Aggregat.

**Inputs:** ak_metadata pro AK, PL-Naming-Regeln (oder: SKIP).
**Outputs:** PL-Items im Parking-Lot (oder: BERATER_OUTPUTS.plAggregation.status=SKIP).
**Konsumenten:** Phase 3.5 (validator) — direkt wenn SKIP.

**Drei Beispiele:**
1. A-Pipeline DONE mit Phase 5c → Phase 3.2 SKIP, IDF springt zu Phase 3.5.
2. AK-A-1 + AK-A-2 betreffen gleiches Modul → 1 PL-Item (normaler Lauf).
3. AK-A-4 ohne klare Layer-Zuordnung → Berater wirft Frage, HiL.

---

## PHASE 4 — DEPENDENCY_MATRIX [_IDF_berater_dependencyAnalyzer]

**Was die Phase tut:** Bildet einen DAG ueber alle PL-Items: welches PL-Item
referenziert welches? Berater war frueher in SDF, ist nun in IDF absorbiert.

**Daseins-Berechtigung:** Ohne DAG koennte SDF zwei voneinander abhaengige
PL-Items in den falschen Batch packen. DAG-Bildung gehoert zu Decomposition,
nicht zu Mode-Decision — daher in IDF.

**Inputs:** PL-Items + Anchors.
**Outputs:** `DEPENDENCY-MATRIX.md` mit DAG.
**Konsumenten:** Phase 5, Phase 6.

**Drei Beispiele:**
1. PL-A baut auf PL-B → DAG-Kante PL-B → PL-A.
2. Zwei PL-Items unabhaengig → keine Kante, parallel-faehig.
3. Zyklus erkannt → Berater wirft Fehler, A muss Spec entzyklen.

---

## PHASE 5 — CLUSTERING

**Was die Phase tut:** Gruppiert PL-Items in Cluster basierend auf Cohesion
(gemeinsame Layer / gemeinsame Anchors / gemeinsame Pattern). Aggregiert pro
Cluster — als **Hint** fuer SDF, nicht als Pflicht.

**Daseins-Berechtigung:** Cluster sind die **thematische Karte**. SDF kann sich
einen Cluster als "ein Thema" nehmen. Aber: Cluster ist Hint, nicht Vertrag.
Der autoritative Plan kommt erst in Phase 7.

**Inputs:** PL-Items, DAG.
**Outputs:** `CLUSTER-MAP.md` + Aggregate pro Cluster.
**Konsumenten:** Phase 6, Phase 7.

**Drei Beispiele:**
1. 4 PL-Items im gleichen Layer → 1 Cluster.
2. 1 PL-Item Cross-Cutting → Singleton-Cluster.
3. PL-Items lose verbunden → kleinere Cluster mit Hint "evtl trennbar".

---

## PHASE 6 — BATCH_SEQUENCE [_IDF_berater_sequencePlanner]

**Was die Phase tut:** Topologisch sortiert PL-Items unter DAG-Constraints.
Erzeugt eine **Reihenfolge** ueber alle PL-Items.

**Daseins-Berechtigung:** Sequence ist die **Voraussetzung fuer Batch-Bildung**.
Sortierung berueksichtigt Dependencies + Cluster-Hints. Berater war frueher in
SDF; topologische Sortierung gehoert aber zu Decomposition.

**Inputs:** PL-Items, DAG, Cluster.
**Outputs:** `BATCH-SEQUENCE.md` (lineare Reihenfolge).
**Konsumenten:** Phase 7.

**Drei Beispiele:**
1. DAG hat klare Topologie → eine eindeutige Sequenz.
2. Mehrere gueltige Topologien → Berater waehlt nach Cluster-Cohesion.
3. Topologie unmoeglich (Zyklus) → Phase 4 haette schon abgebrochen.

---

## PHASE 7 — BATCH_PLAN (NEU) [_IDF_berater_batchPlan]

**Was die Phase tut:** Schreibt den **autoritativen Batch-Plan**. Wraps
batchPlanner. Zusaetzlich:

- EXTERN/INTERN-Scan (welche Items brauchen externe Sources, welche bleiben
  intern?)
- Aggregate pro Batch (Batch-Aggregate)

**Daseins-Berechtigung:** BATCH-PLAN ist die **autoritative
Entscheidungs-Einheit**. SDF C3 entscheidet pro Batch, nicht pro PL-Item, nicht
pro Cluster. Phase 7 fasst alle vorherigen Outputs zu einem
unaenderbaren Plan zusammen.

**Inputs:** BATCH-SEQUENCE, Cluster, PL-Items.
**Outputs:** `BATCH-PLAN-{N}.md` mit Batch-Aggregat + EXTERN/INTERN-Markierung.
**Konsumenten:** SDF Phase 1 (BATCH-MODUS C3).

**Drei Beispiele:**
1. 12 PL-Items → 3 Batches (4-4-4) mit jeweils Aggregat + Scan.
2. Ein PL-Item benoetigt externes Wissen → INTERN-Scan negativ, EXTERN-Marker.
3. Batch-Aggregat unklar → Berater eskaliert (zurueck zu Phase 5/6).

---

## PHASE 8.0 — FINAL_SUMMARY (NEU BL-204)

**Was die Phase tut:** Konsolidiert alle IDF-Phasen-Outputs (Phase 0..7.6)
READ-ONLY in zwei Vektor-Formate:
- Mensch-Output: `{bl_folder}/4_Blueprint/idf_final_summary_{date}.md` (9-Spalten-Tabelle)
- Maschine-Output: `_manifest.md` IDF_FINAL_SUMMARY YAML-Block

**Invarianten:** INV-RO-1 (kein vorheriges Feld aendern), INV-MODUS-1 (modus_hint
ist Vorhersage — C3 entscheidet final in SDF Phase 1.1), INV-ANTIHUT-1 (1-Satz-
Komprimierung nur aus Phase-7-Rationale, keine Erfindung).

**Inputs:** DF_BATCH_STATE (batch_sequence, metric_per_batch, batch_stages), BERATER_OUTPUTS_IDF (batchPlan.rationale, plBewertung.pain_signals, dependencyAnalyzer.edges).
**Outputs:** 4_Blueprint/idf_final_summary_{date}.md + _manifest.md IDF_FINAL_SUMMARY.
**Konsumenten:** Operator (Tabelle), SDF Phase 1.1 modusEntscheidung (modus_hint als Kontext).

---

## PHASE 8 — IDF_DONE → Recheck-Guard

**Was die Phase tut:** Schliesst IDF ab, ruft Recheck-Guard, liefert Batch
explizit an SDF.

**Daseins-Berechtigung:** Ohne Recheck-Guard koennte ein zirkulaerer Aufruf
entstehen (SDF triggert IDF-Rollback, IDF triggert SDF, ...). Guard erzwingt:
**1 IDF-Lauf = 1 Batch-Lieferung**, Re-Batches gehen direkt in Phase 7, nicht
zurueck zu Phase 1.

**Inputs:** BATCH-PLAN.
**Outputs:** SDF wird mit Batch-ID gestartet.
**Konsumenten:** SDF.

**Drei Beispiele:**
1. Erfolgs-Pfad → SDF erhaelt Batch 1.
2. SDF brach Mitte Batch ab → IDF startet **nicht** neu, SDF resumed selbst.
3. SDF meldet new PL-Items → Phase 8 routet zu Phase 4 (nicht 1).

---

## DAG-BILDUNG (Detail)

DAG = gerichteter azyklischer Graph. Jede PL-Kante ist gerichtet (PL-A "haengt
ab von" PL-B). Zyklen bedeuten: zwei PL-Items koennen ohne einander nicht
gebaut werden — was meist auf eine Spec-Schwaeche hindeutet (zu eng gekoppelt).
IDF blockt Zyklen und schickt zurueck an A.

---

## CLUSTER-LOGIK (Cohesion)

Cohesion-Metriken:

- **Layer-Match:** PL-Items im gleichen Layer (z.B. API-Schicht).
- **Anchor-Overlap:** PL-Items teilen sich spec_anchor / model_anchor.
- **Pattern-Reuse:** PL-Items wenden gleiches Pattern an.

Cluster-Bildung ist heuristisch, nicht deterministisch. Daher: Hint-Status, nicht
Pflicht.

---

## TOPOLOGISCHE SORTIERUNG

Standard-Algorithmus (Kahn / DFS-basiert). Bei mehreren gueltigen Topologien
waehlt Berater die mit hoechster Cluster-Cohesion (zwei PL-Items aus gleichem
Cluster moeglichst nebeneinander).

---

## BATCH_PLAN ALS AUTORITATIVE ENTSCHEIDUNGS-EINHEIT

Vor BL-142 entschied SDF auf PL-Item-Ebene. Mit BL-142 entscheidet SDF auf
Batch-Ebene. Der Unterschied: ein Batch kann mehrere PL-Items als **eine Mode-
Entscheidung** behandeln (z.B. M2 fuer alle 4 PL-Items im Batch). Das reduziert
Mode-Wechsel und steigert Konsistenz.

---

## EXTERN/INTERN-SCAN-MECHANIK

Pro Batch scannt der Berater:

- **INTERN-faehig:** Alles Wissen liegt in der Wissensbasis (Model, Spec,
  Vault).
- **EXTERN noetig:** Es fehlt Wissen, das aus externer Quelle (Doku, RAG, User-
  Hint) ergaenzt werden muss.

EXTERN-Markierung triggert SDF, in seinem Mode-Pfad ggf. einen
Wissens-Beschaffungs-Schritt einzuplanen.

---

## RECHECK-GUARD (Anti-Zirkel)

Ohne Guard koennte SDF ein "neues PL-Item" melden und IDF Phase 1 neu starten —
das setzt aber den Naming-Counter nicht zurueck und kann Stale-Teams erzeugen.
Recheck-Guard erzwingt: Re-Batches landen direkt in Phase 7, kein Re-Init.

---

## MITOSE-SIGNAL

Wenn ein einzelnes PL-Item zu gross wird (z.B. Aggregat > Schwellwert),
empfiehlt Phase 5 / Phase 7 eine **Mitose** (Spalt-Operation). Berater meldet,
A muss Spec verfeinern. Mitose passiert nicht in IDF — aber das Signal kommt
hier.

---

## MINI-THESE

IDF ist **kein Erfinder**, sondern eine **reine PL-Verwalterin** (nach BL-198).
A liefert das aufbereitete Material (PL-Items aus Phase 5a/5b/5c); IDF schichtet
es in DAG, Cluster und Batch-Plan. Dass IDF nach BL-197/BL-198 die PL-Erzeugung
an A abgibt, ist konsequent: **Wissen erzeugen ist A's Job, Wissen verwalten
und in Batches uebersetzen ist IDF's Job**. Mit dieser Trennung wird IDF zur
**reinen Transformations-Schicht** — sie bringt keine Erkenntnisse hervor,
sie strukturiert was A erkannt hat. Phase 3.7 (modelSync Reverse) ist die einzige
Rueck-Kommunikation: Korrekturen aus dem Parking-Lot fliessen zurueck ins Model.

---

ARGUMENTS: $ARGUMENTS
