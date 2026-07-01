---
status: active
version: 0.2.0
type: berater
parent: _A_orchestrate
phase: phase_4.3
model_tier: middle
created: 2026-04-25
updated: 2026-05-06
feature_anchor: BL-142
optional: false
changelog_0_2_0: |
  v0.2.0 (2026-05-06): Skelett -> produktiv.
    - Pattern B Rollover bei 50KB-Schwelle.
    - YAML-Snapshot mit ISO-Datum-Header.
    - Vault-First Protokoll-Pfad (mit Lokal-Fallback).
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE", purpose: "Komplettstand vor Persistierung"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.*", purpose: "Berater-Sub-Felder"}
    - {file: "_manifest_protokoll.md", path: "Top-Section (Pattern B Rollover)", purpose: "Rotation-Schwelle"}
  writes:
    - {file: "_manifest_protokoll.md", path: "Append + ggf Rollover", purpose: "State-Snapshot persistieren"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.last_state_snapshot_at", purpose: "Snapshot-Zeitstempel"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.stateMaintain", purpose: "Schema (s.u.)"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser stateMaintain)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.routing_target / modus / derived_name"}
  calls: []
---

# _A_berater_stateMaintain (Phase 4.3 in _A_orchestrate)

> **Zweck:** Snapshot des A_PIPELINE_STATE in _manifest_protokoll.md, vor Routing.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _A_berater_stateMaintain                                   |
+======================================================================+
|  LIEST:                                                              |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      A_PIPELINE_STATE (kompletter Block)                             |
|      BERATER_OUTPUTS.* (alle Sub-Felder)                             |
|    _manifest_protokoll.md                                            |
|      Top-Section (Pattern B Rollover-Schwelle)                       |
|                                                                      |
|  SCHREIBT:                                                           |
|    _manifest_protokoll.md                                            |
|      Append-Block mit Snapshot                                       |
|      ggf Rollover (alte Eintraege archivieren)                       |
|    {WORKING_DIR}/_manifest.md                                                      |
|      A_PIPELINE_STATE.last_state_snapshot_at = "{ISO-Datum}"         |
|      BERATER_OUTPUTS.stateMaintain = {                               |
|        snapshot_lines, rollover_done                                 |
|      }                                                               |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser stateMaintain)                          |
|    A_PIPELINE_STATE.routing_target / modus / derived_name            |
|                                                                      |
|  ACTOR: _A_orchestrate Phase 4.3 (vor Routing!)                      |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: File-Append + Rollover-Threshold-Check.             |
|    Format-Treue wichtig — Sonnet ausreichend.                       |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-SM-1: Pattern B Rollover bei Schwelle (z.B. >5000 LOC)        |
|    INV-SM-2: ISO-Datum im Snapshot-Header                            |
|    INV-SM-3: Schreib-Isolation auf BERATER_OUTPUTS.stateMaintain     |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - aggregat_*-Felder gesetzt (Phase 4.2a done)                     |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - _manifest_protokoll.md enthaelt aktuellen Snapshot              |
|    - last_state_snapshot_at gesetzt                                  |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_A_berater_stateMaintain, args="{NAME}")

Parameter:
  {NAME} - Feature-Name

Ausgabe:
  - _manifest_protokoll.md mit Snapshot
  - A_PIPELINE_STATE.last_state_snapshot_at
  - BERATER_OUTPUTS.stateMaintain
  - Exitcode: 0=OK, 2=FAIL

Logging-Format:
  [A_STATE] ENTRY name={NAME}
  [A_STATE] EXIT duration={ms}ms snapshot_lines={n} rollover={bool}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  stateMaintain:
    snapshot_lines: 84
    rollover_done: false
    last_berater: "stateMaintain"
```

## Logik (v0.2.0 produktiv)

```
SCHRITT 0: Entry + Pfad-Resolution
  NAME = args[0]
  Logge: "[A_STATE] ENTRY name={NAME}"
  bl_folder = subprocess(".claude/scripts/resolve_bl_path.py", BL_ID).stdout.strip()

  # Protokoll-Pfad: Vault-First, Lokal-Fallback
  protokoll_path = "{VAULT}/_manifest_protokoll.md"
  IF NOT exists(parent_dir(protokoll_path)):
    protokoll_path = ".claude/analysis/_manifest_protokoll.md"

SCHRITT 1: A_PIPELINE_STATE + BERATER_OUTPUTS lesen
  manifest = Read({WORKING_DIR}/_manifest.md)
  state    = manifest.A_PIPELINE_STATE
  outputs  = manifest.BERATER_OUTPUTS ?? {}

SCHRITT 2: Snapshot serialisieren (YAML)
  ts = ISO_NOW()
  derived_name = state.derived_name ?? NAME
  snapshot_yaml = render_yaml({
    timestamp: ts,
    feature: derived_name,
    a_status: state.a_status,
    modus: state.modus,
    aggregat_reifegrad: state.aggregat_reifegrad,
    aggregat_k_score: state.aggregat_k_score,
    aggregat_gap: state.aggregat_gap,
    aggregat_aks_count: state.aggregat_aks_count,
    last_berater_outputs: outputs.keys()
  })
  snapshot_lines = count_lines(snapshot_yaml)

SCHRITT 3: Pattern B Rollover-Check (INV-SM-1)
  rollover_threshold_bytes = 50000
  rollover_done = false
  current_size = exists(protokoll_path) ? file_size(protokoll_path) : 0

  IF current_size > rollover_threshold_bytes:
    archive_path = "{protokoll_path}.archived_{ts.replace(':','-')}.md"
    bash("mv {protokoll_path} {archive_path}")
    rollover_done = true
    Logge: "[A_STATE] ROLLOVER size={current_size} -> {archive_path}"

SCHRITT 4: Snapshot prependen (INV-SM-2 ISO-Datum-Header)
  IF NOT exists(protokoll_path):
    Write(protokoll_path, "# Manifest-Protokoll\n\n")

  existing_content = Read(protokoll_path)
  new_block = "## A-Pipeline Snapshot {ts} - {derived_name}\n\n```yaml\n{snapshot_yaml}\n```\n\n"

  # Prepend (W18 Pattern: neuer Eintrag oben, alte Eintraege bleiben)
  header_end = find_header_end(existing_content)  # nach "# Manifest-Protokoll\n\n"
  new_content = existing_content[:header_end] + new_block + existing_content[header_end:]
  Write(protokoll_path, new_content)

SCHRITT 5: Output schreiben (INV-SM-3 Schreib-Isolation)
  Edit({WORKING_DIR}/_manifest.md, A_PIPELINE_STATE.last_state_snapshot_at = ts)
  Edit({WORKING_DIR}/_manifest.md, BERATER_OUTPUTS.stateMaintain = {
    snapshot_lines: snapshot_lines,
    rollover_done: rollover_done,
    protokoll_path: protokoll_path,
    last_berater: "stateMaintain"
  })

SCHRITT 6: Exit
  Logge: "[A_STATE] EXIT lines={snapshot_lines} rollover={rollover_done}"
  EXIT 0
```

## format_version-Stamping-Disziplin (BL-333, B1 — Manifest ist Langzeit-Artefakt)

> **Spiegel der Lane-A-Stamp-Logik** (`.claude/scripts/resolve_format_version.py`). Prosa-Konvention, kein Python-Manifest-Writer.

Das `_manifest.md` ist ein versioniertes Langzeit-Artefakt (Typ `manifest` in der Registry `.claude/config/format_versions.yaml`). Dieser Berater ist ein Manifest-Writer (SCHRITT 5) und MUSS daher die Stamp-Disziplin wahren:

- **Top-Level-Stamp (additiv):** Beim Schreiben des Manifests traegt das Frontmatter eine Top-Level-Zeile `format_version: {N}`. Der Wert `{N}` kommt AUSSCHLIESSLICH via Loader-Call `resolve_format_version("manifest")` (Writer=Follow, PT-GEN-LeadFollow) — **kein eigenes Versions-Literal hardcoden.**
- **Idempotent:** Ist `format_version:` bereits im Frontmatter vorhanden, wird KEIN Duplikat geschrieben (Re-Stamp == No-Op).
- **Dual-Read-Gen-0-Konvention:** Ein Manifest OHNE `format_version:`-Stempel gilt als **Generation-0** (`read_format_version` liefert 0) — NIE ein Crash (Case-Study 1944: 234KB-Manifest ohne Stempel). Liefert der Loader `None` (Registry nicht ladbar), wird der Stamp **weggelassen** statt zu brechen (Symmetrie zu G2e).
- **Rein additiv:** Bestehende Frontmatter-Felder werden NICHT umbenannt/re-formatiert. Der Stamp ist eine zusaetzliche Zeile, kein Re-Format.

## Begruendung Modell-Tier

sonnet — File-Append, Threshold-Check, YAML-Serialisierung. Kein Reasoning.
