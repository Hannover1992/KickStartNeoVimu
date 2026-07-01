# /_A_orchestrate - Team Lead Analyse-Orchestrierung (Thin-Manager)

```yaml
status: active
version: 3.6.0
created: 2026-02-19
updated: 2026-06-14
changelog_3_6_0: |
  BL-346: pileOfMud-Relevanz-Gate + mature-consolidated-EPIC-Carve-Out in Phase 0.5.
    AK-1: vor findingsExtraction filtert pile_relevance.partition_pile_by_relevance die
      Live-Pile-Files gegen den per-BL Snapshot ({bl_folder}/Sources/_pileOfMud_snapshot/,
      Basename+original_hash). Fremd-Material (andere Session) wird LAUT gemeldet + geskippt.
      Fresh-Intake (Snapshot==Live) laeuft UNVERAENDERT (abwaertskompatibel).
    AK-2: ein BL mit 0 relevanten Pile-Files + reichem AK-Cluster + superseded-Sources
      (consolidated EPIC, z.B. BL-282) nutzt Node+superseded als Findings-Quelle, NICHT
      fremden pileOfMud (is_mature_consolidated_epic). Verhindert stillen Garbage-Extract.
changelog_3_5_0: |
  BL-209 Hard-Cut: --skip-pl-generation Flag ENTFERNT.
  PL-Generierung (Phase 5a/5b/5c) ist IMMER Teil A-Pipeline. Kein Bypass.
  IDF erwartet immer pl_pre_filled_after=true. INV-BC-1 + INV-IDF-SKIP-1 RETIRED in IDF.
  INV-NS-1 (BL-197): _IDF_berater_specParse/akExtraktion/plAggregation jetzt DEPRECATED.
changelog_3_4_0: |
  BL-197 batch_D Integration vollstaendig.
  Phase 5c setzt A_PIPELINE_STATE.pl_pre_filled_after=true direkt (INV-ROUTING-1 downstream).
  --skip-pl-generation Flag im VERTRAG-Block dokumentiert (jetzt ENTFERNT via BL-209).
  Cross-Reference zu _IDF_orchestrate.md INV-IDF-SKIP-1 ergaenzt.
changelog_3_3_0: |
  BL-197 A-Pipeline absorbiert Forward-PL-Generierung.
  Drei neue Phasen 5a/5b/5c eingefuegt (nach Phase 4g, vor Phase 4.2a).
  Phase 5 (routing) bleibt LAST — keine Renummerierung (OQ-1 resolved).
  Drei neue Berater: _A_berater_specParse (5a), _A_berater_akExtraktion (5b),
  _A_berater_plAggregation (5c). INV-A-ORDER-5/6, INV-PL-1, INV-NS-1 aktiv.
changelog_3_2_0: |
  W_fetch verschoben von Phase 3a (NACH Model) auf Phase 2.5 (VOR Model).
  Begruendung: Model muss W_fetch-Output als Wissensbasis nutzen — sonst baut
  Model parallel zu existierendem Vault-Wissen ohne es zu kennen.
  Aktiver Guard INV-A-ORDER-4 hinzugefuegt: ABORT wenn Phase 3 model
  ohne BERATER_OUTPUTS.wfetch.status == "DONE" startet (vorher nur dokumentarisch).
  Aktiver Guard INV-PM-5 hinzugefuegt: Skill-Calls MUESSEN ueber Worker-Spawn
  (Agent()) erfolgen, NIE durch Team Lead direkt. Vorher nur INV-PM-1
  dokumentarisch — wurde verletzt weil Pseudocode "Skill(_A_berater_X)"
  mehrdeutig war (konnte als Direkt-Load gelesen werden).
op: AnalysisPipeline
phase: Meta
type: orchestration
chain_position: meta
difficulty_scaling: true
team_based: true
bl_142_implementation: true
```

---

## BL-173 Manifest-Routing (NEU 2026-05-18)

**Manifest-Scope-Split aktiv** (siehe BL-173, INV-MANIFEST-SPLIT-1..4):

| State-Block | Heimat | Helper |
|---|---|---|
| A_PIPELINE_STATE | `{bl_folder}/_manifest.md` | `manifest_reader.read_bl_block(bl_id, "A_PIPELINE_STATE")` |
| BL_LIFECYCLE_STATE | `{bl_folder}/_manifest.md` | `manifest_reader.read_bl_block(bl_id, "BL_LIFECYCLE_STATE")` |
| BERATER_OUTPUTS | `{bl_folder}/_manifest.md` | `manifest_reader.read_bl_block(bl_id, "BERATER_OUTPUTS")` |
| GLOBAL_* (read-only) | `{vault_root}/_factory_manifest.md` | `manifest_reader.read_factory_block("GLOBAL_*")` |

**Pfad-Aufloesung:**
- Factory-State: `manifest_reader.read_factory_block(...)` ODER direkt `{vault_root}/_factory_manifest.md`
- BL-State: `manifest_reader.read_bl_block(bl_id, ...)` ODER direkt `{bl_folder}/_manifest.md`
- Legacy-Fallback aktiv solange `is_split_active() == False` (1-Sprint-Uebergang)

**Migration:** `py -3 .claude/scripts/migrate_manifest_split.py migrate --vault-root="..." --rollback-tag=YYYY-MM-DD`

---

```
+======================================================================+
| /_A_orchestrate v3.4.0 (Thin-Manager, BL-142 Phase 4A + BL-197)     |
+======================================================================+
| ACTOR: TEAM LEAD (DU - reiner Orchestrator)                         |
| ZWECK: Wissensbasis-Bauer — Pile of Mud -> Findings -> taskDef ->   |
|        Model -> Spec -> K-Score -> Gap -> Routing-Entscheidung      |
| LIFECYCLE: 6-Stufen-Klammer (Cleanup -> TeamCreate -> Modus ->       |
|            Tasks -> Phasen -> TeamDelete)                            |
| PHASEN (Reihenfolge):                                               |
|   0.1 modusErkennung -> 0.2 discovery -> 0.5 findingsExtraction ->  |
|   0.5.2 findingsReview -> 0.5.3 domainBrief -> 0.6 taskDefinition ->|
|   1.5 git_analyse (optional pr=true) ->                              |
|   2 iddContext -> 2.5 W_fetch (VOR Model) -> 3 model ->             |
|   4 spec (+HiL AK) -> 4k K_score -> 4g gap ->                        |
|   5a specParse -> 5b akExtraktion -> 5c plAggregation (BL-197 NEU) -> |
|   4.2a metadatenAggregation -> 4.4 gitTracking ->                   |
|   4.3 stateMaintain -> 5d arc42 (BL-378) -> 5 routing (LAST)        |
+======================================================================+
```

---

## VERTRAG (kompakt, Detail in Beratern)

```
WORKING_DIR = resolve_bl_path(BL_ID)  # INV-VAULT-9

LIEST:
  {WORKING_DIR}/_manifest.md (A_PIPELINE_STATE)  # per-Story (BL-155 AK-1)
  {VAULT}/_manifest.md (BACKLOG_STATE)           # global
  {VAULT}/_session_params.md                     # global Session-Params
  {VAULT}/Task.md (optional)
  {VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md   # Vault-First (BL-151 Migration abgeschlossen 2026-05-06)
  FALLBACK .claude/models/{NAME}_Model.md
  .claude/pileOfMud/ (Rohmaterial)
  .claude/crumbs/{NAME}_*_crumbs.md (findings, wp, taskDef-Crumbs)
  --parent-pr {branch}: IDD-Modus, liest Parent-Branch via iddContext-Berater
  # --skip-pl-generation ENTFERNT (BL-209 2026-05-24): PL-Generierung (Phase 5a/5b/5c) ist
  #   IMMER Teil der A-Pipeline. Kein Bypass mehr. IDF erwartet immer pl_pre_filled_after=true.

SCHREIBT:
  {WORKING_DIR}/_manifest.md (A_PIPELINE_STATE inkl. phase, modus, recommendation,
                              k_score, idd_active, completion_signal)  # per-Story (BL-155 AK-1)
  BERATER_OUTPUTS.{name} (pro Berater eigener State-Subtree)
  BERATER_OUTPUTS.specParse (Phase 5a) — sections[], aks[], rfs[], status
  BERATER_OUTPUTS.akExtraktion.{ak_id} (Phase 5b) — pl_item_draft, status pro AK
  BERATER_OUTPUTS.plAggregation (Phase 5c) — pl_master_path, item_count, status, pl_pre_filled
  .claude/crumbs/{NAME}_findings_crumbs.md (via findingsReview)
  Vault: Task.md, Model.md, Spec.md, K-Score.md, Gap.md
  {VAULT}/Backlog/{BL_SLUG}/6_PL/{BL_ID}-parking-lot.md (Phase 5c, INV-PL-1)
  FALLBACK lokal: .claude/specs / .claude/models / .claude/analysis/synthese
  _manifest_protokoll.md (Pattern B Rollover via stateMaintain)

RUFT (12 Berater via Skill()):
  _A_berater_modusErkennung   (Phase 0.1)
  _A_berater_discovery        (Phase 0.2)
  _A_berater_findingsExtraction (Phase 0.5)
  _A_berater_findingsReview   (Phase 0.5.2)
  _A_berater_domainBrief      (Phase 0.5.3, BL-254 NEU — DomainLibrary-Konsultation/Dedup)
  _A_berater_iddContext       (Phase 2, NUR bei --parent-pr)
  _A_berater_specParse        (Phase 5a, BL-197 NEU)
  _A_berater_akExtraktion     (Phase 5b, BL-197 NEU — pro AK)
  _A_berater_plAggregation    (Phase 5c, BL-197 NEU)
  # Downstream-Konsumenten (nicht direkt gerufen, konsumieren A-Pipeline-Output):
  # _IDF_orchestrate Phase 0.9 liest A_PIPELINE_STATE.pl_pre_filled_after
  #   → INV-IDF-SKIP-1: SKIP Phase 2/3.1/3.2 wenn true (BL-197 AK-6, batch_C)
  # _A_postRoute Exit-Router liest A_PIPELINE_STATE.completion_signal
  _A_berater_metadatenAggregation (Phase 4.2a)
  _A_berater_gitTracking      (Phase 4.4)
  _A_berater_stateMaintain    (Phase 4.3)
  _A_berater_routing          (Phase 5 LAST)

RUFT (Pipeline-Commands via Skill, eigene Wellen):
  _taskDefinition (Phase 0.6 NEU FRUEH)
  _git_analyse    (Phase 1.5, optional pr=true)
  _W_fetch        (Phase 2.5, VOR Model — INV-A-ORDER-4)
  _model | _SC_modelMaintain (Phase 3, modus-abhaengig)
  _spec           (Phase 4)
  _K_score        (Phase 4k)
  _gap            (Phase 4g)
  _arc42_orchestrate (Phase 5d, BL-378 — terminale arc42-View-Schicht, NON-BLOCKING, scope!=transkript-only)
```

---

## INVARIANTEN

```
INV-LIFECYCLE-1..5: 6-Stufen-Klammer (Cleanup/TeamCreate/Modus/Tasks/Phasen/TeamDelete)
INV-DATA-1: Datentraeger-Kette via BERATER_OUTPUTS / A_PIPELINE_STATE
INV-THIN-1: Orchestrator <= 350 LOC
INV-THIN-2: Inline-Logik pro Phase <= 30 LOC
INV-THIN-3: Berater-Schreib-Isolation (jeder schreibt nur seinen BERATER_OUTPUTS-Slot)

INV-YAML-APPEND-1 (AK-7, BL-364 F6): BERATER_OUTPUTS-Writes in _manifest.md sind IMMER
               APPEND-Operationen (neuer YAML-Block anhaengen), NIEMALS Overwrite des gesamten
               Manifests. Schema-Doktrin:
                 KORREKT (nested, Append):
                   ```yaml
                   BERATER_OUTPUTS:
                     berater_name:
                       key: value
                   ```
                 AUCH AKZEPTIERT (flach, Append — Bash-echo-Drift):
                   ```yaml
                   BERATER_OUTPUTS_berater_name:
                     key: value
                   ```
               Downstream-Berater MUESSEN beide Formen tolerieren (toleranter Reader via
               Grep-Fallback: erst `BERATER_OUTPUTS.berater_name` nested suchen,
               Fallback `BERATER_OUTPUTS_berater_name` Top-Level). Die nested Form ist
               kanonisch; Bash-echo/Append-Operationen driften zum flachen Top-Level-Key —
               das ist toleriert solange der Block-Anfang klar abgegrenzt ist (```yaml + ```).
               Block-Grenzen (```yaml ... ```) sind PFLICHT — kein YAML ohne Fence.
               Verweis: [[BL-364]] AK-7 (F6 Schema-Drift), [[BL-367]] F8/F9 (manifest-append-Helper).

INV-A-ORDER-1 (RF-A-ORDER): taskDefinition LAEUFT VOR W_fetch (Phase 0.6 vor Phase 2.5)
INV-A-ORDER-2: W_fetch nutzt taskDefinition-Output als Suchkontext;
               Model nutzt W_fetch-Output als Wissensbasis (Phase 2.5 vor Phase 3)
INV-A-ORDER-3: Routing ist immer LAST (Phase 5, nach allen Pipeline-Commands)
INV-A-ORDER-4 (AKTIVER GUARD, v3.2.0): Phase 3 model MUSS ABORTEN wenn
               BERATER_OUTPUTS.wfetch.status != "DONE". Ohne diesen Check baut
               Model parallel zu existierendem Vault-Wissen — Wissens-Drift.
INV-A-ORDER-5 (BL-197): Phase 5a (specParse) MUSS nach Phase 4g (gap) laufen.
               Verletzt wenn specParse startet ohne gap.status=DONE.
INV-A-ORDER-6 (BL-197): Phase 5b (akExtraktion) MUSS nach Phase 5a DONE laufen.
               Alle akExtraktion-Worker abgeschlossen vor Phase 5c.
INV-PL-1 (BL-197): PL_Master existiert NACH Phase 5c und NICHT vorher.
               A-Pipeline darf vor Phase 5c keine PL_Master.md schreiben.
INV-NS-1 (BL-197, UPDATED BL-209): _A_berater_specParse/akExtraktion/plAggregation
               sind Single-Source (A-Pipeline Phase 5a/5b/5c).
               _IDF_berater_specParse/akExtraktion/plAggregation sind DEPRECATED (BL-209).
               IDF ruft diese Berater NICHT mehr. Kein Namespace-Split mehr noetig.

INV-PM-5 (AKTIVER GUARD, v3.2.0): Berater-Skills MUESSEN ueber Worker-Spawn
               aufgerufen werden — Team Lead lädt den Skill NIE selbst.
               Konkret: Pseudocode-Notation "Skill(_A_berater_X, args=...)"
               wird semantisch interpretiert als:
                  Agent(subagent_type=tier, prompt="Lade Skill _A_berater_X
                  und fuehre Vertrag aus mit args=...", team_name="a-{name}")
               Begruendung: Verstoss gegen INV-PM-1 (Worker-Pflicht ABSOLUT)
               passiert sonst still — Team Lead wird zum Ausfuehrenden.
               CaseStudy SemantischePatternLibrary 2026-04-30: Skill-Direkt-
               Load durch Team Lead beim ersten Lauf — nur dokumentarischer
               INV-PM-1 reichte nicht.

INV-SP-1 (RF-08): Anti-Stille-Post — Wellen lesen Primaerquellen DIREKT
INV-SP-2 (RF-08, AK-08-04): Spec-Drafter lesen Model.md/Commands/Task.md DIREKT
INV-PM-1 (RF-06): Worker-Pflicht — Auch bei easy spawnt Team Lead Worker
INV-EXTRACT-1..5: Findings-Extraktion erzwingt Sonnet-Floor (kein Haiku)
INV-W7: Kein Agent(), nur Skill() / Lies / Schreibe (Worker-Spawning in Berater)

INV-AO-CALLER (AKTIVER GUARD, Sanity-Check V11, 2026-05-07):
               Dieser Orchestrator MUSS vom Team Lead SELBST ausgefuehrt werden,
               direkt nach `Skill(_A_orchestrate)`-Load. VERBOTEN: Aufruf via
               `Agent(general-sonnet, prompt="orchestrate A-Pipeline ...")`
               oder anderes Sub-Agent-Delegieren. Der Sub-Agent wird sonst zum
               Mega-Agent: interpretiert die `Skill(_A_berater_X)`-Stellen
               unten als Inline-Logik statt 9 Worker-Spawns. INV-PM-5 deckt nur
               Berater-Skill-Direkt-Loads ab, NICHT die Hub-Delegation.
               Beweis-Lauf: DCSRE-2014 Hot-Fix 2026-05-07 — 1 general-sonnet
               machte alle 9 Berater-Phasen, ohne Team, ohne BERATER_OUTPUTS-
               Trennung, AK-4 ungeklaert weil keine Phase-Separation.
```

---

## STATE-MACHINE (kompakt)

```
INIT -> MODUS_ERKANNT -> DISCOVERY_DONE -> FINDINGS_DONE
     -> TASKDEF_DONE  -> IDD_DONE        -> WFETCH_DONE
     -> MODEL_DONE    -> SPEC_DONE       -> KSCORE_DONE
     -> GAP_DONE
     -> PHASE_5A_DONE -> PHASE_5B_DONE  -> PHASE_5C_DONE  # BL-197 NEU
     -> META_DONE     -> ROUTING_DONE
     -> COMPLETED | COMPLETED_TRANSKRIPT_ONLY | ABORTED
```

---

## PARAMETER

| Name | Default | Werte | Beschreibung |
|------|---------|-------|--------------|
| `name` | `auto` | string \| `auto` | `auto` triggert Discovery (Phase 0.2). |
| `modus` | `fresh` | `fresh \| resync` | Fresh = voller Prozess; Resync = modelMaintain. |
| `difficulty` | `normal` | `easy \| normal \| hard` | Wellen-Skalierung. |
| `ceiling` | `sonnet` | `haiku \| sonnet \| opus` | Hoechstes Modell. |
| `floor` | `haiku` | `haiku \| sonnet` | Niedrigstes Modell. |
| `--parent-pr` | (leer) | `{branch}` | IDD-Modus, aktiviert iddContext (Phase 2). |
| `--entry-point` | `manual` | `bdf \| manual` | BDF-getriggert oder manueller Start. |
| `--scope` | `full` | `full \| transkript-only` | Transkript-Only = kein Routing zu SC/I. |
| `--mode` | `normal` | `normal \| dryRun` | Dry-Run via init-Berater (BL-089). |
| `pr` | `false` | `true \| false` | Optional Phase 1.5 — `/_git_analyse` Snapshot fuer PR-Aufgaben. |

```
Skill(skill="_A_orchestrate", args="{name} {modus} {difficulty} {ceiling} {floor}")
Skill(skill="_A_orchestrate", args="DCSRE-93 fresh normal sonnet haiku --parent-pr feature/base")
Skill(skill="_A_orchestrate", args="QuickCheck resync easy haiku haiku")
```

---

## 6-STUFEN-LIFECYCLE

| Stufe | Name | Zweck | Invariante |
|-------|------|-------|------------|
| 1 | **Cleanup** | altes `active_team` shutdown + TeamDelete | INV-LIFECYCLE-1 |
| 2 | **TeamCreate** | neues Team `a-{name}` registrieren | INV-LIFECYCLE-2 |
| 3 | **Modus-Erkennung** | fresh/resync + GLOBAL_HIL + autonomie | INV-LIFECYCLE-3 |
| 4 | **Tasks vorab** | TaskCreate fuer alle Phasen mit DAG | INV-LIFECYCLE-4 |
| 5 | **Phasen-Ausfuehrung** | Skill()-Calls in NEUER Reihenfolge | INV-THIN-1..3 |
| 6 | **TeamDelete** | `a-{name}` abbauen, `active_team=null` | INV-LIFECYCLE-5 |

---

## WORKER-SPAWN-PATTERN (INV-PM-5, v3.2.0)

Jedes `Skill(_A_berater_X, args=...)` im Pseudocode unten ist KURZSCHRIFT fuer:

```
Agent(
  subagent_type="general-sonnet" | "general-haiku" | "general-purpose",
                                    # Tier laut Berater-Spec
  description="A-Pipeline Phase {N} {berater_name}",
  prompt="""
    Du bist kurzlebiger Worker fuer A-Pipeline Phase {N}.
    ENV: CLAUDE_BL_ID={bl_id}   # AK-9 (BL-364): bl_id explizit uebergeben (H3)

    AUFGABE: Lade Skill _A_berater_X via Skill-Tool und fuehre den dort
    definierten Vertrag aus mit args="{args}".

    REGELN:
    - W7-Constraint: KEIN Sub-Agent-Spawning durch dich.
    - Schreibe BERATER_OUTPUTS.{berater_name} ins _manifest.md.
    - SendMessage an "team-lead" mit Ergebnis-Summary.
    - Worker stirbt nach Skill-Ausfuehrung.
  """,
  team_name="a-{NAME}"
)
```

**Verbotene Anti-Pattern:**
- ❌ Team Lead ruft `Skill(_A_berater_X)` direkt auf → Direkt-Load
- ❌ Team Lead liest Skill-Markdown selbst und fuehrt aus
- ✅ Team Lead spawnt Worker via Agent(), Worker laedt Skill

**INV-MODUS-Reminder:** Worker darf modus-Feld NICHT setzen ausser via _SDF_berater_modusEntscheidung (BL-165 INV-MODUS-1).

---

## SYNC-DRIVE-DOKTRIN (AK-5, BL-364 H1 — Run-Card)

**Berater-Worker werden PLAIN (synchron) gespawnt — KEIN `team_name` in kompaktierten/geladenen Sessions.**

Hintergrund (H1-Beweis, BL-339-Lauf 2026-06-15): In kompaktierten oder lang laufenden Sessions
dominiert der Stop-Hook die async-Team-Mailbox. Worker-Reports kommen nicht beim Lead an
(Nondelivery) — die Pipeline haelt an, weil der Lead auf ein ACK wartet, das den Stop-Hook nie
passiert. Der 30+-Worker-Marathon ist turn-fuer-turn in solchen Sessions nicht fahrbar.

**Konsequenz fuer volles A→IDF→SDF-Pipeline-Bau:**
- In geladener/kompaktierter Session → Fresh-Session empfohlen (kein async-Overhead, sauberer Kontext)
- Wenn in laufender Session noetig: PLAIN `Agent(...)` OHNE `team_name` (synchroner Spawn;
  Stop-Hook trifft die Worker-Antwort direkt, kein Mailbox-Bypass-Problem)
- Async-Team (`team_name=...`) ist fuer frische, kurze Flows reserviert wo Stop-Hook-Dominanz
  nicht auftritt

**Doktrin:** Worker-Report-Nondelivery ist ein Session-Context-Problem, NICHT ein Framework-Bug.
Die richtige Antwort: Fresh-Session fuer volle Pipeline, PLAIN-Spawn als Fallback in geladener Session.
Beweis-Lauf: BL-364 F1 (2026-06-15, BL-339-A-Pipeline in geladener Session → Workers berichteten
nicht → Lead-Stall). Referenz: [[BL-364]] H1.

---

## WELLEN-SPAWN-KONTRAKT (BL-422 AK-2)

**Jede A-Pipeline-Welle (_spec, _K_score, _gap, etc.) wird als BENANNTES, sichtbares Team gespawnt — NIE als ein einziger anonymer Sub-Agent (Mega-Worker-Kollaps, INV-PM-5 / INV-AO-CALLER).**

Der Lead laedt jeden Wellen-Skill SELBST via Skill-Tool (Handschuh-Wechsel, INV-AO-CALLER). Wellen laufen als benannte team_name-Member mit TaskCreate(blockedBy)-DAG. Anonyme Einzel-Sub-Agent-Spawns fuer die ganze Welle sind VERBOTEN (INV-PM-5, guard_agent_prompt_validator AK-4). Fallback in geladener Session: PLAIN synchrone, scope-harte per-Phase-Worker ohne team_name — ABER NIE 1 anonymer Mega-Worker fuer alle Phasen (SYNC-DRIVE-DOKTRIN).

### Positive Pflicht: benannte Wellen-Member mit TaskCreate-DAG

difficulty skaliert die Wellen-Groesse:

| difficulty | Explorer | Drafter | Synthese |
|---|---|---|---|
| easy | — | — | 1 Synthese-solo |
| normal | 5 Explorer (E01-E05) | 3 Drafter (D01-D03) | 1 Synthese |
| hard | 9 Explorer (E01-E09) | 5 Drafter (D01-D05) | 1 Synthese |

**Spawn-Muster (normal, Beispiel _spec-Welle):**

```
# Explorer-Welle: 5 benannte Member
FOR i IN ["E01","E02","E03","E04","E05"]:
  Agent(name="spec-explorer-{i}", team_name="a-{name}", subagent_type="general-haiku",
        prompt="Explorer {i}: lies Primaerquelle X, extrahiere Teilaspekt ...")
  TaskCreate name="spec-explorer-{i}" status=IN_PROGRESS

# Drafter-Welle: 3 benannte Member, blockedBy Explorer
FOR j IN ["D01","D02","D03"]:
  Agent(name="spec-drafter-{j}", team_name="a-{name}", subagent_type="general-sonnet",
        prompt="Drafter {j}: synthetisiere Explorer-Outputs fuer Teilbereich ...")
  TaskCreate name="spec-drafter-{j}" blockedBy=["spec-explorer-E01",...,"spec-explorer-E05"]

# Synthese: 1 benannter Member, blockedBy Drafter
Agent(name="spec-synthese", team_name="a-{name}", subagent_type="general-sonnet",
      prompt="Synthese: konsolidiere alle Drafter-Outputs zu finalem Spec-Draft ...")
TaskCreate name="spec-synthese" blockedBy=["spec-drafter-D01","spec-drafter-D02","spec-drafter-D03"]
```

**Invarianten:**
- Jeder Member hat `name` + `team_name` (INV-VEHIKEL-3: "altmodisch" = benannte Member + Task-DAG + Deps)
- DAG-Abhaengigkeiten via `blockedBy` (Drafter blockedBy Explorer, Synthese blockedBy Drafter)
- Explorer = Haiku-Tier (Recherche/Extract), Drafter = Sonnet-Tier (Synthese), Synthese = Sonnet-Tier (Konsolidierung)
- Der Lead laedt den Wellen-Skill SELBST via Skill-Tool (INV-AO-CALLER: Handschuh-Wechsel, kein Sub-Agent-Delegieren)

### Verbot: Einzel-anonymer-Sub-Agent (INV-PM-5 / INV-AO-CALLER)

**VERBOTEN — Mega-Worker-Kollaps:**
- `Agent(prompt="Fuehre die gesamte Spec-Welle aus, alle Explorer+Drafter+Synthese")` → 1 anonymer Mega-Agent fuer alle Phasen
- `Agent(prompt="Lade _spec und schreibe den vollstaendigen Spec-Draft")` → kein Wellen-DAG, kein Team, kein Phase-Separation
- Kein `team_name` bei Wellen-Spawn → anonyme Einzel-Spawns werden von `guard_agent_prompt_validator` (AK-4) abgelehnt

**Begruendung:** DCSRE-1699 (Mega-Worker-Kollaps): 1 anonymer Sub-Agent fuer die ganze Welle macht alle Explorer/Drafter/Synthese-Phasen ohne Team, ohne BERATER_OUTPUTS-Trennung, ohne Phase-Separation. INV-PM-5 + INV-AO-CALLER fangen das nicht ab wenn der Lead selbst einen breit-formulierten Prompt schreibt.

### SYNC-DRIVE-Fallback (geladene Session)

In kompaktierten/geladenen Sessions (SYNC-DRIVE-DOKTRIN aktiv): PLAIN synchrone, scope-harte per-Phase-Worker OHNE `team_name` — aber weiterhin 1 Worker = 1 Phase = 1 Skill-Load. **NIE 1 anonymer Mega-Worker fuer alle Wellen-Phasen.** Die 1-Phase-pro-Worker-Regel gilt auch im PLAIN-Modus. (Verweis: SYNC-DRIVE-DOKTRIN unten.)

---

## MEGA-WORKER-SCOPE-KLÄRUNG (AK-6, BL-364 H2 — Worker-Task-Listen-Verbot)

**Worker darf NICHT die geteilte Team-Task-Liste als eigene Instruktion lesen.**

Klärung H2-Lesart: Die Audit-Signal-Analyse (audit_hook.py L275-291 TaskCreate-Event,
`description`-Feld) zeigt, dass TaskCreate-Descriptions den verbatim Lead-Text tragen.
Lesart (b) — Worker liest die gesamte Task-Liste als Selbst-Instruktion — ist das konservativ
zu verhütende Risiko (INV-AO-CALLER / INV-PM-5). Lesart (a) — reine Audit-Fehlattribution —
ist wahrscheinlich (kein falsches Verhalten im konkreten BL-339-Lauf belegt), aber strukturell
nicht beweisbar ohne weiteren Lauf-Beweis.

**Guard-Prinzip (konservativ, Lesart b):**
- Worker-Spawn-Prompt DARF keine kopierte Task-Listen aus dem Lead-Kontext enthalten
- Worker kennt AUSSCHLIESSLICH: seine Phase-ID, seinen Skill, seinen bl_id, W7-Constraint
- Scope = 1 Phase, 1 Skill-Load, 1 SendMessage-Report — nicht mehr
- Ein Worker der "alle 9 Berater-Phasen macht" ist ein Mega-Worker (INV-AO-CALLER-Verletzung),
  egal ob durch Task-Listen-Kopie oder durch direktes Pseudocode-Interpretieren ausgeloest

**Symptom (BL-364 H2, F5):** Wenn ein Worker-Spawn-Prompt die Lead-Task-Liste als Instruktion
enthält, kann der Worker seinen Scope auf alle Phasen ausweiten (implizit: "das sind meine Tasks").
Fix: Worker-Prompts sind scope-hart (1 Phase), keine Task-DAG-Kopien. Referenz: [[BL-364]] H2,
[[INV-AO-CALLER]], [[INV-PM-5]].

---

## ORCHESTRATOR-PSEUDOCODE

```
ENTRY:
  args = parse_args($ARGUMENTS)   # name, modus, difficulty, ceiling, floor, mode, parent-pr, entry-point, scope
  # ─── BL-234 AK-2: per-BL Session-Params fuellen JEDEN nicht explizit uebergebenen Param ───
  # Explizite $ARGUMENTS GEWINNEN (Owner-Direktive); fehlende werden per-BL aufgeloest
  # (BL > Vault > Framework, BL-174-Resolver). Der Resolver extrahiert die Ticket-ID aus
  # dem Namen selbst, daher reicht args.name:
  #   resolved = `py -3 .claude/scripts/session_params_resolver.py resolve-all --bl-id={args.name}`
  #   FOR p IN [difficulty, ceiling, floor, hil]: IF args.p in (None,"","auto") -> args.p = resolved[p]
  # Resolver-Fehler/leer -> bisheriges FLACHES Verhalten ({VAULT}/_session_params.md / Defaults),
  # damit Worktrees ohne per-BL-Datei (z.B. 486) unveraendert laufen (additiv, kein Downgrade).
  args = fill_absent_params_per_bl(args, resolver_bl_id=args.name)
  Logge: "[A] ENTRY name={args.name} modus={args.modus} mode={args.mode}"

# ─── Stufe 1: Cleanup (INV-LIFECYCLE-1) ─────────────────────────────
active_team = Read(_manifest.md).BDF_PIPELINE_STATE.active_team
IF active_team != null AND active_team != "a-{args.name}":
  Logge: "[A Stufe 1] Cleanup altes Team: {active_team}"
  Sende shutdown_request, warte ACK, TeamDelete team_id={active_team}
  Set _manifest.md.BDF_PIPELINE_STATE.active_team = null
# BL-349 HINWEIS: Manifest.active_team ist NICHT die einzige Wahrheit — der Zombie sitzt oft im
# SESSION-Kontext (Manifest<->Session-Drift). Der echte Recovery-Punkt ist die Stufe-2-TeamCreate
# unten (INV-TEAM-GC-2).

# ─── Stufe 2: TeamCreate (INV-LIFECYCLE-2) ──────────────────────────
TeamCreate team_id="a-{args.name}" purpose="A-Pipeline {args.name} ({args.modus})"
# BL-349 AK-2 / INV-TEAM-GC-2 (Team-Transition-Recovery, reaktiv + concurrency-safe):
# Scheitert TeamCreate mit "Already leading team X" -> X gehoert DIESEM Lead-Kontext (Harness sagt es;
# nie ein Peer-Team) -> `py .claude/scripts/team_gc.py strip X` -> TeamDelete X -> TeamCreate erneut.
# (Protokoll-Home: team_gc.py-Docstring. team_gc strippt nur config-Records, TeamDelete loescht Dirs.)
Set BDF_PIPELINE_STATE.active_team = {name: "a-{args.name}", pipeline: "a", created: ISO_NOW()}

# ─── Team-Kontext-Resilienz (BL-422 AK-3) ───────────────────────────
# Bei TeamCreate-Re-Establishment / Session-Drift: bevorzugt RE-ATTACH an das bestehende
# Team statt Neu-Anlage, damit das Task-Board NICHT verloren geht.
#
# Re-Attach-Strategie (Session-Drift-Fall):
#   1. Pruefe ob Team "a-{args.name}" noch LIVE im Harness-Kontext existiert
#      (Fehler "Already leading team a-{args.name}" = Harness sagt: Team IS noch da)
#   2. WENN Team noch da -> RE-ATTACH (kein strip/recreate): Das Task-Board
#      (TaskCreate-DAG der Wellen-Phasen) bleibt erhalten — re-attach statt recreate.
#      Kein TaskCreate-Neubau noetig; bestehende Task-IDs sind weiter gueltig.
#   3. ERST wenn re-attach unmoeglich (Team wirklich weg, Harness hat keinen Record) ->
#      BL-349 strip+recreate-Recovery als Fallback (INV-TEAM-GC-2 oben).
#
# Task-Board-Persistenz: Das Task-Board ueberlebt Kontext-Wachstum und Re-Establishment
# solange re-attach moeglich ist. "Task-Board verloren" ist der LETZTE Ausweg (Fallback).
#
# Invariante: INV-PM-5 (kein Mega-Agent) + INV-AO-CALLER bleiben unberuehrt —
# re-attach aendert nichts an der Team-Member-Spawn-Disziplin.

# ─── BL-089 Dry-Run-Short-Circuit ───────────────────────────────────
IF args.mode == "dryRun":
  write_dry_run_report(args, ".claude/output/A_Pipeline_DryRun_{name}_{DATE}.md")
  Set A_PIPELINE_STATE.phase = "DRY_RUN_DONE"
  GOTO Stufe 6

# ─── Stufe 3: Modus-Erkennung (INV-LIFECYCLE-3) ─────────────────────
Skill(_A_berater_modusErkennung, args="{args.name} {args.modus}")
# modusErkennung: liest _session_params (GLOBAL_HIL, difficulty/ceiling/floor),
# bestimmt autonomie_modus (puppet_master/semi_autonom/minimal_hil/interaktiv),
# Auto-Detect FRESH vs RESYNC (Model+Task.md vorhanden -> resync), Git-Baseline.
# Output -> BERATER_OUTPUTS.modusErkennung.{modus, autonomie, git_baseline}

modus = BERATER_OUTPUTS.modusErkennung.modus
autonomie = BERATER_OUTPUTS.modusErkennung.autonomie

# ─── Stufe 4: Tasks vorab (INV-LIFECYCLE-4) ─────────────────────────
TaskCreate name="phase-0-1-modusErkennung"     status=DONE  # bereits durch Stufe 3 erledigt
TaskCreate name="phase-0-2-discovery"          depends_on=["phase-0-1-modusErkennung"]
TaskCreate name="phase-0-5-findingsExtraction" depends_on=["phase-0-2-discovery"]   # nur fresh
TaskCreate name="phase-0-5-2-findingsReview"   depends_on=["phase-0-5-findingsExtraction"]
TaskCreate name="phase-0-5-3-domainBrief"      depends_on=["phase-0-5-2-findingsReview"]  # BL-254 NEU
TaskCreate name="phase-0-6-taskDefinition"     depends_on=["phase-0-5-3-domainBrief"]     # NEU FRUEH
TaskCreate name="phase-1-5-gitAnalyse"         depends_on=["phase-0-6-taskDefinition"]    # optional pr=true
TaskCreate name="phase-2-iddContext"           depends_on=["phase-1-5-gitAnalyse"]
TaskCreate name="phase-2-5-wfetch"             depends_on=["phase-2-iddContext"]          # VOR Model
TaskCreate name="phase-3-model"                depends_on=["phase-2-5-wfetch"]            # GUARD INV-A-ORDER-4
TaskCreate name="phase-4-spec"                 depends_on=["phase-3-model"]
TaskCreate name="phase-4k-kscore"              depends_on=["phase-4-spec"]
TaskCreate name="phase-4g-gap"                 depends_on=["phase-4k-kscore"]
TaskCreate name="phase-5a-specParse"           depends_on=["phase-4g-gap"]          # BL-197 NEU
TaskCreate name="phase-5b-akExtraktion"        depends_on=["phase-5a-specParse"]    # BL-197 NEU
TaskCreate name="phase-5c-plAggregation"       depends_on=["phase-5b-akExtraktion"] # BL-197 NEU
TaskCreate name="phase-4-2a-metadaten"         depends_on=["phase-5c-plAggregation"]
TaskCreate name="phase-4-4-gitTracking"        depends_on=["phase-4-2a-metadaten"]
TaskCreate name="phase-4-3-stateMaintain"      depends_on=["phase-4-4-gitTracking"]
TaskCreate name="phase-5d-arc42"               depends_on=["phase-4-3-stateMaintain"]      # BL-378 arc42-Sichten (NON-BLOCKING, vor Routing)
TaskCreate name="phase-5-routing"              depends_on=["phase-5d-arc42"]               # LAST

# ─── Stufe 5: Phasen-Ausfuehrung ────────────────────────────────────

# ═══ PHASE 0.2: DISCOVERY (Auto-Name-Ableitung, --parent-pr-Validierung) ═══
IF args.name == "auto":
  Skill(_A_berater_discovery, args="{args.name} {args.parent_pr}")
  # discovery: Keyword-Extraktion (4 Quellen) -> _W_fetch easy -> anchor_nodes
  # discovery: 3 Szenarien (auto-accept >=0.85, Tabelle, Fallback)
  # discovery: --parent-pr-Validierung (lokal + remote git-Check)
  # Output -> BERATER_OUTPUTS.discovery.{derived_name, idd_active, parent_pr_valid}
  args.name = BERATER_OUTPUTS.discovery.derived_name
TaskUpdate name="phase-0-2-discovery" status=DONE

# ═══ PHASE 0.5: FINDINGS-EXTRACTION (File-Iteration ueber pileOfMud) ═══
# F38-Fix 2026-05-08 (User-Direktive): Pro pileOfMud-Datei EIN Worker-Spawn (Stateless, W7-konform).
# - Keine 3-Drafter-Welle mehr (weicht von easy-Skalierung ab, war Drift).
# - difficulty wirkt pro-File: easy=1 Sonnet-Worker, normal/hard koennen spaeter mehr Drafter pro File spawnen.
# - User-Vision: "der gesamte Inhalt der pileOfMud wird analysiert, eine Datei nach der anderen".
IF modus == "fresh":
  # 2026-06-01: Extrahierbar = Text + alles was Claude via Read DIREKT lesen kann
  # (Bilder + PDF — visuell). NUR Audio/Video/Binaer bleibt nicht-extrahierbar (kein
  # Transkriptions-/Decode-Step). Nicht-Extrahierbares wird NICHT still gedroppt,
  # sondern LAUT gemeldet ("No silent caps"). /_backlog akzeptiert auch Audio/Bilder.
  EXTRACTABLE_EXT = [".md", ".txt", ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".pdf"]
  pile_all     = Glob(".claude/pileOfMud/*")
  pile_all     = [f FOR f IN pile_all IF BASENAME(f) NOT IN [".gitignore", ".gitkeep"]]
  pile_files   = [f FOR f IN pile_all IF ANY(lower(f).endswith(ext) FOR ext IN EXTRACTABLE_EXT)]
  pile_skipped = [f FOR f IN pile_all IF f NOT IN pile_files]   # Audio/Video/sonstiges Binaer

  # ═══ BL-346 AK-1: pileOfMud-RELEVANZ-GATE (vor Extraktion) ═══════════════
  # PROBLEM (Live-Fall 2026-06-14, BL-282-Launch): die obige Glob nimmt ALLES was im
  # Briefkasten liegt — auch Material ANDERER Sessions/BLs. Ohne Gate haette die A-Pipeline
  # 5 BL-282-fremde Files als BL-282-Findings mis-extrahiert (stiller Garbage).
  # RELEVANZ-WAHRHEIT: /_backlog snapshottet die fuer DIESEN BL gedroppten Pile-Files nach
  #   {bl_folder}/Sources/_pileOfMud_snapshot/ MIT source_provenance.original_hash. Relevant =
  #   Live-Files, deren Basename (+ Inhalts-Hash, wenn vorhanden) im Snapshot wiedergefunden wird.
  # ABWAERTSKOMPAT: ein frisches Intake-BL hat den Snapshot == die eben gedroppten Files
  #   -> alle relevant -> fresh-pile-Pfad laeuft UNVERAENDERT. Der Gate filtert NUR Fremdes.
  bl_folder = subprocess(".claude/scripts/resolve_bl_path.py", args.name).stdout.strip()
  rel       = py(".claude/scripts/pile_relevance.py").partition_pile_by_relevance(bl_folder, pile_files)
  IF |rel.foreign| > 0:
    # "No silent caps" (Muster wie pile_skipped): Fremd-Material LAUT melden, NICHT extrahieren.
    LOG: "[A_FX] WARN BL-346 Relevanz-Gate — {|rel.foreign|} Pile-File(s) NICHT diesem BL "
         "({args.name}) zuordenbar (snapshot_present={rel.snapshot_present}): "
         "{[e.path + ' [' + e.skip_reason + ']' FOR e IN rel.foreign]}. "
         "→ werden NICHT zu BL-Findings (fremde Session / consolidated EPIC)."
  pile_files = rel.relevant   # ab hier NUR noch die dem BL zugeordneten Files

  # ═══ BL-346 AK-2: MATURE-CONSOLIDATED-EPIC-CARVE-OUT ════════════════════
  # Ein reifer, konsolidierter Vault-EPIC (needs_a_pipeline ABER 0 relevante Pile-Files,
  # reicher in-Node-AK-Cluster, superseded-Sources — z.B. BL-282 merged BL-240/249/250/263)
  # bricht das fresh-pile-Intake-Modell: seine Quelle ist NICHT pileOfMud, sondern der Node
  # selbst + die superseded Nodes. KEIN Garbage-Extract aus fremdem Pile.
  node_text = exists("{bl_folder}/../{args.name}*.md") ? Read(bl_huelle) : null
  IF |pile_files| == 0 AND py(".claude/scripts/pile_relevance.py").is_mature_consolidated_epic(
       relevant_count=0, node_text=node_text,
       node_ak_count=count_aks_in_node(node_text), has_superseded=node_has_superseded(node_text)):
    LOG: "[A_FX] BL-346 AK-2 — {args.name} ist mature consolidated EPIC (0 relevante Pile-Files, "
         "reicher AK-Cluster, superseded-Sources). Findings-Quelle = Node + superseded Nodes, "
         "NICHT pileOfMud. → findingsExtraction liest Node-AKs/superseded statt fremdem Pile "
         "(ODER route zu IDF-grade Refinement). KEIN Garbage-Extract."
    # findingsExtraction-Spawn unten bekommt --source=node (Node+superseded als Quelle).
    # KEIN pileOfMud-Iteration fuer diesen BL — die Relevanz-Wahrheit sagt: kein eigenes Pile-Material.

  IF |pile_skipped| > 0:
    # NUR noch echte Nicht-Lesbare (Audio/Video). Bilder + PDF werden jetzt extrahiert (Read visuell).
    LOG: "[A_FX] WARN — {|pile_skipped|} Pile-File(s) NICHT extrahierbar (Audio/Video/Binaer): {pile_skipped}. "
         "→ werden NICHT zu Findings (kein Transkriptions-/Decode-Step). Audio erst zu .md/.txt transkribieren, dann re-run. "
         "Vault-Snapshot bleibt erhalten, aber inhaltlich gehen sie NICHT in die Findings-Extraction."
    IF args.hil != "off":
      AskUserQuestion: "{|pile_skipped|} nicht-extrahierbare Pile-File(s) (z.B. Audio): {pile_skipped}. "
                       "Fortfahren NUR mit den {|pile_files|} md/txt-Files — oder erst transkribieren + re-run?"
      # [Fortfahren] → weiter mit pile_files   [Abbrechen] → STOP, User transkribiert zuerst
  IF |pile_files| == 0:
    IF |pile_skipped| > 0:
      LOG: "[A_FX] STOP-HINT — pileOfMud enthaelt NUR nicht-extrahierbare Files ({pile_skipped}). "
           "Keine Findings moeglich → erst transkribieren."
    LOG: "[A_FX] WARN pileOfMud leer (keine md/txt) — Fallback Berater spawnt User-Dialog"
    Skill(_A_berater_findingsExtraction, args="{args.name} {args.difficulty} {args.ceiling}")
  ELSE:
    # ─── BL-235 Asymptotic Findings Engine (PREFERRED; ersetzt 1-Pass+dedup-0.85 ATOMAR, AK-9) ───
    # Deterministischer Findings-Motor: loop-until-dry (Hard-Cap 3, DeltaCORE==0) -> cleancoder-Cluster
    # (CORE/BORDER) -> Timeline-Gewicht -> Valenz/Pruning -> CORE-Destillat oben + BORDER-Anhang.
    # AK-8 als WORKFLOW (NICHT in-Skill-Pseudocode) => Mega-Worker strukturell unmoeglich (BL-222/FIX2-Lehre).
    # Source-only, wirkt erst bei Redeploy (F-REDEPLOY-DRIFT). Fallback = klassische File-Iteration darunter.
    fx = Workflow(name="dispatch_findings", args={bl_id: args.name, pile_files: pile_files})
    engine_master_written = false
    IF fx != null AND fx.findings_core != null:
      # write_findings_crumbs_core_border (BL-267 DEFINITION — war zuvor undefinierter Pseudocode-Helper):
      #   Write("{bl_folder}/Crumbs/{name}_findings_crumbs.md", render(
      #     frontmatter{type:"findings_crumbs", feature:name, status:"draft", source:"bl235_engine",
      #                 core_count:|core|, border_count:|border|, pruned_count:|pruned|},
      #     body = "## CORE (gerankt)\n" + render_findings(core, with_weight=true)        # CORE oben, headline-faehig
      #          + "\n## BORDER (Anhang)\n" + render_findings(border)
      #          + "\n## PRUNED (dokumentiert)\n" + render_pruned(pruned)))
      #   DIE Datei, die findingsReview Checkpoint A liest. AK-11: CORE-Rang/weight bleibt Sortier-Signal.
      write_findings_crumbs_core_border(fx.findings_core, fx.findings_border, fx.pruned)
      # ─── BL-267 SEAM-FIX: Engine-Pfad produziert das Destillat DIREKT als Master (Ranking erhalten). ───
      # Der Multi-File-consolidate (unten) globt {derived_name}_*_findings_crumbs.md = die FALLBACK-per-File-
      # Crumbs, die hier NICHT existieren (ELSE-Zweig lief nicht) -> frueher: 0 Crumbs -> EXIT 2 FAIL ->
      # Master NIE gebaut, BL-235-Destillat verworfen (tote Naht, BL-267). Jetzt: Master direkt schreiben.
      Write("{bl_folder}/Crumbs/{derived_name}_findings_crumbs_master.md", render(
        frontmatter{type:"findings_crumbs_master", feature: derived_name, status:"draft", source:"bl235_engine",
                    findings_total: |fx.findings_core| + |fx.findings_border|, files_consolidated: 0,
                    bl235_rounds: fx.rounds, bl235_clusters: fx.cluster_count},
        body = render_findings(fx.findings_core, with_weight=true) + render_findings(fx.findings_border)))
      engine_master_written = true
      LOG: "[A_FX] BL-235-Engine: {fx.raw_count} roh -> {|fx.findings_core|} CORE + {|fx.findings_border|} BORDER ({fx.rounds} Runden, {fx.cluster_count} Cluster); Master direkt geschrieben (BL-267 Seam-Fix)."
    ELSE:
      # ─── Fallback (klassisch, pre-BL-235): File-Iteration pro pileOfMud-Datei ───
      FOR file IN pile_files:
        Skill(_A_berater_findingsExtraction, args="{args.name} {args.difficulty} {args.ceiling} --file={file}")
      # Pro File: Pattern-Match + LLM-Reasoning (Single-Worker), Crumbs file-spezifisch geschrieben
      #   -> {bl_folder}/Crumbs/{derived_name}_{file_basename}_findings_crumbs.md (status=draft)
    END
    # Final-Konsolidierung NUR im Fallback-Pfad (BL-267): der Engine-Pfad hat den Master schon DIREKT geschrieben
    # (Ranking erhalten). Der consolidate globt die Fallback-per-File-Crumbs — im Engine-Pfad gibt es keine,
    # und ein Lauf dort wuerde am 0-Crumbs-EXIT-2 scheitern (die alte tote Naht).
    IF NOT engine_master_written:
      Skill(_A_berater_findingsExtraction, args="{args.name} {args.difficulty} {args.ceiling} --mode=consolidate")
      #   -> {bl_folder}/Crumbs/{derived_name}_findings_crumbs_master.md (status=draft)
  # findingsExtraction MODELL (2026-06-01 User-Direktive "Intelligenz NIE downgraden"):
  #   Der Berater DEKLARIERT model_tier=opus (Frontmatter) — Findings sind intelligenz-tragend:
  #   Foundation der GANZEN Analyse + Visual-PNG-Reasoning + latente Findings (analog _A_berater_specParse=opus).
  #   extraction_model = max( min(opus, GLOBAL_CEILING), GLOBAL_FLOOR )  → bei ceiling=opus: OPUS.
  #   → ALLE obigen Skill(_A_berater_findingsExtraction)-Spawns laufen auf diesem Tier (default OPUS).
  #   SPAWN: Carrier-Agent (general-sonnet/general-purpose) MIT model:opus-Override — NICHT "general-opus"
  #          (existiert nicht / registriert nicht). Ref: reference_model_routing_canonical.
  #   INV-EXTRACT-1: nie UNTER sonnet (haiku verboten). Das alte "extraction_floor = max(floor, sonnet)" war ein
  #   FALSCHER Downgrade opus→sonnet — der DEKLARIERTE Berater-Tier GEWINNT, nur gecappt durch ceiling.
  # Output -> BERATER_OUTPUTS.findingsExtraction.alle_findings (konsolidiert)
TaskUpdate name="phase-0-5-findingsExtraction" status=DONE

# ═══ PHASE 0.5.2: FINDINGS-REVIEW (Checkpoint A) ═══
# NEUER STANDARD-PATTERN bei HiL=on (v3.2.0, CaseStudy SemantischePatternLibrary):
#   1. PARALLEL-ASSAYS: pro Finding 1 Sonnet-Worker via Skill(_assay) — bis 10 parallel.
#   2. KONSOLIDIERUNG: Master-Doku in {VAULT}/Backlog/{FEATURE}/Findings_Assays_Konsolidiert_{DATE}.md
#   3. /fullPath ausgeben (User-Klick-Pfad ins Master-Doku).
#   4. /_question EINZELN pro Finding (nicht 4er-Batch — Tiefe vor Tempo).
# Bei HiL=off: Auto-Confirm aller Findings (K5-Fix konservativ, kein Pattern).
# Volle Logik im Berater (`.claude/commands/_A_berater_findingsReview.md`).
IF modus == "fresh":
  Skill(_A_berater_findingsReview, args="{args.name}")
  # Output -> BERATER_OUTPUTS.findingsReview.{
  #   hil_used, items_total, assays_path, master_doc_path, questions_path,
  #   verdicts: {uebernehmen, praezisieren, dismiss}, last_berater
  # }
TaskUpdate name="phase-0-5-2-findingsReview" status=DONE

# ═══ PHASE 0.5.3: DOMAIN-BRIEF (BL-254 — DomainLibrary-Konsultation vor Model/AKs) ═══
# Zwilling von _SDF_berater_patternBrief (Pattern @SDF/I), hier Domaene @A: confirm-or-add-or-contradict.
# Konsultiert die DomainLibrary mit den frischen Findings -> matched_domain (wiederverwenden, kein Doppel),
# new_candidates (neue Domaenen-Wahrheiten), contradictions (HiL). NON-BLOCKING (leere Lib -> no_match=true).
# Downstream nutzen specParse/akExtraktion matched_domain fuer Reuse statt Neu-Erfindung.
Skill(_A_berater_domainBrief, args="{args.name}")
# Output -> BERATER_OUTPUTS.domainBrief.{matched_domain, new_candidates, contradictions, no_match, brief_summary}
TaskUpdate name="phase-0-5-3-domainBrief" status=DONE

# ═══ PHASE 0.6: TASK-DEFINITION (NEU FRUEH, vor Model/W_fetch — INV-A-ORDER-1) ═══
# Begruendung RF-A-ORDER: taskDefinition liefert die Aufgabe-Klarheit, die W_fetch
# als Such-Kontext braucht. Frueher Phase 2 (nach W_fetch) -> jetzt Phase 0.6.
Skill(_taskDefinition, args="{args.name} {args.difficulty} {args.ceiling} {args.floor}")
TaskUpdate name="phase-0-6-taskDefinition" status=DONE

# ═══ PHASE 1.5: GIT-ANALYSE (optional pr=true) ═══
# Begruendung: Bei PR-Aufgaben ist Git-State Teil der Wissensbasis.
# Snapshot offener PRs / Branch-Diff / PR-Reviews -> .claude/git-state/
# Konsumenten: Phase 2 iddContext (Diff-Analyse), spaeter SDF/I.
IF args.pr == true:
  Skill(_git_analyse, args="{args.name}")
  # git_analyse: PR-Status, Branch-Diff, Commit-History, offene Reviews
  # Output -> BERATER_OUTPUTS.gitAnalyse.{pr_state, branch_diff, drift}
TaskUpdate name="phase-1-5-gitAnalyse" status=DONE

# ═══ PHASE 2: IDD-CONTEXT (NUR --parent-pr, Interface-Extraktion) ═══
IF BERATER_OUTPUTS.discovery.idd_active OR args.parent_pr != null:
  Skill(_A_berater_iddContext, args="{args.name} {args.parent_pr}")
  # iddContext: haiku-Worker fuer git-Diff-Analyse (Interfaces, StableTypes, MergeRisks)
  # iddContext: Schreibt .claude/merge-instructions/{name}-idd-context.md
  # Output -> BERATER_OUTPUTS.iddContext.{interfaces, stable_types, merge_risks}
TaskUpdate name="phase-2-iddContext" status=DONE

# ═══ PHASE 2.5: W_FETCH (VOR Model — Wissensbasis fuer Model-Bau) ═══
# Begruendung RF-A-ORDER: Model muss existierendes Vault-Wissen kennen
# bevor es neue W{n}-Knoten baut, sonst Wissens-Drift.
Skill(_W_fetch, args="{args.name} {args.difficulty} {args.ceiling} {args.floor}")
TaskUpdate name="phase-2-5-wfetch" status=DONE

# ═══ PHASE 3: MODEL (modus-abhaengig: _model fresh, _SC_modelMaintain resync) ═══
# GUARD INV-A-ORDER-4 (v3.2.0): Pre-Check vor Skill-Call
wfetch_status = manifest_reader.read_bl_block(bl_id, "BERATER_OUTPUTS.wfetch.status") ?? "MISSING"
IF wfetch_status != "DONE":
  Logge: "[A GUARD INV-A-ORDER-4] Phase 3 model abgebrochen: wfetch.status={wfetch_status}"
  ABORT("INV-A-ORDER-4: Model-Phase ohne W_fetch DONE — Wissensbasis fehlt")

IF modus == "fresh":
  Skill(_model, args="{args.name} {args.difficulty} {args.ceiling} {args.floor}")
ELSE:  # resync
  Skill(_SC_modelMaintain, args="{args.name} {args.difficulty}")
TaskUpdate name="phase-3-model" status=DONE

# ═══ PHASE 4: SPEC (Checkpoint B mit AK-Review) ═══
# Bei HiL=on: AK-Review nutzt DENSELBEN Standard-Pattern wie Phase 0.5.2 (v3.2.0):
#   PARALLEL-ASSAYS pro AK → KONSOLIDIERUNG → /fullPath → /_question EINZELN.
# Logik im selben Berater (oder Schwester-Berater _A_berater_specReview), Pattern
# ist wiederverwendbar (DRY, INV-HIL-5 in _A_berater_findingsReview).
spec_loop = true
WHILE spec_loop:
  Skill(_spec, args="{args.name} {args.difficulty} {args.ceiling} {args.floor}")
  IF modus == "fresh" AND autonomie != "puppet_master":
    # HiL AK Review — STANDARD-PATTERN aus _A_berater_findingsReview (HiL=on Modus)
    # 1. Parallel-Assays pro AK (Sonnet, bis 10 parallel)
    # 2. Master-Doku: {VAULT}/Backlog/{FEATURE}/AK_Assays_Konsolidiert_{DATE}.md
    # 3. /fullPath ausgeben
    # 4. /_question pro AK EINZELN (mit Assay-Block im question-Feld)
    korrekturen = run_hil_review_pattern(spec_path, item_type="AK")
    IF |korrekturen| > 0:
      Skill(_spec, args="{args.name} --korrektur=true")  # Re-run mit Korrekturen
      CONTINUE
  spec_loop = false
TaskUpdate name="phase-4-spec" status=DONE

# ═══ PHASE 4k: K-SCORE (BL-129 + RF-A5, pro AK Detail-Bewertung) ═══
# RF-A5: K-SCORE.md schreibt pro AK K-Score (k_score_pro_ak) + anchors + model_refs
#        (Detail-Aufloesung statt nur globaler k_score-Wert).
#
# ═══ BL-312 AK-2 — SRS-ENTKERNUNG aus A-4k (K BLEIBT, deferred AK-10/BL-311) ═══
# WO-Verlagerung (BL-312): A Phase 4k ist NICHT mehr SRS-Bewertungs-Ort.
#   SRS-QUELLE = IDF Phase 3.8 plBewertung (per_pl_evaluation) — ERST+EINZIG-SRS-Rechner
#               (BL-312 AK-1). A schreibt KEINEN srs_pro_ak / srs-Frontmatter-Map mehr.
#               (Beseitigt den srs=0-uniform-Drift: vor BL-312 schrieb A-4k srs_pro_ak=0
#               uniform, IDF flippte via INV-BC-1 auf 100 → 3 widerspruechliche SRS-Quellen.
#               Jetzt genau 1 SRS-Ort = IDF 3.8 per_pl_evaluation, keine A-SRS-Doppelung.)
#   K-QUELLE   = WEITERHIN A-4k (k_score_pro_ak) — die K-Migration nach IDF ist
#               DEFERRED an AK-10/BL-311 (Code-K-Skala muss erst kanonisiert werden,
#               sonst reproduziert sich die Doppelungs-Drift am heissesten Code-Target).
#               _K_score bleibt unveraendert die K-Engine; A ruft es weiter NUR fuer K.
#   UEBERGANGS-KOMPAT (1 Release, Dual-Quelle): A-4k K-SCORE.md fuehrt den K-Block
#               (k_score_pro_ak) weiter, damit metricPlanner (BL-312 AK-3) waehrend der
#               Migration nicht orphant laeuft. BL-266-Contract-Test schuetzt das Schema.
#   _K_score selbst (Engine) ist NICHT geloescht und NICHT geaendert — nur der A-seitige
#   SRS-Output-Pfad faellt; der SRS-Anteil aus K-SCORE.md ist downstream-irrelevant
#   (metricPlanner liest SRS ab AK-3 aus per_pl_evaluation, nicht mehr aus srs_pro_ak).
Skill(_K_score, args="{args.name} {args.difficulty} {args.ceiling} {args.floor}")
TaskUpdate name="phase-4k-kscore" status=DONE

# ═══ PHASE 4g: GAP-Analyse ═══
Skill(_gap, args="{args.name} {args.difficulty} {args.ceiling} {args.floor}")
TaskUpdate name="phase-4g-gap" status=DONE

# ═══ PHASE 5a: SPEC-PARSE (BL-197 NEU — INV-A-ORDER-5) ═══
# Begruendung BL-197: A-Pipeline muss Spec parsen bevor PL-Items erzeugt werden.
# GUARD INV-A-ORDER-5: Phase 5a nur nach gap.status=DONE
gap_status = BERATER_OUTPUTS.gap.status ?? "MISSING"
IF gap_status != "DONE":
  ABORT("INV-A-ORDER-5: Phase 5a specParse ohne gap DONE — Reihenfolge verletzt")
Logge: "[A Phase 5a] specParse — Spec strukturiert extrahieren"
Skill(_A_berater_specParse, args="{args.name}")
# specParse: liest Vault-Spec Vault-First (3_Spec/ oder lokal Fallback)
# specParse: extrahiert sections[], aks[], rfs[]
# Output -> BERATER_OUTPUTS.specParse.{sections, aks, rfs, aks_count, status=DONE}
Set A_PIPELINE_STATE.phase = "PHASE_5A_DONE"
TaskUpdate name="phase-5a-specParse" status=DONE

# ═══ PHASE 5b: AK-EXTRAKTION (BL-197 NEU — INV-A-ORDER-6, sequenziell per OQ-3) ═══
# GUARD INV-A-ORDER-6: Alle akExtraktion-Worker abgeschlossen vor Phase 5c
Logge: "[A Phase 5b] akExtraktion — PL-Draft pro AK erzeugen"
ak_list = BERATER_OUTPUTS.specParse.aks   # aus Phase 5a
IF ak_list == null OR |ak_list| == 0:
  ABORT("Phase 5b: specParse.aks leer — Phase 5a Ergebnis pruefen")
FOR ak IN ak_list:
  Skill(_A_berater_akExtraktion, args="{args.name}|{ak.id}")
  # akExtraktion: liest Spec-Section gezielt (via line_start/line_end aus 5a)
  # akExtraktion: erzeugt pl_item_draft pro AK
  # Output -> BERATER_OUTPUTS.akExtraktion[ak.id].{pl_item_draft, status}
  # INV-AKE-1: Per-AK Schreib-Isolation — kein Cross-AK-Write
END
Set A_PIPELINE_STATE.phase = "PHASE_5B_DONE"
TaskUpdate name="phase-5b-akExtraktion" status=DONE

# ═══ PHASE 5c: PL-AGGREGATION (BL-197 NEU — INV-PL-1) ═══
# INV-PL-1: PL_Master existiert erst NACH Phase 5c
Logge: "[A Phase 5c] plAggregation — PL_Master.md erzeugen"
Skill(_A_berater_plAggregation, args="{args.name}")
# plAggregation: liest BERATER_OUTPUTS.akExtraktion.* (alle AK-Drafts aus 5b)
# plAggregation: erzeugt {VAULT}/Backlog/{BL_SLUG}/6_PL/{BL_ID}-parking-lot.md
# plAggregation: setzt plAggregation.pl_pre_filled = true (Signal fuer IDF AK-6/AK-8)
# Output -> BERATER_OUTPUTS.plAggregation.{pl_master_path, item_count, status, pl_pre_filled=true}
Set A_PIPELINE_STATE.phase = "PHASE_5C_DONE"
Set BERATER_OUTPUTS.plAggregation.status = "DONE"
Set BERATER_OUTPUTS.plAggregation.pl_pre_filled = true
# BL-197 AK-7 downstream: A_PIPELINE_STATE.pl_pre_filled_after signalisiert IDF
# dass Phase 2/3.1/3.2 SKIP (INV-IDF-SKIP-1 in _IDF_orchestrate.md Phase 0.9).
# Wird von _A_berater_routing in BERATER_OUTPUTS.routing.pl_pre_filled gespiegelt.
Set A_PIPELINE_STATE.pl_pre_filled_after = true
TaskUpdate name="phase-5c-plAggregation" status=DONE

# ═══ PHASE 4.2a: METADATEN-AGGREGATION (RF-A-RENAME + RF-A6 + Backlog-Item-Erzeugung) ═══
# Frueher: Phase 4.2a (COMPLEXITY_STATE init) + 4.2b inline.
# RF-A-RENAME: Umbenannt von COMPLEXITY_STATE init -> Metadaten-Aggregation.
# Jetzt: Berater macht NUR Aggregation + setzt backlog_spawn_required=true (W7/INV-MA-4);
#        der ORCHESTRATOR ruft danach /_backlog (Node-Writer inkl. RF-A6) — siehe unten.
#
# Backwards-Compat (1 Release): Berater schreibt PARALLEL beide Feldgruppen:
#   NEU (Schema, RF-A-RENAME): aggregat_k_score, aggregat_srs_score,
#     aggregat_gap_percent, aggregat_model_maturity, aggregat_freiheitsgrade,
#     aggregat_is_meta_command
#   DEPRECATED (alte Caller): complexity_k_score, complexity_srs_score,
#     complexity_gap_percent, complexity_model_maturity, complexity_freiheitsgrade,
#     complexity_is_meta_command  -> nach Phase 5 Caller-Migration ENTFERNEN.
#
# DEPRECATED: A_PIPELINE_STATE.recommendation wird NICHT mehr geschrieben (=null).
# Mode-Decision lebt jetzt in SDF C3 _SDF_berater_modusEntscheidung; alte
# Caller bekommen recommendation=null und MUESSEN auf SDF-Mode-Decision migrieren.
#
# RF-A6: BL-Item-Frontmatter erweitert um:
#   ak_anchors (Liste der AK-Anker-Namen),
#   srs_per_ak (Map AK -> SRS-Score),
#   k_score_per_ak (Map AK -> K-Score-Komponenten).
#
Skill(_A_berater_metadatenAggregation, args="{args.name}")
# metadatenAggregation: AGGREGAT-Felder schreiben (NEU + DEPRECATED parallel)
# metadatenAggregation: setzt A_PIPELINE_STATE.backlog_spawn_required=true (INV-MA-4) — ruft /_backlog
#                       NICHT selbst (W7-Compliance)
# metadatenAggregation: liefert reifegrad (REIF/UNREIF/SC-REIF) aus gap+modellreife
# Output -> BERATER_OUTPUTS.metadatenAggregation.{aggregat_state, reifegrad}

# ─── INV-MA-4-Consumer (BL-350 D1 Fix 2026-06-14): ORCHESTRATOR ruft /_backlog ───
# Frueher TOTE NAHT: das Flag wurde gesetzt, aber NIE konsumiert (kein /_backlog-Call hier) →
# /_backlog (der EINZIGE korrekte Node-Writer inkl. RF-A6 ak_anchors/srs_per_ak/k_score_per_ak,
# _backlog.md SCHRITT 4 create+update-shared) lief NIE → RF-A6 silent-skipped (BL-308-Live-Beleg,
# Deviation #1). Fix: Flag lesen + /_backlog mit korrektem Modus invoken.
IF Read({WORKING_DIR}/_manifest.md).A_PIPELINE_STATE.backlog_spawn_required == true:
  # Mode-Selektion: existierender Node -> update (refresht RF-A6 + aggregat), sonst create.
  bl_exists = exists({VAULT}/Backlog/{BL_SLUG}.md) OR exists({VAULT}/Backlog/{BL_SLUG}/)
              OR (A_PIPELINE_STATE.backlog_item_created == true)
  backlog_mode = bl_exists ? "update" : "create"
  Logge: "[A Phase 4.2a] INV-MA-4-Consumer: Skill(_backlog, args='{args.name} --mode={backlog_mode}') — RF-A6-Node-Writer"
  Skill(_backlog, args="{args.name} --mode={backlog_mode}")
  # /_backlog schreibt Node-Frontmatter (SCHRITT 4, shared) inkl. RF-A6 aus 4_K-Score/*-K-SCORE.md +
  # aggregat-Metriken; setzt backlog_item_id/backlog_item_status im Manifest.
  Set A_PIPELINE_STATE.backlog_spawn_required = false   # konsumiert (Idempotenz)
ELSE:
  Logge: "[A Phase 4.2a] backlog_spawn_required != true — kein /_backlog-Call (z.B. transkript-only)"
TaskUpdate name="phase-4-2a-metadaten" status=DONE

# ═══ PHASE 4.4: GIT-TRACKING (Model-Frontmatter sync.last_sync_commit) ═══
Skill(_A_berater_gitTracking, args="{args.name}")
TaskUpdate name="phase-4-4-gitTracking" status=DONE

# ═══ PHASE 4.3: STATE-MAINTAIN (Pattern B Rollover, Manifest-Protokoll) ═══
Skill(_A_berater_stateMaintain, args="{args.name}")
TaskUpdate name="phase-4-3-stateMaintain" status=DONE
# BL-376 Fund#2 (INV-PROV-TRENNUNG): Nach stateMaintain haelt propagate_provenance die A-Phase
# source_provenance fuer Downstream (IDF/SDF) fest. Aufruf: propagate_provenance.py update {doc}
# (source_provenance vs. BERATER_OUTPUTS-Provenance = 2 Welten, nicht fusioniert).
# py -3 .claude/scripts/propagate_provenance.py update {bl_folder}/... --vault {VAULT_ROOT}

# ═══ PHASE 5d: ARC42-SICHTEN (BL-378 — terminale View-Schicht, NON-BLOCKING) ═══
# Nach 5c+Metadaten sind ALLE Wahrheiten + der reife BL-Node da. arc42 rendert sie als normierte
# Sichten + Mermaid in {bl_folder}/arc42/ — reine VIEW-Schicht (KEIN Truth-Write, INV-ARC42-1).
# NON-BLOCKING: ein Doku-Fehler darf A NICHT aborten / das Routing NICHT blockieren.
# Sub-Orchestrierung via Skill-Handschuh (NICHT Agent — INV-AO-CALLER/INV-PM-2): _arc42_orchestrate
# erkennt das aktive Parent-Team (a-{name}, nested-aware) und faechert seine Sektions-Berater darin
# file-isoliert auf (kein eigenes TeamCreate). MUSS VOR Phase 5 routing laufen — routing kann via
# _A_postRoute zu IDF auto-chainen und kehrt evtl. nicht zu A zurueck. Routing bleibt LAST (INV-A-ORDER-3).
IF args.scope != "transkript-only":
  TRY:
    Skill(_arc42_orchestrate, args="{args.name} --mode=organic --tier=auto")
    Logge: "[A Phase 5d] arc42-Sichten gerendert -> {bl_folder}/arc42/ (organisch, idempotent)."
  CATCH e:
    Logge: "[A Phase 5d] arc42-Render fehlgeschlagen (NON-BLOCKING): {e} — A faehrt fort zu Routing."
ELSE:
  Logge: "[A Phase 5d] scope=transkript-only — arc42-Sichten uebersprungen."
TaskUpdate name="phase-5d-arc42" status=DONE

# ═══ PHASE 5: ROUTING (LAST — INV-A-ORDER-3) ═══
# Begruendung RF-A-ORDER: Routing-Entscheidung ist Exit-Punkt der Pipeline.
# Absorbiert frueheres 4.1c (EXTERN/INTERN-Scan), 4.2 (MODE-RECOMMENDATION),
# 4.3 (User-Decision), 4.3a (Handschuh-Wechsel A->SC/I).
# Berater-intern: Skill(_A_postRoute) fuer Exit-Router (frischer Kontext).
Skill(_A_berater_routing, args="{args.name} {args.entry_point} {args.scope}")
# routing: EXTERN/INTERN-Keyword-Scan (offene W{n})
# routing: MODE-RECOMMENDATION (2D-Matrix COMPLEXITY x SRS_RANGE)
# routing: User-Decision (oder puppet_master autonom)
# routing: Pfad 1 (transkript-only RETURN), Pfad 2 (entry_point=bdf RETURN),
#          Pfad 3 (entry_point=manual -> _A_postRoute)
# routing: setzt A_PIPELINE_STATE.completion_signal + phase=COMPLETED
# routing: setzt A_PIPELINE_STATE.idf_invoke_required = true wenn target=IDF
TaskUpdate name="phase-5-routing" status=DONE

# BL-211 Fix 2026-05-24: explicit Auto-Chain Trigger (T79 hatte _A_postRoute "tot" gefunden).
# _A_berater_routing setzt NUR Flag idf_invoke_required (W7-Constraint INV-RT-4),
# Orchestrator MUSS jetzt explizit _A_postRoute aufrufen damit Auto-Chain zu IDF wirkt.
# Option B aus BL-211 Spec: Orchestrator-Driven Auto-Chain statt _A_postRoute Reanimation.
idf_invoke_required = Read({WORKING_DIR}/_manifest.md).A_PIPELINE_STATE.idf_invoke_required ?? false
routing_target      = Read({WORKING_DIR}/_manifest.md).A_PIPELINE_STATE.routing_target ?? "STOP"

# BL-226 AK-1 (Hub) 2026-05-30: entry_point-Gate entfernt — A chaint bei routing=proceed
# BEDINGUNGSLOS direkt zu IDF (auch entry_point=bdf). Kein completion_signal=ready_for_bdf,
# kein BDF-Polling-Roundtrip mehr (1-Seam-Chain via _A_postRoute, INV-A-EXCEPT-1).
IF idf_invoke_required == true AND routing_target == "IDF":
  Logge: "[A Phase 5+BL-211/BL-226] Auto-Chain trigger Skill(_A_postRoute, args={args.name}) — target=IDF (entry={args.entry_point})"
  Skill(_A_postRoute, args="{args.name}")
  # _A_postRoute liest next_skill + ruft Skill(_IDF_orchestrate, args=next_args)
ELIF routing_target == "STOP":
  Logge: "[A Phase 5+BL-211] target=STOP — kein Auto-Chain (transkript-only)"
ELSE:
  Logge: "[A Phase 5+BL-211] kein Auto-Chain — idf_invoke_required={idf_invoke_required} target={routing_target} entry={args.entry_point}"

# ─── Stufe 6: TeamDelete (INV-LIFECYCLE-5) ──────────────────────────
LABEL: Stufe 6
Logge: "[A Stufe 6] EXIT phase={A_PIPELINE_STATE.phase} name={args.name}"
TeamDelete team_id="a-{args.name}"
# BL-349 AK-2 / INV-TEAM-GC-1 (eigener Teardown-Recovery): scheitert TeamDelete mit
# "Cannot cleanup team with N active member(s)" -> die N sind tote Worker DIESER Session ->
# `py .claude/scripts/team_gc.py strip a-{args.name}` -> TeamDelete erneut (laeuft dann durch).
Set BDF_PIPELINE_STATE.active_team = null
RETURN 0


SUBROUTINE: ABORT(reason):
  Set A_PIPELINE_STATE.phase = "ABORTED"
  Set A_PIPELINE_STATE.abort_reason = reason
  Logge: "[A ABORT] {reason}"
  GOTO Stufe 6
```

---

## BACKWARDS-COMPATIBILITY (RF-A-RENAME)

Die Phasen-Reordering bricht keine Aufrufer:

| Alter Phase-Name | Neue Position | Aliasse |
|------------------|---------------|---------|
| Phase 1 W_fetch (v2.x) | Phase 3a v3.0-3.1 (NACH Model) → Phase 2.5 v3.2 (VOR Model) | berater nutzt phase=phase_2_5_wfetch \| phase_3a_wfetch \| phase_1_wfetch |
| Phase 2 taskDef | Phase 0.6 (VOR W_fetch) | berater nutzt phase=phase_0_6_taskdef \| phase_2_taskdef |
| Phase 4.1c keyword-scan | Berater-intern (routing) | absorbiert |
| Phase 4.2 MODE-RECOMMENDATION | Berater-intern (routing) | absorbiert |
| Phase 4.3 User-Decision | Berater-intern (routing) | absorbiert |
| Phase 4.3a Handschuh-Wechsel | Phase 5 (LAST) | absorbiert |

Externe Konsumenten (BDF, A_postRoute) lesen `A_PIPELINE_STATE.phase`
unveraendert (`COMPLETED`, `WP_PIPELINE_READY`, `SC_*_READY`, `I_PIPELINE_READY`).

---

## RECHECK / DRY-RUN / RESUME

**Dry-Run (`--mode=dryRun`, BL-089):** Stufe 1+2 werden ausgefuehrt, dann
short-circuit zu Stufe 6 mit Mock-Report nach
`.claude/output/A_Pipeline_DryRun_{name}_{DATE}.md`.

**Resume:** Berater sind individuell idempotent (lesen eigenen
BERATER_OUTPUTS-Slot und ueberspringen fertige Arbeit). Bei Wiederaufnahme
laeuft Stufe 1-3 immer; Stufe 5 springt zur ersten unfertigen Phase.

**Recheck (`--scope=transkript-only`):** Routing (Phase 5) erkennt scope
und exited via Pfad 1 ohne Handschuh-Wechsel.

---

## QUICK-START

```
# Frischer Lauf (Discovery + voller Prozess)
Skill(_A_orchestrate, args="auto fresh normal sonnet haiku")

# Konkretes Feature, Resync-Modus
Skill(_A_orchestrate, args="DCSRE-93 resync normal opus haiku")

# IDD-Modus (Parent-Branch)
Skill(_A_orchestrate, args="DCSRE-882 fresh normal sonnet haiku --parent-pr feature/DCSRE-881_DateiabholungAnalyse")

# BDF-getriggert (Auto-Detect entry_point)
Skill(_A_orchestrate, args="DCSRE-93 fresh normal --entry-point=bdf")

# Dry-Run (Architektur-Validierung ohne Wellen-Spawns)
Skill(_A_orchestrate, args="DCSRE-93 fresh normal sonnet haiku --mode=dryRun")
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| pileOfMud leer (fresh) | findingsExtraction-Berater spawnt User-Dialog im fallback |
| Model fehlt (resync) | modusErkennung-Berater Fallback auf fresh |
| Berater crash | Team Lead Re-Spawn (max 1 Retry), bei 2. Crash AskUserQuestion |
| Spec aktuell (resync) | _spec berater-intern SKIP |
| Git nicht verfuegbar | gitTracking + iddContext degraded |
| Partial-Wellen (<=50%) | Berater-intern degraded mode |
| Partial-Wellen (>50%) | Berater-intern Re-Spawn |

---

## VERWANDTE COMMANDS

- `_A_help` / `_A_help_extended` — Uebersicht / Tiefen-Narrativ
- `_A_postRoute` — Exit-Router (von routing-Berater gerufen)
- 9 `_A_berater_*` — Phasen-Berater (siehe VERTRAG)
- Pipeline-Commands: `_taskDefinition`, `_W_fetch`, `_model`,
  `_SC_modelMaintain`, `_spec`, `_K_score`, `_gap`, `_backlog`

---

## ABHAENGIGKEITEN

- **BL-142** (THIS): Thin-Manager-Refactor + Phase-Reorder + Berater-Migration.
- **BL-129** (DONE): K-Score pro AK (Phase 4k).
- **BL-089** (DONE): Dry-Run-Modus.
- **BL-076/088** (DONE): IDF-Vorgaenger-Pattern.
- **BL-065** (DONE): Vault-First (PRIMAER Vault, FALLBACK lokal).
- **BL-060** (DONE): active_team Manifest-Write nach TeamCreate.
- **BL-045** (DONE): Vault-First, kein Fire-Together-Sync mehr.
- **BL-043** (DONE): WP-Crumbs als Spec-Primaerquelle.
- **BL-032** (DONE): entry_point/scope Parameter.
- **BL-016 Epic E3** (DONE): INV-SP-1/INV-SP-2 Anti-Stille-Post.
