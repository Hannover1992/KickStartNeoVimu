---
doc_type: berater
feature: ArchitektonischePatternLibrary
bl_item: BL-154
ak_ref: AK-2-1
phase: "1.0"
chain_position: "VOR C9b (_SDF_PreBerater_orchestrate), VOR modusEntscheidung"
status: active
version: 1.1.0
created: 2026-05-01
updated: 2026-05-10
model_tier: middle  # NEU 2026-05-10: hochgestuft von floor (haiku) → middle (sonnet)
                    # Begruendung: INV-PL-VAULT-1 + INV-LAYER-DISCOVERY-1 erfordern
                    # Python-subprocess + ls + ASSERT + Whitelist-Validation + Auto-Map.
                    # Haiku hat im DCSRE-486 Live-Run 2026-05-10 den Patch nicht
                    # ausgefuehrt (keine INV-LAYER-Logs, keine Vault-Whitelist gelesen).
---

# _SDF_berater_architecturalBrief (Phase 1.0)

> **Einschub-Strategie (W30, ADR-1, INV-EINSCHUB):** Dieser Berater wird VOR C9b
> (_SDF_PreBerater_orchestrate) in den SDF-orchestrate Batch-Loop eingehängt.
> C9b, patternBrief (Phase 1.5) und alle bestehenden Schritte bleiben UNVERÄNDERT.
> architecturalBrief liegt WEITER AUSSEN (W9, ADR-3: Architekten-Primat).

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_berater_architecturalBrief (Phase 1.0)               ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {WORKING_DIR}/_manifest.md → DF_BATCH_STATE.batch_items                ║
║    {VAULT_ROOT}/Libraries/PatternLibrary/_index.md (Pattern-Index)  ║
║    {VAULT_ROOT}/Libraries/PatternLibrary/_project/BE-{LAYER}/_index.md║
║    {VAULT_ROOT}/Libraries/PatternLibrary/_project/BE-{LAYER}/*.md   ║
║    VAULT_ROOT via: resolve_vault_root.py (ARCH-N8, Single Source)   ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    {WORKING_DIR}/_manifest.md:                                             ║
║      DF_BATCH_STATE.architectural_brief_logged: true                 ║
║      DF_BATCH_STATE.architectural_brief_at: {ISO8601}                ║
║    BERATER_OUTPUTS.architecturalBrief:                               ║
║      batch_layers: [{layer_id}]                                      ║
║      matched_patterns: [{id, title, layer, applies_to, severity}]   ║
║      anti_patterns: [{id, description}]                              ║
║      min_max_summary: [{id, min_scope, max_scope}]                   ║
║      broken_patterns: [{id, broken_count, boundary_notes}]           ║
║      no_match: true|false                                            ║
║      brief_summary: "Freitext, max 3 Sätze"                         ║
║      arch_vertrag_block: "String — ARCH-VERTRAG-Block fuer Worker"  ║
║        (inkl. max_search_attempts: 3 — AK-4-5 Stop-Mechanismus)     ║
║                                                                      ║
║  SCHREIBT NICHT:                                                     ║
║    DF_BATCH_STATE.modus (nur C3 schreibt das)                       ║
║    BERATER_OUTPUTS.patternBrief (BL-153, separates System)          ║
║                                                                      ║
║  MODELL-TIER: middle (sonnet) — NEU 2026-05-10 hochgestuft von floor.║
║    Grund: INV-PL-VAULT-1 + INV-LAYER-DISCOVERY-1 erfordern               ║
║    subprocess(resolve_vault_root.py) + ls(_project/) + ASSERT-Validation║
║    + Auto-Map-Aliases + Whitelist-Check. Haiku konnte das im DCSRE-486   ║
║    Run 2026-05-10 nicht ausfuehren (Drift-Halluzination "BE-VALIDATION", ║
║    "BE-CONTROLLER" statt echte Vault-Layer "BE-CONT", "BE-MAP").         ║
║  INVARIANTEN:                                                        ║
║    INV-ARCH-1: NON-BLOCKING — EMPTY_SEED/leerer Vault → Graceful    ║
║      Skip. architectural_brief_logged=true IMMER gesetzt.            ║
║    INV-ARCH-2: architectural_brief_at IMMER gesetzt (auch bei Skip) ║
║    INV-ARCH-3: Schreibt NICHT DF_BATCH_STATE.modus (C3-Hoheit)      ║
║    INV-ARCH-4: Kein _global/ Ordner (W5: Patterns immer Layer-spez.)║
║    INV-ARCH-5: architecturalBrief_at < pattern_brief_at (W43, AK-2-1║
║      Verifikationskriterium V4)                                      ║
║    INV-PL-VAULT-1 (2026-05-10): VAULT-ONLY. Worker MUSS              ║
║      resolve_vault_root.py aufrufen + Pfad loggen. KEIN Fallback     ║
║      auf {WORKING_DIR}/.claude/patterns/ (Anti-Pattern, Legacy-Stale).║
║      Pattern Libraries leben AUSSCHLIESSLICH im Vault als            ║
║      projekt-weit-shared Single-Source-of-Truth (User-Direktive      ║
║      2026-05-10: "wachsen wie Models ueber Zeit").                  ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
Skill(_SDF_berater_architecturalBrief, args="{NAME}")
```

Wird von `_SDF_orchestrate` Phase 1.0 aufgerufen — VOR C9b.
KEIN direkter User-Aufruf. KEIN Aufruf aus C9b oder patternBrief heraus.

---

## Ablauf

### Schritt 0: PatternLibrary verfügbar? (INV-ARCH-1)

```
# ═══ INV-PL-VAULT-1 (NEU 2026-05-10, User-Direktive): VAULT-ONLY ═══
# Pattern Libraries leben AUSSCHLIESSLICH im Vault. KEINE local copy in
# {WORKING_DIR}/.claude/patterns/ — auch wenn das Verzeichnis existiert
# (Legacy-Stale, ggf. aus alten Runs). Worker MUSS resolve_vault_root.py
# aufrufen + Pfad LOGGEN. Lokales `.claude/patterns/` ist VERBOTEN als
# Quelle (siehe ANTI-PATTERN unten).

# Schritt 0.0: VAULT_ROOT verbindlich aufloesen (PFLICHT)
VAULT_ROOT = subprocess.check_output([
  sys.executable,
  ".claude/scripts/resolve_vault_root.py"
], text=True).strip()
Logge: "[architecturalBrief] VAULT_ROOT={VAULT_ROOT} (resolve_vault_root.py)"

ASSERT VAULT_ROOT != "" AND VAULT_ROOT != WORKING_DIR
  Logge FEHLER bei Bruch: "[architecturalBrief] FAIL — VAULT_ROOT-Resolution gescheitert"

# Schritt 0.1: Vault-Pfad konstruieren
vault_pl = f"{VAULT_ROOT}/Libraries/PatternLibrary"
Logge: "[architecturalBrief] vault_pl={vault_pl}"

# Schritt 0.2: ANTI-PATTERN-Guard — local patterns/ NICHT lesen
local_pl = f"{WORKING_DIR}/.claude/patterns"
IF exists(local_pl):
  Logge WARNUNG: "[architecturalBrief] ANTI-PATTERN: local {local_pl} existiert (Legacy-Stale). IGNORIERE — Vault ist canonical."
  # KEIN read von local_pl — auch wenn _pattern-library.md / _pl-index.md
  # darin existiert. Diese sind veraltete Artefakte vor INV-PL-VAULT-1.

# Schritt 0.3: EMPTY_SEED-Check NUR auf vault_pl (kein Fallback)
IF NOT exists(vault_pl):
  Logge FEHLER: "[architecturalBrief] FAIL — Vault-PatternLibrary fehlt: {vault_pl}. User muss /_PT_arch_init aufrufen."
  RETURN exitcode=2  # NICHT graceful skip — Vault-Vorhandensein ist PFLICHT

IF vault_pl/_index.md NICHT vorhanden OR leer (EMPTY_SEED):
  Logge: "[architecturalBrief] PatternLibrary leer/nicht vorhanden — NON-BLOCKING Skip"
  Schreibe DF_BATCH_STATE.architectural_brief_logged = true
  Schreibe DF_BATCH_STATE.architectural_brief_at = {ISO8601 jetzt}
  Schreibe BERATER_OUTPUTS.architecturalBrief = {
    batch_layers: [],
    matched_patterns: [],
    anti_patterns: [],
    min_max_summary: [],
    broken_patterns: [],
    no_match: true,
    brief_summary: "PatternLibrary leer (EMPTY_SEED) — kein architecturalBrief möglich."
  }
  → RETURN (kein Fehler, kein Abbruch)
```

### Schritt 1: Batch-Layers aus DF_BATCH_STATE (W42)

```
# ═══ INV-LAYER-DISCOVERY-1 (NEU 2026-05-10): VAULT-WHITELIST PFLICHT ═══
# DCSRE-486 Live-Bug 2026-05-10: Worker erfand Layer-Namen ("BE-VALIDATION",
# "BE-MAPPING", "BE-CONTROLLER", "BE-SERVICE") statt aus Vault zu lesen.
# Folge: nur 3 von 96 Patterns gefunden (97% Verlust).
# Loesung: Vault ist authoritative — Layer-Namen MUESSEN aus _project/ kommen.

# Schritt 1.0: VAULT-Layer-Whitelist (AUTHORITATIVE — Single-Source)
vault_layers = sorted([d for d in listdir(vault_pl/_project/) if d.startswith("BE-")])
Logge: "[architecturalBrief] vault_layers (whitelist)={vault_layers}"
ASSERT len(vault_layers) >= 1
  Bei Bruch: FAIL — PatternLibrary _project/ leer
# Erwartung DCSRE: [BE-AUTH, BE-CONT, BE-CORE, BE-DOMAIN, BE-DTO, BE-MAP,
#                   BE-MID, BE-MIGRATION, BE-TEST] — 9 Layer

# ANTI-PATTERN — Worker DARF NICHT:
#   ❌ Layer-Namen erfinden ("BE-VALIDATION", "BE-MAPPING", "BE-CONTROLLER",
#      "BE-SERVICE" sind nicht in Vault — VERBOTEN)
#   ❌ Verbose-Namen statt 3-Letter-Suffix verwenden
#      ("BE-MAPPING" statt "BE-MAP", "BE-CONTROLLER" statt "BE-CONT")
#   ❌ Fallback auf vermutete Layer ohne Vault-Read

# Schritt 1.1: layer_hint pro AK lesen + gegen Whitelist validieren
batch_items = DF_BATCH_STATE.batch_items
batch_layers = []
unknown_hints = []

FOR ak_id IN batch_items:
  ak_data = BERATER_OUTPUTS.akExtraktion.aks.get(ak_id)
  layer_hint = ak_data.layer_hint IF ak_data else null

  IF layer_hint == null:
    Logge: "[architecturalBrief] WARN: AK={ak_id} hat kein layer_hint"
    CONTINUE

  # Validation gegen Vault-Whitelist
  IF layer_hint IN vault_layers:
    IF layer_hint NOT IN batch_layers:
      batch_layers.append(layer_hint)
  ELSE:
    # Auto-Map bekannte Drift-Aliases
    aliases = {
      "BE-VALIDATION":  "BE-CORE",   # FluentValidation lebt in BE-CORE/PT-CORE-009
      "BE-MAPPING":     "BE-MAP",    # 3-Letter-Suffix-Konvention
      "BE-CONTROLLER":  "BE-CONT",
      "BE-SERVICE":     "BE-CORE",   # Application Services = BE-CORE
      "BE-MID-WARE":    "BE-MID",
      "BE-MIDDLEWARE":  "BE-MID",
    }
    mapped = aliases.get(layer_hint)
    IF mapped AND mapped IN vault_layers:
      Logge: "[architecturalBrief] WARN: layer_hint={layer_hint} (AK={ak_id}) → auto-mapped to {mapped} (Vault-Whitelist)"
      IF mapped NOT IN batch_layers:
        batch_layers.append(mapped)
    ELSE:
      unknown_hints.append((ak_id, layer_hint))
      Logge: "[architecturalBrief] FEHLER: layer_hint={layer_hint} (AK={ak_id}) NICHT in Vault-Whitelist {vault_layers}. IGNORE."

# Schritt 1.2: Fallback bei leerer batch_layers — IMMER aus Vault, nie erfunden
IF batch_layers leer:
  batch_layers = vault_layers   # ALLE Vault-Layer als Fallback
  Logge: "[architecturalBrief] Kein gueltiger layer_hint in batch_items — Fallback: alle {len(vault_layers)} Vault-Layer"

# Schritt 1.3: Final Sanity-Check (KEIN Erfinden moeglich)
FOR layer IN batch_layers:
  ASSERT layer IN vault_layers
    Bei Bruch: FAIL — Layer {layer} nicht in Whitelist (sollte nie passieren nach 1.1+1.2)

Logge: "[architecturalBrief] Schritt 1: batch_layers={batch_layers} (validiert gegen Vault-Whitelist {len(vault_layers)} Layer)"
IF unknown_hints:
  Logge: "[architecturalBrief] WARN: {len(unknown_hints)} unbekannte layer_hints geignored: {unknown_hints}"
```

### Schritt 2: Layer-spezifische Patterns laden (Stop-Mechanismus, BL-154-PL-31, AK-4-5)

> **Stop-Mechanismus (W33, W34, PL-31):** Max `max_search_attempts = 3` Lookup-Versuche
> pro Layer. Nach 3 erfolglosen Versuchen → STOP + Plateau-Detection-Signal.
> Verhindert Endlos-Loop bei fehlenden oder nicht-matchenden Patterns.

```
matched_patterns = []
anti_patterns    = []
min_max_summary  = []
broken_patterns  = []

# Stop-Mechanismus: Versuchs-Zaehler pro Layer (AK-4-5, W33, PL-31)
max_search_attempts = 3  # Konstante — darf nicht per Caller-Override gesenkt werden

FÜR jeden layer IN batch_layers:
  layer_path = vault_pl/_project/{layer}/
  layer_attempts = 0  # Zaehler fuer diesen Layer

  IF layer_path NICHT vorhanden:
    Logge: "[architecturalBrief] Layer {layer} hat keinen Ordner — SKIP"
    CONTINUE

  # Layer-Patterns laden
  layer_patterns = lies alle *.md in layer_path
  filter: frontmatter.status != "DEPRECATED"

  # Plateau-Detection: Falls keine Patterns vorhanden → sofort zaehlen
  IF |layer_patterns| == 0:
    layer_attempts += 1
    IF layer_attempts >= max_search_attempts:
      Logge: "[architecturalBrief] STOP (PL-31): {max_search_attempts} Versuche erschoepft fuer Layer {layer} — kein Pattern gefunden (Plateau)"
      CONTINUE  # Naechster Layer, kein weiterer Versuch
    CONTINUE

  FÜR jedes pattern IN layer_patterns:
    layer_attempts += 1
    IF layer_attempts > max_search_attempts:
      Logge: "[architecturalBrief] STOP (PL-31): max_search_attempts={max_search_attempts} erreicht fuer Layer {layer} — Verarbeitung gestoppt"
      BREAK  # Inner-Loop stoppen, naechster Layer
    # Aktive Patterns sammeln
    matched_patterns.append({
      id: pattern.id,
      title: pattern.title ?? pattern.id,
      layer: layer,
      applies_to: pattern.applies_to ?? "",
      severity: pattern.severity ?? "RECOMMENDED"
    })

    # Min/Max-Grenzen (W15)
    IF pattern.min_scope OR pattern.max_scope:
      min_max_summary.append({
        id: pattern.id,
        min_scope: pattern.min_scope ?? null,
        max_scope: pattern.max_scope ?? null
      })

    # Broken-Patterns (boundary_notes, W13)
    IF pattern.broken_count >= 1:
      broken_patterns.append({
        id: pattern.id,
        broken_count: pattern.broken_count,
        boundary_notes: pattern.boundary_notes ?? []
      })

Logge: "[architecturalBrief] Schritt 2: {|matched_patterns|} Patterns aus {|batch_layers|} Layern"
```

### Schritt 3: Brief formulieren

```
# Top-N Begrenzung (max 5 pro Layer, höchster usage_count zuerst)
matched_patterns = top_N_per_layer(matched_patterns, n=5, key="usage_count")

IF |matched_patterns| == 0:
  no_match = true
  brief_summary = "Keine architektonischen Patterns für Layer {batch_layers} gefunden."
ELSE:
  no_match = false
  brief_summary = (
    "{|matched_patterns|} Pattern(s) für Layer {batch_layers}. "
    "ARCH-VERTRAG-Block: PatternSet={[p.id for p in matched_patterns]}, "
    "BrokenPatterns={[p.id for p in broken_patterns]}."
  )
```

### Schritt 3a: ARCH-VERTRAG-Block Template generieren (AK-2-4, W21, W22)

> **BL-154 AK-4-5 Stop-Mechanismus (W33):** ARCH-VERTRAG-Block enthaelt IMMER
> `max_search_attempts: 3`. Worker liest diesen Wert und stoppt nach 3 erfolglosen
> Lookup-Versuchen via `/_PT_update --arch-lifecycle pfad-5`.

```
# ARCH-VERTRAG-Block fuer Worker-Prompt (W21, W22, AK-2-4)
# PFLICHT: ERSTE Section im Worker-Prompt (vor SEM-VERTRAG-Block)
# Kein leerer Block erlaubt wenn no_match=false (W21: "kein leerer Block ohne Begruendung")

IF no_match == false:
  arch_vertrag_block = """
[ARCH-VERTRAG]
Layer: {batch_layers[0] if len(batch_layers)==1 else batch_layers}
PatternSet:
{fuer jedes pattern in matched_patterns: "  - {pattern.id}: {pattern.applies_to} (severity={pattern.severity})"}
MinMax:
{fuer jedes eintrag in min_max_summary: "  - {eintrag.id}: min={eintrag.min_scope}, max={eintrag.max_scope}"}
BrokenPatterns:
{fuer jedes broken in broken_patterns: "  - {broken.id}: broken_count={broken.broken_count}, letzte_notiz={broken.boundary_notes[-1] if broken.boundary_notes else 'keine'}"}
StopMechanismus:
  max_search_attempts: 3
  bei_3_attempts_stop: "/_PT_update --arch-lifecycle pfad-5 --layer {layer} --context '{kontext}'"
  ergebnis_pfad5: no_pattern_found=true → pattern-usage.log + Parking-Lot Notiz
[/ARCH-VERTRAG]
"""
ELSE:  # no_match=true → leere Library
  arch_vertrag_block = """
[ARCH-VERTRAG]
Layer: {batch_layers}
PatternSet: [] (EMPTY_SEED — keine architektonischen Patterns vorhanden)
MinMax: []
BrokenPatterns: []
StopMechanismus:
  max_search_attempts: 3
  note: "PatternLibrary leer — kein Lookup moeglich. Neue Patterns via Pfad-4 anlegen."
[/ARCH-VERTRAG]
"""

# BERATER_OUTPUTS erweiterung: arch_vertrag_block als String fuer Worker-Prompt
Schreibe BERATER_OUTPUTS.architecturalBrief.arch_vertrag_block = arch_vertrag_block
```

### Schritt 4: Output schreiben

```
# Manifest
Schreibe {WORKING_DIR}/_manifest.md:
  DF_BATCH_STATE.architectural_brief_logged = true
  DF_BATCH_STATE.architectural_brief_at = {ISO8601 jetzt}  # INV-ARCH-2

# BERATER_OUTPUTS
Schreibe BERATER_OUTPUTS.architecturalBrief = {
  batch_layers:       batch_layers,
  matched_patterns:   matched_patterns,
  anti_patterns:      anti_patterns,
  min_max_summary:    min_max_summary,
  broken_patterns:    broken_patterns,
  no_match:           no_match,
  brief_summary:      brief_summary,
  arch_vertrag_block: arch_vertrag_block  # NEU (AK-4-5, AK-2-4) — inkl. max_search_attempts: 3
}

Logge: "[architecturalBrief] DONE — {|matched_patterns|} Patterns, no_match={no_match}, vertrag_block={len(arch_vertrag_block)} Zeichen"
```

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| PatternLibrary leer (EMPTY_SEED) | Skip + architectural_brief_logged=true (INV-ARCH-1) |
| Layer nicht erkennbar aus batch_items | Alle BE-Layer als Fallback (alle _project/ Ordner) |
| Layer-Ordner fehlt in _project/ | SKIP Layer + Warnung, kein Abbruch |
| Pattern-Datei nicht lesbar | WARNUNG + überspringen |
| BERATER_OUTPUTS nicht schreibbar | WARNUNG + nur Manifest-Feld setzen |

---

## Verifikations-Kriterium (AK-2-1, V4)

Nach Implementation in `_SDF_orchestrate`:
- `BERATER_OUTPUTS.architecturalBrief` im Manifest vorhanden
- `DF_BATCH_STATE.architectural_brief_at` < `DF_BATCH_STATE.pattern_brief_at`
- Bei EMPTY_SEED: `no_match=true`, kein Fehler, Pipeline läuft weiter

---

## Referenzen

| Quelle | Bedeutung |
|--------|-----------|
| W6 | 3-Phasen-Mantra: architecturalBrief ZUERST |
| W7 | Dieser Berater als Thin-Wrapper (analog patternBrief) |
| W9/W43 | Phase 1.0 VOR C9b — Architekten-Primat |
| W30 | Einschub-Strategie: SDF-orchestrate inline |
| W35 | Thin-Wrapper-Pattern für neue Berater |
| W42 | scope-Detection via batch_layers aus PL-Frontmatter |
| AK-2-1 | architecturalBrief vor patternBrief (k=100) |
| AK-2-3 | Leer-Robustheit bei EMPTY_SEED |
| _SDF_berater_patternBrief.md | Analogon (Phase 1.5, BL-153) |
