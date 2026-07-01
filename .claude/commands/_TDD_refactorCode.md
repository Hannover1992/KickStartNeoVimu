# /_TDD_refactorCode — TDD Schritt 6e: Code generischer machen

```yaml
status: active
version: 1.1.0
created: 2026-03-07
updated: 2026-03-07
op: TDD-SubCommand
phase: Refactor-Code
chain_position: 6e
type: building-block
```

## Aufruf

```
/_TDD_refactorCode {SLICE} {STUFE} {ITERATION}
```

Wird von `spawne_tdd_agent(slice, "_TDD_refactorCode", stufe, iteration)` in `/_I_orchestrate` gerufen.

---

## SCHRITT 0.0 (PFLICHT — BL-NEW-45 SKILL-LOAD-VERIFIKATION, 2026-05-12)

```
VOR allen anderen Schritten — verifiziere dass du via Skill(_TDD_refactorCode) geladen wurdest,
NICHT als Inline-Worker-Auftrag.

INDIKATOREN fuer korrekten Skill-Load (mindestens 1 muss zutreffen):
  - <command-name>_TDD_refactorCode</command-name>-Tag im Conversation-Turn
  - Erster Prompt-Block: "Skill(_TDD_refactorCode, args=...)"
  - args-Parameter SLICE/STUFE/ITERATION sind explizit uebergeben

INDIKATOREN fuer Mega-Agent-Pattern (BL-NEW-45 Verletzung):
  - Worker-Prompt beginnt mit "AUFTRAG:" oder "Worker fuer Step 14 _TDD_refactorCode..."
  - Refactor-Anweisungen sind INLINE im Prompt (Code-Diff-Blocks)
  - KEIN expliziter Skill(_TDD_refactorCode)-Call vor AUFTRAG-Block

WENN Mega-Agent-Pattern detected:
  1. STOPPE sofort — keine Code-Edits, kein File-Write
  2. Schreibe Error in TDD-STATE.md:
     ```
     state: SKILL_LOAD_VIOLATION
     last_action: _TDD_refactorCode_SCHRITT_0.0
     error: "INV-WORKER-SKILL-LOAD verletzt (BL-NEW-45). Worker wurde mit Inline-AUFTRAG-Prompt gespawnt statt via Skill(_TDD_refactorCode)."
     audit_event: BL_NEW_45_VIOLATION
     ```
  3. audit_jsonl_append({
       type: "BL_NEW_45_VIOLATION",
       skill: "_TDD_refactorCode",
       worker: "{worker_name}",
       reason: "inline_AUFTRAG_without_skill_load",
       timestamp: ISO
     })
  4. SendMessage an team-lead:
     "ABORT @{worker_name}: BL-NEW-45 verletzt. Re-spawn mit Skill(_TDD_refactorCode, args=\"{SLICE} {STUFE} {ITERATION}\") als ZEILE 1, AUFTRAG-Detail als KURZLEBIG_PROMPT-Anhang."
  5. EXIT mit Status FAIL — KEIN Refactor, KEIN Code-Edit.

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

## VERTRAG

```
LIEST:
  {WORKTREE_PATH}/.claude/TDD-STATE.md                (state: GREEN_VERIFIED + code_written — Worktree-local)
  {BLUEPRINT_BASE}/{SLICE}/sub-{NR}.md                 (Pattern-Zuweisung — Vault-First, BL-NEW-30/43)
    LEGACY-Fallback (NUR wenn Vault-Read ENOENT): {WORKTREE_PATH}/.claude/analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md
  {WORKTREE_PATH}/.claude/TDD_INSTRUCTIONS.md          (falls vorhanden)
  Bestehender Production-Code                          (was wurde in _TDD_green geschrieben)

SCHREIBT:
  Production-Code im Worktree                          (refaktorierter, generischerer Code)
  {WORKTREE_PATH}/.claude/TDD-STATE.md                 (state: REFACTOR_CODE_DONE)
```

---

## Schritt 0.4: Stage-Kontext laden (BL-NEW-63, 2026-05-12) — PFLICHT

> Lies `stage_{STUFE}.md` BEVOR du Production-Code refactor'st. Refactor-Scope haengt
> stark von Stage-Konventionen ab: in Unit-Stage darf Refactor Mock-freundliche Strukturen
> haben, in Integration-Stage muss Refactor DB-Layer-konform sein.

```
stage_meta_path = "{WORKTREE_PATH}/.claude/meta/implementation/stage_{STUFE}.md"
stage_meta = parse_yaml_frontmatter(stage_meta_path)

testtyp        = stage_meta.testtyp         # unit | integration | e2e
infrastruktur  = stage_meta.infrastruktur   # none | testcontainers | docker-compose
mocks_erlaubt  = stage_meta.mocks_erlaubt   # ja | nein
fanout         = stage_meta.fanout          # hoch | mittel | niedrig

# Override-Detection (Schicht-3 BL-NEW-59):
override_path = "{BL_FOLDER}/meta-overrides/stage_{STUFE}.md"
IF EXISTS(override_path):
  stage_meta = merge(stage_meta, parse_yaml_frontmatter(override_path))

audit_jsonl_append({type: "STAGE_CONTEXT_LOADED", skill: "_TDD_refactorCode", stage: STUFE})
Logge: "[STAGE-KONTEXT] testtyp={testtyp} infra={infrastruktur} mocks={mocks_erlaubt}"
```

**Behavior-Hints fuer _TDD_refactorCode:**

| Feld | Wert | Refactor-Scope |
|---|---|---|
| `testtyp: unit` | | Refactor darf Mock-freundlich sein (DI-Constructor-Erweiterungen OK fuer Test-Mocks) |
| `testtyp: integration` | | Refactor muss DB-Side-Effects + Provider-Pattern respektieren — KEINE In-Memory-Substitute |
| `mocks_erlaubt: nein` | | Refactor darf KEINE `if (isTestEnvironment)`-Logic einbauen — Production-Code = Test-Code-Pfad |
| `infrastruktur: testcontainers` | | Provider/Service-Refactor muss Container-Lifecycle-Lazy-Init kompatibel sein |
| `blueprint_perspektive: Laserpointer` | | atomarer Refactor — eine Klasse, eine Methode |
| `blueprint_perspektive: Scheinwerfer` | | Schicht-uebergreifender Refactor erlaubt — aber nur intentional, nicht "boy scout" |

Case-Anchor: `.claude/_parking-lot.md` BL-NEW-63.

---

## Schritt 0.5: Polier-Auftrag laden (AK-F-8, AK-B-4, BL-153) — BLOCKING (BL-NEW-46, 2026-05-12)

> **Einschub-Strategie (INV-EINSCHUB):** VOR Schritt 1 (Kontext laden).
> Empfängt `polier_kontext` aus KURZLEBIG_PROMPT falls vorhanden.
> **BLOCKING ab 2026-05-12 (BL-NEW-46):** Refactor OHNE PatternLibrary/SemanticLibrary-
> Konsultation ist VERBOTEN — Worker entscheidet *nicht* selbst, ob er Patterns
> verwendet, das sind die Bibliotheken fuer da. Self-Discovery-Fallback wenn
> KURZLEBIG_PROMPT keinen polier_kontext liefert.

```
polier_kontext = lies KURZLEBIG_PROMPT → polier_kontext ?? null

IF polier_kontext != null:
  # Pfad A: Lead hat polier_kontext via KURZLEBIG_PROMPT bereitgestellt
  Logge: "[refactorCode] Polier-Auftrag aktiv: {|polier_kontext.matched_patterns|} Patterns + {|polier_kontext.matched_semantics ?? []|} Semantics"
  # polier_kontext.auftrag enthält die Pattern-Direktive (strukturell + semantisch) für Schritt 2

ELSE:
  # Pfad B (NEU BL-NEW-46): SELF-DISCOVERY-FALLBACK — Worker konsultiert Bibliotheken SELBST
  Logge: "[refactorCode] BL-NEW-46 Self-Discovery: polier_kontext fehlt, konsultiere PatternLibrary + SemanticLibrary selbst"

  # B.1: Lies sub-{NR}.md fuer Pattern-Zuweisungen aus Blueprint-Phase
  sub_blueprint_path = "{BLUEPRINT_BASE}/{SLICE}/sub-{NR}.md"
  IF EXISTS(sub_blueprint_path):
    sub_blueprint = lies sub_blueprint_path
    discovered_patterns = parse sub_blueprint → ## Pattern-Zuweisung (PT/SL-Refs)
  ELSE:
    discovered_patterns = []

  # B.2: PatternLibrary-Konsultation (architektonisch)
  Skill(_I_patternLibrary, args="--sub-batch={SLICE} --stage={STUFE} --mode=refactor-discovery")
  arch_patterns = BERATER_OUTPUTS.patternLibrary.matched ?? []

  # B.3: SemanticLibrary-Konsultation (semantisch — analoge Naming/Idempotency/Konsistenz)
  Skill(_SL_conformance, args="--sub-batch={SLICE} --stage={STUFE} --mode=refactor-discovery") [if available]
  ODER: Skill(_I_architecturalLibrary, args="--sub-batch={SLICE} --layer=domain --mode=refactor-discovery")
  semantic_patterns = BERATER_OUTPUTS.architecturalLibrary.matched_semantics ?? []

  # B.3b: DomainLibrary + FactoringLibrary-Konsultation (BL-237 batch_C4 AK-7) — NON-BLOCKING
  # ─────────────────────────────────────────────────────────────────────────────────────
  # Die DomainLibrary (fachliche Achse) + FactoringLibrary (Refactoring-Achse) sind die zwei
  # neuen Achsen des 4-kind-Pattern-Systems. Sie sind GREENFIELD (F5: frisch via AK-7 bootstrappt,
  # usage_count=0). Konsultation ist ZUSAETZLICH (4-kind), NICHT die strukturelle Pflicht aus B.2/B.3.
  #
  # **NON-BLOCKING-KLAUSEL (AK-7-Constraint, HART):** Eine leere/greenfield DomainLibrary oder
  # FactoringLibrary darf diesen Refactor-Schritt NIEMALS abbrechen. 0 Domain-/Factoring-Matches
  # ist der ERWARTETE Cold-Start-Zustand (gerade gebootstrappt) — kein Fehler, kein EXIT, kein
  # Hard-Abort. Der B.5-Hard-Abort unten gilt AUSSCHLIESSLICH fuer Pattern+Semantic (B.2/B.3),
  # NICHT fuer Domain/Factoring. Greenfield bricht Refactor nie.
  domain_patterns    = lies {VAULT_ROOT}/Libraries/DomainLibrary/_generic/*.md +
                       {VAULT_ROOT}/Libraries/DomainLibrary/_project/{LAYER}/*.md   # leer falls greenfield → OK
  factoring_patterns = lies {VAULT_ROOT}/Libraries/FactoringLibrary/_generic/*.md +
                       {VAULT_ROOT}/Libraries/FactoringLibrary/_project/{LAYER}/*.md  # leer falls greenfield → OK
  IF |domain_patterns| == 0 AND |factoring_patterns| == 0:
    Logge: "[refactorCode] AK-7 Domain/Factoring greenfield (0 Matches) — NON-BLOCKING, fahre fort (kein Abbruch)"

  # B.4: Konsolidierung
  polier_kontext = {
    source: "self_discovery",
    matched_patterns: discovered_patterns + arch_patterns,
    matched_semantics: semantic_patterns,
    matched_domain: domain_patterns,        # BL-237 AK-7 (NON-BLOCKING, additiv)
    matched_factoring: factoring_patterns,  # BL-237 AK-7 (NON-BLOCKING, additiv)
    auftrag: "BLOCKING: Refactor MUSS oben aufgefuehrte Patterns + Semantics in Betracht ziehen. Falls ein Pattern nicht passt, dokumentiere Begruendung in Schritt 2. KEIN Refactor ohne Pattern-Beruecksichtigung. Domain-/Factoring-Matches sind ZUSAETZLICH + NON-BLOCKING (greenfield-leer = OK, kein Abbruch, AK-7)."
  }

  # B.5: Hard-Abort wenn Self-Discovery KEINE Patterns findet UND Sub-Blueprint keine Hint hat.
  # BL-237 AK-7: Der Abort prueft NUR matched_patterns + matched_semantics — NICHT
  # matched_domain/matched_factoring (die sind NON-BLOCKING, greenfield-leer ist erlaubt).
  IF |polier_kontext.matched_patterns| == 0 AND |polier_kontext.matched_semantics| == 0:
    Logge: "[refactorCode] BL-NEW-46 ABORT — Pattern-Self-Discovery liefert 0 Treffer + sub-{NR}.md ohne Pattern-Zuweisung"
    audit_jsonl_append({
      type: "BL_NEW_46_VIOLATION",
      skill: "_TDD_refactorCode",
      reason: "no_patterns_available_for_refactor",
      sub_blueprint: sub_blueprint_path,
      timestamp: ISO
    })
    Schreibe TDD-STATE.md:
      state: PATTERN_DISCOVERY_FAILED
      error: "BL-NEW-46: Weder Lead noch Self-Discovery konnten PatternLibrary/SemanticLibrary-Matches finden. Refactor ohne Pattern-Vergleich ist verboten."
    SendMessage an team-lead: "ABORT @{worker_name}: BL-NEW-46 — Pattern-Discovery leer. Lead muss polier_kontext liefern ODER sub-{NR}.md mit Pattern-Zuweisung versehen."
    EXIT FAIL.

  Logge: "[refactorCode] BL-NEW-46 Self-Discovery DONE: {|polier_kontext.matched_patterns|} Patterns + {|polier_kontext.matched_semantics|} Semantics"
```

**BL-NEW-46 — Lehre (Projekt-agnostisch, Case-Anchor in `.claude/_parking-lot.md`):**
- Bei fehlendem polier_kontext im KURZLEBIG_PROMPT besteht das Risiko dass Worker direkt zu Code-Edit greift ohne PatternLibrary-Lookup.
- Fix: Self-Discovery-Fallback macht PatternLibrary/SemanticLibrary-Konsultation MANDATORY auch wenn Lead-Prompt unvollstaendig ist.

## Schritt 0.6: Cross-Check Symmetrie (ARCH-33, BL-153)

> **Einschub-Strategie (INV-EINSCHUB):** NACH Schritt 0.5, VOR Schritt 1.
> Sicherstellt dass refactorCode + refactorTests BEIDE polier_kontext sehen
> wenn einer von beiden ihn hat. NON-BLOCKING — Warning ohne Pipeline-Stopp.

```
# Lies TDD-STATE.md: Hat refactorTests in diesem Ring polier_kontext_aktiv gesetzt?
tdd_state_refactor_tests = lies TDD-STATE.md → tests_refined.polier_kontext_aktiv ?? null

IF polier_kontext == null AND tdd_state_refactor_tests == true:
  Logge: "[ARCH-33] WARNING: refactorTests hatte polier_kontext=true, refactorCode hat polier_kontext=null — KURZLEBIG_PROMPT-Asymmetrie. Prüfe Spawn-Konfiguration."
ELIF polier_kontext != null AND tdd_state_refactor_tests == false:
  Logge: "[ARCH-33] WARNING: refactorCode hat polier_kontext, refactorTests hatte polier_kontext=false — KURZLEBIG_PROMPT-Asymmetrie. refactorTests sollte ebenfalls polier_kontext erhalten."
ELIF tdd_state_refactor_tests == null:
  Logge: "[ARCH-33] refactorTests-State nicht lesbar (null) — Cross-Check uebersprungen (NON-BLOCKING)"
ELSE:
  Logge: "[ARCH-33] Cross-Check OK: refactorCode polier_kontext={polier_kontext != null}, refactorTests polier_kontext_aktiv={tdd_state_refactor_tests}"
```

---

## Schritt 0.7: TWIN-DIFF-CHECK — Twin-Conformance-Enforcement (BL-NEW-55, 2026-05-12)

> **NACH Schritt 0.6, VOR Schritt 1.** Wenn ein **Twin** (existierender Schwester-Service / Schwester-Klasse / Schwester-Test) im polier_kontext referenziert ist, dann MUSS der Refactor diesen Twin **line-by-line spiegeln** — nicht nur "Pattern aus Library angewendet". Verhindert BL-NEW-55-Class Twin-Drift. Case-Anchor + Details: `.claude/_parking-lot.md` BL-NEW-55.

```
twin_file = polier_kontext.twin_file ?? null

# Self-Discovery-Fallback wenn twin_file nicht in KURZLEBIG_PROMPT gesetzt aber
# sub-{NR}.md oder PL-Item einen twin_ref enthaelt:
IF twin_file == null:
  sub_blueprint_path = "{BLUEPRINT_BASE}/{SLICE}/sub-{NR}.md"
  IF EXISTS(sub_blueprint_path):
    sub_blueprint = lies sub_blueprint_path
    twin_file = parse sub_blueprint → ## Twin-Ref ?? null
  IF twin_file == null:
    # Auch in der PL-Aggregation suchen
    pl_master = lies "{VAULT}/Backlog/{slug}/6_PL/{bl_id}-parking-lot.md"
    twin_refs = grep pl_master fuer "twin_ref:" oder "Twin (Soll):"
    IF |twin_refs| > 0 AND alle gleich: twin_file = twin_refs[0]

IF twin_file == null:
  Logge: "[TWIN-DIFF] Kein Twin im polier_kontext + sub-Blueprint + PL-Master → SKIP (regulaerer Refactor ohne Twin-Mirror)"
  → weiter zu Schritt 1

# Twin existiert — Mirror-Disziplin PFLICHT
twin_content  = lies twin_file
target_files  = identifiziere Refactor-Targets (aus TDD-STATE.md.affected_files oder Sub-Blueprint)
current_state = lies(target_files)

twin_signatures = extract_method_signatures(twin_content)
twin_deps       = extract_constructor_deps(twin_content)
twin_helpers    = extract_private_helpers(twin_content)

current_signatures = extract_method_signatures(current_state)
current_deps       = extract_constructor_deps(current_state)
current_helpers    = extract_private_helpers(current_state)

diff = {
  missing_methods:  twin_signatures - current_signatures,
  missing_deps:     twin_deps       - current_deps,
  missing_helpers:  twin_helpers    - current_helpers,
  extra_methods:    current_signatures - twin_signatures,   # informativ
}

Logge: "[TWIN-DIFF] twin_file={twin_file} missing_methods={|diff.missing_methods|} missing_deps={|diff.missing_deps|} missing_helpers={|diff.missing_helpers|}"

# Severity-Berechnung
critical_threshold = 0   # bei Twin-Existenz: KEIN missing erlaubt (Twin-Mirror = wortwoertlich)

IF |diff.missing_methods| > 0 OR |diff.missing_deps| > 0 OR |diff.missing_helpers| > 0:
  # TWIN-DRIFT detected — Worker darf NICHT silent refactorieren
  TDD-STATE.md update:
    state: TWIN_DRIFT_DETECTED
    last_action: _TDD_refactorCode_SCHRITT_0.7
    twin_file: {twin_file}
    twin_drift: {diff}
    audit_event: BL_NEW_55_TWIN_DRIFT_DETECTED

  audit_jsonl_append({
    type: "BL_NEW_55_TWIN_DRIFT_DETECTED",
    skill: "_TDD_refactorCode",
    worker: "{worker_name}",
    twin_file: twin_file,
    missing_methods: diff.missing_methods,
    missing_deps:    diff.missing_deps,
    missing_helpers: diff.missing_helpers,
    timestamp: ISO
  })

  SendMessage an team-lead:
    "ABORT @{worker_name}: BL-NEW-55 TWIN-DRIFT detected.
     Twin: {twin_file}
     Missing methods: {diff.missing_methods}
     Missing deps:    {diff.missing_deps}
     Missing helpers: {diff.missing_helpers}
     Lead-Decision:
       (A) Refactor-Scope erweitern: alle Twin-Methods/Deps/Helpers im aktuellen Refactor mitnehmen (kann Worker-Tokens sprengen — pruefen)
       (B) PL-Item splitten: separate Worker pro Twin-Method (Multi-Spawn, AK-Granular)
       (C) ACCEPT-WITH-DOCUMENTATION: bewusste Abweichung dokumentieren (Lead muss begruenden warum kein Mirror — selten OK)"
  EXIT mit Status TWIN_DRIFT_DETECTED — KEIN silent Refactor.

# Twin-Mirror confirmed
Logge: "[TWIN-DIFF] PASS — Twin {twin_file} vollstaendig gespiegelt (keine missing methods/deps/helpers). Refactor darf laufen mit Mirror-Disziplin."
TDD-STATE.md.twin_mirror_verified = true
# Weiter zu Schritt 1
```

**BL-NEW-55 — Lehre (Projekt-agnostisch, Case-Anchor in `.claude/_parking-lot.md`):**
- Worker kann PatternLibrary korrekt konsultieren (BL-NEW-46 ok) UND trotzdem den konkreten Twin nur partiell spiegeln — Library-Patterns sind generisch, Twin ist konkret.
- Symptom: funktional gruene Tests, architektonisch incomplete Code (fehlende Methoden, Deps, Helpers vs Twin).
- Folge wenn nicht abgefangen: spaeterer Twin-Vergleich enthuellt CRITICAL Drift (z.B. Data-Loss, Audit-Trail-Verlust) — Re-Cluster + Re-Implementation noetig.
- Fix: dieser SCHRITT 0.7 — Twin-Mirror-Disziplin als HARTE Bedingung (kein silent Refactor bei detected Twin-Drift).

**Verhaeltnis zu BL-NEW-46:**
- BL-NEW-46 (Schritt 0.5): zwingt PatternLibrary-Konsultation (STRUKTURELL — gibt Library-Patterns)
- BL-NEW-55 (Schritt 0.7): zwingt Twin-Mirror-Disziplin wenn konkreter Twin existiert (SEMANTISCH — line-by-line vs konkreter Service)

Beide sind notwendig — Library gibt generische Patterns, Twin gibt konkrete Soll-Implementierung.

---

## Ziel

Mache den Production-Code **generischer** ohne die Tests zu brechen.

Uncle Bob Regel: "As the tests get more specific, the code gets more generic."

**Boy Scout Rule:** Hinterlasse den Code sauberer als du ihn vorgefunden hast.
Wenn du etwas Schmutziges siehst das NICHT in diesem Ring entstanden ist
und du es in 2 Minuten beheben kannst — behebe es. Aber hitch it to a test.

**Overshoot-Verbot (GESETZ 3):** Der refaktorierte Code darf NICHT mehr tun
als die vorhandenen Tests verlangen. Wenn du generalisierst und kein Test
diese Generalisierung fordert — rueckgaengig machen.

- Tests werden SPEZIFISCHER (mehr Assertions, mehr Edge Cases) → wird in _TDD_refactorTests getan
- Code wird GENERISCHER (echte Algorithmen statt Fake-Implementierungen) → HIER

---

## Was ist Refactoring?

```
ERLAUBT (Code-Refactoring):
  - Fake-Implementierung durch echte Logik ersetzen
  - Duplizierung entfernen (DRY)
  - Methode extrahieren (Extract Method)
  - Klasse aufteilen (Extract Class)
  - Magic Numbers durch benannte Konstanten ersetzen
  - Bessere Variablen-/Methoden-Namen

NICHT ERLAUBT (Neue Features):
  - Neue Methoden fuer Tests die NOCH NICHT existieren
  - Spekulativer Code fuer zukuenftige Anforderungen
  - Interfaces/Abstraktionen die kein Test fordert
```

---

## Ablauf

### Schritt 1: Kontext laden

```
1. Lies TDD-STATE.md:
   - code_written (was in _TDD_green implementiert wurde)
   - state muss GREEN_VERIFIED sein (_TDD_execute hat bestaetigt)
2. Lies Sub-Blueprint ## Pattern-Zuweisung:
   - Welche Patterns sollen verwendet werden?
   - Gibt es konkrete Refactoring-Hinweise?
3. Lies den aktuellen Production-Code
```

### Schritt 2: Refactoring identifizieren

```
Checkliste vor dem Refactoring:
  [ ] Gibt es Fake-Implementierungen (hardcoded return values)?
  [ ] Gibt es Code-Duplikation (gleiche Logik mehrfach)?
  [ ] Sind Methoden zu lang? (>10 Zeilen → Kandidat fuer Extract Method)
  [ ] Macht jede Methode EINE Sache? (SRP auf Methoden-Ebene)
  [ ] Sind Variablen-Namen klar und aussagekraeftig?
  [ ] Passen die verwendeten Patterns zum Sub-Blueprint?
  [ ] Ueberschiesst der Code was die Tests verlangen? (Overshoot-Check)
  [ ] Falls polier_kontext != null: Passt Code zu Patterns UND Semantics? (polier_kontext.matched_patterns + polier_kontext.matched_semantics beachten)

WICHTIG: Nur refaktorieren was JETZT noetig ist.
Nicht: "Ich koennte spaeter X brauchen."
```

### Schritt 3: Refactoring durchfuehren

```
Vorgehen:
  1. Einen Refactoring-Schritt auf einmal
  2. Nach jedem Schritt: Tests laufen noch? (Mental-Check)
  3. Commit NICHT hier (nur wenn _TDD_execute GREEN_CONFIRMED)

Typisches Muster (Fake it → echte Logik):
  VORHER (_TDD_green):
    public int Calculate(int a, int b) => 42;  // Fake!

  NACHHER (_TDD_refactorCode):
    public int Calculate(int a, int b) => a + b;  // Echte Logik
```

### Schritt 4: TDD-STATE.md aktualisieren

```yaml
state: REFACTOR_CODE_DONE
last_action: _TDD_refactorCode
refactoring_done:
  - typ: {z.B. "Fake→Logik" | "Extract Method" | "DRY"}
    beschreibung: {was wurde geaendert}
    datei: {Pfad}
iteration: {ITERATION}
polier_kontext_aktiv: {polier_kontext != null}
patterns_count: {|polier_kontext.matched_patterns ?? []|}
semantics_count: {|polier_kontext.matched_semantics ?? []|}
pattern_konformanz_hinweise: "{Freitext oder 'kein polier_kontext'}"
```

---

## Output (SendMessage an team-lead)

```
_TDD_refactorCode {SLICE} i{ITERATION}: Code refaktoriert.
Typ: {Refactoring-Typ}, Datei: {PFAD}.
Naechster Schritt: _TDD_execute(GREEN) zur Verifikation.
```

---

## Regeln

- Tests NICHT aendern (das ist _TDD_refactorTests)
- KEIN neuer Production-Code fuer noch nicht existierende Tests
- KEIN git commit
- Kanarienvogel-Tests NICHT anfassen
- Kleine Schritte bevorzugen: lieber 2 kleine Refactorings als 1 grosses
- **VERBOTEN: `dotnet build`, `dotnet test`, `Bash(dotnet ...)`, `powershell dotnet`** — REFACTOR = NUR Code UMSCHREIBEN. Compilieren + Ausfuehren macht _TDD_execute (8f).
