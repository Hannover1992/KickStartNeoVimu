---
type: building-block
status: NEU v1.0 (BL-237 batch_C5 AK-8 — Living Pattern System Sichtbarkeit)
---

# /_pattern_status

**Status:** NEU v1.0 (BL-237 batch_C5 AK-8)
**Actor:** DIAGNOSE (READ-ONLY)
**Zweck:** Sichtbarkeit der PatternLibrary-Reife — Reife-Ranking + pending Lern-Signale + contested/retired + Time-Axis-Evolution. Rendert den fertigen Stage-8-`.report`-Slot + die PatternLibrary-Frontmatter-Counter. **Mutiert die PatternLibrary NIE** (PT-CMD-014, analog `/_D_status` ohne `--fix`).

---

## Vertrag

```
+========================================================================+
|  COMMAND: /_pattern_status [BL_ID] [--full] [--scope=<scope>]          |
+========================================================================+
|                                                                        |
|  LIEST (Input) — PFLICHT (PT-CMD-006 Vault-First-Resolution):          |
|    VAULT_ROOT via resolve_vault_root.py (INV-PL-VAULT-1)               |
|    {VAULT}/Libraries/PatternLibrary/_project/*/_index.md   (Counter-Spalten, AK-8/F3) |
|    {VAULT}/Libraries/PatternLibrary/_project/*/*.md         (Pattern-Frontmatter: usage_count/broken_count/status) |
|    {bl_folder}/_manifest.md                                           |
|      BERATER_OUTPUTS_PT.report.{materialized,matured,contested,        |
|        retired,pending{quiescenz_deferred,worthiness_pending},         |
|        yield_ratio,summary_line}            (Stage-8-Slot, F2 — Datenquelle) |
|      (bl_folder via resolve_bl_path.py, falls BL_ID gegeben)           |
|                                                                        |
|  SCHREIBT (Output):                                                    |
|    KEINES — rein diagnostisch, idempotent (PT-CMD-014 Read-Only-Actor) |
|    [Ausgabe: Reife-Karte + pending Lern-Signale als Text-Tabelle]      |
|    KEIN --fix, KEIN Library-Mutate, KEIN zweiter Live-Aggregat-Call.   |
|                                                                        |
|  INVARIANTEN:                                                          |
|    INV-PS-1 (PT-CMD-014 Read-Only): 0 Schreiboperationen, mutiert die  |
|      PatternLibrary NIE (kein lifecycle/add_arch/_index-Write).        |
|    INV-PS-2 (.report-Konsum, F2): konsumiert den fertigen Stage-8-     |
|      .report-Slot — KEIN zweiter eigener Aggregat-Call (kein Doppel-   |
|      Logik gegen _PT_berater_report).                                  |
|    INV-PS-3 (Code-Vokabular, W-CNT-7): zeigt NUR usage_count /         |
|      broken_count / maturity()=usage_count-broken_count / status —     |
|      KEIN erfundenes Reife-Feld (confirm_count/maturity_score-Phantom).|
|    INV-PS-4 (Graceful, PT-CMD-023): leere/teil-befuellte PL ODER       |
|      fehlender .report-Slot -> Leer-Karte, kein Crash.                 |
|                                                                        |
+========================================================================+
```

---

## 1. Verantwortlichkeit

Der **DIAGNOSE**-Actor (READ-ONLY) hat eine einzige Verantwortung:

**Sichtbar machen — niemals mutieren.**

Was `/_pattern_status` **TUT**:
- Liest die PatternLibrary-Frontmatter-Counter (`usage_count`/`broken_count`/`status`) + die `_index.md`-Counter-Spalten (AK-8/F3)
- Berechnet `maturity() = usage_count - broken_count` (ABGELEITET, W-CNT-7) — kein Frontmatter-Feld
- Rendert das Reife-Ranking (maturity DESC), die pending Lern-Signale (quiescenz_deferred / worthiness_pending aus `.report`), die contested/retired-Bilanz und die Time-Axis-Evolution
- Konsumiert den fertigen Stage-8-`.report`-Slot (`_PT_berater_report`) — KEINEN eigenen zweiten Aggregat-Call (INV-PS-2, F2)

Was `/_pattern_status` **NICHT TUT** (PT-CMD-014 Read-Only-Actor-Constraint):
- Die PatternLibrary aendern (kein `lifecycle`/`add_arch`/`_index`-Write — 0 Schreiboperationen)
- Einen `--fix`-Pfad anbieten (anders als `/_D_status` — es gibt KEIN `--fix`)
- Counter neu aggregieren statt den `.report`-Slot zu lesen (kein Doppel-Logik gegen Stage 8)
- Den scharfen 486-Live-Lauf triggern (AK-9 ist ein separates HiL/EXTERN-Gate)

---

## 2. Datenquellen (READ-ONLY)

| Quelle | Feld | Verwendung |
|--------|------|------------|
| `.report`-Slot (`_PT_berater_report` Stage 8) | `materialized`/`matured`/`contested`/`retired` | Harvest-Bilanz-Zeile (F2) |
| `.report`-Slot | `pending.quiescenz_deferred`/`pending.worthiness_pending` | pending Lern-Signale (INV-REP-3 -> hier sichtbar; worthiness_pending=false seit batch_C5) |
| `.report`-Slot | `yield_ratio`/`summary_line` | Anti-95%-Leak-Kennzahl + 1-Zeilen-Bilanz |
| PatternLibrary `_project/*/*.md` Frontmatter | `usage_count`/`broken_count`/`status` | Reife-Ranking pro Pattern (`pl.read_counter` + `pl.maturity`) |
| PatternLibrary `_project/*/_index.md` | Counter-Spalten (AK-8/F3) | schnelle Index-Sicht ohne jede Datei zu oeffnen |
| Pattern-Frontmatter | `boundary_notes`/`broken_locations` | Time-Axis-Evolution + contested-Detail (`--full`) |

> **Reuse (PT-CMD-006 Vault-First-Resolution):** Lesen via `pattern_library.read_counter()` /
> `pattern_library.maturity()` / `pattern_library.rank_by_maturity()` — KEIN eigener Frontmatter-Parser,
> KEIN eigener Counter-Kern (Reuse-not-rebuild, DoD-21; Vokabular code-konform W-CNT-7).

---

## 3. Algorithmus (READ-ONLY)

```
SCHRITT 0 (PT-CMD-002 ENTRY-Logging):
  Logge: "[pattern_status] ENTRY scope={scope} bl={BL_ID or '-'}"
  VAULT_ROOT = resolve_vault_root()   # PT-CMD-006, INV-PL-VAULT-1

SCHRITT 1: Pattern-Frontmatter sammeln (READ-ONLY)
  Fuer jede {VAULT}/Libraries/PatternLibrary/_project/<layer>/*.md (ausser _index.md):
    counter = pattern_library.read_counter(file)         # graceful default (AK-MIG-0)
    entries.append({id, layer, usage_count, broken_count,
                    maturity: pattern_library.maturity(counter), status, broken_locations})
  (Bei --scope=domain|factoring: gegen DomainLibrary/FactoringLibrary; default arch.)

SCHRITT 2: Reife-Ranking (INV-PS-3 Code-Vokabular)
  ranked = pattern_library.rank_by_maturity(entries, top_n=999)   # maturity DESC, _generic/_global erhalten
  # KEIN erfundenes Reife-Feld — nur usage_count/broken_count/maturity()/status.

SCHRITT 3: .report-Slot konsumieren (INV-PS-2, F2 — KEIN zweiter Aggregat-Call)
  IF BL_ID gegeben:
    report = read BERATER_OUTPUTS_PT.report aus {resolve_bl_path(BL_ID)}/_manifest.md
  ELSE report = null
  pending = report.pending ?? {quiescenz_deferred:false, worthiness_pending:false}

SCHRITT 4: Ausgabe (rein diagnostisch)
  Rendere Reife-Karte (Summary + Ranking) + pending Lern-Signale + (--full: Time-Axis/contested-Detail).
  IF leere PL: "Keine Patterns in {scope}. (Cold-Start — Library greenfield/teil-befuellt.)" (INV-PS-4)

SCHRITT 5 (PT-CMD-002 EXIT-Logging):
  Logge: "[pattern_status] EXIT 0 Schreiboperationen (READ-ONLY, PT-CMD-014)"
```

---

## 4. Ausgabe-Format (Reife-Karte)

### Standard-Ausgabe

```markdown
# Pattern-Reife-Karte: {scope} ({Datum})

## Zusammenfassung

| Status        | Anzahl |
|---------------|--------|
| PROVEN        | {N}    |
| active        | {N}    |
| experimental  | {N}    |
| deprecated    | {N}    |

Harvest-Bilanz (aus .report): {materialized} materialisiert / {matured} gereift / {contested} contested / {retired} retired (yield {yield_ratio})

## Reife-Ranking (maturity = usage_count - broken_count, DESC)

| Pattern-ID | Layer | usage_count | broken_count | maturity | status |
|------------|-------|-------------|--------------|----------|--------|
| PT-DOM-005 | BE-DOMAIN | 12 | 0 | 12 | PROVEN |
| ...        | ...   | ... | ... | ... | ... |

## Pending Lern-Signale (INV-REP-3)

| Signal | Wert |
|--------|------|
| quiescenz_deferred | {true/false} |
| worthiness_pending | false  (AK-CTX-WORTHINESS-EXTRACT gebaut, batch_C5) |
```

### --full Ausgabe (zusaetzlich)

```markdown
## Time-Axis-Evolution / contested-Detail

| Pattern-ID | broken_locations | boundary_notes |
|------------|------------------|----------------|
| PT-DOM-007 | [Foo.cs: revert ...] | [broken in Bar.cs: ...] |
```

---

## 5. Parameter

| Parameter | Pflicht | Beschreibung |
|-----------|---------|-------------|
| `BL_ID` | OPTIONAL | wenn angegeben: liest den `.report`-Slot aus dem BL-Manifest fuer die Harvest-Bilanz + pending-Signale |
| `--full` | OPTIONAL | zusaetzliche Time-Axis-Evolution / contested-Detail-Tabelle |
| `--scope=<scope>` | OPTIONAL | `arch` (default) \| `domain` \| `factoring` — gegen die jeweilige Library |

**KEIN `--fix`** (anders als `/_D_status`): `/_pattern_status` ist READ-ONLY (PT-CMD-014). Die Reife
bewegt ausschliesslich der organische Counter-Feed (R6b-Drain via `lifecycle`), nie das Dashboard.

---

## 6. Abgrenzung zu /_D_status

`/_D_status` misst Zeilen-Bloat aller Artefakt-Typen (mit optionalem `--fix`-Debloat-Pfad).
`/_pattern_status` misst die **PatternLibrary-Reife** (Counter/maturity) und ist STRIKT READ-ONLY
(kein `--fix`, kein Mutate). Beide teilen die DIAGNOSE-Actor-Struktur (Ampel-/Karten-Renderer,
idempotent, 0 Schreiboperationen ohne expliziten Fix-Pfad). `/_pattern_status` hat keinen Fix-Pfad.

---

## Kompakt-Sicherheit

Nach Command-Abschluss:
- State: Keine Aenderungen (PT-CMD-014, INV-PS-1 — 0 Schreiboperationen)
- Resume: Reife-Karte als Text-Output, nicht persistent

---

## Siehe auch

- [[_PT_berater_report]] — Stage 8, liefert den `.report`-Slot (Datenquelle, F2/INV-PS-2)
- [[_PT_orchestrate]] — Pattern-Extraction-Orchestrator (Stage 8 -> Phase 9)
- [[_D_status]] — kanonisches READ-ONLY-Dashboard-Analog (Struktur-Vorlage, ABER mit --fix)
- `pattern_library.py` — `read_counter`/`maturity`/`rank_by_maturity` (Reuse-Quelle, INV-PS-3)
