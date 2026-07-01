---
name: _sanity_check_post
description: /_sanity_check_post — Post-Execution Sanity-Check mit Schweizer-Uhrmacher-Granularitaet. Verifiziert AKTUELLE Ausfuehrung gegen erwarteten Vertrag/INVs. Manifest-Delta + audit.jsonl + Process-Compliance-Score. Pair mit _sanity_check_pre.
type: orchestrator
status: active
version: 1.0.0
created: 2026-05-11
feature_anchor: BL-NEW-13
op: AnalystSchweizerUhrmacher
model_tier: sonnet
contract:
  reads:
    - {file: "{VAULT}/Backlog/{bl_slug}/_manifest.md", purpose: "Post-Execution State"}
    - {file: "{WORKING_DIR}/.claude/commands/{skill}.md", purpose: "Vertrag des Skills der gelaufen ist"}
    - {file: "{VAULT}/Backlog/{bl_slug}/audit.jsonl", purpose: "Actual execution trail"}
    - {file: "output/Sanity_Pre_{phase}_{date}.watch-list.md", purpose: "Erwartungen vom Pre-Check"}
    - {file: "user_pasted_trace", purpose: "Lead-Output nach Skill-Call"}
  writes:
    - {file: "{WORKING_DIR}/output/Sanity_Post_{phase}_{date}.md", purpose: "POST-REPORT"}
    - {file: "{VAULT}/Backlog/{bl_slug}/6_PL/{bl_id}-parking-lot.md", purpose: "BL-Items bei Verstoss-Detection (append)"}
---

# /_sanity_check_post — Post-Execution Pipeline-Audit

## Zweck

Nachdem ein Skill/Phase ausgefuehrt wurde, verifiziert dieser Command:
- **Hat sich Pipeline wie erwartet verhalten?** (Vertrag-Compliance)
- **Sind alle Transitionen passiert?** (State-Delta korrekt)
- **Manifest-Variablen alle berechnet?** (kein null/missing wo erwartet)
- **Audit-Logs vollstaendig?** (jeder Step hat seinen Event)
- **Lead-Protokoll eingehalten?** (INV-PM, INV-HANDOVER, INV-AUDIT-CHAIN)
- **Datenfluss-Integritaet?** (was geschrieben wurde, kann gelesen werden)

**Process-Compliance-Score:** quantifizierte Bewertung (X/Y items DONE wie geplant).

---

## Aufruf

```
/_sanity_check_post {phase|skill} [--pre-report={pfad}] [--trace=user_paste_file] [--bl={BL_ID}] [--vault={VAULT}]

Beispiele:
  /_sanity_check_post "Phase 1.5 patternBrief batch_2" --bl=DCSRE-486 --pre-report=output/Sanity_Pre_phase15_20260511.md
  /_sanity_check_post "_I_orchestrate Round 2" --bl=DCSRE-486
  /_sanity_check_post "_SDF_orchestrate_post Round 2 first-test" --bl=DCSRE-486
```

User-Pasted Trace (optional): Komplette Lead-Session-Ausgabe nach Skill-Call.

---

## VERTRAG

```
╔══════════════════════════════════════════════════════════════════════╗
║  VERTRAG: _sanity_check_post                                         ║
╠══════════════════════════════════════════════════════════════════════╣
║  LIEST:                                                              ║
║    - {WORKING_DIR}/_manifest.md (Post-Execution State)              ║
║    - .claude/commands/{skill}.md (Vertrag des Skills)              ║
║    - audit.jsonl (actual events, Source-of-Truth)                   ║
║    - WATCH-LIST aus Pre-Check (Erwartungen)                         ║
║    - User-pasted Lead-Trace (Kontext)                               ║
║                                                                      ║
║  SCHREIBT:                                                           ║
║    - output/Sanity_Post_{phase}_{date}.md (POST-REPORT)             ║
║    - 6_PL/{bl_id}-parking-lot.md (Append bei Verstoss-Detection)    ║
║                                                                      ║
║  NICHT-AUFGABE:                                                      ║
║    - Auto-Fix anwenden (nur Empfehlungen)                           ║
║    - Manifest aendern (read-only ausser PL-Append)                  ║
║    - Process-Strict-Block (nur informativ markieren)                ║
║                                                                      ║
║  INVARIANTEN:                                                        ║
║    INV-POST-1: Read-only auf Manifest (kein State-Patch)            ║
║    INV-POST-2: PL-Append nur bei HIGH-Severity-Findings             ║
║    INV-POST-3: Process-Compliance-Score MUSS quantifiziert sein     ║
║                (X/Y mit X=PASS-Items, Y=Total-Expected)             ║
║    INV-POST-4: Bei FAIL-Verdict: Patch-Recommendation konkret       ║
║                (Skill-File + Line + neue Logik)                     ║
╚══════════════════════════════════════════════════════════════════════╝
```

---

## METHODOLOGIE (7-Schritt Verifikation)

### Schritt 1: Pre-Report-Loading (Erwartungen)

```
1.1 Wenn --pre-report uebergeben:
    - Lese WATCH-LIST (audit-events + manifest-deltas + verifikations-punkte)
    - Wenn nicht uebergeben: leite Erwartungen aus Skill-Vertrag selbst ab
1.2 Konsolidiere Erwartungs-Liste:
    - {expected_audit_events: [...]}
    - {expected_manifest_changes: {...}}
    - {critical_verification_points: [...]}
```

### Schritt 2: Output-Validation (Write-Side)

```
2.1 FOR jedes contract.writes-Feld:
    - Ist es im Manifest nach Ausfuehrung vorhanden?
    - Schema/Typ korrekt?
    - Wert plausibel (nicht null/empty wo Vertrag das verbietet)?
    
2.2 FOR jeden erwarteten Berater-Output:
    - BERATER_OUTPUTS.{skill}.{field} populiert?
    - Sub-Felder konsistent (last_update Timestamp, status etc.)?

2.3 FOR jeden NICHT-erwarteten Write:
    - Wurde Lead-Inline-Write detected (INV-PM-1 Verstoss)?
    - Berater hat in nicht-vertraglich-deklariertes Feld geschrieben?

REPORT: Per Output-Feld → PASS/FAIL mit Diff
```

### Schritt 3: Manifest-Delta-Analyse (Vor → Nach)

```
3.1 Vergleiche Manifest_BEFORE vs Manifest_AFTER:
    - Welche Felder haben sich geaendert?
    - Sind alle Aenderungen vertraglich vorgesehen?

3.2 Unauthorized-Changes-Detection:
    - Field-Change ausserhalb contract.writes? → INV-PM-1 violation
    - Beispiel: Lead schreibt `completed_sub_batches=[X]` direkt → das war batchEnde's Job

3.3 Missing-Changes-Detection:
    - Vertrag sagt Field X soll geschrieben werden, Manifest unveraendert? → SKIP detected
    - Wenn SKIP nicht im Vertrag erwaehnt → BUG
```

### Schritt 4: Audit-Trail-Verification (Source of Truth)

```
4.1 Parse audit.jsonl seit Pre-Snapshot:
    - SKILL_LOAD(_{skill_name}) — Skill wurde wirklich geladen?
    - PHASE_*_STEP Events — alle erwarteten Schritte ausgefuehrt?
    - Special Events (POST_HANDOVER, WAVE_FORK/JOIN, BUILD_FAIL, etc.)

4.2 Event-Ordering:
    - Reihenfolge logisch korrekt? (SKILL_LOAD vor PHASE_STEP vor SKILL_EXIT)
    - Keine fehlenden Zwischen-Events?

4.3 Skip-Detection:
    - Erwartet aber fehlt → SKIP detected
    - Lead-Heuristik-Bypass-Indikator (siehe Phase-3-Skip-Bug-Case-Study 2026-05-11)

4.4 BL-NEW-12-spezifische Checks:
    - Nach I/SC-Skill: SKILL_LOAD(_SDF_orchestrate_post) im audit.jsonl?
    - Bei Pre-SDF Phase 2 dispatch: kein direkter Phase 3 inline?
    - Wave-Events paaren? (FORK ohne JOIN = haengende Wave)
```

### Schritt 5: Invariant-Compliance-Verification

```
5.1 INV-PM-1 (Worker-Pflicht):
    - Hat Lead Code/State direkt geaendert wo Worker-Spawn vorgesehen war?
    - Detection: Manifest-Top-Level-Write zwischen Skill-Calls

5.2 INV-PM-2 (Skill-Load):
    - Wurden Sub-Orchestratoren via Skill(...) oder Agent(...) gerufen?
    - Detection: audit-Trail "skill" vs "agent" Event

5.3 INV-HANDOVER-1 (BL-NEW-12):
    - I/SC-Skill ende OHNE Skill(_SDF_orchestrate_post)?
    - Detection: SKILL_LOAD-Event fehlt nach NACHPHASE

5.4 INV-AUDIT-CHAIN:
    - Pro Round Sequenz vollstaendig?
    - SKILL_LOAD(_SDF) → SKILL_LOAD(_I/SC) → SKILL_LOAD(_SDF_post) → PHASE_3_STEP × N

5.5 Skill-spezifische INVs:
    - Aus Frontmatter.INVARIANTEN des ausgefuehrten Skills
    - Pro INV: Nachbedingung erfuellt?
```

### Schritt 6: Process-Compliance-Score (Quantifiziert)

```
6.1 Zaehle Expected-Items:
    - Anzahl audit-Events erwartet (aus Watch-List)
    - Anzahl Manifest-Felder erwartet (aus contract.writes)
    - Anzahl INVs zu pruefen

6.2 Zaehle Actual-PASS:
    - Wie viele Items haben PASS?

6.3 Score = (PASS / TOTAL) × 100%
    - 100%: Pipeline lief perfekt
    - 80-99%: WARN, kleine Abweichungen
    - 50-79%: Process-Drift, INV-Verstoss moeglich
    - <50%: Process-Bruch, sofort fixen
```

### Schritt 7: Recommendation + Findings → PL

```
7.1 Bei FAIL-Items:
    - Konkrete Patch-Empfehlung (Skill-Datei + Line)
    - Falls strukturell: BL-Item-Vorschlag

7.2 Bei HIGH-Severity:
    - Append zu 6_PL/{bl_id}-parking-lot.md:
      "- [ ] BL-NEW-{NEXT}: {kurze Beschreibung}
         Quelle: Sanity-Check-Post {phase} {date}
         Severity: HIGH
         Detail: ..."

7.3 Bei MED/LOW: nur in POST-REPORT logged, kein PL-Append
```

---

## OUTPUT-FORMAT

### POST-REPORT (Sanity_Post_{phase}_{date}.md)

```markdown
# Sanity-Check POST — {phase}
**Datum:** {ISO}
**BL:** {BL_ID}
**Skill:** {file.md}
**Pre-Report:** {pfad oder N/A}

## Process-Compliance-Score
**{X} / {Y} = {pct}%**
- PASS: {n} items
- WARN: {m} items
- FAIL: {k} items

## Output-Validation (Write-Side)
| Field | Vertrag | Actual | Status |
|---|---|---|---|
| BERATER_OUTPUTS.modusEntscheidung.gewaehlter_modus | M{1..9} | M3 | PASS |
| ... | ... | ... | ... |

## Manifest-Delta-Analyse
**Geaenderte Felder:**
- {field}: {before} → {after} — AUTHORIZED (vertraglich)
- {field}: {before} → {after} — **UNAUTHORIZED** (Lead-Self-Inline detected!)

**Erwartete-aber-Fehlt Felder:**
- {field}: SKIP detected — INV-? Verstoss

## Audit-Trail-Verification
**Expected events:** {n}
**Actual events:** {m}
**Missing:** {[event1, event2]}
**Extra:** {[event3]}

**Event-Ordering:** {OK | drift detected: ...}

## Invariant-Compliance
- INV-PM-1: {PASS | FAIL — Lead-Inline-Write detected at {line}}
- INV-HANDOVER-1: {PASS | FAIL — kein SKILL_LOAD(_SDF_orchestrate_post)}
- INV-AUDIT-CHAIN: {PASS | partial: ...}
- INV-{skill-spez}: ...

## Findings
- [HIGH] {finding} — {file}:{line} → {recommended_patch}
- [MED] {finding} — {file}:{line}
- [LOW] {note}

## Process-Deviations Detected
- {deviation_1}: Lead hat Phase X nicht aufgerufen
- {deviation_2}: Worker-Tier hat Sonnet statt Haiku verwendet

## Recommendations
- {actionable_patch_1}
- {actionable_patch_2}

## PL-Items aus diesem Check
- BL-NEW-{N+1}: {beschreibung}

## Gesamt-Verdict
{GREEN: 100% compliance | YELLOW: drift mit acceptable level | RED: process-bruch, fix vor naechstem Run}
```

---

## INVARIANTEN

- **INV-POST-1:** Read-Only — kein State-Patch durch Sanity-Check selbst
- **INV-POST-2:** PL-Append nur bei HIGH-Severity (Spam-Vermeidung)
- **INV-POST-3:** Process-Compliance-Score MUSS quantifiziert (X/Y, kein "looks good")
- **INV-POST-4:** Bei FAIL: Patch-Recommendation konkret (file + line + neue Logik)
- **INV-POST-5:** Schweizer-Uhrmacher — pro Audit-Event, pro Vertrag-Feld, pro INV

---

## Workflow-Pair mit _sanity_check_pre

```
[Pipeline gleich Phase X auszufuehren]
   ↓
1. /_sanity_check_pre "Phase X"
   - PRE-REPORT
   - WATCH-LIST mit Erwartungs-Liste
   ↓
2. [User fuehrt Phase X aus via Lead]
   ↓
3. /_sanity_check_post "Phase X" --pre-report={watch-list-pfad}
   - Vergleicht Erwartung mit Realitaet
   - POST-REPORT mit Score + Findings
   - Bei Verstoss: PL-Item geschrieben
```

**Erwartung:** Pre+Post als Paar liefert vollstaendige Live-Pipeline-Verifikation
ohne in die Pipeline selbst einzugreifen (Read-Only-Beobachter).

---

## Praezedenz-Faelle (echte Bugs die Sanity-Check-Post entdecken sollte)

### Case 1: Lead-Self-Inline Skip (Phase 3, 2026-05-11)
**Lead-Verhalten:** Nach codeAtomic done, Lead schreibt direkt Manifest:
```
completed_sub_batches=[batch_1], item_done=[AK-CTX-2], batch_done=1
```
ohne `Skill(_SDF_berater_statusTransition)` zu rufen.

**Post-Check soll detecten:**
- `BERATER_OUTPUTS.statusTransition` MISSING
- `audit.jsonl PHASE_3_STEP step=3.3` MISSING
- INV-PM-1 violation: Lead direct manifest-write
- INV-HANDOVER-1: SKILL_LOAD(_SDF_orchestrate_post) MISSING
- Verdict: RED — Phase 3 wurde KOMPLETT skipped
- PL-Item: BL-NEW-11 Phase-3-Mandatory-Enforcement

### Case 2: Wave 3 Promotion auf Non-Last-Round (Hypothetisch)
**Lead-Verhalten:** is_last_round-Check verwendet falsche Felder → True auf jeder Round.

**Post-Check soll detecten:**
- PT_promoteFromPL/SL_promoteFromPL bei batch_2 (sollte erst bei batch_6)
- INV-? violation: Vault-Promotion-on-Wrong-Round
- Verdict: YELLOW — Vault-Pollution-Risiko
