---
status: active
version: 1.0.0
created: 2026-05-04
op: IntermediateFactory
phase: 0.5
type: berater
parent: _IDF_orchestrate
chain_position: middle
model_tier: middle
feature_anchor: BL-151
---

# /_IDF_berater_teamSetup (Phase 0.5 — Team-Setup fuer IDF-Pipeline)

> **Zweck:** Analog zu `_I_berater_teamSetup`. Erste Phase nach Stufe 1 Cleanup.
> Setzt Team korrekt auf, resolved Vault-Pfade, populiert IDF_PIPELINE_STATE.
> WICHTIG: Phase 0.5 ist VOR Phase 0 ResumeGuard — der Guard braucht das Team.

[VERTRAG]
LIEST:
  - .claude/config/vault-routing.json (FESTER PFAD!)
    → vaults.{detected_vault}.windows_path
    → detection.rules[matched].backlog.subfolder
    → ticket_prefix_map (BL/DCSRE → vault)
  - .claude/analysis/_manifest.md
    → active_team (zur Reaktivierung wenn match)
    → IDF_PIPELINE_STATE.idf_status (zur Resume-Erkennung)
    → BL_LIFECYCLE_STATE
  - .claude/_session_params.md
    → ceiling, floor, GLOBAL_HIL, GLOBAL_DIFFICULTY
    → enforceProcess, dark_factory_max_cycles_override

SCHREIBT:
  - .claude/analysis/_manifest.md
    → active_team (TeamCreate ODER Reaktivierung)
    → BERATER_OUTPUTS.teamSetup (Schema unten)
    → IDF_PIPELINE_STATE.bl_id, bl_slug, ceiling, floor (init)

BERATER_OUTPUTS.teamSetup:
  team_name:           string ("idf-{BL_ID}")
  team_action:         "created" | "reactivated"
  vault_root:          string (resolved windows_path)
  bl_folder:           string (resolved Vault-BL-Pfad)
  manifest_path:       string (.claude/analysis/_manifest.md)
  pl_files:            list[string] (alle 6_PL/*.md)
  routing_rule:        string (welche detection.rule matched)
  ticket_prefix:       string (BL oder DCSRE)
  worker_tier_ceiling: string (von _session_params)
  worker_tier_floor:   string
  exit_code:           0 (OK) | 1 (WARN) | 2 (ABORT)

PFLICHT-LOGGING (Worker im Terminal):
  [IDF_TS] vault_root={path}
  [IDF_TS] bl_folder={path}
  [IDF_TS] manifest={path}
  [IDF_TS] pl_files={N} files in 6_PL/
  [IDF_TS] team_action={created|reactivated} team_name={name}
  [IDF_TS] routing_rule={pattern_matched}
  [IDF_TS] ceiling={tier} floor={tier}

CROSS-REFERENCES:
  - Phase 0 ResumeGuard konsumiert BERATER_OUTPUTS.teamSetup (vault paths!)
  - Phase 1+2+3.x Worker bekommen paths via SPAWN-CONVENTION (orchestrate)
[/VERTRAG]

[INVARIANTEN]
- INV-TS-1: KEIN Worker wird gespawnt bevor teamSetup DONE ist
- INV-TS-2: TeamCreate schlaegt fehl → exit_code=2 ABORT (kein Workaround)
- INV-TS-3: Wenn active_team == idf-{BL_ID}: REAKTIVIEREN (kein TeamCreate-Konflikt)
- INV-TS-4: Vault-Pfad-Resolution MUSS via vault-routing.json laufen, NIE hardcoded
- INV-TS-5: pl_files MUSS ALLE *.md im 6_PL/ enthalten (nicht nur {bl_id}-parking-lot.md)
[/INVARIANTEN]

---

## PHASE 0.5: TEAM SETUP

### 0.5.1 Vault-Pfad-Resolution (KRITISCH, ZUERST)

```
# FESTE PFADE (NIE hardcoded ohne diese Konstanten):
VAULT_ROUTING_PATH = ".claude/config/vault-routing.json"
LOCAL_MANIFEST_PATH = ".claude/analysis/_manifest.md"
SESSION_PARAMS_PATH = ".claude/_session_params.md"

# Read routing
routing = Read(VAULT_ROUTING_PATH)

# Detect via cwd pattern + ticket_prefix_map
cwd = subprocess("pwd").stdout.strip()
ticket_prefix = BL_ID.split("-")[0]   # "BL" oder "DCSRE"

# Erste Stufe: ticket_prefix_map (NEU BL-151)
if ticket_prefix in routing.ticket_prefix_map:
  vault_name = routing.ticket_prefix_map[ticket_prefix]
else:
  # Fallback: detection.rules nach cwd-Pattern
  for rule in routing.detection.rules:
    if pattern_matches(cwd, rule.pattern):
      vault_name = rule.vault
      matched_rule = rule
      break

vault_root = routing.vaults[vault_name].windows_path

# Backlog-Subfolder + Folder-Naming
matched_rule = find_rule_for_pattern(routing, cwd_or_prefix)
subfolder = matched_rule.backlog.subfolder    # "DCSRE/Backlog"
folder_name = format_folder(matched_rule.backlog.dateiname_convention,
                             BL_ID, BL_SLUG)
# z.B. "DCSRE-94-qdvs-selbstauskunft-bearbeiten-analyse"

bl_folder = f"{vault_root}/{subfolder}/{folder_name}"

# Pflicht-Logging
Logge: "[IDF_TS] vault_root={vault_root}"
Logge: "[IDF_TS] bl_folder={bl_folder}"
Logge: "[IDF_TS] manifest={LOCAL_MANIFEST_PATH}"

# Vault-BL-Folder MUSS existieren (oder neu anlegen wenn fresh)
if NOT exists(bl_folder):
  if BL_LIFECYCLE_STATE.first_run:
    create_dir_structure(bl_folder)  # 1_Task, 2_Model, 3_Spec, 4_K-Score, 5_Gap, 6_PL
  else:
    exit_code = 2
    Logge: "[IDF_TS] FATAL: bl_folder nicht da, kein first_run → ABORT"
    return

# PL-Files Liste (KRITISCH fuer Phase 3.2 plAggregation)
pl_files = list(f"{bl_folder}/6_PL/*.md")
Logge: f"[IDF_TS] pl_files={len(pl_files)} files in 6_PL/"
for f in pl_files:
  Logge: f"  - {basename(f)}"
```

### 0.5.2 Team-Create ODER Reaktivierung (RESUME-AWARE)

```
manifest = Read(LOCAL_MANIFEST_PATH)
active_team = manifest.get("active_team", {}).get("name")

target_team = f"idf-{BL_ID}"

IF active_team == target_team:
  # Resume-Lauf: Team existiert schon, NICHT TeamCreate
  team_action = "reactivated"
  Logge: f"[IDF_TS] Team REAKTIVIERT (Resume): {target_team}"
ELSE IF active_team is not None AND active_team != target_team:
  # Anderes Team aktiv → Stufe 1 sollte das schon gecleant haben
  # Wenn nicht: harter Abbruch
  exit_code = 2
  Logge: f"[IDF_TS] FATAL: active_team={active_team} != {target_team}, Stufe 1 Cleanup hat versagt"
  return
ELSE:
  # Frischer Lauf
  TeamCreate team_id=target_team purpose="IDF fuer {BL_ID}"
  Set manifest.active_team = {
    name: target_team,
    wellen_tracking_enabled: false,
    created: ISO_NOW()
  }
  team_action = "created"
  Logge: f"[IDF_TS] Team CREATED: {target_team}"
```

### 0.5.3 Tier-Resolution

```
session = Read(SESSION_PARAMS_PATH)
ceiling = session.GLOBAL_CEILING ?? "sonnet"
floor   = session.GLOBAL_FLOOR ?? "haiku"

Logge: f"[IDF_TS] ceiling={ceiling} floor={floor}"
```

### 0.5.4 BERATER_OUTPUTS schreiben

```
Schreibe in LOCAL_MANIFEST_PATH:
  BERATER_OUTPUTS.teamSetup = {
    team_name: target_team,
    team_action: team_action,
    vault_root: vault_root,
    bl_folder: bl_folder,
    manifest_path: LOCAL_MANIFEST_PATH,
    pl_files: pl_files,
    routing_rule: matched_rule.pattern,
    ticket_prefix: ticket_prefix,
    worker_tier_ceiling: ceiling,
    worker_tier_floor: floor,
    exit_code: 0
  }

Logge: "[IDF_TS] EXIT exit_code=0 status=OK"
return
```

---

## zone_advisory Wiring (BL-330 AK-3)

> **advisory_only — NIEMALS bindend.** Der Berater emittiert einen Vorschlag, kein Kommando.
> Analog INV-MODUS-1: der Lead / Param-Owner entscheidet, nicht der Berater.

```
# BL-330 AK-3: zone_advisory-Emission (advisory_only=True, NICHT bindend)
# Zweck: Lead bekommt einen strukturierten Vehicle-Hinweis direkt aus der ZONE_REGISTRY,
# ohne dass der Berater den Vehicle-Entscheid vorwegnimmt.

from workflow_zones import zone_advisory  # .claude/scripts/workflow_zones.py

activity = "_idf_berater_sequenceplanner"  # oder die konkrete IDF-Aktivitaet dieses Laufs
mode = _session_params.workflow ?? "false"  # session_params_resolver Dial

advisory = zone_advisory(activity, mode=mode)
# advisory["advisory_only"] ist IMMER True (BL-330 AK-3 Invariante)
# advisory["motor_faehig"]  ist True NUR wenn recommended_vehicle=="workflow"

BERATER_OUTPUTS.teamSetup.zone_advisory = advisory
# Lead integriert in vehicle-Entscheidung — advisory_only=True, NICHT Auto-Routing.
Logge: "[BL-330] zone_advisory: zone={advisory['zone']} motor_faehig={advisory['motor_faehig']} advisory_only={advisory['advisory_only']}"
```

**Wichtig:** `advisory_only` ist strukturell `True` — der Berater empfiehlt, der Lead entscheidet
(INV-VEHIKEL-1: Vehicle-Entscheidung via `workflow_zones.py vehicle`-CLI durch den Lead).
Kein Auto-Routing aus dem Advisory heraus.

## ABHAENGIGKEITEN

- **BL-151** (in progress): Vault-Driven Development — diese Berater-Datei ist Teil der
  Architektur-Klaerung (Resolver-Chaos-Aufloesung).
- **vault-routing.json** muss `ticket_prefix_map` haben (BL-151 NEU-K3).
- **vault-routing.json** muss `detection.rules[].backlog` haben (mit subfolder + dateiname_convention).

## FOLGE-TASKS

- Spaeter: Berater-Skill-Datei umziehen nach `.claude/skills/_IDF_berater_teamSetup/SKILL.md`
  (Skill-Plugin-Architektur).
- Phase 0.5 sollte auch fuer SDF und BDF analog existieren (`_SDF_berater_teamSetup`,
  `_BDF_berater_teamSetup`) — aktuell machen die das inline.
