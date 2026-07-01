---
status: active
version: 1.7
type: berater
parent: _SDF_orchestrate
model_tier: ceiling
actor: _SDF_PreBerater_orchestrate (C9b) -- Schritt 3 (letzter)
sdf_quelle: Z869-1178
tc: TC3
feature: BL-134
created: 2026-04-18
updated: 2026-06-12 v1.7 (BL-314 markdown_uncoverable_gate: SCHRITT 5 ELSE-Coverage-Zweig unterscheidet jetzt 'untested CODE' (uncovered→M3 test-first, RICHTIG) von 'structurally uncoverable by nature' (Markdown-Skill-Doc/Konzept-Doc, kein ausfuehrbares Artefakt → kein RED-Pfad → M2 Disziplin-Direkt-Build). Konsumiert coverage_per_batch[sb].coverage_class / markdown_uncoverable_befund (von IDF Phase 7.7 testSearch BL-314 AK-2, reine Coverage-Daten). SCHRITT 6.5 Work-Type-Boost trägt jetzt markdown_uncoverable-Carve-Out (sonst würde der Greenfield→M3-Boost das Gate annullieren). Schliesst die BL-239-Wurzel (3× RED stage_abort auf Markdown-Targets). INV-MODUS-1 unberührt — C3 bleibt alleiniger modus-Writer, das Gate liest NUR Coverage-Daten. [[feedback_markdown_engine_bootstrap]]. | 2026-06-04 v1.6 (BL-280 COVERAGE-GATE-VOR-M1: cov_verdict frueh gelesen (SCHRITT 0); M1-Trigger-A+B gegated mit NOT cov_undertested — ein uncovered/partial Item bekommt NIE M1-Skelett (tdd=false), sondern faellt zu SCHRITT 5 → M3 test-first. Trivialitaet (M1) und Test-Beduerfnis (Coverage) sind orthogonal. Live-Defekt BL-242 batch_PL1 (k=8/srs=0/uncovered → M1 Skelett ohne Test → stage_abort). | v1.5 (BL-218 AK-4: batch_mode_hints-Konsumption — C3 liest IDF-Anti-Shadow-Hints, loggt sie, laesst C3-Entscheidung aber UNVERAENDERT autoritativ. v1.4: DCSRE-486 Case-Study Root-Fix: SC-Modi M4-M7 NUR bei srs>=60 [SC_GATE], Komplexitaet/Kopplung triggert NIE SC sondern Rigor M2->M3 [SCHRITT 5/5.5/6 recalibrated]; M1-Trigger-B braucht items_count==1. v1.3: M1-Trigger-B K<15+Safety-Lite, Split-Empfehlung k_max>=80. PRINZIP: SRS=Readiness-Gate, K-Score=Rigor-Dial — orthogonal.)
batch_aware: true
ak_implements: [AK-3, AK-4, BL-314-AK-1]
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items", purpose: "Liste der PL-Items im Batch (BL-134)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.metric_per_batch", purpose: "PRIMAER (BL-172 INV-METRIC-1): Per-Sub-Batch K-Score/SRS-Aggregation {batch_N: {srs_max, srs_avg, k_score_max, k_score_avg, ...}}. Konsumiert metric_per_batch[current_sub_batch_id] fuer Modus-Entscheidung pro Batch — NICHT Story-Aggregat."}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.k_score_aggregate", purpose: "FALLBACK (Story-Level) — NUR bei fehlendem metric_per_batch mit explicit WARN-Log"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE", purpose: "k_score/srs/freiheitsgrade/etc (Aggregat-Fallback fuer batch_modes-leer-Edge-Case)"}
    - {file: "_session_params.md", path: ".pr", purpose: "PR-Guard-Flag (M8)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_mode_hints", purpose: "BL-218 AK-4: IDF Anti-Shadow-Hints (IDF Phase 7.6 Anti-Shadow korrigiert batch_modes→batch_mode_hints). C3 liest als advisory INPUT, entscheidet aber AUTORITATIV. INV-MODUS-1 bleibt: NUR C3 schreibt batch_modes."}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_modes", purpose: "Per-Batch Mode-Map {batch_N: M{X}} — autoritativ bei heterogenen Batches (BL-165 INV-MODUS-4 2026-05-09)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.modus_begruendung_per_batch", purpose: "Per-Batch Begruendung-Map {batch_N: 'reasoning...'}"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.modus", purpose: "Dominanter/primaerer Modus aus batch_modes (Mehrheits-Mode oder einziger). Backward-Compat-Slot fuer Legacy-Konsumenten"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.modus_begruendung", purpose: "Freitext-Begruendung des dominanten Mode (fuer Legacy)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.pipeline_route", purpose: "Single Source: A_I/A_SC_I/A_SC_ANALYSE/A_PR_REVIEW/A_WP_RESEARCH"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.modusEntscheidung", purpose: "Legacy-Audit-Slot (gleicher Inhalt + batch_modes)"}
---

# _SDF_berater_modusEntscheidung (C3)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_modusEntscheidung (C3) -- BL-134 Batch-Aware  ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST: DF_BATCH_STATE.batch_items[]   (PRIMAER, BL-134)             ║
║         DF_BATCH_STATE.k_score_aggregate (Aggregat vom BatchPlanner) ║
║         DF_BATCH_STATE.batch_mode_hints  (BL-218 AK-4: IDF Advisory) ║
║         {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded):                                                ║
║           A_PIPELINE_STATE.k_score, k_aufwand, k_kopplung,          ║
║           k_fragilitaet, srs_score, phase, unreife_typ,             ║
║           freiheitsgrade, IS_META_COMMAND, bl_reifegrad             ║
║         _session_params.md: pr (PR-Guard-Flag)                      ║
║  SCHREIBT: DF_BATCH_STATE.batch_modes (PRIMAER, BL-165 INV-MODUS-4) ║
║              {batch_1: M{X}, batch_2: M{Y}, ...}                    ║
║              autoritative Per-Batch Mode-Map bei heterogenen Batches║
║            DF_BATCH_STATE.modus_begruendung_per_batch (Per-Batch)    ║
║              {batch_1: "reasoning...", batch_2: "reasoning..."}     ║
║            DF_BATCH_STATE.modus (dominant/Mehrheit aus batch_modes) ║
║              Backward-Compat-Slot fuer Legacy-Konsumenten           ║
║            DF_BATCH_STATE.modus_begruendung (Freitext fuer dominant)║
║            DF_BATCH_STATE.pipeline_route      (Single Source)        ║
║            BERATER_OUTPUTS.modusEntscheidung  (Legacy-Audit-Slot,    ║
║              spiegelt BATCH_STATE-Inhalt + batch_modes Map)          ║
║            + _berater_outputs.md Frontmatter: last_update,           ║
║              last_berater="C3"                                       ║
║  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                  ║
║                  andere DF_BATCH_STATE-Felder                        ║
║                  {WORKING_DIR}/_manifest.md-Felder direkt (ausser BATCH_STATE)     ║
║  ACTOR: _SDF_PreBerater_orchestrate (C9b) — Schritt 3               ║
║  MODELL-TIER: ceiling (opus) — TC3, SDF-Quelle Z869-1178            ║
║               50+ Entscheidungspfade + Begruendungstext-Freitext     ║
║               Bei N Batches: N-mal Decision-Tree intern + Aggregat   ║
║  INVARIANTEN: INV-2 (Write-Isolation, kein Fremdzugriff),            ║
║               INV-6 (blocked=true → C3 wird NICHT aufgerufen,       ║
║                 Pruning-Gate liegt in C9b, nicht in C3),            ║
║               INV-MODUS-1-LESEN (BL-218 AK-4): C3 liest              ║
║                 batch_mode_hints als advisory INPUT (SCHRITT 0b).    ║
║                 batch_mode_hints wird NIEMALS direkt als batch_modes  ║
║                 uebernommen — C3 bleibt alleiniger Schreiber von      ║
║                 DF_BATCH_STATE.batch_modes (INV-MODUS-1 absolut).    ║
║               INV-MODUS-4 (NEU 2026-05-09, BL-165): bei              ║
║                 batch_items_per_batch[] mit |Batches|>1 MUSS C3      ║
║                 pro Batch separat entscheiden — NICHT global one-fit-║
║                 all. Output batch_modes Map. DF_BATCH_STATE.modus    ║
║                 (singular) ist nur dominant/Mehrheits-Slot.          ║
║               INV-METRIC-1 (NEU 2026-05-10, BL-172): C3 MUSS         ║
║                 metric_per_batch[batch_X].srs_max + .k_score_avg/max ║
║                 als PRIMAER-Datenquelle fuer Modus-Entscheidung      ║
║                 nutzen — NICHT k_score_aggregate / srs_aggregate     ║
║                 (Story-Level). Story-Aggregat NUR Fallback bei       ║
║                 fehlendem metric_per_batch + explicit WARN-Log.      ║
║                 Beweis: DCSRE-486 Live-Run 2026-05-10 — ohne dies    ║
║                 zwingt sich Lead zu BL-151-FIX-Override-Improvisation║
║               W6 (6 Input-Felder: k_score/k_aufwand/k_kopplung/    ║
║                 k_fragilitaet/srs/reifegrad),                       ║
║               W7 (9-Modus-Baum + 3 Sonderfaelle),                  ║
║               W8 (Output 5 Felder deterministisch ausser begruend.),║
║               W9 (M→Pipeline-Mapping deterministisch),              ║
║               INV-MODUS-1 (BL-405: C3 entscheidet den Modus ALLEIN  ║
║                 aus k-score/srs/coverage. KEIN Modus-Override-       ║
║                 Eingang von itemContext mehr — reifegrad routet      ║
║                 upstream A/IDF/SDF. Altschuld geschnitten.)         ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_SDF_berater_modusEntscheidung, args="{NAME}")

Parameter:
  {NAME} — Feature-Name (z.B. "BL-124")

Vorbedingung (alle PASS, sonst C3 nicht aufgerufen):
  - BERATER_OUTPUTS.itemContext gesetzt (C2 DONE)
  - itemContext.blocked == false (Pruning-Gate in C9b)
  - _berater_outputs.md Frontmatter item_id + cycle_nr gesetzt

Ausgabe:
  - BERATER_OUTPUTS.modusEntscheidung (5 Felder)
  - Exitcode: 0=OK, 2=FAIL (unerwarteter State)

Logging-Format (NFR-4):
  [C3_modusEntscheidung] ENTRY item_id={item_id} cycle_nr={cycle_nr}
  [C3_modusEntscheidung] MODUS={gewaehlter_modus} route={pipeline_route}
  [C3_modusEntscheidung] EXIT duration={ms}ms status={OK|FAIL}
```

## Warum opus/ceiling (PFLICHT)?

50+ Entscheidungspfade (9 Modi x mehrere Bedingungskombinationen) + Begruendungstext als Freitext.
Haiku/Sonnet verwechseln Pfade bei dieser Tiefe — Qualitaets-Degradation nachgewiesen (BL-124 Spec ADR-D).
ceiling-Tier DARF NICHT auf middle/floor abgesenkt werden ohne Spec-Aenderung (G9-Kriterium).

## Decision-Tree Pseudo-Code (9 Modi + 3 Sonderfaelle, W7)

Reihenfolge ist absolut — hoechste Prioritaet zuerst, kein LLM-Check an Entscheidungspunkten.
`begruendung` ist Freitext (W8, AK-7) — darf zwischen Aufrufen variieren.
Alle 4 anderen Output-Felder MUESSEN bei gleichem Input deterministisch sein (G15).

```
SCHRITT 0 IDEMPOTENZ-GATE (NEU 2026-05-11, BL-NEW-15 — analog BL-NEW-7 recalibrate)
  # Resume-aware: wenn fuer diesen Sub-Batch schon entschieden wurde, RETURN cached.
  # Verhindert ~30-50k Token-Waste pro Resume bei hil=phase Multi-Session-Flows.
  #
  # Greift VOR jedem anderen Berater-Code, inkl. SCHRITT 0a.

  current_sub_batch_id    = DF_BATCH_STATE.current_sub_batch_id ?? null
  cached_modus            = DF_BATCH_STATE.batch_modes?.[current_sub_batch_id] ?? null
  cached_begruendung      = DF_BATCH_STATE.modus_begruendung_per_batch?.[current_sub_batch_id] ?? null

  IF current_sub_batch_id != null AND cached_modus != null:
    Logge: "[C3-IDEMPOTENZ-GATE] batch_modes[{current_sub_batch_id}]={cached_modus} bereits gesetzt — SKIP_CACHED"
    audit_jsonl_append({type: "C3_SKIP_CACHED", round: current_sub_batch_id, modus: cached_modus, timestamp: ISO})
    # WICHTIG: BERATER_OUTPUTS.modusEntscheidung BEIBEHALTEN (nicht überschreiben!)
    # Falls leer (z.B. nach Manifest-Reset): minimal rekonstruieren aus cached state
    IF BERATER_OUTPUTS.modusEntscheidung == null OR BERATER_OUTPUTS.modusEntscheidung == {}:
      BERATER_OUTPUTS.modusEntscheidung = {
        gewaehlter_modus: cached_modus,
        begruendung: cached_begruendung ?? "cached from prior run",
        cache_hit: true,
        last_update: DATE
      }
    ELSE:
      # Output schon im Manifest — nur cache_hit Flag setzen
      BERATER_OUTPUTS.modusEntscheidung.cache_hit = true
    [C3_modusEntscheidung] EXIT status=SKIP_CACHED round={current_sub_batch_id} modus={cached_modus}
    → RETURN exitcode=0

  # FALL-THROUGH: kein Cache-Hit → normaler Decision-Tree
  Logge: "[C3-IDEMPOTENZ-GATE] no cached modus for {current_sub_batch_id} — proceed with decision"

SCHRITT 0b: batch_mode_hints Konsumption (BL-218 AK-4)
  # IDF Phase 7.6 Anti-Shadow schreibt batch_mode_hints wenn batch_modes ohne C3-Lauf
  # gesetzt war (INV-MODUS-1-SHADOW-CORRECTED). C3 liest den Hint als ADVISORY INPUT —
  # kein Override, KEINE Bypass-Moeglichkeit (INV-MODUS-1 bleibt absolut).
  # Zweck: Transparenz + Audit-Trail (Hint geloggt → Operator sieht ob Hint abweicht).
  #
  # BL-313 AK-3 (2026-06-11) KLARSTELLUNG: batch_mode_hints hat jetzt einen Happy-Path-
  # Producer (_IDF_berater_batchPlan SCHRITT 5b emittiert es im NORMAL-Pfad aus build_klasse).
  # Auf sauberen INV-MODUS-1-konformen Laeufen ist batch_mode_hints daher ZUVERLAESSIG
  # vorhanden — NICHT mehr leer-by-default (frueher nur vom Anti-Shadow-Korrektur-Pfad
  # geschrieben). VERHALTEN UNVERAENDERT: C3 liest den Hint weiterhin advisory-only und
  # MUSS den vollen Decision-Tree (SCHRITT 1..8) laufen lassen. Der ELSE-Zweig (kein Hint)
  # bleibt gueltig fuer Single-Batch / Re-Entry-Faelle ohne Het-Split.

  batch_mode_hints = DF_BATCH_STATE.batch_mode_hints ?? null

  IF batch_mode_hints != null:
    hint_for_current = batch_mode_hints.get(current_sub_batch_id, null)
    IF hint_for_current != null:
      Logge: "[C3-HINTS] batch_mode_hints[{current_sub_batch_id}]={hint_for_current} — advisory only, C3 entscheidet autoritativ (INV-MODUS-1)"
      audit_jsonl_append({type: "C3_HINT_CONSUMED", round: current_sub_batch_id, hint: hint_for_current, timestamp: ISO})
      # WICHTIG: C3 macht KEINE automatische Uebernahme des Hints.
      # Der Hint ist ein Datenpunkt aus IDF-Analyse — C3 kann ihn in der begruendung
      # erwaehnen, MUSS aber eigenen Decision-Tree (SCHRITT 1..8) vollstaendig laufen lassen.
      # Erst NACH dem Decision-Tree wird der Hint (falls abweichend) als Divergenz geloggt.
      _hints_hint_for_current = hint_for_current  # Zwischenspeicher fuer Post-Check SCHRITT 8b
    ELSE:
      Logge: "[C3-HINTS] batch_mode_hints vorhanden, aber kein Eintrag fuer {current_sub_batch_id} — kein Hint fuer aktuelle Round"
      _hints_hint_for_current = null
  ELSE:
    Logge: "[C3-HINTS] batch_mode_hints nicht gesetzt (normaler Lauf ohne IDF Anti-Shadow-Korrektur)"
    _hints_hint_for_current = null

SCHRITT 0a: Per-Round-Sub-Batch-Awareness (REVISED 2026-05-09, BL-165 INV-MODUS-6 D-Architektur)
  # D-Refactor 2026-05-09: SDF-Outer-Loop iteriert ueber Sub-Batches.
  # C3 wird PRO ROUND aufgerufen — eine Mode-Decision fuer den aktuellen Sub-Batch.
  # KEIN interner Loop mehr — Outer-Loop ist im SDF-Orchestrator.

  current_sub_batch_items = DF_BATCH_STATE.current_sub_batch_items ?? null

  IF current_sub_batch_id != null AND current_sub_batch_items != null:
    # Outer-Loop-Path: C3 entscheidet fuer DIESEN Sub-Batch
    [C3_modusEntscheidung] ENTRY outer_loop_round={current_sub_batch_id} items={|current_sub_batch_items|}
    # Decision-Tree (SCHRITT 0+1 unten) liest current_sub_batch_items statt globalem batch_items
    # Aggregate (k_score, srs, frag) werden aus current_sub_batch_items berechnet
    # NICHT global aus DF_BATCH_STATE.batch_items (ganze Story)
    target_items = current_sub_batch_items
    # ... Rest des Pseudocodes (SCHRITT 0..end) verwendet target_items
    # Nach Decision: schreibe in batch_modes Map (akkumuliert ueber Outer-Loop)
    DF_BATCH_STATE.batch_modes[current_sub_batch_id] = gewaehlter_modus
    DF_BATCH_STATE.modus_begruendung_per_batch[current_sub_batch_id] = begruendung
    # Plus: aktueller Round-Mode auch in DF_BATCH_STATE.modus (Konsumenten-Slot fuer aktuelle Round)
    DF_BATCH_STATE.modus = gewaehlter_modus
    DF_BATCH_STATE.modus_begruendung = "Round-{current_sub_batch_id}: " + begruendung
    [C3_modusEntscheidung] EXIT round={current_sub_batch_id} mode={gewaehlter_modus}
    RETURN exitcode=0

  ELSE:
    # Single-Batch-Path (Legacy / kein Outer-Loop) — folgt SCHRITT 0 unten
    [C3_modusEntscheidung] INFO single_batch_path
    target_items = DF_BATCH_STATE.batch_items

SCHRITT 0: Entry + Input laden (BL-134 Batch-Aware)
  [C3_modusEntscheidung] ENTRY batch_index={DF_BATCH_STATE.batch_index} items={|DF_BATCH_STATE.batch_items|}

  # BL-134: Batch-Vertrag -- Liste der Items im Batch
  batch_items    = DF_BATCH_STATE.batch_items ?? []
  IF batch_items == []:
    Logge FEHLER: "[C3_modusEntscheidung] FAIL -- DF_BATCH_STATE.batch_items leer"
    [C3_modusEntscheidung] EXIT status=FAIL
    RETURN exitcode=2

  # BL-210 M8 TODO 2026-05-24: Audit Mode-Decision-Tabelle gegen BL-205 SRS-Refactor v2.
  # BL-205 hat SRS-Berechnung als Epistemik-Score 0-100 (w_offen/w_total) etabliert.
  # SDF C3 (dieser Berater) entscheidet M1..M9 basierend auf SRS + K-Score + Reifegrad.
  # AUDIT-PUNKT: Mode-Selection-Logik (SWITCH-Entscheidungen) gegen
  # BL-205 Konventionen pruefen: INTERN/EXTERN-Routing (SC vs WP), srs_weight binary 0/1,
  # epistemik-based mode mapping (UNREIF→M7 analyse vs SC-REIF→M5 vs REIF→M2/M3).
  # Folge-Action: Pipeline-Audit-BL fuer detaillierten C3-Mode-Tabellen-Refactor erstellen.

  # SCHRITT 1: (BL-405, INV-MODUS-1-Bereinigung) — KEINE Modus-Override-Aggregation mehr.
  # Frueher las C3 hier pro Item einen von itemContext berechneten reifegrad-Override
  # (+ LEGACY single-item Fallback) und konnte ihn in SCHRITT 2 ueber das k-score-System
  # druecken. Das war Altschuld: es verletzte INV-MODUS-1 (der Modus gehoert ALLEIN C3 aus
  # k-score/srs/coverage). Der reifegrad routet bereits upstream (A/IDF/SDF) — C3 braucht
  # keinen Override. Geschnitten -> C3 entscheidet ab SCHRITT 1.5 rein aus k/srs/coverage.

  pr_flag        = lies _session_params.md > .pr ?? false

  # ═══ BL-172 INV-METRIC-1 (NEU 2026-05-10): Per-Batch-Metriken sind PRIMAER ═══
  # IDF Phase 7.6 metricPlanner aggregiert per_ak K-Score/SRS pro Sub-Batch in
  # DF_BATCH_STATE.metric_per_batch[batch_X] = {srs_max, srs_avg, k_score_max, k_score_avg, ...}
  #
  # SDF Phase 1.1 MUSS metric_per_batch[current_sub_batch_id] lesen, NICHT k_score_aggregate.
  # Story-Aggregat ist NUR Fallback bei fehlendem metric_per_batch (Pre-BL-172 Storys) +
  # explicit WARN-Log fuer Audit-Trail.
  #
  # BL-151-FIX-Override (2026-04-26) wird durch BL-172 OBSOLET — Per-Batch-Daten sind
  # jetzt primaer und decken den BL-151-Edge-Case (pure-Doku-Batch in M7-Falle) sauber ab.
  metric_per_batch = DF_BATCH_STATE.metric_per_batch ?? {}
  batch_metric     = metric_per_batch.get(current_sub_batch_id, null)

  IF batch_metric != null:
    # PRIMAER (BL-172 INV-METRIC-1): Per-Batch-Aggregation aus K-SCORE.md per_ak
    # MAX-Logik fuer srs (worst-case-driver) + AVG fuer k_score (Effort-Verteilung)
    srs           = batch_metric.srs_max          # MAX (BL-172 INV-METRIC-2)
    k_score       = batch_metric.k_score_avg      # AVG (BL-172 INV-METRIC-2)
    k_score_max   = batch_metric.k_score_max      # MAX als Sekundaer-Slot fuer TDD-Decision
    Logge: "[C3_modusEntscheidung] PER-BATCH metrics ({current_sub_batch_id}): srs_max={srs}, k_score_avg={k_score}, k_score_max={k_score_max}"
    # ═══ DEFENSE-IN-DEPTH BL-402 (2026-06-18): story_fallback_k_score Override — Safety-Net ═══
    # PROPER-FIX: metricPlanner SCHRITT 2 liest jetzt per_pl_evaluation[item_id].k_score als PRIMAER
    # (BL-402 AK-1) — story_fallback_k_score sollte fuer PL-keyed Batches nicht mehr feuern.
    # DIESER OVERRIDE BLEIBT als Defense-in-Depth (Safety-Net) fuer den Fall, dass der Proper-Fix
    # noch nicht griff (alte Manifeste, Race-Condition, unerwarteter Edge-Case). Kein Entfernen ohne
    # Beweis-Lauf dass story_fallback_k_score nie mehr fuer PL-keyed Batches erscheint. [BL-402 AK-6]
    # Hintergrund: mangels PL->AK-Mapping (K-SCORE.md keyed by AK-BE-*, batchPlanner schreibt PL-IDs)
    # fiel metricPlanner auf den STORY-Aggregat-k_score zurueck (special_flags="story_fallback_k_score"),
    # k_score_avg/max wurden Platzhalter (ganze-Story-k, NICHT item-granular). LIVE-BEWEIS DCSRE-1699
    # PL-12: k_score_avg=38(story_fallback) -> M1-B FAIL trotz echtem pl_k_score_avg=3.
    # SCOPE: nur single-item (pl_k_score_avg dann unzweideutig Item-k); Multi-Item bleibt unangetastet.
    sub_items_n = |DF_BATCH_STATE.current_sub_batch_items ?? []|
    IF "story_fallback_k_score" IN (batch_metric.special_flags ?? []) AND batch_metric.pl_k_score_avg != null AND sub_items_n == 1:
      k_score     = batch_metric.pl_k_score_avg     # granular (per_pl_evaluation) statt Story-Platzhalter
      k_score_max = batch_metric.pl_k_score_avg     # single-item: max==avg
      Logge: "[C3_modusEntscheidung] STORY-FALLBACK-OVERRIDE (BL-402): k_score_avg/max waren Story-Platzhalter ({batch_metric.k_score_avg}); single-item -> granulares pl_k_score_avg={k_score} (per_pl_evaluation). M1-Trigger nicht mehr fehl-entwaffnet."
  ELSE:
    # FALLBACK: Pre-BL-172 Story (kein metric_per_batch im Manifest)
    Logge: "[C3_modusEntscheidung] WARN — metric_per_batch fehlt fuer {current_sub_batch_id}, Story-Aggregat-Fallback"
    Logge: "[C3_modusEntscheidung] WARN — Re-Run IDF Phase 7.6 empfohlen fuer saubere Per-Batch-Decisions"
    srs            = DF_BATCH_STATE.srs_aggregate ?? A_PIPELINE_STATE.srs_score ?? 50
    k_score        = DF_BATCH_STATE.k_score_aggregate ?? A_PIPELINE_STATE.k_score ?? 50
    k_score_max    = k_score   # bei Fallback identisch (kein per-AK-Detail verfuegbar)

  # k_kopplung + k_fragilitaet bleiben Story-Level (noch nicht von metricPlanner aggregiert).
  # FOLGE-TASK BL-172-EXT (optional): metricPlanner um diese 2 Werte erweitern.
  k_kopplung     = DF_BATCH_STATE.k_kopplung ?? A_PIPELINE_STATE.k_kopplung ?? 50
  k_fragilitaet  = DF_BATCH_STATE.k_fragilitaet ?? A_PIPELINE_STATE.k_fragilitaet ?? 50

  # ═══ BL-381 batch_3 (AK-3 + AK-6 code-Teil): Kazman-Schaerfungs-Achsen als DATEN ═══
  # Per-Batch-Felder aus metricPlanner (Producer-DEKLARATION; Zahlen aus den read-only Helfern
  # kazman_screening_metrics / kazman_kscore_axes / kazman_coupling_dimensions). Hier NUR gelesen
  # (Diagnose/Context), forward-compat null bis die K-Score-Produktion sie befuellt.
  #
  # ⚠ INV-MODUS-1 + AK-5-Guard (W-AK5-2): diese Achsen sind reine DATEN-Eingabe. Sie setzen den
  #   Modus NICHT (Modus entscheidet C3 allein, INV-MODUS-1) und werden NICHT als alleiniges Urteil
  #   verwendet. KEIN Rueckkollaps der Kopplungs-Dimensionen in 1 Skalar (W-AK6-2): structural
  #   (Ca/Ce) und temporal/resource (Co-Commit) bleiben GETRENNT gelesen.
  dl_axis        = batch_metric.decoupling_level ?? null            # AK-1, 0-100 (screening-grade)
  pc_axis        = batch_metric.propagation_cost ?? null            # AK-1, 0-100 (screening-grade)
  co_commit_axis_v = batch_metric.co_commit_coupling ?? null        # AK-2, 0-100 (Fragilitaet, getrennt von aenderungs_risiko)
  coup_structural = batch_metric.coupling_structural ?? null        # AK-6 structural (syntactic, Martin Ca/Ce)
  coup_temporal_resource = batch_metric.coupling_temporal_resource ?? null  # AK-6 temporal/resource (Co-Commit)
  IF dl_axis != null OR pc_axis != null OR co_commit_axis_v != null:
    Logge: "[C3_modusEntscheidung] BL-381 Kazman-Achsen ({current_sub_batch_id}, DATEN — kein Modus-Set): dl={dl_axis} pc={pc_axis} co_commit={co_commit_axis_v} coupling_structural/temporal_resource GETRENNT (W-AK6-2, kein Skalar-Kollaps)"
  phase          = A_PIPELINE_STATE.phase ?? null
  unreife_typ    = A_PIPELINE_STATE.unreife_typ ?? null
  freiheitsgrade = A_PIPELINE_STATE.freiheitsgrade ?? false
  IS_META        = A_PIPELINE_STATE.is_meta_command ?? false
  bl_reifegrad   = DF_PIPELINE_STATE.bl_reifegrad ?? "SC-REIF"

  # Komplexitaet aus K-Score ABLEITEN (nicht umgekehrt — SDF Z892-893)
  IF k_score <= 33:         komplexitaet = "LOW"
  ELIF k_score <= 66:       komplexitaet = "MEDIUM"
  ELSE:                     komplexitaet = "HIGH"

  IF k_fragilitaet <= 33:   fragilitaet = "LOW"
  ELIF k_fragilitaet <= 66: fragilitaet = "MEDIUM"
  ELSE:                     fragilitaet = "HIGH"

  # ═══ [BL-280] Coverage-Verdikt FRUEH lesen (vor M1-Trigger SCHRITT 1.5) ═══
  # Trivialitaet (M1-Skelett) und Test-Beduerfnis (Coverage) sind ORTHOGONAL: ein Item kann
  # winzig sein (k<15) UND trotzdem einen Test brauchen (uncovered = es gibt keinen Test, der
  # das neue Verhalten absichert). M1-Trigger-B feuerte bisher VOR der Coverage-Matrix (SCHRITT 5)
  # → ein uncovered-aber-trivialer Fix bekam M1 (Skelett, tdd=false, KEIN Test) statt M3 (test-first).
  # Live-Defekt BL-242 batch_PL1 (k=8, srs=0, uncovered): M1 schrieb den Encoding-Fix ohne
  # Regressions-Test → Skeleton-Outcome RED → stage_abort. Coverage-Achse muss M1 VORGESCHALTET
  # sein. Hoisted hierher, damit SCHRITT 1.5 sie konsumieren kann (SCHRITT 4.5b/5/6.5 lesen sie
  # erneut — idempotent, gleiche Quelle). [BL-280 AK-S1]
  cov_verdict     = DF_BATCH_STATE.coverage_per_batch?.[current_sub_batch_id]?.batch_coverage_verdict ?? null
  cov_undertested = cov_verdict IN ["uncovered", "partial"]   # untested → braucht Test → NIE M1-Skelett (BL-280)

  gewaehlter_modus = null
  sc_mode = null
  scope_mode = null
  begruendung = null

# ═══ PRIORITAET 1: M8 PR-Guard (absolut hoechste Prioritaet, W7) ═══
# Quelle: SDF Z1095-1103, User-Entscheidung 2026-03-30
# M8 ueberschreibt ALLE anderen Modi — pr=true → M8 IMMER
SCHRITT 1: PR-Guard
  IF pr_flag == true:
    gewaehlter_modus = "M8"
    begruendung = "PR-Review-Modus: pr=true gesetzt. Nur Analyse+Bewertung, keine Implementierung."
    → GOTO SCHRITT 9 (Pipeline-Mapping)

# ═══ PRIORITAET 1.5: M1 Skelett-Check (NEU 2026-05-10 BL-174 — REAKTIVIERT) ═══
# Quelle: User-Direktive 2026-05-10 nach Druckpunkt-Aufloesung.
# M1 = "Skelett vor Pruefung" — condensed 4-Step-Subset via Skill(_I_orchestrate
# --worker-mode --scope=skeleton) in einem GESPAWNTEN Worker (KEIN Lead-inline,
# INV-PM-1 ABSOLUT; KORRIGIERT 2026-06-18 — frueheres "Lead-inline OHNE Skill-Loads"
# war die BL-174-v1-Idee, SUPERSEDED durch INV-PM-1-Haertung + BL-212).
# Zweck: Triviale templated Cases (z.B. Konstanten mit 1:1-Sister-Pattern) brauchen
# keine volle ~20-Step-Pipeline — nur das 4-Step-Skelett. M1 entspannt M2 von Pragmatismus-Verletzungen.
#
# WICHTIG (INV-MODUS-9 NEU): M1 setzt voraus dass M2/M3 STRIKT eingehalten werden
# (siehe INV-PROCESS-STRICT in _I_orchestrate). Ohne diese Gegenleistung waere M1
# erneut DCSRE-1430-Risiko. Nicht beide locker, nicht beide strikt — M1 locker,
# M2/M3 knochenhart.
SCHRITT 1.5: M1-Skelett-Check
  # Inputs (ALLE UND-verknuepft):
  layers_for_batch    = BERATER_OUTPUTS.dependencyAnalyzer.layers_per_item filtered fuer current_sub_batch_items
  stages_for_batch    = DF_BATCH_STATE.batch_stages[current_sub_batch_id] ?? [1]
  has_template        = check_1to1_template(current_sub_batch_items, BERATER_OUTPUTS.architecturalBrief.matched_patterns)
  items_count         = |current_sub_batch_items|

  # Helper-Funktion (Lead-Logik, keine LLM-Frage):
  function check_1to1_template(items, matched_patterns):
    # 1:1-Template = Pattern mit confidence>=stable AND sister_story_link != null
    # Beispiel: PT-CORE-* mit "DCSRE-94 ValidationConstantsQDVS als 1:1-Vorlage"
    FOR p IN matched_patterns:
      IF p.confidence IN ["stable", "battle-tested"] AND p.sister_story_link != null:
        IF any item in items uses pattern p:
          RETURN true
    RETURN false

  # M1-TRIGGER (UND-Verknuepfung — alle MUESSEN matchen):
  IF items_count == 1 AND \
     stages_for_batch == [1] AND \
     layers_for_batch ⊆ ["BE-CORE"] AND \
     has_template == true AND \
     NOT cov_undertested:   # [BL-280 AK-S2] M1-Skelett NIE auf uncovered/partial — Test-Beduerfnis schlaegt Trivialitaet (Coverage→M3)
    gewaehlter_modus = "M1"
    begruendung = "M1-Skelett (BL-174 reaktiviert): {layers_for_batch} + Stage-1-only + 1:1-Sister-Pattern verfuegbar + 1 AK. " +
                  "Skill(_I_orchestrate --worker-mode --scope=skeleton) — condensed Worker mit Bare-Minimum-Subset " +
                  "[architecturalLibrary, patternLibrary, semanticLibrary, codeAtomic]. " +
                  "INV-PM-1 ABSOLUT auch fuer M1: Lead-Self-Inline NICHT zulaessig (User-Direktive 2026-05-10). " +
                  "Worker-Tier=sonnet (haiku-Trust nicht etabliert per User-Direktive 2026-05-10). " +
                  "Skip-erlaubt: testSearch, blueprintQG, Stufen-Loop, mitose, fanOut/fanIn. " +
                  "M2/M3-Strict-Enforcement gilt unveraendert fuer andere Batches."
    Logge: "[C3_modusEntscheidung] M1 fuer {current_sub_batch_id} (Skelett-Modus, INV-MODUS-9, condensed Worker via I_orchestrate)"
    → GOTO SCHRITT 9 (Pipeline-Mapping)
  # ─── M1-TRIGGER B (K-basiert + Safety-Lite, User-Direktive 2026-05-29, an DCSRE-486 kalibriert) ───
  # Trivialer Aufwand (k_score<15) UND Wissen steht (srs<33) UND KEIN Architektur-/Risiko-Signal.
  # EMPIRIE-BELEG (metric_per_batch v3): batch_v3_12 hatte k_avg=6 ABER srs_max=70 → NICHT M1,
  #   sondern M7 (Safety-Lite faengt es: srs>=33 -> kein M1). batch_v3_04 k_max=100 war
  #   normalization_artifact → kein Split. => Multi-Faktor schlaegt naive K-Baender (User-Einsicht).
  # M1 bleibt der EINE sanktionierte Single-Worker-Fall (INV-HW-2); Safety-Lite = Anti-DCSRE-1430.
  # ─── COVERAGE-GATE (BL-280 AK-S1, Live-Defekt BL-242 batch_PL1) ───
  # NOT cov_undertested ist PFLICHT: ein uncovered/partial Item braucht einen Test (Coverage→M3),
  # egal wie trivial (k=8, srs=0). OHNE dieses Gate pre-emptete M1-B die Coverage-Matrix → der
  # Encoding-Fix bekam M1 (Skelett, tdd=false), schrieb Code OHNE Regressions-Test → RED → stage_abort.
  # M1-Skelett ist fuer schon-getestete/Boilerplate-Skelette, NICHT fuer untested Fixes.
  ELIF items_count == 1 \
       AND k_score < 15 \
       AND srs < 33 \
       AND NOT cov_undertested \
       AND (BERATER_OUTPUTS.architecturalBrief == null \
            OR BERATER_OUTPUTS.architecturalBrief.no_match == true \
            OR (|BERATER_OUTPUTS.architecturalBrief.broken_patterns| == 0 \
                AND |[p for p in BERATER_OUTPUTS.architecturalBrief.matched_patterns IF p.severity == "MANDATORY"]| == 0)) \
       AND len([f for f in (batch_metric.special_flags ?? []) \
                IF f CONTAINS ANY ["hidden_complexity", "pain_signal", "unsicher", "extern_blocked", "deferred"]]) == 0:
    # items_count==1 PFLICHT (Fix 2026-05-29 DCSRE-486 Case-Study): M1 ist ein SINGLE-Item-Skelett.
    # OHNE diese Bedingung feuerte M1-B faelschlich auf batch_C2 (3 konkrete BE-Fixes, k=12.7<15) →
    # Skelett statt Implement. M1 NIE fuer Multi-Item-Batches (die brauchen volles M2-Implement).
    gewaehlter_modus = "M1"
    begruendung = "M1-Skelett (K-Trigger B, items_count==1 + k_score={k_score}<15 trivialer Aufwand + srs={srs}<33 Wissen steht + coverage NICHT undertested ({cov_verdict}) + keine broken/MANDATORY-Architektur-Patterns + keine Risiko-Flags). " +
                  "Skill(_I_orchestrate --worker-mode --scope=skeleton) — der EINE sanktionierte Single-Worker-Fall (INV-HW-2). " +
                  "Safety-Lite verhindert DCSRE-1430 (kein Skelett auf architektonisch/epistemisch riskantem Item); Coverage-Gate (BL-280) verhindert Skelett-ohne-Test auf untested Item. INV-PM-1 ABSOLUT: Handschuh-Wechsel via Skill, kein Lead-Self-Inline."
    Logge: "[C3_modusEntscheidung] M1-B (K<15+Safety-Lite+covered) fuer {current_sub_batch_id}: k_score={k_score} srs={srs} cov={cov_verdict} — sanktionierter Skelett-Single-Worker"
    → GOTO SCHRITT 9 (Pipeline-Mapping)
  # ─── DISCLAIMER (BL-304 AK-1/AK-2/AK-4, 2026-06-13) — der k_max<15-Gate ist UNVERAENDERT ───
  # WICHTIG: Die folgende M1-MULTI-Lane-Logik (k_score_max<15) ist seit BL-246 BYTE-IDENTISCH und
  # wird durch BL-304 NICHT geaendert. modusEntscheidung ist RED-Zone (INV-MODUS-1 / INV-VEHIKEL-2):
  # hier wird NUR dokumentiert, die Entscheidungslogik wird NICHT angefasst.
  #
  # Der BL-304-Defekt (DCSRE-486 batch_PL23) war: ein heterogener Batch (10 triviale k<15 + 1 schweres
  # k>=15) kam ungetrennt an -> k_score_max>=15 -> diese M1-MULTI-Lane fiel aus -> der GANZE Batch wurde
  # M2, obwohl 10/11 trivial. Die Luecke [15,80) hatte keinen Split (BL-279/Mitose splittet erst bei
  # k_max>=80). Der Fix ist UPSTREAM im Clustering (IDF _IDF_berater_clustering SCHRITT 3.5 / INV-CL-HETERO-1
  # + _IDF_berater_batchPlanner INV-BPN-HETERO-1, via pl_effort_split.split_by_effort_class, threshold=15
  # = genau diese Decke). Batches kommen seit BL-304 effort-HOMOGEN an -> der UNVERAENDERTE k_score_max<15-Gate
  # (Z429 unten) feuert jetzt korrekt fuer die triviale Mehrheit. Die [15,80)-Luecke ist UPSTREAM (Clustering)
  # geschlossen, NICHT hier. INV-MODUS-1 unberuehrt — C3 bleibt alleiniger modus-Writer.
  # ─── M1-MULTI Light-Lane (BL-246 AK-2 — proportionaler Modus fuer HOMOGEN-TRIVIALE Multi-Item-Batches) ───
  # Problem (BL-246 User-Beobachtung): ein Sub-Batch aus mehreren trivialen 1-Zeilen-Items bekommt heute den vollen
  # M2/M3-Bogen, weil M1-A/B ein items_count==1-Hart-Gate tragen (Fix 2026-05-29 gegen batch_C2-Fehlroutung). Aber:
  # batch_C2 war k_AVG<15 mit konkreten BE-Fixes drin (also NICHT alle trivial). Der echte proportionale Modus:
  # wenn AUCH DAS SCHWERSTE Item trivial ist (k_score_MAX<15 — nicht avg) UND alle Wissen-steht (srs=srs_max<33) UND
  # NOT cov_undertested UND keine MANDATORY/broken-Patterns UND keine Risiko-Flags, dann ist der GANZE Batch homogen
  # trivial → M1-multi: EIN Skelett-Worker fuer alle Items (Bare-Minimum-Subset), statt pro 1-Zeilen-Item den Vollbogen.
  # k_score_MAX (nicht k_avg) ist der Diskriminator gegen den batch_C2-Fehler: ein einzelnes nicht-triviales Item
  # (k>=15) kippt den ganzen Batch aus M1-multi zurueck in M2/M3-Strict. INV-PM-1 bleibt ABSOLUT (Skill-Handschuh,
  # kein Lead-Self-Inline); Safety-Lite + Coverage-Gate identisch zu M1-B. M1-multi ist der homogen-triviale Multi-Fall,
  # M1-B der Single-Fall — beide via _I_orchestrate --scope=skeleton.
  ELIF items_count > 1 \
       AND k_score_max < 15 \
       AND srs < 33 \
       AND NOT cov_undertested \
       AND (BERATER_OUTPUTS.architecturalBrief == null \
            OR BERATER_OUTPUTS.architecturalBrief.no_match == true \
            OR (|BERATER_OUTPUTS.architecturalBrief.broken_patterns| == 0 \
                AND |[p for p in BERATER_OUTPUTS.architecturalBrief.matched_patterns IF p.severity == "MANDATORY"]| == 0)) \
       AND len([f for f in (batch_metric.special_flags ?? []) \
                IF f CONTAINS ANY ["hidden_complexity", "pain_signal", "unsicher", "extern_blocked", "deferred"]]) == 0:
    gewaehlter_modus = "M1"
    begruendung = "M1-multi (BL-246 AK-2 proportionaler Modus): ALLE {items_count} Items homogen trivial — k_score_MAX={k_score_max}<15 (auch das schwerste Item trivial) + srs_max={srs}<33 (alle Wissen-steht) + coverage NICHT undertested ({cov_verdict}) + keine MANDATORY/broken-Patterns + keine Risiko-Flags. " +
                  "EIN Skelett-Worker fuer den ganzen Batch (kein Vollbogen pro 1-Zeilen-Item). " +
                  "Skill(_I_orchestrate --worker-mode --scope=skeleton --batch={alle current_sub_batch_items}) — INV-PM-1 ABSOLUT (Skill-Handschuh, kein Lead-Self-Inline), Safety-Lite + Coverage-Gate wie M1-B. k_score_MAX-Gate (nicht avg) verhindert den batch_C2-Fehler (1 nicht-triviales Item → zurueck zu M2/M3-Strict). M2/M3-Strict fuer heterogene/nicht-triviale Batches unveraendert."
    Logge: "[C3_modusEntscheidung] M1-multi (BL-246 AK-2) fuer {current_sub_batch_id}: {items_count} homogen-triviale Items, k_max={k_score_max} srs_max={srs} cov={cov_verdict} — EIN Skelett-Worker fuer den Batch"
    → GOTO SCHRITT 9 (Pipeline-Mapping)
  ELSE:
    # [BL-280 AK-S3] cov_verdict im Log: macht "uncovered → kein M1 (geht M3)" als Fallthrough-Grund sichtbar,
    # statt es spaeter als generischen stage_abort zu verschleiern.
    Logge: "[C3_modusEntscheidung] M1-Check FAIL fuer {current_sub_batch_id}: items={items_count}, stages={stages_for_batch}, layers={layers_for_batch}, has_template={has_template}, k_score={k_score}, srs={srs}, cov_verdict={cov_verdict} (undertested={cov_undertested}) — fallthrough zu Standard-Routing (uncovered → SCHRITT 5 → M3 test-first)"
    # Continue zu SCHRITT 2.5+ (PRIORITAET 2 forced-Override ist BL-405-entfernt; naechster live Step = Bottleneck-Check, dann der k/srs/coverage-Decision-Tree).

# ═══ PRIORITAET 2: ENTFERNT (BL-405, INV-MODUS-1-Bereinigung) ═══
# Hier stand frueher ein "Modus-Override"-Zweig: ein von itemContext aus reifegrad
# berechneter Modus (M1 bei REIF / M7 bei UNREIF / expliziter Override) konnte das
# k-score-System ueberstimmen, BEVOR der eigentliche Decision-Tree (SCHRITT 3+) lief.
# Das war Altschuld und verletzte INV-MODUS-1: der Modus gehoert AUSSCHLIESSLICH C3,
# abgeleitet aus k-score/srs/coverage. reifegrad routet bereits upstream (A/IDF/SDF);
# ein zusaetzlicher Override hier war redundant + INV-MODUS-1-widrig. KOMPLETT geschnitten.
# Die M1-Skelett-Entscheidung bleibt erhalten — sie wird in SCHRITT 1.5 RICHTIG aus
# k-score (k<15) + srs (<33) + coverage + Architektur-Signalen getroffen, nicht aus reifegrad.

# ═══ PRIORITAET 2.5: Bottleneck-Queue-Check (NEU BL-206) ═══
# Quelle: BL-206 AK-3 — IDF Phase 3.8e baut bottleneck_queue (queue_for_sc + queue_for_wp)
# INV-MODUS-1: C3 entscheidet FINAL — bottleneck_queue ist NUR INPUT/HINT
# INV-MODUS-5: Dieser Schritt darf recommended_modus/sdf_mode NICHT setzen
# Prioritaet 2.5 (nach dem entfernten Override-Schritt, vor WP_PIPELINE_READY-Check):
# Bottleneck-PLs bekommen SC (M5) oder WP (M9) STATT normalem K-Score-Routing.
SCHRITT 2.5: Bottleneck-Queue-Check
  bottleneck_queue = DF_BATCH_STATE.bottleneck_queue ?? null

  IF bottleneck_queue != null:
    current_items = target_items ?? DF_BATCH_STATE.current_sub_batch_items ?? DF_BATCH_STATE.batch_items ?? []
    current_item_ids = [item.id for item in current_items]

    # Pruefe ob aktuelle Batch-Items in einer Bottleneck-Queue sind
    items_in_wp_queue = [id for id in current_item_ids if id IN bottleneck_queue.queue_for_wp]
    items_in_sc_queue = [id for id in current_item_ids if id IN bottleneck_queue.queue_for_sc]

    IF len(items_in_wp_queue) > 0:
      # Extern-Bottleneck DOMINIERT: WP-Modus fuer diesen Batch
      gewaehlter_modus = "M9"
      begruendung = ("BL-206 Bottleneck-Loop (SCHRITT 2.5): Items {items_in_wp_queue} in "
                     "queue_for_wp (extern-Bottleneck, unsichere externe W{n}) → M9 WP-Research. "
                     "INV-MODUS-1: C3 entscheidet final auf Basis bottleneck_queue Signal.")
      Logge: "[C3_modusEntscheidung] BOTTLENECK-WP: {items_in_wp_queue} → M9"
      → GOTO SCHRITT 9 (Pipeline-Mapping)

    ELIF len(items_in_sc_queue) > 0 AND len(items_in_wp_queue) == 0 AND NOT (k_score != null AND k_score < 33):
      # +PFLASTER 2026-06-26 (GROUNDING-PARITY): trivial (k_score<33) sc-Bottleneck ist nie M5 — ein winzig-
      #   blindes Item (no_truth_refs-Kollaps, nie durch A's Wahrheits-Fabrik) ist nicht "intern-unklar →
      #   Forschung", sondern billig-baubar. Faellt durch zu standard routing -> SCHRITT 5 trivial_blind-Floor
      #   -> I-Familie (M2/M3). Konservativ (nur k<33), null-safe. Siehe Vault _parking-lot GROUNDING-PARITY-EPIC.
      # Nur intern-Bottleneck (non-trivial): SC-FULL Modus
      gewaehlter_modus = "M5"
      begruendung = ("BL-206 Bottleneck-Loop (SCHRITT 2.5): Items {items_in_sc_queue} in "
                     "queue_for_sc (intern-Bottleneck, interne W{n} unklar) → M5 SC-FULL. "
                     "INV-MODUS-1: C3 entscheidet final auf Basis bottleneck_queue Signal.")
      Logge: "[C3_modusEntscheidung] BOTTLENECK-SC: {items_in_sc_queue} → M5"
      → GOTO SCHRITT 9 (Pipeline-Mapping)

    ELSE:
      # Kein Bottleneck-Match fuer aktuelle Items → normales K-Score-Routing
      Logge: "[C3_modusEntscheidung] BOTTLENECK-CHECK: keine Queue-Matches fuer {current_item_ids} — standard routing"

  ELSE:
    Logge: "[C3_modusEntscheidung] BOTTLENECK-CHECK: bottleneck_queue nicht gesetzt (pre-BL-206 oder leere Queue) — standard routing"

# ═══ PRIORITAET 3: M9 WP-Pipeline (3 Bedingungen ALLE PFLICHT, W7) ═══
# Quelle: SDF Z1111-1134
# ALLE 3 Bedingungen PFLICHT — MODEL_MATURITY=LOW allein → M7 (nicht M9)
# INV-4 Ausnahme: M9 einziger Modus mit erzwungener HiL auch bei GLOBAL_HIL=off
SCHRITT 3: M9 WP-Check
  IF phase == "WP_PIPELINE_READY"
     AND unreife_typ == "EXTERN"
     AND freiheitsgrade == true:
    IF GLOBAL_HIL == "off":
      # M9 = einziger erzwungener HiL-Punkt auch im dark_factory-Modus (INV-4)
      AskUserQuestion:
        "M9 WP-Modus gewaehlt. WARNUNG: Ultra-teuer (heavy loading, Stunden).
         Bestaetigen (WP startet) oder Fallback M7?"
        options: ["WP_BESTAETIGT", "FALLBACK_M7"]
      IF user_choice == "FALLBACK_M7":
        gewaehlter_modus = "M7"
        A_PIPELINE_STATE.phase = "WP_PIPELINE_REJECTED"   # OQ-3: Re-Trigger verhindern
        A_PIPELINE_STATE.unreife_typ = null               # OQ-3: Reset PFLICHT
        begruendung = "M9 User-Fallback → M7. phase=WP_PIPELINE_REJECTED gesetzt."
      ELSE:
        gewaehlter_modus = "M9"
        begruendung = "M9 WP-Modus bestaetigt: WP_PIPELINE_READY + EXTERN + freiheitsgrade=true."
    ELSE:
      # GLOBAL_HIL=on: User hat sowieso interagiert
      gewaehlter_modus = "M9"
      begruendung = "M9 WP-Modus: phase=WP_PIPELINE_READY, unreife_typ=EXTERN, freiheitsgrade=true."
    → GOTO SCHRITT 9 (Pipeline-Mapping)

# ═══ PRIORITAET 4: META-Sonderfall RF-12 (IS_META + srs<20 + MEDIUM) ═══
# Quelle: SDF Z1136-1142, AK-12-05
# Hohe Kopplung bei Command-Aenderungen → Kaskadeneffekte (F028) → SC-Kontext PFLICHT
SCHRITT 4: META-Sonderfall
  IF IS_META == true AND srs < 20 AND komplexitaet == "MEDIUM":
    gewaehlter_modus = "M5"
    begruendung = "META-Sonderfall (RF-12): OmniCommand-interne Aenderung. MEDIUM+srs<20 → M5 (SC-FULL SYMBIOSE). Hohe Kopplung bei Command-Aenderungen → Kaskadeneffekte erfordern SC-Kontext (F028)."
    → GOTO SCHRITT 9 (Pipeline-Mapping)

# ═══ PRIORITAET 4.5: BL-239 — Kategorie-Trigger (experiment_provable) + Greenfield-Abgrenzung ═══
# Quelle: BL-239 Spec §3 + §4.2/§4.3 (AK-2, AK-3, AK-4). Laeuft VOR dem SRS-Hoehen-Gate (SCHRITT 5):
# die ART der Unsicherheit (Kategorie) schlaegt die rohe SRS-Hoehe.
#
# ─── M4/M5-SEMANTIK (AK-3, Beobachtung vs. Experiment) ────────────────────────────────────────
#   SRS sinkt auf genau ZWEI Arten — und die ART bestimmt den Modus, NICHT die Hoehe:
#   • M4 = observation/reasoning-confirmable: Wahrheiten die durch BEOBACHTUNG, RECHERCHE,
#          logische SCHLUSSFOLGERUNG schliessbar sind. KEIN Experiment noetig.
#   • M5 = experiment-required: Wahrheiten die OHNE Experiment NICHT geschlossen werden koennen
#          (Marker: W{n}.status == experiment_provable). Echte wissenschaftliche Methode.
#   Konsequenz: hoher SRS ALLEIN ist KEIN M5-Grund (das war die DCSRE-486-Ueberklassifikation) —
#   M5 verlangt entweder den experiment_provable-Marker (a) ODER den SRS-Hoehen-Fallback (SCHRITT 5).
SCHRITT 4.5: BL-239 Kategorie-Trigger + Greenfield-Abgrenzung
  # Datenquelle: per-Batch W{n}-Status-Menge. Bevorzugt aus metric_per_batch (falls metricPlanner
  # w_status_set fuehrt — forward-compat), sonst aus dem _srs_compute-Breakdown (Phase 1.1 Daten-Input,
  # enthaelt pro aktivem W{n} den status).
  batch_w_status_set = (metric_per_batch[current_sub_batch_id].w_status_set)
                       ?? { b.status FOR b IN (srs_breakdown ?? []) }
  has_experiment_provable = "experiment_provable" IN batch_w_status_set

  # ─── (a) experiment_provable-Trigger (AK-2): kategorie-basiert M5, UNABHAENGIG von SRS-Hoehe ───
  IF has_experiment_provable:
    gewaehlter_modus = "M5"
    begruendung = "experiment_provable-W{n} im Batch → M5 SC-FULL (kategorie-basiert, unabhaengig SRS-Hoehe: "
                + "nur-experimentell-schliessbare Wahrheit, Beobachtung/Recherche reicht nicht). [BL-239 AK-2]"
    → GOTO SCHRITT 9 (Pipeline-Mapping)

  # ─── (b) Greenfield-Abgrenzung (AK-4): hoher SRS weil UNGEBAUT ≠ genuines Unbekanntes ──────────
  # Ein Greenfield-Batch kann srs>=60 haben, weil die W{n} OFFEN sind (kein Code zum Bestaetigen),
  # NICHT weil ein Experiment noetig ist. Solche hohe-SRS-weil-ungebaut-Batches gehoeren in die
  # I-Familie (Bau via TDD), NICHT in den SC-Zyklus (Forschung). Verhindert die BL-237-batch_C1-
  # und DCSRE-486-Ueberklassifikation (1-Zeilen-/Bau-Items faelschlich M5).
  gap_status   = batch_metric.gap_status_dominant ?? batch_metric.gap_status ?? null
  cov_verdict  = DF_BATCH_STATE.coverage_per_batch?.[current_sub_batch_id]?.batch_coverage_verdict ?? null   # [BL-266] numerisches coverage_percent existiert nicht — Coverage lebt als Verdikt in coverage_per_batch
  is_greenfield = (gap_status == "MISSING") OR (cov_verdict == "uncovered")   # [BL-266] uncovered = Greenfield (kein Code → keine Tests)
  # ─── [BL-424] markdown_uncoverable Carve-Out (Decision-Tree-Ordering-Fix) ──────────────────────
  # Defekt-Wurzel: der Greenfield-Guard (GOTO SCHRITT 9 → M3) lief VOR dem SCHRITT-5
  # markdown_uncoverable_gate (BL-314). Ein uncoverable-by-nature Markdown-Target (Skill-Doc/
  # Konzept-Doc: uncovered=true → is_greenfield=true, srs>=60, kein experiment_provable) schoss
  # dadurch faelschlich nach M3 und ueberSPRANG das Gate → spaeter stage_abort (kein RED-Pfad auf
  # einem nicht-ausfuehrbaren Artefakt; BL-239/BL-314-Falle). Live-Beweis BL-423 batch_c: nur durch
  # opus-Worker-Judgement zu M2 gerettet — der mechanische dispatch_implement.js-Pfad / ein schwaches
  # Modell wuerde ungebremst fehlrouten. Fix (analog SCHRITT-6.5-Carve-Out, BL-314): das gleiche
  # markdown_uncoverable-Signal (IDF Phase 7.7 testSearch, reine Coverage-DATEN, INV-MODUS-1 unberuehrt)
  # nimmt den Greenfield-M3-GOTO aus → Durchfall zu SCHRITT 5 → markdown_uncoverable_gate → M2.
  # [BL-438] Single-Source-Resolver: liest BEIDE Signal-Orte (coverage_class + special_flags-Fallback).
  # Aufruf: markdown_uncoverable_resolver.resolve_markdown_uncoverable(coverage_per_batch[sb], metric_per_batch[sb])
  # Resolver prueft coverage_class, markdown_uncoverable_befund UND metric_per_batch.special_flags
  # ({"markdown_uncoverable","markdown_uncoverable_class"}) — schliesst Signal-Ort-Mismatch (BL-438).
  # INV-MODUS-1 unberuehrt (Gate liest nur Coverage-DATEN, C3 bleibt alleiniger modus-Writer).
  coverage_class_45b       = DF_BATCH_STATE.coverage_per_batch?.[current_sub_batch_id]?.coverage_class ?? null
  markdown_uncoverable_45b = markdown_uncoverable_resolver.resolve_markdown_uncoverable(
                               DF_BATCH_STATE.coverage_per_batch?.[current_sub_batch_id],
                               DF_BATCH_STATE.metric_per_batch?.[current_sub_batch_id]
                             )
  # (liest BEIDE Orte: coverage_class/markdown_uncoverable_befund UND metric special_flags-Fallback, BL-438)
  IF is_greenfield AND srs >= 60 AND NOT has_experiment_provable AND NOT markdown_uncoverable_45b:   # 60 = SC_GATE (SCHRITT 5); [BL-424] markdown-uncoverable ausgenommen
    gewaehlter_modus = "M3"   # Greenfield = uncovered (kein Code → keine Tests) → test-first Bau.
    begruendung = "Greenfield (gap=MISSING / coverage<20%) mit srs={srs}>=60 ABER kein experiment_provable → "
                + "hoher SRS = UNGEBAUT (W{n} OFFEN, kein Code), NICHT genuines Unbekanntes → M3 (test-first Bau), "
                + "NICHT M5 (Forschung). Coverage-Achse bleibt (uncovered→M3). [BL-239 AK-4]"
    → GOTO SCHRITT 9 (Pipeline-Mapping)
  # sonst: faellt durch zu SCHRITT 5 (SRS-Hoehen-Gate / Coverage-Matrix). [BL-424] markdown_uncoverable
  # faellt jetzt HIER durch (statt M3-GOTO) → SCHRITT-5 markdown_uncoverable_gate routet es deterministisch
  # zu M2 (Disziplin-Direkt-Build, kein RED-Pfad) — ohne opus-Judgement-Maskierung, motor-sicher.

# ═══ PRIORITAET 4.6: BL-239 AK-6 — SRS-Provenance-Guard (OQ-1 Option A) ═══
# Quelle: BL-239 Spec §14 (OQ-1 ENTSCHIEDEN: Guard). Loest die SRS-Semantik-Inversion durch EINZAEUNUNG
# statt Flip: die Engine-Konvention hoch=unsicher bleibt, ABER nur ENGINE-DERIVED srs darf das SC-Gate
# treiben. Hand-authored srs (Mensch tippt eine Zahl ins Frontmatter, oft invertiert gemeint) ist NICHT
# vertrauenswuerdig fuer Gate-Entscheidungen — nur Anzeige. Live-Beweis DCSRE-486: hand-srs=85 auf reifem
# 1-Zeilen-Item feuerte faelschlich M5. Genuine Unsicherheit signalisiert der Mensch ueber experiment_provable
# (SCHRITT 4.5(a), kategorie-basiert), NICHT ueber eine rohe Zahl.
SCHRITT 4.6: SRS-Provenance-Guard
  srs_source = (metric_per_batch[current_sub_batch_id].srs_source) ?? null
  # Default-Trust (non-breaking, INV-SRS-NAMING-4): fehlend/engine-derived → trusted; nur explizit
  # hand_authored → untrusted. So brechen Legacy-BLs (unmarkiert, engine-derived) NICHT.
  srs_gate_trusted = (srs_source != "hand_authored")
  IF NOT srs_gate_trusted:
    Logge WARNUNG: "[C3_modusEntscheidung] SRS-GUARD (BL-239 AK-6): srs={srs} ist HAND-AUTHORED "
                 + "(srs_source=hand_authored) → SC-Hoehen-Gate (srs>=60) wird NICHT getriggert; faellt auf "
                 + "Coverage-Matrix (Bau). Fuer genuine Unsicherheit den experiment_provable-Status setzen, "
                 + "nicht die rohe srs-Zahl."
  # srs_gate_trusted wird in SCHRITT 5 (SC-Gate) konsumiert.

# ═══ PRIORITAET 5: K-Score-Matrix (Standard-Routing, W7) ═══
# Quelle: SDF Z1144-1177
# WICHTIG (BL-174 2026-05-10): M1 NICHT mehr deprecated. M1-Faelle wurden bereits
# in SCHRITT 1.5 abgefangen (Skelett-Check). Diese Matrix routet alles was NICHT
# M1-Skelett-eligible ist — d.h. mehrere AKs, mehrere Stages, komplexere Layer,
# kein 1:1-Template. Default ist M2 (Skill-Handoff-PFLICHT, INV-PROCESS-STRICT).
#
# SKALEN-INVARIANTE (BL-129, 2026-04-18 + BL-154 Fix 2026-05-01):
# Alle Score-Werte (srs, k_kopplung, k_fragilitaet, k_score) leben auf
# 0-100-Skala mit Boundaries 33 (LOW/MEDIUM) und 66 (MEDIUM/HIGH).
# Die alten 0-10-Schwellen (srs<20, k_kopplung>7, srs>=60) waren Reste der
# pre-BL-129 Skala — bei BL-154 Batch 1 (k_score=15.5 LOW, srs=24.75 LOW)
# fuehrte das zu fehlerhaftem M5 statt M2 (User-Audit 2026-05-01).
# Skalen-Boundaries:
#   srs/k_kopplung/k_fragilitaet < 33  → LOW    (klar/lose/robust)
#   srs/k_kopplung/k_fragilitaet < 66  → MEDIUM
#   sonst                               → HIGH   (Pandora/Tight/Fragil)
SCHRITT 5: K-Score Standard-Matrix (RECALIBRATED 2026-05-29 — DCSRE-486 Case-Study)
  # ═══ ZWEI-ACHSEN-MODELL (User-Direktive + Live-Beweis) ═══
  # SRS = READINESS-GATE (Wissens-Unreife): NUR hoher SRS → SC-Modi (echte Unbekannte/Klaerungsbedarf).
  # K-Score/Fragilitaet = RIGOR-DIAL INNERHALB der I-Familie (M2 vs M3). Komplexitaet triggert NIE SC.
  #
  # FEHLER VORHER (Live DCSRE-486, behoben): die alte Matrix routete via Komplexitaet in SC:
  #   - 'srs<33 + MEDIUM-komplex → M5'  → C3 (srs30/k37) faelschlich M5 (klarer Refactor in SC-Zyklus)
  #   - 'srs>=33 + komplex HIGH → M6'   → C4 (srs35/k80) faelschlich M6 (Rename braucht keine Forschung)
  # Beide srs<60 = BEKANNT → gehoeren in die I-Familie (M2/M3), NICHT in SC.
  # SC-Modi (M4-M7) sind fuer EPISTEMISCHES Unbekanntes (hoher SRS), nicht fuer hohe Komplexitaet.
  SC_GATE = 60   # SRS-Schwelle ab der SC-Modi gerechtfertigt sind. Tunebar (User-Stellschraube).

  # ─── PFLASTER 2026-06-26 (GROUNDING-PARITY: K-Score-Sanity-Floor auf den SC-Gates) ───
  # Ein TRIVIAL kleines Item (k_score LOW < 33) ist NIE eine Pandora-Box / kein Forschungs-Fall —
  # selbst bei ceiling-SRS (haeufig der no_truth_refs-Kollaps srs=100 ungegroundeter Orphan/Seed-Items,
  # die nie durch A's Wahrheits-Fabrik liefen). Es gehoert in die I-Familie (M2/M3 — Bau klaert das
  # Unbekannte billig), NICHT in M5/M6/M7 SC-Analyse. Konservativ: NUR k<33 (LOW) wird abgefangen,
  # substanzielle Items routen unveraendert; null-safe (k_score==null -> kein Eingriff). Verlaengert das
  # Zwei-Achsen-Modell (Komplexitaet triggert nie SC) um die Symmetrie: TRIVIALITAET deckelt SC ebenfalls.
  # Proper-fix (Grounding-Gate @ IDF-3.75 + blind-vs-uncertain-Diskriminator in C3 + SRS-Formel-Reconcile):
  # Vault _parking-lot GROUNDING-PARITY-EPIC.
  trivial_blind = (k_score != null AND k_score < 33)

  IF srs >= 66 AND srs_gate_trusted AND NOT trivial_blind:   # AK-6 + PFLASTER: trivial (k<33) ist nie Pandora-Box
    # Pandora-Box — zu viel offen, noch nicht implementieren
    gewaehlter_modus = "M7"
    begruendung = "srs={srs} >= 66 (Pandora-Box, engine-derived) — zu viel epistemisch offen. NUR Analyse → M7 SC pure."

  ELIF srs >= SC_GATE AND srs_gate_trusted AND NOT trivial_blind:   # AK-6 + PFLASTER: trivial (k<33) ist nie SC
    # Echter Klaerungsbedarf (Wissen unsicher, aber implementierbar) → SC-Zyklus gerechtfertigt
    # ─── BL-239 AK-3 M4/M5-DISTINKTION (hier MIGRATION-GATED dokumentiert, NICHT default-geflippt) ───
    #   Saubere Ziel-Semantik: srs>=60 + experiment_provable → M5 (bereits in SCHRITT 4.5(a) abgefangen);
    #   srs>=60 OHNE Experiment-Marker = observation/recherche-resolvable → waere M4 (SC-INLINE).
    #   ABER: der experiment_provable-Marker ist NEU (BL-239) — bestehende W{n} sind noch NICHT klassifiziert.
    #   Ein Default-Flip srs>=60→M4 wuerde unmarkierte ECHTE-Experiment-Items faelschlich von M5 auf M4
    #   herabstufen (under-serve). Darum bleibt M5 der SICHERE Default bis W{n}-Reklassifikation
    #   (Migration, vgl. AK-10) erfolgt ist. Der Flip ist test-suite-gated (AK-5 T-M4-OBS) + migration-gated.
    IF fragilitaet == "HIGH" OR komplexitaet == "HIGH":
      gewaehlter_modus = "M6"
      begruendung = "srs={srs} >= 60 (echtes Unbekanntes) + fragil/komplex HIGH → M6 SC-FULL + TDD."
    ELSE:
      gewaehlter_modus = "M5"
      begruendung = "srs={srs} >= 60 (echtes Unbekanntes, kein experiment_provable-Marker → observation-resolvable; M5 sicherer Default bis W{n}-Reklassifikation, BL-239 AK-3) → M5 SC-FULL SYMBIOSE (wiss. Klaerung vor Impl)."

  ELSE:
    # srs < 60 = BEKANNT → I-Familie. (AK-6: ODER srs>=60 ABER hand-authored/untrusted → SC-Gate geguardet,
    #   faellt hierher = Bau statt Forschung; das ist der DCSRE-486-Fix.) MODUS = COVERAGE (BL-231/BL-232 2026-05-30):
    # M2 vs M3 entscheidet sich aus der ART der Aufgabe = ob die Ziel-Code-Stellen schon Tests haben —
    # NICHT aus K-Score/Kopplung (= Umfang, gehoert zu Clustering). Quelle: IDF Phase 7.7 testSearch.
    # (M1-Skelett wurde bereits in SCHRITT 1.5 abgefangen — nur Single-Item-Trivial.)
    coverage = DF_BATCH_STATE.coverage_per_batch[current_sub_batch_id].batch_coverage_verdict ?? null

    # ─── [BL-314] markdown_uncoverable_gate (NACH Coverage-Read, VOR dem M3-test-first-Default) ───
    # SCHRITT 5 unterscheidet sonst NICHT 'untested CODE' (uncovered → M3 test-first, RICHTIG) von
    # 'structurally uncoverable by nature' (Markdown-Skill-Doc / Konzept-Doc → M2 noetig): bei
    # uncoverable-by-nature gibt es kein ausfuehrbares Artefakt, ein TDD-RED kann NIE geschrieben werden →
    # der Stage laeuft in stage_abort (BL-239 Live-Defekt, 3× RED). Ein denkender Worker (sonnet+) rettet
    # es bisher per autoritativem M3→M2-Override (BL-255 PL1 2026-06-10), ABER der MECHANISCHE Tree
    # (dispatch_implement.js / schwaches Modell) folgt dem Baum und mis-routet → die Falle ist strukturell
    # offen, nur durch Worker-Intelligenz maskiert. Das Gate macht MECHANISCH was der Worker per Reasoning tat.
    # Das diskriminierende Signal liefert IDF Phase 7.7 testSearch (BL-314 AK-2, reine Coverage-DATEN —
    # INV-MODUS-1 unberuehrt, C3 bleibt alleiniger modus-Writer). Greift NUR bei markdown_target_uncoverable;
    # uncovered+CODE (coverage_class=testable) bleibt M3. Verweis: [[feedback_markdown_engine_bootstrap]].
    coverage_class       = DF_BATCH_STATE.coverage_per_batch?.[current_sub_batch_id]?.coverage_class ?? null
    # [BL-438] Single-Source-Resolver nutzen: liest coverage_class/markdown_uncoverable_befund
    # (coverage_per_batch[sb]) UND metric_per_batch[sb].special_flags-Fallback
    # ({"markdown_uncoverable","markdown_uncoverable_class"}) — schliesst Signal-Ort-Mismatch.
    # Aufruf: markdown_uncoverable_resolver.resolve_markdown_uncoverable(coverage_per_batch[sb], metric_per_batch[sb])
    # INV-MODUS-1 unberuehrt (Gate liest nur Coverage-DATEN, C3 bleibt alleiniger modus-Writer).
    markdown_uncoverable = markdown_uncoverable_resolver.resolve_markdown_uncoverable(
                             DF_BATCH_STATE.coverage_per_batch?.[current_sub_batch_id],
                             DF_BATCH_STATE.metric_per_batch?.[current_sub_batch_id]
                           )
    # (liest BEIDE Orte: coverage_class UND metric special_flags-Fallback, BL-438)

    IF markdown_uncoverable AND coverage IN ["uncovered", "partial"]:
      gewaehlter_modus = "M2"   # Disziplin-Direkt-Build, KEIN TDD-RED
      begruendung = "srs={srs}<60 + coverage={coverage} ABER markdown_target_uncoverable (Skill-Doc/Konzept-Target, " +
                    "kein ausfuehrbares Artefakt → kein RED-Pfad) → markdown_uncoverable_override (BL-314: " +
                    "uncoverable-by-nature, kein ausfuehrbares Artefakt → M2 statt M3-stage_abort). " +
                    "M2 = Disziplin-Direkt-Build + Szenario-Verify, KEIN M3/test-first. [BL-314 / BL-239-Wurzel / [[feedback_markdown_engine_bootstrap]]]"
      Logge: "[C3_modusEntscheidung] MARKDOWN-UNCOVERABLE-GATE (BL-314): coverage={coverage} + coverage_class=markdown_target_uncoverable → M2 (statt M3, kein RED-Pfad) fuer {current_sub_batch_id}"
    ELIF coverage == "covered":
      gewaehlter_modus = "M2"
      begruendung = "srs={srs}<60 + Ziel-Code MIT Tests (coverage=covered, IDF testSearch) → M2 (code-with-test): Code aendern + bestehende Tests ausfuehren. KEIN K-Score-Einfluss (= Umfang, nicht Art)."
    ELIF coverage == "uncovered" OR coverage == "partial":
      gewaehlter_modus = "M3"
      begruendung = "srs={srs}<60 + Ziel-Code OHNE (vollstaendige) Tests (coverage={coverage}, IDF testSearch) → M3 (test-first/greenfield): neue Tests + Code fuer den ungetesteten Teil. (markdown_uncoverable_gate NICHT getriggert → testbares Code-Target, M3 korrekt.)"
    ELSE:
      # FALLBACK (coverage_map fehlt — alter BL ohne IDF-Phase-7.7 ODER kein Ziel-Datei-Ref):
      # gap_status, dann (degradiert) komplex/fragil. NICHT der Normalpfad.
      gap = batch_metric.gap_status_dominant ?? batch_metric.gap_status ?? null
      IF gap == "MISSING":
        gewaehlter_modus = "M3"; begruendung = "FALLBACK (keine coverage_map): gap_status=MISSING (neuer Code) → M3 (test-first)."
      ELIF komplexitaet == "HIGH" OR fragilitaet == "HIGH":
        gewaehlter_modus = "M3"; begruendung = "FALLBACK (keine coverage_map + kein gap): komplex/fragil HIGH → M3 (degradiert — eigentlich coverage-Frage)."
      ELSE:
        gewaehlter_modus = "M2"; begruendung = "FALLBACK (keine coverage_map): default M2 (code-with-test, bestehende Tests greifen im Verify)."

# ═══ SCHRITT 5.5: architectural_depth-Achse (BL-154-PL-35, ARCH-H9, V3) ═══
# NACH Modus-Entscheidung (SCHRITT 5), VOR K-Feinkorn (SCHRITT 6)
# Unterscheidet explizit: "patternBrief reicht" vs. "architecturalBrief noetig"
# Quelle: BL-154 PL-35 — modusEntscheidung kennt architectural_depth-Achse
SCHRITT 5.5: architectural_depth-Achse
  # architectural_depth aus BERATER_OUTPUTS.architecturalBrief lesen (falls vorhanden)
  arch_brief = BERATER_OUTPUTS.architecturalBrief ?? null
  architectural_depth = "patternBrief_reicht"  # Default

  IF arch_brief != null AND arch_brief.no_match == false:
    # Signal 1: Patterns mit MANDATORY-Severity vorhanden → architecturalBrief noetig
    mandatory_count = |[p for p in arch_brief.matched_patterns IF p.severity == "MANDATORY"]|
    IF mandatory_count > 0:
      architectural_depth = "architecturalBrief_noetig"
      Logge: "[C3_modusEntscheidung] architectural_depth=architecturalBrief_noetig (MANDATORY-Patterns: {mandatory_count})"

    # Signal 2: broken_patterns vorhanden → architecturalBrief noetig (Boundary-Instabilitaet)
    ELIF |arch_brief.broken_patterns| > 0:
      architectural_depth = "architecturalBrief_noetig"
      Logge: "[C3_modusEntscheidung] architectural_depth=architecturalBrief_noetig (broken_patterns: {|arch_brief.broken_patterns|})"

    # Signal 3: no_match=false aber nur OPTIONAL → patternBrief reicht
    ELSE:
      architectural_depth = "patternBrief_reicht"
      Logge: "[C3_modusEntscheidung] architectural_depth=patternBrief_reicht (keine MANDATORY/broken Patterns)"

  ELIF arch_brief == null OR arch_brief.no_match == true:
    # Kein architecturalBrief → patternBrief reicht (NON-BLOCKING)
    architectural_depth = "patternBrief_reicht"
    Logge: "[C3_modusEntscheidung] architectural_depth=patternBrief_reicht (architecturalBrief fehlt/EMPTY_SEED)"

  # Modus-Boost bei architecturalBrief_noetig:
  # Falls Modus M2 gewählt UND architecturalBrief_noetig → M5 (SC-Analyse-Kontext)
  IF architectural_depth == "architecturalBrief_noetig" AND gewaehlter_modus == "M2":
    gewaehlter_modus = "M3"
    begruendung += " [ARCH-DEPTH-BOOST] architecturalBrief_noetig (MANDATORY/broken Patterns) → M2→M3 (volle I-Pipeline + TDD fuer Architektur-Rigor). KEIN SC-Boost (2026-05-29 Case-Study: Architektur-Komplexitaet = Rigor-Bedarf, NICHT epistemisches Unbekanntes; SC nur bei srs>=60)."
    Logge: "[C3_modusEntscheidung] ARCH-DEPTH-BOOST: M2→M3 (Rigor, NICHT SC) wegen MANDATORY/broken Patterns"

  # architectural_depth in BERATER_OUTPUTS.modusEntscheidung mitschreiben
  # (wird in SCHRITT 9 Output-Block ergaenzt)
  _arch_depth_signal = architectural_depth  # Variable fuer SCHRITT 9

# ═══ SCHRITT 6: K-Score Feinkorn (Kopplung/Fragilitaet-Booster) ═══
# Optionale Ueberschreibung nach Basis-Routing wenn Kopplung/Fragilitaet sehr hoch
# Skalen-Konsistenz: LOW<33, MEDIUM<66, HIGH>=66 (siehe SCHRITT 5 Skalen-Invariante).
# K-BOOST greift NUR ab MEDIUM-Schwelle (>33), nicht bei marginaler Kopplung.
SCHRITT 6: K-Score Feinkorn (RECALIBRATED 2026-05-29 — Rigor-Boost, KEIN SC-Boost)
  # Hohe Kopplung/Fragilitaet → mehr Rigor INNERHALB der I-Familie (M2→M3), NIE in SC.
  # FEHLER VORHER (DCSRE-486): M3→M6 / M4→M5 schob die I-Familie via Kopplung in SC-Modi —
  #   derselbe Fehler wie die alte SCHRITT-5-Matrix (Komplexitaet/Kopplung != epistemisches
  #   Unbekanntes). Kopplung/Fragilitaet ist KOMPLEXITAET → eskaliert Rigor (TDD), nicht Forschung.
  #   SC-Modi entstehen AUSSCHLIESSLICH ueber das SRS-Gate (SCHRITT 5, srs>=60).
  # K-BOOST ENTFERNT (BL-231/BL-232 Durchbruch 2026-05-30): M2 vs M3 = COVERAGE (SCHRITT 5 via
  #   IDF Phase 7.7 testSearch), NICHT Kopplung/Umfang. Hohe Kopplung/Fragilitaet ist eine
  #   CLUSTERING/Reihenfolge-Frage (zu komplex → IDF splittet via Mitose, SCHRITT 7), KEINE Modus-Frage.
  #   K-Score/Kopplung bleibt NUR Clustering-Signal (IDF Phase 5/7) + M1-Schwelle (SCHRITT 1.5).
  #   Begruendung: K-Score = grobes numerisches Umfang-Mass (ungenau); der Modus haengt an der ART
  #   (Test-Coverage). Kopplung→M3 schob frueher M2-Aufgaben faelschlich in TDD obwohl Tests da waren.
  PASS  # (kein K-BOOST mehr — coverage entscheidet M2 vs M3)

# ═══ SCHRITT 6.5: WORK-TYPE-BOOST (BL-231 — Greenfield → M3) ═══
# M2 ist DESIGN-maessig "Refactor/bekannter Fix, bestehende Tests greifen" (SCHRITT 5, Z516).
# Wenn die Batch-Arbeit GREENFIELD ist (neues Verhalten/Code, KEINE bestehenden Tests, gap_status MISSING),
# gehoert sie in M3 (voller TDD: neuer Test + neuer Code), NICHT M2 (Refactor-Strom auf existierendem Code).
# Beleg DCSRE-486: greenfield-Batch landete via K-Score-Basis in M2 -> M2 hatte keinen passenden Code-Pfad.
# Seit BL-231 schreibt der Motor zwar auch bei M2 Code (entkoppeltes _TDD_green), ABER Greenfield verdient
# volle TDD-Rigor (Test-First) statt nur green-decoupled -> deshalb Eskalation M2->M3.
# Defensiv: fehlt das Greenfield-Signal -> KEIN Boost (M2 bleibt; Motor schreibt seit BL-231 trotzdem Code).
SCHRITT 6.5: Work-Type-Boost (Greenfield -> M3)
  gap_status   = batch_metric.gap_status_dominant ?? batch_metric.gap_status ?? null   # "MISSING" = neuer Code
  cov_verdict  = DF_BATCH_STATE.coverage_per_batch?.[current_sub_batch_id]?.batch_coverage_verdict ?? null   # [BL-266] numerisches coverage_percent existiert nicht — Coverage lebt als Verdikt in coverage_per_batch
  is_greenfield = (gap_status == "MISSING") OR (cov_verdict == "uncovered")   # [BL-266] uncovered = Greenfield (kein Code → keine Tests)
  # [BL-314] markdown_uncoverable-Carve-Out: ein in SCHRITT 5 per markdown_uncoverable_gate auf M2 gesetztes
  # uncovered-Markdown-Target ist zwar greenfield, aber uncoverable-by-nature (kein RED-Pfad). Der Greenfield→M3-
  # Boost wuerde es sonst sofort wieder nach M3 (test-first) eskalieren und damit das SCHRITT-5-Gate annullieren →
  # erneuter stage_abort (BL-239). Darum: KEIN Greenfield-Boost wenn markdown_target_uncoverable.
  coverage_class       = DF_BATCH_STATE.coverage_per_batch?.[current_sub_batch_id]?.coverage_class ?? null
  markdown_uncoverable = (coverage_class == "markdown_target_uncoverable") OR \
                         (DF_BATCH_STATE.coverage_per_batch?.[current_sub_batch_id]?.markdown_uncoverable_befund == true)
  IF gewaehlter_modus == "M2" AND is_greenfield AND NOT markdown_uncoverable:
    gewaehlter_modus = "M3"
    begruendung += " [WORK-TYPE-BOOST BL-231] Greenfield (gap_status=MISSING / coverage<20% = neues Verhalten, keine bestehenden Tests) -> M2->M3 (voller TDD/Test-First fuer neuen Code, statt M2-Refactor-Strom)."
  ELIF gewaehlter_modus == "M2" AND is_greenfield AND markdown_uncoverable:
    Logge: "[C3_modusEntscheidung] WORK-TYPE-BOOST SKIP (BL-314): greenfield ABER markdown_target_uncoverable (kein RED-Pfad) → M2 bleibt (markdown_uncoverable_override aus SCHRITT 5 erhalten)"
    Logge: "[C3_modusEntscheidung] WORK-TYPE-BOOST: M2->M3 (Greenfield, BL-231)"

# ═══ SCHRITT 7: Mitose-Split-ZWANG (BL-279: aus non-blocking "Wunsch" wird Zwang bei Extrem/Heterogenitaet) ═══
# Historie: NEU 2026-05-29 k_max-basiert, non-blocking. BL-279 (batch_3-Live-Beweis 2026-06-04): die non-blocking
# Empfehlung versickerte — batch_3 [k=21 + k=100, tdd+scenario gemischt] lief ungesplittet → der vorhergesagte
# Schmerz (J13 ~2h Markdown-via-TDD-Umweg) trat exakt am k=100-Item ein. „Eine Empfehlung, die niemand befolgt,
# ist ein toter Ast." DREI Split-Kriterien, alle erzwingbar (486-Lehre bleibt: k_score_MAX, kein Artefakt):
#   (1) Groesse: k_score_max >= hard_threshold (kein normalization_artifact) — extreme Komplexitaet.
#   (2) Verify-Mode (BL-276/BL-456): verify_mode_heterogeneous — tdd + scenario/convention im selben Batch (Kategorie-Mix).
#       INTRA-AK-Carve-Out (BL-456): split_het feuert NUR bei INTER-AK-Heterogenitaet (trennbare AKs mit je homogenem
#       verify_mode). INTRA-AK (Script+Doc desselben AK, per Re-Cut unaufloesbar) → KEIN split → Misch-Modus im selben
#       Batch (Script-Anteil per TDD, Doc-Anteil per scenario/M2, getragen via per-Datei verify_mode_of(f)).
#       INV-MODUS-1: verify_mode_heterogeneity_scope ist C3-internes Split-Mechanik-Signal, kein Modus-Feld.
#   (3) Effort-Heterogenitaet (BL-304): k_score_max >= het_floor (Default 15) UND k_score_avg < het_floor — triviale
#       Mehrheit von EINEM schweren Item (k_max in [het_floor, hard_threshold)) nach M2 mitgerissen. Schliesst die
#       Gate-Luecke [15,80) zwischen M1-MULTI-Decke (k_max<15, SCHRITT 1.5) und split_size (k_max>=80). Live 486 batch_PL23.
SCHRITT 7: Mitose-Split-Zwang
  is_k_artifact = "high_k_score_normalization_artifact" IN (batch_metric.special_flags ?? [])
  # AK-S4 (BL-279): Schwelle als Parameter (Default 80) — NICHT hart geraten. Daten-Kalibrierung (Bayesian ueber
  # die Schnitt-Menge, Proxy=Korrektur-Haeufung) ist an BL-273 gekoppelt (deferred). Bis dahin konfigurierbarer Default.
  hard_threshold = session_params.mitose_k_hard_threshold ?? 80
  het_floor      = session_params.het_split_k_floor ?? 15   # BL-304: deckungsgleich M1-MULTI-Decke (SCHRITT 1.5 k_score_max<15)
  het = DF_BATCH_STATE.coverage_per_batch?.[current_sub_batch_id]?.verify_mode_heterogeneous ?? false   # BL-276/BL-279

  # ─── BL-456: INTRA-vs-INTER-AK-Diskriminator (Consumer-seitig, INV-MODUS-1-konform) ───
  # Liest NUR Coverage-/AK-DATEN (batch_items[].ak_id + file_refs). Kein Modus-Hint (INV-MODUS-5 gewahrt).
  # verify_mode_heterogeneity_scope ist C3-internes Split-Mechanik-Signal, KEIN Modus-Feld.
  # Vorbedingung: het == true (sonst scope = "none", kein Diskriminator noetig).
  #
  # per_ak_modes: pro AK-ID alle verify_modes der zugehoerigen Dateien sammeln.
  # Quellen: batch_items[].ak_id + batch_items[].file_refs (via per_pl_evaluation / akExtraktion).
  # verify_mode_of(f): gleiche Mapping-Regel wie testSearch (W-DOM-3: .py→tdd, .md→scenario, .cs→tdd, ...).
  IF het:
    per_ak_modes = {}                                    # ak_id → set(verify_mode_of(f))
    FOR item IN (target_items ?? DF_BATCH_STATE.batch_items):
      ak = item.ak_id                                    # AK-Zugehoerigkeit des PL-Items
      FOR f IN (item.file_refs ?? []):
        per_ak_modes[ak].add( verify_mode_of(f) )        # gleiche Mapping-Regel wie testSearch (W-DOM-3)
    any_ak_internally_het = ANY( |modes| > 1 FOR modes IN per_ak_modes.values() )
    # Diskriminator-Regel (BL-456 AK-1):
    # intra_ak = mind. EIN AK traegt selbst >1 verify_mode → unaufloesbar per Re-Cut
    # inter_ak = jeder AK in sich homogen, Heterogenitaet erst ZWISCHEN AKs → trennbar → split gueltig
    IF any_ak_internally_het:
      verify_mode_heterogeneity_scope = "intra_ak"
    ELSE:
      verify_mode_heterogeneity_scope = "inter_ak"
    Logge: "[C3_modusEntscheidung] BL-456 SCOPE: verify_mode_heterogeneity_scope={verify_mode_heterogeneity_scope} (per_ak_modes={per_ak_modes})"
  ELSE:
    verify_mode_heterogeneity_scope = "none"
  # INV-SPLIT-SCOPE-1 (BL-456): split_het NUR bei inter_ak; intra_ak → Misch-Modus im selben Batch.
  # DOGFOOD-VERIFY (BL-456 AK-7, SB-2, 2026-06-23): BL-456 selbst (reine Markdown-Skill-Doc-Aenderungen)
  # routete in C3 als markdown_target_uncoverable → verify_mode=scenario → M2/scenario, split_required=false,
  # scope=none (alle Targets .md → homogen → kein Diskriminator-Lauf). Bestaetigt: INV-SPLIT-SCOPE-1 +
  # BL-314-markdown_uncoverable_gate greifen korrekt; INTRA-AK-Fix dogfood-t das eigene Gate.

  split_size = (k_score_max >= hard_threshold AND NOT is_k_artifact)
  split_het  = (het == true AND verify_mode_heterogeneity_scope == "inter_ak")
  # BL-304: items_count>1 PFLICHT (Single-Item k_max==k_avg -> nie heterogen). NUR in [het_floor,hard_threshold):
  # k_max>=hard_threshold deckt split_size, k_max<het_floor ist homogen-trivial -> M1-MULTI (SCHRITT 1.5). k_score=k_score_avg (Z280).
  split_het_effort = (items_count > 1 AND k_score_max >= het_floor AND k_score < het_floor \
                      AND k_score_max < hard_threshold AND NOT is_k_artifact)
  # BL-303 Test-Correction-Trigger: Ein Item das bestehende Test-Assertions aendert ("test_correction")
  # ist KEIN M2-kandidat — der korrigierte Test IST das neue RED. split_required=true -> raus aus M2-Batch -> M3-Pflicht.
  # test_correction_authorized ist KEIN Modus-Feld (INV-MODUS-1 bleibt); es ist reine Split-Mechanik:
  # das autorisierte Item bekommt einen eigenen Sub-Batch mit M3 (RED=korrigierter Test, GREEN=Impl).
  split_test_correction = ANY(item IN batch_items WHERE item.test_correction_authorized == true)
  IF split_size OR split_het OR split_het_effort OR split_test_correction:
    # BLOCKING (BL-279 AK-S1/S2/S3): aus "Wunsch" wird Zwang. Der Motor (dispatch_implement.js) liest split_required
    # aus dem Rueckgabe-JSON (MODUS_SCHEMA), baut den mal-geformten Sub-Batch NICHT, sondern RETURNED RE-BATCH an
    # den Lead (INV-MOTOR-2) → IDF-Re-Cut. KEIN Modus-Override (INV-MODUS-1 bleibt: split ist orthogonal zum modus).
    reason = (split_size ? "k_score_max={k_score_max} >= {hard_threshold} (echte Komplexitaet, kein normalization_artifact)" : "")
           + (split_size AND (split_het OR split_het_effort OR split_test_correction) ? " + " : "")
           + (split_het  ? "verify_mode-Heterogenitaet INTER-AK (trennbare AKs mit je homogenem verify_mode, BL-276/BL-456 — intra-AK-Faelle sind KEIN split)" : "")
           + (split_het AND split_het_effort ? " + " : "")
           + (split_het_effort ? "Effort-Heterogenitaet (BL-304): k_score_avg={k_score}<{het_floor} (triviale Mehrheit) ABER k_score_max={k_score_max} in [{het_floor},{hard_threshold}) -> triviale Items nach M2 mitgerissen (Gate-Luecke [15,80))" : "")
           + ((split_het OR split_het_effort) AND split_test_correction ? " + " : "")
           + (split_test_correction ? "test_correction (BL-303): Item aendert bestehende Test-Assertion -> split_required=true -> M3-Pflicht (korrigierter Test IST das neue RED; kein M2 fuer Test-Assertion-Aenderung)" : "")
    # BL-456 AK-5: recovery_hint fuer IDF-recluster NUR im inter_ak-Zweig emittieren.
    # Bei intra_ak-Heterogenitaet ist IDF-Re-Cut keine Loesung (unaufloesbar per Re-Cut) →
    # kein irrefuehrender recovery_hint. split_het ist bei intra_ak ohnehin false (split_het=false → dieser Block
    # wird nicht betreten). Recovery-Hint guard: nur wenn split_het==true (inter_ak) in reason aufgenommen.
    _recovery_hint_idf_recluster = (verify_mode_heterogeneity_scope == "inter_ak" OR split_het)
    BERATER_OUTPUTS.modusEntscheidung.split_recommendation = {
      k_score_max:  k_score_max,
      verify_mode_heterogeneous: het,
      verify_mode_heterogeneity_scope: verify_mode_heterogeneity_scope,
      reason:       reason,
      suggestion:   "IDF-Re-Cut: nach verify_mode homogen + k_max-Extreme isoliert schneiden (clustering/batchPlan)",
      blocking:     true,
      recovery_hint: (_recovery_hint_idf_recluster ? "Lead: loop_decision=RE-BATCH → Skill(_IDF_orchestrate, --recluster) → neue homogene Sub-Batches → re-dispatch" : "Kein IDF-recluster noetig (intra-AK-Heterogenitaet ist per Re-Cut unaufloesbar; Misch-Modus im selben Batch via per-Datei verify_mode_of(f))")
    }
    # Rueckgabe-JSON an den Motor (MODUS_SCHEMA, BL-279): split_required + split_reason setzen.
    return_json.split_required = true
    return_json.split_reason   = reason
    Logge: "[C3_modusEntscheidung] SPLIT-ZWANG (BL-279/BL-303/BL-304, BLOCKING): {reason} — Sub-Batch NICHT bauen, RE-BATCH an Lead. (Modus waere {gewaehlter_modus}; bei Effort-Heterogenitaet greift M1-MULTI erst auf der re-cut trivial-Mehrheit; bei test_correction -> M3 auf dem re-cut Item.)"
  ELIF k_score_max >= 70:
    return_json.split_required = false
    Logge WARNUNG: "[C3_modusEntscheidung] k_score_max={k_score_max} >= 70 — Mitose-Kandidat (post-BL-124 ADR). Weiter mit {gewaehlter_modus}."
  ELSE:
    return_json.split_required = false   # kein Zwang → Motor baut normal weiter

# ═══ SCHRITT 8: Fail-Guard — kein gueltiger Modus bestimmt ═══
SCHRITT 8: Null-Check
  IF gewaehlter_modus == null:
    Logge FEHLER: "[C3_modusEntscheidung] FAIL — kein Modus bestimmt. State-Dump: k_score={k_score} srs={srs} fragilitaet={fragilitaet} cov_verdict={cov_verdict} pr_flag={pr_flag}"
    [C3_modusEntscheidung] EXIT duration={ms}ms status=FAIL
    → RETURN exitcode=2

# ═══ SCHRITT 8b: Hint-Divergenz-Post-Check (BL-218 AK-4) ═══
# Nach dem kompletten Decision-Tree: war der IDF-Hint anders als C3-Entscheidung?
# Bei Divergenz: Audit-Log + begruendung-Anhang. Kein Modus-Override — INV-MODUS-1 absolut.
SCHRITT 8b: Hint-Divergenz-Log
  IF _hints_hint_for_current != null AND _hints_hint_for_current != gewaehlter_modus:
    Logge WARNUNG: "[C3-HINTS] HINT-DIVERGENZ: hint={_hints_hint_for_current} vs C3-Entscheidung={gewaehlter_modus} — C3 hat Vorrang (INV-MODUS-1)"
    audit_jsonl_append({
      type: "C3_HINT_DIVERGENCE",
      round: current_sub_batch_id,
      hint: _hints_hint_for_current,
      c3_decision: gewaehlter_modus,
      timestamp: ISO,
      note: "IDF batch_mode_hints war abweichend — C3 modusEntscheidung ist autoritativ"
    })
    begruendung += " [HINT-DIVERGENZ BL-218: IDF-Hint={_hints_hint_for_current}, C3-Entscheidung bleibt {gewaehlter_modus} (INV-MODUS-1)]"
  ELIF _hints_hint_for_current != null AND _hints_hint_for_current == gewaehlter_modus:
    Logge: "[C3-HINTS] HINT-MATCH: hint={_hints_hint_for_current} == C3-Entscheidung (IDF-Analyse und C3 kongruent)"

# ═══ SCHRITT 9: Pipeline-Mapping + Output (deterministisch, W9) ═══
# Mapping-Tabelle (W9, Spec ADR-A) — kein LLM-Aufruf, reiner Switch
SCHRITT 9: Pipeline-Mapping + Output
  # BL-169 (2026-05-09): M3 + M6 dispatchen auf I-/SC-Pipeline mit --tdd=true.
  # KEIN separater Skill(_TDD_orchestrate)-Call. TDD-Steps sind Top-Level-Steps
  # 9-18 der I-Pipeline am Pipeline-Ende (siehe _I_orchestrate.md REVISION-Block).
  #
  # BL-174 (2026-05-10): M1-Skelett-Modus dispatcht ebenfalls auf I-Pipeline,
  # ABER: scope_mode="skeleton" + worker_mode=true. Lead callt:
  #   Skill(_I_orchestrate, args="... --worker-mode --scope=skeleton ...")
  # I-Pipeline laeuft mit Bare-Minimum-Subset:
  #   {architecturalLibrary, patternLibrary, semanticLibrary, codeAtomic}
  # Skip: testSearch, blueprintQG, Stufen-Loop, mitose, fanOut/fanIn.
  # INV-PM-1 ABSOLUT auch fuer M1: Lead-Self-Inline NICHT zulaessig
  # (User-Direktive 2026-05-10: "Handschuh-Wechsel und immer I_orchestrate").
  # Worker-Tier=sonnet (haiku-Trust noch nicht etabliert per User-Direktive 2026-05-10).
  SWITCH gewaehlter_modus:
    "M1": pipeline_route="A_I",           sc_mode=null,      scope_mode="skeleton", tdd_flag=false  # BL-174 condensed Worker via --worker-mode
    "M2": pipeline_route="A_I",           sc_mode=null,      scope_mode="full",  tdd_flag=false
    "M3": pipeline_route="A_I",           sc_mode=null,      scope_mode="full",  tdd_flag=true   # BL-169 inline TDD
    "M4": pipeline_route="A_SC_I",        sc_mode="INLINE",  scope_mode="core",  tdd_flag=false
    "M5": pipeline_route="A_SC_I",        sc_mode="FULL",    scope_mode="full",  tdd_flag=false
    "M6": pipeline_route="A_SC_I",        sc_mode="FULL",    scope_mode="full",  tdd_flag=true   # BL-169 inline TDD
    "M7": pipeline_route="A_SC_ANALYSE",  sc_mode="ANALYSE", scope_mode="full",  tdd_flag=false
    "M8": pipeline_route="A_PR_REVIEW",   sc_mode=null,      scope_mode=null,    tdd_flag=false
    "M9": pipeline_route="A_WP_RESEARCH", sc_mode=null,      scope_mode="full",  tdd_flag=false
    DEFAULT:
      Logge FEHLER: "[C3_modusEntscheidung] FAIL — Unbekannter Modus: {gewaehlter_modus}"
      [C3_modusEntscheidung] EXIT duration={ms}ms status=FAIL
      → RETURN exitcode=2

  # BL-134: PRIMAER nach DF_BATCH_STATE schreiben (Single Source of Truth fuer Batch)
  Schreibe {WORKING_DIR}/_manifest.md:
    DF_BATCH_STATE.modus:             {gewaehlter_modus}
    DF_BATCH_STATE.modus_begruendung: {begruendung}
    DF_BATCH_STATE.pipeline_route:    {pipeline_route}

  # Legacy-Audit-Slot (gleicher Inhalt) -- BERATER_OUTPUTS.modusEntscheidung
  Schreibe _berater_outputs.md:
    BERATER_OUTPUTS.modusEntscheidung:
      gewaehlter_modus: {gewaehlter_modus}
      begruendung: {begruendung}
      pipeline_route: {pipeline_route}
      sc_mode: {sc_mode}
      scope_mode: {scope_mode}
      batch_aware: true
      batch_size: {|batch_items|}
      architectural_depth: {_arch_depth_signal ?? "patternBrief_reicht"}  # BL-154-PL-35
    Frontmatter:
      last_update: {jetzt}
      last_berater: "C3"

  # INV-MODUS-1-Whitelist-Marker (BL-165 AK-5 PL-5-01):
  # C3 ist der EINZIGE authorisierte Schreiber fuer DF_BATCH_STATE.modus.
  # guard_modus_writer.py prueft diesen Marker und blockiert alle anderen Schreiber.
  Schreibe {WORKING_DIR}/_manifest.md:
    DF_BATCH_STATE.modus_set_by: "_SDF_berater_modusEntscheidung"

  Logge: "[C3_modusEntscheidung] MODUS={gewaehlter_modus} route={pipeline_route} sc_mode={sc_mode} scope_mode={scope_mode}"
  [C3_modusEntscheidung] EXIT duration={ms}ms status=OK
  → RETURN exitcode=0
```

## Output an BERATER_OUTPUTS.modusEntscheidung

```yaml
modusEntscheidung:
  gewaehlter_modus: "M5"         # M2..M9, kein M1 (deprecated)
  begruendung: "..."             # Freitext — darf variieren (W8), erklaert Wahl
  pipeline_route: "A_SC_I"      # A_I | A_SC_I | A_SC_ANALYSE | A_PR_REVIEW | A_WP_RESEARCH
  sc_mode: "FULL"               # null | INLINE | FULL | ANALYSE
  scope_mode: "full"            # null | full | core
```

## Architektur-Notizen

- **INV-SPLIT-SCOPE-1 (BL-456, 2026-06-24):** `split_required` (aus dem het-Kriterium) NUR bei INTER-AK-verify_mode-Heterogenitaet (`verify_mode_heterogeneity_scope == "inter_ak"`). Bei INTRA-AK-Heterogenitaet (Script+Doc desselben AK, per Re-Cut unaufloesbar) KEIN split — stattdessen Misch-Modus im selben Batch (Script-Anteil per TDD, Doc-Anteil per scenario/M2, getragen via per-Datei `verify_mode_of(f)`). INV-MODUS-1 unberuehrt: `verify_mode_heterogeneity_scope` ist reine Split-Mechanik, kein Modus-Feld. Kein IDF-recluster-Hint fuer intra_ak (Re-Cut loest es nicht).
- **Opus-Tier PFLICHT** (ceiling): 50+ Entscheidungspfade + Begruendungstext-Freitext. G9-Kriterium: Tier-Absenkung erfordert Spec-Aenderung.
- **M1 via k-score** (BL-405): M1-Skelett wird in SCHRITT 1.5 aus k-score/srs/coverage/Architektur entschieden — NICHT mehr aus einem reifegrad-Override. (Historie: M1 war zwischenzeitlich deprecated DCSRE-1430 2026-04-15, dann BL-174 reaktiviert.)
- **OQ-5 ENTFERNT (BL-405, INV-MODUS-1-Bereinigung)**: C3 liest KEINEN Modus-Override mehr von itemContext (frueher das `itemContext`-Modus-Override-Feld + Vault-Frontmatter pro Item). Der Modus gehoert AUSSCHLIESSLICH C3, abgeleitet aus k-score/srs/coverage. reifegrad routet upstream (A/IDF/SDF). Altschuld geschnitten.
- **M9 HiL-Ausnahme** (INV-4): Einziger Modus der auch bei `GLOBAL_HIL=off` AskUserQuestion macht. Dokumentiert in VERTRAG-Block.
- **Pruning liegt in C9b, nicht in C3**: C3 bekommt blocked=true NIE zu sehen (Precondition). Wenn C3 aufgerufen wird, ist blocked garantiert false.
- **Determinismus**: 4 Output-Felder (ausser begruendung) MUESSEN bei gleichem Input identisch sein (G15). begruendung ist Freitext-Ausnahme (W8).

## BL-134 Migration (WARNUNG)

- **Batch-Vertrag (PRIMAER):** C3 liest `DF_BATCH_STATE.batch_items[]` und schreibt `DF_BATCH_STATE.modus`/`modus_begruendung`/`pipeline_route`. Single Source of Truth fuer den Batch.
- **Modus-Override ENTFERNT (BL-405):** Der alte BL-133-Pfad (Item-Level Modus-Override aus itemContext) UND die Batch-Aggregation dieses Override-Felds sind komplett geschnitten (INV-MODUS-1-Bereinigung). C3 entscheidet den Modus ausschliesslich aus k-score/srs/coverage; reifegrad routet upstream.
- **Legacy-Audit-Slot:** `BERATER_OUTPUTS.modusEntscheidung` wird weiterhin gespiegelt fuer Audit/Backwards-Compat (gleicher Inhalt wie BATCH_STATE).
- **K-Score-Quelle:** `DF_BATCH_STATE.k_score_aggregate` (vom BatchPlanner gesetzt) hat Vorrang vor `A_PIPELINE_STATE.k_score`.
