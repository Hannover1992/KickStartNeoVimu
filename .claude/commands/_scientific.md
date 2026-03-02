# Forschungszyklus: Scientific Method

Du fuehrst einen vollstaendigen wissenschaftlichen Forschungszyklus durch.

## Aufruf

```
/_scientific {NAME} [FRAGE]
```

- **NAME** (Pflicht): Model-Name, z.B. `Dateiabholung`, `Auth-Flow`
- **FRAGE** (Optional): Die wissenschaftliche Frage / das Problem

---

## VERTRAG (Pflicht-I/O)

```
╔═══════════════════════════════════════════════════════════════╗
║  COMMAND: /_scientific {NAME}                                ║
╠═══════════════════════════════════════════════════════════════╣
║                                                               ║
║  META-COMMAND: Orchestriert die einzelnen Phasen.             ║
║  Delegiert an: /_taskDefinition, /_spec, /_model, /_gap,      ║
║                /_SC_observe, /_SC_modelMaintain,               ║
║                /_SC_qualityGate, /_SC_hypothese,               ║
║                /_SC_implement, /_SC_ergebnis                   ║
║                                                               ║
║  LIEST:                                                       ║
║    .claude/analysis/_manifest.md (Zustand ermitteln)          ║
║                                                               ║
║  SCHREIBT:                                                    ║
║    Nichts direkt - delegiert an Sub-Commands.                 ║
║    Jeder Sub-Command schreibt seine eigenen Dateien           ║
║    gemaess seinem VERTRAG.                                    ║
║                                                               ║
║  COMPACT-SICHER:                                              ║
║    Kann JEDERZEIT unterbrochen und fortgesetzt werden.        ║
║    Manifest trackt wo der Zyklus steht.                       ║
║    Nach /compact: /_scientific {NAME} liest Manifest          ║
║    und setzt an der richtigen Stelle fort.                    ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

---

## Workflow

```
PRE-CYCLE (einmalig):

  Frage definieren ──▶ /_taskDefinition {NAME} ──▶ crumbs/{NAME}_crumbs.md
                                                          │
SPEC (einmalig):                                          ▼

  /_spec {NAME} ──LIEST crumbs+Task──▶ specs/{NAME}_Spec.md (SOLL)
                                                     │
INIT (einmalig):                                     ▼

  /_model {NAME} hard ──LIEST crumbs──▶ models/{NAME}_Model.md (IST)
                                                     │
GAP (einmalig + Re-Eval):                            ▼

  /_gap {NAME} ──LIEST SPEC+MODEL──▶ synthese/{NAME}-GAP.md (Delta)
                                                     │
ITERATIVER ZYKLUS:                                   ▼

  /_SC_observe → /_SC_modelMaintain → /_SC_qualityGate
       │                                        │
       │                                        ▼
       │                              /_SC_hypothese → /_SC_implement → TEST → [/_SC_ergebnis]
       ▲                                                                            │
       └────────────────────────────────────────────────────────────────────────────┘
              (Rohdaten → /_SC_observe sammelt Findings,
               /_SC_modelMaintain updated MODEL)
```

---

## Phase 0: Task-Definition + Kruemmel sammeln (einmalig)

Delegiert an: `/_taskDefinition {NAME} [easy|normal|hard]`

Sammelt Rohmaterial aus `.claude/pileOfMud/`, verarbeitet es zu strukturierten
Kruemmeln und definiert die Aufgabe in `.claude/Task.md`.

**Ergebnis:**
- `.claude/Task.md` (Aufgaben-Definition)
- `.claude/crumbs/{NAME}_crumbs.md` (Strukturierte Kruemmel)

---

## Phase 0b: Spezifikation erstellen (einmalig)

Delegiert an: `/_spec {NAME} [easy|normal|hard]`

Definiert den SOLL-Zustand als Referenz fuer alle weiteren Phasen.
Liest Task.md und crumbs als Input.

**Ergebnis:** `.claude/specs/{NAME}_Spec.md` (SOLL-Definition)

---

## Phase 1: Model initialisieren (einmalig)

Delegiert an: `/_model {NAME} hard`

Liest Kruemmel aus `.claude/crumbs/{NAME}_crumbs.md` als Orientierung.
Jede Welle schreibt auf Disk. Zwischen Wellen kann /compact ausgefuehrt werden.
Siehe `/_model` VERTRAG fuer Details.

**Ergebnis:** `.claude/models/{NAME}_Model.md` (IST-Zustand)

---

## Phase 1b: Gap-Analyse (einmalig + Re-Eval nach Zyklen)

Delegiert an: `/_gap {NAME} [easy|normal|hard]`

Vergleicht SPEC (SOLL) mit MODEL (IST) und quantifiziert das Delta.
GAP-Score muss ueber Zyklen SCHRUMPFEN (Growing Conformance).
Circuit Breaker bei kritischem GAP% (>80%).

**Ergebnis:** `.claude/analysis/synthese/{NAME}-GAP.md` (Delta IST↔SOLL)

---

## Phase 2-7: Iterativer Zyklus

### Phase 2: Observe (Findings sammeln)

Delegiert an: `/_SC_observe [easy|normal|hard]`

**Liest** MODEL + ERGEBNIS (falls vorhanden) + GAP, **schreibt** OBSERVE{N}.
Sammelt Findings OHNE Interpretation.

### Phase 2b: Model-Maintain (Model aktualisieren)

Delegiert an: `/_SC_modelMaintain`

**Liest** OBSERVE{N} + MODEL, **aktualisiert** MODEL (W{n}, SRS-Score).

### Phase 2c: Quality Gate (Qualitaet pruefen)

Delegiert an: `/_SC_qualityGate [easy|normal|hard]`

**Liest** MODEL + OBSERVE{N} + ERGEBNIS* (falls vorhanden, SRS-Trend), **schreibt** QUALITYGATE{N}.
Prueft Battle-Royale, Kohaesion, Feature-Abschluss, BSD-Trigger, Stagnation.

### Phase 3: Hypothese

Delegiert an: `/_SC_hypothese [easy|normal|hard]`

**Liest** MODEL + OBSERVE{N} + QUALITYGATE{N}, **schreibt** HYPOTHESEN.

### Phase 4: Implementation

Delegiert an: `/_SC_implement`

**Liest** HYPOTHESEN + MODEL, **schreibt** Code + HYPOTHESEN-Update.

### Phase 5: Compose (Container)

```bash
# PowerShell im Sources-Verzeichnis:
./docker-up.ps1 -Profile dev-backend -NoCache -SkipTests
```

Warte bis alle Container "healthy" sind:
```bash
docker ps --format "table {{.Names}}\t{{.Status}}"
```

### Phase 6: Test

Manuelle Tests durchfuehren, Ergebnis dokumentieren.

### Phase 7: Ergebnis (optional)

Delegiert an: `/_SC_ergebnis [easy|normal|hard]`

**Liest** HYPOTHESEN + Logs, **schreibt** strukturierte Rohdaten (ERGEBNIS.md).
KEIN Model-Update — das macht /_SC_observe + /_SC_modelMaintain im naechsten Zyklus.
**Optional:** Skip wenn Ergebnisse offensichtlich (Build OK/FAIL).

---

## Fortsetzung nach /compact

1. Lies `.claude/analysis/_manifest.md`
2. Ermittle aktuellen Stand:

```
Manifest sagt:                    │ Aktion:
──────────────────────────────────┼──────────────────────────
_taskDefinition done              │ /_spec {NAME}
_spec done                        │ /_model {NAME} hard
_model Welle 1 done, 2 pending   │ /_model {NAME} (setzt bei Welle 2 fort)
_model done                       │ /_gap {NAME}
_gap done                         │ /_SC_observe
_SC_observe Welle 1 done          │ /_SC_observe (setzt bei Welle 2 fort)
_SC_observe done                  │ /_SC_modelMaintain
_SC_modelMaintain done            │ /_SC_qualityGate
_SC_qualityGate done              │ /_SC_hypothese
_SC_hypothese done                │ /_SC_implement
_SC_implement done                │ User testet, dann /_SC_ergebnis (oder skip)
_SC_ergebnis done                 │ /_SC_observe (neuer Zyklus)
_SC_qualityGate: GELOEST          │ FERTIG oder /_presentation
_SC_qualityGate: NEUER ZYKLUS     │ /_SC_hypothese (neuer Zyklus)
```

---

## Interaktiver Modus

Fuehre die Phasen SCHRITTWEISE aus:

1. **Phase 0**: `/_taskDefinition {NAME}` (Kruemmel sammeln, Task definieren)
2. **Phase 0b**: `/_spec {NAME}` (SOLL-Zustand definieren)
3. **Phase 1**: `/_model {NAME} hard` (einmalig, liest Kruemmel, IST-Zustand)
4. **Phase 1b**: `/_gap {NAME}` (Delta IST↔SOLL quantifizieren)
5. **Frage den User**: "Bereit fuer Phase 2 (Observe)?"
6. **Nach jeder Phase**: Zeige Zusammenfassung und frage nach naechster Phase
7. **Bei Compose**: Warte auf User-Bestaetigung dass Container laufen
8. **Bei Test**: Warte auf User-Feedback zum Testergebnis
9. **Bei Ergebnis**: Rohdaten sammeln, dann /_SC_observe (Findings + Model-Update via /_SC_modelMaintain + Entscheidung via /_SC_qualityGate)

---

## Dokument-Flow

```
{NAME}_Spec.md   (persistent, SOLL-Definition)
     │
     ├──▶ {NAME}-GAP.md  (Delta IST↔SOLL, MUSS schrumpfen)
     │         ▲
     │         │
{NAME}_Model.md  (persistent, waechst, IST-Zustand)
     │         │
     ├──▶ {NAME}-OBSERVE{N}.md  (pro Zyklus, Findings)
     │         │
     │         ├──▶ MODEL-UPDATE (via /_SC_modelMaintain)
     │         │
     │         ├──▶ {NAME}-QUALITYGATE{N}.md  (pro Zyklus, Gates)
     │         │         │
     │         │         ├──▶ {NAME}-HYPOTHESEN.md  (pro Zyklus)
     │         │         │         │
     │         │         │         ├──▶ Code-Aenderungen
     │         │         │         │
     │         │         │         └──▶ {NAME}-ERGEBNIS{N}.md (optional, Rohdaten)
     │         │         │                   │
     │         │         ◄───────────────────┘
     │         │         (/_SC_observe sammelt Findings)
     │         │         │
     │         └─────────┘
     │           (W{n} zurueck ins MODEL via /_SC_modelMaintain)
     │
     ├──▶ {NAME}-GAP.md  (Re-Eval: GAP muss schrumpfen)
```

Alle Zwischen-Drafts der Wellen (exploration/*.md, drafts/*.md) bleiben erhalten
als Audit-Trail und Quellennachweis.

---

## Agent-Strategie Uebersicht

| Phase | Easy | Normal | Hard |
|-------|------|--------|------|
| /_taskDefinition | 1 Hauptagent | 2-3 Drafter + Hauptagent | 3-5 Drafter + Hauptagent |
| /_spec | 1 Hauptagent | Drafts + Synthese | Exploration + Drafts + Synthese |
| /_model (init) | 1 Hauptagent | Drafts + Synthese | Exploration + Drafts + Synthese |
| /_gap | 1 Hauptagent | Drafts + Synthese | Exploration + Drafts + Synthese |
| /_SC_observe | 1 Hauptagent | 2-3 Drafter + Hauptagent | 3-5 Drafter + Hauptagent |
| /_SC_modelMaintain | 1 Hauptagent | 1 Hauptagent | 1 Hauptagent |
| /_SC_qualityGate | 1 Hauptagent | 1 Hauptagent | 1 Hauptagent |
| /_SC_hypothese | 1 Hauptagent | 2-3 Drafter + Hauptagent | 3-5 Drafter + Hauptagent |
| /_SC_implement | 1 Hauptagent | 1 Hauptagent | 1 Hauptagent |
| /_SC_ergebnis | 1 Hauptagent | 2-3 Subagenten + Hauptagent | 5-10 Subagenten + Hauptagent |

> **Modell-Zuweisung:** Abhaengig von SYSTEM-MODEL im Manifest.
> Jeder Sub-Command hat seinen eigenen Command-Max (siehe jeweiliger VERTRAG).
> Effektives Modell = min(SYSTEM-MODEL, Command-Max).

---

## Abbruch-Bedingungen

- User sagt "stop" oder "abbrechen"
- 3 Iterationen ohne Fortschritt → /_model Review
- GAP-Score steigt statt sinkt → /_gap Re-Eval
- Circuit Breaker: GAP% > 80% → ABORT
- Kritischer Fehler bei Compose

---

## Erfolgs-Bedingung

1. Alle definierten Erfolgskriterien erfuellt
2. Loesung im Model als W{n} dokumentiert
3. GAP-Score nahe 0% (Delta IST↔SOLL geschlossen)
4. Optional: `/_presentation PR`

---

## Starte jetzt

1. Lies `.claude/analysis/_manifest.md`
2. Falls Manifest existiert → setze dort fort
3. Falls kein Manifest → beginne mit Phase 0 (`/_taskDefinition {NAME}`)

Falls Argumente angegeben: Nutze {NAME} als Model-Name und {FRAGE} als Frage.

ARGUMENTS: $ARGUMENTS
