---
status: active
version: 1.2.0
created: 2026-05-04
updated: 2026-05-24
op: IntermediateFactory
phase: 3.7
type: berater
sync_tier: REVERSE
parent: _IDF_orchestrate
chain_position: middle
model_tier: ceiling
feature_anchor: BL-151
bl_198_ak4: INV-IDF-REVERSE-1
bl_201_ak2: INV-PL-WRITER-1
invariants:
  - "INV-PL-WRITER-1 (BL-201): Dieser Berater ist ERLAUBTER Writer c) fuer parking-lot.md (Reverse-Annotationen via Phase 3.7). Schreibt NUR Annotationen zurueck, keine Forward-Items."
  - "INV-IDF-REVERSE-1 (BL-198): Phase 3.7 ist AUSSCHLIESSLICH Reverse-Sync (PL → Model)."
---

# /_IDF_berater_modelSync (Phase 3.7 — PL → Model/Spec Promotion)

> **Zweck:** Schliesst die "Schwarzes Loch"-Luecke in IDF. Stabile Findings aus
> Parking-Lot werden in Model.md (Wahrheiten W{n}) und Spec.md (Constraints)
> promoviert. So bleiben Model+Spec synchron mit dem aktuellen Wissensstand —
> NICHT NUR PL waechst, auch das kanonische Wissen.
>
> **REVERSE-Sync Tier (BL-198 AK-4, INV-IDF-REVERSE-1):**
> Phase 3.7 ist AUSSCHLIESSLICH Reverse-Sync: PL → Model (Continuous Learning
> durch /_parking-lot Entry-3-Mechanik, BL-201). Forward-Richtung (Spec → PL)
> gehoert zur A-Pipeline (BL-197/198 Pipeline-Schnitt). Phase 3.7 BLEIBT in IDF.
>
> **Problem das wir loesen (BL-151 Erkenntnis 2026-05-04):**
> Worker im I-Pipeline lesen Model+Spec. Wenn IDF nur PL fuellt aber Model nicht
> updatet, bekommen Worker veraltetes Wissen. PL wird zum Schwarzen Loch.

[VERTRAG]
LIEST:
  - {bl_folder}/6_PL/{bl_id}-parking-lot.md
    → Frontmatter, alle Items, Audits, Leitprinzipien
    → BERATER_OUTPUTS.plAggregation.master_file
  - {bl_folder}/2_Model/{NAME}_Model.md
    → bestehende W{n}-Liste (zur Idempotenz-Pruefung)
  - {bl_folder}/3_Spec/{NAME}_Spec.md
    → bestehende Constraints (Sektion VALIDATION/CONSTANTS)
  - .claude/analysis/_manifest.md
    → BERATER_OUTPUTS.itemContext (Per-Item Stabilitaet)
    → BERATER_OUTPUTS.validator (Per-Item validity)

SCHREIBT:
  - {bl_folder}/2_Model/{NAME}_Model.md
    → NEUE W{n}-Eintraege fuer stabile Wahrheiten (append)
    → Frontmatter version_increment + last_synced
  - {bl_folder}/3_Spec/{NAME}_Spec.md
    → NEUE Constraints/Validation-Regeln (append)
    → Frontmatter version_increment + last_synced
  - {bl_folder}/6_PL/{bl_id}-parking-lot.md
    → Per-promovierten Item: `synced-to-model: {DATE}` Marker
    → KEIN Loeschen — Item bleibt fuer Audit-Trail
  - .claude/analysis/_manifest.md
    → BERATER_OUTPUTS.modelSync (siehe Schema)
  - {bl_folder}/2_Model/_modelSync_log_{DATE}.md
    → Append-Only Log: was promoviert wurde, mit PL-Source-References

BERATER_OUTPUTS.modelSync:
  promoted_truths_count:    int (neue W{n})
  promoted_constraints_count: int (neue Spec-Constraints)
  skipped_items_count:      int (nicht-stabil oder bereits synced)
  total_items_evaluated:    int
  promoted_items_ids:       list[string] (welche PL-Items wurden synced)
  model_path:               string
  spec_path:                string
  log_path:                 string
  exit_code:                0 OK | 1 WARN (nichts promoviert) | 2 ABORT

PFLICHT-LOGGING (Worker im Terminal):
  [modelSync] reading PL: {path} ({n_items} items)
  [modelSync] reading Model: {path} ({n_truths} W{{n}})
  [modelSync] reading Spec: {path} ({n_constraints} constraints)
  [modelSync] evaluating {n} items for promotion
  [modelSync] promote: {item_id} → W{n} "{truth}" (reason: {criterion})
  [modelSync] skip:    {item_id} (reason: not stable / already synced / open)
  [modelSync] DONE — {N} truths promoted, {M} constraints promoted

CROSS-REFERENCES:
  - Phase 4 dependencyAnalyzer profitiert: Items haben jetzt model_refs
  - Phase 7 batchPlan profitiert: Aggregate basieren auf aktuellem Model
  - I-Pipeline cleanCodeArchitect liest danach AKTUELLES Model+Spec
[/VERTRAG]

[INVARIANTEN]
- INV-MS-1: IDEMPOTENT — bereits synced Items (Marker `synced-to-model:`)
            werden uebersprungen. Re-Run schreibt nichts doppelt.
- INV-MS-2: CONSERVATIVE — nur STABILE Findings promovieren. Kriterien:
              a) Item hat `[x]` Status (DONE)
              b) Item hat Audit-Ergebnis ("Audit: ... konform/widersprueche/...")
              c) Item enthaelt Leitprinzip ("PRINZIP:", "Leitprinzip:", "FINAL")
              d) Item hat User-Direktive ("FINAL-FINAL", User-Decision)
              e) Item hat math-derivation mit verifizierten Zahlen
            ELSE: skip (lieber zu wenig als falsche Wahrheit promoten)
- INV-MS-3: SOURCED — jede neue W{n} hat Source-Reference im Format
            "Source: BL-{ID}-PL-{NR} ({DATE})" als Frontmatter-Field oder
            Inline-Hinweis nach der Wahrheit.
- INV-MS-4: APPEND-ONLY — Model + Spec werden NUR erweitert, nie ueberschrieben.
            Bestehende W{n} bleiben unangetastet (Konflikt-Aufloesung manuell).
- INV-MS-5: VERSIONING — Model + Spec bekommen Frontmatter-Update:
              version: X.Y → X.(Y+1)
              last_synced: {ISO_DATE}
              synced_from: {bl_id}-parking-lot.md (Audit-Trail)
- INV-MS-6: PFLICHT-LOG — modelSync_log_{DATE}.md mit kompletter Traceability:
              jede Promotion mit Source-Item, Reason, Diff
- INV-MS-7: CONFLICT-DETECTION — wenn neue Truth existiertem W{n} widerspricht:
              promote NICHT, schreibe in BERATER_OUTPUTS.modelSync.conflicts[]
              Lead muss manuell aufloesen.
[/INVARIANTEN]

---

## PHASE 3.7: MODEL-SYNC

### 3.7.1 Pfad-Resolution + Read-All

```
paths = Read(_manifest.md).BERATER_OUTPUTS.teamSetup
bl_folder = paths.bl_folder

pl_path     = f"{bl_folder}/6_PL/{bl_id}-parking-lot.md"
model_path  = f"{bl_folder}/2_Model/{NAME}_Model.md"
spec_path   = f"{bl_folder}/3_Spec/{NAME}_Spec.md"
log_path    = f"{bl_folder}/2_Model/_modelSync_log_{DATE}.md"

pl_content    = Read(pl_path)
model_content = Read(model_path)
spec_content  = Read(spec_path)

Logge: f"[modelSync] reading PL: {pl_path} ({count_items(pl_content)} items)"
Logge: f"[modelSync] reading Model: {model_path} ({count_truths(model_content)} W{{n}})"
Logge: f"[modelSync] reading Spec: {spec_path}"
```

### 3.7.2 Stabilitaets-Klassifikation

```
items = parse_pl(pl_content)
existing_truths = parse_truths(model_content)
existing_constraints = parse_constraints(spec_content)

candidates = []
for item in items:
  # Skip wenn bereits synced
  if item.has_marker("synced-to-model"):
    log_skip(item.id, "already synced")
    continue

  # Stabilitaets-Kriterien (INV-MS-2)
  stable = False
  reasons = []

  if item.status == "[x]":  # done
    stable = True
    reasons.append("status:done")
  if item.has_audit_result():  # "Audit: ... konform/widersprueche..."
    stable = True
    reasons.append("audit-completed")
  if item.has_keyword("PRINZIP:") or item.has_keyword("Leitprinzip:"):
    stable = True
    reasons.append("principle")
  if item.has_keyword("FINAL-FINAL") or item.has_user_direktive():
    stable = True
    reasons.append("user-final")
  if item.has_math_derivation_verified():
    stable = True
    reasons.append("math-verified")

  if stable:
    candidates.append((item, reasons))
  else:
    log_skip(item.id, "not stable")

Logge: f"[modelSync] evaluating {len(candidates)} stable candidates"
```

### 3.7.3 Promotion: Truth → Model

```
new_truths = []
conflicts = []
next_w = max([t.id for t in existing_truths]) + 1

for item, reasons in candidates:
  # Generiere Truth-Statement aus Item
  truth_text = synthesize_truth(item)

  # Konflikt-Check (INV-MS-7)
  conflict = find_conflicting_truth(truth_text, existing_truths)
  if conflict:
    conflicts.append({item: item, with: conflict.id})
    log_skip(item.id, f"conflicts with {conflict.id}")
    continue

  # Truth-Block bauen
  truth_block = format_W_block(
    id=f"W{next_w}",
    text=truth_text,
    source=f"BL-{BL_ID}-{item.id} ({DATE})",
    reasons=reasons,
  )
  new_truths.append((next_w, truth_block, item))
  next_w += 1
  Logge: f"[modelSync] promote: {item.id} -> W{next_w-1} ({reasons})"

# Append zu Model.md
if new_truths:
  Append(model_path, build_truths_section(new_truths))
  Update(model_path).frontmatter.version = increment(version)
  Update(model_path).frontmatter.last_synced = ISO_DATE()
  Update(model_path).frontmatter.synced_from = pl_path
```

### 3.7.4 Promotion: Constraint → Spec

```
new_constraints = []
for item, reasons in candidates:
  if item.is_constraint_type():  # Validierungs-Regel, MaxLength, etc.
    constraint_text = synthesize_constraint(item)
    if not exists_in(constraint_text, existing_constraints):
      new_constraints.append((constraint_text, item))
      Logge: f"[modelSync] constraint: {item.id} -> Spec"

if new_constraints:
  Append(spec_path, build_constraints_section(new_constraints))
  Update(spec_path).frontmatter.version = increment(version)
  Update(spec_path).frontmatter.last_synced = ISO_DATE()
```

### 3.7.5 PL-Items markieren

```
# Pro promovierten Item: synced-to-model Marker setzen
for (_, _, item) in new_truths:
  Update_in_file(pl_path, item.id, add_marker="synced-to-model: " + DATE)

# Marker-Format in PL-Item:
#   - [x] **PL-XX** ... synced-to-model: 2026-05-04
```

### 3.7.6 Log + Output

```
Write(log_path, build_log(new_truths, new_constraints, conflicts))

Schreibe BERATER_OUTPUTS.modelSync = {
  promoted_truths_count: len(new_truths),
  promoted_constraints_count: len(new_constraints),
  skipped_items_count: len(items) - len(candidates) - already_synced_count,
  total_items_evaluated: len(items),
  promoted_items_ids: [item.id for (_,_,item) in new_truths],
  model_path: model_path,
  spec_path: spec_path,
  log_path: log_path,
  conflicts: conflicts,
  exit_code: 0 if (new_truths or new_constraints) else 1
}

Logge: f"[modelSync] DONE — {len(new_truths)} truths, {len(new_constraints)} constraints, {len(conflicts)} conflicts"
return
```

---

## ABHAENGIGKEITEN

- **BL-151** (in progress): Vault-Driven Development. Diese Berater-Datei
  schliesst die "Schwarzes-Loch"-Luecke (Erkenntnis 2026-05-04).
- **Phase 3.6 itemContext** muss done sein (liefert Per-Item Kontext).
- **Phase 3.5 validator** muss done sein (liefert Per-Item validity).
- **Model.md + Spec.md** muessen existieren mit Frontmatter (version, last_synced).

## FOLGE-TASKS (in BL-151 Backlog aufnehmen)

- **NEU-IDF-9**: Truth-Synthese-Logik (synthesize_truth) als eigene Sub-Routine
  oder eigener Berater. Aktuell heuristisch.
- **NEU-IDF-10**: Conflict-Resolution-UI fuer manuelle Aufloesung wenn
  conflicts != []. Aktuell: Lead muss manuell ranschauen.
- **NEU-IDF-11**: SC-Pipeline analoger modelMaintain ist anders gestrickt
  (intra-cycle), modelSync ist post-PL. Beide sollten konvergieren.
- **NEU-I-2**: I-Pipeline cleanCodeArchitect Pflicht-Read soll auch PL umfassen
  (transitional bis modelSync stabil ist).

## QUICK-START

```
# Manuell als Skill aufrufbar (zum Test):
Skill(_IDF_berater_modelSync, args="DCSRE-94")

# Oder via _IDF_orchestrate Phase 3.7 (automatisch nach 3.6):
/_IDF_orchestrate DCSRE-94 ...   # ruft 3.7 als Teil der AK_PER_PL Phase
```
