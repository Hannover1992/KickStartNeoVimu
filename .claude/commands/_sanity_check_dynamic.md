---
type: satellite
status: active
version: 1.0.0
created: 2026-05-08
op: Sanity-Check-Dynamic Live-Pipeline-Beobachtung
phase: Meta
chain_position: standalone
reference_run: DCSRE-486 (2026-05-08, Erst-Validierung)
companion_skill: _sanity_check (statisch — Code-Snapshot-Audit)
---

# /_sanity_check_dynamic — Live-Pipeline-Beobachtungs-Audit

> **Zweck:** Beobachtet einen LIVE-Pipeline-Lauf (statt statischer Code-Audit wie
> `/_sanity_check`) und sammelt Findings nach Triage-Logik (Live-Fix / PL / BL).
> Geboren aus Erst-Lauf DCSRE-486 am 2026-05-08 (88 Findings, 6 BL-Items, 3 Skill-Patches).

> **Komplementaer:** `/_sanity_check` (statisch) und `/_sanity_check_dynamic` (dynamisch)
> sind Schwester-Skills. Static = Architektur-Plaene-Audit. Dynamic = Hotelbetrieb-Audit.

---

## Aufruf

```
/_sanity_check_dynamic [target] [mode] [scope] [--start={pipeline}]
```

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `target` | `current` | `BL-{NNN}` \| feature-name \| `current` | Welche Story / welcher Lauf |
| `mode` | `echo` | `live` \| `echo` \| `post-hoc` | Beobachtungs-Modus |
| `scope` | `full` | `full` \| `pipeline` \| `skill` \| `memory` | Tiefe der Auditierung |
| `--start=` | `auto` | `pre-pipeline` \| `backlog` \| `bdf` \| `bl` \| `a` \| `idf` \| `sdf` \| `i` \| `tdd` \| `auto` | Start-Punkt der Beobachtung (auto = aus Manifest A_PIPELINE_STATE.phase ableiten) |

**Beispiele:**
```
/_sanity_check_dynamic                                        → echo-Modus, current Lauf, auto-detect
/_sanity_check_dynamic DCSRE-486 echo full                    → User pastet Outputs (echo), full-scope
/_sanity_check_dynamic DCSRE-486 post-hoc full                → Retrospektiv aus Vault-Artefakten
/_sanity_check_dynamic DCSRE-486 echo full --start=idf        → Beobachtung beginnt bei IDF (DCSRE-486 schon SC-REIF nach A-Pipeline)
/_sanity_check_dynamic DCSRE-486 echo pipeline --start=sdf    → Nur SDF beobachten (z.B. nach IDF DONE)
/_sanity_check_dynamic _spec.md echo skill                    → Einzelner Skill (Skill-spezifischer Watch)
```

**Start-Point-Auto-Detection** (`--start=auto`):
Liest `{VAULT}/Backlog/{slug}/_manifest.md` A_PIPELINE_STATE.phase + a_pipeline_completed:
```
- A_PIPELINE_STATE.phase=COMPLETED + idf_pipeline_state empty → start=idf
- IDF_PIPELINE_STATE.phase=COMPLETED + sdf_pipeline_state empty → start=sdf
- SDF_PIPELINE_STATE.phase=BATCH_RUNNING + i_pipeline_state empty → start=i
- I_PIPELINE_STATE.phase=STAGE_N → start=i (resume in Stage N)
- All empty → start=pre-pipeline (fresh)
```

**Modi-Erklaerung:**

- **`live`**: Skill laeuft in OmniCommand-Branch PARALLEL zum Operator-Pipeline-Branch.
  Erfordert Cross-Session-Tooling (aktuell experimentell — User leitet Outputs manuell).
- **`echo`**: User pastet Pipeline-Output ins Skill-Fenster. Skill analysiert + persistiert.
  **Pragmatisch validierter Standard** (DCSRE-486 lief im echo-Modus).
- **`post-hoc`**: Nach Pipeline-Ende. Skill liest Vault-Artefakte (Manifest, _manifest_protokoll,
  BERATER_OUTPUTS) + erstellt Sanity-Report retrospektiv.

---

## VERTRAG

```
+======================================================================+
| COMMAND: /_sanity_check_dynamic                                      |
+======================================================================+
|                                                                      |
| ACTOR: SANITY-OBSERVER (Team Lead direkt, OmniCommand-Branch)        |
|                                                                      |
| LIEST:                                                               |
|   {VAULT}/Backlog/{slug}/_manifest.md                                |
|     BERATER_OUTPUTS.* + A_PIPELINE_STATE                             |
|   {VAULT}/Backlog/{slug}/_manifest_protokoll.md   (Pattern-B Audit)  |
|   {VAULT}/Backlog/{slug}/{1_Task,2_Model,3_Spec,...}/   (Artefakte)  |
|   .claude/_session_params.md  (dark_factory + hil-Werte)             |
|   .claude/_parking-lot.md  (existing Sanity-Block)                   |
|   User-pastes (echo-Modus)                                           |
|                                                                      |
| SCHREIBT:                                                            |
|   .claude/output/Audit_Dynamic_Live_{TARGET}_{DATE}.md  (master)     |
|   .claude/_parking-lot.md   (Sanity-Block APPEND)                    |
|   .claude/audit/audit.jsonl  (strukturierte Findings, F{N})          |
|   {OmniCommand-Vault}/Backlog/BL-{NNN}-{slug}.md  (BL-Item-Anlage)   |
|   {OmniCommand-Vault}/_backlog_index.md  (Counter + Tabelle)         |
|   ~/.claude/projects/{path}/memory/project_sanity_dynamic_*.md       |
|   {VAULT}/Backlog/{slug}/3_Audit/CaseStudy_DynamicSanityCheck_*.md   |
|                                                                      |
| FINDINGS-KATEGORIEN (Triage-Aktionen):                               |
|   GEFIXT      : <20 LOC mechanisch, reversibel → INLINE-Fix         |
|   DRIFT       : Unerwartetes Skill-Verhalten, dokumentiert → PL     |
|   KRITISCH    : Architektur-Verletzung, systemisch → BL-Item        |
|   POSITIV     : Best-Practice oder Live-Validierung von Spec        |
|   RE-EVAL     : zurueckgenommen mit Param-Kontext (z.B. dark_factory)|
|                                                                      |
| TRIAGE-MATRIX:                                                       |
|   trivial  + DRIFT    → Live-Fix + Redeploy                         |
|   mittel   + DRIFT    → PL mit Skill-Patch-Vorschlag                |
|   hoch     + KRITISCH → BL-Item formal mit AKs                      |
|   user-direktive       → BL-Item (Architektur-Erweiterung)         |
|                                                                      |
| INVARIANTEN:                                                         |
|   INV-SCD-1: Findings sind aufsteigend nummeriert (F1, F2, ...)     |
|   INV-SCD-2: Phase-Zuordnung pflicht (welche Pipeline-Phase produzierte F{N})|
|   INV-SCD-3: Triage-Entscheidung pflicht (live-fix / PL / BL)        |
|   INV-SCD-4: Bei BL-Anlage: Counter inkrement + Index-Append        |
|   INV-SCD-5: Endbilanz pflicht (Tabelle aller F{N} + Aktionen)      |
|   INV-SCD-6: Cross-Refs zu Vault-Artefakten pflicht (Provenance)    |
|   INV-SCD-7: Audit-Trail in audit.jsonl strukturiert (Cross-Run)    |
|   INV-SCD-8: Dual-Branch-Awareness (Operator-Branch erkennen)       |
|                                                                      |
+======================================================================+
```

---

## Begruendung (Why dynamic statt static)

Statisches `/_sanity_check` (Schweizer-Uhrmacher Code-Audit) findet:
- Drift in Code/Skill-Source
- Skelett-Code, veraltete Pfade
- Schema-Inkonsistenzen
- Aber: **nur Snapshot, kein Live-Verhalten**

User-Analogie 2026-05-08:
> "Architekturplaene anzuschauen sagt dir nicht, ob der Hotelbetrieb laeuft."

Dynamic-Sanity-Check ergaenzt:
- Live-Beobachtung von Pipeline-Spawn-Reihenfolge
- Manifest-Updates pro Phase (BERATER_OUTPUTS)
- Worker-Awareness (worker_context im Spawn-Prompt)
- Vertragstreue (INV-PM-2 Skill-Load, INV-AO-CALLER Orchestrator-Caller)
- Vision-Match (was hinten rauskommt deckt sich mit User-Intent)

**Empirischer Beweis (DCSRE-486-Erstlauf 2026-05-08):**
88 Befunde in einem Lauf. Statischer Audit haette ~30 davon erreicht. Die anderen ~58
sind nur durch Live-Beobachtung sichtbar (Skill-Load-Pattern, Auto-Confirm-Logik,
HiL-Compliance, Worker-Spawn-Verhalten, Token-Effizienz, Param-Conditional Verhalten).

---

## Schritt 1: Modus-Erkennung + Setup

```
IF target == "current":
  Lese .claude/_session_params.md (dark_factory, hil)
  Lese {VAULT}/_manifest.md A_PIPELINE_STATE.backlog_active → target = active_BL_ID
ELSE:
  target = args.target

bl_folder = resolve_bl_path(target)
audit_file = ".claude/output/Audit_Dynamic_Live_" + target + "_" + ISO_DATE + ".md"

IF mode == "post-hoc":
  Lese alle Vault-Artefakte aus bl_folder
  GOTO Schritt 5 (Endbilanz erstellen)
ELIF mode == "echo":
  Erwarte User-Pastes (Worker-Outputs nach jeder Pipeline-Phase)
ELIF mode == "live":
  WARNING: "live-Modus experimentell. Cross-Session-Tooling fehlt. Fallback auf echo."
  mode = "echo"
```

## Schritt 2: Audit-File initialisieren

Frontmatter:
```yaml
---
type: sanity-dynamic-audit
target: {BL-ID oder feature-name}
mode: echo | live | post-hoc
scope: full | pipeline | skill | memory
created: {DATE}
session_params:
  dark_factory: {true|false}
  hil: {off|cycle|phase|manual}
  difficulty: {easy|normal|hard}
  ceiling: {haiku|sonnet|opus}
  floor: {haiku|sonnet}
reference_run: DCSRE-486 (2026-05-08, Erst-Validierung 88 Findings)
findings_count: 0
triage_summary:
  live_fix: 0
  pl: 0
  bl: 0
  positive: 0
  re_eval: 0
related_bl: []  # wird gefuellt mit BL-IDs angelegt
---
```

Body initialisieren mit Run-Setup-Sektion + Findings-Tabelle (leer).

## Schritt 3: Pro Pipeline-Phase — Watch-Listen anwenden

Aus DCSRE-486-Erstlauf (Reference-Run) abgeleitete Watch-Patterns:

### Phase Pre-Pipeline (`/_param`, `/_backlog`)

- **Worker-Awareness Check:** `current_context.py` muss bl_id + vault_root + bl_folder NICHT-LEER liefern. Sonst BLOCKER.
- **Cross-Platform-Lint:** Subprocess-Calls mit `sys.executable` (nicht `python3`)
- **Vault-Pfad-Konsistenz:** `process_state_files` ↔ `vaults[X].linux_path` matchen
- **Symlink-Hygiene:** Vault-Pfade duerfen nicht via Symlink auf alte Worktrees zeigen
- **State-File-Init:** `_manifest.md`, `_session_params.md`, `_backlog_index.md` muessen existieren

→ Findings-Pattern: F1-F5 (DCSRE-486)

### Phase /_backlog (Story-Intake)

- **Counter-Inkrement:** `backlog_counter` 0→1 sauber
- **3-Phasen-Persistenz:** Vault-Knoten + Index-Append + Manifest-Update
- **Subfolder-Struktur:** 6 Pflicht-Folder (1_Task..6_PL) plus optional (Crumbs, Sources, Implementation, ...)
- **Per-Story-Manifest** (BL-155 AK-1) — VaultDrivenDevelopment-konform
- **RAW-Snapshot:** pileOfMud-File ggf. ins `Sources/`-Subfolder snapshotten (BL-160)
- **Naming-Schema:** BL-{NNN} oder DCSRE-{NNN} (gemischt erlaubt — F9)

→ Findings-Pattern: F8-F12

### Phase /_BDF_orchestrate / /_BL_orchestrate

- **Skill-Load:** `Skill(_X_orchestrate)` als ECHTER Tool-Call (nicht inline-interpretiert)
- **State-Machine:** Klare Phase-Transitionen (INIT → SCANNING → ITEM_RUNNING → ...)
- **Anti-Zirkel-Guards:** `bdf_bl_handoff_depth`, `reifung_cycles` aktiv
- **HiL-Compliance:** Bei `hil=phase` Pause nach jeder Phase, bei `hil=off` Dark Factory

→ Findings-Pattern: F13-F32

### Phase /_A_orchestrate (16 Phasen)

**0.1 modusErkennung:** Worker-Tier konsistent (haiku oder sonnet?), BERATER_OUTPUTS reichhaltig
**0.2 discovery:** SKIP wenn name explizit + kein --parent-pr
**0.5 findingsExtraction:** File-Iteration ueber pileOfMud (BL-161 AK-2 + RF-WF-LIVE 4-Stufen),
  Welle-Skalierung respektiert difficulty (easy=1 Worker, INV-EXTRACT-1 floor=sonnet)
**0.5.2 findingsReview:** Cluster-Assays + /_question Pattern (Gold-Standard)
**0.6 taskDefinition:** Single Worker, 14 AKs + 12 DoD strukturiert
**2.5 W_fetch:** 4-Stufen-Strategie (Anker-First + Disambig + Graph-Traversal + Keyword-Glob)
**3 model:** RF-MODEL-LIVE Pflicht-Frontmatter + 11 Sektionen + Edges-Pflicht (11 Edge-Typen)
**4 spec:** RF-SPEC-LIVE Auto-Confirm-Logik (mit BL-163 Korrektur fuer hil=phase)
**4k K_score:** First-Principle-Herleitung (BL-162 AK-1) + LSP-Integration (BL-162 AK-2) + Separation of Concerns (BL-162 AK-7)
**4g gap:** IST-vs-SOLL Coverage-Klassifikation
**4.2a metadatenAggregation:** Reifegrad-Routing-Entscheidung (KRITISCH bei hil=phase HiL-Pause)
**4.4 gitTracking + 4.3 stateMaintain:** mechanisch
**5 routing:** completion_signal setzen, param-conditional dark_factory beachten

→ Findings-Pattern: F33-F87

### Phase /_IDF_orchestrate (Decomposition, 8 Phasen)

**Watch-Listen (Skelett — wird bei IDF-Live-Run inkrementell erweitert):**
- **0.5 teamSetup:** active_team `i-{slug}`, ceiling/floor angewandt
- **1 resumeGuard + init:** IDF_PIPELINE_STATE-Init im Per-Story-Manifest
- **2 specParse:** AKs-Extraktion aus `3_Spec/...Spec.md`, ak_count konsistent mit Spec-Frontmatter
- **3.1 akExtraktion (parallel pro Cluster):** Wellen-Skalierung respektiert difficulty
- **3.2 plAggregation:** PL_Master_{date}.md erstellt, Items konsolidiert
- **3.5 validator:** AK-Coverage-Check
- **3.6 itemContext:** worker_context pro PL-Item gesetzt
- **3.7 modelSync:** PL→Model/Spec Promotion (cross-story Patterns extrahieren)
- **4 dependencyAnalyzer:** Pattern-Library-Lookup, Edges erkennen
- **5 clustering:** Items thematisch gruppieren
- **6 sequencePlanner:** Reihenfolge optimieren
- **7 batchPlan:** Opus-Synthese, DF_BATCH_STATE.batch_items befuellen, K-Score-Inputs nutzen (BL-162)
- **8 IDF_DONE:** completion_signal + routing-Hint

→ Findings-Pattern: F-IDF-{N} (eigene Numerierung pro Pipeline)

### Phase /_SDF_orchestrate (Batch-Worker, INNER LOOP)

**Watch-Listen (Skelett):**
- **0 resumeGuard:** DF_BATCH_STATE prufung
- **0.5 testRun-Fork:** --mode=testRun erkannt
- **1.0 analyse:** A-Pipeline-Recall, Batch-Size-Evaluation
- **1.0 architecturalBrief:** PT-Layer-Lookup (Libraries/PatternLibrary)
- **1.1 modusEntscheidung:** M1..M9 Routing (HIER ist legitime Modus-Empfehlung — BL-162 AK-7 Param-conditional)
- **1.5 patternBrief:** PT-Pattern-Lookup
- **1.6 IDF-GATE:** Plausibilitaets-Check
- **2 EXECUTION DISPATCH:** Skill-Tool-Calls (M2 → I_orchestrate, M3 → I+TDD, M4-M7 → SC, M8 → T, M9 → WP)
- **3 BATCH-ENDE:** recalibrate + postItem + statusTransition + modelSync + PT/SL-Promote + batchEnde
- **4 loopDecision:** ROLLBACK / RE-BATCH / TERMINATE

→ Findings-Pattern: F-SDF-{N}

### Phase /_I_orchestrate (Implementation, Stufen-Loop)

**Watch-Listen (Skelett):**
- **0 ResumeGuard:** Stage-N-Erkennung
- **1 teamSetup + 2 kurzlebigPrompt + 3 teamLeadSteuerung**
- **STUFEN-LOOP S1-S5:**
  - Blueprint: architect / requirementCheck / patternLibrary / testSearch / goldDefine / blueprintQG
  - cleanCodeSlice / mitose / fanOut
  - TDD-Phase (needs_tdd=true): SDF-Hub → /_TDD_orchestrate
  - Stage-Transition: commit + handschuh-wechsel
- **EXIT-PHASE:** /_I_verify global, Scope-Gate, Rollover Pattern B

→ Findings-Pattern: F-I-{N}

### Phase /_TDD_orchestrate (RED/GREEN/REFACTOR)

**Watch-Listen (Skelett):**
- 8a RED: failing test schreiben → 8b execute-RED
- 8c GREEN: minimaler Code → 8d execute-GREEN
- 8e refactorCode (Opus) → 8f execute
- 8g refactorTests → 8h execute
- 8i check (gold?)
- 9 verify pro Slice, 10 fanIn, 11 Stufen-QG (HiL)

→ Findings-Pattern: F-TDD-{N}

**Erweiterbarkeit:** Diese Skeletons werden bei jedem Live-Run einer neuen Pipeline
inkrementell mit konkreten Findings angereichert (analog wie A-Pipeline durch DCSRE-486
zu 88 Findings kam). Neue Watch-Patterns werden in dieser Skill-Datei erweitert.

### Cross-Phase-Watches

- **Token-Effizienz:** Mechanik-Phasen ~30-50k (sonnet), Substanz ~110-160k (opus), 1-Pass-Pattern
- **W7-Disziplin:** Workers stateless, kein Sub-Agent-Spawning, Stirb-nach-Durchlauf
- **Skill-Routing:** Skill-zu-Skill via `Skill(...)` Tool-Call (Mega-Agent vermeiden)
- **Param-Conditional:** dark_factory + hil bestimmen erlaubtes Worker-Verhalten

## Schritt 4: Findings extrahieren + Triage

Pro Output (User-Paste in echo-Modus):

```python
findings = []

FOR observation IN parse_pipeline_output(output):
    f = {
      "id": "F" + next_counter(),
      "kategorie": classify(observation),  # GEFIXT|DRIFT|KRITISCH|POSITIV|RE-EVAL
      "beschreibung": observation.text,
      "pipeline_phase": observation.phase,
      "source_node": observation.source,
      "complexity": estimate_complexity(observation),  # trivial|mittel|hoch
      "param_context": current_session_params(),
    }
    
    # Triage-Entscheidung
    IF f.complexity == "trivial" AND f.kategorie == "DRIFT":
      f.action = "live-fix"
      apply_live_fix(f)  # Edit + Redeploy
    ELIF f.complexity == "mittel":
      f.action = "PL"
      append_to_parking_lot(f)
    ELIF f.complexity == "hoch" OR f.systemisch:
      f.action = "BL"
      bl_id = create_bl_item(f)  # Counter inkrement + Index-Append
      f.related_bl = bl_id
    ELIF f.kategorie == "POSITIV":
      f.action = "dokumentieren"
      append_to_audit_positive_section(f)
    ELIF f.kategorie == "RE-EVAL":
      f.action = "korrigieren"
      mark_previous_finding_as_revised(f)
    
    audit_append(f)
    audit_jsonl_append(f)  # strukturiert fuer Cross-Run-Audit
    findings.append(f)
```

## Schritt 5: Endbilanz erstellen

Master-Tabelle in Audit-File:

```markdown
## Endbilanz (Sanity-Check-Dynamic 2026-05-08)

| Kategorie | Anzahl | F-IDs |
|-----------|--------|-------|
| GEFIXT live | {N} | F1, F2, ... |
| Skill-Patches | {N} | RF-WF-LIVE, RF-MODEL-LIVE, ... |
| POSITIV | {N} | F11, F23, F33, ... |
| BL-Items angelegt | {N} | BL-158, BL-159, ... |
| PL-Folge-Items | {N} | F4, F10, F12, ... |
| RE-EVAL | {N} | F81, F82, ... |
| Architektur-Direktiven (User) | {N} | ... |

## Token-Bilanz Pipeline

[pro Phase: Worker, Tier, Tokens, Tool-Uses]

## BL-Items (formal angelegt)

| BL-ID | Title | Prio | Source-Findings |
|-------|-------|------|----------------|
| BL-{NNN} | ... | ... | F{NNN} |
```

## Schritt 6: Persistenz finalisieren

```
1. Audit-File abschliessen (Endbilanz-Sektion + Cross-Refs)
2. PL-Sanity-Block updaten ({SANITY-CHECK-DYNAMIC-{DATE}})
3. Memory-Files anlegen:
   - project_{target}_completion.md
   - project_sanity_dynamic_findings_{DATE}.md
   - MEMORY-Index aktualisieren
4. CaseStudy in {VAULT}/Backlog/{slug}/3_Audit/CaseStudy_DynamicSanityCheck_{DATE}.md
5. audit.jsonl APPEND mit allen Findings (strukturiert, fuer kuenftige Cross-Run-Vergleiche)
```

## Schritt 7: Exit + Reporting

Output:
```
[SANITY_DYNAMIC] EXIT target={target} findings={N} mode={mode}
  Live-Fix: {N1}  PL: {N2}  BL: {N3}  POSITIV: {N4}  RE-EVAL: {N5}
  BL-Items angelegt: {comma_separated}
  Audit-File: {path}
  CaseStudy: {path}
  Memory: {N_files} updated
```

---

## Reference-Run: DCSRE-486 (2026-05-08)

Erst-Validierung des `/_sanity_check_dynamic`-Konzepts durch Live-Lauf:

| Aspekt | Wert |
|--------|------|
| Pipeline | A-Pipeline (12 Phasen + 14 Worker-Spawns) |
| Modus | echo (User pastete Outputs in OmniCommand-Branch) |
| Dauer | ~3h Wall-Clock (User-Beobachtung mit hil=phase) |
| Tokens | ~1.25M (Substanz-Phasen 110-160k Opus, Mechanik-Phasen 30-50k Sonnet) |
| **Findings** | **88 (F1-F88)** |
| **GEFIXT live** | 9 (F1, F2, F3, F5, F6, F9, F13, F38) |
| **Skill-Patches** | 3 (RF-WF-LIVE, RF-MODEL-LIVE, RF-SPEC-LIVE) |
| **BL-Items** | 6 (BL-158 bis BL-163) |
| **PL-Folge-Items** | 7 (F4 GEFIXT, F10, F12, F14-F16, F88) |
| **POSITIV** | ~30 (F11, F23, F33, F37, F40-F47, F66-F70, F73-F76, F77-F80, F83, F85, F89) |
| **RE-EVAL** | 2 (F81, F82 — param-conditional dark_factory) |
| **Architektur-Direktiven (User)** | 5 (Vault-Driven A, Source-Provenance, Vault-Skalierung 200k, K-Score-LSP, HiL-Symmetrie) |

**Skill-Patches im Detail:**
- `_W_fetch.md` — 4-Stufen-Strategie (Anker-First + Disambig + Graph + Keyword)
- `_model.md` — STRENGE Variante (Pflicht-Frontmatter, 11 Sektionen, 11 Edge-Typen)
- `_spec.md` — STRENGE Variante (Auto-Confirm-Logik — von BL-163 korrigiert)

**BL-Items im Detail:**
- BL-158: Memory-Architektur Worktree-Inheritance (mittel)
- BL-159: Skill-Loading-Compliance — Mega-Agent-Praevention (KRITISCH)
- BL-160: Source-Provenance-System — Coherenz-Kette (HOCH)
- BL-161: Vault-Quality-System — Skalierung 2k→200k (HOCH)
- BL-162: K-Score Coupling-Enhancement — LSP + Multi-Step + SoC (HOCH)
- BL-163: HiL-Review-Symmetrie — Cluster-Assays + /_question Pattern (HOCH)

---

## Architektur — Dual-Branch-Setup

```
+----------------------------------+              +----------------------------------+
| OPERATOR-BRANCH                  |              | ANALYST-BRANCH                   |
| (im Worktree, fuehrt Pipeline)   | <-- echo --> | (in OmniCommand, beobachtet)     |
|                                  |              |                                  |
| - /_BDF_orchestrate              |  Output      | - /_sanity_check_dynamic         |
| - /_A_orchestrate                |  paste       | - Findings-Triage                |
| - Worker-Spawns                  |  via         | - Live-Patches (Quick-Wins)      |
| - Vault-Persistierung            |  User        | - PL/BL-Anlage                   |
| - HiL-Pausen (bei hil=phase)     |              | - Audit-File-Update              |
+----------------------------------+              +----------------------------------+
                |                                              |
                +-------------> Vault (Shared) <---------------+
                       (DCS/DCSRE/Backlog/{slug}/...)
```

**Echo-Loop pro Pipeline-Phase:**
1. Operator triggert Phase (z.B. `/_param`, `/_backlog`, Phase 0.5, ...)
2. Worker-Output erscheint in Operator-Branch
3. User pastet Output in Analyst-Branch (`/_sanity_check_dynamic` Skill aktiv)
4. Skill analysiert + triagt + persistiert
5. Findings + ggf. Quick-Fixes flow back
6. Nächste Phase

---

## Patch-Targets fuer kuenftige Erweiterungen

Nach BL-163 (HiL-Review-Symmetrie) werden folgende Skills erweitert:
- `_K_score.md` — STRENGE Variante (BL-162 AK-5 + BL-163 HiL-Review)
- `_gap.md` — STRENGE Variante (BL-163 HiL-Review)
- `_A_berater_metadatenAggregation.md` — HiL-Review fuer Reifegrad-Entscheidung (BL-163 AK-5)
- `_taskDefinition.md` — STRENGE Variante (Pattern uebernehmen)
- `_A_berater_routing.md` — Param-Conditional dark_factory (F86)

Worker-Vertraege werden konsequent angeglichen:
- Pflicht-Frontmatter mit kompletten Audit-Feldern
- Edges-Manifest pflicht (11 Edge-Typen)
- Anker-Verbindung pflicht
- Stirb-nach-Durchlauf (W7-Disziplin)
- Cross-Pipeline-Konsistenz

---

## Hinweise

- **Cross-Run-Audit:** `audit.jsonl` sammelt Findings strukturiert ueber alle Sanity-Runs.
  Pattern-Erkennung: welche Findings tauchen bei JEDEM Lauf auf? → systemische Issues.
- **Memory-Updates:** Nach jedem Lauf MEMORY.md Index erweitern um Sanity-Findings-Datei.
- **BL-Items werden formal:** Counter inkrement, Index-Append, Vault-Knoten anlegen
  (analog manueller `/_backlog`-Aufruf, hier integriert).
- **Echo-Modus ist STANDARD** bis Cross-Session-Tooling existiert.
- **Companion zu `/_sanity_check`** (statisch): beide ergaenzen sich. Static = Code-Drift,
  Dynamic = Verhalten-Drift.
- **Reference-Run als Lern-Vorlage:** DCSRE-486 (2026-05-08) ist Trainings-Datensatz fuer
  Pattern-Erkennung. Bei kuenftigen Sanity-Runs: gleiche Watch-Listen anwenden, Findings
  vergleichen, Patterns verfeinern.

---

*Geboren aus DCSRE-486 Erst-Lauf 2026-05-08 — 88 Findings, 6 BL-Items, 3 Skill-Patches.
Companion zu /_sanity_check (statisch). Kern: Live-Pipeline-Beobachtung mit Triage-Logik.*
