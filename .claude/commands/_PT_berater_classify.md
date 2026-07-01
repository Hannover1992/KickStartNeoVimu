# _PT_berater_classify (Pattern-Extraction Stage 5)

```yaml
type: berater
status: active
version: 1.1.0
created: 2026-06-02
updated: 2026-06-08
op: PatternExtraction
phase: "5"
chain_position: "fuenfte Stage in _PT_orchestrate — nach contradiction, vor forensic"
feature_anchor: BL-237 (AK-4: Achsen-Diskriminator orthogonal, Tie-Break Pflicht) + BL-257 (4. Achse factoring)
model_tier: ceiling  # opus — Klassifikations-Urteil (4 orthogonale Achsen)
```

## Zweck (EIN Job)

**Klassifiziere jedes Cluster-Signal auf 4 ORTHOGONALEN Achsen.** Das ist die zentrale 4-Achsen-Zuweisung
(BL-237 AK-4 + BL-257): ein Signal kann gleichzeitig eine semantische, eine architektonische, eine fachliche
UND eine **factoring** (Refactoring-Transformations-)Dimension tragen — die Achsen sind **nicht hierarchisch**
und kein Signal verschwindet, weil eine Achse "staerker" wirkt. Insbesondere geht die **FACHLICHE** Achse NICHT
in der semantischen unter, und **factoring** (die Struktur-TRANSFORMATION) geht NICHT in architektonisch (dem
statischen Struktur-ZUSTAND) unter.

> **Single Unit of Work (/_help P-10):** liest .clustering + .contradiction, klassifiziert auf 4 Achsen,
> schreibt EINEN eigenen Slot (.classify), stirbt. Keine Materialisierung (→ Stage 7), keine Forensik
> (→ Stage 6), kein Library-Write.

## Die 4 orthogonalen Achsen

| Achse | Diskriminator | Quelle | Beispiel |
|---|---|---|---|
| **semantisch** | Naming/Vokabular/Ausdrucks-Konvention | `_SCOPE_LIB` semantic-Map (reuse) | "Orchestrator immer `_X_orchestrate`-Prefix" |
| **architektonisch** | Struktur/Layer/Kopplung/Schichtgrenze (statischer ZUSTAND) | `_SCOPE_LIB` arch-Layer-Map (reuse) | "Berater schreibt nur EINEN Slot (Single-Writer)" |
| **FACHLICH** (domain) | Domaenen-Begriff/Geschaeftsregel | Domain-Diskriminator (batch_C1) | "Reife-Counter: confirm vs. contradiction" |
| **factoring** (refactoring) | Struktur-TRANSFORMATION / Refactoring-Bewegung (vorher→nachher: extract/inline/declarativize/dedup/move) | `_SCOPE_LIB` factoring-Map + git-diff (forensic) | "imperativ→deklarativ: setValidators-Aufrufe → buildValidatorMap" |

**Orthogonalitaet:** ein Signal kann auf 0..4 Achsen zugleich liegen. Achsen-Zuweisung ist additiv, nicht
ausschliessend. **architektonisch vs factoring (der subtile Schnitt):** architektonisch = der statische
Struktur-ZUSTAND ("ist ein Single-Responsibility-Handler"); factoring = die TRANSFORMATION, die ihn erzeugte
("Glue-Methoden in den Handler extrahiert, vorher dupliziert"). Beide koennen auf demselben Signal liegen.

## Tie-Break (PFLICHT — B-3)

Bei mehrdeutiger Achsen-Zuordnung (ein Signal koennte zu zwei Achsen gehoeren) MUSS deterministisch
aufgeloest werden — nie zufaellig:

```
TIE-BREAK-REGEL (deterministisch, dokumentationspflichtig):
  1. FACHLICH gewinnt NIE automatisch unter semantisch — bleibt eigene Achse (AK-4-Kern).
     factoring gewinnt NIE automatisch unter architektonisch — bleibt eigene Achse (BL-257-Kern).
  2. Liegt ein Signal auf mehreren Achsen → es wird auf ALLEN zutreffenden gelistet (orthogonal, kein Tie noetig).
  3. ECHTER Tie (genau eine Achse zuzuordnen, aber 2 plausibel):
     Prioritaet architektonisch > factoring > fachlich > semantisch  (stabilste/strukturellste zuerst).
     Die gewaehlte Achse + die Begruendung werden in tie_break_log dokumentiert.
```

## VERTRAG

```
LIEST:
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.clustering.clusters[]       (zu klassifizierende Cluster + member_signal_ids)
    BERATER_OUTPUTS_PT.contradiction.items[]       (contested-Status als Klassifikations-Kontext)
    BERATER_OUTPUTS_PT.gatherSignals.signals[]     (Roh-Text fuer Achsen-Urteil)
  {VAULT}/Libraries/PatternLibrary/_index.md       (Layer-Map _SCOPE_LIB — semantic/arch reuse, read-only)
  WORKING_DIR via resolve_bl_path.py

SCHREIBT (NUR eigener Slot — INV-PTO-4 Single-Writer):
  {bl_folder}/_manifest.md
    BERATER_OUTPUTS_PT.classify:
      semantic:      [{signal_id, cluster_id, label, confidence}]
      architectural: [{signal_id, cluster_id, layer, confidence}]
      fachlich:      [{signal_id, cluster_id, domain_term, confidence}]
      factoring:     [{signal_id, cluster_id, transform, confidence}]   # BL-257: Refactoring-Bewegung (extract/inline/declarativize/dedup/move)
      tie_break_log: [{signal_id, candidates: [achse,...], chosen, reason}]   # B-3 Pflicht-Doku
      counts: {semantic, architectural, fachlich, factoring, multi_axis, tie_breaks}
      status: DONE | EMPTY

  NICHT: Libraries/* (Layer-Map nur lesen), andere BERATER_OUTPUTS_PT-Slots, DF_BATCH_STATE.

INVARIANTEN:
  INV-CLS-1 (Single-Writer): schreibt NUR BERATER_OUTPUTS_PT.classify.
  INV-CLS-2 (Orthogonal): die 4 Achsen sind additiv, nicht hierarchisch — FACHLICH geht NICHT in semantisch unter (AK-4-Kern); factoring (Transformation) geht NICHT in architektonisch (Zustand) unter (BL-257-Kern).
  INV-CLS-3 (Tie-Break-Pflicht): jeder echte Tie wird deterministisch aufgeloest UND in tie_break_log dokumentiert (B-3) — kein stiller/zufaelliger Tie.
  INV-CLS-4 (Reuse): semantic-/arch-Achse nutzt _SCOPE_LIB-Layer-Map (read-only); Domain- + factoring-Diskriminator sind eigenstaendig (factoring zusaetzlich git-diff-belegt via forensic).
  INV-CLS-5 (Graceful): leere clustering → alle Achsen=[], status=EMPTY.
```

## Aufruf

```
Skill(_PT_berater_classify, args="{BL_ID} [--axes=all|arch|semantic|fachlich|factoring]")
```
Aufgerufen von `_PT_orchestrate` Stage 5 (Worker-Spawn). KEIN direkter User-Aufruf.

## Ablauf

```
1. WORKING_DIR = resolve_bl_path(BL_ID); bl_folder = WORKING_DIR
   IDEMPOTENZ: IF BERATER_OUTPUTS_PT.classify.status == DONE: RETURN (Resume-SKIP)

2. clusters = .clustering.clusters[]; signals = .gatherSignals.signals[]; contested = .contradiction.items[]
   IF clusters == []: SCHREIBE classify={...alle []..., status:EMPTY}; RETURN (INV-CLS-5)
   layer_map = read _SCOPE_LIB aus PatternLibrary/_index.md  (read-only, INV-CLS-4)

3. FOR signal IN alle member_signal_ids der clusters:
     # ORTHOGONAL (INV-CLS-2): jede Achse unabhaengig pruefen, Signal kann auf mehreren liegen
     IF semantisch_relevant(signal, layer_map): semantic.append({signal_id, label, confidence})
     IF architektonisch_relevant(signal, layer_map): architectural.append({signal_id, layer, confidence})
     IF fachlich_relevant(signal):  # Domain-Diskriminator
        fachlich.append({signal_id, domain_term, confidence})
     IF factoring_relevant(signal):  # BL-257: Signal beschreibt eine Struktur-TRANSFORMATION (vorher→nachher)
        # Diskriminator: extract/inline/declarativize/dedup/move-Bewegung. transform = die Refactoring-Art.
        # git-diff-Beleg liefert Stage 6 (forensic) nach; hier reicht das vorher→nachher-Urteil aus dem Roh-Text.
        factoring.append({signal_id, transform, confidence})

4. Tie-Break (INV-CLS-3, B-3):
   FOR signal WHERE echter_tie(signal):   # genau 1 Achse erwartet, 2 plausibel
     chosen = tie_break(candidates)        # architektonisch > factoring > fachlich > semantisch
     tie_break_log.append({signal_id, candidates, chosen, reason})

5. counts (inkl. multi_axis = Signale auf >=2 Achsen, tie_breaks = |tie_break_log|).
   Schreibe BERATER_OUTPUTS_PT.classify = {semantic, architectural, fachlich, factoring, tie_break_log, counts, status: DONE}.
   SendMessage team-lead: "classify: {semantic} semantisch / {architectural} arch / {fachlich} FACHLICH / {factoring} factoring ({multi_axis} multi-axis, {tie_breaks} Tie-Breaks)"
```

## Beispiele (je 1 pro Achse + Tie-Break — Vertrag-Selbsttest)

| Fall | Signal (roh) | Achse(n) | Tie-Break? |
|---|---|---|---|
| semantisch | "Command ohne `_X_`-Prefix benannt" | semantic | nein |
| architektonisch | "Berater schrieb 2 BERATER_OUTPUTS-Slots" | architectural | nein |
| FACHLICH | "usage_count vs confirm_count vermischt" | fachlich (geht NICHT in semantisch unter, INV-CLS-2) | nein |
| factoring | "Glue-Methoden in shared Handler extrahiert (vorher dupliziert)" | factoring (+ architectural: der resultierende Single-Handler) | nein (orthogonal) |
| factoring | "imperative setValidators-Kette → deklarative buildValidatorMap" | factoring | nein |
| Tie | "Naming einer Domaenen-Klasse falsch" | semantic + fachlich plausibel | ja → architektonisch>factoring>fachlich>semantisch → fachlich, reason dokumentiert |

## Verwandt
- `_PT_berater_clustering` (Stage 2) · `_PT_berater_contradiction` (Stage 4) — Eingaben ·
  `_PT_berater_forensic` (Stage 6, liefert git-diff-Beleg fuer factoring) ·
  `_PT_berater_materialize` (Stage 7, konsumiert .classify → 4 Libraries) · BL-237 (AK-4) + BL-257 (4. Achse factoring)
