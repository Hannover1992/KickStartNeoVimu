---
status: active
version: 1.0.0
created: 2026-04-26
op: ImplementationPipeline
phase: 3
type: berater
chain_position: middle
model_tier: middle
---

# /_I_berater_teamLeadSteuerung (Phase 3 — Team-Lead-Steuerung der Wellen)

[VERTRAG]
- LIEST:   BERATER_OUTPUTS.teamSetup.{slices, difficulty, ceiling, floor, middle, worker_mode}  ← Phase 1
- LIEST:   BERATER_OUTPUTS.kurzlebigPrompt.KURZLEBIG_PROMPT(command, slice, welle, task_id)    ← Phase 2
- SCHREIBT: BERATER_OUTPUTS.teamLeadSteuerung.{synthese, manifest_state, stufe_final, resume_zaehler}
- Output:  Wellen-Spawn-Ergebnisse, Synthese-Dateien pro Slice, aktualisiertes Manifest
- Cross-References:
    - Phase 1 (_I_berater_teamSetup): liefert slices, difficulty, ceiling/floor/middle, worker_mode
    - Phase 2 (_I_berater_kurzlebigPrompt): liefert KURZLEBIG_PROMPT-Funktion fuer alle Spawns

## Verantwortlichkeit

**TUT:** Tasks erstellen, Messages lesen, HiL-Checkpoints, Manifest persistieren, Resume-Tasks bei partial.
**NICHT:** Commands ausfuehren, Code/Tests schreiben, Git.

## Kommunikationsstil (PFLICHT)

```
VERBOTEN: "Soll ich X machen?" / "Moechtest du Y?" / "Ich koennte Z tun..."
RICHTIG:  "X wird ausgefuehrt." / "Starte Y." / "Naechster Schritt: Z."

Der Team Lead ist ein PROCESS MANAGER, kein Kellner.
Fuehre die Pipeline-Schritte AUS. Frage NUR bei echten HiL-Checkpoints.
Wenn ein Prerequisite fehlt: Erstelle es SELBST (stage_*.md, Manifest-Felder).
Wenn ein Guard FAIL wirft: Melde den Fehler und STOPP. Kein "Soll ich stoppen?"
```

## Wellen-Spawn (Kern-Mechanismus)

```
FUNKTION spawne_wellen(command, slice, stufe):
  """
  Respektiert die Skalierung-Tabelle (easy/normal/hard).
  Jeder Command durchlaeuft die Wellen gemaess difficulty.
  """

  # ═══════════════════════════════════════════════════════════════════════
  # PFLASTER 2026-04-20 — COMMAND-CAP vor Wellen-Spawn
  # Command-basierter Cap: _I_blueprintArchitect → opus, _I_testSearch → sonnet, etc.
  # Ceiling wird durch COMMAND_MODEL_MAP eingeschraenkt (kein Opus-Verschwenden
  # fuer triviale Commands). Jeder Spawn bekommt PFLICHT-[SPAWN]-Log.
  # ═══════════════════════════════════════════════════════════════════════
  command_cap = resolve_command_cap(command, ceiling)
  effective_ceiling = command_cap.model  # opus | sonnet | haiku

  # Worker-Mode Guard (RF-19): Sequentielle Calls statt Wellen # (Z2: RF-19)
  IF worker_mode == true:
    Logge: "Worker-Mode: Sequentielle Calls statt Wellen."
    task_id = TaskCreate(subject="[{slice}] {command} (worker-seq)")
    worker = "i-sc-{slice}-{command}-seq"
    Logge: "[SPAWN] {worker} type={model_fuer(effective_ceiling)} model={effective_ceiling} cmd={command}"
    Agent(name=worker,
         subagent_type=model_fuer(effective_ceiling),
         model=effective_ceiling,
         prompt=KURZLEBIG_PROMPT(command, slice, "seq", task_id))
    warte(task_id)
    synthese = lese_synthese_datei(command, slice)
    manifest.update()
    RETURN synthese

  IF difficulty == "easy":
    # 1 Agent direkt (kein Wellen-Pattern) — Command-Cap ist das Model
    task_id = TaskCreate(subject="[{slice}] {command}")
    worker = "i-sc-{slice}-{command}-b1"
    Logge: "[SPAWN] {worker} type={model_fuer(effective_ceiling)} model={effective_ceiling} cmd={command}"
    Agent(name=worker,
         subagent_type=model_fuer(effective_ceiling),
         model=effective_ceiling,
         prompt=KURZLEBIG_PROMPT(command, slice, 1, task_id))
    warte(task_id)

  ELIF difficulty == "normal" ODER "hard":
    # ═══ WELLE 1: Explorer (floor-Modell, PARALLEL) ═══
    explorer_count = 5 wenn normal, 9 wenn hard
    explorer_tasks = []
    FOR i IN 1..explorer_count:
      task_id = TaskCreate(subject="[{slice}] {command} W1-explore-{i}")
      worker = "i-sc-{slice}-{command}-w1-{i}"
      Logge: "[SPAWN] {worker} type={model_fuer(floor)} model={floor} cmd={command} wave=explorer"
      Agent(name=worker,
           subagent_type=model_fuer(floor),
           model=floor,
           prompt=KURZLEBIG_PROMPT(command, slice, "w1-{i}", task_id),
           run_in_background=true)
      explorer_tasks.append(task_id)
    warte_alle(explorer_tasks)

    # ═══ WELLE 2: Drafter (middle-Modell, PARALLEL) ═══
    drafter_count = 3 wenn normal, 5 wenn hard
    drafter_tasks = []
    FOR i IN 1..drafter_count:
      task_id = TaskCreate(subject="[{slice}] {command} W2-draft-{i}")
      worker = "i-sc-{slice}-{command}-w2-{i}"
      Logge: "[SPAWN] {worker} type={model_fuer(middle)} model={middle} cmd={command} wave=drafter"
      Agent(name=worker,
           subagent_type=model_fuer(middle),
           model=middle,
           prompt=KURZLEBIG_PROMPT(command, slice, "w2-{i}", task_id),
           run_in_background=true)
      drafter_tasks.append(task_id)
    warte_alle(drafter_tasks)

    # ═══ WELLE 3: Synthesizer (effective_ceiling, 1 Agent) ═══
    # Nutzt COMMAND-Cap statt rohen ceiling (verhindert Opus-Verschwendung)
    task_id = TaskCreate(subject="[{slice}] {command} W3-synthesize")
    worker = "i-sc-{slice}-{command}-w3"
    Logge: "[SPAWN] {worker} type={model_fuer(effective_ceiling)} model={effective_ceiling} cmd={command} wave=synthese"
    Agent(name=worker,
         subagent_type=model_fuer(effective_ceiling),
         model=effective_ceiling,
         prompt=KURZLEBIG_PROMPT(command, slice, "w3", task_id))
    warte(task_id)

  # Wellen-Ergebnis pruefen
  synthese = lese_synthese_datei(command, slice)
  manifest.update()
  RETURN synthese
```

## Modell-Mapping

```
# ═══════════════════════════════════════════════════════════════════════
# PFLASTER 2026-04-20 — Saubere general-{model} Palette (BL-125 AK-6)
# ═══════════════════════════════════════════════════════════════════════
# ALT: "general-sonnet-4" (Legacy-Name) + "haiku" (ungueltig als subagent_type).
# NEU: konsistent general-{opus|sonnet|haiku} — alle drei existieren als Agent-Typen.
# ═══════════════════════════════════════════════════════════════════════
FUNKTION model_fuer(level):
  """Liefert den REGISTRIERTEN Carrier-Agent-Typ pro Tier.
  ═══ NEUFASSUNG 2026-05-31 (Research-belegt: code.claude.com/docs/sub-agents + model-config) ═══
  KERN-WAHRHEIT: Die ECHTE Modell-Wahl macht der `model=`-Param beim Spawn (model=level, danebenstehend),
  NICHT der subagent_type. Der Spawn-`model` GEWINNT gegen die Agent-Def (Agent-Def model:sonnet +
  Spawn model:"opus" -> laeuft Opus; kein Inheritance-Leck, weil explizit). Alias ("opus"/"sonnet") ist
  bump-safe (= immer current; kein Versions-Pin wie das alte general-sonnet-4).
  -> `general-opus` EXISTIERT NICHT (registriert nicht) und wird NICHT mehr gebraucht. Diese Funktion gibt
     nur einen gueltigen, registrierten Carrier zurueck; `model=level` treibt das echte Modell.
  USER-REGEL: Haiku NUR in Welle-1 (Explorer); auf Command-Level kein Haiku (sonnet als Floor)."""
  # Carrier = registrierter general-{sonnet|haiku}. Fuer opus KEIN general-opus -> general-sonnet als
  # Carrier; der Spawn `model="opus"` ueberschreibt -> echtes (current) Opus.
  IF level == "opus":   RETURN "general-sonnet"   # Carrier; Spawn model="opus" treibt -> Opus (model gewinnt)
  IF level == "sonnet": RETURN "general-sonnet"
  IF level == "haiku":  RETURN "general-haiku"   # Erlaubt in Welle-1 Explorer
# INVARIANTE (model-routing): subagent_type = nur registrierter Carrier; `model=` = autoritative Tier-Wahl.
# NIE einen nicht-registrierten/versions-gepinnten Agent-Typ (general-opus, general-sonnet-4) als Modell-Vehikel.
```

## COMMAND_MODEL_MAP — Command-basierter Cap (BL-125 AK-6)

```
# Wenn difficulty=easy (1 Worker): nutze COMMAND_MODEL_MAP direkt.
# Wenn difficulty>=normal (Wellen): ceiling wird durch COMMAND_MODEL_MAP gecappt.
# Verteilung per User-Genehmigung 2026-04-20 (Komplexitaets-Analyse):
COMMAND_MODEL_MAP = {
  # opus — Architektur & tiefe Abstraktion. ZUWEISUNG bleibt `model:"opus"` (sakrosankt) — das ist die
  # Intelligenz-Zuweisung. subagent = registrierter Carrier (general-sonnet); der Spawn `model:"opus"`
  # GEWINNT (Research 2026-05-31) -> laeuft echtes current Opus. KEIN general-opus mehr (existiert nicht).
  "_I_blueprintArchitect":  {subagent: "general-sonnet", model: "opus"},
  "_I_cleanCodeArchitect":  {subagent: "general-sonnet", model: "opus"},
  "_I_codeFullSystem":      {subagent: "general-sonnet", model: "opus"},
  "_TDD_refactorCode":      {subagent: "general-sonnet", model: "opus"},

  # sonnet — Worker-Standard (USER-OVERRIDE 2026-04-20: KEIN Haiku mehr)
  # Begruendung: Haiku halluzinierte Bash-Outputs bei _TDD_execute (Fake-Timestamps,
  # keine echten Test-Runs). Vertrauens-Verlust. Ex-haiku-Commands:
  # _TDD_execute, _TDD_check, _TDD_init, _I_mitose, _I_fanOut → alle jetzt sonnet.
  "DEFAULT":                {subagent: "general-sonnet", model: "sonnet"},
}

FUNKTION resolve_command_cap(command, ceiling):
  """Gibt Cap-Model fuer diesen Command zurueck (gecappt durch ceiling)."""
  mapping = COMMAND_MODEL_MAP.get(command, COMMAND_MODEL_MAP["DEFAULT"])
  IF model_rank(mapping.model) > model_rank(ceiling):
    Logge: "[MODEL-CAP] {command} wollte {mapping.model}, Ceiling={ceiling} — downgrade"
    return {subagent: model_fuer(ceiling), model: ceiling}
  return mapping
```

## Slicing-Guard (Session-Parameter)

```
# Lies slicing + tdd aus _session_params.md
#
# slicing=false Effekt (NUR Worktree-bezogen):
#   - SKIP: /_I_mitose + /_I_fanOut + /_I_fanIn (Worktree-Operationen)
#   - Blueprint LAEUFT normal (Architect, testSearch, goldDefine, patternLibrary, etc.)
#   - Slices werden SEQUENTIELL im gleichen Branch abgearbeitet (kein Parallel)
#   - Stufen-Loop laeuft normal (Stage 1 → alle Slices → Stage 2 → ...)
#   - TDD laeuft normal (gesteuert durch tdd-Parameter)
#
# tdd=false Effekt (unabhaengig von slicing):
#   - SKIP: TDD-Phase pro Stufe (/_TDD_orchestrate wird nicht aufgerufen)
#   - Blueprint + Verify laufen trotzdem
#
# slicing=false + tdd=true:
#   - Blueprint laeuft, Slices sequentiell im gleichen Branch
#   - TDD laeuft pro Stufe via /_TDD_orchestrate
#   - Kein fanOut/fanIn — alles in einem Branch
#
# slicing=false + tdd=false:
#   - Blueprint laeuft, Slices sequentiell im gleichen Branch
#   - Kein TDD — direkte Implementation via codeAtomic/codeIntegration/codeSystem
#   - Verify + Nachphase normal

worktree_parallel = (slicing == true)  # Steuert NUR ob Worktrees verwendet werden

IF slicing == false:
  Logge: "slicing=false → Sequentieller Modus (gleicher Branch, keine Worktrees)"
  Logge: "Blueprint + Stufen-Loop laufen normal. Slices sequentiell statt parallel."

IF tdd == false:
  Logge: "tdd=false → TDD-Phase SKIP. Blueprint + Verify laufen."

IF slicing == true:
  Logge: "slicing=true → Worktree-Modus (Mitose/FanOut/FanIn aktiv)"
```

## Stufen-Loop (nutzt Wellen-Spawn, bei slicing=true ODER tdd=true)

```
WHILE nicht_alle_slices_final:
  aktive_slices = [s fuer s in slices wenn nicht stufe_final[s]]

  FOR EACH slice IN aktive_slices:
    synthese = spawne_wellen(command, slice, aktuelle_stufe)

    # Query-Guard (I-14): Pruefe query_status im exit_report
    pruefe_query_status(synthese.exit_report)
    IF >50% query_status=missing → HiL-Eskalation

    # I→SC Return Check
    IF T1-T4 Trigger → Pipeline STOPP, SC_RECOVERY

    # Synthese-Status
    IF synthese.status == 'final': stufe_final[slice] = True
    ELSE: resume_zaehler += 1 (Stagnation bei >= 5)

  manifest.update()  # Nach JEDEM Batch-Zyklus
```

## INVARIANTEN

- Team Lead spawnt Workers, fuehrt KEINE Commands selbst aus
- Jeder Spawn bekommt PFLICHT-[SPAWN]-Log mit type/model/cmd/wave
- manifest.update() nach JEDEM Batch-Zyklus (nicht nur am Ende)
- Haiku NUR in Welle-1 Explorer (niemals auf Command-Level)
- HiL-Eskalation NUR bei echten Guards (>50% query_status=missing, T1-T4 Trigger)
- Stagnation-Grenze: resume_zaehler >= 5 → Abbruch mit Fehlermeldung
