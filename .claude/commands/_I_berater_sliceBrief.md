---
doc_type: berater
feature: SemantischePatternLibrary
bl_item: BL-153
ak_ref: AK-B-2
phase: "1b"
chain_position: "delegiert von _I_patternLibrary (Schritt 1b), vor _I_cleanCodeSlice"
status: active
version: 1.0.0
created: 2026-04-30
---

# _I_berater_sliceBrief (Schritt 1b Delegate)

> **Einschub-Strategie (AK-F-3, INV-EINSCHUB):** Dieser Berater wird von
> `_I_patternLibrary` delegiert (Thin-Wrapper-Muster, AK-B-4).
> `_I_patternLibrary` bleibt der offizielle Aufrufer in Schritt 1b — kein
> neuer Orchestrator-Schritt nötig.

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _I_berater_sliceBrief (Schritt 1b Delegate)               ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    {WORKING_DIR}/_manifest.md → s{N}_blueprint_path, active_slice    ║
║      (per-Story I_PIPELINE_STATE-Felder, BL-155 AK-1)                ║
║    {WORKING_DIR}/_manifest.md → BERATER_OUTPUTS.patternBrief (Batch-Level Inheritance) ║
║    .claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md           ║
║      (Gross-Blueprint von cleanCodeArchitect)                         ║
║    Libraries/PatternLibrary/_index.md (Pattern-Index)                ║
║    Libraries/PatternLibrary/_generic/*.md (PT-GEN-*)                 ║
║    Libraries/PatternLibrary/_project/{LAYER}/*.md (Layer-Patterns)   ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    BERATER_OUTPUTS.sliceBrief:                                       ║
║      slice_id: {N}                                                   ║
║      matched_patterns: [{id, title, layer, confidence, applies_to}]  ║
║      matched_semantics: [{id, title, layer, applies_to, confidence}] ║
║        (ARCH-28: gleiches Format wie patternBrief, ARCH-20, BL-153) ║
║      pattern_assignments: [{slice, pattern_id, rationale}]           ║
║      no_match: true|false                                            ║
║      brief_summary: "Freitext, max 3 Sätze"                         ║
║                                                                      ║
║  SCHREIBT NICHT:                                                     ║
║    Blueprint-Sektionen direkt (nur _I_patternLibrary schreibt dort) ║
║    andere BERATER_OUTPUTS-Felder                                     ║
║                                                                      ║
║  MODELL-TIER: floor/middle — Index-Lookup + schlankes Reasoning      ║
║  INVARIANTEN:                                                        ║
║    INV-B2-1: NON-BLOCKING — leere Library → Graceful Skip           ║
║    INV-B2-2: Ausgabe BERATER_OUTPUTS.sliceBrief PFLICHT (auch leer) ║
║    INV-B2-3: Kein direktes Blueprint-Schreiben (→ _I_patternLibrary)║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
# Intern von _I_patternLibrary aufgerufen (Thin-Wrapper-Delegation):
Skill(_I_berater_sliceBrief, args="{NAME} --stufe {N}")
```

Kein direkter Orchestrator-Aufruf. `_I_patternLibrary` ist der offizielle Einstiegspunkt.

---

## Ablauf

### Schritt 0: PatternLibrary verfügbar?

```
IF Libraries/PatternLibrary/_index.md NICHT vorhanden OR leer:
  Logge: "[sliceBrief] PatternLibrary leer — Graceful Skip"
  Schreibe BERATER_OUTPUTS.sliceBrief.no_match = true
  Schreibe BERATER_OUTPUTS.sliceBrief.brief_summary = "PatternLibrary EMPTY_SEED — kein Brief möglich."
  → RETURN (NON-BLOCKING)
```

### Schritt 0.5: PatternBrief Inheritance (AK-B-8, BL-153)

> **Einschub-Strategie (INV-EINSCHUB):** NACH Schritt 0 (PatternLibrary-Check),
> VOR Schritt 1 (Blueprint-Kontext laden).
> Liest Batch-Level-Patterns aus patternBrief — verhindert doppelten Vault-Lookup
> für Patterns die bereits auf Batch-Ebene gematchted wurden (AK-B-8: "kein Re-Lookup").

```
pb = lies {WORKING_DIR}/_manifest.md → BERATER_OUTPUTS.patternBrief ?? null

IF pb != null AND pb.no_match == false AND (|pb.matched_patterns| > 0 OR |pb.matched_semantics| > 0):
  inherited_patterns  = pb.matched_patterns ?? []
  inherited_semantics = pb.matched_semantics ?? []   # ARCH-10
  Logge: "[sliceBrief] Inheritance: {|inherited_patterns|} Patterns + {|inherited_semantics|} Semantics aus patternBrief geladen."
  # Schritt 2 Delta-Lookup: nur Slice-spezifische Patterns/Semantics suchen, nicht Batch-Daten neu laden
ELSE:
  inherited_patterns  = []
  inherited_semantics = []
  Logge: "[sliceBrief] Kein patternBrief oder no_match=true → vollständiger Vault-Lookup in Schritt 2"
```

### Schritt 1: Blueprint-Kontext laden

```
blueprint_path = s{N}_blueprint_path aus Manifest
blueprint = lies blueprint_path
slices = extrahiere Slice-Liste aus blueprint "## Slices" Sektion
layer = extrahiere Layer aus Blueprint-Header oder Manifest-Stufe
```

### Schritt 2: Delta-Pattern-Lookup pro Slice (ARCH-19, BL-153)

> **ARCH-19 Fix (INV-EINSCHUB):** Nur DELTA-Suche — Patterns die NICHT in inherited_patterns sind.
> _generic/ wird NICHT neu durchsucht wenn patternBrief sie bereits geladen hat.
> dedup-by-id erzwungen nach Append-Block (verhindert Doppel-Eintraege).

```
inherited_ids = {p.id FOR p IN inherited_patterns}  # Set fuer O(1)-Lookup

FÜR jeden Slice in slices:
  query_terms = [Slice-Titel, Slice-Komponenten-Namen, Layer]
  kandidaten = list(inherited_patterns)  # Kopie der Batch-Level-Patterns

  # Delta-Primär: Layer-spezifische Patterns DIE NOCH NICHT GEERBT
  FÜR jedes Pattern in Libraries/PatternLibrary/_project/{layer}/:
    IF Pattern.id NOT IN inherited_ids AND applies_to enthält Layer AND status != DEPRECATED:
      kandidaten.append(pattern)

  # Delta-Sekundär: Universelle Patterns DIE NOCH NICHT GEERBT
  # SKIP wenn inherited_patterns enthält _generic-Patterns (patternBrief hat INV-B1-4 gemacht)
  IF |inherited_ids| == 0:  # Kein patternBrief → vollständiger Vault-Lookup nötig
    FÜR jedes Pattern in Libraries/PatternLibrary/_generic/:
      IF Pattern.id NOT IN inherited_ids AND (applies_to enthält Layer OR scope == "global"):
        kandidaten.append(pattern)

  # dedup-by-id (ARCH-19: Pflicht nach Append-Block)
  kandidaten = deduplicate_by_id(kandidaten)

  # Auswahl: max 2 pro Slice, höchster confidence
  slice_patterns[Slice] = kandidaten[:2] sortiert nach confidence DESC

Logge: "[sliceBrief] {N} inherited + {M} delta = {N+M} kandidaten (nach dedup)"
```

### Schritt 3: Pattern-Assignments formulieren

```
pattern_assignments = []
FÜR jeden Slice, seine Patterns:
  FÜR jedes Pattern:
    pattern_assignments.append({
      slice: Slice-ID,
      pattern_id: Pattern.id,
      rationale: "1-Satz: warum dieses Pattern für diesen Slice"
    })

matched_patterns  = alle einzigartigen Patterns aus allen Slices
matched_semantics = inherited_semantics  # ARCH-20: propagate Semantics aus patternBrief
no_match = |matched_patterns| == 0
brief_summary = "N Patterns + {|matched_semantics|} Semantics für S{N} ({|slices|} Slices): {top-3 IDs}."
```

### Schritt 4: Output schreiben

```
Schreibe BERATER_OUTPUTS.sliceBrief = {
  slice_id: N,
  matched_patterns: matched_patterns,
  matched_semantics: matched_semantics,  # ARCH-20: Semantics propagated
  pattern_assignments: pattern_assignments,
  no_match: no_match,
  brief_summary: brief_summary
}

Logge: "[sliceBrief] DONE — {|matched_patterns|} Patterns + {|matched_semantics|} Semantics, {|pattern_assignments|} Assignments für S{N}"
```

### Schritt 5: Rückgabe an _I_patternLibrary

```
RETURN sliceBrief-Output
→ _I_patternLibrary schreibt basierend darauf ## Pattern-Zuweisung in Blueprint
→ (MCP-Query als Fallback falls sliceBrief.no_match == true — AK-B-4 Backward-Compat)
```

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| PatternLibrary leer | no_match=true, brief_summary mit Hinweis, NON-BLOCKING |
| Blueprint nicht lesbar | WARNUNG + Fallback auf Layer-Only-Suche |
| Layer nicht erkennbar | Nur _generic/ Patterns verwenden |
| Keine Patterns gefunden | no_match=true, MCP-Fallback in _I_patternLibrary greift |
