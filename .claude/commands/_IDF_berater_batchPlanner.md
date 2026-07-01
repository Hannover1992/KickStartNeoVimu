---
status: active
version: 0.2.0
type: berater
parent: _IDF_orchestrate
phase: phase_7_inner
model_tier: middle
created: 2026-04-25
feature_anchor: BL-142
optional: false
migrated_from: _SDF_berater_batchPlanner
extern_intern_scan_planned: true
contract:
  reads:
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items (k_score)", purpose: "Aggregat-K-Score"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.sequencePlanner.ordered_items", purpose: "Eingangs-Sequenz"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.validator.pruning_recommendation", purpose: "Skip-Hint"}
    - {file: "_session_params.md", path: "GLOBAL_MODUS", purpose: "Batch-Size-Default"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.current_stage", purpose: "current_stage: int — aktuelle Test-Stage des IDF-Laufs (BL-224 AK-CTX-3 NEU). Steuert Architekt-/Test-Fokus deterministisch (1=Logik/neue Tests, 3/6=Refactor/Boilerplate-Check). Backward-Compat: fehlt → Default current_stage=1 (Logik-Fokus)."}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items", purpose: "Finale Batch-Liste"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.k_score_aggregate", purpose: "Aggregat-K-Score"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.batchPlanner", purpose: "Batch-Plan-Output"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser batchPlanner)"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "(read-only)"}
  calls:
    - "EXTERN/INTERN-Scan-Subroutine (BL-142 vorgesehen)"
---

# _IDF_berater_batchPlanner (Phase 7 inner in _IDF_orchestrate)

> **Zweck:** Migriert aus SDF. Innerer Berater fuer batchPlan-Wrap. EXTERN/INTERN-Scan-Integration vorgesehen.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_batchPlanner                                  |
+======================================================================+
|  LIEST:                                                              |
|    {VAULT}/Backlog/{bl_slug}/6_PL/                       |
|      {bl_id}-parking-lot.md (k_score je Item)                        |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      BERATER_OUTPUTS.sequencePlanner.ordered_items                   |
|      BERATER_OUTPUTS.validator.pruning_recommendation                |
|    _session_params.md                                                |
|      GLOBAL_MODUS                                                    |
|    {WORKING_DIR}/_manifest.md                                        |
|      IDF_PIPELINE_STATE.current_stage: int  (NEU BL-224 AK-CTX-3)    |
|        Aktuelle Test-Stage → deterministisches Fokus-Mapping         |
|        (1=Logik, 3/6=Refactor). Default current_stage=1 wenn fehlt.  |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      DF_BATCH_STATE.batch_items                                      |
|      DF_BATCH_STATE.k_score_aggregate                                |
|      BERATER_OUTPUTS.batchPlanner = {                                |
|        batch_size, batch_items, k_score_aggregate,                   |
|        escalation_hint, extern_intern_scan_summary                   |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser batchPlanner)                           |
|    DF_BATCH_STATE.modus / pipeline_route                             |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 7 inner (gerufen von batchPlan)       |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: 1:1 aus SDF (BL-134 W7). Heuristik + Aggregat.     |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-BATCH-1..5 (1:1 uebernommen von SDF)                          |
|    INV-EXTSCAN-1: extern_intern_scan_summary nur als Hint, kein Veto|
|    INV-BPN-DEFER-1 (BL-304 AK-3): Defer-markierte PL-Items ([~] ODER |
|      DEFER-Token) raus VOR k_score/candidate-Bildung (Defense-in-    |
|      Depth am Schnitt, pl_defer_filter). Verhindert k_max-Inflation  |
|      durch ein defer-Item. Kein Ueber-Filter, orthogonal zum Modus.  |
|    INV-BPN-HETERO-1 (BL-304 AK-1/AK-2): Das Candidate-Fenster        |
|      RESPEKTIERT die effort-homogenen Sub-Cluster (clustering         |
|      SCHRITT 3.5 / INV-CL-HETERO-1) — es MISCHT NICHT trivial (k<15)  |
|      und rigorous (k>=15) Items in EINEN Batch. Das Fenster wird an   |
|      der ersten Effort-Klassen-Grenze beschnitten                     |
|      (pl_effort_split.is_heterogeneous als Re-Mix-Guard, threshold=15)|
|      So bleibt der geschnittene Batch effort-homogen -> der           |
|      UNVERAENDERTE k_max<15-M1-MULTI-Gate feuert fuer die triviale    |
|      Mehrheit. Orthogonal zum Modus (INV-MODUS-1 unberuehrt).         |
|    INV-STAGE-CTX-1 (BL-224 AK-CTX-3): current_stage steuert Fokus    |
|      deterministisch via Mapping-Tabelle (1=Logik, 3/6=Refactor).    |
|      Default current_stage=1 (Logik) wenn nicht gesetzt.             |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - sequencePlanner done                                            |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - DF_BATCH_STATE.batch_items + k_score_aggregate gesetzt          |
|    - BERATER_OUTPUTS.batchPlanner vollstaendig                       |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_batchPlanner, args="{NAME}")

Parameter:
  {NAME} - Feature-Name oder bl_id

Ausgabe:
  - DF_BATCH_STATE 2 Aggregate
  - BERATER_OUTPUTS.batchPlanner
  - Exitcode: 0=OK, 1=ESCALATE, 2=SKIP

Logging-Format:
  [IDF_BPN] ENTRY feature={NAME} sequence={n} modus={x}
  [IDF_BPN] EXIT duration={ms}ms batch={items} hint={x}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  batchPlanner:
    batch_size: 2
    batch_items: ["BL-142-PL-1", "BL-142-PL-11"]
    k_score_aggregate: 35
    escalation_hint: "SONNET_OK"
    extern_intern_scan_summary:
      extern_refs: 2
      intern_refs: 8
    last_berater: "batchPlanner"
```

## Schritte

```
SCHRITT 0a: bl_slug + bl_id aufloesen (BL-143 Erweiterung)
  bl_id = IDF_PIPELINE_STATE.bl_id  # z.B. "BL-141"

  # Stufe 1: BDF_BATCH_STATE (PRIMAER, wenn big_dark_factory=true)
  IF BDF_BATCH_STATE.bl_items != null AND not empty:
    bl_item = BDF_BATCH_STATE.bl_items.find(item => item.id == bl_id)
    IF bl_item AND bl_item.vault_path:
      bl_slug = extract_slug(bl_item.vault_path)
      Logge: "[BL-140-Pfad-Fix] bl_slug={bl_slug} (Quelle: BDF)"
      -> DONE

  # Stufe 2: IDF_PIPELINE_STATE (wenn big_dark_factory=false aber IDF aktiv)
  IF IDF_PIPELINE_STATE.bl_slug != null:
    bl_slug = IDF_PIPELINE_STATE.bl_slug
    Logge: "[BL-143-Fallback] bl_slug={bl_slug} (Quelle: IDF)"
    -> DONE

  # Stufe 3: Glob-Fallback (Vault-Suche)
  candidates = Glob("{VAULT}/Backlog/{bl_id}-*.md")
  IF |candidates| == 1:
    bl_slug = extract_filename_without_ext(candidates[0])
    Logge: "[BL-143-Fallback] bl_slug={bl_slug} (Quelle: Glob)"
    -> DONE
  ELIF |candidates| > 1:
    FAIL: "Mehrere Vault-Items fuer {bl_id} gefunden -- mehrdeutig: {candidates}"
  ELSE:
    # Stufe 4: Letzter Fallback fuer direct-Modus
    bl_slug = bl_id
    Logge: "[BL-143-Fallback] bl_slug={bl_id} (Quelle: direct, kein Vault-Item)"

SCHRITT 0b: current_stage lesen + Fokus-Mapping (BL-224 AK-CTX-3)
  # current_stage steuert den Architekt-/Test-Fokus deterministisch.
  # Backward-Compat: fehlt → Default 1 (Logik-Fokus, heutiges Verhalten).
  current_stage = IDF_PIPELINE_STATE?.current_stage ?? 1   # int, Default 1

  # Deterministisches Fokus-Mapping (SRP — eine Tabelle, kein verstreutes Inline-If):
  STAGE_FOCUS_MAP = {
    1: "logik",       # Stage 1 (Atomic/Unit): Logik-Fokus, neue Tests, isolierte Inseln
    3: "refactor",    # Stage 3 (Integration): Refactor-/Verdrahtungs-Check-Fokus
    6: "refactor"     # Stage 6 (E2E): Refactor-/Boilerplate-Check-Fokus
  }
  fokus = STAGE_FOCUS_MAP.get(current_stage, "logik")   # unbekannte Stage → Default Logik
  Logge: "[IDF_BPN] current_stage={current_stage} → fokus={fokus} (BL-224 AK-CTX-3)"

SCHRITT 0: Entry-Log + Skip-Guard
  Logge: "[IDF_BPN] ENTRY feature={NAME} sequence_size={|sequencePlanner.ordered_items|} modus={GLOBAL_MODUS}"
  IF BERATER_OUTPUTS.validator.pruning_recommendation == "SKIP_DOWNSTREAM":
    BERATER_OUTPUTS.batchPlanner = {batch_size: 0, batch_items: [], k_score_aggregate: 0, escalation_hint: "SKIPPED", extern_intern_scan_summary: null}
    EXIT 2
  IF sequencePlanner.ordered_items.length == 0:
    BERATER_OUTPUTS.batchPlanner = {batch_size: 0, batch_items: [], k_score_aggregate: 0, escalation_hint: "EMPTY", extern_intern_scan_summary: null}
    EXIT 2

SCHRITT 1: Eigentliche Logik (Heuristik + Aggregat)
  vault_pl  = read({VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md)

  # BL-304 AK-3 (INV-BPN-DEFER-1, Defense-in-Depth am Schnitt): Defer-markierte
  # PL-Items ([~] ODER DEFER-Token) raus, BEVOR k_scores/candidates gebildet werden —
  # sonst inflationiert ein defer-Item (z.B. DCSRE-486 T2076) den k-Schnitt. sequencePlanner
  # filtert bereits (INV-SQ-DEFER-1); dieser Filter haelt auch ohne Sequenz-Wrap dicht.
  # Kanonischer Filter: .claude/scripts/pl_defer_filter.py -> filter_active_batch_items.
  # KONSERVATIV: nur eindeutige Defer-Marker, kein Ueber-Filter von [ ]/[x].
  vault_pl  = filter_active_batch_items(vault_pl)
  active_ids = {item.id FOR item IN vault_pl}
  candidates_in = [id FOR id IN sequencePlanner.ordered_items IF id IN active_ids]
  Logge: "[IDF_BPN] DEFER-FILTER active={|vault_pl|} (defer-markierte ausgeschlossen, BL-304 AK-3)"

  k_scores  = {item.id: (item.frontmatter.k_score ?? 30) FOR item IN vault_pl}

  default_size = (GLOBAL_MODUS == "easy")   ? 1
               : (GLOBAL_MODUS == "hard")   ? 5
               :                              3   # normal

  candidates       = candidates_in[0 : default_size]   # BL-304 AK-3: defer-gefiltert (s. SCHRITT 1)

  # BL-304 AK-1/AK-2 (INV-BPN-HETERO-1, Re-Mix-Guard): das Candidate-Fenster darf NICHT
  # ueber eine Effort-Klassen-Grenze spannen — sonst mischt es einen trivialen (k<15) mit
  # einem schweren (k>=15) Item in EINEN Batch und reisst die Triviale wieder nach M2 (genau
  # der Defekt, den clustering SCHRITT 3.5 upstream behoben hat). clustering liefert bereits
  # effort-homogene Sub-Cluster; dieser Guard haelt den Schnitt auch dann homogen, wenn die
  # Sequenz mehrere Sub-Cluster aneinanderreiht. Kanonischer Primitiv (EINE Wahrheit, wie
  # clustering SCHRITT 3.5): .claude/scripts/pl_effort_split.py.
  #   is_heterogeneous(items, threshold=15) -> True gdw. k_max>=15 UND ∃ k<15. threshold=15
  #   = die EXISTIERENDE M1-MULTI-Decke (KEIN neuer Magic-Number). None-k_score -> rigorous.
  cand_items = [{id: id, k_score: k_scores[id]} FOR id IN candidates]   # pl_effort_split-Item-Form
  IF is_heterogeneous(cand_items, threshold=15):   # pl_effort_split.is_heterogeneous
    # Auf die Effort-Klasse des ERSTEN Items beschneiden (Sequenz-Reihenfolge gewahrt):
    first_trivial = (k_scores[candidates[0]] ?? 30) < 15
    candidates = [id FOR id IN candidates IF ((k_scores[id] ?? 30) < 15) == first_trivial]
    Logge: "[IDF_BPN] HETERO-CUT Fenster auf Effort-Klasse beschnitten (first_trivial={first_trivial}), batch={|candidates|} (BL-304 AK-1, threshold=15)"

  k_score_per_item = [k_scores[id] FOR id IN candidates]
  aggregate        = (sum(k_score_per_item) / |k_score_per_item|) IF |k_score_per_item|>0 ELSE 0

  IF aggregate >= 70:
    escalation_hint = "OPUS_MITOSE_HINT"
    # Bei hohem k zieh den Batch enger (Risiko-Reduktion)
    candidates = candidates[0 : max(1, default_size-1)]
    k_score_per_item = [k_scores[id] FOR id IN candidates]
    aggregate        = (sum(k_score_per_item) / |k_score_per_item|) IF |k_score_per_item|>0 ELSE 0
  ELSE:
    escalation_hint = "SONNET_OK"

  Logge: "[IDF_BPN] AGGREGATE k_score={aggregate} -> {escalation_hint}"

SCHRITT 1b: EXTERN/INTERN-Scan (BL-142 Spezial — gerufen von _IDF_berater_batchPlan Phase 7)
  # Hinweis: EXTERN/INTERN-Scan integriert via Wrap durch _IDF_berater_batchPlan (Phase 7).
  # Dieser Berater nimmt das Scan-Ergebnis als extern_intern_scan_summary entgegen
  # (wird von batchPlan befuellt, hier nur in Output-Schema eingebunden).
  #
  # Falls direkt ausgefuehrt (ohne batchPlan-Wrap):
  extern_refs = 0
  intern_refs = 0
  FOR item_id IN candidates:
    pl_item = vault_pl.find(id == item_id)
    IF pl_item AND pl_item.file_refs:
      FOR ref IN pl_item.file_refs:
        IF ref.module != IDF_PIPELINE_STATE.bl_module:
          extern_refs += 1
        ELSE:
          intern_refs += 1
  extern_intern_scan_summary = {extern_refs: extern_refs, intern_refs: intern_refs}
  Logge: "[IDF_BPN] EXTERN_INTERN_SCAN extern={extern_refs} intern={intern_refs}"

SCHRITT 2: Output schreiben (DF_BATCH_STATE + BERATER_OUTPUTS.batchPlanner)
  DF_BATCH_STATE.batch_items       = candidates
  DF_BATCH_STATE.k_score_aggregate = aggregate

  BERATER_OUTPUTS.batchPlanner = {
    batch_size:               |candidates|,
    batch_items:              candidates,
    k_score_aggregate:        aggregate,
    escalation_hint:          escalation_hint,
    extern_intern_scan_summary: extern_intern_scan_summary
  }
  Aktualisiere {WORKING_DIR}/_manifest.md

SCHRITT 3: Exit-Log
  exitcode = (escalation_hint == "OPUS_MITOSE_HINT") ? 1 : 0
  Logge: "[IDF_BPN] EXIT duration={ms}ms batch={candidates} hint={escalation_hint}"
  EXIT exitcode
```

### Konkrete Tool-Anweisungen (BL-142)

Worker-Aufruf-Pattern:
1. Lies `BERATER_OUTPUTS.sequencePlanner.ordered_items` aus Manifest via Read-Tool
2. Pro Item: k_score aus Vault-Frontmatter mit Regex `k_score:\s*(\d+)`
   - Zugriff auf PL-File via Read-Tool: `pl_content = Read(pl_path)`
3. k_score_aggregate = mean of next 1-3 items (je nach GLOBAL_MODUS)
4. Batch-Heuristik anwenden (>=70 Mitose-Hint, batch_size=1; 40-69: batch=3; <40: batch=5)
5. EXTERN/INTERN-Scan: Datei-Refs aus PL-Item klassifizieren (Modul-Grenze)
6. `Edit({WORKING_DIR}/_manifest.md, ...)` setze `DF_BATCH_STATE.batch_items` + `DF_BATCH_STATE.k_score_aggregate` + `BERATER_OUTPUTS.batchPlanner`

## AK-Mapping

- **AK-2** (Vault-Pfad-Pattern): `{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md` via Slug-Lookup (SCHRITT 0a + SCHRITT 1).
- **AK-6** (Berater-Vertrag): VERTRAG-Block + INV-BATCH-1..5 + INV-EXTSCAN-1.
- **AK-13** (Pruning-Hint): `escalation_hint` (OPUS_MITOSE_HINT) + Skip-Guard via Validator.
- **AK-CTX-3** (BL-224, IDF current_stage im Input-Schema): `current_stage: int` als expliziter Input im VERTRAG-`LIEST` + `contract.reads`; deterministisches Fokus-Mapping (SCHRITT 0b) + Default `current_stage=1`.

## current_stage Input + Fokus-Mapping (BL-224 AK-CTX-3)

`current_stage: int` ist ein **expliziter Input** des IDF-Input-Vertrags (kanonisch hier
in `_IDF_berater_batchPlanner`, gemaess Spec Abschnitt 3 Endpoint-Vertrag). Er macht den
IDF-Lauf stage-bewusst, OHNE dass IDF selbst Stages durchlaeuft — der Architekt-/Test-Fokus
passt sich stage-abhaengig an.

**Deterministisches Fokus-Mapping (SRP — eine Tabelle, kein verstreutes Inline-If):**

| current_stage | fokus | Bedeutung |
|---|---|---|
| `1` | `logik` | Stage 1 (Atomic/Unit): Logik-Fokus, neue Tests, isolierte Inseln |
| `3` | `refactor` | Stage 3 (Integration): Refactor-/Verdrahtungs-Check-Fokus |
| `6` | `refactor` | Stage 6 (E2E): Refactor-/Boilerplate-Check-Fokus |
| _andere/unbekannt_ | `logik` | Fallback Logik-Fokus |

**Backward-Compat-Default:** Fehlt `IDF_PIPELINE_STATE.current_stage`, gilt
`current_stage = 1` (Logik-Fokus) — das entspricht dem heutigen Verhalten ohne
Stage-Bewusstsein (additive OCP-Erweiterung, INV-STAGE-CTX-1).

## Begruendung Modell-Tier

sonnet — wie SDF-Original (BL-134 W7). EXTERN/INTERN-Scan ist Datei-Listen-Klassifikation, kein opus-Tier noetig.
