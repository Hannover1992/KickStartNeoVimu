---
status: active
version: 0.2.0
type: berater
parent: _IDF_orchestrate
phase: phase_7
model_tier: ceiling
created: 2026-04-25
feature_anchor: BL-142
optional: false
wraps: _IDF_berater_batchPlanner
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.sequencePlanner.ordered_items", purpose: "Sequenz-Eingang"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.plAggregation.pl_items", purpose: "Per-Item-Lookup-Map fuer model_refs/spec_refs/k_score/srs (Pseudocode Z181)"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "Per-Item k_score, srs, model_refs, unreife_typ", purpose: "Aggregat-Berechnung"}
    - {file: "{VAULT}/Backlog/{bl_slug}/2_Model/{name}_Model.md", path: "EXTERN/INTERN-Scan", purpose: "Dependency-Block-Aggregat (Pseudocode Z367)"}
    - {file: "_session_params.md", path: "GLOBAL_MODUS", purpose: "easy/normal/hard fuer Batch-Size"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items", purpose: "Endgueltige Batch-Liste"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.k_score_aggregat", purpose: "Aggregat-K-Score (Mitose-Trigger)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.srs_aggregat", purpose: "Strukturelle-Risiko-Aggregat"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.unreife_typ", purpose: "Reifegrad-Aggregat"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_mode_hints", purpose: "ADVISORY Mode-Hints pro Sub-Batch aus build_klasse (BL-313 AK-3 Happy-Path-Producer). INV-MODUS-1: advisory only, C3/SDF Phase 1.1 entscheidet autoritativ; batch_mode_hints != batch_modes != modus, kein forced_mode-Override."}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.batchPlan", purpose: "Schema (s.u.) — KEIN batch_stages mehr (BL-168 Refactor 2026-05-09 → _IDF_berater_stagePlanner Phase 7.5)"}
  # batch_stages + stage_begruendung_per_batch wurden 2026-05-09 in _IDF_berater_stagePlanner verschoben (SRP).
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser batchPlan)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.idf_status"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.modus", note: "BL-162 AK-7 / F98 verschaerft 2026-05-08 — Modus-Quelle ist NUR _SDF_berater_modusEntscheidung"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.sdf_mode_hint", note: "REVOKED 2026-05-08 — Feld entfernt, IDF darf KEINEN Mode-Hint setzen"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.recommended_modus", note: "REVOKED 2026-05-08 — INV-BP-5 zurueckgenommen, IDF schreibt das nicht"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.expected_sdf_mode", note: "BL-165 AK-9 — forbidden_key, IDF liefert nur Daten"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.mode_recommendation", note: "BL-165 AK-9 — forbidden_key, Modus-Quelle NUR C3"}
  calls:
    - "Skill(_IDF_berater_batchPlanner) — innerer Call (BL-142 wraps Pattern)"
    - "EXTERN/INTERN-Scan-Subroutine (vorgesehen)"
---

# _IDF_berater_batchPlan (Phase 7 in _IDF_orchestrate)

> **Zweck:** Batch-Planung mit Wraps um batchPlanner + EXTERN/INTERN-Scan + DF_BATCH_STATE-Aggregate.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_batchPlan                                     |
+======================================================================+
|  LIEST:                                                              |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      BERATER_OUTPUTS.sequencePlanner.ordered_items                   |
|    {VAULT}/Backlog/{bl_slug}/6_PL/                       |
|      {bl_id}-parking-lot.md (k_score, srs, model_refs, unreife)    |
|    _session_params.md                                                |
|      GLOBAL_MODUS                                                    |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                        |
|      DF_BATCH_STATE.batch_items                                      |
|      DF_BATCH_STATE.k_score_aggregat                                 |
|      DF_BATCH_STATE.srs_aggregat                                     |
|      DF_BATCH_STATE.unreife_typ                                      |
|      DF_BATCH_STATE.batch_type    (NEU 2026-05-04)                   |
|      DF_BATCH_STATE.batch_mode_hints  (BL-313 AK-3 — ADVISORY,       |
|        Happy-Path-Producer aus build_klasse; INV-MODUS-1: C3         |
|        entscheidet autoritativ, != batch_modes != modus)             |
|      BERATER_OUTPUTS.batchPlan = {                                   |
|        batch_size, batch_items, aggregates, escalation_hint,         |
|        batch_type,         (NEU)                                     |
|        polish_signals[]    (NEU)                                     |
|      }                                                               |
|                                                                      |
|  RUFT (intern):                                                      |
|    Skill(_IDF_berater_batchPlanner, args="{NAME}")                   |
|    EXTERN/INTERN-Scan-Subroutine                                     |
|    Polish-Detection-Subroutine (NEU 2026-05-04)                      |
|                                                                      |
|  SCHREIBT NICHT (BL-162 AK-7, F98 verschaerft 2026-05-08):           |
|    BERATER_OUTPUTS.* (ausser batchPlan)                              |
|    IDF_PIPELINE_STATE.idf_status                                     |
|    DF_BATCH_STATE.modus / sdf_mode / sdf_mode_hint /                 |
|    recommended_modus / pipeline_route (Mode-M{N})                    |
|    -> Alleinige Modus-Quelle: _SDF_berater_modusEntscheidung (C3).   |
|    IDF liefert NUR Daten (Aggregate, batch_type, polish_signals,    |
|    escalation_hint=Tier-Empfehlung HAIKU/SONNET/OPUS, NICHT Mode).   |
|    AUSNAHME (BL-313 AK-3): batch_mode_hints IST erlaubt — ADVISORY   |
|    Vorhersage aus build_klasse, KEIN Mode-Befehl. batch_mode_hints   |
|    != batch_modes (Letzteres bleibt C3-exklusiv, oben verboten).     |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 7 (NEU, wraps batchPlanner)           |
|                                                                      |
|  MODELL-TIER: opus                                                   |
|    Begruendung: Multi-Aggregate (k, srs, unreife), Escalation-      |
|    Heuristik, EXTERN/INTERN-Scan-Integration. Wraps inneren         |
|    Berater + Synthese.                                              |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-BP-1: 4 Aggregate immer gesetzt (k, srs, unreife, batch_size)|
|    INV-BP-2: Wraps batchPlanner — kein direktes Bypass               |
|    INV-BP-3: Schreib-Isolation auf BERATER_OUTPUTS.batchPlan         |
|    INV-BP-4 (NEU 2026-05-04): batch_type-Klassifikation PFLICHT.    |
|      Werte: feature | refactor | polish | cleanup | mixed            |
|      Detection per Polish-Signals (siehe Subroutine unten).          |
|    INV-BP-5 (REVOKED 2026-05-08, F98 verschaerft, BL-162 AK-7):     |
|      Frueher: "recommended_modus PFLICHT — abgeleitet aus           |
|      batch_type". ZURUECKGENOMMEN — IDF/batchPlan setzt KEINEN      |
|      Modus, keinen Hint, keine Empfehlung. Entscheidung exklusiv   |
|      in _SDF_berater_modusEntscheidung (Phase 1.1, Opus-Tier).     |
|      batch_type bleibt erlaubt als Daten-Klassifikation             |
|      (feature/refactor/polish/cleanup/mixed) — KEIN Mode-M{N}.     |
|                                                                      |
|  POLISH-DETECTION-SUBROUTINE (Heuristik, NEU 2026-05-04):           |
|    polish_signals = []                                               |
|    FOR item IN batch_items:                                          |
|      IF item.linked_aks_status == "all_done":                        |
|        polish_signals.append("ak-done:" + item.id)                   |
|      IF item.title_keywords IN ["cleanup", "refactor",              |
|         "polish", "magic", "constants", "rename",                    |
|         "doc", "comment"]:                                           |
|        polish_signals.append("polish-kw:" + item.id)                 |
|      IF item.k_score < 20 AND item.srs < 20:                         |
|        polish_signals.append("low-complexity:" + item.id)            |
|                                                                      |
|    polish_ratio = len(polish_signals) / len(batch_items)             |
|    IF polish_ratio > 0.7:                                            |
|      batch_type = "polish"                                           |
|    ELIF polish_ratio > 0.3:                                          |
|      batch_type = "mixed"                                            |
|    ELSE:                                                             |
|      batch_type = "feature" / "refactor" je nach k/srs               |
|    # Hinweis (F98 verschaerft 2026-05-08, BL-162 AK-7):              |
|    # batch_type ist Daten-Klassifikation, KEIN Mode-Vorschlag.       |
|    # SDF Phase 1.1 (C3) liest batch_type + k_score_aggregate +       |
|    # srs_aggregate + gap + items und entscheidet M{N} selbst.        |
|                                                                      |
|  PFLICHT-LOGGING (NEU 2026-05-04, korrigiert 2026-05-08 F98):       |
|    [batchPlan] batch_size={N} items={ids}                            |
|    [batchPlan] aggregates: k={k} srs={srs} unreife={u}               |
|    [batchPlan] polish_ratio={ratio} signals={N}                      |
|    [batchPlan] batch_type={type}                                     |
|    # KEIN recommended_modus mehr im Logging — IDF liefert Daten.     |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - sequencePlanner done                                            |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - DF_BATCH_STATE 4 Aggregate gesetzt                              |
|    - BERATER_OUTPUTS.batchPlan vollstaendig                          |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_batchPlan, args="{NAME}")

Parameter:
  {NAME} - Feature-Name oder bl_id

Ausgabe:
  - DF_BATCH_STATE 4 Aggregate
  - BERATER_OUTPUTS.batchPlan
  - Exitcode: 0=OK, 1=ESCALATE, 2=FAIL

Logging-Format:
  [IDF_BPLAN] ENTRY name={NAME} sequence={n}
  [IDF_BPLAN] EXIT duration={ms}ms batch={k} k_agg={n} hint={x}
```

## Output-Schema

```yaml
DF_BATCH_STATE:
  batch_items: ["BL-142-PL-1", "BL-142-PL-2"]
  k_score_aggregat: 35
  srs_aggregat: "low"
  unreife_typ: "ok"

BERATER_OUTPUTS:
  batchPlan:
    batch_size: 2
    batch_items: ["BL-142-PL-1", "BL-142-PL-2"]
    aggregates:
      k_score: 35
      srs: "low"
      unreife_typ: "ok"
    escalation_hint: "SONNET_OK"
    last_berater: "batchPlan"
```

## Logik (NEU + wraps batchPlanner)

```
SCHRITT 0: Entry-Log + Vorbedingungen
  name = args[0]
  Logge: "[IDF_BPLAN] ENTRY name={name}"
  manifest = Read("{WORKING_DIR}/_manifest.md")
  ordered = manifest.BERATER_OUTPUTS.sequencePlanner.ordered_items
  IF ordered == null OR |ordered| == 0:
    FAIL exitcode=2 "sequencePlanner fehlt — Phase 6 zuerst"
  pl_items_map = {item.id: item for item in manifest.BERATER_OUTPUTS.plAggregation.pl_items}
  global_modus = manifest.GLOBAL_MODUS or "normal"

SCHRITT 1: Wrap-Call inneren Berater
  inner = Skill(_IDF_berater_batchPlanner, args=name)
  # innerer Berater selektiert ersten Batch (z.B. erste N Items)
  batch_ids = inner.batch_items
  batch_size = |batch_ids|
  batch_pls  = [pl_items_map[id] for id in batch_ids]

SCHRITT 2: EXTERN/INTERN-Scan ueber model_refs
  EXTERN_KEYWORDS = [
    "welcher standard", "best practice", "open source",
    "library", "framework", "industry standard",
    "convention", "rfc", "spec compliance"
  ]
  INTERN_KEYWORDS = [
    "wie implementieren wir", "wo ist der bug",
    "warum failed", "internal state", "current code"
  ]

  model = Read("{VAULT}/Backlog/{bl_slug}/2_Model/{name}_Model.md")
  extern_hits = 0
  intern_hits = 0
  unreife_typ = null

  FOR pl IN batch_pls:
    FOR w_id IN pl.model_refs:
      w_text = extract_W_section(model, w_id)
      FOR kw IN EXTERN_KEYWORDS:
        IF kw in lower(w_text): extern_hits += 1
      FOR kw IN INTERN_KEYWORDS:
        IF kw in lower(w_text): intern_hits += 1

  IF extern_hits > intern_hits AND extern_hits >= 3:
    unreife_typ = "EXTERN"
  ELIF intern_hits > extern_hits AND intern_hits >= 3:
    unreife_typ = "INTERN"
  ELSE:
    unreife_typ = "ok"   # IDF-Output ist generell REIF

SCHRITT 3: Batch-Aggregate berechnen (PL-VDD-FIX-001 Producer-Fix 2026-04-26)
  # Versuche PL-Items mit Aggregat-Feldern. Fallback: Heuristik aus batch_type.
  k_score_aggregate     = mean([pl.k_score_pl for pl in batch_pls if pl.k_score_pl != null])
                          ?? heuristik_k_score(batch_type)
  srs_aggregate         = mean([pl.srs_pl for pl in batch_pls if pl.srs_pl != null])
                          ?? heuristik_srs(batch_type)
  k_kopplung_aggregate  = mean([pl.k_kopplung_pl for pl in batch_pls if pl.k_kopplung_pl != null])
                          ?? heuristik_k_kopplung(batch_type)
  k_fragilitaet_aggregate = mean([pl.k_fragilitaet_pl for pl in batch_pls if pl.k_fragilitaet_pl != null])
                          ?? heuristik_k_fragilitaet(batch_type)

  # WICHTIG: Werte sind ALLE als Zahl (Score 0-100), NICHT als bucket-string.
  # Consumer (_SDF_berater_modusEntscheidung) erwartet Zahl fuer Decision-Tree.
  # Falls PL-Items noch keine *_pl Felder haben (Schema-Migration ausstehend),
  # liefert die Heuristik einen sinnvollen batch_type-basierten Default.

  # batch_type Heuristik (Fallback wenn PL-Items keine *_pl Felder haben):
  #   "schema_doku":    srs= 5, k_kopplung= 2, k_fragilitaet= 1, k_score= 8
  #   "code_refactor":  srs=30, k_kopplung=80, k_fragilitaet=40, k_score=50
  #   "kritisch_migration": srs=70, k_kopplung=85, k_fragilitaet=80, k_score=90
  #   "pilot_test":     srs=50, k_kopplung=20, k_fragilitaet=30, k_score=40
  #   "pure_inline":    srs= 5, k_kopplung=10, k_fragilitaet=15, k_score=15
  # batch_type Inferenz: aus batch_label oder pl.suggested_mode (M1/M2 → schema/inline,
  # M4 → code_refactor, M5/M6 → kritisch_migration, M7 → pilot/forschung).

  # SRS bucket NUR fuer Logging/Display, NICHT fuer State-Write
  IF srs_aggregate < 33:
    srs_bucket = "low"
  ELIF srs_aggregate < 66:
    srs_bucket = "medium"
  ELSE:
    srs_bucket = "high"

  model_refs_batch = union([pl.model_refs for pl in batch_pls])
  spec_refs_batch  = union([pl.spec_refs for pl in batch_pls])

  # Escalation-Hint (auf Basis Zahl-Werte)
  # BL-367 AK-1: floor=sonnet (feedback_haiku_verboten). HAIKU_OK-Stufe entfernt —
  # Mindest-Worker-Tier ist SONNET_OK (auch bei k_score_aggregate < 33).
  IF k_score_aggregate >= 70 OR srs_aggregate >= 66:
    escalation_hint = "OPUS_REQUIRED"
  ELIF k_score_aggregate >= 33:
    escalation_hint = "SONNET_OK"
  ELSE:
    escalation_hint = "SONNET_OK"   # floor=sonnet (feedback_haiku_verboten, BL-367 AK-1)

SCHRITT 4: DF_BATCH_STATE schreiben (englisch "aggregate" — Consumer-Konvention)
  Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE = {
    batch_items:              batch_ids,
    batch_total:              batch_size,
    # NEU (englisch, Zahl) — Consumer _SDF_berater_modusEntscheidung Line 140-143:
    k_score_aggregate:        k_score_aggregate,
    srs_aggregate:            srs_aggregate,
    k_kopplung:               k_kopplung_aggregate,    # Direct-Field (kein "_aggregate"-Suffix) — match Consumer _SDF_berater_modusEntscheidung Z140-143
    k_fragilitaet:            k_fragilitaet_aggregate,  # Direct-Field — match Consumer _SDF_berater_modusEntscheidung
    # DEPRECATED (deutsch, bucket) — 1 Release Backwards-Compat fuer alte Caller:
    k_score_aggregat:         k_score_aggregate,
    srs_aggregat:             srs_bucket,              # alter Bucket-Format, deprecated
    # Restliche Felder unveraendert:
    unreife_typ:              unreife_typ,
    model_refs_batch:         model_refs_batch,
    spec_refs_batch:          spec_refs_batch,
    batch_type:               batch_type,              # NEU — fuer Heuristik-Audit
    reifegrad:                "REIF"
  })

SCHRITT 5: BERATER_OUTPUTS.batchPlan schreiben
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.batchPlan = {
    batch_size:       batch_size,
    batch_items:      batch_ids,
    aggregates: {
      k_score:           k_score_aggregate,
      srs:               srs_aggregate,                # Zahl statt bucket (PL-VDD-FIX-001)
      srs_bucket:        srs_bucket,                   # bucket fuer Display
      k_kopplung:        k_kopplung_aggregate,
      k_fragilitaet:     k_fragilitaet_aggregate,
      unreife_typ:       unreife_typ,
      batch_type:        batch_type
    },
    extern_hits:      extern_hits,
    intern_hits:      intern_hits,
    escalation_hint:  escalation_hint,
    last_berater:     "batchPlan"
  })

SCHRITT 5b: batch_mode_hints emittieren — Happy-Path-Producer (BL-313 AK-3)

> **Zweck (BL-313 AK-3):** `batch_mode_hints` hatte bisher KEINEN Happy-Path-Producer
> — der einzige Writer war der IDF Phase 7.6 Anti-Shadow-Korrektur-Pfad
> (`_IDF_orchestrate.md` Anti-Shadow Post-Check: `batch_mode_hints = batch_modes`),
> der NUR feuert wenn IDF faelschlich `batch_modes` schrieb. In einem sauberen
> INV-MODUS-1-konformen Lauf blieb `batch_mode_hints` LEER → `guard_geist5_idf_to_sdf.py`
> (verlangt `batch_mode_hints` bei SDF-ENTRY, BEVOR C3/SDF Phase 1.1 `batch_modes` setzt)
> blockte JEDEN sauberen Erst-SDF-Eintritt bei `enforceProcess=true`. **Genau diese
> Luecke schliesst BL-313.** batchPlan ist der natuerliche Producer, weil es bereits
> pro Sub-Batch eine `build_klasse` (M2/M3/...) im Het-Split (BL-304) ableitet.
>
> **INV-MODUS-1-DISCLAIMER (ABSOLUT):** `batch_mode_hints` ist **ADVISORY ONLY**.
> `_SDF_berater_modusEntscheidung` (C3, SDF Phase 1.1) entscheidet **AUTORITATIV** den
> Modus PRO ROUND mit aktuellem Vault-State. `batch_mode_hints != batch_modes` und
> `batch_mode_hints != modus`. Kein `forced_mode`-Override, KEINE Bypass-Moeglichkeit
> (BL-218 AK-4). batchPlan schreibt `batch_mode_hints`, **NIEMALS** `batch_modes`
> (das bleibt C3-Hoheit, INV-MODUS-1; `batch_modes` steht auf der Forbidden-Liste
> oben im VERTRAG / `not_writes`).
>
> **CONTRACT-OWNERSHIP (BL-313 AK-2 — Single-Source pro Feld).** Jedes vom
> `guard_geist5_idf_to_sdf.py` geforderte Vertrags-Feld hat genau EINEN Owner:
>
> | Vertrags-Feld (geist5)   | Owner (Producer)                  | Diese Datei? |
> |--------------------------|-----------------------------------|--------------|
> | `batch_items_per_batch`  | batchPlanner / Phase 7            | ja (Phase-7) |
> | `batch_mode_hints`       | **batchPlan (SCHRITT 5b)**         | **ja**       |
> | `batch_stages`           | stagePlanner (Phase 7.5)          | nein         |
> | `IDF_DONE` (idf_status)  | _IDF_orchestrate (Phase 8)        | nein         |
>
> `metric_per_batch` wird von `_IDF_berater_metricPlanner` geowned (Konsument von
> `batch_items_per_batch`, KEIN Owner davon). batchPlan/Phase-7 emittiert
> `batch_items_per_batch` (Sub-Batch-Mapping) + `batch_mode_hints` (ADVISORY) —
> NIEMALS `batch_modes`/`batch_stages`/`metric_per_batch`.

  # Nur emittieren wenn ein Het-Split mit per-Sub-Batch build_klasse vorliegt
  # (BL-304). build_klasse → modus_hint Mapping ist 1:1 (M2→"M2", M3→"M3", ...).
  IF batch_items_per_batch != null:   # Sub-Batch-Plan vorhanden (Het-Split)
    batch_mode_hints = {}
    FOR sub_batch_id IN batch_items_per_batch.keys():
      build_klasse = sub_batch_build_klasse[sub_batch_id]   # aus Het-Split (M2/M3/M1/M5/...)
      batch_mode_hints[sub_batch_id] = String(build_klasse)  # "M2" / "M3" / ... ADVISORY
    Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE.batch_mode_hints = batch_mode_hints)
    Logge: "[IDF_BPLAN] BL-313 AK-3 batch_mode_hints (ADVISORY, INV-MODUS-1: C3 entscheidet autoritativ): {batch_mode_hints}"
    # KEIN batch_modes schreiben (C3-Hoheit). batch_mode_hints ist advisory-Vorhersage.
  ELSE:
    # Single-Batch / kein Het-Split: optional Story-weiter build_klasse-Hint, sonst
    # leer lassen (Anti-Shadow-Pfad bleibt als Korrektur-Netz fuer Drift-Faelle).
    Logge: "[IDF_BPLAN] BL-313 AK-3 kein Het-Split (batch_items_per_batch leer) — batch_mode_hints nicht emittiert (Anti-Shadow-Fallback bleibt)"

SCHRITT 5c: ENTFERNT 2026-05-09 (BL-168 Refactor)

> **Refactor 2026-05-09 (User-Direktive):** Stage-Planung war urspruenglich hier
> als SCHRITT 5c integriert. SRP-Verletzung — batchPlan macht Batches, NICHT
> Stages. Logik ist jetzt in `_IDF_berater_stagePlanner.md` (Phase 7.5),
> dynamisch aus `stage_*.md` Discovery statt hardcoded Stages [1,3,6].
>
> Vorteile: SRP, Discoverability (neue stage_N.md auto-verfuegbar), testbar
> isoliert. Siehe `_IDF_berater_stagePlanner.md` + IDF_orchestrate Phase 7.5.

SCHRITT 6: User-Story-Boundary-Detection (BL-154-PL-37, ARCH-M11)

> **Zweck (PL-37):** architecturalBrief wird pro User-Story getriggert,
> nicht nur pro Batch-Level. Wenn ein Batch eine Story-Grenze ueberschreitet
> (Items aus mehreren User-Stories), wird ein Story-Boundary-Marker gesetzt.

  # Story-Boundary-Erkennung: PL-Items haben user_story_id Frontmatter-Feld
  story_ids = set([pl.user_story_id for pl in batch_pls if pl.user_story_id != null])

  IF |story_ids| > 1:
    # Batch ueberschreitet Story-Grenze → Marker setzen
    Schreibe DF_BATCH_STATE.story_boundary = true
    Schreibe DF_BATCH_STATE.story_ids = list(story_ids)
    Schreibe DF_BATCH_STATE.architectural_brief_trigger = "per_story"
    Logge: "[IDF_BPLAN] PL-37 Story-Boundary: {|story_ids|} User-Stories im Batch — architecturalBrief wird pro Story getriggert"
  ELSE:
    # Einzel-Story oder keine Story-ID → Default Batch-Level
    Schreibe DF_BATCH_STATE.story_boundary = false
    Schreibe DF_BATCH_STATE.architectural_brief_trigger = "batch_level"
    Logge: "[IDF_BPLAN] PL-37 kein Story-Boundary ({|story_ids|} Stories) — architectural_brief_trigger=batch_level"

SCHRITT 7: NEEDS_HUMAN-Items aufgreifen (BL-154-PL-38, ARCH-M12)

> **Zweck (PL-38):** [NEEDS_HUMAN]-praefixierte PL-Items aus _PostBatch_ArchConformance
> duerfen nicht im ewigen ROUTED-Limbo verschwinden. Dieser Schritt prueft ob
> solche Items im Parking-Lot existieren und nimmt sie explizit in den Batch-Plan auf.

  # [NEEDS_HUMAN]-Items scannen (aus aktuellem Parking-Lot)
  parking_lot = Read("{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md")
  needs_human_items = [
    item for item in parking_lot.items
    if item.text.startswith("[NEEDS_HUMAN]") OR "[NEEDS_HUMAN]" in item.tags
  ]

  IF |needs_human_items| > 0:
    Logge: "[IDF_BPLAN] PL-38 NEEDS_HUMAN: {|needs_human_items|} Items gefunden — werden im Batch-Plan aufgegriffen"
    Schreibe BERATER_OUTPUTS.batchPlan.needs_human_items = [
      {id: item.id, text: item.text, source: "PostBatch_ArchConformance"}
      for item in needs_human_items
    ]
    Schreibe BERATER_OUTPUTS.batchPlan.needs_human_count = |needs_human_items|

    # Hinweis: NEEDS_HUMAN-Items sind HiL-pflichtig — NICHT automatisch in Batch einschieben
    # Nur dokumentieren + sichtbar machen (kein Auto-Include in batch_items)
    IF GLOBAL_HIL == "on":
      Logge WARNUNG: "[IDF_BPLAN] PL-38 NEEDS_HUMAN: {|needs_human_items|} Items brauchen manuelle Bearbeitung (HiL=on). Bitte manuell priorisieren."
    ELSE:
      Logge: "[IDF_BPLAN] PL-38 NEEDS_HUMAN: {|needs_human_items|} Items dokumentiert. HiL=off — Items werden am Ende des aktuellen BDF-Zyklus als Hinweis angezeigt."
  ELSE:
    Schreibe BERATER_OUTPUTS.batchPlan.needs_human_count = 0
    Logge: "[IDF_BPLAN] PL-38 NEEDS_HUMAN: keine Items — kein Limbo"

SCHRITT 8: Exit
  exitcode = (escalation_hint == "OPUS_REQUIRED") ? 1 : 0
  Logge: "[IDF_BPLAN] EXIT duration={ms}ms batch={batch_size} k_agg={k_score_aggregate} hint={escalation_hint}"
  EXIT exitcode
```

**Dependencies:**
- sequencePlanner.ordered_items (Phase 6)
- plAggregation.pl_items (Phase 3.2 — fuer model_refs/spec_refs/k/srs pro PL)
- batchPlanner (innerer Skill — selektiert Batch-Subset)
- {VAULT}/Backlog/{bl_slug}/2_Model/{name}_Model.md fuer EXTERN/INTERN-Scan

**Downstream:** DF_BATCH_STATE wird vom Batch-Loop (PRE/POST/Item) konsumiert.

## Begruendung Modell-Tier

opus — Synthese ueber inneren Berater + EXTERN/INTERN-Scan + Multi-Aggregate. Sonnet wuerde subtile srs/unreife-Faelle verfehlen.
