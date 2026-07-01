---
status: active
version: 2.1.0
created: 2026-03-30
updated: 2026-04-25
op: KomplexitaetsBemessung
phase: Analysis
type: orchestration
chain_position: post-spec
difficulty_scaling: true
team_based: true
---

```
+======================================================================+
| COMMAND: /_K_score                                              |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (DU — reiner Orchestrator)                          |
|   CONSTRAINT: Team Lead fuehrt KEINE Berechnungen selbst aus.        |
|   NUR spawnen, tracken, konsolidieren.                                |
|                                                                        |
| ZWECK: Numerische Komplexitaetsbemessung einer Aufgabe anhand der     |
|        Spezifikation (AKs/RFs). Produziert 3 Metriken:               |
|          1. AUFWAND (Menge × Kategorie × Konfidenz)                   |
|          2. KOPPLUNG (Fan-In/Out, Interfaces, Abhaengigkeiten)        |
|          3. FRAGILITAET (Kopplung × Risiko × Unbekannte)              |
|        Aggregat: K-Score (0-100) = gewichtete Kombination.            |
|                                                                        |
| PIPELINE-POSITION:                                                     |
|   A-Pipeline: ... → /_spec → /_K_score → /_gap → ...           |
|   SDF-Trigger: AKs ohne K-Werte → Handschuh-Wechsel hierher          |
|                                                                        |
| PRINZIP: Wellen-basiert (Standard OmniCommand Pattern).               |
|          Agents teilen AKs untereinander auf.                         |
|          Gesamt-Score = Aggregat aller AK-Werte.                      |
|                                                                        |
| AUFRUF:                                                                |
|   /_K_score {NAME} [difficulty] [ceiling] [floor]               |
|                                                                        |
| LIEST:                                                                 |
|   {VAULT}/.../Spec/{NAME}_Spec.md       (AKs/RFs — Primaer-Input)    |
|     FALLBACK: .claude/specs/{NAME}_Spec.md                             |
|   {VAULT}/.../Model/{NAME}_Model.md     (W{n}-Konfidenz)             |
|     FALLBACK: .claude/models/{NAME}_Model.md                           |
|   .claude/patterns/                     (Pattern Library Lookup)      |
|   {VAULT}/_manifest.md                  (State)                       |
|   {VAULT}/_session_params.md            (globale Parameter)           |
|   Codebase (bei BEARBEITEN-AKs: Glob/Grep fuer Kopplung)             |
|                                                                        |
| SCHREIBT (BL-065 Vault-First DirectWrite):                            |
|   # BL-065: Write direkt in Vault (RF-06, INV-VFC-4)                  |
|   vault_path = "{VAULT}/Backlog/{BL_SLUG}/4_K-Score/{NAME}-K-SCORE.md" |
|   # Pre-Flight mkdir + Fail-fast (BL-065 AK-10, INV-VFC-4)           |
|   mkdir -p {VAULT}/Backlog/{BL_SLUG}/4_K-Score/           |
|   IF mkdir fehlschlaegt ODER DCS_VAULT_ROOT leer:                     |
|     log_error "Vault unreachable: {vault_path}"                       |
|     exit 1  # KEIN stiller Fallback (INV-VFC-2)                       |
|   Schreibe {vault_path}                                               |
|   Vault-Pfad via vault-routing.json (5-stufig)                        |
|   {VAULT}/_manifest.md                         (K-Felder Update)     |
|                                                                        |
| SCHREIBT NICHT:                                                        |
|   .claude/specs/* (nur /_spec schreibt Specs)                         |
|   .claude/models/* (nur /_model schreibt Models)                      |
|   Codebase (KEINE Code-Aenderungen)                                   |
|   DF_BATCH_STATE.recommended_modus  (BL-165 AK-9 forbidden_key)       |
|   DF_BATCH_STATE.sdf_mode_hint      (BL-165 AK-9 forbidden_key)       |
|   DF_BATCH_STATE.expected_sdf_mode  (BL-165 AK-9 forbidden_key)       |
|   DF_BATCH_STATE.sdf_mode           (BL-165 AK-9 forbidden_key)       |
|   DF_BATCH_STATE.mode_recommendation (BL-165 AK-9 forbidden_key)      |
|   --- not_writes (AK-7 / INV-MODUS-5, prefix-frei) ---                |
|   recommended_modus                                                    |
|   sdf_mode                                                             |
|   sdf_mode_hint                                                        |
|   expected_sdf_mode                                                    |
|   mode_recommendation                                                  |
+======================================================================+
```

## AK-7-REVISION (2026-05-08 — dark_factory AUFGEHOBEN)

Historischer ALT-Block aus `BL-162-kscore-coupling-analysis-lsp.md` Z292-318
(der INV-MODUS-5 bei `dark_factory=false` lockerte) ist **AUFGEHOBEN**.

UNCONDITIONAL gilt: K-Score-Output enthaelt NIE Modus-Empfehlung — unabhaengig von
dark_factory-Status. Siehe Model W17 (STABIL-N7).

---

## v3-Orchestrate-Engine (BL-311 AK-16, 2026-06-21)

**Zwei Pfade — Pfad-Weiche in Phase 0:**

```
+=========================================================================+
| PFAD-WEICHE: Solo 2.0 vs. v3-Orchestrate                               |
|                                                                         |
| should_use_v3_full = (item_count >= n_schwelle) OR k_verdacht           |
|   n_schwelle = session_params.k_v3_schwelle ?? 3  (AK-15 / SOA-3)      |
|   k_verdacht = session_params.k_verdacht ?? false                       |
|                                                                         |
| IF NOT should_use_v3_full:                                              |
|   → PFAD A: Solo-Pfad 2.0 (weiter unten ab "Phase 0: Initialisierung") |
|     Schema 2.0, 3 LLM-Achsen, Wellen-basiert (5-3-1).                  |
|     Proportionalitaet: Messen darf nicht teurer sein als die Arbeit.   |
|     (dispatch_kscore.js gibt terminated_reason='solo_path_2.0' zurueck) |
|                                                                         |
| IF should_use_v3_full:                                                  |
|   → PFAD B: v3-Orchestrate (dispatch_kscore.js — 4-Stage-Walker-Engine) |
|     Schema 3.0, 8+1 Achsen, parallele read-only Walker.               |
+=========================================================================+
```

### PFAD B: v3-Orchestrate — Artefakte + Stages

**Engine:** `.claude/workflows/dispatch_kscore.js` (BL-311 batch_3)
**Python-Substrat:**
- `.claude/scripts/kscore_v3_axes.py` — 6 Achsen-Definitionen (BL-311 batch_1)
- `.claude/scripts/kscore_v3_topology.py` — Overlap-Graph + contention_per_item (BL-311 batch_2)
- `.claude/scripts/kscore_v3_scoring.py` — 3-Schicht-Formel k_roh→k_praez→k_final (BL-311 batch_2)
- `.claude/scripts/kscore_v3_persist.py` — Schema-3.0-Write + Solo-Pfad-Weiche (BL-311 batch_2)

**Substrat-Reuse (bestehende Scripts, KEIN Duplikat):**
- `.claude/scripts/kazman_kscore_axes.py` — co_commit_axis, fragility_axes, kscore_risk_finding, RISK_CLASS_ENUM (BL-381)
- `.claude/scripts/cochange_coupling.py` — cochange_pairs, file_degree (BL-381)

**4-Stage-Ablauf (dispatch_kscore.js, deterministisch — INV-MOTOR-1-analog):**

```
Stage 0 PLAN:    Planer-Agent erzeugt walker_plan[] (1 Eintrag pro PL-Item)
                 → safeSchemaAgent (schema-erzwungen, BL-228-haertet)

Stage 1 WALKERS: N Items → N agent()-Calls parallel (read-only)
                 Jeder Walker erhebt Achsen 1-6 pro Item:
                   Achse 1 (Scope/Groesse): LOC, zyklomatik, kognitiv
                   Achse 2 (Operation-Typ): ADD/EXTEND/MODIFY/DELETE/MOVE + OP_MULT
                   Achse 3 (Kopplung): Ca/Ce/Instability, fan_in, call_tiefe (INV-K2)
                   Achse 4 (Kohaesion/SRP): srp_defizit, lcom
                   Achse 5 (OCP): ocp_vorhanden, erweiterungspunkte
                   Achse 6 (Lokalitaet): streuung_klasse, streuung_faktor
                 Barrier: alle Walker-Outputs gesammelt bevor Stage 2 startet.

Stage 2 TOPOLOGY: kscore_v3_topology.build_overlap_graph + contention_per_item
                  → Overlap-Graph (gemeinsam betroffene Dateien zwischen Items)
                  → Contention-Score pro Item (Hotspot-Signal)

Stage 3 SCORING:  kscore_v3_scoring.score_item + aggregate
                  → k_roh (6 Achsen gewichtet)
                  → k_praez (k_roh + Overlap-Contention)
                  → k_final (k_praez + epistemische Penalty (Achse 8) + Pattern-Discount (Achse 9))
                  → k_max / k_avg / k_min (BL-304-Heterogenitaets-Praezision)

Stage 4 PERSIST:  kscore_v3_persist.write_schema_3
                  → Schema 3.0 = Schema 2.0 Felder +
                                 overlap_edges +
                                 contention_per_item +
                                 k_min
                  → Dual-Felder-Strategie (Schema-2.0-Leser bleiben funktionsfaehig,
                    BL-266-Lehre: kein harter Cut)
```

**Aufruf durch Team Lead (PFAD B):**

```
Workflow(name="dispatch_kscore", args={
  bl_id:         "{BL-ID}",
  name:          "{NAME}",
  vault:         "{VAULT_ROOT}",
  working_dir:   "{BL_FOLDER}",
  pl_items:      [{id, title, ziel_symbole, ziel_dateien, pl_draft_text}, ...],
  n_schwelle:    {session_params.k_v3_schwelle ?? 3},
  k_verdacht:    {false|true},
  session_params: {weights?, OP_MULT-Overrides?, PATTERN_DISCOUNT-Overrides?}
})
RETURN: { walker_outputs, topology, scores, persist_path, terminated_reason, agent_spawns }
```

**Heimat-Hinweis (BL-312, forward-Referenz):**
`_K_score.md` ist der _orchestrierende Vertrag_. Die **primaere Heimat** des v3-Orchestrate-Aufrufs
ist `_IDF_berater_metricPlanner` (BL-312, Lane A — EIN Bewertungs-Ort, zentraler IDF-Messpunkt).
IDF ruft `dispatch_kscore.js` dort auf; `_K_score.md` bleibt der Solo-Pfad-Einstieg fuer
direkte `/_K_score {NAME}`-Aufrufe (A-Pipeline + Stand-alone-Auswertungen).

> **FENCE (Lane B):** Dieser Block dokumentiert nur den Wiring-Vertrag.
> `_IDF_berater_metricPlanner` und `_IDF_orchestrate` werden NICHT veraendert (Lane A).

**Schema-3.0-Output (kscore_v3_persist.py, Ergaenzung zu Schema 2.0):**

```yaml
# Schema 3.0 — NEU gegenueber 2.0 (additiv, Dual-Felder):
schema_version: "3.0"
overlap_edges:         # Walker-Schnittmengen (Dateien die mehrere Items benoetigen)
  - [item_a, item_b, datei]
contention_per_item:   # Hotspot-Schwere pro Item (0.0-1.0)
  {item_id}: {0.0-1.0}
k_min: {0-100}         # Untergrenze des Heterogenitaets-Bandes (BL-304)
k_max: {0-100}         # Obergrenze
k_avg: {0-100}         # Durchschnitt
# Schema-2.0-Felder bleiben erhalten (k_score, k_aufwand, k_kopplung, k_fragilitaet, ...)
```

**Solo-Pfad-Weiche in kscore_v3_persist.py (AK-15):**

```python
# should_use_v3_full(item_count, k_verdacht, n_schwelle) -> bool
# Rueckgabe: True = v3-Full-Workflow; False = Solo-Pfad 2.0 (Trickle)
```

**INV-MODUS-5-Compliance (unveraendert):** Schema-3.0-Output enthaelt ebenso NIE Modus-Felder
(`recommended_modus`, `sdf_mode`, `sdf_mode_hint`, `expected_sdf_mode`, `mode_recommendation`).
Die alleinige Modus-Quelle bleibt `_SDF_berater_modusEntscheidung` (INV-MODUS-1).

---

## SOURCE-PROVENANCE-PROPAGATION (BL-160 AK-5)

**INV-PROV-PROP-5:** Jeder Output-Datei MUSS source_provenance + provenance_chain Frontmatter-Block enthalten.

**Pattern:**
1. Lies Vorgaenger-Output (Spec, Model). Extrahiere predecessor.source_provenance + predecessor.provenance_chain.
2. Bei Output-Schreibung ({NAME}-K-SCORE.md):
   - source_provenance: kopiere von predecessor (gleiche Source-URL/PageId)
   - provenance_chain: haenge neuen Layer-Eintrag an (layer=4, artifact=kscore_pfad, role="metric", timestamp=ISO, derived_from=[spec_pfad, model_pfad])
3. Bei mehreren Predecessors: provenance_chain.derived_from sammelt alle Vorgaenger (Spec + Model).
4. Wenn predecessor.source_provenance FEHLT (legacy): setze source_provenance={source: "legacy_pre_BL-160", source_kind: "legacy", fetched_at: ISO_NOW}.

**Helper:** Verwende `.claude/scripts/propagate_provenance.py update <output_path>` nach Output-Schreibung — autoupdate predecessor.used_in (Hebb-bidir).

**role-Mapping fuer diesen Skill:** `"metric"`

---

## Parameter

| Parameter | Default | Werte | Beschreibung |
|-----------|---------|-------|-------------|
| `NAME` | (auto) | String | Feature-Name. Falls leer: aus Manifest A_PIPELINE_STATE.feature |
| `difficulty` | normal | easy, normal, hard | Wellen-Tiefe |
| `ceiling` | opus | haiku, sonnet, opus | Hoechstes Modell |
| `floor` | haiku | haiku, sonnet | Niedrigstes Modell |
| `--mode` | (leer) | pl_item | Aufruf-Modus. `pl_item`: K-Score fuer ein einzelnes PL-Item berechnen (BL-203 AK-3). Erwartet `--pl={pl_id}` als Pflicht-Arg. Output: `{k_score: N}` statt Story-Aggregat. |
| `--pl` | null | PL-Item-ID | PL-Item-ID (Pflicht wenn --mode=pl_item). Z.B. `--pl=PL-BL203-1`. |

---

## Wellen-Uebersicht

```
difficulty=easy:   1 Synthese (ceiling) — direkt, keine Wellen
difficulty=normal: 5 Explorer (floor) → 3 Drafter (middle) → 1 Synthese (ceiling)
difficulty=hard:   9 Explorer (floor) → 5 Drafter (middle) → 1 Synthese (ceiling)
```

---

## Prozess-Statusanzeige (RF-10)

```
┌───────┬──────────────────────────┬──────────────────────────┬──────────┬──────────────────────────────────────────────┐
│ Phase │ Aktion                   │ Agenten / Delegation     │ Status   │ Inhalt (Mini-Assay, NUR bei DONE)            │
├───────┼──────────────────────────┼──────────────────────────┼──────────┼──────────────────────────────────────────────┤
│ 0     │ Initialisierung          │ Team Lead direkt         │ . PENDING│                                              │
│ 1     │ W1: Explorer (Inputs)    │ {N} haiku PARALLEL       │ . PENDING│                                              │
│ 2     │ W2: Drafter (Metriken)   │ {M} sonnet PARALLEL      │ . PENDING│                                              │
│ 3     │ W3: Synthese (K-SCORE)   │ 1 opus                   │ . PENDING│                                              │
│ 4     │ Manifest + Monitoring    │ Team Lead direkt         │ . PENDING│                                              │
└───────┴──────────────────────────┴──────────────────────────┴──────────┴──────────────────────────────────────────────┘
```

---

## Pflicht-Walk (4 Schritte — sequential, KEIN Monolith)

Bei `schema_version="2.0"` MUSS der Worker den 4-Schritt-Walk ausfuehren.
Bei `schema_version="1.0"` siehe Sektion F (Schema-Version-Branch).

### SCHRITT 1 — per AK

Fuer jede AK in der Story:

- **1a.** LSP: `findReferences(AK-Haupt-Symbol)` → `Ca` (afferent coupling)
- **1b.** LSP: `getCallHierarchy(AK-Haupt-Symbol)` → `Ce` (efferent coupling)
- **1c.** Berechne `I = Ce / (Ca + Ce)`. Sonderfall `Ca == 0 AND Ce == 0` → `I = 0`.
- **1d.** Berechne `k_aufwand`, `k_kopplung` (mit Ca/Ce/I), `k_fragilitaet` —
  je mit Pflicht-Feld `*_components` (INV-DERIV-1).
- **1e.** Berechne `k_score_ak = 0.30 * k_aufwand + 0.30 * k_kopplung + 0.40 * k_fragilitaet`.

**Abschluss-Marker:** `BERATER_OUTPUTS.kscore.per_ak` vollstaendig befuellt
bevor Schritt 2 startet (PL-1.3).

### SCHRITT 2 — per Layer

Fuer jeden relevanten Layer (DTO/Validator/Mapper/Service/Controller — Layer-Set
projekt-spezifisch aus `session_params.layer_set`):

- **2a.** LSP: `findReferences(layer-boundary-symbol)` → `Ca_layer`.
- **2b.** Berechne `k_score_layer` aus `Ca_layer` + Layer-spezifischer Fragilitaet.

**Abschluss-Marker:** `BERATER_OUTPUTS.kscore.per_layer` vollstaendig befuellt
bevor Schritt 3 startet (PL-1.3).

### SCHRITT 3 — per Component

Fuer jede neue Code-Einheit (DTO-Klasse, Validator, Methode, etc.):

- **3a.** LSP: `getDefinition(component)` → Abstractness `A` = Anteil abstrakte
  Member.
- **3b.** LSP: `getDocumentSymbols(component-file)` → Hierarchie-Tiefe.
- **3c.** Berechne `D = |A + I - 1|` (Distance from Main Sequence).
- **3d.** Weise `k_score_component` basierend auf `D + I` zu.

**Abschluss-Marker:** `BERATER_OUTPUTS.kscore.per_component` vollstaendig befuellt
bevor Schritt 4 startet (PL-1.3).

### SCHRITT 4 — Aggregation

- **4a.** `k_score_total = Σ(k_score_ak × 0.30) + Σ(k_score_layer × 0.30) + Σ(k_score_component × 0.40)`.
- **4b.** Berechne `coupling_metrics`: `Ca_total`, `Ce_total`, `I_avg`, `A_avg`, `D_avg`.
- **4c.** Leite `maturity_indicator` ab (HIGH/MEDIUM/LOW per Threshold-Tabelle aus Sektion B-Sub).
- **4d.** Schreibe `sdf_modus_input` (Beobachtungsdaten, KEINE Empfehlung — siehe Sektion D).

### INV-K1-Guard (PL-1.2)

Vor Schreiben des K-SCORE.md MUSS Validator pruefen:

```
IF schema_version == "2.0" AND BERATER_OUTPUTS.kscore.per_ak IS EMPTY:
  FAIL "INV-K1 violation: schema 2.0 ohne per_ak"
```

### INV-DERIV-1-Guard (PL-1.4)

Vor Schreiben des K-SCORE.md MUSS Validator pruefen:

```
FOR EACH score_field in [k_aufwand, k_kopplung, k_fragilitaet, k_score_*]:
  IF score_field.value != null AND score_field.components IS EMPTY:
    FAIL "INV-DERIV-1 violation: {score_field} ohne *_components"
```

### Difficulty-Mapping zum Wellen-Muster (BS-3 Klaerung)

- **easy:** 4-Schritt-Walk laeuft in Phase 3 (Synthese solo), keine Wellen.
- **normal/hard:** 4-Schritt-Walk laeuft in D03 (Aggregator) **nach** D01/D02-DONE.
  D01/D02 bleiben Wellen-parallel — D03 strukturiert ihr Output als per_ak/per_layer/per_component.

---

## LSP-Pflicht-Protokoll (AK-2)

Jeder Schritt 1-3 (Sektion A) MUSS LSP-Calls ausfuehren BEVOR Werte geschrieben werden.

### LSP-Tool-Matrix (Pflicht-Calls)

| LSP-Tool | Verwendungszweck | Mapping auf Metrik |
|----------|------------------|--------------------|
| `findReferences(symbol)` | Wer ruft `symbol` auf? | `Ca` (afferent coupling) |
| `getCallHierarchy(symbol)` | Wen ruft `symbol` auf? | `Ce` (efferent coupling) |
| `getDefinition(symbol)` | Wo ist `symbol` definiert? | `A` (Abstractness) |
| `getDocumentSymbols(file)` | Welche Symbole in Datei? | Hierarchie-Tiefe |

### Ablauf-Protokoll (pro Call)

1. **Anzeige:** Worker zeigt LSP-Aufruf explizit:
   `"LSP: findReferences(SymbolName)"`
2. **Wait:** Worker wartet auf Ergebnis.
3. **Dokumentation:** Worker schreibt in `lsp_evidence` (siehe Sektion E):
   `"{file}:{line} via {lsp-tool}"`
4. **Ableitung:** Score-Wert wird abgeleitet aus LSP-Output.

### Fallback bei LSP-Nichtverfuegbarkeit (PL-2.3, INV-K2)

Wenn LSP nicht erreichbar:

- **Fahre** mit Pattern-Match-Heuristik fort (fan_in/fan_out via Glob+Grep).
- **Markiere** JEDEN davon abgeleiteten Wert explizit:

```yaml
k_kopplung:
  value: 6
  components: [...]
  warning: "lsp_unavailable — pattern_match_fallback aktiviert"
```

- **KEIN stiller Fallback** ohne `warning`-Markierung (INV-K2). Verletzung = FAIL.

### Sonderfall `.md`-Commands (PL-2.4 — md-proxy-Mapping)

LSP-Tools arbeiten primaer auf Source-Code (.cs/.ts/.py). Fuer `.md`-Command-Dateien gilt:

- `findReferences` → Glob-Suche: `grep -r "Skill(_{COMMAND}" .claude/commands/`
- `getCallHierarchy` → Grep nach `Skill\(` Aufrufen INNERHALB des `.md`-Files

### lsp_evidence-Format fuer md-proxy (INV-LSP-1)

Eintraege fuer `.md`-Proxy-Aufloesungen MUESSEN den Prefix `md-proxy:` tragen:

```
md-proxy: Skill(_K_score) in _IDF_berater_batchPlan.md via glob
```

Format-Verletzung (fehlender Prefix bei Glob-basierten Eintraegen) = FAIL.

### PL-Items Mapping

- PL-2.1: LSP-Tool-Matrix vollstaendig (4 Tools).
- PL-2.2: `lsp_evidence`-Pflicht (Schritt 3 Ablauf-Protokoll, Detail in Sektion E).
- PL-2.3: Fallback-Protokoll mit `warning: lsp_unavailable`.
- PL-2.4: md-proxy-Mapping (Sonderfall .md-Commands).
- PL-2.5: Reihenfolge LSP-vor-Wert (Schritt 1-4 Ablauf-Protokoll, explizit).
- PL-2.6: Worker zeigt LSP-Aufruf vor Ergebnis (Schritt 1 Anzeige).
- PL-2.7: `lsp_evidence` Format-Pflicht (Vertragsteil — Detail siehe Sektion E).

---

## Coupling-Metriken nach Robert C. Martin (Ca/Ce/I/A/D) — AK-3

Bei `schema_version="2.0"` MUSS der Worker pro Komponente alle 5 Martin-Metriken
berechnen.

### Die 5 Metriken

| Metrik | Name | Formel | LSP-Quelle |
|--------|------|--------|------------|
| `Ca` | Afferent Coupling | Anzahl externer Caller | `findReferences` |
| `Ce` | Efferent Coupling | Anzahl ausgehender Aufrufe | `getCallHierarchy` |
| `I` | Instability | `Ce / (Ca + Ce)` | abgeleitet |
| `A` | Abstractness | abstract_members / total_members | `getDefinition` |
| `D` | Distance from Main Sequence | `|A + I - 1|` | abgeleitet |

### INV-DIV-ZERO Guard (PL-3.2)

Die I-Formel hat einen Division-by-Zero-Sonderfall:

```
IF Ca == 0 AND Ce == 0:
  I = 0     # Per Spec-Konvention (W16, STABIL-N6)
ELSE:
  I = Ce / (Ca + Ce)
```

Verletzung (Division-by-Zero ungehandelt) = FAIL.

### maturity_indicator-Ableitung (PL-3.3, PL-3.4)

Aus `D` (Distance from Main Sequence) wird der `maturity_indicator` abgeleitet:

| `D`-Bereich | `maturity_indicator` | Bedeutung |
|-------------|---------------------|-----------|
| `D < 0.30` | HIGH | Auf oder nahe Main Sequence — gesund |
| `0.30 ≤ D < 0.70` | MEDIUM | Pain Zone (zu wenig abstract bei hoher Ce) — Refactoring-Kandidat |
| `D ≥ 0.70` | LOW | Zone of Pain / Zone of Uselessness — kritisch |

### Konfigurierbare Thresholds (PL-3.5)

Die Threshold-Werte sind **NICHT hardcoded** im Skill. Sie werden aus
`_session_params.md` Block `coupling_thresholds` gelesen:

```yaml
coupling_thresholds:
  instability_critical: 0.7      # I-Wert ab dem Komponente in high_coupling_components
  distance_pain_zone_low: 0.30   # D unter dem HIGH startet
  distance_pain_zone_high: 0.70  # D ab dem LOW startet
```

Defaults (wenn `coupling_thresholds`-Block fehlt) sind oben angegeben. Worker MUSS
in `lsp_evidence` dokumentieren ob Defaults verwendet wurden oder Konfiguration.

### Pflicht-Output

Pro Komponente erscheinen alle 5 Werte im Schema-2.0-Output unter
`BERATER_OUTPUTS.kscore.coupling_metrics` (Schema-Definition kommt mit AK-4 — SubB):

```yaml
coupling_metrics:
  per_component:
    {ComponentName}:
      Ca: 5
      Ce: 3
      I: 0.375
      A: 0.20
      D: 0.575
      maturity_indicator: MEDIUM
```

Fehlt eine der 5 Metriken bei `schema_version="2.0"` = FAIL (INV-K1 / AK-3).

---

## Evidence-Edges (BL-160-Provenance, INV-LSP-1)

Jeder `lsp_evidence`-Eintrag MUSS folgendes Format einhalten:

```
{file}:{line} via {lsp-tool}
```

### Beispiele

- `EinrichtungsdatenService.cs:42 via findReferences`
- `IEinrichtungsdatenService.GetByIdAsync via getCallHierarchy` (line optional fuer Interface-Symbole)
- `md-proxy: Skill(_K_score) in _IDF_berater_batchPlan.md via glob` (Sonderfall .md, vgl. PL-2.4)

### Format-Pruefung (INV-LSP-1)

Regex zur Validierung (Pflicht-Test):

```
^(md-proxy: )?[\w./:\-]+ via (findReferences|getCallHierarchy|getDefinition|getDocumentSymbols|glob|grep)$
```

Verletzung (Eintrag matched Regex nicht) = FAIL.

> **Hinweis:** Diese Sektion ist in SubA enthalten, weil PL-2.6/PL-2.7 ein klar
> definiertes Format-Vertragsstueck benoetigen. Das vollstaendige Schema-2.0-Output-Template
> inkl. `lsp_evidence`-Feld-Definition kommt mit AK-4 in SubB.

---

## Phase 0: Initialisierung

```
# NAME herleiten (IF-8 Fallback)
IF NAME nicht angegeben:
  NAME = lies(_manifest.md → A_PIPELINE_STATE.feature)
  IF NAME leer: FEHLER "NAME nicht angegeben und nicht aus Manifest herleitbar"

# Session-Parameter lesen
params = lies(_session_params.md)
difficulty = params.difficulty ?? "normal"
ceiling    = min(ceiling, params.ceiling)
floor      = max(floor, params.floor)
middle     = sonnet wenn ceiling=opus, sonnet wenn ceiling=sonnet, haiku wenn ceiling=haiku

# Inputs validieren (BL-065 Vault-First)
# Primaer: Vault-Pfad via vault-routing.json; Fallback: .claude/ (nur fuer Lese-Operationen)
spec_path = "{VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md"
IF NOT exists(spec_path):
  spec_path = ".claude/specs/{NAME}_Spec.md"  # Legacy Read-Fallback
IF NOT exists(spec_path): FEHLER "Spec fehlt. Starte /_spec {NAME}"

model_path = "{VAULT}/Backlog/{BL_SLUG}/2_Model/{NAME}_Model.md"
IF NOT exists(model_path):
  model_path = ".claude/models/{NAME}_Model.md"  # Legacy Read-Fallback
IF NOT exists(model_path): WARNUNG "Model fehlt — W{n}-Konfidenz-Penalty entfaellt"

# AKs aus Spec extrahieren
spec = lies(spec_path)
ak_liste = extrahiere_aks(spec)  # Alle AK-IDs + Beschreibungen + Labels
Logge: "=== /_K_score GESTARTET: {NAME} ==="
Logge: "AKs: {|ak_liste|}, Difficulty: {difficulty}, Ceiling: {ceiling}"
```

---

## Phase 1: Welle 1 — Explorer (Inputs sammeln, PARALLEL)

```
IF difficulty == "easy": SKIP Phase 1, springe zu Phase 3 (Synthese solo)
```

Starte N Explorer-Agents PARALLEL (N=5 bei normal, N=9 bei hard).

### Explorer-Fokus-Bereiche

| Agent | Fokus | Liest | Produziert |
|-------|-------|-------|-----------|
| E01 | spec-extraktion | Spec.md | AK-Liste: ID, Beschreibung, betroffene Dateien, Typ (Backend/Frontend/Infra/Meta) |
| E02 | model-konfidenz | truth_consume.value(ref) (statt Model.md frei) | Pro AK: welche W{n} sind betroffen, w_offen/w_total Ratio (via truth_consume.is_open(ref)), Konfidenz-Score — source=atomic-first |
| E03 | code-kopplung | Codebase (Glob/Grep) | Pro betroffene Datei: Fan-In (wer referenziert), Fan-Out (was wird referenziert), Interface-Tiefe |
| E04 | pattern-lookup | .claude/patterns/ | Pro AK: Pattern-Treffer (battle-tested/unbattle-tested/keiner), Pattern-Name |
| E05 | abhaengigkeiten | Spec + Parking-Lot | AK-Abhaengigkeiten untereinander, externe Blocker, Reihenfolge-Constraints |

### Explorer Worker-Vertrag

```
Du bist Explorer E{NN} fuer die Komplexitaetsbemessung von "{NAME}".

INPUT — LIES ZUERST:
  1. {VAULT}/Backlog/{BL_SLUG}/3_Spec/{NAME}_Spec.md (BL-065 Vault-First)
     FALLBACK (legacy): .claude/specs/{NAME}_Spec.md
  2. {Fokus-spezifische Dateien — siehe Fokus-Tabelle}

AUFTRAG: {Fokus-Beschreibung}

SCHREIB-PFLICHT:
  .claude/analysis/drafts/{NAME}-K-E{NN}-{fokus}.md

FORMAT:
  ---
  name: {NAME}
  phase: k-score
  wave: exploration
  agent: E{NN}
  fokus: {fokus}
  date: {YYYY-MM-DD}
  status: final
  ---

  # K-Explorer E{NN}: {Fokus-Titel}

  ## AK-Analyse
  | AK-ID | {fokus-spezifische Spalten} |
  |-------|----------------------------|

  ## Zusammenfassung
  {3-5 Saetze}

VERBOTEN: Code-Editieren, Spec-Aendern, Model-Aendern. NUR LESEN + Output schreiben.
```

**Team Lead nach Welle 1:** Warte auf alle Explorer. Lies Outputs. Weiter zu Welle 2.

---

## Phase 2: Welle 2 — Drafter (Metriken berechnen, PARALLEL)

Starte M Drafter-Agents (M=3 bei normal, M=5 bei hard).
**SEQUENZ-CONSTRAINT (FC4, D03):** D01 + D02 starten PARALLEL. D03 startet ERST nach D01+D02 DONE.

### Drafter-Fokus-Bereiche

| Agent | Fokus | Liest | Produziert | Parallel? |
|-------|-------|-------|-----------|-----------|
| D01 | kategorisierung-aufwand | E01 + E04 | Pro AK: Kategorie (NEU/BEARBEITEN/LOESCHEN) + OC-Modifikator + Aufwand-Score | JA (mit D02) |
| D02 | kopplung-quadrant | E03 + E05 | Pro AK: Kopplung-Score + 4-Quadrant (Q1-Q4) + Hidden-Complexity-Signal | JA (mit D01) |
| D03 | fragilitaet-aggregation | E02 + **D01 + D02** | Pro AK: Fragilitaet-Score + Konfidenz-Penalty + Gesamt-K-Score + Aggregat | NEIN (wartet auf D01+D02) |

### Drafter Worker-Vertrag

```
Du bist Drafter D{NN} fuer die Komplexitaetsbemessung von "{NAME}".

INPUT — LIES ZUERST:
  1. .claude/specs/{NAME}_Spec.md
  2. Alle Explorer-Outputs: .claude/analysis/drafts/{NAME}-K-E*.md
  {Bei D03: Auch D01 + D02 Outputs lesen}

AUFTRAG: {Fokus-Beschreibung — siehe Formeln unten}

SCHREIB-PFLICHT:
  .claude/analysis/drafts/{NAME}-K-D{NN}-{fokus}.md

FORMAT:
  ---
  name: {NAME}
  phase: k-score
  wave: drafts
  agent: D{NN}
  fokus: {fokus}
  date: {YYYY-MM-DD}
  status: final
  ---

  # K-Drafter D{NN}: {Fokus-Titel}

  ## AK-Scores
  | AK-ID | {metrik-spezifische Spalten} | Score |
  |-------|------------------------------|-------|

  ## Zusammenfassung
  {5-10 Saetze}

VERBOTEN: Code-Editieren, Spec-Aendern, Model-Aendern. NUR LESEN + BERECHNEN + Output schreiben.
```

### Formeln fuer Drafter

#### D01: Kategorisierung + Aufwand

```
PRO AK:

1. KATEGORIE bestimmen:
   - NEU:        AK beschreibt etwas das NICHT existiert (neue Datei/Klasse/Command)
   - BEARBEITEN: AK beschreibt Aenderung an BESTEHENDEM Code/Command
   - LOESCHEN:   AK beschreibt Entfernung (selten)

2. KATEGORIE-FAKTOR:
   - NEU:        1.0 (Basis, OC-Modifikator kommt separat — siehe Schritt 2a)
   - BEARBEITEN: 4 feste Stufen basierend auf kopplung_norm (aus D02):
     kopplung_norm <=30:  1.5 (niedrige Kopplung)
     kopplung_norm 31-60: 2.0 (moderate Kopplung)
     kopplung_norm 61-80: 2.5 (hohe Kopplung)
     kopplung_norm >80:   3.0 (extreme Kopplung)
   - LOESCHEN:   0.5

2a. OC-MODIFIKATOR (nur bei NEU, AK-K2-B002, W22):
   Pruefe ob betroffene Stelle Open/Closed-konform ist:
   - OC-konform (Extension Point vorhanden):     NEU × 0.75
   - Gemischt (teilweise erweiterbar):            NEU × 1.0
   - Monolith (kein Extension Point):             NEU × 1.3

3. PATTERN-MODIFIKATOR (aus E04):
   - battle-tested Pattern:    × 0.5
   - unbattle-tested Pattern:  × 0.7
   - kein Pattern:             × 1.0

4. TESTBARKEIT (AK-K-020, F-NEU-2):
   - gut testbar (Unit-Test reicht):    × 0.8
   - schwer testbar (Integration noetig): × 1.3
   - nicht testbar (manuell/visuell):   × 1.5

5. PARALLELISIERBARKEIT (AK-K-021, F-NEU-3):
   - parallel bearbeitbar (viele Dateien aber unabhaengig): × 0.5
   - teilweise parallel:  × 0.8
   - strikt sequentiell:  × 1.0
   WICHTIG: Viele Dateien ≠ komplex! Dokumentations-Aenderungen an 100 Stellen
   sind EINFACH wenn parallel. Kopplung entscheidet, nicht Dateimenge.

6. AUFWAND-SCORE:
   aufwand(ak) = basis_gewicht(ak)
               × kategorie_faktor
               × pattern_modifikator
               × testbarkeit_faktor
               × parallelisierbarkeit_faktor

   basis_gewicht: Geschaetzt aus AK-Beschreibung (1-10 Skala):
     1-2:  Trivial (Konfiguration, Kommentar, Feld hinzufuegen)
     3-4:  Einfach (einzelne Methode, kleine Logik)
     5-6:  Mittel (Klasse/Interface, mehrere Methoden)
     7-8:  Komplex (Cross-Cutting, Architektur-Aenderung)
     9-10: Sehr komplex (Framework-Aenderung, Multi-Datei)

7. NORMALISIERUNG:
   aufwand_norm(ak) = aufwand(ak) / max(aufwand) × 100
```

#### D02: Kopplung + Quadrant (AK-K2-D001, AK-K2-C001-C006)

```
PRO AK:

1. KOPPLUNG-SCORE (aus E03 Daten):
   kopplung_roh(ak) = fan_in × 0.25
                    + fan_out × 0.15
                    + interface_tiefe × 0.25
                    + abh_anzahl × 0.15
                    + (1.0 - kohaesion_ratio) × 0.20

   kohaesion_ratio: Wie eng gehoeren die betroffenen Elemente zusammen?
                    1.0 = hohe Kohaesion (alles in einer Klasse/einem Modul)
                    0.0 = keine Kohaesion (ueber viele Module verstreut)
                    (AK-K-025, F-NEU-7: Hohe Kohaesion SENKT Kopplung-Score)

   kopplung(ak) = kopplung_roh(ak)

   fan_in:           Wie viele Dateien referenzieren die betroffene(n) Datei(en)?
   fan_out:          Wie viele externe Dateien werden referenziert?
   interface_tiefe:  Baseklasse mit N Ableitungen → N. Interface mit M Implementierungen → M.
   abh_anzahl:       Direkte externe Abhaengigkeiten (Imports, Skill-Aufrufe, etc.)

   SONDERFALL .md-Commands:
     fan_in  = Anzahl Commands die DIESEN Command per Skill() aufrufen
     fan_out = Anzahl Skill()-Aufrufe IN diesem Command
     interface_tiefe = 0 (Commands haben keine Vererbung)
     abh_anzahl = Anzahl LIEST/SCHREIBT Dateien im VERTRAG

2. 4-QUADRANTEN-ASSESSMENT (Uncle Bob Stability Metrics, AK-K2-C001/C002):
   NUR fuer BEARBEITEN-AKs. NEU/LOESCHEN → Q0 (kein Quadrant).

   Bestimme pro AK:
     ist_abstrakt:   Hat die betroffene Stelle ein Interface/Abstraktion? (true/false)
     wird_viel_genutzt: fan_in > Median(fan_in aller AKs)? (true/false)

   QUADRANT-ZUORDNUNG:
     Q1 (stable-unused):    NOT abstrakt AND NOT viel_genutzt → Faktor 0.8
     Q2 (stable-heavy):     NOT abstrakt AND viel_genutzt     → Faktor 1.5 (PAIN!)
     Q3 (volatile-light):   abstrakt AND NOT viel_genutzt     → Faktor 1.0 (DEFAULT)
     Q4 (volatile-heavy):   abstrakt AND viel_genutzt         → Faktor 1.2

   SONDERFALL .md-Commands (AK-K2-C003):
     .md-Commands sind per Definition Q3 (volatile-light) weil:
       - Keine Vererbung (interface_tiefe=0)
       - Aenderungen betreffen NUR den Command selbst
       - AUSNAHME: fan_in > 5 (viel aufgerufen) → Q4

3. HIDDEN-COMPLEXITY SIGNAL (AK-K2-C004/C005/C006):
   hidden_complexity = (basis_gewicht × kategorie_faktor) > 3.0

   WENN hidden_complexity == true:
     Logge: "⚠ HIDDEN-COMPLEXITY bei AK {ak_id}: basis={basis_gewicht}, kat={kategorie_faktor}"
     hidden_signal = true

   WENN hidden_complexity == true UND quadrant == Q2:
     Logge: "⚠⚠ PAIN-KOMBI: Hidden-Complexity + Q2 (stable-heavy) bei AK {ak_id}"
     pain_signal = true

4. NORMALISIERUNG:
   kopplung_norm(ak) = kopplung(ak) / max(kopplung) × 100
```

#### D03: Fragilitaet + Konfidenz-Penalty + Aggregation (AK-K2-D003)

```
SEQUENZ-CONSTRAINT: D03 startet ERST nach D01+D02 DONE (braucht beide Outputs).

PRO AK:

1. FRAGILITAET-SCORE (aus D02 Kopplung + E02 Daten):
   fragilitaet(ak) = kopplung_norm(ak) × 0.6
                    + aenderungs_risiko × 0.2
                    + unbekannte_stellen × 0.2

   aenderungs_risiko:  Aus git log: Wie oft wurde die Datei in letzten 30 Commits geaendert?
                        0 Aenderungen = 0, 1-3 = 0.3, 4-7 = 0.6, 8+ = 1.0
                        (schwacher Proxy: Volatilitaet einer EINZELNEN Datei, KEINE Paar-Kopplung)
   unbekannte_stellen: Anzahl OFFENER W{n} die diese Stelle betreffen (aus E02)
                        Normalisiert: count / max_count

   fragilitaet_norm(ak) = fragilitaet(ak) / max(fragilitaet) × 100

1b. CO-COMMIT-COUPLING (EIGENE Fragilitaets-Achse, BL-381 AK-2 — NICHT in fragilitaet(ak) addieren):
   co_commit_coupling(ak): Co-Change-GRAD der von der AK betroffenen Datei(en) — wie oft sie
                           mit ANDEREN Dateien im SELBEN Commit geaendert werden (Paar-Kopplung,
                           Kazman "historical co-commit reveals nonstructural coupling"). Das ist
                           etwas ANDERES als aenderungs_risiko (= Change-Frequenz EINER Datei).
   PRODUCER (EIN einziger, kein Doppel): .claude/scripts/cochange_coupling.py liefert
       file_degree(cochange_pairs(parse_git_log(git log --name-only))) = {datei: grad};
       .claude/scripts/kazman_kscore_axes.py:co_commit_axis(file_degree) normalisiert auf 0-100
       (Max-Normalisierung, K-Skala-Constraint W-CON-1).
   GETRENNT FUEHREN (W-AK2-2-Adjudikation): co_commit_coupling wird als EIGENES benanntes Feld
       NEBEN aenderungs_risiko gefuehrt — NICHT in denselben fragilitaet-Term gewichtet-addiert
       (sonst Doppel-Zaehlung + Verlust der Aktionierbarkeit). Beide Achsen liefert
       kazman_kscore_axes.fragility_axes(file_degree, aenderungs_risiko) als getrennte Maps.
   SCHWELLEN: welcher 0-100-Wert "rot/gelb/gruen" ist, ist NICHT hier definiert (an BL-311/312
       delegiert, W-CON-1). D03 fuehrt nur die 0-100-Achse.

2. KONFIDENZ-PENALTY (aus E02 Daten, W-Status via truth_consume.is_open(ref) source=atomic-first):
   # [BL-387 source=atomic] truth_resolver/truth_consume ist atomic-first + faellt auf legacy-Model-parse
   #   zurueck (resolve() Stufe-3) -> atom-frei heute = source=legacy == Vorher-Verhalten
   #   (backward-compat, legacy-fallback). truth_resolver UNVERAENDERT.
   w_bezug = W{n} die diese AK betreffen (Refs via truth_resolver.resolve)
   w_offen_bezug = count(ref in w_bezug WHERE truth_consume.is_open(ref, bl_folder=BL_SLUG, vault_root=VAULT) == True)
   penalty = 1.0 + (w_offen_bezug / max(w_bezug, 1)) × 0.5

   Effekt: AK die auf unsicheren Wahrheiten basiert → Score steigt um bis zu 50%

3. AUFWAND MIT PENALTY:
   aufwand_final(ak) = aufwand_norm(ak) × penalty

4. AGGREGAT PRO AK:
   k_score(ak) = aufwand_final(ak) × 0.40
               + kopplung_norm(ak)  × 0.35
               + fragilitaet_norm(ak) × 0.25

5. GESAMT-AGGREGAT:
   k_aufwand     = mean(aufwand_final(ak) fuer alle AKs)
   k_kopplung    = mean(kopplung_norm(ak) fuer alle AKs)
   k_fragilitaet = mean(fragilitaet_norm(ak) fuer alle AKs)
   k_score       = k_aufwand × 0.40 + k_kopplung × 0.35 + k_fragilitaet × 0.25

6. LABEL-ABLEITUNG:
   LOW    = k_score in [0, 33]
   MEDIUM = k_score in (33, 66]
   HIGH   = k_score in (66, 100]
```

#### D03b: K-Score-Aktionierbarkeit — risk_class + cost/benefit (BL-381 AK-4, Library-Reuse)

Der K-Score-**Skalar** bleibt unveraendert (`k_aufwand/k_kopplung/k_fragilitaet/k_score`).
Aktionierbarkeit ("Komplexitaet nur gut, wenn noetig + angemessen") entsteht als **nachgelagerter
eval_finding-Record** (eval_kind=design_eval), der den K-Score-Befund per `ref_node` (AK-ID /
Komponente) referenziert — W-AK4-3-Adjudikation. **KEIN neues Enum, kein dupliziertes Schema.**

```
PRO auffaelliger AK/Komponente (z.B. HIGH-k_score ODER hohe co_commit_coupling-Achse):
   record = kazman_kscore_axes.kscore_risk_finding(
              bl_slug, idx, ref_node=<AK-ID>,
              risk_class=<Omission|Commission|Realization|Managerial>,   # aus RISK_CLASS_ENUM
              severity, befund, cost, benefit, suggested_action)
   # risk_class wird gegen quality_model_wform.RISK_CLASS_ENUM erzwungen (freier String -> ValueError);
   # cost UND benefit muessen nicht-leer sein (EVAL_FINDING_NONEMPTY_FIELDS, Aktionierbarkeits-Pflicht).
   # render_eval_finding_block(record) besteht quality_model_wform.check_eval_finding_block (exit 0).
```

REUSE-NACHWEIS (W-AK4-1/2): `RISK_CLASS_ENUM` + `check_eval_finding_block` stammen aus
`.claude/scripts/quality_model_wform.py` (BL-382/383). `kazman_kscore_axes.py` IMPORTIERT das
Enum-Objekt (Identitaet) — es gibt KEIN zweites K-Score-eigenes risk_class-Enum.

#### D03c: Geteiltes Co-Change-Substrat — Seam zu BL-342/BL-415 (BL-381 AK-2, EIN Producer)

`.claude/scripts/cochange_coupling.py` ist der **EINZIGE** Co-Change-Producer. Geteiltes Artefakt:
`cochange_pairs` (Paarliste `(datei_a, datei_b, gemeinsame_commits)`) + `file_degree` (Grad-Map).
- **BL-381 (hier):** verdrahtet `file_degree` ueber `kazman_kscore_axes.co_commit_axis` als
  `co_commit_coupling`-Fragilitaets-Achse (D03 Schritt 1b).
- **BL-342/BL-415 (dort):** konsumiert DENSELBEN Producer-Output als Konflikt-Wahrscheinlichkeits-
  Praediktor fuer den Parallel-Scheduler (oft gemeinsam geaenderte Dateien kollidieren haeufiger).
- **Vertrag:** kein zweites Co-Change-Skript. Schema-Mismatch ist strukturell ausgeschlossen, weil
  beide denselben Modul-Output (`cochange_pairs` + `file_degree`) lesen (W-AK2-3-Adjudikation).

#### D03d: WO-Verdrahtung Decoupling-Level + Propagation-Cost (BL-381 AK-1-WO, screening-grade)

Diese Sektion ist die **WO-Doktrin** fuer AK-1 (markdown_uncoverable): sie beschreibt, WO + WIE die
screening-grade DL/PC in den K-Score-Produzenten einfliessen. Das **Compute-Modul existiert bereits**
(`.claude/scripts/kazman_screening_metrics.py`, batch_2: `decoupling_level`/`propagation_cost`/
`screening_metrics`/`adjacency_from_pairs`/`instability`, read-only, 0-100); D03d rechnet NICHTS neu,
sondern verdrahtet nur dessen Output.

- **WER konsumiert (Schritt):** D03 (`fragilitaet-aggregation`, dieselbe Welle-2-Stufe, die schon
  Schritt 1b `co_commit_coupling` verdrahtet). DL/PC sind plan-/design-zeit-Achsen (W-AK1-1) — sie
  gehoeren in den Fragilitaets-/Kopplungs-Aggregations-Schritt, NICHT in die D01-Aufwand- oder
  D02-Kopplungs-Quadrant-Stufe (die auf E03-Fan-Daten, nicht auf der Adjazenz-Topologie arbeiten).
  Im easy-Pfad uebernimmt der Synthese-Agent (Phase 3) die Verdrahtung.
- **WORAUS (Adjazenz-Quelle, zwei Optionen, EINE waehlen pro Lauf):**
  1. `_IDF_berater_dependencyAnalyzer`-DAG (`nodes[]`/`edges[]` als `{knoten: [nachbarn]}`-Map) —
     die design-time PL-Item-/Schichten-Topologie. Direkt an `kazman_screening_metrics.decoupling_level`/
     `propagation_cost` uebergeben.
  2. `cochange_coupling.cochange_pairs` als Co-Change-DSM-PROXY — ueber
     `kazman_screening_metrics.adjacency_from_pairs(pairs)` in eine ungerichtete Adjazenz wandeln, dann
     in dieselben DL/PC-Funktionen. Fallback/Ergaenzung, wenn keine DAG vorliegt (z.B. SDF-Re-Entry ohne
     frischen IDF-Lauf). KEINE neue file-level DSM, KEIN Import-/AST-Parser (Screening-Grade-Garantie,
     Spec Sec 0 / W-AK1-2).
- **WOHIN (Output-Feld):** zwei GETRENNTE benannte 0-100-Felder `decoupling_level` + `propagation_cost`
  (Konstanten `DECOUPLING_LEVEL_NAME`/`PROPAGATION_COST_NAME`, via `screening_metrics(adjacency)`). Sie
  werden als **per-Batch-Felder** in `metric_per_batch` gefuehrt (Producer `_IDF_berater_metricPlanner`
  Phase 7.6, Consumer `_SDF_berater_modusEntscheidung` C3 — AK-3, Drift-Test BL-266). KEIN globaler
  Repo-weiter Skalar (W-DOM-2). Sie werden NICHT in `k_kopplung`/`k_fragilitaet` addiert
  (kein Rueckkollaps, W-AK1-3 / W-DOM-1) — sie stehen NEBEN dem Skalar als eigene Achsen.
- **Schwellen:** welcher DL/PC-Wert "rot/gelb/gruen" ist, ist NICHT hier definiert (an BL-311/312
  delegiert, W-CON-1). D03d fuehrt nur die 0-100-Achsen.

#### D03e: Mehrdimensionale Kopplung — ableitbare Dimensionen + dokumentierte Luecken (BL-381 AK-6)

Der heute zu **einem** Skalar (`kopplung_roh` -> `k_kopplung`, Schritt 1 in D02) kollabierte
Kopplungs-Begriff wird mehrdimensional gefuehrt — **soweit aus vorhandenem Substrat ableitbar**, OHNE
Rueckkollaps in einen Sammel-Skalar (W-AK6-2: ein gewichteter Kopplungs-Skalar reproduziert W-DOM-1 auf
der Kopplungs-Ebene). Kazman (CMU/SEI-2020-TR-006) unterscheidet fuenf Kopplungs-Arten; davon:

**Ableitbar (code, batch_3 — `.claude/scripts/kazman_coupling_dimensions.py`, GETRENNTE Felder):**
- `coupling_structural` (syntactic) — Martin `Ca`/`Ce` -> Instabilitaet `I = Ce/(Ca+Ce)` je Komponente,
  via `kazman_screening_metrics.instability`. KEIN eigener Zaehler — Reuse des batch_2-Producers.
- `coupling_temporal_resource` — Co-Commit-Coupling (Kazman: co-commit "reveals control, data, timing,
  and resource-based coupling"), via `kazman_kscore_axes.co_commit_axis` (0-100, AK-2-Achse, batch_1).

**Bewusste, benannte Luecke (markdown, NICHT erzwungen, KEIN Fake, KEIN Rueckkollaps):**
- **data-semantic coupling** — zwei Stellen teilen dasselbe Daten-/Bedeutungs-Modell (z.B. implizite
  Annahmen ueber Feld-Semantik, Einheiten, Wertebereiche). Aus rein statischer Struktur + Git-Historie
  NICHT zuverlaessig ableitbar: erfordert Daten-Fluss-/Schema-Semantik-Analyse, idR mit Laufzeit-Trace.
- **behavioral coupling** — zwei Stellen sind ueber Verhalten/Kontrollfluss gekoppelt (Reihenfolge-,
  Timing-, Zustands-Abhaengigkeit zur Laufzeit), die nicht in der Aufruf-/Co-Change-Topologie sichtbar
  ist. OHNE Laufzeit-Trace (Ausfuehrungs-/Aufruf-Spuren) NICHT ableitbar.

Behandlung der Luecke (Anti-Fake-Pflicht): die beiden nicht-ableitbaren Dimensionen werden **NICHT** als
Pflichtfelder erzwungen und **NICHT** mit einer erfundenen Zahl gefuellt. Es gibt KEINEN Rueckkollaps der
ableitbaren Dimensionen in einen einzigen Kopplungs-Skalar, um die Luecke zu kaschieren. Wer
data-semantic/behavioral Kopplung sucht, findet HIER die benannte Luecke + Begruendung ("ohne
Laufzeit-Trace nicht ableitbar"), statt eines falschen Werts. Schliessen der Luecke (echte
Laufzeit-Trace-Analyse) ist eine Stretch-OQ ausserhalb BL-381-Scope (analog file-level DSM, W-AK1-2).

**Team Lead nach Welle 2:** Warte auf alle Drafter. Lies Outputs. Weiter zu Welle 3.

---

## BERATER_OUTPUTS.kscore Schema 2.0 (AK-4)

Dieses Schema definiert den **In-Memory-Vertrag** zwischen K-Score-Worker und Caller
(BERATER_OUTPUTS-Block im _manifest.md). Es ist die strukturierte Variante des
persistierten `K-SCORE.md`-Outputs und Pflicht bei `schema_version="2.0"`.

> **Verhaeltnis zu `K-SCORE.md`:**
> - `BERATER_OUTPUTS.kscore` = In-Memory-Schema (YAML im Manifest, Maschinen-Konsum)
> - `K-SCORE.md` = persistierter Bericht (Mensch-lesbar, gleiche Daten)
> Beide MUESSEN konsistent sein. K-SCORE.md-Frontmatter spiegelt BERATER_OUTPUTS.kscore.

### Pflicht-Felder (AK4-PL-1, INV-K1)

```yaml
BERATER_OUTPUTS:
  kscore:
    schema_version: "2.0"           # IMMER String (AK4-PL-6 / BL-161-Compat)
    computation_method: "4-step-walk + LSP-Pflicht-Protokoll (AK-1, AK-2, AK-3)"
    per_ak:                          # Pflicht: ≥1 Eintrag (INV-K1)
      AK-{id}:
        k_aufwand: {Zahl}
        k_aufwand_components: [...]  # Pflicht (INV-DERIV-1)
        k_kopplung:                  # OBJEKT, nicht Skalar (AK4-PL-4)
          ca: {Zahl}                 # Afferent Coupling via findReferences
          ce: {Zahl}                 # Efferent Coupling via getCallHierarchy
          instability: {0.0-1.0}     # I = Ce/(Ca+Ce); Sonderfall siehe INV-DIV-ZERO
        k_kopplung_components: [...] # Pflicht (INV-DERIV-1)
        k_fragilitaet: {Zahl}
        k_fragilitaet_components: [...]
        k_score_ak: {Zahl}           # 0.30*k_aufwand + 0.30*k_kopplung + 0.40*k_fragilitaet
        lsp_evidence:                # BL-160-Provenance (AK4-PL-3)
          - "{file}:{line} via {lsp-tool}"
    per_layer:                       # Aus SCHRITT 2
      {layer-name}:
        ca_layer: {Zahl}
        k_score_layer: {Zahl}
        k_score_layer_components: [...]
    per_component:                   # Aus SCHRITT 3
      {ComponentName}:
        k_score_component: {Zahl}
        k_score_component_components: [...]
    coupling_metrics:                # AK-3 Pflicht (AK4-PL-1)
      afferent_coupling_total: {Zahl}    # Σ(Ca)
      efferent_coupling_total: {Zahl}    # Σ(Ce)
      instability_avg: {0.0-1.0}         # Mean(I)
      abstractness_avg: {0.0-1.0}        # Mean(A)
      distance_avg: {0.0-1.0}            # Mean(D)
      per_component:                     # Detail je Komponente (Martin Ca/Ce/I/A/D)
        {ComponentName}:
          Ca: {Zahl}
          Ce: {Zahl}
          I: {0.0-1.0}
          A: {0.0-1.0}
          D: {0.0-1.0}
          maturity_indicator: HIGH|MEDIUM|LOW   # via D-Threshold (Sektion B-Sub)
    aggregate:
      k_score_total: {0-100}              # Σ(per_ak × 0.30) + Σ(per_layer × 0.30) + Σ(per_component × 0.40)
      weighting_scheme: "30/30/40 (AK/Layer/Component)"
      maturity_indicator: HIGH|MEDIUM|LOW  # Gesamt-Reife
      high_coupling_components: [...]     # I > coupling_thresholds.instability_critical
    sdf_modus_input:                    # AK4-PL-5 — Beobachtungs-Feld (Detail Sektion D)
      k_score_total: {Zahl}
      high_coupling_components: [...]
      fragility_drivers: [...]
      # "Beobachtungen, KEINE Empfehlung. SDF Phase 1.1 interpretiert."
```

### INV-MODUS-5-Compliance (AK4-PL-2, UNCONDITIONAL)

Der Schema-2.0-Output enthaelt **NIE** folgende Felder (Pre-Write-Hook prueft):

| Verbotenes Feld | Begruendung |
|-----------------|-------------|
| `recommended_modus` | INV-MODUS-5; alleinige Modus-Quelle ist SDF Phase 1.1 |
| `sdf_mode` | INV-MODUS-5 |
| `sdf_mode_hint` | INV-MODUS-5 |
| `expected_sdf_mode` | INV-MODUS-5 |
| `mode_recommendation` | INV-MODUS-5 |

dark_factory-Conditional ist **AUFGEHOBEN** (AK-7-REVISION 2026-05-08, vgl. Sektion AK-7-REVISION oben). INV-MODUS-5 gilt fuer alle Modi.

### lsp_evidence-Format (AK4-PL-3, INV-LSP-1)

Erlaubte Formate fuer Eintraege unter `per_ak.{id}.lsp_evidence`:

| Format | Verwendung | Beispiel |
|--------|-----------|----------|
| `{file}:{line} via {lsp-tool}` | Source-Code (.cs/.ts/.py) | `EinrichtungsdatenService.cs:42 via findReferences` |
| `md-proxy: {description} via glob` | `.md`-Command-Files | `md-proxy: Skill(_K_score) in _IDF_berater_batchPlan.md via glob` |
| LSP-Ausfall-Marker | siehe Sektion B (PL-2.3) — `lsp_evidence` enthaelt KEINEN Wert ohne expliziten Fail-Marker | (Detail in Sektion B Fallback-Protokoll) |

Freiform-Strings = INV-LSP-1-Verletzung = FAIL.

Vollstaendige Format-Validierung (Regex) siehe Sektion `## Evidence-Edges`.

### per_ak.k_kopplung als Objekt (AK4-PL-4)

Bei `schema_version="2.0"` MUSS `k_kopplung` in `per_ak` als **strukturiertes Objekt**
mit Ca/Ce/Instability ausgegeben werden — NICHT als monolithischer Skalar.

```yaml
# RICHTIG (Schema 2.0):
per_ak:
  AK-1:
    k_kopplung:
      ca: 5
      ce: 3
      instability: 0.375
    k_kopplung_components:
      - "Ca=5 via findReferences(GetByIdAsync)"
      - "Ce=3 via getCallHierarchy(GetByIdAsync)"

# VERBOTEN (Schema 2.0): monolithischer Skalar ohne Sub-Felder
per_ak:
  AK-1:
    k_kopplung: 40           # FAIL (INV-K1-Analogie)
```

### sdf_modus_input (AK4-PL-5)

Strukturierte Beobachtungsdaten, NIE Modus-Empfehlung. Detailspezifikation siehe
Sektion `## sdf_modus_input — Beobachtungs-Feld`. Bei `dark_factory=true` Pflicht;
bei `dark_factory=false` empfohlen. INV-MODUS-1/5 gelten unconditional.

### BL-161 + BL-160 Kompatibilitaet (AK4-PL-6)

| Constraint | Quelle | Form |
|------------|--------|------|
| `schema_version` immer String `"2.0"` (nicht Float `2.0`) | BL-161 (W8) | YAML-Loader-Konversion via `str()` (vgl. Sektion F PL-AK6-2) |
| `lsp_evidence`-Format = direkte BL-160-Provenance-Edge | BL-160 (W9) | `{file}:{line} via {lsp-tool}` — Format DARF NICHT abweichen |

### INV-K1-Guard (Pre-Write-Hook)

Vor Schreiben des `BERATER_OUTPUTS.kscore`-Blocks MUSS Validator pruefen:

```
IF schema_version == "2.0":
  ASSERT per_ak IS NOT EMPTY                       # AK4-PL-1
  ASSERT coupling_metrics has all 5 fields         # AK4-PL-1
  ASSERT aggregate.k_score_total IS NOT NULL       # AK4-PL-1
  ASSERT aggregate.weighting_scheme IS NOT NULL    # AK4-PL-1
  ASSERT aggregate.maturity_indicator IN [HIGH, MEDIUM, LOW]
  FOR EACH ak in per_ak:
    ASSERT ak.k_kopplung IS OBJECT WITH (ca, ce, instability)   # AK4-PL-4
    ASSERT ak.lsp_evidence MATCHES REGEX (AK4-PL-3)             # INV-LSP-1
  ASSERT NO field in [recommended_modus, sdf_mode, sdf_mode_hint,
                       expected_sdf_mode, mode_recommendation]    # AK4-PL-2
```

Verletzung jeder dieser Regeln = FAIL, **KEIN stiller Fallback**.

### Schema-1.0-Branch (Backwards-Compat)

Bei `schema_version="1.0"` gilt das Legacy-Schema (monolithischer `k_score`-Skalar
im K-SCORE.md-Frontmatter, kein `per_ak`/`coupling_metrics`-Pflicht). Branch-Logik
siehe Sektion `## Schema-Version-Branch (AK-6)`.

INV-COMPAT-1: Bestehende Legacy-Files bleiben unveraendert gueltig.

---

## Phase 3: Welle 3 — Synthese (K-SCORE.md schreiben)

1 Synthese-Agent (ceiling-Modell). Bei easy: Team Lead direkt.

### Synthese Worker-Vertrag

```
Du bist Synthese-Agent fuer die Komplexitaetsbemessung von "{NAME}".

INPUT — LIES ZUERST:
  1. .claude/specs/{NAME}_Spec.md (AK-Referenz)
  2. Alle Drafter-Outputs: .claude/analysis/drafts/{NAME}-K-D*.md
  {Bei easy: Explorer-Outputs ODER Spec + Model + Code direkt}

AUFTRAG:
  1. Konsolidiere alle Drafter-Scores (Deduplizierung, Konsistenz-Check)
  2. Berechne Gesamt-Aggregat (k_aufwand, k_kopplung, k_fragilitaet, k_score)
  3. Leite Labels ab (LOW/MEDIUM/HIGH)
  4. Schreibe K-SCORE.md

SCHREIB-PFLICHT (BL-050 Vault-First):
  PRIMAER: {VAULT}/Backlog/{BL_SLUG}/K-Score/{NAME}-K-SCORE.md
  FALLBACK: .claude/analysis/synthese/{NAME}-K-SCORE.md

FORMAT: Siehe K-SCORE.md Output-Format (unten)

VERBOTEN: Code-Editieren, Spec-Aendern, Model-Aendern. NUR KONSOLIDIEREN + Output schreiben.
```

---

## K-SCORE.md Output-Format

**Pfad (BL-050 Vault-First):**
  PRIMAER: `{VAULT}/Backlog/{BL_SLUG}/K-Score/{NAME}-K-SCORE.md`
  FALLBACK: `.claude/analysis/synthese/{NAME}-K-SCORE.md`

```markdown
---
feature: {NAME}
date: {DATUM}
type: k-score
version: 2.0
k_aufwand: {0-100}
k_kopplung: {0-100}
k_fragilitaet: {0-100}
k_score: {0-100}
aks_total: {N}
aks_kategorien: {NEU: n, BEARBEITEN: m, LOESCHEN: l}
hidden_complexity_count: {N}
pain_kombination_count: {N}
ak_details:                                # BL-142 RF-A5 (additiv)
  AK-001:
    srs_pro_ak: {0-100}
    k_score_pro_ak: {0-100}                 # BL-266: metricPlanner liest dies (Per-Batch K-Aggregation); ohne -> Story-Fallback
    spec_anchor: "{S-id}"
    model_refs: ["W{n}", ...]
    model_refs_status: {W{n}: open|confirmed|superseded}
    rf_refs: ["RF-{n}", ...]
  AK-002:
    srs_pro_ak: {0-100}
    k_score_pro_ak: {0-100}                 # BL-266: metricPlanner liest dies (Per-Batch K-Aggregation); ohne -> Story-Fallback
    spec_anchor: "{S-id}"
    model_refs: [...]
    model_refs_status: {...}
    rf_refs: [...]
---

# K-Score: {NAME}

**Erstellt:** {DATUM}
**AKs bewertet:** {N}
**Formeln-Version:** 2.0 (Gewichte: 40/35/25, Kopplung fuehrt — F3)

## Gesamt-Aggregat

| Metrik | Score | Gewicht | Gewichtet |
|--------|-------|---------|-----------|
| Aufwand | {0-100} | 0.40 | {wert} |
| Kopplung | {0-100} | 0.35 | {wert} |
| Fragilitaet | {0-100} | 0.25 | {wert} |
| **K-Score** | | | **{0-100}** |
| **Label** | | | **{LOW/MEDIUM/HIGH}** |

## AK-Kategorien

| Kategorie | Anzahl | Anteil |
|-----------|--------|--------|
| NEU | {n} | {%} |
| BEARBEITEN | {m} | {%} |
| LOESCHEN | {l} | {%} |

## Pro-AK Detail

| AK-ID | Beschreibung | Kat. | srs | Aufwand | Kopplung | Quadrant | Fragilitaet | K-Score | Hidden | Pattern | W-Penalty |
|-------|-------------|------|-----|---------|----------|----------|-------------|---------|--------|---------|-----------|
| AK-001 | {kurz} | NEU | {0-100} | {0-100} | {0-100} | Q0 | {0-100} | {0-100} | — | {ja/nein} | {%} |
| AK-002 | {kurz} | BEARB | {0-100} | {0-100} | {0-100} | Q1-Q4 | {0-100} | {0-100} | {ja/nein} | {ja/nein} | {%} |
| ... | | | | | | | | | | |

## Pro-AK Anker (BL-142 RF-A5, additiv)

Pro-AK persistiert: srs_pro_ak (Epistemik-Score [BL-205]), k_score_pro_ak (K-Score pro AK [BL-266],
= round(per_ak.k_score_ak) bzw. round(k_score(ak)) — dieselbe Skala wie das Story-Aggregat),
spec_anchor (Section-ID in Spec), model_refs (W{n}-Anker im Model), model_refs_status (W{n}-Status pro
Anker — MUSS den ECHTEN Status inkl. experiment_provable fuehren, srs_conventions AK-5, nicht nur
open/confirmed/superseded; speist w_status_set [BL-266]), rf_refs (RF-IDs).
Konsumenten: /_backlog (BL-Frontmatter), /_A_berater_akExtraktion (Per-AK-Detailausarbeitung, BL-209 Single-Source — NICHT der deprecated IDF-Zwilling _IDF_berater_akExtraktion [BL-268]),
/_IDF_berater_metricPlanner (k_score_pro_ak → metric_per_batch.k_score_avg/max; model_refs_status → w_status_set [BL-266]).

> [BL-205] srs_pro_ak = w_offen / w_total × 100 (Epistemik-Score, orthogonal zu K-Score)
> w_offen = OPEN model_refs dieser AK; w_total = alle model_refs dieser AK.
> Bei fehlenden model_refs → PRIMAER-Heuristik (Typ-Tabelle in Berechnungs-Hinweise).

| AK-ID | srs_pro_ak | spec_anchor | model_refs | model_refs_status | rf_refs |
|-------|-----------|------------|-----------|------------------|---------|
| AK-001 | {0-100} | {S-1.2} | [W3, W7] | {W3:confirmed, W7:open} | [RF-1, RF-2] |
| AK-002 | {0-100} | {S-2.4} | [W11] | {W11:open} | [RF-3] |
| ... | | | | | |

### Per-AK YAML-Struktur (im Frontmatter additiv)

```yaml
ak_details:
  AK-001:
    srs_pro_ak: 35
    k_score_pro_ak: 48
    spec_anchor: "S-1.2"
    model_refs: ["W3", "W7"]
    model_refs_status:
      W3: "confirmed"
      W7: "open"
    rf_refs: ["RF-1", "RF-2"]
  AK-002:
    srs_pro_ak: 62
    k_score_pro_ak: 71
    spec_anchor: "S-2.4"
    model_refs: ["W11"]
    model_refs_status:
      W11: "open"
    rf_refs: ["RF-3"]
```

### Berechnungs-Hinweise (BL-142 RF-A5, BL-205 AK-1/2/3 Refactor)

```
srs_pro_ak (Epistemik-Score, 0-100) [BL-205]:
  DEFINITION (BL-205 S-2, kanonisch):
    w_refs_active = model_refs dieser AK OHNE status=RETRACTED
    IF len(w_refs_active) == 0:
      srs_pro_ak = 100  # no_truth_refs — maximale Unsicherheit
    ELSE:
      srs_pro_ak = (sum(srs_weight[w.status] for w in w_refs_active) / len(w_refs_active)) × 100

    srs_weight (Angleich an _srs_compute.md srs_weight — Single-Source-Vokabular, BL-269):
      BESTAETIGT | BESTAETIGT-DB | STABLE | AKTIV (BESTAETIGT) | RESOLVED | RESOLVED-DB | CLOSED → 0.0
      TENTATIV | HYPOTHESE | OFFEN → 1.0
      experiment_provable → 1.0   # BL-239: nur-experimentell-schliessbare Wahrheit (max. Unsicherheit, srs_compute:46)
      RETRACTED → ausgeschlossen (zaehlt nicht im Nenner)

    Kurzform: srs_pro_ak ≈ w_offen / w_total × 100 (binaere Gewichtung)
    - w_offen: Anzahl unsicherer Wahrheiten (TENTATIV/HYPOTHESE/OFFEN)
    - w_total: Gesamtzahl aktiver Wahrheiten (OHNE RETRACTED)
    - Eigenschaft: orthogonal zu K-Score (keine gemeinsamen Inputs)
    - Wertebereich: 0 (alle bestaetigt) bis 100 (alle offen oder keine Refs)

  PRIMAER-Heuristik (wenn model_refs fehlen — Schnell-Schaetzung):
    AK = pure Markdown-Doku ohne Code        → srs 5-10
    AK = klares Code-Schema, Standard-Pattern → srs 20-30
    AK = Code mit Open Questions/neuem Pattern → srs 50-70
    AK = Forschung / explorativ / OQ-Gates    → srs 80+
    AK = Migration mit Cross-Cutting-Risiko   → srs 60-80

  FALLBACK (wenn per-AK Formeln nicht berechnet):
    srs_pro_ak = null  — Konsumenten greifen auf globalen srs_score zurueck
    (Backwards-Compat: fehlende srs_pro_ak ≠ Fehler — Heuristik ist optional)

  Hoehere Werte → mehr epistemische Unsicherheit bei dieser AK

  INTERN/EXTERN-ROUTING (AK-3, BL-205):
    hohe SRS (>= 60) + Intern-AK  → SC-FULL (Scientific-Cycle)
    hohe SRS (>= 60) + Extern-AK  → WP (Working-Paper / Recherche)
    niedrige SRS (< 60)            → Standard-SDF-Routing (M1..M3 per modusEntscheidung)
    Routing-Entscheidung BLEIBT bei _SDF_berater_modusEntscheidung (INV-MODUS-1)

spec_anchor:
  Section-ID aus Spec.md Header (z.B. "S-1.2", "AK-S-3" — frei waehlbar je Spec-Format)
  Default: "S-{n}" wenn AK keine eigene Section hat

model_refs:
  Liste der W{n}-IDs aus Model.md, die diese AK referenzieren
  Aus E02 Explorer-Output (model-konfidenz Fokus)

model_refs_status:
  Pro W{n}-Ref der ROHE Status via truth_consume.value(ref, bl_folder=BL_SLUG, vault_root=VAULT).status
  (BL-387: statt Model-Frontmatter frei; source=atomic-first, legacy-fallback. BL-269: KEIN reduziertes Mapping).
  Werte: das VOLLE W-Status-Vokabular (srs_conventions AK-5, 12 Werte) — open | confirmed | superseded |
         experiment_provable | TENTATIV | HYPOTHESE | OFFEN | BESTAETIGT | RETRACTED | ... — VERBATIM kopiert,
         damit kategorie-tragende Status (v.a. `experiment_provable`) erhalten bleiben.
  Konsument: IDF/SDF — open W{n} → Pruning/Modus-Hint; `experiment_provable` speist w_status_set
             (_IDF_berater_metricPlanner, BL-266) → modusEntscheidung 4.5a → M5-Kategorie-Trigger (BL-239 AK-2).
  WICHTIG (BL-269): das frühere reduzierte {open|confirmed|superseded} liess experiment_provable fallen →
             der M5-Trigger war an der Quelle tot. Jetzt: rohen Status führen.

rf_refs:
  Liste der RF-IDs aus Spec.md, die diese AK adressiert
  Aus E01 Explorer-Output (spec-extraktion Fokus)
  Bidirektionale Verbindung: rf_refs (AK→RF) komplementiert refs (RF→AK)
```

## Wahrheits-Status-Konvention (AK-5, BL-205 S-5) — KANONISCH

Alle zulaessigen Status-Werte fuer `W{n}` in Model.md. Freie Strings sind VERBOTEN.
Validierung: Pre-Write-Hook oder `_IDF_berater_validator`.

| Status | Kategorie | SRS-Gewicht | Bedeutung |
|--------|-----------|-------------|-----------|
| BESTAETIGT | Sicher | 0.0 | Durch Code/Test bestaetigt |
| BESTAETIGT-DB | Sicher | 0.0 | Durch Datenbank-Beleg bestaetigt |
| STABLE | Sicher | 0.0 | Langfristig stabil |
| AKTIV (BESTAETIGT) | Sicher | 0.0 | Aktiv und bestaetigt |
| RESOLVED | Sicher | 0.0 | Offene Frage geklaert |
| RESOLVED-DB | Sicher | 0.0 | Offene Frage durch DB-Beleg geklaert |
| CLOSED | Sicher | 0.0 | Abgeschlossen |
| TENTATIV | Unsicher | 1.0 | Vorlaeufige Annahme |
| HYPOTHESE | Unsicher | 1.0 | Theorie, noch nicht verifiziert |
| OFFEN | Unsicher | 1.0 | Ungeklaert, Klaerungs-Bedarf |
| RETRACTED | Ausgeschlossen | n/a | Zurueckgezogen, zaehlt nicht im Nenner |

> Lebenszyklus: OFFEN → (SC/WP) → RESOLVED/BESTAETIGT oder RETRACTED

## SRS Resolve-Strategie + Source-Klassifikation (AK-6, BL-205 S-3/S-4)

### SRS pro Granularitaet

```
SRS_pro_AK:
  w_refs = K-SCORE.md "W-Refs"-Spalte fuer diese AK ODER AK.model_refs aus BERATER_OUTPUTS
  Status pro W{n}: Model.md Frontmatter ODER inline "status:"-Marker

SRS_pro_PL:
  Wenn PL hat AK-Anker: w_refs = SRS_pro_AK.w_refs (Vererbung)
  Sonst (Drift/Twin/Manual PL ohne AK-Anker): w_refs = [] → SRS=100, flag="no_truth_refs"

SRS_batch:
  SRS_batch = MAX(SRS_pl for pl in batch)
  Begruendung: MAX statt AVG — eine unsichere PL macht ganzen Batch unsicher

SRS_global (W-Status via truth_consume.srs_for(all_w_refs, bl_folder=BL_SLUG, vault_root=VAULT) source=atomic-first):
  SRS_global = (w_offen_total / w_total) × 100
  w_offen_total = count(W{n} WHERE truth_consume.is_open(W{n}) == True)   # entspricht status IN [TENTATIV, HYPOTHESE, OFFEN]
  w_total = count(W{n} WHERE truth_consume.value(W{n}).status != RETRACTED)
  # srs_for(refs) liefert die SRS-View direkt + unresolved_refs (lautes Signal, kein stiller Default)
```

### W{n}.source Klassifikation (PL-AK6-1, BL-205 S-4)

`W{n}.source` bestimmt ob eine unsichere Wahrheit intern klaerbar ist (SC) oder externe Recherche braucht (WP).

**INTERN** (SC-klaerbar):
- `"Repo: ..."` — Code-Analyse im Repo
- `"Crumbs: ..."` — Vault-Recherche (Crumbs-Dateien)
- `"Assays: ..."` — Vault-Recherche (Assay-Dateien)
- `"W_fetch: ..."` — bereits gefetcht, lokal verfuegbar

**EXTERN** (WP erforderlich, nicht durch SC klaerbar):
- `"Wiki: ..."` — externe Dokumentation
- `"URL: https://..."` — externe Online-Quelle
- andere Story-ID — externer Pointer
- `"Stakeholder: ..."` — User-Decision pending
- `"Industry-Standard: ..."` — externes Regelwerk

### Bottleneck-Routing-Signal (pro PL-Item, KEIN Modus-Vorschlag)

```
unsicher_intern_count = count(w WHERE w.source INTERN AND srs_weight[w.status] == 1.0)
unsicher_extern_count = count(w WHERE w.source EXTERN AND srs_weight[w.status] == 1.0)

IF unsicher_extern_count > 0:  bottleneck_signal = "WP"
ELIF unsicher_intern_count > 0: bottleneck_signal = "SC"
ELSE:                           bottleneck_signal = null  # SRS=0, kein Bottleneck
```

> Routing-Entscheidung BLEIBT bei `_SDF_berater_modusEntscheidung` (INV-MODUS-1).
> `bottleneck_signal` = Beobachtung fuer SDF Phase 1.1, KEIN bindender Modus-Vorschlag.

## K-Score Penalty — Invariante (AK-4, BL-205)

> Die K-Score Penalty-Berechnung bleibt UNVERAENDERT durch BL-205:
> ```
> penalty = 1.0 + (w_offen_bezug / max(w_bezug, 1)) × 0.5
> aufwand_final(ak) = aufwand_norm(ak) × penalty
> ```
> BL-205 aendert NUR die SRS-Formel (Epistemik-Score, orthogonal).
> K-Score-Formel, Penalty, Gewichte (40/35/25) — alles unveraendert. [INV-K-PENALTY-1]

## Konfidenz-Info

| Metrik | Wert |
|--------|------|
| W{n} gesamt (Model) | {N} |
| W{n} BESTAETIGT | {N} ({%}) |
| W{n} OFFEN | {N} ({%}) |
| Max Penalty angewandt | {%} |

## Daten-Output (NICHT: Modus-Empfehlung)

> **PROZESS-INVARIANTE (BL-162 AK-7, F98 verschaerft 2026-05-08):**
> K-Score liefert **NUR Daten** (k_aufwand, k_kopplung, k_fragilitaet, k_score, k_label).
> **VERBOTEN:** Modus-Vorschlag M1..M9, "Empfohlener Modus", "SDF-Empfehlung".
>
> **Begruendung:** Alleinige Modus-Quelle ist `_SDF_berater_modusEntscheidung`
> (SDF Phase 1.1, C3-Opus). Diese aggregiert K-Score + SRS + Gap + batch_items
> selbst und entscheidet M1..M9 in einem nachvollziehbaren C3-Schritt.
>
> **Anti-Pattern (gefangen DCSRE-486 2026-05-08):** Wenn K-Score eine
> Modus-Tabelle haette, koennten IDF/SDF-Worker die Empfehlung kopieren und
> C3 ueberspringen. Tabelle ist daher hier bewusst entfernt.
```

---

## Goodhart/Screening-Guard: K-Score-Skalar ist NIE alleiniges Urteil (BL-381 AK-5)

> **DOKTRIN (BL-381 AK-5, analog `EVAL_FINDING_FORBIDDEN_PASSFAIL`):**
> Der K-Score-**Skalar** (`k_score`/`k_aufwand`/`k_kopplung`/`k_fragilitaet`, 0-100) ist ein
> **SCREENING-Layer, NIE das aktionierbare Urteil.** Das aktionierbare Urteil traegt die
> **Risiko-Klasse + Cost/Benefit** (AK-4, eval_finding-Record) zusammen mit den begleitenden
> getrennten Achsen (DL/PC, Co-Commit, Kopplungs-Dimensionen). Ein K-Score-Konsum, der NUR den
> Skalar (ohne begleitende Achsen / ohne risk_class) als Go/No-Go-Entscheidung nutzt, ist eine
> **Verletzung** — er reproduziert exakt das von Kazman (CMU/SEI-2020-TR-006) diskreditierte
> Single-Maintainability-Index-Antimuster ("not actionable", W-DOM-1).

**Vorbild (Strukturspiegel):** `EVAL_FINDING_FORBIDDEN_PASSFAIL` (`quality_model_wform.py:77`, BL-383)
verbietet ein binaeres PASS/FAIL-Verdikt als Primaer-Output am eval_finding-Record. Diese Klausel ist
die K-Score-Analogie: das **Goodhart-Gesetz** ("wird eine Metrik zum Ziel, taugt sie nicht mehr als
Metrik") — der K-Score-Skalar darf nicht zum alleinigen Steuer-Ziel werden.

**Die 3 bestehenden Stuetz-Schichten (diese Klausel ergaenzt die fehlende Skalar-Klausel, W-AK5-2):**
1. **INV-MODUS-1** (CLAUDE.md) — der K-Score traegt KEINE Modus-Empfehlung; die alleinige Modus-Quelle
   ist `_SDF_berater_modusEntscheidung` (SDF Phase 1.1). Deckt aber NUR Modus-Felder, NICHT "Skalar als
   alleinige Entscheidung" (genau die Luecke, die diese AK-5-Klausel schliesst).
2. **BL-380 W-GH-1** — `response_measure.method` als Schema-Pflichtfeld zwingt eine Mess-Methode neben
   jede Metrik (Goodhart-Schutz auf der Qualitaetsszenario-Ebene).
3. **BL-174 INV-DERIV-1** — `guard_metric_derivation.py` erzwingt Ableitungs-Transparenz (jeder
   Score-Wert braucht `*_components`); ein hand-waved Skalar ist bereits FAIL.

**Konform vs Verletzung (Entscheidungs-Regel):**
- KONFORM: K-Score-Skalar wird als Screening/Triage gelesen UND die Entscheidung stuetzt sich auf die
  begleitenden Achsen (DL/PC, Co-Commit, Kopplungs-Dimensionen) + die Risiko-Klasse/Cost-Benefit (AK-4).
- VERLETZUNG: ein Konsument leitet ein Go/No-Go, eine Priorisierung oder einen Modus allein aus dem
  Skalar ab (z.B. "k_score > 66 -> ablehnen") OHNE begleitende Achsen/risk_class.

**Form:** Diese Klausel ist primaer **Doktrin/Vertrag** (markdown_uncoverable, W-AK5-2). Ein optionaler
struktureller Hook/Validator (analog `check_eval_finding_block`), der einen Skalar-allein-Konsum
maschinell blockt, ist laut Spec NICHT erzwungener Scope — er ist erlaubt, sobald ein klar testbarer
Konsum-Kontext existiert. Bis dahin gilt die Klausel als Konsum-Disziplin (wie die `not_writes`-Liste).

---

## not_writes (Worker-Vertrag, AK-7 + INV-MODUS-5)

Der K-Score-Worker **DARF NIE** folgende Felder schreiben:

### Verbotene Feld-Namen (unconditional)

- `recommended_modus`
- `sdf_mode`
- `sdf_mode_hint`
- `expected_sdf_mode`
- `mode_recommendation`

### Verbotene Prosa-Pattern (Regex)

Der K-SCORE.md Body darf keinen Treffer auf folgende Patterns enthalten:

- `/Empfehlung\s+M[1-9]/` — z.B. "Empfehlung M5"
- `/recommend.*M[1-9]/` — z.B. "we recommend M3"
- `/naechster\s+Modus/` — z.B. "naechster Modus: M2"
- `/Standard.*Pipeline/` — z.B. "Standard IDF+SDF Pipeline"

### Strukturelle Invarianten

- `k_score` als monolithischer Einzel-Skalar OHNE `per_ak` ist VERBOTEN
  bei `schema_version="2.0"` (INV-K1).
- Jeder numerische Score-Wert MUSS mindestens 1 `*_components`-Eintrag haben
  (INV-DERIV-1). Hand-waved Werte ohne Herleitung sind FAIL.

Verletzung jeder dieser Regeln = Worker-FAIL, KEIN stiller Fallback.

---

## SRS-Formel-Migration (AK-9, BL-205) — srs_formula_v2_migrated Flag

### Flag-Spec in A_PIPELINE_STATE

```yaml
A_PIPELINE_STATE:
  srs_formula_v2_migrated: true | false | null
  # true  = srs_pro_ak-Werte nach Epistemik-Formel (BL-205, w_offen/w_total × 100)
  # false = srs_pro_ak-Werte nach alter Formel (kopplung_norm × 0.5 + ...)
  # null  = unbekannt / vor BL-205 (behandeln wie false)
```

### Lazy-Migration-Strategie (BL-205 AK-9)

Bestehende K-SCORE.md Dateien mit `srs_pro_ak`-Werten nach alter Formel werden
NICHT rueckwirkend migriert. Migration erfolgt beim naechsten A-Pipeline-Lauf der
betreffenden BL (Natural Refresh).

```
IF A_PIPELINE_STATE.srs_formula_v2_migrated == true:
  → srs_pro_ak-Werte sind valide nach Epistemik-Formel
  → IDF.metricPlanner kann direkt aggregieren
ELIF A_PIPELINE_STATE.srs_formula_v2_migrated IN [false, null]:
  → srs_pro_ak-Werte sind nach alter Formel (zirkulaer mit K-Score)
  → IDF.metricPlanner WARN: "srs_pro_ak aus Legacy-Formel — Vertrauensgrad niedrig"
  → SDF Phase 1.1 fallback auf globalen srs aus A_PIPELINE_STATE.srs (Heuristik)
```

### BLs mit Legacy-srs_pro_ak (vor BL-205)

Alle BLs die vor 2026-05-24 einen A-Pipeline-Lauf hatten haben `srs_formula_v2_migrated=null`.
Identifizierbar via: `A_PIPELINE_STATE.timestamp_completed < 2026-05-24`.
Aktiv-Arbeit: BL-197, BL-198 haben srs=0 (keine model_refs) — nicht betroffen.

---

## sdf_modus_input — Beobachtungs-Feld (KEINE Empfehlung)

Der K-Score-Worker schreibt in `BERATER_OUTPUTS.kscore.sdf_modus_input` ausschliesslich
strukturierte Beobachtungsdaten — niemals Modus-Empfehlungen oder Pipeline-Namen.

### Pflicht-Struktur

```yaml
sdf_modus_input:
  k_score_total: {Zahl}                    # Aggregat-Score
  high_coupling_components:                # Komponenten mit I > 0.7
    - {ComponentName}
  fragility_drivers:                       # k_fragilitaet-Treiber-Liste
    - {Beobachtung als Kurzform}
  # Pflicht-Kommentar:
  # "Beobachtungen, KEINE Empfehlung. SDF Phase 1.1 interpretiert."
```

### Was hier NICHT erlaubt ist

- `modus: "M{N}"` oder `recommended_modus: "M{N}"`
- Prosa-Empfehlungen ("eignet sich fuer SC-FULL", "Standard-Pipeline reicht")
- `pipeline_hint`, `sdf_mode`, `mode_recommendation` (vgl. `not_writes`)

SDF Phase 1.1 (`_SDF_berater_modusEntscheidung`) ist die alleinige Modus-Quelle (INV-MODUS-1).

---

## Schema-Version-Branch (AK-6 — Backwards-Kompatibilitaet)

Der Worker liest in Phase 0 das Feld `schema_version` (String) aus `session_params`
oder `_manifest.md` (Default: `"2.0"` ab BL-162).

### Branch-Logik (PL-AK6-1)

```
schema_version = read_session_param("schema_version", default="2.0")

IF schema_version == "1.0":
  # Legacy-Modus
  worker_mode = "legacy_1.0"
  4_schritt_walk_required = FALSE
  per_ak_required = FALSE
  coupling_metrics_required = FALSE
  lsp_evidence_required = FALSE
  # Bestehender Output (Z468-629 Template, monolithischer k_score-Skalar) ist gueltig.
ELSE IF schema_version == "2.0":
  # Schema-2.0-Modus (siehe Pflicht-Walk / LSP-Pflicht-Protokoll / Coupling-Metriken / Evidence-Edges)
  worker_mode = "schema_2.0"
  4_schritt_walk_required = TRUE
  per_ak_required = TRUE
  coupling_metrics_required = TRUE
  lsp_evidence_required = TRUE
ELSE:
  FAIL "Unbekannte schema_version: {schema_version}"
```

### String-vs-Zahl-Vergleich (PL-AK6-2)

`schema_version` ist **immer String** (`"1.0"`, `"2.0"`). YAML-Loader die das Feld
als Float interpretieren MUESSEN explizit auf String konvertiert werden:

```python
schema_version = str(yaml_value["schema_version"])   # immer als String behandeln
```

Vergleich `schema_version == 2.0` (Float) ist VERBOTEN. Worker-Validierung muss
`schema_version == "2.0"` (String) sicherstellen.

### Forward-Compat-Kennzeichnung (PL-AK6-3, optional)

Legacy-K-SCORE.md-Dateien (vor BL-162) haben kein `schema_version`-Feld. Solche
Dateien werden als `schema_version="1.0"` interpretiert (Default-Fallback).

**Empfehlung:** Bestehende Legacy-Files DUERFEN freiwillig mit
`schema_version: "1.0"` annotiert werden, um Default-Drift zu vermeiden.
Dies ist **nicht verpflichtend** (INV-COMPAT-1: Legacy bleibt unveraendert gueltig).

### OUT-OF-SCOPE-Vermerk (PL-AK6-4, INV-SCOPE-1)

Ein Migration-Tool `1.0 → 2.0` ist **OUT OF SCOPE** fuer BL-162. Es wird NICHT
geliefert. Legacy-Files bleiben Schema 1.0 — keine automatische Konvertierung.
Manuelle Re-Generierung mittels `/_K_score` mit `schema_version="2.0"` ist der
empfohlene Weg.

---

## Phase 3.5: Circuit-Breaker (BL-129 AK-10 Migration, 2026-04-18)

```
# K-Threshold-Guard — migrierte _gap-Funktion
k_score_label = aus k_score ableiten
k_breaker_threshold = 80  # K-Score-Schwelle analog _gap 81-100% KRITISCH

IF k_score > k_breaker_threshold:
  IF GLOBAL_HIL == "off":
    Logge WARNUNG: "[CIRCUIT-BREAKER] k_score={k_score} > {k_breaker_threshold}. Pipeline faehrt fort (HiL=off)."
    # Kein Abbruch — nur Warnung. Caller (SDF/BDF) kann entscheiden.
    Manifest: A_PIPELINE_STATE.k_circuit_breaker = "WARN(K>80+HiL=off)"
  ELSE:
    Logge FEHLER: "[CIRCUIT-BREAKER] k_score={k_score} > {k_breaker_threshold}. HiL-Entscheidung erforderlich."
    AskUserQuestion: "K-Score={k_score} (KRITISCH). Trotzdem fortfahren?
      [FORTFAHREN] K akzeptieren, Pipeline weiter
      [MITOSE]     Feature splitten (if k > 100: Mitose-Empfehlung)
      [ABORT]      Pipeline stoppen"
    Manifest: A_PIPELINE_STATE.k_circuit_breaker = "{user-decision}"
ELSE:
  Manifest: A_PIPELINE_STATE.k_circuit_breaker = "GREEN"
```

---

## Phase 4: Manifest + Monitoring Update

```
# K-SCORE.md lesen
k_score_data = lies(".claude/analysis/synthese/{NAME}-K-SCORE.md")

# Manifest aktualisieren (4 neue K-Felder)
Schreibe in _manifest.md → A_PIPELINE_STATE:
  k_aufwand: {k_score_data.k_aufwand}
  k_kopplung: {k_score_data.k_kopplung}
  k_fragilitaet: {k_score_data.k_fragilitaet}
  k_score: {k_score_data.k_score}
  k_label: {k_score_data.k_label}
  k_date: {DATUM}

# Monitoring-Anzeige (wie SRS)
Logge: "=== K-SCORE BERECHNET ==="
Logge: "┌──────────────────────────────────────┐"
Logge: "│ K-Score: {k_score} ({k_label})       │"
Logge: "│   Aufwand:     {k_aufwand}           │"
Logge: "│   Kopplung:    {k_kopplung}           │"
Logge: "│   Fragilitaet: {k_fragilitaet}        │"
Logge: "│ AKs: {N} ({NEU}N/{BEARBEITEN}B/{LOESCHEN}L) │"
Logge: "└──────────────────────────────────────┘"
# F98 verschaerft 2026-05-08: KEIN "SDF-Empfehlung: {modus}" mehr.
# K-Score liefert NUR Daten — Modus entscheidet C3 in SDF Phase 1.1.

# --- KLAERUNGSBEDARF (AK-K-024, F-NEU-6) ---
# K-Messung ist der LETZTE Moment fuer Dialog VOR Implementierung.
# Wenn Unklarheiten erkannt → in K-SCORE.md dokumentieren.
klaerungsbedarf = []
FUER JEDEN ak IN ak_liste:
  IF ak hat KEINEN W{n}-Bezug im Model:
    klaerungsbedarf.append("AK-{ak.id}: Kein W{n}-Bezug im Model — Model-Luecke (AK-K-027)")
  IF ak.kopplung_score > 70 AND ak.kategorie == "BEARBEITEN":
    klaerungsbedarf.append("AK-{ak.id}: Hohe Kopplung ({ak.kopplung}) bei BEARBEITEN — Risiko-Klaerung empfohlen")
  IF ak.konfidenz_penalty > 1.3:
    klaerungsbedarf.append("AK-{ak.id}: Hohe Unsicherheit (Penalty {ak.penalty}) — offene W{n} klaeren")

IF |klaerungsbedarf| > 0:
  Logge: "=== KLAERUNGSBEDARF ({|klaerungsbedarf|} Punkte) ==="
  FUER punkt IN klaerungsbedarf:
    Logge: "  ! {punkt}"
  # Schreibe Klaerungsbedarf in K-SCORE.md Sektion "Klaerungsbedarf"
  # Bei HiL=off: NUR loggen (kein AskUserQuestion)
  # Bei HiL=cycle: AskUserQuestion mit Klaerungsbedarf-Liste

# --- KALIBRIERUNG: Vorhersage speichern (AK-K-028, F-NEU-1) ---
# K-Score-Vorhersage wird gespeichert fuer spaetere Kalibrierung.
# Nach Implementierung: Tatsaechlicher Aufwand → Vergleich → Gewichte anpassen.
Schreibe in _manifest.md → A_PIPELINE_STATE:
  k_vorhersage: {k_score}
  k_vorhersage_datum: {DATUM}
  k_vorhersage_aks: {|ak_liste|}
  # Nach Implementierung (in /_finish oder /_SC_ergebnis):
  #   k_tatsaechlich: {gemessener Aufwand}
  #   k_kalibrierung_delta: k_vorhersage - k_tatsaechlich
  #   → Positiv = ueberschaetzt, Negativ = unterschaetzt
  #   → Gewichte anpassen wenn |delta| > 20% ueber 3+ Features

# Handschuh zurueck an Aufrufer (A-Pipeline oder SDF)
Logge: "/_K_score DONE. Handschuh zurueck."
RETURN
```

---

## ANTI-PATTERN Guard

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERBOTEN:                                                           ║
║    Code editieren (KEIN Write/Edit auf .cs/.ts/.md-Commands)        ║
║    Spec aendern (NUR /_spec schreibt Specs)                         ║
║    Model aendern (NUR /_model/_SC_modelMaintain schreibt Models)    ║
║    Labels direkt setzen ohne Score (IMMER Score → Label ableiten)   ║
║    K-Score fuer Modi-Entscheidung treffen (das macht SDF)           ║
║                                                                      ║
║  RICHTIG:                                                            ║
║    NUR lesen (Spec, Model, Code, Patterns)                          ║
║    NUR berechnen (Formeln anwenden)                                  ║
║    NUR schreiben: K-SCORE.md + Manifest K-Felder                    ║
║    Labels aus Score ABLEITEN (nicht umgekehrt)                      ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## QUICK-START

```
1. /_K_score {NAME}
2. Phase 0: Spec lesen, AKs extrahieren
3. Phase 1 (W1): 5 Explorer lesen Spec+Model+Code+Patterns+Abhaengigkeiten
4. Phase 2 (W2): 3 Drafter berechnen Aufwand+Kopplung+Fragilitaet+Aggregat
5. Phase 3 (W3): 1 Synthese konsolidiert → K-SCORE.md
6. Phase 4: Manifest K-Felder setzen, Monitoring-Anzeige
7. RETURN (Handschuh zurueck an A-Pipeline oder SDF)
```

---

## Akzeptanzkriterien

| AK-ID | Kriterium | Status |
|-------|-----------|--------|
| AK-K-001 | Command VERTRAG-Block mit LIEST/SCHREIBT | ✓ |
| AK-K-002 | AK-Kategorisierung NEU/BEARBEITEN/LOESCHEN | ✓ |
| AK-K-003 | Aufwand-Berechnung numerisch (0-100) | ✓ |
| AK-K-004 | Kopplung-Berechnung Fan-In/Out (0-100) | ✓ |
| AK-K-005 | Fragilitaet-Berechnung (0-100) | ✓ |
| AK-K-006 | Pattern Library Lookup mit Modifikatoren | ✓ |
| AK-K-007 | W{n}-Konfidenz-Penalty | ✓ |
| AK-K-008 | Aggregat-Score 40/35/25 (revidiert, Kopplung fuehrt) | ✓ |
| AK-K-009 | K-SCORE.md Output-Format | ✓ |
| AK-K-010 | Wellen-Architektur 5-3-1 | ✓ |
| AK-K-019 | Kalibrierung (Vorhersage speichern) | ✓ |
| AK-K-020 | Testbarkeit-Dimension | ✓ |
| AK-K-021 | Parallelisierbarkeits-Modifikator | ✓ |
| AK-K-024 | Dialog-Fragen aufwerfen (Klaerungsbedarf) | ✓ |
| AK-K-025 | Kohaesion messen | ✓ |
| AK-K-027 | Model-Luecken als Signal | ✓ |
| AK-K-028 | K-Score Vorhersage speichern | ✓ |
| AK-K-029 | Per-AK ak_details persistieren (BL-142 RF-A5) | ✓ (additiv) |
| AK-K-030 | srs_pro_ak + spec_anchor + model_refs + model_refs_status + rf_refs | ✓ (additiv) |

---

## NOTIFY (Pflicht - Allerletzter Schritt)

```bash
powershell -Command "notify '{NAME} /_K_score abgeschlossen — K-Score: {k_score} ({k_label})'"
```
