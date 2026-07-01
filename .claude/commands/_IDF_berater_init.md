---
status: active
version: 0.2.0
type: berater
parent: _IDF_orchestrate
phase: phase_1
model_tier: middle
created: 2026-04-25
feature_anchor: BL-142
optional: false
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE (vorab)", purpose: "Resume-Erkennung"}
    - {file: "{VAULT}/Backlog/{bl_id}-{bl_slug}.md", path: "BL-Frontmatter", purpose: "bl_id/bl_slug ableiten"}
    - {file: "_session_params.md", path: "GLOBAL_*", purpose: "Modus + HiL"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.idf_status", purpose: "INIT|ITEM_LOOP|...|DONE"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.bl_id / bl_slug", purpose: "BL-Kontext"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.team_lead", purpose: "TeamCreate-Resultat"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.init", purpose: "Schema (s.u.)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser init)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_PIPELINE_STATE.*"}
  calls:
    - "TeamCreate (falls noch kein Team existiert)"
---

# _IDF_berater_init (Phase 1 in _IDF_orchestrate)

> **Zweck:** IDF-Pipeline initialisieren: Resume-Check, State-Setup, TeamCreate.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_init                                          |
+======================================================================+
|  LIEST:                                                              |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      IDF_PIPELINE_STATE (Vorabwerte fuer Resume)                     |
|    {VAULT}/Backlog/                                                  |
|      {bl_id}-{bl_slug}.md (Index-Knoten mit Frontmatter)             |
|    _session_params.md                                                |
|      GLOBAL_MODUS, GLOBAL_HIL                                        |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                                      |
|      IDF_PIPELINE_STATE.idf_status = "INIT"                          |
|      IDF_PIPELINE_STATE.bl_id                                        |
|      IDF_PIPELINE_STATE.bl_slug                                      |
|      IDF_PIPELINE_STATE.team_lead = "{team-handle}"                  |
|      BERATER_OUTPUTS.init = {                                        |
|        resumed, bl_id, bl_slug, team_created                         |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser init)                                   |
|    DF_PIPELINE_STATE.*                                               |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 1 (Resume + State + TeamCreate)       |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: State-Init + Frontmatter-Read + ein                  |
|    TeamCreate-Call. Kein Reasoning.                                 |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-INIT-1: idempotent — bei Resume kein neuer Team-Create       |
|    INV-INIT-2: bl_slug aus Vault-Pfad oder Frontmatter, nicht raten |
|    INV-INIT-3: Schreib-Isolation auf BERATER_OUTPUTS.init            |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - bl_id im Args oder im Manifest                                  |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - IDF_PIPELINE_STATE init (idf_status, bl_id, bl_slug, team_lead) |
|    - BERATER_OUTPUTS.init vollstaendig                               |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_init, args="{NAME}")

Parameter:
  {NAME} - BL-ID oder Feature-Name

Ausgabe:
  - IDF_PIPELINE_STATE init
  - BERATER_OUTPUTS.init
  - Exitcode: 0=OK, 1=RESUMED, 2=FAIL

Logging-Format:
  [IDF_INIT] ENTRY name={NAME}
  [IDF_INIT] EXIT duration={ms}ms resumed={bool} bl_id={id}
```

## Output-Schema

```yaml
IDF_PIPELINE_STATE:
  idf_status: "INIT"
  bl_id: "BL-142"
  bl_slug: "BL-142-foundation-skeletons"
  team_lead: "team-idf-2026-04-25"

BERATER_OUTPUTS:
  init:
    resumed: false
    bl_id: "BL-142"
    bl_slug: "BL-142-foundation-skeletons"
    team_created: true
    last_berater: "init"
```

## Logik

```
SCHRITT 0: Entry-Log + Args-Parse
  bl_id = args[0]                # z.B. "BL-142"
  Logge: "[IDF_INIT] ENTRY name={bl_id}"
  resumed = false
  team_created = false

SCHRITT 1: Resume-Check (Idempotenz INV-INIT-1)
  manifest = Read({WORKING_DIR}/_manifest.md)
  IF manifest.IDF_PIPELINE_STATE != null
     AND manifest.IDF_PIPELINE_STATE.idf_status NOT IN [null, "IDLE", "DONE"]:
    resumed = true
    bl_slug = manifest.IDF_PIPELINE_STATE.bl_slug
    team_lead = manifest.IDF_PIPELINE_STATE.team_lead
    Logge: "[IDF_INIT] RESUME idf_status={manifest.IDF_PIPELINE_STATE.idf_status}"
    -> SCHRITT 4

SCHRITT 2: bl_slug aufloesen (4-Stufen, INV-INIT-2 — nicht raten)
  # Stufe 1: aus BDF-State
  IF BDF_BATCH_STATE.bl_items != null:
    bl_item = BDF_BATCH_STATE.bl_items.find(i => i.id == bl_id)
    IF bl_item AND bl_item.vault_path:
      bl_slug = extract_slug(bl_item.vault_path)
      -> SCHRITT 3

  # Stufe 2: A_PIPELINE_STATE (vorheriger A-Lauf)
  IF manifest.A_PIPELINE_STATE.bl_slug:
    bl_slug = manifest.A_PIPELINE_STATE.bl_slug
    -> SCHRITT 3

  # Stufe 3: Glob-Fallback
  candidates = Glob("{VAULT}/Backlog/{bl_id}-*.md")
  IF |candidates| == 1:
    bl_slug = extract_filename_without_ext(candidates[0])
  ELIF |candidates| > 1:
    FAIL: "Mehrdeutige Vault-Items fuer {bl_id}: {candidates}"
  ELIF |candidates| == 0:
    # Stufe 4: bl_id selbst (direct-Modus)
    bl_slug = bl_id
    Logge: "[IDF_INIT] WARN bl_slug={bl_id} (direct-Modus, kein Vault-Item)"

SCHRITT 3: TeamCreate (fresh-Pfad)
  team_lead = TeamCreate(name="idf-{bl_id}", role="TeamLead")
  team_created = true

SCHRITT 4: State + Output schreiben
  Edit({WORKING_DIR}/_manifest.md, IDF_PIPELINE_STATE = {
    idf_status: resumed ? manifest.IDF_PIPELINE_STATE.idf_status : "INIT",
    bl_id: bl_id,
    bl_slug: bl_slug,
    team_lead: team_lead
  })
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.init = {
    resumed: resumed,
    bl_id: bl_id,
    bl_slug: bl_slug,
    team_created: team_created,
    last_berater: "init"
  })

SCHRITT 5: Exit
  exitcode = resumed ? 1 : 0
  Logge: "[IDF_INIT] EXIT duration={ms}ms resumed={resumed} bl_id={bl_id}"
  EXIT exitcode
```

## Begruendung Modell-Tier

sonnet — Init-Sequenz, Frontmatter-Parse, ein TeamCreate-Call. Kein Deep-Reasoning.
