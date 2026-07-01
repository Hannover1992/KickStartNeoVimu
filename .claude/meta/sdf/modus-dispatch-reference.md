# SDF Modus-Dispatch-Reference — Phase 1.1 Modus-Entscheidung + SCHRITT 2.1 M1..M9-Mapping

Referenz fuer `/_SDF_orchestrate` Phase 1.1 (modusEntscheidung-Gate) + SCHRITT 2.1
(Team-Lead-Dispatcher). Der Conductor behaelt den Gate-Call (Pre-Check + Skill(C3) + Post-Check)
und die ausfuehrbare `SWITCH modus`; die Begruendungs-Narrative, Per-Batch-Beispiele und die
M1..M9-Mapping-Detail-Doku liegen hier. Ausgelagert aus BL-401 (SRP-Refactor).

---

## Phase 1.1 modusEntscheidung — Gate-Doktrin

C3 (`_SDF_berater_modusEntscheidung`) ist Opus-Tier (50+ Pfade) und liest BATCH_STATE.batch_items
+ Aggregat-K-Score.

**INV-MODUS-PRE-WRITE-1 (RCA DCSRE-486 Round 11):**
- Vor Skill(_SDF_berater_modusEntscheidung): Pre-Check auf existing batch_modes/modus
- Wenn Feld gesetzt ohne BERATER_OUTPUTS.modusEntscheidung_*: ABORT
- "lead_fallback" als Wert in DF_BATCH_STATE.mode ist VERBOTEN — schreibe Reason in BERATER_OUTPUTS
- Verhindert dass Lead oder ein Pre-SDF-Skill (IDF, K-Score) batch_modes als Decision schreibt ohne
  dass _SDF_berater_modusEntscheidung lief.

Live-Beweis: DCSRE-486 Round 11 hatte batch_modes in IDF-Output OHNE
BERATER_OUTPUTS.modusEntscheidung_round11 → mode: lead_fallback in DF_BATCH_STATE_round11.
INV-MODUS-1 still gebrochen.

**KRITISCH (F98, BL-162 AK-7): Phase 1.1 ist nicht skippbar.**

> **Anti-Pattern beobachtet im DCSRE-486-Lauf:** SDF-Worker uebersprang Phase 1.1 mit Begruendung
> "IDF hat M3 SC-TDD bereits empfohlen". **VERBOTEN.**
>
> **User-Direktive (verschaerft):** IDF darf KEINE Empfehlung machen — auch keinen Hint. K-Score
> darf KEINE Empfehlung machen. SDF Phase 1.1 (C3) ist ALLEINIGE Quelle fuer M1..M9 und aggregiert
> die Daten selbst.

**Phase-1.1-Regel (haerter):**
- SDF Phase 1.1 ruft IMMER `_SDF_berater_modusEntscheidung` (C3) auf — kein Bypass.
- C3 liest selbst: `k_score_aggregate` + `srs_aggregate` + `batch_items` + `batch_type` +
  `escalation_hint` + Gap + ggf. K-Score-Detail-Felder.
- C3 gibt `DF_BATCH_STATE.modus = M1..M9` + `modus_begruendung` aus.
- Auch wenn upstream ein Mode "klar wirkt": KEIN Skip. C3 dokumentiert seine Ableitung.

---

## INV-MODUS-4 (BL-165): Per-Batch Mode-Decision Pflicht bei heterogenen Sub-Batches

Wenn IDF-batchPlan in mehrere Sub-Batches geteilt hat (`DF_BATCH_STATE.batch_items_per_batch` mit
`|Batches|>1`), MUSS C3 PRO BATCH separat entscheiden — NICHT eine globale Mode-Wahl fuer alle.
Heterogene Komplexitaet (triviale Konstanten-Batches vs DTO-Hierarchie-Batches) braucht heterogene
Modi.

**Output bei Per-Batch:**
```yaml
DF_BATCH_STATE.batch_modes:        # PRIMAER (autoritativ)
  batch_1: M2
  batch_2: M3
  batch_3: M3
  batch_4: M2
  batch_5: M3
  batch_6: M2

DF_BATCH_STATE.modus_begruendung_per_batch:
  batch_1: "trivial Konstanten, k=8 — M2 Inline reicht"
  batch_2: "DTO-Hierarchie 600 LOC, frag=55 — M3 SC-TDD"
  ...

DF_BATCH_STATE.modus: M3            # Backward-Compat (dominant/Mehrheit)
DF_BATCH_STATE.modus_begruendung:    # Backward-Compat
  "Per-Batch-Modi (BL-165 INV-MODUS-4): {...} dominant=M3"
```

**Phase 2 executionDispatch (Konsumenten-Update):**
- Iteriere `batch_items_per_batch[]`
- Pro Sub-Batch: lies `batch_modes[batch_N]` (NICHT globalen `modus`)
- Dispatch entsprechend (M1..M9-spezifisches I/SC/TDD)

**Anti-Pattern (DCSRE-486 F104 Live-Beobachtung):** C3 hat M3 global fuer alle 12 Items entschieden
— Over-Engineering fuer triviale Items (Batch-1/4/6). Korrekt waere: M2 fuer triviale, M3 fuer
komplexe — heterogene `batch_modes`-Map.

---

## SCHRITT 1.0 architecturalBrief + SCHRITT 1.5 patternBrief (Einschub-Doku)

**SCHRITT 1.0 ArchitecturalBrief (BL-154 AK-2-1):** architektonischer Pattern-Lookup VOR C9b und
VOR modusEntscheidung (C3). architecturalBrief liegt WEITER AUSSEN als patternBrief (Architekten-
Primat). Setzt `architectural_brief_logged`/`architectural_brief_at`. NON-BLOCKING bei leerer
PatternLibrary (EMPTY_SEED → Graceful Skip, INV-ARCH-1). Verifikation: `architectural_brief_at` <
`pattern_brief_at`.

**SCHRITT 1.5 PatternBrief (BL-153 AK-B-1):** PatternLibrary auf aktuelle Batch-Items abfragen.
Setzt `pattern_brief_logged`/`pattern_brief_at`. NON-BLOCKING → Graceful Skip. Ergebnis in
`BERATER_OUTPUTS.patternBrief` fuer executionDispatch + Sub-Pipelines.

---

## SCHRITT 2.1 Zwei-Pfad-Status (B12, BL-222 Motor / BL-373 altmodisch)

Ob die Modus-SWITCH inline gefahren wird, haengt vom Vehikel-Gate im OUTER-LOOP-WRAPPER ab
(`motor_allowed`):

- **MOTOR-Pfad (`motor_allowed=true` — NACH Gate-D + `workflow!=false`):** die SWITCH wird NICHT
  inline gefahren. Der Implement-Dispatch laeuft DETERMINISTISCH im Workflow-Motor
  `.claude/workflows/dispatch_implement.js` (1 agent/Sub-Skill → Mega-Worker strukturell unmoeglich;
  modusEntscheidung+stageElevation+Phase-3.x+loopDecision IM Workflow). Die SWITCH ist dort REFERENZ
  fuer die Modus→Sub-Skill-Mapping-Wahrheit (der Workflow leitet seine Step-Skeletons daraus ab).
- **ALTMODISCHER Pfad (`motor_allowed=false` — Default vor Gate-D / `workflow=false`, BL-373):** die
  SWITCH wird vom Team-Lead LIVE gefahren — der OUTER-LOOP-WRAPPER ELSE-Zweig dispatcht GENAU EINEN
  Sub-Batch und ruft `EXEC SCHRITT 2.1`. Re-entrant via INV-MODUS-7 SKILL-HANDSCHUH (das dispatchte
  I/SC chained `_SDF_orchestrate_post`, der Stage-Loop + RE-BATCH-Re-Entry + TERMINATE besitzt).

**ARCHITEKTUR-FIX (CaseStudy BL-154):** Der frueher hier aufgerufene
`_SDF_berater_executionDispatch` ist DEPRECATED. Ein Subagent kann keinen Handschuh-Wechsel
durchfuehren — `Skill()` laedt frischen Kontext fuer den Team Lead, nicht fuer einen Worker.
Verstoss gegen INV-PM-2. Neuer Pfad: SDF-Team-Lead liest `DF_BATCH_STATE.modus` direkt und ruft
`Skill(...)` selbst auf. Kein Worker-Spawn, kein Berater dazwischen.

---

## M1..M9-Mapping-Referenz

| Modus | Bedeutung | Dispatch |
|-------|-----------|----------|
| M1 | Skelett-Modus (Bare-Minimum, --scope=skeleton, BL-174/BL-212) | `_I_orchestrate --worker-mode --scope=skeleton --tdd=false` |
| M2 | I FULL ohne SC, TDD off (LOW-Komplexitaet, Standard) | `_I_orchestrate --tdd=false` |
| M3 | I + TDD-Inline (BL-169 — kein separater TDD-Orchestrator) | `_I_orchestrate --tdd=true` |
| M4 | SC INLINE | `_SC_orchestrate -I` |
| M5 | SC FULL SYMBIOSE | `_SC_orchestrate` |
| M6 | SC FULL + TDD | `_SC_orchestrate` (tdd=true) |
| M7 | SC PURE ANALYSE | `_SC_orchestrate --mode=analyse` |
| M8 | PR-Review (T + smoothing + presentation, Exit-Code-gated) | `_T_orchestrate` → `_smoothing` → `_presentation` |
| M9 | WP-Research (HiL in C3 eingeholt; Bottleneck-Trigger BL-206) | `_WP_orchestrate --bl-source` |

**M3 Hinweis:** I-Orchestrate fuehrt TDD-Cycle (RED/GREEN/REFACTOR) inline pro Slice durch (BL-169).
KEIN Skill(_TDD_orchestrate) mehr — Pipeline-Skill ist DEPRECATED.

**M8 Hinweis (BL-210 M9 Fix):** Exit-Code-Pruefung zwischen den 3 Skill-Calls. Vorher: bei
Teil-FAIL (z.B. _T_orchestrate) liefen smoothing+presentation trotzdem. Jetzt: bei FAIL → ABORTED.

**M9 Hinweis (BL-206 AK-4):** wenn von BL-206 SCHRITT 2.5 geroutet, schreibe bottleneck_trigger=true
damit WP-Pipeline den idf_reentry_signal korrekt setzt (AK-6).

**INV-DISPATCH-INLINE-1:** Skill-Loads laufen IMMER beim Team Lead (SDF). Ein Berater darf NIE
`Skill(_X_orchestrate)` rufen — `Skill()` ist Handschuh-Wechsel-Vehikel und gehoert nur dem
Orchestrator-Layer.

**INV-DISPATCH-INLINE-2:** Jeder Skill-Aufruf MUSS `--vault={VAULT}` mitgeben. Sub-Orchestratoren
lesen `--vault` als WORKING_DIR-Override und propagieren weiter (siehe INV-VAULT-9 +
`.claude/scripts/resolve_bl_path.py`).

**Recovery:** Bei Crash + Re-Trigger erkennt resumeGuard `batch_status==STARTED`, skipped Phase 0+1,
Team-Lead-Dispatcher verarbeitet ab erstem nicht-DONE Item via `DF_BATCH_STATE.item_done[]`
(BL-134 AK-9). Bei `BERATER_OUTPUTS.executionDispatch.status == "FAIL_*"`: Logge Error, setze
`df_status = ABORTED`, EXIT.
