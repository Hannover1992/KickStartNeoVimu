---
status: active
version: 0.2.0
type: berater
parent: _A_orchestrate
phase: phase_4.4
model_tier: middle
created: 2026-04-25
updated: 2026-05-06
feature_anchor: BL-142
optional: false
changelog_0_2_0: |
  v0.2.0 (2026-05-06): Skelett -> produktiv.
    - Vault-First Model-Pfad mit Lokal-Fallback.
    - Frontmatter-Patch nur (Body unangetastet).
    - Drift-Hint bei previous_sha != head_sha.
contract:
  reads:
    - {file: "git", path: "rev-parse HEAD", purpose: "Aktueller HEAD-SHA"}
    - {file: "{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md", path: "Frontmatter Vault-First", purpose: "last_sync_commit Vorabwert (BL-151)"}
    - {file: ".claude/models/{NAME}_Model.md", path: "Frontmatter Lokal-Fallback", purpose: "Legacy"}
  writes:
    - {file: "{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md", path: "Frontmatter.last_sync_commit", purpose: "Commit-Anchor (Vault-First)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.gitTracking", purpose: "Schema (s.u.)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser gitTracking)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.*"}
    - {file: "Model.md Body/Sections", path: "(nur Frontmatter-Patch)"}
  calls: []
---

# _A_berater_gitTracking (Phase 4.4 in _A_orchestrate)

> **Zweck:** HEAD-SHA als last_sync_commit ins Model-Frontmatter schreiben — Drift-Detection-Anchor. Vor Routing.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_gitTracking                                     |
+======================================================================+
|  LIEST:                                                              |
|    git rev-parse HEAD                                                |
|    .claude/models/{NAME}_Model.md                                    |
|      Frontmatter.last_sync_commit (Vorabwert)                        |
|                                                                      |
|  SCHREIBT:                                                           |
|    .claude/models/{NAME}_Model.md                                    |
|      Frontmatter.last_sync_commit = "{HEAD-SHA}"                     |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      BERATER_OUTPUTS.gitTracking = {                                 |
|        head_sha, previous_sha, frontmatter_updated                   |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser gitTracking)                            |
|    A_PIPELINE_STATE.*                                                |
|    Model-Body (nur Frontmatter-Patch)                                |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 4.4 (vor Routing!)                      |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: Ein git-Call + ein Frontmatter-Patch.               |
|    Sonnet ausreichend.                                              |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-GT-1: HEAD-SHA voll (40 Zeichen), nicht gekuerzt              |
|    INV-GT-2: Nur Frontmatter beschreiben, nie Body                  |
|    INV-GT-3: Schreib-Isolation auf BERATER_OUTPUTS.gitTracking       |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - Model existiert (sonst Skip mit Warning)                        |
|    - git ist verfuegbar                                              |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - Model-Frontmatter.last_sync_commit auf HEAD                     |
|    - BERATER_OUTPUTS.gitTracking vollstaendig                        |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_A_berater_gitTracking, args="{NAME}")

Parameter:
  {NAME} - Feature-Name

Ausgabe:
  - Model-Frontmatter.last_sync_commit aktualisiert
  - BERATER_OUTPUTS.gitTracking
  - Exitcode: 0=OK, 1=PARTIAL (Model fehlt → Skip), 2=FAIL

Logging-Format:
  [A_GIT] ENTRY name={NAME}
  [A_GIT] EXIT duration={ms}ms head={sha} updated={bool}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  gitTracking:
    head_sha: "abc1234567890..."
    previous_sha: "fed9876543210..."
    frontmatter_updated: true
    last_berater: "gitTracking"
```

## Logik (v0.2.0 produktiv)

```
SCHRITT 0: Entry + Pfad-Resolution
  NAME = args[0]
  Logge: "[A_GIT] ENTRY name={NAME}"
  bl_folder = subprocess(".claude/scripts/resolve_bl_path.py", BL_ID).stdout.strip()

  model_path = "{bl_folder}/2_Model/{NAME}_Model.md"
  IF NOT exists(model_path):
    model_path = ".claude/models/{NAME}_Model.md"   # Legacy-Fallback
  IF NOT exists(model_path):
    Logge: "[A_GIT] PARTIAL — Model nicht vorhanden, skip Frontmatter-Patch"
    Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.gitTracking = {
      head_sha: null, previous_sha: null, frontmatter_updated: false,
      skipped: true, skip_reason: "model_not_found", last_berater: "gitTracking"
    })
    EXIT 1   # PARTIAL

SCHRITT 1: HEAD-SHA ermitteln (INV-GT-1: voll, nicht gekuerzt)
  head_sha = bash("git rev-parse HEAD").stdout.strip()
  IF head_sha == "" OR len(head_sha) < 40:
    Logge: "[A_GIT] FAIL — git rev-parse HEAD fehlgeschlagen oder gekuerzt"
    EXIT 2

SCHRITT 2: Vorab-SHA aus Model-Frontmatter
  model_content = Read(model_path)
  fm = parse_frontmatter(model_content)
  previous_sha = fm.last_sync_commit ?? null

  drift_detected = (previous_sha != null) AND (previous_sha != head_sha)
  IF drift_detected:
    Logge: "[A_GIT] DRIFT — previous={previous_sha[:8]} vs HEAD={head_sha[:8]}"

SCHRITT 3: Frontmatter-Patch (INV-GT-2: nur Frontmatter, nie Body)
  new_content = patch_frontmatter_field(model_content, "last_sync_commit", head_sha)
  Write(model_path, new_content)
  frontmatter_updated = true

SCHRITT 4: Output (INV-GT-3 Schreib-Isolation)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.gitTracking = {
    head_sha: head_sha,
    previous_sha: previous_sha,
    frontmatter_updated: frontmatter_updated,
    drift_detected: drift_detected,
    model_path: model_path,
    last_berater: "gitTracking"
  })

SCHRITT 5: Exit
  Logge: "[A_GIT] EXIT head={head_sha[:8]} updated={frontmatter_updated}"
  EXIT 0
```

## Begruendung Modell-Tier

sonnet — minimaler git-Call + Frontmatter-Patch. Kein Reasoning.
