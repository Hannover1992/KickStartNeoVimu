---
name: _sanity_check_pre
description: /_sanity_check_pre — Pre-Execution Sanity-Check mit Schweizer-Uhrmacher-Granularitaet. Analysiert geplanten Skill/Phase-Aufruf BEVOR Ausfuehrung. Trace Data-Flow + Agent-Perspektive + Invariant-Compliance. Outputs PRE-REPORT + WATCH-LIST fuer Post-Check.
type: orchestrator
status: active
version: 1.0.0
created: 2026-05-11
feature_anchor: BL-NEW-13
op: AnalystSchweizerUhrmacher
model_tier: sonnet
contract:
  reads:
    - {file: "{VAULT}/Backlog/{bl_slug}/_manifest.md", purpose: "Pre-Execution State Snapshot"}
    - {file: "{WORKING_DIR}/.claude/commands/{skill}.md", purpose: "Vertrag des Skills der gleich laeuft"}
    - {file: "{WORKING_DIR}/_session_params.md", purpose: "Modus + GLOBAL_HIL + worker-mode"}
    - {file: "user_pasted_trace", purpose: "Lead-Output vor Skill-Call (optional)"}
  writes:
    - {file: "{WORKING_DIR}/output/Sanity_Pre_{phase}_{date}.md", purpose: "PRE-REPORT"}
    - {file: "{WORKING_DIR}/output/Sanity_Pre_{phase}_{date}.watch-list.md", purpose: "Watch-List fuer Post-Check"}
---

# /_sanity_check_pre — Pre-Execution Pipeline-Audit

## Zweck

Bevor ein Skill/Phase ausgefuehrt wird, prueft dieser Command:
- **Was wird gleich passieren?** (Skill-Vertrag, INVs, erwartete State-Transitions)
- **Sind alle Inputs verfuegbar?** (Vertrag.reads-Felder im Manifest da)
- **Ist die Logik vollstaendig?** (keine Dead-Refs, kein Schema-Mismatch, keine Rekursions-Traps)
- **Aus Agent-Perspektive konsistent?** (was wuerde Lead/Worker/Berater sehen?)
- **Welche Beobachtungen sind kritisch fuer Post-Check?**

**Schweizer-Uhrmacher-Prinzip:** Granular pro Variable, pro INV, pro Data-Flow-Edge.
Kein "alles sieht gut aus" — entweder bewiesen oder explizit flagged.

---

## Aufruf

```
/_sanity_check_pre {phase|skill} [--trace=user_paste_file] [--bl={BL_ID}] [--vault={VAULT}]

Beispiele:
  /_sanity_check_pre "Phase 1.5 patternBrief batch_2" --bl=DCSRE-486
  /_sanity_check_pre "_I_orchestrate dispatch M3" --bl=DCSRE-486
  /_sanity_check_pre "_SDF_orchestrate_post BL-NEW-12 first-test" --bl=DCSRE-486
```

User-Pasted Trace (optional): Wenn User die Lead-Session-Ausgabe von vor dem Skill-Call bereitstellt
(z.B. Phase 1.1 Output + manifest-snapshot), wird das mit eingelesen fuer Kontext.

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _sanity_check_pre                                          ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    - {WORKING_DIR}/_manifest.md (aktueller State)                   ║
║    - .claude/commands/{skill}.md (Vertrag der naechsten Skill)      ║
║    - .claude/commands/_SDF_orchestrate.md (Pre-Caller, fuer Pipeline-Kontext) ║
║    - _session_params.md (modus + worker-mode + GLOBAL_HIL)          ║
║    - User-pasted Lead-Trace (optional, Kontext)                     ║
║    - Vorherige BERATER_OUTPUTS (was upstream geliefert hat)         ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    - output/Sanity_Pre_{phase}_{date}.md (PRE-REPORT)               ║
║    - output/Sanity_Pre_{phase}_{date}.watch-list.md (fuer Post)     ║
║                                                                      ║
║  NICHT-AUFGABE:                                                      ║
║    - Skill ausfuehren (das ist Lead's Job)                          ║
║    - Manifest aendern (read-only)                                    ║
║    - Fixes anwenden (nur diagnostisch)                              ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    INV-PRE-1: Read-Only — Command darf KEINEN Pipeline-State aendern║
║    INV-PRE-2: Output zwingend in output/ Folder (Vault-Audit)       ║
║    INV-PRE-3: Watch-List MUSS Liste konkreter audit.jsonl-Events    ║
║                produzieren, die Post-Check verifizieren soll        ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## METHODOLOGIE (7-Schritt Schweizer-Uhrmacher)

### Schritt 1: Skill-Vertrag Parsing (Read-Inputs)

```
1.1 Lade Ziel-Skill (.claude/commands/{skill}.md)
1.2 Extrahiere Frontmatter.contract.reads + .writes + INVARIANTEN
1.3 Identifiziere Parameter-Erwartungen (args, frontmatter)
1.4 Notiere Side-Effects (Skill-Calls, Worker-Spawns, Agent()-Aufrufe)
```

### Schritt 2: Input-Verfuegbarkeits-Pruefung (Read-Side)

```
2.1 FOR jedes contract.reads-Feld:
    - Ist es in Manifest vorhanden?
    - Ist Schema/Typ korrekt?
    - Ist Wert nicht null/empty wo Vertrag das verbietet?
    
2.2 FOR jeden upstream Berater-Output:
    - Liegt es vor (z.B. BERATER_OUTPUTS.modusEntscheidung fuer Phase 1.5)?
    - Felder konsistent mit Erwartung des Ziel-Skills?

2.3 FOR jede Path-Referenz im Skill:
    - Existiert die Datei?
    - Ist die Path-Resolution korrekt (resolve_vault_root.py vs hardcoded)?

REPORT: Per Input-Feld → PASS/FAIL mit Begruendung
```

### Schritt 3: Data-Flow-Tracing (Upstream → Downstream)

```
3.1 Backward-Trace: Wer hat jede Eingabe-Variable geschrieben?
    - Wenn unklar: FAIL "Dead Read Reference"
    - Wenn upstream Skill nicht gelaufen ist: FAIL "Missing Upstream"

3.2 Forward-Trace: Wer wird jede Ausgabe-Variable konsumieren?
    - Welcher Downstream-Skill liest BERATER_OUTPUTS.{name}?
    - Wenn niemand: WARN "Orphan Output"

3.3 Cross-Skill-Reads (Vault-Files):
    - Manifest → Vault-Path-Konsistenz pruefen
    - INV-VAULT-9 (resolve_vault_root via Single-Source-Resolver)
```

### Schritt 4: Agent-Perspektive (3-Augen-Prinzip)

```
4.1 LEAD-Perspektive:
    - Was sieht der Lead vor dem Skill-Call?
    - Versteht Lead das Command-Argument richtig?
    - INV-PM-2: Skill-Load via Skill(...), nicht Agent(...)?

4.2 WORKER-Perspektive (falls Spawn vorgesehen):
    - Welcher Worker-Type wird gespawnt? (general-haiku|sonnet)
    - Tier passt zum Skill (model_tier in Frontmatter)?
    - Hat Worker Zugriff auf alle Reads (Pfade absolut)?

4.3 BERATER-Perspektive (falls Skill ein Berater ist):
    - Vertrag-Block respektiert (reads/writes/INV)?
    - BERATER_OUTPUTS-Struktur klar definiert?
    - INV-PM-5: Worker schreibt nur in BERATER_OUTPUTS, kein Top-Level-Manifest?
```

### Schritt 5: Invariant-Compliance-Check

```
5.1 Globale INVs:
    - INV-PM-1 (Worker-Pflicht): Lead darf NICHT inline ausfuehren wo Worker-Spawn vorgesehen
    - INV-PM-2 (Skill-Load): Sub-Orchestratoren via Skill(...), nicht Agent(...)
    - INV-PM-5 (Berater-Output-Isolation): nur in BERATER_OUTPUTS-Feld
    - INV-VAULT-9 (Path-Resolver): resolve_vault_root.py statt hardcoded paths

5.2 Skill-spezifische INVs:
    - Aus Frontmatter.INVARIANTEN extrahieren
    - Pro INV: ist die Vorbedingung erfuellt?

5.3 BL-NEW-12 (Split-Architektur):
    - Bei I-orchestrate/SC-orchestrate Ende: POST_HANDOVER step in den Skill-Text drin?
    - Bei Pre-SDF Phase 2.1: dispatch zu I/SC vorgesehen, kein Phase 3 inline?
```

### Schritt 6: Watchmaker-Deep-Check (Bug-Mining)

```
6.1 Schema-Drift-Detection:
    - Verwendete Manifest-Felder existieren im Schema?
    - Schema-Beispiel: completed_sub_batches (list), current_sub_batch_id (str)
    - Wenn Skill Feld X liest, das nirgends geschrieben → BUG

6.2 Dead-Reference-Detection (B2-style):
    - Skill verwendet PIPELINE_CALL_STACK[-2] aber Feld wird nirgends gepflegt → WARN

6.3 Recursion-Trap-Detection (B3-style):
    - Skill ruft Skill(_X_orchestrate) am Ende, das wiederum ruft DIESEN Skill auf → WARN
    - Hint: Doppel-Verarbeitung-Risiko

6.4 Lead-Self-Inline-Risk:
    - Skill enthaelt Manifest-Direct-Writes ohne Berater-Wrap?
    - Lead-Heuristik wuerde "kompakte Schreibung" als Inline-Update interpretieren?

6.5 Audit-Trail-Completeness:
    - Plant Skill audit_jsonl_append({...}) events?
    - Mindest-Set: SKILL_LOAD am Anfang + Output-Event am Ende
```

### Schritt 7: Predict-Outcome (was wird passieren)

```
7.1 Erwartete Manifest-Delta:
    - Welche Felder werden geschrieben? (aus contract.writes)
    - Welche Werte-Bereiche sind erwartet?

7.2 Erwartete Skill-Calls:
    - Sub-Skills die diese Skill aufruft (Skill(_X), Agent(...))
    - Pro Sub-Call: parent-context-propagation?

7.3 Erwartete audit.jsonl-Events:
    - SKILL_LOAD(_{skill_name})
    - PHASE_*_STEP({step_name}, status: DONE|SKIP|FAIL)
    - Special events (WAVE_FORK, POST_HANDOVER, BUILD_FAIL, etc.)

7.4 Erwartete Exit-Routes:
    - Normaler Exit: zurueck zum Caller (Pre-SDF outer-loop, BDF, etc.)
    - Fehler-Exits: GOTO Phase 4 loopDecision, ABORT, etc.
```

---

## OUTPUT-FORMAT

### PRE-REPORT (Sanity_Pre_{phase}_{date}.md)

```markdown
# Sanity-Check PRE — {phase}
**Datum:** {ISO}
**BL:** {BL_ID}
**Skill:** {file.md}
**Phase:** {phase_name}

## Kontext
- modus: {M1..M9}
- worker_mode: {true|false}
- current_sub_batch_id: {batch_X}
- completed_sub_batches: {[...]}

## Input-Validation
| Field | Source | Status | Detail |
|---|---|---|---|
| DF_BATCH_STATE.modus | upstream Phase 1.1 | PASS | M3 set |
| BERATER_OUTPUTS.architecturalBrief | Phase 1.0 | PASS | cached |
| ... | ... | ... | ... |

## Data-Flow-Tracing
- {var}: written by {skill}, read by {skill} — VERIFIED
- {var}: DEAD READ — no upstream writer found — FAIL

## Agent-Perspective
- LEAD: ... PASS
- WORKER (general-sonnet): tier correct, args complete — PASS
- BERATER (if applicable): contract clear — PASS

## Invariant-Checks
- INV-PM-1 PASS
- INV-HANDOVER-1 PRE-CHECK: Skill enthaelt POST_HANDOVER section — PASS
- INV-NEW-{N} ...

## Watchmaker-Deep-Findings
- [HIGH] {finding} — {skill_file}:{line}
- [MED] ...
- [LOW] ...

## Predicted-Outcome
- Manifest will write: {fields}
- audit.jsonl will have: {events}
- Sub-Skills called: {list}
- Exit-Route: {expected}

## Recommendation
- {actionable_step_1}
- {actionable_step_2}

## Gesamt-Verdict
{GREEN: safe to execute | YELLOW: WARN about X | RED: BLOCK — fix Y before run}
```

### WATCH-LIST (Sanity_Pre_{phase}_{date}.watch-list.md)

```markdown
# Watch-List fuer Post-Sanity-Check

## Erwartete audit.jsonl-Events (in dieser Reihenfolge)
1. SKILL_LOAD(_{skill_name}, {ISO})
2. PHASE_{N}_STEP({step}, status=DONE)
3. ...
4. {Exit-Event}

## Erwartete Manifest-Felder (mit Schema)
- BERATER_OUTPUTS.{skill}.{field}: {type} = {expected_range}
- DF_BATCH_STATE.{field}: {expected_after_value}

## Kritische Verifikations-Punkte
- [ ] Field X muss von value A nach B transitionieren
- [ ] Event SKILL_LOAD(_SDF_orchestrate_post) muss erscheinen (BL-NEW-12)
- [ ] Wave-Events FORK + JOIN muessen paaren

## Bei Failure: Patch-Hint
- Falls X fehlt: Patch in {skill}.md line Y
- Falls Y inkorrekt: BL-Item BL-NEW-{N+1}
```

---

## INVARIANTEN

- **INV-PRE-1:** Read-Only — keine Pipeline-State-Aenderungen
- **INV-PRE-2:** Output zwingend in `output/` Folder fuer Vault-Audit
- **INV-PRE-3:** Watch-List muss konkrete audit.jsonl-Events produzieren
- **INV-PRE-4:** Schweizer-Uhrmacher-Granularitaet — pro Variable, pro INV, pro Edge
- **INV-PRE-5:** Bei RED-Verdict: User soll Skill NICHT ausfuehren bis Fix

---

## Verwendung mit _sanity_check_post

```
1. User triggert Pre-Check: /_sanity_check_pre "Phase 1.5 patternBrief batch_2"
2. Pre erzeugt PRE-REPORT + WATCH-LIST
3. User fuehrt Phase 1.5 aus (Lead)
4. User triggert Post-Check: /_sanity_check_post "Phase 1.5 patternBrief batch_2" --pre-report={pfad}
5. Post liest WATCH-LIST, vergleicht mit actual execution
6. Post erzeugt POST-REPORT mit Compliance-Score
```

Die zwei Commands sind ein Paar — Pre praepariert Beobachtungs-Erwartungen, Post verifiziert.
