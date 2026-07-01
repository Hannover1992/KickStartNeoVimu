---
status: active
version: 0.2.0
type: berater
parent: _A_orchestrate
phase: phase_0.1
model_tier: middle
created: 2026-04-25
updated: 2026-05-06
feature_anchor: BL-142
optional: false
changelog_0_2_0: |
  v0.2.0 (2026-05-06): Skelett -> produktiv.
    - Vollstaendiger Pseudocode (Existenz-Checks + Decision-Tabelle + git rev-parse).
    - Vault-First Pfade via resolve_bl_path.py (statt .claude/models/).
    - INV-MOD-4 NEU: Worker spawnt KEINE Sub-Agents (W7-konform, sequentielle Reads).
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.modus / a_status / git_baseline", purpose: "Resync-vs-Fresh-Erkennung"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md", path: "Existenz-Check", purpose: "Vault-First (BL-151) — fresh vs resync"}
    - {file: ".claude/models/{NAME}_Model.md", path: "Existenz-Check FALLBACK", purpose: "Legacy-Fallback nur bei Vault-Miss"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/1_Task/Task.md", path: "Existenz-Check", purpose: "Aufgabendefinition vorhanden?"}
    - {file: ".claude/pileOfMud/", path: "Verzeichnis-Listing", purpose: "Roh-Material vorhanden?"}
    - {file: "git", path: "rev-parse HEAD", purpose: "git_baseline setzen"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.modus", purpose: "fresh|resync"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.git_baseline", purpose: "HEAD-SHA bei Modus-Entscheidung"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.modusErkennung", purpose: "Schema (s.u.)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser modusErkennung)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.routing_target"}
  calls: []
---

# _A_berater_modusErkennung (Phase 0.1 in _A_orchestrate)

> **Zweck:** Vor Tasks erkennen, ob es sich um einen frischen Lauf oder ein Resync (bestehendes Model) handelt.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_modusErkennung                                  |
+======================================================================+
|  LIEST:                                                              |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      A_PIPELINE_STATE.modus (Vorabwert)                              |
|      A_PIPELINE_STATE.a_status                                       |
|      A_PIPELINE_STATE.git_baseline                                   |
|    .claude/models/{NAME}_Model.md (Existenz-Check)                  |
|    {taskMd} (Existenz-Check)                                         |
|    {pileOfMud} (Existenz-Check)                                      |
|    git rev-parse HEAD                                                |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      A_PIPELINE_STATE.modus = "fresh" | "resync"                     |
|      A_PIPELINE_STATE.git_baseline = "{sha}"                         |
|      BERATER_OUTPUTS.modusErkennung = {                              |
|        modus, model_exists, task_present, pile_present,              |
|        git_baseline                                                  |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser modusErkennung)                         |
|    A_PIPELINE_STATE.routing_target / derived_name                    |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 0.1 (vor Tasks)                         |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Existenz-Checks + Vorabwert-Vergleich,              |
|    Tabellen-Logik. Kein Deep-Reasoning.                             |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-MOD-1: modus IN {fresh, resync}                               |
|    INV-MOD-2: resync impliziert Model existiert UND a_status != IDLE |
|    INV-MOD-3: Schreib-Isolation auf BERATER_OUTPUTS.modusErkennung   |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - {WORKING_DIR}/_manifest.md existiert                                          |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - A_PIPELINE_STATE.modus + git_baseline gesetzt                   |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_A_berater_modusErkennung, args="{NAME}")

Parameter:
  {NAME} - Feature-Name

Ausgabe:
  - A_PIPELINE_STATE.modus
  - A_PIPELINE_STATE.git_baseline
  - BERATER_OUTPUTS.modusErkennung
  - Exitcode: 0=OK, 2=FAIL

Logging-Format:
  [A_MODUS] ENTRY name={NAME}
  [A_MODUS] EXIT duration={ms}ms modus={fresh|resync}
```

## Output-Schema

```yaml
A_PIPELINE_STATE:
  modus: "fresh"
  git_baseline: "abc1234"

BERATER_OUTPUTS:
  modusErkennung:
    modus: "fresh"
    model_exists: false
    task_present: true
    pile_present: true
    git_baseline: "abc1234"
    last_berater: "modusErkennung"
```

## Logik (v0.2.0 produktiv)

```
SCHRITT 0: Entry + Args
  NAME = args[0]
  Logge: "[A_MODUS] ENTRY name={NAME}"

SCHRITT 1: Manifest-Vorabwerte lesen
  manifest = Read({WORKING_DIR}/_manifest.md)
  prev_modus  = manifest.A_PIPELINE_STATE.modus     ?? null
  prev_status = manifest.A_PIPELINE_STATE.a_status  ?? "IDLE"
  prev_baseline = manifest.A_PIPELINE_STATE.git_baseline ?? null

SCHRITT 2: BL-Folder + Vault-Pfade aufloesen (INV-VAULT-9)
  bl_folder = subprocess(".claude/scripts/resolve_bl_path.py", BL_ID).stdout.strip()
  model_path_vault = "{bl_folder}/2_Model/{NAME}_Model.md"
  task_path_vault  = "{bl_folder}/1_Task/Task.md"

SCHRITT 3: Existenz-Checks (Vault-First, Lokal-Fallback)
  model_exists = exists(model_path_vault)
  IF NOT model_exists:
    # Legacy-Fallback nur bei Vault-Miss
    model_exists = exists(".claude/models/{NAME}_Model.md")

  task_present = exists(task_path_vault) OR exists("{WORKING_DIR}/Task.md")
  pile_present = directory_listing(".claude/pileOfMud/").length > 0

SCHRITT 4: git_baseline ermitteln
  git_baseline = bash("git rev-parse HEAD").stdout.strip()
  IF git_baseline == "":
    Logge: "[A_MODUS] WARN git rev-parse fehlgeschlagen — baseline=null"
    git_baseline = null

SCHRITT 5: Decision-Tabelle (INV-MOD-1, INV-MOD-2)
  IF model_exists AND prev_status NOT IN [null, "IDLE", "ABORTED"]:
    modus = "resync"
    decision_reason = "Model existiert + a_status={prev_status} != IDLE -> resync"
  ELSE:
    modus = "fresh"
    decision_reason = "model_exists={model_exists}, a_status={prev_status} -> fresh"

SCHRITT 6: Output schreiben (INV-MOD-3 Schreib-Isolation)
  Edit({WORKING_DIR}/_manifest.md, A_PIPELINE_STATE.modus = modus)
  Edit({WORKING_DIR}/_manifest.md, A_PIPELINE_STATE.git_baseline = git_baseline)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.modusErkennung = {
    modus: modus,
    decision_reason: decision_reason,
    model_exists: model_exists,
    task_present: task_present,
    pile_present: pile_present,
    git_baseline: git_baseline,
    last_berater: "modusErkennung"
  })

SCHRITT 7: Exit
  Logge: "[A_MODUS] EXIT modus={modus} model_exists={model_exists}"
  EXIT 0
```

## INV-MOD-4 (NEU v0.2.0): W7-Konformitaet
Dieser Berater ist ein **Single-Worker** der sequentielle Reads + Bash-Calls
macht. Er spawnt KEINE Sub-Agents (W7-Constraint). Wenn der Orchestrator
Wellen-Pattern braucht, spawnt er mehrere Berater-Worker — nicht der Berater
selbst.

## Begruendung Modell-Tier

sonnet — kleine Tabelle, Existenz-Checks, ein git-call. Sonnet ausreichend.
