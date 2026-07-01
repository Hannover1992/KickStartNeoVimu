---
status: active
version: 1.0.0
created: 2026-05-24
feature: BL-204
ak_implements: [AK-1, AK-3, AK-4, AK-5, AK-6, AK-7, AK-8, AK-9]
type: berater
phase: "8.0"
chain_position: after-metricPlanner-7.6-before-IDF_DONE-8
model_tier: middle
contract:
  reads:
    - {file: "_manifest.md", purpose: "DF_BATCH_STATE.batch_items_per_batch, metric_per_batch, batch_stages, modus_begruendung_per_batch"}
    - {file: "_manifest.md", purpose: "BERATER_OUTPUTS_IDF.batchPlan.rationale (fuer 1-Satz-Komprimierung)"}
    - {file: "_manifest.md", purpose: "BERATER_OUTPUTS_IDF.dependencyAnalyzer (edges fuer depends_on)"}
    - {file: "_manifest.md", purpose: "BERATER_OUTPUTS_IDF.plBewertung (pain_signals, blocking_clarifications)"}
  writes:
    - {output: "{bl_folder}/4_Blueprint/idf_final_summary_{date}.md", purpose: "Mensch-lesbare 9-Spalten-Tabelle"}
    - {output: "_manifest.md IDF_FINAL_SUMMARY", purpose: "Maschine-lesbarer YAML-Vektor-Output"}
    - {output: "BERATER_OUTPUTS_IDF.finalSummary", purpose: "Status + Pfade"}
  not_writes:
    - modus
    - recommended_modus
    - sdf_mode
    - sdf_mode_hint
    - mode_recommendation
    - expected_sdf_mode
    - DF_BATCH_STATE (ausser IDF_FINAL_SUMMARY)
---

# _IDF_berater_finalSummary (Phase 8.0)

Liest alle IDF-Phasen-Outputs (Phase 0..7.6) READ-ONLY und konsolidiert sie in
zwei Formate: Mensch-Tabelle (9 Spalten) + Maschine-YAML (IDF_FINAL_SUMMARY).
Downstream-Konsumenten: Operator (direkt), SDF Phase 1.1 (modus_hint als Kontext).

## INVARIANTEN

- INV-RO-1: Phase 8.0 ist READ-ONLY — darf KEIN vorheriges Datenfeld aendern
- INV-MODUS-1: Schreibt NIEMALS `modus` — modus_hint ist Vorhersage, C3 entscheidet
- INV-MODUS-5: Alle verbotenen Felder in contract.not_writes
- INV-ANTIHUT-1: 1-Satz-Komprimierung NUR aus Phase-7-Rationale — keine Erfindung
- INV-DISCLAIMER-1: inv_modus_1_disclaimer PFLICHT in IDF_FINAL_SUMMARY YAML

## Ablauf

### Schritt 0: Idempotenz-Gate

```python
# [finalSummary] ENTRY
LOG "[finalSummary] Phase 8.0 gestartet"

IF BERATER_OUTPUTS_IDF.finalSummary.status == "DONE":
  LOG "[finalSummary] IDEMPOTENZ-GATE — bereits ausgefuehrt, SKIP"
  RETURN exitcode=0
```

### Schritt 1: Daten sammeln

```python
# Pflicht-Felder aus Manifest laden
batch_sequence   = DF_BATCH_STATE.batch_sequence ?? []
batch_items_map  = DF_BATCH_STATE.batch_items_per_batch ?? {}
metric_map       = DF_BATCH_STATE.metric_per_batch ?? {}
stages_map       = DF_BATCH_STATE.batch_stages ?? {}
modus_hint_map   = DF_BATCH_STATE.modus_begruendung_per_batch ?? {}
rationale_map    = BERATER_OUTPUTS_IDF.batchPlan.rationale ?? {}
pain_map         = BERATER_OUTPUTS_IDF.plBewertung.pain_signals ?? {}
dep_edges        = BERATER_OUTPUTS_IDF.dependencyAnalyzer.edges ?? []
blocking_map     = BERATER_OUTPUTS_IDF.plBewertung.blocking_clarifications ?? []

IF len(batch_sequence) == 0:
  LOG "[finalSummary] WARN: batch_sequence leer — SKIP (IDF nicht vollstaendig?)"
  RETURN exitcode=0
```

### Schritt 2: 1-Satz-Komprimierung pro Batch (INV-ANTIHUT-1)

```python
# Mini-Sub-Skill: LLM-Komprimierung NUR aus vorhandener Rationale
one_liners = {}
FOR batch_id IN batch_sequence:
  rationale = rationale_map[batch_id] ?? ""
  IF rationale == "":
    one_liners[batch_id] = batch_id  # Fallback: batch_id selbst
    CONTINUE
  # Komprimierung — Input streng begrenzt auf vorhandene Rationale
  one_liner = LLM_compress(
    prompt = f"Komprimiere in GENAU 1 Satz (max 120 Zeichen). Nur was da steht, keine Erfindung:\n{rationale}",
    max_tokens = 60
  )
  one_liners[batch_id] = one_liner[:120]  # Hard-Cap
  LOG f"[finalSummary] {batch_id}: one_liner='{one_liners[batch_id]}'"
```

### Schritt 3: Difficulty-Hint pro Batch (AK-7, deterministisch)

```python
difficulty_hints = {}
FOR batch_id IN batch_sequence:
  metric   = metric_map[batch_id] ?? {}
  items_n  = metric.items_count ?? 0
  stages_n = len(stages_map[batch_id] ?? [])
  effort   = metric.effort_bucket ?? "MEDIUM"  # aus batchPlan falls vorhanden

  IF effort == "LOW" OR (items_n <= 2 AND stages_n == 1):
    difficulty_hints[batch_id] = "S"
  ELIF effort == "HIGH" OR items_n >= 5 OR stages_n >= 3:
    difficulty_hints[batch_id] = "L"
  ELSE:
    difficulty_hints[batch_id] = "M"
```

### Schritt 4: Stage-Begruendung pro Batch (AK-6)

```python
stages_labels = {}
FOR batch_id IN batch_sequence:
  stages = stages_map[batch_id] ?? [1]
  label  = metric_map[batch_id].stages_rationale ?? ""
  IF label != "":
    stages_labels[batch_id] = f"{stages} — {label}"
  ELSE:
    stages_labels[batch_id] = str(stages)
```

### Schritt 5: modus_hint extrahieren (INV-MODUS-1 konform)

```python
modus_hints = {}
FOR batch_id IN batch_sequence:
  raw_begruendung = modus_hint_map[batch_id] ?? ""
  # Vorsicht: begruendung enthaelt modus-Entscheid — nur M{N}-Teil extrahieren
  # Suche Pattern "M[1-9]" am Anfang der Begruendung
  hint = extract_modus_hint(raw_begruendung)  # regex: r'M[1-9]'
  modus_hints[batch_id] = hint ?? "TBD"
  LOG f"[finalSummary] {batch_id}: modus_hint={modus_hints[batch_id]}"
# WICHTIG: modus_hint ist VORHERSAGE — C3 entscheidet final (INV-MODUS-1)
```

### Schritt 6: recommended_next ableiten (AK-9)

```python
# 1. Batches ohne depends_on (blocker-frei) oder bereits completed
batch_deps = {}
FOR edge IN dep_edges:
  target = edge.to
  IF target NOT IN batch_deps:
    batch_deps[target] = []
  batch_deps[target].append(edge.from)

blocker_free = [b for b in batch_sequence if b NOT IN batch_deps]

# 2. Sortiere nach k_score_avg aufsteigend (niedrigster zuerst = "leichtester Einstieg")
blocker_free.sort(key=lambda b: metric_map[b].k_score_avg ?? 99)

# 3. Max 3
recommended_next = blocker_free[:3]
LOG f"[finalSummary] recommended_next={recommended_next}"
```

### Schritt 7: Vektor-Daten zusammenstellen

```python
batch_vectors = []
FOR i, batch_id IN enumerate(batch_sequence):
  metric   = metric_map[batch_id] ?? {}
  items_n  = metric.items_count ?? 0
  items_ext = metric.items_extern_count ?? 0
  items_frz = metric.items_frozen_count ?? 0
  k_avg    = metric.k_score_avg ?? 0
  srs_max  = metric.srs_max ?? 0
  stages   = stages_map[batch_id] ?? [1]
  depends  = [e.from for e in dep_edges if e.to == batch_id]

  batch_vectors.append({
    id:              batch_id,
    sequence_pos:    i + 1,
    one_liner:       one_liners[batch_id],
    items_count:     items_n,
    items_extern_count: items_ext,
    items_frozen_count: items_frz,
    k_score_avg:     k_avg,
    k_score_max:     metric.k_score_max ?? 0,
    srs_max:         srs_max,
    modus_hint:      modus_hints[batch_id],
    stages:          stages,
    stages_rationale: stages_labels[batch_id],
    pain_signals:    pain_map[batch_id] ?? [],
    anmerkung:       metric.special_flags ?? "",
    depends_on:      depends,
    difficulty_hint: difficulty_hints[batch_id]
  })

aggregate = {
  total_batches:       len(batch_vectors),
  total_items_active:  sum(v.items_count for v in batch_vectors),
  total_items_extern:  sum(v.items_extern_count for v in batch_vectors),
  total_items_frozen:  sum(v.items_frozen_count for v in batch_vectors),
  total_items_deferred: 0,  # aus DF_BATCH_STATE.deferred falls vorhanden
  k_score_avg_overall: mean([v.k_score_avg for v in batch_vectors]),
  srs_max_overall:     max([v.srs_max for v in batch_vectors]),
  opus_required_any:   any(v.difficulty_hint == "L" for v in batch_vectors)
}
```

### Schritt 8: Mensch-Output schreiben (AK-3)

```python
# Verzeichnis erstellen falls nicht vorhanden
mkdir_if_not_exists(f"{bl_folder}/4_Blueprint/")

human_path = f"{bl_folder}/4_Blueprint/idf_final_summary_{today()}.md"

table_header = "| # | Batch | Was passiert (1 Satz) | items | k | srs | erwarteter C3 | Stages | Anmerkung |"
table_sep    = "|---|---|---|---|---|---|---|---|---|"

rows = []
FOR v IN batch_vectors:
  items_str = str(v.items_count)
  IF v.items_extern_count > 0: items_str += f" ({v.items_extern_count} ext)"
  IF v.items_frozen_count > 0: items_str += f" ({v.items_frozen_count} frz)"

  row = f"| {v.sequence_pos} | {v.id} | {v.one_liner} | {items_str} | {v.k_score_avg:.0f} | {v.srs_max:.0f} | {v.modus_hint} | {v.stages} | {v.anmerkung} |"
  rows.append(row)

disclaimer_block = """
> **INV-MODUS-1 Disclaimer:** `erwarteter C3` ist modus_hint aus IDF Phase 7 batchPlan.
> C3 (_SDF_berater_modusEntscheidung) entscheidet final pro Round.
> modus_hint != modus.
"""

Write(human_path,
  content = f"""# IDF Final Summary — {bl_id} ({today()})

{disclaimer_block}

## Batch-Uebersicht

{table_header}
{table_sep}
{chr(10).join(rows)}

## Aggregat

| Metrik | Wert |
|---|---|
| Batches total | {aggregate.total_batches} |
| Items aktiv | {aggregate.total_items_active} |
| Items extern | {aggregate.total_items_extern} |
| Items frozen | {aggregate.total_items_frozen} |
| K-Score Gesamt-Ø | {aggregate.k_score_avg_overall:.1f} |
| SRS-Max | {aggregate.srs_max_overall:.0f} |
| Opus required | {aggregate.opus_required_any} |

## recommended_next

{chr(10).join(f"- {b}" for b in recommended_next)}

## blocking_clarifications

{chr(10).join(f"- [{b.batch}] {b.item}: {b.question}" for b in blocking_clarifications) or "(keine)"}
"""
)
LOG f"[finalSummary] Mensch-Output: {human_path}"
```

### Schritt 9: Maschine-Output + BERATER_OUTPUTS schreiben (AK-4)

```python
Write(_manifest.md -> IDF_FINAL_SUMMARY = {
  generated_at:    ISO_NOW(),
  generated_by:    "_IDF_berater_finalSummary v1.0.0",
  bl_id:           bl_id,
  inv_modus_1_disclaimer: "modus_hint ist Vorhersage aus IDF Phase 7 batchPlan. C3 entscheidet final per Round in SDF Phase 1.1 via _SDF_berater_modusEntscheidung. modus_hint != modus.",
  batches:         batch_vectors,
  aggregate:       aggregate,
  recommended_next: recommended_next,
  blocking_clarifications: blocking_clarifications
})

Write(BERATER_OUTPUTS_IDF.finalSummary = {
  status:                "DONE",
  human_output_path:     human_path,
  machine_output_path:   "_manifest.md IDF_FINAL_SUMMARY block",
  batches_summarized:    len(batch_vectors),
  total_items:           aggregate.total_items_active,
  recommended_next:      recommended_next,
  blocking_clarifications: len(blocking_clarifications)
})

LOG f"[finalSummary] DONE — {len(batch_vectors)} Batches, {aggregate.total_items_active} Items"
# [finalSummary] EXIT status=OK
RETURN exitcode=0
```

## Aufruf-Kontext

Dieser Berater wird aufgerufen von:
- `_IDF_orchestrate` Phase 8.0 (nach Phase 7.6 metricPlanner, vor Phase 8 IDF_DONE)

## Graceful Degradation

| Situation | Verhalten |
|---|---|
| `batch_sequence` leer | LOG WARN + SKIP (exitcode=0) |
| Rationale fuer Batch fehlt | Fallback: batch_id als one_liner |
| `4_Blueprint/` Verzeichnis fehlt | Erstellen (mkdir) |
| `effort_bucket` fehlt | Fallback MEDIUM → difficulty_hint=M |
| `pain_signals` fehlt | Leere Liste (kein Fehler) |
| Zweiter Aufruf (idempotent) | SKIP via Idempotenz-Gate |

## Downstream-Integrationen

- **Operator**: liest `4_Blueprint/idf_final_summary_{date}.md` direkt
- **SDF Phase 1.1 _SDF_berater_modusEntscheidung**: kann `IDF_FINAL_SUMMARY.batches[*].modus_hint`
  als Kontext lesen — C3 entscheidet aber IMMER selbst (INV-MODUS-1)
- **PostBatch recalibrate**: kann `IDF_FINAL_SUMMARY.aggregate` fuer globale Metriken nutzen
