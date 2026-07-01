---
status: deprecated
version: 1.0
type: berater
parent: _SDF_orchestrate
model_tier: middle
actor: _SDF_PreBerater_orchestrate (C9b) — Schritt 1
sdf_quelle: Z478-574
tc: TC1
feature: BL-124
created: 2026-04-18
---

# _SDF_berater_resumeGuard (C1)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_resumeGuard (C1)                              ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST: {WORKING_DIR}/_manifest.md  (INV-VAULT-9: via Path-Resolver, nicht hardcoded) (DF_PIPELINE_STATE.df_status,                   ║
║           DF_PIPELINE_STATE.last_commit, batch_done,                 ║
║           GLOBAL_HIL, GLOBAL_MODUS)                                  ║
║         _berater_outputs.md Frontmatter (item_id, cycle_nr)          ║
║         {VAULT}/.../6_PL/{bl_id}-parking-lot.md (batch_done Verf.)  ║
║  SCHREIBT: BERATER_OUTPUTS.resumeGuard                               ║
║            {status, corrections[], resume_target}                    ║
║            + _berater_outputs.md Frontmatter: last_update,           ║
║              last_berater="C1"                                        ║
║  SCHREIBT AUCH: {WORKING_DIR}/_manifest.md DF_PIPELINE_STATE.last_commit (Stale-   ║
║                 Korrektur, AK-09-02) + resume_guard_corrected=true   ║
║                 {WORKING_DIR}/_manifest.md DF_PIPELINE_STATE.batch_done (Prune)    ║
║  SCHREIBT NICHT: andere BERATER_OUTPUTS-Sub-Felder                   ║
║  ACTOR: _SDF_PreBerater_orchestrate (C9b) — erster Schritt           ║
║  MODELL-TIER: middle (sonnet) — TC1, SDF-Quelle Z478-574            ║
║  INVARIANTEN: INV-2 (Write-Isolation), INV-6 (kein Pruning hier —   ║
║               resumeGuard laeuft IMMER als Phase-0-Berater),         ║
║               INV-FACTORY-1 (K5-Fix: AskUserQuestion NUR bei         ║
║               status=aborted, NICHT bei HiL=off + IDLE),            ║
║               W17 (Regression-Baseline BL-113a AK-9)                ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Aufruf-Interface

```
Skill(_SDF_berater_resumeGuard, args="{NAME}")

Parameter:
  {NAME} — Feature-Name (z.B. "BL-124")

Ausgabe:
  - BERATER_OUTPUTS.resumeGuard (3 Felder)
  - Exitcode: 0=OK (clean|corrected), 2=ABORTED (hard failure)

Logging-Format (NFR-4):
  [C1_resumeGuard] ENTRY item_id={item_id} cycle_nr={cycle_nr}
  [C1_resumeGuard] EXIT duration={ms}ms status={OK|ABORTED}
```

## Schritte (K5-Fix — aus SDF Z478-574, OBSERVE1 K5)

```
SCHRITT 0: Entry-Log
  [C1_resumeGuard] ENTRY item_id={item_id} cycle_nr={cycle_nr}
  df_status = DF_PIPELINE_STATE.df_status ?? null
  corrections = []
  resume_target = null
  status = null

SCHRITT 1: IDLE-Guard MIT K5-Fix (ersetzt SDF Z491-509)
  IF df_status IN [null, "IDLE", "DONE", "ABORTED"]:
    # Frischer Start — kein Resume noetig
    status = "clean"
    resume_target = "phase_0"
    → SCHRITT 4 (Output)

  IF df_status IN ["INIT","PRE_LOAD_DONE","ANALYSE","ITEM_LOOP","ITEM_DONE","ITEM_STAGE"]:
    # Pipeline laufend — K5-Fix: HiL-Flag VOR AskUserQuestion pruefen
    IF GLOBAL_HIL == "off":
      # INV-FACTORY-1: kein AskUserQuestion bei HiL=off
      auto_resume = true
      corrections.append("AUTO_RESUME: HiL=off, df_status={df_status}")
      Logge: "[C1_resumeGuard] K5-FIX: HiL=off → Auto-Resume (kein AskUserQuestion)"
      # Kein STOP, direkt zu SCHRITT 2
    ELSE:
      # HiL=on: User-Interaktion erlaubt (SDF v0.8.0 Verhalten beibehalten)
      AskUserQuestion:
        header: "IDLE-Guard: Pipeline bereits aktiv"
        question: "SDF-Pipeline aktiv (df_status={df_status}). RESUME / FORCE / STOP?"
      IF user_choice == "FORCE":
        df_state_transition(ABORTED)
        df_state_transition(INIT)
        status = "corrected"
        corrections.append("FORCE_RESTART")
        → SCHRITT 4 (Output)
      ELIF user_choice == "STOP":
        status = "aborted"
        → SCHRITT 4 (Output)
      # RESUME → weiter mit SCHRITT 2

SCHRITT 2: Manifest-vs-Git-Validierung (AK-09-01..05, aus SDF Z514-573)
  git_head = `git rev-parse HEAD`
  manifest_last_commit = DF_PIPELINE_STATE.last_commit ?? null

  IF manifest_last_commit != null:
    commit_exists = (`git cat-file -t {manifest_last_commit}` == "commit")
    IF NOT commit_exists:
      DF_PIPELINE_STATE.last_commit = git_head
      DF_PIPELINE_STATE.resume_guard_corrected = true
      DF_PIPELINE_STATE.resume_guard_reason = "Commit {manifest_last_commit} nicht in Git"
      Aktualisiere {WORKING_DIR}/_manifest.md
      corrections.append("STALE_COMMIT: {manifest_last_commit} → {git_head}")
      Logge: "[C1_resumeGuard] STALE_COMMIT korrigiert: {manifest_last_commit} → {git_head}"

SCHRITT 3: Artefakt-Existenz-Check (AK-09-04)
  IF DF_PIPELINE_STATE.last_completed == "ANALYSE":
    model_ok = exists("{VAULT}/Backlog/{bl_slug}/2_Model/{NAME}_Model.md")
    spec_ok  = exists("{VAULT}/Backlog/{bl_slug}/3_Spec/{NAME}_Spec.md")
    IF NOT (model_ok AND spec_ok):
      # Harter Fehler: Artefakte fehlen trotz ANALYSE DONE (P8 Fail-Loud)
      status = "aborted"
      resume_target = "phase_0"
      Logge: "[C1_resumeGuard] ARTEFAKT-MISMATCH → ABORTED (hard failure)"
      → SCHRITT 4 (Output)

  IF DF_PIPELINE_STATE.last_completed == "BATCH_ITEM_LOOP":
    FOR item_id IN DF_PIPELINE_STATE.batch_done:
      pl_path = "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md"
      IF "[x] {item_id}" NOT IN read(pl_path):
        DF_PIPELINE_STATE.batch_done.remove(item_id)
        Aktualisiere {WORKING_DIR}/_manifest.md
        corrections.append("BATCH_DONE_PRUNE: {item_id}")
        Logge: "[C1_resumeGuard] BATCH_DONE_PRUNE: {item_id} nicht in PL — entfernt"

  # Status setzen (P8 Fail-Safe: auto-korrigierbare Abweichungen)
  IF status != "aborted":
    status = "corrected" IF corrections.length > 0 ELSE "clean"
    resume_target = "phase_{df_phase}"

SCHRITT 4: Output schreiben
  BERATER_OUTPUTS.resumeGuard = {
    status: {status},           # clean | corrected | aborted
    corrections: {corrections},
    resume_target: {resume_target}
  }
  _berater_outputs.md Frontmatter: last_update={jetzt}, last_berater="C1"

SCHRITT 5: Exit-Log
  exitcode = 2 wenn status=="aborted" else 0
  [C1_resumeGuard] EXIT duration={ms}ms status={OK wenn exitcode==0 else ABORTED}
```

## Output an BERATER_OUTPUTS.resumeGuard

```yaml
resumeGuard:
  status: "clean"          # clean | corrected | aborted
  corrections: []          # Liste von Korrekturen (leer wenn clean)
  resume_target: "phase_0" # Phase fuer C9b-Sprung
```

## K5-Fix Rationale (INV-FACTORY-1)

Bei `GLOBAL_HIL=off` blockiert `AskUserQuestion` den autonomen 24/7-Betrieb.
K5-Fix: HiL-Flag wird VOR jeder AskUserQuestion geprueft.
`aborted`-Status (exitcode=2) ist der einzige Fail-Loud-Pfad (P8).
`corrected`-Status (exitcode=0) deckt alle auto-reparierbaren Abweichungen ab.
