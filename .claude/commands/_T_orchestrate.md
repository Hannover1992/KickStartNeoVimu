# /_T_orchestrate — Test-Verifikation Orchestrator

```yaml
status: active
version: 1.2.0
created: 2026-03-30
updated: 2026-04-02
op: TestOrchestrator
phase: Verification
type: orchestration
chain_position: post-implement
depends_on:
  - _I_orchestrate
  - _SDF_orchestrate
feeds_into:
  - _SDF_orchestrate
  - _parking-lot.md
related:
  - _TDD_orchestrate
  - _TDD_execute
  - _I_testSearch
```

---

## ABGRENZUNG (WICHTIG — lies das ZUERST)

| Command | Zweck |
|---------|-------|
| `/_T_orchestrate` | **Test-Verifikation**: Bestehende Tests ausfuehren, Regression pruefen |
| `/_TDD_orchestrate` | **TDD-Entwicklung**: Red/Green/Refactor, NEUE Tests schreiben |

`/_T_orchestrate` schreibt KEINE Tests. Es verifiziert NUR, dass bestehende Tests gruen sind.

---

## VERTRAG

```
+======================================================================+
| COMMAND: /_T_orchestrate {NAME}                                       |
+======================================================================+
|                                                                        |
| ACTOR: TEAM LEAD (SDF delegiert hierher via Handschuh-Wechsel)       |
|                                                                        |
| ZWECK: Stufen-basierte Test-Verifikation.                             |
|   Pro Stufe: testSearch (Tests finden) + TDD_execute (Tests laufen). |
|   Bei FAIL: PL-Item erstellen. Bei ALL PASS: Erfolg melden.          |
|                                                                        |
| AUFGERUFEN VON: /_SDF_orchestrate (nach I-Completion, PFLICHT)       |
| GIBT ZURUECK AN: /_SDF_orchestrate (Handschuh-Wechsel)              |
|                                                                        |
| LIEST (Input) - PFLICHT:                                              |
|   1. {VAULT}/_session_params.md                                       |
|      (tdd_stages: Array der zu pruefenden Stufen, z.B. [1,2,3,4,5]) |
|   2. {VAULT}/_manifest.md                                             |
|      (Pipeline-State, Feature-Name)                                   |
|   3. .claude/meta/implementation/stage_{N}.md                         |
|      (test_projekte, testbefehl — pro Stufe)                          |
|                                                                        |
| LIEST (Input) - OPTIONAL:                                              |
|   4. {VAULT}/Task.md                                                   |
|      (User-Story / Ticket-Beschreibung — fuer Scope-basierte          |
|       Test-Selektion via --user-story, RF-TS-001/ADR-TS-001)         |
|      Wenn nicht vorhanden → user_story_scope = null (Fallback)        |
|                                                                        |
| SCHREIBT (Output) - PFLICHT:                                          |
|   {VAULT}/_manifest.md:                                               |
|     T_ORCHESTRATE_STATE:                                              |
|       status: {RUNNING | DONE_PASS | DONE_FAIL}                     |
|       stages_passed: [1, 2, ...]                                      |
|       stages_failed: [3, ...]                                         |
|       started_at: "{DATUM}"                                           |
|       finished_at: "{DATUM}"                                          |
|   {VAULT}/_parking-lot.md (APPEND, nur bei FAIL):                    |
|     Neues PL-Item pro fehlgeschlagener Stufe                          |
|                                                                        |
| HAUPTPRODUKT:                                                         |
|   Stufen-basierte Test-Verifikation mit Monitoring-Tabelle            |
|                                                                        |
| INVARIANTEN:                                                          |
|   - Team Lead fuehrt KEINE Tests selbst aus (R2, CS5)                |
|   - Team Lead spawnt KEINE Agents fuer direkte Test-Ausfuehrung      |
|   - NUR Skill(_I_testSearch) + Skill(_TDD_execute) als Tandem        |
|   - Kein Abbruch bei FAIL (verify-only: alle Stufen durchlaufen)     |
|   - KEIN git commit, KEIN git push                                    |
+======================================================================+
```

---

## STUFEN-SPEZIFISCHES WORKFLOW-PATTERN (PFLICHT-LESEN)

Vor dem Spawn eines Test-Workers MUSS der Team Lead die `stage_{N}.md` der jeweiligen Stufe lesen und das dort beschriebene Workflow-Pattern befolgen. Stage-spezifische Konventionen sind autoritativ — sie ergaenzen den hier beschriebenen Ablauf um konkrete Befehle, Trait-Namen, Container-Konfiguration und Watchdog-Regeln.

> **Stage-Resolution (BL-392 AK-CONSUMER-REWRITE):** Die Stage-Doc-Aufloesung laeuft ueber den
> kanonischen `resolve_vault_stage`-Resolver (Dual-Read) — NICHT mehr per Direkt-Pfad. Ist die Stage
> in den Vault migriert (`{VAULT}/Stage/stage_N_<name>/`), liest der Lead den jeweiligen Concern-Slice
> (`execute`/`setup`/`teardown`/...); ist sie noch nicht migriert, faellt der Resolver auf den
> Legacy-Monolith `.claude/meta/implementation/stage_N.md` zurueck (IDENTISCH zu heute). Hier
> referenziertes `stage_{N}.md` meint diesen kanonischen Slice-Satz bzw. seinen Legacy-Fallback.

**Insbesondere fuer Stage 3 (Integration / Docker):**
- Tandem-Pattern: 1 Test-Runner (sonnet) + 1 Watchdog (haiku) parallel im Team — siehe `stage_3.md` Abschnitt "Workflow-Pattern: Tandem-Lauf mit Watchdog".
- Befehls-Wrapper `powershell.exe -Command` ist Pflicht (Cmd-Quoting + Out-String + Stderr-Merge).
- Result-Datei pro Test-Lauf nach `.claude/analysis/test-runs/test{N}-{shortName}-{TS}.md`.
- Trait-Filter: `Category=Docker` (NICHT `Category=Integration` — als Trait nicht existent; NICHT `Category=System` — Entwurf, nicht durchgegangen).
- Docker-Forensik: Watchdog scannt Container-Logs alle 45 s nach stillen Warnleuchten (Login-Failed, Migration-Konflikte, OOM) — diese kommen NICHT im Test-Output an.

**Insbesondere fuer Stage 7 (User-Journey / Browser via Playwright MCP):**
- Stage 7 ruft KEIN `dotnet test` auf, sondern delegiert an `Skill(_user_journey)`.
- **PRE-FLIGHT-CHECK PFLICHT:** Bevor Stage 7 startet, MUSS der Team Lead beim User explizit bestaetigen lassen:
  - Frontend laeuft (lokal `npm start` ODER Docker) auf https://localhost:8443?
  - Backend laeuft (lokal `dotnet run` ODER Docker) auf https://localhost:5443?
  - Datenbank + Keycloak Container healthy?
  - Test-User-Daten geseedet?
  Wenn EINE Frage mit "nein" beantwortet wird → Stage 7 abbrechen (`stages_no_tests` markieren), Hinweis "System nicht bereit" loggen.
- **Tools:** Nur Playwright MCP (`browser_navigate`, `browser_snapshot`, `browser_click`, `browser_type`, `browser_fill_form`, `browser_evaluate`, `browser_take_screenshot`, `browser_wait_for`).
- **Result-Datei:** `.claude/output/UJ-{FEATURE}-{DATE}.md` (durch Skill geschrieben).
- **Test-Quelle:** Klartext-Journey (entweder inline an Skill uebergeben oder aus `.claude/scripts/journeys/{FEATURE}.md` gelesen) — KEINE xUnit-`[Trait]`s, KEINE .cs-Test-Datei.

Stage 1 + 2 + 4 + 5 haben keine Container-Pflicht und brauchen keinen Watchdog — siehe jeweilige `stage_{N}.md`.

---

## ANTI-PATTERN Guards

```
# VERBOTEN (CS5, VERTRAG Z155):
  Team Lead fuehrt "dotnet test" SELBST aus (Bash/PowerShell)
  → RICHTIG: Skill(_TDD_execute)

# VERBOTEN (W7, R9):
  spawn_agent() / TaskCreate fuer direkte Test-Ausfuehrung
  → RICHTIG: Skill(_TDD_execute) — der Command weiss wie man Tests startet

# VERBOTEN:
  Tests schreiben, Code aendern, Architektur aendern
  → Das ist _TDD_orchestrate Territorium, NICHT _T_orchestrate

# VERBOTEN:
  Stufen ueberspringen oder bei FAIL abbrechen
  → Alle Stufen aus tdd_stages MUESSEN durchlaufen werden (verify-only)
```

---

## Aufruf

```
/_T_orchestrate {NAME}

Parameter:
  NAME:  Feature-Name (PFLICHT, wird an Sub-Commands durchgereicht)

Beispiel:
  /_T_orchestrate BigDarkFactory
  /_T_orchestrate DCSRE-881
```

---

## Ablauf

### Schritt 0: Team + Parameter + Manifest (PFLICHT — CaseStudy DCSRE-1672)

```
# ═══ TEAM ERSTELLEN (Fix PL #3: "KEIN TeamCreate") ═══
# PFLICHT: Team MUSS vor jeder Aktion erstellt werden.
# Ohne Team: Agents laufen ohne Isolation, Skill-Routing kann fehlschlagen.
# CaseStudy DCSRE-1672: Agent sprang direkt rein ohne Team → 3x User-Korrektur.
TeamCreate: "t-{NAME}"
Logge: "[T_orchestrate] Team t-{NAME} erstellt"

1. Lies {VAULT}/_session_params.md:
   - tdd_stages: Array (z.B. [1, 2, 3, 4, 5])
   - IF tdd_stages nicht vorhanden oder leer:
     → FEHLER: "tdd_stages nicht in _session_params.md — ABBRUCH"
     → Handschuh-Wechsel zurueck an SDF mit Fehler-Signal
   - Logge: "[T_orchestrate] tdd_stages geladen: {tdd_stages}"

2. Lies {VAULT}/_manifest.md:
   - Bestaetige Feature-Name passt zu {NAME}
   - Lies aktuellen Pipeline-State

3. Schreibe Manifest (T_ORCHESTRATE_STATE Initialisierung — PFLICHT!):
   # ═══ MANIFEST-INIT (Fix PL #3: "KEIN Manifest-State") ═══
   # PFLICHT: T_ORCHESTRATE_STATE MUSS geschrieben werden BEVOR die Stufen-Loop startet.
   # Ohne Manifest-State: Resume unmoeglich, SDF kann Ergebnis nicht lesen.
   T_ORCHESTRATE_STATE:
     status: RUNNING
     stages_total: {Anzahl Stufen}
     stages_passed: []
     stages_failed: []
     stages_no_tests: []
     started_at: "{DATUM}"

4. Logge: "[T_orchestrate] START — {NAME}, Stufen: {tdd_stages}, Team: t-{NAME}"
```

### Schritt 0.5: User-Story-Scope laden (OPTIONAL — RF-TS-001, ADR-TS-001)

```
# ═══ USER-STORY-SCOPE (BL-011: UserStory_TestSelektion) ═══
# OPTIONAL: Task.md lesen fuer Scope-basierte Test-Selektion.
# Wenn vorhanden: extrahiere Keywords → user_story_scope (kompakter String, max ~100 Zeichen).
# Wenn NICHT vorhanden: user_story_scope = null → Verhalten identisch zu v1.1.0.
# ADR-TS-001: Scope als CLI-String, nicht als Datei-Referenz.

IF {VAULT}/Task.md EXISTIERT UND NICHT LEER:
  Lies {VAULT}/Task.md:
    - Extrahiere betroffene Bereiche / Module / Keywords
    - Komprimiere auf max 5-10 Keywords (keine ganzen Saetze)
    - user_story_scope = "{keyword1} {keyword2} ... {keywordN}"
  Logge: "[T_orchestrate] User-Story-Scope geladen: {user_story_scope}"
ELSE:
  user_story_scope = null
  Logge: "[T_orchestrate] Kein Task.md — User-Story-Scope: null (Fallback)"
```

### Schritt 1: STUFEN-LOOP

```
# ═══ ANTI-SKIP INVARIANTE (Fix PL #1, CaseStudy DCSRE-1672) ═══
# ALLE Stufen in tdd_stages MUESSEN durchlaufen werden — AUSNAHMSLOS.
# CaseStudy DCSRE-1672: Nur S1 (556 Tests) lief, S2-S5 alle SKIP.
# User-Erwartung: "alle 5 Stufen testen, nicht nur Unit"
#
# REGELN:
#   KEIN break aus diesem Loop.
#   KEIN continue OHNE die Stufe als PASS/FAIL/NO_TESTS zu markieren.
#   KEIN early return. KEIN "skip weil keine Tests gefunden".
#   Wenn testSearch KEINE Tests findet → Stufe = NO_TESTS (NICHT SKIP).
#   Am Ende: Vollstaendigkeits-Pruefung (jede Stufe MUSS einen Status haben).

Logge: "[T_orchestrate] STUFEN-LOOP: {tdd_stages.length} Stufen zu durchlaufen: {tdd_stages}"

FOR stufe IN tdd_stages:
  Logge: "[T_orchestrate] ═══ S{stufe} START ({tdd_stages.indexOf(stufe) + 1}/{tdd_stages.length}) ═══"

  # ═══════════════════════════════════════════════════════════════════
  # Stage 7 SONDERBEHANDLUNG: User-Journey via Playwright MCP
  # Stage 7 ruft KEIN dotnet test, sondern Skill(_user_journey).
  # Pre-Flight-Check + Skill-Routing — siehe stage_7.md.
  # ═══════════════════════════════════════════════════════════════════
  IF stufe == 7:
    # PRE-FLIGHT (PFLICHT): User explizit fragen ob System bereit ist
    # Dies ist der EINZIGE HiL-Punkt in T_orchestrate (auch im Dark-Factory-Modus,
    # weil System-Hochfahren extern ist).
    Frage User:
      "[T_orchestrate Stage 7 PRE-FLIGHT] System fuer User-Journey bereit?"
      "  - Frontend laeuft auf https://localhost:8443 (lokal/Docker)?"
      "  - Backend laeuft auf https://localhost:5443 (lokal/Docker)?"
      "  - DB + Keycloak Container healthy?"
      "  - Test-User-Daten geseedet?"
    IF Antwort != "alles bereit":
      stages_no_tests APPEND 7
      Logge: "[T_orchestrate] S7: NO_TESTS — System nicht bereit (User-Bestaetigung fehlt). Stage uebersprungen."
      Aktualisiere _manifest.md → T_ORCHESTRATE_STATE (stages_no_tests).
      CONTINUE  # zur naechsten Stufe (oder Loop-Ende)

    # Journey-Quelle bestimmen: Inline aus Manifest ODER Datei
    journey_file = ".claude/scripts/journeys/{NAME}.md"
    IF DATEI_EXISTIERT(journey_file):
      journey_content = lies(journey_file)
    ELIF user_story_scope != null:
      journey_content = "Test User-Story-Scope: {user_story_scope}"
    ELSE:
      stages_no_tests APPEND 7
      Logge: "[T_orchestrate] S7: NO_TESTS — Keine Journey-Beschreibung gefunden ({journey_file} fehlt + kein user_story_scope)."
      CONTINUE

    # Skill-Routing: Browser-Test via Playwright MCP
    Skill(skill="_user_journey", args="{NAME}\n\n{journey_content}")
    # Skill schreibt: .claude/output/UJ-{NAME}-{DATE}.md
    # Skill liefert: PASS/FAIL pro Schritt + Screenshots

    # Ergebnis lesen
    uj_report = neueste(".claude/output/UJ-{NAME}-*.md")
    journey_pass = uj_report.frontmatter.result == "PASS"

    IF journey_pass:
      stages_passed APPEND 7
      Logge: "[T_orchestrate] S7: PASS ({uj_report.steps_passed}/{uj_report.steps_total} Journey-Schritte gruen)"
    ELSE:
      stages_failed APPEND 7
      Logge: "[T_orchestrate] S7: FAIL ({uj_report.steps_failed} Schritte fehlgeschlagen)"
      # PL-Item analog zu anderen Stufen
      Schreibe _parking-lot.md APPEND PL-Item mit uj_report-Pfad.

    Aktualisiere _manifest.md → T_ORCHESTRATE_STATE.
    CONTINUE  # → naechste Stufe

  # --- Phase A: Tests finden (Stages 1-6) ---
  # Fix PL #3: NUR via Skill() — NIEMALS selbst "dotnet test" ausfuehren!
  # BL-011: --user-story bedingt anhaengen (RF-TS-001, ADR-TS-001)
  IF user_story_scope != null:
    Skill(skill="_I_testSearch", args="{NAME} --stufe {stufe} --mode=testRun --user-story {user_story_scope}")
  ELSE:
    Skill(skill="_I_testSearch", args="{NAME} --stufe {stufe} --mode=testRun")
  # _I_testSearch findet Tests fuer diese Stufe
  # Mit --user-story: Scope-basierte K/B/A Kategorisierung (RF-TS-003)
  # Ohne --user-story: Kanarienvogel-Modus (alle Tests = K, Fallback wie v1.1.0)

  # Pruefe ob Tests gefunden wurden (Anti-Skip Guard)
  test_count = lies testSearch_result.test_count ?? 0

  IF test_count == 0:
    # KEIN Skip! Stufe als NO_TESTS markieren und zur naechsten Stufe
    stages_no_tests APPEND stufe
    Logge: "[T_orchestrate] S{stufe}: NO_TESTS (0 Tests gefunden — KEIN Skip, kein Regressions-Risiko)"
    # Manifest-Update auch bei NO_TESTS
    Aktualisiere _manifest.md → T_ORCHESTRATE_STATE:
      stages_passed: {aktuelle Liste}
      stages_failed: {aktuelle Liste}
      stages_no_tests: {aktuelle Liste}
    # WEITER zur naechsten Stufe (NICHT abbrechen!)
    CONTINUE

  Logge: "[T_orchestrate] S{stufe}: {test_count} Tests gefunden — fuehre aus"

  # --- Phase B: Tests ausfuehren ---
  # Fix PL #3: NUR via Skill() — NIEMALS selbst ausfuehren!
  Skill(skill="_TDD_execute", args="{NAME} {stufe} 1 GREEN")
  # _TDD_execute fuehrt testbefehl aus stage_{N}.md aus
  # EXPECTED=GREEN: Alle Tests muessen bestehen (Verifikation, nicht TDD-Red)
  # Iteration=1: Erster (und einziger) Durchlauf pro Stufe

  # --- Phase C: Ergebnis auswerten ---
  Lies Ergebnis aus TDD-STATE.md oder Manifest:
    green_confirmed: {true | false}
    test_output: {letzte relevante Zeilen}

  IF green_confirmed == true:
    stages_passed APPEND stufe
    Logge: "[T_orchestrate] S{stufe}: PASS ({test_count} Tests gruen)"

  ELSE (green_confirmed == false):
    stages_failed APPEND stufe
    Logge: "[T_orchestrate] S{stufe}: FAIL"

    # PL-Item erstellen (SDF/T_orchestrate hat PL-Schreibrecht)
    Schreibe {VAULT}/_parking-lot.md APPEND:
      - [ ] **[TestVerify-S{stufe}] {NAME}: Test-Failures** — Gefunden in Test-Verifikation
        - Prioritaet: HOCH
        - Quelle: /_T_orchestrate {DATUM}, Stufe S{stufe}
        - Details: {test_output, max 5 Zeilen}

  # Manifest-Update nach JEDER Stufe (nicht erst am Ende!)
  Aktualisiere _manifest.md → T_ORCHESTRATE_STATE:
    stages_passed: {aktuelle Liste}
    stages_failed: {aktuelle Liste}
    stages_no_tests: {aktuelle Liste}

  Logge: "[T_orchestrate] S{stufe} ERLEDIGT — weiter zu S{stufe+1}"
  # → KEIN Abbruch bei FAIL (verify-only) — PFLICHT: naechste Stufe starten!

END FOR

# ═══ VOLLSTAENDIGKEITS-PRUEFUNG (Fix PL #1: S2-S5 Skip erkennen) ═══
completed_stages = stages_passed + stages_failed + stages_no_tests
missing_stages = [s fuer s in tdd_stages wenn s NICHT in completed_stages]
IF missing_stages.length > 0:
  Logge: "[T_orchestrate] FEHLER: {missing_stages.length} Stufe(n) NICHT durchlaufen: {missing_stages}"
  Logge: "[T_orchestrate] Dies ist eine ANOMALIE — Stufen duerfen NICHT uebersprungen werden!"
  FUER stufe IN missing_stages:
    stages_failed APPEND stufe
    Logge: "[T_orchestrate] S{stufe}: als FAIL markiert (nicht durchlaufen = Anomalie)"
  Aktualisiere _manifest.md → T_ORCHESTRATE_STATE:
    stages_passed: {aktuelle Liste}
    stages_failed: {aktuelle Liste}
    stages_no_tests: {aktuelle Liste}
ELSE:
  Logge: "[T_orchestrate] VOLLSTAENDIG: Alle {tdd_stages.length} Stufen durchlaufen"
```

### Schritt 2: Monitoring-Ausgabe

```
# Zusammenfassungs-Tabelle (PFLICHT-Output)
Logge:

## T_orchestrate Ergebnis: {NAME}

# BL-011 RF-TS-005: User-Story-Scope Anzeige
User-Story-Scope: {user_story_scope ?? "nicht geladen (Fallback: alle Tests = K)"}

| Stufe | Tests gefunden | Status | PL-Item |
|-------|----------------|--------|---------|
| S{1}  | {count_s1}     | PASS / FAIL / NO_TESTS | {ID oder —} |
| S{2}  | {count_s2}     | PASS / FAIL / NO_TESTS | {ID oder —} |
| ...   | ...            | ...    | ...     |
| **GESAMT** | — | {pass}/{total} PASS, {fail}/{total} FAIL, {no_tests}/{total} NO_TESTS | {pl_count} Items |

# VOLLSTAENDIGKEITS-CHECK: Alle {total} Stufen durchlaufen? {JA/NEIN}
```

### Schritt 3: Manifest finalisieren + Handschuh-Wechsel

```
# Final-State berechnen
IF stages_failed ist leer:
  final_status = DONE_PASS
  Logge: "[T_orchestrate] ALL PASS — keine Regressionen gefunden"
ELSE:
  final_status = DONE_FAIL
  Logge: "[T_orchestrate] {Anzahl} Stufe(n) FAIL — {Anzahl} PL-Items erstellt"

# Manifest abschliessen
Aktualisiere _manifest.md → T_ORCHESTRATE_STATE:
  status: {final_status}
  finished_at: "{DATUM}"

# Team aufraeumen
TeamDelete: "t-{NAME}"
Logge: "[T_orchestrate] Team t-{NAME} geloescht"

# Handschuh-Wechsel zurueck an SDF (Puppet-Master-Pattern)
# SDF liest T_ORCHESTRATE_STATE.status und entscheidet:
#   DONE_PASS → Stage-Progression oder POST-Phase
#   DONE_FAIL → Neue PL-Items abarbeiten (zurueck in SDF-Loop)
Logge: "[T_orchestrate] Handschuh-Wechsel → SDF"
```

---

## Pipeline-Position

```
[/_I_orchestrate]     Implementation abgeschlossen
        |
        v (Handschuh-Wechsel via SDF)
[/_T_orchestrate]     Test-Verifikation  <-- DIESER COMMAND
   |         |
   |  (pro Stufe)
   |    [/_I_testSearch]    Tests finden (--mode=testRun)
   |    [/_TDD_execute]     Tests ausfuehren (EXPECTED=GREEN)
   |         |
   v         v
[/_SDF_orchestrate]   Entscheidet: weiter oder PL-Items abarbeiten
```

---

## Regeln

1. **KEIN Code schreiben** — nur bestehende Tests ausfuehren
2. **KEIN git** — kein commit, kein push, kein stage
3. **ALLE Stufen durchlaufen** — auch bei FAIL nicht abbrechen
4. **PL-Item bei FAIL** — jede fehlgeschlagene Stufe wird im Parking Lot dokumentiert
5. **Handschuh-Wechsel** — am Ende IMMER Kontrolle an SDF zurueckgeben
6. **Manifest-Update** — nach JEDER Stufe aktualisieren (nicht erst am Ende)
7. **Tandem-Prinzip** — _I_testSearch + _TDD_execute, IMMER zusammen, NIE einzeln
