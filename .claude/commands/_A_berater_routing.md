---
status: active
version: 0.2.1
type: berater
parent: _A_orchestrate
phase: phase_5
model_tier: middle
created: 2026-04-25
updated: 2026-05-15
feature_anchor: BL-142
optional: false
changelog_0_2_1: |
  v0.2.1 (2026-05-15, BL-165 PL-2-01): Naming-Disambiguierung.
    - DF_BATCH_STATE.routing_decision (NEU, BDF-Post-A) vs DF_BATCH_STATE.modus (SDF M1..M9) getrennt.
    - Berater schreibt NICHT DF_BATCH_STATE.modus (SDF-exklusiv, Owner: _SDF_berater_modusEntscheidung).
    - Berater schreibt NICHT DF_BATCH_STATE.routing_decision (das macht der BDF-Caller nach A-Phase).
    - Leser-Hinweis in contract.not_writes explizit eingetragen.
changelog_0_2_0: |
  v0.2.0 (2026-05-06): Skelett -> produktiv.
    - 2-Path-Binary (IDF | DIRECT_I) mit Threshold-Tabelle.
    - Reifegrad-aware: UNREIF/SC-REIF/REIF beeinflusst Routing.
    - INV-RT-4 NEU: Berater spawnt NICHT IDF (W7-Compliance) — setzt Flag.
contract:
  reads:
    - {file: "_session_params.md", path: "GLOBAL_MODUS", purpose: "easy/normal/hard fuer Routing-Path"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.aggregat_*", purpose: "Aggregat-Metadaten als Heuristik"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.derived_name / modus", purpose: "Feature-Anker + fresh/resync (A_PIPELINE_STATE.modus ∈ {fresh, resync} — NICHT BDF routing_decision)"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.routing_target", purpose: "IDF | DIRECT_I (2-Path-Binary)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.pl_pre_filled_after", purpose: "true wenn plAggregation.status=DONE (BL-197 AK-7, INV-ROUTING-1)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.routing", purpose: "Schema (s.u.) inkl. idf_entry_phase + pl_pre_filled (BL-197 AK-7)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser routing)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.modus / derived_name / aggregat_*"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.routing_decision", note: "BL-165: routing_decision (refine|proceed|defer) wird vom BDF-Caller nach A-Phase gesetzt, NICHT hier"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.modus", note: "BL-165: SDF-Execution-Modus (M1..M9) ist exklusiv Owner von _SDF_berater_modusEntscheidung"}
  calls:
    - "Skill(_IDF_orchestrate, args={NAME}) — bei routing_target=IDF (LETZTER Schritt)"
---

# _A_berater_routing (Phase 5 in _A_orchestrate)

> **Zweck:** LETZTER Schritt der A-Pipeline. 2-Path-Binary: IDF oder DIRECT_I. Triggert IDF bei Bedarf.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_routing                                         |
+======================================================================+
|  LIEST:                                                              |
|    _session_params.md                                                |
|      GLOBAL_MODUS (easy | normal | hard)                             |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      A_PIPELINE_STATE.aggregat_k_score                               |
|      A_PIPELINE_STATE.aggregat_gap                                   |
|      A_PIPELINE_STATE.aggregat_reifegrad                             |
|      A_PIPELINE_STATE.aggregat_aks_count                             |
|      A_PIPELINE_STATE.derived_name                                   |
|      A_PIPELINE_STATE.modus                                          |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      A_PIPELINE_STATE.routing_target = "IDF" | "DIRECT_I"            |
|      A_PIPELINE_STATE.pl_pre_filled_after = true|false (BL-197 AK-7) |
|      BERATER_OUTPUTS.routing = {                                     |
|        target, decision_reason, idf_invoked,                         |
|        idf_entry_phase, pl_pre_filled (BL-197 AK-7)                 |
|      }                                                               |
|                                                                      |
|  RUFT (optional, NUR wenn target=IDF):                               |
|    Skill(_IDF_orchestrate, args="{NAME}")                            |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser routing)                                |
|    A_PIPELINE_STATE.modus / derived_name / aggregat_*                |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 5 (LETZTER Schritt)                     |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Binary-Entscheidung mit Threshold-Tabelle,          |
|    kein Deep-Reasoning. IDF-Trigger ist Skill-Call.                 |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-RT-1: 2-Path-Binary (IDF | DIRECT_I), keine dritte Option    |
|    INV-RT-2: Routing ist letzter Schritt — kein nachgelagerter      |
|              Berater darf Manifest mehr aendern                     |
|    INV-RT-3: idf_invoked=true impliziert target=IDF                 |
|    INV-ROUTING-1 (BL-197 AK-7): idf_entry_phase=3.5 NUR wenn       |
|              plAggregation.status=DONE. Fehlendes Feld → null-Safe  |
|              (pl_pre_filled=false, normaler IDF-Lauf, INV-BC-1).    |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - aggregat_*-Felder gesetzt (Phase 4.2a done)                     |
|    - stateMaintain + gitTracking abgeschlossen (Phase 4.3, 4.4)      |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - A_PIPELINE_STATE.routing_target gesetzt                         |
|    - bei IDF: IDF-Skill aufgerufen                                   |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_A_berater_routing, args="{NAME}")

Parameter:
  {NAME} - Feature-Name

Ausgabe:
  - A_PIPELINE_STATE.routing_target
  - BERATER_OUTPUTS.routing
  - bei target=IDF: Skill(_IDF_orchestrate) wurde getriggert
  - Exitcode: 0=OK, 2=FAIL

Logging-Format:
  [A_ROUTE] ENTRY name={NAME} modus={easy|normal|hard}
  [A_ROUTE] EXIT duration={ms}ms target={IDF|DIRECT_I} idf_invoked={bool}
```

## Output-Schema

```yaml
A_PIPELINE_STATE:
  routing_target: "IDF"

BERATER_OUTPUTS:
  routing:
    target: "IDF"
    decision_reason: "aks_count>=3 AND modus!=easy"
    idf_invoked: true
    last_berater: "routing"
```

## Logik (v0.2.0 produktiv)

```
SCHRITT 0: Entry + Inputs
  NAME = args[0]
  Logge: "[A_ROUTE] ENTRY name={NAME}"

  manifest = Read({WORKING_DIR}/_manifest.md)
  state    = manifest.A_PIPELINE_STATE
  session  = Read("{VAULT}/_session_params.md") fallback Read(".claude/config/_session_params.md")

  difficulty         = session.difficulty ?? "normal"
  aggregat_k_score   = state.aggregat_k_score   ?? 50
  aggregat_gap       = state.aggregat_gap       ?? 0
  aggregat_reifegrad = state.aggregat_reifegrad ?? "UNREIF"
  aggregat_aks_count = state.aggregat_aks_count ?? 0
  modus              = state.modus              ?? "fresh"
  derived_name       = state.derived_name       ?? NAME

SCHRITT 1: Vorbedingung pruefen (Berater 4.2a + 4.3 + 4.4 muessen DONE sein)
  IF state.aggregat_k_score == null AND state.aggregat_aks_count == null:
    Logge: "[A_ROUTE] WARN aggregat_*-Felder leer -> metadatenAggregation noch nicht gelaufen"
    # Fail-Soft: weiter mit Defaults

SCHRITT 2: 3-Target Decision-Matrix V3 (INV-RT-1-V3, Pipeline-Hierarchie-konform)
  # REFIT-V3 2026-05-17 (User-Direct-Korrektur):
  # V2 (5-Target {BDF, SC, IDF, SDF, STOP}) war Architektur-Bullshit:
  #   - A->SC direct verletzt /_help Pipeline-Reihenfolge (SC ist Sub-Modus von SDF M4-M7)
  #   - A->SDF direct verletzt Decomp-Pflicht (ohne PL-Items kann SDF nicht starten)
  # V3: 3-Target {BDF, IDF, STOP}. A geht IMMER zu IDF (egal UNREIF/SC-REIF/REIF).
  # IDF entscheidet selbst: Decomp moeglich? -> ja: decomp + Phase 8.5 Auto-Chain SDF.
  #   nein (UNREIF zu stark): recheck-A via --mode=recheck.
  # SC ist erreichbar NUR via SDF Phase 1.1 modusEntscheidung (M4-M7).
  target = null
  decision_reason = ""
  skill_to_load = null
  skill_args = ""

  # PRIORITAET 1: Entry-Point + Scope Overrides
  IF entry_point == "bdf":
    target = "BDF"
    skill_to_load = null   # BDF liest completion_signal selbst via SCAN
    decision_reason = "entry_point=bdf -> BDF (resume outer-loop, BDF scannt selbst)"

  ELIF scope == "transkript-only":
    target = "STOP"
    skill_to_load = null
    decision_reason = "scope=transkript-only -> STOP (kein Routing, exit clean)"

  # PRIORITAET 2: DEFAULT -> IDF (immer, egal Reifegrad)
  ELSE:
    target = "IDF"
    skill_to_load = "_IDF_orchestrate"
    skill_args = "{derived_name} --from=direct"
    decision_reason = (
      "reifegrad={aggregat_reifegrad} + aks_count={aggregat_aks_count} + "
      "gap={aggregat_gap}% -> IDF Decomposition (PL-Items + Batch-Plan). "
      "IDF Phase 8.5 Auto-Chain zu SDF wenn Spec ready. "
      "SC ist Sub-Modus von SDF (M4-M7), via SDF Phase 1.1 modusEntscheidung erreichbar."
    )

  # Rail Guard V3 (INV-RT-RAILGUARD-V3): 3-Whitelist enforcement
  VALID_TARGETS = {"BDF", "IDF", "STOP"}
  RETIRED_TARGETS = {"DIRECT_I", "I_DIRECT", "DIRECT_SC", "SC_DIRECT"}
  INVALID_AS_A_TARGET = {"SC", "SDF", "I"}  # Skills existieren, aber A darf nicht direct routen
  IF target NOT IN VALID_TARGETS:
    IF target IN RETIRED_TARGETS:
      ABORT("INV-RT-RAILGUARD-V3 Violation: target='{target}' RETIRED (alt-Vokabular). Whitelist: {VALID_TARGETS}.")
    ELIF target IN INVALID_AS_A_TARGET:
      ABORT("INV-RT-RAILGUARD-V3 Violation: target='{target}' invalid AS A-routing target. SC/SDF/I sind erreichbar nur via IDF Phase 8.5 -> SDF Phase 1.1 modusEntscheidung. Use IDF stattdessen.")
    ELSE:
      ABORT("INV-RT-RAILGUARD-V3 Violation: target='{target}' nicht in {VALID_TARGETS}.")

SCHRITT 3: Output schreiben (INV-RT-2 Routing-LAST, INV-RT-3-V2 skill_to_load persistieren)
  Edit({WORKING_DIR}/_manifest.md, A_PIPELINE_STATE.routing_target = target)
  Edit({WORKING_DIR}/_manifest.md, A_PIPELINE_STATE.next_skill = skill_to_load)
  Edit({WORKING_DIR}/_manifest.md, A_PIPELINE_STATE.next_args = skill_args)

  # Legacy idf_invoke_required (backwards-compat, postRoute liest jetzt next_skill direkt)
  IF target == "IDF":
    Edit({WORKING_DIR}/_manifest.md, A_PIPELINE_STATE.idf_invoke_required = true)
    idf_invoked_flag = false   # Berater hat NUR Flag gesetzt, nicht selbst gerufen
  ELSE:
    Edit({WORKING_DIR}/_manifest.md, A_PIPELINE_STATE.idf_invoke_required = false)
    idf_invoked_flag = false

  # BL-197 AK-7: idf_entry_phase + pl_pre_filled (INV-ROUTING-1)
  # Liest plAggregation.status aus Manifest (von Phase 5c geschrieben).
  # null-Safety: fehlendes Feld → pl_pre_filled=false (INV-BC-1 Backward-Compat).
  pl_agg_status = Read({WORKING_DIR}/_manifest.md).BERATER_OUTPUTS.plAggregation.status ?? null
  idf_entry_phase = null
  pl_pre_filled = false
  IF pl_agg_status == "DONE":
    idf_entry_phase = "3.5"
    pl_pre_filled = true
    skill_args = "{derived_name} --from=direct"   # IDF weiss via Manifest selbst dass pl_pre_filled
    Logge: "[A_ROUTE] BL-197 INV-ROUTING-1: plAggregation.status=DONE → idf_entry_phase=3.5, pl_pre_filled=true"

  Edit({WORKING_DIR}/_manifest.md, A_PIPELINE_STATE.pl_pre_filled_after = pl_pre_filled)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.routing = {
    target: target,
    skill_to_load: skill_to_load,
    skill_args: skill_args,
    decision_reason: decision_reason,
    idf_invoked: idf_invoked_flag,
    idf_entry_phase: idf_entry_phase,
    pl_pre_filled: pl_pre_filled,
    inputs: {
      difficulty: difficulty,
      aggregat_k_score: aggregat_k_score,
      aggregat_gap: aggregat_gap,
      aggregat_klaerungsbedarf: aggregat_klaerungsbedarf,
      aggregat_reifegrad: aggregat_reifegrad,
      aggregat_aks_count: aggregat_aks_count,
      modus: modus
    },
    last_berater: "routing"
  })

SCHRITT 4: Exit
  Logge: "[A_ROUTE] EXIT target={target} idf_required={target == 'IDF'}"
  EXIT 0
```

## INV-RT-4 (NEU v0.2.0): W7-Compliance fuer IDF-Trigger
Berater spawnt KEINEN IDF-Worker (W7-Constraint: Worker spawnt keine
Sub-Agents). Stattdessen: setzt `A_PIPELINE_STATE.idf_invoke_required = true`.
Der Orchestrator (`_A_orchestrate` Phase 5) liest dieses Flag und macht
danach `Skill(_IDF_orchestrate, args="{NAME}")` ALS Handschuh-Wechsel
(Skill-Load durch Team-Lead, nicht Worker-Spawn).

## Begruendung Modell-Tier

sonnet — Binary-Decision, Threshold-Lookup, ein Skill-Call. Kein Reasoning-Bedarf.
