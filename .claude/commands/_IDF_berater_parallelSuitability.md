---
status: active
version: 1.0.0
type: berater
parent: _IDF_orchestrate
phase: "7.8"
model_tier: middle
actor: _IDF_orchestrate Phase 7.8 — NACH testSearch (7.7), VOR finalSummary (8.0)
created: 2026-06-15
feature: BL-342
ak_implements: [AK-1 (conflict_matrix), AK-2 (erklaerbar), AK-3 (n_cap=4 / Konsument-fail-safe), AK-6 (build_share-Daempfung)]
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items_per_batch", purpose: "Sub-Batch->Items-Map (PFLICHT-Input von Phase 7 batchPlan); die Sub-Batches deren Parallelisierbarkeit gescored wird"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.dependencyAnalyzer.file_index", purpose: "INVERTIERTER Index {datei: [item_ids]} (Phase 4) = die KANONISCHE per-Item-Pfadquelle (szenario-verifiziert gegen echtes 486-Manifest; dateien_geplant existiert real NICHT). Basis fuer ziel_dateien-Aggregation."}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_mode_hints (optional)", purpose: "NUR informativ — NICHT als change_type missbrauchen (Mode != change_type). change_type hat aktuell KEINE etablierte Quelle -> None."}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.parallel_suitability", purpose: "ADDITIV. EIN story-level Block ueber ALLE Sub-Batches: {format_version, story_type, conflict_islands, largest_island, build_share, recommended_N, suitable, reason, ziel_dateien_per_batch, matrix}. Konsument = Wellen-Scheduler BL-230 Phase C (fail-safe seriell bei fehlendem Feld)."}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.parallelSuitability", purpose: "Audit-Slot: {status, computed_at, n_sub_batches, exit_code}"}
  not_writes:
    - {path: "modus / batch_modes / batch_mode_hints / recommended_modus / sdf_mode", note: "INV-MODUS-1 + INV-MODUS-5: parallel_suitability ist ein INFO-Feld fuer den Scheduler, NIEMALS eine Modus-/Mode-Quelle. C3 (modusEntscheidung) liest es NICHT."}
    - {path: "batch_items_per_batch / batch_stages / metric_per_batch / k_score_aggregate / srs_aggregate", note: "Single-Source-Ownership (BL-313 AK-2): parallelSuitability ist reiner KONSUMENT dieser Felder."}
---

# _IDF_berater_parallelSuitability (Phase 7.8)

## Zweck

**SRP-Ergaenzung von BL-342 (Roadmap Phase 1a):** batchPlan macht Batches, stagePlanner
macht Stages, metricPlanner macht Metriken, testSearch macht Coverage — **parallelSuitability
macht die ZWEITE Graph-Achse: welche Sub-Batch-PAARE koennen gefahrlos NEBENEINANDER laufen
(found parallelism)**, nicht nur welche nacheinander muessen (depends_on). Ohne sie plant der
spaetere Wellen-Scheduler (BL-230 Phase C) blind.

**Praediktor-Oekonomie (Keller-Doktrin):** Stufe-1 = `file_index`-Ueberlappung pro Sub-Batch-Paar
(deterministisch, billig, deckt die Mehrheit; BL-316: Datei-Disjunktheit = 0-Lost-Update-Bedingung).
Stufe-2 (Small-World, semantischer Konflikt trotz Datei-Disjunktheit) = BL-297-C2 (gated, BL-361).

**Empirie (BL-353):** Parallelitaet ist SELEKTIV (Foundation fraktal) + gedeckelt (n_cap=4) +
fine-cut. Darum ist `recommended_N=1` (seriell) der NORMALFALL fuer gekoppelte/review-schwere
Stories, NICHT die Ausnahme. Der Producer ist deterministisch + erklaerbar (kein Black-Box-Score).

Output: `DF_BATCH_STATE.parallel_suitability` = EIN story-level Block ueber alle Sub-Batches
(der Producer nimmt die GANZE Sub-Batch-Liste, liefert EINEN Verdict — per-batch waere irrefuehrend).

## VERTRAG

```
╔════════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _IDF_berater_parallelSuitability (Phase 7.8) — BL-342         ║
╠════════════════════════════════════════════════════════════════════════╣
║  POSITION:                                                              ║
║    NACH Phase 7.7 testSearch (coverage_per_batch existiert)            ║
║    VOR  Phase 8.0 finalSummary                                         ║
║    Rein ADDITIV — beruehrt KEINE bestehende Naht (minimal-blast).      ║
║                                                                         ║
║  LIEST:                                                                 ║
║    DF_BATCH_STATE.batch_items_per_batch        (von Phase 7, PFLICHT)  ║
║    BERATER_OUTPUTS.dependencyAnalyzer.file_index (von Phase 4, PFLICHT)║
║      → INVERTIERTER Index {datei: [item_ids]} = per-Item-Pfadquelle     ║
║        (KANONISCH; dateien_geplant existiert real NICHT — verifiziert)  ║
║                                                                         ║
║  SCHREIBT:                                                              ║
║    DF_BATCH_STATE.parallel_suitability   (ADDITIV, story-level)        ║
║    BERATER_OUTPUTS.parallelSuitability   (Audit-Slot)                  ║
║                                                                         ║
║  INVARIANTEN:                                                          ║
║    INV-PARALLEL-1: conflict_matrix deterministisch + erklaerbar        ║
║                    (file-level Disjunktheit, BL-316). KEIN Black-Box.   ║
║    INV-PARALLEL-2: recommended_N <= n_cap (default 4). Region-Level     ║
║                    (mehr Spuren) = Stufe-2, deferred BL-361.            ║
║    INV-PARALLEL-3: suitable = (recommended_N >= 2). Bei fehlendem Feld  ║
║                    konsumiert der Scheduler konservativ seriell.        ║
║    INV-MODUS-1:    schreibt NIEMALS modus/batch_modes/sdf_mode — reines ║
║                    INFO-Feld fuer den Scheduler, NICHT Modus-Quelle.    ║
║    INV-DATENFLUSS-1: liest NUR existierende Outputs, aendert KEINE      ║
║                    Upstream-Felder (Read-Only-Intent ausser eigenem Slot)║
║                                                                         ║
║  ACTOR:                                                                 ║
║    _IDF_orchestrate Phase 7.8 — Skill(_IDF_berater_parallelSuitability)║
║                                                                         ║
║  MODELL-TIER: middle (sonnet) — Block-Extraktion + deterministischer    ║
║    Python-Compute-Call. KEIN LLM-Reasoning (Logik in Engine-.py).      ║
║                                                                         ║
║  EXIT-CODES:                                                           ║
║    0 = SUCCESS (parallel_suitability geschrieben)                     ║
║    1 = WARN (batch_items_per_batch ODER file_index fehlt/leer ->        ║
║            Trivial-Block recommended_N=1/suitable=false geschrieben,    ║
║            idf_light-kompatibel; KEIN FAIL)                            ║
║    2 = FAIL (Manifest nicht lesbar / Producer-Crash)                  ║
╚════════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_IDF_berater_parallelSuitability, args="{BL_ID}")

Vorbedingung:
  - DF_BATCH_STATE.batch_items_per_batch != null  (Phase 7 DONE)
  - BERATER_OUTPUTS.dependencyAnalyzer.file_index != null  (Phase 4 DONE)
  Fehlt eins -> WARN-Pfad (Trivial-Block, exit 1), NICHT FAIL.
```

## Logik

**Architektur (machine-not-context):** die BERECHNUNG (Konflikt-Inseln, ziel_dateien,
build_share) ist deterministisch in `.claude/scripts/parallel_suitability_producer.py`
gekapselt. Der Worker macht NUR die Manifest-I/O (Markdown lesen/schreiben — manifest_reader
kann nested file_index/matrix nicht I/O-en) und ruft den Compute-Driver via CLI.

### SCHRITT 1: Eingabe-Bloecke extrahieren

```
bipb = parse_yaml(DF_BATCH_STATE.batch_items_per_batch)        # {batch_id: [item_id,...]}
file_index = parse_yaml(BERATER_OUTPUTS.dependencyAnalyzer.file_index)  # {datei: [item_id,...]}

IF bipb == null OR len(bipb) == 0 OR file_index == null:
  Logge: "[parallelSuitability] WARN — batch_items_per_batch oder file_index fehlt/leer"
  → SCHRITT 3 mit Trivial-Block (recommended_N=1, suitable=false, story_type=trivial), exit_code=1
```

### SCHRITT 2: Deterministisch rechnen (Compute-Bridge)

```
payload = json({batch_items_per_batch: bipb, file_index: file_index})
# change_type_map NICHT setzen — keine etablierte Quelle (Mode != change_type). build_share=None
# -> AK-6-Daempfung inert bis change_type-Quelle existiert (dokumentiertes v1-Limit, Folge-BL).
block = Bash("py -3 .claude/scripts/parallel_suitability_producer.py", stdin=payload)
# block = kanonischer parallel_suitability-Block (JSON):
#   {format_version, story_type, conflict_islands, largest_island, build_share,
#    recommended_N, suitable, reason, ziel_dateien_per_batch, matrix:[{pair,status,files}]}
IF Bash exit != 0: Logge FEHLER; RETURN exit_code=2
```

### SCHRITT 3: Persist (ADDITIV)

```
Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE.parallel_suitability = block)
# ADDITIV: KEINE bestehenden DF_BATCH_STATE-Felder veraendern (guard_geist5 prueft nur
# 4 positive Pflicht-Anker, kein additionalProperties-Reject -> handoff-safe, verifiziert).

Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.parallelSuitability = {
  status:        "DONE",
  computed_at:   now(),
  n_sub_batches: len(bipb),
  recommended_N: block.recommended_N,
  suitable:      block.suitable,
  exit_code:     (1 IF warn ELSE 0)
})

Logge: "[parallelSuitability] {len(bipb)} Sub-Batches -> {block.conflict_islands} Konflikt-Inseln, recommended_N={block.recommended_N} ({block.story_type}): {block.reason}"
RETURN exit_code
```

## Beispiel (echte 486 v6-orphan file_index)

**Input** (2-Wege-Split):
```yaml
DF_BATCH_STATE.batch_items_per_batch:
  chips:    [PR2-DUC-1, PR2-DUC-3, PR2-DUC-4, PR2-DUC-5, PR2-DUC-6]
  timemask: [PR2-DUC-13]
BERATER_OUTPUTS.dependencyAnalyzer.file_index:
  autocomplete-chips-field.ts: [PR2-DUC-1, PR2-DUC-2, PR2-DUC-3, PR2-DUC-4, PR2-DUC-5, PR2-DUC-6]
  time-mask.directive.ts:      [PR2-DUC-13]
```

**Output**:
```yaml
DF_BATCH_STATE.parallel_suitability:
  format_version: "1.0"
  story_type: build-parallel
  conflict_islands: 2          # chips ⊥ timemask (disjunkte Dateien)
  recommended_N: 2
  suitable: true
  reason: "2 disjunkte Konflikt-Inseln -> N=2"
  ziel_dateien_per_batch:
    chips:    [autocomplete-chips-field.ts]
    timemask: [time-mask.directive.ts]
  matrix:
    - {pair: [chips, timemask], status: disjoint, files: []}
```

(Mit DUC-2 — dem Kopplungs-Hub, der 5 Dateien beruehrt — in EINEM Batch und DUC-7 in
einem anderen teilen beide `selbstauskunft-details-qdvtp.component.ts` -> 1 Konflikt-Insel
-> recommended_N=1 seriell. Das Foundation-fraktal-Muster aus BL-353, live an 486 belegt.)

## Verlinkungen

- **BL-342** — IDF-Parallel-Planungs-Schicht (dieser Berater = der Producer, Stufe 1)
- **BL-353** — Daten-basiertes Schneide-Modell (80/20, Foundation fraktal, selektiv+gedeckelt)
- **BL-316** — Datei-Disjunktheit = 0-Lost-Update-Bedingung (Stufe-1-Praediktor-Grundlage)
- **BL-247** — Region-Lock (Runtime-Enforcement-Schwester der Plan-Zeit-Vorhersage, MVCC)
- **BL-230 Phase C** — Wellen-Scheduler = Konsument von parallel_suitability
- **BL-297-C2 / BL-361** — Small-World-Karte (Stufe 2, gated/deferred)
- **parallel_suitability_producer.py** — deterministischer Compute-Driver (CLI-Bridge)
- **sub_batch_targets.py / parallel_suitability.py** — Substrat-Kernels (ziel_dateien / Inseln)
