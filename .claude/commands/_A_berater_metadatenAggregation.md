---
status: active
version: 0.3.0
type: berater
parent: _A_orchestrate
phase: phase_4.2a
model_tier: middle
created: 2026-04-25
updated: 2026-06-12
feature_anchor: BL-142
bl_312_ak_4: "Reifegrad-Routing-Refit Option-a: gap+modellreife, KEIN k/srs"
optional: false
renamed_from: _A_berater_complexityState
changelog_0_2_0: |
  v0.2.0 (2026-05-06): Skelett -> produktiv.
    - Vault-First: liest aus {bl_folder}/4_K-Score/, /5_Gap/, /2_Model/, /3_Spec/.
    - 6 Aggregat-Felder berechnet (k_score, gap, reifegrad, sections, aks, rfs).
    - Reifegrad-Inferenz aus Model-Frontmatter + Gap-Schwelle.
    - INV-MA-4 NEU: backlog_spawn_required-Flag (Orchestrator triggert /_backlog).
changelog_0_3_0: |
  v0.3.0 (2026-06-12, BL-312 AK-4 SB-routing, Option-a node+user-voiced):
    - Reifegrad-Routing REFIT: stuetzt sich jetzt AUSSCHLIESSLICH auf gap + modellreife.
      KEIN k, KEIN srs im Reifegrad-/Routing-Pfad mehr (waren vorher k_score+gap).
    - Begruendung: K/SRS-Erstbewertung wandert nach IDF (BL-312 AK-1, SB-srseval FERTIG)
      und steht am A-Ende NICHT mehr zur Verfuegung. User-Voice 2026-06-10 (2.Voice):
      "K-Score, SRS ... eigentlich Gap brauchen wir dazu nicht" => K/SRS vom Grob-Routing entkoppelt.
    - modellreife (W-Status-Quote %) wird in SCHRITT 4 ermittelt und ist 2. Routing-Treiber.
    - reifegrad_reason dokumentiert gap+modellreife-Ableitung (nachvollziehbar).
    - aggregat_k_score bleibt Metadaten-Feld (NICHT Routing-Treiber); _K_score-Engine unberuehrt.
    - INV-MA-5 NEU: Reifegrad ausschliesslich aus gap+modellreife (kein k/srs).
contract:
  reads:
    - {file: "{VAULT}/Backlog/{BL_SLUG}/4_K-Score/{NAME}-K-SCORE.md", path: "Top-Section + Aggregat", purpose: "K-Score Vault-First (BL-151)"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/5_Gap/{NAME}-GAP.md", path: "Gap-Total + Klassen", purpose: "Gap Vault-First"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md", path: "Frontmatter + Section-Count", purpose: "Model Vault-First"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md", path: "AK-Liste + RF-Liste", purpose: "Spec Vault-First"}
    - {file: ".claude/analysis/K-SCORE.md", path: "Lokal-Fallback", purpose: "Legacy"}
    - {file: ".claude/analysis/Gap.md", path: "Lokal-Fallback", purpose: "Legacy"}
    - {file: ".claude/models/{NAME}_Model.md", path: "Lokal-Fallback", purpose: "Legacy"}
    - {file: ".claude/specs/{NAME}_Spec.md", path: "Lokal-Fallback", purpose: "Legacy"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE", purpose: "Resync-Vorabwerte"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.aggregat_k_score", purpose: "Aggregat 1/6"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.aggregat_gap", purpose: "Aggregat 2/6"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.aggregat_reifegrad", purpose: "Aggregat 3/6 — BL-312 AK-4: aus gap+modellreife (KEIN k/srs)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.aggregat_sections_count", purpose: "Aggregat 4/6"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.aggregat_aks_count", purpose: "Aggregat 5/6"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.aggregat_rfs_count", purpose: "Aggregat 6/6"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.backlog_spawn_required", purpose: "Flag fuer Orchestrator"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.metadatenAggregation", purpose: "Schema (s.u.)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser metadatenAggregation)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.routing_target"}
    - {file: "Backlog-Items", path: "Aufruf von /_backlog ist Orchestrator-Aufgabe (W7-Compliance)"}
  calls: []
---

# _A_berater_metadatenAggregation (Phase 4.2a in _A_orchestrate)

> **Zweck:** Aggregierte Metadaten (6 Felder) aus K-Score, Gap, Model, Spec sammeln — Routing-Vorbereitung. Umbenannt aus complexityState.
>
> **BL-312 AK-4 (v0.3.0):** Die Reifegrad-Ableitung (GROB-Triage fuers A-Ende-Routing) stuetzt sich AUSSCHLIESSLICH auf **gap + modellreife** — KEIN k, KEIN srs. K/SRS-Erstbewertung wandert nach IDF (NACH dem Routing); `aggregat_k_score` bleibt nur Metadaten-Feld.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_metadatenAggregation                            |
+======================================================================+
|  LIEST:                                                              |
|    .claude/analysis/K-SCORE.md (Top + Aggregat)                      |
|    .claude/analysis/Gap.md (Gap-Total + Klassen)                     |
|    .claude/models/{NAME}_Model.md (Frontmatter + Section-Count)      |
|    .claude/specs/{NAME}_Spec.md (AK + RF Listen)                     |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      A_PIPELINE_STATE (Resync-Vorabwerte)                            |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      A_PIPELINE_STATE.aggregat_k_score                               |
|      A_PIPELINE_STATE.aggregat_gap                                   |
|      A_PIPELINE_STATE.aggregat_reifegrad                             |
|      A_PIPELINE_STATE.aggregat_sections_count                        |
|      A_PIPELINE_STATE.aggregat_aks_count                             |
|      A_PIPELINE_STATE.aggregat_rfs_count                             |
|      BERATER_OUTPUTS.metadatenAggregation = {                        |
|        ... 6 Aggregate + summary                                     |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser metadatenAggregation)                   |
|    A_PIPELINE_STATE.routing_target / modus / derived_name            |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 4.2a (vor stateMaintain)                |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Multi-File-Aggregation, Zaehlung + simple Klass.,   |
|    kein Volltext-Reasoning.                                         |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-MA-1: Alle 6 Aggregate gesetzt oder explizit null            |
|    INV-MA-2: aggregat_reifegrad IN {UNREIF, SC-REIF, REIF, null}    |
|    INV-MA-3: Schreib-Isolation auf BERATER_OUTPUTS.metadaten*       |
|    INV-MA-5 (BL-312 AK-4): aggregat_reifegrad wird AUSSCHLIESSLICH   |
|      aus gap + modellreife abgeleitet. KEIN k, KEIN srs im           |
|      Reifegrad-/Routing-Pfad (K/SRS-Erstbewertung wandert nach IDF). |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - K-Score, Gap, Model, Spec existieren (oder explizit null)       |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - 6 Aggregat-Felder in A_PIPELINE_STATE gesetzt                   |
|    - BERATER_OUTPUTS.metadatenAggregation vollstaendig               |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_A_berater_metadatenAggregation, args="{NAME}")

Parameter:
  {NAME} - Feature-Name

Ausgabe:
  - 6 A_PIPELINE_STATE.aggregat_*-Felder
  - BERATER_OUTPUTS.metadatenAggregation
  - Exitcode: 0=OK, 1=PARTIAL (manche Quellen fehlen), 2=FAIL

Logging-Format:
  [A_AGG] ENTRY name={NAME}
  [A_AGG] EXIT gap={n} modellreife={n} reifegrad={x} reason='{...}'
```

## Output-Schema

```yaml
A_PIPELINE_STATE:
  aggregat_k_score: 42        # Metadaten-Feld — NICHT Routing-Treiber (BL-312 AK-4)
  aggregat_gap: 18            # Routing-Treiber (Spec-vs-IST)
  aggregat_reifegrad: "SC-REIF"
  aggregat_sections_count: 7
  aggregat_aks_count: 12
  aggregat_rfs_count: 5

BERATER_OUTPUTS:
  metadatenAggregation:
    aggregat_k_score: 42      # Metadaten-Feld — NICHT Routing-Treiber (BL-312 AK-4)
    aggregat_gap: 18          # Routing-Treiber 1/2 (gap)
    modellreife: 60           # Routing-Treiber 2/2 (W-Status-Quote %)
    aggregat_reifegrad: "SC-REIF"
    reifegrad_reason: "gap=18% + modellreife=60% -> SC-REIF"   # gap+modellreife, KEIN k/srs
    aggregat_sections_count: 7
    aggregat_aks_count: 12
    aggregat_rfs_count: 5
    summary: "SC-REIF (gap=18%, modellreife=60%), AKs=12"
    last_berater: "metadatenAggregation"
```

## Logik (v0.2.0 produktiv)

```
SCHRITT 0: Entry + Pfad-Resolution
  NAME = args[0]
  Logge: "[A_AGG] ENTRY name={NAME}"
  bl_folder = subprocess(".claude/scripts/resolve_bl_path.py", BL_ID).stdout.strip()

  # Vault-First Pfade mit Lokal-Fallback
  k_score_path = "{bl_folder}/4_K-Score/{NAME}-K-SCORE.md"
  IF NOT exists(k_score_path):
    k_score_path = ".claude/analysis/K-SCORE.md"

  gap_path = "{bl_folder}/5_Gap/{NAME}-GAP.md"
  IF NOT exists(gap_path):
    gap_path = ".claude/analysis/Gap.md"

  model_path = "{bl_folder}/2_Model/{NAME}_Model.md"
  IF NOT exists(model_path):
    model_path = ".claude/models/{NAME}_Model.md"

  spec_path = "{bl_folder}/3_Spec/{NAME}_Spec.md"
  IF NOT exists(spec_path):
    spec_path = ".claude/specs/{NAME}_Spec.md"

SCHRITT 1: Sequentielle Reads (W7-konform, kein Sub-Agent-Spawn)
  k_score_data       = exists(k_score_path) ? Read(k_score_path) : null
  gap_data           = exists(gap_path)     ? Read(gap_path)     : null
  model_data         = exists(model_path)   ? Read(model_path)   : null
  spec_data          = exists(spec_path)    ? Read(spec_path)    : null

  partial_sources = sum([1 for x in [k_score_data, gap_data, model_data, spec_data] if x is null])

SCHRITT 2: K-Score-Aggregat (Top-Section parsen)
  IF k_score_data:
    aggregat_k_score = parse_field_int(k_score_data, "K-Score:") ??
                       parse_field_int(k_score_data, "Total:") ??
                       null
  ELSE:
    aggregat_k_score = null

SCHRITT 3: Gap-Aggregat (Prozent parsen)
  IF gap_data:
    aggregat_gap = parse_field_int(gap_data, "GAP:") ??
                   parse_field_int(gap_data, "Total Gap:") ??
                   null
  ELSE:
    aggregat_gap = null

SCHRITT 4: Model-Aggregat (Sections + Modellreife = W-Status-Quote)
  # modellreife (BL-312 AK-4): W-Status-Quote = Anteil der bestaetigten/verifizierten
  # W-Knoten im Model. Traegt zusammen mit gap das GROB-Routing (SCHRITT 6). KEIN k, KEIN srs.
  IF model_data:
    model_fm = parse_frontmatter(model_data)
    aggregat_sections_count = count_h2_sections(model_data)

    # W-Status-Quote: confirmed/verified W-Knoten / alle W-Knoten (0..100 %).
    # Quelle 1: explizites Frontmatter-Feld (maturity_pct / w_status_quote), falls vorhanden.
    # Quelle 2: ableiten aus W-Knoten-Status im Model-Body (confirmed|verified vs offen|hypothese|draft).
    w_total     = count_pattern(model_data, r"^### W\d+")
    w_confirmed = count_pattern(model_data, r"^### W\d+.*(confirmed|verified|bestaetigt)")
    IF model_fm.maturity_pct != null OR model_fm.w_status_quote != null:
      modellreife = parse_int(model_fm.maturity_pct ?? model_fm.w_status_quote)   # 0..100
    ELIF w_total > 0:
      modellreife = round(100 * w_confirmed / w_total)                            # abgeleitete W-Quote
    ELSE:
      modellreife = null   # kein Model-Reife-Signal ermittelbar
  ELSE:
    aggregat_sections_count = null
    modellreife = null

SCHRITT 5: Spec-Aggregat (AKs + RFs zaehlen)
  IF spec_data:
    aggregat_aks_count = count_pattern(spec_data, r"^AK-\d+:")
    aggregat_rfs_count = count_pattern(spec_data, r"^RF-\d+:")
  ELSE:
    aggregat_aks_count = null
    aggregat_rfs_count = null

SCHRITT 6: Reifegrad-Inferenz (INV-MA-2, INV-MA-5 — GROB-TRIAGE aus gap + modellreife)
  # BL-312 AK-4 (Option-a, node+user-voiced 2026-06-10 2.Voice):
  #   "K-Score, SRS — diese zwei Schritte ... eigentlich Gap brauchen wir dazu nicht"
  #   => K und SRS sind vom GROB-Routing ENTKOPPELT. Die K/SRS-Erstbewertung
  #      passiert jetzt in IDF (NACH dem Routing, BL-312 AK-1, SB-srseval FERTIG)
  #      und steht am A-Ende NICHT mehr zur Verfuegung. Das Routing DARF daher
  #      nicht mehr auf k/srs bauen.
  #   => Reifegrad-Routing stuetzt sich AUSSCHLIESSLICH auf:
  #        gap         (Spec-vs-IST-Delta, A-Artefakt, kleiner=reifer)
  #        modellreife (W-Status-Quote in %, A-Artefakt, hoeher=reifer)
  #   aggregat_k_score wird WEITERHIN als Metadaten-Feld gefuehrt (SCHRITT 2),
  #   geht aber NICHT in die Reifegrad-Ableitung ein. KEIN k-Lookup im Routing-Pfad.
  #
  # Konservative, nachvollziehbare Schwellen (GROB-Triage, kein Feintuning):
  #   gap = 0% UND modellreife hoch (>= 70)            -> REIF
  #   gap gross (>= 50%) ODER modellreife niedrig (<40)-> UNREIF
  #   alles dazwischen                                  -> SC-REIF
  IF aggregat_gap != null AND modellreife != null:
    IF aggregat_gap == 0 AND modellreife >= 70:
      aggregat_reifegrad = "REIF"
    ELIF aggregat_gap >= 50 OR modellreife < 40:
      aggregat_reifegrad = "UNREIF"
    ELSE:
      aggregat_reifegrad = "SC-REIF"
    reifegrad_reason = "gap={aggregat_gap}% + modellreife={modellreife}% -> {aggregat_reifegrad}"
  ELIF aggregat_gap != null:
    # Nur gap verfuegbar (kein Model-Reife-Signal): konservativ aus gap allein triagieren.
    IF aggregat_gap == 0:
      aggregat_reifegrad = "REIF"
    ELIF aggregat_gap >= 50:
      aggregat_reifegrad = "UNREIF"
    ELSE:
      aggregat_reifegrad = "SC-REIF"
    reifegrad_reason = "gap={aggregat_gap}% (modellreife n/a) -> {aggregat_reifegrad}"
  ELSE:
    aggregat_reifegrad = "UNREIF"   # Default bei fehlendem gap-Signal
    reifegrad_reason = "gap n/a -> UNREIF (Default, konservativ)"
  # HINWEIS: K/SRS-Erstbewertung erfolgt erst in IDF (nach diesem Grob-Routing).
  #          Dieses A-Ende-Routing ist GROB-Triage aus gap+modellreife (kein k, kein srs).

SCHRITT 7: Output schreiben (Atomarer Edit-Block, INV-MA-1, INV-MA-3)
  manifest_updates = {
    "A_PIPELINE_STATE.aggregat_k_score":        aggregat_k_score,
    "A_PIPELINE_STATE.aggregat_gap":            aggregat_gap,
    "A_PIPELINE_STATE.aggregat_reifegrad":      aggregat_reifegrad,
    "A_PIPELINE_STATE.aggregat_sections_count": aggregat_sections_count,
    "A_PIPELINE_STATE.aggregat_aks_count":      aggregat_aks_count,
    "A_PIPELINE_STATE.aggregat_rfs_count":      aggregat_rfs_count,
    "A_PIPELINE_STATE.backlog_spawn_required":  true   # INV-MA-4: Orchestrator-Trigger
  }
  Edit({WORKING_DIR}/_manifest.md, manifest_updates)

  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.metadatenAggregation = {
    aggregat_k_score:        aggregat_k_score,
    aggregat_gap:            aggregat_gap,
    modellreife:             modellreife,           # BL-312 AK-4: W-Status-Quote (%), Routing-Treiber
    aggregat_reifegrad:      aggregat_reifegrad,
    reifegrad_reason:        reifegrad_reason,      # BL-312 AK-4: gap+modellreife-Ableitung (KEIN k/srs)
    aggregat_sections_count: aggregat_sections_count,
    aggregat_aks_count:      aggregat_aks_count,
    aggregat_rfs_count:      aggregat_rfs_count,
    summary: "{aggregat_reifegrad} (gap={aggregat_gap}%, modellreife={modellreife}%), AKs={aggregat_aks_count}",
    last_berater: "metadatenAggregation",
    sources_resolved: 4 - partial_sources
  })

SCHRITT 8: Exit
  status = "OK" if partial_sources == 0 else "PARTIAL"
  Logge: "[A_AGG] EXIT gap={aggregat_gap} modellreife={modellreife} reifegrad={aggregat_reifegrad} reason='{reifegrad_reason}'"
  EXIT (status == "OK") ? 0 : 1
```

## INV-MA-4 (NEU v0.2.0): backlog_spawn-Trigger
Berater spawnt NICHT `/_backlog` selbst (W7-Compliance). Stattdessen setzt
er `A_PIPELINE_STATE.backlog_spawn_required = true`. Der Orchestrator
(`_A_orchestrate` Phase 4.2a) liest dieses Flag und ruft danach
`Skill(_backlog)` mit den Aggregat-Werten als Args auf.

## format_version-Stamping-Disziplin (BL-333, B3 — Model/Metadaten-Stamp via Skill-Pfad)

> **Spiegel der Lane-A-Stamp-Logik** (`.claude/scripts/resolve_format_version.py`). Es gibt KEINEN Python-Model-Writer — der Model-Stamp ist ein **Skill-Pfad** (Prosa-Konvention). Loader-Wert = Single-Source.

Das Model (`_model.md`) ist ein versioniertes Langzeit-Artefakt (Typ `model` in der Registry `.claude/config/format_versions.yaml`). Wenn dieser Berater Metadaten/Model-Aggregate in ein Model-/Metadaten-Frontmatter persistiert, gilt:

- **Top-Level-Stamp (additiv, idempotent):** `format_version: {N}` im Model/Metadaten-Frontmatter; `{N}` kommt AUSSCHLIESSLICH via `resolve_format_version("model")` (Loader = Single-Source der Versions-Wahrheit, kein hardcoded Literal); vorhanden -> kein Duplikat.
- **Dual-Read-Gen-0:** Model ohne Stempel == Generation-0 (NIE Crash); Loader `None` -> Stamp weglassen statt brechen (Symmetrie zu G2e).
- **Rein additiv:** keine Bestands-Frontmatter-Felder umbenennen/re-formatieren.

Vertrags-Spiegel von `stamp_format_version_lines` / `read_format_version` in `resolve_format_version.py`. Lead der Manifest-Variante: `_A_berater_stateMaintain.md` (B1).

## Begruendung Modell-Tier

sonnet — Aggregation + Zaehlung + simple Klassifikation. Kein Reasoning-Bedarf.
