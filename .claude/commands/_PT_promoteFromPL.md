---
type: building-block
status: active
version: 1.0.0
created: 2026-05-06
op: PostBatch
phase: 4
type_role: promoter
related: _IDF_berater_modelSync, _PT_extract, _PT_update, _SL_promoteFromPL
chain_position: post-batch
model_tier: opus
---

# /_PT_promoteFromPL — Per-Story-PL → PatternLibrary (Vault) Promotion

**Status:** v1.0.0 (initial — Schwester-Command von `_IDF_berater_modelSync`)
**Actor:** PATTERN-PROMOTER
**Zweck:** Schliesst die Lücke zwischen per-Story-Parking-Lot und der globalen PatternLibrary im Vault. Stabile architektur-/struktur-relevante PL-Items werden als Pattern-Kandidaten in `{VAULT}/ParkingLotGlobal/` geschrieben, sodass der bestehende `_PT_extract --parking-lot-walk` sie aufgreifen und in `Libraries/PatternLibrary/_project/{LAYER}/` als DRAFT-Pattern persistieren kann.

> **Architektur (BL-153/BL-154):** Per-Story-PL liegt in `{bl_folder}/6_PL/{bl_id}-parking-lot.md` (projekt-lokal). Die PatternLibrary lebt im Vault unter `{VAULT_ROOT}/Libraries/PatternLibrary/` (cross-projekt). Brücke: dieser Command + `_PT_extract --parking-lot-walk`.

> **Abgrenzung zu `_IDF_berater_modelSync`:** modelSync schreibt nach Model/Spec (intra-Projekt). DIESER Command schreibt nach Vault-PT-Kandidaten (cross-projekt, Library).

---

## Aufruf

```
/_PT_promoteFromPL {BL-ID} [--dry-run] [--auto-extract]
```

| Parameter | Pflicht | Default | Beispiel |
|-----------|---------|---------|----------|
| `BL-ID` | JA | — | `BL-151`, `DCSRE-94` |
| `--dry-run` | NEIN | false | Zeigt was promoviert wuerde, schreibt nichts |
| `--auto-extract` | NEIN | false | Ruft anschliessend automatisch `_PT_extract --parking-lot-walk` auf |

---

## VERTRAG

```
+======================================================================+
| VERTRAG: /_PT_promoteFromPL                                          |
+======================================================================+
| LIEST:                                                                |
|   {bl_folder}/6_PL/{bl_id}-parking-lot.md  (per-Story-PL)            |
|   {bl_folder}/2_Model/{NAME}_Model.md       (Layer-Hinweise)          |
|   {VAULT_ROOT}/Libraries/PatternLibrary/_index.md  (Duplikat-Check)  |
|   {VAULT_ROOT}/Libraries/PatternLibrary/_project/{LAYER}/*.md        |
|   .claude/analysis/_manifest.md             (BERATER_OUTPUTS)        |
|                                                                       |
| SCHREIBT:                                                             |
|   {VAULT}/ParkingLotGlobal/PT-Kandidaten-{BL_ID}-{DATE}.md           |
|     -> Pattern-Kandidaten mit [PT-Kandidat] Tag (Format fuer         |
|        _PT_extract --parking-lot-walk konform)                       |
|   {bl_folder}/6_PL/{bl_id}-parking-lot.md                            |
|     -> Per-promovierten Item: `synced-to-pattern-library: {DATE}`    |
|     -> KEIN Loeschen — Audit-Trail bleibt                            |
|   .claude/analysis/_manifest.md                                       |
|     -> BERATER_OUTPUTS.ptPromote (siehe Schema)                      |
|   {bl_folder}/2_Model/_ptPromote_log_{DATE}.md                       |
|     -> Append-Only Log                                                |
|                                                                       |
| BERATER_OUTPUTS.ptPromote:                                            |
|   promoted_candidates_count:    int (neue PT-Kandidaten)              |
|   skipped_items_count:          int (nicht-stabil oder bereits synced)|
|   total_items_evaluated:        int                                   |
|   promoted_items_ids:           list[string] (welche PL-Items)        |
|   vault_kandidaten_path:        string                                |
|   log_path:                     string                                |
|   exit_code:                    0 OK | 1 WARN (nichts) | 2 ABORT     |
|                                                                       |
| ACTOR: PATTERN-PROMOTER                                               |
| MODELL-TIER: opus (klassifizierungs-intensiv)                         |
+======================================================================+
```

---

## INVARIANTEN (analog `_IDF_berater_modelSync` INV-MS-1..7)

| INV | Beschreibung |
|-----|-------------|
| INV-PTP-1 | **IDEMPOTENT** — Items mit Marker `synced-to-pattern-library` werden uebersprungen. Re-Run schreibt nichts doppelt. |
| INV-PTP-2 | **CONSERVATIVE** — nur **stabile + pattern-wuerdige** Items promovieren. Kriterien siehe 3.2 unten. |
| INV-PTP-3 | **SOURCED** — jeder Vault-Kandidat hat `Source: BL-{ID}-PL-{NR} ({DATE})` Reference im Frontmatter. |
| INV-PTP-4 | **APPEND-ONLY** — Vault-Kandidaten-Datei wird NUR erweitert, bestehende Eintraege unangetastet. |
| INV-PTP-5 | **VAULT-ONLY** — schreibt **ausschliesslich** nach `{VAULT_ROOT}/...` und `{bl_folder}/...`. NIEMALS direkt in `Libraries/PatternLibrary/_project/{LAYER}/` (das macht `_PT_extract` nach Battle-Test). |
| INV-PTP-6 | **PFLICHT-LOG** — `_ptPromote_log_{DATE}.md` mit Traceability: jede Promotion mit Source-Item, Layer-Heuristik, Reason. |
| INV-PTP-7 | **DUPLIKAT-CHECK** — vor Vault-Schreiben: prüfe ob analoges Pattern bereits in `Libraries/PatternLibrary/_project/{LAYER}/` existiert. Wenn ja: SKIP + Log. |
| INV-PTP-8 | **NO-DIRECT-PROMOTION** — Items werden NICHT direkt zu `status: promoted` Patterns. Sie werden zu `[PT-Kandidat]`-getaggten Vault-PL-Items, die `_PT_extract --parking-lot-walk` als `confidence: low, status: experimental` aufnimmt. |
| INV-PTP-9 | **PROMOTION-MUTEX (BL-320)** — vor dem Vault-Library-Schreiben MUSS der gemeinsame Promotion-Lock gehalten werden (`factory_lock.acquire_promotion_lock`). PT und SL teilen sich EINEN Lock (`bl_id="_pt_promotion"`), damit zwei parallele Batches nie gleichzeitig in dieselbe Library promovieren (Library-Write-Race). Stale-Reclaim erbt von `is_bl_stale` (kein Dead-Lock bei Worker-Tod). |

---

## CHAIN-POSITION

```
SDF Phase 3 (modelSync) DONE
     │
     ▼
[/_PT_promoteFromPL {BL-ID}]   ← DIESER COMMAND
     │
     ├──► {VAULT}/ParkingLotGlobal/PT-Kandidaten-{BL_ID}-{DATE}.md
     │      (Pattern-Kandidaten mit [PT-Kandidat] Tag)
     │
     ▼  --auto-extract (optional)
[/_PT_extract --parking-lot-walk]  ← bestehender Command
     │
     ▼
Libraries/PatternLibrary/_project/{LAYER}/{name}.md  (DRAFT, confidence: low)
     │
     ▼
[/_Pre_PR_orchestrate Battle-Test]  → PROMOTED (W257)
```

---

## ABLAUF

### Phase 1: Pfad-Resolution + Read-All

```python
paths = read_manifest_paths()  # {bl_folder, vault_root, NAME}
bl_folder = paths.bl_folder
vault_root = paths.vault_root  # via resolve_vault_root.py (ARCH-N9)

pl_path        = f"{bl_folder}/6_PL/{bl_id}-parking-lot.md"
model_path     = f"{bl_folder}/2_Model/{NAME}_Model.md"
master_index   = f"{vault_root}/Libraries/PatternLibrary/_index.md"
vault_pl_dir   = f"{vault_root}/ParkingLotGlobal"
kandidaten_path = f"{vault_pl_dir}/PT-Kandidaten-{BL_ID}-{DATE}.md"
log_path       = f"{bl_folder}/2_Model/_ptPromote_log_{DATE}.md"

pl_content       = Read(pl_path)
model_content    = Read(model_path)
existing_pt_idx  = Read(master_index)

Logge: f"[ptPromote] reading PL: {pl_path} ({count_items(pl_content)} items)"
Logge: f"[ptPromote] reading PT-Index: {master_index} ({count_patterns(existing_pt_idx)} patterns)"
```

#### Phase 1b: Promotion-Mutex erwerben (INV-PTP-9, BL-320)

Direkt **nach** der Pfad-Resolution und **vor** dem Read-All den gemeinsamen Promotion-Lock
erwerben. PT und SL nutzen denselben Lock (`bl_id="_pt_promotion"`), damit zwei parallele
Batches nie gleichzeitig in dieselbe Vault-Library promovieren (Library-Write-Race). Der Lock
wird in Phase 8 (bzw. bei `--auto-extract` ueber Phase 9 hinaus) wieder freigegeben.

```python
import factory_lock as fl   # Single-Source des Promotion-Mutex (Wrapper ueber BL-Locks)

worker_id = f"pt-promote-{BL_ID}-{os.getpid()}"

# acquire_promotion_lock -> .locks/_pt_promotion.lock; erbt is_bl_stale-Reclaim (AK-3).
# True = exklusiv erworben / False = von anderem Promoter (non-stale) gehalten -> warten/abbrechen.
if not fl.acquire_promotion_lock(worker_id=worker_id, ttl=600, vault_root=vault_root, phase="promote"):
  Logge: "[ptPromote] Promotion-Lock von anderem Promoter gehalten — ABORT (exit_code=2) oder spaeter erneut versuchen."
  # exit_code=2 (ABORT) — KEIN Library-Schreiben ohne Lock.
  return

# Convenience-Form (Skill-Seam): with fl.promotion_lock(worker_id=worker_id, vault_root=vault_root):
#     <Phase 2 .. Phase 8 (und Phase 9 bei --auto-extract)>
# acquire @__enter__, release @__exit__ (auch bei Exception) — deckt Phase 2-9 ab.
```

> **🔌 FAN-IN-ANDOCK-PUNKT fuer BL-230 (BL-320 AK-2, AK-MOTOR-WELLE) — NUR DOKU, KEINE BARRIER HIER.**
>
> Der hier in Phase 1b erworbene und in Phase 8 (bzw. Phase 9 bei `--auto-extract`) freigegebene
> Promotion-Lock (`factory_lock.acquire_promotion_lock(bl_id="_pt_promotion")`) ist der
> **dokumentierte ANDOCK-PUNKT** fuer die kuenftige **BL-230-Wellen-Fan-In-Barrier**. PT **und** SL
> (`_SL_promoteFromPL`, INV-SLP-9, Phase 1b/8) referenzieren denselben Lock (`_pt_promotion`) —
> daher entsteht **EIN gemeinsamer Andock-Punkt** fuer beide Promoter.
>
> **Migrations-Skizze (sobald die BL-230 Wellen-Barrier existiert):**
> - Die `acquire_promotion_lock` (Phase 1b) / `release_promotion_lock` (Phase 8/9) Calls wandern
>   **IN die Fan-In-Barrier des Motors**. Die Promotionen serialisieren dann am **kommutativen
>   Fan-In-Punkt der Welle** (single-writer am Barrier-Austritt), statt dass parallele Batch-Worker
>   einzeln um den mkdir-Lock racen.
> - Der Lock **bleibt als Korrektheits-Fallback** erhalten (Re-Entrancy / Out-of-Wave-Aufrufe /
>   manuelle Einzel-Promotions), aber der **Normalpfad serialisiert an der Barrier**, nicht mehr am
>   Lock.
>
> **Abgrenzung (WICHTIG):** Dies ist **ausschliesslich** ein dokumentierter Andock-Punkt. **HIER
> wird KEINE Barrier gebaut.** Die Barrier selbst bleibt **BL-230** (`gate_for: BL-230`,
> Wahrheits-Contention-Achse). Siehe BL-320 AK-2 + BL-230. Der bestehende Mutex (INV-PTP-9) bleibt
> unveraendert; dieser Block ergaenzt ihn nur um den Migrationspfad.

### Phase 2: Stabilitaets-Klassifikation

Identische Stabilitaets-Kriterien wie modelSync (INV-MS-2):

```python
items = parse_pl(pl_content)
candidates = []

for item in items:
  if item.has_marker("synced-to-pattern-library"):
    log_skip(item.id, "already synced to PT-Library")
    continue

  stable = False
  reasons = []
  if item.status == "[x]":          stable = True; reasons.append("status:done")
  if item.has_audit_result():       stable = True; reasons.append("audit-completed")
  if item.has_keyword("PRINZIP:"):  stable = True; reasons.append("principle")
  if item.has_keyword("FINAL-FINAL"): stable = True; reasons.append("user-final")

  if stable:
    candidates.append((item, reasons))
  else:
    log_skip(item.id, "not stable")

Logge: f"[ptPromote] {len(candidates)} stable candidates evaluated"
```

### Phase 3: Pattern-Wuerdigkeit (Pattern-spezifisches Filter)

Nicht jedes stabile Item ist pattern-wuerdig. Filter — die 5-Signal-Klassen-Heuristik lebt seit
BL-237 batch_C5 (AK-CTX-WORTHINESS-EXTRACT, F1/§4.1) als aufrufbare **Single-Source** in
`pattern_library.py` (`is_pattern_worthy()` / `worthiness_reasons()`). KEIN Inline-Reimpl mehr —
der Aufruf ersetzt das frueher hier duplizierte Pseudocode (Extract-not-reimplement; derselbe
Aufruf gilt im Konsumenten `_PT_berater_materialize`, INV-MAT-5 worthiness_pending aufgeloest):

```python
import pattern_library as pl   # Single-Source der Worthiness-Heuristik (5 Signal-Klassen)

pattern_worthy = []
for item, reasons in candidates:
  # is_pattern_worthy()/worthiness_reasons() = die 5 Signal-Klassen 1:1 (arch-keyword,
  # cross-cutting, validation-pattern, compiler-rule, has-concrete-example) aus pattern_library.py
  # (NICHT mehr hier inline reimplementiert — BL-237 batch_C5, F1).
  w_reasons = pl.worthiness_reasons(item)   # item: str|dict|obj mit .text (candidate-tolerant)
  if w_reasons:                             # == pl.is_pattern_worthy(item)
    pattern_worthy.append((item, reasons + w_reasons))
  else:
    log_skip(item.id, "not pattern-worthy (no arch/cross-cutting signals)")

Logge: f"[ptPromote] {len(pattern_worthy)} of {len(candidates)} candidates are pattern-worthy"
```

> **Anti-Doppel-Impl-Invariante (BL-237 batch_C5 K-1):** Die 5 Signal-Klassen duerfen hier NICHT
> erneut inline ausgeschrieben werden. Einzige Quelle ist `pattern_library.is_pattern_worthy()` /
> `worthiness_reasons()`. Eine zweite lokale Reimplementierung der Keyword-Listen ist ein
> Signal-Parity-Drift-Bruch (Extract-to-callable-Verletzung, §4.1).

### Phase 4: Layer-Heuristik

Layer-Zuordnung pro Kandidat (analog `_PT_extract` Schritt 0):

```python
def derive_layer(item) -> str:
  # Datei-Pfad-Hinweis
  if "Controller" in item.text:    return "BE-CONT"
  if "Service" in item.text:       return "BE-CORE"
  if ".Domain" in item.text:       return "BE-DOMAIN"
  if "Dto" in item.text or ".DTO." in item.text: return "BE-DTO"
  if "Profile" in item.text:       return "BE-MAP"
  if "Middleware" in item.text:    return "BE-MID"
  if "Auth" in item.text:          return "BE-AUTH"
  if "Migration" in item.text:     return "BE-MIGRATION"
  if "Test" in item.text:          return "BE-TEST"
  # XML-Doc / Compiler-Regeln → _generic
  if any(kw in item.text for kw in ["XML-Doc", "StyleCop", "SA1611", "SA1615"]):
    return "_generic"
  # Fallback
  return "_generic"
```

### Phase 5: Duplikat-Check (INV-PTP-7)

```python
for item, reasons in pattern_worthy:
  layer = derive_layer(item)
  proposed_name = synthesize_pattern_name(item)  # kebab-case

  # Existiert in Vault-PatternLibrary schon?
  existing = grep_pattern_name(master_index, proposed_name) or \
             check_layer_dir(vault_root, layer, proposed_name)

  if existing:
    log_skip(item.id, f"duplicate: {existing} already in PT-Library")
    continue
  # ... siehe Phase 6
```

### Phase 6: Vault-Kandidaten-Datei schreiben (INV-PTP-3, -4, -5, -8)

```python
kandidaten_entries = []
for item, reasons in pattern_worthy_filtered:
  layer = derive_layer(item)
  name = synthesize_pattern_name(item)

  entry = format_pt_kandidat(
    tag="[PT-Kandidat]",
    name=name,
    layer=layer,
    description=item.short_description,
    code_example=item.code_block_or_file_ref,
    source=f"BL-{BL_ID}-{item.id} ({DATE})",
    reasons=reasons,
    confidence_cap="low",  # INV-PTP-8: kein direct promotion
  )
  kandidaten_entries.append((entry, item))

# Vault-Kandidaten-Datei
if kandidaten_entries:
  Write(kandidaten_path, build_kandidaten_md(kandidaten_entries, BL_ID, DATE))
  Logge: f"[ptPromote] wrote {len(kandidaten_entries)} candidates to {kandidaten_path}"
```

**Format der Vault-Kandidaten-Datei:**

```markdown
---
type: pattern-candidates
source_story: {BL_ID}
created: {DATE}
created_by: /_PT_promoteFromPL
candidates_count: {N}
---

# Pattern-Kandidaten aus {BL_ID} ({DATE})

> Gesammelt aus per-Story-PL fuer `_PT_extract --parking-lot-walk`.
> Confidence-Cap: low (INV-PTP-8 — Promotion durch Battle-Test, nicht durch diesen Command).

## Kandidaten

### [PT-Kandidat] {pattern-name-1}
- **Layer:** {LAYER}
- **Beschreibung:** {description}
- **Source:** BL-{ID}-{PL-ITEM-ID} ({DATE})
- **Worthiness:** {reasons-comma-separated}
- **Code-Beispiel:**
  ```csharp
  {code_block}
  ```

### [PT-Kandidat] {pattern-name-2}
...
```

### Phase 7: Source-Items markieren (INV-PTP-1)

```python
for (_, item) in kandidaten_entries:
  Update_in_file(pl_path, item.id, add_marker=f"synced-to-pattern-library: {DATE}")
```

### Phase 8: Log + Output

```python
Write(log_path, build_log(kandidaten_entries, skipped_items, conflicts))

manifest_update("BERATER_OUTPUTS.ptPromote", {
  promoted_candidates_count: len(kandidaten_entries),
  skipped_items_count: len(items) - len(pattern_worthy_filtered),
  total_items_evaluated: len(items),
  promoted_items_ids: [item.id for (_, item) in kandidaten_entries],
  vault_kandidaten_path: kandidaten_path,
  log_path: log_path,
  exit_code: 0 if kandidaten_entries else 1,
})

Logge: f"[ptPromote] DONE — {len(kandidaten_entries)} candidates promoted to Vault"

# Promotion-Mutex freigeben (INV-PTP-9, BL-320) — NACH Log+Output.
# Bei --auto-extract bleibt der Lock ueber Phase 9 hinaus gehalten (Library-Write geht
# in _PT_extract weiter); dann erst NACH Phase 9 releasen (siehe Phase 9).
if "--auto-extract" not in args:
  fl.release_promotion_lock(worker_id=worker_id, vault_root=vault_root)
  Logge: "[ptPromote] Promotion-Lock freigegeben."
```

### Phase 9 (optional): Auto-Extract

```python
if "--auto-extract" in args:
  Logge: "[ptPromote] --auto-extract: triggering /_PT_extract --parking-lot-walk"
  Skill(skill="_PT_extract", args="--parking-lot-walk")
  # Lock-Ausdehnung (INV-PTP-9): _PT_extract schreibt in die Library -> Lock erst JETZT releasen.
  fl.release_promotion_lock(worker_id=worker_id, vault_root=vault_root)
  Logge: "[ptPromote] Promotion-Lock nach --auto-extract freigegeben."
```

---

## QUICK-START

```bash
# Standard-Aufruf nach SDF Phase 3
/_PT_promoteFromPL DCSRE-94

# Mit auto-extract → direkt in PatternLibrary
/_PT_promoteFromPL DCSRE-94 --auto-extract

# Dry-Run zum Testen
/_PT_promoteFromPL DCSRE-94 --dry-run
```

---

## INTEGRATION (SDF Phase 4)

Wird nach `_IDF_berater_modelSync` (Phase 3.7) aufgerufen — siehe `_SDF_orchestrate.md` Phase 4.

```yaml
# In _SDF_orchestrate Phase 4 (Batch-Ende)
- Skill(skill="_IDF_berater_modelSync", args="{BL_ID}")        # PL → Model/Spec
- Skill(skill="_PT_promoteFromPL", args="{BL_ID}")             # PL → PT-Kandidaten
- Skill(skill="_SL_promoteFromPL", args="{BL_ID}")             # PL → SemanticLibrary
```

---

## ABGRENZUNG

| Command | Macht was |
|---------|-----------|
| `_IDF_berater_modelSync` | PL → Model/Spec (intra-Projekt) |
| `/_PT_promoteFromPL` (DIESER) | PL → Vault-PT-Kandidaten (cross-projekt Brücke) |
| `_PT_extract --parking-lot-walk` | Vault-PT-Kandidaten → DRAFT-Pattern in Library |
| `_PT_update --from-pl-feedback` | Confidence-Downgrade bei Pattern-Conformance-WARNs |
| `/_Pre_PR_orchestrate` | DRAFT → PROMOTED via Battle-Test |

---

ARGUMENTS: $ARGUMENTS
