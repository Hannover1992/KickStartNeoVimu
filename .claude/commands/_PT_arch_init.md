---
type: building-block
bl_id: BL-154
created: 2026-05-01
version: 1.0.0
ak_refs: ["AK-5-1", "AK-5-2", "AK-5-3", "RF-N4"]
model_refs: ["W17", "W18", "W19", "W20"]
---

# /_PT_arch_init

**Status:** v1.0.0 (BL-154 AK-5-1/5-2/5-3 — Initial-Bootstrap fuer Architektonische Pattern Library)
**Actor:** ARCH-PATTERN-BOOTSTRAPPER
**Zweck:** Initialisiert die Architektonische Pattern Library durch zyklisches Iterieren ueber die Codebase. Pro Zyklus: 1 Cool-Pattern (Diversitaets-Heuristik, >= 3 Klassen) + 1 Random-Pattern (Anti-Bias). Korb-Limit = max 5 neue Pattern pro Zyklus. Stop bei Plateau (3 aufeinanderfolgende Iterationen mit < 2 neuen Kandidaten). Safety-Stop bei 10 Zyklen.

> **ABGRENZUNG zu `_PT_init`:** `_PT_init` ist DEPRECATED (BL-153, ARCH-4) und initialisiert
> den alten `.claude/patterns/`-Pfad. `_PT_arch_init` arbeitet AUSSCHLIESSLICH mit
> `Libraries/PatternLibrary/_project/{LAYER}/` (Vault-First, BL-154). Logik fundamental
> verschieden: zyklisch + Plateau-Stop + Cool/Random-Heuristik vs. einmaliger Template-Copy.
> ADR-5 (BL-154): eigener Command statt Erweiterung _PT_init.

---

## Aufruf

```
/_PT_arch_init [LAYER] [--dry-run] [--max-cycles N] [--batch={L1,L2}] [--korb-limit-per-layer=N] [--trigger=auto|manual]
```

| Parameter | Pflicht | Format | Default | Beispiel |
|-----------|---------|--------|---------|----------|
| LAYER | NEIN | Layer-Kuerzel (aus `layers.yaml`) | alle Layer sequentiell | `COMMANDS`, `BERATER`, `ORCHESTRATOR` |
| --dry-run | NEIN | Flag | false | Simuliert Extraktion ohne Schreiben |
| --max-cycles | NEIN | Integer | 10 (Safety-Stop, RF-N4) | `--max-cycles 5` |
| --batch | NEIN | Komma-separierte Layer-Liste | null (alle Layer) | `--batch={SCRIPTS,HOOKS}` |
| --korb-limit-per-layer | NEIN | Integer | 5 (aus layers.yaml oder INV-1) | `--korb-limit-per-layer=3` |
| --trigger | NEIN | `auto` oder `manual` | `auto` | `--trigger=manual` |

> **HINWEIS:** Layer-Liste aus `.claude/config/layers.yaml` — Beispiele variieren pro Projekt.
> OmniCommand-Layer: `COMMANDS`, `BERATER`, `ORCHESTRATOR`. DCSRE-Projekte verwenden andere Layer.

**`--batch` vs LAYER:** `--batch={L1,L2}` bootstrappt exakt diese Layer (Multi-Layer, kein LAYER-Arg noetig).
LAYER als Positional-Arg bootstrappt genau 1 Layer. `--batch` hat Vorrang vor LAYER.

**`--trigger=manual`:** Nach jedem Layer HiL-Pause. Agent fragt:
`"Layer {X} abgeschlossen ({N} Pattern). Naechster Layer: {Y} — fortsetzen? [ja/nein/stop]"`

**Beispiele:**

```
/_PT_arch_init                                        # Bootstrap alle Layer sequentiell (auto)
/_PT_arch_init COMMANDS                               # Bootstrap nur COMMANDS Layer
/_PT_arch_init --dry-run                              # Simulation ohne Schreiben
/_PT_arch_init BERATER --max-cycles 5                 # Max 5 Zyklen fuer BERATER
/_PT_arch_init --batch={SCRIPTS,HOOKS} --korb-limit-per-layer=3   # Batch: 2 Layer, max 3 Pattern/Layer
/_PT_arch_init --trigger=manual                       # Interaktiv: nach jedem Layer HiL-Pause
```

---

## Vertrag

```
+=======================================================================================+
|  COMMAND: /_PT_arch_init [LAYER] [--dry-run] [--max-cycles N]                        |
|                          [--batch={L1,L2}] [--korb-limit-per-layer=N] [--trigger=..] |
+=======================================================================================+
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    0. .claude/config/layers.yaml (ARCH-K5 PL-26)              |
|       -> Layer-Liste, vault_folder, path_globs, id_prefix      |
|       -> bootstrap_config (korb_limit, plateau etc.)           |
|    1. Libraries/PatternLibrary/{vault_folder}/_index.md        |
|       -> Existierende Pattern (Duplikat-Check)                 |
|    2. Libraries/PatternLibrary/_index.md (Master-Index)        |
|       -> Layer-Routing, Gesamt-Uebersicht                      |
|    3. Libraries/PatternLibrary/_generic/frontmatter-schema.md  |
|       -> Pflichtfelder fuer neuen Pattern-Knoten               |
|                                                                |
|  LIEST (Input) - OPTIONAL:                                     |
|    2. Codebase-Dateien gemaess path_globs pro LAYER            |
|       -> Kandidaten-Scan pro Zyklus (ARCH-K5: dynamisch)       |
|    3. .claude/models/{PROJEKT}_Model.md                        |
|       -> Layer-Taxonomie + Schicht-Semantik                    |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. Libraries/PatternLibrary/_project/{LAYER}/               |
|       {pattern-id}.md (neue Pattern-Knoten, max 5/Zyklus)      |
|    2. Libraries/PatternLibrary/_project/{LAYER}/_index.md      |
|       -> Aktualisiert mit neuen Eintraegen                     |
|    3. Libraries/PatternLibrary/_index.md (Master-Index Update) |
|    4. .claude/output/PT_arch_init_report_{LAYER}_{Datum}.md   |
|       -> Bootstrap-Report mit Zusammenfassung + Plateau-Info   |
|                                                                |
|  SCHREIBT NICHT:                                               |
|    - .claude/patterns/ (DEPRECATED, BL-153 ARCH-4)            |
|    - Libraries/PatternLibrary/_generic/ (nur _project/)        |
|                                                                |
|  ACTOR: ARCH-PATTERN-BOOTSTRAPPER                              |
|    Zyklisches Iterieren, Cool+Random-Heuristik, Plateau-Stop.  |
|    Erstausstattung pro Layer — danach organisches Wachstum.    |
|                                                                |
+===============================================================+
```

---

## Invarianten

- **INV-1 (AK-5-3 Korb-Limit):** Pro Zyklus MAXIMAL 5 neue Pattern-Knoten erstellt. Bei > 5 Kandidaten: Pruefung — beste 5 gemaess Diversitaet + Relevanz.
- **INV-2 (AK-5-2 Cool+Random):** Pro Zyklus MINDESTENS 1 Cool-Pattern (>= 3 verschiedene Klassen als Quelle) UND 1 Random-Pattern (zufall-basiert, Anti-Bias). Wenn Codebase-Sektion erschoepft: SKIP mit Logging.
- **INV-3 (AK-5-1 Plateau-Detection):** Bootstrap STOPPT wenn 3 aufeinanderfolgende Iterationen jeweils < 2 neue Kandidaten gefunden. Safety-Stop bei --max-cycles (Default: 10, RF-N4).
- **INV-4 (Vault-First):** Schreibt AUSSCHLIESSLICH in `Libraries/PatternLibrary/_project/{LAYER}/`. Kein `.claude/patterns/`.
- **INV-5 (seed=true):** Alle Bootstrap-generierten Knoten erhalten `seed: true` + `status: experimental` im Frontmatter.
- **INV-6 (Duplikat-Check):** Vor jedem Schreiben: Pattern-ID gegen bestehende `_index.md` pruefen. Duplikat → SKIP + Log.
- **INV-7 (Parallele Layer-Wellen, BL-154 Iter-3 Konsistenz mit `_SL_init`):**
  Bei `--trigger=auto` (Default): Layer-Bootstrap laeuft PARALLEL via Wellen-Pattern —
  Team Lead spawnt N Sonnet-Worker (einer pro Layer) gleichzeitig. Jeder Worker
  iteriert intern seinen kompletten Zyklus-Loop (Cool+Random+Plateau) fuer SEINEN Layer.
  Bei `--trigger=manual`: Layer SEQUENTIELL (HiL-Pause zwischen Layern noetig).
  Plateau-Counter und Bootstrap-History sind WORKER-LOKAL (kein Shared State).
  Konsolidierung (Master-Index, CrossRef) erst NACH allen Worker-DONE in Phase 5.

---

## Pseudocode

### Phase 0: Initialisierung (BL-154 PL-26 ARCH-K5 — dynamisch via layers.yaml)

```
# ARCH-K5 (PL-26): Layer-Liste NICHT hardcoded — aus layers.yaml laden
# ARCH-N7 (BL-154 Iter-3, 2026-05-01): layers.yaml ist VAULT-spezifisch.
# Reihenfolge:
#   1. {vault_root}/config/layers.yaml         ← PRIMAER (projekt-spezifisch)
#   2. .claude/config/layers.yaml              ← FALLBACK (Repo-Default fuer Self/OmniCommand)
# Bei Deployment-nach-anderem-Projekt soll die Vault-Version greifen, nicht
# die mitkopierte Repo-Version.
vault_root = python3(.claude/scripts/resolve_vault_root.py).stdout.strip()
              # ODER ENV CLAUDE_VAULT_ROOT
              # ODER .claude/.vault_root pin-Datei
              # ODER Heuristik {~/Documents/{cwd_name}}

layers_config_path = "{vault_root}/config/layers.yaml"
IF NOT exists(layers_config_path):
  Logge: "[PT_ARCH_INIT] Vault-config nicht gefunden ({layers_config_path}) — fallback auf Repo-Default"
  layers_config_path = ".claude/config/layers.yaml"

layers_config = lies(layers_config_path)
Logge: "[PT_ARCH_INIT] layers.yaml geladen aus: {layers_config_path}"

IF layers_config == null OR layers_config.layers == null:
  Logge FEHLER: "[PT_ARCH_INIT] FAIL — layers.yaml nicht gefunden oder leer: {layers_config_path}"
  Logge FEHLER: "[PT_ARCH_INIT] Erstelle layers.yaml gemaess BL-154 PL-26 ARCH-K5 Schema bevor Bootstrap laeuft."
  EXIT exitcode=2

# Layer-Liste aus Config laden (sortiert nach scan_priority)
ALL_LAYERS_CONFIG = sortiere(layers_config.layers, nach="scan_priority")
ALL_LAYER_IDS = [layer.id FOR layer IN ALL_LAYERS_CONFIG]

# HiL-Vorschlag (Phase 0, ARCH-K5): Zeige erkannte Layer vor Start
IF layers_config.bootstrap_config.hil_vorschlag == true:
  Logge: "[PT_ARCH_INIT] Phase 0 — Erkannte Layer aus layers.yaml:"
  FOR layer_cfg IN ALL_LAYERS_CONFIG:
    Logge: "  - {layer_cfg.id}: {layer_cfg.label} (prefix={layer_cfg.id_prefix}, globs={layer_cfg.path_globs})"
  Logge: "[PT_ARCH_INIT] Phase 0 — Vault-Ordner werden angelegt unter Libraries/PatternLibrary/{layer.vault_folder}"
  # Bei HiL=on: AskUserQuestion fuer Bestaetigung
  # Bei HiL=off: automatisch weiter (INV-4 dark_factory-Modus)

# Argument-Override: Falls spezifischer Layer angegeben, nur diesen Layer verarbeiten
IF args.LAYER != null:
  layer_cfg_filtered = [cfg FOR cfg IN ALL_LAYERS_CONFIG IF cfg.id == args.LAYER]
  IF layer_cfg_filtered.empty:
    Logge FEHLER: "[PT_ARCH_INIT] FAIL — LAYER='{args.LAYER}' nicht in layers.yaml definiert."
    Logge FEHLER: "[PT_ARCH_INIT] Bekannte Layer: {ALL_LAYER_IDS}"
    EXIT exitcode=2
  LAYER_LIST = [args.LAYER]
  LAYERS_CONFIG_FILTERED = layer_cfg_filtered
ELSE:
  LAYER_LIST = ALL_LAYER_IDS
  LAYERS_CONFIG_FILTERED = ALL_LAYERS_CONFIG

# Lade bootstrap_config Werte (mit Defaults falls nicht gesetzt)
MAX_CYCLES = args.max_cycles ?? layers_config.bootstrap_config.default_max_cycles ?? 10  # Safety-Stop RF-N4
DRY_RUN = args.dry_run ?? false
TRIGGER_MODE = args.trigger ?? "auto"   # "auto" oder "manual" (ARCH-N3)

# --korb-limit-per-layer ueberschreibt globalen Korb-Limit (ARCH-N3)
KORB_LIMIT = args.korb_limit_per_layer ?? layers_config.bootstrap_config.korb_limit ?? 5  # INV-1, AK-5-3
PLATEAU_THRESHOLD = layers_config.bootstrap_config.plateau_threshold ?? 3      # INV-3, AK-5-1
PLATEAU_MIN_NEUE = layers_config.bootstrap_config.plateau_min_neue ?? 2        # INV-3

# --batch={L1,L2} hat Vorrang vor LAYER-Positional-Arg (ARCH-N3)
IF args.batch != null:
  batch_layer_ids = split(args.batch, ",")  # z.B. ["SCRIPTS", "HOOKS"]
  BATCH_MODE = true
  # Validierung: alle batch-Layer muessen in layers.yaml definiert sein
  FOR EACH bl IN batch_layer_ids:
    IF bl NOT IN ALL_LAYER_IDS:
      Logge FEHLER: "[PT_ARCH_INIT] FAIL — batch-Layer '{bl}' nicht in layers.yaml. Bekannte Layer: {ALL_LAYER_IDS}"
      EXIT exitcode=2
  LAYER_LIST = batch_layer_ids
  LAYERS_CONFIG_FILTERED = [cfg FOR cfg IN ALL_LAYERS_CONFIG IF cfg.id IN batch_layer_ids]
  Logge: "[PT_ARCH_INIT] Batch-Modus: Layer={LAYER_LIST} (--batch Override)"
ELSE:
  BATCH_MODE = false
  # LAYER_LIST bleibt wie oben gesetzt (LAYER-Arg oder alle Layer)

Logge: "[PT_ARCH_INIT] Start Bootstrap. Layer: {LAYER_LIST}. max_cycles={MAX_CYCLES}. dry_run={DRY_RUN}. korb_limit={KORB_LIMIT}. trigger={TRIGGER_MODE}."
Logge: "[PT_ARCH_INIT] Config geladen aus: {layers_config_path} (schema_version={layers_config.schema_version})"
```

### Phase 1: Layer-Verarbeitung (PARALLEL bei auto, SEQUENTIELL bei manual)

```
# INV-7 (BL-154 Iter-3): Parallel-vs-Sequentiell-Switch nach TRIGGER_MODE.
# Bei auto: spawn alle Layer-Worker gleichzeitig (Wellen-Pattern wie _SL_init).
# Bei manual: HiL-Pause zwischen Layern noetig → Sequenziell.

IF TRIGGER_MODE == "auto" AND NOT BATCH_MODE_FORCE_SEQUENTIAL:
  Logge: "[PT_ARCH_INIT] Phase 1 — PARALLELE LAYER-WELLE: {|LAYER_LIST|} Worker spawnen (Sonnet)"

  # Team Lead spawnt N Worker GLEICHZEITIG — einer pro Layer
  # Jeder Worker iteriert SEINEN kompletten Layer-Zyklus-Loop unten (Phase 1a)
  # Worker schreiben PRO Layer in eigenen vault_folder — keine Race-Condition
  # (verschiedene Verzeichnisse) ausser shared Master-_index.md (in Phase 5 konsolidiert)
  parallel_for layer IN LAYER_LIST:
    spawne_worker(
      subagent_type="general-sonnet",
      description="PT_arch_init Layer={layer}",
      prompt=build_layer_worker_prompt(layer, LAYERS_CONFIG_FILTERED, MAX_CYCLES, KORB_LIMIT, PLATEAU_THRESHOLD, PLATEAU_MIN_NEUE, DRY_RUN),
      team_name="pt-arch-init"
    )
  # warte_auf_alle_workers_done()
  Logge: "[PT_ARCH_INIT] Alle {|LAYER_LIST|} Layer-Worker DONE"

ELSE:
  # Sequenzieller Pfad: nur bei --trigger=manual (HiL-Pause zwischen Layern)
  Logge: "[PT_ARCH_INIT] Phase 1 — SEQUENZIELLE LAYER-VERARBEITUNG (manual-Modus)"
  FOR EACH layer IN LAYER_LIST:
    fuehre_layer_zyklus_loop_aus(layer)  # → unten Phase 1a (gleicher Worker-Body inline)
    # Hand-Trigger HiL-Pause am Layer-Ende (siehe unten)

# ─────────────────────────────────────────────────────────────────────
# Phase 1a: Layer-Zyklus-Loop (BODY)
# Worker-Body bei parallel auch identischer Inhalt — wird via build_layer_worker_prompt
# in den Worker-Prompt eingebunden.
# ─────────────────────────────────────────────────────────────────────

FUNCTION fuehre_layer_zyklus_loop_aus(layer):
  # Layer-Config aus LAYERS_CONFIG_FILTERED laden (ARCH-K5)
  layer_cfg = LAYERS_CONFIG_FILTERED.find(id == layer)
  vault_folder = layer_cfg.vault_folder  # z.B. "_project/COMMANDS"
  path_globs = layer_cfg.path_globs      # Welche Codebase-Pfade scannen
  id_prefix = layer_cfg.id_prefix        # z.B. "PT-CMD"

  Logge: "[PT_ARCH_INIT] === Layer: {layer} ({layer_cfg.label}) vault={vault_folder} ==="

  # Vault-Ordner anlegen wenn nicht vorhanden (ARCH-K5 Vault-First)
  IF NOT exists(Libraries/PatternLibrary/{vault_folder}/):
    erstelle_ordner(Libraries/PatternLibrary/{vault_folder}/)
    Logge: "[PT_ARCH_INIT] Vault-Ordner angelegt: Libraries/PatternLibrary/{vault_folder}/"

  # Bestehende Pattern laden (Duplikat-Check Grundlage)
  existing_patterns = lies(Libraries/PatternLibrary/{vault_folder}/_index.md)
  existing_ids = extract_ids(existing_patterns) ?? []

  # Plateau-Tracking (AK-5-1)
  plateau_counter = 0        # aufeinanderfolgende Zyklen mit < PLATEAU_MIN_NEUE
  cycle_no = 0
  total_new_patterns = 0
  bootstrap_history = []     # [{cycle, neue_kandidaten, cool_id, random_id}]

  # Zyklus-Loop
  WHILE cycle_no < MAX_CYCLES:
    cycle_no += 1
    Logge: "[PT_ARCH_INIT] Layer={layer} Zyklus={cycle_no}/{MAX_CYCLES}"

    ### Phase 2: Kandidaten-Scan pro Zyklus

    # Scan: Code-Dateien fuer diesen Layer lesen
    code_candidates = scan_layer_code(layer)
    # Filtere bereits bekannte Pattern heraus
    neue_kandidaten_raw = filter_existing(code_candidates, existing_ids)

    # Cool-Pattern Heuristik (AK-5-2, INV-2):
    # Cool = Pattern mit >= 3 verschiedenen Klassen als Kandidaten-Quelle
    cool_candidates = [c for c in neue_kandidaten_raw IF c.source_class_count >= 3]
    IF cool_candidates.empty:
      Logge: "[PT_ARCH_INIT] Cool-Kandidaten erschoepft — SKIP Cool (INV-2 Graceful-Skip)"
      cool_pattern = null
    ELSE:
      cool_pattern = select_best(cool_candidates, strategy="diversity")

    # Random-Pattern Heuristik (AK-5-2, INV-2):
    # Random = zufall-gewaehlt aus verbleibendem Pool (Anti-Bias)
    remaining_pool = neue_kandidaten_raw - [cool_pattern]
    IF remaining_pool.empty:
      Logge: "[PT_ARCH_INIT] Random-Pool erschoepft — SKIP Random (INV-2 Graceful-Skip)"
      random_pattern = null
    ELSE:
      random_pattern = random_select(remaining_pool)

    # Zyklus-Kandidaten: Cool + Random + Fuell-Kandidaten bis KORB_LIMIT
    zyklus_kandidaten = compact([cool_pattern, random_pattern])
    fuell_kandidaten = select_best(
      remaining_pool - [random_pattern],
      count = KORB_LIMIT - zyklus_kandidaten.length,
      strategy = "relevance"
    )
    zyklus_kandidaten = zyklus_kandidaten + fuell_kandidaten

    # Korb-Limit erzwingen (AK-5-3, INV-1)
    IF zyklus_kandidaten.length > KORB_LIMIT:
      zyklus_kandidaten = zyklus_kandidaten[:KORB_LIMIT]
      Logge: "[PT_ARCH_INIT] Korb-Limit ({KORB_LIMIT}) erreicht — {zyklus_kandidaten.length - KORB_LIMIT} Kandidaten gekappt."

    neue_count = zyklus_kandidaten.length
    Logge: "[PT_ARCH_INIT] Zyklus {cycle_no}: {neue_count} neue Kandidaten (Cool={cool_pattern?.id ?? 'none'}, Random={random_pattern?.id ?? 'none'})"

    ### Phase 3: Pattern-Knoten schreiben

    FOR EACH kandidat IN zyklus_kandidaten:
      # Duplikat-Check (INV-6)
      IF kandidat.id IN existing_ids:
        Logge: "[PT_ARCH_INIT] DUPLIKAT {kandidat.id} — SKIP"
        CONTINUE

      # Pattern-ID aus id_prefix + laufender Nummer generieren (ARCH-K5)
      pattern_nr = next_pattern_nr(existing_ids, prefix=id_prefix)  # z.B. PT-CMD-003
      pattern_id = "{id_prefix}-{pattern_nr:03d}"

      pattern_node = {
        id: pattern_id,
        name: kandidat.name,
        layer: layer,
        status: "experimental",     # INV-5
        seed: true,                  # INV-5 — Bootstrap-Ursprung
        confidence: "low",
        usage_count: 0,
        broken_count: 0,
        source_classes: kandidat.source_classes,
        bootstrap_cycle: cycle_no,
        cool_selected: (kandidat == cool_pattern),
        random_selected: (kandidat == random_pattern),
        created_at: heute_iso8601,
        # BL-154 Architektonische Pflichtfelder:
        scope: "architectural",
        applies_to: kandidat.applies_to_description,
        severity: "RECOMMENDED",   # Default — Worker-Review empfohlen
        min_scope: null,           # Nach Bootstrap durch Review zu befuellen
        max_scope: null            # Nach Bootstrap durch Review zu befuellen
      }

      IF NOT DRY_RUN:
        schreibe(Libraries/PatternLibrary/{vault_folder}/{pattern_id}.md, pattern_node)
        aktualisiere_index(Libraries/PatternLibrary/{vault_folder}/_index.md, kandidat)
        existing_ids.add(pattern_id)

      total_new_patterns += 1

    # Bootstrap-Historie
    bootstrap_history.append({
      cycle: cycle_no,
      neue_kandidaten: neue_count,
      cool_id: cool_pattern?.id ?? null,
      random_id: random_pattern?.id ?? null
    })

    ### Phase 4: Plateau-Detection (AK-5-1, INV-3)

    IF neue_count < PLATEAU_MIN_NEUE:
      plateau_counter += 1
      Logge: "[PT_ARCH_INIT] Plateau-Signal: Zyklus {cycle_no} → {neue_count} neue Kandidaten < {PLATEAU_MIN_NEUE}. Plateau-Counter={plateau_counter}/{PLATEAU_THRESHOLD}"
    ELSE:
      plateau_counter = 0  # Reset bei genuegend neuen Kandidaten

    IF plateau_counter >= PLATEAU_THRESHOLD:
      Logge: "[PT_ARCH_INIT] PLATEAU ERREICHT: {PLATEAU_THRESHOLD} aufeinanderfolgende Zyklen < {PLATEAU_MIN_NEUE} neue Kandidaten. Bootstrap-Stop fuer Layer={layer}."
      BREAK  # Plateau-Stop (AK-5-1)

    IF cycle_no >= MAX_CYCLES:
      Logge: "[PT_ARCH_INIT] SAFETY-STOP: max_cycles={MAX_CYCLES} erreicht (RF-N4). Layer={layer}."
      BREAK  # Safety-Stop

  # Layer abgeschlossen
  Logge: "[PT_ARCH_INIT] Layer={layer} DONE. Zyklen={cycle_no}. Neue Pattern={total_new_patterns}. Stop-Grund={plateau_counter >= PLATEAU_THRESHOLD ? 'PLATEAU' : 'SAFETY_STOP'}."

  # Hand-Trigger HiL-Pause (ARCH-N3): nach jedem Layer bei --trigger=manual
  # NUR im sequentiellen Pfad relevant — Parallel-Worker koennen keine AskUserQuestion
  # ausfuehren (W7-Constraint). Im auto-Pfad ist TRIGGER_MODE!=manual, daher SKIP.
  IF TRIGGER_MODE == "manual":
    remaining_layers = LAYER_LIST[LAYER_LIST.index(layer)+1:]
    IF remaining_layers.length > 0:
      next_layer = remaining_layers[0]
      antwort = AskUserQuestion(
        "Layer {layer} abgeschlossen ({total_new_patterns} neue Pattern). " +
        "Naechster Layer: {next_layer} — fortsetzen? [ja/nein/stop]"
      )
      IF antwort IN ["nein", "stop", "n"]:
        Logge: "[PT_ARCH_INIT] Hand-Trigger: User hat Bootstrap nach Layer={layer} gestoppt."
        BREAK  # Vorzeitiger Abbruch der Layer-Schleife
      ELSE:
        Logge: "[PT_ARCH_INIT] Hand-Trigger: Weiter mit Layer={next_layer}."
END FUNCTION fuehre_layer_zyklus_loop_aus

# ─────────────────────────────────────────────────────────────────────
# Helper: build_layer_worker_prompt (INV-7 Parallel-Pattern, BL-154 Iter-3)
# ─────────────────────────────────────────────────────────────────────

FUNCTION build_layer_worker_prompt(layer, layers_config_filtered, max_cycles,
                                    korb_limit, plateau_threshold, plateau_min_neue,
                                    dry_run):
  # Erzeugt vollstaendigen Worker-Prompt fuer EINEN Layer-Sonnet-Worker.
  # Worker-Body enthaelt fuehre_layer_zyklus_loop_aus(layer) als Inline-Logik
  # (Skill-Pattern: kein Sub-Spawn, alles im Worker selbst).
  RETURN """
    Du bist kurzlebiger Sonnet-Worker fuer PT_arch_init Layer-Bootstrap.

    LAYER: {layer}
    PARAMETER:
      max_cycles            = {max_cycles}
      korb_limit            = {korb_limit}
      plateau_threshold     = {plateau_threshold}
      plateau_min_neue      = {plateau_min_neue}
      dry_run               = {dry_run}
      layer_cfg             = {layers_config_filtered.find(id == layer)}

    AUFGABE: Fuehre den Zyklus-Loop fuer DIESEN Layer aus (Phase 2-4 unten).
    Iteriere Cool/Random/Plateau-Detection lokal — kein Shared-State mit
    anderen Workers. Schreibe Pattern-Knoten in
    Libraries/PatternLibrary/{layer_cfg.vault_folder}/.

    REGELN:
    - W7-Constraint: KEIN Sub-Spawn.
    - INV-VAULT-9 strikt — Schreibungen NUR in Vault.
    - INV-3 Plateau-Detection: 3 aufeinanderfolgende Zyklen <2 neue → BREAK.
    - INV-1 Korb-Limit: max korb_limit neue Pattern pro Zyklus.
    - INV-2 Cool+Random: pro Zyklus ein Cool + ein Random Kandidat.
    - KEIN Hand-Trigger HiL (Parallel-Worker kann keine AskUserQuestion).

    OUTPUT: SendMessage Summary mit
      {layer_id, zyklen_done, total_new_patterns, stop_grund, bootstrap_history}
  """
END FUNCTION
```

### Phase 5: Master-Index aktualisieren

```
IF NOT DRY_RUN:
  aktualisiere_master_index(Libraries/PatternLibrary/_index.md)
  Logge: "[PT_ARCH_INIT] Master-Index aktualisiert."
```

### Phase 6: Bootstrap-Report

```
report = {
  date: heute_iso8601,
  feature: PROJEKT,
  layers_processed: LAYER_LIST,
  total_new_patterns: gesamt,
  dry_run: DRY_RUN,
  plateau_threshold: PLATEAU_THRESHOLD,
  plateau_min_neue: PLATEAU_MIN_NEUE,
  korb_limit: KORB_LIMIT,
  max_cycles: MAX_CYCLES,
  per_layer: [
    {layer, zyklen, neue_patterns, stop_grund, bootstrap_history}
    for each layer
  ],
  hinweis: "Schwellwerte (3 Zyklen, <2 Kandidaten) sind HYPOTHESEN (W18). Empirische Kalibrierung nach erstem Bootstrap empfohlen."
}

report_path = ".claude/output/PT_arch_init_report_{erster_Layer}_{Datum}.md"
schreibe(report_path, report)
Logge: "[PT_ARCH_INIT] Bootstrap-Report: {report_path}"
```

---

## Kanarienvogel-Tests (AK-5-1, AK-5-2, AK-5-3)

```
# Gold-1 (AK-5-1): Plateau-Detection terminiert Bootstrap
Given _PT_arch_init laeuft
WHEN 3 aufeinanderfolgende Iterationen < 2 neue Kandidaten
THEN Bootstrap-Loop endet + Report geschrieben (stop_grund="PLATEAU")

# Gold-2 (AK-5-2): Cool+Random pro Zyklus enthalten
Given Bootstrap-Zyklus
WHEN Extraktion mit genuegend Code-Kandidaten
THEN mindestens 1 Cool-Pattern (cool_selected=true, source_class_count>=3)
     UND 1 Random-Pattern (random_selected=true) im Korb

# Gold-3 (AK-5-3): Korb-Limit eingehalten
Given Bootstrap-Zyklus mit > 5 Kandidaten
WHEN Zyklus abgeschlossen
THEN max 5 neue Pattern-Knoten erstellt (KORB_LIMIT erzwungen)

# Gold-4 (RF-N4): Safety-Stop bei 10 Zyklen
Given _PT_arch_init mit DEFAULT max_cycles=10
WHEN 10 Zyklen abgeschlossen ohne Plateau
THEN Bootstrap-Stop mit stop_grund="SAFETY_STOP"
```

---

## Verwandte Commands

| Command | Zweck | Wann |
|---------|-------|------|
| `_PT_init` | DEPRECATED: Legacy .claude/patterns/ init | Nie (BL-153 ARCH-4) |
| `_PT_update --arch-lifecycle` | Pattern Lifecycle-Updates | Nach jeder User Story |
| `_PT_extract` | Einzelnes Pattern extrahieren | SC RED-Klassifikation |
| `_PT_arch_init` | Pattern-Library scannen | Audit |
| `_PostBatch_ArchConformance` | Post-Batch Arch-Conformance Check | Nach jedem Batch |

---

## Bekannte Offene Punkte (W18 HYPOTHESEN)

- **Plateau-Schwellwert (3 Zyklen, < 2 Kandidaten):** Empirisch — Erstbetrieb zeigt ob Werte passen (W18 HYPOTHESE, Q3 BL-154).
- **Cool-Heuristik (>= 3 Klassen):** Operationalisierung vereinfacht — in Praxis kann "Coolness" kontextueller sein.
- **Korb-Limit (5/Zyklus):** Empirisch — bei grossen Codebases ggf. erhoehen.
- **Layer-Reihenfolge:** Sequentiell aufsteigend (Foundation zuerst). Parallelisierung moeglich aber nicht implementiert.
