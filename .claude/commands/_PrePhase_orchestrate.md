---
status: NEU v1.0
version: 1.0
created: 2026-04-25
type: orchestrator
chain_position: PRE-Item-im-Batch-Loop
ceiling: sonnet
floor: sonnet
contract:
  reads:
    - {file: "_manifest.md", path: "DF_PIPELINE_STATE.batch_current", purpose: "Aktueller Batch"}
    - {file: "_parking-lot.md", path: "items_for_current_batch", purpose: "Welche PL-Items im Batch"}
    - {file: "_session_params.md", path: "GLOBAL_HIL", purpose: "HiL-Modus"}
  writes:
    - {file: "_manifest.md", path: "PREPHASE_PIPELINE_STATE", purpose: "Eigener State-Slot"}
  not_writes:
    - {file: "_manifest.md", path: "BERATER_OUTPUTS.*", excluding: "(keine — delegiert an C1/C2)"}
  calls:
    - {skill: "_SDF_berater_resumeGuard", purpose: "C1 — Session-Recovery + last_commit"}
    - {skill: "_SDF_berater_itemContext", purpose: "C2 — Vault-Frontmatter + tc_scope + reifegrad"}
    - {skill: "_IDF_orchestrate", optional: true, args: "--gate-only", purpose: "BL-130 Phase 1.6 IDF-Gate (falls Item ein Spec-Item ist)"}
related:
  - _PostBatch_orchestrate (Schwester-Wrapper, BATCH-Ende)
  - _SDF_PreBerater_orchestrate (C9b — bestehender Pre-Berater-Hook, koennte spaeter wandern)
absorbs: [Inline-Pre-Item-Logic im SDF Item-Loop]
adr_reference: ADR-7 (Q1=Option-B Resolution)
---

# _PrePhase_orchestrate — PRE-Item-Wrapper im Batch-Loop

## Zweck

Dieser Command laeuft VOR jedem Item im Batch-Item-Loop — er bereitet den Session-Kontext
und Item-Kontext vor, bevor der eigentliche Berater-Durchlauf (C3 modusEntscheidung usw.)
startet.

Aufruf-Reihenfolge: SDF Batch-Loop Item-Start → **_PrePhase_orchestrate** → C3 modusEntscheidung
→ ... → _SDF_PostBerater_orchestrate (C9c) → _PostBatch_orchestrate (nach Batch-Ende).

_PostBatch_orchestrate ist die Schwester-Wrapper auf BATCH-Ebene; dieser Wrapper hier
operiert auf PRE-Item-Ebene (laeuft einmal pro Item, nicht einmal pro Batch).

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _PrePhase_orchestrate v1.0                                 ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:   _manifest.md                                               ║
║             DF_PIPELINE_STATE.batch_current                          ║
║             DF_PIPELINE_STATE.item_id (aktuelles Item)               ║
║           _parking-lot.md                                            ║
║             items_for_current_batch                                  ║
║           _session_params.md                                         ║
║             GLOBAL_HIL                                               ║
║  SCHREIBT: _manifest.md                                              ║
║             PREPHASE_PIPELINE_STATE.item_id                          ║
║             PREPHASE_PIPELINE_STATE.batch_pre_done                   ║
║             PREPHASE_PIPELINE_STATE.idf_gate_ran (optional)          ║
║  SCHREIBT NICHT: BERATER_OUTPUTS.*  (delegiert an C1/C2)             ║
║                  DF_PIPELINE_STATE.df_status (unveraendert)          ║
║  RUFT AUF: _SDF_berater_resumeGuard (C1),                            ║
║            _SDF_berater_itemContext (C2),                            ║
║            _IDF_orchestrate --gate-only (optional, Spec-Items)       ║
║  INV-PREPHASE-1: Enthaelt NUR Skill-Calls + State-Handling.          ║
║    Kein Inline-Vault-Read direkt — das ist Aufgabe von C2 (AK-13)   ║
╚══════════════════════════════════════════════════════════════════════╝
```

## VERTRAG-Tabelle

| Feld | Richtung | Quelle/Ziel | Zweck |
|------|----------|-------------|-------|
| `DF_PIPELINE_STATE.batch_current` | LIEST | `_manifest.md` | Aktueller Batch |
| `DF_PIPELINE_STATE.item_id` | LIEST | `_manifest.md` | Zu bearbeitendes Item |
| `items_for_current_batch` | LIEST | `_parking-lot.md` | Batch-Item-Liste |
| `GLOBAL_HIL` | LIEST | `_session_params.md` | HiL-Modus aktiv? |
| `PREPHASE_PIPELINE_STATE.item_id` | SCHREIBT | `_manifest.md` | Welches Item wurde vorbereitet |
| `PREPHASE_PIPELINE_STATE.batch_pre_done` | SCHREIBT | `_manifest.md` | Pre-Phase vollstaendig |
| `PREPHASE_PIPELINE_STATE.idf_gate_ran` | SCHREIBT (opt.) | `_manifest.md` | IDF-Gate wurde ausgefuehrt |
| `BERATER_OUTPUTS.resumeGuard` | (via C1) | von C1 selbst | resumeGuard schreibt seinen Slot |
| `BERATER_OUTPUTS.itemContext` | (via C2) | von C2 selbst | itemContext schreibt seinen Slot |

## Pipeline-Logik

```
SCHRITT 0: Entry-Log
  Lies batch_current aus DF_PIPELINE_STATE (_manifest.md)
  Lies item_id aus DF_PIPELINE_STATE (_manifest.md)
  Lies GLOBAL_HIL aus _session_params.md
  Logge: "[PREPHASE] ENTRY batch={batch_current} item={item_id} hil={GLOBAL_HIL}"

SCHRITT 1: C1 — Session-Recovery + last_commit
  Skill(_SDF_berater_resumeGuard, args="{NAME}")
  # C1 schreibt BERATER_OUTPUTS.resumeGuard + DF_PIPELINE_STATE.last_commit (Stale-Korrektur)
  Lies BERATER_OUTPUTS.resumeGuard aus _manifest.md
  IF resumeGuard.status == "ABORTED":
    PREPHASE_PIPELINE_STATE.batch_pre_done = false
    PREPHASE_PIPELINE_STATE.item_id = item_id
    Logge: "[PREPHASE] EXIT item={item_id} → ABORTED (C1 resumeGuard)"
    RETURN

SCHRITT 2: C2 — Vault-Frontmatter + tc_scope + reifegrad
  Skill(_SDF_berater_itemContext, args="{NAME}")
  # C2 schreibt BERATER_OUTPUTS.itemContext (item_type, blocked, tc_scope)
  Lies BERATER_OUTPUTS.itemContext aus _manifest.md
  IF itemContext.blocked == true:
    PREPHASE_PIPELINE_STATE.batch_pre_done = false
    PREPHASE_PIPELINE_STATE.item_id = item_id
    Logge: "[PREPHASE] EXIT item={item_id} → BLOCKED (C2 itemContext, Alpha-Beta-Pruning)"
    RETURN

SCHRITT 3 (optional): IDF-Gate fuer Spec-Items
  # BL-130 Phase 1.6: IDF-Gate nur wenn Item ein Spec-Item ist
  IF itemContext.item_type == "spec" UND Skill(_IDF_orchestrate) verfuegbar:
    Skill(_IDF_orchestrate, args="--gate-only --item {item_id}")
    PREPHASE_PIPELINE_STATE.idf_gate_ran = true
    Logge: "[PREPHASE] IDF-Gate ran fuer Spec-Item {item_id}"
  ELSE:
    PREPHASE_PIPELINE_STATE.idf_gate_ran = false

SCHRITT 4: Pre-Phase abschliessen
  PREPHASE_PIPELINE_STATE.item_id = item_id
  PREPHASE_PIPELINE_STATE.batch_pre_done = true
  Logge: "[PREPHASE] EXIT item={item_id} batch={batch_current} → batch_pre_done=true"
```

## Drei-Ebenen-Hinweis

PrePhase ist eine von drei Ebenen im Item-/Batch-Lifecycle und darf NICHT mit den anderen
verwechselt werden:

| Ebene        | Command                          | Wann                                        |
|--------------|----------------------------------|---------------------------------------------|
| PRE-ITEM     | `_PrePhase_orchestrate` (hier)   | Vor jedem Item: C1 resumeGuard + C2 itemContext |
| PRE-BERATER  | `_SDF_PreBerater_orchestrate`    | Bestehender Hook C9b — koennte spaeter wandern |
| POST-BATCH   | `_PostBatch_orchestrate`         | Nach Batch-Item-Loop: Tests + Stage         |

## INV-PREPHASE-1

Diese Datei enthaelt ausschliesslich Skill-Calls (`_SDF_berater_resumeGuard`, `_SDF_berater_itemContext`,
optional `_IDF_orchestrate`) sowie State-Lesen/-Schreiben. Kein Inline-Vault-Read direkt —
Vault-Lesen ist Aufgabe von C2. Kein git, kein gh, keine Shell-Kommandos inline. AK-13
verbietet Inline-Operationen systemweit ab BL-133.
