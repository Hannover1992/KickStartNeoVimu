# /_D_orchestrate - Debloat-Orchestrator

```yaml
status: active
version: 1.0.0
created: 2026-02-26
op: Debloat
phase: orchestration
type: orchestration
chain_position: entry
team_based: false
```

---

```
+======================================================================+
| STANDALONE COMMAND: /_D_orchestrate {FEATURE} [--hard]              |
+======================================================================+
|                                                                        |
| ACTOR: DEBLOAT-ORCHESTRATOR (DU - die ausfuehrende Claude-Instanz)  |
| AGENTS: Kurzlebige Agents fuer _D_separate, _D_kollaps              |
|         1 Agent = 1 Command = 1 Response. Kein Worker-Loop.          |
|                                                                        |
| ZWECK: Orchestriert vollstaendigen Debloat-Prozess fuer ein Model.  |
|        Standalone: User ruft direkt auf wenn Model ausgeartet ist.  |
|        Pipeline: _SC_modelMaintain HARD-Trigger ruft automatisch auf.|
|                                                                        |
| TRIGGER:                                                               |
|   Manuell:   /_D_orchestrate OmniCommand                             |
|   Manuell:   /_D_orchestrate OmniCommand --hard (erzwingt Kollaps)  |
|   Pipeline:  _SC_modelMaintain erkennt HARD → ruft diesen Command   |
|                                                                        |
| COMMAND-CHAIN:                                                         |
|   _D_orchestrate (Orchestrator)                                        |
|     ↓ liest Model → entscheidet                                       |
|     → _D_separate (Protokoll anlegen, falls nicht vorhanden)         |
|     → _D_kollaps  (5-Phasen-Wahrheiten-Kollaps)                     |
|                                                                        |
| SOFT/HARD-TRIGGER (aus W06):                                           |
|   SOFT: >500 Zeilen ODER >8 neue W{n} seit letztem Kollaps          |
|         → Nur Scan-Report (--scan-only Modus)                        |
|   HARD: >700 Zeilen ODER >15 neue W{n} seit letztem Kollaps         |
|         → Vollstaendiger 5-Phasen-Kollaps                           |
|   --hard Flag: Erzwingt Kollaps unabhaengig von Zeilen/W{n}-Zahl   |
|                                                                        |
| CONTEXT-COLLAPSE-SICHER:                                               |
|   State IMMER im Manifest (D_PIPELINE_STATE Sektion), nie im Kontext.|
|   Nach jeder Phase Manifest aktualisieren, vor naechster Phase lesen.|
+======================================================================+
```

---

## Vertrag

```
╔═══════════════════════════════════════════════════════════════════════════╗
║  COMMAND: /_D_orchestrate {FEATURE} [--hard]                             ║
╠═══════════════════════════════════════════════════════════════════════════╣
║  LIEST (Input) - PFLICHT:                                                ║
║    1. {VAULT}/_manifest.md (D_PIPELINE_STATE, falls vorhanden)          ║
║    2. .claude/models/{FEATURE}_Model.md (Ziel-Model, MUSS EXISTIEREN)  ║
║                                                                          ║
║  LIEST (Input) - OPTIONAL:                                               ║
║    3. .claude/models/{FEATURE}_Protokoll.md (Vorhandensein pruefen)    ║
║                                                                          ║
║  MANIFEST-SCHREIB-MUSTER (ManifestSplit, ADR-3):                         ║
║    Pattern B: State-Write + Protokoll-Rollover (W18)                     ║
║    SCHREIBT STATE (_manifest.md):                                        ║
║      D_PIPELINE_STATE: trigger_level, kollaps_mode, last_run_date,      ║
║        separate_done, model_lines_before/after, last_run_result          ║
║    SCHREIBT PROTOKOLL (_manifest_protokoll.md, Rollover):               ║
║      Nach Schritt 4 (Abschluss): Rotiere D_PIPELINE_STATE[N-2]:         ║
║      Prepend an _manifest_protokoll.md (W18):                            ║
║        last_append + append_count++ im Frontmatter                       ║
║        ## D_orchestrate [{Datum}] {trigger_level}                        ║
║        [Archivierte Felder: trigger, kollaps_mode, lines_before→after]   ║
║                                                                          ║
║  SCHREIBT (Output) - PFLICHT:                                            ║
║    1. {VAULT}/_manifest.md                                               ║
║       → D_PIPELINE_STATE: Phase, Trigger-Level, Timestamp aktualisieren ║
║                                                                          ║
║  SCHREIBT (Output) - INDIREKT (via Sub-Agents):                         ║
║    2. .claude/models/{FEATURE}_Protokoll.md (via _D_separate Agent)    ║
║    3. .claude/models/{FEATURE}_Model.md (bereinigt, via _D_kollaps)    ║
║    4. .claude/models/{FEATURE}_Protokoll.md (INTEGRATED, via _D_kollaps)║
║                                                                          ║
║  INVARIANTEN:                                                            ║
║    - {FEATURE}_Model.md MUSS vor Aufruf existieren                     ║
║    - Manifest-Update nach JEDER Phase (Context-Collapse-Sicherheit)    ║
║    - Kein Kollaps ohne vorherige Protokoll-Datei (_D_separate erst)    ║
║    - WP-Hook: TODO (EC-F 80%, externe Klaerung ausstehend)            ║
║                                                                          ║
║  ACTOR: DEBLOAT-ORCHESTRATOR                                             ║
║    Liest Model, entscheidet Trigger-Level, koordiniert Sub-Commands.   ║
║    Kein Worker-Loop, kein Team noetig (2 kurzlebige Agents max).       ║
╚═══════════════════════════════════════════════════════════════════════════╝
```

---

## GLOBALE PARAMETER (/_param Override)

_D_orchestrate reagiert nicht auf difficulty/ceiling/floor Parameter.
Der Debloat-Prozess wird durch Komplexitaets-Schwellwerte ausgeloest (Zeilen-/W{n}-Trigger),
nicht durch Ressourcen-Limits. Globale Parameter haben hier keine Wirkung.

## GLOBALE PARAMETER — STRUKTURELLE AUSNAHME

_D_orchestrate ist bewusst NICHT nach 9-5-1 skalierbar:

**Grund:** _D_orchestrate ist **komplexitaets-getrieben**, nicht ressourcen-getrieben.
- Trigger: Zeilen-Anzahl (>500Z SOFT, >700Z HARD), nicht difficulty/ceiling/floor
- Dependency-Chain: _D_separate muss VOR _D_kollaps abgeschlossen sein (keine Parallelisierung moeglich)
- Max 2 Agents sequentiell (by design)

**GLOBAL_PARAM Wirkung:**
- GLOBAL_DIFFICULTY: Keine Wirkung (Trigger basiert auf Zeilen, nicht difficulty)
- GLOBAL_CEILING: Keine Wirkung (max 2 sequentielle Agents)
- GLOBAL_FLOOR: Keine Wirkung

Diese Ausnahme ist eine bewusste Design-Entscheidung, kein Implementierungs-Fehler.

---

## Chain-Position

```
_SC_modelMaintain (HARD) → **_D_orchestrate** → _D_separate → _D_kollaps
                                    ↑
                            User (jederzeit, standalone)
```

**Prev:** Keiner (Standalone-Entry) ODER `_SC_modelMaintain` (HARD-Trigger)
**Next:** `_D_separate` (Protokoll anlegen) → `_D_kollaps` (Kollaps-Mechanismus)

---

## SCHRITTE

### Schritt 0: Vorbedingungen pruefen

```
0. FEATURE-Herleitung (IF-8, name-herleitung.md):
   IF FEATURE nicht als Argument angegeben:
     Lies {WORKING_DIR}/_manifest.md  # per-Story (BL-155 AK-1)
     Suche SC_PIPELINE_STATE → feature:
     IF feature vorhanden: FEATURE = feature
       Logge: "FEATURE auto-hergeleitet aus Manifest (SC_PIPELINE_STATE): {FEATURE}"
     ELSE:
       Suche I_PIPELINE_STATE → feature:
       IF feature vorhanden: FEATURE = feature
         Logge: "FEATURE auto-hergeleitet aus Manifest (I_PIPELINE_STATE): {FEATURE}"
       ELSE:
         → FEHLER: "FEATURE nicht angegeben und nicht aus Manifest herleitbar"

1. Lies .claude/models/{FEATURE}_Model.md
   → Existiert? NEIN → Fehler: "Model nicht gefunden: {FEATURE}_Model.md"
   → JA → weiter

2. Lies {VAULT}/_manifest.md
   → Suche Sektion D_PIPELINE_STATE (falls vorhanden)
   → Notiere: last_collapse_date, last_collapse_lines, w_n_count_at_collapse

3. Flag --hard gesetzt?
   → JA: Trigger = HARD (erzwungen), weiter zu Schritt 2
   → NEIN: weiter zu Schritt 1
```

### Schritt 1: Trigger-Level bestimmen

```
Messe {FEATURE}_Model.md:
  - ZEILEN = Zeilenzahl (wc -l aequivalent: zähle Zeilen beim Lesen)
  - W_N_NEU = Anzahl W{n}-Bloecke mit Status OFFEN/BESTAETIGT
              seit last_collapse_date (aus Manifest)

# Index-Model-Erkennung (IF-10, Pfad A)
Lies Model-Frontmatter → model_type Feld
IF model_type == "index":
  Logge: "Index-Model erkannt: HARD-Trigger wird auf 2000 Zeilen angehoben (statt 700)"
  HARD_TRIGGER = 2000
  SOFT_TRIGGER = 1200
ELSE:
  # Standard-Schwellen (Content-Model)
  HARD_TRIGGER = 700
  SOFT_TRIGGER = 500

Entscheide Trigger-Level:
  IF ZEILEN > HARD_TRIGGER OR W_N_NEU > 15:
    TRIGGER = HARD
  ELIF ZEILEN > SOFT_TRIGGER OR W_N_NEU > 8:
    TRIGGER = SOFT
  ELSE:
    TRIGGER = KEIN → Schritt 4 (Kein Kollaps)

Aktualisiere Manifest: D_PIPELINE_STATE.trigger_level = {TRIGGER}
```

### Schritt 2: Protokoll-Datei sicherstellen

```
Pruefe: .claude/models/{FEATURE}_Protokoll.md existiert?

  NEIN → Spawne kurzlebigen Agent mit Command /_D_separate {FEATURE}:
    Prompt-Kern:
      "Du bist ein Single-Command-Agent. Fuehre /_D_separate {FEATURE} aus.
       Lies .claude/commands/_D_separate.md, befolge alle Schritte.
       Antworte einmal, dann fertig."
    → Warte auf Abschluss-Meldung
    → Aktualisiere Manifest: D_PIPELINE_STATE.separate_done = true

  JA → Pruefe YAML-Format (hat feature/type/blueprint Header?)
       → Format OK: weiter
       → Format veraltet: TODO-Flag im Manifest setzen, weiter
```

### Schritt 3: Kollaps ausfuehren

```
IF TRIGGER = SOFT:
  Spawne kurzlebigen Agent: /_D_kollaps {FEATURE} --scan-only
  Prompt-Kern:
    "Du bist ein Single-Command-Agent. Fuehre /_D_kollaps {FEATURE} --scan-only aus.
     Lies .claude/commands/_D_kollaps.md, befolge alle Schritte im --scan-only Modus.
     (Nur P1+P2: Cluster-Analyse, KEIN Schreiben ins Model/Protokoll)
     Gib Scan-Report aus. Antworte einmal, dann fertig."
  Manifest: D_PIPELINE_STATE.kollaps_mode = scan-only
  → Ausgabe: Scan-Report an User weitergeben

IF TRIGGER = HARD:
  Spawne kurzlebigen Agent: /_D_kollaps {FEATURE}
  Prompt-Kern:
    "Du bist ein Single-Command-Agent. Fuehre /_D_kollaps {FEATURE} aus.
     Lies .claude/commands/_D_kollaps.md, befolge ALLE 5 Phasen (P1-P5).
     Human-in-Loop bei P3 wenn Confidence <0.85: Pausiere und frage User.
     Antworte einmal (nach P5 oder HiL-Pause), dann fertig."
  Manifest: D_PIPELINE_STATE.kollaps_mode = full
```

### Schritt 4: Abschluss

```
Aktualisiere {VAULT}/_manifest.md Sektion D_PIPELINE_STATE:

  ## D_PIPELINE_STATE
  feature: {FEATURE}
  trigger_level: {KEIN|SOFT|HARD}
  kollaps_mode: {none|scan-only|full}
  separate_done: {true|false}
  last_run_date: {YYYY-MM-DD}
  last_run_result: {clean|scan-report|kollaps-abgeschlossen|fehler}
  model_lines_before: {N}
  model_lines_after: {M}   # nur bei full kollaps

Gib kurze Summary aus:
  - Feature: {FEATURE}
  - Trigger: {KEIN|SOFT|HARD}
  - Aktion: {Kein Kollaps noetig|Scan-Report erstellt|Kollaps abgeschlossen}
  - Model vorher/nachher: {N}Z → {M}Z (nur bei full kollaps)
```

### Schritt 4a: D_PIPELINE_STATE Rollover Sub-Schritt (Pattern B, W18)

Nach Abschluss von Schritt 4 (Manifest aktualisiert, Summary ausgegeben):

```
1. Lies _manifest.md: Suche D_PIPELINE_STATE-Eintraege aelter als N-2 Laeufe
   Falls >= 3 abgeschlossene D_orchestrate-Laeufe vorhanden:

2. Frontmatter _manifest_protokoll.md aktualisieren:
   last_append: {Datum}
   append_count: {N+1}

3. Prepend nach YAML-Frontmatter in _manifest_protokoll.md:
   ## D_orchestrate [{Datum}] {trigger_level}
   - feature: {FEATURE}
   - trigger_level: {KEIN|SOFT|HARD}
   - kollaps_mode: {none|scan-only|full}
   - last_run_result: {clean|scan-report|kollaps-abgeschlossen|fehler}
   - model_lines: {N}Z → {M}Z

4. Entferne archivierten Eintrag aus _manifest.md
   (nur der N-2 Lauf wird rotiert, aktueller D_PIPELINE_STATE bleibt)
```

---

## Ablauf-Diagramm

```
User: /_D_orchestrate {FEATURE} [--hard]
         │
         ▼
    Lese Model + Manifest
         │
    ┌────▼──────────────────────────┐
    │ Trigger bestimmen             │
    │ --hard? → HARD (erzwungen)    │
    │ >700Z / >15 W{n}? → HARD     │
    │ >500Z / >8 W{n}? → SOFT      │
    │ sonst? → KEIN                 │
    └────┬──────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │ Protokoll vorhanden?          │
    │ NEIN → _D_separate Agent     │
    │ JA   → weiter                 │
    └────┬──────────────────────────┘
         │
    ┌────▼──────────────────────────┐
    │ Kollaps-Aktion                │
    │ KEIN  → Meldung, fertig      │
    │ SOFT  → _D_kollaps --scan    │
    │ HARD  → _D_kollaps (voll)    │
    └────┬──────────────────────────┘
         │
         ▼
    Manifest aktualisieren + Summary
```

---

## QUICK-START

```bash
# Manueller Debloat (User entdeckt Bloat im OmniCommand):
/_D_orchestrate OmniCommand

# Erzwungener Kollaps (ignoriert Zeilen-Schwelle):
/_D_orchestrate OmniCommand --hard

# Anderes Projekt:
/_D_orchestrate DCSRE-93

# Was passiert:
# 1. Misst OmniCommand_Model.md (Zeilen + neue W{n})
# 2. Legt Protokoll an falls noetig (_D_separate)
# 3. Fuehrt Kollaps durch falls Trigger (SOFT=Scan, HARD=Voll)
# 4. Aktualisiert Manifest (D_PIPELINE_STATE)
# 5. Gibt Summary aus
```

---

## Fehler-Handling

| Fehler | Reaktion |
|--------|----------|
| `{FEATURE}_Model.md` nicht gefunden | Fehler ausgeben, abbrechen |
| `{FEATURE}_Protokoll.md` Anlage fehlgeschlagen | Manifest: fehler, Ursache dokumentieren, abbrechen |
| _D_kollaps meldet HiL-Pause | Pause ausgeben an User, auf Antwort warten |
| _D_kollaps Rollback | Manifest: rollback, alten Stand sichern |
| Manifest nicht schreibbar | Fehler ausgeben (Context-Collapse-Risiko!) |

---

## Siehe auch

- [[_D_separate]] - Protokoll-Datei anlegen
- [[_D_kollaps]] - 5-Phasen-Wahrheiten-Kollaps
- [[_D_migrate]] - Big-Bang-Migration bestehender Models (S2_Protokoll)
- [[_SC_modelMaintain]] - SOFT/HARD-Trigger-Quelle (v2.4+)
- [[ModelBloat_Model]] - W06 (Trigger), W07 (HiL), W08 (Dual-Track)

---

## TODO (EC-F offen)

```
WP-Hook: Nutzt WritePaper ein Model? Falls ja:
  _W_push_orchestrate → Debloat-Check → /_D_orchestrate {FEATURE}
  Klaerung: Parking-Lot Entry, extern abhaengig.
  Bis Klaerung: nur SC- und I-Pipeline-Integration aktiv.
```
