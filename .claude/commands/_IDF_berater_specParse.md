---
status: DEPRECATED
deprecated_at: 2026-05-24
deprecated_by: BL-209
deprecated_reason: "Hard-Cut. _A_berater_specParse (A-Pipeline Phase 5a) ist Nachfolger und Single-Source."
version: 0.2.0
type: berater
parent: _IDF_orchestrate
phase: phase_2
model_tier: ceiling
created: 2026-04-25
feature_anchor: BL-142
optional: false
contract:
  reads:
    - {file: ".claude/specs/{NAME}_Spec.md", path: "Volltext", purpose: "Spec-Sektionen, AKs, RFs extrahieren"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.bl_id / bl_slug", purpose: "Feature-Anker"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.specParse", purpose: "Sections + AK-Liste + RF-Liste"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser specParse)"}
    - {file: ".claude/specs/{NAME}_Spec.md", path: "(read-only)"}
  calls:
    - "Wellen-Pattern: 5 Drohnen + 3 Synth + 1 Final (Opus)"
---

# _IDF_berater_specParse (Phase 2 in _IDF_orchestrate)

> **Zweck:** Spec parsen: Sections, AKs, RFs strukturiert extrahieren.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_specParse                                     |
+======================================================================+
|  LIEST:                                                              |
|    .claude/specs/{NAME}_Spec.md (Volltext)                           |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      IDF_PIPELINE_STATE.bl_id / bl_slug                              |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      BERATER_OUTPUTS.specParse = {                                   |
|        sections[], aks[], rfs[],                                     |
|        sections_count, aks_count, rfs_count                          |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser specParse)                              |
|    Spec selbst (read-only)                                           |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 2 (Wellen 5+3+1)                      |
|                                                                      |
|  MODELL-TIER: opus                                                   |
|    Begruendung: Volltext-Spec-Parse + Section-Klassifikation        |
|    + AK/RF-Identifikation. Sonnet uebersieht subtile RFs.           |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-SP-1: Jede AK traegt eindeutige ID (AK-{n} oder {bl}-AK-{n}) |
|    INV-SP-2: Jede RF traegt eindeutige ID                            |
|    INV-SP-3: Schreib-Isolation auf BERATER_OUTPUTS.specParse         |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - Spec existiert                                                  |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - BERATER_OUTPUTS.specParse vollstaendig                          |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_specParse, args="{NAME}")

Parameter:
  {NAME} - Feature-Name

Ausgabe:
  - BERATER_OUTPUTS.specParse (sections, aks, rfs + counts)
  - Exitcode: 0=OK, 2=FAIL

Logging-Format:
  [IDF_SPEC] ENTRY name={NAME}
  [IDF_SPEC] EXIT duration={ms}ms sections={n} aks={k} rfs={m}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  specParse:
    sections:
      - {id: "S-1", title: "Ziel"}
    aks:
      - {id: "AK-1", title: "...", refs: ["S-1"]}
    rfs:
      - {id: "RF-1", title: "...", refs: ["AK-1"]}
    sections_count: 7
    aks_count: 12
    rfs_count: 5
    last_berater: "specParse"
```

## Logik

```
SCHRITT 0: Entry-Log + Spec-Pfad
  spec_path = ".claude/specs/{NAME}_Spec.md"
  Logge: "[IDF_SPEC] ENTRY name={NAME}"
  IF NOT exists(spec_path):
    FAIL: "Spec nicht vorhanden: {spec_path}"

SCHRITT 1: Welle 1 — Section-Extraktion (5 Haiku-Drohnen parallel)
  spec_text = Read(spec_path)
  total_lines = count_lines(spec_text)
  chunk_size = ceil(total_lines / 5)

  drohnen_outputs = parallel(5 workers, model=haiku, fuer i=0..4):
    chunk = slice(spec_text, i*chunk_size, (i+1)*chunk_size)
    PROMPT-Drohne-i:
      "Extrahiere alle Markdown-Sections (## Header) aus dem Chunk.
       Fuer jede Section: id (S-{n}), title, line_start, line_end."
    -> chunk_sections[]

SCHRITT 2: Welle 2 — AK/RF-Extraktion (3 Sonnet-Drafter sequenziell)
  alle_sections = union(drohnen_outputs)
  drafters_outputs = parallel(3 workers, model=sonnet):
    Drafter-A: AK-Extraktion via Pattern "AK-{n}: {Beschreibung}"
    Drafter-B: RF-Extraktion via Pattern "RF-{n}: {Beschreibung}"
    Drafter-C: Cross-Ref-Extraktion (AK -> Section, RF -> AK)

  aks = drafters_outputs[A]
  rfs = drafters_outputs[B]
  cross_refs = drafters_outputs[C]

SCHRITT 3: Welle 3 — Synthese (1 Opus-Final-Pass)
  PROMPT-Synthese:
    Input: alle_sections, aks, rfs, cross_refs
    Aufgaben:
      - Deduplizieren (gleiche AK-ID -> merge)
      - Nummerierung pruefen (luecken-frei)
      - Latente RFs aus Prosa heben (subtile "soll/muss"-Saetze)
      - Cross-Refs validieren (AK referenziert existierende Section)
    Output: {sections, aks, rfs} final konsolidiert

SCHRITT 4: Output schreiben (INV-SP-1, INV-SP-2, INV-SP-3)
  output = {
    sections: synthesized.sections,
    aks: synthesized.aks,
    rfs: synthesized.rfs,
    sections_count: |sections|,
    aks_count: |aks|,
    rfs_count: |rfs|,
    last_berater: "specParse"
  }
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.specParse = output)

SCHRITT 5: Exit
  exitcode = |aks| > 0 ? 0 : 2  # FAIL bei 0 AKs (Spec leer/defekt)
  Logge: "[IDF_SPEC] EXIT duration={ms}ms sections={n} aks={k} rfs={m}"
  EXIT exitcode
```

## Begruendung Modell-Tier

opus — Volltext-Spec mit subtilen Anforderungen. Latente RFs koennen versteckt sein in Prosa-Saetzen. Wellen-Pattern erfordert Synthese-Tiefe.
