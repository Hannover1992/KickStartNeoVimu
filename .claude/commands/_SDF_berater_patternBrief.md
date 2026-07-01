---
doc_type: berater
feature: SemantischePatternLibrary
bl_item: BL-153
ak_ref: AK-B-1
phase: "1.5"
chain_position: "nach modusEntscheidung, vor executionDispatch"
status: active
version: 1.1.0
created: 2026-04-30
updated: 2026-05-10
model_tier: middle  # NEU 2026-05-10: hochgestuft floor (haiku) → middle (sonnet) fuer INV-PL-VAULT-1
---

# _SDF_berater_patternBrief (Phase 1.5)

> **Einschub-Strategie (AK-F-5, INV-EINSCHUB):** Dieser Berater wird nach Phase 1
> (modusEntscheidung C3) und VOR Phase 2 (executionDispatch C9b) ausgeführt.
> Bestehende Schritte werden NICHT verändert.

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_patternBrief (Phase 1.5)                     ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {WORKING_DIR}/_manifest.md → DF_BATCH_STATE.batch_items                ║
║    {VAULT_ROOT}/Libraries/PatternLibrary/_index.md (Pattern-Index)  ║
║    {VAULT_ROOT}/Libraries/PatternLibrary/_project/{LAYER}/*.md      ║
║    {VAULT_ROOT}/Libraries/PatternLibrary/_generic/*.md (IMMER)      ║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/_index.md (ARCH-10)       ║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/_global/*.md (INV-SL-1)   ║
║    {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/*.md     ║
║    VAULT_ROOT via: resolve_vault_root.py (ARCH-N8, Single Source)   ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {WORKING_DIR}/_manifest.md:                                            ║
║      DF_BATCH_STATE.pattern_brief_logged: true                       ║
║      DF_BATCH_STATE.pattern_brief_at: {ISO8601}                      ║
║      DF_BATCH_STATE.pattern_brief.lead_reference: {obj}|null        ║
║    BERATER_OUTPUTS.patternBrief:                                     ║
║      matched_patterns: [{id, title, layer, applies_to}]              ║
║      matched_semantics: [{id, title, layer, applies_to}] (ARCH-10)  ║
║      no_match: true|false (true wenn BEIDE Listen leer)            ║
║      brief_summary: "Freitext, max 3 Sätze"                         ║
║      lead_reference: {source, twin_of|raw_ref} | null               ║
║                                                                      ║
║  SCHREIBT NICHT:                                                     ║
║    DF_BATCH_STATE.modus (nur C3 schreibt das)                       ║
║    andere BERATER_OUTPUTS-Felder                                     ║
║                                                                      ║
║  MODELL-TIER: middle (sonnet) — NEU 2026-05-10 hochgestuft von floor.║
║    Grund: INV-PL-VAULT-1 erfordert subprocess(resolve_vault_root.py) +║
║    BEIDE Libraries (Pattern + Semantic) Path-Resolution + Anti-Pattern║
║    Guard. Haiku scheiterte im DCSRE-486 Run 2026-05-10 (Phase 1.0     ║
║    Schwester architecturalBrief produzierte erfundene Layer-Namen).   ║
║  INVARIANTEN:                                                       ║
║    INV-B1-1: NON-BLOCKING — leere PatternLibrary → Graceful Skip    ║
║    INV-B1-2: pattern_brief_logged=true IMMER gesetzt (auch bei Skip)║
║    INV-B1-3: Schreibt NICHT DF_BATCH_STATE.modus (C3-Hoheit)       ║
║    INV-B1-4: _generic/ MUSS in matched_patterns enthalten wenn Library nicht leer ║
║    INV-SL-1: _global/ MUSS in matched_semantics enthalten wenn          ║
║      SemanticLibrary nicht leer (ARCH-10, analog INV-B1-4)             ║
║    INV-A1-1: Gate-Timestamp (pattern_brief_at) MUSS vor Slice-Start ║
║      liegen (AK-A-1, F-001). Messbar: pattern_brief_at < slice_start║
║      Enforcement in _TDD_orchestrate VOR Schritt 8c GREEN-Spawn.   ║
║      Verletzung = BLOCKER: kein Code-Schreiben ohne gueltigen       ║
║      patternBrief-Timestamp (F-001).                                ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
Skill(_SDF_berater_patternBrief, args="{NAME}")
```

Wird von `_SDF_orchestrate` Phase 1.5 aufgerufen — KEIN direkter User-Aufruf.

---

## Ablauf

### Schritt 0: PatternLibrary + SemanticLibrary verfügbar?

```
# ═══ INV-PL-VAULT-1 (NEU 2026-05-10, User-Direktive): VAULT-ONLY ═══
# BEIDE Libraries (PatternLibrary + SemanticLibrary) leben AUSSCHLIESSLICH im Vault.
# KEINE local copy in {WORKING_DIR}/.claude/patterns/ oder /.claude/semantics/.
# Worker MUSS resolve_vault_root.py aufrufen + Pfade LOGGEN.
# Lokale Verzeichnisse mit Library-Artefakten sind Legacy-Stale → IGNORIEREN.

# Schritt 0.0: VAULT_ROOT verbindlich aufloesen (PFLICHT)
VAULT_ROOT = subprocess.check_output([
  sys.executable,
  ".claude/scripts/resolve_vault_root.py"
], text=True).strip()
Logge: "[patternBrief] VAULT_ROOT={VAULT_ROOT} (resolve_vault_root.py)"

ASSERT VAULT_ROOT != "" AND VAULT_ROOT != WORKING_DIR
  Logge FEHLER bei Bruch: "[patternBrief] FAIL — VAULT_ROOT-Resolution gescheitert"

# SCHRITT 0.0 IDEMPOTENZ-GATE (NEU 2026-05-11, BL-NEW-15 — analog BL-NEW-7 recalibrate)
# Resume-aware: wenn pattern_brief_logged=true und Output cached, RETURN.
# Verhindert ~44k Token-Waste + 22 tool uses pro Resume.
#
# Greift VOR Vault-Library-Reads (teurer Step).

pattern_brief_logged = DF_BATCH_STATE.pattern_brief_logged ?? false
cached_output        = BERATER_OUTPUTS.patternBrief ?? null

IF pattern_brief_logged == true AND cached_output != null AND cached_output != {}:
  Logge: "[patternBrief] IDEMPOTENZ-GATE — pattern_brief_logged=true + cached output present — SKIP_CACHED"
  audit_jsonl_append({type: "PATTERN_BRIEF_SKIP_CACHED", timestamp: ISO,
                       cached_patterns_count: len(cached_output.patterns ?? []),
                       cached_semantics_count: len(cached_output.semantics ?? [])})
  # Output BEIBEHALTEN — kein Ueberschreiben!
  BERATER_OUTPUTS.patternBrief.cache_hit = true
  [patternBrief] EXIT status=SKIP_CACHED
  → RETURN exitcode=0

# FALL-THROUGH: kein Cache-Hit → Vault-Library-Reads + Pattern-Match
Logge: "[patternBrief] IDEMPOTENZ-GATE — no cache present, proceed with Vault-Read + match"

# Schritt 0.1: BEIDE Library-Pfade konstruieren
vault_pl = f"{VAULT_ROOT}/Libraries/PatternLibrary"
vault_sl = f"{VAULT_ROOT}/Libraries/SemanticLibrary"
Logge: "[patternBrief] vault_pl={vault_pl}"
Logge: "[patternBrief] vault_sl={vault_sl}"

# Schritt 0.2: ANTI-PATTERN-Guard — local NICHT lesen
local_pl = f"{WORKING_DIR}/.claude/patterns"
local_sl = f"{WORKING_DIR}/.claude/semantics"
IF exists(local_pl):
  Logge WARNUNG: "[patternBrief] ANTI-PATTERN: local {local_pl} existiert (Legacy-Stale, z.B. _pattern-library.md / _pl-index.md). IGNORIERE — Vault ist canonical."
IF exists(local_sl):
  Logge WARNUNG: "[patternBrief] ANTI-PATTERN: local {local_sl} existiert. IGNORIERE — Vault ist canonical."

# Schritt 0.3: Vault-Existenz pruefen — KEIN graceful Fallback fuer initialisierte Vaults
IF NOT exists(vault_pl):
  Logge FEHLER: "[patternBrief] FAIL — Vault-PatternLibrary fehlt: {vault_pl}. User muss /_PT_arch_init aufrufen."
  RETURN exitcode=2
IF NOT exists(vault_sl):
  Logge WARNUNG: "[patternBrief] Vault-SemanticLibrary fehlt: {vault_sl} — User soll /_SL_init aufrufen. Continue mit nur PatternLibrary."

# Schritt 0.4: EMPTY_SEED-Check NUR auf Vault (kein Fallback auf local)
IF {vault_pl}/_index.md NICHT vorhanden OR leer (EMPTY_SEED):
  Logge: "[patternBrief] PatternLibrary EMPTY_SEED — NON-BLOCKING Skip"
  Schreibe DF_BATCH_STATE.pattern_brief_logged = true
  Schreibe BERATER_OUTPUTS.patternBrief.no_match = true
  Schreibe BERATER_OUTPUTS.patternBrief.brief_summary = "PatternLibrary noch leer (EMPTY_SEED) — kein Pattern-Brief möglich."
  → RETURN (kein Fehler, kein Abbruch)
```

### Schritt 1: Batch-Scope laden (ARCH-34: konkreter Layer-Algorithmus)

```
batch_items = DF_BATCH_STATE.batch_items

# ARCH-34: Konkreter Layer-Algorithmus via Path-Glob statt hand-waving
# Schritt 1a: Betroffene Dateien aus Git-Diff oder batch_items ermitteln
IF batch_items enthält Datei-Pfade:
  betroffene_dateien = batch_items  # Direkteintrag
ELSE:
  betroffene_dateien = git_unstaged_files()  # Fallback: aktueller Diff

# Schritt 1b: Datei-Pfad → Layer via Path-Glob-Mapping
# Reihenfolge: spezifischster Match gewinnt
# Vault-First (ARCH-N7): {vault_root}/config/layers.yaml PRIMAER
vault_root = python3(.claude/scripts/resolve_vault_root.py).stdout.strip()
layers_yaml_path = "{vault_root}/config/layers.yaml"
IF NOT exists(layers_yaml_path):
  layers_yaml_path = ".claude/config/layers.yaml"
layers_config = lies(layers_yaml_path)

LAYER_GLOB_MAP = [(glob, layer.id) FOR layer in layers_config.layers FOR glob in layer.path_globs]
# DCSRE-spezifische BE-* Mapping bleibt nur als Fallback wenn layers.yaml fehlt:
# [("**/Controllers/**","BE-CONT"),("**/Middleware/**","BE-MID"),("**/DTOs/**","BE-DTO"),
#  ("**/Mappings/**","BE-MAP"),("**/Domain/**","BE-DOMAIN"),("**/Migrations/**","BE-MIGRATION"),
#  ("**/Auth/**","BE-AUTH"),("**/*Tests*/**","BE-TEST"),("**/*Test*/**","BE-TEST"),("**/Core/**","BE-CORE")]

layer_set = set()
FÜR jede datei in betroffene_dateien:
  gemappt = false
  FÜR jedes (glob, layer) in LAYER_GLOB_MAP:
    IF datei matches glob:
      layer_set.add(layer)
      gemappt = true
      BREAK   # Erstes Match gewinnt
  IF NOT gemappt:
    layer_set.add("_generic")  # Fallback: global-Pattern wenn kein Layer erkannt

batch_layers = list(layer_set)
Logge: "[patternBrief] Schritt 1 Layer-Mapping: {|betroffene_dateien|} Dateien → {batch_layers} (ARCH-34)"

# ARCH-31 Naming-Klarstellung:
# PatternLibrary Fallback-Layer = "_generic"  (BL-154 Konvention, Ordner: _generic/)
# SemanticLibrary Fallback-Layer = "_global"  (BL-153 Konvention, Ordner: _global/)
# "_generic" in batch_layers bedeutet: PatternLibrary/_generic/ laden
# SemanticLibrary/_global/ wird IMMER geladen (INV-SL-1, Schritt 2.0) — kein Layer-Mapping noetig
```

### Schritt 2.0: Globale Patterns + Semantik laden (IMMER, Default-Basis, ARCH-10)

```
# INV-B1-4: PatternLibrary/_generic/ IMMER laden — unabhängig von batch_layers
global_patterns = lies {VAULT_ROOT}/Libraries/PatternLibrary/_generic/*.md
filter: status != DEPRECATED
Logge: "[patternBrief] Globale Patterns geladen: {|global_patterns|} (INV-B1-4)"

# INV-SL-1: SemanticLibrary/_global/ IMMER laden — analog (ARCH-10)
global_semantics = lies {VAULT_ROOT}/Libraries/SemanticLibrary/_global/*.md
filter: status != DEPRECATED
Logge: "[patternBrief] Globale Semantik geladen: {|global_semantics|} (INV-SL-1)"
```

### Schritt 2.1: Layer-spezifische Patterns + Semantik dazu (kontextuell, ARCH-10)

```
FÜR jeden Layer in batch_layers:
  # PatternLibrary Layer-Patterns
  layer_patterns = lies {VAULT_ROOT}/Libraries/PatternLibrary/_project/{Layer}/README.md
  Sammle Patterns deren applies_to den Layer enthält
  Filter: status != DEPRECATED
  Ergänze: global_patterns + layer_patterns (dedup by id)

  # SemanticLibrary Layer-Semantik (ARCH-10)
  layer_semantics = lies {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{Layer}/*.md
  Sammle Semantics deren applies_to den Layer enthält
  Filter: status != DEPRECATED
  Ergänze: global_semantics + layer_semantics (dedup by id)

# Ergebnis: matched_patterns + matched_semantics (beide dedup)
matched_patterns  = dedup(global_patterns + alle_layer_patterns, key="id")
matched_semantics = dedup(global_semantics + alle_layer_semantics, key="id")
Logge: "[patternBrief] Schritt 2.1 Merge: {|matched_patterns|} Patterns + {|matched_semantics|} Semantics total"
```

### Schritt 3: Brief formulieren (ARCH-10 erweitert)

```
# Top-N Begrenzung pro Liste — REIFE-GETRIEBEN (BL-237 AK-CTX-R3, W-PRE-1 RESOLVED).
# Sort-Primaer = maturity() = usage_count - broken_count (ABGELEITET, pattern_library.py:322-324),
# Cold-Start-Tie-Break = confidence DESC. Single-Sort-Ort (R3); _I_patternLibrary ehrt nur (AK-1, O-4).
#
# Cold-Start-Invariante (O-6, C-K1): solange alle usage_count==0 (heute Regel-Fall, bevor die
# Counter-Feeds aus batch_C3a usage_count von 0 wegbewegen) ist maturity gleich -> der confidence-
# Tie-Break greift -> Reihenfolge BIT-IDENTISCH zum frueheren top_5_by_confidence. Erst echte
# Counter-Daten differenzieren. Vokabular code-konform (W-CNT-7): NUR usage_count/broken_count/maturity().
# _generic/_global IMMER erhalten (INV-B1-4 / INV-SL-1) — der Top-5-Cut filtert sie NIE heraus.
matched_patterns  = pattern_library.rank_by_maturity(matched_patterns,  top_n=5)
matched_semantics = pattern_library.rank_by_maturity(matched_semantics, top_n=5)

# no_match nur wenn BEIDE Listen leer (ARCH-10)
IF |matched_patterns| == 0 AND |matched_semantics| == 0:
  no_match = true
  brief_summary = "Keine passenden Patterns/Semantics für Batch {batch_id} gefunden."
ELSE:
  no_match = false
  brief_summary = "{|matched_patterns|} Pattern(s) + {|matched_semantics|} Semantic(s) für Batch {batch_id}."
```

### Schritt 4: Output schreiben

```
Schreibe {WORKING_DIR}/_manifest.md:
  DF_BATCH_STATE.pattern_brief_logged = true
  DF_BATCH_STATE.pattern_brief_at = {ISO8601}

Schreibe BERATER_OUTPUTS.patternBrief = {
  matched_patterns:  [{id, title, layer, applies_to, confidence}],
  matched_semantics: [{id, title, layer, applies_to, confidence}],   # ARCH-10
  no_match: {bool},
  brief_summary: "{text}"
}

Logge: "[patternBrief] DONE — {|matched_patterns|} Patterns gefunden, no_match={no_match}"
```

### Schritt 5: Twin-Detection (AK-E-4, OQ-3 Resolution, BL-153)

> **OQ-3 Heuristik-Entscheidung (IDF Phase 1, 2026-04-30):**
> Kombinierte Signale: (1) PatternLibrary `twin_of` Frontmatter-Feld (PRIMAER),
> (2) `bezug_zum_twin` aus letztem PATTERN-VERTRAG-Block (SEKUNDAER).
> NON-BLOCKING — kein Twin erkannt → lead_reference=null, kein Fehler.

```
lead_reference = null

# Signal PRIMAER: PatternLibrary-Knoten mit twin_of Frontmatter-Feld
FÜR jedes pattern in matched_patterns:
  IF pattern.frontmatter.twin_of EXISTS AND pattern.frontmatter.twin_of != null:
    lead_reference = {
      source: "pattern_frontmatter",
      pattern_id: pattern.id,
      twin_of: pattern.frontmatter.twin_of
    }
    Logge: "[patternBrief] Twin via Frontmatter: {pattern.id} → twin_of={twin_of}"
    BREAK   # Ersten Fund verwenden

# Signal SEKUNDAER: bezug_zum_twin aus Manifest (letzter PATTERN-VERTRAG-Block)
IF lead_reference == null:
  letzter_vertrag = lies {WORKING_DIR}/_manifest.md → TDD_STATE.pattern_vertrag.bezug_zum_twin ?? null
  IF letzter_vertrag != null
     AND letzter_vertrag NOT STARTS WITH "kein Twin"
     AND letzter_vertrag NOT STARTS WITH "kein relevantes":
    lead_reference = {
      source: "bezug_zum_twin",
      raw_ref: letzter_vertrag
    }
    Logge: "[patternBrief] Twin via bezug_zum_twin: {letzter_vertrag}"

# Output schreiben (explizit auch wenn null)
Schreibe {WORKING_DIR}/_manifest.md:
  DF_BATCH_STATE.pattern_brief.lead_reference = lead_reference

Schreibe BERATER_OUTPUTS.patternBrief.lead_reference = lead_reference

IF lead_reference == null:
  Logge: "[patternBrief] Kein Twin erkannt — lead_reference=null (NON-BLOCKING)"
```

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| PatternLibrary leer (EMPTY_SEED) | Skip + pattern_brief_logged=true (NON-BLOCKING) |
| Layer nicht erkennbar | Alle _generic/ Patterns als Fallback |
| Pattern-Datei nicht lesbar | WARNUNG + überspringen, nicht abbrechen |
| BERATER_OUTPUTS nicht schreibbar | WARNUNG + nur Manifest-Feld setzen |
| Kein Twin erkannt (Schritt 5) | lead_reference=null, NON-BLOCKING, kein Fehler |
| TDD_STATE.pattern_vertrag nicht lesbar | bezug_zum_twin-Signal überspringen, nur Frontmatter-Signal prüfen |
| Leere batch_layers | _generic/ trotzdem geladen (INV-B1-4), layer_patterns leer |
