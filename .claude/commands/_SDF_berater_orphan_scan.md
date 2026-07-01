---
status: active
version: 1.0.0
type: berater
parent: _SDF_orchestrate_post
phase: phase_4_pre_loopdecision
model_tier: middle
created: 2026-05-12
feature_anchor: BL-NEW-60
contract:
  reads:
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", path: "Alle [ ] Items mit Severity-Marker", purpose: "Quelle aller offenen PL-Items"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_items_per_batch", purpose: "Welche PL-Items sind welchen Batches zugeordnet"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.completed_sub_batches", purpose: "Welche Batches sind als done markiert"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.batch_stages", purpose: "Welche Stages sind pro Batch geplant"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "I_PIPELINE_STATE.impl_test_stages_per_batch", purpose: "Per-Batch Per-Stage Status (NEU Schema-Erweiterung)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.orphan_scan_after_each_batch", purpose: "Feature-Flag (Default true)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.orphan_severity_threshold", purpose: "Trigger-Schwelle (Default HIGH)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.orphan_scan_history", purpose: "Audit-Trail bisheriger Scans"}
  writes:
    - {file: "{WORKING_DIR}/_manifest.md", path: "BERATER_OUTPUTS.orphan_scan", purpose: "Scan-Ergebnis (pl_orphans, stage_orphans, decision, severity_summary)"}
    - {file: "{WORKING_DIR}/_manifest.md", path: "DF_BATCH_STATE.orphan_scan_history[append]", purpose: "Audit-Eintrag dieses Laufs"}
  calls: []
optional: false
invariants:
  - "INV-ORPH-1: Read-only auf parking-lot.md (kein Schreiben in PL)"
  - "INV-ORPH-2: Severity-Klassifikation MUSS folgen: CRITICAL > HIGH > MED > LOW > OBS > DESIGN-CLOSED"
  - "INV-ORPH-3: Stage-Level-Orphan immer mind. HIGH (Phantom-Done = potentielle Test-Coverage-Luecke)"
  - "INV-ORPH-4: trigger_recluster bool MUSS aus severity_threshold + count abgeleitet werden (kein Lead-Override)"
  - "INV-ORPH-5: Bei DESIGN-CLOSED-Items (Status [~] oder explicit DESIGN-CLOSED-Severity): NIE Re-Cluster triggern"
  - "INV-ORPH-6: Idempotent — bei wiederholtem Lauf gleicher State gleiches Output"
---

# _SDF_berater_orphan_scan — Orphan-Detection nach Batch-Ende (BL-NEW-60)

## Zweck

Nach jedem Batch-Ende (in SDF Phase 4) prueft dieser Berater ob **Orphans** existieren — PL-Items oder Stages die NICHT in der Pipeline gecovered sind und somit "vergessen" werden wuerden.

**Zwei Orphan-Klassen:**

1. **PL-Orphan:** Item in `parking-lot.md` (Status `[ ]`) ABER nicht in `batch_items_per_batch[*]`
2. **Stage-Orphan (Phantom-Done):** `batch_key` in `completed_sub_batches` ABER eine Stage aus `batch_stages[batch_key]` ist nicht `done` (z.B. "deferred", "skipped", "pending")

Bei detected Orphans mit Severity >= Threshold triggert der Berater einen IDF-Re-Cluster fuer die naechste Iteration. Iterative-Adaptive Pipeline.

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_orphan_scan                                   ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {VAULT}/Backlog/{slug}/6_PL/{bl_id}-parking-lot.md (alle [ ] Items) ║
║    Manifest.DF_BATCH_STATE.{batch_items_per_batch, completed,        ║
║      batch_stages, orphan_scan_after_each_batch, severity_threshold} ║
║    Manifest.I_PIPELINE_STATE.impl_test_stages_per_batch              ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    BERATER_OUTPUTS.orphan_scan = {                                   ║
║      scan_at: ISO,                                                   ║
║      pl_orphans: [{item_id, severity, source_line, ...}],           ║
║      stage_orphans: [{batch, stage, actual_status, severity}],      ║
║      severity_summary: {CRITICAL: N, HIGH: N, MED: N, LOW: N, ...}, ║
║      decision: {                                                     ║
║        trigger_recluster: bool,                                      ║
║        reason: string,                                               ║
║        recluster_args: string  // wenn trigger=true                  ║
║      }                                                               ║
║    }                                                                 ║
║    DF_BATCH_STATE.orphan_scan_history[append] = {scan_at, decision} ║
║                                                                      ║
║  RUFT:                                                               ║
║    KEINE Skills (reiner Decision-Berater).                          ║
║    Re-Cluster-Aufruf passiert in _SDF_orchestrate_post Phase 4     ║
║    BASIEREND auf BERATER_OUTPUTS.orphan_scan.decision.               ║
║                                                                      ║
║  PHASE: SDF Phase 4 (NACH loopDecision, VOR RE-BATCH/TERMINATE)     ║
║  MODELL-TIER: middle (Lese-intensiv + Severity-Klassifikation)      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## SEVERITY-CONVENTION (Projekt-agnostisch)

PL-Items in `parking-lot.md` sollen einen **Severity-Marker** haben. Bei fehlendem Marker wird auf Default mit WARN-Audit gemappt.

```
Severity-Hierarchie (hoechste zuerst):

  CRITICAL    → PR-Blocker, Daten-Verlust, Security-Risiko, Compliance-Gap
  HIGH        → Architektur-Bruch, Audit-Trail-Luecke, falsche Tests
  MED         → DRY-Violation, Wartungs-Last, Code-Quality
  LOW         → Cosmetic, Refactor-Folge-Story, Optional
  OBS         → Observation (informativ, kein Code-Aufwand)
  DESIGN-CLOSED → User-Decision dokumentiert, kein Code-Aufwand
```

**Marker-Variationen in parking-lot.md (alle akzeptiert):**

```
**Severity:** CRITICAL
**Severity:** HIGH
**Prioritaet:** HOCH       → mapped to HIGH
**Prioritaet:** MITTEL     → mapped to MED
**Prioritaet:** NIEDRIG    → mapped to LOW

(Multi-Token "**HIGH**" / "**CRITICAL**" in Beschreibung wird auch gescannt als Fallback)
```

**Status-Marker:**
```
[ ]   OFFEN                  → wird gescannt
[~]   FREEZE / DECIDED       → wird SKIPPED (treated as DESIGN-CLOSED)
[x]   DONE                   → wird SKIPPED
[!]   BLOCKER (NEU)          → wird gescannt, severity=CRITICAL minimum
[?]   HOLD (NEU)             → wird SKIPPED (treated as OBS)
```

---

## TRIGGER-LOGIC (Hybrid Severity-Threshold)

```
threshold = Manifest.DF_BATCH_STATE.orphan_severity_threshold ?? "HIGH"

trigger_recluster = false
reason = ""

# Stage-Orphans haben hoechste Prio — immer Re-Cluster
IF stage_orphans.length > 0:
  trigger_recluster = true
  reason = "Stage-Orphans detected (Phantom-Done): {N} batches haben deferred/skipped/pending Stages"

# CRITICAL — immer
ELSE IF severity_summary.CRITICAL > 0:
  trigger_recluster = true
  reason = "CRITICAL PL-Orphans detected: {N} items"

# HIGH — default threshold
ELSE IF severity_summary.HIGH > 0 AND threshold IN ["HIGH", "MED"]:
  trigger_recluster = true
  reason = "HIGH PL-Orphans detected: {N} items"

# MED — Aggregat-Schwelle 3
ELSE IF severity_summary.MED >= 3 AND threshold == "MED":
  trigger_recluster = true
  reason = "MED PL-Orphans aggregate >= 3 ({N} items)"

# LOW / OBS / DESIGN-CLOSED — nie triggern
ELSE:
  trigger_recluster = false
  reason = "Orphans unter Schwelle: HIGH=0, MED<3, LOW={N}, OBS={N}, DESIGN-CLOSED={N}"
```

---

## METHODOLOGIE (5 Schritte)

### Schritt 1: PL-Items laden + filtern

```
pl_path_primary  = "{VAULT}/Backlog/{slug}/6_PL/{bl_id}-parking-lot.md"
pl_path_fallback = "{VAULT}/Backlog/{slug}/6_PL/parking-lot.md"

pl_content = read(pl_path_primary) OR read(pl_path_fallback)

all_items = parse_pl_items(pl_content)
  # Parsing-Regeln:
  # - Section beginnt mit "### " ODER "- " mit Status-Marker
  # - Status-Marker: [ ] [~] [x] [!] [?]
  # - Severity aus **Severity:** ODER **Prioritaet:** ODER inline
  # - Item-ID aus erster Zeile (slug-form)

# Filter: nur Items mit Status-Marker zaehlen
open_items = items WHERE status IN [OFFEN, BLOCKER]   # [ ] und [!]
ignored_items = items WHERE status IN [FREEZE, HOLD, DONE]   # [~] [?] [x]
```

### Schritt 2: Batch-Coverage Matrix bauen

```
batch_items_per_batch = Manifest.DF_BATCH_STATE.batch_items_per_batch
all_assigned_items = flatten(batch_items_per_batch.values())

# PL-Orphans: open aber nicht assigned
pl_orphans = []
FOR item IN open_items:
  IF item.id NOT IN all_assigned_items:
    pl_orphans.append({
      item_id: item.id,
      severity: item.severity,
      source_line: item.line_number,
      status_marker: item.status,
      title: item.title,
      first_seen: item.date_added ?? scan_at
    })
```

### Schritt 3: Stage-Orphan Detection (Phantom-Done)

```
completed = Manifest.DF_BATCH_STATE.completed_sub_batches
batch_stages = Manifest.DF_BATCH_STATE.batch_stages
impl_per_batch = Manifest.I_PIPELINE_STATE.impl_test_stages_per_batch ?? {}

stage_orphans = []
FOR batch_key IN completed:
  expected_stages = batch_stages[batch_key] ?? [1]
  FOR stage IN expected_stages:
    # Schema-Erweiterung — per-batch Stage-Tracking:
    actual = impl_per_batch[batch_key]?[stage]?.status ?? "unknown"

    IF actual NOT IN ["done", "gold_reached"]:
      stage_orphans.append({
        batch: batch_key,
        stage: stage,
        actual_status: actual,
        severity: "HIGH",   # Phantom-Done immer mind. HIGH (INV-ORPH-3)
        note: "Batch markiert als done, aber Stage {stage} ist {actual}"
      })
```

### Schritt 4: Severity-Summary + Decision

```
severity_summary = {
  CRITICAL: count(pl_orphans WHERE severity == CRITICAL),
  HIGH:     count(pl_orphans WHERE severity == HIGH) + stage_orphans.length,
  MED:      count(pl_orphans WHERE severity == MED),
  LOW:      count(pl_orphans WHERE severity == LOW),
  OBS:      count(pl_orphans WHERE severity == OBS),
  DESIGN_CLOSED: count(pl_orphans WHERE severity == DESIGN-CLOSED)
}

# Apply Trigger-Logic (s.o.)
decision = apply_trigger_logic(severity_summary, stage_orphans, threshold)
```

### Schritt 5: Output + Audit

```
BERATER_OUTPUTS.orphan_scan = {
  scan_at: now_iso,
  scanner_version: "1.0.0",
  pl_orphans: [...],
  stage_orphans: [...],
  severity_summary: {...},
  threshold_used: threshold,
  decision: {
    trigger_recluster: decision.trigger,
    reason: decision.reason,
    recluster_args: "--mode=recluster --orphan-only --sticky-ids --from=orphan_scan"
      IF decision.trigger ELSE null
      # BL-298 2026-06-10: --from=orphan_scan ist PFLICHT (sonst from=direct -> falscher Chain-Pfad).
      # KEIN --no-chain: Auto-Build-Bounded (User-Entscheid) -> IDF Phase 8.5a chaint zu SDF, gebounded INV-IDF-ORPHAN-2.
  }
}

DF_BATCH_STATE.orphan_scan_history.append({
  scan_at: now_iso,
  batch_ended: previous_batch_key,
  pl_orphans_count: pl_orphans.length,
  stage_orphans_count: stage_orphans.length,
  trigger_recluster: decision.trigger
})

audit_jsonl_append({
  type: "ORPHAN_SCAN_DONE",
  pl_orphans: pl_orphans.length,
  stage_orphans: stage_orphans.length,
  severity_summary: {...},
  decision: decision.trigger,
  timestamp: now_iso
})

Logge: "[ORPHAN-SCAN] PL={N}, STAGE={M}, decision={trigger|skip}, reason={...}"
```

---

## OUTPUT-SCHEMA (Beispiel)

```yaml
BERATER_OUTPUTS.orphan_scan:
  scan_at: 2026-05-12T14:00:00Z
  scanner_version: "1.0.0"
  pl_orphans:
    - item_id: "design-decision-foreach-membres-null-skip"
      severity: HIGH
      source_line: 286
      status_marker: "[ ]"
      title: "DESIGN-DECISION — KEIN ForAllMembers null-skip"
      first_seen: 2026-05-12T11:30:00Z
  stage_orphans:
    - batch: batch_3
      stage: 3
      actual_status: "deferred"
      severity: HIGH
      note: "Batch markiert als done, aber Stage 3 ist deferred"
  severity_summary:
    CRITICAL: 0
    HIGH: 2     # 1 PL + 1 stage
    MED: 0
    LOW: 0
    OBS: 0
    DESIGN_CLOSED: 0
  threshold_used: HIGH
  decision:
    trigger_recluster: true
    reason: "Stage-Orphans detected (Phantom-Done): 1 batch hat deferred Stage"
    recluster_args: "--mode=recluster --orphan-only --sticky-ids --from=orphan_scan"
```

---

## INVARIANTEN

- **INV-ORPH-1:** Read-only auf parking-lot.md
- **INV-ORPH-2:** Severity-Hierarchie strikt: CRITICAL > HIGH > MED > LOW > OBS > DESIGN-CLOSED
- **INV-ORPH-3:** Stage-Level-Orphan immer mind. HIGH (Phantom-Done = Test-Coverage-Luecke)
- **INV-ORPH-4:** trigger_recluster aus severity_threshold + count abgeleitet (deterministisch)
- **INV-ORPH-5:** DESIGN-CLOSED + Status `[~]` / `[?]` NIE triggern
- **INV-ORPH-6:** Idempotent
- **INV-ORPH-7:** Bei `orphan_scan_after_each_batch == false`: ABORT mit SKIP-Audit (Feature-Flag aus)

---

## REGELN

- Keine Skill-Calls (reiner Decision-Berater)
- Keine Pipeline-State-Aenderung ausserhalb BERATER_OUTPUTS.orphan_scan + orphan_scan_history
- Bei fehlendem Severity-Marker: Default MED + WARN-Audit (Convention-Drift detected)
- Bei zerstoertem parking-lot.md: ABORT mit FAIL-Audit, SendMessage(team-lead, "PL-File unparsbar, manuelle Verifikation noetig")
- Max Token: 10k pro Scan (middle, ~2min)

---

## VERWENDUNG (in `_SDF_orchestrate_post.md` Phase 4)

```
# Nach _SDF_berater_loopDecision:

IF DF_BATCH_STATE.orphan_scan_after_each_batch == true:
  Skill(_SDF_berater_orphan_scan, args="{NAME}")
  decision = BERATER_OUTPUTS.orphan_scan.decision

  IF decision.trigger_recluster == true:
    Logge: "[Phase 4] Orphan-Scan triggered Re-Cluster: {decision.reason}"

    # Max-Iteration-Schutz (siehe INV-ORPH-X)
    recluster_count = DF_BATCH_STATE.orphan_scan_history.count(trigger=true)
    IF recluster_count >= 3:
      SendMessage(team-lead, "Max 3 Re-Cluster-Iterations erreicht. HiL-Decision noetig.")
      # User-Confirm via AskUserQuestion ODER abort
    ELSE:
      Skill(_IDF_orchestrate, args="{NAME} {decision.recluster_args}")
      # IDF Re-Cluster; IDF chained SELBST zurueck zu SDF via Phase 8.5a orphan_scan-Zweig (BL-298 2026-06-10)
      # (recluster_args traegt --from=orphan_scan -> <3 Iter: RE-BATCH-Chain (Auto-Build-Bounded); >=3: HiL-Alert).
ELSE:
  Logge: "[Phase 4] orphan_scan_after_each_batch=false — SKIP Scan"
```

---

## BL-NEW-60 Lehre (Projekt-agnostisch)

Iterative-Adaptive Pipeline mit Orphan-Scan-Trigger verhindert:
1. **PL-Orphans:** PL-Items die nach IDF-Plan entstehen werden nie abgearbeitet
2. **Stage-Orphans (Phantom-Done):** Batches die als done markiert sind aber deferred Stages haben
3. **Decision-Drift:** Lead-Heuristik die Stages skipt ohne Validation

Trade-Off Compute-Kosten vs Adaptivitaet wird ueber Severity-Threshold gesteuert.
Hybrid-Default: HIGH-Threshold — LOW/OBS/DESIGN-CLOSED-Orphans sammeln sich fuer Story-Ende-Review.

Case-Anchor: `.claude/_parking-lot.md` BL-NEW-60.
