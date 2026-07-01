---
status: active
version: 1.0.0
created: 2026-05-01
updated: 2026-05-01
op: ImplementationPipeline
phase: Architect
type: building-block
chain_position: architect-1c-of-7
team_based: false
bl_item: BL-154
ak_ref: AK-2-1
arch_delta_id: ARCH-K1
---

# /_I_architecturalLibrary

```
+======================================================================+
| META-COMMAND: /_I_architecturalLibrary                               |
+======================================================================+
|                                                                      |
| ACTOR: ARCHITEKTUR-PRUEFER                                           |
|        Liest bestehenden Gross-Blueprint (von cleanCodeArchitect),   |
|        prueft ihn gegen ARCH-VERTRAG aus architecturalBrief,        |
|        weist Architektur-Hinweise zu.                                |
|        Analog zu _I_patternLibrary (BL-044) fuer Architektur.       |
|                                                                      |
| PIPELINE-POSITION: Nach _I_patternLibrary (Schritt 1b),             |
|                    vor _I_testSearch (Schritt 2) [BL-154]            |
|                                                                      |
| SRP: Einzig verantwortlich fuer Architektur-Zuweisung im Blueprint  |
|      Definiert KEINE neue Architektur (-> cleanCodeArchitect)        |
|      Bewertet NICHT den Blueprint (-> blueprintQG)                   |
|      Erstellt KEINE Sub-Blueprints (-> cleanCodeSlice)               |
+======================================================================+
```

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_I_architecturalLibrary {NAME} --stufe {N}               ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                            ║
║    1. {VAULT}/_manifest.md                                           ║
║       (Pipeline-State, BERATER_OUTPUTS.architecturalBrief)           ║
║    2. .claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md        ║
║       (Gross-Blueprint von cleanCodeArchitect -- PFLICHT)            ║
║    3. BERATER_OUTPUTS.architecturalBrief.arch_vertrag_block          ║
║       (von _SDF_berater_architecturalBrief vorgeladen — PRIMAER)    ║
║       (inkl. max_search_attempts: 3 — AK-4-5 Stop-Mechanismus)      ║
║                                                                      ║
║  SCHREIBT (Output) - PFLICHT:                                        ║
║    .claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md           ║
║      UPDATE: ## Architektur-Zuweisung Sektion wird befuellt/ersetzt  ║
║    {VAULT}/_manifest.md                                              ║
║      s{N}_arch_zuweisung: done|pending                               ║
║      s{N}_arch_zuweisung_at: "{DATUM}"                               ║
║      s{N}_arch_vertrag_injected: true|false                          ║
║                                                                      ║
║  SCHREIBT NICHT:                                                     ║
║    BERATER_OUTPUTS.architecturalBrief (read-only — _SDF-Hoheit)      ║
║    BERATER_OUTPUTS.patternBrief (separates System, BL-153)           ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    - Aendert NUR ## Architektur-Zuweisung Sektion im Blueprint       ║
║    - Loescht KEINE anderen Blueprint-Sektionen                       ║
║    - NON-BLOCKING: architecturalBrief fehlend oder no_match=true →  ║
║      Graceful Skip (kein Fehler-Abbruch)                            ║
║    - INV-ARCH-K1: Wird NACH _I_patternLibrary ausgefuehrt            ║
║    - INV-ARCH-K1-2: ARCH-VERTRAG-Block MUSS in Blueprint-Abschnitt  ║
║      ## Architektur-Zuweisung eingebettet werden (W21, W22)         ║
║    - ARCH-N9: Wenn Libraries/ direkt benoetigt → VAULT_ROOT via     ║
║      resolve_vault_root.py (.claude/scripts/), NICHT relativ        ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
/_I_architecturalLibrary {NAME} --stufe {N}

Parameter:
  NAME:    Feature-Name (PFLICHT)
  --stufe: Teststufe 1-5 (PFLICHT). Bestimmt welcher Blueprint geladen wird.

Beispiele:
  /_I_architecturalLibrary BL-154 --stufe 1
  /_I_architecturalLibrary MeinFeature --stufe 2
```

---

## Ablauf

### Schritt 0: Vorbedingungen pruefen

```
# architecturalBrief aus SDF vorhanden?
arch_brief = lies BERATER_OUTPUTS.architecturalBrief ?? null

IF arch_brief == null:
  Logge: "[architecturalLibrary] WARN: architecturalBrief nicht vorhanden — Graceful Skip"
  Schreibe s{N}_arch_zuweisung = "skipped_no_brief"
  Schreibe s{N}_arch_zuweisung_at = "{DATUM}"
  → RETURN (kein Fehler)

IF arch_brief.no_match == true:
  Logge: "[architecturalLibrary] architecturalBrief.no_match=true — PatternLibrary leer (EMPTY_SEED)"
  Schreibe s{N}_arch_zuweisung = "skipped_empty_seed"
  Schreibe s{N}_arch_zuweisung_at = "{DATUM}"
  → Weiter mit Schritt 1 (Blueprint mit leerem ARCH-VERTRAG-Block anreichern)
```

### Schritt 1: Blueprint laden

```
1. Lies {WORKING_DIR}/_manifest.md  # per-Story I_PIPELINE_STATE (BL-155 AK-1)
   - Extrahiere s{N}_blueprint_path (falls vorhanden)
2. Falls s{N}_blueprint_path nicht gesetzt:
   - Verwende Default: .claude/analysis/blueprints/{NAME}/S{N}/blueprint.md
3. Lies Blueprint vollstaendig
4. Falls Blueprint nicht vorhanden → FEHLER (Vorbedingung: _I_patternLibrary muss zuerst)
```

### Schritt 2: ARCH-VERTRAG-Block aus architecturalBrief extrahieren

```
# Primaer-Quelle: BERATER_OUTPUTS.architecturalBrief.arch_vertrag_block
arch_vertrag_block = arch_brief.arch_vertrag_block ?? null

IF arch_vertrag_block == null:
  # Fallback: Synthese aus matched_patterns
  matched = arch_brief.matched_patterns ?? []
  IF |matched| == 0:
    arch_vertrag_block = "[ARCH-VERTRAG]\nPatternSet: [] (kein architektonisches Pattern gefunden)\n[/ARCH-VERTRAG]"
  ELSE:
    arch_vertrag_block = (
      "[ARCH-VERTRAG]\n"
      "Layer: {arch_brief.batch_layers}\n"
      "PatternSet:\n"
      + "\n".join(["  - {p.id}: {p.applies_to} (severity={p.severity})" for p in matched])
      + "\n[/ARCH-VERTRAG]"
    )
  Logge: "[architecturalLibrary] arch_vertrag_block aus matched_patterns synthetisiert (kein gespeicherter Block)"

# Stop-Mechanismus pruefen (AK-4-5, W33):
# arch_vertrag_block enthaelt immer max_search_attempts: 3 (gesetzt von _SDF_berater_architecturalBrief)
# — Keine Aktion noetig, nur validieren:
IF "max_search_attempts" NOT IN arch_vertrag_block:
  Logge: "[architecturalLibrary] WARN: max_search_attempts fehlt im ARCH-VERTRAG-Block"
  # NON-BLOCKING: kein Abbruch
```

### Schritt 3: ## Architektur-Zuweisung Sektion im Blueprint erstellen

```markdown
## Architektur-Zuweisung

<!-- Erstellt von _I_architecturalLibrary, {DATUM} -->
<!-- ARCH-VERTRAG-Block: {|matched_patterns|} Patterns geladen -->

### ARCH-VERTRAG-Block (fuer Worker-Prompts)

{arch_vertrag_block}

### Architektur-Pattern-Zusammenfassung

| Pattern-ID | Layer | Severity | Gilt fuer |
|-----------|-------|---------|-----------|
{fuer jedes p in arch_brief.matched_patterns:
  "| {p.id} | {p.layer} | {p.severity} | {p.applies_to} |"}

{falls arch_brief.min_max_summary vorhanden:
### Min/Max-Grenzen

| Pattern-ID | Min-Scope | Max-Scope |
|-----------|-----------|----------|
{fuer jedes e in arch_brief.min_max_summary:
  "| {e.id} | {e.min_scope ?? '-'} | {e.max_scope ?? '-'} |"}
}

{falls arch_brief.broken_patterns vorhanden und nicht leer:
### Broken-Patterns (Achtung: boundary_notes vorhanden)

| Pattern-ID | broken_count | Letzte Notiz |
|-----------|-------------|--------------|
{fuer jedes b in arch_brief.broken_patterns:
  "| {b.id} | {b.broken_count} | {b.boundary_notes[-1] if b.boundary_notes else 'keine'} |"}
}

### Architektur-Abdeckung

- **Patterns gefunden:** {|arch_brief.matched_patterns|}
- **Broken-Patterns:** {|arch_brief.broken_patterns|}
- **no_match:** {arch_brief.no_match}
- **Brief-Summary:** {arch_brief.brief_summary}
```

**Wichtig:** NUR `## Architektur-Zuweisung` Sektion ersetzen/hinzufuegen. Alle anderen Sektionen bleiben unveraendert.

Wenn `## Architektur-Zuweisung` NICHT im Blueprint existiert → am Ende anhaengen.
Wenn sie existiert → Inhalt ersetzen.

---

### Schritt 4: Manifest aktualisieren

```yaml
s{N}_arch_zuweisung: done
s{N}_arch_zuweisung_at: "{YYYY-MM-DD}"
s{N}_arch_vertrag_injected: true
```

---

### Schritt 5: Exit-Report

```
_I_architecturalLibrary {NAME} --stufe {N}: ABGESCHLOSSEN

Architektur-Zuweisung:
  - Patterns gefunden:   {|matched_patterns|}
  - Broken-Patterns:     {|broken_patterns|}
  - ARCH-VERTRAG-Block:  {vorhanden | synthetisiert | leer}
  - no_match:            {arch_brief.no_match}

Blueprint aktualisiert: .claude/analysis/blueprints/{NAME}/S{N}/blueprint.md
Manifest: s{N}_arch_zuweisung = done

Naechster Schritt: /_I_testSearch {NAME} --stufe {N}
```

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| architecturalBrief nicht in Manifest | Skip mit Vermerk s{N}_arch_zuweisung=skipped_no_brief |
| architecturalBrief.no_match=true (EMPTY_SEED) | Skip Zuweisung, aber leeren ARCH-VERTRAG-Block einfuegen |
| Blueprint nicht vorhanden | FEHLER — Vorbedingung nicht erfuellt |
| arch_vertrag_block nicht im Brief | Synthese aus matched_patterns (Fallback) |
| Keine matched_patterns | Leerer ARCH-VERTRAG-Block + Vermerk |

---

## Pipeline-Position

```
[/_I_cleanCodeArchitect]      Schritt 1: Architektur
          |
          v
[/_I_requirementCheck]        Schritt 1a: Requirement Check
          |
          v
[/_I_patternLibrary]          Schritt 1b: Pattern Library (semantisch, BL-153)
          |
          v
[/_I_architecturalLibrary]    Schritt 1c: Architektur-Pruefung  <-- DIESER COMMAND
          |
          v
[/_I_testSearch]              Schritt 2: Test-Suche
          |
          v
[/_I_goldDefine]              Schritt 3: Gold-Definition
          |
          v
[/_I_blueprintQG]             Schritt 4: Quality Gate
```

**Prev:** `/_I_patternLibrary` (Schritt 1b — semantische Pattern-Zuweisung)
**Next:** `/_I_testSearch` (sucht und kategorisiert bestehende Tests)

---

## Referenzen

| Quelle | Bedeutung |
|--------|-----------|
| BL-154 AK-2-1 | architecturalBrief vor patternBrief (k=100) |
| BL-154 PL-27 | ARCH-K1: _I_architecturalLibrary NEU |
| W21, W22 | ARCH-VERTRAG-Block in Worker-Prompts |
| W33, W34 | Stop-Mechanismus max_search_attempts=3 |
| _SDF_berater_architecturalBrief | Primaer-Quelle fuer arch_vertrag_block |
| _I_patternLibrary | Analogon fuer semantische Patterns (BL-153) |

ARGUMENTS: $ARGUMENTS
