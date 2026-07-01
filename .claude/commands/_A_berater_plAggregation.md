---
status: active
version: 0.2.0
type: berater
parent: _A_orchestrate
phase: phase_5c
model_tier: middle
created: 2026-05-23
updated: 2026-05-24
feature_anchor: BL-197
optional: false
invariants:
  - "INV-PL-WRITER-1 (BL-201): Dieser Berater ist ERLAUBTER Writer a) fuer parking-lot.md (Forward-Generierung). Kein anderer unerlaubter Schreibzugriff erlaubt."
  - "INV-PL-1: Phase 5c ist erste und einzige A-Pipeline-Phase die parking-lot.md schreibt."
changelog_0_2_0: |
  v0.2.0 (2026-05-24): BL-201 AK-2 — INV-PL-WRITER-1 Single-Writer-Disziplin referenziert.
    - invariants-Block mit INV-PL-WRITER-1 hinzugefuegt.
    - Klarer: Erlaubter Writer a) (Forward-Generierung via A-Pipeline Phase 5c).
changelog_0_1_0: |
  v0.1.0 (2026-05-23): Initial — BL-197 A-Pipeline absorbiert Forward-PL-Generierung.
    - Kopiert und angepasst aus _IDF_berater_plAggregation.md (INV-NS-1: IDF unveraendert).
    - parent: _A_orchestrate statt _IDF_orchestrate.
    - Liest BERATER_OUTPUTS.akExtraktion aus A_PIPELINE_STATE-Namespace.
    - OQ-2: Speicherort identisch zu IDF (6_PL/{bl_id}-parking-lot.md).
    - Phase 5c (nach Phase 5b akExtraktion, INV-PL-1: erst hier schreiben).
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.akExtraktion[*]", purpose: "Per-AK pl_item_drafts aggregieren"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.bl_id / derived_name", purpose: "Vault-Pfad"}
    - {file: ".claude/config/vault-routing.json", path: "vaults.{detected_vault}.windows_path", purpose: "Pfad-Resolution"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/6_PL/", path: "Existenz + bestehende Items (Idempotenz)", purpose: "Merge wenn PL schon existiert"}
  writes:
    - {file: "{VAULT}/Backlog/{BL_SLUG}/6_PL/{BL_ID}-parking-lot.md", path: "PL-Items + Aggregat-Block (INV-PL-1)", purpose: "PL_Master aus AK-Extraktion"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.plAggregation", purpose: "Schema (s.u.)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser plAggregation)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.*"}
  calls: []
---

# _A_berater_plAggregation (Phase 5c in _A_orchestrate)

> **Zweck:** Aus Per-AK pl_item_drafts ein PL_Master (parking-lot.md) im Vault aggregieren. Sequenziell. INV-PL-1: erste und einzige Phase die parking-lot.md schreibt.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_plAggregation                                   |
+======================================================================+
|  LIEST:                                                              |
|    {WORKING_DIR}/_manifest.md (INV-VAULT-9 Path-Resolver)            |
|      BERATER_OUTPUTS.akExtraktion[*] (Per-AK pl_item_drafts)         |
|      A_PIPELINE_STATE.bl_id / derived_name                           |
|    .claude/config/vault-routing.json                                 |
|      vaults.{detected_vault}.windows_path                            |
|    {VAULT_BL_FOLDER}/6_PL/ (ALLE PL-Files, INV-PLA-4)               |
|                                                                      |
|  SCHREIBT:                                                           |
|    {VAULT_BL_FOLDER}/6_PL/{BL_ID}-parking-lot.md (INV-PL-1)         |
|      (Master-File, Aggregat + PL-Items aus AK-Extraktion)            |
|    {WORKING_DIR}/_manifest.md                                        |
|      BERATER_OUTPUTS.plAggregation = {                               |
|        items_total, items_new, items_existing,                       |
|        pl_master_path, aggregate_k_score,                            |
|        aggregate_unreife_typ, status                                 |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser plAggregation)                          |
|    A_PIPELINE_STATE.* (read-only hier)                               |
|                                                                      |
|  PFLICHT-LOGGING (INV-PLA-5):                                        |
|    [A_PLA] vault_root={path}                                         |
|    [A_PLA] bl_folder={path}                                          |
|    [A_PLA] reading: {file} ({n_lines} Zeilen)                        |
|    [A_PLA] master_file={path} (wo geschrieben wird)                  |
|    [A_PLA] items_total={N} (new={A}, existing={B})                   |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 5c (nach Phase 5b akExtraktion)         |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Aggregation aus pl_item_drafts in Vault-PL,         |
|    Markdown-Listen-Schreiben. Kein Reasoning.                       |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-PL-1: parking-lot.md existiert ERST nach Phase 5c            |
|    INV-PLA-1: Idempotent — bestehende Items mergen, nicht ueberschr.|
|    INV-PLA-2: Aggregate (k_score, unreife_typ) als Frontmatter      |
|    INV-PLA-3: Schreib-Isolation auf BERATER_OUTPUTS.plAggregation    |
|    INV-PLA-4: MUSS ALLE 6_PL/*.md Dateien lesen (Vollbild)          |
|    INV-PLA-5: Pfade explizit loggen (User-Sichtbarkeit)              |
|    INV-A-ORDER-6: Alle akExtraktion-Items DONE vor Phase 5c          |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - akExtraktion done fuer alle AKs                                 |
|    - BERATER_OUTPUTS.akExtraktion[*] vollstaendig                    |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - parking-lot.md existiert mit allen PL-Items                     |
|    - BERATER_OUTPUTS.plAggregation vollstaendig                      |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_A_berater_plAggregation, args="{NAME}")

Parameter:
  {NAME} - Feature-Name (aus A_PIPELINE_STATE.derived_name)

Ausgabe:
  - {VAULT_BL_FOLDER}/6_PL/{BL_ID}-parking-lot.md (erstellt oder gemergt)
  - BERATER_OUTPUTS.plAggregation
  - Exitcode: 0=OK, 2=FAIL

Logging-Format:
  [A_PLA] ENTRY name={NAME} aks={n}
  [A_PLA] EXIT duration={ms}ms items_total={n} new={k}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  plAggregation:
    items_total: 10
    items_new: 10
    items_existing: 0
    pl_master_path: "C:/Users/Administrator/Documents/OmniCommand/Backlog/{BL_SLUG}/6_PL/{BL_ID}-parking-lot.md"
    aggregate_k_score: 62
    aggregate_unreife_typ: "ok"
    status: DONE
    last_berater: "plAggregation"
```

## Logik (v0.1.0)

```
SCHRITT 0: Entry-Log + Vorbedingung (INV-A-ORDER-6)
  Logge: "[A_PLA] ENTRY name={NAME}"
  manifest = Read({WORKING_DIR}/_manifest.md)
  ak_outputs = manifest.BERATER_OUTPUTS.akExtraktion
  IF ak_outputs == null OR |ak_outputs| == 0:
    Logge: "[A_PLA] FAIL — akExtraktion fehlt (INV-A-ORDER-6)"
    EXIT 2

  bl_id       = manifest.A_PIPELINE_STATE.bl_id
  bl_slug     = manifest.A_PIPELINE_STATE.derived_name
  aks_total   = |ak_outputs|
  Logge: "[A_PLA] aks={aks_total} bl_id={bl_id}"

SCHRITT 1: Vault-Pfad auflösen (INV-PLA-5 Logging)
  vault_routing = Read(".claude/config/vault-routing.json")
  vault_root    = vault_routing.vaults.{detected_vault}.windows_path
  bl_folder     = "{vault_root}/Backlog/{bl_slug}"
  pl_dir        = "{bl_folder}/6_PL"

  Logge: "[A_PLA] vault_root={vault_root}"
  Logge: "[A_PLA] bl_folder={bl_folder}"

  # 6_PL Ordner erstellen falls nicht vorhanden
  IF NOT exists(pl_dir):
    bash("mkdir -p {pl_dir}")

  # INV-PLA-4: ALLE PL-Files lesen
  pl_files_existing = Glob("{pl_dir}/*.md")
  Logge: "[A_PLA] pl_files_found={|pl_files_existing|}"
  FOR f in pl_files_existing:
    lines = count_lines(Read(f))
    Logge: "[A_PLA] reading: {f} ({lines} Zeilen)"

  pl_path = "{pl_dir}/{bl_id}-parking-lot.md"
  Logge: "[A_PLA] master_file={pl_path}"

SCHRITT 2: Bestehende Items lesen (INV-PLA-1 Idempotenz)
  existing_items = []
  IF exists(pl_path):
    pl_content = Read(pl_path)
    existing_items = parse_pl_items(pl_content)  # by id
  Logge: "[A_PLA] existing_items={|existing_items|}"

SCHRITT 3: pl_item_drafts aus akExtraktion sammeln
  pl_items_neu = []
  FOR ak_id, ak_output IN ak_outputs:
    IF ak_output.pl_item_draft != null:
      draft = ak_output.pl_item_draft
      # Schema-Pruefung (PL-12-04, BL-165 AK-12)
      FOR field IN [srs, k_score]:
        IF draft[field] IN ["LOW", "MED", "MEDIUM", "HIGH"]:
          Logge: "[A_PLA] SCHEMA-FAIL item={draft.id} field={field} val={draft[field]} — kategorisch verboten"
          FAIL: "PL-Item {draft.id}: {field} muss int 0..100, nicht kategorisch"
      IF draft.source_aks == null OR |draft.source_aks| == 0:
        Logge: "[A_PLA] SCHEMA-FAIL item={draft.id} field=source_aks — leer"
      pl_items_neu.append(draft)

SCHRITT 4: Idempotenz-Merge mit existing_items (INV-PLA-1)
  merged_items = []
  items_new = 0
  items_existing = 0
  FOR new_item in pl_items_neu:
    existing = existing_items.find(e => e.id == new_item.id)
    IF existing:
      # Merge: behalte status / user-edits, ueberschreibe Aggregate
      merged = {
        ...existing,
        source_aks:  new_item.source_aks,
        k_score:     new_item.k_score,
        srs:         new_item.srs,
        layer_hint:  new_item.layer_hint,
        unreife_typ: new_item.unreife_typ,
        dependencies: new_item.dependencies,
        regenerated_at: ISO_DATE_TODAY()
      }
      merged_items.append(merged)
      items_existing += 1
    ELSE:
      merged_items.append(new_item)
      items_new += 1

SCHRITT 5: Aggregate berechnen (INV-PLA-2)
  k_scores = [i.k_score FOR i in merged_items IF i.k_score != null]
  aggregate_k_score = |k_scores| > 0 ? mean(k_scores) : null
  aggregate_unreife_typ = aggregate_unreife([i.unreife_typ FOR i in merged_items])
  # aggregate_unreife Hierarchie: model_unreif > EXTERN > forward_verify > INTERN > ok  (BL-369)

SCHRITT 6: parking-lot.md schreiben (INV-PL-1: erste Phase die schreibt)
  pl_frontmatter = render_yaml({
    bl_id:                bl_id,
    generated_at:         ISO_DATE_TODAY(),
    generated_by:         "_A_berater_plAggregation v0.1.0",
    source_phase:         "A-Pipeline Phase 5c",
    items_total:          |merged_items|,
    aggregate_k_score:    aggregate_k_score,
    aggregate_unreife_typ: aggregate_unreife_typ
  })

  pl_body = "# PL Master — {bl_id}\n\n"
  pl_body += "Generiert von A-Pipeline Phase 5c (_A_berater_plAggregation).\n\n"
  pl_body += "## Items\n\n"
  FOR item in merged_items:
    pl_body += render_pl_item_markdown(item)

  Write(pl_path, "---\n{pl_frontmatter}\n---\n\n" + pl_body)
  Logge: "[A_PLA] items_total={|merged_items|} (new={items_new}, existing={items_existing})"

SCHRITT 7: BERATER_OUTPUTS.plAggregation schreiben (INV-PLA-3)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.plAggregation = {
    items_total:           |merged_items|,
    items_new:             items_new,
    items_existing:        items_existing,
    pl_master_path:        pl_path,
    aggregate_k_score:     aggregate_k_score,
    aggregate_unreife_typ: aggregate_unreife_typ,
    status:                "DONE",
    last_berater:          "plAggregation"
  })

SCHRITT 8: Exit
  exitcode = |merged_items| > 0 ? 0 : 2
  Logge: "[A_PLA] EXIT items_total={|merged_items|} new={items_new}"
  EXIT exitcode
```

## aggregate_unreife-Funktion

Hierarchie: `model_unreif > EXTERN > forward_verify > INTERN > ok`. Wenn auch nur ein Item
`model_unreif` ist, ist der Aggregat `model_unreif`. Wenn keiner unreif aber
mind. einer EXTERN, dann EXTERN. Etc. (BL-369: `forward_verify` = dormant Forward-Verify-
Companion rangiert UNTER EXTERN -> triggert NICHT das EXTERN-/_orakel-Web-Routing; nur ein
echtes EXTERN-AK [drittsystem/api/consumer/downstream] macht den Aggregat EXTERN.)

## render_pl_item_markdown-Funktion

Emittiert AUSSCHLIESSLICH das kanonische Format (AK-3, BL-435).
Schema-Guard: Ergebnis ist `is_canonical_pl_item`-kompatibel (pl_item_marker.py AK-5).

```
render_pl_item_markdown(item) -> str:
  """
  Erzeugt genau eine kanonische PL-Item-Zeile.

  Kanonisches Format (ADE-4, CANONICAL_PATTERN aus pl_item_marker.py):
    - [ ] **{bl}-AK-{n}-PL-1** (status: open) — {title}

  Checkbox '[ ]' = menschliche Aufgabe (Mensch markiert done via Skill).
  Feld '(status: open)' = Maschinen-Signal fuer pl_item_is_done / mark_pl_done.

  INVARIANTE: KEINE Alt-Formate. KEIN [STATUS: IN_ARBEIT]-Tag.
              KEIN Tabellen-Format. KEINE PL-N Kurzform.
  ID-Schema: {bl}-AK-{n}-PL-1 (NICHT Kurzform PL-N).
  """
  item_id = item.id     # z.B. "BL-435-AK-3-PL-1"
  title   = item.title  # z.B. "render_pl_item_markdown kanonisches Format"

  # Defensiv: leere id oder title -> kein Crash, aber leere Zeile
  IF NOT item_id OR NOT title:
    Logge: "[A_PLA] WARN: item.id oder item.title leer — PL-Item uebersprungen"
    RETURN ""

  line = f"- [ ] **{item_id}** (status: open) — {title}\n"

  # VERTRAG (AK-F2, BL-447): Emittierte Zeile MUSS kanonisch sein — fail-loud bei Abweichung.
  from pl_item_marker import is_canonical_pl_item
  assert is_canonical_pl_item(line.rstrip()), f"BUG: render_pl_item_markdown Format-Verletzung: {line!r}"

  RETURN line
```

## INV-PL-1 Wichtig

Diese Phase ist die EINZIGE in der A-Pipeline, die {BL_ID}-parking-lot.md schreibt.
Keine andere Phase (specParse, akExtraktion, gap, kscore) darf parking-lot.md anfassen.
Verletzung von INV-PL-1 ist ein Kritischer-Fehler.

## Begruendung Modell-Tier

sonnet — Aggregation aus pl_item_drafts, Markdown-Listen-Schreiben, Idempotenz-Merge. Sequenziell — kein opus-Bedarf.
