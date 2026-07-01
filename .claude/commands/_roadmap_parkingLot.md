# /_roadmap_parkingLot {BL} — der Within-BL-Kompass (Micro)

```yaml
status: active
version: 1.0.0
created: 2026-06-19
op: RoadmapParkingLot
phase: Meta
chain_position: standalone
feature_anchor: BL-418
```

## Zweck
Zeigt **WO wir INNERHALB eines Backlog-Items stehen** — auf PL-Item- und Sub-Batch-Granularitaet.
Micro-Bruder von **`/_roadmap_backlog`** (Macro: welches BL als naechstes ueber den ganzen Backlog).
Zusammen = volle Aufloesung (welches BL × wo im BL). Read-only. Template = der DCSRE-1648-Kompass.

## Aufruf
```
/_roadmap_parkingLot {BL}        # z.B. /_roadmap_parkingLot BL-392
```

## Ablauf
```
1. bl_folder = py -3 .claude/scripts/resolve_bl_path.py {BL}
2. py -3 .claude/scripts/roadmap_parkinglot.py --bl-folder {bl_folder} --bl-id {BL}
3. Output 1:1 spiegeln (die 6 Panels). Read-only — kein Vault-Write.
```

## Die 6 Panels
1. **Pipeline-Stufen** — Intake → A-Pipeline → arc42 → IDF → SDF → Post, je `[x]`/`[~]`/`[ ]` + 1-Satz-Zustand.
2. **PL-Item-Tabelle** — PL-Item · AK · granularer K-Score (aus `4_K-Score` `ak_details.k_score_pro_ak`) ·
   Stage (aus Sub-Batch-Zuordnung) · Klassifikation (code|md|split) · Status · depends_on.
3. **Sub-Batch-Sicht** — **AUTORITATIV** (Manifest `BERATER_OUTPUTS_IDF.batchPlan` + `stagePlanner` + `batch_modes`,
   wenn IDF lief) **ODER PROJEKTION** (topologische PL-Gruppierung nach `dependencies`, vor IDF — EXPLIZIT als
   „simulierter Orchestrator, nicht autoritativ" markiert).
4. **Orchestrator-Kette mit Position** — `/_A → /_IDF → /_SDF → /_I (sub-batch a,b,c) → /_SDF_post`.
5. **Fortschritt** — **K-gewichtet** (Σ K_done / Σ K_total, ehrliche Effort-Masse) + Count-% .
6. **Naechster Befehl** — prozess-korrekt (UNREIF→A, reif→IDF, IDF-done→SDF, SDF-done→Post), Lead-self.

## Invarianten (BL-418)
- **INV-ROADMAP-PL-1:** read-only (kein Vault-/State-Write; reine Projektion des aktuellen Wissensstands).
- **INV-ROADMAP-PL-2:** Sub-Batch-Sicht vor IDF ist IMMER laut als **„nicht autoritativ — verbindlich erst nach
  IDF Phase 7/7.5/7.6 + SDF C3"** markiert (DCSRE-1648-Lehre: Projektion ≠ IDF-Ausgabe).
- **INV-ROADMAP-PL-3:** der naechste Befehl ist prozess-korrekt + Lead-self (INV-AO-CALLER) — kein Auto-Dispatch.

## Verwandt
- `/_roadmap_backlog` (Macro, `roadmap_status.py`) · `/_roadmap` (duenner Dispatcher: BL-Arg→parkingLot, sonst→backlog).
- Kern: `roadmap_parkinglot.py` (TDD: `test_roadmap_parkinglot.py`) · importiert `roadmap_status.next_command_for_bl`.
- BL-418 (Heimat) · BL-375 (Live-Observability) · BL-378 (arc42, andere View-Schicht).
