---
type: building-block
status: active
version: 1.0.0
created: 2026-05-06
op: PostBatch
phase: 4
type_role: promoter
related: _IDF_berater_modelSync, _SL_init, _SL_conformance, _PT_promoteFromPL
chain_position: post-batch
model_tier: opus
---

# /_SL_promoteFromPL — Per-Story-PL → SemanticLibrary (Vault) Promotion

**Status:** v1.0.0 (initial — Schwester-Command von `_PT_promoteFromPL`)
**Actor:** SEMANTIC-PROMOTER
**Zweck:** Naming-/Vocabulary-relevante PL-Items werden direkt in die SemanticLibrary im Vault promoviert. Zielort je nach Item-Typ: `domain-glossary.md` (globale Begriffe), `naming-conventions.md` (Layer-Naming), `domain-terms.md` (Layer-Vokabular).

> **Architektur:** SemanticLibrary lebt im Vault unter `{VAULT_ROOT}/Libraries/SemanticLibrary/` (cross-projekt, Vault-only — siehe `feedback_libraries_vault_only`).
>
> **Abgrenzung zu `_PT_promoteFromPL`:** PT promoviert ueber Brücke (Vault-PL-Kandidaten + Battle-Test). SL promoviert **direkt** — Naming-Konventionen brauchen keinen Battle-Test, sind deklarativ.

---

## Aufruf

```
/_SL_promoteFromPL {BL-ID} [--dry-run]
```

| Parameter | Pflicht | Default | Beispiel |
|-----------|---------|---------|----------|
| `BL-ID` | JA | — | `BL-151`, `DCSRE-94` |
| `--dry-run` | NEIN | false | Zeigt was promoviert wuerde, schreibt nichts |

---

## VERTRAG

```
+======================================================================+
| VERTRAG: /_SL_promoteFromPL                                          |
+======================================================================+
| LIEST:                                                                |
|   {bl_folder}/6_PL/{bl_id}-parking-lot.md  (per-Story-PL)            |
|   {VAULT_ROOT}/Libraries/SemanticLibrary/_global/domain-glossary.md  |
|   {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/*.md       |
|   .claude/analysis/_manifest.md  (BERATER_OUTPUTS)                   |
|                                                                       |
| SCHREIBT:                                                             |
|   {VAULT_ROOT}/Libraries/SemanticLibrary/_global/domain-glossary.md  |
|     -> APPEND neue globale Begriffe                                   |
|   {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/naming-conventions.md |
|     -> APPEND neue Naming-Regel                                       |
|   {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/domain-terms.md |
|     -> APPEND neue Layer-Begriffe                                     |
|   {bl_folder}/6_PL/{bl_id}-parking-lot.md                            |
|     -> Per-promovierten Item: `synced-to-semantic-library: {DATE}`   |
|   .claude/analysis/_manifest.md                                       |
|     -> BERATER_OUTPUTS.slPromote (siehe Schema)                      |
|   {bl_folder}/2_Model/_slPromote_log_{DATE}.md                       |
|     -> Append-Only Log                                                |
|                                                                       |
| BERATER_OUTPUTS.slPromote:                                            |
|   promoted_glossary_count:    int (neue Domain-Begriffe global)       |
|   promoted_naming_count:      int (neue Naming-Regeln per Layer)      |
|   promoted_terms_count:       int (neue Domain-Terms per Layer)       |
|   skipped_items_count:        int                                     |
|   total_items_evaluated:      int                                     |
|   promoted_items_ids:         list[string]                            |
|   files_written:              list[path]                              |
|   log_path:                   string                                  |
|   exit_code:                  0 OK | 1 WARN (nichts) | 2 ABORT       |
|                                                                       |
| ACTOR: SEMANTIC-PROMOTER                                              |
| MODELL-TIER: opus (Klassifikation Naming vs. Pattern vs. Term)        |
+======================================================================+
```

---

## INVARIANTEN

| INV | Beschreibung |
|-----|-------------|
| INV-SLP-1 | **IDEMPOTENT** — Items mit Marker `synced-to-semantic-library` werden uebersprungen. |
| INV-SLP-2 | **CONSERVATIVE** — nur **stabile + naming-/vocab-relevante** Items promovieren. |
| INV-SLP-3 | **SOURCED** — jeder neue Eintrag in SemanticLibrary hat Source-Reference. |
| INV-SLP-4 | **APPEND-ONLY** — Library-Files werden NUR erweitert. Bestehende Eintraege/Begriffe nie ueberschrieben. |
| INV-SLP-5 | **VAULT-ONLY** — schreibt **ausschliesslich** nach `{VAULT_ROOT}/Libraries/SemanticLibrary/...`. NIEMALS in Repo-lokale Pfade (siehe Memory `project_libraries_vault_only`). |
| INV-SLP-6 | **PFLICHT-LOG** — `_slPromote_log_{DATE}.md` mit Traceability. |
| INV-SLP-7 | **CLASSIFICATION** — pro Item: globaler Begriff (→ glossary) vs. Naming-Regel (→ naming-conventions) vs. Layer-Begriff (→ domain-terms). |
| INV-SLP-8 | **CONFLICT-DETECTION** — wenn neuer Begriff existierendem widerspricht: SKIP + log conflict, manuelle Aufloesung. |
| INV-SLP-9 | **PROMOTION-MUTEX (BL-320)** — vor dem SemanticLibrary-Schreiben (Phase 6 APPEND-ONLY = Lost-Update-Surface, INV-SLP-4) MUSS der gemeinsame Promotion-Lock gehalten werden (`factory_lock.acquire_promotion_lock`). SL teilt sich mit PT EINEN Lock (`bl_id="_pt_promotion"`), damit zwei parallele Batches nie gleichzeitig in dieselbe Library appenden (Read-Modify-Append-Race auf glossary/naming/domain-terms). Stale-Reclaim erbt von `is_bl_stale` (kein Dead-Lock). |

---

## CHAIN-POSITION

```
SDF Phase 3 (modelSync) DONE
     │
     ▼
[/_PT_promoteFromPL {BL-ID}]   (Schwester-Command, parallel)
     │
[/_SL_promoteFromPL {BL-ID}]   ← DIESER COMMAND
     │
     ├──► {VAULT}/Libraries/SemanticLibrary/_global/domain-glossary.md
     ├──► {VAULT}/Libraries/SemanticLibrary/_project/{LAYER}/naming-conventions.md
     └──► {VAULT}/Libraries/SemanticLibrary/_project/{LAYER}/domain-terms.md
     │
     ▼  (Konsumiert direkt — kein Battle-Test)
[/_SL_conformance / /_SL_pre_pr]   pruefen aktualisierte Library
```

---

## ABLAUF

### Phase 1: Pfad-Resolution + Read-All

```python
paths = read_manifest_paths()
bl_folder = paths.bl_folder
vault_root = paths.vault_root  # via resolve_vault_root.py

pl_path        = f"{bl_folder}/6_PL/{bl_id}-parking-lot.md"
glossary_path  = f"{vault_root}/Libraries/SemanticLibrary/_global/domain-glossary.md"
log_path       = f"{bl_folder}/2_Model/_slPromote_log_{DATE}.md"
sl_project_dir = f"{vault_root}/Libraries/SemanticLibrary/_project"

pl_content       = Read(pl_path)
glossary_content = Read(glossary_path)
existing_terms   = parse_glossary_terms(glossary_content)

Logge: f"[slPromote] reading PL: {pl_path}"
Logge: f"[slPromote] reading Glossary: {glossary_path} ({len(existing_terms)} terms)"
```

#### Phase 1b: Promotion-Mutex erwerben (INV-SLP-9, BL-320)

Direkt **nach** der Pfad-Resolution den gemeinsamen Promotion-Lock erwerben — **vor** dem
Read-All, da Phase 6 ein Read-Modify-Append auf glossary/naming/domain-terms ist (Lost-Update-
Surface, INV-SLP-4). PT und SL nutzen denselben Lock (`bl_id="_pt_promotion"`), damit zwei
parallele Batches nie gleichzeitig in dieselbe Vault-Library appenden. Freigabe in Phase 8.

```python
import factory_lock as fl   # Single-Source des Promotion-Mutex (Wrapper ueber BL-Locks)

worker_id = f"sl-promote-{BL_ID}-{os.getpid()}"

# acquire_promotion_lock -> .locks/_pt_promotion.lock; erbt is_bl_stale-Reclaim (AK-3).
# True = exklusiv erworben / False = von anderem Promoter (non-stale, z.B. PT) gehalten.
if not fl.acquire_promotion_lock(worker_id=worker_id, ttl=600, vault_root=vault_root, phase="promote"):
  Logge: "[slPromote] Promotion-Lock von anderem Promoter gehalten — ABORT (exit_code=2) oder spaeter erneut versuchen."
  # exit_code=2 (ABORT) — KEIN Library-Append ohne Lock.
  return

# Convenience-Form (Skill-Seam): with fl.promotion_lock(worker_id=worker_id, vault_root=vault_root):
#     <Phase 2 .. Phase 8>
# acquire @__enter__, release @__exit__ (auch bei Exception).
```

> **🔌 FAN-IN-ANDOCK-PUNKT fuer BL-230 (BL-320 AK-2, AK-MOTOR-WELLE) — NUR DOKU, KEINE BARRIER HIER.**
>
> Der hier in Phase 1b erworbene und in Phase 8 freigegebene Promotion-Lock
> (`factory_lock.acquire_promotion_lock(bl_id="_pt_promotion")`) ist der **dokumentierte
> ANDOCK-PUNKT** fuer die kuenftige **BL-230-Wellen-Fan-In-Barrier**. SL **und** PT
> (`_PT_promoteFromPL`, INV-PTP-9, Phase 1b/8) referenzieren denselben Lock (`_pt_promotion`) —
> daher entsteht **EIN gemeinsamer Andock-Punkt** fuer beide Promoter.
>
> **Migrations-Skizze (sobald die BL-230 Wellen-Barrier existiert):**
> - Die `acquire_promotion_lock` (Phase 1b) / `release_promotion_lock` (Phase 8) Calls wandern
>   **IN die Fan-In-Barrier des Motors**. Die Promotionen serialisieren dann am **kommutativen
>   Fan-In-Punkt der Welle** (single-writer am Barrier-Austritt), statt dass parallele Batch-Worker
>   einzeln um den mkdir-Lock racen — fuer SL besonders relevant, da Phase 6 ein
>   Read-Modify-Append (Lost-Update-Surface, INV-SLP-4) auf glossary/naming/domain-terms ist.
> - Der Lock **bleibt als Korrektheits-Fallback** erhalten (Re-Entrancy / Out-of-Wave-Aufrufe /
>   manuelle Einzel-Promotions), aber der **Normalpfad serialisiert an der Barrier**, nicht mehr am
>   Lock.
>
> **Abgrenzung (WICHTIG):** Dies ist **ausschliesslich** ein dokumentierter Andock-Punkt. **HIER
> wird KEINE Barrier gebaut.** Die Barrier selbst bleibt **BL-230** (`gate_for: BL-230`,
> Wahrheits-Contention-Achse). Siehe BL-320 AK-2 + BL-230. Der bestehende Mutex (INV-SLP-9) bleibt
> unveraendert; dieser Block ergaenzt ihn nur um den Migrationspfad.

### Phase 2: Stabilitaets-Klassifikation

Identische Stabilitaets-Kriterien wie modelSync (INV-MS-2):

```python
items = parse_pl(pl_content)
candidates = []

for item in items:
  if item.has_marker("synced-to-semantic-library"):
    log_skip(item.id, "already synced to SemanticLibrary")
    continue

  stable = is_stable(item)  # status:done OR audit OR principle OR user-final
  if stable:
    candidates.append(item)
  else:
    log_skip(item.id, "not stable")

Logge: f"[slPromote] {len(candidates)} stable candidates"
```

### Phase 3: Naming-/Vocabulary-Wuerdigkeit (3-Wege-Klassifikation)

```python
class Classification(Enum):
  GLOSSARY  = "global term for domain-glossary"
  NAMING    = "naming convention for naming-conventions per layer"
  TERMS     = "layer-specific term for domain-terms per layer"
  NONE      = "not naming/vocab relevant"

def classify(item) -> Classification:
  text = item.text.lower()

  # Global: Domain-Begriffe die projekt-uebergreifend gelten
  if any(kw in text for kw in ["fachbegriff", "domain-term", "ubiquitous language",
                                  "abkürzung", "akronym", "qdvs", "qdvtp"]):
    return Classification.GLOSSARY

  # Naming-Regel: "soll/muss/darf/heißt"-Aussagen ueber Bezeichner
  if any(kw in text for kw in ["naming", "benennen", "bezeichner", "konvention",
                                  "umlaut", "kebab-case", "pascalcase", "präfix",
                                  "prefix", "suffix"]):
    return Classification.NAMING

  # Layer-Term: spezifischer Begriff in einem Layer
  if any(kw in text for kw in ["controller", "service", "validator", "dto", "entity",
                                  "profile", "middleware", "migration"]):
    return Classification.TERMS

  return Classification.NONE


classified = []
for item in candidates:
  cls = classify(item)
  if cls == Classification.NONE:
    log_skip(item.id, "not naming/vocab relevant")
    continue
  classified.append((item, cls))

Logge: f"[slPromote] {len(classified)} classified for SL promotion"
```

### Phase 4: Layer-Heuristik (fuer NAMING + TERMS)

```python
def derive_layer(item) -> str:
  # Identisch zu _PT_promoteFromPL
  text = item.text
  if "Controller" in text:    return "BE-CONT"
  if "Service" in text:       return "BE-CORE"
  if ".Domain" in text:       return "BE-DOMAIN"
  if "Dto" in text:           return "BE-DTO"
  if "Profile" in text:       return "BE-MAP"
  if "Middleware" in text:    return "BE-MID"
  if "Auth" in text:          return "BE-AUTH"
  if "Migration" in text:     return "BE-MIGRATION"
  if "Test" in text:          return "BE-TEST"
  return "_global"  # Fallback fuer GLOSSARY
```

### Phase 5: Conflict-Detection (INV-SLP-8)

```python
def find_conflict(new_term: str, existing: list[str]) -> str | None:
  # Exakte Duplikate: SKIP idempotent
  # Aehnliche Begriffe (gleicher Stamm, andere Bedeutung): CONFLICT
  for term in existing:
    if normalize(new_term) == normalize(term): return None  # exact dup → silent skip
    if has_similar_root(new_term, term) and different_meaning(new_term, term):
      return term
  return None


conflicts = []
final = []
for item, cls in classified:
  new_text = synthesize_entry(item, cls)
  conflict = find_conflict(new_text, existing_terms_for_cls(cls))
  if conflict:
    conflicts.append((item, conflict))
    log_skip(item.id, f"conflicts with: {conflict}")
    continue
  final.append((item, cls, new_text))
```

### Phase 6: Promote (3 Sub-Pfade)

```python
glossary_entries = []
naming_entries_per_layer = defaultdict(list)
terms_entries_per_layer = defaultdict(list)

for item, cls, entry in final:
  if cls == Classification.GLOSSARY:
    glossary_entries.append((entry, item))
  elif cls == Classification.NAMING:
    layer = derive_layer(item)
    naming_entries_per_layer[layer].append((entry, item))
  elif cls == Classification.TERMS:
    layer = derive_layer(item)
    terms_entries_per_layer[layer].append((entry, item))

# Sub-Pfad A: Glossary append
if glossary_entries:
  Append(glossary_path, build_glossary_section(glossary_entries, BL_ID, DATE))

# Sub-Pfad B: Naming-Conventions per Layer
for layer, entries in naming_entries_per_layer.items():
  naming_path = f"{sl_project_dir}/{layer}/naming-conventions.md"
  ensure_exists(naming_path)
  Append(naming_path, build_naming_section(entries, BL_ID, DATE))

# Sub-Pfad C: Domain-Terms per Layer
for layer, entries in terms_entries_per_layer.items():
  terms_path = f"{sl_project_dir}/{layer}/domain-terms.md"
  ensure_exists(terms_path)
  Append(terms_path, build_terms_section(entries, BL_ID, DATE))

files_written = collect_paths(...)
Logge: f"[slPromote] wrote to {len(files_written)} library files"
```

**Eintrags-Format pro Sub-Pfad:**

```markdown
<!-- Sub-Pfad A: domain-glossary.md APPEND -->
## {DATE} — Aus {BL_ID}

### {Begriff}
**Definition:** {definition aus PL-Item}
**Source:** BL-{ID}-{PL-ITEM-ID}
**Aliases:** {falls vorhanden}


<!-- Sub-Pfad B: naming-conventions.md APPEND -->
## {DATE} — Aus {BL_ID}

### Regel: {Titel}
- **Severity:** BLOCKER | WARNUNG | INFO
- **Beschreibung:** {regel-text}
- **Beispiel VORHER:** `{wrong}`
- **Beispiel NACHHER:** `{right}`
- **Source:** BL-{ID}-{PL-ITEM-ID}


<!-- Sub-Pfad C: domain-terms.md APPEND -->
## {DATE} — Aus {BL_ID}

### {Term} ({LAYER})
**Bedeutung:** {bedeutung}
**Verwendung:** {wo es vorkommt}
**Source:** BL-{ID}-{PL-ITEM-ID}
```

### Phase 7: Source-Items markieren (INV-SLP-1)

```python
for (item, _, _) in final:
  Update_in_file(pl_path, item.id, add_marker=f"synced-to-semantic-library: {DATE}")
```

### Phase 8: Log + Output

```python
Write(log_path, build_log(final, conflicts, skipped))

manifest_update("BERATER_OUTPUTS.slPromote", {
  promoted_glossary_count: len(glossary_entries),
  promoted_naming_count: sum(len(v) for v in naming_entries_per_layer.values()),
  promoted_terms_count: sum(len(v) for v in terms_entries_per_layer.values()),
  skipped_items_count: len(items) - len(final) - len(conflicts),
  total_items_evaluated: len(items),
  promoted_items_ids: [item.id for (item, _, _) in final],
  files_written: files_written,
  conflicts: [{item: i.id, with: c} for (i, c) in conflicts],
  log_path: log_path,
  exit_code: 0 if final else 1,
})

Logge: f"[slPromote] DONE — glossary:{N1}, naming:{N2}, terms:{N3}, conflicts:{C}"

# Promotion-Mutex freigeben (INV-SLP-9, BL-320) — NACH Log+Output.
fl.release_promotion_lock(worker_id=worker_id, vault_root=vault_root)
Logge: "[slPromote] Promotion-Lock freigegeben."
```

---

## QUICK-START

```bash
# Standard-Aufruf (Sister von _PT_promoteFromPL)
/_SL_promoteFromPL DCSRE-94

# Dry-Run
/_SL_promoteFromPL DCSRE-94 --dry-run
```

---

## INTEGRATION (SDF Phase 4)

```yaml
# In _SDF_orchestrate Phase 4 (Batch-Ende, nach modelSync)
- Skill(skill="_IDF_berater_modelSync", args="{BL_ID}")        # PL → Model/Spec
- Skill(skill="_PT_promoteFromPL",     args="{BL_ID}")          # PL → PT-Kandidaten
- Skill(skill="_SL_promoteFromPL",     args="{BL_ID}")          # PL → SemanticLibrary  ← DIESER
```

---

## ABGRENZUNG

| Command | Was es macht |
|---------|--------------|
| `_SL_init` | Bootstrap der SemanticLibrary (einmalig, Code-Scan) |
| `/_SL_promoteFromPL` (DIESER) | Inkrementelles Wachstum aus PL-Erkenntnissen |
| `_SL_conformance` | Pruefung unstaged Branch-Aenderungen vs. SL |
| `_SL_pre_pr` | Branch-Total-Pruefung vor PR |

---

ARGUMENTS: $ARGUMENTS
