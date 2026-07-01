---
status: active
version: 2.1.0
type: berater
parent: _IDF_orchestrate
phase: "7.5"
model_tier: middle
actor: _IDF_orchestrate Phase 7.5 — NACH batchPlan, VOR IDF_DONE
created: 2026-05-09
updated: 2026-06-11
feature: BL-207
bl_implements: BL-207
also_implements: [BL-318, BL-247]
ak_implements: [AK-1, AK-2, AK-3, AK-4, AK-5, AK-6, AK-7, AK-8, AK-9, AK-10]
ak_implements_bl318: [AK-1, AK-2, AK-4]
ak_implements_bl247: [AK-7]
predecessor_version: 1.0.0 (BL-168, heuristic-only)
contract:
  reads:
    - {file: ".claude/meta/implementation/stage_*.md", path: "frontmatter", purpose: "Discovery aller global verfuegbaren Test-Stages (stufe, name, testtyp, infrastruktur, mocks_erlaubt, fokus, concurrency_class, concurrency_depends_on). Dynamisch — neue stage_N.md automatisch verfuegbar. concurrency_class (BL-318): PARALLEL|DEPENDS|EXCLUSIVE fuer den BL-230-Scheduler."}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items_per_batch", purpose: "Sub-Batches von Phase 7 batchPlan (PFLICHT-Input)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.sequencePlanner.ordered_items", purpose: "Sequence-Position pro Item von Phase 6"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.dependencyAnalyzer.layers_per_item", purpose: "Layer-Mapping (BE-CONT, BE-CORE, BE-MAP, BE-DOMAIN, BE-VAL, BE-DTO, ...) von Phase 4"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.architecturalBrief.matched_patterns", purpose: "Pattern-Coverage (optional — fuer 'neuer Pattern → Integration noetig')"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.plBewertung.per_batch_risk_class", purpose: "Risk-Class pro Batch (BL-207 AK-5 NEU — data_loss|breaking_api|behavior_drift|ui_only|trivial)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.patternBrief.twin_available_per_batch", purpose: "Twin-Verfuegbarkeit pro Batch (BL-207 AK-6 NEU — aus SDF Phase 1.5 patternBrief-Output)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.plBewertung.per_batch_code_anchors", purpose: "Code-Anchors pro Batch (BL-207 AK-2 NEU — welche Files werden beruehrt)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.allowed_stages", purpose: "allowed_stages: int[] — Whitelist erlaubter Test-Stages (BL-224 AK-3 NEU). Filter ueber global_stages_discovered: planned_stages/batch_stages ⊆ allowed_stages. Backward-Compat: fehlt/leer → Fallback global_stages_discovered (kein Filter)."}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.available_stages", purpose: "available_stages: int[] — ZWEITE, orthogonale Gate-Stufe NACH allowed_stages (BL-247 AK-7 NEU). Eine Stage laeuft nur wenn allowed UND available (ihre concurrency_depends_on-Ressourcen FREE). Verfuegbarkeit wird LIVE aus stage_resource_registry.lookup_free gelesen (.locks/-Zustand, SOA-1), NICHT aus der .md. Backward-Compat: fehlt/leer → KEIN Filter (heutiges Verhalten). LOCKED → BL-318-soft-defer (AK-9)."}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_stages", purpose: "Per-Sub-Batch Test-Stage-Map {batch_N: [1, 3, 6]} fuer SDF Outer-Loop (BL-168 Konsumption)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.stage_begruendung_per_batch", purpose: "Per-Sub-Batch Stage-Begruendung-Map {batch_N: 'reasoning...'} (BL-207 AK-4 NEU — Begruendungs-Vektor pro Stage)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.stage_rationale_per_batch", purpose: "Per-Sub-Batch stage_rationale Dict {stage_id: reason} (BL-207 AK-4 NEU — maschinenlesbar)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.stage_concurrency_per_batch", purpose: "Per-Sub-Batch Nebenlaeufigkeits-Map {batch_N: {stage_id: PARALLEL|DEPENDS|EXCLUSIVE}} (BL-318 AK-2 NEU — der BL-230-Scheduler liest das, um EXCLUSIVE zu serialisieren und PARALLEL-Wellen zu planen). 100% Coverage: jede geplante Stage hat einen Wert, NIE null (INV-STAGE-11)."}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.stagePlanner", purpose: "Audit-Slot mit global_stages_discovered, batch_stages, stage_begruendung_per_batch, stage_rationale_per_batch, risk_class_per_batch, twin_note_per_batch, concurrency_class_per_stage_global, stage_concurrency_per_batch (BL-318)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items (Phase 7-Output)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items_per_batch (Phase 7-Output)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.batchPlan (Phase 7-Output)"}
---

# _IDF_berater_stagePlanner (Phase 7.5) — v2.0.0 (BL-207)

## Zweck

**SRP-Trennung von BL-168:** batchPlan macht Batches, stagePlanner macht Stages.

**BL-207 Upgrade:** Stage-Wahl wird von Heuristik auf **Vektor-basierte Entscheidung** umgestellt.
Pro Sub-Batch entscheidet stagePlanner welche Test-Stages (1=Unit, 3=Integration,
6=E2E, 7=Journey ...) relevant sind. Entscheidung basiert auf Multi-Signal-Vektor:

```
VEKTOR (BL-207 INV-STAGE-1):
  {
    layer_mix,          # welche Schichten im Batch
    sequence_pos,       # Reife-Indikator (Code schon vorhanden?)
    risk_class,         # data_loss | breaking_api | behavior_drift | ui_only | trivial
    twin_available,     # Schwester-Pattern vorhanden?
    code_anchors,       # welche Files konkret beruehrt
    new_pattern         # architectural Pattern neu eingeführt?
  }
```

Jede Stage-Wahl braucht einen `stage_rationale`-Eintrag (AK-4). Kein "aus dem Hut".

## VERTRAG

```
╔════════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _IDF_berater_stagePlanner (Phase 7.5) — v2.0.0 BL-207       ║
╠════════════════════════════════════════════════════════════════════════╣
║  POSITION:                                                              ║
║    NACH Phase 7 batchPlan (Batches existieren)                          ║
║    VOR  Phase 8 IDF_DONE                                                ║
║                                                                         ║
║  LIEST:                                                                 ║
║    .claude/meta/implementation/stage_*.md (Glob, dynamische Discovery)  ║
║    DF_BATCH_STATE.batch_items_per_batch[]  (von Phase 7)               ║
║    BERATER_OUTPUTS.sequencePlanner.ordered_items  (von Phase 6)        ║
║    BERATER_OUTPUTS.dependencyAnalyzer.layers_per_item  (von Phase 4)   ║
║    BERATER_OUTPUTS.architecturalBrief.matched_patterns  (optional)     ║
║    BERATER_OUTPUTS.plBewertung.per_batch_risk_class    (NEU BL-207)    ║
║    BERATER_OUTPUTS.patternBrief.twin_available_per_batch (NEU BL-207)  ║
║    BERATER_OUTPUTS.plBewertung.per_batch_code_anchors  (NEU BL-207)    ║
║    IDF_PIPELINE_STATE.allowed_stages: int[]            (NEU BL-224)    ║
║      Whitelist erlaubter Stages — batch_stages ⊆ allowed_stages.       ║
║      Fehlt/leer → Fallback global_stages_discovered (kein Filter).     ║
║    IDF_PIPELINE_STATE.available_stages: int[]          (NEU BL-247)    ║
║      2. orthogonale Gate-Stufe NACH allowed_stages: Stage laeuft nur   ║
║      wenn allowed UND available (concurrency_depends_on FREE laut      ║
║      stage_resource_registry.lookup_free, NICHT .md). Fehlt/leer →     ║
║      kein Filter (Backward-Compat). LOCKED → BL-318-soft-defer (AK-9). ║
║                                                                         ║
║  SCHREIBT:                                                              ║
║    DF_BATCH_STATE.batch_stages              (PRIMAER)                  ║
║    DF_BATCH_STATE.stage_begruendung_per_batch  (menschenlesbar)        ║
║    DF_BATCH_STATE.stage_rationale_per_batch    (NEU BL-207, dict)      ║
║    DF_BATCH_STATE.stage_concurrency_per_batch  (NEU BL-318 —          ║
║      {batch_N: {stage_id: PARALLEL|DEPENDS|EXCLUSIVE}}, 100% Coverage) ║
║    BERATER_OUTPUTS.stagePlanner             (Audit-Slot)               ║
║                                                                         ║
║  INVARIANTEN:                                                          ║
║    INV-STAGE-1: Stage-Wahl basiert auf VEKTOR {layer, risk_class,      ║
║                 twin_avail, sequence_pos, code_anchors}, NICHT Defaults ║
║                 (BL-207 Upgrade — ersetzt alte Skalar-Heuristik)       ║
║    INV-STAGE-2: Stage 1 PFLICHT in jedem Batch (Unit-Tests immer)      ║
║    INV-STAGE-3: batch_stages[batch_key] ⊆ global_stages_discovered     ║
║                 (≤-Subset, nie Stages ausserhalb der bekannten)         ║
║    INV-STAGE-4: E2E (Stage mit testtyp=controller-e2e) NUR wenn:       ║
║                 BE-CONT-Layer ODER risk_class IN [data_loss, breaking_api]║
║                 (BL-207 Erweiterung — nicht mehr nur sequence_pos >= 4) ║
║    INV-STAGE-5: stage_begruendung_per_batch UND stage_rationale_per_batch║
║                 PFLICHT (Audit-Trail, BL-207 AK-4)                     ║
║    INV-STAGE-6: risk_class DEFAULT = "behavior_drift" wenn nicht gesetzt ║
║                 (BL-207 AK-10 Backward-Compat)                         ║
║    INV-STAGE-7: twin_available DEFAULT = false wenn nicht gesetzt       ║
║                 (BL-207 AK-6 Backward-Compat)                          ║
║    INV-STAGE-8: Stage 6 ist TEUER — nur hinzufuegen wenn Mehrwert klar ║
║                 (BL-207 AK-3 Cost-Benefit)                             ║
║    INV-STAGE-9: stage_rationale[N].note WENN twin_full_match + trivial ║
║                 — dokumentiert dass Reduktion moeglich waere (BL-207)  ║
║    INV-STAGE-10: batch_stages[batch_key] ⊆ allowed_stages (BL-224 AK-3)║
║                 Whitelist-Filter NACH Vektor-Wahl, VOR Subset-Check.   ║
║                 allowed_stages fehlt/leer → Fallback                   ║
║                 global_stages_discovered (Backward-Compat, kein Filter)║
║    INV-STAGE-11: 100% concurrency-Coverage (BL-318 AK-2) — JEDE Stage  ║
║                 in batch_stages hat einen concurrency_class-Wert in    ║
║                 stage_concurrency_per_batch, NIE null. Messkriterium   ║
║                 BL-230 Z98.                                            ║
║    INV-STAGE-12: EXCLUSIVE-Default (BL-318) — fehlt concurrency_class  ║
║                 in einer stage_N.md (z.B. neue Stage ohne Backfill),   ║
║                 default = EXCLUSIVE (sicher: nie faelschlich           ║
║                 parallelisieren) + WARN. Conservatism over throughput. ║
║    INV-STAGE-AVAIL: available_stages-Filter (BL-247 AK-7) — ZWEITE     ║
║                 Gate-Stufe NACH allowed_stages, orthogonal: Stage      ║
║                 laeuft nur wenn allowed UND available (alle ihre       ║
║                 concurrency_depends_on FREE laut lookup_free). LOCKED  ║
║                 → Stage raus → BL-318-soft-defer (AK-9, KEINE neue     ║
║                 Wartelogik). Default leer = kein Filter (Backward-     ║
║                 Compat). Stage-1-Floor (INV-STAGE-2) bleibt erzwungen. ║
║                                                                         ║
║  ACTOR:                                                                 ║
║    _IDF_orchestrate Phase 7.5 — Skill(_IDF_berater_stagePlanner)       ║
║                                                                         ║
║  MODELL-TIER: middle (sonnet) — Vektor-Analyse mit Frontmatter-Parsing ║
║                                                                         ║
║  EXIT-CODES:                                                           ║
║    0 = SUCCESS (batch_stages + stage_rationale geschrieben)            ║
║    1 = WARN (kein Layer-Mapping vorhanden, fallback auf Stage 1 only)  ║
║    2 = FAIL (stage_*.md nicht lesbar oder DF_BATCH_STATE corrupt)      ║
╚════════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_IDF_berater_stagePlanner, args="{BL_ID}")

Vorbedingung (alle PASS, sonst SKIP/FAIL):
  - DF_BATCH_STATE.batch_items_per_batch != null (Phase 7 DONE)
  - BERATER_OUTPUTS.sequencePlanner gesetzt (Phase 6 DONE)
  - BERATER_OUTPUTS.dependencyAnalyzer gesetzt (Phase 4 DONE)
```

## PFAD-RESOLUTION (KRITISCH — BL-168 INV-STAGE-1, BL-392 AK-CONSUMER-REWRITE Update)

**Kanonische Stage-Resolution laeuft ueber `resolve_vault_stage` (Dual-Read) — NICHT mehr per Direkt-Glob.**

BL-392 verlagert die Stage-Docs vom repo-lokalen Monolith `.claude/meta/implementation/stage_N.md`
in atomare, Vault-residente 8-Slice-Saetze (`{VAULT}/Stage/stage_N_<name>/`). Die WO-Aufloesung
(welche Stage liegt wo, welcher Slice) ist ab jetzt EINMAL zentralisiert im read-only Resolver
`resolve_vault_stage.py` — der stagePlanner globt **nicht** mehr selbst (das war der W-CONS-1-Wildwuchs).

**INV-STAGE-1 (BL-392-Neufassung):** Stage-Discovery + Slice-Read laufen ueber die kanonische
`resolve_vault_stage`-Resolution. Pro Stage-Nummer `n`:

1. **`resolve_stage(n)`** globt `{VAULT}/Stage/stage_{n}_*/` (Postfix, genau-1-Match) via
   `resolve_vault_root()`-SSoT und liefert einen `StageHandle` (Slice-Satz: `_index`/`execute`/
   `setup`/`teardown`/`health_check`/`resources`/`concurrency_class`/`exit_criteria`).
2. Der stagePlanner liest fuer die Discovery NUR die noetigen Concern-Slices — `_index`
   (stufe/name) + `resources`/`concurrency_class` (infrastruktur, concurrency_class/depends_on) —
   statt das ganze Doc (W-SLICE-2 single unit of work).
3. **Dual-Read-Fallback (Backward-Compat, W-VAULT-1):** ist eine Stage noch NICHT migriert
   (kein Vault-Slice-Verzeichnis), faellt `resolve_stage(n)` IN-MEMORY auf den Legacy-Monolith
   `.claude/meta/implementation/stage_N.md` zurueck (via `STAGE_DISCOVERY_HINT.repo_path`-cwd
   bzw. der `_resolve_legacy_monolith`-Walkup) und liefert die Slice-Views aus dessen Frontmatter.
   So koexistieren migrierte + nicht-migrierte Stages waehrend der Umstellung — IDENTISCHES
   Discovery-Ergebnis wie heute, nur via Resolver.
4. **HARTE FAIL bei kein Match:** `resolve_stage(n)` == None → FAIL "Stage n nicht aufloesbar
   (weder Vault-Slice noch Legacy-Monolith)". NICHT auf `T_ORCHESTRATE_STATE.stages_planned`
   ausweichen — das verletzt INV-STAGE-1.

**Anti-Pattern (BUG aus 1. Re-Run 2026-05-09 — bleibt verboten):**
- FALSCH: `glob(./Implementation/stage_*.md)` / `glob(./SC/stage_*.md)` (falscher Pfad).
- FALSCH: jeder Consumer globt `.claude/meta/implementation/stage_*.md` selbst (W-CONS-1-Wildwuchs).
- FALSCH: Fallback auf `T_ORCHESTRATE_STATE.stages_planned=[1,3,6]` als "global stages".
- RICHTIG: `resolve_vault_stage.resolve_stage(n)` (Vault-Slice-Satz, sonst Legacy-Monolith-Fallback) —
  EINE Zentralstelle, kein Per-Consumer-Glob mehr (BL-392 AK-GLOB/AK-CONSUMER-REWRITE).

> Hinweis: Der nachstehende `glob(...stage_*.md)`-Pseudocode (SCHRITT 1) beschreibt die heutige
> Discovery-Mechanik und wird beim Code-Consumer-Rewrite (AK-CONSUMER-REWRITE-PL-1) durch den
> `resolve_vault_stage`-Aufruf ersetzt; die Discovery-Felder (stufe/name/infrastruktur/
> concurrency_class) kommen dann aus den `_index`/`resources`/`concurrency_class`-Slices.

---

## Logik (v2.0.0 — Vektor-basiert)

### SCHRITT 0: Vektor-Inputs lesen

```
# Backward-Compat: alle neuen Inputs haben Defaults (INV-STAGE-6/7)
risk_class_map    = BERATER_OUTPUTS.plBewertung?.per_batch_risk_class ?? {}
twin_avail_map    = BERATER_OUTPUTS.patternBrief?.twin_available_per_batch ?? {}
code_anchors_map  = BERATER_OUTPUTS.plBewertung?.per_batch_code_anchors ?? {}

# allowed_stages Whitelist (BL-224 AK-3) — Backward-Compat: fehlt/leer → kein Filter
allowed_stages    = IDF_PIPELINE_STATE?.allowed_stages ?? []   # int[]
Logge: "[stagePlanner v2] allowed_stages={allowed_stages} (leer = kein Filter, Fallback global_stages_discovered)"

# risk_class Enum (BL-207 AK-5)
RISK_CLASS_ENUM = {
  "data_loss":     4,   # hoechste Prioritaet fuer E2E
  "breaking_api":  3,   # API-Vertrag gebrochen → E2E zwingend
  "behavior_drift": 2,  # default — Verhalten aendert sich, Integration noetig
  "ui_only":       1,   # reine UI-Aenderung → Journey, kein E2E
  "trivial":       0    # minimale Aenderung
}

Logge: "[stagePlanner v2] risk_class_map={risk_class_map}"
Logge: "[stagePlanner v2] twin_avail_map={twin_avail_map}"
```

### SCHRITT 1: Discovery global verfuegbarer Stages

```
global_stages = {}
FOR f IN glob("{STAGE_DISCOVERY_HINT.repo_path}/.claude/meta/implementation/stage_*.md"):
  fm = parse_frontmatter(f)
  stage_id = fm.stufe                    # int (1, 2, 3, ...)
  global_stages[stage_id] = {
    name:           fm.name,             # "Atomic", "Integration", "Controller-E2E"
    testtyp:        fm.testtyp,          # "powershell-verification", "integration", "controller-e2e"
    infrastruktur:  fm.infrastruktur,    # "docker", "real-system", oder null
    mocks_erlaubt:  fm.mocks_erlaubt,    # ja/nein
    fokus:          fm.fokus,
    fanout:         fm.fanout,
    parallelitaet:  fm.ressourcen_constraints?.parallelitaet_max,
    # --- BL-318 (G1-Writer): Nebenlaeufigkeits-Klasse fuer den BL-230-Scheduler ---
    concurrency_class:      fm.concurrency_class ?? "EXCLUSIVE",   # INV-STAGE-12 Default
    concurrency_depends_on: fm.concurrency_depends_on ?? []
  }
  IF fm.concurrency_class == null:
    Logge: "[stagePlanner v2.1] WARN INV-STAGE-12: stage_{stage_id} ohne concurrency_class → Default EXCLUSIVE (sicher). Backfill stage_{stage_id}.md empfohlen."

Logge: "[stagePlanner v2] discovered {|global_stages|} global stages: {sorted(global_stages.keys())}"
Logge: "[stagePlanner v2.1] concurrency_class_per_stage_global={{sid: s.concurrency_class FOR sid,s IN global_stages.items()}}"
```

### SCHRITT 2: Pro Sub-Batch Vektor-basierte Stage-Entscheidung

```
batches       = DF_BATCH_STATE.batch_items_per_batch
sequence      = BERATER_OUTPUTS.sequencePlanner.ordered_items
layers_map    = BERATER_OUTPUTS.dependencyAnalyzer.layers_per_item
patterns      = BERATER_OUTPUTS.architecturalBrief?.matched_patterns ?? []

batch_stages                = {}
stage_begruendung_per_batch = {}
stage_rationale_per_batch   = {}
risk_class_per_batch        = {}
twin_note_per_batch         = {}
stage_concurrency_per_batch = {}   # BL-318 AK-2: {batch_N: {stage_id: PARALLEL|DEPENDS|EXCLUSIVE}}

FOR i, batch_items IN enumerate(batches):
  batch_key    = "batch_" + str(i+1)
  layers       = collect_layers(batch_items, layers_map)
  sequence_pos = max_sequence_position(batch_items, sequence)
  code_anchors = code_anchors_map.get(batch_key, [])

  # INV-STAGE-6: Backward-Compat Default
  risk_class   = risk_class_map.get(batch_key, "behavior_drift")
  twin_avail   = twin_avail_map.get(batch_key, false)

  risk_class_per_batch[batch_key] = risk_class
  risk_priority = RISK_CLASS_ENUM.get(risk_class, 2)

  # INV-STAGE-2: Unit immer
  stages       = [1]
  stage_rationale = {1: "PFLICHT (alle Batches, INV-STAGE-2)"}

  # --- Stage 3: Integration ---
  # Datenschicht-Layer brauchen echten DB-Kontext
  data_layers = [l FOR l IN layers IF l IN ["BE-CORE", "BE-MAP", "BE-DOMAIN", "BE-VAL", "BE-SVC"]]
  IF data_layers:
    integration_stage = find_stage(global_stages, testtyp="integration")
    IF integration_stage:
      stages.append(integration_stage.id)
      stage_rationale[integration_stage.id] = (
        "Layer {data_layers} → Daten-Logik braucht realen DB-Kontext (keine Mocks)")

  # Neuer architectural Pattern → Integration-Verifikation
  ELIF has_new_pattern(batch_items, patterns):
    integration_stage = find_stage(global_stages, testtyp="integration")
    IF integration_stage AND integration_stage.id NOT IN stages:
      stages.append(integration_stage.id)
      stage_rationale[integration_stage.id] = (
        "Neuer Pattern eingeführt → Integration-Verifikation der Pattern-Implementierung")

  # behavior_drift mit Code-Anchors → Integration wenn API-Schnittstellen beruehrt
  ELIF risk_class == "behavior_drift" AND has_api_anchors(code_anchors):
    integration_stage = find_stage(global_stages, testtyp="integration")
    IF integration_stage AND integration_stage.id NOT IN stages:
      stages.append(integration_stage.id)
      stage_rationale[integration_stage.id] = (
        "behavior_drift + API-Code-Anchors → Integration zur Schnittstellen-Verifikation")

  # --- Stage 6: E2E (TEUER — INV-STAGE-8, AK-3 Cost-Benefit) ---
  e2e_stage = find_stage(global_stages, testtyp="controller-e2e")
  needs_e2e = false
  e2e_reason = null

  IF "BE-CONT" IN layers:
    needs_e2e = true
    e2e_reason = "Controller-Endpoint → HTTP-Durchstich mit Token zwingend"

  ELIF risk_class == "breaking_api":
    needs_e2e = true
    e2e_reason = "breaking_api → API-Vertrag-Aenderung muss E2E verifiziert werden"

  ELIF risk_class == "data_loss":
    needs_e2e = true
    e2e_reason = "data_loss-Risiko → E2E mit DB-Persistenz-Verifikation zwingend"

  # INV-STAGE-4: sequence_pos pruefung NUR als Zusatz-Guard wenn kein Risk-Trigger
  ELIF has_endpoint(batch_items) AND sequence_pos >= 4:
    needs_e2e = true
    e2e_reason = "Endpoint + sequence_pos={sequence_pos} >= 4 (Code-Reife-Guard)"

  IF needs_e2e AND e2e_stage:
    stages.append(e2e_stage.id)
    stage_rationale[e2e_stage.id] = e2e_reason

  # --- Stage 7: Journey/FE ---
  fe_layers = [l FOR l IN layers IF l IN ["FE-COMP", "FE-FORM", "FE-SVC"]]
  IF fe_layers:
    journey_stage = find_stage(global_stages, testtyp="journey")  # oder "browser-state"
    IF journey_stage AND journey_stage.id NOT IN stages:
      stages.append(journey_stage.id)
      stage_rationale[journey_stage.id] = (
        "Layer {fe_layers} → Browser-State und User-Interaktion (FE-Journey)")

  # ui_only ohne FE-Layer-Mapping
  ELIF risk_class == "ui_only" AND NOT fe_layers:
    journey_stage = find_stage(global_stages, testtyp="journey")
    IF journey_stage AND journey_stage.id NOT IN stages:
      stages.append(journey_stage.id)
      stage_rationale[journey_stage.id] = (
        "risk_class=ui_only → Journey-Verifikation der UI-Interaktion")

  # --- INV-STAGE-9: Twin-Note (kein Reduzierer, aber Marker) ---
  twin_note = null
  IF twin_avail AND risk_class == "trivial":
    twin_note = "twin_full_match + trivial → Stage-Reduktion moeglich (manuell pruefen)"
    stage_rationale["twin_note"] = twin_note
  twin_note_per_batch[batch_key] = twin_note

  # --- INV-STAGE-10: allowed_stages Whitelist-Filter (BL-224 AK-3) ---
  # Whitelist-Semantik: planned_stages ⊆ allowed_stages. Filter NACH Vektor-Wahl.
  # Backward-Compat (INV-STAGE-10 Default): allowed_stages leer → KEIN Filter
  #   (Fallback global_stages_discovered = heutiges Verhalten, batch_stages unveraendert).
  # Worked example: allowed_stages=[1] → planned_stages=[1] only
  #   (Vektor haette z.B. [1,3] gewollt, aber 3 ∉ [1] → herausgefiltert; Stage 1 bleibt).
  IF allowed_stages != []:
    int_stages = [s FOR s IN stages IF isinstance(s, int)]
    filtered   = [s FOR s IN int_stages IF s IN allowed_stages]
    # INV-STAGE-2 bleibt unverletzt: Stage 1 ist immer in stages; sollte allowed_stages
    # 1 ausschliessen, ist das ein Whitelist-Konflikt → Stage 1 bleibt erzwungen (Pflicht-Floor).
    IF 1 NOT IN filtered:
      filtered = [1] + filtered
      stage_rationale["allowed_stages_floor"] = (
        "INV-STAGE-2 Pflicht-Floor: Stage 1 trotz allowed_stages={allowed_stages} erzwungen")
    dropped = [s FOR s IN int_stages IF s NOT IN allowed_stages]
    IF dropped:
      stage_rationale["allowed_stages_filter"] = (
        "INV-STAGE-10: Stages {dropped} nicht in allowed_stages={allowed_stages} → herausgefiltert")
    stages = filtered
    Logge: "[stagePlanner v2] {batch_key} allowed_stages-Filter: {int_stages} → {filtered}"

  # --- INV-STAGE-AVAIL: available_stages-Filter (BL-247 AK-7) ---
  # ZWEITE Gate-Stufe, ORTHOGONAL zu allowed_stages: eine Stage laeuft nur wenn
  #   allowed (Whitelist, INV-STAGE-10) UND available (Ressource gerade FREE).
  # available_stages ERSETZT allowed_stages NICHT — beide filtern hintereinander.
  # Quelle der Verfuegbarkeit = stage_resource_registry.lookup_free (LIVE .locks/-Zustand,
  #   SOA-1), NICHT die .md (die ist nur Mensch-Spiegel). Eine Stage ist "available"
  #   gdw ALLE ihre non-shareable resource(s) FREE sind.
  # BACKWARD-COMPAT (PFLICHT, INV-STAGE-AVAIL Default): available_stages leer/fehlt →
  #   KEIN Filter → heutiges Verhalten unveraendert (Plan unveraendert).
  # Worked example: Stage 3 (DEPENDS docker_integration_stack) LOCKED von anderem Lauf
  #   → 3 raus aus stages → Plan via BL-318-soft-defer (AK-9) umgebaut (KEINE neue Wartelogik).
  available_stages = IDF_PIPELINE_STATE?.available_stages ?? []   # int[] (Default leer = kein Filter)
  IF available_stages != []:
    int_stages = [s FOR s IN stages IF isinstance(s, int)]
    # Pro Stage: ALLE concurrency_depends_on-Ressourcen muessen FREE sein.
    # PARALLEL-Stages (Stage 1) haben normal keine non-shareable resource → immer available.
    avail = []
    FOR s IN int_stages:
      res_of_s = global_stages[s].concurrency_depends_on ?? []
      IF |res_of_s| == 0:
        avail.append(s)                       # teilbar → immer available
      ELSE:
        free_map = stage_resource_registry.lookup_free(res_of_s)   # {rid: FREE|LOCKED}
        IF all(st == "FREE" FOR st IN free_map.values()):
          avail.append(s)
        ELSE:
          locked = [rid FOR rid, st IN free_map.items() IF st == "LOCKED"]
          stage_rationale["available_stages_defer"] = (
            "INV-STAGE-AVAIL (BL-247 AK-7): Stage {s} Ressource(n) {locked} LOCKED → "
            "Stage raus, BL-318-soft-defer (AK-9, keine neue Wartelogik)")
          Logge: "[stagePlanner v2.1+247] {batch_key} Stage {s} not-available (LOCKED {locked}) → soft-defer"
    # INV-STAGE-2-Floor: Stage 1 bleibt IMMER erhalten (analog allowed_stages_floor).
    #   Stage 1 ist PARALLEL/teilbar (AK-10), hat normal keine non-shareable resource —
    #   sie sollte hier gar nicht herausfallen, der Floor ist die fail-safe Garantie.
    IF 1 NOT IN avail:
      avail = [1] + avail
      stage_rationale["available_stages_floor"] = (
        "INV-STAGE-2 Pflicht-Floor: Stage 1 trotz available_stages-Filter erzwungen (teilbar)")
    stages = avail
    Logge: "[stagePlanner v2.1+247] {batch_key} available_stages-Filter: {int_stages} → {avail}"

  # --- INV-STAGE-3: Subset-Check ---
  assert all(s IN global_stages.keys() FOR s IN stages IF isinstance(s, int)), (
    "INV-STAGE-3 verletzt: Stage {s} nicht in global_stages_discovered")

  batch_stages[batch_key] = sorted([s FOR s IN stages IF isinstance(s, int)])
  stage_begruendung_per_batch[batch_key] = build_readable_begruendung(
    stages, stage_rationale, layers, risk_class, twin_avail, sequence_pos)
  stage_rationale_per_batch[batch_key] = stage_rationale

  # --- BL-318 AK-2: concurrency_class pro geplante Stage aufloesen (100% Coverage) ---
  # INV-STAGE-11: jede Stage in batch_stages bekommt EINEN Wert, NIE null.
  # Quelle = global_stages[stage_id].concurrency_class (mit INV-STAGE-12 EXCLUSIVE-Default
  # bereits in SCHRITT 1 aufgeloest). Der BL-230-Scheduler liest diese Map.
  stage_concurrency_per_batch[batch_key] = {
    s: global_stages[s].concurrency_class           # PARALLEL | DEPENDS | EXCLUSIVE
    FOR s IN batch_stages[batch_key]
  }
  # INV-STAGE-11 Assertion: kein null in der Map
  assert all(v IN ["PARALLEL","DEPENDS","EXCLUSIVE"]
             FOR v IN stage_concurrency_per_batch[batch_key].values()), (
    "INV-STAGE-11 verletzt: null/unbekannte concurrency_class in {batch_key}")

  Logge: "[stagePlanner v2] {batch_key} layers={layers} risk={risk_class} "
         "twin={twin_avail} pos={sequence_pos} → stages={batch_stages[batch_key]} "
         "concurrency={stage_concurrency_per_batch[batch_key]}"
```

### SCHRITT 3: Persist

```
Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE.batch_stages = batch_stages)
Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE.stage_begruendung_per_batch = stage_begruendung_per_batch)
Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE.stage_rationale_per_batch = stage_rationale_per_batch)
Edit({WORKING_DIR}/_manifest.md, DF_BATCH_STATE.stage_concurrency_per_batch = stage_concurrency_per_batch)  # BL-318 AK-2

concurrency_class_per_stage_global = {sid: s.concurrency_class FOR sid, s IN global_stages.items()}

Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.stagePlanner = {
  version:                  "2.1.0",
  bl_implements:            "BL-207",
  also_implements:          "BL-318",
  global_stages_discovered: sorted(global_stages.keys()),
  batch_stages:             batch_stages,
  stage_begruendung_per_batch: stage_begruendung_per_batch,
  stage_rationale_per_batch:   stage_rationale_per_batch,
  risk_class_per_batch:     risk_class_per_batch,
  twin_note_per_batch:      twin_note_per_batch,
  concurrency_class_per_stage_global: concurrency_class_per_stage_global,  # BL-318
  stage_concurrency_per_batch:        stage_concurrency_per_batch,         # BL-318 AK-2
  ts:                       now(),
  last_berater:             "stagePlanner"
})
```

### SCHRITT 4: Audit + Exit

```
Logge: "[stagePlanner v2] DONE — {|batches|} batches, Vektor-basierte Stage-Wahl"
RETURN exit_code=0
```

---

## Hilfsfunktionen

### build_readable_begruendung

```
FUNKTION build_readable_begruendung(stages, stage_rationale, layers, risk_class, twin_avail, sequence_pos):
  lines = []
  FOR stage_id IN sorted(stages):
    IF isinstance(stage_id, int):
      reason = stage_rationale.get(stage_id, "kein Grund dokumentiert")
      lines.append(f"Stage {stage_id}: {reason}")
  IF twin_avail:
    lines.append(f"Twin verfuegbar (risk={risk_class})")
  IF stage_rationale.get("twin_note"):
    lines.append(f"Note: {stage_rationale['twin_note']}")
  RETURN " | ".join(lines)
```

### has_api_anchors

```
FUNKTION has_api_anchors(code_anchors):
  api_patterns = [".controller.", "Controller", "endpoint", "route", "api/", "/api"]
  RETURN any(pattern IN anchor FOR anchor IN code_anchors FOR pattern IN api_patterns)
```

### has_endpoint

```
FUNKTION has_endpoint(batch_items):
  RETURN any("Controller" IN item OR "Endpoint" IN item OR "endpoint" IN item
             FOR item IN batch_items)
```

---

## Vektor-Entscheidungs-Tabelle (BL-207 INV-STAGE-1)

| risk_class | layer_mix | twin_avail | sequence_pos | → stages | Begruendung |
|---|---|---|---|---|---|
| trivial | BE-DTO only | nein | egal | [1] | Minimal-Aenderung, kein Netz-Kontext noetig |
| trivial | BE-DTO only | ja | egal | [1] + note | Twin voll verfuegbar — manuell pruefen ob Stage 1 reicht |
| behavior_drift | BE-DTO + BE-CORE | nein | egal | [1, 3] | Daten-Logik → DB-Kontext noetig |
| behavior_drift | BE-CONT | nein | < 4 | [1, 3] | Controller aber noch frueh → kein E2E |
| behavior_drift | BE-CONT | nein | >= 4 | [1, 3, 6] | Controller + Code-Reife → E2E |
| breaking_api | BE-CONT | egal | egal | [1, 3, 6] | API-Vertrag gebrochen → E2E zwingend |
| data_loss | beliebig | egal | egal | [1, 3, 6] | Data-Loss-Risiko → E2E mit DB-Persistenz |
| ui_only | FE-COMP | nein | egal | [1, 7] | FE-Komponente → Browser-State/Journey |
| behavior_drift | BE-MAP + BE-VAL | nein | egal | [1, 3] | Mapping/Validation → Integration |
| behavior_drift | beliebig | nein | egal | [1] | Kein Datenschicht-Layer, kein API-Anker |

---

## Backward-Compat (BL-207 AK-10)

| Fehlender Input | Default | Verhalten |
|---|---|---|
| `per_batch_risk_class` nicht in BERATER_OUTPUTS | "behavior_drift" pro Batch | INV-STAGE-6 |
| `twin_available_per_batch` nicht in BERATER_OUTPUTS | false pro Batch | INV-STAGE-7 |
| `per_batch_code_anchors` nicht in BERATER_OUTPUTS | [] pro Batch | leer, has_api_anchors=false |
| `IDF_PIPELINE_STATE.allowed_stages` nicht gesetzt/leer | `[]` (kein Filter) | INV-STAGE-10 Fallback `global_stages_discovered` — heutiges Verhalten unveraendert |

## allowed_stages Whitelist-Filter (BL-224 AK-3)

`allowed_stages: int[]` ist ein **Whitelist-Filter** ueber dem vorhandenen
`global_stages_discovered`-Pool. Er greift NACH der Vektor-basierten Stage-Wahl
(SCHRITT 2) und VOR dem INV-STAGE-3 Subset-Check.

**Whitelist-Semantik (INV-STAGE-10):**

```
planned_stages ⊆ allowed_stages
```

Nur Stages, die sowohl der Vektor waehlt ALS AUCH in `allowed_stages` enthalten sind,
landen in `batch_stages[batch_key]`. Stage 1 bleibt als INV-STAGE-2 Pflicht-Floor
immer erhalten (auch wenn `allowed_stages` sie faelschlich ausschliesst).

**Worked example:**

| allowed_stages | Vektor-Wahl (vor Filter) | → batch_stages (nach Filter) |
|---|---|---|
| `[1]` | `[1, 3]` | `[1]` (3 herausgefiltert, da 3 ∉ [1]) |
| `[1, 3]` | `[1, 3, 6]` | `[1, 3]` (6 herausgefiltert) |
| `[1, 3, 6]` | `[1, 3]` | `[1, 3]` (alle erlaubt, kein Drop) |
| `[]` (leer/fehlt) | `[1, 3, 6]` | `[1, 3, 6]` (Backward-Compat: kein Filter) |

**Backward-Compat-Default:** Fehlt `IDF_PIPELINE_STATE.allowed_stages` oder ist leer (`[]`),
findet KEIN Filter statt — `batch_stages` ergibt sich allein aus `global_stages_discovered`
und der Vektor-Wahl (heutiges Verhalten, INV-STAGE-10 Fallback).

**Regression-Test:** DCSRE-486-Batches muessen mit v2.0.0 GLEICHE oder BESSERE
Stage-Zuordnung kriegen als mit v1.0.0 (BL-207 AK-8):

```
batch_v3_01_be_core_constants:    v1=[1,3]   v2=[1,3]   ✓ (BE-CORE + behavior_drift)
batch_v3_04_be_controller_service: v1=[1,3,6] v2=[1,3,6] ✓ (BE-CONT + pos=4)
batch_v3_05_fe_form_validation:    v1=[1,7]   v2=[1,7]   ✓ (FE-FORM layer)
batch_v3_10_fe_twin_refactor:      v1=[1]     v2=[1]+note ✓ (trivial + twin=true)
```

---

## concurrency_class — G1-Writer fuer BL-230 (BL-318)

`concurrency_class` ist die Antwort auf die eine Scheduler-Frage: **Duerfen zwei Batches
DIESE Test-Stage gleichzeitig laufen?** Das Feld ist eine STAGE-Eigenschaft (lebt in
`stage_N.md`), der stagePlanner hebt sie pro geplanter Stage in `stage_concurrency_per_batch`.
Geschrieben hier (Writer-Haelfte). Gelesen vom Motor-Scheduler in **BL-230 AK-G1-CC**
(Reader-Haelfte — nicht dieser BL).

### Drei Werte (Semantik)

| Wert | Bedeutung | Scheduler-Verhalten | Typische Stage |
|---|---|---|---|
| **PARALLEL** | Keine geteilte mutable Host-Ressource (gemockt, kein Docker, keine fixen Ports, bin/obj per-Worktree). | N Batches gleichzeitig — PARALLEL-Welle. | Stage 1 (Unit), Stage 2 (Module) |
| **DEPENDS** | Teilbar ABER ressourcen-beschraenkt: geteilte Ressource bedient mehrere Konsumenten nur koordiniert (Container-Budget, geteilter Docker-Stack). Traegt `concurrency_depends_on`. | Parallel bis Ressourcen-Cap, sonst **Defer**. | Stage 3 (Integration, `container_isolation` + `max_container_parallel`) |
| **EXCLUSIVE** | Host-Singleton, nicht teilbar (fixe Port-Bindung, `parallelitaet_max=1`, destruktives globales `docker-compose down -v`). | Global serialisiert. | Stage 4/5/6 (System/E2E/Controller-E2E, Port 5443/5080) |

### Konflikt-Policy: EXCLUSIVE = Defer-statt-Warten (AK-4, BL-230 Kritiker #7)

Trifft der Scheduler auf eine EXCLUSIVE-Stage, deren Singleton bereits von einem anderen
Batch gehalten wird, **wartet er NICHT blockierend** — er **defert** den Batch (re-queue,
arbeitet derweil an einem unabhaengigen PARALLEL-Batch weiter). Begruendung: blockierendes
Warten verschwendet einen ganzen Worker-Slot fuer eine garantiert-belegte Ressource; Defer
haelt den Durchsatz oben. DEPENDS folgt derselben Policy am Ressourcen-Cap.

Dieser Vorentscheid ist **Input fuer die BL-247-A-Pipeline** (Verfuegbarkeits-/Ressourcen-
Registry): BL-247 formalisiert die Singleton-Registry + den Defer→Re-Queue-Trigger. Der
Defer selbst MUSS — sobald der Scheduler ihn ausloest — ein Folge-Work-Item materialisieren,
NICHT nur ein Prosa-Marker sein (siehe **BL-323**, maschinen-strukturelle Defer-Materialisierung).

### 100%-Coverage + Default (INV-STAGE-11/12)

- **INV-STAGE-11:** Jede Stage in `batch_stages` hat einen Wert in `stage_concurrency_per_batch`
  — NIE `null` (Messkriterium BL-230 Z98). Der Writer assertet das pro Batch.
- **INV-STAGE-12:** Fehlt `concurrency_class` in einer `stage_N.md` (neue Stage ohne Backfill),
  default = **EXCLUSIVE** + WARN. Konservativ: lieber faelschlich serialisieren (Durchsatz-
  Verlust) als faelschlich parallelisieren (Ressourcen-Race). Conservatism over throughput.

### Forward-Verify (AK-5)

`concurrency_class` muss in einem ECHTEN IDF-Lauf erscheinen (`stage_concurrency_per_batch`
im Manifest belegt), BEVOR der 230-Reader gebaut wird — ein Deploy-Zyklus Vorlauf. Erster
Live-Beleg = naechster IDF-Lauf nach Redeploy (z.B. ein 1944/486/Haupt-Batch).

### Worked example (DCSRE-486 6-Batch-Beispiel von unten)

```yaml
DF_BATCH_STATE.stage_concurrency_per_batch:
  batch_1: {1: PARALLEL}                          # [1]      reine Unit-Welle
  batch_2: {1: PARALLEL, 3: DEPENDS}              # [1,3]    Integration unter Container-Budget
  batch_3: {1: PARALLEL, 3: DEPENDS}              # [1,3]
  batch_4: {1: PARALLEL, 3: DEPENDS, 6: EXCLUSIVE}# [1,3,6]  6 serialisiert (Port 5443+5080)
  batch_5: {1: PARALLEL, 3: DEPENDS, 6: EXCLUSIVE}# [1,3,6]
  batch_6: {1: PARALLEL, 3: DEPENDS}              # [1,3]
# Scheduler-Lesart: alle batch_*.stage_1 als eine PARALLEL-Welle; stage_3 parallel bis
# max_container_parallel, sonst Defer; stage_6 von batch_4 und batch_5 NIE gleichzeitig.
```

---

## available_stages — LIVE-Verfuegbarkeits-Gate (BL-247 AK-7)

`available_stages` ist die **zweite Gate-Stufe** im SCHRITT-2-Filter, DIREKT NACH der
`allowed_stages`-Whitelist (INV-STAGE-10). Die zwei Achsen sind **orthogonal**:

| Achse | Frage | Quelle | BL |
|---|---|---|---|
| `allowed_stages` | DARF diese Stage ueberhaupt laufen (per Policy/Whitelist)? | `IDF_PIPELINE_STATE.allowed_stages` (statisch) | BL-224 |
| `available_stages` | KANN diese Stage JETZT laufen (Ressource gerade FREE)? | `stage_resource_registry.lookup_free` (LIVE) | BL-247 |

Eine Stage landet nur dann in `batch_stages`, wenn sie **allowed UND available** ist.

**Verfuegbarkeits-Lesung (SOA-1):** die Wahrheit ist der LIVE `.locks/`-Zustand, gelesen
ueber `stage_resource_registry.lookup_free(resource_ids)` → `{rid: FREE|LOCKED}`. NICHT
die `_resource_availability.md` parsen (die ist nur Mensch-/Anzeige-Spiegel und kann
stale sein). Eine Stage ist *available* gdw ALLE ihre `concurrency_depends_on`-Ressourcen
FREE sind. PARALLEL-Stages (Stage 1, kein `concurrency_depends_on`) sind immer available.

**LOCKED → soft-defer (AK-9, KEINE neue Wartelogik):** trifft der Filter eine Stage,
deren Ressource LOCKED ist, faellt die Stage aus dem Plan — die Reaktion ist der bereits
geshippte **BL-318-AK-4-soft-defer** (Batch defern, an unabhaengigem PARALLEL-Batch
weiterarbeiten). BL-247 liefert NUR den LIVE-FREE/LOCKED-Lookup, den diese bestehende
Defer-Entscheidung als Input braucht — keine eigene Warte-/Re-Queue-Logik.

**Backward-Compat (PFLICHT):** `available_stages` fehlt/leer → KEIN Filter → heutiges
Verhalten unveraendert (Plan wie ohne BL-247). **INV-STAGE-2-Floor:** Stage 1 bleibt
IMMER erhalten (analog `allowed_stages_floor`) — sie ist teilbar (PARALLEL) und faellt
normal gar nicht aus dem Filter.

### Worked example (BL-247 AK-7)

```yaml
# Vektor haette batch_4 = [1, 3, 6] gewollt (BE-CONT + breaking_api).
# allowed_stages = []  (kein Whitelist-Filter)
# available_stages != [] und stage_resource_registry.lookup_free ergibt:
#   docker_integration_stack (Stage 3 DEPENDS): LOCKED  (anderer Lauf haelt sie)
#   Stage 6 EXCLUSIVE-Singleton:                FREE
# → Stage 3 raus (Ressource LOCKED), Stage 1+6 bleiben:
batch_4: [1, 6]   # Stage 3 soft-deferred (BL-318 AK-4), Plan umgebaut
# Gegenprobe (Backward-Compat): available_stages leer → kein Filter → batch_4: [1, 3, 6]
```

---

## BL-204 Integration (AK-7)

`stage_rationale_per_batch` wird von `_IDF_berater_finalSummary` (Phase 8.0, BL-204) konsumiert.
Final-Summary-Spalten:

```
| batch_id | stages | stage_rationale_short |
| batch_1  | [1]    | Stage 1: PFLICHT      |
| batch_4  | [1,3,6]| Stage 1: PFLICHT | Stage 3: BE-CONT Daten-Logik | Stage 6: Controller+pos>=4 |
```

INV-MODUS-1 bleibt: `modus_hint` in Final-Summary = Vorhersage, NICHT Vertrag.

---

## Heuristik-Tabelle v1.0 (DCSRE-Backend-Konvention 2026-05-09, als Referenz)

Die alte Heuristik-Tabelle bleibt als Referenz erhalten. v2.0.0 erweitert sie um den Vektor.

| Layer-Mix im Batch              | Sequence-Pos | → batch_stages (v1) | Differenz v2 |
|---------------------------------|--------------|---------------------|--------------|
| Nur BE-DTO                      | egal         | [1]                 | identisch    |
| BE-DTO + BE-CORE                | egal         | [1, 3]              | identisch    |
| BE-DTO + BE-MAP/BE-DOMAIN/BE-VAL| egal         | [1, 3]              | identisch    |
| BE-CONT + BE-CORE (Endpoint)    | < 4          | [1, 3]              | identisch    |
| BE-CONT + BE-CORE (Endpoint)    | >= 4         | [1, 3, 6]           | identisch    |
| Beliebig + neuer Pattern        | egal         | [1, 3, ...]         | identisch    |
| breaking_api (neu)              | egal         | N/A (v1 kannte nicht)| [1, 3, 6]  |
| data_loss (neu)                 | egal         | N/A                 | [1, 3, 6]   |
| trivial + twin (neu)            | egal         | N/A                 | [1] + note  |

---

## Beispiel (v2.0.0)

**Input** (DCSRE-486 mit 6 Sub-Batches, risk_class ergaenzt):

```
batch_1: items=[DTO_x, DTO_y]        layers=[BE-DTO]        risk=trivial   twin=false pos=1
batch_2: items=[Mapper_x]            layers=[BE-MAP]        risk=behavior_drift twin=false pos=2
batch_3: items=[Service_x]           layers=[BE-CORE]       risk=behavior_drift twin=false pos=3
batch_4: items=[Controller_x]        layers=[BE-CONT]       risk=breaking_api  twin=false pos=4
batch_5: items=[Service_y, Ctrl_y]   layers=[BE-CORE,BE-CONT] risk=data_loss  twin=false pos=5
batch_6: items=[Validator_x]         layers=[BE-VAL]        risk=behavior_drift twin=true pos=6
```

**Output:**
```yaml
DF_BATCH_STATE.batch_stages:
  batch_1: [1]          # trivial, kein DB-Layer
  batch_2: [1, 3]       # BE-MAP → Integration
  batch_3: [1, 3]       # BE-CORE → Integration
  batch_4: [1, 3, 6]    # BE-CONT + breaking_api → E2E zwingend
  batch_5: [1, 3, 6]    # BE-CORE + BE-CONT + data_loss → E2E zwingend
  batch_6: [1, 3]       # BE-VAL → Integration (twin verfuegbar aber nicht trivial)

DF_BATCH_STATE.stage_rationale_per_batch:
  batch_1:
    1: "PFLICHT (alle Batches, INV-STAGE-2)"
  batch_4:
    1: "PFLICHT (alle Batches, INV-STAGE-2)"
    3: "Layer [BE-CONT] → Daten-Logik braucht realen DB-Kontext (keine Mocks)"
    6: "breaking_api → API-Vertrag-Aenderung muss E2E verifiziert werden"
  batch_6:
    1: "PFLICHT (alle Batches, INV-STAGE-2)"
    3: "Layer [BE-VAL] → Daten-Logik braucht realen DB-Kontext (keine Mocks)"
```

---

## Changelog

### v2.2.0 (BL-247, 2026-06-14) — available_stages LIVE-Verfuegbarkeits-Gate
- **AK-7:** ZWEITE Gate-Stufe `available_stages` DIREKT NACH dem `allowed_stages`-Filter
  (INV-STAGE-AVAIL). Orthogonal zu allowed_stages: Stage laeuft nur wenn allowed UND
  available (alle `concurrency_depends_on` FREE laut `stage_resource_registry.lookup_free`,
  LIVE .locks/-Zustand SOA-1, NICHT .md). LOCKED → Stage raus → BL-318-soft-defer (AK-9,
  keine neue Wartelogik). Backward-Compat: `available_stages` leer/fehlt → kein Filter
  (heutiges Verhalten). Stage-1-Floor (INV-STAGE-2) bleibt erzwungen. Markdown-Naht
  (markdown_uncoverable), Szenario-verifiziert.

### v2.1.0 (BL-318, 2026-06-11) — G1-Writer fuer BL-230
- **AK-1:** `concurrency_class` (PARALLEL|DEPENDS|EXCLUSIVE) + `concurrency_depends_on` ins
  `stage_N.md`-Schema gehoben; SCHRITT 1 Discovery liest beide Felder in `global_stages`.
- **AK-2:** stagePlanner schreibt `DF_BATCH_STATE.stage_concurrency_per_batch`
  `{batch_N: {stage_id: class}}` bei JEDEM Plan — 100% Stage-Coverage (INV-STAGE-11).
- **AK-3:** Backfill stage_1..6.md mit `concurrency_class` (Begruendung je Stage im
  `concurrency_rationale`-Feld): 1/2=PARALLEL, 3=DEPENDS, 4/5/6=EXCLUSIVE.
- **AK-4:** Konflikt-Policy dokumentiert: EXCLUSIVE/DEPENDS = Defer-statt-Warten
  (BL-230 Kritiker #7) — als Input fuer BL-247 (Verfuegbarkeits-Registry).
- **INV-STAGE-11 NEU:** 100% concurrency-Coverage, kein null.
- **INV-STAGE-12 NEU:** EXCLUSIVE-Default + WARN bei fehlendem Feld (Conservatism over throughput).
- **Abgrenzung:** NUR der Writer. Reader/Scheduler = BL-230 AK-G1-CC. Backward-Compat:
  reines Additiv — batch_stages/stage_rationale unveraendert; alte Konsumenten ignorieren
  das neue Feld.

### v2.0.0 (BL-207, 2026-05-24)
- **INV-STAGE-1 UPGRADE:** Stage-Wahl basiert auf Vektor {layer, risk_class, twin_avail, sequence_pos, code_anchors}
- **AK-1:** stagePlanner-Logik erweitert (Vektor-basierte Stage-Wahl)
- **AK-2:** Neue Inputs: code_anchors, twin_available, risk_class (aus BERATER_OUTPUTS)
- **AK-3:** Cost-Benefit Stage 6: nur bei BE-CONT, breaking_api, data_loss, oder Endpoint+pos>=4
- **AK-4:** stage_rationale Dict pro Batch (maschinenlesbar, BL-204-Integration)
- **AK-5:** risk_class Enum definiert: data_loss|breaking_api|behavior_drift|ui_only|trivial
- **AK-6:** twin_available_per_batch aus BERATER_OUTPUTS.patternBrief gelesen
- **AK-7:** stage_rationale_per_batch → BERATER_OUTPUTS.stagePlanner → BL-204 finalSummary
- **AK-8:** Regression-Tabelle: DCSRE-486-Batches bleiben identisch mit v1.0.0
- **AK-9:** INV-STAGE-4 erweitert: risk_class-basierter E2E-Trigger (nicht nur sequence_pos)
- **AK-10:** Backward-Compat: Defaults für fehlende Inputs (INV-STAGE-6/7)
- **INV-STAGE-6/7/8/9 NEU:** Backward-Compat, Cost-Benefit, Twin-Note

### v1.0.0 (BL-168, 2026-05-09)
- Initiale Implementierung: Layer-Heuristik + sequence_pos
- INV-STAGE-1..5 etabliert
- DCSRE-Backend-Konvention: BE-CONT+pos>=4 → E2E

---

## Verlinkungen

- **BL-318** — concurrency_class-Writer (G1-Writer-Haelfte), dieses v2.1.0-Upgrade
- **BL-230** — Reader/Scheduler (AK-G1-CC) konsumiert `stage_concurrency_per_batch`; Parallelitaet
- **BL-247** — Verfuegbarkeits-/Ressourcen-Registry; bekommt Defer-statt-Warten-Vorentscheid als Input
- **BL-323** — Defer MUSS ein Folge-PL-Item materialisieren (maschinen-strukturell), nicht Prosa
- **BL-207** — Stage-Spezialist, dieses Upgrade implementiert
- **BL-168** — IDF Stages-Planning Backlog-Item, Vorversion v1.0.0
- **BL-204** — Final-Summary konsumiert stage_rationale_per_batch (AK-7)
- **BL-203** — PL-Bewertung liefert risk_class + code_anchors als Input (AK-5)
- **BL-166** — SDF Outer-Loop konsumiert `batch_stages` in STAGE-INNER-LOOP
- **BL-169** — I-Pipeline `--stage=N` Param ist die Konsumption pro Stage
- **stage_*.md** — Source-of-Truth fuer global verfuegbare Stages
