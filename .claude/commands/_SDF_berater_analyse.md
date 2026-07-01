---
status: active
version: 1.0.0
created: 2026-04-26
op: SmallDarkFactory
phase: 1.0
type: berater
chain_position: middle
model_tier: middle
parent: _SDF_orchestrate
actor: _SDF_orchestrate — Phase 1.0 (vor Modus-Entscheidung)
sdf_quelle: Z495-562
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.phase", purpose: "Completion-Check"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items", purpose: "Batch-Size-Evaluation"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "Items", purpose: "LOC-Schaetzung + Komplexitaet pro Item"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.current_worker", purpose: "null nach A-Completion"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.last_completed", purpose: "ANALYSE"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items", purpose: "ggf. Sub-Batch (BATCH-SPLIT)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_total", purpose: "ggf. Sub-Batch Laenge"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_split", purpose: "true/false"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_remaining", purpose: "zurueckgestellte Items"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.analyse", purpose: "a_phase + abbruch_grund"}
  writes_not:
    - A_PIPELINE_STATE (schreibt _A_orchestrate selbst)
    - DF_PIPELINE_STATE.df_status (kein State-Transition hier)
---

# /_SDF_berater_analyse (Phase 1.0 — A-Pipeline + Batch-Size-Evaluation)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_analyse (Phase 1.0)                           ║
╠══════════════════════════════════════════════════════════════════════╣
║  EINGABE: NAME, difficulty, ceiling, floor (aus SDF-Kontext)         ║
║  LIEST: A_PIPELINE_STATE.phase (Completion-Check)                    ║
║         DF_BATCH_STATE.batch_items (Batch-Size-Evaluation)           ║
║         {VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md: LOC + Komplexitaet ║
║  SCHREIBT: DF_PIPELINE_STATE.{current_worker=null, last_completed}   ║
║            DF_BATCH_STATE.{batch_items, batch_total, batch_split,    ║
║              batch_remaining} (NUR bei BATCH-SPLIT)                  ║
║            BERATER_OUTPUTS.analyse.{a_phase, abbruch_grund?}         ║
║  RUFT: Skill(_A_orchestrate) — Handschuh-Wechsel                     ║
║  ACTOR: _SDF_orchestrate Phase 1.0                                   ║
║  MODELL-TIER: sonnet                                                  ║
║  INVARIANTEN:                                                         ║
║    INV-1: A-Pipeline MUSS status=COMPLETED liefern — sonst ABBRUCH   ║
║    INV-2: A liefert Aggregat-Daten (INV-A-RAW-DATA), KEINE Mode-Dec. ║
║    INV-3: Batch-Split-Heuristik: LOC > 200 ODER > 2 HIGH-Items       ║
║    INV-4: ANTI-PATTERN: spawn_agent("/_A_orchestrate") VERBOTEN      ║
║           NUR Skill()-Handschuh-Wechsel erlaubt                       ║
╚══════════════════════════════════════════════════════════════════════╝
```

## INPUT / OUTPUT

```
INPUT:
  NAME        - Feature-Name (aus SDF-Kontext)
  difficulty  - easy | normal | hard
  ceiling     - haiku | sonnet | opus
  floor       - haiku | sonnet

OUTPUT (BERATER_OUTPUTS.analyse):
  a_phase:      "COMPLETED" | "ABORTED"   # Status der A-Pipeline
  abbruch_grund: {String}                  # NUR bei ABORTED: Fehlermeldung
```

## Pseudocode

```
df_state_transition(ANALYSE, 1, "a-sdf-analyse", "Starting A-Pipeline")

# ═══ HANDSCHUH-WECHSEL: SDF → A_orchestrate ═══
# ANTI-PATTERN: spawn_agent(command="/_A_orchestrate ...") ← VERBOTEN
# RICHTIG: Team Lead laedt A-Skill SELBST. EINE Instanz, nur Handschuh-Wechsel.
# State ueberlebt im Manifest (DF_PIPELINE_STATE bleibt erhalten).
Skill(skill="_A_orchestrate", args="{NAME} {difficulty} {ceiling} {floor}")
# Nach A-Completion: Team Lead ist ZURUECK im SDF-Kontext.

# A_PIPELINE_STATE auswerten (aus Manifest)
Lies A_PIPELINE_STATE aus {WORKING_DIR}/_manifest.md
IF A_PIPELINE_STATE.phase != "COMPLETED":
  Logge FEHLER: "A-Pipeline nicht abgeschlossen: {A_PIPELINE_STATE.phase}"
  Schreibe {WORKING_DIR}/_manifest.md → BERATER_OUTPUTS.analyse:
    a_phase:      A_PIPELINE_STATE.phase
    abbruch_grund: "A-Pipeline FAIL — phase={A_PIPELINE_STATE.phase}"
  df_state_transition(ABORTED, 1, null, "A-Pipeline FAIL")
  → ABBRUCH

# A liefert Aggregat-Daten (INV-A-RAW-DATA), KEINE Mode-Decision.
# Mode-Decision (M1..M9) macht C3 (_SDF_berater_modusEntscheidung) in Phase 1.
# DF_BATCH_STATE.modus + pipeline_route sind nach Phase 1 die alleinige Wahrheit.
Logge: "A-Pipeline DONE. Aggregat-Daten im Manifest. C3 entscheidet Modus in Phase 1."

DF_PIPELINE_STATE.current_worker = null
DF_PIPELINE_STATE.last_completed = "ANALYSE"

# ═══ BATCH-SIZE-EVALUATION (#6, RF-SDF-006b) ═══
# Nach A-Pipeline: Evaluiere ob Batch zu gross fuer einen SDF-Durchlauf.
# Heuristik: Batch-LOC > 200 ODER > 2 HIGH-Items → Sub-Batch empfohlen.
# Problem: Grosser Batch (z.B. 3 KRITISCH-Items) sprengt Context-Budget.
# Loesung: SDF kuerzt Batch, verbleibende Items bleiben offen → BDF naechster Lauf.
IF batch_items.length > 1:
  batch_loc_estimate = 0
  batch_high_count = 0
  FUER JEDEN item_id IN batch_items:
    pl_item = lies {VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md → suche Item mit ID/Name = {item_id}
    # LOC-Schaetzung aus PL-Beschreibung parsen (z.B. "~100-200 LOC" → 150)
    item_loc = parse_loc_midpoint(pl_item.beschreibung) ?? 50
    item_komplexitaet = parse_complexity(pl_item.beschreibung) ?? komplexitaet_global
    batch_loc_estimate += item_loc
    IF item_komplexitaet IN ["HIGH", "HOCH"]:
      batch_high_count += 1

  IF batch_loc_estimate > 200 OR batch_high_count > 2:
    # Sub-Batch: Behalte 1 Item bei HIGH, 2 bei MEDIUM
    max_items = 1 wenn batch_high_count > 0 SONST 2
    max_items = min(max_items, batch_items.length)
    sub_batch = batch_items[0..max_items]
    remaining = batch_items[max_items..]

    Logge: "[BATCH-SPLIT] Batch zu gross ({batch_loc_estimate} LOC, {batch_high_count} HIGH-Items)."
    Logge: "[BATCH-SPLIT] Sub-Batch: {sub_batch.length} behalten, {remaining.length} zurueck an BDF."
    FUER item IN remaining:
      Logge: "[BATCH-SPLIT]   Zurueckgestellt: {item}"

    # Batch reduzieren — verbleibende Items bleiben [ ] in PL
    batch_items = sub_batch
    DF_BATCH_STATE.batch_items = sub_batch
    DF_BATCH_STATE.batch_total = sub_batch.length
    DF_BATCH_STATE.batch_split = true
    DF_BATCH_STATE.batch_remaining = remaining
    manifest.update()
  ELSE:
    Logge: "[BATCH-EVAL] Batch-Groesse OK ({batch_loc_estimate} LOC, {batch_high_count} HIGH)."
    DF_BATCH_STATE.batch_split = false
# ═══ ENDE BATCH-SIZE-EVALUATION ═══

# Output schreiben
Schreibe {WORKING_DIR}/_manifest.md → BERATER_OUTPUTS.analyse:
  a_phase: "COMPLETED"
```

## INVARIANTEN

```
INV-1: A_PIPELINE_STATE.phase != "COMPLETED" → ABBRUCH mit BERATER_OUTPUTS.analyse.abbruch_grund.
INV-2: A_orchestrate liefert NUR Aggregat-Daten. Mode-Decision macht C3, NICHT dieser Berater.
INV-3: Batch-Split-Schwellwert: LOC > 200 OR HIGH-Items > 2.
INV-4: Handschuh-Wechsel IMMER via Skill(_A_orchestrate) — KEIN spawn_agent().
INV-5: last_completed="ANALYSE" MUSS nach erfolgreicher A-Pipeline gesetzt sein (Resume-Signal).
```
