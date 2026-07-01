# /_BL_orchestrate - Backlog Lifecycle Manager (Block A, WAS-Schicht)

```yaml
status: active
version: 1.3.0
created: 2026-04-06
updated: 2026-04-11
op: BacklogLifecycle
phase: Meta
type: factory
chain_position: pre-bdf
team_based: false
```

---

```
+======================================================================+
| META-COMMAND: /_BL_orchestrate                                        |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU — reiner Orchestrator)                          |
|   CONSTRAINT: Team Lead fuehrt KEINE Sub-Commands selbst aus.        |
|   NUR spawnen, tracken, entscheiden.                                  |
|                                                                        |
| PRINZIP: BL = Einmal-Lauf (On-Demand, kein Loop).                    |
|          Bewertet Backlog-Items, routet, eskaliert.                   |
|          State lebt im MANIFEST (BL_LIFECYCLE_STATE).                 |
|          Kommunikation BL↔BDF: NUR ueber Dateien (R1).              |
|                                                                        |
| AUFRUF:                                                                |
|   /_BL_orchestrate [ceiling=opus] [floor=haiku]                       |
|                                                                        |
| LIEST:                                                                 |
|   {VAULT}/_manifest.md                (BL_LIFECYCLE_STATE,            |
|                                        items_stucked[]) — global     |
|   {WORKING_DIR}/_manifest.md          (A_PIPELINE_STATE)              |
|                                       — per-Story (BL-155 AK-1)       |
|   {VAULT}/_backlog_index.md           (status DRAFT/READY)          |
|     !! BL-178 INV-INDEX-SPLIT-5: NUR Active-Index lesen.            |
|     Archive (_backlog_index_done.md) NICHT lesen — Token-Waste.     |
|   {VAULT}/Backlog/*.md (Vault-Frontmatter:           |
|                                         reifegrad, dependencies,      |
|                                         k_score, needs_a_pipeline)    |
|   .claude/models/{NAME}_Model.md       (W{n} zaehlen)                |
|                                                                        |
| SCHREIBT:                                                              |
|   {VAULT}/_manifest.md                (BL_LIFECYCLE_STATE Block)     |
|   {VAULT}/_backlog_index.md           (status DRAFT->READY)         |
|   {VAULT}/Backlog/*.md (reifegrad,                   |
|                                         needs_a_pipeline nach         |
|                                         A-Pipeline)                   |
|                                                                        |
| SCHREIBT NICHT:                                                        |
|   {VAULT}/_manifest.md BDF_PIPELINE_STATE                            |
|   {VAULT}/_parking-lot.md                                            |
|   .claude/commands/_BDF_orchestrate.md                                |
|   .claude/commands/_SDF_orchestrate.md                                |
+======================================================================+
```

---

## ANTI-PATTERN Guard (AK-01-03)

```
╔══════════════════════════════════════════════════════════════════════╗
║  KERN-INVARIANTE: BL ist reiner Bewerter — KEIN Executor            ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                      ║
║  VERBOTEN:                                                           ║
║    Agent(prompt="...") direkt spawnen                                ║
║    Skill("_BDF_orchestrate") aufrufen (kein Zirkel)                 ║
║      AUSNAHME: Phase 9 AUTO-CHAIN (BL-046)                          ║
║        Skill("_BDF_orchestrate") in Phase 9 DONE ist ERLAUBT wenn  ║
║        items_routed_ready > 0 (Loop-Terminierung via BDF-Semantik)  ║
║    Skill("_SDF_orchestrate") aufrufen (INV-4: BL entscheidet        ║
║      nicht ueber SDF-Modi)                                           ║
║                                                                      ║
║  ERLAUBT:                                                            ║
║    Skill("_A_orchestrate")   → A-Pipeline fuer UNREIF-Items         ║
║    Skill("_WP_orchestrate")  → Whitepaper-Recherche                 ║
║    Skill("_SC_orchestrate")  → SC-Pipeline fuer Forschungs-Items    ║
║    Skill("_I_mitose")        → Zerlegung bei k_score > 70           ║
║                                                                      ║
║  PROZESS-INVARIANTEN (erbt von BDF RF-BDF-022):                     ║
║    INV-PM-2: Handschuh-Wechsel = Skill() — Agent() ist VERLETZUNG  ║
║    INV-5:  Single-Writer auf BL_LIFECYCLE_STATE (Ausnahme:          ║
║            items_stucked[] von BDF geschrieben)                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## State-Machine (5 aktive Phasen, terminiert nach 1 Lauf)

```
INIT → LIFECYCLE_CHECK → WAHRHEITEN_ROUTING → A_PIPELINE_TRIGGER → DONE

Phase 4 TRIAGE + Phase 5 DEPENDENCY_RESOLVE + Phase 6 MITOSE_CHECK +
Phase 8 STATUS_UPDATE entfernt (BL-078b).
TRIAGE/DEPENDENCY ohne Konsument nach Phase 8 Streichung (Batch B).
Mitose wandert nach BL-077, Status-Promotion via IDF Phase 6 BATCH_SEQUENCE.
Dependencies leben jetzt in BL-Vault-Knoten Frontmatter (BDF Phase 2b).

Kein OUTER LOOP. Kein Polling. Terminiert nach DONE.
```

---

## Phase 1: INIT

```
# Parameter parsen
bl_ceiling = $ARGUMENTS.ceiling ?? "opus"
bl_floor   = $ARGUMENTS.floor ?? "haiku"

# BL_LIFECYCLE_STATE initialisieren (backward-kompatibel: Feld kann fehlen)
Lies {VAULT}/_manifest.md → BL_LIFECYCLE_STATE ?? {}
Schreibe in {VAULT}/_manifest.md → BL_LIFECYCLE_STATE:
  bl_status: RUNNING
  last_run: {Datum ISO}
  lifecycle_phase: null
  items_evaluated: 0
  items_escalated: []
  items_routed_ready: 0
  items_routed_sc: 0
  items_routed_unreif: 0
  wahrheiten_routing: null
  w_total: 0
  w_confirmed: 0
  w_offen: 0
  w_maturity_level: null
  last_a_pipeline_run: null
  # items_stucked[] wird NICHT initialisiert — von BDF geschrieben, hier nur gelesen

Logge: "=== BACKLOG LIFECYCLE GESTARTET ==="
Logge: "Ceiling: {bl_ceiling}, Floor: {bl_floor}"
```

## Phase 2: LIFECYCLE_CHECK

```
# ═══ Teil A: Lebenszyklus-Erkennung (migriert aus BDF Z.355-373, RF-BDF-016) ═══
# Heuristik: GAP-Score + Model-Reife bestimmen Phase
Lies {WORKING_DIR}/_manifest.md → A_PIPELINE_STATE_{NAME}
bl_gap_percent     = A_PIPELINE_STATE.gap_percent ?? 100
bl_model_maturity  = A_PIPELINE_STATE.model_maturity ?? "0%"

IF bl_gap_percent > 50 OR bl_model_maturity < "30%":
  lifecycle_phase = "INITIAL"
  Logge: "Lebenszyklus-Phase: INITIAL (GAP={bl_gap_percent}%, Reife={bl_model_maturity})"
  Logge: "  → Schwere Analyse empfohlen, volles Model bauen"
ELIF bl_gap_percent < 20:
  lifecycle_phase = "LAUFEND"
  Logge: "Lebenszyklus-Phase: LAUFEND (GAP={bl_gap_percent}%, Reife={bl_model_maturity})"
  Logge: "  → Aufbauen auf bestehendes Wissen, leichtere Analyse"
ELSE:
  lifecycle_phase = "UEBERGANG"
  Logge: "Lebenszyklus-Phase: UEBERGANG (GAP={bl_gap_percent}%, Reife={bl_model_maturity})"

Schreibe in {VAULT}/_manifest.md → BL_LIFECYCLE_STATE.lifecycle_phase: {lifecycle_phase}

# ═══ Teil B: Backward-Kanal items_stucked[] lesen (Task.md T7) ═══
# items_stucked[] wird von BDF geschrieben — BL liest und reagiert
items_stucked = BL_LIFECYCLE_STATE.items_stucked ?? []

IF items_stucked.length > 0:
  Logge: "[LIFECYCLE_CHECK] {items_stucked.length} STUCKED-Items im Backward-Kanal"
  FOR stucked_item IN items_stucked:
    vault_path = Finde Vault-Knoten fuer {stucked_item.name}
    IF exists(vault_path):
      bl_reifungsrunden = Lies vault_path → Frontmatter.bl_reifungsrunden ?? 0
      bl_reifungsrunden = bl_reifungsrunden + 1
      Schreibe vault_path → Frontmatter.bl_reifungsrunden: {bl_reifungsrunden}
      Logge: "[LIFECYCLE_CHECK] {stucked_item.name}: bl_reifungsrunden={bl_reifungsrunden} (Grund: {stucked_item.reason})"
      IF bl_reifungsrunden >= 3:
        Logge: "[LIFECYCLE_CHECK] {stucked_item.name}: bl_reifungsrunden >= 3 → PO-Trigger/FREEZE (EK-4)"
        items_escalated.append(stucked_item.name)
ELSE:
  Logge: "[LIFECYCLE_CHECK] Kein STUCKED-Item im Backward-Kanal"
```

## Phase 3: WAHRHEITEN_ROUTING

```
# ═══ Model-Reife berechnen (migriert aus BDF Z.375-427, RF-02 AK-02-01..04) ═══
# intern → /_A_orchestrate resync (Model aktualisieren)
# extern → /_WP_orchestrate (Whitepaper-Recherche)

model_path = "{WORKING_DIR}/.claude/models/{NAME}_Model.md"
IF exists(model_path):
  model = lies(model_path)
  w_total     = zaehle W{n} Eintraege in model
  w_confirmed = zaehle W{n} mit Status [BEST] oder [BESTAETIGT]
  w_offen     = zaehle W{n} mit Status [OFFEN]

  # AK-02-02: intern/extern Klassifizierung
  # Fallback: Nutze w_extern_count/w_intern_count aus Model-Frontmatter
  w_extern = model.frontmatter.w_extern_count ?? 0
  w_intern = model.frontmatter.w_intern_count ?? 0

  # AK-02-04: Reife-Ratio berechnen (HIGH>=70%, MEDIUM 40-70%, LOW<40%)
  IF w_total > 0:
    maturity_ratio = w_confirmed / w_total
    IF maturity_ratio >= 0.70: maturity_level = "HIGH"
    ELIF maturity_ratio >= 0.40: maturity_level = "MEDIUM"
    ELSE: maturity_level = "LOW"
  ELSE:
    maturity_ratio = 0
    maturity_level = "LOW"
  Logge: "[WAHRHEITEN-ROUTING] Model-Reife: {maturity_level} ({w_confirmed}/{w_total}, {maturity_ratio*100:.0f}%)"

  # AK-02-03: Routing-Entscheidung
  IF w_offen > 0 AND w_extern >= 2 AND w_extern > w_intern:
    Logge: "[WAHRHEITEN-ROUTING] {w_extern} EXTERN W{n} offen → WP-Kandidat"
    routing_empfehlung = "WP_KANDIDAT"
  ELIF w_offen > 0 AND w_intern >= 1:
    Logge: "[WAHRHEITEN-ROUTING] {w_intern} INTERN W{n} offen → resync-Kandidat"
    routing_empfehlung = "RESYNC_KANDIDAT"
  ELSE:
    Logge: "[WAHRHEITEN-ROUTING] Alle W{n} bestaetigt oder kein klares Signal"
    routing_empfehlung = "KEINE_AKTION"

  Schreibe in {VAULT}/_manifest.md → BL_LIFECYCLE_STATE:
    w_total: {w_total}
    w_confirmed: {w_confirmed}
    w_offen: {w_offen}
    w_maturity_level: {maturity_level}
    wahrheiten_routing: {routing_empfehlung}
ELSE:
  # Graceful Degradation: fehlendes Model → KEINE_AKTION, kein Crash
  Logge: "[WAHRHEITEN-ROUTING] Kein Model vorhanden — KEINE_AKTION (Graceful Degradation)"
  routing_empfehlung = "KEINE_AKTION"
  Schreibe in {VAULT}/_manifest.md → BL_LIFECYCLE_STATE.wahrheiten_routing: "KEINE_AKTION"
```

## Phase 4: TRIAGE — ENTFERNT (BL-078b, nach BL-076 IDF ohne Konsument)
# Die 5-Kategorien-Klassifikation (komplex/forschung/prozess/...) wurde
# ausschliesslich von Phase 8 STATUS_UPDATE konsumiert, welche in BL-078b
# Batch B entfernt wurde. BL_orchestrate ist jetzt schlanker
# Lifecycle-Hook.

## Phase 5: DEPENDENCY_RESOLVE — ENTFERNT (BL-078b, nach BL-076 ohne Konsument)
# BL-Item-Dependency-Check wanderte als Responsibility in die BL-Vault-Knoten
# Frontmatter (dependencies: [...]) und wird von BDF gelesen in Phase 2b.
# Diese Phase hat die Ergebnisse nur an Phase 8 weitergegeben, die jetzt
# entfernt ist.

## Phase 6: MITOSE_CHECK — ENTFERNT (BL-078b, BL-077 Vorbereitung)

# Dead-Code: _I_mitose erwartete ARCHITECT.md, nicht BL-Items.
# Mitose-Entscheidung wandert nach BL-077 (BL_split Prozess) im Kontext
# von IDF Phase 5 CLUSTERING mitose_signal.

## Phase 7: A_PIPELINE_TRIGGER

```
# ═══ needs_a_pipeline=true → Skill(_A_orchestrate) (migriert aus BDF Z.536-579) ═══
# BL-Items die via /_backlog intake erstellt wurden haben needs_a_pipeline=true.
# A-Pipeline: pileOfMud → Findings → Model → Spec → K-Score → Gap → Reifegrad.
# Nach A-Pipeline: needs_a_pipeline=false, reifegrad wird von A-Pipeline gesetzt.
#
# Nach BL-078b Batch C: Phase 4 TRIAGE entfernt, daher liest Phase 7 die
# Items direkt aus dem Backlog-Index (kein bl_items[] mehr).

a_pipeline_items = []
IF exists("{VAULT}/_backlog_index.md"):
  bl_raw = Lies {VAULT}/_backlog_index.md
  bl_candidates = Filtere Items mit Status IN ("DRAFT", "READY")
  FOR item IN bl_candidates:
    vault_path = item.vault_path
    IF NOT exists(vault_path):
      Logge: "[A-PIPELINE-TRIGGER] WARN: BL-{item.id} Vault-Knoten nicht lesbar — uebersprungen"
      CONTINUE
    item.vault_frontmatter = Lies vault_path → Frontmatter (YAML)
    IF item.vault_frontmatter.needs_a_pipeline == true:
      a_pipeline_items.append(item)

IF a_pipeline_items.length > 0:
  Logge: "[A-PIPELINE-TRIGGER] {a_pipeline_items.length} Items brauchen A-Pipeline"
  FOR a_item IN a_pipeline_items:
    Logge: "[A-PIPELINE-TRIGGER] BL-{a_item.id}: {a_item.title} — Handschuh-Wechsel zu A-Pipeline"
    # HANDSCHUH-WECHSEL: BL → A_orchestrate (Fresh, INV-PM-2)
    Skill(skill="_A_orchestrate", args="{a_item.title} fresh normal {bl_ceiling} {bl_floor} --entry-point=bl")

    # Nach A-Pipeline: completion_signal lesen
    Lies A_PIPELINE_STATE aus _manifest.md
    IF A_PIPELINE_STATE.phase IN ["COMPLETED", "COMPLETED_TRANSKRIPT_ONLY"]:
      Schreibe a_item.vault_frontmatter.needs_a_pipeline = false
      Schreibe a_item.vault_frontmatter.reifegrad = A_PIPELINE_STATE.backlog_item_reifegrad ?? "SC-REIF"
      Schreibe a_item.vault_frontmatter.spec_link = A_PIPELINE_STATE.spec_link ?? null
      Schreibe a_item.vault_frontmatter.k_score   = A_PIPELINE_STATE.k_score ?? null
      Aktualisiere _backlog_index.md (Reifegrad-Spalte fuer BL-{a_item.id})
      Logge: "[A-PIPELINE-TRIGGER] BL-{a_item.id}: A-Pipeline DONE → reifegrad={a_item.vault_frontmatter.reifegrad}"
      # Reifegrad aktualisieren (fuer Folge-Konsumenten via Vault-Frontmatter)
      a_item.reifegrad = a_item.vault_frontmatter.reifegrad
    ELSE:
      Logge: "[A-PIPELINE-TRIGGER] BL-{a_item.id}: A-Pipeline NICHT abgeschlossen — bleibt UNREIF"

    IF A_PIPELINE_STATE.completion_signal == "ready_for_bdf_rescan":
      Manifest: A_PIPELINE_STATE.completion_signal = null  # Reset
  Schreibe in {VAULT}/_manifest.md → BL_LIFECYCLE_STATE.last_a_pipeline_run: {Datum ISO}
```

## Phase 8: STATUS_UPDATE — ENTFERNT (BL-078b, AK-09 Dual-Write Fix)

# items_routed_ready wird nach BL-076 ausschliesslich von IDF Phase 6
# BATCH_SEQUENCE geschrieben. BL_LIFECYCLE_STATE.items_routed_ready
# Reader in BDF Z598 unveraendert.
# BL-075 T2 Reifungs-Loop liest direkt vom IDF-Write.
# DRAFT→READY Status-Promotion ist nach BL-076 Migration Responsibility
# des BL-Items selbst via /_A_orchestrate Phase 4.2b.

# Phase 9 AUTO-CHAIN liest items_routed_ready aus BL_LIFECYCLE_STATE
# (geschrieben von IDF Phase 6 BATCH_SEQUENCE).
items_routed_ready = BL_LIFECYCLE_STATE.items_routed_ready ?? 0
items_routed_sc    = BL_LIFECYCLE_STATE.items_routed_sc ?? 0
items_routed_unreif = BL_LIFECYCLE_STATE.items_routed_unreif ?? 0

## Phase 9: DONE

```
# BL_LIFECYCLE_STATE finalisieren
Schreibe in {VAULT}/_manifest.md → BL_LIFECYCLE_STATE:
  bl_status: DONE
  last_run: {Datum ISO}

Logge: "=== BACKLOG LIFECYCLE DONE ==="
Logge: "Items evaluiert: {items_evaluated}"
Logge: "Routing: READY={items_routed_ready}, SC={items_routed_sc}, UNREIF={items_routed_unreif}"
Logge: "Eskalationen: {items_escalated.length}"
Logge: "Lifecycle-Phase: {lifecycle_phase}"
Logge: "Wahrheiten-Routing: {routing_empfehlung}"

# ═══ BL-075 T2 + BL-078 AK-03: Phase 9 AUTO-CHAIN Guard ═══
# Bei --mode=recheck: SKIP Phase 9, Aufrufer wartet auf Return.
# --from=bdf_empty  (BL-075): BDF Phase 2 EMPTY-Handler Delegation
# --from=sdf_finish (BL-078): SDF Phase 7 Post-finish Lifecycle-Hook
# --from=idf_plan   (BL-076): IDF Phase 7 Recheck-Hook (falls IDF BL_orchestrate aufruft)
# Verhindert BL→BDF→BL Rekursion (Anti-Zirkel, BL-075 ADR-3, BL-078 AK-06).
bl_mode = $ARGUMENTS.mode ?? "normal"
bl_from = $ARGUMENTS.from ?? "direct"
IF bl_mode == "recheck":
  Logge: "[BL-075/BL-078] Phase 9 AUTO-CHAIN SKIPPED (--mode=recheck, from={bl_from})"
  # Nur Statistik schreiben, Aufrufer entscheidet selbst
  Schreibe in {VAULT}/_manifest.md → BL_LIFECYCLE_STATE.last_recheck_ready: {items_routed_ready}
  Schreibe in {VAULT}/_manifest.md → BL_LIFECYCLE_STATE.last_recheck_from: {bl_from}
  → Skip Phase 9 (return zu Aufrufer: bdf_empty→BDF, sdf_finish→SDF)

# ═══ AUTO-CHAIN: BL → BDF (BL-046, Work-Until-Drop) ═══
# Nach BL DONE: Wenn READY Items vorhanden → BDF sofort starten.
# Kein manueller Aufruf noetig. Show must go on.
# Terminationsbedingungen: Keine READY Items, alle BLOCKED, bdf_max_items, Context-Limit.
IF items_routed_ready > 0:
  Logge: "[BL→BDF AUTOLOOP] {items_routed_ready} READY Items → BDF wird gestartet"
  Skill(skill="_BDF_orchestrate")
  # Nach BDF DONE: Pruefe ob neue DRAFT Items entstanden (z.B. durch Mitose/SDF)
  # Lies _backlog_index.md → DRAFT Items mit needs_a_pipeline=true
  bl_neue_drafts = Filtere Items mit status=DRAFT aus _backlog_index.md
  IF bl_neue_drafts.length > 0:
    Logge: "[BL→BDF AUTOLOOP] {bl_neue_drafts.length} neue DRAFT Items → BL erneut starten"
    # Rekursion: BL_orchestrate erneut ausfuehren (gleiche Parameter)
    # Terminiert natuerlich wenn keine DRAFT Items mehr oder Context-Limit
    GOTO Phase 1 (INIT)
  ELSE:
    Logge: "[BL→BDF AUTOLOOP] Keine neuen DRAFT Items → Loop beendet"
ELSE:
  Logge: "[BL→BDF AUTOLOOP] Keine READY Items → kein BDF-Start"
  # Terminiert. Kein BDF noetig.
```

---

## QUICK-START

```
1. /_BL_orchestrate [ceiling=opus] [floor=haiku]
2. INIT (Phase 1): BL_LIFECYCLE_STATE initialisieren
3. LIFECYCLE_CHECK (Phase 2): Gap/Reife lesen, items_stucked[] verarbeiten
4. WAHRHEITEN_ROUTING (Phase 3): Model-Wahrheiten zaehlen, WP/RESYNC/KEINE_AKTION
5. TRIAGE (Phase 4): ENTFERNT (BL-078b Batch C, ohne Konsument)
6. DEPENDENCY_RESOLVE (Phase 5): ENTFERNT (BL-078b Batch C, ohne Konsument)
7. MITOSE_CHECK (Phase 6): ENTFERNT (BL-078b → BL-077)
8. A_PIPELINE_TRIGGER (Phase 7): needs_a_pipeline=true → Skill(_A_orchestrate)
9. STATUS_UPDATE (Phase 8): ENTFERNT (BL-078b → IDF Phase 6 BATCH_SEQUENCE)
10. DONE (Phase 9): Finalisieren, terminieren, ggf. AUTO-CHAIN BL→BDF
```
