---
status: DEPRECATED
deprecated_at: 2026-05-24
deprecated_by: BL-209
deprecated_reason: "Hard-Cut. _A_berater_akExtraktion (A-Pipeline Phase 5b) ist Nachfolger und Single-Source."
version: 0.2.0
type: berater
parent: _IDF_orchestrate
phase: phase_3.1
model_tier: middle
created: 2026-04-25
feature_anchor: BL-142
optional: false
contract:
  reads:
    - {file: ".claude/specs/{NAME}_Spec.md", path: "AK-Sektion (gezielt per AK-ID)", purpose: "Per-AK-Detailausarbeitung"}
    - {file: ".claude/models/{NAME}_Model.md", path: "TC-Sektionen", purpose: "Model-Anchor pro AK"}
    - {file: ".claude/analysis/K-SCORE.md", path: "Per-AK k-score (falls vorhanden)", purpose: "Komplexitaets-Hinweis"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.specParse.aks[AK-ID]", purpose: "AK-Eintrag aus Phase 2"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.akExtraktion[AK-ID]", purpose: "Per-AK ak_metadata"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser akExtraktion)"}
    - {file: ".claude/specs/*", path: "(read-only)"}
  calls: []
---

# _IDF_berater_akExtraktion (Phase 3.1 in _IDF_orchestrate)

> **Zweck:** Per-AK Detailausarbeitung — pro AK ein Metadaten-Block. Parallel-faehig.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_akExtraktion                                  |
+======================================================================+
|  LIEST:                                                              |
|    .claude/specs/{NAME}_Spec.md                                      |
|      AK-Sektion (gezielt per AK-ID)                                  |
|    .claude/models/{NAME}_Model.md                                    |
|      TC-Headers (Model-Anchor)                                       |
|    .claude/analysis/K-SCORE.md                                       |
|      Per-AK k-score (falls vorhanden)                                |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      BERATER_OUTPUTS.specParse.aks[AK-ID]                            |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      BERATER_OUTPUTS.akExtraktion[AK-ID] = {                         |
|        ak_id, title, k_score, tc_anchors[], dependencies[],          |
|        unreife_typ                                                   |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser akExtraktion[AK-ID])                    |
|    andere AK-IDs (Per-AK-Schreib-Isolation)                          |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 3.1 (Per-AK, parallel-faehig)         |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Per-AK Section-Read + Metadaten-Aggregation,        |
|    parallel-faehig. Pro AK genau ein Worker.                        |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-AKE-1: Per-AK Schreib-Isolation (kein Cross-AK-Write)         |
|    INV-AKE-2: ak_metadata enthaelt ALLE 6 Felder oder explizit null |
|    INV-AKE-3: unreife_typ IN {model_unreif, spec_unreif, ok, null}  |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - specParse done (BERATER_OUTPUTS.specParse vorhanden)            |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - BERATER_OUTPUTS.akExtraktion[AK-ID] vollstaendig                |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_akExtraktion, args="{NAME}|{AK-ID}")

Parameter:
  {NAME}  - Feature-Name
  {AK-ID} - AK-Identifier (z.B. "AK-3")

Ausgabe:
  - BERATER_OUTPUTS.akExtraktion[AK-ID]
  - Exitcode: 0=OK, 2=FAIL

Logging-Format:
  [IDF_AK] ENTRY name={NAME} ak={AK-ID}
  [IDF_AK] EXIT duration={ms}ms k_score={n} unreife_typ={x}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  akExtraktion:
    AK-3:
      ak_id: "AK-3"
      title: "Validator schreibt..."
      k_score: 35
      tc_anchors: ["TC-2", "TC-7"]
      dependencies: ["AK-1"]
      unreife_typ: "ok"
      last_berater: "akExtraktion"
```

## Logik (RF-IDF4a Critical-Berater)

```
SCHRITT 0: Args + Entry-Log
  NAME, ak_id = parse_args(args)  # z.B. "BL-142|AK-3"
  Logge: "[IDF_AK] ENTRY name={NAME} ak={ak_id}"

SCHRITT 1: Per-AK Spec-Section gezielt lesen (NICHT Volltext)
  manifest = Read({WORKING_DIR}/_manifest.md)
  spec_anchor = manifest.BERATER_OUTPUTS.specParse.aks[ak_id]
  IF spec_anchor == null:
    FAIL: "AK-{ak_id} nicht in specParse — Phase 2 zuerst laufen lassen"

  # gezieltes Section-Read via line_start/line_end aus Welle 1
  section_lines = Read(
    ".claude/specs/{NAME}_Spec.md",
    offset=spec_anchor.line_start,
    limit=(spec_anchor.line_end - spec_anchor.line_start)
  )
  ak_title = parse_ak_title(section_lines[0])
  ak_body = section_lines[1..]

SCHRITT 2: TC-Anchors aus Model matchen
  model_text = Read(".claude/models/{NAME}_Model.md")
  tc_anchors = []
  FOR jeden Pattern "TC-{n}" in ak_body:
    IF model_text contains "## TC-{n}":
      tc_anchors.append("TC-{n}")
  # zusaetzlich: explizite W{n}-Refs
  w_refs = []
  FOR jeden Pattern "W-{n}" in ak_body:
    w_refs.append("W-{n}")

SCHRITT 3: K-Score laden (oder Default)
  k_score_file = Read(".claude/analysis/K-SCORE.md", optional=true)
  IF k_score_file AND k_score_file contains ak_id:
    k_score = parse_k_score(k_score_file, ak_id)        # 0-100
    srs_pro_ak = parse_srs(k_score_file, ak_id)         # 0-100
    k_aufwand = parse_field(k_score_file, ak_id, "k_aufwand")
    k_kopplung = parse_field(k_score_file, ak_id, "k_kopplung")
    k_fragilitaet = parse_field(k_score_file, ak_id, "k_fragilitaet")
  ELSE:
    k_score = null
    srs_pro_ak = null
    k_aufwand = k_kopplung = k_fragilitaet = null

SCHRITT 4: Dependencies aus Spec-Refs ableiten
  dependencies = []
  FOR jeden Pattern "AK-{n}" in ak_body:
    IF "{n}" != ak_id_number:  # nicht selbst-referenz
      dependencies.append("AK-{n}")

SCHRITT 5: unreife_typ klassifizieren (INV-AKE-3)
  # Schwelle >= 2 Hinweise pro Kategorie -> EXTERN, sonst INTERN, sonst ok
  external_hints = count_keywords(ak_body, [
    "extern", "drittsystem", "api", "library", "framework",
    "consumer", "downstream", "abnehmer"
  ])
  internal_hints = count_keywords(ak_body, [
    "intern", "modul", "klasse", "methode", "field", "property"
  ])
  model_unreif = count_keywords(ak_body, ["TBD", "offen", "?"]) >= 2

  IF model_unreif AND |tc_anchors| == 0:
    unreife_typ = "model_unreif"
  ELIF external_hints >= 2:
    unreife_typ = "EXTERN"
  ELIF internal_hints >= 2:
    unreife_typ = "INTERN"
  ELSE:
    unreife_typ = "ok"  # Default INV-3

SCHRITT 6: layer_hint + dateien_hint ableiten
  layer_hint = null
  IF ak_body contains "Controller" OR "Endpoint": layer_hint = "API"
  ELIF ak_body contains "Service" OR "Domain":     layer_hint = "Domain"
  ELIF ak_body contains "Repository" OR "DbContext": layer_hint = "Persistence"

  dateien_hint = []
  FOR jeden Pattern "`*.cs`" OR "`*.ts`" OR Path-Pattern in ak_body:
    dateien_hint.append(matched_path)

SCHRITT 7: w_offen_count berechnen (Model-Refs ohne resolved-Status)
  w_offen_count = 0
  FOR w_id in w_refs:
    w_status = parse_w_status(model_text, w_id)
    IF w_status != "RESOLVED":
      w_offen_count += 1

SCHRITT 8: Output schreiben (INV-AKE-1: Per-AK Schreib-Isolation)
  ak_metadata = {
    ak_id: ak_id,
    title: ak_title,
    spec_anchor: { section: spec_anchor.title, ak_id: ak_id },
    rf_refs: extract_rf_refs(ak_body),
    k_score: k_score,
    srs_pro_ak: srs_pro_ak,
    k_aufwand: k_aufwand,
    k_kopplung: k_kopplung,
    k_fragilitaet: k_fragilitaet,
    model_refs: tc_anchors + w_refs,
    tc_anchor_status: tc_anchors.length > 0 ? "matched" : "unmatched",   # BL-269: umbenannt (war model_refs_status — Namens-Konflikt mit der K-SCORE.md W-Status-Map {W{n}:status}, die w_status_set speist; dieser IDF-Berater ist BL-209-deprecated, daher latent — aber Name befreit)
    w_offen_count: w_offen_count,
    layer_hint: layer_hint,
    dateien_hint: dateien_hint,
    unreife_typ: unreife_typ,
    dependencies: dependencies,
    last_berater: "akExtraktion"
  }
  # INV-AKE-1: Per-AK Pfad — nur akExtraktion[ak_id] schreiben, NICHT andere AKs
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.akExtraktion[ak_id] = ak_metadata)

SCHRITT 9: Exit
  exitcode = (k_score != null AND |tc_anchors| > 0) ? 0 : 2
  Logge: "[IDF_AK] EXIT duration={ms}ms k_score={k_score} unreife_typ={unreife_typ}"
  EXIT exitcode
```

## Cache-Faehigkeit (AK-IDF4a-03)

Hash-Schema fuer Idempotenz:

```
ak_hash = sha256(spec_section_content + tc_anchors_status_json + w_refs_status_json)
```

Bei Resync prueft der Berater zuerst:

```
manifest_hash = manifest.BERATER_OUTPUTS.akExtraktion[ak_id].hash
IF manifest_hash == ak_hash:
  SKIP: "AK-{ak_id} unveraendert (Hash-Match)"
  EXIT 0
```

## Begruendung Modell-Tier

sonnet — Per-AK fokussiert, klare Section-Reads, simple Aggregation. Parallel-faehig — opus waere Overkill.
