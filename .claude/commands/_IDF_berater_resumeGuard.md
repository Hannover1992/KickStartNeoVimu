---
status: active
version: 0.3.0
type: berater
parent: _IDF_orchestrate
phase: phase_1
model_tier: middle
created: 2026-04-25
updated: 2026-05-24
feature_anchor: BL-142
optional: false
migrated_from: _SDF_berater_resumeGuard
bl_patches:
  - BL-198-AK5-PL1: "PL-Existenz-Pre-Check (6_PL/ leer → ABORT)"
  - BL-198-AK5-PL2: "ABORT-Meldung mit Routing-Hinweis zur A-Pipeline"
  - BL-198-AK5-PL3: "Inkonsistenz-Guard pl_pre_filled=true + PL leer"
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.idf_status / last_commit / batch_done", purpose: "Resume-Erkennung"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "GLOBAL_HIL / GLOBAL_MODUS", purpose: "K5-Fix HiL-Flag"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.pl_pre_filled_after", purpose: "AK5-PL-3: Inkonsistenz-Check"}
    - {file: "_berater_outputs.md", path: "Frontmatter (item_id, cycle_nr)", purpose: "Lauf-Kontext"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/", path: "PL_Master*.md + *.md count", purpose: "AK5-PL-1: PL-Existenz-Check"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "batch_done-Verifikation", purpose: "Stale-Pruning"}
    - {file: "git", path: "rev-parse HEAD / cat-file -t {sha}", purpose: "Manifest-vs-Git-Check"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.resumeGuard", purpose: "{status, corrections[], resume_target, abort_reason, inconsistency_flag}"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.last_commit (Stale-Korrektur)", purpose: "Auto-Fix bei nicht existentem Commit"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.batch_done (Pruning)", purpose: "Stale-Eintraege entfernen"}
    - {file: "_berater_outputs.md", path: "Frontmatter last_update / last_berater", purpose: "Berater-Audit-Trail"}
  not_writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.* (ausser resumeGuard)"}
  calls:
    - "AskUserQuestion (NUR bei GLOBAL_HIL=on AND IDF_PIPELINE_STATE.idf_status laufend)"
---

# _IDF_berater_resumeGuard (Phase 1 in _IDF_orchestrate)

> **Zweck:** Migriert aus SDF. IDLE-Guard + Manifest-vs-Git-Validierung + Artefakt-Existenz-Check + PL-Existenz-Safety-Guard (BL-198 AK-5). K5-Fix bleibt aktiv.

## VERTRAG

```
+======================================================================+
|  VERTRAG: _IDF_berater_resumeGuard                                   |
+======================================================================+
|  LIEST:                                                              |
|    {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded)                                                      |
|      IDF_PIPELINE_STATE.idf_status / last_commit / batch_done        |
|      A_PIPELINE_STATE.pl_pre_filled_after (AK5-PL-3 Inkonsistenz)   |
|      GLOBAL_HIL, GLOBAL_MODUS                                        |
|    _berater_outputs.md Frontmatter (item_id, cycle_nr)               |
|    {VAULT}/Backlog/{bl_slug}/6_PL/                                   |
|      PL_Master*.md (AK5-PL-1 Existenz-Check)                        |
|      *.md count (AK5-PL-1 Fallback-Check)                           |
|      {bl_id}-parking-lot.md (batch_done-Verifikation)                |
|    git rev-parse HEAD                                                |
|    git cat-file -t {sha}                                             |
|                                                                      |
|  SCHREIBT:                                                           |
|    {WORKING_DIR}/_manifest.md                                        |
|      BERATER_OUTPUTS.resumeGuard = {                                 |
|        status, corrections[], resume_target,                         |
|        maturity_signal,    (NEU: fresh|in_progress|mature)           |
|        all_aks_done,       (NEU: bool)                               |
|        recommended_mode,   (NEU: normal|pl-only|refresh-aks)         |
|        abort_reason,       (AK5-PL-2: Routing-Hinweis bei ABORT)    |
|        inconsistency_flag  (AK5-PL-3: true wenn pl_pre_filled+PL leer)|
|      }                                                               |
|      IDF_PIPELINE_STATE.last_commit (Stale-Korrektur)                |
|      IDF_PIPELINE_STATE.resume_guard_corrected                       |
|      IDF_PIPELINE_STATE.batch_done (Pruning)                         |
|    _berater_outputs.md Frontmatter (last_update, last_berater)       |
|                                                                      |
|  SCHREIBT NICHT:                                                     |
|    BERATER_OUTPUTS.* (ausser resumeGuard)                            |
|                                                                      |
|  PFLICHT-LOGGING (NEU 2026-05-04):                                   |
|    [IDF_RG] vault_root={resolved_path}                               |
|    [IDF_RG] bl_folder={resolved_path}                                |
|    [IDF_RG] manifest={resolved_path}                                 |
|    [IDF_RG] idf_status={status} maturity={signal}                    |
|    [IDF_RG] aks_total={N} aks_done={D} → all_done={bool}             |
|    [IDF_RG] recommended_mode={mode}                                  |
|    [IDF_RG] pl_files_found: {liste}                                  |
|    [IDF_RG] AK5-GUARD pl_dir={path} pl_master_exists={bool}         |
|    [IDF_RG] AK5-GUARD pl_pre_filled={bool} inconsistency={bool}     |
|                                                                      |
|  ACTOR: _IDF_orchestrate Phase 1 (erster Berater)                    |
|                                                                      |
|  MODELL-TIER: sonnet                                                 |
|    Begruendung: 1:1 aus SDF migriert (TC1, sonnet bewaehrt).        |
|                                                                      |
|  INVARIANTEN:                                                        |
|    INV-2 (Write-Isolation auf BERATER_OUTPUTS.resumeGuard)           |
|    INV-FACTORY-1 (K5-Fix: AskUserQuestion NUR bei status=aborted     |
|                   bzw HiL=on, NICHT bei HiL=off + IDLE)              |
|    W17 (Regression-Baseline BL-113a AK-9)                            |
|    INV-MATURITY (NEU 2026-05-04): MUSS Maturity-Signal setzen.       |
|      maturity_signal=fresh:   IDF_PIPELINE_STATE leer/null            |
|      maturity_signal=in_progress: einige AKs DONE, andere offen      |
|      maturity_signal=mature:  ALLE AKs.status=DONE                   |
|      Wenn mature: recommended_mode='pl-only' (Phase 1+2+3.1 SKIP)    |
|    INV-IDF-SKIP-SAFETY-1 (BL-198 AK-5): BEVOR pl_only_from_a=true   |
|      im Orchestrate gesetzt wird, prüft resumeGuard SCHRITT 3b:      |
|      PL_Master.md MUSS in 6_PL/ existieren. Fehlt es bei             |
|      pl_pre_filled_after=true → ABORT mit Routing-Hinweis.           |
|      Fehlt es bei pl_pre_filled_after=false → ABORT (normaler Lauf   |
|      ohne A-Pipeline-Vorbedingung — erst A-Pipeline ausfuehren).     |
|                                                                      |
|  VORBEDINGUNGEN:                                                     |
|    - {WORKING_DIR}/_manifest.md existiert                            |
|                                                                      |
|  AUSGANGSBEDINGUNGEN:                                                |
|    - BERATER_OUTPUTS.resumeGuard {clean | corrected | aborted}       |
|    - BERATER_OUTPUTS.resumeGuard.maturity_signal gesetzt             |
|    - BERATER_OUTPUTS.resumeGuard.inconsistency_flag gesetzt (bool)   |
|    - Lead nutzt recommended_mode falls --pl-only nicht expl. gesetzt |
+======================================================================+
```

## Aufruf-Interface

```
Skill(_IDF_berater_resumeGuard, args="{NAME}")

Parameter:
  {NAME} - Feature-Name oder bl_id

Ausgabe:
  - BERATER_OUTPUTS.resumeGuard
  - Exitcode: 0=OK (clean|corrected), 2=ABORTED

Logging-Format:
  [IDF_RG] ENTRY item_id={x} cycle_nr={n}
  [IDF_RG] EXIT duration={ms}ms status={OK|ABORTED}
```

## Output-Schema

```yaml
BERATER_OUTPUTS:
  resumeGuard:
    status: "clean"              # clean | corrected | aborted
    corrections: []
    resume_target: "phase_1"
    maturity_signal: "fresh"     # fresh | in_progress | mature
    all_aks_done: false
    recommended_mode: "normal"   # normal | pl-only | refresh-aks
    abort_reason: null           # AK5-PL-2: gesetzt bei PL-Existenz-ABORT
    inconsistency_flag: false    # AK5-PL-3: true wenn pl_pre_filled=true + PL leer
    last_berater: "resumeGuard"
```

## Schritte (K5-Fix — aus SDF Z478-574, Pfad/State adaptiert auf IDF)

```
SCHRITT 0: Entry-Log
  [IDF_RG] ENTRY item_id={item_id} cycle_nr={cycle_nr}
  idf_status   = IDF_PIPELINE_STATE.idf_status ?? null
  corrections  = []
  resume_target = null
  status       = null

SCHRITT 1: IDLE-Guard MIT K5-Fix (ersetzt SDF Z491-509)
  IF idf_status IN [null, "IDLE", "DONE", "ABORTED"]:
    # Frischer Start — kein Resume noetig
    status        = "clean"
    resume_target = "phase_1"
    -> SCHRITT 4 (Output)

  IF idf_status IN ["INIT","PRE_LOAD_DONE","ANALYSE","ITEM_LOOP","ITEM_DONE","ITEM_STAGE"]:
    # Pipeline laufend — K5-Fix: HiL-Flag VOR AskUserQuestion pruefen
    IF GLOBAL_HIL == "off":
      # INV-FACTORY-1: kein AskUserQuestion bei HiL=off
      auto_resume = true
      corrections.append("AUTO_RESUME: HiL=off, idf_status={idf_status}")
      Logge: "[IDF_RG] K5-FIX: HiL=off -> Auto-Resume (kein AskUserQuestion)"
      # Kein STOP, direkt zu SCHRITT 2
    ELSE:
      # HiL=on: User-Interaktion erlaubt
      AskUserQuestion:
        header:   "IDLE-Guard: Pipeline bereits aktiv"
        question: "IDF-Pipeline aktiv (idf_status={idf_status}). RESUME / FORCE / STOP?"
      IF user_choice == "FORCE":
        idf_state_transition(ABORTED)
        idf_state_transition(INIT)
        status = "corrected"
        corrections.append("FORCE_RESTART")
        -> SCHRITT 4 (Output)
      ELIF user_choice == "STOP":
        status = "aborted"
        -> SCHRITT 4 (Output)
      # RESUME -> weiter mit SCHRITT 2

SCHRITT 2: Manifest-vs-Git-Validierung (AK-09-01..05, aus SDF Z514-573)
  git_head              = `git rev-parse HEAD`
  manifest_last_commit  = IDF_PIPELINE_STATE.last_commit ?? null

  IF manifest_last_commit != null:
    commit_exists = (`git cat-file -t {manifest_last_commit}` == "commit")
    IF NOT commit_exists:
      IDF_PIPELINE_STATE.last_commit            = git_head
      IDF_PIPELINE_STATE.resume_guard_corrected = true
      IDF_PIPELINE_STATE.resume_guard_reason    = "Commit {manifest_last_commit} nicht in Git"
      Aktualisiere {WORKING_DIR}/_manifest.md
      corrections.append("STALE_COMMIT: {manifest_last_commit} -> {git_head}")
      Logge: "[IDF_RG] STALE_COMMIT korrigiert: {manifest_last_commit} -> {git_head}"

SCHRITT 3: Artefakt-Existenz-Check (AK-09-04)
  IF IDF_PIPELINE_STATE.last_completed == "ANALYSE":
    model_ok = exists(".claude/models/{NAME}_Model.md")
    spec_ok  = exists(".claude/specs/{NAME}_Spec.md")
    IF NOT (model_ok AND spec_ok):
      # Harter Fehler: Artefakte fehlen trotz ANALYSE DONE (P8 Fail-Loud)
      status        = "aborted"
      resume_target = "phase_1"
      Logge: "[IDF_RG] ARTEFAKT-MISMATCH -> ABORTED (hard failure)"
      -> SCHRITT 4 (Output)

  IF IDF_PIPELINE_STATE.last_completed == "BATCH_ITEM_LOOP":
    FOR item_id IN IDF_PIPELINE_STATE.batch_done:
      pl_path = "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"
      IF "[x] {item_id}" NOT IN read(pl_path):
        IDF_PIPELINE_STATE.batch_done.remove(item_id)
        Aktualisiere {WORKING_DIR}/_manifest.md
        corrections.append("BATCH_DONE_PRUNE: {item_id}")
        Logge: "[IDF_RG] BATCH_DONE_PRUNE: {item_id} nicht in PL — entfernt"

  # Status setzen (P8 Fail-Safe: auto-korrigierbare Abweichungen)
  IF status != "aborted":
    status        = "corrected" IF corrections.length > 0 ELSE "clean"
    resume_target = "phase_{idf_phase}"

SCHRITT 3b: PL-Existenz-Safety-Guard (BL-198 AK-5, INV-IDF-SKIP-SAFETY-1)
  # Laeuft NACH SCHRITT 3 (Artefakt-Check), VOR Output.
  # Verhindert IDF-Lauf gegen leeres 6_PL/ (A-Pipeline unvollstaendig).
  # Guard greift auch wenn status bereits "aborted" (fruehzeitiger Guard bleibt aktiv).
  bl_folder        = BERATER_OUTPUTS.teamSetup.bl_folder ?? resolve_bl_path(bl_id)
  pl_dir           = f"{bl_folder}/6_PL/"
  pl_pre_filled    = A_PIPELINE_STATE.pl_pre_filled_after ?? false
  inconsistency_flag = false
  abort_reason       = null

  # AK5-PL-1: Existenz-Check — PL_Master*.md ODER mind. 1 *.md in 6_PL/
  pl_master_exists = exists_glob(f"{pl_dir}/PL_Master*.md")
  pl_files_count   = count_files(f"{pl_dir}/*.md")
  pl_exists        = pl_master_exists OR pl_files_count > 0

  Logge: "[IDF_RG] AK5-GUARD pl_dir={pl_dir} pl_master_exists={pl_master_exists} pl_files_count={pl_files_count}"
  Logge: "[IDF_RG] AK5-GUARD pl_pre_filled={pl_pre_filled} pl_exists={pl_exists}"

  # AK5-PL-3: Inkonsistenz-Check (pl_pre_filled=true ABER PL leer)
  IF pl_pre_filled == true AND NOT pl_exists:
    inconsistency_flag = true
    abort_reason = (
      "[INV-IDF-SKIP-SAFETY-1] INKONSISTENZ: pl_pre_filled_after=true aber 6_PL/ ist leer.\n"
      f"  bl_id={bl_id} pl_dir={pl_dir}\n"
      "  A-Pipeline hat pl_pre_filled_after gesetzt, aber PL_Master.md fehlt.\n"
      "  A-Pipeline war moeglicherweise unvollstaendig. Loesung:\n"
      f"  1. Skill(_A_orchestrate, args='{bl_id} fresh normal sonnet haiku') ausfuehren\n"
      "  2. Nach A-Pipeline: PL_Master.md muss in 6_PL/ existieren\n"
      "  3. Dann IDF erneut starten"
    )
    status = "aborted"
    Logge: "[IDF_RG] AK5-GUARD ABORT: INKONSISTENZ pl_pre_filled=true + PL leer"
    Logge: "[IDF_RG] {abort_reason}"
    # Kein GOTO — SCHRITT 4 schreibt den vollen Output inkl. abort_reason

  # AK5-PL-1 + AK5-PL-2: Normaler Lauf ohne PL (A-Pipeline fehlt)
  ELIF pl_pre_filled == false AND NOT pl_exists:
    # IDF kann nicht laufen ohne PL — A-Pipeline muss zuerst ausgefuehrt werden
    abort_reason = (
      "[IDF-GUARD AK5] PL fehlt fuer {bl_id}.\n"
      f"  pl_dir={pl_dir} — keine *.md Dateien vorhanden.\n"
      "  Loesung: Skill(_A_orchestrate, args='{bl_id} fresh normal sonnet haiku')\n"
      "  Nach A-Pipeline: pl_pre_filled_after=true → IDF startet bei Phase 3.5"
    )
    status = "aborted"
    Logge: "[IDF_RG] AK5-GUARD ABORT: PL leer, A-Pipeline erforderlich"
    Logge: "[IDF_RG] {abort_reason}"

  ELSE:
    # PL vorhanden — Guard PASS
    Logge: "[IDF_RG] AK5-GUARD PASS: pl_exists={pl_exists} pl_pre_filled={pl_pre_filled}"

SCHRITT 4: Output schreiben
  BERATER_OUTPUTS.resumeGuard = {
    status:             {status},          # clean | corrected | aborted
    corrections:        {corrections},
    resume_target:      {resume_target},
    maturity_signal:    {maturity_signal},
    all_aks_done:       {all_aks_done},
    recommended_mode:   {recommended_mode},
    abort_reason:       {abort_reason},    # null wenn kein ABORT
    inconsistency_flag: {inconsistency_flag}
  }
  _berater_outputs.md Frontmatter: last_update={jetzt}, last_berater="resumeGuard"

SCHRITT 5: Exit-Log
  exitcode = 2 wenn status=="aborted" else 0
  [IDF_RG] EXIT duration={ms}ms status={OK wenn exitcode==0 else ABORTED}
```

## K5-Fix Rationale (INV-FACTORY-1)

Bei `GLOBAL_HIL=off` blockiert `AskUserQuestion` den autonomen 24/7-Betrieb.
K5-Fix: HiL-Flag wird VOR jeder AskUserQuestion geprueft.
`aborted`-Status (exitcode=2) ist der einzige Fail-Loud-Pfad (P8).
`corrected`-Status (exitcode=0) deckt alle auto-reparierbaren Abweichungen ab.

## Begruendung Modell-Tier

sonnet — wie SDF-Original. Keine Aenderung am Reasoning-Bedarf durch Migration.
