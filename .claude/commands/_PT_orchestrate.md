# /_PT_orchestrate — Pattern-Extraction-Orchestrator (Single-Unit-of-Work Harvest)

```yaml
status: active
version: 1.2.0
created: 2026-06-02
updated: 2026-06-20   # BL-427 Cap-2: --source=commits Pfad + --target-lib + INV-PTO-7 (--ticket|--branch) + INV-PTO-COMMIT-1 + Parameter-Block + G-3/G-5-Update
op: PatternExtraction
phase: Orchestrator
type: orchestrator
chain_position: manual (KEIN Auto-Zyklus — User startet per Hand)
feature_anchor: BL-237 (Living Pattern System) — batch_C1 Spine-Aktivierung (PTO-0, SCOPE-SESSION, AK-6)
model_tier: ceiling (opus — Klassifikation + Forensik)
related: [_PT_promoteFromPL, _PT_extract, _PT_update, pattern_library.py, _SDF_berater_patternBrief, _PostBatch_PatternConformance, manifest_quiescence.py]
berater: [_PT_berater_gatherSignals, _PT_berater_clustering, _PT_berater_timeAxis, _PT_berater_contradiction, _PT_berater_classify, _PT_berater_forensic, _PT_berater_materialize, _PT_berater_report]
```

## Zweck

**Der mehrstufige, manuell gestartete Harvest der Pattern-Lernsignale** — der kohaerente Ersatz fuer
den heutigen 2-Hop-Leak (`_PT_promoteFromPL` → Kandidaten-Liste → `_PT_extract` → materialisieren, 95%
Verlust in DCSRE-486). Erntet ALLE verstreuten Fehler-/Lernsignale eines BL an EINEM Ort, klassifiziert
sie auf 3 Achsen, baut die Zeitachse, betreibt Revert-Forensik und materialisiert EINSTUFIG + reift die
Counter. Schliesst den Loop, der heute „designed alive, running dead" ist (BL-237).

**KEIN Auto-Zyklus** (User-Direktive 2026-06-02): per Hand gestartet, nicht Teil der BDF/SDF-Schleife.

## Architektur — Single-Unit-of-Work (/_help TEIL 0, P-10)

> **Team Lead = reiner Orchestrator** (spawn/track/Handschuh, KEIN Inline-Code). **Jede Stage = 1 Berater
> = 1 Job = stateless Worker, der eine Vault-Stelle liest, EIN Ding tut, seinen BERATER_OUTPUTS-Slot
> schreibt, stirbt.** State lebt im Manifest (`PT_EXTRACT_STATE` + `BERATER_OUTPUTS_PT.*`). Wie A/IDF/SDF.

```
  /_PT_orchestrate {BL_ID}   (Team Lead, INV-AO-CALLER)
        │  resumeGuard (PT_EXTRACT_STATE.stage_done — Resume-aware)
        │  QUIESCENZ-GATE: py manifest_quiescence.py check {BL_ID}  (BL-229 AK-E; BUSY → ABORT)
        ▼
   Stage 1  _PT_berater_gatherSignals     1 Job: ALLE Signale eines BL sammeln
   Stage 2  _PT_berater_clustering        1 Job: semantisch clustern (CORE/BORDER)
   Stage 3  _PT_berater_timeAxis          1 Job: git-History → temporale Ordnung + Reverts roh
   Stage 4  _PT_berater_contradiction     1 Job: widerspruechliche/zurueckgebaute Signale isolieren
   Stage 5  _PT_berater_classify          1 Job: 3-Achsen-Zuweisung (semantisch|architektonisch|fachlich)
   Stage 6  _PT_berater_forensic          1 Job: pro Revert — Pattern falsch / falsch-verwendet / Beschreibung-falsch
   Stage 7  _PT_berater_materialize       1 Job: EINSTUFIG materialisieren (pattern_library.py) + Counter (_PT_update pfad-1/2)
   Stage 8  _PT_berater_report            1 Job: Sichtbarkeits-Report (materialisiert/gereift/contested/retired)
```

Jede Stage liest die Outputs der Vorgaenger (Kompass) + ihre Primaerquelle direkt. Kein Shared State
ausser dem Manifest. Worker-Tier: gather/cluster/timeAxis = sonnet; classify/forensic/materialize = opus.

## VERTRAG (Orchestrator)

```
LIEST:
  {bl_folder}/_manifest.md  ODER  .claude/output/pt_harvest_{ticket_slug}.json (bei --source=commits)
    PT_EXTRACT_STATE.stage_done[]                 (Resume)
    BERATER_OUTPUTS_PT.*                           (Stage-Outputs)
  {bl_folder}/6_PL/{bl_id}-parking-lot.md          (PL-Signale; nur BL-gebundener Pfad)
  {bl_folder}/_manifest.md PATTERN_CONFORMANCE_STATE + s{N}_pt_signal   (Conformance/KEIN_PATTERN; nur BL-Pfad)
  {VAULT}/Libraries/PatternLibrary/_index.md       (Dedup + Counter-Stand)
  {VAULT}/Libraries/SemanticLibrary/_index.md
  git log/diff (via Worker)                         (Time-Axis + Reverts; + commit_sweep bei --source=commits)

SCHREIBT (nur via Berater-Slots — Single-Writer):
  {bl_folder}/_manifest.md  ODER  .claude/output/pt_harvest_{ticket_slug}.json (bei --source=commits)
    PT_EXTRACT_STATE                                (stage_done, started_at, verdict)
    BERATER_OUTPUTS_PT.{gatherSignals,clustering,timeAxis,contradiction,classify,forensic,materialize,report}
  {VAULT}/Libraries/{Pattern|Semantic|Factoring}Library/...   (NUR Stage 7, quiescenz-gated, via pattern_library.py)
  audit.jsonl                                       (PT_EXTRACT_* Events)

RUFT (Worker-Spawns, INV-PM-2 via Skill-Load im Worker):
  Agent(general-sonnet|opus, prompt="lade Skill(_PT_berater_X) + args") pro Stage

INVARIANTEN:
  INV-PTO-1 (AO-CALLER): Team Lead fuehrt _PT_orchestrate SELBST — NIE an Mega-Worker delegieren.
  INV-PTO-2 (Quiescenz): vor JEDER Stage-7-Materialisierung manifest_quiescence GREEN — sonst ABORT
    (kein Live-Write in eine Library bei aktiver Zweit-Session; BL-229 AK-E, 486-Incident-Lehre).
  INV-PTO-3 (Einstufig): Materialisierung NUR via pattern_library.py add (kein Kandidat→extract-2-Hop).
  INV-PTO-4 (Single-Writer): jeder Berater schreibt NUR seinen BERATER_OUTPUTS_PT-Slot.
  INV-PTO-5 (Manual): KEIN Auto-Trigger aus BDF/SDF. Nur expliziter User-/Lead-Aufruf.
  INV-PTO-6 (Reuse, nicht Neubau): nutzt bestehende Primitiven — pattern_library.py (add/find/counter),
    _PT_update --arch-lifecycle (pfad-1 usage++ / pfad-2 broken++), _PT_promoteFromPL-Worthiness-Heuristik.
  INV-PTO-7 (commits-Pflicht-Anker): --source=commits ohne --ticket UND ohne --branch → ABORT mit
    "[PT-ORCH] --source=commits erfordert --ticket={PRAEFFIX} oder --branch={range} als git-Anker.
    Recovery: mindestens einen der beiden Args ergaenzen."
    (Beides erlaubt: --ticket allein, --branch allein, oder beide zusammen.)
  INV-PTO-8 (synthetischer Slot): im --source=commits-Pfad lebt PT_EXTRACT_STATE im synthetischen
    Harvest-Slot (.claude/output/pt_harvest_{ticket_slug}.json) — KEIN bl_folder/manifest.md write.
    Stages 1-8 lesen/schreiben diesen Slot statt {bl_folder}/_manifest.md. materialize schreibt
    Library-Eintraege wie im BL-Pfad (quiescenz-gated, INV-PTO-2 gilt unveraendert).
  INV-PTO-COMMIT-1 (Abwaertskompatibilitaet): --source=pl (explizit) oder kein --source (Default = pl)
    verhalten sich EXAKT wie vor BL-427 — bl_folder/resolve_bl_path/PL-Quellen/Manifest-Slots unveraendert,
    commit_sweep_args leer, Stage-Loop identisch. Jeder bestehende Aufruf `/_PT_orchestrate {BL_ID}` bleibt
    ohne Aenderung gueltig. Kein alter Code-Pfad wird durch die neuen Params beruehrt.
```

## Aufruf

```
# BL-gebundener Harvest (Standard-Pfad — bl_folder aus BL_ID aufgeloest; unveraendert seit v1.1.0)
/_PT_orchestrate {BL_ID} [--dry-run] [--resume] [--axes=all|arch|semantic|fachlich] [--since={git-ref}]
                          [--target-lib={lib-slug}]

# Freistehender Commit-Harvest (BL-427 Cap-2 — KEIN BL_ID erforderlich)
/_PT_orchestrate --source=commits (--ticket={PRAEFFIX} | --branch={range} | beide)
                 [--author={substr}] [--target-lib={lib-slug}]
                 [--dry-run] [--axes=all|arch|semantic|fachlich]
```

> **BL-gebundener Pfad** (AK-CTX-SCOPE-SESSION, batch_C1): der einzige bewiesene Harvest (DCSRE-486);
> bl_folder wird aus BL_ID via `resolve_bl_path.py` aufgeloest. INV-PTO-COMMIT-1: unveraendert zu v1.1.0.
>
> **`--source=commits`-Pfad** (BL-427 Cap-2): kein OmniCommand-BL noetig; mindestens `--ticket` oder
> `--branch` ist Pflicht-Anker (INV-PTO-7); synthetischer Harvest-Slot statt bl_folder (INV-PTO-8).
> Rest der Stages (cluster→classify→forensic→materialize) identisch zum BL-Pfad.

## Parameter

| Parameter | Pfad | Pflicht | Default | Beschreibung |
|---|---|---|---|---|
| `{BL_ID}` | BL-gebunden | ja (ausser `--source=commits`) | — | OmniCommand-Backlog-ID; Heimat fuer `resolve_bl_path` + `bl_folder` |
| `--source=pl\|commits` | beide | nein | `pl` | `pl` = BL-gebundener Harvest (bewiesener Pfad). `commits` = freistehender Commit-Harvest ohne BL_ID (BL-427 Cap-2). Kein `--source` = implizit `pl` (INV-PTO-COMMIT-1). |
| `--ticket={PRAEFFIX}` | commits | nein* | — | git-log `--grep`-Anker; Pflicht-Anker bei `--source=commits` wenn kein `--branch` (INV-PTO-7). Wird 1:1 an Stage 1 gatherSignals durchgereicht. |
| `--author={substr}` | commits | nein | — | Substring-Filter auf `git log --author`; optionaler Eng-Qualifier. Wird an Stage 1 durchgereicht. |
| `--branch={range}` | commits | nein* | — | Branch-/Ref-Range (z.B. `main..HEAD`); ergaenzt oder ersetzt `--all` in git log. Alternativ-Anker zu `--ticket` (INV-PTO-7). Wird an Stage 1 durchgereicht. |
| `--target-lib={lib-slug}` | beide | nein | vault-default | Expliziter Ziel-Slug fuer die PatternLibrary-Schicht (z.B. `DCS-PatternLibrary-BE`). Wird NUR an Stage 7 `_PT_berater_materialize` durchgereicht (G-5); alle anderen Stages ignorieren ihn. Im commits-Pfad ueber `commit_sweep_args` transportiert. |
| `--dry-run` | beide | nein | — | Kein Library-Write; Stage 7 loggt was materialisiert wuerde. |
| `--resume` | beide | nein | — | Ueberspringt bereits erledigte Stages (resumeGuard via `stage_done[]`). |
| `--axes=all\|arch\|semantic\|fachlich` | beide | nein | `all` | Schraenkt Stage 5 classify auf eine Achse ein. |
| `--since={git-ref}` | BL-gebunden | nein | — | Git-Ref-Limit fuer Stage 3 timeAxis (commit-History-Schnitt). |

> *Bei `--source=commits`: mindestens `--ticket` oder `--branch` Pflicht (INV-PTO-7). Beide zusammen erlaubt.

## Spine-Glue (AK-CTX-PTO-0 — die 5 Aktivierungs-Punkte)

> Der Spine-Glue ist die Naht zwischen Team-Lead-Orchestrierung und den 8 isolierten Berater-Inseln.
> Genau 5 Glue-Punkte machen den Draft-Skeleton zum lauffaehigen `active`-Spine:

| # | Glue-Punkt | Wo | Was |
|---|---|---|---|
| G-1 | **Verdikt-Handling** | nach jedem Worker-Return (Phase 1-8) | Worker-`status`/-Slot lesen; bei `EMPTY`/Berater-Verdikt entscheidet der Lead CONTINUE vs. STOP (kein Inline-Re-Compute). |
| G-2 | **audit-Events** | Phase 0 + pro Stage + Phase 9 | `PT_EXTRACT_STARTED` / `PT_EXTRACT_STAGE_DONE` / `PT_EXTRACT_STAGE_SKIP` / `PT_EXTRACT_DONE` nach `audit.jsonl`. |
| G-3 | **Args-Durchreichung** | Worker-Spawn-Prompt | BL-Pfad: `{BL_ID}` + Flags (`--axes`/`--since`/`--dry-run`) an alle Stages. commits-Pfad: `--source=commits --harvest-slot` + `--axes`/`--dry-run` an alle Stages; zusaetzlich `--ticket`/`--author`/`--branch` NUR an Stage 1 gatherSignals (via `commit_sweep_args`). |
| G-4 | **Stage-7-BUSY-SKIP** | Phase 1-8 Loop | bei `materialize_allowed=false` wird NUR Stage 7 uebersprungen; Stages 1-6 + 8 laufen read-only weiter (INV-PTO-2). |
| G-5 | **Vault-/target-lib-/Quiescenz-Durchreichung** | Phase 0 → Stage 7 | `--target-vault={VAULT}` wird **IMMER** an `_PT_berater_materialize` durchgereicht (BL-374 AK-3 — deterministisch aus `current_context.py` aufgeloest, tier-1-Override gewinnt). `--target-lib` wird **konditional** durchgereicht wenn gesetzt (BL-427 Cap-2). `--quiescenz-override` ist der dritte konditionale Teil. Kein zweiter Gate-/Vault-Compute im Berater. |

## Ablauf (Team Lead — spawn/track/Handschuh)

### Phase 0: ResumeGuard + Quiescenz
```
# BL-374 AK-3: {VAULT} deterministisch aufloesen (kanonischer Resolver) — KEIN Platzhalter,
# damit der materialize-Stage-7-Write NIE in pattern_library.resolve_vault_root's hardcoded
# Fallback faellt (tier-1 Override gewinnt). Fail-safe: kein vault_root -> ABORT (kein Guess).
ctx = json.loads(Bash("py -3 .claude/scripts/current_context.py --format=json"))
VAULT = ctx.vault_root
IF VAULT == null OR VAULT == "": ABORT "[PT-ORCH] BL-374: vault_root nicht deterministisch aufloesbar — ABBRUCH (kein hardcoded-Fallback-Guess). Recovery: .vault_root/vault-routing.json pruefen."

# BL-427 Cap-2: Pfad-Weiche — BL-gebunden vs. freistehender Commit-Harvest (INV-PTO-COMMIT-1)
IF --source == "commits":
  # INV-PTO-7: --ticket ODER --branch als Pflicht-Anker
  IF NOT --ticket AND NOT --branch:
    ABORT "[PT-ORCH] --source=commits erfordert --ticket={PRAEFFIX} oder --branch={range} als git-Anker. Recovery: mindestens einen der beiden Args ergaenzen."
  ticket_slug = sanitize_filename(--ticket ?? --branch)   # z.B. "BL-427" oder "main..HEAD" → slug fuer Dateinamen
  harvest_slot = ".claude/output/pt_harvest_{ticket_slug}.json"
  # INV-PTO-8: synthetischer Slot statt bl_folder/_manifest.md
  PT_EXTRACT_STATE = read_json(harvest_slot).PT_EXTRACT_STATE ?? {stage_done: [], started_at: now, source: "commits", ticket: --ticket, branch: --branch}
  BL_ID = null          # kein BL gebunden — Stages ignorieren bl_folder-abhaengige Quellen (PL / Conformance)
  bl_folder = null
  # commit_sweep_args: an Stage 1 gatherSignals durchgereicht (G-3)
  commit_sweep_args = ""
  IF --ticket: commit_sweep_args += " --ticket={--ticket}"
  IF --author:  commit_sweep_args += " --author={--author}"
  IF --branch:  commit_sweep_args += " --branch={--branch}"
  LOG "[PT-ORCH] commits-Pfad: harvest_slot={harvest_slot}, ticket={--ticket ?? ''}, branch={--branch ?? ''}"
ELSE:
  # Standard BL-gebundener Pfad — EXAKT unveraendert (INV-PTO-COMMIT-1)
  bl_folder = resolve_bl_path(BL_ID)
  harvest_slot = null   # Manifest-Slot in {bl_folder}/_manifest.md (kein JSON-Sidecar)
  commit_sweep_args = ""
  ticket_slug = null
  PT_EXTRACT_STATE = manifest.PT_EXTRACT_STATE ?? {stage_done: [], started_at: now}

audit_jsonl_append({type: "PT_EXTRACT_STARTED", bl: BL_ID ?? ("commits-" + ticket_slug), source: --source ?? "pl", started_at: PT_EXTRACT_STATE.started_at})   # G-2
IF alle 8 Stages in stage_done: print "PT-Extract bereits DONE (Resume-SKIP)"; RETURN   # resumeGuard idempotent (B-1)

# Quiescenz NUR fuer den destruktiven Teil (Stage 7) — Stages 1-6/8 sind read-only/Manifest-lokal
quiescent = Bash("py .claude/scripts/manifest_quiescence.py check {BL_ID ?? 'global'}")
IF NOT quiescent AND NOT --dry-run:
  LOG "[PT-ORCH] BUSY — Stage 7 (Library-Write) gesperrt. Stages 1-6 laufen read-only weiter; Materialisierung deferred."
  materialize_allowed = false
ELSE: materialize_allowed = true

# G-5: Vault-/target-lib-/Quiescenz-Durchreichung an Stage 7 (einzige destruktive Stage)
# BL-374 AK-3: --target-vault IMMER durchreichen — tier-1 Override gewinnt, hardcoded Fallback nie erreicht.
# BL-427 Cap-2: --target-lib konditional durchreichen (ueberschreibt vault-default PatternLibrary-Schicht).
target_vault_arg = "--target-vault={VAULT}"                                    # IMMER (deterministisch aus Phase 0)
target_lib_arg = ("--target-lib={--target-lib}" IF --target-lib ELSE "")      # konditional (BL-427 Cap-2)
quiescenz_override_arg = ("--quiescenz-override" IF --quiescenz-override ELSE "")
materialize_vault_args = (target_vault_arg + " " + target_lib_arg + " " + quiescenz_override_arg).strip()
```

### Phase 1-8: Stage-Loop (1 Worker pro Stage, FLAT-SEQUENCE — AK-6 Schlussstein)
```
# AK-6: FLAT-SEQUENCE-Loop = 1 Worker = 1 Stage = 1 Job (INV-PTO-4 Single-Writer, INV-MOTOR-1-analog).
# resumeGuard SKIPt erledigte Stages (B-1 idempotenter Re-Run). KEIN Auto-Zyklus (INV-PTO-5).
harvest_id = BL_ID ?? ("commits-" + ticket_slug)   # fuer Logging + team_name
FOR stage IN [gatherSignals, clustering, timeAxis, contradiction, classify, forensic, materialize, report]:
  IF stage IN PT_EXTRACT_STATE.stage_done: CONTINUE          # resumeGuard — Resume-SKIP (B-1)
  IF stage == "materialize" AND NOT materialize_allowed:
    LOG "[PT-ORCH] Stage 7 SKIP (BUSY) — Signale klassifiziert+forensisch bereit, Materialisierung wartet auf Quiescenz."
    audit_jsonl_append({type: "PT_EXTRACT_STAGE_SKIP", stage, bl: harvest_id, reason: "quiescenz_busy"})   # G-2 + G-4
    CONTINUE                                                  # G-4: NUR Stage 7 skippt; Stages 1-6/8 laufen weiter
  tier = (stage IN [classify, forensic, materialize]) ? "opus" : "sonnet"
  # G-3 Args-Durchreichung: BL-Pfad vs. commits-Pfad (INV-PTO-COMMIT-1: BL-Pfad unveraendert)
  IF BL_ID != null:
    stage_args = "{BL_ID}" + pass_flags(--axes, --since, --dry-run)
  ELSE:
    # freistehender commits-Pfad: kein BL_ID; harvest_slot als State-Ankerpunkt
    stage_args = "--source=commits --harvest-slot={harvest_slot}" + pass_flags(--axes, --dry-run)
    # commit_sweep_args (--ticket/--author/--branch) NUR an Stage 1 gatherSignals — andere Stages ignorieren sie (G-3)
    IF stage == "gatherSignals": stage_args += commit_sweep_args
  # G-5: materialize_vault_args = --target-vault IMMER + --target-lib konditional + --quiescenz-override konditional
  IF stage == "materialize": stage_args += " " + materialize_vault_args
  Agent(
    subagent_type = "general-"+tier,
    description    = "PT-Extract Stage: "+stage+" ("+harvest_id+")",
    team_name      = "pt-extract-{harvest_id}",
    prompt = """
      [WORKER] Single-Unit-of-Work — Stage {stage} fuer Pattern-Extraction {harvest_id}.
      Lade via Skill-Tool: Skill(_PT_berater_{stage}, args="{stage_args}").
      Fuehre dessen VERTRAG aus. Lies Vorgaenger-BERATER_OUTPUTS_PT als Kompass + Primaerquelle direkt.
      Schreibe NUR BERATER_OUTPUTS_PT.{stage} (in harvest_slot falls --source=commits, sonst bl_folder/_manifest.md).
      SendMessage team-lead 1-Satz-Bilanz. STIRB.
    """
  )
  # nach Worker-Return (G-1 Verdikt-Handling): Slot-status lesen; Lead entscheidet CONTINUE vs STOP
  PT_EXTRACT_STATE.stage_done.append(stage)
  # INV-PTO-8: State-Persistenz in den richtigen Slot
  IF harvest_slot != null: write_json(harvest_slot, {PT_EXTRACT_STATE})
  ELSE: manifest.PT_EXTRACT_STATE = PT_EXTRACT_STATE
  audit_jsonl_append({type: "PT_EXTRACT_STAGE_DONE", stage, bl: harvest_id})   # G-2
END FOR
```

### Phase 9: Verdikt
```
report = BERATER_OUTPUTS_PT.report
print "[PT-ORCH] DONE — {report.materialized} materialisiert / {report.matured} gereift / {report.contested} contested / {report.retired} retired"
audit_jsonl_append({type: "PT_EXTRACT_DONE", bl: harvest_id, stages_done: PT_EXTRACT_STATE.stage_done, materialize_allowed})   # G-2
IF NOT materialize_allowed:
  IF BL_ID != null:
    resume_cmd = "/_PT_orchestrate {BL_ID} --resume" + ("--target-lib={--target-lib}" IF --target-lib ELSE "")
  ELSE:
    resume_cmd = "/_PT_orchestrate --source=commits"
    IF --ticket: resume_cmd += " --ticket={--ticket}"
    IF --author:  resume_cmd += " --author={--author}"
    IF --branch:  resume_cmd += " --branch={--branch}"
    IF --target-lib: resume_cmd += " --target-lib={--target-lib}"
    resume_cmd += " --resume"
  print "[PT-ORCH] HINWEIS: Materialisierung quiescenz-deferred — bei Quiescenz erneut: {resume_cmd}"
```

## Die 8 Berater (single unit of work — je eigenes Command, naechster Build-Schritt)

| Stage | Command | EIN Job | Liest | Schreibt (Slot) | Reuse |
|---|---|---|---|---|---|
| 1 | `_PT_berater_gatherSignals` | alle Signale sammeln | 6_PL + PATTERN_CONFORMANCE_STATE + s{N}_pt_signal + pattern-usage.log **+ git log/show (bei --ticket/--branch, INV-GS-5)** | `.gatherSignals.signals[]` | — |
| 2 | `_PT_berater_clustering` | CORE/BORDER clustern | .gatherSignals | `.clustering.clusters[]` | dispatch_findings-Logik |
| 3 | `_PT_berater_timeAxis` | git-History → Ordnung+Reverts | git log/diff | `.timeAxis.timeline[] + reverts_raw[]` | — |
| 4 | `_PT_berater_contradiction` | Widersprueche/Reverts isolieren | .clustering + .timeAxis | `.contradiction.items[]` | — |
| 5 | `_PT_berater_classify` | 3-Achsen-Zuweisung | .clustering + .contradiction | `.classify.{semantic,architectural,fachlich}[]` | Library-Layer-Map |
| 6 | `_PT_berater_forensic` | Revert→Hypothese (falsch/misused/mis-described) | .contradiction + .timeAxis + Code | `.forensic.verdicts[]` | — |
| 7 | `_PT_berater_materialize` | EINSTUFIG add + Counter | .classify + .forensic | `.materialize.{created,updated,retired}` | pattern_library.py add, _PT_update pfad-1/2 |
| 8 | `_PT_berater_report` | Sichtbarkeits-Report | alle obigen | `.report.*` | — |

## Abgrenzung

- **Ersetzt** den leckigen `_PT_promoteFromPL`→`_PT_extract`-2-Hop fuer den BL-Harvest (deren Worthiness-
  Heuristik wird in Stage 1/5 wiederverwendet; Single-Add `_pattern_add` bleibt der on-the-fly-Pfad).
- **NICHT** PRE-Consult (das ist `_SDF_berater_patternBrief` / `_I_patternLibrary`) und **NICHT** POST-A
  Conformance (`_PostBatch_PatternConformance`). Dieser Orchestrator ist POST-B: die Lern-Ernte.
- Counter-Mechanik wird NICHT dupliziert — Stage 7 delegiert an `_PT_update --arch-lifecycle` (BL-154).

## Status
**ACTIVE** v1.2.0 (BL-237 batch_C1 2026-06-02 + BL-427 Cap-2 2026-06-20). Spine draft→active: PTO-0 Glue
(5 Punkte G-1..G-5), AK-CTX-SCOPE-SESSION entfernt, AK-6 FLAT-SEQUENCE-Loop verdrahtet (resumeGuard-SKIP /
Stage-7-BUSY-SKIP / Args-Durchreichung / Vault-Durchreichung — BL-374 AK-3: `--target-vault={VAULT}` IMMER,
deterministisch via `current_context.py`). Alle 8 `_PT_berater_*`-Commands existieren (Stage 1 gatherSignals
v0.2.0 + Stages 2-8 batch_C1). Manual-only (INV-PTO-5), KEIN Auto-Zyklus.

**BL-427 Cap-2 (2026-06-20):** freistehender `--source=commits`-Pfad — synthetischer Harvest-Slot
(`.claude/output/pt_harvest_{ticket_slug}.json`, INV-PTO-8), Pfad-Weiche Phase 0, INV-PTO-7 (--ticket|--branch
als Anker), commit_sweep_args→Stage-1-Durchreichung (G-3), --target-lib→Stage-7-Durchreichung (G-5),
INV-PTO-COMMIT-1 (BL-Pfad vollstaendig unveraendert). Parameter-Block dokumentiert.

Naechste Batches (NICHT hier): Counter-Feed-Anschluesse (LOGFMT/R6a/R6b/R1/R2/R4 = C3a), Factoring-/Domain-
Library-Anlage (C4), WORTHINESS-EXTRACT (C5), 486-Live-Beweis (C5). Erst-Lauf: manuell gegen DCSRE-486
(die ~80 un-geernteten Signale, quiescenz-gated).
