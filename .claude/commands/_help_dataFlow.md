---
status: active
version: 1.0.0
created: 2026-05-17
updated: 2026-05-17
type: satellite
chain_position: standalone
team_based: false
zweck: "Hochaufloesende Datenfluss-Map des OmniCommand-Systems — von /_init bis Backlog-Item-Lifecycle, mit Read/Write-Matrix und Schwachstellen-Tabelle. Wird nach jedem ParallelArbeit-Foundation-Fix (BL-155, BL-151, BL-156) aktualisiert."
maintenance:
  - Nach BL-155 DONE: S1, S2 als FIXED markieren, Manifest-Split aktualisieren
  - Nach BL-151 DONE: S3, S4, S7, S11 als FIXED markieren, Per-BL-Folder aktualisieren
  - Nach BL-156 DONE: S8, S9 als FIXED markieren, Multi-Worktree-Topologie ergaenzen
---

# /_help_dataFlow — Hochaufloesende Datenfluss-Map (OmniCommand)

```
+======================================================================+
| COMMAND: /_help_dataFlow                                              |
+======================================================================+
|                                                                        |
| ACTOR: DU (die ausfuehrende Claude-Instanz, kein Worker)             |
|                                                                        |
| ZWECK: Komplette Datenfluss-Map des OmniCommand-Systems anzeigen.     |
|        Wer liest/schreibt wo, welche State-Files existieren,           |
|        welche Schwachstellen Parallel-Arbeit blockieren.               |
|                                                                        |
| AUFRUF:                                                                |
|   /_help_dataFlow                                                      |
|                                                                        |
| OUTPUT: ASCII-UML Maps + Read/Write-Matrix + Schwachstellen-Liste     |
|                                                                        |
| LIEST NICHT: Manifest, Vault oder Code — dies ist eine statische      |
|              Referenz-Map. Updates erfolgen manuell nach Foundation-   |
|              Fixes (siehe `maintenance` im Frontmatter).               |
+======================================================================+
```

---

## VERSION + SCHWACHSTELLEN-STATUS

**Map-Version:** 1.0 (2026-05-17, initial nach dataFlow-Analyse)
**Foundation-Phasen-Status:**

| Phase | BL-ID | Status | Wirkt auf Schwachstellen |
|-------|-------|--------|--------------------------|
| Phase 1 | BL-155 BDF_Lock_Manifest_Split | DRAFT/UNREIF | S1, S2 |
| Phase 2 | BL-151 VaultDrivenDevelopment Phase C | TEILWEISE (BL-151 angelegt, Phase C aktivieren) | S3, S4, S7, S11 |
| Phase 3 | BL-156 Multi_Worktree_Parallel_SDF | DRAFT/UNREIF | S8, S9 |

---

## 0. TL;DR — Die 5 Kern-Erkenntnisse

| # | Erkenntnis | Status (Map v1.0) |
|---|------------|-------------------|
| 1 | `_manifest.md` ist GLOBAL pro Vault, nicht pro BL | OFFEN (BL-151 Phase C) |
| 2 | Es gibt KEINEN Filesystem-Lock (`_manifest.lock` nur in BL-151 Spec) | OFFEN (BL-155 Phase 1) |
| 3 | `active_team` ist einzige Single-Writer-Heuristik (Soft-Lock) | OFFEN (BL-155 + BL-151) |
| 4 | BL-151 Per-BL-Folder-Schema entworfen, Migration noch nicht durch | OFFEN (BL-151 Phase C) |
| 5 | BDF ist nicht reentrant-safe — keine Lock auf Outer-Loop | OFFEN (BL-155 Phase 1) |

---

## 1. SYSTEM-TOPOLOGIE (3 Schichten)

```
+--------------------------------------------------------------------+
|  USER-LAYER                                                         |
|  pileOfMud/ -> /_init -> /_A_orchestrate -> ...                    |
+--------------------------------------------------------------------+
                              |
                              v
+--------------------------------------------------------------------+
|  MANAGEMENT-LAYER (WAS-Schicht)                                    |
|                                                                     |
|   /_BL_orchestrate  -------> Reifegrad, A-Trigger, Lifecycle       |
|        |  (terminiert)                                              |
|        v                                                            |
|   /_BDF_orchestrate -------> OUTER-LOOP über Backlog/PL-Items     |
|        |  (single-tenant)                                           |
+--------+-----------------------------------------------------------+
         |
         v
+--------------------------------------------------------------------+
|  EXECUTION-LAYER (WIE-Schicht)                                     |
|                                                                     |
|   /_IDF_orchestrate -------> Spec -> AK -> PL -> Cluster -> Batch  |
|        |  (1 BL -> N PL-Items)                                      |
|        v                                                            |
|   /_SDF_orchestrate -------> Modus-Decision M1..M9 + Item-Loop     |
|        |  (1 Batch sequentiell, BL-156 -> N parallel)              |
|        v                                                            |
|   /_I_orchestrate  --------> TDD/Blueprint pro Stufe              |
|   /_SC_orchestrate --------> Forschung                            |
|   /_TDD_orchestrate -------> Red-Green-Refactor pro Stufe         |
+--------------------------------------------------------------------+
                              |
                              v
+--------------------------------------------------------------------+
|  STATE-LAYER                                                        |
|                                                                     |
|   {VAULT}/_*.md       -- globaler State                            |
|   {VAULT}/Backlog/*/  -- BL-spezifischer Content                  |
|   .claude/            -- Toolbox + ephemere Wellen-Outputs         |
+--------------------------------------------------------------------+
```

---

## 2. PHASE 0: /_init (Einmalig pro Projekt)

```
SCHREIBT:
  {PROJEKT_PFAD}/.claude/         <- Toolbox kopiert
  {PROJEKT_PFAD}/CLAUDE.md        <- NEU (BDF-Regeln)
  {PROJEKT_PFAD}/.claude/INSTRUCTION.md <- NEU
  {PROJEKT_PFAD}/.claude/config/vault-routing.json <- NEU (Source-Leak-frei)
  {VAULT_PATH}/{NAME}/Backlog/    <- MKDIR
  {VAULT_PATH}/_manifest.md       <- BLANK (PHASE=READY)
  {VAULT_PATH}/_parking-lot.md    <- LEER
  {VAULT_PATH}/_backlog_index.md  <- counter=0
  QUELLE/.claude/config/vault-routing.json <- APPEND neue Rule

Schwachstelle: /_init schreibt Quell-vault-routing.json (APPEND nicht atomic).
  -> S12 (NIEDRIG)
```

---

## 3. AKTUELLER VAULT-STATE (Wo wohnt was?)

### 3.1 Globale Files (1 pro Vault, NICHT pro BL!)

```
{VAULT}/OmniCommand/
  -- GLOBAL STATE-FILES (heute) --
  _manifest.md           <- BDF/BL/A/SC/I/IDF/SDF schreiben ALLE hier!
  _manifest_protokoll.md <- Pattern B Rollover
  _backlog_index.md      <- BL-001 bis BL-156
  _session_params.md     <- HiL/difficulty/ceiling/floor
  _parking-lot.md        <- Cross-BL PL-Items
  Task.md                <- AKTUELLE Aufgabe

  -- BL-FOLDER (heute, partial) --
  Backlog/
    BL-{N}-{slug}.md     <- BL-Huelle (Frontmatter)
    BL-{N}-{slug}/       <- Subfolder
      1_Task/Task.md
      2_Model/{Name}_Model.md
      3_Spec/{Name}_Spec.md
      4_K-Score/{Name}-K-SCORE.md
      5_Gap/{Name}-GAP.md
      6_PL/                <- IDF-Output
      crumbs/, SC/, ...
      _manifest.md         <- BL-151 SPEC, NICHT IMPLEMENTIERT!
      _manifest.lock       <- BL-151 SPEC, NICHT IMPLEMENTIERT!
```

### 3.2 Lokale Files (.claude/ pro Worktree-Repo)

```
{PROJEKT}/.claude/                <- Pro Worktree EIGENE Kopie
  -- TOOLBOX (durch /_redeploy synchronisiert) --
  commands/, agents/, scripts/, meta/
  config/vault-routing.json
  settings.local.json

  -- EPHEMERE Wellen-Outputs (pro Pipeline-Lauf) --
  analysis/exploration/, drafts/, synthese/, post-impl/
  analysis/_guard_log.md
  audit/audit.jsonl
  pileOfMud/    <- User-Roh-Eingaben
  output/

  -- LEGACY (deprecated) --
  models/, specs/, Task.md
```

---

## 4. DATENFLUSS eines Backlog-Items (END-TO-END)

```
pileOfMud/{FEATURE}_RAW.md
        |
        v
/_A_orchestrate {NAME} fresh
  Phase 0.1 modusErkennung
  Phase 0.2 discovery
  Phase 0.5 findingsExtraction
  Phase 0.5.2 findingsReview (HiL Checkpoint A)
  Phase 0.6 taskDefinition -> 1_Task/Task.md
  Phase 1.5 git_analyse (optional)
  Phase 2 iddContext (optional)
  Phase 3 model -> 2_Model/{Name}_Model.md
  Phase 3a W_fetch
  Phase 4 spec (HiL Checkpoint B) -> 3_Spec/{Name}_Spec.md
  Phase 4k K_score -> 4_K-Score/{Name}-K-SCORE.md
  Phase 4g gap -> 5_Gap/{Name}-GAP.md
  Phase 4.2a metadatenAggregation -> /_backlog (vergibt BL-Nummer)
  Phase 5 routing -> BDF | IDF
        |
        v
/_IDF_orchestrate {BL_ID}
  Phase 1 INIT
  Phase 2 SPEC_PARSE
  Phase 3 AK_PER_PL (akExtraktion parallel, plAggregation, validator, itemContext)
  Phase 4 DEP_MATRIX
  Phase 5 CLUSTERING (Mitose-Signal)
  Phase 6 SEQUENCE_PLANNER -> items_routed_ready
  Phase 7 BATCH_PLAN -> DF_BATCH_STATE.batch_items
        |
        v
/_BDF_orchestrate (Outer-Loop)
  Phase 1 INIT
  Phase 2 SCANNING (PL + BL merge, Reifegrad-Banding, Dependency-Check)
  Phase 3 BATCH_PLANNING (Skill _BDF_batchPlan)
  Phase 4 ITEM_RUNNING -> Skill(_SDF_orchestrate --batch=...)
  Phase 5 ITEM_DONE
  Phase 6 Loop oder EMPTY -> testRun -> DONE
        |
        v
/_SDF_orchestrate --batch=PL-1,PL-2,...
  Phase 0 PRE-LOAD
  Phase 1.6 IDF-GATE (falls IDF noch nicht lief)
  Phase 1.1 modusEntscheidung (C3 berechnet M1..M9)
  Phase 2 executionDispatch
    M1 INLINE     -> SC_implement
    M2 STANDARD   -> I_orchestrate FULL
    M5 SC_INLINE  -> SC + I core
    M7 SC_PURE    -> nur SC
    M9 WP         -> Whitepaper-Pipeline
  Phase 3 BATCH_ENDE (recalibrate, GAP-Check, stage)
  Phase 4 LOOP_DECISION (ROLLBACK | TERMINATE | RE-BATCH)
        |
        v
/_I_orchestrate (Stufen-Loop)
  Phase 0 RESUME-GUARD
  Phase 1 TEAM_SETUP
  Pro Stufe N=1..5:
    Blueprint: cleanCodeArchitect -> requirementCheck -> patternLibrary ->
               testSearch -> goldDefine -> blueprintQG -> cleanCodeSlice ->
               mitose -> fanOut
    TDD: /_TDD_orchestrate (RGR pro Stufe)
    Stage-Transition -> zurueck SDF
  EXIT: verify global -> Scope-Gate -> Rollover

  Hub-Invariante: SC <-> SDF <-> I <-> SDF <-> TDD (NIE direkt SC->I!)
```

---

## 5. READ/WRITE-MATRIX

### 5.1 Vault Process-State-Files (GLOBAL — Kollisions-Hotspots!)

```
                          | /_init | /_A | /_BL | /_BDF | /_IDF | /_SDF | /_SC | /_I  | /_TDD | Guards |
--------------------------+--------+-----+------+-------+-------+-------+------+------+-------+--------|
{VAULT}/_manifest.md      | INIT   |  W  |  W   |   W   |   W   |   W   |  W   |  W   |   R   |   R    |
   |- A_PIPELINE_STATE    |   -    |  W  |  R   |   R   |   R   |   R   |  R   |  R   |   -   |   -    |
   |- BL_LIFECYCLE_STATE  |   -    |  -  |  W   | W(R)  |   R   |   R   |  -   |  -   |   -   |   -    |
   |- BDF_PIPELINE_STATE  |   -    |  -  |  R   |   W   |   R   |   R   |  -   |  -   |   -   |   -    |
   |- BDF_BATCH_STATE     |   -    |  -  |  -   |   W   |   R   |   R   |  R   |  R   |   -   |   -    |
   |- IDF_PIPELINE_STATE  |   -    |  R  |  R   |   R   |   W   |   R   |  -   |  -   |   -   |   -    |
   |- DF_PIPELINE_STATE   |   -    |  -  |  -   |   R   |   R   |   W   |  R   |  R   |   R   |   -    |
   |- DF_BATCH_STATE      |   -    |  -  |  -   |   R   |   W   |   W   |  R   |  R   |   -   |   -    |
   |- SC_PIPELINE_STATE   |   -    |  -  |  -   |   -   |   -   |   R   |  W   |  R   |   -   |   -    |
   |- I_PIPELINE_STATE    |   -    |  -  |  -   |   -   |   -   |   R   |  R   |  W   |   R   |   -    |
   |- BERATER_OUTPUTS.*   |   -    |  W  |  -   |   -   |   W   |   W   |  W   |  W   |   -   |   -    |
   |- active_team         |   -    |  W  |  -   |   W   |   W   |   W   |  W   |  W   |   -   |   -    |
   |- FACTORY_STATES      |   -    |  -  |  -   |   W   |   R   |   W   |  -   |  -   |   -   |   -    |
                          |        |     |      |       |       |       |      |      |       |        |
{VAULT}/_manifest_prot... |   -    |  W  |  -   |   W   |   -   |   W   |  W   |  W   |   -   |   -    |
{VAULT}/_backlog_index.md | INIT   |  W  |  W   |   W   |   R   |   R   |  -   |  -   |   -   |   R*   |
{VAULT}/_session_params   |  W*    |  R  |  R   |   R   |   R   |   W   |  R   |  R   |   R   |   R    |
{VAULT}/_parking-lot.md   | INIT   |  -  |  -   |  W**  |  W    |   W   |  W   |  -   |   -   |   R*   |

W=Write  R=Read  INIT=Erstellt
W*=nur ueber /_param   W**=nur STUCKED [!] (Ausnahme)   R*=Guards lesen fuer Enforcement
```

### 5.2 BL-Folder Files (PRO BL — bessere Isolation)

```
{VAULT}/Backlog/BL-{N}-{slug}/   | /_A | /_IDF | /_SDF | /_I  | /_SC  | /_TDD |
---------------------------------+-----+-------+-------+------+-------+-------|
 1_Task/Task.md                  |  W  |   R   |   R   |  R   |   R   |   R   |
 2_Model/*_Model.md              |  W  |   R   |   R   |  R   |   W   |   R   |
 3_Spec/*_Spec.md                |  W  |   R   |   R   |  R   |   R   |   R   |
 4_K-Score/*-K-SCORE.md          |  W  |   R   |   R   |  R   |   R   |   -   |
 5_Gap/*-GAP.md                  |  W  |   R   |   R   |  R   |   R   |   -   |
 6_PL/PL-*.md (PL-Items)         |  -  |   W   |   R   |  R   |   R   |   -   |
 crumbs/*_findings_crumbs.md     |  W  |   R   |   R   |  R   |   R   |   -   |
 SC/*-OBSERVE*.md                |  -  |   -   |   R   |  R   |   W   |   -   |
 SC/*-HANDOFF.md                 |  -  |   -   |   -   |  R   |   W   |   -   |
 Implementation/                 |  -  |   -   |   -   |  W   |   -   |   W   |
 _manifest.md (BL-151 SPEC)      |  -  |   -   |   -   |  -   |   -   |   -   |  <- NICHT IMPL.
```

---

## 6. SCHWACHSTELLEN-LISTE (Priorisiert + Foundation-Mapping)

| # | Schwachstelle | Risiko | Status | Fix-BL | Fix-Vorschlag |
|---|---------------|--------|--------|--------|----------------|
| **S1** | `_manifest.md` global, 12+ State-Bloecke | KRITISCH | OFFEN | BL-155+BL-151 | Manifest-Split BDF/BL/Session |
| **S2** | Kein FS-Lock auf BDF (re-entrant) | KRITISCH | OFFEN | BL-155 | `_bdf_manifest.lock` mit fcntl/msvcrt |
| **S3** | Kein FS-Lock pro BL | KRITISCH | OFFEN | BL-151 | `_manifest.lock` pro BL-Folder |
| **S4** | `active_team` killt fremde Teams (Cleanup) | HOCH | OFFEN | BL-151 | Per-BL `active_team` |
| **S5** | `_session_params.md` Cross-Worktree-Kollision | HOCH | OFFEN | NEU | Per-Worktree oder User-Lock |
| **S6** | `_backlog_index.md` Counter nicht atomic | MITTEL | OFFEN | BL-151 W6 | fcntl.LOCK_EX vor Counter-Increment |
| **S7** | BDF lokales Manifest vs BL-151 Folder | HOCH | OFFEN | BL-151 | INV-VAULT-9 Resolver durchziehen |
| **S8** | FACTORY_STATES Multi-Tenant Schema da, nicht aktiv | MITTEL | OFFEN | BL-156 | v2 Worktree-Lifecycle aktivieren |
| **S9** | Message-Files SDF<->BDF nicht implementiert | NIEDRIG | OFFEN | BL-156 | Hub-and-Spoke Message-Pattern |
| **S10** | Guards laufen LOKAL, kein Cross-Audit | NIEDRIG | OFFEN | NEU | Audit zentral in Vault |
| **S11** | Migration Legacy .claude/analysis/_manifest.md unvollstaendig | MITTEL | OFFEN | BL-151 | Phase C Migration |
| **S12** | /_init schreibt Quell-vault-routing.json (APPEND nicht atomic) | NIEDRIG | OFFEN | NEU | fcntl.LOCK_EX um Append |

---

## 7. ZIEL-ARCHITEKTUR (Nach Phase 1 + 2 + 3)

```
+======================================================================+
|  VAULT-FIRST (Cross-Session, Multi-BL persistent)                    |
+======================================================================+
|                                                                       |
|  {VAULT}/                                                            |
|  +- _backlog_index.md            <- GLOBAL Cross-BL                  |
|  +- _parking_lot_global_index.md <- GLOBAL Cross-BL                  |
|  +- _session_params.md           <- GLOBAL User-Defaults             |
|  +- _findings_index.md           <- GLOBAL Findings-Lookup           |
|  +- _bdf_manifest.md             <- BDF/BL/Factory-State (BL-155) NEU|
|  +- _bdf_manifest.lock           <- Exklusiv-Lock BDF (BL-155) NEU   |
|  |                                                                    |
|  +- Backlog/                                                          |
|      +- BL-{N}-{slug}/           <- WORKING_DIR PRO BL (BL-151)      |
|          +- _manifest.md          <- BL-spezifisch (BL-151 Phase C)  |
|          +- _manifest.lock        <- FS-Lock pro BL (BL-151) NEU     |
|          +- _parking_lot_index.md                                     |
|          +- ParkingLot/PL-*.md                                        |
|          +- 1_Task/Task.md                                            |
|          +- 2_Model/, 3_Spec/, 4_K-Score/, 5_Gap/                    |
|          +- 6_PL/, crumbs/, SC/, Implementation/                     |
|                                                                       |
+======================================================================+
|  LOKAL pro Worktree (.claude/)                                        |
+======================================================================+
|                                                                       |
|  .claude/                                                             |
|  +- commands/, agents/, scripts/, meta/   <- Toolbox (synced)        |
|  +- config/vault-routing.json    <- Lokal                            |
|  +- settings.local.json          <- Lokal                            |
|  +- analysis/                    <- Ephemere Wellen-Outputs          |
|  +- audit/audit.jsonl            <- Lokal                            |
|  +- pileOfMud/                   <- User-Inputs                       |
|  +- output/                      <- Ephemere Artefakte               |
|                                                                       |
|  + BL-156: .worktrees/SDF_{id}/  <- N parallele SDFs in Worktrees   |
|  + BL-156: .claude/messages/      <- Hub-and-Spoke SDF<->BDF         |
|                                                                       |
+======================================================================+
```

---

## 8. CONTRACT-BUCH (Wer ruft wen — IMMER via Skill!)

```
                       +----------------------+
                       | User                  |
                       +-----------+----------+
                                   |
        +--------------------------+--------------------------+
        |                          |                          |
        v                          v                          v
+--------------+         +--------------+          +--------------+
| /_init       |         |/_A_orchestr. |          |/_BL_orchestr.|
| (Standalone) |         |              |          | (Term. 1x)   |
+--------------+         +------+-------+          +------+-------+
                                |                          |
                                |  +-----------------------+
                                |  | AUTO-CHAIN (items_routed_ready > 0)
                                v  v
                       +------------------+
                       |/_BDF_orchestrate |
                       |  (Outer-Loop)    |
                       +--------+---------+
                                |  (Skill, NIE Agent!)
                                |  --batch=PL-1,PL-2,...
                                v
                       +------------------+
                       |/_IDF_orchestrate |
                       |  (Spec->PL)      |
                       +--------+---------+
                                |
                                v
                       +------------------+
                       |/_SDF_orchestrate |
                       |  (Modus M1..M9)  |
                       |                  |
                       |  Phase 1 C3 ->   |
                       |  executionDispatch|
                       +--------+---------+
                                |
                +---------------+---------------+
                v               v               v
         +-----------+  +-----------+  +-----------+
         |/_SC_orch. |  |/_I_orch.  |  |/_WP_orch. |
         +-----+-----+  +-----+-----+  +-----------+
               |              |
               |              v
               |       +-----------+
               +-----> |/_TDD_orch.|   Hub-Invariante:
                       +-----------+   SC<->SDF<->I<->SDF<->TDD
                                       (NIE direkt SC->I!)

  Skill()-Pflicht (INV-PM-2):
    BDF -> SDF: Skill(skill="_SDF_orchestrate", args="...")
    SDF -> I:   Skill(skill="_I_orchestrate", args="...")
    SDF -> SC:  Skill(skill="_SC_orchestrate", args="...")
    NIE: Agent(prompt="...") fuer Orchestrator-Calls!

  Berater-Pattern (Thin-Manager):
    A_orchestrate ruft 9 _A_berater_* via Skill()
    IDF_orchestrate ruft 12 _IDF_berater_* via Skill()
    SDF_orchestrate ruft 8 _SDF_berater_* via Skill()
    Jeder Berater schreibt NUR seinen BERATER_OUTPUTS-Slot (INV-THIN-3)
```

---

## 9. EXISTIERENDE LOCK-MECHANISMEN

| Mechanismus | Wo | Was schuetzt es | Aktiv? |
|-------------|-----|------------------|--------|
| `active_team` Manifest-Field | `_manifest.md` | Soft-Single-Writer | JA (aber kill-on-conflict) |
| `TeamCreate`/`TeamDelete` Lifecycle | Alle Orchestratoren | 1 Team pro Pipeline | JA (in same Session) |
| `enforceProcess` Guard | `_session_params.md` | Schreib-Blockierung State-Files | JA |
| `guard_state_file_protection.py` | Hook | Blockiert manuelle Edits | JA |
| `guard_session_params_protection.py` | Hook | Verhindert difficulty-Upgrade | JA |
| `is_dark_factory_active()` Check | Guards | SDF/BDF duerfen editieren | JA |
| `hash_cache.py` fcntl.LOCK_EX | `_session_params.md` Cache | atomic hash_cache | JA |
| `bdf_bl_handoff_depth` Counter | BDF | Anti-Zirkel BDF<->BL | JA (Soft) |
| `bdf_scan_iterations` Hard-Break | BDF | Endlosschleifen-Schutz | JA (Soft) |
| `_manifest.lock` Filesystem-Lock | BL-151 Spec | atomic Manifest-Write | **NICHT IMPL.** |
| Per-BL-Folder `_manifest.md` | BL-151 Spec | Manifest-Isolation pro BL | **NICHT IMPL.** |
| `vault_index_first.py` Hook | BL-151 Spec | INV-VAULT-1..9 Enforcement | **NICHT IMPL.** |
| Worktree-Lifecycle Multi-SDF | BL-156 (geplant) | Parallele SDFs | **GEPLANT** |
| Message-Files SDF<->BDF | BL-156 (geplant) | Cross-Worktree Sync | **GEPLANT** |

---

## 10. MIGRATIONS-PFAD (3 Phasen)

```
Phase 1 (BL-155) - SOFORT, niedrig-invasiv:
  - BDF-Lock: {VAULT}/_bdf_manifest.lock mit fcntl/msvcrt
  - _bdf_manifest.md aus _manifest.md herausloesen
  -> Verhindert parallele BDF-Worker
  -> Fix: S1 (teilweise), S2

Phase 2 (BL-151) - MITTELFRISTIG:
  - INV-VAULT-9 Resolver in allen Orchestratoren
  - Per-BL _manifest.md aktivieren
  - vault_index_first.py Hook scharf schalten
  -> 2 Worktrees auf 2 BLs sind isoliert
  -> Fix: S3, S4, S7, S11

Phase 3 (BL-156) - LANGFRISTIG, nach Phase 1+2:
  - FACTORY_STATES multi-tenant aktivieren
  - Worktree-Lifecycle in BDF integrieren
  - Message-Files SDF<->BDF
  -> N SDFs parallel innerhalb 1 BDF
  -> Fix: S8, S9

BL-155 dep: keine
BL-151 dep: keine (Foundation existiert)
BL-156 dep: BL-155 + BL-151 (HART)
```

---

## 11. PFLEGE / WANN UPDATEN

Diese Map ist eine eingefrorene Referenz (Map v1.0 stand 2026-05-17). Sie wird
aktualisiert nach:

- **BL-155 DONE:** S1 (teilweise), S2 als FIXED markieren, Sektion 5.1 Manifest-Block-Split einfuegen, Sektion 9 Lock-Mechanismen aktualisieren
- **BL-151 DONE (Phase C):** S3, S4, S7, S11 als FIXED markieren, Sektion 3.1 Per-BL _manifest.md einbauen, Read/Write-Matrix umstrukturieren
- **BL-156 DONE:** S8, S9 als FIXED markieren, Sektion 7 Ziel-Architektur als Ist-Stand uebernehmen, Multi-Worktree-Topologie ausarbeiten

Version-Bumps:
- v1.0 (2026-05-17): Initial nach dataFlow-Analyse
- v1.1: nach BL-155 DONE
- v1.2: nach BL-151 Phase C DONE
- v2.0: nach BL-156 DONE (Ziel-Architektur erreicht)

---

ARGUMENTS: $ARGUMENTS
