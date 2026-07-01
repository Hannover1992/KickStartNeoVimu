---
status: active
version: 1.1.0
created: 2026-03-06
updated: 2026-04-06
op: PatternLibrary
phase: Architect
type: building-block
chain_position: architect-1b-of-7
team_based: false
---

# /_I_patternLibrary

```
+======================================================================+
| META-COMMAND: /_I_patternLibrary                                 |
+======================================================================+
|                                                                        |
| ACTOR: PATTERN-ZUWEISER                                               |
|        Liest bestehenden Gross-Blueprint (von cleanCodeArchitect),    |
|        durchsucht Pattern Library, weist Patterns zu.                 |
|        Erstellt KEINEN neuen Blueprint -- ergaenzt bestehenden.       |
|                                                                        |
| PIPELINE-POSITION: Nach _I_requirementCheck (Schritt 1a),            |
|                    vor _I_testSearch (Schritt 2)     [BL-044]         |
|                                                                        |
| SRP: Einzig verantwortlich fuer Pattern-Zuweisung                     |
|      Definiert KEINE Architektur (-> cleanCodeArchitect)              |
|      Bewertet NICHT den Blueprint (-> blueprintQG)                    |
|      Erstellt KEINE Sub-Blueprints (-> cleanCodeSlice)                |
+======================================================================+
```

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_I_patternLibrary {NAME} --stufe {N}                 ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                            ║
║    1. {WORKING_DIR}/_manifest.md  (per-Story BL-155 AK-1)   ║
║       (Pipeline-State, Blueprint-Pfad via s{N}_blueprint_path)       ║
║    2. .claude/meta/implementation/stage_{STUFE}.md                   ║
║       (Stufen-Metadaten: blueprint_perspektive, fanout, etc.)        ║
║    3. .claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md        ║
║       (Gross-Blueprint von cleanCodeArchitect -- PFLICHT)            ║
║    4. {VAULT_ROOT}/Libraries/PatternLibrary/_index.md  (VAULT-ONLY) ║
║       (Pattern Library Index — Vault-First BL-151, PRIMAER)         ║
║       Fallback: .claude/patterns/_pl-index.md (DEPRECATED, BL-151)  ║
║       VAULT_ROOT via: resolve_vault_root.py (ARCH-N8, Single Source)║
║    5. {VAULT_ROOT}/Libraries/PatternLibrary/_generic/*.md +         ║
║       {VAULT_ROOT}/Libraries/PatternLibrary/_project/{LAYER}/*.md  ║
║       (Pattern Library Details — Vault-First BL-151)                ║
║    6. BERATER_OUTPUTS.patternBrief.matched_patterns (PRIMAER)        ║
║       (von _SDF_berater_patternBrief vorgeladen — Single-Source      ║
║       ARCH-8: bevorzugt vor eigenem PatternLibrary-Re-Load)         ║
║                                                                      ║
║  SCHREIBT (Output) - PFLICHT:                                        ║
║    .claude/analysis/blueprints/{FEATURE}/S{N}/blueprint.md           ║
║      UPDATE: ## Pattern-Zuweisung Sektion wird befuellt/ersetzt      ║
║    {VAULT}/_manifest.md                                     ║
║      s{N}_pattern_zuweisung: done|pending                            ║
║      s{N}_pattern_zuweisung_at: "{DATUM}"                            ║
║      s{N}_pattern_coverage: "{N}/{M} Slices"                         ║
║      s{N}_pt_signal: KEIN_PATTERN (nur bei [KEIN PATTERN GEFUNDEN])  ║
║      s{N}_pt_signal_slices: "{slice1}, {slice2}" (betroffene Slices) ║
║      s{N}_pt_signal_at: "{YYYY-MM-DD}"                               ║
║    .claude/wissen/pattern-usage.log                                   ║
║      APPEND: KEIN_PATTERN Eintrag pro betroffenem Slice              ║
║                                                                      ║
║  HAUPTPRODUKT:                                                       ║
║    Aktualisierter Blueprint mit vollstaendiger                        ║
║    ## Pattern-Zuweisung Sektion                                       ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    - Aendert NUR die ## Pattern-Zuweisung Sektion im Blueprint       ║
║    - Loescht KEINE anderen Blueprint-Sektionen                       ║
║    - MCP-Bremse: easy=1Q, normal=3Q, hard=5Q                         ║
║    - Falls Pattern Library nicht vorhanden: Graceful Degradation      ║
║      (leere Zuweisung + Hinweis, kein Fehler-Abbruch)               ║
║                                                                      ║
║  MCP INTEGRATION:                                                    ║
║    - mcp__cleancoder__query() fuer Pattern-Suche                     ║
║    - collection: "local_knowledge"                                   ║
║    - limit: 3 pro Query                                              ║
║                                                                      ║
║  MCP-BREMSE:                                                         ║
║    ┌───────────────────────────────────────────────────┐             ║
║    │  easy:   max 1 Query  (1 Query fuer alle Slices)  │             ║
║    │  normal: max 3 Queries (wichtigste Slices)        │             ║
║    │  hard:   max 5 Queries (komplexeste Slices)       │             ║
║    └───────────────────────────────────────────────────┘             ║
║                                                                      ║
║  PIPELINE-POSITION:                                                  ║
║    [_I_requirementCheck] -> [_I_patternLibrary] -> [_I_testSearch]   ║
║                                                                      ║
║  ACTOR: PATTERN-ZUWEISER                                             ║
║    Liest Blueprint, sucht Patterns, schreibt Zuweisung.              ║
║    KEINE Architektur-Entscheidungen, KEINE Tests.                    ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## Aufruf

```
/_I_patternLibrary {NAME} --stufe {N}

Parameter:
  NAME:    Feature-Name (PFLICHT)
  --stufe: Teststufe 1-5 (PFLICHT). Bestimmt welcher Blueprint geladen wird.

Beispiele:
  /_I_patternLibrary DCSRE-881 --stufe 1   -> Pattern-Zuweisung fuer Stufe 1 Blueprint
  /_I_patternLibrary MeinFeature --stufe 2  -> Pattern-Zuweisung fuer Stufe 2 Blueprint
```

---

## Ablauf

### Schritt 1: Blueprint laden

1. Lies `{WORKING_DIR}/_manifest.md`  # per-Story I_PIPELINE_STATE (BL-155 AK-1)
   - Extrahiere `s{N}_blueprint_path` (falls vorhanden)
   - Validiere dass `s{N}_blueprint: done` gesetzt ist (Vorbedingung)
2. Falls `s{N}_blueprint_path` nicht im Manifest gesetzt:
   - Verwende Default-Pfad: `.claude/analysis/blueprints/{NAME}/S{N}/blueprint.md`
3. Lies `.claude/meta/implementation/stage_{N}.md`
   - Extrahiere `blueprint_perspektive` (Laserpointer/Taschenlampe/Scheinwerfer/Flutlicht)
   - Extrahiere `fanout`, `mocks_erlaubt` als Kontext
4. Lies Blueprint vollstaendig
5. Extrahiere alle Slices/Inseln/Module aus `## Slice-Plan` oder `## Scope` Sektion
   - Erstelle Liste: [{Slice-Name, Beschreibung, Komplexitaet}]
   - Falls keine Slices/Inseln erkennbar: HiL-Eskalation (Blueprint moeglicherweise leer)

**Vorbedingungs-Check:**

Falls `s{N}_blueprint: done` NICHT gesetzt:
```
FEHLER: Blueprint fuer Stufe {N} noch nicht erstellt.
Vorbedingung nicht erfuellt: _I_cleanCodeArchitect muss zuerst ausgefuehrt werden.
Naechster Schritt: /_I_cleanCodeArchitect {NAME} --stufe {N}
```

---

### Schritt 1.5: Single-Source patternBrief + sliceBrief-Delegation (AK-B-4, BL-153, ARCH-8)

> **ARCH-8 Single-Source (INV-EINSCHUB, ARCH-8):** `_SDF_berater_patternBrief` laedt die
> PatternLibrary VOR `_I_patternLibrary`. Wenn `BERATER_OUTPUTS.patternBrief.matched_patterns`
> vorhanden und `no_match=false` → direkt verwenden, KEIN Re-Load der PatternLibrary (vermeidet
> Double-Read). Nur bei `no_match=true` oder fehlendem patternBrief → Schritt 2 (MCP-Fallback).

# BL-237 AK-1 (O-4, Split-Brain-Vermeidung) — EHRT patternBrief-Reihenfolge, KEIN Doppel-Sort:
# Die matched_patterns/matched_semantics kommen aus _SDF_berater_patternBrief BEREITS reife-sortiert
# (Schritt 3: rank_by_maturity() = maturity() DESC + confidence-Cold-Start-Tie-Break, AK-CTX-R3).
# Der EINZIGE Sort-Ort ist R3 (patternBrief Schritt 3). _I_patternLibrary konsumiert die Reihenfolge
# READ-ONLY und sortiert NICHT erneut (keine Zweitsortierung nach confidence/maturity/sonstwas) — sonst
# Split-Brain zweier divergenter Ranking-Quellen. Die patternBrief-Ordnung ist verbindlich.

```
# Phase A: patternBrief Single-Source (ARCH-8 + ARCH-10, Primaer-Quelle)
patternBrief = lies BERATER_OUTPUTS.patternBrief ?? null

IF patternBrief != null AND patternBrief.no_match == false:
  sdf_matched_patterns  = patternBrief.matched_patterns  ?? []   # BEREITS reife-sortiert (R3) — Reihenfolge EHREN
  sdf_matched_semantics = patternBrief.matched_semantics ?? []   # ARCH-10 — ebenfalls R3-sortiert, KEIN Re-Sort
  # AK-1: KEIN Doppel-Sort hier (Single-Sort-Ort = R3 / patternBrief Schritt 3, O-4). Read-only-Konsum.
  Logge: "[patternLibrary] patternBrief Single-Source: {|sdf_matched_patterns|} Patterns + {|sdf_matched_semantics|} Semantics aus SDF (ARCH-8/10; Reihenfolge=R3 reife-sortiert, KEIN Doppel-Sort)"
  → GOTO Phase B (sliceBrief mit Patterns+Semantics als Kontext)

# Phase B: sliceBrief-Delegation (AK-B-4, Thin-Wrapper)
Skill(_I_berater_sliceBrief, args="{NAME} --stufe {N}")

sliceBrief = BERATER_OUTPUTS.sliceBrief

IF sliceBrief.no_match == false:
  matched_patterns    = sliceBrief.matched_patterns
  pattern_assignments = sliceBrief.pattern_assignments
  → GOTO Schritt 3a (Pattern-Zuweisung-Tabelle erstellen, sliceBrief-Daten als Input)

IF sliceBrief.no_match == true AND patternBrief == null:
  Logge: "[patternLibrary] sliceBrief.no_match=true + kein patternBrief → Fallback MCP-Query (Schritt 2)"
  → Weiter mit Schritt 2 (MCP-Query als Fallback, AK-B-4 Backward-Compat)

IF sliceBrief.no_match == true AND sdf_matched_patterns != null:
  Logge: "[patternLibrary] sliceBrief.no_match=true aber patternBrief vorhanden → Schritt 3a mit SDF-Patterns"
  matched_patterns    = sdf_matched_patterns
  pattern_assignments = []  # Slice-Zuordnung vom sliceBrief leer — manuell nach 3a
  → GOTO Schritt 3a
```

**NON-BLOCKING (INV-B2-1):** Falls sliceBrief-Skill nicht verfuegbar oder Fehler → automatisch Fallback auf Schritt 2.

---

### Schritt 2: Pattern Library durchsuchen (MCP-Bremse)

**Budget-Ermittlung:**

| Schwierigkeit (aus Kontext) | Max Queries |
|-----------------------------|-------------|
| easy | 1 |
| normal | 3 |
| hard | 5 |

**Priorisierung (falls Slices > Budget):**

1. Schwierigste Slices zuerst (Komplexitaet: schwer > mittel > leicht)
2. Bei Gleichstand: Slices ohne offensichtliches Standard-Pattern bevorzugen
3. Nicht genutztes Budget NICHT aufsparen (1 Command = 1 Ausfuehrung)

**Pruefe zuerst Pattern Library Index (VAULT-ONLY, INV-PL-VAULT-1):**

```
# ═══ INV-PL-VAULT-1 (NEU 2026-05-10): VAULT-ONLY ═══
# Siehe meta/INV-PL-VAULT.md fuer vollstaendige Invariante-Definition.
# User-Direktive 2026-05-10: "Pattern Libraries SOLLEN vault-oriented funktionieren,
# keine local copy, keine local arbeit. Wachsen wie Models ueber Zeit."

# Schritt 0: VAULT_ROOT verbindlich aufloesen (PFLICHT)
VAULT_ROOT = subprocess.check_output([
  sys.executable, ".claude/scripts/resolve_vault_root.py"
], text=True).strip()
Logge: "[patternLibrary] VAULT_ROOT={VAULT_ROOT}"

ASSERT VAULT_ROOT != "" AND VAULT_ROOT != WORKING_DIR
  Bei Bruch: FAIL exitcode=2

# Schritt 1: Vault-Pfad konstruieren (NIE local)
vault_pl = f"{VAULT_ROOT}/Libraries/PatternLibrary"
Logge: "[patternLibrary] vault_pl={vault_pl}"

# Schritt 2: ANTI-PATTERN-Guard — local IGNORIEREN (DEPRECATED Legacy-Stale)
local_pl = f"{WORKING_DIR}/.claude/patterns"
IF exists(local_pl):
  Logge WARNUNG: "[patternLibrary] ANTI-PATTERN: lokales {local_pl} existiert (Legacy-Stale, ggf. _pattern-library.md/_pl-index.md). IGNORIERE — Vault ist canonical."
  # KEIN read von local_pl — auch nicht als Fallback. KEIN _pl-index.md mehr lesen.

# Schritt 3: Vault-Existenz pruefen (kein Fallback auf local)
IF NOT exists(vault_pl):
  Logge FEHLER: "[patternLibrary] FAIL — Vault-PatternLibrary fehlt: {vault_pl}. /_PT_arch_init aufrufen."
  -> Graceful Degradation (Schritt 3b) ABER ohne local-Fallback

Lies {vault_pl}/_index.md
Falls NICHT vorhanden:
  -> Graceful Degradation (Schritt 3b)
Falls vorhanden:
  -> Fahre mit MCP-Queries fort
```

**MCP-Query pro Slice (innerhalb Budget):**

```python
mcp__cleancoder__query(
    query_text="{Slice-Name} {Slice-Beschreibung} Pattern Implementierung",
    collection="local_knowledge",
    limit=3
)
```

**Fuer easy-Modus (1 Query fuer alle Slices zusammen):**

```python
mcp__cleancoder__query(
    query_text="Pattern Zuweisung fuer {alle Slice-Namen kommagetrennt}",
    collection="local_knowledge",
    limit=5
)
```

**Sammle pro Slice:**
- Pattern-Name (oder "[KEIN PATTERN GEFUNDEN]")
- Kurze Beschreibung (1-2 Saetze)
- Pfad in Pattern Library (z.B. `_patterns/be-cont-001.md` oder `-`)
- Min-Anwendungen (falls angegeben, sonst `-`)
- Max-Anwendungen (falls angegeben, sonst `-`)
- Fallback (falls Pattern nicht anwendbar oder nicht gefunden)

---

### Schritt 3a: Pattern-Zuweisung-Tabelle erstellen (Normal-Pfad)

Erstelle Markdown-Tabelle mit allen identifizierten Slices:

```markdown
| Insel/Modul | Pattern-Name | Beschreibung | PL-Pfad | Semantik-Regeln | Min | Max | Fallback |
|-------------|-------------|--------------|---------|-----------------|-----|-----|---------|
| {Slice 1}   | {Pattern}   | {Desc}       | {Pfad}  | {SR-ID oder "-"} | {N} | {M} | {Alt}   |
| {Slice 2}   | {Pattern}   | {Desc}       | {Pfad}  | {SR-ID oder "-"} | {N} | {M} | {Alt}   |
```

<!-- ARCH-20 (BL-153): Semantik-Regeln-Spalte ergaenzt — aus sliceBrief.matched_semantics befuellen.
     Wert: SR-ID(s) aus matched_semantics (z.B. "SR-001, SR-003") oder "-" wenn keine. -->

Fuer Slices ausserhalb des MCP-Budgets (nicht abgefragt):

```markdown
| {Slice K}   | [BUDGET ERSCHOEPFT] | Kein Query mehr im Budget. Fallback: Standard-Implementierung. | - | - | - | Standard |
```

---

### Schritt 3b: Graceful Degradation (Pattern Library nicht vorhanden)

Falls `_pl-index.md` nicht gefunden ODER MCP liefert keine Ergebnisse:

```markdown
| Insel/Modul | Pattern-Name | Beschreibung | PL-Pfad |
|-------------|-------------|--------------|---------|
| {Slice 1}   | [KEIN PATTERN GEFUNDEN] | Pattern Library nicht verfuegbar oder kein passendes Pattern. Fallback: Standard-Implementierung gemaess Stufen-Perspektive. | - |
| {Slice 2}   | [KEIN PATTERN GEFUNDEN] | Pattern Library nicht verfuegbar oder kein passendes Pattern. | - |
```

Hinweis fuer Team Lead hinzufuegen:
```
> HINWEIS: Pattern Library nicht verfuegbar. Zuweisung kann in einem separaten Schritt
> ergaenzt werden wenn Pattern Library aufgebaut wurde.
```

**PT-Signal bei [KEIN PATTERN GEFUNDEN] (RF-PIL2, W255, W263):**

Bei JEDEM Slice mit `[KEIN PATTERN GEFUNDEN]` (aus Schritt 3a oder 3b):

1. **Manifest-Felder schreiben** (AC-PIL2-1):
```yaml
s{N}_pt_signal: KEIN_PATTERN
s{N}_pt_signal_slices: "{slice1}, {slice2}, ..."
s{N}_pt_signal_at: "{YYYY-MM-DD}"
```
Nur bei echten KEIN-PATTERN-Faellen setzen, NICHT pauschal (AC-PIL2-2).
Wenn ALLE Slices ein Pattern haben: KEIN pt_signal setzen.

2. **pattern-usage.log Eintrag** (pro betroffenem Slice):
```
{YYYY-MM-DD} | KEIN_PATTERN | {feature-name} | {slice-cluster} | KEIN_PATTERN | i-patternlibrary
```
Datei: `.claude/wissen/pattern-usage.log`
Falls nicht vorhanden: Erstellen mit Header.

**INVARIANTE (ADR-PL-008, AC-PIL2-3):** KEIN direkter `/_PT_extract` Aufruf aus `_I_patternLibrary`. Das PT-Signal im Manifest ist ein SIGNAL fuer den Orchestrator, der ueber tatsaechlichen PT-Aufruf entscheidet.

---

### Schritt 4: Blueprint aktualisieren

Ersetze die `## Pattern-Zuweisung` Sektion im Blueprint (die von `_I_cleanCodeArchitect`
als Platzhalter angelegt wurde):

```markdown
## Pattern-Zuweisung

<!-- Erstellt von _I_patternLibrary, {DATUM} -->
<!-- MCP-Queries: {Q} von {max_Q} Budget genutzt -->

{Pattern-Zuweisung-Tabelle aus Schritt 3a oder 3b}

### Pattern-Abdeckung

- **Abgedeckt:** {N} von {M} Slices mit Patterns
- **Ohne Pattern:** {K} Slices (Fallback: Standard-Implementierung)
- **MCP-Queries:** {Q} von {max_Q} Budget genutzt
- **Pattern Library:** {verfuegbar|nicht verfuegbar}
```

**Wichtig:** NUR `## Pattern-Zuweisung` Sektion ersetzen. Alle anderen Sektionen
(Frontmatter, Scope, Stufen-Block, Test-Inventar, Slice-Plan) bleiben unveraendert.

Aktualisiere Blueprint-Frontmatter:
```yaml
pattern_zuweisung: done
```

---

### Schritt 5: Manifest aktualisieren

Ergaenze in `{VAULT}/_manifest.md`:

```yaml
s{N}_pattern_zuweisung: done
s{N}_pattern_zuweisung_at: "{YYYY-MM-DD}"
s{N}_pattern_coverage: "{N}/{M} Slices"
```

---

### Schritt 6: Exit-Report

Ausgabe an Konsole:

```
_I_patternLibrary {NAME} --stufe {N}: ABGESCHLOSSEN

Pattern-Zuweisung:
  - Slices gesamt:    {M}
  - Mit Pattern:      {N}
  - Ohne Pattern:     {K}
  - Coverage:         {N}/{M}

MCP-Queries: {Q}/{max_Q} Budget genutzt
Blueprint aktualisiert: .claude/analysis/blueprints/{NAME}/S{N}/blueprint.md
Manifest: s{N}_pattern_zuweisung = done

Naechster Schritt: /_I_testSearch {NAME} --stufe {N}
```

Sende SendMessage an "team-lead":

```
_I_patternLibrary {NAME} --stufe {N}: FINAL
Pattern-Zuweisung: {N}/{M} Slices abgedeckt
MCP-Queries: {Q}/{max_Q}
Blueprint aktualisiert: .claude/analysis/blueprints/{NAME}/S{N}/blueprint.md
Manifest: s{N}_pattern_zuweisung = done
```

---

## MCP-Bremse (Query-Budget)

| Modus | Max Queries | Strategie |
|-------|-------------|-----------|
| easy | 1 | 1 Query fuer alle Slices zusammen |
| normal | 3 | 3 Queries fuer wichtigste Slices |
| hard | 5 | 5 Queries fuer komplexeste Slices |

**Query-Budget-Verwaltung:**

1. Zaehle Slices aus Blueprint
2. Falls Slices <= Budget: 1 Query pro Slice
3. Falls Slices > Budget: Priorisiere nach Komplexitaet (schwer zuerst)
4. Verbleibende Slices erhalten `[BUDGET ERSCHOEPFT]` Eintrag
5. Nicht genutztes Budget NICHT aufsparen (1 Command = 1 Ausfuehrung)

---

## Abgrenzung (Was dieser Command NICHT tut)

- **Erstellt KEINEN neuen Blueprint** (-> _I_cleanCodeArchitect ist dafuer zustaendig)
- **Bewertet NICHT den Blueprint** (-> _I_blueprintQG ist dafuer zustaendig)
- **Aendert KEINE Architektur-Entscheidungen** (-> cleanCodeArchitect hat diese bereits getroffen)
- **Erstellt KEINE Sub-Blueprints** (-> _I_cleanCodeSlice ist dafuer zustaendig)
- **Verwaltet NICHT die Pattern Library** (-> separates Feature, nur lesend)
- **Schreibt KEINE Tests** (-> TDD-Zyklus ist dafuer zustaendig)
- **Loescht KEINE Blueprint-Sektionen** (NUR ## Pattern-Zuweisung wird ersetzt)

---

## Pipeline-Position

```
[/_I_cleanCodeArchitect]   Schritt 1: Architektur
          |
          v
[/_I_requirementCheck]     Schritt 1a: Requirement Check
          |
          v
[/_I_patternLibrary]       Schritt 1b: Pattern Library  <-- DIESER COMMAND
          |
          v
[/_I_testSearch]           Schritt 2: Test-Suche
          |
          v
[/_I_goldDefine]           Schritt 3: Gold-Definition
          |
          v
[/_I_blueprintQG]          Schritt 4: Quality Gate
```

**Prev:** `/_I_requirementCheck` (validiert Anforderungen nach Architect)
**Next:** `/_I_testSearch` (sucht und kategorisiert bestehende Tests)

---

## Obsidian-Tags

```yaml
tags:
  - type/pattern-assignment
  - pipeline/implementation
  - op/{FEATURE}
  - topic/Patterns
  - topic/Blueprint
pipeline-position: architect-1b-of-7
prev: [[I_requirementCheck]]
next: [[I_testSearch]]
```

---

## Siehe auch

- [[_I_requirementCheck]] - Vorheriger Schritt (Anforderungs-Verifikation)
- [[_I_testSearch]] - Naechster Schritt (Test-Suche & Kategorisierung)
- [[_I_cleanCodeSlice]] - Erstellt Sub-Blueprints nach QG-Freigabe
- [[_pl-index.md]] - Pattern Library Index (Input)
