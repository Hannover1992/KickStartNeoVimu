---
status: active
version: 0.2.0
type: berater
parent: _A_orchestrate
phase: phase_0.5.2
model_tier: middle
created: 2026-04-25
updated: 2026-04-30
feature_anchor: BL-142
optional: false
changelog_0_2_0: |
  HiL=on STANDARD-PATTERN ergaenzt: Parallel-Assays pro Item (Sonnet) →
  Master-Konsolidierung → /fullPath → /_question EINZELN durchgehen.
  Generalisiert wiederverwendbar fuer Phase 0.5.2 (Findings) UND Phase 4.1b
  (Spec AK-Review). Ableitbar fuer alle HiL-Listen-Reviews.
  Quelle: CaseStudy SemantischePatternLibrary 2026-04-30 (20 Findings → 20 Assays
  → Master-Konsolidierung → /_question pro Finding).
contract:
  reads:
    - {file: "{VAULT}/Backlog/{BL_SLUG}/Crumbs/{NAME}_findings_crumbs.md", path: "Volltext (status=draft)", purpose: "HiL-Review-Eingang (BL-151 Vault-Pfad, gleich wie findingsExtraction.writes)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.derived_name", purpose: "Feature-Anker"}
    - {file: "_session_params.md", path: "GLOBAL_HIL", purpose: "HiL on/off entscheidet AskUserQuestion"}
  writes:
    - {file: "{VAULT}/Backlog/{BL_SLUG}/Crumbs/{NAME}_findings_crumbs.md", path: "Frontmatter status=confirmed + ggf Krumen-Edits", purpose: "Review-Bestaetigung (BL-151 Vault-Pfad)"}
    - {file: ".claude/_parking-lot.md", path: "neue PL-Items (falls aus Review hervorgegangen)", purpose: "Out-of-scope Findings parken"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.findingsReview", purpose: "Review-Resultat (s.u.)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser findingsReview)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.routing_target"}
  calls:
    - "AskUserQuestion (NUR bei GLOBAL_HIL=on) — INV-FACTORY-1 K5-Fix"
---

# _A_berater_findingsReview (Phase 0.5.2 in _A_orchestrate)

> **Zweck:** HiL-Review der draft-Krumen — bestaetigt confirmed-Status, parkt Out-of-Scope in PL.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_findingsReview                                  |
+======================================================================+
|  LIEST:                                                              |
|    {VAULT}/Backlog/{BL_SLUG}/Crumbs/{NAME}_findings_crumbs.md       |
|      (status=draft, BL-151 Vault-Pfad)                              |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      A_PIPELINE_STATE.derived_name                                   |
|    _session_params.md                                                |
|      GLOBAL_HIL                                                      |
|                                                                      |
|  SCHREIBT:                                                           |
|    {VAULT}/Backlog/{BL_SLUG}/Crumbs/{NAME}_findings_crumbs.md       |
|      Frontmatter status=confirmed                                    |
|      ggf Krumen-Edits (Streichung, Verschiebung)                    |
|    .claude/_parking-lot.md (optional)                                |
|      neue PL-Items aus Out-of-Scope-Krumen                          |
|    {WORKING_DIR}/_manifest.md                                                      |
|      BERATER_OUTPUTS.findingsReview = {                              |
|        confirmed_total, parked_total, hil_used                       |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser findingsReview)                         |
|    A_PIPELINE_STATE.routing_target                                   |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 0.5.2 (HiL Review)                      |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Review-Aggregation, kein Volltext-Reasoning;        |
|    HiL traegt die fachliche Last.                                   |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-FR-1: AskUserQuestion NUR bei GLOBAL_HIL=on (K5-Fix)         |
|    INV-FR-2: status=confirmed darf NUR hier gesetzt werden          |
|    INV-FR-3: Schreib-Isolation auf BERATER_OUTPUTS.findingsReview    |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - findings_crumbs.md existiert mit status=draft                   |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - findings_crumbs.md status=confirmed                             |
|    - BERATER_OUTPUTS.findingsReview vollstaendig                     |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_A_berater_findingsReview, args="{NAME}")

Parameter:
  {NAME} - Feature-Name

Ausgabe:
  - findings_crumbs.md status=confirmed
  - BERATER_OUTPUTS.findingsReview
  - Exitcode: 0=OK, 2=FAIL

Logging-Format:
  [A_FX_REVIEW] ENTRY hil={on|off} draft_crumbs={n}
  [A_FX_REVIEW] EXIT duration={ms}ms confirmed={n} parked={k}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  findingsReview:
    confirmed_total: 14
    parked_total: 3
    hil_used: true
    last_berater: "findingsReview"
```

## Logik — zwei Modi nach GLOBAL_HIL

### Modus A: HiL=off (autonom)

```
1. Lies {VAULT}/Backlog/{BL_SLUG}/Crumbs/{NAME}_findings_crumbs.md (status=draft)
   # BL-235 AK-11: traegt die Datei CORE/BORDER-Struktur (vom dispatch_findings-Motor), dann
   # CORE-Destillate ZUERST (weight-absteigend = Headline) reviewen, BORDER als Anhang.
   # CORE-Rang/weight ist das Headline-+Sortier-Signal, das downstream taskDefinition + _model lesen.
2. Auto-Confirm aller Findings (K5-Fix konservativ)
3. status=confirmed setzen
4. BERATER_OUTPUTS.findingsReview.{confirmed_total, parked_total: 0, hil_used: false}
5. RETURN
```

Kein User-Dialog, kein Assay, kein Master-Doku. Pipeline laeuft durch.

---

### Modus B: HiL=on — STANDARD-PATTERN "Assay-Review"

Dieser Pattern ist **wiederverwendbar** und MUSS auch von **Phase 4.1b (Spec AK-Review)**
und allen anderen HiL-Listen-Reviews (Phase B Checkpoints) so umgesetzt werden.

**Ablauf in 4 Schritten:**

```
SCHRITT 1: PARALLEL ASSAYS (Wellen-Spawn pro Item)

  Team Lead spawnt N Sonnet-Worker PARALLEL — einen pro Item (Finding/AK/etc).
  Skalierung: bis zu 10 Worker gleichzeitig (zwei Wellen bei N>10).

  Jeder Worker:
    - Laedt Skill `_assay`
    - Schreibt Mini-Essay (200-400 Woerter, expository oder argumentative)
      zur Frage: "Soll Item {ID} als-ist uebernommen werden, praezisiert, oder dismissed?"
    - Output-Pfad (Vault):
        {VAULT}/Backlog/{FEATURE}/Assays/Assay_{ITEM_ID}_{DATE}.md
    - SendMessage an "team-lead" mit 50-Char-Summary

  Modell-Tier: sonnet (medium) — keine haiku-Floor-Anhebung wie bei Extraction
  noetig, weil Assay reflektiv ist und Textqualitaet braucht.


SCHRITT 2: KONSOLIDIERUNG (Master-Doku)

  Nach Abschluss aller Worker:
    Team Lead konsolidiert alle Assays in EIN Master-Doku mit:
      - Frontmatter (type=findings_review oder ak_review)
      - Executive Summary (Verdict-Verteilung: Uebernehmen/Praezisieren/Dismiss)
      - Verdict-Tabelle (alle Items, eine Zeile, mit Kern-Insight)
      - Cluster-Analyse (thematische Gruppierung)
      - Spec-Phase Action Items (priorisiert)
      - Output-Pfade

    Output-Pfad (Vault):
      {VAULT}/Backlog/{FEATURE}/{TYPE}_Konsolidiert_{DATE}.md


SCHRITT 3: /fullPath AUSGEBEN

  Team Lead ruft Skill `/fullPath` auf um:
    - Vollen Pfad des Master-Doku ins Terminal zu schreiben
    - User kann das Doku per Klick im Editor oeffnen + lesen

  Ohne diesen Schritt geht der User blind in /_question.


SCHRITT 4: /_question EINZELN PRO ITEM

  Pro Item (sequenziell, nicht parallel — User-Aufmerksamkeit):
    Team Lead ruft Skill `/_question` auf:
      - Frage: "Item {ID} — Verdict?"
      - Im question-Feld embedded: ASSAY-Block (aus Schritt 1, gekuerzt auf 200 Woerter)
      - 3-4 Optionen: korrekt | praezisieren | dismiss (+ ggf. Q1/Q2/Q3)
      - User waehlt + ggf. Notes
      - Decision-Rationale wird persistiert in:
        {VAULT}/Backlog/{FEATURE}/Questions/Question_{ITEM_ID}_{DATE}.md

  EINZELN bedeutet: ein /_question pro Item, nicht 4er-Batch.
  Begruendung: Assay-Tiefe pro Item rechtfertigt einzelne Aufmerksamkeit.

---

## Verallgemeinerung — wann diesen Pattern nutzen?

| HiL-Checkpoint | Phase | Items |
|---|---|---|
| Checkpoint A (Findings-Review) | Phase 0.5.2 | Findings F-001..F-NN |
| Checkpoint B (Spec AK-Review) | Phase 4.1b | AK-001..AK-NN |
| (zukuenftig) Checkpoint C-Review | nach Finish | PL-Items (selten, kompakter) |

Phase 4.1b MUSS denselben Pattern aufrufen. `_A_orchestrate` Phase 4 spec
verweist deshalb auf diesen Berater (oder einen Schwester-Berater
`_A_berater_specReview` der dieselbe Logik nutzt) statt eine eigene Variante zu bauen.

---

## INVARIANTEN (HiL=on Pattern)

- INV-HIL-1: Parallel-Assays MUESSEN pro Item geschrieben werden (kein Sammel-Assay)
- INV-HIL-2: Master-Doku MUSS Verdict-Tabelle UND Cluster-Analyse enthalten
- INV-HIL-3: /fullPath MUSS aufgerufen werden VOR /_question (User braucht Klick-Pfad)
- INV-HIL-4: /_question wird EINZELN aufgerufen, nicht in Batches (Tiefe vor Tempo)
- INV-HIL-5: Pattern ist wiederverwendbar — Phase 4.1b ruft denselben Pattern,
  nicht eigene Variante (DRY)

---

## Output-Schema (BERATER_OUTPUTS bei HiL=on)

```yaml
BERATER_OUTPUTS:
  findingsReview:
    hil_used: true
    items_total: 20
    assays_path: "{VAULT}/Backlog/{FEATURE}/Assays/"
    master_doc_path: "{VAULT}/Backlog/{FEATURE}/Findings_Assays_Konsolidiert_{DATE}.md"
    questions_path: "{VAULT}/Backlog/{FEATURE}/Questions/"
    verdicts:
      uebernehmen: 16
      praezisieren: 1
      dismiss: 0
      praezisieren_mit_AK: 4
    last_berater: "findingsReview"
    completed_at: "{DATE}"
```

---

## Begruendung Modell-Tier

sonnet (medium) fuer Assays — kein haiku, weil Assay-Qualitaet reflektive Tiefe
braucht. Keine opus-Anhebung, weil 20 parallele Sonnet-Worker insgesamt
guenstiger und schneller sind als 5 sequenzielle Opus-Calls.

Bei HiL=off ist Auto-Confirm konservativ — kein Modell-Call ueberhaupt.
