---
type: building-block
status: active
version: 1.0.0
created: 2026-05-04
feature: SemantischePatternLibrary
chain_position: standalone (Manueller Pre-PR Quality-Gate)
related: _SL_init, _SL_conformance, _Pre_PR_orchestrate, _assay, _question, _parking-lot
---

# /_SL_pre_pr — Pre-PR Conformance-Check Branch vs. develop (Batch-parallel)

**Status:** v1.0.0 (initial)
**Actor:** SEMANTIC-PRE-PR-CHECKER (Batch-Wellen-Pattern: 1 Batch = 1 Sonnet-Drafter)
**Zweck:** Manuell ausgefuehrt vor PR-Erstellung. Diff gesamten Branch gegen `develop`, alle geaenderten Dateien plus zugehoerige Tests, Aufteilung in parallele Batches, jeder Batch prueft seine Files gegen die SemanticLibrary, anschliessend Synthese. Bei `hil=true` Read-Only-Modus mit Pro-Gruppe-Reflexion (`/_assay` + `/_question`). Resultate werden ADDITIV ins Parking-Lot angehaengt.

> **Abgrenzung zu `/_SL_conformance`:** `_SL_conformance` arbeitet auf **unstaged Changes** (Working-Tree), pro Layer 1 Drafter. `_SL_pre_pr` ist **Branch-Total** (HEAD vs develop), Batch-aufgeteilt (file-count, nicht layer-bound), und manuell HiL-faehig.

> **Frequenz:** PRO PR (vor PR-Erstellung). Aufruf per Hand durch User, nicht automatisch.

---

## Aufruf

```
/_SL_pre_pr [--vs BRANCH] [--scope PFAD] [--batch-size N] [--hil true|false] [--no-pl] [--ceiling MODEL]
```

| Parameter      | Pflicht | Default          | Beispiel                  |
|----------------|---------|------------------|---------------------------|
| `--vs`         | NEIN    | `develop`        | `--vs main`               |
| `--scope`      | NEIN    | `Sources/Backend/` | `--scope Sources/Frontend/` |
| `--batch-size` | NEIN    | `8` (Files/Batch) | `--batch-size 12`         |
| `--hil`        | NEIN    | `true`            | `--hil false` (autonom, kein User-Stop) |
| `--no-pl`      | NEIN    | false             | Keine Anhang an Parking-Lot |
| `--ceiling`    | NEIN    | `opus`            | Synthese-Modell           |

> **HiL-Default:** Memory `feedback_a_pipeline_order` + `feedback_dark_factory_stage_flow` => Standard `--hil false` (autonom).
> Mit `--hil true`: Read-Only-Reflexions-Modus, Findings werden gruppenweise praesentiert.

---

## VERTRAG

```
+======================================================================+
| VERTRAG: /_SL_pre_pr                                                |
+======================================================================+
| LIEST:                                                               |
|   {repo_root}/.claude/config/layers.yaml                            |
|   {VAULT_ROOT}/Libraries/SemanticLibrary/_global/domain-glossary.md              |
|   {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/*.md (alle 9 Layer)    |
|   git diff {vs}...HEAD --name-only                                  |
|   git diff {vs} -- {file}                  (pro Datei im Batch)     |
|                                                                      |
| LIEST (Test-Pull-In):                                                |
|   Pro Production-File: zugehoerige Test-Files automatisch ermitteln |
|   und mit-aufnehmen — auch wenn der Test nicht im Diff ist.        |
|                                                                      |
| SCHREIBT (Per Batch):                                                |
|   .claude/wissen/sl_pre_pr_batch_{NN}.md       (Batch-Reports)      |
|                                                                      |
| SCHREIBT (Synthese):                                                 |
|   .claude/wissen/sl_pre_pr_{FEATURE}_{DATUM}.md (Master-Report)     |
|                                                                      |
| SCHREIBT (HiL-Modus, --hil true):                                   |
|   .claude/presentation/sl_pre_pr_group_{NN}.md  (pro Finding-Gruppe)|
|   .claude/wissen/sl_pre_pr_decisions_{DATUM}.md (User-Entscheidungen)|
|                                                                      |
| SCHREIBT (Parking-Lot, default an):                                  |
|   {VAULT}/.../6_PL/{bl_id}-parking-lot.md                          |
|     -> ADDITIV: Sektion "## {DATUM} - Pre-PR Conformance"          |
|     -> Items aus den must-fix + backlog Findings                   |
|                                                                      |
| AKTOR: SEMANTIC-PRE-PR-CHECKER                                      |
| MODELL-TIER: Drafter sonnet, Synthese opus (ceiling)                |
|                                                                      |
| INVARIANTEN:                                                         |
|   INV-PREPR-1: SemanticLibrary muss befuellt sein (sonst HiL Fehler)|
|   INV-PREPR-2: Test-Pull-In ist PFLICHT (Production-File holt Tests) |
|   INV-PREPR-3: Batches sind file-balanced (nicht layer-bound)       |
|   INV-PREPR-4: Read-Only — KEIN Code wird geaendert in diesem Cmd  |
|   INV-PREPR-5: Drafter IMMER sonnet (Memory-Regel feedback_drafter) |
|   INV-PREPR-6: Bei hil=true wird PRO Finding-Gruppe ein /_assay     |
|                geschrieben + /_question gestellt — sequentiell       |
|   INV-PREPR-7: Parking-Lot-Anhang ist ADDITIV (kein Replace, kein   |
|                Delete bestehender Items)                             |
|   INV-PREPR-8: Niemals PR autonom erstellen (Memory PR VERBOTEN)    |
+======================================================================+
```

---

## Chain-Position

```
Branch-Arbeit fertig (commits da, alle Tests gruen)
     |
     v
[/_SL_pre_pr]    <- DIESES COMMAND (manueller User-Trigger)
     |
     +--> .claude/wissen/sl_pre_pr_batch_*.md    (Batch-Reports)
     +--> .claude/wissen/sl_pre_pr_{FEATURE}_{DATUM}.md (Master)
     |
     +--> hil=false:  Parking-Lot-Anhang ADDITIV (alle CONF-Items)
     |
     +--> hil=true:   Pro Finding-Gruppe:
     |                  1. /_assay <Gruppe>             (Tiefen-Reflexion)
     |                  2. /_question "Diese Gruppe umsetzen?"
     |                  3. JA -> CONF-Items in PL append
     |                     NEIN -> SKIP, Entscheidung loggen
     |                  -> sequentiell, eine Gruppe nach der anderen
     |
     v
[Must-fix Items abarbeiten] (falls YELLOW/RED)
     |
     v
[/_Pre_PR_orchestrate] (Pattern-Battle-Test, Build, Tests-Run)
     |
     v
[PR erstellen] (gh pr create — User-Freigabe Pflicht)
```

---

## Test-Pull-In Heuristik (INV-PREPR-2)

Pro Production-File werden zugehoerige Test-Files mit-aufgenommen, auch wenn sie im Diff fehlen — der Conformance-Check prueft dann ob die Tests konsistent zur Produktionsaenderung sind.

**Heuristik (in dieser Reihenfolge versuchen):**

| Production-Pfad | Test-Pfad-Suchmuster |
|-----------------|----------------------|
| `Sources/Backend/VDEK.DCSP.{X}/{Y}/{File}.cs` | `Sources/Backend/VDEK.DCSP.{X}.UnitTests/{Y}/{File}Tests.cs` |
| `Sources/Backend/VDEK.Common/{Y}/{File}.cs` | `Sources/Backend/VDEK.Common.UnitTests/{Y}/{File}Tests.cs` |
| `Controllers/{Name}Controller.cs` | `WebApi.UnitTests/Controllers/{Name}ControllerTests.cs` + `IntegrationTests/Controllers/{Name}ControllerTests/**/*.cs` |
| `Services/{Name}Service.cs` | `Application.UnitTests/Services/{Name}ServiceTests.cs` |
| `Mapping/{Name}Profile.cs` | `*.UnitTests/Mapping/{Name}*.cs` |
| `Domain/Extensions/{Name}.cs` | `Domain.UnitTests/Extensions/{Name}Tests.cs` |
| `Setup.Database/Structure/.../{Migration}.cs` | (keine direkten Tests — Integration via Container) |

**Verhalten:**
- Test-File existiert: in Batch aufnehmen, **Markierung "test-pulled"** (auch ohne Diff geprueft)
- Test-File fehlt: **WARN-Finding "missing-test"** im Conformance-Bericht
- Production-File ohne klares Mapping: kein Pull-In, nur Production-File pruefen

---

## Batch-Bildung

```
1. Diff-Set holen:
   git diff {vs}...HEAD --name-only > /tmp/sl_pre_pr_diff_{FEATURE}.txt

2. Auf {scope} (default Sources/Backend/) filtern.
   Frontend/Cypress/E2E raus (Memory feedback_backend_only_scope).
   csproj/json/yml raus (kein Code).

3. Test-Pull-In:
   Pro Production-File aus Diff-Set: Test-Pfade ermitteln (Heuristik oben),
   bestehende Test-Dateien dem File-Pool hinzufuegen ("test-pulled" Marker).

4. Layer-Tagging (informativ):
   Jede Datei einem Layer aus layers.yaml zuordnen — wird im Batch-Report
   gezeigt, beeinflusst aber NICHT das Batch-Splitting.

5. Batches bilden (file-balanced, NICHT layer-balanced):
   N = max(1, ceil(|file_pool| / batch_size))
   Files werden gleichmaessig auf N Batches verteilt
   ABER: Production-File + zugehoerige Tests landen IMMER im selben Batch
   (Kohaerenz fuer Prufung — sonst sieht ein Drafter den Test ohne den Code)

6. Tasks erstellen:
   1 Task pro Batch (parallel) + 1 Synthese-Task (blocked_by alle Batches)
```

---

## Phase 0: Voraussetzungen + Setup

```
1. Voraussetzungen:
   a. Branch != vs (sonst nichts zu pruefen)
   b. SemanticLibrary _global/domain-glossary.md existiert
      _project/{LAYER}/naming-conventions.md existiert fuer mind. 1 Layer
      → NICHT befuellt: STOPP "Run /_SL_init zuerst"
   c. Git-Status sauber (uncommitted Changes erlaubt — werden mit-geprueft)

2. HiL-Mode bestimmen:
   --hil true|false vom CLI ODER aus _session_params.md hil-Feld ODER Memory-Default off

3. Diff + Test-Pull-In + Batch-Bildung (siehe oben)

4. Team erstellen:
   TeamCreate name="sl-pre-pr-{FEATURE}"
   Tasks: 1 pro Batch + 1 Synthese (blocked_by alle Batches) [+ 1 HiL-Iterator falls hil=true]

5. Status-Display Pflicht (Memory feedback_status_display):
   "[/_SL_pre_pr] Branch: {feature/...} vs {vs}. {N} Files (production: {P}, tests: {T}).
    {B} Batches a ~{batch_size} Files. Modelle: drafter sonnet, ceiling {ceiling}.
    HiL: {true|false}. Erwartete Dauer: ~{N*30}s."
```

---

## Phase 1: WELLE 1 — Batch-Drafter (Sonnet) PARALLEL

**Pro Batch 1 Sonnet-Worker.** Alle parallel via `run_in_background: true`.

Worker-Prompt-Vorlage:
```
[WORKER-MODE] Welle 1 Batch-{NN} Conformance-Check (Sonnet)

REPO: {repo_root}
Branch: {current_branch}. Vergleichsbasis: {vs}.

DEINE {N} DATEIEN (production + zugehoerige tests):
{file_list_with_role_marker}
  prod / test-pulled / new-file / deleted

SEMANTIK-REGELN — LIES ZUERST:
1. {VAULT_ROOT}/Libraries/SemanticLibrary/_global/domain-glossary.md (KOMPLETT)
2. Pro File: passender Layer aus layers.yaml ableiten -->
   {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/naming-conventions.md
   {VAULT_ROOT}/Libraries/SemanticLibrary/_project/{LAYER}/domain-terms.md
   Bei mehreren Layern im Batch: alle relevanten Layer-Files lesen.

PRO DATEI (production):
1. git diff {vs} -- <file>
2. Read aktueller Stand (Working-Tree)
3. Pruefe gegen Regeln aus SemanticLibrary
4. Klassifiziere: PASS / INFO / WARN / VIOLATION
5. Bei Findings: Datei:Zeile + zitiere Regel + 1-2 Saetze Begruendung

PRO DATEI (test-pulled):
1. git diff {vs} -- <test-file>     (kann leer sein wenn Test nicht geaendert)
2. Read aktueller Stand
3. Pruefe gegen Test-Konventionen UND Konsistenz mit zugehoeriger Production-Aenderung:
   - Wenn Production geaendert aber Test unveraendert: WARN "test-not-updated"
   - Wenn Test fehlt fuer neue Production-Methode: WARN "missing-test-coverage"
4. Klassifiziere wie oben.

NUANCE — beabsichtigte neue Konventionen:
- Wenn Branch ABSICHTLICH neue Konvention einfuehrt: NICHT als Violation
- Pruefe: Konsistent mit Bestand?
- Subversive Brueche werden geflaggt.

OUTPUT: .claude/wissen/sl_pre_pr_batch_{NN}.md

Frontmatter:
---
type: pre-pr-conformance-batch
batch: {NN}
date: {DATUM}
files_in_batch: {N}
production_files: {P}
test_files: {T}
worker: drafter-{NN} (Sonnet)
---

Inhalt: per-file Sections (### {file} - {KAT}) mit Diff-Summary + Findings.

ABSCHLUSS:
1. TaskUpdate Task-ID auf status=completed
2. SendMessage team-lead 1-Satz-Bilanz:
   "Batch-{NN}: {N} Files | x PASS, y INFO, z WARN, w VIOLATION (test-not-updated: m)"
```

---

## Phase 2: Synthese-WELLE — Opus (ceiling)

NACH allen Batch-Drafter completed:

```
[WORKER-MODE] Welle 2 Synthese (ceiling)

LIES alle Batch-Reports:
.claude/wissen/sl_pre_pr_batch_*.md

KONSOLIDIERE Findings:
1. Sammle alle WARN/VIOLATION/INFO ueber alle Batches
2. Gruppiere thematisch (NICHT batch-bound):
   - Gruppe A: Bug-Findings (echte Defekte)
   - Gruppe B: Test-Drift (Test-not-updated, missing-coverage)
   - Gruppe C: Naming/XML-Doc-Konventionen (Stil-Drift)
   - Gruppe D: Architektur-Drift (Pattern-Brueche)
   - Gruppe E: Beabsichtigte Konventions-Erweiterungen (NICHT-Violation, dokumentieren)
3. Pro Gruppe:
   - Anzahl Findings
   - Top-3 Beispiele mit Datei:Zeile
   - Empfohlener Fix-Aufwand (TRIVIAL/LOW/MITTEL/HOCH)

SCHREIBE Master-Report:
.claude/wissen/sl_pre_pr_{FEATURE}_{DATUM}.md

INHALT:
- Executive Summary (Bilanz Files + Findings + Merge-Empfehlung GREEN/YELLOW/RED)
- Per-Gruppe Section (A-E) — KEIN per-file Detail (das ist in den Batch-Reports)
- Cross-Cutting-Beobachtungen
- Empfohlener Fix-Plan (Vor-Merge / Nach-Merge / Backlog)
- Test-Pull-In Statistik (wie viele Tests fehlen / sind veraltet?)
- Methodik

ABSCHLUSS:
1. TaskUpdate Synthese-Task auf completed
2. SendMessage team-lead: Pfad + Empfehlung + Top-3 Must-Fix + Bilanz +
   Liste der Findings-Gruppen (A-E mit jeweils Anzahl)
```

---

## Phase 3: Auswertung — Zwei Pfade

### Pfad A — `--hil false` (Default, autonom)

```
1. Team Lead liest Synthese-Master-Report.
2. Falls --no-pl: SKIP, Report bleibt nur unter .claude/wissen/.
3. Sonst: ADDITIV in Parking-Lot anhaengen.
   Format wie /_SL_conformance — neue Sektion "## {DATUM} - Pre-PR Conformance":
     ### Must-fix vor Merge
       - [ ] CONF-N-{TYP}: ... (KRITISCH/WARN aus Gruppe A/B)
     ### Backlog
       - [ ] CONF-N-{TYP}: ... (INFO aus Gruppe C/D/E)
4. Team-Lead-Status-Display: Bilanz + Top-3 + PL-Anhang gemeldet.
```

### Pfad B — `--hil true` (Read-Only Reflexions-Modus)

```
1. Team Lead liest Synthese-Master-Report (Gruppen A-E).
2. Pro Gruppe (sequentiell, 1 nach der anderen):
   a. Skill aufrufen: /_assay "Wovon Gruppe {X} der Pre-PR-Befunde wirklich handelt"
      mit @kontext = Master-Report + Top-3 Findings dieser Gruppe.
      Output: .claude/presentation/sl_pre_pr_group_{X}.md
      (Reflektiver Mini-Essay — Essenz der Gruppe, KEIN Fix-Plan)
   b. User liest den Assay (vorher/nachher Stil — was waere die Implikation
      eines Fix? Was bleibt wenn nicht?).
   c. Skill aufrufen: /_question "Gruppe {X} ({K} Findings, Top: ...) jetzt umsetzen?"
      mit Optionen:
        - JA: Items in Parking-Lot anhaengen mit Status [ ]
        - NEIN: SKIP, Items NICHT in PL anhaengen, Entscheidung loggen
        - SPAETER: Items in PL anhaengen mit Status [~] (parked)
        - TEILWEISE: User markiert manuell welche Items in den ersten Lauf
      Antwort + Notes wird in .claude/wissen/sl_pre_pr_decisions_{DATUM}.md persistiert.
   d. Je nach Antwort: PL-Anhang dieser Gruppe ausfuehren oder ueberspringen.
3. NACH allen Gruppen:
   Team-Lead-Status-Display: gesamt-PL-Anhang, Anzahl SKIP, naechster Schritt.

KEIN /_assay+/_question fuer Gruppe E (beabsichtigte Konventions-Erweiterungen) —
diese werden nur dokumentiert, KEINE Frage ob umsetzen.
```

---

## Phase 4: Parking-Lot Anhang — additiv (INV-PREPR-7)

```
PFAD ZUM PL: {VAULT}/.../6_PL/{bl_id}-parking-lot.md
            (Vault aus vault-routing.json, Backlog-Subfolder pro Branch)

REGELN:
- KEIN Replace bestehender Items.
- KEIN Delete von Items mit Status [x] / [~].
- Sektion "## Abgeschlossen" am Ende NICHT verschieben.
- Neue Sektion VOR "## Abgeschlossen" einfuegen:
  "## {DATUM} - Pre-PR Conformance"
- Items numerieren als CONF-N-{TYP} mit fortlaufender N (lokal pro Sektion ok).
- Bilanz-Header in Sektion: "Bilanz: x PASS, y WARN, z INFO. Quelle: {Master-Report-Pfad}."

EINBETTUNG IN /_parking-lot SKILL:
- Bevorzugt: Falls /_parking-lot Skill APPEND-Modus unterstuetzt -> diesen nutzen
  fuer konsistentes Frontmatter / Indexing.
- Fallback: direkt Edit auf parking-lot.md (so wie /_SL_conformance es macht).
```

---

## Output-Struktur

```
.claude/wissen/
  sl_pre_pr_batch_01.md                  <- Batch-1 Drafter (Sonnet)
  sl_pre_pr_batch_02.md                  <- Batch-2
  ...
  sl_pre_pr_batch_NN.md
  sl_pre_pr_{FEATURE}_{DATUM}.md         <- Synthese (ceiling)
  sl_pre_pr_decisions_{DATUM}.md         <- nur bei --hil true

.claude/presentation/
  sl_pre_pr_group_A.md                   <- /_assay je Gruppe (nur --hil true)
  sl_pre_pr_group_B.md
  ...

{VAULT}/.../6_PL/{bl_id}-parking-lot.md
  ## {DATUM} - Pre-PR Conformance
    > Quelle: .claude/wissen/sl_pre_pr_{FEATURE}_{DATUM}.md
    > Bilanz: ... Merge-Empfehlung: ...
    ### Must-fix vor Merge
    - [ ] CONF-N-...
    ### Backlog
    - [ ] CONF-N-...
```

---

## Graceful Degradation

| Situation | Verhalten |
|-----------|-----------|
| Diff gegen vs leer | STOPP: "Branch hat keine Aenderungen vs {vs}" |
| SemanticLibrary leer | STOPP: "Run /_SL_init zuerst" |
| Test-File existiert nicht (Heuristik kein Treffer) | KEIN Fehler — WARN-Finding "missing-test" |
| Production-File geloescht (deleted in Diff) | Drafter prueft nur ob Test ebenfalls geloescht / migriert wurde |
| Batch-Drafter Timeout / API-Error | TaskUpdate failed, Synthese ueberspringt mit Hinweis "Batch-NN incomplete" |
| Synthese-Worker Fehler | Batch-Reports bleiben nutzbar; Master-Report wird vom Team Lead inline erstellt |
| Parking-Lot Datei fehlt | WARN + --no-pl Verhalten erzwingen |
| --hil true aber keine User-Antwort innerhalb Timeout | Default: SPAETER (Items mit [~] anhaengen) |

---

## Abgrenzung

```
/_SL_init        = SemanticLibrary EINMALIG befuellen (Bootstrap, Code-Scan)
/_SL_conformance = Unstaged-Batch-Pruefung (Working-Tree, layer-bound)
/_SL_pre_pr      = BRANCH-TOTAL Pruefung HEAD vs develop (file-batched, HiL-faehig) <- DIESE
/_PT_extract     = Einzelnes Pattern aus Code extrahieren
/_PT_update      = Pattern manuell registrieren/upgraden
/_Pre_PR_orchestrate = Pre-Merge-Battle-Test (Pattern-Promotion, Build, Tests)

Reihenfolge in einer typischen DCSRE-Story:
  Branch-Arbeit
   -> /_SL_conformance (laufend, pro Batch unstaged)
   -> commits
   -> /_SL_pre_pr (manuell vor PR, gegen develop)             <-- DIESES Command
   -> Fix Must-Fixes aus PL
   -> /_Pre_PR_orchestrate (Build/Tests/Pattern-Battle)
   -> PR (gh pr create — User-Freigabe Pflicht)
```

---

## Memory-Regeln (DCSRE)

- Drafter IMMER sonnet (nicht ceiling, nicht middle) — Memory `feedback_drafter_immer_sonnet`
- Backend-Only Scope (default Sources/Backend/) — Memory `feedback_backend_only_scope`
- HiL-Default off — Memory `Dark Factory`
- PR niemals autonom — Memory `PR VERBOTEN`
- Status-Display: Modelle + 1-Satz-Zustand bei Welle-Spawn — Memory `feedback_status_display`
- Nvim fuer Praesentationen oeffnen — Memory `feedback_open_with_nvim` (User oeffnet, nicht das Command)
- Bob-Spawns explizit `model="sonnet"` (gilt nicht hier — wir spawnen sonnet/opus, kein Bob)

---

## Beispiel-Lauf

### Autonom (--hil false, Default)

```
/_SL_pre_pr

→ Diff vs develop: 63 Production + 28 Tests = 91 Files
→ Test-Pull-In: 4 missing-test WARNs
→ Batches: 12 a ~8 Files (file-balanced, prod+test gepaart)
→ W1: 12 Sonnet-Drafter parallel
→ W2: 1 Opus-Synthese (blocked_by W1)
→ Bilanz: 78 PASS / 6 WARN / 31 INFO / 0 VIOLATION
→ Gruppen: A=1 (Bug), B=4 (Test-Drift), C=12 (Naming), D=2 (Arch), E=12 (Beabsichtigt)
→ Merge-Empfehlung: YELLOW
→ PL-Anhang ADDITIV: 7 Items must-fix + 14 Items backlog
```

### HiL-Modus (--hil true)

```
/_SL_pre_pr --hil true

→ Wie oben bis Synthese
→ Pro Gruppe (A,B,C,D — NICHT E):
  /_assay "Was Gruppe A wirklich bedeutet"  (User liest)
  /_question "Gruppe A umsetzen?"            (User entscheidet)
    - JA  -> 1 Item in PL als [ ]
    - NEIN -> SKIP, in decisions.md geloggt
    - SPAETER -> 1 Item als [~]
  ... naechste Gruppe
→ User-Steuerung: kann jederzeit abbrechen, Reihenfolge der Gruppen folgt KAT-Schwere
   (A Bug -> B Test-Drift -> D Arch -> C Naming).
```
