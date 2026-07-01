---
status: active
version: 5.0.0
type: skill
parent: _A_orchestrate
phase: phase_5
created: 2026-04-25
updated: 2026-05-17
bl_142_implementation: true
refit_v3_2026_05_17: |
  V3.0 (2-Path-Binary BDF|IDF) hatte DIRECT_I-Drift-Bug.
  V4.0 (5-Target BDF|SC|IDF|SDF|STOP) war Architektur-Bullshit:
    - A->SC direct verletzt /_help Pipeline-Hierarchie (SC ist Sub-Modus SDF M4-M7).
    - A->SDF direct verletzt Decomp-Pflicht (ohne PL-Items kann SDF nicht starten).
  V5.0: 3-Target {BDF, IDF, STOP}. A geht IMMER zu IDF (egal Reifegrad).
  IDF entscheidet Decomp-Strategie + Phase 8.5 Auto-Chain SDF.
  SC erreichbar NUR via SDF Phase 1.1 modusEntscheidung (M4/M5/M6/M7).
---

# /_A_postRoute v5.0.0 — Exit-Router nach A-Pipeline (3-Target Matrix V3)

> **Rolle:** Letzter Schritt der A-Pipeline (Phase 5). Routet das fertige BL-Item
> an die naechste Schicht. Pipeline-Hierarchie strict: A → IDF (Default) ODER
> BDF (entry_point) ODER STOP (transkript-only). SC/SDF/I sind direct unerreichbar.

## VERTRAG

```
+======================================================================+
| VERTRAG: /_A_postRoute v5.0.0 (Refit-V3 2026-05-17)                 |
+======================================================================+
|                                                                       |
| LIEST:                                                                |
|   {VAULT}/_session_params.md                                          |
|     GLOBAL_MODUS: big_dark_factory | small_dark_factory | manual      |
|   {WORKING_DIR}/_manifest.md                                          |
|     A_PIPELINE_STATE.bl_id                                            |
|     A_PIPELINE_STATE.bl_slug                                          |
|     A_PIPELINE_STATE.routing_target  (BDF | IDF | STOP)               |
|     A_PIPELINE_STATE.next_skill      (Skill-Path vom routing-Berater) |
|     A_PIPELINE_STATE.next_args       (Args vom routing-Berater)       |
|                                                                       |
| SCHREIBT:                                                             |
|   {WORKING_DIR}/_manifest.md                                          |
|     A_PIPELINE_STATE.completion_signal = "ready_for_bdf" | "routed_to_idf" | "transkript_only_done"
|     A_PIPELINE_STATE.phase             = "COMPLETED"                  |
|                                                                       |
| RUFT (Skill):                                                         |
|   /_IDF_orchestrate (bei target=IDF — Default-Pfad)                   |
|   KEIN _SC_orchestrate  (SC nur via SDF Phase 1.1 M4-M7)              |
|   KEIN _SDF_orchestrate (SDF nur via IDF Phase 8.5 Auto-Chain)        |
|   KEIN _I_orchestrate   (Implementation via SDF Phase 2.1 Dispatch)   |
|   KEIN _BDF_orchestrate (BDF liest completion_signal selbst per SCAN) |
|                                                                       |
| INVARIANTEN:                                                          |
|   INV-ROUTE-1-V3: 3-Target {BDF, IDF, STOP} — Whitelist enforced.     |
|   INV-ROUTE-2:   A schreibt routing_target NACH Lifecycle-Phase 4.4.  |
|   INV-ROUTE-3-V3: SC/SDF/I als Direct-A-Target VERBOTEN. Sie sind     |
|                  erreichbar nur via Pipeline-Hierarchie:              |
|                    A -> IDF -> (Phase 8.5 Auto-Chain) -> SDF          |
|                    SDF Phase 1.1 modusEntscheidung -> M{N}            |
|                    M2/M3 -> I_orchestrate                             |
|                    M4-M7 -> SC_orchestrate (Symbiose)                 |
|                    INV-MODUS-7 Pflicht-Autochain SC -> SDF_post.      |
|   INV-ROUTE-4-V3: target=IDF ist DEFAULT, egal Reifegrad. IDF         |
|                  entscheidet selbst: Decomp moeglich? Phase 8.5       |
|                  Auto-Chain. Sonst: --mode=recheck -> A.              |
|   INV-ROUTE-5-V3 (BL-226-KONFORM, BL-350 F8): GLOBAL_MODUS=          |
|                  big_dark_factory ueberschreibt target zu BDF — ABER  |
|                  NICHT bei routing=proceed (idf_invoke_required=true + |
|                  routing_target=IDF): dann DIREKTER A->IDF-Chain       |
|                  (INV-A-EXCEPT-1, kein ready_for_bdf-Polling).         |
+======================================================================+
```

## Decision-Tree

```
SCHRITT 0: Inputs lesen
  GLOBAL_MODUS = lies(_session_params.md).GLOBAL_MODUS
  bl_id        = A_PIPELINE_STATE.bl_id
  bl_slug      = A_PIPELINE_STATE.bl_slug
  target       = A_PIPELINE_STATE.routing_target  # geschrieben vom routing-Berater
  next_skill   = A_PIPELINE_STATE.next_skill      # geschrieben vom routing-Berater
  next_args    = A_PIPELINE_STATE.next_args       # geschrieben vom routing-Berater

SCHRITT 0.5: Rail Guard V3 (INV-ROUTE-1-V3 + INV-ROUTE-3-V3)
  VALID_TARGETS = {"BDF", "IDF", "STOP"}
  RETIRED_TARGETS = {"DIRECT_I", "I_DIRECT", "DIRECT_SC", "SC_DIRECT"}
  INVALID_AS_A_TARGET = {"SC", "SDF", "I"}

  IF target IN RETIRED_TARGETS:
    Logge: "[A-POSTROUTE GUARD] FATAL: target='{target}' RETIRED (alt-Vokabular Refit-V2)"
    ABORT("INV-ROUTE-1-V3 Violation: RETIRED target")

  IF target IN INVALID_AS_A_TARGET:
    Logge: "[A-POSTROUTE GUARD] FATAL: target='{target}' invalid AS A-routing target."
    Logge: "[A-POSTROUTE GUARD] SC/SDF/I sind erreichbar via IDF Phase 8.5 -> SDF Phase 1.1 (M{{N}})."
    Logge: "[A-POSTROUTE GUARD] Use IDF als A-routing target stattdessen."
    ABORT("INV-ROUTE-3-V3 Violation: invalid AS A-target")

  IF target NOT IN VALID_TARGETS:
    ABORT("INV-ROUTE-1-V3 Violation: target='{target}' nicht in {VALID_TARGETS}")

SCHRITT 1: GLOBAL_MODUS Override (INV-ROUTE-5-V3 — BL-226-KONFORM seit BL-350 F8 2026-06-14)
  # BL-226/INV-A-EXCEPT-1 (NEWER, authoritative — CLAUDE.md + _A_orchestrate Phase 5): bei
  # routing=proceed (idf_invoke_required=true UND routing_target="IDF") chaint A BEDINGUNGSLOS
  # DIREKT zu IDF — KEIN big_dark_factory->BDF-Override, KEIN ready_for_bdf-Polling (1-Seam-Chain).
  # Der frueher unbedingte Override (pre-BL-226) ersetzte den Direkt-Chain durch ready_for_bdf und
  # liess den Lauf im Direkt-Drive STALLEN (kein BDF-Outer-Loop konsumiert das Signal). Darum gilt
  # der BDF-Override jetzt NUR fuer Nicht-proceed-Targets (BDF/STOP), wo BDF tatsaechlich vermittelt.
  idf_required = A_PIPELINE_STATE.idf_invoke_required ?? false
  IF GLOBAL_MODUS == "big_dark_factory" AND NOT (target == "IDF" AND idf_required):
    A_PIPELINE_STATE.routing_target    = "BDF"
    A_PIPELINE_STATE.completion_signal = "ready_for_bdf"
    A_PIPELINE_STATE.phase             = "COMPLETED"
    Logge: "[A-POSTROUTE] big_dark_factory -> BDF (target={target} overridden by GLOBAL_MODUS)"
    RETURN
  ELIF GLOBAL_MODUS == "big_dark_factory":
    Logge: "[A-POSTROUTE BL-226/BL-350-F8] big_dark_factory ABER routing=proceed->IDF: KEIN BDF-Override, direkter A->IDF-Chain (INV-A-EXCEPT-1, 1-Seam, kein ready_for_bdf-Polling)"
    # Fallthrough zu SCHRITT 2 -> target=="IDF"-Dispatch -> Skill(_IDF_orchestrate)

SCHRITT 2: 3-Target Dispatch
  IF target == "BDF":
    A_PIPELINE_STATE.completion_signal = "ready_for_bdf"
    A_PIPELINE_STATE.phase             = "COMPLETED"
    Logge: "[A-POSTROUTE] target=BDF -> completion_signal=ready_for_bdf (kein Skill-Call)"
    RETURN

  ELIF target == "STOP":
    A_PIPELINE_STATE.completion_signal = "transkript_only_done"
    A_PIPELINE_STATE.phase             = "COMPLETED"
    Logge: "[A-POSTROUTE] target=STOP -> transkript-only RETURN (kein Skill-Call)"
    RETURN

  ELIF target == "IDF":
    A_PIPELINE_STATE.completion_signal = "routed_to_idf"
    A_PIPELINE_STATE.phase             = "COMPLETED"
    Logge: "[A-POSTROUTE] target=IDF -> Skill({next_skill}, args='{next_args}')"
    Skill(_IDF_orchestrate, args=next_args)
    RETURN
```

## Aufruf-Interface

```
Skill(_A_postRoute, args="{NAME}")
# Wird von _A_orchestrate Phase 5 als finalen Schritt aufgerufen
```

## Beispiele

### Beispiel 1: big_dark_factory (Override)
```
GLOBAL_MODUS = big_dark_factory
routing_target = IDF (Default)
-> Override: completion_signal=ready_for_bdf, kein Skill-Call
-> BDF Outer-Loop scant Vault, nimmt BL-Item auf
```

### Beispiel 2: small_dark_factory + UNREIF -> IDF
```
GLOBAL_MODUS = small_dark_factory
routing_target = IDF
next_skill = _IDF_orchestrate
next_args = "BL-162 --from=direct"
-> Skill(_IDF_orchestrate, args="BL-162 --from=direct")
-> IDF Phase 2 specParse erkennt Spec-Stand
-> Bei UNREIF: IDF macht entweder Decomp soweit moeglich ODER --mode=recheck zu A
-> Bei reif: Phase 8.5 Auto-Chain SDF
```

### Beispiel 3: small_dark_factory + REIF + 5 AKs -> IDF
```
GLOBAL_MODUS = small_dark_factory
routing_target = IDF
next_skill = _IDF_orchestrate
-> IDF Decomposition + PL-Items + Batch-Plan
-> Phase 8.5 Auto-Chain zu SDF
-> SDF Phase 1.1 modusEntscheidung waehlt M{N}
```

### Beispiel 4: scope=transkript-only -> STOP
```
GLOBAL_MODUS = manual
routing_target = STOP
-> completion_signal=transkript_only_done, kein Skill-Call
-> A-Pipeline beendet ohne Handoff
```

## VERBOTEN (Anti-Pattern)

- **DIRECT_I als routing_target** — RETIRED (V3.0 Drift-Bug, BL-165 INV-MODUS-1)
- **SC als A-routing target** — Pipeline-Hierarchie-Verletzung (SC ist Sub-Modus SDF M4-M7)
- **SDF als A-routing target** — Decomp-Pflicht-Verletzung (PL-Items entstehen in IDF)
- **I als A-routing target** — Implementation via SDF Phase 2.1 Dispatch
- Direct-Skill-Call zu `/_SC_orchestrate` aus A — verboten
- Direct-Skill-Call zu `/_SDF_orchestrate` aus A — verboten
- Direct-Skill-Call zu `/_I_orchestrate` aus A — verboten
- Direct-Skill-Call zu `/_BDF_orchestrate` — BDF liest completion_signal per SCAN
- Mode-Decision (M1-M9) in A — gehoert zu SDF C3
- AskUserQuestion — A laeuft autonom durch
- 4-Path-Routing mit SC-First/I-First Heuristik (alt v1.x)
- 2-Path-Binary BDF|DIRECT_I (alt v3.0, RETIRED)
- 5-Target BDF|SC|IDF|SDF|STOP (alt v4.0, Architektur-Bullshit)

## Verwandte Commands

- `_A_orchestrate.md` — Phase 5 Caller
- `_A_berater_routing.md` — wraps diesen Skill (3-Target Matrix V3 seit 2026-05-17)
- `_IDF_orchestrate.md` — Default-Pfad (IDF entscheidet Decomp + Phase 8.5 Auto-Chain SDF)
- `_BDF_orchestrate.md` — liest completion_signal beim SCAN
- `_SDF_orchestrate.md` — INDIREKT erreichbar (via IDF Phase 8.5 Auto-Chain)
- `_SC_orchestrate.md` — INDIREKT erreichbar (via SDF Phase 1.1 M4-M7)
- `_I_orchestrate.md` — INDIREKT erreichbar (via SDF Phase 2.1 Dispatch M2/M3)

## Migrations-Notiz (V4.0 → V5.0)

| V4.0 Behaviour | V5.0 Replacement |
|----------------|------------------|
| target=BDF -> completion_signal | Bleibt erhalten |
| target=IDF -> Skill(_IDF_orchestrate) | Bleibt erhalten — JETZT DEFAULT |
| **target=SC** -> Skill(_SC_orchestrate) — ARCHITEKTUR-BULLSHIT | target=IDF -> IDF entscheidet, SC via SDF |
| **target=SDF** -> Skill(_SDF_orchestrate) — Decomp-Pflicht ignoriert | target=IDF -> Phase 8.5 Auto-Chain SDF |
| target=STOP -> exit clean | Bleibt erhalten |

**Backward-Compat:** 
- `routing_target=IDF` → funktioniert weiter (Default-Pfad)
- `routing_target=BDF` → funktioniert weiter
- `routing_target=STOP` → funktioniert weiter
- `routing_target=DIRECT_I` → HARD-ABORT (Rail Guard)
- `routing_target=SC` → HARD-ABORT (INV-ROUTE-3-V3)
- `routing_target=SDF` → HARD-ABORT (INV-ROUTE-3-V3)
- `routing_target=I` → HARD-ABORT (INV-ROUTE-3-V3)
