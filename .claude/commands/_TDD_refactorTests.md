# /_TDD_refactorTests — TDD Schritt 6g: Tests spezifischer machen

```yaml
status: active
version: 1.1.0
created: 2026-03-07
updated: 2026-03-07
op: TDD-SubCommand
phase: Refactor-Tests
chain_position: 6g
type: building-block
```

## Aufruf

```
/_TDD_refactorTests {SLICE} {STUFE} {ITERATION}
```

Wird von `spawne_tdd_agent(slice, "_TDD_refactorTests", stufe, iteration)` in `/_I_orchestrate` gerufen.

---

## SCHRITT 0.0 (PFLICHT — BL-NEW-45 SKILL-LOAD-VERIFIKATION, 2026-05-12)

```
VOR allen anderen Schritten — verifiziere dass du via Skill(_TDD_refactorTests) geladen wurdest,
NICHT als Inline-Worker-Auftrag.

INDIKATOREN fuer korrekten Skill-Load (mindestens 1 muss zutreffen):
  - <command-name>_TDD_refactorTests</command-name>-Tag im Conversation-Turn
  - Erster Prompt-Block: "Skill(_TDD_refactorTests, args=...)"
  - args-Parameter SLICE/STUFE/ITERATION sind explizit uebergeben

INDIKATOREN fuer Mega-Agent-Pattern (BL-NEW-45 Verletzung):
  - Worker-Prompt beginnt mit "AUFTRAG:" oder "Worker fuer Step 16 _TDD_refactorTests..."
  - Test-Refactor-Anweisungen sind INLINE im Prompt (kompletter Test-Code-Diff)
  - KEIN expliziter Skill(_TDD_refactorTests)-Call vor AUFTRAG-Block

WENN Mega-Agent-Pattern detected:
  1. STOPPE sofort — keine Test-Edits, kein File-Write
  2. Schreibe Error in TDD-STATE.md:
     state: SKILL_LOAD_VIOLATION
     last_action: _TDD_refactorTests_SCHRITT_0.0
     error: "INV-WORKER-SKILL-LOAD verletzt (BL-NEW-45)."
     audit_event: BL_NEW_45_VIOLATION
  3. audit_jsonl_append({type: "BL_NEW_45_VIOLATION", skill: "_TDD_refactorTests", worker: "{worker_name}", timestamp: ISO})
  4. SendMessage an team-lead: "ABORT @{worker_name}: BL-NEW-45 verletzt. Re-spawn mit Skill(_TDD_refactorTests, args=\"{SLICE} {STUFE} {ITERATION}\") als ZEILE 1."
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

> Lies `stage_{STUFE}.md` BEVOR du Tests spezifischer machst. Test-Refactor muss
> Stage-Konventionen respektieren (mocks_erlaubt, testtyp, fixture-Pattern).

```
stage_meta_path = "{WORKTREE_PATH}/.claude/meta/implementation/stage_{STUFE}.md"
stage_meta = parse_yaml_frontmatter(stage_meta_path)

testtyp        = stage_meta.testtyp         # unit | integration | e2e
mocks_erlaubt  = stage_meta.mocks_erlaubt   # ja | nein
testpfad       = stage_meta.testpfad
container_isolation = stage_meta.container_isolation ?? false

# Override-Detection (Schicht-3 BL-NEW-59):
override_path = "{BL_FOLDER}/meta-overrides/stage_{STUFE}.md"
IF EXISTS(override_path):
  stage_meta = merge(stage_meta, parse_yaml_frontmatter(override_path))

audit_jsonl_append({type: "STAGE_CONTEXT_LOADED", skill: "_TDD_refactorTests", stage: STUFE})
Logge: "[STAGE-KONTEXT] testtyp={testtyp} mocks={mocks_erlaubt} container_isolation={container_isolation}"
```

**Behavior-Hints fuer _TDD_refactorTests:**

| Feld | Wert | Test-Refactor-Scope |
|---|---|---|
| `mocks_erlaubt: nein` | | KEINE neuen `Mock<T>` in Test-Code-Refactor — nur Fixture-getriebene Real-Provider |
| `testtyp: integration` | | Test-Refactor darf nicht Setup-Logic der Fixture in Test-Method ziehen (Fixture-Convention erhalten) |
| `container_isolation: true` | | Tests sind in IClassFixture isoliert — Refactor darf Fixture-Scope nicht brechen |
| `testtyp: unit` | | Refactor darf Test-Hierarchien (Theory/InlineData) ausbauen — kein Real-Infra-Zugriff einbauen |

Case-Anchor: `.claude/_parking-lot.md` BL-NEW-63.

---

## Schritt 0.5: Pattern-Library-Konsultation (BL-NEW-46, 2026-05-12) — BLOCKING

> Tests werden SPEZIFISCHER — aber sie sollten **Pattern-konform** spezifischer werden.
> Konsultiere PatternLibrary + SemanticLibrary fuer analoge Test-Patterns (BE-TEST, Twin-Tests).

```
polier_kontext = lies KURZLEBIG_PROMPT → polier_kontext ?? null

IF polier_kontext == null:
  # Self-Discovery analog _TDD_refactorCode SCHRITT 0.5
  sub_blueprint = lies "{BLUEPRINT_BASE}/{SLICE}/sub-{NR}.md"
  discovered_test_patterns = parse sub_blueprint → ## Test-Patterns (BE-TEST/PT-Refs)
  Skill(_I_patternLibrary, args="--sub-batch={SLICE} --stage={STUFE} --mode=test-refactor-discovery")
  arch_test_patterns = BERATER_OUTPUTS.patternLibrary.matched ?? []
  polier_kontext = {
    source: "self_discovery",
    matched_patterns: discovered_test_patterns + arch_test_patterns,
    auftrag: "BLOCKING: Test-Refactor MUSS analoge Test-Patterns (Twin-Tests, AAA-Strukturen) anwenden."
  }
  IF |polier_kontext.matched_patterns| == 0:
    audit_jsonl_append({type: "BL_NEW_46_VIOLATION", skill: "_TDD_refactorTests", reason: "no_test_patterns_available"})
    SendMessage an team-lead: "ABORT @{worker_name}: BL-NEW-46 — keine Test-Pattern-Discovery moeglich"
    EXIT FAIL.

Logge: "[refactorTests] Pattern-Konsultation: {|polier_kontext.matched_patterns|} Patterns aktiv"
```

---

## VERTRAG

```
LIEST:
  {WORKTREE_PATH}/.claude/TDD-STATE.md                (state: GREEN_VERIFIED nach _TDD_execute(6f) — Worktree-local)
  {BLUEPRINT_BASE}/{SLICE}/sub-{NR}.md                 (Exit-Kriterien — Vault-First, BL-NEW-30/43)
    LEGACY-Fallback (NUR wenn Vault-Read ENOENT): {WORKTREE_PATH}/.claude/analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md
  {WORKTREE_PATH}/.claude/TDD_INSTRUCTIONS.md          (falls vorhanden)
  Bestehende Test-Datei(en)                            (Tests die verfeinert werden)

SCHREIBT:
  Test-Datei(en) im Worktree                           (spezifischere Tests)
  {WORKTREE_PATH}/.claude/TDD-STATE.md                 (state: REFACTOR_TESTS_DONE)
```

---

## Schritt 0.5: Polier-Auftrag laden (AK-F-8, AK-B-4, BL-153 ARCH-13)

> **Einschub-Strategie (INV-EINSCHUB):** VOR Schritt 1 (Kontext laden).
> Empfängt `polier_kontext` aus KURZLEBIG_PROMPT falls vorhanden.
> NON-BLOCKING — fehlendes polier_kontext = normaler Test-Refactor ohne Pattern-Direktive.

```
polier_kontext = lies KURZLEBIG_PROMPT → polier_kontext ?? null

IF polier_kontext != null:
  Logge: "[refactorTests] Polier-Auftrag aktiv: {|polier_kontext.matched_patterns|} Patterns + {|polier_kontext.matched_semantics ?? []|} Semantics"
  # polier_kontext.auftrag enthält Pattern+Semantik-Direktive für Schritt 3
ELSE:
  Logge: "[refactorTests] Kein Polier-Auftrag (polier_kontext=null) — NON-BLOCKING"
```

## Schritt 0.6: Cross-Check Symmetrie (ARCH-33, BL-153)

> **Einschub-Strategie (INV-EINSCHUB):** NACH Schritt 0.5, VOR Schritt 1.
> Sicherstellt dass refactorTests + refactorCode BEIDE polier_kontext sehen
> wenn einer von beiden ihn hat. NON-BLOCKING — Warning ohne Pipeline-Stopp.

```
# Lies TDD-STATE.md: Hat refactorCode in diesem Ring polier_kontext_aktiv gesetzt?
tdd_state_refactor_code = lies TDD-STATE.md → refactoring_done.polier_kontext_aktiv ?? null

IF polier_kontext == null AND tdd_state_refactor_code == true:
  Logge: "[ARCH-33] WARNING: refactorCode hatte polier_kontext=true, refactorTests hat polier_kontext=null — KURZLEBIG_PROMPT-Asymmetrie. refactorTests sollte ebenfalls polier_kontext erhalten."
ELIF polier_kontext != null AND tdd_state_refactor_code == false:
  Logge: "[ARCH-33] WARNING: refactorTests hat polier_kontext, refactorCode hatte polier_kontext=false — KURZLEBIG_PROMPT-Asymmetrie. Prüfe Spawn-Konfiguration."
ELIF tdd_state_refactor_code == null:
  Logge: "[ARCH-33] refactorCode-State nicht lesbar (null) — Cross-Check uebersprungen (NON-BLOCKING)"
ELSE:
  Logge: "[ARCH-33] Cross-Check OK: refactorTests polier_kontext={polier_kontext != null}, refactorCode polier_kontext_aktiv={tdd_state_refactor_code}"
```

---

## Ziel

Mache die Tests **spezifischer** ohne den Production-Code zu aendern.

Uncle Bob Regel: "As the tests get more specific, the code gets more generic."

- Tests werden SPEZIFISCHER (mehr Assertions, mehr Boundary-Checks) → HIER
- Code wird GENERISCHER (echte Algorithmen) → wurde in _TDD_refactorCode getan

---

## Was ist Test-Refactoring?

```
ERLAUBT (Test-Verfeinerung):
  - Vage Assertions durch praezisere ersetzen
    VORHER: Assert.NotNull(result)
    NACHHER: Assert.Equal(expectedValue, result.Amount)
  - Test-Namen praezisieren (Should_When Konvention)
  - Hilfsmethoden extrahieren (Arrange-Abschnitt vereinfachen)
  - Magic Numbers in Test-Konstanten auslagern
  - Mehrfache Assertions in separate Tests aufteilen

NICHT ERLAUBT:
  - Neue Tests schreiben (das ist _TDD_red im naechsten Ring)
  - Tests schwaechen (Assertions entfernen)
  - Production-Code aendern
```

---

## Ablauf

### Schritt 1: Kontext laden

```
1. Lies TDD-STATE.md:
   - tests_written (welche Tests wurden in diesem Ring geschrieben)
   - state muss GREEN_VERIFIED sein (nach _TDD_refactorCode + _TDD_execute)
2. Pruefe: Sind die Tests noch aussagekraeftig?
   - Sind Assertions konkret genug?
   - Ist der Test-Name praezise?
   - Ist der Arrange-Teil klar und minimal?
3. Lies Sub-Blueprint ## Exit-Kriterien:
   - Welche Qualitaet werden Tests erwartet?
```

### Schritt 2: Test-Verfeinerungen identifizieren

```
Checkliste vor dem Test-Refactoring:
  [ ] Assertions: Pruefe ich den RICHTIGEN Wert oder nur "irgendetwas"?
  [ ] Test-Name: Beschreibt er GENAU was getestet wird?
  [ ] Arrange: Ist nur das Minimum aufgebaut das dieser Test braucht?
  [ ] AAA-Pattern: Ist Arrange/Act/Assert klar getrennt?
  [ ] Test-Isolation: Haengt der Test nicht von anderen Tests ab?

GOLD-TEST Kriterium (aus Sub-Blueprint):
  Bringt der Test den Code naeher an das finale Verhalten?
  Ein GOLD-Test prueft genau das was die Exit-Kriterien fordern.

Living Documentation Pruefung:
  Koennte ein neuer Entwickler diesen Test lesen und das System verstehen?
  Test = Spezifikation in Code-Form. Wenn der Test eine Erklaerung braucht
  um verstanden zu werden — schreibe ihn um bis er selbst-erklarend ist.
```

### Schritt 3: Tests verfeinern

```
Vorgehen:
  1. Einen Test-Schritt auf einmal verbessern
  2. Kein neuer Production-Code noetig (bereits gruen)
  3. Ziel: Test als lebendige Dokumentation

Typisches Muster (vage → praezise):
  VORHER (nach _TDD_red/_TDD_green):
    [Fact]
    public void Calculate_Works()
    {
      var result = _sut.Calculate(2, 3);
      Assert.True(result > 0);  // Zu vage!
    }

  NACHHER (nach _TDD_refactorTests):
    [Fact]
    public void Calculate_WithTwoPositiveIntegers_ReturnsTheirSum()
    {
      var result = _sut.Calculate(2, 3);
      Assert.Equal(5, result);  // Praezise!
    }
```

### Schritt 4: TDD-STATE.md aktualisieren

```yaml
state: REFACTOR_TESTS_DONE
last_action: _TDD_refactorTests
tests_refined:
  - test_name: {Original-Name oder neuer Name}
    aenderung: {was wurde verbessert}
    datei: {Pfad}
iteration: {ITERATION}
polier_kontext_aktiv: {polier_kontext != null}
semantics_count: {|polier_kontext.matched_semantics ?? []|}
```

---

## Output (SendMessage an team-lead)

```
_TDD_refactorTests {SLICE} i{ITERATION}: Tests verfeinert.
{N} Tests praezisiert: {kurze Beschreibung der Aenderung}.
Naechster Schritt: _TDD_execute(GREEN) zur Verifikation.
```

---

## Regeln

- Production-Code NICHT aendern (das ist _TDD_refactorCode)
- Tests nicht SCHWAECHEN (keine Assertions entfernen)
- KEIN git commit
- Kanarienvogel-Tests NICHT anfassen — beruehre nur Tests die in DIESEM Ring geschrieben wurden
- Falls Tests unveraendert optimal sind: Melde "keine Verfeinerung noetig" + REFACTOR_TESTS_DONE
- **VERBOTEN: `dotnet build`, `dotnet test`, `Bash(dotnet ...)`, `powershell dotnet`** — REFACTOR TESTS = NUR Tests UMSCHREIBEN. Compilieren + Ausfuehren macht _TDD_execute (8h).
