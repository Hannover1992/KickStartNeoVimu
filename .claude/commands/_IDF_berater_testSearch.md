# _IDF_berater_testSearch (IDF Phase 7.7 — Coverage-Map, Plan-Zeit)

```yaml
status: active
version: 1.0.0
created: 2026-05-30
op: IntermediateFactory
phase: 7.7
type: berater
tier: middle  # sonnet (haiku verboten — Codebase-Scan + File-Test-Linking)
chain_position: idf-inner
feature_anchor: BL-231/BL-232 (Modus=Test-Coverage, testSearch wandert von i_orchestrate nach IDF)
```

---

## ZWECK (der Durchbruch 2026-05-30)

**testSearch wandert von `_I_orchestrate` (Implement-Zeit, Step 4) nach IDF (Plan-Zeit).** Grund: die
**Test-Coverage entscheidet den MODUS** (M2 vs M3) und **welche Stages laufen** — beides sind PLAN-Fragen, keine
Implement-Fragen. Modus = ART der Aufgabe (Coverage), NICHT Umfang (K-Score).

**KERN-CONSTRAINT (User B, 2026-05-30):** Die gefundenen Tests muessen INTAKT bleiben — die `coverage_map`
wird ZWEIMAL konsumiert:
1. **Modus-Entscheidung** (C3): Ziel-Code mit Tests → M2; ohne → M3.
2. **Implement spaeter** (I-Pipeline/Motor): die gefundenen Tests werden AUSGEFUEHRT (M2 Stage 1 + hoehere
   Stages = testSearch-Treffer gezielt laufen lassen). Deshalb PERSISTENT, nicht weggeworfen.

---

## VERTRAG

```
WORKING_DIR = resolve_bl_path(BL_ID)

LIEST:
  {WORKING_DIR}/_manifest.md
    DF_BATCH_STATE.sub_batch_plan[*]            (Batches + items — von batchPlan/Phase 7)
    BERATER_OUTPUTS_IDF.plBewertung.per_pl_evaluation  (file_refs pro PL-Item)
    {WORKING_DIR}/3_Spec/*_Spec.md              (Ziel-Dateien/Methoden pro AK)
  {VAULT}/_session_params.md
    test_stages (PARAMETER — projekt-vorgesehene Stufen, min [1])   # BL-224
  Codebase (Worktree/Repo): Test-Dateien scannen (xUnit/Integration/E2E je Stage)

SCHREIBT (NUR eigener Slot — INV-THIN-3):
  {WORKING_DIR}/_manifest.md
    BERATER_OUTPUTS_IDF.testSearch.coverage_map     (das Artefakt, persistent — ALLE Batches)
    DF_BATCH_STATE.coverage_per_batch[sub_batch_id] = coverage_map.per_sub_batch[sub_batch_id]
      # SELF-CONTAINED per-batch-Scheibe (NICHT verdict-only!) — 3 Konsumenten lesen je ein anderes Feld:
      #   C3 (Modus)      → .batch_coverage_verdict          (covered/partial/uncovered)
      #   C3 (Modus)      → .coverage_class / .markdown_uncoverable_befund  (BL-314: uncoverable-by-nature → M2)
      #   Pre-SDF (L4)    → .stages_with_tests               (welche Stages laufen)
      #   Motor M2 (L4)   → .per_file[*].covering_tests      (welche Tests ausfuehren)
      # Darum MUSS coverage_per_batch[sb] verdict + coverage_class + stages_with_tests + per_file (covering_tests) enthalten.
  INV-MODUS-1: setzt NIEMALS modus/batch_modes/coverage_modus_hint — liefert NUR Coverage-DATEN.

RUFT: (W7) keine Sub-Agents. Optional parallel-intern: 1 Scan-Pass pro test_stage.
```

---

## COVERAGE-MAP SCHEMA (das persistente Artefakt)

```yaml
coverage_map:
  scanned_at: ISO
  test_stages_scanned: [1, 3, 5]            # aus session_params.test_stages (min [1])
  per_sub_batch:
    SB-x:
      target_files: ["src/Foo/Bar.cs", ...]  # aus file_refs der PL-Items + Spec-Ziel-Dateien
      per_file:
        "src/Foo/Bar.cs":
          covered: true                       # gibt es einen Test der diese Datei/Methode abdeckt?
          covering_tests:                      # File-Test-Linking (INTAKT fuer Implement!)
            - {test_file: "tests/Foo/BarTests.cs", test_name: "Update_SetsField", stage: 1}
            - {test_file: "tests/Integration/BarIT.cs", test_name: "Update_Persists", stage: 3}
          stage_coverage: {unit: true, integration: true, e2e: false}
      # Batch-Aggregat (das C3 fuer den Modus liest):
      batch_coverage_verdict: "covered"        # covered | partial | uncovered
      uncovered_targets: []                    # Ziel-Dateien OHNE Test → treiben M3
      stages_with_tests: [1, 3]                # → L4: welche Stages laufen (Integration da → Stage 3)
      verify_mode: "tdd"                        # BL-276: tdd | scenario | convention — WIE verifiziert wird.
                                                #   Diskriminator: kann das Ziel-Artefakt einen automatisierten
                                                #   RED-Zustand annehmen? (.py/.cs/.js+Harness → tdd; .md/.txt →
                                                #   scenario=Bootstrap-Direkt+Szenario-Verify; .json/.yaml → convention)
      coverage_class: "testable"                # BL-314 AK-2: STRUKTURIERTER Diskriminator pro Sub-Batch —
                                                #   testable | markdown_target_uncoverable. Unterscheidet
                                                #   'untested CODE' (→ M3 test-first richtig) von
                                                #   'uncoverable-by-nature' (Markdown-Skill-Doc/Konzept-Doc, kein
                                                #   ausfuehrbares Artefakt → KEIN RED-Pfad → M2 noetig).
      markdown_uncoverable_befund: false        # BL-314 AK-2: boolesch, ableitbar (siehe ABLAUF). C3 (SDF Phase 1.1)
                                                #   liest es DETERMINISTISCH (Feld, kein Prosa-Parse).
```

---

## ABLAUF (Pseudocode)

```
# Phase 7.7: NACH batchPlan (Phase 7, Ziel-Dateien bekannt), VOR finalSummary (Phase 8.0).
test_stages = session_params.test_stages ?? [1]   # min Stage 1 Unit (BL-224)

FOR sub_batch IN DF_BATCH_STATE.sub_batch_plan:
  target_files = union( pl.file_refs FOR pl IN sub_batch.items ) + spec_target_files(sub_batch)

  # PARALLEL ueber alle test_stages (User B: "fuer alle vorgesehenen Test-Stufen parallel"):
  FOR stage IN test_stages:   # konzeptionell parallel
    tests_at_stage = scan_codebase_for_tests(stage)   # xUnit (1), Integration/Docker (3), Endpoint/E2E (5/6/7)
    FOR f IN target_files:
      hits = link_file_to_tests(f, tests_at_stage)    # File-Test-Linking: deckt ein Test f/Methode ab?
      coverage_map[sub_batch][f].covering_tests += hits
      coverage_map[sub_batch][f].stage_coverage[stage] = (|hits| > 0)

  # Aggregat:
  per_file = coverage_map[sub_batch].per_file
  uncovered = [f FOR f IN target_files IF NOT any(per_file[f].stage_coverage.values())]
  coverage_map[sub_batch].uncovered_targets = uncovered
  coverage_map[sub_batch].batch_coverage_verdict =
      "uncovered" IF |uncovered| == |target_files|       # gar keine Tests → M3 (greenfield)
      ELSE "partial" IF |uncovered| > 0                   # teils → C3 entscheidet (meist M3 fuer die neuen Teile)
      ELSE "covered"                                      # alles abgedeckt → M2
  coverage_map[sub_batch].stages_with_tests = [s FOR s IN test_stages IF any per_file covered at s]

  # BL-276 verify_mode (AK-S4): pro Sub-Batch ableiten WIE verifiziert wird — orthogonal zum coverage_verdict
  # (das sagt OB Tests da sind; verify_mode sagt OB TDD ueberhaupt das richtige Werkzeug ist). Diskriminator =
  # "kann das Ziel-Artefakt einen automatisierten RED-Zustand annehmen?" (Datei-Faehigkeit, NICHT Sprach-naiv).
  # Default-Regel + Projekt-Override: {META}/implementation/verify-mode.md + {BL_FOLDER}/meta-overrides/
  # stage_N.md (AK-S7 — Command agnostisch, Vault steuert). verify_mode_of(f): .py/.cs/.ts/.js(+Harness)→tdd;
  # .md/.txt/.rst→scenario; .json/.yaml/.xml/.toml→convention.
  modes = [ verify_mode_of(f) FOR f IN target_files ]
  coverage_map[sub_batch].verify_mode =
      modes[0]   IF |set(modes)| == 1                      # homogen → klarer Modus
      ELSE "tdd"                                            # heterogen → sicherer tdd-Fallback
  coverage_map[sub_batch].verify_mode_heterogeneous = (|set(modes)| > 1)   # BL-279/BL-456: Datentaeger fuer SCHRITT 7
  # WICHTIG (BL-456): verify_mode_heterogeneous ist reiner Datentaeger — OB Heterogenitaet vorliegt.
  # OB daraus split_required=true folgt, entscheidet C3 SCHRITT 7 Consumer-seitig via INTRA-vs-INTER-AK-Diskriminator
  # (INV-SPLIT-SCOPE-1): split NUR bei INTER-AK-Heterogenitaet (trennbare AKs); INTRA-AK → Misch-Modus, kein split.
  # testSearch emittiert KEINEN Modus-Hint (INV-MODUS-5 gewahrt). Der Scope-Entscheid faellt in C3 SCHRITT 7.
  IF |set(modes)| > 1:
    # Homogenitaet ist das Ziel (J12 build_retrieval_index.py + J13 _W_fetch.md lagen im SELBEN Sub-Batch →
    # Motor nahm den TDD-Umweg fuer J13). Wenn moeglich: nach verify_mode in homogene Sub-Batches splitten.
    Logge: "[IDF_TESTSEARCH] WARN Sub-Batch {sub_batch} heterogen (verify_mode {set(modes)}) — erwaege Split nach verify_mode (BL-276 AK-S4); sonst tdd-Fallback + Motor-WARN"

  # ═══ BL-314 AK-2: coverage_class / markdown_uncoverable_befund (STRUKTURIERTER Diskriminator) ═══
  # ZWECK: C3 (SDF Phase 1.1, _SDF_berater_modusEntscheidung SCHRITT 5) muss 'untested CODE' (→ M3 test-first,
  # RICHTIG) von 'uncoverable-by-nature' (Markdown-Skill-Doc / Konzept-Doc → kein ausfuehrbares Artefakt →
  # kein RED-Pfad → M2 noetig) unterscheiden. Ohne dieses Feld routet der MECHANISCHE Tree (Motor / schwaches
  # Modell) uncovered+Markdown → M3 → stage_abort (BL-239 3× RED). Nur ein denkender Worker rettet es bisher
  # per autoritativem Override — die Falle ist strukturell offen, nur durch Worker-Intelligenz maskiert.
  #
  # ABLEITUNG (deterministisch, reuse der bestehenden verify_mode-Mechanik — KEINE neue Klassifikation):
  #   markdown_uncoverable_befund = (verify_mode == "scenario")                       # .md/.txt/.rst/.adoc dominant
  #                                  AND (batch_coverage_verdict IN ["uncovered", "partial"])  # kein/teil-Test da
  #   d.h. die uncovered/partial Ziel-Dateien sind dominant nicht-coverbare Doku-Artefakte.
  # [BL-473] HARNESS-KONSULTATION: bevor markdown_uncoverable_befund=true gesetzt wird,
  #   die Harness-Detektion konsultieren (has_grep_harness(target_basename, scripts_dir),
  #   .claude/scripts/markdown_uncoverable_resolver.py). Eine Spec-.md MIT realem grep-Test-
  #   Harness (ein test_*.py referenziert den Ziel-Basename im INHALT) ist testbar
  #   (coverage_class=testable -> M3), NICHT markdown_uncoverable — auch wenn die AKs
  #   verdict IN {uncovered, partial} liefern. Der Harness-Befund DOMINIERT den schwankenden
  #   verdict-Term (beseitigt den run-zu-run Nondeterminismus, BL-464/465/466/470 Live-Empirie).
  #   markdown_uncoverable_befund = (verify_mode == "scenario"
  #       AND batch_coverage_verdict IN ["uncovered","partial"]
  #       AND NOT has_grep_harness(target_basename, scripts_dir))   # <-- BL-473-Klausel
  coverage_map[sub_batch].markdown_uncoverable_befund =
      (coverage_map[sub_batch].verify_mode == "scenario"
       AND coverage_map[sub_batch].batch_coverage_verdict IN ["uncovered", "partial"])
  coverage_map[sub_batch].coverage_class =
      "markdown_target_uncoverable" IF coverage_map[sub_batch].markdown_uncoverable_befund == true
      ELSE "testable"
  # INV-TESTSEARCH-1 bleibt absolut: das ist ein Coverage-DATUM, KEIN modus/batch_modes/coverage_modus_hint.
  # C3 liest coverage_per_batch[sb].coverage_class / .markdown_uncoverable_befund deterministisch (Feld, kein
  # Prosa-Parse) und routet uncovered+markdown_target_uncoverable → M2 (BL-314 AK-1 markdown_uncoverable_gate).
  IF coverage_map[sub_batch].markdown_uncoverable_befund == true:
    Logge: "[IDF_TESTSEARCH] Sub-Batch {sub_batch} coverage_class=markdown_target_uncoverable (verify_mode=scenario + verdict={batch_coverage_verdict}) → C3 routet zu M2 (BL-314, kein RED-Pfad)"

Schreibe BERATER_OUTPUTS_IDF.testSearch.coverage_map (alle Batches).
# Pro Sub-Batch die VOLLE per_sub_batch-Scheibe in den DF_BATCH_STATE-Spiegel kopieren (self-contained):
FOR sub_batch IN coverage_map.per_sub_batch:
  DF_BATCH_STATE.coverage_per_batch[sub_batch] = coverage_map.per_sub_batch[sub_batch]
  # enthaelt: target_files, per_file{covered,covering_tests,stage_coverage}, batch_coverage_verdict,
  #          uncovered_targets, stages_with_tests, verify_mode (BL-276),
  #          coverage_class + markdown_uncoverable_befund (BL-314) — alle Konsumenten finden ihr Feld.
Logge: "[IDF_TESTSEARCH] {n} Batches: covered={c} partial={p} uncovered={u} stages_scanned={test_stages}"
```

---

## File-Test-Linking (die Kern-Mechanik, OQ-B)

Wie wird zur Plan-Zeit Coverage gemessen (ohne den Code auszufuehren)?
1. **Namens-/Pfad-Heuristik:** `src/Foo/Bar.cs` ↔ `tests/**/BarTests.cs` (Konventions-Match).
2. **Referenz-Scan:** Test-Dateien nach `using`/`new Bar`/`Bar.Method` durchsuchen → welcher Test instanziiert/ruft das Ziel.
3. **Methoden-Granularitaet (optional, tiefer):** welche Test-Methode ruft welche Ziel-Methode (genauer fuer „teilweise abgedeckt").
4. **Pro Stage:** Stage 1 = Unit-Test-Projekte; Stage 3 = Integration (Docker-getaggte Tests); Stage 5/6/7 = Endpoint/E2E (PowerShell-Skripte/E2E-Projekte).

→ Verdikt-Logik: **alle Ziel-Dateien abgedeckt → `covered` → M2** (aendern + bestehende Tests laufen lassen).
**Mindestens eine Ziel-Datei ohne Test → die ist greenfield → M3** (Test-First fuer den neuen Teil).

---

## INVARIANTEN

- **INV-TESTSEARCH-1:** Liefert NUR Coverage-DATEN, setzt NIE den modus (INV-MODUS-1). coverage_modus_hint VERBOTEN.
- **INV-TESTSEARCH-2:** coverage_map ist PERSISTENT (BERATER_OUTPUTS_IDF.testSearch) — wird NICHT geloescht; Implement-Phase liest die covering_tests, um sie auszufuehren (User-Constraint B).
- **INV-TESTSEARCH-3:** Scan ueber ALLE session_params.test_stages (min [1]), parallel pro Stage.
- **INV-TESTSEARCH-4:** Schreib-Isolation (nur eigener BERATER_OUTPUTS_IDF.testSearch-Slot + coverage_per_batch-Spiegel).
- **INV-TESTSEARCH-5 (BL-314):** `coverage_class` + `markdown_uncoverable_befund` werden PRO Sub-Batch (INV-MODUS-4-Symmetrie) als STRUKTURIERTE Felder emittiert (kein Freitext) — deterministisch aus `verify_mode==scenario AND verdict IN [uncovered,partial]` abgeleitet, reuse der verify_mode-Mechanik (KEINE eigene srs/k-Logik). Sind weiterhin reine Coverage-DATEN (INV-TESTSEARCH-1): KEIN modus.
- **INV-EXTRACT/haiku-verboten:** mindestens sonnet (Codebase-Scan + Linking ist mehrstufig).

---

## DOWNSTREAM-KONSUMENTEN

- **C3 `_SDF_berater_modusEntscheidung`** (L2): liest `coverage_per_batch[sb].batch_coverage_verdict` → M2 (covered) / M3 (uncovered/partial). Ersetzt den K-BOOST als M2/M3-Decider. **BL-314:** liest zusaetzlich `coverage_per_batch[sb].coverage_class` / `markdown_uncoverable_befund` — bei `markdown_target_uncoverable` + uncovered/partial routet C3 SCHRITT 5 (`markdown_uncoverable_gate`) zu **M2** statt M3 (uncoverable-by-nature, kein RED-Pfad → kein stage_abort; BL-239-Wurzel).
- **finalSummary Phase 8.0** (L3): baut den modus_hint aus coverage_verdict + SRS (SC) + Trivial (M1).
- **stagePlanner / Stage-Loop** (L4): `stages_with_tests` → welche Stages real laufen.
- **I-Pipeline Implement** (L3): liest `covering_tests` → fuehrt GENAU diese Tests aus (M2 Stage 1 + hoehere Stages). `_I_testSearch` (alt, Step 4) entfaellt — die Arbeit ist hier schon getan.
- **Motor `dispatch_implement` (L4, BL-276):** liest `verify_mode` (`sb.verify_mode`) → bei `scenario`/`convention` KEIN `_TDD_red/green`, sondern Bootstrap-Direkt-Edit + Szenario-/Konventions-Verify. Fehlt das Feld (Pre-BL-276-Plan), leitet der Motor es als Fallback aus den Datei-Endungen ab (`deriveVerifyMode`).
- **`_I_verify` (BL-276 AK-S5):** ehrt `verify_mode` — ein `scenario`/`convention`-Item wird per Szenario-/Konventions-Beleg VERIFIED, NICHT als „0 pytest = MISSING/RED" geblockt.

---

## BL-Anker
BL-231 (Modell: Modus=Coverage), BL-232 (Entscheidung: testSearch→IDF, K-Score/SRS=Clustering), BL-224 (test_stages-Parameter), BL-276 (verify_mode), BL-314 (coverage_class / markdown_uncoverable_befund — Producer fuer das C3 markdown_uncoverable_gate, BL-239-Wurzel; siehe [[feedback_markdown_engine_bootstrap]]). Findings: `modus_model_findings_2026-05-30.md` (kristallisierte Architektur).
