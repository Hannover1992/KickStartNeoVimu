---
status: active
version: 1.0.0
created: 2026-04-26
op: ResearchCycle
phase: 2
type: berater
chain_position: middle
model_tier: middle
---

# /_SC_berater_kurzlebigPrompt (Phase 2 — SC Single-Command-Agent Prompts)

[VERTRAG: LIEST SC_PIPELINE_STATE aus {WORKING_DIR}/_manifest.md (geschrieben von Phase 1 teamSetup — siehe _SC_orchestrate.md Phase 1; BL-155 AK-1: SC_PIPELINE_STATE = per-Story)]
[SCHREIBT {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count nach jeder Welle]
[SCHREIBT {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.stufe bei SDF-HUB-Handschuh]
[Output BERATER_OUTPUTS.kurzlebigPrompt.{observe|hypothese|ergebnis|sdfHub|continueDecision}]
[Cross-Reference Phase 1: _SC_orchestrate.md § PHASE 1 — teamSetup definiert ceiling/floor/difficulty/autonomie_modus/sc_mode/NAME]

---

## 2.0 Zyklus-Orchestrierung (Puppet Master)

```
# ALLE Autonomie-Modi orchestrieren SCHRITT-FUER-SCHRITT mit Wellen.
# KEIN Fullcycle-Worker (W7-Verletzung: 1 Worker kann keine Wellen spawnen).
# Puppet Master = Team Lead spawnt JEDEN Schritt als eigenen Worker.
# Unterschied: puppet_master hat keine HiL-Pausen, semi_autonom hat HiL nach Zyklus.

FUER JEDEN ZYKLUS (cycle_nr = 1..max_cycles):

  # --- RESUME-GUARD (SDF-HUB, CaseStudy DCSRE-1430) ---
  # Wenn --resume-at=ergebnis → SC wurde von SDF nach I/TDD zurueckgerufen.
  # SC soll NICHT nochmal observe/hypothese laufen, sondern direkt Ergebnis sammeln.
  IF CLI_PARAM("--resume-at") == "ergebnis" AND cycle_nr == SC_PIPELINE_STATE.cycle_nr:
    Logge: "[RESUME] SC Z{cycle_nr}: Resume nach SDF-Hub I/TDD → direkt zu Ergebnis."
    manifest.reload()
    # I hat SC_SYMBIOSE_I_DONE + i_core_result ins Manifest geschrieben
    Lies i_core_result aus Manifest
    Manifest: pipeline_mode = SC (zurueck von SC_SYMBIOSE_I_DONE)
    Manifest: SC_PIPELINE_STATE.stufe = "ergebnis"
    # --resume-at wird nach erstem Resume GELOESCHT (kein endloser Skip)
    CLI_PARAM("--resume-at") = null
    → SKIP zu Schritt 6 (ERGEBNIS)

  # --- Schritt 1: OBSERVE (Wellen bei normal/hard) ---
  IF difficulty IN [normal, hard]:
    # BL-060 T3: WELLEN-COUNT INIT observe (RF-02, AK-03, INV-BL060-3)
    # observe: 0 Explorer, N_drafter Drafter + 1 Synthese
    N_drafter = 5 wenn hard, 3 wenn normal
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count:
      cmd: "observe"
      difficulty: "{difficulty}"
      team_name: "sc-{NAME}"
      planned:
        explorer: 0
        drafter: {N_drafter}
        synthese: 1
        total: {N_drafter + 1}
      spawned:
        explorer: 0
        drafter: 0
        synthese: 0
      wave_active: "drafter"
      violation: false
    # Welle 1: Drafter PARALLEL (hard=5, normal=3) — PFLASTER 2026-04-20: [SPAWN]-Log + explizites subagent_type
    # MLG S3 Log-Doppel (2026-04-24): resolve() VOR Spawn
    r = resolve(command="_SC_observe", wave="w1", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
    FUER i = 1..N_drafter:
      Logge: "[SPAWN] worker=sc-{name}-Z{cycle_nr}-observe-D{i:02d} type={r.subagent_type} model={r.model} cmd=_SC_observe wave=W1-drafter batch={i}/{N_drafter}"
      Agent(name="sc-{name}-Z{cycle_nr}-observe-D{i:02d}", subagent_type=r.subagent_type, model=r.model, PARALLEL)
    warte_alle()
    # BL-060 T3: spawned update nach Welle 1 (RF-02, AK-03)
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.spawned.drafter: {N_drafter}
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.wave_active: "synthese"
    # Welle 2: Synthese (1 Agent) — PFLASTER 2026-04-20
    r_s = resolve(command="_SC_observe", wave="w2", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
    Logge: "[SPAWN] worker=sc-{name}-Z{cycle_nr}-observe-synthese type={r_s.subagent_type} model={r_s.model} cmd=_SC_observe wave=W2-synthese"
    Agent(name="sc-{name}-Z{cycle_nr}-observe-synthese", subagent_type=r_s.subagent_type, model=r_s.model)
    warte()
    # BL-060 T3: spawned update nach Synthese
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.spawned.synthese: 1
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.wave_active: null
  ELSE:  # easy
    r = resolve(command="_SC_observe", wave="seq", difficulty="easy", session_ceiling={ceiling}, session_floor={floor})
    Logge: "[SPAWN] worker=sc-{name}-Z{cycle_nr}-observe type={r.subagent_type} model={r.model} cmd=_SC_observe wave=seq"
    Agent(name="sc-{name}-Z{cycle_nr}-observe", subagent_type=r.subagent_type, model=r.model)
    warte()

  # --- Schritt 2: MODELMAINTAIN (1 Agent, sequentiell) ---
  r = resolve(command="_SC_modelMaintain", wave="seq", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
  Logge: "[SPAWN] worker=sc-{name}-Z{cycle_nr}-modelMaintain type={r.subagent_type} model={r.model} cmd=_SC_modelMaintain wave=seq"
  Agent(name="sc-{name}-Z{cycle_nr}-modelMaintain", subagent_type=r.subagent_type, model=r.model)
  warte()

  # --- Schritt 2a: Fire-Together Trigger — ENTFERNT (BL-045 Vault-First) ---
  # BL-045: _model/_SC_modelMaintain schreibt direkt in Vault. Kein Post-Synthese-Sync noetig.
  # _W_fireTogether ist als OBSOLET markiert (status: obsolet, obsoleted_by: BL-045).

  # --- Schritt 3: QUALITYGATE (1 Agent, sequentiell) ---
  # MLG S3 Log-Doppel (2026-04-24): resolve() + [SPAWN]-Log
  r = resolve(command="_SC_qualityGate", wave="seq", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
  Logge: "[SPAWN] worker=sc-{name}-Z{cycle_nr}-qualityGate type={r.subagent_type} model={r.model} cmd=_SC_qualityGate wave=seq"
  Agent(name="sc-{name}-Z{cycle_nr}-qualityGate", subagent_type=r.subagent_type, model=r.model)
  warte()

  # --- Schritt 4: HYPOTHESE (Wellen bei normal/hard) ---
  IF difficulty IN [normal, hard]:
    # BL-060 T3: WELLEN-COUNT INIT hypothese (RF-02, AK-03, INV-BL060-3)
    # hypothese: 0 Explorer, N_drafter Drafter + 1 Synthese
    N_drafter = 5 wenn hard, 3 wenn normal
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count:
      cmd: "hypothese"
      difficulty: "{difficulty}"
      team_name: "sc-{NAME}"
      planned:
        explorer: 0
        drafter: {N_drafter}
        synthese: 1
        total: {N_drafter + 1}
      spawned:
        explorer: 0
        drafter: 0
        synthese: 0
      wave_active: "drafter"
      violation: false
    # Welle 1: Drafter PARALLEL (hard=5, normal=3) — MLG S3 Log-Doppel (2026-04-24)
    r = resolve(command="_SC_hypothese", wave="w1", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
    FUER i = 1..N_drafter:
      Logge: "[SPAWN] worker=sc-{name}-Z{cycle_nr}-hypothese-D{i:02d} type={r.subagent_type} model={r.model} cmd=_SC_hypothese wave=W1-drafter batch={i}/{N_drafter}"
      Agent(name="sc-{name}-Z{cycle_nr}-hypothese-D{i:02d}", subagent_type=r.subagent_type, model=r.model, PARALLEL)
    warte_alle()
    # BL-060 T3: spawned update nach Welle 1 (RF-02, AK-03)
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.spawned.drafter: {N_drafter}
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.wave_active: "synthese"
    # Welle 2: Synthese (1 Agent)
    r_s = resolve(command="_SC_hypothese", wave="w2", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
    Logge: "[SPAWN] worker=sc-{name}-Z{cycle_nr}-hypothese-synthese type={r_s.subagent_type} model={r_s.model} cmd=_SC_hypothese wave=W2-synthese"
    Agent(name="sc-{name}-Z{cycle_nr}-hypothese-synthese", subagent_type=r_s.subagent_type, model=r_s.model)
    warte()
    # BL-060 T3: spawned update nach Synthese
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.spawned.synthese: 1
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.wave_active: null
  ELSE:  # easy
    r = resolve(command="_SC_hypothese", wave="seq", difficulty="easy", session_ceiling={ceiling}, session_floor={floor})
    Logge: "[SPAWN] worker=sc-{name}-Z{cycle_nr}-hypothese type={r.subagent_type} model={r.model} cmd=_SC_hypothese wave=seq"
    Agent(name="sc-{name}-Z{cycle_nr}-hypothese", subagent_type=r.subagent_type, model=r.model)
    warte()

  # --- Schritt 5: IMPLEMENT (modus-abhaengig) ---
  # ═══ SDF-HUB INVARIANTE (CaseStudy DCSRE-1430) ═══
  # ANTI-PATTERN: Agent(prompt="/_I_orchestrate ...") ← VERBOTEN (W7, PM)
  # ANTI-PATTERN: Skill("_I_orchestrate") direkt ← VERBOTEN (SDF uebersprungen!)
  # RICHTIG: Handschuh zurueck an SDF. SDF routet zu I → (TDD) → SC(ergebnis).
  # Heilige Trinitaet: SC ↔ SDF ↔ I ↔ SDF ↔ TDD — SDF ist IMMER dazwischen.
  #
  # BL-060 T3: INV-BL060-5 Worker-Mode-Pfad — KEINE wellen_count-Schreibung (RF-06)
  # pipeline_mode=SC_SYMBIOSE_I_ACTIVE: I-Worker erbt das sc-{NAME}-Team.
  # I-Pipeline traegt EIGENES wellen_count in I_PIPELINE_STATE (nicht SC_PIPELINE_STATE).
  # Diese Stelle NICHT aendern — nur dokumentiert, nicht enforced durch SC.
  IF sc_mode IN [FULL, INLINE]:
    Manifest: SC_PIPELINE_STATE.stufe = "SC_NEEDS_IMPL"
    Manifest: SC_PIPELINE_STATE.sc_impl_request = {
      mode: sc_mode,                    # FULL oder INLINE
      cycle_nr: cycle_nr,
      hypothese_ref: "SC_HYPOTHESE_Z{cycle_nr}"  # Referenz auf Hypothese im Manifest
    }
    Logge: "[SDF-HUB] SC Z{cycle_nr}: Hypothese DONE → Handschuh zurueck an SDF."
    Logge: "[SDF-HUB] SC pausiert. SDF routet: I → (TDD) → SC --resume-at=ergebnis"
    → EXIT (SC pausiert, SDF uebernimmt Implement-Routing)
  # REVIEW/ANALYSE: SKIP (kein Implement-Step, weiter zu Ergebnis)

  # --- Schritt 6: ERGEBNIS (Wellen bei normal/hard, mit Modell-Downgrade) ---
  IF difficulty IN [normal, hard]:
    # BL-060 T3: WELLEN-COUNT INIT ergebnis (RF-02, AK-03, INV-BL060-3)
    # ergebnis: 0 Explorer, N_sammler Drafter + 1 Synthese
    N_sammler = 9 wenn hard, 5 wenn normal
    sammler_model = sonnet wenn ceiling=opus, haiku wenn ceiling=sonnet, haiku wenn ceiling=haiku
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count:
      cmd: "ergebnis"
      difficulty: "{difficulty}"
      team_name: "sc-{NAME}"
      planned:
        explorer: 0
        drafter: {N_sammler}
        synthese: 1
        total: {N_sammler + 1}
      spawned:
        explorer: 0
        drafter: 0
        synthese: 0
      wave_active: "drafter"
      violation: false
    # Welle 1: Sammler PARALLEL (hard=9, normal=5), Modell-Downgrade
    # MLG S3 Log-Doppel (2026-04-24): resolve() nutzt command-spezifisches Downgrade-Mapping
    r = resolve(command="_SC_ergebnis", wave="w1", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
    FUER i = 1..N_sammler:
      Logge: "[SPAWN] worker=sc-{name}-Z{cycle_nr}-ergebnis-DS{i:02d} type={r.subagent_type} model={r.model} cmd=_SC_ergebnis wave=W1-sammler batch={i}/{N_sammler}"
      Agent(name="sc-{name}-Z{cycle_nr}-ergebnis-DS{i:02d}", subagent_type=r.subagent_type, model=r.model, PARALLEL)
    warte_alle()
    # BL-060 T3: spawned update nach Welle 1 (RF-02, AK-03)
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.spawned.drafter: {N_sammler}
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.wave_active: "synthese"
    # Welle 2: Synthese (1 Agent), auch Downgrade
    r_s = resolve(command="_SC_ergebnis", wave="w2", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
    Logge: "[SPAWN] worker=sc-{name}-Z{cycle_nr}-ergebnis-synthese type={r_s.subagent_type} model={r_s.model} cmd=_SC_ergebnis wave=W2-synthese"
    Agent(name="sc-{name}-Z{cycle_nr}-ergebnis-synthese", subagent_type=r_s.subagent_type, model=r_s.model)
    warte()
    # BL-060 T3: spawned update nach Synthese
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.spawned.synthese: 1
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count.wave_active: null
  ELSE:  # easy
    r = resolve(command="_SC_ergebnis", wave="seq", difficulty="easy", session_ceiling={ceiling}, session_floor={floor})
    Logge: "[SPAWN] worker=sc-{name}-Z{cycle_nr}-ergebnis type={r.subagent_type} model={r.model} cmd=_SC_ergebnis wave=seq"
    Agent(name="sc-{name}-Z{cycle_nr}-ergebnis", subagent_type=r.subagent_type, model=r.model)
    warte()

  # --- Schritt 7: CONTINUE/DONE Entscheidung (Team Lead direkt) ---
  manifest.reload()

  # DONE_SCHWELLE: SRS-basierte Terminierung (AufwandsMetrik v1.0, AK-M8)
  # Wert: 15 (5 Punkte unter SRS-NIEDRIG-Schwelle von 20)
  # SRS kann > 100 sein (INV-1, DCSRE-98: SRS=115) — absolute Unter-Grenze
  # KONSISTENZ: _SC_qualityGate.md (SRS-Schwellen 20/60/85)
  DONE_SCHWELLE = 15

  IF SC_PIPELINE_STATE.sc_status == "DONE" OR manifest.SC_Z{cycle_nr}_SRS <= DONE_SCHWELLE:
    Logge: "Zyklus {cycle_nr}: DONE. Starte POST-CYCLE."
    # BL-060 T3: wellen_count = null Reset nach SC-Pipeline-Ende (RF-02, W11-Reset-Konformitaet)
    Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.wellen_count: null
    → Phase 3.4 (DONE-Decision)
    BREAK
  ELSE:
    Logge: "Zyklus {cycle_nr}: CONTINUE (SRS={srs}). Naechster Zyklus."

    # HiL-Pause (nur semi_autonom):
    IF autonomie_modus == "semi_autonom":
      HiL: "Zyklus {cycle_nr} abgeschlossen. SRS={srs}. [CONTINUE] [DONE] [ABORT]"
      → User-Entscheidung verarbeiten

    → Naechste Iteration (cycle_nr += 1)
```

**WICHTIG: Kein FULLCYCLE_PROMPT mehr.**
Ein einzelner Worker kann keine Wellen orchestrieren (W7-Constraint).
Team Lead muss JEDEN Schritt einzeln spawnen — genau wie in /_A_orchestrate.
Puppet Master = autonome Schritt-fuer-Schritt-Orchestrierung OHNE HiL-Pausen.
Semi-autonom = gleich, aber MIT HiL-Pause nach jedem Zyklus.
Interaktiv = gleich, aber MIT HiL-Pause nach jedem Schritt.

---

## 2.1 Single-Command-Agent Prompt (interaktiver Modus)

```
Du bist ein Single-Command-Agent fuer den Scientific Cycle.
Agent-Name: sc-{name}-{command}
Team: sc-{name}

=== INTRO-LOG (Schritt 0, PFLICHT — MLG S3 Log-Doppel) ===

ERSTE Zeile deiner Antwort (Runtime-Watchdog matched auf dieses Format):
[AGENT] worker=sc-{name}-{command} | model={MODEL} | type={SUBAGENT_TYPE} | task={TASK_SUMMARY}

Felder:
  worker={AGENT_NAME}          — muss identisch mit Spawn-Name sein (Top-Log-Bottom-Match)
  model={MODEL}                — aus Spawn-Kontext (resolve().model)
  type={SUBAGENT_TYPE}         — aus Spawn-Kontext (resolve().subagent_type)
  task={5-10 Woerter Summary}  — was dieser Command in einem Satz tut

DANACH erst das uebliche Tool-Call-Verhalten.

=== DEIN AUFTRAG ===

Genau 1 Command ausfuehren, dann fertig.

Command:     {COMMAND_PATH} {NAME} {DIFFICULTY}
Task-ID:     {TASK_ID}

=== WISSEN ABRUFEN (Optional) ===

Falls feature-lokales Wissen vorhanden:
  mcp__cleancoder__query(
    query_text="[dein Fokus]",
    collection="local_knowledge_{FEATURE_ID}",
    limit=3
  )
  {FEATURE_ID} = sanitized Feature-Name (lowercase, underscores)

=== SCHRITTE ===

1. Lade den Command via Skill-Tool:
   Skill(skill="{COMMAND_NAME}", args="{NAME} {DIFFICULTY}")
   WICHTIG: Nutze das Skill-Tool — NICHT die .md-Datei direkt lesen!
2. Fuehre den geladenen Skill vollstaendig aus.
3. TaskUpdate {TASK_ID} status=completed
4. SendMessage an "team-lead":
   "{COMMAND} {NAME}: [2-3 Saetze Summary]"

=== REGELN ===

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- IMMER Skill-Tool verwenden
- NUR dieser eine Command, dann fertig
- Manifest ({WORKING_DIR}/_manifest.md) nach Command aktualisieren
- Arbeite gruendlich, nicht schnell
```

---

## 2.2 Wellen-Phase Prompt (fuer Wellen-Worker)

```
Du bist ein Wellen-Worker fuer den Scientific Cycle.
Agent-Name: sc-{wellen-name}
Team: sc-{name}

=== INTRO-LOG (Schritt 0, PFLICHT — MLG S3 Log-Doppel) ===

ERSTE Zeile deiner Antwort (Runtime-Watchdog matched auf dieses Format):
[AGENT] worker=sc-{wellen-name} | model={MODEL} | type={SUBAGENT_TYPE} | task={WELLE-SUMMARY}

DANACH erst das uebliche Tool-Call-Verhalten.

=== DEIN AUFTRAG ===

Genau 1 Welle ausfuehren, dann fertig.

Welle:       {WELLEN-BESCHREIBUNG}
Task-ID:     {TASK_ID}

=== ROLLEN-ERKENNUNG ===

Deine Rolle kommt direkt aus diesem Prompt (KEIN TaskGet noetig):
- Welle 1 (Exploration): Lies Crumbs/Model, schreibe exploration/{NAME}-E{NN}-{fokus}.md
- Welle 2 (Drafts): Lies Crumbs + Model + Exploration (NUR als Kompass), schreibe drafts/*-D{NN}-*.md
  # ═══ INV-SP-1 (RF-08): Anti-Stille-Post Primaerquellen-Pflicht ═══
  # Explorer-Outputs sind Wegweiser (drogowskaz), KEINE Faktenquelle.
  # Drafter MUSS Primaerquellen SELBST lesen: Model.md, Commands, Task.md, Code.
  # Stille-Post-Anti-Pattern: haiku beobachtet → sonnet interpretiert → Fehler-Kaskade.
  # KONTEXT-ANKER: Pruefe jeden Befund gegen kontext_constraint
  #   - Befund in negative_scope → IGNORE (nicht aufnehmen)
  #   - Befund ausserhalb boundary → [WARN-SCOPE] markieren
  #   - Befund besteht relevanz_test nicht → [GRENZWERTIG] markieren
  #   - [GRENZWERTIG] als Hauptpfad → VERBOTEN
- Welle 3 (Synthese): Lies Crumbs + Model + Drafts (NUR als Kompass), verifiziere an Primaerquellen
  # ═══ INV-SP-1 (RF-08): Anti-Stille-Post Primaerquellen-Pflicht ═══
  # Drafts sind Inspiration, NICHT Faktenquelle.
  # Synthese MUSS JEDE Aussage an Primaerquellen verifizieren (Crumbs, Task.md, Code).
  # SD-Agents (Spec-Drafter) lesen Primaerquellen DIREKT, nie ueber Drafts-Output (AK-08-04).

=== KONTEXT-ANKER (wenn kontext_constraint vorhanden) ===

{KONTEXT_CONSTRAINT}

=== SCHRITTE ===

1. Fuehre die zugewiesene Welle aus.
2. TaskUpdate {TASK_ID} status=completed
3. SendMessage an "team-lead": "{WELLE} {NAME}: [2-3 Saetze Summary]"

=== REGELN ===

- KEIN git commit, KEIN git push
- KEIN Sub-Agent spawnen (W7-Constraint)
- NUR diese eine Welle, dann fertig
```

---

## 2.3 kontext_constraint Block-Template (CaseStudy MV-1, v3.1+)

Team Lead setzt `{KONTEXT_CONSTRAINT}` im Wellen-Phase Prompt. Bei easy kann der Block leer bleiben:

```
=== KONTEXT-ANKER (lies ZUERST — steuert Lese-Prozess) ===

kontext_constraint:
  entry_point: "{ENTRY_POINT}"
  boundary: "{BOUNDARY}"
  negative_scope: "{NEGATIVE_SCOPE}"
  relevanz_test: "{RELEVANZ_TEST}"

PRUEFREGEL (Welle 1 Explorer — fuer JEDEN Befund):
  1. Liegt die Datei/Klasse im boundary? → NEIN: [WARN-SCOPE] markieren
  2. Ist die Datei/Klasse in negative_scope? → JA: IGNORIEREN
  3. Besteht der relevanz_test? → NEIN: [GRENZWERTIG] markieren

PRUEFREGEL (Welle 2 Drafter — nach SP-FIX Verifikation):
  1. Befund in negative_scope → IGNORE
  2. Befund ausserhalb boundary → [WARN-SCOPE] Block
  3. relevanz_test schlaegt fehl → [GRENZWERTIG] Tag + Begruendung
  4. GRENZWERTIG-Befund als Hauptpfad: → VERBOTEN, eskaliere als WARN

PRUEFREGEL (Welle 3 Synthese):
  [WARN-SCOPE] mit Abhaengigkeit zu entry_point → Als Risiko-Kontext aufnehmen
  [WARN-SCOPE] ohne Abhaengigkeit → Verwerfen + Notiz
  [GRENZWERTIG] mit Begruendung → Mit Einschraenkung aufnehmen
  [GRENZWERTIG] ohne Begruendung → Verwerfen
```

**easy-Modus (kontext_constraint OPTIONAL):**
```
(kontext_constraint — easy, optional)
kontext_constraint:
  entry_point: ""
  boundary: ""
  negative_scope: []
  relevanz_test: ""
```
Wenn alle Felder leer: PRUEFREGEL entfaellt. Normaler Wellen-Flow ohne Scope-Filter.

---

## INVARIANTEN

- INV-W7: Kein Worker spawnt Sub-Agents (W7-Constraint gilt absolut)
- INV-BL060-3: wellen_count MUSS vor jeder Welle initialisiert werden (RF-02, AK-03)
- INV-BL060-5: SC schreibt KEIN wellen_count fuer I-Pipeline (I traegt eigenes I_PIPELINE_STATE)
- INV-SDF: SC ↔ SDF ↔ I ↔ SDF ↔ TDD — SDF ist IMMER Intermediar bei Implement-Routing
- INV-SP-1: Anti-Stille-Post — jede Welle liest Primaerquellen direkt (RF-08)
- INV-RESUME: --resume-at=ergebnis wird nach erstem Resume auf null gesetzt (kein endloser Skip)
- INV-DONE: DONE_SCHWELLE = 15 (absolut, SRS-basiert, konsistent mit _SC_qualityGate.md)
