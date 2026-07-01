---
status: active
version: 0.3.0
type: berater
parent: _A_orchestrate
phase: phase_0.5
model_tier: ceiling
created: 2026-04-25
updated: 2026-06-14
feature_anchor: BL-142
optional: false
changelog_0_3_0: |
  v0.3.0 (2026-06-14, BL-346): pileOfMud-Relevanz-Gate im all-mode ELSE-Zweig.
    - Kein per-BL Snapshot -> Live-Pile via pile_relevance.partition_pile_by_relevance
      gefiltert (ohne Snapshot 0 relevant) statt blindem .claude/pileOfMud/*-Glob.
    - Verhindert stillen Garbage-Extract bei mature consolidated EPICs (Live-Fall BL-282:
      5 fremde Files anderer Sessions waeren als BL-282-Findings mis-extrahiert worden).
    - "No silent caps": Fremd-Material wird LAUT geloggt, NICHT extrahiert.
    - Snapshot-Pfad (fresh-intake) UNVERAENDERT — Abwaertskompatibel.
changelog_0_2_0: |
  v0.2.0 (2026-05-06): Skelett -> produktiv.
    - Single-Worker-Logik (W7-konform). Wellen-Spawn ist Orchestrator-Aufgabe.
    - Vault-First Pfade: schreibt nach {bl_folder}/Crumbs/, nicht .claude/analysis/.
    - Findings-Klassifikation (observation|hypothesis|burden) durch Pattern-Match.
    - INV-FX-4 NEU: W7-Compliance (kein Sub-Agent-Spawn).
contract:
  reads:
    - {file: ".claude/pileOfMud/", path: "Volltext aller *.md/*.txt", purpose: "Findings-Extraktion"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/1_Task/Task.md", path: "Volltext (Vault-First)", purpose: "Aufgaben-Kontext erweitern"}
    - {file: ".claude/Task.md", path: "Volltext FALLBACK", purpose: "Legacy-Lokal"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.derived_name", purpose: "Feature-Anker"}
  writes:
    - {file: "{VAULT}/Backlog/{BL_SLUG}/Crumbs/{NAME}_findings_crumbs.md", path: "Volltext (status=draft)", purpose: "Krumen-Liste im Vault (BL-151)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.findingsExtraction", purpose: "Aggregat-Schema (s.u.)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser findingsExtraction)"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/Crumbs/{NAME}_findings_crumbs.md", path: "(status=confirmed bleibt findingsReview vorbehalten)"}
  calls: []
---

# _A_berater_findingsExtraction (Phase 0.5 in _A_orchestrate)

> **Zweck:** Extraktion von Krumen (Findings) aus pileOfMud + Task — als Vorbereitung fuer findingsReview.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_findingsExtraction                              |
+======================================================================+
|  LIEST:                                                              |
|    {pileOfMud} (Volltext)                                            |
|    {taskMd} (falls vorhanden, Volltext)                              |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      A_PIPELINE_STATE.derived_name (Feature-Anker)                   |
|                                                                      |
|  SCHREIBT:                                                           |
|    .claude/analysis/findings_crumbs.md                               |
|      Frontmatter status=draft                                        |
|      Liste von Krumen (Beobachtung | Hypothese | Last)               |
|    {WORKING_DIR}/_manifest.md                                                      |
|      BERATER_OUTPUTS.findingsExtraction = {                          |
|        crumbs_total, drones_used, synthesis_pass                     |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser findingsExtraction)                     |
|    findings_crumbs.md mit status=confirmed (das ist findingsReview)  |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 0.5 (Wellen 3 Drohnen + 1 Synth Opus)   |
|                                                                      |
|  MODELL-TIER: opus                                                   |
|    Begruendung: Volltext-Synthese ueber pileOfMud + Task,           |
|    erkennt latente Hypothesen und Lasten — Deep-Reasoning noetig.   |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-FX-1: status=draft als einzig erlaubter Schreibwert           |
|    INV-FX-2: Krumen tragen Typ-Tag (observation|hypothesis|burden)   |
|    INV-FX-3: Schreib-Isolation auf BERATER_OUTPUTS.findingsExtraction|
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - pileOfMud existiert und ist lesbar                              |
|    - A_PIPELINE_STATE.derived_name gesetzt (Phase 0.2 done o. fix)   |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - findings_crumbs.md existiert mit status=draft                   |
|    - BERATER_OUTPUTS.findingsExtraction vollstaendig                 |
+======================================================================+
```

## SOURCE-PROVENANCE-PROPAGATION (BL-160 AK-5)

**INV-PROV-PROP-1:** Jeder Output-Datei MUSS source_provenance + provenance_chain Frontmatter-Block enthalten.

**Pattern:**
1. Lies Vorgaenger-Output (pileOfMud, taskMd). Extrahiere predecessor.source_provenance + predecessor.provenance_chain.
2. Bei Output-Schreibung (findings_crumbs.md):
   - source_provenance: kopiere von predecessor (gleiche Source-URL/PageId)
   - provenance_chain: haenge neuen Layer-Eintrag an (layer=2, artifact=findings_crumbs_pfad, role="finding", timestamp=ISO, derived_from=[predecessor_pfad])
3. Bei mehreren Predecessors: provenance_chain.derived_from sammelt alle Vorgaenger.
4. Wenn predecessor.source_provenance FEHLT (legacy): setze source_provenance={source: "legacy_pre_BL-160", source_kind: "legacy", fetched_at: ISO_NOW}.

**Helper:** Verwende `.claude/scripts/propagate_provenance.py update <output_path>` nach Output-Schreibung — autoupdate predecessor.used_in (Hebb-bidir).

**role-Mapping fuer diesen Skill:** `"finding"`

---

## Aufruf-Interface

```
Skill(_A_berater_findingsExtraction, args="{NAME} [{DIFFICULTY}] [{CEILING}] [--file={PATH}] [--mode=consolidate]")

Parameter:
  {NAME}        - Feature-Name (derived oder explizit)
  {DIFFICULTY}  - easy|normal|hard (optional, default: aus _session_params)
  {CEILING}     - opus|sonnet|haiku (optional, default: aus _session_params)
  --file={PATH} - F38-Fix 2026-05-08: NUR diese pileOfMud-Datei verarbeiten (file-iteration via Orchestrator).
                  Crumbs-Output ist file-spezifisch: {derived_name}_{file_basename}_findings_crumbs.md
  --mode=consolidate - Final-Pass: alle file-spezifischen Crumbs zu Master-Crumbs konsolidieren.
                  Output: {derived_name}_findings_crumbs_master.md

Ausgabe:
  - findings_crumbs.md (intermediate, status=draft) — file-spezifisch wenn --file gesetzt
  - findings_crumbs_master.md (status=draft) — bei --mode=consolidate
  - BERATER_OUTPUTS.findingsExtraction (akkumuliert ueber Spawns)
  - Exitcode: 0=OK, 1=PARTIAL (wenig Krumen), 2=FAIL

Logging-Format:
  [A_FX_EXTRACT] ENTRY pile={path} task={path|null} file={file|all} mode={extract|consolidate}
  [A_FX_EXTRACT] EXIT duration={ms}ms crumbs={n} status={OK|PARTIAL|FAIL}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  findingsExtraction:
    crumbs_total: 17
    drones_used: 3
    synthesis_pass: true
    last_berater: "findingsExtraction"
```

## Logik (v0.2.0 produktiv, W7-konform Single-Worker)

> **W7-Note:** Dieser Berater laeuft als Single-Worker mit sequentiellen Reads.
> Echte Wellen-Parallelisierung ist Orchestrator-Aufgabe (mehrere Worker-Spawns
> mit chunk-spezifischen Args), NICHT Berater-Logik. Siehe BL-W1-A3.

```
SCHRITT 0: Entry + Pfad-Resolution
  NAME = args[0]
  Logge: "[A_FX_EXTRACT] ENTRY name={NAME}"
  bl_folder = subprocess(".claude/scripts/resolve_bl_path.py", BL_ID).stdout.strip()
  derived_name = Read({WORKING_DIR}/_manifest.md).A_PIPELINE_STATE.derived_name ?? NAME

SCHRITT 1: pileOfMud-Material laden (--file Mode | --mode=consolidate | all)
  # F38-Fix 2026-05-08: Drei Modi
  IF args.has("--mode") AND args["--mode"] == "consolidate":
    # Konsolidierungs-Mode: keine Roh-Extraktion, sondern Master-Bau aus existierenden file-Crumbs
    Logge: "[A_FX_EXTRACT] consolidate-mode: lese file-spezifische Crumbs"
    GOTO SCHRITT 7 (consolidate)
  ELIF args.has("--file"):
    pile_files = [args["--file"]]
    Logge: "[A_FX_EXTRACT] file-mode: {pile_files[0]}"
  ELSE:
    # ## AK-2 Snapshot-Check BEGIN (BL-160, PL-AK2-4, PT-CMD-023 + PT-CMD-006)
    # 2026-06-01: extrahierbar = Text + Bilder + PDF (Read liest alle — Bild/PDF visuell).
    EXTRACT_GLOB = "*.{md,txt,png,jpg,jpeg,gif,webp,bmp,pdf}"
    snapshot_dir = "{bl_folder}/Sources/_pileOfMud_snapshot"
    IF exists(snapshot_dir) AND Glob("{snapshot_dir}/{EXTRACT_GLOB}").length > 0:
      pile_files = Glob("{snapshot_dir}/{EXTRACT_GLOB}")
      Logge: "[A_FX_EXTRACT] Snapshot-Pfad gefunden: {snapshot_dir} ({|pile_files|} files)"
    ELSE:
      # ## BL-346 AK-1: kein Snapshot -> Live-Pile NICHT diesem BL zuordenbar (Relevanz-Gate)
      # Frueher: blindes Glob ueber .claude/pileOfMud/* -> bei einem mature consolidated EPIC
      # (BL-282) waren das 5 FREMDE Files anderer Sessions -> stiller Garbage-Extract.
      # Jetzt: pile_relevance.partition gibt OHNE Snapshot 0 relevante Files zurueck (alle foreign).
      live_pile  = Glob(".claude/pileOfMud/{EXTRACT_GLOB}")
      rel        = py(".claude/scripts/pile_relevance.py").partition_pile_by_relevance(bl_folder, live_pile)
      pile_files = rel.relevant   # ohne Snapshot: leer (kein zuordenbares Material)
      IF |rel.foreign| > 0:
        # "No silent caps": Fremd-Material LAUT melden, NICHT extrahieren.
        Logge: "[A_FX_EXTRACT] WARN BL-346 — kein per-BL Snapshot; {|rel.foreign|} Live-Pile-File(s) "
               "NICHT diesem BL zuordenbar -> NICHT extrahiert: "
               "{[e.path FOR e IN rel.foreign]}. (fremde Session / consolidated EPIC -> Node-Quelle nutzen)"
      ELSE:
        Logge: "[A_FX_EXTRACT] all-mode: {|pile_files|} relevante files (Snapshot fehlt, Live-Pile leer/irrelevant)"
    # ## AK-2 Snapshot-Check END

  IF |pile_files| == 0:
    Logge: "[A_FX_EXTRACT] WARN pileOfMud leer — Findings-Liste wird minimal"

  # 2026-06-01: Read ist polymorph — Text->Text, Bild/PDF->visuell an den Worker.
  IMAGE_PDF_EXT = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".pdf"]
  pile_contents = {}
  is_visual     = {}
  FOR file IN pile_files:
    pile_contents[file] = Read(file)
    is_visual[file]     = ANY(lower(file).endswith(ext) FOR ext IN IMAGE_PDF_EXT)

  # Task-Kontext (Vault-First)
  task_path = "{bl_folder}/1_Task/Task.md"
  IF NOT exists(task_path):
    task_path = "{WORKING_DIR}/Task.md"
  task_content = exists(task_path) ? Read(task_path) : null

SCHRITT 2: Findings-Extraktion (Pattern-Match + LLM-Reasoning)
  findings = []

  # Marker-basierte Heuristik (deterministisch)
  observation_markers  = ["beobachtung", "observation", "fakt", "fact", "ist-zustand"]
  hypothesis_markers   = ["annahme", "hypothese", "vermutung", "moeglicherweise", "vielleicht"]
  burden_markers       = ["last", "schwierigkeit", "problem", "burden", "schmerz", "blocker"]

  FOR file, content IN pile_contents:
    IF is_visual[file]:
      # Bild/PDF: KEINE H2-/Marker-Heuristik (kein Text-Markup). Der Worker extrahiert
      # Findings rein aus dem VISUELLEN Inhalt (Screenshot/Diagramm/Mockup/Annotation)
      # via Reasoning — Read hat ihm das Bild/PDF bereits visuell gezeigt.
      visual_findings = llm_reason_about_visual(content, task_content,
        prompt="Beschreibe den visuellen Inhalt (UI, Fehlermeldung, Diagramm, Mockup) "
               "und leite Findings ab. Pro Finding: type (observation|hypothesis|burden), "
               "text, source={basename(file)}, line_start=0.")
      findings.extend(visual_findings)
      CONTINUE
    sections = split_by_h2(content)
    FOR section IN sections:
      section_text = section.body.lower()
      FOR (markers, type_tag) IN [
        (observation_markers, "observation"),
        (hypothesis_markers, "hypothesis"),
        (burden_markers, "burden")
      ]:
        IF any(marker IN section_text FOR marker IN markers):
          findings.append({
            type: type_tag,
            text: section.title + ": " + section.body[:300],
            source: basename(file) + "#" + section.title,
            line_start: section.line_start
          })

  # Plus: Worker-LLM-Reasoning ueber Volltext (latente Findings)
  # Dieser Schritt nutzt die Reasoning-Faehigkeit des Worker-Models (opus).
  # Kein Sub-Agent-Spawn — der Worker selbst denkt.
  latente_findings = llm_reason_about(pile_contents, task_content,
    prompt="Identifiziere latente Beobachtungen/Hypothesen/Lasten die nicht
            durch explizite Marker gefunden wurden. Pro Finding: type, text,
            source, line_start.")
  findings.extend(latente_findings)

SCHRITT 3: Konsolidierung (Dedup + Sortierung)
  findings = dedup_by_text_similarity(findings, threshold=0.85)
  findings = sort_by(findings, key=lambda f: (f.source, f.line_start))

  # Mindest-Output: bei < 3 Findings -> Exit-Code 1 (PARTIAL)
  status = "OK" if |findings| >= 3 else "PARTIAL" if |findings| > 0 else "FAIL"

SCHRITT 4: Crumbs-Datei schreiben (Vault-First, INV-FX-1 status=draft)
  crumbs_dir = "{bl_folder}/Crumbs"
  bash("mkdir -p {crumbs_dir}")

  # F38-Fix 2026-05-08: file-spezifischer Pfad bei --file Mode
  IF args.has("--file"):
    file_basename = basename(args["--file"])
    FOR ext IN [".md", ".txt", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".pdf"]:
      file_basename = file_basename.replace(ext, "")
    crumbs_path = "{crumbs_dir}/{derived_name}_{file_basename}_findings_crumbs.md"
  ELSE:
    # Legacy / Fallback (kein --file): einzelne aggregierte Crumbs-Datei
    crumbs_path = "{crumbs_dir}/{derived_name}_findings_crumbs.md"

  crumbs_yaml = render_frontmatter({
    type: "findings_crumbs",
    feature: derived_name,
    source_file: args.has("--file") ? args["--file"] : "all_pileOfMud",
    status: "draft",                # INV-FX-1: draft erlaubt, confirmed verboten
    created: ISO_DATE_TODAY(),
    findings_count: |findings|,
    drones_used: 1,                 # Single-Worker (W7)
  })
  crumbs_body = render_findings_list(findings)
  Write(crumbs_path, crumbs_yaml + crumbs_body)

SCHRITT 5: Manifest-Output (INV-FX-3 Schreib-Isolation)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.findingsExtraction = {
    crumbs_total: |findings|,
    drones_used: 1,                 # Single-Worker, NICHT 3 (W7-konform)
    synthesis_pass: true,           # Single-Worker macht Extraktion + Synthese in einem
    crumbs_path: crumbs_path,
    counts_by_type: {
      observation: count_by_type(findings, "observation"),
      hypothesis:  count_by_type(findings, "hypothesis"),
      burden:      count_by_type(findings, "burden")
    },
    last_berater: "findingsExtraction"
  })

SCHRITT 6: Exit
  Logge: "[A_FX_EXTRACT] EXIT crumbs={|findings|} status={status}"
  EXIT (status == "OK") ? 0 : (status == "PARTIAL") ? 1 : 2

SCHRITT 7: Konsolidierungs-Mode (--mode=consolidate)
  # F38-Fix 2026-05-08: Lese alle file-spezifischen Crumbs und baue Master-Crumbs.
  crumbs_dir = "{bl_folder}/Crumbs"
  per_file_crumbs = Glob("{crumbs_dir}/{derived_name}_*_findings_crumbs.md")
  # Filter: Master-Datei selbst nicht mit aufnehmen (falls Re-Run)
  per_file_crumbs = [f FOR f IN per_file_crumbs IF NOT endswith(f, "_master.md")]

  IF |per_file_crumbs| == 0:
    Logge: "[A_FX_EXTRACT] WARN keine file-Crumbs gefunden — kein Konsolidieren noetig"
    EXIT 2 (FAIL)

  master_findings = []
  FOR crumb_file IN per_file_crumbs:
    findings_in_file = parse_findings_from_crumbs(crumb_file)
    master_findings.extend(findings_in_file)

  # Cross-File-Dedup
  master_findings = dedup_by_text_similarity(master_findings, threshold=0.85)
  master_findings = sort_by(master_findings, key=lambda f: (f.source, f.line_start))

  # Master-Crumbs schreiben
  master_path = "{crumbs_dir}/{derived_name}_findings_crumbs_master.md"
  master_yaml = render_frontmatter({
    type: "findings_crumbs_master",
    feature: derived_name,
    status: "draft",                # INV-FX-1: draft, findingsReview macht confirmed
    created: ISO_DATE_TODAY(),
    findings_total: |master_findings|,
    files_consolidated: |per_file_crumbs|,
    consolidation_mode: true
  })
  master_body = render_findings_list(master_findings)
  Write(master_path, master_yaml + master_body)

  # Manifest-Update final (BERATER_OUTPUTS.findingsExtraction)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.findingsExtraction = {
    crumbs_total: |master_findings|,
    files_consolidated: |per_file_crumbs|,
    crumbs_path: master_path,
    consolidation_done: true,
    drones_used: 1,                 # Single-Worker pro File (W7)
    last_berater: "findingsExtraction"
  })

  Logge: "[A_FX_EXTRACT] EXIT consolidate crumbs={|master_findings|} files={|per_file_crumbs|}"
  EXIT 0
```

## INV-FX-4 (NEU v0.2.0): W7-Konformitaet
Dieser Berater spawnt KEINE Sub-Agents. Echte Wellen-Parallelisierung
(z.B. 3 Drohnen ueber chunks von pileOfMud) muss vom Orchestrator
implementiert werden — er spawnt N Berater-Worker mit unterschiedlichen
chunk-Args. Diese Architektur-Klaerung gehoert zu BL-W1-A3.

## Begruendung Modell-Tier

opus — Wellen 3 Drohnen + 1 Synth, Volltext-Reasoning, latente-Hypothesen-Erkennung. Sonnet wuerde subtile Lasten verfehlen.
