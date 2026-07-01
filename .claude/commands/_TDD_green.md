# /_TDD_green — TDD Schritt 6c: Minimaler Code fuer GREEN

```yaml
status: active
version: 1.1.0
created: 2026-03-07
updated: 2026-03-07
op: TDD-SubCommand
phase: Green
chain_position: 6c
type: building-block
```

## Aufruf

```
/_TDD_green {SLICE} {STUFE} {ITERATION}
```

Wird von `spawne_tdd_agent(slice, "_TDD_green", stufe, iteration)` in `/_I_orchestrate` gerufen.

---

## SCHRITT 0.0 (PFLICHT — BL-NEW-45 SKILL-LOAD-VERIFIKATION, 2026-05-12)

```
VOR allen anderen Schritten — verifiziere dass du via Skill(_TDD_green) geladen wurdest,
NICHT als Inline-Worker-Auftrag.

INDIKATOREN fuer korrekten Skill-Load (mindestens 1 muss zutreffen):
  - <command-name>_TDD_green</command-name>-Tag im Conversation-Turn
  - Erster Prompt-Block: "Skill(_TDD_green, args=...)"
  - args-Parameter SLICE/STUFE/ITERATION sind explizit uebergeben

INDIKATOREN fuer Mega-Agent-Pattern (BL-NEW-45 Verletzung):
  - Worker-Prompt beginnt mit "AUFTRAG:" oder "Worker fuer Step 12 _TDD_green..."
  - Code-Anweisungen sind INLINE im Prompt (kompletter Code-Block, Minimal-Impl-Anweisung)
  - KEIN expliziter Skill(_TDD_green)-Call vor AUFTRAG-Block

WENN Mega-Agent-Pattern detected:
  1. STOPPE sofort — keine Code-Edits, kein File-Write
  2. Schreibe Error in TDD-STATE.md:
     state: SKILL_LOAD_VIOLATION
     last_action: _TDD_green_SCHRITT_0.0
     error: "INV-WORKER-SKILL-LOAD verletzt (BL-NEW-45)."
     audit_event: BL_NEW_45_VIOLATION
  3. audit_jsonl_append({type: "BL_NEW_45_VIOLATION", skill: "_TDD_green", worker: "{worker_name}", timestamp: ISO})
  4. SendMessage an team-lead: "ABORT @{worker_name}: BL-NEW-45 verletzt. Re-spawn mit Skill(_TDD_green, args=\"{SLICE} {STUFE} {ITERATION}\") als ZEILE 1."
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

> Lies `stage_{STUFE}.md` BEVOR du Production-Code anfasst. Stage-Konventionen entscheiden:
> ob Mocking erlaubt ist, welche Infrastruktur erwartet wird, welcher Testpfad gilt.
> Ohne Stage-Kontext riskiert der Minimal-Impl Pattern-Drift (z.B. Mock-Logic in Stage 3
> wo Real-DB erwartet wird).

```
stage_meta_path = "{WORKTREE_PATH}/.claude/meta/implementation/stage_{STUFE}.md"

IF NOT EXISTS(stage_meta_path):
  Logge: "[STAGE-KONTEXT] WARN stage_{STUFE}.md nicht gefunden — fallback Default-Verhalten"
  stage_meta = { testtyp: "unknown", mocks_erlaubt: "ja", infrastruktur: "none" }
ELSE:
  stage_meta = parse_yaml_frontmatter(stage_meta_path)

# Felder die _TDD_green braucht:
testtyp                = stage_meta.testtyp        # unit | integration | e2e
infrastruktur          = stage_meta.infrastruktur  # none | testcontainers | docker | docker-compose
mocks_erlaubt          = stage_meta.mocks_erlaubt  # ja | nein
test_projekte          = stage_meta.test_projekte  # [VDEK.DCSP.Application.UnitTests, ...]

# Override-Detection (Schicht-3 wenn vorhanden — BL-NEW-59 Vorschlag):
override_path = "{BL_FOLDER}/meta-overrides/stage_{STUFE}.md"
IF EXISTS(override_path):
  stage_meta_override = parse_yaml_frontmatter(override_path)
  stage_meta = merge(stage_meta, stage_meta_override)   # Override gewinnt
  Logge: "[STAGE-KONTEXT] Override aktiv aus {override_path}"

# Audit
audit_jsonl_append({
  type: "STAGE_CONTEXT_LOADED",
  skill: "_TDD_green",
  stage: STUFE,
  testtyp: testtyp,
  mocks_erlaubt: mocks_erlaubt,
  infrastruktur: infrastruktur
})

Logge: "[STAGE-KONTEXT] testtyp={testtyp} mocks={mocks_erlaubt} infra={infrastruktur}"
```

**Behavior-Hints fuer _TDD_green (Minimal-Code):**

| stage_meta-Feld | Wert | Behavior in Minimal-Impl |
|---|---|---|
| `mocks_erlaubt` | `ja` | Mock-Implementations OK fuer Dependencies (Stage 1 Unit) |
| `mocks_erlaubt` | `nein` | KEINE Mock-Logic im Production-Code — Service muss gegen echte Provider/DB laufen koennen |
| `infrastruktur` | `testcontainers` | DI muss container-aware sein (echte DBContext, echte Provider) — KEINE In-Memory-Substitute |
| `infrastruktur` | `none` | Stage 1 Unit — In-Memory / Mock-Setup im Test-Layer OK |
| `testtyp` | `unit` | Minimal-Impl konzentriert auf isolierte Logik-Branches |
| `testtyp` | `integration` | Minimal-Impl muss DB-Side-Effects + DI-Wiring korrekt machen |

**Konflikt-Vermeidung:**
- Bei `mocks_erlaubt: nein` und Worker-Verlockung "ich mock kurz das hier" → ABORT mit
  `STAGE_CONVENTION_VIOLATION` audit. Lead muss eingreifen ODER Worker schreibt
  konventions-konformen Code (Real-DB-Path).
- Bei `infrastruktur: testcontainers` und Worker plant Container-Setup-Code → VERBOTEN
  (BL-NEW-52: Container-Lifecycle ist Fixture-managed, nicht Service-Code).

**Live-Case-Anchor:** `.claude/_parking-lot.md` BL-NEW-63.

---

## Schritt 0.5: Pattern-Library-Konsultation (BL-NEW-46, 2026-05-12) — BLOCKING

> Auch der Minimal-Code soll Pattern-konform sein. Nicht "irgendein Code, Hauptsache GREEN" —
> sondern "minimal, ABER analoge Patterns aus Library beachtet".
> Konsultiere PatternLibrary + SemanticLibrary fuer Naming, Structure, Idempotency.

```
polier_kontext = lies KURZLEBIG_PROMPT → polier_kontext ?? null

IF polier_kontext == null:
  # Self-Discovery analog _TDD_refactorCode SCHRITT 0.5
  sub_blueprint = lies "{BLUEPRINT_BASE}/{SLICE}/sub-{NR}.md"
  discovered_patterns = parse sub_blueprint → ## Pattern-Zuweisung (PT/SL-Refs)
  Skill(_I_patternLibrary, args="--sub-batch={SLICE} --stage={STUFE} --mode=green-discovery")
  arch_patterns = BERATER_OUTPUTS.patternLibrary.matched ?? []
  Skill(_I_architecturalLibrary, args="--sub-batch={SLICE} --layer=domain --mode=green-discovery")
  semantic_patterns = BERATER_OUTPUTS.architecturalLibrary.matched_semantics ?? []
  polier_kontext = {
    source: "self_discovery",
    matched_patterns: discovered_patterns + arch_patterns,
    matched_semantics: semantic_patterns,
    auftrag: "BLOCKING: Minimal-Impl MUSS analoge Patterns (Naming, Structure, Idempotency) beachten."
  }
  IF |polier_kontext.matched_patterns| == 0 AND |polier_kontext.matched_semantics| == 0:
    audit_jsonl_append({type: "BL_NEW_46_VIOLATION", skill: "_TDD_green", reason: "no_patterns_available_for_green"})
    SendMessage an team-lead: "ABORT @{worker_name}: BL-NEW-46 — keine Pattern-Discovery moeglich fuer Green-Step"
    EXIT FAIL.

Logge: "[green] Pattern-Konsultation: {|polier_kontext.matched_patterns|} Patterns + {|polier_kontext.matched_semantics|} Semantics aktiv"
```

---

## VERTRAG

```
LIEST:
  {WORKTREE_PATH}/.claude/TDD-STATE.md                (state: RED + tests_written — Worktree-local)
  {BLUEPRINT_BASE}/{SLICE}/sub-{NR}.md                 (Exit-Kriterien — Vault-First, BL-NEW-30/43)
    LEGACY-Fallback (NUR wenn Vault-Read ENOENT): {WORKTREE_PATH}/.claude/analysis/blueprints/{FEATURE}/{SLICE}/sub-{NR}.md
  {WORKTREE_PATH}/.claude/TDD_INSTRUCTIONS.md          (falls vorhanden)
  Bestehende Test-Datei(en)                            (welcher Test soll gruen werden)

SCHREIBT:
  Production-Code im Worktree                          (minimale Implementierung)
  {WORKTREE_PATH}/.claude/TDD-STATE.md                 (state: GREEN_ATTEMPT)
```

---

## Ziel

Schreibe den **minimalen** Production-Code um den letzten ROT-Test (aus _TDD_red) zum Laufen zu bringen.

**Uncle Bob Regel: "Don't go for the gold"**
Schreibe nur so viel Code wie noetig. Kein vorausschauendes Design, keine generische Loesung,
keine zusaetzlichen Features. Der Code darf sogar "haesslich" sein — das wird in _TDD_refactorCode gefixt.

---

## Ablauf

### Schritt 1: Fehlschlagenden Test identifizieren

```
1. Lies TDD-STATE.md → tests_written (letzter Eintrag)
2. Lies den Test-Code
3. Verstehe: Was GENAU fehlt damit dieser Test gruen wird?
```

### Schritt 1.5: Pattern-Kontext laden (ARCH-14, BL-153)

> **Einschub-Strategie (INV-EINSCHUB, ARCH-14):** Nach Test-Identifikation, VOR Implementierung.
> Empfängt `green_pattern_context` aus KURZLEBIG_PROMPT falls vorhanden.
> NON-BLOCKING — fehlendes green_pattern_context = normales GREEN ohne Pattern-Direktive.

```
green_pattern_context = lies KURZLEBIG_PROMPT → green_pattern_context ?? null

IF green_pattern_context != null:
  Logge: "[green] Pattern-Kontext aktiv: {|green_pattern_context.matched_patterns|} Patterns + {|green_pattern_context.matched_semantics ?? []|} Semantics"
  # green_pattern_context.hinweis enthält Pattern-Direktive fuer Schritt 2
ELSE:
  Logge: "[green] Kein Pattern-Kontext (green_pattern_context=null) — NON-BLOCKING"
```

---

### Schritt 1.6: Green-Schutz — autorisierte Test-Korrektur Escape-Hatch (BL-303)

> **Green-Schutz-Abschnitt:** Der gruene Agent darf KEINE bestehenden Test-Assertions
> veraendern — das ist der Kern-Invariant. Ausnahme (Escape-Hatch, BL-303):
> Bei autorisierter Verhaltens-Aenderung DARF der gruene Agent die Test-Assertion mitziehen.

```
IF caller_context.test_correction_authorized == true
   AND caller_context.authorization_evidence != null:

  # Escape-Hatch aktiv (BL-303 autorisiert)
  Logge: "[BL-303 Escape] test_correction_authorized=true — gruener Worker zieht Test+Caller+Verhalten mit."
  # Vorgehen:
  #   1. Korrigiere die Test-Assertion gemaess authorization_evidence
  #   2. Implementiere das neue Verhalten (minimale Impl, GESETZ 3 gilt weiterhin)
  #   3. TDD-STATE.md: test_correction_authorized=true + authorization_evidence loggen
  audit_jsonl_append({
    type: "TEST_CORRECTION_AUTHORIZED",
    skill: "_TDD_green",
    authorization_evidence: caller_context.authorization_evidence
  })

ELSE:
  # Green-Schutz protektiv (Normalfall, BL-303)
  IF gruener Worker versucht Test-Assertion zu aendern:
    state: GREEN_BLOCKED_TEST_CONFLICT
    audit_jsonl_append({type: "GREEN_BLOCKED_TEST_CONFLICT", skill: "_TDD_green"})
    SendMessage an team-lead: "ABORT: Green-Schutz greift. Test-Assertion-Aenderung ohne
      test_correction_authorized=true verboten (BL-303). Entweder Impl. korrigieren
      ODER autorisierte Korrektur via test_correction_authorized=true signalisieren."
    EXIT FAIL.
```

**INV-MODUS-1 Hinweis:** `test_correction_authorized` ist KEIN Modus-Feld — es liegt
im `caller_context`, NICHT in `DF_BATCH_STATE.modus`. INV-MODUS-1 wird nicht verletzt.

---

### Schritt 2: Minimale Implementierung schreiben

```
Fragenkatalog vor dem Schreiben:
  - Was ist das ABSOLUTE Minimum das diesen einen Test besteht?
  - Kann ich es mit einer Return-Anweisung loesen? (Fake it!)
  - Erst wenn Fake-Loesung nicht reicht: echte Logik schreiben
  - Falls green_pattern_context != null: Schreibe Code der registrierten Patterns entspricht (green_pattern_context.hinweis beachten)

Schrittfolge:
  1. Fake it (return hardcoded value) — falls Test das akzeptiert: FERTIG
  2. Triangulate (zweiter Test erzwingt echte Logik) — falls noetig
  3. Obvious implementation (wenn Loesung offensichtlich ist)
```

**Strikte Grenzen (GESETZ 3):**
- Nur Klassen/Methoden die DIESER Test direkt benoetigt
- Kein Code fuer zukuenftige Tests schreiben
- Keine spekulativen Abstraktionen (kein Interface wenn nicht zwingend)
- KEIN Code der ueber das hinausgeht was _TDD_execute(GREEN) benoetigt

**Regressions-Bewusstsein:**
Der neue Production-Code darf KEINE vorher gruenen Tests brechen.
Mental-Check vor dem Schreiben: "Koennte diese Aenderung bestehende Tests
beeinflussen?" Falls ja: Kleinere Schritte waehlen.

### Schritt 2.5: PATTERN-VERTRAG-Block befuellen (AK-B-3, BL-153)

> **Einschub-Strategie (INV-EINSCHUB, AK-B-3):** Nach Implementierung, VOR
> STATE-Update. BLOCKER: fehlender Block oder fehlendes Pflichtfeld = NICHT erlaubt.
> Explizit-leere Felder mit Begruendung sind erlaubt (AK-E-1 Kategorien a/b/c).

```
Befuelle PATTERN-VERTRAG-Block mit 5 Pflichtfeldern:
  1. anwendungsbereich:  "{wo gilt das Pattern — Layer/Command/Scope}"
  2. vermiedene_antipatterns: "{was NICHT getan werden soll — aus Code-Kontext}"
  3. grenzen: "{boundary rules — wann Pattern NICHT anwenden}"
  4. verwendete_vorlagen: "{Beispiele aus Vault-PatternLibrary oder 'keine' + Begruendung}"
  5. bezug_zum_twin: "{Lead-Reference falls applicable — Twin-Command oder 'kein Twin' + Begruendung}"

BLOCKER-Check:
  IF eines der 5 Felder fehlt komplett (nicht leer, sondern nicht vorhanden):
    → FEHLER: "PATTERN-VERTRAG-Block unvollstaendig: {fehlendes_feld} fehlt"
    → KEIN Weiter zu Schritt 3 bis Feld befuellt (auch mit explizit-leerer Begruendung)

# Kategorie-Validierung fuer "explizit leer" (AK-E-1, BL-153)
# Explizit-leere Felder sind ERLAUBT — aber NUR mit einer der 3 gueltigen Kategorien:
#   (a) "Library leer: {Begruendung}" — PatternLibrary noch nicht befuellt
#   (b) "kein relevantes Pattern: {Layer/Scope Begruendung}" — kein Pattern fuer diesen Kontext
#   (c) "Boilerplate: {Begruendung}" — Slice ist reines Infrastruktur/Boilerplate ohne Pattern-Bezug
# Freitext ohne Kategorie (a), (b) oder (c) ist NICHT gueltige Begruendung → BLOCKER
FUER jedes explizit-leeres Feld (Inhalt enthaelt "keine:" oder "kein " aber KEINE Kategorie):
  IF Feld-Inhalt NICHT enthaelt "Library leer" AND
     NICHT enthaelt "kein relevantes Pattern" AND
     NICHT enthaelt "Boilerplate":
    → FEHLER: "AK-E-1 Verletzung: Feld '{feld_name}' hat Freitext ohne gueltige Kategorie.
               Gueltig: 'Library leer: ...', 'kein relevantes Pattern: ...', 'Boilerplate: ...'
               Nicht gueltig: beliebiger Freitext ohne Kategorie-Prefix."

# Cross-Check verwendete_vorlagen vs. green_pattern_context (ARCH-17, BL-153)
# INV-EINSCHUB: NACH Kategorie-Validierung — Green_pattern_context-bewusstes Gate.
# Zweck: Wenn Patterns geladen wurden, muss verwendete_vorlagen Bezug nehmen — "Boilerplate" reicht nicht.
IF green_pattern_context != null AND |green_pattern_context.matched_patterns| > 0:
  vorlagen = pattern_vertrag.verwendete_vorlagen ?? ""
  pat_ids  = green_pattern_context.matched_patterns | ids als Liste
  referenz_ok = (
    IRGENDEINE ID aus pat_ids enthalten in vorlagen
    OR vorlagen enthaelt "kein relevantes Pattern:" mit Layer-Begruendung
    OR vorlagen enthaelt "Library leer:"
  )
  IF NOT referenz_ok:
    → FEHLER: "ARCH-17 Verletzung: verwendete_vorlagen muss mind. 1 ID aus matched_patterns referenzieren
               ODER 'kein relevantes Pattern: {Layer-Begruendung}'.
               matched_patterns: {pat_ids}
               'Boilerplate: ...' reicht NICHT wenn Patterns fuer diesen Layer existieren.
               (NON-BLOCKING gilt nur wenn patternBrief leer/null war — hier war er aktiv)"
```

### Schritt 3: TDD-STATE.md aktualisieren

```yaml
state: GREEN_ATTEMPT
last_action: _TDD_green
code_written:
  - datei: {Pfad}
    beschreibung: {was wurde implementiert}
iteration: {ITERATION}
green_pattern_context_aktiv: {green_pattern_context != null}
pattern_vertrag:
  anwendungsbereich: "{Freitext}"
  vermiedene_antipatterns: "{Freitext}"
  grenzen: "{Freitext}"
  verwendete_vorlagen: "{Freitext oder 'keine: {Begruendung}'}"
  bezug_zum_twin: "{Freitext oder 'kein Twin: {Begruendung}'}"
```

---

## Output (SendMessage an team-lead)

```
_TDD_green {SLICE} i{ITERATION}: Minimaler Code geschrieben.
Datei: {PFAD}, {N} Zeilen hinzugefuegt.
Naechster Schritt: _TDD_execute(GREEN) zur Verifikation.
```

---

## Regeln

- KEIN Refactoring in diesem Schritt (das ist _TDD_refactorCode)
- KEIN git commit
- Code darf redundant/haesslich sein — Korrektheit vor Eleganz
- Kanarienvogel-Tests NICHT anfassen

## VERBOTEN (Enforcement Guard)

```
VERBOTEN: dotnet build         ← Compilieren ist Aufgabe von _TDD_execute (8d)
VERBOTEN: dotnet test          ← Tests ausfuehren ist Aufgabe von _TDD_execute (8d)
VERBOTEN: Bash(dotnet ...)     ← Jeder dotnet-Aufruf ist VERBOTEN
VERBOTEN: powershell dotnet    ← Auch ueber PowerShell VERBOTEN

GREEN = NUR Code SCHREIBEN. Kein Compilieren. Kein Testen.
Der naechste Schritt (8d: _TDD_execute) compiliert UND testet.
Bei FAIL springt der Enforcement-Loop zurueck zu GREEN (8c).

Warum: Trennung von Kreativitaet (GREEN=sonnet) und Mechanik (EXECUTE=haiku).
GREEN-Worker soll DENKEN und SCHREIBEN, nicht debuggen.
```
