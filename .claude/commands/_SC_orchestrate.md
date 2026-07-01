# /_SC_orchestrate - Team Lead Forschungszyklus-Orchestrierung

```yaml
status: active
version: 3.5.0
created: 2026-02-15
updated: 2026-06-03
op: ScientificCycle
phase: Meta
type: orchestration
chain_position: meta
difficulty_scaling: true
team_based: true
depends_on:
  - _W_fetch
  - _A_orchestrate
feeds_into:
  - _SDF_orchestrate
  - _I_orchestrate
  - _W_push_orchestrate
related:
  - _TDD_orchestrate
bl_134_pflaster: true
bl_134_pflaster_inserted: 2026-04-25
bl_134_pflaster_real_refactor_in: BL-136
bl_140_pflaster_code: true
# BL-142 Caller-Migration (2026-04-26):
# - A_PIPELINE_STATE.recommendation: GESTRICHEN (A liefert nur aggregat_*, Mode-Decision → SDF C3)
# - A→SC Guard: ersetzt durch SDF→SC Guard (bereits in Schritt 1.1 vorhanden)
# - complexity_auto_tdd_pending → aggregat_auto_tdd_pending (RF-A-RENAME)
# - complexity_switch_recommendation → aggregat_switch_recommendation (RF-A-RENAME)
# - complexity_trend, complexity_score: GESTRICHEN (Felder entfallen in A_PIPELINE_STATE)
```

---

## BL-173 Manifest-Routing (NEU 2026-05-18)

**Manifest-Scope-Split aktiv** (siehe BL-173, INV-MANIFEST-SPLIT-1..4):

| State-Block | Heimat | Helper |
|---|---|---|
| SC_PIPELINE_STATE | `{bl_folder}/_manifest.md` | `manifest_reader.read_bl_block(bl_id, "SC_PIPELINE_STATE")` |

**Pfad-Aufloesung:**
- Factory-State: `manifest_reader.read_factory_block(...)` ODER direkt `{vault_root}/_factory_manifest.md`
- BL-State: `manifest_reader.read_bl_block(bl_id, ...)` ODER direkt `{bl_folder}/_manifest.md`
- Legacy-Fallback aktiv solange `is_split_active() == False` (1-Sprint-Uebergang)

**Migration:** `py -3 .claude/scripts/migrate_manifest_split.py migrate --vault-root="..." --rollback-tag=YYYY-MM-DD`

> **Registry-Loader (MLG S3 Log-Doppel):** Dieses Command nutzt `.claude/hooks/load_registries.py::resolve()` fuer Model-Resolution (ModelLeakGuard Feature, 4-Stufen-Kette: Welle-Schema → Session-Cap → Command-Override → Spawn).
> Jeder Wellen-/Pipeline-Spawn ruft vor `Agent(...)` das Pattern auf:
> `r = resolve(command="{CMD}", wave="w1|w2|w3|seq", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})`
> → `r.subagent_type` und `r.model` sind die Soll-Werte. Der `[SPAWN]`-Top-Log protokolliert sie VOR dem Agent-Call. Der Worker quittiert spiegelnd mit `[AGENT]`-Bottom-Log (Schritt 0, KURZLEBIG_PROMPT).

---

```
+======================================================================+
| META-COMMAND: /_SC_orchestrate                                       |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU — reiner Orchestrator)                          |
|   CONSTRAINT: Team Lead fuehrt KEINE Commands aus.                   |
|   NUR spawnen, tracken, entscheiden.                                  |
|                                                                        |
| WORKER: Kurzlebige Single-Command-Agents (1 Agent = 1 Command)       |
|         + N Wellen-Agents (PARALLEL: Explorer/Drafter/Synthese)      |
|                                                                        |
| PRINZIP: 1 Agent = 1 Command = stirbt danach (KURZLEBIG_PROMPT).    |
|          State lebt in DOKUMENTEN, nicht im Agenten.                  |
|          Kein Worker-Loop, kein TaskList-Polling.                      |
|          Kein Worker spawnt Sub-Agents (W7-Constraint).               |
|                                                                        |
| FLOW:  W_FETCH → PRE-CYCLE → SC-CYCLE ⟲ → POST-CYCLE → HiL         |
|                                                                        |
| MODUS: FULL | INLINE (-I) | REVIEW (--mode=review) | ANALYSE        |
|                                                                        |
| META-DATEIEN (on-demand per Read-Tool):                               |
|   {META}/sc/task-templates.md    (Task 0-11 Beschreibungen)    |
|   {META}/sc/decision-tables.md   (3 Decision Tables)           |
|   {META}/sc/sc-i-gate.md         (Gate + Finale Verifikation)  |
|   {META}/sc/symbiose-protocol.md (SC⟲I FULL-Modus)            |
|   {META}/sc/review-modus.md      (Post-I Review Details)       |
|   {META}/sc/handoff-template.md  (HandOff-Dokument Template)   |
+======================================================================+
```

---

## VERTRAG

```
WORKING_DIR = resolve_bl_path(BL_ID)  # INV-VAULT-9

LIEST:
  {VAULT}/_manifest.md           (Startpunkt, NAME, Phase)
  {VAULT}/Task.md                (Aufgabendefinition, optional)
  # PRIMAER: Vault (BL-065)
  {VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md (existierendes Model, optional)
  # FALLBACK: lokal (Legacy)
  # fallback-read: expected vault, using .claude/
  .claude/models/{NAME}_Model.md (existierendes Model, Fallback)
  .claude/pileOfMud/             (Rohmaterial, optional)

SCHREIBT STATE (_manifest.md):
  sc_status: RUNNING/DONE (Einzeiler)
  SC_PIPELINE_STATE: {YAML-Block, nur laufender Zyklus}
  SC_PIPELINE_STATE.sc_verdict: {Enum, BL-238 AK-7 — Saettigungs-Verdikt am Phase-5-Exit}

SCHREIBT (Output) — BL-238 AK-7 (Saettigungs-Signal, Slot-Isolation PT-CMD-008):
  SC_PIPELINE_STATE.sc_verdict ∈ {SATURATED_READY_FOR_IMPL, EXPERIMENT_OPEN, ABORT}
    # Geschrieben am Phase-5 AUTOCHAIN-EXIT (VOR Skill(_SDF_orchestrate_post)).
    # Lebt im SC_PIPELINE_STATE-Slot (NICHT modus-Slot) — KEIN INV-MODUS-5-Bypass-Feld.
    # Reader: dispatch_implement.js (Consumer AK-1) — runPhase3-Trigger ausserhalb BATCH_DONE.
  i_gate_response: {Einzeiler-Ergebnis nach POST-CYCLE}
  sdf_mode_original: {SDF-Mode Rohwert aus DF_BATCH_STATE.modus, z.B. "M5"}
  sdf_mode_override: {true/false — CLI-Modus weicht von SDF-Dispatch ab}
  next_cycle_context: {YAML-Block, 7 Felder aus i_core_result + PRE-FILTER}
  pre_filter_veto: {true/false — VETO gegen DONE}
  pre_filter_reason: {Liste der VETO-Gruende}
  pt_feature_summary: {Einzeiler — N DRAFTs, N PROMOTED (POST-CYCLE Schritt 5, NON-BLOCKING)}
  Pattern A fuer sc_status + i_gate_response
  Pattern B fuer SC_Z{N-2}_* Rollover (bei CONTINUE in Phase 3.3.0)

  # BL-165 AK-11 PL-11-05: DF_BATCH_STATE Marker (geschrieben von SC-Berater, gelesen von SDF Phase 4)
  DF_BATCH_STATE.sc_cycle_count_per_batch: {batch_1: N, batch_2: M}
    # Schreiber: Phase 0 Resume-Check bei sc_resume_from="ergebnis" (increment)
    # Reader: SDF Phase 4 loopDecision (beobachtet Anzahl SC-Zyklen pro Batch)
  # LIEST (nicht schreibt):
  DF_BATCH_STATE.sc_resume_from: "ergebnis" | "observe" | null
    # Schreiber: SDF Phase 4 loopDecision (INV-MODUS-9 BL-165) — SC schreibt dieses Feld NICHT

SCHREIBT PROTOKOLL (_manifest_protokoll.md):
  ## SC Zyklus Z{N-2} Archiv (Pattern B, bei Rollover in 3.3.0)
  ## sc_i_gate [{Datum}] (Pattern C, bei POST-CYCLE Schritt 2)
  Prepend-Mechanismus (W18): last_append + append_count aktualisieren
  Frontmatter: last_append={Datum}, append_count++ (vor Eintrag)

SCHREIBT NICHT:
  _manifest_protokoll.md direkt ohne Prepend-Mechanismus (W18)


AUSGABEN DURCH WORKER (BL-045 Vault-First):
  {VAULT}/.../Model/{NAME}_Model.md                 (via _model)
    FALLBACK: .claude/models/{NAME}_Model.md
  {WORKING_DIR}/.claude/analysis/synthese/{NAME}-OBSERVE{N}.md    (via _SC_observe — per-Story BL-155 AK-1)
  {WORKING_DIR}/.claude/analysis/synthese/{NAME}-ERGEBNIS{N}.md   (via _SC_ergebnis)
  {WORKING_DIR}/.claude/analysis/exploration/{NAME}-E*.md          (Welle 1)
  {WORKING_DIR}/.claude/analysis/drafts/{NAME}-*-D*.md             (Welle 2)
  {VAULT}/Backlog/{BL_SLUG}/SC/{NAME}-HANDOFF.md                   (Team Lead, DONE — BL-151 + PL-D 2026-05-07)
  {WORKING_DIR}/.claude/analysis/post-impl/{NAME}-REVIEW-PROTOKOLL.md (nur --mode=review)

HAUPTPRODUKT: MODEL (Wissensbasis)

INVARIANTEN:
  - Team Lead fuehrt KEINE Commands aus (R2)
  - 1 Agent = 1 Command = 1 Batch (R3, R4)
  - Kein Agent spawnt Sub-Agents (W7, R9)
  - Manifest-Update nach JEDER Welle und jedem Batch-Zyklus

PROZESS-INVARIANTEN (BL-016 Epic E3):

  INV-PM-1 (RF-06, AK-06-01): Worker-Pflicht ABSOLUT
    Auch bei Inline/Easy/Trivial MUSS ein Worker gespawnt werden.
    Team Lead fuehrt KEINE Analyse/Synthese selbst aus — IMMER Worker.

  INV-PM-2 (RF-06, AK-06-02): Handschuh-Wechsel = Skill-Load (frisch)
    Agent() statt Skill() ist Prozess-Verletzung UNABHAENGIG vom Ergebnis.

  INV-AO-CALLER (Sanity-Check V11/V12, 2026-05-07/2026-05-08):
    Skill(_SC_orchestrate) DIREKT vom Team Lead — kein Hub-Delegate via
    `Agent(general-sonnet, prompt="orchestrate ...")`. Sub-Agent wird Mega-
    Agent (Zyklus-Berater werden Inline-Logik). CLAUDE.md Z6 + _A_orchestrate
    INVARIANTEN. Beweis: DCSRE-2014 Hot-Fix.

  INV-HW-1 (RF-07, AK-07-01): SC ↔ SDF ↔ I — IMMER durch SDF
    SC ruft I NICHT direkt auf. I ruft TDD NICHT direkt auf.
    Heilige Trinitaet: SC ↔ SDF ↔ I ↔ SDF ↔ TDD (Hub-Invariante).
    SC setzt SC_NEEDS_IMPL → EXIT → SDF routet (CaseStudy DCSRE-1430).

  INV-SP-1 (RF-08, AK-08-01..03): Anti-Stille-Post Primaerquellen-Pflicht
    Jede Welle (Explorer, Drafter, Synthese) MUSS ihre EIGENE Analyse
    an den ORIGINAL-QUELLEN machen (Model, Commands, Task.md, Code).
    Vorgaenger-Output dient NUR als Kompass/Scope-Eingrenzung.
    Explorer-Outputs sind Wegweiser, KEINE Faktenquelle fuer Drafter.
    Drafts sind Inspiration, KEINE Faktenquelle fuer Synthese.

  INV-SP-2 (RF-08, AK-08-04): SD-Agents Primaerquellen DIREKT
    Spec-Drafter lesen Primaerquellen DIREKT, nie ueber Drafts-Output.

  INV-SP-3 (RF-08, AK-08-05): IDD-Feature Schwester-Vergleich
    Bei IDD-Feature ist die Schwester-Implementierung der Vertrag.
    Direkter Code-Vergleich obligatorisch (nicht ueber Wellen-Output).
```

### Lifecycle-Guard: Artefakt-Namespaces (v2.2+, I-11)

| Phase | Prefix/Ordner | Erzeuger |
|-------|---------------|----------|
| A-Phase | `exploration/{NAME}-E*`, `drafts/{NAME}-model-D*` | `/_model`, `/_A_orchestrate` |
| SC-Phase | `drafts/{NAME}-observe*-D*`, `synthese/{NAME}-OBSERVE*` | `/_SC_observe`, `/_SC_hypothese` |
| I-Phase | `{VAULT}/Backlog/{BL_SLUG}/SC/{NAME}-HANDOFF.md`, `post-impl/{NAME}-REVIEW-*` | `/_SC_orchestrate`, `/_I_orchestrate` |

**Regel:** Keine Vermischung zwischen Phasen-Namespaces.

### Lifecycle-Guard: Feature-Prefix-Isolation (v3.1+, CaseStudy F-03/SV-2)

**INVARIANTE:** Jedes Artefakt das ein Worker erstellt MUSS mit `{NAME}-` prefixed sein.

```
NACH JEDER WELLE (Team Lead prueft):
  Fuer jede neue/geaenderte Datei in exploration/, drafts/, synthese/:
    IF Dateiname startet NICHT mit "{NAME}-":
      → FEHLER: "Namespace-Verletzung: {datei} hat Prefix != {NAME}"
      → Worker erneut spawnen mit Korrektur-Kontext
    IF Datei gehoert zu anderem Feature:
      → FEHLER: "Fremdartefakt: {datei} gehoert zu {anderes_feature}"
      → Datei NICHT in Manifest aufnehmen
```

**Warum:** In DCSRE-882 landeten 5 Fremdartefakte im Analyse-Verzeichnis,
in OmniCommand 19 newsPage-Dateien. Ohne Guard ist Namespace-Verschmutzung
unsichtbar und korrumpiert spaetere Synthesen.

### Lifecycle-Guard: OBSERVE Mode-Infix (v3.1+, CaseStudy F-09/SV-3)

**INVARIANTE:** Bei Mode-Wechsel (z.B. THEORETISCH→ANALYSE) MUSS der alte
OBSERVE-Satz umbenannt werden, damit Erkenntnisse nicht still ueberschrieben werden.

```
BEI MODE-WECHSEL (Team Lead, VOR neuem Zyklus):
  alter_modus = SC_PIPELINE_STATE.sc_mode (aus letztem Zyklus)
  neuer_modus = angeforderter Modus

  IF alter_modus != neuer_modus:
    Fuer jede {NAME}-OBSERVE{N}.md in synthese/:
      RENAME → {NAME}-OBSERVE{N}-{alter_modus}.md
    Manifest: mode_transitions APPEND: "{alter_modus}→{neuer_modus} (Zyklus {C})"
    Log: "Mode-Infix: {K} OBSERVE-Dateien archiviert als *-{alter_modus}.md"
```

**Warum:** In DCSRE-882 wechselte der SC von THEORETISCH (Sprint-kritisch) zu
ANALYSE (Architektur-Fragen). Die neuen OBSERVE-Dateien ueberschrieben die alten
lautlos — Erkenntnisse aus dem THEORETISCH-Zyklus gingen verloren. Mit Mode-Infix
bleiben beide Saetze nebeneinander erhalten.

---

## SCHRITT 0: BL-140 Batch-Pflaster (echter Branch)

<!-- BL-144 L4: Echter Branch-Header fuer Batch-Pflaster. INV-SC-PFLASTER-3 unten. -->

## BL-134 PFLASTER: Batch-Input-Adapter (Sub-Pipeline)

**Eingefuegt:** 2026-04-25 als Teil von BL-134 Slice 3.

Diese Pipeline akzeptiert ab BL-134 oberflaechlich einen `batch={PL-Items}` Parameter
vom SDF-executionDispatch und iteriert intern **sequentiell** durch die Items
(kein paralleler Batch-Refactor).

### Vertrag (Pflaster)

- **LIEST:** Wenn `batch=` Param gesetzt -> Liste der PL-Items aus `DF_BATCH_STATE.batch_items` (vom executionDispatch durchgereicht).
- **ITERIERT INTERN:** `FOR item IN batch_items: pipeline_aufruf(item)` (sequentiell).
- **SCHREIBT pro Item:** `DF_BATCH_STATE.item_done.append(item_id)` nach erfolgreichem Pipeline-Durchlauf (Recovery-Hook).
- **EXIT:** Wenn alle Items DONE.

### BL-134-PFLASTER-MARKER (Pseudo-Code)

```
batch = lies CLI_PARAM("batch") ?? null
IF batch != null:
  Logge: "[BL-134-PFLASTER] sc_orchestrate batch-modus: {len(batch)} Items sequentiell."
  FOR item IN batch:
    skip_if_done = item IN DF_BATCH_STATE.item_done
    IF skip_if_done: Logge "[BL-134-PFLASTER] SKIP {item} (bereits done)"; CONTINUE
    pipeline_aufruf(item)
    DF_BATCH_STATE.item_done.append(item)
    manifest.update()
  RETURN

# kein batch-Param -> normaler Single-Item-Pfad (Legacy)
```

### Echter Batch-Refactor

Dieser Pflaster ist Uebergangs-Loesung. Echter Batch-Support (paralleler
intern-Loop, Aggregat-Kontext) folgt im jeweiligen Pipeline-Refactor:

- **sc_orchestrate echter Refactor:** BL-136

### INV-SC-PFLASTER-1

Pflaster-Pfad MUSS sequentiell bleiben bis BL-136 den echten Refactor liefert.
Paralleler intern-Loop ohne explizite BATCH_STATE-Race-Locks ist VERBOTEN.

### BL-140 PFLASTER-CODE (echte Implementation)

```
# CLI-Param oder Manifest
batch = lies CLI_PARAM("batch") OR DF_BATCH_STATE.batch_items
IF batch != null AND |batch| > 0:
  Logge: "[BL-140-PFLASTER] sc_orchestrate Batch-Modus: {len(batch)} Items sequentiell"
  FOR item IN batch:
    # Skip falls schon DONE
    IF item IN DF_BATCH_STATE.item_done:
      Logge: "[BL-140-PFLASTER] SKIP {item} (bereits in item_done)"
      CONTINUE

    # Original-Pipeline-Aufruf fuer dieses Item
    pipeline_main_logic(item)

    # Recovery-Hook
    DF_BATCH_STATE.item_done.append(item)
    manifest.update()

  RETURN  # Batch-Modus fertig

# Fallback: kein batch -> Single-Item-Pfad (Legacy)
pipeline_main_logic(NAME)
```

INV-SC-PFLASTER-2 (NEU, BL-140):
Pflaster-Code MUSS sequentiell iterieren (kein paralleler Loop ohne Race-Lock).
Pflaster-Code MUSS item_done.append nach JEDEM erfolgreichen Item.
Pflaster-Code MUSS RETURN am Ende des batch-Pfads (NICHT in den Legacy-Pfad fallen).

INV-SC-PFLASTER-3 (BL-144):
Echter Batch-Branch IM Pipeline-Body -- NICHT nur Doku am Datei-Ende.
Der SCHRITT-0-Block MUSS vor PHASE 1 aktiv ausgefuehrt werden (kein toter Doku-Anhang).

---

## Aufruf

```
/_SC_orchestrate [name] [difficulty] [ceiling] [floor] [-I] [--mode=review] [--mode=analyse] [--symbiose] [--full-symbiose] [--only-I] [--resume-at=ergebnis]
```

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `name` | (Manifest) | String | Feature-/Forschungsname. Falls nicht angegeben: lese `NAME:` aus `{VAULT}/_manifest.md`. Falls kein Manifest: FEHLER. |
| `difficulty` | normal | easy, normal, hard | Agent-Anzahl, Wellen-Tiefe |
| `ceiling` | sonnet | haiku, sonnet, opus | Hoechstes Modell |
| `floor` | haiku | haiku, sonnet | Niedrigstes Modell |
| `-I` | - | Flag | INLINE: /_SC_implement (1 IC, 100 LOC) |
| `--mode=review` | - | Flag | Post-I Review (separater Pfad) |
| `--mode=analyse` | - | Flag | Reine Analyse ohne Implementation |
| `--symbiose` | - | Flag | (Z4: RF-33) Gate 6 Mode-Switch-Check erzwungen (auch Zyklus 1) |
| `--full-symbiose` | - | Flag | (Z4: RF-33) Gate 6 SKIP, sofort sc_mode=FULL + I core |
| `--only-I` | - | Flag | (Z4: RF-33) SC sofort POST-CYCLE, I-STANDALONE (scope_mode=full) starten |
| `--resume-at` | - | ergebnis | SDF-HUB Resume: SC springt direkt zum Ergebnis-Schritt (nach SDF→I→TDD Return). CaseStudy DCSRE-1430. |

**4 Modi + I-STANDALONE:**

| Modus | Implement-Step | Max Zyklen (e/n/h) |
|-------|---------------|-------------------|
| FULL (Default / --symbiose / --full-symbiose) | /_I_orchestrate (SYMBIOSE) | 3/5/8 |
| INLINE (-I) | /_SC_implement (klein) | 3/5/8 |
| REVIEW | SKIP | 2/3/5 |
| ANALYSE | SKIP | 1/2/3 |
| I_STANDALONE (--only-I) | Direkt /_I_orchestrate (scope_mode=full) | — |

**Dark Factory max_cycles Override (W225, ADR-5):**
```
# Nach max_cycles Berechnung aus Tabelle oben:
Lies dark_factory_max_cycles_override aus _manifest.md (falls vorhanden)
IF dark_factory_max_cycles_override vorhanden UND dark_factory_max_cycles_override > 0:
  max_cycles = dark_factory_max_cycles_override
  Logge: "Dark Factory Override: max_cycles={max_cycles} (statt Standard)"
# Effekt: hard=9 statt hard=8 im Dark Factory Modus
```

**Inkompatibilitaeten (9 Paare → ABBRUCH bei Verletzung): (Z4: RF-12)**

Bestehend (3): -I + --mode=review, -I + --mode=analyse, --mode=review + --mode=analyse

Neu (6):
- -I + --symbiose
- -I + --full-symbiose
- --symbiose + --full-symbiose
- --only-I + -I
- --only-I + --symbiose
- --only-I + --full-symbiose
- (implizit: --only-I + --mode=analyse, --symbiose + --mode=analyse, --full-symbiose + --mode=analyse)

**Modell-Zuordnung:**

| Rolle | easy | normal | hard |
|-------|------|--------|------|
| Team Lead | DU (Opus) | DU (Opus) | DU (Opus) |
| Synthese (Welle 3) | 1 {ceiling} | 1 {ceiling} | 1 {ceiling} |
| Drafter (Welle 2) | --- | 3 {middle} | 5 {middle} |
| Explorer (Welle 1)* | --- | 5 {floor} | 9 {floor} |

*Explorer-Welle gilt NUR fuer `/_model` (3-Wellen-Pattern). SC-Commands (observe, hypothese, ergebnis) starten direkt mit Draftern/Sammlern.

---

## Command-spezifische Wellen-Konfiguration (SC-Zyklus)

### Wellen-Commands (SC_orchestrate)

| Command | Welle 1 | Welle 2 | Welle 3 | Fokus-Quelle | Modell-Override |
|---------|---------|---------|---------|--------------|-----------------|
| /_SC_observe | Drafter (D01-D03/D05) | Synthese | --- | /_SC_observe "Worker-Vertraege" | Standard |
| /_SC_hypothese | Drafter (D01-D03/D05) | Synthese | --- | /_SC_hypothese "Worker-Vertraege" | Standard |
| /_SC_ergebnis | Sammler (DS01-DS05/DS09) | Synthese | --- | /_SC_ergebnis "Worker-Vertraege" | Downgrade (W7) |

### Modell-Override fuer _SC_ergebnis (niedrig-kognitiv)

| Ceiling | Sammler | Synthese |
|---------|---------|----------|
| opus | sonnet | sonnet |
| sonnet | haiku | sonnet |
| haiku | haiku | haiku |

**Begruendung:** _SC_ergebnis ist explizit NIEDRIG-KOGNITIV (docker ps parsen,
Zahlen abzaehlen, SRS-Formel anwenden). Sonnet/Haiku reichen fuer mechanische Sammlung.

---

## Wellen-Statusanzeige (RF-9)

Team Lead gibt nach JEDER Wellen-Transition folgende Tabelle aus:

```
┌───────┬──────────────────────────────┬────────┬─────────┐
│ Welle │        Worker                │ Modell │ Status  │
├───────┼──────────────────────────────┼────────┼─────────┤
│ W1    │ {N} Drafter/Sammler (D01-DN) │ {mod}  │ {status}│
│ W2    │ 1 Synthese                   │ {ceil} │ {status}│
└───────┴──────────────────────────────┴────────┴─────────┘
Command: /_SC_observe {NAME} | Zyklus: Z{N}
```

**Status-Werte:** DONE, RUNNING, PENDING
**Wann:** Nach Abschluss jeder Welle (W1→W2, W2→fertig)
**Modell-Override:** Bei _SC_ergebnis Modell-Spalte aus Override-Tabelle lesen
**Bei easy:** Nur 1 Zeile (Synthese solo)

---

## Prozess-Statusanzeige (RF-10)

Team Lead gibt nach JEDEM Schrittwechsel folgende Tabelle aus.
**Ziel: Alles auf 1 Blick** — Schritt, Agenten, Modell, Status, Inhalt.

```
┌────┬─────────────┬──────────────────────┬────────┬──────────┬──────────────────────────────────────────────────────┐
│ #  │ Schritt     │ Agenten              │ Modell │ Status   │ Inhalt (Mini-Assay, NUR bei DONE)                    │
├────┼─────────────┼──────────────────────┼────────┼──────────┼──────────────────────────────────────────────────────┤
│ 1  │ observe     │ 5 Drafter PARALLEL   │ sonnet │ ✓ DONE   │ Provider hat 3 undokumentierte Sonderfaelle,         │
│    │             │                      │        │          │ Status-Mapping weicht vom Domain-Model ab             │
│ 2  │ modelMaint  │ 1 (sequentiell)      │ opus   │ ✓ DONE   │ 4 neue W{n}, Kern: Event-Replay hat Race Condition   │
│ 3  │ qualityGate │ 1 (sequentiell)      │ opus   │ ► ACTIVE │                                                      │
│ 4  │ hypothese   │ 3 Drafter PARALLEL   │ sonnet │ · PENDING│                                                      │
│ 5  │ implement   │ modus-abhaengig      │ varies │ · PENDING│                                                      │
│ 6  │ ergebnis    │ 1 (sequentiell)      │ opus   │ · PENDING│                                                      │
└────┴─────────────┴──────────────────────┴────────┴──────────┴──────────────────────────────────────────────────────┘
Zyklus 2/5 | SRS: 71.5 | K-Score: 42 (MEDIUM) | Route: SC-INLINE
```

**Inhalt-Spalte:** 1-2 Saetze was INHALTLICH gefunden/produziert wurde (nicht prozess-spezifisch).
**Status-Symbole:** ✓ DONE, ► ACTIVE, · PENDING, — SKIP, ✗ FAIL
**Modell-Regel:** Explorer={floor}, Drafter={middle} (IMMER sonnet bei ceiling>=sonnet), Synthese={ceiling}
**SC-spezifisch:** Unter der Tabelle zusaetzlich Zyklus-Nr, SRS-Wert und Route anzeigen.
**Wann:** Nach Abschluss jedes Schritts und vor Start des naechsten.

---

## GLOBALE PARAMETER (/_param Override)

```
Lies _session_params.md → difficulty, ceiling, floor, HiL.
difficulty = params.difficulty
ceiling    = min(ceiling, params.ceiling)
floor      = max(floor, params.floor)
Validierung: ceiling >= floor (sonst ceiling = floor + Warning)
middle = sonnet wenn ceiling=opus, sonnet wenn ceiling=sonnet, haiku wenn ceiling=haiku
```

---

## PHASE 0: RESUME-CHECK (BL-165 AK-11, PL-11-02)

> INV-MODUS-9 (BL-165): SDF Phase 4 loopDecision setzt `DF_BATCH_STATE.sc_resume_from`
> vor jedem SC-Aufruf. Phase 0 liest diesen Marker und bestimmt START_AT.

```
# Phase 0: Resume-Check — START_AT Bestimmung (BL-165 AK-11)
sc_resume_from = lies DF_BATCH_STATE.sc_resume_from aus _manifest.md ?? null

SWITCH sc_resume_from:
  "ergebnis":
    START_AT = "_SC_ergebnis"
    Logge: "[PHASE-0] sc_resume_from=ergebnis → START_AT=_SC_ergebnis (SC-Re-Entry mit prior summary)"
    # Increment cycle_count_per_batch (INV-MODUS-9)
    current_batch = DF_BATCH_STATE.current_sub_batch_id ?? "default"
    DF_BATCH_STATE.sc_cycle_count_per_batch[current_batch] += 1
    Logge: "[PHASE-0] cycle_count_per_batch[{current_batch}]={count}"

  "observe" | null:
    START_AT = "_SC_observe"
    Logge: "[PHASE-0] sc_resume_from={sc_resume_from} → START_AT=_SC_observe (First-Entry, skip ergebnis)"

  SONST:
    # Unbekannter Wert — defensiv zu _SC_observe
    START_AT = "_SC_observe"
    Logge WARNUNG: "[PHASE-0] sc_resume_from={sc_resume_from} unbekannt → START_AT=_SC_observe (Fallback)"

manifest.update(DF_BATCH_STATE.sc_cycle_count_per_batch)
```

---

## PHASE 1: TEAM SETUP

Skill(skill="_SC_berater_teamSetup", args="{NAME} {flags}")
# BL-165 PL-11-01: _SC_berater_teamSetup registriert Team "sc-{batch_id}",
# resolved Vault-Pfade, liest sc_resume_from, prueft Inkompatibilitaeten.
# Output: BERATER_OUTPUTS.teamSetup.{team_name, batch_id, vault_root, bl_folder,
#   sc_mode, sdf_guard_active, sdf_mode_normalized, sc_resume_from,
#   puppet_master_active, startpunkt, flags, exit_code}
IF BERATER_OUTPUTS.teamSetup.dryRun_done == true: RETURN
IF BERATER_OUTPUTS.teamSetup.only_I_done == true: RETURN  # Skill spawnt _I_orchestrate direkt

---
## SC Modus-Matrix (AK-03-04, BL-036)

Skill(skill="_SC_berater_modusMatrix")
# Liest: SC_PIPELINE_STATE.sc_mode, sdf_guard_active, sdf_mode_normalized, GLOBAL_HIL, difficulty
# Schreibt: BERATER_OUTPUTS.modusMatrix.{schritt_aktiv, sdf_guard_result, pipeline_mode_log, autonomie_modus}
# Deckt: Modus-Tabelle, SDF-Guard, pipeline_mode State Machine, Autonomie-Modus, Tasks 1.3, Agents 1.4

---
## PHASE 2: KURZLEBIG_PROMPT (Single-Command-Agent)

Skill(skill="_SC_berater_kurzlebigPrompt")
# Sub-Sektionen 2.0-2.3: Zyklus-Orchestrierung (Puppet Master), Single-Command-Prompt,
# Wellen-Phase-Prompt, kontext_constraint-Template
# Liest: BERATER_OUTPUTS.teamSetup (ceiling/floor/difficulty/sc_mode/NAME)
# Schreibt: BERATER_OUTPUTS.kurzlebigPrompt.{prompt_string, schritt_zaehler}

---
## PHASE 3: TEAM LEAD STEUERUNG

Skill(skill="_SC_berater_teamLeadSteuerung")
# Sub-Sektionen 3.1-3.7:
#   3.1 Pipeline-Sequenz + SC_PIPELINE_STATE
#   3.2 Zyklus-Entscheidung (incl. AUTO_TDD_CHECK RF-05)
#   3.2a SYMBIOSE
#   3.3 CONTINUE-Decision (incl. W_sync_orchestrate Trigger, Archive-Hook)
#   3.4 DONE/FORCE
#   3.5 ABORT, 3.6 HiL-Pause, 3.7 User-Decision
# Liest: BERATER_OUTPUTS.teamSetup + kurzlebigPrompt + modusMatrix
# Schreibt: BERATER_OUTPUTS.teamLeadSteuerung.{pipelineSequenz, zyklusEntscheidung,
#          modeSwitchResult, continueDecision, doneDecision, abortDecision}

---
## PHASE 4: OPTIONALE ESKALATIONEN

### 4.1 Architectural Boundaries (von qualityGate getriggert)

Wenn Worker "BSD Trigger T1-T5" oder "Boundaries empfohlen" meldet:
→ Zusatz-Task: /_architecturalBoundaries (VOR hypothese einschieben)

### 4.2 Blind-Spot Detection (von qualityGate getriggert)

Wenn Worker "BSD T1-T5 Muster erkannt" meldet:
→ Zusatz-Task: /_blindspotDetection (VOR hypothese einschieben)

### 4.3 Knowledge Deep-Dive (parallel)

Bei tieferem Recherche-Bedarf:
→ Paralleler Task: /_knowledge {THEMA} {difficulty} (blockiert NICHT Hauptzyklus)

---

## PHASE 5: AUTOCHAIN-EXIT (BL-165 AK-11, PL-11-03 — kein User-Tap)

> **INV-MODUS-7 (BL-165):** `_SC_orchestrate` hat KEIN Recht zu Selbst-Exit.
> Nach jedem CYCLE-LOOP-Durchgang ist Pflicht-Autochain via `Skill(_SDF_orchestrate_post)`.
> Re-Entry zu SC erfolgt ausschliesslich durch SDF Phase 4 loopDecision.

```
# Phase 5: AUTOCHAIN-EXIT (PL-11-03, BL-165 AK-11)
# Wird nach _SC_implement (Handover-Step) ausgefuehrt — KEIN User-Tap.
# Ersetzt den internen DONE_SCHWELLE-Check (DEPRECATED, siehe unten).

Logge: "[PHASE-5] AUTOCHAIN-EXIT — Skill-Wechsel zu _SDF_orchestrate_post (INV-MODUS-7)"

# BL-238 AK-7: Saettigungs-Verdikt explizit lesbar machen (Slot-Isolation PT-CMD-008).
# Additiver Write VOR dem Exit — Exit-Mechanik bleibt unveraendert (Kanarienvogel :582-607).
# sc_verdict ∈ {SATURATED_READY_FOR_IMPL, EXPERIMENT_OPEN, ABORT}, im SC_PIPELINE_STATE-Slot
# (NICHT modus-Slot, KEIN INV-MODUS-5-Bypass-Feld).
SC_PIPELINE_STATE.sc_verdict = (
  "SATURATED_READY_FOR_IMPL" if SC_PIPELINE_STATE.saturated == true
  else "EXPERIMENT_OPEN"      if SC_PIPELINE_STATE.experiment_open == true
  else "ABORT"
)
manifest_reader.write_bl_block(BL_ID, "SC_PIPELINE_STATE", SC_PIPELINE_STATE)
Logge: "[PHASE-5] sc_verdict={SC_PIPELINE_STATE.sc_verdict} geschrieben (BL-238 AK-7, Reader=dispatch_implement.js)"

audit_jsonl_append({
  type: "SC_AUTOCHAIN_EXIT",
  from: "_SC_orchestrate",
  to: "_SDF_orchestrate_post",
  feature: NAME,
  cycle: SC_PIPELINE_STATE.zyklus_count ?? 0,
  sc_verdict: SC_PIPELINE_STATE.sc_verdict,
  timestamp: ISO
})

Skill(_SDF_orchestrate_post, args="{NAME} --vault={VAULT}")
# _SDF_orchestrate_post fuehrt aus:
#   Phase 3.1 _SDF_berater_recalibrate
#   Phase 3.2 _SDF_berater_postItem
#   Phase 3.3 _SDF_berater_statusTransition
#   Phase 3.5 _SDF_berater_modelSync
#   Phase 4   _SDF_berater_loopDecision
#     → loopDecision Ergebnis:
#       SRS_max >= threshold_high → Skill(_SC_orchestrate, --sc_resume_from=ergebnis)  [SC-again]
#       SRS_max < threshold_high  → Skill(_I_orchestrate, --stage=N --tdd={t|f})       [I-Dispatch]
#       DONE                      → return SDF Phase FINAL
```

---

## [DEPRECATED] Interner DONE_SCHWELLE-Check (INV-MODUS-7, BL-165 PL-11-04)

> **INV-MODUS-7 (BL-165):** SC-Exit ist EXKLUSIV via SDF Phase 1.1 / loopDecision.
> Interne SRS-Threshold-Checks / DONE_SCHWELLE-Logik sind DEPRECATED und wurden
> durch Phase 5 AUTOCHAIN-EXIT ersetzt.
>
> Reminder: Versuch loggt sich als:
>   `[INV-MODUS-7] SC-Self-Exit blockiert: feature={X} cycle={N}`
> SDF-Re-Entry wird erzwungen.
>
> Alt-Code (Z725, vor BL-165): `IF srs < DONE_THRESHOLD: SC.EXIT()` — ENTFERNT.
> Neu: Phase 5 AUTOCHAIN-EXIT (oben) mit Pflicht-Skill(_SDF_orchestrate_post).

---

## POST_HANDOVER (BL-NEW-12, PFLICHT 2026-05-11) — Handschuh-Wechsel zu Post-SDF

> **INV-HANDOVER-1 (SC-Variante):** Wenn SC_orchestrate als Sub-Pipeline von SDF
> gerufen wurde (parent in {_SDF_orchestrate, _SDF_orchestrate_pre}), MUSS es als
> letzten Step `Skill(_SDF_orchestrate_post, ...)` aufrufen. Bei Standalone-SC
> (z.B. /_SC_orchestrate direkt vom User) entfaellt der Handover.
>
> **Grund:** Skill-Context-Override — wenn SC zurueckkehrt und SDF Phase 3
> nicht via expliziten Skill-Call laeuft, vergisst der Lead Phase 3 (BUILD-Sanity,
> Wave 1/2, batchEnde, loopDecision). Siehe BL-NEW-12 Diagnose 2026-05-11.

```
# Allerletzter Schritt — nach Hypothese/Implement/Ergebnis-Zyklus
#
# BL-NEW-12 Fix B2 (2026-05-11): Vereinfacht — kein PIPELINE_CALL_STACK-Check
# (Feld nicht maintained). SC hat naturgemaess zwei Modi:
#   --standalone (User direct /_SC_orchestrate, BDF/W-Pipeline) → kein Handover
#   default (von SDF dispatched in M5/M6/M7) → Handover zu Post-SDF
# Da Standalone-SC fuehlbar ist (User-Direct-Call), MUSS dieser Aufruf explizit
# --standalone setzen. Sonst wird Post-Handover gerufen.

standalone_flag = args.standalone ?? false

# ─── BL-206 AK-5: SC Re-Entry-Signal (NEU 2026-05-24) ─────────────────────
# Nach SC-Done: idf_reentry_signal in sc_handover.md schreiben.
# Wenn dieser SC-Lauf via BL-206 Bottleneck-Route getriggert wurde
# (WP_PIPELINE_STATE.bottleneck_trigger=true ODER modus=M5 mit bottleneck_queue-Match),
# signalisiert dieses Feld an IDF dass SRS-Refresh fuer betroffene PLs noetig ist.
#
# INV-LOOP-2: Nur W{n} die wirklich aktualisiert wurden in updated_w_refs eintragen.
# IDF liest dieses Signal via Phase 0 resumeGuard beim Re-Entry (--from=sdf_finish).

is_bottleneck_sc = (DF_BATCH_STATE.bottleneck_queue != null
                    AND DF_BATCH_STATE.modus == "M5"
                    AND any(item IN (DF_BATCH_STATE.bottleneck_queue.queue_for_sc ?? [])
                            for item in (DF_BATCH_STATE.batch_items ?? [])))

IF is_bottleneck_sc:
  # SC-qualityGate-Output lesen — welche W{n} wurden bestaetigt?
  qg_output     = BERATER_OUTPUTS.qualityGate ?? {}
  updated_w_refs = qg_output.confirmed_wahrheiten ?? []
  affected_items = [item for item in (DF_BATCH_STATE.batch_items ?? [])
                    if item IN (DF_BATCH_STATE.bottleneck_queue.queue_for_sc ?? [])]

  sc_handover_reentry = {
    "idf_reentry":          true,
    "reason":               "SC-Cycle DONE via BL-206 Bottleneck-Route",
    "affected_pl_items":    affected_items,
    "updated_w_refs":       updated_w_refs,
    "srs_refresh_needed":   len(updated_w_refs) > 0,
    "loop_count_increment": 1,
    "completed_at":         now()
  }

  # BL-210 M10 Fix 2026-05-24: Single-Writer-Disziplin restaurieren (INV-MODUS-8).
  # Vorher: direkter Append zu sc_handover.md verletzte _SC_implement Single-Writer-Pflicht (BL-206 AK-5).
  # Fix: schreibe zu separater Datei {bl_folder}/SC/idf_reentry_signal.md.
  # _SC_implement bleibt einziger sc_handover.md-Writer. IDF Re-Entry-Detection liest
  # beide Files (sc_handover.md UND idf_reentry_signal.md) per merged-Read in
  # _IDF_orchestrate Phase 0 BL-206-AK7-Block.
  reentry_signal_path = {bl_folder} + "/SC/idf_reentry_signal.md"
  Write {reentry_signal_path}:
    ---
    type: idf_reentry_signal
    source: _SC_orchestrate_BL_206_AK5
    bl_id: {BL_ID}
    written_at: {now}
    ---
    {sc_handover_reentry as YAML}

  Logge: f"[BL-206 AK-5 + BL-210 M10] SC Re-Entry-Signal geschrieben (Single-Writer-konform): {reentry_signal_path}"
  audit_jsonl_append({
    type: "BL206_SC_REENTRY_SIGNAL",
    affected_items: affected_items,
    w_updated: updated_w_refs,
    target_file: reentry_signal_path,
    single_writer_restored: true
  })

ELSE:
  Logge: "[BL-206 AK-5] Kein Bottleneck-SC-Kontext — kein idf_reentry_signal noetig"
# ─── Ende BL-206 AK-5 ──────────────────────────────────────────────────────

IF standalone_flag == true:
  # SC standalone — kein Handover noetig
  Logge: "[POST-HANDOVER SC] standalone-Modus — SKIP SDF-Post-Handover"
  audit_jsonl_append({type: "POST_HANDOVER_SKIP", from: "_SC_orchestrate", reason: "standalone_flag"})

ELSE:
  # SC wurde von Pre-SDF Phase 2 dispatched (M5/M6/M7-Modus) → Post-SDF muss laufen
  Logge: "[POST-HANDOVER SC] Skill-Wechsel zu Post-SDF (BL-NEW-12)"
  audit_jsonl_append({
    type: "POST_HANDOVER",
    from: "_SC_orchestrate",
    to: "_SDF_orchestrate_post",
    name: NAME,
    timestamp: ISO
  })
  Skill(_SDF_orchestrate_post, args="{NAME} --vault={VAULT}")
```

---

## FEHLERBEHANDLUNG

| Fehler | Aktion |
|--------|--------|
| Agent meldet MCP-Fehler | MCP health_check, bei Timeout: Warte + Retry |
| Agent stagniert (>5min) | SendMessage "Status?" |
| Fehlende Datei | Vorherigen Task pruefen, ggf. wiederholen |
| Implement bricht ab | NON-BLOCKING, Hypothese "OFFEN", weiter zu ergebnis |
| Stagnation >= 7.0 | ABORT-Decision |
| Agent crashed (einzeln) | Neuen Agent spawnen, gleichen Task. Max. 1 Retry. Bei 2. Crash: AskUserQuestion (Skip oder Abort). |
| Partial-Wellen-Failure (<= 50%) | Weiter mit vorhandenen Ergebnissen (degraded). Notiz im Manifest. |
| Partial-Wellen-Failure (> 50%) | Gesamte Welle neu spawnen (max. 1 Retry). Bei erneutem Failure: AskUserQuestion. |
| Vault nicht erreichbar | Degraded Mode: nur RAG |
| Budget erschoepft | FORCE-Decision |

---

## QUICK-START

```
GROSSER ZYKLUS (Default):
1. /_SC_orchestrate X → Team "sc-x" + Tasks
2. PRE-CYCLE: W_fetch → TaskDef → Model
3. SC-CYCLE:  Observe → ModelMaintain → QG → Hypothese
4. /_I_orchestrate X (SYMBIOSE, core I-Pipeline)
5. SC-Ergebnis (misst ECHTE Fortschritte)
6. CONTINUE? → neuer Zyklus | DONE? → Post-Cycle
7. Post-Cycle: HandOff → Gate → W_push → finish
8. HiL: ACCEPT / RETRY / PIVOT / ABORT

INLINE (mit -I): Schritt 4 = /_SC_implement (1 IC, 100 LOC)
REVIEW: Schritt 4 = SKIP, Gate 6 statt Gate 1
ANALYSE: Schritt 4 = SKIP, Saettigungs-basiert (delta_wn)
```

---

ARGUMENTS: $ARGUMENTS
