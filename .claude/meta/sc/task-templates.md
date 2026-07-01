# SC Task-Beschreibungen (Vorlagen fuer TaskCreate)

**Quelle:** Extrahiert aus `_SC_orchestrate.md` v2.4 → v3.0 (Decomposition)
**Geladen von:** Team Lead beim Erstellen von Tasks (Phase 1.3, Phase 3.3)

---

## Task 0: W_fetch

```
Subject: "Wissen holen (Vault + RAG)"
ActiveForm: "Fetching knowledge from Vault and RAG"
Description: |
  Fuehre /_W_fetch {NAME} aus.

  Suche in Vault UND RAG nach existierendem Wissen zu "{name}".
  Kopiere relevante Models und Wissens-Dokumente in .claude/.
  RAG-only Hits als Referenz notieren.

  Falls Vault nicht konfiguriert: Nur RAG-Suche (degraded mode).

  Input: Task.md (falls vorhanden), User-Keywords
  Output: .claude/models/*.md, .claude/wissen/*.md, _manifest.md

  Melde dem Team Lead:
    - Vault-Hits: {V} Dokumente
    - RAG-Hits: {R} Dokumente
    - BOTH-Hits: {B} Dokumente
    - Kopiert: {N} Dateien nach .claude/
    - "Keine Treffer" falls nichts gefunden
```

---

## Task 1: TaskDefinition

```
Subject: "Aufgabe definieren"
ActiveForm: "Defining task and collecting crumbs"
Description: |
  Fuehre /_taskDefinition {NAME} aus.

  Sammle Material aus .claude/pileOfMud/ (Screenshots, PDFs, alte Models).
  Erstelle Task.md mit Aufgabe, Scope, Erfolgskriterien.
  Erstelle crumbs/{NAME}_crumbs.md mit strukturierten Kruemmeln.

  Falls pileOfMud/ leer: Erstelle Task.md direkt aus dem Kontext.

  Input: .claude/pileOfMud/*, User-Beschreibung, W_fetch-Ergebnisse
  Output: Task.md, crumbs/{NAME}_crumbs.md

  Melde dem Team Lead:
    - Aufgabe in 1-2 Saetzen
    - Scope (was ist DRIN, was ist RAUS)
    - Erfolgskriterien (3-5 Punkte)
```

---

## Task 2: Model (Wellen-Tasks)

HINWEIS: Task 2 ist ein PLATZHALTER. Team Lead erstellt nach Task 1
MEHRERE Wellen-Tasks statt eines einzigen Tasks.

**Easy (Synthese solo):**
```
Subject: "[WORKER-MODE] Model: Welle 3 - Synthese (solo)"
ActiveForm: "Building knowledge model"
Description: |
  [WORKER-MODE] Welle 3: Synthese fuer {NAME} (easy, solo)
  INPUT: crumbs/{NAME}_crumbs.md, Task.md, bestehende Models
  OUTPUT: .claude/models/{NAME}_Model.md
  Frontmatter-Pflicht: wave=synthese, status=final, primaerquelle_gelesen: true
  Aufgabe: Synthetisiere alle Inputs zu finalem Model. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

**Explorer (Welle 1, normal/hard):**
```
Subject: "[WORKER-MODE] Model: Welle 1 - Explorer E{NN} {fokus}"
ActiveForm: "Exploring {fokus} for knowledge model"
Description: |
  [WORKER-MODE] Welle 1: Explorer E{NN} fuer {NAME}
  FOKUS: {fokus_beschreibung}
  INPUT: .claude/crumbs/{NAME}_crumbs.md, Task.md
  OUTPUT: .claude/analysis/exploration/{NAME}-E{NN}-{fokus}.md
  Frontmatter-Pflicht: wave=exploration, agent=E{NN}, status=final, primaerquelle_gelesen: true
  Aufgabe: Kartographiere den Fokus-Bereich. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

**Drafter (Welle 2, normal/hard):**
```
Subject: "[WORKER-MODE] Model: Welle 2 - Drafter D{NN} {fokus}"
ActiveForm: "Drafting {fokus} analysis"
Description: |
  [WORKER-MODE] Welle 2: Drafter D{NN} fuer {NAME}
  FOKUS: {fokus_beschreibung}
  # SP-FIX-1: Stille-Post-Schutz (Explorer nur als Kompass)
  INPUT: .claude/crumbs/{NAME}_crumbs.md, models/{NAME}_Model.md PLUS .claude/analysis/exploration/{NAME}-E*.md (NUR als Kompass)
  STILLE-POST-SCHUTZ: Nutze Explorer-Outputs nur zur Scope-Einteilung. Mache DEINE EIGENE Analyse an den Primaerquellen (Crumbs, Model).
  OUTPUT: .claude/analysis/drafts/{NAME}-model-D{NN}-{fokus}.md
  Frontmatter-Pflicht: wave=drafts, agent=D{NN}, status=final, primaerquelle_gelesen: true
  Aufgabe: Tiefenanalyse des Fokus-Bereichs. Kein Spawning.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

---

## Task 3: SC_observe (Zyklus {C})

```
Subject: "Observe: Findings sammeln (Zyklus {C})"
ActiveForm: "Collecting observations"
Description: |
  Fuehre /_SC_observe aus.

  ACTOR: OBSERVER — sammle Findings OHNE Interpretation.
  Lies Model + vorheriges ERGEBNIS (falls Zyklus > 1).
  Schreibe OBSERVE{C}.md mit Findings.
  Optional: Incidental Findings in _parking-lot.md.

  REVIEW-MODUS (wenn SC_PIPELINE_STATE.modus=REVIEW):
    Vergleiche Code mit Model. Suche Divergenzen:
    - Code-Patterns ohne W{n} (unerklaerter Code)
    - W{n} ohne Code-Entsprechung (nicht implementiert)
    - Quality-Issues (Tests, Naming, Style)
    Findings in post-impl/{NAME}-REVIEW-PROTOKOLL.md, NICHT ins Model.

  Input: models/{NAME}_Model.md, ERGEBNIS{C-1}.md (falls vorhanden)
  Output: analysis/synthese/{NAME}-OBSERVE{C}.md

  Melde dem Team Lead:
    - Anzahl Findings
    - Top 3 Findings (kurz)
    - Incidental Findings: {N} (falls welche)
```

---

## Task 4: SC_modelMaintain (Zyklus {C})

```
Subject: "Model pflegen (Zyklus {C})"
ActiveForm: "Maintaining model"
Description: |
  Fuehre /_SC_modelMaintain aus.

  ACTOR: MODEL-MAINTAINER — pflege das Model.
  Neue W{n} hinzufuegen, GC durchfuehren, ggf. Split ausfuehren.
  Aktualisiere Kap. 6a (Statusaenderungen).

  REVIEW-MODUS (wenn SC_PIPELINE_STATE.modus=REVIEW):
    Reparatur-Findings → post-impl/{NAME}-REVIEW-PROTOKOLL.md (NICHT ins Model)
    Nur strukturelle Erkenntnisse die das Model AENDERN muessen → als W{n} ins Model
    Bug-Fixes, Refactoring-Hints, Style-Issues → post-impl/ Protokoll

  Input: Model.md, OBSERVE{C}.md, ERGEBNIS{C-1}.md
  Output: Model.md (UPDATE), ggf. Model-Topologie.md
         [REVIEW: + post-impl/{NAME}-REVIEW-PROTOKOLL.md]

  Melde dem Team Lead:
    - Neue W{n}: {N}
    - GC: {N} WIDERLEGT, {N} ELIMINIERT
    - Split: Ja/Nein (falls Trigger)
    - Gesamte W{n}: {total} AKTIV
```

---

## Task 5: SC_qualityGate (Zyklus {C})

```
Subject: "Quality Gates pruefen (Zyklus {C})"
ActiveForm: "Running quality gates"
Description: |
  Fuehre /_SC_qualityGate aus.

  ACTOR: QUALITY-GATE — 5 Gates pruefen (6 bei REVIEW-Modus):
    Gate 1: Battle-Royale (SRS-Trend, Anti-Patterns R-AP1..R-AP5)
           [REVIEW-Modus: DEAKTIVIERT, ersetzt durch Gate 6]
    Gate 2: Kohaesion (W{n}/TC Ratio, Split-Trigger)
    Gate 3: Feature-Abschluss (Coverage-%)
           [REVIEW-Modus: Code-Quality Coverage statt W{n} Coverage]
    Gate 4: Blind-Spot-Detection (T1-T5 Muster)
    Gate 5: Stagnation (Schwellen, ABORT-Empfehlung)
    Gate 6: Post-Implementation-Reality-Check (NUR bei REVIEW-Modus)
           → Code↔Model Konsistenz, W{n} Coverage im Code, unerklaerter Code

  Input: Model.md, OBSERVE{C}.md, ERGEBNIS{C-1}.md, Model-Topologie
  Output: analysis/synthese/{NAME}-QUALITYGATE{C}.md

  WICHTIG: Melde dem Team Lead:
    - Gate 1-5 Ergebnisse (PASS/WARN/FAIL pro Gate)
    - Feature-Coverage: {X}%
    - Stagnation: {zaehler}
    - BSD-Trigger: Ja/Nein (welches T-Muster)
    - Empfehlung: CONTINUE / DONE / ESCALATE
```

---

## Task 6: SC_hypothese (Zyklus {C})

```
Subject: "Hypothese formulieren (Zyklus {C})"
ActiveForm: "Formulating hypothesis"
Description: |
  Fuehre /_SC_hypothese aus.

  ACTOR: HYPOTHESEN-FORMULIERER — KREATIVE Phase.
  Sektion 0: GC-Pruefung (PFLICHT ab Zyklus 2).
  Sektion 1: Genau 1 falsifizierbare Hypothese.
  Verifikations-Kriterium V1-V5 + Scope-Deklaration.

  Input: Model.md, QUALITYGATE{C}.md
  Output: analysis/synthese/{NAME}-HYPOTHESEN.md (UPDATE/APPEND)

  Melde dem Team Lead:
    - Hypothese in 1 Satz
    - Scope: {welche Dateien/Module betroffen}
    - Verifikations-Plan: {V1-V5 zusammengefasst}
    - GC: {N} Hypothesen als WIDERLEGT/ELIMINIERT markiert
```

---

## Task 7: Implementieren (Zyklus {C}) — MODUS-ABHAENGIG

**FULL-Modus (Default):**

Team Lead startet /_I_orchestrate als EIGENEN ORCHESTRATOR (Grosser Zyklus).
→ Lies `.claude/meta/sc/symbiose-protocol.md` fuer SYMBIOSE-Details.

```
Team Lead:
  1. SC-Zyklus pausieren (SC_PIPELINE_STATE.stufe: "I_orchestrate")
  2. /_I_orchestrate {NAME} {difficulty} {ceiling} {floor} starten
     → Eigenes Team, eigene Tasks
     → Volle I-Pipeline laeuft durch (core bei SYMBIOSE)
  3. Nach I-Pipeline-Abschluss: SC-Zyklus fortsetzen
     → sc-{name}-ergebnis spawnen

Manifest waehrend I-Pipeline:
  SC_PIPELINE_STATE.stufe: "I_orchestrate"
  SC_PIPELINE_STATE.i_pipeline_active: true
```

**INLINE-Modus (-I):**

```
Subject: "Implementieren (Zyklus {C})"
ActiveForm: "Implementing changes (inline)"
Description: |
  Fuehre /_SC_implement aus.

  ACTOR: IMPLEMENTIERER — genau 1 IC pro Durchgang.
  Horizontale Suche: Pattern-Matching im gleichen Layer.
  Soft-Limits: 5 Dateien, 100 LOC.
  Verifikations-Anleitung: 3-5 konkrete Test-Schritte.

  Input: HYPOTHESEN.md, Model.md, Pattern-Library
  Output: Code-Aenderungen, HYPOTHESEN.md (aktualisiert)

  Melde dem Team Lead:
    - IC: {was implementiert wurde}
    - Dateien geaendert: {N}
    - LOC: +{added} / -{removed}
    - Verifikation: {bestanden/fehlgeschlagen}
    - Hypothese: BESTAETIGT / WIDERLEGT / OFFEN
```

**REVIEW-Modus:** Task 7 wird UEBERSPRUNGEN (kein Implement im Review-Modus).
**ANALYSE-Modus:** Task 7 wird UEBERSPRUNGEN (kein Implement im Analyse-Modus).

---

## Task 8: SC_ergebnis (Zyklus {C})

```
Subject: "Ergebnis sammeln (Zyklus {C})"
ActiveForm: "Collecting results"
Description: |
  Fuehre /_SC_ergebnis aus.

  ACTOR: ERGEBNIS-SAMMLER — DATENBANK-MODUS.
  Drei-Kategorien-Regel:
    ROHDATEN: sammeln, zaehlen, woertlich zitieren
    MECHANISCHE ABLEITUNG: Formeln, Zaehler, boolesche Ausdruecke
    INTERPRETATION: VERBOTEN (gehoert in /_SC_observe)

  SRS-Messung + Widerlegungs-Marker + Stagnations-Check.

  Input: HYPOTHESEN.md, Model.md, vorheriges ERGEBNIS, Logs/Tests
  Output: analysis/synthese/{NAME}-ERGEBNIS{C}.md

  WICHTIG — Melde dem Team Lead AUSFUEHRLICH:
    - SRS-Score: {score}
    - SRS-Trend: {steigend|fallend|stagnierend}
    - Offene W{n}: {N} AKTIV, {M} ZUR_PRUEFUNG
    - Widerlegte W{n}: {N} neu in diesem Zyklus
    - Stagnations-Zaehler: {zaehler}
    - Fortschritt: STARK / SCHWACH / KEINER
    Team Lead entscheidet basierend auf diesen Daten.
```

---

## Task 9: W_push_temp (strategisch)

```
Subject: "Wissen temporaer pushen (nach Zyklus {C})"
ActiveForm: "Pushing knowledge to RAG"
Description: |
  Fuehre /_W_push_temp auto aus.

  Strategischer Push nach jedem Zyklus:
  → Model, OBSERVE, ERGEBNIS in local_knowledge_{feature_id}
  → Sichert Zwischen-Wissen fuer spaetere W_fetch-Aufrufe

  Input: .claude/models/*.md, .claude/analysis/synthese/*
  Output: RAG local_knowledge_{feature_id}, _manifest.md

  Melde dem Team Lead:
    - Dokumente gepusht: {N}
    - Chunks erstellt: {total}
    - Collection: local_knowledge_{feature_id}
```

---

## Task 10: W_push_orchestrate (Post-Cycle)

```
Subject: "Wissens-Push orchestrieren"
ActiveForm: "Orchestrating knowledge push"
Description: |
  Fuehre /_W_push_orchestrate {NAME} {difficulty} {ceiling} {floor} aus.

  Eigener Orchestrator fuer den POST-CYCLE Wissens-Push.
  Erstellt eigenes Team, spawnt kurzlebige Agents pro Step:
    1. /_model {NAME} finish (Model konsolidieren)
    2. /_gap {NAME} (Finaler IST vs SOLL Vergleich)
    3. /_W_push_global auto (Quality Gate + RAG push)
    4. /_W_modelSplit {NAME} (Thematisch splitten)
    5. /_W_sync_orchestrate {NAME} {difficulty} --co-work (Vault sync)
    6. /_retrospektive {NAME} (Wissenstransfer)

  Melde dem Team Lead:
    - Alle 6 Steps abgeschlossen
    - GAP: {X}% (IST vs SOLL)
    - RAG: global_knowledge gepusht
    - Vault: synchronisiert
```

---

## Task 11: Feature finalisieren (Post-Cycle)

```
Subject: "Feature finalisieren"
ActiveForm: "Finalizing feature"
Description: |
  Fuehre /_finish {NAME} aus.

  HINWEIS: ImplementationHandOff bereits vorhanden:
    {VAULT}/Backlog/{BL_SLUG}/SC/{NAME}-HANDOFF.md  # BL-151 + PL-D 2026-05-07
    → Nutze HandOff fuer Scope-Verifikation und offene Aufgaben.

  HANDOFF-Konsumption und Gate-Antwort (EC-6, W181):
  _I_orchestrate fuehrt Schritt 0.4 aus (HANDOFF-Konsumption):
    0.4a-0.4b: HANDOFF.md lesen (alle 8 Sektionen)
    0.4c:      Pflicht-Sektionen pruefen
               Fehlen Pflicht-Sektionen → i_gate_response: reject_needs_more_sc → ABORT
    0.4d-0.4g: Extraktion in handoff_context + Flags setzen

  SC-Recovery-Auswertung (naechster Zyklus falls noetig):
    IF i_sc_return.triggered == true:
      → sc_recommendations lesen
      → recovery_cycle_count pruefen (Max: 2)
      → pipeline_mode: SC_RECOVERY
      → Neue Zyklen mit w_focus_list aus refuted_wn

  Offene Items pruefen: Parking-Lot, Task.md ECs/TCs, Model W{n}.
  Pro Item: PARKEN / DISCARD / ERLEDIGT (HiL).
  Manifest: PHASE=READY.

  Melde dem Team Lead:
    - Geparkt: {N} Items
    - Verworfen: {M} Items
    - Naechste Optionen fuer User
```

---

## Wellen-Task-Skalierung (Referenz)

| difficulty | Welle 1 (Explorer/Drafter/Sammler) | Welle 2 (Drafter/Synthese) | Welle 3 (Synthese) |
|------------|-----------------------------------|---------------------------|-------------------|
| easy | --- | --- | 1 {ceiling} (solo) |
| normal | 5/3/5 {floor}/{middle} PARALLEL | 3/1/1 {middle}/{ceiling} PARALLEL | 1 {ceiling} |
| hard | 9/5/9 {floor}/{middle} PARALLEL | 5/1/1 {middle}/{ceiling} PARALLEL | 1 {ceiling} |

Gilt fuer: _model (Task 2), _SC_observe (Task 3), _SC_ergebnis (Task 8), _spec (A-Pipeline).

---

## Wellen-Task-Vorlagen (Command-spezifisch)

### _SC_observe Wellen-Tasks

**Observer-Drafter (Welle 1, normal/hard):**
```
Subject: "[WORKER-MODE] Observe: Drafter D{NN} {fokus} (Zyklus {C})"
ActiveForm: "Observing {fokus} for cycle {C}"
Description: |
  [WORKER-MODE] Observer-Drafter D{NN} fuer {NAME} (Zyklus {C})
  FOKUS: {fokus_beschreibung}
  Lies /_SC_observe Sektion "Worker-Vertrag: Observer-Drafter" fuer Fokus-Beschreibung D{NN}.
  INPUT: models/{NAME}_Model.md, synthese/{NAME}-ERGEBNIS{C-1}.md (falls vorhanden), synthese/{NAME}-GAP.md (falls vorhanden)
  OUTPUT: .claude/analysis/drafts/{NAME}-observe{C}-D{NN}-{fokus}.md
  Frontmatter-Pflicht: wave=drafts, agent=D{NN}, status=final
  G-UNTRACKED (PFLICHT, W92): Pruefe git-Status vor W{n}-Formulierung.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

**Observer-Synthese (Welle 2):**
```
Subject: "[WORKER-MODE] Observe: Synthese (Zyklus {C})"
ActiveForm: "Synthesizing observations for cycle {C}"
Description: |
  [WORKER-MODE] Observer-Synthese fuer {NAME} (Zyklus {C})
  Lies /_SC_observe Sektion "Worker-Vertrag: Observer-Synthese".
  INPUT: .claude/analysis/drafts/{NAME}-observe{C}-D*.md (ALLE)
  OUTPUT: .claude/analysis/synthese/{NAME}-OBSERVE{C}.md
  Konsolidiere Findings, dedupliziere, F-Nummern vereinheitlichen.
  KEINE Interpretation, KEINE Model-Updates.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

### _SC_ergebnis Wellen-Tasks

**Ergebnis-Sammler (Welle 1, normal/hard):**
```
Subject: "[WORKER-MODE] Ergebnis: Sammler DS{NN} {quellen} (Zyklus {C})"
ActiveForm: "Collecting data from {quellen} for cycle {C}"
Description: |
  [WORKER-MODE] Ergebnis-Sammler DS{NN} fuer {NAME} (Zyklus {C})
  QUELLEN: {quellen_beschreibung}
  Lies /_SC_ergebnis Sektion "Worker-Vertrag: Ergebnis-Sammler" fuer Fokus-Beschreibung DS{NN}.
  INPUT: _manifest.md, synthese/{NAME}-HYPOTHESEN.md
  OUTPUT: .claude/analysis/synthese/{NAME}-DATA{C}-DS{NN}.md
  Frontmatter-Pflicht: wave=datensammlung, agent=DS{NN}, status=final
  NUR zugewiesene Quellen sammeln. KEINE Interpretation.
  Kein Manifest-Update (macht Synthese-Agent).
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

**MODELL-OVERRIDE:** Sammler verwenden DOWNGRADE-Modell (siehe _SC_orchestrate "Modell-Override fuer _SC_ergebnis").

**Ergebnis-Synthese (Welle 2):**
```
Subject: "[WORKER-MODE] Ergebnis: Synthese + SRS (Zyklus {C})"
ActiveForm: "Synthesizing results for cycle {C}"
Description: |
  [WORKER-MODE] Ergebnis-Synthese fuer {NAME} (Zyklus {C})
  Lies /_SC_ergebnis Sektion "Worker-Vertrag: Ergebnis-Synthese".
  INPUT: .claude/analysis/synthese/{NAME}-DATA{C}-DS*.md (ALLE), HYPOTHESEN.md, Model.md (DB-Modus)
  OUTPUT: .claude/analysis/synthese/{NAME}-ERGEBNIS{C}.md
  Konsolidiere Rohdaten, berechne SRS, Widerlegungs-Marker, Stagnation.
  Manifest aktualisieren (Pattern C).
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

### _spec Wellen-Tasks

**Spec-Drafter (Welle 1, normal/hard):**
```
Subject: "[WORKER-MODE] Spec: Drafter D{NN} {fokus}"
ActiveForm: "Extracting {fokus} for specification"
Description: |
  [WORKER-MODE] Spec-Drafter D{NN} fuer {NAME}
  FOKUS: {fokus_beschreibung}
  Lies /_spec Sektion "Worker-Vertrag: Spec-Drafter" fuer Fokus-Beschreibung D{NN}.
  INPUT: crumbs/{NAME}_crumbs.md, Task.md
  OUTPUT: .claude/analysis/drafts/{NAME}-spec-D{NN}-{fokus}.md
  Frontmatter-Pflicht: wave=drafts, agent=D{NN}, status=final
  EXTRAHIERE aus Kruemmeln, ERFINDE NICHT.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```

**Spec-Synthese (Welle 2):**
```
Subject: "[WORKER-MODE] Spec: Synthese"
ActiveForm: "Synthesizing specification"
Description: |
  [WORKER-MODE] Spec-Synthese fuer {NAME}
  Lies /_spec Sektion "Worker-Vertrag: Spec-Synthese".
  INPUT: .claude/analysis/drafts/{NAME}-spec-D*.md (ALLE)
  OUTPUT: .claude/specs/{NAME}_Spec.md
  Konsolidiere Architektur-Vorgaben, erstelle Ziel-Architektur-Diagramm.
  Wenn fertig: TaskUpdate completed + SendMessage an Team Lead.
```
