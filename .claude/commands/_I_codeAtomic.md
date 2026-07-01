---
type: building-block
---

# /_I_codeAtomic

**Status:** v5.1 (BL-065: Vault-First DirectWrite, Hybrid-Marker ersetzt)
**Actor:** ATOMARER CODER
**Zweck:** Unit Tests + Production Code via Red-Green-Refactor (Batch: 3-5 Tests pro Aufruf)

---

## Vertrag

```
+===============================================================+
|  COMMAND: /_I_codeAtomic {SLICE_NAME}                          |
+===============================================================+
|                                                                |
|  LIEST (Input) - PFLICHT:                                      |
|    1. {VAULT}/_manifest.md                            |
|    2. .claude/CURRENT_SLICE.md (falls Mitose-Worktree)        |
|    3. .claude/analysis/plans/{NAME}-{SLICE}-PLAN.md            |
|       → Test-Liste, Architektur, Pattern Reuse                |
|    4. .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md       |
|       → RESUME: Falls vorhanden, lies status + done Tests     |
|    5. {VAULT_ROOT}/Libraries/PatternLibrary/_index.md  (VAULT-ONLY, INV-PL-VAULT-1) (Blueprint)        |
|    6. Codebase (Produktion + bestehende Tests)                |
|                                                                |
|  LIEST (Input) - OPTIONAL bei Code-Generierung:               |
|    7. {META}/implementation/testing.md                   |
|       → TestBase<T> Vererbung, TestBuilder, Fixtures           |
|       → Falls fehlt: WARN + CONTINUE (kein ABORT)             |
|       → Lesen VOR Schritt 1 (RED)                             |
|                                                                |
|  SCHREIBT (Output) - PFLICHT:                                  |
|    1. Code: Unit Tests + Production Code (via TDD)            |
|    2. Vault-First (BL-065)                                     |
|       Implementation-Logs werden DIREKT in den Vault geschrieben:|
|       {VAULT}/Backlog/{BL_SLUG}/Implementation/{NAME}-ATOMIC-{SLICE}.md |
|       Status (partial/final) wird im FRONTMATTER der Log-Datei |
|       kodiert, NICHT ueber Pfad-Unterschied.                   |
|       Pre-Flight-Check (verbindlich, RF-06):                   |
|       mkdir -p {VAULT}/Backlog/{BL_SLUG}/Implementation/ |
|       if [ $? -ne 0 ] || [ -z "$DCS_VAULT_ROOT" ]; then       |
|         log_error "Vault unreachable: ..."                     |
|         exit 1                                                 |
|       fi                                                       |
|       Schreibpfad: {VAULT}/Backlog/{BL_SLUG}/Implementation/{NAME}-ATOMIC-{SLICE}.md |
|       Frontmatter: status: partial|final (Feld, nicht Pfad).  |
|       INKREMENTELL (status=partial): lokal zwischenspeichern   |
|       .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md       |
|       → status: partial (N/M) oder final (M/M)               |
|    3. {VAULT}/_manifest.md (nach JEDEM Test update)  |
|                                                                |
|  SCHREIBT (Output) - OPTIONAL:                                 |
|    {VAULT_ROOT}/Libraries/PatternLibrary/_index.md  (VAULT-ONLY, INV-PL-VAULT-1)                       |
|    {VAULT}/_parking-lot.md (APPEND bei Findings)     |
|                                                                |
|  MCP: mcp__cleancoder__query() NUR bei Unsicherheit           |
|    MIN-Modus: max 1 Query, limit=1                            |
|                                                                |
|  WORKER-TEST-ISOLATION (W224, RF-PI-003):                      |
|    Worker fuehrt NUR Tests aus die er geschrieben oder         |
|    angefasst hat. KEINE fremden Tests starten.                 |
|    Begruendung: Parallelitaet bei Worktrees — Race Conditions  |
|    bei DB-Tests, File-Locks, Port-Konflikte.                   |
|    Enforcement: Teil des KURZLEBIG_PROMPT (statische Regel).   |
|                                                                |
|  BATCH-MODUS:                                                  |
|    Bearbeite 3-5 Tests pro Aufruf, dann STOPPE.              |
|    User ruft Command erneut auf fuer naechsten Batch.        |
|    Resume liest ATOMIC.md → weiss wo weitermachen.            |
|                                                                |
|  PIPELINE:                                                     |
|    [/_I_cleanCodeSlice] → [/_I_codeAtomic] →                  |
|    [/_I_codeIntegration]                                       |
|                                                                |
|  VORAUSSETZUNG:                                                |
|    PLAN-{SLICE}.md existiert (status=final)                   |
|                                                                |
|  ERGEBNIS:                                                     |
|    ATOMIC-{SLICE}.md (status=partial oder final)              |
|    partial → User ruft erneut auf                             |
|    final   → /_I_codeIntegration kann starten                |
|                                                                |
+===============================================================+
```

---

## Verantwortlichkeit

**ATOMARER CODER:** Unit Tests + Production Code via TDD (30-Sekunden-Zyklen)

**TUT:** Unit Tests schreiben (RED), minimalen Code (GREEN), refactoren (REFACTOR),
Blueprint nutzen, Pattern Library aktualisieren, Manifest nach jedem Test updaten.

**NICHT:** Integration Tests, System Tests, Architektur planen.

**Eskalation:** Bei 5+ RGR ohne Fortschritt → /_SC_observe

---

## Schritt 0: Resume-Check + Inputs

### 0.1 Mitose-Check

```
Falls .claude/CURRENT_SLICE.md existiert:
  → {SLICE_NAME} aus CURRENT_SLICE.md verwenden
  → NUR an diesem Slice arbeiten
```

### 0.2 Resume-Check (NEU v4.0)

```
Falls .claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md existiert:
  → Lies Frontmatter: status, tests_done, tests_total, next_test
  → Falls status=final:
      AUSGABE: "ATOMIC Phase bereits abgeschlossen (M/M Tests)."
      AUSGABE: "Naechster Schritt: /_I_codeIntegration {SLICE}"
      → STOP (nichts zu tun)
  → Falls status=partial:
      AUSGABE: "Resume: {tests_done}/{tests_total} Tests fertig."
      AUSGABE: "Starte bei {next_test}."
      → Setze fort beim naechsten Test
Falls NICHT existiert:
  → Neuer Start bei T1
```

### 0.3 Standard-Inputs

1. Lies `_manifest.md` → {NAME}, Slice-Status
2. Lies `plans/{NAME}-{SLICE}-PLAN.md` → Test-Liste, Blueprint
3. Lies `_pattern-library.md` (falls vorhanden)
4. Bestimme: Welche Tests sind noch offen?
5. Bestimme BATCH_SIZE:
   - Einfache Tests (GRAY/Blueprint): 5 pro Batch
   - Mittlere Tests (ORANGE/Angepasst): 4 pro Batch
   - Komplexe Tests (RED/Custom): 3 pro Batch

---

### 0.4 Optional-Input: Implementation Meta

Fuer relevante Topics laden (falls Datei existiert):
  - `{META}/implementation/testing.md` (TestBase<T>, TestBuilder, Fixtures)

Falls Datei nicht existiert:
  - WARN: "⚠️ `{META}/implementation/testing.md` nicht gefunden — weiter ohne"
  - CONTINUE (kein ABORT)

Falls Datei vorhanden: Regeln R1..Rn extrahieren und als Vorgaben in RED/GREEN/REFACTOR nutzen.
Beim Schreiben referenzieren: `// testing.md R1: TestBase<T> angewendet`

Bei RESUME (status=partial): testing.md erneut lesen — kein Cache. Meta kann via `/_I_updateMeta` aktualisiert worden sein.

---

## Test-Filter: KEINE logiklosen Tests

```
BEVOR ein Test geschrieben wird, pruefe:

  VERBOTEN — Tests die NUR Framework-Verhalten verifizieren:
    ✗ AutoMapper Property-Mapping (A.Prop → B.Prop)
    ✗ Entity Framework Navigation Properties
    ✗ DI-Container Registrierung (AddScoped/AddTransient)
    ✗ Reine Getter/Setter ohne Logik
    ✗ DTO/BO Konstruktor setzt Default-Werte

  FAUSTREGEL:
    "Wenn der GREEN-Schritt NULL eigenen Code erfordert
     (weil ein Framework/Library die Arbeit macht)
     → Test hat keinen Wert → SKIP."

  ERLAUBT — Tests mit echtem Erkenntnisgewinn:
    ✓ Business-Logik (Berechnung, Entscheidung, Transformation)
    ✓ Zustandsuebergaenge (Status A → B unter Bedingung X)
    ✓ Fehlerbehandlung (Exception bei ungueltigem Input)
    ✓ Randfall-Verhalten (null, leer, Grenzwerte)
    ✓ Mapping MIT Logik (Konvertierung, Bedingte Felder)

  BEI PLAN-REVIEW:
    Tests aus PLAN.md die unter VERBOTEN fallen → SKIP + Kommentar
    in ATOMIC.md: "T{N}: SKIP (logiklos, reines Framework-Mapping)"
```

---

## Schritt 0.5: 3 Einstiegsfragen (VOR jedem Batch — PFLICHT)

Bevor der erste Test geschrieben wird, beantworte diese 3 Fragen:

```
1. Was ist der EINFACHSTE Test der mich zwingt, echten Code zu schreiben?
   → Starte mit dem trivialsten Edge Case (null, leer, Grenzwert)
   → NICHT mit dem Normalfall ("Don't go for the gold" — Uncle Bob)

2. Welchen Edge Case deckt dieser Test ab?
   → Benenne explizit die Grenze die getestet wird
   → Ein guter erster Test zwingt zu einer if-Abfrage oder einem Guard

3. Braucht dieser Test ueberhaupt eigenen Production-Code?
   → Falls der GREEN-Schritt NULL eigenen Code erfordert → SKIP
   → Logiklose Tests verschwenden Zeit (siehe Test-Filter)
```

---

## TDD-Methodik: Gegenlaeufer-Prinzip (PFLICHT — Uncle Bob)

```
REIHENFOLGE DER TESTS (konzentrische Kreise, von aussen nach innen):

  Kreis 1 (Randfall):  Leere Listen, null, 0, Grenzwerte
                        → Erzwingt Guards + Initialisierung
  Kreis 2 (Einfach):   Ein-Element-Fall, Normalfall
                        → Erzwingt Kernlogik
  Kreis 3 (Komplex):   Mehrere Elemente, Kombinationen, Edge-Edge
                        → Erzwingt Generalisierung

PRINZIP: Tests werden SPEZIFISCHER → Code wird GENERISCHER.
         "As the tests get more specific, the code gets more generic."

ANTI-PATTERN: Direkt den Normalfall testen → zu viel Code auf einmal →
              kein inkrementeller Fortschritt → "Going for the gold".
```

---

## Schritt 1: RGRC-Loop (Batch-Modus) — Red-Green-Refactor-CHECK

### Fuer die naechsten BATCH_SIZE Tests aus der offenen Liste:

**RED:**
1. Test aus PLAN.md nehmen (Arrange-Act-Assert)
2. FILTER: Ist dieser Test logiklos? → SKIP (siehe Test-Filter)
3. "Don't go for the gold": Waehle den EINFACHSTEN naechsten Test
   → Nicht den offensichtlichsten, sondern den der am wenigsten Code erfordert
4. Test ausfuehren → MUSS fehlschlagen
5. Falls sofort gruen → Test ist trivial, ueberdenken

**GREEN:**
1. MINIMALER Code um Test zu passen (Fake OK, Hardcoded OK)
2. Blueprint aus PLAN.md als Vorlage
3. KEINE Vorausplanung — nur genau den Code den der Test verlangt
4. Test ausfuehren → MUSS gruen sein
5. ALLE bisherigen Tests → MUESSEN gruen bleiben

**REFACTOR:**
1. DRY, Extract Method/Class, Rename, Move
2. Tests bereinigen (Setup-Methoden, Helper)
3. Pattern-Check (bekannt? neu?)
4. ALLE Tests → MUESSEN gruen bleiben

**CHECK (4. Schritt — nach REFACTOR, vor naechstem RED):**
1. Passt der geschriebene Code zum Sub-Blueprint (falls vorhanden)?
   → Lese Sub-Blueprint "## Exit-Kriterien" — naehere ich mich dem Ziel?
2. Habe ich die Grenze meines Slices ueberschritten?
   → Falls Code ausserhalb des Slice-Scope → Finding dokumentieren
3. Ist eine Abweichung vom Blueprint entstanden?
   → Falls ja: Dokumentiere Abweichung in ATOMIC.md "## Abweichungen"
   → Entscheide: Absichtlich (Blueprint falsch) oder versehentlich (Code korrigieren)

**CHECKPOINT (nach JEDEM gruenen Test):**
1. Manifest aktualisieren (Test-Fortschritt)
2. ATOMIC-{SLICE}.md aktualisieren (inkrementell)

### Batch-Ende

Nach BATCH_SIZE Tests:

```
Falls ALLE Tests aus PLAN.md fertig:
  → ATOMIC.md mit status=final schreiben
  → AUSGABE: "ATOMIC Phase abgeschlossen ({M}/{M} Tests)."
  → AUSGABE: "Naechster Schritt: /_I_codeIntegration {SLICE}"

Falls noch Tests offen:
  → ATOMIC.md mit status=partial schreiben
  → AUSGABE: "{done}/{total} Tests fertig."
  → AUSGABE: "Naechster Batch: /_I_codeAtomic {SLICE}"
```

---

## Schritt 2: MCP bei Bedarf

| Situation | Query |
|-----------|-------|
| Unsicher wie testen | "how to test {behavior}" |
| Code Smell erkannt | "refactoring {smell}" |
| Pattern entsteht | "design pattern for {structure}" |
| Stuck (>3 Versuche) | "getting unstuck in TDD {problem}" |

---

## Schritt 3: Stagnations-Erkennung

```
RGR_OHNE_FORTSCHRITT Zaehler:
  Test gruen → Reset auf 0
  Test NICHT gruen → +1
  >= 4: MCP Query
  >= 5: Eskalation → /_SC_observe
```

---

## Output-Format: ATOMIC-{SLICE}.md (INKREMENTELL)

**Pfad:** `.claude/analysis/synthese/{NAME}-ATOMIC-{SLICE}.md`

```markdown
---
name: {NAME}
slice: {SLICE_NAME}
phase: atomic
pipeline: implementation
status: partial
tests_total: 20
tests_done: 5
next_test: T6
batch_size: 5
batches_completed: 1
last_updated: {YYYY-MM-DD}
---

# Atomic: {NAME} - {SLICE_NAME}

**Tests:** {done}/{total} | **Status:** partial | **Batches:** {N}

## Test-Ergebnisse

| # | Test | Status | RGR | Pattern |
|---|------|--------|-----|---------|
| T1 | {Test-Name} | GRUEN | 1 | GRAY |
| T2 | {Test-Name} | GRUEN | 2 | ORANGE |
| T3 | {Test-Name} | GRUEN | 1 | GRAY |
| T4 | {Test-Name} | GRUEN | 1 | RED |
| T5 | {Test-Name} | GRUEN | 3 | RED |
| T6 | {Test-Name} | OFFEN | - | - |
| ... | ... | OFFEN | - | - |

## RGR-Protokoll

### Batch 1 (T1-T5)
- T1: RED weil {X} → GREEN mit {Y} → REFACTOR {Z}
- T2: RED weil {X} → GREEN mit {Y} → REFACTOR {Z}
- ...

## Refactoring-Entscheidungen

| # | Refactoring | Begruendung |
|---|-------------|-------------|
| 1 | Extract Method: {Name} | DRY |

## Naechster Batch

T6-T10 (/_I_codeAtomic {SLICE_NAME})
```

Wenn status=final: Ersetze "Naechster Batch" durch:
```
## Naechster Schritt
/_I_codeIntegration {SLICE_NAME}
```

---

## Manifest-Update (nach JEDEM gruenen Test)

```markdown
**PHASE:** _I_codeAtomic {SLICE_NAME}
**PIPELINE:** Implementation
**TESTS:** {done}/{total} (T1-T{done} GRUEN, T{done+1} OFFEN)
**STATUS:** partial | final
**NAECHSTER TEST:** T{done+1}: {Test-Name}
**BATCH:** {N} von geschaetzt {ceil(total/batch_size)}
```

---

## Qualitaetskriterien

- TDD Drei Gesetze strikt einhalten (kein Production Code ohne roten Test)
- RED vor GREEN vor REFACTOR vor CHECK (4-Schritt-Reihenfolge!)
- "Don't go for the gold" — einfachster Test zuerst, nicht offensichtlichster
- Gegenlaeufer-Prinzip: Edge Cases → Normalfall → Komplex (konzentrische Kreise)
- 3 Einstiegsfragen VOR jedem Batch beantwortet
- CHECK-Schritt: Blueprint-Abgleich nach jedem Refactor
- ALLE Tests gruen nach jedem Schritt
- Blueprint aus PLAN.md nutzen
- Manifest nach JEDEM Test aktuell
- ATOMIC.md nach JEDEM Test aktuell (inkrementell!)
- Batch-Limit einhalten (3-5 Tests, dann STOP)
- Bei Stagnation eskalieren (nicht endlos versuchen)
- KEINE logiklosen Tests (reines Mapping, Getter/Setter, Framework-Verhalten)
- Jeder Test MUSS eigenen Production-Code im GREEN-Schritt erfordern
- XML-Docs in C#: ECHTE Umlaute (ä, ö, ü, ß) — NIEMALS ae, oe, ue, ss
- XML-Docs: Einfaches Deutsch, KEINE kryptischen Referenzen (T1, S4, W12, PLAN.md)

---

## exit_report (PFLICHT - VOR NOTIFY)

**IMMER schreiben** — egal ob status=partial oder status=final.
Schreibe diesen Block ans Ende der ATOMIC-{SLICE}.md Synthese-Datei (APPEND):

```yaml
exit_report:
  status: partial|final
  blocked_items: []          # Tests die nicht bearbeitet werden konnten
  block_reason: ""           # Warum blockiert (z.B. "Kontext-Limit", "Entity fehlt")
  recommended_strategy: ""   # Empfehlung fuer naechsten Batch (z.B. "Resume ab T6")
  context_health: ""         # low|medium|high — wie viel Kontext war noch verfuegbar
  findings: []               # Erkenntnisse ausserhalb des Scope (W{n}-Kandidaten)
```

**Regeln:**
- `findings` NIEMALS leer lassen wenn Erkenntnisse vorhanden — diese werden Parking-Lot-Kandidaten
- `context_health: low` wenn Kontext-Limit Grund fuer partial war
- `block_reason` bei `status: final` leer lassen ("")
- Falls `findings` nicht leer: APPEND an `{VAULT}/_parking-lot.md`

---

## NOTIFY (Pflicht - Allerletzter Schritt)

**NUR wenn ALLES fertig ist** (exit_report geschrieben, Zusammenfassung ausgegeben):

```bash
powershell -Command "notify '{FEATURE} /_I_codeAtomic abgeschlossen'"
```

WICHTIG: Keine Zwischen-Benachrichtigungen! NUR ganz am Ende.
