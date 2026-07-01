---
status: active
version: 0.1.0
type: berater
parent: _A_orchestrate
phase: phase_5b
model_tier: middle
created: 2026-05-23
feature_anchor: BL-197
optional: false
changelog_0_1_0: |
  v0.1.0 (2026-05-23): Initial — BL-197 A-Pipeline absorbiert Forward-PL-Generierung.
    - Kopiert und angepasst aus _IDF_berater_akExtraktion.md (INV-NS-1: IDF unveraendert).
    - parent: _A_orchestrate statt _IDF_orchestrate.
    - Liest aus A_PIPELINE_STATE / BERATER_OUTPUTS.specParse (A-Namespace).
    - Phase 5b (parallel pro AK, nach Phase 5a specParse).
    - OQ-3: sequenziell by default (parallel-Upgrade in BL-200 vorbehalten).
contract:
  reads:
    - {file: "{VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md", path: "AK-Sektion (gezielt per AK-ID)", purpose: "Per-AK-Detailausarbeitung"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md", path: "W-Knoten / TC-Sektionen", purpose: "Model-Anchor pro AK"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/4_K-Score/k_score.md", path: "Per-AK k-score (falls vorhanden)", purpose: "Komplexitaets-Hinweis"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.specParse.aks[AK-ID]", purpose: "AK-Eintrag aus Phase 5a"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.akExtraktion[AK-ID]", purpose: "Per-AK pl_item_draft"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser akExtraktion[AK-ID])"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/3_Spec/*", path: "(read-only)"}
  calls: []
---

# _A_berater_akExtraktion (Phase 5b in _A_orchestrate)

> **Zweck:** Per-AK Detailausarbeitung — pro AK ein PL-Item-Draft. Sequenziell by default (parallel-faehig, Upgrade in BL-200).

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_akExtraktion                                    |
+======================================================================+
|  LIEST:                                                              |
|    {VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md                   |
|      AK-Sektion (gezielt per AK-ID, line_start/line_end)             |
|    {VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md                 |
|      W-Knoten / TC-Headers (Model-Anchor)                            |
|    {VAULT}/Backlog/{BL_SLUG}/4_K-Score/k_score.md                    |
|      Per-AK k-score (falls vorhanden)                                |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver)      |
|      BERATER_OUTPUTS.specParse.aks[AK-ID]                            |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                        |
|      BERATER_OUTPUTS.akExtraktion[AK-ID] = {                         |
|        ak_id, title, k_score, pl_item_draft,                         |
|        unreife_typ, dependencies[], layer_hint, status               |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser akExtraktion[AK-ID])                    |
|    andere AK-IDs (Per-AK-Schreib-Isolation)                          |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 5b (Per-AK, sequenziell by default)     |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Per-AK Section-Read + Metadaten-Aggregation,        |
|    parallel-faehig. Pro AK genau ein Worker.                        |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-AKE-1: Per-AK Schreib-Isolation (kein Cross-AK-Write)         |
|    INV-AKE-2: pl_item_draft enthaelt id, title, k_score, source_aks |
|    INV-AKE-3: unreife_typ IN {model_unreif, EXTERN, forward_verify,  |
|               INTERN, ok, null} (BL-369 forward_verify)              |
|    INV-A-ORDER-6: Phase 5b startet erst wenn specParse DONE          |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - specParse done (BERATER_OUTPUTS.specParse vorhanden)            |
|    - BERATER_OUTPUTS.specParse.aks[AK-ID] vorhanden                 |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - BERATER_OUTPUTS.akExtraktion[AK-ID] vollstaendig                |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_A_berater_akExtraktion, args="{NAME}|{AK-ID}")

Parameter:
  {NAME}  - Feature-Name (aus A_PIPELINE_STATE.derived_name)
  {AK-ID} - AK-Identifier (z.B. "AK-3")

Ausgabe:
  - BERATER_OUTPUTS.akExtraktion[AK-ID]
  - Exitcode: 0=OK, 2=FAIL

Logging-Format:
  [A_AKE] ENTRY name={NAME} ak={AK-ID}
  [A_AKE] EXIT duration={ms}ms k_score={n} unreife_typ={x}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  akExtraktion:
    AK-3:
      ak_id: "AK-3"
      title: "A-Orchestrate Phase 5c plAggregation"
      k_score: 62
      srs_pro_ak: 0
      pl_item_draft:
        id: "BL-197-AK-3-PL-1"
        source_aks: ["AK-3"]
        k_score: 62
        srs: 0
        title: "Phase 5c plAggregation Pseudocode in _A_orchestrate"
        layer_hint: "orchestration"
        status: "open"
      dependencies: ["AK-1", "AK-2"]
      unreife_typ: "ok"
      layer_hint: "orchestration"
      status: DONE
      last_berater: "akExtraktion"
```

## Logik (v0.1.0, sequenziell by default — OQ-3)

```
SCHRITT 0: Args + Entry-Log
  NAME, ak_id = parse_args(args)  # Format: "BL-197|AK-3"
  Logge: "[A_AKE] ENTRY name={NAME} ak={ak_id}"

SCHRITT 1: Vorbedingung pruefen (INV-A-ORDER-6)
  manifest = Read({WORKING_DIR}/_manifest.md)
  spec_parse_output = manifest.BERATER_OUTPUTS.specParse
  IF spec_parse_output == null OR spec_parse_output.status != "DONE":
    Logge: "[A_AKE] FAIL — specParse nicht DONE (INV-A-ORDER-6)"
    EXIT 2

  spec_anchor = spec_parse_output.aks[ak_id]
  IF spec_anchor == null:
    Logge: "[A_AKE] FAIL — AK-ID {ak_id} nicht in specParse.aks"
    EXIT 2

SCHRITT 2: Per-AK Spec-Section gezielt lesen
  spec_path = "{VAULT}/Backlog/{bl_slug}/3_Spec/{NAME}_Spec.md"
  IF NOT exists(spec_path):
    spec_path = ".claude/specs/{NAME}_Spec.md"

  # Gezieltes Section-Read via line_start/line_end aus Phase 5a
  section_text = Read(
    spec_path,
    offset=spec_anchor.line_start,
    limit=(spec_anchor.line_end - spec_anchor.line_start)
  )
  ak_title = spec_anchor.title ?? parse_ak_title(section_text[0])
  ak_body = section_text

SCHRITT 3: Model-Anchor matchen (W-Knoten)
  model_path = "{VAULT}/Backlog/{bl_slug}/2_Model/{NAME}_Model.md"
  IF NOT exists(model_path):
    model_path = ".claude/models/{NAME}_Model.md"

  # [BL-387 source=atomic] truth_resolver/truth_consume ist atomic-first + faellt auf legacy-Model-parse
  #   zurueck (resolve() Stufe-3) -> atom-frei heute = source=legacy == Vorher-Verhalten
  #   (backward-compat, legacy-fallback). truth_resolver UNVERAENDERT.
  # source_w via truth_resolver.resolve_truth_refs (atomic-first + kanonisches W-Lexikon _WID_TOKEN,
  #   Renumber-robust) statt Read(Model.md) + roh-W-\d+-Regex. bl_folder/vault_root aus Manifest + resolve_vault_root.
  resolved = truth_resolver.resolve_truth_refs(ak_body, bl_folder=bl_slug, vault_root=VAULT)
  w_refs = sorted(resolved.keys())   # kanonisches W-Lexikon (resolve_truth_refs/_WID_TOKEN), nicht roh-"W-\d+"
  # (Existenz-Pruefung pro Ref optional via truth_resolver.resolve(w_id, bl_folder=...).found)

SCHRITT 4: K-Score laden (Per-AK, oder Global-Fallback)
  k_score_path = "{VAULT}/Backlog/{bl_slug}/4_K-Score/k_score.md"
  IF NOT exists(k_score_path):
    k_score_path = ".claude/analysis/K-SCORE.md"

  k_score_file = exists(k_score_path) ? Read(k_score_path) : null
  IF k_score_file AND k_score_file contains ak_id:
    k_score    = parse_k_score(k_score_file, ak_id) ?? null
    srs_pro_ak = parse_srs(k_score_file, ak_id) ?? null
  ELSE:
    # Global-Fallback: A_PIPELINE_STATE.k_score
    k_score    = manifest.A_PIPELINE_STATE.k_score ?? null
    srs_pro_ak = manifest.A_PIPELINE_STATE.srs_pro_ak[ak_id] ?? 0

SCHRITT 5: Dependencies aus Spec-Refs ableiten
  ak_id_number = extract_number(ak_id)
  dependencies = []
  FOR jeden Pattern "AK-\d+" in ak_body:
    ref_num = extract_number(matched_pattern)
    IF ref_num != ak_id_number:
      dependencies.append("AK-{ref_num}")
  dependencies = dedup(dependencies)

SCHRITT 6: unreife_typ klassifizieren (INV-AKE-3)
  model_unreif_count = count_keywords(ak_body, ["TBD", "offen", "TENTATIV", "?"])
  # BL-369: Forward-Verify-dormant ZUERST erkennen (hoehere Praezedenz als EXTERN). Eine
  # Forward-Verify-Companion-AK traegt ein "external-pending"-Edge, verifiziert aber erst beim
  # NAECHSTEN Live-Lauf (Herkunft INTERN, KEINE Web-Quelle) — external-pending-Edge != EXTERN-
  # Web-Herkunft. Darf NICHT als EXTERN (= /_orakel-Web-Grounding) klassifiziert werden.
  forward_verify_hints = count_keywords(ak_body,
    ["forward-verify", "forward verify", "external-pending", "dormant", "Companion-AK", "naechsten Live-Lauf"])
  external_hints     = count_keywords(ak_body, ["extern", "drittsystem", "api", "consumer", "downstream"])
  internal_hints     = count_keywords(ak_body, ["intern", "modul", "klasse", "methode", "field", "property"])

  IF model_unreif_count >= 2:
    unreife_typ = "model_unreif"
  ELIF forward_verify_hints >= 1:
    unreife_typ = "forward_verify"   # BL-369: dormant Forward-Verify — KEIN EXTERN, kein /_orakel-Trigger
  ELIF external_hints >= 2:
    unreife_typ = "EXTERN"
  ELIF internal_hints >= 2:
    unreife_typ = "INTERN"
  ELSE:
    unreife_typ = "ok"

SCHRITT 7: layer_hint ableiten
  IF ak_body contains ("Controller" OR "Endpoint" OR "Route"):
    layer_hint = "API"
  ELIF ak_body contains ("Service" OR "Domain" OR "BL-Logik"):
    layer_hint = "Domain"
  ELIF ak_body contains ("Repository" OR "DbContext" OR "SQL"):
    layer_hint = "Persistence"
  ELIF ak_body contains ("orchestrate" OR "_orchestrate" OR "Phasen"):
    layer_hint = "orchestration"
  ELIF ak_body contains ("berater" OR "_berater_" OR "Berater-Datei"):
    layer_hint = "berater"
  ELIF ak_body contains ("test" OR "Test" OR "Smoke"):
    layer_hint = "test"
  ELSE:
    layer_hint = null

SCHRITT 8: PL-Item-Draft erzeugen (INV-AKE-2)
  pl_item_id = "{bl_id}-{ak_id}-PL-1"
  pl_item_draft = {
    id:          pl_item_id,
    source_aks:  [ak_id],
    source_w:    w_refs[0] if |w_refs| > 0 else null,
    k_score:     k_score,
    srs:         srs_pro_ak ?? 0,
    title:       ak_title,
    layer_hint:  layer_hint,
    unreife_typ: unreife_typ,
    dependencies: dependencies,
    status:      "open",
    generated_at: ISO_DATE_TODAY()
  }

SCHRITT 9: Output schreiben (INV-AKE-1 Per-AK Schreib-Isolation)
  ak_output = {
    ak_id:         ak_id,
    title:         ak_title,
    k_score:       k_score,
    srs_pro_ak:    srs_pro_ak,
    pl_item_draft: pl_item_draft,
    dependencies:  dependencies,
    unreife_typ:   unreife_typ,
    layer_hint:    layer_hint,
    w_refs:        w_refs,
    status:        "DONE",
    last_berater:  "akExtraktion"
  }
  # INV-AKE-1: nur [ak_id] schreiben, NICHT andere AK-Slots
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.akExtraktion[ak_id] = ak_output)

SCHRITT 10: Exit
  exitcode = (k_score != null) ? 0 : 0  # 0 auch bei k_score=null (Global-Fallback OK)
  Logge: "[A_AKE] EXIT k_score={k_score} unreife_typ={unreife_typ}"
  EXIT exitcode
```

## OQ-3 Notiz: Parallelitaet

Sequenziell by default (BL-197 OQ-3 aufgeloest: sequenziell fuer BL-197).
Echter Parallel-Upgrade (mehrere Worker-Spawns pro AK) in BL-200 vorbehalten.
Der Berater selbst ist parallel-faehig — der Orchestrator entscheidet ueber Spawn-Strategie.

## Begruendung Modell-Tier

sonnet — Per-AK fokussiert, klare Section-Reads, simple Aggregation + PL-Item-Draft-Erzeugung. Parallel-faehig — opus waere Overkill.
