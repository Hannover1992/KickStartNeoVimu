---
status: active
version: 1.0.0
created: 2026-04-26
op: ResearchCycle
phase: meta
type: berater
chain_position: lookup
model_tier: middle
---

# /_SC_berater_modusMatrix (SC-Modus-Matrix BL-036)

[VERTRAG: LIEST SC_PIPELINE_STATE.sc_mode (aus Phase 1 teamSetup / Modus-Erkennung); SCHREIBT BERATER_OUTPUTS.modusMatrix.{schritt_aktiv, sdf_guard_result, pipeline_mode_log, autonomie_modus}]
[Cross-Reference: Phase 1 teamSetup (Schritt 1.1–1.4), Phase 3 STEUERUNG (pipeline_mode State Machine)]
[INVARIANTEN: Keine HiL-Entscheidung durch Berater — nur Lookup + Log. Transitionen gehen durch pipeline_mode_wechsel(). SDF-Guard loggt, erzwingt NICHT.]

---

## 1. SC Modus-Matrix (AK-03-04, BL-036)

| Schritt      | FULL | INLINE | REVIEW | ANALYSE | I_STANDALONE |
|--------------|------|--------|--------|---------|--------------|
| observe      | ✓    | ✓      | ✓      | ✓       | —            |
| modelMaint   | ✓    | ✓      | —      | ✓       | —            |
| qualityGate  | ✓    | ✓      | ✓      | ✓       | —            |
| hypothese    | ✓    | ✓      | —      | ✓       | —            |
| implement    | ✓    | ✓(inline)| —    | —       | —            |
| ergebnis     | ✓    | ✓      | ✓      | ✓       | —            |

**Lookup-Logik:** Gegeben `sc_mode` → welche Schritte sind aktiv?
Jeder Schritt mit `✓` wird in Phase 3 (STEUERUNG) gespawnt. `—` = Schritt wird uebersprungen (kein Agent-Spawn).

---

## 2. SDF→SC Guard — Abweichungs-Check (BL-142 Caller-Migration, NACH Modus-Erkennung)

```
# NACH CLI-Flag-Auswertung: Vergleiche SDF-Mode (DF_BATCH_STATE.modus) mit
# effektivem SC-Modus. Begruendung: Wenn SDF C3 dispatcht hat, soll SC den
# erwarteten Mode laufen. Abweichungen sind moeglich (z.B. Direct-Call mit
# CLI-Flag-Override) und werden geloggt, nicht erzwungen — User-Override-Hoheit.
IF sdf_guard_active == true:
  effektiver_modus = SC_PIPELINE_STATE.sc_mode   # Ergebnis der Modus-Erkennung oben
  IF effektiver_modus == sdf_mode_normalized:
    Logge: "[SDF-GUARD] SDF-Mode bestaetigt: {effektiver_modus}"
    Manifest: SC_PIPELINE_STATE.sdf_mode_original = sdf_mode_raw
    Manifest: SC_PIPELINE_STATE.sdf_mode_override = false
  ELSE:
    Logge WARNUNG: "[SDF-GUARD] Abweichung: SDF dispatcht {sdf_mode_normalized}, SC startet als {effektiver_modus}"
    Logge WARNUNG: "[SDF-GUARD] User darf uebersteuern — KEIN ABBRUCH (CLI-Flags haben Vorrang)"
    Manifest: SC_PIPELINE_STATE.sdf_mode_original = sdf_mode_raw
    Manifest: SC_PIPELINE_STATE.sdf_mode_override = true
```

---

## 3. pipeline_mode Initialisierung (EC-4, W200)

```
Manifest: pipeline_mode: SC
SC_I_LIFECYCLE.current_mode: SC
SC_I_LIFECYCLE.transition_log APPEND: {from: init/vorher, to: SC, reason: "PRE-CYCLE"}
```

---

## 4. Mode-Infix Archivierung (v3.1+, SV-3)

```
IF Manifest.SC_PIPELINE_STATE.sc_mode existiert AND sc_mode != angeforderter_modus:
  → Lifecycle-Guard "OBSERVE Mode-Infix" ausfuehren (siehe oben)
  → Alte OBSERVE-Dateien umbenennen BEVOR neuer Zyklus startet
```

---

## 5. Schritt 1.1a: G-SESSION-INIT (Stale-Task-Cleanup)

```
1. TaskList → gibt es Tasks mit status=in_progress?
   → NEIN: WEITER
   → JA: Laufendes Team erreichbar?
     → JA: HiL "Bestehendes Team gefunden. Fortsetzen? (j/n)"
     → NEIN: Auto-Cancel alle in_progress Tasks
             (TaskUpdate status=completed, subject="[STALE-CANCELLED] ...")
```

---

## 6. Schritt 1.1b: pipeline_mode State Machine (Z5: RF-38, W242, W245)

```
# Gueltige Zustaende:
VALID_STATES = [
  "READY", "SC", "SC_SYMBIOSE_I_ACTIVE", "SC_SYMBIOSE_I_DONE",
  "SC_SYMBIOSE_I_ABORTED", "POST_CYCLE", "READY_FOR_I", "I",
  "I_COMPLETE", "I_STANDALONE", "POST_PIPELINE", "SC_NACH_I_RUECKKEHR",
  "SC_ANALYSE"
]

# Gueltige Transitionen (von_zustand -> erlaubte_zustaende):
VALID_TRANSITIONS = {
  "init":                    ["SC", "I_STANDALONE"],
  "READY":                   ["SC", "I_STANDALONE"],
  "SC":                      ["SC_SYMBIOSE_I_ACTIVE", "POST_CYCLE", "SC"],
  "SC_SYMBIOSE_I_ACTIVE":    ["SC_SYMBIOSE_I_DONE", "SC_SYMBIOSE_I_ABORTED"],
  "SC_SYMBIOSE_I_DONE":      ["SC"],
  "SC_SYMBIOSE_I_ABORTED":   ["SC", "POST_CYCLE"],
  "POST_CYCLE":              ["READY_FOR_I", "I_STANDALONE"],
  "READY_FOR_I":             ["I"],
  "I":                       ["I_COMPLETE", "SC_NACH_I_RUECKKEHR", "SC_ANALYSE"],
  "I_COMPLETE":              ["POST_PIPELINE"],
  "SC_NACH_I_RUECKKEHR":     ["SC"],
  "SC_ANALYSE":              ["SC", "POST_CYCLE"],
  "I_STANDALONE":            ["POST_PIPELINE"],
  "POST_PIPELINE":           []
}

# Validierung bei jedem pipeline_mode Wechsel:
FUNKTION pipeline_mode_wechsel(aktuell, neu, reason):
  IF aktuell NOT IN VALID_TRANSITIONS:
    aktuell = "init"  # Fallback fuer ungekannten Zustand
  IF neu NOT IN VALID_TRANSITIONS[aktuell]:
    Logge WARNUNG: "[STATE-MACHINE] Ungueltiger pipeline_mode Uebergang: {aktuell} → {neu} (Grund: {reason})"
    IF GLOBAL_HIL != "off":
      HiL: "Ungueltiger State-Machine-Uebergang: {aktuell} → {neu}. [TROTZDEM] [ABBRUCH]"
    → Weiter (kein STOPP, aber geloggt — Defensiv)
  SC_I_LIFECYCLE.transition_log APPEND:
    {from: aktuell, to: neu, timestamp: ISO8601, reason: reason}
  Manifest: pipeline_mode = neu
```

---

## 7. Schritt 1.1c: Autonomie-Modus (Puppet Master Pattern) # (PM: Puppet-Master-Pattern)

```
# Lies GLOBAL_HIL aus _session_params.md (bereits geladen in Schritt 1.1)

IF GLOBAL_HIL == "off":
  autonomie_modus = "puppet_master"
  Logge: "Autonomie-Modus: PUPPET MASTER (HiL=off)"

  # Puppet Master Regeln:
  # 1. Team Lead spawnt fuer JEDEN SC-Schritt einen Worker-Agent
  # 2. Team Lead schreibt/liest NUR Manifest + Tasks
  # 3. Worker lesen Primaerquellen, implementieren, verifizieren
  # 4. Nach ERGEBNIS mit CONTINUE: naechster Zyklus AUTOMATISCH
  # 5. Nach ERGEBNIS mit DONE: POST-CYCLE automatisch starten

ELIF GLOBAL_HIL IN ["cycle", "phase"]:
  autonomie_modus = "semi_autonom"
  Logge: "Autonomie-Modus: Semi-Autonom (HiL={GLOBAL_HIL})"
  # Worker fuer Implementation, aber HiL-Checkpoints bei Cycle/Phase-Ende

ELIF GLOBAL_HIL == "manual":
  autonomie_modus = "minimal_hil"
  Logge: "Autonomie-Modus: Minimal-HiL (HiL=manual — nur Blocker)"

ELSE:  # Defensiver Fallback fuer unbekannte Werte
  autonomie_modus = "interaktiv"
  Logge: "Autonomie-Modus: Interaktiv (HiL={GLOBAL_HIL})"
```

---

## 8. Schritt 1.2: Team erstellen

```
TeamCreate: team_name="sc-{name}", description="Scientific Cycle - {name}"
```

---

## 9. BL-060 T3: Idempotenter TeamCreate Guard (RF-01, AK-01)

```
# Wird VOR dem ersten Wellen-Agent-Spawn ausgefuehrt (nicht beim Session-Start-TeamCreate oben).
# Guard ist idempotent: bei erneutem Aufruf (z.B. nach /compact) wird nur Manifest-Feld
# geprueft — kein doppelter TeamCreate ausgefuehrt.
IF {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.active_team.name != "sc-{NAME}":
  TeamCreate(team_name="sc-{NAME}")
Schreibe in {WORKING_DIR}/_manifest.md → SC_PIPELINE_STATE.active_team:
  name: "sc-{NAME}"
  created_at: {ISO-8601 jetzt}
  pipeline: "sc"
  wellen_tracking_enabled: true
```

---

## 10. Schritt 1.3: Tasks erstellen

→ Lies `{META}/sc/task-templates.md` fuer vollstaendige Task-Beschreibungen.

**PRE-CYCLE (einmalig):**

| # | Command | Blocked By | Hinweis |
|---|---------|------------|---------|
| CP-0 | PT_init-Guard | - | **NON-BLOCKING.** IF `.claude/patterns/` NICHT existiert → Team Lead spawnt PT_init-Agent: `/_PT_init {NAME}`. IF `.claude/patterns/` existiert → SKIP (Duplikat-Schutz in _PT_init Schritt 0 wuerde es ohnehin stoppen). Kein separater Agent noetig wenn SKIP. |
| CP-1 | /_D_status {NAME} | CP-0 | Zeilen-Karte als Baseline (KontextManagement v1.0). Team Lead fuehrt direkt aus (kein Agent). Bei HARD-Trigger: WARNING + Log (kein ABORT). Output: Zeilen-Karte im Manifest als Orientierung. |
| 0 | /_W_fetch | CP-1 | |
| 1 | /_taskDefinition | T0 | |
| 2 | /_model (Wellen-Tasks) | T1 | |

**CP-0 PT_init-Guard Logik:**
```
CP-0 (Team Lead direkt, NON-BLOCKING):
  IF .claude/patterns/ EXISTIERT:
    → SKIP: "Pattern Library bereits vorhanden — CP-0 uebersprungen."
    → Weiter mit CP-1 (keine Verzoegerung)
  ELSE:
    → SPAWN: Agent sc-{name}-ptinit
        subagent_type: {floor} (niedrigstes Modell)
        team_name: "sc-{name}"
        prompt: KURZLEBIG_PROMPT
        command: "/_PT_init {NAME}"
    → WARTE auf Agent-Abschluss (einmalig, kurz)
    → Verifiziere: .claude/patterns/ existiert jetzt
    → Weiter mit CP-1
```

**SC-CYCLE (Iteration 1):**

| # | Task Subject | Command | Blocked By | activeForm |
|---|-------------|---------|------------|------------|
| 3 | Observe: Findings sammeln | /_SC_observe | Task 2 | Collecting observations |
| 4 | Model pflegen | /_SC_modelMaintain | Task 3 | Maintaining model |
| 5 | Quality Gates pruefen | /_SC_qualityGate | Task 4 | Running quality gates |
| 6 | Hypothese formulieren | /_SC_hypothese | Task 5 | Formulating hypothesis |
| 7 | Implementieren (FULL: /_I_orchestrate, INLINE: /_SC_implement) | Modus-abhaengig | Task 6 | Implementing changes |
| 7a | Pattern extrahieren (optional) | /_PT_extract {NAME} | Task 7 | Extracting patterns (FULL/INLINE only) |
| 8 | Ergebnis sammeln | /_SC_ergebnis | Task 7a (oder 7) | Collecting results |

HINWEIS: Task 7a (PT-Extract) wird NUR gespawnt wenn:
  a) _PT_extract.md existiert (.claude/commands/_PT_extract.md)
  b) SC_PIPELINE_STATE.sc_mode IN [FULL, INLINE] (nicht REVIEW, nicht ANALYSE)
  c) implement-Step hat neue Pattern-Kandidaten identifiziert (exit_message enthaelt "Pattern-Kandidat")

**Wellen-Tasks:** Task 2, 3, 8 werden nach difficulty in Wellen aufgesplittet.
Team Lead erstellt N Tasks pro Welle (Explorer/Drafter/Synthese).
Siehe task-templates.md fuer Wellen-Task-Vorlagen.

---

## 11. Schritt 1.4: Agents spawnen

**SEQUENTIELLE PHASE** (Pipeline-Tasks):
```
# PFLASTER 2026-04-20: general-{model} Palette, haiku→sonnet Override
# MLG S3 Log-Doppel (2026-04-24): resolve() VOR Spawn + [SPAWN]-Top + [AGENT]-Bottom
r = resolve(command="{command}", wave="seq", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
Agent tool:
  name: "sc-{name}-{command}"
  subagent_type: r.subagent_type        # Soll aus Registry-Resolver
  model: r.model                         # explizit, kein null
  team_name: "sc-{name}"
  mode: "bypassPermissions"
  prompt: [KURZLEBIG_PROMPT]
# VOR SPAWN: Logge "[SPAWN] worker=sc-{name}-{command} type={r.subagent_type} model={r.model} cmd={command} wave=seq"
```

**WELLEN-PHASE** (model, observe, ergebnis bei normal/hard):
```
# PFLASTER 2026-04-20 (korrigiert): Haiku ERLAUBT in Welle-1 (Kartographierung/Explorer).
# Viele parallele Explorer → kein Einzel-Punkt-Versagen, Haiku reicht fuer RAG/Grep.
# Welle-2/3 (Drafter/Synthese) bleiben sonnet/opus (Einzel-Worker-Kritikalitaet).
# MLG S3 Log-Doppel (2026-04-24): Pro Welle VOR Spawn → resolve() nutzen.
#   r_w1 = resolve(command="{cmd}", wave="w1", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
#   r_w2 = resolve(command="{cmd}", wave="w2", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
#   r_w3 = resolve(command="{cmd}", wave="w3", difficulty={difficulty}, session_ceiling={ceiling}, session_floor={floor})
Welle 1 (Explorer, PARALLEL): N Agents mit subagent_type=r_w1.subagent_type ({floor}=haiku), model=r_w1.model, run_in_background=true
  → AMBIGUITY GATE (v3.1+, CaseStudy KV-2): Team Lead prueft ZWISCHEN Welle 1 und 2
Welle 2 (Drafter, PARALLEL):  N Agents mit subagent_type=r_w2.subagent_type ({middle}=sonnet), model=r_w2.model, run_in_background=true
Welle 3 (Synthese, 1 Agent):  1 Agent mit subagent_type=r_w3.subagent_type ({ceiling}=opus), model=r_w3.model

# VOR JEDEM SPAWN: Logge "[SPAWN] worker={worker_name} type={r.subagent_type} model={r.model} cmd={cmd} wave={W1|W2|W3} batch={i}/{N}"
# Der gespawnte Worker quittiert in Schritt 0 mit [AGENT] worker={name} | model={MODEL} | type={SUBAGENT_TYPE} | task={TASK}
```

---

## 12. kontext_constraint Vorbefuellung (CaseStudy MV-1, v3.1+)

**WANN:** VOR Welle-1-Spawn (Explorer-Tasks).
**WER:** Team Lead direkt.

```
IF difficulty == easy:
  kontext_constraint = OPTIONAL (Felder koennen leer sein)
ELSE (normal/hard):
  kontext_constraint = PFLICHT (alle 4 Felder muessen belegt sein)

  IF ein Feld ist leer/Placeholder:
    → FEHLER: "kontext_constraint unvollstaendig: {feld} fehlt"
    → Welle-1-Spawn BLOCKIERT bis alle 4 Felder befuellt

kontext_constraint:
  entry_point: "{Einstiegspunkt der Analyse — z.B. DicFaService.ProcessFile()}"
  boundary: "{Expliziter Scope — z.B. Nur Dateien im DicFa-Namespace}"
  negative_scope: "{Explizite Ausschluesse — z.B. NICHT: Helper-Klassen, NICHT: Logging}"
  relevanz_test: "{Prueffrage in Ja/Nein-Form — z.B. Hat der Code direkten Einfluss auf EM0012-Felder?}"
```

---

## 13. Ambiguity Gate (v3.1+, CaseStudy F-02/KV-2)

**WANN:** Nach Welle 1 (alle Explorer fertig), VOR Welle 2 (Drafter-Spawn).
**WER:** Team Lead direkt (kein Worker noetig).

```
NACH WELLE 1 ABSCHLUSS:

1. Lies .claude/crumbs/{NAME}_crumbs.md
2. Scanne nach Ambiguitaets-Mustern:
   - "Bedeutung unklar"
   - "PO klaeren" / "PO fragen"
   - "koennte bedeuten: a)... b)..."
   - "Annahme:" ohne Beleg
   - Fragezeichen in Feld-Definitionen

3. Fuer jeden Fund:
   IF Feld ist MUSS-Feld (aus Model/Spec):
     → SEVERITY: BLOCKER
   ELSE:
     → SEVERITY: WARNING

4. Entscheidung:
   IF keine BLOCKER → PROCEED (Welle 2 starten)
   IF BLOCKER vorhanden:
     HiL-Frage (auch bei hil=off, da BLOCKER):
       "Ambiguitaet in MUSS-Feld(ern) erkannt:
        - {feld1}: {ambiguitaets_text}
        - {feld2}: {ambiguitaets_text}

        Optionen:
        [PROCEED] Als RISIKO akzeptieren (Crumb wird WARNING)
        [BLOCK]   PO/Stakeholder fragen (Zyklus pausiert)
        [ASSUME]  Mit Annahme weiterarbeiten: {vorgeschlagene_annahme}"
```

**Warum:** In DCSRE-882 wurde "DicFileName" aus Crumbs falsch interpretiert
(bedeutete Package-Dateiname, nicht FileImport-Dateiname). Die resultierende
.jason-Kurskorrektur kostete ~1 Tag. Der Ambiguity Gate haette den Drafter
daran gehindert, auf Basis der Ambiguitaet zu planen.

**easy:** Kein Wellen-Modus, 1 Agent pro Step. Ambiguity Gate entfaellt (kein Welle-1/2-Split).
