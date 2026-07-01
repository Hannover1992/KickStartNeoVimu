# /_TDD_check — TDD Schritt 6i: GOLD erreicht?

```yaml
status: active
version: 1.1.0
created: 2026-03-07
updated: 2026-03-07
op: TDD-SubCommand
phase: Check
chain_position: 6i
type: building-block
```

## Aufruf

```
/_TDD_check {SLICE} {STUFE} {ITERATION}
```

Wird von `spawne_tdd_agent(slice, "_TDD_check", stufe, iteration)` in `/_I_orchestrate` gerufen.

---

## SCHRITT 0.0 (PFLICHT — BL-NEW-45 SKILL-LOAD-VERIFIKATION, 2026-05-12)

```
VOR allen anderen Schritten — verifiziere dass du via Skill(_TDD_check) geladen wurdest,
NICHT als Inline-Worker-Auftrag.

INDIKATOREN fuer korrekten Skill-Load (mindestens 1 muss zutreffen):
  - <command-name>_TDD_check</command-name>-Tag im Conversation-Turn
  - Erster Prompt-Block: "Skill(_TDD_check, args=...)"
  - args-Parameter SLICE/STUFE/ITERATION sind explizit uebergeben

INDIKATOREN fuer Mega-Agent-Pattern (BL-NEW-45 Verletzung):
  - Worker-Prompt beginnt mit "AUFTRAG:" oder "Worker fuer Step 18 _TDD_check..."
  - Gold-Check-Anweisungen sind INLINE im Prompt
  - KEIN expliziter Skill(_TDD_check)-Call vor AUFTRAG-Block

WENN Mega-Agent-Pattern detected:
  1. STOPPE sofort — keine TDD-STATE-Edits
  2. Schreibe Error in TDD-STATE.md:
     state: SKILL_LOAD_VIOLATION
     last_action: _TDD_check_SCHRITT_0.0
     error: "INV-WORKER-SKILL-LOAD verletzt (BL-NEW-45)."
     audit_event: BL_NEW_45_VIOLATION
  3. audit_jsonl_append({type: "BL_NEW_45_VIOLATION", skill: "_TDD_check", worker: "{worker_name}", timestamp: ISO})
  4. SendMessage an team-lead: "ABORT @{worker_name}: BL-NEW-45 verletzt. Re-spawn mit Skill(_TDD_check, args=\"{SLICE} {STUFE} {ITERATION}\") als ZEILE 1."
  5. EXIT mit Status FAIL.

WENN korrekter Skill-Load: weiter zu SCHRITT 0 (PATH-RESOLUTION).
```

---

## SCHRITT 0 (PFLICHT — BL-NEW-30/43 PATH-RESOLUTION, 2026-05-11)

```bash
VAULT_ROOT = $(python "{WORKTREE_PATH}/.claude/scripts/resolve_vault_root.py")
BL_FOLDER  = $(python "{WORKTREE_PATH}/.claude/scripts/resolve_bl_path.py" "{FEATURE_ID}")
BLUEPRINT_BASE = "{BL_FOLDER}/4_Blueprint"
# Fail-Hard wenn leer/ENOENT — KEIN Fallback auf .claude/analysis/
```

**Verboten:** Sidecar-Writes nach `{WORKTREE_PATH}/.claude/analysis/4_Blueprint/`.
ALLE Sidecar-Reads/Writes via `{BLUEPRINT_BASE}`.

---

## Schritt 0.4: Stage-Kontext laden (BL-NEW-63, 2026-05-12) — PFLICHT

> Lies `stage_{STUFE}.md` BEVOR du GOLD-Check machst. Exit-Kriterien fuer GOLD-State
> sind stage-spezifisch (z.B. `kanarienvogel_tests: alle_gruen`, `blueprint_qg: pass`).

```
stage_meta_path = "{WORKTREE_PATH}/.claude/meta/implementation/stage_{STUFE}.md"
stage_meta = parse_yaml_frontmatter(stage_meta_path)

exit_criteria = stage_meta.exit_criteria       # [blueprint_qg, stufen_tests_gruen, ...]
testtyp       = stage_meta.testtyp
infrastruktur = stage_meta.infrastruktur

# Override-Detection (Schicht-3 BL-NEW-59):
override_path = "{BL_FOLDER}/meta-overrides/stage_{STUFE}.md"
IF EXISTS(override_path):
  stage_meta = merge(stage_meta, parse_yaml_frontmatter(override_path))

audit_jsonl_append({type: "STAGE_CONTEXT_LOADED", skill: "_TDD_check", stage: STUFE})
Logge: "[STAGE-KONTEXT] exit_criteria={exit_criteria} testtyp={testtyp}"
```

**Behavior-Hints fuer _TDD_check (GOLD-Validation):**

| Feld | Wert | GOLD-Check-Erweiterung |
|---|---|---|
| `exit_criteria` | Liste | Alle gelisteten Kriterien MUESSEN PASS sein — nicht nur rings GREEN |
| `exit_criteria.kanarienvogel_tests` | `alle_gruen` | Kanarienvogel-Tests pruefen — Kollateralschaden detected |
| `exit_criteria.blueprint_qg` | `pass` | Blueprint-Quality-Gate war pre-Stage gruen — verifizieren |
| `infrastruktur: testcontainers` | | Container-Teardown-Status pruefen (keine orphan Container) |

Case-Anchor: `.claude/_parking-lot.md` BL-NEW-63.

---

## VERTRAG

```
LIEST:
  {WORKTREE_PATH}/.claude/TDD-STATE.md                (aktueller Stand + alle Ringe — Worktree-local)
  {BLUEPRINT_BASE}/{SLICE}/sub-{NR}.md                 (Exit-Kriterien — Vault-First, BL-NEW-30/43)
    LEGACY-Fallback (NUR wenn Vault-Read ENOENT): {WORKTREE_PATH}/.claude/analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md
  {WORKTREE_PATH}/.claude/TDD_INSTRUCTIONS.md          (falls vorhanden: GOLD-Definition)

SCHREIBT:
  {WORKTREE_PATH}/.claude/TDD-STATE.md                 (gold_reached: true/false + next_ring)
```

---

## Ziel

Entscheide ob das GOLD-Kriterium erreicht ist — d.h. ob alle Exit-Kriterien aus dem Sub-Blueprint erfuellt sind.

Das ist der einzige Schritt der entscheidet ob die aeussere WHILE-Schleife in `/_I_orchestrate` beendet wird.

---

## GOLD-Kriterium

```
GOLD_REACHED = true wenn:
  1. Alle Exit-Kriterien aus sub-{NR}.md ## Gold-Definition sind erfuellt
  2. Alle Ringe aus TDD-STATE.md rings[] haben status: GREEN
  3. Die Tests beweisen das Verhalten (nicht nur "kein Compile-Fehler")

GOLD_REACHED = false (NOT_YET) wenn:
  - Noch Ringe mit status != GREEN (naechster Ring identifiziert)
  - Exit-Kriterien noch nicht alle erfuellt
  - Offene Edge Cases die noch getestet werden muessen
```

---

## Ablauf

### Schritt 1: Kontext laden

```
1. Lies TDD-STATE.md:
   - rings[]: Alle geplanten Ringe mit aktuellem status (GREEN/RED/UNKNOWN)
   - current_ring: Welcher Ring war zuletzt aktiv?
   - gold_definition: Was ist GOLD fuer diesen Slice?
   - Wie viele Iterationen wurden durchlaufen?
   - Gibt es all_rings_covered: true?

2. Lies sub-{NR}.md ## Gold-Definition:
   - Akzeptanzkriterien (WANN ist das Ziel erreicht)
   - Exit-Kriterien fuer diesen Slice

3. Abgleich: TDD-STATE rings[] gegen Gold-Definition
```

### Schritt 2: Ring-Abdeckung + Gold pruefen

```
Ring-Abdeckungs-Check (DYNAMISCH aus TDD-STATE.md):
  Lies rings[] aus TDD-STATE.md.
  Fuer JEDEN Ring:
    - Hat der Ring status: GREEN? → abgedeckt
    - Hat der Ring status: RED/UNKNOWN? → NICHT abgedeckt
  Ringanzahl ist aufgabenabhaengig (KEINE feste 3er-Struktur).
  Es koennen 5, 10, 20 oder mehr Ringe sein.
  ALLE muessen GREEN sein fuer GOLD_REACHED.

Gold-Abdeckungs-Check (gegen Sub-Blueprint ## Gold-Definition):
  Fuer JEDES Akzeptanzkriterium aus Gold-Definition:
    - Gibt es einen Test der DIESES Kriterium prueft?
    - Ist der Test gruen (_TDD_execute hat GREEN_CONFIRMED)?

Overshoot-Check (GESETZ 3 Retrospektiv):
  Gibt es Production-Code der kein Test verlangt?
  Methoden ohne Test-Abdeckung = spekulativer Code = Verletzung von Gesetz 3.
  Falls gefunden: NOT_YET melden + overshoot_detected: true in STATE.
  Der Team Lead muss entscheiden: Test schreiben ODER Code loeschen.
```

### Schritt 3: Entscheidung

**GOLD_REACHED = true:**

```yaml
state: GOLD_REACHED
last_action: _TDD_check
gold_reached: true
rings_total: {Anzahl Ringe aus TDD-STATE}
rings_green: {Anzahl GREEN Ringe}
gold_criteria_met: true  # Alle Akzeptanzkriterien aus Gold-Definition erfuellt
iteration: {ITERATION}
summary: "{Kurze Beschreibung was getestet und implementiert wurde}"
```

**GOLD_REACHED = false (NOT_YET):**

```yaml
state: NOT_YET
last_action: _TDD_check
gold_reached: false
rings_total: {Anzahl Ringe aus TDD-STATE}
rings_green: {Anzahl GREEN Ringe}
next_ring: {naechster Ring mit status != GREEN}
next_focus: "{Was muss als naechstes getestet werden}"
overshoot_detected: false  # true wenn Production-Code ohne Test-Deckung gefunden
iteration: {ITERATION}
```

---

## Output (SendMessage an team-lead)

```
# Bei GOLD_REACHED:
_TDD_check {SLICE} i{ITERATION}: GOLD_REACHED.
Alle {N} Exit-Kriterien erfuellt, alle Ringe abgedeckt.
Slice {SLICE} Stufe {STUFE}: DONE.

# Bei NOT_YET:
_TDD_check {SLICE} i{ITERATION}: NOT_YET.
{N}/{M} Exit-Kriterien erfuellt. Naechster Ring: {RING}.
Fokus: {was als naechstes getestet werden muss}.
Naechster Schritt: zurueck zu _TDD_red (6a), naechster Ring.
```

---

## Regeln

- Kein Code schreiben, kein Test schreiben — NUR pruefen
- KEIN git commit
- Im Zweifel: NOT_YET (lieber einen Ring mehr als einen vergessen)
- Kanarienvogel-Tests zaehlen NICHT fuer GOLD (sie waren vorher gruen)
- Bei `all_rings_covered: true` in TDD-STATE.md → kann direkt GOLD_REACHED melden ohne Re-Check
- Ring-Anzahl ist dynamisch (aus TDD-STATE.md rings[]) — NICHT auf 3 fixiert
