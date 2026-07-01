# /_TDD_red — TDD Schritt 6a: Failing Test schreiben

```yaml
status: active
version: 1.1.0
created: 2026-03-07
updated: 2026-03-07
op: TDD-SubCommand
phase: Red
chain_position: 6a
type: building-block
```

## Aufruf

```
/_TDD_red {SLICE} {STUFE} {ITERATION}
```

Wird von `spawne_tdd_agent(slice, "_TDD_red", stufe, iteration)` in `/_I_orchestrate` gerufen.

---

## SCHRITT 0.0 (PFLICHT — BL-NEW-45 SKILL-LOAD-VERIFIKATION, 2026-05-12)

```
VOR allen anderen Schritten — verifiziere dass du via Skill(_TDD_red) geladen wurdest,
NICHT als Inline-Worker-Auftrag.

INDIKATOREN fuer korrekten Skill-Load (mindestens 1 muss zutreffen):
  - <command-name>_TDD_red</command-name>-Tag im Conversation-Turn
  - Erster Prompt-Block: "Skill(_TDD_red, args=...)"
  - args-Parameter SLICE/STUFE/ITERATION sind explizit uebergeben

INDIKATOREN fuer Mega-Agent-Pattern (BL-NEW-45 Verletzung):
  - Worker-Prompt beginnt mit "AUFTRAG:" oder "Worker fuer Step 10 _TDD_red..."
  - Test-Code-Anweisungen sind INLINE im Prompt (kompletter Test-Code-Block)
  - KEIN expliziter Skill(_TDD_red)-Call vor AUFTRAG-Block

WENN Mega-Agent-Pattern detected:
  1. STOPPE sofort — keine Code-Edits, kein Test-File-Write
  2. Schreibe Error in TDD-STATE.md:
     state: SKILL_LOAD_VIOLATION
     last_action: _TDD_red_SCHRITT_0.0
     error: "INV-WORKER-SKILL-LOAD verletzt (BL-NEW-45)."
     audit_event: BL_NEW_45_VIOLATION
  3. audit_jsonl_append({type: "BL_NEW_45_VIOLATION", skill: "_TDD_red", worker: "{worker_name}", timestamp: ISO})
  4. SendMessage an team-lead: "ABORT @{worker_name}: BL-NEW-45 verletzt. Re-spawn mit Skill(_TDD_red, args=\"{SLICE} {STUFE} {ITERATION}\") als ZEILE 1."
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

**Verboten:** Sidecar-Writes nach `{WORKTREE_PATH}/.claude/analysis/4_Blueprint/`
oder `.claude/analysis/blueprints/`. ALLE Sidecar-Reads/Writes via `{BLUEPRINT_BASE}`.

---

## Schritt 0.4: Stage-Kontext laden (BL-NEW-63, 2026-05-12) — PFLICHT

> Lies `stage_{STUFE}.md` BEVOR du den Failing-Test schreibst. Stage-Konventionen
> entscheiden: welcher Testpfad gilt, welche Fixtures verwendet werden, ob Mocks
> erlaubt sind, welche `using`-Imports der Test braucht.

```
stage_meta_path = "{WORKTREE_PATH}/.claude/meta/implementation/stage_{STUFE}.md"
stage_meta = parse_yaml_frontmatter(stage_meta_path)

# Felder die _TDD_red braucht:
testtyp        = stage_meta.testtyp         # unit | integration | e2e
infrastruktur  = stage_meta.infrastruktur   # none | testcontainers | docker-compose
mocks_erlaubt  = stage_meta.mocks_erlaubt   # ja | nein
testpfad       = stage_meta.testpfad        # Tests/Unit/ | Tests/Integration/ | Tests/E2E/
test_projekte  = stage_meta.test_projekte   # [VDEK.DCSP.Application.UnitTests, ...]

# Override-Detection (Schicht-3 BL-NEW-59):
override_path = "{BL_FOLDER}/meta-overrides/stage_{STUFE}.md"
IF EXISTS(override_path):
  stage_meta = merge(stage_meta, parse_yaml_frontmatter(override_path))

audit_jsonl_append({type: "STAGE_CONTEXT_LOADED", skill: "_TDD_red", stage: STUFE, testtyp: testtyp})
Logge: "[STAGE-KONTEXT] testtyp={testtyp} testpfad={testpfad} mocks={mocks_erlaubt}"
```

**Behavior-Hints fuer _TDD_red (Failing-Test):**

| Feld | Wert | Test-Schreib-Verhalten |
|---|---|---|
| `testtyp: unit` | | xUnit + Moq, isolierte Klasse, mocked Dependencies |
| `testtyp: integration` | | xUnit + IClassFixture<TestcontainersFixture>, echte DB |
| `mocks_erlaubt: nein` | | KEINE `Mock<T>` im Test — Real-Provider via Fixture |
| `infrastruktur: testcontainers` | | `IClassFixture` Pattern, Lazy Container-Init im Constructor |
| `testpfad` | | Test-File MUSS in diesen Pfad geschrieben werden |

Case-Anchor: `.claude/_parking-lot.md` BL-NEW-63.

---

## VERTRAG

```
LIEST:
  {WORKTREE_PATH}/.claude/TDD-STATE.md                (aktueller Zustand — Worktree-local)
  {BLUEPRINT_BASE}/{SLICE}/sub-{NR}.md                 (TDD-Aufgaben — Vault-First, BL-NEW-30/43)
    LEGACY-Fallback (NUR wenn Vault-Read ENOENT): {WORKTREE_PATH}/.claude/analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md
  {WORKTREE_PATH}/.claude/TDD_INSTRUCTIONS.md          (falls vorhanden: Fokus, Testbefehl)
    Constraint: mocks_erlaubt aus TDD_INSTRUCTIONS.md bestimmt Mock-Scope
      mocks_erlaubt="ja"       → alle_externen Mocks erlaubt
      mocks_erlaubt="begrenzt" → nur extern_only (keine internen Mocks)
      mocks_erlaubt="nein"     → keine Mocks (Real-System)
    Widerspruchs-Check: Falls Test Mocks verwendet UND mocks_erlaubt="nein":
      Logge WARNUNG: "[MOCK-WIDERSPRUCH] Test {test_name} nutzt Mocks, aber mocks_erlaubt=nein."
      → Test anpassen (Mocks entfernen) ODER HiL-Eskalation

SCHREIBT:
  Test-Datei(en) im Worktree                           (neuer / erweiterter Test)
  {WORKTREE_PATH}/.claude/TDD-STATE.md                 (state: RED, tests_written: [...])
```

---

## Die Drei Gesetze des TDD (Uncle Bob — unverletzlich)

```
GESETZ 1: Du darfst KEINEN Production-Code schreiben, ausser um einen
          fehlschlagenden Test zum Bestehen zu bringen.

GESETZ 2: Du darfst NICHT mehr von einem Test schreiben als noetig,
          damit er fehlschlaegt. Compile-Fehler zaehlen als Fehlschlag.

GESETZ 3: Du darfst NICHT mehr Production-Code schreiben als noetig,
          um den einen fehlschlagenden Test zum Bestehen zu bringen.
```

Diese Gesetze sind der Grund warum _TDD_red, _TDD_green und _TDD_refactorCode
separate Commands sind. Jedes Gesetz schuetzt einen anderen Schritt.

---

## Ziel

Schreibe genau einen neuen Test (oder eine neue Test-Methode), der:
1. Jetzt FAIL ist (ROT) — der Test testet etwas das noch nicht implementiert ist
2. Dich zwingt, genau den Code zu schreiben den du schon weisst dass du schreiben musst
3. Den naechsten Edge Case oder Normalfall aus dem Sub-Blueprint abdeckt

GESETZ 2 gilt: Schreibe nur so viel Test wie noetig, um den Fehlschlag zu erzeugen.
Kein aufwaendiges Arrange wenn ein einfaches Assert reicht, um rot zu werden.

---

## Ablauf

### Schritt 1: Kontext laden

```
1. Lies TDD-STATE.md:
   - current_ring: Welcher Ring ist aktiv?
   - rings[]: Was ist der Name/Ziel dieses Rings?
   - Welche Tests wurden in frueheren Ringen bereits geschrieben?
   Falls TDD-STATE.md KEINE rings[] hat:
     → Ring-Planung fehlt (Schritt 5b wurde uebersprungen)
     → Plane Ringe selbst aus Sub-Blueprint (Stufe 1-2: trivial)

2. Lies Sub-Blueprint ## Gold-Definition + ## TDD-Aufgaben:
   - Was ist GOLD fuer diesen Slice?
   - Welche konkreten Red-Green-Refactor Schritte sind definiert?

3. Falls TDD_INSTRUCTIONS.md vorhanden: lies Fokus + Testpfad

WICHTIG: Arbeite NUR am current_ring. Nicht vorgreifen.
1 Ring = 1 Test = 1 Assertion. Baby Steps.
```

### Schritt 1.6: Autorisierte Test-Korrektur — korrigierter Test ist das neue RED (BL-303)

> Bei autorisierter Verhaltens-Aenderung (test_correction_authorized=true, BL-303)
> ist der RED-Worker verantwortlich, den KORRIGIERTEN Test als neues RED zu schreiben.
> Der test_correction-Pfad ersetzt den Standard-RED-Schritt fuer diesen Ring.

```
IF caller_context.test_correction_authorized == true:
  # test_correction-Pfad (BL-303):
  #   1. Lies authorization_evidence: Was aendert sich am erwarteten Verhalten?
  #   2. Schreibe den KORRIGIERTEN Test als neuen Failing-Test (RED)
  #      — der alte Test testet jetzt das FALSCHE Verhalten, der neue testet das NEUE
  #   3. TDD-STATE.md: test_correction=true + authorization_evidence loggen
  #   4. Naechster Schritt: _TDD_green zieht Test+Impl mit (Escape-Hatch aktiv)
  Logge: "[BL-303 test_correction] Korrigierter Test ist das neue RED."
  audit_jsonl_append({
    type: "TEST_CORRECTION_RED",
    skill: "_TDD_red",
    authorization_evidence: caller_context.authorization_evidence
  })
```

**Normalfall (ohne test_correction_authorized):** Standard-RED-Vorgehen, keine Aenderung
an bestehenden Tests (GESETZ 2).

---

### Schritt 2: 4 Einstiegsfragen beantworten (PFLICHT vor dem Schreiben)

Bevor du den Test schreibst:

1. **Was ist der EINFACHSTE Test der mich zwingt, echten Code zu schreiben?**
2. **Welchen Edge Case deckt dieser Test ab?** (Gegenlaeufer-Prinzip: starte mit Edge Cases)
3. **Braucht dieser Test eigenen Production-Code?** (Logiklos-Test → SKIP, naechster)
4. **Verletzt dieser Test GESETZ 2?** (Schreibe ich mehr als noetig um Fehlschlag zu erzeugen?)
   Wenn ja: Test vereinfachen bis das Minimum erreicht ist.

### Schritt 3: Test schreiben

```
Konzentrische Ringe (aus TDD-STATE.md):
  Lies current_ring aus TDD-STATE.md.
  Der Ring definiert WAS getestet wird (code-agnostisch).
  DU entscheidest WIE (konkreter Test-Code).

  Falls KEINE Ringe in TDD-STATE → Gegenlaeufer-Prinzip:
    Von aussen nach innen (Edge Cases → Normalfall → Komplex)

  1 Ring = 1 Test = 1 Assertion.
```

**Regeln:**
- Test laeuft NICHT (RED ist der Beweis, dass der Test etwas Neues prueft)
- Minimaler Test: prueft genau EINE Sache
- Test-Name: beschreibt was getestet wird (`Given_When_Then` oder `Should_When` Konvention)
- KEINE Implementierungs-Logik im Test schreiben

### Schritt 4: TDD-STATE.md aktualisieren

```yaml
state: RED
last_action: _TDD_red
ring: {aktueller Ring}
tests_written:
  - test_name: {Test-Name}
    beschreibung: {kurze Beschreibung}
    datei: {Pfad zur Test-Datei}
    gesetz2_check: passed  # Beweise: Minimum-Test, nicht mehr als noetig
iteration: {ITERATION}
```

---

## Output (SendMessage an team-lead)

```
_TDD_red {SLICE} i{ITERATION}: Test '{TEST_NAME}' geschrieben.
Ring {N}: {Edge Case / Normalfall / Komplex}.
Naechster Schritt: _TDD_execute(RED).
```

---

## Regeln

- KEIN Production-Code in diesem Schritt
- KEIN git commit
- Test MUSS semantisch sinnvoll sein (testet echte Logik, nicht Trivialitaeten)
- Falls kein Test mehr noetig (alle Ringe abgedeckt) → in TDD-STATE.md notieren: `all_rings_covered: true`
- **VERBOTEN: `dotnet build`, `dotnet test`, `Bash(dotnet ...)`, `powershell dotnet`** — RED = NUR Tests SCHREIBEN. Compilieren + Ausfuehren macht _TDD_execute (8b).
