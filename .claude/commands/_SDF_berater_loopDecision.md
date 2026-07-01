---
status: active
version: 1.1.0  # BL-NEW-5 SOFT-REPRIO Branch 2026-05-11
type: berater
parent: _SDF_orchestrate
phase: phase_4
model_tier: ceiling
created: 2026-04-25
updated: 2026-05-11
feature_anchor: BL-142
contract:
  reads:
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_status", purpose: "aktuelle Batch-Lage"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_done", purpose: "abgearbeitete Items"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "IDF_PIPELINE_STATE.batch_items", purpose: "alle Items aus IDF"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.recalibrate_batch", purpose: "K-Drift fuer SOFT-REPRIO (BL-NEW-5)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "A_PIPELINE_STATE.k_score", purpose: "Pre-Round-K-Score fuer Drift-Berechnung"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "PL-Items", purpose: "neue Items im Vault?"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.loopDecision", purpose: "decision: ROLLBACK | TERMINATE | RE-BATCH | SOFT-REPRIO"}
optional: false
---

# _SDF_berater_loopDecision

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_loopDecision — BL-142 RF-EXTRACT-SDF         ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST: DF_BATCH_STATE.batch_done[]         (abgearbeitete Items)   ║
║         IDF_PIPELINE_STATE.batch_items[]    (alle bekannten Items)  ║
║         {VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md       ║
║  SCHREIBT: BERATER_OUTPUTS.loopDecision     (decision + reason)     ║
╠══════════════════════════════════════════════════════════════════════╣
║  AUFRUF: Skill(_SDF_berater_loopDecision, args="{NAME}")            ║
║  PHASE:  Phase 4 LOOP-DECISION (nach PostBatch)                     ║
║  ZWECK:  Entscheidet ob ROLLBACK (neue Items) / TERMINATE / RE-BATCH║
╚══════════════════════════════════════════════════════════════════════╝
```

## 3-WEGE-ROUTING-MODELL (BL-429 AK-1/2/3/4/5/6/8/9)

> **Kanonischer Klassifikator:** `sdf_last_item_detect.classify_route(idf_items, batch_done, completed_sub_batches, open_pl_deferred, stage_orphans)` → `{weg, decision_token, is_last, reason}`.
> Die intern verwendeten Routing-Tokens (ROLLBACK / TERMINATE / SOFT-REPRIO / RE-BATCH) bleiben erhalten — das 3-Wege-Framing ist eine **Doku-Schicht** obendrauf, kein Breaking-Rename.

### Auswertungs-Reihenfolge: WEG1 > WEG3 > WEG2 (AK-6)

| Weg | Kurzname | Routing-Token | Bedeutung |
|-----|----------|---------------|-----------|
| **WEG 1** | neue-PL → IDF | `ROLLBACK` | Neue oder unbekannte PL-Items (stage_orphans ODER open_pl_deferred außerhalb idf_items) |
| **WEG 3** | alles-zu → Roadmap/BDF | `TERMINATE` | Alle IDF-Items done, **keine** open_pl_deferred, **keine** stage_orphans (`is_last == True`) |
| **WEG 2** | bekannte-PL → SDF | `RE-BATCH` | Items noch offen oder bekannte Deferrals (in idf_items) verbleibend — Default |

### WEG 1 — "neue PL → IDF" (konsolidiert, AK-2)

WEG 1 vereint alle bisher verstreuten Pfade unter einem semantisch klaren Dach:

- **ROLLBACK** (neue PL-Items im Vault, len(vault_pl_items) > len(idf_items)) — klassischer Fall
- **orphan_scan** (Phase 4.1.5) — stage_orphans entdeckt → ebenfalls WEG 1
- **SOFT-REPRIO** (K-Drift > 30%) — triggert IDF Re-Cluster → ebenfalls semantisch WEG 1 (bekannte Items, neuer K-Kontext; technisch eigener Token, aber "neue Konfiguration → IDF")

Konsequenz: Wann immer der classify_route-Helper `weg=1` zurückgibt (stage_orphans ODER neue Orphans in open_pl_deferred), lautet der kanonische Exit `→ IDF`.

### WEG 2 — "bekannte PL → SDF" (RE-BATCH, AK-3)

WEG 2 re-chaint SDF über `Skill(_SDF_orchestrate, --resume)`. **INV-MODUS-1:** loopDecision und das Exit-Routing setzen **nie** `batch_modes` oder `modus` — die Modus-Entscheidung pro neuer Runde obliegt ausschließlich `_SDF_berater_modusEntscheidung` (Phase 1.1, C3).

### WEG 3 — "alles zu → Roadmap/BDF" (TERMINATE, AK-4/AK-5)

WEG 3 feuert **nur** bei `is_last == True` des Klassifikators. Last-Item-Detektion erfordert ALLE drei Bedingungen (pure Set-Equality reicht NICHT):

1. `set(idf_items) == set(batch_done)` (alle bekannten Items abgearbeitet)
2. `open_pl_deferred` ist leer (INV-LD-7: kein offenes deferred-stage/deferred-ak-Item)
3. `stage_orphans` ist leer (kein hängendes Stage-Phantom)

→ Verweise auf Helper: `sdf_last_item_detect.classify_route` in `.claude/scripts/sdf_last_item_detect.py` (BL-429 batch_1).

### Endlos-Loop-Counter → 3-Wege-Mapping (AK-8)

`DF_BATCH_STATE.loop_counters` bildet auf die zwei iterativen Wege ab:

| Counter | Weg | Trigger |
|---------|-----|---------|
| `loop_counters.rollback` | WEG 1 | ROLLBACK + SOFT-REPRIO (rollback/soft_reprio-Counter) |
| `loop_counters.re_batch` | WEG 2 | RE-BATCH-Counter |

WEG 3 (TERMINATE) hat keinen Counter — er ist per Definition ein nicht-iterativer Abschluss-Pfad. Endlos-Loop-Schwelle: `MAX_LOOPS_PER_DECISION` (Default 3, BL-210).

### Konsistenz mit INV-LD-1..7 + INV-POST-1 (AK-9)

Das 3-Wege-Modell bricht keine bestehende Invariante:

- INV-LD-1..5: decision-Enum {ROLLBACK/TERMINATE/SOFT-REPRIO/RE-BATCH} unverändert; WEG-Nummern sind Doku-Aliase.
- INV-LD-6: SOFT-REPRIO-Schwellenwert 30% unverändert (WEG 1, IDF Re-Cluster-Zweig).
- INV-LD-7: TERMINATE (WEG 3) darf nicht feuern bei offenem deferred-Item — exakt abgebildet in `is_last`-Bedingung des Klassifikators (open_pl_deferred leer Pflicht).
- INV-POST-1: Post-SDF returnt nie inline — jeder Weg endet in einem expliziten Skill-Call.

---

## LOGIK

### SCHRITT 0: Entry

```
Lies DF_BATCH_STATE.batch_done[]          -> batch_done (Liste abgearbeiteter Item-IDs)
Lies IDF_PIPELINE_STATE.batch_items[]     -> idf_items  (alle Items laut IDF)
Lies {VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md -> vault_pl_items (aktueller Vault-Stand)
```

### SCHRITT 1: Decision-Tree (BL-NEW-5 SOFT-REPRIO erweitert 2026-05-11)

```
# Reihenfolge der Prueefungen (oben gewinnt):
#   1. ROLLBACK     — neue PL-Items im Vault
#   2. TERMINATE    — alle Items DONE
#   3. SOFT-REPRIO  — K-Drift > 30% (BL-NEW-5, NEU)
#   4. RE-BATCH     — Default

IF len(vault_pl_items) > len(idf_items):
  # Neue PL-Items im Vault die IDF noch nicht kennt
  decision = "ROLLBACK"
  reason = "Neue PL-Items detected: vault={len(vault_pl_items)}, idf={len(idf_items)}"
  new_items_count = len(vault_pl_items) - len(idf_items)
  remaining_count = 0
  k_drift = null

ELIF set(idf_items) == set(batch_done):
  # Alle bekannten Items abgearbeitet
  decision = "TERMINATE"
  reason = "Alle {len(idf_items)} Items DONE"
  new_items_count = 0
  remaining_count = 0
  k_drift = null

ELSE:
  # Default: Re-Batch — pruefe vorher ob SOFT-REPRIO geboten ist
  remaining = set(idf_items) - set(batch_done)
  remaining_count = len(remaining)

  # SOFT-REPRIO-Check (BL-NEW-5): K-Score-Drift > 30%?
  # Triggert wenn recalibrate aktuelle Round signifikanten K-Drift fand
  # → IDF sollte Rest-Items neu clustern basierend auf neuem K-Score
  # (kein Full-ROLLBACK, nur Re-Cluster der noch offenen Items).
  recalibrate = BERATER_OUTPUTS.recalibrate_batch
  k_drift_threshold = 0.30  # 30%
  k_drift = null
  IF recalibrate AND NOT recalibrate.skipped AND remaining_count > 0:
    k_score_old = A_PIPELINE_STATE.k_score_before_round ?? null
    k_score_new = recalibrate.k_score_new ?? null
    IF k_score_old AND k_score_new AND k_score_old > 0:
      k_drift = abs(k_score_new - k_score_old) / max(k_score_old, 1)

  IF k_drift != null AND k_drift > k_drift_threshold:
    decision = "SOFT-REPRIO"
    reason = "K-Drift {k_drift*100|round=1}% (old={k_score_old} → new={k_score_new}) > {k_drift_threshold*100}% — Re-Cluster Rest-Items via IDF (BL-NEW-5)"
    new_items_count = 0
  ELSE:
    decision = "RE-BATCH"
    reason = "{remaining_count} Items verbleibend, Re-Batch ueber IDF Phase 7 (K-Drift={k_drift|round=2 OR 'n/a'})"
    new_items_count = 0
```

### SCHRITT 2: Output schreiben

```
BERATER_OUTPUTS.loopDecision = {
  decision: "ROLLBACK" | "TERMINATE" | "SOFT-REPRIO" | "RE-BATCH",
  reason: <reason>,
  new_items_count: <N>,
  remaining_count: <N>,
  k_drift: <float|null>,         # BL-NEW-5: K-Score-Drift (null bei ROLLBACK/TERMINATE)
  last_berater: "loopDecision"
}

Logge: "[LOOP-DECISION] decision={decision} -- {reason}"
```

## DECISION-BEDEUTUNG

| decision | Bedeutung | SDF-Aktion |
|----------|-----------|------------|
| `ROLLBACK` | Vault hat neue Items die IDF nicht kennt | IDF Phase 4-7 neu durchlaufen via `_IDF_orchestrate --mode=recheck` |
| `TERMINATE` | Alle IDF-bekannten Items sind in batch_done | df_status=DONE, TeamDelete |
| `SOFT-REPRIO` (BL-NEW-5) | K-Drift > 30% — Rest-Items neu clustern, kein Full-Rollback | IDF Phase 5-7 via `_IDF_orchestrate --mode=recluster --from=sdf_drift` |
| `RE-BATCH` | Items verbleibend, DAG unveraendert | IDF Phase 7 direkt via `_IDF_berater_batchPlan` |

## INVARIANTEN

- INV-LD-1: decision ist immer eines von ROLLBACK / TERMINATE / SOFT-REPRIO / RE-BATCH (keine anderen Werte)
- INV-LD-2: ROLLBACK iff len(vault_pl_items) > len(idf_items)
- INV-LD-3: TERMINATE iff set(idf_items) == set(batch_done) AND kein ROLLBACK
- INV-LD-4: SOFT-REPRIO iff (kein ROLLBACK ∧ kein TERMINATE) ∧ k_drift > 0.30 ∧ recalibrate.skipped=false
- INV-LD-5: RE-BATCH iff weder ROLLBACK noch TERMINATE noch SOFT-REPRIO (default)
- INV-LD-6 (BL-NEW-5): SOFT-REPRIO Schwellenwert 30% ist fix — Aenderung erfordert Spec-Update
- INV-LD-7 (BL-323 AK-2 — Story-DONE-Gate gegen ueberklagtes completed): TERMINATE (→ df_status=DONE) DARF NICHT feuern, solange ein offenes PL-Item `typ ∈ {deferred-stage, deferred-ak}` existiert (via stageElevation INV-STAGE-ELEV-6/7 materialisiert). Ein Sub-Batch in batch_done mit `stage_plan_complete: false` ist 'Stage-gebankt', NICHT 'stage-plan-vollstaendig' — die Story ist erst DONE, wenn alle aufgeschobenen Stages nachgeholt + ihre Folge-PL-Items geschlossen sind. Offene deferred-Items re-surfen ueber loopCheck (INV-IDF-LOOP-6) sobald ihr resurface_trigger erfuellt ist → kein 'Loch' im Work-Stream, kein still-DONE-trotz-offener-Arbeit. [[feedback_machine_not_context]]
