---
status: active
version: 2.0.0
created: 2026-04-26
updated: 2026-05-15
op: ResearchCycle
phase: 1
type: berater
chain_position: middle
model_tier: middle
bl_patch: BL-165
bl_item: PL-11-01
---

# /_SC_berater_teamSetup (Phase 1 — SC-Zyklus Team-Setup)

> **BL-165 AK-11 (2026-05-15):** Team-Registrierung auf `sc-{batch_id}` umgestellt.
> Vault-Pfade via vault-routing.json resolved. sc_resume_from-Marker gelesen.
> Analog `_I_berater_teamSetup` und `_IDF_berater_teamSetup`.

## VERTRAG

**LIEST:**
- `.claude/analysis/_manifest.md`
  → active_team (Reaktivierung wenn match)
  → DF_BATCH_STATE.current_sub_batch_id (batch_id fuer Team-Name)
  → DF_BATCH_STATE.sc_resume_from (Re-Entry-Marker, INV-MODUS-9 BL-165)
  → SC_PIPELINE_STATE (Resume-Erkennung)
- `.claude/config/vault-routing.json`
  → vaults.{detected_vault}.windows_path, detection.rules[matched].backlog.subfolder
- `.claude/_session_params.md` → ceiling, floor, GLOBAL_HIL, dark_factory_max_cycles_override
- `$ARGUMENTS.mode` / `_session_params.mode`

**SCHREIBT:**
- `.claude/analysis/_manifest.md` → active_team = "sc-{batch_id}" (BL-165 PL-11-01)
- `.claude/analysis/_manifest.md` → SC_PIPELINE_STATE (modus, phase, mock_report)
- `{WORKING_DIR}/output/SC_DryRun_{NAME}_{Datum}.md` (nur bei dryRun)

**OUTPUT:** `BERATER_OUTPUTS.teamSetup.{team_name, team_action, batch_id, vault_root, bl_folder, sc_resume_from, sc_mode, sdf_guard_active, sdf_mode_normalized, startpunkt, flags, puppet_master_active, exit_code}`

**PFLICHT-LOGGING:**
```
[SC_TS] vault_root={path}
[SC_TS] bl_folder={path}
[SC_TS] manifest=.claude/analysis/_manifest.md
[SC_TS] batch_id={id}
[SC_TS] team_action={created|reactivated} team_name={name}
[SC_TS] sc_resume_from={ergebnis|observe|null}
[SC_TS] ceiling={tier} floor={tier}
```

**CROSS-REFERENCES:**
- Modus-Matrix: Phase 2 KURZLEBIG_PROMPT konsumiert sc_mode + flags
- Phase 3 STEUERUNG liest SC_PIPELINE_STATE.sc_mode fuer Zyklus-Steuerung
- SDF C3 setzt DF_BATCH_STATE.modus (BL-142) — SC liest, schreibt nie
- Phase 4 QualityGate: gate6_forced / gate6_skip Flags beeinflussen Gate-6-Logik
- SDF Phase 4 loopDecision schreibt sc_resume_from — teamSetup liest es hier (INV-MODUS-9)

---

## PHASE 1: TEAM SETUP

### Schritt 0.9: Batch-ID, Team-Name und Vault-Pfad-Resolution (BL-165 PL-11-01, ZUERST)

```
# batch_id aus DF_BATCH_STATE.current_sub_batch_id (INV-SC-TS-5)
batch_id = lies DF_BATCH_STATE.current_sub_batch_id aus .claude/analysis/_manifest.md ?? null
IF batch_id == null:
  batch_id = $ARGUMENTS.batch_id ?? "default"
  Logge WARNUNG: "[SC_TS] DF_BATCH_STATE.current_sub_batch_id fehlt — Fallback: {batch_id}"

team_name = "sc-{batch_id}"
Logge: "[SC_TS] batch_id={batch_id} team_name={team_name}"

# Vault-Pfad (INV-SC-TS-4 — NIE hardcoded)
lies .claude/config/vault-routing.json
vault_root = vaults.{detected_vault}.windows_path
bl_folder  = vault_root + "/" + detection.rules[matched].backlog.subfolder + "/" + BL_ID
Logge: "[SC_TS] vault_root={vault_root}"
Logge: "[SC_TS] bl_folder={bl_folder}"
Logge: "[SC_TS] manifest=.claude/analysis/_manifest.md"

# Team erstellen oder reaktivieren
active_team = lies active_team aus _manifest.md ?? null
IF active_team == team_name:
  team_action = "reactivated"
  Logge: "[SC_TS] team_action=reactivated team_name={team_name}"
ELSE:
  TeamCreate: team_name="{team_name}"
  IF TeamCreate schlaegt fehl → STOPP exit_code=2 "[SC_TS] TeamCreate fehlgeschlagen — ABORT"
  team_action = "created"
  Logge: "[SC_TS] team_action=created team_name={team_name}"
Schreibe _manifest.md → active_team = team_name

# Re-Entry-Marker lesen (INV-MODUS-9 BL-165)
sc_resume_from = lies DF_BATCH_STATE.sc_resume_from aus _manifest.md ?? null
Logge: "[SC_TS] sc_resume_from={sc_resume_from}"

# Session-Parameter
ceiling = _session_params.ceiling ?? "sonnet"
floor   = _session_params.floor   ?? "haiku"
puppet_master_active = (_session_params.GLOBAL_HIL == "off")
Logge: "[SC_TS] ceiling={ceiling} floor={floor} puppet_master_active={puppet_master_active}"

BERATER_OUTPUTS.teamSetup.team_name            = team_name
BERATER_OUTPUTS.teamSetup.team_action          = team_action
BERATER_OUTPUTS.teamSetup.batch_id             = batch_id
BERATER_OUTPUTS.teamSetup.vault_root           = vault_root
BERATER_OUTPUTS.teamSetup.bl_folder            = bl_folder
BERATER_OUTPUTS.teamSetup.sc_resume_from       = sc_resume_from
BERATER_OUTPUTS.teamSetup.puppet_master_active = puppet_master_active
BERATER_OUTPUTS.teamSetup.exit_code            = 0
```

### Schritt 0.95: HARD GATE — Team + Vault vor Phase 1 (BL-165)

```
BEVOR du irgendeinen Worker spawnst:
[ ] Team "{team_name}" erstellt oder reaktiviert (Schritt 0.9)
[ ] vault_root + bl_folder resolved (Schritt 0.9)
[ ] sc_resume_from gelesen (Schritt 0.9)
ALLE 3 muessen TRUE sein. Sonst STOPP.
```

### Schritt 1.0: Dry-Run Short-Circuit (BL-090, Universal_Dry_Run_Pattern)

```
# BL-090: SC-Pipeline Dry-Run-Modus (5. Child des Universal_Dry_Run_Pattern)
# Vorgaenger: BL-082 BDF, BL-087 SDF, BL-088 IDF, BL-089 A-Pipeline
# Zweck: Wenn sc_mode == "dryRun", skip SC-Zyklus (Observe/Hypothese/Ergebnis/QualityGate)
sc_mode = $ARGUMENTS.mode ?? _session_params.mode ?? "normal"

IF sc_mode == "dryRun":
  Logge: "[BL-090 SC DRY-RUN] Mock-Modus aktiviert — Phase 1-4 short-circuited"

  sc_dry_run_report = {
    date: {Datum},
    feature: NAME,
    mode: "dryRun",
    would_run: [
      "Phase 1 Team Setup (Team Lead Init)",
      "Phase 3 SC-Zyklus: /_SC_observe → /_SC_hypothese → /_SC_ergebnis → /_SC_qualityGate",
      "SC-INLINE oder SC-FULL (Cycles bis SRS < Threshold)",
      "Optional: /_SC_modelMaintain, /_SC_implement"
    ],
    skipped: true,
    note: "Fuer echten SC-Zyklus: mode=normal (oder weglassen)"
  }

  sc_dry_run_report_path = "{WORKING_DIR}/output/SC_DryRun_{NAME}_{Datum}.md"
  Schreibe {sc_dry_run_report_path} mit Frontmatter type=sc_dry_run_report + sc_dry_run_report Inhalt

  Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE:
    name: NAME
    modus: dryRun
    phase: DRY_RUN_DONE
    mock_report: {sc_dry_run_report_path}

  Logge: "[BL-090 SC DRY-RUN] Mock-Completion — Report: {sc_dry_run_report_path}"
  → Return zu Aufrufer
```

### Schritt 1.1: Kontext laden + Modus-Erkennung

Lies (falls vorhanden):
1a. `{VAULT}/_manifest.md` → NAME (global)
1b. `{WORKING_DIR}/_manifest.md` → SC_PIPELINE_STATE (aktueller Stand, Phase) — per-Story (BL-155 AK-1)
2. `{VAULT}/Task.md` → Aufgabendefinition
3. Model (PRIMAER Vault, FALLBACK lokal) → existierendes Model
   # PRIMAER: Vault (BL-065)
   `{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md`
   # FALLBACK: lokal (Legacy)
   # fallback-read: expected vault, using .claude/
   ODER `.claude/models/{NAME}_Model.md`
4. `.claude/pileOfMud/` → Rohmaterial?

Bestimme Startpunkt:
- Kein Manifest, kein Task.md → Voller Zyklus ab W_fetch
- Task.md vorhanden, kein Model → Ab /_model
- Model vorhanden → Ab /_SC_observe (Zyklus direkt)

**SDF→SC Guard (BL-142 Caller-Migration, ersetzt frueheren A→SC Guard):**

```
# BL-142 Migration (2026-04-26):
# A schreibt KEINE recommendation mehr (INV-A-RAW-DATA — A liefert nur aggregat_*).
# Mode-Decision wandert vollstaendig zu SDF C3, der DF_BATCH_STATE.modus setzt.
# Falls SC im Symbiose-Pfad gerufen wird (M4/M5/M6 von SDF dispatched), liest SC
# den Mode aus DF_BATCH_STATE.modus. Direkter Aufruf ohne SDF-Kontext SKIP-t den
# Guard und nimmt --mode-Flag oder Default FULL.

# Graceful Degradation: Falls DF_BATCH_STATE oder .modus fehlt → SKIP
IF Manifest.DF_BATCH_STATE existiert UND Manifest.DF_BATCH_STATE.modus existiert:
  sdf_mode_raw = Manifest.DF_BATCH_STATE.modus    # z.B. "M4" | "M5" | "M6"
  # Normierung: SDF M-Codes → SC-Modi
  sdf_mode_normalized = SWITCH sdf_mode_raw:
    "M4"  → "INLINE"          # SC-Inline (kleine ICs)
    "M5"  → "FULL"            # SC-Symbiose mit I-Pipeline
    "M6"  → "ANALYSE"         # SC reine Analyse, kein Code
    SONST → null              # M1/M2/M3/M7/M8/M9 = nicht-SC, sollte SC nicht erreichen
  IF sdf_mode_normalized == null:
    Logge: "[SDF-GUARD] Mode {sdf_mode_raw} ist kein SC-Mode — SKIP Guard (vermutlich Direct-Call)"
    sdf_guard_active = false
  ELSE:
    sdf_guard_active = true
    Logge: "[SDF-GUARD] DF_BATCH_STATE.modus={sdf_mode_raw} → SC-Mode: {sdf_mode_normalized}"
ELSE:
  Logge: "[SDF-GUARD] Kein DF_BATCH_STATE.modus gefunden — SKIP Guard (Direct-Call ohne SDF)"
  sdf_guard_active = false

# Backwards-Compatibility: A_PIPELINE_STATE.recommendation wird NICHT mehr gelesen.
# Frueher (vor BL-142) gab es einen A→SC-Guard. Ab BL-142 ist A mode-frei.
# Falls altes Manifest noch recommendation enthaelt: ignorieren, SDF C3 ist Quelle.
```

**Modus-Erkennung:**

```
# (Z4: RF-12) Inkompatibilitaets-Check (9 Paare → ABBRUCH bei Verletzung, VOR TeamCreate):
# Bestehend:
#   -I + --mode=review → ABBRUCH "INKOMPATIBEL: -I und --mode=review gleichzeitig"
#   -I + --mode=analyse → ABBRUCH "INKOMPATIBEL: -I und --mode=analyse gleichzeitig"
#   --mode=review + --mode=analyse → ABBRUCH "INKOMPATIBEL: --mode=review und --mode=analyse gleichzeitig"
# Neu (Z4: RF-12, W254):
#   -I + --symbiose → ABBRUCH "INKOMPATIBEL: -I und --symbiose gleichzeitig"
#   -I + --full-symbiose → ABBRUCH "INKOMPATIBEL: -I und --full-symbiose gleichzeitig"
#   --symbiose + --full-symbiose → ABBRUCH "INKOMPATIBEL: --symbiose und --full-symbiose gleichzeitig"
#   --only-I + -I → ABBRUCH "INKOMPATIBEL: --only-I und -I gleichzeitig"
#   --only-I + --symbiose → ABBRUCH "INKOMPATIBEL: --only-I und --symbiose gleichzeitig"
#   --only-I + --full-symbiose → ABBRUCH "INKOMPATIBEL: --only-I und --full-symbiose gleichzeitig"

WENN --mode=analyse:
  → SC_PIPELINE_STATE.sc_mode: ANALYSE
  → Implement-Step: SKIP
  → Lies {META}/sc/decision-tables.md fuer ANALYSE-spezifische Decision Table

WENN --mode=review:
  → SC_PIPELINE_STATE.sc_mode: REVIEW
  → Pruefe: I-Pipeline-Ergebnis existiert? (WARNUNG wenn NEIN)
  → Erstelle post-impl/ Verzeichnis
  → Lies {META}/sc/review-modus.md fuer Details

WENN -I:
  → SC_PIPELINE_STATE.sc_mode: INLINE
  → Implement-Step: /_SC_implement

# (Z4: RF-34, W253) Neue Zweige:
WENN --only-I:
  → SC_PIPELINE_STATE.sc_mode: I_STANDALONE
  → sc_mode = "ONLY_I"
  → Manifest: pipeline_mode = POST_CYCLE
  → SC_I_LIFECYCLE.transition_log APPEND: {from: SC, to: POST_CYCLE, reason: "--only-I Flag"}
  → Kein SC-Zyklus. Direkt: Spawne /_I_orchestrate {NAME} (scope_mode=full, I-STANDALONE)
  → STOPP (kein weiterer SC-Zyklus)

WENN --symbiose:
  → SC_PIPELINE_STATE.sc_mode: FULL
  → sc_mode = "FULL"
  → gate6_forced = true  # Gate 6 auch in Zyklus 1 erzwungen
  → Implement-Step: /_I_orchestrate (SYMBIOSE-Protokoll)
  → LOG: "Modus: FULL SYMBIOSE (--symbiose, Gate 6 erzwungen)"

WENN --full-symbiose:
  → SC_PIPELINE_STATE.sc_mode: FULL
  → sc_mode = "FULL"
  → gate6_skip = true  # Gate 6 wird nicht ausgefuehrt
  → Implement-Step: /_I_orchestrate (SYMBIOSE-Protokoll, scope_mode=full (BL-054))
  → LOG: "Modus: FULL SYMBIOSE (--full-symbiose, Gate 6 SKIP)"

SONST:
  → SC_PIPELINE_STATE.sc_mode: FULL (Default)
  → Implement-Step: /_I_orchestrate (SYMBIOSE-Protokoll)
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

activity = "_sc_berater_teamsetup"  # oder die konkrete SC-Aktivitaet dieses Zyklus
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

## INVARIANTEN

- INV-DRYRUN: dryRun short-circuits VOR jeder anderen Logik
- INV-SDF-READ-ONLY: SC liest DF_BATCH_STATE.modus, schreibt ihn nie
- INV-INCOMPAT-BEFORE-TEAM: 9 Inkompatibilitaets-Paare werden VOR TeamCreate geprueft (ABBRUCH)
- INV-ONLY-I-STOPP: --only-I → kein SC-Zyklus, direkter Sprung zu /_I_orchestrate
- INV-FALLBACK-LOG: Vault-FALLBACK auf lokal muss geloggt werden ("fallback-read: expected vault, using .claude/")
- INV-BACKWARDS-COMPAT: A_PIPELINE_STATE.recommendation wird ignoriert (BL-142)
