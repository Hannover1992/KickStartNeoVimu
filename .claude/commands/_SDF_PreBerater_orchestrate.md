---
status: active
version: 1.0
type: orchestrator
sub_type: pre_berater
model_tier: middle
feature: BL-124
handschuh_nr: 1
created: 2026-04-18
---

# _SDF_PreBerater_orchestrate (C9b)

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _SDF_PreBerater_orchestrate (C9b)                          ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST: _manifest.md (GLOBAL_MODUS, GLOBAL_HIL,                      ║
║           DF_PIPELINE_STATE.task_source, batch_current)              ║
║         _berater_outputs.md (Frontmatter: item_id, cycle_nr,         ║
║           nach C1/C2/C3: BERATER_OUTPUTS-Bloecke)                   ║
║  SCHREIBT: _berater_outputs.md Frontmatter (item_id, cycle_nr init)  ║
║            SC_PIPELINE_STATE.scope_mode (OQ-4: Orchestrator-Init)   ║
║            _session_params.md (Modus-Setup vor Item-Work, OQ-4)     ║
║            → delegiert Berater-Writes an C1/C2/C3                   ║
║  SCHREIBT NICHT: BERATER_OUTPUTS-Sub-Felder direkt                   ║
║                  _manifest.md DF_PIPELINE_STATE direkt               ║
║  ACTOR: Team Lead (Skill-Load) — Handschuh #1 von 3 (INV-5)         ║
║  SEQUENZ: Phase 0 Init → Phase 1 resumeGuard (C1) →                 ║
║           Phase 2 itemContext (C2) + [Pruning-Gate] →               ║
║           Phase 3 modusEntscheidung (C3)                             ║
║  INVARIANTEN: INV-1/INV-FACTORY-1 (SHOW MUST GO ON),                ║
║               INV-5 (genau 3 Handschuh-Wechsel, dieser ist #1),     ║
║               INV-6 (blocked=true → Phase 3 nicht aufrufen),        ║
║               W17 (Regression-Baseline BL-113a 3c9b669)             ║
╚══════════════════════════════════════════════════════════════════════╝
```

## INVARIANTEN — SHOW MUST GO ON

```
INV-FACTORY-1 (INV-1): GLOBAL_HIL=off → VOLLAUTOMATISCH
  # PFLASTER 2026-06-11 (BL-295 AK-5): HiL-Quelle ist AUSSCHLIESSLICH der hil-Param/GLOBAL_HIL,
  # NICHT GLOBAL_MODUS (PL-S2-06: BDF/Modus und HiL sind ORTHOGONAL). Vollautomatik haengt nur
  # an hil=off — unabhaengig vom Modus (small/big_dark_factory, manual). Frueher: "GLOBAL_MODUS=
  # dark_factory + GLOBAL_HIL=off" — der Modus-Konjunkt war HiL-Proxy-Kopplung (entfernt).
  ENDE-BEDINGUNGEN (einzig erlaubte Stops):
    PL-EMPTY | SDF-MAX-ITERATIONS | ABORT (harter Pipeline-Failure)

VERBOTEN (auch bei Context-Druck):
  - Fresh-Session-Empfehlung durch Team Lead
  - Mid-Run-Pause / "Soll ich fortfahren?" / "Darf ich weitermachen?"
  - AskUserQuestion ohne harten Pipeline-Failure (ABORT-Pfad)
  - Context-Budget als Abbruch-Grund

ERLAUBT:
  - Fail-Loud (ABORT + BDF-Signal ABORTED): HARD_FAILURE-Pfade (Phase 1 resumeGuard ABORTED)
  - Fail-Safe (CONTINUE + Warnung-Log): SOFT_DEGRADATION-Pfade (Phase 1 resumeGuard CORRECTED)
  - Auto-Resume via resumeGuard (C1) nach Context-Wiederaufnahme (K5-Fix)
  - EXIT_PRUNED (Exitcode 1): Alpha-Beta-Pruning bei blocked=true (Phase 2)

HARD_FAILURE → Fail-Loud (ABORT + BDF-Signal ABORTED):
  - resumeGuard.status == "aborted" (unkorrigierbarer State)
  - modusEntscheidung.gewaehlter_modus == null (kein Modus bestimmt)

SOFT_DEGRADATION → Fail-Safe (CONTINUE + Warnung-Log):
  - resumeGuard.status == "corrected" (Korrekturen angewendet, weiter)

K5-FIX (MUSS in C1 implementiert sein — hier als Reminder):
  resumeGuard Phase 0: IF GLOBAL_HIL=="off" AND sdf_status=="IDLE" → auto_resume=true
  KEIN AskUserQuestion bei auto_resume (SDF v0.8.0 Z494-509 Verletzung behoben)
```

## Aufruf-Interface

```
Skill(_SDF_PreBerater_orchestrate, args="{NAME}")

Parameter:
  {NAME} — Feature-Name (z.B. "BL-124")

Vorbedingung:
  - _berater_outputs.md existiert (M1 GATE PASS)
  - item_id + cycle_nr aus DF_PIPELINE_STATE bekannt
  - C1 (_SDF_berater_resumeGuard) implementiert mit K5-FIX

Ausgabe:
  - BERATER_OUTPUTS belegt (via C1+C2+C3-Delegation)
  - Exitcodes: 0=OK, 1=PRUNED, 2=FAIL

Logging-Format (NFR-4):
  [C9b_PreBerater] ENTRY item_id={item_id} cycle_nr={cycle_nr}
  [C9b_PreBerater] EXIT duration={ms}ms status={OK|PRUNED|FAIL} modus={modus}
```

## Sequenz Pseudo-Code

```
[C9b_PreBerater] ENTRY item_id={item_id} cycle_nr={cycle_nr}

# ═══ PHASE 0: INIT (Contract-Datei + Defaults setzen) ═══
PHASE 0: Init
  # INV-FACTORY-1 Basis-Guard (deterministisch, kein LLM)
  # PFLASTER 2026-06-11 (BL-295 AK-5): HiL-Quelle ist NUR GLOBAL_HIL/hil-Param, NICHT GLOBAL_MODUS
  # (PL-S2-06 Orthogonalitaet). Der fruehere global_modus-Read war HiL-Proxy-Kopplung — entfernt.
  global_hil   = lies _manifest.md → GLOBAL_HIL   # bzw. BL-174-Resolver: resolve --param=hil

  # item_id + cycle_nr aus DF_PIPELINE_STATE lesen (vorbelegt durch SDF/BDF)
  item_id  = DF_PIPELINE_STATE.batch_items[batch_current] ?? DF_PIPELINE_STATE.item_id
  cycle_nr = BERATER_OUTPUTS.cycle_nr ?? 1

  # _berater_outputs.md Frontmatter initialisieren (Phase-0-Write, OQ-4)
  Schreibe _berater_outputs.md Frontmatter:
    item_id:      {item_id}
    cycle_nr:     {cycle_nr}
    last_update:  {jetzt}
    last_berater: "C9b_init"

  # SC_PIPELINE_STATE.scope_mode vorbelegen (Default "full", wird nach C3 ueberschrieben)
  # OQ-4 Resolution: Orchestrator schreibt Scope — Berater C3 schreibt NUR BERATER_OUTPUTS
  SC_PIPELINE_STATE.scope_mode = "full"
  manifest.update()

  Logge: "[C9b_PreBerater] PHASE 0 DONE — Contract initialisiert, item={item_id}, cycle={cycle_nr}"

# ═══ PHASE 1: resumeGuard (C1) ═══
# K5-FIX: GLOBAL_HIL=off + IDLE → auto_resume (kein AskUserQuestion)
PHASE 1: Resume-Guard
  Skill(_SDF_berater_resumeGuard, args="{NAME}")
  resume = BERATER_OUTPUTS.resumeGuard

  # HARD_FAILURE: aborted → Fail-Loud (INV-FACTORY-1 konform: harter Failure erlaubt)
  IF resume.status == "aborted":
    Logge FEHLER: "[C9b_PreBerater] PHASE 1 resumeGuard ABORTED: {resume.corrections}"
    Schreibe BDF-Signal: ABORTED, reason="resumeGuard: {resume.corrections[0]}"
    [C9b_PreBerater] EXIT duration={ms}ms status=FAIL
    → RETURN exitcode=2

  # SOFT_DEGRADATION: corrected → CONTINUE mit Warnung
  IF resume.status == "corrected":
    Logge WARNUNG: "[C9b_PreBerater] PHASE 1 resumeGuard CORRECTED — Korrekturen angewendet: {resume.corrections}. Weiter."

  # OK oder CORRECTED → weiter
  Logge: "[C9b_PreBerater] PHASE 1 DONE — resumeGuard.status={resume.status}"

# ═══ PHASE 2: itemContext (C2) + Alpha-Beta-Pruning Gate ═══
# INV-6: blocked=true → Phase 3 NICHT aufrufen (Pruning liegt in C9b, nicht in C3)
PHASE 2: Item-Kontext laden + Pruning-Gate
  Skill(_SDF_berater_itemContext, args="{NAME}")
  ctx = BERATER_OUTPUTS.itemContext

  # Alpha-Beta-Pruning (INV-6): blocked=true → sofortiger Exit
  IF ctx.blocked == true:
    Logge: "[C9b_PreBerater] PHASE 2 PRUNED — item={ctx.item_id} blocked=true. modusEntscheidung SKIP. CONTINUE zum naechsten Item."
    [C9b_PreBerater] EXIT duration={ms}ms status=PRUNED
    → RETURN exitcode=1   # SDF reagiert mit CONTINUE (naechstes Item)

  Logge: "[C9b_PreBerater] PHASE 2 DONE — itemContext OK, blocked=false, tc_scope={ctx.tc_scope}"

# ═══ PHASE 3: modusEntscheidung (C3, opus/ceiling) ═══
# C3 ist der letzte Schritt — blocked=false ist Precondition (garantiert durch Phase 2)
PHASE 3: Modus-Entscheidung
  Skill(_SDF_berater_modusEntscheidung, args="{NAME}")
  modus_out = BERATER_OUTPUTS.modusEntscheidung

  # HARD_FAILURE: kein gueltiger Modus → Fail-Loud
  IF modus_out.gewaehlter_modus == null:
    Logge FEHLER: "[C9b_PreBerater] PHASE 3 modusEntscheidung FAIL — kein Modus bestimmt"
    Schreibe BDF-Signal: ABORTED, reason="modusEntscheidung: kein Modus"
    [C9b_PreBerater] EXIT duration={ms}ms status=FAIL
    → RETURN exitcode=2

  # _session_params.md: Modus-Setup fuer nachfolgende Main-Skill schreiben (OQ-4)
  # C9b ist der einzige Ort wo Modus-Setup vor Item-Work passt (Orchestrator-Verantwortung)
  Schreibe _session_params.md:
    gewaehlter_modus: {modus_out.gewaehlter_modus}
    pipeline_route:   {modus_out.pipeline_route}
    sc_mode:          {modus_out.sc_mode}
    scope_mode:       {modus_out.scope_mode}

  # SC_PIPELINE_STATE.scope_mode aktualisieren (ueberschreibt Phase-0-Default)
  IF modus_out.scope_mode != null:
    SC_PIPELINE_STATE.scope_mode = modus_out.scope_mode
    manifest.update()

  Logge: "[C9b_PreBerater] PHASE 3 DONE — MODUS={modus_out.gewaehlter_modus} route={modus_out.pipeline_route}"
  [C9b_PreBerater] EXIT duration={ms}ms status=OK modus={modus_out.gewaehlter_modus}
  → RETURN exitcode=0
```

## Exitcode-Semantik

| Exitcode | Status | Bedeutung | SDF-Reaktion |
|----------|--------|-----------|-------------|
| 0 | OK | Alle Phasen PASS, Modus bestimmt | Weiter mit Inline-Switch (C9a) |
| 1 | PRUNED | itemContext.blocked=true | CONTINUE (naechstes Item) |
| 2 | FAIL | Hard-Failure (resumeGuard aborted / kein Modus) | ABORT + BDF-Signal |

## Architektur-Notizen

- **Handschuh #1 von 3** (INV-5): C9b laeuft EINMAL pro Item, VOR dem Main-Skill. Kein zweiter Aufruf pro Item-Iteration.
- **Pruning liegt in C9b, nicht in C3** (INV-6): C3 bekommt blocked=true NIE zu sehen. Precondition garantiert durch Phase 2 Exit-PRUNED.
- **_session_params.md schreiben** (OQ-4 Resolution): C9b ist der einzige Ort wo Modus-Setup passt. Nicht in C3 (Berater-Scope-Verletzung: C3 schreibt nur BERATER_OUTPUTS).
- **SC_PIPELINE_STATE.scope_mode** (OQ-4): Default "full" in Phase 0, ueberschrieben in Phase 3 nach C3. Idempotent.
- **K5-FIX als Enforcement-Reminder**: C9b selbst implementiert K5-FIX NICHT — C1 (resumeGuard) ist zustaendig. Phase 1 relayed Ergebnis deterministisch.
