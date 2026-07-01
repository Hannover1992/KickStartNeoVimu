---
status: active
version: 1.0.0
type: berater
parent: _IDF_orchestrate
phase: "7.6"
model_tier: middle
actor: _IDF_orchestrate Phase 7.6 — NACH stagePlanner, VOR IDF_DONE
created: 2026-05-10
updated: 2026-05-10
feature: BL-172
ak_implements: [AK-1, AK-2, AK-3]
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.per_pl_evaluation", purpose: "BL-312 AK-3: PRIMAERE SRS-QUELLE — Per-PL-Item-Vektor {srs, k_score, bottleneck} von plBewertung (Phase 3.8, ERST+EINZIG-SRS-Rechner). metric_per_batch.srs_* wird HIERAUS aggregiert (nicht mehr aus K-SCORE.md srs_pro_ak). Single-Source fuer SRS — beseitigt die DREI-Quellen-Drift (smt229)."}
    - {file: "{WORKING_DIR}/4_K-Score/*-K-SCORE.md", path: "ak_details", purpose: "BL-312 AK-3: NUR NOCH K-QUELLE fuer AK-keyed items — Per-AK k_score_pro_ak als Fallback wenn per_pl_evaluation[item_id].k_score=null (Bottleneck-Items oder AK-keyed Batches). BL-402 AK-1: per_pl_evaluation.k_score ist PRIMAER fuer PL-keyed items (Story-Aggregat-Fallback ist Fehler-Zustand). srs_pro_ak wird fuer SRS NICHT mehr gelesen (SRS = per_pl_evaluation)."}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items_per_batch", purpose: "Sub-Batch-Mapping AK/PL→Batch (PFLICHT-Input von Phase 7)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE", purpose: "k_aufwand/k_kopplung/k_fragilitaet (Story-Level K-Fallback bei fehlendem Per-AK)"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.metric_per_batch", purpose: "Per-Sub-Batch K-Score/SRS-Aggregation {batch_N: {srs_max, srs_avg, k_score_max, k_score_avg, items_count, items_with_data}} fuer SDF Phase 1.1 Konsumption"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.metricPlanner", purpose: "Audit-Slot mit Aggregations-Methode + Per-Batch-Werte"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items (Phase 7-Output)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items_per_batch", note: "BL-313 AK-2: metricPlanner ist KONSUMENT von batch_items_per_batch (LIEST es, reads-Block Z16/Z59). OWNER = batchPlanner/Phase-7. Das 'Beispiel :362'-Vorkommen ist ein Beispiel-Block, KEINE Ownership-Deklaration (anker_drift_check). Single-Source: genau 1 Owner = batchPlanner/Phase-7."}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_mode_hints", note: "BL-313 AK-2/AK-3: Owner = batchPlan (SCHRITT 5b Happy-Path-Producer). metricPlanner schreibt es NICHT."}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_stages (Phase 7.5-Output, Owner = stagePlanner)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.k_score_aggregate (Story-Level, von batchPlanner)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.srs_aggregate (Story-Level, von batchPlanner)"}
---

# _IDF_berater_metricPlanner (Phase 7.6)

## Zweck

**SRP-Trennung von BL-172:** batchPlan macht Batches, stagePlanner macht Stages,
metricPlanner macht **Per-Batch-Metriken**.

Pro Sub-Batch aggregiert metricPlanner per-Item-Werte zu Sub-Batch-Aggregaten.
Damit kann SDF Phase 1.1 `_SDF_berater_modusEntscheidung` per-Batch-Modus-
Entscheidungen treffen statt auf Story-Aggregat zurueckgreifen zu muessen
(BL-151-FIX-Override-Anti-Pattern).

**BL-312 AK-3 — Single-Source-Naht (SRS):**
- **SRS** wird aus `DF_BATCH_STATE.per_pl_evaluation` (PRIMAER) aggregiert — dem
  Output von Phase 3.8 plBewertung (ERST+EINZIG-SRS-Rechner, BL-312 AK-1). NICHT
  mehr aus `K-SCORE.md` `ak_details.srs_pro_ak`. EINE SRS-Quelle, kein Drift
  (beseitigt die smt229-DREI-Quellen-Divergenz: K-SCORE.md differenziert vs
  srs_pro_ak-Frontmatter 0-uniform vs per_pl_evaluation 100-uniform).
- **K-Score** wird ab BL-402 PRIMAER aus `DF_BATCH_STATE.per_pl_evaluation[item_id].k_score`
  gelesen fuer PL-keyed items (analog der SRS-Single-Source-Naht — derselbe Vektor von
  plBewertung 3.8c). Fallback auf `K-SCORE.md` `ak_details.k_score_pro_ak` fuer AK-keyed
  items oder Bottleneck-Items (k_score=None). Die vollstaendige K-Single-Source-Naht ist
  DEFERRED bis AK-10/BL-311 (Code-K-Skala kanonisieren).

Output: `DF_BATCH_STATE.metric_per_batch = {batch_1: {srs_max:95, srs_avg:95.0, k_score_max:50, k_score_avg:50.0, ...}, ...}`
Map fuer SDF Phase 1.1 (BL-165 INV-MODUS-1) saubere Modus-Entscheidung pro Batch.

## VERTRAG

```
╔════════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _IDF_berater_metricPlanner (Phase 7.6) — BL-172 SRP-Refactor ║
╠════════════════════════════════════════════════════════════════════════╣
║  POSITION:                                                              ║
║    NACH Phase 7.5 stagePlanner (batch_stages existiert)                ║
║    VOR  Phase 8 IDF_DONE                                                ║
║                                                                         ║
║  LIEST:                                                                 ║
║    DF_BATCH_STATE.per_pl_evaluation  (BL-312 AK-3: PRIMAERE SRS-Quelle) ║
║      → per_pl_evaluation[pl_id].srs   (von plBewertung 3.8, Single-Ort) ║
║    {WORKING_DIR}/4_K-Score/*-K-SCORE.md  (ak_details — NUR NOCH K)      ║
║      → ak_details[AK-X].k_score_pro_ak  (K-Aggregation; deferred AK-10) ║
║      (srs_pro_ak wird fuer SRS NICHT mehr gelesen — BL-312 AK-3)        ║
║    DF_BATCH_STATE.batch_items_per_batch  (von Phase 7)                 ║
║    A_PIPELINE_STATE.k_aufwand/k_kopplung/k_fragilitaet  (K-Fallback)   ║
║                                                                         ║
║  SCHREIBT:                                                              ║
║    DF_BATCH_STATE.metric_per_batch       (PRIMAER)                     ║
║    BERATER_OUTPUTS.metricPlanner         (Audit-Slot)                  ║
║                                                                         ║
║  INVARIANTEN:                                                          ║
║    INV-METRIC-1: SDF Phase 1.1 _SDF_berater_modusEntscheidung MUSS     ║
║                  metric_per_batch[current_sub_batch_id] lesen, NICHT    ║
║                  k_score_aggregate / srs_aggregate (Story-Level)        ║
║                  als Modus-Entscheidungs-Basis.                         ║
║                  Fallback NUR mit explicit WARN-Log.                    ║
║    INV-METRIC-2: Aggregation-Methode autoritativ:                       ║
║                  - srs:      MAX  (worst-case-driver fuer Modus)        ║
║                  - k_score:  AVG + MAX  (beide Slots, SDF waehlt)       ║
║                  Begruendung: ein high-risk-AK im Batch reisst Modus    ║
║                  hoch. Effort dagegen avg-aussagekraeftig.              ║
║                  [BL-205] srs = w_offen/w_total×100 (Epistemik)         ║
║                  Orthogonal zu K-Score — keine zirkulaere Abhaengigkeit.║
║    INV-METRIC-SRS-SRC (BL-312 AK-3): SRS-Aggregation liest             ║
║                  AUSSCHLIESSLICH DF_BATCH_STATE.per_pl_evaluation[pl].srs║
║                  (plBewertung 3.8 = Single-SRS-Ort). K-SCORE.md         ║
║                  srs_pro_ak ist KEINE SRS-Quelle mehr. K-Aggregation    ║
║                  liest weiter K-SCORE.md k_score_pro_ak (deferred AK-10)║
║    INV-METRIC-K-SRC (BL-402 AK-3): K-Aggregation liest                 ║
║                  per_pl_evaluation[item_id].k_score ALS PRIMAER fuer    ║
║                  PL-keyed items. Fallback: ak_details.k_score_pro_ak    ║
║                  fuer AK-keyed items ODER wenn per_pl_eval.k_score=null ║
║                  (Bottleneck-Items, Phase 3.8c). Story-Aggregat-Fallback║
║                  (special_flags=story_fallback_k_score) = Fehler-Zustand║
║                  fuer PL-keyed Batches, nicht Normal-Zustand. [BL-402]  ║
║    INV-METRIC-3: Items mit srs=null (kein per_pl_evaluation-Eintrag /   ║
║                  FE-only / Spec-skip) werden aus SRS-Aggregation         ║
║                  excluded. items_with_data zaehlt nur non-null.          ║
║    INV-METRIC-4: items_count = |batch_items_per_batch[batch_X]|         ║
║                  items_with_data <= items_count (immer)                 ║
║                  Bei items_with_data == 0 → Warn + Fallback auf Story.  ║
║    INV-METRIC-5: metric_per_batch.keys() == batch_items_per_batch.keys()║
║                  (jeder Sub-Batch hat einen Eintrag, auch leere)        ║
║                  BL-313 AK-2: das ist eine KONSUMENTEN-Relation —       ║
║                  metricPlanner LIEST batch_items_per_batch (Owner =     ║
║                  batchPlanner/Phase-7) und SCHREIBT NUR metric_per_batch.║
║                  metricPlanner OWNT batch_items_per_batch NICHT.        ║
║                                                                         ║
║  CONTRACT-OWNERSHIP (BL-313 AK-2 — Single-Source pro Feld):            ║
║    batch_items_per_batch → batchPlanner/Phase-7  (metricPlanner LIEST) ║
║    batch_mode_hints      → batchPlan (SCHRITT 5b, ADVISORY)            ║
║    batch_stages          → stagePlanner (Phase 7.5)                    ║
║    metric_per_batch      → metricPlanner (DIESER Berater, exklusiv)    ║
║    (Jedes geist5-Pflicht-Feld hat genau 1 dokumentierten Owner.)       ║
║                                                                         ║
║  ACTOR:                                                                 ║
║    _IDF_orchestrate Phase 7.6 — Skill(_IDF_berater_metricPlanner)      ║
║                                                                         ║
║  MODELL-TIER: middle (sonnet) — YAML-Parsing + Aggregations-Math       ║
║                                                                         ║
║  EXIT-CODES:                                                           ║
║    0 = SUCCESS (metric_per_batch fuer alle Sub-Batches geschrieben)    ║
║    1 = WARN (mind. 1 Sub-Batch ohne Per-AK-Daten — Story-Fallback)     ║
║    2 = FAIL (K-SCORE.md nicht lesbar oder DF_BATCH_STATE corrupt)      ║
╚════════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_IDF_berater_metricPlanner, args="{BL_ID}")

Vorbedingung (alle PASS, sonst SKIP/FAIL):
  - DF_BATCH_STATE.batch_items_per_batch != null  (Phase 7 DONE)
  - DF_BATCH_STATE.per_pl_evaluation != null  (BL-312 AK-3: Phase 3.8 plBewertung DONE
    — PRIMAERE SRS-Quelle. Phase 3.8 laeuft VOR Phase 7 im IDF-Flow, also normalerweise
    erfuellt. Fehlt es → SRS-Story-Fallback + WARN, SRS NICHT aus K-SCORE.md srs_pro_ak.)
  - {WORKING_DIR}/4_K-Score/*-K-SCORE.md vorhanden (K-Quelle, deferred AK-10 — A-4k DONE)
```

## PFAD-RESOLUTION

K-SCORE.md liegt im **Vault-BL-Folder**, nicht im Repo:

```
{WORKING_DIR}/4_K-Score/{STORY_NAME}-K-SCORE.md
```

Wobei `{WORKING_DIR}` = Vault-BL-Folder (z.B. `C:/Users/.../DCS/DCSRE/Backlog/DCSRE-486-...analyse/`)
und `{STORY_NAME}` = z.B. `DCSRE-486_QDVTPSelbstauskunftBearbeiten_Analyse`.

**Discovery via Glob:**
```
ks_files = glob({WORKING_DIR}/4_K-Score/*-K-SCORE.md)
assert len(ks_files) == 1, "INV-METRIC-1: genau 1 K-SCORE-Datei pro Story"
ks_file = ks_files[0]
```

## Logik

### SCHRITT 1: K-SCORE.md parsen

```
ks_content = Read(ks_file)
ks_yaml    = parse_frontmatter_yaml(ks_content)  # Frontmatter-Header
# Note: K-SCORE.md hat ak_details + aggregat als TOP-LEVEL YAML-Frontmatter,
# nicht als Body-Markdown. Beispiel-Struktur:
#   ak_details:
#     AK-1: {srs_pro_ak: 90, k_score_pro_ak: 55, anchors: [...], model_refs: [...]}
#     AK-2: {srs_pro_ak: 85, k_score_pro_ak: 50, ...}
#     AK-7: {srs_pro_ak: null, k_score_pro_ak: null, ...}  # FE-only oder Spec-skip
#     ...
#   aggregat:
#     k_aufwand: 50, k_kopplung: 40, k_fragilitaet: 55, srs: 94, k_score: 49
# BL-312 AK-3: ak_details.srs_pro_ak / aggregat.srs werden NUR NOCH als SRS-STORY-FALLBACK
# (aggregat.srs) herangezogen, NICHT mehr als primaere Per-Item-SRS. Per-Item-SRS = per_pl_evaluation.
# k_score_pro_ak / aggregat.k_score bleiben die K-Quelle (deferred AK-10/BL-311).

ak_details = ks_yaml.ak_details          # BL-312 AK-3: NUR NOCH K-Quelle (k_score_pro_ak)
aggregat   = ks_yaml.aggregat
batches    = DF_BATCH_STATE.batch_items_per_batch

# BL-312 AK-3: per_pl_evaluation = PRIMAERE SRS-Quelle (von plBewertung 3.8, Single-Ort).
# Map {pl_id: {srs, k_score, bottleneck, ...}}. Im IDF-Flow laeuft 3.8 VOR Phase 7.6,
# also normalerweise befuellt. Fehlt es → SRS-Story-Fallback (NICHT srs_pro_ak).
per_pl_eval = DF_BATCH_STATE.per_pl_evaluation ?? null
```

### SCHRITT 2: Pro Sub-Batch aggregieren

```
metric_per_batch = {}
warn_count = 0

# BL-266 w_status_set-Quelle: ak_details fuehrt bereits `model_refs_status` pro AK ({W{n}: status}, Z936/942)
# — KEIN zweiter Model.md-Parser noetig (DRY). Vokabular = srs_conventions.md AK-5 (12 Werte inkl.
# experiment_provable). Voraussetzung: der ak_details-Writer (_K_score / _A_berater_akExtraktion) muss den
# ECHTEN W-Status (inkl. experiment_provable) in model_refs_status fuehren, nicht nur open/confirmed/superseded
# — sonst feuert der M5-Kategorie-Trigger nie (Upstream-Vollstaendigkeit, BL-266 Folge-Notiz).

FOR batch_key, batch_items IN batches.items():
  # Sammle Per-AK-Werte fuer diesen Batch
  srs_values     = []
  k_score_values = []
  items_with_data = 0
  batch_w_status   = set()    # BL-266: W{n}-Status-Menge des Batches (experiment_provable-Trigger BL-239 AK-2)
  batch_srs_srcs   = set()    # BL-266: srs_source-Provenance der Batch-AKs (BL-239 AK-6)

  FOR item_id IN batch_items:
    # item_id kann "AK-1"/"AK-CTX-2" (AK-Granularitaet) ODER eine PL-Item-ID sein.

    # ── K-Quelle: per_pl_evaluation PRIMAER fuer PL-keyed items (BL-402 AK-1 Proper-Fix) ──
    # Analog BL-312 AK-3 SRS-Umstellung: per_pl_evaluation[pl_id].k_score von plBewertung
    # 3.8c (nur wenn NOT bottleneck, sonst null). Fallback auf ak_details fuer AK-keyed items
    # ODER wenn per_pl_eval kein k_score hat (Bottleneck-Items). K-SCORE.md ist nur noch
    # K-Quelle fuer items, die NICHT in per_pl_eval stehen (z.B. rein AK-keyed Batches).
    pl_eval = (per_pl_eval.get(item_id) IF per_pl_eval != null ELSE null)
    pl_k    = (pl_eval.k_score IF pl_eval != null AND pl_eval.k_score != null ELSE null)

    ak_data = ak_details.get(item_id)
    ak_k    = (ak_data.k_score_pro_ak IF ak_data != null ELSE null)

    # Primaer: per_pl_evaluation.k_score; Fallback: ak_details.k_score_pro_ak [BL-402 AK-1]
    k = pl_k ?? ak_k

    # ── SRS-Quelle: per_pl_evaluation (BL-312 AK-3 — PRIMAER, plBewertung 3.8 Single-Ort) ──
    # srs_pro_ak aus ak_details wird NICHT mehr fuer SRS gelesen.
    # pl_eval bereits oben gelesen (Re-Bind redundant, pl_eval == per_pl_eval.get(item_id)).
    srs = (pl_eval.srs IF pl_eval != null ELSE null)
    IF per_pl_eval == null:
      Logge: "[metricPlanner] WARN — {batch_key}: per_pl_evaluation fehlt (Phase 3.8 noch nicht gelaufen?) — SRS-Story-Fallback"
    ELIF pl_eval == null:
      Logge: "[metricPlanner] WARN — {batch_key}: item={item_id} nicht in per_pl_evaluation — SRS fuer dieses Item fehlt"

    IF k == null AND pl_eval == null:
      # k=null: weder per_pl_eval.k_score noch ak_details.k_score_pro_ak vorhanden.
      # pl_eval=null: auch kein SRS-Eintrag. Item komplett undokumentiert.
      Logge: "[metricPlanner] WARN — {batch_key}: item={item_id} weder in per_pl_evaluation noch K-SCORE.md (k=null, srs=null)"
      CONTINUE

    # BL-266 w_status_set: die W{n}-Status der Batch-Items aus ak_data.model_refs_status einsammeln (RETRACTED
    # ausschliessen, Konsistenz srs_compute INV-STATUS-2). Speist den experiment_provable→M5-Trigger (4.5a).
    FOR w_ref, st IN ((ak_data.model_refs_status IF ak_data != null ELSE {}) ?? {}).items():
      IF st != null AND st != "RETRACTED":
        batch_w_status.add(st)
    # BL-266/BL-312 srs_source: Provenance pro Item. SRS kommt jetzt aus plBewertung (srs_compute-Engine).
    batch_srs_srcs.add((pl_eval.srs_source IF pl_eval != null ELSE null) ?? "srs_compute")

    IF srs != null:
      srs_values.append(srs)
    IF k != null:
      k_score_values.append(k)

    IF srs != null OR k != null:
      items_with_data += 1

  # Aggregation (INV-METRIC-2)
  IF len(srs_values) > 0:
    srs_max = max(srs_values)
    srs_avg = round(sum(srs_values) / len(srs_values), 1)
  ELSE:
    srs_max = aggregat.srs   # Story-Fallback (INV-METRIC-3)
    srs_avg = aggregat.srs
    warn_count += 1

  IF len(k_score_values) > 0:
    k_score_max = max(k_score_values)
    k_score_avg = round(sum(k_score_values) / len(k_score_values), 1)
  ELSE:
    k_score_max = aggregat.k_score
    k_score_avg = aggregat.k_score
    warn_count += 1

  # BL-266 Aggregation der neuen Felder:
  #   w_status_set    = sorted Liste (YAML-serialisierbar; Consumer nutzt IN-Test) — experiment_provable-Trigger
  #   srs_source      = OR-dominant: "hand_authored" wenn IRGENDEIN AK so markiert, sonst "srs_compute"
  #                     (pessimistisch: untrusted dominiert, BL-239 AK-6). Heute immer "srs_compute".
  #   special_flags   = K-Score-Normalisierungs-Artefakt-Flags (BL-232); Default [] (kein Artefakt)
  #   gap_status / gap_status_dominant = forward-compat NULL-Platzhalter (Schema-Vertrag). Der REALE
  #                     Greenfield-Signal ist coverage_per_batch.batch_coverage_verdict — der Consumer
  #                     (modusEntscheidung 4.5b/6.5) liest ihn direkt als cov_verdict (BL-266). Hier null
  #                     deklariert, damit der gap_status-Read kein undeklariertes Feld trifft (Schema-Drift-Test
  #                     gruen) + fuer den Z625-Fallback (Pre-7.7-Story ohne coverage_map: kein Signal=null).
  #                     KEINE Befuellung durch testSearch (verletzte INV-TESTSEARCH-4 Schreib-Isolation).
  metric_per_batch[batch_key] = {
    "srs_max":              srs_max,
    "srs_avg":              srs_avg,
    "k_score_max":          k_score_max,
    "k_score_avg":          k_score_avg,
    "items_count":          len(batch_items),
    "items_with_data":      items_with_data,
    "fallback_used":        (items_with_data == 0),
    "w_status_set":         sorted(list(batch_w_status)),
    "srs_source":           ("hand_authored" IF "hand_authored" IN batch_srs_srcs ELSE "srs_compute"),
    "special_flags":        [],
    "gap_status":           null,   # befuellt von testSearch Phase 7.7
    "gap_status_dominant":  null,   # befuellt von testSearch Phase 7.7
    # ═══ BL-381 batch_3 (AK-3 + AK-6 code-Teil): Kazman-Schaerfungs-Achsen, per-Batch ═══
    # Forward-compat null-Platzhalter (Schema-Slot, analog gap_status). Die ZAHLEN sind read-only
    # ableitbar aus vorhandenem Substrat (DAG/Co-Change/Ca-Ce) via den BL-381-Helfern und docken
    # PRO SUB-BATCH an (scope-relativ, W-DOM-2 — KEIN globaler Repo-Skalar). Der Consumer
    # (modusEntscheidung) liest sie als DATEN (INV-MODUS-1: NICHT modus-setzend ausser C3 selbst).
    #   decoupling_level / propagation_cost  -> kazman_screening_metrics.screening_metrics() (AK-1, 0-100)
    #   co_commit_coupling                   -> kazman_kscore_axes.co_commit_axis()           (AK-2, 0-100)
    #   coupling_structural                  -> kazman_coupling_dimensions (Martin Ca/Ce, syntactic)
    #   coupling_temporal_resource           -> kazman_coupling_dimensions (co-commit, timing/resource)
    # AK-6: coupling_* werden GETRENNT gefuehrt — KEIN Rueckkollaps in einen k_kopplung-Skalar (W-AK6-2).
    # data-semantic + behavioral = dokumentierte Luecke (kein Laufzeit-Trace), NICHT hier (batch_4).
    "decoupling_level":           null,
    "propagation_cost":           null,
    "co_commit_coupling":         null,
    "coupling_structural":        null,
    "coupling_temporal_resource": null
  }

  Logge: "[metricPlanner] {batch_key}: srs_max={srs_max} srs_avg={srs_avg} k_max={k_score_max} k_avg={k_score_avg} items={items_with_data}/{len(batch_items)} w_status={sorted(list(batch_w_status))} srs_source={metric_per_batch[batch_key].srs_source}"
```

### SCHRITT 3: Persist

```
# ═══ INV-METRIC-SCHEMA-1 (NEU 2026-05-10): SCHEMA-PFLICHT ═══
# DCSRE-486 Live-Bug 2026-05-10: Worker schrieb falsches Schema (k_score/srs statt
# srs_max/k_score_avg). SDF Phase 1.1 liest `srs_max` und `k_score_avg` — fehlende
# Felder → Story-Fallback → falsche Modus-Decision.
#
# PFLICHT-Output-Schema pro Batch (KEIN Workaround, KEIN Custom-Schema):
#   srs_max:          int (MAX of per_pl_evaluation[item].srs values)  # BL-312 AK-3
#   srs_avg:          float (AVG, round 1 dec)
#   k_score_max:      int (MAX of ak_details.k_score_pro_ak values)    # K-Quelle bleibt A-4k
#   k_score_avg:      float (AVG, round 1 dec)
#   items_count:      int (len of batch_items)
#   items_with_data:  int (items with srs!=null OR k!=null)
#   fallback_used:    bool (True wenn items_with_data == 0)
#
# ANTI-PATTERN — ABSOLUT VERBOTEN:
#   ❌ "srs": <value>          ← FEHLT _max/_avg-Suffix
#   ❌ "k_score": <value>      ← FEHLT _max/_avg-Suffix
#   ❌ "k_aufwand"/"k_kopplung"/"k_fragilitaet" pro Batch  ← Story-Aggregat NICHT erlaubt
#   ❌ "label": "MEDIUM"        ← KEINE Klassifikation hier (Schritt 5 in modusEntscheidung)
#   ❌ "items": [...]           ← Items-Liste NICHT in metric_per_batch (steht in batch_items_per_batch)

# Schema-Validation VOR Persist (PFLICHT)
# BL-266: w_status_set/srs_source/special_flags/gap_status/gap_status_dominant ergaenzt — der Consumer
# (_SDF_berater_modusEntscheidung 4.5a/4.5b/4.6/6.5) liest sie; ohne Producer waren es stille ?? null-No-Ops
# (BL-239/BL-231 run-dead). gap_status/gap_status_dominant = forward-compat null (realer Greenfield-Signal =
# coverage_per_batch.batch_coverage_verdict, Consumer liest ihn direkt). Schema-Vertrag-Test:
# scripts/test_metric_per_batch_contract.py (AK-S4).
required_keys = {"srs_max", "srs_avg", "k_score_max", "k_score_avg",
                 "items_count", "items_with_data", "fallback_used",
                 "w_status_set", "srs_source", "special_flags",
                 "gap_status", "gap_status_dominant",
                 # BL-381 batch_3 (AK-3): Kazman-Schaerfungs-Achsen als per-Batch-Felder.
                 # Producer-DEKLARATION (Schema-Slot); die ZAHLEN liefern die read-only Helfer
                 # (.claude/scripts/kazman_screening_metrics.py {decoupling_level,propagation_cost},
                 #  kazman_kscore_axes.co_commit_axis {co_commit_coupling},
                 #  kazman_coupling_dimensions.coupling_dimensions {coupling_structural,
                 #  coupling_temporal_resource}) — analog gap_status: hier null-deklariert, damit
                 # der Consumer-Read (modusEntscheidung, als DATEN — INV-MODUS-1, NICHT modus-setzend)
                 # kein undeklariertes Feld trifft (BL-266-Drift-Test gruen). Scope-relativ pro
                 # Sub-Batch (W-DOM-2), KEIN globaler Repo-Skalar. KEIN Rueckkollaps in 1 Skalar (W-AK6-2).
                 "decoupling_level", "propagation_cost", "co_commit_coupling",
                 "coupling_structural", "coupling_temporal_resource"}
forbidden_keys = {"srs", "k_score", "k_aufwand", "k_kopplung",
                  "k_fragilitaet", "label", "items"}

FOR batch_key, m IN metric_per_batch.items():
  missing = required_keys - set(m.keys())
  forbidden = set(m.keys()) & forbidden_keys
  IF missing:
    Logge FEHLER: "[metricPlanner] FAIL — {batch_key}: PFLICHT-Felder fehlen: {missing}"
    RETURN exit_code=2
  IF forbidden:
    Logge FEHLER: "[metricPlanner] FAIL — {batch_key}: VERBOTENE Felder: {forbidden} (siehe ANTI-PATTERN)"
    RETURN exit_code=2

Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE.metric_per_batch = metric_per_batch)
Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.metricPlanner = {
  status:                   "DONE",
  timestamp:                now(),
  ks_file:                  ks_file,
  aggregation_methode_srs:  "MAX",
  aggregation_methode_k_score: "AVG+MAX",
  metric_per_batch:         metric_per_batch,
  batches_total:            len(batches),
  batches_with_fallback:    warn_count,
  schema_version:           "INV-METRIC-SCHEMA-1",
  exit_code:                (1 IF warn_count > 0 ELSE 0)
})
```

### SCHRITT 3.5: per_pl_evaluation ZUSATZ-Anreicherung (BL-203 AK-8)

```
# BL-312 AK-3 ABGRENZUNG: Die BASIS-SRS (srs_max/srs_avg) kommt bereits aus SCHRITT 2
# aus per_pl_evaluation (PRIMAERE SRS-Quelle). DIESER Schritt fuegt NUR die ZUSATZ-Felder
# pl_srs_max/pl_k_score_avg/pl_bottleneck_ct hinzu (PL-Level-Anreicherung fuer modusEntscheidung).
# Kein zweiter SRS-Read-Pfad — same Quelle, andere Slots.
# per_pl_eval ist bereits in SCHRITT 1 geladen (Re-Bind redundant, harmlos).
per_pl_eval = DF_BATCH_STATE.per_pl_evaluation ?? null

IF per_pl_eval != null:
  FOR batch_key IN batches:
    batch_pl_ids = batch_items_per_batch[batch_key]
    pl_srs_values   = [per_pl_eval[pl_id].srs for pl_id IN batch_pl_ids
                       IF per_pl_eval.get(pl_id) != null]
    pl_k_score_vals = [per_pl_eval[pl_id].k_score for pl_id IN batch_pl_ids
                       IF per_pl_eval.get(pl_id) != null
                       AND per_pl_eval[pl_id].k_score != null]

    metric_per_batch[batch_key]["pl_srs_max"]      = max(pl_srs_values)      IF pl_srs_values   ELSE null
    metric_per_batch[batch_key]["pl_k_score_avg"]  = avg(pl_k_score_vals)    IF pl_k_score_vals ELSE null
    metric_per_batch[batch_key]["pl_k_score_max"]  = max(pl_k_score_vals)    IF pl_k_score_vals ELSE null  # BL-402 AK-CTX-2: Multi-Item-Override-Faehigkeit
    metric_per_batch[batch_key]["pl_bottleneck_ct"] = count(
      pl_id for pl_id IN batch_pl_ids
      IF per_pl_eval.get(pl_id) != null AND per_pl_eval[pl_id].bottleneck == true
    )

  Logge: "[metricPlanner] per_pl_evaluation aggregiert fuer {len(batches)} Batches"
  Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE.metric_per_batch = metric_per_batch)
ELSE:
  Logge: "[metricPlanner] per_pl_evaluation nicht verfuegbar (Phase 3.8 noch nicht gelaufen) — SKIP"
```

### SCHRITT 4: Audit + Exit

```
Logge: "[metricPlanner] DONE — {len(batches)} batches aggregiert ({warn_count} mit Fallback)"
RETURN exit_code=1 IF warn_count > 0 ELSE 0
```

## Aggregations-Tabelle

| Metric | Methode | Begruendung |
|--------|---------|-------------|
| `srs_max` | MAX (von per_pl_evaluation[item].srs in batch — BL-312 AK-3) | High-risk-Item reisst Batch-Modus hoch (M5/M7 wenn srs>=90) |
| `srs_avg` | AVG (round 1 dec) | Sekundaer fuer Trend-Erkennung |
| `k_score_max` | MAX (von per_pl_eval.k_score PRIMAER; Fallback ak_details.k_score_pro_ak — BL-402 AK-1) | High-Komplexitaet-Item reisst TDD-Bedarf hoch (M3) |
| `k_score_avg` | AVG (round 1 dec) | Effort-Verteilung im Batch |
| `items_count` | COUNT | |batch_items| |
| `items_with_data` | COUNT non-null | Aussagekraefigkeit |
| `fallback_used` | bool | True bei items_with_data == 0 |

## Beispiel

**Input** (DCSRE-486 mit 6 Sub-Batches):

```yaml
DF_BATCH_STATE.batch_items_per_batch:
  batch_1: [AK-CTX-2]
  batch_2: [AK-1]
  batch_3: [AK-CTX-3, AK-2, AK-4, AK-CTX-4]
  batch_4: [AK-CTX-1]
  batch_5: [AK-13, AK-3]
  batch_6: [AK-9, AK-14, AK-6]

K-SCORE.md ak_details:
  AK-1:    srs=90, k=55
  AK-2:    srs=85, k=50
  AK-3:    srs=95, k=35
  AK-4:    srs=90, k=45
  AK-6:    srs=95, k=30
  AK-9:    srs=95, k=40
  AK-13:   srs=90, k=65
  AK-14:   srs=null, k=null     # Spec-skip
  AK-CTX-1: srs=95, k=35
  AK-CTX-2: srs=95, k=50
  AK-CTX-3: srs=95, k=35
  AK-CTX-4: srs=90, k=40
```

**Output**:

```yaml
DF_BATCH_STATE.metric_per_batch:
  batch_1:
    srs_max: 95
    srs_avg: 95.0
    k_score_max: 50
    k_score_avg: 50.0
    items_count: 1
    items_with_data: 1
    fallback_used: false
  batch_2:
    srs_max: 90
    srs_avg: 90.0
    k_score_max: 55
    k_score_avg: 55.0
    items_count: 1
    items_with_data: 1
    fallback_used: false
  batch_3:
    srs_max: 95          # max(95, 85, 90, 90)
    srs_avg: 90.0        # avg(95+85+90+90)/4 = 90.0
    k_score_max: 50      # max(35, 50, 45, 40)
    k_score_avg: 42.5    # avg(35+50+45+40)/4 = 42.5
    items_count: 4
    items_with_data: 4
    fallback_used: false
  batch_4:
    srs_max: 95
    srs_avg: 95.0
    k_score_max: 35
    k_score_avg: 35.0
    items_count: 1
    items_with_data: 1
    fallback_used: false
  batch_5:
    srs_max: 95          # max(90, 95)
    srs_avg: 92.5        # avg(90+95)/2
    k_score_max: 65      # max(65, 35)
    k_score_avg: 50.0    # avg(65+35)/2
    items_count: 2
    items_with_data: 2
    fallback_used: false
  batch_6:
    srs_max: 95          # max(95, 95) — AK-14 null excluded
    srs_avg: 95.0
    k_score_max: 40
    k_score_avg: 35.0    # avg(40+30)/2
    items_count: 3
    items_with_data: 2   # AK-14 excluded
    fallback_used: false
```

## Konsumption durch SDF Phase 1.1

`_SDF_berater_modusEntscheidung` liest `DF_BATCH_STATE.metric_per_batch[current_sub_batch_id]`:

```
metric = DF_BATCH_STATE.metric_per_batch[current_sub_batch_id]
srs    = metric.srs_max          # Worst-Case-Driver
k      = metric.k_score_avg      # Effort-Distribution

# Modus-Entscheidung pro Batch (W7-Decision-Tree, jetzt mit per-Batch-Daten):
IF srs >= 90 AND k >= 50:
  modus = M5   # SC FULL Symbiose (high-risk + high-complexity)
ELIF srs >= 90 AND k < 50:
  modus = M3   # I + TDD (high-risk, low-complexity = TDD-relevant)
ELIF srs < 90 AND k >= 50:
  modus = M3   # I + TDD (medium-risk, high-complexity)
ELIF srs < 90 AND k < 50:
  modus = M2   # I Standard
...
```

(BL-151-FIX-Override-Pattern bleibt als zusaetzliche Override-Schicht fuer
Template-Verfuegbarkeit, ist aber jetzt sekundaer — Per-Batch-Daten sind primaer.)

## Verlinkungen

- **BL-172** — IDF Phase 7.6 metricPlanner Backlog-Item, Source: DCSRE-486 Live-Run
- **BL-168** — IDF Phase 7.5 stagePlanner (Schwester-Berater, Pattern-Vorlage)
- **BL-165** — INV-MODUS-1 (SDF Phase 1.1 alleinige Modus-Quelle)
- **BL-312 AK-3** — SRS-Single-Source-Naht: SRS aus per_pl_evaluation statt K-SCORE.md srs_pro_ak (K bleibt A-4k, deferred AK-10/BL-311)
- **per_pl_evaluation** — Single-Source fuer SRS (von _IDF_berater_plBewertung Phase 3.8, BL-312 AK-1)
- **K-SCORE.md** — Source-of-Truth NUR NOCH fuer K (k_score_pro_ak; SRS-Anteil downstream-irrelevant ab BL-312 AK-3)
- **_SDF_berater_modusEntscheidung** — Konsument von metric_per_batch
